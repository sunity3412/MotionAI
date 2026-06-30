"""Phase 10 (injury-risk-flags) Wave 0 — programmatic fixtures.

phase08/conftest.py 의 programmatic factory 패턴 미러 (합성 배열 + ForceSignalsReport).

PROVENANCE (regression-only, NOT fit input): 정은지 success/fail 페어 데이터셋에서
영감 받은 fixture 는 모두 KNOWN-ANSWER REGRESSION FIXTURE 이며 calibration/fit 입력이
아니다 ([[calibration-source-hard-gate]] — 보유 13영상 curve-fit 금지). 합성 좌표는
도메인 기하만 인코딩하며 임계값을 fitting 하지 않는다.

CHANNEL CONVENTION: `keypoints_4ch[:, :, 3]` 은 **uncertainty_proxy** 이다
(1.0 = 미감지/최악, low ≈0.05 = 양호 — pose_frame.py:326,335). confidence 가 아니다.
모든 합성 (T,17,4) fixture 는 ch3 를 이 규약대로 채운다 — 양질 keypoint ≈0.05~0.1,
불확실/미감지 keypoint ≈0.8~1.0.

FRAME-ALIGNMENT: 모든 합성 (T,17,4) keypoint fixture 는 함께 테스트되는 angles
행렬과 SAME row count(T) 를 가진다 (angles 에서 도출한 window index 가 keypoints 를
유효하게 인덱싱) — 유일 예외는 frame-mismatch 케이스(테스트 내 truncation 으로 생성).

3D-SOURCE PROVENANCE (review HIGH): 유효한 `(T,17,4)` 3D source 는 오직
`to_coco17_array(pose_frames)` (pose_frame.py:325 → `(x,y,z,uncertainty_proxy)`,
skeleton.KEYPOINT_NAMES 17 keypoint 순서) 뿐이다. 10-03 의 real-elite 3D fixture 도
이를 따라야 한다 — `referenceKeypointReport`(2D 8-keypoint overlay, data=T*J*2, J=8)
와 `reference-angles.json`(angle-only, 8 joint) 은 `(T,17,4)` 3D source 로 금지.

TWO-SEGMENT positive fixture (D-05 calibration premise, 10-03 L111): reverse-bend
positive fixture 는 CALIBRATION 세그먼트(included_angle < CLEAR_FLEXION_MAX=90° 인
명백한 굽힘 프레임)에 이어 REVERSE-BEND HOLD 세그먼트(중립 넘어 과신전)를 가진다.
같은 clip 안의 DIFFERENT 세그먼트다 — calibration 프레임은 argmin(included_angle)
으로 10-03 의 결정론적 flexion-sign 기준을 주고, profile.hold_window 는 hold
세그먼트를 가리켜 `dimensions._select_window` 가 hold 를 선택한다.
"""

from __future__ import annotations

import numpy as np
import pytest

