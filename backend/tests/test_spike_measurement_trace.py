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


# ─────────────────────────────────────────────────────────────────────────────
# T-3: TestComputeCrossEngineDisagreement
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeCrossEngineDisagreement:
    def test_identical_zero_disagreement(self) -> None:
        """동일 matrix → disagreement 0."""
        arr = _const_angles(T=15, value=90.0)
        out = trace.compute_cross_engine_disagreement(arr, arr)
        assert out["overall_mean_disagreement_deg"] == pytest.approx(0.0)
        for k in JOINT_KEYS:
            assert out["per_joint_mean_disagreement"][k] == pytest.approx(0.0)

    def test_uniform_offset_30deg(self) -> None:
        """rtmpose 모두 60, mp 모두 90 → joint별 평균 30도."""
        a = _const_angles(T=15, value=60.0)
        b = _const_angles(T=15, value=90.0)
        out = trace.compute_cross_engine_disagreement(a, b)
        assert out["overall_mean_disagreement_deg"] == pytest.approx(30.0)

    def test_nan_frame_nanmean(self) -> None:
        """일부 frame NaN — nanmean 으로 무시."""
        a = _const_angles(T=10, value=90.0)
        b = _const_angles(T=10, value=90.0)
        b[3, :] = np.nan
        out = trace.compute_cross_engine_disagreement(a, b)
        # frame 3 전체 NaN → per_frame[3] = nan, 나머지 0
        # overall = nanmean = 0
        assert out["overall_mean_disagreement_deg"] == pytest.approx(0.0)

    def test_different_T_truncates(self) -> None:
        """T 다르면 짧은 쪽 truncate."""
        a = _const_angles(T=12, value=90.0)
        b = _const_angles(T=20, value=120.0)
        out = trace.compute_cross_engine_disagreement(a, b)
        assert out["frame_count"] == 12


# ─────────────────────────────────────────────────────────────────────────────
# T-3: TestDetectLrSwap
# ─────────────────────────────────────────────────────────────────────────────


class TestDetectLrSwap:
    def test_same_sign_no_swap(self) -> None:
        """두 path 부호 동일 → swap 0."""
        arr = _const_angles(T=10, value=90.0)
        key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
        # 양 쪽 다 left_knee > right_knee
        a = arr.copy()
        a[:, key_to_idx["left_knee"]] = 180.0
        b = arr.copy()
        b[:, key_to_idx["left_knee"]] = 150.0  # 여전히 > 90 = right
        out = trace.detect_lr_swap(a, b)
        assert out["swap_frame_ratio"] == pytest.approx(0.0)

    def test_opposite_sign_50pct(self) -> None:
        """frame 절반은 swap (부호 반대), 절반은 동일 → ratio = 0.5."""
        T = 10
        a = _const_angles(T=T, value=90.0)
        b = _const_angles(T=T, value=90.0)
        key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
        # a: 전체 left_knee = 180 (L > R)
        a[:, key_to_idx["left_knee"]] = 180.0
        # b: 절반은 left_knee = 0 (L < R, swap), 절반은 left_knee = 180 (L > R, no swap)
        b[:5, key_to_idx["left_knee"]] = 0.0
        b[5:, key_to_idx["left_knee"]] = 180.0
        out = trace.detect_lr_swap(a, b)
        knee_pair = "left_knee_vs_right_knee"
        # frames 0..4 swap, 5..9 no swap → ratio = 5/10 = 0.5
        assert out["swap_frame_ratio_per_pair"][knee_pair] == pytest.approx(0.5)
        # 다른 3 pair 는 0 → overall = (0.5 + 0 + 0 + 0) / 4 = 0.125
        assert out["swap_frame_ratio"] == pytest.approx(0.5 / 4)

    def test_pair_isolation(self) -> None:
        """각 pair 가 독립적으로 swap 카운트."""
        T = 10
        a = _const_angles(T=T, value=90.0)
        b = _const_angles(T=T, value=90.0)
        key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
        # left_knee/right_knee swap (a: L > R, b: L < R) all frames
        a[:, key_to_idx["left_knee"]] = 180.0
        b[:, key_to_idx["left_knee"]] = 0.0
        out = trace.detect_lr_swap(a, b)
        knee_pair = "left_knee_vs_right_knee"
        assert out["swap_frame_ratio_per_pair"][knee_pair] == pytest.approx(1.0)
        other_pairs = [
            p for p in out["swap_frame_ratio_per_pair"] if p != knee_pair
        ]
        for p in other_pairs:
            assert out["swap_frame_ratio_per_pair"][p] == pytest.approx(0.0)

    def test_nan_frames_excluded(self) -> None:
        """NaN frame 은 valid 에서 제외."""
        T = 10
        a = _const_angles(T=T, value=90.0)
        b = _const_angles(T=T, value=90.0)
        key_to_idx = {k: j for j, k in enumerate(JOINT_KEYS)}
        # 모든 left_knee swap, 그러나 frame 3 의 left_knee 둘 다 NaN
        a[:, key_to_idx["left_knee"]] = 180.0
        b[:, key_to_idx["left_knee"]] = 0.0
        a[3, key_to_idx["left_knee"]] = np.nan
        b[3, key_to_idx["left_knee"]] = np.nan
        out = trace.detect_lr_swap(a, b)
        knee_pair = "left_knee_vs_right_knee"
        # 9 valid frame 모두 swap → ratio = 9/9 = 1.0
        assert out["swap_frame_ratio_per_pair"][knee_pair] == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# T-3: TestVerdictHypothesis
