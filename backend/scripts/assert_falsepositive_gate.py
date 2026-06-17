#!/usr/bin/env python3
"""Phase 15 위양성 게이트 assert — sweep evidence 를 FROZEN 08.1 baseline 에 대조.

Phase 15 / CONTEXT D-01/D-02/D-06 / MEDIUM 5 (frozen checksum hard gate + fallback==0) /
MEDIUM 6 (success=low-severity, fail=객관 machine 기준).

입력 = Firestore sweep evidence 문서 (sweep_phase15.py 가 쓴 per-run uid scoped analysis doc)
+ 분류 라벨 (success/fail — 영상 입력 라벨만; CONTEXT D-06 ground-truth 점수 라벨 영구 금지).

동작:
  (1) MEDIUM 5 — 실행 시작에 backend/judging_data/tilt_thresholds.yaml 의 sha256 을 계산해
      08.1 evidence 의 frozen checksum 과 일치하는지 hard gate. 경로는 force_signals.py:250
      (_TILT_THRESHOLDS_PATH) 과 동일 경로를 mirror 한다 (존재하지 않는 analysis/ 경로 금지).
      불일치 시 non-zero exit + frozen baseline drift 메시지 (재calibrate 차단,
      D-02 / calibration-source-hard-gate).

  (2) MEDIUM 6 — success 영상: axis severity 'low' (08.1 25/25 'low' invariant mirror) +
      명시된 최소 점수 기대치(있으면) assert. fail 영상: 객관 machine 기준 — fail 영상이
      all-'low' severity 가 아님 / deficit·finding 키를 노출함 (가용 필드 기준) assert.
      정확한 per-fault 기준을 지금 객관적으로 핀할 수 없으면 fail-video FAULT-TYPE assertion 을
      "manual evidence review" 로 다운그레이드하고 자동 per-fault gating 은 Phase 18 로 명시
      deferred (--fail-mode manual). 임계 기준은 08.1 evidence + IPSF baseline 의 기존 확정값만
      사용하고 신규 fit 금지.

  (3) MEDIUM 5 — evidence 가 분석된 force-signal warning 전반에서 tilt_thresholds_fallback
      카운트 == 0 임을 확인 (fail-open 탐지).

threshold 를 이 스크립트에서 재산출/재저장하지 않는다 — 오직 대조만. evidence 문서·stdout 에
API 키를 절대 출력하지 않는다 (RESEARCH Security / T-15.01-02). per-video PASS/FAIL 표를
출력하고 하나라도 FAIL 이면 non-zero exit. --dry-run 에서는 checksum hard gate + 인자 파싱만 검증.

CLI:
    python backend/scripts/assert_falsepositive_gate.py \
        --uid phase15_mode3_climb_<runId> --label-map '{"climbSuccess<runId>":"success",...}'
    python backend/scripts/assert_falsepositive_gate.py --dry-run   # checksum gate + 인자만
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "shared" / "python"))

# force_signals.py:250 _TILT_THRESHOLDS_PATH 와 동일 경로 mirror (존재하지 않는 analysis/ 금지).
TILT_THRESHOLDS_PATH = BACKEND / "judging_data" / "tilt_thresholds.yaml"

# 08.1 SWEEP-EVIDENCE.md frozen baseline — thresholdChecksum (재calibrate 차단, D-02).
FROZEN_THRESHOLD_CHECKSUM = (
    "c94bb8c7cc87120255c244548bd59464840130cbf9144fd109490588a3e1e87c"
)

# 08.1 25/25 'low' invariant — success 영상 axis severity 기대값.
SUCCESS_EXPECTED_SEVERITY = "low"
FALLBACK_WARNING = "tilt_thresholds_fallback"


def _checksum_hard_gate() -> str:
    """MEDIUM 5 — tilt_thresholds.yaml sha256 == frozen baseline. 불일치 시 RuntimeError."""
    if not TILT_THRESHOLDS_PATH.exists():
        raise RuntimeError(
            f"tilt_thresholds.yaml not found at {TILT_THRESHOLDS_PATH} — frozen baseline 부재"
        )
    actual = hashlib.sha256(TILT_THRESHOLDS_PATH.read_bytes()).hexdigest()
    if actual != FROZEN_THRESHOLD_CHECKSUM:
        raise RuntimeError(
            "frozen baseline drift — tilt_thresholds.yaml sha256 불일치.\n"
            f"  expected (08.1 frozen): {FROZEN_THRESHOLD_CHECKSUM}\n"
            f"  actual:                 {actual}\n"
            "Phase 15 는 임계값 재calibrate 금지 (D-02 / calibration-source-hard-gate). "
            "yaml 을 08.1 baseline 으로 복원하거나 별도 plan 으로 재calibrate 할 것."
        )
    return actual


# ── evidence 추출 (재calibrate 0 — 오직 대조만) ────────────────────────────


def _axis_severities(result: dict) -> list[str]:
    """forceSignalsReport.axisMetrics[].severity 추출."""
    fsr = (result or {}).get("forceSignalsReport") or {}
    metrics = fsr.get("axisMetrics") or []
    return [str(m.get("severity", "")) for m in metrics if isinstance(m, dict)]


def _fallback_warning_count(result: dict) -> int:
    """MEDIUM 5 — tilt_thresholds_fallback 카운트 (fail-open 탐지)."""
    fsr = (result or {}).get("forceSignalsReport") or {}
    count = 0
    for w in fsr.get("warnings") or []:
        if w == FALLBACK_WARNING:
            count += 1
    for m in fsr.get("axisMetrics") or []:
        if isinstance(m, dict):
            for w in m.get("warnings") or []:
                if w == FALLBACK_WARNING:
                    count += 1
    return count


def _has_objective_fault_signal(result: dict) -> bool:
    """fail 영상 객관 machine 기준 — all-'low' severity 가 아니거나 finding/deficit 노출."""
    severities = _axis_severities(result)
    if any(s and s != "low" for s in severities):
        return True
    body = (result or {}).get("bodyComparisonReport") or {}
    findings = body.get("findings") or []
    if findings:
        return True
    # force_pattern_inference / forceSignalsReport top-level warnings 도 신호로 인정.
    fpi = (result or {}).get("forcePatternInference") or {}
    if fpi.get("findings"):
        return True
    return False


def _assert_one(uid: str, analysis_id: str, label: str, fail_mode: str, db) -> dict:
    """단일 doc 대조. PASS/FAIL row 반환 (재calibrate 0 — read-only 대조)."""
    from sunity_shared import firestore_admin as fa  # noqa: E402

    doc = fa.get_analysis(uid, analysis_id)
    if doc is None:
        return {"analysisId": analysis_id, "label": label, "status": "FAIL",
                "reason": "doc 없음"}
    result = doc.get("result") or {}
    fallback = _fallback_warning_count(result)
    if fallback != 0:
        return {"analysisId": analysis_id, "label": label, "status": "FAIL",
                "reason": f"tilt_thresholds_fallback={fallback} (fail-open, MEDIUM 5)"}

    severities = _axis_severities(result)
    if label == "success":
        # MEDIUM 6 — success = 08.1 25/25 'low' invariant.
        bad = [s for s in severities if s and s != SUCCESS_EXPECTED_SEVERITY]
        if bad:
            return {"analysisId": analysis_id, "label": label, "status": "FAIL",
                    "reason": f"success 영상 axis severity {bad} != 'low' (위양성, MEDIUM 6)"}
        return {"analysisId": analysis_id, "label": label, "status": "PASS",
                "reason": f"all-low severity ({len(severities)} axis)"}

    # fail 영상.
    if fail_mode == "manual":
        # per-fault 객관 기준 미확정 → manual review 다운그레이드 (Phase 18 defer).
        return {"analysisId": analysis_id, "label": label, "status": "REVIEW",
                "reason": "fail per-fault gating Phase 18 defer (manual evidence review)"}
    # auto — 객관 machine 기준.
    if _has_objective_fault_signal(result):
        return {"analysisId": analysis_id, "label": label, "status": "PASS",
                "reason": "객관 fault 신호 노출 (non-low severity 또는 finding)"}
    return {"analysisId": analysis_id, "label": label, "status": "FAIL",
            "reason": "fail 영상이 객관 fault 신호 미노출 (all-low + finding 0)"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 15 위양성 게이트 assert — sweep evidence 를 FROZEN 08.1 baseline 에 대조 "
            "(재calibrate 금지, D-02). success=low-severity / fail=객관 machine 기준."
        )
    )
    parser.add_argument("--uid", help="sweep_phase15.py 가 쓴 per-run uid")
    parser.add_argument(
        "--label-map",
        help='JSON {"<analysisId>":"success|fail", ...} — 영상 입력 라벨만 (점수 라벨 금지, D-06)',
    )
    parser.add_argument(
        "--fail-mode", default="auto", choices=["auto", "manual"],
        help="fail 영상 검증 — auto(객관 machine) 또는 manual(Phase 18 defer review)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # MEDIUM 5 — checksum hard gate 는 dry-run 에서도 항상 먼저 실행.
    checksum = _checksum_hard_gate()
    print(f"[checksum] tilt_thresholds.yaml sha256 == frozen baseline ({checksum[:8]}…) OK", flush=True)

    if args.dry_run:
        print("[dry-run] checksum hard gate + 인자 파싱만 검증. Firestore read 없음.", flush=True)
        return 0

    if not args.uid or not args.label_map:
        parser.error("--uid 와 --label-map 은 실행(non-dry-run) 모드에서 필수")

    label_map = json.loads(args.label_map)
    norm_labels = {}
    for aid, lab in label_map.items():
        lab = str(lab).lower()
        if lab not in ("success", "fail"):
            raise RuntimeError(f"라벨 {lab!r} 는 success|fail 만 허용 (점수 라벨 금지, D-06)")
        norm_labels[aid] = lab

    from sunity_shared import firestore_admin as fa  # noqa: E402
    db = fa._db()

    rows = [
        _assert_one(args.uid, aid, lab, args.fail_mode, db)
        for aid, lab in norm_labels.items()
    ]

    print("\n[evidence] per-video PASS/FAIL:", flush=True)
    print(f"  {'analysisId':<32} {'label':<8} {'status':<7} reason", flush=True)
    for r in rows:
        print(
            f"  {r['analysisId']:<32} {r['label']:<8} {r['status']:<7} {r['reason']}",
            flush=True,
        )

    failed = [r for r in rows if r["status"] == "FAIL"]
    if failed:
        print(f"\n[verdict] FAIL — {len(failed)}/{len(rows)} video(s) failed gate", flush=True)
        return 1
    print(f"\n[verdict] PASS — {len(rows)} video(s) (재calibrate 0, baseline 대조만)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
