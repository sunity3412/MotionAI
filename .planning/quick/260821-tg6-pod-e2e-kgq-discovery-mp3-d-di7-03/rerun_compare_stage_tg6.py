"""tg6 no-write 재구동 하네스 (수정판) — backend/scripts/rerun_compare_stage.py 의
FA 스텁 결함을 우회한다 (Deviation Rule 3, backend/ 무접촉).

원 드라이버(jix 시절)의 no-write 배선은 `papp.firestore_admin` 을
`update_analysis_rendered_compare` 하나만 가진 FA 스텁으로 **통째 교체**한다.
quick-260814-ghs 가 스테이지에 추가한 읽기 호출
`firestore_admin.get_analysis_discovery(uid, analysis_id)` (app.py:4256)가
이 스텁에 없어 AttributeError -> 스테이지 fail-open 으로 조달이 통째 스킵된다
(tg6 round 1 실측: rerun_pdshape_round1_harness_defect.log).

수정 = 읽기 전건 실통과 + `update_analysis_rendered_compare` 만 차단하는
__getattr__ 위임 프록시. 프로덕션 코드 경로는 그대로 — 측정 기구만 고친다.
출력 메시지 문구는 원 드라이버와 동일 (게이트 grep 호환).

Pod 실행 (원 드라이버와 동일 env):
    cd /workspace/SunityMotion && source /workspace/aws_env.sh && \
    /usr/bin/python3 /tmp/rerun_compare_stage_tg6.py \
      --uid <uid> --analysis-id <analysisId>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

BACKEND = Path("/workspace/SunityMotion/backend")
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ORT CUDA 프로바이더 파리티 (원 드라이버 주석 그대로 — torch 프리로드)
try:
    import torch  # noqa: F401 - cudnn 프리로드 전용
except Exception:  # noqa: BLE001 - torch 부재 = CPU 폴백 (경고는 ORT 가 출력)
    pass

from sunity_shared import firestore_admin  # noqa: E402
from sunity_shared.analysis import compare_verify  # noqa: E402


def _load_pipeline_app():
    path = BACKEND / "functions" / "pipeline" / "app.py"
    name = "pipeline_app_rerun_compare_stage_tg6"
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


class FAReadPassthroughProxy:
    """firestore_admin 읽기 전건 실통과 — update_analysis_rendered_compare 만 차단.

    원 드라이버의 type('FA', ...) 스텁 대체물. get_analysis_discovery 등 ghs 가
    추가한 읽기 경로가 실 모듈로 위임되어 운영 배선이 그대로 돈다.
    """

    def __init__(self, real, capture):
        self._real = real
        self._capture = capture

    def __getattr__(self, name):
        if name == "update_analysis_rendered_compare":
            return self._capture
        return getattr(self._real, name)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uid", required=True)
    ap.add_argument("--analysis-id", required=True)
    ap.add_argument("--outdir", type=Path, default=None)
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

    # ── 원본/기준 영상 회수 (outdir 캐시) ────────────────────────────────
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

    # ── no-write 배선 (항상 no-write — --write 없음) ──────────────────────
    updates: list[dict] = []
    papp._s3 = NoWriteS3Proxy(s3)

    def _capture_update(uid, analysis_id, key, status, freezes=None):
        payload = {"status": status, "key": key}
        if freezes is not None:
            payload["freezes"] = list(freezes)
        firestore_admin._validate_rendered_compare(payload)
        updates.append(payload)
        print(f"[no-write] doc 마킹 차단: status={status} key={key!r} "
              f"freezes={len(freezes) if freezes else 0}건")

    papp.firestore_admin = FAReadPassthroughProxy(firestore_admin, _capture_update)

    # ── verify 래핑 — PASS/FAIL 무관 산출물을 outdir 로 복사 ─────────────
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
    print(f"[no-write] 차단된 마킹: {updates}")
    sys.exit(0 if (rig and rig[-1][0]) else 1)


if __name__ == "__main__":
    main()
