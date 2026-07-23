"""Phase 33 (33-18) — gate_check.py 계약 잠금 (LOCAL ONLY, 순수 데이터 게이트).

codex concern 8: 다운스트림 게이트가 `grep -q PASS` 처럼 **문서가 단어 PASS 를
포함하기만 하면** 통과해 버린다 — 안에 FAIL 항목이 있어도 샌다. gate_check 는
JSON 을 파싱해 **명명된 항목이 정확히 status=="PASS"** 일 때만 0 을 반환한다.

이 테스트가 잠그는 것:
  1. FAIL 항목이 하나라도 있으면, 문서에 'PASS' 문자열이 있어도 non-zero.
  2. 전 항목 PASS 문서는 0.
  3. scoring-constant drift(tol/slope/cap/epsilon)는 non-zero — D-20/D-29 불변식을
     grep 이 아니라 데이터 비교로 강제.
"""

from __future__ import annotations

import json

import gate_check as gc


def _write(tmp_path, name: str, obj: dict) -> str:
    p = tmp_path / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


# ─────────────────────── 1. FAIL 항목이 있으면 'PASS' 문자열 있어도 실패 ───────────────────────


def test_require_all_pass_rejects_doc_with_fail_item(tmp_path):
    # 문서에 'PASS' 문자열이 다수 존재 — grep 게이트는 통과시킨다.
    evidence = {
        "successMarginPositive": {"status": "PASS"},
        "faultSuccessSeparation": {"status": "PASS"},
        "m3Fired": {"status": "FAIL", "note": "still 12/12 inert but text says PASS elsewhere"},
        "safetyNoRegression": {"status": "PASS"},
    }
    path = _write(tmp_path, "evidence_fail.json", evidence)
    rc = gc.main(
        [
            "--file",
            path,
            "--require-all-pass",
            "successMarginPositive",
            "faultSuccessSeparation",
            "m3Fired",
            "safetyNoRegression",
        ]
    )
    assert rc != 0


def test_require_all_pass_accepts_all_pass_doc(tmp_path):
    evidence = {
        "successMarginPositive": {"status": "PASS"},
        "faultSuccessSeparation": {"status": "PASS"},
        "m3Fired": {"status": "PASS"},
        "safetyNoRegression": {"status": "PASS"},
    }
    path = _write(tmp_path, "evidence_pass.json", evidence)
    rc = gc.main(
        [
            "--file",
            path,
            "--require-all-pass",
            "successMarginPositive",
            "faultSuccessSeparation",
            "m3Fired",
            "safetyNoRegression",
        ]
    )
    assert rc == 0


def test_require_all_pass_rejects_missing_item(tmp_path):
    evidence = {"a": {"status": "PASS"}}
    path = _write(tmp_path, "evidence_missing.json", evidence)
    rc = gc.main(["--file", path, "--require-all-pass", "a", "b"])
    assert rc != 0


# ─────────────────────── 2. hash count 게이트 ───────────────────────


def test_require_hashes_count(tmp_path):
    good = {"perDocHashes": {f"ref-{i}": "deadbeef" * 8 for i in range(11)}}
    path_ok = _write(tmp_path, "hashes_ok.json", good)
    assert gc.main(["--file", path_ok, "--require-hashes", "11"]) == 0

    short = {"perDocHashes": {f"ref-{i}": "deadbeef" for i in range(5)}}
    path_short = _write(tmp_path, "hashes_short.json", short)
    assert gc.main(["--file", path_short, "--require-hashes", "11"]) != 0

    empty_val = {"perDocHashes": {f"ref-{i}": "" for i in range(11)}}
    path_empty = _write(tmp_path, "hashes_empty.json", empty_val)
    assert gc.main(["--file", path_empty, "--require-hashes", "11"]) != 0


# ─────────────────────── 3. rollback-trigger 게이트 ───────────────────────


def test_no_rollback_trigger(tmp_path):
    clean = {"rollbackTriggers": {"marginNegative": False, "safetyRegression": False}}
    path_clean = _write(tmp_path, "rb_clean.json", clean)
    assert gc.main(["--file", path_clean, "--no-rollback-trigger"]) == 0

    tripped = {"rollbackTriggers": {"marginNegative": False, "safetyRegression": True}}
    path_trip = _write(tmp_path, "rb_trip.json", tripped)
    assert gc.main(["--file", path_trip, "--no-rollback-trigger"]) != 0


# ─────────────────────── 4. scoring-constants drift ───────────────────────


def _pinned(tmp_path) -> str:
    return _write(
        tmp_path,
        "pinned.json",
        {
            "tol": 20,
            "slope": 1.2,
            "cap": 90,
            "MEAN_EPSILON_DEG": 0.1,
            "P99_EPSILON_DEG": 1.0,
        },
    )


def test_scoring_constants_match_accepts_identical(tmp_path):
    pinned = _pinned(tmp_path)
    same = _write(
        tmp_path,
        "constants_same.json",
        {
            "tol": 20,
            "slope": 1.2,
            "cap": 90,
            "MEAN_EPSILON_DEG": 0.1,
            "P99_EPSILON_DEG": 1.0,
        },
    )
    assert gc.main(["--file", same, "--scoring-constants-match", pinned]) == 0


def test_scoring_constants_match_rejects_drift(tmp_path):
    pinned = _pinned(tmp_path)
    drifted = _write(
        tmp_path,
        "constants_drift.json",
        {
            "tol": 25,  # tol 20 → 25 drift (re-fit 금지 위반)
            "slope": 1.2,
            "cap": 90,
            "MEAN_EPSILON_DEG": 0.1,
            "P99_EPSILON_DEG": 1.0,
        },
    )
    assert gc.main(["--file", drifted, "--scoring-constants-match", pinned]) != 0


def test_scoring_constants_match_rejects_missing_constant(tmp_path):
    pinned = _pinned(tmp_path)
    missing = _write(
        tmp_path,
        "constants_missing.json",
        {"tol": 20, "slope": 1.2, "cap": 90, "MEAN_EPSILON_DEG": 0.1},
    )
    assert gc.main(["--file", missing, "--scoring-constants-match", pinned]) != 0


# ─────────────────────── 5. 여러 모드 결합 — 하나라도 실패면 non-zero ───────────────────────


def test_combined_modes_fail_if_any_gate_fails(tmp_path):
    pinned = _pinned(tmp_path)
    evidence = {
        "a": {"status": "PASS"},
        "perDocHashes": {f"ref-{i}": "h" * 16 for i in range(11)},
        "rollbackTriggers": {"x": False},
        "tol": 20,
        "slope": 1.2,
        "cap": 90,
        "MEAN_EPSILON_DEG": 0.1,
        "P99_EPSILON_DEG": 99.0,  # drift
    }
    path = _write(tmp_path, "combined.json", evidence)
    rc = gc.main(
        [
            "--file",
            path,
            "--require-all-pass",
            "a",
            "--require-hashes",
            "11",
            "--no-rollback-trigger",
            "--scoring-constants-match",
            pinned,
        ]
    )
    assert rc != 0
