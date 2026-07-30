"""33-G S8/M-1 (quick-260730-l7t Task 3) — 각도 표시 베이크 + 대칭 게이트.

승인 목업 7R#2 확정 기하 (mockups/index.html 619-630 + 770-814행):
  · 꼭짓점 = **겨드랑이** (어깨 관절 아님 — 6R 이 어깨 관절을 썼다가 belle 지적
    "각·호가 90도 넘어 보이고 몸 위쪽에 등장"으로 기각).
  · 학생 겨드랑이 = shoulder->hip 선분 t=0.15 → 승인 known-answer (200,262).
  · 팔 선 64px · 옆구리 선 85px · **호 반경 27->16 축소** (각이 겨드랑이 안쪽에 작게).
  · 두 패널 동일 기하. 실측 사이각 = 기준 129.9도 · 학생 139.8도 (수치 **비노출**).

승인 자산 픽셀 실측 (belle_shoulder_pair_dtwmatch_r7.png, 이 커밋에서 재측정):
  · 선 = 브랜드 코어 약 6px + 흰 halo 양옆 → CSS `.legfx polyline` 코어 5 / halo 9 정합.
  · 호 = **흰 단색** r 13..16 (브랜드 코어 없음) → 호는 halo 색으로만 그린다.
  · 학생 패널 실측: 팔 선 65.3px @ -105.1도 · 옆구리 선 84.3px @ 112.3도.
  · 기준 패널 실측: 64.8px @ -76.6도 · 84.4px @ 53.7도 → 사이각 130.3도 (문서 129.9도).

대칭 게이트 (M-4): user·ref **둘 다** 스펙이 성립할 때만 두 패널에 그린다.
기준 report(phase4_v1 legacy 8관절)에 elbow/ankle 이 없으면 앵커 대입 선언이
채워질 때까지 양쪽 모두 각도 없이 원 마커로 폴백한다 (L-7 fail-closed).

순수 — PIL/numpy 외 의존 0. 채점 무접촉(D-44).
"""

from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from sunity_shared.analysis import fault_zoom as fz


# ─────────── 합성 fixture ───────────


@dataclass
class _Match:
    start: int
    path: list


_IDENTITY9 = _Match(start=0, path=[(i, i) for i in range(9)])


def _frames(n: int = 9, h: int = 640, w: int = 360) -> np.ndarray:
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    a[:, :, :, :] = 90   # 중간 회색 — 흰 halo / 브랜드 코어 모두 검출 가능
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


# 승인 7R 학생 패널 실좌표 (doc keypointReport, mockups/index.html 774-776행).
_R7_STUDENT = {
    "left_shoulder": (0.564, 0.397),
    "left_elbow": (0.516, 0.336),
    "left_hip": (0.505, 0.475),
}
# 기준 8kp 형상 (phase4_v1 legacy — elbow/ankle 부재).
_REF8 = {
    "left_shoulder": (0.50, 0.30),
    "left_hip": (0.48, 0.55),
    "left_hand": (0.40, 0.10),
    "right_shoulder": (0.60, 0.30),
    "right_hip": (0.56, 0.55),
    "left_knee": (0.46, 0.80),
    "right_knee": (0.62, 0.80),
    "right_hand": (0.70, 0.12),
}

_BRAND = np.array([255, 75, 51])


