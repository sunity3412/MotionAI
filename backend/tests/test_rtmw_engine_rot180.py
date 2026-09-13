"""quick-260913-udr Task 2 — RTMWPoseEngine rot180 2-pass 배선 (mock inferencer DI).

골격은 phase32/test_inversion_warp.py TestEngineSecondPassHook 을 따른다
(create_with_inferencer, W=72/H=128, monkeypatch env, `out == baseline`).

마커 인식 mock: 원본 프레임은 frames[t, 0, 0, 0] = 255, 회전 프레임에선 그 마커가
(H-1, W-1) 에 온다. mock 은 마커 위치로 "회전 프레임이냐" 를 판단하고, 회전 프레임이면
**테스트 안에서 직접 계산한** x→W-1-x, y→H-1-y 좌표를 돌려준다 (모듈 함수를 쓰지
않는다 — 독립 검증). 비대칭 골격(왼어깨 x < 오른어깨 x, 역립: 엉덩이 y < 어깨 y,
마진 = torso 1.0 배, 8프레임 지속).

검증의 한계: mock 은 픽셀을 보지 않는 상수 골격이라 "회전이 검출기를 돕는가" 는 증명하지
못한다 — 그건 MEASUREMENTS §2 실측이 답한 것. 여기서는 **배선의 좌표 정합** 만 증명한다.
GPU 실경로(RunPod Pod)는 미검증 — Pod 0대.

Behavior (260913-udr-PLAN Task 2):
  1. 두 플래그 다 off: 호출 수 = T, rot180 함수 미진입 (raise 로 monkeypatch 해도 정상 반환)
  2. rot180 on + 정립: detect False → 호출 수 = T, 산출 == off 기준선, pickle 바이트 동일
  3. rot180 on + 역립 + 마커 mock: 호출 수 = 2T, 산출 == 기준선, 이름별 좌표 동일(좌우 스왑 없음)
  4. 회전 패스가 회전공간 x 에 +5 → 채택 프레임의 원본공간 x 는 기준선 −5 (역매핑 방향)
  5. 회전 패스 t∈{2,5} 미검출 → 그 두 프레임은 기준선과 같고 나머지는 채택
  6. 회전 패스 t=3 body 관절 NaN → t=3 은 기준선과 같음
  7. 회전 패스 예외 → estimate 는 예외 없이 off 기준선과 == 반환
  8. 두 플래그 동시 on: warp_frames 미호출(3패스 없음), 호출 수 = 2T, both_flags_on 경고 1줄
  9. rot180 off + PR on: PR 경로가 종전대로 돌고 rot180 함수는 미진입 (PR 무회귀)
"""

from __future__ import annotations

import logging
import pickle
from unittest.mock import MagicMock

import numpy as np
import pytest

from sunity_shared.analysis import inversion_warp as iw
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

W, H = 72, 128
T = 8
_ENGINE_LOGGER = "sunity_shared.analysis.pose_engines.rtmw.rtmw_engine"
_R_ELBOW = 8


def _skeleton(inverted: bool) -> np.ndarray:
    """(133,2) 비대칭 골격, 원본 프레임 공간. 왼어깨 x(26) < 오른어깨 x(46)."""
    k = np.zeros((133, 2), dtype=np.float32)
    k[:, 0] = 36.0
    k[:, 1] = 64.0
    if inverted:
        # 역립: 어깨 y=90, 엉덩이 y=50 → torso 40, 마진 (90-50)/40 = 1.0 ≥ 0.3
        body = {
            0: (36, 100), 1: (34, 98), 2: (38, 98), 3: (32, 99), 4: (40, 99),
            5: (26, 90), 6: (46, 90), 7: (20, 100), 8: (52, 100), 9: (16, 110), 10: (56, 110),
            11: (30, 50), 12: (42, 50), 13: (28, 30), 14: (44, 30), 15: (26, 12), 16: (46, 12),
        }
    else:
        # 정립: 어깨 y=38, 엉덩이 y=78
        body = {
            0: (36, 28), 1: (34, 30), 2: (38, 30), 3: (32, 29), 4: (40, 29),
            5: (26, 38), 6: (46, 38), 7: (20, 28), 8: (52, 28), 9: (16, 18), 10: (56, 18),
            11: (30, 78), 12: (42, 78), 13: (28, 98), 14: (44, 98), 15: (26, 116), 16: (46, 116),
        }
    for i, (x, y) in body.items():
        k[i] = (float(x), float(y))
    return k


