"""Phase 35 (quick-260808-jix 실 E2E 라운드) — 실분석 doc 로 compare_render 스테이지 단독 재구동.

Pod 진단 드라이버: Firestore 의 실분석 doc(analysisId)을 읽어 pipeline
`_run_deferred_compare_render` 를 그대로 1회 재구동한다 — S3 원본 영상·기준 영상·
코칭 mp3 실회수 + 실 GPU align + 렌더 + 리그.

**기본 = 비-쓰기 (no-write)**: doc 마킹 0, S3 mp4 업로드 0 — 렌더+리그만.
리그 FAIL 이면 스테이지의 아티팩트 보존(/tmp/compare_fail_{analysisId})이 발동하고,
드라이버도 verify 직전 산출물(mp4·report.json·align.json)을 --outdir 로 복사해
이중으로 남긴다 (scp 회수 → 로컬 진단: 렌더·리그는 CPU 라 align.json 만 있으면
로컬 반복 가능 — Pod 유휴 최소화).

`--write`: 실 스테이지 그대로 — 리그 ALL PASS 시 S3 업로드 + doc renderedCompare
done 마킹 (재검증 통과 후 1회용).

Pod 실행:
    cd /workspace/SunityMotion && source /workspace/aws_env.sh && \
    python3 backend/scripts/rerun_compare_stage.py \
      --uid <uid> --analysis-id <analysisId>
(RTMW env 는 /workspace/start_server.sh 상단과 동일하게 — YOLOX_ONNX_PATH/
RTMW_ONNX_PATH 실파일이어야 능력 프로브 통과. FIREBASE_SA_* env 필요.)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ORT CUDA 프로바이더 파리티 — 운영 스테이지는 서버 프로세스(torch 로드됨) 안에서
# 돌아 onnxruntime 이 torch 동봉 cudnn 을 찾는다. 드라이버가 torch 없이 돌면
# libcudnn.so.9 미발견 → CPU 폴백으로 align 이 달라진다 (실측: E 13% vs 28%).
# 서버 등가 조건을 위해 선로드 (없으면 CPU — 로그로 판별 가능).
try:
    import torch  # noqa: F401 - cudnn 프리로드 전용
except Exception:  # noqa: BLE001 - torch 부재 = CPU 폴백 (경고는 ORT 가 출력)
    pass

from sunity_shared import firestore_admin  # noqa: E402
from sunity_shared.analysis import compare_verify  # noqa: E402


def _load_pipeline_app():
    path = BACKEND / "functions" / "pipeline" / "app.py"
    name = "pipeline_app_rerun_compare_stage"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class NoWriteS3Proxy:
    """download_file 은 실통과, put_object 만 차단 (no-write — 업로드 0)."""

    def __init__(self, real):
        self._real = real
        self.blocked_puts: list[str] = []

    def download_file(self, *a, **k):
        return self._real.download_file(*a, **k)

    def put_object(self, **kwargs):
        body = kwargs.pop("Body", None)
        if hasattr(body, "read"):
            body.read()  # 소비만 (파일 핸들 계약 유지)
        self.blocked_puts.append(kwargs.get("Key", ""))
        print(f"[no-write] S3 put_object 차단: {kwargs.get('Key')}")
        return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uid", required=True)
    ap.add_argument("--analysis-id", required=True)
    ap.add_argument("--write", action="store_true",
                    help="실 마킹+업로드 (기본 = 비-쓰기: 렌더+리그만)")
    ap.add_argument("--outdir", type=Path, default=None,
                    help="아티팩트 복사 경로 (기본 /tmp/compare_rerun_{analysisId})")
    ap.add_argument("--bucket", default=os.environ.get("VIDEO_BUCKET", "sunity-motion-pilot-videos"))
    args = ap.parse_args()

    outdir = args.outdir or Path(f"/tmp/compare_rerun_{args.analysis_id}")
    outdir.mkdir(parents=True, exist_ok=True)

    papp = _load_pipeline_app()

    # ── doc 회수 (읽기 전용) ──────────────────────────────────────────────
    doc = firestore_admin.get_analysis(args.uid, args.analysis_id)
    if not doc:
        print(f"ERROR: doc 없음 uid={args.uid} analysis_id={args.analysis_id}", file=sys.stderr)
        sys.exit(2)
    json.dump(doc, open(outdir / "doc.json", "w"), ensure_ascii=False, default=str)
    result = dict(doc.get("result") or {})
    mode = doc.get("mode")
    kp = result.get("keypointReport")
    if kp is None:
        print("ERROR: result.keypointReport 없음", file=sys.stderr)
        sys.exit(2)
    coach_audio = result.get("coachAudio") or {}
    items = coach_audio.get("items") or []
    records = (result.get("deductionBreakdown") or {}).get("records") or []
    print(f"doc OK mode={mode} records={len(records)} coachAudio items={len(items)} "
          f"renderedCompare(현재)={result.get('renderedCompare')}")

    # ── 원본/기준 영상 회수 (outdir 캐시 — 재실행 시 S3 GET 절약) ─────────
    s3 = papp._s3
    user_key = result.get("myVideoKey")
    if not user_key:
        print("ERROR: result.myVideoKey 없음", file=sys.stderr)
        sys.exit(2)
    user_mp4 = outdir / "user.mp4"
    if not user_mp4.exists():
        print(f"S3 GET {user_key} -> {user_mp4}")
        s3.download_file(args.bucket, user_key, str(user_mp4))

    ref_id = (result.get("comparison") or {}).get("referenceMotionId")
    if not ref_id:
        print("ERROR: comparison.referenceMotionId 없음 (mode1 아님?)", file=sys.stderr)
        sys.exit(2)
    ref_doc = firestore_admin.get_reference_motion(ref_id) or {}
    ref_key = ref_doc.get("videoS3Key")
    if not ref_key:
        print(f"ERROR: reference/{ref_id} videoS3Key 없음", file=sys.stderr)
        sys.exit(2)
    ref_mp4 = outdir / "ref.mp4"
    if not ref_mp4.exists():
        print(f"S3 GET {ref_key} -> {ref_mp4}")
        s3.download_file(args.bucket, ref_key, str(ref_mp4))

    # ── no-write 배선 ─────────────────────────────────────────────────────
    updates: list[dict] = []
    if not args.write:
        papp._s3 = NoWriteS3Proxy(s3)

        def _capture_update(uid, analysis_id, key, status):
            firestore_admin._validate_rendered_compare({"status": status, "key": key})
            updates.append({"key": key, "status": status})
            print(f"[no-write] doc 마킹 차단: status={status} key={key!r}")

        papp.firestore_admin = type(
            "FA", (), {"update_analysis_rendered_compare": staticmethod(_capture_update)}
        )()

    # ── verify 래핑 — PASS/FAIL 무관 산출물을 outdir 로 복사 (정리 전) ────
    rig: list[tuple[bool, list[str]]] = []
    real_verify = compare_verify.verify

    def _capture_verify(mp4, report, workdir, **kw):
        ok, lines = real_verify(mp4, report, workdir, **kw)
        rig.append((ok, lines))
        try:
            shutil.copyfile(mp4, outdir / "compare.mp4")
            json.dump(report, open(outdir / "report.json", "w"), ensure_ascii=False, indent=1)
            wa = Path(workdir) / "align.json"
            if wa.exists():
                shutil.copyfile(wa, outdir / "align.json")
        except Exception as e:  # noqa: BLE001 - 복사 실패는 판정 무영향
            print(f"[warn] 아티팩트 복사 실패: {e}", file=sys.stderr)
        return ok, lines

    compare_verify.verify = _capture_verify

    # ── 실 스테이지 재구동 ────────────────────────────────────────────────
    papp._run_deferred_compare_render(
        result=result,
        keypoint_report_dict=kp,
        coach_audio_items=items,
        mode=mode,
        uid=args.uid,
        analysis_id=args.analysis_id,
        bucket=args.bucket,
        local_video_path=str(user_mp4),
        reference_local_video_path=str(ref_mp4),
    )

    # ── 판정 출력 ─────────────────────────────────────────────────────────
    if rig:
        ok, lines = rig[-1]
        print(f"리그: {'ALL PASS' if ok else 'FAIL'}")
        print("\n".join(lines))
    else:
        print("리그: 미도달 (align/렌더 단계 실패 — 보존 경로/로그 확인)")
    fail_dir = Path(f"/tmp/compare_fail_{args.analysis_id}")
    print(f"아티팩트: {outdir} (doc/align/report/compare.mp4)"
          + (f" + FAIL 보존 {fail_dir}" if fail_dir.exists() else ""))
    if not args.write:
        print(f"[no-write] 차단된 마킹: {updates}")
    sys.exit(0 if (rig and rig[-1][0]) else 1)


if __name__ == "__main__":
    main()
