"""Plan 5-01 Task 3 (W4 fix 신설) — GeminiTechniqueRecognizer 어댑터 단위 테스트.

mock 박제만 — google.genai / boto3 / firebase_admin 실 호출 0.

박제 정신:
  · D-04 / D-05 / D-08 / D-09 / D-13 / D-16
  · [[analysis-objectivity-no-human-scores]] reject patterns 2차 가드
  · B2 fix: production classifier 직접 호출 검증
  · B3 fix: unregistered_hook 인자 = (keyword, video_hash) — video_path X
  · B5 fix: raw_text 가 reject patterns 입력으로 도달함 단위 시험

2026-09-20 (동시 분석 오염 수리) 계약 변경 반영:
  · extractor 가 (moments, raw_response) 를 **반환**한다 — `_last_raw_response` /
    `_last_motion_name` 사이드카 속성 폐기. 전역 싱글턴 extractor 를 두 분석이 동시에
    쓸 때, 값을 써 두고 Gemini 왕복 뒤에 되읽는 구조가 서로를 덮어썼다.
  · 질의할 동작 이름은 `recognize(motion_hint=...)` 인자다. 예전 `raw_motion_name` 은
    extractor 가 되돌려준 이름처럼 보였지만 프로덕션의 유일한 쓰기가
    `self._last_motion_name = motion` (= 호출자가 넘긴 질의) 였다 — Gemini 자체 분류명이
    그 필드에 들어간 적은 없다. 그래서 스텁도 이름을 "돌려주지" 않는다.
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

    2026-09-20 동시 분석 오염 수리 — 운영 경로가 부르는 메서드는
    `extract_key_moments_with_response` 하나이고, raw 응답을 **반환값**으로 준다.
    스텁도 사이드카 속성을 두지 않는다 (속성을 두면 이 테스트가 없앤 고장을 다시 박제).

    `last_motion_query` 는 스텁이 **받은** 질의 문자열 기록 — 분석-로컬 motion_hint 가
    extractor 까지 그대로 도달하는지 검증용 (쓰기 아님, 호출 관찰).
    """

    def __init__(
        self,
        *,
        moments: list,
        raw_response: str = "",
        raise_on_call: Exception | None = None,
    ) -> None:
        self._moments = list(moments)
        self._raw_response = raw_response
        self._raise = raise_on_call
        self.call_count = 0
        self.last_motion_query: str | None = None

    def extract_key_moments_with_response(
        self, video_uri: str, motion: str, *, preuploaded_handle=None
    ) -> tuple[list, str]:
        # 27-04: recognizer 가 preuploaded_handle 을 전달하므로 stub 도 수용 (무시).
        self.call_count += 1
        self.last_motion_query = motion
        if self._raise is not None:
            raise self._raise
        return list(self._moments), self._raw_response


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
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        # 2026-09-20 — 질의할 동작은 분석-로컬 인자다 (mode1 = referenceMotionId).
        profile = rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
        )
        assert profile.category == "recognized"
        assert profile.name == "ref-invert"
        # joint_expectations 가 JOINT_KEYS 8개 모두 포함.
        assert set(profile.joint_expectations.keys()) == set(JOINT_KEYS)
        # motion_hint 가 인스턴스를 경유하지 않고 extractor 까지 그대로 도달.
        assert ext.last_motion_query == "ref-invert"

    def test_no_motion_hint_queries_auto(self) -> None:
        # mode3 처럼 기준 동작이 없으면 Gemini 자체 분류 질의 "auto".
        # "auto" 는 REGISTERED_MOTIONS 밖 → unregistered (D-09 case 3).
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.2, 0.85)],
            raw_response='{"motion_name": "auto"}',
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")
        assert ext.last_motion_query == "auto"
        assert profile.category == "unregistered"


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
        )
        rec = GeminiTechniqueRecognizer(extractor=ext, low_confidence_threshold=0.5)
        profile = rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
        )
        assert profile.category == "low_confidence"
        assert profile.joint_expectations == {}
        assert profile.name == "신뢰도 낮음"

    def test_empty_moments_treated_as_low_confidence(self) -> None:
        # moments=[] → mean_conf=0.0 → low_confidence.
        ext = _StubExtractor(
            moments=[],
            raw_response='{"motion_name": "ref-invert"}',
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
        )
        assert profile.category == "low_confidence"


