"""33-G S9/M-2 (quick-260730-l7t Task 2) — criterion 꼭짓점 정중앙 crop + 동일 배율.

승인 목업 4R#1: "두 패널 모두 꼭짓점 = 패널 정중앙(180,180)·같은 배율".
7R 확정: crop = 360x640 프레임의 **겨드랑이 중심 220px**, 학생 겨드랑이 근사 =
shoulder->hip 선분 t=0.15 (일반화 규칙, 육안 검증 통과).

수리 대상 (33-G S9 = FAIL):
  · crop 중심이 region bbox 였다 → criterion 이 계측한 **꼭짓점 관절** 정중앙으로.
  · 두 패널 배율이 각자 bbox 파생이었다 → 카드당 1회 산출한 **공용 한 변**으로.
  · region 인접 매핑(elbow->hand)이 belle #7·#9 의 원인 → 제거(Task 1) + region 강등.

일반화 게이트 (D-41, blocking): 전 규칙은 criterion id·관절명 접미사로만 키잉된다.
프로덕션 코드에 동작명(ref-*) 분기 0 — 본 파일이 grep 으로 박제한다.

순수 — PIL/numpy 외 의존 0. 채점 무접촉(D-44).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from sunity_shared.analysis import fault_zoom as fz


# ─────────── 합성 fixture ───────────


@dataclass
class _Match:
    start: int
    path: list


_IDENTITY9 = _Match(start=0, path=[(i, i) for i in range(9)])


def _frames(n: int = 9, h: int = 640, w: int = 360) -> np.ndarray:
    """위치-인코딩 gradient (red=x, green=y) — crop 출처 픽셀 추적용."""
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    a[:, :, :, 0] = np.linspace(0, 255, w).astype(np.uint8)[None, None, :]
    a[:, :, :, 1] = np.linspace(0, 255, h).astype(np.uint8)[None, :, None]
    a[:, :, :, 2] = 128
    return a


def _report(n: int, fps: float, joint_xy: dict, joint_conf: dict | None = None) -> dict:
    joints = list(joint_xy)
    data: list[float] = []
    conf: list[float] = []
    for _f in range(n):
        for j in joints:
            data += list(joint_xy[j])
            conf.append((joint_conf or {}).get(j, 0.9))
    return {
        "joints": joints, "frames": n, "fps": fps,
        "data": data, "confidence": conf,
    }


# 승인 7R 학생 패널 실좌표 (mockups/index.html 770-782행 doc keypointReport).
_R7_STUDENT = {
    "left_shoulder": (0.564, 0.397),
    "left_elbow": (0.516, 0.336),
    "left_hip": (0.505, 0.475),
}


# ─────────── 1. 꼭짓점 해석기 ───────────


def test_armpit_vertex_known_answer_from_approved_asset():
    """어깨류 꼭짓점 = shoulder->hip 선분 t=0.15 → 승인 7R 의 (200,262).

    근거 = mockups/index.html 7R 행: "겨드랑이 근사 = shoulder(203,254)->hip(182,304)
    선분 t=0.15 지점 (200,262)"(360x640 좌표). lerp 는 아핀이라 정규화 공간 계산이
    프레임 px 공간과 같은 지점을 준다.
    """
    rep = _report(3, 9.0, _R7_STUDENT)
    xy = fz.criterion_vertex_xy(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep, 0
    )
    assert xy is not None
    assert (round(xy[0] * 360), round(xy[1] * 640)) == (200, 262)


def test_armpit_t_constant_is_approved_value():
    assert fz._ARMPIT_T == 0.15


def test_criterion_crop_frac_is_approved_220_over_360():
    """승인 7R 자산 = 360px 프레임의 220px 크롭 (L-1)."""
    assert fz._CRITERION_CROP_FRAC == 220.0 / 360.0


def test_single_joint_vertex_is_that_joint():
    rep = _report(3, 9.0, {"left_knee": (0.4, 0.7), "left_hip": (0.45, 0.4)})
    xy = fz.criterion_vertex_xy(
        "angle_vs_reference__left_knee", ("left_knee",), rep, 0
    )
    assert xy == (0.4, 0.7)


def test_split_angle_vertex_is_pelvis_midpoint():
    """split_angle 꼭짓점 = 골반 중점 = _leg_line_pts[0] 와 동일 정의."""
    xy_map = {
        "left_hip": (0.42, 0.35), "right_hip": (0.58, 0.35),
        "left_knee": (0.30, 0.72), "right_knee": (0.70, 0.72),
    }
    rep = _report(3, 9.0, xy_map)
    got = fz.criterion_vertex_xy("split_angle", tuple(xy_map), rep, 0)
    pts = fz._leg_line_pts(rep, 0)
    assert pts is not None
    assert got == pts[0]
    assert got == (0.5, 0.35)


def test_multi_joint_vertex_is_max_deviation_member():
    """다관절 criterion(leg_extension 등) → _anchor_xy 최대편차 멤버."""
    xy_map = {
        "left_hip": (0.42, 0.35), "right_hip": (0.58, 0.35),
        "left_knee": (0.30, 0.72), "right_knee": (0.70, 0.72),
    }
    rep = _report(3, 9.0, xy_map)
    got = fz.criterion_vertex_xy(
        "leg_extension", tuple(xy_map), rep, 0,
        deltas={"left_knee": 5.0, "right_knee": 30.0},
    )
    assert got == (0.70, 0.72)


def test_vertex_none_when_source_gate_fails():
    """소스 kp 저신뢰/부재 → None (환각 좌표로 crop 중심을 잡지 않는다)."""
    rep = _report(3, 9.0, _R7_STUDENT, {"left_hip": 0.2})
    assert fz.criterion_vertex_xy(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep, 0
    ) is None
    rep2 = _report(3, 9.0, {"left_shoulder": (0.5, 0.4)})   # hip 부재
    assert fz.criterion_vertex_xy(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep2, 0
    ) is None


def test_vertex_uses_injected_resolver_for_absent_joint():
    """기준 8kp 에 없는 관절은 주입된 resolver(대입 선언 경유)로 해석된다."""
    ref8 = _report(3, 9.0, {
        "left_shoulder": (0.50, 0.30), "left_hip": (0.48, 0.55),
        "left_hand": (0.40, 0.10),
    })
    # 대입 선언 없는 기본 resolver → elbow 미해석.
    assert fz.criterion_vertex_xy(
        "angle_vs_reference__left_elbow", ("left_elbow",), ref8, 0
    ) is None
    resolver = fz.make_reference_anchor_resolver(
        "ref-power-spin", "angle_vs_reference__left_elbow",
        anchors={"angle_vs_reference__left_elbow": {
            "joint_substitutions": {"left_elbow": "left_hand"}, "note": "t",
        }},
    )
    assert fz.criterion_vertex_xy(
        "angle_vs_reference__left_elbow", ("left_elbow",), ref8, 0,
        resolver=resolver,
    ) == (0.40, 0.10)


def test_vertex_path_does_not_consult_region_constants(monkeypatch):
    """region 강등 (S9) — crop 중심 결정이 region 표를 참조하지 않는다."""
    monkeypatch.setattr(fz, "CRITERION_REGION", {})
    monkeypatch.setattr(fz, "REGION_MEMBERS", {})
    monkeypatch.setattr(fz, "_REGION_JOINTS", {})
    rep = _report(3, 9.0, _R7_STUDENT)
    xy = fz.criterion_vertex_xy(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep, 0
    )
    assert xy is not None and (round(xy[0] * 360), round(xy[1] * 640)) == (200, 262)


def test_no_motion_name_branching_in_production_module():
    """D-41 blocking — fault_zoom.py 에 동작명(ref-*) 분기 0 (주석 예시 제외)."""
    src = Path(fz.__file__).read_text(encoding="utf-8").splitlines()
    offenders = [
        ln for ln in src
        if re.search(r'["\']ref-[a-z]', ln) and not ln.lstrip().startswith("#")
    ]
    assert offenders == [], f"동작명 문자열 분기 발견: {offenders}"


# ─────────── 2. 정중앙 crop / 동일 배율 ───────────


def test_crop_box_centered_has_no_inner_shift():
    """경계 근처에서도 안쪽 shift 0 (L-3) — 음수 left/top 허용."""
    left, top, side = fz._crop_box_centered(640, 360, 0.02, 0.02, 220)
    assert side == 220
    assert left == round(0.02 * 360 - 110)
    assert top == round(0.02 * 640 - 110)
    assert left < 0 and top < 0
    # 기존 _crop_box 는 clamp/shift 하므로 서로 다른 함수임을 박제 (legacy 보존).
    assert fz._crop_box(640, 360, 0.02, 0.02, 220)[0] >= 0


def test_render_crop_padded_uses_white_padding():
    """프레임 밖 영역은 흰 패딩 (_full_frame_fit 선례) — 검은 패딩 금지."""
    frame = _frames(n=1)[0]
    img = fz._render_crop_padded(frame, -200, -200, 220)
    a = np.asarray(img)
    assert a.shape == (fz._OUT, fz._OUT, 3)
    # 좌상단은 프레임 밖 → 흰색.
    assert tuple(a[2, 2]) == (255, 255, 255)


def test_vertex_lands_on_panel_center():
    """꼭짓점의 crop-내 출력 픽셀 = 패널 정중앙 (±1px)."""
    frame = _frames(n=1)[0]
    h, w = frame.shape[0], frame.shape[1]
    side = round(min(h, w) * fz._CRITERION_CROP_FRAC)
    for cx, cy in ((0.5, 0.5), (0.02, 0.02), (0.98, 0.97), (0.5556, 0.4086)):
        _img, kind, anchor_px, box = fz._side_crop(
            frame, [(cx, cy)], [], anchor=(cx, cy),
            center=(cx, cy), side_override=side,
        )
        assert kind == "valid"
        assert box is not None and box[2] == side
        px = fz._to_crop_px(
            (cx, cy), box[0], box[1], box[2], w, h
        )
        assert abs(px[0] - fz._OUT // 2) <= 1, (cx, cy, px)
        assert abs(px[1] - fz._OUT // 2) <= 1, (cx, cy, px)
        assert anchor_px is not None
        assert abs(anchor_px[0] - fz._OUT // 2) <= 1
        assert abs(anchor_px[1] - fz._OUT // 2) <= 1


def test_side_crop_without_center_routes_through_legacy_helpers():
    """center 미지정 = 기존 3단 강하 그대로 (_crop_box + _render_crop)."""
    frame = _frames(n=1)[0]
    h, w = frame.shape[0], frame.shape[1]
    pts = [(0.4, 0.6)]
    img, kind, _anchor, box = fz._side_crop(frame, pts, [])
    expect_box = fz._crop_box(h, w, 0.4, 0.6, round(min(h, w) * fz._CROP_FRAC))
    assert box == expect_box and kind == "valid"
    expect_img = fz._render_crop(frame, *expect_box)
    assert np.array_equal(np.asarray(img), np.asarray(expect_img))


def _spec(span_x: float, span_y: float = 0.0):
    """(꼭짓점, 사지 방향점, 몸통 방향점) — 정규화 span 만 만드는 최소 스펙."""
    return ((0.5, 0.5), (0.5 + span_x, 0.5), (0.5, 0.5 + span_y))


def test_crop_side_puts_part_at_target_fraction():
    """밴드 안이면 부위가 패널의 목표 비율(_CRITERION_PART_TARGET)이 되게 잡는다."""
    short = 1000
    # 정사각 프레임이라 정규화 span 0.22 = 220px → 목표 0.5 → 한 변 440px (밴드 안).
    got = fz.criterion_crop_side(short, [(_spec(0.22), (1000, 1000))])
    assert got == 440, got
    assert 220 / got == pytest.approx(fz._CRITERION_PART_TARGET, abs=1e-9)


def test_crop_side_clamps_to_floor_for_small_parts():
    """부위가 작아도 하한 아래로는 안 좁힌다 — 맥락(거꾸로 매달린 자세)이 사라진다."""
    short = 1000
    got = fz.criterion_crop_side(short, [(_spec(0.05), (1000, 1000))])
    assert got == round(short * fz._CRITERION_CROP_FRAC_MIN), got


def test_crop_side_clamps_to_cap_for_large_parts():
    """부위가 커도 상한 위로는 안 넓힌다 — belle '전신 사진이면 안되지'."""
    short = 1000
    got = fz.criterion_crop_side(short, [(_spec(0.90), (1000, 1000))])
    assert got == round(short * fz._CRITERION_CROP_FRAC_MAX), got


def test_crop_side_takes_the_wider_of_the_two_panels():
    """두 패널 중 **큰 부위** 쪽에 맞춘다 — 작은 쪽에 맞추면 큰 쪽 표시가 잘린다."""
    short = 1000
    small, big = _spec(0.18), _spec(0.24)
    got = fz.criterion_crop_side(short, [(small, (1000, 1000)), (big, (1000, 1000))])
    assert got == fz.criterion_crop_side(short, [(big, (1000, 1000))])
    assert got == 480, got


def test_crop_side_uses_the_cap_when_part_cannot_be_measured():
    """부위를 못 재면 밴드 상한 — 종전 고정값(0.61)은 밴드 밖이라 여기서만 전신이 샌다."""
    short = 1000
    got = fz.criterion_crop_side(short, [(None, (1000, 1000))])
    assert got == round(short * fz._CRITERION_CROP_FRAC_MAX), got
    assert got < round(short * fz._CRITERION_CROP_FRAC), "종전 고정값보다는 좁아야 한다"


def test_both_panels_share_side_px_end_to_end(caplog):
    """criterion 카드: 두 패널 crop 한 변 px 동일 + vertex_centered 로그."""
    u_frames = _frames(n=9, h=640, w=360)
    r_frames = _frames(n=9, h=480, w=270)   # 촬영거리/해상도 다른 기준 영상
    user_rep = _report(9, 9.0, _R7_STUDENT)
    ref_rep = _report(9, 9.0, {
        "left_shoulder": (0.50, 0.30), "left_hip": (0.48, 0.55),
    })
    with caplog.at_level(logging.INFO, logger="sunity_shared.analysis.fault_zoom"):
        comps = fz.build_fault_zoom_comparisons(
            u_frames, r_frames, user_rep, ref_rep,
            worst_seconds=0.5, fault_joints=["left_shoulder"],
            joint_deltas={"left_shoulder": 25.0}, frames_fps=9.0,
            dtw_match=_IDENTITY9,
            criterion_units=[{
                "criterion": "angle_vs_reference__left_shoulder",
                "joints": ("left_shoulder",),
                "region": None,
            }],
        )
    assert len(comps) == 1
    line = next(
        m for m in caplog.messages if "fault_zoom_crop " in m
    )
    u = int(re.search(r"user_side_px=(\d+)", line).group(1))
    r = int(re.search(r"ref_side_px=(\d+)", line).group(1))
    assert u == r, f"두 패널 배율 불일치 user={u} ref={r}"
    assert "vertex_centered=True" in line
    # 공용 한 변 = 두 프레임 짧은 변 min 에서 파생 (L-2 — 어느 프레임도 초과 안 함).
    # 폭 자체는 **부위 크기에서 나온다**(quick-260810-ms2, belle 08-10 "전신 사진이면
    # 안되지") — 종전 고정 220/360 은 카드마다 부위가 22~58%로 벌어졌다. 여기서
    # 못 박는 것은 그 계약이지 특정 숫자가 아니다: 하한·상한 밴드 안에 있을 것.
    short = min(360, 270)
    assert round(short * fz._CRITERION_CROP_FRAC_MIN) <= u <= round(
        short * fz._CRITERION_CROP_FRAC_MAX
    ), f"crop 폭이 하한·상한 밴드 밖: {u} (short={short})"
    assert f"shared_side_px={u}" in line


def test_legacy_card_logs_vertex_centered_false(caplog):
    """legacy fan-out 은 정중앙 경로 미진입 — 로그로 구분 가능."""
    frames = _frames(n=9)
    rep = _report(9, 9.0, {"left_knee": (0.4, 0.7)})
    with caplog.at_level(logging.INFO, logger="sunity_shared.analysis.fault_zoom"):
        comps = fz.build_fault_zoom_comparisons(
            frames, frames, rep, rep,
            worst_seconds=0.5, fault_joints=["left_knee"],
            joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
            dtw_match=_IDENTITY9,
        )
    assert len(comps) == 1
    line = next(m for m in caplog.messages if "fault_zoom_crop " in m)
    assert "vertex_centered=False" in line


def test_marker_circle_sits_at_panel_center():
    """정중앙 crop 카드의 원 마커 중심 = 패널 중앙 (승인본 정합)."""
    frames = _frames(n=9)
    user_rep = _report(9, 9.0, _R7_STUDENT)
    ref_rep = _report(9, 9.0, {
        "left_shoulder": (0.50, 0.30), "left_hip": (0.48, 0.55),
    })
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_shoulder"],
        joint_deltas={"left_shoulder": 25.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9,
        criterion_units=[{
            "criterion": "angle_vs_reference__left_shoulder",
            "joints": ("left_shoulder",),
            "region": None,
        }],
    )
    assert len(comps) == 1
    import io

    img = np.asarray(Image.open(io.BytesIO(comps[0]["png"])).convert("RGB")).astype(int)
    brand = np.array([255, 75, 51])
    for x0 in (0, fz._OUT + 6):
        panel = img[:, x0:x0 + fz._OUT, :]
        mask = np.abs(panel - brand[None, None, :]).sum(axis=2) < 40
        ys, xs = np.nonzero(mask)
        assert len(xs) > 0, "브랜드 마커 없음"
        # 원(또는 각도 기하)의 중심이 패널 중앙 근처.
        assert abs(xs.mean() - fz._OUT / 2) < 24, xs.mean()
        assert abs(ys.mean() - fz._OUT / 2) < 24, ys.mean()


# ─────────── 3. 꼭짓점 미성립 = 인접 대체 금지 (L-6) ───────────


def test_elbow_card_dropped_when_reference_lacks_joint_and_annotation():
    """기준 8kp 에 elbow 부재 + 주석 없음 → 카드 미방출 (인접 관절 대체 0)."""
    frames = _frames(n=9)
    user_rep = _report(9, 9.0, {
        "left_elbow": (0.45, 0.30), "left_shoulder": (0.50, 0.40),
    })
    ref_rep = _report(9, 9.0, {
        "left_shoulder": (0.50, 0.30), "left_hand": (0.40, 0.10),
        "left_hip": (0.48, 0.55),
    })
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_elbow"],
        joint_deltas={"left_elbow": 25.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9,
        criterion_units=[{
            "criterion": "angle_vs_reference__left_elbow",
            "joints": ("left_elbow",),
            "region": None,
        }],
        motion_id="ref-not-annotated-260730",
    )
    assert comps == [], "기준 관절 부재인데 카드가 방출됨 — 인접 대체 금지 위반(L-6)"


def test_elbow_card_restored_with_anchor_annotation():
    """앵커 주석이 있으면 그 카드가 복귀한다 (§C-4 주석 채움의 실효 증명)."""
    frames = _frames(n=9)
    user_rep = _report(9, 9.0, {
        "left_elbow": (0.45, 0.30), "left_shoulder": (0.50, 0.40),
    })
    ref_rep = _report(9, 9.0, {
        "left_shoulder": (0.50, 0.30), "left_hand": (0.40, 0.10),
        "left_hip": (0.48, 0.55),
    })
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_elbow"],
        joint_deltas={"left_elbow": 25.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9,
        criterion_units=[{
            "criterion": "angle_vs_reference__left_elbow",
            "joints": ("left_elbow",),
            "region": None,
        }],
        motion_id="ref-power-spin",
        reference_anchor_overrides={
            "angle_vs_reference__left_elbow": {
                "joint_substitutions": {"left_elbow": "left_hand"},
                "note": "test",
            }
        },
    )
    assert len(comps) == 1
    assert comps[0]["criterion"] == "angle_vs_reference__left_elbow"
