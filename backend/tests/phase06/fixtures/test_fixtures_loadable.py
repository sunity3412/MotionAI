"""Phase 6 fixture sanity smoke test (Wave 0 selfcheck).

6 fixture JSON 모두 _factory.pose_frame_from_dict 로 list[PoseFrame] 로 로딩 가능
+ 각 fixture 의 의도된 임계값 정합 검증.

본 sanity test 가 GREEN 이면 Task 1 완료. Tasks 2~5 는 본 fixture 의존.
"""

from __future__ import annotations

import math

from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

from tests.phase06.fixtures._factory import (
    load_fixture_raw,
    load_paired_frames,
    load_single_frames,
)


# ── Test 1: 6 fixture loadable + RTMW COCO-17 17 keypoint 정합 ─────────


def _assert_frame_keypoints_complete(frames: list, fixture_name: str) -> None:
    """각 frame 의 keypoints_3d 가 17 keypoint 모두 포함."""
    assert len(frames) >= 10, (
        f"{fixture_name} 의 frame 수 < 10 (실제 {len(frames)})"
    )
    for i, frame in enumerate(frames):
        for kp_name in KEYPOINT_NAMES:
            assert kp_name in frame.keypoints_3d, (
                f"{fixture_name}[{i}] 에 '{kp_name}' keypoint 누락"
            )


def test_fixture_160cm_pro_vs_140cm_student_loadable() -> None:
    pro, student = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    _assert_frame_keypoints_complete(pro, "fixture_160cm_pro_vs_140cm_student.pro_frames")
    _assert_frame_keypoints_complete(student, "fixture_160cm_pro_vs_140cm_student.student_frames")


def test_fixture_lefty_vs_righty_twist_loadable() -> None:
    frames = load_single_frames("fixture_lefty_vs_righty_twist")
    _assert_frame_keypoints_complete(frames, "fixture_lefty_vs_righty_twist")


def test_fixture_foreshortening_lying_pose_loadable() -> None:
    frames = load_single_frames("fixture_foreshortening_lying_pose")
    _assert_frame_keypoints_complete(frames, "fixture_foreshortening_lying_pose")


def test_fixture_unstable_arm_swing_loadable() -> None:
    frames = load_single_frames("fixture_unstable_arm_swing")
    _assert_frame_keypoints_complete(frames, "fixture_unstable_arm_swing")


def test_fixture_split_angle_hipline_loadable() -> None:
    short, long_ = load_paired_frames(
        "fixture_split_angle_hipline",
        key_a="short_leg_frames",
        key_b="long_leg_frames",
    )
    _assert_frame_keypoints_complete(short, "fixture_split_angle_hipline.short_leg_frames")
    _assert_frame_keypoints_complete(long_, "fixture_split_angle_hipline.long_leg_frames")


def test_fixture_high_dispersion_arms_sprawled_loadable() -> None:
    frames = load_single_frames("fixture_high_dispersion_arms_sprawled")
    _assert_frame_keypoints_complete(frames, "fixture_high_dispersion_arms_sprawled")


# ── Test 2: fixture_160cm_pro_vs_140cm_student metadata 정합 ──────────


def test_fixture_160cm_pro_vs_140cm_student_metadata() -> None:
    raw = load_fixture_raw("fixture_160cm_pro_vs_140cm_student")
    assert raw["metadata"]["scale_ratio"] == 0.875, (
        f"scale_ratio expected 0.875, got {raw['metadata']['scale_ratio']}"
    )
    assert len(raw["pro_frames"]) >= 10
    assert len(raw["student_frames"]) >= 10


# ── Test 3: fixture_lefty_vs_righty_twist Twist 자세 정합 ─────────────


def test_fixture_lefty_vs_righty_twist_asymmetry() -> None:
    raw = load_fixture_raw("fixture_lefty_vs_righty_twist")
    md = raw["metadata"]
    assert md.get("intentional_asymmetry") is True
    # 두 키 중 하나 이상 있으면 OK (구 카멜/스네이크 호환)
    assert (
        md.get("expected_shoulder_hip_ratio") is not None
    ), "expected_shoulder_hip_ratio metadata 누락"


# ── Test 4: fixture_foreshortening_lying_pose 픽셀 거리 정합 ──────────


def test_fixture_foreshortening_lying_pose_pixel_distance() -> None:
    frames = load_single_frames("fixture_foreshortening_lying_pose")
    # 평균 어깨-골반 픽셀 거리 < 150px 검증
    distances = []
    for f in frames:
        kp = f.keypoints_3d
        ls = kp["left_shoulder"]
        rs = kp["right_shoulder"]
        lh = kp["left_hip"]
        rh = kp["right_hip"]
        msx = (ls.x + rs.x) / 2
        msy = (ls.y + rs.y) / 2
        mhx = (lh.x + rh.x) / 2
        mhy = (lh.y + rh.y) / 2
        d = math.sqrt((mhx - msx) ** 2 + (mhy - msy) ** 2)
        distances.append(d)
    avg_d = sum(distances) / len(distances)
    assert avg_d < 150.0, (
        f"foreshortening fixture 의 어깨-골반 평균 픽셀 거리 < 150 필요, "
        f"실제 {avg_d:.1f}"
    )