# ─────────────────────────────────────────────────────────────────────────────


class TestVerdictHypothesis:
    def test_strong(self) -> None:
        assert trace.verdict_hypothesis(35.0, 30.0, 10.0) == "strong"
        assert trace.verdict_hypothesis(30.0, 30.0, 10.0) == "strong"

    def test_weak(self) -> None:
        assert trace.verdict_hypothesis(20.0, 30.0, 10.0) == "weak"
        assert trace.verdict_hypothesis(10.0, 30.0, 10.0) == "weak"

    def test_rejected(self) -> None:
        assert trace.verdict_hypothesis(5.0, 30.0, 10.0) == "rejected"
        assert trace.verdict_hypothesis(0.0, 30.0, 10.0) == "rejected"

    def test_inconclusive_on_none_or_nan(self) -> None:
        assert trace.verdict_hypothesis(None, 30.0, 10.0) == "inconclusive"
        assert trace.verdict_hypothesis(float("nan"), 30.0, 10.0) == "inconclusive"


# ─────────────────────────────────────────────────────────────────────────────
# T-3: TestAggregateVerdicts (6 분기 — multi-view 키워드 0건)
# ─────────────────────────────────────────────────────────────────────────────


def _make_traces(
    a_value: float | None,
    b_value: float | None,
    c_value: float | None,
    d_value: float | None,
) -> tuple[dict, dict, dict, dict]:
    """4 가설 trace 결과 stub."""
    return (
        {"mean_disagreement_deg": a_value},
        {"overall_mean_abs_lr_deg": b_value},
        {"swap_frame_ratio": c_value},
        {"overall_mean_disagreement_deg": d_value},
    )


class TestAggregateVerdicts:
    def test_dominant_a_only(self) -> None:
        ta, tb, tc, td = _make_traces(35.0, 5.0, 0.05, 5.0)
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert out["dominant"] == ["a"]
        assert "path D 조기 진입" in out["next_path_recommendation"]
        # multi-view 키워드 0건
        assert "multi-view" not in out["next_path_recommendation"]
        assert "다각도" not in out["next_path_recommendation"]
        assert "multi camera" not in out["next_path_recommendation"]

    def test_dominant_b_only(self) -> None:
        ta, tb, tc, td = _make_traces(5.0, 50.0, 0.05, 5.0)
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert out["dominant"] == ["b"]
        assert "path B" in out["next_path_recommendation"]
        assert "multi-view" not in out["next_path_recommendation"]
        assert "다각도" not in out["next_path_recommendation"]

    def test_dominant_c_only(self) -> None:
        ta, tb, tc, td = _make_traces(5.0, 5.0, 0.5, 5.0)
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert out["dominant"] == ["c"]
        assert "좌우 매핑" in out["next_path_recommendation"]
        assert "multi-view" not in out["next_path_recommendation"]
        assert "다각도" not in out["next_path_recommendation"]

    def test_dominant_d_only(self) -> None:
        ta, tb, tc, td = _make_traces(5.0, 5.0, 0.05, 35.0)
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert out["dominant"] == ["d"]
        assert "path B" in out["next_path_recommendation"]
        assert "강제" in out["next_path_recommendation"]
        assert "multi-view" not in out["next_path_recommendation"]
        assert "다각도" not in out["next_path_recommendation"]

    def test_dominant_a_and_b(self) -> None:
        ta, tb, tc, td = _make_traces(35.0, 50.0, 0.05, 5.0)
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert set(out["dominant"]) == {"a", "b"}
        assert "path B + path D combined" in out["next_path_recommendation"]
        assert "multi-view" not in out["next_path_recommendation"]
        assert "다각도" not in out["next_path_recommendation"]

    def test_all_rejected(self) -> None:
        ta, tb, tc, td = _make_traces(5.0, 5.0, 0.05, 5.0)
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert out["dominant"] == []
        assert "path D 정식 진입" in out["next_path_recommendation"]
        assert "multi-view" not in out["next_path_recommendation"]
        assert "다각도" not in out["next_path_recommendation"]
