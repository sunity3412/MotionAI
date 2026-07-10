"""매니페스트 ↔ S3 적재분 정합 + 균등 카운트 게이트 (22-02 Task 1·2).

검사:
  (a) s3_key 중복 0 + 스키마 정합(필수 키 존재).
  (b) 균등 게이트 — 동작별 max <= 2*min, 각 동작 정타·fault >= 1. _meta.
      collection_complete 플래그로만 활성화(silent 통과 금지 — 비활성 시 명시 gated
      상태를 assert). fail-closed 최종 강제는 22-04 진입 assert (DR-06).
      2026-07-10 수집 마감(belle 승인): 현 수집분은 정타 편중(fault=내부 371 이월)이라
      게이트 미충족 — silent 우회 대신 _meta.balance_waiver 로 위반 항목을 명시 문서화
      하고, 테스트는 waiver 가 실제 위반을 정확히 기술하는지 검증한다(은폐 불가).
      JSONL 단계 균등은 build_jsonl._balance_media 가 소유.
  (c) holdout=hard_negative_eval 행은 학습 카운트에서 제외 (실증 케이스 오염 금지).
  (d) --check-s3 셋 일치 — 네트워크 검사는 skip 마커.
"""

import json
from collections import defaultdict
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]
_MANIFEST = _BACKEND / "training" / "data" / "manifest.json"

ROW_REQUIRED_KEYS = (
    "s3_key", "motion", "label_bucket", "source", "usage", "holdout",
)


def _load() -> dict:
    if not _MANIFEST.exists():
        return {"_meta": {}, "rows": []}
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def _training_rows(rows: list[dict]) -> list[dict]:
    """holdout(hard_negative_eval 등) 행을 학습 카운트에서 제외."""
    return [r for r in rows if not r.get("holdout")]


def test_manifest_loads_and_has_meta():
    """매니페스트가 로드되고 _meta 블록(provenance)이 존재."""
    m = _load()
    assert "_meta" in m
    assert "rows" in m
    meta = m["_meta"]
    assert meta.get("usage_policy") == "training-only-no-redistribution"
    # collection_complete 플래그가 명시적으로 존재(silent 통과 금지).
    assert "collection_complete" in meta


def test_no_duplicate_s3_keys_and_schema():
    """s3_key 중복 0 + 행 스키마 필수 키 정합 (null s3_key 는 미수집 행이라 skip)."""
    m = _load()
    keys = [r["s3_key"] for r in m["rows"] if r.get("s3_key")]
    assert len(keys) == len(set(keys)), "s3_key 중복 존재"
    for row in m["rows"]:
        for k in ROW_REQUIRED_KEYS:
            assert k in row, f"행 스키마 누락 키 {k!r}: {row.get('s3_key')}"


def test_hard_negatives_excluded_from_training_count():
    """holdout=hard_negative_eval 행은 학습 카운트에서 제외 (Pitfall 2 격리)."""
    m = _load()
    rows = m["rows"]
    hard = [r for r in rows if r.get("holdout") == "hard_negative_eval"]
    training = _training_rows(rows)
    # 학습 카운트에 hard-negative 가 섞이지 않는다.
    for r in hard:
        assert r not in training
    # hard-negative 는 학습 소비 대상이 아님(라벨 오염 방지) — 카운트만 분리 확인.
    assert all(r.get("holdout") for r in hard)


def test_balance_gate_active_only_when_collection_complete():
    """균등 게이트 — collection_complete=true 일 때만 강제(silent 통과 금지)."""
    m = _load()
    meta = m["_meta"]
    training = _training_rows(m["rows"])
    complete = bool(meta.get("collection_complete"))

    if not complete:
        # 비활성 상태를 명시 assert — 조용히 지나가지 않는다.
        assert meta.get("collection_complete") is False, (
            "collection_complete 플래그가 명시적 False 여야(균등 게이트 gated 상태)"
        )
        pytest.skip("collection_complete=false — 균등 게이트는 Task 3 수집 후 활성화 (gated, DR-06)")

    # ── 활성 경로: 동작별 정타·fault >= 1 + max <= 2*min ──
    per_motion_bucket = defaultdict(lambda: defaultdict(int))
    for r in training:
        per_motion_bucket[r["motion"]][r["label_bucket"]] += 1
    counts = []
    violations: set[str] = set()
    for motion, buckets in per_motion_bucket.items():
        if buckets.get("정타", 0) < 1:
            violations.add("per_motion_jeongta_min1")
        if buckets.get("fault", 0) < 1:
            violations.add("per_motion_fault_min1")
        counts.append(sum(buckets.values()))
    if counts and max(counts) > 2 * min(counts):
        violations.add("max_le_2min")

    if not violations:
        return  # 게이트 완전 충족 — waiver 불요.

    # 위반이 있으면 반드시 문서화된 waiver 가 있어야 하고(silent 우회 금지),
    # waiver.unmet 이 실제 위반을 정확히 커버해야 한다(현실 은폐 불가).
    waiver = meta.get("balance_waiver")
    assert waiver, (
        f"균등 게이트 위반 {sorted(violations)} — _meta.balance_waiver 부재. "
        "silent 우회 금지: 승인·사유·이월 트랙을 문서화하거나 수집을 보강할 것."
    )
    for key in ("approved_by", "approved_at", "reason", "deferred_track", "unmet"):
        assert waiver.get(key), f"balance_waiver.{key} 부재 — waiver 문서화 불충분"
    assert violations <= set(waiver["unmet"]), (
        f"waiver.unmet={sorted(waiver['unmet'])} 이 실제 위반 {sorted(violations)} 을 "
        "커버하지 못함 — waiver 가 현실을 정확히 기술해야 한다"
    )


@pytest.mark.skip(reason="네트워크 검사 — --check-s3 실행 시에만 (fixtures/phase22 적재 후)")
def test_check_s3_three_way_consistency():
    """매니페스트 ↔ S3 fixtures/phase22 적재분 ↔ info.json 셋 일치 (Task 3 후)."""
    pass
