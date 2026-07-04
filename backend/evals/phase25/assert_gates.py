#!/usr/bin/env python3
"""Phase 25 vision-pointed 상체 감점 게이트 (pod-free, exit 0 = PASS).

phase24 의 7 게이트(traceability / monotonicity / determinism / criterion-selection /
generalization / clean_residual / sensitivity)를 **import 재사용**하고, phase25 신규
게이트를 추가한다 (25-04 Task 1):

  8.  check_success_100            — success 멤버 overallScore != 100 이 하나라도 있으면
                                     FAIL (phase24 check_generalization 의 within-tolerance
                                     허용보다 강함 — 260702-o0c success 위양성 4건 재발 금지).
                                     climb 은 phase18 known not_pole 게이트라 제외(그 유지는
                                     check_fault_no_regression 소관).
  9.  check_pointed_only_window    — 어느 멤버든 seedObservation.window_joints ⊄
                                     pointed_joints 면 FAIL (SCORE-15 구조 assert: window
                                     감점은 vision 이 짚은 관절에서만).
  10. check_kipup_upper_structure  — kip-up fault 멤버 3중 구조 assert:
                                     (a) overallScore < phase24 baseline (방향 비교 —
                                         고정 타깃 아님), (b) pointed 상체 관절(shoulder/
                                         elbow)의 angle_vs_reference record ≥ 1,
                                     (c) 그 record 관절 ∈ pointed set.
  11. check_fault_no_regression    — 5 fault 멤버 각각 overallScore <= phase24 baseline
                                     (방향 비교, 무퇴행 — curve-fit 아님) + climb not_pole
                                     유지. baseline artifact 부재 시 SKIPPED.
  12. check_cold_warm_determinism  — cold sweep vs warm 재실행(캐시 hit, Gemini 0 call)
                                     report 동일성: status/errorCode/overallScore/
                                     activatedCriteria/deductionBreakdown. warm report
                                     부재 시 SKIPPED.

특정 점수 assert 금지 (locked, [[scoring-redesign-must-generalize-no-overfit]]):
  kip-up 의 "phase24 baseline 미만" 은 baseline artifact(phase24_sweep_report.json 의
  kip-up fault overallScore = 실측 88) **대비 방향 비교**(fault 변별 개선 gate, ROADMAP
  locked)이지 고정 타깃이 아니다. 게이트 소스에 점수 리터럴 타깃을 하드코딩하지 않는다.
  사람 점수 라벨 0 ([[analysis-objectivity-no-human-scores]]). 밴드 0.

artifact-gating (phase24 HIGH-4 패턴): 모든 신규 게이트는 sweep report artifact 부재 시
SKIPPED marker 반환(실패 아님). exit 계약 = phase24 동일: exit 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_LAYER = _HERE.parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

# ── artifacts (25-SWEEP-EVIDENCE 근본원인 4 — 신규 산출물/기준 물리 분리) ──────
# 신규 산출물(이번 sweep 의 report/breakdowns)은 run_sweep.py 와 동일 해석의
# repo 밖 EVAL_OUT_DIR 에서 읽는다 — sweep 이 repo 내 baseline/ 을 덮어써 pod
# 소스트리가 오염되고 게이트가 오염 기준으로 판정한 사고(2026-07-02) 재발 금지.
_EVAL_OUT_ENV = "EVAL_OUT_DIR"
_EVAL_OUT_DEFAULT = "/tmp/sunity_eval_out"
_OUT_DIR = (
    pathlib.Path(os.environ.get(_EVAL_OUT_ENV) or _EVAL_OUT_DEFAULT).expanduser()
    / "phase25"
).resolve()
_REPORT_ARTIFACT = _OUT_DIR / "phase25_sweep_report.json"
_REPORT_WARM_ARTIFACT = _OUT_DIR / "phase25_sweep_report_warm.json"
_BREAKDOWN_ARTIFACT = _OUT_DIR / "phase25_breakdowns.json"
# 비교 기준(baseline)은 **항상 git 커밋본**(repo 내 read-only) — EVAL_OUT_DIR 로
# 절대 리다이렉트하지 않는다. 방향 비교의 anchor 가 흔들리면 게이트가 무의미해진다.
_P24_REPORT_ARTIFACT = (
    _HERE.parents[0] / "phase24" / "baseline" / "phase24_sweep_report.json"
)

# 상체 관절 (SCORE-15 — kip-up 상체 감점 실효 판정 대상).
UPPER_BODY_JOINTS = ("left_shoulder", "right_shoulder", "left_elbow", "right_elbow")

# phase18 dataset 의 known not_pole 게이트 동작 (pairs.yaml / phase24 eval_keys.json:
# "climb=known not_pole gate"). 구조 기대이지 점수 타깃 아님 — climb 은 채점 자체가
# 안전 게이트로 차단되는 것이 정상이고, 그 유지는 check_fault_no_regression 이 assert.
KNOWN_NOT_POLE_GATED = frozenset({"climb"})


# ── phase24 게이트 모듈 로드 (import 재사용 — evals/ 는 패키지 아님) ───────────


def _load_phase24_gates():
    path = _HERE.parents[0] / "phase24" / "assert_gates.py"
    spec = importlib.util.spec_from_file_location("phase24_assert_gates", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── 공통 helpers ─────────────────────────────────────────────────────────────


def _load_json(path: pathlib.Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _results(report) -> list[dict]:
    if not isinstance(report, dict):
        return []
    res = report.get("results")
    return list(res) if isinstance(res, list) else []


def _is_not_pole(entry: dict) -> bool:
    """not_pole 안전 게이트 발화 여부 — errorCode 또는 exception 에서 검출."""
    ec = entry.get("errorCode")
    if isinstance(ec, str) and "not_pole" in ec:
        return True
    exc = entry.get("exception")
    return isinstance(exc, str) and "NotPoleMotionError" in exc


def _baseline_scores(p24_report) -> dict:
    """phase24 baseline report → {(motion_id, label): overallScore}."""
    return {
        (e.get("motion_id"), e.get("label")): e.get("overallScore")
        for e in _results(p24_report)
    }


def _records_of(entry: dict) -> list[dict]:
    bd = entry.get("deductionBreakdown")
    if isinstance(bd, dict):
        return list(bd.get("records") or [])
    return []


# ── (8) success_100 ──────────────────────────────────────────────────────────


def check_success_100(report=None) -> list[str]:
    """success 멤버 전원 overallScore == 100 (위양성 0 — 260702-o0c FAIL 재발 금지).

    phase24 check_generalization 은 success 의 within-tolerance record 를 허용했다 —
    phase25 는 "vision 짚은 관절만 window 감점" 구조가 지면 clean 영상은 감점 0 이어야
    하므로 100 을 직접 assert 한다 (RESULT 확인이지 curve-fit 타깃 아님: 100 은 감점
    record 0 의 산술 결과). climb 은 known not_pole 게이트 — 이 게이트 소관 아님.
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase25 sweep report absent for success_100)"]

    failures: list[str] = []
    for e in _results(report):
        if e.get("label") != "success":
            continue
        motion = e.get("motion_id")
        if motion in KNOWN_NOT_POLE_GATED:
            continue  # climb — not_pole 게이트 유지는 check_fault_no_regression 소관
        score = e.get("overallScore")
        if score != 100:
            failures.append(
                f"[success_100] {motion}: success member overallScore={score} != 100 "
                f"(status={e.get('status')}, errorCode={e.get('errorCode')}) — "
                f"clean 영상 위양성(260702-o0c 재발 방향)"
            )
    return failures


