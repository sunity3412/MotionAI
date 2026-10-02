"""평가셋 분리 점검(backend/scripts/eval_split_check.py) 순수 부분 — 37-DATA-SPEC 규칙 6 + TRAINING-DUE 게이트 4.
단언: (1) 안 닫힌 시험(sealed/run/graded) 영상 → 짝 → 같은 인물·세션 클립까지 평가
(2) 닫힌 시험 영상과 practice 는 연습 영상 — 평가 아님, 학습 후보 (belle 09-26 "시험 영상은 배우지 않는다, 나머지는 전부 배운다")
(3) L1/L2/L3 분류 (4) 인물 1명이면 보고서가 '인물 분리 불가'를 적는다
(5) 평가셋 0편이면 '평가셋 없음' + verdict 2 — 통과로 안 읽힌다 (6) holdout 행은 학습 후보가 아니다."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("eval_split_check", Path(__file__).resolve().parents[1] / "scripts" / "eval_split_check.py")
esc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(esc)

H = lambda c: c * 64  # noqa: E731
NO_LEAKS = {"L1_same_file": [], "L2_same_session": [], "L3_same_subject": []}
ELIGIBLE = lambda r: not r.get("holdout") and bool(r.get("s3_key"))  # noqa: E731 — gemini_teacher.eligible_for_distill 과 같은 규칙


def _clips():
    return [
        {"video_hash": H("a"), "subject_id": "sub_je", "capture": {"session": "2026-06-17"}, "s3_key": "fixtures/phase15/ps/correct.mp4"},
        {"video_hash": H("b"), "subject_id": "sub_je", "capture": {"session": "2026-06-17"}, "s3_key": "fixtures/phase15/ps/fault.mp4"},
        {"video_hash": H("c"), "subject_id": "sub_je", "capture": {"session": "2026-06-17"}, "s3_key": "fixtures/phase15/climb/fault.mp4"},
        {"video_hash": H("d"), "subject_id": "sub_s01", "capture": {"session": "2026-10-05"}, "s3_key": "fixtures/intake/d.mov"},
        {"video_hash": H("e"), "subject_id": "sub_je", "capture": {"session": "2026-10-05"}, "s3_key": "fixtures/intake/e.mov"},
    ]


def _pairs():
    return [{"correct_hash": H("a"), "fault_hash": H("b")}]


def _test(status, rows, practice=(), test_id="t"):
    """sealed_tests.jsonl 한 줄 — status 수명 sealed → run → graded → closed (sealed_test.py)."""
    return {"test_id": test_id, "status": status,
            "rows": [{"video_hash": h} for h in rows], "practice": [{"video_hash": h} for h in practice]}


@pytest.mark.parametrize("status", ["sealed", "run", "graded"])
def test_open_test_expands_by_pair_and_session(status):
    ev = esc.eval_groups(_clips(), _pairs(), [_test(status, [H("d"), H("b")])])
    assert ev["hashes"] == {H("d"), H("b"), H("a")}                # 시험 영상 d·b + b 의 짝 a
    assert ev["groups"] == {("sub_s01", "2026-10-05"), ("sub_je", "2026-06-17")}
    assert {c["video_hash"] for c in ev["clips"]} == {H("a"), H("b"), H("c"), H("d")}  # c 는 같은 세션이라 평가
    assert ev["subjects"] == {"sub_je", "sub_s01"}


def test_closed_test_is_practice_not_eval():
    ev = esc.eval_groups(_clips(), _pairs(), [_test("closed", [H("b")], test_id="t-closed")])
    assert ev["hashes"] == set() and ev["groups"] == set() and ev["subjects"] == set()
    assert ev["clips"] == []
    assert ev["closed"] == ["t-closed"]
    assert esc.verdict_code(ev, NO_LEAKS) == 2


def test_practice_and_closed_rows_are_learnable():
    sealed = [_test("closed", [H("b")], test_id="t-closed"), _test("sealed", [H("d")], practice=[H("e")])]
    ev = esc.eval_groups(_clips(), _pairs(), sealed)
    assert ev["hashes"] == {H("d")}                               # b(닫힘)·e(practice) 아님, b 가 평가가 아니니 짝 a 도 아님
    assert ev["groups"] == {("sub_s01", "2026-10-05")}
    manifest = [
        {"s3_key": "fixtures/phase15/ps/fault.mp4", "holdout": None},    # b 닫힌 시험 영상
        {"s3_key": "fixtures/intake/e.mov", "holdout": None},            # e practice
        {"s3_key": "fixtures/phase15/ps/correct.mp4", "holdout": None},  # a b 의 짝
    ]
    leaks = esc.find_leaks(manifest, _clips(), ev, eligible=ELIGIBLE)
    assert leaks == NO_LEAKS


def test_leak_levels():
    ev = esc.eval_groups(_clips(), _pairs(), [_test("sealed", [H("d"), H("b")])])
    manifest = [
        {"s3_key": "fixtures/phase15/ps/fault.mp4", "holdout": None},        # L1 평가 영상 자체
        {"s3_key": "fixtures/phase15/climb/fault.mp4", "holdout": None},     # L1 (같은 세션 클립도 평가 클립)
        {"s3_key": "fixtures/intake/e.mov", "holdout": None},                # L3 같은 인물 다른 세션
        {"s3_key": "reference/ref-kip-up.mp4", "holdout": None},             # L3 reference = sub_je
        {"s3_key": "fixtures/phase15/ps/correct.mp4", "holdout": "sealed_eval"},  # holdout 은 후보 아님
        {"s3_key": "youtube/x.mp4", "holdout": None},                        # 무관
    ]
    leaks = esc.find_leaks(manifest, _clips(), ev, eligible=ELIGIBLE)
    assert leaks["L1_same_file"] == ["fixtures/phase15/ps/fault.mp4", "fixtures/phase15/climb/fault.mp4"]
    assert leaks["L2_same_session"] == []
    assert leaks["L3_same_subject"] == ["fixtures/intake/e.mov", "reference/ref-kip-up.mp4"]


def test_report_states_single_subject_limit_and_verdict():
    ev = esc.eval_groups(_clips()[:3], _pairs(), [_test("sealed", [H("c")])])
    ok = {"L1_same_file": [], "L2_same_session": [], "L3_same_subject": ["reference/ref-x.mp4"]}
    md = esc.render_report(ev, ok, 10, now="t")
    assert "인물 분리 불가" in md and "세션 분리 OK" in md
    assert esc.verdict_code(ev, ok) == 0
    bad = {"L1_same_file": ["fixtures/phase15/climb/fault.mp4"], "L2_same_session": [], "L3_same_subject": []}
    md2 = esc.render_report(ev, bad, 10, now="t")
    assert "누수" in md2
    assert esc.verdict_code(ev, bad) == 1


def test_empty_eval_set_is_not_a_pass():
    ev = esc.eval_groups(_clips(), _pairs(), [_test("closed", [H("b")], test_id="t-closed")])
    md = esc.render_report(ev, NO_LEAKS, 10, now="t")
    assert "평가셋 없음 — 다음 시험 영상이 봉인되기 전까지 게이트 4 꺼짐" in md
    assert "세션 분리 OK" not in md
    assert "인물 분리 불가" not in md          # 평가 인물 0명에 "1명뿐(정은지)" 이라 쓰면 거짓
    assert "t-closed" in md                    # 왜 비었는지 — 닫힌 시험을 적는다
    assert esc.verdict_code(ev, NO_LEAKS) == 2
