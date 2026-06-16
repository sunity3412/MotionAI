"""corrective_exercises.json 스키마 게이트 (Plan 13-A Task 1 / criteria 1).

검증:
  - 유효 JSON + defects 정확히 5 키 + painAreas 정확히 8 키(= models.PAIN_AREAS).
  - 각 defect exercises >= 5, 각 exercise 가 name/setsReps/purpose/sourceRef 보유.
  - 모든 sourceRef 가 "NotebookLM" 포함 (출처 cite 강제, 임의 생성 차단).
  - trigger sourceSignals 가 ForceSourceSignal enum 값만 사용.
  - schemaVersion 박제 (app-side mirror lockstep 키).
  - sample_force_pattern_inference.json fixture 존재 + findings[] camelCase.
"""

from __future__ import annotations

from sunity_shared import models
from sunity_shared.analysis import force_pattern

from .conftest import load_corrective_exercises, load_phase13_fixture

_EXPECTED_DEFECT_KEYS = {
    "grip_weak",
    "shoulder_unstable",
    "core_weak",
    "legs_not_extended",
    "hip_hamstring_tight",
}
_EXERCISE_FIELDS = {"name", "setsReps", "purpose", "sourceRef"}


def test_fixture_is_valid_json_with_header() -> None:
    data = load_corrective_exercises()
    assert isinstance(data, dict)
    assert data["schemaVersion"] == "1.0.0"
    assert data["sourceNotebook"] == "e688fb4e-a4fb-4e83-a168-9c4726a98e09"


def test_defects_exactly_five_keys() -> None:
    data = load_corrective_exercises()
    assert set(data["defects"].keys()) == _EXPECTED_DEFECT_KEYS


def test_pain_areas_match_models_frozenset() -> None:
    data = load_corrective_exercises()
    assert set(data["painAreas"].keys()) == set(models.PAIN_AREAS)
    assert len(models.PAIN_AREAS) == 8


def test_each_defect_has_at_least_five_exercises() -> None:
    data = load_corrective_exercises()
    for key, defect in data["defects"].items():
        assert len(defect["exercises"]) >= 5, f"{key} exercises < 5"


def test_every_exercise_has_required_fields() -> None:
    data = load_corrective_exercises()
    blocks = list(data["defects"].values()) + list(data["painAreas"].values())
    for block in blocks:
        for ex in block["exercises"]:
            assert _EXERCISE_FIELDS <= set(ex.keys()), (
                f"exercise missing fields: {ex}"
            )
            assert "NotebookLM" in ex["sourceRef"], (
                f"sourceRef must cite NotebookLM: {ex}"
            )


def test_defect_triggers_use_valid_source_signals() -> None:
    data = load_corrective_exercises()
    valid = force_pattern._FORCE_SOURCE_SIGNALS
    for key, defect in data["defects"].items():
        signals = defect["triggers"]["sourceSignals"]
        for sig in signals:
            assert sig in valid, f"{key} has invalid sourceSignal {sig!r}"


def test_each_pain_area_has_avoid_line() -> None:
    data = load_corrective_exercises()
    for key, area in data["painAreas"].items():
        assert isinstance(area["avoid"], str) and area["avoid"], (
            f"{key} missing avoid line"
        )


def test_sample_force_pattern_inference_fixture_is_camel_case() -> None:
    fx = load_phase13_fixture("sample_force_pattern_inference.json")
    findings = fx["findings"]
    assert len(findings) >= 2
    signals = {f["sourceSignal"] for f in findings}
    assert "late_contact" in signals
    assert "axis_tilt" in signals
    for f in findings:
        # camelCase 키 박제 (Firestore result.forcePatternInference.findings[]).
        assert "sourceSignal" in f
        assert "jointHint" in f
