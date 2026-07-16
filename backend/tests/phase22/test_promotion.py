"""22-12 승격 래칫 순수 로직 테스트 (TDD RED 먼저).

불변식:
  · parse_gate_verdict — require-pass exit 0 만 pass=True (게이트 PASS 유일 승격 조건).
  · make_ledger_entry — promoted = verdict.pass (판정 문자열만, 사람/judge 점수 저장 금지).
  · apply_ratchet — append-only + promoted=True 일 때만 current 전진(단조성), 기존 entries 불변.
  · current=None 에서 FAIL 만 쌓이면 current 는 None 유지(미승격 모델이 current 가 되는 경로 부재).
  · make_cycle_report — 비용 관측치 전 필드 방출, est_gemini_calls = new_labeled*2, 사람 점수 필드 없음.

네트워크·파일 I/O 0 — 순수 함수만 검증.
"""

from __future__ import annotations

import copy

from sft import promotion


def _verdict(passed: bool):
    return promotion.parse_gate_verdict(0 if passed else 1)


# ── parse_gate_verdict ──────────────────────────────────────────────────────
def test_parse_gate_verdict_exit0_only_passes():
    assert promotion.parse_gate_verdict(0)["pass"] is True
    assert promotion.parse_gate_verdict(1)["pass"] is False
    assert promotion.parse_gate_verdict(3)["pass"] is False


def test_parse_gate_verdict_per_gate_map_from_results():
    # assert_gates.run_all_checks() 출력 형태 {label: (fails, skips)}.
    results = {
        "motion_balance": ([], []),
        "eval18_no_regression": (["[eval18] 변별 실패"], []),
        "svg_spec_validity": ([], ["SKIPPED (svg 0건)"]),
    }
    v = promotion.parse_gate_verdict(1, results)
    assert v["gates"]["motion_balance"] == "PASS"
    assert v["gates"]["eval18_no_regression"] == "FAIL"
    # skip-only 는 fail 아님 → PASS 로 표기(fails 없음).
    assert v["gates"]["svg_spec_validity"] == "PASS"
    assert v["pass"] is False  # exit 1


# ── make_ledger_entry ───────────────────────────────────────────────────────
def test_make_ledger_entry_promoted_follows_verdict():
    snap = {"train_rows": 120, "val_rows": 4, "distill": 90, "perturb": 20, "text": 10}
    e_pass = promotion.make_ledger_entry(
        "/w/ckpt-52-merged", _verdict(True), snap, ["watch-260716"], "2026-07-16T00:00:00Z"
    )
    e_fail = promotion.make_ledger_entry(
        "/w/ckpt-52-merged", _verdict(False), snap, ["watch-260716"], "2026-07-16T00:00:00Z"
    )
    assert e_pass["promoted"] is True
    assert e_fail["promoted"] is False
    assert e_pass["ckpt"] == "/w/ckpt-52-merged"
    assert e_pass["data"] == snap
    assert e_pass["batch_ids"] == ["watch-260716"]


# ── apply_ratchet ───────────────────────────────────────────────────────────
def _new_ledger():
    return {"schema": "promotion-ledger-v1", "current": None, "entries": []}


def test_apply_ratchet_pass_advances_current():
    ledger = _new_ledger()
    entry = promotion.make_ledger_entry("/w/a-merged", _verdict(True), {}, [], "t1")
    out = promotion.apply_ratchet(ledger, entry)
    assert out["current"] == {"ckpt": "/w/a-merged", "ts": "t1"}
    assert len(out["entries"]) == 1


def test_apply_ratchet_fail_does_not_advance_current():
    ledger = _new_ledger()
    ledger = promotion.apply_ratchet(
        ledger, promotion.make_ledger_entry("/w/a-merged", _verdict(True), {}, [], "t1")
    )
    before_current = copy.deepcopy(ledger["current"])
    out = promotion.apply_ratchet(
        ledger, promotion.make_ledger_entry("/w/b-merged", _verdict(False), {}, [], "t2")
    )
    # FAIL entry 후 current 는 직전 promoted(a) 를 그대로 가리킴.
    assert out["current"] == before_current
    assert out["current"]["ckpt"] == "/w/a-merged"
    assert len(out["entries"]) == 2


def test_apply_ratchet_does_not_mutate_prior_entries():
    ledger = promotion.apply_ratchet(
        _new_ledger(),
        promotion.make_ledger_entry("/w/a-merged", _verdict(True), {"x": 1}, [], "t1"),
    )
    before = copy.deepcopy(ledger)
    _ = promotion.apply_ratchet(
        ledger, promotion.make_ledger_entry("/w/b-merged", _verdict(False), {}, [], "t2")
    )
    # 원본 ledger 는 변형되지 않는다(순수 — deep-equal 보존).
    assert ledger == before


def test_current_stays_none_when_only_fail_accumulates():
    ledger = _new_ledger()
    for i in range(3):
        ledger = promotion.apply_ratchet(
            ledger,
            promotion.make_ledger_entry(f"/w/f{i}-merged", _verdict(False), {}, [], f"t{i}"),
        )
    assert ledger["current"] is None  # 미승격 모델이 current 가 되는 경로 부재.
    assert len(ledger["entries"]) == 3


def test_two_fails_then_pass_advances_and_keeps_history():
    ledger = _new_ledger()
    seq = [(False, "/w/f1-merged"), (False, "/w/f2-merged"), (True, "/w/p3-merged")]
    for i, (passed, ckpt) in enumerate(seq):
        ledger = promotion.apply_ratchet(
            ledger, promotion.make_ledger_entry(ckpt, _verdict(passed), {}, [], f"t{i}")
        )
    assert ledger["current"] == {"ckpt": "/w/p3-merged", "ts": "t2"}
    assert len(ledger["entries"]) == 3
    assert [e["promoted"] for e in ledger["entries"]] == [False, False, True]


# ── make_cycle_report ───────────────────────────────────────────────────────
def test_make_cycle_report_all_fields_and_cost_estimate():
    label_stats = {
        "n_processed": 12,
        "stats": {
            "accepted": 9,
            "rejected_judge": 1,
            "rejected_parse": 1,
            "rejected_contract": 1,
        },
    }
    report = promotion.make_cycle_report(label_stats, 4321.0, _verdict(False), promoted=False)
    for key in (
        "new_labeled", "accepted", "rejected_judge", "rejected_parse",
        "rejected_contract", "est_gemini_calls", "sft_wall_seconds", "gates", "promoted",
    ):
        assert key in report, key
    assert report["new_labeled"] == 12
    assert report["accepted"] == 9
    assert report["est_gemini_calls"] == 24  # new_labeled * 2 (교사 + judge)
    assert report["sft_wall_seconds"] == 4321.0
    assert report["promoted"] is False
    # 사람 점수 라벨 필드 부재(객관성 hard gate).
    assert "human_score" not in report
    assert "score" not in report
