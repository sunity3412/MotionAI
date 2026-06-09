"""분석 파이프라인 — S3 업로드 이벤트 → SQS → 이 함수 (비동기).

두 가지 처리 경로:
  1. RunPod 위임 (운영) — RUNPOD_ANALYZE_URL + RUNPOD_AUTH_TOKEN 환경변수가
     set 이면 HTTP POST 로 위임. Lambda 는 즉시 끝. RunPod 서버가 S3 다운로드 →
     NLF GPU 추출 → reference 비교 → Firestore Admin 갱신 일체 처리.
     backend/runpod_inference/server.py 참조.
  2. 직접 처리 (폴백, 개발용) — RunPod 환경변수 미설정 시 이 Lambda 가 직접
     NLF 추론까지. Lambda 가 GPU 없는 환경이라 실제로는 NaN — #7-follow
     운영 GPU 인프라 켜지기 전 흐름 검증용.

알고리즘 코어(features/temporal/motiondtw/kismam/selfmotion/assemble)는 모델
무관·유닛 검증됨. 무거운 모델/ffmpeg/Cerebras 는 interfaces 어댑터로 분리 —
3D 포즈는 NLF(pose_estimator), 영상은 ffmpeg(frame_extractor), 코칭은
Cerebras(coach_writer). NLF 추론은 GPU 필요(plan.md #7-follow).

오케스트레이션 정직성:
  - 인체 미감지(NoHumanError) → contract no_human 으로 실패 기록.
  - 그 외 런타임 오류 → server_error 로 실패 기록(사용자 노출 문구).

상태/오류/경로는 docs/contract.md, 단계는 models.PIPELINE_SEQUENCE.

Phase 6 (2026-06-08, Plan 06-02) — body_normalizer 통합 wiring:
  - R3 fix: 단일 `_extract_video_analysis_inputs` helper — S3 download + frame
    extract + RTMW estimate 1회만 실행. Gemini ON 시 keep_local_video=True.
  - R4 fix: student_profile 반환 non-null (measure_body_profile fallback 정합).
  - R2 wiring: reference 의 bodyComparisonSourcePose 도 fetch + source_keypoints 전달.
  - R8 fix: extra_warnings injection (dataclasses.replace 우회 금지).
  - C2 fix: _match_reference_by_motion_id exact-match (profile.motion_id 기반).
  - C8 fix: _dataclass_to_camel_case_dict 4-case helper (Task 3 wiring).
  - W1: comparisonType 3 cases + usedReferenceFallback boolean.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import tempfile
import threading
import urllib.error
import urllib.request
from enum import Enum
from pathlib import Path
from typing import NamedTuple

import boto3  # Lambda 런타임 제공
import numpy as np

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import (
    assemble,
    body_normalizer,
    dimensions,
    kismam,
    segments,
    skeleton,
    technique,
)
from sunity_shared.analysis import force_signals as fs
from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.body_normalization_measurer import measure_body_profile
from sunity_shared.analysis.features import (
    compute_joint_angles,
    feature_vector,
    joint_uncertainty,
)
from sunity_shared.analysis.interfaces import NoHumanError, NotPoleMotionError  # 가벼움 — 예외만
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
from sunity_shared.analysis.pole_geometry import (
    PoleAxisMeasurement,
    build_pole_axis_measurement,
)
from sunity_shared.analysis.pose_frame import PoleAxis, to_coco17_array
from sunity_shared.analysis.temporal import temporal_fill
from sunity_shared.events import iter_s3_keys_from_sqs
from sunity_shared.s3keys import parse_upload_key

# FfmpegFrameExtractor / NlfPoseEstimator / CerebrasCoachWriter 는 imageio·torch·
# requests 같은 무거운 의존성을 끌어옴. RunPod 위임 모드에선 사용하지 않으므로
# _ensure_adapters() 안에서 lazy import — Lambda 콜드스타트 절감 + 테스트가
# 어댑터 의존성 없이도 lambda_handler 디스패치를 검증할 수 있게 한다.

log = logging.getLogger()
log.setLevel(logging.INFO)

_s3 = boto3.client("s3")
# 결과 화면 영상 재생 서명 URL 만료(초). 7일 = sigv4 + 영구 IAM 키의 최대값.
# 3600s 였을 때 belle 가 시연 후 다시 결과 화면을 열면 URL 이 만료돼 본인 영상이
# 비어 보였다(P0 #6). 운영 경로(RunPod)는 sunity-motion 영구 키로 서명하므로
# 7일 풀로 사용 가능. Lambda 폴백 경로의 임시 자격증명은 세션 길이로 자동 캡됨.
_PLAYBACK_EXPIRES = 7 * 24 * 60 * 60

# RunPod 위임 환경 — 운영에서만 set. 미설정 시 폴백(_process) 이라 개발은 그대로.
_RUNPOD_URL = os.environ.get("RUNPOD_ANALYZE_URL", "").strip()
_RUNPOD_TOKEN = os.environ.get("RUNPOD_AUTH_TOKEN", "").strip()
_RUNPOD_TIMEOUT_S = 10  # HTTP 위임 응답 대기 (Pod 은 202 즉시 반환 — 늦으면 장애)


def _runpod_enabled() -> bool:
    return bool(_RUNPOD_URL and _RUNPOD_TOKEN)


def _delegate_to_runpod(bucket: str, key: str) -> None:
    """RunPod /analyze 로 위임. 202/200 외 응답은 예외 → Lambda 가 fail_analysis 매핑.
    urllib 표준 라이브러리만 사용(requests 의존성 X — Layer 추가 부담 없음).

    RunPod proxy(*.proxy.runpod.net) 는 Cloudflare 뒤에 있다. urllib 의 기본
    User-Agent("Python-urllib/3.x") 가 Cloudflare 의 봇 차단(에러 1010) 에 걸려
    403 이 떨어진다. 일반적인 UA 와 Accept 헤더를 박아 통과시킨다."""
    payload = json.dumps({"bucket": bucket, "key": key}).encode("utf-8")
    req = urllib.request.Request(
        _RUNPOD_URL,
        method="POST",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "sunity-motion-pilot/1.0 (+aws-lambda)",
            "X-RunPod-Token": _RUNPOD_TOKEN,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_RUNPOD_TIMEOUT_S) as resp:
            if resp.status not in (200, 202):
                body = resp.read()[:512]
                raise RuntimeError(f"runpod {resp.status}: {body!r}")
    except urllib.error.HTTPError as e:
        body = e.read()[:512] if hasattr(e, "read") else b""
        raise RuntimeError(f"runpod HTTPError {e.code}: {body!r}") from e


# ML 어댑터 (폴백 경로 전용). RunPod 위임 사용 시 이 어댑터는 호출되지 않으므로
# Lambda 콜드스타트 비용도 절감 — 모듈 로드 시 즉시 생성하던 동작을 지연 생성으로
# 바꿔 RunPod 모드에서 NLF/ffmpeg/torch import 비용을 회피한다.
_FRAME_EXTRACTOR = None  # type: ignore[var-annotated]
_POSE_ESTIMATOR = None  # type: ignore[var-annotated]
_COACH_WRITER = None  # type: ignore[var-annotated]
# R3 fix (Phase 6, Plan 06-02): _extract_video_analysis_inputs 가 직접 호출하는
# RTMW engine singleton. _POSE_ESTIMATOR (RTMWNlfCompat) 는 NLF interface 호환용
# 래퍼. 새 통합 helper 는 estimate(frames, pole_axis) → list[PoseFrame] 시그너처
# 의 RTMW 본체를 직접 호출 — pose_frames 가 measure_body_profile / body_normalizer
# 양 경로에서 필요. None 기본값 — lazy init in _ensure_adapters().
_RTMW_ENGINE = None  # type: ignore[var-annotated]

# 기술 인식 어댑터 — swappable (technique.TechniqueRecognizer 프로토콜).
# Plan 5-03 박제 — 즉시 생성 박제 X → `_ensure_recognizer()` lazy creation 분기.
#
# 박제 정신 (D-12 / D-16 / Plan 5-03):
#   · D-12: RunPod server.py 무수정 1pass — pipeline 모듈 1점 swap 박제로 자동 작동.
#   · D-16: lazy import — pipeline 모듈 로드 시 google.genai / firebase_admin / boto3
#     (Lambda 런타임 제외) 0 import. Gemini 모드 진입 시점에만 lazy import.
#   · default = FallbackRecognizer (env 미설정 시) — 회귀 위험 최소 + A/B 비교 가능.
#
# env switch 박제 (둘 중 하나):
#   · GEMINI_RECOGNIZER_ENABLED=1|true|on|yes  (case-insensitive)
#   · RECOGNIZER_BACKEND=gemini                 (case-insensitive)
# 그 외 (미설정 / 다른 값) = FallbackRecognizer 박제 보존.
_RECOGNIZER: technique.TechniqueRecognizer | None = None
_RECOGNIZER_LOCK = threading.Lock()

# env switch 박제 값 (case-insensitive lower).
_GEMINI_ENV_TRUTHY = frozenset({"1", "true", "on", "yes", "gemini"})


def _gemini_enabled() -> bool:
    """env 기반 Gemini 어댑터 활성 여부 박제.

    두 env var 박제 (호환 alias):
      · GEMINI_RECOGNIZER_ENABLED — Plan 5-03 신설 박제
      · RECOGNIZER_BACKEND        — 기존 RunPod env 박제 패턴 정합

    case-insensitive. 박제 truthy 값 = {"1", "true", "on", "yes", "gemini"}.
    그 외 또는 미설정 = False (FallbackRecognizer 박제 보존).

    Plan 08-03 (REVIEWS R6 helper drift 차단) — Phase 8 Layer 2 wiring 박제도
    본 helper 재사용 (신규 keep-local-video 박제 helper 영구 차단).
    """
    for env_var in ("GEMINI_RECOGNIZER_ENABLED", "RECOGNIZER_BACKEND"):
        val = os.environ.get(env_var, "").strip().lower()
        if val in _GEMINI_ENV_TRUTHY:
            return True
    return False


# ── Phase 8 Plan 08-03 wiring — Layer 2 + preflight gate env helper ─────────


def _force_signals_layer2_enabled() -> bool:
    """REVIEWS R7 — FORCE_SIGNALS_LAYER2_ENABLED 별도 env flag 박제.

    Phase 5 RECOGNIZER_BACKEND 와 분리. Phase 8 Layer 2 default off — env 박제
    unset 시 비활성. belle 운영 작업 시 Lambda env / RunPod Pod env 박제만으로
    flip (코드 변경 0).
    """
    raw = os.environ.get("FORCE_SIGNALS_LAYER2_ENABLED", "").strip().lower()
    return raw in ("1", "true", "on", "yes")


def _preflight_label_gate_passed() -> bool | None:
    """REVIEWS Cycle 2 NEW HIGH #1 차단 (R4 carryover plumbing).

    belle 운영 작업: Plan 08-00 박제 25-timestamp PASS 검증 후 Lambda env 또는
    RunPod Pod env 박제 `PREFLIGHT_LABEL_GATE_PASSED=1` 박제만으로 Layer 1
    confidence='medium' 승급 박제 — 코드 변경 0.

    3-state 박제:
      · '1'/'true'/'on'/'yes'   → True  (gate PASS, confidence='medium' 승급)
      · '0'/'false'/'off'/'no'  → False (gate FAIL, 'low' + warning 'preflight_label_gate_failed')
      · '' (unset) 또는 그 외   → None  (gate 미실행 default, 'low' + warning 'preflight_gate_pending')

    Plan 08-00 박제 preflight_label_template.csv + Plan 08-02 박제
    compute_phase_boundaries 의 preflight_label_gate_passed 인자 박제 정합.
    """
    raw = os.environ.get("PREFLIGHT_LABEL_GATE_PASSED", "").strip().lower()
    if raw in ("1", "true", "on", "yes"):
        return True
    if raw in ("0", "false", "off", "no"):
        return False
    return None


# Phase 5 박제 GeminiTechniqueRecognizer 재사용 박제 singleton — Phase 8 Layer 2
# 가 동일 instance 박제 reuse (신규 instance 영구 차단, REVIEWS R6).
_FORCE_SIGNALS_LAYER2_RECOGNIZER = None  # type: ignore[var-annotated]


def _get_force_signals_layer2_recognizer():
    """Phase 8 Layer 2 박제 recognizer singleton 박제 (REVIEWS R6 정합).

    FORCE_SIGNALS_LAYER2_ENABLED env truthy AND _gemini_enabled() truthy 시 lazy
    init. Phase 5 _ensure_recognizer 박제와는 별도 path — 본 helper 는 force_signals
    가 단순 reuse 박제 hook (실제 Layer 2 박제는 technique_profile.key_moments
    박제 reuse 박제이므로 recognizer 직접 호출 X).

    Plan 08-03 박제 — 본 helper 는 활성화 판정 source 박제 (env 둘 다 truthy 시 True).
    """
    global _FORCE_SIGNALS_LAYER2_RECOGNIZER
    if not _force_signals_layer2_enabled():
        return None
    if not _gemini_enabled():
        return None
    # Phase 5 _ensure_recognizer 박제 singleton 재사용 — 신규 instance 영구 차단.
    if _FORCE_SIGNALS_LAYER2_RECOGNIZER is None:
        _FORCE_SIGNALS_LAYER2_RECOGNIZER = _ensure_recognizer()
    return _FORCE_SIGNALS_LAYER2_RECOGNIZER


def _ensure_recognizer() -> technique.TechniqueRecognizer:
    """lazy creation + env switch 박제 (Plan 5-03).

    double-checked locking 박제로 thread 안전 — Pod uvicorn 은 `--workers 1` 박제
    기본이지만 BackgroundTasks 가 다중 분석 동시 진입 가능 (다중 SQS 메시지).

    분기:
      · env switch ON  → GeminiTechniqueRecognizer + TechniqueCache + record_unregistered_keyword hook 합성
      · env switch OFF → FallbackRecognizer 박제 (회귀 0)

    return: technique.TechniqueRecognizer 인스턴스 (멱등 — 2회 호출 = 같은 instance).
    """
    global _RECOGNIZER
    if _RECOGNIZER is not None:
        return _RECOGNIZER
    with _RECOGNIZER_LOCK:
        if _RECOGNIZER is not None:
            return _RECOGNIZER
        if _gemini_enabled():
            # D-16 lazy import — Gemini 모드 진입 시점에만 import.
            from sunity_shared.analysis.gemini_technique_recognizer import (
                GeminiTechniqueRecognizer,
            )
            from sunity_shared.analysis.technique_cache import TechniqueCache

            cache = TechniqueCache()
            # D-09 case 3 — Phase 16 TERM-DATA-01 분기 3 자동 수집 hook.
            # cache 생성 시점에 uid 미상이므로 default uid="anonymous-pipeline".
            # WR-03 fix: _process 진입 시점에 closure 로 rebind 해서 실제 caller
            # uid 가 record_unregistered_keyword(uid=...) 에 전달됨. 본 default 는
            # _process 우회 path (직접 recognize 호출 — 현재 없음) 의 안전망.
            def _record_unregistered_default(keyword: str, video_hash: str) -> None:
                firestore_admin.record_unregistered_keyword(
                    keyword, uid="anonymous-pipeline", video_hash=video_hash
                )

            _RECOGNIZER = GeminiTechniqueRecognizer(
                cache=cache,
                unregistered_hook=_record_unregistered_default,
            )
            log.info("Recognizer = GeminiTechniqueRecognizer (env switch ON)")
        else:
            _RECOGNIZER = technique.FallbackRecognizer()
            log.info("Recognizer = Fallback (env switch OFF — default)")
        return _RECOGNIZER


class _RTMWNlfCompat:
    """Plan 25 atomic swap (2026-06-05): RTMW → NLF interface 호환 어댑터.

    pipeline/_process 의 `_POSE_ESTIMATOR.estimate(frames) → np.ndarray (T,17,4)` 호출
    유지. 내부에서 RTMWPoseEngine + vertical pole_axis fallback + to_coco17_array 변환.

    박제 정신 [[rtmw-free-stack-pivot]] 정합 — NLF/ultralytics 의존 제거.
    """

    def __init__(self) -> None:
        from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
        from sunity_shared.analysis.pose_frame import PoleAxis
        self._engine = RTMWPoseEngine()
        self._default_pole = PoleAxis(
            axis_vector=(0.0, 1.0, 0.0),
            confidence_level="low",
            source="vertical_fallback",
            frame_index=None,
        )

    def estimate(self, frames):
        """RTMW pose estimation → COCO-17 array (T,17,4) — NLF 호환 interface.

        B8 박제 (2026-06-04 revision) — 시그너처 `-> np.ndarray` 무변경.
        body_shape injection 은 estimate_with_profile 의 책임 — 본 method
        는 회귀 0 유지.
        """
        from sunity_shared.analysis.pose_frame import to_coco17_array
        pose_frames = self._engine.estimate(frames, self._default_pole)
        return to_coco17_array(pose_frames)

    def estimate_with_profile(self, frames):
        """RTMW pose estimation + BodyNormalizationProfile measure → race-safe tuple.

        HIGH-1 v4 박제: 본 method 는 local-return tuple 반환. 사이드카
        mutable instance attribute (v3 의 stale-cache pattern) 영구 폐기.
        RunPod FastAPI BackgroundTasks (server.py:198, 213) 환경에서
        concurrent analyses 가 _POSE_ESTIMATOR 글로벌 공유해도 profile
        leak 0 — caller 가 자기 frame 의 profile 만 local tuple 로 받음.
        B8 박제 (estimate / _angles_from_video /
        _angles_and_video_path_from_video 시그너처) 무변경.

        Returns:
          (coco_array, profile) — coco_array shape (T,17,4), profile 은
          measure_body_profile 산출 BodyNormalizationProfile (fallback 가능).
        """
        from sunity_shared.analysis.body_normalization_measurer import (
            measure_body_profile,
        )
        from sunity_shared.analysis.pose_frame import to_coco17_array

        pose_frames = self._engine.estimate(frames, self._default_pole)
        profile = measure_body_profile(pose_frames)
        # body_shape 주입 — caller 가 dataclasses.asdict 시 동일 video-level profile.
        pose_frames_with_profile = [
            dataclasses.replace(pf, body_shape=profile) for pf in pose_frames
        ]
        coco_array = to_coco17_array(pose_frames_with_profile)
        return coco_array, profile


def _ensure_adapters() -> None:
    """폴백 처리(_process) 진입 시 1회 어댑터 생성 + lazy import.
    RunPod 모드에선 이 함수가 호출되지 않아 imageio·torch 도 import 안 됨.

    Plan 25 atomic swap (2026-06-05): NlfPoseEstimator → _RTMWNlfCompat (RTMW 기반,
    NLF interface 호환). 박제 정신 [[rtmw-free-stack-pivot]] 정합.

    Plan 06-02 R3 fix: _RTMW_ENGINE singleton 추가 — _extract_video_analysis_inputs
    가 RTMW 본체를 직접 호출 (pose_frames list[PoseFrame] 필요).
    """
    global _FRAME_EXTRACTOR, _POSE_ESTIMATOR, _COACH_WRITER, _RTMW_ENGINE
    if _FRAME_EXTRACTOR is None:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        _FRAME_EXTRACTOR = FfmpegFrameExtractor()
    if _POSE_ESTIMATOR is None:
        _POSE_ESTIMATOR = _RTMWNlfCompat()
    if _RTMW_ENGINE is None:
        # _POSE_ESTIMATOR._engine 재사용 — 동일 RTMW instance.
        # _POSE_ESTIMATOR (RTMWNlfCompat) 의 _engine attribute 가 RTMWPoseEngine.
        _RTMW_ENGINE = _POSE_ESTIMATOR._engine  # type: ignore[attr-defined]
    if _COACH_WRITER is None:
        from sunity_shared.analysis.coach_writer import CerebrasCoachWriter
        _COACH_WRITER = CerebrasCoachWriter()


def _signed_get(bucket: str, key: str) -> str:
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=_PLAYBACK_EXPIRES,
    )


def _angles_from_video(bucket: str, key: str) -> np.ndarray:
    """S3 영상 → 프레임 → NLF 3D keypoints → 관절각(T,J), 시간축 폐색 보간.

    B8 fix (2026-06-04 revision) — 시그너처 무변경 유지 박제. RunPod server.py
    `_process` 호출이 본 함수 path 를 직접 사용 X (server.py 는 pipeline 모듈을
    import 만 함). 본 함수의 시그너처는 단위 테스트가 박제로 검증 — 변경 시
    test_pipeline_recognizer_switch.TestB8FixSignature 가 차단.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        _s3.download_file(bucket, key, tmp.name)
        frames = _FRAME_EXTRACTOR.extract(tmp.name)
    keypoints = _POSE_ESTIMATOR.estimate(frames)  # (T,17,4) — 미감지 시 NoHumanError
    angles = compute_joint_angles(keypoints)
    return temporal_fill(angles, joint_uncertainty(keypoints))


