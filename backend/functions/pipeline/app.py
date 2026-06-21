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
from sunity_shared.analysis import exercise_map  # Phase 13 (Plan 13-A, PERS-03)
from sunity_shared.analysis.coach_hook_builder import (  # Phase 11 (Plan 11-01)
    resolve_coach_hook_bundle,
)
from sunity_shared.analysis import force_pattern as fp
from sunity_shared.analysis import force_signals as fs
from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.body_normalization_measurer import measure_body_profile
# Phase 12 Wave 0B (Plan 12-01, 2026-06-10) — KeypointReport build wiring.
from sunity_shared.analysis.assemble import build_keypoint_report
from sunity_shared.analysis.keypoint_frame import KeypointReport, upsample_to_fps
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
# sunity_shared.gemini 박제 — Lambda 250MB 한도 정합 박제 (lazy import).
# 운영 path = RunPod 위임 (RUNPOD_ANALYZE_URL 박힘) — Lambda 의 _process CPU
# 폴백 path 에서만 Gemini Vision 호출. lazy import 로 google-genai 의 ~100MB
# transitive deps (googleapiclient 등) 를 Lambda 배포에서 제거 + Pod 에는 영향 0
# (Pod 의 runpod_inference/requirements.txt 박힘 유지).
# 박제 후속 사용 위치 안에서 `from sunity_shared.gemini.* import ...` 박는다.
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
# Plan 08-04 (B fix, 2026-06-09) — HoughPoleDetector singleton 박제. lazy init
# _ensure_adapters() 안. detect_with_line() 호출로 PoleLine2D 박제 → Phase 8
# axisMetrics 실효성.
_POLE_DETECTOR = None  # type: ignore[var-annotated]

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


# Phase 17 4 영역 토글 박제 — Plan 17-01 Task 4 (R-B4 정합).
# B/C 는 default "1" — Plan 03 (coach) / 04 (finding) 의 default ON 박제.
# A/D 는 default unset = False — Plan 02 (reference 등록) / 05 (keypoint refinement)
# 의 default OFF 박제 (운영자 명시 opt-in).
_VISION_ENV_DEFAULTS: tuple[tuple[str, str], ...] = (
    ("GEMINI_REFERENCE_ENABLED", ""),  # 영역 A — default OFF
    ("GEMINI_COACH_ENABLED", "1"),  # 영역 B — default ON
    ("GEMINI_FINDING_ENABLED", "1"),  # 영역 C — default ON
    ("GEMINI_D_ENABLED", ""),  # 영역 D — default OFF
)

# falsy 박제 값 — "0" / "false" / "False" / "" 모두 OFF. 그 외는 ON (Phase 5 helper 와 분리 박제).
_VISION_FALSY = frozenset({"0", "false", ""})


def _gemini_vision_enabled() -> bool:
    """Phase 17 4 영역 (A/B/C/D) Gemini Vision 토글 중 하나라도 ON 인지 박제.

    박제 정신 (Plan 17-01 R-B4):
      · 4 토글 중 하나라도 truthy 면 True — keep_local_video=True 게이트.
      · 기존 `_gemini_enabled()` 시그니처/동작 변경 0 — backward compat.
      · B/C default "1" 박제 (Plan 03/04 default ON). A/D 미설정 = False (default OFF).
      · falsy 박제 = {"0", "false", "False", ""} — case-insensitive lower 비교.
        그 외 (예: "1", "true", "yes", "on") 는 ON.

    Returns:
        True = 4 영역 중 ≥1 ON. False = 모두 OFF.
    """
    for env_var, default_val in _VISION_ENV_DEFAULTS:
        raw = os.environ.get(env_var, default_val)
        if raw.strip().lower() not in _VISION_FALSY:
            return True
    return False


# Phase 20-03 (SCORE-08, iter2 MEDIUM-1) — Gemini 비전 거부권 토글.
# 토글은 **pipeline(app.py) 단독 소유** — 20-02 어댑터(gemini_vision_scorer)는 토글을
# 정의/복제하지 않는다(drift → no-op 버그 재발 차단). _apply_vision_veto 가 유일한
# feature-toggle 게이트이며, keep_local_video 보존 게이트(HIGH-1)도 이 토글을 읽는다.
# default OFF (env 미설정 = False) — belle 운영자 명시 opt-in (20-RESEARCH Runtime State).
def _gemini_vision_veto_enabled() -> bool:
    """GEMINI_VISION_VETO_ENABLED 토글 (Phase 20-03, pipeline 단독 소유).

    박제 정신:
      · iter2 MEDIUM-1 — 토글은 pipeline 에만 정의/사용. 어댑터 복제 금지(drift 방지).
      · falsy 박제 = {"0", "false", ""} (case-insensitive). 그 외 truthy 면 ON.
      · default OFF — env 미설정 = False (운영자 명시 opt-in).

    Returns:
        True = 비전 거부권 ON. False = OFF.
    """
    raw = os.environ.get("GEMINI_VISION_VETO_ENABLED", "")
    return raw.strip().lower() not in _VISION_FALSY


def _safe_unlink_local_video(local_video_path: str | None) -> None:
    """local_video_path 안전 unlink — 실패 시 log.warning + graceful return.

    박제 정신 (Plan 17-01 Task 4 — 2차 R-W6 정합):
      · B/C default ON 으로 모든 분석에서 keep_local_video=True 가 될 수 있음 →
        finally 박제 unlink 가 disk budget (Lambda /tmp 512MB / Pod tmpfs) 누수 차단.
      · `Path.unlink(missing_ok=True)` 는 FileNotFoundError 만 흡수 — PermissionError /
        OSError 는 raise. 본 wrapper 가 모든 예외를 흡수 (graceful) 하여 분석 흐름 차단 0.
      · 실패 시 log.warning 1회 — 운영자 가시성 박제.
    """
    if local_video_path is None:
        return
    try:
        Path(local_video_path).unlink(missing_ok=True)
    except (OSError, PermissionError) as exc:  # noqa: BLE001 - 차단 0 박제
        log.warning(
            "local_video_path unlink 실패 — graceful skip path=%s err=%s",
            local_video_path,
            exc,
        )


# ── Plan 17-02 Wave 1 — 영역 C Finding 장면 인식 wiring ─────────────────────
#
# 박제 정신 (3차 R-W3):
#   · `_process(bucket, key, uid, analysis_id)` 시그너처 변경 0 — caller (RunPod
#     server.py / Lambda SQS) 갱신 0.
#   · `_resolve_is_reference` 가 S3 key prefix 1차 + Firestore mode 2차 박제로
#     is_reference 산출 — 단일 source 신뢰 X (T-17-09 spoofing 정합).
#   · `_call_wave1_scene_finder` 가 wave 1 진입점:
#       - GEMINI_FINDING_ENABLED=0 / local_video_path=None → skip + None 반환.
#       - find_scene_flags 호출 후 결과 dict 반환 (G4 가드는 find_scene_flags 안에서).
#       - 예외 흡수 — graceful None (분석 흐름 차단 0).
#   · find_scene_flags 안에서 S3 재다운로드 / RTMW 재실행 0 (B4 hard gate). caller
#     의 `local_video_path` (Phase 6 `_extract_video_analysis_inputs` 가 1회만
#     download + RTMW 1회만 실행) 만 사용.


# `mode1_register` 은 정은지 영상 등록 모드 (영역 A 후속 plan 박제). models.MODE_*
# 에 아직 박제 X — 본 모듈 상수로 로컬 박제 (후속 plan 에서 models.MODE_REGISTER
# 박제 시 단일 source 로 마이그레이션).
_MODE_REFERENCE_REGISTER: str = "mode1_register"

# S3 key prefix 박제 — 정은지 reference 영상 업로드 위치.
_REFERENCE_KEY_PREFIX: str = "reference/"


def _resolve_is_reference(key: str, meta: dict | None) -> bool:
    """is_reference 박제 — S3 key prefix 1차 + Firestore analysis doc mode 2차.

    박제 정신 (Plan 17-02 R-W3 정합):
      · S3 key 가 `reference/` 로 시작 → True (Firestore 조회 0, 1차 source).
      · 그 외엔 Firestore analysis doc `mode == 'mode1_register'` → True (2차).
      · 단일 source 신뢰 X — T-17-09 spoofing 정합. 일반 사용자 영상이 reference
        분기로 박혀 G4 가드 우회되는 risk 차단.

    Args:
      key: S3 object key (이미 caller 가 `parse_upload_key` 통과).
      meta: `firestore_admin.get_analysis(uid, analysis_id)` 결과 dict 또는 None.

    Returns:
      True = reference 영상 (G4 가드 활성). False = 일반 사용자 영상.
    """
    if key.startswith(_REFERENCE_KEY_PREFIX):
        return True
    if meta is not None and meta.get("mode") == _MODE_REFERENCE_REGISTER:
        return True
    return False


def _finding_enabled() -> bool:
    """GEMINI_FINDING_ENABLED env 박제 — wave 1 영역 C 토글.

    Plan 17-01 R-B4 정합 — `_VISION_ENV_DEFAULTS` 와 동일 박제 (default '1' = ON,
    `_VISION_FALSY` = {"0", "false", ""} 박제 OFF). `_gemini_vision_enabled()` 의
    OR-gate 와 일관성 박제.
    """
    raw = os.environ.get("GEMINI_FINDING_ENABLED", "1")
    return raw.strip().lower() not in _VISION_FALSY


def _call_wave1_scene_finder(
    local_video_path: str | None,
    is_reference: bool,
) -> dict | None:
    """Wave 1 영역 C Finding 호출 진입점 — graceful 폴백 + skip 조건 박제.

    Skip 조건 (return None):
      · `GEMINI_FINDING_ENABLED` env = "0"/"false"/"" → 운영자 박제 차단 path.
      · `local_video_path` = None → caller 가 keep_local_video=False 박혔거나 (
        Phase 17 4 영역 모두 OFF) 임시 path 박혀있지 않음.
      · find_scene_flags 예외 (객관성 가드 ValueError 등) → 흡수 + None.

    Returns:
      find_scene_flags 결과 dict 또는 None (skip / 폴백).
    """
    if local_video_path is None:
        return None
    if not _finding_enabled():
        log.info("GEMINI_FINDING_ENABLED OFF — wave 1 skip")
        return None
    try:
        # Lazy import — Lambda 250MB 정합 (top-level import 시 google-genai 박힘).
        from sunity_shared.gemini.scene_finder import find_scene_flags

        return find_scene_flags(local_video_path, is_reference=is_reference)
    except Exception as exc:  # noqa: BLE001 - 분석 흐름 차단 0 박제
        log.warning(
            "find_scene_flags raise — graceful skip (is_reference=%s): %s",
            is_reference,
            exc,
        )
        return None


# ── Plan 17-03 Wave 2 — 영역 D Keypoint 보강 wiring ─────────────────────────
#
# 박제 정신 (B2 hard gate + 3차 R-B3):
#   · `_d_enabled()` — GEMINI_D_ENABLED env truthy (default OFF, AI-SPEC §4 "Pod
#     RTMW failure path 만 호출, 빈도 낮음" 정합).
#   · `_call_wave2_keypoint_augmenter` 가 wave 2 진입점:
#       - occlusion_severe=True (wave 1 결과) → skip + None (게이트 1).
#       - GEMINI_D_ENABLED=0 → skip + None (게이트 2).
#       - local_video_path=None → skip + None (B4 hard gate).
#       - low_uncertainty_frame_indices 빈 → skip + None (Gemini 호출 0).
#       - augment_low_confidence 예외 흡수 — graceful None.
#   · **3D coco_array 행렬은 본 wave 입력/출력 모두 격리** (B2 hard gate).
#     augment_low_confidence 시그너처에 coco_array 인자 영구 박제 X. user-visible
#     KeypointReport.data + confidence 만 보강.


