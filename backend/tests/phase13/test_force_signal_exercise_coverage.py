"""ForceSourceSignal → 보완운동 전수 커버리지 게이트 (13-A GAP / belle 표준).

belle 2026-06-16 표준 (load-bearing): 시스템은 예시 집합이 아니라 STANDARD 를
지켜야 한다 — "새 영상이 들어와도 동작은 동작". 구체적으로 13-A 에 대해:
Phase 9 force_pattern 이 emit 할 수 있는 모든 ForceSourceSignal 은 적어도 1개의
보완운동 defect 에 매핑되어야 한다 (silent miss = 표준 위반).

본 게이트는 force_pattern.py._FORCE_SOURCE_SIGNALS (force_pattern_copy.py 의
ForceSourceSignal Literal 과 lockstep) 의 6 신호 각각에 대해, 실제 emit 형태의
synthetic finding (sourceSignal + joint_hint_for(signal)) 을 구성하고
exercise_map._defect_keys_from_findings 가 비지 않은 defect 리스트를 돌려주는지
검증한다.

이 테스트는 pelvis_drop 갭이 닫히기 전 tree 에서 FAIL 하고(갭 증명), 닫힌 뒤
PASS 한다 — belle 표준의 영속 가드.
"""

from __future__ import annotations

from typing import get_args

from sunity_shared.analysis import force_pattern
from sunity_shared.analysis.exercise_map import _defect_keys_from_findings
from sunity_shared.analysis.force_pattern_copy import ForceSourceSignal, joint_hint_for

# force_pattern_copy.ForceSourceSignal Literal 의 6 멤버 — joint_hint_for 와 동일
# 모듈의 신호 집합 (durable, copy-module-local source). force_pattern.py 의
# _FORCE_SOURCE_SIGNALS frozenset 과 lockstep 임은 아래 test 가 강제.
_COPY_SIGNALS: tuple[str, ...] = get_args(ForceSourceSignal)


def _synthetic_finding(signal: str) -> dict:
    """force_pattern.py 가 emit 하는 실제 finding 모양의 최소 dict.

    sourceSignal + (있으면) jointHint = joint_hint_for(signal). 이는 매핑 입력으로
    실제 파이프라인이 채우는 두 키와 동일하다.
    """
    return {"sourceSignal": signal, "jointHint": joint_hint_for(signal)}


def test_copy_signals_lockstep_with_force_pattern() -> None:
    """force_pattern_copy 의 6 신호 집합이 force_pattern.py frozenset 과 동일.

    이 lockstep 이 깨지면 본 커버리지 게이트가 잘못된 신호 집합을 검사하므로
    먼저 확인.
    """
    assert set(_COPY_SIGNALS) == set(force_pattern._FORCE_SOURCE_SIGNALS)
    assert len(_COPY_SIGNALS) == 6


def test_every_force_source_signal_maps_to_a_defect() -> None:
    """6 신호 전수 — 각 신호의 synthetic finding 이 >=1 defect 로 매핑된다.

    belle 표준의 핵심 가드. 어떤 신호든 0 defect 면 silent miss 회귀.
    """
    uncovered: list[str] = []
    for signal in sorted(_COPY_SIGNALS):
        finding = _synthetic_finding(signal)
        matched = _defect_keys_from_findings([finding])
        if not matched:
            uncovered.append(signal)
    assert not uncovered, (
        "보완운동 매핑이 비어있는 ForceSourceSignal (belle 표준 위반 — "
        f"모든 신호는 >=1 defect 매핑 필수): {uncovered}"
    )


def test_pelvis_drop_specifically_covered() -> None:
    """13-A GAP 회귀 핀 — pelvis_drop 이 명시적으로 커버된다.

    pelvis_drop 은 lateral pelvic drop(중둔근/고관절 외전근 불안정) 신호로,
    갭 클로저 이전에는 어떤 defect 의 sourceSignals/jointHints 에도 매칭되지
    않아 0 운동(silent miss)이었다.
    """
    finding = _synthetic_finding("pelvis_drop")
    matched = _defect_keys_from_findings([finding])
    assert matched, "pelvis_drop 이 어떤 defect 에도 매핑되지 않음 (13-A GAP 미해결)"
