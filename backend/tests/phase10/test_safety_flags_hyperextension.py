"""Phase 10 Wave 0 — D-05 관절 과신전 firing-rule + helper-contract.

GREEN = 정답이 [] 인 케이스 (stub). xfail(strict) = 플래그가 SHOULD fire (10-03 flip).
각 single-variable no-flag 테스트는 게이트를 ONE 만 격리하도록 precondition 을 먼저
assert 한다 — pass 가 오직 게이트에서만 오게 (무관한 mismatch 가 아니라).

per Plan 10-01 Task 3 + CONTEXT D-05.
"""

from __future__ import annotations

import numpy as np
import pytest

from sunity_shared.analysis.features import compute_joint_angles
from sunity_shared.analysis.safety_flags import compute_safety_flags
from sunity_shared.analysis.skeleton import JOINT_KEYS, KEYPOINT_NAMES, kp_index

from .conftest import (
    CLEAR_FLEXION_MAX,
    HOLD_WINDOW,
    REAL_ELITE_FIXTURE_PATH,
    REAL_ELITE_PINNED_IDS,
)


def _call(*, angles, keypoints_4ch, report, profile, mode="mode1", dimension_scores=None):
    return compute_safety_flags(
        angles=angles,
        keypoints_4ch=keypoints_4ch,
        force_signals_report=report,
        dimension_scores=dimension_scores or {},
        reference_angles=None,
        experience=None,
        reference_level=None,
        mode=mode,
        profile=profile,
    )


def _knee_min_included(kp_4ch) -> float:
    """clip 전체에서 left_knee included angle 최솟값 (calibration premise 검증용)."""
    ang = compute_joint_angles(kp_4ch)
    return float(np.nanmin(ang[:, JOINT_KEYS.index("left_knee")]))


# ── GREEN: no-flag 불변식 ────────────────────────────────────────────────────


