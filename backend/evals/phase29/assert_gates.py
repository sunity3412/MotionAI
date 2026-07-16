#!/usr/bin/env python3
"""Phase 29 D-02 mode3 tally 전환 게이트 (pod-free, exit 0 = PASS).

phase25 계보 승계 (artifact-gated SKIPPED / exit 계약 동일). 게이트 5종 + 보조 —
**전부 방향/구조/항등 비교, 점수 리터럴 타깃 0** (100/0 은 tally 항등식 상수로만 사용,
[[scoring-redesign-must-generalize-no-overfit]] + calibration-source-hard-gate):

  1. check_success_members        — success 멤버: 감점 record 0 AND overallScore >=
                                    그 키의 preSeamOverall(기존=구코드 점수, run_sweep
                                    read-only tee 캡처). ">= 기존" 은 clean tally 의
                                    100 승격 허용 (제품 수용 여부는 SUMMARY score-switch
                                    정지 조건 — 게이트 소관 아님).
  2. check_powerspin_fault        — power-spin fault: leg_extension 계열 감점 record
                                    >= 1 (유일한 criteria 보유 동작 — 변별 실증).
  3. check_fallback_identity      — kip-up/peter-pan/elbow-twist-sister/pdshape fault:
                                    deductionBreakdown 미방출 AND overallScore ==
                                    preSeamOverall 항등 (fallback 무회귀 — Pitfall 1:
                                    이 4동작 무감점은 정상. "감점 엔진 고장" 오판·임계
                                    조정 금지).
  4. check_cold_warm_determinism  — cold vs warm 재실행: 전 키 status/errorCode/
                                    overallScore/records 동일. warm report 부재 시 SKIPPED.
  5. check_breakdown_identity     — breakdown 방출 키: overallScore == final ==
                                    max(0, round(100 + Σ signed-negative points)) (D-02
                                    항등). record 구조 검증은 phase24 check_traceability
                                    import 재사용.
  보조. check_mode3_held_status   — 채점 완료 멤버 전원 visionVeto.status ==
                                    'mode3_held' ('applied' 오염 0 — 29-02 결정).

"기존 baseline" 의 소스: mode3 는 repo 커밋 baseline artifact 가 없다. run_sweep 의
read-only tee 가 캡처한 preSeamOverall 이 정확히 구코드가 저장했을 값이다 — 29-02 seam
은 종단 in-place 교체(방출 시)와 byte-불변 passthrough(미방출 시)뿐이므로 pre-seam
overallScore == 구코드 점수 (29-02 SUMMARY 케이스 3/7 근거). 자기 sweep 재보정이 아니다:
비교 기준은 이번 run 이 산출한 값이 아니라 seam 이전 단계(구코드와 동일 경로)의 값이다.

artifact-gating: sweep report artifact 부재 시 SKIPPED marker 반환(실패 아님).
exit 계약 = phase24/25 동일: exit 0 = PASS, 1 = FAIL.

not_pole 게이트는 mode3 에 미적용 — climb 관련 mode1 게이트는 포함하지 않는다
(RESEARCH Pattern 5 판단). climb 은 gate 1(success)과 4(결정론)에만 자연 포함.
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

# ── artifacts — 신규 산출물은 repo 밖 EVAL_OUT_DIR 에서 읽는다 (근본원인 4).
# repo 내 evals/*/baseline/ 은 read-only 이며 이 게이트는 어디에도 쓰지 않는다.
_EVAL_OUT_ENV = "EVAL_OUT_DIR"
_EVAL_OUT_DEFAULT = "/tmp/sunity_eval_out"
_OUT_DIR = (
    pathlib.Path(os.environ.get(_EVAL_OUT_ENV) or _EVAL_OUT_DEFAULT).expanduser()
    / "phase29"
).resolve()
_REPORT_ARTIFACT = _OUT_DIR / "phase29_sweep_report.json"
_REPORT_WARM_ARTIFACT = _OUT_DIR / "phase29_sweep_report_warm.json"

# criteria 실체 (RESEARCH Pitfall 1): power-spin 만 유효 criteria(무릎 EXTEND —
# leg_extension seed). 아래 4동작은 2026-06-27 Pod 진단으로 knee EXTEND 가 제거된
# 빈 criteria yaml → md 빈 dict → 미방출 fallback 이 정상 동작.
CRITERIA_MOTION = "power-spin"
FALLBACK_MOTIONS = ("kip-up", "peter-pan", "elbow-twist-sister", "pdshape")


def _load_phase24_gates():
    """phase24 게이트 헬퍼 import 재사용 (evals/ 는 패키지 아님 — importlib 로드)."""
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


def _records_of(entry: dict) -> list[dict]:
    bd = entry.get("deductionBreakdown")
    if isinstance(bd, dict):
        return list(bd.get("records") or [])
    return []


def _entry(report, motion: str, label: str) -> dict | None:
    return next(
        (e for e in _results(report)
         if e.get("motion_id") == motion and e.get("label") == label),
        None,
    )


# ── (1) success 멤버 — 무감점 + 비하락 ───────────────────────────────────────


def check_success_members(report=None) -> list[str]:
    """success 멤버: 감점 record 0 AND overallScore >= preSeamOverall(기존 점수).

    ">= 기존" 은 clean tally(records 0 → final 100)의 승격을 게이트로는 허용한다 —
    수용 여부는 SUMMARY score-switch 정지 조건(belle 결정)이 별도로 판정 (MEDIUM-1).
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase29 sweep report absent for success_members)"]

    failures: list[str] = []
    for e in _results(report):
        if e.get("label") != "success":
            continue
        motion = e.get("motion_id")
        if e.get("status") != "done":
            failures.append(
                f"[success] {motion}: status={e.get('status')} != done "
                f"(errorCode={e.get('errorCode')}, exception={e.get('exception')})"
            )
            continue
        records = _records_of(e)
        if records:
            failures.append(
                f"[success] {motion}: 감점 record {len(records)}건 "
                f"({sorted({r.get('criterion') for r in records})}) — success 무감점 위반"
            )
        score = e.get("overallScore")
        baseline = e.get("preSeamOverall")
        if baseline is None:
            failures.append(
                f"[success] {motion}: preSeamOverall 부재 — harness tee 배선 결함"
            )
        elif score is None or score < baseline:
            failures.append(
                f"[success] {motion}: overallScore={score} < 기존(preSeam)={baseline} "
                f"— success 점수 하락 (D-02 무회귀 위반)"
            )
    return failures