# ─────────────────── Test 4: unregistered + hook (B3 fix) ───────────────────


class TestUnregisteredPath:
    """D-09 case 3 — unregistered + hook 호출 + video_hash 인자 검증.

    2026-09-20 — 미등록 동작은 `motion_hint` 로 **질의**해서 표현한다. 예전 스텁의
    raw_motion_name 은 프로덕션에 없는 동작(Gemini 가 질의와 다른 이름을 돌려주는 것)
    이었다. hook 은 경로가 둘 — 생성 시점 기본값과 recognize() 인자.
    """

    def test_unregistered_motion_returns_empty_expectations(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 5.0, 0.8)],
            raw_response='{"motion_name": "Aerial Yogi"}',
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="Aerial Yogi"
        )
        assert profile.category == "unregistered"
        assert profile.joint_expectations == {}
        assert "Aerial Yogi" in profile.name

    def test_unregistered_hook_called_with_keyword_and_video_hash(self) -> None:
        # B3 fix 검증 — hook(keyword, video_hash). video_path 박제 X.
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 5.0, 0.8)],
            raw_response='{"motion_name": "Aerial Yogi"}',
        )
        hook = MagicMock()
        rec = GeminiTechniqueRecognizer(extractor=ext, unregistered_hook=hook)
        rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="Aerial Yogi"
        )
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
        )

        def _failing_hook(keyword: str, video_hash: str) -> None:
            raise RuntimeError("Firestore down")

        rec = GeminiTechniqueRecognizer(
            extractor=ext, unregistered_hook=_failing_hook
        )
        profile = rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="Unknown Move"
        )
        # hook 실패해도 unregistered profile 반환.
        assert profile.category == "unregistered"

    def test_call_arg_hook_overrides_instance_default(self) -> None:
        # 2026-09-20 신설 — 인자가 인스턴스 기본값을 이긴다.
        # 프로덕션에서 분석마다 다른 것(caller uid 를 문 클로저)은 인자로 오고,
        # 인스턴스 기본값은 전역 싱글턴이 물고 있는 상수다. 인자가 이겨야
        # A 의 분석이 B 의 uid 로 수집되지 않는다.
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 5.0, 0.8)],
            raw_response='{"motion_name": "Aerial Yogi"}',
        )
        instance_hook = MagicMock()
        call_hook = MagicMock()
        rec = GeminiTechniqueRecognizer(
            extractor=ext, unregistered_hook=instance_hook
        )
        rec.recognize(
            _angles_8j(),
            frames="/tmp/fake.mp4",
            motion_hint="Aerial Yogi",
            unregistered_hook=call_hook,
        )
        call_hook.assert_called_once()
        assert call_hook.call_args[0][0] == "Aerial Yogi"
        instance_hook.assert_not_called()

    def test_instance_hook_used_when_call_arg_omitted(self) -> None:
        # 인자 None → 인스턴스 기본값 사용 (기존 생성자 경로 유지).
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 5.0, 0.8)],
            raw_response='{"motion_name": "Aerial Yogi"}',
        )
        instance_hook = MagicMock()
        rec = GeminiTechniqueRecognizer(
            extractor=ext, unregistered_hook=instance_hook
        )
        rec.recognize(
            _angles_8j(),
            frames="/tmp/fake.mp4",
            motion_hint="Aerial Yogi",
            unregistered_hook=None,
        )
        instance_hook.assert_called_once()


# ─────────────── Test 4-b (2026-09-20): 생성 이후 속성 대입 차단 ───────────────


class TestPostConstructionAssignmentBlocked:
    """동시 분석 오염 수리의 구조적 보증 — 분석별 값을 인스턴스에 써 둘 수 없다.

    이 인식기는 pipeline 의 모듈 전역 싱글턴이다. 예전 호출자는 속성에 값을 써 두고
    recognize() 가 포즈 추론(51~177초) **뒤에** 되읽었고, 그 창에서 다른 분석이
    덮어썼다. 비-frozen dataclass 는 선언되지 않은 이름에도 대입이 조용히 성공하므로,
    옛 호출자가 말없이 no-op 이 되지 않도록 AttributeError 로 막는다.
    """

    def test_motion_query_hint_assignment_raises(self) -> None:
        rec = GeminiTechniqueRecognizer(extractor=_StubExtractor(moments=[]))
        with pytest.raises(AttributeError, match="motion_hint"):
            rec.motion_query_hint = "ref-invert"

    def test_unregistered_hook_assignment_raises(self) -> None:
        rec = GeminiTechniqueRecognizer(extractor=_StubExtractor(moments=[]))
        with pytest.raises(AttributeError):
            rec.unregistered_hook = MagicMock()