def _d_enabled() -> bool:
    """GEMINI_D_ENABLED env 박제 — wave 2 영역 D 토글 (default OFF).

    Plan 17-01 R-B4 정합 — _VISION_ENV_DEFAULTS 와 동일 박제 (default "" = OFF,
    `_VISION_FALSY` = {"0", "false", ""} 박제 OFF). 운영자 박제 opt-in.
    """
    raw = os.environ.get("GEMINI_D_ENABLED", "")
    return raw.strip().lower() not in _VISION_FALSY


def _call_wave2_keypoint_augmenter(
    local_video_path: str | None,
    low_uncertainty_frame_indices: list[int],
    keypoint_report_2d,
    scene_result: dict | None,
) -> dict | None:
    """Wave 2 영역 D Keypoint 보강 호출 진입점 — graceful 폴백 + skip 조건 박제.

    Skip 조건 (return None):
      · `scene_result["occlusion_severe"]==True` → 가려진 frame 에 좌표 보강 의미 0
        (AI-SPEC §4b async pattern).
      · `GEMINI_D_ENABLED` env = "0"/"false"/"" → 운영자 박제 차단 path (default OFF).
      · `local_video_path` = None → B4 hard gate (S3 재다운로드 X).
      · `keypoint_report_2d` is None → 보강할 KeypointReport 없음.
      · augment_low_confidence 예외 (객관성 가드 ValueError 등) → 흡수 + None.

    빈 low_uncertainty_frame_indices 는 augment_low_confidence 내부에서 graceful
    빈 dict 반환 — 본 helper 가 그대로 전달.

    Returns:
      augment_low_confidence 결과 dict 또는 None (skip / 폴백).
    """
    if local_video_path is None:
        return None
    if not _d_enabled():
        log.info("GEMINI_D_ENABLED OFF — wave 2 skip")
        return None
    if keypoint_report_2d is None:
        return None
    # 게이트 1 — occlusion_severe=True → 가려진 frame 보강 의미 X.
    if scene_result is not None and bool(scene_result.get("occlusion_severe")):
        log.info("occlusion_severe=True — wave 2 skip (영역 D)")
        return None
    try:
        # Lazy import — Lambda 250MB 정합.
        from sunity_shared.gemini.keypoint_augmenter import augment_low_confidence

        return augment_low_confidence(
            video_path=local_video_path,
            low_uncertainty_frame_indices=low_uncertainty_frame_indices,
            keypoint_report_2d=keypoint_report_2d,
        )
    except Exception as exc:  # noqa: BLE001 - 분석 흐름 차단 0 박제
        log.warning(
            "augment_low_confidence raise — graceful skip: %s", exc
        )
        return None


def _low_uncertainty_frame_indices(keypoints_4ch) -> list[int]:
    """3차 R-B3 정합 — `coco_array[:, :, 3].max(axis=1) > 0.5` 인 frame index 산출.

    keypoints_4ch shape (T, 17, 4). 4번째 채널 = uncertainty_proxy
    (pose_frame.py:325-353, 1.0 = 미감지). 본 frame 의 17개 keypoint 중 어떤 하나라도
    uncertainty_proxy > 0.5 면 보강 대상 (max(axis=1) > 0.5). `min < 0.5` 박제 금지
    (의미 정반대 — 이전 plan 박제 오해 정정).
    """
    if keypoints_4ch is None:
        return []
    arr = np.asarray(keypoints_4ch)
    if arr.ndim != 3 or arr.shape[-1] != 4:
        return []
    max_uncertainty = arr[:, :, 3].max(axis=1)
    return [int(i) for i, u in enumerate(max_uncertainty) if float(u) > 0.5]


def _apply_keypoint_refinement_to_report(
    keypoint_report,
    augment_result: dict,
):
    """augment_low_confidence 결과 dict 의 refined 좌표를 KeypointReport 에 박제.

    박제 정신 (B2 정합):
      · KeypointReport.data / confidence / reliability / warnings 만 보강 — 3D
        scoring 행렬 (coco_array) mutate 0.
      · dataclasses.replace — frozen dataclass 정합.
      · refined entry 의 joint_key 가 KeypointReport.joints 에 없으면 skip
        (예: elbow — audit only, KeypointReport 에 elbow 없음).
      · warnings 에 "gemini_d_augmented" 추가.

    Args:
      keypoint_report: KeypointReport instance (frozen dataclass).
      augment_result: augment_low_confidence 결과 dict.

    Returns:
      보강된 새 KeypointReport instance (원본은 변경 X).
    """
    refined: list[dict] = augment_result.get("refined", [])
    if not refined:
        # 보강 0 — 원본 그대로.
        return keypoint_report

    joints = list(keypoint_report.joints)
    J = len(joints)
    # Plan 17-03 박제 schema joint_key → KeypointReport joint name 매핑 박제.
    # schema 는 elbow/shoulder/hip/knee, KeypointReport 는 shoulder/hip/knee/hand.
    # elbow 는 KeypointReport 에 없어서 skip (audit only).
    schema_to_report: dict[str, str | None] = {
        "left_elbow": None,
        "right_elbow": None,
        "left_shoulder": "left_shoulder",
        "right_shoulder": "right_shoulder",
        "left_hip": "left_hip",
        "right_hip": "right_hip",
        "left_knee": "left_knee",
        "right_knee": "right_knee",
    }

    new_data = list(keypoint_report.data)
    new_confidence = list(keypoint_report.confidence)
    augmented_frames_set: set[int] = set()

    for entry in refined:
        f_idx = int(entry["frame_index"])
        schema_joint = str(entry["joint_key"])
        report_joint = schema_to_report.get(schema_joint)
        if report_joint is None or report_joint not in joints:
            continue
        joint_idx = joints.index(report_joint)
        if f_idx < 0 or f_idx >= keypoint_report.frames:
            continue
        data_base = (f_idx * J + joint_idx) * 2
        conf_idx = f_idx * J + joint_idx
        if data_base + 1 >= len(new_data) or conf_idx >= len(new_confidence):
            continue
        new_data[data_base] = float(entry["x_normalized"])
        new_data[data_base + 1] = float(entry["y_normalized"])
        new_confidence[conf_idx] = float(entry["confidence"])
        augmented_frames_set.add(f_idx)

    # reliability — 보강된 frame 은 적어도 "medium" 으로 승급 (R6 정합 — Gemini conf
    # 가 RTMW 저신뢰 frame 보다 신뢰도 ↑). 단순화: 보강 frame = "medium" 으로 박제.
    new_reliability = list(keypoint_report.reliability)
    for f_idx in augmented_frames_set:
        if f_idx < len(new_reliability):
            # 기존 "high" 은 유지, "low" / "medium" 은 "medium" 으로 박제.
            if new_reliability[f_idx] != "high":
                new_reliability[f_idx] = "medium"

    new_warnings = list(keypoint_report.warnings)
    if "gemini_d_augmented" not in new_warnings:
        new_warnings.append("gemini_d_augmented")

    return dataclasses.replace(
        keypoint_report,
        data=new_data,
        confidence=new_confidence,
        reliability=new_reliability,
        warnings=new_warnings,
    )


# ── Plan 04-01 Wave 1 (Phase 4) — Occlusion 합성 어댑터 wiring ──────────────
#
# 박제 정신 (POSE-03 D-07 / D-08 / R1 / R2 / R6):
#   · _call_synthesis_adapter 진입점:
#       - is_reference=True → G4 가드 (최우선) → SynthesisResult(status="skipped",
#         warnings=("g4_reference_guard",)). adapter 호출 0.
#       - SYNTHESIS_ENABLED env OFF (default) → SynthesisResult(status="skipped").
#       - 그 외 모든 except → SynthesisResult(status="failed",
#         warnings=("ai_synthesis_failed",)) — graceful degrade.
#   · R1 non-scoring 하드월: 본 wrapper 가 반환한 SynthesisResult 는 pipeline 의
#     KeypointReport / aiSynthesisMeta / joints3d 흐름에만 흘러간다. DTW/kismam/
#     IPSF coco_array 에 절대 mutate 0 (B2 hard gate 정합).
#   · _get_synthesis_adapter() — module-level lazy singleton. 첫 호출 시
#     GeminiViewReasoner 인스턴스 박제.
#   · warning surface (BLOCKER-3 canonical) — warning 은 `ai_synthesis_meta["warnings"]`
#     리스트로 흘러가야 함. `profile.extra_warnings` 같은 경로 영구 금지 (warning
#     surface 단일화). pipeline 의 _process 가 ai_synthesis_meta dict 를 조립해
#     complete_analysis 의 ai_synthesis_meta= kwarg 로 주입한다.


_SYNTHESIS_FALSY: frozenset[str] = frozenset({"0", "false", ""})
_SYNTHESIS_ADAPTER = None  # module-level lazy singleton


def _synthesis_enabled() -> bool:
    """SYNTHESIS_ENABLED env 박제 — Phase 4 wave 1 합성 토글 (default OFF, D-07).

    운영 안전 스위치 — Wave 1 wiring 박제 후에도 default OFF 로 두어 시연/배포 시
    명시적 ON 박제. `_VISION_FALSY` 와 동일한 falsy set ({"0", "false", ""}) 사용.
    """
    raw = os.environ.get("SYNTHESIS_ENABLED", "0")
    return raw.strip().lower() not in _SYNTHESIS_FALSY


def _get_synthesis_adapter():
    """Lazy singleton — GeminiViewReasoner (Stage 1 PRIMARY, D-18).

    Wave 3 (04-03) 이후 CylindricalMeshAdapter 추가 시 본 helper 에서 chain 분기 박제.
    현 단계는 PRIMARY 만.
    """
    global _SYNTHESIS_ADAPTER
    if _SYNTHESIS_ADAPTER is None:
        # Lazy import — Lambda 250MB 정합 + Wave 1 신설 패키지 path 박제.
        from sunity_shared.analysis.synthesis.gemini_view_reasoner import (
            GeminiViewReasoner,
        )

        _SYNTHESIS_ADAPTER = GeminiViewReasoner()
    return _SYNTHESIS_ADAPTER


def _call_synthesis_adapter(
    *,
    adapter,
    joint_sequence,
    confidence_sequence,
    occlusion_mask,
    scene_findings: dict | None,
    is_reference: bool = False,
):
    """Phase 4 — SynthesisResult 기반 조건부 합성 (D-03/D-07 R2 fix).

    G4 가드 (최우선): is_reference=True → SynthesisResult(status='skipped',
    warnings=('g4_reference_guard',)). adapter.synthesize_occluded_joints 자체 호출 0.

    합성 output 은 KeypointReport / aiSynthesisMeta / joints3d 에만 흘러간다 —
    DTW/kismam/IPSF coco_array 에 절대 mutate 금지 (R1 non-scoring 하드월,
    [[gap-and-line-angle-mandatory-gates]] 정합 — Wave 3 진입 1순위인 line/angle
    게이트는 본 합성 path 와 무관, 채점은 1차 RTMW 원본만).

    Args:
      adapter: SynthesisAdapter Protocol 구현체 (GeminiViewReasoner 등).
      joint_sequence: (T, 17, 3) 1차 RTMW joints.
      confidence_sequence: (T, 17) keypoint confidence.
      occlusion_mask: (T, 17) bool — 합성 대상 영역.
      scene_findings: scene_finder.find_scene_flags 결과 dict (또는 None).
      is_reference: 정은지 reference 영상 여부 (G4 가드 trigger).

    Returns:
      SynthesisResult dataclass. None 반환 영구 금지 (R2 fix).
    """
    # Lazy import — Wave 1 신설 패키지.
    from sunity_shared.analysis.synthesis.interfaces import SynthesisResult

    # G4 가드 — 최우선. test_synthesis_g4_guard 회귀 게이트.
    if is_reference:
        log.info("synthesis — is_reference=True G4 guard skip")
        return SynthesisResult(
            status="skipped",
            warnings=("g4_reference_guard",),
        )

    # SYNTHESIS_ENABLED env 게이트는 caller (_process) 측에서 처리한다.
    # 본 wrapper 는 G4 가드 + graceful degrade 만 책임 — adapter 가 명시적으로
    # 전달되면 항상 호출 시도 (test_synthesis_adapter 회귀 게이트 정합).

    # adapter 호출 — 모든 예외 graceful degrade (R2 fix).
    try:
        return adapter.synthesize_occluded_joints(
            joint_sequence,
            confidence_sequence,
            occlusion_mask,
            scene_findings or {},
        )
    except Exception:  # noqa: BLE001 - 분석 흐름 차단 0 + graceful degrade
        log.exception("synthesis adapter raise — graceful degrade")
        return SynthesisResult(
            status="failed",
            warnings=("ai_synthesis_failed",),
        )