def _angles_and_body_profile_from_video(
    bucket: str, key: str
):
    """Phase 2 v4 박제 — race-safe local-return helper (HIGH-1 v4).

    HIGH-1 v4 박제: _POSE_ESTIMATOR.estimate_with_profile 가 local tuple 로
    (angles_filled, profile) 반환. 사이드카 mutable state 0. RunPod FastAPI
    BackgroundTasks 환경 concurrent analyses 가 module-level _POSE_ESTIMATOR
    글로벌 공유해도 caller 가 자기 frame 의 profile 만 받음.
    B8 박제 (_angles_from_video / _angles_and_video_path_from_video) 무변경 —
    본 helper 는 그 옆 신설.

    Returns:
      (angles_filled, profile) — angles shape (T,J), profile 은
      BodyNormalizationProfile 또는 None.

    MEDIUM-1 v4 박제: Firestore 저장 / AnalysisDoc 갱신 X — Phase 6 plan
    이 본 helper 를 호출하여 wire-up. 본 phase 는 helper 박제만.
    """
    _ensure_adapters()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        _s3.download_file(bucket, key, tmp.name)
        frames = _FRAME_EXTRACTOR.extract(tmp.name)
    keypoints, profile = _POSE_ESTIMATOR.estimate_with_profile(frames)
    angles = compute_joint_angles(keypoints)
    angles_filled = temporal_fill(angles, joint_uncertainty(keypoints))
    return angles_filled, profile


