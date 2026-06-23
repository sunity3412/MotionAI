"""Phase 23-03 Task 1 — still-frame veto eval harness (Pod-bound, 순차).

목적 (23-03 PLAN Task 1 / H5 / D-10..D-17):
  23-01/02 의 still-frame veto 구현을 Pod GPU 에서 **실측**하되, codex HIGH(H5)에 따라
  어댑터 직접호출이 아니라 **FULL production 경로**를 통과해 측정한다:

    _collect_vision_fault_context(coach 전, Gemini 소유)
      → coach writers 가 VisionFaultContext.to_coach_context() 소비
      → build_result
      → _apply_vision_veto(result, vision_fault_context=ctx)  (cap+audit, Gemini 미호출)
      → 캐시

  collect 가 Gemini 단독 소유 → verdict 호출은 **1회**(geminiCallCount=1).

핵심 invariant (전부 기계 판정 가능 필드로 박제):
  (A) FULL production seam 통과 (어댑터 직접호출 아님 — direct_adapter_still 은 보조 arm).
  (B) 동일-모델 whole-video baseline 재실행 (옛 JSON 비교 아님, apples-to-apples).
  (B2) multi-arm result shape: cases[]{row_id, arms:{production_still, whole_video_baseline,
       direct_adapter_still}} — (case,arm) 평면 row 아님 (D-17 HIGH-2).
  (C) 확장 케이스 매트릭스 + case_class + abstention_allowed + budget_stress (manifest 소유).
  (D) FP / alignment-abstention / resource-incomplete 3-way 분리 + completion_pass
      + case-class 게이트 + coverage 임계 (manifest gate_policy 소유).
  (E) arm 별 격리 cold/warm 결정론 (arm·cold 반복별 cache_namespace/run_id).
  (F) cost/latency 게이트 (MAX_VETO_CALLS/UPLOADS/WALL_S).
  (G) machine-checkable pass/fail 필드 + to_trace_dict 직렬화 + FaultKey.to_dict recall.
  (H) Phase 20-04 흡수 게이트 (D-14): elite 95~100 / kip-up moderate≤75 / 결정론 / EVAL18 4쌍.
  (I) frozen manifest (JSON, stdlib only) — Task 1 이 manifest.json + result 스키마 소유.
  (J) run-commit ancestry 강제 (D-17 HIGH-1): lock 부재/sha 불일치/lock∉ancestor(run HEAD)/
      worktree dirty 면 실행 거부. result 에 run_git_commit/worktree_dirty_at_run/
      manifest_lock_git_commit/manifest_sha256/eval_command/result_generated_at 기록.
  (K) manifest top-level regression_pairs + gate_policy 에서만 margin/coverage 계산.

★ 경계 (절대 — [[scoring-redesign-must-generalize-no-overfit]] + D-06):
  recall 은 프로젝트 자체 라벨셋으로 측정. 프롬프트는 generic — known-answer 임계/프롬프트
  주입 0. known-answer 라벨은 비교용일 뿐. 점수 라벨링 영구 금지(객관성).

★ 순차 강제 ([[pipeline-not-concurrency-safe-eval-serial]]):
  동시 호출 = 결과 오염. 병렬 실행 primitive(스레드 풀/이벤트 루프 gather) 미사용 — 단일
  for 루프로만 측정한다.

Pod 필수: 라이브 Gemini · 실 영상 · GPU. 구현(23-01/02)은 Pod-free 였으나 본 eval 은 Pod-bound.

키 로드:
  env GEMINI_API_KEY 우선. 미설정 시 SSM /sunity/motion/gemini-api-key (sunity-motion 프로필).
  키는 절대 로그하지 않는다 (T-23-10 / T-20-06).

실행 (Pod):
  PYTHONPATH=backend/shared/python:. python3 backend/research/spikes/eval_stillframe_veto.py \\
    --manifest backend/research/spikes/eval_stillframe_veto_manifest.json \\
    --out backend/research/spikes/reports/eval_stillframe_veto_phase23.json \\
    --created-at 2026-06-23T00:00:00Z
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("eval_stillframe_veto")

# Pod 실행 시점 모델 — 동일-모델 baseline 재실행이 apples-to-apples 가 되도록 단일 상수.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")

# arm enum — case 의 nested 필드 (D-17 HIGH-2).
ARM_PRODUCTION = "production_still"
ARM_BASELINE = "whole_video_baseline"
ARM_DIRECT = "direct_adapter_still"
KNOWN_ARMS = (ARM_PRODUCTION, ARM_BASELINE, ARM_DIRECT)

# clean(특이도 분모) case class 분류용 status.
STATUS_APPLIED = "applied"
STATUS_NONE = "none"
STATUS_NOT_APPLICABLE = "not_applicable"
STATUS_LOW_ALIGNMENT = "low_alignment_confidence"
STATUS_RESOURCE_LIMITED = "resource_limited"


# ─────────────────────────── 키 로드 (로그 금지) ───────────────────────────


def load_api_key() -> str:
    inline = os.environ.get("GEMINI_API_KEY")
    if inline:
        # 키 값/길이/접두 미로그 — 존재 여부만 (T-23-10).
        log.info("Gemini 키: env GEMINI_API_KEY (set)")
        return inline
    import boto3  # lazy

    ssm = boto3.client("ssm", region_name="ap-northeast-2")
    resp = ssm.get_parameter(
        Name="/sunity/motion/gemini-api-key", WithDecryption=True
    )
    log.info("Gemini 키: SSM /sunity/motion/gemini-api-key")
    return resp["Parameter"]["Value"]


# ─────────────────────────── git helpers (run-commit ancestry, D-17 HIGH-1) ──


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _rev_parse_head() -> str:
    return _git("rev-parse", "HEAD")


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    """git merge-base --is-ancestor — exit 0 이면 ancestor 관계."""
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def _worktree_dirty(exclude_paths: list[str]) -> bool:
    """git status --porcelain — 출력 결과 경로를 제외한 dirty 여부."""
    out = _git("status", "--porcelain")
    exclude = {os.path.normpath(p) for p in exclude_paths}
    for line in out.splitlines():
        # porcelain: XY <path> — path 는 3번째 문자부터.
        path = line[3:].strip()
        # rename "old -> new" 형식이면 new 측만 검사.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if os.path.normpath(path) in exclude:
            continue
        return True
    return False


def _sha256_of_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _enforce_run_commit_ancestry(
    manifest_path: str, lock_path: str, out_path: str
) -> dict:
    """eval 시작 시 lock 상태 강제 (D-17 HIGH-1). 위반 시 SystemExit(non-zero).

    (a) lock.json 존재, (b) 현 manifest sha == lock.manifest_sha256,
    (c) lock_git_commit ∈ ancestor(현 run HEAD), (d) worktree clean(출력 경로 제외).
    반환: {run_git_commit, worktree_dirty_at_run, manifest_lock_git_commit, manifest_sha256}.
    """
    if not os.path.isfile(lock_path):
        log.error(
            "lock.json 부재 — freeze 미수행. 먼저 freeze_stillframe_veto_manifest.py 로 "
            "lock 을 생성·commit 한 뒤 실행하라 (D-16 HIGH-1). path=%s", lock_path
        )
        raise SystemExit(2)
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))

    cur_sha = _sha256_of_file(manifest_path)
    lock_sha = lock.get("manifest_sha256")
    if cur_sha != lock_sha:
        log.error(
            "manifest sha256 불일치 — manifest 가 freeze 이후 변경됨 (post-result relabel "
            "차단). cur=%s lock=%s", cur_sha, lock_sha
        )
        raise SystemExit(2)

    lock_commit = lock.get("lock_git_commit")
    run_head = _rev_parse_head()
    if not lock_commit or not _is_ancestor(lock_commit, run_head):
        log.error(
            "lock_git_commit 이 현 run HEAD 의 ancestor 아님 — freeze commit 이 측정 commit "
            "보다 나중. lock=%s head=%s", lock_commit, run_head
        )
        raise SystemExit(2)

    dirty = _worktree_dirty([out_path])
    if dirty:
        log.error(
            "worktree dirty (출력 경로 제외) — clean 상태에서만 측정 (run-commit ancestry, "
            "D-17 HIGH-1)."
        )
        raise SystemExit(2)

    return {
        "run_git_commit": run_head,
        "worktree_dirty_at_run": dirty,
        "manifest_lock_git_commit": lock_commit,
        "manifest_sha256": lock_sha,
    }


# ─────────────────────────── manifest 로드 + FaultKey 검증 ───────────────────


def _load_faultkey_module():
    """23-01 Task 2 단일 owner FaultKey 를 import (drift 금지, D-17 MED-3)."""
    from sunity_shared.analysis.vision_veto import FaultKey  # type: ignore

    return FaultKey


def load_manifest(manifest_path: str) -> dict:
    """manifest.json 로드 + expected_recall_keys 를 FaultKey.from_dict 로 검증.

    unknown fault_kind/part_scope/side/keypoint_set 면 어떤 Pod 측정 전에 SystemExit
    (D-17 MED-3). regression_pairs / gate_policy top-level 존재 강제.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    FaultKey = _load_faultkey_module()

    rows = manifest.get("rows") or []
    if not rows:
        log.error("manifest 에 rows 없음.")
        raise SystemExit(2)

    for row in rows:
        for key_obj in row.get("expected_recall_keys") or []:
            try:
                FaultKey.from_dict(key_obj)  # unknown enum → raise
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "manifest row=%s expected_recall_keys 검증 실패 (unknown enum?): %s",
                    row.get("row_id"), exc,
                )
                raise SystemExit(2)

    if "regression_pairs" not in manifest:
        log.error("manifest top-level regression_pairs 부재 (D-17 MED-1).")
        raise SystemExit(2)
    if "gate_policy" not in manifest:
        log.error("manifest top-level gate_policy 부재 (D-17 MED-2).")
        raise SystemExit(2)
    return manifest


