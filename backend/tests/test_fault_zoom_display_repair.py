"""quick-260813-fxx — 확정 카드 표시 좌표 align 단일 출처 + 골반 P3 하이브리드.

belle 라운드 3 최종 판정(08-13, JUDGMENT.md locked)의 운영 배선을 순수 함수
수준에서 고정한다 — AWS/네트워크/GPU 0, 합성 keypoint report + 프로덕션 함수
직접 호출 (test_fault_zoom_record_moment.py 픽스처 관례):

  1. 스펙 평행이동(shift_bake_spec)은 px-공간 V 사이각을 보존한다 — round3
     `_R3Patch._repaired_pts` 와 동치 (방향점 재측정 금지, 앵커만 수리).
  2. 하이브리드 ghost 게이팅: 델타 >= 8.0 도일 때만 고스트 점선 (경계 7.9
     미방출, 8.0 방출) — bz5 _GHOST_MIN_DELTA_DEG 이식값 그대로.
  3. display_anchor=None 하위호환: 기존 시그니처 호출과 display_anchor=None
     명시 호출의 산출 PNG 가 byte-동일 (legacy/advisory/mode3 무회귀의 근거).
     display_anchor 지정 시에는 산출이 실제로 바뀐다 (배선 no-op 방지).
  4. _draw_hybrid_joint_angle 은 합성 이미지에서 True, degenerate 방향
     벡터(len < _MIN_LEG_VEC_PX)면 False.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

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


def _build_hip(**kw):
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
        analysis_id="t-fxx",
        **kw,
    )


def _inner_deg_px(v, a, b):
    ua = (a[0] - v[0], a[1] - v[1])
    ub = (b[0] - v[0], b[1] - v[1])
    na, nb = math.hypot(*ua), math.hypot(*ub)
    d = (ua[0] * ub[0] + ua[1] * ub[1]) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


# ── 1. 평행이동 사이각 보존 ─────────────────────────────────────────────────


def test_shift_bake_spec_preserves_px_inner_angle():
    spec = ((0.505, 0.475), (0.402, 0.628), (0.564, 0.397))
    anchor = (0.531, 0.446)  # 임의 새 vertex (align 게이트 순간 좌표 대역)
    shifted = fz.shift_bake_spec(spec, anchor)
    # 꼭짓점 == anchor 정확 일치 (앵커 교체가 배선의 목적)
    assert shifted[0][0] == pytest.approx(anchor[0], abs=1e-12)
    assert shifted[0][1] == pytest.approx(anchor[1], abs=1e-12)
    # px 공간(비정방 프레임 → 종횡비 왜곡 존재)에서도 내각 보존 — 평행이동은
    # 아핀 px 변환과 교환 가능하다 (translation 만이라 각 불변).
    box = (7, 13, 61)
    w, h = 96, 128
    before = [fz._to_crop_px_unclamped(p, *box, w, h) for p in spec]
    after = [fz._to_crop_px_unclamped(p, *box, w, h) for p in shifted]
    a0 = _inner_deg_px(before[0], before[1], before[2])
    a1 = _inner_deg_px(after[0], after[1], after[2])
    assert abs(a0 - a1) < 1e-9


def test_shift_bake_spec_none_passthrough():
    assert fz.shift_bake_spec(None, (0.5, 0.5)) is None
    spec = ((0.5, 0.5), (0.6, 0.6), (0.4, 0.4))
    assert fz.shift_bake_spec(spec, None) == spec


# ── 2. 하이브리드 ghost 게이팅 (델타 >= 8.0 도) ─────────────────────────────

_GHOST_CORE = (60, 60, 60)


def _hybrid_img(ref_inner_deg):
    img = Image.new("RGB", (360, 360), (200, 200, 200))
    v = (180.0, 180.0)
    limb = (280.0, 180.0)   # +x → user 내각 90도
    torso = (180.0, 280.0)  # +y
    ok = fz._draw_hybrid_joint_angle(img, v, limb, torso, ref_inner_deg)
    assert ok is True
    return np.asarray(img)


def _has_ghost(arr):
    return bool(np.any(np.all(arr == np.array(_GHOST_CORE), axis=-1)))


def test_hybrid_ghost_below_threshold_omitted():
    # user 90도 vs ref 97.9도 → 델타 7.9 < 8.0 → 고스트 점선 미방출
    assert not _has_ghost(_hybrid_img(97.9))


def test_hybrid_ghost_at_threshold_emitted():
    # 델타 정확 8.0 → 방출 (>= 경계 포함 — bz5 이식값 그대로)
    assert _has_ghost(_hybrid_img(98.0))


# ── 3. display_anchor 하위호환 (None = 무변경) + 실배선 (지정 = 변경) ────────


def test_display_anchor_none_is_byte_identical():
    base = _build_hip()
    explicit = _build_hip(display_anchor=None)
    assert len(base) == 1 and len(explicit) == 1
    assert base[0]["png"] == explicit[0]["png"]


def test_display_anchor_moves_the_card():
    base = _build_hip()
    moved = _build_hip(display_anchor={
        # rep12 vertex(0.505, 0.475)에서 유의미하게 이동한 align 좌표 가정
        "user": (0.545, 0.435), "ref": (0.545, 0.435),
    })
    assert len(base) == 1 and len(moved) == 1
    assert base[0]["png"] != moved[0]["png"]


# ── 4. _draw_hybrid_joint_angle 성립/degenerate ─────────────────────────────


def test_hybrid_draw_true_on_synthetic():
    img = Image.new("RGB", (360, 360), (200, 200, 200))
    ok = fz._draw_hybrid_joint_angle(
        img, (180.0, 180.0), (280.0, 180.0), (180.0, 280.0), 120.0
    )
    assert ok is True
    # 쐐기/실선이 실제로 찍혔다 (배경색만 남지 않음)
    assert np.asarray(img).std() > 0


def test_hybrid_draw_false_on_degenerate_vector():
    img = Image.new("RGB", (360, 360), (200, 200, 200))
    before = np.asarray(img).copy()
    ok = fz._draw_hybrid_joint_angle(
        img,
        (180.0, 180.0),
        (180.0 + fz._MIN_LEG_VEC_PX - 1.0, 180.0),  # len < _MIN_LEG_VEC_PX
        (180.0, 280.0),
        120.0,
    )
    assert ok is False
    # False 면 드로잉 0 (부분 드로잉 금지 — copy-then-commit 계약)
    assert np.array_equal(before, np.asarray(img))


# ── 5. align_bake B 스펙 (quick-260813-nh4 — m0k seam 1/2 운영판) ────────────
#
# belle 08-13 채택: rep12 스펙/멤버 미성립 측만 게이트 freeze 순간 align
# 좌표로 폴백. conf 게이트는 호출측(app.py) 소유 — payload 는 통과 점만.

_HIP_BAKE_PTS = {
    "left_hip": (0.505, 0.475),
    "left_knee": (0.402, 0.628),      # 사지 (ANGLE_BAKE_MAP hip → knee)
    "left_shoulder": (0.564, 0.397),  # 몸통 (ANGLE_BAKE_MAP hip → shoulder)
}


def _report_conf(xy, conf_by_joint=None):
    """`_report` 변형 — 관절별 confidence override (relaxed/저신뢰 합성)."""
    joints = list(xy)
    data: list[float] = []
    conf: list[float] = []
    for _f in range(_N):
        for j in joints:
            data += list(xy[j])
            conf.append((conf_by_joint or {}).get(j, 0.9))
    return {"joints": joints, "frames": _N, "fps": _FPS,
            "data": data, "confidence": conf}


def _build_hip_reports(user_report, **kw):
    """user report 를 바꾼 left_hip 확정 카드 빌드 (_build_hip 미러)."""
    return fz.build_fault_zoom_comparisons(
        _frames(), _frames(),
        user_report, _report(_REF_KP),
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
        analysis_id="t-nh4",
        **kw,
    )


def test_align_bake_spec_unit():
    members = ("left_hip",)
    crit = "angle_vs_reference__left_hip"
    spec = fz.align_bake_spec(crit, members, _HIP_BAKE_PTS)
    assert spec == (
        _HIP_BAKE_PTS["left_hip"], _HIP_BAKE_PTS["left_knee"],
        _HIP_BAKE_PTS["left_shoulder"],
    )
    # 3점 중 1점 부재 = None (환각 좌표 금지 — 정직한 침묵 유지)
    partial = {k: v for k, v in _HIP_BAKE_PTS.items() if k != "left_shoulder"}
    assert fz.align_bake_spec(crit, members, partial) is None
    # payload 없음 / 미선언 접미사 / 다관절 criterion = None
    assert fz.align_bake_spec(crit, members, None) is None
    assert fz.align_bake_spec(
        "angle_vs_reference__left_wrist", ("left_wrist",), _HIP_BAKE_PTS
    ) is None
    assert fz.align_bake_spec(
        "leg_extension", ("left_knee", "right_knee"), _HIP_BAKE_PTS
    ) is None


def test_align_bake_none_is_byte_identical():
    base = _build_hip()
    explicit = _build_hip(align_bake=None)
    empty = _build_hip(align_bake={"user": {}, "ref": {}})
    assert len(base) == len(explicit) == len(empty) == 1
    assert base[0]["png"] == explicit[0]["png"]
    assert base[0]["png"] == empty[0]["png"]


def test_align_bake_recovers_v_when_rep12_spec_fails(caplog):
    # user report 에서 사지 방향 관절(left_knee) 제거 → rep12 u_spec None.
    user_kp = {k: v for k, v in _USER_KP.items() if k != "left_knee"}
    caplog.set_level("INFO")
    base = _build_hip_reports(_report(user_kp))
    assert len(base) == 1
    assert any(
        "angle_bake=omitted:user_gate" in r.getMessage()
        for r in caplog.records
    )
    caplog.clear()
    recovered = _build_hip_reports(
        _report(user_kp),
        align_bake={"user": dict(_HIP_BAKE_PTS), "ref": {}},
    )
    assert len(recovered) == 1
    # align 유도 스펙으로 V 성립 (hip = 하이브리드 문법)
    assert any(
        "angle_bake=drawn" in r.getMessage() for r in caplog.records
    )
    assert recovered[0]["png"] != base[0]["png"]


def test_align_bake_partial_payload_keeps_honest_silence(caplog):
    # payload 가 3점 중 1점(몸통) 미달 → V 생략 + 산출 byte-동일 (침묵 유지).
    user_kp = {k: v for k, v in _USER_KP.items() if k != "left_knee"}
    base = _build_hip_reports(_report(user_kp))
    caplog.set_level("INFO")
    partial = {
        k: v for k, v in _HIP_BAKE_PTS.items() if k != "left_shoulder"
    }
    silent = _build_hip_reports(
        _report(user_kp), align_bake={"user": partial, "ref": {}},
    )
    assert len(base) == len(silent) == 1
    assert any(
        "angle_bake=omitted:user_gate" in r.getMessage()
        for r in caplog.records
    )
    assert silent[0]["png"] == base[0]["png"]


def test_align_bake_valid0_member_fallback(caplog):
    # user left_hip conf 0.2 → _member_pts valid 0 (relaxed 크롭 강하).
    low = _report_conf(_USER_KP, {"left_hip": 0.2})
    caplog.set_level("INFO")
    base = _build_hip_reports(low)
    assert len(base) == 1
    assert any(
        "angle_bake=omitted:user_crop_relaxed" in r.getMessage()
        for r in caplog.records
    )
    caplog.clear()
    # seam 2 — align 점이 valid 자리에 폴백 (relaxed 자리 주입이었다면
    # u_kind 가 relaxed 로 남아 V 진입 자체가 불가) + seam 1 — rep12 vertex
    # 저신뢰라 u_spec None → align 유도 스펙. 둘이 함께 카드+V 를 회복한다
    # (m0k member_conf_zero 소생 경로의 합성 재현).
    recovered = _build_hip_reports(
        low, align_bake={"user": dict(_HIP_BAKE_PTS), "ref": {}},
    )
    assert len(recovered) == 1
    assert any(
        "angle_bake=drawn" in r.getMessage() for r in caplog.records
    )
    assert recovered[0]["png"] != base[0]["png"]
