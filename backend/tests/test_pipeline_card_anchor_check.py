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


def _stub_eye(monkeypatch, tokens, mark_tokens=None):
    """눈 스텁 — 1단(part)은 tokens, 2단(mark_part)은 mark_tokens 를 순서대로.

    mark_tokens 를 안 주면 2단도 tokens 를 이어 쓴다(1단과 같은 판독 = 확정 불일치).
    반환 = (1단 호출 목록, 2단 호출 목록) — 2단이 돌았는지까지 잠근다.
    """
    seen: list[str] = []
    seen_mark: list[str] = []

    def _fake(crop, *, api_key, model=None, rounds=None, timeout_s=None,
              claim="part"):
        if claim == "mark_part":
            src = mark_tokens if mark_tokens is not None else tokens
            tok = src[len(seen_mark)] if len(seen_mark) < len(src) else src[-1]
            seen_mark.append(tok)
        else:
            tok = tokens[len(seen)] if len(seen) < len(tokens) else tokens[-1]
            seen.append(tok)
        return {"observed": tok, "tokens": [tok], "calls": 1, "reason": ""}

    monkeypatch.setattr(cg, "eye_part_token", _fake)
    return seen, seen_mark


# ── ① 불일치 측만 표시 생략 ─────────────────────────────────────────────────


def test_mismatch_side_is_suppressed(monkeypatch):
    app = _import_pipeline()
    seen, _ = _stub_eye(monkeypatch, ["hand", "knee"])   # user 틀림, ref 맞음
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    assert cb(_ctx()) == frozenset({"user"})
    assert st["suppressed"] == 1 and st["pass"] == 1 and st["sides"] == 2
    assert seen == ["hand", "knee"]