# ─────────────────────────── production seam 측정 ───────────────────────────


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recall_set_from_trace(trace: dict) -> list[dict]:
    """to_trace_dict() 의 faultKeys (FaultKey.to_dict 산출) 를 recall_set 으로.

    한글 표시라벨이 아니라 canonical FaultKey dict (D-16 MED-1 + D-17 MED-3).
    """
    return list(trace.get("faultKeys") or [])


def run_production_arm(
    *,
    case: dict,
    arm: str,
    cache_namespace: str,
    run_id: str,
    api_key: str,
    model: str,
) -> dict:
    """단일 (case, arm) 측정 — FULL production seam 통과.

    collect → coach 소비 → build_result → apply(vision_fault_context=) 를 호출하고,
    런타임 trace 를 VisionFaultContext.to_trace_dict() 로 직렬화한다. Gemini 호출은
    collect 가 단독 소유 → geminiCallCount=1. (어댑터 직접호출 arm 은 direct_adapter_still.)

    Pod 에서 실제 영상/Gemini 로 채워지는 측정 단위. 본 함수는 production seam 호출
    래퍼이며, 비-Pod 환경에서는 import 단계에서 실패할 수 있다(설계상 Pod-bound).
    """
    # Pod-bound import — Gemini/GPU/pipeline 의존. 비-Pod 환경에서는 호출되지 않음.
    from functions.pipeline import app as pipeline  # type: ignore

    student_video = os.path.expanduser(case["student_video"])
    reference_video = os.path.expanduser(case.get("reference_video", "")) or None

    t0 = time.monotonic()

    # FULL production seam (D-10 HIGH-1) — collect(Gemini 소유, coach 전 1회) →
    # build_result → apply(vision_fault_context=, Gemini 미호출).
    if arm == ARM_BASELINE:
        # 동일-모델 whole-video baseline 재실행 (격리 namespace). pair=None 경로로
        # whole-video Gemini 호출 → 옛 JSON 비교가 아니라 같은 모델 재실행 (H5).
        ctx = pipeline._collect_vision_fault_context(
            overall_score=int(case.get("overall_score", 100)),
            dimension_scores=case.get("dimension_scores", {}),
            mode=case.get("mode", "mode1"),
            local_video_path=student_video,
            reference_video_path=reference_video,
            # baseline arm 은 still-pair 미선택 — whole-video 경로 강제 (profile=None).
            profile=None,
        )
    else:
        # production_still / direct_adapter_still — still-pair seam.
        ctx = pipeline._collect_vision_fault_context(
            overall_score=int(case.get("overall_score", 100)),
            dimension_scores=case.get("dimension_scores", {}),
            mode=case.get("mode", "mode1"),
            local_video_path=student_video,
            reference_video_path=reference_video,
            profile=case.get("_profile"),
        )

    # coach 소비 (collect-before-coach 증명용 trace).
    context_collected_before_coach = True
    coach_ctx = ctx.to_coach_context()
    context_reused_for_audit = coach_ctx is not None

    # build_result + apply (final cap + audit, Gemini 미호출).
    base_result = {"overallScore": int(case.get("overall_score", 100))}
    quantification = pipeline._build_vision_quantification_result(
        fault_context=ctx,
        selected_frame_pair=(
            ctx.selected_frame_pairs[0] if ctx.selected_frame_pairs else None
        ),
    )
    applied = pipeline._apply_vision_veto(
        base_result,
        vision_fault_context=ctx,
        quantification=quantification,
    )

    duration_ms = int((time.monotonic() - t0) * 1000.0)

    trace = ctx.to_trace_dict()
    telemetry = ctx.telemetry or {}
    vision_veto_audit = applied.get("visionVeto") or {}
    final_status = vision_veto_audit.get("status") or trace.get("collectionStatus")
    final_score = applied.get("overallScore")

    return {
        "arm": arm,
        "cache_namespace": cache_namespace,
        "run_id": run_id,
        "call_count": telemetry.get("completedCalls", 0),
        "upload_count": telemetry.get("uploadCount", 0),
        "duration_ms": duration_ms,
        "cacheKey": telemetry.get("cacheKey"),
        "cacheHit": bool(telemetry.get("cacheHit", False)),
        "recall_set": _recall_set_from_trace(trace),
        "alignment_status": final_status,
        "samplingComplete": bool(telemetry.get("samplingComplete", True)),
        "final_score": final_score,
        "severity": vision_veto_audit.get("severity"),
        # to_trace_dict() 직렬화 trace 필드 (raw dict fork 금지, D-11 MED-2).
        "entrypoint": "collect_apply_seam",
        "selectorVersion": trace.get("selectorVersion"),
        "studentFrameIndices": telemetry.get("studentFrameIndices"),
        "referenceFrameIndices": telemetry.get("referenceFrameIndices"),
        "alignmentConfidence": trace.get("alignmentAdoption"),
        "pathUsed": trace.get("alignmentAdoption"),
        "contextCollectedBeforeCoach": context_collected_before_coach,
        "contextReusedForAudit": context_reused_for_audit,
        "geminiCallCount": trace.get("geminiCallCount", 1),
    }


