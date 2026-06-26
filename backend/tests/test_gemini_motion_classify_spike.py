"""Plan 5-01 Task 1 — Gemini motion_name 분류 spike 단위 테스트.

stub mode 만 검증 (live mode 는 belle Pod 에서 실측, Plan 5-05).

박제 정신:
  · D-08: 좌표 / 점수 / 판단 reject patterns 가드 1차 (spike layer).
  · D-16: google.genai / boto3 / pydantic lazy import — 모듈 로드 시 0 import.
  · W1 fix: spike 의 _GEMINI_PROMPT_TEMPLATE 박제에 좌표 / score / 점수 keyword 0건.
  · B2 fix: spike 가 production classifier 를 import (역방향 금지).

모든 테스트는 stdlib + pytest 만 사용.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# B2 fix 검증 — spike 가 production classifier import 박제.
from sunity_shared.analysis.gemini_motion_classifier import (
    REGISTERED_MOTIONS,
    classify_motion_name,
)
from backend.research.spikes import spike_gemini_motion_classify as spike


_FIXTURE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "gemini_responses"
)
_FIXTURE_NAMES = (
    "ko_invert",
    "en_foxtop",
    "ipsf_split",
    "unregistered",
    "multi_word",
)


# ─────────────────── stub mode 정규화 path ───────────────────


class TestStubModeFixtures:
    """5 fixture 박제 정규화 path 검증."""

    @pytest.mark.parametrize("fixture_name", _FIXTURE_NAMES)
    def test_fixture_file_exists(self, fixture_name: str) -> None:
        path = _FIXTURE_DIR / f"{fixture_name}.json"
        assert path.exists(), f"fixture 미존재: {path}"

    def test_ko_motion_name_normalized(self) -> None:
        result = spike._run_stub(motion_hint="auto", fixture_name="ko_invert")
        assert result["raw_motion_name"] == "인버트"
        assert result["canonical_motion"] == "ref-invert"
        assert result["scope_status"] == "recognized"

    def test_en_motion_name_normalized(self) -> None:
        result = spike._run_stub(motion_hint="auto", fixture_name="en_foxtop")
        assert result["raw_motion_name"] == "Fox Top"
        assert result["canonical_motion"] == "ref-foxtop"
        assert result["scope_status"] == "recognized"

    def test_ipsf_code_normalized_via_substring(self) -> None:
        # "IPSF §4.2 Inverted Split (code XYZ)" → substring "inverted split" 매치.
        result = spike._run_stub(motion_hint="auto", fixture_name="ipsf_split")
        assert result["canonical_motion"] == "ref-foxtop-split"
        assert result["scope_status"] == "recognized"

    def test_unregistered_motion_name(self) -> None:
        # adapter (gemini_technique_recognizer) 가 `scope_status == "unregistered"`
        # 로 D-09 case 3 분기. canonical 위치 = raw_name 보존 (Firestore 분기 3 자동
        # 수집이 학원 통용 용어 그대로 저장).
        result = spike._run_stub(motion_hint="auto", fixture_name="unregistered")
        assert result["canonical_motion"] == "Aerial Yogi"
        assert result["scope_status"] == "unregistered"

    def test_multi_word_korean_substring_match(self) -> None:
        # "기본 사이드웨이 스핀 시연" → substring "사이드웨이 스핀" 매치.
        result = spike._run_stub(motion_hint="auto", fixture_name="multi_word")
        assert result["canonical_motion"] == "ref-sideway-spin"
        assert result["scope_status"] == "recognized"


# ─────────────────── REGISTERED_MOTIONS 정합 (D-01) ───────────────────


class TestRegisteredMotions:
    def test_registered_motions_set_matches_p1_scope(self) -> None:
        # P1 step 4 (2026-06-27): 5→10 scope 확장 (객관 무릎신전 5동작 등록).
        expected = {
            "ref-climb",
            "ref-foxtop",
            "ref-foxtop-split",
            "ref-invert",
            "ref-sideway-spin",
            "ref-kip-up",
            "ref-power-spin",
            "ref-peter-pan",
            "ref-elbow-twist-sister",
            "ref-pdshape",
        }
        assert REGISTERED_MOTIONS == expected

    def test_registered_motions_count_10(self) -> None:
        assert len(REGISTERED_MOTIONS) == 10


# ─────────────────── reject patterns 가드 (D-08, 1차) ───────────────────


class TestRejectPatternsGuard:
    """spike layer 1차 가드 — 좌표 / 점수 / 판단 응답 거부."""

    def _make_bad_fixture(
        self, tmp_path: Path, raw_text: str
    ) -> str:
        # spike._load_fixture 가 정해진 path 만 찾으므로, 직접 _enforce 만 검증.
        return raw_text

    def test_coordinate_in_raw_text_rejected(self, tmp_path: Path) -> None:
        bad_text = '{"motion_name": "ref-invert", "left_knee x=120 y=80": true}'
        with pytest.raises(ValueError, match="좌표"):
            spike._enforce_no_reject_patterns(bad_text, context="test")

    def test_score_in_raw_text_rejected(self) -> None:
        bad_text = '{"motion_name": "ref-invert", "description": "85점 입니다"}'
        with pytest.raises(ValueError, match="점수"):
            spike._enforce_no_reject_patterns(bad_text, context="test")

    def test_judgment_in_raw_text_rejected(self) -> None:
        bad_text = '{"motion_name": "ref-invert", "verdict": "passed"}'
        with pytest.raises(ValueError, match="심사"):
            spike._enforce_no_reject_patterns(bad_text, context="test")


# ─────────────────── lazy import 검증 (D-16) ───────────────────


class TestLazyImport:
    """spike 모듈 로드 시 무거운 SDK 미import 검증.

    pytest 의 다른 테스트가 google.genai / boto3 / pydantic 를 import 할 수 있으므로,
    spike 모듈 자체가 top-level 에서 import 하지 않는 것만 검증한다 (소스 grep).
    """

    def test_spike_module_source_does_not_import_google_genai_at_top_level(
        self,
    ) -> None:
        source = Path(spike.__file__).read_text(encoding="utf-8")
        # top-level (function 외부) 에서 google import 가 없는지 — 함수 안 indent 박제.
        # 단순 grep: "from google import genai" 가 들여쓰기 0 줄에 등장하면 fail.
        for line in source.splitlines():
            if line.startswith("from google") or line.startswith("import google"):
                pytest.fail(
                    f"spike module top-level 에 google import 박제: '{line}'. "
                    f"D-16 lazy import 위반."
                )

    def test_spike_module_source_does_not_import_boto3_at_top_level(self) -> None:
        source = Path(spike.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.startswith("import boto3") or line.startswith("from boto3"):
                pytest.fail(
                    f"spike module top-level 에 boto3 import 박제: '{line}'. "
                    f"D-16 lazy import 위반."
                )

    def test_spike_module_source_does_not_import_pydantic_at_top_level(self) -> None:
        source = Path(spike.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.startswith("import pydantic") or line.startswith("from pydantic"):
                pytest.fail(
                    f"spike module top-level 에 pydantic import 박제: '{line}'. "
                    f"D-16 lazy import 위반."
                )


# ─────────────────── W1 fix: prompt 텍스트 박제 검증 ───────────────────


class TestPromptText:
    """W1 fix — spike prompt 텍스트에 좌표 / score / 점수 keyword 0건."""

    def test_prompt_template_has_no_coordinate_keyword(self) -> None:
        prompt = spike._GEMINI_PROMPT_TEMPLATE
        assert "좌표" not in prompt, "W1 fix 위반: prompt 에 '좌표' keyword 박제"
        assert "pixel" not in prompt.lower(), "W1 fix 위반: prompt 에 'pixel' keyword 박제"
        assert "keypoint" not in prompt.lower(), (
            "W1 fix 위반: prompt 에 'keypoint' keyword 박제"
        )

    def test_prompt_template_has_no_score_keyword(self) -> None:
        prompt = spike._GEMINI_PROMPT_TEMPLATE
        assert "점수" not in prompt, "W1 fix 위반: prompt 에 '점수' keyword 박제"
        assert "score" not in prompt.lower(), "W1 fix 위반: prompt 에 'score' keyword 박제"

    def test_prompt_template_mentions_5_registered_motions(self) -> None:
        prompt = spike._GEMINI_PROMPT_TEMPLATE
        for motion in REGISTERED_MOTIONS:
            assert motion in prompt, (
                f"prompt 에 등재 motion ID '{motion}' 박제 누락"
            )
