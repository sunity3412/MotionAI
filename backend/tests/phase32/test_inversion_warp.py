"""32-15 Task 1 — PR 인버전 보정: 검출 휴리스틱 + 호모그래피 round-trip (D-22).

검증 대상: sunity_shared/analysis/inversion_warp.py (순수 numpy 부분만 — 로컬).
GPU 프레임 워프 실행(warp_frames)은 Pod 제한 통합 게이트(Task 2)가 커버.

Behavior (32-15-PLAN Task 1):
  1. 검출(합성): 엉덩이 y < 어깨 y 지속 구간 → True. 정립 → False.
     순간 역전(점프 프레임)만으로는 False (지속성 요구 — 고속 스핀 오검출 방지).
  2. 검출(spike 실데이터): kpts/ .npz — invert 계열 True (TP ≥ 2), 비인버전 False (FP 0).
  3. round-trip: warp_points(H) → unwarp_points(H) → 원좌표 복원 (eps ≤ 1e-6).
  4. fail-safe: 역변환 비유한/범위 대탈출 프레임 → 1차 좌표 유지 표식 (ok=False).
  5. 순수성: detect·호모그래피 경로에 torch import 0 (numpy만).

spike 실데이터 근거 (.planning/spikes/004 — 2026-07-22 로컬 재계측, margin 0.3 기준):
  invert ratio 0.289/run 18 · straddle-invert 0.300/20 · elbow-twist-sister 1.000/9 (TP)
  power-spin 0.042/2 · sideway-spin 0.025/1 · 나머지 0.000/0 (FP 후보 전부 임계 미달)
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

from sunity_shared.analysis import inversion_warp as iw

# spike 실측 keypoint 시퀀스 (.npz — kpts[T,133,2] / scores[T,133] / ts[T]).
# CI/타 환경에 spike 산출물이 없으면 해당 테스트 skip (플랜 명시 — 경로 안전).
_REPO = Path(__file__).resolve().parents[3]
_SPIKE_KPTS = _REPO / ".planning" / "spikes" / "004-gemini-omni-view-editing" / "kpts"

# COCO body 인덱스 (RTMW 133 의 선두 17 = COCO-17 순서)
_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP = 5, 6, 11, 12


def _make_seq(
    n_frames: int,
    inverted_mask: list[bool],
    torso_px: float = 200.0,
) -> tuple[np.ndarray, np.ndarray]:
    """합성 (T,17,2) keypoint + (T,17) score 시퀀스.

    정립 프레임: 어깨 y=400, 엉덩이 y=600 (이미지 좌표 — 아래로 증가).
    역전 프레임: 어깨 y=600, 엉덩이 y=400 (엉덩이가 어깨 위 — torso 1.0배 마진).
    """
    kpts = np.zeros((n_frames, 17, 2), dtype=np.float32)
    scores = np.full((n_frames, 17), 0.9, dtype=np.float32)
    for t in range(n_frames):
        sh_y, hip_y = (600.0, 400.0) if inverted_mask[t] else (400.0, 600.0)
        kpts[t, :, 0] = 360.0  # x 는 검출과 무관 — 중앙 고정
        kpts[t, :, 1] = 500.0
        kpts[t, [_L_SHOULDER, _R_SHOULDER], 1] = sh_y
        kpts[t, [_L_HIP, _R_HIP], 1] = hip_y
    assert torso_px == 200.0  # 마진 = torso 1.0배 — INVERSION_MARGIN(0.3) 여유 통과
    return kpts, scores


class TestDetectSynthetic:
    """Behavior 1 — 합성 시퀀스 검출."""

    def test_upright_sequence_is_false(self):
        kpts, scores = _make_seq(60, [False] * 60)
        det = iw.detect_inversion(kpts, scores)
        assert det.is_inverted is False

    def test_sustained_inversion_is_true(self):
        # 60프레임 중 24프레임(40%) 연속 역전 — ratio·run 둘 다 임계 초과
        mask = [False] * 18 + [True] * 24 + [False] * 18
        kpts, scores = _make_seq(60, mask)
        det = iw.detect_inversion(kpts, scores)
        assert det.is_inverted is True
        assert det.longest_run_frames >= iw.INVERSION_MIN_RUN

    def test_brief_flickers_are_false(self):
        # 순간 역전(1프레임)이 흩어져 ratio 는 임계(0.15)를 넘지만 run=1 —
        # 지속성 요구가 고속 스핀류 오검출을 막는지 검증 (플랜 behavior 1).
        mask = [False] * 60
        for t in range(0, 60, 5):  # 12/60 = 0.20 ≥ INVERSION_RATIO
            mask[t] = True
        kpts, scores = _make_seq(60, mask)
        det = iw.detect_inversion(kpts, scores)
        assert det.inverted_ratio >= iw.INVERSION_RATIO  # 전제 확인 (ratio 만으론 통과)
        assert det.is_inverted is False  # run < INVERSION_MIN_RUN → 미검출

    def test_low_confidence_frames_excluded(self):
        # 어깨·엉덩이 저신뢰 프레임은 판정 모수에서 제외 — 전 프레임 저신뢰면 False
        kpts, scores = _make_seq(30, [True] * 30)
        scores[:, [_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP]] = 0.1
        det = iw.detect_inversion(kpts, scores)
        assert det.is_inverted is False
        assert det.valid_frames == 0


class TestDetectSpikeRealData:
    """Behavior 2 — spike 실측 keypoint 시퀀스 (npz). TP ≥ 2 / FP == 0.

    분류 근거 = 신체 방향 실측 (몸통 벡터 버킷, 2026-07-22 재계측):
      invert(down 0.24+side 0.36) · straddle-invert(side 0.68) · elbow-twist-sister(down 0.91)
      → 지속 역전 성립 (TP). elbow-twist-sister 는 플랜 예시 열거에 없지만 실데이터가
      91% 역위(hip-above-shoulder ratio 1.000)로 invert 본인보다 강한 인버전 —
      이름 열거가 아닌 기준(신체 방향)으로 일반화 ([[motion-routing-generalize-principle]]).
      비인버전(power-spin 0.042 / sideway-spin 0.025 / 정립 5종 0.000) → False.
    """

    EXPECTED = {
        "invert": True,
        "straddle-invert": True,
        "elbow-twist-sister": True,
        "power-spin": False,   # 전면 적용 시 boneCV 1.03→7.0 파괴 실측 — 절대 미검출
        "sideway-spin": False,
        "peter-pan": False,
        "kip-up": False,       # spike 8s 트림 구간은 정립 (up 1.00) — 실측 그대로
        "Chair-spin": False,
        "Diamond-Spin": False,
        "sliding-spin": False,
    }

    @pytest.mark.skipif(not _SPIKE_KPTS.exists(), reason="spike kpts 산출물 없음 (로컬 전용)")
    def test_spike_sequences(self):
        results: dict[str, bool] = {}
        for name, expected in self.EXPECTED.items():
            npz = _SPIKE_KPTS / f"{name}.npz"
            assert npz.exists(), f"spike npz 누락: {npz}"
            d = np.load(npz)
            det = iw.detect_inversion(d["kpts"][:, :, :2], d["scores"])
            results[name] = det.is_inverted
            assert det.is_inverted is expected, (
                f"{name}: expected {expected}, got {det.is_inverted} "
                f"(ratio={det.inverted_ratio:.3f} run={det.longest_run_frames})"
            )
        assert sum(results.values()) >= 2  # TP ≥ 2 (invert 계열)
        assert not any(results[n] for n, e in self.EXPECTED.items() if e is False)  # FP 0


class TestHomographyRoundTrip:
    """Behavior 3 — H forward → H⁻¹ inverse 좌표 왕복 (원본 공간 복원)."""

    W, H = 720, 1280

    def test_round_trip_interior_points(self):
        H = iw.build_homography(np.array([200.0, 300.0]), self.W, self.H)
        rng = np.random.default_rng(42)
        pts = rng.uniform([0, 0], [self.W, self.H], size=(50, 2))
        back = iw.unwarp_points(H, iw.warp_points(H, pts))
        assert np.all(np.isfinite(back))
        assert np.max(np.abs(back - pts)) <= 1e-6

    def test_round_trip_boundary_and_outside_points(self):
        # 프레임 경계·경계 밖 투영 좌표도 유한 왕복 (플랜 behavior 3)
        H = iw.build_homography(np.array([100.0, 1100.0]), self.W, self.H)
        pts = np.array(
            [[0.0, 0.0], [self.W, 0.0], [0.0, self.H], [self.W, self.H],
             [-100.0, -50.0], [self.W + 200.0, self.H + 300.0]]
        )
        back = iw.unwarp_points(H, iw.warp_points(H, pts))
        assert np.all(np.isfinite(back))
        assert np.max(np.abs(back - pts)) <= 1e-6

    def test_center_at_principal_point_is_identity(self):
        # 인물이 광학 중심에 있으면 H = I (워프 무의미 — spike ±0.03 무영향 근거)
        H = iw.build_homography(np.array([self.W / 2, self.H / 2]), self.W, self.H)
        assert np.allclose(H, np.eye(3), atol=1e-9)


class TestUnwarpFailSafe:
    """Behavior 4 — 프레임 단위 폴백: 비유한/범위 대탈출 → 1차 좌표 유지 표식."""

    W, H = 720, 1280

    def test_nan_keypoints_marked_invalid(self):
        H = iw.build_homography(np.array([200.0, 300.0]), self.W, self.H)
        kpts = np.full((17, 2), 350.0)
        kpts[3] = np.nan
        _, ok = iw.unwarp_frame_keypoints(H, kpts, self.W, self.H)
        assert ok is False

    def test_far_out_of_bounds_marked_invalid(self):
        H = iw.build_homography(np.array([200.0, 300.0]), self.W, self.H)
        kpts = np.full((17, 2), 350.0)
        kpts[5] = [self.W * 3.0, self.H * 3.0]  # 허용 마진(25%) 대탈출
        _, ok = iw.unwarp_frame_keypoints(H, kpts, self.W, self.H)
        assert ok is False

    def test_valid_keypoints_pass_and_recover(self):
        H = iw.build_homography(np.array([200.0, 300.0]), self.W, self.H)
        orig = np.full((17, 2), 0.0)
        orig[:, 0] = np.linspace(50, 650, 17)
        orig[:, 1] = np.linspace(100, 1200, 17)
        warped = iw.warp_points(H, orig)
        back, ok = iw.unwarp_frame_keypoints(H, warped, self.W, self.H)
        assert ok is True
        assert np.max(np.abs(back - orig)) <= 1e-5

    def test_singular_homography_marked_invalid(self):
        singular = np.zeros((3, 3))
        kpts = np.full((17, 2), 350.0)
        _, ok = iw.unwarp_frame_keypoints(singular, kpts, self.W, self.H)
        assert ok is False


class TestEngineSecondPassHook:
    """32-15 Task 2 — RTMWPoseEngine 2-pass 조건부 훅 배선 (mock inferencer DI).

    warp_frames 는 cv2 의존(GPU/Pod 경로)이라 identity 스텁으로 monkeypatch —
    mock inferencer 는 픽셀 무관 상수 반환이므로 배선 검증에 충분하다.
    수학 자체(왕복·fail-safe)는 위 순수 테스트가 커버.
    """

    W, H = 72, 128  # principal point = (36, 64)

    def _engine(self, inferencer):
        from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
        return RTMWPoseEngine.create_with_inferencer(inferencer)

    def _pole(self):
        from sunity_shared.analysis.pose_frame import PoleAxis
        return PoleAxis(
            axis_vector=(0.0, 1.0, 0.0),
            confidence_level="low",
            source="vertical_fallback",
            frame_index=None,
        )

    def _make_inferencer(self, inverted: bool, center_x: float = 36.0):
        """모든 프레임 동일 인체 반환 mock — body 17 평균 = (center_x, 64)."""
        from unittest.mock import MagicMock

        kps = np.zeros((1, 133, 2), dtype=np.float32)
        kps[0, :, 0] = center_x
        kps[0, :17, 1] = 64.0
        sh_y, hip_y = (74.0, 54.0) if inverted else (54.0, 74.0)
        kps[0, [_L_SHOULDER, _R_SHOULDER], 1] = sh_y
        kps[0, [_L_HIP, _R_HIP], 1] = hip_y
        scores = np.full((1, 133), 0.9, dtype=np.float32)
        mock = MagicMock()
        mock.return_value = (kps, scores)
        return mock

    def _frames(self, n=8):
        return np.zeros((n, self.H, self.W, 3), dtype=np.uint8)

    def test_env_off_no_second_pass(self, monkeypatch):
        monkeypatch.delenv("PR_INVERSION_ENABLED", raising=False)
        mock = self._make_inferencer(inverted=True)
        out = self._engine(mock).estimate(self._frames(), self._pole())
        assert len(out) == 8
        assert mock.call_count == 8  # 1차만 — env 기본 off

    def test_env_on_upright_detect_false_identical(self, monkeypatch):
        # 정립 영상: detect False → 기존 경로 그대로 (추론 1회분 + 결과 동일)
        mock_off = self._make_inferencer(inverted=False)
        monkeypatch.delenv("PR_INVERSION_ENABLED", raising=False)
        baseline = self._engine(mock_off).estimate(self._frames(), self._pole())

        mock_on = self._make_inferencer(inverted=False)
        monkeypatch.setenv("PR_INVERSION_ENABLED", "1")
        out = self._engine(mock_on).estimate(self._frames(), self._pole())
        assert mock_on.call_count == 8  # 2차 없음
        assert out == baseline  # frozen dataclass 동등 — 바이트 동일 경로

    def test_env_on_inverted_identity_center_runs_second_pass(self, monkeypatch):
        # 인체 중심 = 광학 중심 → H = I → 교체돼도 좌표 불변 (왕복 무손실 배선 증명)
        mock_off = self._make_inferencer(inverted=True)
        monkeypatch.delenv("PR_INVERSION_ENABLED", raising=False)
        baseline = self._engine(mock_off).estimate(self._frames(), self._pole())

        mock_on = self._make_inferencer(inverted=True)
        monkeypatch.setenv("PR_INVERSION_ENABLED", "1")
        monkeypatch.setattr(iw, "warp_frames", lambda frames, hs: frames.copy())
        out = self._engine(mock_on).estimate(self._frames(), self._pole())
        assert mock_on.call_count == 16  # 1차 8 + 2차 8
        assert out == baseline  # H=I → unwarp identity → 좌표 동일

    def test_env_on_inverted_offcenter_coords_unwarped(self, monkeypatch):
        # 중심이 광학 중심 밖 → H ≠ I → 2차 좌표가 H⁻¹ 로 원본 공간 변환됨
        mock_off = self._make_inferencer(inverted=True, center_x=12.0)
        monkeypatch.delenv("PR_INVERSION_ENABLED", raising=False)
        baseline = self._engine(mock_off).estimate(self._frames(), self._pole())

        mock_on = self._make_inferencer(inverted=True, center_x=12.0)
        monkeypatch.setenv("PR_INVERSION_ENABLED", "1")
        monkeypatch.setattr(iw, "warp_frames", lambda frames, hs: frames.copy())
        out = self._engine(mock_on).estimate(self._frames(), self._pole())
        assert mock_on.call_count == 16
        assert out != baseline  # 좌표 교체 발생 (2차 적용)

    def test_env_on_warp_failure_graceful_first_pass(self, monkeypatch):
        # 워프 실패(cv2 부재 등) → 1차 결과 유지 (graceful — 분석 중단 금지)
        mock_off = self._make_inferencer(inverted=True)
        monkeypatch.delenv("PR_INVERSION_ENABLED", raising=False)
        baseline = self._engine(mock_off).estimate(self._frames(), self._pole())

        def _boom(frames, hs):
            raise RuntimeError("warp 실패 시뮬레이션")

        mock_on = self._make_inferencer(inverted=True)
        monkeypatch.setenv("PR_INVERSION_ENABLED", "1")
        monkeypatch.setattr(iw, "warp_frames", _boom)
        out = self._engine(mock_on).estimate(self._frames(), self._pole())
        assert mock_on.call_count == 8  # 2차 추론 미도달
        assert out == baseline


class TestPurity:
    """Behavior 5 — 순수성: torch 0 / cv2 는 GPU 워프 함수 내부 lazy 만."""

    def test_no_torch_import(self):
        src = inspect.getsource(iw)
        assert "import torch" not in src

    def test_no_module_level_cv2(self):
        # cv2 는 warp_frames(GPU/Pod 경로) 내부 lazy import 만 허용 —
        # detect/호모그래피 순수 경로가 cv2 부재 환경(Lambda/CI)에서도 동작.
        for line in inspect.getsource(iw).splitlines():
            stripped = line.strip()
            if stripped.startswith(("import cv2", "from cv2")):
                assert line.startswith((" ", "\t")), "cv2 는 함수 내부 lazy import 만 허용"

    def test_detect_and_homography_pure_numpy(self):
        # 함수 소스에 cv2 참조 자체가 없어야 함 (Rodrigues 는 numpy 구현)
        for fn in (iw.detect_inversion, iw.build_homography, iw.warp_points, iw.unwarp_points):
            assert "cv2" not in inspect.getsource(fn)