class _MarkerInferencer:
    """rtmlib Wholebody mock — frame (H,W,3) → ((N,133,2), (N,133)).

    rotated_hook(t_rot, kps_rot) → kps_rot | None(미검출) | raise — 회전 패스 결과를
    테스트가 조작한다. t_rot 는 회전 프레임 호출 순번(= 프레임 인덱스, _infer_raw 가 순서대로 돈다).
    """

    def __init__(self, inverted: bool, rotated_hook=None) -> None:
        self.skeleton = _skeleton(inverted)
        self.rotated_hook = rotated_hook
        self.rot_calls = 0

    def __call__(self, frame: np.ndarray):
        scores = np.full((1, 133), 0.9, dtype=np.float32)
        is_rotated = frame[H - 1, W - 1, 0] == 255 and frame[0, 0, 0] == 0
        if not is_rotated:
            return self.skeleton[None].copy(), scores
        t = self.rot_calls
        self.rot_calls += 1
        kps_rot = self.skeleton.copy()
        kps_rot[:, 0] = (W - 1) - kps_rot[:, 0]  # 테스트 안에서 직접 계산 — 모듈 함수 미사용
        kps_rot[:, 1] = (H - 1) - kps_rot[:, 1]
        if self.rotated_hook is not None:
            kps_rot = self.rotated_hook(t, kps_rot)
            if kps_rot is None:
                return np.zeros((0, 133, 2), dtype=np.float32), np.zeros((0, 133), dtype=np.float32)
        return kps_rot[None], scores


def _mock(inverted: bool, rotated_hook=None) -> MagicMock:
    return MagicMock(side_effect=_MarkerInferencer(inverted, rotated_hook))


def _frames(n: int = T) -> np.ndarray:
    frames = np.zeros((n, H, W, 3), dtype=np.uint8)
    frames[:, 0, 0, 0] = 255  # 원본 마커 — 회전하면 (H-1, W-1) 로 간다
    return frames


def _engine(inferencer):
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
    return RTMWPoseEngine.create_with_inferencer(inferencer)


def _pole():
    from sunity_shared.analysis.pose_frame import PoleAxis
    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )


def _baseline(monkeypatch, inverted: bool):
    monkeypatch.delenv("PR_INVERSION_ENABLED", raising=False)
    monkeypatch.delenv("ROT180_INVERSION_ENABLED", raising=False)
    return _engine(_mock(inverted)).estimate(_frames(), _pole())


def _shift_x(dx: float):
    def hook(_t, kps_rot):
        kps_rot[:, 0] += dx
        return kps_rot
    return hook


def _px_x(frame, name: str) -> float:
    return frame.keypoints_2d[name].x * W


# ── 1. 두 플래그 off — rot180 미진입 ─────────────────────────────────────

def test_both_flags_off_never_enters_rot180(monkeypatch):
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine

    monkeypatch.delenv("PR_INVERSION_ENABLED", raising=False)
    monkeypatch.delenv("ROT180_INVERSION_ENABLED", raising=False)

    def _boom(self, *args, **kwargs):
        raise AssertionError("rot180 경로에 진입하면 안 된다 (두 플래그 off)")

    monkeypatch.setattr(RTMWPoseEngine, "_maybe_second_pass_rot180", _boom)
    mock = _mock(inverted=True)
    out = _engine(mock).estimate(_frames(), _pole())
    assert len(out) == T
    assert mock.call_count == T


# ── 2. rot180 on + 정립 — detect False → 1차 그대로 ───────────────────────

def test_rot180_on_upright_detect_false_identical(monkeypatch):
    baseline = _baseline(monkeypatch, inverted=False)
    monkeypatch.setenv("ROT180_INVERSION_ENABLED", "1")
    mock = _mock(inverted=False)
    out = _engine(mock).estimate(_frames(), _pole())
    assert mock.call_count == T
    assert out == baseline
    assert pickle.dumps(out) == pickle.dumps(baseline)


# ── 3. rot180 on + 역립 — 역매핑이 좌표를 정확히 되돌리고 좌우 스왑 없음 ────

def test_rot180_on_inverted_roundtrip_identical_by_name(monkeypatch):
    baseline = _baseline(monkeypatch, inverted=True)
    monkeypatch.setenv("ROT180_INVERSION_ENABLED", "1")
    mock = _mock(inverted=True)
    out = _engine(mock).estimate(_frames(), _pole())
    assert mock.call_count == 2 * T
    assert out == baseline
    for t in range(T):
        for name in KEYPOINT_NAMES:
            assert out[t].keypoints_2d[name] == baseline[t].keypoints_2d[name], (t, name)
    # 좌우가 스왑됐다면 여기서 갈린다 — 이름으로 대조한다.
    assert _px_x(out[0], "left_shoulder") == pytest.approx(26.0)
    assert _px_x(out[0], "right_shoulder") == pytest.approx(46.0)


# ── 4. 회전공간 +5 → 원본공간 −5 (역매핑 방향) ────────────────────────────

