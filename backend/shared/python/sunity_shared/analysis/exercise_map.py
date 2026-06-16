"""보완 운동 매핑 layer (Phase 13 Plan 13-A / PERS-03).

분석 결과의 실패 원인 후보(Phase 9 forcePatternInference.findings)와 자가입력
통증부위(BodyProfile.painAreas)를 입력으로 받아 결함/통증부위별 보완 운동을
backend/data/corrective_exercises.json fixture 에서 매핑한다.

순수성 (Layer 2 boto3 영구 차단 — force_pattern.py / classify_findings 패턴 정합):
  - numpy/AWS-free, network-free. 단위 test 로 전부 검증.
  - 입력은 plain dict / list[str] / str|None, 출력은 plain camelCase scalar dict
    (dataclass 아님 — Firestore recommendedExercises 가 그대로 저장됨).

3-way contract lockstep (Task 3 박제): TS `app/src/types/analysis.ts`
RecommendedExercise ↔ models.py recommendedExercises 계약 ↔ docs/contract.md §4.

D-05 하드월: painAreas 는 본 매핑 출력에만 흘러가고 어떤 점수/차원 채점 경로에도
닿지 않는다. 본 함수는 차원 채점 값을 인자로 받지 않으며 채점 경로 토큰을 참조하지
않는다 (test_exercise_map_no_scoring_leak.py grep 게이트).
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import models

# corrective_exercises.json — repo root 기준 (force_signals._CONTACT_POINTS_PATH
# 패턴 정합: analysis → sunity_shared → python → shared → backend / "data").
_CORRECTIVE_EXERCISES_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "data"
    / "corrective_exercises.json"
)
_CORRECTIVE_EXERCISES_CACHE: dict | None = None

# defect 키 검증용 frozenset (fixture defects 키와 lockstep).
# glute_hip_unstable = 13-A GAP 클로저 (pelvis_drop 커버리지 — 중둔근/고관절
# 외전근 STABILITY 결함, hip_hamstring_tight 의 flexibility 와 구분).
_DEFECT_KEYS: frozenset[str] = frozenset(
    {
        "grip_weak",
        "shoulder_unstable",
        "core_weak",
        "legs_not_extended",
        "hip_hamstring_tight",
        "glute_hip_unstable",
    }
)
# painArea 키 = models.PAIN_AREAS 재사용 (단일 진실원).
_PAIN_AREA_KEYS: frozenset[str] = frozenset(models.PAIN_AREAS)

# 보완 운동 출력 cap (criteria 2 = 3~5).
_MAX_EXERCISES = 5
_MIN_EXERCISES = 3


def _load_corrective_exercises() -> dict:
    """corrective_exercises.json lazy load + 모듈 캐시."""
    global _CORRECTIVE_EXERCISES_CACHE
    if _CORRECTIVE_EXERCISES_CACHE is None:
        _CORRECTIVE_EXERCISES_CACHE = json.loads(
            _CORRECTIVE_EXERCISES_PATH.read_text(encoding="utf-8")
        )
    return _CORRECTIVE_EXERCISES_CACHE


def _defect_keys_from_findings(findings: list) -> list[str]:
    """findings[] 의 sourceSignal + jointHint 를 defect 키로 join.

    fixture 의 defect.triggers.sourceSignals / jointHints 와 매칭. 우선순위는
    findings 순서 (Phase 9 가 이미 Top-3 ranking 적용) 를 보존한다.
    """
    library = _load_corrective_exercises()
    defects = library.get("defects", {})
    matched: list[str] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        source_signal = finding.get("sourceSignal")
        joint_hint = finding.get("jointHint")
        for defect_key, defect in defects.items():
            if defect_key not in _DEFECT_KEYS or defect_key in matched:
                continue
            triggers = defect.get("triggers", {})
            signals = triggers.get("sourceSignals", [])
            hints = triggers.get("jointHints", [])
            signal_hit = source_signal is not None and source_signal in signals
            hint_hit = (
                joint_hint is not None
                and any(h in joint_hint or joint_hint in h for h in hints)
            )
            if signal_hit or hint_hit:
                matched.append(defect_key)
    return matched


def _valid_pain_area_keys(pain_areas: list[str]) -> list[str]:
    """painAreas[] 를 painArea 키로 join — PAIN_AREAS 멤버만, 순서/중복 보존 제거."""
    result: list[str] = []
    for area in pain_areas or []:
        if area in _PAIN_AREA_KEYS and area not in result:
            result.append(area)
    return result


def map_exercises(
    force_pattern_inference: dict | None,
    pain_areas: list[str],
    motion_id: str | None,
) -> list[dict]:
    """결함 + 통증부위 → 보완 운동 3~5개 (criteria 2,3).

    Args:
        force_pattern_inference: Firestore result.forcePatternInference dict
            (findings[] camelCase) 또는 None (FallbackRecognizer / 미산출).
        pain_areas: bodyProfile.painAreas snapshot (PAIN_AREAS 멤버).
        motion_id: TechniqueProfile.motion_id 또는 None — v1 은 generic 결함
            운동만 산출 (move-specific gating 은 미래 확장 hook).

    Returns:
        plain camelCase scalar dict list — {name, setsReps, purpose, sourceRef}.
        painArea 안전 운동이 우선 정렬, name 기준 dedup, 3~5 cap. 입력이 비면
        빈 list (graceful, 크래시 X).
    """
    library = _load_corrective_exercises()

    findings: list = []
    if isinstance(force_pattern_inference, dict):
        raw = force_pattern_inference.get("findings")
        if isinstance(raw, list):
            findings = raw

    valid_pain_areas = _valid_pain_area_keys(pain_areas)
    defect_keys = _defect_keys_from_findings(findings)

    # painArea 안전 운동 우선 (criteria: avoid 안전 라인 우선 정렬), 그 다음 defect.
    ordered: list[dict] = []
    for area_key in valid_pain_areas:
        area = library.get("painAreas", {}).get(area_key, {})
        ordered.extend(area.get("exercises", []))
    for defect_key in defect_keys:
        defect = library.get("defects", {}).get(defect_key, {})
        ordered.extend(defect.get("exercises", []))

    # name 기준 dedup (순서 보존).
    seen: set[str] = set()
    deduped: list[dict] = []
    for ex in ordered:
        if not isinstance(ex, dict):
            continue
        name = ex.get("name")
        if not isinstance(name, str) or name in seen:
            continue
        seen.add(name)
        # plain camelCase scalar dict 만 emit (nested 차단).
        deduped.append(
            {
                "name": ex.get("name"),
                "setsReps": ex.get("setsReps"),
                "purpose": ex.get("purpose"),
                "sourceRef": ex.get("sourceRef"),
            }
        )

    if not deduped:
        return []

    # 3~5 cap. 후보가 3 미만이면 있는 만큼만 (fabrication 금지).
    return deduped[:_MAX_EXERCISES]
