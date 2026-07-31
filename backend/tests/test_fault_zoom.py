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


# ─────────── belle 2026-07-28 — 각도 배지 제거 (초 표기 대체) ───────────


def test_no_angle_badge_on_crops():
    """각도 배지("40°" 우상단) 미렌더 — belle "각도 배지는 빼고 초 표기로 바꿔줘".

    (a) _mark 단독: 구 배지 영역(우상단)에 브랜드 픽셀 0 — circle 만 그린다.
    (b) build e2e: joint_deltas 가 있어도 크롭 우상단 배지 영역은 무채색이고,
        deficitDeg **데이터**는 payload 에 그대로 방출 (D-20 — 렌더만 제거).
    _deficit_label 헬퍼도 함께 제거됐다 (사용처 소멸).
    """
    # (a) 구 배지 자리 = 우상단 [_OUT-58.._OUT-8, 8..34] 근방 — 브랜드 픽셀 0.
    img = fz._mark(
        fz._full_frame_fit(np.zeros((64, 64, 3), dtype=np.uint8)), circle=False
    )
    for x in range(fz._OUT - 58, fz._OUT - 8, 5):
        for y in range(8, 34, 5):
            assert img.getpixel((x, y)) != (255, 75, 51), "각도 배지 렌더 금지"

    assert not hasattr(fz, "_deficit_label"), "_deficit_label 제거(사용처 소멸)"

    # (b) e2e — deltas 있어도 학생 패널 우상단에 브랜드 배지 없음 + payload 유지.
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 40.0}, frames_fps=9.0,
    )
    assert comps and comps[0]["deficitDeg"] == 40.0, "deficitDeg 데이터는 방출 유지"
    import io

    from PIL import Image as _I

    png = _I.open(io.BytesIO(comps[0]["png"]))
    # 합성 이미지 = [학생|기준] 가로 병치 — 학생 패널 우상단 검사.
    for x in range(fz._OUT - 58, fz._OUT - 8, 5):
        for y in range(8, 34, 5):
            assert png.getpixel((x, y)) != (255, 75, 51), "e2e 각도 배지 없음"


# ─────────── quick-260704-fz4 — select_advisory_joints (advisory tier 선별) ───────────
# advisory = 측정 초과("참고·확인 권장") — 표시 전용, 채점 입력 금지
# ([[window-median-silent-seed-fp-reverted]]).


def test_advisory_selects_only_over_tolerance():
    """|delta| > tol 만 선별 — 21° 포함 / 19° 제외 / 경계값 20° 제외 (strict >)."""
    kp = {"left_shoulder": 21.0, "right_shoulder": 19.0, "left_hip": 20.0}
    assert fz.select_advisory_joints(kp, set(), 20.0) == ["left_shoulder"]


def test_advisory_excludes_confirmed_joints():
    """확정(fault_joints) 관절은 advisory 에서 제외 — 겹치면 확정이 이긴다."""
    kp = {"left_shoulder": 30.0, "right_shoulder": 25.0}
    assert fz.select_advisory_joints(kp, {"left_shoulder"}, 20.0) == [
        "right_shoulder"
    ]


def test_advisory_sorted_desc_and_capped():
    """|delta| 내림차순 + max_items cap (캐러셀 과밀 방지 기본 2장)."""
    kp = {"left_knee": 21.0, "left_shoulder": 40.0, "right_shoulder": 30.0}
    assert fz.select_advisory_joints(kp, set(), 20.0, max_items=2) == [
        "left_shoulder", "right_shoulder",
    ]
    assert fz.select_advisory_joints(kp, set(), 20.0, max_items=1) == [
        "left_shoulder",
    ]


def test_advisory_negative_delta_uses_abs():
    """signed delta 도 |delta| 로 판정 (기준보다 큰/작은 방향 무관 측정 초과)."""
    assert fz.select_advisory_joints({"left_hip": -35.0}, set(), 20.0) == [
        "left_hip"
    ]


def test_advisory_nonfinite_and_invalid_skipped_gracefully():
    """nan/None/문자열 delta 는 defensive skip — 빈 입력도 graceful."""
    kp = {"a": float("nan"), "b": None, "c": "oops", "d": 25.0}
    assert fz.select_advisory_joints(kp, set(), 20.0) == ["d"]
    assert fz.select_advisory_joints({}, set(), 20.0) == []
    assert fz.select_advisory_joints(None, set(), 20.0) == []


# ─────────── quick-260705-ftn — select_confident_frame (표시 프레임 선택) ───────────
# window median 이 keypoint 붕괴 구간이면 relaxed/full 강하로 카드가 망가짐
# (2026-07-05 pod 재현: ref-kip-up frame 37). 측정-표시 정합은 window 안에서
# 유지하면서 신뢰 프레임을 고른다 — 표시 전용, 채점/veto/게이트 무접촉.


def _report_conf_seq(n: int, fps: float, joint_conf_seq: dict[str, list]) -> dict:
    """per-joint per-frame confidence 지정 합성 keypointReport (nan 허용)."""
    joints = list(joint_conf_seq)
    data: list[float] = []
    conf: list[float] = []
    for f in range(n):
        for j in joints:
            data += [0.5, 0.5]
            conf.append(joint_conf_seq[j][f])
    return {
        "joints": joints, "frames": n, "fps": fps, "data": data,
        "confidence": conf,
    }


def test_select_confident_frame_picks_max_conf_not_median():
    """candidates [3,4,5] 중 median(4)=0.1 이 아니라 conf 최대(3)=0.9 를 고른다."""
    conf = [0.5] * 9
    conf[3], conf[4], conf[5] = 0.9, 0.1, 0.5
    rep = _report_conf_seq(9, 9.0, {"left_knee": conf})
    assert fz.select_confident_frame(rep, [3, 4, 5], ["left_knee"]) == 3

    # 결정론 tie-break — 동점(3,5 모두 0.9)이면 sorted 오름차순 첫 인덱스.
    conf2 = [0.5] * 9
    conf2[3], conf2[4], conf2[5] = 0.9, 0.1, 0.9
    rep2 = _report_conf_seq(9, 9.0, {"left_knee": conf2})
    assert fz.select_confident_frame(rep2, [5, 3, 4], ["left_knee"]) == 3


def test_select_confident_frame_legacy_median_fallback():
    """confidence 부재 report → sorted(candidates) median (기존 pipeline 동작 보존)."""
    rep = _report(9, 9.0)  # confidence 키 없음 = legacy
    assert fz.select_confident_frame(rep, [5, 3, 4], ["left_knee"]) == 4


def test_select_confident_frame_edges():
    """빈 candidates → None / 전원 비정수 → None / 멤버 일부 conf None 은 나머지 평균."""
    rep = _report(9, 9.0)
    assert fz.select_confident_frame(rep, [], ["left_knee"]) is None
    assert fz.select_confident_frame(rep, ["x", None], ["left_knee"]) is None

    # left_hip conf 전 프레임 nan(None 취급) → left_knee conf 만으로 평균.
    knee = [0.5] * 9
    knee[2], knee[6] = 0.2, 0.8
    hip = [float("nan")] * 9
    rep2 = _report_conf_seq(9, 9.0, {"left_knee": knee, "left_hip": hip})
    assert fz.select_confident_frame(
        rep2, [2, 6], ["left_knee", "left_hip"]
    ) == 6


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


# ─────────── quick-260705-r6x — legs 사이각 드로잉 (선 2 + 호 + 수치) ───────────
# belle 2026-07-05 실기기: "다리에 동그라미가 아니라 다리와 다리 사이각을 표시".
# 스플릿(legs) valid 측에 골반 중점→양 다리 선 + 사이각 호. 채점 무접촉(display).

_LEGS_XY = {
    "left_hip": (0.4, 0.4), "right_hip": (0.6, 0.4),
    "left_knee": (0.3, 0.7), "right_knee": (0.7, 0.7),
}


def _report_pos_conf(
    n: int,
    fps: float,
    joint_xy: dict[str, tuple[float, float]],
    joint_conf: dict[str, float] | None = None,
) -> dict:
    """per-joint 위치/confidence 지정 합성 keypointReport (사이각 드로잉 테스트)."""
    joints = list(joint_xy)
    data: list[float] = []
    for _f in range(n):
        for j in joints:
            data += list(joint_xy[j])
    rep = {"joints": joints, "frames": n, "fps": fps, "data": data}
    if joint_conf is not None:
        conf: list[float] = []
        for _f in range(n):
            for j in joints:
                conf.append(joint_conf.get(j, 0.9))
        rep["confidence"] = conf
    return rep


def _spy_mark(monkeypatch):
    calls: list[tuple[bool, tuple[int, int] | None]] = []
    orig = fz._mark

    def spy(img, circle=True, anchor_px=None):
        calls.append((circle, anchor_px))
        return orig(img, circle=circle, anchor_px=anchor_px)

    monkeypatch.setattr(fz, "_mark", spy)
    return calls


def _spy_leg_angle(monkeypatch):
    calls: list[tuple] = []

    def spy(img, pelvis_px, left_px, right_px):
        calls.append((pelvis_px, left_px, right_px))
        return True  # 그렸다고 가정 (드로잉 분기 검증 — 실 픽셀은 Test 7)

    monkeypatch.setattr(fz, "_draw_leg_angle", spy)
    return calls


