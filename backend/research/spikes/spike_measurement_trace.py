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


# ── stub angles fixture (report-only mode 전용) ───────────────────────────────


def _build_stub_angles(
    T: int = 20,
    frame_index: int = 10,
    rtmpose_baseline: float = 90.0,
    mediapipe_baseline: float = 90.0,
) -> tuple[np.ndarray, np.ndarray]:
    """report-only mode 용 (T, J=8) stub fixture 두 set.

    두 set 은 baseline 이 다르고 frame_index 에서 RTMPose+MB 만 좌우 비대칭이
    있도록 구성 — 4 가설 임계 분기 검증용 (실측정값 모사).
    """
    rtm = np.full((T, len(JOINT_KEYS)), rtmpose_baseline, dtype=float)
    mp = np.full((T, len(JOINT_KEYS)), mediapipe_baseline, dtype=float)
    # RTMPose+MB frame_index 만 약간 다르게 (가설 (a) 시뮬레이션)
    rtm[frame_index, :] = rtmpose_baseline - 5.0
    return rtm, mp


# ── live mode helper (lazy import — 모듈-load 시점 0 import) ───────────────────


def _live_rtmpose_angles(
    args: argparse.Namespace, resolved_video: str, frames: np.ndarray
) -> np.ndarray:
    """live mode: RTMPose+MB lift path → (T, J=8) angles.

    Plan 11 spike_rtmpose 의 함수 시그너처를 무수정 호출. 실 시그너처 정합 가드 —
    Plan 13 의 _run_rtmpose_2d kwargs 같은 belle Pod 발견 차단 목적.
    """
    from .spike_rtmpose import (  # noqa: PLC0415
        _run_rtmpose_2d,
        _load_motionbert,
        _run_motionbert_inference,
        _h36m17_to_coco17_subset,
    )
    from .rtmpose_to_h36m17 import convert_rtmpose_coco17_to_h36m17  # noqa: PLC0415
    from sunity_shared.analysis.features import (  # noqa: PLC0415
        compute_joint_angles,
        joint_uncertainty,
    )
    from sunity_shared.analysis.temporal import temporal_fill  # noqa: PLC0415

    # RTMPose-l 2D → COCO-17 (T, 17, 3)
    rtmpose_kp, image_size, _avg_score = _run_rtmpose_2d(
        frames,
        args.rtmpose_config,
        args.rtmpose_checkpoint,
        det_model=None,  # single-person mode (Plan 11 default)
    )
    # COCO-17 (pixel + score) → H3.6M 17 (정규화 2D)
    h36m_2d = convert_rtmpose_coco17_to_h36m17(
        rtmpose_kp,
        image_size=image_size,
        score_threshold=0.3,
        use_score_as_conf=False,
    )
    # MotionBERT lift
    weights = args.motionbert_weights or str(
        Path(args.motionbert_root)
        / "checkpoint"
        / "pose3d"
        / "FT_MB_lite_MB_ft_h36m_global_lite"
        / "best_epoch.bin"
    )
    model, device = _load_motionbert(args.motionbert_root, weights)
    h36m_xyz = _run_motionbert_inference(model, device, h36m_2d)
    coco17_array = _h36m17_to_coco17_subset(h36m_xyz)

    angles = compute_joint_angles(coco17_array)
    filled = temporal_fill(angles, uncertainty=joint_uncertainty(coco17_array))
    return filled


def _live_mediapipe_angles(
    args: argparse.Namespace, resolved_video: str, frames: np.ndarray
) -> np.ndarray:
    """live mode: MediaPipe + MB lift path → (T, J=8) angles.

    Plan 08 spike_motionbert path 무수정 호출 — _run_mediapipe_2d (33 keypoint) +
    convert_mp33_to_h36m17 + _load_motionbert + _run_motionbert_inference +
    h36m17_to_coco17_subset (mediapipe_to_h36m17 어댑터).
    """
    from .spike_motionbert import (  # noqa: PLC0415
        _run_mediapipe_2d,
        _load_motionbert,
        _run_motionbert_inference,
    )
    from .mediapipe_to_h36m17 import (  # noqa: PLC0415
        convert_mp33_to_h36m17,
        h36m17_to_coco17_subset,
    )
    from sunity_shared.analysis.features import (  # noqa: PLC0415
        compute_joint_angles,
        joint_uncertainty,
    )
    from sunity_shared.analysis.temporal import temporal_fill  # noqa: PLC0415

    # MediaPipe 33 → (T, 33, 3)
    mp_lm, _avg_conf = _run_mediapipe_2d(frames)
    # MP 33 → H36M 17
    h36m_2d = convert_mp33_to_h36m17(mp_lm, use_visibility_as_conf=False)
    # MotionBERT lift
    weights = args.motionbert_weights or str(
        Path(args.motionbert_root)
        / "checkpoint"
        / "pose3d"
        / "FT_MB_lite_MB_ft_h36m_global_lite"
        / "best_epoch.bin"
    )
    model, device = _load_motionbert(args.motionbert_root, weights)
    h36m_xyz = _run_motionbert_inference(model, device, h36m_2d)
    coco17_array = h36m17_to_coco17_subset(h36m_xyz)

    angles = compute_joint_angles(coco17_array)
    filled = temporal_fill(angles, uncertainty=joint_uncertainty(coco17_array))
    return filled


