"""quick-260919-o8v — 표시 억제는 **원 마커만** 지운다. 각도·사이각은 남긴다.

belle 2026-09-18 판정 3줄:
  1. 사진은 9/03 규칙대로 전부 내보낸다 — 어떤 게이트도 사진을 없앨 권한이 없다.
     (9/06 의 "게이트 확인분만 내보낸다"= 사진 삭제는 기각)
  2. 게이트가 부위를 확인 못 해 표시가 생략된 자리에는 **각도 표시를 놓는다**.
     9/06 원문 "사진 **대신** 각도"의 "대신"을 "**함께**"로 개정한 것이다.
  3. "확인 안 됨" 류 문구·배지·아이콘은 쓰지 않는다 — 우리 불확실성을 수강생에게
     방송해 신뢰를 깎는다. (그래서 이 단위는 UI 카피를 한 줄도 만들지 않는다)

**과제가 좁혀진 이유 (코드 실측):** `fault_zoom.py` 의 드로잉 분기에서 각도와
원(·화살표)은 이미 **배타적**이다 — `if u_drew_legs or u_drew_angle: _mark(circle=False)`.
각도를 그린 패널에는 지울 원이 애초에 없다. 그래서 belle 규칙 2 의 실행 가능한
형태는 "억제할 때 각도까지 지우지 마라" 하나뿐이고, 되돌릴 대상은 0 이다.
종전 구현은 드로잉 **이전** 스냅샷(`_u_plain`/`_r_plain`)으로 되돌려 각도까지 함께
지웠다 — 그것이 false-suppress(맞는 표식을 지움)다.

**범위 밖 (섞지 말 것):** 좌표 저신뢰(conf<0.5 → `angle_reason=user_crop_relaxed` 등)나
`ANGLE_BAKE_MAP` 미선언(`unmapped`)으로 각도가 **애초에 안 그려진** 카드는 종전대로
원만 그렸다가 억제되면 무표시가 된다. 없던 각도를 지어내면 "재지 않은 것을 쟀다"고
말하는 셈이다. 아래 ⑤·⑥ 이 그 경계를 잠근다.

여기서 잠그는 것:
  ① `anchor_check` 가 학생 측을 억제해도 각도 카드는 `userMarked True` + 학생 패널
     브랜드색 픽셀 > 0 — 플래그와 그림이 함께 산다.
  ② 기준 측 대칭 — `refMarked True` + 기준 패널 픽셀 > 0.
  ③ 양측 억제도 양쪽 다 살아남고 `png != pngPlain` (표시 판과 무표시 판이 갈린다).
  ④ 장수 불변 (belle 규칙 1 — 게이트는 사진을 못 없앤다).
  ⑤ **회귀 가드**: 각도가 성립하지 않는(원만 그리던) 카드는 종전 그대로 무표시 + False.
  ⑥ advisory 카드(criterion 없음 → 각도 경로 미진입)도 종전 그대로.
  ⑦ `suppress_marks` 인자 입구도 `anchor_check` 와 같은 규칙을 탄다.
  ⑧ `pngPlain` 무접촉 — 억제 여부와 무관하게 양 패널 표시 픽셀 0.

계약: `docs/contract.md` §11.9 (refMarked) / §11.11 (userMarked).

fixture 는 tests/test_fault_zoom_anchor_check.py(_KP/_Match/_identity/_report/_frames/
_unit/_UNITS/_build) 와 tests/test_fault_zoom_advisory_user_marked.py(_build_advisory),
tests/test_fault_zoom.py(_brand_px_left_panel) 를 복제 — 테스트 모듈 간 import 금지 관행.
각도 픽셀이 증거가 되는 근거: `_draw_joint_angle` 은 선을 `_BRAND` 로 긋는다(원 마커와
같은 색) — 기존 헬퍼가 그대로 각도의 증거다.

전부 합성 keypoint report + 프로덕션 함수 직접 호출 — GPU/S3/네트워크/눈 0.
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
    """합성 PNG 왼쪽(학생) 패널의 브랜드색 픽셀 수 — 표시가 그려졌는지의 픽셀 증거."""
    arr = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))[:, : fz._OUT, :]
    return int(np.all(arr == np.asarray(fz._BRAND, dtype=np.uint8), axis=-1).sum())


def _brand_px_right_panel(png: bytes) -> int:
    """오른쪽(기준) 패널 미러. `_compose` 의 `gap` 은 함수 지역 리터럴이라 상수로
    못 읽는다 — 그래서 앞에서 오프셋을 더하지 않고 **마지막 `_OUT` 열**을 자른다."""
    arr = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))[:, -fz._OUT:, :]
    return int(np.all(arr == np.asarray(fz._BRAND, dtype=np.uint8), axis=-1).sum())


def _unit(criterion, joints, region=None):
    return {"criterion": criterion, "joints": tuple(joints),
            "region": region, "at_frame_idx": None}


# 이 두 카드는 `ANGLE_BAKE_MAP` 선언 접미사(shoulder/knee)이고 conf 0.9 라
# `angle_bake=drawn` 이다 (2026-09-19 로그 실측) — 즉 각도 경로를 타는 카드다.
_UNITS = [
    _unit("angle_vs_reference__left_shoulder", ["left_shoulder"]),
    _unit("angle_vs_reference__right_knee", ["right_knee"]),
]

# 대조군: 접미사 `hand` 는 `ANGLE_BAKE_MAP` 미선언 → `angle_bake=omitted:unmapped`.
# 각도를 **잴 수 없어서** 원만 그린 카드라, 억제되면 종전대로 전부 사라져야 한다.
_CIRCLE_ONLY_UNITS = [_unit("angle_vs_reference__left_hand", ["left_hand"])]


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


_ADVISORY_JOINTS = ["left_shoulder", "right_knee"]


def _build_advisory(**kw):
    """pipeline/app.py advisory 배치 미러 — criterion_units 를 넘기지 않는다."""
    return fz.build_fault_zoom_comparisons(
        _frames(), _frames(),
        _report(), _report(),
        worst_seconds=1.0,
        fault_joints=list(_ADVISORY_JOINTS),
        joint_deltas={j: 20.0 for j in _ADVISORY_JOINTS},
        frames_fps=_FPS,
        joint_kinds={j: "deficit" for j in _ADVISORY_JOINTS},
        dtw_match=_identity(),
        user_frame_candidates=[8, 9, 10, 11, 12],
        ref_frame_candidates=[8, 9, 10, 11, 12],
        draw_arrows=False,
        split_angle_present=False,
        analysis_id="t",
        **kw,
    )


# ── ① 학생 측 억제 — 각도는 남고 인증도 남는다 ────────────────────────────────


def test_user_suppression_keeps_angle_and_user_marked():
    """기계 눈이 학생 패널을 억제해도 각도 카드는 그림·플래그가 함께 산다.

    플래그가 그림과 어긋나면 앱은 사진에 각도가 있는데도 "왼쪽 사진에는 표시를
    넣지 않았어요"라고 없는 사실을 말하게 된다 (DeductionDetailSheet USER_UNMARKED_NOTE).
    """
    items = _build(anchor_check=lambda ctx: frozenset({"user"}))
    assert items, "카드가 안 나오면 이 게이트는 성립하지 않는다"
    for it in items:
        assert it["userMarked"] is True, "각도를 그린 패널은 억제돼도 인증이 산다"
        assert _brand_px_left_panel(it["png"]) > 0, "학생 패널에 각도 픽셀이 남아 있다"


# ── ② 기준 측 대칭 ────────────────────────────────────────────────────────────


def test_ref_suppression_keeps_angle_and_ref_marked():
    items = _build(anchor_check=lambda ctx: frozenset({"ref"}))
    assert items
    for it in items:
        assert it["refMarked"] is True
        assert _brand_px_right_panel(it["png"]) > 0, "기준 패널에 각도 픽셀이 남아 있다"


# ── ③ 양측 억제 — 각도 both-or-neither 가 억제로 깨지지 않는다 ────────────────


def test_both_sides_suppressed_keep_angles_on_both_panels():
    """각도 베이크는 `_u_ok and _r_ok` 양측 대칭이 불변식이다. 종전 억제는 한쪽만
    걸리면 그 쪽만 지워 **한 패널만 각도**인 비대칭을 만들었다 — 구조적으로 막는다."""
    items = _build(anchor_check=lambda ctx: frozenset({"user", "ref"}))
    assert items
    for it in items:
        assert it["userMarked"] is True and it["refMarked"] is True
        assert _brand_px_left_panel(it["png"]) > 0
        assert _brand_px_right_panel(it["png"]) > 0
        assert it["png"] != it["pngPlain"], "표시 판과 무표시 판이 갈려야 한다"


# ── ④ 장수 불변 (belle 규칙 1) ────────────────────────────────────────────────


def test_card_count_unchanged_by_suppression():
    base = _build()
    for supp in ({"user"}, {"ref"}, {"user", "ref"}):
        items = _build(anchor_check=lambda ctx, s=frozenset(supp): s)
        assert len(items) == len(base), "게이트는 사진을 없앨 권한이 없다"
        assert [it["joint"] for it in items] == [b["joint"] for b in base]


# ── ⑤ 회귀 가드: 원만 그리던 카드는 종전 그대로 사라진다 ──────────────────────


def test_circle_only_card_is_still_fully_suppressed():
    """`hand` 는 `ANGLE_BAKE_MAP` 미선언 = 각도를 **잴 수 없어** 원만 그린 카드다.
    억제 사유 두 가지(기계 눈 / 각도 미성립)를 섞는 구현을 이 시험이 즉시 깨뜨린다."""
    base = _build(units=_CIRCLE_ONLY_UNITS)
    assert base and base[0]["userMarked"] is True, "평시엔 원 마커로 True"
    items = _build(
        units=_CIRCLE_ONLY_UNITS, anchor_check=lambda ctx: frozenset({"user"})
    )
    assert len(items) == len(base)
    for it in items:
        assert it["userMarked"] is False, "지울 원이 있었으므로 종전대로 내려간다"
        assert _brand_px_left_panel(it["png"]) == 0


# ── ⑥ advisory 무변경 (criterion 없음 → 각도 경로 미진입) ─────────────────────


def test_advisory_suppression_is_unchanged():
    items = _build_advisory(anchor_check=lambda ctx: frozenset({"user"}))
    assert items
    for it in items:
        assert "criterion" not in it, "advisory 형상 — criterion 이 없어야 한다"
        assert it["userMarked"] is False
        assert _brand_px_left_panel(it["png"]) == 0


# ── ⑦ suppress_marks 인자 입구도 같은 규칙 ────────────────────────────────────


def test_suppress_marks_argument_follows_the_same_rule():
    """두 입구(`suppress_marks` 인자 / `anchor_check` 콜백)가 같은 `_supp` 로 합쳐져
    같은 규칙을 탄다 — 한쪽만 고치면 라이브에서 경로에 따라 결과가 갈린다."""
    items = _build(suppress_marks=frozenset({"user"}))
    assert items
    for it in items:
        assert it["userMarked"] is True
        assert _brand_px_left_panel(it["png"]) > 0


# ── ⑧ pngPlain 무접촉 ─────────────────────────────────────────────────────────


def test_png_plain_has_no_marks_regardless_of_suppression():
    """belle 09-09 '관절선 끄기' 판은 별개 산출물이다 — 이 단위가 건드리지 않는다."""
    for kw in ({}, {"anchor_check": lambda ctx: frozenset({"user", "ref"})}):
        items = _build(**kw)
        assert items
        for it in items:
            assert _brand_px_left_panel(it["pngPlain"]) == 0
            assert _brand_px_right_panel(it["pngPlain"]) == 0
