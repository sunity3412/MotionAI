"""Phase 7 단위 테스트 공통 helper. classify_findings + copy_templates 박제 정합.

Phase 6 conftest.py 패턴 미러 — fixture 디렉토리 상수 단일 노출.

기존 backend/tests/conftest.py 가 parents[1]/shared/python 을 sys.path 에 자동 주입
하므로 본 파일은 별도 path 주입 X — Phase 7 fixture 디렉토리 경로 상수만 노출.

per .planning/phases/07-difference-classification/07-PATTERNS.md §"backend/tests/phase07/conftest.py".
"""

from __future__ import annotations

from pathlib import Path

# Phase 7 fixture 디렉토리 (6 classification fixture JSON).
PHASE07_FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"