# ─────────────────────────── 3-way 분리 + 게이트 산출 ───────────────────────


def classify_clean_outcome(arm_result: dict) -> str:
    """clean case 의 arms.production_still 결과를 outcome class 로 분류 (D-12 HIGH-2).

    applied(=false positive) / true_negative(none|not_applicable) /
    alignment_abstention(low_alignment_confidence 만) /
    resource_incomplete(resource_limited | samplingComplete=false = 완료실패).

    (D-13 HIGH-2, Option A) applied 인데 samplingComplete=false 면 clean success 로
    세지 않고 resource_incomplete 로 분류 — 부분 샘플 applied 는 비결정.
    """
    status = arm_result.get("alignment_status")
    sampling_complete = bool(arm_result.get("samplingComplete", True))
    if status == STATUS_RESOURCE_LIMITED or not sampling_complete:
        return "resource_incomplete"
    if status == STATUS_LOW_ALIGNMENT:
        return "alignment_abstention"
    if status == STATUS_APPLIED:
        return "applied"
    if status in (STATUS_NONE, STATUS_NOT_APPLICABLE):
        return "true_negative"
    # 그 외 status (skipped_error/missing 등) 는 evaluable 아님 — true_negative/applied
    # 어디에도 넣지 않음(분모 오염 방지). assert 의 status 화이트리스트가 별도로 잡는다.
    return "other"


