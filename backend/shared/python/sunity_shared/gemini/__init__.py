"""Phase 17 Wave 0 — Gemini Vision 공통 베이스 (4 영역 통합 진입점).

박제 정신:
  · 후속 plan 02 (영역 A 영상 reference 등록) / 03 (영역 B 코칭) / 04 (영역 C finding) /
    05 (영역 D keypoint refinement) 가 동일한 client / retry / 객관성 가드 / Pydantic
    검증을 재구현하지 않도록 단일 베이스 박제.
  · 객관성 헌장 ([[analysis-objectivity-no-human-scores]]) 위반은 graceful 폴백 X —
    `_enforce_no_reject_patterns` 가 ValueError raise.
  · 영역별 default model string 은 `config.py` 가 단일 source 박제 — Plan 02~05 는 raw
    string 박지 않고 본 모듈만 import.
"""

from __future__ import annotations

from .client import GeminiVisionCall
from .config import (
    ALLOWED_MODELS,
    DEFAULT_A_MODEL,
    DEFAULT_B_MODEL,
    DEFAULT_C_MODEL,
    DEFAULT_C_MODEL_OVERRIDE,
    DEFAULT_D_MODEL,
    resolve_model,
)
from .guardrails import _enforce_no_reject_patterns
from .keypoint_augmenter import augment_low_confidence
from .scene_finder import find_scene_flags
from .schemas import (
    CheckpointJoint,
    CoachCause,
    CoachDetail2,
    CoachPayload,
    ExpectationLiteral,
    FindingFlags,
    JointCoaching,
    JointKeyLiteral,
    KeypointRefinement,
    ReferenceRegistration,
    RefinedKeypoint,
)

__all__ = [
    # client
    "GeminiVisionCall",
    # config
    "ALLOWED_MODELS",
    "DEFAULT_A_MODEL",
    "DEFAULT_B_MODEL",
    "DEFAULT_C_MODEL",
    "DEFAULT_C_MODEL_OVERRIDE",
    "DEFAULT_D_MODEL",
    "resolve_model",
    # guardrails
    "_enforce_no_reject_patterns",
    # keypoint_augmenter (Plan 17-03 — 영역 D Keypoint)
    "augment_low_confidence",
    # scene_finder (Plan 17-02 — 영역 C Finding)
    "find_scene_flags",
    # schemas
    "CheckpointJoint",
    "CoachCause",
    "CoachDetail2",
    "CoachPayload",
    "ExpectationLiteral",
    "FindingFlags",
    "JointCoaching",
    "JointKeyLiteral",
    "KeypointRefinement",
    "ReferenceRegistration",
    "RefinedKeypoint",
]
