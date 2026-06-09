"""Phase 08.1 공용 pytest fixture — Plan 08.1-00 Wave 0.

PHASE08_1_FIXTURES_DIR 상수 + Phase 8 fixture factory import 가능.
Wave 0 (본 plan) 에서는 fixtures 디렉토리 생성 deferred — Wave 1 가 신설.

per Plan 08.1-00 must_haves (test infra Phase 7/8 패턴 정합).
"""

from __future__ import annotations

from pathlib import Path

import pytest  # noqa: F401 — pytest 인식 강제 (fixture 진입점)

PHASE08_1_FIXTURES_DIR = Path(__file__).parent / "fixtures"
