"""합성 교란 순수 모듈 검증 (22-01 Task 3, D-10a 좌표 보정 자가 라벨).

불변식:
  · 정답 = 교란 전 원좌표 (자가 라벨, 교사 무관 — 사람 점수 라벨 아님).
  · 교란 파라미터(run 길이·지터 크기)는 rtmw_error_profile.json 실측 분포에서 샘플 —
    NLM 임의 수치 하드코딩 금지 (A3).
  · 가려짐 = 키 삭제 금지, Null(NaN) + confidence 저값 덮어쓰기 (D-11 Null 바인딩).
  · numpy 외 서드파티 0, boto3/네트워크 0 (analysis core 순수성).
"""

import numpy as np
import pytest

from datagen import perturb

_JOINTS = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
]


def _profile() -> dict:
    """최소 유효 프로파일 (rtmw_error_profile.json 형상 미러)."""
    return {
        "confidence_drop_run_length": {
            "bin_edges": [1, 2, 3, 4, 5, 6],
            "counts": [10, 5, 3, 1, 1],
            "count": 20,
        },
        "per_joint_jump_deg": {
            "left_knee": {"bin_edges": [0, 2.5, 5, 7.5, 10], "counts": [5, 4, 2, 1], "count": 12},
            "right_knee": {"bin_edges": [0, 2.5, 5, 7.5, 10], "counts": [6, 3, 2, 1], "count": 12},
        },
        "low_confidence_joint_rank": [
            {"joint": "left_knee", "low_conf_fraction": 0.14},
            {"joint": "right_knee", "low_conf_fraction": 0.13},
        ],
    }


def _coords(t: int = 24, c: int = 3) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.random((t, len(_JOINTS), c))


def test_original_preserved_as_ground_truth():
    """Test 1 — 교란 전 원좌표가 정답 라벨로 함께 반환 (자가 라벨)."""
    coords = _coords()
    rng = np.random.default_rng(1)
    res = perturb.perturb_sequence(coords, _profile(), 2, rng, joint_keys=_JOINTS)
    assert res.original.shape == coords.shape
    assert np.array_equal(res.original, coords)  # 정답 = 교란 전.
    assert res.perturbed.shape == coords.shape
    assert len(res.perturbed_joints) >= 1
    assert len(res.perturbed_frames) >= 1
    # 교란은 실제로 변형을 낸다.
    assert not np.array_equal(
        np.nan_to_num(res.perturbed), np.nan_to_num(coords)
    )


def test_occlusion_nulls_value_and_lowers_confidence():
    """Test 2 — 가려짐이 키 삭제 없이 Null(NaN) + confidence 저값으로 덮어쓴다."""
    coords = _coords()
    rng = np.random.default_rng(2)
    res = perturb.perturb_sequence(coords, _profile(), 2, rng, joint_keys=_JOINTS)
    # 관절 축 보존 (삭제 금지).
    assert res.perturbed.shape[1] == coords.shape[1]
    # 가려진 (frame, joint) 는 좌표가 NaN, confidence 채널이 저값.
    found_occlusion = False
    for j in res.perturbed_joints:
        for f in res.perturbed_frames:
            if np.isnan(res.perturbed[f, j, 0]):
                assert np.isnan(res.perturbed[f, j, 1])
                assert res.perturbed[f, j, 2] <= perturb.OCCLUSION_CONFIDENCE
                found_occlusion = True
    assert found_occlusion


def test_profile_required_typeerror():
    """Test 3 — profile 없이(None) 호출하면 TypeError (분포 출처 강제)."""
    coords = _coords()
    rng = np.random.default_rng(3)
    with pytest.raises(TypeError):
        perturb.perturb_sequence(coords, None, 1, rng, joint_keys=_JOINTS)
    # 샘플러는 히스토그램 bin 범위 안에서만 값을 낸다.
    hist = {"bin_edges": [0, 2.5, 5], "counts": [3, 1], "count": 4}
    for _ in range(20):
        v = perturb._sample_histogram(hist, np.random.default_rng(7))
        assert 0.0 <= v <= 5.0


def test_stage_curriculum_structure():
    """Test 4 — stage1=비핵심 소수, stage2=핵심 관절 연속 Null, stage3=L/R 스왑."""
    coords = _coords()
    core = {"left_hip", "right_hip", "left_knee", "right_knee"}
    noncore = set(_JOINTS) - core

    res1 = perturb.perturb_sequence(coords, _profile(), 1, np.random.default_rng(4), joint_keys=_JOINTS)
    names1 = {_JOINTS[j] for j in res1.perturbed_joints}
    assert names1  # 최소 하나 교란.
    assert names1 <= noncore  # stage1 은 비핵심 관절만.

    res2 = perturb.perturb_sequence(coords, _profile(), 2, np.random.default_rng(4), joint_keys=_JOINTS)
    names2 = {_JOINTS[j] for j in res2.perturbed_joints}
    assert names2 & core  # stage2 는 핵심 관절 포함.
    # 연속 다프레임 Null (run length >= 2 존재).
    assert len(res2.perturbed_frames) >= 2

    # stage3 — L/R 스왑 함수 직접 검증.
    swapped, pairs = perturb.swap_lr_joints(coords, _JOINTS)
    assert ("left_knee", "right_knee") in pairs
    lk = _JOINTS.index("left_knee")
    rk = _JOINTS.index("right_knee")
    assert np.array_equal(swapped[:, lk], coords[:, rk])
    assert np.array_equal(swapped[:, rk], coords[:, lk])
    res3 = perturb.perturb_sequence(coords, _profile(), 3, np.random.default_rng(4), joint_keys=_JOINTS)
    assert res3.stage == 3