# ── (9) pointed_only_window ──────────────────────────────────────────────────


def check_pointed_only_window(report=None) -> list[str]:
    """전 멤버 seedObservation.window_joints ⊆ pointed_joints (SCORE-15 구조 assert).

    window 감점 seed 는 vision 이 짚은(pointed) 관절에서만 발생해야 한다 (25-01 merge
    불변식). 채점 완료(done) 멤버인데 seedObservation 자체가 없으면 harness 배선 결함
    으로 FAIL. not_pole 등으로 채점 전 중단된 멤버는 seed 부재가 정상(skip).
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase25 sweep report absent for pointed_only_window)"]

    failures: list[str] = []
    for e in _results(report):
        motion, label = e.get("motion_id"), e.get("label")
        seed = e.get("seedObservation")
        if not isinstance(seed, dict):
            if e.get("status") == "done":
                failures.append(
                    f"[pointed_only_window] {motion}/{label}: scored member has no "
                    f"seedObservation (harness tee 배선 결함)"
                )
            continue
        pointed = set(seed.get("pointed") or ())
        window = list(seed.get("window_joints") or ())
        stray = [jk for jk in window if jk not in pointed]
        if stray:
            failures.append(
                f"[pointed_only_window] {motion}/{label}: window_joints {stray} not in "
                f"pointed set {sorted(pointed)} — vision 이 짚지 않은 관절의 window 감점"
            )
    return failures


# ── (10) kipup_upper_structure ───────────────────────────────────────────────


def check_kipup_upper_structure(report=None, phase24_report=None) -> list[str]:
    """kip-up fault 3중 구조 assert — (a)+(b)+(c) 모두 충족해야 PASS.

    (a) overallScore < phase24 baseline(kip-up fault 실측값) — 방향 비교(fault 변별
        개선), 고정 타깃 아님.
    (b) deductionBreakdown 에 pointed 상체 관절(shoulder/elbow)의 angle_vs_reference
        record ≥ 1 — 상체 감점 메커니즘 실효(SCORE-15 "보이는데 0감점" 해소).
    (c) 그 record 관절 ∈ seedObservation.pointed — 감점 출처가 vision-짚기임을 구조로.
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase25 sweep report absent for kipup_upper_structure)"]
    if phase24_report is None:
        phase24_report = _load_json(_P24_REPORT_ARTIFACT)
    baseline = _baseline_scores(phase24_report).get(("kip-up", "fault"))
    if baseline is None:
        return ["SKIPPED (phase24 baseline artifact absent for kipup_upper_structure)"]

    entry = next(
        (e for e in _results(report)
         if e.get("motion_id") == "kip-up" and e.get("label") == "fault"),
        None,
    )
    if entry is None:
        return ["[kipup_upper] kip-up fault member missing from sweep report"]

    failures: list[str] = []
    # (a) 방향 비교 — baseline 미만.
    score = entry.get("overallScore")
    if score is None or not score < baseline:
        failures.append(
            f"[kipup_upper] (a) kip-up fault overallScore={score} not below phase24 "
            f"baseline={baseline} (방향 비교 — fault 변별 미개선)"
        )
    # (b) 상체 angle_vs_reference record ≥ 1.
    upper_records = [
        r for r in _records_of(entry)
        if isinstance(r.get("criterion"), str)
        and r["criterion"].startswith("angle_vs_reference__")
        and r["criterion"].removeprefix("angle_vs_reference__") in UPPER_BODY_JOINTS
    ]
    if not upper_records:
        failures.append(
            "[kipup_upper] (b) no upper-body (shoulder/elbow) angle_vs_reference "
            "deduction record — 상체 감점 메커니즘 미발화"
        )
    # (c) record 관절 ∈ pointed set.
    seed = entry.get("seedObservation")
    pointed = set((seed or {}).get("pointed") or ())
    for r in upper_records:
        jk = r["criterion"].removeprefix("angle_vs_reference__")
        if jk not in pointed:
            failures.append(
                f"[kipup_upper] (c) upper-body record joint {jk} not in pointed set "
                f"{sorted(pointed)} — 감점 출처가 vision-짚기가 아님"
            )
    return failures


