"""Phase 9 Wave 1 T1 — force_pattern_copy.py render test.

18 canned (sourceSignal × modeContext) lookup PASS + 3 mode prefix const 일치 +
jointHint 부위 어휘 매핑 + fallback body 단일 본문 매칭 + mode prefix consistency
invariant + body length floor.

per Plan 09-02 Task T1 / D-09-D2 / Assumption A3 / Open Q 3.
"""

from __future__ import annotations

import itertools

import pytest

from sunity_shared.analysis.force_pattern import (
    _FORCE_SOURCE_SIGNALS,
    _MODE_CONTEXTS,
)
from sunity_shared.analysis.force_pattern_copy import (
    _FALLBACK_BODY,
    _FORCE_PATTERN_COPY,
    _JOINT_HINT_BY_SIGNAL,
    _MODE_PREFIX,
    fallback_body,
    force_pattern_canned_text,
    joint_hint_for,
)


_EIGHTEEN_KEYS = tuple(
    itertools.product(sorted(_FORCE_SOURCE_SIGNALS), sorted(_MODE_CONTEXTS))
)


def test_eighteen_canned_entries_present() -> None:
    """18 entry (6 signal × 3 mode) Cartesian completeness."""
    assert len(_FORCE_PATTERN_COPY) == 18
    assert set(_FORCE_PATTERN_COPY.keys()) == set(_EIGHTEEN_KEYS)


def test_mode_prefix_const_exact_strings() -> None:
    """3 mode prefix verbatim — trailing comma + space 포함."""
    assert _MODE_PREFIX["mode1"] == "정은지 선수 기준 패턴과 비교했을 때, "
    assert _MODE_PREFIX["mode3_first"] == "이번 첫 분석에서, "
    assert _MODE_PREFIX["mode3_progress"] == "지난 영상 대비, "


def test_mode_prefix_consistency_invariant() -> None:
    """모든 canned body 가 해당 mode prefix 로 시작 — D-09-D2 톤 invariant."""
    for (sig, mc), body in _FORCE_PATTERN_COPY.items():
        prefix = _MODE_PREFIX[mc]
        assert body.startswith(prefix), (
            f"({sig}, {mc}) body 가 mode prefix 로 시작하지 않음: "
            f"prefix={prefix!r}, body={body[:40]!r}"
        )


@pytest.mark.parametrize("sig,mc", _EIGHTEEN_KEYS)
def test_force_pattern_canned_text_lookup(sig: str, mc: str) -> None:
    """helper 가 dict lookup 과 동일 string 반환."""
    got = force_pattern_canned_text(sig, mc)
    assert got == _FORCE_PATTERN_COPY[(sig, mc)]
    assert isinstance(got, str) and got


def test_joint_hint_mapping() -> None:
    """6 hint (4 string + 2 None) — Assumption A3 + 2026-06-10 belle 쉬운 어휘 정합.
    실증 테스트 시점 belle + 강사 + 수강생 함께 어휘 검수 (deferred-items.md)."""
    assert joint_hint_for("axis_tilt") == "몸 중심"
    assert joint_hint_for("pelvis_drop") == "엉덩이 관절"
    assert joint_hint_for("late_contact") == "허벅지 안쪽"
    assert joint_hint_for("abnormal_release") == "등 근육"
    assert joint_hint_for("high_jerk") is None
    assert joint_hint_for("high_jitter") is None
    # 직접 dict lookup 도 동일 결과.
    assert _JOINT_HINT_BY_SIGNAL == {
        "axis_tilt": "몸 중심",
        "pelvis_drop": "엉덩이 관절",
        "late_contact": "허벅지 안쪽",
        "abnormal_release": "등 근육",
        "high_jerk": None,
        "high_jitter": None,
    }


def test_fallback_body_single_sentence() -> None:
    """fallback body 단일 본문 (D-09-B4 / Open Q 3)."""
    expected = (
        "이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다. 강사와 함께 "
        "확인하는 것을 권장해요."
    )
    assert fallback_body() == expected
    assert _FALLBACK_BODY == expected


def test_body_length_floor() -> None:
    """모든 canned body 길이 ≥ 25 chars — slop floor.

    mode1 prefix(~22 chars) + 본문 ≥ 3 chars 정도가 floor. mode3_first/progress
    는 prefix 가 더 짧지만 본문이 더 길어야 하므로 동일 floor 25 chars 적용.
    """
    for (sig, mc), body in _FORCE_PATTERN_COPY.items():
        assert len(body) >= 25, (
            f"({sig}, {mc}) body 길이 미달 ({len(body)} < 25): {body!r}"
        )