# ── (2) power-spin fault — leg_extension 변별 실증 ───────────────────────────


def check_powerspin_fault(report=None) -> list[str]:
    """power-spin fault: leg_extension 계열 감점 record >= 1 발화."""
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase29 sweep report absent for powerspin_fault)"]

    e = _entry(report, CRITERIA_MOTION, "fault")
    if e is None:
        return [f"[powerspin_fault] {CRITERIA_MOTION} fault member missing from report"]
    if e.get("status") != "done":
        return [
            f"[powerspin_fault] status={e.get('status')} != done "
            f"(errorCode={e.get('errorCode')}, exception={e.get('exception')})"
        ]
    leg_records = [
        r for r in _records_of(e)
        if isinstance(r.get("criterion"), str)
        and r["criterion"].startswith("leg_extension")
    ]
    if not leg_records:
        return [
            f"[powerspin_fault] leg_extension 계열 감점 record 0 "
            f"(activated={sorted({r.get('criterion') for r in _records_of(e)})}, "
            f"mdKeys={e.get('mdKeys')}) — 유일 criteria 동작의 변별 미실증"
        ]
    return []


# ── (3) fallback 4동작 fault — 미방출 + 점수 항등 ────────────────────────────


def check_fallback_identity(report=None) -> list[str]:
    """4동작 fault: breakdown 미방출 AND overallScore == preSeamOverall 항등.

    Pitfall 1: 이 4동작의 무감점은 정상(빈 criteria yaml → md 빈 dict → passthrough).
    FAIL 이 나와도 임계/criteria 조정 금지 — 정지·보고 (calibration-source-hard-gate).
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase29 sweep report absent for fallback_identity)"]

    failures: list[str] = []
    for motion in FALLBACK_MOTIONS:
        e = _entry(report, motion, "fault")
        if e is None:
            failures.append(f"[fallback] {motion} fault member missing from report")
            continue
        if e.get("status") != "done":
            failures.append(
                f"[fallback] {motion}: status={e.get('status')} != done "
                f"(errorCode={e.get('errorCode')}, exception={e.get('exception')})"
            )
            continue
        if e.get("deductionBreakdown") is not None:
            failures.append(
                f"[fallback] {motion}: deductionBreakdown 방출됨 "
                f"(mdKeys={e.get('mdKeys')}) — 빈 criteria 동작은 미방출이 정상 (D-03)"
            )
        score = e.get("overallScore")
        baseline = e.get("preSeamOverall")
        if baseline is None:
            failures.append(
                f"[fallback] {motion}: preSeamOverall 부재 — harness tee 배선 결함"
            )
        elif score != baseline:
            failures.append(
                f"[fallback] {motion}: overallScore={score} != 기존(preSeam)={baseline} "
                f"— passthrough 항등 위반 (byte-불변 회귀)"
            )
    return failures


# ── (4) cold/warm 결정론 ─────────────────────────────────────────────────────

_DET_FIELDS = ("status", "errorCode", "overallScore", "activatedCriteria")


def check_cold_warm_determinism(report=None, warm_report=None) -> list[str]:
    """cold vs warm 재실행: 전 키 status/errorCode/overallScore/records 동일.

    mode3 의 Gemini 는 recognizer 1회뿐 — TechniqueCache(영상 hash, Firestore 영속)
    hit 로 warm 은 동일 profile. RTMW_DETERMINISTIC=1 로 각도 동일 → 동일 verdict 기대.
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase29 sweep report absent for cold_warm_determinism)"]
    if warm_report is None:
        warm_report = _load_json(_REPORT_WARM_ARTIFACT)
    if not warm_report:
        return ["SKIPPED (phase29 warm rerun report absent for cold_warm_determinism)"]

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
        cb = json.dumps(_records_of(ce), sort_keys=True, ensure_ascii=False)
        wb = json.dumps(_records_of(we), sort_keys=True, ensure_ascii=False)
        if cb != wb:
            failures.append(
                f"[cold_warm] {key[0]}/{key[1]}: deduction records not identical "
                f"across cold/warm rerun"
            )
    return failures