# ── (11) fault_no_regression ─────────────────────────────────────────────────


def check_fault_no_regression(report=None, phase24_report=None) -> list[str]:
    """5 fault 멤버 score <= phase24 baseline (방향 비교, 무퇴행) + climb not_pole 유지.

    kip-up "< baseline" 과 동일한 방향 비교 패턴 — 특정 점수 짜맞추기 아님. climb 은
    양 멤버 모두 not_pole 안전 게이트가 유지돼야 한다 (게이트 해제 = 안전성 퇴행).
    baseline artifact 부재 시 SKIPPED (phase24 HIGH-4 패턴).
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase25 sweep report absent for fault_no_regression)"]
    if phase24_report is None:
        phase24_report = _load_json(_P24_REPORT_ARTIFACT)
    baselines = _baseline_scores(phase24_report)
    if not baselines:
        return ["SKIPPED (phase24 baseline artifact absent for fault_no_regression)"]

    failures: list[str] = []
    for e in _results(report):
        motion, label = e.get("motion_id"), e.get("label")
        if motion in KNOWN_NOT_POLE_GATED:
            # climb — 양 멤버 not_pole 유지.
            if not _is_not_pole(e):
                failures.append(
                    f"[fault_no_regression] {motion}/{label}: not_pole gate not retained "
                    f"(overallScore={e.get('overallScore')}, status={e.get('status')})"
                )
            continue
        if label != "fault":
            continue
        base = baselines.get((motion, "fault"))
        if base is None:
            continue  # baseline 에 없는 멤버 — 비교 불가(무해)
        score = e.get("overallScore")
        if score is None or score > base:
            failures.append(
                f"[fault_no_regression] {motion}: fault overallScore={score} > phase24 "
                f"baseline={base} (fault 변별 퇴행 방향)"
            )
    return failures


# ── (12) cold/warm determinism ───────────────────────────────────────────────

_DET_FIELDS = ("status", "errorCode", "overallScore", "activatedCriteria")


def check_cold_warm_determinism(report=None, warm_report=None) -> list[str]:
    """cold sweep vs warm 재실행 결정론 — 동일 verdict/breakdown.

    warm 재실행은 rich 캐시 hit(Gemini 0 call) 이므로 같은 입력에 대해 status/
    errorCode/overallScore/activatedCriteria/deductionBreakdown 이 동일해야 한다
    (MATH-determinism + selection-determinism 의 실영상 실측판). warm report 부재 시
    SKIPPED — Task 3 이 warm 재실행 후 생성.
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase25 sweep report absent for cold_warm_determinism)"]
    if warm_report is None:
        warm_report = _load_json(_REPORT_WARM_ARTIFACT)
    if not warm_report:
        return ["SKIPPED (phase25 warm rerun report absent for cold_warm_determinism)"]

    failures: list[str] = []
    cold_by = {(e.get("motion_id"), e.get("label")): e for e in _results(report)}
    warm_by = {(e.get("motion_id"), e.get("label")): e for e in _results(warm_report)}
    for key, ce in cold_by.items():
        we = warm_by.get(key)
        if we is None:
            failures.append(f"[cold_warm] {key[0]}/{key[1]}: missing from warm report")
            continue
        for field in _DET_FIELDS:
            if ce.get(field) != we.get(field):
                failures.append(
                    f"[cold_warm] {key[0]}/{key[1]}: {field} cold={ce.get(field)} != "
                    f"warm={we.get(field)}"
                )
        cb = json.dumps(ce.get("deductionBreakdown"), sort_keys=True, ensure_ascii=False)
        wb = json.dumps(we.get("deductionBreakdown"), sort_keys=True, ensure_ascii=False)
        if cb != wb:
            failures.append(
                f"[cold_warm] {key[0]}/{key[1]}: deductionBreakdown not identical "
                f"across cold/warm rerun"
            )
    return failures