# ── live mode helper signature integration check (no heavy import) ───────────


def assert_live_helper_signatures() -> dict[str, list[str]]:
    """live helper 가 import 하는 함수 시그너처를 mmpose / torch 없이 점검.

    Plan 13 belle Pod 발견 (joint_uncertainty import / _run_rtmpose_2d kwargs /
    SDK / File API ACTIVE) 같은 시그너처 불일치 차단. 본 함수는 ast 기반 정합 검증 —
    spike_rtmpose / spike_motionbert / mediapipe_to_h36m17 의 함수 시그너처를
    import 없이 점검 (mmpose / torch / mediapipe 미설치 환경 OK).

    Returns:
        dict[module_name → list[function_name]] — 발견된 함수 목록.
        함수 누락 / 인자 변경 시 RuntimeError fail-loud.
    """
    import ast  # noqa: PLC0415

    expected = {
        "spike_rtmpose": [
            "_resolve_video",
            "_extract_frames",
            "_run_rtmpose_2d",
            "_load_motionbert",
            "_run_motionbert_inference",
            "_h36m17_to_coco17_subset",
        ],
        "rtmpose_to_h36m17": ["convert_rtmpose_coco17_to_h36m17"],
        "mediapipe_to_h36m17": [
            "convert_mp33_to_h36m17",
            "h36m17_to_coco17_subset",
        ],
        "spike_motionbert": [
            "_resolve_video",
            "_extract_frames",
            "_run_mediapipe_2d",
            "_load_motionbert",
            "_run_motionbert_inference",
        ],
    }

    spikes_dir = Path(__file__).parent
    found: dict[str, list[str]] = {}

    for module_name, fns in expected.items():
        src_path = spikes_dir / f"{module_name}.py"
        if not src_path.exists():
            raise RuntimeError(
                f"live helper 의 모듈 의존 깨짐: {src_path} 없음. "
                "기존 spike 무수정 박제 확인 필요."
            )
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        module_fns = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]
        missing = [fn for fn in fns if fn not in module_fns]
        if missing:
            raise RuntimeError(
                f"live helper 가 import 하는 함수 누락: {module_name}.{missing}. "
                "Plan 13 식 belle Pod 발견 차단 — 기존 spike 시그너처 정합 검증 실패."
            )
        found[module_name] = sorted(set(module_fns) & set(fns))

    return found


# ── run_trace 진입점 ──────────────────────────────────────────────────────────


