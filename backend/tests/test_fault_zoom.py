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


# ─────────── quick-260704-fz4 후속 — deficit 배지 라벨 "N°" 포맷 ───────────


def test_deficit_label_uses_degree_symbol():
    """배지 라벨 = 숫자 + 도 기호 (구 "40deg" 원어 표기 교체, belle 실기기).

    round 반올림 + 도 기호(U+00B0)가 PIL 기본 폰트 글리프를 보유하는지까지
    못 박는다 — confirmed/advisory 양 배치가 _mark 를 공유하므로 단일 검증으로
    충분.
    """
    assert fz._deficit_label(40.0) == "40°"
    assert fz._deficit_label(23.4) == "23°"
    assert fz._deficit_label(23.5) == "24°"
    assert "deg" not in fz._deficit_label(30.0)

    from PIL import ImageFont

    mask = ImageFont.load_default().getmask("°")
    assert mask.size[0] > 0, "PIL 기본 폰트에 도 기호 글리프 존재"

    # 실제 배지 렌더 smoke — 예외 없이 그려지고 배지 사각형에 브랜드 픽셀 존재.
    img = fz._mark(
        fz._full_frame_fit(np.zeros((64, 64, 3), dtype=np.uint8)), 40.0
    )
    assert img.getpixel((fz._OUT - 12, 10)) == (255, 75, 51), "배지 배경 렌더"


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

    def spy(img, deficit, circle=True, anchor_px=None):
        calls.append((circle, anchor_px))
        return orig(img, deficit, circle=circle, anchor_px=anchor_px)

    monkeypatch.setattr(fz, "_mark", spy)
    return calls


def _spy_leg_angle(monkeypatch):
    calls: list[tuple] = []

    def spy(img, pelvis_px, left_px, right_px, angle_deg):
        calls.append((pelvis_px, left_px, right_px, angle_deg))
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
    _mark circle=False(원 생략, 배지 유지). ref 는 _mark 없음(선 없는 crop).
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
    assert mark_calls == [(False, None)], "user 원 생략(배지 유지), ref 는 _mark 없음"


def test_legs_split_angle_numbers_passed(monkeypatch):
    """Test 3a: split_angle_degs=(130,170) → user 측 130 만 전달 (게이트 B)."""
    leg_calls = _spy_leg_angle(monkeypatch)
    frames = _frames(9, h=400, w=400)
    rep = _report_pos_conf(9, 9.0, _LEGS_XY, {})  # 명시적 고신뢰 0.9
    fz.build_fault_zoom_comparisons(
        frames, frames, rep, rep, worst_seconds=0.5,
        fault_joints=list(_LEGS_XY), joint_deltas=None, frames_fps=9.0,
        joint_kinds={j: "deficit" for j in _LEGS_XY},
        split_angle_degs=(130.0, 170.0), split_angle_present=True,
    )
    assert [c[3] for c in leg_calls] == [130.0], "user 측 학생 벌림각만(ref 미드로잉)"


def test_legs_split_angle_none_omits_numbers(monkeypatch):
    """Test 3b: split_angle_degs=None → user 측 angle_deg=None (수치 생략, 선+호만).

    kip-up reference_relative 경로: 수치는 없지만 사이각 자체는 의미 있어 학생
    측에 선+호만 그린다 (2026-07-05 belle pod 전동작 검증).
    """
    leg_calls = _spy_leg_angle(monkeypatch)
    frames = _frames(9, h=400, w=400)
    rep = _report_pos_conf(9, 9.0, _LEGS_XY, {})  # 명시적 고신뢰 0.9
    fz.build_fault_zoom_comparisons(
        frames, frames, rep, rep, worst_seconds=0.5,
        fault_joints=list(_LEGS_XY), joint_deltas=None, frames_fps=9.0,
        joint_kinds={j: "deficit" for j in _LEGS_XY},
        split_angle_degs=None, split_angle_present=True,
    )
    assert [c[3] for c in leg_calls] == [None], "user 측만 선+호(수치 None)"


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
    assert fz._draw_side_leg_angle(img, frame, rep, 0, (150, 280, 100), None) is False
    assert leg_calls == [], "crop 밖 hip → 사이각 드로잉 생략(폴백)"

    # 대조(regression): hip 을 포함하는 큰 crop → 정상 드로잉 (게이트 통과).
    assert fz._draw_side_leg_angle(img, frame, rep, 0, (0, 0, 400), None) is True
    assert len(leg_calls) == 1, "crop 이 3점 전부 포함하면 그린다"


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
    """Test 7: 실 픽셀 smoke — 두 선 위 브랜드색 + degenerate 폴백(False)."""
    from PIL import Image as _I

    img = _I.new("RGB", (fz._OUT, fz._OUT), (0, 0, 0))
    assert fz._draw_leg_angle(img, (180, 80), (80, 300), (280, 300), 130.0) is True
    # 두 선(골반→왼/오른) 중점 픽셀 = 브랜드색.
    assert img.getpixel((130, 190)) == fz._BRAND, "골반→왼 다리 선"
    assert img.getpixel((230, 190)) == fz._BRAND, "골반→오른 다리 선"

    # degenerate — 벡터 길이 < _MIN_LEG_VEC_PX → 드로잉 없이 원본 반환.
    img2 = _I.new("RGB", (fz._OUT, fz._OUT), (0, 0, 0))
    assert fz._draw_leg_angle(
        img2, (100, 100), (103, 100), (280, 300), 130.0
    ) is False
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
