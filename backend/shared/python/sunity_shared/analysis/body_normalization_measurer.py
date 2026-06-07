"""measure_body_profile — RTMW 키포인트 list[PoseFrame] → BodyNormalizationProfile.

D-19 / Phase 2 BODY-01 박제. 순수 numpy 함수. scipy 의존 0.

Phase 1 temporal.py MAD 패턴 재사용 (DEFAULT_OUTLIER_K=3.0).

MEDIUM-3 v5 박제 (pose_too_inverted image-y-order 직접):
  v3/v4: dot(torso_up, pole_axis.axis_vector) < 0 → inverted.
  v5: 폐기. image y-down 좌표 직접 비교. mid_shoulder.y vs mid_hip.y.
      어깨가 화면 위쪽 (y 작음) 이면 직립. 아래쪽 (y 큼) 이면 인버트.
      PoleAxis.axis_vector 부호와 독립적 — `_is_inverted_frame` 시그너처에서
      pole_axis 인자 폐기.

MEDIUM-2 v5 박제 (fallback path emits 1.0):
  BodyNormalizationProfile.__post_init__ 가 5 numeric scale 필드 finite +
  strictly positive 강제. fallback 경로 (short clip / all-NaN / measurer 산출
  NaN) 는 5 scale 필드 = 1.0 + confidence = 0.0 emit (validator 통과).

5 warning enum (Phase 2 BODY-01 박제):
  - low_keypoint_confidence: 전체 keypoint 평균 confidence < 0.4.
  - occluded_endpoint: endpoint conf<0.5 가 60% 초과 frame.
  - insufficient_frames: frame 수 < 30.
  - asymmetric_landmark_count: 좌/우 valid frame 차이 > 30%.
  - pose_too_inverted: 인버트 frame > 50% (image y-down).
"""

from __future__ import annotations

import math

import numpy as np

from .body_normalization import BodyNormalizationProfile
from .pose_frame import PoseFrame


# ── 상수 (Phase 2 BODY-01 박제) ────────────────────────────────────────────

# segment 측정 pair (start, end, side). side='left'|'right'|'mid'.
# torso 는 별도 _measure_torso 함수로 처리.
SEGMENT_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("left_shoulder", "left_elbow", "left"),    # upper_arm L
    ("left_elbow", "left_wrist", "left"),       # forearm L
    ("left_hip", "left_knee", "left"),          # thigh L
    ("left_knee", "left_ankle", "left"),        # shank L
    ("right_shoulder", "right_elbow", "right"),  # upper_arm R
    ("right_elbow", "right_wrist", "right"),    # forearm R
    ("right_hip", "right_knee", "right"),       # thigh R
    ("right_knee", "right_ankle", "right"),     # shank R
    ("left_shoulder", "right_shoulder", "mid"),  # shoulder_width
    ("left_hip", "right_hip", "mid"),           # hip_width
)

TORSO_TOP_KPS: tuple[str, str] = ("left_shoulder", "right_shoulder")
TORSO_BOTTOM_KPS: tuple[str, str] = ("left_hip", "right_hip")

WARNING_CODES: frozenset[str] = frozenset({
    "low_keypoint_confidence",
    "occluded_endpoint",
    "insufficient_frames",
    "asymmetric_landmark_count",
    "pose_too_inverted",
})

# 임계값
CONF_GATE_PER_FRAME: float = 0.5  # endpoint conf gate
MIN_VALID_FRAMES: int = 5
MIN_FRAMES_FOR_INSUFFICIENT: int = 30
MAX_BAD_FRAME_RATIO: float = 0.6  # occluded_endpoint trigger
MAD_K: float = 3.0
LOW_CONFIDENCE_GATE: float = 0.4
INVERTED_FRAME_RATIO: float = 0.5
ASYMMETRIC_FRAME_RATIO: float = 0.3


# ── per-frame segment 측정 ────────────────────────────────────────────────

def _measure_segment_per_frame(
    frame: PoseFrame, start_name: str, end_name: str
) -> tuple[float, float]:
    """단일 frame 의 (segment_length, confidence). z 무시 — 2D image 측정.

    미감지 시 (length=nan, conf=0).
    """
    kp = frame.keypoints_3d
    if start_name not in kp or end_name not in kp:
        return float("nan"), 0.0
    s = kp[start_name]
    e = kp[end_name]
    dx = e.x - s.x
    dy = e.y - s.y
    length = math.sqrt(dx * dx + dy * dy)
    conf = float(min(s.confidence, e.confidence))
    return length, conf


