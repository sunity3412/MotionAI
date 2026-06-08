"""Task 0 (C2 + R1 fix) — Phase 5 retroactive patch 검증.

TechniqueProfile dataclass 의 맨 끝 (hold_window 뒤) 에 motion_id: str | None = None
필드 추가 + FallbackRecognizer 회귀 부재 + dataclass import 자체 성공 (R1 fix).

박제 정신:
  - C2 fix (2026-06-08, Plan 06-02 reviews): Gemini canonical motion 이름을 reference
    컬렉션 lookup 의 stable key 로 박제. None 가능 (FallbackRecognizer / Gemini
    low_confidence / unregistered path 등).
  - R1 fix (2026-06-08 round-2): 위치는 dataclass 의 맨 끝 (hold_window 필드 뒤).
    default 있는 필드가 non-default 필드 앞에 오면 Python dataclass import 거부
    (`non-default argument follows default argument`).
"""

from __future__ import annotations

import numpy as np


def test_technique_profile_carries_motion_id() -> None:
    """R1 fix — motion_id 는 마지막 keyword argument. positional 7개 뒤 위치.

    keyword argument 로 motion_id 설정 시 정상 동작.
    """
    from sunity_shared.analysis.technique import TechniqueProfile

    profile = TechniqueProfile(
        name="inversion",
        category="recognized",
        joint_expectations={},
        required_split_deg=None,
        requires_hold=True,
        is_symmetric=False,
        hold_window=None,
        motion_id="inversion",
    )
    assert profile.motion_id == "inversion"


def test_technique_profile_motion_id_default_none() -> None:
    """motion_id 미지정 시 None (backwards-compatible default)."""
    from sunity_shared.analysis.technique import TechniqueProfile

    profile = TechniqueProfile(
        name="x",
        category="unknown",
        joint_expectations={},
    )
    assert profile.motion_id is None


def test_technique_profile_dataclass_imports_without_default_order_error() -> None:
    """R1 fix 핵심 — import 자체가 ImportError / TypeError 없이 성공.

    default 있는 필드가 default 없는 필드 앞에 위치하면 Python 이 import time
    거부 (`non-default argument follows default argument`). motion_id 가 맨 끝에
    위치해야 import 가 통과.
    """
    # 모듈 재로드 강제 — dataclass 정의 시점의 TypeError 가 발생하면 ImportError 로 wrapping
    import importlib

    import sunity_shared.analysis.technique as technique_module

    importlib.reload(technique_module)
    assert hasattr(technique_module, "TechniqueProfile")

    # motion_id 가 dataclass 의 마지막 필드 (R1 fix 위치 검증)
    fields_order = list(technique_module.TechniqueProfile.__dataclass_fields__)
    assert fields_order[-1] == "motion_id", (
        f"R1 fix 위반 — motion_id 가 dataclass 마지막 필드 아님. fields={fields_order}"
    )


def test_fallback_recognizer_motion_id_none() -> None:
    """FallbackRecognizer.recognize() 산출 profile.motion_id is None (회귀 없음)."""
    from sunity_shared.analysis.technique import FallbackRecognizer

    rec = FallbackRecognizer()
    profile = rec.recognize(angles=np.zeros((10, 17)))
    assert profile.motion_id is None
