"""quick-260813-u8i — 카드 초 라벨 환산 label_fps (표시 전용, 채점 무접촉).

fault_zoom 확대 카드의 초 라벨(÷frames_fps=9.0 라벨 사슬, 실제보다 ~10% 큼)을
측별 실효 fps 로 환산하는 keyword-only `label_fps` 배선을 순수 함수 수준에서
고정한다 — AWS/네트워크/GPU 0, 합성 프레임 + 최소 report
(test_fault_zoom_display_repair.py 픽스처 관례 상속):

  1. 하위호환 — label_fps 미지정(None) 호출은 결과 dict(userVideoSec/
     refVideoSec 포함)와 png 가 종전과 byte-동일.
  2. 측별 환산 — label_fps=(9.997, 15.0) 이면 userVideoSec == u_idx/9.997,
     refVideoSec == r_display_idx/15.0 (frames_fps 는 프레임 선택에만 관여).
  3. 측별 폴백 — label_fps=(None, 15.0) 이면 user 측만 frames_fps 환산 유지,
     ref 측은 15.0.
  4. fail-open — 0/음수/비유한 값은 그 측 frames_fps 폴백 (라벨 때문에 카드를
     죽이지 않는다 — 좌표 게이트 display_anchor 만 fail-closed 인 층위 유지).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import numpy as np  # noqa: E402

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

_FPS = 12.0
_N = 24
_SIZE = 96

_USER_KP = {
    "left_shoulder": (0.564, 0.397), "right_shoulder": (0.612, 0.372),
    "left_hip": (0.505, 0.475), "right_hip": (0.548, 0.462),
    "left_knee": (0.402, 0.628), "right_knee": (0.612, 0.652),
    "left_hand": (0.470, 0.196), "right_hand": (0.628, 0.184),
}
_REF_KP = dict(_USER_KP)


def _report(xy):
    joints = list(xy)
    data: list[float] = []
    conf: list[float] = []
    for _f in range(_N):
        for j in joints:
            data += list(xy[j])
            conf.append(0.9)
    return {"joints": joints, "frames": _N, "fps": _FPS,
            "data": data, "confidence": conf}


def _frames():
    base = np.full((_N, _SIZE, _SIZE, 3), 120, dtype=np.uint8)
    for f in range(_N):
        base[f, 0, 0, :] = np.uint8((f * 11) % 256)
    return base


def _build(**kw):
    """left_hip 확정(angle) 카드 1장 — override 경로 (운영 units 루프 미러)."""
    return fz.build_fault_zoom_comparisons(
        _frames(), _frames(),
        _report(_USER_KP), _report(_REF_KP),
        None,
        ["left_hip"],
        joint_deltas={"left_hip": 20.0},
        frames_fps=_FPS,
        joint_kinds={"left_hip": "deficit"},
        dtw_match=None,
        user_frame_idx=10,
        ref_frame_idx=10,
        criterion_units=[{
            "criterion": "angle_vs_reference__left_hip",
            "joints": ("left_hip",), "region": None, "at_frame_idx": None,
        }],
        analysis_id="t-u8i",
        **kw,
    )


def _base_indices(base_item):
    """base 런의 초 → 표시 인덱스 역산 — 인덱스 하드코딩 없이 기대값 유도.

    base 초 == idx/frames_fps (종전 계약) 이므로 round(sec x frames_fps) 가
    그 카드의 표시 인덱스다 (u_idx_unit / r_display_idx).
    """
    u_idx = round(base_item["userVideoSec"] * _FPS)
    r_idx = round(base_item["refVideoSec"] * _FPS)
    return u_idx, r_idx


# ── 1. 하위호환 — label_fps 미지정(None) = byte-동일 ────────────────────────


def test_label_fps_none_is_byte_identical():
    base = _build()
    explicit = _build(label_fps=None)
    assert len(base) == 1 and len(explicit) == 1
    assert base[0]["png"] == explicit[0]["png"]
    assert base[0]["userVideoSec"] == explicit[0]["userVideoSec"]
    assert base[0]["refVideoSec"] == explicit[0]["refVideoSec"]
    # 종전 계약 그 자체 — 미지정 경로는 frames_fps 환산 (÷12 픽스처).
    assert base[0]["userVideoSec"] == pytest.approx(10 / _FPS, abs=1e-12)


# ── 2. 측별 환산 — 분모만 교체, 프레임 선택 무접촉 ──────────────────────────


def test_label_fps_per_side_conversion():
    base = _build()
    labeled = _build(label_fps=(9.997, 15.0))
    assert len(base) == 1 and len(labeled) == 1
    u_idx, r_idx = _base_indices(base[0])
    assert labeled[0]["userVideoSec"] == pytest.approx(u_idx / 9.997, abs=1e-12)
    assert labeled[0]["refVideoSec"] == pytest.approx(r_idx / 15.0, abs=1e-12)
    # 프레임 선택 사슬 무접촉 — rep 인덱스 필드는 그대로.
    assert labeled[0]["userFrameIdx"] == base[0]["userFrameIdx"]
    assert labeled[0]["refFrameIdx"] == base[0]["refFrameIdx"]
    # 0.1s 표시 정밀도에서 값이 갈리므로(0.8s vs 1.0s) 라벨 픽셀도 변한다.
    assert labeled[0]["png"] != base[0]["png"]


# ── 3. 측별 폴백 — None 인 측만 frames_fps 유지 ─────────────────────────────


def test_label_fps_per_side_fallback():
    base = _build()
    labeled = _build(label_fps=(None, 15.0))
    assert len(labeled) == 1
    _u_idx, r_idx = _base_indices(base[0])
    assert labeled[0]["userVideoSec"] == base[0]["userVideoSec"]
    assert labeled[0]["refVideoSec"] == pytest.approx(r_idx / 15.0, abs=1e-12)


# ── 4. fail-open — 비양수/비유한 값은 그 측 frames_fps 폴백 ─────────────────


@pytest.mark.parametrize("bad", [
    (0.0, -3.0),
    (float("nan"), float("inf")),
])
def test_label_fps_nonpositive_fail_open(bad):
    base = _build()
    labeled = _build(label_fps=bad)
    assert len(labeled) == 1
    assert labeled[0]["userVideoSec"] == base[0]["userVideoSec"]
    assert labeled[0]["refVideoSec"] == base[0]["refVideoSec"]
    assert labeled[0]["png"] == base[0]["png"]