def test_temporal_trap_is_permutation():
    """Test 5 — 시간 역전/셔플 함정 (언어-프라이어 shortcut 검출용, Pitfall 6)."""
    coords = _coords()
    rng = np.random.default_rng(5)
    trapped = perturb.make_temporal_trap(coords, rng)
    assert trapped.shape == coords.shape
    assert not np.array_equal(trapped, coords)
    # 행 순열이므로 각 열 정렬은 원본과 동일 (프레임 셔플/역전).
    assert np.array_equal(np.sort(coords, axis=0), np.sort(trapped, axis=0))


def test_reproducible_and_pure():
    """Test 6 — 같은 seed → 같은 출력 + numpy 외 import 없음."""
    coords = _coords()
    a = perturb.perturb_sequence(coords, _profile(), 3, np.random.default_rng(42), joint_keys=_JOINTS)
    b = perturb.perturb_sequence(coords, _profile(), 3, np.random.default_rng(42), joint_keys=_JOINTS)
    assert np.array_equal(np.nan_to_num(a.perturbed), np.nan_to_num(b.perturbed))
    assert a.perturbed_joints == b.perturbed_joints
    assert a.perturbed_frames == b.perturbed_frames
    # 모듈 소스에 boto3/requests/urllib import 부재 (순수성).
    src = perturb.__file__
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    for forbidden in ("import boto3", "import requests", "import urllib"):
        assert forbidden not in text


def test_shape_contract_valueerror():
    """(T,J,C) shape 계약 위반 → ValueError (validation.py _as_tj 패턴)."""
    rng = np.random.default_rng(9)
    with pytest.raises(ValueError):
        perturb.perturb_sequence(np.zeros((5, 8)), _profile(), 1, rng, joint_keys=_JOINTS)


# ---------------------------------------------------------------------------
# quick-260715-fjw — 변위(displacement) 위주 stage 재설계 (D1/D2).
# ---------------------------------------------------------------------------
def test_apply_drift_constant_offset_finite_confidence_unchanged():
    """Test A — _apply_drift: run 구간 상수 오프셋, 전부 finite, confidence 불변.

    지속 변위 = 프레임별 독립 노이즈(_apply_jitter)와 달리 run 내 프레임 간 동일한
    오프셋 벡터 — RTMW 지속 오추적 모방. 가려짐(NaN)이 아닌 가시 오류."""
    coords = _coords()
    out = coords.copy()
    rng = np.random.default_rng(11)
    jump_hist = perturb._aggregate_jump_hist(_profile())
    ji = 2
    start, end = 4, 9  # run 길이 5 (>= 2).
    perturb._apply_drift(out, ji, start, end, jump_hist, rng)
    seg = out[start:end, ji, :2]
    orig = coords[start:end, ji, :2]
    # 가시 변위: 값이 변하고 전부 finite (NaN 0).
    assert np.all(np.isfinite(seg))
    assert not np.array_equal(seg, orig)
    # 오프셋은 run 내 프레임 간 동일한 상수 벡터.
    offsets = seg - orig
    assert np.allclose(offsets, offsets[0])
    assert np.linalg.norm(offsets[0]) > 0.0
    # confidence 채널 불변 (가시 오류 — 모델이 영상/궤적으로 잡아내야 함).
    assert np.array_equal(out[:, :, 2], coords[:, :, 2])
    # run 밖 프레임 불변.
    mask = np.ones(coords.shape[0], dtype=bool)
    mask[start:end] = False
    assert np.array_equal(out[mask], coords[mask])


def test_stage_visible_displacement_coverage():
    """Test B — stage 1/2/3 전부 가시 변위 셀(finite + original 과 상이) >= 1.

    특히 stage2 — 종전 순수 가려짐이라 게이트(가시 마스크) 대상 변위 신호가 0 이던
    것을 고정. 가시 변위 셀은 perturbed_joints/perturbed_frames 에 등재돼야 한다."""
    coords = _coords()
    for stage in (1, 2, 3):
        res = perturb.perturb_sequence(
            coords, _profile(), stage, np.random.default_rng(13), joint_keys=_JOINTS
        )
        xy = res.perturbed[:, :, :2]
        visible = np.isfinite(xy).all(axis=2) & (xy != res.original[:, :, :2]).any(axis=2)
        assert visible.any(), f"stage{stage} 가시 변위 셀 0"
        # 가시 변위 셀은 교란 등재 계약을 따른다.
        frames, joints = np.nonzero(visible)
        for f, j in zip(frames.tolist(), joints.tolist()):
            assert j in res.perturbed_joints
            assert f in res.perturbed_frames


def test_stage2_displacement_run_at_least_two_frames():
    """Test B' — stage2 drift 는 연속 >= 2 프레임 가시 변위 (지속 변위 구조)."""
    coords = _coords()
    res = perturb.perturb_sequence(
        coords, _profile(), 2, np.random.default_rng(13), joint_keys=_JOINTS
    )
    xy = res.perturbed[:, :, :2]
    visible = np.isfinite(xy).all(axis=2) & (xy != res.original[:, :, :2]).any(axis=2)
    per_joint = visible.sum(axis=0)
    assert per_joint.max() >= 2, "stage2 가시 변위 run < 2 프레임"
