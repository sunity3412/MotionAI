"""Phase 08.1 공용 pytest fixture — Plan 08.1-00 Wave 0 + Plan 08.1-01 Wave 1.

PHASE08_1_FIXTURES_DIR 상수 + Phase 8 fixture factory import 가능.
Wave 1 augment: `_reset_tilt_cache` autouse — `_TILT_THRESHOLDS_CACHE` 누수 방지
(W10 정합 — module-global mutable flag 부재).

per Plan 08.1-00 must_haves + Plan 08.1-01 must_haves (Step 2 conftest augment).
"""

from __future__ import annotations

from pathlib import Path

import pytest

PHASE08_1_FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _reset_tilt_cache():
    """test 간 _TILT_THRESHOLDS_CACHE 누수 방지 (W10 정합)."""
    from sunity_shared.analysis import force_signals as _fs

    _fs._TILT_THRESHOLDS_CACHE = None
    yield
    _fs._TILT_THRESHOLDS_CACHE = None