def test_rot180_shift_in_rotated_space_maps_back_negative(monkeypatch):
    baseline = _baseline(monkeypatch, inverted=True)
    monkeypatch.setenv("ROT180_INVERSION_ENABLED", "1")
    mock = _mock(inverted=True, rotated_hook=_shift_x(+5.0))
    out = _engine(mock).estimate(_frames(), _pole())
    assert mock.call_count == 2 * T
    assert out != baseline
    for t in range(T):
        for name in ("left_shoulder", "right_shoulder", "left_hip", "right_knee"):
            assert _px_x(out[t], name) == pytest.approx(_px_x(baseline[t], name) - 5.0, abs=1e-4)


# ── 5. 회전 패스 미검출 프레임 → 1차 유지, 나머지 채택 ───────────────────

def test_rotated_pass_missing_frames_keep_first(monkeypatch):
    baseline = _baseline(monkeypatch, inverted=True)
    monkeypatch.setenv("ROT180_INVERSION_ENABLED", "1")

    def hook(t, kps_rot):
        if t in (2, 5):
            return None  # 미검출
        kps_rot[:, 0] += 5.0
        return kps_rot

    out = _engine(_mock(inverted=True, rotated_hook=hook)).estimate(_frames(), _pole())
    for t in range(T):
        if t in (2, 5):
            assert out[t] == baseline[t]
        else:
            assert out[t] != baseline[t]
            assert _px_x(out[t], "left_shoulder") == pytest.approx(26.0 - 5.0)


# ── 6. 회전 패스 NaN 관절 → 그 프레임만 1차 유지 ─────────────────────────

def test_rotated_pass_nan_joint_keeps_first_for_that_frame(monkeypatch):
    baseline = _baseline(monkeypatch, inverted=True)
    monkeypatch.setenv("ROT180_INVERSION_ENABLED", "1")

    def hook(t, kps_rot):
        kps_rot[:, 0] += 5.0
        if t == 3:
            kps_rot[_R_ELBOW, 0] = np.nan
        return kps_rot

    out = _engine(_mock(inverted=True, rotated_hook=hook)).estimate(_frames(), _pole())
    assert out[3] == baseline[3]
    for t in (0, 1, 2, 4, 5, 6, 7):
        assert out[t] != baseline[t]


# ── 7. 회전 패스 예외 → 1차 그대로, 예외 없음 ─────────────────────────────

def test_rotated_pass_exception_graceful_first_pass(monkeypatch):
    baseline = _baseline(monkeypatch, inverted=True)
    monkeypatch.setenv("ROT180_INVERSION_ENABLED", "1")

    def hook(_t, _kps_rot):
        raise RuntimeError("2차 추론 실패 시뮬레이션")

    out = _engine(_mock(inverted=True, rotated_hook=hook)).estimate(_frames(), _pole())
    assert out == baseline


# ── 8. 두 플래그 동시 on — 회전이 이긴다, 3패스 없음 ──────────────────────

def test_both_flags_on_rotation_wins_no_third_pass(monkeypatch, caplog):
    baseline = _baseline(monkeypatch, inverted=True)
    monkeypatch.setenv("ROT180_INVERSION_ENABLED", "1")
    monkeypatch.setenv("PR_INVERSION_ENABLED", "1")

    def _boom(frames, hs):
        raise AssertionError("PR 워프가 돌면 안 된다 (회전이 이긴다 — 3패스 금지)")

    monkeypatch.setattr(iw, "warp_frames", _boom)
    mock = _mock(inverted=True)
    with caplog.at_level(logging.WARNING, logger=_ENGINE_LOGGER):
        out = _engine(mock).estimate(_frames(), _pole())
    assert mock.call_count == 2 * T
    assert out == baseline
    warnings = [r for r in caplog.records if "rot180_inversion both_flags_on" in r.getMessage()]
    assert len(warnings) == 1


# ── 9. rot180 off + PR on — PR 경로 무회귀, rot180 미진입 ─────────────────

def test_pr_path_unchanged_when_rot180_off(monkeypatch):
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine

    baseline = _baseline(monkeypatch, inverted=True)
    monkeypatch.setenv("PR_INVERSION_ENABLED", "1")
    monkeypatch.delenv("ROT180_INVERSION_ENABLED", raising=False)

    def _boom(self, *args, **kwargs):
        raise AssertionError("rot180 경로에 진입하면 안 된다 (rot180 off)")

    monkeypatch.setattr(RTMWPoseEngine, "_maybe_second_pass_rot180", _boom)
    # PR 워프는 cv2 의존 — phase32 선례대로 identity 스텁. mock 은 회전 마커가 없는
    # 프레임을 1차와 같은 골격으로 답하므로 H=I 가 아니어도 좌표는 unwarp 로 되돌아온다.
    monkeypatch.setattr(iw, "warp_frames", lambda frames, hs: frames.copy())
    mock = _mock(inverted=True)
    out = _engine(mock).estimate(_frames(), _pole())
    assert mock.call_count == 2 * T  # PR 2차는 종전대로 돈다
    assert len(out) == len(baseline)
