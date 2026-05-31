"""MediaPipe 33 → H3.6M 17 매핑 어댑터 단위 테스트 (production 경로).

Plan 01-08 — pose_lifters 패키지의 새 import 경로로 이전.
mediapipe 없이 실행 가능. 순수 numpy.

원본: backend/tests/test_spike_mediapipe_to_h36m17.py (Plan 01-07 spike 경로)
승격: backend/shared/python/sunity_shared/analysis/pose_lifters/mediapipe_to_h36m17

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

from sunity_shared.analysis.pose_lifters.mediapipe_to_h36m17 import (
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
        """각 MediaPipe 관절이 고유한 좌표값을 갖도록 생성 (인덱스 × 0.01)."""
        arr = np.zeros((T, 33, 2), dtype=float)
        for i in range(33):
            arr[:, i, 0] = i * 0.01       # x = index × 0.01
            arr[:, i, 1] = (i + 0.5) * 0.01  # y = (index+0.5) × 0.01
        return arr

    def test_r_hip_mapping(self):
        """MP 24 (right hip) → H36M 1 (r_hip)."""
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_idx = H36M_IDX["r_hip"]  # 1
        assert out[0, h36m_idx, 0] == pytest.approx(24 * 0.01)
        assert out[0, h36m_idx, 1] == pytest.approx(24.5 * 0.01)

    def test_l_hip_mapping(self):
        """MP 23 (left hip) → H36M 4 (l_hip)."""
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_idx = H36M_IDX["l_hip"]  # 4
        assert out[0, h36m_idx, 0] == pytest.approx(23 * 0.01)

    def test_l_shoulder_mapping(self):
        """MP 11 (left shoulder) → H36M 11 (l_shoulder)."""
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_idx = H36M_IDX["l_shoulder"]  # 11
        assert out[0, h36m_idx, 0] == pytest.approx(11 * 0.01)

    def test_r_shoulder_mapping(self):
        """MP 12 (right shoulder) → H36M 14 (r_shoulder)."""
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_idx = H36M_IDX["r_shoulder"]  # 14
        assert out[0, h36m_idx, 0] == pytest.approx(12 * 0.01)

    def test_head_mapping(self):
        """MP 0 (nose) → H36M 10 (head/nose proxy)."""
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_idx = H36M_IDX["head"]  # 10
        assert out[0, h36m_idx, 0] == pytest.approx(0 * 0.01)  # MP 0의 x = 0

    def test_r_wrist_mapping(self):
        """MP 16 (right wrist) → H36M 16 (r_wrist)."""
        lm = self._mp_lm_identity()
        out = convert_mp33_to_h36m17(lm)
        h36m_idx = H36M_IDX["r_wrist"]  # 16
        assert out[0, h36m_idx, 0] == pytest.approx(16 * 0.01)

    def test_all_direct_joints_not_nan(self):
        """직접 대응 관절 13개 모두 NaN 없음."""
        lm = _make_mp_lm(T=2, C=2)
        out = convert_mp33_to_h36m17(lm)
        direct_joints = [
            "r_hip", "r_knee", "r_foot", "l_hip", "l_knee", "l_foot",
            "head", "l_shoulder", "l_elbow", "l_wrist",
            "r_shoulder", "r_elbow", "r_wrist",
        ]
        for name in direct_joints:
            idx = H36M_IDX[name]
            assert not np.any(np.isnan(out[:, idx, :])), f"{name} 에 NaN 있음"


# ── 파생 관절 테스트 ──────────────────────────────────────────────────────────


class TestDerivedJoints:
    """파생 관절 (hip, thorax, spine, neck_nose) 좌표 계산 정확성."""

    def _uniform_lm(self, T: int = 1) -> np.ndarray:
        """모든 관절 좌표가 (0.5, 0.5)인 landmark 배열."""
        arr = np.full((T, 33, 2), 0.5, dtype=float)
        return arr

    def test_thorax_is_mean_of_shoulders(self):
        """H36M 8 Thorax = mean(MP 11, MP 12) = 0.5 (균등 입력)."""
        lm = self._uniform_lm()
        out = convert_mp33_to_h36m17(lm)
        thorax_idx = H36M_IDX["thorax"]  # 8
        assert out[0, thorax_idx, 0] == pytest.approx(0.5)
        assert out[0, thorax_idx, 1] == pytest.approx(0.5)

    def test_thorax_specific_values(self):
        """Thorax = mean(left_shoulder, right_shoulder) 정확성."""
        lm = np.zeros((1, 33, 2), dtype=float)
        lm[0, 11, 0] = 0.2   # l_shoulder x
        lm[0, 12, 0] = 0.4   # r_shoulder x
        lm[0, 11, 1] = 0.3   # l_shoulder y
        lm[0, 12, 1] = 0.5   # r_shoulder y
        out = convert_mp33_to_h36m17(lm)
        thorax_idx = H36M_IDX["thorax"]
        assert out[0, thorax_idx, 0] == pytest.approx(0.3)   # (0.2+0.4)/2
        assert out[0, thorax_idx, 1] == pytest.approx(0.4)   # (0.3+0.5)/2

    def test_hip_is_mean_of_hips(self):
        """H36M 0 Hip = mean(MP 23, MP 24) 정확성."""
        lm = np.zeros((1, 33, 2), dtype=float)
        lm[0, 23, 0] = 0.3   # l_hip x
        lm[0, 24, 0] = 0.7   # r_hip x
        out = convert_mp33_to_h36m17(lm)
        hip_idx = H36M_IDX["hip"]  # 0
        assert out[0, hip_idx, 0] == pytest.approx(0.5)  # (0.3+0.7)/2

    def test_spine_is_mean_of_hip_and_thorax(self):
        """H36M 7 Spine = mean(Hip, Thorax) 정확성."""
        lm = np.zeros((1, 33, 2), dtype=float)
        # l_hip=0.2, r_hip=0.2 → hip=0.2
        lm[0, 23, 0] = 0.2
        lm[0, 24, 0] = 0.2
        # l_shoulder=0.6, r_shoulder=0.6 → thorax=0.6
        lm[0, 11, 0] = 0.6
        lm[0, 12, 0] = 0.6
        out = convert_mp33_to_h36m17(lm)
        spine_idx = H36M_IDX["spine"]
        assert out[0, spine_idx, 0] == pytest.approx(0.4)  # (0.2+0.6)/2

    def test_neck_nose_is_mean_of_thorax_and_nose(self):
        """H36M 9 NeckNose = mean(Thorax, Nose) 정확성."""
        lm = np.zeros((1, 33, 2), dtype=float)
        # shoulders 동일값 → thorax = 0.4
        lm[0, 11, 0] = 0.4
        lm[0, 12, 0] = 0.4
        # nose = 0.0
        lm[0, 0, 0] = 0.0
        out = convert_mp33_to_h36m17(lm)
        neck_nose_idx = H36M_IDX["neck_nose"]
        assert out[0, neck_nose_idx, 0] == pytest.approx(0.2)  # (0.4+0.0)/2


# ── h36m17_to_coco17_subset 테스트 ───────────────────────────────────────────


class TestH36mToCoco17Subset:
    """h36m17_to_coco17_subset 형상 + 매핑 + NaN 검증."""

    def _make_h36m_xyz(self, T: int = 3) -> np.ndarray:
        """재현 가능한 H36M (T, 17, 3) 배열."""
        rng = np.random.default_rng(7)
        return rng.uniform(-1.0, 1.0, size=(T, 17, 3))

    def test_output_shape(self):
        """(3, 17, 3) → (3, 17, 4)."""
        h36m = self._make_h36m_xyz(T=3)
        out = h36m17_to_coco17_subset(h36m)
        assert out.shape == (3, 17, 4), f"예상 (3,17,4), 실제 {out.shape}"

    def test_limb_joints_not_nan(self):
        """12개 limb joints (COCO-17 인덱스 5~16) 는 NaN 없음."""
        h36m = self._make_h36m_xyz()
        out = h36m17_to_coco17_subset(h36m)
        limb_coco_indices = [p[1] for p in H36M_TO_COCO17_LIMB_PAIRS]
        for coco_idx in limb_coco_indices:
            assert not np.any(np.isnan(out[:, coco_idx, :3])), \
                f"COCO-17 인덱스 {coco_idx}에 NaN 있음"

    def test_face_joints_are_nan(self):
        """face joints (COCO-17 인덱스 0~4) 는 xyz NaN."""
        h36m = self._make_h36m_xyz()
        out = h36m17_to_coco17_subset(h36m)
        for face_idx in range(5):  # nose, l_eye, r_eye, l_ear, r_ear
            assert np.all(np.isnan(out[:, face_idx, :3])), \
                f"face joint COCO-17[{face_idx}] xyz가 NaN이어야 함"

    def test_face_uncertainty_is_1(self):
        """face joints uncertainty_proxy = 1.0."""
        h36m = self._make_h36m_xyz()
        out = h36m17_to_coco17_subset(h36m)
        for face_idx in range(5):
            assert np.all(out[:, face_idx, 3] == 1.0), \
                f"face joint COCO-17[{face_idx}] uncertainty_proxy != 1.0"

    def test_limb_uncertainty_is_0(self):
        """limb joints uncertainty_proxy = 0.0."""
        h36m = self._make_h36m_xyz()
        out = h36m17_to_coco17_subset(h36m)
        limb_coco_indices = [p[1] for p in H36M_TO_COCO17_LIMB_PAIRS]
        for coco_idx in limb_coco_indices:
            assert np.all(out[:, coco_idx, 3] == 0.0), \
                f"COCO-17 [{coco_idx}] uncertainty_proxy != 0.0"

    def test_wrong_shape_raises(self):
        """잘못된 형상 ValueError."""
        with pytest.raises(ValueError):
            h36m17_to_coco17_subset(np.zeros((3, 16, 3)))

    def test_wrong_channels_raises(self):
        with pytest.raises(ValueError):
            h36m17_to_coco17_subset(np.zeros((3, 17, 2)))


# ── NaN 전파 테스트 ───────────────────────────────────────────────────────────


class TestNanPropagation:
    """미감지 프레임 NaN 전파."""

    def test_nan_frame_propagates(self):
        """모든 값이 NaN인 프레임 → 해당 프레임 출력도 NaN."""
        lm = np.zeros((3, 33, 2), dtype=float)
        lm[1, :, :] = np.nan  # 프레임 1을 NaN으로
        out = convert_mp33_to_h36m17(lm)
        # 프레임 1의 직접 대응 관절은 NaN이어야 함
        assert np.all(np.isnan(out[1, H36M_IDX["r_hip"], :]))

    def test_non_nan_frames_not_affected(self):
        """NaN 프레임이 다른 프레임에 영향 없음."""
        lm = _make_mp_lm(T=3, C=2, seed=1)
        lm[1, :, :] = np.nan  # 프레임 1만 NaN
        out = convert_mp33_to_h36m17(lm)
        # 프레임 0, 2는 NaN 없음 (직접 대응 관절 기준)
        assert not np.any(np.isnan(out[0, H36M_IDX["r_hip"], :]))
        assert not np.any(np.isnan(out[2, H36M_IDX["r_hip"], :]))


# ── 입력 검증 테스트 ──────────────────────────────────────────────────────────


class TestInputValidation:
    """잘못된 입력 → ValueError."""

    def test_wrong_joint_count(self):
        with pytest.raises(ValueError, match="33"):
            convert_mp33_to_h36m17(np.zeros((5, 32, 2)))

    def test_too_few_channels(self):
        with pytest.raises(ValueError):
            convert_mp33_to_h36m17(np.zeros((5, 33, 1)))

    def test_4d_input(self):
        with pytest.raises(ValueError):
            convert_mp33_to_h36m17(np.zeros((2, 5, 33, 2)))

    def test_1d_input(self):
        with pytest.raises(ValueError):
            convert_mp33_to_h36m17(np.zeros(33))

    def test_correct_shapes_do_not_raise(self):
        """올바른 입력 형상은 에러 없음."""
        convert_mp33_to_h36m17(np.zeros((5, 33, 2)))
        convert_mp33_to_h36m17(np.zeros((5, 33, 3)))
        convert_mp33_to_h36m17(np.zeros((33, 2)))


# ── 라운드트립 테스트 ─────────────────────────────────────────────────────────


class TestRoundtrip:
    """MP33 → H36M17 → COCO17 연속 변환 정확성."""

    def test_roundtrip_shape(self):
        """MP33 → H36M17 → COCO17: 최종 shape (T, 17, 4)."""
        lm = _make_mp_lm(T=5, C=2)
        h36m = convert_mp33_to_h36m17(lm)  # (5, 17, 2)
        # h36m17_to_coco17_subset 은 (T, 17, 3) 입력 필요
        h36m_3d = np.concatenate([h36m, np.zeros((5, 17, 1))], axis=2)
        coco = h36m17_to_coco17_subset(h36m_3d)
        assert coco.shape == (5, 17, 4)

    def test_limb_coords_preserved(self):
        """라운드트립 후 limb joint xy 좌표가 원본과 일치."""
        lm = _make_mp_lm(T=2, C=2, seed=99)
        h36m = convert_mp33_to_h36m17(lm)
        h36m_3d = np.concatenate([h36m, np.zeros((2, 17, 1))], axis=2)
        coco = h36m17_to_coco17_subset(h36m_3d)

        # l_shoulder: H36M 11 → COCO 5
        h36m_l_shoulder_x = h36m[:, 11, 0]
        coco_l_shoulder_x = coco[:, 5, 0]
        np.testing.assert_allclose(coco_l_shoulder_x, h36m_l_shoulder_x, rtol=1e-5)


# ── confidence 채널 테스트 ────────────────────────────────────────────────────


class TestConfidenceChannel:
    """visibility confidence 채널 정확성 (use_visibility_as_conf=True)."""

    def test_confidence_channel_present(self):
        """use_visibility_as_conf=True → 출력 채널 수 = 3."""
        lm = _make_mp_lm(T=3, C=3)
        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=True)
        assert out.shape[2] == 3

    def test_confidence_matches_mp_visibility(self):
        """직접 대응 관절의 confidence == MP landmark의 visibility (세 번째 채널)."""
        lm = np.zeros((1, 33, 3), dtype=float)
        lm[0, :, 2] = np.linspace(0.1, 0.9, 33)  # visibility 값 지정
        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=True)
        # MP 24 (r_hip) → H36M 1 (r_hip): visibility = lm[0, 24, 2]
        r_hip_idx = H36M_IDX["r_hip"]
        assert out[0, r_hip_idx, 2] == pytest.approx(lm[0, 24, 2])

    def test_derived_joint_confidence_is_minimum(self):
        """파생 관절 confidence = 구성 관절 visibility 최솟값."""
        lm = np.zeros((1, 33, 3), dtype=float)
        lm[0, 11, 2] = 0.8  # l_shoulder visibility
        lm[0, 12, 2] = 0.6  # r_shoulder visibility
        out = convert_mp33_to_h36m17(lm, use_visibility_as_conf=True)
        thorax_idx = H36M_IDX["thorax"]
        # Thorax confidence = min(0.8, 0.6) = 0.6
        assert out[0, thorax_idx, 2] == pytest.approx(0.6)

    def test_no_conf_flag_gives_2_channels(self):
        """use_visibility_as_conf=False (기본값) → 채널 수 = 2."""
        lm = _make_mp_lm(T=3, C=3)
        out = convert_mp33_to_h36m17(lm)  # 기본값 False
        assert out.shape[2] == 2
