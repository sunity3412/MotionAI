"""quick-260924-vw2 — 잰 값 조건부 카드(measuredPattern)의 영상 멈춤: 순간 물려받기 + 동그라미 문법.

belle 08-09: 카드 순간 = 합성 영상 멈춤 순간(출처 하나). belle 09-24: 킵업 카드의 각도 선이 어긋났다 —
"동그라미나 다른 표시". 이 테스트가 단언하는 것:
  (1) select_pairs — measuredPattern record 는 record 의 기준 초(atRefVideoSec)를 그대로 쓴다(자세거리 재선정 0),
      다른 record 는 종전 규칙 그대로
  (2) build_timeline — measuredPattern record 는 pairSrc='measured', rt = 물려받은 기준 초, 사이각 선·링 0,
      양 패널 동그라미 재료(circle_viz). 다른 겨드랑이 record 는 종전 사이각 그대로
  (3) 동그라미 재료 — 그 팔 세 점 + 낮은발, 신뢰 하한 미만이면 None, 한쪽이라도 None 이면 양쪽 다 안 그린다
  (4) 그리기 — 브랜드 색 원 두 개가 그 자리에
전부 합성 값 (실좌표/분석 ID 리터럴 0). GPU·S3·Firestore 호출 0.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest
from PIL import Image, ImageDraw

from sunity_shared.analysis import compare_align, compare_render
from sunity_shared.analysis.compare_render import FF

_J17 = (
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)
_FPS = 15.0


def _kp_frames(frames: int, *, ankle_l_y=0.85, ankle_r_y=0.80, conf=0.9, low_conf=()):
    kp = np.full((frames, len(_J17), 2), 0.5, dtype=float)
    pos = {
        "left_shoulder": (0.45, 0.40), "left_elbow": (0.50, 0.46), "left_wrist": (0.55, 0.40),
        "right_shoulder": (0.40, 0.40), "right_elbow": (0.38, 0.30), "right_wrist": (0.55, 0.20),
        "left_hip": (0.44, 0.60), "right_hip": (0.40, 0.60),
        "left_ankle": (0.30, ankle_l_y), "right_ankle": (0.45, ankle_r_y),
    }
    for n, (x, y) in pos.items():
        kp[:, _J17.index(n)] = (x, y)
    sc = np.full((frames, len(_J17)), conf, dtype=float)
    for n in low_conf:
        sc[:, _J17.index(n)] = 0.2
    return kp, sc


def _align(user_frames=90, ref_frames=90, pairs=None, ref_low_conf=()):
    ukp, usc = _kp_frames(user_frames)
    rkp, rsc = _kp_frames(ref_frames, ankle_l_y=0.70, ankle_r_y=0.75, low_conf=ref_low_conf)
    return {
        "fps": _FPS, "joints17": list(_J17),
        "userFrames": user_frames, "refFrames": ref_frames,
        "userKp": ukp.tolist(), "userScore": usc.tolist(),
        "refKp": rkp.tolist(), "refScore": rsc.tolist(),
        "userSize": [640, 1080], "refSize": [640, 1080],
        "curveRefSec": (np.arange(user_frames) / _FPS).tolist(),
        "pairs": pairs or {},
    }


def _doc(records):
    frames = 60
    return {"result": {
        "motionAlignment": {"anchors": [0.0, 0.0, 5.0, 5.0]},
        "keypointReport": {"joints": ["left_shoulder"], "frames": frames, "fps": 9.0,
                           "data": [0.5] * (frames * 2), "confidence": [0.9] * frames},
        "deductionBreakdown": {"records": records},
    }}


def _rec(rid="r00", joint="left_shoulder", *, measured=True, ut=2.1, rt=2.53):
    r = {"recordId": f"{rid}:angle_vs_reference__{joint}", "criterion": f"angle_vs_reference__{joint}",
         "atVideoSec": ut, "statusLine": "상태", "cueLine": "왼팔을 굽혀 옆구리에 붙인 채 돌아보세요"}
    if measured:
        r["measuredPattern"] = "body_low_arm_open"
        r["atRefVideoSec"] = rt
    return r


@pytest.fixture
def audio_dir(tmp_path):
    d = tmp_path / "audio"
    d.mkdir()
    for rid in ("r00", "r01"):
        subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc", "-t", "1",
                        str(d / f"{rid}.mp3")], check=True)
    return d


# ── (1) select_pairs ─────────────────────────────────────────────────────────


def _pair_inputs(fu=90, fr=90):
    D = np.full((fu, fr), 5.0)
    np.fill_diagonal(D, 1.0)            # 자세거리 최소 = 대각선(같은 초)
    curve = np.arange(fu, dtype=float)
    kp, sc = _kp_frames(fu)
    return D, curve, kp, sc, sc


def test_select_pairs_keeps_the_records_reference_second():
    D, curve, ukn, usc, rsc = _pair_inputs()
    pairs = compare_align.select_pairs([_rec(ut=2.0, rt=4.0)], D, curve, ukn, usc, rsc)
    assert pairs["r00"]["atVideoSec"] == 2.0
    assert pairs["r00"]["refVideoSec"] == pytest.approx(4.0)   # 자세거리 최소(2.0s)가 아니라 record 의 초


def test_select_pairs_other_records_keep_the_pose_distance_rule():
    D, curve, ukn, usc, rsc = _pair_inputs()
    pairs = compare_align.select_pairs([_rec(measured=False, ut=2.0)], D, curve, ukn, usc, rsc)
    assert pairs["r00"]["refVideoSec"] == pytest.approx(2.0)


# ── (2) build_timeline ───────────────────────────────────────────────────────


def _timeline(records, align):
    return compare_render.build_timeline(_doc(records), audio_dir_path[0], align=align)


audio_dir_path: list = []


@pytest.fixture(autouse=True)
def _remember_audio_dir(audio_dir):
    audio_dir_path.clear()
    audio_dir_path.append(audio_dir)


def test_measured_freeze_inherits_the_pair_and_draws_circles_only():
    align = _align(pairs={"r00": {"atVideoSec": 2.1, "refVideoSec": 2.53, "marker": None}})
    _warp, freezes, excluded = _timeline([_rec()], align)
    assert not excluded
    (fz,) = freezes
    assert fz["pair_src"] == "measured"
    assert (fz["ut"], fz["rt"]) == (2.1, 2.53)
    assert fz["legs_viz"] is None and fz["markers"] == [] and fz["pole_viz"] is None
    cv = fz["circle_viz"]
    assert cv["user"]["arm"] == [[0.45, 0.40], [0.50, 0.46], [0.55, 0.40]]
    assert cv["user"]["foot"] == [0.30, 0.85]            # 낮은발 = y 큰 왼발목
    assert cv["ref"]["foot"] == [0.45, 0.75]             # 기준은 오른발목이 더 낮다


def test_other_armpit_record_keeps_the_angle_lines(monkeypatch):
    # 합성 키포인트는 정지 상태라 종전 재선정(폴·그립·가중)이 퇴화한다 — 여기서는 "종전 문법이 쓰인다"만 본다.
    monkeypatch.setattr(compare_render, "_pole_prox_pair", lambda *a, **k: None)
    monkeypatch.setattr(compare_render, "_grip_pair", lambda *a, **k: None)
    monkeypatch.setattr(compare_render, "_weighted_repair_pair", lambda *a, **k: None)
    align = _align(pairs={"r01": {"atVideoSec": 2.1, "refVideoSec": 2.53, "marker": None}})
    _warp, freezes, _ex = _timeline([_rec(rid="r01", measured=False)], align)
    (fz,) = freezes
    assert fz["pair_src"] != "measured"
    assert fz["circle_viz"] is None
    assert fz["viz_kind"] == "armpit" and fz["legs_viz"] is not None


def test_one_unreadable_panel_draws_no_circles_on_either_side():
    align = _align(pairs={"r00": {"atVideoSec": 2.1, "refVideoSec": 2.53, "marker": None}},
                   ref_low_conf=("left_elbow",))
    _warp, freezes, _ex = _timeline([_rec()], align)
    (fz,) = freezes
    assert fz["pair_src"] == "measured" and fz["circle_viz"] is None and fz["legs_viz"] is None


# ── (3)(4) 재료 · 그리기 ─────────────────────────────────────────────────────


def test_circle_marks_need_the_arm_and_a_readable_ankle():
    kp_at = compare_render._kp_reader(_align(), "user")
    assert compare_render._circle_marks(kp_at, 1.0, "left") is not None
    assert compare_render._circle_marks(kp_at, 1.0, "middle") is None
    low = _align(ref_low_conf=("left_ankle", "right_ankle"))
    assert compare_render._circle_marks(compare_render._kp_reader(low, "ref"), 1.0, "left") is None


def test_draw_circle_marks_puts_two_brand_rings_where_the_points_are():
    img = Image.new("RGB", (400, 800), (255, 255, 255))
    d = ImageDraw.Draw(img, "RGBA")
    marks = {"arm": [[0.45, 0.40], [0.50, 0.46], [0.55, 0.40]], "foot": [0.30, 0.85]}
    compare_render.draw_circle_marks(d, marks, 0, 400, 800, 1.0)
    px = np.asarray(img)
    brand = np.all(px == np.array(compare_render.BRAND), axis=-1)
    ys, xs = np.nonzero(brand)
    assert brand.sum() > 0
    # 발 원은 발목(120, 680) 둘레 반경 26 링, 팔 원은 세 점 중심(200, ~331) 둘레
    foot = brand[680 - 30:680 + 31, 120 - 30:120 + 31]
    assert foot.sum() > 0 and not brand[680, 120]           # 링(속은 비어 있음)
    arm_c = (int(round(np.mean([180, 200, 220]))), int(round(np.mean([320, 368, 320]))))
    assert not brand[arm_c[1], arm_c[0]]
    assert (np.abs(xs - arm_c[0]) + np.abs(ys - arm_c[1])).min() < 80


# ── (5) 카드 합성 (quick-260924-vw2 Task 3) ─────────────────────────────────


def _frame(h=1080, w=608, color=(200, 200, 200)):
    return Image.new("RGB", (w, h), color)


def test_card_is_two_square_panels_in_the_app_aspect_and_plain_has_no_marks():
    import io

    marks = {"arm": [[0.45, 0.40], [0.50, 0.46], [0.55, 0.40]], "foot": [0.30, 0.85]}
    box = (0.25, 0.30, 0.60, 0.88)
    png, plain = compare_render.circle_card_png(_frame(), _frame(), box, box, marks, marks)
    img = Image.open(io.BytesIO(png)).convert("RGB")
    pl = Image.open(io.BytesIO(plain)).convert("RGB")
    assert img.size == (compare_render.CARD_PANEL * 2 + compare_render.CARD_GAP, compare_render.CARD_PANEL)
    brand = np.all(np.asarray(img) == np.array(compare_render.BRAND), axis=-1)
    assert brand[:, :compare_render.CARD_PANEL].sum() > 0 and brand[:, compare_render.CARD_PANEL + compare_render.CARD_GAP:].sum() > 0
    assert not np.all(np.asarray(pl) == np.array(compare_render.BRAND), axis=-1).any()


def test_card_draws_no_circles_when_one_panel_has_no_marks():
    import io

    marks = {"arm": [[0.45, 0.40], [0.50, 0.46], [0.55, 0.40]], "foot": [0.30, 0.85]}
    box = (0.25, 0.30, 0.60, 0.88)
    png, _plain = compare_render.circle_card_png(_frame(), _frame(), box, box, marks, None)
    assert not np.all(np.asarray(Image.open(io.BytesIO(png)).convert("RGB")) == np.array(compare_render.BRAND), axis=-1).any()


def test_same_box_keeps_heights_comparable_across_panels():
    """두 패널을 같은 상자로 자른다 — 같은 정규화 높이의 점은 두 패널에서 같은 픽셀 높이에 온다."""
    import io

    u = _frame(); r = _frame()
    ImageDraw.Draw(u).rectangle([0, 900, 608, 905], fill=(0, 0, 255))   # y≈0.836 줄
    ImageDraw.Draw(r).rectangle([0, 900, 608, 905], fill=(0, 0, 255))
    png, plain = compare_render.circle_card_png(u, r, (0.3, 0.35, 0.5, 0.80), (0.2, 0.30, 0.6, 0.85), None, None)
    a = np.asarray(Image.open(io.BytesIO(plain)).convert("RGB"))
    P = compare_render.CARD_PANEL
    rows_u = np.nonzero((a[:, :P, 2] > 200) & (a[:, :P, 0] < 60))[0]
    rows_r = np.nonzero((a[:, P + compare_render.CARD_GAP:, 2] > 200) & (a[:, P + compare_render.CARD_GAP:, 0] < 60))[0]
    assert rows_u.size and rows_r.size and abs(int(np.median(rows_u)) - int(np.median(rows_r))) <= 1


def test_person_bbox_uses_readable_points_only():
    align = _align(ref_low_conf=("left_ankle", "right_ankle"))
    ub = compare_render.person_bbox(align, "user", 1.0)
    rb = compare_render.person_bbox(align, "ref", 1.0)
    assert ub[3] == pytest.approx(0.85)          # 학생 왼발목까지
    assert rb[3] < 0.70                          # 기준은 발목이 안 읽혀 상자에서 빠진다


# ── (6) 자막 위치 — 동그라미가 가려질 때만 위로 (vw2 E2E 466ee4c5 에서 발견) ───────────────


_W = 608 * 2 + compare_render.GAP
_S = compare_render.PANEL_H / 640.0
_LINE_H = round(40 * _S)


def _cv(foot_y, arm_y=0.5):
    m = {"arm": [[0.45, arm_y - 0.03], [0.50, arm_y], [0.55, arm_y - 0.03]], "foot": [0.30, foot_y]}
    return {"user": m, "ref": m}


def test_caption_moves_up_only_when_a_circle_is_under_the_bottom_band():
    y0, y1 = compare_render._caption_band(_W, 2, _LINE_H, _S)
    under = (y0 + y1) / 2 / compare_render.PANEL_H
    assert compare_render.caption_should_move_up(_cv(under), _W, 2, _LINE_H, _S) is True
    assert compare_render.caption_should_move_up(_cv(0.55), _W, 2, _LINE_H, _S) is False
    assert compare_render.caption_should_move_up(None, _W, 2, _LINE_H, _S) is False


def test_top_band_sits_inside_the_visible_area_symmetric_to_the_bottom():
    b0, b1 = compare_render._caption_band(_W, 2, _LINE_H, _S)
    t0, t1 = compare_render._caption_band(_W, 2, _LINE_H, _S, at_top=True)
    assert t0 == compare_render.PANEL_H - b1 and t1 - t0 == b1 - b0


def test_caption_stays_down_when_the_top_band_would_hide_a_circle_too():
    t0, t1 = compare_render._caption_band(_W, 2, _LINE_H, _S, at_top=True)
    b0, b1 = compare_render._caption_band(_W, 2, _LINE_H, _S)
    cv = _cv((b0 + b1) / 2 / compare_render.PANEL_H, arm_y=(t0 + t1) / 2 / compare_render.PANEL_H)
    assert compare_render.caption_should_move_up(cv, _W, 2, _LINE_H, _S) is False