def test_leg_line_pts_pure():
    """Test 1: hips 중점 + ankle 우선/knee 폴백 + hip 결측/저신뢰/conf부재 → None."""
    xy = {
        **_LEGS_XY,
        "left_ankle": (0.35, 0.95), "right_ankle": (0.65, 0.95),
    }
    # 명시적 고신뢰(전원 0.9) — 사이각 드로잉 게이트는 conf 증명 필수.
    pelvis, left_end, right_end = fz._leg_line_pts(
        _report_pos_conf(1, 9.0, xy, {}), 0
    )
    assert pelvis == (0.5, 0.4), "골반 = hips 중점"
    assert left_end == (0.35, 0.95) and right_end == (0.65, 0.95), "ankle 우선"

    # ankle 저신뢰 → knee 폴백.
    rep2 = _report_pos_conf(1, 9.0, xy, {"left_ankle": 0.1, "right_ankle": 0.1})
    _p, le, re = fz._leg_line_pts(rep2, 0)
    assert le == (0.3, 0.7) and re == (0.7, 0.7), "저신뢰 ankle → knee 폴백"

    # hip 한쪽 저신뢰 → None.
    assert fz._leg_line_pts(
        _report_pos_conf(1, 9.0, xy, {"left_hip": 0.1}), 0
    ) is None
    # hip 결측 → None.
    assert fz._leg_line_pts(
        _report_pos_conf(
            1, 9.0, {"left_knee": (0.3, 0.7), "right_knee": (0.7, 0.7)}, {}
        ),
        0,
    ) is None
    # confidence 부재(legacy report) → None — crop 게이트(부재=통과)와 달리
    # 사이각 드로잉은 신뢰 증명 필수 (2026-07-05 pod PNG: confidence 없는
    # reference report 가 통과해 몸과 무관한 방향으로 선 폭주 — 재발 방지 가드).
    assert fz._leg_line_pts(_report_pos_conf(1, 9.0, xy), 0) is None


def test_legs_valid_side_draws_angle(monkeypatch):
    """Test 2: 게이트 B — legs valid + split_angle_present → user 측만 사이각 1회.

    2026-07-05 belle 승인: 정은지(ref) 측은 kip-up 도립 pose 부정확으로 선이
    폭주(pose 한계)해 그리지 않는다. 학생 측만 _draw_leg_angle 1회 + user
    _mark circle=False(원 생략). ref 는 _mark 없음(선 없는 crop).
    """
    leg_calls = _spy_leg_angle(monkeypatch)
    mark_calls = _spy_mark(monkeypatch)
    frames = _frames(9, h=400, w=400)
    rep = _report_pos_conf(9, 9.0, _LEGS_XY, {})  # 명시적 고신뢰 0.9
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, rep, rep, worst_seconds=0.5,
        fault_joints=list(_LEGS_XY), joint_deltas={j: 20.0 for j in _LEGS_XY},
        frames_fps=9.0, joint_kinds={j: "deficit" for j in _LEGS_XY},
        split_angle_present=True,
    )
    assert len(comps) == 1 and comps[0]["region"] == "legs"
    assert len(leg_calls) == 1, "게이트 B: user 측만 사이각(ref 측 미드로잉)"
    assert mark_calls == [(False, None)], "user 원 생략, ref 는 _mark 없음"


def test_legs_split_angle_degs_ignored_no_numbers(monkeypatch):
    """Test 3 (2026-07-28 개정): split_angle_degs 는 렌더에 미사용 — 수치 없는 선+호만.

    belle "각도 배지는 빼고 초 표기로" — 구 3a/3b(수치 전달 검증)를 대체한다.
    split_angle_degs 가 있든(130,170) 없든(None) 드로잉 호출은 동일 1회이고
    각도 수치는 어떤 값도 전달되지 않는다 (파라미터는 app.py 호출 호환으로만
    잔존). 선+호 시각 언어는 유지 (2026-07-05 belle 승인 사항 보존).
    """
    leg_calls = _spy_leg_angle(monkeypatch)
    frames = _frames(9, h=400, w=400)
    rep = _report_pos_conf(9, 9.0, _LEGS_XY, {})  # 명시적 고신뢰 0.9
    for degs in ((130.0, 170.0), None):
        fz.build_fault_zoom_comparisons(
            frames, frames, rep, rep, worst_seconds=0.5,
            fault_joints=list(_LEGS_XY), joint_deltas=None, frames_fps=9.0,
            joint_kinds={j: "deficit" for j in _LEGS_XY},
            split_angle_degs=degs, split_angle_present=True,
        )
    assert len(leg_calls) == 2, "degs 유무 무관 user 측 1회씩 드로잉(동작 동일)"
    assert all(len(c) == 3 for c in leg_calls), "각도 수치 미전달(3점 좌표만)"


def test_legs_low_conf_ref_side_no_angle(monkeypatch):
    """Test 4: 게이트 B — ref 측은 신뢰와 무관하게 무조건 미드로잉, user 측만."""
    leg_calls = _spy_leg_angle(monkeypatch)
    frames = _frames(9, h=400, w=400)
    user_rep = _report_pos_conf(9, 9.0, _LEGS_XY, {})  # 명시적 고신뢰 0.9
    ref_rep = _report_pos_conf(9, 9.0, _LEGS_XY, {j: 0.1 for j in _LEGS_XY})
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep, worst_seconds=0.5,
        fault_joints=list(_LEGS_XY), joint_deltas=None, frames_fps=9.0,
        joint_kinds={j: "deficit" for j in _LEGS_XY},
        split_angle_present=True,
    )
    assert len(comps) == 1
    assert len(leg_calls) == 1, "게이트 B: ref 측 무조건 미드로잉(user 측만)"


def test_legs_conf_absent_ref_side_no_angle(monkeypatch):
    """Test 4b: 게이트 B — ref confidence 부재(legacy report)도 무조건 미드로잉.

    2026-07-05 belle pod PNG 검증: confidence 없는 reference report 는 crop
    게이트(부재=통과)로 kind='valid' 가 되지만, 좌표 신뢰가 증명되지 않아 선이
    몸과 무관한 방향으로 폭주했다. 게이트 B 로 ref 측은 조건과 무관하게 항상
    생략 — legacy 측은 기존 렌더 그대로(카드 유지, 드로잉만 생략).
    """
    leg_calls = _spy_leg_angle(monkeypatch)
    frames = _frames(9, h=400, w=400)
    user_rep = _report_pos_conf(9, 9.0, _LEGS_XY, {})  # 명시적 고신뢰 0.9
    ref_rep = _report_pos_conf(9, 9.0, _LEGS_XY)  # confidence 키 자체 부재
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep, worst_seconds=0.5,
        fault_joints=list(_LEGS_XY), joint_deltas=None, frames_fps=9.0,
        joint_kinds={j: "deficit" for j in _LEGS_XY},
        split_angle_present=True,
    )
    assert len(comps) == 1
    assert len(leg_calls) == 1, "게이트 B: ref 측 무조건 미드로잉(user 측만)"


def test_legs_no_split_record_keeps_circle(monkeypatch):
    """Test 4-A: 게이트 A — split_angle_present 기본 False → legs 카드도 사이각 미진입.

    스플릿 아닌 legs 결함(무릎 leg_extension / 골반 hip)은 사이각을 그리지 않고
    r6x 이전 circle 렌더로 복귀한다 (2026-07-05 belle pod 전동작 검증:
    power-spin=leg_extension+hip, elbow-twist=hip+knee 오적용 회귀 방지 가드).
    """
    leg_calls = _spy_leg_angle(monkeypatch)
    mark_calls = _spy_mark(monkeypatch)
    frames = _frames(9, h=400, w=400)
    rep = _report_pos_conf(9, 9.0, _LEGS_XY, {})  # 명시적 고신뢰 0.9
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, rep, rep, worst_seconds=0.5,
        fault_joints=list(_LEGS_XY), joint_deltas={j: 20.0 for j in _LEGS_XY},
        frames_fps=9.0, joint_kinds={j: "deficit" for j in _LEGS_XY},
    )  # split_angle_present 미지정(기본 False)
    assert len(comps) == 1 and comps[0]["region"] == "legs"
    assert leg_calls == [], "게이트 A: split record 없는 legs = 사이각 미드로잉"
    assert mark_calls and mark_calls[0][0] is True, "스플릿 아닌 legs = 기존 circle 복귀"


def test_has_split_angle_record_pure():
    """Test 4-B: has_split_angle_record — 존재 판정(수치 유무와 분리).

    2026-07-05 belle pod 전동작 검증: kip-up reference_relative 경로는 수치가
    None(편차라 벌림각 아님)이지만 사이각 자체는 의미 있어 True. 수치 추출
    (split_angle_degs_from_records)과 존재 판정을 분리한다.
    """
    # reference_relative split(수치 None 경로)도 존재 판정 True.
    assert fz.has_split_angle_record(
        [{"criterion": "split_angle", "unit": "deg", "measuredValue": 50.0,
          "deviationSource": "reference_relative"}]
    ) is True
    # ipsf_absolute split → True.
    assert fz.has_split_angle_record(
        [{"criterion": "split_angle", "unit": "deg", "measuredValue": 132.0,
          "deviationSource": "ipsf_absolute"}]
    ) is True
    # line-only record → False.
    assert fz.has_split_angle_record([{"criterion": "line", "unit": "deg"}]) is False
    # unit != 'deg' → False.
    assert fz.has_split_angle_record(
        [{"criterion": "split_angle", "unit": "ratio", "measuredValue": 1.0}]
    ) is False
    # None / 비리스트 / 빈 리스트 → graceful False.
    assert fz.has_split_angle_record(None) is False
    assert fz.has_split_angle_record("nope") is False
    assert fz.has_split_angle_record([]) is False


def test_pt_in_crop_pure():
    """Test 4c-i: crop-포함 판정은 clamp 전 raw 픽셀로 (경계 밖 = False)."""
    # frame 400x400, crop box (left56, top76, side288) — 표준 legs crop.
    assert fz._pt_in_crop((0.5, 0.55), 56, 76, 288, 400, 400) is True
    # hip 이 crop 위로(y0.0)이고 crop 은 하단만(top280,side100) → raw ay ≪ 0 → 밖.
    assert fz._pt_in_crop((0.5, 0.0), 150, 280, 100, 400, 400) is False
    # 경계 살짝 밖(마진 내, x0.9 → raw ax≈380 ≤ 396)은 허용 — rounding 관용.
    assert fz._pt_in_crop((0.9, 0.5), 56, 76, 288, 400, 400) is True
    # 명백히 밖(x1.0 → raw ax≈430 > 396) → False.
    assert fz._pt_in_crop((1.0, 0.5), 56, 76, 288, 400, 400) is False


