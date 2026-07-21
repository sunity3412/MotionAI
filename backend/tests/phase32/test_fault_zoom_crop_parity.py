"""fault_zoom relaxed 프레이밍 parity + crop side 로그 단위테스트 — Phase 32 (D-20).

수리(32-PATTERNS §A-4, faultzoom-reference-crop-2x-wider-diagnosed 합의): relaxed
경로의 프레이밍 배율을 valid 와 동일(양측 1.8배)하게 통일한다 — "정은지 crop 이 2배
넓어 비교와 안 맞음" belle 실기기 해소. 마커는 좌표 오차에 민감하므로 relaxed 의
anchor_px=None(생략 게이트)는 현행 유지(프레이밍/마커 신뢰도 게이트 분리).

crop side px 구조 로그도 검증한다 — 32-03 전수 스윕이 육안 비교에 더해 user/ref crop
side 비(0.8~1.25)로 수치 parity 를 판정하는 재료. 로그는 관측 전용(채점/방출 무접촉).

순수 — PIL/numpy 외 의존 0 (S3/네트워크/firestore import 금지). 인용: 32-CONTEXT D-20.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from sunity_shared.analysis import fault_zoom as fz


# ─────────── 합성 fixture ───────────


@dataclass
class _Match:
    start: int
    path: list


_IDENTITY9 = _Match(start=0, path=[(i, i) for i in range(9)])


def _frames(n: int = 1, h: int = 400, w: int = 400) -> np.ndarray:
    """위치-인코딩 gradient 프레임 (red=x, green=y) — crop 출처 픽셀 검증용."""
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    a[:, :, :, 0] = np.linspace(0, 255, w).astype(np.uint8)[None, None, :]
    a[:, :, :, 1] = np.linspace(0, 255, h).astype(np.uint8)[None, :, None]
    return a


def _report(n: int, fps: float, joint_xy, joint_conf) -> dict:
    """per-joint 위치/confidence 지정 합성 keypointReport."""
    joints = list(joint_xy)
    data: list[float] = []
    for _f in range(n):
        for j in joints:
            data += list(joint_xy[j])
    conf: list[float] = []
    for _f in range(n):
        for j in joints:
            conf.append(joint_conf.get(j, 0.9))
    return {"joints": joints, "frames": n, "fps": fps, "data": data, "confidence": conf}


# bbox 100px(0.375~0.625 × 400) → valid side = max(floor 168, 100*1.8) = 180,
# 구 relaxed(margin 2.0) side = max(168, 100*1.8*2.0) = 360 (프레임 400 내 미클램프).
# D-20 후: 양측 margin 1.0 → 둘 다 180 (parity).
_SCATTERED_PTS = [(0.375, 0.5), (0.625, 0.5)]


# ─────────── Test 1 — 프레이밍 parity (valid 배율 == relaxed 배율) ───────────


def test_valid_and_relaxed_framing_parity():
    """동일 bbox 입력에서 valid 경로와 relaxed 경로의 crop side 길이가 동일 (양측 1.8배).

    구 코드: relaxed 가 _RELAXED_MARGIN(2.0)만큼 더 넓어 정은지 쪽이 전신처럼 보임."""
    frame = _frames()[0]
    valid_box = fz._side_crop(frame, _SCATTERED_PTS, [])[3]
    relaxed_box = fz._side_crop(frame, [], _SCATTERED_PTS)[3]
    assert valid_box is not None and relaxed_box is not None
    assert valid_box[2] == relaxed_box[2], (
        "relaxed 프레이밍이 valid 와 동일 배율(1.8)이어야 함 (D-20)"
    )


# ─────────── Test 2 — 마커 생략 게이트 보존 (kind='relaxed', anchor_px=None) ─────


def test_relaxed_kind_and_no_anchor_preserved():
    """relaxed 경로 반환 crop_kind='relaxed' 유지, anchor_px=None 유지.

    프레이밍만 통일하고 마커(anchor) 생략 게이트는 현행 보존 — 저신뢰 좌표에
    확정 표식을 찍지 않는다(260702-sic 요구 3 정신)."""
    frame = _frames()[0]
    _img, kind, anchor_px, _box = fz._side_crop(
        frame, [], _SCATTERED_PTS, anchor=(0.5, 0.5)
    )
    assert kind == "relaxed"
    assert anchor_px is None, "relaxed 는 anchor_px=None (마커 생략 게이트 보존)"


# ─────────── Test 3 — valid 경로 무회귀 (byte 동일) ───────────


def test_valid_path_unchanged_no_regression():
    """valid 경로 산출은 수정 전과 동일 — D-20 은 relaxed 분기만 건드린다.

    valid side = max(floor 168, bbox 100 * 1.8) = 180 (margin 1.0 baked in) 고정 +
    동일 입력 2회 render 픽셀 동일(결정론)."""
    frame = _frames()[0]
    img, kind, _anchor, box = fz._side_crop(
        frame, _SCATTERED_PTS, [], anchor=(0.375, 0.5)
    )
    assert kind == "valid"
    assert box[2] == 180, "valid 배율 무변경 (bbox 100 * 1.8 = 180)"
    img2 = fz._side_crop(frame, _SCATTERED_PTS, [], anchor=(0.375, 0.5))[0]
    assert np.array_equal(np.asarray(img), np.asarray(img2)), "valid render 결정론(무회귀)"


# ─────────── Test 4 — crop side px 구조 로그 방출 (32-03 parity 재료) ───────────


def test_crop_side_px_log_emitted(caplog):
    """crop 산출 지점에서 user/ref crop side px 구조 로그 방출 (관측 전용).

    32-03 스윕이 user/ref side 비로 수치 parity 를 판정하는 재료. analysis_id 는
    caller 가 넘긴 로그 상관 키."""
    frames = _frames(9)
    user_rep = _report(9, 9.0, {"left_knee": (0.375, 0.5)}, {"left_knee": 0.9})
    ref_rep = _report(9, 9.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    with caplog.at_level(logging.INFO, logger="sunity_shared.analysis.fault_zoom"):
        comps = fz.build_fault_zoom_comparisons(
            frames, frames, user_rep, ref_rep,
            worst_seconds=0.5, fault_joints=["left_knee"],
            joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
            dtw_match=_IDENTITY9, analysis_id="test-analysis-1",
        )
    assert len(comps) == 1
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "user_side_px=" in joined and "ref_side_px=" in joined
    assert "analysis_id=test-analysis-1" in joined
