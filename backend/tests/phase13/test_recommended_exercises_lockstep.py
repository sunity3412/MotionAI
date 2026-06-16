"""Plan 13-A Task 3 — recommendedExercises wiring + validator (PERS-03).

검증:
  - complete_analysis(recommended_exercises=[...]) → payload result.recommendedExercises 저장.
  - recommended_exercises=None → 키 미저장 (graceful).
  - _validate_recommended_exercises: len > 5 reject / nested-array reject / non-list reject.

phase12 test_firestore_lockstep_phase12._FakeDocRef 패턴 재사용.
"""

from __future__ import annotations

import pytest

from sunity_shared import firestore_admin
from sunity_shared.firestore_admin import _validate_recommended_exercises


class _FakeDocRef:
    def __init__(self) -> None:
        self.set_calls: list[dict] = []

    def set(self, payload: dict, merge: bool = False) -> None:  # noqa: ARG002
        self.set_calls.append(dict(payload))


def _valid_exercises() -> list[dict]:
    return [
        {
            "name": "Farmer's Walk",
            "setsReps": "왕복",
            "purpose": "전완근/악력 강화",
            "sourceRef": "NotebookLM e688fb4e [1]",
        },
        {
            "name": "Planks",
            "setsReps": "30~60s",
            "purpose": "코어 안정화",
            "sourceRef": "NotebookLM e688fb4e [3]",
        },
    ]


# ── complete_analysis wiring ──────────────────────────────────────────────


def test_complete_analysis_recommended_exercises_wiring(monkeypatch) -> None:
    fake_doc = _FakeDocRef()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: fake_doc)

    exercises = _valid_exercises()
    firestore_admin.complete_analysis(
        uid="u1",
        analysis_id="a1",
        result={"overallScore": 80},
        recommended_exercises=exercises,
    )

    assert len(fake_doc.set_calls) == 1
    payload = fake_doc.set_calls[0]
    assert payload["result"].get("recommendedExercises") == exercises


def test_complete_analysis_recommended_exercises_none_skips(monkeypatch) -> None:
    fake_doc = _FakeDocRef()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: fake_doc)

    firestore_admin.complete_analysis(
        uid="u1",
        analysis_id="a1",
        result={"overallScore": 80},
        recommended_exercises=None,
    )

    assert len(fake_doc.set_calls) == 1
    payload = fake_doc.set_calls[0]
    assert "recommendedExercises" not in payload.get("result", {})


def test_complete_analysis_recommended_exercises_over_cap_raises(monkeypatch) -> None:
    fake_doc = _FakeDocRef()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: fake_doc)

    too_many = _valid_exercises() * 3  # 6 > 5 cap.
    with pytest.raises(ValueError, match="length > 5|cap"):
        firestore_admin.complete_analysis(
            uid="u1",
            analysis_id="a1",
            result={"overallScore": 80},
            recommended_exercises=too_many,
        )
    assert len(fake_doc.set_calls) == 0


# ── validator unit ────────────────────────────────────────────────────────


def test_validator_none_returns_early() -> None:
    _validate_recommended_exercises(None)


def test_validator_valid_list_passes() -> None:
    _validate_recommended_exercises(_valid_exercises())


def test_validator_non_list_rejects() -> None:
    with pytest.raises(ValueError, match="list"):
        _validate_recommended_exercises({"name": "x"})


def test_validator_over_cap_rejects() -> None:
    with pytest.raises(ValueError, match="length > 5|cap"):
        _validate_recommended_exercises(_valid_exercises() * 3)


def test_validator_nested_array_in_item_rejects() -> None:
    bad = _valid_exercises()
    bad[0]["nestedList"] = ["a", "b"]
    with pytest.raises((ValueError, TypeError)):
        _validate_recommended_exercises(bad)


def test_validator_non_dict_item_rejects() -> None:
    with pytest.raises(ValueError, match="dict"):
        _validate_recommended_exercises(["not a dict"])
