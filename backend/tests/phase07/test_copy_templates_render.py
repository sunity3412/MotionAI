"""Plan 07-01 Task 2 — render_finding_copy 시그너처 + 33 카피 매핑 coverage + 3
mode prefix prepend + fallback graceful + interpretation mode-invariant +
**CR-01 used_reference_fallback path** (Test 7) 박제.

per Plan 07-01 Task 2 + .planning/phases/07-difference-classification/07-PATTERNS.md
§"test_copy_templates_render.py".

iteration 2 cross-AI review fix:
  - CR-01: render_finding_copy(used_reference_fallback=True) → unprefixed 단일 카피
    (None, "이 동작은 기준 영상이 없어, AI 가 IPSF 절대 기준만으로 분석했어요.
    강사와 함께 확인 권유드려요.") deficit 무관 동일 반환.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.copy_templates import (
    _COPY_TEMPLATES,
    _MODE_PREFIX,
    render_finding_copy,
)


# ── Test 1: 33 카피 매핑 coverage ─────────────────────────────────────


@pytest.mark.parametrize("key", list(_COPY_TEMPLATES.keys()))
def test_renders_all_canned_keys(key: tuple[str, str, str]) -> None:
    """33 카피 key 전체 (CR-02 fix: 21 + 12 global) iterate 시 render_finding_copy
    호출이 KeyError 없이 정상 통과."""
    deficit_code, category, joint_group = key
    interp, recom = render_finding_copy(
        deficit_code, category, joint_group, comparison_type="mode1"
    )
    assert interp is not None and isinstance(interp, str) and interp.strip()
    assert isinstance(recom, str) and recom.strip()


# ── Test 2: mode1 prefix ─────────────────────────────────────────────


def test_render_finding_copy_mode1_prefix() -> None:
    interp, recom = render_finding_copy(
        "knee_toe_alignment", "needs_adjustment", "leg", "mode1"
    )
    assert recom.startswith(_MODE_PREFIX["mode1"]), (
        f"mode1 prefix 누락 — got: {recom!r}"
    )


# ── Test 3: mode3_first prefix (normal path, used_reference_fallback=False) ──


def test_render_finding_copy_mode3_first_prefix() -> None:
    interp, recom = render_finding_copy(
        "knee_toe_alignment", "needs_adjustment", "leg", "mode3_first"
    )
    assert recom.startswith(_MODE_PREFIX["mode3_first"]), (
        f"mode3_first prefix 누락 — got: {recom!r}"
    )


# ── Test 4: mode3_progress prefix ────────────────────────────────────


def test_render_finding_copy_mode3_progress_prefix() -> None:
    interp, recom = render_finding_copy(
        "knee_toe_alignment", "needs_adjustment", "leg", "mode3_progress"
    )
    assert recom.startswith(_MODE_PREFIX["mode3_progress"]), (
        f"mode3_progress prefix 누락 — got: {recom!r}"
    )


# ── Test 5: prefix is on recommendation only (interpretation mode-invariant) ──


def test_interpretation_is_mode_invariant() -> None:
    """D-07-D3: 같은 (deficit_code, category, joint_group) 입력 + mode 변경 시
    interpretation 동일, recommendation prefix 만 다름."""
    args = ("knee_toe_alignment", "needs_adjustment", "leg")
    interp1, recom1 = render_finding_copy(*args, "mode1")
    interp3f, recom3f = render_finding_copy(*args, "mode3_first")
    interp3p, recom3p = render_finding_copy(*args, "mode3_progress")
    assert interp1 == interp3f == interp3p
    assert recom1 != recom3f
    assert recom3f != recom3p


# ── Test 6: graceful fallback for missing key ─────────────────────────


def test_render_finding_copy_fallback_on_missing_key() -> None:
    """키 미발견 시 graceful fallback tuple 반환 (Phase 11 LLM 풍부화 전 안전망)."""
    interp, recom = render_finding_copy(
        "nonexistent_deficit", "uncertain", "global", "mode1"
    )
    assert interp == "이 부분은 AI 분석 결과예요."
    # mode prefix 가 fallback recommendation 에도 prepend 됨 (정상 path)
    assert "강사와 함께 영상을 한 번 더 확인해 보세요." in recom


# ── Test 7: CR-01 fix — used_reference_fallback=True path ────────────


def test_render_with_used_reference_fallback_returns_unprefixed_single_copy() -> None:
    """CR-01 fix — used_reference_fallback=True 시 deficit 무관 단일 unprefixed
    카피 반환. interpretation=None, recommendation=fixture #6 exact match.
    mode prefix 결합 X."""
    interp, recom = render_finding_copy(
        deficit_code="knee_toe_alignment",
        category="uncertain",
        joint_group="leg",
        comparison_type="mode3_first",
        used_reference_fallback=True,
    )
    assert interp is None, f"used_reference_fallback path 의 interpretation = None 이어야 함 (got: {interp!r})"
    expected = (
        "이 동작은 기준 영상이 없어, AI 가 IPSF 절대 기준만으로 분석했어요. "
        "강사와 함께 확인 권유드려요."
    )
    assert recom == expected, f"CR-01 fix: recommendation exact match 실패 — got: {recom!r}"

    # deficit_code 무관 동일 반환 확인.
    for deficit in ("clean_lines", "extension", "posture", "body_placement", "pose_reliability_low"):
        interp2, recom2 = render_finding_copy(
            deficit_code=deficit,
            category="needs_adjustment",
            joint_group="global",
            comparison_type="mode3_first",
            used_reference_fallback=True,
        )
        assert interp2 is None
        assert recom2 == expected, (
            f"deficit={deficit!r} 입력 변경에도 동일 단일 카피여야 함 — got: {recom2!r}"
        )

    # mode prefix 결합되지 않음 확인.
    for prefix in (
        "정은지 선수 영상 기준으로 보면",
        "세계 심사 기준 (IPSF) 으로 보면",
        "이전 영상 대비",
    ):
        assert not recom.startswith(prefix), (
            f"mode prefix {prefix!r} 가 fallback path 에 결합됨 — got: {recom!r}"
        )


# ── Test 8: skeleton.JOINT_LABEL_KO import 박제 확인 ──────────────────


def test_imports_joint_label_ko_from_skeleton() -> None:
    """copy_templates.py 가 from .skeleton import JOINT_LABEL_KO 박제 보유.
    Phase 11 LLM 풍부화 layer 가 부위 한국어 라벨 재사용."""
    from sunity_shared.analysis import copy_templates as ct

    # JOINT_LABEL_KO 가 모듈 namespace 에 임포트되어 있어야 함.
    assert hasattr(ct, "JOINT_LABEL_KO"), (
        "copy_templates 모듈에 JOINT_LABEL_KO 가 import 되지 않음"
    )
    assert isinstance(ct.JOINT_LABEL_KO, dict)
    assert len(ct.JOINT_LABEL_KO) > 0
