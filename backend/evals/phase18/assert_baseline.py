#!/usr/bin/env python3
"""Phase 18 deliberate-fault eval set — baseline self-consistency 검사 (pod-free).

박제 정신:
  · Phase 18 fixture(pairs.yaml + baseline 스냅샷)가 게이트 의미론을 만족하는지
    Pod/GPU 없이 검사한다. 실 Pod 재실행 대조는 Pod 재개 후 sweep_phase15.py 산출과
    이 baseline 을 비교 — 여기서는 박제된 스냅샷의 self-consistency 만 확정한다.
  · 객관성(D-06): baseline 점수는 채점기 출력 스냅샷(라벨 아님). 사람 점수 라벨 금지.

ND-07 RETIRE 노트:
  verdict-consistency(expected↔verdict 정합) + discriminate-margin(fault<success / margin)
  asserts 는 **`phase24/assert_gates.py` 로 이동**했다(ND-07). 그 case-by-case 밴드
  매니페스트(moderate≤75 / major=50 류)는 curve-fit 유발이라 retire 한다. 대신 phase24
  게이트가 합성 데이터 위 추적성/단조성/결정성 + 실 Pod artifact 위 STRUCTURAL 일반화를
  증명한다. 이 파일은 fault-label/regression 소스(pairs.yaml + known_issue 추적)만 유지 —
  pairs.yaml ↔ baseline.json 의 페어-셋 일치 + known_false_positive/known_gate_blocked 의
  silent-통과 금지를 self-consistency 로 확정한다.

게이트 의미론 (band asserts 제거 후):
  1. pairs.yaml ↔ baseline.json 페어 셋 일치.
  2. known_false_positive / known_gate_blocked 는 명시 추적(silent 통과 금지) +
     known_issue 라벨 보유.

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

    # known_issue 추적 카운트(verdict/margin band assert 는 phase24 로 이동 — ND-07).
    known_fp = 0
    known_blocked = 0
    for motion_id, pair in pairs.items():
        res = results.get(motion_id)
        if res is None:
            failures.append(f"{motion_id}: baseline 스냅샷 누락")
            continue

        verdict = res["verdict"]

        # known-issue 명시 추적(silent 통과 금지) — fault-label 소스로서 유지.
        # 변별 자체(fault < success / margin)는 phase24/assert_gates.py 가 실 Pod artifact
        # 위 STRUCTURAL 일반화로 증명한다. 여기서는 점수-밴드를 단언하지 않는다.
        if verdict == "known_false_positive":
            if "known_issue" not in pair:
                failures.append(f"{motion_id}: known_false_positive 인데 known_issue 라벨 없음")
            known_fp += 1

        elif verdict == "known_gate_blocked":
            if "known_issue" not in pair:
                failures.append(f"{motion_id}: known_gate_blocked 인데 known_issue 라벨 없음")
            known_blocked += 1

    if failures:
        print("Phase 18 baseline FAIL:")
        for f in failures:
            print("  -", f)
        return 1

    print(
        f"Phase 18 baseline PASS — {len(pairs)} 페어 fault-label/regression 소스 정합 "
        f"(위양성 {known_fp}, 게이트차단 {known_blocked}). "
        "verdict/margin 밴드 asserts → phase24/assert_gates.py (ND-07)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
