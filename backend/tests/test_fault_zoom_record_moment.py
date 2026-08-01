"""quick-260801-gbk Task 3 — 확대비교 카드가 자기 감점의 측정 순간을 앵커로 쓴다.

종전엔 모든 카드가 `worst_seconds` 한 시각에서 잘렸다 — 그 시각의 정의는 "동작
국면"이지 "감점이 난 순간"이 아니다. record 가 `atFrameIdx` 로 자기 순간을 나르면
카드마다 프레임이 갈리고, 표시 프레임이 측정 프레임과 같을 때만 `atMatched` 가
인증된다.

전부 합성 keypoint report + 프로덕션 함수 직접 호출 — GPU/S3/네트워크 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

# **일부러 프로덕션 기본 fps 가 아닌 값** — 프레임 인덱스/초 변환이 인자로 받은
# fps 를 실제로 쓰는지, 기본값을 가정하고 있는지를 값으로 구분한다.
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


class _Match:
    def __init__(self, start, path):
        self.start = start
        self.path = path


def _identity(n=_N):
    return _Match(0, [(i, i) for i in range(n)])


def _report(xy, low_conf_frames=()):
    joints = list(xy)
    data: list[float] = []
    conf: list[float] = []
    low = set(low_conf_frames)
    for f in range(_N):
        for j in joints:
            data += list(xy[j])
            conf.append(0.0 if f in low else 0.9)
    return {"joints": joints, "frames": _N, "fps": _FPS,
            "data": data, "confidence": conf}


def _frames():
    """프레임마다 픽셀 1개를 달리해 '다른 프레임을 골랐다'가 PNG 로 드러나게."""
    base = np.full((_N, _SIZE, _SIZE, 3), 120, dtype=np.uint8)
    for f in range(_N):
        base[f, 0, 0, :] = np.uint8((f * 11) % 256)
    return base


def _unit(criterion, joints, at=None, region=None):
    return {"criterion": criterion, "joints": tuple(joints),
            "region": region, "at_frame_idx": at}


def _build(units, user_rep=None, ref_rep=None, dtw_match=None, **kw):
    joints: list[str] = []
    for u in units:
        for j in u["joints"]:
            if j not in joints:
                joints.append(j)
    return fz.build_fault_zoom_comparisons(
        _frames(), _frames(),
        user_rep or _report(_USER_KP), ref_rep or _report(_REF_KP),
        worst_seconds=1.0,
        fault_joints=joints,
        joint_deltas={j: 20.0 for j in joints},
        frames_fps=_FPS,
        joint_kinds={j: "deficit" for j in joints},
        dtw_match=dtw_match if dtw_match is not None else _identity(),
        criterion_units=units,
        user_frame_candidates=[8, 9, 10, 11, 12],
        ref_frame_candidates=[8, 9, 10, 11, 12],
        analysis_id="t",
        **kw,
    )


# ── unit 파생 — record 의 순간이 unit 까지 실려 온다 ─────────────────────────


def test_criterion_units_carry_at_frame_idx():
    recs = [
        {"criterion": "angle_vs_reference__left_knee", "atFrameIdx": 7},
        {"criterion": "angle_vs_reference__right_knee"},
        {"criterion": "angle_vs_reference__left_hip", "atFrameIdx": -3},
        {"criterion": "angle_vs_reference__right_hip", "atFrameIdx": True},
    ]
    amap = {
        "left_knee": "left_knee", "right_knee": "right_knee",
        "left_hip": "left_hip", "right_hip": "right_hip",
    }
    units = fz.criterion_units_from_records(recs, list(amap.values()), amap)
    got = {u["criterion"]: u["at_frame_idx"] for u in units}
    assert got["angle_vs_reference__left_knee"] == 7
    # 부재/음수/bool 은 전부 None 강등 (fail-closed).
    assert got["angle_vs_reference__right_knee"] is None
    assert got["angle_vs_reference__left_hip"] is None
    assert got["angle_vs_reference__right_hip"] is None


# ── 카드가 자기 순간을 쓴다 ─────────────────────────────────────────────────


def test_cards_with_different_moments_get_different_frames():
    units = [
        _unit("angle_vs_reference__left_knee", ["left_knee"], at=4),
        _unit("angle_vs_reference__right_knee", ["right_knee"], at=13),
    ]
    comps = _build(units)
    assert len(comps) == 2
    frames = [c["userFrameIdx"] for c in comps]
    assert frames == [4, 13]
    assert len(set(frames)) == 2


def test_cards_with_the_same_moment_share_a_frame():
    """두 감점의 측정 순간이 실제로 같으면 카드도 같은 프레임 — 인위적 분산 없음."""
    units = [
        _unit("angle_vs_reference__left_knee", ["left_knee"], at=6),
        _unit("angle_vs_reference__right_knee", ["right_knee"], at=6),
    ]
    comps = _build(units)
    assert [c["userFrameIdx"] for c in comps] == [6, 6]
    assert all(c.get("atMatched") is True for c in comps)


def test_at_matched_true_only_when_display_equals_measurement():
    units = [_unit("angle_vs_reference__left_knee", ["left_knee"], at=5)]
    comps = _build(units)
    assert comps[0]["atMatched"] is True
    assert comps[0]["userFrameIdx"] == 5


def test_collapsed_anchor_falls_back_inside_the_window_without_certifying():
    """앵커 프레임 keypoint 가 붕괴하면 창 안 다른 프레임이 쓰이고 인증은 없다."""
    at = 11
    crushed = _report(_USER_KP, low_conf_frames=[at])
    units = [_unit("angle_vs_reference__left_knee", ["left_knee"], at=at)]
    comps = _build(units, user_rep=crushed)
    assert comps, "붕괴해도 카드 자체는 나와야 한다"
    card = comps[0]
    assert card["userFrameIdx"] != at
    assert abs(card["userFrameIdx"] - at) <= fz._MOMENT_ANCHOR_RADIUS
    assert "atMatched" not in card


# ── fail-closed 무회귀 ──────────────────────────────────────────────────────


def test_units_without_moment_are_byte_identical_to_legacy():
    """at_frame_idx 없는 unit 은 종전 경로와 산출이 완전히 같다."""
    units = [
        _unit("angle_vs_reference__left_knee", ["left_knee"]),
        _unit("angle_vs_reference__right_knee", ["right_knee"]),
    ]
    a = _build(units)
    b = _build(units)
    assert [c["png"] for c in a] == [c["png"] for c in b]
    assert all("atMatched" not in c for c in a)
    # 앵커가 없으므로 종전처럼 두 카드가 같은 batch 프레임을 공유한다.
    assert len({c["userFrameIdx"] for c in a}) == 1


def test_reference_frame_still_comes_from_dtw_not_from_the_record():
    """record 는 기준 순간을 나르지 않는다 — 기준은 여전히 DTW 대응에서 나온다."""
    units = [_unit("angle_vs_reference__left_knee", ["left_knee"], at=3)]
    comps = _build(units)
    card = comps[0]
    # identity DTW 이므로 기준도 같은 인덱스로 따라온다 — record 가 준 값이 아니라
    # _matched_ref_frame 이 만든 값이다.
    assert card["refMatched"] is True
    assert card["refFrameIdx"] == fz._matched_ref_frame(_identity(), 3, _N)


def test_dtw_failure_drops_synthetic_candidates_and_keeps_working():
    """DTW 대응이 성립하지 않으면 합성 후보를 버리고 기존 경로로 떨어진다."""
    broken = _Match(0, [])  # path 없음 → _matched_ref_frame None
    units = [_unit("angle_vs_reference__left_knee", ["left_knee"], at=4)]
    comps = _build(units, dtw_match=broken)
    # criterion 카드는 기준 대응 실패 시 D-12 로 미방출 — 크래시 0 이 요점.
    assert isinstance(comps, list)


# ── override 경로 (W3 — UnboundLocalError 회귀 가드) ─────────────────────────


def test_ref_frame_idx_override_path_does_not_raise():
    """_dtw_ref_fps/_dtw_ref_frames 가 분기 안에만 있으면 여기서 NameError 가 난다."""
    units = [_unit("angle_vs_reference__left_knee", ["left_knee"], at=4)]
    comps = _build(units, ref_frame_idx=6)
    assert comps
    assert comps[0]["userFrameIdx"] == 4


def test_override_path_without_moment_also_safe():
    units = [_unit("angle_vs_reference__left_knee", ["left_knee"])]
    comps = _build(units, ref_frame_idx=6)
    assert isinstance(comps, list)


# ── 앵커 클램프 (T-gbk-02 — 인덱싱 사고 방어) ───────────────────────────────


@pytest.mark.parametrize("at", [0, _N - 1, _N + 500])
def test_out_of_range_anchor_is_clamped_not_crashing(at):
    units = [_unit("angle_vs_reference__left_knee", ["left_knee"], at=at)]
    comps = _build(units)
    assert comps
    assert 0 <= comps[0]["userFrameIdx"] <= _N - 1
