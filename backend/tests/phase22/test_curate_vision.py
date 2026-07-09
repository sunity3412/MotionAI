"""Gemini Vision 선별 게이트 순수 로직 테스트 (22-02 Task 1).

불변식(하드 제약):
  · verdict schema 에 score/severity 필드 부재 — 모델은 점수를 내지 않는다.
  · bucket enum 강제 ("정타"|"fault"|None) — 숫자 점수 유입 차단.
  · decide() 순수성 — Gemini 미호출.
  · 키 미설정 graceful — 크래시 없이 unknown 반환.
Gemini 네트워크는 절대 호출하지 않는다(순수 로직만).
"""

import pytest

from datagen import curate_vision as cv


def test_verdict_schema_has_no_score_or_severity():
    """VERDICT_KEYS 에 score/severity/overall/points 계열 부재 (불변식)."""
    for banned in cv.BANNED_VERDICT_FIELDS:
        assert banned not in cv.VERDICT_KEYS
    # 정확한 키 집합.
    assert cv.VERDICT_KEYS == ("bucket", "keep", "move_guess", "reason", "single_person_pole")
    # 알파벳 정렬.
    assert list(cv.VERDICT_KEYS) == sorted(cv.VERDICT_KEYS)


def test_normalize_drops_score_fields_and_enforces_bucket_enum():
    """score/severity 유입 시 화이트리스트로 탈락 + bucket enum 밖 값 → None."""
    raw = {
        "keep": True,
        "single_person_pole": True,
        "move_guess": "windmill",
        "bucket": "정타",
        "reason": "깨끗한 폴 클립",
        "score": 87,          # 유입 시도 — 통과 금지.
        "severity": "high",   # 유입 시도 — 통과 금지.
    }
    v = cv.normalize_verdict(raw)
    assert "score" not in v
    assert "severity" not in v
    assert v["bucket"] == "정타"
    # enum 밖 bucket(숫자 점수 포함) → None.
    assert cv.normalize_verdict({"bucket": "41점"})["bucket"] is None
    assert cv.normalize_verdict({"bucket": "excellent"})["bucket"] is None
    # 키 알파벳 정렬.
    assert list(v.keys()) == sorted(v.keys())


def test_decide_keeps_only_clean_single_person_pole_with_bucket():
    """keep=true + 단일인물 폴 + 유효 bucket 일 때만 status=keep."""
    keep = cv.decide({
        "keep": True, "single_person_pole": True,
        "bucket": "fault", "move_guess": "kip-up", "reason": "교정 대상",
    })
    assert keep.status == "keep"
    assert keep.keep is True
    assert keep.bucket == "fault"
    # 단일인물 아님 → reject.
    rej = cv.decide({
        "keep": True, "single_person_pole": False, "bucket": "정타", "reason": "다인",
    })
    assert rej.status == "reject"
    assert rej.keep is False
    # bucket 없음(enum 밖) → reject.
    rej2 = cv.decide({"keep": True, "single_person_pole": True, "bucket": None})
    assert rej2.status == "reject"


def test_decide_graceful_unknown_when_verdict_absent():
    """verdict None/빈값(키 미설정 graceful) → status=unknown, 크래시 없음."""
    assert cv.decide(None).status == "unknown"
    assert cv.decide({}).status == "unknown"
    assert cv.decide(None).keep is False


def test_decide_is_pure_no_gemini_call(monkeypatch):
    """decide()/normalize 는 Gemini 를 절대 호출하지 않는다 (순수)."""
    # _load_api_key 를 호출하면 예외 — decide 경로에 도달하면 안 됨.
    def _boom():
        raise AssertionError("decide() 가 Gemini 키 로드를 호출했다 — 순수성 위반")

    monkeypatch.setattr(cv, "_load_api_key", _boom)
    d = cv.decide({"keep": True, "single_person_pole": True, "bucket": "정타", "reason": "ok"})
    assert d.status == "keep"


def test_vision_gate_graceful_without_key(monkeypatch, tmp_path):
    """키 미설정 시 VisionGate 구성·gate 호출이 크래시 없이 unknown 반환 (네트워크 0)."""
    monkeypatch.setattr(cv, "_load_api_key", lambda: None)
    gate = cv.VisionGate(cache_path=tmp_path / "verdicts.json")
    assert gate._client is None
    verdict = gate.gate("vid123", "https://youtube.com/watch?v=vid123")
    # unknown verdict — keep=False, score 필드 없음.
    d = cv.decide(verdict)
    assert d.status in ("unknown", "reject")
    assert d.keep is False
    for banned in cv.BANNED_VERDICT_FIELDS:
        assert banned not in verdict