def run_trace(args: argparse.Namespace) -> dict[str, Any]:
    """본 spike 의 진입점 — 두 lift path angles → 4 가설 helper chain → JSON dict.

    report-only mode: stub angles fixture 두 set 으로 helper chain end-to-end.
    live mode: belle Pod 전용 — lazy import + 두 lift path 직렬 실행 ~5분
    (RTMPose+MB ~3분 + MP+MB ~2분). 두 set 동일 helper chain 통과.
    """
    # 1) live mode guard — Pod 전용 인자 누락 시 fail-loud
    if args.mode == "live":
        missing = []
        if args.rtmpose_config is None:
            missing.append("--rtmpose-config")
        if args.rtmpose_checkpoint is None:
            missing.append("--rtmpose-checkpoint")
        # motionbert weights: --motionbert-weights 가 None 이면 root 에서 default 경로 사용
        if not args.motionbert_root and args.motionbert_weights is None:
            missing.append("--motionbert-weights")
        if missing:
            raise ValueError(
                f"live mode 필수 인자 누락: {', '.join(missing)}. "
                "belle Pod 절차 README Plan 16 섹션 참조."
            )

    # 2) live helper 시그너처 정합 (mmpose 없이도 점검 — Plan 13 fix 차단)
    sig_check = assert_live_helper_signatures()

    # 3) 두 lift path angles 산출
    if args.mode == "report-only":
        rtmpose_angles, mediapipe_angles = _build_stub_angles(
            T=20, frame_index=min(10, max(0, args.frame_index)),
            rtmpose_baseline=90.0,
            mediapipe_baseline=90.0,
        )
        # report-only 의 frame_index 는 stub T=20 의 안전 범위 (10)
        effective_frame_index = min(10, args.frame_index)
        effective_hold_window = min(5, args.hold_window)
    else:
        # live mode: 두 lift path 직렬 실행 (RTMPose+MB 먼저, MP+MB 다음)
        from .spike_rtmpose import _resolve_video, _extract_frames  # noqa: PLC0415
        import tempfile  # noqa: PLC0415

        effective_frame_index = args.frame_index
        effective_hold_window = args.hold_window

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            resolved_video = _resolve_video(
                None, args.motion, args.bucket, tmp_dir
            )
            frames = _extract_frames(resolved_video)
            rtmpose_angles = _live_rtmpose_angles(args, resolved_video, frames)
            mediapipe_angles = _live_mediapipe_angles(
                args, resolved_video, frames
            )

    # 4) 4 가설 helper chain (mmpose / torch 미import 시에도 동작)
    rtm_trace_a = trace_angles_per_frame(
        rtmpose_angles, effective_frame_index, effective_hold_window
    )
    mp_trace_a = trace_angles_per_frame(
        mediapipe_angles, effective_frame_index, effective_hold_window
    )
    rtm_lr = compute_lr_asymmetry(rtmpose_angles)
    mp_lr = compute_lr_asymmetry(mediapipe_angles)
    rtm_hold_lr = compute_hold_window_lr(
        rtmpose_angles, effective_frame_index, effective_hold_window
    )
    mp_hold_lr = compute_hold_window_lr(
        mediapipe_angles, effective_frame_index, effective_hold_window
    )
    cross = compute_cross_engine_disagreement(rtmpose_angles, mediapipe_angles)
    swap = detect_lr_swap(rtmpose_angles, mediapipe_angles)

    # verdict 4 가설 — (a) = RTMPose+MB frame 단일 vs window 평균 (Plan 13 trace 기준).
    trace_a_for_verdict = rtm_trace_a
    trace_b_for_verdict = rtm_lr
    trace_c_for_verdict = swap
    trace_d_for_verdict = cross

    verdicts = aggregate_verdicts(
        trace_a_for_verdict,
        trace_b_for_verdict,
        trace_c_for_verdict,
        trace_d_for_verdict,
    )

    # 5) JSON 결과 dict — numpy ndarray 는 list 로 직렬화 (json.dump 전 처리)
    def _drop_ndarray(d: dict[str, Any]) -> dict[str, Any]:
        return {
            k: (v.tolist() if isinstance(v, np.ndarray) else v)
            for k, v in d.items()
        }

    plan_13_inputs = {
        "frame_index": PLAN_13_FRAME_INDEX,
        "hold_window": PLAN_13_HOLD_WINDOW,
        "ref_invert_hold_frame_88_5_of_5_fail": {
            "left_shoulder": 88.2,
            "right_shoulder": 18.2,
            "left_hip": 54.9,
            "right_hip": 115.5,
            "right_knee": 73.0,
        },
        "convention": "compute_joint_angles inner angle 0-180도 (180도 = 완전 신전)",
    }

    baseline_inconsistency = {
        "plan_08_mp_mb_ref_invert_frame_mean_overall": PLAN_08_MP_MB_REF_INVERT_OVERALL,
        "plan_11_rtmpose_mb_ref_invert_frame_mean_overall": PLAN_11_RTMPOSE_MB_REF_INVERT_OVERALL,
        "plan_13_rtmpose_mb_frame_88_single_5_of_5_fail": True,
        "cross_engine_ratio": "4-5x",
    }

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "motion": args.motion,
        "frame_index": effective_frame_index,
        "hold_window": effective_hold_window,
        "engines": {
            ENGINE_RTMPOSE_MB: {
                "trace_angles_per_frame": rtm_trace_a,
                "lr_asymmetry": _drop_ndarray(rtm_lr),
                "hold_window_lr": rtm_hold_lr,
            },
            ENGINE_MEDIAPIPE_MB: {
                "trace_angles_per_frame": mp_trace_a,
                "lr_asymmetry": _drop_ndarray(mp_lr),
                "hold_window_lr": mp_hold_lr,
            },
        },
        "cross_engine": {
            "disagreement": cross,
            "lr_swap": swap,
        },
        "verdicts": verdicts,
        "baseline_inconsistency": baseline_inconsistency,
        "plan_13_inputs": plan_13_inputs,
        "signature_check": sig_check,
    }
    return result