# ── R3 fix (Phase 6, Plan 06-02) — 통합 helper _extract_video_analysis_inputs ──
#
# 기존 `_angles_and_video_path_from_video` (B8 fix Gemini path) 폐기 — 새 단일
# helper 가 Gemini ON / OFF 분기 모두 수용. RTMW estimate 1회만 실행 보장
# (T-06-02-06 mitigation — 두 helper 가 동시 호출되면 double RTMW).
#
# `_angles_from_video` + `_angles_and_body_profile_from_video` (Phase 2 caller) 는
# 무수정 보존 — RunPod server.py + 기존 테스트 정합.


class _VideoAnalysisInputs(NamedTuple):
    """R3 fix Phase 6 — 단일 helper 반환 5종 (Plan 08-03 박제 pole_axis_measurement 신설).

    angles: (T, J) 시간축 보간된 관절각.
    student_profile: BodyNormalizationProfile (R4 fix — 항상 non-null,
      measure_body_profile 의 _fallback_profile 정합).
    pose_frames: list[PoseFrame] — body_normalizer.compare_body_profiles 의
      pose_frames 인자 + _extract_target_torso_px helper 입력.
    local_video_path: Path | None — Gemini ON path (keep_local_video=True) 일
      때만 Path. caller 가 unlink 책임.
    pole_axis_measurement: PoleAxisMeasurement — Plan 08-03 신설 (REVIEWS R10
      정합). 기존 vertical fallback PoleAxis 박제 한계 explicit 노출. line=None
      → coordinate_space='unavailable' (Plan 08-00 박제 build_pole_axis_measurement
      박제). Phase 8 의 axis distance None 분기 자동 활성. 추후 HoughPoleDetector
      활성화 plan 박제 시 line 박제.
    """

    angles: np.ndarray
    student_profile: BodyNormalizationProfile
    pose_frames: list
    local_video_path: Path | None
    pole_axis_measurement: PoleAxisMeasurement


