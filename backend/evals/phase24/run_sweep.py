"""Phase 24 generalization sweep — serial, in-process _process, distinct IDs per member.

phase18 6 fault->correct 페어를 BOTH members Mode 1 (vs reference) 로 채점하고, 각 멤버의
실 result['deductionBreakdown'] 을 캡처해 두 산출물을 쓴다 (repo 밖 EVAL_OUT_DIR —
phase25 25-SWEEP-EVIDENCE 근본원인 4: repo 내 baseline/ 덮어쓰기가 pod 소스트리를
오염시켜 게이트가 오염 기준으로 판정. repo 의 baseline/ 은 git 커밋본 전용 read-only):

  · $EVAL_OUT_DIR/phase24/phase24_breakdowns.json — check_generalization 게이트 artifact (HIGH-4).
      {motion_id: {"correct": <deductionBreakdown dict | null>,
                   "fault":   <deductionBreakdown dict | null>}}
  · $EVAL_OUT_DIR/phase24/phase24_sweep_report.json — belle 관찰용 rich 리포트
      (overallScore / status / errorCode / activated criterion set / cold-rerun).
  기본 EVAL_OUT_DIR=/tmp/sunity_eval_out. 승격(커밋 baseline 갱신)은 게이트 PASS +
  belle 승인 후 명시적 copy+commit 만 — evals/phase25/README.md "Pod 운영 절차" 참조.

객관성 ([[analysis-objectivity-no-human-scores]]): fault 라벨=영상 파생(OK). 점수=채점기
결정론 출력 스냅샷(라벨 아님). 사람 점수 ground-truth 라벨 금지.

동시성 ([[pipeline-not-concurrency-safe-eval-serial]]): _process 는 동시성 비안전 — SERIAL.
한 멤버 _process 완료까지 대기 후 다음. 동시 트리거 = cross-contamination(가짜 결과).

실행 (Pod, RTMW GPU + Gemini env 필요):
    source /workspace/aws_env.sh && \
    export CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key GEMINI_COACH_ENABLED=1 \
           RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx \
           YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx RTMW_DEVICE=cuda \
           FIREBASE_SA_PATH=/workspace/firebase-sa.json RECOGNIZER_BACKEND=gemini && \
    export GEMINI_API_KEY=$(python3 -c "import boto3;print(boto3.client('ssm',region_name='ap-northeast-2').get_parameter(Name='/sunity/motion/gemini-api-key',WithDecryption=True)['Parameter']['Value'])") && \
    cd /workspace/SunityMotion/backend && PYTHONPATH=shared/python:. python3 evals/phase24/run_sweep.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent.parent  # backend/
sys.path.insert(0, str(BACKEND / "shared" / "python"))
sys.path.insert(0, str(BACKEND))

# ── 산출물 경로 (phase25 근본원인 4 동일 패턴 — pod repo 오염 방지) ────────────
_EVAL_OUT_ENV = "EVAL_OUT_DIR"
_EVAL_OUT_DEFAULT = "/tmp/sunity_eval_out"
_PHASE_SUBDIR = "phase24"


def _eval_out_dir() -> Path:
    root = Path(os.environ.get(_EVAL_OUT_ENV) or _EVAL_OUT_DEFAULT)
    return (root.expanduser() / _PHASE_SUBDIR).resolve()


def _resolve_out_dir() -> Path:
    """출력 디렉토리 확정 — repo 안이면 즉시 중단 (baseline 오염 차단)."""
    out = _eval_out_dir()
    repo_root = BACKEND.parent.resolve()
    if out == repo_root or repo_root in out.parents:
        raise SystemExit(
            f"[eval-out] EVAL_OUT_DIR={out} 가 repo({repo_root}) 안을 가리킨다 — "
            "sweep 산출물이 git 커밋 baseline 을 오염시킨다 (phase25 25-SWEEP-EVIDENCE "
            f"근본원인 4). repo 밖 경로로 설정하라 (기본 {_EVAL_OUT_DEFAULT})."
        )
    return out

BUCKET = "sunity-motion-pilot-videos"
UID = "phase24eval"
RUNID = str(int(time.time()))
# phase18 6 페어 (combo 제외 — fault 영상 없음). climb=known not_pole 게이트,
# kip-up=known false-positive (새 tally 가 해소해야 할 대상).
PAIRS = ["power-spin", "peter-pan", "elbow-twist-sister", "pdshape", "kip-up", "climb"]
COLD_RERUN_MOTION = "pdshape"  # 결정성/선택 재현 검증용 cold re-run 대상


def _load_pipeline():
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", str(BACKEND / "functions" / "pipeline" / "app.py")
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline


def _aid(motion: str, role: str) -> str:
    # s3keys analysisId 는 영숫자만 — 하이픈 슬러그 금지 (HIGH 2 정합).
    return motion.replace("-", "") + role + RUNID


def _run_member(pipeline, fa, models, motion: str, label: str, analysis_id: str) -> dict:
    """단일 멤버 _process 직접 호출 + Firestore 결과 readback. SERIAL (완료까지 블로킹)."""
    fixture = "fault" if label == "fault" else "correct"
    key = f"fixtures/phase15/{motion}/{fixture}.mp4"
    fa._doc(models.analysis_doc_path(UID, analysis_id)).set({
        "mode": models.MODE_EXPERT,              # mode1 = 정은지 reference 비교
        "referenceMotionId": f"ref-{motion}",
        "status": "uploading",
        "createdAt": int(time.time() * 1000),
        "fileName": analysis_id + ".mp4",
        "videoKey": key,
        "sourceLabel": f"phase24_sweep:{motion}:{label}",
    })
    err = None
    try:
        pipeline._process(BUCKET, key, UID, analysis_id)
    except Exception as exc:  # noqa: BLE001 — not_pole 등은 doc 에 failed 로 기록됨
        err = f"{type(exc).__name__}: {exc}"

    d = fa.get_analysis(UID, analysis_id) or {}
    r = d.get("result") or {}
    ec = d.get("errorCode")
    bd = r.get("deductionBreakdown")
    # 24-06 §3 진단 — clip 별 visionVeto(collectionStatus + alignment.adoption)를 캡처해
    # kip-up 의 정확한 low_alignment 발화 조건을 다음 pod-run 에서 확정한다(관찰 전용, score 무관).
    vv = r.get("visionVeto")
    rec = {
        "motion_id": motion,
        "label": label,
        "analysisId": analysis_id,
        "status": d.get("status"),
        "overallScore": r.get("overallScore"),
        "errorCode": ec.get("code") if isinstance(ec, dict) else ec,
        "exception": err,
        "deductionBreakdown": bd,
        "visionVeto": vv,
    }
    crit = None
    if isinstance(bd, dict):
        crit = sorted({rr.get("criterion") for rr in (bd.get("records") or [])})
    rec["activatedCriteria"] = crit
    cs = vv.get("collectionStatus") if isinstance(vv, dict) else None
    aa = (vv.get("alignment") or {}).get("adoption") if isinstance(vv, dict) else None
    print(
        f"  done {motion:20s} {label:7s} status={rec['status']} "
        f"overall={rec['overallScore']} crit={crit} vv={cs}/{aa} "
        f"err={rec['errorCode'] or err or '-'}",
        flush=True,
    )
    return rec


def main() -> int:
    from sunity_shared import firestore_admin as fa, models  # noqa: E402

    print(f"[setup] runId={RUNID} uid={UID} pairs={len(PAIRS)} (serial, in-process)", flush=True)
    pipeline = _load_pipeline()

    report: list[dict] = []
    artifact: dict[str, dict] = {}

    for motion in PAIRS:
        print(f"\n[pair] {motion}", flush=True)
        # fault 먼저 → correct (페어 순서 무관, 단 SERIAL).
        fault_rec = _run_member(pipeline, fa, models, motion, "fault", _aid(motion, "Fault"))
        correct_rec = _run_member(pipeline, fa, models, motion, "success", _aid(motion, "Correct"))
        report.append(fault_rec)
        report.append(correct_rec)
        artifact[motion] = {
            "fault": fault_rec["deductionBreakdown"],
            "correct": correct_rec["deductionBreakdown"],
        }

    # ── cold re-run (결정성 + criterion selection 재현) ──
    print(f"\n[cold-rerun] {COLD_RERUN_MOTION} correct (2nd, distinct id)", flush=True)
    cold = _run_member(
        pipeline, fa, models, COLD_RERUN_MOTION, "success",
        _aid(COLD_RERUN_MOTION, "ColdCorrect"),
    )
    # 첫 실행의 correct 기록과 activated criterion set 비교.
    warm = next(
        (r for r in report if r["motion_id"] == COLD_RERUN_MOTION and r["label"] == "success"),
        None,
    )
    cold_check = {
        "motion": COLD_RERUN_MOTION,
        "warm_overall": warm["overallScore"] if warm else None,
        "cold_overall": cold["overallScore"],
        "warm_criteria": warm["activatedCriteria"] if warm else None,
        "cold_criteria": cold["activatedCriteria"],
        "selection_identical": (
            bool(warm) and warm["activatedCriteria"] == cold["activatedCriteria"]
        ),
    }
    print(f"  cold-check: {json.dumps(cold_check, ensure_ascii=False)}", flush=True)

    out_dir = _resolve_out_dir()  # repo 밖 — 커밋 baseline 무접촉 (근본원인 4)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "phase24_breakdowns.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "phase24_sweep_report.json").write_text(
        json.dumps(
            {
                "_meta": {
                    "phase": "24",
                    "runId": RUNID,
                    "uid": UID,
                    "captured_epoch": int(time.time()),
                    "scorer": "phase24_transparent_deduction_tally",
                    "mode": "mode1",
                    "run": "serial in-process _process (pipeline-not-concurrency-safe-eval-serial)",
                    "objectivity": "fault 라벨=영상 파생. 점수=채점기 결정론 출력 스냅샷(라벨 아님).",
                },
                "results": report,
                "cold_rerun_check": cold_check,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"\n[done] wrote {out_dir}/phase24_breakdowns.json ({len(artifact)} motions) "
        f"+ {out_dir}/phase24_sweep_report.json (repo 밖 — 커밋 baseline 무접촉)",
        flush=True,
    )

    # 관찰 요약 (belle 검증 — pass/fail 게이트 아님).
    print("\n=== SWEEP OBSERVATION (belle review) ===", flush=True)
    print(f"{'motion':22s} | {'fault.overall':13s} | {'correct.overall':15s} | verdict", flush=True)
    for motion in PAIRS:
        f = next((r for r in report if r["motion_id"] == motion and r["label"] == "fault"), {})
        c = next((r for r in report if r["motion_id"] == motion and r["label"] == "success"), {})
        fo, co = f.get("overallScore"), c.get("overallScore")
        if fo is None or co is None:
            verdict = f"gate/err (fault={f.get('errorCode') or f.get('status')}, correct={c.get('errorCode') or c.get('status')})"
        elif fo < co:
            verdict = f"discriminate (margin={co - fo})"
        elif fo == co:
            verdict = "TIE (no discrimination)"
        else:
            verdict = "INVERTED (fault>correct — investigate)"
        print(f"{motion:22s} | {str(fo):13s} | {str(co):15s} | {verdict}", flush=True)
    print("ALLDONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
