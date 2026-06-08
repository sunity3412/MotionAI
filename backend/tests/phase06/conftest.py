"""Phase 6 단위 테스트 공통 helper. Validation Architecture 6 fixture 정합.

R5 fix 신규 fixture_high_dispersion_arms_sprawled 포함 (2026-06-08 round-2 reviews).

기존 backend/tests/conftest.py 가 parents[1]/shared/python 을 sys.path 에 자동 주입
하므로 본 파일은 별도 path 주입 X — Phase 6 fixture 디렉토리 경로 상수만 노출.
"""

from __future__ import annotations

from pathlib import Path

# Phase 6 fixture 디렉토리 (Validation Architecture 6 fixture).
PHASE06_FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"
