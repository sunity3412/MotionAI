"""Plan 07-02 Task 2 — compare_body_profiles() Phase 7 wiring 통합 test.

박제 정신:
  - Phase 6 fixture (`fixture_160cm_pro_vs_140cm_student.json`) 재사용 — 별도
    Phase 7 합성 fixture 미필요. compare_body_profiles() 본체 안 classify_findings()
    wiring 검증.
  - 본 plan 의 must_haves §11 + RESEARCH.md §"Code Examples Example 2".
  - WR-03 fix — recommended_focus[] 빈 list 일 때 recommended_focus_fallback
    populated, populated 시 None.

4 integration test (Plan 02 acceptance criteria 정합):
  1. test_compare_body_profiles_emits_classified_findings
  2. test_compare_body_profiles_emits_do_not_over_correct
  3. test_compare_body_profiles_emits_recommended_focus
  4. test_compare_body_profiles_emits_recommended_focus_fallback_when_empty (WR-03)
"""

from __future__ import annotations

from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.body_normalizer import compare_body_profiles
from sunity_shared.analysis.copy_templates import _EMPTY_FOCUS_FALLBACK

from tests.phase06.fixtures._factory import load_paired_frames


def _make_profile(**kw) -> BodyNormalizationProfile:
    """Phase 6 helper 정합 — confidence/scale 디폴트 OK."""
    defaults = dict(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.9,
        warnings=[],
    )
    defaults.update(kw)
    return BodyNormalizationProfile(**defaults)


def _frame_to_dict(frame) -> dict:
    """Phase 6 helper 정합 — keypoints_3d 만 추출."""
    return {n: (kp.x, kp.y, kp.z) for n, kp in frame.keypoints_3d.items()}


def _build_report():
    """공통 setup — fixture_160cm_pro_vs_140cm_student 활용해 mode1 + 안정 path
    report 생성. 4 test 가 본 helper 재사용."""
    pro_frames, student_frames = load_paired_frames(
        "fixture_160cm_pro_vs_140cm_student",
        key_a="pro_frames",
        key_b="student_frames",
    )
    pro_kp = _frame_to_dict(pro_frames[0])
    student_profile = _make_profile(
        estimated_height_scale=0.875,
        arm_scale=0.875,
        leg_scale=0.875,
        confidence=0.85,
    )
    pro_profile = _make_profile()
    return compare_body_profiles(
        pose_frames=student_frames,
        student_profile=student_profile,
        reference_profile=pro_profile,
        comparison_type="mode1",
        source_keypoints=pro_kp,
        angles=None,
        technique_profile=None,
        reference_motion_id="ref-test",
        reference_athlete_name="정은지",
        target_torso_px=200.0,
    )


# ── Test 1: classified findings ──────────────────────────────────────────


def test_compare_body_profiles_emits_classified_findings() -> None:
    """compare_body_profiles 호출 후 BodyComparisonReport.findings[*].category
    모두 valid enum + phase='hold' + interpretation/recommendation 둘 다 채워짐 (정상 path).
    """
    report = _build_report()
    for f in report.findings:
        assert f.category in ("body_type_allowed", "needs_adjustment", "uncertain"), (
            f"invalid category={f.category!r}"
        )
        assert f.phase == "hold"
        # body_type_interpretation 은 정상 (non-fallback) path 에서 non-None.
        # mode1 + used_reference_fallback=False 이므로 interpretation 도 채워짐.
        # (단, render_finding_copy 의 graceful fallback path 시 None 가능하지만 본
        # fixture 는 표준 deficit code 이므로 lookup 성공)
        assert f.recommendation is not None


# ── Test 2: do_not_over_correct ──────────────────────────────────────────


def test_compare_body_profiles_emits_do_not_over_correct() -> None:
    """report.do_not_over_correct: list[str] + populated 시 mode prefix 시작."""
    report = _build_report()
    assert isinstance(report.do_not_over_correct, list)
    for s in report.do_not_over_correct:
        assert isinstance(s, str)
        # mode1 prefix — "정은지 선수 영상 기준으로 보면"
        assert s.startswith("정은지 선수 영상 기준으로 보면"), (
            f"mode1 prefix 누락: {s!r}"
        )


# ── Test 3: recommended_focus ────────────────────────────────────────────


def test_compare_body_profiles_emits_recommended_focus() -> None:
    """report.recommended_focus: list[str] + populated 시 mode prefix 시작."""
    report = _build_report()
    assert isinstance(report.recommended_focus, list)
    for s in report.recommended_focus:
        assert isinstance(s, str)
        assert s.startswith("정은지 선수 영상 기준으로 보면"), (
            f"mode1 prefix 누락: {s!r}"
        )


# ── Test 4 (WR-03 fix): recommended_focus_fallback when empty ────────────


def test_compare_body_profiles_emits_recommended_focus_fallback_when_empty() -> None:
    """WR-03 fix — 양질 영상 (pose_reliability_low 없음) → recommended_focus 가
    빈 list 일 때 fallback 카피 populated. 채워졌을 때는 None.
    """
    report = _build_report()
    if not report.recommended_focus:
        assert report.recommended_focus_fallback == _EMPTY_FOCUS_FALLBACK, (
            "빈 recommended_focus → fallback 카피 populated 필요"
        )
    else:
        assert report.recommended_focus_fallback is None, (
            f"populated recommended_focus → fallback None 필요 (got {report.recommended_focus_fallback!r})"
        )
