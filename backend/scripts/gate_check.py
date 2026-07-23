"""gate_check.py — JSON 데이터 게이트 (grep-for-a-word 게이트 은퇴).

codex concern 8: 다운스트림 검증이 `grep -q PASS evidence.md || echo OK` 처럼
**문서가 단어 PASS 를 포함하기만 하면** 통과한다 — 안에 FAIL 항목이 있어도 샌다.
33-05 의 trailing `|| echo ... OK` 도 같은 결함(실패해도 0 종료).

gate_check 는 산문을 grep 하지 않는다. **구조화된 JSON 을 파싱**해, 호출자가
명명한 단언이 성립할 때만 0 을 반환한다. 종료 코드가 곧 게이트다.

모드 (결합 가능 — 하나라도 실패하면 non-zero):
  --require-all-pass K [K ...]      명명된 각 항목의 status 가 정확히 "PASS"
  --require-hashes N                perDocHashes 가 N 개 present + 전부 non-empty
  --no-rollback-trigger             rollback-trigger 플래그가 하나도 True 가 아님
  --scoring-constants-match P.json  tol/slope/cap/epsilon 이 pinned 매니페스트와 동일
                                    (D-20/D-29 불변식을 grep 이 아니라 데이터로 강제)

채점 무접촉 — 이 스크립트는 채점 코드를 import 하지 않는다. scoring-constants 모드는
JSON↔JSON 값 비교일 뿐이다(코드 상수 재fit 여부를 데이터로 잡는다).
"""

from __future__ import annotations

import argparse
import json
import sys

# scoring-constants 모드가 대조하는 정식 상수 키 — 실제 요구 키 집합은 pinned JSON
# 이 소유한다(pinned 에 있는 키는 전부 --file 에서 동일해야 함). 참고용 기본 목록.
CANONICAL_SCORING_KEYS: tuple[str, ...] = (
    "tol",
    "slope",
    "cap",
    "MEAN_EPSILON_DEG",
    "P99_EPSILON_DEG",
)


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_item_status(data: dict, name: str):
    """명명된 항목의 status 문자열을 찾는다 (없으면 None).

    지원 형상:
      · 최상위 dict:  {"itemA": {"status": "PASS"}}  또는  {"itemA": "PASS"}
      · 리스트 컨테이너: {"items"|"checks": [{"name": "itemA", "status": "PASS"}, ...]}
    """
    if name in data:
        val = data[name]
        if isinstance(val, dict):
            return val.get("status")
        if isinstance(val, str):
            return val
        return None
    for container_key in ("items", "checks", "results"):
        container = data.get(container_key)
        if isinstance(container, list):
            for entry in container:
                if isinstance(entry, dict) and entry.get("name") == name:
                    return entry.get("status")
    return None


def _check_all_pass(data: dict, names: list[str]) -> list[str]:
    problems: list[str] = []
    for name in names:
        status = _resolve_item_status(data, name)
        if status is None:
            problems.append(f"all-pass: 항목 {name!r} 부재")
        elif status != "PASS":
            problems.append(f"all-pass: 항목 {name!r} status={status!r} (PASS 아님)")
    return problems


def _check_hashes(data: dict, expected_n: int) -> list[str]:
    hashes = data.get("perDocHashes")
    if not isinstance(hashes, dict):
        return ["require-hashes: perDocHashes dict 부재"]
    problems: list[str] = []
    if len(hashes) != expected_n:
        problems.append(
            f"require-hashes: perDocHashes 개수 {len(hashes)} != 기대 {expected_n}"
        )
    for key, val in hashes.items():
        if not isinstance(val, str) or not val:
            problems.append(f"require-hashes: perDocHashes[{key}] 빈/비문자열")
    return problems


def _check_no_rollback_trigger(data: dict) -> list[str]:
    problems: list[str] = []
    triggers = data.get("rollbackTriggers")
    if isinstance(triggers, dict):
        for name, val in triggers.items():
            if val:
                problems.append(f"no-rollback-trigger: {name} == {val!r} (트리거 발동)")
    elif isinstance(triggers, list):
        for entry in triggers:
            if isinstance(entry, dict) and entry.get("triggered"):
                problems.append(
                    f"no-rollback-trigger: {entry.get('name', entry)} 발동"
                )
    # 최상위 단일 bool 형상도 지원.
    if data.get("rollbackTriggered"):
        problems.append("no-rollback-trigger: rollbackTriggered == True")
    return problems


def _check_scoring_constants(data: dict, pinned_path: str) -> list[str]:
    """pinned 매니페스트에 있는 모든 상수 키가 --file 에서 동일값인지 검사.

    pinned 가 요구 키 집합의 단일 출처다 — pinned 의 키가 --file 에 없거나 값이
    다르면 drift 로 판정(D-20/D-29: 채점 상수 재fit 금지).
    """
    pinned = _load(pinned_path)
    problems: list[str] = []
    if not isinstance(pinned, dict) or not pinned:
        return [f"scoring-constants: pinned {pinned_path} 비어있음/형식 오류"]
    for key, want in pinned.items():
        if key not in data:
            problems.append(f"scoring-constants: {key} 부재 (pinned={want!r})")
            continue
        got = data[key]
        # bool 은 int 와 구분해 엄격 비교 (True==1 회피).
        if isinstance(want, bool) or isinstance(got, bool):
            if want is not got and want != got:
                problems.append(f"scoring-constants: {key} drift ({got!r} != {want!r})")
            continue
        if got != want:
            problems.append(f"scoring-constants: {key} drift ({got!r} != {want!r})")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gate_check",
        description="JSON 데이터 게이트 — 명명된 단언이 성립할 때만 0 종료.",
    )
    parser.add_argument("--file", required=True, help="검사 대상 JSON evidence/manifest")
    parser.add_argument(
        "--require-all-pass",
        nargs="+",
        metavar="ITEM",
        help="명명된 각 항목의 status 가 정확히 PASS",
    )
    parser.add_argument(
        "--require-hashes",
        type=int,
        metavar="N",
        help="perDocHashes 가 N 개 present + 전부 non-empty",
    )
    parser.add_argument(
        "--no-rollback-trigger",
        action="store_true",
        help="rollback-trigger 플래그가 하나도 True 가 아님",
    )
    parser.add_argument(
        "--scoring-constants-match",
        metavar="PINNED.json",
        help="tol/slope/cap/epsilon 이 pinned 매니페스트와 동일 (D-20/D-29)",
    )
    args = parser.parse_args(argv)

    try:
        data = _load(args.file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"gate_check: --file 로드 실패: {exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("gate_check: --file 최상위가 JSON object 가 아님", file=sys.stderr)
        return 2

    requested = (
        args.require_all_pass
        or args.require_hashes is not None
        or args.no_rollback_trigger
        or args.scoring_constants_match
    )
    if not requested:
        print("gate_check: 최소 1개 게이트 모드를 지정해야 함", file=sys.stderr)
        return 2

    problems: list[str] = []
    if args.require_all_pass:
        problems += _check_all_pass(data, args.require_all_pass)
    if args.require_hashes is not None:
        problems += _check_hashes(data, args.require_hashes)
    if args.no_rollback_trigger:
        problems += _check_no_rollback_trigger(data)
    if args.scoring_constants_match:
        problems += _check_scoring_constants(data, args.scoring_constants_match)

    if problems:
        print("gate_check FAIL:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("gate_check PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
