"""quick-260906-n2j — stage-1·advisory 카드도 앵커 부위 확인 게이트를 지난다.

09-06 j8g 라이브: 게이트를 gated(멈춤 상속) 경로에만 붙였더니 pdshape 문서에 틀린 표시가
3장 남았고 그 중 1장은 **advisory** 카드였다(기계 눈이 얼굴 위 목에 표시가 있다고 5/5).
stage-1·advisory 는 카드 여러 장을 `build_fault_zoom_comparisons` **한 번**에 만들기 때문에
호출 전체에 걸리는 `suppress_marks` 로는 카드별 판정을 실을 수 없다 — 카드마다 부르는
콜백이 필요하다.

여기서 잠그는 것:
  ① 콜백은 카드마다 1회, `_side_crop` 이 실제로 쓴 **크롭 중심**(vertex 우선, 없으면
     anchor)과 kind 를 양측 모두 받는다 — 게이트가 검사할 좌표가 카드가 보여주는
     좌표와 같아야 한다.
  ② 반환한 측만 억제된다. **카드는 그대로 나간다** (belle 09-03 규칙 1
     "검사는 표시만 정한다") — 장수 불변.
     ★ quick-260919-o8v (belle 2026-09-18 규칙 2) 개정: 억제가 지우는 것은 **원
     마커·화살표뿐**이고 각도·사이각은 남는다. 이 파일의 픽스처 카드 2장은
     `angle_bake=drawn`(shoulder/knee 접미사 + conf 0.9, 2026-09-19 로그 실측)이라
     억제돼도 그림과 인증이 함께 산다 — 그래서 아래 ②·⑤ 의 기대값이 뒤집혔다.
     플래그가 더 이상 "반환한 측만"의 증인이 아니므로 **증인을 억제 로그로 바꾼다**
     (시험 삭제 0 — phase33/test_zoom_join_joint_exact.py:199 선례).
     각도가 없어 원만 그리던 카드의 억제는 종전 그대로이고, 그쪽 경계는
     tests/test_fault_zoom_suppress_keeps_angle.py 가 잠근다.
  ③ 콜백 예외 = fail-open. 검사가 깨져도 카드도 표시도 살아남는다.
  ④ 콜백 미전달 = 종전 동작 불변 (png 바이트까지).
  ⑤ 기존 `suppress_marks` 와 **합집합** — 두 출처가 서로를 지우지 않는다.

전부 합성 keypoint report + 프로덕션 함수 직접 호출 — GPU/S3/네트워크/눈 0.
"""

from __future__ import annotations

import io
import logging
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

_FPS = 12.0
_N = 24
_SIZE = 96

_KP = {
    "left_shoulder": (0.564, 0.397), "right_shoulder": (0.612, 0.372),
    "left_hip": (0.505, 0.475), "right_hip": (0.548, 0.462),
    "left_knee": (0.402, 0.628), "right_knee": (0.612, 0.652),
    "left_hand": (0.470, 0.196), "right_hand": (0.628, 0.184),
    "left_ankle": (0.386, 0.792), "right_ankle": (0.640, 0.804),
    "left_elbow": (0.498, 0.288), "right_elbow": (0.640, 0.272),
}


class _Match:
    def __init__(self, start, path):
        self.start = start
        self.path = path


def _identity(n=_N):
    return _Match(0, [(i, i) for i in range(n)])


def _report(xy=None, conf=0.9):
    xy = xy or _KP
    names = list(xy)
    data: list[float] = []
    confs: list[float] = []
    for _f in range(_N):
        for j in names:
            data += list(xy[j])
            confs.append(float(conf))
    return {"joints": names, "frames": _N, "fps": _FPS,
            "data": data, "confidence": confs}


def _frames():
    base = np.full((_N, _SIZE, _SIZE, 3), 120, dtype=np.uint8)
    for f in range(_N):
        base[f, 0, 0, :] = np.uint8((f * 11) % 256)
    return base


def _brand_px_left_panel(png: bytes) -> int:
    """합성 PNG 왼쪽(학생) 패널의 브랜드색 픽셀 수 — 표시가 그려졌는지의 픽셀 증거.

    tests/test_fault_zoom.py 복제 (테스트 모듈 간 import 금지 관행).
    """
    arr = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))[:, : fz._OUT, :]
    return int(np.all(arr == np.asarray(fz._BRAND, dtype=np.uint8), axis=-1).sum())


