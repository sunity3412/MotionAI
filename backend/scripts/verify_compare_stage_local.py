"""Phase 35 (quick-260808-jix) — compare_render 사후 스테이지 로컬 검증 리허설.

pipeline `_run_deferred_compare_render` 의 **실제 스테이지 함수 경로**를 GPU 없이
로컬에서 끝까지 태운다 (fixture align 주입) — 게이트·mp3 회수·렌더·리그·업로드·
doc 마킹의 전 배선이 실제 코드로 실행되는지의 리허설. 판정 = 리그(compare_verify)
ALL PASS + done 마킹이면 exit 0.

이중 용도 (SUMMARY "Pod 재가동 시 검증 절차" 가 이 스크립트를 지목):
  · 기본 (로컬, GPU 없음): compare_align.build_align 을 픽스처 align.json 반환
    스텁으로 치환 — GPU 추출부만 skip, 나머지 전 경로 실코드.
  · --build-align (Pod, GPU): 스텁 없이 실 build_align 실행 — 실 GPU align 경유
    end-to-end 리허설 (rtmlib+가중치 필요. 능력 프로브도 실판정).

스텁 대상 (외부 부수효과만):
  · papp._s3 — download_file 은 로컬 audio 디렉터리 복사, put_object 는 캡처
    (업로드 바이트를 --out 으로 저장해 사람이 열어볼 수 있게).
  · firestore_admin.update_analysis_rendered_compare — 캡처 (단, 실 validator
    _validate_rendered_compare 는 통과시킨다 — 계약 위반이면 여기서 터진다).
  · compare_verify.verify — 실 verify 를 그대로 호출하되 (ok, lines) 를 캡처해
    stdout 에 리그 표를 출력.

실행:
    backend/.venv/bin/python backend/scripts/verify_compare_stage_local.py \
      --motion elbow --sp <scratchpad p35 루트>
    (--sp 생략 시 SUNITY_P35_SP env → 그것도 없으면 에러)
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
REPO = BACKEND.parent
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sunity_shared import firestore_admin, models  # noqa: E402
from sunity_shared.analysis import compare_align, compare_verify  # noqa: E402
from sunity_shared.s3keys import build_coach_audio_key  # noqa: E402

DATA_DEFAULT = REPO / ".planning" / "phases" / "35-server-rendered-comparison-video" / "data"
UID = "localverify"
ANALYSIS_ID = "a" * 32


def _load_pipeline_app():
    """pipeline app.py 를 파일 경로 spec 로드 (tests 관례 — 'app' 모듈명 충돌 회피)."""
    path = BACKEND / "functions" / "pipeline" / "app.py"
    name = "pipeline_app_compare_stage_local"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeS3:
    """S3 스텁 — download_file 은 로컬 audio 복사, put_object 는 캡처+저장."""

    def __init__(self, audio_dir: Path, out_mp4: Path):
        self.audio_dir = audio_dir
        self.out_mp4 = out_mp4
        self.puts: list[str] = []

    def download_file(self, _bucket: str, key: str, dst: str) -> None:
        # key = results/{uid}/{aid}/coach_audio_{rid}:{criterion}.mp3 → r{NN}.mp3
        base = key.rsplit("coach_audio_", 1)[-1]
        rid = base.split(":")[0]
        src = self.audio_dir / f"{rid}.mp3"
        if not src.exists():
            raise FileNotFoundError(f"로컬 mp3 없음: {src} (key={key})")
        shutil.copyfile(src, dst)

    def put_object(self, *, Bucket: str, Key: str, Body, ContentType: str) -> dict:  # noqa: N803
        self.puts.append(Key)
        self.out_mp4.parent.mkdir(parents=True, exist_ok=True)
        with open(self.out_mp4, "wb") as fh:
            shutil.copyfileobj(Body, fh)
        return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--motion", default="elbow")
    ap.add_argument("--data-dir", type=Path, default=DATA_DEFAULT,
                    help="doc.json/align.json 픽스처 루트 (기본 = .planning p35 data)")
    ap.add_argument("--sp", type=Path, default=None,
                    help="user.mp4/ref.mp4/audio 가 있는 p35 스크래치 루트 "
                         "({sp}/{motion}/...). 생략 시 SUNITY_P35_SP env")
    ap.add_argument("--out", type=Path, default=None,
                    help="업로드 캡처 mp4 저장 경로 (기본 {sp}/{motion}/out_stage_local.mp4)")
    ap.add_argument("--build-align", action="store_true",
                    help="픽스처 align 스텁 없이 실 build_align (Pod GPU 리허설)")
    args = ap.parse_args()

    sp = args.sp or (Path(os.environ["SUNITY_P35_SP"]) if os.environ.get("SUNITY_P35_SP") else None)
    if sp is None:
        print("ERROR: --sp 또는 SUNITY_P35_SP env 필요 (user/ref mp4·audio 위치)", file=sys.stderr)
        sys.exit(2)

    mdir = sp / args.motion
    ddir = args.data_dir / args.motion
    doc = json.load(open(ddir / "doc.json"))
    result = dict(doc["result"])
    # 스테이지 계약 재현 — keypointReport 는 complete_analysis kwarg 라 in-memory
    # result 에 없다. doc.json 에서 분리해 스테이지 kwarg 로 따로 전달.
    keypoint_report = result.pop("keypointReport", None)
    if keypoint_report is None:
        print("ERROR: doc.json 에 result.keypointReport 없음", file=sys.stderr)
        sys.exit(2)

    records = result.get("deductionBreakdown", {}).get("records", [])
    audio_dir = mdir / "audio"
    coach_audio_items = []
    for rec in records:
        rid_full = rec.get("recordId", "")
        rid = rid_full.split(":")[0]
        if rid and (audio_dir / f"{rid}.mp3").exists():
            coach_audio_items.append(
                {"recordId": rid_full, "key": build_coach_audio_key(UID, ANALYSIS_ID, rid_full)}
            )

    out_mp4 = args.out or (mdir / "out_stage_local.mp4")

    papp = _load_pipeline_app()

    # ── 스텁 배선 ──────────────────────────────────────────────────────────
    fake_s3 = FakeS3(audio_dir, out_mp4)
    papp._s3 = fake_s3

    updates: list[dict] = []

    def _capture_update(uid, analysis_id, key, status, freezes=None):
        # 실 validator 경유 — 계약 위반이면 여기서 터진다 (스텁이 가리지 않음).
        payload = {"status": status, "key": key}
        if freezes is not None:
            payload["freezes"] = list(freezes)
        firestore_admin._validate_rendered_compare(payload)
        updates.append({"uid": uid, "analysisId": analysis_id, **payload})

    papp.firestore_admin = type(
        "FA", (), {"update_analysis_rendered_compare": staticmethod(_capture_update)}
    )()

    if args.build_align:
        # 실 build_align — 능력 프로브도 실판정 (rtmlib+가중치 필요, Pod 전용).
        pass
    else:
        # 픽스처 align 주입 — GPU 추출부만 skip (모델 로드 0), 능력 프로브 우회.
        fixture_align = json.load(open(ddir / "align.json"))
        compare_align.build_align = (  # type: ignore[assignment]
            lambda *_a, **_k: fixture_align
        )
        papp._compare_render_capability = lambda: True

    rig: list[tuple[bool, list[str]]] = []
    real_verify = compare_verify.verify

    def _capture_verify(mp4, report, workdir, **kw):
        ok, lines = real_verify(mp4, report, workdir, **kw)
        rig.append((ok, lines))
        return ok, lines

    compare_verify.verify = _capture_verify  # type: ignore[assignment]

    # ── 실 스테이지 함수 실행 ──────────────────────────────────────────────
    papp._run_deferred_compare_render(
        result=result,
        keypoint_report_dict=keypoint_report,
        coach_audio_items=coach_audio_items,
        mode=models.MODE_EXPERT,
        uid=UID,
        analysis_id=ANALYSIS_ID,
        bucket="local-verify-bucket",
        local_video_path=str(mdir / "user.mp4"),
        reference_local_video_path=str(mdir / "ref.mp4"),
    )

    # ── 판정 출력 ──────────────────────────────────────────────────────────
    print(f"motion={args.motion} mp3_items={len(coach_audio_items)} records={len(records)}")
    if rig:
        ok, lines = rig[-1]
        print(f"리그: {'ALL PASS' if ok else 'FAIL'}")
        print("\n".join(lines))
    else:
        print("리그: 미도달 (align/렌더 단계 실패 — 스테이지 로그 확인)")
    print(f"updates: {updates}")
    print(f"S3 puts: {fake_s3.puts}")
    if out_mp4.exists():
        print(f"업로드 캡처 mp4: {out_mp4} ({out_mp4.stat().st_size} bytes)")

    done = bool(updates) and updates[-1]["status"] == models.RENDERED_COMPARE_STATUS_DONE
    ok_rig = bool(rig) and rig[-1][0]
    if done and ok_rig:
        print("STAGE_LOCAL_VERIFY: PASS (리그 ALL PASS + done 마킹)")
        sys.exit(0)
    print("STAGE_LOCAL_VERIFY: FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