# ── 짚기-FP 관측 (게이트 아님 — OD-2) ─────────────────────────────────────────


def summarize_pointing_fp(report) -> list[str]:
    """success 멤버의 Gemini collect 짚기 관측 요약 (짚기-FP율 — 관측 지표, 게이트 아님).

    감점은 tol 20° 게이트 + window 측정이 지므로 clean 영상 짚기 자체는 FAIL 이 아니다.
    리서치 §3 관측 공백(na_audit 는 collect 산출을 버림)을 harness tee 가 채운 첫 관측치.
    """
    lines: list[str] = []
    success = [e for e in _results(report) if e.get("label") == "success"]
    observed = [e for e in success if isinstance(e.get("collectObservation"), dict)]
    pointed_any = 0
    pointed_upper = 0
    for e in observed:
        pj = list((e.get("collectObservation") or {}).get("pointedJoints") or ())
        upper = [j for j in pj if j in UPPER_BODY_JOINTS]
        if pj:
            pointed_any += 1
        if upper:
            pointed_upper += 1
        lines.append(
            f"  · {e.get('motion_id')}: pointed={pj or '-'} upper={upper or '-'} "
            f"status={(e.get('collectObservation') or {}).get('collectionStatus')}"
        )
    if observed:
        lines.insert(0, (
            f"짚기-FP 관측 (success {len(observed)} 멤버): pointed-any "
            f"{pointed_any}/{len(observed)}, pointed-upper {pointed_upper}/{len(observed)} "
            f"— 관측 지표(게이트 아님, 감점 판정은 측정+tol 소관)"
        ))
    return lines


# ── compose ──────────────────────────────────────────────────────────────────


def _split_skips(results):
    skips = [r for r in results if r.startswith("SKIPPED")]
    fails = [r for r in results if not r.startswith("SKIPPED")]
    return fails, skips


def main() -> int:
    p24 = _load_phase24_gates()
    breakdowns = _load_json(_BREAKDOWN_ARTIFACT) or {}
    synthetic = p24._synthetic_breakdowns()

    checks = (
        # phase24 상속 7 게이트 (합성 게이트는 항상, artifact 게이트는 phase25 artifact 로).
        ("traceability", p24.check_traceability(synthetic)),
        ("monotonicity", p24.check_monotonicity()),
        ("determinism", p24.check_determinism()),
        ("criterion_selection", p24.check_criterion_selection_determinism()),
        ("generalization", p24.check_generalization(breakdowns=breakdowns)),
        ("clean_residual", p24.check_clean_residual(breakdowns=breakdowns)),
        ("sensitivity", p24.check_sensitivity()),
        # phase25 신규 게이트 (artifact-gated).
        ("success_100", check_success_100()),
        ("pointed_only_window", check_pointed_only_window()),
        ("kipup_upper_structure", check_kipup_upper_structure()),
        ("fault_no_regression", check_fault_no_regression()),
        ("cold_warm_determinism", check_cold_warm_determinism()),
    )

    failures: list[str] = []
    skipped: list[str] = []
    for _label, result in checks:
        fails, skips = _split_skips(result)
        failures.extend(fails)
        skipped.extend(skips)

    report = _load_json(_REPORT_ARTIFACT)
    if failures:
        print("Phase 25 gates FAIL:")
        for f in failures:
            print("  -", f)
        for s in skipped:
            print("  ·", s)
        if report:
            for line in summarize_pointing_fp(report):
                print(line)
        return 1

    print("Phase 25 gates PASS — phase24 상속 7 게이트 + 신규 5 게이트 green.")
    for s in skipped:
        print("  ·", s)
    if report:
        for line in summarize_pointing_fp(report):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
