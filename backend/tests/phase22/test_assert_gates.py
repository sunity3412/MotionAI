"""22-07 assert_gates pod-free 검증 — 합성 artifact fixture 로 check_* 로직만.

Pod artifact 없이 게이트 의미론을 강제한다:
  · 각 check 의 PASS/FAIL 방향성
  · ARTIFACT-GATED: artifact 부재 = SKIPPED (FAIL 아님)
  · main() exit 규약: FAIL=1 / SKIPPED-only=0+경고 / --require-pass 는 SKIPPED 도 비0 (DR-03)
"""
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
    fails = [r for r in res if not r.startswith("SKIPPED")]
    skips = [r for r in res if r.startswith("SKIPPED")]
    assert fails == []
    # known 페어는 FAIL 없이 명시 추적 라인.
    assert any("kip-up" in s for s in skips)


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


def test_svg_spec_majority_wellformed_passes():
    doc = _doc([
        _rec("real-a-fault", report=_report(faults=[_fault()], svg_spec=_SVG_OK)),
        _rec("real-b-fault", report=_report(faults=[_fault()], svg_spec=_SVG_OK)),
        _rec("real-c-fault", report=_report(faults=[_fault()], svg_spec=None)),
    ])
    assert ag.check_svg_spec_validity(doc) == []


def test_svg_spec_all_null_fails():
    doc = _doc([
        _rec("real-a-fault", report=_report(faults=[_fault()], svg_spec=None)),
        _rec("real-b-fault", report=_report(faults=[_fault()], svg_spec=None)),
    ])
    fails = ag.check_svg_spec_validity(doc)
    assert fails and "[svg_spec]" in fails[0]


def test_svg_spec_non_numeric_angle_fails():
    bad = dict(_SVG_OK, target_angle_deg="많이")
    doc = _doc([_rec("real-a-fault", report=_report(faults=[_fault()], svg_spec=bad))])
    fails = ag.check_svg_spec_validity(doc)
    assert any("target_angle_deg" in f for f in fails)


def test_svg_spec_no_faulted_reports_skipped():
    doc = _doc([_rec("real-a-correct", report=_report(faults=[]))])
    res = ag.check_svg_spec_validity(doc)
    assert res and res[0].startswith("SKIPPED")


# ── _parsed_report 방어 파서 (quick-260714-hv4 — 판정 기준 무변경) ──────────
def test_parsed_report_thought_preamble_extracted():
    """<thought> 프리앰블 + 유효 리포트 JSON raw → normalize_report dict 로 파싱.

    v4 자유생성 출력(학습 타겟 양식)이 게이트에서 파싱 실패 처리되던 계측 결함 fix —
    파서만 schema.extract_report_json 공유, 4 게이트 임계·비교식은 불변."""
    rep = _report(faults=[_fault()])
    raw = "<thought>\n무릎 각도 분석.\n</thought>\n" + json.dumps(rep, ensure_ascii=False)
    parsed = ag._parsed_report(_rec("real-a-fault", raw=raw))
    assert isinstance(parsed, dict)
    assert len(parsed["faults"]) == 1
    # normalize_report 통과 — REPORT_KEYS Null 고정 구조.
    assert "svg_spec" in parsed


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
