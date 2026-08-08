"""Phase 35 — 합성 비교 영상 기계 판정 리그 CLI 래퍼 (돌파 ②의 첫 조각).

본체는 sunity_shared.analysis.compare_verify 로 이동 (quick-260808-jix 라이브러리화).
렌더 결과를 belle 에게 보내기 **전에** 스크립트가 판독한다 — "전 항목 PASS 아니면 전달 없음".
판정 항목(A/A2/B/C/D/E/F)·미포함 항목은 compare_verify 모듈 docstring 참조.

실행:
    .venv/bin/python scripts/verify_render_prototype.py --mp4 out.mp4 --report report.json
report 는 render_compare_prototype.py stdout JSON.
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

from sunity_shared.analysis.compare_verify import verify  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp4", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--workdir", type=Path, default=Path("/tmp/renderrig"))
    # H 진품 축 입력 (quick-260808-jix 방어 라운드) — 제공 시 산출-분석 일치 판정.
    ap.add_argument("--doc-json", type=Path, default=None)
    ap.add_argument("--align-json", type=Path, default=None)
    ap.add_argument("--text-override-json", type=Path, default=None)
    args = ap.parse_args()
    report = json.load(open(args.report))
    doc = json.load(open(args.doc_json)) if args.doc_json else None
    align = json.load(open(args.align_json)) if args.align_json else None
    overrides = json.load(open(args.text_override_json)) if args.text_override_json else None
    ok, lines = verify(args.mp4, report, args.workdir,
                       align=align, doc=doc, text_overrides=overrides)
    print(f"{args.mp4.name}: {'ALL PASS' if ok else 'FAIL'}")
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
