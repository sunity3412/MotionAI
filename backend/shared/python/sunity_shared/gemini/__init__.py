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

import importlib
from typing import TYPE_CHECKING

# ★lazy 화 (2026-08-21, quick-260821-umc): 이 __init__ 이 .client 를 즉시 import 하면
# `from google import genai` 가 무조건 딸려 온다. 그러면 pure 모듈인 .config 만 쓰는
# 소비자(gemini_teacher — 문서화된 계약 "google-genai/boto3 는 lazy import" — 를 거쳐
# run_bakeoff 게이트 하네스)까지 google-genai 미설치 venv 에서 ImportError 로 죽는다.
# 실측: 08-18 중앙 config 도입(359b9de5) 후 게이트 venv(ab_venv_cu129)에서
# `import run_bakeoff` 가 client.py 의 genai import 로 사망 — 게이트는 --skip-judge 라
# Gemini 호출 0 인데도. PEP 562 __getattr__ 로 공개 API 는 그대로, import 는 접근 시점.
_LAZY_EXPORTS: dict[str, str] = {
    "GeminiVisionCall": ".client",
    "GeminiCoachWriter": ".coach_writer_v2",
    "ALLOWED_MODELS": ".config",
    "DEFAULT_A_MODEL": ".config",
    "DEFAULT_B_MODEL": ".config",
    "DEFAULT_C_MODEL": ".config",
    "DEFAULT_C_MODEL_OVERRIDE": ".config",
    "DEFAULT_D_MODEL": ".config",
    "resolve_model": ".config",
    "_enforce_no_reject_patterns": ".guardrails",
    "augment_low_confidence": ".keypoint_augmenter",
    "extract_reference_metadata": ".reference_extractor",
    "find_scene_flags": ".scene_finder",
    "CheckpointJoint": ".schemas",
    "CoachCause": ".schemas",
    "CoachDetail2": ".schemas",
    "CoachPayload": ".schemas",
    "ExpectationLiteral": ".schemas",
    "FindingFlags": ".schemas",
    "JointCoaching": ".schemas",
    "JointKeyLiteral": ".schemas",
    "KeypointRefinement": ".schemas",
    "ReferenceRegistration": ".schemas",
    "RefinedKeypoint": ".schemas",
}


def __getattr__(name: str):  # noqa: D103 — PEP 562 lazy export.
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is not None:
        module = importlib.import_module(module_name, __name__)
        value = getattr(module, name)
        globals()[name] = value  # 재접근 시 __getattr__ 재진입 방지.
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


if TYPE_CHECKING:  # 정적 분석용 — 런타임 import 없음.
    from .client import GeminiVisionCall
    from .coach_writer_v2 import GeminiCoachWriter
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
    from .reference_extractor import extract_reference_metadata
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
    # coach_writer_v2 (Plan 17-04 — 영역 B Coach)
    "GeminiCoachWriter",
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
    # reference_extractor (Plan 17-05 — 영역 A Reference 자동 등록)
    "extract_reference_metadata",
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
