"""GeminiMomentExtractor 단위 테스트 (Plan 01-13 T-1).

목적:
  · KeyMoment.validate() 가드 — moment_key / timestamp / frame_index / confidence.
  · Gemini 응답 좌표/점수/판단 정규식 차단 — SCORE-01 1차 차단선.
  · API 키 로드 — env 우선 → AWS Parameter Store fallback → 둘 다 없으면 RuntimeError.
  · 응답 캐시 동작 — 같은 (video_uri, motion, model) 재호출 시 SDK 미호출.
  · markdown fence 응답 흡수.
  · assign_frame_indices — fps + frames_total 로 frame_index 채우기.

모든 테스트는 stdlib + pytest 만 사용 (mmpose / torch / google.generativeai / boto3 미import).
"""

from __future__ import annotations

import json

import pytest

from sunity_shared.judging import (
    GeminiMomentExtractor,
    KeyMoment,
    assign_frame_indices,
)
from sunity_shared.judging.gemini_moment_extractor import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_API_KEY_PARAM_NAME,
    _enforce_no_coordinate_or_score,
    _load_api_key,
    _parse_gemini_response,
    _strip_markdown_fence,
)
from sunity_shared.judging.geometric_criterion import VALID_MOMENT_KEYS


# ─────────────────── KeyMoment.validate() ───────────────────


def _valid_moment() -> KeyMoment:
    return KeyMoment(
        motion="ref-invert",
        moment_key="hold",
        timestamp_seconds=7.2,
        frame_index=64,
        confidence=0.85,
        source_response_excerpt='{"moments":[{"moment_key":"hold"}]}',
    )


class TestKeyMomentValidate:
    def test_valid_passes(self) -> None:
        _valid_moment().validate()  # no raise

    def test_invalid_moment_key_rejected(self) -> None:
        m = KeyMoment(
            motion="ref-invert",
            moment_key="bogus",
            timestamp_seconds=1.0,
            frame_index=1,
            confidence=0.5,
            source_response_excerpt="setup",
        )
        with pytest.raises(ValueError) as exc:
            m.validate()
        # 4 유효값이 모두 메시지에 포함
        for k in VALID_MOMENT_KEYS:
            assert k in str(exc.value)

    def test_negative_timestamp_rejected(self) -> None:
        m = KeyMoment(
            motion="ref-invert",
            moment_key="hold",
            timestamp_seconds=-0.1,
            frame_index=1,
            confidence=0.5,
            source_response_excerpt="setup",
        )
        with pytest.raises(ValueError, match="timestamp_seconds"):
            m.validate()

    def test_negative_frame_index_rejected(self) -> None:
        m = KeyMoment(
            motion="ref-invert",
            moment_key="hold",
            timestamp_seconds=1.0,
            frame_index=-1,
            confidence=0.5,
            source_response_excerpt="setup",
        )
        with pytest.raises(ValueError, match="frame_index"):
            m.validate()

    @pytest.mark.parametrize("conf", [-0.01, 1.01, 2.0])
    def test_confidence_out_of_range_rejected(self, conf: float) -> None:
        m = KeyMoment(
            motion="ref-invert",
            moment_key="hold",
            timestamp_seconds=1.0,
            frame_index=1,
            confidence=conf,
            source_response_excerpt="setup",
        )
        with pytest.raises(ValueError, match="confidence"):
            m.validate()

    def test_excerpt_with_coordinate_rejected(self) -> None:
        m = KeyMoment(
            motion="ref-invert",
            moment_key="hold",
            timestamp_seconds=1.0,
            frame_index=1,
            confidence=0.5,
            source_response_excerpt="hip x=120 y=80",
        )
        with pytest.raises(ValueError, match="좌표"):
            m.validate()

    def test_excerpt_with_score_rejected(self) -> None:
        m = KeyMoment(
            motion="ref-invert",
            moment_key="hold",
            timestamp_seconds=1.0,
            frame_index=1,
            confidence=0.5,
            source_response_excerpt="이 동작은 85점 입니다.",
        )
        with pytest.raises(ValueError, match="점수"):
            m.validate()


# ─────────────────── 좌표/점수/판단 정규식 가드 ───────────────────


class TestRejectPatterns:
    @pytest.mark.parametrize(
        "text",
        [
            "x: 120, y: 80",
            "X=120",
            "kp[0] = something",
            "keypoint left_knee at x=180",
            "좌표 x=120",
            "픽셀 좌표 출력",
            "pixel x=120",
        ],
    )
    def test_coordinate_patterns_rejected(self, text: str) -> None:
        with pytest.raises(ValueError, match="좌표"):
            _enforce_no_coordinate_or_score(text, context="test")

    @pytest.mark.parametrize(
        "text",
        [
            "score: 85",
            "Score = 92",
            "이 동작은 85점 입니다",
            "out of 100",
            "85/100 정도",
        ],
    )
    def test_score_patterns_rejected(self, text: str) -> None:
        with pytest.raises(ValueError, match="점수"):
            _enforce_no_coordinate_or_score(text, context="test")

    @pytest.mark.parametrize(
        "text",
        [
            "심사 결과 통과",
            "judgment: pass",
            "verdict: failed",
            "this run passed",
        ],
    )
    def test_judgment_patterns_rejected(self, text: str) -> None:
        with pytest.raises(ValueError, match="심사"):
            _enforce_no_coordinate_or_score(text, context="test")

    def test_clean_text_passes(self) -> None:
        # 좌표/점수/판단 없는 일반 description 은 통과
        _enforce_no_coordinate_or_score(
            "동작이 완성되어 정지한 시점입니다.",
            context="test",
        )

    def test_empty_text_is_noop(self) -> None:
        # 빈 응답은 가드의 책임 아님 (필수 키 누락 가드가 별도로 처리)
        _enforce_no_coordinate_or_score("", context="test")


