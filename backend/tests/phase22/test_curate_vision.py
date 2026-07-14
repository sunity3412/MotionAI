"""Gemini Vision 선별 게이트 순수 로직 테스트 (22-02 Task 1).

불변식(하드 제약):
  · verdict schema 에 score/severity 필드 부재 — 모델은 점수를 내지 않는다.
  · bucket enum 강제 ("정타"|"fault"|None) — 숫자 점수 유입 차단.
  · decide() 순수성 — Gemini 미호출.
  · 키 미설정 graceful — 크래시 없이 unknown 반환.
Gemini 네트워크는 절대 호출하지 않는다(순수 로직만).
"""

import json

import pytest

from datagen import curate_vision as cv


def test_verdict_schema_has_no_score_or_severity():
    """VERDICT_KEYS 에 score/severity/overall/points 계열 부재 (불변식)."""
    for banned in cv.BANNED_VERDICT_FIELDS:
        assert banned not in cv.VERDICT_KEYS
    # 정확한 키 집합 (quick-260714-js2: fault_demo/fault_desc 편입 — 서술 필드만, 점수 아님).
    assert cv.VERDICT_KEYS == (
        "bucket", "fault_demo", "fault_desc", "keep", "move_guess", "reason",
        "single_person_pole",
    )
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


# ---------------------------------------------------------------------------
# fault_demo 큐레이션 프로필 (quick-260714-js2 — 튜토리얼 fault 재수집 라운드).
# 22-02 에서 편집/자막 reject 가 튜토리얼을 통째로 걸러 fault=0 이었던 근본원인의
# 데이터 처방. default 프로필 판정은 문자 그대로 무변경이 하드 제약.
# ---------------------------------------------------------------------------
def test_fault_demo_fields_added_banned_fields_still_dropped():
    """fault_demo/fault_desc 편입 후에도 score/severity 계열은 normalize 에서 드롭 (불변식 유지)."""
    assert "fault_demo" in cv.VERDICT_KEYS
    assert "fault_desc" in cv.VERDICT_KEYS
    raw = {
        "keep": True, "single_person_pole": True, "bucket": "fault",
        "fault_demo": True, "fault_desc": "잘못된 예시 구간에서 무릎 굽힘 시연",
        "reason": "교정형 튜토리얼",
        "score": 41,          # 유입 시도 — 통과 금지.
        "severity": "high",   # 유입 시도 — 통과 금지.
    }
    v = cv.normalize_verdict(raw)
    for banned in cv.BANNED_VERDICT_FIELDS:
        assert banned not in v
    assert v["fault_demo"] is True
    assert v["fault_desc"] == "잘못된 예시 구간에서 무릎 굽힘 시연"


def test_normalize_legacy_verdict_defaults_fault_fields():
    """구 캐시 verdict(두 키 부재) 재정규화 → fault_demo=False / fault_desc=None (오염 0)."""
    legacy = {
        "keep": True, "single_person_pole": True, "bucket": "정타",
        "move_guess": "windmill", "reason": "깨끗한 폴 클립",
    }
    v = cv.normalize_verdict(legacy)
    assert v["fault_demo"] is False
    assert v["fault_desc"] is None
    # 알파벳 정렬 재방출 유지.
    assert list(v.keys()) == sorted(v.keys())


def test_decide_fault_demo_profile_keeps_only_demonstrated_fault():
    """fault_demo 프로필: keep && 단일인물 폴 && bucket=fault && fault_demo=true 조합만 keep."""
    keep = cv.decide({
        "keep": True, "single_person_pole": True, "bucket": "fault",
        "fault_demo": True, "fault_desc": "등 과신전 시연", "reason": "교정 튜토리얼",
    }, profile="fault_demo")
    assert keep.status == "keep"
    assert keep.bucket == "fault"
    # 정타 버킷 → fault 프로필에선 reject (fault 시연 없는 일반 튜토리얼 유입 차단).
    rej_bucket = cv.decide({
        "keep": True, "single_person_pole": True, "bucket": "정타", "fault_demo": True,
    }, profile="fault_demo")
    assert rej_bucket.status == "reject"
    # fault_demo=false → reject (fault 시연 구간 없음).
    rej_demo = cv.decide({
        "keep": True, "single_person_pole": True, "bucket": "fault", "fault_demo": False,
    }, profile="fault_demo")
    assert rej_demo.status == "reject"
    # 단일인물 요건은 프로필에서도 유지.
    rej_multi = cv.decide({
        "keep": True, "single_person_pole": False, "bucket": "fault", "fault_demo": True,
    }, profile="fault_demo")
    assert rej_multi.status == "reject"
    # verdict 부재 graceful unknown 은 프로필 무관 동일.
    assert cv.decide(None, profile="fault_demo").status == "unknown"