def test_draw_side_leg_angle_skips_when_hip_outside_crop(monkeypatch):
    """Test 4c-ii: 드로잉 keypoint 가 crop 밖(hip 이 crop 위) → 그 측 사이각 생략.

    2026-07-05 belle pod 좌표 특정: 정은지 ref-kip-up 프레임에서 legs conf 는
    0.55~0.80 으로 게이트 통과했으나 crop 이 정강이 하단만 잘라 hip(선 시작점)이
    crop 밖 → clamp 로 선이 몸과 무관하게 폭주. crop-포함 게이트로 그 측 생략.
    """
    leg_calls = _spy_leg_angle(monkeypatch)
    from PIL import Image as _I

    img = _I.new("RGB", (fz._OUT, fz._OUT), (0, 0, 0))
    frame = _frames(1, h=400, w=400)[0]
    # hips 상단(y0.1, conf 0.7 통과), 다리 끝 하단(y0.9). 자세=다리 모음(스플릿 아님).
    xy = {
        "left_hip": (0.45, 0.1), "right_hip": (0.55, 0.1),
        "left_knee": (0.4, 0.9), "right_knee": (0.6, 0.9),
    }
    rep = _report_pos_conf(1, 9.0, xy, {j: 0.7 for j in xy})
    # crop box = 하단만(top280,side100) → hip(y0.1=40px) 이 crop 위로 벗어남.
    assert fz._draw_side_leg_angle(img, frame, rep, 0, (150, 280, 100)) is False
    assert leg_calls == [], "crop 밖 hip → 사이각 드로잉 생략(폴백)"

    # 대조(regression): hip 을 포함하는 큰 crop → 정상 드로잉 (게이트 통과).
    assert fz._draw_side_leg_angle(img, frame, rep, 0, (0, 0, 400)) is True
    assert len(leg_calls) == 1, "crop 이 3점 전부 포함하면 그린다"


# ── quick-260731-f5h D-1 — 다리 끝점 crop 인지 선택 (deferred 2안) ──────────────
# 근본원인(quick-260730-l7t deferred D-1, 실측 확정): crop 멤버 집합
# (REGION_MEMBERS["legs"] = hips+knees, **ankle 없음**)과 드로잉 점 집합
# (_leg_line_pts = ankle 우선)이 어긋나, 12관절 doc 에서 벌림이 큰 스플릿일수록
# ankle 이 crop 밖 → _pt_in_crop 게이트 탈락 → 사이각이 통째로 생략됐다.
# 아래 두 테스트는 **단조 추가 계약 6행**을 각각 가른다 (수치 채우기 금지).

_D1_LEGS_XY = {
    **_LEGS_XY,
    "left_ankle": (0.35, 0.95), "right_ankle": (0.65, 0.95),
}


def test_leg_line_pts_crop_aware_endpoint_selection():
    """계약 1·2·3·4·6행 + 기본값 계약 — in_crop 술어 주입으로 선택 로직만 가른다.

    술어는 좌표만 받는 순수 함수라 crop 기하 없이 각 행을 독립으로 세울 수 있다
    (실 box 배선은 test_draw_side_leg_angle_uses_knee_when_ankle_outside_crop).
    """
    rep = _report_pos_conf(1, 9.0, _D1_LEGS_XY, {})  # 전원 고신뢰 0.9

    # 계약 1행 — crop 이 전부 담으면 종전대로 ankle. (지금 그려지는 것은 그대로)
    _p, le, re_ = fz._leg_line_pts(rep, 0, in_crop=lambda _xy: True)
    assert le == (0.35, 0.95) and re_ == (0.65, 0.95), "crop 안이면 ankle 유지"

    # 계약 2행 — ankle 만 crop 밖(y>=0.85 배제) → knee 폴백. None 아님.
    #   ← 이 수리의 전부. 종전에는 ankle 이 선택돼 호출측 게이트에서 탈락했다.
    _p, le, re_ = fz._leg_line_pts(rep, 0, in_crop=lambda xy: xy[1] < 0.85)
    assert le == (0.3, 0.7) and re_ == (0.7, 0.7), "crop 밖 ankle → knee 폴백"

    # 계약 6행 — 왼 ankle 만 배제 → 그 측만 knee, 반대측은 ankle (측별 독립).
    _p, le, re_ = fz._leg_line_pts(
        rep, 0, in_crop=lambda xy: not (xy[1] >= 0.85 and xy[0] < 0.5)
    )
    assert le == (0.3, 0.7), "왼측만 crop 밖 → 왼측 knee"
    assert re_ == (0.65, 0.95), "오른측은 crop 안 → ankle 유지"

    # 계약 4행 — ankle·knee 둘 다 crop 밖 → None (미드로잉 유지).
    assert fz._leg_line_pts(rep, 0, in_crop=lambda xy: xy[1] < 0.6) is None

    # 기본값 계약 — in_crop 미지정(2-인자 호출)이면 ankle 이 어디 있든 ankle.
    # 기존 호출부(phase33/test_criterion_vertex_crop.py 포함) 거동 불변.
    _p, le, re_ = fz._leg_line_pts(rep, 0)
    assert le == (0.35, 0.95) and re_ == (0.65, 0.95), "기본값 = 종전 ankle 우선"

    # 계약 3행 — ankle 부재(8관절 doc) + in_crop 지정 → 종전대로 knee.
    rep8 = _report_pos_conf(1, 9.0, _LEGS_XY, {})
    _p, le, re_ = fz._leg_line_pts(rep8, 0, in_crop=lambda _xy: True)
    assert le == (0.3, 0.7) and re_ == (0.7, 0.7), "8관절 doc 거동 불변"


def test_draw_side_leg_angle_uses_knee_when_ankle_outside_crop(monkeypatch):
    """실 crop box 배선 — 끝점이 crop 기하에 따라 knee/ankle 로 갈린다 (계약 1·2·5).

    box 는 `_side_crop` 이 반환하는 그 (left, top, side) 형식이고, 포함 판정은
    프로덕션 `_pt_in_crop` 단일 출처가 한다 — 마진을 테스트에 복제하지 않는다.
    """
    leg_calls = _spy_leg_angle(monkeypatch)
    from PIL import Image as _I

    img = _I.new("RGB", (fz._OUT, fz._OUT), (0, 0, 0))
    frame = _frames(1, h=400, w=400)[0]
    # hips·knees 는 box 안, ankle 만 box 아래로 크게 벗어난 12관절 형상.
    xy = {
        "left_hip": (0.45, 0.35), "right_hip": (0.55, 0.35),
        "left_knee": (0.35, 0.60), "right_knee": (0.65, 0.60),
        "left_ankle": (0.25, 0.95), "right_ankle": (0.75, 0.95),
    }
    rep = _report_pos_conf(1, 9.0, xy, {})
    tight = (100, 100, 200)   # ankle 만 밖 (y 상한 0.80)
    wide = (0, 0, 400)        # ankle 까지 담음

    # 전제 — 같은 형상에서 box 만으로 ankle 포함 여부가 갈린다 (프로덕션 술어).
    assert fz._pt_in_crop((0.25, 0.95), *tight, 400, 400) is False
    assert fz._pt_in_crop((0.35, 0.60), *tight, 400, 400) is True
    assert fz._pt_in_crop((0.25, 0.95), *wide, 400, 400) is True

    # 계약 2행 — ankle 이 crop 밖이어도 그린다. 끝점은 **knee 파생**.
    assert fz._draw_side_leg_angle(img, frame, rep, 0, tight) is True
    assert len(leg_calls) == 1, "crop 밖 ankle 은 knee 로 대체 — 미드로잉 아님"
    _pelvis, lpx, rpx = leg_calls[0]
    assert lpx == fz._to_crop_px((0.35, 0.60), *tight, 400, 400)
    assert rpx == fz._to_crop_px((0.65, 0.60), *tight, 400, 400)
    assert lpx != fz._to_crop_px((0.25, 0.95), *tight, 400, 400), "ankle 픽셀 아님"

    # 계약 1행(대조) — ankle 까지 담는 box 면 끝점이 **ankle 파생**.
    assert fz._draw_side_leg_angle(img, frame, rep, 0, wide) is True
    assert len(leg_calls) == 2
    _pelvis, lpx2, rpx2 = leg_calls[1]
    assert lpx2 == fz._to_crop_px((0.25, 0.95), *wide, 400, 400)
    assert rpx2 == fz._to_crop_px((0.75, 0.95), *wide, 400, 400)

    # 계약 5행 — 골반이 box 밖이면 끝점이 전부 crop 안이어도 미드로잉(폴백 유지).
    xy_hi = {**xy, "left_hip": (0.45, 0.10), "right_hip": (0.55, 0.10),
             "left_knee": (0.40, 0.70), "right_knee": (0.60, 0.70),
             "left_ankle": (0.38, 0.90), "right_ankle": (0.62, 0.90)}
    rep_hi = _report_pos_conf(1, 9.0, xy_hi, {})
    low_box = (150, 280, 100)
    assert fz._pt_in_crop((0.38, 0.90), *low_box, 400, 400) is True, "끝점은 안"
    assert fz._pt_in_crop((0.5, 0.10), *low_box, 400, 400) is False, "골반은 밖"
    assert fz._draw_side_leg_angle(img, frame, rep_hi, 0, low_box) is False
    assert len(leg_calls) == 2, "골반 crop 밖 → 드로잉 0 (폴백)"


def test_non_legs_cards_no_leg_angle(monkeypatch):
    """Test 5: non-legs(arms grouped) → 사이각 0회, _mark 기존 circle=True 규칙."""
    leg_calls = _spy_leg_angle(monkeypatch)
    mark_calls = _spy_mark(monkeypatch)
    arms = {
        "left_shoulder": (0.3, 0.3), "right_shoulder": (0.7, 0.3),
        "left_elbow": (0.3, 0.7), "right_elbow": (0.7, 0.7),
    }
    frames = _frames(9, h=400, w=400)
    rep = _report_pos_conf(9, 9.0, arms)
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, rep, rep, worst_seconds=0.5,
        fault_joints=list(arms), joint_deltas={j: 20.0 for j in arms},
        frames_fps=9.0, joint_kinds={j: "deficit" for j in arms},
    )
    assert len(comps) == 1 and comps[0]["region"] == "arms"
    assert leg_calls == [], "non-legs 카드는 사이각 드로잉 미호출"
    assert mark_calls and mark_calls[0][0] is True, "non-legs = 기존 circle 규칙"