def _extract_video_analysis_inputs(
    bucket: str,
    key: str,
    default_pole: PoleAxis,
    *,
    keep_local_video: bool = False,
) -> _VideoAnalysisInputs:
    """R3 fix (2026-06-08 round-2, Plan 06-02 reviews).

    Phase 6 + Gemini path 의 video extraction 을 단일 helper 로 통합. S3 download +
    frame_extract + RTMW estimate 단 1회 실행 — 기존 `_angles_and_video_path_from_video`
    와 신설 예정이었던 `_angles_profile_and_frames_from_video` 가 동시 호출되면
    double RTMW 실행 (T-06-02-06). keep_local_video=True 시 local_video_path 반환
    (caller 가 unlink 책임). keep_local_video=False 시 cleanup. student_profile 은
    measure_body_profile 의 fallback 보장으로 non-null (R4 fix).
    """
    _ensure_adapters()
    tmp_path: str | None = None
    if keep_local_video:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            _s3.download_file(bucket, key, tmp_path)
            frames = _FRAME_EXTRACTOR.extract(tmp_path)
            pose_frames = _RTMW_ENGINE.estimate(frames, default_pole)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
    else:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
            _s3.download_file(bucket, key, tmp.name)
            frames = _FRAME_EXTRACTOR.extract(tmp.name)
            pose_frames = _RTMW_ENGINE.estimate(frames, default_pole)

    # R4 fix — measure_body_profile 의 _fallback_profile 정합 (non-null 보장).
    student_profile = measure_body_profile(pose_frames)

    # angles 산출 — R6 정합 (to_coco17_array 4채널 보존).
    keypoints_4ch = to_coco17_array(pose_frames)
    angles = compute_joint_angles(keypoints_4ch)
    angles_filled = temporal_fill(angles, joint_uncertainty(keypoints_4ch))

    local_video_path = Path(tmp_path) if tmp_path else None

    # Plan 08-03 (REVIEWS R10 정합) — pole_axis_measurement 박제. 현재 vertical
    # fallback (line=None → coordinate_space='unavailable'). 추후 HoughPoleDetector
    # 활성 plan 박제 시 line 박제. Phase 8 의 axis distance None 분기 자동 활성 박제.
    pole_axis_measurement = build_pole_axis_measurement(
        axis_3d=default_pole,
        line=None,
        frame_index=None,
    )
    return _VideoAnalysisInputs(
        angles=angles_filled,
        student_profile=student_profile,
        pose_frames=pose_frames,
        local_video_path=local_video_path,
        pole_axis_measurement=pole_axis_measurement,
    )


def _coerce_source_pose_dict(raw: dict | None) -> dict | None:
    """R2 wiring helper — Firestore stored source_pose dict → BodyComparisonSourcePose 생성자 dict.

    Firestore 가 list 로 저장한 joint_keys / values 를 tuple 로 변환 (frozen dataclass
    validator 정합). camelCase / snake_case 둘 다 수용 — Plan 06-03 백필이 camelCase
    로 저장.

    CR-03 fix (2026-06-08 review): silent `or` defaults 제거 — 실데이터 결손은 명시적
    ValueError. 진단 메시지는 server_error 로그에서 root cause 식별 가능. 정상 데이터
    (0.0 confidence, frame_index=0 등) 가 falsy 로 짤리는 함정도 동시 해결.
    """
    if raw is None:
        return None
    # camelCase → snake_case fallback lookup
    def _g(snake: str, camel: str):
        if snake in raw:
            return raw[snake]
        return raw.get(camel)

    joint_keys = _g("joint_keys", "jointKeys")
    # values 는 TS/Python 필드명 동일 — alias 없음. raw.get 직접.
    values = raw.get("values")
    if not joint_keys or not values:
        raise ValueError(
            "bodyComparisonSourcePose missing joint_keys or values "
            "(firestore document corrupted — refusing to coerce silently)"
        )
    frame_index = _g("frame_index", "frameIndex")
    torso_px = _g("torso_px", "torsoPx")
    confidence = _g("confidence", "confidence")
    measured_at = _g("measured_at", "measuredAt")
    if frame_index is None or torso_px is None or confidence is None or measured_at is None:
        raise ValueError(
            "bodyComparisonSourcePose missing required scalar field "
            "(frame_index / torso_px / confidence / measured_at)"
        )
    return {
        "joint_keys": tuple(joint_keys),
        "values": tuple(float(v) for v in values),
        "frame_index": int(frame_index),
        "torso_px": float(torso_px),
        "confidence": float(confidence),
        "measured_at": int(measured_at),
    }