# ── (5) breakdown 방출 키 — D-02 항등 ────────────────────────────────────────


def check_breakdown_identity(report=None) -> list[str]:
    """방출 키: overallScore == final == max(0, round(100 + Σ points)) (D-02 항등).

    산술/record 구조 검증은 phase24 check_traceability 를 import 재사용 — 항등식의
    100/0 은 tally 정의 상수이지 점수 타깃이 아니다.
    """
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase29 sweep report absent for breakdown_identity)"]

    failures: list[str] = []
    emitted: list[dict] = []
    for e in _results(report):
        bd = e.get("deductionBreakdown")
        if not isinstance(bd, dict):
            continue
        emitted.append(bd)
        score = e.get("overallScore")
        if score != bd.get("final"):
            failures.append(
                f"[identity] {e.get('motion_id')}/{e.get('label')}: "
                f"overallScore={score} != breakdown.final={bd.get('final')} "
                f"— D-02 in-place 교체 항등 위반"
            )
    if emitted:
        # phase24 게이트 헬퍼 재사용 — final == max(0, round(100 + Σ points)) +
        # record 필드 구조(ruleId/criterion/deviationSource/ipsfAnchor 등) 검증.
        p24 = _load_phase24_gates()
        failures.extend(p24.check_traceability(emitted))
    return failures


# ── (보조) mode3_held status — 'applied' 오염 0 ──────────────────────────────


def check_mode3_held_status(report=None) -> list[str]:
    """채점 완료 멤버 전원 visionVeto.status == 'mode3_held' (29-02 결정 — 'applied'
    재사용 금지: result.tsx vetoApplied 파생 의미 오염 방지)."""
    if report is None:
        report = _load_json(_REPORT_ARTIFACT)
    if not report:
        return ["SKIPPED (phase29 sweep report absent for mode3_held_status)"]

    failures: list[str] = []
    for e in _results(report):
        if e.get("status") != "done":
            continue  # 실패 멤버는 gate 1/3 소관
        vv = e.get("visionVeto")
        status = vv.get("status") if isinstance(vv, dict) else vv
        if status != "mode3_held":
            failures.append(
                f"[mode3_held] {e.get('motion_id')}/{e.get('label')}: "
                f"visionVeto.status={status} != 'mode3_held' — status 오염"
            )
    return failures


# ── compose ──────────────────────────────────────────────────────────────────


def _split_skips(results):
    skips = [r for r in results if r.startswith("SKIPPED")]
    fails = [r for r in results if not r.startswith("SKIPPED")]
    return fails, skips


def main() -> int:
    checks = (
        ("success_members", check_success_members()),
        ("powerspin_fault", check_powerspin_fault()),
        ("fallback_identity", check_fallback_identity()),
        ("cold_warm_determinism", check_cold_warm_determinism()),
        ("breakdown_identity", check_breakdown_identity()),
        ("mode3_held_status", check_mode3_held_status()),
    )

    failures: list[str] = []
    skipped: list[str] = []
    for _label, result in checks:
        fails, skips = _split_skips(result)
        failures.extend(fails)
        skipped.extend(skips)

    if failures:
        print("Phase 29 gates FAIL:")
        for f in failures:
            print("  -", f)
        for s in skipped:
            print("  ·", s)
        print(
            "FAIL 프로토콜: 임계/criteria/게이트 기대치 수정 금지 "
            "(calibration-source-hard-gate + Pitfall 1) — 정지·보고. "
            "Pod 서버 재기동 금지 (구코드 유지 = 무회귀)."
        )
        return 1

    print("Phase 29 gates PASS — D-02 게이트 5종 + mode3_held 보조 green.")
    for s in skipped:
        print("  ·", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
