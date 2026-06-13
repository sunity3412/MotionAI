"""Phase 4 Wave 0 — POSE-03-d: warning frozenset 3-way lockstep gate.

D-08 합성 실패 → `ai_synthesis_failed` warning code.
D-08 partial 합성 → `ai_synthesis_partial` warning code.

본 테스트는 Wave 1 게이트 — Wave 0 시점에서는 RED 여야 한다.
sunity_shared.models 에 SYNTHESIS_WARNING_CODES frozenset 박제 + 두 코드 포함
시점이 Wave 1 (04-01) Task 1. 그 전에는 AttributeError → 회귀 게이트 역할.

xfail / pytest.skip 금지 — 이 테스트는 Wave 1 완료를 증명하는 gate 라
정상적인 실패가 필요하다.
"""

from __future__ import annotations

from sunity_shared import models as _models


def test_ai_synthesis_failed_in_frozenset() -> None:
    """SYNTHESIS_WARNING_CODES frozenset 에 'ai_synthesis_failed' 포함 (D-08)."""
    codes = getattr(_models, "SYNTHESIS_WARNING_CODES", None)
    assert codes is not None, (
        "sunity_shared.models.SYNTHESIS_WARNING_CODES 미존재 — Wave 1 (04-01) gate"
    )
    assert "ai_synthesis_failed" in codes


def test_ai_synthesis_partial_in_frozenset() -> None:
    """SYNTHESIS_WARNING_CODES frozenset 에 'ai_synthesis_partial' 포함 (D-08)."""
    codes = getattr(_models, "SYNTHESIS_WARNING_CODES", None)
    assert codes is not None, (
        "sunity_shared.models.SYNTHESIS_WARNING_CODES 미존재 — Wave 1 (04-01) gate"
    )
    assert "ai_synthesis_partial" in codes


def test_synthesis_warning_codes_type() -> None:
    """SYNTHESIS_WARNING_CODES 는 frozenset 타입 — mutable set / list 불가."""
    codes = getattr(_models, "SYNTHESIS_WARNING_CODES", None)
    assert codes is not None, (
        "sunity_shared.models.SYNTHESIS_WARNING_CODES 미존재 — Wave 1 (04-01) gate"
    )
    assert isinstance(codes, frozenset), (
        f"SYNTHESIS_WARNING_CODES must be frozenset (immutable), got {type(codes).__name__}"
    )