# ─────────────────── Test 5: B5 fix — raw_text 2차 가드 ───────────────────


class TestRejectPatternsSecondaryGuard:
    """B5 fix 검증 — extractor 가 **반환한** raw 응답이 좌표 포함 → 어댑터 2차 가드 ValueError.

    raw_text 가 reject patterns 입력으로 도달함을 단위 검증. 의도 불변, 전달 경로만
    사이드카 속성(`_last_raw_response`) → 반환값으로 바뀌었다 (2026-09-20).
    """

    def test_coordinate_in_raw_response_triggers_value_error(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.8)],
            # B5 fix — extractor 반환 raw 응답이 좌표 포함.
            raw_response='{"left_knee": "x=120 y=80"}',
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        with pytest.raises(ValueError, match="좌표"):
            rec.recognize(
                _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
            )

    def test_score_in_raw_response_triggers_value_error(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.8)],
            raw_response='{"description": "이 동작은 85점 입니다"}',
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        with pytest.raises(ValueError, match="점수"):
            rec.recognize(
                _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
            )

    def test_clean_raw_response_passes_secondary_guard(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.8)],
            raw_response='{"motion_name": "ref-invert", "description": "동작 완성"}',
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
        )
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
    def test_default_model_comes_from_config_region_c(self) -> None:
        """moment extractor 기본 모델 = config 영역 C — raw string 박제 금지.

        ~~D-13(2026-06-04) 'gemini-3.1-pro-preview 고정'~~ 은 이후 27-09/D-05 가
        moment extractor 만 Flash 로 스코핑하면서 이 모듈에 한해 대체됐다. 그런데
        폴백은 그 뒤로도 갱신에서 누락돼 **2026-08-28 까지 `gemini-2.5-pro`**(08-18
        이후 ALLOWED_MODELS 밖 = 영구 금지 모델)로 남아 있었다.

        그래서 문자열을 다시 박지 않는다 — 박으면 같은 방식으로 또 낡는다.
        불변식만 검사한다: (1) config 영역 C 기본값과 일치, (2) 화이트리스트 통과.
        모델을 올릴 때 손대야 하는 곳은 gemini/config.py 한 곳이면 된다.
        """
        from sunity_shared.gemini.config import ALLOWED_MODELS, DEFAULT_C_MODEL

        assert DEFAULT_GEMINI_MODEL == DEFAULT_C_MODEL, (
            "moment extractor 기본값이 config 영역 C 와 어긋났다 — raw string 박제 의심"
        )
        assert DEFAULT_GEMINI_MODEL in ALLOWED_MODELS, (
            f"{DEFAULT_GEMINI_MODEL} 은 ALLOWED_MODELS 밖 — resolve_model 가 거부하는 모델"
        )


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
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
        )
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
        )
        rec = GeminiTechniqueRecognizer(extractor=ext)
        profile = rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-climb"
        )
        assert set(profile.joint_expectations.keys()) == set(JOINT_KEYS)
        # ref-climb hold_moment = [] → 모든 관절 BENT_OK.
        assert all(
            v == JOINT_BENT_OK for v in profile.joint_expectations.values()
        ), "ref-climb 은 hold_moment 빈 list → 8관절 BENT_OK 박제"


# ─────────────────── Test 10: cache lookup short-circuit ───────────────────


class TestCacheShortCircuit:
    """cache.lookup 가 dict 반환 시 extractor 미호출."""

    def test_cache_hit_skips_extractor(self) -> None:
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.0, 0.85)],
            raw_response='{"motion_name": "ref-invert"}',
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
        )
        cache = MagicMock()
        cache.lookup.return_value = None
        rec = GeminiTechniqueRecognizer(extractor=ext, cache=cache)
        rec.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
        )
        assert ext.call_count == 1
        cache.store.assert_called_once()
        # store 인자 = (frames, payload dict)
        store_args, _ = cache.store.call_args
        assert store_args[0] == "/tmp/fake.mp4"
        assert "motion" in store_args[1]
        assert "joint_expectations" in store_args[1]


# ─────────────────── Test 10-b (33-A4 수리): cache hit hold_window 복원 ───────────────────