def test_both_sides_can_pass(monkeypatch):
    app = _import_pipeline()
    _, seen_mark = _stub_eye(monkeypatch, ["knee", "thigh"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    assert cb(_ctx()) == frozenset()
    assert st["pass"] == 2 and st["suppressed"] == 0
    assert seen_mark == [], "1단 통과면 2단을 묻지 않는다"


# ── ② 재확인 없음 — 측당 1회 ────────────────────────────────────────────────


def test_no_retry_one_eye_call_per_side(monkeypatch):
    app = _import_pipeline()
    seen, seen_mark = _stub_eye(monkeypatch, ["hand", "hand"])   # 양측 다 불일치
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    assert cb(_ctx()) == frozenset({"user", "ref"})
    assert len(seen) == 2, "재확인 프레임을 주지 않으므로 1단은 측당 정확히 1회"
    assert st["moved"] == 0
    # 2단은 지우기 직전에만 — 1단이 둘 다 mismatch 라 두 측 모두 2단이 돈다.
    assert len(seen_mark) == 2
    assert st["eye_calls"] == 4 and st["mark_calls"] == 2


# ── ③ 호출 0 (감사 불가는 불일치가 아니다) ──────────────────────────────────


def test_full_fallback_side_is_unbound(monkeypatch):
    app = _import_pipeline()
    seen, _ = _stub_eye(monkeypatch, ["knee"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    # 전신 폴백 측은 애초에 표시가 없다 — 검사할 것이 없다.
    assert cb(_ctx(user_kind="full")) == frozenset()
    assert seen == ["knee"], "ref 만 물었어야 한다"
    assert st["unbound"] == 1


def test_missing_center_is_unbound(monkeypatch):
    app = _import_pipeline()
    seen, _ = _stub_eye(monkeypatch, ["knee"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="stage1", stats=st)
    assert cb(_ctx(user_xy=None)) == frozenset()
    assert len(seen) == 1 and st["unbound"] == 1


def test_underivable_expectation_is_unbound(monkeypatch):
    app = _import_pipeline()
    seen, _ = _stub_eye(monkeypatch, ["hand"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    assert cb(_ctx(criterion=None, joint="")) == frozenset()
    assert seen == [], "기대 부위를 못 만들면 눈을 부르지 않는다"
    assert st["unbound"] == 2


def test_no_api_key_keeps_marks(monkeypatch):
    app = _import_pipeline()
    seen, _ = _stub_eye(monkeypatch, ["hand", "hand"])
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


# ── ⑤ 2단 판정 (quick-260918-gpx) ───────────────────────────────────────────
#
# 1단(part, 무표시 정중앙)이 mismatch 라고 해도 그것만으로 지우지 않는다. 설계가
# 이미 그렇게 적혀 있었는데(card_photo_audit.adjudicate: "crop 정중앙이 이웃 부위로
# 읽히는 것은 정상이고, 카드가 실제로 가리키는 지점은 표시다") 운영에만 빠져 있었다.
# 1단 질문이 "정중앙에 **가장 크게** 보이는 부위"라 역립 자세의 어깨 크롭에 머리가
# 더 크게 들어오면 눈은 질문대로 head 라고 정확히 답하고, 그걸 좌표 오류로 읽으면
# 맞는 표식이 지워진다.


def test_stage2_rescues_when_mark_is_in_expected(monkeypatch):
    """1단이 이웃 부위를 읽어도 표시가 허용 안이면 지우지 않는다 (mark_in_expected)."""
    app = _import_pipeline()
    seen, seen_mark = _stub_eye(
        monkeypatch, ["head", "head"], mark_tokens=["knee", "knee"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    assert cb(_ctx()) == frozenset(), "표시가 무릎 위면 두 측 모두 살아야 한다"
    assert len(seen) == 2 and len(seen_mark) == 2
    assert st["suppressed"] == 0, "구제되면 집계도 되돌린다"
    assert st["stage2_rescued"] == 2


def test_stage2_confirms_when_mark_is_elsewhere(monkeypatch):
    """표시까지 허용 밖이면 지운다 (mark_elsewhere) — 사진이 정말 다른 부위를 가리킨다."""
    app = _import_pipeline()
    _, seen_mark = _stub_eye(
        monkeypatch, ["head", "head"], mark_tokens=["hand", "hand"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    assert cb(_ctx()) == frozenset({"user", "ref"})
    assert len(seen_mark) == 2
    assert st["suppressed"] == 2 and st["stage2_confirmed"] == 2
    assert st.get("stage2_rescued", 0) == 0


def test_stage2_unreadable_keeps_the_mark(monkeypatch):
    """눈이 표시를 못 읽으면 지우지 않는다 — 감사 불가는 불일치가 아니다.

    anchor_verdict 의 unreadable 규칙과 동형("눈이 못 본 것은 틀린 게 아니다").
    """
    app = _import_pipeline()
    _stub_eye(monkeypatch, ["head", "head"], mark_tokens=["unclear", "unclear"])
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    assert cb(_ctx()) == frozenset()
    assert st["suppressed"] == 0 and st["stage2_rescued"] == 2


def test_stage2_unavailable_honours_stage1(monkeypatch):
    """2단을 **아예 못 돌리면** 1단 판정(지움)을 그대로 따른다.

    눈이 못 읽음(2단이 돈 결과 → 구제)과 2단 자체가 불가(증거 0 → 1단 유지)는 다르다.
    둘을 섞으면 인프라 장애가 조용히 표시를 되살린다.
    """
    app = _import_pipeline()
    calls: list[str] = []

    def _fake(crop, *, api_key, model=None, rounds=None, timeout_s=None,
              claim="part"):
        if claim == "mark_part":
            raise RuntimeError("mark crop 실패")
        calls.append("part")
        return {"observed": "head", "tokens": ["head"], "calls": 1, "reason": ""}

    monkeypatch.setattr(cg, "eye_part_token", _fake)
    st = _stats()
    cb = app._make_card_anchor_check(
        api_key="k", analysis_id="a", path="advisory", stats=st)
    assert cb(_ctx()) == frozenset({"user", "ref"}), "2단 불가 → 1단 유지(지움)"
    assert st["suppressed"] == 2 and st["stage2_unavailable"] == 2
    assert st.get("stage2_rescued", 0) == 0
