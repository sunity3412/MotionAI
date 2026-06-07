"""BodyNormalizationProfile validator 단위 테스트 (Plan 01-19 Task 1).

D-19 박제: SMPL-X β 없이 segment 길이 비율 + confidence + warnings 만으로
체형 정규화 표현. 본 테스트는 dataclass validator 의 경계값/타입 검증을
test_pose_engine_contract.py 의 contract 검증과 분리해 둔다.

본 파일은 Task 1 의 acceptance — 별도 파일로 분리한 이유:
  - test_pose_engine_contract.py 는 인터페이스·필드 집합 위주 (contract)
  - 본 파일은 validator behavior 위주 (post_init 동작)
"""

from __future__ import annotations

import pytest


def test_construct_with_all_required_fields() -> None:
    """모든 필드 명시 시 정상 생성."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    p = BodyNormalizationProfile(
        estimated_height_scale=1.05,
        arm_scale=0.97,
        leg_scale=1.02,
        torso_scale=1.00,
        shoulder_hip_ratio=1.18,
        confidence=0.85,
        warnings=["short_arm_clip"],
    )
    assert p.estimated_height_scale == 1.05
    assert p.shoulder_hip_ratio == 1.18
    assert p.confidence == 0.85
    assert p.warnings == ["short_arm_clip"]


def test_confidence_boundary_values_accepted() -> None:
    """confidence 0.0 / 1.0 경계 정상 통과."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    for c in (0.0, 0.5, 1.0):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=c,
        )


def test_confidence_negative_rejected() -> None:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    with pytest.raises(ValueError):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=-0.0001,
        )


def test_confidence_above_one_rejected() -> None:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    with pytest.raises(ValueError):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=1.0001,
        )


def test_warnings_default_empty_list() -> None:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    p = BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.7,
    )
    assert p.warnings == []
    assert isinstance(p.warnings, list)


def test_warnings_must_be_list_of_str() -> None:
    """warnings 가 list[str] 이 아니면 거부."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    # tuple — 거부
    with pytest.raises((TypeError, ValueError)):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=0.7,
            warnings=("a", "b"),  # type: ignore[arg-type]
        )

    # None — 거부
    with pytest.raises((TypeError, ValueError)):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=0.7,
            warnings=None,  # type: ignore[arg-type]
        )

    # list 안에 str 이 아닌 값 — 거부
    with pytest.raises((TypeError, ValueError)):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=0.7,
            warnings=[123, "ok"],  # type: ignore[list-item]
        )


# ── Phase 2 v5 박제 (MEDIUM-2 v5): 5 numeric scale 필드 finite + strictly positive ──

import math  # noqa: E402

_NUMERIC_FIELDS = (
    "estimated_height_scale",
    "arm_scale",
    "leg_scale",
    "torso_scale",
    "shoulder_hip_ratio",
)


def _build_kwargs(**overrides: float) -> dict:
    """정상 값 baseline + overrides 로 dataclass 인자 dict 생성."""
    base = {
        "estimated_height_scale": 1.0,
        "arm_scale": 1.0,
        "leg_scale": 1.0,
        "torso_scale": 1.0,
        "shoulder_hip_ratio": 1.0,
        "confidence": 0.9,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("field_name", _NUMERIC_FIELDS)
def test_numeric_field_rejects_nan(field_name: str) -> None:
    """5 필드 각각 NaN → ValueError + message 에 필드명 (MEDIUM-2 v5)."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    with pytest.raises(ValueError, match=field_name):
        BodyNormalizationProfile(**_build_kwargs(**{field_name: math.nan}))


@pytest.mark.parametrize("field_name", _NUMERIC_FIELDS)
def test_numeric_field_rejects_positive_inf(field_name: str) -> None:
    """5 필드 각각 +inf → ValueError (MEDIUM-2 v5)."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    with pytest.raises(ValueError, match=field_name):
        BodyNormalizationProfile(**_build_kwargs(**{field_name: math.inf}))


@pytest.mark.parametrize("field_name", _NUMERIC_FIELDS)
def test_numeric_field_rejects_negative_inf(field_name: str) -> None:
    """5 필드 각각 -inf → ValueError (MEDIUM-2 v5)."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    with pytest.raises(ValueError, match=field_name):
        BodyNormalizationProfile(**_build_kwargs(**{field_name: -math.inf}))


@pytest.mark.parametrize("field_name", _NUMERIC_FIELDS)
def test_numeric_field_rejects_zero(field_name: str) -> None:
    """5 필드 각각 0.0 → ValueError (strictly positive, MEDIUM-2 v5)."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    with pytest.raises(ValueError, match=field_name):
        BodyNormalizationProfile(**_build_kwargs(**{field_name: 0.0}))


@pytest.mark.parametrize("field_name", _NUMERIC_FIELDS)
def test_numeric_field_rejects_negative(field_name: str) -> None:
    """5 필드 각각 음수 → ValueError (MEDIUM-2 v5)."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    with pytest.raises(ValueError, match=field_name):
        BodyNormalizationProfile(**_build_kwargs(**{field_name: -1.0}))


def test_valid_profile_passes_validator() -> None:
    """정상 값 5 필드 + confidence + warnings=[] → 객체 생성 OK (MEDIUM-2 v5)."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    p = BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.1,
        leg_scale=1.05,
        torso_scale=1.0,
        shoulder_hip_ratio=0.85,
        confidence=0.9,
        warnings=[],
    )
    assert p.arm_scale == 1.1
    assert p.confidence == 0.9
    assert p.warnings == []
