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

import contextlib
import dataclasses
import hashlib
import json
import logging
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor  # Phase 27 D-03 — 분석-로컬 prefetch
from enum import Enum
from pathlib import Path
from typing import Iterator, NamedTuple

import boto3  # Lambda 런타임 제공
import numpy as np

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import (
    assemble,
    body_normalizer,
    dimensions,
    kismam,
    safety_flags as safety_flags_mod,  # Phase 10 (Plan 10-02) — 결정론 부상 위험 신호
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
    max_split,
    split_angle_series,
)
from sunity_shared.analysis.interfaces import NoHumanError, NotPoleMotionError  # 가벼움 — 예외만
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
from sunity_shared.analysis.motion_alignment import build_motion_alignment  # Phase 28 (ALGN-01)
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
from sunity_shared.s3keys import build_coach_audio_key, parse_upload_key

# FfmpegFrameExtractor / NlfPoseEstimator / CerebrasCoachWriter 는 imageio·torch·
# requests 같은 무거운 의존성을 끌어옴. RunPod 위임 모드에선 사용하지 않으므로
# _ensure_adapters() 안에서 lazy import — Lambda 콜드스타트 절감 + 테스트가
# 어댑터 의존성 없이도 lambda_handler 디스패치를 검증할 수 있게 한다.

log = logging.getLogger()
log.setLevel(logging.INFO)


# ── Phase 27 SPD-01 — stage-timing 계측 (27-RESEARCH Pattern 6) ──────────────
# D-01 before/after 표의 데이터 소스 + D-02 진행률 재배분 실측 기반. 계측 없이는
# 레버 효과(152s vs 197s 의 ~45s 미계상)를 증명할 수 없다 — 모든 최적화 wave 의 전제.
# 계약 = analysis.ts `AnalysisResult.timingsMs?` + contract.md timingsMs 절
# (backend/audit 전용, 사용자 비노출). Python 정본은 본 helper 주석 (자유 키 dict —
# status enum 아님, models.py 상수 불필요).
#
# 순수 helper (boto3/네트워크 무의존 — unit test 가능). timings 는 flat dict[str, int]
# 만 누적 ([[firestore-nested-array-flat]] 정합). 로그는 %-lazy 구조 로그 —
# analysis_id/stage/elapsed_ms 만 (시크릿/영상 바이트/URL 금지, [[never-log-secrets]]).
@contextlib.contextmanager
def _stage(timings: dict[str, int], analysis_id: str, name: str) -> Iterator[None]:
    """단계 경계 elapsed(ms) 를 timings[name] 에 누적 + stage_timing 로그 방출.

    try/finally — stage 블록 안 예외가 나도 elapsed 를 기록한 뒤 예외를 전파한다
    (계측 실패/예외가 분석 흐름을 깨지 않게 하되, 부분 소요는 남긴다). 기존 분석
    로직은 이동 0 — 감싸기만 한다.
    """
    t0 = time.monotonic()
    try:
        yield
    finally:
        timings[name] = int((time.monotonic() - t0) * 1000)
        log.info(
            "stage_timing analysis_id=%s stage=%s elapsed_ms=%d",
            analysis_id,
            name,
            timings[name],
        )

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


def _student_frame_cache_enabled() -> bool:
    """학생 프레임 배열 재사용 캐시 게이트 (Phase 27 SPD-04 Task 3, 27-RESEARCH Pattern 7).

    RunPod Pod(대용량 RAM)에서는 ON — 9fps/640px 프레임(~190MB/영상)을 분석-로컬로 보존해
    still-pair/ fault_zoom 재추출을 소멸시킨다(디코딩 3회→1회). Lambda 폴백 경로
    (256MB~1GB, CPU NaN flow-only)에서는 `STUDENT_FRAME_CACHE=0` 로 비활성해 메모리 부담
    회피 — 기존 재추출 경로 유지(A5 OOM 방어). default ON(=1). Pod start_server.sh /
    Lambda template env 반영은 27-09(27-05 의 env 이중 박제 패턴 정합). 메모리 env 게이트라
    RunPod 자동 감지에 의존하지 않는다.
    """
    return os.environ.get("STUDENT_FRAME_CACHE", "1") != "0"


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


def _gemini_upload_prefetch_enabled() -> bool:
    """GEMINI_UPLOAD_PREFETCH 토글 (Phase 27 D-03/SPD-03, pipeline 단독 소유).

    박제 정신:
      · 단일 분석 내부 prefetch 겹치기(포즈 ∥ Gemini 업로드/scene_finder) on/off 레버.
      · default ON ("1") — "0"/"false"/"" 면 27-04 동기 경로 그대로 (canary/rollback,
        27-09 sweep 이 이 레버로 before/after 대조). 분석 간 SERIAL 불변 (executor 는
        분석-로컬, 모듈 전역 금지).

    Returns:
        True = prefetch 겹치기 ON. False = 동기 경로.
    """
    raw = os.environ.get("GEMINI_UPLOAD_PREFETCH", "1")
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
    preuploaded_handle: object | None = None,
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

        return find_scene_flags(
            local_video_path,
            is_reference=is_reference,
            preuploaded_handle=preuploaded_handle,
        )
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
    # [32-14 audit 판정 — 의도적 유지] KeypointReport 는 12관절로 확장됐지만
    # (elbow 존재), refined elbow 좌표의 **쓰기측 반영은 보수 유지 (None)**.
    # 신규 관절 좌표 덮어쓰기는 관절별 신뢰도 실측 게이트(2단) 뒤 재검토 —
    # augmenter 측 매핑 활성은 읽기(대조·mirror hint) 전용 (fail-safe).
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
    # Phase 27 SPD-04 (Task 3, 27-RESEARCH Pattern 7) — 학생 영상 9fps/640px 프레임
    # 배열 (T, H, W, 3) uint8. FfmpegFrameExtractor(9.0, 640) 산출을 분석-로컬 캐시로
    # 보존해 still-pair/ fault_zoom 재추출을 소멸시킨다(ffmpeg 디코딩 3회→1회). 동일
    # 파라미터 전제 — 파라미터가 다른 extract 호출이 생기면 이 캐시를 쓰지 말 것.
    # default None — 실경로(_extract_video_analysis_inputs_from_local)는 항상 채우고,
    # 기존 테스트 stub 은 미지정 시 None(캐시 비활성=재추출)으로 하위호환.
    frames: "np.ndarray | None" = None