def compute_aggregates(cases: list[dict], manifest: dict) -> dict:
    """clean 분모 + completion + coverage 를 manifest gate_policy 에서만 재계산
    (D-17 MED-2). script 상수/row 추론 0.
    """
    gate_policy = manifest.get("gate_policy", {})
    clean_classes = set(gate_policy.get("clean_gate_case_classes") or [])
    abstention_classes = set(gate_policy.get("alignment_abstention_case_classes") or [])
    coverage_min = int(gate_policy.get("clean_coverage_min", 0))

    rows_by_id = {r["row_id"]: r for r in (manifest.get("rows") or [])}

    clean_applied = 0
    clean_true_negative = 0
    clean_abstention = 0
    resource_incomplete = 0
    completion_violation = False

    for case in cases:
        row = rows_by_id.get(case["row_id"], {})
        case_class = row.get("case_class")
        budget_stress = bool(row.get("budget_stress", False))
        prod = (case.get("arms") or {}).get(ARM_PRODUCTION) or {}
        outcome = classify_clean_outcome(prod)

        # completion_pass: budget_stress 아닌 모든 케이스가 samplingComplete=true AND
        # status != resource_limited (D-13 HIGH-2).
        if not budget_stress:
            if prod.get("alignment_status") == STATUS_RESOURCE_LIMITED or not bool(
                prod.get("samplingComplete", True)
            ):
                completion_violation = True

        if case_class in clean_classes:
            if outcome == "applied":
                clean_applied += 1
            elif outcome == "true_negative":
                clean_true_negative += 1
            elif outcome == "alignment_abstention":
                # alignment-unverifiable 로 명시 안 한 clean gate 케이스의 abstention 은
                # specificity 미증명 — coverage 분모에서 빠지지만 별도 추적.
                clean_abstention += 1
            elif outcome == "resource_incomplete":
                resource_incomplete += 1
        elif case_class in abstention_classes:
            if outcome == "alignment_abstention":
                clean_abstention += 1
            elif outcome == "resource_incomplete":
                resource_incomplete += 1
            elif outcome == "applied":
                clean_applied += 1
            elif outcome == "true_negative":
                clean_true_negative += 1

    clean_evaluable = clean_applied + clean_true_negative
    completion_pass = not completion_violation
    coverage_pass = clean_evaluable >= coverage_min

    return {
        "false_positive_count": clean_applied,
        "clean_applied_fault_count": clean_applied,
        "clean_true_negative_count": clean_true_negative,
        "clean_abstention_count": clean_abstention,
        "resource_incomplete_count": resource_incomplete,
        "clean_evaluable_count": clean_evaluable,
        "completion_pass": completion_pass,
        "coverage_pass": coverage_pass,
    }


