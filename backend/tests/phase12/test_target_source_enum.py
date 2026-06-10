"""Phase 12 Wave 0A R4 (Codex 직접 리뷰 2026-06-10) — TargetSource enum 4종 검증.

dimensions.TargetSource Literal 4 enum + _TARGET_SOURCES validator frozenset.
kismam.TargetSource 와 1:1 lockstep — 3-way contract (Python kismam + dimensions +
TS analysis.ts JointScore.targetSource + docs/contract.md).

cite: 12-00-PLAN.md Task T3.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis import dimensions, kismam


def test_target_source_enum_4_values():
    """_TARGET_SOURCES 가 정확히 4 enum value 박제."""
    expected = {
        "reference_motion",
        "previous_analysis",
        "extension_requirement",
        "unavailable",
    }
    assert dimensions._TARGET_SOURCES == expected


def test_validate_target_source_accepts_valid():
    """4 enum value 모두 통과 + 입력 그대로 반환."""
    for value in [
        "reference_motion",
        "previous_analysis",
        "extension_requirement",
        "unavailable",
    ]:
        assert dimensions._validate_target_source(value) == value


def test_invalid_target_source_raises():
    """허용 외 값 입력 → ValueError."""
    with pytest.raises(ValueError, match="target_source must be one of"):
        dimensions._validate_target_source("other")
    with pytest.raises(ValueError):
        dimensions._validate_target_source("")
    with pytest.raises(ValueError):
        dimensions._validate_target_source("REFERENCE_MOTION")  # case-sensitive


def test_kismam_target_source_enum_lockstep_with_dimensions():
    """kismam.TargetSource 와 dimensions.TargetSource Literal 4 enum 동일성 박제.

    Literal type 자체 비교는 불가하므로 _TARGET_SOURCES frozenset + kismam.assess
    의 실 값 분기 동작으로 간접 검증.
    """
    import numpy as np

    from sunity_shared.analysis.skeleton import JOINT_KEYS

    n = len(JOINT_KEYS)
    deviation = np.zeros(n, dtype=float)
    # 4 enum 모두 kismam.assess 가 거부 안 함 (target_angle dict 비어도 진행).
    for source in (
        "reference_motion",
        "previous_analysis",
        "extension_requirement",
        "unavailable",
    ):
        result = kismam.assess(deviation, target_source=source)
        assert len(result) == n
