#!/usr/bin/env python3
"""Phase 18 deliberate-fault eval set — baseline self-consistency 검사 (pod-free).

박제 정신:
  · Phase 18 fixture(pairs.yaml + baseline 스냅샷)가 게이트 의미론을 만족하는지
    Pod/GPU 없이 검사한다. 실 Pod 재실행 대조는 Pod 재개 후 sweep_phase15.py 산출과
    이 baseline 을 비교 — 여기서는 박제된 스냅샷의 self-consistency 만 확정한다.
  · 객관성(D-06): baseline 점수는 채점기 출력 스냅샷(라벨 아님). 사람 점수 라벨 금지.

게이트 의미론:
  1. expected verdict ↔ baseline verdict 정합 (pairs.yaml ↔ baseline.json).
  2. discriminate 페어는 fault < success (margin > 0).
  3. known_false_positive / known_gate_blocked 는 명시 추적(silent 통과 금지).

exit 0 = PASS, non-zero = FAIL.
"""
from __future__ import annotations

import json
import pathlib
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML 필요: pip install pyyaml")

_HERE = pathlib.Path(__file__).resolve().parent
_PAIRS = _HERE / "dataset" / "pairs.yaml"
_BASELINE = _HERE / "baseline" / "eval18_serial_baseline.json"


def main() -> int:
    pairs_doc = yaml.safe_load(_PAIRS.read_text(encoding="utf-8"))
    baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))

    pairs = {p["motion_id"]: p for p in pairs_doc["pairs"]}
    results = {r["motion_id"]: r for r in baseline["results"]}

    failures: list[str] = []

    # 0) 페어 셋 일치
    if set(pairs) != set(results):
        failures.append(
            f"페어 셋 불일치: pairs={sorted(pairs)} baseline={sorted(results)}"
        )

    discriminating = 0
    for motion_id, pair in pairs.items():
        res = results.get(motion_id)
        if res is None:
            failures.append(f"{motion_id}: baseline 스냅샷 누락")
            continue

        expected = pair["expected"]
        verdict = res["verdict"]

        # 1) expected ↔ verdict 정합
        if expected != verdict:
            failures.append(
                f"{motion_id}: expected={expected} != baseline verdict={verdict}"
            )

        if verdict == "discriminate":
            f, s, m = res["fault_overall"], res["success_overall"], res["margin"]
            # 2) fault < success + margin 정합
            if f is None or s is None:
                failures.append(f"{motion_id}: discriminate 인데 점수 None")
            elif not (f < s):
                failures.append(f"{motion_id}: fault {f} >= success {s} (변별 실패)")
            elif m != (s - f):
                failures.append(f"{motion_id}: margin {m} != success-fault {s - f}")
            else:
                discriminating += 1

        elif verdict == "known_false_positive":
            # 3) 위양성 = 변별 안 됨(margin 0)이 명시돼야 함
            if res.get("margin") not in (0, None):
                failures.append(
                    f"{motion_id}: known_false_positive 인데 margin={res.get('margin')} "
                    "(변별로 바뀌었으면 fixture 갱신 — silent 금지)"
                )
            if "known_issue" not in pair:
                failures.append(f"{motion_id}: known_false_positive 인데 known_issue 라벨 없음")

        elif verdict == "known_gate_blocked":
            if res.get("fault_overall") is not None or res.get("success_overall") is not None:
                failures.append(
                    f"{motion_id}: known_gate_blocked 인데 점수 존재 — 게이트 해소됐으면 fixture 갱신"
                )
            if "known_issue" not in pair:
                failures.append(f"{motion_id}: known_gate_blocked 인데 known_issue 라벨 없음")
        else:
            failures.append(f"{motion_id}: 알 수 없는 verdict={verdict}")

    # summary 정합
    summ = baseline.get("summary", {})
    if summ.get("discriminating_pairs") != discriminating:
        failures.append(
            f"summary.discriminating_pairs={summ.get('discriminating_pairs')} "
            f"!= 실측 {discriminating}"
        )

    if failures:
        print("Phase 18 baseline FAIL:")
        for f in failures:
            print("  -", f)
        return 1

    print(
        f"Phase 18 baseline PASS — {len(pairs)} 페어 "
        f"(변별 {discriminating}, 위양성 {summ.get('known_false_positives')}, "
        f"게이트차단 {summ.get('known_gate_blocked')})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