def _suppressed_sides_by_criterion(caplog) -> dict[str, str]:
    """`fault_zoom_marks_suppressed` 로그 → {criterion: "user,ref"}.

    quick-260919-o8v — 억제가 각도를 더 이상 지우지 않으면서 userMarked/refMarked 는
    "어느 측이 억제됐는가"의 증인이 아니게 됐다. 억제가 **카드마다 / 두 출처의
    합집합으로** 성립하는지는 이 로그로 잠근다 (판정 자체는 무접촉이므로 로그가
    유일하게 남은 관측점이다).
    """
    out: dict[str, str] = {}
    pat = re.compile(
        r"fault_zoom_marks_suppressed analysis_id=\S+ criterion=(\S+) sides=(\S+)"
    )
    for rec in caplog.records:
        m = pat.search(rec.getMessage())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _unit(criterion, joints, region=None):
    return {"criterion": criterion, "joints": tuple(joints),
            "region": region, "at_frame_idx": None}


_UNITS = [
    _unit("angle_vs_reference__left_shoulder", ["left_shoulder"]),
    _unit("angle_vs_reference__right_knee", ["right_knee"]),
]


def _build(units=None, **kw):
    units = _UNITS if units is None else units
    joints: list[str] = []
    for u in units:
        for j in u["joints"]:
            if j not in joints:
                joints.append(j)
    return fz.build_fault_zoom_comparisons(
        _frames(), _frames(),
        _report(), _report(),
        worst_seconds=1.0,
        fault_joints=joints,
        joint_deltas={j: 20.0 for j in joints},
        frames_fps=_FPS,
        joint_kinds={j: "deficit" for j in joints},
        dtw_match=_identity(),
        criterion_units=units,
        user_frame_candidates=[8, 9, 10, 11, 12],
        ref_frame_candidates=[8, 9, 10, 11, 12],
        analysis_id="t",
        **kw,
    )


# ── ① 카드마다 1회, 카드가 실제로 쓴 크롭 중심을 받는다 ──────────────────────


def test_anchor_check_called_once_per_card_with_crop_centers():
    seen: list[dict] = []

    def _cb(ctx):
        seen.append(ctx)
        return frozenset()

    items = _build(anchor_check=_cb)
    assert items, "카드가 안 나오면 이 게이트는 성립하지 않는다"
    assert len(seen) == len(items), "콜백은 방출 카드마다 정확히 1회"
    assert [c["joint"] for c in seen] == [it["joint"] for it in items]
    for ctx, it in zip(seen, items):
        assert ctx["criterion"] == it.get("criterion")
        for side in ("user", "ref"):
            xy = ctx[side]["xy"]
            assert xy is not None, f"{side} 크롭 중심이 없으면 검사할 표시가 없다"
            assert 0.0 <= float(xy[0]) <= 1.0 and 0.0 <= float(xy[1]) <= 1.0
            assert isinstance(ctx[side]["kind"], str)
            assert ctx[side]["frame"].ndim == 3, "그 측이 실제로 자른 프레임"


def test_anchor_check_center_matches_side_crop_center(monkeypatch):
    """콜백이 받는 중심 = `_side_crop` 이 그 카드에 넘긴 중심(또는 anchor 폴백).

    좌표가 갈리면 게이트는 카드가 보여주지 않는 자리를 검사하게 된다 — 09-06 이전
    감사와 게이트가 어긋난 그 자리다.
    """
    centers: list[tuple] = []
    orig = fz._side_crop

    def _spy(frame, pts, relaxed, *, anchor=None, center=None, **kw):
        centers.append(center if center is not None else anchor)
        return orig(frame, pts, relaxed, anchor=anchor, center=center, **kw)

    monkeypatch.setattr(fz, "_side_crop", _spy)
    seen: list[dict] = []
    items = _build(anchor_check=lambda ctx: (seen.append(ctx), frozenset())[1])
    assert items and len(seen) == len(items)
    # _side_crop 은 카드마다 학생·기준 순서로 2회 불린다.
    assert len(centers) == 2 * len(items)
    for i, ctx in enumerate(seen):
        assert ctx["user"]["xy"] == centers[2 * i]
        assert ctx["ref"]["xy"] == centers[2 * i + 1]


