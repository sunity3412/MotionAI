"""Plan 5-01 Task 3 (W4 fix 신설) — GeminiTechniqueRecognizer 어댑터 단위 테스트.

mock 박제만 — google.genai / boto3 / firebase_admin 실 호출 0.

박제 정신:
  · D-04 / D-05 / D-08 / D-09 / D-13 / D-16
  · [[analysis-objectivity-no-human-scores]] reject patterns 2차 가드
  · B2 fix: production classifier 직접 호출 검증
  · B3 fix: unregistered_hook 인자 = (keyword, video_hash) — video_path X
  · B5 fix: raw_text 가 reject patterns 입력으로 도달함 단위 시험
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from sunity_shared.analysis.gemini_technique_recognizer import (
    GeminiTechniqueRecognizer,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS
from sunity_shared.analysis.technique import (
    JOINT_BENT_OK,
    JOINT_EXTEND,
    FallbackRecognizer,
    TechniqueProfile,
)
from sunity_shared.judging.gemini_moment_extractor import DEFAULT_GEMINI_MODEL


# ─────────────────── 테스트용 더미 KeyMoment / Extractor ───────────────────


@dataclass
class _StubMoment:
    """KeyMoment 호환 더미 — dataclass(frozen) 회피.

    GeminiTechniqueRecognizer._call_extractor 가 m.confidence 만 읽으므로,
    confidence 만 필수.
    """

    moment_key: str
    timestamp_seconds: float
    confidence: float
    frame_index: int = 0


class _StubExtractor:
    """GeminiMomentExtractor 호환 mock.

    _last_raw_response / _last_motion_name attribute + extract_key_moments 만 구현.
    """

    def __init__(
        self,
        *,
        moments: list,
        raw_response: str = "",
        raw_motion_name: str = "auto",
        raise_on_call: Exception | None = None,
    ) -> None:
        self._moments = list(moments)
        self._last_raw_response = raw_response
        self._last_motion_name = raw_motion_name
        self._raise = raise_on_call
        self.call_count = 0

    def extract_key_moments(self, video_uri: str, motion: str) -> list:
        self.call_count += 1
        if self._raise is not None:
            raise self._raise
        return list(self._moments)


def _angles_8j(rows: int = 20) -> np.ndarray:
    """더미 (T, 8) angle 행렬."""
    return np.full((rows, len(JOINT_KEYS)), 170.0)


# ─────────────────── Test 1: 정상 path (recognized) ───────────────────


class TestRecognizedPath:
    """Gemini 정상 응답 → TechniqueProfile + joint_expectations."""

    def test_recognized_motion_returns_profile_with_expectations(self) -> None:
        # ref-invert yaml = 6관절 EXTEND (shoulder/hip/knee 좌우), elbow 2관절 = BENT_OK.
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.2, 0.85)],
            raw_response='{"motion_name": "ref-invert", "moments": []}',
            raw_motion_name="ref-invert",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "recognized"
        assert profile.name == "ref-invert"
        # joint_expectations 가 JOINT_KEYS 8개 모두 포함.
        assert set(profile.joint_expectations.keys()) == set(JOINT_KEYS)


# ─────────────────── Test 2: API 실패 → api_failure ───────────────────


class TestApiFailurePath:
    """D-09 case 1 — RuntimeError 시 FallbackRecognizer 위임 + category="api_failure"."""

    def test_runtime_error_falls_back_to_api_failure(self) -> None:
        ext = _StubExtractor(
            moments=[], raise_on_call=RuntimeError("Gemini quota exceeded")
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "api_failure"
        # FallbackRecognizer 결과여야 함 — joint_expectations 8개 모두 채워짐.
        assert set(profile.joint_expectations.keys()) == set(JOINT_KEYS)

    def test_value_error_from_extractor_falls_back(self) -> None:
        # Gemini 응답 JSON 파싱 실패 등 → ValueError → fallback.
        ext = _StubExtractor(
            moments=[], raise_on_call=ValueError("invalid JSON")
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "api_failure"

    def test_api_failure_falls_back(self) -> None:
        # 어댑터 layer 2차 — fallback 객체 주입해서 위임 동작 확인.
        ext = _StubExtractor(moments=[], raise_on_call=RuntimeError("net down"))
        custom_fallback = FallbackRecognizer()
        rec = GeminiTechniqueRecognizer(extractor=ext, fallback=custom_fallback)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "api_failure"


# ─────────────────── Test 3: low confidence ───────────────────


class TestLowConfidencePath:
    """D-09 case 2 — mean confidence < threshold → joint_expectations={}."""

    def test_low_confidence_returns_empty_expectations(self) -> None:
        # threshold default = 0.5. 0.2 + 0.3 mean = 0.25 < 0.5.
        ext = _StubExtractor(
            moments=[
                _StubMoment("hold", 7.0, 0.2),
                _StubMoment("setup", 1.0, 0.3),
            ],
            raw_response='{"motion_name": "ref-invert"}',
            raw_motion_name="ref-invert",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext, low_confidence_threshold=0.5)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "low_confidence"
        assert profile.joint_expectations == {}
        assert profile.name == "신뢰도 낮음"

    def test_empty_moments_treated_as_low_confidence(self) -> None:
        # moments=[] → mean_conf=0.0 → low_confidence.
        ext = _StubExtractor(
            moments=[],
            raw_response='{"motion_name": "ref-invert"}',
            raw_motion_name="ref-invert",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "low_confidence"


# ─────────────────── Test 4: unregistered + hook (B3 fix) ───────────────────


class TestUnregisteredPath:
    """D-09 case 3 — unregistered + hook 호출 + video_hash 인자 검증."""

    def test_unregistered_motion_returns_empty_expectations(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 5.0, 0.8)],
            raw_response='{"motion_name": "Aerial Yogi"}',
            raw_motion_name="Aerial Yogi",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "unregistered"
        assert profile.joint_expectations == {}
        assert "Aerial Yogi" in profile.name

    def test_unregistered_hook_called_with_keyword_and_video_hash(self) -> None:
        # B3 fix 검증 — hook(keyword, video_hash). video_path 박제 X.
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 5.0, 0.8)],
            raw_response='{"motion_name": "Aerial Yogi"}',
            raw_motion_name="Aerial Yogi",
        )
        hook = MagicMock()
        rec = GeminiTechniqueRecognizer(extractor=ext, unregistered_hook=hook)
        rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        hook.assert_called_once()
        args, kwargs = hook.call_args
        # 시그너처 = (keyword, video_hash). 인자 2개.
        assert len(args) == 2, f"hook 인자 개수 위반 (기대 2, 실제 {len(args)})"
        assert args[0] == "Aerial Yogi", "hook 첫 인자 = raw motion name 키워드"
        # video_hash 는 Plan 5-02 technique_cache 미신설 → "" (graceful fallback).
        assert isinstance(args[1], str), "hook 두번째 인자 = video_hash str"
        # video_path 가 인자로 들어가면 안 됨 (PII 미노출).
        assert args[1] != "/tmp/fake.mp4", "B3 fix 위반: video_path 가 hook 인자로 노출"

    def test_unregistered_hook_failure_does_not_block_analysis(self) -> None:
        # hook 가 throw 해도 분석 흐름 계속.
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 5.0, 0.8)],
            raw_response='{"motion_name": "Unknown Move"}',
            raw_motion_name="Unknown Move",
        )

        def _failing_hook(keyword: str, video_hash: str) -> None:
            raise RuntimeError("Firestore down")

        rec = GeminiTechniqueRecognizer(
            extractor=ext, unregistered_hook=_failing_hook
        )
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        # hook 실패해도 unregistered profile 반환.
        assert profile.category == "unregistered"


# ─────────────────── Test 5: B5 fix — raw_text 2차 가드 ───────────────────


class TestRejectPatternsSecondaryGuard:
    """B5 fix 검증 — extractor._last_raw_response 가 좌표 포함 → 어댑터 2차 가드 ValueError.

    raw_text 가 reject patterns 입력으로 도달함을 단위 검증.
    """

    def test_coordinate_in_raw_response_triggers_value_error(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.8)],
            # B5 fix — _last_raw_response 가 좌표 포함.
            raw_response='{"left_knee": "x=120 y=80"}',
            raw_motion_name="ref-invert",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        with pytest.raises(ValueError, match="좌표"):
            rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")

    def test_score_in_raw_response_triggers_value_error(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.8)],
            raw_response='{"description": "이 동작은 85점 입니다"}',
            raw_motion_name="ref-invert",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        with pytest.raises(ValueError, match="점수"):
            rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")

    def test_clean_raw_response_passes_secondary_guard(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.8)],
            raw_response='{"motion_name": "ref-invert", "description": "동작 완성"}',
            raw_motion_name="ref-invert",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "recognized"


# ─────────────────── Test 6: lazy import (D-16) ───────────────────


class TestLazyImport:
    def test_module_import_does_not_load_google_genai(self) -> None:
        # adapter 모듈 import 시점에 google.genai 미import.
        # (다른 테스트가 google.genai import 했을 수 있으므로 source grep 으로 검증.)
        from sunity_shared.analysis import gemini_technique_recognizer as adapter

        source = Path(adapter.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.startswith("from google") or line.startswith("import google"):
                pytest.fail(f"adapter top-level google import 박제: '{line}'")

    def test_module_import_does_not_load_boto3(self) -> None:
        from sunity_shared.analysis import gemini_technique_recognizer as adapter

        source = Path(adapter.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.startswith("from boto3") or line.startswith("import boto3"):
                pytest.fail(f"adapter top-level boto3 import 박제: '{line}'")

    def test_module_import_does_not_load_firebase_admin(self) -> None:
        from sunity_shared.analysis import gemini_technique_recognizer as adapter

        source = Path(adapter.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.startswith("from firebase_admin") or line.startswith(
                "import firebase_admin"
            ):
                pytest.fail(
                    f"adapter top-level firebase_admin import 박제: '{line}'"
                )


# ─────────────────── Test 7: DEFAULT_GEMINI_MODEL (D-13) ───────────────────


class TestDefaultModel:
    def test_default_model_is_gemini_3_1_pro(self) -> None:
        # D-13 belle 2026-06-04 확정 (Gemini 3.1 Pro 단일).
        # fix v2 2026-06-05: gemini-3.1-pro-preview (gemini-3-pro-preview deprecated).
        assert DEFAULT_GEMINI_MODEL == "gemini-3.1-pro-preview"


# ─────────────────── Test 8: ref-invert joint_expectations ───────────────────


class TestJointExpectationsFromYaml:
    """yaml hold_moment criteria → joint_expectations EXTEND/BENT_OK 매핑 검증.

    yaml lookup 실패 (PyYAML 미설치 환경 등) 시 = 8관절 BENT_OK fallback.
    어느 path 든 8관절 키가 모두 채워져야 함 (dimensions.py 가 KeyError 0).
    """

    def test_ref_invert_expectations_contains_all_8_joints(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.85)],
            raw_response='{"motion_name": "ref-invert"}',
            raw_motion_name="ref-invert",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        # 정상 path / yaml lookup fallback path 모두 8관절 전부 박제.
        assert set(profile.joint_expectations.keys()) == set(JOINT_KEYS)
        # 모든 값이 JOINT_EXTEND 또는 JOINT_BENT_OK.
        for joint_key, label in profile.joint_expectations.items():
            assert label in {JOINT_EXTEND, JOINT_BENT_OK}, (
                f"{joint_key}={label} — EXTEND/BENT_OK 외 라벨 박제"
            )

    def test_ref_climb_expectations_all_bent_ok(self) -> None:
        # ref-climb yaml = hold_moment 빈 list (D-20). 모든 관절 BENT_OK.
        # yaml lookup 실패 path 도 8관절 BENT_OK 보장.
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 5.0, 0.85)],
            raw_response='{"motion_name": "ref-climb"}',
            raw_motion_name="ref-climb",
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert set(profile.joint_expectations.keys()) == set(JOINT_KEYS)
        # ref-climb hold_moment = [] → 모든 관절 BENT_OK.
        assert all(
            v == JOINT_BENT_OK for v in profile.joint_expectations.values()
        ), "ref-climb 은 hold_moment 빈 list → 8관절 BENT_OK 박제"


# ─────────────────── Test 10: cache lookup short-circuit ───────────────────


class TestCacheShortCircuit:
    """cache.lookup 가 dict 반환 시 extractor.extract_key_moments 미호출."""

    def test_cache_hit_skips_extractor(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.85)],
            raw_response='{"motion_name": "ref-invert"}',
            raw_motion_name="ref-invert",
        )
        cache = MagicMock()
        cache.lookup.return_value = {
            "motion": "ref-invert",
            "joint_expectations": {jk: JOINT_BENT_OK for jk in JOINT_KEYS},
        }
        rec = GeminiTechniqueRecognizer(extractor=ext, cache=cache)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert profile.category == "recognized"
        assert ext.call_count == 0, "cache hit 시 extractor 호출 0"
        cache.lookup.assert_called_once_with("/tmp/fake.mp4")

    def test_cache_miss_calls_extractor_and_stores(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.85)],
            raw_response='{"motion_name": "ref-invert"}',
            raw_motion_name="ref-invert",
        )
        cache = MagicMock()
        cache.lookup.return_value = None
        rec = GeminiTechniqueRecognizer(extractor=ext, cache=cache)
        rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert ext.call_count == 1
        cache.store.assert_called_once()
        # store 인자 = (frames, payload dict)
        store_args, _ = cache.store.call_args
        assert store_args[0] == "/tmp/fake.mp4"
        assert "motion" in store_args[1]
        assert "joint_expectations" in store_args[1]


# ─────────────────── Test 11 (W1 fix): adapter source has no reject keywords ───────────────────


class TestAdapterPromptHygiene:
    """W1 fix — 어댑터 source 안의 prompt 박제 (있다면) 에 좌표/score 미박제.

    GeminiTechniqueRecognizer 자체는 prompt 박제 X (extractor 가 prompt 박제).
    spike + extractor source 검증으로 W1 fix 전체 정합 확인.
    """

    def test_adapter_module_has_no_prompt_with_coordinate_keyword(self) -> None:
        from sunity_shared.analysis import gemini_technique_recognizer as adapter

        # 어댑터는 prompt 박제 X. 'PROMPT' 같은 박제 keyword 자체가 없으면 OK.
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        # docstring / 주석 내부의 의미 있는 좌표 토큰 검사 — "x=", "kp[" 박제 X.
        assert "x=120" not in source
        assert "keypoint" not in source.lower()

    def test_spike_prompt_template_clean(self) -> None:
        # spike (Task 1 산출물) 의 prompt 가 W1 fix 정합인지 재검증 (Task 3 통합 sanity).
        from backend.research.spikes.spike_gemini_motion_classify import (
            _GEMINI_PROMPT_TEMPLATE,
        )

        assert "좌표" not in _GEMINI_PROMPT_TEMPLATE
        assert "점수" not in _GEMINI_PROMPT_TEMPLATE
        assert "score" not in _GEMINI_PROMPT_TEMPLATE.lower()
