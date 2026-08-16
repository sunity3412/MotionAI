"""mirror_reference_candidate_top_level.py 의 `_build_mirror_fields` 순수 함수 테스트
(quick-260816-r7k Task 3, TDD RED).

`_build_mirror_fields` 는 Firestore/네트워크 무관 순수 함수다 (validation.py 의
"순수 함수(boto3/네트워크 무관)" 컨벤션과 동일 스타일) — 이 테스트는 실 Firestore
접속 없이 동작을 검증한다.

왜 BASE_FIELDS 는 fail-closed 로 막고 DOWNSTREAM_FIELDS 도 똑같이 막는가:
  candidate 문서에 angles/joints3d(BASE) 는 있는데 meanAngles 등(DOWNSTREAM) 이
  없는 상태로 top-level 을 write 하면, 같은 문서 안에서 일부는 새 영상 일부는 구
  영상을 가리키는 내부 불일치가 생긴다 — 이는 PLAN.md <objective> "다운스트림
  백필 필요 여부 판단" 절이 "선택이 아니라 필수"라고 명시한 바로 그 상태다
  (threat_model T-r7k-04). 조용히 partial write 하지 않고 ValueError 로 막는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from mirror_reference_candidate_top_level import (  # noqa: E402
    BASE_FIELDS,
    DOWNSTREAM_FIELDS,
    _build_mirror_fields,
)

_VERSION = "quick-260816-r7k"
_NOW_MS = 1755331200000


def _fixture_candidate_doc() -> dict:
    """BASE_FIELDS + DOWNSTREAM_FIELDS 를 전부 갖춘 candidate 문서 fixture."""
    doc = {f: f"base-{f}-value" for f in BASE_FIELDS}
    doc.update({f: f"downstream-{f}-value" for f in DOWNSTREAM_FIELDS})
    return doc


# ── Test 1: 완전한 candidate_doc → 18필드 + activeVersion + 7 UpdatedAt = 26키 ──


def test_returns_base_and_downstream_fields_plus_active_version_and_updated_at():
    doc = _fixture_candidate_doc()

    result = _build_mirror_fields(doc, _VERSION, _NOW_MS)

    for field in BASE_FIELDS:
        assert result[field] == doc[field], f"BASE_FIELDS[{field}] 값 불일치"
    for field in DOWNSTREAM_FIELDS:
        assert result[field] == doc[field], f"DOWNSTREAM_FIELDS[{field}] 값 불일치"
    assert result["activeVersion"] == _VERSION
    for field in DOWNSTREAM_FIELDS:
        assert result[f"{field}UpdatedAt"] == _NOW_MS

    assert len(result) == len(BASE_FIELDS) + len(DOWNSTREAM_FIELDS) + 1 + len(
        DOWNSTREAM_FIELDS
    )
    assert len(result) == 26


# ── Test 2: candidate-only 부기 필드가 top-level 에 새지 않는다 (정확히 26키) ──


def test_no_candidate_only_bookkeeping_fields_leak_into_mirror():
    doc = _fixture_candidate_doc()
    # backfill_reference_downstream.py 가 candidate 문서에만 남기는 부기 필드 —
    # top-level mirror 대상이 아니다.
    doc["downstreamBackfillVersion"] = _VERSION
    doc["downstreamBackfilledAt"] = "2026-08-16T00:00:00Z"

    result = _build_mirror_fields(doc, _VERSION, _NOW_MS)

    assert "downstreamBackfillVersion" not in result
    assert "downstreamBackfilledAt" not in result
    # base 필드는 UpdatedAt 컴패니언이 없다 — downstream 만 감사 필드를 가진다.
    assert "keypointReportUpdatedAt" not in result
    assert "anglesUpdatedAt" not in result
    assert len(result) == 26


# ── Test 3: BASE_FIELDS 결측 → ValueError (fail-closed, 부분 write 금지) ──


@pytest.mark.parametrize("missing_field", BASE_FIELDS)
def test_raises_on_missing_base_field(missing_field):
    doc = _fixture_candidate_doc()
    del doc[missing_field]

    with pytest.raises(ValueError):
        _build_mirror_fields(doc, _VERSION, _NOW_MS)


# ── 추가: DOWNSTREAM_FIELDS 결측도 동일하게 fail-closed (T-r7k-04 방어) ──


@pytest.mark.parametrize("missing_field", DOWNSTREAM_FIELDS)
def test_raises_on_missing_downstream_field(missing_field):
    doc = _fixture_candidate_doc()
    del doc[missing_field]

    with pytest.raises(ValueError):
        _build_mirror_fields(doc, _VERSION, _NOW_MS)