# ── ② 반환한 측만 무표시 — 카드는 그대로 나간다 ─────────────────────────────


def test_anchor_check_suppresses_only_returned_side(caplog):
    base = _build()
    with caplog.at_level(logging.INFO, logger=fz.__name__):
        items = _build(anchor_check=lambda ctx: frozenset({"user"}))
    assert len(items) == len(base), "검사는 표시만 정한다 — 장수 불변"
    # quick-260919-o8v (belle 2026-09-18): 억제는 원만 지운다 — 이 픽스처는 각도가
    # 그려지는 카드라 플래그가 산다.
    for it, b in zip(items, base):
        assert it["userMarked"] is True
        assert _brand_px_left_panel(it["png"]) > 0, "각도 픽셀이 남아 있다"
        assert it["refMarked"] == b["refMarked"], "반대측은 무접촉"
    # "반환한 측만"의 증인 = 억제 로그. 플래그가 더 이상 그 성질을 못 말한다.
    sides = _suppressed_sides_by_criterion(caplog)
    assert sides, "억제가 아예 안 걸렸으면 이 시험은 아무것도 안 잰다"
    assert set(sides.values()) == {"user"}, "반환하지 않은 ref 는 억제 대상이 아니다"


def test_anchor_check_can_suppress_per_card(caplog):
    """카드마다 다른 판정 — 호출 전체 인자(suppress_marks)로는 못 하던 것."""
    def _cb(ctx):
        return frozenset({"ref"}) if ctx["joint"] == "right_knee" else frozenset()

    with caplog.at_level(logging.INFO, logger=fz.__name__):
        items = _build(anchor_check=_cb)
    by_joint = {it["joint"]: it for it in items}
    # quick-260919-o8v (belle 2026-09-18): 억제는 원만 지운다 — 이 픽스처는 각도가
    # 그려지는 카드라 플래그가 산다(양쪽 다 True). 그래서 **카드별 판정**의 증인을
    # 플래그에서 억제 로그로 옮긴다: right_knee 만 로그에 오르고 left_shoulder 는
    # 아예 안 오른다.
    assert by_joint["right_knee"]["refMarked"] is True
    assert by_joint["left_shoulder"]["refMarked"] is True
    sides = _suppressed_sides_by_criterion(caplog)
    assert sides == {"angle_vs_reference__right_knee": "ref"}, (
        "카드별 판정이 안 걸렸다 — 콜백 반환이 카드 경계를 넘었거나 안 불렸다"
    )


# ── ③ 예외 = fail-open ──────────────────────────────────────────────────────


def test_anchor_check_exception_keeps_card_and_marks():
    def _boom(ctx):
        raise RuntimeError("눈이 죽었다")

    base = _build()
    items = _build(anchor_check=_boom)
    assert len(items) == len(base)
    for it, b in zip(items, base):
        assert it["userMarked"] == b["userMarked"]
        assert it["refMarked"] == b["refMarked"]


# ── ④ 미전달 = 종전 동작 불변 ───────────────────────────────────────────────


def test_no_anchor_check_is_byte_identical():
    a = _build()
    b = _build(anchor_check=None)
    assert [x["png"] for x in a] == [x["png"] for x in b]


# ── ⑤ 기존 suppress_marks 와 합집합 ─────────────────────────────────────────


def test_anchor_check_unions_with_suppress_marks(caplog):
    with caplog.at_level(logging.INFO, logger=fz.__name__):
        items = _build(
            suppress_marks=frozenset({"ref"}),
            anchor_check=lambda ctx: frozenset({"user"}),
        )
    assert items
    # quick-260919-o8v (belle 2026-09-18): 억제는 원만 지운다 — 이 픽스처는 각도가
    # 그려지는 카드라 플래그가 산다(양측 억제여도 True). **합집합**의 증인은 억제
    # 로그의 sides 다: 인자(ref) ∪ 콜백(user) = 두 측 모두.
    for it in items:
        assert it["userMarked"] is True
        assert it["refMarked"] is True
    sides = _suppressed_sides_by_criterion(caplog)
    assert len(sides) == len(items), "카드마다 억제가 걸려야 한다"
    assert set(sides.values()) == {"user,ref"}, (
        "두 출처가 서로를 지웠다 — 합집합이 아니라 덮어쓰기가 됐다"
    )
