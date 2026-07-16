"""Phase 29 D-02 mode3 tally 전환 sweep — serial, in-process _process, mode3 단독 분석.

phase25 harness(evals/phase25/run_sweep.py) 복제-확장 (같은 계보 3대째, 29-05 Task 1).
phase24 6페어(fixtures/phase15)를 **mode='mode3' 단독 분석**(prev 없음)으로 채점한다 —
29-02(mode3_held tally seam)/29-03(zoom 소스 교체)의 production 전환(D-02) 조건 검증.

mode3 전용 조정 (RESEARCH Pattern 5):
  · eval_keys.json 의 12 멤버를 mode=MODE_SELF, referenceMotionId 없이 분석.
  · **멤버별 고유 uid** — firestore_admin.get_previous_analysis 는 uid-scoped
    (같은 uid 안 mode3 done 문서를 prev 로 잡음) 이므로, 멤버마다 uid 를 분리해
    prev-free 첫 분석(절대 기준 채점 = D-02 본체)을 구조적으로 보장한다.
    warm 재실행도 RUNID 가 달라 prev-free.
  · not_pole 게이트는 mode3 미적용 — climb 도 채점된다 (mode1 게이트 미포함).

tee 2종 (read-only — 인자/채점 경로 무접촉, phase25 함정 ③ 승계):
  · preSeamOverall — pipeline._apply_vision_veto_from_context 진입 시점의
      score_result["overallScore"] 캡처. **이 값이 곧 '기존(구코드) 점수'다**:
      29-02 seam 은 종단 in-place 교체(방출 시 overallScore←breakdown.final)뿐이고
      미방출 경로는 byte-불변 passthrough 이므로(29-02 SUMMARY 케이스 3/7), pre-seam
      overallScore == 구코드가 저장했을 값. assert_gates 의 "기존 baseline" 비교와
      SUMMARY score-switch 대조표(29-PLAN-REVIEW MEDIUM-1)의 old 컬럼 소스.
  · mdKeys — pipeline._build_deduction_measured_deviations 반환 md 의 키 목록 캡처
      (등록/빈-criteria 판별 관측: md 빈 dict → 미방출 fallback 이 정상 — Pitfall 1).

산출물 (repo 밖 EVAL_OUT_DIR 로만 기록 — 25-SWEEP-EVIDENCE 근본원인 4):
  · $EVAL_OUT_DIR/phase29/phase29_breakdowns.json   — {motion: {correct, fault}}
  · $EVAL_OUT_DIR/phase29/phase29_sweep_report.json — rich 리포트 (score/status/
      preSeamOverall/deductionBreakdown/visionVeto/mdKeys/faultZoom 관측)
  --tag warm 실행 시 *_warm.json 으로 기록 (cold/warm 결정론 게이트 입력).
  기본 EVAL_OUT_DIR=/tmp/sunity_eval_out. repo 내 evals/*/baseline/ 은 read-only —
  sweep 이 절대 덮어쓰지 않는다 (2026-07-02 baseline 오염 사고 재발 금지).

객관성 ([[analysis-objectivity-no-human-scores]]): fault 라벨=영상 파생(OK). 점수 비교는
전부 같은 run 의 pre-seam 캡처(채점기 결정론 출력) 대비 방향/항등 비교 — 사람 점수 라벨 0.
게이트 FAIL 시 임계/criteria 수정 금지 (calibration-source-hard-gate) — 정지·보고만.

동시성 ([[pipeline-not-concurrency-safe-eval-serial]]): _process 는 동시성 비안전 — SERIAL.
한 멤버 _process 완료까지 대기 후 다음. 동시 트리거 = cross-contamination(가짜 결과).

크레딧: mode3 는 Gemini 호출이 recognizer 1회뿐 (collect 는 mode3_held 조기 bail —
Gemini 0 call). TechniqueCache(영상 hash 키, Firestore 영속)가 hit 하면 그마저 0 call.
429/resource_limited 발생 시 fail-closed 중단 후 belle 보고.

실행 (Pod, RTMW GPU + Gemini env 필요 — phase25 헤더 승계):
    source /workspace/aws_env.sh && \
    export CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key GEMINI_COACH_ENABLED=1 \
           RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx \
           YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx RTMW_DEVICE=cuda \
           FIREBASE_SA_PATH=/workspace/firebase-sa.json RECOGNIZER_BACKEND=gemini && \
    export GEMINI_API_KEY=$(python3 -c "import boto3;print(boto3.client('ssm',region_name='ap-northeast-2').get_parameter(Name='/sunity/motion/gemini-api-key',WithDecryption=True)['Parameter']['Value'])") && \
    cd /workspace/SunityMotion/backend && \
    PYTHONPATH=shared/python:. python3 evals/phase29/run_sweep.py            # cold
    PYTHONPATH=shared/python:. python3 evals/phase29/run_sweep.py --tag warm # warm 재실행

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

# ── RTMW 결정론 (Phase 25 근본원인 #2 승계) — eval 은 항상 결정론 모드 ────────
# CUDA EP conv algo flip 이 tol 경계 관절 criterion 활성을 흔든다 → 결정론 옵션 주입.
# setdefault: 운영자가 RTMW_DETERMINISTIC=0 을 명시 export 하면 그 값 우선.
# pipeline 로드(_ensure_adapters) 전에 설정돼야 하므로 module-level 주입.
os.environ.setdefault("RTMW_DETERMINISTIC", "1")

# ── Gemini vision veto env (2026-07-05 신규 pod sweep 무효화 사고 재발 방지) ──
# 이 env 가 없으면 veto/collect 경로 전체가 조용히 OFF — mode3 의 collect 조기 bail
# (mode3_held ctx) 자체가 안 돌아 tally seam 미도달 → sweep 전체 무효.
# production /workspace/start_server.sh 영구 박제 구성과 동일 값 mirror (setdefault —
# 명시 export 시 그 값 우선). pipeline 로드 전 module-level 주입.
os.environ.setdefault("GEMINI_VISION_VETO_ENABLED", "1")
os.environ.setdefault("GEMINI_MAX_VETO_WALL_S", "300")

# ── production mirror env (phase25/27 계보 승계 — 명시 export 시 그 값 우선) ──
os.environ.setdefault("GEMINI_UPLOAD_PREFETCH", "1")
os.environ.setdefault("GEMINI_MOMENT_MODEL", "gemini-3.5-flash")

# ── 산출물 경로 (25-SWEEP-EVIDENCE 근본원인 4 — repo 오염 방지) ───────────────
# 신규 산출물은 repo 밖 EVAL_OUT_DIR 로만 쓴다. repo 내 evals/*/baseline/ 은
# git 커밋본(비교 기준) 전용 read-only.
_EVAL_OUT_ENV = "EVAL_OUT_DIR"
_EVAL_OUT_DEFAULT = "/tmp/sunity_eval_out"
_PHASE_SUBDIR = "phase29"


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


RUNID = str(int(time.time()))
UID_BASE = "phase29eval"

# 현재 _process 가 트리거한 멤버 키 — tee wrapper 가 캡처를 귀속시킨다 (phase25 probe 패턴).
_CURRENT = {"key": None}
_PRESEAM_CAP: dict[str, dict] = {}
_MD_CAP: dict[str, list] = {}


def _load_keys() -> tuple[str, list[dict]]:
    data = json.loads((HERE / "eval_keys.json").read_text(encoding="utf-8"))
    return data["bucket"], list(data["items"])


def _load_pipeline():
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", str(BACKEND / "functions" / "pipeline" / "app.py")
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline


def _install_tee(pipeline) -> None:
    """read-only tee 2종 설치 — 인자/반환 무변경, 캡처만 (phase25 함정 ③ 승계)."""
    orig_apply = pipeline._apply_vision_veto_from_context

    def _apply_tee(score_result, ctx, quantification, **kwargs):
        # pre-seam overallScore = 구코드가 저장했을 값 (seam 은 종단 in-place 교체뿐 —
        # 29-02 SUMMARY 케이스 3/7). 인자 무변경으로 원본에 그대로 전달.
        try:
            md = kwargs.get("measured_deviations")
            _PRESEAM_CAP[_CURRENT["key"]] = {
                "preSeamOverall": (score_result or {}).get("overallScore"),
                "collectionStatus": getattr(ctx, "collection_status", None),
                "mdNonEmpty": bool(md),
            }
        except Exception as exc:  # noqa: BLE001 — 관측 실패는 분석 흐름 차단 0
            _PRESEAM_CAP[_CURRENT["key"]] = {
                "captureError": f"{type(exc).__name__}: {exc}"
            }
        return orig_apply(score_result, ctx, quantification, **kwargs)

    pipeline._apply_vision_veto_from_context = _apply_tee

    orig_build = pipeline._build_deduction_measured_deviations

    def _build_tee(**kwargs):
        md = orig_build(**kwargs)
        try:
            _MD_CAP[_CURRENT["key"]] = sorted(md.keys()) if isinstance(md, dict) else []
        except Exception:  # noqa: BLE001 — 관측 실패는 분석 흐름 차단 0
            _MD_CAP[_CURRENT["key"]] = []
        return md

    pipeline._build_deduction_measured_deviations = _build_tee


def _slug(motion: str, label: str) -> str:
    # analysisId/uid 는 영숫자만 — 하이픈 슬러그 금지 (phase24 HIGH 2 정합).
    return motion.replace("-", "") + ("Fault" if label == "fault" else "Correct")


def _run_member(pipeline, fa, models, bucket: str, item: dict) -> dict:
    """단일 멤버 _process 직접 호출 + Firestore 결과 readback. SERIAL (완료까지 블로킹).

    uid 를 멤버별로 분리 — get_previous_analysis(uid-scoped) 가 prev 를 못 찾게 해
    mode3 첫 분석(단독·절대 기준 채점)을 보장한다 (D-02 본체).
    """
    motion, label = item["motionId"], item["label"]
    key = item["sourceS3Key"]
    uid = UID_BASE + _slug(motion, label) + RUNID
    analysis_id = _slug(motion, label) + RUNID
    _CURRENT["key"] = f"{motion}:{label}:{analysis_id}"
    fa._doc(models.analysis_doc_path(uid, analysis_id)).set({
        "mode": models.MODE_SELF,                # mode3 = 자기 성장 (reference 없음)
        "status": "uploading",
        "createdAt": int(time.time() * 1000),
        "fileName": analysis_id + ".mp4",
        "videoKey": key,
        "sourceLabel": f"phase29_sweep:{motion}:{label}",
    })
    err = None
    _wall_t0 = time.monotonic()
    try:
        pipeline._process(bucket, key, uid, analysis_id)
    except Exception as exc:  # noqa: BLE001 — 실패는 doc 에 failed 로 기록됨
        err = f"{type(exc).__name__}: {exc}"
    wall_ms = int((time.monotonic() - _wall_t0) * 1000)

    d = fa.get_analysis(uid, analysis_id) or {}
    r = d.get("result") or {}
    ec = d.get("error")
    bd = r.get("deductionBreakdown")
    vv = r.get("visionVeto")
    preseam = _PRESEAM_CAP.pop(_CURRENT["key"], None) or {}
    zoom = r.get("faultZoomComparisons")
    zoom_obs = None
    if isinstance(zoom, list):
        zoom_obs = {
            "count": len(zoom),
            "kinds": sorted({str(z.get("kind")) for z in zoom if isinstance(z, dict)}),
            "regions": [z.get("region") for z in zoom if isinstance(z, dict)],
            "status": r.get("faultZoomStatus"),
        }
    rec = {
        "motion_id": motion,
        "label": label,
        "uid": uid,
        "analysisId": analysis_id,
        "status": d.get("status"),
        "overallScore": r.get("overallScore"),
        # score-switch 대조표 old 컬럼 + 게이트 1/3 의 "기존 baseline" 소스.
        "preSeamOverall": preseam.get("preSeamOverall"),
        "collectionStatus": preseam.get("collectionStatus"),
        "mdNonEmpty": preseam.get("mdNonEmpty"),
        "mdKeys": _MD_CAP.pop(_CURRENT["key"], None),
        "errorCode": ec.get("code") if isinstance(ec, dict) else ec,
        "exception": err,
        "deductionBreakdown": bd,
        "visionVeto": vv,
        # D-08 관찰 (게이트 외): mode3 zoom = 감점 record criterion->region, improved 0.
        "faultZoomObservation": zoom_obs,
        "timingsMs": r.get("timingsMs"),
        "wallMs": wall_ms,
    }
    crit = None
    if isinstance(bd, dict):
        crit = sorted({rr.get("criterion") for rr in (bd.get("records") or [])})
    rec["activatedCriteria"] = crit
    print(
        f"  done {motion:20s} {label:7s} status={rec['status']} "
        f"pre={rec['preSeamOverall']} overall={rec['overallScore']} crit={crit} "
        f"mdKeys={rec['mdKeys']} veto={(vv or {}).get('status') if isinstance(vv, dict) else vv} "
        f"wall={wall_ms}ms err={rec['errorCode'] or err or '-'}",
        flush=True,
    )
    return rec


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 29 mode3 sweep (serial, in-process)")
    parser.add_argument(
        "--tag", choices=("cold", "warm"), default="cold",
        help="cold=1차 실행(기본) / warm=재실행(*_warm.json 기록, 결정론 게이트 입력)",
    )
    args = parser.parse_args()
    suffix = "" if args.tag == "cold" else "_warm"

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    from sunity_shared import firestore_admin as fa, models  # noqa: E402

    bucket, items = _load_keys()
    print(
        f"[setup] runId={RUNID} tag={args.tag} members={len(items)} bucket={bucket} "
        f"rtmw_deterministic={os.environ.get('RTMW_DETERMINISTIC')} "
        "(serial, in-process, mode3 단독, tee=preSeam+mdKeys)",
        flush=True,
    )
    pipeline = _load_pipeline()
    _install_tee(pipeline)

    report: list[dict] = []
    artifact: dict[str, dict] = {}

    for item in items:  # eval_keys.json 순서 그대로 — SERIAL
        motion, label = item["motionId"], item["label"]
        print(f"\n[member] {motion} {label}", flush=True)
        rec = _run_member(pipeline, fa, models, bucket, item)
        report.append(rec)
        slot = "fault" if label == "fault" else "correct"
        artifact.setdefault(motion, {})[slot] = rec["deductionBreakdown"]

    out_dir = _resolve_out_dir()  # repo 밖 — 근본원인 4 (커밋 baseline 무접촉)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"phase29_breakdowns{suffix}.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / f"phase29_sweep_report{suffix}.json").write_text(
        json.dumps(
            {
                "_meta": {
                    "phase": "29",
                    "runId": RUNID,
                    "tag": args.tag,
                    "captured_epoch": int(time.time()),
                    "scorer": "phase29_mode3_tally_seam",
                    "mode": "mode3",
                    "run": "serial in-process _process, 멤버별 고유 uid = prev-free 단독 분석",
                    "tee": "preSeamOverall(구코드 점수) + mdKeys (read-only)",
                    "objectivity": "fault 라벨=영상 파생. 비교=pre-seam 캡처 대비 방향/항등 — 사람 점수 라벨 0.",
                },
                "results": report,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"\n[done] wrote {out_dir}/phase29_breakdowns{suffix}.json ({len(artifact)} motions) "
        f"+ {out_dir}/phase29_sweep_report{suffix}.json (repo 밖 — 커밋 baseline 무접촉)",
        flush=True,
    )

    # 관찰 요약 — score-switch 대조표 원자료 (게이트는 assert_gates.py 소관).
    print("\n=== SCORE-SWITCH OBSERVATION (old=preSeam / new=stored) ===", flush=True)
    print(
        f"{'motion':22s} | {'label':7s} | {'old':4s} | {'new':4s} | {'recs':4s} | criteria",
        flush=True,
    )
    for rec in report:
        n_rec = (
            len((rec["deductionBreakdown"] or {}).get("records") or [])
            if isinstance(rec["deductionBreakdown"], dict) else "-"
        )
        print(
            f"{rec['motion_id']:22s} | {rec['label']:7s} | {str(rec['preSeamOverall']):4s} | "
            f"{str(rec['overallScore']):4s} | {str(n_rec):4s} | {rec['activatedCriteria']}",
            flush=True,
        )
    print("ALLDONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
