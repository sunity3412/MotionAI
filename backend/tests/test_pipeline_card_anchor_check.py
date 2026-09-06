"""quick-260906-n2j — stage-1·advisory 카드 앵커 부위 확인 콜백 (파이프라인 배선).

순수 층(card_gates.verify_anchor_side / card_photo_audit.anchor_verdict)은 이미
잠겨 있다(test_anchor_part_check.py). 여기서 잠그는 것은 **배선**이다:

  ① 눈이 기대 밖 부위를 읽으면 그 측만 표시 생략 집합에 들어간다.
  ② 재확인 프레임을 쓰지 않는다 — 측당 눈 호출 1회 (09-06 라이브 moved=0/15).
  ③ 호출 0 이어야 하는 경우: 크롭 중심 없음 / 전신 폴백(kind='full') / 기대 부위
     파생 불가 / API 키 부재. 감사 불가는 불일치가 아니다 → 표시 유지.
  ④ 집계는 두 경로(stage1/advisory)가 같은 dict 에 합산한다.

눈은 스텁 — 네트워크 0.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

from sunity_shared.analysis import card_gates as cg  # noqa: E402


def _import_pipeline():
    sys.modules.pop("app", None)
    import app  # noqa: WPS433
    return importlib.reload(app)


_FRAME = np.full((64, 48, 3), 120, dtype=np.uint8)


def _stats():
    return {"sides": 0, "eye_calls": 0, "pass": 0, "moved": 0,
            "suppressed": 0, "unbound": 0}


def _ctx(criterion="angle_vs_reference__left_knee", joint="left_knee",
         *, user_kind="valid", ref_kind="valid", user_xy=(0.5, 0.5),
         ref_xy=(0.5, 0.5)):
    return {
        "joint": joint, "criterion": criterion,
        "user": {"frame": _FRAME, "kind": user_kind, "xy": user_xy},
        "ref": {"frame": _FRAME, "kind": ref_kind, "xy": ref_xy},
    }


def _stub_eye(monkeypatch, tokens):
    """side 순서(user, ref)대로 토큰을 돌려주는 눈 스텁. 호출 목록을 반환."""
    seen: list[str] = []

    def _fake(crop, *, api_key, model=None, rounds=None, timeout_s=None):
        tok = tokens[len(seen)] if len(seen) < len(tokens) else tokens[-1]
        seen.append(tok)
        return {"observed": tok, "tokens": [tok], "calls": 1, "reason": ""}

    monkeypatch.setattr(cg, "eye_part_token", _fake)
    return seen


# ── ① 불일치 측만 표시 생략 ─────────────────────────────────────────────────


def test_mismatch_side_is_suppressed(monkeypatch):
    app = _import_pipeline()
    seen = _stub_eye(monkeypatch, ["hand", "knee"])   # user 틀림, ref 맞음
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    assert cb(_ctx()) == frozenset({"user"})
    assert st["suppressed"] == 1 and st["pass"] == 1 and st["sides"] == 2
    assert seen == ["hand", "knee"]


def test_both_sides_can_pass(monkeypatch):
    app = _import_pipeline()
    _stub_eye(monkeypatch, ["knee", "thigh"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    assert cb(_ctx()) == frozenset()
    assert st["pass"] == 2 and st["suppressed"] == 0


# ── ② 재확인 없음 — 측당 1회 ────────────────────────────────────────────────


def test_no_retry_one_eye_call_per_side(monkeypatch):
    app = _import_pipeline()
    seen = _stub_eye(monkeypatch, ["hand", "hand"])   # 양측 다 불일치
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    assert cb(_ctx()) == frozenset({"user", "ref"})
    assert len(seen) == 2, "재확인 프레임을 주지 않으므로 측당 정확히 1회"
    assert st["eye_calls"] == 2 and st["moved"] == 0


# ── ③ 호출 0 (감사 불가는 불일치가 아니다) ──────────────────────────────────


def test_full_fallback_side_is_unbound(monkeypatch):
    app = _import_pipeline()
    seen = _stub_eye(monkeypatch, ["knee"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    # 전신 폴백 측은 애초에 표시가 없다 — 검사할 것이 없다.
    assert cb(_ctx(user_kind="full")) == frozenset()
    assert seen == ["knee"], "ref 만 물었어야 한다"
    assert st["unbound"] == 1


def test_missing_center_is_unbound(monkeypatch):
    app = _import_pipeline()
    seen = _stub_eye(monkeypatch, ["knee"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    assert cb(_ctx(user_xy=None)) == frozenset()
    assert len(seen) == 1 and st["unbound"] == 1


def test_underivable_expectation_is_unbound(monkeypatch):
    app = _import_pipeline()
    seen = _stub_eye(monkeypatch, ["hand"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    assert cb(_ctx(criterion=None, joint="")) == frozenset()
    assert seen == [], "기대 부위를 못 만들면 눈을 부르지 않는다"
    assert st["unbound"] == 2


def test_no_api_key_keeps_marks(monkeypatch):
    app = _import_pipeline()
    seen = _stub_eye(monkeypatch, ["hand", "hand"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="", analysis_id="a", path="stage1", stats=st)
    assert cb(_ctx()) == frozenset(), "키가 없다고 표시를 지우지 않는다"
    assert seen == [] and st["unbound"] == 2


# ── ④ 두 경로가 같은 집계에 합산 ────────────────────────────────────────────


def test_stats_accumulate_across_paths(monkeypatch):
    app = _import_pipeline()
    _stub_eye(monkeypatch, ["knee", "knee", "knee", "knee"])
    st = _stats()
    s1 = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    adv = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    s1(_ctx())
    adv(_ctx())
    assert st["sides"] == 4 and st["pass"] == 4 and st["eye_calls"] == 4