# ─────────────────── API 키 로드 ───────────────────


class TestLoadApiKey:
    def test_env_key_wins_over_param_store(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "env-key-value")
        # boto3 가 호출되면 fail — env 가 우선해야 SSM 안 만져야 함
        assert _load_api_key() == "env-key-value"

    def test_missing_env_and_no_boto3_raises_runtime(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        # boto3 미설치 시뮬레이션
        import builtins

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "boto3":
                raise ImportError("simulated: boto3 not installed")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(RuntimeError, match="boto3"):
            _load_api_key()

    def test_default_param_name_constant(self) -> None:
        assert GEMINI_API_KEY_PARAM_NAME == "/sunity/motion/gemini-api-key"


# ─────────────────── Gemini 응답 파싱 ───────────────────


_VALID_GEMINI_RESPONSE = json.dumps(
    {
        "moments": [
            {
                "moment_key": "hold",
                "timestamp_seconds": 7.2,
                "confidence": 0.85,
                "description": "동작이 완성되어 정지한 시점",
            },
            {
                "moment_key": "setup",
                "timestamp_seconds": 1.0,
                "confidence": 0.7,
                "description": "동작 진입 준비",
            },
        ]
    }
)


class TestParseResponse:
    def test_clean_response_parses(self) -> None:
        moments = _parse_gemini_response("ref-invert", _VALID_GEMINI_RESPONSE)
        assert len(moments) == 2
        assert moments[0].moment_key == "hold"
        assert moments[0].timestamp_seconds == 7.2
        assert moments[0].confidence == 0.85
        # frame_index 는 placeholder (caller 가 fps 로 후처리)
        assert moments[0].frame_index == 0

    def test_markdown_fence_response_parses(self) -> None:
        wrapped = "```json\n" + _VALID_GEMINI_RESPONSE + "\n```"
        moments = _parse_gemini_response("ref-invert", wrapped)
        assert len(moments) == 2

    def test_invalid_json_rejected(self) -> None:
        with pytest.raises(ValueError, match="JSON 파싱"):
            _parse_gemini_response("ref-invert", "{not json}")

    def test_non_dict_top_level_rejected(self) -> None:
        with pytest.raises(ValueError, match="dict 가 아님"):
            _parse_gemini_response("ref-invert", '["just", "a", "list"]')

    def test_missing_moments_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="moments"):
            _parse_gemini_response("ref-invert", '{"foo": "bar"}')

    def test_invalid_moment_key_in_response_rejected(self) -> None:
        bad = json.dumps(
            {
                "moments": [
                    {
                        "moment_key": "bogus_phase",
                        "timestamp_seconds": 1.0,
                        "confidence": 0.5,
                    }
                ]
            }
        )
        with pytest.raises(ValueError, match="moment_key"):
            _parse_gemini_response("ref-invert", bad)

    def test_missing_required_field_rejected(self) -> None:
        bad = json.dumps(
            {
                "moments": [
                    {
                        "moment_key": "hold",
                        # timestamp_seconds 누락
                        "confidence": 0.5,
                    }
                ]
            }
        )
        with pytest.raises(ValueError, match="필수 키 누락"):
            _parse_gemini_response("ref-invert", bad)

    def test_response_with_coordinate_rejected(self) -> None:
        # raw text 자체가 좌표 포함 → 파싱 전에 거부
        bad = json.dumps(
            {
                "moments": [
                    {
                        "moment_key": "hold",
                        "timestamp_seconds": 1.0,
                        "confidence": 0.5,
                        "description": "left_knee x=120 y=80",
                    }
                ]
            }
        )
        with pytest.raises(ValueError, match="좌표"):
            _parse_gemini_response("ref-invert", bad)

    def test_response_with_score_in_description_rejected(self) -> None:
        bad = json.dumps(
            {
                "moments": [
                    {
                        "moment_key": "hold",
                        "timestamp_seconds": 1.0,
                        "confidence": 0.5,
                        "description": "85점 수준의 동작",
                    }
                ]
            }
        )
        with pytest.raises(ValueError, match="점수"):
            _parse_gemini_response("ref-invert", bad)

    def test_negative_timestamp_in_response_rejected(self) -> None:
        bad = json.dumps(
            {
                "moments": [
                    {
                        "moment_key": "hold",
                        "timestamp_seconds": -1.0,
                        "confidence": 0.5,
                    }
                ]
            }
        )
        with pytest.raises(ValueError, match="timestamp_seconds"):
            _parse_gemini_response("ref-invert", bad)