def test_split_angle_degs_from_records_pure():
    """Test 6: 벌림각 semantics(ipsf_absolute)만 수치화 + 기준 측 항상 생략.

    2026-07-05 belle pod PNG 검증 fix: 현행 split_vs_reference record 는
    reference_relative(measuredValue=정은지-대비 편차 50, baselineValue=0) —
    그대로 표기하면 학생 라벨이 deficit(50°)로, 기준 라벨이 0°로 오표기됐다.
    벌림각 semantics 인 ipsf_absolute record 의 measuredValue(=180−deficit,
    추정 학생 벌림각)만 학생 측에 표기하고, 기준 측은 baselineValue(180)가
    IPSF 목표치지 정은지 실측각이 아니므로 항상 생략한다.
    """
    recs = [
        {"criterion": "line", "unit": "deg", "measuredValue": 5.0,
         "baselineValue": 0.0, "deviationSource": "ipsf_absolute"},
        {"criterion": "split_angle", "unit": "deg", "measuredValue": 132.0,
         "baselineValue": 180.0, "deviationSource": "ipsf_absolute"},
    ]
    assert fz.split_angle_degs_from_records(recs) == (132.0, None), (
        "학생=measuredValue(벌림각), 기준=생략(180 은 실측각 아님)"
    )
    # reference_relative(현행 vision-주입 kip-up 경로) — measured=편차 50 은
    # 벌림각이 아님 → 전체 None (수치 생략, 선+호만). pod 재현 record 형상.
    assert fz.split_angle_degs_from_records(
        [{"criterion": "split_angle", "unit": "deg", "measuredValue": 50.0,
          "baselineValue": 0.0, "deviationSource": "reference_relative"}]
    ) is None
    # deviationSource 부재(미상 출처) → 수치 생략 (defensive).
    assert fz.split_angle_degs_from_records(
        [{"criterion": "split_angle", "unit": "deg", "measuredValue": 132.0,
          "baselineValue": 180.0}]
    ) is None
    # criterion 불일치만 → None.
    assert fz.split_angle_degs_from_records(
        [{"criterion": "line", "unit": "deg"}]
    ) is None
    # unit 불일치 → skip → None.
    assert fz.split_angle_degs_from_records(
        [{"criterion": "split_angle", "unit": "ratio", "measuredValue": 1.0,
          "baselineValue": 1.0, "deviationSource": "ipsf_absolute"}]
    ) is None
    # 비유한 measuredValue → None (표기할 벌림각 없음).
    assert fz.split_angle_degs_from_records(
        [{"criterion": "split_angle", "unit": "deg",
          "measuredValue": float("nan"), "baselineValue": 180.0,
          "deviationSource": "ipsf_absolute"}]
    ) is None
    # records None/비리스트/빈 → graceful.
    assert fz.split_angle_degs_from_records(None) is None
    assert fz.split_angle_degs_from_records("nope") is None
    assert fz.split_angle_degs_from_records([]) is None


def test_draw_leg_angle_pixels_and_degenerate():
    """Test 7: 실 픽셀 smoke — 두 선 위 브랜드색 + 수치 라벨 부재 + degenerate 폴백.

    2026-07-28 belle "각도 배지는 빼고": 구 각도 수치 라벨(호 이등분 방향
    r+12 지점 배지)이 그려지지 않음을 픽셀로 못 박는다 — 이 기하(골반 180,80 /
    다리 끝 y300)에서 구 라벨 중심은 (180,142)였다.
    """
    from PIL import Image as _I

    img = _I.new("RGB", (fz._OUT, fz._OUT), (0, 0, 0))
    assert fz._draw_leg_angle(img, (180, 80), (80, 300), (280, 300)) is True
    # 두 선(골반→왼/오른) 중점 픽셀 = 브랜드색.
    assert img.getpixel((130, 190)) == fz._BRAND, "골반→왼 다리 선"
    assert img.getpixel((230, 190)) == fz._BRAND, "골반→오른 다리 선"
    # 구 수치 라벨 자리(호 아래 중앙) = 무드로잉 (선/호 경로 밖 좌표).
    assert img.getpixel((180, 142)) == (0, 0, 0), "각도 수치 라벨 없음"

    # degenerate — 벡터 길이 < _MIN_LEG_VEC_PX → 드로잉 없이 원본 반환.
    img2 = _I.new("RGB", (fz._OUT, fz._OUT), (0, 0, 0))
    assert fz._draw_leg_angle(img2, (100, 100), (103, 100), (280, 300)) is False
    assert img2.getpixel((100, 100)) == (0, 0, 0), "degenerate = 원본 유지"


# ─── 관절별 프레임 선택 (faultzoom-same-frame-crops fix) ───────────────────────
# windowMedianAngleDeltas.sourceFrameIndices 는 worst-pose 중심 ±window 공용 리스트
# (관절별 데이터 아님). 종전엔 호출측이 select_confident_frame(전 fault_joints)로
# 이 window 를 단일 프레임으로 뭉개 넘겨 모든 카드가 같은 프레임(§6.6 재발 버그).
# fix: window 를 candidates 로 넘기고 build 루프가 unit 멤버 confidence 최대 프레임을
# 카드마다 독립 선택 → 카드별 프레임 상이. 채점 무접촉(deductionBreakdown 불변).


def _report_perframe_conf(n: int, fps: float, joints, conf_by_joint):
    """joint 별로 프레임마다 다른 confidence 를 심은 합성 report.

    conf_by_joint[joint] = [프레임별 conf ...] (길이 n). data 는 전부 중앙(0.5).
    confidence flat layout = T*J (frame-major, conf[fi*nj + j]).
    """
    nj = len(joints)
    data: list[float] = []
    conf: list[float] = []
    for fi in range(n):
        for j, jn in enumerate(joints):
            data += [0.5, 0.5]
            conf.append(float(conf_by_joint[jn][fi]))
    return {
        "joints": list(joints), "frames": n, "fps": fps,
        "data": data, "confidence": conf,
    }


def test_per_joint_candidates_select_different_frames():
    """관절별 confidence peak 시점이 다르면 카드마다 다른 프레임에서 잘린다."""
    joints = ["left_knee", "left_shoulder"]
    n = 10
    # knee conf peak = frame 3, shoulder conf peak = frame 7 (둘 다 >=0.5 valid).
    conf = {
        "left_knee": [0.6] * n,
        "left_shoulder": [0.6] * n,
    }
    conf["left_knee"][3] = 0.95
    conf["left_shoulder"][7] = 0.95
    user_rep = _report_perframe_conf(n, 9.0, joints, conf)
    ref_rep = _report_perframe_conf(n, 9.0, joints, conf)
    window = [3, 4, 5, 6, 7]
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n), user_rep, ref_rep,
        worst_seconds=None,  # 폴백 무의미 — candidates 가 프레임을 결정
        fault_joints=joints,
        joint_deltas={"left_knee": 20.0, "left_shoulder": 15.0},
        frames_fps=9.0,
        user_frame_candidates=window,
        ref_frame_candidates=window,
    )
    by_joint = {c["joint"]: c for c in comps}
    assert set(by_joint) == {"left_knee", "left_shoulder"}
    # 각 카드는 자기 관절 confidence 최대 프레임 (report fps==frames_fps → identity).
    assert by_joint["left_knee"]["userFrameIdx"] == 3
    assert by_joint["left_shoulder"]["userFrameIdx"] == 7
    assert by_joint["left_knee"]["refFrameIdx"] == 3
    assert by_joint["left_shoulder"]["refFrameIdx"] == 7
    # 핵심 회귀 게이트: 카드끼리 프레임이 다르다 (§6.6 "전부 같은 프레임" 재발 방지).
    assert (
        by_joint["left_knee"]["userFrameIdx"]
        != by_joint["left_shoulder"]["userFrameIdx"]
    )
    # window 선택 성공 = vision 측정 프레임 정합 → refMatch 'dtw'.
    assert by_joint["left_knee"]["refMatch"] == "dtw"


def test_candidates_none_preserves_single_frame_behavior():
    """candidates 미지정(mode3/legacy) → worst_seconds 단일 프레임 경로 100% 보존."""
    joints = ["left_knee", "left_shoulder"]
    n = 10
    conf = {"left_knee": [0.9] * n, "left_shoulder": [0.9] * n}
    user_rep = _report_perframe_conf(n, 9.0, joints, conf)
    ref_rep = _report_perframe_conf(n, 9.0, joints, conf)
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n), user_rep, ref_rep,
        worst_seconds=0.5,  # 9fps → frame 4 (양 카드 공통)
        fault_joints=joints, joint_deltas=None, frames_fps=9.0,
    )
    frames = {c["userFrameIdx"] for c in comps}
    # candidates 없으면 모든 카드가 worst_seconds 단일 프레임 (종전 동작).
    assert len(frames) == 1


def test_candidates_fallback_when_selection_yields_no_confident_frame():
    """candidates 있으나 unit 멤버 conf 전무 → batch 기본 프레임 폴백(비크래시)."""
    # report 에 confidence 부재 → select_confident_frame 은 sorted median 폴백.
    joints = ["left_knee", "left_shoulder"]
    user_rep = _report(9, 9.0, joints=tuple(joints))  # confidence 부재(legacy)
    ref_rep = _report(9, 9.0, joints=tuple(joints))
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), user_rep, ref_rep,
        worst_seconds=0.2, fault_joints=joints,
        joint_deltas={"left_knee": 10.0, "left_shoulder": 10.0},
        frames_fps=9.0,
        user_frame_candidates=[2, 3, 4],
        ref_frame_candidates=[2, 3, 4],
    )
    # legacy conf 부재 → select 는 window median(3) 반환 → 양 카드 공통 프레임 3.
    assert all(c["userFrameIdx"] == 3 for c in comps)
    assert len(comps) == 2


