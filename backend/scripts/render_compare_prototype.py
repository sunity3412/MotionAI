"""Phase 35 — 서버측 정렬 합성 비교 영상 렌더러 (프로토타입 CLI 래퍼).

본체는 sunity_shared.analysis.compare_render 로 이동 (quick-260808-jix 라이브러리화
— byte-보존 게이트: 같은 입력에 이동 전과 byte-동일 산출). 이 스크립트는 argparse
+ 라이브러리 호출만 남긴 얇은 래퍼다. 운영 경로는 pipeline
`_run_deferred_compare_render` 사후 스테이지 (같은 render() 를 dict 입력으로 호출).

실행 (로컬 프로토):
    cd backend && .venv/bin/python scripts/render_compare_prototype.py \
      --doc-json <analysis doc json> --user-video u.mp4 --ref-video r.mp4 \
      --audio-dir <mp3 dir: {rid}.mp3> --workdir <scratch> --out out.mp4
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sunity_shared.analysis.compare_render import render  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-json", required=True, type=Path)
    ap.add_argument("--user-video", required=True, type=Path)
    ap.add_argument("--ref-video", required=True, type=Path)
    ap.add_argument("--audio-dir", required=True, type=Path)
    ap.add_argument("--workdir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--moments-json", type=Path, default=None)
    ap.add_argument("--align-json", type=Path, default=None)
    ap.add_argument("--text-override-json", type=Path, default=None,
                    help="rid→문장 오버라이드 (자막·음성 공용 단일 테이블)")
    ap.add_argument("--pair-override-json", type=Path, default=None,
                    help="rid→{refVideoSec, note} 명시 기준 정지 (자동 판정보다 우선, pairSrc=override)")
    ap.add_argument("--probe", action="store_true",
                    help="발동 집합 dry-run — 렌더 없이 record→경로 표만 출력")
    args = ap.parse_args()
    report = render(args.doc_json, args.user_video, args.ref_video,
                    args.audio_dir, args.workdir, args.out, args.moments_json,
                    args.align_json, args.text_override_json, args.probe,
                    args.pair_override_json)
    if not args.probe:
        print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