# ── Test 5: fixture_unstable_arm_swing temporal variance > 10% 검증 ──


def test_fixture_unstable_arm_swing_temporal_variance() -> None:
    frames = load_single_frames("fixture_unstable_arm_swing")
    # 좌측 팔 (shoulder→elbow) 길이 분산 / 평균
    lengths = []
    for f in frames:
        kp = f.keypoints_3d
        ls = kp["left_shoulder"]
        le = kp["left_elbow"]
        L = math.sqrt((le.x - ls.x) ** 2 + (le.y - ls.y) ** 2)
        lengths.append(L)
    mean_L = sum(lengths) / len(lengths)
    var = sum((x - mean_L) ** 2 for x in lengths) / len(lengths)
    std = math.sqrt(var)
    ratio = std / mean_L if mean_L > 0 else 0.0
    assert ratio > 0.10, (
        f"unstable_arm_swing 의 좌팔 길이 std/mean > 10% 필요, "
        f"실제 {ratio:.3f}"
    )


# ── Test 6: fixture_split_angle_hipline hip→knee 각도 동일 + toe→toe 다름 ──


def _hip_knee_angle_deg(frame) -> float:
    """단일 frame 의 hip→knee 라인 각도 (vertical down 기준 cos law).

    여기서는 단순화: left hip→knee 벡터 vs (0,1,0) 의 각도.
    """
    kp = frame.keypoints_3d
    lh = kp["left_hip"]
    lk = kp["left_knee"]
    dx = lk.x - lh.x
    dy = lk.y - lh.y
    norm = math.sqrt(dx * dx + dy * dy)
    if norm == 0:
        return 0.0
    cos_a = dy / norm
    cos_a = max(-1.0, min(1.0, cos_a))
    return math.degrees(math.acos(cos_a))


def test_fixture_split_angle_hipline_same_angle_diff_distance() -> None:
    short, long_ = load_paired_frames(
        "fixture_split_angle_hipline",
        key_a="short_leg_frames",
        key_b="long_leg_frames",
    )
    # 각 list 의 평균 hip→knee 각도
    short_angles = [_hip_knee_angle_deg(f) for f in short]
    long_angles = [_hip_knee_angle_deg(f) for f in long_]
    short_mean = sum(short_angles) / len(short_angles)
    long_mean = sum(long_angles) / len(long_angles)
    assert abs(short_mean - long_mean) < 0.5, (
        f"hip→knee 각도 차이 < 0.5° 필요, 실제 |{short_mean:.2f} - "
        f"{long_mean:.2f}| = {abs(short_mean - long_mean):.3f}"
    )

    # toe→toe (ankle 좌우) Euclidean
    def _toe_to_toe(frames):
        ds = []
        for f in frames:
            la = f.keypoints_3d["left_ankle"]
            ra = f.keypoints_3d["right_ankle"]
            ds.append(math.sqrt((ra.x - la.x) ** 2 + (ra.y - la.y) ** 2))
        return sum(ds) / len(ds)

    short_toe = _toe_to_toe(short)
    long_toe = _toe_to_toe(long_)
    assert (long_toe - short_toe) > 100.0, (
        f"toe→toe Euclidean 차이 > 100px 필요, "
        f"long {long_toe:.1f} - short {short_toe:.1f} = {long_toe - short_toe:.1f}"
    )


# ── Test 7 (R5 fix 신규): fixture_high_dispersion_arms_sprawled 의 C_s ratio 정합 ──


def test_fixture_high_dispersion_arms_sprawled_dispersion_ratio() -> None:
    raw = load_fixture_raw("fixture_high_dispersion_arms_sprawled")
    assert raw["metadata"]["expected_dispersion_ratio"] == 3.2

    frames = load_single_frames("fixture_high_dispersion_arms_sprawled")
    # C_s(t) = mean over joints of ||P_j(t) - centroid(t)||
    # shoulder_width = ||left_shoulder - right_shoulder||
    ratios = []
    for f in frames:
        kp = f.keypoints_3d
        # 단순화: 17 keypoint 모두 사용
        xs = [v.x for v in kp.values()]
        ys = [v.y for v in kp.values()]
        cx_centroid = sum(xs) / len(xs)
        cy_centroid = sum(ys) / len(ys)
        dispersions = [
            math.sqrt((v.x - cx_centroid) ** 2 + (v.y - cy_centroid) ** 2)
            for v in kp.values()
        ]
        c_s = sum(dispersions) / len(dispersions)
        ls = kp["left_shoulder"]
        rs = kp["right_shoulder"]
        shoulder_w = math.sqrt((rs.x - ls.x) ** 2 + (rs.y - ls.y) ** 2)
        if shoulder_w > 0:
            ratios.append(c_s / shoulder_w)
    avg_ratio = sum(ratios) / len(ratios)
    assert avg_ratio >= 3.0, (
        f"high_dispersion fixture 의 C_s/shoulder_width 평균 >= 3.0 필요, "
        f"실제 {avg_ratio:.2f}"
    )