# ─── 카드 내 student↔reference DTW 정렬 (NEW 서브버그, belle 2026-07-25) ────────
# belle 육안: 프레임 뭉침(전부 140)은 해소됐으나 카드 안에서 학생 패널 ↔ 정은지 패널이
# 서로 다른 동작 순간("정은지 쪽은 아예 다른 장면"). 원인: sel_r 을 ref 자기 confidence
# 로 독립 선택 → user/ref window index 어긋남. fix: 학생 가시성으로 window position 1개
# 선택 → 기준 프레임 = ref_frame_candidates[그 position] (DTW 짝). 채점 무접촉.


def test_select_confident_index_maps_value_to_position():
    """select_confident_index = select_confident_frame 값의 원본 candidates 위치."""
    conf = [0.5] * 9
    conf[3], conf[4], conf[5] = 0.9, 0.1, 0.5
    rep = _report_conf_seq(9, 9.0, {"left_knee": conf})
    # 값 선택 3 → 원본 [5,3,4] 에서 위치 1.
    assert fz.select_confident_frame(rep, [5, 3, 4], ["left_knee"]) == 3
    assert fz.select_confident_index(rep, [5, 3, 4], ["left_knee"]) == 1
    # 오름차순 candidates 면 값==원본 위치의 값 (position 0).
    assert fz.select_confident_index(rep, [3, 4, 5], ["left_knee"]) == 0
    # 빈/전원 비정수 → None (select_confident_frame 계약 계승).
    assert fz.select_confident_index(rep, [], ["left_knee"]) is None
    assert fz.select_confident_index(rep, ["x", None], ["left_knee"]) is None


def test_ref_frame_dtw_aligned_to_user_not_independent():
    """카드 내 기준 프레임 = 학생이 고른 window position 의 DTW 짝 (독립 선택 아님).

    핵심 회귀 게이트: user window 와 ref window 가 **다른 절대 프레임**(DTW 로 대응된
    서로 다른 시각)이고, ref confidence peak 이 학생과 **다른 position** 을 가리켜도,
    ref 프레임은 학생이 고른 position 의 ref 후보를 따른다 — 카드 내 두 패널이 같은
    DTW 순간. 종전 독립 선택이면 ref 는 자기 peak(position 4=frame 14)를 골랐다.
    """
    joints = ["left_knee"]
    n = 20
    # user knee conf peak = frame 3 (window position 0).
    user_conf = {"left_knee": [0.6] * n}
    user_conf["left_knee"][3] = 0.95
    # ref knee conf peak = frame 14 (window position 4) — 독립 선택이면 14 를 고를 것.
    ref_conf = {"left_knee": [0.6] * n}
    ref_conf["left_knee"][14] = 0.95
    user_rep = _report_perframe_conf(n, 9.0, joints, user_conf)
    ref_rep = _report_perframe_conf(n, 9.0, joints, ref_conf)
    user_window = [3, 4, 5, 6, 7]
    ref_window = [10, 11, 12, 13, 14]  # DTW 짝: position i ↔ user_window[i]
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n), user_rep, ref_rep,
        worst_seconds=None, fault_joints=joints,
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        user_frame_candidates=user_window,
        ref_frame_candidates=ref_window,
    )
    assert len(comps) == 1
    c = comps[0]
    # 학생이 window position 0(frame 3)을 고름 → 기준 = ref_window[0] = 10.
    assert c["userFrameIdx"] == 3
    assert c["refFrameIdx"] == 10, "ref = DTW 짝(position 0)=10, 독립선택 14 아님"
    assert c["refMatch"] == "dtw"


def test_multi_card_ref_frames_stay_dtw_aligned_per_card():
    """다관절 카드 각각에서 user/ref 가 같은 window position(DTW 짝)으로 정렬된다."""
    joints = ["left_knee", "left_shoulder"]
    n = 20
    # user: knee peak = frame 3(pos 0), shoulder peak = frame 6(pos 3).
    user_conf = {"left_knee": [0.6] * n, "left_shoulder": [0.6] * n}
    user_conf["left_knee"][3] = 0.95
    user_conf["left_shoulder"][6] = 0.95
    # ref confidence 는 어디를 가리키든 무관 — 정렬은 학생 position 을 따른다.
    ref_conf = {"left_knee": [0.9] * n, "left_shoulder": [0.9] * n}
    user_rep = _report_perframe_conf(n, 9.0, joints, user_conf)
    ref_rep = _report_perframe_conf(n, 9.0, joints, ref_conf)
    user_window = [3, 4, 5, 6, 7]
    ref_window = [12, 13, 14, 15, 16]  # position i ↔ user_window[i]
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n), user_rep, ref_rep,
        worst_seconds=None, fault_joints=joints,
        joint_deltas={"left_knee": 20.0, "left_shoulder": 15.0},
        frames_fps=9.0,
        user_frame_candidates=user_window,
        ref_frame_candidates=ref_window,
    )
    by_joint = {c["joint"]: c for c in comps}
    # knee: user pos 0 (frame 3) → ref_window[0] = 12.
    assert by_joint["left_knee"]["userFrameIdx"] == 3
    assert by_joint["left_knee"]["refFrameIdx"] == 12
    # shoulder: user pos 3 (frame 6) → ref_window[3] = 15.
    assert by_joint["left_shoulder"]["userFrameIdx"] == 6
    assert by_joint["left_shoulder"]["refFrameIdx"] == 15
    # 각 카드의 user/ref 가 같은 window position (DTW 짝) 임을 명시 검증.
    for c in comps:
        u_pos = user_window.index(c["userFrameIdx"])
        r_pos = ref_window.index(c["refFrameIdx"])
        assert u_pos == r_pos, f"{c['joint']}: user/ref 같은 window index"


# ─── 같은-포즈 기준 프레임 매칭 (belle 육안 #2, 2026-07-25) ──────────────────────
# belle: "정은지는 앞을 보는데 학생은 뒤돌아본 순간 → 이게 무슨 비교지?" DTW window
# position 정렬은 **타이밍** 대응일 뿐 **시각 국면** 대응이 아니다. 2026-07-26 실측:
# 학생 9fps 프레임 70 에 시각적으로 맞는 기준 프레임은 68 인데 DTW 짝은 73 이었고,
# 68 은 종전 후보 window(±2) 밖이라 window 내 재선택으로는 도달 불가였다.
# → anchor(DTW 짝) 주변으로 확대 탐색 + 포즈 거리 최소 선택. 판정 불가 시 anchor 유지.

# 정면(앞) 포즈와 그 좌우 반전(뒤돌아봄) — facing 판별의 최소 재현.
_POSE_JOINTS = (
    "left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee",
)
_POSE_FRONT = {
    "left_shoulder": (0.40, 0.30), "right_shoulder": (0.60, 0.30),
    "left_hip": (0.42, 0.60), "right_hip": (0.58, 0.60),
    "left_knee": (0.45, 0.85),
}
_POSE_BACK = {j: (1.0 - x, y) for j, (x, y) in _POSE_FRONT.items()}


def _report_xy(n, fps, joints, pose_of_frame, conf: float = 0.9) -> dict:
    """프레임별 관절 좌표를 직접 심은 합성 report (포즈 매칭 검증용).

    pose_of_frame(frame_idx) -> {joint: (x, y)}. conf 는 전 관절 공통.
    """
    data: list[float] = []
    confs: list[float] = []
    for fi in range(n):
        pose = pose_of_frame(fi)
        for jn in joints:
            x, y = pose[jn]
            data += [float(x), float(y)]
            confs.append(float(conf))
    return {
        "joints": list(joints), "frames": n, "fps": fps,
        "data": data, "confidence": confs,
    }


def test_pose_distance_ignores_translation_and_scale():
    """체격/카메라거리/화면위치 차이는 제거 — 같은 포즈면 거리 0."""
    a = dict(_POSE_FRONT)
    # 0.5 배 축소 + (0.2, -0.1) 평행이동 = 같은 포즈의 다른 사람/다른 촬영.
    b = {j: (0.5 * x + 0.2, 0.5 * y - 0.1) for j, (x, y) in a.items()}
    d = fz.pose_distance(a, b)
    assert d is not None and d < 1e-9, f"이동·스케일 정규화되어야 함 (got {d})"


def test_pose_distance_detects_facing_flip():
    """좌우 반전(앞/뒤 돌아봄)은 **크게** 다른 포즈로 잡혀야 한다.

    belle 지적의 핵심 신호 — 회전까지 정규화하면 이 차이가 지워지므로 하면 안 된다.
    """
    same = fz.pose_distance(_POSE_FRONT, _POSE_FRONT)
    flipped = fz.pose_distance(_POSE_FRONT, _POSE_BACK)
    assert same is not None and flipped is not None
    assert same < 1e-9
    assert flipped > 0.3, f"facing 반전이 거의 0 이면 판별 불가 (got {flipped})"


def test_pose_distance_requires_min_common_joints():
    """공통 신뢰관절 3개 이하 → None (노이즈로 프레임 옮기기 금지)."""
    a = {j: _POSE_FRONT[j] for j in list(_POSE_FRONT)[:3]}
    assert fz.pose_distance(a, _POSE_FRONT) is None
    b = {j: _POSE_FRONT[j] for j in list(_POSE_FRONT)[:4]}
    assert fz.pose_distance(b, _POSE_FRONT) is not None


def test_pose_distance_none_on_collapsed_points():
    """전 관절이 한 점에 뭉친 붕괴 프레임 → 정규화 0/0 → None."""
    collapsed = {j: (0.5, 0.5) for j in _POSE_JOINTS}
    assert fz.pose_distance(collapsed, _POSE_FRONT) is None
    assert fz.pose_distance(collapsed, collapsed) is None


