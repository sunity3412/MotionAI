"""fault_zoom 확대 비교 이미지 생성 단위테스트 (belle 2026-06-21).

순수 — PIL/numpy 외 의존 0 (S3/네트워크/firestore import 금지). 합성 프레임 +
합성 keypointReport 로 인덱싱(프레임배열 fps vs report fps 분리) + crop + PNG 출력 +
좌표 부재/미매핑 관절 skip 을 못 박는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402


def _frames(n: int, h: int = 200, w: int = 120) -> np.ndarray:
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    for i in range(n):
        a[i, :, :, 0] = (i * 10) % 255
    return a


def _report(
    n: int,
    fps: float,
    joints=("left_knee", "right_knee", "left_hip"),
    confidence: float | None = None,
):
    """합성 keypointReport. confidence 기본 부재 = legacy 하위호환 경로 검증 유지."""
    nj = len(joints)
    data: list[float] = []
    for _f in range(n):
        for _j in range(nj):
            data += [0.5, 0.5]  # 중앙
    rep = {"joints": list(joints), "frames": n, "fps": fps, "data": data}
    if confidence is not None:
        rep["confidence"] = [confidence] * (n * nj)
    return rep


def test_build_produces_valid_png_with_deficit_marker():
    comps = fz.build_fault_zoom_comparisons(
        _frames(18), _frames(9), _report(18, 18.0), _report(9, 9.0),
        worst_seconds=0.5,
        fault_joints=["left_knee", "right_knee"],
        joint_deltas={"left_knee": 23.0},
        frames_fps=9.0,
    )
    assert len(comps) == 2
    by_joint = {c["joint"]: c for c in comps}
    assert by_joint["left_knee"]["deficitDeg"] == 23.0
    assert by_joint["right_knee"]["deficitDeg"] is None
    for c in comps:
        assert c["png"][:4] == b"\x89PNG", "유효 PNG 시그니처"


def test_unmapped_joint_skipped():
    # left_hand 는 report.joints 에 없음 → 좌표 부재 → skip (빈 결과).
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.5, fault_joints=["left_hand"], joint_deltas=None,
        frames_fps=9.0,
    )
    assert comps == []


def test_dedup_and_max_items():
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=None,  # None → 중앙 프레임 (graceful)
        fault_joints=["left_knee", "left_knee", "right_knee", "left_hip"],
        joint_deltas=None, frames_fps=9.0, max_items=2,
    )
    joints = [c["joint"] for c in comps]
    assert joints == ["left_knee", "right_knee"], "중복 제거 + max_items 2"


def test_none_frames_graceful():
    assert fz.build_fault_zoom_comparisons(
        None, None, {}, {}, 0.0, ["left_knee"], None
    ) == []


# ─────────── B1 (2026-06-21) DTW 같은-pose 기준 프레임 ───────────

from dataclasses import dataclass as _dc


@_dc
class _Match:
    start: int
    path: list


def test_matched_ref_frame_maps_via_dtw():
    m = _Match(start=5, path=[(0, 7), (1, 8), (2, 9), (3, 10), (3, 11), (4, 12)])
    assert fz._matched_ref_frame(m, 5, ref_n=20) == 7   # local 0 → 7
    assert fz._matched_ref_frame(m, 8, ref_n=20) == 11  # local 3 → median([10,11])
    assert fz._matched_ref_frame(m, 8, ref_n=10) == 9   # clamp to ref_n-1
    assert fz._matched_ref_frame(m, 99, ref_n=20) is None  # out of path → fallback
    assert fz._matched_ref_frame(None, 8, 20) is None      # no match → fallback


def test_build_uses_dtw_match_for_ref_frame():
    """dtw_match 제공 시 기준 프레임이 시간비례가 아닌 match 매핑을 따른다(graceful)."""
    m = _Match(start=0, path=[(i, i) for i in range(9)])
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.5, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0, dtw_match=m,
    )
    assert len(comps) == 1 and comps[0]["png"][:4] == b"\x89PNG"


# ─────────── quick-260702-sic — 프레임 override / grouping / 저신뢰 폴백 ───────────

import io as _io  # noqa: E402

from PIL import Image as _Img  # noqa: E402

_LEG_JOINTS = ("left_hip", "right_hip", "left_knee", "right_knee")


def _png_pixel(png: bytes, x: int, y: int) -> tuple[int, int, int]:
    return _Img.open(_io.BytesIO(png)).convert("RGB").getpixel((x, y))


def test_user_frame_override_wins_over_worst_seconds():
    """user_frame_idx 전달 시 user crop 이 그 9fps 프레임에서 나온다.

    _frames 는 프레임 i 의 red 채널 = i*10 — crop 픽셀색으로 프레임 출처 검증
    (test_build_uses_dtw_match_for_ref_frame 패턴 재사용).
    """
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.0,  # override 없으면 frame 0 (red 0)
        fault_joints=["left_knee"], joint_deltas=None, frames_fps=9.0,
        user_frame_idx=7,
    )
    assert len(comps) == 1
    r, _g, _b = _png_pixel(comps[0]["png"], 5, 100)
    assert r == 70, "user crop = frame 7 (red 70) — override 가 worst_seconds 를 이김"


def test_ref_frame_override_wins_over_dtw_match():
    """ref_frame_idx 전달 시 dtw_match 가 있어도 override 가 이긴다."""
    m = _Match(start=0, path=[(i, 0) for i in range(9)])  # DTW 는 전부 ref 0 매핑
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.0, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0, dtw_match=m, ref_frame_idx=5,
    )
    assert len(comps) == 1
    # ref 반쪽 = x >= _OUT + gap(6).
    r, _g, _b = _png_pixel(comps[0]["png"], fz._OUT + 6 + 5, 100)
    assert r == 50, "ref crop = frame 5 (red 50) — override 가 DTW match 를 이김"


def test_grouping_legs_single_card():
    """좌+우 hips+knees 4관절 kind 전원 'deficit' → legs 1장 + deficit=max."""
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9),
        _report(9, 9.0, _LEG_JOINTS), _report(9, 9.0, _LEG_JOINTS),
        worst_seconds=0.5,
        fault_joints=list(_LEG_JOINTS),
        joint_deltas={
            "left_hip": 30.0, "right_hip": 28.0,
            "left_knee": 25.0, "right_knee": 30.0,
        },
        frames_fps=9.0,
        joint_kinds={j: "deficit" for j in _LEG_JOINTS},
    )
    assert len(comps) == 1, "스플릿 4관절 → 결함단위 1장"
    c = comps[0]
    assert c["region"] == "legs"
    assert c["joint"] == "left_hip", "대표 joint = fault_joints 순서상 첫 멤버"
    assert c["deficitDeg"] == 30.0, "grouped deficit = 멤버 max"
    assert c["kind"] == "deficit"
    assert c["png"][:4] == b"\x89PNG"


def test_grouping_requires_both_sides():
    """좌측만(left_hip+left_knee) → grouping 안 됨 (2개 카드, region 없음)."""
    joints = ("left_hip", "left_knee")
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0, joints), _report(9, 9.0, joints),
        worst_seconds=0.5, fault_joints=list(joints), joint_deltas=None,
        frames_fps=9.0, joint_kinds={j: "deficit" for j in joints},
    )
    assert [c["joint"] for c in comps] == ["left_hip", "left_knee"]
    assert all("region" not in c for c in comps)


def test_grouping_disabled_on_mixed_kinds():
    """kind 혼재(improved+worsened, mode3) → grouping 안 됨."""
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.5, fault_joints=["left_knee", "right_knee"],
        joint_deltas=None, frames_fps=9.0,
        joint_kinds={"left_knee": "improved", "right_knee": "worsened"},
    )
    assert [c["joint"] for c in comps] == ["left_knee", "right_knee"]
    assert all("region" not in c for c in comps)


def test_low_confidence_ref_side_falls_back_to_full_frame():
    """ref keypoint 저신뢰(0.1 < _KP_CONF_MIN) → skip 대신 전신 폴백으로 항목 유지."""
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9),
        _report(9, 9.0), _report(9, 9.0, confidence=0.1),
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        joint_kinds={"left_knee": "deficit"},
    )
    assert len(comps) == 1, "한 측 저신뢰는 skip 이 아니라 전신 폴백"
    assert comps[0]["png"][:4] == b"\x89PNG"


def test_both_sides_low_confidence_skipped():
    """양측 다 저신뢰 → 전신 vs 전신은 정보 없음 — 기존처럼 skip."""
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9),
        _report(9, 9.0, confidence=0.1), _report(9, 9.0, confidence=0.1),
        worst_seconds=0.5, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0, joint_kinds={"left_knee": "deficit"},
    )
    assert comps == []


def test_confidence_present_and_high_passes_gate():
    """confidence >= 0.5 는 기존 crop 경로 그대로 (게이트 통과)."""
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9),
        _report(9, 9.0, confidence=0.9), _report(9, 9.0, confidence=0.9),
        worst_seconds=0.5, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0,
    )
    assert len(comps) == 1 and comps[0]["png"][:4] == b"\x89PNG"


def test_group_fault_joints_pure_helper():
    """_group_fault_joints 직접 단위테스트 — 대표 joint 안정성 + region 판정."""
    kinds = {j: "deficit" for j in _LEG_JOINTS}
    units = fz._group_fault_joints(
        ["right_knee", "left_hip", "right_hip", "left_knee"], kinds
    )
    assert len(units) == 1
    u = units[0]
    assert u.joint == "right_knee", "대표 = fault_joints 순서상 첫 멤버"
    assert u.members == ("right_knee", "left_hip", "right_hip", "left_knee")
    assert u.region == "legs"

    # kind 부재(None) = legacy 호출 → grouping 비활성 (관절당 1 unit).
    units = fz._group_fault_joints(["left_knee", "right_knee"], None)
    assert [(u.joint, u.region) for u in units] == [
        ("left_knee", None), ("right_knee", None),
    ]

    # region 밖 관절 + grouped region 혼합 — 순서 보존, 비멤버는 단일 unit.
    kinds2 = {**kinds, "left_shoulder": "deficit"}
    units = fz._group_fault_joints(
        ["left_shoulder", "left_hip", "right_knee"], kinds2
    )
    assert [(u.joint, u.region) for u in units] == [
        ("left_shoulder", None), ("left_hip", "legs"),
    ]
    assert units[1].members == ("left_hip", "right_knee")