class TestCacheHoldWindowRestore:
    """33-A4-PHASE-EVIDENCE §5 끊긴 지점 1 회귀 방지.

    캐시 히트 경로가 hold_window(yaml hold_moment 국면 게이트의 유일한 구현)를
    복원하지 않으면 dimensions._select_window 가 국면 무관 분산 최소 자동 창으로
    폴백한다. 본 클래스는 캐시 경로가 신선 경로와 동일한 hold_window 를 내는지
    (동작 무관, 구조 불변식)를 검증한다.
    """

    def _cache_hit_profile(self, payload: dict) -> TechniqueProfile:
        cache = MagicMock()
        cache.lookup.return_value = payload
        rec = GeminiTechniqueRecognizer(extractor=MagicMock(), cache=cache)
        return rec.recognize(_angles_8j(), frames="/tmp/fake.mp4")

    def test_cache_hit_restores_hold_window(self) -> None:
        # 단일 hold moment 7.0s → ±2초 창 = (5.0*9, 9.0*9) = (45, 81).
        profile = self._cache_hit_profile(
            {
                "motion": "ref-invert",
                "joint_expectations": {jk: JOINT_BENT_OK for jk in JOINT_KEYS},
                "moments": [
                    {
                        "moment_key": "hold",
                        "timestamp_seconds": 7.0,
                        "confidence": 0.85,
                        "frame_index": 63,
                    }
                ],
            }
        )
        assert profile.hold_window == (45, 81), (
            "cache hit 시 hold_window 미복원 — 국면 게이트 소실 (33-A4 §5 재발)"
        )

    def test_fresh_and_cache_paths_produce_identical_hold_window(self) -> None:
        # 구조 불변식: 같은 moments 라면 신선 경로 profile 과 캐시 round-trip
        # profile 의 hold_window 가 동일해야 한다.
        ext = _StubExtractor(
            moments=[_StubMoment("hold", 7.2, 0.85)],
            raw_response='{"motion_name": "ref-invert"}',
        )
        store_cache = MagicMock()
        store_cache.lookup.return_value = None
        rec_fresh = GeminiTechniqueRecognizer(extractor=ext, cache=store_cache)
        fresh_profile = rec_fresh.recognize(
            _angles_8j(), frames="/tmp/fake.mp4", motion_hint="ref-invert"
        )
        assert fresh_profile.hold_window is not None, "신선 경로 hold_window 전제"

        # 신선 경로가 store 한 payload 그대로 캐시 히트로 재현.
        store_args, _ = store_cache.store.call_args
        cached_payload = store_args[1]
        cached_profile = self._cache_hit_profile(cached_payload)
        assert cached_profile.hold_window == fresh_profile.hold_window, (
            "캐시 히트 profile 의 hold_window 가 신선 경로와 다름 — 코드 2벌 분기"
        )

    def test_cache_hit_without_hold_moment_keeps_hold_window_none(self) -> None:
        # hold moment 없음 → None (자동 창 폴백 유지, 가짜 창 생성 금지).
        profile = self._cache_hit_profile(
            {
                "motion": "ref-invert",
                "joint_expectations": {jk: JOINT_BENT_OK for jk in JOINT_KEYS},
                "moments": [
                    {
                        "moment_key": "setup",
                        "timestamp_seconds": 1.0,
                        "confidence": 0.9,
                        "frame_index": 9,
                    }
                ],
            }
        )
        assert profile.hold_window is None

    def test_hold_window_survives_key_moments_restore_failure(self) -> None:
        # KeyMoment dataclass 복원 실패(비수치 confidence → Layer 2 비활성)와
        # 독립적으로 hold_window 는 raw dict 에서 복원되어야 한다.
        profile = self._cache_hit_profile(
            {
                "motion": "ref-invert",
                "joint_expectations": {jk: JOINT_BENT_OK for jk in JOINT_KEYS},
                "moments": [
                    {
                        "moment_key": "hold",
                        "timestamp_seconds": 7.0,
                        "confidence": "not-a-number",
                        "frame_index": 63,
                    }
                ],
            }
        )
        assert profile.key_moments is None, "비수치 confidence → Layer 2 비활성 전제"
        assert profile.hold_window == (45, 81), (
            "Layer 2 복원 실패가 hold_window 복원까지 무너뜨림 — 결합 금지"
        )


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