# ─────────────────── markdown fence helper ───────────────────


class TestStripMarkdownFence:
    def test_plain_text_unchanged(self) -> None:
        assert _strip_markdown_fence('{"a":1}') == '{"a":1}'

    def test_json_fence_stripped(self) -> None:
        assert (
            _strip_markdown_fence('```json\n{"a":1}\n```').strip() == '{"a":1}'
        )

    def test_plain_fence_stripped(self) -> None:
        assert _strip_markdown_fence('```\n{"a":1}\n```').strip() == '{"a":1}'


# ─────────────────── GeminiMomentExtractor ───────────────────


class _StubExtractor(GeminiMomentExtractor):
    """Test double — _call_gemini 를 stub. SDK 의존성 0."""

    def __init__(self, stub_response: str) -> None:
        super().__init__(api_key_loader=lambda: "stub-key")
        self._stub_response = stub_response
        self.call_count = 0

    def _call_gemini(
        self, video_uri: str, motion: str, *, preuploaded_handle=None
    ) -> str:
        # 27-04: base 가 preuploaded_handle kwarg 를 전달하므로 stub 도 수용 (무시).
        self.call_count += 1
        return self._stub_response


class TestExtractor:
    def test_extract_returns_parsed_moments(self) -> None:
        ext = _StubExtractor(_VALID_GEMINI_RESPONSE)
        moments = ext.extract_key_moments("/tmp/fake.mp4", "ref-invert")
        assert len(moments) == 2
        assert {m.moment_key for m in moments} == {"hold", "setup"}

    def test_cache_skips_second_call(self) -> None:
        ext = _StubExtractor(_VALID_GEMINI_RESPONSE)
        ext.extract_key_moments("/tmp/fake.mp4", "ref-invert")
        ext.extract_key_moments("/tmp/fake.mp4", "ref-invert")
        assert ext.call_count == 1

    def test_cache_keyed_by_motion(self) -> None:
        ext = _StubExtractor(_VALID_GEMINI_RESPONSE)
        ext.extract_key_moments("/tmp/fake.mp4", "ref-invert")
        ext.extract_key_moments("/tmp/fake.mp4", "ref-foxtop")
        # 다른 motion → 새 호출
        assert ext.call_count == 2

    def test_default_model_constant(self) -> None:
        # Phase 5 D-13 (belle 2026-06-04 확정) — Gemini 3.1 Pro 단일.
        # fix v2 2026-06-05: gemini-3.1-pro-preview (gemini-3-pro-preview deprecated).
        ext = _StubExtractor(_VALID_GEMINI_RESPONSE)
        assert ext.model_name == DEFAULT_GEMINI_MODEL == "gemini-3.1-pro-preview"


# ─────────────────── assign_frame_indices ───────────────────


class TestAssignFrameIndices:
    def test_basic_assignment(self) -> None:
        moments = [
            KeyMoment(
                motion="ref-invert",
                moment_key="hold",
                timestamp_seconds=7.0,
                frame_index=0,
                confidence=0.85,
                source_response_excerpt="hold",
            ),
            KeyMoment(
                motion="ref-invert",
                moment_key="setup",
                timestamp_seconds=1.0,
                frame_index=0,
                confidence=0.7,
                source_response_excerpt="setup",
            ),
        ]
        filled = assign_frame_indices(moments, fps=9.0, frames_total=100)
        # 7.0 * 9.0 = 63
        assert filled[0].frame_index == 63
        # 1.0 * 9.0 = 9
        assert filled[1].frame_index == 9

    def test_clamp_to_frames_total(self) -> None:
        moments = [
            KeyMoment(
                motion="ref-invert",
                moment_key="hold",
                timestamp_seconds=100.0,
                frame_index=0,
                confidence=0.85,
                source_response_excerpt="hold",
            )
        ]
        filled = assign_frame_indices(moments, fps=9.0, frames_total=50)
        assert filled[0].frame_index == 49

    def test_invalid_fps_raises(self) -> None:
        with pytest.raises(ValueError, match="fps"):
            assign_frame_indices([], fps=0, frames_total=10)

    def test_invalid_frames_total_raises(self) -> None:
        with pytest.raises(ValueError, match="frames_total"):
            assign_frame_indices([], fps=9.0, frames_total=0)

    def test_validate_runs_after_assignment(self) -> None:
        # invalid moment_key 가 KeyMoment 자체에 들어있으면 assign_frame_indices 단계에서 validate 거부
        moments = [
            KeyMoment(
                motion="ref-invert",
                moment_key="invalid",
                timestamp_seconds=1.0,
                frame_index=0,
                confidence=0.85,
                source_response_excerpt="x",
            )
        ]
        with pytest.raises(ValueError, match="moment_key"):
            assign_frame_indices(moments, fps=9.0, frames_total=10)
