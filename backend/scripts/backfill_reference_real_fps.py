"""기준 doc 에 angles 축의 **실측 rate** 를 심는다 (quick-260810-e4v U3).

왜: 기준 doc 의 `keypointReport.fps` 는 재처리 때 **요청한** target_fps(18.0)이고 실제
산출 rate 가 아니다. `frame_extractor.extract` 가 정수 step 으로 솎으므로 30fps 원본에
target 18 이면 step 2 → ~14.93fps. 이 라벨이 `ref_boundary_step_mask` 의 마진
`ceil(0.5s × fps)` 로 들어가 9 프레임(=0.60초)을 제외해 왔다 — 의도는 0.5초(8 프레임).

무엇을 쓰나: **top-level doc** 에 `anglesRealFps`(신규 필드) 하나만 set(merge).
기존 필드·`versions/{v}` 문서·`activeVersion`·`_release` 무접촉. `get_reference_motion`
은 버전 doc 의 필드를 top-level 위에 overlay 하는데 버전 doc 에는 이 키가 없으므로
top-level 값이 그대로 읽힌다. 파이프라인은 이 필드가 있으면 쓰고 없으면 종전 라벨로
fail-open 하므로, **이 스크립트를 돌리는 것이 점수가 움직이는 스위치**다.

값의 유도: 정본은 `effective_fps(src_fps, 라벨) = src_fps / 정수 step` 이다 — 그것이
`extract()` 의 실제 규칙이다. 교차 검증은 `(anglesFrames − 1) / 영상 실길이` 로 한다:
**−1 은 강제 마지막 프레임**(영상 끝 잔여 1장 추가 규칙, 12-deferred §12-B)이다. 이걸
빼지 않으면 유도값이 항상 조금 크고, 짧은 클립에서 그 편향이 커진다(1차 dry-run 에서
ref-peter-pan 8.6초가 1.56% 로 fail-closed 에 걸려 드러났다 — 게이트가 내 식을 잡았다).
두 값이 1% 이상 벌어지면 그 doc 은 **쓰지 않는다**(fail-closed).

실행:
  # 계산·대조만 (쓰기 없음) — 먼저 이걸로 점수표를 만든다
  FIREBASE_SA_PATH=../firebase-sa.json python backfill_reference_real_fps.py --dry-run
  # 실제 기록 (belle 승인 후)
  FIREBASE_SA_PATH=../firebase-sa.json python backfill_reference_real_fps.py --write
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared" / "python"))

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis.frame_extractor import effective_fps  # noqa: E402

BUCKET = "sunity-motion-pilot-videos"
TOLERANCE = 0.01          # 두 유도 값의 허용 상대차 — 넘으면 쓰지 않는다
FIELD = "anglesRealFps"


def probe(path: Path) -> tuple[float, float]:
    """(src_fps, duration) — ffprobe 실측."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate", "-show_entries", "format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    num, den = j["streams"][0]["avg_frame_rate"].split("/")
    return float(num) / float(den), float(j["format"]["duration"])


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="계산·대조만 (쓰기 없음)")
    g.add_argument("--write", action="store_true", help="Firestore 에 기록")
    ap.add_argument("--motions", nargs="*", help="특정 motionId 만 (기본 = 전체)")
    args = ap.parse_args()

    db = fa._db()
    docs = list(db.collection("reference").stream()) \
        if not args.motions else \
        [db.collection("reference").document(m).get() for m in args.motions]

    print(f"{'motionId':<26}{'프레임':>7}{'라벨':>7}{'실길이':>9}{'(n-1)/길이':>11}"
          f"{'step 유도':>10}{'차':>7}  판정")
    rows, writes = [], []
    for snap in docs:
        d = snap.to_dict() or {}
        mid = snap.id
        n = d.get("anglesFrames")
        label = ((d.get("keypointReport") or {}).get("fps"))
        if not (isinstance(n, int) and n > 0 and isinstance(label, (int, float))
                and label > 0):
            print(f"{mid:<26}  메타 미비(anglesFrames/fps) — 건너뜀")
            continue
        key = f"reference/{mid}.mp4"
        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / f"{mid}.mp4"
            try:
                fa_s3 = __import__("boto3").client("s3")
                fa_s3.download_file(BUCKET, key, str(local))
                src_fps, dur = probe(local)
            except Exception as e:  # noqa: BLE001 — 영상 미확보 = 쓰지 않는다
                print(f"{mid:<26}  영상 확보 실패({type(e).__name__}) — 건너뜀")
                continue
        # 교차 검증 — 강제 마지막 프레임 1장 제외(그 1장은 rate 표본이 아니다)
        by_dur = (n - 1) / dur
        by_step = effective_fps(src_fps, float(label))
        if by_step is None:
            print(f"{mid:<26}  step 유도 불가 — 건너뜀")
            continue
        rel = abs(by_dur - by_step) / by_step
        ok = rel <= TOLERANCE
        print(f"{mid:<26}{n:>7}{float(label):>7.1f}{dur:>8.2f}s{by_dur:>11.3f}"
              f"{by_step:>10.3f}{rel*100:>6.2f}%  {'기록' if ok else '★불일치 — 미기록'}")
        rows.append((mid, n, float(label), dur, by_dur, by_step, ok))
        if ok:
            # 기록값 = 정본(step 유도). by_dur 은 교차 검증용이다.
            writes.append((mid, round(by_step, 4)))

    print(f"\n대상 {len(rows)}건 / 기록 후보 {len(writes)}건 "
          f"(불일치 {len(rows)-len(writes)}건은 fail-closed 로 제외)")
    if args.dry_run:
        print("\n--dry-run — Firestore 쓰기 없음. 점수표를 belle 께 낸 뒤 --write.")
        for mid, v in writes:
            print(f"  {mid}: {FIELD} = {v}")
        return 0

    for mid, v in writes:
        db.collection("reference").document(mid).set({FIELD: v}, merge=True)
        print(f"  wrote {mid}.{FIELD} = {v}")
    print(f"\n기록 {len(writes)}건 완료 — 이제 파이프라인이 실측 rate 를 쓴다 "
          "(마진 9 → 8 프레임). 다음 분석부터 점수가 움직인다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
