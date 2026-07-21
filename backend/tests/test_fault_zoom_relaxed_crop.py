"""fault_zoom 완화(relaxed) crop 3단 강하 + 앵커 정밀화 단위테스트 (Phase 25-03).

순수 — PIL/numpy 외 의존 0 (S3/네트워크/firestore import 금지). 배경:
reference(정은지) 측 keypoint 가 저신뢰(<_KP_CONF_MIN)인 kip-up 류에서
카드마다 동일 전신 사진이 반복돼 "분석 안 한 것처럼 보임" — 좌표가 유한하면
부위-중심 완화 crop 으로 카드별 차별화한다 (belle 2026-07-04 실기기).

3단 강하: valid(confidence 게이트 통과) → relaxed(저신뢰-유한 좌표) →
full(좌표 결측 전신 폴백). relaxed/full 측은 앵커 circle 생략 (좌표 불확실 —
엉뚱한 부위에 확정 표식 금지, 260702-sic belle 요구 3 정신 유지).
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402


# ─────────── 합성 fixture ───────────


from dataclasses import dataclass  # noqa: E402


@dataclass
class _Match:
    start: int
    path: list


# 28-05 D-04: dtw_match 부재 = 기준 프레임 대응 실패 → ref 전신 폴백(refMatch='failed').
# 아래 crop-tier(relaxed/full/부위 차별화) 테스트들은 '대응이 서는' 전제에서 ref 측
# crop 계층을 검증하므로 identity DTW 를 넘겨 대응을 세운다 (기존 ratio 근사가 우연히
# 유효 ref 프레임을 준 것을 대체 — Rule 3 필연 연쇄).
_IDENTITY9 = _Match(start=0, path=[(i, i) for i in range(9)])


def _grad_frames(n: int = 1, h: int = 400, w: int = 400) -> np.ndarray:
    """위치-인코딩 gradient 프레임 — red=x 비례, green=y 비례.

    crop 출력 픽셀색으로 'crop 이 프레임 어느 부위에서 왔는지'를 검증한다.
    """
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    a[:, :, :, 0] = np.linspace(0, 255, w).astype(np.uint8)[None, None, :]
    a[:, :, :, 1] = np.linspace(0, 255, h).astype(np.uint8)[None, :, None]
    return a


def _report_pos(
    n: int,
    fps: float,
    joint_xy: dict[str, tuple[float, float]],
    joint_conf: dict[str, float] | None = None,
) -> dict:
    """per-joint 위치/confidence 지정 합성 keypointReport."""
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


def _png_pixel(png: bytes, x: int, y: int) -> tuple[int, int, int]:
    return Image.open(io.BytesIO(png)).convert("RGB").getpixel((x, y))


# ─────────── Task 1 — _side_crop 3단 강하 (valid → relaxed → full) ───────────


def test_side_crop_three_tier_kinds():
    """valid pts → 'valid' / relaxed pts 만 → 'relaxed' / 둘 다 없음 → 'full'."""
    frame = _grad_frames()[0]
    _img, kind = fz._side_crop(frame, [(0.5, 0.5)], [])[:2]
    assert kind == "valid"
    _img, kind = fz._side_crop(frame, [], [(0.5, 0.5)])[:2]
    assert kind == "relaxed"
    _img, kind = fz._side_crop(frame, [], [])[:2]
    assert kind == "full"


def test_relaxed_crop_centers_follow_low_conf_coords():
    """완화 crop 중심이 저신뢰 좌표를 따라간다 — 좌표가 다르면 crop 도 다르다."""
    frame = _grad_frames()[0]
    img_a = fz._side_crop(frame, [], [(0.25, 0.25)])[0]
    img_b = fz._side_crop(frame, [], [(0.75, 0.75)])[0]
    c = fz._OUT // 2
    ra, ga, _ = img_a.getpixel((c, c))
    rb, gb, _ = img_b.getpixel((c, c))
    assert rb - ra > 20 and gb - ga > 20, "부위-중심 차별화 (동일 전신 반복 해소)"


def test_relaxed_framing_matches_valid_after_d20():
    """Phase 32 (D-20): relaxed 프레이밍이 valid 와 동일 배율(1.8)로 통일.

    구 계약(relaxed 가 _RELAXED_MARGIN=2.0 만큼 더 넓음)은 "정은지 crop 이 비교와
    안 맞음"(belle 실기기)이라, _side_crop 의 relaxed 분기가 valid 와 동일하게
    margin=1.0(bbox*1.8)으로 프레이밍을 통일했다. 마커는 좌표 오차에 민감하므로
    relaxed 의 anchor_px=None 생략 게이트는 현행 유지(프레이밍/마커 분리).
    상수 _RELAXED_MARGIN 은 향후 마커 게이트 튜닝 참조용으로 보존(프레이밍 미사용).
    """
    assert fz._RELAXED_MARGIN == 2.0  # 상수 보존(삭제 아님, D-20 프레이밍 미사용)
    frame = _grad_frames()[0]
    pts = [(0.3, 0.5), (0.7, 0.5)]  # bbox 160px → valid/relaxed 둘 다 bbox*1.8=288
    valid_box = fz._side_crop(frame, pts, [])[3]
    relaxed_box = fz._side_crop(frame, [], pts)[3]
    # 구 코드: relaxed 변 = 160*1.8*2.0=576 → 프레임 400 클램프 ≠ valid 288 (더 넓음).
    # D-20 후: 양측 margin 1.0 → 둘 다 288 (parity).
    assert valid_box[2] == relaxed_box[2] == 288, "relaxed 프레이밍 == valid (D-20 통일)"


def test_relaxed_dense_pts_stay_at_floor_size_not_full_width():
    """밀집 relaxed 좌표는 floor(_CROP_FRAC 줌 수준) 크기 부위 crop — 전폭 미도달.

    2026-07-05 pod 재현 (ref-kip-up frame 37, belle 실기기): floor 에도
    _RELAXED_MARGIN 을 곱하면 side 가 프레임 전폭에 클램프돼 모든 relaxed crop
    이 전신처럼 보임 — "부위-중심 완화 crop 차별화"(Phase 25-03) 무력화.
    밀집 2점(bbox 8px*1.8*2.0=29 < floor 168)의 relaxed crop 이 같은 중심 단일
    valid 점 crop 과 픽셀 동일해야 함 = side == floor 증명 (구 코드는
    floor*2.0=336 폭주).
    """
    frame = _grad_frames()[0]
    relaxed_img = fz._side_crop(frame, [], [(0.49, 0.5), (0.51, 0.5)])[0]
    valid_img = fz._side_crop(frame, [(0.5, 0.5)], [])[0]
    c = fz._OUT // 2
    assert relaxed_img.getpixel((0, c)) == valid_img.getpixel((0, c)), (
        "밀집 relaxed 변 == floor (valid 단일점과 동일 crop 영역)"
    )


def test_build_ref_low_conf_cards_differ_by_joint():
    """reference 측 저신뢰-유한 좌표 → 카드별로 다른 부위-중심 완화 crop.

    구 동작(전신 폴백)이면 두 카드의 ref 반쪽이 동일 전신 사진 — 본 테스트가
    RED. left_knee/left_shoulder 는 서로 다른 region + 단측이라 grouping 미발동
    (카드 2장 보장).
    """
    frames = _grad_frames(9)
    user_rep = _report_pos(
        9, 9.0,
        {"left_knee": (0.5, 0.5), "left_shoulder": (0.5, 0.5)},
        {"left_knee": 0.9, "left_shoulder": 0.9},
    )
    ref_rep = _report_pos(
        9, 9.0,
        {"left_knee": (0.2, 0.8), "left_shoulder": (0.8, 0.2)},
        {"left_knee": 0.1, "left_shoulder": 0.1},  # 저신뢰 but finite
    )
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_knee", "left_shoulder"],
        joint_deltas=None, frames_fps=9.0, dtw_match=_IDENTITY9,
    )
    assert len(comps) == 2
    cx = fz._OUT + 6 + fz._OUT // 2  # ref 반쪽 중앙
    cy = fz._OUT // 2
    px_knee = _png_pixel(comps[0]["png"], cx, cy)
    px_shoulder = _png_pixel(comps[1]["png"], cx, cy)
    assert px_knee != px_shoulder, "카드마다 동일 전신 반복이 아니라 부위별 crop"
    # 전신 폴백이면 contain-fit 정사각(400x400→흰 패딩 없음)이라도 중앙 픽셀이
    # 두 카드 동일 — 위 불일치가 relaxed 차별화의 직접 증거.


def test_build_missing_coords_still_full_fallback():
    """좌표 자체 결측(NaN) 측은 relaxed 가 아니라 기존 전신 폴백 유지."""
    frames = _grad_frames(9, h=400, w=200)  # 세로 프레임 → 전신 폴백 시 흰 패딩
    user_rep = _report_pos(9, 9.0, {"left_knee": (0.5, 0.5)}, {"left_knee": 0.9})
    ref_rep = _report_pos(
        9, 9.0, {"left_knee": (float("nan"), float("nan"))}, {"left_knee": 0.9}
    )
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0, dtw_match=_IDENTITY9,
    )
    assert len(comps) == 1
    # 전신 contain-fit → ref 반쪽 좌상단 = 흰 패딩. relaxed/crop 이면 프레임 내용.
    assert _png_pixel(comps[0]["png"], fz._OUT + 6 + 2, 2) == (255, 255, 255)


def test_build_ref_low_conf_finite_is_crop_not_full():
    """저신뢰-유한 좌표 측은 전신 폴백이 아니라 부위 crop (흰 패딩 부재)."""
    frames = _grad_frames(9, h=400, w=200)  # 전신 폴백이면 좌우 흰 패딩 생김
    user_rep = _report_pos(9, 9.0, {"left_knee": (0.5, 0.5)}, {"left_knee": 0.9})
    ref_rep = _report_pos(9, 9.0, {"left_knee": (0.5, 0.5)}, {"left_knee": 0.1})
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas=None, frames_fps=9.0, dtw_match=_IDENTITY9,
    )
    assert len(comps) == 1
    px = _png_pixel(comps[0]["png"], fz._OUT + 6 + 2, 2)
    assert px != (255, 255, 255), "relaxed = 부위 crop (전신 contain-fit 아님)"


# ─────────── Task 2 — 앵커 정밀화 (circle=관절 좌표, relaxed/full 생략) ───────────


def test_side_crop_anchor_maps_to_joint_pixel():
    """valid grouped crop 의 anchor_px = 결함 관절의 crop-내 상대 좌표.

    400px 프레임, pts x=100/300px → bbox 200 → 변 = 200*1.8=360, left/top=20.
    anchor (0.25,0.5) → ((100-20)/360*360, (200-20)/360*360) = (80,180) ≠ 중앙.
    """
    frame = _grad_frames()[0]
    # quick-260705-r6x: _side_crop 이 4-tuple (..., box) 반환 — box 는 여기선 미사용.
    _img, kind, anchor_px, _box = fz._side_crop(
        frame, [(0.25, 0.5), (0.75, 0.5)], [], anchor=(0.25, 0.5)
    )
    assert kind == "valid"
    assert anchor_px == (80, 180)
    assert anchor_px != (fz._OUT // 2, fz._OUT // 2), "crop 중심 고정이 아님"


def test_side_crop_relaxed_and_full_have_no_anchor():
    """relaxed/full 측은 anchor_px = None (좌표 불확실 — 확정 표식 금지)."""
    frame = _grad_frames()[0]
    assert fz._side_crop(frame, [], [(0.5, 0.5)], anchor=(0.5, 0.5))[2] is None
    assert fz._side_crop(frame, [], [], anchor=(0.5, 0.5))[2] is None


def test_mark_circle_drawn_at_anchor_not_center():
    """_mark 의 circle 이 anchor_px 에 그려진다 (픽셀 검증)."""
    img = Image.new("RGB", (fz._OUT, fz._OUT), (0, 0, 0))
    fz._mark(img, None, circle=True, anchor_px=(80, 180))
    r = int(fz._OUT * 0.16)
    assert img.getpixel((80 + r, 180)) == (255, 75, 51), "링이 anchor 를 둘러쌈"
    assert img.getpixel((fz._OUT // 2 + r, fz._OUT // 2)) == (0, 0, 0), (
        "구 crop-중앙 링 위치엔 없음"
    )
    # anchor_px 부재 → 기존 중앙 circle (하위호환, 기존 테스트와 동일 규칙).
    img2 = Image.new("RGB", (fz._OUT, fz._OUT), (0, 0, 0))
    fz._mark(img2, None, circle=True)
    c = fz._OUT // 2
    assert img2.getpixel((c + r, c)) == (255, 75, 51)


def _spy_mark(monkeypatch):
    calls: list[tuple[bool, tuple[int, int] | None]] = []
    orig = fz._mark

    def spy(img, deficit, circle=True, anchor_px=None):
        calls.append((circle, anchor_px))
        return orig(img, deficit, circle=circle, anchor_px=anchor_px)

    monkeypatch.setattr(fz, "_mark", spy)
    return calls


def test_build_grouped_circle_at_max_deficit_joint(monkeypatch):
    """grouped(arms) 카드의 circle = deficit 최대 대표 관절 좌표 (호출 인자 검증).

    legs 는 quick-260705-r6x 사이각 드로잉으로 이전 — arms 로 계약 보존 (grouped
    카드 circle=deficit 최대 관절 규칙은 non-legs grouped 에 여전히 유효).
    400px 프레임, 4관절 px 120..280 → bbox 160 → 변 288, left/top=56.
    right_elbow(0.7,0.7)=280px, delta 최대 → anchor = ((280-56)/288*360)=(280,280).
    """
    calls = _spy_mark(monkeypatch)
    arms = {
        "left_shoulder": (0.3, 0.3), "right_shoulder": (0.7, 0.3),
        "left_elbow": (0.3, 0.7), "right_elbow": (0.7, 0.7),
    }
    frames = _grad_frames(9)
    rep = _report_pos(9, 9.0, arms, {j: 0.9 for j in arms})
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, rep, rep,
        worst_seconds=0.5, fault_joints=list(arms),
        joint_deltas={
            "left_shoulder": 10.0, "right_shoulder": 12.0,
            "left_elbow": 15.0, "right_elbow": 35.0,
        },
        frames_fps=9.0, joint_kinds={j: "deficit" for j in arms},
    )
    assert len(comps) == 1 and comps[0]["region"] == "arms"
    assert calls == [(True, (280, 280))], "circle=대표(deficit 최대) 관절 좌표"


def test_build_relaxed_user_side_no_circle(monkeypatch):
    """user 측 저신뢰-유한(relaxed) → circle=False (앵커 생략, deficit 배지 유지)."""
    calls = _spy_mark(monkeypatch)
    frames = _grad_frames(9)
    user_rep = _report_pos(9, 9.0, {"left_knee": (0.5, 0.5)}, {"left_knee": 0.1})
    ref_rep = _report_pos(9, 9.0, {"left_knee": (0.5, 0.5)}, {"left_knee": 0.9})
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0, dtw_match=_IDENTITY9,
    )
    assert len(comps) == 1 and comps[0]["deficitDeg"] == 20.0
    assert calls == [(False, None)], "relaxed 측 circle 생략"


def test_build_full_user_side_no_circle(monkeypatch):
    """user 측 좌표 결측(full 폴백) → circle=False (기존 규칙 유지)."""
    calls = _spy_mark(monkeypatch)
    frames = _grad_frames(9)
    user_rep = _report_pos(
        9, 9.0, {"left_knee": (float("nan"), float("nan"))}, {"left_knee": 0.9}
    )
    ref_rep = _report_pos(9, 9.0, {"left_knee": (0.5, 0.5)}, {"left_knee": 0.9})
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas=None, frames_fps=9.0, dtw_match=_IDENTITY9,
    )
    assert len(comps) == 1
    assert calls == [(False, None)], "전신 폴백 측 circle 생략 (기존 그대로)"
