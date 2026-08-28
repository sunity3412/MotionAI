"""Phase 23-03 Task 2 — non-zero exit assert gate (D-15 HIGH-2 + D-16 + D-17).

목적:
  Phase 20-04 가 가졌던 terminal-gate 강제력을 still-frame eval 에 부여한다. "machine-checkable
  JSON" 만으론 약하다 — 필드 누락 / `"true"` 문자열 / stale / row 실패 은닉 / precomputed 신뢰가
  통과해버린다. 본 스크립트는 결과 JSON + frozen manifest + lock 을 받아 **어떤 실패에서도
  non-zero exit** 하고 compact gate report 를 stdout 에 emit 한다. belle 의 게이트 판정은 raw
  JSON 이 아니라 이 report 를 읽는다.

검사 (전부 — 하나라도 실패 시 non-zero exit):
  (1) lock 정합 + run-commit ancestry (MED-2 + D-16 HIGH-1 + D-17 HIGH-1):
      manifest sha256==lock.manifest_sha256 / lock.dirty_worktree==false /
      lock_git_commit ∈ ancestor(result.run_git_commit) ∈ ancestor(HEAD) /
      result.worktree_dirty_at_run==false / result.manifest_lock_git_commit==lock /
      result.manifest_sha256==lock / expected_policy 일치.
  (2) multi-arm result shape (D-17 HIGH-2): cases[]{row_id, arms:{...}}; manifest row_id
      set == result cases[].row_id set; required_arms 정확히 1회; unknown arm 0.
  (3) 타입/스키마: bool/int/list 정확 타입 ("true" 문자열은 bool 아님 → fail).
  (4) 재계산 (precomputed 불신): coverage/completion/determinism/arm 캐시격리/D-14 게이트를
      cases/arms 에서 재계산. coverage·case-class·EVAL18 margin 은 locked gate_policy/
      regression_pairs 에서만 읽음 (D-17 MED-1/MED-2).
  (5) D-14 게이트를 실제 final score 에서 도출 (kip-up moderate≤75 severity/cap 구분 메시지).
  (5b) recall 을 canonical FaultKey 4-tuple 로 대조 (D-16 MED-1 + D-17 MED-3; unknown
       fault_kind 는 Pod 결과 보기 전 fail).
  (6) abstention/resource 분리: budget_stress 아닌 resource_limited/samplingComplete=false
      는 fail; abstention_allowed=false case 의 low_alignment_confidence 는 fail.
  (7) status 화이트리스트: allowed_veto_statuses 밖 / skipped_error / missing_local_video fail.
  (8) coverage: clean_evaluable_count < gate_policy.clean_coverage_min 면 fail.

★ stdlib only (D-16 HIGH-2): json / hashlib / subprocess(git) 만. YAML 파서 의존 금지
  (PyYAML 은 RunPod requirements 에 없어 Pod-terminal assert 가 import 단계에서 죽음).

★ 임계/프롬프트 주입 0 (D-06): manifest 의 expected-policy/gate_policy/regression_pairs 만
  읽고 known-answer 를 프롬프트에 넣지 않는다.

호출 (고정):
  cd backend && python3 research/spikes/assert_stillframe_veto_gate.py \\
    --results research/spikes/reports/eval_stillframe_veto_phase23.json \\
    --manifest research/spikes/eval_stillframe_veto_manifest.json \\
    [--lock research/spikes/eval_stillframe_veto_manifest.lock.json] [--head <commit>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ARM_PRODUCTION = "production_still"
ARM_BASELINE = "whole_video_baseline"

# locked enum — FaultKey import 불가 시 fallback 정규화용 (23-01 Task 2 와 동일 어휘).
_FAULT_PART_SCOPES = ("upper_body", "core", "lower_body", "line")
_FAULT_SIDES = ("left", "right", "unknown")
_FAULT_KEYPOINT_SETS = (
    "arm", "shoulder", "leg", "hip", "head_neck", "grip", "torso", "line",
)
_FAULT_KINDS = ("pole_gap_or_bent", "extension_or_alignment")

# unknown_mode 추가 (2026-08-28) — skipped_error 에서 갈라져 나온 사유다. 블록리스트에
# 안 넣으면 "mode 를 못 읽어 veto 가 안 돈 판"이 게이트를 조용히 통과한다.
_STATUS_BLOCKLIST = (
    "skipped_error",
    "unknown_mode",
    "missing_local_video",
    "missing_current_video",
)


class GateFail(Exception):
    """게이트 실패 — main 이 잡아 non-zero exit + report."""


# ─────────────────────────── FaultKey 정규화 (단일 owner) ───────────────────


def _normalize_faultkey(d: dict) -> tuple:
    """canonical FaultKey 4-tuple. 23-01 Task 2 owner import 시도, 불가 시 locked enum.

    unknown enum 값이면 GateFail (D-17 MED-3).
    """
    try:
        from sunity_shared.analysis.vision_veto import FaultKey  # type: ignore

        fk = FaultKey.from_dict(d)  # unknown → ValueError
        return (fk.part_scope, fk.side, fk.keypoint_set, fk.fault_kind)
    except ImportError:
        pass  # Pod-terminal fallback — 동일 locked enum 으로 정규화.
    except Exception as exc:  # noqa: BLE001 — FaultKey.from_dict 의 unknown enum raise.
        raise GateFail(f"unknown FaultKey enum: {d!r} ({exc})")

    part_scope = str((d or {}).get("part_scope", ""))
    side = str((d or {}).get("side", ""))
    keypoint_set = str((d or {}).get("keypoint_set", ""))
    fault_kind = str((d or {}).get("fault_kind", ""))
    if part_scope not in _FAULT_PART_SCOPES:
        raise GateFail(f"unknown part_scope: {part_scope!r}")
    if side not in _FAULT_SIDES:
        raise GateFail(f"unknown side: {side!r}")
    if keypoint_set not in _FAULT_KEYPOINT_SETS:
        raise GateFail(f"unknown keypoint_set: {keypoint_set!r}")
    if fault_kind not in _FAULT_KINDS:
        raise GateFail(f"unknown fault_kind: {fault_kind!r}")
    return (part_scope, side, keypoint_set, fault_kind)


# ─────────────────────────── git helpers ───────────────────────────


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    if not ancestor or not descendant:
        return False
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def _rev_parse_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


# ─────────────────────────── 타입 검사 helpers ───────────────────────────


def _require_bool(obj: dict, key: str, ctx: str) -> bool:
    v = obj.get(key)
    if not isinstance(v, bool):  # "true"(str)/None/int 거부 (D-15 — string-bool 차단).
        raise GateFail(f"{ctx}: {key} 가 bool 아님 (got {type(v).__name__}={v!r})")
    return v


def _require_int(obj: dict, key: str, ctx: str) -> int:
    v = obj.get(key)
    if isinstance(v, bool) or not isinstance(v, int):
        raise GateFail(f"{ctx}: {key} 가 int 아님 (got {type(v).__name__}={v!r})")
    return v


def _require_list(obj: dict, key: str, ctx: str) -> list:
    v = obj.get(key)
    if not isinstance(v, list):
        raise GateFail(f"{ctx}: {key} 가 list 아님 (got {type(v).__name__})")
    return v


# ─────────────────────────── 게이트 검사 ───────────────────────────


def check_lock_and_ancestry(result: dict, manifest: dict, lock: dict, manifest_path: str,
                            head: str, report: list) -> None:
    """(1) lock 정합 + run-commit ancestry (D-16 HIGH-1 + D-17 HIGH-1)."""
    cur_sha = hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()
    if cur_sha != lock.get("manifest_sha256"):
        raise GateFail(
            f"manifest sha256 != lock (cur={cur_sha[:12]} lock={str(lock.get('manifest_sha256'))[:12]})"
        )
    if lock.get("dirty_worktree") is True:
        raise GateFail("lock.dirty_worktree == true (freeze 가 dirty 에서 생성됨)")

    run_commit = result.get("run_git_commit")
    if not isinstance(run_commit, str) or not run_commit:
        raise GateFail("result.run_git_commit 부재/비문자열")

    lock_commit = lock.get("lock_git_commit")
    # (a) lock_git_commit ∈ ancestor(result.run_git_commit) — post-result freeze 차단.
    if not _is_ancestor(lock_commit, run_commit):
        raise GateFail(
            f"lock_git_commit({str(lock_commit)[:12]}) ∉ ancestor(result.run_git_commit"
            f"={run_commit[:12]}) — eval 이 freeze 전에 돈 흔적 (post-result freeze)"
        )
    # (b) result.run_git_commit ∈ ancestor(HEAD).
    if not _is_ancestor(run_commit, head):
        raise GateFail(
            f"result.run_git_commit({run_commit[:12]}) ∉ ancestor(HEAD={head[:12]})"
        )
    # (c) worktree_dirty_at_run == false.
    if _require_bool(result, "worktree_dirty_at_run", "result") is not False:
        raise GateFail("result.worktree_dirty_at_run != false")
    # (d) manifest_lock_git_commit == lock.lock_git_commit.
    if result.get("manifest_lock_git_commit") != lock_commit:
        raise GateFail("result.manifest_lock_git_commit != lock.lock_git_commit")
    # (e) manifest_sha256 == lock.manifest_sha256.
    if result.get("manifest_sha256") != lock.get("manifest_sha256"):
        raise GateFail("result.manifest_sha256 != lock.manifest_sha256")

    # expected_policy 일치 (lock snapshot vs manifest 현재).
    rows_by_id = {r["row_id"]: r for r in (manifest.get("rows") or [])}
    for row_id, snap in (lock.get("expected_policy") or {}).items():
        row = rows_by_id.get(row_id)
        if row is None:
            raise GateFail(f"lock expected_policy row {row_id} 가 manifest 에 없음")
        for field, snap_val in snap.items():
            if row.get(field) != snap_val:
                raise GateFail(
                    f"row {row_id} field {field} 가 lock snapshot 과 다름 "
                    f"(manifest={row.get(field)!r} lock={snap_val!r})"
                )
    report.append("PASS  lock+ancestry: sha/dirty/lock∈run∈HEAD/expected_policy")


def check_multi_arm_shape(result: dict, manifest: dict, report: list) -> dict:
    """(2) multi-arm result shape (D-17 HIGH-2). 반환: cases_by_id."""
    cases = result.get("cases")
    if not isinstance(cases, list):
        raise GateFail("result.cases 가 list 아님 (multi-arm shape 위반)")
    cases_by_id: dict[str, dict] = {}
    for c in cases:
        rid = c.get("row_id")
        if not isinstance(rid, str):
            raise GateFail("case.row_id 비문자열")
        if not isinstance(c.get("arms"), dict):
            raise GateFail(f"case {rid}.arms 가 dict 아님 (평면 row 의심)")
        cases_by_id[rid] = c

    manifest_ids = {r["row_id"] for r in (manifest.get("rows") or [])}
    result_ids = set(cases_by_id.keys())
    if manifest_ids != result_ids:
        missing = manifest_ids - result_ids
        extra = result_ids - manifest_ids
        raise GateFail(
            f"row_id set 불일치 (manifest 에만={sorted(missing)} result 에만={sorted(extra)})"
        )

    rows_by_id = {r["row_id"]: r for r in (manifest.get("rows") or [])}
    for rid, case in cases_by_id.items():
        row = rows_by_id[rid]
        required = row.get("required_arms") or [ARM_PRODUCTION, ARM_BASELINE]
        optional = row.get("optional_arms") or []
        allowed_arms = set(required) | set(optional)
        arms = case["arms"]
        for arm in required:
            if arm not in arms:
                raise GateFail(f"case {rid}: required arm '{arm}' 결측")
        for arm in arms:
            if arm not in allowed_arms:
                raise GateFail(f"case {rid}: unknown arm '{arm}' (required+optional 밖)")
    report.append("PASS  multi-arm shape: cases[].arms, required 1회, unknown arm 0")
    return cases_by_id


def check_arm_fields_and_status(cases_by_id: dict, manifest: dict, report: list) -> None:
    """(3) 타입/스키마 + (7) status 화이트리스트 (arms.production_still)."""
    rows_by_id = {r["row_id"]: r for r in (manifest.get("rows") or [])}
    for rid, case in cases_by_id.items():
        row = rows_by_id[rid]
        prod = case["arms"].get(ARM_PRODUCTION)
        if not isinstance(prod, dict):
            raise GateFail(f"case {rid}: production_still arm 이 dict 아님")
        # arm-level 필수 타입.
        _require_bool(prod, "cacheHit", f"{rid}.production_still")
        _require_bool(prod, "samplingComplete", f"{rid}.production_still")
        _require_int(prod, "call_count", f"{rid}.production_still")
        _require_int(prod, "upload_count", f"{rid}.production_still")
        _require_int(prod, "duration_ms", f"{rid}.production_still")
        _require_list(prod, "recall_set", f"{rid}.production_still")
        status = prod.get("alignment_status")
        if not isinstance(status, str):
            raise GateFail(f"case {rid}: alignment_status 비문자열")
        # (7) status 화이트리스트.
        if status in _STATUS_BLOCKLIST:
            raise GateFail(f"case {rid}: blocked status '{status}'")
        allowed = set(row.get("allowed_veto_statuses") or [])
        if status not in allowed:
            raise GateFail(
                f"case {rid}: status '{status}' 가 allowed_veto_statuses {sorted(allowed)} 밖"
            )
    report.append("PASS  arm 타입/스키마 + status 화이트리스트")


def check_abstention_resource(cases_by_id: dict, manifest: dict, report: list) -> None:
    """(6) abstention/resource 분리 (D-12 HIGH-2)."""
    rows_by_id = {r["row_id"]: r for r in (manifest.get("rows") or [])}
    for rid, case in cases_by_id.items():
        row = rows_by_id[rid]
        prod = case["arms"][ARM_PRODUCTION]
        status = prod.get("alignment_status")
        budget_stress = bool(row.get("budget_stress", False))
        sampling_complete = prod.get("samplingComplete")
        # resource_limited / samplingComplete=false 가 budget_stress 아니면 fail (완료실패).
        if not budget_stress and (
            status == "resource_limited" or sampling_complete is False
        ):
            raise GateFail(
                f"case {rid}: non-budget-stress 인데 resource_limited/samplingComplete=false "
                "(완료실패 — abstention 과 그룹화 금지)"
            )
        # abstention_allowed=false 인데 low_alignment_confidence 면 fail (alignment_unverifiable 만 면제).
        if (
            status == "low_alignment_confidence"
            and not bool(row.get("abstention_allowed", False))
            and not bool(row.get("alignment_unverifiable", False))
        ):
            raise GateFail(
                f"case {rid}: abstention_allowed=false 인데 low_alignment_confidence"
            )
    report.append("PASS  abstention/resource 분리 (완료실패 ≠ abstention)")


def check_coverage_completion(result: dict, cases_by_id: dict, manifest: dict,
                              report: list) -> None:
    """(4)+(8) coverage/completion 재계산 (locked gate_policy, precomputed 불신)."""
    gate_policy = manifest.get("gate_policy") or {}
    clean_classes = set(gate_policy.get("clean_gate_case_classes") or [])
    abstention_classes = set(gate_policy.get("alignment_abstention_case_classes") or [])
    coverage_min = int(gate_policy.get("clean_coverage_min", 0))
    rows_by_id = {r["row_id"]: r for r in (manifest.get("rows") or [])}

    applied = true_negative = 0
    completion_violation = False
    for rid, case in cases_by_id.items():
        row = rows_by_id[rid]
        case_class = row.get("case_class")
        budget_stress = bool(row.get("budget_stress", False))
        prod = case["arms"][ARM_PRODUCTION]
        status = prod.get("alignment_status")
        sc = prod.get("samplingComplete")
        if not budget_stress and (status == "resource_limited" or sc is False):
            completion_violation = True
        if case_class in clean_classes or case_class in abstention_classes:
            if status == "applied" and sc is not False:
                applied += 1
            elif status in ("none", "not_applicable"):
                true_negative += 1

    evaluable = applied + true_negative
    completion_pass = not completion_violation
    coverage_pass = evaluable >= coverage_min

    # precomputed 와 일치 확인 (불신 — 재계산 우선).
    if result.get("coverage_pass") != coverage_pass:
        raise GateFail(
            f"coverage_pass precomputed({result.get('coverage_pass')}) != "
            f"재계산({coverage_pass})"
        )
    if result.get("completion_pass") != completion_pass:
        raise GateFail(
            f"completion_pass precomputed({result.get('completion_pass')}) != "
            f"재계산({completion_pass})"
        )
    if not completion_pass:
        raise GateFail("completion_pass=false (budget_stress 아닌 케이스 resource_limited/timeout)")
    if not coverage_pass:
        raise GateFail(
            f"coverage 미달: evaluable={evaluable} < clean_coverage_min={coverage_min} "
            "(전부 abstain 의심)"
        )
    # false positive (evaluable 분모) 0.
    if applied != 0:
        raise GateFail(f"false_positive_count={applied} (evaluable clean 에서 fault 잡힘)")
    report.append(
        f"PASS  coverage={evaluable}>={coverage_min} completion_pass FP=0 (재계산)"
    )


def check_recall(cases_by_id: dict, manifest: dict, report: list) -> None:
    """(5b) recall 을 canonical FaultKey 4-tuple 로 대조 (D-16 MED-1 + D-17 MED-3).

    known-fault row 의 arms.production_still.recall_set ⊇ expected_recall_keys.
    """
    rows_by_id = {r["row_id"]: r for r in (manifest.get("rows") or [])}
    for rid, case in cases_by_id.items():
        row = rows_by_id[rid]
        expected = row.get("expected_recall_keys") or []
        if not expected:
            continue
        expected_tuples = {_normalize_faultkey(k) for k in expected}
        prod = case["arms"][ARM_PRODUCTION]
        recall_tuples = {_normalize_faultkey(k) for k in (prod.get("recall_set") or [])}
        missing = expected_tuples - recall_tuples
        if missing:
            raise GateFail(
                f"case {rid}: recall_set 이 expected_recall_keys 를 누락 "
                f"(missing={sorted(missing)})"
            )
    report.append("PASS  recall: canonical FaultKey 4-tuple ⊇ expected")


def check_d14_gates(result: dict, cases_by_id: dict, manifest: dict, report: list) -> None:
    """(5) D-14 흡수 게이트를 실제 final score 에서 도출 (severity/cap 구분 메시지)."""
    rows_by_id = {r["row_id"]: r for r in (manifest.get("rows") or [])}

    for rid, case in cases_by_id.items():
        row = rows_by_id[rid]
        prod = case["arms"][ARM_PRODUCTION]
        case_class = row.get("case_class")

        # elite_clean → final score 95~100 (V-3).
        if case_class == "elite_clean":
            score = prod.get("final_score")
            if not isinstance(score, int) or isinstance(score, bool):
                raise GateFail(f"case {rid}: elite final_score int 아님")
            if not (95 <= score <= 100):
                raise GateFail(f"case {rid}: elite final_score={score} 가 95~100 밖 (V-3)")

        # kip-up known_fault → severity==moderate AND score<=75 (V-1, D-14 HIGH-3).
        if row.get("expected_severity") == "moderate" and row.get("max_score") == 75:
            severity = prod.get("severity")
            score = prod.get("final_score")
            if severity != "moderate":
                # severity-misclassification — ≤50/major 억지 격상 금지.
                raise GateFail(
                    f"case {rid}: severity-misclassification — severity={severity!r} != "
                    "moderate (kip-up 은 moderate 실행결함, ≤50/major 강등 금지)"
                )
            if not isinstance(score, int) or isinstance(score, bool) or score > 75:
                raise GateFail(
                    f"case {rid}: cap-application 실패 — severity=moderate 이나 "
                    f"final_score={score!r} > 75 (cap 미적용)"
                )

    # EVAL18 4쌍 — locked regression_pairs 에서만 margin 계산 (D-17 MED-1).
    pairs = manifest.get("regression_pairs") or []
    regressions = 0
    for pair in pairs:
        fault = cases_by_id.get(pair["fault_row_id"])
        success = cases_by_id.get(pair["success_row_id"])
        min_margin = int(pair.get("min_margin", 1))
        if fault is None or success is None:
            regressions += 1
            continue
        fs = fault["arms"][ARM_PRODUCTION].get("final_score")
        ss = success["arms"][ARM_PRODUCTION].get("final_score")
        if not isinstance(fs, int) or not isinstance(ss, int) or isinstance(fs, bool) or isinstance(ss, bool):
            raise GateFail(f"pair {pair.get('pair_id')}: final_score int 아님")
        if (ss - fs) < min_margin:
            regressions += 1
    if regressions != 0:
        raise GateFail(
            f"eval18_discrimination_regression_count={regressions} != 0 (변별 퇴행)"
        )
    # precomputed 와도 일치 (재계산 우선, 불신).
    if result.get("eval18_discrimination_regression_count") != 0:
        raise GateFail(
            f"eval18 precomputed={result.get('eval18_discrimination_regression_count')} != 0"
        )
    report.append("PASS  D-14: elite 95~100 / kip-up moderate≤75 / EVAL18 4쌍 퇴행 0")


def check_determinism_cache_isolation(cases_by_id: dict, report: list) -> None:
    """(4) determinism + arm 캐시 격리 재계산 — 같은 case 내 cross-arm cacheKey 상이."""
    for rid, case in cases_by_id.items():
        arms = case["arms"]
        prod = arms.get(ARM_PRODUCTION)
        base = arms.get(ARM_BASELINE)
        if prod is not None and base is not None:
            pk = prod.get("cacheKey")
            bk = base.get("cacheKey")
            # 둘 다 None 이 아니고 같으면 cross-arm 캐시 누수.
            if pk is not None and bk is not None and pk == bk:
                raise GateFail(
                    f"case {rid}: production_still.cacheKey == whole_video_baseline.cacheKey "
                    "(arm 캐시 격리 위반)"
                )
    report.append("PASS  arm 캐시 격리 (cross-arm cacheKey 상이)")


# ─────────────────────────── main ───────────────────────────


def run_gate(results_path: str, manifest_path: str, lock_path: str,
             head: str | None = None) -> list:
    """모든 게이트 실행. 실패 시 GateFail raise. 반환: report lines."""
    result = json.loads(Path(results_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not os.path.isfile(lock_path):
        raise GateFail(f"lock.json 부재: {lock_path}")
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))

    # manifest expected_recall_keys 를 먼저 검증 — unknown fault_kind 면 Pod 결과 보기 전 fail.
    for row in manifest.get("rows") or []:
        for key_obj in row.get("expected_recall_keys") or []:
            _normalize_faultkey(key_obj)  # unknown enum → GateFail.

    head_commit = head or _rev_parse_head()
    report: list = []
    check_lock_and_ancestry(result, manifest, lock, manifest_path, head_commit, report)
    cases_by_id = check_multi_arm_shape(result, manifest, report)
    check_arm_fields_and_status(cases_by_id, manifest, report)
    check_abstention_resource(cases_by_id, manifest, report)
    check_coverage_completion(result, cases_by_id, manifest, report)
    check_recall(cases_by_id, manifest, report)
    check_d14_gates(result, cases_by_id, manifest, report)
    check_determinism_cache_isolation(cases_by_id, report)
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Phase 23-03 non-zero exit assert gate (stdlib only)"
    )
    p.add_argument("--results", required=True, help="eval 결과 JSON")
    p.add_argument("--manifest", required=True, help="frozen manifest.json")
    p.add_argument("--lock", default=None, help="lock.json (기본: manifest .lock.json)")
    p.add_argument("--head", default=None, help="ancestry 검증 기준 HEAD (테스트용 override)")
    args = p.parse_args(argv)

    lock_path = args.lock or args.manifest.replace(".json", ".lock.json")
    try:
        report = run_gate(args.results, args.manifest, lock_path, args.head)
    except GateFail as exc:
        print(f"FAIL  {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — 어떤 예외도 non-zero (게이트는 fail-closed).
        print(f"FAIL  unexpected: {type(exc).__name__}: {exc}")
        return 1
    for line in report:
        print(line)
    print("GATE PASS — 전 게이트 통과 (assert report).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