def test_flexed_knee_no_flag(flexed_knee_4ch, high_control_loss_report, hold_profile) -> None:
    """forward flexion (과신전 아님) → 통제 상실 있어도 플래그 없음."""
    ang = compute_joint_angles(flexed_knee_4ch)
    assert _call(angles=ang, keypoints_4ch=flexed_knee_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_ambiguous_geometry_no_flag(ambiguous_geometry_4ch, high_control_loss_report, hold_profile) -> None:
    """hinge keypoint 高 uncertainty → fail-conservative → 플래그 없음."""
    ang = compute_joint_angles(ambiguous_geometry_4ch)
    assert _call(angles=ang, keypoints_4ch=ambiguous_geometry_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_elite_extension_no_joint_flag(elite_angles, high_control_loss_report, hold_profile) -> None:
    """곧은 신전 hold (과신전 아님) → joint flag 없음."""
    straight = np.zeros((elite_angles.shape[0], 17, 4), dtype=np.float32)
    # 좌표 부재여도 stub 은 [] — 본 케이스 정답은 [] (과신전 방향 없음).
    assert _call(angles=elite_angles, keypoints_4ch=straight, report=high_control_loss_report, profile=hold_profile) == []


def test_d05_wrong_phase_no_flag(reverse_bent_knee_4ch, wrong_phase_knee_control_loss_report, hold_profile) -> None:
    """SINGLE-VARIABLE phase isolator — 관절은 맞고(left_knee ∈ unstable) PHASE 만 틀림.
    phase 게이트 제거 시 flag → 따라서 pass 는 phase 게이트에서만 온다."""
    report = wrong_phase_knee_control_loss_report
    joint_hit = any("left_knee" in m.unstable_body_parts for m in report.stability_metrics)
    assert joint_hit, "precondition: left_knee must be in unstable_body_parts (joint gate satisfied)"
    ang = compute_joint_angles(reverse_bent_knee_4ch)
    assert _call(angles=ang, keypoints_4ch=reverse_bent_knee_4ch, report=report, profile=hold_profile) == []


def test_d05_wrong_joint_no_flag(reverse_bent_knee_4ch, wrong_joint_same_phase_report, hold_profile) -> None:
    """SINGLE-VARIABLE joint isolator — phase 는 hold 와 겹치고 JOINT 만 틀림(left_elbow).
    joint-locality 게이트 제거 시 flag → 따라서 pass 는 joint 게이트에서만 온다."""
    report = wrong_joint_same_phase_report
    phase_overlaps = any(
        m.phase == "hold" for m in report.stability_metrics
    ) and any(b.phase == "hold" for b in report.phase_boundaries)
    assert phase_overlaps, "precondition: instability phase overlaps posture hold window (phase gate satisfied)"
    ang = compute_joint_angles(reverse_bent_knee_4ch)
    assert _call(angles=ang, keypoints_4ch=reverse_bent_knee_4ch, report=report, profile=hold_profile) == []


def test_d05_missing_phase_boundaries_no_flag(reverse_bent_knee_4ch, no_phase_boundaries_report, hold_profile) -> None:
    """phase_boundaries 빈 → _phase_for_window None → no-op."""
    assert no_phase_boundaries_report.phase_boundaries == []
    ang = compute_joint_angles(reverse_bent_knee_4ch)
    assert _call(angles=ang, keypoints_4ch=reverse_bent_knee_4ch, report=no_phase_boundaries_report, profile=hold_profile) == []


def test_d05_frame_mismatch_no_flag(reverse_bent_knee_4ch, high_control_loss_report, hold_profile) -> None:
    """keypoints row count != angles row count → no-op (방어)."""
    ang = compute_joint_angles(reverse_bent_knee_4ch)
    truncated = reverse_bent_knee_4ch[:-5]  # frame count mismatch by construction
    assert truncated.shape[0] != ang.shape[0]
    assert _call(angles=ang, keypoints_4ch=truncated, report=high_control_loss_report, profile=hold_profile) == []


# ── xfail-strict: positive (10-03 에서 flip) ────────────────────────────────


def test_reverse_bent_knee_with_control_loss_flags(reverse_bent_knee_4ch, high_control_loss_report, hold_profile) -> None:
    ang = compute_joint_angles(reverse_bent_knee_4ch)
    flags = _call(angles=ang, keypoints_4ch=reverse_bent_knee_4ch, report=high_control_loss_report, profile=hold_profile)
    assert any(f.flag_type == "joint_hyperextension" for f in flags)


def test_d05_same_phase_positive(reverse_bent_knee_4ch, high_control_loss_report, hold_profile) -> None:
    """reverse_bent_knee(two-segment) + SAME-phase knee control-loss → 정확히 1
    joint_hyperextension. calibration premise(10-03): clip 의 min included angle <
    CLEAR_FLEXION_MAX 라 positive 경로 도달 가능."""
    assert _knee_min_included(reverse_bent_knee_4ch) < CLEAR_FLEXION_MAX
    ang = compute_joint_angles(reverse_bent_knee_4ch)
    flags = _call(angles=ang, keypoints_4ch=reverse_bent_knee_4ch, report=high_control_loss_report, profile=hold_profile)
    jh = [f for f in flags if f.flag_type == "joint_hyperextension"]
    assert len(jh) == 1


def test_d05_multi_joint_picks_worst_with_tiebreak(multi_joint_reverse_bent_4ch, high_control_loss_report, hold_profile) -> None:
    """무릎 AND 팔꿈치 reverse-bend + same-phase 통제 상실 → 정확히 1 consolidated
    flag (worst severity, 고정 tie-break left_knee,right_knee,left_elbow,right_elbow)."""
    assert _knee_min_included(multi_joint_reverse_bent_4ch) < CLEAR_FLEXION_MAX
    ang = compute_joint_angles(multi_joint_reverse_bent_4ch)
    flags = _call(angles=ang, keypoints_4ch=multi_joint_reverse_bent_4ch, report=high_control_loss_report, profile=hold_profile)
    jh = [f for f in flags if f.flag_type == "joint_hyperextension"]
    assert len(jh) == 1


def test_d05_uncertainty_channel_not_inverted(reverse_bent_knee_4ch, uncertain_reverse_bent_4ch, high_control_loss_report, hold_profile) -> None:
    """LOW uncertainty(ch3≈0.05) → SHOULD flag / HIGH uncertainty(ch3≈0.9) → MUST NOT.
    채널이 반전되지 않았음을 증명 (uncertainty_proxy, NOT confidence)."""
    ang_low = compute_joint_angles(reverse_bent_knee_4ch)
    low = _call(angles=ang_low, keypoints_4ch=reverse_bent_knee_4ch, report=high_control_loss_report, profile=hold_profile)
    ang_high = compute_joint_angles(uncertain_reverse_bent_4ch)
    high = _call(angles=ang_high, keypoints_4ch=uncertain_reverse_bent_4ch, report=high_control_loss_report, profile=hold_profile)
    low_fires = any(f.flag_type == "joint_hyperextension" for f in low)
    high_fires = any(f.flag_type == "joint_hyperextension" for f in high)
    assert low_fires and not high_fires


def test_d05_nan_unused_keypoint_still_flags(reverse_bent_knee_4ch, high_control_loss_report, hold_profile) -> None:
    """안 쓰는 keypoint(nose)에 NaN 주입해도 무릎 과신전 flag 는 여전히 발화 →
    NaN 가드가 쓰이는 keypoint 에만 스코프됨 (blanket NaN-anywhere reject 아님)."""
    from sunity_shared.analysis.skeleton import kp_index

    kp = reverse_bent_knee_4ch.copy()
    kp[:, kp_index("nose"), :3] = np.nan
    kp[:, kp_index("nose"), 3] = 1.0
    ang = compute_joint_angles(reverse_bent_knee_4ch)  # nose 는 관절각 미사용
    flags = _call(angles=ang, keypoints_4ch=kp, report=high_control_loss_report, profile=hold_profile)
    assert any(f.flag_type == "joint_hyperextension" for f in flags)


# ── Task 2: robustness hardening (좌우 대칭/결정론/윈도우 집계/scoped-NaN 양면) ──


def test_d05_left_right_symmetry(
    reverse_bent_knee_4ch,
    reverse_bent_right_knee_4ch,
    flexed_knee_4ch,
    high_control_loss_report,
    right_knee_control_loss_report,
    hold_profile,
) -> None:
    """좌·우 무릎 모두 reverse-bend → flag, forward-fold/straight → no flag.
    frontal 축이 per-side 일관(mirror-flip 버그 없음)임을 증명."""
    ang_l = compute_joint_angles(reverse_bent_knee_4ch)
    left = _call(angles=ang_l, keypoints_4ch=reverse_bent_knee_4ch, report=high_control_loss_report, profile=hold_profile)
    assert any(f.flag_type == "joint_hyperextension" for f in left), "left reverse-bend should flag"

    ang_r = compute_joint_angles(reverse_bent_right_knee_4ch)
    right = _call(angles=ang_r, keypoints_4ch=reverse_bent_right_knee_4ch, report=right_knee_control_loss_report, profile=hold_profile)
    assert any(f.flag_type == "joint_hyperextension" for f in right), "right reverse-bend should flag"

    ang_f = compute_joint_angles(flexed_knee_4ch)
    assert _call(angles=ang_f, keypoints_4ch=flexed_knee_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_d05_elbow_reverse_bend_flags(reverse_bent_elbow_4ch, high_control_loss_report, hold_profile) -> None:
    """팔꿈치 reverse-bend (frontal=어깨축) → flag — knee 경로와 대칭."""
    ang = compute_joint_angles(reverse_bent_elbow_4ch)
    flags = _call(angles=ang, keypoints_4ch=reverse_bent_elbow_4ch, report=high_control_loss_report, profile=hold_profile)
    assert any(f.flag_type == "joint_hyperextension" for f in flags)


def test_d05_determinism_same_clip_twice(reverse_bent_knee_4ch, high_control_loss_report, hold_profile) -> None:
    """같은 clip 2회 → 동일 verdict (min-angle calibration 결정론)."""
    ang = compute_joint_angles(reverse_bent_knee_4ch)
    a = _call(angles=ang, keypoints_4ch=reverse_bent_knee_4ch, report=high_control_loss_report, profile=hold_profile)
    b = _call(angles=ang, keypoints_4ch=reverse_bent_knee_4ch, report=high_control_loss_report, profile=hold_profile)
    assert [(f.severity, f.posture_condition) for f in a] == [(f.severity, f.posture_condition) for f in b]


def test_d05_window_aggregation_single_spike_no_flag(single_frame_reverse_4ch, high_control_loss_report, hold_profile) -> None:
    """GATE (c): hold 안 단 한 프레임만 역부호 → 다수결 미달 → no flag."""
    ang = compute_joint_angles(single_frame_reverse_4ch)
    assert _call(angles=ang, keypoints_4ch=single_frame_reverse_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_d05_nan_used_keypoint_suppresses(reverse_bent_knee_4ch, high_control_loss_report, hold_profile) -> None:
    """scoped-NaN 반대편 — USED keypoint(left_knee)에 NaN → flag 억제 (스코프 정확성 양면 증명)."""
    kp = reverse_bent_knee_4ch.copy()
    kp[:, kp_index("left_knee"), :3] = np.nan
    ang = compute_joint_angles(reverse_bent_knee_4ch)
    assert _call(angles=ang, keypoints_4ch=kp, report=high_control_loss_report, profile=hold_profile) == []


# ── Task 2: per-branch fail-conservative 게이트 — 브랜치당 1 negative ─────────


def test_d05_gate_high_uncertainty_no_flag(high_uncertainty_4ch, high_control_loss_report, hold_profile) -> None:
    """GATE (a): used keypoint ch3 > MAX_KP_UNCERTAINTY → no flag (통제 상실 있어도)."""
    ang = compute_joint_angles(high_uncertainty_4ch)
    assert _call(angles=ang, keypoints_4ch=high_uncertainty_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_d05_gate_inconsistent_segment_no_flag(inconsistent_segment_4ch, high_control_loss_report, hold_profile) -> None:
    """GATE (b): hold 윈도우 세그먼트 길이 비일관(teleport) → no flag."""
    ang = compute_joint_angles(inconsistent_segment_4ch)
    assert _call(angles=ang, keypoints_4ch=inconsistent_segment_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_d05_gate_degenerate_frontal_no_flag(degenerate_frontal_4ch, high_control_loss_report, hold_profile) -> None:
    """GATE (d): hip 붕괴 → frontal 축 퇴화 → no flag."""
    ang = compute_joint_angles(degenerate_frontal_4ch)
    assert _call(angles=ang, keypoints_4ch=degenerate_frontal_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_d05_gate_spin_collinear_no_flag(spin_collinear_4ch, high_control_loss_report, hold_profile) -> None:
    """GATE (e): frontal≈longitudinal (spin/inversion) → 방위 미해결 → no flag."""
    ang = compute_joint_angles(spin_collinear_4ch)
    assert _call(angles=ang, keypoints_4ch=spin_collinear_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_d05_gate_collinear_segment_no_flag(collinear_segment_4ch, high_control_loss_report, hold_profile) -> None:
    """GATE (f)+floor: 곧은 신전 hold (|u×w|≈0) → 굽힘축 미정의 → no flag."""
    ang = compute_joint_angles(collinear_segment_4ch)
    assert _call(angles=ang, keypoints_4ch=collinear_segment_4ch, report=high_control_loss_report, profile=hold_profile) == []


def test_d05_gate_no_flexion_calibration_no_flag(no_flexion_calibration_4ch, high_control_loss_report, hold_profile) -> None:
    """GATE (g): clip 내내 near-straight/reverse — clear-flexion calibration 프레임 부재 → no flag."""
    ang = compute_joint_angles(no_flexion_calibration_4ch)
    assert _call(angles=ang, keypoints_4ch=no_flexion_calibration_4ch, report=high_control_loss_report, profile=hold_profile) == []


# ── Task 2: multi-clip real-elite 회귀 + fixture schema gate (POD-DEFERRED) ───
#
# pinned-source 정은지 (T,17,4) 가 repo 에 들어오기 전까지 skipif (deferred-items.md).
# npz 가 생기면 자동 활성화 — 합성 데이터로 만족 불가(schema gate 가 (T,17,4) 강제).

_POD_DEFERRED = pytest.mark.skipif(
    not REAL_ELITE_FIXTURE_PATH.exists(),
    reason="pod-deferred: real-elite (T,17,4) needs RunPod RTMW to_coco17_array extraction — see deferred-items.md",
)


@_POD_DEFERRED
def test_real_elite_clips_no_hyperextension(real_elite_clips, high_control_loss_report, hold_profile) -> None:
    """다중 pinned 정은지 클립(spin/invert/split) — 전부 zero joint_hyperextension (D-02 no-FP)."""
    assert real_elite_clips, "real-elite npz present but empty"
    for mid, clip in real_elite_clips.items():
        ang = compute_joint_angles(clip)
        flags = _call(angles=ang, keypoints_4ch=clip, report=high_control_loss_report, profile=hold_profile)
        assert not any(f.flag_type == "joint_hyperextension" for f in flags), f"{mid} produced a hyperextension flag"


@_POD_DEFERRED
def test_real_elite_mirrored_no_flag(real_elite_clips, high_control_loss_report, hold_profile) -> None:
    """ref-invert (inverted/mirrored orientation) → no flag."""
    clip = real_elite_clips.get("ref-invert")
    assert clip is not None, "ref-invert clip missing from npz"
    ang = compute_joint_angles(clip)
    flags = _call(angles=ang, keypoints_4ch=clip, report=high_control_loss_report, profile=hold_profile)
    assert not any(f.flag_type == "joint_hyperextension" for f in flags)


@_POD_DEFERRED
def test_real_elite_spin_no_flag(real_elite_clips, high_control_loss_report, hold_profile) -> None:
    """ref-sideway-spin (spin-around-pole) → no flag (방위 게이트 보존)."""
    clip = real_elite_clips.get("ref-sideway-spin")
    assert clip is not None, "ref-sideway-spin clip missing from npz"
    ang = compute_joint_angles(clip)
    flags = _call(angles=ang, keypoints_4ch=clip, report=high_control_loss_report, profile=hold_profile)
    assert not any(f.flag_type == "joint_hyperextension" for f in flags)


@_POD_DEFERRED
def test_d05_real_elite_fixture_schema(real_elite_clips) -> None:
    """real-elite fixture 가 (T,17,4) + ch3∈[0,1] + fully-NaN-coord 프레임 ch3==1.0 임을 강제 —
    2D(J=8 referenceKeypointReport) / wrong-order 데이터로 회귀 만족 불가."""
    assert real_elite_clips, "real-elite npz present but empty"
    assert set(real_elite_clips.keys()) <= set(REAL_ELITE_PINNED_IDS) or real_elite_clips, "unexpected keys"
    for mid, arr in real_elite_clips.items():
        assert arr.ndim == 3, f"{mid} not 3D"
        assert arr.shape[1] == 17 == len(KEYPOINT_NAMES), f"{mid} joint count != 17"
        assert arr.shape[2] == 4, f"{mid} channel count != 4 (not x,y,z,uncertainty_proxy)"
        ch3 = arr[..., 3]
        finite = np.isfinite(ch3)
        assert np.all((ch3[finite] >= 0.0) & (ch3[finite] <= 1.0)), f"{mid} ch3 out of [0,1]"
        for t in range(arr.shape[0]):
            fully_nan = np.all(np.isnan(arr[t, :, :3]), axis=1)
            if np.any(fully_nan):
                assert np.all(arr[t, fully_nan, 3] == 1.0), f"{mid} frame {t} NaN-coord ch3 != 1.0"
