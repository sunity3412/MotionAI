"""Phase 13 (llm-coaching-detail) 단위 테스트 공통 헬퍼.

phase09/conftest.py 패턴 미러 — repo-root path 해석 + fixture 로더.
backend/tests/conftest.py 가 sunity_shared 를 sys.path 에 주입하므로
본 conftest 는 import 경로를 다시 손대지 않고 path/loader 헬퍼만 제공한다.

- _repo_root(): SunityMotion 저장소 루트 (phase13 → tests → backend → repo).
- _backend_data_path(name): backend/data/<name> 절대 경로.
- load_phase13_fixture(name): tests/phase13/fixtures/<name> JSON 로드.
- load_corrective_exercises(): backend/data/corrective_exercises.json 로드.
"""

from __future__ import annotations

import json
from pathlib import Path

# phase13 → tests → backend → repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _repo_root() -> Path:
    return _REPO_ROOT


def _backend_data_path(name: str) -> Path:
    return _REPO_ROOT / "backend" / "data" / name


def load_phase13_fixture(name: str) -> dict:
    """tests/phase13/fixtures/<name> JSON 로드."""
    return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))


def load_corrective_exercises() -> dict:
    """backend/data/corrective_exercises.json 로드 (단일 진실원)."""
    return json.loads(
        _backend_data_path("corrective_exercises.json").read_text(encoding="utf-8")
    )
