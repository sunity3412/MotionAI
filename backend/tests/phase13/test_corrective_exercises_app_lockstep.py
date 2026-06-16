"""HIGH-2 (13-REVIEW-FIXES.md §5) — app mirror FULL-CONTENT lockstep.

backend/data/corrective_exercises.json ↔ app/src/data/corrective_exercises.json
가 byte-copy (deep-equal) 인지 검증. name-set smoke check 가 아니라 canonical
직렬화 deep-equal 로 어떤 필드 drift(schemaVersion / defects / painAreas / 각
exercise·avoid·trigger 필드)든 fail.

생성은 cp(byte-identical)이되 정식 게이트는 content deep-equal (3차 LOW-1: 포맷-only
drift 는 앱에 무의미하므로 deep-equal 이 canonical 게이트). test_body_normalization
_lockstep.py 의 repo-root Path 해석 패턴 정합.
"""

from __future__ import annotations

import json
from pathlib import Path

# phase13 → tests → backend → repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_JSON = _REPO_ROOT / "backend" / "data" / "corrective_exercises.json"
_APP_JSON = _REPO_ROOT / "app" / "src" / "data" / "corrective_exercises.json"

_DEFECT_KEYS = {
    "grip_weak",
    "shoulder_unstable",
    "core_weak",
    "legs_not_extended",
    "hip_hamstring_tight",
}
_PAIN_AREA_KEYS = {
    "shoulder",
    "wrist",
    "lower_back",
    "knee",
    "ankle",
    "neck",
    "hip",
    "elbow",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_app_mirror_exists() -> None:
    assert _APP_JSON.exists(), (
        "app/src/data/corrective_exercises.json 누락 — backend byte-copy 필요 (HIGH-2)"
    )


def test_full_content_deep_equal() -> None:
    """BEST 게이트 — canonical 직렬화 deep-equal (어떤 필드 drift 든 fail)."""
    backend = _load(_BACKEND_JSON)
    app = _load(_APP_JSON)
    backend_canon = json.dumps(backend, sort_keys=True, ensure_ascii=False)
    app_canon = json.dumps(app, sort_keys=True, ensure_ascii=False)
    assert backend_canon == app_canon, (
        "app mirror ↔ backend fixture content drift — "
        "cp backend/data/corrective_exercises.json app/src/data/ 로 재복사 필요 (HIGH-2)"
    )


# ── 명시 필드 단위 게이트 (deep-equal 보조, drift 위치 진단용) ──────────────


def test_schema_version_matches() -> None:
    assert _load(_BACKEND_JSON)["schemaVersion"] == _load(_APP_JSON)["schemaVersion"]


def test_defect_and_pain_area_keys_match() -> None:
    backend = _load(_BACKEND_JSON)
    app = _load(_APP_JSON)
    assert set(backend["defects"]) == set(app["defects"]) == _DEFECT_KEYS
    assert set(backend["painAreas"]) == set(app["painAreas"]) == _PAIN_AREA_KEYS


def test_each_defect_exercises_and_triggers_match() -> None:
    backend = _load(_BACKEND_JSON)
    app = _load(_APP_JSON)
    for key in _DEFECT_KEYS:
        b = backend["defects"][key]
        a = app["defects"][key]
        # 모든 exercise {name, setsReps, purpose, sourceRef} 일치.
        assert b["exercises"] == a["exercises"], f"defect {key} exercises drift"
        # trigger sourceSignals + jointHints 일치.
        assert b["triggers"]["sourceSignals"] == a["triggers"]["sourceSignals"]
        assert b["triggers"]["jointHints"] == a["triggers"]["jointHints"]


def test_each_pain_area_avoid_and_exercises_match() -> None:
    backend = _load(_BACKEND_JSON)
    app = _load(_APP_JSON)
    for key in _PAIN_AREA_KEYS:
        b = backend["painAreas"][key]
        a = app["painAreas"][key]
        assert b["avoid"] == a["avoid"], f"painArea {key} avoid drift"
        assert b["exercises"] == a["exercises"], f"painArea {key} exercises drift"
