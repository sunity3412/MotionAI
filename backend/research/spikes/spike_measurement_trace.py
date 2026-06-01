"""측정 신뢰도 frame-by-frame trace spike (Plan 01-16).

Plan 01-13 verdict `measurement_unreliable_blocked` (2026-06-01) 후속 path A —
ref-invert hold frame 88 단일 frame 측정 결과 = 정은지 (폴스포츠 세계챔피언) invert
split peak hold 자세에서 right_shoulder 18.2도 / left_hip 54.9도 / right_knee 73도
같은 인체학적 비정상 + 5/5 minimum fail. 동일 영상 Plan 08 (MP+MB) frame-mean overall
92 / Plan 11 (RTMPose+MB) frame-mean overall 70 / Plan 13 (RTMPose+MB) hold frame 88
5/5 fail = 4-5배 cross-engine inconsistency. 각도 컨벤션 (compute_joint_angles inner
angle 0-180도, 180도 = 완전 신전) IPSF target 일치 확인됨 — 컨벤션 미스매치 아님.
측정값 자체가 root cause.

본 spike 의 4 가설 trace path (Plan 13 SUMMARY 박제):

| # | 가설                                              | trace path                                         |
|---|---------------------------------------------------|----------------------------------------------------|
| (a) | Gemini frame_idx=88 정확도 — hold 정점 아닌 transition | hold_window (88±5) 평균 vs frame 88 단일 비교       |
| (b) | RTMPose+MB lift 단일 frame 좌우 noise 폭주          | RTMPose+MB frame 별 |L-R| 비대칭 trace, 평균 baseline |
| (c) | lifter occlusion 자세 좌우 keypoint 헷갈림           | RTMPose+MB vs MP+MB 좌우 매핑 swap detection       |
| (d) | RTMPose+MB lift 자체가 invert family 부적합          | RTMPose+MB vs MP+MB frame-by-frame 각도 disagreement |

단일 카메라 단독 박제 — memory `single-camera-first-multi-view-last.md` (2026-06-01)
영구 자동 제외. 본 spike / 권고 / 분기 어디서도 추가 view 옵션 0건. belle 명시
지시 시에만 재진입.

NLF 호출 0 — Plan 12 (c) verdict 후 영구 폐기 (memory `license-blocklist-pose.md` +
Plan 13 박제). 본 spike 의 측정 비교군 = RTMPose+MB + MediaPipe+MB 두 path 만.

라이선스:
  MediaPipe                : Apache 2.0
  MotionBERT               : MIT
  RTMPose / mmpose / mmcv  : Apache 2.0
  본 spike                 : 운영 코드베이스 라이선스와 동일

운영 코드 / Plan 13 모듈 / Plan 15 데이터 / 기존 spike 8개 모두 무수정 (PLAN 16
must_haves 박제). 본 spike 는 함수 import + 호출만 (spike_rtmpose / mediapipe_to_h36m17 /
spike_motionbert / 공유 features / temporal / skeleton). Gemini SDK 호출 0 (frame_idx=88
박제 상수만 사용).

8 angle joints (skeleton.JOINT_KEYS = left/right × elbow/shoulder/hip/knee) 만 trace —
derive joint (hip center/spine/thorax/neck_nose/head) 미사용. Plan 12 (d) verdict
(RTMPose H36M ordering vs NLF COCO ordering 17/17 다름) 회피 유지.

실행 — report-only mode (로컬 OK, mmpose/torch/mediapipe 미설치 환경):
  python3 -m backend.research.spikes.spike_measurement_trace \\
    --mode report-only --motion ref-invert

실행 — live mode (belle Pod 전용, ref-invert 단독, ~5분):
  python3 -m backend.research.spikes.spike_measurement_trace \\
    --mode live --motion ref-invert --frame-index 88 --hold-window 5 \\
    --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \\
    --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \\
    --motionbert-root /workspace/MotionBERT \\
    --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# skeleton 만 모듈-load 시점 import — features / temporal 은 함수 본문에서 import
# (numpy 만 필요, heavy deps 0). spike_rtmpose / mediapipe_to_h36m17 /
# spike_motionbert 는 live helper 안에서 lazy import (모듈-load 시점 mmpose / torch /
# mediapipe import 0 유지).
from sunity_shared.analysis.skeleton import JOINT_KEYS


# ── 4 가설 verdict 임계 (모듈 상수, rationale) ──────────────────────────────────

# (a) Gemini frame_idx 정확도 — frame 88 단일과 hold_window (88±5) 11 frame 평균
# 의 8 joint 평균 절대 차이. >=30도 면 단일 frame sampling 이 직접 원인.
HYPOTHESIS_A_FRAME_VS_WINDOW_STRONG_DEG = 30.0
HYPOTHESIS_A_WEAK_DEG = 10.0

# (b) RTMPose+MB 단일 lift 좌우 noise — 영상 전체 4 pair |L - R| 평균. >=40도 면
# Plan 13 frame 88 의 left vs right delta 60-70도 와 직접 일치.
HYPOTHESIS_B_LR_ASYMMETRY_STRONG_DEG = 40.0
HYPOTHESIS_B_WEAK_DEG = 15.0

# (c) lifter occlusion 자세 좌우 keypoint 헷갈림 — RTMPose+MB 와 MP+MB 두 path
# 에서 좌/우 joint 의 부호 (L > R vs L < R) 가 반대인 frame 비율. >=0.30 (30%)
# 면 occlusion 자세에서 좌우 매핑 swap 빈발.
HYPOTHESIS_C_LR_SWAP_FRAME_RATIO_STRONG = 0.30
HYPOTHESIS_C_WEAK_RATIO = 0.10

# (d) RTMPose+MB vs MP+MB cross-engine — frame 별 8 joint 평균 disagreement.
# >=30도 면 두 lift 가 invert family 에서 불일치 (Plan 12 (e) 두 엔진 3D 분포
# strong distance 220+ 와 직접 연결).
HYPOTHESIS_D_CROSS_ENGINE_DISAGREEMENT_STRONG_DEG = 30.0
HYPOTHESIS_D_WEAK_DEG = 10.0

# Plan 13 박제 입력 — Gemini key moment frame_idx (ref-invert hold).
PLAN_13_FRAME_INDEX = 88
# hold_window = frame ±5 (11 frame). dimensions.py 의 hold_window 동등.
PLAN_13_HOLD_WINDOW = 5

# Cross-engine inconsistency baseline (Plan 08 / Plan 11 frame-mean overall).
PLAN_08_MP_MB_REF_INVERT_OVERALL = 92.0
PLAN_11_RTMPOSE_MB_REF_INVERT_OVERALL = 70.0

# 기본 motion — Plan 15 1차 박제된 유일 motion (ref-invert 5 hold entries).
DEFAULT_MOTION = "ref-invert"

# Engine tag string — JSON top-level engines dict 키와 일관.
ENGINE_RTMPOSE_MB = "rtmpose_mb"
ENGINE_MEDIAPIPE_MB = "mediapipe_mb"


# ── 4 LR pair tuple (skeleton.JOINT_KEYS 8 joint 와 정합) ─────────────────────

# 8 angle joint 를 좌우 4 쌍으로 묶는다 — Plan 16 must_haves "8 angle joints 만"
# 박제. 인덱스는 skeleton.JOINT_KEYS 순서 기준 — 모듈 로드 시 정합 검증.
LR_PAIRS: tuple[tuple[str, str], ...] = (
    ("left_elbow", "right_elbow"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
)


def _assert_lr_pair_integrity() -> None:
    """LR_PAIRS 가 skeleton.JOINT_KEYS 8 joint 와 정합인지 module-load 시 검증.

    정합이 깨지면 본 spike 의 좌우 비대칭 / cross-engine swap 결과가 의미를
    잃으므로 fail-loud. Plan 12 (d) keypoint mapping 회피와 같은 패턴.
    """
    flat = tuple(j for pair in LR_PAIRS for j in pair)
    if set(flat) != set(JOINT_KEYS):
        raise RuntimeError(
            "LR_PAIRS 와 skeleton.JOINT_KEYS 정합 깨짐 — "
            f"LR_PAIRS flat={flat}, JOINT_KEYS={JOINT_KEYS}"
        )
    if len(flat) != len(JOINT_KEYS):
        raise RuntimeError(
            "LR_PAIRS 가 8 joint 를 정확히 4 쌍으로 덮지 않음 — "
            f"len={len(flat)} vs JOINT_KEYS={len(JOINT_KEYS)}"
        )


_assert_lr_pair_integrity()


# ── frame-by-frame trace 함수 (numpy-only, mmpose/torch import 0) ─────────────


def _assert_tj(angles_tj: np.ndarray) -> np.ndarray:
    """(T, J=8) 형상 검증 — 8 angle joint 한정 박제 (Plan 12 (d) 회피)."""
    arr = np.asarray(angles_tj, dtype=float)
    if arr.ndim != 2:
        raise ValueError(
            f"angles_tj 형상은 (T, J) 2차원이어야 합니다. 받은 형상: {arr.shape}"
        )
    if arr.shape[1] != len(JOINT_KEYS):
        raise ValueError(
            f"angles_tj 의 J = {arr.shape[1]} 이 skeleton.JOINT_KEYS 길이 "
            f"{len(JOINT_KEYS)} 과 다릅니다. 8 angle joint 한정 박제 (Plan 16 must_haves)."
        )
    return arr


def trace_angles_per_frame(
    angles_tj: np.ndarray, frame_index: int, hold_window: int
) -> dict[str, Any]:
    """frame_index 단일 vs frame_index±hold_window 평균 비교 — 가설 (a) trace.

    8 joint 의 frame_index 단일 측정과 hold_window 평균 측정의 절대 차이 평균이
    가설 (a) 임계 (HYPOTHESIS_A_FRAME_VS_WINDOW_STRONG_DEG) 와 비교된다. NaN-safe.

    Args:
        angles_tj: (T, J=8) 각도 행렬 (도). features.compute_joint_angles 출력 형식.
        frame_index: 가설 (a) hold 시점 frame.
        hold_window: ±N frame 평균 (dimensions.py hold_window 동등).

    Returns:
        dict with keys:
          frame_single, frame_window_mean, frame_window_min, frame_window_max
            (각각 joint_key → 도, 8 키),
          window_indices (list[int]),
          frame_vs_window_disagreement_per_joint (joint_key → abs_diff 도),
          mean_disagreement_deg (8 joint 평균, NaN-safe).
    """
    arr = _assert_tj(angles_tj)
    T = arr.shape[0]
    if not (0 <= frame_index < T):
        raise ValueError(
            f"frame_index {frame_index} 가 (T, J) T={T} 범위를 벗어남."
        )
    if hold_window < 0:
        raise ValueError(f"hold_window 는 0 이상이어야 합니다. 받은 값: {hold_window}")

    lo = max(0, frame_index - hold_window)
    hi = min(T, frame_index + hold_window + 1)
    window_indices = list(range(lo, hi))
    window = arr[lo:hi, :]  # (W, J)

    single_row = arr[frame_index, :]  # (J,)
    with np.errstate(invalid="ignore", all="ignore"):
        window_mean = np.nanmean(window, axis=0)
        window_min = np.nanmin(window, axis=0)
        window_max = np.nanmax(window, axis=0)
        diff = np.abs(single_row - window_mean)
        mean_disagreement = float(np.nanmean(diff)) if diff.size > 0 else float("nan")

    def _row_to_dict(row: np.ndarray) -> dict[str, Any]:
        return {
            k: (None if np.isnan(row[j]) else float(row[j]))
            for j, k in enumerate(JOINT_KEYS)
        }

    return {
        "frame_single": _row_to_dict(single_row),
        "frame_window_mean": _row_to_dict(window_mean),
        "frame_window_min": _row_to_dict(window_min),
        "frame_window_max": _row_to_dict(window_max),
        "window_indices": window_indices,
        "frame_vs_window_disagreement_per_joint": _row_to_dict(diff),
        "mean_disagreement_deg": (
            None if np.isnan(mean_disagreement) else float(mean_disagreement)
        ),
    }


def compute_lr_asymmetry(angles_tj: np.ndarray) -> dict[str, Any]:
    """4 LR pair frame-by-frame |L - R| — 가설 (b) trace.

    skeleton.JOINT_KEYS 8 joint 를 LR_PAIRS 의 4 쌍 (elbow / shoulder / hip /
    knee) 으로 묶어 영상 전체 frame 별 |L - R| 산출. >= HYPOTHESIS_B_LR_ASYMMETRY_
    STRONG_DEG 면 단일 lift path 좌우 noise 폭주 (Plan 13 frame 88 left vs right
    delta 60-70도 와 직접 일치).

    Args:
        angles_tj: (T, J=8) 각도 행렬 (도).

    Returns:
        dict with keys:
          per_frame: (T, 4) np.ndarray |L - R|, pair 순서 = LR_PAIRS,
          per_pair: pair_name → 영상 전체 평균 |L - R| (NaN-safe),
          overall_mean_abs_lr_deg: 4 pair 평균.
    """
    arr = _assert_tj(angles_tj)
    T = arr.shape[0]

    # joint_key → column index
    key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}

    per_frame = np.full((T, len(LR_PAIRS)), np.nan, dtype=float)
    per_pair: dict[str, float | None] = {}
    pair_means: list[float] = []
    for p, (lk, rk) in enumerate(LR_PAIRS):
        li, ri = key_to_idx[lk], key_to_idx[rk]
        diff = np.abs(arr[:, li] - arr[:, ri])
        per_frame[:, p] = diff
        with np.errstate(invalid="ignore", all="ignore"):
            mean_v = float(np.nanmean(diff)) if diff.size > 0 else float("nan")
        pair_name = f"{lk}_vs_{rk}"
        per_pair[pair_name] = None if np.isnan(mean_v) else mean_v
        if not np.isnan(mean_v):
            pair_means.append(mean_v)

    overall = float(np.mean(pair_means)) if pair_means else float("nan")

    return {
        "per_frame": per_frame,
        "per_pair": per_pair,
        "overall_mean_abs_lr_deg": None if np.isnan(overall) else overall,
    }


def compute_hold_window_lr(
    angles_tj: np.ndarray, frame_index: int, hold_window: int
) -> dict[str, Any]:
    """frame_index 단일 |L - R| vs hold_window 평균 |L - R| — 가설 (a) + (b) 결합.

    Args:
        angles_tj: (T, J=8) 각도 행렬 (도).
        frame_index: hold 시점 frame.
        hold_window: ±N frame 평균.

    Returns:
        dict with keys:
          frame_single_lr: pair_name → 도 (단일 frame |L - R|),
          frame_window_mean_lr: pair_name → 도 (window 평균 |L - R|).
    """
    arr = _assert_tj(angles_tj)
    T = arr.shape[0]
    if not (0 <= frame_index < T):
        raise ValueError(
            f"frame_index {frame_index} 가 (T, J) T={T} 범위를 벗어남."
        )
    if hold_window < 0:
        raise ValueError(f"hold_window 는 0 이상이어야 합니다. 받은 값: {hold_window}")

    key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
    lo = max(0, frame_index - hold_window)
    hi = min(T, frame_index + hold_window + 1)

    frame_single_lr: dict[str, float | None] = {}
    frame_window_mean_lr: dict[str, float | None] = {}
    for lk, rk in LR_PAIRS:
        li, ri = key_to_idx[lk], key_to_idx[rk]
        single_diff = float(abs(arr[frame_index, li] - arr[frame_index, ri]))
        with np.errstate(invalid="ignore", all="ignore"):
            window_diff = np.abs(arr[lo:hi, li] - arr[lo:hi, ri])
            window_mean = (
                float(np.nanmean(window_diff)) if window_diff.size > 0 else float("nan")
            )
        pair_name = f"{lk}_vs_{rk}"
        frame_single_lr[pair_name] = None if np.isnan(single_diff) else single_diff
        frame_window_mean_lr[pair_name] = (
            None if np.isnan(window_mean) else window_mean
        )

    return {
        "frame_single_lr": frame_single_lr,
        "frame_window_mean_lr": frame_window_mean_lr,
    }


# ── cross-engine + swap detection + verdict (T-3, numpy-only) ────────────────


def compute_cross_engine_disagreement(
    rtmpose_angles: np.ndarray, mediapipe_angles: np.ndarray
) -> dict[str, Any]:
    """RTMPose+MB vs MP+MB 의 frame-by-frame 평균 disagreement — 가설 (d).

    두 (T, J=8) 행렬 frame 별 joint 평균 절대 차이. T 가 다르면 짧은 쪽 truncate.

    Args:
        rtmpose_angles: (T1, J=8) RTMPose+MB 결과.
        mediapipe_angles: (T2, J=8) MP+MB 결과.

    Returns:
        dict with keys:
          frame_count: int (truncated min(T1, T2)),
          per_frame_mean_disagreement: list[float | None] (T,),
          per_joint_mean_disagreement: joint_key → mean_abs_deg (8 키),
          overall_mean_disagreement_deg: float | None (8 joint 평균),
          peak_disagreement_frame_idx: int (-1 if all NaN).
    """
    a = _assert_tj(rtmpose_angles)
    b = _assert_tj(mediapipe_angles)
    min_T = min(a.shape[0], b.shape[0])
    a = a[:min_T]
    b = b[:min_T]

    with np.errstate(invalid="ignore", all="ignore"):
        diff = np.abs(a - b)  # (T, 8)
        per_frame = np.nanmean(diff, axis=1)  # (T,)
        per_joint = np.nanmean(diff, axis=0)  # (8,)

    valid = ~np.isnan(per_frame)
    if not np.any(valid):
        overall = float("nan")
        peak_idx = -1
    else:
        overall = float(np.nanmean(per_frame))
        # NaN masked argmax
        masked = np.where(valid, per_frame, -np.inf)
        peak_idx = int(np.argmax(masked))

    per_frame_list = [
        None if np.isnan(x) else float(x) for x in per_frame.tolist()
    ]
    per_joint_dict = {
        k: (None if np.isnan(per_joint[j]) else float(per_joint[j]))
        for j, k in enumerate(JOINT_KEYS)
    }

    return {
        "frame_count": int(min_T),
        "per_frame_mean_disagreement": per_frame_list,
        "per_joint_mean_disagreement": per_joint_dict,
        "overall_mean_disagreement_deg": None if np.isnan(overall) else overall,
        "peak_disagreement_frame_idx": peak_idx,
    }


def detect_lr_swap(
    rtmpose_angles: np.ndarray,
    mediapipe_angles: np.ndarray,
    lr_pairs: tuple[tuple[str, str], ...] = LR_PAIRS,
) -> dict[str, Any]:
    """좌/우 부호 (L > R vs L < R) 두 lift path 가 반대인 frame 비율 — 가설 (c).

    occlusion 자세 (거꾸로 매달림) 에서 lifter 가 좌/우 keypoint 를 헷갈리면
    한 path 는 L > R, 다른 path 는 L < R 출력. NaN frame 은 판정 제외.

    Args:
        rtmpose_angles: (T1, J=8).
        mediapipe_angles: (T2, J=8).
        lr_pairs: pair tuple list. 기본 LR_PAIRS 4 쌍.

    Returns:
        dict with keys:
          frame_count: int (min(T1, T2)),
          swap_frames_per_pair: pair_name → list[int] (swap frame index),
          swap_frame_ratio: float (0~1) — 4 pair 평균,
          swap_frame_ratio_per_pair: pair_name → float (0~1).
    """
    a = _assert_tj(rtmpose_angles)
    b = _assert_tj(mediapipe_angles)
    min_T = min(a.shape[0], b.shape[0])
    a = a[:min_T]
    b = b[:min_T]

    key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
    swap_frames_per_pair: dict[str, list[int]] = {}
    swap_ratios: dict[str, float] = {}
    ratios_list: list[float] = []

    for lk, rk in lr_pairs:
        li, ri = key_to_idx[lk], key_to_idx[rk]
        # 두 path 의 (L - R) 부호 비교
        delta_a = a[:, li] - a[:, ri]
        delta_b = b[:, li] - b[:, ri]
        # NaN frame 은 판정 제외
        valid = ~(np.isnan(delta_a) | np.isnan(delta_b))
        # swap = 부호 반대 (한 쪽 +, 다른 쪽 -). 0 은 swap 아님 (동일).
        sign_a = np.sign(delta_a)
        sign_b = np.sign(delta_b)
        swap_mask = valid & (sign_a * sign_b < 0)
        swap_indices = np.where(swap_mask)[0].tolist()
        n_valid = int(valid.sum())
        ratio = (len(swap_indices) / n_valid) if n_valid > 0 else 0.0

        pair_name = f"{lk}_vs_{rk}"
        swap_frames_per_pair[pair_name] = swap_indices
        swap_ratios[pair_name] = float(ratio)
        ratios_list.append(float(ratio))

    overall_ratio = float(np.mean(ratios_list)) if ratios_list else 0.0

    return {
        "frame_count": int(min_T),
        "swap_frames_per_pair": swap_frames_per_pair,
        "swap_frame_ratio_per_pair": swap_ratios,
        "swap_frame_ratio": float(overall_ratio),
    }


def verdict_hypothesis(
    measure_value: float | None, strong_threshold: float, weak_threshold: float
) -> str:
    """utility — 단일 측정값과 두 임계로 strong / weak / rejected / inconclusive.

    NaN / None 입력은 inconclusive. strong > weak 전제 (가설 (a)(b)(d) 임계).

    Returns:
        "strong" | "weak" | "rejected" | "inconclusive"
    """
    if measure_value is None:
        return "inconclusive"
    try:
        v = float(measure_value)
    except (TypeError, ValueError):
        return "inconclusive"
    if np.isnan(v):
        return "inconclusive"
    if v >= strong_threshold:
        return "strong"
    if v >= weak_threshold:
        return "weak"
    return "rejected"


def aggregate_verdicts(
    trace_a: dict[str, Any],
    trace_b: dict[str, Any],
    trace_c: dict[str, Any],
    trace_d: dict[str, Any],
) -> dict[str, Any]:
    """4 가설 trace 결과 → verdict 표 + dominant + next_path_recommendation.

    Args:
        trace_a: trace_angles_per_frame 결과 (mean_disagreement_deg key).
        trace_b: compute_lr_asymmetry 결과 (overall_mean_abs_lr_deg key).
        trace_c: detect_lr_swap 결과 (swap_frame_ratio key).
        trace_d: compute_cross_engine_disagreement 결과
                 (overall_mean_disagreement_deg key).

    Returns:
        dict with keys:
          hypotheses: {a: {value, verdict, threshold_strong, threshold_weak},
                       b: {...}, c: {...}, d: {...}},
          dominant: list[str] of hypothesis labels that scored "strong",
          next_path_recommendation: str (6 분기 — 추가 view 옵션 키워드 0건 박제).
    """
    v_a = trace_a.get("mean_disagreement_deg")
    v_b = trace_b.get("overall_mean_abs_lr_deg")
    v_c = trace_c.get("swap_frame_ratio")
    v_d = trace_d.get("overall_mean_disagreement_deg")

    verd_a = verdict_hypothesis(
        v_a, HYPOTHESIS_A_FRAME_VS_WINDOW_STRONG_DEG, HYPOTHESIS_A_WEAK_DEG
    )
    verd_b = verdict_hypothesis(
        v_b, HYPOTHESIS_B_LR_ASYMMETRY_STRONG_DEG, HYPOTHESIS_B_WEAK_DEG
    )
    verd_c = verdict_hypothesis(
        v_c, HYPOTHESIS_C_LR_SWAP_FRAME_RATIO_STRONG, HYPOTHESIS_C_WEAK_RATIO
    )
    verd_d = verdict_hypothesis(
        v_d,
        HYPOTHESIS_D_CROSS_ENGINE_DISAGREEMENT_STRONG_DEG,
        HYPOTHESIS_D_WEAK_DEG,
    )

    hypotheses = {
        "a": {
            "label": "Gemini frame_idx 정확도 (frame 단일 vs hold_window 평균)",
            "value": v_a,
            "verdict": verd_a,
            "threshold_strong": HYPOTHESIS_A_FRAME_VS_WINDOW_STRONG_DEG,
            "threshold_weak": HYPOTHESIS_A_WEAK_DEG,
        },
        "b": {
            "label": "RTMPose+MB 단일 lift 좌우 noise (영상 평균 |L-R|)",
            "value": v_b,
            "verdict": verd_b,
            "threshold_strong": HYPOTHESIS_B_LR_ASYMMETRY_STRONG_DEG,
            "threshold_weak": HYPOTHESIS_B_WEAK_DEG,
        },
        "c": {
            "label": "lifter occlusion 좌우 매핑 swap (두 path 부호 반대 비율)",
            "value": v_c,
            "verdict": verd_c,
            "threshold_strong": HYPOTHESIS_C_LR_SWAP_FRAME_RATIO_STRONG,
            "threshold_weak": HYPOTHESIS_C_WEAK_RATIO,
        },
        "d": {
            "label": "RTMPose+MB vs MP+MB cross-engine 각도 disagreement",
            "value": v_d,
            "verdict": verd_d,
            "threshold_strong": HYPOTHESIS_D_CROSS_ENGINE_DISAGREEMENT_STRONG_DEG,
            "threshold_weak": HYPOTHESIS_D_WEAK_DEG,
        },
    }

    dominant = [k for k, v in hypotheses.items() if v["verdict"] == "strong"]

    # next_path_recommendation 6 분기 — 후속 plan path. 추가 view 옵션 0건 박제
    # (memory `single-camera-first-multi-view-last.md` 인용 키워드만 사용).
    if set(dominant) == {"a"}:
        recommendation = (
            "path D 조기 진입 또는 path B-light (window 평균 채택) — "
            "단일 frame sampling 만이 dominant. Plan 13 moment_dimensions 의 "
            "window=5 평균 채택 또는 Gemini frame 선택 정확도 개선."
        )
    elif "a" in dominant and "b" in dominant:
        # (a)+(b) 우선 (a)+(b) 분기
        recommendation = (
            "path B + path D combined — 단일 frame + 단일 lift 둘 다 noise. "
            "multi-engine averaging + Gemini frame 정확도 동시 개선."
        )
    elif set(dominant) == {"b"}:
        recommendation = (
            "path B (multi-engine averaging) 진입 — RTMPose+MB 단일 lift 좌우 noise. "
            "MP+MB / RTMPose+MB 두 lift 평균 또는 voting."
        )
    elif set(dominant) == {"c"}:
        recommendation = (
            "좌우 매핑 sanity check 추가 + path B 검토 — lifter occlusion swap. "
            "RTMPose+MB lift 의 좌우 sign correction layer 추가, 또는 MP+MB "
            "단독 path 전환 검토."
        )
    elif set(dominant) == {"d"}:
        recommendation = (
            "path B (multi-engine averaging) 진입 강제 — 단일 lift path 자체가 "
            "invert family 부적합. 두 lift 평균 / voting / ensemble 필수 "
            "(Plan 12 (e) verdict 와 일치)."
        )
    elif dominant:
        # 그 외 다중 dominant 조합
        recommendation = (
            f"다중 dominant {sorted(dominant)} — path B + path D combined "
            "권고 (단일 frame + 단일 lift 동시 개선)."
        )
    else:
        # 모두 weak / rejected / inconclusive
        recommendation = (
            "path D 정식 진입 (Phase 5 조기) — Gemini 직접 EXTEND/BENT 분류. "
            "측정 path 자체 신뢰 불가 → Gemini 분류 결과로 측정 우회 (SCORE-01 정식 path 조기)."
        )

    return {
        "hypotheses": hypotheses,
        "dominant": dominant,
        "next_path_recommendation": recommendation,
    }


# ── argparse parser ───────────────────────────────────────────────────────────


def _default_out_path() -> Path:
    """기본 출력 경로 (UTC ISO 8601 timestamp, reports/ 아래)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("backend/research/spikes/reports") / f"spike_measurement_trace_{ts}.json"


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI argparse parser 빌더 (smoke 테스트 재사용 위해 분리).

    Plan 16 T-1-5 CLI surface — 10 args. report-only 모드는 mmpose / torch /
    mediapipe 미설치 환경에서도 e2e 동작 (stub angles fixture). live 모드는
    belle Pod 전용 — ref-invert 단독 ~5분 (RTMPose+MB ~3분 + MP+MB ~2분).
    """
    parser = argparse.ArgumentParser(
        description=(
            "측정 신뢰도 frame-by-frame trace spike (Plan 01-16). "
            "Plan 13 verdict measurement_unreliable_blocked 후속 path A — "
            "ref-invert 단독 + RTMPose+MB / MP+MB 두 lift path + 4 가설 (a/b/c/d) verdict."
        )
    )
    parser.add_argument(
        "--mode",
        choices=["report-only", "live"],
        default="report-only",
        help=(
            "report-only (기본): stub angles fixture e2e — mmpose/torch/mediapipe 미import. "
            "live: belle Pod 전용 — 두 lift path 직렬 실행 ~5분."
        ),
    )
    parser.add_argument(
        "--motion",
        default=DEFAULT_MOTION,
        help=(
            f"motion_id (S3: reference/<motion>.mp4). 기본: {DEFAULT_MOTION} "
            "— Plan 15 1차 박제된 유일 motion (5 hold entries)."
        ),
    )
    parser.add_argument(
        "--frame-index",
        type=int,
        default=PLAN_13_FRAME_INDEX,
        help=(
            f"hold 시점 frame index. 기본: {PLAN_13_FRAME_INDEX} "
            "(Plan 13 Gemini moment 결과 박제 — ref-invert hold)."
        ),
    )
    parser.add_argument(
        "--hold-window",
        type=int,
        default=PLAN_13_HOLD_WINDOW,
        help=(
            f"frame_index 주변 ±N frame 평균 윈도우. 기본: {PLAN_13_HOLD_WINDOW} "
            "(dimensions.py hold_window 동등, 11 frame)."
        ),
    )
    parser.add_argument(
        "--bucket",
        default="sunity-motion-pilot-videos",
        help="S3 버킷 (live mode). 기본: sunity-motion-pilot-videos.",
    )
    parser.add_argument(
        "--rtmpose-config",
        default=None,
        help="RTMPose config (.py) 경로 (live mode 필수).",
    )
    parser.add_argument(
        "--rtmpose-checkpoint",
        default=None,
        help="RTMPose pretrained 가중치 (.pth) 경로 (live mode 필수).",
    )
    parser.add_argument(
        "--motionbert-root",
        default="/workspace/MotionBERT",
        help="MotionBERT 저장소 루트 경로 (live mode).",
    )
    parser.add_argument(
        "--motionbert-weights",
        default=None,
        help=(
            "MotionBERT 가중치 경로 (live mode 필수). None 이면 "
            "{root}/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin"
        ),
    )
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "JSON 결과 저장 경로. None 이면 "
            "backend/research/spikes/reports/spike_measurement_trace_<UTC>.json 자동 생성. "
            ".md sibling 도 같이 생성."
        ),
    )
    return parser


# ── 두 lift path 골격 분기 (helper 함수는 T-2/T-3/T-4 에서 추가) ────────────────


def run_trace(args: argparse.Namespace) -> dict[str, Any]:
    """본 spike 의 진입점 — argparse 결과 받아 두 lift path trace 수행.

    골격 (T-1):
      - report-only mode: stub angles fixture 두 set (RTMPose+MB / MP+MB) 생성 →
        T-2/T-3 helper 호출 → JSON dict 반환.
      - live mode: lazy import spike_rtmpose / mediapipe_to_h36m17 / spike_motionbert →
        두 lift path 직렬 실행 → 동일 helper chain.

    본 함수 본체는 T-4 에서 stub fixture + helper chain 완성. T-1 단계에서는
    골격 + live mode guard 만 박제 (rtmpose-config / rtmpose-checkpoint /
    motionbert-weights 누락 시 ValueError).
    """
    if args.mode == "live":
        # live mode guard — Pod 전용 인자 누락 시 fail-loud (belle 가 빠뜨려도
        # mmpose 가 늦게 폭발하는 대신 진입 단계에서 멈춤).
        missing = []
        if args.rtmpose_config is None:
            missing.append("--rtmpose-config")
        if args.rtmpose_checkpoint is None:
            missing.append("--rtmpose-checkpoint")
        if args.motionbert_weights is None and not args.motionbert_root:
            missing.append("--motionbert-weights")
        if missing:
            raise ValueError(
                f"live mode 필수 인자 누락: {', '.join(missing)}. "
                "belle Pod 절차 README Plan 16 섹션 참조."
            )

    # T-4 가 완성 — T-1 단계에서는 진입 가능성만 박제.
    raise NotImplementedError(
        "run_trace 본체는 T-4 에서 완성됩니다. T-1 = CLI + 모듈 상수 박제."
    )


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """CLI 진입점 — T-4 에서 JSON dump + sibling Markdown 출력 완성."""
    parser = build_arg_parser()
    args = parser.parse_args()
    run_trace(args)  # T-4 가 완성
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
