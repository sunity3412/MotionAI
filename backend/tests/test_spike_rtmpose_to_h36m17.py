"""RTMPose COCO-17 → H3.6M 17 매핑 어댑터 단위 테스트 (Plan 01-10).

mmpose 의존 없이 mock RTMPose 출력으로 어댑터 검증.

테스트 범위:
  - 입력 형상 (T, 17, 2|3) / (17, 2|3) 단일 프레임 확장
  - 출력 형상 (T, 17, 2) / (T, 17, 3)
  - 직접 매핑 12 joint 정확성
  - 파생 5 joint (hip, thorax, spine, neck_nose, head) 좌표 계산
  - image_size 정규화 (pixel → [0, 1])
  - score_threshold NaN 처리 (low-confidence keypoint)
  - NaN 입력 전파 (미감지 프레임)
  - 잘못된 입력 형상 ValueError
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.research.spikes.rtmpose_to_h36m17 import (
    DEFAULT_SCORE_THRESHOLD,
    H36M_IDX,
    NUM_H36M_JOINTS,
    convert_rtmpose_coco17_to_h36m17,
)


# ── fixture ──────────────────────────────────────────────────────────────────


def _make_rtmpose_kp(T: int = 3, C: int = 3, seed: int = 42) -> np.ndarray:
    """재현 가능한 mock RTMPose COCO-17 출력 (T, 17, C).

    x ∈ [0, 640], y ∈ [0, 480] (pixel 좌표 가정), score ∈ [0.5, 1.0] (모두 신뢰).
    """
    rng = np.random.default_rng(seed)
    out = np.zeros((T, 17, C), dtype=float)
    out[:, :, 0] = rng.uniform(0.0, 640.0, size=(T, 17))   # x pixel
    out[:, :, 1] = rng.uniform(0.0, 480.0, size=(T, 17))   # y pixel
    if C >= 3:
        out[:, :, 2] = rng.uniform(0.5, 1.0, size=(T, 17))  # score
    return out


# ── 입출력 형상 ──────────────────────────────────────────────────────────────


class TestShape:
    def test_output_shape_default(self):
        kp = _make_rtmpose_kp(T=5, C=3)
        out = convert_rtmpose_coco17_to_h36m17(kp)
        assert out.shape == (5, 17, 2)

    def test_output_shape_with_conf(self):
        kp = _make_rtmpose_kp(T=4, C=3)
        out = convert_rtmpose_coco17_to_h36m17(kp, use_score_as_conf=True)
        assert out.shape == (4, 17, 3)

    def test_output_shape_no_score(self):
        kp = _make_rtmpose_kp(T=5, C=2)
        out = convert_rtmpose_coco17_to_h36m17(kp)
        assert out.shape == (5, 17, 2)

    def test_single_frame_expanded(self):
        kp = _make_rtmpose_kp(T=1, C=3).squeeze(0)  # (17, 3)
        assert kp.shape == (17, 3)
        out = convert_rtmpose_coco17_to_h36m17(kp)
        assert out.shape == (1, 17, 2)

    def test_num_joints_constant(self):
        assert NUM_H36M_JOINTS == 17

    def test_default_threshold_constant(self):
        # 0.3 (Plan 10 frontmatter T-2-3) — 변경 시 테스트도 함께 변경
        assert DEFAULT_SCORE_THRESHOLD == 0.3


# ── 직접 매핑 12 joint ───────────────────────────────────────────────────────


class TestDirectMapping:
    """COCO-17 → H3.6M 직접 매핑 12개 joint 좌표 정확성."""

    def _identity_kp(self, T: int = 1) -> np.ndarray:
        """COCO 인덱스를 좌표값으로 사용 — 매핑 정확성 검증 편의."""
        kp = np.zeros((T, 17, 3), dtype=float)
        for i in range(17):
            kp[:, i, 0] = float(i) * 10.0   # x = idx * 10
            kp[:, i, 1] = float(i) * 1.0    # y = idx * 1
            kp[:, i, 2] = 0.9               # high score (passes threshold)
        return kp

    def test_r_hip_from_coco_12(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_r_hip = H36M_IDX["r_hip"]  # 1
        assert out[0, h36m_r_hip, 0] == pytest.approx(12 * 10.0)
        assert out[0, h36m_r_hip, 1] == pytest.approx(12 * 1.0)

    def test_l_hip_from_coco_11(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_l_hip = H36M_IDX["l_hip"]  # 4
        assert out[0, h36m_l_hip, 0] == pytest.approx(11 * 10.0)

    def test_r_knee_from_coco_14(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_r_knee = H36M_IDX["r_knee"]  # 2
        assert out[0, h36m_r_knee, 0] == pytest.approx(14 * 10.0)

    def test_l_knee_from_coco_13(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_l_knee = H36M_IDX["l_knee"]
        assert out[0, h36m_l_knee, 0] == pytest.approx(13 * 10.0)

    def test_r_foot_from_coco_16(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_r_foot = H36M_IDX["r_foot"]
        assert out[0, h36m_r_foot, 0] == pytest.approx(16 * 10.0)  # right ankle

    def test_l_foot_from_coco_15(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_l_foot = H36M_IDX["l_foot"]
        assert out[0, h36m_l_foot, 0] == pytest.approx(15 * 10.0)  # left ankle

    def test_l_shoulder_from_coco_5(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_l_sh = H36M_IDX["l_shoulder"]
        assert out[0, h36m_l_sh, 0] == pytest.approx(5 * 10.0)

    def test_r_shoulder_from_coco_6(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_r_sh = H36M_IDX["r_shoulder"]
        assert out[0, h36m_r_sh, 0] == pytest.approx(6 * 10.0)

    def test_l_elbow_from_coco_7(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_l_el = H36M_IDX["l_elbow"]
        assert out[0, h36m_l_el, 0] == pytest.approx(7 * 10.0)

    def test_r_elbow_from_coco_8(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_r_el = H36M_IDX["r_elbow"]
        assert out[0, h36m_r_el, 0] == pytest.approx(8 * 10.0)

    def test_l_wrist_from_coco_9(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_l_wr = H36M_IDX["l_wrist"]
        assert out[0, h36m_l_wr, 0] == pytest.approx(9 * 10.0)

    def test_r_wrist_from_coco_10(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_r_wr = H36M_IDX["r_wrist"]
        assert out[0, h36m_r_wr, 0] == pytest.approx(10 * 10.0)

    def test_head_is_nose_proxy_coco_0(self):
        kp = self._identity_kp()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_head = H36M_IDX["head"]  # 10
        assert out[0, h36m_head, 0] == pytest.approx(0 * 10.0)
        assert out[0, h36m_head, 1] == pytest.approx(0 * 1.0)


# ── 파생 joint 5개 ───────────────────────────────────────────────────────────


class TestDerivedJoints:
    """hip, thorax, spine, neck_nose 파생 joint 좌표 계산 정확성."""

    def _make_simple(self) -> np.ndarray:
        """좌우 대칭 + nose 위로 — 파생 계산 검증 편의."""
        kp = np.zeros((1, 17, 3), dtype=float)
        kp[:, :, 2] = 0.9  # 모든 keypoint 높은 신뢰도
        # COCO 0 nose
        kp[0, 0, 0] = 0.50; kp[0, 0, 1] = 0.05
        # COCO 5 l_shoulder, 6 r_shoulder
        kp[0, 5, 0] = 0.35; kp[0, 5, 1] = 0.20
        kp[0, 6, 0] = 0.65; kp[0, 6, 1] = 0.20
        # COCO 11 l_hip, 12 r_hip
        kp[0, 11, 0] = 0.30; kp[0, 11, 1] = 0.60
        kp[0, 12, 0] = 0.70; kp[0, 12, 1] = 0.60
        return kp

    def test_hip_is_mean_of_hips(self):
        kp = self._make_simple()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_hip = H36M_IDX["hip"]
        assert out[0, h36m_hip, 0] == pytest.approx((0.30 + 0.70) / 2)
        assert out[0, h36m_hip, 1] == pytest.approx((0.60 + 0.60) / 2)

    def test_thorax_is_mean_of_shoulders(self):
        kp = self._make_simple()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_thorax = H36M_IDX["thorax"]
        assert out[0, h36m_thorax, 0] == pytest.approx((0.35 + 0.65) / 2)
        assert out[0, h36m_thorax, 1] == pytest.approx((0.20 + 0.20) / 2)

    def test_spine_is_mean_of_hip_and_thorax(self):
        kp = self._make_simple()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_hip = H36M_IDX["hip"]
        h36m_thorax = H36M_IDX["thorax"]
        h36m_spine = H36M_IDX["spine"]
        expected_x = (out[0, h36m_hip, 0] + out[0, h36m_thorax, 0]) / 2
        expected_y = (out[0, h36m_hip, 1] + out[0, h36m_thorax, 1]) / 2
        assert out[0, h36m_spine, 0] == pytest.approx(expected_x)
        assert out[0, h36m_spine, 1] == pytest.approx(expected_y)

    def test_neck_nose_is_mean_of_thorax_and_nose(self):
        kp = self._make_simple()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_thorax = H36M_IDX["thorax"]
        h36m_neck_nose = H36M_IDX["neck_nose"]
        expected_x = (out[0, h36m_thorax, 0] + 0.50) / 2
        expected_y = (out[0, h36m_thorax, 1] + 0.05) / 2
        assert out[0, h36m_neck_nose, 0] == pytest.approx(expected_x)
        assert out[0, h36m_neck_nose, 1] == pytest.approx(expected_y)

    def test_spine_x_is_0_5_when_symmetric(self):
        """좌우 대칭 입력 → Hip x = 0.5, Thorax x = 0.5 → Spine x = 0.5."""
        kp = self._make_simple()
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_spine = H36M_IDX["spine"]
        assert out[0, h36m_spine, 0] == pytest.approx(0.5, abs=1e-9)


# ── image_size 정규화 ────────────────────────────────────────────────────────


class TestImageSizeNormalization:
    """pixel 좌표 → [0, 1] 정규화."""

    def test_normalization_divides_x_by_width(self):
        kp = np.zeros((1, 17, 3), dtype=float)
        kp[:, :, 2] = 0.9
        kp[0, 5, 0] = 320.0  # l_shoulder x = 320 pixel
        kp[0, 5, 1] = 240.0
        out = convert_rtmpose_coco17_to_h36m17(kp, image_size=(640, 480))
        h36m_l_sh = H36M_IDX["l_shoulder"]
        assert out[0, h36m_l_sh, 0] == pytest.approx(320.0 / 640.0)
        assert out[0, h36m_l_sh, 1] == pytest.approx(240.0 / 480.0)

    def test_no_normalization_when_size_none(self):
        kp = np.zeros((1, 17, 3), dtype=float)
        kp[:, :, 2] = 0.9
        kp[0, 5, 0] = 0.42
        out = convert_rtmpose_coco17_to_h36m17(kp, image_size=None)
        h36m_l_sh = H36M_IDX["l_shoulder"]
        assert out[0, h36m_l_sh, 0] == pytest.approx(0.42)

    def test_zero_width_raises(self):
        kp = _make_rtmpose_kp(T=1, C=3)
        with pytest.raises(ValueError, match="양수"):
            convert_rtmpose_coco17_to_h36m17(kp, image_size=(0, 480))

    def test_negative_height_raises(self):
        kp = _make_rtmpose_kp(T=1, C=3)
        with pytest.raises(ValueError, match="양수"):
            convert_rtmpose_coco17_to_h36m17(kp, image_size=(640, -10))


# ── score_threshold NaN 처리 ─────────────────────────────────────────────────


class TestScoreThreshold:
    """RTMPose keypoint score < threshold → NaN 처리."""

    def test_low_score_keypoint_becomes_nan(self):
        kp = np.zeros((1, 17, 3), dtype=float)
        kp[:, :, 2] = 0.9
        # l_shoulder score 만 낮음
        kp[0, 5, 0] = 0.42; kp[0, 5, 1] = 0.30; kp[0, 5, 2] = 0.1
        out = convert_rtmpose_coco17_to_h36m17(kp, score_threshold=0.3)
        h36m_l_sh = H36M_IDX["l_shoulder"]
        assert np.isnan(out[0, h36m_l_sh, 0]), "low-score l_shoulder x should be NaN"
        assert np.isnan(out[0, h36m_l_sh, 1])

    def test_high_score_keypoint_preserved(self):
        kp = np.zeros((1, 17, 3), dtype=float)
        kp[:, :, 2] = 0.9
        kp[0, 5, 0] = 0.42; kp[0, 5, 1] = 0.30; kp[0, 5, 2] = 0.85
        out = convert_rtmpose_coco17_to_h36m17(kp, score_threshold=0.3)
        h36m_l_sh = H36M_IDX["l_shoulder"]
        assert out[0, h36m_l_sh, 0] == pytest.approx(0.42)

    def test_threshold_at_boundary_is_excluded(self):
        """score == threshold 이면 NaN 처리 (< threshold 기준)."""
        kp = np.zeros((1, 17, 3), dtype=float)
        kp[:, :, 2] = 0.9
        kp[0, 5, 2] = 0.3  # exactly threshold
        out = convert_rtmpose_coco17_to_h36m17(kp, score_threshold=0.3)
        h36m_l_sh = H36M_IDX["l_shoulder"]
        # 0.3 >= 0.3 → preserved (strict <)
        assert not np.isnan(out[0, h36m_l_sh, 0])

    def test_low_score_propagates_to_derived(self):
        """저신뢰 hip 양쪽 → 파생 hip 도 NaN."""
        kp = np.zeros((1, 17, 3), dtype=float)
        kp[:, :, 2] = 0.9
        # 양 hip 다 low score
        kp[0, 11, 2] = 0.1
        kp[0, 12, 2] = 0.1
        kp[0, 11, 0] = 0.3; kp[0, 11, 1] = 0.6
        kp[0, 12, 0] = 0.7; kp[0, 12, 1] = 0.6
        out = convert_rtmpose_coco17_to_h36m17(kp, score_threshold=0.3)
        h36m_hip = H36M_IDX["hip"]
        assert np.isnan(out[0, h36m_hip, 0]), "derived hip x = mean(NaN, NaN) → NaN"


# ── NaN 입력 전파 ────────────────────────────────────────────────────────────


class TestNanPropagation:
    def test_nan_frame_stays_nan(self):
        """RTMPose 미감지 프레임 (NaN) → H36M 출력 NaN."""
        kp = np.zeros((3, 17, 3), dtype=float)
        kp[:, :, 2] = 0.9
        # 1번 프레임 모든 keypoint NaN
        kp[1, :, :] = np.nan
        out = convert_rtmpose_coco17_to_h36m17(kp)
        h36m_r_hip = H36M_IDX["r_hip"]
        assert np.isnan(out[1, h36m_r_hip, 0])
        assert not np.isnan(out[0, h36m_r_hip, 0])
        assert not np.isnan(out[2, h36m_r_hip, 0])


# ── 입력 검증 ────────────────────────────────────────────────────────────────


class TestInputValidation:
    def test_wrong_num_keypoints(self):
        kp = np.zeros((3, 33, 2))  # MediaPipe-shaped (33) 입력
        with pytest.raises(ValueError, match="17"):
            convert_rtmpose_coco17_to_h36m17(kp)

    def test_too_few_channels(self):
        kp = np.zeros((3, 17, 1))
        with pytest.raises(ValueError):
            convert_rtmpose_coco17_to_h36m17(kp)

    def test_4d_input_rejected(self):
        kp = np.zeros((2, 3, 17, 3))
        with pytest.raises(ValueError):
            convert_rtmpose_coco17_to_h36m17(kp)
