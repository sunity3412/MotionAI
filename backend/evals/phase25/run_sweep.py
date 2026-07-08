"""Phase 25 vision-pointed 상체 감점 sweep — serial, in-process _process, tee 관측 확장.

phase24 harness(evals/phase24/run_sweep.py) 복제-확장 (25-04 Task 1). phase18 6 fault->
correct 페어를 BOTH members Mode 1 (vs reference) 로 채점하고, phase24 산출물에 더해
멤버별 관측 2종을 read-only tee 로 캡처한다:

  · collectObservation — pipeline._collect_vision_fault_context 반환 ctx 의
      collection_status + supported_differences 의 canonical _faultKey 목록 +
      pointed_joints_from_supported_differences 결과. **success 멤버 포함 전 12 멤버**
      (OD-2 짚기-FP 관측 — na_audit 가 버리던 collect 산출을 harness 가 채움. 관측만,
      게이트 아님. 리서치 §3 관측 공백 + Open Q2 의 eval-전용 권장).
  · seedObservation — pipeline._build_deduction_measured_deviations 에 seed_audit_out
      dict 를 주입(25-01 관측 파라미터)해 {pointed, window_joints, fallback_joints} 캡처
      (assert_gates.check_pointed_only_window / check_kipup_upper_structure 구조 게이트 입력).

wrapper 불변식 (리서치 함정 ③): **read-only tee — collect 인자 변경 금지.** collect 는
받은 kwargs 그대로 원본에 전달만 한다 (at_seconds 는 collect 내부 소관 — full-video 호출
at_seconds=None 불변). seed builder wrapper 는 seed_audit_out(관측 전용 kwarg, production
미전달·부작용 0)만 주입한다 — measured substrate/채점 경로 무접촉.

산출물 (25-SWEEP-EVIDENCE 근본원인 4 — repo 밖 EVAL_OUT_DIR 로만 기록):
  · $EVAL_OUT_DIR/phase25/phase25_breakdowns.json   — {motion: {correct, fault}} (phase24 게이트 형상)
  · $EVAL_OUT_DIR/phase25/phase25_sweep_report.json — rich 리포트 (score/status/activated criteria/
                                                      collectObservation/seedObservation/짚기-FP 요약)
  --tag warm 실행 시 *_warm.json 으로 기록 (cold/warm 결정론 게이트 입력).
  기본 EVAL_OUT_DIR=/tmp/sunity_eval_out. repo 내 evals/phase25/baseline/ 은 git 커밋본
  (비교 기준) 전용 read-only — sweep 이 절대 덮어쓰지 않는다 (2026-07-02 FAIL run 값이
  pod network volume 의 baseline/ 을 오염시켜 게이트가 오염 기준으로 판정한 사고 재발 금지).
  승격(게이트 PASS + belle 승인 후 명시적 copy+commit)은 README "Pod 운영 절차" 참조.

객관성 ([[analysis-objectivity-no-human-scores]]): fault 라벨=영상 파생(OK). 점수=채점기
결정론 출력 스냅샷(라벨 아님). 사람 점수 ground-truth 라벨 금지.

동시성 ([[pipeline-not-concurrency-safe-eval-serial]]): _process 는 동시성 비안전 — SERIAL.
한 멤버 _process 완료까지 대기 후 다음. 동시 트리거 = cross-contamination(가짜 결과).

크레딧 (T-25-10): cold sweep = 캐시 전량 miss(25-04 #3: PROMPT_VERSION v11.0 + SCHEMA
v8.0 + AGGREGATION_VERSION agg4 bump) → 12 멤버 × 3 call = 36 Gemini pro call + 멤버당
영상 2 업로드. 429/resource_limited 발생 시 fail-closed 중단 후 belle 보고.

실행 (Pod, RTMW GPU + Gemini env 필요 — phase24 헤더 승계):
    source /workspace/aws_env.sh && \
    export CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key GEMINI_COACH_ENABLED=1 \
           RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx \
           YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx RTMW_DEVICE=cuda \
           FIREBASE_SA_PATH=/workspace/firebase-sa.json RECOGNIZER_BACKEND=gemini && \
    export GEMINI_API_KEY=$(python3 -c "import boto3;print(boto3.client('ssm',region_name='ap-northeast-2').get_parameter(Name='/sunity/motion/gemini-api-key',WithDecryption=True)['Parameter']['Value'])") && \
    cd /workspace/SunityMotion/backend && \
    PYTHONPATH=shared/python:. python3 evals/phase25/run_sweep.py            # cold
    PYTHONPATH=shared/python:. python3 evals/phase25/run_sweep.py --tag warm # warm 재실행

    veto env 2종(GEMINI_VISION_VETO_ENABLED=1 / GEMINI_MAX_VETO_WALL_S=300)은
    run_sweep 이 스스로 setdefault 하므로 별도 export 불필요 (production
    start_server.sh mirror; 명시 export 시 그 값 우선).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent.parent  # backend/
sys.path.insert(0, str(BACKEND / "shared" / "python"))
sys.path.insert(0, str(BACKEND))

# ── RTMW 결정론 (Phase 25 근본원인 #2) — eval 은 항상 결정론 모드 ─────────────
# cold/warm 프로세스 간 2~5점 흔들림의 엔지니어링 해법: CUDA EP EXHAUSTIVE conv
# algo 벤치마크의 run-to-run algo flip 이 tol 20° 경계 관절 criterion 활성을
# flip 시킨다 → RTMWPoseEngine 이 RTMW_DETERMINISTIC=1 이면 세션 생성 시점에
# 결정론 옵션을 주입 (sunity_shared/.../rtmw/ort_determinism.py — 근거/한계 명시).
# setdefault: 운영자가 명시적으로 RTMW_DETERMINISTIC=0 을 export 하면 A/B 비교
# 목적의 비결정 baseline 재현이 가능하다. pipeline 로드(_ensure_adapters) 전에
# 설정돼야 하므로 module-level 에서 주입.
os.environ.setdefault("RTMW_DETERMINISTIC", "1")

# ── Gemini vision veto env (2026-07-05 신규 pod sweep 무효화 사고 재발 방지) ──
# 실행 셸에 이 env 가 없으면 veto 경로 전체가 조용히 OFF 된다 — visionVeto:
# disabled → deductionBreakdown 없음 + 레거시 min-of-core 점수 → sweep 전체 무효
# (2026-07-05 새 pod svn31pzja7uay0 에서 실제 발생, 1차 sweep 통째로 폐기).
# eval 은 production 구성을 mirror 해야 한다: /workspace/start_server.sh 영구
# 박제 구성(GEMINI_VISION_VETO_ENABLED=1 + GEMINI_MAX_VETO_WALL_S=300,
# 2026-07-02 FP 재발 사고 fix)과 동일 값. setdefault 이므로 운영자가 명시적으로
# export 하면 그 값이 우선한다 (예: GEMINI_VISION_VETO_ENABLED=0 으로 veto-off
# baseline A/B 재현). pipeline 로드(_load_pipeline → functions/pipeline/app.py
# 가 env 소비) 전에 설정돼야 하므로 module-level 주입 — RTMW_DETERMINISTIC 과
# 동일 패턴.
os.environ.setdefault("GEMINI_VISION_VETO_ENABLED", "1")
os.environ.setdefault("GEMINI_MAX_VETO_WALL_S", "300")

# ── Phase 27 D-03 (SPD-03) — 단일 분석 내부 prefetch 겹치기 env ───────────────
# GEMINI_UPLOAD_PREFETCH: 학생 업로드 ∥ scene_finder 를 포즈 추출 그늘에 숨기는
# 레버 (분석 간 SERIAL 불변, 분석 내부만 병렬). 코드 default 는 "1"(ON)이지만
# eval 하니스도 명시 박제 — 27-09 sweep 이 이 레버로 before/after 를 대조한다.
# setdefault 이므로 운영자가 GEMINI_UPLOAD_PREFETCH=0 을 export 하면 동기 baseline
# (27-04 경로) A/B 재현 가능. pipeline 로드 전 module-level 주입 (위 패턴 동일).
os.environ.setdefault("GEMINI_UPLOAD_PREFETCH", "1")

# ── 산출물 경로 (25-SWEEP-EVIDENCE 근본원인 4 — pod repo 오염 방지) ───────────
# 신규 산출물은 repo 밖 EVAL_OUT_DIR 로만 쓴다. repo 내 evals/*/baseline/ 은
# git 커밋본(비교 기준) 전용 read-only.
_EVAL_OUT_ENV = "EVAL_OUT_DIR"
_EVAL_OUT_DEFAULT = "/tmp/sunity_eval_out"
_PHASE_SUBDIR = "phase25"


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
            "sweep 산출물이 git 커밋 baseline 을 오염시킨다 (25-SWEEP-EVIDENCE "
            f"근본원인 4). repo 밖 경로로 설정하라 (기본 {_EVAL_OUT_DEFAULT})."
        )
    return out

BUCKET = "sunity-motion-pilot-videos"
UID = "phase25eval"
RUNID = str(int(time.time()))
# phase18 6 페어 (combo 제외 — fault 영상 없음). climb=known not_pole 게이트,
# kip-up=상체 감점 실효 판정 대상 (SCORE-15 — phase24 baseline 88 대비 방향 개선).
PAIRS = ["power-spin", "peter-pan", "elbow-twist-sister", "pdshape", "kip-up", "climb"]
COLD_RERUN_MOTION = "pdshape"  # in-run 결정성/선택 재현 검증용 (phase24 승계)

UPPER_BODY_JOINTS = ("left_shoulder", "right_shoulder", "left_elbow", "right_elbow")

# 현재 _process 가 트리거한 멤버 키 — tee wrapper 가 캡처를 귀속시킨다 (probe 패턴).
_CURRENT = {"key": None}
_COLLECT_CAP: dict[str, dict] = {}
_SEED_CAP: dict[str, dict] = {}


def _load_pipeline():
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", str(BACKEND / "functions" / "pipeline" / "app.py")
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline


def _fault_key_json(rec: dict) -> dict:
    """supported difference 1건 → JSON-안전 관측 dict (_faultKey canonical 만 소비)."""
    fk = rec.get("_faultKey")
    if hasattr(fk, "to_dict"):
        fk = fk.to_dict()
    elif not isinstance(fk, dict):
        fk = None
    return {
        "faultKey": fk,
        "severity": rec.get("severity"),
        "supportCount": rec.get("_supportCount"),
    }


def _install_tee(pipeline) -> None:
    """read-only tee 2종 설치 — 인자 무변경(at_seconds 불변), 캡처만."""
    from sunity_shared.analysis import vision_veto as vv

    orig_collect = pipeline._collect_vision_fault_context

    def _collect_tee(**kwargs):
        # 인자 변경 금지 — kwargs 그대로 통과 (리서치 함정 ③: at_seconds=None 은
        # collect 내부의 Gemini 호출 소관이며 이 tee 는 접촉하지 않는다).
        ctx = orig_collect(**kwargs)
        try:
            supported = list(getattr(ctx, "supported_differences", None) or [])
            pointed = vv.pointed_joints_from_supported_differences(supported)
            # 27-02 — cold 증빙 read-only tee: ctx.telemetry 의 cacheHit/호출수만
            # 캡처 (VisionVetoCache miss=false 가 cold run 증거. Pitfall 1 정합).
            telem = dict(getattr(ctx, "telemetry", None) or {})
            _COLLECT_CAP[_CURRENT["key"]] = {
                "collectionStatus": getattr(ctx, "collection_status", None),
                "pointedJoints": list(pointed),
                "supportedCount": len(supported),
                "supportedFaultKeys": [
                    _fault_key_json(r) for r in supported if isinstance(r, dict)
                ],
                "vetoTelemetry": {
                    "cacheHit": telem.get("cacheHit"),
                    "cacheKey": telem.get("cacheKey"),
                    "completedCalls": telem.get("completedCalls"),
                    "plannedCalls": telem.get("plannedCalls"),
                    "durationMs": telem.get("durationMs"),
                },
            }
        except Exception as exc:  # noqa: BLE001 — 관측 실패는 분석 흐름 차단 0
            _COLLECT_CAP[_CURRENT["key"]] = {
                "captureError": f"{type(exc).__name__}: {exc}"
            }
        return ctx

    pipeline._collect_vision_fault_context = _collect_tee

    orig_build = pipeline._build_deduction_measured_deviations

    def _build_tee(**kwargs):
        audit = kwargs.get("seed_audit_out")
        if not isinstance(audit, dict):
            audit = {}
            kwargs["seed_audit_out"] = audit  # 25-01 관측 kwarg — 채점 경로 무접촉
        md = orig_build(**kwargs)
        _SEED_CAP[_CURRENT["key"]] = dict(audit)
        return md

    pipeline._build_deduction_measured_deviations = _build_tee


def _aid(motion: str, role: str) -> str:
    # s3keys analysisId 는 영숫자만 — 하이픈 슬러그 금지 (phase24 HIGH 2 정합).
    return motion.replace("-", "") + role + RUNID


def _run_member(pipeline, fa, models, motion: str, label: str, analysis_id: str) -> dict:
    """단일 멤버 _process 직접 호출 + Firestore 결과 readback. SERIAL (완료까지 블로킹)."""
    fixture = "fault" if label == "fault" else "correct"
    key = f"fixtures/phase15/{motion}/{fixture}.mp4"
    _CURRENT["key"] = f"{motion}:{label}:{analysis_id}"
    fa._doc(models.analysis_doc_path(UID, analysis_id)).set({
        "mode": models.MODE_EXPERT,              # mode1 = 정은지 reference 비교
        "referenceMotionId": f"ref-{motion}",
        "status": "uploading",
        "createdAt": int(time.time() * 1000),
        "fileName": analysis_id + ".mp4",
        "videoKey": key,
        "sourceLabel": f"phase25_sweep:{motion}:{label}",
    })
    err = None
    _wall_t0 = time.monotonic()  # 27-02 — 멤버당 벽시계 (stage 합산 대비 미계상 구간 산출)
    try:
        pipeline._process(BUCKET, key, UID, analysis_id)
    except Exception as exc:  # noqa: BLE001 — not_pole 등은 doc 에 failed 로 기록됨
        err = f"{type(exc).__name__}: {exc}"
    wall_ms = int((time.monotonic() - _wall_t0) * 1000)

    d = fa.get_analysis(UID, analysis_id) or {}
    r = d.get("result") or {}
    ec = d.get("errorCode")
    bd = r.get("deductionBreakdown")
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
        # 27-02 — stage-timing 실측 (result.timingsMs flat dict, 27-01 계측) + 벽시계.
        "timingsMs": r.get("timingsMs"),
        "wallMs": wall_ms,
        # tee 캡처 귀속 (없으면 None — not_pole 등 채점 전 중단 멤버).
        "collectObservation": _COLLECT_CAP.pop(_CURRENT["key"], None),
        "seedObservation": _SEED_CAP.pop(_CURRENT["key"], None),
    }
    crit = None
    if isinstance(bd, dict):
        crit = sorted({rr.get("criterion") for rr in (bd.get("records") or [])})
    rec["activatedCriteria"] = crit
    co = rec["collectObservation"] or {}
    so = rec["seedObservation"] or {}
    _vt = co.get("vetoTelemetry") or {}
    print(
        f"  done {motion:20s} {label:7s} status={rec['status']} "
        f"overall={rec['overallScore']} crit={crit} "
        f"pointed={co.get('pointedJoints')} window={so.get('window_joints')} "
        f"wall={wall_ms}ms cacheHit={_vt.get('cacheHit')} "
        f"err={rec['errorCode'] or err or '-'}",
        flush=True,
    )
    return rec


def _pointing_fp_summary(report: list[dict]) -> dict:
    """짚기-FP율 관측 요약 (OD-2 — 관측 지표, 게이트 아님)."""
    success = [r for r in report if r["label"] == "success"]
    observed = [r for r in success if isinstance(r.get("collectObservation"), dict)]
    by_member = {}
    pointed_any = pointed_upper = 0
    for r in observed:
        pj = list((r["collectObservation"] or {}).get("pointedJoints") or ())
        upper = [j for j in pj if j in UPPER_BODY_JOINTS]
        by_member[r["motion_id"]] = {"pointed": pj, "pointedUpper": upper}
        pointed_any += 1 if pj else 0
        pointed_upper += 1 if upper else 0
    return {
        "note": "짚기-FP율 = success 멤버 중 Gemini 가 관절을 짚은 빈도 — 관측 지표"
                "(게이트 아님, OD-2). 감점 판정은 window 측정 + tol 20° 게이트 소관.",
        "successObserved": len(observed),
        "pointedAny": pointed_any,
        "pointedUpper": pointed_upper,
        "byMember": by_member,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 25 sweep (serial, in-process)")
    parser.add_argument(
        "--tag", choices=("cold", "warm"), default="cold",
        help="cold=캐시 전량 miss 1차 실행(기본) / warm=재실행(캐시 hit, *_warm.json 기록)",
    )
    args = parser.parse_args()
    suffix = "" if args.tag == "cold" else "_warm"

    # 27-02 — stage_timing INFO 로그 방출 (27-01 계측 log.info 는 핸들러 미구성 시
    # lastResort(WARNING) 에 걸러진다). eval 로그 파일에 단계별 라인 박제용.
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    from sunity_shared import firestore_admin as fa, models  # noqa: E402

    print(
        f"[setup] runId={RUNID} uid={UID} tag={args.tag} pairs={len(PAIRS)} "
        f"rtmw_deterministic={os.environ.get('RTMW_DETERMINISTIC')} "
        "(serial, in-process, tee=collect+seed)",
        flush=True,
    )
    pipeline = _load_pipeline()
    _install_tee(pipeline)

    report: list[dict] = []
    artifact: dict[str, dict] = {}

    for motion in PAIRS:
        print(f"\n[pair] {motion}", flush=True)
        fault_rec = _run_member(pipeline, fa, models, motion, "fault", _aid(motion, "Fault"))
        correct_rec = _run_member(pipeline, fa, models, motion, "success", _aid(motion, "Correct"))
        report.append(fault_rec)
        report.append(correct_rec)
        artifact[motion] = {
            "fault": fault_rec["deductionBreakdown"],
            "correct": correct_rec["deductionBreakdown"],
        }

    # ── in-run cold re-run (결정성 + criterion selection 재현 — phase24 승계) ──
    print(f"\n[cold-rerun] {COLD_RERUN_MOTION} correct (2nd, distinct id)", flush=True)
    cold = _run_member(
        pipeline, fa, models, COLD_RERUN_MOTION, "success",
        _aid(COLD_RERUN_MOTION, "ColdCorrect"),
    )
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

    fp_summary = _pointing_fp_summary(report)

    out_dir = _resolve_out_dir()  # repo 밖 — 근본원인 4 (커밋 baseline 무접촉)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"phase25_breakdowns{suffix}.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / f"phase25_sweep_report{suffix}.json").write_text(
        json.dumps(
            {
                "_meta": {
                    "phase": "25",
                    "runId": RUNID,
                    "uid": UID,
                    "tag": args.tag,
                    "captured_epoch": int(time.time()),
                    "scorer": "phase25_vision_pointed_window_merge",
                    "mode": "mode1",
                    "run": "serial in-process _process (pipeline-not-concurrency-safe-eval-serial)",
                    "tee": "collectObservation + seedObservation (read-only, at_seconds 불변)",
                    "objectivity": "fault 라벨=영상 파생. 점수=채점기 결정론 출력 스냅샷(라벨 아님).",
                },
                "results": report,
                "cold_rerun_check": cold_check,
                "pointingFpObservation": fp_summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"\n[done] wrote {out_dir}/phase25_breakdowns{suffix}.json ({len(artifact)} motions) "
        f"+ {out_dir}/phase25_sweep_report{suffix}.json (repo 밖 — 커밋 baseline 무접촉)",
        flush=True,
    )

    # 관찰 요약 (belle 검증 — pass/fail 게이트 아님. 게이트는 assert_gates.py).
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
    print(
        f"pointing-FP: success {fp_summary['successObserved']} 관측 — any "
        f"{fp_summary['pointedAny']} / upper {fp_summary['pointedUpper']} (관측만)",
        flush=True,
    )
    print("ALLDONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