def _clusters(panel: np.ndarray, vertex=(fz._OUT // 2, fz._OUT // 2)):
    """브랜드 코어 픽셀을 두 선(각 방향)으로 나눠 (길이, 각도) 반환."""
    mask = np.abs(panel.astype(int) - _BRAND[None, None, :]).sum(axis=2) < 40
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return []
    d = np.hypot(xs - vertex[0], ys - vertex[1])
    ang = np.degrees(np.arctan2(ys - vertex[1], xs - vertex[0]))
    out = []
    # 각도 히스토그램 최빈 2방향으로 분리 (far 픽셀만).
    far = d > 20
    if far.sum() == 0:
        return []
    bins = {}
    for a, dd in zip(ang[far], d[far]):
        bins.setdefault(int(a // 20) * 20, []).append((a, dd))
    for _k, vs in sorted(bins.items(), key=lambda kv: -len(kv[1]))[:2]:
        out.append((max(v[1] for v in vs), float(np.mean([v[0] for v in vs]))))
    return out


# ─────────── 1. 상수 · 맵 계약 ───────────


def test_geometry_constants_match_approved_7r():
    assert fz._ANGLE_LIMB_LEN_FRAC == 64.0 / 360.0
    assert fz._ANGLE_TORSO_LEN_FRAC == 85.0 / 360.0
    assert fz._ANGLE_ARC_R_FRAC == 16.0 / 360.0
    # _OUT == 360 이라 승인본 px 와 1:1.
    assert round(fz._ANGLE_LIMB_LEN_FRAC * fz._OUT) == 64
    assert round(fz._ANGLE_TORSO_LEN_FRAC * fz._OUT) == 85
    assert round(fz._ANGLE_ARC_R_FRAC * fz._OUT) == 16


def test_angle_bake_map_is_suffix_keyed_no_side_no_motion():
    """관절명 **접미사**로만 키잉 — 좌우 접두사·동작명 분기 0 (D-41)."""
    for k, v in fz.ANGLE_BAKE_MAP.items():
        assert not k.startswith(("left_", "right_")), k
        assert not k.startswith("ref-"), k
        assert isinstance(v, tuple) and len(v) == 2
    assert fz.ANGLE_BAKE_MAP["shoulder"] == ("elbow", "hip")
    assert fz.ANGLE_BAKE_MAP["hip"] == ("knee", "shoulder")
    assert fz.ANGLE_BAKE_MAP["knee"] == ("ankle", "hip")
    assert fz.ANGLE_BAKE_MAP["elbow"] == ("hand", "shoulder")


# ─────────── 2. 선-쌍 스펙 (known-answer) ───────────


def test_build_angle_bake_spec_known_answer_shoulder():
    """승인 7R 학생 스펙: 꼭짓점 (200,262) · 팔 = elbow · 몸통 = hip."""
    rep = _report(3, 9.0, _R7_STUDENT)
    spec = fz.build_angle_bake_spec(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep, 0
    )
    assert spec is not None
    vertex, limb, torso = spec
    assert (round(vertex[0] * 360), round(vertex[1] * 640)) == (200, 262)
    assert limb == _R7_STUDENT["left_elbow"]
    assert torso == _R7_STUDENT["left_hip"]


def test_known_answer_inner_angle_matches_approved_measurement():
    """승인 7R 학생 실측 사이각 139.8도 재현 (등방 frame px 공간)."""
    rep = _report(3, 9.0, _R7_STUDENT)
    vertex, limb, torso = fz.build_angle_bake_spec(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep, 0
    )
    px = lambda p: (p[0] * 360, p[1] * 640)  # noqa: E731
    deg = fz.joint_inner_angle_deg(px(limb), px(vertex), px(torso))
    assert abs(deg - 139.8) < 1.0, deg


def test_spec_none_for_unmapped_joint_suffix():
    rep = _report(3, 9.0, {**_R7_STUDENT, "left_hand": (0.4, 0.1)})
    assert fz.build_angle_bake_spec(
        "angle_vs_reference__left_hand", ("left_hand",), rep, 0
    ) is None
    # 다관절/split criterion 도 각도 베이크 대상 아님 (다리 사이각이 담당).
    assert fz.build_angle_bake_spec(
        "split_angle", ("left_hip", "right_hip"), rep, 0
    ) is None
    assert fz.build_angle_bake_spec(
        "leg_extension", ("left_hip", "left_knee"), rep, 0
    ) is None


def test_spec_none_when_reference_lacks_direction_joint():
    """기준 8kp 는 elbow 부재 → 어깨 스펙 미성립 (L-7 fail-closed)."""
    ref = _report(3, 9.0, _REF8)
    assert fz.build_angle_bake_spec(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), ref, 0
    ) is None


def test_spec_recovers_with_anchor_resolver():
    ref = _report(3, 9.0, _REF8)
    resolver = fz.make_reference_anchor_resolver(
        "m", "angle_vs_reference__left_shoulder",
        anchors={"angle_vs_reference__left_shoulder": {
            "joint_substitutions": {"left_elbow": "left_hand"}, "note": "t",
        }},
    )
    spec = fz.build_angle_bake_spec(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), ref, 0,
        resolver=resolver,
    )
    assert spec is not None
    assert spec[1] == _REF8["left_hand"]


def test_knee_and_hip_specs_use_declared_direction_joints():
    xy = {
        "left_hip": (0.45, 0.40), "left_knee": (0.42, 0.62),
        "left_ankle": (0.38, 0.86), "left_shoulder": (0.47, 0.20),
    }
    rep = _report(3, 9.0, xy)
    v, limb, torso = fz.build_angle_bake_spec(
        "angle_vs_reference__left_knee", ("left_knee",), rep, 0
    )
    assert v == xy["left_knee"] and limb == xy["left_ankle"] and torso == xy["left_hip"]
    v, limb, torso = fz.build_angle_bake_spec(
        "angle_vs_reference__left_hip", ("left_hip",), rep, 0
    )
    assert v == xy["left_hip"] and limb == xy["left_knee"]
    assert torso == xy["left_shoulder"]


# ─────────── 3. 렌더 기하 ───────────


def _draw_on_blank(spec, w=360, h=640):
    """스펙을 정중앙 crop 좌표계로 옮겨 blank 패널에 그린다."""
    vertex, limb, torso = spec
    side = round(min(h, w) * fz._CRITERION_CROP_FRAC)
    left, top, side = fz._crop_box_centered(h, w, vertex[0], vertex[1], side)
    img = Image.new("RGB", (fz._OUT, fz._OUT), (90, 90, 90))
    ok = fz._draw_joint_angle(
        img,
        fz._to_crop_px(vertex, left, top, side, w, h),
        fz._to_crop_px_unclamped(limb, left, top, side, w, h),
        fz._to_crop_px_unclamped(torso, left, top, side, w, h),
    )
    return ok, np.asarray(img)


def test_drawn_lines_have_approved_fixed_lengths_and_angles():
    """팔 선 64px · 옆구리 선 85px · 승인 자산 실측 각도 재현."""
    rep = _report(3, 9.0, _R7_STUDENT)
    spec = fz.build_angle_bake_spec(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep, 0
    )
    ok, arr = _draw_on_blank(spec)
    assert ok
    cl = _clusters(arr)
    assert len(cl) == 2, cl
    lens = sorted(c[0] for c in cl)
    # round cap(width 5) 여유 포함.
    assert abs(lens[0] - 64) <= 6, lens
    assert abs(lens[1] - 85) <= 6, lens
    angs = sorted(c[1] for c in cl)
    # 승인 자산 실측 -105.1도 / 112.3도.
    assert abs(angs[0] - (-105.1)) < 6, angs
    assert abs(angs[1] - 112.3) < 6, angs


def test_arc_is_white_only_at_radius_16():
    """호 = 흰 단색 r16 (승인 자산 픽셀 실측 — 브랜드 코어 없음)."""
    rep = _report(3, 9.0, _R7_STUDENT)
    spec = fz.build_angle_bake_spec(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep, 0
    )
    _ok, arr = _draw_on_blank(spec)
    c = fz._OUT // 2
    # minor arc 는 두 선(-105.1도 / 112.3도) 사이 = ±180도 를 지나는 쪽.
    hits = 0
    for deg in (150, 165, 180, -175, -160):
        for r in (13, 14, 15, 16):
            x = int(round(c + r * math.cos(math.radians(deg))))
            y = int(round(c + r * math.sin(math.radians(deg))))
            if tuple(arr[y, x]) == (255, 255, 255):
                hits += 1
    assert hits >= 12, f"흰 호가 r13..16 에 없음 (hits={hits})"
    # 반대쪽(major arc 영역)에는 호가 없어야 한다.
    misses = 0
    for deg in (0, 20, -20):
        for r in (13, 14, 15, 16):
            x = int(round(c + r * math.cos(math.radians(deg))))
            y = int(round(c + r * math.sin(math.radians(deg))))
            if tuple(arr[y, x]) == (255, 255, 255):
                misses += 1
    assert misses == 0, f"major arc 쪽에 호가 그려짐 (misses={misses})"


def test_lines_have_white_halo_around_brand_core():
    """흰 halo 아래 + 브랜드 코어 위 — 어떤 배경에서도 읽히게 (승인 자산 정합)."""
    rep = _report(3, 9.0, _R7_STUDENT)
    spec = fz.build_angle_bake_spec(
        "angle_vs_reference__left_shoulder", ("left_shoulder",), rep, 0
    )
    _ok, arr = _draw_on_blank(spec)
    c = fz._OUT // 2
    vertex, limb, _torso = spec
    # 팔 선 방향 60% 지점에서 수직 스캔 → W R... R W 패턴.
    ux, uy = limb[0] * 360 - vertex[0] * 360, limb[1] * 640 - vertex[1] * 640
    n = math.hypot(ux, uy)
    ux, uy = ux / n, uy / n
    mx, my = c + ux * 40, c + uy * 40
    px, py = -uy, ux
    row = ""
    for t in range(-8, 9):
        x, y = int(round(mx + px * t)), int(round(my + py * t))
        p = tuple(arr[y, x])
        row += "R" if abs(p[0] - 255) + abs(p[1] - 75) + abs(p[2] - 51) < 40 else (
            "W" if p == (255, 255, 255) else "."
        )
    assert "W" in row and "R" in row, row
    assert row.index("R") > row.index("W"), f"halo 가 코어 밖에 없음: {row}"


def test_degenerate_vectors_omit_drawing():
    img = Image.new("RGB", (fz._OUT, fz._OUT), (90, 90, 90))
    c = fz._OUT // 2
    assert fz._draw_joint_angle(img, (c, c), (c + 2, c), (c, c + 40)) is False
    assert np.asarray(img).std() == 0.0, "degenerate 인데 뭔가 그려짐"


def test_minor_arc_helper_is_single_source_for_leg_angle(monkeypatch):
    """다리 사이각도 같은 helper 를 쓴다 (중복 공식 금지)."""
    calls = []
    orig = fz._minor_arc_span_deg

    def spy(*a):
        calls.append(a)
        return orig(*a)

    monkeypatch.setattr(fz, "_minor_arc_span_deg", spy)
    img = Image.new("RGB", (fz._OUT, fz._OUT), (90, 90, 90))
    assert fz._draw_leg_angle(img, (180, 180), (120, 260), (240, 260)) is True
    assert len(calls) == 1, "_draw_leg_angle 이 helper 를 쓰지 않음"


# ─────────── 4. 대칭 게이트 · 통합 ───────────


def _spy_draw(monkeypatch):
    rec = {"arc": [], "line": [], "ellipse": [], "text": [], "polygon": []}
    for name in list(rec):
        orig = getattr(ImageDraw.ImageDraw, name)

        def make(n, o):
            def f(self, *a, **k):
                rec[n].append(a)
                return o(self, *a, **k)
            return f

        monkeypatch.setattr(ImageDraw.ImageDraw, name, make(name, orig))
    return rec


def _build_shoulder_card(**kw):
    frames = _frames()
    user_rep = _report(9, 9.0, _R7_STUDENT)
    ref_rep = _report(9, 9.0, _REF8)
    base = dict(
        worst_seconds=0.5, fault_joints=["left_shoulder"],
        joint_deltas={"left_shoulder": 34.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9,
        criterion_units=[{
            "criterion": "angle_vs_reference__left_shoulder",
            "joints": ("left_shoulder",),
            "region": None,
        }],
    )
    base.update(kw)
    return fz.build_fault_zoom_comparisons(frames, frames, user_rep, ref_rep, **base)


def test_symmetric_gate_neither_panel_drawn_without_annotation(monkeypatch):
    """기준측 스펙 미성립 → 양쪽 모두 각도 미드로잉 + 원 마커 폴백 (M-4)."""
    rec = _spy_draw(monkeypatch)
    comps = _build_shoulder_card()
    assert len(comps) == 1
    assert rec["arc"] == [], "한쪽만 각도가 그려짐 — 비대칭 (M-4 재발)"
    assert rec["ellipse"], "원 마커 폴백이 없음"


def test_symmetric_bake_when_annotation_present(monkeypatch):
    """앵커 주석 있으면 두 패널 모두 각도 베이크 (선 2 + 호)."""
    rec = _spy_draw(monkeypatch)
    comps = _build_shoulder_card(
        motion_id="m",
        reference_anchor_overrides={
            "angle_vs_reference__left_shoulder": {
                "joint_substitutions": {"left_elbow": "left_hand"}, "note": "t",
            }
        },
    )
    assert len(comps) == 1
    assert len(rec["arc"]) == 2, f"두 패널 호 2개여야 함: {len(rec['arc'])}"
    # 선 = 패널당 halo 2 + 코어 2 = 4 → 두 패널 8.
    assert len(rec["line"]) == 8, len(rec["line"])
    # 각도를 그린 카드는 원 마커·화살표 생략 (시각 언어 충돌 방지).
    assert rec["ellipse"] == [], "각도 카드에 원 마커가 남음"


def test_angle_bake_geometry_identical_across_panels(monkeypatch):
    """두 패널 선 길이·호 반경이 동일 기하 (승인본 '두 패널 동일')."""
    comps = _build_shoulder_card(
        motion_id="m",
        reference_anchor_overrides={
            "angle_vs_reference__left_shoulder": {
                "joint_substitutions": {"left_elbow": "left_hand"}, "note": "t",
            }
        },
    )
    img = np.asarray(Image.open(io.BytesIO(comps[0]["png"])).convert("RGB"))
    u = _clusters(img[:, :fz._OUT, :])
    r = _clusters(img[:, fz._OUT + 6:, :])
    assert len(u) == 2 and len(r) == 2
    assert abs(sorted(c[0] for c in u)[0] - sorted(c[0] for c in r)[0]) <= 2
    assert abs(sorted(c[0] for c in u)[1] - sorted(c[0] for c in r)[1]) <= 2


def test_split_card_keeps_leg_angle_no_double_draw(monkeypatch):
    """다리 사이각 카드는 기존 경로 유지 — 각도 베이크와 이중 드로잉 0."""
    rec = _spy_draw(monkeypatch)
    frames = _frames()
    legs = {
        "left_hip": (0.42, 0.35), "right_hip": (0.58, 0.35),
        "left_knee": (0.30, 0.72), "right_knee": (0.70, 0.72),
    }
    rep = _report(9, 9.0, legs)
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, rep, rep,
        worst_seconds=0.5, fault_joints=list(legs),
        joint_deltas={"left_knee": 40.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9, split_angle_present=True,
        criterion_units=[{
            "criterion": "split_angle", "joints": tuple(legs), "region": "legs",
        }],
    )
    assert len(comps) == 1
    # 사이각 = 패널당 호 1 → 두 패널 2. 각도 베이크가 겹쳐 그리면 4가 된다.
    assert len(rec["arc"]) == 2, len(rec["arc"])


_TS_RE = re.compile(r"^\d+(\.\d)?s$")


def test_no_numeric_labels_baked(monkeypatch):
    """숫자 라벨 0 — 타임스탬프 외 텍스트 금지 (belle 2026-07-28)."""
    rec = _spy_draw(monkeypatch)
    _build_shoulder_card(
        motion_id="m",
        reference_anchor_overrides={
            "angle_vs_reference__left_shoulder": {
                "joint_substitutions": {"left_elbow": "left_hand"}, "note": "t",
            }
        },
    )
    texts = [str(a[1]) for a in rec["text"] if len(a) > 1]
    offenders = [t for t in texts if not _TS_RE.match(t)]
    assert offenders == [], offenders
