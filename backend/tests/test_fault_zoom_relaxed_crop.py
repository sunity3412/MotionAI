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


def test_relaxed_margin_widens_crop_vs_valid():
    """같은 중심의 relaxed crop 은 valid crop 보다 넓다 (_RELAXED_MARGIN=2.0).

    display 전용 상수 — 채점 경로 무접촉이라 calibration gate 대상 아님.
    """
    assert fz._RELAXED_MARGIN == 2.0
    frame = _grad_frames()[0]
    valid_img = fz._side_crop(frame, [(0.5, 0.5)], [])[0]
    relaxed_img = fz._side_crop(frame, [], [(0.5, 0.5)])[0]
    c = fz._OUT // 2
    r_valid_edge = valid_img.getpixel((0, c))[0]
    r_relaxed_edge = relaxed_img.getpixel((0, c))[0]
    # 400px 프레임: valid 변=168(left=116, red≈74) / relaxed 변=336(left=32, red≈20)
    assert r_relaxed_edge < r_valid_edge - 20, "relaxed 가 더 넓은 컨텍스트를 담는다"


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
        joint_deltas=None, frames_fps=9.0,
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
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
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
        joint_deltas=None, frames_fps=9.0,
    )
    assert len(comps) == 1
    px = _png_pixel(comps[0]["png"], fz._OUT + 6 + 2, 2)
    assert px != (255, 255, 255), "relaxed = 부위 crop (전신 contain-fit 아님)"