def _build_ai_synthesis_meta(synth_result, *, synthesis_path: str) -> dict:
    """SynthesisResult → aiSynthesisMeta dict (warnings 분류 + cost 카운터 통합).

    public warning ('ai_synthesis_failed' / 'ai_synthesis_partial') 만 warnings 에,
    raw reason ('gemini_api_error' / 'g4_reference_guard' / 'exception' 등) 은
    debugWarnings 에 분리 보존 (HIGH-4 — public enum 오염 금지).

    promotion 은 별도 후속 phase — 본 Wave 1 박제는 audit 메타 저장만.
    """
    raw_warnings = list(getattr(synth_result, "warnings", ()) or ())
    public_codes = set(getattr(models, "SYNTHESIS_WARNING_CODES", frozenset()))

    # status 기반 public warning 매핑 — adapter 의 raw warning 과 별개.
    public_warnings: list[str] = []
    debug_warnings: list[str] = []
    if synth_result.status == "failed":
        if "ai_synthesis_failed" not in public_warnings:
            public_warnings.append("ai_synthesis_failed")
    elif synth_result.status == "partial":
        if "ai_synthesis_partial" not in public_warnings:
            public_warnings.append("ai_synthesis_partial")
    for w in raw_warnings:
        if w in public_codes:
            if w not in public_warnings:
                public_warnings.append(w)
        else:
            if w not in debug_warnings:
                debug_warnings.append(w)

    meta = dict(getattr(synth_result, "meta", {}) or {})
    # 기본 cost 카운터 (adapter 가 채우지 않은 경우 0 박제).
    out: dict = {
        "synthesizedFrameCount": int(meta.get("framesSynthesized", 0)),
        "synthesizedJointKeys": list(meta.get("synthesizedJointKeys", []) or []),
        "synthesisPath": synthesis_path,
        "degraded": synth_result.status in ("failed", "skipped"),
        "modelId": str(meta.get("modelId", "")),
        "modelVersion": str(meta.get("modelVersion", "")),
        "promptHash": str(meta.get("promptHash", "")),
        "framesConsidered": int(meta.get("framesConsidered", 0)),
        "framesSynthesized": int(meta.get("framesSynthesized", 0)),
        "geminiCalls": int(meta.get("geminiCalls", 0)),
        "framesSkipped": int(meta.get("framesSkipped", 0)),
        "framesFailed": int(meta.get("framesFailed", 0)),
        "estCostUsd": float(meta.get("estCostUsd", 0.0)),
        "warnings": public_warnings,
        "debugWarnings": debug_warnings,
    }
    return out


# ── Plan 17-04 Wave 3 — 영역 B 코칭 멘트 dual-track wiring ──────────────────
#
# 박제 정신 (3차 R-B1 Option A + R-B2 + R-W4):
#   · 기존 Cerebras coach writer 호출부 (`_process` 의 `_COACH_WRITER.write(...)`)
#     를 dual-track 으로 감싸 GEMINI_COACH_ENABLED=1 (default) 시 GeminiCoachWriter
#     우선, fallback dict (`{}` 또는 `{"_fallbackReason": ...}`) 시 Cerebras 폴백.
#   · 3차 R-B1 (Option A) — wave 1 (`find_scene_flags`) 가 먼저 await 종료 후 B 호출.
#     `_process` 본체 박제 순서로 자연 박힘 (wave 1 = line 1238, wave 3 B = line ~1494).
#   · 3차 R-B2 — B 삽입 위치는 기존 Cerebras coach writer 호출부 (`assemble.build_result`
#     직전). Plan 03 D 는 build_keypoint_report 직후 박혀 B 보다 늦음 → v1 에서 B 가 D
#     결과 받을 수 없음 (geminiD context 박제 X — v2 후속 plan).
#   · 2차 R-W4 — None 반환 박제 0. dual-track 분기 = `_fallbackReason` 키 또는 빈 dict
#     여부로 결정. 양쪽 writer 가 단일 `_build_coach_context` 결과 dict 공유 (B3 정합).
#   · B4 hard gate — caller (`_process`) 가 keep_local_video=True 박제 후 local_video_path
#     만 전달. Gemini writer 안에서 S3 재다운로드 / RTMW 재실행 0.


def _coach_enabled() -> bool:
    """GEMINI_COACH_ENABLED env 박제 — wave 3 영역 B 토글 (default ON).

    Plan 17-01 R-B4 정합 — `_VISION_ENV_DEFAULTS` 와 동일 박제 (default "1" = ON,
    `_VISION_FALSY` = {"0", "false", ""} 박제 OFF).
    """
    raw = os.environ.get("GEMINI_COACH_ENABLED", "1")
    return raw.strip().lower() not in _VISION_FALSY


# Gemini Coach writer 인스턴스 — RunPod / Lambda 콜드스타트 1회 박제.
_GEMINI_COACH_WRITER = None  # type: ignore[var-annotated]


def _ensure_gemini_coach_writer() -> "GeminiCoachWriter":
    """GeminiCoachWriter singleton lazy init.

    `_COACH_WRITER` (Cerebras) 와 별도 — Gemini 는 _ensure_adapters 외부에서 박제.
    (Gemini import 가 boto3 / SSM 의존성 부담 적음 — 항상 lazy 박제 가능.)
    """
    global _GEMINI_COACH_WRITER
    if _GEMINI_COACH_WRITER is None:
        # Lazy import — Lambda 250MB 정합.
        from sunity_shared.gemini.coach_writer_v2 import GeminiCoachWriter

        _GEMINI_COACH_WRITER = GeminiCoachWriter()
    return _GEMINI_COACH_WRITER


# ── Phase 13-B: coach 프롬프트 angle_fixture 로더 (criteria 7 / HIGH-1 / WARNING-1) ──
# angle_fixture 는 angleSource 로 선택 (copyBranch 아님 — 직교):
#   ipsf_registered_fixture → registered_move_angles.json["angles"][angleFixtureKey]
#   eunji_measured_yaml     → criteria/{angleFixtureKey}.yaml (motion_id 가 이미 ref-
#                             로 시작 → double-prefix 금지, ref-ref-foxtop.yaml 0)
#   no_angle_criterion      → None (가짜 각도 0 — _build_prompt 가 "fixture 없음" 라인)

_REGISTERED_MOVE_ANGLES_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "registered_move_angles.json"
)
_CRITERIA_DIR = (
    Path(__file__).resolve().parents[2] / "judging_data" / "criteria"
)


def _load_coach_angle_fixture(branch_info) -> dict | None:
    """angleSource 별 angle_fixture dict 로드 ({joint: {angle, isExtension}}).

    no_angle_criterion / 미존재 → None (가짜 각도 미주입). 로드 실패도 None graceful.
    """
    source = getattr(branch_info, "angleSource", None)
    key = getattr(branch_info, "angleFixtureKey", None)
    if not key or source not in ("ipsf_registered_fixture", "eunji_measured_yaml"):
        return None
    try:
        if source == "ipsf_registered_fixture":
            data = json.loads(
                _REGISTERED_MOVE_ANGLES_PATH.read_text(encoding="utf-8")
            )
            fixture = data.get("angles", {}).get(key)
            return fixture if isinstance(fixture, dict) and fixture else None
        # eunji_measured_yaml — WARNING-1: key 가 이미 ref- 로 시작, double-prefix 금지.
        yaml_path = _CRITERIA_DIR / f"{key}.yaml"
        if not yaml_path.exists():
            return None
        import yaml as _yaml

        doc = _yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        criteria = doc.get("criteria", {}) or {}
        out: dict[str, dict] = {}
        for moment in ("setup_moment", "hold_moment", "peak_moment", "release_moment"):
            for entry in criteria.get(moment, []) or []:
                if not isinstance(entry, dict):
                    continue
                joint = entry.get("joint")
                angle = entry.get("angle_target")
                if joint is None or angle is None:
                    continue
                # BENT_OK = 부분 굽힘 hold (line 채점 out_of_scope) → 신전 아님.
                is_ext = entry.get("extension_class") == "EXTEND"
                out.setdefault(joint, {"angle": angle, "isExtension": is_ext})
        return out or None
    except Exception:  # noqa: BLE001 — fixture 로드 실패는 가짜 각도 0 으로 graceful.
        log.exception("coach angle_fixture 로드 실패 (key=%s, source=%s)", key, source)
        return None


def _build_coach_context(
    *,
    mode: str,
    assessments,
    dim_scores: dict | None,
    local_video_path: str | None,
    scene_flags: dict | None,
    body_profile: dict | None = None,
    branch_info=None,
) -> dict:
    """Cerebras / Gemini 양 writer 가 공유하는 단일 coach_context dict 박제 (B3 정합).

    박제 정신 (3차 R-B2 — geminiD 키 v1 박제 X):
      · 기존 Cerebras 호환 키 (`mode`, `joints`) — coach_writer.py L121~123 정합.
      · Phase 17 신규 키 — `videoPath`, `dimensionScores`, `sceneFlags`. Cerebras 는
        `context.get("joints")` 만 박제하므로 신규 키 무시 (graceful).
      · gemini_d_result 인자 박제 X — D wave 가 B 보다 늦게 실행 (`_process` line ~1634)
        → v1 에서 B 가 D 결과 받을 수 없음. v2 후속 plan 에서 wave 순서 재조정 후 진입.

    Args:
      mode: models.MODE_EXPERT / MODE_SELF.
      assessments: kismam top issues 박제 source (`kismam.top_issues(assessments, n=3)`).
      dim_scores: dimensions.absolute_dimension_scores 결과 dict (또는 None).
      local_video_path: keep_local_video=True 박제 후 caller 가 박은 path (또는 None).
      scene_flags: Plan 17-02 영역 C `find_scene_flags` 결과 dict (또는 None).

    Returns:
      dict — 양 writer 가 그대로 박는 단일 context.
    """
    return {
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
        "videoPath": local_video_path,
        "dimensionScores": dim_scores,
        "sceneFlags": scene_flags,
        # Phase 3 (Plan 03-01, D-04) — 자가입력 컨텍스트 훅. Phase 13 LLM 이 소비
        # (통증부위 회피·경력별 톤). 현 writer 는 context.get("joints") 만 박제하므로
        # 신규 키 graceful 무시 (위 docstring 748-751 정합 — zero behavior change).
        # weightKg 보조 ONLY (D-05) — 점수 경로 진입 금지, coach context 전달만 허용.
        "bodyProfile": body_profile,
        # Phase 13-B (criteria 7) — 동작 분기 + 정의 각도 주입. branch_info=None 시
        # graceful (motionName/branch/angleFixture 모두 None → 기존 프롬프트 불변).
        "motionName": getattr(branch_info, "officialName", None) or None,
        "branch": getattr(branch_info, "copyBranch", None),
        "angleFixture": _load_coach_angle_fixture(branch_info)
        if branch_info is not None
        else None,
    }


def _strip_reserved_keys(d: dict) -> dict:
    """`_` prefix 키 strip — user-visible result 에 reserved 키 (`_fallbackReason` /
    `_meta`) leak 차단 (Codex B3 + WARNING-3 정합).

    audit (Firestore top-level `geminiB`) 박제는 caller 가 strip 전 dict 에서 추출.
    """
    return {k: v for k, v in d.items() if not str(k).startswith("_")}


