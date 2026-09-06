"""quick-260906-vho — advisory/legacy 카드도 userMarked 를 방출한다 (refMarked 는 그대로 부재).

09-06 n2j 라이브(uid NdVZrpbmUbPMNMjASFwUgy8Fj9p1, 6동작): 앵커 게이트가 advisory 학생
표시를 실제로 지웠는데(pdshape·peterpan advisory 억제 3면) 방출부가 `if unit.criterion is
not None:` 안에서만 `userMarked` 를 실어 doc 에는 키가 없었다. 감사(scripts/
audit_card_photos.py marked_flags)는 키 부재를 "학생 측 표시 있음"으로 추정해 1단 탈락 패널에
2단(mark_part) 질의를 내고 눈이 no_mark 를 답해 판정 불가(mark_disagreement)가 됐다 —
라이브 실물 `ref-peter-pan [1] advisory right_elbow user=back_waist→no_mark None/mark:
mark_disagreement`.

여기서 잠그는 것:
  ① advisory 카드(criterion_units 미전달)도 `userMarked` 를 방출한다.
  ② 값은 그리는 코드가 인증한다 — 앵커 게이트가 학생 측을 억제하면 False 이고 왼쪽 패널
     브랜드색 픽셀도 0 이다. 반대측(ref)만 억제되면 학생은 True 그대로.
  ③ `refMarked` 는 contract §11.9 정책대로 키 부재 — 기준 측은 게이트 B(quick-260705-wbs)로
     legacy/advisory 무마킹이 정책이라 false 를 실으면 앱이 없는 이유를 말한다.

fixture 는 tests/test_fault_zoom_anchor_check.py(_KP/_Match/_identity/_report/_frames) 와
tests/test_fault_zoom.py(_brand_px_left_panel) 를 복제 — 테스트 모듈 간 import 금지 관행.
`_build_advisory` 는 pipeline/app.py advisory 배치 호출 형상(joint_kinds deficit,
draw_arrows False, split_angle_present False, criterion_units 없음)을 미러한다.
GPU/S3/네트워크/눈 0.
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


# ── ① 평시: advisory 카드도 userMarked True, refMarked 는 부재 ────────────────────


def test_advisory_cards_emit_user_marked_true_when_drawn():
    items = _build_advisory()
    assert items, "advisory 카드가 안 나오면 이 게이트는 성립하지 않는다"
    for it in items:
        assert "criterion" not in it, "advisory 형상 — criterion 이 없어야 한다"
        assert it["userMarked"] is True
        assert "refMarked" not in it, "기준 측은 §11.9 정책대로 키 부재"
        assert _brand_px_left_panel(it["png"]) > 0, "학생 패널에 표시가 실제로 그려졌다"


# ── ② 앵커 게이트가 학생 측을 억제하면 False 이고 픽셀도 0 ────────────────────────


def test_advisory_cards_emit_user_marked_false_when_user_suppressed():
    items = _build_advisory(anchor_check=lambda ctx: frozenset({"user"}))
    assert items
    for it in items:
        assert it["userMarked"] is False
        assert "refMarked" not in it
        assert _brand_px_left_panel(it["png"]) == 0, "플래그가 그림과 일치 — 학생 표시 픽셀 0"


# ── ③ 반대측(ref)만 억제 — 학생 측은 무접촉 True ──────────────────────────────────


def test_advisory_cards_keep_user_marked_true_when_only_ref_suppressed():
    items = _build_advisory(anchor_check=lambda ctx: frozenset({"ref"}))
    assert items
    for it in items:
        assert it["userMarked"] is True
        assert "refMarked" not in it
