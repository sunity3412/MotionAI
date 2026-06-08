"""Task 2: Kinematic Tree Reprojection + ScaleProfile + BodyComparisonSourcePose (C1 fix target-profile-based L_ref, R2 fix flat values, R10 fix source_profile independence)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.body_normalizer import (
    BodyComparisonSourcePose,
    KINEMATIC_TREE_EDGES,
    ScaleProfile,
    _ref_segment_ratio,
    normalize_pose_by_segments,
)
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

from tests.phase06.fixtures._factory import load_paired_frames


def _make_profile(
    *,
    estimated_height_scale: float = 1.0,
    arm_scale: float = 1.0,
    leg_scale: float = 1.0,
    torso_scale: float = 1.0,
    shoulder_hip_ratio: float = 1.0,
    confidence: float = 0.9,
    warnings: list | None = None,
) -> BodyNormalizationProfile:
    return BodyNormalizationProfile(
        estimated_height_scale=estimated_height_scale,
        arm_scale=arm_scale,
        leg_scale=leg_scale,
        torso_scale=torso_scale,
        shoulder_hip_ratio=shoulder_hip_ratio,
        confidence=confidence,
        warnings=warnings if warnings is not None else [],
    )


def _frame_to_source_keypoints(frame) -> dict:
    """PoseFrame → source_keypoints dict[str, (x, y, z)]."""
    return {
        name: (kp.x, kp.y, kp.z) for name, kp in frame.keypoints_3d.items()
    }


# ── Test 1: 160cm pro → 140cm student reproject — torso 픽셀 거리 정합 ──


def test_kinematic_tree_reproject_pro_to_student_140cm() -> None:
    """source = pro pose, target = student profile + student torso_px →
    reproject 결과의 mid_hip→mid_shoulder = target_torso_px × torso_scale."""
    pro_frames, student_frames = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = _frame_to_source_keypoints(pro_frames[0])
    pro_profile = _make_profile(arm_scale=1.0, leg_scale=1.0)
    student_profile = _make_profile(
        estimated_height_scale=0.875,
        arm_scale=0.875,
        leg_scale=0.875,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
    )
    target_torso_px = 175.0  # student 본인 torso 픽셀

    norm = normalize_pose_by_segments(
        pro_kp, pro_profile, student_profile, target_torso_px
    )

    # mid_hip → mid_shoulder 거리 = target_torso_px × torso_scale (1.0)
    mid_hip = norm["mid_hip"]
    mid_shoulder = norm["mid_shoulder"]
    dx = mid_shoulder[0] - mid_hip[0]
    dy = mid_shoulder[1] - mid_hip[1]
    dz = mid_shoulder[2] - mid_hip[2]
    actual_torso_px = math.sqrt(dx * dx + dy * dy + dz * dz)
    assert abs(actual_torso_px - target_torso_px) < 1.0, (
        f"reproject torso 픽셀 거리 = {actual_torso_px:.2f}, "
        f"expected {target_torso_px}"
    )


# ── Test 2: KINEMATIC_TREE_EDGES DAG + mid_hip root ──────────────────────


def test_kinematic_tree_edges_are_dag() -> None:
    """13 edge 가 DAG (mid_hip root, 사이클 없음). 모든 17 keypoint 도달 가능."""
    assert len(KINEMATIC_TREE_EDGES) == 13

    # parents/children 집합
    parents = {p for p, _ in KINEMATIC_TREE_EDGES}
    children = {c for _, c in KINEMATIC_TREE_EDGES}
    # mid_hip 은 어떤 child 도 아니어야 한다 (root)
    assert "mid_hip" not in children, "mid_hip 은 root — child 일 수 없음"

    # 사이클 검사: 각 child 는 한 번만 등장
    assert len(children) == len(KINEMATIC_TREE_EDGES), (
        f"children 중복 발견 — 사이클 가능성. children={sorted(children)}"
    )

    # 도달 가능성: BFS from mid_hip
    children_of: dict[str, list[str]] = {}
    for p, c in KINEMATIC_TREE_EDGES:
        children_of.setdefault(p, []).append(c)
    visited = {"mid_hip"}
    queue = ["mid_hip"]
    while queue:
        node = queue.pop(0)
        for c in children_of.get(node, []):
            if c not in visited:
                visited.add(c)
                queue.append(c)
    # 17 keypoint 중 nose/eye/ear 는 tree 에 포함 안 됨 — 도달 필요 keypoint 만 확인.
    must_reach = {
        "mid_shoulder",
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
    }
    missing = must_reach - visited
    assert not missing, f"keypoint {missing} 가 mid_hip 에서 도달 불가"


# ── Test 3: split 위양성 회피 — hip→knee 각도 동일 ────────────────────


def test_split_angle_hipline_invariant_to_leg_length() -> None:
    """fixture_split_angle_hipline 의 short/long_leg → 정규화 후 hip→knee 각도 동일."""
    short, long_ = load_paired_frames(
        "fixture_split_angle_hipline",
        key_a="short_leg_frames",
        key_b="long_leg_frames",
    )
    profile = _make_profile()
    target_torso_px = 200.0

    def _hip_knee_angle(norm: dict) -> float:
        lh = norm["left_hip"]
        lk = norm["left_knee"]
        dx, dy, dz = lk[0] - lh[0], lk[1] - lh[1], lk[2] - lh[2]
        n = math.sqrt(dx * dx + dy * dy + dz * dz)
        if n < 1e-6:
            return 0.0
        # vs vertical-down (0, 1, 0)
        cos_a = dy / n
        cos_a = max(-1.0, min(1.0, cos_a))
        return math.degrees(math.acos(cos_a))

    s_kp = _frame_to_source_keypoints(short[0])
    l_kp = _frame_to_source_keypoints(long_[0])
    s_norm = normalize_pose_by_segments(s_kp, profile, profile, target_torso_px)
    l_norm = normalize_pose_by_segments(l_kp, profile, profile, target_torso_px)
    s_angle = _hip_knee_angle(s_norm)
    l_angle = _hip_knee_angle(l_norm)
    # 같은 자세 (각도 의도적 동일), 정규화 후도 같아야 한다.
    assert abs(s_angle - l_angle) < 1.0, (
        f"normalized split hip→knee 각도 차이 < 1° 필요, "
        f"|{s_angle:.2f} - {l_angle:.2f}| = {abs(s_angle - l_angle):.3f}"
    )


# ── Test 4: shoulder_hip_ratio OFF → neutral 폭 ──────────────────────


def test_shoulder_hip_ratio_off_returns_neutral_width() -> None:
    """apply_shoulder_hip_ratio=False → mid_shoulder ↔ l/r_shoulder ratio = 0.25."""
    profile = _make_profile(shoulder_hip_ratio=2.0)  # 비정상 큰 값
    ratio_off = _ref_segment_ratio(
        "mid_shoulder",
        "left_shoulder",
        profile,
        apply_shoulder_hip_ratio=False,
    )
    assert ratio_off == 0.25, f"OFF neutral ratio = 0.25 expected, got {ratio_off}"

    ratio_on = _ref_segment_ratio(
        "mid_shoulder",
        "left_shoulder",
        profile,
        apply_shoulder_hip_ratio=True,
    )
    assert ratio_on != 0.25, (
        f"ON ratio 는 0.25 가 아니어야 (shoulder_hip_ratio 반영), got {ratio_on}"
    )


# ── Test 5: ScaleProfile __post_init__ NaN reject ─────────────────────


def test_scale_profile_post_init_rejects_nan() -> None:
    """ScaleProfile 의 numeric 필드에 NaN 입력 시 ValueError."""
    with pytest.raises(ValueError, match="finite"):
        ScaleProfile(
            estimated_height_scale=float("nan"),
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            shoulder_hip_ratio_applied=True,
        )
    with pytest.raises(ValueError, match="positive"):
        ScaleProfile(
            estimated_height_scale=1.0,
            arm_scale=-0.5,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            shoulder_hip_ratio_applied=True,
        )


# ── Test 6: 방향 B — target scale 추종 (C1 fix) ───────────────────────


def test_normalize_direction_b_target_scale_is_student() -> None:
    """160cm pro keypoints → reproject 결과 height 가 student scale 을 따른다."""
    pro_frames, _ = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = _frame_to_source_keypoints(pro_frames[0])
    pro_profile = _make_profile(arm_scale=1.0, leg_scale=1.0)
    student_profile = _make_profile(
        estimated_height_scale=0.875,
        arm_scale=0.875,
        leg_scale=0.875,
        torso_scale=1.0,
    )
    student_torso_px = 175.0
    norm = normalize_pose_by_segments(
        pro_kp, pro_profile, student_profile, student_torso_px
    )

    # mid_hip → mid_shoulder = student_torso_px × torso_scale (1.0)
    mh = norm["mid_hip"]
    ms = norm["mid_shoulder"]
    torso = math.sqrt(
        (ms[0] - mh[0]) ** 2 + (ms[1] - mh[1]) ** 2 + (ms[2] - mh[2]) ** 2
    )
    assert abs(torso - student_torso_px) < 1.0

    # 팔 길이 (left_shoulder → left_elbow + left_elbow → left_wrist) = student arm_scale × torso_px
    ls = norm["left_shoulder"]
    le = norm["left_elbow"]
    lw = norm["left_wrist"]
    upper = math.sqrt((le[0] - ls[0]) ** 2 + (le[1] - ls[1]) ** 2 + (le[2] - ls[2]) ** 2)
    forearm = math.sqrt((lw[0] - le[0]) ** 2 + (lw[1] - le[1]) ** 2 + (lw[2] - le[2]) ** 2)
    total_arm = upper + forearm
    expected_arm = student_profile.arm_scale * student_torso_px
    assert abs(total_arm - expected_arm) < 2.0, (
        f"student arm 길이 = {expected_arm:.1f} expected, got {total_arm:.1f}"
    )


# ── Test 7 (C1 fix 핵심): segment-aware ≠ uniform scale ─────────────


def test_segment_aware_not_uniform_scale() -> None:
    """같은 height + 다른 팔/다리 비율 두 student → 서로 다른 normalized pose."""
    pro_frames, _ = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = _frame_to_source_keypoints(pro_frames[0])
    pro_profile = _make_profile()

    student_a = _make_profile(arm_scale=1.10, leg_scale=0.95, torso_scale=1.0)
    student_b = _make_profile(arm_scale=0.90, leg_scale=1.10, torso_scale=1.0)
    torso_px = 200.0

    norm_a = normalize_pose_by_segments(pro_kp, pro_profile, student_a, torso_px)
    norm_b = normalize_pose_by_segments(pro_kp, pro_profile, student_b, torso_px)

    # mid_shoulder → l_wrist 픽셀 거리 (팔 길이) 비교 — 5% 이상 차이
    def _arm_len(norm: dict) -> float:
        ms = norm["left_shoulder"]
        lw = norm["left_wrist"]
        return math.sqrt(
            (lw[0] - ms[0]) ** 2 + (lw[1] - ms[1]) ** 2 + (lw[2] - ms[2]) ** 2
        )

    arm_a = _arm_len(norm_a)
    arm_b = _arm_len(norm_b)
    diff_ratio = abs(arm_a - arm_b) / max(arm_a, arm_b)
    assert diff_ratio > 0.05, (
        f"segment-aware: studentA arm = {arm_a:.1f}, studentB arm = {arm_b:.1f}, "
        f"차이 비율 {diff_ratio:.3f} > 5% 필요"
    )

    # 마찬가지 mid_hip → l_ankle (다리)
    def _leg_len(norm: dict) -> float:
        mh = norm["left_hip"]
        la = norm["left_ankle"]
        return math.sqrt(
            (la[0] - mh[0]) ** 2 + (la[1] - mh[1]) ** 2 + (la[2] - mh[2]) ** 2
        )

    leg_a = _leg_len(norm_a)
    leg_b = _leg_len(norm_b)
    leg_diff = abs(leg_a - leg_b) / max(leg_a, leg_b)
    assert leg_diff > 0.05, (
        f"segment-aware leg: A={leg_a:.1f}, B={leg_b:.1f}, "
        f"차이 비율 {leg_diff:.3f} > 5% 필요"
    )


# ── Test 8 (R10 fix): source_profile 인자가 결과에 영향 없음 ──────────


def test_normalize_pose_by_segments_output_independent_of_source_profile() -> None:
    """동일 source_keypoints + target_profile + torso_px → source_profile 만 다른 두 호출의 출력 동일."""
    pro_frames, _ = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = _frame_to_source_keypoints(pro_frames[0])
    target_profile = _make_profile(arm_scale=0.875, leg_scale=0.875)
    torso_px = 175.0

    source_a = _make_profile(arm_scale=1.0, leg_scale=1.0)
    source_b = _make_profile(
        arm_scale=0.5,  # 매우 다른 비율
        leg_scale=2.0,
        shoulder_hip_ratio=0.3,
    )

    out_a = normalize_pose_by_segments(pro_kp, source_a, target_profile, torso_px)
    out_b = normalize_pose_by_segments(pro_kp, source_b, target_profile, torso_px)

    # 모든 key 의 좌표가 동일
    assert set(out_a.keys()) == set(out_b.keys())
    for key in out_a:
        a = np.array(out_a[key])
        b = np.array(out_b[key])
        assert np.allclose(a, b, atol=1e-6), (
            f"key={key}: source_profile 변경에 출력이 변함 — R10 회귀. "
            f"a={a}, b={b}"
        )


# ── Test 9 (R2 fix): BodyComparisonSourcePose flat values validation ───


def test_body_comparison_source_pose_post_init_validates_flat_values() -> None:
    """values 길이 != 4 × len(joint_keys) → ValueError. 올바른 길이 PASS."""
    # 잘못된 길이 (4 != 4 × 2 = 8)
    with pytest.raises(ValueError, match="length must be"):
        BodyComparisonSourcePose(
            joint_keys=("nose", "left_eye"),
            values=(1.0, 2.0, 3.0, 0.9),
            frame_index=0,
            torso_px=350.0,
            confidence=0.8,
            measured_at=1700000000000,
        )

    # 올바른 길이 8
    pose = BodyComparisonSourcePose(
        joint_keys=("nose", "left_eye"),
        values=(1.0, 2.0, 3.0, 0.9, 4.0, 5.0, 6.0, 0.8),
        frame_index=0,
        torso_px=350.0,
        confidence=0.8,
        measured_at=1700000000000,
    )
    assert pose.confidence == 0.8

    # confidence 범위 위반
    with pytest.raises(ValueError, match="confidence"):
        BodyComparisonSourcePose(
            joint_keys=("nose",),
            values=(1.0, 2.0, 3.0, 0.9),
            frame_index=0,
            torso_px=350.0,
            confidence=1.5,
            measured_at=1700000000000,
        )

    # torso_px 음수 위반
    with pytest.raises(ValueError, match="torso_px"):
        BodyComparisonSourcePose(
            joint_keys=("nose",),
            values=(1.0, 2.0, 3.0, 0.9),
            frame_index=0,
            torso_px=-1.0,
            confidence=0.5,
            measured_at=1700000000000,
        )


# ── Test 10 (R2 fix): to_keypoints_array reshape ──────────────────────


def test_body_comparison_source_pose_to_keypoints_array_reshape() -> None:
    """flat values → (J, 4) ndarray."""
    pose = BodyComparisonSourcePose(
        joint_keys=("nose", "left_eye"),
        values=(1.0, 2.0, 3.0, 0.9, 4.0, 5.0, 6.0, 0.8),
        frame_index=0,
        torso_px=350.0,
        confidence=0.85,
        measured_at=1700000000000,
    )
    arr = pose.to_keypoints_array()
    assert arr.shape == (2, 4)
    assert np.allclose(arr[0], [1.0, 2.0, 3.0, 0.9])
    assert np.allclose(arr[1], [4.0, 5.0, 6.0, 0.8])