from sunity_shared.analysis.force_signals import (
    ForceSignalsReport,
    PhaseBoundary,
    StabilityMetric,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS, KEYPOINT_NAMES, kp_index
from sunity_shared.analysis.technique import JOINT_EXTEND, TechniqueProfile

# D-05 calibration premise — calibration 프레임의 included angle 상한 (10-03 정합).
CLEAR_FLEXION_MAX = 90.0

# 합성 clip 표준 길이 + hold window. 0~9 = calibration, 10~39 = reverse-bend hold.
_T = 40
_CALIB_END = 10
HOLD_WINDOW = (_CALIB_END, _T)


# ── (T,17,4) keypoint clip 빌더 ──────────────────────────────────────────────

# 대략 곧게 선 figure 의 17 keypoint 기본 좌표 (sagittal-ish, z≈0).
_BASE_XYZ: dict[str, tuple[float, float, float]] = {
    "nose": (0.0, 1.70, 0.0),
    "left_eye": (0.03, 1.72, 0.0),
    "right_eye": (-0.03, 1.72, 0.0),
    "left_ear": (0.06, 1.70, 0.0),
    "right_ear": (-0.06, 1.70, 0.0),
    "left_shoulder": (0.18, 1.40, 0.0),
    "right_shoulder": (-0.18, 1.40, 0.0),
    "left_elbow": (0.22, 1.10, 0.0),
    "right_elbow": (-0.22, 1.10, 0.0),
    "left_wrist": (0.25, 0.85, 0.0),
    "right_wrist": (-0.25, 0.85, 0.0),
    "left_hip": (0.12, 0.90, 0.0),
    "right_hip": (-0.12, 0.90, 0.0),
    "left_knee": (0.13, 0.50, 0.0),
    "right_knee": (-0.13, 0.50, 0.0),
    "left_ankle": (0.14, 0.10, 0.0),
    "right_ankle": (-0.14, 0.10, 0.0),
}

# 세그먼트별 distal keypoint override.
#   flexed   = 명백한 굽힘 (included < 90°) — calibration 세그먼트.
#   straight = 곧은 신전 (~179°) — elite/non-flag.
#   reverse  = 중립 넘어 과신전 (magnitude ~167°, cross-product 부호 반전) — hold.
_LEFT_KNEE_ANKLE = {
    "flexed": (0.70, 0.70, 0.0),
    "straight": (0.14, 0.10, 0.0),
    "reverse": (0.05, 0.10, 0.0),
}
_LEFT_ELBOW_WRIST = {
    "flexed": (0.50, 1.35, 0.0),
    "straight": (0.25, 0.85, 0.0),
    "reverse": (0.20, 0.83, 0.0),
}


def _frame(unc: float = 0.05, overrides: dict[str, tuple[float, float, float]] | None = None) -> np.ndarray:
    """단일 (17,4) 프레임 — 모든 keypoint xyz 채움 + ch3 = uncertainty_proxy."""
    f = np.zeros((len(KEYPOINT_NAMES), 4), dtype=np.float32)
    pos = dict(_BASE_XYZ)
    if overrides:
        pos.update(overrides)
    for name, (x, y, z) in pos.items():
        i = kp_index(name)
        f[i, 0], f[i, 1], f[i, 2] = x, y, z
        f[i, 3] = unc
    return f


def _two_segment_clip(
    *,
    knee_reverse: bool = False,
    elbow_reverse: bool = False,
    hinge_unc: float = 0.05,
) -> np.ndarray:
    """calibration(굽힘) + reverse-bend hold 의 (40,17,4) clip.

    calibration 세그먼트(0~9): 무릎/팔꿈치 모두 명백히 굽힘 (included < 90°) →
    argmin(included_angle) 이 여기 떨어져 10-03 flexion-sign 기준 제공.
    hold 세그먼트(10~39): knee_reverse/elbow_reverse 면 과신전, 아니면 곧은 신전.
    hinge_unc 는 hinge keypoint(무릎+발목 / 팔꿈치+손목)의 ch3 (uncertainty_proxy).
    """
    frames: list[np.ndarray] = []
    for t in range(_T):
        calib = t < _CALIB_END
        ov: dict[str, tuple[float, float, float]] = {}
        # 무릎 (좌측 hinge) — calibration=flexed, hold=reverse|straight
        ov["left_ankle"] = _LEFT_KNEE_ANKLE["flexed"] if calib else (
            _LEFT_KNEE_ANKLE["reverse"] if knee_reverse else _LEFT_KNEE_ANKLE["straight"]
        )
        # 팔꿈치 (좌측 hinge) — calibration=flexed, hold=reverse|straight
        ov["left_wrist"] = _LEFT_ELBOW_WRIST["flexed"] if calib else (
            _LEFT_ELBOW_WRIST["reverse"] if elbow_reverse else _LEFT_ELBOW_WRIST["straight"]
        )
        frame = _frame(unc=0.05, overrides=ov)
        # hinge keypoint 만 hinge_unc 로 (frontal-axis hip/shoulder 는 양질 유지)
        for name in ("left_knee", "left_ankle", "left_elbow", "left_wrist"):
            frame[kp_index(name), 3] = hinge_unc
        frames.append(frame)
    return np.stack(frames, axis=0)


def _straight_clip(unc: float = 0.05) -> np.ndarray:
    """곧게 선 figure (T,17,4) — elite 신전, 과신전 아님."""
    return np.stack([_frame(unc=unc) for _ in range(_T)], axis=0)


# ── angles (T, J) 빌더 ───────────────────────────────────────────────────────


def _angles_constant(value: float = 178.0, t: int = _T) -> np.ndarray:
    """(t, NUM_JOINTS) 일정 각도 행렬 (의도적 극단 신전 hold)."""
    return np.full((t, len(JOINT_KEYS)), value, dtype=float)


def _angles_symmetric(t: int = _T) -> np.ndarray:
    """좌우 대칭 각도 (asymmetry no-flag 용)."""
    a = np.full((t, len(JOINT_KEYS)), 150.0, dtype=float)
    return a


def _angles_with_extreme_at(window: tuple[int, int], t: int = _T) -> np.ndarray:
    """[window] 구간에만 극단(과신전 ~178°)이 나타나는 각도 행렬.

    그 외 구간은 중립(120°). timing-shift DTW 상쇄 검증용.
    """
    a = np.full((t, len(JOINT_KEYS)), 120.0, dtype=float)
    s, e = window
    a[s:e, :] = 178.0
    return a


# ── PhaseBoundary / StabilityMetric / ForceSignalsReport 빌더 ────────────────


def _hold_boundary() -> PhaseBoundary:
    """posture hold window(10~40) 를 'hold' phase 로 매핑."""
    return PhaseBoundary(
        phase="hold",
        start_frame_idx=HOLD_WINDOW[0],
        end_frame_idx=HOLD_WINDOW[1],
        start_ms=HOLD_WINDOW[0] * 33,
        end_ms=HOLD_WINDOW[1] * 33,
        confidence="medium",
        source="heuristic",
    )


def _entry_boundary() -> PhaseBoundary:
    """hold window 와 겹치지 않는 'entry' phase(0~10)."""
    return PhaseBoundary(
        phase="entry",
        start_frame_idx=0,
        end_frame_idx=_CALIB_END,
        start_ms=0,
        end_ms=_CALIB_END * 33,
        confidence="medium",
        source="heuristic",
    )


def _stability(phase: str, severity: str, parts: list[str]) -> StabilityMetric:
    # PRECONDITION: unstable_body_parts 는 반드시 JOINT_KEYS 멤버 (관절각 키).
    for p in parts:
        assert p in JOINT_KEYS, f"unstable_body_part {p!r} not a JOINT_KEYS member"
    return StabilityMetric(
        phase=phase,
        jitter_score=10.0 if severity != "low" else 1.0,
        jerk_score=900.0 if severity != "low" else 50.0,
        hold_stability_score=40.0 if severity != "low" else 95.0,
        unstable_body_parts=list(parts),
        severity=severity,
        confidence="medium",
        warnings=[],
    )


def _report(boundaries: list[PhaseBoundary], metrics: list[StabilityMetric], conf: str = "medium") -> ForceSignalsReport:
    return ForceSignalsReport(
        version="1.0",
        overall_confidence=conf,
        warnings=[],
        phase_boundaries=list(boundaries),
        axis_metrics=[],
        stability_metrics=list(metrics),
        contact_metrics=[],
    )


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def hold_profile() -> TechniqueProfile:
    """hold_window 이 reverse-bend hold 세그먼트를 가리키는 profile."""
    return TechniqueProfile(
        name="미상",
        category="unknown",
        joint_expectations={
            "left_knee": JOINT_EXTEND,
            "right_knee": JOINT_EXTEND,
            "left_elbow": JOINT_EXTEND,
            "right_elbow": JOINT_EXTEND,
        },
        hold_window=HOLD_WINDOW,
    )


@pytest.fixture
def dimension_scores() -> dict[str, int]:
    return {"angle": 95, "line": 95, "stability": 90}


@pytest.fixture
def elite_angles() -> np.ndarray:
    """정은지-style 의도적 극단 신전 hold (near-180°)."""
    return _angles_constant(178.0)


@pytest.fixture
def low_control_loss_report() -> ForceSignalsReport:
    """elite-no-FP 파트너 — 모든 StabilityMetric severity='low', 빈 unstable_body_parts.

    phase_boundaries 에 hold boundary 1개 포함 (phase-localization 가능).
    """
    return _report(
        [_hold_boundary()],
        [_stability("hold", "low", [])],
        conf="medium",
    )


@pytest.fixture
def high_control_loss_report() -> ForceSignalsReport:
    """hold phase 에 knee/elbow/hip 통제 상실 (medium/high) — posture 와 SAME window."""
    return _report(
        [_hold_boundary()],
        [_stability("hold", "high", ["left_hip", "left_knee", "left_elbow"])],
    )


@pytest.fixture
def window_disjoint_report() -> ForceSignalsReport:
    """HIGH-1 TRUNK temporal-colocation negative — 불안정이 hold 와 겹치지 않는
    entry phase 에만 있고, unstable_body_parts 도 posture 의 joint 미포함."""
    return _report(
        [_entry_boundary(), _hold_boundary()],
        [_stability("entry", "high", ["right_knee"])],
    )


@pytest.fixture
def wrong_phase_knee_control_loss_report() -> ForceSignalsReport:
    """HIGH-1 SINGLE-VARIABLE phase-gate isolator — 'left_knee' 는 unstable_body_parts
    에 있으나(joint 게이트 충족), 그 PhaseBoundary phase(entry)가 hold window 와 미겹침.
    오직 PHASE 만 틀림."""
    return _report(
        [_entry_boundary(), _hold_boundary()],
        [_stability("entry", "high", ["left_knee"])],
    )


@pytest.fixture
def wrong_joint_same_phase_report() -> ForceSignalsReport:
    """HIGH-1 SINGLE-VARIABLE joint-locality isolator — 불안정이 hold phase 와
    겹치나(phase 게이트 충족), unstable_body_parts 가 knee 가 아닌 'left_elbow'.
    오직 JOINT 만 틀림."""
    return _report(
        [_hold_boundary()],
        [_stability("hold", "high", ["left_elbow"])],
    )


@pytest.fixture
def no_phase_boundaries_report() -> ForceSignalsReport:
    """D-05 missing-phase no-op — knee-local 통제 상실은 있으나 phase_boundaries 빈.
    `_phase_for_window` → None → localized flag no-op."""
    return _report(
        [],
        [_stability("hold", "high", ["left_knee"])],
    )


@pytest.fixture
def timing_shifted_student_angles() -> np.ndarray:
    """극단 hold 가 frames 10~20 에 나타나는 student 행렬."""
    return _angles_with_extreme_at((10, 20))


@pytest.fixture
def timing_shifted_reference_angles() -> np.ndarray:
    """동일 극단이 frames 30~40 에 나타나는 reference 행렬 (다른 time offset).
    DTW path-alignment 후 두 극단이 짝지어 reference-anchored excess 상쇄 → no-flag."""
    return _angles_with_extreme_at((30, 40))


@pytest.fixture
def flexed_knee_4ch() -> np.ndarray:
    """무릎이 내내 forward flexion (과신전 아님) — no-flag. 곧은 hold."""
    return _two_segment_clip(knee_reverse=False)


@pytest.fixture
def flexed_elbow_4ch() -> np.ndarray:
    """팔꿈치가 내내 forward flexion — no-flag. 곧은 hold."""
    return _two_segment_clip(elbow_reverse=False)


@pytest.fixture
def reverse_bent_knee_4ch() -> np.ndarray:
    """TWO-SEGMENT: calibration fold(0~9, included<90°) + reverse-bend knee hold(10~39).
    ch3 ≈0.05 (양질). profile.hold_window 가 hold 세그먼트를 가리킴 (positive 경로 도달).
    """
    return _two_segment_clip(knee_reverse=True, hinge_unc=0.05)


@pytest.fixture
def reverse_bent_elbow_4ch() -> np.ndarray:
    """TWO-SEGMENT: calibration fold + reverse-bend elbow hold. ch3 ≈0.05."""
    return _two_segment_clip(elbow_reverse=True, hinge_unc=0.05)


@pytest.fixture
def uncertain_reverse_bent_4ch() -> np.ndarray:
    """reverse_bent_knee_4ch 와 동일 TWO-SEGMENT 기하 + reverse-bend 좌표지만
    hinge keypoint 의 ch3 ≈0.9 (high uncertainty). 채널-not-inverted regression
    파트너 — 오직 uncertainty 만 다르다. 올바른 게이트는 flag 금지(반전 게이트는 flag).
    """
    return _two_segment_clip(knee_reverse=True, hinge_unc=0.9)


@pytest.fixture
def multi_joint_reverse_bent_4ch() -> np.ndarray:
    """TWO-SEGMENT: calibration fold(무릎+팔꿈치 둘 다) + hold 에서 무릎 AND 팔꿈치
    동시 reverse-bend. ch3 ≈0.05. D-05 multi-joint consolidation fixture — joint-count
    만 reverse_bent_knee_4ch 와 다름."""
    return _two_segment_clip(knee_reverse=True, elbow_reverse=True, hinge_unc=0.05)


@pytest.fixture
def ambiguous_geometry_4ch() -> np.ndarray:
    """D-05 fail-conservative — hinge keypoint 에 HIGH ch3 uncertainty(≈0.9) →
    신뢰 불가 → no-flag. (reverse-bend 기하지만 hinge 불확실.)"""
    return _two_segment_clip(knee_reverse=True, hinge_unc=0.9)