def _measure_torso_per_frame(frame: PoseFrame) -> tuple[float, float]:
    """단일 frame torso 길이 (mid_shoulder ↔ mid_hip). conf=4 endpoint min."""
    kp = frame.keypoints_3d
    needed = (
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
    )
    for n in needed:
        if n not in kp:
            return float("nan"), 0.0
    ls, rs, lh, rh = (kp[n] for n in needed)
    mid_shoulder_x = (ls.x + rs.x) / 2
    mid_shoulder_y = (ls.y + rs.y) / 2
    mid_hip_x = (lh.x + rh.x) / 2
    mid_hip_y = (lh.y + rh.y) / 2
    dx = mid_hip_x - mid_shoulder_x
    dy = mid_hip_y - mid_shoulder_y
    length = math.sqrt(dx * dx + dy * dy)
    conf = float(min(ls.confidence, rs.confidence, lh.confidence, rh.confidence))
    return length, conf


# ── robust median (MAD outlier rejection) ─────────────────────────────────

def _robust_median(
    values: np.ndarray, confs: np.ndarray, *, k: float = MAD_K
) -> tuple[float, float]:
    """MAD outlier rejection + median + (kept_ratio × mean_conf).

    valid < MIN_VALID_FRAMES → (nan, 0.0).
    """
    finite_mask = np.isfinite(values)
    finite_vals = values[finite_mask]
    finite_confs = confs[finite_mask]

    if finite_vals.size < MIN_VALID_FRAMES:
        return float("nan"), 0.0

    med = float(np.median(finite_vals))
    mad = float(np.median(np.abs(finite_vals - med)))

    if mad > 0:
        bad = np.abs(finite_vals - med) > k * 1.4826 * mad
        kept_mask = ~bad
    else:
        # MAD collapse — 모두 같은 값. 전부 keep.
        kept_mask = np.ones_like(finite_vals, dtype=bool)

    if not np.any(kept_mask):
        return float("nan"), 0.0

    kept_vals = finite_vals[kept_mask]
    kept_confs = finite_confs[kept_mask]

    median_val = float(np.median(kept_vals))
    kept_ratio = float(kept_mask.sum()) / float(values.size)
    mean_conf = float(np.mean(kept_confs))

    return median_val, kept_ratio * mean_conf


# ── inversion 판정 (MEDIUM-3 v5 — image y-order 직접) ──────────────────────

def _is_inverted_frame(frame: PoseFrame) -> bool | None:
    """단일 frame inversion 판정 (MEDIUM-3 v5 박제).

    MEDIUM-3 v5: image y-down 픽셀 좌표 직접 비교. y-down image 에서
    `mid_shoulder.y < mid_hip.y` 면 직립 (어깨가 화면 위쪽 = y 작음).
    `mid_shoulder.y > mid_hip.y` 면 인버트. PoleAxis.axis_vector 부호와
    독립적 — pole_axis 가 어떤 방향이든 동일 verdict. v3/v4 의
    `dot(torso_up, axis_vector)` 박제 폐기 (`_is_inverted_frame`
    시그너처에서 pole_axis 인자 영구 폐기).

    4 endpoint (left/right shoulder/hip) 중 하나라도 미감지 시 None 반환.
    """
    kp = frame.keypoints_3d
    needed = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")
    for n in needed:
        if n not in kp:
            return None
    mid_shoulder_y = (kp["left_shoulder"].y + kp["right_shoulder"].y) / 2
    mid_hip_y = (kp["left_hip"].y + kp["right_hip"].y) / 2
    # y-down: 위쪽 = y 작음. inverted = 어깨가 hip 아래 = mid_shoulder_y > mid_hip_y.
    return mid_shoulder_y > mid_hip_y


# ── fallback profile (MEDIUM-2 v5 — strictly positive) ────────────────────

def _fallback_profile(warnings: list[str]) -> BodyNormalizationProfile:
    """MEDIUM-2 v5 박제: fallback 시 5 scale 필드 = 1.0, confidence = 0.0.

    __post_init__ validator (strictly positive) 통과 보장.
    """
    return BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.0,
        warnings=warnings,
    )


def _safe_positive(v: float, fallback: float = 1.0) -> float:
    """finite + strictly positive 보장 — NaN/inf/0/negative → fallback."""
    if not math.isfinite(v) or v <= 0.0:
        return fallback
    return v


# ── 메인 함수 ─────────────────────────────────────────────────────────────