# ── Markdown 출력 ─────────────────────────────────────────────────────────────


def _fmt(v: Any) -> str:
    """None / NaN / float 표시 헬퍼."""
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if np.isnan(v):
            return "N/A"
        return f"{v:.2f}"
    return str(v)


def generate_markdown(trace_result: dict[str, Any]) -> str:
    """JSON 결과 → 9 섹션 Markdown sibling 생성.

    섹션: (1) 메타 (2) RTMPose+MB trace (3) MP+MB trace (4) 좌우 비대칭
    (5) cross-engine disagreement (6) 좌우 swap detection (7) 4 가설 verdict
    (8) next_path_recommendation (9) baseline_inconsistency.
    """
    eng = trace_result.get("engines", {})
    rtm = eng.get(ENGINE_RTMPOSE_MB, {})
    mp = eng.get(ENGINE_MEDIAPIPE_MB, {})
    cross = trace_result.get("cross_engine", {})
    verdicts = trace_result.get("verdicts", {})
    baseline = trace_result.get("baseline_inconsistency", {})

    lines: list[str] = []

    # (1) 메타
    lines += [
        "# Spike: Measurement Trace (Plan 01-16)",
        "",
        f"생성: {trace_result.get('generated_at', 'N/A')}",
        f"모드: `{trace_result.get('mode', 'N/A')}`",
        f"모션: `{trace_result.get('motion', 'N/A')}`",
        f"frame_index: {trace_result.get('frame_index', 'N/A')}",
        f"hold_window: ±{trace_result.get('hold_window', 'N/A')}",
        "",
    ]

    # (2) RTMPose+MB trace
    lines += ["## (2) RTMPose+MB trace — frame 단일 vs hold_window 평균", ""]
    rtm_tap = rtm.get("trace_angles_per_frame", {})
    if rtm_tap:
        lines += [
            "| joint | frame_single | window_mean | window_min | window_max | disagreement |",
            "|---|---|---|---|---|---|",
        ]
        single = rtm_tap.get("frame_single", {})
        mean_ = rtm_tap.get("frame_window_mean", {})
        min_ = rtm_tap.get("frame_window_min", {})
        max_ = rtm_tap.get("frame_window_max", {})
        diff = rtm_tap.get("frame_vs_window_disagreement_per_joint", {})
        for k in JOINT_KEYS:
            lines.append(
                f"| {k} | {_fmt(single.get(k))} | {_fmt(mean_.get(k))} | "
                f"{_fmt(min_.get(k))} | {_fmt(max_.get(k))} | {_fmt(diff.get(k))} |"
            )
        lines.append(
            f"\nmean_disagreement_deg: **{_fmt(rtm_tap.get('mean_disagreement_deg'))}**"
        )
    lines.append("")

    # (3) MP+MB trace
    lines += ["## (3) MP+MB trace — frame 단일 vs hold_window 평균", ""]
    mp_tap = mp.get("trace_angles_per_frame", {})
    if mp_tap:
        lines += [
            "| joint | frame_single | window_mean | window_min | window_max | disagreement |",
            "|---|---|---|---|---|---|",
        ]
        single = mp_tap.get("frame_single", {})
        mean_ = mp_tap.get("frame_window_mean", {})
        min_ = mp_tap.get("frame_window_min", {})
        max_ = mp_tap.get("frame_window_max", {})
        diff = mp_tap.get("frame_vs_window_disagreement_per_joint", {})
        for k in JOINT_KEYS:
            lines.append(
                f"| {k} | {_fmt(single.get(k))} | {_fmt(mean_.get(k))} | "
                f"{_fmt(min_.get(k))} | {_fmt(max_.get(k))} | {_fmt(diff.get(k))} |"
            )
        lines.append(
            f"\nmean_disagreement_deg: **{_fmt(mp_tap.get('mean_disagreement_deg'))}**"
        )
    lines.append("")

    # (4) 좌우 비대칭
    lines += ["## (4) 좌우 비대칭 (4 pair, 양 엔진 비교)", ""]
    rtm_lr = rtm.get("lr_asymmetry", {})
    mp_lr = mp.get("lr_asymmetry", {})
    lines += [
        "| pair | RTMPose+MB 영상 평균 | MP+MB 영상 평균 |",
        "|---|---|---|",
    ]
    for lk, rk in LR_PAIRS:
        pair_name = f"{lk}_vs_{rk}"
        lines.append(
            f"| {pair_name} | {_fmt(rtm_lr.get('per_pair', {}).get(pair_name))} "
            f"| {_fmt(mp_lr.get('per_pair', {}).get(pair_name))} |"
        )
    lines += [
        f"\n- RTMPose+MB overall: **{_fmt(rtm_lr.get('overall_mean_abs_lr_deg'))}**",
        f"- MP+MB overall: **{_fmt(mp_lr.get('overall_mean_abs_lr_deg'))}**",
        "",
    ]

    # (5) cross-engine disagreement
    lines += ["## (5) Cross-engine disagreement (RTMPose+MB vs MP+MB)", ""]
    dis = cross.get("disagreement", {})
    lines += [
        f"- frame_count: {_fmt(dis.get('frame_count'))}",
        f"- overall_mean_disagreement_deg: **{_fmt(dis.get('overall_mean_disagreement_deg'))}**",
        f"- peak_disagreement_frame_idx: {_fmt(dis.get('peak_disagreement_frame_idx'))}",
        "",
        "joint별 평균 disagreement:",
        "",
        "| joint | mean_abs_deg |",
        "|---|---|",
    ]
    per_joint = dis.get("per_joint_mean_disagreement", {})
    for k in JOINT_KEYS:
        lines.append(f"| {k} | {_fmt(per_joint.get(k))} |")
    lines.append("")

    # (6) LR swap detection
    lines += ["## (6) 좌우 swap detection (pair 별 부호 반대 비율)", ""]
    swap = cross.get("lr_swap", {})
    lines += [
        f"- frame_count: {_fmt(swap.get('frame_count'))}",
        f"- swap_frame_ratio (4 pair 평균): **{_fmt(swap.get('swap_frame_ratio'))}**",
        "",
        "| pair | swap_ratio |",
        "|---|---|",
    ]
    swap_per = swap.get("swap_frame_ratio_per_pair", {})
    for lk, rk in LR_PAIRS:
        pair_name = f"{lk}_vs_{rk}"
        lines.append(f"| {pair_name} | {_fmt(swap_per.get(pair_name))} |")
    lines.append("")

    # (7) 4 가설 verdict 매트릭스
    lines += ["## (7) 4 가설 verdict 매트릭스", ""]
    lines += [
        "| # | 가설 | 측정값 | strong 임계 | weak 임계 | verdict |",
        "|---|---|---|---|---|---|",
    ]
    hyp = verdicts.get("hypotheses", {})
    for letter in ("a", "b", "c", "d"):
        h = hyp.get(letter, {})
        lines.append(
            f"| ({letter}) | {h.get('label', 'N/A')} | "
            f"{_fmt(h.get('value'))} | {_fmt(h.get('threshold_strong'))} | "
            f"{_fmt(h.get('threshold_weak'))} | **{h.get('verdict', 'N/A')}** |"
        )
    dominant = verdicts.get("dominant", [])
    lines += [
        "",
        f"dominant: **{dominant if dominant else '(없음)'}**",
        "",
    ]

    # (8) next_path_recommendation
    lines += [
        "## (8) next_path_recommendation",
        "",
        verdicts.get("next_path_recommendation", "(미산출)"),
        "",
    ]

    # (9) baseline_inconsistency
    lines += [
        "## (9) Plan 08 / Plan 11 / Plan 13 cross-engine inconsistency baseline",
        "",
        "| measure | Plan 08 (MP+MB) | Plan 11 (RTMPose+MB) | Plan 13 (RTMPose+MB) |",
        "|---|---|---|---|",
        "| sampling | frame-mean | frame-mean | hold frame 88 단일 |",
        f"| overall | {baseline.get('plan_08_mp_mb_ref_invert_frame_mean_overall', 'N/A')} | "
        f"{baseline.get('plan_11_rtmpose_mb_ref_invert_frame_mean_overall', 'N/A')} | "
        f"5/5 minimum fail |",
        f"\ncross-engine ratio: {baseline.get('cross_engine_ratio', 'N/A')}",
        "",
    ]

    return "\n".join(lines) + "\n"


# ── main ──────────────────────────────────────────────────────────────────────


def _serialize_for_json(obj: Any) -> Any:
    """numpy ndarray / NaN safe JSON 직렬화 helper."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    if isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


def main() -> int:
    """CLI 진입점 — argparse + run_trace + JSON dump + sibling Markdown."""
    import json  # noqa: PLC0415

    parser = build_arg_parser()
    args = parser.parse_args()
    result = run_trace(args)

    out_path = Path(args.out) if args.out else _default_out_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_serialize_for_json(result), f, ensure_ascii=False, indent=2)

    md_path = out_path.with_suffix(".md")
    md_path.write_text(generate_markdown(result), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