def test_pose_matched_ref_frame_beats_dtw_anchor():
    """핵심 게이트 — DTW 짝이 아니라 **포즈가 닮은** 기준 프레임을 고른다.

    학생=정면. 기준은 프레임 12 만 정면이고 나머지(anchor 17 포함)는 전부 반전.
    종전 동작이면 anchor 17(반전=belle 이 지적한 '다른 장면')을 그대로 썼다.
    """
    n = 40
    user_rep = _report_xy(n, 9.0, _POSE_JOINTS, lambda _f: _POSE_FRONT)
    ref_rep = _report_xy(
        n, 9.0, _POSE_JOINTS, lambda f: _POSE_FRONT if f == 12 else _POSE_BACK
    )
    got = fz.select_pose_matched_ref_frame(
        user_rep, ref_rep, user_kp_idx=3, ref_anchor_idx=17, ref_n=n,
        frames_fps=9.0, ref_rep_fps=9.0, ref_rep_frames=n,
    )
    assert got == 12, f"포즈 일치 프레임 12 를 골라야 함 (got {got})"


def test_pose_matched_ref_frame_stays_inside_search_window():
    """탐색 반경 밖의 완벽 일치는 고르지 않는다 (DTW = 타이밍 backbone 유지).

    search_seconds 를 명시(1.2s)해 반경 불변식 자체를 검증한다 — 모듈 기본값
    (_POSE_SEARCH_SECONDS)은 실측 drift 에 따라 조정될 수 있는 값(2026-07-28
    1.2→4.0)이므로 테스트가 기본값에 결합하면 값 조정마다 오탐한다.
    9fps·1.2s → span 11 → anchor 17 의 탐색 범위 [6,28]. 완벽 일치를 2(범위 밖)에
    두면 무시하고, 범위 안은 전부 동률이므로 tie-break 로 anchor 를 유지한다.
    """
    n = 40
    user_rep = _report_xy(n, 9.0, _POSE_JOINTS, lambda _f: _POSE_FRONT)
    ref_rep = _report_xy(
        n, 9.0, _POSE_JOINTS, lambda f: _POSE_FRONT if f == 2 else _POSE_BACK
    )
    got = fz.select_pose_matched_ref_frame(
        user_rep, ref_rep, user_kp_idx=3, ref_anchor_idx=17, ref_n=n,
        frames_fps=9.0, ref_rep_fps=9.0, ref_rep_frames=n,
        search_seconds=1.2,
    )
    assert got == 17, f"범위 밖(2)을 집지 말고 동률 tie-break=anchor (got {got})"


def test_pose_matched_fires_with_low_confidence_user_joints():
    """게이트 재설계 (2026-07-27) — 학생 conf 가 낮아도(배열이 존재하면) 발동한다.

    실 fixture 실측: 역립 무릎 카드의 학생 프레임은 conf>=0.5 관절이 2개뿐이라
    strict 게이트로는 belle 수용 기준("무릎 카드도 같은 포즈 기준 패널") 자체가
    구조적으로 불가능했다. 저신뢰 좌표도 finite 면 매칭 신호로 쓰되 confidence 를
    관절 가중치로 할인한다 (Pod A/B: 3카드 발동 + knee 승자 = 육안 GT 국면)."""
    n = 40
    user_rep = _report_xy(n, 9.0, _POSE_JOINTS, lambda _f: _POSE_FRONT, conf=0.2)
    ref_rep = _report_xy(
        n, 9.0, _POSE_JOINTS, lambda f: _POSE_FRONT if f == 12 else _POSE_BACK
    )
    got = fz.select_pose_matched_ref_frame(
        user_rep, ref_rep, user_kp_idx=3, ref_anchor_idx=17, ref_n=n,
        frames_fps=9.0, ref_rep_fps=9.0, ref_rep_frames=n,
    )
    assert got == 12, f"저신뢰(0.2)여도 발동해 포즈일치 12 를 골라야 함 (got {got})"


def test_pose_matched_ref_frame_none_when_user_confidence_absent():
    """confidence 배열 부재(legacy report) → None — 가중을 세울 수 없어 이동 금지.

    저신뢰 발동(위 테스트)과 달리 신뢰도 신호 자체가 없는 좌표로 기준 프레임을
    옮기면 조용한 악화가 된다 — 종전 보수성 유지 (anchor 폴백)."""
    n = 40
    ref_rep = _report_xy(n, 9.0, _POSE_JOINTS, lambda _f: _POSE_FRONT)
    legacy = _report_xy(n, 9.0, _POSE_JOINTS, lambda _f: _POSE_FRONT)
    legacy.pop("confidence")
    assert fz.select_pose_matched_ref_frame(
        legacy, ref_rep, user_kp_idx=3, ref_anchor_idx=17, ref_n=n,
        frames_fps=9.0, ref_rep_fps=9.0, ref_rep_frames=n,
    ) is None


def test_build_ref_frame_uses_pose_match_outside_dtw_window():
    """end-to-end — 카드의 refFrameIdx 가 DTW 후보 window 밖 포즈일치 프레임이 된다.

    2026-07-26 실측 구조 재현: 시각적으로 맞는 기준 프레임이 후보 window(±2) 밖에
    있어서, window 내 재선택만으로는 도달 불가였던 상황.

    2026-07-28 (belle #3, pair-opt 궤적 매칭): 일치 프레임을 단일 스파이크가 아니라
    **plateau(9..13)** 로 둔다 — 궤적 평균(±_POSE_TRAJ_RADIUS)은 이웃까지 닮아야
    최소가 되는 설계라(환각 flicker 의 고립 최소 강등이 목적) 고립 단일프레임
    일치는 의도적으로 우승하지 못한다. plateau 중심 11 이 유일 최소.
    """
    n = 40
    joints = list(_POSE_JOINTS)
    user_rep = _report_xy(n, 9.0, joints, lambda _f: _POSE_FRONT)
    ref_rep = _report_xy(
        n, 9.0, joints, lambda f: _POSE_FRONT if 9 <= f <= 13 else _POSE_BACK
    )
    user_window = [3, 4, 5, 6, 7]
    ref_window = [15, 16, 17, 18, 19]  # DTW 짝 — 전부 반전 포즈
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n), user_rep, ref_rep,
        worst_seconds=None, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        user_frame_candidates=user_window,
        ref_frame_candidates=ref_window,
    )
    assert len(comps) == 1
    c = comps[0]
    assert c["userFrameIdx"] == 3, (
        "학생 후보 전원 동일 포즈/conf → 결정론 tie-break 로 첫 후보 유지"
    )
    assert c["refFrameIdx"] == 11, (
        f"기준 = 포즈일치 plateau 중심 11 (DTW 짝 15 아님) (got {c['refFrameIdx']})"
    )
    assert c["refMatch"] == "dtw"


def test_build_keeps_dtw_ref_when_pose_match_impossible():
    """포즈 판정 불가(좌표 붕괴) → 기준 프레임 = DTW 짝 그대로 (조용한 악화 없음).

    관절은 4개(기저 크기 게이트 통과) + 전 좌표 (0.5,0.5) 붕괴 — 코드리뷰 INFO:
    종전엔 관절 1개(<4)라 관절수 미달로 폴백해 docstring(좌표 붕괴)과 다른 분기를
    태우고 있었다. 4관절 전부 붕괴로 바꿔 실제 붕괴 분기(스케일 0 → None)를 태운다.
    """
    n = 20
    joints = ["left_knee", "left_hip", "left_shoulder", "right_shoulder"]
    conf = {j: [0.9] * n for j in joints}
    # _report_perframe_conf 는 전 좌표 (0.5,0.5) = 붕괴 → pose_distance None.
    user_rep = _report_perframe_conf(n, 9.0, joints, conf)
    ref_rep = _report_perframe_conf(n, 9.0, joints, conf)
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n), user_rep, ref_rep,
        worst_seconds=None, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        user_frame_candidates=[3, 4, 5, 6, 7],
        ref_frame_candidates=[10, 11, 12, 13, 14],
    )
    assert len(comps) == 1
    assert comps[0]["refFrameIdx"] == 10, "ea55069 DTW 짝 동작 보존"


# ─── 관절 기저 고정 (비교불가 BLOCKER, 2026-07-27) ──────────────────────────────
# 후보마다 자기 공통관절로 pose_distance 를 재면 값이 서로 다른 공간에서 나온다 —
# 이동+스케일 제거 후 남는 자유도가 관절 수에 비례해 **관절 적은 후보가 최소값
# 경쟁에서 구조적으로 이긴다** (실측: 랜덤 포즈 min 통계 k=4→0.185 vs k=8→0.486,
# ref-elbow-twist-sister 실 탐색에서 k=4 후보가 k=8 후보 전부 추월). fix = 탐색
# 1회 안에서 기저(학생 신뢰관절)를 고정, 기저 못 덮는 후보는 채점 불가로 제외.


def test_pose_distance_basis_rejects_partial_candidate():
    """기저를 못 덮는 후보 = 채점 불가(None) — 저관절 허위승리의 입구 차단.

    BLOCKER 재현(probe A): 학생 관절의 부분집합(4관절)만 가진 후보가 그 4관절의
    정확한 닮음변환 사본이면, 자동-공통관절 모드에선 거리 ~0 으로 전신 거의동일
    후보를 제쳤다. 기저 고정 후에는 채점 자체가 안 되어 추월이 불가능하다.
    """
    student = dict(_POSE_FRONT)  # 5관절
    subset = {"left_shoulder", "right_shoulder", "left_hip", "right_hip"}
    partial = {
        j: (0.5 * x + 0.2, 0.5 * y - 0.1)
        for j, (x, y) in student.items() if j in subset
    }
    # 자동 모드(단일 쌍 비교 전용)는 부분집합 교집합으로 ~0 을 낸다 — 버그의 재료.
    auto = fz.pose_distance(student, partial)
    assert auto is not None and auto < 1e-9
    # 기저 고정: 학생 5관절 기저를 못 덮음 → None (탐색에서 제외).
    assert fz.pose_distance(student, partial, basis=sorted(student)) is None


