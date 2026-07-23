"""dump_scoring_constants.py — 채점 상수 live 덤프 (33-05 scoring-untouched 데이터 게이트).

kismam 코드에서 채점 상수를 **직접 읽어** JSON 으로 방출한다. 감점 산식 상수(tol/slope)
를 코드가 바꾸면 이 덤프가 pinned 매니페스트(tests/phase33/scoring_constants_pinned.json)
와 drift → gate_check.py --scoring-constants-match 가 non-zero 로 게이트한다.

codex concern 8 대응: 산문 grep 이나 trailing `|| echo ... OK` 가 아니라, live 코드값 ↔
pinned 값의 **데이터 비교 + 종료 코드**로 D-20/D-29 불변식을 강제한다.

cap/MEAN_EPSILON_DEG/P99_EPSILON_DEG 는 정렬 게이트/판정 문서 상수(코드 리터럴 아님)로,
pinned 와 동일 값을 그대로 방출한다. tol/slope 만 live 코드에서 파생된다.

사용:
  python3 scripts/dump_scoring_constants.py            # stdout 으로 JSON
  python3 scripts/dump_scoring_constants.py -o out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_LAYER = _BACKEND / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared.analysis import kismam  # noqa: E402


def current_scoring_constants() -> dict:
    """kismam 코드에서 직접 읽은 채점 상수 dict."""
    return {
        "tol": kismam._IPSF_TOLERANCE_DEG,
        "slope": kismam._PENALTY_PER_DEG,
        "cap": 90,
        "MEAN_EPSILON_DEG": 0.1,
        "P99_EPSILON_DEG": 1.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dump_scoring_constants")
    parser.add_argument("-o", "--out", help="출력 파일 경로 (없으면 stdout)")
    args = parser.parse_args(argv)
    payload = json.dumps(current_scoring_constants(), ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
