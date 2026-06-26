"""Plan 5-01 Task 3 (W4 fix 신설) — production classify_motion_name 단위 테스트.

B2 fix 검증 — spike 가 production 을 import (역방향 금지).
본 테스트는 production 함수 직접 호출 (spike 경로 미사용).

박제 정신:
  · D-01: 5영상 scope (REGISTERED_MOTIONS).
  · D-08: 정규화 결과는 객관 enum (사람 점수 X).
  · [[studio-term-3branch-system]] 분기 1 (학원 통용 한국어) 매핑 검증.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.gemini_motion_classifier import (
    REGISTERED_MOTIONS,
    classify_motion_name,
)


# ─────────────────── REGISTERED_MOTIONS (D-01) ───────────────────


class TestRegisteredMotionsConstant:
    def test_10_motions_exactly(self) -> None:
        # P1 step 4 (2026-06-27): 5→10 scope 확장 (객관 무릎신전 5동작 등록).
        assert len(REGISTERED_MOTIONS) == 10

    def test_motion_ids_match_p1_scope(self) -> None:
        assert REGISTERED_MOTIONS == frozenset(
            {
                # D-01 원 5영상.
                "ref-climb",
                "ref-foxtop",
                "ref-foxtop-split",
                "ref-invert",
                "ref-sideway-spin",
                # P1 step 4 객관 무릎신전 5동작.
                "ref-kip-up",
                "ref-power-spin",
                "ref-peter-pan",
                "ref-elbow-twist-sister",
                "ref-pdshape",
            }
        )


# ─────────────────── 정확 매치 (canonical ID 직접 반환) ───────────────────


class TestExactMatch:
    @pytest.mark.parametrize(
        "motion_id",
        [
            "ref-climb",
            "ref-foxtop",
            "ref-foxtop-split",
            "ref-invert",
            "ref-sideway-spin",
        ],
    )
    def test_canonical_id_recognized(self, motion_id: str) -> None:
        canonical, scope_status = classify_motion_name(motion_id)
        assert canonical == motion_id
        assert scope_status == "recognized"

    def test_case_insensitive_canonical(self) -> None:
        canonical, scope_status = classify_motion_name("REF-INVERT")
        assert canonical == "ref-invert"
        assert scope_status == "recognized"


# ─────────────────── 한국어 alias 매핑 (B2 fix Test 12) ───────────────────


class TestKoreanAlias:
    """학원 통용 한국어 → canonical (분기 1)."""

    def test_invert_korean(self) -> None:
        canonical, scope_status = classify_motion_name("인버트")
        assert canonical == "ref-invert"
        assert scope_status == "recognized"

    def test_foxtop_korean(self) -> None:
        canonical, scope_status = classify_motion_name("폭스탑")
        assert canonical == "ref-foxtop"
        assert scope_status == "recognized"

    def test_foxtop_split_korean(self) -> None:
        canonical, scope_status = classify_motion_name("폭스탑 스플릿")
        assert canonical == "ref-foxtop-split"
        assert scope_status == "recognized"

    def test_sideway_spin_korean(self) -> None:
        canonical, scope_status = classify_motion_name("사이드웨이 스핀")
        assert canonical == "ref-sideway-spin"
        assert scope_status == "recognized"

    def test_climb_korean(self) -> None:
        canonical, scope_status = classify_motion_name("클라임")
        assert canonical == "ref-climb"
        assert scope_status == "recognized"


# ─────────────────── 영어 alias 매핑 ───────────────────


class TestEnglishAlias:
    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("Inverted Butterfly", "ref-invert"),
            ("Inverted Split", "ref-foxtop-split"),
            ("Fox Top", "ref-foxtop"),
            ("Sideway Spin", "ref-sideway-spin"),
            ("Climb", "ref-climb"),
        ],
    )
    def test_english_alias_recognized(self, alias: str, expected: str) -> None:
        canonical, scope_status = classify_motion_name(alias)
        assert canonical == expected
        assert scope_status == "recognized"


# ─────────────────── substring 매치 (긴 매치 우선) ───────────────────


class TestSubstringMatch:
    def test_ipsf_code_substring_match(self) -> None:
        # "IPSF §4.2 Inverted Split (code XYZ)" — substring "inverted split" 매치.
        canonical, scope_status = classify_motion_name(
            "IPSF §4.2 Inverted Split (code XYZ)"
        )
        assert canonical == "ref-foxtop-split"
        assert scope_status == "recognized"

    def test_longer_match_wins_over_shorter(self) -> None:
        # "inverted split" 이 "invert" 보다 우선 (긴 매치).
        canonical, _ = classify_motion_name("Performed inverted split here")
        assert canonical == "ref-foxtop-split"

    def test_korean_multi_word_substring(self) -> None:
        # "기본 사이드웨이 스핀 시연" — substring "사이드웨이 스핀" 매치.
        canonical, scope_status = classify_motion_name("기본 사이드웨이 스핀 시연")
        assert canonical == "ref-sideway-spin"
        assert scope_status == "recognized"


# ─────────────────── unregistered (Test 13 spec) ───────────────────


class TestUnregistered:
    def test_unknown_move_returns_unregistered_tuple(self) -> None:
        # plan Task 3 Test 13: classify_motion_name("unknown move") →
        # (raw_name, "unregistered"). adapter 는 scope_status (position 1) == "unregistered"
        # 로 D-09 case 3 분기.
        canonical, scope_status = classify_motion_name("unknown move")
        assert scope_status == "unregistered"
        # canonical 위치 = raw_name 보존 (Firestore 자동 수집 학원 용어 그대로).
        assert canonical == "unknown move"

    def test_empty_string_unregistered(self) -> None:
        canonical, scope_status = classify_motion_name("")
        assert scope_status == "unregistered"

    def test_whitespace_only_unregistered(self) -> None:
        canonical, scope_status = classify_motion_name("   ")
        assert scope_status == "unregistered"

    def test_aerial_yogi_unregistered(self) -> None:
        # 5영상 scope 외 — Aerial Yogi 류.
        canonical, scope_status = classify_motion_name("Aerial Yogi")
        assert scope_status == "unregistered"
        assert canonical == "Aerial Yogi"


# ─────────────────── 정규화 robustness ───────────────────


class TestNormalization:
    def test_leading_trailing_whitespace_stripped(self) -> None:
        canonical, scope_status = classify_motion_name("  인버트  ")
        assert canonical == "ref-invert"
        assert scope_status == "recognized"

    def test_mixed_case_alias(self) -> None:
        canonical, scope_status = classify_motion_name("INVERTED SPLIT")
        assert canonical == "ref-foxtop-split"
        assert scope_status == "recognized"