def test_pose_distance_basis_restricts_scored_joints():
    """기저가 채점 관절을 **정확히** 규정한다 — 모든 후보가 동일 공간의 값을 받는다."""
    student = dict(_POSE_FRONT)
    candidate = dict(_POSE_FRONT)
    candidate["left_knee"] = (0.95, 0.05)  # 기저 밖 관절에서만 크게 다름
    basis = ["left_shoulder", "right_shoulder", "left_hip", "right_hip"]
    auto = fz.pose_distance(student, candidate)  # 공통 5관절 → 큰 거리
    fixed = fz.pose_distance(student, candidate, basis=basis)  # 기저 4관절 → 0
    assert auto is not None and auto > 0.1
    assert fixed is not None and fixed < 1e-9


def _report_xy_conf(n, fps, joints, pose_of_frame, conf_of_frame) -> dict:
    """프레임·관절별 좌표+confidence 를 직접 심은 합성 report (기저 검증용).

    pose_of_frame(fi) -> {joint: (x, y)}, conf_of_frame(fi) -> {joint: conf}
    (누락 관절 conf 는 0.9).
    """
    data: list[float] = []
    confs: list[float] = []
    for fi in range(n):
        pose = pose_of_frame(fi)
        cmap = conf_of_frame(fi)
        for jn in joints:
            x, y = pose[jn]
            data += [float(x), float(y)]
            confs.append(float(cmap.get(jn, 0.9)))
    return {
        "joints": list(joints), "frames": n, "fps": fps,
        "data": data, "confidence": confs,
    }


def test_pose_matched_low_joint_similarity_copy_cannot_win():
    """BLOCKER 회귀 게이트 — 기저를 못 덮는 닮음사본 후보가 탐색에서 우승 불가.

    ref 프레임 12 = 학생 기저(5관절) 중 left_knee 좌표가 **결측(NaN)** + 나머지
    4관절이 학생의 정확한 닮음변환. 종전 코드(후보별 교집합)에선 거리 ~0 으로
    무조건 우승 + tie 밴드(best*1.05)가 0 으로 붕괴해 정직한 후보를 전부 배제했다.
    ref 프레임 20 = 전 관절 존재 + 학생과 거의 동일(정직한 최적).
    기저 고정 후: 12 는 채점 불가 → 20 이 이겨야 한다.

    2026-07-27 게이트 재설계 반영: 후보의 관절 커버리지는 **finite 좌표** 기준
    (ref confidence 는 매칭에 미사용 — 역립 구간 ref conf 붕괴로 게이트하면 무발동
    재발). f==12 의 left_knee conf 0.2 는 무시됨을 함께 못 박는다 — 배제는 오직
    NaN 좌표(기저 미커버)로만 일어난다.
    """
    n = 40
    joints = list(_POSE_JOINTS)
    near_pose = dict(_POSE_FRONT)
    near_pose["left_knee"] = (0.46, 0.84)  # 미세 차이 — 거리 작지만 0 아님
    sim_copy = {
        j: (0.5 * x + 0.2, 0.5 * y - 0.1) for j, (x, y) in _POSE_FRONT.items()
    }
    sim_copy["left_knee"] = (float("nan"), float("nan"))  # 기저 미커버(결측)

    def ref_pose(f):
        if f == 12:
            return sim_copy
        if f == 20:
            return near_pose
        return _POSE_BACK

    def ref_conf(f):
        if f == 12:
            return {"left_knee": 0.2}  # 무시되어야 함 (ref conf 미사용)
        return {}

    user_rep = _report_xy(n, 9.0, joints, lambda _f: _POSE_FRONT)
    ref_rep = _report_xy_conf(n, 9.0, joints, ref_pose, ref_conf)
    got = fz.select_pose_matched_ref_frame(
        user_rep, ref_rep, user_kp_idx=3, ref_anchor_idx=17, ref_n=n,
        frames_fps=9.0, ref_rep_fps=9.0, ref_rep_frames=n,
    )
    assert got == 20, (
        f"기저 미커버 닮음사본(12)이 아니라 전기저 정직 후보(20)여야 함 (got {got})"
    )


# ─── 게이트/기저 재설계 + ref 타임베이스 매핑 (2026-07-27) ──────────────────────
# 실 fixture 무발동 3갈래 실측: (a) 학생 conf>=0.5 관절 2~3개 < 4 게이트,
# (b) user 12관절 vs ref 8관절 이름공간 불일치 → 기저 커버 0. 재설계 = 기저를
# finite∩ref이름공간∩conf>0 으로, 학생 confidence 를 가중으로. 그리고 ref rep 공간
# 인덱스로 비디오 배열을 직접 인덱싱하던 타임베이스 버그(4/3 왜곡 실측)를
# ref_display_frame_index 로 교정.


def test_pose_matched_basis_restricted_to_ref_joint_namespace():
    """user 12관절 vs ref 8관절 — 기저가 이름공간 교집합으로 제한되어 발동한다.

    실측(2026-07-27): phase4_v1 ref report 는 8관절(ankle/elbow 부재)인데 학생
    report 는 12관절. 종전엔 학생 신뢰관절(ankle/elbow 포함)이 기저가 되어 ref 가
    구조적으로 못 덮음 → 무발동. 교집합 제한 후엔 공유 관절만으로 매칭한다.
    """
    n = 40
    extra = {"left_ankle": (0.44, 0.95), "right_elbow": (0.66, 0.45)}
    user_joints = list(_POSE_JOINTS) + list(extra)
    user_front = {**_POSE_FRONT, **extra}
    user_rep = _report_xy(n, 9.0, user_joints, lambda _f: user_front)
    ref_rep = _report_xy(
        n, 9.0, _POSE_JOINTS, lambda f: _POSE_FRONT if f == 12 else _POSE_BACK
    )
    got = fz.select_pose_matched_ref_frame(
        user_rep, ref_rep, user_kp_idx=3, ref_anchor_idx=17, ref_n=n,
        frames_fps=9.0, ref_rep_fps=9.0, ref_rep_frames=n,
    )
    assert got == 12, f"이름공간 교집합 기저로 발동해야 함 (got {got})"


def test_pose_distance_weights_discount_low_confidence_joints():
    """가중 거리 — 저신뢰 관절의 편차는 신뢰도만큼 할인된다 (탐색 내 가중 고정 전제)."""
    basis = sorted(_POSE_FRONT)
    moved_knee = dict(_POSE_FRONT)
    moved_knee["left_knee"] = (0.75, 0.55)  # knee 만 크게 이동
    # knee 가중 ~0 → knee 편차가 사실상 무시되어 거리 ~0.
    w_knee_dead = {j: (1e-6 if j == "left_knee" else 0.9) for j in basis}
    d_w = fz.pose_distance(_POSE_FRONT, moved_knee, basis=basis, weights=w_knee_dead)
    d_u = fz.pose_distance(_POSE_FRONT, moved_knee, basis=basis)
    assert d_u is not None and d_u > 0.1
    assert d_w is not None and d_w < 0.05, f"저가중 관절 편차는 할인 (got {d_w})"
    # 가중 합 0 / 음수 가중 → None (계산 불가 — 조용한 오답 금지).
    w_zero = {j: 0.0 for j in basis}
    assert fz.pose_distance(_POSE_FRONT, moved_knee, basis=basis, weights=w_zero) is None
    w_neg = {j: (-0.5 if j == "left_knee" else 0.9) for j in basis}
    assert fz.pose_distance(_POSE_FRONT, moved_knee, basis=basis, weights=w_neg) is None


def test_ref_display_frame_index_timebase_mapping():
    """rep 공간 → 비디오 배열 인덱스 — 실측(4/3 왜곡) 재현 + 정합 identity 보존."""
    # 실측 재현: rep 329@18fps(9fps 환산 164.5) vs 비디오 220프레임 → 배율 4/3.
    assert fz.ref_display_frame_index(0, 220, 329, 18.0) == 0
    assert fz.ref_display_frame_index(67, 220, 329, 18.0) == 90
    assert fz.ref_display_frame_index(73, 220, 329, 18.0) == 98
    assert fz.ref_display_frame_index(163, 220, 329, 18.0) == 218
    # 정합(학생 in-run report / mode3 지난영상): rep 2N@18fps == 비디오 N → identity.
    for i in (0, 5, 9):
        assert fz.ref_display_frame_index(i, 10, 20, 18.0) == i
    # rep 메타 부재(legacy) → identity + clamp.
    assert fz.ref_display_frame_index(7, 10, 0, 18.0) == 7
    assert fz.ref_display_frame_index(99, 10, 0, 18.0) == 9
    assert fz.ref_display_frame_index(3, 0, 329, 18.0) == 0


def test_build_ref_crop_uses_timebase_mapped_video_frame():
    """end-to-end — ref 크롭이 rep 인덱스가 아니라 매핑된 비디오 프레임에서 잘린다.

    rep 10프레임@18fps(9fps 환산 5) vs 비디오 10프레임 → 배율 2. 선택된 rep 공간
    anchor 3 → 비디오 프레임 6 (_frames R채널 = idx*10 → 60). 종전 버그면 비디오
    3 (R=30). refFrameIdx(kp 공간) 방출은 불변 — 뷰어 계약 무접촉.
    """
    import io as _io

    from PIL import Image as _Img

    comps = fz.build_fault_zoom_comparisons(
        _frames(10), _frames(10), _report(10, 9.0), _report(10, 18.0),
        worst_seconds=None, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        user_frame_candidates=[1, 2, 3],
        ref_frame_candidates=[2, 3, 4],
    )
    assert len(comps) == 1
    c = comps[0]
    # 학생(legacy conf 부재) → median 후보 2 = pos 1 → ref anchor = 3 (rep 공간).
    assert c["refFrameIdx"] == 6, "kp 공간 방출 불변 (rep idx 3 → 18fps kp 6)"
    img = _Img.open(_io.BytesIO(c["png"])).convert("RGB")
    # ref 반쪽 **우하단** 픽셀 — 비디오 프레임 6 의 R=60. 좌하단은 2026-07-28
    # 타임스탬프 배지(_stamp_time, fill 40)가 덮으므로 샘플 지점을 옮겼다.
    r, _g, _b = img.getpixel((2 * fz._OUT - 12, fz._OUT - 12))
    assert r == 60, f"타임베이스 매핑된 비디오 프레임 6(R=60)이어야 함 (got R={r})"


