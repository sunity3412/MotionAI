"""Task 0 (C2 fix) — GeminiTechniqueRecognizer 4 path 의 motion_id populate 검증.

박제 정신:
  - line 174 low_confidence path → motion_id is None (name="신뢰도 낮음")
  - line 197 unregistered path → motion_id is None (name="미등록: ...")
  - line 310 _build_profile 정상 path → motion_id == canonical motion (recognized)
  - line 322 _profile_from_cache → motion_id == cached["motion"]

extractor monkeypatch 박제 — google.genai 실 호출 0.

2026-09-20 (동시 분석 오염 수리) — extractor 의 `_last_raw_response` /
`_last_motion_name` 사이드카 속성이 폐기되고 raw 응답이 **반환값**이 됐다. 전역
싱글턴 extractor 에 값을 써 두고 Gemini 왕복 뒤에 되읽던 구조라, 동시 업로드가
들어오면 남의 응답/동작 이름으로 채점됐다. 여기 stub 도 새 계약
(`extract_key_moments_with_response` → (moments, raw_response)) 을 따른다.
동작 이름도 마찬가지로 인스턴스가 아니라 recognize(motion_hint=...) 로 넘긴다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _MockMoment:
    """KeyMoment mock — Gemini extractor 가 반환하는 모양."""

    moment_key: str = "hold"
    timestamp_seconds: float = 1.0
    confidence: float = 0.9
    frame_index: int = 9


class _MockExtractor:
    """GeminiMomentExtractor mock — (moments, raw_response) 를 반환한다.

    2026-09-20 동시 분석 오염 수리: raw 응답은 인스턴스 속성이 아니라 반환값이다.
    """

    def __init__(
        self,
        moments: list[_MockMoment] | None = None,
        raw_text: str = "ok",
    ) -> None:
        self._moments = moments if moments is not None else [_MockMoment()]
        self._raw_text = raw_text

    def extract_key_moments_with_response(
        self, video_uri, motion, *, preuploaded_handle=None
    ):
        # 27-04: recognizer 가 preuploaded_handle 전달 → stub 수용 (무시).
        return self._moments, self._raw_text


def test_gemini_build_profile_populates_motion_id() -> None:
    """정상 path — _build_profile("inversion", moments) → profile.motion_id == "inversion"."""
    from sunity_shared.analysis.gemini_technique_recognizer import (
        GeminiTechniqueRecognizer,
    )

    rec = GeminiTechniqueRecognizer()
    profile = rec._build_profile("inversion", moments=[])
    assert profile.motion_id == "inversion"
    assert profile.name == "inversion"
    assert profile.category == "recognized"


def test_gemini_low_confidence_path_motion_id_none(monkeypatch) -> None:
    """low confidence path — motion_id is None (name="신뢰도 낮음")."""
    import numpy as np

    from sunity_shared.analysis.gemini_technique_recognizer import (
        GeminiTechniqueRecognizer,
    )

    # extractor 가 low confidence 반환
    low_moment = _MockMoment(confidence=0.1)
    extractor = _MockExtractor(moments=[low_moment])

    # _adapter_reject_guard 의 lazy import 우회 — _enforce_no_coordinate_or_score noop
    from sunity_shared.analysis import gemini_technique_recognizer as gtr_mod

    monkeypatch.setattr(gtr_mod, "_adapter_reject_guard", lambda text, *, context: None)

    rec = GeminiTechniqueRecognizer(extractor=extractor, low_confidence_threshold=0.5)
    profile = rec.recognize(np.zeros((10, 8)), frames="/tmp/fake.mp4")
    assert profile.motion_id is None
    assert profile.category == "low_confidence"


def test_gemini_unregistered_path_motion_id_none(monkeypatch) -> None:
    """unregistered path — motion_id is None (name="미등록: ...")."""
    import numpy as np

    from sunity_shared.analysis.gemini_technique_recognizer import (
        GeminiTechniqueRecognizer,
    )
    from sunity_shared.analysis import gemini_technique_recognizer as gtr_mod

    monkeypatch.setattr(gtr_mod, "_adapter_reject_guard", lambda text, *, context: None)

    # classify_motion_name 가 unregistered 반환하도록 mock
    monkeypatch.setattr(
        gtr_mod,
        "classify_motion_name",
        lambda raw: (raw, "unregistered"),
    )

    # 2026-09-20 — 미등록 동작 이름은 **질의 문자열**로 표현한다. 예전엔 extractor 의
    # `_last_motion_name` 사이드카를 되읽었는데, 프로덕션에서 그 필드의 유일한 쓰기가
    # "호출자가 넘긴 질의" 였다 (Gemini 자체 분류명이 들어간 적 없음). 지금은
    # raw_motion_name = motion_query 이므로 motion_hint 로 넣는다.
    extractor = _MockExtractor()
    rec = GeminiTechniqueRecognizer(extractor=extractor)
    profile = rec.recognize(
        np.zeros((10, 8)), frames="/tmp/fake.mp4", motion_hint="obscure-move-9999"
    )
    assert profile.motion_id is None
    assert profile.category == "unregistered"
    # 미등록 이름이 profile 까지 흘러오는지 — 질의 문자열이 곧 raw_motion_name.
    assert profile.name == "미등록: obscure-move-9999"


def test_gemini_cache_path_motion_id_from_cached_motion() -> None:
    """cache hit path — _profile_from_cache({"motion": "split"}) → motion_id == "split"."""
    from sunity_shared.analysis.gemini_technique_recognizer import (
        GeminiTechniqueRecognizer,
    )

    rec = GeminiTechniqueRecognizer()
    profile = rec._profile_from_cache({"motion": "split", "joint_expectations": {}})
    assert profile.motion_id == "split"


def test_gemini_recognizer_keyword_motion_id_in_all_paths() -> None:
    """R1 정합 — 4 path 의 TechniqueProfile 생성자 호출이 keyword 박제 motion_id 사용.

    grep gate 의 보완 — 실제 instance 의 motion_id 가 정확히 populate.
    """
    from sunity_shared.analysis.gemini_technique_recognizer import (
        GeminiTechniqueRecognizer,
    )

    rec = GeminiTechniqueRecognizer()
    # _build_profile path
    p1 = rec._build_profile("inversion", moments=[])
    assert p1.motion_id == "inversion"
    # _profile_from_cache path
    p2 = rec._profile_from_cache({"motion": "split"})
    assert p2.motion_id == "split"
    # _profile_from_cache 가 motion 키 없을 때 None
    p3 = rec._profile_from_cache({})
    assert p3.motion_id is None
