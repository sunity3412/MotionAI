"""Phase 17 Plan 06B Task 2 — LLM judge (영역 B 코칭 톤) 테스트.

박제 정신:
  · `judge_coach_tone(coach_payload, belle_label=None)` 가 Gemini Flash text-only
    호출로 코칭 톤 binary pass 산출 + belle binary 라벨 calibration mode.
  · 외부 호출 0 — `_call_judge_llm` monkeypatch 박제.
  · belle_label 일치/불일치 시 confidence 박제 (correlation 측정 입력).

테스트 매트릭스 (PLAN done gate 5 케이스 정합):
  1. coach_payload 정상 + LLM "pass=true" → pass=True.
  2. blocklist 어휘 stub + LLM "pass=false" → pass=False.
  3. belle_label 일치 (True 라벨 + judge pass=True) → confidence 1.0.
  4. belle_label 불일치 (False 라벨 + judge pass=True) → confidence 0.0.
  5. judge LLM None (graceful) → pass=None.
"""

from __future__ import annotations

import importlib
import json
from typing import Any

import pytest


def _reload_llm_judge():
    import sunity_shared.eval.llm_judge as lj

    importlib.reload(lj)
    return lj


# ─────────────────── 5 케이스 ───────────────────


def test_judge_pass_true(monkeypatch):
    """T2-1: coach_payload 정상 + LLM "pass=true" → pass=True."""
    lj = _reload_llm_judge()

    monkeypatch.setattr(
        lj,
        "_call_judge_llm",
        lambda prompt, model: {
            "pass": True,
            "reasoning_ko": "강사 보조 톤 충족.",
        },
    )

    result = lj.judge_coach_tone(
        {"hip": {"detail": "고관절 외회전 부족", "detail2": {"coachNote": "강사와 함께 확인"}}}
    )

    assert result["pass"] is True
    assert result["judge_model"] == "gemini-3.5-flash"
    assert result["confidence"] is None  # belle_label 없음 — calibration mode X


def test_judge_pass_false(monkeypatch):
    """T2-2: blocklist 어휘 stub + LLM "pass=false" → pass=False."""
    lj = _reload_llm_judge()

    monkeypatch.setattr(
        lj,
        "_call_judge_llm",
        lambda prompt, model: {
            "pass": False,
            "reasoning_ko": "단정형 어휘 박혀있음.",
        },
    )

    result = lj.judge_coach_tone(
        {"hip": {"detail2": {"coachNote": "당신은 이렇게 하세요"}}}
    )

    assert result["pass"] is False
    assert result["reasoning_ko"]


def test_judge_calibration_match(monkeypatch):
    """T2-3: belle_label 일치 (True 라벨 + judge pass=True) → confidence 1.0."""
    lj = _reload_llm_judge()

    monkeypatch.setattr(
        lj,
        "_call_judge_llm",
        lambda prompt, model: {"pass": True, "reasoning_ko": "OK"},
    )

    result = lj.judge_coach_tone(
        {"hip": {"detail2": {"coachNote": "강사 확인"}}},
        belle_label=True,
    )

    assert result["pass"] is True
    assert result["confidence"] == 1.0


def test_judge_calibration_mismatch(monkeypatch):
    """T2-4: belle_label 불일치 (False 라벨 + judge pass=True) → confidence 0.0."""
    lj = _reload_llm_judge()

    monkeypatch.setattr(
        lj,
        "_call_judge_llm",
        lambda prompt, model: {"pass": True, "reasoning_ko": "OK"},
    )

    result = lj.judge_coach_tone(
        {"hip": {"detail2": {"coachNote": "강사 확인"}}},
        belle_label=False,
    )

    assert result["pass"] is True
    assert result["confidence"] == 0.0


def test_judge_graceful_when_llm_none(monkeypatch):
    """T2-5: judge LLM None (graceful — API 키 미설정 등) → pass=None."""
    lj = _reload_llm_judge()

    monkeypatch.setattr(lj, "_call_judge_llm", lambda prompt, model: None)

    result = lj.judge_coach_tone(
        {"hip": {"detail2": {"coachNote": "강사 확인"}}}
    )

    assert result["pass"] is None
    assert result["confidence"] is None