# ── (학생, 기준) 쌍 동시 최적화 — 궤적 매칭 (belle #3, 2026-07-28) ──────────────


def _pose_displaced(joint: str, xy: tuple[float, float]) -> dict:
    """_POSE_FRONT 에서 한 관절만 xy 로 옮긴 변형 — 환각 flicker 재현용."""
    p = dict(_POSE_FRONT)
    p[joint] = xy
    return p


def test_pair_prefers_student_frame_with_best_trajectory_match():
    """conf argmax 가 아니라 **최적 궤적 짝**으로 학생 프레임을 고른다.

    실 fixture 재현 (2026-07-28): 학생 어깨 keypoint 가 kp144 에서 얼굴에 환각
    (conf 0.57)돼 conf argmax(vs 진짜 어깨 kp148 의 0.56)가 환각 프레임을 골랐다.
    합성: 후보 B(프레임 8)는 conf 가 더 높지만 어깨가 환각 위치 — 어떤 기준
    궤적과도 일치가 나빠 쌍 경쟁에서 진다. 후보 A(프레임 3, conf 낮음)가 승자.
    """
    n = 20
    joints = list(_POSE_JOINTS)
    user_rep = _report_xy_conf(
        n, 9.0, joints,
        lambda f: (
            _pose_displaced("right_shoulder", (0.45, 0.85)) if f == 8
            else _POSE_FRONT
        ),
        lambda f: {"right_shoulder": 0.99 if f == 8 else 0.6},
    )
    ref_rep = _report_xy(n, 9.0, joints, lambda _f: _POSE_FRONT)
    got = fz.select_pose_matched_pair(
        user_rep, ref_rep, [3, 8], [10, 12], ("right_shoulder",), n,
        frames_fps=9.0, user_rep_fps=9.0, user_rep_frames=n,
        ref_rep_fps=9.0, ref_rep_frames=n,
    )
    assert got is not None
    pos, r = got
    assert pos == 0, f"환각(고conf) 후보가 아니라 궤적 최적 후보 (got pos={pos})"
    assert r == 10, f"완전 동률 ref 는 anchor 유지 (got r={r})"


def test_pair_excludes_student_frames_without_valid_marker_member():
    """valid(conf>=0.5) 멤버 없는 학생 프레임은 궤적이 완벽해도 후보가 아니다.

    마커(원)는 valid 멤버에만 그려진다 — belle 이 승인한 마커가 사라지는
    프레임으로 옮기지 않는다 (marker-capable 게이트).
    """
    n = 20
    joints = list(_POSE_JOINTS)
    # 후보 B(프레임 8)는 완벽 일치지만 멤버 conf 0.3 → 제외. A(프레임 3)는
    # 살짝 어긋난 포즈(무릎만 이동)여도 valid 라 승자.
    user_rep = _report_xy_conf(
        n, 9.0, joints,
        lambda f: (
            _pose_displaced("left_knee", (0.50, 0.80)) if 1 <= f <= 5
            else _POSE_FRONT
        ),
        lambda f: {"right_shoulder": 0.3 if f == 8 else 0.9},
    )
    ref_rep = _report_xy(n, 9.0, joints, lambda _f: _POSE_FRONT)
    got = fz.select_pose_matched_pair(
        user_rep, ref_rep, [3, 8], [10, 12], ("right_shoulder",), n,
        frames_fps=9.0, user_rep_fps=9.0, user_rep_frames=n,
        ref_rep_fps=9.0, ref_rep_frames=n,
    )
    assert got is not None
    assert got[0] == 0, f"valid 멤버 없는 후보(8)는 제외돼야 함 (got pos={got[0]})"


def test_pair_none_when_no_marker_capable_candidate():
    """전 후보가 저신뢰 멤버뿐 → None → 호출측 종전 사슬 폴백."""
    n = 20
    joints = list(_POSE_JOINTS)
    user_rep = _report_xy_conf(
        n, 9.0, joints, lambda _f: _POSE_FRONT,
        lambda _f: {"right_shoulder": 0.2},
    )
    ref_rep = _report_xy(n, 9.0, joints, lambda _f: _POSE_FRONT)
    assert fz.select_pose_matched_pair(
        user_rep, ref_rep, [3, 8], [10, 12], ("right_shoulder",), n,
        frames_fps=9.0, user_rep_fps=9.0, user_rep_frames=n,
        ref_rep_fps=9.0, ref_rep_frames=n,
    ) is None


def test_pair_none_for_legacy_report_without_confidence():
    """confidence 배열 부재(legacy) → None — 신뢰 신호 없는 좌표로 쌍을 세우지
    않는다 (select_pose_matched_ref_frame 의 legacy 보수성과 동일)."""
    n = 20
    joints = list(_POSE_JOINTS)
    legacy = _report_xy(n, 9.0, joints, lambda _f: _POSE_FRONT)
    legacy.pop("confidence")
    ref_rep = _report_xy(n, 9.0, joints, lambda _f: _POSE_FRONT)
    assert fz.select_pose_matched_pair(
        legacy, ref_rep, [3, 8], [10, 12], ("left_knee",), n,
        frames_fps=9.0, user_rep_fps=9.0, user_rep_frames=n,
        ref_rep_fps=9.0, ref_rep_frames=n,
    ) is None


def test_pair_ref_search_escapes_candidate_window():
    """기준 탐색이 DTW 후보 window 밖(±_POSE_SEARCH_SECONDS)까지 미친다.

    2026-07-28 실측 재현: DTW anchor 가 ≈2.4s drift 해 진짜 같은-포즈 프레임이
    window 밖에 있던 상황. plateau(4..8) 중심 6 은 anchor 30 에서 24프레임
    (2.7s) 떨어져 있어도 ±4.0s 탐색이 도달한다.
    """
    n = 60
    joints = list(_POSE_JOINTS)
    user_rep = _report_xy(n, 9.0, joints, lambda _f: _POSE_FRONT)
    ref_rep = _report_xy(
        n, 9.0, joints, lambda f: _POSE_FRONT if 4 <= f <= 8 else _POSE_BACK
    )
    got = fz.select_pose_matched_pair(
        user_rep, ref_rep, [20, 21], [30, 31], ("left_knee",), n,
        frames_fps=9.0, user_rep_fps=9.0, user_rep_frames=n,
        ref_rep_fps=9.0, ref_rep_frames=n,
    )
    assert got is not None
    assert got[1] == 6, f"plateau 중심 6 (anchor 30 에서 2.7s 밖) (got r={got[1]})"


# ── 타임스탬프 배지 (belle #3 요구 4, 2026-07-28) ──────────────────────────────


def test_timestamp_label_format():
    assert fz._timestamp_label(7.777) == "7.8s"
    assert fz._timestamp_label(0.0) == "0.0s"
    assert fz._timestamp_label(12.0) == "12.0s"


def test_stamp_time_noop_on_invalid_seconds():
    from PIL import Image as _Img

    base = _Img.new("RGB", (fz._OUT, fz._OUT), (7, 7, 7))
    for bad in (None, -1.0, float("nan")):
        img = _Img.new("RGB", (fz._OUT, fz._OUT), (7, 7, 7))
        out = fz._stamp_time(img, bad)
        assert list(out.getdata()) == list(base.getdata()), f"no-op 이어야 함: {bad}"


def test_build_stamps_video_seconds_on_student_panel_only():
    """end-to-end — 타임스탬프 배지는 **학생 패널에만** 찍힌다 (belle ④ 2026-07-28).

    배지 fill (40,40,40) 픽셀을 좌하단 샘플로 확인 — 학생 = 프레임 인덱스/fps.
    기준(정은지) 패널은 미표기: 앱 동작비교 싱크 미세조정 값을 서버 렌더가
    모르는 채 원시 초를 박으면 조정한 사용자에게 혼란 (구 "양패널" 테스트 대체).
    """
    import io as _io

    from PIL import Image as _Img

    m = _Match(start=0, path=[(i, i) for i in range(10)])
    comps = fz.build_fault_zoom_comparisons(
        _frames(10), _frames(10), _report(10, 9.0), _report(10, 9.0),
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0, dtw_match=m,
    )
    assert len(comps) == 1
    assert comps[0]["refMatch"] == "dtw", "이 테스트는 대응 성공 경로여야 함"
    img = _Img.open(_io.BytesIO(comps[0]["png"])).convert("RGB")
    # 합성 canvas 는 가운데 6px 구분선 — ref 패널 로컬 x = 합성 x − (_OUT + 6).
    assert img.getpixel((12, fz._OUT - 12)) == (40, 40, 40), "학생 패널 배지"
    assert img.getpixel((fz._OUT + 6 + 12, fz._OUT - 12)) != (40, 40, 40), (
        "기준 패널 미표기 (belle ④)"
    )


def test_build_skips_ref_stamp_on_full_body_fallback():
    """전신 폴백(refMatch='failed') 기준 패널도 당연히 미표기 — belle ④ 이후
    기준 패널 전면 미표기의 폴백 경로 회귀 가드(구 사유: 대응 오독 방지)."""
    import io as _io

    from PIL import Image as _Img

    comps = fz.build_fault_zoom_comparisons(
        _frames(10), _frames(10), _report(10, 9.0), _report(10, 9.0),
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
    )
    assert len(comps) == 1
    assert comps[0]["refMatch"] == "failed"
    img = _Img.open(_io.BytesIO(comps[0]["png"])).convert("RGB")
    assert img.getpixel((12, fz._OUT - 12)) == (40, 40, 40), "학생 패널은 찍힘"
    assert img.getpixel((fz._OUT + 6 + 12, fz._OUT - 12)) != (40, 40, 40), (
        "전신 폴백 기준 패널은 미표기"
    )
