"""Phase 17 Plan 06B Task 2 — Smart sampling 가중치 (AI-SPEC §7) 테스트.

박제 정신:
  · `should_sample(analysis_doc)` 가 7 rule 박제 — isReference / guardrail / score 양극단
    / causes 최소 / 영역 C flag / branch_3_auto / baseline.
  · random.random monkeypatch 박제 — 외부 randomness 0.

테스트 매트릭스 (PLAN done gate 6 케이스):
  1. isReference=True → (True, "reference_100").
  2. guardrail_triggered 박힘 → (True, "guardrail_100").
  3. score < 30 + random<0.2 → (True, "score_extreme_20"); score > 95 → (True, ...).
  4. causes len == 3 + random<0.3 → (True, "causes_min_30").
  5. occlusion_severe=True + random<0.15 → (True, "flag_true_15").
  6. branch_3_auto → (True, "branch3_100"); baseline (모든 rule miss + random<0.02).
"""

from __future__ import annotations

import importlib

import pytest


def _reload_sampling():
    import sunity_shared.eval.sampling as sp

    importlib.reload(sp)
    return sp


# ─────────────────── 7 rule 케이스 ───────────────────


def test_rule_reference_100():
    """T2-S1: isReference=True → reference_100 박제 (weight 1.0)."""
    sp = _reload_sampling()
    sampled, reason = sp.should_sample({"isReference": True})
    assert sampled is True
    assert reason == "reference_100"


def test_rule_guardrail_100():
    """T2-S2: guardrail_triggered 박힘 → guardrail_100."""
    sp = _reload_sampling()
    sampled, reason = sp.should_sample(
        {"isReference": False, "guardrail_triggered": "G4_reference_occlusion_fp"}
    )
    assert sampled is True
    assert reason == "guardrail_100"


def test_rule_score_extreme_low(monkeypatch):
    """T2-S3a: score < 30 + random<0.2 → score_extreme_20."""
    sp = _reload_sampling()
    monkeypatch.setattr(sp, "_random", lambda: 0.1)  # < 0.2 → 샘플링.

    sampled, reason = sp.should_sample({"score": 25})
    assert sampled is True
    assert reason == "score_extreme_20"


def test_rule_score_extreme_high(monkeypatch):
    """T2-S3b: score > 95 + random ≥ 0.2 → not sampled."""
    sp = _reload_sampling()
    monkeypatch.setattr(sp, "_random", lambda: 0.5)  # ≥ 0.2 → 미샘플링.

    sampled, reason = sp.should_sample({"score": 97})
    assert sampled is False
    assert reason == "score_extreme_20"


def test_rule_causes_min(monkeypatch):
    """T2-S4: geminiB.causes len == 3 (최소) + random<0.3 → causes_min_30."""
    sp = _reload_sampling()
    monkeypatch.setattr(sp, "_random", lambda: 0.2)

    sampled, reason = sp.should_sample(
        {"geminiB": {"hip": {"detail2": {"causes": ["a", "b", "c"]}}}}
    )
    assert sampled is True
    assert reason == "causes_min_30"


def test_rule_flag_true(monkeypatch):
    """T2-S5: geminiC.occlusion_severe=True + random<0.15 → flag_true_15."""
    sp = _reload_sampling()
    monkeypatch.setattr(sp, "_random", lambda: 0.1)

    sampled, reason = sp.should_sample({"geminiC": {"occlusion_severe": True}})
    assert sampled is True
    assert reason == "flag_true_15"


def test_rule_branch3_100():
    """T2-S6: geminiA.routing_branch == branch_3_auto → branch3_100 (100%)."""
    sp = _reload_sampling()
    sampled, reason = sp.should_sample(
        {"geminiA": {"routing_branch": "branch_3_auto"}}
    )
    assert sampled is True
    assert reason == "branch3_100"


def test_rule_baseline_skip(monkeypatch):
    """T2-S7a: 모든 rule miss + random ≥ 0.02 → baseline_2 미샘플링."""
    sp = _reload_sampling()
    monkeypatch.setattr(sp, "_random", lambda: 0.5)

    sampled, reason = sp.should_sample({"score": 50})
    assert sampled is False
    assert reason == "baseline_2"


def test_rule_baseline_sample(monkeypatch):
    """T2-S7b: 모든 rule miss + random<0.02 → baseline_2 샘플링."""
    sp = _reload_sampling()
    monkeypatch.setattr(sp, "_random", lambda: 0.01)

    sampled, reason = sp.should_sample({"score": 50})
    assert sampled is True
    assert reason == "baseline_2"