def measure_body_profile(
    pose_frames: list[PoseFrame],
) -> BodyNormalizationProfile:
    """RTMW PoseFrame list → BodyNormalizationProfile (video-level 측정).

    Phase 2 BODY-01 박제. 순수 함수 — 외부 의존 0 (numpy + body_normalization).

    Args:
        pose_frames: RTMW 어댑터 산출 PoseFrame list (image y-down 좌표).

    Returns:
        BodyNormalizationProfile (7 필드).
        fallback (insufficient / all-NaN) 시 scale=1.0, confidence=0.0,
        warnings=['insufficient_frames'].
    """
    T = len(pose_frames)

    # ── Edge case: 빈 list 또는 너무 짧음 → fallback ──────────────────────
    if T < MIN_VALID_FRAMES:
        return _fallback_profile(["insufficient_frames"])

    # ── per-frame segment 측정 ────────────────────────────────────────────
    seg_lengths: dict[tuple[str, str, str], np.ndarray] = {}
    seg_confs: dict[tuple[str, str, str], np.ndarray] = {}
    for pair in SEGMENT_PAIRS:
        sn, en, side = pair
        lens = np.empty(T, dtype=float)
        cfs = np.empty(T, dtype=float)
        for t, frame in enumerate(pose_frames):
            length, conf = _measure_segment_per_frame(frame, sn, en)
            lens[t] = length
            cfs[t] = conf
        seg_lengths[pair] = lens
        seg_confs[pair] = cfs

    torso_lens = np.empty(T, dtype=float)
    torso_confs = np.empty(T, dtype=float)
    for t, frame in enumerate(pose_frames):
        length, conf = _measure_torso_per_frame(frame)
        torso_lens[t] = length
        torso_confs[t] = conf

    # ── robust median per segment ─────────────────────────────────────────
    medians: dict[tuple[str, str, str], tuple[float, float]] = {}
    for pair in SEGMENT_PAIRS:
        medians[pair] = _robust_median(seg_lengths[pair], seg_confs[pair])

    torso_median, torso_conf_agg = _robust_median(torso_lens, torso_confs)

    if not math.isfinite(torso_median) or torso_median <= 0.0:
        # torso 미산출 → fallback (모든 ratio 의 분모 X)
        return _fallback_profile(["insufficient_frames"])

    # 좌우 평균 — upper_arm, forearm, thigh, shank.
    def _avg_lr(left_pair: tuple[str, str, str], right_pair: tuple[str, str, str]) -> tuple[float, float]:
        l_med, l_conf = medians[left_pair]
        r_med, r_conf = medians[right_pair]
        finite_pairs: list[tuple[float, float]] = []
        if math.isfinite(l_med):
            finite_pairs.append((l_med, l_conf))
        if math.isfinite(r_med):
            finite_pairs.append((r_med, r_conf))
        if not finite_pairs:
            return float("nan"), 0.0
        avg_med = sum(m for m, _ in finite_pairs) / len(finite_pairs)
        avg_conf = sum(c for _, c in finite_pairs) / len(finite_pairs)
        return avg_med, avg_conf

    upper_arm, upper_arm_conf = _avg_lr(SEGMENT_PAIRS[0], SEGMENT_PAIRS[4])
    forearm, forearm_conf = _avg_lr(SEGMENT_PAIRS[1], SEGMENT_PAIRS[5])
    thigh, thigh_conf = _avg_lr(SEGMENT_PAIRS[2], SEGMENT_PAIRS[6])
    shank, shank_conf = _avg_lr(SEGMENT_PAIRS[3], SEGMENT_PAIRS[7])

    shoulder_width_med, shoulder_width_conf = medians[SEGMENT_PAIRS[8]]
    hip_width_med, hip_width_conf = medians[SEGMENT_PAIRS[9]]

    # ── ratio 계산 ───────────────────────────────────────────────────────
    arm_total = (upper_arm if math.isfinite(upper_arm) else 0.0) + (
        forearm if math.isfinite(forearm) else 0.0
    )
    leg_total = (thigh if math.isfinite(thigh) else 0.0) + (
        shank if math.isfinite(shank) else 0.0
    )

    arm_scale = arm_total / torso_median if torso_median > 0 else float("nan")
    leg_scale = leg_total / torso_median if torso_median > 0 else float("nan")
    torso_scale = 1.0  # self-reference
    if (
        math.isfinite(shoulder_width_med)
        and math.isfinite(hip_width_med)
        and hip_width_med > 0
    ):
        shoulder_hip_ratio = shoulder_width_med / hip_width_med
    else:
        shoulder_hip_ratio = float("nan")

    # M3: estimated_height_scale = (arm_scale + leg_scale + 1.0) / 3.
    estimated_height_scale = (
        ((arm_scale if math.isfinite(arm_scale) else 0.0)
         + (leg_scale if math.isfinite(leg_scale) else 0.0)
         + 1.0) / 3.0
    )

    # MEDIUM-2 v5: 모든 scale 필드 strictly positive 보장 — NaN/0/negative → 1.0.
    arm_scale = _safe_positive(arm_scale, 1.0)
    leg_scale = _safe_positive(leg_scale, 1.0)
    torso_scale = _safe_positive(torso_scale, 1.0)
    shoulder_hip_ratio = _safe_positive(shoulder_hip_ratio, 1.0)
    estimated_height_scale = _safe_positive(estimated_height_scale, 1.0)

    # ── confidence: 11 segment confs 평균 ─────────────────────────────────
    all_confs = [
        upper_arm_conf,
        forearm_conf,
        thigh_conf,
        shank_conf,
        shoulder_width_conf,
        hip_width_conf,
        torso_conf_agg,
    ]
    finite_confs = [c for c in all_confs if math.isfinite(c)]
    confidence = float(sum(finite_confs) / len(finite_confs)) if finite_confs else 0.0
    confidence = max(0.0, min(1.0, confidence))

    # ── Warnings 산출 ────────────────────────────────────────────────────
    warnings: list[str] = []

    # 1) low_keypoint_confidence — 전체 keypoint 평균 conf
    all_kp_confs: list[float] = []
    for frame in pose_frames:
        for kp in frame.keypoints_3d.values():
            all_kp_confs.append(kp.confidence)
    if all_kp_confs:
        mean_kp_conf = float(sum(all_kp_confs) / len(all_kp_confs))
        if mean_kp_conf < LOW_CONFIDENCE_GATE:
            warnings.append("low_keypoint_confidence")

    # 2) occluded_endpoint — endpoint conf<0.5 가 60% 초과
    endpoint_kps = (
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
    )
    occluded_any = False
    for ep in endpoint_kps:
        low_count = 0
        total = 0
        for frame in pose_frames:
            if ep in frame.keypoints_3d:
                total += 1
                if frame.keypoints_3d[ep].confidence < CONF_GATE_PER_FRAME:
                    low_count += 1
        if total > 0 and (low_count / total) > MAX_BAD_FRAME_RATIO:
            occluded_any = True
            break
    if occluded_any:
        warnings.append("occluded_endpoint")

    # 3) insufficient_frames — T < 30
    if T < MIN_FRAMES_FOR_INSUFFICIENT:
        warnings.append("insufficient_frames")

    # 4) asymmetric_landmark_count — 좌/우 valid frame 차이 > 30%
    def _valid_count(side_name: str) -> int:
        count = 0
        for frame in pose_frames:
            if side_name in frame.keypoints_3d and frame.keypoints_3d[side_name].confidence >= CONF_GATE_PER_FRAME:
                count += 1
        return count

    asymmetric = False
    for left_kp, right_kp in (
        ("left_shoulder", "right_shoulder"),
        ("left_hip", "right_hip"),
        ("left_knee", "right_knee"),
    ):
        l_count = _valid_count(left_kp)
        r_count = _valid_count(right_kp)
        max_count = max(l_count, r_count)
        if max_count == 0:
            continue
        diff_ratio = abs(l_count - r_count) / max_count
        if diff_ratio > ASYMMETRIC_FRAME_RATIO:
            asymmetric = True
            break
    if asymmetric:
        warnings.append("asymmetric_landmark_count")

    # 5) pose_too_inverted (MEDIUM-3 v5 — image y-order 직접)
    inverted_results = [_is_inverted_frame(f) for f in pose_frames]
    valid_inv = [r for r in inverted_results if r is not None]
    if valid_inv:
        inverted_ratio = sum(1 for r in valid_inv if r) / len(valid_inv)
        if inverted_ratio > INVERTED_FRAME_RATIO:
            warnings.append("pose_too_inverted")

    return BodyNormalizationProfile(
        estimated_height_scale=estimated_height_scale,
        arm_scale=arm_scale,
        leg_scale=leg_scale,
        torso_scale=torso_scale,
        shoulder_hip_ratio=shoulder_hip_ratio,
        confidence=confidence,
        warnings=warnings,
    )