def _coerce_body_profile_dict(raw: dict | None) -> dict | None:
    """CR-01/CR-02 fix (2026-06-08 review) — Firestore stored bodyNormalizationProfile
    dict → BodyNormalizationProfile 생성자 dict.

    Firestore 가 camelCase 로 저장 (extract_reference_body_profiles.py:_bp_to_camel_dict,
    seed-reference-body-profile.mjs:REQUIRED_BODY_PROFILE_FIELDS, firestore_admin.complete_analysis
    의 _dataclass_to_camel_case_dict 결과). 그러나 BodyNormalizationProfile dataclass
    는 snake_case 필드. 본 helper 가 camel/snake 양쪽 수용해서 snake_case kwargs 생성.

    camelCase 우선 시도, snake_case fallback — 테스트 fixture (snake) 와 production
    (camel) 모두 통과. None 입력 시 None 반환 (caller 의 None-skip 분기 정합).
    """
    if raw is None:
        return None

    def _g(snake: str, camel: str):
        if snake in raw:
            return raw[snake]
        return raw.get(camel)

    return {
        "estimated_height_scale": float(_g("estimated_height_scale", "estimatedHeightScale")),
        "arm_scale": float(_g("arm_scale", "armScale")),
        "leg_scale": float(_g("leg_scale", "legScale")),
        "torso_scale": float(_g("torso_scale", "torsoScale")),
        "shoulder_hip_ratio": float(_g("shoulder_hip_ratio", "shoulderHipRatio")),
        "confidence": float(_g("confidence", "confidence")),
        "warnings": list(_g("warnings", "warnings") or []),
    }


def _match_reference_by_motion_id(motion_id: str | None) -> dict | None:
    """C2 fix (2026-06-08, Plan 06-02 reviews) — exact-match reference lookup.

    TechniqueProfile.motion_id (Gemini canonical) → reference 컬렉션 exact-match.
    R2 wiring 정합 — 반환 dict 의 bodyNormalizationProfile + bodyComparisonSourcePose
    모두 read. motion_id None 시 None 반환 (FallbackRecognizer / low_confidence
    / unregistered path 등).
    """
    if not motion_id:
        return None
    return firestore_admin.get_reference_motion(motion_id)


def _extract_target_torso_px(pose_frames: list) -> float | None:
    """R2 wiring (2026-06-08 round-2) — target 영상의 평균 mid_shoulder↔mid_hip 거리.

    각 frame 의 keypoints_3d 에서 mid_shoulder = (l_shoulder + r_shoulder) / 2,
    mid_hip = (l_hip + r_hip) / 2. 두 좌표의 3D Euclidean 거리.

    WR-04 (2026-06-08 review): 3D Euclidean (x/y/z) 사용. 알고리즘 본체
    (normalize_pose_by_segments / _compute_temporal_variance_per_segment) 가
    3D 로 동작하므로 anchor 도 3D 이어야 self-consistent. 2D 만 사용하던 구
    버전은 forward/back lean 시 20-40% 작게 산출 → 모든 reproject segment 가
    비례 축소되어 spurious deficit 유발. 2D 변형은 is_foreshortening_detected
    안에서만 유지 (projection 이 점 자체인 케이스).

    NaN-safe — endpoint 미감지 frame skip + 모든 frame skip 시 None 반환
    (compare_body_profiles 가 'target_torso_px_missing' warning emit, WR-02).
    """
    if not pose_frames:
        return None
    distances: list[float] = []
    for f in pose_frames:
        kp = getattr(f, "keypoints_3d", None)
        if not kp:
            continue
        needed = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
        if not all(n in kp for n in needed):
            continue
        ls, rs, lh, rh = (kp[n] for n in needed)
        ms_x = (ls.x + rs.x) / 2
        ms_y = (ls.y + rs.y) / 2
        ms_z = (ls.z + rs.z) / 2
        mh_x = (lh.x + rh.x) / 2
        mh_y = (lh.y + rh.y) / 2
        mh_z = (lh.z + rh.z) / 2
        dx = mh_x - ms_x
        dy = mh_y - ms_y
        dz = mh_z - ms_z
        d = (dx * dx + dy * dy + dz * dz) ** 0.5
        if d > 0:
            distances.append(d)
    if not distances:
        return None
    mean = sum(distances) / len(distances)
    import math as _math

    if not _math.isfinite(mean) or mean <= 0:
        return None
    return float(mean)


# ── C8 fix (Phase 6, Plan 06-02) — _dataclass_to_camel_case_dict 4-case 명세 ──
#
# Plan 06-02 Task 3 에서 사용 — body_comparison_report / student_profile dataclass
# → Firestore camelCase dict 변환. 4 case 명시 + 4 unit test.

def _snake_to_camel(key: str) -> str:
    """snake_case → camelCase. 첫 단어 lowercase + 나머지 capitalize."""
    parts = key.split("_")
    if not parts:
        return key
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


