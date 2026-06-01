"""spike_measurement_trace 단위 테스트 (Plan 01-16 T-2/T-3).

검증 (numpy-only, mmpose / torch / mediapipe import 0):
  - trace_angles_per_frame — frame_index 단일 vs hold_window 평균 disagreement
  - compute_lr_asymmetry — 4 LR pair 영상 평균 |L - R|
  - compute_hold_window_lr — frame_index 단일 vs window 평균 |L - R|
  - compute_cross_engine_disagreement — 두 (T, J) 행렬 frame-by-frame diff (T-3)
  - detect_lr_swap — 좌우 부호 반대 frame 비율 (T-3)
  - verdict_hypothesis — strong / weak / rejected / inconclusive (T-3)
  - aggregate_verdicts — 4 가설 + dominant + next_path_recommendation (T-3)

모든 stub angles fixture 는 (T, J=8) shape (skeleton.JOINT_KEYS 8 joint).
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.research.spikes import spike_measurement_trace as trace
from sunity_shared.analysis.skeleton import JOINT_KEYS


# ── 공통 fixture helper ───────────────────────────────────────────────────────


def _const_angles(T: int = 20, value: float = 90.0) -> np.ndarray:
    """(T, J=8) 전부 value 도 - baseline fixture."""
    return np.full((T, len(JOINT_KEYS)), value, dtype=float)


# ─────────────────────────────────────────────────────────────────────────────
# T-2: TestTraceAnglesPerFrame
# ─────────────────────────────────────────────────────────────────────────────


class TestTraceAnglesPerFrame:
    def test_all_constant_zero_disagreement(self) -> None:
        """전부 90도 → frame 단일 == window 평균 → disagreement = 0."""
        arr = _const_angles(T=20, value=90.0)
        out = trace.trace_angles_per_frame(arr, frame_index=10, hold_window=5)
        assert out["mean_disagreement_deg"] == pytest.approx(0.0)
        for k in JOINT_KEYS:
            assert out["frame_single"][k] == pytest.approx(90.0)
            assert out["frame_window_mean"][k] == pytest.approx(90.0)
            assert out["frame_vs_window_disagreement_per_joint"][k] == pytest.approx(0.0)
        assert out["window_indices"] == list(range(5, 16))

    def test_frame_spike_creates_disagreement(self) -> None:
        """frame_index 만 다른 값 → single ≠ window mean → disagreement > 0."""
        arr = _const_angles(T=20, value=90.0)
        # frame 10 의 모든 joint 를 0도로 — 다른 frame 은 90도
        arr[10, :] = 0.0
        out = trace.trace_angles_per_frame(arr, frame_index=10, hold_window=5)
        # window = frames 5..15 (11 frame). 그 중 frame 10 (0도) 만 다름.
        # window_mean = (10*90 + 0) / 11 ≈ 81.818. single = 0 → |0 - 81.818| ≈ 81.818
        assert out["mean_disagreement_deg"] is not None
        assert out["mean_disagreement_deg"] > 30.0

    def test_frame_index_out_of_range(self) -> None:
        arr = _const_angles(T=10)
        with pytest.raises(ValueError):
            trace.trace_angles_per_frame(arr, frame_index=10, hold_window=2)
        with pytest.raises(ValueError):
            trace.trace_angles_per_frame(arr, frame_index=-1, hold_window=2)

    def test_window_boundary_clipping(self) -> None:
        """frame_index = 0 / T-1 일 때 window 경계 clipping 정상."""
        arr = _const_angles(T=10, value=90.0)
        out_start = trace.trace_angles_per_frame(arr, frame_index=0, hold_window=5)
        assert out_start["window_indices"] == [0, 1, 2, 3, 4, 5]
        out_end = trace.trace_angles_per_frame(arr, frame_index=9, hold_window=5)
        assert out_end["window_indices"] == [4, 5, 6, 7, 8, 9]

    def test_nan_safe_window_mean(self) -> None:
        """NaN frame 포함 시 nanmean 동작."""
        arr = _const_angles(T=10, value=90.0)
        arr[3, :] = np.nan  # frame 3 전체 NaN
        out = trace.trace_angles_per_frame(arr, frame_index=5, hold_window=3)
        # frame 5 = 90, window 2..8 (7 frames) 중 frame 3 NaN — 나머지 6 frame 90
        # window_mean = nanmean ≈ 90
        assert out["mean_disagreement_deg"] == pytest.approx(0.0)
        for k in JOINT_KEYS:
            assert out["frame_window_mean"][k] == pytest.approx(90.0)


# ─────────────────────────────────────────────────────────────────────────────
# T-2: TestComputeLrAsymmetry
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeLrAsymmetry:
    def test_all_equal_zero_asymmetry(self) -> None:
        """전부 90도 → 모든 pair |L - R| = 0."""
        arr = _const_angles(T=15, value=90.0)
        out = trace.compute_lr_asymmetry(arr)
        for pair_name, mean in out["per_pair"].items():
            assert mean == pytest.approx(0.0), f"pair {pair_name} expected 0"
        assert out["overall_mean_abs_lr_deg"] == pytest.approx(0.0)

    def test_single_pair_asymmetry(self) -> None:
        """left_knee=180 / right_knee=90 → knee pair 90도, 나머지 pair 0."""
        arr = _const_angles(T=15, value=90.0)
        key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
        arr[:, key_to_idx["left_knee"]] = 180.0
        out = trace.compute_lr_asymmetry(arr)
        knee_pair = "left_knee_vs_right_knee"
        assert out["per_pair"][knee_pair] == pytest.approx(90.0)
        # 나머지 3 pair 는 0
        other_pairs = [p for p in out["per_pair"].keys() if p != knee_pair]
        for p in other_pairs:
            assert out["per_pair"][p] == pytest.approx(0.0)
        # overall = (90 + 0 + 0 + 0) / 4 = 22.5
        assert out["overall_mean_abs_lr_deg"] == pytest.approx(22.5)

    def test_per_frame_shape(self) -> None:
        """per_frame shape = (T, 4)."""
        arr = _const_angles(T=12, value=90.0)
        out = trace.compute_lr_asymmetry(arr)
        assert out["per_frame"].shape == (12, len(trace.LR_PAIRS))

    def test_nan_frame_nanmean(self) -> None:
        """일부 frame NaN — nanmean 으로 무시."""
        arr = _const_angles(T=10, value=90.0)
        key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
        # frame 3 의 left_knee 만 NaN
        arr[3, key_to_idx["left_knee"]] = np.nan
        out = trace.compute_lr_asymmetry(arr)
        # left_knee = NaN 한 frame 빼고 모두 90 → per_pair[knee] = 0 (NaN 무시)
        knee_pair = "left_knee_vs_right_knee"
        assert out["per_pair"][knee_pair] == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# T-2: TestComputeHoldWindowLr
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeHoldWindowLr:
    def test_single_vs_window_separation(self) -> None:
        """frame 단일 |L - R| 과 window 평균 |L - R| 분리 산출."""
        arr = _const_angles(T=20, value=90.0)
        key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
        # frame 10 의 left_knee 만 180 → frame 10 단일 |L-R| = 90, 다른 frame 0
        arr[10, key_to_idx["left_knee"]] = 180.0
        out = trace.compute_hold_window_lr(arr, frame_index=10, hold_window=5)
        knee_pair = "left_knee_vs_right_knee"
        # 단일 frame 10 = |180 - 90| = 90
        assert out["frame_single_lr"][knee_pair] == pytest.approx(90.0)
        # window mean = 11 frame 중 frame 10 만 90, 나머지 10 frame 0 → 90/11
        assert out["frame_window_mean_lr"][knee_pair] == pytest.approx(90.0 / 11.0)

    def test_keys_match_lr_pairs(self) -> None:
        """출력 키가 4 LR pair 와 일치."""
        arr = _const_angles(T=10)
        out = trace.compute_hold_window_lr(arr, frame_index=5, hold_window=2)
        expected_keys = {f"{lk}_vs_{rk}" for lk, rk in trace.LR_PAIRS}
        assert set(out["frame_single_lr"].keys()) == expected_keys
        assert set(out["frame_window_mean_lr"].keys()) == expected_keys

    def test_boundary_frame(self) -> None:
        """frame_index = T-1 일 때 window 가 우측 clipping."""
        arr = _const_angles(T=10, value=90.0)
        # 정상 동작 보장 — exception 없이
        out = trace.compute_hold_window_lr(arr, frame_index=9, hold_window=5)
        for pair_name, v in out["frame_single_lr"].items():
            assert v == pytest.approx(0.0)
        for pair_name, v in out["frame_window_mean_lr"].items():
            assert v == pytest.approx(0.0)
