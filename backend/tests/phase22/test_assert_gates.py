"""22-07 assert_gates pod-free 검증 — 합성 artifact fixture 로 check_* 로직만.

Pod artifact 없이 게이트 의미론을 강제한다:
  · 각 check 의 PASS/FAIL 방향성
  · ARTIFACT-GATED: artifact 부재 = SKIPPED (FAIL 아님)
  · main() exit 규약: FAIL=1 / SKIPPED-only=0+경고 / --require-pass 는 SKIPPED 면 비0 (DR-03)
  · SKIPPED vs DESCOPED (quick-260918-0q8): 선언된 범위 밖(DESCOPED)은 승격을 막지
    않고, 쟀어야 하는데 못 잰 것(SKIPPED)만 막는다. 섞여 있던 탓에 승격이 구조적으로
    도달 불가였다 — assert_gates 모듈 독트린 참조.
"""
# svg_spec 게이트는 2026-08-30 에 폐기했다 — 일러스트(소비처)가 08-24 에 전면
# 제거됐고, 채워질 수 없는 배선(reference_loader 미주입)으로 승급을 막고 있었다.
# 사유 전문 = assert_gates.py 의 "(6) svg_spec 게이트 — 폐기" 주석.
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[2]
for p in (BACKEND / "evals" / "phase22", BACKEND / "training", BACKEND / "shared" / "python"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import assert_gates as ag  # noqa: E402


# ── fixture 빌더 (합성 — Pod/보유 영상 무관) ─────────────────────────────────
def _report(faults=None, svg_spec=None, coaching="ok"):
    return {
        "coaching": coaching,
        "corrected_coords": [],
        "faults": faults if faults is not None else [],
        "segments": [],
        "svg_spec": svg_spec,
        "time_anchors": [],
    }


def _fault(category="무릎 굽음", body_part="무릎", student=140.0, reference=175.0):
    return {
        "fault_category": category,
        "body_part": body_part,
        "student_angle_deg": student,
        "reference_angle_deg": reference,
    }


def _rec(item_id, typ="real", mode="zero", report=None, raw=None, **extra):
    rec = {"id": item_id, "type": typ, "mode": mode}
    if raw is None and report is not None:
        raw = json.dumps(report, ensure_ascii=False)
    if raw is not None:
        rec["raw"] = raw
    rec.update(extra)
    return rec


def _doc(records):
    return {"_meta": {}, "records": records}


def _synth_rec(item_id, corrected, uncorrected, stage=1, report=None):
    return _rec(
        item_id, typ="synthetic_grounding", stage=stage,
        report=report if report is not None else _report(),
        grounding=corrected, grounding_uncorrected=uncorrected,
    )


# ── Test 1: synthetic holdout (상대 개선만) ──────────────────────────────────
def test_synthetic_holdout_improvement_passes():
    doc = _doc([_synth_rec("s1", 0.01, 0.05), _synth_rec("s2", 0.02, 0.04)])
    assert ag.check_synthetic_holdout(doc) == []


def test_synthetic_holdout_no_improvement_fails():
    doc = _doc([_synth_rec("s1", 0.05, 0.05), _synth_rec("s2", 0.06, 0.04)])
    fails = ag.check_synthetic_holdout(doc)
    assert fails and "[synthetic_holdout]" in fails[0]


def test_synthetic_holdout_old_report_skipped():
    rec = _rec("s1", typ="synthetic_grounding", report=_report(), grounding=0.01)
    res = ag.check_synthetic_holdout(_doc([rec]))
    assert res and res[0].startswith("SKIPPED")


# ── Test 2: motion balance ──────────────────────────────────────────────────
def _manifest(items):
    return {"items": items}


def test_motion_balance_kipup_only_fails():
    manifest = _manifest([
        {"id": "real-kipup-correct", "type": "real", "motion": "kip-up"},
        {"id": "real-kipup-fault", "type": "real", "motion": "kip-up"},
    ])
    doc = _doc([
        _rec("real-kipup-correct", report=_report()),
        _rec("real-kipup-fault", report=_report()),
    ])
    fails = ag.check_motion_balance(doc, manifest=manifest)
    assert any("kip-up 단독" in f for f in fails)


def test_motion_balance_full_coverage_passes():
    manifest = _manifest([
        {"id": "real-kipup-correct", "type": "real", "motion": "kip-up"},
        {"id": "real-climb-correct", "type": "real", "motion": "climb"},
    ])
    doc = _doc([
        _rec("real-kipup-correct", report=_report()),
        _rec("real-climb-correct", report=_report()),
    ])
    assert ag.check_motion_balance(doc, manifest=manifest) == []


def test_motion_balance_missing_item_fails():
    manifest = _manifest([
        {"id": "real-kipup-correct", "type": "real", "motion": "kip-up"},
        {"id": "real-climb-correct", "type": "real", "motion": "climb"},
    ])
    doc = _doc([_rec("real-kipup-correct", report=_report())])
    fails = ag.check_motion_balance(doc, manifest=manifest)
    assert any("real-climb-correct" in f for f in fails)


# ── Test 3: EVAL18 무회귀 ────────────────────────────────────────────────────
_PAIRS = [
    {"motion_id": "power-spin", "expected": "discriminate"},
    {"motion_id": "kip-up", "expected": "known_false_positive"},
]


def test_eval18_discriminate_pass():
    doc = _doc([
        _rec("real-powerspin-fault", report=_report(faults=[_fault(), _fault(body_part="스플릿")])),
        _rec("real-powerspin-correct", report=_report(faults=[])),
        _rec("real-kipup-fault", report=_report(faults=[])),
        _rec("real-kipup-correct", report=_report(faults=[])),
    ])
    res = ag.check_eval18_no_regression(doc, pairs=_PAIRS)
    # 모듈 자신의 분류기를 쓴다 — 접두어를 테스트가 다시 적으면 또 어긋난다.
    fails, skips = ag._split_skips(res)
    assert fails == []
    # known 페어는 FAIL 없이 명시 추적 라인 — 그리고 **승격을 막지 않는** DESCOPED 다.
    kipup = [x for x in skips if "kip-up" in x]
    assert kipup, skips
    assert kipup[0].startswith(ag.DESCOPED)
    assert ag.blocking_skips(skips) == []


def test_eval18_fault_member_zero_faults_fails():
    doc = _doc([
        _rec("real-powerspin-fault", report=_report(faults=[])),
        _rec("real-powerspin-correct", report=_report(faults=[])),
    ])
    res = ag.check_eval18_no_regression(doc, pairs=[_PAIRS[0]])
    assert any("짚기 실패" in r for r in res)


def test_eval18_no_discrimination_fails():
    doc = _doc([
        _rec("real-powerspin-fault", report=_report(faults=[_fault()])),
        _rec("real-powerspin-correct", report=_report(faults=[_fault()])),
    ])
    res = ag.check_eval18_no_regression(doc, pairs=[_PAIRS[0]])
    assert any("변별 실패" in r for r in res)


# ── Test 4: determinism (verdict 단위 — raw bytes 아님) ─────────────────────
def test_determinism_same_verdicts_pass():
    r1 = _doc([_rec("real-a-fault", report=_report(faults=[_fault()]))])
    r2 = _doc([_rec("real-a-fault", report=_report(faults=[_fault()]), raw=None)])
    # run2 는 문장이 달라도(coaching) verdict 같으면 PASS — bit-비결정 분리.
    r2["records"][0]["raw"] = json.dumps(_report(faults=[_fault()], coaching="다른 문장"))
    assert ag.check_determinism(r1, r2) == []


def test_determinism_verdict_mismatch_fails():
    r1 = _doc([_rec("real-a-fault", report=_report(faults=[_fault()]))])
    r2 = _doc([_rec("real-a-fault", report=_report(faults=[]))])
    fails = ag.check_determinism(r1, r2)
    assert fails and "[determinism]" in fails[0]


def test_determinism_no_common_records_skipped():
    r1 = _doc([_rec("real-a-fault", report=_report())])
    r2 = _doc([_rec("real-b-fault", report=_report())])
    res = ag.check_determinism(r1, r2)
    assert res and res[0].startswith("SKIPPED")


# ── Test 5: ARTIFACT-GATED + main() exit 규약 (DR-03) ───────────────────────
def test_artifact_absent_all_skipped_exit0(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    assert ag.main(["--model", "no/such-model"]) == 0
    out = capsys.readouterr().out
    assert "SKIPPED" in out


def test_require_pass_rejects_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    assert ag.main(["--model", "no/such-model", "--require-pass"]) != 0


def test_fail_exit1_with_real_artifact(tmp_path, monkeypatch):
    # 개선 없는 synthetic holdout 을 가진 run1 artifact → exit 1.
    out_dir = tmp_path / "phase22"
    out_dir.mkdir(parents=True)
    doc = _doc([_synth_rec("s1", 0.09, 0.05)])
    (out_dir / "bakeoff_fake_model_run1.json").write_text(
        json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    assert ag.main(["--model", "fake/model"]) == 1


# ── Test 6: svg_spec 형식·존재 ──────────────────────────────────────────────
_SVG_OK = {"force_vector": [1, 0], "ideal_trajectory": [[0, 0], [1, 1]], "target_angle_deg": 175}






def test_parsed_report_prose_still_none():
    """JSON 없는 산문 raw → 여전히 None (실패 집계 유지 — 관대화 금지)."""
    assert ag._parsed_report(_rec("real-b-fault", raw="결함이 없습니다.")) is None
    # 순수 JSON(legacy guided 출력) 하위호환 — 동일 결과.
    pure = ag._parsed_report(_rec("real-c-fault", report=_report(faults=[_fault()])))
    assert isinstance(pure, dict) and len(pure["faults"]) == 1


# ── 추적성 + 단조성 번안 ────────────────────────────────────────────────────
def test_traceability_nonfinite_angle_fails():
    doc = _doc([_rec("real-a-fault", report=_report(faults=[_fault(student=float("nan"))]))])
    fails = ag.check_traceability_and_monotonicity(doc)
    assert any("[traceability]" in f for f in fails)


def test_traceability_missing_routing_keys_fails():
    f = {"student_angle_deg": 140.0}
    doc = _doc([_rec("real-a-fault", report=_report(faults=[f]))])
    fails = ag.check_traceability_and_monotonicity(doc)
    assert any("라우팅 키" in x for x in fails)


def test_monotonicity_decreasing_fault_count_fails():
    doc = _doc([
        _synth_rec("s11", 0.01, 0.05, stage=1, report=_report(faults=[_fault(), _fault()])),
        _synth_rec("s21", 0.01, 0.05, stage=2, report=_report(faults=[_fault()])),
        _synth_rec("s31", 0.01, 0.05, stage=3, report=_report(faults=[])),
    ])
    fails = ag.check_traceability_and_monotonicity(doc)
    assert any("[monotonicity]" in f for f in fails)


def test_monotonicity_nondecreasing_passes():
    doc = _doc([
        _synth_rec("s11", 0.01, 0.05, stage=1, report=_report(faults=[])),
        _synth_rec("s21", 0.01, 0.05, stage=2, report=_report(faults=[_fault()])),
        _synth_rec("s31", 0.01, 0.05, stage=3, report=_report(faults=[_fault(), _fault()])),
    ])
    assert ag.check_traceability_and_monotonicity(doc) == []


# ── quick-260918-0q8: SKIPPED vs DESCOPED — 승격 도달 가능성 ──────────────────
#
# 2026-09-14 실측으로 "재학습을 아무리 잘 돌려도 승격 불가"가 확인됐다. 원인은
# 두 의미가 한 통에 있었던 것 — pairs.yaml 이 known_issue 로 못박은 페어와
# belle 이 descope 한 트랙이, 못 잰 artifact 와 같은 취급을 받아 --require-pass 를
# 항상 exit 3 으로 만들었다. 아래 3개가 그 회귀를 붙잡는다.


def test_descoped_does_not_block_promotion():
    """선언된 범위 밖(DESCOPED)만 남으면 승격을 막지 않는다."""
    skips = [
        f"{ag.DESCOPED} (eval18 kip-up: expected=known_false_positive — 명시 추적만)",
        f"{ag.DESCOPED} (perturb 트랙 0행 — belle C1 descope)",
    ]
    assert ag.blocking_skips(skips) == []
    assert len(ag.descoped_only(skips)) == 2


def test_unmeasured_still_blocks_promotion():
    """못 잰 것(SKIPPED)은 그대로 막는다 — '못 쟀다'를 '통과'로 번역하지 않는다."""
    skips = [
        f"{ag.DESCOPED} (eval18 climb: expected=known_gate_blocked)",
        f"{ag.SKIPPED} (SFT bake-off run1 artifact absent)",
    ]
    blocking = ag.blocking_skips(skips)
    assert len(blocking) == 1
    assert "artifact absent" in blocking[0]


def test_perturb_descope_is_not_blocking():
    """belle C1 descope 된 좌표 보정 게이트가 DESCOPED 로 나온다 (라이브 함수)."""
    res = ag.check_synthetic_holdout(None, corpus_meta={"track_counts": {"perturb": 0}})
    fails, skips = ag._split_skips(res)
    assert fails == []
    assert skips and skips[0].startswith(ag.DESCOPED)
    assert ag.blocking_skips(skips) == []


def _full_passing_doc():
    """5 게이트를 전부 만족하는 run 리포트 — DESCOPED 만 남게 만든 fixture.

    · motion_balance: manifest 의 real 21항목 전부에 비-skip 레코드
    · eval18: 변별 4페어는 fault>correct, known 2페어는 DESCOPED 로 빠진다
    · traceability: fault 항목에 유한 각도 + 라우팅 키 (_fault 가 이미 만족)
    · monotonicity: 합성 stage 1→2→3 평균 결함 수 비감소
    · synthetic_holdout: perturb 0행이라 DESCOPED
    """
    import yaml as _yaml
    manifest = _yaml.safe_load(
        (BACKEND / "evals" / "phase22" / "fixtures" / "manifest.yaml").read_text(encoding="utf-8"))
    recs = []
    for row in manifest.get("items") or []:
        if row.get("type") != "real":
            continue
        rid = row.get("id")
        # 변별 4페어만 fault 쪽에 결함을 심는다(fault > correct). 나머지는 빈 결함이어도
        # motion_balance 는 '비-skip 레코드 존재'만 본다.
        discriminating = any(
            k in rid for k in ("powerspin", "peterpan", "elbowtwist", "pdshape"))
        faults = [_fault(), _fault(body_part="스플릿")] if (
            discriminating and rid.endswith("-fault")) else []
        recs.append(_rec(rid, report=_report(faults=faults)))
    # 단조성 트랙 — stage 1→2→3 결함 수 비감소.
    for stage, n in ((1, 1), (2, 1), (3, 2)):
        recs.append(_rec(f"synthetic-s{stage}", type="synthetic", stage=stage,
                         report=_report(faults=[_fault()] * n)))
    return _doc(recs)


def test_require_pass_reaches_exit0_with_only_descoped(tmp_path, monkeypatch, capsys):
    """★ 회귀 방지의 핵심 — 범위 안을 다 재면 --require-pass 가 exit 0 에 **도달한다**.

    2026-09-14 실측: 고치기 전에는 이 조건에서도 항상 exit 3 이었다(승격 구조적 불가).
    """
    out_dir = tmp_path / "phase22"
    out_dir.mkdir(parents=True)
    doc = _full_passing_doc()
    for run in ("run1", "run2"):
        (out_dir / f"bakeoff_fake_model_{run}.json").write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    # 실제 상황 그대로 — 학습셋 perturb 트랙 0행(belle C1 descope).
    meta = tmp_path / "_meta.json"
    meta.write_text(json.dumps({"track_counts": {"perturb": 0, "distill": 400}}),
                    encoding="utf-8")
    monkeypatch.setenv("SFT_CORPUS_META", str(meta))
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    rc = ag.main(["--model", "fake/model", "--require-pass"])
    out = capsys.readouterr().out
    assert rc == 0, out
    # 범위 밖 항목은 사라지지 않고 **보인다** — 조용히 통과시키는 것이 아니다.
    assert ag.DESCOPED in out
    assert "kip-up" in out or "climb" in out
