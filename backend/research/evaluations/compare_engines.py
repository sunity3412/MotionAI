"""MediaPipe vs NLF 회귀 검증 (D-13, D-14, D-15, D-16).

**Wave 2 시점** — NLF는 아직 sunity_shared.analysis.pose_estimator (옛 위치)에서
import. R&D 격리 (Plan 04)는 본 회귀 검증 belle 승인 후에 진행.

H-1 박제: atomic swap 직전 게이트 — Wave 3 (Plan 04 격리 + Plan 05 swap)는
본 스크립트의 belle checkpoint가 approved resume-signal을 내야만 진행.

검증 기준 (D-14, D-15 박제):
  D-14: 점수 갭 허용 ±5점 이내 (within_tolerance_5pt).
        갭이 ±5점 초과면 D-16에 따라 atomic swap 보류.
  D-15 ①: 정은지 영상이 MediaPipe에서 ≥70점 (mediapipe_score_ge_70).
           고수 위양성 0 — SCORE-04 직결.
  D-15 ②: Top-3 실패 원인 ≥2/3 겹침 (top3_overlap_2_of_3).
  D-15 ③: MediaPipe 평균 keypoint confidence ≥ threshold (avg_confidence_ok).
  D-15 ④: MediaPipe Heavy ms/frame 측정 (mediapipe_ms_per_frame).

A9 threshold 박제:
  AVG_CONFIDENCE_THRESHOLD = 0.5 — placeholder.
  Plan 06 Task 2 회귀 결과 후 belle가 5영상 avg_confidence 분포 확인해 확정.
  확정값 반영 위치: 본 파일 AVG_CONFIDENCE_THRESHOLD + plan.md 갱신.

Plan 01-08 추가 — --engine 옵션:
  nlf-vs-mediapipe         (기본, 기존 호환)
  nlf-vs-mediapipe-lifter  MP+MotionBERT vs NLF 비교 (Wave 3 진입 판정용)
  mediapipe-vs-mediapipe-lifter  순수 lifter 효과 비교

실행 경로 (L-2 박제): /workspace/SunityMotion
  cd /workspace/SunityMotion
  python -m backend.research.evaluations.compare_engines \\
    --motions ref-ballerina-spin ref-front-hook-spin ref-plank-spin \\
              ref-invert-butterfly-combo ref-gemini-to-ayesha-combo \\
    --out backend/research/evaluations/reports/compare_$(date +%Y%m%d).json \\
    --engine nlf-vs-mediapipe-lifter

출력: JSON 보고서 + Markdown 보고서 (--out 경로와 같은 이름, .md 확장자).
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# --engine 옵션 허용 값 (Plan 01-08 T-4)
EngineMode = Literal[
    "nlf-vs-mediapipe",           # 기본: 기존 호환
    "nlf-vs-mediapipe-lifter",    # MP+MotionBERT vs NLF (Wave 3 진입 판정용)
    "mediapipe-vs-mediapipe-lifter",  # lifter 효과 단독 비교
]
_ENGINE_MODE_CHOICES = ("nlf-vs-mediapipe", "nlf-vs-mediapipe-lifter", "mediapipe-vs-mediapipe-lifter")

import numpy as np

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# ── 검증 기준 상수 ─────────────────────────────────────────────────────────

# D-14: 점수 갭 허용 범위 (overall 100점 만점)
SCORE_GAP_TOLERANCE_PT: float = 5.0

# D-15 ①: 정은지 영상 최소 점수 (위양성 방지 — SCORE-04 직결)
MEDIAPIPE_MIN_SCORE_FOR_EXPERT: float = 70.0

# D-15 ③: MediaPipe 평균 keypoint confidence 임계값
# A9 belle 보류 — placeholder. Plan 06 Task 2 회귀 결과 후 belle가 확정값으로 갱신.
# 5영상 avg_keypoint_confidence 분포를 보고 0.5 / 0.55 / 0.6 중 결정.
AVG_CONFIDENCE_THRESHOLD: float = 0.5

# D-13: 기본 검증 영상 5개 (정은지 기준 모션 motion_id)
DEFAULT_MOTIONS: tuple[str, ...] = (
    "ref-ballerina-spin",
    "ref-front-hook-spin",
    "ref-plank-spin",
    "ref-invert-butterfly-combo",
    "ref-gemini-to-ayesha-combo",
)

# S3 기준 모션 영상 키 경로 패턴 (bucket 내부)
_REFERENCE_VIDEO_PREFIX = "reference"

# ── EngineResult 데이터 계약 ───────────────────────────────────────────────


@dataclass
class EngineResult:
    """한 영상 + 한 엔진의 분석 결과 요약.

    overall_score: 100점 만점 종합 점수.
    dimension_scores: {'line': ..., 'angle': ..., 'stability': ...} — 차원별.
    top3_failures: ['left_knee_bend', 'hip_rotation', ...] — 점수 낮은 상위 3 차원.
    avg_keypoint_confidence: MediaPipe confidence 평균 (D-15 ③). NLF는 NaN.
    ms_per_frame: 엔진 추론 시간 (프레임당 밀리초, D-15 ④).
    """

    overall_score: float
    dimension_scores: dict[str, float] = field(default_factory=dict)
    top3_failures: list[str] = field(default_factory=list)
    avg_keypoint_confidence: float = float("nan")
    ms_per_frame: float = float("nan")


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────


def _download_video(s3_key: str, bucket: str, dest: Path) -> None:
    """S3에서 reference 영상 다운로드. T-1-03: 임시 경로에만 저장."""
    import boto3  # Lambda 런타임 또는 Pod 환경 제공

    s3 = boto3.client("s3")
    log.info("downloading s3://%s/%s → %s", bucket, s3_key, dest)
    s3.download_file(bucket, s3_key, str(dest))


def _extract_frames(video_path: str) -> np.ndarray:
    """영상 → (T,H,W,3) RGB uint8 numpy 배열.

    lazy import: FfmpegFrameExtractor는 imageio/ffmpeg 의존 — 모듈 load 시점엔 불필요.
    9fps / 640px 다운샘플 (frame_extractor.py 기본값).
    """
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    extractor = FfmpegFrameExtractor()
    frames = extractor.extract(video_path)
    return frames


def _extract_avg_confidence(pose_frames: list) -> float:
    """list[PoseFrame] → 평균 keypoint confidence.

    D-15 ③: MediaPipe 엔진 결과에만 유효. NLF 결과는 NaN 반환.
    """
    confidences: list[float] = []
    for frame in pose_frames:
        # PoseFrame.keypoints_3d: dict[str, Keypoint3D]
        if not hasattr(frame, "keypoints_3d"):
            continue
        for kp in frame.keypoints_3d.values():
            if hasattr(kp, "confidence") and not np.isnan(kp.confidence):
                confidences.append(kp.confidence)
    if not confidences:
        return float("nan")
    return float(np.mean(confidences))


def _compute_top3_failures(dimension_scores: dict[str, float]) -> list[str]:
    """차원별 점수 → 점수 낮은 Top-3 실패 원인 반환.

    점수 낮을수록 실패 — 오름차순 상위 3개.
    """
    if not dimension_scores:
        return []
    sorted_dims = sorted(dimension_scores.items(), key=lambda x: x[1])
    return [k for k, _ in sorted_dims[:3]]


def _run_mediapipe(frames: np.ndarray, pole_axis: object) -> tuple[list, dict]:
    """MediaPipe 엔진으로 분석 수행 → (pose_frames, score_payload).

    lazy import: mediapipe는 RunPod x86_64에서만 가용 (Pitfall 1).
    score_payload: {'overall': float, 'dimensions': dict, 'top3': list, 'avg_conf': float}
    """
    from sunity_shared.analysis.features import compute_joint_angles, joint_uncertainty
    from sunity_shared.analysis.pose_engines.mediapipe_engine import MediaPipePoseEngine
    from sunity_shared.analysis.pose_frame import to_coco17_array
    from sunity_shared.analysis.temporal import temporal_fill

    engine = MediaPipePoseEngine()
    pose_frames = engine.estimate(frames, pole_axis)

    # COCO-17 배열 변환 (T,17,4) — 기존 downstream 인터페이스
    kp_array = to_coco17_array(pose_frames)
    angles = compute_joint_angles(kp_array)
    # uncertainty 는 (T,J) joint-angle-level. 운영 pipeline 과 동일하게 joint_uncertainty 사용.
    filled_angles = temporal_fill(angles, uncertainty=joint_uncertainty(kp_array))

    # dimensions 점수 계산
    score_payload = _score_from_angles(filled_angles, kp_array)

    # avg_confidence (D-15 ③)
    avg_conf = _extract_avg_confidence(pose_frames)
    score_payload["avg_conf"] = avg_conf

    return pose_frames, score_payload


def _run_nlf(frames: np.ndarray, pole_axis: object) -> tuple[np.ndarray, dict]:
    """NLF 엔진으로 분석 수행 → (kp_array, score_payload).

    **Wave 2 시점** — NLF는 아직 sunity_shared.analysis.pose_estimator (옛 위치)에서
    import. H-1 박제: atomic swap 직전 게이트이므로 격리 전 import 경로 사용.

    NLF는 PoseFrame을 반환하지 않고 (T,17,4) numpy 배열을 직접 반환.
    confidence 개념이 MediaPipe와 다름 (uncertainty 역방향) — avg_conf는 NaN.

    GPU 필요: NLF는 CUDA 필수 (CPU에서 NaN 발산). RunPod Pod에서만 실행.
    """
    # Wave 2 시점 옛 위치 import (H-1 박제 — atomic swap 직전)
    from sunity_shared.analysis.features import compute_joint_angles, joint_uncertainty
    from sunity_shared.analysis.pose_estimator import NlfPoseEstimator  # noqa: PLC0415 — Wave 2 옛 위치
    from sunity_shared.analysis.temporal import temporal_fill

    estimator = NlfPoseEstimator()
    kp_array = estimator.estimate(frames)  # (T,17,4) = COCO-17 · (x,y,z,uncertainty)

    angles = compute_joint_angles(kp_array)
    # 운영 pipeline (functions/pipeline/app.py) 과 동일: joint_uncertainty(kp_array) 는 (T,J).
    filled_angles = temporal_fill(angles, uncertainty=joint_uncertainty(kp_array))

    score_payload = _score_from_angles(filled_angles, kp_array)
    score_payload["avg_conf"] = float("nan")  # NLF: confidence 개념 없음

    return kp_array, score_payload


def _run_mediapipe_lifter(frames: np.ndarray, pole_axis: object) -> tuple[list, dict]:
    """MediaPipeWithLifterEngine 으로 분석 수행 → (pose_frames, score_payload).

    Plan 01-08 T-4-2: _run_mediapipe 패턴과 동일한 다운스트림 체인 사용.

    MediaPipeWithLifterEngine 은 MP 2D xy + MotionBERT z 를 합성 → COCO-17 PoseFrame.
    lazy import: mediapipe + torch 는 RunPod Pod 에서만 가용.

    score_payload: {'overall': float, 'dimensions': dict, 'top3': list, 'avg_conf': float}
    """
    from sunity_shared.analysis.features import compute_joint_angles, joint_uncertainty
    from sunity_shared.analysis.pose_engines.mediapipe_lifter_engine import (  # noqa: PLC0415
        MediaPipeWithLifterEngine,
    )
    from sunity_shared.analysis.pose_frame import to_coco17_array
    from sunity_shared.analysis.temporal import temporal_fill

    engine = MediaPipeWithLifterEngine()
    pose_frames = engine.estimate(frames, pole_axis)

    # COCO-17 배열 변환 (T,17,4) — 기존 downstream 인터페이스
    kp_array = to_coco17_array(pose_frames)
    angles = compute_joint_angles(kp_array)
    filled_angles = temporal_fill(angles, uncertainty=joint_uncertainty(kp_array))

    score_payload = _score_from_angles(filled_angles, kp_array)

    # avg_confidence (D-15 ③) — lifter confidence (1 - uncertainty_proxy 평균)
    avg_conf = _extract_avg_confidence(pose_frames)
    score_payload["avg_conf"] = avg_conf

    return pose_frames, score_payload


def _score_from_angles(angles: np.ndarray, kp_array: np.ndarray) -> dict:
    """관절각 배열 → 종합 점수 + 차원 점수 payload.

    기존 pipeline과 동일한 dimensions/kismam/assemble 체인을 사용.
    이 함수는 두 엔진 결과를 같은 다운스트림(compute_joint_angles, dimensions)으로
    넣어 공정한 비교를 보장한다.
    """
    from sunity_shared.analysis import dimensions, kismam, technique

    # 기술 프로파일 (FallbackRecognizer — 폴 동작 일반)
    profile = technique.FallbackRecognizer().recognize(angles)

    # 차원별 점수 계산 — 운영 pipeline (functions/pipeline/app.py:185) 과 동일 시그니처.
    # absolute_dimension_scores(angles, profile) 는 angles 와 profile 두 인자만 받는다.
    try:
        dim_scores = dimensions.absolute_dimension_scores(angles, profile)
    except Exception:
        log.exception("차원 점수 계산 실패 — 빈 scores 반환")
        dim_scores = {}

    # 종합 점수 계산 (100점 만점) — 함수명은 overall_from_dimensions.
    try:
        overall = dimensions.overall_from_dimensions(dim_scores)
    except Exception:
        log.exception("종합 점수 계산 실패 — 0.0 반환")
        overall = 0.0

    # Top-3 실패 원인 (D-15 ②)
    top3 = _compute_top3_failures(dim_scores)

    return {
        "overall": float(overall),
        "dimensions": {k: float(v) for k, v in dim_scores.items()},
        "top3": top3,
    }


# ── 공개 API ──────────────────────────────────────────────────────────────


def run_engine(
    engine_name: Literal["mediapipe", "nlf", "mediapipe-lifter"],
    video_s3_key: str,
    bucket: str,
) -> EngineResult:
    """한 영상에 대해 지정 엔진을 실행하고 EngineResult를 반환.

    T-1-03 박제: tempfile 사용 — 임시 다운로드 영상은 자동 cleanup.
    임시 파일 경로 이외에 영상 내용을 보관하지 않음.

    Plan 01-08 T-4: 'mediapipe-lifter' 엔진 추가
      MediaPipeWithLifterEngine (MP 2D + MotionBERT z) 로 추론.
      기존 'mediapipe' | 'nlf' 호환 유지.

    Args:
        engine_name: 'mediapipe' | 'nlf' | 'mediapipe-lifter'.
        video_s3_key: S3 내부 키 (예: "reference/ref-ballerina-spin.mp4").
        bucket: S3 버킷 이름.

    Returns:
        EngineResult — overall_score, dimension_scores, top3_failures,
                       avg_keypoint_confidence, ms_per_frame.

    Raises:
        ValueError: engine_name이 유효하지 않을 때.
        NoHumanError: 영상에서 사람을 못 찾을 때.
    """
    _valid = ("mediapipe", "nlf", "mediapipe-lifter")
    if engine_name not in _valid:
        raise ValueError(f"engine_name must be one of {_valid}, got {engine_name!r}")

    log.info("run_engine engine=%s key=%s bucket=%s", engine_name, video_s3_key, bucket)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        # 1. 영상 다운로드 (T-1-03: tempfile 자동 cleanup)
        _download_video(video_s3_key, bucket, Path(tmp.name))

        # 2. 프레임 추출
        frames = _extract_frames(tmp.name)
        T = len(frames)
        log.info("frames extracted T=%d", T)

        # 3. 폴 축 검출 (lazy import — cv2 필요)
        from sunity_shared.analysis.pole.detector import HoughPoleDetector
        pole_axis = HoughPoleDetector().detect(frames)

        # 4. 엔진 실행 시간 측정 (D-15 ④)
        start = time.perf_counter()

        if engine_name == "mediapipe":
            _, score_payload = _run_mediapipe(frames, pole_axis)
        elif engine_name == "mediapipe-lifter":
            _, score_payload = _run_mediapipe_lifter(frames, pole_axis)
        else:
            _, score_payload = _run_nlf(frames, pole_axis)

        elapsed_ms = (time.perf_counter() - start) * 1000

    ms_per_frame = elapsed_ms / T if T > 0 else float("nan")
    log.info(
        "engine=%s overall=%.1f ms_per_frame=%.1f",
        engine_name,
        score_payload["overall"],
        ms_per_frame,
    )

    return EngineResult(
        overall_score=score_payload["overall"],
        dimension_scores=score_payload.get("dimensions", {}),
        top3_failures=score_payload.get("top3", []),
        avg_keypoint_confidence=score_payload.get("avg_conf", float("nan")),
        ms_per_frame=ms_per_frame,
    )


def compare_engines(
    motion_ids: list[str],
    bucket: str = "sunity-motion-pilot-videos",
    engine_mode: str = "nlf-vs-mediapipe",
) -> dict:
    """motion_ids 목록에 대해 두 엔진을 비교하고 보고서 payload를 반환.

    D-13: 정은지 영상 5개 기본. D-14/D-15 게이트 4개 박제.
    summary.phase1_ready_to_swap이 True여야 Wave 3 진행 가능 (D-08/D-16/H-1).

    Plan 01-08 T-4: engine_mode 추가.
      'nlf-vs-mediapipe'          — 기존 호환 (기본값)
      'nlf-vs-mediapipe-lifter'   — MP+MotionBERT vs NLF (Wave 3 판정용)
      'mediapipe-vs-mediapipe-lifter' — lifter 효과 단독 비교

    엔진 이름 매핑:
      'nlf-vs-mediapipe':               engine_a='nlf', engine_b='mediapipe'
      'nlf-vs-mediapipe-lifter':        engine_a='nlf', engine_b='mediapipe-lifter'
      'mediapipe-vs-mediapipe-lifter':  engine_a='mediapipe', engine_b='mediapipe-lifter'

    보고서 키 명명:
      engine_a 결과 → 'engine_a', engine_b 결과 → 'engine_b'.
      기존 'nlf-vs-mediapipe' 모드에서는 backward compat 을 위해
      'nlf' / 'mediapipe' 키를 추가로 포함.

    Args:
        motion_ids: 비교할 motion_id 목록.
        bucket: S3 버킷 이름.
        engine_mode: 비교 모드 ('nlf-vs-mediapipe' | 'nlf-vs-mediapipe-lifter' | 'mediapipe-vs-mediapipe-lifter').

    Returns:
        {
          "engine_mode": str,
          "criteria": {...},           # 검증 기준값 (D-14, D-15)
          "generated_at": str,         # ISO 8601 UTC
          "motions": {                 # motion별 결과
            "<motion_id>": {
              "engine_a": {...},        # engine_a 결과
              "engine_b": {...},        # engine_b 결과
              # 기존 호환 (nlf-vs-mediapipe 모드 전용): "nlf", "mediapipe" 키 추가
              "gates": {
                "score_gap": float,
                "within_tolerance_5pt": bool,       # D-14
                "mediapipe_score_ge_70": bool,       # D-15 ① (engine_b 기준)
                "top3_overlap_2_of_3": bool,         # D-15 ②
                "avg_confidence_ok": bool,           # D-15 ③ (engine_b 기준)
                "mediapipe_ms_per_frame": float,     # D-15 ④ (engine_b ms)
              }
            }
          },
          "summary": {
            "all_within_tolerance": bool,
            "all_mediapipe_ge_70": bool,
            "all_top3_overlap_ok": bool,
            "all_avg_confidence_ok": bool,
            "phase1_ready_to_swap": bool,           # D-08 Wave 3 gate
          }
        }
    """
    if engine_mode not in _ENGINE_MODE_CHOICES:
        raise ValueError(
            f"engine_mode must be one of {_ENGINE_MODE_CHOICES}, got {engine_mode!r}"
        )

    # 모드 → 엔진 이름 매핑
    _mode_to_engines = {
        "nlf-vs-mediapipe": ("nlf", "mediapipe"),
        "nlf-vs-mediapipe-lifter": ("nlf", "mediapipe-lifter"),
        "mediapipe-vs-mediapipe-lifter": ("mediapipe", "mediapipe-lifter"),
    }
    engine_a_name, engine_b_name = _mode_to_engines[engine_mode]
    log.info(
        "compare_engines mode=%s engine_a=%s engine_b=%s motions=%s",
        engine_mode, engine_a_name, engine_b_name, motion_ids,
    )

    results: dict = {}

    for motion_id in motion_ids:
        log.info("--- compare_engines: motion_id=%s ---", motion_id)
        s3_key = f"{_REFERENCE_VIDEO_PREFIX}/{motion_id}.mp4"

        _empty = EngineResult(
            overall_score=float("nan"),
            dimension_scores={},
            top3_failures=[],
            avg_keypoint_confidence=float("nan"),
            ms_per_frame=float("nan"),
        )

        try:
            a_result = run_engine(engine_a_name, s3_key, bucket)
        except Exception:
            log.exception("engine_a=%s 실패 motion_id=%s", engine_a_name, motion_id)
            a_result = _empty

        try:
            b_result = run_engine(engine_b_name, s3_key, bucket)
        except Exception:
            log.exception("engine_b=%s 실패 motion_id=%s", engine_b_name, motion_id)
            b_result = _empty

        # D-14: 점수 갭
        score_gap = abs(a_result.overall_score - b_result.overall_score)
        within_tolerance = (
            score_gap <= SCORE_GAP_TOLERANCE_PT
            and not np.isnan(score_gap)
        )

        # D-15 ①: 위양성 없음 — engine_b (MP 혹은 MP+lifter)가 ≥70점
        b_ge_70 = (
            not np.isnan(b_result.overall_score)
            and b_result.overall_score >= MEDIAPIPE_MIN_SCORE_FOR_EXPERT
        )

        # D-15 ②: Top-3 실패 원인 ≥2/3 겹침
        overlap_count = len(
            set(a_result.top3_failures) & set(b_result.top3_failures)
        )
        top3_overlap = overlap_count >= 2

        # D-15 ③: confidence 임계값 (engine_b 기준)
        avg_conf_ok = (
            not np.isnan(b_result.avg_keypoint_confidence)
            and b_result.avg_keypoint_confidence >= AVG_CONFIDENCE_THRESHOLD
        )

        motion_data: dict = {
            "engine_a": {
                "name": engine_a_name,
                "overall_score": _safe_float(a_result.overall_score),
                "dimension_scores": a_result.dimension_scores,
                "top3_failures": a_result.top3_failures,
                "avg_keypoint_confidence": _safe_float(a_result.avg_keypoint_confidence),
                "ms_per_frame": _safe_float(a_result.ms_per_frame),
            },
            "engine_b": {
                "name": engine_b_name,
                "overall_score": _safe_float(b_result.overall_score),
                "dimension_scores": b_result.dimension_scores,
                "top3_failures": b_result.top3_failures,
                "avg_keypoint_confidence": _safe_float(b_result.avg_keypoint_confidence),
                "ms_per_frame": _safe_float(b_result.ms_per_frame),
            },
            "gates": {
                "score_gap": _safe_float(score_gap),
                "within_tolerance_5pt": within_tolerance,       # D-14
                "mediapipe_score_ge_70": b_ge_70,               # D-15 ① (engine_b 기준)
                "top3_overlap_2_of_3": top3_overlap,            # D-15 ②
                "avg_confidence_ok": avg_conf_ok,               # D-15 ③
                "mediapipe_ms_per_frame": _safe_float(          # D-15 ④
                    b_result.ms_per_frame
                ),
            },
        }

        # backward compat: nlf-vs-mediapipe 모드에서 기존 'nlf'/'mediapipe' 키 제공
        if engine_mode == "nlf-vs-mediapipe":
            motion_data["nlf"] = motion_data["engine_a"]
            motion_data["mediapipe"] = motion_data["engine_b"]

        results[motion_id] = motion_data

    # 전체 summary
    all_within_tolerance = all(
        r["gates"]["within_tolerance_5pt"] for r in results.values()
    )
    all_mediapipe_ge_70 = all(
        r["gates"]["mediapipe_score_ge_70"] for r in results.values()
    )
    all_top3_overlap_ok = all(
        r["gates"]["top3_overlap_2_of_3"] for r in results.values()
    )
    all_avg_confidence_ok = all(
        r["gates"]["avg_confidence_ok"] for r in results.values()
    )

    # D-08/D-16/H-1: 4개 게이트 모두 PASS여야 Wave 3 진행 가능
    phase1_ready_to_swap = (
        all_within_tolerance
        and all_mediapipe_ge_70
        and all_top3_overlap_ok
        and all_avg_confidence_ok
    )

    return {
        "engine_mode": engine_mode,
        "criteria": {
            "score_gap_tolerance_pt": SCORE_GAP_TOLERANCE_PT,
            "mediapipe_min_score_for_expert": MEDIAPIPE_MIN_SCORE_FOR_EXPERT,
            "avg_confidence_threshold": AVG_CONFIDENCE_THRESHOLD,
            "top3_overlap_min": 2,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "motions": results,
        "summary": {
            "all_within_tolerance": all_within_tolerance,
            "all_mediapipe_ge_70": all_mediapipe_ge_70,
            "all_top3_overlap_ok": all_top3_overlap_ok,
            "all_avg_confidence_ok": all_avg_confidence_ok,
            "phase1_ready_to_swap": phase1_ready_to_swap,
        },
    }


def _safe_float(v: float) -> float | None:
    """NaN/Inf는 JSON-serializable None으로 변환."""
    if v is None:
        return None
    try:
        if np.isnan(v) or np.isinf(v):
            return None
    except (TypeError, ValueError):
        return None
    return float(v)


# ── 보고서 생성 ───────────────────────────────────────────────────────────


def generate_markdown_report(payload: dict) -> str:
    """compare_engines 결과 payload → Markdown 보고서 문자열.

    포맷 (D-13~D-16 + H-1 박제):
      헤더 + 생성시각 + 엔진 모드 + 검증 기준 박스
      → motion별 표 (engine_a / engine_b 점수 / gap / top3 / avg_conf / ms / 게이트)
      → 요약 표 (4개 게이트 PASS/FAIL)
      → 최종 결정 박스 (phase1_ready_to_swap)

    Plan 01-08 T-4: engine_mode 에 따라 헤더 + 열 이름 변경.
    backward compat: nlf-vs-mediapipe 모드에서 'MediaPipe vs NLF' 제목 유지.
    """
    lines: list[str] = []

    engine_mode = payload.get("engine_mode", "nlf-vs-mediapipe")

    # 엔진 이름 레이블 (헤더용)
    _mode_labels = {
        "nlf-vs-mediapipe": ("NLF", "MediaPipe"),
        "nlf-vs-mediapipe-lifter": ("NLF", "MP+MotionBERT"),
        "mediapipe-vs-mediapipe-lifter": ("MediaPipe", "MP+MotionBERT"),
    }
    label_a, label_b = _mode_labels.get(engine_mode, ("Engine A", "Engine B"))

    lines.append(
        f"# Phase 1 회귀 검증 보고서 — {label_b} vs {label_a} "
        f"(Wave 2, atomic swap 직전 게이트)"
    )
    lines.append("")
    lines.append(f"엔진 모드: `{engine_mode}`")
    lines.append(f"생성: {payload.get('generated_at', 'N/A')}")
    lines.append("")

    criteria = payload.get("criteria", {})
    lines.append("## 검증 기준 (D-14, D-15 박제)")
    lines.append("")
    lines.append(f"- 점수 갭 허용: ±{criteria.get('score_gap_tolerance_pt', 5.0):.0f}점 이내 (D-14)")
    lines.append(
        f"- 정은지 영상 최소 점수 ({label_b}): "
        f"{criteria.get('mediapipe_min_score_for_expert', 70.0):.0f}점 (D-15 ① — SCORE-04)"
    )
    lines.append(
        f"- 평균 confidence 임계값: {criteria.get('avg_confidence_threshold', 0.5):.2f}"
        " (D-15 ③ — A9 belle 확정 필요)"
    )
    lines.append(f"- Top-3 겹침 최소: {criteria.get('top3_overlap_min', 2)}/3 (D-15 ②)")
    lines.append("")

    motions = payload.get("motions", {})

    lines.append("## motion별 결과")
    lines.append("")
    lines.append(
        f"| motion_id | {label_b} 점수 | {label_a} 점수 | 갭 | within_tolerance | ge_70 "
        f"| top3_overlap | avg_conf | ms/frame | 판정 |"
    )
    lines.append(
        "|-----------|---------|---------|-----|-----------------|------|"
        "------------|----------|----------|------|"
    )

    for motion_id, data in motions.items():
        b = data.get("engine_b", data.get("mediapipe", {}))
        a = data.get("engine_a", data.get("nlf", {}))
        gates = data.get("gates", {})

        b_score = _fmt_score(b.get("overall_score"))
        a_score = _fmt_score(a.get("overall_score"))
        gap = _fmt_score(gates.get("score_gap"))
        within = _gate_str(gates.get("within_tolerance_5pt"))
        ge70 = _gate_str(gates.get("mediapipe_score_ge_70"))
        top3 = _gate_str(gates.get("top3_overlap_2_of_3"))
        avg_conf = _fmt_score(b.get("avg_keypoint_confidence"))
        ms_fr = _fmt_score(gates.get("mediapipe_ms_per_frame"))

        # 모든 게이트 PASS면 PASS
        all_gates = (
            gates.get("within_tolerance_5pt", False)
            and gates.get("mediapipe_score_ge_70", False)
            and gates.get("top3_overlap_2_of_3", False)
            and gates.get("avg_confidence_ok", False)
        )
        verdict = "PASS" if all_gates else "FAIL"

        lines.append(
            f"| {motion_id} | {b_score} | {a_score} | {gap} "
            f"| {within} | {ge70} | {top3} | {avg_conf} | {ms_fr} | {verdict} |"
        )

    lines.append("")

    summary = payload.get("summary", {})
    lines.append("## 요약 게이트")
    lines.append("")
    lines.append("| 게이트 | 결과 | 기준 |")
    lines.append("|-------|------|------|")
    lines.append(
        f"| all_within_tolerance (D-14) | {_gate_str(summary.get('all_within_tolerance'))} "
        f"| ±{criteria.get('score_gap_tolerance_pt', 5.0):.0f}점 이내 |"
    )
    lines.append(
        f"| all_mediapipe_ge_70 (D-15 ①) | {_gate_str(summary.get('all_mediapipe_ge_70'))} "
        f"| {label_b} 영상 ≥{criteria.get('mediapipe_min_score_for_expert', 70.0):.0f}점 |"
    )
    lines.append(
        f"| all_top3_overlap_ok (D-15 ②) | {_gate_str(summary.get('all_top3_overlap_ok'))} "
        f"| Top-3 원인 ≥2/3 겹침 |"
    )
    lines.append(
        f"| all_avg_confidence_ok (D-15 ③) | {_gate_str(summary.get('all_avg_confidence_ok'))} "
        f"| avg_confidence ≥{criteria.get('avg_confidence_threshold', 0.5):.2f} |"
    )
    lines.append("")

    ready = summary.get("phase1_ready_to_swap", False)
    lines.append("## 최종 결정 (D-08/D-16/H-1 박제)")
    lines.append("")
    if ready:
        lines.append(
            "**Wave 3 진행 가능** — 모든 게이트 PASS."
        )
        lines.append(
            "Plan 04 NLF R&D 격리 + Plan 05 atomic swap을 belle 승인 후 진행."
        )
    else:
        lines.append(
            "**D-16에 따라 Wave 3 보류** — 게이트 FAIL."
        )
        lines.append(
            "Hough 파라미터 / keypoint 매핑 / confidence 튜닝 후 본 plan 재실행."
        )
        lines.append("Wave 3 (Plan 04 + 05) 시작 금지 (H-1 박제).")

    lines.append("")
    lines.append(
        f"**phase1_ready_to_swap: {'true' if ready else 'false'}**"
    )

    return "\n".join(lines)


def _fmt_score(v: float | None) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.1f}"
    except (TypeError, ValueError):
        return "N/A"


def _gate_str(v: bool | None) -> str:
    if v is None:
        return "N/A"
    return "PASS" if v else "FAIL"


# ── CLI 진입점 ────────────────────────────────────────────────────────────


def main() -> None:
    """CLI 진입점.

    사용법 (L-2 박제 — /workspace/SunityMotion):
      cd /workspace/SunityMotion

      # 기존 호환 (nlf vs mediapipe):
      python3 -m backend.research.evaluations.compare_engines \\
        --motions ref-ballerina-spin ref-front-hook-spin ref-plank-spin \\
                  ref-invert-butterfly-combo ref-gemini-to-ayesha-combo \\
        --out backend/research/evaluations/reports/compare_20260601.json

      # Plan 01-08 Wave 2 게이트 재판정 (nlf vs MP+MotionBERT):
      python3 -m backend.research.evaluations.compare_engines \\
        --engine nlf-vs-mediapipe-lifter \\
        --motions ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin \\
        --out backend/research/evaluations/reports/compare_lifter_20260601.json

      # lifter 효과 단독 비교 (mediapipe vs mediapipe+lifter):
      python3 -m backend.research.evaluations.compare_engines \\
        --engine mediapipe-vs-mediapipe-lifter \\
        --motions ref-foxtop-split
    """
    parser = argparse.ArgumentParser(
        description=(
            "엔진 회귀 검증 (D-13~D-16, H-1 박제). "
            "실행 경로: /workspace/SunityMotion (L-2)."
        )
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=list(DEFAULT_MOTIONS),
        help="비교할 motion_id 목록 (기본: D-13 정은지 5영상)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON 보고서 출력 경로 (기본: reports/compare_<timestamp>.json)",
    )
    parser.add_argument(
        "--bucket",
        default="sunity-motion-pilot-videos",
        help="S3 버킷 이름",
    )
    parser.add_argument(
        "--engine",
        choices=list(_ENGINE_MODE_CHOICES),
        default="nlf-vs-mediapipe",
        help=(
            "비교 엔진 모드. "
            "nlf-vs-mediapipe (기본, 기존 호환) | "
            "nlf-vs-mediapipe-lifter (Wave 3 판정용) | "
            "mediapipe-vs-mediapipe-lifter (lifter 효과 단독)"
        ),
    )

    args = parser.parse_args()

    # 출력 경로 결정
    if args.out is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        engine_tag = args.engine.replace("-vs-", "_vs_")
        out_json = Path(__file__).parent / "reports" / f"compare_{engine_tag}_{ts}.json"
    else:
        out_json = args.out
    out_md = out_json.with_suffix(".md")
    out_json.parent.mkdir(parents=True, exist_ok=True)

    log.info(
        "compare_engines start engine=%s motions=%s bucket=%s",
        args.engine, args.motions, args.bucket,
    )

    payload = compare_engines(
        motion_ids=args.motions,
        bucket=args.bucket,
        engine_mode=args.engine,
    )

    # JSON 출력
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info("JSON report: %s", out_json)

    # Markdown 출력
    md = generate_markdown_report(payload)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    log.info("Markdown report: %s", out_md)

    # 결과 출력
    summary = payload["summary"]
    print(f"\n보고서 위치: {out_json}")
    print(f"Markdown: {out_md}")
    print(f"엔진 모드: {args.engine}")
    print("\n=== 요약 ===")
    print(f"  all_within_tolerance (D-14):   {'PASS' if summary['all_within_tolerance'] else 'FAIL'}")
    print(f"  all_mediapipe_ge_70  (D-15 ①): {'PASS' if summary['all_mediapipe_ge_70'] else 'FAIL'}")
    print(f"  all_top3_overlap_ok  (D-15 ②): {'PASS' if summary['all_top3_overlap_ok'] else 'FAIL'}")
    print(f"  all_avg_confidence_ok (D-15 ③): {'PASS' if summary['all_avg_confidence_ok'] else 'FAIL'}")
    print(f"\nphase1_ready_to_swap: {'true' if summary['phase1_ready_to_swap'] else 'false'}")

    if not summary["phase1_ready_to_swap"]:
        print("\n[D-16] Wave 3 보류 — 게이트 FAIL. 튜닝 후 재실행 필요.")
    else:
        print("\n[D-08] Wave 3 진행 가능 — belle 승인 후 Plan 04 + 05 시작.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    main()