def _dataclass_to_camel_case_dict(obj):
    """C8 fix (2026-06-08, Plan 06-02 reviews). 5 case 명시.

    dataclass / list / dict / Enum / scalar 5 case 명시. BodyComparisonReport 의
    중첩 ScaleProfile + list[BodyComparisonFinding] 까지 모두 camelCase 변환.
    None 입력 시 None 반환.
    """
    if obj is None:
        return None
    if dataclasses.is_dataclass(obj):
        raw = dataclasses.asdict(obj)
        return {_snake_to_camel(k): _dataclass_to_camel_case_dict(v) for k, v in raw.items()}
    if isinstance(obj, Enum):
        return str(obj.value)
    if isinstance(obj, list):
        return [_dataclass_to_camel_case_dict(x) for x in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_camel_case_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {_snake_to_camel(k): _dataclass_to_camel_case_dict(v) for k, v in obj.items()}
    return obj


def _deviation_against(
    user_angles: np.ndarray, ref_angles_flat, num_joints: int
):
    """기준 시퀀스 대비 관절별 각도 편차(도) — mode1(정은지)·mode3 second+(이전 영상)
    공용 코어. flat 저장 angles 를 reshape → DTW 정렬 → per_joint_deviation.
    반환: (deviation(J,), match, user_seg, a_ref) — mode1 은 segment 점수에 match 사용."""
    a_ref = np.asarray(ref_angles_flat, dtype=float)
    if a_ref.ndim == 1:
        a_ref = a_ref.reshape(-1, num_joints)
    match = motion_dtw(feature_vector(user_angles), feature_vector(a_ref))
    user_seg = user_angles[match.start : match.end]
    deviation = per_joint_deviation(match.path, user_seg, a_ref)
    return deviation, match, user_seg, a_ref


def _mode3_comparison(
    angles: np.ndarray, prev: dict | None, profile: technique.TechniqueProfile
):
    """자기 성장(mode3) 분기 — 순수(어댑터/S3/Firestore 불필요, 테스트 가능).

    절대 차원(라인/안정성)은 기준 없이 산출 → 세션 간 같은 척도라 발전 측정 가능
    ([[mode3-progress-not-similarity]]). 각도 차원은 기준이 필요하므로 이전 분석이
    있을 때만(이전 영상 대비 일관성) 표시하고 overall/delta 에선 제외(척도 안정).

    반환: (assessments, dimension_scores, overall, comparison).
      - assessments: 관절각 기반(코칭 tips 용). 첫 분석은 신전 부족분(IPSF 라인),
        이후는 이전 영상 대비.
      - dimension_scores: 첫 분석=절대 차원, 이후=절대 + angle(일관성).
      - overall: 절대 차원 평균(첫 분석/이후 동일 척도)."""
    abs_dims = dimensions.absolute_dimension_scores(angles, profile)
    prev_angles = (prev or {}).get("angles")
    if not prev or not prev_angles:
        # 첫 분석(또는 이전 angles 미저장) — 비교 대상 없음. 코칭은 신전 부족분(IPSF 라인) 기준.
        overall = dimensions.overall_from_dimensions(abs_dims)
        assessments = kismam.assess(dimensions.extension_deviation(angles, profile))
        return assessments, abs_dims, overall, assemble.build_mode3(is_first=True)
    num_joints = len(prev.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    deviation, *_ = _deviation_against(angles, prev_angles, num_joints)
    assessments = kismam.assess(deviation)
    dim_scores = {dimensions.DIM_ANGLE: kismam.overall_score(assessments), **abs_dims}
    # 박제 (2026-06-06 belle): mode3 second+ overall = 모든 차원 평균.
    # 이전 박제 = abs_dims 만 평균 (박제 메모 [[mode3-progress-not-similarity]] 정신).
    # belle 의문: "각도 100, 안정성 93 인데 총점 93? 각도 점수 어디 가나" — 정합.
    # overall 박제 변경 = (angle + line + stability) 평균. delta 박제는 abs_dims 만
    # 유지 (절대 척도 안정 — 박제 메모 정신 유지).
    overall = dimensions.overall_from_dimensions(dim_scores)
    prev_dims = (prev.get("result") or {}).get("dimensionScores")
    comparison = assemble.build_mode3(
        is_first=False,
        previous_analysis_id=prev.get("analysisId"),
        prev_dimension_scores=prev_dims,
        cur_dimension_scores=abs_dims,  # 발전 델타는 절대 3차원만(같은 척도)
    )
    return assessments, dim_scores, overall, comparison


def _process(bucket: str, key: str, uid: str, analysis_id: str) -> None:
    _ensure_adapters()
    firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_QUEUED)

    meta = firestore_admin.get_analysis(uid, analysis_id)
    if meta is None:
        raise RuntimeError(f"분석 문서 없음 users/{uid}/analyses/{analysis_id}")
    mode = meta.get("mode")

    firestore_admin.update_analysis_status(
        uid, analysis_id, models.STATUS_FRAME_EXTRACTION
    )
    firestore_admin.update_analysis_status(
        uid, analysis_id, models.STATUS_POSE_ANALYSIS
    )

    # R3 fix (Phase 6, Plan 06-02) — 단일 helper _extract_video_analysis_inputs.
    # 기존 분기 (`_angles_from_video` vs `_angles_and_video_path_from_video`) 폐기.
    # S3 download + frame extract + RTMW estimate 단 1회만 실행.
    # Gemini ON 시 keep_local_video=True (local_video_path 반환 — caller cleanup).
    recognizer = _ensure_recognizer()
    default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    inputs = _extract_video_analysis_inputs(
        bucket, key, default_pole, keep_local_video=_gemini_enabled()
    )
    angles = inputs.angles
    student_profile = inputs.student_profile  # R4 fix — non-null
    pose_frames = inputs.pose_frames
    local_video_path_obj = inputs.local_video_path
    local_video_path = str(local_video_path_obj) if local_video_path_obj else None

    # Path A production 정합 (2026-06-05): mode=expert = motion known case
    # (사용자가 referenceMotionId 선택). recognizer.motion_query_hint 박제 →
    # Gemini extractor 가 알려진 motion 기준 key moment 추출 (default 'auto' 폴백 차단).
    # mode=self (mode3) = motion 미상 (본인 영상 비교) → hint=None (Gemini 'auto').
    #
    # WR-07 (2026-06-08 review): module-global singleton (_RECOGNIZER) 가 SQS
    # 메시지 / BackgroundTask 간 공유됨. 이전 분석이 set 한 hint 가 다음 분석에
    # leak 하면 Gemini 가 잘못된 motion 으로 biased. **항상** rebind (None 또는
    # 새 motion_id) — set/unset 분기 X.
    ref_motion_id = meta.get("referenceMotionId")
    if hasattr(recognizer, "motion_query_hint"):
        recognizer.motion_query_hint = (
            str(ref_motion_id)
            if mode == models.MODE_EXPERT and ref_motion_id
            else None
        )

    # WR-03 (2026-06-08 review) — unregistered_hook 의 uid 를 실제 caller uid 로 교체.
    # _ensure_recognizer 의 hook 은 cache 생성 시점에 uid 미상이라 "anonymous-pipeline"
    # 으로 박힘 — term_collection.unique_users 가 single-element set 으로 수렴해서
    # Phase 16 TERM-DATA-01 promotion (pending → reviewing → approved) 의 unique_users
    # 임계 결정이 불가. _process 진입 시점에 uid 가 알려져 있으므로 closure 로 rebind.
    if hasattr(recognizer, "unregistered_hook"):
        def _record_unregistered_with_uid(
            keyword: str, video_hash: str, _uid: str = uid
        ) -> None:
            firestore_admin.record_unregistered_keyword(
                keyword, uid=_uid, video_hash=video_hash
            )
        try:
            recognizer.unregistered_hook = _record_unregistered_with_uid
        except (AttributeError, TypeError):
            # frozen / Protocol-only recognizer 는 set 거절 — graceful skip.
            pass

    firestore_admin.update_analysis_status(
        uid, analysis_id, models.STATUS_COMPARISON
    )
    my_video_url = _signed_get(bucket, key)
    reference_video_url = None

    # R2 wiring — target 영상 torso px 산출 (compare_body_profiles target_torso_px arg).
    target_torso = _extract_target_torso_px(pose_frames)

    try:
        # 기술 인식(swappable) → 절대 차원(라인/안정성)은 기준 영상 없이 항상 산출.
        # Plan 5-03 박제 — recognize(angles, frames=local_video_path) 호출. Gemini
        # 어댑터는 frames 인자 (video path) 를 File API 입력으로 사용. Fallback 은
        # frames 인자 ignore (Protocol 정합 — TestProtocolCompat 박제 검증).
        profile = recognizer.recognize(angles, frames=local_video_path)
        abs_dims = dimensions.absolute_dimension_scores(angles, profile)

        # body_comparison_report — D-06-B3 통합 schema 박제 위치.
        # Task 3 가 firestore_admin.complete_analysis 에 wiring (camelCase 변환).
        body_comparison_report = None

        if mode == models.MODE_EXPERT:
            ref = firestore_admin.get_reference_motion(meta.get("referenceMotionId"))
            if ref is None or "angles" not in ref:
                raise RuntimeError("기준 모션 또는 keyframe 데이터 없음")
            # R2 wiring — reference 의 bodyNormalizationProfile + bodyComparisonSourcePose 둘 다 fetch.
            # CR-01 fix — Firestore camelCase → snake_case 변환 (_coerce_body_profile_dict).
            ref_profile_dict = ref.get("bodyNormalizationProfile")
            ref_profile = (
                BodyNormalizationProfile(**_coerce_body_profile_dict(ref_profile_dict))
                if ref_profile_dict
                else None
            )
            ref_source_pose_dict = ref.get("bodyComparisonSourcePose")
            ref_source_pose = (
                body_normalizer.BodyComparisonSourcePose(**_coerce_source_pose_dict(ref_source_pose_dict))
                if ref_source_pose_dict
                else None
            )
            source_keypoints = (
                ref_source_pose.to_keypoints_array() if ref_source_pose else None
            )
            # R2 canary — bodyNormalizationProfile 있는데 source_pose 만 None 일 때 명시적 경고.
            extra_warnings: list[str] = []
            if ref_profile_dict and not ref_source_pose:
                extra_warnings.append("reference_source_pose_missing")
            # WR-01 (2026-06-08 review) — ref_source_pose.torso_px 를 사용해서 sanity
            # 체크 log. 정규화 산식은 student-anchored (target_torso_px) 이므로 알고리즘
            # 본체에는 영향 X. ratio > 3 차이는 사용자가 다른 거리/focal 로 촬영한 경우
            # — 무효 정규화 가능성 신호. 향후 plan 에서 'source_torso_px_mismatch' warning
            # enum 도입 시 본 log → warnings.append 로 승격 가능 (3-way contract lockstep 필요).
            if ref_source_pose is not None and target_torso is not None and target_torso > 0:
                ratio = target_torso / ref_source_pose.torso_px
                if ratio > 3.0 or ratio < 1.0 / 3.0:
                    log.warning(
                        "torso_px ratio extreme uid=%s analysis_id=%s "
                        "target=%.1f ref=%.1f ratio=%.2f — student/reference 촬영 거리 불일치 가능",
                        uid, analysis_id, target_torso,
                        ref_source_pose.torso_px, ratio,
                    )
            body_comparison_report = body_normalizer.compare_body_profiles(
                pose_frames=pose_frames,
                student_profile=student_profile,
                reference_profile=ref_profile,
                comparison_type="mode1",
                source_keypoints=source_keypoints,
                angles=angles,
                technique_profile=profile,
                reference_motion_id=meta.get("referenceMotionId"),
                reference_athlete_name=(ref or {}).get("athleteName"),
                used_reference_fallback=False,
                target_torso_px=target_torso,
                extra_warnings=extra_warnings or None,
            )
            # seed 는 Firestore 의 nested-array 금지 회피로 angles 를 flat 저장.
            num_joints = len(ref.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
            deviation, match, user_seg, a_ref = _deviation_against(
                angles, ref["angles"], num_joints
            )
            assessments = kismam.assess(deviation)
            # 각도 정확도 차원 = 정은지 대비 관절각 일치도. 모드1 게이지/일치도이기도 함.
            angle_dim = kismam.overall_score(assessments)
            # 비폴 영상 차단 안전망(belle P1 #8). 기준 동작과 너무 동떨어진 자세는
            # 폴 영상이 아닐 가능성이 높아 의미 없는 점수를 결과 화면에 노출하지 않는다.
            if angle_dim < models.NOT_POLE_SIMILARITY_THRESHOLD:
                log.info(
                    "비폴 영상 추정 차단 angle=%d threshold=%d",
                    angle_dim,
                    models.NOT_POLE_SIMILARITY_THRESHOLD,
                )
                raise NotPoleMotionError(
                    f"angle {angle_dim} < {models.NOT_POLE_SIMILARITY_THRESHOLD}"
                )
            dimension_scores = {dimensions.DIM_ANGLE: angle_dim, **abs_dims}
            overall = dimensions.overall_from_dimensions(dimension_scores)  # 4차원 평균
            # 콤보 모션이면 베이스/확장 구간 부분 점수 (reference-motions.md §7).
            seg_scores = None
            if ref.get("sharedBaseMotionId"):
                base_ref = firestore_admin.get_reference_motion(
                    ref["sharedBaseMotionId"]
                )
                seg_scores = segments.segment_scores(
                    ref,
                    (base_ref or {}).get("name", ""),
                    match.path,
                    user_seg,
                    a_ref,
                )
            comparison = assemble.build_mode1(ref, angle_dim, seg_scores)
            if ref.get("videoS3Key"):
                reference_video_url = _signed_get(bucket, ref["videoS3Key"])
        else:  # MODE_SELF — 자기 성장. 절대 차원 + (이전 분석 있으면) 발전 델타.
            # 박제 (2026-06-07 belle): mode=MODE_SELF 박제 — mode1 (정은지) 분석을
            # prev 로 잡는 함정 fix. 같은 mode 안에서만 prev 검색.
            prev = firestore_admin.get_previous_analysis(
                uid, analysis_id, mode=models.MODE_SELF
            )
            assessments, dimension_scores, overall, comparison = _mode3_comparison(
                angles, prev, profile
            )

            # body_comparison_report mode3 분기 — prev 유무 → mode3_first vs mode3_progress.
            # R2 wiring + R8 fix + C2 fix (exact-match fallback by profile.motion_id).
            if not prev or not prev.get("bodyNormalizationProfile"):
                # mode3_first path — Gemini fallback 매칭 시도.
                used_fallback = False
                ref_profile_m3: BodyNormalizationProfile | None = None
                source_keypoints_m3 = None
                extra_warnings_m3: list[str] = []
                motion_id = getattr(profile, "motion_id", None)
                if motion_id is not None and student_profile.confidence >= 0.5:
                    matched = _match_reference_by_motion_id(motion_id)
                    if matched and matched.get("bodyNormalizationProfile"):
                        # CR-01 fix — Firestore camelCase → snake_case 변환.
                        ref_profile_m3 = BodyNormalizationProfile(
                            **_coerce_body_profile_dict(matched["bodyNormalizationProfile"])
                        )
                        matched_source_pose_dict = matched.get("bodyComparisonSourcePose")
                        matched_source_pose = (
                            body_normalizer.BodyComparisonSourcePose(
                                **_coerce_source_pose_dict(matched_source_pose_dict)
                            )
                            if matched_source_pose_dict
                            else None
                        )
                        source_keypoints_m3 = (
                            matched_source_pose.to_keypoints_array()
                            if matched_source_pose
                            else None
                        )
                        if not matched_source_pose:
                            extra_warnings_m3.append("reference_source_pose_missing")
                        used_fallback = True
                    elif matched is None:
                        # R8 fix — caller-injected warning (dataclasses.replace 우회 금지).
                        extra_warnings_m3.append("fallback_reference_not_found")
                body_comparison_report = body_normalizer.compare_body_profiles(
                    pose_frames=pose_frames,
                    student_profile=student_profile,
                    reference_profile=ref_profile_m3,
                    comparison_type="mode3_first",
                    source_keypoints=source_keypoints_m3,
                    angles=angles,
                    technique_profile=profile,
                    used_reference_fallback=used_fallback,
                    target_torso_px=target_torso,
                    extra_warnings=extra_warnings_m3 or None,
                )
            else:
                # mode3_progress path — prev.bodyNormalizationProfile 정합.
                # CR-02 fix — get_previous_analysis 가 반환하는 Firestore doc 의
                # bodyNormalizationProfile 은 production 에서 항상 camelCase
                # (complete_analysis 가 _dataclass_to_camel_case_dict 로 저장).
                # snake_case 도 수용 — 테스트 fixture 정합.
                prev_profile = BodyNormalizationProfile(
                    **_coerce_body_profile_dict(prev["bodyNormalizationProfile"])
                )
                prev_source_pose_raw = prev.get("bodyComparisonSourcePose")
                prev_source_pose = (
                    body_normalizer.BodyComparisonSourcePose(
                        **_coerce_source_pose_dict(prev_source_pose_raw)
                    )
                    if prev_source_pose_raw
                    else None
                )
                prev_source_keypoints = (
                    prev_source_pose.to_keypoints_array() if prev_source_pose else None
                )
                prev_extra_warnings = (
                    ["reference_source_pose_missing"]
                    if (prev_profile and not prev_source_pose)
                    else None
                )
                body_comparison_report = body_normalizer.compare_body_profiles(
                    pose_frames=pose_frames,
                    student_profile=student_profile,
                    reference_profile=prev_profile,
                    comparison_type="mode3_progress",
                    source_keypoints=prev_source_keypoints,
                    angles=angles,
                    technique_profile=profile,
                    previous_analysis_id=prev.get("analysisId"),
                    used_reference_fallback=False,
                    target_torso_px=target_torso,
                    extra_warnings=prev_extra_warnings,
                )

        coach_details = _COACH_WRITER.write(
            {
                "mode": mode,
                "joints": [
                    {
                        "key": a.key,
                        "labelKo": a.label_ko,
                        "deviation_deg": a.deviation_deg,
                        "direction": a.direction,
                    }
                    for a in kismam.top_issues(assessments, n=3)
                ],
            }
        )
        result = assemble.build_result(
            assessments,
            dimension_scores,
            overall,
            comparison,
            my_video_url,
            reference_video_url=reference_video_url,
            coach_details=coach_details,
            my_video_key=key,  # 박제 (2026-06-06): GET /playback-url 재발급용
            # Phase 12.5 (2026-06-07): dimensionExplanation source 박제 박제
            # — line/stability deficit 가 점수 산식 (line_score/stability_score) 과 동일
            # _select_window + dimensions helpers 사용 (Codex v3 HIGH-2 정합).
            joint_angles=angles,
            profile=profile,
        )
        # 추출 angles 를 flat 저장 — 다음 mode3 분석이 '이전 영상' 기준으로 DTW 비교.
        # Phase 6 (Plan 06-02 Task 3) wiring — body_comparison_report (camelCase 변환) +
        # body_normalization_profile (mode3 progress prev fetch path).
        body_comparison_report_dict = _dataclass_to_camel_case_dict(
            body_comparison_report
        ) if body_comparison_report is not None else None
        body_normalization_profile_dict = _dataclass_to_camel_case_dict(
            student_profile
        ) if student_profile is not None else None

        # Phase 8 (Plan 08-03) — force signals 산출.
        #   REVIEWS R5 정합: angles 는 _extract_video_analysis_inputs 가 1회 temporal_fill
        #     적용 (double smoothing 차단).
        #   REVIEWS R6 정합: technique_profile 는 compare_body_profiles 호출 시점에 이미 박제됨
        #     (recognizer reuse — 신규 GeminiMomentExtractor singleton 영구 차단).
        #   REVIEWS R7 정합: FORCE_SIGNALS_LAYER2_ENABLED env flag check (Phase 5 와 분리).
        #   REVIEWS R10 정합: pole_axis_measurement coordinate_space='unavailable' 박제
        #     vertical fallback (Phase 8 의 axis distance None 분기 자동 활성).
        #   REVIEWS Cycle 2 NEW HIGH #1 차단: preflight_label_gate_passed 는 env 박제
        #     helper 활용 — belle 가 Lambda env / RunPod Pod env 박제만으로 gate flip
        #     (코드 변경 0).
        layer2_recognizer = _get_force_signals_layer2_recognizer()
        force_signals_report = fs.compute_force_signals(
            inputs.pose_frames,
            inputs.pole_axis_measurement,  # REVIEWS R10
            student_profile,
            angles=angles,  # _extract_video_analysis_inputs 가 temporal_fill 적용 (REVIEWS R5)
            fps=9.0,
            motion_id=getattr(profile, "motion_id", None),
            preflight_label_gate_passed=_preflight_label_gate_passed(),  # Cycle 2 NEW HIGH #1
            technique_profile=profile if layer2_recognizer is not None else None,  # REVIEWS R6
        )
        force_signals_dict = _dataclass_to_camel_case_dict(force_signals_report)

        firestore_admin.complete_analysis(
            uid,
            analysis_id,
            result,
            angles=np.asarray(angles, dtype=float).reshape(-1).tolist(),
            angles_joint_keys=list(skeleton.JOINT_KEYS),
            angles_frames=int(np.asarray(angles).shape[0]),
            body_comparison_report=body_comparison_report_dict,
            body_normalization_profile=body_normalization_profile_dict,
            force_signals_report=force_signals_dict,
        )
        log.info("분석 완료 uid=%s analysis_id=%s mode=%s", uid, analysis_id, mode)
    finally:
        # Plan 5-03 박제 — Gemini 어댑터 path 에서 신설한 임시 파일 정리.
        # delete=False NamedTemporaryFile 박제 정신 정합 — caller 책임 (B8 fix).
        # T-05-03-02 (DoS — 디스크 누수) 박제 — try/finally + missing_ok=True.
        if local_video_path is not None:
            Path(local_video_path).unlink(missing_ok=True)


def lambda_handler(event: dict, _context) -> dict:
    """SQS 이벤트 → 메시지마다 RunPod 위임 또는 직접 처리.

    RunPod 위임 분기: _runpod_enabled() True 시 status=queued 로 일단 표시하고
    HTTP POST. Pod 가 202 를 반환하면 그 이후 status 갱신은 RunPod 서버가 책임.
    위임 호출 자체가 실패하면(타임아웃·5xx) ERR_SERVER_ERROR 로 매핑.
    """
    processed = 0
    delegated = _runpod_enabled()
    if delegated:
        log.info("RunPod 위임 모드 ON url=%s", _RUNPOD_URL)
    for bucket, key in iter_s3_keys_from_sqs(event):
        parsed = parse_upload_key(key)
        if parsed is None:
            log.warning("스킵: 인식 불가 S3 키 %s", key)
            continue
        uid, analysis_id = parsed.uid, parsed.analysis_id
        try:
            if delegated:
                # 위임 시 Lambda 는 queued 까지만 갱신. 그 이후 단계는 RunPod 책임.
                firestore_admin.update_analysis_status(
                    uid, analysis_id, models.STATUS_QUEUED
                )
                _delegate_to_runpod(bucket, key)
            else:
                _process(bucket, key, uid, analysis_id)
            processed += 1
        except NoHumanError:
            log.info("인체 미감지 uid=%s analysis_id=%s", uid, analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_NO_HUMAN,
                models.ERROR_MESSAGE[models.ERR_NO_HUMAN],
            )
        except NotPoleMotionError:
            log.info("비폴 영상 차단 uid=%s analysis_id=%s", uid, analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_NOT_POLE_MOTION,
                models.ERROR_MESSAGE[models.ERR_NOT_POLE_MOTION],
            )
        except Exception:  # noqa: BLE001
            log.exception("분석 실패 analysis_id=%s", analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_SERVER_ERROR,
                models.ERROR_MESSAGE[models.ERR_SERVER_ERROR],
            )
    return {"processed": processed}