def test_decide_default_profile_unchanged_and_ignores_fault_fields():
    """기본 호출(프로필 미지정) 판정은 fault_demo 필드 존재와 무관하게 기존과 동일 (fence)."""
    # 정타 keep — fault_demo 필드가 있어도 default 판정 불변.
    d = cv.decide({
        "keep": True, "single_person_pole": True, "bucket": "정타",
        "fault_demo": True, "fault_desc": "x", "reason": "ok",
    })
    assert d.status == "keep"
    # default 에서 bucket=fault 는 fault_demo 없이도 keep (기존 로직 그대로).
    d2 = cv.decide({"keep": True, "single_person_pole": True, "bucket": "fault"})
    assert d2.status == "keep"


def test_gate_cache_key_profile_scoped(monkeypatch, tmp_path):
    """default 키에 reject 박제된 vid 도 fault_demo 프로필로 재판정 경로에 진입한다.

    22-02 당시 vision_verdicts.json 은 video_id 단독 키 — 프로필 스코프 없이는
    default reject 가 fault 재큐레이션을 영구 차단(핵심 함정).
    """
    monkeypatch.setattr(cv, "_load_api_key", lambda: None)
    # 캐시 키 빌더 계약: default = video_id 그대로(기존 캐시 히트 유지), 프로필 = suffix.
    assert cv.cache_key("vid1") == "vid1"
    assert cv.cache_key("vid1", "fault_demo") == "vid1::fault_demo"

    cache_file = tmp_path / "verdicts.json"
    default_reject = cv.normalize_verdict({
        "keep": False, "single_person_pole": True, "bucket": None,
        "reason": "편집/자막 과다 — 폐기",
    })
    cache_file.write_text(
        json.dumps({cv.cache_key("vid1"): default_reject}, ensure_ascii=False),
        encoding="utf-8",
    )
    gate = cv.VisionGate(cache_path=cache_file)
    # default 프로필 → 박제 reject 캐시 히트 (재호출 0 유지).
    assert gate.gate("vid1", "https://youtu.be/vid1") == default_reject

    # fault_demo 프로필 → 캐시 미스 → 재판정 경로 진입 (_call_gemini mock, 네트워크 0).
    gate._client = object()
    calls: list[str] = []

    def fake_call(url, profile="default"):
        calls.append(profile)
        return {
            "keep": True, "single_person_pole": True, "bucket": "fault",
            "fault_demo": True, "fault_desc": "무릎 굽힘 시연", "reason": "잘못된 예시 구간",
        }

    monkeypatch.setattr(gate, "_call_gemini", fake_call)
    verdict = gate.gate("vid1", "https://youtu.be/vid1", profile="fault_demo")
    assert calls == ["fault_demo"]
    assert cv.decide(verdict, profile="fault_demo").status == "keep"
    # 프로필 스코프 키에 저장 — default 키 오염 0.
    assert gate._cache[cv.cache_key("vid1", "fault_demo")] == verdict
    assert gate._cache[cv.cache_key("vid1")] == default_reject

    # 키 미설정 graceful unknown 동작은 프로필 무관 동일.
    monkeypatch.setattr(cv, "_load_api_key", lambda: None)
    gate2 = cv.VisionGate(cache_path=tmp_path / "v2.json")
    u = gate2.gate("vid9", "https://youtu.be/vid9", profile="fault_demo")
    assert cv.decide(u, profile="fault_demo").status in ("unknown", "reject")
    assert cv.decide(u, profile="fault_demo").keep is False


def test_fault_demo_prompt_static_fence():
    """fault_demo 프롬프트: 점수 산출 지시 부재 + 후프/에어리얼/스트렝스/비폴 reject 유지."""
    p = cv._GATE_PROMPT_FAULT_DEMO
    # 점수 필드 산출 지시 부재 (JSON 스키마에 score/severity 키 없음).
    assert '"score"' not in p
    assert '"severity"' not in p
    # 점수/severity 금지 문구는 유지 (산출 지시가 아니라 금지 지시).
    assert "절대" in p
    # reject 유지 대상 명시.
    for kw in ("후프", "에어리얼", "스트렝스", "비폴"):
        assert kw in p
    # fault 시연 필드 요구 + 편집/자막 수용 명시 (22-02 통째 reject 근본원인 완화).
    assert '"fault_demo"' in p
    assert '"fault_desc"' in p
    assert "편집" in p
    assert "자막" in p
