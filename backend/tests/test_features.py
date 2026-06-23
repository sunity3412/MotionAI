"""3D 관절각/특징벡터/불확실도 — 합성 좌표로 결정적 검증. AWS 불필요."""

import inspect

import numpy as np
import pytest

from sunity_shared.analysis import skeleton
from sunity_shared.analysis.features import (
    compute_joint_angles,
    feature_vector,
    fill_gaps,
    frame_pair_angle_deltas,
    joint_uncertainty,
    window_median_angle_deltas,
)


def _straight_frame():
    """3D keypoint 한 프레임. 왼쪽 팔꿈치를 직각(90도)으로 배치."""
    kp = np.zeros((17, 3), dtype=float)
    kp[skeleton.kp_index("left_shoulder")] = [0.0, 1.0, 0.0]
    kp[skeleton.kp_index("left_elbow")] = [0.0, 0.0, 0.0]
    kp[skeleton.kp_index("left_wrist")] = [1.0, 0.0, 0.0]
    return kp


def test_right_angle_elbow():
    frames = _straight_frame()[None, :, :]  # (1,17,3)
    angles = compute_joint_angles(frames)
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert angles.shape == (1, skeleton.NUM_JOINTS)
    assert abs(angles[0, j] - 90.0) < 1e-6


def test_uses_z_coordinate():
    """z 를 버리면 0도가 나오는 배치 — 진짜 3D 계산임을 확인."""
    kp = np.zeros((1, 17, 3), dtype=float)
    kp[0, skeleton.kp_index("left_shoulder")] = [0, 1, 0]
    kp[0, skeleton.kp_index("left_elbow")] = [0, 0, 0]
    kp[0, skeleton.kp_index("left_wrist")] = [0, 1, 1]
    angles = compute_joint_angles(kp)
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert abs(angles[0, j] - 45.0) < 1e-6


def test_fourth_channel_ignored_for_angles():
    """4채널(xyz+불확실도) 입력 — 불확실도 채널은 각도 계산에서 무시."""
    kp = np.zeros((1, 17, 4), dtype=float)
    kp[0, :, :3] = _straight_frame()
    kp[0, :, 3] = 9.9  # 불확실도 — 각도에 영향 없어야
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert abs(compute_joint_angles(kp)[0, j] - 90.0) < 1e-6


def test_rejects_2d_input():
    with pytest.raises(ValueError):
        compute_joint_angles(np.zeros((1, 17, 2)))


def test_joint_uncertainty_takes_max_of_defining_keypoints():
    kp = np.zeros((1, 17, 4), dtype=float)
    # left_elbow 각 = shoulder/elbow/wrist 3점. 그 중 하나만 큰 불확실도.
    kp[0, skeleton.kp_index("left_shoulder"), 3] = 0.2
    kp[0, skeleton.kp_index("left_elbow"), 3] = 0.9
    kp[0, skeleton.kp_index("left_wrist"), 3] = 0.1
    u = joint_uncertainty(kp)
    j = skeleton.JOINT_KEYS.index("left_elbow")
    assert u[0, j] == pytest.approx(0.9)  # 3점 중 최댓값


def test_joint_uncertainty_zero_without_uncertainty_channel():
    u = joint_uncertainty(np.zeros((3, 17, 3)))
    assert u.shape == (3, skeleton.NUM_JOINTS)
    assert np.all(u == 0.0)


def test_fill_gaps_interpolates_and_fills_all_nan_column():
    a = np.array([[10.0, np.nan], [np.nan, np.nan], [30.0, np.nan]])
    f = fill_gaps(a)
    assert f[1, 0] == pytest.approx(20.0)  # 선형보간
    assert np.all(f[:, 1] == 0.0)  # 전체 결측 → 0


def test_feature_vector_shape_and_layout():
    a = np.tile(np.arange(skeleton.NUM_JOINTS, dtype=float), (5, 1))  # (5,J)
    F = feature_vector(a, alpha=0.1, beta=0.02)
    J = skeleton.NUM_JOINTS
    assert F.shape == (5, 3 * J)
    # 상수 각도 → 속도/가속 0, 앞 J 열은 원본 각도
    assert np.allclose(F[:, :J], a)
    assert np.allclose(F[:, J:], 0.0)


def test_feature_vector_single_frame_no_crash():
    F = feature_vector(np.ones((1, skeleton.NUM_JOINTS)))
    assert F.shape == (1, 3 * skeleton.NUM_JOINTS)


# ─────────── Task 1 (23-02): frame-specific 표시 각도 (D-10 HIGH-3) ───────────
#
# 표시용 per-joint 각도는 verdict 를 낸 그 still 프레임 쌍(user_frame_idx/ref_frame_idx)
# 의 행 값에서만 계산한다 — DTW window median 아님. window median 을 쓰려면 별도
# windowMedianAngleDeltas 함수로만 노출.


def _angle_matrix_for(joint: str, deg_by_frame: dict[int, float], n_frames: int):
    """(T, NUM_JOINTS) 각도 행렬 — 한 관절만 프레임별 지정 각도, 나머지는 0."""
    j = skeleton.JOINT_KEYS.index(joint)
    m = np.zeros((n_frames, skeleton.NUM_JOINTS), dtype=float)
    for t in range(n_frames):
        m[t, j] = deg_by_frame.get(t, 0.0)
    return m, j