# ── Phase 13-C: writer 재시도 래퍼 + user-visible 키 판정 ────────────────────
# belle 2026-06-16 [[section-dual-coach-report]] — 계층형 폴백 (1) 두 writer 동시
# 호출 + 재시도 1회 + 짧은 타임아웃. coach_writer 는 자체 타임아웃이 없으므로
# 호출부에서 1회 재시도 래퍼로 감싼다. 둘 다 동일 coach_context 공유 (B3 정합).

# 파일럿 규모 rate-limit≈0 (decisions_13c). 짧은 타임아웃 — provider 장애 구간만
# 폴백 진입. SDK 자체 네트워크 타임아웃에 더해 시도당 1회 재시도.
_COACH_RETRY_ATTEMPTS = 2  # 최초 1 + 재시도 1


def _coach_user_visible_keys(result: dict) -> list[str]:
    """writer 결과에서 reserved(`_`) 키 제외한 joint 키 (≥1 면 성공 path)."""
    if not isinstance(result, dict):
        return []
    return [k for k in result.keys() if not str(k).startswith("_")]


def _call_coach_writer_with_retry(
    writer_name: str, write_fn, context: dict
) -> dict:
    """writer.write(context) 를 재시도 1회로 호출 (13-C 계층형 폴백 1).

    fallback dict(`{}` / `{"_fallbackReason": ...}` / user-visible 키 0) 또는 예외면
    재시도. 최종 결과(성공 dict 또는 마지막 fallback dict) 반환 — None 반환 0 (R-W4).
    """
    last: dict = {}
    for attempt in range(1, _COACH_RETRY_ATTEMPTS + 1):
        try:
            result = write_fn(context)
        except Exception:  # noqa: BLE001 — writer 예외 = 폴백 trigger, 분석 중단 X.
            log.exception(
                "coach writer 호출 예외 (writer=%s, attempt=%d)", writer_name, attempt
            )
            result = {}
        last = result if isinstance(result, dict) else {}
        if _coach_user_visible_keys(last):
            if attempt > 1:
                log.info(
                    "coach writer 재시도 성공 (writer=%s, attempt=%d)",
                    writer_name,
                    attempt,
                )
            return last
        if attempt < _COACH_RETRY_ATTEMPTS:
            log.info(
                "coach writer fallback dict — 재시도 (writer=%s, attempt=%d)",
                writer_name,
                attempt,
            )
    return last


