"""v29 run1 실물 29건(trap/hard_negative 제외) 재파싱 감사 — quick-260816-e26 Task 2.

Task 1 에서 수리한 schema.extract_report_json 을 v29 게이트 원문 회수분
(v29-20260815-124030_checkpoint-64-merged_run1.json) 의 real+synthetic_grounding
29건 raw 에 재적용해, 계획 단계(2026-08-16)에 "바깥 최상위 객체가 raw_decode 로
즉시 완결되는가"를 record 별로 직접 측정해 확정한 정답 기준(ground truth: none
15건/dict 14건)과 정확히 일치하는지 대조한다.

598KB 원본 JSON 은 Read 도구로 직접 읽지 말 것 — 이 스크립트(Bash 실행)가 처리하고
stdout 요약만 확인한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# repo root = .planning/quick/260816-e26-gate-parser-runaway/ 에서 3단계 위.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_TRAINING = _REPO_ROOT / "backend" / "training"
if str(_TRAINING) not in sys.path:
    sys.path.insert(0, str(_TRAINING))

from datagen import schema  # noqa: E402 — sys.path 주입 후 import 필요

_CORPUS_PATH = Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "4cd70dc3-9461-4b35-bf25-b2405ed6c7e7/scratchpad/"
    "v29-20260815-124030_checkpoint-64-merged_run1.json"
)

_INCLUDED_TYPES = ("real", "synthetic_grounding")

# ── 계획 단계(2026-08-16) 정밀 검증된 기대치 — 재조사 불필요 ──
# "바깥 객체가 raw_decode 로 즉시 완결되는가"를 29건 전부 직접 측정한 정답 기준.
EXPECTED_NONE: frozenset[str] = frozenset({
    "real-kipup-fault",
    "real-powerspin-correct",
    "real-powerspin-fault",
    "real-peterpan-correct",
    "real-climb-fault",
    "real-invert",
    "real-sideway-spin",
    "real-cocoon",
    "real-jadesplit",
    "synth-ground-stage1-s11",
    "synth-ground-stage1-s12",
    "synth-ground-stage2-s21",
    "synth-ground-stage2-s22",
    "synth-ground-stage3-s32",
    "synth-ground-stage1-s13",
})

EXPECTED_DICT: frozenset[str] = frozenset({
    "real-kipup-correct",
    "real-peterpan-fault",
    "real-elbowtwist-correct",
    "real-elbowtwist-fault",
    "real-pdshape-correct",
    "real-pdshape-fault",
    "real-climb-correct",
    "real-combo-correct",
    "real-foxtop",
    "real-ironx",
    "real-angle-corner",
    "real-various-poleorg",
    "synth-ground-stage3-s31",
    "synth-ground-stage2-s23",
})


def _expected_classification(rec_id: str) -> str:
    """record id → 기대 분류. 두 기대 집합 어디에도 없으면 "unknown"(코퍼스 drift
    감지 — 정답 기준 재확인 필요 신호)."""
    if rec_id in EXPECTED_NONE:
        return "none"
    if rec_id in EXPECTED_DICT:
        return "dict"
    return "unknown"


def main() -> int:
    with _CORPUS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    records = [r for r in data["records"] if r.get("type") in _INCLUDED_TYPES]

    dict_count = 0
    none_count = 0
    mismatches: list[str] = []
    seen_ids: set[str] = set()

    for rec in records:
        rec_id = str(rec.get("id", "<no-id>"))
        seen_ids.add(rec_id)
        raw = rec.get("raw")
        raw_len = len(raw) if isinstance(raw, str) else 0

        parsed = schema.extract_report_json(raw)
        classification = "dict" if isinstance(parsed, dict) else "none"
        if classification == "dict":
            dict_count += 1
        else:
            none_count += 1

        expected = _expected_classification(rec_id)
        matches = expected == classification
        if not matches:
            mismatches.append(rec_id)

        print(
            f"{rec_id:32s} raw_len={raw_len:6d} "
            f"classified={classification:5s} expected={expected:7s} "
            f"{'OK' if matches else 'MISMATCH'}"
        )

    # 코퍼스 drift 감지: 정답 기준에 있는 id 가 실제 29건에서 하나라도 빠졌으면
    # 기대치 자체가 더 이상 이 코퍼스를 대표하지 않는다 — 조용히 넘기지 않는다.
    expected_ids = EXPECTED_NONE | EXPECTED_DICT
    missing_ids = sorted(expected_ids - seen_ids)
    extra_ids = sorted(seen_ids - expected_ids)

    print("-" * 70)
    print(f"records audited: {len(records)} (expected 29)")
    print(f"dict={dict_count} none={none_count} mismatches={len(mismatches)}")
    if missing_ids:
        print(f"기대치에는 있는데 이번 29건에는 없는 id: {missing_ids}")
    if extra_ids:
        print(f"이번 29건에는 있는데 기대치 어느 집합에도 없는 id: {extra_ids}")

    if mismatches or missing_ids or extra_ids:
        if mismatches:
            print(f"MISMATCH record ids: {mismatches}")
        return 1

    print("29건 전부 기대 분류와 일치 (exit 0).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
