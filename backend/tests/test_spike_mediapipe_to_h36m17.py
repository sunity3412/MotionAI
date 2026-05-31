"""MediaPipe 33 → H3.6M 17 매핑 어댑터 단위 테스트.

Plan 01-07 — mediapipe 없이 실행 가능. 순수 numpy.

테스트 범위:
  - 입력 형상 검증 (T, 33, 2) / (T, 33, 3) / (33, 2) 단일 프레임
  - 출력 형상 (T, 17, 2) / (T, 17, 3)
  - 직접 대응 관절 인덱스 정확성
  - 파생 관절 (hip, thorax, spine, neck_nose) 좌표 계산 정확성
  - h36m17_to_coco17_subset: 형상 + limb joint 매핑 + face NaN
  - 라운드트립: MP33 → H36M17 → COCO17 limb joints 연속 변환
  - NaN 입력 전파 (미감지 프레임)
  - 잘못된 입력 형상 ValueError
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.research.spikes.mediapipe_to_h36m17 import (
    H36M_IDX,
    H36M_TO_COCO17_LIMB_PAIRS,
    NUM_H36M_JOINTS,
    convert_mp33_to_h36m17,
    h36m17_to_coco17_subset,
)

# ── fixture ──────────────────────────────────────────────────────────────────


def _make_mp_lm(T: int = 3, C: int = 2, seed: int = 42) -> np.ndarray:
    """재현 가능한 가짜 MP 33-landmark 배열 (T, 33, C). 값 범위 [0, 1]."""
    rng = np.random.default_rng(seed)
    return rng.uniform(0.0, 1.0, size=(T, 33, C))


# ── 기본 형상 테스트 ──────────────────────────────────────────────────────────


class TestConvertMp33ToH36m17Shape:
    """convert_mp33_to_h36m17 입출력 형상 검증."""

    def test_output_shape_t33_2_no_conf(self):
        lm = _make_mp_lm(T=5, C=2)
        out = convert_mp33_to_h36m17(lm)
        assert out.shape == (5, 17, 2), f"예상 (5,17,2), 실제 {out.shape}"

    def test_output_shape_t33_3_no_conf(self):
        lm = _make_mp_lm(T=5, C=3)
        out = convert_mp33_to_h36m17(lm)
        assert out.shape == (5, 17, 2), f"C=3 입력이라도 use_visibility_as_conf=False → (5,17,2)"

    def test_output_shape_with_conf(self):
        lm = _make_mp_lm(T=4, C=3)
        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=True)
        assert out.shape == (4, 17, 3), f"예상 (4,17,3), 실제 {out.shape}"

    def test_single_frame_input_expanded(self):
        lm = _make_mp_lm(T=1, C=2).squeeze(0)  # (33, 2)
        assert lm.shape == (33, 2)
        out = convert_mp33_to_h36m17(lm)
        assert out.shape == (1, 17, 2), "단일 프레임 (33,2) → (1,17,2)"

    def test_single_frame_with_visibility(self):
        lm = _make_mp_lm(T=1, C=3).squeeze(0)  # (33, 3)
        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=True)
        assert out.shape == (1, 17, 3)

    def test_num_joints_constant(self):
        assert NUM_H36M_JOINTS == 17


# ── 직접 대응 관절 인덱스 테스트 ─────────────────────────────────────────────


class TestDirectMapping:
    """MediaPipe → H3.6M 직접 대응 관절 좌표 정확성."""

    def _mp_lm_identity(self, T: int = 1) -> np.ndarray:
        """MP 인덱스를 좌표값으로 사용해 대응 확인 쉽게."""
        lm = np.zeros((T, 33, 2), dtype=float)
        for i in range(33):
            lm[:, i, 0] = float(i) * 0.01   # x = 인덱스 * 0.01
            lm[:, i, 1] = float(i) * 0.001  # y = 인덱스 * 0.001
        return lm

    def test_r_hip_direct(self):
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_r_hip = H36M_IDX["r_hip"]  # 1
        assert out[0, h36m_r_hip, 0] == pytest.approx(24 * 0.01), "RHip x = MP[24].x"
        assert out[0, h36m_r_hip, 1] == pytest.approx(24 * 0.001), "RHip y = MP[24].y"

    def test_l_hip_direct(self):
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_l_hip = H36M_IDX["l_hip"]  # 4
        assert out[0, h36m_l_hip, 0] == pytest.approx(23 * 0.01)
        assert out[0, h36m_l_hip, 1] == pytest.approx(23 * 0.001)

    def test_r_knee_direct(self):
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_r_knee = H36M_IDX["r_knee"]  # 2
        assert out[0, h36m_r_knee, 0] == pytest.approx(26 * 0.01)

    def test_l_foot_direct(self):
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_l_foot = H36M_IDX["l_foot"]  # 6
        assert out[0, h36m_l_foot, 0] == pytest.approx(27 * 0.01)  # l_ankle = MP 27

    def test_head_is_nose_proxy(self):
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_head = H36M_IDX["head"]  # 10
        assert out[0, h36m_head, 0] == pytest.approx(0 * 0.01)   # nose = MP 0
        assert out[0, h36m_head, 1] == pytest.approx(0 * 0.001)

    def test_l_shoulder_direct(self):
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_l_sh = H36M_IDX["l_shoulder"]  # 11
        assert out[0, h36m_l_sh, 0] == pytest.approx(11 * 0.01)

    def test_r_wrist_direct(self):
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_r_wr = H36M_IDX["r_wrist"]  # 16
        assert out[0, h36m_r_wr, 0] == pytest.approx(16 * 0.01)  # r_wrist = MP 16


# ── 파생 관절 테스트 ──────────────────────────────────────────────────────────


class TestDerivedJoints:
    """Hip, Thorax, Spine, NeckNose 파생 관절 계산 정확성."""

    def _make_simple(self) -> np.ndarray:
        """특정 joint에 고정값을 넣어 파생 계산 검증."""
        lm = np.zeros((1, 33, 2), dtype=float)
        lm[0, 23, 0] = 0.30  # l_hip x
        lm[0, 23, 1] = 0.60  # l_hip y
        lm[0, 24, 0] = 0.70  # r_hip x
        lm[0, 24, 1] = 0.60  # r_hip y
        lm[0, 11, 0] = 0.35  # l_shoulder x
        lm[0, 11, 1] = 0.20  # l_shoulder y
        lm[0, 12, 0] = 0.65  # r_shoulder x
        lm[0, 12, 1] = 0.20  # r_shoulder y
        lm[0, 0, 0] = 0.50   # nose x
        lm[0, 0, 1] = 0.05   # nose y
        return lm

    def test_hip_is_mean_of_hips(self):
        lm = self._make_simple()
        out = convert_mp33_to_h36m17(lm)
        h36m_hip = H36M_IDX["hip"]  # 0
        assert out[0, h36m_hip, 0] == pytest.approx((0.30 + 0.70) / 2), "Hip x = mean(l_hip, r_hip)"
        assert out[0, h36m_hip, 1] == pytest.approx((0.60 + 0.60) / 2), "Hip y"

    def test_thorax_is_mean_of_shoulders(self):
        lm = self._make_simple()
        out = convert_mp33_to_h36m17(lm)
        h36m_thorax = H36M_IDX["thorax"]  # 8
        assert out[0, h36m_thorax, 0] == pytest.approx((0.35 + 0.65) / 2)
        assert out[0, h36m_thorax, 1] == pytest.approx((0.20 + 0.20) / 2)

    def test_spine_is_mean_of_hip_and_thorax(self):
        lm = self._make_simple()
        out = convert_mp33_to_h36m17(lm)
        h36m_hip = H36M_IDX["hip"]
        h36m_thorax = H36M_IDX["thorax"]
        h36m_spine = H36M_IDX["spine"]
        expected_x = (out[0, h36m_hip, 0] + out[0, h36m_thorax, 0]) / 2
        expected_y = (out[0, h36m_hip, 1] + out[0, h36m_thorax, 1]) / 2
        assert out[0, h36m_spine, 0] == pytest.approx(expected_x)
        assert out[0, h36m_spine, 1] == pytest.approx(expected_y)

    def test_neck_nose_is_mean_of_thorax_and_nose(self):
        lm = self._make_simple()
        out = convert_mp33_to_h36m17(lm)
        h36m_thorax = H36M_IDX["thorax"]
        h36m_neck_nose = H36M_IDX["neck_nose"]
        thorax_x = out[0, h36m_thorax, 0]
        expected_x = (thorax_x + 0.50) / 2  # (thorax.x + nose.x) / 2
        expected_y = (out[0, h36m_thorax, 1] + 0.05) / 2
        assert out[0, h36m_neck_nose, 0] == pytest.approx(expected_x)
        assert out[0, h36m_neck_nose, 1] == pytest.approx(expected_y)

    def test_spine_x_is_0_5_when_symmetric(self):
        """좌우 대칭 입력 → Hip=(0.5,0.6), Thorax=(0.5,0.2) → Spine x=0.5."""
        lm = self._make_simple()
        out = convert_mp33_to_h36m17(lm)
        h36m_spine = H36M_IDX["spine"]
        assert out[0, h36m_spine, 0] == pytest.approx(0.5, abs=1e-6)


# ── h36m17_to_coco17_subset 테스트 ────────────────────────────────────────────


class TestH36mToCoco17Subset:
    """h36m17_to_coco17_subset 형상, limb joint 매핑, face NaN."""

    def test_output_shape(self):
        h36m_xyz = np.ones((10, 17, 3), dtype=float)
        out = h36m17_to_coco17_subset(h36m_xyz)
        assert out.shape == (10, 17, 4), f"예상 (10,17,4), 실제 {out.shape}"

    def test_limb_joints_not_nan(self):
        h36m_xyz = np.ones((3, 17, 3), dtype=float)
        out = h36m17_to_coco17_subset(h36m_xyz)
        # 12개 limb joint COCO 인덱스: 5~16
        for _, coco_idx in H36M_TO_COCO17_LIMB_PAIRS:
            assert not np.isnan(out[0, coco_idx, 0]), f"COCO {coco_idx} x가 NaN이어서는 안 됨"
            assert not np.isnan(out[0, coco_idx, 1]), f"COCO {coco_idx} y가 NaN이어서는 안 됨"
            assert not np.isnan(out[0, coco_idx, 2]), f"COCO {coco_idx} z가 NaN이어서는 안 됨"

    def test_face_joints_are_nan(self):
        h36m_xyz = np.ones((3, 17, 3), dtype=float)
        out = h36m17_to_coco17_subset(h36m_xyz)
        # COCO face joints: 0(nose), 1(l_eye), 2(r_eye), 3(l_ear), 4(r_ear)
        for coco_idx in range(5):
            assert np.isnan(out[0, coco_idx, 0]), f"face joint {coco_idx}는 NaN 이어야 함"

    def test_limb_uncertainty_is_zero(self):
        """MotionBERT 출력 limb joints: uncertainty_proxy = 0.0."""
        h36m_xyz = np.ones((2, 17, 3), dtype=float)
        out = h36m17_to_coco17_subset(h36m_xyz)
        for _, coco_idx in H36M_TO_COCO17_LIMB_PAIRS:
            assert out[0, coco_idx, 3] == 0.0, f"COCO {coco_idx} uncertainty가 0 이어야 함"

    def test_face_uncertainty_is_one(self):
        """미감지 face joints: uncertainty_proxy = 1.0."""
        h36m_xyz = np.ones((2, 17, 3), dtype=float)
        out = h36m17_to_coco17_subset(h36m_xyz)
        for coco_idx in range(5):
            assert out[0, coco_idx, 3] == 1.0, f"face joint {coco_idx} uncertainty가 1.0 이어야 함"

    def test_xyz_values_transferred_correctly(self):
        """H3.6M 값이 COCO 배열에 정확히 복사되는지 확인."""
        h36m_xyz = np.zeros((1, 17, 3), dtype=float)
        # H36M_IDX["l_shoulder"] = 11 → COCO 5
        h36m_l_sh_idx = H36M_IDX["l_shoulder"]  # 11
        h36m_xyz[0, h36m_l_sh_idx, :] = [0.1, 0.2, 0.3]

        out = h36m17_to_coco17_subset(h36m_xyz)
        coco_l_sh = 5  # left_shoulder in COCO-17
        assert out[0, coco_l_sh, 0] == pytest.approx(0.1)
        assert out[0, coco_l_sh, 1] == pytest.approx(0.2)
        assert out[0, coco_l_sh, 2] == pytest.approx(0.3)

    def test_pairs_count(self):
        """12개 limb joint 쌍이 정의되어 있어야 함."""
        assert len(H36M_TO_COCO17_LIMB_PAIRS) == 12


# ── NaN 전파 테스트 ───────────────────────────────────────────────────────────


class TestNanPropagation:
    """미감지 프레임 NaN 전파."""

    def test_nan_frame_stays_nan(self):
        """MP landmarks가 NaN인 프레임 → H36M 출력도 NaN."""
        lm = np.zeros((3, 33, 2), dtype=float)
        lm[1, :, :] = np.nan  # 1번 프레임 전체 NaN (미감지)

        out = convert_mp33_to_h36m17(lm)
        # 직접 대응 관절 확인 (r_hip = MP 24)
        h36m_r_hip = H36M_IDX["r_hip"]
        assert np.isnan(out[1, h36m_r_hip, 0]), "미감지 프레임 직접 관절은 NaN"
        # 정상 프레임 확인
        assert not np.isnan(out[0, h36m_r_hip, 0])
        assert not np.isnan(out[2, h36m_r_hip, 0])

    def test_h36m_nan_propagates_to_coco17(self):
        """H3.6M NaN → COCO-17 limb NaN."""
        h36m_xyz = np.ones((2, 17, 3), dtype=float)
        h36m_xyz[0, H36M_IDX["l_shoulder"], :] = np.nan

        out = h36m17_to_coco17_subset(h36m_xyz)
        assert np.isnan(out[0, 5, 0]), "h36m NaN → COCO left_shoulder NaN"
        assert not np.isnan(out[1, 5, 0]), "다른 프레임은 정상"


# ── 입력 검증 테스트 ──────────────────────────────────────────────────────────


class TestInputValidation:
    """잘못된 입력에 대한 ValueError 검증."""

    def test_wrong_num_landmarks(self):
        """33개가 아닌 landmark → ValueError."""
        lm = np.zeros((3, 20, 2))
        with pytest.raises(ValueError, match="33"):
            convert_mp33_to_h36m17(lm)

    def test_wrong_channel_count(self):
        """채널이 1개 → ValueError."""
        lm = np.zeros((3, 33, 1))
        with pytest.raises(ValueError):
            convert_mp33_to_h36m17(lm)

    def test_wrong_4d_input(self):
        """4차원 입력 → ValueError."""
        lm = np.zeros((2, 3, 33, 2))
        with pytest.raises(ValueError):
            convert_mp33_to_h36m17(lm)

    def test_h36m_wrong_joints(self):
        """H3.6M 관절 수가 17 아닐 때 → ValueError."""
        h36m = np.ones((3, 16, 3))
        with pytest.raises(ValueError, match="17"):
            h36m17_to_coco17_subset(h36m)

    def test_h36m_wrong_xyz_channels(self):
        """xyz 채널이 3 미만 → ValueError."""
        h36m = np.ones((3, 17, 2))
        with pytest.raises(ValueError):
            h36m17_to_coco17_subset(h36m)


# ── 라운드트립 테스트 ─────────────────────────────────────────────────────────


class TestRoundtrip:
    """MP33 → H36M17 → COCO17 연속 변환 정합성."""

    def test_roundtrip_limb_count(self):
        """변환 후 COCO-17 출력에 12개 limb joint가 non-NaN이어야 함."""
        lm = _make_mp_lm(T=5, C=2)
        h36m = convert_mp33_to_h36m17(lm)

        # h36m17_to_coco17_subset는 (T, 17, 3=xyz) 필요 — z 채널 추가
        z = np.zeros((5, 17, 1))
        h36m_xyz = np.concatenate([h36m, z], axis=2)

        coco = h36m17_to_coco17_subset(h36m_xyz)
        assert coco.shape == (5, 17, 4)

        # 12개 limb joint 모두 non-NaN 확인
        for _, coco_idx in H36M_TO_COCO17_LIMB_PAIRS:
            assert not np.any(np.isnan(coco[:, coco_idx, 0])), \
                f"COCO limb joint {coco_idx} NaN 발생"

    def test_roundtrip_values_preserved(self):
        """r_hip 값이 MP → H36M → COCO 라운드트립 후 보존되는지."""
        lm = np.zeros((1, 33, 2), dtype=float)
        lm[0, 24, 0] = 0.55  # r_hip x = MP 24
        lm[0, 24, 1] = 0.45  # r_hip y

        h36m = convert_mp33_to_h36m17(lm)
        # H36M r_hip(1) x, y 확인
        assert h36m[0, H36M_IDX["r_hip"], 0] == pytest.approx(0.55)
        assert h36m[0, H36M_IDX["r_hip"], 1] == pytest.approx(0.45)

        # h36m → coco17
        z = np.zeros((1, 17, 1))
        h36m_xyz = np.concatenate([h36m, z], axis=2)
        coco = h36m17_to_coco17_subset(h36m_xyz)

        # COCO right_hip = index 12
        coco_r_hip = 12
        assert coco[0, coco_r_hip, 0] == pytest.approx(0.55)
        assert coco[0, coco_r_hip, 1] == pytest.approx(0.45)


# ── confidence 채널 테스트 ────────────────────────────────────────────────────


class TestConfidenceChannel:
    """use_visibility_as_conf=True 시 3채널 출력 정확성."""

    def test_direct_joint_confidence_preserved(self):
        lm = np.zeros((1, 33, 3), dtype=float)
        lm[0, 24, 2] = 0.85  # r_hip visibility = 0.85

        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=True)
        h36m_r_hip = H36M_IDX["r_hip"]
        assert out[0, h36m_r_hip, 2] == pytest.approx(0.85)

    def test_thorax_confidence_is_min_of_shoulders(self):
        lm = np.zeros((1, 33, 3), dtype=float)
        lm[0, 11, 2] = 0.90  # l_shoulder visibility
        lm[0, 12, 2] = 0.70  # r_shoulder visibility

        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=True)
        h36m_thorax = H36M_IDX["thorax"]
        # thorax confidence = min(l_sh, r_sh)
        assert out[0, h36m_thorax, 2] == pytest.approx(0.70)

    def test_hip_confidence_is_min_of_hips(self):
        lm = np.zeros((1, 33, 3), dtype=float)
        lm[0, 23, 2] = 0.60  # l_hip
        lm[0, 24, 2] = 0.80  # r_hip

        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=True)
        h36m_hip = H36M_IDX["hip"]
        assert out[0, h36m_hip, 2] == pytest.approx(0.60)

    def test_no_conf_when_flag_false(self):
        lm = _make_mp_lm(T=2, C=3)
        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=False)
        assert out.shape[2] == 2, "use_visibility_as_conf=False → 2채널"