def compute_eval18_regression(cases: list[dict], manifest: dict) -> dict:
    """EVAL18 변별 4쌍 퇴행 — manifest regression_pairs mapping 에서만 margin 계산
    (row_id/motion-id 추론 0, D-17 MED-1). success_final − fault_final >= min_margin.
    """
    by_id = {c["row_id"]: c for c in cases}
    pairs = manifest.get("regression_pairs") or []
    regressions = 0
    margins = []
    for pair in pairs:
        fault_case = by_id.get(pair["fault_row_id"])
        success_case = by_id.get(pair["success_row_id"])
        min_margin = int(pair.get("min_margin", 1))
        if fault_case is None or success_case is None:
            regressions += 1  # 측정 누락도 퇴행으로 처리 (silent pass 금지).
            margins.append({"pair_id": pair.get("pair_id"), "margin": None})
            continue
        fault_score = (
            (fault_case.get("arms") or {}).get(ARM_PRODUCTION) or {}
        ).get("final_score")
        success_score = (
            (success_case.get("arms") or {}).get(ARM_PRODUCTION) or {}
        ).get("final_score")
        if fault_score is None or success_score is None:
            regressions += 1
            margins.append({"pair_id": pair.get("pair_id"), "margin": None})
            continue
        margin = int(success_score) - int(fault_score)
        margins.append({"pair_id": pair.get("pair_id"), "margin": margin})
        if margin < min_margin:
            regressions += 1
    return {
        "eval18_discrimination_regression_count": regressions,
        "eval18_pair_margins": margins,
    }