def _download_analysis_video(
    bucket: str,
    key: str,
    *,
    timings_ms: dict[str, int] | None = None,
    analysis_id: str = "",
) -> str:
    """S3 에서 분석 영상을 로컬 임시 파일로 내려받고 경로 문자열을 반환한다.

    27-PLAN-REVIEW HIGH-1 — prefetch seam. 이 함수 반환 시점 = "다운로드 완료,
    포즈 미시작". 이 라인 뒤·`_extract_video_analysis_inputs_from_local`(프레임 추출/
    RTMW) 호출 앞이 Gemini prefetch 시작점(27-05 Task 2 — 겹치기 수확). delete=False
    NamedTemporaryFile — caller(또는 keep_local_video=False 분기) 가 unlink 책임.
    다운로드 예외 시 임시 파일 정리 후 raise (현행 계약 정합).
    """
    if timings_ms is None:
        timings_ms = {}
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        with _stage(timings_ms, analysis_id, "s3_download"):
            _s3.download_file(bucket, key, tmp_path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    return tmp_path


def _extract_video_analysis_inputs_from_local(
    local_video_path: str,
    default_pole: PoleAxis,
    *,
    keep_local_video: bool = False,
    timings_ms: dict[str, int] | None = None,
    analysis_id: str = "",
    unlink_on_error: bool = True,
) -> _VideoAnalysisInputs:
    """이미 로컬에 확보된 영상에서 frame_extract + RTMW estimate + 후처리를 수행한다.

    R3/R4 fix (Plan 06-02) — frame_extract + RTMW estimate 단 1회 실행 (T-06-02-06 —
    double RTMW 금지). `_download_analysis_video` 로 seam 분리됐지만 실행 순서·횟수
    불변 (다운로드 1 / 추출 1 / RTMW 1). student_profile 은 measure_body_profile 의
    fallback 보장으로 non-null (R4 fix). keep_local_video=True 시 local_video_path
    반환(caller 가 unlink 책임), False 시 추출 완료 후 unlink + local_video_path=None
    (기존 delete=True 의미론 보존). 추출/후처리 예외 시 임시 파일 unlink 후 raise.

    unlink_on_error (WR-02 fix, 27-REVIEW): 추출/후처리 **실패** 시 즉시-unlink 여부.
    prefetch 활성 caller(_process, 27-05)는 False 로 넘긴다 — 업로드 스레드가 같은
    파일을 읽는 중일 수 있어(선언 불변: future 생존 중 unlink 0) caller 가 future
    join(shutdown wait=True) **후** unlink 책임을 진다. 기본 True = 기존 계약 보존
    (prefetch 없는 caller 는 누수 0 즉시 정리).
    """
    _ensure_adapters()
    # Phase 27 SPD-01 — frame_extract / rtmw 단계 계측 (27-RESEARCH Pattern 6).
    # 기존 로직 이동 0 — 각 호출을 `_stage` 로 감싸기만.
    if timings_ms is None:
        timings_ms = {}
    try:
        with _stage(timings_ms, analysis_id, "frame_extract"):
            frames = _FRAME_EXTRACTOR.extract(local_video_path)
        with _stage(timings_ms, analysis_id, "rtmw"):
            pose_frames = _RTMW_ENGINE.estimate(frames, default_pole)

        # R4 fix — measure_body_profile 의 _fallback_profile 정합 (non-null 보장).
        student_profile = measure_body_profile(pose_frames)

        # angles 산출 — R6 정합 (to_coco17_array 4채널 보존).
        keypoints_4ch = to_coco17_array(pose_frames)
        angles = compute_joint_angles(keypoints_4ch)
        angles_filled = temporal_fill(angles, joint_uncertainty(keypoints_4ch))

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
    except Exception:
        # 추출/후처리 실패 — 임시 파일 누수 0 (현행 계약: keep 여부와 무관하게 정리).
        # WR-02 fix: prefetch caller 는 unlink_on_error=False 로 여기 즉시-unlink 를
        # 봉인하고 future join 후 스스로 unlink (업로드 스레드 read 중 unlink 레이스 0).
        if unlink_on_error:
            Path(local_video_path).unlink(missing_ok=True)
        raise

    if keep_local_video:
        local_video_path_out: Path | None = Path(local_video_path)
    else:
        # 기존 delete=True 의미론 보존 — 추출 후 즉시 정리 (frames 는 메모리 보유).
        Path(local_video_path).unlink(missing_ok=True)
        local_video_path_out = None

    return _VideoAnalysisInputs(
        angles=angles_filled,
        student_profile=student_profile,
        pose_frames=pose_frames,
        local_video_path=local_video_path_out,
        pole_axis_measurement=pole_axis_measurement,
        keypoints_4ch=keypoints_4ch,
        frames=frames,  # Phase 27 Task 3 — 학생 프레임 캐시 (재추출 소멸)
    )


def _extract_video_analysis_inputs(
    bucket: str,
    key: str,
    default_pole: PoleAxis,
    *,
    keep_local_video: bool = False,
    timings_ms: dict[str, int] | None = None,
    analysis_id: str = "",
) -> _VideoAnalysisInputs:
    """얇은 합성 wrapper (시그니처·반환 불변) — `_download_analysis_video` +
    `_extract_video_analysis_inputs_from_local` 순차 호출.

    27-05 부터 `_process` 는 이 wrapper 대신 2단 호출로 전환됐다(prefetch seam 확보).
    이 wrapper 는 외부 호출부(RunPod/기타) 호환 전용 — 기존 테스트 통과를 보장하지
    않는다(테스트는 2-함수 patch 로 마이그레이션됨). S3 download 1 / frame_extract 1 /
    RTMW estimate 1 — 분리 전후 호출 횟수 동일(T-06-02-06 불변).
    """
    local_video_path = _download_analysis_video(
        bucket, key, timings_ms=timings_ms, analysis_id=analysis_id
    )
    return _extract_video_analysis_inputs_from_local(
        local_video_path,
        default_pole,
        keep_local_video=keep_local_video,
        timings_ms=timings_ms,
        analysis_id=analysis_id,
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


def _reshape_prev_angles(prev: dict | None) -> np.ndarray | None:
    """이전 분석 영상의 flat angles 를 (T, J) 로 reshape — Phase 10 (Plan 10-02).

    Mode-3 safety_flags reference-anchor source. _mode3_comparison (app.py:2786-2788) 의
    idiom 재사용: num_joints = len(prev['anglesJointKeys'] or []) or skeleton.NUM_JOINTS.
    첫 Mode-3 영상(이전 baseline 없음) 또는 angles 부재 → None (reference-anchored 플래그
    graceful no-op). 어떤 입력 오류도 raise 하지 않는다.
    """
    if not isinstance(prev, dict):
        return None
    flat = prev.get("angles")
    if not flat:
        return None
    num_joints = len(prev.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    try:
        arr = np.asarray(flat, dtype=float)
        if arr.size == 0 or num_joints <= 0 or arr.size % num_joints != 0:
            return None
        return arr.reshape(-1, num_joints)
    except Exception:
        return None


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


def _build_selected_frame_pair(
    *,
    user_video_path: str | None,
    reference_video_path: str | None,
    reference_dtw_match,
    user_frame_idx: int,
    pose_frames=None,
    reference_pose_frames=None,
    cached_user_frames=None,
):
    """still 프레임 추출/정리 helper (D-10 HIGH-2) → SelectedFramePair | None.

    ref frame 은 fault_zoom._matched_ref_frame(DTW match)로 선택(DTW 재계산 금지). 추출
    프레임은 기존 FfmpegFrameExtractor(9fps/640px) 재사용. cleanup_paths = 생성된 로컬
    이미지 — 호출자 finally 가 unlink(Gemini File API delete 와 독립). graceful — 실패 시
    None (분석 흐름 차단 0).
    """
    from sunity_shared.analysis import fault_zoom, vision_veto

    if not user_video_path or not reference_video_path:
        return None
    cleanup: list[str] = []
    try:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        from PIL import Image

        ext = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
        # Phase 27 Task 3 — 학생 프레임 캐시 재사용(재추출 소멸). 동일 9fps/640px 파라미터
        # 전제라 byte-동일. 캐시 부재(Lambda 폴백/legacy) 시 기존 추출 경로 폴백. 기준
        # 영상은 캐시 타협(A5 메모리) — zoom 시점 추출 1회 유지.
        user_frames = (
            cached_user_frames if cached_user_frames is not None
            else ext.extract(user_video_path)
        )
        ref_frames = ext.extract(reference_video_path)
        u_n = int(user_frames.shape[0])
        r_n = int(ref_frames.shape[0])
        u_idx = max(0, min(int(user_frame_idx), u_n - 1)) if u_n else 0
        # DTW match 로 같은-pose 기준 프레임 (재계산 0).
        r_matched = fault_zoom._matched_ref_frame(reference_dtw_match, u_idx, r_n)
        r_idx = r_matched if r_matched is not None else (
            int(round(u_idx / max(1, u_n - 1) * (r_n - 1))) if (u_n > 1 and r_n > 1) else 0
        )
        # 선택 인덱스만 로컬 PNG 로 write.
        student_path = tempfile.NamedTemporaryFile(
            prefix="vveto_u_", suffix=".png", delete=False
        ).name
        ref_path = tempfile.NamedTemporaryFile(
            prefix="vveto_r_", suffix=".png", delete=False
        ).name
        cleanup.extend([student_path, ref_path])
        Image.fromarray(user_frames[u_idx]).convert("RGB").save(student_path)
        Image.fromarray(ref_frames[r_idx]).convert("RGB").save(ref_path)
        # keypoint 가시성/confidence — pose_frames 직접 추출(veto 전에 존재, fps 정합 단순).
        student_kp = _pose_frame_keypoints(pose_frames, u_idx)
        ref_kp = _pose_frame_keypoints(reference_pose_frames, r_idx)
        return vision_veto.SelectedFramePair(
            student_frame_path=student_path,
            reference_frame_path=ref_path,
            user_frame_idx=u_idx,
            ref_frame_idx=r_idx,
            student_keypoints=student_kp[0] if student_kp else None,
            reference_keypoints=ref_kp[0] if ref_kp else None,
            student_confidence=student_kp[1] if student_kp else None,
            reference_confidence=ref_kp[1] if ref_kp else None,
            cleanup_paths=tuple(cleanup),
            # provenance 판별 (quick 260705-h5z): DTW 매칭 성공 여부 — 소비자가
            # "dtw" 일 때만 이 pair 를 하이브리드 vision still 입력으로 쓴다.
            ref_match_source="dtw" if r_matched is not None else "ratio",
        )
    except Exception:  # noqa: BLE001 - still 추출 실패 graceful (보류 status 로 swallow)
        for p in cleanup:
            _safe_unlink_local_video(p)
        log.warning("SelectedFramePair 추출 실패 — None (graceful)")
        return None


def _pose_frame_keypoints(pose_frames, idx):
    """pose_frames[idx] 의 keypoints_3d + mean confidence (가시성 신호). 결측 → None.

    배선 버그 수정(24-06): PoseFrame 의 실제 필드는 keypoints_3d:
    dict[str, Keypoint3D] (key=COCO-17 관절명, value.confidence 0.0~1.0).
    과거 코드는 존재하지 않는 .keypoints 를 읽고 dict 를 list 처럼 순회해
    KEY(문자열)만 돌아 confidence 를 영영 못 읽었다 → mean_conf=None →
    student_confidence=None → alignment visibility=0.0 (전 클립) → local_ok 항상
    실패 → Gemini collect 가 low_alignment 로 bail. 이제 .values() 의
    confidence 평균을 읽는다.
    """
    if not pose_frames:
        return None
    try:
        if idx < 0 or idx >= len(pose_frames):
            return None
        pf = pose_frames[idx]
        kps = getattr(pf, "keypoints_3d", None)
        if kps is None and isinstance(pf, dict):
            kps = pf.get("keypoints_3d")
        # keypoints_3d 는 dict[str, Keypoint3D] — .values() 의 confidence 만 읽는다.
        values = kps.values() if isinstance(kps, dict) else (kps or [])
        confs = []
        for kp in values:
            c = getattr(kp, "confidence", None)
            if c is None and isinstance(kp, dict):
                c = kp.get("confidence")
            if c is not None:
                fc = float(c)
                if np.isfinite(fc):
                    confs.append(fc)
        mean_conf = sum(confs) / len(confs) if confs else None
        return (kps, mean_conf)
    except Exception:  # noqa: BLE001 - 가시성 산출 실패 graceful
        return None


def _collect_vision_fault_context(
    *,
    overall_score: int,
    dimension_scores: dict,
    mode: str | None,
    local_video_path: str | None = None,
    angles: np.ndarray | None = None,
    profile: "technique.TechniqueProfile | None" = None,
    reference_dtw_match=None,
    reference_angles=None,
    reference_video_path: str | None = None,
    keypoint_report=None,
    pose_frames=None,
    reference_pose_frames=None,
    preuploaded_student_handle=None,
    preuploaded_reference_handle=None,
    cached_user_frames=None,
) -> "vision_veto.VisionFaultContext":
    """Gemini 호출 소유자 (coach 전 1회, D-10 HIGH-1). keyword pre-build primitive 시그니처.

    result dict(score_result)를 받지 않는다 — numeric overall_score 가 build_result 이전
    (app.py:2442)에 가용하므로 build_result 를 앞당길 유인을 제거한다(D-12 MED-1). collect
    동작: (1) 부위별 worst 후보 selector + 글로벌+로컬 정렬 게이팅, (2) SelectedFramePair
    still 추출, (3) assess_fault_severity still-pair 호출 + support 게이트, (4) cap_would_apply
    = Gemini 이 coach-worthy (moderate/major) fault 를 짚었는지 — band-free coach-root-cause
    eligibility pointer; minor/none 미발화. (밴드 제거로 continuity 이며 과거 cap 산식과
    byte-동일 아님, HIGH-6), (5) VisionFaultContext(pre-apply/pre-coach) 반환 또는
    score-free collection_status.

    graceful — 어떤 실패도 분석 흐름 차단 0 (skipped_error/보류 status 로 swallow).
    """
    from sunity_shared.analysis import vision_veto, gemini_vision_scorer

    def _ctx(status, *, verdict=None, supported=None, root_causes=None,
             frame_pairs=None, alignment=None, telemetry=None, cap=False):
        return vision_veto.VisionFaultContext(
            collection_status=status,
            verdict=verdict,
            supported_differences=supported or [],
            root_cause_hypotheses=root_causes or [],
            selected_frame_pairs=frame_pairs or [],
            alignment=alignment or {},
            telemetry=telemetry or {},
            cap_would_apply=cap,
        )

    try:
        if not _gemini_vision_veto_enabled():
            return _ctx("disabled")
        if mode == models.MODE_SELF:
            return _ctx("mode3_held")
        if local_video_path is None:
            return _ctx("missing_current_video")
        if mode == models.MODE_EXPERT and reference_video_path is None:
            return _ctx("missing_reference")

        # (1) 부위별 worst 후보 + 정렬 게이팅.
        selection = vision_veto.select_worst_frame_candidates(profile)
        at = vision_veto.worst_pose_timestamp(profile)
        user_frame_idx = int(round((at or 0.0) * 9.0))  # 9fps 정합.
        pair = _build_selected_frame_pair(
            user_video_path=local_video_path,
            reference_video_path=reference_video_path,
            reference_dtw_match=reference_dtw_match,
            user_frame_idx=user_frame_idx,
            pose_frames=pose_frames,
            reference_pose_frames=reference_pose_frames,
            cached_user_frames=cached_user_frames,
        )
        visibility = 0.0
        if pair is not None and pair.student_confidence is not None:
            visibility = float(pair.student_confidence)
        alignment = vision_veto.assess_alignment_confidence(
            match=reference_dtw_match,
            selected_user_frame=user_frame_idx,
            keypoint_visibility=visibility,
        ) if reference_dtw_match is not None else {"adoption": "single"}
        alignment["selector_version"] = selection.get("selector_version")

        # 정렬 게이트 분리 (Phase 24 plan 06 = Option B1, belle 2026-06-29).
        # alignment 게이트는 frame "선택 품질"만 판단하게 하고, Gemini "실행 여부"와 분리한다.
        # 과거: low_alignment 면 Gemini 호출 전 무조건 bail(D-03 fabrication 선제 방어) →
        # 그런데 keypoint 신뢰도가 낮은 바로 그 동작(kip-up: 다리 keypoint 가 몸통으로 붕괴,
        # [[split-measurement-doesnt-discriminate-kipup]])에서 Gemini(픽셀 비전)를 꺼버려,
        # vision 이 가장 필요한 케이스에서 vision 이 차단되는 자기모순이었다. Gemini 는
        # keypoint 가 아니라 이미지를 본다 — keypoint 저신뢰여도 픽셀로는 비교 가능하다
        # (2026-06-29 검증: reference-anchored vision 6/6 fault<correct 변별, kip-up 포함).
        #
        # B1: frame-pair 를 골랐으면(pair 존재) low_alignment 여도 best-effort 로 Gemini 를
        # 돌린다. fabrication 방어는 pre-bail 이 아니라 **출력단 support 게이트**로 이동 —
        # assess_fault_context 가 canonical FaultKey + support count + 시각증거로 확증한
        # difference 만 채택(어긋난 프레임의 환각 difference 는 support 게이트가 drop). 객관성
        # 불변(사람 점수 라벨 0, [[analysis-objectivity-no-human-scores]]). alignment.adoption=
        # low_alignment_confidence 는 아래 모든 _ctx 반환에 그대로 실려 apply/audit 가
        # 저신뢰로 라벨한다(신규 필드 0). frame 조차 못 고르면(pair None) 비교 자체 불가 →
        # bail 유지. (rollback = 이 블록을 무조건 bail 로 되돌리면 됨.)
        if alignment.get("adoption") == "low_alignment_confidence" and pair is None:
            # 24-06 §3 진단 — alignment 텔레메트리 보존(collect-side drop 금지).
            return _ctx("low_alignment_confidence", frame_pairs=[], alignment=alignment)

        # (2/3) Gemini 호출 = **full-VIDEO reference-anchored part-wise fan-out** (Phase 24
        # close-out A, belle 2026-06-29). 과거 production 은 still-frame 1쌍(pair)을 fan-out 에
        # 넣었는데, dynamic/inverted 동작(kip-up)에서 단편 프레임이 결함 순간을 놓쳐 위양성을
        # 냈다(2026-06-29 A/B sweep: kip-up fault 99/100, vision eligible인데도 미검출,
        # [[kipup-fp-is-stillframe-vision-not-alignment-gate]]). full-video 입력은 Gemini 가
        # 영상 안에서 결함 순간을 직접 찾게 한다(spike 6/6 변별). _call_gemini_comparison
        # 프롬프트는 이미 "두 영상" 비교용이라 영상 입력이 더 정합. still-pair(pair)는 정량화/
        # fault-zoom 용으로만 ctx 에 실어 보낸다(frame_pairs) — 채점 결함은 영상에서 나온다.
        # canonical FaultKey + support 게이트 + root cause + telemetry(faultKeys/callCount) 보존.
        try:
            # at_seconds=None (Phase 24 close-out A, 2026-06-29): full-video 호출엔 worst-pose
            # 순간 hint 를 넘기지 않는다. 그 hint 는 still-FRAME 선택용(어느 프레임을 고를까)인데,
            # full-video 는 Gemini 가 전 구간을 훑어 결함 순간을 직접 찾아야 한다 — 단일 순간
            # hint 가 오히려 dynamic 결함(kip-up split)을 좁혀 놓친다. 실측 확정: pod 에서
            # at=None 6/6 moderate 검출 vs sweep at=worst_pose 1회 no_fault(그게 캐시 박힘).
            # 부수: at=None → 캐시 bucket='whole' → at-keyed poisoned 엔트리 우회.
            #
            # still 페어 = pair 재사용 (quick 260705-h5z, g1d 스코어러-측 추출 대체):
            # pair 는 자기 9fps 프레임 배열의 worst window median 인덱스(user_frame_idx)
            # + fault_zoom._matched_ref_frame DTW-매칭 인덱스(ref_frame_idx)로 만든
            # PNG 2장 — 시간비례 근사 still 은 측정 window 와 다른 동작 국면이라 위상
            # 불일치 페어를 만들고, Gemini 는 그걸 정당하게 "편차 없음" 판정한다
            # (2026-07-05 pod 진단 3회: 위상 불일치 0/6 vs window/DTW 인덱스 페어 6/6
            # 발화). 그래서 DTW-매칭("dtw") 페어만 still 로 보내고, 매칭 실패(ratio
            # 폴백) 또는 pair 부재 시 still 미전달 = upper scope video-only. PNG unlink
            # 는 아래 기존 finally 유지(assess 호출 후 정리 — 순서 불변).
            still_kwargs = {}
            if pair is not None and pair.ref_match_source == "dtw":
                still_kwargs = {
                    "still_student_png": pair.student_frame_path,
                    "still_reference_png": pair.reference_frame_path,
                    "still_frame_indices": [pair.user_frame_idx, pair.ref_frame_idx],
                }
            rich = gemini_vision_scorer.assess_fault_context_video(
                local_video_path,
                reference_video_path,
                at_seconds=None,
                part_scopes=list(gemini_vision_scorer.VETO_PART_SCOPES),
                preuploaded_student_handle=preuploaded_student_handle,
                preuploaded_reference_handle=preuploaded_reference_handle,
                **still_kwargs,
            )
        finally:
            # still 이미지(pair) unlink — vision 입력은 아니지만 quant/zoom 산출 후 outer 가
            # 쓰는 reference 영상과 독립. pair 정리는 여기서(생성처와 짝, D-10 HIGH-2).
            if pair is not None:
                for p in pair.cleanup_paths:
                    _safe_unlink_local_video(p)

        # still-pair 는 정량화/fault-zoom 용으로만 ctx 에 보존(vision 결함과 무관).
        pairs_for_ctx = [pair] if pair is not None else []
        telemetry = dict(rich.get("telemetry") or {})
        status = rich.get("status")
        if status == "resource_limited":
            # 예산 소진 fail-closed (Option A) — verdict 후보 금지.
            return _ctx("resource_limited", frame_pairs=pairs_for_ctx,
                        alignment=alignment, telemetry=telemetry)
        verdict = rich.get("verdict")
        if verdict is None or status != "candidate_verdict":
            return _ctx("skipped_error", frame_pairs=pairs_for_ctx,
                        alignment=alignment, telemetry=telemetry)
        if getattr(verdict, "severity", "none") == "none":
            return _ctx("no_fault", verdict=verdict, frame_pairs=pairs_for_ctx,
                        alignment=alignment, telemetry=telemetry)

        # cap_would_apply — band-free coach-root-cause eligibility pointer (HIGH-6,
        # severity-only): Gemini 이 coach-worthy(moderate/major) fault 를 짚었는지.
        cap_would_apply = getattr(verdict, "severity", "none") in ("moderate", "major")
        return _ctx(
            "candidate_verdict",
            verdict=verdict,
            supported=list(rich.get("supported_differences") or ()),
            root_causes=list(rich.get("root_cause_hypotheses") or ()),
            frame_pairs=pairs_for_ctx,
            alignment=alignment,
            telemetry=telemetry,
            cap=cap_would_apply,
        )
    except Exception:  # noqa: BLE001 - collect 실패는 분석 흐름 차단 0 (graceful)
        log.exception("vision fault context 수집 실패 — skipped_error (graceful)")
        return _ctx("skipped_error")


def _build_vision_quantification_result(
    *,
    fault_context=None,
    selected_frame_pair=None,
    current_measurements=None,
    reference_measurements=None,
    body_profile=None,
    pole_geometry=None,
    student_angles=None,
    reference_angles=None,
    baseline_kind: str = "hip_line",
    floor_y=None,
    pole_line=None,
):
    """post-geometry 정량화 named production seam (D-13 HIGH-1, 23-02 Task1/2/4 산출).

    파이프라인 순서: overall_score → collect → coach → build_result →
    _build_vision_quantification_result → apply. selected_frame_pair(그 프레임 keypoints +
    user/ref_frame_idx)로 FramePairMeasurementContext 를 구성해 결정적 칸(Task 2) +
    frame-specific 각도(Task 1)를 산출한다. **None 반환 금지** — 입력 결측/산출 실패 시
    VisionQuantificationResult(quantificationStatus="unavailable") 반환(D-11 MED-1).

    baseline_kind 기본 hip_line — 공중 동작 다수에서 엉덩이-라인 baseline 이 floor/pole_line
    입력 없이 keypoint 만으로 결정적 산출 가능(D-08). floor/pole_vertical 은 floor_y/pole_line
    입력이 있을 때 호출자가 지정.
    """
    from sunity_shared.analysis import vision_veto

    if selected_frame_pair is None:
        return vision_veto.VisionQuantificationResult(
            quantificationStatus="unavailable",
            warnings=["selected_frame_pair_missing"],
        )
    try:
        measurement = vision_veto.FramePairMeasurementContext(
            user_frame_idx=int(getattr(selected_frame_pair, "user_frame_idx", 0)),
            ref_frame_idx=int(getattr(selected_frame_pair, "ref_frame_idx", 0)),
            student_keypoints=getattr(selected_frame_pair, "student_keypoints", None),
            reference_keypoints=getattr(selected_frame_pair, "reference_keypoints", None),
            baseline_kind=baseline_kind,
            pole_line=pole_line,
            floor_y=floor_y,
            visibility=getattr(selected_frame_pair, "student_confidence", None),
        )
        return vision_veto.build_quantification_result(
            measurement=measurement,
            student_angles=student_angles,
            reference_angles=reference_angles,
        )
    except Exception:  # noqa: BLE001 - 정량화 산출 실패 graceful (unavailable, crash 0, D-11 MED-1)
        log.warning("정량화 산출 실패 — quantificationStatus=unavailable (graceful)")
        return vision_veto.VisionQuantificationResult(
            quantificationStatus="unavailable",
            warnings=["quantification_build_failed"],
        )


# ---------------------------------------------------------------------------
# Phase 24 (ND-01~07) — 투명 감점-합산 seam helpers.
#
# _baseline_kind_for_profile / _build_deduction_measured_deviations 는 _process 의
# 단일 채점 seam(분기 0, 코드 1벌)에서만 호출된다. 엔진(deduction_engine.tally)은
# technique profile 을 절대 받지 않으므로(BLOCKER B no-NameError), substrate 는 여기서
# 명명된 dict 로 한 번 만들어져 apply 경로에 keyword 로 threaded 된다(iter4 HIGH-1).
# ---------------------------------------------------------------------------

# 동작명(name/motion_id)으로 per-move baseline 을 정한다 (BLOCKER B). profile.category
# (flexibility/strength/spin/transition/unknown/unregistered)는 floor/aerial/horizontal 을
# 인코딩하지 않으므로 NAME 을 substring-match 한다. kip-up 류 = 바닥(floor), 깃발/수평 =
# 폴-수직(pole_vertical), 그 외/미상 = hip_line(정직한 기본 — keypoint 만으로 결정적, 공중/
# 역위 동작에 옳고 truly-unknown 에 유일하게 안전한 기본). 보편 per-move 주장 없음.
_FLOOR_MOVE_KEYWORDS = ("kip-up", "kip up", "kip_up", "킵업", "floor", "바닥", "ground")
_HORIZONTAL_MOVE_KEYWORDS = ("flag", "plank", "horizontal", "수평", "깃발")


def _baseline_kind_for_profile(profile) -> str:
    """technique profile → vision_veto.BASELINE_KINDS 멤버 (per-move, name 매칭, BLOCKER B).

    category 가 아닌 name/motion_id 를 case-insensitive substring 매칭한다(category 는
    floor/aerial 을 인코딩하지 않음). 매칭 없음/미상 → 'hip_line'(정직한 기본). kip-up 처럼
    NAMED 일 때만 floor 가 production 에서 발동 — 보편 per-move baseline 주장 아님(ND-05).
    """
    name = str(getattr(profile, "name", "") or "")
    motion_id = str(getattr(profile, "motion_id", "") or "")
    hay = f"{name} {motion_id}".lower()
    if any(k.lower() in hay for k in _FLOOR_MOVE_KEYWORDS):
        return "floor"
    if any(k.lower() in hay for k in _HORIZONTAL_MOVE_KEYWORDS):
        return "pole_vertical"
    return "hip_line"


def _build_deduction_measured_deviations(
    *, angles, profile, assessments, dimension_scores, quantification,
    reference_dtw_match=None, reference_angles=None, split_deficit_deg=None,
    vision_pointed_joints=None, seed_audit_out=None,
):
    """측정-기하 substrate(NAMED dict) — deduction_engine.tally 의 measured_deviations.

    HIGH-3 score-not-deviation safety: 0-100 dimension SCORE 를 deviation(deg/notch) 자리에
    절대 넣지 않는다. 각도 편차는 dimensions.extension_deviation(angles, profile)(관절별
    180° 부족분, deg, profile.expects_extension gated)에서만 뽑는다 — line_score 와 동일
    substrate(_select_window + extension deficit). reach 칸은 quantification.bodyRelativeNotches
    (student/reference notches 동반)를 forward 해 엔진이 insufficient-reach shortfall 을
    계산(HIGH-2)하게 한다.

    NAMED substrate 의도(score-not-deviation 안전):
      · extension_deficits_by_joint: 관절별 180° deg 부족분(extension_deviation, NOT 0-100 score).
        leg_extension(무릎 max) / arm_extension(팔꿈치 max) 로 묶어 md 에 방출.
      · line_deficit: 모든 EXTEND 관절 부족분 평균(line_score 와 동일 source, deg).
      · body_relative_notches: quantification.bodyRelativeNotches(student/reference 칸 동반).
    반환 키 (deduction_engine.tally md 계약 — criterion id 키):
      · leg_extension / arm_extension / line: ipsf_absolute deg deficit(없으면 키 부재 → honest 0).
      · split_angle: reference_relative — max(0, 정은지 max-split − 학생 max-split) deg.
        split_deficit_deg(mode1, peak inter-thigh 사이각) 보유 시만 방출, 없으면 honest 0.
      · body_relative_notches: quantification.bodyRelativeNotches list(있을 때만).
      · angle_vs_reference__{joint}: 24-07 ① + 25-01 — 정은지(reference) 대비 per-joint
        각도 편차(deg, reference_relative). reference_dtw_match+reference_angles 보유 시
        (mode1)만, expects_extension 미소유 관절에 한해 방출(미등록 동작 granular seed,
        §3-2). 25-01 관절 단위 2-source merge: vision_pointed_joints(Gemini 가 짚은 관절)
        ∩ quantification.windowMedianAngleDeltas 관절만 worst-window median 값(abs) 방출,
        Gemini-silent 관절은 기존 full-path DTW median 유지 — 260702-o0c(경로 either/or)
        FAIL 원인(silent 관절까지 window 편향 표집 → success 위양성)의 정확한 해소.
        pointed=None/빈(legacy/mode3) → 전 관절 DTW fallback (기존과 byte-동일, 무회귀).
      · seed_audit_out: dict 전달 시 {pointed, window_joints, fallback_joints} 기록
        (25-04 eval harness 구조 게이트 입력 — production 호출부는 미전달, 부작용 0.
        스키마/Firestore 계약 변경 0 — window 집계 출처는 로그+eval audit 로만 관측).
    """
    from sunity_shared.analysis import dimensions
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    md: dict = {}
    # ── 각도 편차 (deg) — extension_deviation 만(0-100 SCORE 금지, HIGH-3) ──
    if angles is not None and profile is not None:
        try:
            # 관절별 180° deg 부족분 벡터 (J,) — 0-100 dimension SCORE 아님(HIGH-3).
            extension_deficits_by_joint = dimensions.extension_deviation(angles, profile)
        except Exception:  # noqa: BLE001 — substrate 산출 실패는 honest 0(키 부재)
            extension_deficits_by_joint = None
        if extension_deficits_by_joint is not None:
            dev_vec = extension_deficits_by_joint

            def _max_dev(joint_names):
                vals = []
                for jk in joint_names:
                    if jk in JOINT_KEYS:
                        v = float(dev_vec[JOINT_KEYS.index(jk)])
                        if v == v:  # not NaN
                            vals.append(v)
                return max(vals) if vals else None

            leg = _max_dev(("left_knee", "right_knee"))
            if leg is not None and leg > 0.0:
                md["leg_extension"] = leg
            arm = _max_dev(("left_elbow", "right_elbow"))
            if arm is not None and arm > 0.0:
                md["arm_extension"] = arm
            # line_deficit = COLLECTIVE 180° deficit (line_score 와 동일 source) — 모든 EXTEND
            # 관절 부족분의 평균(deg). leg/arm 과의 cross-exclusion 은 엔진 union 이후.
            extend_devs = [
                float(dev_vec[JOINT_KEYS.index(jk)])
                for jk in JOINT_KEYS
                if profile.expects_extension(jk)
                and float(dev_vec[JOINT_KEYS.index(jk)]) == float(dev_vec[JOINT_KEYS.index(jk)])
            ]
            extend_devs = [d for d in extend_devs if d > 0.0]
            if extend_devs:
                line_deficit = sum(extend_devs) / len(extend_devs)
                md["line"] = line_deficit

    # ── reach 칸 — quantification.bodyRelativeNotches forward(student/reference 동반, HIGH-2) ──
    # 각 칸 항목은 student_notches/reference_notches/delta_notches 를 들고 있어 엔진이
    # insufficient-reach shortfall(max(0, reference−student−tol))을 직접 계산한다.
    notches = getattr(quantification, "bodyRelativeNotches", None)
    if notches:
        md["body_relative_notches"] = list(notches)

    # ── split — 객관 inter-thigh 사이각 부족분 seed (reference_relative, mode1) ──
    # split_deficit_deg = max(0, 정은지 max-split − 학생 max-split) (deg) — _process 에서
    # features.split_angle_series + max_split(peak)으로 산출(keypoints_4ch). 객관 180°
    # 강요 아님(belle over-EXTEND 위양성 회피, 15-SPLIT-MEASUREMENT-DESIGN §3). split_angle
    # criterion(reference_relative)이 소비: over = max(0, deficit − tol). None/0 → 미방출(honest 0).
    if split_deficit_deg is not None:
        d_split = float(split_deficit_deg)
        if d_split == d_split and d_split > 0.0:  # not NaN, 양수만
            md["split_angle"] = d_split

    # ── 24-07 ① + 25-01: reference-relative per-joint 각도 편차 seed (관절 단위 merge) ──
    # ipsf_absolute(extension) seed 가 빈 미등록 동작(인식기 미등재 → expects_extension 전부
    # False)에서, 정은지(reference) 대비 per-joint 각도 편차를 deduction 엔진 seed 로 주입한다.
    # 편차는 모두 DEG (0-100 score 아님 — HIGH-3 score-not-deviation 정합).
    #
    # 25-01 관절 단위 2-source merge (260702-o0c 경로 either/or 의 정확한 해소):
    #   · jk ∈ vision_pointed_joints(Gemini 가 짚은 관절) AND jk ∈ wm_by_joint →
    #     worst-window median 값(abs) 방출 — kip-up 어깨 Δ40° 처럼 국소 결함이 전체
    #     DTW path median 에서 tol 미만으로 희석되던 "표시는 40° 인데 감점 0" 해소.
    #   · 그 외(Gemini-silent / wm 결측 / pointed=None 빈) → 기존 full-path DTW median
    #     (per_joint_deviation) 유지 — silent 관절까지 window 편향 표집하면 RTMW jitter/
    #     촬영거리 노이즈가 감점으로 증폭돼 success 위양성(260702-o0c FAIL 실증).

    def _emit_reference_relative(jk, v) -> bool:
        """양 경로 공통 방출 규칙 — seed-stage cross-exclusion(§3-2) 포함.

        profile.expects_extension(jk) 관절은 ipsf_absolute(leg/arm/line)가 이미 채점하므로
        reference_relative 미방출(double-count 금지). line(collective)도 expects_extension
        파생이므로 이 gate 가 정확히 차단 — 엔진-stage 는 leg/arm/split 만 보증.
        JOINT_KEYS 외 문자열은 skip(엔진 md 계약은 criterion id 키만 기대 — spurious 금지)."""
        if jk not in JOINT_KEYS:
            return False
        if v != v or v <= 0.0:  # NaN/0/음수 미방출(md 슬림 — 엔진 tol gate 가 self-compare 0 도 거름)
            return False
        if profile is not None and profile.expects_extension(jk):
            return False
        md[f"angle_vs_reference__{jk}"] = v
        return True

    # 1. window 측정치 파싱 — {joint: abs(delta_deg)} (SIGNED→magnitude, f513587 패턴).
    #    NaN/0/형상불량 entry 는 wm_by_joint 미등재 → 그 관절은 DTW fallback 으로 강하.
    wm_by_joint: dict = {}
    wm = getattr(quantification, "windowMedianAngleDeltas", None)
    wm_deltas = wm.get("deltas") if isinstance(wm, dict) else None
    for entry in wm_deltas or ():
        if not isinstance(entry, dict):
            continue  # 형상불량 entry 는 honest skip
        try:
            _jk = entry.get("joint")
            _v = abs(float(entry.get("delta_deg", 0.0)))
        except (TypeError, ValueError):
            continue
        if _jk in JOINT_KEYS and _v == _v and _v > 0.0:
            wm_by_joint[_jk] = _v

    # 2. DTW fallback 편차 — 기존 per_joint_deviation 1회 계산 (honest skip 유지).
    dtw_by_joint: dict = {}
    if reference_dtw_match is not None and reference_angles is not None and angles is not None:
        try:
            path = getattr(reference_dtw_match, "path", None)
            start = getattr(reference_dtw_match, "start", None)
            end = getattr(reference_dtw_match, "end", None)
            if path and start is not None and end is not None:
                # 점수경로(_deviation_against)와 동일 인덱싱: user_seg = angles[start:end],
                # path 는 그 segment local 인덱스. 재계산은 path 순회만(저비용).
                user_seg = angles[start:end]
                dev = per_joint_deviation(path, user_seg, reference_angles)
                for i, jk in enumerate(JOINT_KEYS):
                    dtw_by_joint[jk] = float(dev[i])
        except Exception:  # noqa: BLE001 — 형상 mismatch/예외는 honest skip(reference_relative 미방출)
            dtw_by_joint = {}

    # 3. 관절 단위 선택 — pointed ∩ wm 만 window, 나머지 전부 DTW (pointed=None/빈 → 전 관절 DTW).
    pointed = tuple(vision_pointed_joints or ())
    window_joints: list = []
    fallback_joints: list = []
    for jk in JOINT_KEYS:
        if jk in pointed and jk in wm_by_joint:
            if _emit_reference_relative(jk, wm_by_joint[jk]):
                window_joints.append(jk)
        elif jk in dtw_by_joint:
            if _emit_reference_relative(jk, dtw_by_joint[jk]):
                fallback_joints.append(jk)

    # 4. 관찰 가능성 — 어느 경로가 감점 seed 를 만들었는지 로그 + eval audit 만
    #    (contract/Firestore 스키마 불변 — record source 는 기존 geometry 표기 유지).
    if window_joints or fallback_joints:
        log.info(
            "angle_vs_reference seed pointed=%d window=%d fallback=%d",
            len(pointed), len(window_joints), len(fallback_joints),
        )
    if isinstance(seed_audit_out, dict):
        seed_audit_out["pointed"] = list(pointed)
        seed_audit_out["window_joints"] = list(window_joints)
        seed_audit_out["fallback_joints"] = list(fallback_joints)

    return md


def _apply_vision_veto(
    score_result: dict,
    local_video_path: str | None = None,
    angles: np.ndarray | None = None,
    profile: "technique.TechniqueProfile | None" = None,
    mode: str | None = None,
    reference_video_path: str | None = None,
    *,
    vision_fault_context=None,
    quantification=None,
    measured_deviations=None,
    baseline_kind: str = "hip_line",
) -> dict:
    """v2 비전 채점 seam — reference-anchored 투명 감점-합산 (Phase 24 ND-01, 밴드 제거).

    belle 결정: **Mode1 비교 앵커 + Mode3 보류**.
      · Mode1 (MODE_EXPERT) — 학생 영상을 코치 reference 영상과 **비교**해 측정대상 짚기
        (Gemini) + 측정 편차 감점(deduction_engine.tally). 진공 단일 영상 판정은 mild fault
        와 정타를 구별 못 해 위양성/위음성을 냄 — 비교가 원칙적 fix.
      · Mode3 (MODE_SELF) — **보류**. 고정 reference 가 없음 (본인 영상 비교). 절대
        차원 + 이전 영상 델타가 그대로 성립 → veto 미실행 (mode3_held).

    Phase 24: severity→고정천장 밴드 제거. overallScore = deduction_engine.tally(측정편차 →
    명시규칙 감점 → 합산).final. seam-built measured substrate(measured_deviations) + per-move
    baseline_kind 가 keyword 로 threaded(엔진은 profile 미수신, BLOCKER B). criterion 선택은
    엔진의 criteria_for_fault 라우터(severity 미사용, ND-02). visionVeto.status 가 채점 실행을
    증명(부재 ≠ 실행, HIGH-1).

    status enum (TRUST-08, 무음실패 방지 — Pitfall 5):
      · disabled            — _gemini_vision_veto_enabled() OFF (adapter 미호출)
      · mode3_held          — mode==MODE_SELF (belle 보류 — reference 없음)
      · missing_local_video — local_video_path None (graceful, HIGH-1)
      · missing_reference   — Mode1 인데 reference 영상 부재 (진공 판정 안 함, graceful)
      · skipped_error       — adapter None(키부재/실패) → graceful + WARNING
      · not_applicable      — tally 가 돌았으나 측정 감점/located criterion 0 (점수 불변)
      · applied             — 측정 감점 적용 (overallScore = tally final)

    mode=None (back-compat) — 단일 영상 진공 판정 경로 유지 (기존 호출/테스트 보존).

    토글은 pipeline 단독 소유 (iter2 MEDIUM-1) — 어댑터는 토글 미참조.
    """
    import sunity_shared.models as models  # lazy — mode 상수 비교

    # ── context 제공 시 Gemini 미호출 — verdict 재사용 + deduction tally + audit (D-10 HIGH-1) ──
    if vision_fault_context is not None:
        return _apply_vision_veto_from_context(
            score_result, vision_fault_context, quantification,
            measured_deviations=measured_deviations, baseline_kind=baseline_kind,
        )

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
        from sunity_shared.analysis import deduction_engine  # lazy — pure, no adapter

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
        # Phase 24 (iter4 HIGH-2) — LEGACY 단일-영상 Gemini 경로: quantification 도
        # 명명 substrate 도 없다(plain VisionVerdict). deduction_engine.tally 에
        # quantification=None → quantification-unavailable fallback(final=dimension_overall,
        # ONE traceable record, NO band, NO criteria_for_fault). 명명 substrate 미빌드.
        breakdown = deduction_engine.tally(
            None, None,
            dimension_overall=score_result["overallScore"],
            measured_deviations=None,
            dimension_scores=score_result.get("dimensionScores"),
            baseline_kind=baseline_kind,
        )
        # 결함이 있는 verdict(none 아님)면 applied audit + tally final. 결함 없음(none)은
        # not_applicable(점수 = dimension_overall fallback, 변동 없음).
        if getattr(verdict, "severity", "none") != "none":
            fault_joints = vision_veto.fault_joints_from_differences(
                verdict.differences
            )
            fault_deficits = vision_veto.fault_joint_deficits_from_differences(
                verdict.differences
            )
            vision_veto_audit = {
                "status": "applied",
                "severity": verdict.severity,
                "tallyFinal": breakdown.final,
                "primaryFault": verdict.primary_fault,
            }
            if fault_joints:
                vision_veto_audit["faultJoints"] = fault_joints
            if fault_deficits:
                vision_veto_audit["faultJointDeficits"] = fault_deficits
            return {
                **score_result,
                "overallScore": breakdown.final,
                "deductionBreakdown": breakdown.to_dict(),
                "visionVeto": vision_veto_audit,
            }
        # 결함 없음(none) — 점수 불변(fallback final == dimension_overall).
        return _veto_passthrough(score_result, "not_applicable")
    except Exception:  # noqa: BLE001 - 비전 hook 실패는 분석을 막지 않는다 (graceful)
        log.exception(
            "vision veto hook 실패 — score_result 그대로 통과 (graceful, skipped_error)"
        )
        return _veto_passthrough(score_result, "skipped_error")


def _apply_vision_veto_from_context(
    score_result: dict, ctx, quantification,
    *, measured_deviations=None, baseline_kind: str = "hip_line",
) -> dict:
    """context 제공 경로 — Gemini 미호출, verdict 재사용 + deduction tally + to_audit_dict (D-12 HIGH-1).

    Phase 24 (ND-01/ND-02, iter5 HIGH-1): severity→고정천장 밴드 제거 — collect 가
    산출한 VisionFaultContext 를 deduction_engine.tally 로 채점한다(seam-built measured
    substrate + baseline_kind keyword threaded, profile 미전달 BLOCKER B). criterion 선택은
    엔진의 criteria_for_fault 라우터(body_part/fault_state)가 하고 severity 는 읽지 않는다.

    TALLY-ELIGIBLE status = {candidate_verdict, no_fault, low_alignment_confidence}.
    no_fault(Gemini 정타, 정렬·정량화 가용)는 더 이상 passthrough 가 아니다 —
    supported_differences 가 비어 있어도 measured seed(criteria_from_measured_deviations)가
    측정 편차로 감점할 수 있다(Gemini-silent 방어). low_alignment_confidence(정렬 신뢰도
    낮음 — collect 가 Gemini 호출 전 bail) 도 24-04(Option A, belle 2026-06-26)부터
    tally-eligible 이다: RTMW 측정 편차(extension deficit + body-relative notch)는 student↔
    reference DTW 정렬에 독립인 객관 측정값이므로, Gemini 정렬이 낮아도 측정 가능한 기하 편차는
    감점해야 한다. ctx.supported_differences 가 비어 있어(collect-side bail) criteria_for_fault
    는 아무 것도 더하지 않는다 — Gemini-located fault 는 부재(위양성 fabricate 금지,
    objectivity [[analysis-objectivity-no-human-scores]]). 기하가 깨끗하면 not_applicable
    (final 불변). 그 외 비측정 status 는 score-free passthrough 그대로.
    geminiCallCount=1(collect 만 호출, apply 재호출 0).

    29-02 (D-01/D-02/D-03): mode3_held 도 md(ipsf_absolute measured seed) 보유 시
    tally 를 실행해 deductionBreakdown 을 방출한다 — 단 status 는 'mode3_held' 를
    유지한다(vision 비교는 여전히 보류라는 진실 신호). md 빈 dict 는 기존 passthrough
    (미방출 + 점수 byte-불변). production 노출은 29-05 sweep 게이트 후.
    """
    from sunity_shared.analysis import vision_veto
    from sunity_shared.analysis import deduction_engine  # lazy — pure, no adapter

    try:
        status = ctx.collection_status
        # tally-eligible: candidate_verdict(Gemini 결함) / no_fault(정타지만 measured seed 가
        # 감점 가능 — iter5 HIGH-1) / low_alignment_confidence(정렬 낮음이지만 RTMW 측정 편차는
        # 정렬-독립 — 24-04 Option A). 그 외 status 는 측정 불가 → score-free passthrough.
        if status not in ("candidate_verdict", "no_fault", "low_alignment_confidence"):
            # 29-CONTEXT D-01/D-02 — mode3_held tally-eligible (24-04 Option A 이식).
            # mode3 는 고정 reference 가 없어 vision 비교는 계속 보류 — status 는
            # 'mode3_held' 유지('applied' 재사용 금지: result.tsx vetoApplied 파생 의미
            # 오염 방지, RESEARCH Pattern 1 옵션 a). 그러나 md(ipsf_absolute measured
            # seed — RTMW 절대 각도, 등록 동작 profile-gated)는 reference 무관 측정이므로
            # md 가 비어있지 않으면 deduction_engine.tally 로 투명 감점-합산을 방출한다
            # (Gemini 추가 호출 0). md 빈 dict(미등록 + 빈 criteria 4동작)는 아래
            # passthrough 그대로 — 기준 없는 감점 0=100 위양성 차단(D-03). production
            # 노출은 29-05 sweep 게이트 통과 후 Pod 재기동 시점(D-02 전환 조건).
            if status == "mode3_held" and measured_deviations:
                try:
                    # vision frame-pair 정량화(quantification)는 mode3 에 존재하지
                    # 않는다. 그러나 tally 의 quantification-unavailable 폴백(contract
                    # §10.5)은 "양쪽 substrate 빔"(측정 자체 불가) 전용 — mode3 는 md
                    # substrate 가 실재하므로 폴백이 아니라 measured-seed 산술을 태운다.
                    # in-process 전용 status sentinel 로 폴백 게이트를 우회(이 객체는
                    # 저장/방출 경로에 실리지 않음). 이로써 clean md(전 편차 tolerance
                    # 이내)도 mode1 no_fault clean 선례(260630-l4e)와 동일하게
                    # records 0 → final 100 이 방출된다.
                    mode3_quant = vision_veto.VisionQuantificationResult(
                        quantificationStatus="mode3_measured_seed",
                        angleDeltas=None, bodyRelativeNotches=None,
                        windowMedianAngleDeltas=None, warnings=(),
                    )
                    breakdown = deduction_engine.tally(
                        mode3_quant, None,
                        dimension_overall=score_result["overallScore"],
                        measured_deviations=measured_deviations,
                        dimension_scores=score_result.get("dimensionScores"),
                        baseline_kind=baseline_kind,
                    )
                    # fallback-only(측정 불가) 방어 — sentinel 로 도달 불가하지만
                    # 명시 불변식으로 유지(D-03 자연 방어 + D-02 무회귀 산술 보장).
                    if breakdown.fallback != "quantification_unavailable":
                        log.info(
                            "mode3 tally 방출 records=%d final=%s baseline_kind=%s",
                            len(breakdown.records), breakdown.final, baseline_kind,
                        )
                        return {
                            **score_result,
                            "overallScore": breakdown.final,
                            "deductionBreakdown": breakdown.to_dict(),
                            "visionVeto": {"status": "mode3_held"},
                        }
                except Exception:  # noqa: BLE001 - mode3 tally hook 실패는 분석 차단 0
                    log.exception(
                        "mode3 tally 실패 — mode3_held passthrough (graceful)"
                    )
            passthrough_map = {
                "resource_limited": "resource_limited",
                "disabled": "disabled",
                "mode3_held": "mode3_held",
                "missing_reference": "missing_reference",
                "missing_current_video": "missing_local_video",
                "skipped_error": "skipped_error",
            }
            final = passthrough_map.get(status, "skipped_error")
            audit = {"status": final}
            telem = ctx.telemetry or {}
            if final == "resource_limited" and telem:
                audit["telemetry"] = {
                    k: telem.get(k)
                    for k in ("completedCalls", "plannedCalls", "samplingComplete")
                    if k in telem
                }
            return {**score_result, "visionVeto": audit}

        # ── candidate_verdict / no_fault / low_alignment_confidence — deduction tally
        # (seam-built substrate) ── low_alignment 은 measured seed 만 점화(supported_differences
        # 비어 criteria_for_fault 부재) — Gemini fault fabricate 0(24-04 Option A).
        quant = quantification
        if quant is None:
            quant = vision_veto.VisionQuantificationResult(
                quantificationStatus="unavailable",
                angleDeltas=None, bodyRelativeNotches=None,
                windowMedianAngleDeltas=None, warnings=["quantification_absent"],
            )
        # ctx 가 supported_differences + FaultKey 를 운반 → 엔진이 criteria_for_fault 로
        # 라우팅(candidate_verdict). no_fault 는 supported_differences 가 비어 measured seed
        # 만 활성화(Gemini-silent 방어). 엔진은 technique profile 을 받지 않는다(HIGH-2).
        breakdown = deduction_engine.tally(
            quant, ctx,
            dimension_overall=score_result["overallScore"],
            measured_deviations=measured_deviations,
            dimension_scores=score_result.get("dimensionScores"),
            baseline_kind=baseline_kind,
        )
        # 측정 감점 record 가 있으면 applied(final<dimension_overall 가능). 없으면 not_applicable
        # (측정 감점 0 AND Gemini-located criterion 0 — 점수 불변). TRUST-08 무음실패 방지:
        # fallback record 만 있는 경우(quantification unavailable)도 applied 로 추적된다.
        has_deduction = bool(breakdown.records)
        if has_deduction:
            verdict = ctx.verdict
            audit = ctx.to_audit_dict(
                final_status="applied", breakdown_final=breakdown.final,
                quantification=quant,
            )
            # faultJoints/Deficits 부착 (verdict.differences 기반; no_fault 면 비어 부재).
            fault_joints = vision_veto.fault_joints_from_differences(
                getattr(verdict, "differences", ()) or ()
            )
            fault_deficits = vision_veto.fault_joint_deficits_from_differences(
                getattr(verdict, "differences", ()) or ()
            )
            if fault_joints:
                audit["faultJoints"] = fault_joints
            if fault_deficits:
                audit["faultJointDeficits"] = fault_deficits
            return {
                **score_result,
                "overallScore": breakdown.final,
                "deductionBreakdown": breakdown.to_dict(),
                "visionVeto": audit,
            }
        # tally 가 돌았으나 측정 감점/located criterion 0 → not_applicable(점수 불변).
        # 24-06 §3 진단 — to_audit_dict 를 거치지 않는 직접 dict 이므로 동일 alignment 요약을
        # ctx.alignment 에서 직접 붙인다(관찰 메타데이터, score 무관). low_alignment bail 의
        # 발화 조건(distance/visibility/localPathCount)을 not_applicable 경로에서도 캡처.
        na_audit = {"status": "not_applicable"}
        _align = vision_veto.alignment_summary(getattr(ctx, "alignment", None))
        if _align is not None:
            na_audit["alignment"] = _align
        # Phase 24 — not_applicable 도 breakdown.final 이 authoritative(측정 기하 clean →
        # final=100). 레거시 min-of-core dimension passthrough 제거
        # ([[scoring-must-be-transparent-deduction-tally]], [[score-spec-95-100-elite-vision-fix]]).
        # quant-unavailable 은 applied 경로(fallback record)라 불변.
        return {
            **score_result,
            "overallScore": breakdown.final,
            "deductionBreakdown": breakdown.to_dict(),
            "visionVeto": na_audit,
        }
    except Exception:  # noqa: BLE001 - context apply 실패도 분석 차단 0 (graceful)
        log.exception("vision veto context apply 실패 — passthrough (skipped_error)")
        return _veto_passthrough(score_result, "skipped_error")


# kismam joint key(result.joints[].key) → 앱이 강조하는 keypoint 이름.
# 손은 elbow 의 시각 proxy (KeypointOverlay JOINT_KEY_TO_ANGLE_KEY 역방향 정합).
_KISMAM_TO_KEYPOINT = {
    "left_elbow": "left_hand",
    "right_elbow": "right_hand",
    "left_shoulder": "left_shoulder",
    "right_shoulder": "right_shoulder",
    "left_hip": "left_hip",
    "right_hip": "right_hip",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
}


def _keypoint_deltas(joints: list) -> dict[str, float]:
    """result.joints(kismam key + deltaDeg) → {keypoint 이름: abs deficit deg}.

    fault-zoom 의 deficit 숫자 마커 + 편차 top 폴백 source. deltaDeg 없는 관절 skip.
    """
    out: dict[str, float] = {}
    for j in joints or ():
        kp = _KISMAM_TO_KEYPOINT.get(str((j or {}).get("key", "")))
        if kp is None:
            continue
        dd = (j or {}).get("deltaDeg")
        if dd is None:
            continue
        try:
            out[kp] = abs(float(dd))
        except (TypeError, ValueError):
            continue
    return out


def _render_fault_zoom(
    result: dict,
    user_video_path: str,
    right_video_path: str,
    user_report: dict,
    right_report: dict,
    fault_joints: list[str],
    deficits: dict[str, float],
    kinds: dict[str, str],
    worst: float | None,
    uid: str,
    analysis_id: str,
    bucket: str,
    dtw_match=None,
    user_frame_idx: int | None = None,
    ref_frame_idx: int | None = None,
    *,
    dtw_ref_fps: float | None = None,
    advisory_joints: list[str] | None = None,
    advisory_deltas: dict[str, float] | None = None,
    split_angle_degs: tuple[float | None, float | None] | None = None,
    split_angle_present: bool = False,
    cached_user_frames=None,
) -> list[dict]:
    """fault-zoom 공용 코어 — 프레임 추출 → crop 합성 → S3 업로드 → comparisons 리스트.

    Phase 27 SPD-04 (D-06) — 사후 분리로 전환하며 반환을 result 부착 대신 comparisons
    list[dict] 반환으로 변경(호출측이 update_analysis_fault_zoom 로 사후 부착). `result`
    인자는 결함/편차 read 용으로만 유지(사후 mutation 금지 — D-03 경계).

    Mode1(right=정은지) / Mode3(right=지난 영상) 공용. 한글 캡션/라벨은 앱이 부여
    (이미지엔 숫자만). graceful 은 호출측 try 가 담당.
    user_frame_idx/ref_frame_idx: 9fps frames 인덱스 override (quick-260702-sic) —
    vision 측정 프레임(sourceFrameIndices median)과 crop 프레임 정합. None=기존 경로.
    dtw_ref_fps (CR-01): dtw_match.path 의 ref 인덱스가 사는 fps 공간. None=r_rep_fps
    (mode1 = 정은지 ref doc, byte-identical). Mode3 는 prev angles fps(=9fps)를 명시
    (_build_mode3_fault_zoom_comparisons) — prev keypointReport 18fps 오독 방지.
    advisory_joints/advisory_deltas (quick-260704-fz4): 측정 초과("참고·확인 권장")
    관절 — 별도 배치로 tier='advisory' 카드 생성. None/빈 리스트 = 기존 경로 100%
    보존 (Mode3 _build_mode3_fault_zoom_comparisons 은 default None 무접촉). 채점 무접촉 —
    카드 생성·방출만 ([[window-median-silent-seed-fp-reverted]]).
    split_angle_degs (quick-260705-r6x): legs(스플릿) 카드의 (학생 각도, 기준 각도)
    수치 — 호 옆 표기용. None=수치 생략(선+호만). Mode3 는 default None.
    split_angle_present (quick-260705-wbs): 게이트 A — split_angle criterion 이 실제
    있는 confirmed 배치에만 True. advisory("측정 초과·확인 권장")는 확정 스플릿
    결함이 아니므로 항상 False(사이각 미드로잉). Mode3 도 default False(honest 생략).
    """
    from sunity_shared.analysis import fault_zoom
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    if not fault_joints:
        return []
    ext = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
    # Phase 27 Task 3 — 학생(user) 프레임 캐시 재사용(재추출 소멸). 동일 9fps/640px
    # 파라미터라 byte-동일. 캐시 부재(Lambda 폴백/legacy) 시 추출 폴백. 기준/지난
    # 영상(right)은 캐시 타협 — zoom 시점 추출 1회 유지(A5 메모리).
    user_frames = (
        cached_user_frames if cached_user_frames is not None
        else ext.extract(user_video_path)
    )
    right_frames = ext.extract(right_video_path)
    comps = fault_zoom.build_fault_zoom_comparisons(
        user_frames,
        right_frames,
        user_report,
        right_report,
        worst,
        fault_joints,
        deficits,
        frames_fps=9.0,
        joint_kinds=kinds,
        dtw_match=dtw_match,
        dtw_ref_fps=dtw_ref_fps,
        user_frame_idx=user_frame_idx,
        ref_frame_idx=ref_frame_idx,
        split_angle_degs=split_angle_degs,
        split_angle_present=split_angle_present,
        # D-11/D-12 (Phase 31-03) — 확정 결함 카드에만 목표 각도 화살표. 생략 규칙
        # (ref 대응 실패/미선언 관절/저신뢰/parity 불명/미세 delta)은 전부 fault_zoom
        # 안에 있다. 채점 무접촉 — 렌더 전용.
        draw_arrows=True,
    )
    # advisory 배치 (quick-260704-fz4) — 프레임 추출은 위 1회 재사용. joint_kinds
    # 'deficit' 은 좌+우 grouping(arms 1장) 활성용 내부 전달일 뿐, 방출 item 에는
    # kind 를 싣지 않는다 (앱 캡션이 "부족해요" 확정 어조로 오인 방지 — tier 가
    # 캡션을 소유). select_advisory_joints cap=2 로 캐러셀 과밀 방지.
    adv_comps: list[dict] = []
    if advisory_joints:
        adv_comps = fault_zoom.build_fault_zoom_comparisons(
            user_frames,
            right_frames,
            user_report,
            right_report,
            worst,
            list(advisory_joints),
            advisory_deltas or {},
            frames_fps=9.0,
            joint_kinds={j: "deficit" for j in advisory_joints},
            dtw_match=dtw_match,
            dtw_ref_fps=dtw_ref_fps,
            user_frame_idx=user_frame_idx,
            ref_frame_idx=ref_frame_idx,
            split_angle_degs=split_angle_degs,
            # advisory("측정 초과·확인 권장")는 확정 스플릿 결함이 아니므로 사이각을
            # 그리지 않는다(게이트 A) — 확정 어조 오인 방지. tier 가 캡션 소유.
            split_angle_present=False,
            # 화살표도 같은 이유로 미드로잉 — "여기까지 올려야 함"은 확정 지시라
            # advisory("측정 초과·확인 권장") 카드에 얹으면 어조가 뒤집힌다.
            draw_arrows=False,
        )
    out: list[dict] = []
    for tier, batch, key_prefix in (
        ("confirmed", comps, "zoom_"),
        # advisory 는 S3 키 분리(zoom_adv_) — 확정 카드와 충돌 원천 차단.
        ("advisory", adv_comps, "zoom_adv_"),
    ):
        for c in batch:
            skey = f"results/{uid}/{analysis_id}/{key_prefix}{c['joint']}.png"
            _s3.put_object(
                Bucket=bucket, Key=skey, Body=c["png"], ContentType="image/png"
            )
            item = {
                "joint": c["joint"],
                "deficitDeg": c.get("deficitDeg"),
                "imageUrl": _signed_get(bucket, skey),
                # 2단 시각 언어 tier (quick-260704-fz4) — scalar str 이라
                # _validate_dict_only_scalars flat 제약 통과. TS lockstep:
                # FaultZoomComparison.tier ('confirmed'|'advisory', 부재=legacy
                # doc=confirmed 취급).
                "tier": tier,
            }
            if tier == "confirmed" and c.get("kind"):
                item["kind"] = c["kind"]
            # 결함단위 grouping 카드 (quick-260702-sic) — scalar str 이라
            # _validate_dict_only_scalars flat 제약 통과. TS lockstep:
            # FaultZoomComparison.region ('legs'|'arms').
            if c.get("region"):
                item["region"] = c["region"]
            # HIGH-1 (28-05) — refMatch provenance pass-through (D-04). scalar str 이라
            # _validate_dict_only_scalars flat 제약 통과. region 선례와 동일 조건부
            # 복사 — 부재(legacy 형상)면 최종 item 에도 키 부재. TS lockstep:
            # FaultZoomComparison.refMatch ('dtw'|'failed', 부재=legacy=캡션 없음).
            if c.get("refMatch") in ("dtw", "failed"):
                item["refMatch"] = c["refMatch"]
            # 리뷰 B-01 (Phase 31-03) — DTW 대응 프레임 쌍 pass-through. int/bool
            # scalar 라 _validate_dict_only_scalars flat 제약 통과. 2D 비교 뷰어
            # (amended D-10)가 "내 자세 어느 프레임 ↔ 목표 어느 프레임"을 중첩하는
            # 정합 소스. TS lockstep: analysis.ts FaultZoomComparison 의 optional
            # userFrameIdx/refFrameIdx/refMatched — **계약 반영은 31-04 담당**
            # (부재=legacy doc=뷰어 미표시). region/refMatch 선례와 동일 조건부 복사.
            if isinstance(c.get("userFrameIdx"), int):
                item["userFrameIdx"] = c["userFrameIdx"]
            if isinstance(c.get("refFrameIdx"), int):
                item["refFrameIdx"] = c["refFrameIdx"]
            if isinstance(c.get("refMatched"), bool):
                item["refMatched"] = c["refMatched"]
            out.append(item)
    # Phase 27 SPD-04 (D-06) — result 부착 대신 comparisons 반환 (사후 update 경로).
    return out


def _build_fault_zoom_comparisons(
    result: dict,
    user_video_path: str | None,
    ref_video_path: str | None,
    user_report: dict | None,
    ref_report: dict | None,
    profile,
    uid: str,
    analysis_id: str,
    bucket: str,
    dtw_match=None,
    cached_user_frames=None,
) -> list[dict]:
    """Mode1 결함 부위 확대 비교 — 학생 vs 정은지. kind='deficit'(기준보다 부족).

    belle 2026-06-21 ([[fault-zoom-compare-and-phase24-true3d]]). 결함 관절 = veto
    faultJoints 우선, 없으면 편차 top-2. deficit = Gemini 시각 추정 우선/kismam 폴백.

    Phase 27 SPD-04 (D-06) — comparisons list[dict] 반환(사후 update 경로). `result` 는
    결함/편차 read 전용(사후 mutation 금지). 대상 부재/무결함 → 빈 리스트.
    cached_user_frames (Task 3): 학생 프레임 캐시 재사용(재추출 소멸) — _render_fault_zoom
    로 pass-through.
    """
    if not user_video_path or not ref_video_path or not user_report or not ref_report:
        return []
    from sunity_shared.analysis import vision_veto

    vv = result.get("visionVeto") or {}
    joint_deltas = _keypoint_deltas(result.get("joints") or [])
    fault_joints = list(vv.get("faultJoints") or [])
    # deficit 숫자: veto 결함은 Gemini 시각 추정(faultJointDeficits) 우선, 그 외는
    # kismam delta. Gemini 추정이 veto 결함을 의미있게 반영(kismam 은 못 잡아 과소).
    gemini_deficits = vv.get("faultJointDeficits") or {}
    deficits = {**joint_deltas, **{k: float(v) for k, v in gemini_deficits.items()}}
    from sunity_shared.analysis import fault_zoom as _fz

    # crop 프레임 = vision 측정 window (quick-260702-sic). 캡션의 deficit 는
    # windowMedianAngleDeltas 가 측정한 프레임 window 에서 왔으므로 crop 도 그
    # window 내 멤버 관절 평균 confidence 최대 프레임 (부재 시 median 폴백,
    # quick-260705-ftn — 측정-표시 정합은 window 안에서 유지하면서 keypoint
    # 붕괴 프레임 회피, user/ref 각각 독립 선택).
    # 인덱스 공간 = 9fps frames 배열과 동일 — angles 행 = 9fps 추출 프레임
    # (build_keypoint_report(pose_frames, fps=9.0) 동일 소스, _selected_frame_pair
    # 의 u_idx/r_idx 가 frames 인덱스로 window_median 에 그대로 전달됨,
    # vision_veto.py:486 정합). fault_joints 가 vv.faultJoints 에서 온 경우에만
    # 적용 — 편차 top-2 폴백 경로는 vision 측정 프레임과 무관(기존 worst_seconds).
    # 부재/legacy doc → None = 기존 동작 (하위호환).
    user_frame_idx: int | None = None
    ref_frame_idx: int | None = None
    if fault_joints:
        sfi = (vv.get("windowMedianAngleDeltas") or {}).get("sourceFrameIndices") or {}
        u_list = sfi.get("user") or []
        r_list = sfi.get("reference") or []
        if u_list and r_list:
            try:
                user_frame_idx = _fz.select_confident_frame(
                    user_report, u_list, fault_joints
                )
                ref_frame_idx = _fz.select_confident_frame(
                    ref_report, r_list, fault_joints
                )
            except (TypeError, ValueError):
                user_frame_idx = ref_frame_idx = None
    if not fault_joints:
        # veto 미적용(각도 차원이 결함을 잡은 경우) — 편차 최대 keypoint top-2 폴백.
        fault_joints = [
            k for k, _ in sorted(joint_deltas.items(), key=lambda kv: -kv[1])[:2]
        ]
    if not fault_joints:
        return []
    kinds = {j: "deficit" for j in fault_joints}
    # advisory("측정 초과·확인 권장") 카드 배선 (quick-260704-fz4, CONTEXT locked).
    # windowMedianAngleDeltas(veto applied 에서만 존재 — Mode1 전용) 의 kismam
    # angle key 를 _KISMAM_TO_KEYPOINT 로 keypoint 매핑 후, 확정(fault_joints)
    # 제외 + tol 초과만 선별. tol = dimensions._LINE_TOL_DEG(20°) 재사용 — 신규
    # 튜닝 상수 0, IPSF 허용오차 단일 출처 (앱 KeypointOverlay.
    # KEYPOINT_DELTA_HIGHLIGHT_DEG 와 정합). deltas 부재/legacy → advisory 빈
    # 리스트 → 기존 산출과 동일 (하위호환). 채점/veto/게이트 무접촉 — 표시 전용
    # ([[window-median-silent-seed-fp-reverted]]).
    from sunity_shared.analysis import dimensions as _dims

    kp_wm_deltas: dict[str, float] = {}
    for d in (vv.get("windowMedianAngleDeltas") or {}).get("deltas") or []:
        kp = _KISMAM_TO_KEYPOINT.get(str((d or {}).get("joint", "")))
        dd = (d or {}).get("delta_deg")
        if kp is None or dd is None:
            continue
        try:
            kp_wm_deltas[kp] = float(dd)
        except (TypeError, ValueError):
            continue
    advisory = _fz.select_advisory_joints(
        kp_wm_deltas, set(fault_joints), _dims._LINE_TOL_DEG
    )
    advisory_deltas = {kp: abs(kp_wm_deltas[kp]) for kp in advisory}
    # 스플릿(legs) 사이각 수치 = 점수가 쓴 split_angle record 중 벌림각 semantics
    # 인 ipsf_absolute(measuredValue=추정 학생 벌림각)만 — 학생 측 표기, 기준 측은
    # 항상 생략(baselineValue 180 은 IPSF 목표치지 정은지 실측각이 아님). 현행
    # split_vs_reference(reference_relative, vision-주입 kip-up 포함)는 measured
    # 가 편차라 표기하면 오독 → 수치 생략, 선+호만 (belle pod PNG 검증 2026-07-05
    # fix: 학생 라벨=deficit 50°/기준 라벨=0° 오표기). 채점 무접촉 — display 전용.
    _records = (result.get("deductionBreakdown") or {}).get("records")
    split_degs = _fz.split_angle_degs_from_records(_records)
    # 게이트 A(quick-260705-wbs): split_angle criterion 이 records 에 있을 때만 legs
    # 사이각을 그린다. 존재 판정(split_present)과 수치(split_degs)를 분리 — kip-up
    # reference_relative 는 measuredValue 가 편차라 수치는 None 이지만 사이각 자체는
    # 의미 있어 선+호를 그려야 하므로 has_split_angle_record 로 게이트만 연다.
    split_present = _fz.has_split_angle_record(_records)
    return _render_fault_zoom(
        result, user_video_path, ref_video_path, user_report, ref_report,
        fault_joints, deficits, kinds,
        vision_veto.worst_pose_timestamp(profile),
        uid, analysis_id, bucket,
        dtw_match=dtw_match,
        user_frame_idx=user_frame_idx,
        ref_frame_idx=ref_frame_idx,
        advisory_joints=advisory,
        advisory_deltas=advisory_deltas,
        split_angle_degs=split_degs,
        split_angle_present=split_present,
        cached_user_frames=cached_user_frames,  # Phase 27 Task 3 — 학생 재추출 소멸
    )


# 29-CONTEXT D-08 — mode3 zoom 대상 매핑: 감점 record criterion id → region.
# DeductionRecord 는 keypoint 필드를 나르지 않으므로(29-PLAN-REVIEW HIGH-1) record
# 에서 관절을 읽지 않고 criterion id 로 region 을 파생한다. 이 표는 29-04 앱 helper
# (deductionLabels.ts projectDeductionRecordKeypoints) 매핑과 항목 동일해야 record 행
# ↔ zoom 카드 드릴다운 매칭(result.tsx:962-974, REGION_MEMBER_KEYPOINTS 교집합)이
# 성립한다 — 측당 1벌, cross-side 일치가 D-08 수용 기준.
# line · dimension_overall_fallback · 기타 미등록 id 는 의도적 미등록: line 은
# collective 전신 criterion(joint_keys 빈 튜플)이라 특정 부위 카드가 오도
# (29-04 앱 무투영 결정과 정합).
_MODE3_ZOOM_CRITERION_REGION: dict[str, str] = {
    "leg_extension": "legs",
    "split_angle": "legs",
    "arm_extension": "arms",
}

# region 카드 멤버 keypoint — 앱 REGION_MEMBER_KEYPOINTS(deductionLabels.ts:90-96)
# 미러, keypointReport 8-keypoint 이름공간. 좌+우 동일-kind 멤버를 넘기면
# fault_zoom._group_fault_joints 의 기존 region 카드 경로(_REGION_JOINTS 부분집합)
# 가 카드 1장으로 묶는다 — 렌더러 무접촉 재사용.
_MODE3_ZOOM_REGION_MEMBERS: dict[str, tuple[str, ...]] = {
    "legs": ("left_hip", "right_hip", "left_knee", "right_knee"),
    "arms": ("left_shoulder", "right_shoulder", "left_hand", "right_hand"),
}


def _build_mode3_fault_zoom_comparisons(
    result: dict,
    user_video_path: str | None,
    user_report: dict | None,
    prev: dict | None,
    profile,
    uid: str,
    analysis_id: str,
    bucket: str,
    cached_user_frames=None,
    dtw_match=None,
) -> list[dict]:
    """Mode3 감점 부위 확대 비교 — 현재 vs 지난 영상. kind='deficit' 만.

    29-CONTEXT D-08 — zoom 대상 = 이번 분석 deductionBreakdown 감점 record 의
    criterion id → region 매핑(_MODE3_ZOOM_CRITERION_REGION). 구 |Δscore| top-2
    (현재↔지난 per-joint score 차, improved/worsened) 소스는 폐기 — mode1 줌과
    동일 개념(이번 분석 결함 부위만). improved(개선 부위 축하 카드)는 deferred:
    어떤 경로에서도 방출하지 않는다. 지난 영상은 prev.result.myVideoKey 로 S3
    다운로드(임시, 종료 후 정리).

    Phase 27 SPD-04 (D-06) — comparisons list[dict] 반환(사후 update 경로). `result` 는
    deductionBreakdown read 전용(사후 mutation 금지). 감점 record 부재 → 빈 리스트.
    """
    if not user_video_path or not user_report or not prev:
        return []
    prev_result = prev.get("result") or {}
    prev_report = prev_result.get("keypointReport")
    prev_video_key = prev_result.get("myVideoKey")
    if not prev_report or not prev_video_key:
        return []

    # 감점 record criterion → region 파생 (같은 region 중복 record = 카드 1장 dedupe,
    # 순서 = record 등장 순, 카드 수 상한 = 현행 top-2 유지).
    records = (result.get("deductionBreakdown") or {}).get("records") or []
    regions: list[str] = []
    for rec in records:
        region = _MODE3_ZOOM_CRITERION_REGION.get(str((rec or {}).get("criterion", "")))
        if region is not None and region not in regions:
            regions.append(region)
    regions = regions[:2]
    if not regions:
        # 29-CONTEXT D-08 — 감점 record 없으면 zoom 카드 없음 = 의도된 동작
        # (4/5 빈 criteria 동작 자연 귀결 + line 등 비매핑 criterion 뿐인 경우 포함).
        return []
    fault_joints = [j for r in regions for j in _MODE3_ZOOM_REGION_MEMBERS[r]]
    kinds = {j: "deficit" for j in fault_joints}

    from sunity_shared.analysis import vision_veto

    prev_video_path: str | None = None
    try:
        ext = os.path.splitext(prev_video_key)[1] or ".mp4"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.close()
        # 29 리뷰 WR-04 — download 전에 경로 바인딩. download_file 예외 시에도
        # finally 의 _safe_unlink_local_video 가 delete=False 임시파일을 정리한다
        # (종전엔 성공 후 할당이라 실패 반복 시 장수명 Pod 에 빈 파일 누적 —
        # T-05-03-02 "delete=False 는 caller 책임 정리" 규율).
        prev_video_path = tmp.name
        _s3.download_file(bucket, prev_video_key, prev_video_path)
        # Mode3 는 split_angle_present 기본 False(게이트 A) — 기준이 사용자 지난
        # 영상이라 도립 pose 대칭 문제로 사이각을 안전 생략(quick-260705-wbs).
        return _render_fault_zoom(
            result, user_video_path, prev_video_path, user_report, prev_report,
            fault_joints, {}, kinds,  # mode3 = 숫자 없음(region 카드, kind='deficit')
            vision_veto.worst_pose_timestamp(profile),
            uid, analysis_id, bucket,
            # 28-05 가 시간비례 근사를 제거(D-04) — mode3 도 DTW 대응으로 같은-pose
            # 프레임 (전신 폴백 회귀 방지). prev 부재/first = None → 기존 경로 무접촉.
            dtw_match=dtw_match,
            # CR-01 — mode3 prev_dtw_match path 의 ref 인덱스는 prev 사용자 doc 의
            # angles 공간(파이프라인 저장 fps)이다. prev keypointReport 는 18fps 로
            # upsample 저장되므로 dtw_ref_fps 를 명시하지 않으면 ref angles(9fps)를
            # 18fps report 공간으로 오독해 절반 시각 프레임/좌표를 확대한다(D2 재현).
            # _pipeline_frame_fps() = frame_extractor target_fps 단일 출처(리터럴 금지).
            dtw_ref_fps=_pipeline_frame_fps(),
            cached_user_frames=cached_user_frames,  # Phase 27 Task 3 — 학생 재추출 소멸
        )
    finally:
        _safe_unlink_local_video(prev_video_path)


def _run_deferred_fault_zoom(
    *,
    render,
    uid: str,
    analysis_id: str,
) -> None:
    """complete_analysis 이후 zoom 렌더 → update_analysis_fault_zoom 부분 업데이트.

    Phase 27 SPD-04 (D-06) — 점수/verdict/감점 내역은 이미 complete(status='done')됐고,
    zoom PNG 는 표현물이라 여기서 렌더해 사후 도착시킨다(time-to-first-result 단축).
    분석은 이미 complete 이므로 어떤 경로도 재raise 하지 않는다(부가 기능 비차단 규율):

      · render() 성공 → done + comparisons(빈 리스트 허용 — 무결함 = 카드 없음, 고아 아님).
      · render() 예외 → failed(빈 리스트) + log.warning (앱은 카드 자리 숨김).
      · failed write 자체 실패 → log.exception 만 — 앱은 pending 고아 상태가 될 수 있으나
        27-07 의 시간 상한 폴백이 방어한다(T-27-17, 주석 박제).

    Args:
      render: () -> list[dict] — _build_fault_zoom_comparisons /
        _build_mode3_fault_zoom_comparisons 를 감싼 thunk (인자 바인딩은 caller).
    """
    try:
        comparisons = render()
        firestore_admin.update_analysis_fault_zoom(
            uid, analysis_id, comparisons or [],
            status=models.FAULT_ZOOM_STATUS_DONE,
        )
    except Exception:  # noqa: BLE001 - 부가 기능 실패는 분석 비차단 (graceful)
        log.warning(
            "fault-zoom 사후 렌더 실패 — failed 마킹 시도 (분석은 이미 complete) "
            "uid=%s analysis_id=%s", uid, analysis_id,
        )
        try:
            firestore_admin.update_analysis_fault_zoom(
                uid, analysis_id, [], status=models.FAULT_ZOOM_STATUS_FAILED,
            )
        except Exception:  # noqa: BLE001 - failed write 실패 = pending 고아 가능
            # 앱 27-07 시간 상한 폴백이 방어 (분석은 이미 complete 이므로 재raise 0).
            log.exception(
                "fault-zoom failed 마킹 write 실패 — pending 고아 가능 "
                "(앱 27-07 시간 상한 폴백 방어) uid=%s analysis_id=%s",
                uid, analysis_id,
            )


# ═══════ Phase 32 (Plan 32-16, D-18 B안) — 재생 중 큐 오디오 (Polly 사후 합성) ═══════
#
# B안(클라우드 TTS) 확정 (32-GATE-DECISIONS §샘플 게이트): records 의 cueLine
# (승인 문구집 32-05 골격 — D-09 무수치, **문구 변경 금지** = 텍스트 그대로 합성)을
# 분석 **사후** 스테이지에서 AWS Polly(neural)로 합성해
# S3 results/{uid}/{analysisId}/coach_audio_{recordId}.mp3 (s3keys 단일 출처)로
# 저장하고 result.coachAudio 를 부분 갱신한다. 채점·verdict 무접촉 — complete 이후
# 표현물 도착 (fault_zoom 사후 분리 선례). 키의 recordId = cueId 조인 (32-12
# audioCue prefetch). 실패는 전부 graceful (SP-3 — 자막 경로 무영향).
#
# 음성/엔진 = env 우선 (POLLY_VOICE_ID / POLLY_ENGINE) — Pod env 만으로 재배포 없이
# 스왑 가능하게 설계 (32-16 Task 4 belle 청취 게이트 대비). 기본값 Seoyeon neural 은
# belle 확정 전 **잠정** (32-GATE-DECISIONS §샘플 게이트 부속 — 확정 후 기본값 고정).
_POLLY_VOICE_ID = os.environ.get("POLLY_VOICE_ID", "").strip() or "Seoyeon"
_POLLY_ENGINE = os.environ.get("POLLY_ENGINE", "").strip() or "neural"
_POLLY_CLIENT = None


def _get_polly_client():
    """Polly 클라이언트 lazy 싱글턴 — RunPod 위임 Lambda/합성 미사용 경로 무부담.

    신규 시크릿 0 — Lambda IAM(template.yaml polly:SynthesizeSpeech) / Pod
    sunity-motion 자격증명(기존 env)을 그대로 사용. 리전은 자격증명 기본 리전
    (ap-northeast-2 — Pod AWS_DEFAULT_REGION / Lambda 함수 리전).
    """
    global _POLLY_CLIENT
    if _POLLY_CLIENT is None:
        _POLLY_CLIENT = boto3.client("polly")
    return _POLLY_CLIENT


def _synthesize_coach_audio_items(
    cue_records: list[dict], uid: str, analysis_id: str, bucket: str
) -> list[dict]:
    """cueLine 보유 records 를 Polly 합성 → S3 저장 → items 반환 (record 단위 격리).

    합성/업로드 실패는 그 record 만 생략 (log.warning — 부분 성공은 성공분만
    items 로, 앱은 item 없는 큐를 자막만으로 재생). 텍스트는 문구집 cueLine
    그대로 — 변형 0 (D-09 골격 소유권). 로그에 본문/시크릿 미기록.
    """
    items: list[dict] = []
    for rec in cue_records:
        record_id = rec["recordId"]
        try:
            resp = _get_polly_client().synthesize_speech(
                Text=rec["cueLine"],
                VoiceId=_POLLY_VOICE_ID,
                Engine=_POLLY_ENGINE,
                LanguageCode="ko-KR",
                OutputFormat="mp3",
            )
            audio_bytes = resp["AudioStream"].read()
            key = build_coach_audio_key(uid, analysis_id, record_id)
            _s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=audio_bytes,
                ContentType="audio/mpeg",
            )
            items.append({"recordId": record_id, "key": key})
        except Exception:  # noqa: BLE001 - record 1건 실패는 그 record 만 (격리)
            log.warning(
                "coach_audio 합성 실패 — 해당 record 생략 "
                "uid=%s analysis_id=%s record_id=%s",
                uid, analysis_id, record_id,
            )
    return items


def _run_deferred_coach_audio(
    *,
    result: dict,
    uid: str,
    analysis_id: str,
    bucket: str,
) -> None:
    """complete_analysis 이후 큐 오디오 합성 → update_analysis_coach_audio 부분 갱신.

    D-18 (32-GATE-DECISIONS B안) — 분석은 이미 complete(status='done')라 어떤 경로도
    재raise 하지 않는다 (_run_deferred_fault_zoom 뼈대 복제):

      · 합성 (부분)성공 또는 합성할 큐 없음 → done + items (빈 리스트 허용 —
        결함 0/전부 fail-closed = 재생할 오디오 없음. 부재(legacy doc)와 구분).
      · cueLine 보유 records 가 있는데 전부 실패 → failed(빈 리스트) — IAM/Polly
        전면 장애를 done+[] 로 위장하지 않는다 (스윕이 검출 가능해야 함).
      · 스테이지 예외 → failed(빈 리스트) + log.warning (앱은 자막만 — SP-3).
      · failed write 자체 실패 → log.exception 만 (앱은 coachAudio 부재 = 미도착).

    **동기 채점 경로 호출 금지** — 사후 전용 (속도 예산·timingsMs 회귀 0).
    """
    try:
        breakdown = result.get("deductionBreakdown")
        records = breakdown.get("records") if isinstance(breakdown, dict) else None
        if not isinstance(records, list):
            records = []
        # cueLine 부재(fail-closed 조합 — 32-05)는 오디오 대상 아님 (자막도 없음).
        cue_records = [
            r for r in records
            if isinstance(r, dict)
            and isinstance(r.get("recordId"), str) and r.get("recordId")
            and isinstance(r.get("cueLine"), str) and r.get("cueLine")
        ]
        items = _synthesize_coach_audio_items(cue_records, uid, analysis_id, bucket)
        status = (
            models.COACH_AUDIO_STATUS_FAILED
            if cue_records and not items
            else models.COACH_AUDIO_STATUS_DONE
        )
        firestore_admin.update_analysis_coach_audio(
            uid, analysis_id, items, status=status
        )
    except Exception:  # noqa: BLE001 - 부가 기능 실패는 분석 비차단 (graceful)
        log.warning(
            "coach_audio 사후 스테이지 실패 — failed 마킹 시도 (분석은 이미 complete) "
            "uid=%s analysis_id=%s", uid, analysis_id,
        )
        try:
            firestore_admin.update_analysis_coach_audio(
                uid, analysis_id, [], status=models.COACH_AUDIO_STATUS_FAILED,
            )
        except Exception:  # noqa: BLE001 - failed write 실패 = coachAudio 미도착
            log.exception(
                "coach_audio failed 마킹 write 실패 — coachAudio 부재 유지 "
                "uid=%s analysis_id=%s", uid, analysis_id,
            )


# ═══════ Phase 32 (Plan 32-13, D-22/D-23) — 감점 카드 문장↔영상 스팟체크 ═══════
#
# 분석이 방출한 감점 카드 문장(statusLine/cueLine)과 summaryPraise.headline(백엔드
# 방출 단일 원천 — 앱이 렌더하는 바로 그 문장, 리뷰 blocker 5)을 분석 **사후**
# 스테이지에서 프레임과 대조하고, 명백 불일치(mismatch) record 만 hiddenRecordIds
# 로 부분 갱신한다 — 앱이 해당 카드를 표면에서 숨긴다("틀린 말을 내보내느니 안
# 보여줌", D-23). 채점·verdict·tally 무접촉 (판정 권한 = 숨김만, T-32-30).
# **동기 채점 경로 호출 금지** — 사후 전용 (phase 27 1분대 속도 예산 구조 보호,
# 동기 경로 신규 외부 호출 0). 실패 전부 graceful (SP-3 — 완료 분석 무훼손).

# 프레임 서브셋 인코딩 파라미터 — 분석에 이미 쓰인 9fps/640px 프레임을 그대로
# JPEG 재인코딩만 한다 (재추출/재디코딩 0). 스모크 실측 60KB/장 × ≤8장 ≈ ≤0.5MB.
_SPOTCHECK_JPEG_QUALITY = 85


def _build_spot_check_video_ref(
    judged_records: list,
    angles,
    profile,
    frames,
) -> list[dict]:
    """스팟체크 프레임 서브셋 — hold window 균등 대표 프레임 (record 당 최대 2).

    window 근거: 감점 record 의 절대-기준 측정(extension/split/line)은 전부
    dimensions._select_window hold window 에서 이뤄진다(_hold_window_median_dict
    와 동일 소스 공유 — 별도 window 계산 금지, drift 방지). record 별 개별 시간
    창은 계약에 존재하지 않으므로 "record 당 최대 2" 는 프레임 예산 산술로
    구현한다: 총 프레임 = clamp(2×판정 record 수, SPOTCHECK_MIN_FRAMES..MAX).
    판정 record 0건(praise 만 검수)이어도 최소 예산으로 프레임을 공급한다.

    실패는 빈 리스트 반환 (호출측 run_spot_check 가 'skipped' no-op — SP-3).
    """
    from sunity_shared.analysis import spot_check as spot_check_mod

    try:
        if frames is None:
            return []
        arr = np.asarray(frames)
        if arr.ndim != 4 or arr.shape[0] < 1:
            return []
        total = int(arr.shape[0])

        # hold window — 측정과 동일 소스 (dimensions._select_window 공유).
        try:
            _, (ws, we) = dimensions._select_window(np.asarray(angles, dtype=float), profile)
            ws = max(0, min(int(ws), total - 1))
            we = max(ws + 1, min(int(we), total))
        except Exception:  # noqa: BLE001 - window 실패 = 전 구간 폴백 (graceful)
            ws, we = 0, total

        budget = max(
            spot_check_mod.SPOTCHECK_MIN_FRAMES,
            min(
                spot_check_mod.SPOTCHECK_MAX_FRAMES,
                spot_check_mod.SPOTCHECK_FRAMES_PER_RECORD
                * max(1, len(judged_records)),
            ),
        )
        span = we - ws
        n = min(budget, span)
        if n < 1:
            return []
        # 균등 간격 인덱스 (중복 제거, 결정적).
        if n == 1:
            indices = [ws + span // 2]
        else:
            step = (span - 1) / (n - 1)
            indices = sorted({ws + int(round(i * step)) for i in range(n)})

        from io import BytesIO

        from PIL import Image  # lazy — 어댑터 초기화(_ensure_adapters) 후 가용

        # fps 단일 출처 (_pipeline_frame_fps — I1, 리터럴 9.0 금지). 어댑터 미초기화
        # 환경(로컬 단위테스트 — frame_extractor 의존성 부재)에서는 초 라벨을
        # 포기하고 프레임 인덱스 라벨로 강등 (라벨은 프롬프트 표기 전용 — graceful).
        try:
            fps: float | None = _pipeline_frame_fps()
        except Exception:  # noqa: BLE001 - fps 소스 부재 = 인덱스 라벨 폴백
            fps = None
        video_ref: list[dict] = []
        for idx in indices:
            buf = BytesIO()
            Image.fromarray(arr[idx]).convert("RGB").save(
                buf, format="JPEG", quality=_SPOTCHECK_JPEG_QUALITY
            )
            label = (
                f"프레임 t≈{idx / fps:.1f}s:" if fps else f"프레임 #{idx}:"
            )
            video_ref.append(
                {
                    "label": label,
                    "imageBytes": buf.getvalue(),
                    "mime": "image/jpeg",
                }
            )
        return video_ref
    except Exception:  # noqa: BLE001 - 프레임 준비 실패 = 빈 입력 (skipped no-op)
        log.exception("spot_check 프레임 서브셋 준비 실패 — skipped 폴백")
        return []


def _run_deferred_spot_check(
    *,
    result: dict,
    angles,
    profile,
    frames,
    uid: str,
    analysis_id: str,
) -> None:
    """complete_analysis 이후 스팟체크 → update_analysis_spot_check 부분 갱신.

    D-23 — 분석은 이미 complete(status='done')라 어떤 경로도 재raise 하지 않는다
    (_run_deferred_fault_zoom/_run_deferred_coach_audio 뼈대 복제):

      · run_spot_check 반환(항상 dict — done/skipped/failed) → 그대로 저장.
        'done' + 빈 hiddenRecordIds = 검수 통과. 'skipped'/'failed' = fail-open
        (전 카드 표시 — contract.md §12.8 표시 정책).
      · mismatch 발견 시 구조 로그 적재 (D-23 "로그 적재" — analysis_id/recordId/
        criterion/reason. 문장 본문·프레임 바이트 미로그).
      · 스테이지 예외 → failed 마킹 시도, 그마저 실패 → log.exception 만
        (spotCheck 부재 = legacy 표시 정책과 동일 = 전 카드 표시).

    **동기 채점 경로 호출 금지** — 사후 전용 (속도 예산·timingsMs 회귀 0).
    """
    from sunity_shared.analysis import spot_check as spot_check_mod

    try:
        breakdown = result.get("deductionBreakdown")
        records = breakdown.get("records") if isinstance(breakdown, dict) else None
        if not isinstance(records, list):
            records = []
        praise = result.get("summaryPraise")
        praise_headline = (
            praise.get("headline") if isinstance(praise, dict) else None
        )

        judged = spot_check_mod.select_judged_records(records)
        video_ref = _build_spot_check_video_ref(judged, angles, profile, frames)
        payload = spot_check_mod.run_spot_check(
            video_ref, records, praise_headline
        )

        # D-23 구조 로그 적재 — 불일치 판정 감사 추적 (사용자 비노출).
        for verdict in payload.get("verdicts") or []:
            if verdict.get("verdict") == "mismatch":
                rid = verdict.get("recordId", "")
                criterion = rid.split(":", 1)[1] if ":" in rid else ""
                log.warning(
                    "spot_check mismatch analysis_id=%s record_id=%s "
                    "criterion=%s reason=%s",
                    analysis_id, rid, criterion, verdict.get("reason", ""),
                )
        if payload.get("praiseMismatch"):
            log.warning(
                "spot_check praise mismatch analysis_id=%s (summaryPraise 강등 신호)",
                analysis_id,
            )

        firestore_admin.update_analysis_spot_check(uid, analysis_id, payload)
    except Exception:  # noqa: BLE001 - 부가 기능 실패는 분석 비차단 (graceful)
        log.warning(
            "spot_check 사후 스테이지 실패 — failed 마킹 시도 (분석은 이미 complete) "
            "uid=%s analysis_id=%s", uid, analysis_id,
        )
        try:
            firestore_admin.update_analysis_spot_check(
                uid,
                analysis_id,
                {
                    "status": "failed",
                    "hiddenRecordIds": [],
                    "verdicts": [],
                    "praiseMismatch": False,
                    "model": spot_check_mod.DEFAULT_SPOTCHECK_MODEL,
                    "promptVersion": spot_check_mod.SPOTCHECK_PROMPT_VERSION,
                },
            )
        except Exception:  # noqa: BLE001 - failed write 실패 = spotCheck 부재 유지
            log.exception(
                "spot_check failed 마킹 write 실패 — spotCheck 부재 유지 "
                "(부재 = 전 카드 표시, fail-open) uid=%s analysis_id=%s",
                uid, analysis_id,
            )


# ═══════════ Phase 31 (D-05) — correctedPose 자동 생성 enqueue ═══════════
#
# **이 훅은 enqueue 만 한다.** 생성(DashScope)·판정(Gemini)·pose gate 는 전부
# visual-worker 소유다. 여기서 벤더를 부르면 분석 응답 시간에 수분이 붙는다.
#
# 임시 생체 프레임(source PNG)은 **전용 비-버저닝 버킷**(VISUAL_INPUT_BUCKET)에
# 올린다 — VideoBucket 이 아니다. 버저닝 버킷에서는 delete_object 가 delete marker
# 만 만들고 과거 version 이 남아, "즉시 삭제" privacy SLA 를 version 열거 없이는
# 지킬 수 없다. 비-버저닝이면 delete 1회 = 완전 소거다 (6차 아키텍처 / T-31-76).
#
# 순서 계약 = **upload-first** (3차 B3-03): 입력을 먼저 S3 에 올린 뒤에만 job 을
# 만든다. 반대로 하면 "job 은 있는데 입력이 없는" action 이 성립해 worker 가
# 영구 실패한다. 대신 upload-first 는 "job 없이 남은 입력(orphan)" 을 만들 수
# 있으므로, PUT **전에** durable reservation 을 남겨 janitor 가 회수하게 한다
# (7차 B7-05 / T-31-80).

_CORRECTED_POSE_MAX_PUT_RETRY = 3

_SQS_CLIENT = None


def _sqs():
    """lazy SQS client — visual 훅 외의 경로는 SQS 를 쓰지 않는다(콜드스타트 절약)."""
    global _SQS_CLIENT
    if _SQS_CLIENT is None:
        _SQS_CLIENT = boto3.client("sqs")
    return _SQS_CLIENT


def _visual_input_bucket() -> str | None:
    return os.environ.get("VISUAL_INPUT_BUCKET") or None


def _visual_jobs_enabled() -> bool:
    return os.environ.get("VISUAL_JOBS_ENABLED") == "true"


def _s3_error_code(exc) -> str:
    return str(((getattr(exc, "response", None) or {}).get("Error") or {}).get("Code") or "")


def _record_visual_orphan(bucket: str, key: str, *, reason: str) -> None:
    """보상 delete 실패의 **필수** durable 기록 (7차 H7-04).

    옵션 로그가 아니다 — "지우려다 실패했는데 아무도 모르는 PII" 를 만들지 않기
    위해 소비 주체(janitor)가 있는 문서로 남긴다. metric 은 알람용 부가물이라
    실패해도 삼킨다.
    """
    try:
        firestore_admin.upsert_visual_orphan(
            bucket, key, now_ms=_visual_now_ms(), reason=reason
        )
    except Exception:  # noqa: BLE001 - 기록 실패까지는 막지 못한다(로그로 남긴다)
        log.exception("visualOrphans 기록 실패 bucket=%s key=%s", bucket, key)
    try:
        boto3.client("cloudwatch").put_metric_data(
            Namespace="SunityVisual",
            MetricData=[{"MetricName": "VisualOrphanSourceObject", "Value": 1.0}],
        )
    except Exception:  # noqa: BLE001 - 관측 실패가 business path 를 막으면 안 된다
        log.warning("VisualOrphanSourceObject metric put 실패")


def _visual_now_ms() -> int:
    import time

    return int(time.time() * 1000)


def _delete_owned_key(bucket: str, key: str, *, ref: str, owner: str) -> bool:
    """**producer 의 유일한 삭제 경로** (11차 B11-02).

    직접 delete_object 를 부르면 안 되는 이유: 같은 deterministic key 를 쓰는 다른
    live reservation/job 이 있을 수 있다. 내 보상 삭제가 남의 살아있는 입력을
    지우면 그 job 은 입력 없이 영구 실패한다. claim 이 None 이면 삭제하지 않는다.

    commit 재검증까지 통과해야 실제 DeleteObject 를 던진다 — lease 만료 뒤 되살아난
    이전 claimant 를 generation fencing 으로 막는 계약(11차 B11-01)의 일부다.
    """
    now_ms = _visual_now_ms()
    token = firestore_admin.claim_key_for_delete(
        bucket,
        key,
        deleting_ref=ref,
        owner=owner,
        lease_ms=models.VISUAL_OBJECT_DELETE_LEASE_MS,
        now_ms=now_ms,
    )
    if token is None:
        # 다른 live ref 존재 — 내 ref 는 소비됐고 객체는 그 소유자가 책임진다.
        log.info("visual 입력 삭제 보류(다른 live ref) key=%s", key)
        return False
    if not firestore_admin.commit_key_delete(bucket, key, token=token, now_ms=_visual_now_ms()):
        log.warning("visual 입력 삭제 fencing 실패 key=%s", key)
        return False
    try:
        _s3.delete_object(Bucket=bucket, Key=key)
        return True
    except Exception:  # noqa: BLE001 - 실패는 orphan 문서로 승계
        log.warning("visual 입력 delete 실패 — orphan 등록 key=%s", key)
        _record_visual_orphan(bucket, key, reason="producer_compensation_delete_failed")
        return False


def _release_visual_keys(bucket: str, keys, *, ref: str) -> None:
    """ownership ref 해제 — **모든 종료 경로의 필수 부분** (10차 B10-03 / T-31-91).

    빠뜨리면 ownership 문서가 refs 를 든 채 영구 잔존해 그 key 의 cleanup 이 영원히
    skip 된다. loser 경로(created=False)도 예외가 아니다 — 미release 시 winner job 의
    worker terminal gate 가 내 ref TTL 이 끝날 때까지 막힌다 (11차 B11-03).
    """
    for key in keys:
        try:
            firestore_admin.release_key_ownership(bucket, key, ref=ref)
        except Exception:  # noqa: BLE001 - 해제 실패가 분석을 막으면 안 된다
            log.warning("key ownership release 실패 key=%s ref=%s", key, ref)


def _close_visual_reservation(job_id: str, reservation_id: str, *, owner: str) -> None:
    try:
        firestore_admin.close_reservation(
            job_id, reservation_id, owner=owner, now_ms=_visual_now_ms()
        )
    except Exception:  # noqa: BLE001 - janitor 가 TTL 만료로 회수한다
        log.warning("reservation close 실패 job_id=%s", job_id)


def _enqueue_corrected_pose_job(
    *,
    uid: str,
    analysis_id: str,
    target,
    src_png: bytes,
    request_id: str,
) -> None:
    """correctedPose job enqueue (D-05). 어떤 경로도 재raise 하지 않는다.

    분석은 이미 complete 이므로 이 훅의 어떤 실패도 사용자 결과를 막지 않는다.

    단계:
      (0) preflight — job 이 어떤 state 로든 있으면 **source PUT 을 하지 않는다**
          (6차 B6-03). 이미 done/failed 인 job 뒤에 새 입력을 올리면 cleanup 이
          끝난 뒤 PII 가 되살아난다. 최종 권위는 reserve 지만, 대부분의 replay 는
          여기서 S3 접촉 0 으로 끝난다.
      (0.5) PUT **전** per-invocation immutable reservation + key ownership 획득.
          reservation 이 per-invocation 인 이유(8차 B8-05): 단일 {jobId} 문서를
          덮어쓰면 동시 invocation 이 서로의 expectedKeys 를 잃어 회수 대상에서
          빠진다.
      (1) 조건부 PUT(IfNoneMatch='*') — 이미 있으면 HEAD 의 full sha256 을 대조해
          재사용하고, 불일치면 차단한다(collision/tampering). 두 invocation 이
          서로의 입력을 갈아끼울 수 없다 (4차 M4-04 / 5차 B5-02).
      (2) reserve — job + 표시 pending + 초기 outbox + reservation claim +
          ownership 승격이 한 transaction (B3-03 / B8-06 / H10-01).
      (3) inputSealed / terminal replay → 이번에 만든 입력 즉시 삭제.
      (4) 실패/analysis_missing/commit loss → orphan 보상.
      (5) best-effort SQS 발행.
    """
    if not _visual_jobs_enabled():
        return
    if target is None:  # B2-01 — 불확실하면 생성하지 않는다
        return
    bucket = _visual_input_bucket()
    if not bucket:
        log.error("VISUAL_INPUT_BUCKET 미설정 — correctedPose enqueue 생략")
        return
    if not src_png:
        return

    job_id = models.visual_job_id(uid, analysis_id, models.VISUAL_KIND_CORRECTED_POSE)
    # full 64 hex (7차 M7-02) — prefix 절단은 불필요한 충돌 차단만 늘린다.
    source_hash = hashlib.sha256(src_png).hexdigest()
    src_key = f"visual-input/{uid}/{analysis_id}/{source_hash}.png"
    reservation_id = request_id
    created_keys: list[str] = []
    acquired_keys: list[str] = []

    try:
        # ── (0) preflight ────────────────────────────────────────────────
        existing = firestore_admin.read_visual_job(job_id)
        if existing is not None:
            if (
                existing.get("dispatchState") == "pending"
                and existing.get("srcKey") == src_key
            ):
                _dispatch_visual_job(job_id, existing)
            return

        # ── (0.5) reservation + key ownership (PUT 전) ───────────────────
        now_ms = _visual_now_ms()
        firestore_admin.create_input_reservation(
            job_id,
            reservation_id,
            owner=request_id,
            bucket=bucket,
            source_hash=source_hash,
            expected_keys=[src_key],
            now_ms=now_ms,
        )
        if not firestore_admin.acquire_key_ownership(
            bucket,
            src_key,
            ref=reservation_id,
            kind="reservation",
            now_ms=now_ms,
            expire_at_ms=now_ms + models.VISUAL_INPUT_RESERVATION_TTL_MS,
        ):
            # state=='deleting' — 회수 중인 key 를 되살리지 않는다 (11차 B11-01).
            log.info("visual 입력 key 삭제 진행 중 — enqueue 생략 key=%s", src_key)
            _close_visual_reservation(job_id, reservation_id, owner=request_id)
            return
        acquired_keys.append(src_key)

        # ── (1) 조건부 PUT ───────────────────────────────────────────────
        if not _put_visual_source(bucket, src_key, src_png, source_hash):
            _release_visual_keys(bucket, acquired_keys, ref=reservation_id)
            _close_visual_reservation(job_id, reservation_id, owner=request_id)
            return
        created_keys.append(src_key)
        firestore_admin.record_reservation_keys(
            job_id, reservation_id, created_keys=created_keys, owner=request_id
        )

        # ── (2) reserve ──────────────────────────────────────────────────
        payload = dict(target.to_payload())
        payload["srcKey"] = src_key
        payload["sourceHash"] = source_hash
        try:
            res = firestore_admin.reserve_visual_job(
                uid,
                analysis_id,
                models.VISUAL_KIND_CORRECTED_POSE,
                payload=payload,
                allow_retry_failed=False,
                reservation_id=reservation_id,
                reservation_owner=request_id,
                now_ms=_visual_now_ms(),
            )
        except Exception:  # noqa: BLE001 - commit 유실 포함 (4) 보상으로
            log.warning("correctedPose reserve 실패 — orphan 보상 job_id=%s", job_id)
            _compensate_visual_orphan(
                bucket, job_id, src_key, created_keys, reservation_id, request_id
            )
            return

        reason = res.get("reason")
        if reason == "reservation_lost":
            # janitor 가 이미 이 reservation 을 회수했다 — 내 삭제는 0.
            _release_visual_keys(bucket, acquired_keys, ref=reservation_id)
            return
        if reason is not None:
            # analysis_missing 등 — job 이 안 생겼으므로 입력은 고아다.
            _compensate_visual_orphan(
                bucket, job_id, src_key, created_keys, reservation_id, request_id
            )
            return

        job = res.get("job") or {}
        if res.get("created"):
            # 성공 — reserve 가 ownership 을 job 으로 승격하고 reservation 을 닫았다.
            _dispatch_visual_job(job_id, job)
            return

        # ── (3) created False — 기존 job 분기 ────────────────────────────
        sealed = job.get("inputSealed") is True
        terminal = job.get("state") in models.VISUAL_TERMINAL_STATES
        if (sealed or terminal) and created_keys:
            # terminal/sealed 뒤에 남은 새 입력 = cleanup 이 끝난 뒤 되살아난 PII.
            for key in created_keys:
                _delete_owned_key(bucket, key, ref=reservation_id, owner=request_id)
            log.info("terminal/sealed replay 입력 즉시 삭제 job_id=%s", job_id)
        _release_visual_keys(bucket, acquired_keys, ref=reservation_id)
        _close_visual_reservation(job_id, reservation_id, owner=request_id)
    except Exception:  # noqa: BLE001 - 분석은 이미 complete (비차단 규율)
        log.exception("correctedPose enqueue 실패 (분석 비차단) job_id=%s", job_id)


def _maybe_enqueue_corrected_pose(
    *,
    result: dict,
    user_report: dict | None,
    ref_report: dict | None,
    ref_video_path: str | None,
    cached_user_frames,
    uid: str,
    analysis_id: str,
    request_id: str,
) -> None:
    """call-site — target 을 만들고 source 프레임을 PNG 로 굳혀 enqueue 에 넘긴다.

    **flag 를 가장 먼저 본다.** OFF(기본)면 프레임 인코딩도 reference 재추출도 하지
    않는다 — 운영 분석 경로에 비용 0 (D-08 조용한 폴백). 31-12 가 belle 승인 하에
    켠다.

    target 계약의 유일한 소비자다 (B2-01): joint/targetDeg/source frame 을 여기서
    임의로 재계산하지 않고 build_corrected_pose_target 결과만 쓴다. 생성 지시와
    31-09 의 pose gate 검증 기준이 갈라지지 않게 하려는 것이다.

    mode1 전용인 이유: target_deg 는 DTW 로 매칭된 **reference 3점의 내각**이다.
    비교 기준이 없는 mode3 에는 목표각의 출처가 없다.
    """
    if not _visual_jobs_enabled():
        return
    if not user_report or not ref_report or not ref_video_path:
        return
    try:
        from sunity_shared.analysis import fault_zoom as _fz

        vv = result.get("visionVeto") or {}
        sfi = (vv.get("windowMedianAngleDeltas") or {}).get("sourceFrameIndices") or {}
        u_list = sfi.get("user") or []
        r_list = sfi.get("reference") or []
        fault_joints = list(vv.get("faultJoints") or [])
        if not (u_list and r_list and fault_joints):
            return
        # 줌 카드와 **같은** 프레임 쌍을 쓴다 — 교정 이미지와 확대 비교가 다른
        # 순간을 가리키면 사용자에겐 서로 모순된 두 장이 된다 (B2-01).
        u_idx = _fz.select_confident_frame(user_report, u_list, fault_joints)
        r_idx = _fz.select_confident_frame(ref_report, r_list, fault_joints)
        if u_idx is None or r_idx is None:
            return

        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

        ext = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
        ref_frames = ext.extract(ref_video_path)
        if ref_frames is None or len(ref_frames) <= r_idx:
            return
        ref_shape = (int(ref_frames.shape[1]), int(ref_frames.shape[2]))

        target = _fz.build_corrected_pose_target(
            ((result.get("deductionBreakdown") or {}).get("records")),
            user_report,
            ref_report,
            (int(u_idx), int(r_idx)),
            False,
            ref_frame_shape=ref_shape,
        )
        if target is None:
            return

        user_frames = cached_user_frames
        if user_frames is None or len(user_frames) <= target.user_frame_idx:
            return
        src_png = _encode_png(user_frames[target.user_frame_idx])
        if not src_png:
            return

        _enqueue_corrected_pose_job(
            uid=uid,
            analysis_id=analysis_id,
            target=target,
            src_png=src_png,
            request_id=request_id,
        )
    except Exception:  # noqa: BLE001 - 분석은 이미 complete (비차단 규율)
        log.warning(
            "correctedPose target 준비 실패 (분석 비차단) uid=%s analysis_id=%s",
            uid,
            analysis_id,
        )


def _encode_png(frame) -> bytes | None:
    """(H, W, 3) RGB uint8 → PNG 바이트.

    PIL 은 **lazy import** 다 — pipeline/requirements.txt 는 250MB 한도 때문에
    Pillow 를 의도적으로 제외한다(실측 262MB 초과 기록). 이 훅이 실제로 도는 곳은
    Pillow 가 있는 Pod 런타임이고, Lambda 폴백에서는 flag OFF 라 여기 도달하지
    않는다. import 실패는 조용히 생략한다.
    """
    try:
        import io

        from PIL import Image

        buf = io.BytesIO()
        Image.fromarray(frame).save(buf, format="PNG")
        return buf.getvalue()
    except Exception:  # noqa: BLE001 - Pillow 부재(Lambda) 포함
        log.info("correctedPose source PNG 인코딩 생략 (Pillow 미가용 가능)")
        return None


def _compensate_visual_orphan(
    bucket: str,
    job_id: str,
    src_key: str,
    created_keys: list,
    reservation_id: str,
    request_id: str,
) -> None:
    """reserve 미성립 시 보상 (6차 H6-02).

    job 을 다시 읽어 판단한다: job 이 없으면 이번 입력은 확실한 고아이므로 삭제,
    job 이 있고 그 입력이 내 것이면(payload.srcKey 일치) 살아있는 job 의 입력이므로
    유지한다. commit 응답만 유실되고 실제로는 성공한 경우가 여기다.
    """
    try:
        job = firestore_admin.read_visual_job(job_id)
    except Exception:  # noqa: BLE001 - 못 읽으면 삭제하지 않는다(보수적)
        log.warning("보상 판단용 job 재read 실패 job_id=%s", job_id)
        for key in created_keys:
            _record_visual_orphan(bucket, key, reason="compensation_job_read_failed")
        return

    if job is not None and job.get("srcKey") == src_key:
        # commit 은 성사됐다 — 입력은 그 job 의 것이다.
        return
    for key in created_keys:
        _delete_owned_key(bucket, key, ref=reservation_id, owner=request_id)
    _release_visual_keys(bucket, [src_key], ref=reservation_id)
    _close_visual_reservation(job_id, reservation_id, owner=request_id)


def _put_visual_source(bucket: str, key: str, body: bytes, source_hash: str) -> bool:
    """조건부 immutable PUT. 성공(신규 생성) 또는 동일 해시 재사용이면 True.

    IfNoneMatch='*' 는 "없을 때만 생성" 이다. 412/409 는 경쟁이 있었다는 뜻이므로
    HEAD 로 기존 객체의 full sha256 을 읽어 **정확히 같은 바이트**일 때만 재사용한다.
    다르면 같은 key 에 다른 프레임이 있다는 뜻이라 진행하지 않는다 (M4-04).
    """
    for attempt in range(_CORRECTED_POSE_MAX_PUT_RETRY):
        try:
            _s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType="image/png",
                Metadata={"sha256": source_hash},
                IfNoneMatch="*",
            )
            return True
        except Exception as exc:  # noqa: BLE001 - 코드로 분기
            code = _s3_error_code(exc)
            if code in ("PreconditionFailed", "412"):
                break
            if code in ("ConditionalRequestConflict", "409") and attempt + 1 < _CORRECTED_POSE_MAX_PUT_RETRY:
                continue
            if code in ("ConditionalRequestConflict", "409"):
                break
            log.warning("visual source PUT 실패 code=%s key=%s", code, key)
            return False

    try:
        head = _s3.head_object(Bucket=bucket, Key=key)
    except Exception:  # noqa: BLE001 - 존재 판정 불가 → 진행하지 않는다
        log.warning("visual source HEAD 실패 key=%s", key)
        return False
    existing_hash = (head.get("Metadata") or {}).get("sha256")
    if existing_hash != source_hash:
        log.error(
            "srcKey collision/tampering — 기존 객체 해시 불일치 key=%s", key
        )
        return False
    return True  # 동일 바이트 재사용


def _dispatch_visual_job(job_id: str, job: dict) -> None:
    """best-effort 발행. 실패해도 dispatchState='pending' 이 남아 dispatcher 가 복구."""
    queue_url = os.environ.get("VISUAL_QUEUE_URL")
    if not queue_url:
        log.error("VISUAL_QUEUE_URL 미설정 — dispatcher 복구에 위임")
        return
    action = job.get("nextAction") or "create"
    outbox_seq = int(job.get("outboxSeq") or 0)
    generation = int(job.get("generation") or 0)
    try:
        _sqs().send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(
                {
                    "jobId": job_id,
                    "generation": generation,
                    "action": action,
                    "outboxSeq": outbox_seq,
                }
            ),
        )
    except Exception:  # noqa: BLE001 - dispatcher 가 재발행 (H3-09)
        log.warning("correctedPose send 실패 job_id=%s — outbox pending 유지", job_id)
        return
    try:
        firestore_admin.mark_visual_job_dispatched(
            job_id,
            expect_action=action,
            expect_outbox_seq=outbox_seq,
            expect_generation=generation,
        )
    except Exception:  # noqa: BLE001 - mark 실패는 재발행(멱등)으로 흡수
        log.warning("mark_visual_job_dispatched 실패 job_id=%s", job_id)


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

    반환: (assessments, dimension_scores, overall, comparison, prev_dtw_match).
      - assessments: 관절각 기반(코칭 tips 용). 첫 분석은 신전 부족분(IPSF 라인),
        이후는 이전 영상 대비.
      - dimension_scores: 첫 분석=절대 차원, 이후=절대 + angle(일관성).
      - overall: 절대 차원 평균(첫 분석/이후 동일 척도).
      - prev_dtw_match: 이전 영상 대비 DTW MotionMatch (28-04 motionAlignment 방출 +
        mode3 fault_zoom 같은-pose 프레임 정렬용). 첫 분석/prev 부재 = None."""
    abs_dims = dimensions.absolute_dimension_scores(angles, profile)
    # Phase 19 TRUST-03 — branch_info 미전달 시 profile.motion_id 로 lookup (게이트 wiring
    # 이 없는 단위 테스트/호출 경로 호환). is_reference_free_motion 으로 미보유 판정
    # (copyBranch 단독 분기 금지). fail-closed/raise 없음 — 점수는 주되 근거만 라벨링.
    if branch_info is None:
        branch_info = assemble.lookup_motion_branch(
            getattr(profile, "motion_id", None)
        )
    is_reference_free = assemble.is_reference_free_motion(branch_info)
    # Phase 30 WR-04 (30-REVIEW): recognized_motion_id/name 은 적립 전용 옵셔널 필드
    # (contract.md §4 — 이번 phase 화면 미소비). 인식기 경계는 런타임 str 을 보증하지
    # 않음(예: gemini_technique_recognizer._profile_from_cache 의 무검증 캐시 복원).
    # 비-str 이면 build_mode3 의 T-30-03 ValueError 가 _process 광역 except 를 타고
    # 분석 전체를 server_error 로 죽이므로, 여기서 해당 필드만 drop + warning 하고
    # 분석은 계속한다 (scene_finder·coach writer graceful-degrade 관례 정합).
    # builder 의 타입 강제(T-30-03 — 오염 데이터 적립 방지)는 유지: drop 이 곧 방지.
    _rm_id = profile.motion_id if isinstance(profile.motion_id, str) else None
    _rm_name = profile.name if isinstance(profile.name, str) else None
    if profile.motion_id is not None and _rm_id is None:
        log.warning(
            "recognized_motion_id 비-str — 적립 생략 (분석 계속): %r", profile.motion_id
        )
    if profile.name is not None and _rm_name is None:
        log.warning(
            "recognized_motion_name 비-str — 적립 생략 (분석 계속): %r", profile.name
        )
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
            # Phase 30 D-04: 인식된 동작 id/명 적립 (첫 분석도 방출 — build_mode3 가
            # early return 앞 emit). _rm_id 가 None(FallbackRecognizer/인식 실패/비-str
            # drop, WR-04)이면 builder 가 두 키 미추가(계약) → 호출부 조건 분기 불필요.
            # motion_id None 이면 name('미상' placeholder 가능)도 무의미 — builder 가
            # id-None 시 name 도 미emit (Task 1 규칙)이므로 그대로 전달해도 안전.
            # 저신뢰 억제(_apply_score_suppression)와 독립 emit — D-04 는 데이터 적립.
            assemble.build_mode3(
                is_first=True,
                scoring_basis=first_basis,
                recognized_motion_id=_rm_id,
                recognized_motion_name=_rm_name,
            ),
            None,  # prev_dtw_match — 첫 분석은 정렬 컨텍스트 부재 (28-04 미방출 = legacy)
        )
    num_joints = len(prev.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    deviation, prev_dtw_match, _user_seg, prev_seg = _deviation_against(
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
        # Phase 30 D-04: progress 분기도 인식 동작 id/명 적립 (억제와 독립 emit).
        # WR-04: str 경계 정규화(_rm_id/_rm_name) 후 전달 — 비-str 은 필드만 drop.
        recognized_motion_id=_rm_id,
        recognized_motion_name=_rm_name,
    )
    return assessments, dim_scores, overall, comparison, prev_dtw_match


def _pipeline_frame_fps() -> float:
    """학생 angles fps 단일 출처 — frame_extractor 기본 target_fps (I1, 리터럴 9.0 금지).

    _FRAME_EXTRACTOR(_ensure_adapters 초기화분)의 target_fps 를 정본으로 참조 —
    _process 는 진입 즉시 _ensure_adapters() 를 호출하므로 방출 시점엔 항상 초기화됨.
    미초기화 폴백은 FfmpegFrameExtractor 생성자 기본값을 introspect (값 재복제 아님 —
    frame_extractor.py 의 target_fps 기본값이 단일 정본).
    """
    ext = _FRAME_EXTRACTOR
    fps = getattr(ext, "target_fps", None) if ext is not None else None
    if fps:
        return float(fps)
    import inspect
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    return float(
        inspect.signature(FfmpegFrameExtractor.__init__).parameters["target_fps"].default
    )


def _attach_motion_alignment(
    result: dict,
    match,
    *,
    user_fps: float,
    ref_fps: float,
    uid: str,
    analysis_id: str,
) -> None:
    """DTW match → result["motionAlignment"] 방출 (표현/재생 전용 — 채점 무접촉, 28-CONTEXT).

    complete_analysis 호출 **전에만** 호출한다 (27-06 게이트: complete 후 result.* write
    금지 — 사후 업데이트 경로 신설 금지). 유일한 부작용 = motionAlignment 키 1개 추가
    (그 외 result 무변경). match=None(정렬 컨텍스트 부재)이면 아무것도 안 함(미방출 =
    legacy). degenerate 입력(ref fps 결측 등)은 build_motion_alignment 가 tier 'disabled'
    dict 로 방출하므로(28-02 W3) helper 에 별도 분기 없음 — 신규 분석은 필드가 실려
    legacy(필드 부재)와 구분된다. 방출 실패는 graceful skip — 분석 흐름을 차단하지 않는다.
    """
    try:
        alignment = build_motion_alignment(match, user_fps=user_fps, ref_fps=ref_fps)
        if alignment is not None:
            result["motionAlignment"] = alignment
    except Exception:  # noqa: BLE001 - 방출 실패는 분석 비차단 (graceful)
        log.exception(
            "motion alignment 방출 실패 — graceful skip uid=%s analysis_id=%s",
            uid, analysis_id,
        )


# ── Phase 32 (Plan 32-09) — 번역 레이어·미션 루프 방출 배선 ─────────────────────
#
# 32-CONTEXT D-08(감점 카드 3단)/D-11(문구집 골격 소유)/D-19(미션 선정)/D-26(미션
# baseline)/D-27(에스컬레이션)/D-28(코치 질문)/D-29(부분 실패 UX) + 리뷰 blocker
# 1(faultKey 체인)·5(recordId·summaryPraise 단일 원천).
#
# 설계 원칙:
#   · 전부 순수 계산(dict 조립) — 외부 호출 0, 신규 Firestore 쿼리 0 (prev 는 기존
#     mode3 get_previous_analysis 결과 재사용 — composite index 함정 주석 준수).
#   · 방출은 전부 result 안으로 — complete_analysis 신규 kwarg 0 (safetyFlags 선례).
#   · 항목 단위 격리(리뷰 반영): record 1건의 문구 조립 실패는 그 record 만 문구
#     없이 통과, 미션/praise/질문 각각도 독립 try — 표시 부가물이 완료된 분석을
#     fail 시키지 않는다 (T-32-20, SP-3).
#   · LLM(Cerebras)은 이 배선에 관여하지 않는다 — 3단 골격은 phrasebook(32-05,
#     belle 승인 카피)만 소유 (D-11: LLM 전체 실패 시에도 3단 성립).

# 미측정 신호 → 질문 라벨 (D-29). keypoint_set 는 내부 영어 enum 이라 사용자 카피
# 로 못 쓴다 — coverageGaps.bodyPart(Gemini 한국어 서술)가 있으면 그것을 우선,
# 없으면 이 고정 라벨. reach 라벨은 terminology_map terms['reach'](승인 카피,
# D-12 단일 출처) verbatim.
_UNMEASURED_LABEL_KO: dict[str, str] = {
    "head_neck": "머리·목 방향",
    "grip": "그립 위치",
    "torso": "몸통 축",
    "shoulder": "어깨 정렬",
    "hip": "골반 축",
    "body_relative_reach": "목표 지점까지 몸을 뻗어 닿는 정도",
    "dimension_overall_fallback": "세부 부위별 측정",
}
# 질문 완성문 템플릿 (D-28 문구집 스타일 — 조사 회피 위해 라벨은 괄호 병기).
_UNMEASURED_QUESTION_TEMPLATE = (
    "이번 영상에서 정확히 재기 어려웠던 부분이 있어요 ({label}) — "
    "강사님과 직접 확인해보고 싶어요"
)
# coachQuestions 상한 — firestore_admin._MAX_COACH_QUESTIONS(10) lockstep.
_MAX_EMITTED_COACH_QUESTIONS = 10


def _criterion_tolerance(criterion: str) -> float | None:
    """criterion id → 실존 규칙 상수 tolerance (D-10 게이지 스케일 재료).

    출처는 ipsf_criteria.CRITERION_GROUPS 뿐 — 자의 수치 생성 금지. 미등재
    criterion(dimension_overall_fallback 등)은 None (호출부가 키 생략).
    """
    from sunity_shared.analysis import ipsf_criteria

    for crit in ipsf_criteria.CRITERION_GROUPS:
        if crit.get("id") == criterion:
            tol = crit.get("tolerance")
            if not isinstance(tol, bool) and isinstance(tol, (int, float)):
                return float(tol)
            return None
    return None


def collect_unmeasured_signals(breakdown, dimension_explanation) -> list[str]:
    """'이번에 못 잰 것' 신호 수집 adapter (D-28/D-29 — source='unmeasured' 원천).

    실존 신호 실측 기록 (2026-07-21 코드 확인 — 리뷰 반영, 발견 필드 명시):
      · `deductionBreakdown.coverageGaps[]` — deduction_engine._gap_to_dict 방출
        flat entry {faultType, reason, bodyPart, faultState, keypointSet, ruleId}.
        측정 substrate 부재 결함 (ipsf_criteria.COVERAGE_GAP_KEYPOINT_SETS 5종
        head_neck/grip/torso/shoulder/hip + reach 의 quantification_unavailable
        entry — ruleId 'reach_substrate_unavailable_low_alignment').
      · `deductionBreakdown.records[].ruleId ==
        'quantification_unavailable_dimension_overall'` (criterion
        'dimension_overall_fallback') — 정량화 전체 불가 whole-score 폴백 record.
      · `dimensionExplanation` 에는 미측정 서술이 **실존하지 않는다** (assemble.
        _deficit_summary_for 는 양호/deficit 카피만 방출 — 실측 결과 소스 제외).
        시그니처에는 보존 — 향후 미측정 서술 도입 시의 명시 hook (플랜 지정 형상).

    Args:
        breakdown: result['deductionBreakdown'] dict 또는 None.
        dimension_explanation: result['dimensionExplanation'] dict 또는 None
            (현재 미소비 — 위 실측 기록 참조).

    Returns:
        한국어 라벨 list (등장 순서 보존 + dedup). 질문 문장 조립은 호출부
        (_collect_coach_questions) 소관 — 이 함수는 신호 수집만.
    """
    del dimension_explanation  # 실측: 미측정 서술 실존 X — hook 보존 (docstring)
    if not isinstance(breakdown, dict):
        return []
    labels: list[str] = []

    def _add_label(label: str | None) -> None:
        if isinstance(label, str) and label and label not in labels:
            labels.append(label)

    for gap in breakdown.get("coverageGaps") or []:
        if not isinstance(gap, dict):
            continue
        body_part = gap.get("bodyPart")
        keypoint_set = gap.get("keypointSet") or gap.get("faultType")
        mapped = (
            _UNMEASURED_LABEL_KO.get(keypoint_set)
            if isinstance(keypoint_set, str)
            else None
        )
        # bodyPart 는 Gemini 한국어 서술 우선 — 단 reach gap 의 합성값 'reach' 는
        # 영어 내부어라 제외 (deduction_engine.py:298 실측).
        if isinstance(body_part, str) and body_part and body_part != "reach":
            _add_label(body_part)
        else:
            _add_label(mapped)
    for rec in breakdown.get("records") or []:
        if (
            isinstance(rec, dict)
            and rec.get("ruleId") == "quantification_unavailable_dimension_overall"
        ):
            _add_label(_UNMEASURED_LABEL_KO["dimension_overall_fallback"])
    return labels


def _criteria_met_for_praise(records: list, breakdown) -> bool:
    """summaryPraise source='criteria_met' 판정 — 측정된 감점 record 0.

    breakdown 자체 부재(레거시/게이트 경로)나 fallback 마커 존재(측정 불가)는
    '기준 통과' 근거가 아니다 — False (D-06 근거 없는 칭찬 금지).
    """
    if not isinstance(breakdown, dict):
        return False
    if breakdown.get("fallback"):
        return False
    for rec in records:
        if not isinstance(rec, dict):
            continue
        pts = rec.get("points")
        if not isinstance(pts, bool) and isinstance(pts, (int, float)) and pts != 0:
            return False
    return True


# deduction criterion → 관련 차원 (clean_dimension 모순 칭찬 차단용 — D-06).
# 감점 record 가 실린 차원은 dimensionScores 가 100 이어도 '깨끗' 근거가 아니다
# (vision-측정 substrate 가 dimension 산식과 다른 경로로 감점할 수 있음 — split 등).
# body_relative_reach 는 위치 지표라 3 차원 밖 → 차원 차단 없음.
_CRITERION_TO_DIMENSION: dict[str, str | None] = {
    "leg_extension": "line",
    "arm_extension": "line",
    "line": "line",
    "split_angle": "line",
    "body_relative_reach": None,
    "dimension_overall_fallback": None,  # whole-score 폴백 — fallback 체크가 차단
}


def _dimension_for_criterion(criterion: str) -> str | None:
    if criterion.startswith("angle_vs_reference__"):
        return "angle"
    return _CRITERION_TO_DIMENSION.get(criterion)


def _clean_praise_dimensions(result: dict, mode: str) -> list[str]:
    """감점 0 차원 후보 (summaryPraise clean_dimension 재료 — 측정 존재분만).

    호출부 책임(플랜 명시): 커버리지 갭 차원 제외 후 전달 —
      · fallback == 'quantification_unavailable' 이면 전체 측정 불가 → 빈 list
        ('깨끗함'의 측정 근거 부재, D-06).
      · 실감점 record 가 매핑되는 차원 제외 — dimensionScores 100 이어도 감점
        내역과 모순되는 칭찬 금지 (_CRITERION_TO_DIMENSION, D-06).
      · mode3 의 angle 차원은 제외 — angle 은 이전 영상 유사도라 '잘한 점' 근거가
        아니다 ([[mode3-overall-exclude-angle-similarity]] invariant 정합).
    순서 = line → stability → angle (domain 핵심 가치 라인 우선, 결정적).
    """
    breakdown = result.get("deductionBreakdown")
    if not isinstance(breakdown, dict):
        return []
    if breakdown.get("fallback") == "quantification_unavailable":
        return []
    dim_scores = result.get("dimensionScores")
    if not isinstance(dim_scores, dict):
        return []
    deducted_dims: set[str] = set()
    for rec in breakdown.get("records") or []:
        if not isinstance(rec, dict):
            continue
        pts = rec.get("points")
        criterion = rec.get("criterion")
        if (
            not isinstance(pts, bool)
            and isinstance(pts, (int, float))
            and pts != 0
            and isinstance(criterion, str)
        ):
            mapped = _dimension_for_criterion(criterion)
            if mapped:
                deducted_dims.add(mapped)
    out: list[str] = []
    for dim in ("line", "stability", "angle"):
        if mode == models.MODE_SELF and dim == "angle":
            continue
        if dim in deducted_dims:
            continue
        score = dim_scores.get(dim)
        if not isinstance(score, bool) and isinstance(score, (int, float)) and score >= 100:
            out.append(dim)
    return out


def _collect_coach_questions(result: dict, mission: dict | None) -> list[dict]:
    """coachQuestions 자동 수집 (D-28/D-29) — 3 원천, recordId 조인, 상한 10.

    원천 순서 (D-28): ① 위험 결함 항상 (safetyFlags → assemble_safety_phrases
    coachQuestion, source='safety') → ② 3회 미개선 미션 (escalation=='coach_card'
    → 해당 record 의 coachQuestion, source='mission_stuck', recordId 조인) →
    ③ 이번에 못 잰 것 (collect_unmeasured_signals, source='unmeasured').
    dedup = (text, recordId). 각 항목 flat scalar dict {text, source, recordId?}
    — firestore_admin._validate_coach_questions 통과 형상.
    """
    from sunity_shared.analysis import phrasebook

    questions: list[dict] = []
    seen: set[tuple] = set()

    def _add(text, source: str, record_id: str | None = None) -> None:  # noqa: ANN001
        if not isinstance(text, str):
            return
        text = text.strip()
        # validator 상한(200자) 초과 카피는 방출하지 않는다 — 문구집 승인 카피는
        # 전부 상한 이내라 실경로 없음 (방어: 중간 절단 카피 노출 금지 — skip).
        if not text or len(text) > 200:
            return
        key = (text, record_id)
        if key in seen:
            return
        seen.add(key)
        item: dict = {"text": text, "source": source}
        if isinstance(record_id, str) and record_id:
            item["recordId"] = record_id
        questions.append(item)

    # ① 위험 결함 항상 (D-28 — D-14 정합: 안내·강사 유도만, 게임 요소 0).
    for flag in result.get("safetyFlags") or []:
        if not isinstance(flag, dict):
            continue
        flag_type = flag.get("flagType")
        phrases = phrasebook.assemble_safety_phrases(
            flag_type if isinstance(flag_type, str) else ""
        )
        _add(phrases.get("coachQuestion"), "safety")

    # ② 3회 미개선 미션 — coach_card 전면 승격 (D-27 3회차+).
    if isinstance(mission, dict) and mission.get("escalation") == "coach_card":
        record_id = mission.get("recordId")
        records = (result.get("deductionBreakdown") or {}).get("records") or []
        rec = next(
            (
                r
                for r in records
                if isinstance(r, dict)
                and isinstance(record_id, str)
                and r.get("recordId") == record_id
            ),
            None,
        )
        question = rec.get("coachQuestion") if isinstance(rec, dict) else None
        _add(
            question,
            "mission_stuck",
            record_id if isinstance(record_id, str) else None,
        )

    # ③ 이번에 못 잰 것 (D-29 — 정직 고지, 강사 확인 유도).
    for label in collect_unmeasured_signals(
        result.get("deductionBreakdown"), result.get("dimensionExplanation")
    ):
        _add(_UNMEASURED_QUESTION_TEMPLATE.format(label=label), "unmeasured")

    return questions[:_MAX_EMITTED_COACH_QUESTIONS]


def _attach_translation_emission(
    result: dict,
    *,
    mode: str,
    motion_id: str | None,
    prev_doc: dict | None,
    uid: str,
    analysis_id: str,
) -> None:
    """32-09 방출 배선 본체 — recordId·3단 문구·미션·summaryPraise·코치 질문.

    complete_analysis 호출 **전에만** 호출한다 (27-06 게이트 — motionAlignment
    선례와 동일 위치 규율). 부작용 = result 신규 키 4개(mission/missionOutcome/
    summaryPraise/coachQuestions) + records 항목의 additive 확장 키
    (models.DEDUCTION_RECORD_EXTENSION_KEYS)뿐 — 기존 키 무변경(setdefault),
    채점 무접촉. prev_doc = 기존 mode3 경로 get_previous_analysis 결과 재사용
    (신규 쿼리 0 — mission.py 의 motionId 가드가 same-mode-only 실측 사실을 방어).
    전체 실패해도 분석은 완주한다 (상위 try — T-32-20/SP-3).
    """
    try:
        from sunity_shared.analysis import mission as mission_mod
        from sunity_shared.analysis import phrasebook

        breakdown = result.get("deductionBreakdown")
        records = breakdown.get("records") if isinstance(breakdown, dict) else None
        if not isinstance(records, list):
            records = []

        # (1)+(2) recordId 각인 + 문구집 3단·tolerance 병합 — record 단위 격리.
        for i, rec in enumerate(records):
            if not isinstance(rec, dict):
                continue
            criterion = rec.get("criterion")
            if not isinstance(criterion, str) or not criterion:
                continue
            try:
                # 안정 조인 키 — 방출 시 1회 각인 (contract.md §12.3 형식).
                rec.setdefault("recordId", f"r{i:02d}:{criterion}")
                rule_id = rec.get("ruleId")
                phrases = phrasebook.assemble_phrases(
                    motion_id,
                    criterion,
                    rule_id if isinstance(rule_id, str) else None,
                )
                # 계약 확장 키만 병합 — failClosed 마커는 record 계약 밖이라 제외
                # (fail-closed 는 cueLine/exerciseId 부재로 판별, 32-05 스킴).
                for slot in models.DEDUCTION_PHRASE_KEYS:
                    value = phrases.get(slot)
                    if isinstance(value, str) and value and slot not in rec:
                        rec[slot] = value
                tol = _criterion_tolerance(criterion)
                if tol is not None and "tolerance" not in rec:
                    rec["tolerance"] = tol
            except Exception:  # noqa: BLE001 - record 1건 실패는 그 record 만 (리뷰 반영)
                log.exception(
                    "record 문구 조립 실패 — 해당 record 만 문구 없이 통과 "
                    "uid=%s analysis_id=%s idx=%d",
                    uid, analysis_id, i,
                )

        # (3) 미션 체인 — prev.result.mission (motionId 가드는 순수 함수 측).
        prev_mission: dict | None = None
        if isinstance(prev_doc, dict):
            prev_result = prev_doc.get("result")
            if isinstance(prev_result, dict):
                pm = prev_result.get("mission")
                prev_mission = pm if isinstance(pm, dict) else None

        safety_flags = result.get("safetyFlags")
        if not isinstance(safety_flags, list):
            safety_flags = None

        mission: dict | None = None
        try:
            mission = mission_mod.select_mission(
                records, safety_flags, prev_mission, motion_id
            )
            if mission is not None:
                result["mission"] = mission
        except Exception:  # noqa: BLE001 - 미션 실패는 미션만 미방출 (항목 격리)
            mission = None
            log.exception(
                "mission 선정 실패 — 미션 미방출 uid=%s analysis_id=%s",
                uid, analysis_id,
            )

        outcome: dict | None = None
        try:
            outcome = mission_mod.derive_mission_outcome(
                prev_mission, records, mode, motion_id
            )
            if outcome is not None:  # mode3 + prev 보유 시에만 (mode1/None 생략)
                result["missionOutcome"] = outcome
        except Exception:  # noqa: BLE001 - outcome 실패는 outcome 만 미방출
            outcome = None
            log.exception(
                "missionOutcome 산출 실패 — 미방출 uid=%s analysis_id=%s",
                uid, analysis_id,
            )

        # (4) summaryPraise — 잘한 점 단일 원천 (리뷰 blocker 5).
        try:
            praise = phrasebook.assemble_praise(
                outcome,
                _clean_praise_dimensions(result, mode),
                _criteria_met_for_praise(records, breakdown),
            )
            if praise is not None:
                result["summaryPraise"] = praise
        except Exception:  # noqa: BLE001 - praise 실패는 praise 만 미방출
            log.exception(
                "summaryPraise 조립 실패 — 미방출 uid=%s analysis_id=%s",
                uid, analysis_id,
            )

        # (5) coachQuestions 자동 수집 (D-28/D-29).
        try:
            questions = _collect_coach_questions(result, mission)
            if questions:
                result["coachQuestions"] = questions
        except Exception:  # noqa: BLE001 - 질문 실패는 질문만 미방출
            log.exception(
                "coachQuestions 수집 실패 — 미방출 uid=%s analysis_id=%s",
                uid, analysis_id,
            )
    except Exception:  # noqa: BLE001 - 방출 전체 실패도 분석 완주 (SP-3, T-32-20)
        log.exception(
            "32-09 번역 레이어 방출 전체 실패 — 분석 완주 유지 uid=%s analysis_id=%s",
            uid, analysis_id,
        )


def _process(bucket: str, key: str, uid: str, analysis_id: str) -> None:
    _ensure_adapters()
    # Phase 27 SPD-01 — stage-timing 계측 (27-RESEARCH Pattern 6). D-01 before/after
    # 표의 데이터 소스. 계약 = analysis.ts timingsMs? + contract.md (backend/audit 전용).
    # flat dict[str, int] 만 누적 → complete_analysis 직전 result["timingsMs"] 부착.
    timings_ms: dict[str, int] = {}
    firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_QUEUED)

    meta = firestore_admin.get_analysis(uid, analysis_id)
    if meta is None:
        raise RuntimeError(f"분석 문서 없음 users/{uid}/analyses/{analysis_id}")
    mode = meta.get("mode")

    # Phase 27 D-02 — status 갱신을 실제 단계 경계로 교정 (연속 write 해체). 과거엔
    # FRAME_EXTRACTION + POSE_ANALYSIS 를 여기서 **작업 전에 연달아** write 해 앱 진행률이
    # 즉시 다음 단계로 점프(85% 정지 오인, 27-RESEARCH D-02)했다. FRAME_EXTRACTION 은 영상
    # 다운로드+프레임 추출 시작 전에만 write; POSE_ANALYSIS 는 포즈 추출(from_local) 완료
    # 후 write (아래 prefetch try 안). enum/PIPELINE_SEQUENCE 추가 0 — 호출 위치만 이동.
    # PROGRESS_PCT 재배분은 27-07 (loading.tsx Math.max 단조 → 시점 이동만으로 역행 0).
    firestore_admin.update_analysis_status(
        uid, analysis_id, models.STATUS_FRAME_EXTRACTION
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
    keep_local_video = (
        _gemini_enabled()
        or _gemini_vision_enabled()
        or _gemini_vision_veto_enabled()
    )
    # ── 27-05 Task 1 seam (HIGH-1) — 다운로드와 포즈 추출 분리 ──
    # `_download_analysis_video` 반환 시점 = "다운로드 완료·포즈 미시작" = caller-visible
    # prefetch seam (Task 2 가 이 라인 뒤·frame_extract/RTMW 앞에 prefetch submit 삽입).
    # 2단 호출이라도 다운로드 1 / frame_extract 1 / RTMW estimate 1 불변 (T-06-02-06).
    local_video_path_dl = _download_analysis_video(
        bucket, key, timings_ms=timings_ms, analysis_id=analysis_id
    )
    # ── Phase 27 SPD-02 / D-04 — GeminiFileSession (분석-로컬) ──
    # 학생 영상 File API 업로드를 분석당 1회로 축약하고 핸들을 scene_finder/recognizer/veto/
    # coach B 가 공유한다 (중복 4~5회 → 1회, 27-RESEARCH 호출 인벤토리). 세션은 분석-로컬 —
    # 모듈 전역 캐시 금지(분석 간 상태 오염 0). 종료 delete 는 outer finally 의 session.close()
    # 일괄 1회 (NoHuman/NotPole 조기 raise 경로 포함, 20GB 적체 재발 방지 / TTL 최후 안전망).
    # 27-05 D-03: 세션은 포즈 추출 전에 생성 — 학생 업로드를 prefetch 스레드로 시작하기 위함.
    from sunity_shared.gemini.file_session import GeminiFileSession  # lazy (Lambda 250MB)
    session = GeminiFileSession()

    # Path A production 정합 (2026-06-05): mode=expert = motion known case
    # (사용자가 referenceMotionId 선택). recognizer.motion_query_hint 박제 →
    # Gemini extractor 가 알려진 motion 기준 key moment 추출 (default 'auto' 폴백 차단).
    # mode=self (mode3) = motion 미상 (본인 영상 비교) → hint=None (Gemini 'auto').
    #
    # WR-07 (2026-06-08 review): module-global singleton (_RECOGNIZER) 가 SQS
    # 메시지 / BackgroundTask 간 공유됨. 이전 분석이 set 한 hint 가 다음 분석에
    # leak 하면 Gemini 가 잘못된 motion 으로 biased. **항상** rebind (None 또는
    # 새 motion_id) — set/unset 분기 X.
    # 27-05 D-03 순서 제약: rebind 를 prefetch submit **이전**으로 이동 (module-global
    # hint leak 방지 — 27-RESEARCH 공유 상태 표). 입력(recognizer/meta/mode)은 포즈 이전
    # 가용 — 포즈 산출물 무관.
    ref_motion_id = meta.get("referenceMotionId")
    if hasattr(recognizer, "motion_query_hint"):
        recognizer.motion_query_hint = (
            str(ref_motion_id)
            if mode == models.MODE_EXPERT and ref_motion_id
            else None
        )
    # is_reference 박제: S3 key prefix 1차 + Firestore mode 2차 (R-W3 정합).
    is_reference_local = _resolve_is_reference(key, meta)

    # ── Phase 27 D-03 (SPD-03) — 업로드 prefetch 겹치기 (다운로드 직후·포즈 전) ──
    # env 게이트 하에, 학생 영상 File API 업로드 + scene_finder 를 백그라운드 스레드로
    # 시작해 frame_extract/RTMW(포즈) 그늘에 숨긴다 (27-RESEARCH Pattern 2). executor 는
    # 분석-로컬(분석 간 SERIAL 불변 — 모듈 전역 금지, 27-PATTERNS No Analog: 이 파일이
    # 향후 analog). 포즈 산출물 미의존 태스크만 prefetch (업로드 / scene_finder). recognizer
    # moment extractor·기준 영상 prefetch 는 27-05 범위 밖(SUMMARY 근거): recognize 는
    # angles 의존이고 moment 주입은 recognizer 모듈 수정 필요(채점 코어·선언 파일 밖).
    prefetch_active = keep_local_video and _gemini_upload_prefetch_enabled()
    executor = (
        ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini")
        if prefetch_active
        else None
    )
    student_handle_future = None
    scene_future = None
    try:
        if executor is not None:
            # keep_local_video=True 이므로 다운로드 파일이 아직 존재 (from_local 미실행).
            student_handle_future = executor.submit(
                session.get_or_upload, local_video_path_dl
            )

            def _scene_prefetch(
                _path: str = local_video_path_dl,
                _is_ref: bool = is_reference_local,
                _hf=student_handle_future,
            ) -> dict | None:
                # 핸들 준비되면 재사용(업로드 dedupe), 없으면 scene_finder 자체 업로드 폴백.
                handle = _hf.result() if _hf is not None else None
                return _call_wave1_scene_finder(
                    local_video_path=_path,
                    is_reference=_is_ref,
                    preuploaded_handle=handle,
                )

            scene_future = executor.submit(_scene_prefetch)
            # submit 시점 마커 — submit-before-rtmw 로그 순서 검증(HIGH-1). dict 미기록,
            # 마커 전용 (27-01 stage_timing 포맷 정합). 이 라인이 아래 frame_extract/RTMW
            # 보다 앞이라 로그 순서상 prefetch_submit < rtmw 가 보장된다.
            log.info(
                "stage_timing analysis_id=%s stage=gemini_upload_prefetch_submit elapsed_ms=%d",
                analysis_id, 0,
            )

        # 포즈 추출 (frame_extract + RTMW) — prefetch 스레드와 겹쳐 실행.
        inputs = _extract_video_analysis_inputs_from_local(
            local_video_path_dl, default_pole,
            keep_local_video=keep_local_video,
            timings_ms=timings_ms,  # Phase 27 SPD-01 — frame_extract/rtmw 계측
            analysis_id=analysis_id,
            # WR-02 fix (27-REVIEW): prefetch 활성이면 추출-실패 즉시-unlink 봉인 —
            # 업로드 future 생존 중 unlink 레이스 0. 정리는 아래 except 가 join 후 수행.
            unlink_on_error=(executor is None),
        )
        angles = inputs.angles
        student_profile = inputs.student_profile  # R4 fix — non-null
        pose_frames = inputs.pose_frames
        local_video_path_obj = inputs.local_video_path
        local_video_path = str(local_video_path_obj) if local_video_path_obj else None
        # Phase 27 SPD-04 (Task 3, Pattern 7) — 학생 9fps/640px 프레임 캐시. 게이트 ON
        # (RunPod)일 때만 보존해 still-pair/ fault_zoom 재추출을 소멸(디코딩 3회→1회).
        # Lambda 폴백(STUDENT_FRAME_CACHE=0)은 None → 기존 재추출 경로 유지(A5 메모리).
        cached_user_frames = (
            inputs.frames if _student_frame_cache_enabled() else None
        )

        # Phase 27 D-02 — 포즈 추출(frame_extract + RTMW) 완료 후 POSE_ANALYSIS write
        # (실제 단계 경계). 과거엔 작업 전 FRAME_EXTRACTION 와 연속 write 됐다.
        firestore_admin.update_analysis_status(
            uid, analysis_id, models.STATUS_POSE_ANALYSIS
        )

        # 학생 핸들 join (prefetch) 또는 동기 폴백. 업로드 실패(None)는 각 모듈이 자체
        # 업로드로 graceful 폴백 (분석 비차단 — moment extractor 폴백도 27-04 fix 로 누수 0).
        if student_handle_future is not None:
            student_video_handle = student_handle_future.result()
        else:
            student_video_handle = (
                session.get_or_upload(local_video_path) if local_video_path else None
            )

        # ── Plan 17-02 Wave 1 — 영역 C Finding join/호출 (RTMW estimate 직후 / KISMAM 직전) ──
        # B4 hard gate — local_video_path 만 사용 (S3 재다운로드 / RTMW 재실행 0). graceful —
        # find_scene_flags 예외 / GEMINI_FINDING_ENABLED OFF / local path 없음 시 None 반환.
        with _stage(timings_ms, analysis_id, "scene_finder"):  # Phase 27 SPD-01
            if scene_future is not None:
                scene_result = scene_future.result()  # prefetch join
            else:
                scene_result = _call_wave1_scene_finder(
                    local_video_path=local_video_path,
                    is_reference=is_reference_local,
                    preuploaded_handle=student_video_handle,  # Phase 27 D-04 세션 핸들 공유
                )
    except Exception:
        # 조기 실패 (outer try 밖) — future join 먼저(Pitfall 3), 그 다음 세션 즉시 정리
        # (veto/coach 미도달 → outer finally session.close() 미실행이라 여기서 leak 0).
        if executor is not None:
            executor.shutdown(wait=True)
        # WR-02 fix (27-REVIEW): 학생 temp unlink 는 future join **후** 여기서 수행 —
        # 추출-실패 즉시-unlink(unlink_on_error=False 로 봉인)의 이관분. missing_ok:
        # 추출 성공 후 keep_local_video=False 경로가 이미 지웠어도 안전 (이중 unlink 0).
        Path(local_video_path_dl).unlink(missing_ok=True)
        try:
            session.close()
        except Exception:  # noqa: BLE001 - 조기 실패 세션 정리 실패는 분석 흐름 무관
            log.warning(
                "prefetch 조기 실패 세션 정리 실패 (graceful) analysis_id=%s", analysis_id
            )
        raise
    finally:
        # Pitfall 3 — 모든 prefetch future join(shutdown wait=True) 후 진행. executor 는
        # 분석-로컬이라 여기서 폐기. temp unlink 는 outer finally 또는 위 except(join 후)
        # — future 생존 중 unlink 0 (WR-02 fix 로 추출-실패 즉시-unlink 도 봉인됨).
        # 성공 경로에서는 위 .result() 로 이미 join 됨 (shutdown 은 no-op). 실패 경로는 위
        # except 가 join 후 raise (여기 shutdown 은 idempotent no-op).
        if executor is not None:
            executor.shutdown(wait=True)

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
    # fault-zoom (belle 2026-06-21) — Mode1 결함 부위 확대 비교용 reference keypoint 좌표.
    # EXPERT 분기에서 ref doc 가 있을 때 채움. outer scope 초기화 (late ref scope 의존 회피).
    reference_keypoint_report_dict: dict | None = None
    # fault-zoom Mode3 — 지난 분석 doc(현재 vs 지난 영상 변화 비교). SELF 분기에서 채움.
    mode3_prev: dict | None = None
    # Phase 28-04 — mode3 second+ DTW MotionMatch(현재↔지난 영상). SELF 분기의
    # _mode3_comparison 이 채움(첫 분석/prev 부재 = None). motionAlignment 방출 +
    # mode3 fault_zoom 같은-pose 프레임 정렬용. reference_dtw_match 와 동일 수명 관리.
    prev_dtw_match = None
    # fault-zoom B1 (belle 2026-06-21) — mode1 DTW match(user↔reference 프레임 정렬).
    # 확대 비교에서 학생 worst 프레임 ↔ 기준의 같은 pose 프레임을 캡처해 납득성 ↑.
    reference_dtw_match = None
    # Phase 28-04 (ALGN-01) — motionAlignment 방출용 reference angles fps. ref doc 의
    # keypointReport.fps(phase4_v1=18.0, 28-01 live doc 실측)에서 읽는다 — 18.0 하드코딩
    # 금지(재처리 시 방어, I1). EXPERT 분기에서 대입, <=0 이면 build 가 degenerate
    # 'disabled' 방출(28-02 W3). reference_dtw_match 와 동일 수명 관리.
    reference_kp_fps = 0.0
    # 23-02 Task 5 — frame-specific 각도 정량화용 기준 영상 각도 (a_ref). Mode1 에서만 채움.
    # Mode3 는 None → collect 가 mode3_held 로 보류, quantification 미산출.
    reference_angles_for_veto = None
    # split deficit (reference_relative, mode1 only) — max(0, 정은지 max-split − 학생 max-split).
    # Mode3/legacy 는 None → split_angle 미방출(honest 0). 아래 Mode1 블록에서만 채움.
    split_deficit_deg = None

    # R2 wiring — target 영상 torso px 산출 (compare_body_profiles target_torso_px arg).
    target_torso = _extract_target_torso_px(pose_frames)

    try:
        # 기술 인식(swappable) → 절대 차원(라인/안정성)은 기준 영상 없이 항상 산출.
        # Plan 5-03 박제 — recognize(angles, frames=local_video_path) 호출. Gemini
        # 어댑터는 frames 인자 (video path) 를 File API 입력으로 사용. Fallback 은
        # frames 인자 ignore (Protocol 정합 — TestProtocolCompat 박제 검증).
        with _stage(timings_ms, analysis_id, "recognizer"):  # Phase 27 SPD-01
            profile = recognizer.recognize(
                angles,
                frames=local_video_path,
                preuploaded_handle=student_video_handle,  # Phase 27 D-04 세션 핸들 공유
            )
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
            with _stage(timings_ms, analysis_id, "ref_fetch_download"):  # Phase 27 SPD-01
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
            # ── split deficit (reference_relative) — 객관 inter-thigh 사이각 부족분 ──
            # 학생 max-split(peak, keypoints_4ch) vs 정은지 max-split. reference 는 re-seed 한
            # referenceSplitAngle(정은지 max-split) 우선; 미존재 시 bodyComparisonSourcePose
            # 1프레임 split 임시 대체. 둘 중 하나라도 NaN/부재면 None → split_angle 미방출.
            #
            # ⚠ 스코프 게이트(belle 2026-06-29 결정 "스코프 축소", [[split-measurement-doesnt
            # -discriminate-kipup]]): split 은 profile.required_split_deg 가 set 된 **진짜
            # split-요구 동작에만** 발화한다. pod 실측서 inter-thigh peak max-split 이 dynamic
            # 동작(kip-up/elbow-twist/pdshape) fault/correct 를 변별 못 함이 반증됨(antiparallel
            # thigh = 수직 라인도 180°라 saturate). kip-up 은 split 이 아니라 별 트랙(vision/
            # temporal). 비-split 동작에서 reference 대표프레임 다리벌림이 위양성 내는 것 차단
            # (belle #1 = 위양성 0). 현재 어떤 recognizer 도 required_split_deg 를 set 안 함 →
            # split 전면 미발화(infra 보존, 진짜 split 동작 지정 시 활성). 채점 자체는
            # reference_relative(값 아닌 presence 만 게이트로 사용 — 객관 180° 강요 아님).
            if profile is not None and getattr(profile, "required_split_deg", None) is not None:
                try:
                    student_split, _ = max_split(split_angle_series(inputs.keypoints_4ch))
                except Exception:  # noqa: BLE001 — 측정 실패는 split 미채점(honest 0)
                    student_split = float("nan")
                reference_split = ref.get("referenceSplitAngle")
                if reference_split is None and source_keypoints is not None:
                    try:
                        reference_split = float(split_angle_series(source_keypoints[None, :, :])[0])
                    except Exception:  # noqa: BLE001 — source-pose 형상/순서 불일치 → 미채점
                        reference_split = None
                if (
                    reference_split is not None
                    and float(reference_split) == float(reference_split)  # not NaN
                    and student_split == student_split  # not NaN
                ):
                    split_deficit_deg = max(0.0, float(reference_split) - float(student_split))
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
            # Phase 27 SPD-01 — dtw_scoring 단계 계측 (DTW 정렬 + KISMAM 평가 + 각도 차원).
            with _stage(timings_ms, analysis_id, "dtw_scoring"):
                deviation, match, user_seg, a_ref = _deviation_against(
                    angles, ref["angles"], num_joints
                )
                reference_dtw_match = match  # B1 — fault-zoom 같은-pose 프레임 정렬용.
                # 28-04 — ref angles fps 를 doc 메타에서 확보(하드코딩 금지, I1). phase4_v1
                # reference 11 doc 전부 keypointReport.fps==18.0 (28-01 실측 봉인).
                reference_kp_fps = float(
                    (((ref or {}).get("keypointReport")) or {}).get("fps") or 0.0
                )
                reference_angles_for_veto = a_ref  # 23-02 Task 5 — frame-specific 각도 정량화 입력.
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
            # fault-zoom — 기준 영상 keypoint 좌표(reference doc 저장분) 캡처.
            reference_keypoint_report_dict = ref.get("referenceKeypointReport")
            if ref.get("videoS3Key"):
                reference_video_url = _signed_get(bucket, ref["videoS3Key"])
                # Phase 20 — vision veto ON 일 때만 기준 영상을 local 로 다운로드
                # (B4 — _apply_vision_veto 가 어댑터에 path 전달, 어댑터 재다운로드 0).
                # delete=False 임시 파일 → veto 호출 후 finally 에서 _safe_unlink.
                if _gemini_vision_veto_enabled():
                    ref_tmp = None
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
                        # WR-03 fix (27-REVIEW): 생성된 temp 자체(ref_tmp.name)를 지운다.
                        # reference_local_video_path 는 성공 시에만 대입돼 이 시점엔 항상
                        # None(no-op) — 빈/부분 파일이 /tmp 에 적체되던 결함 (장수명 Pod).
                        if ref_tmp is not None:
                            _safe_unlink_local_video(ref_tmp.name)
                        reference_local_video_path = None
        else:  # MODE_SELF — 자기 성장. 절대 차원 + (이전 분석 있으면) 발전 델타.
            # 박제 (2026-06-07 belle): mode=MODE_SELF 박제 — mode1 (정은지) 분석을
            # prev 로 잡는 함정 fix. 같은 mode 안에서만 prev 검색.
            prev = firestore_admin.get_previous_analysis(
                uid, analysis_id, mode=models.MODE_SELF
            )
            mode3_prev = prev  # fault-zoom Mode3 (현재 vs 지난 영상 변화 비교) source.
            assessments, dimension_scores, overall, comparison, prev_dtw_match = _mode3_comparison(
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
        # 23-02 Task 5 (D-10/D-11/D-12 HIGH-1) — collect-before-coach 배선.
        # overall 계산(위 mode 분기) 직후·coach 작성 **이전에** verdict 를 수집한다.
        # build_result 를 앞당기지 않는다 — collect 는 keyword pre-build primitive 만 받으므로
        # numeric overall 만으로 호출 가능(D-12 MED-1). Gemini verdict 는 여기서 1회만 호출되고
        # 같은 ctx 가 아래 _apply_vision_veto(vision_fault_context=) 에서 재사용된다(geminiCallCount=1).
        # coach 주입 게이트: ctx.eligible_for_coach (=collection_status==candidate_verdict AND
        # cap_would_apply, D-13 MED-2). valid-but-not-cap-lowering(minor/88) 은 무주입(D-11 HIGH-1).
        # Phase 27 D-04 — 기준 영상도 세션 1회 업로드 후 핸들 공유 (veto 학생+기준 = 세션 핸들).
        # None(업로드 실패/Mode3 미다운로드) 시 assess_fault_context_video 가 자체 업로드 폴백.
        reference_video_handle = (
            session.get_or_upload(reference_local_video_path)
            if reference_local_video_path
            else None
        )
        with _stage(timings_ms, analysis_id, "veto_collect"):  # Phase 27 SPD-01
            vision_fault_context = _collect_vision_fault_context(
                overall_score=overall,
                dimension_scores=dimension_scores,
                mode=mode,
                local_video_path=local_video_path,
                angles=angles,
                profile=profile,
                reference_dtw_match=reference_dtw_match,
                reference_angles=reference_angles_for_veto,
                reference_video_path=reference_local_video_path,
                pose_frames=pose_frames,
                preuploaded_student_handle=student_video_handle,
                preuploaded_reference_handle=reference_video_handle,
                cached_user_frames=cached_user_frames,  # Phase 27 Task 3 — 재추출 소멸
            )
        # eligible 일 때만 support-gated root-cause 를 coach context 에 주입(graceful 무시 아님 —
        # writer 가 to_coach_context() 의 visionFault 키를 실제 프롬프트 causes 에 렌더).
        vision_coach_context = (
            vision_fault_context.to_coach_context()
            if vision_fault_context is not None and vision_fault_context.eligible_for_coach
            else None
        )
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
        # 23-02 Task 5 — vision-fault root-cause 를 coach context 에 주입(eligible 시에만).
        if vision_coach_context is not None:
            coach_context["visionFault"] = vision_coach_context
        # Phase 27 D-04 — 세션 핸들을 context 로 전달 (coach B retry 재업로드 0). Cerebras 는
        # 이 키를 무시(text-only). None 이면 GeminiCoachWriter 가 자체 업로드 폴백.
        if student_video_handle is not None:
            coach_context["preuploadedHandle"] = student_video_handle
        # ── Phase 13-C: 섹션형 듀얼 coach — 둘 다 호출 + 섹션 조립 + 계층형 폴백 ──
        # belle 2026-06-16 [[section-dual-coach-report]]. GEMINI_COACH_ENABLED=1
        # (default) 시 양쪽 writer 를 둘 다 호출해 섹션별로 조립 (원인/강사확인=Gemini,
        # 교정처방/부상위험=Cerebras). 한쪽 실패(재시도 후) → cross-fill, 둘 다 실패 →
        # coach_details={} (build_result 수치 폴백). env OFF 시 기존 Cerebras-only 보존.
        gemini_b_audit: dict | None = None
        if _coach_enabled():
            # (1) 양쪽 writer 동시 호출 + 시도당 재시도 1회 (단일 coach_context 공유, B3).
            # Phase 27 SPD-01 — coach_dual 단계 계측 (Gemini+Cerebras writer 라운드트립,
            # mode1 지배 비용 구간). 조립/cross-fill 은 CPU-cheap 이라 계측 밖.
            # Phase 27 Task 4 (SPD-05) — coach B(Gemini) ∥ Cerebras 동시 실행. 두 writer 는
            # 같은 immutable coach_context dict 를 읽기만 하므로 안전(B3 정합, 27-RESEARCH
            # Pattern 4). Gemini 는 스레드, Cerebras 는 메인 스레드에서 실행 후 join —
            # 벽시계 = max(B, Cerebras) 로 단축(순차 합 → 병렬 최댓값). 예외/재시도는
            # _call_coach_writer_with_retry 내부 graceful 규율 그대로(사후 점수 변경 0, D-03).
            # writer/write 바운드 메서드는 메인 스레드에서 미리 확보(스레드 내 lazy-init 경쟁 0).
            with _stage(timings_ms, analysis_id, "coach_dual"):
                _gemini_write = _ensure_gemini_coach_writer().write
                with ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="coach_gemini"
                ) as _coach_pool:
                    gemini_future = _coach_pool.submit(
                        _call_coach_writer_with_retry,
                        "gemini", _gemini_write, coach_context,
                    )
                    cerebras_result = _call_coach_writer_with_retry(
                        "cerebras", _COACH_WRITER.write, coach_context
                    )
                    gemini_result = gemini_future.result()
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
        with _stage(timings_ms, analysis_id, "assemble_misc"):  # Phase 27 SPD-01
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
        # Phase 24 (ND-01~07) — 투명 감점-합산 채점 seam (밴드 제거). 23-02 Task 5
        # (D-12 HIGH-1) collect→coach→build_result→_build_vision_quantification_result→apply
        # 순서. collect 가 위에서 verdict 를 1회 수집(vision_fault_context)했으므로, 여기서는
        # build_result 이후 named seam 으로 정량화를 1회 산출하고 같은 ctx 를 apply 에 재사용한다
        # (Gemini 재호출 0, geminiCallCount=1). apply 가 deduction_engine.tally 로 채점한 뒤
        # ctx.to_audit_dict(final_status=, breakdown_final=, quantification=) 로 audit 직렬화.
        # baseline_kind 는 profile 만 있으면 되므로 분기 전 1회 도출(BLOCKER B). measured
        # substrate 는 quantification 이 context 분기에만 존재하므로 분기 안에서 빌드(iter4 HIGH-1).
        # ctx None(레거시 경로) 이면 quantification=None → tally unavailable fallback.
        baseline_kind = _baseline_kind_for_profile(profile)
        if vision_fault_context is not None:
            # 정량화 입력 = collect 가 산출한 SelectedFramePair(그 프레임 keypoints) + 학생/기준
            # 각도. baseline 은 per-move 도출값(kip-up=floor named, hip_line 기본).
            selected_pair = (
                vision_fault_context.selected_frame_pairs[0]
                if vision_fault_context.selected_frame_pairs
                else None
            )
            quantification = _build_vision_quantification_result(
                fault_context=vision_fault_context,
                selected_frame_pair=selected_pair,
                student_angles=angles,
                reference_angles=reference_angles_for_veto,
                baseline_kind=baseline_kind,
            )
            # HIGH-2/iter4 HIGH-1 — 명명 substrate 를 seam 에서 1회 빌드(angles/profile/
            # assessments/dimension_scores/quantification 가 여기서만 동시 가용). apply 경로는
            # 절대 빌드하지 않는다(profile/assessments 부재 → no NameError surface). 0-100
            # dimension SCORE 를 deviation 으로 먹이지 않는다(HIGH-3).
            # 25-01 — Gemini 가 짚은(supported faultKey) 관절만 window-측정 eligible 로
            # 도출(좁은 pointed 매퍼 — line/torso/head_neck/grip broad 확장 금지). silent
            # 관절은 builder 안에서 기존 full-path DTW median 유지 (관절 단위 merge).
            from sunity_shared.analysis.vision_veto import (
                pointed_joints_from_supported_differences,
            )

            vision_pointed_joints = pointed_joints_from_supported_differences(
                vision_fault_context.supported_differences
            )
            measured_deviations = _build_deduction_measured_deviations(
                angles=angles,
                profile=profile,
                assessments=assessments,
                dimension_scores=dimension_scores,
                quantification=quantification,
                # 24-07 ① — mode1 에서 set(2987/2988), mode3/legacy 는 None → graceful 미방출.
                reference_dtw_match=reference_dtw_match,
                reference_angles=reference_angles_for_veto,
                # split — mode1 에서만 산출(reference_relative), mode3/legacy 는 None → 미방출.
                split_deficit_deg=split_deficit_deg,
                vision_pointed_joints=vision_pointed_joints,
            )
            result = _apply_vision_veto(
                result,
                local_video_path,
                angles,
                profile,
                mode=mode,
                reference_video_path=reference_local_video_path,
                vision_fault_context=vision_fault_context,
                quantification=quantification,
                measured_deviations=measured_deviations,
                baseline_kind=baseline_kind,
            )
        else:
            # 레거시 경로 (collect 미산출) — 기존 Gemini 호출 경로 graceful 폴백.
            # quantification 도 명명 substrate 도 없다 → tally unavailable fallback(iter4 HIGH-2).
            result = _apply_vision_veto(
                result,
                local_video_path,
                angles,
                profile,
                mode=mode,
                reference_video_path=reference_local_video_path,
                measured_deviations=None,
                baseline_kind=baseline_kind,
            )
        # quick-260704-fwb follow-up (pod 검증) — veto applied 인데 build_result 의
        # angle>=95 "거의 동일" 일반 팁이 듀얼 코치 detail2 를 통째로 버린 모순 해소.
        # build_result 는 veto apply 이전이라 최종 status 를 모름 → apply 이후 여기서
        # 표시만 재조립 (채점 무접촉). 실패해도 분석 비치명 (기존 tips 유지).
        try:
            result = assemble.rebuild_tips_for_vision_fault(
                result, assessments, coach_details
            )
        except Exception:  # noqa: BLE001 - 표시 재조립 실패는 분석 비치명
            log.exception("vision-fault tips 재조립 실패 — 기존 tips 유지")
        # fault-zoom (belle 2026-06-21) — 기준 영상은 아래 확대 비교 생성까지 살려두고
        # outer finally 가 정리한다(veto 직후 unlink 제거). keypoint_report_dict 빌드 후
        # _build_fault_zoom_comparisons 는 complete 이후 사후 렌더 (Phase 27 SPD-04 D-06 —
        # reference_local_video_path 는 outer finally unlink 前이라 그 시점에도 유효).
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

        # ── Phase 10 (Plan 10-02) — 결정론 부상 위험 신호 (SafetyFlag) ────────
        # D-01: 이 레이어는 LLM injuryRisk 프로즈와 독립 (대체/주입 X). force_signals
        # 직후 + complete_analysis 직전 1회 산출. reference plumbing (HIGH-3, source-proven):
        #   Mode1 = reference_angles_for_veto (= a_ref, 정은지 reshaped 기준 각도 행렬, :3060).
        #   Mode3 = _reshape_prev_angles(mode3_prev) (이전 영상 angles reshape).
        # safety_flags 가 student↔reference DTW 정렬을 INTERNAL 로 재계산하므로 match/
        # user_seg artifact 를 넘기지 않는다 (Mode3 match 는 어차피 scope 밖).
        # KNOWN v1 LIMITATION (SURFACED, silent no-op 아님): 첫 Mode-3 영상(이전 baseline
        # 부재)은 reference_angles=None → reference-anchored 플래그(D-04 trunk, D-03
        # asymmetry)가 발화 불가. 단 belle 의 Mode-3 "내 자세가 이러면 위험" 약속은 절대
        # D-05 관절 과신전 플래그(10-03, reference 불필요)가 Mode-3 에서도 발화해 충족한다.
        if mode == models.MODE_EXPERT:
            safety_reference_angles = reference_angles_for_veto  # a_ref (정은지)
        else:  # MODE_SELF
            safety_reference_angles = _reshape_prev_angles(mode3_prev)  # 이전 영상 (None=첫영상)
        _experience = (
            models.normalize_body_profile(meta.get("bodyProfile")) or {}
        ).get("experience")
        _reference_level = (
            ref.get("level") if mode == models.MODE_EXPERT and ref else None
        )
        try:
            _safety_flags = safety_flags_mod.compute_safety_flags(
                angles=angles,
                keypoints_4ch=inputs.keypoints_4ch,
                force_signals_report=force_signals_report,
                dimension_scores=dimension_scores,
                reference_angles=safety_reference_angles,
                experience=_experience,
                reference_level=_reference_level,
                mode=mode,
                profile=profile,
            )
            result["safetyFlags"] = [
                _dataclass_to_camel_case_dict(f) for f in _safety_flags
            ]
        except Exception:  # noqa: BLE001 - 부가 안전 레이어가 분석을 죽이면 안 됨 (graceful)
            log.exception(
                "safety_flags 산출 실패 — graceful skip (분석 흐름 유지) "
                "uid=%s analysis_id=%s",
                uid, analysis_id,
            )
        # ────────────────────────────────────────────────────────────────

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
        # quick-260704-fwb — vision veto applied 결함 부위(keypoint_set) 를 보완 운동
        # 매칭에 배선. applied + vision_fault_context 존재 시에만 도출, 그 외/예외는
        # None 폴백 = 기존 경로 불변 (도출 실패가 분석을 죽이지 않음).
        fault_keypoint_sets: list[str] | None = None
        try:
            _vv = result.get("visionVeto") if isinstance(result, dict) else None
            if (
                isinstance(_vv, dict)
                and _vv.get("status") == "applied"
                and vision_fault_context is not None
            ):
                _kp_sets: list[str] = []
                for _d in vision_fault_context.supported_differences or []:
                    _fk = (_d or {}).get("_faultKey")
                    _kp = getattr(_fk, "keypoint_set", None)
                    if isinstance(_kp, str) and _kp and _kp not in _kp_sets:
                        _kp_sets.append(_kp)
                for _rc in vision_fault_context.root_cause_hypotheses or []:
                    _fk = getattr(_rc, "fault_key", None)
                    _kp = getattr(_fk, "keypoint_set", None)
                    if isinstance(_kp, str) and _kp and _kp not in _kp_sets:
                        _kp_sets.append(_kp)
                if _kp_sets:
                    fault_keypoint_sets = _kp_sets
        except Exception:  # noqa: BLE001 - 보완운동 매칭 보강 실패는 분석 비치명
            log.exception(
                "vision fault keypoint_set 도출 실패 — 보완운동 기존 경로 폴백"
            )
            fault_keypoint_sets = None
        recommended_exercises = exercise_map.map_exercises(
            force_pattern_inference_dict,
            pain_areas=pain_areas,
            motion_id=getattr(profile, "motion_id", None),
            fault_keypoint_sets=fault_keypoint_sets,
        )
        # ────────────────────────────────────────────────────────────────

        # ── Phase 12 Wave 0B (Plan 12-01) — KeypointReport 산출 + wiring ──
        # D-12-E2 + R3 정합. KeypointOverlay (Wave 1+) 소비 source.
        # 분석 algorithm (DTW / threshold / Phase 6/7/8 calibration) = 9fps 유지.
        # 저장 시점에 18fps 로 선형 upsample (Phase 12 hotfix 2026-06-11 belle UAT
        # 1차: 빠른 회전 시 keypoint 끊김 + 끝부분 정지 자세 mitigation).
        # 18fps 선택 이유 — Firestore 40k index entry/document 한도 (당시 J=8 기준):
        #   30fps × 60s × 8 joints × 2 = 28,800 data + confidence/axis 합 ~60k → 한도 초과.
        #   18fps × 60s × 8 × 2 = 17,280 data + 기타 합 ~26k → 안전.
        # [32-14 J=12 갱신] 18fps × 60s × 12 × 2 = 25,920 data + confidence 12,960
        #   + axis/reliability 합 ~49.7k — naive 인덱싱 기준으론 40k 초과이나,
        #   analyses 컬렉션 keypointReport 리프는 인덱스 면제 적용
        #   ([[analyses-index-exemption-fix]] — 32-14 Task 3 에서 면제 상태 재확인).
        #   1MB 문서 한도는 실측 직렬화 바이트로 별도 검증 (32-14-SUMMARY).
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

        # fault-zoom (belle 2026-06-21) — Phase 27 SPD-04 (D-06) 사후 분리.
        # 렌더(ffmpeg 재디코딩 + crop 합성 + S3 업로드 = 후처리 주요분)는 complete_analysis
        # **이후**로 이동한다(아래 firestore_complete 블록 뒤). 여기서는 zoom 대상 존재
        # 여부만 판정해 pending 마커를 남긴다 — 점수를 먼저 앱에 도착시켜 체감 완료 시점을
        # 앞당긴다(time-to-first-result). 대상 없으면 faultZoomStatus 필드 자체 생략
        # (하위호환 판정 규칙 정합 — 부재=comparisons 유무로 판정). scalar 라 기존 complete
        # 검증 통과. 조건은 기존 Mode1/Mode3 호출부 게이트 그대로 재사용.
        fault_zoom_kind: str | None = None
        if (
            mode == models.MODE_EXPERT
            and reference_local_video_path is not None
            and keypoint_report_dict is not None
        ):
            fault_zoom_kind = "mode1"
        elif (
            mode == models.MODE_SELF
            and mode3_prev is not None
            and keypoint_report_dict is not None
        ):
            fault_zoom_kind = "mode3"
        if fault_zoom_kind is not None:
            result["faultZoomStatus"] = models.FAULT_ZOOM_STATUS_PENDING

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

        # Phase 27 SPD-01 — timingsMs 부착 (complete_analysis 직전). flat dict[str, int]
        # (nested-array 금지 정합 — [[firestore-nested-array-flat]]). backend/audit 전용,
        # 사용자 비노출 (contract.md timingsMs 절 + analysis.ts AnalysisResult.timingsMs?).
        # firestore_complete 단계는 complete_analysis **호출 자체** 를 감싸므로 timings_ms
        # 에 그 키가 들어가는 시점(with finally)이 complete_analysis 직렬화보다 뒤 →
        # 저장 dict 에는 미포함(로그 라인으로만 방출). 의도적 — 저장 재귀 방지.
        # Phase 28-04 (ALGN-01) — motionAlignment 방출 (complete_analysis 직전 — 27-06
        # 게이트: complete 후 result.* write 금지). 표현/재생 전용, 채점 무접촉 (28-CONTEXT).
        # user fps = frame_extractor 기본 target_fps 단일 출처(I1, 리터럴 9.0 금지).
        # mode1 = reference_dtw_match + ref doc keypointReport.fps(18fps phase4_v1, 28-01
        # 실측). mode3 = prev_dtw_match + 양측 파이프라인 9fps(prev angles 는 자기 분석의
        # 9fps 저장분 — Pitfall 6: mode1 의 18fps 변환을 여기 적용 금지, fps 는 인자).
        # mode1/mode3 는 상호 배타 분기이므로 주입 지점을 단일화하고 mode 별 fps 만 선택.
        _ma_frame_fps = _pipeline_frame_fps()
        if mode == models.MODE_EXPERT:
            _attach_motion_alignment(
                result,
                reference_dtw_match,
                user_fps=_ma_frame_fps,
                ref_fps=reference_kp_fps,
                uid=uid,
                analysis_id=analysis_id,
            )
        else:  # MODE_SELF — mode3 second+ (prev 부재/first = prev_dtw_match None → 미방출)
            _attach_motion_alignment(
                result,
                prev_dtw_match,
                user_fps=_ma_frame_fps,
                ref_fps=_ma_frame_fps,  # Pitfall 6 — 양측 9fps (ref 도 자기 9fps 저장분)
                uid=uid,
                analysis_id=analysis_id,
            )
        # ── Phase 32 (Plan 32-09) — 번역 레이어·미션 루프 방출 (complete 직전) ──
        # D-08/D-11/D-19/D-26~D-29 + 리뷰 blocker 1·2·5. 순수 dict 조립 — 외부 호출
        # 0, 신규 쿼리 0 (prev = 위 mode3 경로의 get_previous_analysis 재사용).
        # 채점 무접촉 — records 확장 키·result 신규 키 4개만 additive (32-03 스윕
        # 기준선 diff 0 이 acceptance). 실패해도 분석 완주 (helper 내 상위 try).
        _attach_translation_emission(
            result,
            mode=mode,
            motion_id=getattr(profile, "motion_id", None),
            prev_doc=mode3_prev,
            uid=uid,
            analysis_id=analysis_id,
        )
        result["timingsMs"] = timings_ms
        with _stage(timings_ms, analysis_id, "firestore_complete"):  # Phase 27 SPD-01
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

        # Phase 31 D-05 — correctedPose 자동 생성 enqueue. **fault-zoom 조건부 밖**
        # (H-01): 줌 카드 유무와 무관하게 판단되어야 하고, 여기서 실패해도 분석은
        # 이미 complete 라 사용자 결과에 영향이 없다. flag 기본 OFF 라 31-12 가
        # 켜기 전까지 운영 경로 비용 0 (enqueue 만 — 벤더 호출 0).
        if fault_zoom_kind == "mode1":
            _maybe_enqueue_corrected_pose(
                result=result,
                user_report=keypoint_report_dict,
                ref_report=reference_keypoint_report_dict,
                ref_video_path=reference_local_video_path,
                cached_user_frames=cached_user_frames,
                uid=uid,
                analysis_id=analysis_id,
                request_id=uuid.uuid4().hex,
            )

        # ── Phase 32 (Plan 32-16, D-18 B안) — 재생 중 큐 오디오 사후 합성 ────────
        # complete(status='done') 이후 표현물 스테이지 (fault_zoom 사후 분리 선례).
        # zoom(ffmpeg 재디코딩 수십 초)보다 **앞**에 두어 오디오가 먼저 도착 — 32-12
        # audioCue prefetch 성립 시점 단축. 합성은 문장 N개 Polly 호출(수 초)이라
        # zoom 지연 미미. timings_ms 는 이미 저장됨 → 사후 소요는 stage 로그
        # 라인으로만 (fault_zoom 관례). 실패 전부 graceful — 분석 무훼손 (SP-3).
        with _stage(timings_ms, analysis_id, "coach_audio"):
            _run_deferred_coach_audio(
                result=result, uid=uid, analysis_id=analysis_id, bucket=bucket
            )

        # Phase 27 SPD-04 (D-06) — fault_zoom 사후 렌더. complete_analysis 로 점수/verdict/
        # 감점 내역이 확정된 뒤(status='done'), zoom PNG 를 여기서 렌더해
        # update_analysis_fault_zoom(done/failed) 부분 업데이트로 도착시킨다. **분석 간
        # SERIAL 불변** — 다음 분석은 이 BackgroundTask 종료(finally) 후에만 시작하므로
        # 별도 태스크 불필요(27-RESEARCH Pattern 5). local_video_path/
        # reference_local_video_path 는 아래 outer finally unlink **前**이라 여기서 유효
        # (조기 raise 경로는 complete 미도달 → 이 블록/ pending 마커 모두 미실행 →
        # zoom 이 살아있는 temp 파일을 참조하지 못하는 경우 없음, Pitfall 3). fault_zoom
        # stage 로그는 계속 방출하되 timings_ms 는 이미 저장됨 → 사후 zoom 소요는 로그
        # 라인으로만(= MEDIUM-3 두-지표 분리의 데이터 소스: complete 까지 timingsMs 합 =
        # time-to-first-result, + 사후 fault_zoom 로그 = server task 총 시간).
        if fault_zoom_kind is not None:
            with _stage(timings_ms, analysis_id, "fault_zoom"):
                if fault_zoom_kind == "mode1":
                    _zoom_render = lambda: _build_fault_zoom_comparisons(
                        result,
                        local_video_path,
                        reference_local_video_path,
                        keypoint_report_dict,
                        reference_keypoint_report_dict,
                        profile,
                        uid,
                        analysis_id,
                        bucket,
                        dtw_match=reference_dtw_match,
                        cached_user_frames=cached_user_frames,  # Task 3 — 재추출 소멸
                    )
                else:  # mode3 — 현재 vs 지난 영상 변화 부위 확대 비교 (mode3=progress)
                    _zoom_render = lambda: _build_mode3_fault_zoom_comparisons(
                        result,
                        local_video_path,
                        keypoint_report_dict,
                        mode3_prev,
                        profile,
                        uid,
                        analysis_id,
                        bucket,
                        cached_user_frames=cached_user_frames,  # Task 3 — 재추출 소멸
                        dtw_match=prev_dtw_match,  # 28-04 — mode3 DTW 대응 프레임 정렬
                    )
                _run_deferred_fault_zoom(
                    render=_zoom_render, uid=uid, analysis_id=analysis_id
                )
            # Phase 27 Task 3 — zoom 렌더 완료 후 프레임 캐시 명시 해제(메모리 반환).
            # (inputs.frames 참조도 함수 종료 시 GC — cached 로컬만 즉시 끊는다.)
            cached_user_frames = None

        # ── Phase 32 (Plan 32-13, D-22/D-23) — 문장↔영상 스팟체크 사후 스테이지 ──
        # firestore_complete **이후** (사후 표현물 검수 — fault_zoom/coach_audio
        # 사후 분리 선례, 셋 중 마지막). 동기 채점 경로에 호출 금지 — 구조로 속도
        # 예산 보호 (phase 27 1분대 회귀 0). timings_ms 는 이미 저장됨 → 사후
        # 소요는 stage 로그 라인으로만 (fault_zoom 관례). 프레임은 inputs.frames
        # 재사용 (cached_user_frames 해제 후에도 유효 — 재추출/재디코딩 0).
        # 실패 전부 graceful — 분석 무훼손 (SP-3, T-32-31).
        with _stage(timings_ms, analysis_id, "spot_check"):
            _run_deferred_spot_check(
                result=result,
                angles=angles,
                profile=profile,
                frames=inputs.frames,
                uid=uid,
                analysis_id=analysis_id,
            )
    finally:
        # Phase 27 D-04 — 세션 File API 핸들 일괄 delete = 분석당 1회 (unlink 보다 앞).
        # NoHuman/NotPole 조기 raise 경로 포함 도달 보장 (Pitfall 2) — 20GB 적체 재발 방지.
        # best-effort (delete 예외는 나머지 정리/분석을 막지 않음, close() 내부 규율).
        try:
            session.close()
        except Exception:  # noqa: BLE001 - 세션 정리 실패는 분석 흐름 차단 0
            log.warning("GeminiFileSession close 실패 (graceful) analysis_id=%s", analysis_id)
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
