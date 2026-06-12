"""Plan 17-01 Task 1 — 객관성 reject regex (G1) hard fail 단위 테스트.

박제 정신:
  · [[analysis-objectivity-no-human-scores]] 헌장 — Gemini 응답이 사람 점수/좌표/판단을
    출력하면 graceful 폴백 X, 반드시 ValueError raise. 시스템 의미 자체를 지키는 가드.
  · AI-SPEC §6 G1 "hard fail" 박제 — `_enforce_no_reject_patterns(text, context, allow_coords=False)`.
  · 영역 D (KeypointRefinement) 만 좌표 패턴 우회 — `allow_coords=True` opt-in.

mock 불필요 — pure regex. 외부 의존 0.
"""

from __future__ import annotations

import pytest

from sunity_shared.gemini import _enforce_no_reject_patterns


# ─────────────────── 점수 패턴 (graceful X — ValueError) ───────────────────


class TestScoreRejectPatterns:
    def test_korean_single_score_phrase_rejected(self) -> None:
        with pytest.raises(ValueError, match="점수"):
            _enforce_no_reject_patterns("이 자세는 87점이다", context="coach")

    def test_decimal_korean_score_rejected(self) -> None:
        with pytest.raises(ValueError, match="점수"):
            _enforce_no_reject_patterns("자세 8.5점입니다", context="coach")

    def test_fraction_score_rejected(self) -> None:
        with pytest.raises(ValueError, match="점수"):
            _enforce_no_reject_patterns("9 / 10 수준", context="coach")


# ─────────────────── 좌표 패턴 (allow_coords 분기) ───────────────────


class TestCoordinateRejectPatterns:
    def test_x_equals_pattern_rejected_when_disallowed(self) -> None:
        with pytest.raises(ValueError, match="좌표"):
            _enforce_no_reject_patterns(
                "어깨 위치는 x=0.3, y=0.5", context="finding", allow_coords=False
            )

    def test_korean_coord_word_rejected_when_disallowed(self) -> None:
        with pytest.raises(ValueError, match="좌표"):
            _enforce_no_reject_patterns(
                "좌표 기준 측면 촬영 권장", context="finding"
            )

    def test_x_equals_pattern_allowed_when_allow_coords_true(self) -> None:
        # 영역 D 박제 — keypoint refinement 는 좌표 출력이 schema 정의상 정상.
        _enforce_no_reject_patterns(
            "x=0.3 y=0.5", context="keypoint", allow_coords=True
        )

    def test_korean_coord_word_allowed_when_allow_coords_true(self) -> None:
        _enforce_no_reject_patterns(
            "좌표 보정 결과", context="keypoint", allow_coords=True
        )


# ─────────────────── 사람 판단 어휘 (graceful X — ValueError) ───────────────────


class TestJudgmentRejectPatterns:
    def test_korean_judgment_word_rejected(self) -> None:
        with pytest.raises(ValueError, match="판단"):
            _enforce_no_reject_patterns("정은지는 잘했다", context="coach")

    def test_perfect_word_rejected(self) -> None:
        with pytest.raises(ValueError, match="판단"):
            _enforce_no_reject_patterns("자세가 완벽하다", context="coach")

    def test_judgment_allowed_with_allow_coords_still_rejected(self) -> None:
        # 영역 D 좌표 우회는 판단 어휘를 풀어주지 않는다 — 분리 박제.
        with pytest.raises(ValueError, match="판단"):
            _enforce_no_reject_patterns(
                "정은지는 훌륭하다 x=0.3",
                context="keypoint",
                allow_coords=True,
            )


# ─────────────────── 정상 통과 ───────────────────


class TestCleanText:
    def test_clean_korean_text_passes(self) -> None:
        # 좌표/점수/판단 어휘 0 — 통과해야 한다.
        _enforce_no_reject_patterns(
            "왼쪽 어깨가 위쪽으로 굽어 있어 라인이 끊어집니다.",
            context="coach",
        )

    def test_empty_text_passes_noop(self) -> None:
        # 빈 응답은 별도 path 에서 처리 — guardrail noop.
        _enforce_no_reject_patterns("", context="coach")
