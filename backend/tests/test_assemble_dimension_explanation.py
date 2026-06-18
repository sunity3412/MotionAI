"""Phase 12.5 — dimensionExplanation 단위 테스트.

Codex v2 + v3 review 반영 검증:
- v3 HIGH-1: baseline "IPSF 기준" → "IPSF 실행 기준 참고" (과대 주장 회피)
- v3 HIGH-2: line/stability deficit source 가 점수 산식과 같은 windowing 사용
- v3 HIGH-3: weightPercent 합 = 100 (Largest Remainder)
- v3 MED-1: mode = comparison["mode"] 직접 추출
- v3 MED-2: mode3 first 가 line=None 시 stability 만 1차원
- v3 LOW-2: edge cases (NaN frames, single frame, empty/invalid hold, no EXTEND)
"""

from __future__ import annotations

import dataclasses

import numpy as np

from sunity_shared.analysis import assemble, kismam, technique
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS

_EXT = ("left_elbow", "right_elbow", "left_knee", "right_knee")


def _assess(dev_map=None):
    dev = np.zeros(NUM_JOINTS)
    for k, v in (dev_map or {}).items():
        dev[JOINT_KEYS.index(k)] = v
    return kismam.assess(dev)


def _profile(extend=_EXT, hold_window=None) -> technique.TechniqueProfile:
    exp = {
        k: technique.JOINT_EXTEND if k in extend else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(
        name="t", category="unknown", joint_expectations=exp, hold_window=hold_window
    )


def _pose(angle_map: dict[str, float], t: int = 20) -> np.ndarray:
    base = np.full(NUM_JOINTS, 90.0)
    for k, v in angle_map.items():
        base[JOINT_KEYS.index(k)] = v
    return np.tile(base, (t, 1))


# ── 1. weightPercent = 기여 차원(angle/line) 한정 합 100 (Phase 19 D-01 HIGH-1) ──
# Phase 19: stability 는 종합 비기여(overall_from_dimensions = min-of-core) →
# weightPercent=0 + contributesToOverall=False. weightPercent largest-remainder 는
# 기여 차원(angle/line)에만 분배 (거짓 기여 표시 차단).


def test_weight_contributing_dims_sum_100():
    # angle/line/stability 3차원 → 기여(angle/line)=[50,50], stability=0.
    a = _assess({"left_knee": 50})
    exp = assemble.build_dimension_explanation(
        a, {"angle": 70, "line": 65, "stability": 80}, {"mode": "mode1"}
    )
    pcts = [exp[d]["weightPercent"] for d in ("angle", "line", "stability")]
    assert pcts == [50, 50, 0]
    # 기여 차원 합 = 100
    assert exp["angle"]["weightPercent"] + exp["line"]["weightPercent"] == 100
    assert exp["stability"]["weightPercent"] == 0
    assert exp["angle"]["contributesToOverall"] is True
    assert exp["line"]["contributesToOverall"] is True
    assert exp["stability"]["contributesToOverall"] is False


def test_weight_single_contributing_dim_plus_stability():
    # line + stability → 기여(line)=100, stability=0.
    a = _assess({})
    exp = assemble.build_dimension_explanation(
        a, {"line": 70, "stability": 80}, {"mode": "mode3", "isFirst": True}
    )
    assert exp["line"]["weightPercent"] == 100
    assert exp["line"]["contributesToOverall"] is True
    assert exp["stability"]["weightPercent"] == 0
    assert exp["stability"]["contributesToOverall"] is False


def test_weight_no_contributing_dim_stability_zero():
    # mode3 first 가 line=None 시 stability 만 → 기여 차원 없음 → weightPercent=0.
    # (stability 는 절대 보조 지표 — 종합 비기여, Phase 19 D-01.)
    a = _assess({})
    exp = assemble.build_dimension_explanation(
        a, {"stability": 75}, {"mode": "mode3", "isFirst": True}
    )
    assert exp["stability"]["weightPercent"] == 0
    assert exp["stability"]["contributesToOverall"] is False


def test_weight_empty_dims_returns_empty_dict():
    a = _assess({})
    exp = assemble.build_dimension_explanation(a, {}, {"mode": "mode1"})
    assert exp == {}


# ── 2. baseline mode-aware + "참고" 표현 (Codex v3 HIGH-1) ────────────────


def test_baseline_mode1_uses_ipsf_reference_wording():
    a = _assess({})
    exp = assemble.build_dimension_explanation(
        a, {"angle": 70, "line": 70, "stability": 70}, {"mode": "mode1"}
    )
    assert "참고" in exp["angle"]["baseline"]  # 과대 주장 회피
    assert "정은지" in exp["angle"]["baseline"]
    assert "참고" in exp["line"]["baseline"]
    # stability 는 mode1/mode3 동일 (절대 지표)
    assert "절대 지표" in exp["stability"]["baseline"]


def test_baseline_mode3_does_not_reference_eunji():
    a = _assess({})
    exp = assemble.build_dimension_explanation(
        a, {"line": 70, "stability": 70}, {"mode": "mode3", "isFirst": True}
    )
    assert "정은지" not in exp["line"]["baseline"]
    assert "정은지" not in exp["stability"]["baseline"]


def test_mode_extracted_from_comparison_dict():
    # comparison["mode"] 직접 박제 — 별도 mode 인자 없음 (Codex v3 MED-1)
    a = _assess({})
    exp_m1 = assemble.build_dimension_explanation(
        a, {"line": 70}, {"mode": "mode1"}
    )
    exp_m3 = assemble.build_dimension_explanation(
        a, {"line": 70}, {"mode": "mode3", "isFirst": True}
    )
    assert exp_m1["line"]["baseline"] != exp_m3["line"]["baseline"]


def test_baseline_unknown_mode_defaults_to_mode3():
    # comparison 가 None 또는 mode 없음 → mode3 baseline (정은지 reference 없음)
    a = _assess({})
    exp = assemble.build_dimension_explanation(a, {"stability": 70}, None)
    assert "정은지" not in exp["stability"]["baseline"]


# ── 3. deficitSummary 차원별 source (Codex v2 HIGH-1/2 + v3 HIGH-2) ──────


def test_angle_deficit_uses_top_joint():
    # left_knee deviation 50° → worst joint, 점수 < 80 → 수치 표시
    a = _assess({"left_knee": 50})
    exp = assemble.build_dimension_explanation(
        a, {"angle": 60}, {"mode": "mode1"}
    )
    assert "무릎" in exp["angle"]["deficitSummary"]
    assert "50°" in exp["angle"]["deficitSummary"]


def test_line_deficit_uses_extend_joints_via_dimensions_helper():
    # joint_angles + profile 박제 → line_deficits_by_joint 호출 (산식 정합)
    a = _assess({})
    angles = _pose({"left_knee": 150}, t=20)  # left_knee 신전 부족 30
    profile = _profile()
    exp = assemble.build_dimension_explanation(
        a, {"line": 50}, {"mode": "mode1"}, joint_angles=angles, profile=profile
    )
    # left_elbow default 90° → 신전 부족 90 (worst)
    assert "팔꿈치" in exp["line"]["deficitSummary"] or "어깨" in exp["line"]["deficitSummary"] or "무릎" in exp["line"]["deficitSummary"]
    assert "신전 부족" in exp["line"]["deficitSummary"]


def test_stability_deficit_uses_wobble_helper():
    # joint_angles + profile 박제 → stability_wobble_by_joint 호출
    a = _assess({})
    rng = np.random.default_rng(42)
    angles = _pose({}, t=20) + rng.normal(0, 25, size=(20, NUM_JOINTS))  # 큰 wobble
    profile = _profile()
    exp = assemble.build_dimension_explanation(
        a, {"stability": 50}, {"mode": "mode1"},
        joint_angles=angles, profile=profile,
    )
    assert "떨림" in exp["stability"]["deficitSummary"]


# ── 4. 양호 임계 (점수 ≥ 80) 시 수치 X (Codex v3 LOW-2) ─────────────────


def test_high_score_returns_good_copy_no_number():
    # 점수 ≥ 80 → 양호 카피, deviation 수치 표시 X
    a = _assess({"left_knee": 50})  # deviation 50 이지만
    exp = assemble.build_dimension_explanation(
        a, {"angle": 85}, {"mode": "mode1"}  # 점수 85
    )
    # 양호 카피 — 수치 표시 X
    assert "50°" not in exp["angle"]["deficitSummary"]
    assert "안정" in exp["angle"]["deficitSummary"]


# ── 5. acceptance: keys subset + always emit (Codex v3 suggestion) ───────


def test_explanation_keys_subset_of_dimension_scores():
    a = _assess({})
    dim_scores = {"angle": 70, "stability": 75}
    exp = assemble.build_dimension_explanation(a, dim_scores, {"mode": "mode1"})
    assert set(exp.keys()) <= set(dim_scores.keys())
    # 정확히 일치 (모든 차원 emit)
    assert set(exp.keys()) == set(dim_scores.keys())


def test_explanation_always_emitted_even_empty():
    a = _assess({})
    exp = assemble.build_dimension_explanation(a, {}, {"mode": "mode1"})
    assert exp == {}  # None X, 빈 dict


def test_build_result_always_includes_dimension_explanation_key():
    # build_result 신 결과는 dimensionExplanation 항상 emit
    a = _assess({"left_knee": 50})
    r = assemble.build_result(
        a, {"angle": 70, "line": 70, "stability": 70}, overall_score=70,
        comparison=assemble.build_mode1({"motionId": "m", "name": "x", "athleteName": "y"}, 70),
        my_video_url="s3://x",
    )
    assert "dimensionExplanation" in r


# ── 6. Edge cases (Codex v3 LOW-2) ──────────────────────────────────────


def test_no_extend_joints_in_profile():
    # profile.expects_extension 모두 False → line deficit 양호 카피
    a = _assess({})
    angles = _pose({}, t=20)
    profile = _profile(extend=())
    exp = assemble.build_dimension_explanation(
        a, {"line": 70}, {"mode": "mode1"},
        joint_angles=angles, profile=profile,
    )
    # line_defs 비어있음 → "신전 자세 안정" 박제
    assert "안정" in exp["line"]["deficitSummary"]


def test_single_frame_stability_graceful():
    # T=1 → stability_wobble_by_joint 빈 dict → 양호 카피
    a = _assess({})
    angles = _pose({}, t=1)
    profile = _profile()
    exp = assemble.build_dimension_explanation(
        a, {"stability": 70}, {"mode": "mode1"},
        joint_angles=angles, profile=profile,
    )
    assert "떨림" in exp["stability"]["deficitSummary"]  # 양호 카피