def _gemini_b_audit_payload(
    writer_result: dict,
    *,
    cerebras_used: bool,
    cerebras_fallback_reason: str | None,
) -> dict | None:
    """Firestore top-level `geminiB` audit dict 박제 (성공 / 폴백 양쪽 분기).

    Args:
      writer_result: Gemini writer 결과 dict (성공 시 reserved `_meta` 키 포함).
        Cerebras-only path 박제 시 `{}` 박제.
      cerebras_used: Cerebras 폴백 활성 여부.
      cerebras_fallback_reason: Cerebras 폴백 trigger 박제 reason 박제 (또는 None).

    Returns:
      dict — Firestore top-level `geminiB` 박제 audit. `None` 박제 X (caller 가 None
        체크 후 키 자체 박제 차단).
    """
    meta = writer_result.get("_meta") if isinstance(writer_result, dict) else None
    if cerebras_used:
        return {
            "model": "gpt-oss-120b",  # CerebrasCoachWriter L93 정합
            "fallback": "cerebras",
            "fallbackReason": cerebras_fallback_reason or "unknown",
            "judgeScore": None,
            "latencyMs": int(meta.get("latency_ms", 0)) if isinstance(meta, dict) else 0,
            "tokensUsed": 0,
        }
    if not isinstance(meta, dict):
        return None
    return {
        "model": str(meta.get("model", "")),
        "latencyMs": int(meta.get("latency_ms", 0)),
        "tokensUsed": int(meta.get("tokens_used", 0)),
        "judgeScore": meta.get("judgeScore"),  # None or float
        "fallback": None,
        "fallbackReason": None,
    }


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
    global _FRAME_EXTRACTOR, _POSE_ESTIMATOR, _COACH_WRITER, _RTMW_ENGINE, _POLE_DETECTOR
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
    if _POLE_DETECTOR is None:
        # Plan 08-04 (B fix) — HoughPoleDetector lazy init. cv2 미설치 환경 (Lambda
        # CPU fallback / test) 에선 None 유지 → _extract_video_analysis_inputs
        # 가 vertical_fallback 박제 (graceful degrade).
        try:
            from sunity_shared.analysis.pole.detector import HoughPoleDetector
            _POLE_DETECTOR = HoughPoleDetector()
        except Exception:  # noqa: BLE001 - cv2 부재 시 graceful
            log.warning("HoughPoleDetector lazy init 실패 — vertical_fallback 박제")
            _POLE_DETECTOR = None


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
    """R3 fix Phase 6 — 단일 helper 반환 6종 (Plan 17-03 박제 keypoints_4ch 신설).

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
    keypoints_4ch: np.ndarray shape (T, 17, 4) — Plan 17-03 (3차 R-B3) 신설. to_coco17_array
      산출 (x, y, z, uncertainty_proxy). _extract_video_analysis_inputs 가 1회만 계산
      → 재계산 0 박제 (Phase 6 의 "RTMW estimate 1회" 보장 유지). 영역 D wave 가
      `keypoints_4ch[:, :, 3].max(axis=1) > 0.5` 로 low confidence frame 식별.
    """

    angles: np.ndarray
    student_profile: BodyNormalizationProfile
    pose_frames: list
    local_video_path: Path | None
    pole_axis_measurement: PoleAxisMeasurement
    keypoints_4ch: np.ndarray


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

    # Plan 08-04 (B fix, 2026-06-09) — HoughPoleDetector.detect_with_line() 활성
    # 박제. 검출된 vertical line midpoint x median 으로 PoleLine2D 산출 → Phase 8
    # axisMetrics 실효성. 검출 실패 시 line=None → coordinate_space='unavailable'
    # graceful fallback (08-03 박제 정합).
    frame_arr = frames.frames if hasattr(frames, "frames") else np.asarray(frames)
    if _POLE_DETECTOR is None:
        detected_pole = default_pole
        detected_line = None
    else:
        try:
            detected_pole, detected_line = _POLE_DETECTOR.detect_with_line(frame_arr)
        except Exception:  # noqa: BLE001 - detector 실패 시 vertical_fallback (graceful)
            log.exception("HoughPoleDetector 실패 — vertical_fallback 박제")
            detected_pole = default_pole
            detected_line = None
    pole_axis_measurement = build_pole_axis_measurement(
        axis_3d=detected_pole,
        line=detected_line,
        frame_index=None,
    )
    return _VideoAnalysisInputs(
        angles=angles_filled,
        student_profile=student_profile,
        pose_frames=pose_frames,
        local_video_path=local_video_path,
        pole_axis_measurement=pole_axis_measurement,
        keypoints_4ch=keypoints_4ch,
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


# ── Phase 12 Wave 0A R4 (Codex 직접 리뷰 2026-06-10) — kismam.assess() wiring helpers ──
#
# 3 call site (mode1 / mode3_progress / mode3_first) 모두 user_angles + reference_angles +
# target_source kwarg 박제. 이전: kwarg 없이 호출 → JointAssessment.current_angle/
# target_angle 항상 None → JointScore 가 currentAngle/targetAngle 비어 내려감 →
# result.tsx 가 "시뮬 픽스처" fallback. 본 helper 가 백엔드 실측치 wiring 의 source.

def _angles_to_mean_dict(
    angles_tj: np.ndarray | None, joint_keys: tuple[str, ...]
) -> dict[str, float]:
    """Phase aligned segment 평균 각도. (T, J) → {joint_name: mean_deg}. NaN 무시.

    Phase 12 Wave 0A R4 — kismam.assess() 의 user_angles / reference_angles kwarg source.
    빈 입력 시 빈 dict (caller 가 assess 에 빈 dict 넘기면 모든 joint → None).
    """
    if angles_tj is None:
        return {}
    arr = np.asarray(angles_tj, dtype=float)
    if arr.ndim != 2 or arr.shape[0] == 0:
        return {}
    # all-NaN column 시 RuntimeWarning 회피 — warnings catch_warnings 박제.
    import warnings as _warnings

    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore", RuntimeWarning)
        means = np.nanmean(arr, axis=0)
    return {
        joint: float(mean)
        for joint, mean in zip(joint_keys, means)
        if not np.isnan(mean)
    }


def _angles_to_dtw_median_dicts(
    user_seg: np.ndarray | None,
    ref_angles: np.ndarray | None,
    joint_keys: tuple[str, ...],
) -> tuple[dict[str, float], dict[str, float]]:
    """표시-점수 정합 helper (Phase 19 TRUST-01 / HIGH-2 iter-1).

    표시 각도(현재/기준)를 점수 산출(per_joint_deviation)과 **동일한** DTW path-정렬
    구간의 관절별 finite median 으로 산출한다. 기존 `_angles_to_mean_dict` 는
    whole-clip np.nanmean — (a) jitter/occlusion 프레임에 민감하고 (b) user matched-
    window vs ref full-clip 의 시간 비대칭(점수는 정렬 구간만, 표시는 전체) 이라 표시값
    이 점수와 19° 까지 어긋났다. per_joint_deviation(motiondtw 103-130) 의 path 순회를
    모방하되 abs-diff 가 아니라 **양측 각도값**을 관절별로 모아 median 2 dict 반환.

    Args:
        user_seg: 사용자 각도 시퀀스 (T_u, J). caller 가 정렬 구간을 이미 잘랐든
            full clip 이든 무관 — 내부에서 DTW 로 ref 에 정렬한다.
        ref_angles: 기준 각도 시퀀스 (T_r, J) — 정은지(mode1) 또는 이전 영상(mode3).
        joint_keys: 관절 이름 (분석 JOINT_KEYS).

    Returns:
        (user_median_by_joint, ref_median_by_joint). path 가 비거나 입력이 비면
        빈 dict 둘.
    """
    if user_seg is None or ref_angles is None:
        return {}, {}
    a_user = np.asarray(user_seg, dtype=float)
    a_ref = np.asarray(ref_angles, dtype=float)
    if a_user.ndim != 2 or a_ref.ndim != 2 or a_user.shape[0] == 0 or a_ref.shape[0] == 0:
        return {}, {}
    # 점수 경로(per_joint_deviation)와 동일한 DTW 정렬 사용 — 표시·점수 source 통일.
    match = motion_dtw(feature_vector(a_user), feature_vector(a_ref))
    seg = a_user[match.start : match.end]
    path = match.path
    if not path or seg.shape[0] == 0:
        return {}, {}
    J = min(a_ref.shape[1], seg.shape[1], len(joint_keys))
    user_vals: list[list[float]] = [[] for _ in range(J)]
    ref_vals: list[list[float]] = [[] for _ in range(J)]
    for u, r in path:
        if u >= seg.shape[0] or r >= a_ref.shape[0]:
            continue
        for j in range(J):
            uv = seg[u, j]
            rv = a_ref[r, j]
            if np.isfinite(uv):
                user_vals[j].append(float(uv))
            if np.isfinite(rv):
                ref_vals[j].append(float(rv))
    user_median: dict[str, float] = {}
    ref_median: dict[str, float] = {}
    for j in range(J):
        if user_vals[j]:
            user_median[joint_keys[j]] = float(np.median(user_vals[j]))
        if ref_vals[j]:
            ref_median[joint_keys[j]] = float(np.median(ref_vals[j]))
    return user_median, ref_median


def _hold_window_median_dict(
    angles: np.ndarray | None,
    profile: technique.TechniqueProfile,
    joint_keys: tuple[str, ...],
) -> dict[str, float]:
    """hold-window 관절별 finite median (Phase 19 TRUST-01 — mode3-first 표시 source).

    extension_deviation / line_score / stability_score 와 **동일한** dimensions._select_window
    구간만 본다 — 별도 window 계산 없이 drift 차단. 표시 각도가 점수 산출 frames 와 정합.
    """
    if angles is None:
        return {}
    arr = np.asarray(angles, dtype=float)
    if arr.ndim != 2 or arr.shape[0] == 0:
        return {}
    sliced, _ = dimensions._select_window(arr, profile)
    if sliced.shape[0] == 0:
        return {}
    import warnings as _warnings

    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore", RuntimeWarning)
        meds = np.nanmedian(sliced, axis=0)
    J = min(sliced.shape[1], len(joint_keys))
    return {
        joint_keys[j]: float(meds[j])
        for j in range(J)
        if np.isfinite(meds[j])
    }


def _veto_passthrough(score_result: dict, status: str) -> dict:
    """비전 거부권 audit status 직렬화 헬퍼 (Phase 20-03 TRUST-08).

    점수 불변 + visionVeto.status 만 명시 박제. status enum ∈ {applied, not_applicable,
    disabled, skipped_error, missing_local_video, mode3_held (belle 보류), missing_reference
    (Mode1 기준 영상 부재)}. 부재 ≠ 실행 — status 가 veto 실행 여부를 명시 증명한다
    (HIGH-1). 객관성: score/점수 라벨 필드 0.
    """
    return {**score_result, "visionVeto": {"status": status}}


def _apply_vision_veto(
    score_result: dict,
    local_video_path: str | None = None,
    angles: np.ndarray | None = None,
    profile: "technique.TechniqueProfile | None" = None,
    mode: str | None = None,
    reference_video_path: str | None = None,
) -> dict:
    """v2 비전 거부권 — reference-anchored 하향-전용 mutation (Phase 20 SCORE-08).

    belle 결정 (2026-06-20): **Mode1 비교 앵커 + Mode3 보류**.
      · Mode1 (MODE_EXPERT) — 학생 영상을 정은지 reference 영상과 **비교**해 severity
        산출 (코치처럼). 진공 단일 영상 판정은 mild fault 와 정타를 구별 못 해
        위양성(정타→50)/위음성(잘못된 동작→100)을 냄 — 비교가 원칙적 fix.
      · Mode3 (MODE_SELF) — **보류**. 고정 reference 가 없음 (본인 영상 비교). 절대
        차원 + 이전 영상 델타가 그대로 성립 → veto 미실행 (mode3_held).

    capped < overallScore 일 때만 result['overallScore'] 를 **낮춘다** (절대 안 올림).
    평균 금지 — terminal min cap 만(Pitfall 1). visionVeto.status 가 veto 실행을 증명
    (부재 ≠ 실행, HIGH-1). SEVERITY_CAP 은 spec-anchored (major=50/moderate=75/
    minor·none=no-cap) — 재튜닝 금지(D-02 curve-fit 금지).

    status enum (TRUST-08, 무음실패 방지 — Pitfall 5):
      · disabled            — _gemini_vision_veto_enabled() OFF (adapter 미호출)
      · mode3_held          — mode==MODE_SELF (belle 보류 — reference 없음)
      · missing_local_video — local_video_path None (graceful, HIGH-1)
      · missing_reference   — Mode1 인데 reference 영상 부재 (진공 판정 안 함, graceful)
      · skipped_error       — adapter None(키부재/실패) → graceful + WARNING
      · not_applicable      — cap 미적용 (minor/none/placeholder — 점수 불변)
      · applied             — cap 적용 (overallScore 하향)

    mode=None (back-compat) — 단일 영상 진공 판정 경로 유지 (기존 호출/테스트 보존).

    토글은 pipeline 단독 소유 (iter2 MEDIUM-1) — 어댑터는 토글 미참조.
    """
    import sunity_shared.models as models  # lazy — mode 상수 비교

    try:
        if not _gemini_vision_veto_enabled():
            return _veto_passthrough(score_result, "disabled")
        if mode == models.MODE_SELF:
            # belle 보류 — Mode3 는 고정 reference 가 없어 비교 앵커 불가.
            # 절대 차원 + 이전 영상 델타가 성립 → veto 미실행 (명시 신호).
            return _veto_passthrough(score_result, "mode3_held")
        if local_video_path is None:
            # HIGH-1 — veto ON 인데 local 영상 부재. 무음 no-op 이 아니라 명시 신호.
            return _veto_passthrough(score_result, "missing_local_video")
        if mode == models.MODE_EXPERT and reference_video_path is None:
            # Mode1 비교 앵커인데 기준 영상 부재 → 진공 판정 안 함 (위양성/위음성
            # 재발 차단). 명시 신호로 graceful 통과.
            return _veto_passthrough(score_result, "missing_reference")
        from sunity_shared.analysis import vision_veto, gemini_vision_scorer

        at = vision_veto.worst_pose_timestamp(profile)
        verdict = gemini_vision_scorer.assess_fault_severity(
            local_video_path,
            at_seconds=at,
            reference_video_path=reference_video_path,
        )
        if verdict is None:
            log.warning(
                "vision veto 미실행 — verdict None, v1 점수 통과 "
                "(graceful, 무음실패 관측 — Pitfall 5)"
            )
            return _veto_passthrough(score_result, "skipped_error")
        overall = score_result["overallScore"]
        capped = vision_veto.apply_downward_cap(overall, verdict.severity)
        if capped < overall:
            # 하향-전용 — apply_downward_cap 이 min 만(올림 0). audit 직렬화.
            # Phase 20 (UI B1) — primaryFault 박제: "왜 점수가 내려갔는지"를 앱이
            # 노출할 수 있게 verdict.primary_fault(결함 DESCRIPTION) 만 동반. 객관성:
            # 점수/숫자 라벨 아님 — 자연어 결함 설명만 (analysis-objectivity 박제).
            # Phase 20 #3 (2026-06-21) — faultJoints: Gemini 가 본 실제 결함 위치를
            # 정식 keypoint 로 매핑해 동반 저장한다. 앱 마커가 각도편차 최대 관절
            # (어깨/팔꿈치)이 아니라 진짜 결함 관절(다리/팔 등)을 강조하게 하는 fix.
            # 매핑 불가 시 빈 list → 앱이 기존 편차-기반 폴백 사용 (graceful).
            fault_joints = vision_veto.fault_joints_from_differences(
                verdict.differences
            )
            vision_veto_audit = {
                "status": "applied",
                "severity": verdict.severity,
                "capApplied": capped,
                "primaryFault": verdict.primary_fault,
            }
            if fault_joints:
                vision_veto_audit["faultJoints"] = fault_joints
            return {
                **score_result,
                "overallScore": capped,
                "visionVeto": vision_veto_audit,
            }
        # cap 미적용 (production placeholder None / minor / cap >= overall) — 점수 불변.
        return _veto_passthrough(score_result, "not_applicable")
    except Exception:  # noqa: BLE001 - 비전 hook 실패는 분석을 막지 않는다 (graceful)
        log.exception(
            "vision veto hook 실패 — score_result 그대로 통과 (graceful, skipped_error)"
        )
        return _veto_passthrough(score_result, "skipped_error")


def _extension_target_dict(
    profile: technique.TechniqueProfile,
) -> dict[str, float]:
    """mode3 first 의 reference_angles — extension-required joint 만 IPSF 180°.

    Phase 12 Wave 0A R4 정합 — non-extension joint 는 dict 에 key 없음.
    kismam.assess() 가 reference_angles 에 key 없는 joint 를 target_source='unavailable'
    + target_angle=None 으로 분기 (kismam.assess body 박제 참조).
    """
    return {
        key: 180.0
        for key in skeleton.JOINT_KEYS
        if profile.expects_extension(key)
    }


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


def _mode3_scoring_basis(is_first: bool, is_reference_free: bool) -> str:
    """Mode3 의 scoringBasis 를 실제 채점 SOURCE 로 도출 (Phase 19 TRUST-03).

    first 는 reference motion 비교가 아니라 abs_dims + extension targets — 미등록이면
    절대트랙(reference_free_absolute), 등재면 recognized_motion_absolute. progress 는
    이전 영상 각도 일관성 + 절대트랙 — 미등록은 composite(previous_analysis_plus_
    reference_free_absolute, HIGH-3 lossy 금지), 등재는 previous_analysis_plus_absolute.
    reference_motion 은 절대 사용 안 함 (Mode1 전용).
    """
    if is_first:
        if is_reference_free:
            return assemble.MODE3_SCORING_BASIS_REFERENCE_FREE_ABSOLUTE
        return assemble.MODE3_SCORING_BASIS_RECOGNIZED_ABSOLUTE
    if is_reference_free:
        return assemble.MODE3_SCORING_BASIS_PREV_PLUS_REFERENCE_FREE
    return assemble.MODE3_SCORING_BASIS_PREV_PLUS_ABSOLUTE


# Phase 20-03 iter5 HIGH-2 — recognition_low_confidence 억제 결과의 scoringBasisLabel.
# reference-free '기준 동작 없음' 라벨을 절대 포함하지 않는다 (reason-owns-copy).
_SCORE_SUPPRESSION_LOW_CONF_LABEL = "동작 인식 신뢰도가 낮아 기준을 확정할 수 없어요"


def _score_suppression_reason(
    profile: "technique.TechniqueProfile | None",
    branch_info: "assemble.MotionBranchInfo | None",
) -> str | None:
    """Mode3 점수 억제 사유를 recognizer category PROVENANCE 우선순위로 결정 (iter4 HIGH-1).

    우선순위:
      1. profile.category == 'low_confidence' → 'recognition_low_confidence'.
         **motion_id=None 이 lookup_motion_branch(None)=_SAFE_DEFAULT_BRANCH(is_reference_free
         True)를 유발해도 무조건 우선** — "모르니까 안전 기본" ≠ "확정 미보유".
         _SAFE_DEFAULT_BRANCH(motion_id=None 유래)를 low_confidence 일 때 unheld 의 증거로
         쓰지 않는다 (test_resolver_low_confidence_not_unheld 가 이 경로를 박제).
      2. profile.category == 'unregistered' → 'unheld' (진짜 미등록).
      3. is_reference_free_motion(branch_info) (concrete branch metadata 가 unavailable
         basis) → 'unheld'.
      4. 그 외(등재 동작) → None (억제 아님).

    '둘 다 해당이면 unheld 우선' 류 collapse 로직 절대 사용 금지 (low_confidence 가
    unheld 로 collapse 되는 원인 — iter4 HIGH-1).
    """
    category = getattr(profile, "category", None)
    if category == "low_confidence":
        return "recognition_low_confidence"
    if category == "unregistered":
        return "unheld"
    if assemble.is_reference_free_motion(branch_info):
        return "unheld"
    return None


def _apply_score_suppression(
    result: dict,
    profile: "technique.TechniqueProfile | None",
    branch_info: "assemble.MotionBranchInfo | None",
) -> dict:
    """Mode3 미보유/저신뢰 동작 점수 억제 (Phase 20-03 TRUST-07, branch-3).

    resolver(_score_suppression_reason) 가 결정한 reason 으로 result 에 scoreSuppressed +
    scoreSuppressedReason emit. 점수는 산출하되 화면이 점수카드 전체를 억제 (D-08 confident
    97 차단). fail-closed/raise 금지 ([[motion-routing-generalize-principle]]).

    iter5 HIGH-2 (reason-owns-copy): recognition_low_confidence 면 comparison.scoringBasisLabel
    을 reference-free '기준 동작 없음' 이 아닌 '신뢰도 낮음' 류 라벨로 override — scoringBasisLabel
    이 reason 이 존재하면 scoringBasis 단독에서 파생되지 않는다 (두 번째 UI 필드 reason leak 차단).

    iter5 MEDIUM-2 (A2 reconcile): recognizer category 와 branch is_reference_free 출처가
    달라 불일치 시 정확히 하나의 structured 필드 scoreSuppressionAudit 로 보고 (log.warning
    '또는' 대안 폐기, log 는 additive only).

    producer-contract fail-loud:
      · scoringBasis=='reference_free_absolute' 인데 scoreSuppressed 누락 (iter3 HIGH-2)
      · scoreSuppressed==True 인데 scoreSuppressedReason 누락/무효 (iter4 MEDIUM-1)
      → 둘 다 명시 assert (UI silent 추론 / default 카피 의존 차단).
    """
    comparison = result.get("comparison") or {}
    is_reference_free = assemble.is_reference_free_motion(branch_info)
    reason = _score_suppression_reason(profile, branch_info)

    if reason is not None:
        result["scoreSuppressed"] = True
        result["scoreSuppressedReason"] = reason
        # iter5 HIGH-2 — reason-owns-copy: recognition_low_confidence 는 reference-free
        # '기준 동작 없음' 라벨 금지. unheld 는 기존 reference-free 라벨 유지.
        if reason == "recognition_low_confidence" and isinstance(comparison, dict):
            comparison["scoringBasisLabel"] = _SCORE_SUPPRESSION_LOW_CONF_LABEL
        # iter5 MEDIUM-2 — A2 reconcile 단일 structured sink (불일치 관측).
        result["scoreSuppressionAudit"] = {
            "recognizerCategory": getattr(profile, "category", None) or "",
            "branchReferenceFree": bool(is_reference_free),
            "resolvedReason": reason,
        }

    # producer-contract fail-loud (iter3 HIGH-2 / iter4 MEDIUM-1).
    scoring_basis = comparison.get("scoringBasis") if isinstance(comparison, dict) else None
    if scoring_basis == assemble.MODE3_SCORING_BASIS_REFERENCE_FREE_ABSOLUTE:
        assert result.get("scoreSuppressed") is True, (
            "producer-contract FAILURE — reference_free_absolute 는 scoreSuppressed 동반 "
            "필수 (iter3 HIGH-2, UI silent 추론 금지)"
        )
    if result.get("scoreSuppressed") is True:
        emitted = result.get("scoreSuppressedReason")
        assert emitted in models.SCORE_SUPPRESSED_REASONS, (
            "producer-contract FAILURE — scoreSuppressed=True 는 scoreSuppressedReason "
            "(SCORE_SUPPRESSED_REASONS 내 값) 동반 필수 (iter4 MEDIUM-1, UI default 카피 금지)"
        )
    return result


def _mode3_comparison(
    angles: np.ndarray,
    prev: dict | None,
    profile: technique.TechniqueProfile,
    branch_info: assemble.MotionBranchInfo | None = None,
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
    # Phase 19 TRUST-03 — branch_info 미전달 시 profile.motion_id 로 lookup (게이트 wiring
    # 이 없는 단위 테스트/호출 경로 호환). is_reference_free_motion 으로 미보유 판정
    # (copyBranch 단독 분기 금지). fail-closed/raise 없음 — 점수는 주되 근거만 라벨링.
    if branch_info is None:
        branch_info = assemble.lookup_motion_branch(
            getattr(profile, "motion_id", None)
        )
    is_reference_free = assemble.is_reference_free_motion(branch_info)
    prev_angles = (prev or {}).get("angles")
    if not prev or not prev_angles:
        # 첫 분석(또는 이전 angles 미저장) — 비교 대상 없음. 코칭은 신전 부족분(IPSF 라인) 기준.
        overall = dimensions.overall_from_dimensions(abs_dims)
        # Phase 12 Wave 0A R4 (Codex 직접 리뷰 2026-06-10) — kismam.assess() 3 kwarg 박제.
        # mode3 first: extension-required joint 만 IPSF 180° target,
        # 그 외 joint 는 reference_angles 에 key 없음 → assess 가 target_source='unavailable'
        # 분기 박제 (kismam.assess body 의 else branch).
        ext_targets = _extension_target_dict(profile)
        # Phase 19 TRUST-01 — mode3-first user 표시값은 extension_deviation 과 동일
        # hold-window(_select_window) source 의 median (whole-clip nanmean 아님). 별도
        # window 계산 금지(drift 방지) — dimensions._select_window 를 그대로 공유.
        user_mean = _hold_window_median_dict(angles, profile, skeleton.JOINT_KEYS)
        assessments = kismam.assess(
            dimensions.extension_deviation(angles, profile),
            user_angles=user_mean,
            reference_angles=ext_targets,
            target_source="extension_requirement",
        )
        first_basis = _mode3_scoring_basis(
            is_first=True, is_reference_free=is_reference_free
        )
        return (
            assessments,
            abs_dims,
            overall,
            assemble.build_mode3(is_first=True, scoring_basis=first_basis),
        )
    num_joints = len(prev.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    deviation, _match, _user_seg, prev_seg = _deviation_against(
        angles, prev_angles, num_joints
    )
    # Phase 19 TRUST-01 — mode3 progress: 표시 각도(현재/이전) = 점수 산출 DTW path-정렬
    # median (whole-clip nanmean 비대칭 제거). prev_seg 는 _deviation_against 가 reshape 한
    # 이전 영상 각도 시퀀스. _angles_to_dtw_median_dicts 가 per_joint_deviation 과 동일 source.
    user_mean, ref_mean = _angles_to_dtw_median_dicts(
        angles, prev_seg, skeleton.JOINT_KEYS
    )
    assessments = kismam.assess(
        deviation,
        user_angles=user_mean,
        reference_angles=ref_mean,
        target_source="previous_analysis",
    )
    dim_scores = {dimensions.DIM_ANGLE: kismam.overall_score(assessments), **abs_dims}
    # mode3 second+ overall = 절대 차원(line/stability)만 — angle 제외 (#8 역전 수정).
    # 이유: mode3 의 angle 은 "이전 영상 대비 유사도"라, 사용자가 발전(이전=틀림,
    # 신규=올바름)하면 두 영상이 달라져 유사도(angle)가 떨어지고,
    # overall_from_dimensions 의 min(CORE_DIMENSIONS) 가 종합을 끌어내려 발전을
    # 역전시킨다 (belle 기기: 틀린 kip-up 98 → 올바른 영상 88, -10).
    # 첫 분석 overall(abs_dims)과 동일 source 를 써 세션 간 같은 척도를 유지하고
    # 유사도에 의한 역전을 제거한다 ([[mode3-progress-not-similarity]] /
    # [[mode3-overall-exclude-angle-similarity]] 정합). dim_scores(angle 포함)는 표시/
    # 일관성 지표로 반환에 그대로 유지하고, delta(build_mode3 의 cur_dimension_scores
    # =abs_dims)는 이미 절대 차원만 사용 → 변경 없음.
    overall = dimensions.overall_from_dimensions(abs_dims)
    prev_dims = (prev.get("result") or {}).get("dimensionScores")
    progress_basis = _mode3_scoring_basis(
        is_first=False, is_reference_free=is_reference_free
    )
    comparison = assemble.build_mode3(
        is_first=False,
        previous_analysis_id=prev.get("analysisId"),
        prev_dimension_scores=prev_dims,
        cur_dimension_scores=abs_dims,  # 발전 델타는 절대 3차원만(같은 척도)
        scoring_basis=progress_basis,
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
    # Plan 17-01 Task 4 (R-B4 정합) — Phase 17 4 영역 토글 중 하나만 ON 이어도
    # local_video_path 보존. Phase 5 recognizer 기존 path 와 OR 박제.
    # Phase 20-03 HIGH-1 — keep_local_video 게이트에 _gemini_vision_veto_enabled() 포함.
    # veto 만 ON 이고 Phase17 vision 토글이 OFF 라도 local_video_path 가 보존돼야
    # _apply_vision_veto 가 None 으로 무음 no-op 되지 않는다 (veto no-op 차단).
    inputs = _extract_video_analysis_inputs(
        bucket, key, default_pole,
        keep_local_video=(
            _gemini_enabled()
            or _gemini_vision_enabled()
            or _gemini_vision_veto_enabled()
        ),
    )
    angles = inputs.angles
    student_profile = inputs.student_profile  # R4 fix — non-null
    pose_frames = inputs.pose_frames
    local_video_path_obj = inputs.local_video_path
    local_video_path = str(local_video_path_obj) if local_video_path_obj else None

    # ── Plan 17-02 Wave 1 — 영역 C Finding 호출 (RTMW estimate 직후 / KISMAM 직전) ──
    # is_reference 박제: S3 key prefix 1차 + Firestore mode 2차 (R-W3 정합 — `_process`
    # 시그너처 인자 추가 X). find_scene_flags 안에서 G4 정은지 영상 가드 발동.
    # B4 hard gate — local_video_path 만 사용 (S3 재다운로드 / RTMW 재실행 0).
    # graceful — find_scene_flags 예외 / GEMINI_FINDING_ENABLED OFF / local path 없음
    # 시 None 반환 후 분석 흐름 계속.
    is_reference_local = _resolve_is_reference(key, meta)
    scene_result = _call_wave1_scene_finder(
        local_video_path=local_video_path,
        is_reference=is_reference_local,
    )

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

    # Phase 20 — Mode1 reference-anchored vision veto (belle 2026-06-20).
    # 정은지 reference 영상을 local 로 받아 _apply_vision_veto 에 전달 (코치처럼 비교).
    # outer try **밖** 초기화 → 어떤 경로에서도 outer finally cleanup scope 보장
    # (다운로드~veto 사이 예외 시에도 임시 파일 누수 0). Mode3 는 None 유지 → mode3_held.
    reference_local_video_path: str | None = None

    # R2 wiring — target 영상 torso px 산출 (compare_body_profiles target_torso_px arg).
    target_torso = _extract_target_torso_px(pose_frames)

    try:
        # 기술 인식(swappable) → 절대 차원(라인/안정성)은 기준 영상 없이 항상 산출.
        # Plan 5-03 박제 — recognize(angles, frames=local_video_path) 호출. Gemini
        # 어댑터는 frames 인자 (video path) 를 File API 입력으로 사용. Fallback 은
        # frames 인자 ignore (Protocol 정합 — TestProtocolCompat 박제 검증).
        profile = recognizer.recognize(angles, frames=local_video_path)
        abs_dims = dimensions.absolute_dimension_scores(angles, profile)

        # Phase 19 TRUST-03 (BLOCKER-1 iter-1 + ITER-4) — branch_info lookup 을 recognize
        # 직후로 이동(과거엔 build_result 직전). MODE_SELF 게이트(_mode3_comparison) +
        # coach_context + build_result 가 동일 branch_info 1개를 공유 (중복 lookup 0,
        # single source). 미존재/None → branch2 안전 기본 (lookup_motion_branch 내부 처리).
        branch_info = assemble.lookup_motion_branch(
            getattr(profile, "motion_id", None)
        )

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
            # Phase 19 TRUST-01 (HIGH-2 iter-1): 표시 각도 = 점수 산출 DTW path-정렬 median.
            # 기존 whole-clip np.nanmean(user_seg) vs np.nanmean(a_ref) 는 시간 비대칭
            # (user matched-window vs ref full-clip) + jitter 민감 → 표시·점수 불일치.
            # _angles_to_dtw_median_dicts 가 per_joint_deviation 과 동일 path/median source 사용.
            user_mean_mode1, ref_mean_mode1 = _angles_to_dtw_median_dicts(
                angles, a_ref, skeleton.JOINT_KEYS
            )
            assessments = kismam.assess(
                deviation,
                user_angles=user_mean_mode1,
                reference_angles=ref_mean_mode1,
                target_source="reference_motion",
            )
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
            overall = dimensions.overall_from_dimensions(dimension_scores)  # min-of-core (angle/line); stability 비기여
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
                # Phase 20 — vision veto ON 일 때만 기준 영상을 local 로 다운로드
                # (B4 — _apply_vision_veto 가 어댑터에 path 전달, 어댑터 재다운로드 0).
                # delete=False 임시 파일 → veto 호출 후 finally 에서 _safe_unlink.
                if _gemini_vision_veto_enabled():
                    try:
                        ref_ext = os.path.splitext(ref["videoS3Key"])[1] or ".mp4"
                        ref_tmp = tempfile.NamedTemporaryFile(
                            suffix=ref_ext, delete=False
                        )
                        ref_tmp.close()
                        _s3.download_file(bucket, ref["videoS3Key"], ref_tmp.name)
                        reference_local_video_path = ref_tmp.name
                    except Exception:  # noqa: BLE001 - 기준 영상 다운로드 실패 graceful
                        log.warning(
                            "기준 영상 다운로드 실패 — veto missing_reference 로 graceful "
                            "(분석 흐름 유지) uid=%s analysis_id=%s",
                            uid, analysis_id,
                        )
                        _safe_unlink_local_video(reference_local_video_path)
                        reference_local_video_path = None
        else:  # MODE_SELF — 자기 성장. 절대 차원 + (이전 분석 있으면) 발전 델타.
            # 박제 (2026-06-07 belle): mode=MODE_SELF 박제 — mode1 (정은지) 분석을
            # prev 로 잡는 함정 fix. 같은 mode 안에서만 prev 검색.
            prev = firestore_admin.get_previous_analysis(
                uid, analysis_id, mode=models.MODE_SELF
            )
            assessments, dimension_scores, overall, comparison = _mode3_comparison(
                angles, prev, profile, branch_info=branch_info
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

        # ── Plan 17-04 Wave 3 — 영역 B 코칭 멘트 dual-track 박제 ──────────
        # 박제 위치 (3차 R-B2): 기존 Cerebras coach writer 호출부 — `assemble.build_result`
        # 직전. Plan 03 augment_low_confidence (D) 는 `build_keypoint_report` 직후 박혀
        # B 보다 늦음 → v1 에서 B 가 D 결과 받을 수 없음 (geminiD context 박제 X).
        # 3차 R-B1 (Option A) — wave 1 (find_scene_flags, line ~1238) 가 이미 종료된
        # 후 박힘 (자연 박힘 — _process 본체 박제 순서).
        # 2차 R-W4 — None 박제 0. dual-track 분기 = `_fallbackReason` 키 또는 빈 dict.
        # Phase 13-B (HIGH-2) + Phase 19: branch_info 는 recognize 직후 1회 lookup 한
        # 동일 객체를 재사용 (coach_context / build_result / MODE_SELF 게이트 공유, 중복
        # lookup 0). 미존재/None → branch2 안전 기본 (lookup_motion_branch 내부 처리).
        coach_context = _build_coach_context(
            mode=mode,
            assessments=assessments,
            dim_scores=dimension_scores,
            local_video_path=local_video_path,
            scene_flags=scene_result,
            branch_info=branch_info,
            # Phase 3 (Plan 03-01, D-04) — analysis doc 에 snapshot 된 자가입력
            # 프로필을 meta free-read (referenceMotionId 와 동일 메커니즘). server
            # normalize_body_profile 로 unknown enum/범위 밖 → None graceful (SC#4).
            body_profile=models.normalize_body_profile(meta.get("bodyProfile")),
        )
        # ── Phase 13-C: 섹션형 듀얼 coach — 둘 다 호출 + 섹션 조립 + 계층형 폴백 ──
        # belle 2026-06-16 [[section-dual-coach-report]]. GEMINI_COACH_ENABLED=1
        # (default) 시 양쪽 writer 를 둘 다 호출해 섹션별로 조립 (원인/강사확인=Gemini,
        # 교정처방/부상위험=Cerebras). 한쪽 실패(재시도 후) → cross-fill, 둘 다 실패 →
        # coach_details={} (build_result 수치 폴백). env OFF 시 기존 Cerebras-only 보존.
        gemini_b_audit: dict | None = None
        if _coach_enabled():
            # (1) 양쪽 writer 동시 호출 + 시도당 재시도 1회 (단일 coach_context 공유, B3).
            gemini_result = _call_coach_writer_with_retry(
                "gemini", _ensure_gemini_coach_writer().write, coach_context
            )
            cerebras_result = _call_coach_writer_with_retry(
                "cerebras", _COACH_WRITER.write, coach_context
            )
            gemini_ok = bool(_coach_user_visible_keys(gemini_result))
            cerebras_ok = bool(_coach_user_visible_keys(cerebras_result))

            if gemini_ok or cerebras_ok:
                # (2) 섹션 조립 — top 3 관절키 기준. cross-fill 이 빈 섹션 0 보장.
                top_keys = [a.key for a in kismam.top_issues(assessments, n=3)]
                coach_details, section_audit = assemble.assemble_dual_coach_sections(
                    _strip_reserved_keys(gemini_result) if gemini_ok else {},
                    _strip_reserved_keys(cerebras_result) if cerebras_ok else {},
                    top_keys,
                )
                # (5) 섹션별 출처 + cross-fill audit 로깅 (성공/폴백률 실측 전환 근거).
                cross_filled_joints = [
                    j for j, a in section_audit.items() if a.get("crossFilled")
                ]
                log.info(
                    "coach dual-track 섹션 조립 — gemini_ok=%s cerebras_ok=%s "
                    "joints=%d cross_filled=%s audit=%s",
                    gemini_ok,
                    cerebras_ok,
                    len(top_keys),
                    cross_filled_joints,
                    section_audit,
                )
                gemini_b_audit = _gemini_b_audit_payload(
                    gemini_result if gemini_ok else {},
                    cerebras_used=not gemini_ok,
                    cerebras_fallback_reason=(
                        None
                        if gemini_ok
                        else gemini_result.get("_fallbackReason") or "gemini_fallback"
                    ),
                )
                if gemini_b_audit is not None:
                    gemini_b_audit["dualTrack"] = True
                    gemini_b_audit["sectionAudit"] = section_audit
                    gemini_b_audit["crossFilledJoints"] = cross_filled_joints
            else:
                # (4) 둘 다 실패 → coach_details={} → build_result 수치 폴백 (최후 바닥).
                g_reason = gemini_result.get("_fallbackReason") or "gemini_fallback"
                log.info(
                    "coach dual-track 양쪽 실패 — 수치 폴백 (gemini_reason=%s cerebras=fallback)",
                    g_reason,
                )
                coach_details = {}
                gemini_b_audit = _gemini_b_audit_payload(
                    {},
                    cerebras_used=True,
                    cerebras_fallback_reason="both_failed",
                )
                if gemini_b_audit is not None:
                    gemini_b_audit["dualTrack"] = True
        else:
            # GEMINI_COACH_ENABLED OFF — Cerebras only (기존 path 그대로). audit 박제 X.
            coach_details = _COACH_WRITER.write(coach_context)
            gemini_b_audit = None
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
            # Phase 13-B (HIGH-2): copyBranch 분기 카피 pass-through (coach 와 동일 lookup).
            branch_info=branch_info,
        )
        # Phase 20 SCORE-08 — v2 비전 하향 거부권 (reference-anchored, belle 2026-06-20).
        # 호출부는 mode 분기 밖이지만 mode + 기준 영상 path 를 전달 → _apply_vision_veto
        # 가 내부에서 분기: Mode1=비교 앵커 / Mode3=mode3_held 보류.
        # profile = recognize 직후 산출된 동일 객체 (worst_pose_timestamp source).
        # reference_local_video_path = Mode1 에서만 채워짐 (Mode3 는 None → 보류, 다운로드 0).
        try:
            result = _apply_vision_veto(
                result,
                local_video_path,
                angles,
                profile,
                mode=mode,
                reference_video_path=reference_local_video_path,
            )
        finally:
            # 기준 영상 임시 파일 정리 — disk 누수 차단 (Mode3 는 None → no-op).
            _safe_unlink_local_video(reference_local_video_path)
            reference_local_video_path = None
        # Phase 20-03 TRUST-07 — Mode3 미보유/저신뢰 점수 억제 (branch-3, D-08).
        # MODE_SELF 전용 (Mode1 은 reference 비교라 미보유 개념 없음). resolver provenance +
        # reason-owns-copy scoringBasisLabel + A2 structured audit + producer-contract fail-loud.
        if mode == models.MODE_SELF:
            result = _apply_score_suppression(result, profile, branch_info)
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

        # ── Phase 9 (Plan 09-02) — ForcePatternInference 추론 layer ──────
        # D-09-D6: mode_context 산출 inline (별도 helper 신설 X — RESEARCH Open Q,
        # Pattern 6, Pitfall 3 정합). pipeline `_mode3_comparison` 가 산출한
        # comparison["isFirst"] 를 single source 로 재사용 (Phase 12.5
        # build_mode3 패턴 정합 — assemble.py:244).
        #
        # D-09-A2 raw signal only guard — force_pattern.py 가 axis severity 직접
        # trust X (AST gate test_force_pattern_no_severity_use.py 회귀 차단).
        # D-09-C1 Layer 2 (Gemini) 영구 차단 — pure-function inference.
        force_pattern_inference_dict: dict | None = None
        if force_signals_report is not None:
            if mode == models.MODE_EXPERT:
                mode_context: fp.ModeContext = "mode1"
            else:  # MODE_SELF
                is_first = (
                    comparison.get("isFirst", True)
                    if isinstance(comparison, dict)
                    else True
                )
                mode_context = "mode3_first" if is_first else "mode3_progress"

            force_pattern_inference = fp.infer_force_direction_pattern(
                force_signals_report,
                motion_id=getattr(profile, "motion_id", None),
                mode_context=mode_context,
            )
            # Phase 12 hotfix (2026-06-11 belle UAT 1차) — high score finding gate.
            # 자기-비교 (정은지 vs 정은지) / 거의 동일 영상 시 finding 의미 없음.
            # overall >= 90 → findings 비움 + umbrella warning. UI 가 빈 list 일 때
            # Wave 1 fallback ("분명한 힘 흐름 이슈 신호가 보이지 않습니다") 노출.
            if overall >= 90 and force_pattern_inference.findings:
                force_pattern_inference = dataclasses.replace(
                    force_pattern_inference,
                    findings=[],
                    warnings=list(force_pattern_inference.warnings)
                    + ["high_score_finding_gated"],
                )

            # ── Phase 11 (Plan 11-01) — CoachCommentHook 부착 (single call) ──
            # BLOCKER-2: hook 생성은 force_pattern_inference 생성/high-score gate 직후 +
            #   complete_analysis 직전 window 에서 1회. ForcePatternInference.findings 를 본다.
            # BLOCKER-3: coach_hooks 는 별도 변수 — coach_details(joint writer) 무오염.
            # iter-3 HIGH-1: writer 는 bundle|None 만 반환, per-report 폴백은 helper(resolve_
            #   coach_hook_bundle) 소유 — pipeline 은 tuple 소비만 (자체 폴백 분기 0).
            # D-08: 키 미설정/가드 reject 시 bundle=None → helper canned → 분석 절대 실패 안 함.
            _force_findings = list(force_pattern_inference.findings)
            _body_findings = (
                list(body_comparison_report.findings)
                if body_comparison_report is not None
                else []
            )
            # lazy import — Lambda 250MB 한도 정합 (gemini 의존 콜드스타트 절감).
            from sunity_shared.gemini.coach_hook_writer import GeminiCoachHookWriter

            # D-08 backstop (review CR-01): hook 생성/resolve 의 어떤 예외도
            #   fail_analysis 로 새지 않게 한다 — hook 은 cosmetic, 분석 절대 실패 안 함.
            #   resolve_coach_hook_bundle 은 정제 후에도 raise 하지 않도록 고쳐졌지만
            #   (coach_hook_builder._clean_str_list), 이 try 는 미래 회귀까지 막는 2차 방어.
            try:
                _hook_bundle = GeminiCoachHookWriter().build_coach_hooks(
                    force_findings=_force_findings,
                    body_findings=_body_findings,
                )
                _force_hook, _body_hook = resolve_coach_hook_bundle(
                    _hook_bundle,
                    force_findings=_force_findings,
                    body_findings=_body_findings,
                )
            except Exception:  # noqa: BLE001 - hook 결함이 분석을 죽이면 안 됨 (D-08)
                log.exception(
                    "CoachCommentHook 생성 실패 — canned fallback 으로 분석 계속 (D-08)."
                )
                from sunity_shared.analysis.coach_hook_builder import build_canned_hook

                _force_hook = build_canned_hook(
                    _force_findings, source_report="forcePatternInference"
                )
                _body_hook = build_canned_hook(
                    _body_findings, source_report="bodyComparisonReport"
                )
            force_pattern_inference = dataclasses.replace(
                force_pattern_inference, coach_comment_hook=_force_hook
            )
            if body_comparison_report is not None:
                body_comparison_report = dataclasses.replace(
                    body_comparison_report, coach_comment_hook=_body_hook
                )
                # hook 부착 후 body dict 재변환 (coachCommentHook 포함).
                body_comparison_report_dict = _dataclass_to_camel_case_dict(
                    body_comparison_report
                )

            force_pattern_inference_dict = _dataclass_to_camel_case_dict(
                force_pattern_inference
            )
        # ────────────────────────────────────────────────────────────────

        # ── Phase 13 (Plan 13-A, PERS-03) — 보완 운동 매핑 ──────────────────
        # 실패 원인 후보(Phase 9 findings) + 자가입력 통증부위(bodyProfile.painAreas)
        # + motion_id → exercise_map.map_exercises (pure fn). 3~5 개인화 subset.
        # D-05: painAreas 만 소비 — weightKg 등 점수 경로 진입 0. normalize_body_profile
        # 가 PAIN_AREAS frozenset 멤버만 통과 (위조 painAreas drop). graceful None/빈.
        pain_areas = (
            models.normalize_body_profile(meta.get("bodyProfile")) or {}
        ).get("painAreas", []) or []
        recommended_exercises = exercise_map.map_exercises(
            force_pattern_inference_dict,
            pain_areas=pain_areas,
            motion_id=getattr(profile, "motion_id", None),
        )
        # ────────────────────────────────────────────────────────────────

        # ── Phase 12 Wave 0B (Plan 12-01) — KeypointReport 산출 + wiring ──
        # D-12-E2 + R3 정합. KeypointOverlay (Wave 1+) 소비 source.
        # 분석 algorithm (DTW / threshold / Phase 6/7/8 calibration) = 9fps 유지.
        # 저장 시점에 18fps 로 선형 upsample (Phase 12 hotfix 2026-06-11 belle UAT
        # 1차: 빠른 회전 시 keypoint 끊김 + 끝부분 정지 자세 mitigation).
        # 18fps 선택 이유 — Firestore 40k index entry/document 한도:
        #   30fps × 60s × 8 joints × 2 = 28,800 data + confidence/axis 합 ~60k → 한도 초과.
        #   18fps × 60s × 8 × 2 = 17,280 data + 기타 합 ~26k → 안전.
        # belle UAT 1차 17초 영상에선 9fps → 18fps 만으로도 충분히 부드러움 개선.
        keypoint_report_raw = build_keypoint_report(pose_frames, fps=9.0)
        keypoint_report_obj = (
            upsample_to_fps(keypoint_report_raw, target_fps=18.0)
            if keypoint_report_raw is not None
            else None
        )

        # ── Plan 17-03 Wave 2 — 영역 D Keypoint 보강 wiring ──────────────
        # 박제 위치 (2차 R-B1 정정): build_keypoint_report 직후 + complete_analysis
        # 직전. build_result + DTW/KISMAM/각도/dim_scores 는 wave 2 진입 전에 이미
        # 끝난 상태 — D wave 가 점수 surface 0 (B2 hard gate).
        #
        # **3D `coco_array` (inputs.keypoints_4ch) 는 mutate 0** — user-visible
        # KeypointReport.data / confidence 만 보강. DTW/KISMAM/8 관절각 차원 점수
        # 입력은 RTMW 원본 그대로 (B2 정합).
        gemini_d_result: dict | None = None
        if keypoint_report_obj is not None:
            low_uncertainty_indices = _low_uncertainty_frame_indices(
                inputs.keypoints_4ch
            )
            # build_keypoint_report 가 9fps 박제, upsample_to_fps 가 18fps 로 박제.
            # keypoints_4ch 는 9fps RTMW 원본 → low_uncertainty_indices 는 9fps frame
            # index 박제. KeypointReport (18fps) 의 data 위치 와 mismatch — 본 1차
            # PR 박제는 _process_for_wave2 박제 frame index space 정합 (9fps 박제)
            # 으로 9fps KeypointReport (upsample 전) 박제로 wave 2 호출.
            keypoint_report_for_wave2 = keypoint_report_raw
            gemini_d_result = _call_wave2_keypoint_augmenter(
                local_video_path=local_video_path,
                low_uncertainty_frame_indices=low_uncertainty_indices,
                keypoint_report_2d=keypoint_report_for_wave2,
                scene_result=scene_result,
            )
            if gemini_d_result is not None and gemini_d_result.get("refined"):
                # 보강된 KeypointReport 박제 — frozen dataclass 정합.
                keypoint_report_raw = _apply_keypoint_refinement_to_report(
                    keypoint_report_raw, gemini_d_result
                )
                # upsample 재실행 — 18fps 박제.
                keypoint_report_obj = upsample_to_fps(
                    keypoint_report_raw, target_fps=18.0
                )

        keypoint_report_dict = (
            _dataclass_to_camel_case_dict(keypoint_report_obj)
            if keypoint_report_obj is not None
            else None
        )

        # ── Plan 04-01 Wave 1 (Phase 4) — Occlusion 합성 어댑터 호출 ──────────
        # R1 non-scoring 하드월: 본 분기는 KeypointReport / aiSynthesisMeta /
        # joints3d 흐름에만 흘러간다. DTW/kismam/IPSF 점수 산출은 이미 위에서
        # 1차 RTMW 원본 (inputs.keypoints_4ch) 로 완료된 상태 — coco_array mutate
        # 0 (B2 hard gate 정합, RESEARCH Pitfall 7).
        #
        # G4 가드: _call_synthesis_adapter 내부에서 is_reference=True 시
        # status="skipped" + ("g4_reference_guard",) 반환 — adapter 호출 0.
        # default OFF: SYNTHESIS_ENABLED env 미설정 시 status="skipped".
        ai_synthesis_meta_dict: dict | None = None
        try:
            from sunity_shared.analysis.synthesis.interfaces import (
                identify_occlusion_targets,
            )

            kp_4ch = inputs.keypoints_4ch
            if kp_4ch is not None and np.asarray(kp_4ch).ndim == 3:
                kp_arr = np.asarray(kp_4ch)
                # uncertainty_proxy (channel 3) → confidence ≈ 1 - uncertainty.
                synth_conf_in = np.clip(
                    1.0 - kp_arr[:, :, 3], 0.0, 1.0
                ).astype(np.float32)
                synth_joints_in = kp_arr[:, :, :3].astype(np.float32)
                occlusion_mask = identify_occlusion_targets(
                    synth_conf_in,
                    scene_result or {},
                    [],
                    threshold=0.3,
                )
                # G4 가드는 wrapper 가 처리. SYNTHESIS_ENABLED 게이트는 본
                # 호출 site 에서 — wrapper 가 invoke 하기 전에 skipped 결정.
                if not _synthesis_enabled() or is_reference_local:
                    from sunity_shared.analysis.synthesis.interfaces import (
                        SynthesisResult as _SR,
                    )

                    synth_result = (
                        _SR(
                            status="skipped",
                            warnings=("g4_reference_guard",),
                        )
                        if is_reference_local
                        else _SR(status="skipped")
                    )
                else:
                    adapter = _get_synthesis_adapter()
                    synth_result = _call_synthesis_adapter(
                        adapter=adapter,
                        joint_sequence=synth_joints_in,
                        confidence_sequence=synth_conf_in,
                        occlusion_mask=occlusion_mask,
                        scene_findings=scene_result,
                        is_reference=is_reference_local,
                    )
                # aiSynthesisMeta 만 채움 — joints/confidence 는 KeypointReport
                # 측 별도 wiring (후속 wave). DTW/kismam coco_array mutate 0.
                ai_synthesis_meta_dict = _build_ai_synthesis_meta(
                    synth_result,
                    synthesis_path="gemini_view"
                    if synth_result.status in ("applied", "partial")
                    else "none",
                )
        except Exception:  # noqa: BLE001 - 분석 흐름 차단 0
            log.exception(
                "synthesis wiring raise — graceful skip aiSynthesisMeta"
            )
            ai_synthesis_meta_dict = None

        # ── joints3d flat 박제 (R3 fix + BLOCKER-4) ─────────────────────────
        # source = inputs.keypoints_4ch[:, :, :3] (T, 17, 3 — 4ch uncertainty 제외).
        # to_coco17_array 산출이라 좌표계 = pole_aligned (BLOCKER-1 정정 —
        # rtmw3d 아님). 04-02 가 doc.result.joints3d 를 reshapePose3dData 로 소비.
        joints3d_flat: list[float] | None = None
        joints3d_keys_list: list[str] | None = None
        joints3d_frames_int: int | None = None
        coord_dim_int: int | None = None
        space_str: str | None = None
        try:
            kp_4ch = inputs.keypoints_4ch
            if kp_4ch is not None and np.asarray(kp_4ch).ndim == 3:
                src = np.asarray(kp_4ch)[:, :, :3].astype(np.float32)
                # NaN sentinel → 0.0 (validator 가 finite-only 강제, viewer 안전).
                src = np.nan_to_num(src, nan=0.0, posinf=0.0, neginf=0.0)
                joints3d_frames_int = int(src.shape[0])
                joints3d_keys_list = list(skeleton.KEYPOINT_NAMES)
                coord_dim_int = 3
                space_str = "pole_aligned"
                joints3d_flat = src.reshape(-1).tolist()
        except Exception:  # noqa: BLE001 - 분석 흐름 차단 0
            log.exception(
                "joints3d flat wiring raise — graceful skip joints3d 저장"
            )
            joints3d_flat = None

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
            force_pattern_inference=force_pattern_inference_dict,  # Phase 9 (Plan 09-02)
            recommended_exercises=recommended_exercises,  # Phase 13 (Plan 13-A, PERS-03)
            keypoint_report=keypoint_report_dict,  # Phase 12 Wave 0B (Plan 12-01)
            gemini_b=gemini_b_audit,  # Plan 17-04 Wave 3 (영역 B Coach audit)
            gemini_c=scene_result,  # Plan 17-02 Wave 1 (영역 C Finding flag)
            gemini_d=gemini_d_result,  # Plan 17-03 Wave 2 (영역 D Keypoint 보강)
            ai_synthesis_meta=ai_synthesis_meta_dict,  # Plan 04-01 Wave 1 (R3 fix)
            joints3d=joints3d_flat,  # Plan 04-01 Wave 1 (R3 fix flat)
            joints3d_keys=joints3d_keys_list,
            joints3d_frames=joints3d_frames_int,
            coord_dim=coord_dim_int,
            space=space_str,
        )
        log.info("분석 완료 uid=%s analysis_id=%s mode=%s", uid, analysis_id, mode)
    finally:
        # Plan 5-03 박제 — Gemini 어댑터 path 에서 신설한 임시 파일 정리.
        # delete=False NamedTemporaryFile 박제 정신 정합 — caller 책임 (B8 fix).
        # T-05-03-02 (DoS — 디스크 누수) 박제 — try/finally + missing_ok=True.
        # Plan 17-01 Task 4 (R-W6 정합) — B/C default ON 으로 모든 분석에서
        # keep_local_video=True 가 될 수 있음 → _safe_unlink_local_video 박제
        # (PermissionError 등 unlink 실패 시 log.warning + 분석 흐름 차단 0).
        _safe_unlink_local_video(local_video_path)
        # Phase 20 — Mode1 기준 영상 임시 파일 안전망 cleanup. 정상 경로는 veto 호출부
        # 내부 finally 가 이미 unlink+None 처리 (idempotent — None 이면 no-op). 다운로드~
        # veto 사이 예외 시에도 누수 0 (outer 초기화 → 항상 bound).
        _safe_unlink_local_video(reference_local_video_path)


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