def test_frame_pair_angle_deltas_uses_only_selected_frame_rows():
    """user_frame_idx/ref_frame_idx 의 그 행 값에서만 각도 계산 (frame-specific 핵심)."""
    # 무릎: 학생 프레임 5 = 145°, 정은지 프레임 3 = 178°. 다른 프레임은 미끼.
    student, j = _angle_matrix_for(
        "left_knee", {5: 145.0, 0: 10.0, 9: 99.0}, 10
    )
    reference, _ = _angle_matrix_for(
        "left_knee", {3: 178.0, 0: 20.0, 9: 88.0}, 10
    )
    out = frame_pair_angle_deltas(
        student, reference, user_frame_idx=5, ref_frame_idx=3
    )
    by_joint = {d["joint"]: d for d in out}
    assert "left_knee" in by_joint
    d = by_joint["left_knee"]
    assert d["student_deg"] == pytest.approx(145.0)
    assert d["reference_deg"] == pytest.approx(178.0)
    assert d["delta_deg"] == pytest.approx(145.0 - 178.0)  # -33
    assert d["direction"] == "더 굽음"  # delta<0 → 더 굽음 (작은 각 = 굽음)
    assert d["source"] == "geometry"


def test_frame_pair_angle_deltas_direction_more_extended():
    """delta>0 (학생이 더 큰 각) → '더 펴짐'."""
    student, _ = _angle_matrix_for("left_elbow", {2: 175.0}, 4)
    reference, _ = _angle_matrix_for("left_elbow", {1: 150.0}, 4)
    out = frame_pair_angle_deltas(
        student, reference, user_frame_idx=2, ref_frame_idx=1
    )
    d = {x["joint"]: x for x in out}["left_elbow"]
    assert d["delta_deg"] == pytest.approx(25.0)
    assert d["direction"] == "더 펴짐"


def test_frame_pair_differs_from_window_median():
    """선택 프레임 각도 ≠ window median 인 케이스 — 표시는 프레임 행값, median 은 별도 키."""
    # 무릎 학생: 프레임 5 = 145 (선택), 주변 윈도우는 100/110/120 → median ≈ 110.
    student, j = _angle_matrix_for(
        "left_knee", {3: 100.0, 4: 110.0, 5: 145.0, 6: 120.0, 7: 130.0}, 10
    )
    reference, _ = _angle_matrix_for(
        "left_knee", {1: 170.0, 2: 175.0, 3: 178.0, 4: 176.0}, 10
    )
    # 표시 함수 = 프레임 행값 (median 아님).
    disp = frame_pair_angle_deltas(
        student, reference, user_frame_idx=5, ref_frame_idx=3
    )
    d = {x["joint"]: x for x in disp}["left_knee"]
    assert d["student_deg"] == pytest.approx(145.0)  # 프레임 5 행값 (median 110 아님)

    # window median 함수 = 별도 명명 + sourceFrameIndices/windowPolicy 동반.
    win = window_median_angle_deltas(
        student, reference,
        user_frame_idx=5, ref_frame_idx=3, window=2,
    )
    assert "windowPolicy" in win
    assert "sourceFrameIndices" in win
    md = {x["joint"]: x for x in win["deltas"]}["left_knee"]
    # 프레임 3..7 의 median = 120 (100,110,120,130,145 → median 120). 145 와 다름.
    assert md["student_deg"] != pytest.approx(145.0)
    assert md["student_deg"] == pytest.approx(120.0)


def test_frame_pair_excludes_nan_joint_rows():
    """선택 프레임 행의 한쪽이 NaN 인 관절은 결과에서 제외."""
    student, j = _angle_matrix_for("left_hip", {2: 120.0}, 4)
    student[2, j] = np.nan  # 선택 프레임에서 NaN
    reference, _ = _angle_matrix_for("left_hip", {1: 175.0}, 4)
    out = frame_pair_angle_deltas(
        student, reference, user_frame_idx=2, ref_frame_idx=1
    )
    assert all(d["joint"] != "left_hip" for d in out)


def test_frame_pair_output_has_no_distance_or_percent_keys():
    """출력에 cm/px/거리/percent 키 부재 — 각도(도)만."""
    student, _ = _angle_matrix_for("right_knee", {1: 140.0}, 3)
    reference, _ = _angle_matrix_for("right_knee", {1: 178.0}, 3)
    out = frame_pair_angle_deltas(
        student, reference, user_frame_idx=1, ref_frame_idx=1
    )
    assert out, "최소 1개 관절 산출"
    banned = {"cm", "px", "distance", "percent", "notch", "칸"}
    for d in out:
        for k in d:
            assert k.lower() not in banned, f"금지 키 {k}"
            assert "%" not in str(d.get(k, "")), "percent 표기 금지"


def test_frame_pair_does_not_call_dtw_median():
    """표시 함수 본문이 per_joint_deviation(DTW median scoring 경로)을 호출하지 않는다."""
    src = inspect.getsource(frame_pair_angle_deltas)
    assert "per_joint_deviation" not in src


def test_frame_pair_function_is_pure_no_heavy_imports():
    """features.py 모듈에 boto3/google.genai/requests 모듈-레벨 import 0 (순수)."""
    import sunity_shared.analysis.features as feat

    src = inspect.getsource(feat)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            assert "boto3" not in stripped
            assert "google" not in stripped
            assert "requests" not in stripped