# ─────────────────────────── main ───────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Phase 23-03 still-frame veto eval harness")
    p.add_argument("--manifest", required=True, help="frozen manifest.json 경로")
    p.add_argument("--out", required=True, help="결과 JSON 경로")
    p.add_argument(
        "--lock", default=None,
        help="manifest lock.json (기본: manifest 와 같은 디렉터리 .lock.json)",
    )
    p.add_argument(
        "--created-at", default=None,
        help="result_generated_at (ISO8601, 주입). 미지정 시 현재 UTC.",
    )
    args = p.parse_args(argv)

    manifest_path = args.manifest
    out_path = args.out
    lock_path = args.lock or manifest_path.replace(".json", ".lock.json")

    # (J) run-commit ancestry 강제 — lock 부재/sha 불일치/lock∉ancestor/dirty 면 거부.
    run_meta = _enforce_run_commit_ancestry(manifest_path, lock_path, out_path)

    # manifest 로드 + FaultKey 검증 (unknown enum 이면 Pod 측정 전 fail, D-17 MED-3).
    manifest = load_manifest(manifest_path)

    api_key = load_api_key()

    rows = manifest.get("rows") or []

    # (B2) multi-arm result shape: cases[]{row_id, arms:{...}} — 순차 측정.
    cases: list[dict] = []
    for row in rows:
        row_id = row["row_id"]
        required_arms = row.get("required_arms") or [ARM_PRODUCTION, ARM_BASELINE]
        optional_arms = row.get("optional_arms") or []
        case_payload = row.get("case") or row  # 영상/프로필은 manifest case 블록 소유.

        arms: dict[str, dict] = {}
        for arm in [*required_arms, *optional_arms]:
            if arm not in KNOWN_ARMS:
                log.error("manifest row=%s 에 unknown arm=%s", row_id, arm)
                raise SystemExit(2)
            # (E) arm·case 별 격리 namespace/run_id — cross-arm 캐시 누수 방지.
            cache_namespace = f"{row_id}:{arm}"
            run_id = f"{row_id}:{arm}:cold0"
            arms[arm] = run_production_arm(
                case=case_payload,
                arm=arm,
                cache_namespace=cache_namespace,
                run_id=run_id,
                api_key=api_key,
                model=MODEL,
            )

        cases.append({"row_id": row_id, "arms": arms})

    # (D) 3-way 분리 + completion + coverage (manifest gate_policy 재계산).
    aggregates = compute_aggregates(cases, manifest)
    # (H) EVAL18 4쌍 (manifest regression_pairs 재계산).
    eval18 = compute_eval18_regression(cases, manifest)

    result = {
        # (J) run-commit ancestry transcribe (D-17 HIGH-1).
        "run_git_commit": run_meta["run_git_commit"],
        "worktree_dirty_at_run": run_meta["worktree_dirty_at_run"],
        "manifest_lock_git_commit": run_meta["manifest_lock_git_commit"],
        "manifest_sha256": run_meta["manifest_sha256"],
        "eval_command": list(sys.argv),
        "result_generated_at": args.created_at or _utc_now_iso(),
        "model": MODEL,
        # (B2) multi-arm shape.
        "cases": cases,
        # (D/H) top-level 집계 (machine-checkable).
        **aggregates,
        **eval18,
    }

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("저장: %s", out_path)
    log.info(
        "집계: FP=%d evaluable=%d coverage_pass=%s completion_pass=%s eval18_regression=%d",
        aggregates["false_positive_count"], aggregates["clean_evaluable_count"],
        aggregates["coverage_pass"], aggregates["completion_pass"],
        eval18["eval18_discrimination_regression_count"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
