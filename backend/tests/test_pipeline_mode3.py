"""mode3 자기 성장 분기 (_mode3_comparison) — 순수 로직. NLF·S3·Firestore 불필요.

첫 분석=절대 차원(라인/안정성) + delta 없음, 두 번째+=절대 + angle(이전영상 대비) +
발전 델타. 같은 영상이면 angle 일관성이 높고, 절대 차원은 입력이 같아 동일 점수가 나온다.
line 은 기술 조건부라 TechniqueProfile 을 함께 넘긴다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

import app  # noqa: E402
from sunity_shared.analysis import assemble, technique  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS  # noqa: E402


def _video(seed: int = 0, t: int = 40) -> np.ndarray:
    """그럴듯한 자세 시퀀스 (T, J). seed 로 다른 영상 흉내."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(120, 175, size=NUM_JOINTS)
    return base + rng.normal(0, 3, size=(t, NUM_JOINTS))


def _profile() -> technique.TechniqueProfile:
    """팔꿈치/무릎 EXTEND 인 결정적 프로파일 (line 항상 산출되게)."""
    exp = {
        k: technique.JOINT_EXTEND
        if k.endswith("elbow") or k.endswith("knee")
        else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(name="t", category="unknown", joint_expectations=exp)


def _as_prev(angles: np.ndarray, analysis_id: str, dim_scores: dict) -> dict:
    """get_previous_analysis 반환 모양 (doc dict)."""
    return {
        "analysisId": analysis_id,
        "angles": np.asarray(angles, dtype=float).reshape(-1).tolist(),
        "anglesJointKeys": list(JOINT_KEYS),
        "anglesFrames": int(angles.shape[0]),
        "result": {"dimensionScores": dim_scores},
    }


def test_first_analysis_absolute_only_no_delta():
    assessments, dims, overall, comparison = app._mode3_comparison(
        _video(1), None, _profile()
    )
    # Phase 19 — _mode3_comparison 은 이제 scoringBasis(실제 채점 source 라벨)를 항상
    # emit 한다 (TRUST-03 가시화). first + reference-free(_profile() motion_id None) →
    # reference_free_absolute. 핵심 계약(mode/isFirst/delta 없음)은 불변.
    assert comparison["mode"] == "mode3" and comparison["isFirst"] is True
    assert "previousAnalysisId" not in comparison and "deltaFromPrevious" not in comparison
    assert comparison["scoringBasis"] == "reference_free_absolute"
    assert set(dims) == {"line", "stability"}
    assert 0 <= overall <= 100
    assert len(assessments) == NUM_JOINTS


def test_second_analysis_has_progress_delta_and_angle():
    cur = _video(2)
    prev_angles = _video(7)
    prev = _as_prev(prev_angles, "prevA", {"line": 60, "stability": 65})
    _, dims, overall, comparison = app._mode3_comparison(cur, prev, _profile())
    # 두 번째+ = angle(이전영상 일관성) 표시 + 절대 차원.
    assert set(dims) == {"angle", "line", "stability"}
    assert comparison["mode"] == "mode3" and comparison["isFirst"] is False
    assert comparison["previousAnalysisId"] == "prevA"
    # 발전 델타는 절대 차원만 (각도 제외 — 척도 안정).
    assert set(comparison["deltaFromPrevious"]) == {"line", "stability"}


def test_same_video_is_consistent():
    # 같은 영상 = 이전과 각도 일관성 매우 높음 + 절대 차원 델타 0.
    v = _video(3)
    profile = _profile()
    prev_abs = app.dimensions.absolute_dimension_scores(v, profile)
    prev = _as_prev(v, "selfprev", prev_abs)
    _, dims, _, comparison = app._mode3_comparison(v, prev, profile)
    assert dims["angle"] >= 95  # 자기 자신과 정렬 → 편차 ~0
    assert comparison["deltaFromPrevious"] == {"line": 0, "stability": 0}


# ── Phase 19 신규 RED 케이스 (단독 실행 시 게이트/필드/helper/hook 부재로 behavior fail) ──
#
# Mode3 scoringBasis enum = 4 값 (reference_motion 은 Mode1 전용). TS Mode3Comparison enum 정렬.
_MODE3_BASIS_REFERENCE_FREE_ABSOLUTE = "reference_free_absolute"
_MODE3_BASIS_RECOGNIZED_ABSOLUTE = "recognized_motion_absolute"
_MODE3_BASIS_PREV_PLUS_ABSOLUTE = "previous_analysis_plus_absolute"
_MODE3_BASIS_PREV_PLUS_REFERENCE_FREE = "previous_analysis_plus_reference_free_absolute"
_MODE3_BASES = (
    _MODE3_BASIS_REFERENCE_FREE_ABSOLUTE,
    _MODE3_BASIS_RECOGNIZED_ABSOLUTE,
    _MODE3_BASIS_PREV_PLUS_ABSOLUTE,
    _MODE3_BASIS_PREV_PLUS_REFERENCE_FREE,
)


def _comparison_scoring_basis(comparison: dict) -> str | None:
    """Mode3 comparison dict 에서 scoringBasis 추출 (직렬화 계약 필드)."""
    return comparison.get("scoringBasis")


def test_display_matches_score_source():
    # TRUST-01: 표시 각도(현재/기준)는 점수 산출에 쓰인 DTW-정렬 median 과 동일 source 여야 한다.
    # 현재 _angles_to_mean_dict 는 whole-clip np.nanmean — 점수가 쓰는 per_joint_deviation(median)
    # 와 불일치 (비대칭 근본원인). Wave 2 가 추가할 path-aligned median helper
    # (_angles_to_dtw_median_dicts) 를 통해 표시값이 산출돼야 통과한다.
    # ref full-clip 에 jitter 프레임을 넣어 "정렬 median ≠ whole-clip nanmean" 이 구분되게 구성.
    helper = getattr(app, "_angles_to_dtw_median_dicts", None)
    assert helper is not None, (
        "_angles_to_dtw_median_dicts helper 부재 — Wave 2 가 표시-점수 정합 source 로 추가 (RED)"
    )
    rng = np.random.default_rng(11)
    base = rng.uniform(120, 175, size=NUM_JOINTS)
    user_seg = base + rng.normal(0, 2, size=(30, NUM_JOINTS))
    # ref: 정렬 구간은 base 근처, clip 양 끝에 큰 jitter 프레임 (whole-clip mean 을 왜곡).
    ref_aligned = base + rng.normal(0, 2, size=(30, NUM_JOINTS))
    jitter = np.full((8, NUM_JOINTS), 30.0)
    a_ref = np.vstack([jitter, ref_aligned, jitter])
    # DTW path 정렬 median 은 jitter 에 강건 → whole-clip nanmean 과 달라야 함.
    aligned_user, aligned_ref = helper(user_seg, a_ref, JOINT_KEYS)
    whole_clip = app._angles_to_mean_dict(a_ref, JOINT_KEYS)
    diffs = [abs(aligned_ref[k] - whole_clip[k]) for k in JOINT_KEYS if k in aligned_ref]
    assert any(d > 1.0 for d in diffs), "정렬 median 이 whole-clip nanmean 과 구분돼야 한다"


def test_mode1_scoring_basis_reference_motion():
    # TRUST-03 + ITER-3 MEDIUM-1 (Mode1 분리) + ITER-4 HIGH-1 (직렬화 단언).
    # MODE_EXPERT(reference 각도 비교) 경로가 build_mode1 으로 직렬화한 Mode1Comparison dict 의
    # scoringBasis == "reference_motion" 을 단언한다 (내부 변수/전역 basis 아님 — result 계약 필드).
    # Mode3 게이트와 별도 — Mode3Comparison/build_mode3 를 통하지 않음.
    # 현재 build_mode1 에 scoringBasis emit 부재라 RED.
    ref = {
        "motionId": "ref-climb",
        "name": "클라임",
        "athleteName": "정은지",
    }
    comparison = assemble.build_mode1(ref, similarity=88)
    assert comparison["scoringBasis"] == "reference_motion"
    assert comparison.get("scoringBasisLabel")  # 라벨 존재 (사용자 표시용)


@pytest.mark.parametrize("scoring_basis", _MODE3_BASES)
def test_unknown_move_gate(scoring_basis):
    # TRUST-03 + BLOCKER-1 + ITER-2 HIGH-2/HIGH-3 + ITER-3 MEDIUM-1/HIGH-2.
    # Mode3 의 4 scoringBasis source 만 검증 (reference_motion 은 Mode1 전용 — 미등장).
    #   (a) first + 미등록 motion → reference_free_absolute (절대트랙 line+stability)
    #   (b) first + recognized(등재) → recognized_motion_absolute (first 는 reference 각도 미사용)
    #   (c) progress + known → previous_analysis_plus_absolute
    #   (d) progress + reference-free → previous_analysis_plus_reference_free_absolute (composite, HIGH-3)
    # 명시 invariant: 어떤 Mode3 comparison 도 scoringBasis=="reference_motion" 을 emit 하지 않는다.
    # fail-closed/raise 금지 — 점수는 주되 근거 명시.
    profile = _profile()
    is_first = scoring_basis in (
        _MODE3_BASIS_REFERENCE_FREE_ABSOLUTE,
        _MODE3_BASIS_RECOGNIZED_ABSOLUTE,
    )
    is_reference_free = scoring_basis in (
        _MODE3_BASIS_REFERENCE_FREE_ABSOLUTE,
        _MODE3_BASIS_PREV_PLUS_REFERENCE_FREE,
    )
    # 미등록(reference-free) vs 등재(recognized) 를 motion_id 로 구분. 미등록 → 안전 기본
    # (_SAFE_DEFAULT_BRANCH, copyBranch="branch2_eunji_reference"), 등재 → 실 branch2.
    # ref-foxtop = copyBranch branch2_eunji_reference (안전 기본과 동일값) 이지만
    # angleSource=eunji_measured_yaml + officialName 존재 → is_reference_free=False.
    # 이로써 "copyBranch 동일인데 reference-free 판정 다름" 을 검증한다 (copyBranch 단독 분기 금지).
    motion_id = None if is_reference_free else "ref-foxtop"
    branch = assemble.lookup_motion_branch(motion_id)
    # is_reference_free_motion 판정 helper (Wave 1 신설) — copyBranch 단독 분기 금지.
    is_ref_free_fn = getattr(assemble, "is_reference_free_motion", None)
    assert is_ref_free_fn is not None, (
        "assemble.is_reference_free_motion 부재 — Wave 1 가 추가 (copyBranch 단독 분기 차단, RED)"
    )
    assert is_ref_free_fn(branch) is is_reference_free

    # 게이트 wiring — recognize 직후 lookup 한 branch_info 를 _mode3_comparison 에 흘려야
    # first reference-free vs first recognized 를 구분해 정확한 scoringBasis 를 emit 한다
    # (동일 angles/profile 만으로는 구분 불가 — branch_info 가 motion 인식 정보의 single source).
    if is_first:
        _, _, _, comparison = app._mode3_comparison(
            _video(1), None, profile, branch_info=branch
        )
    else:
        prev = _as_prev(_video(7), "prevA", {"line": 60, "stability": 65})
        _, _, _, comparison = app._mode3_comparison(
            _video(2), prev, profile, branch_info=branch
        )

    # NOTE: scoringBasis 는 motion 인식(profile.motion_id / branch) 에 의존하므로 Wave 1 의
    # 게이트 wiring 이 _mode3_comparison 시그너처에 branch/recognized 정보를 흘려야 emit 된다.
    assert _comparison_scoring_basis(comparison) == scoring_basis
    # Mode3 invariant — reference_motion 은 Mode1 전용, Mode3 에서 절대 emit 0.
    assert _comparison_scoring_basis(comparison) != "reference_motion"

    # 실 branch2(정은지)와 reference-free 가 copyBranch 동일값이어도 scoringBasis 는 달라야 함.
    real_branch2 = assemble.lookup_motion_branch("ref-foxtop")
    safe_default = assemble.lookup_motion_branch(None)
    assert real_branch2.copyBranch == safe_default.copyBranch == "branch2_eunji_reference"
    assert is_ref_free_fn(real_branch2) is not is_ref_free_fn(safe_default)


def test_build_mode3_backward_compat():
    # ITER-2 MEDIUM-2 + ITER-3 HIGH-2. basis 미전달 → 정확히 {"mode":"mode3","isFirst":True}.
    # scoring_basis 전달 시에만 scoringBasis/scoringBasisLabel 키 등장.
    # build_mode3(scoring_basis="reference_motion") → ValueError (Mode3 4-value enum 위반).
    assert assemble.build_mode3(is_first=True) == {"mode": "mode3", "isFirst": True}

    out = assemble.build_mode3(
        is_first=True, scoring_basis=_MODE3_BASIS_REFERENCE_FREE_ABSOLUTE
    )
    assert out["scoringBasis"] == _MODE3_BASIS_REFERENCE_FREE_ABSOLUTE
    assert out.get("scoringBasisLabel")

    with pytest.raises(ValueError):
        assemble.build_mode3(is_first=True, scoring_basis="reference_motion")


def test_vision_hook_passthrough():
    # TRUST-05 + ITER-2 MEDIUM-3. v1 vision hook(_apply_vision_veto) OFF 시 SAME object
    # identity (out is score_result) + score_result 필드 mutate 0. 현재 _apply_vision_veto 부재 → RED.
    veto = getattr(app, "_apply_vision_veto", None)
    assert veto is not None, "_apply_vision_veto 부재 — Wave 1 v1 pass-through hook 추가 (RED)"
    # WR-01: production passes assemble.build_result dict whose key is
    # 'overallScore' (not 'overall'). The fixture must mirror that contract so
    # v2 (which will read/mutate score_result['overallScore']) is exercised on
    # the real key shape, not a phantom 'overall'.
    score_result = {
        "overallScore": 73,
        "dimensionScores": {"angle": 70, "line": 75, "stability": 80},
    }
    snapshot = {
        "overallScore": score_result["overallScore"],
        "dimensionScores": dict(score_result["dimensionScores"]),
    }
    out = veto(score_result)
    assert out is score_result  # SAME object identity (v1 = pass-through)
    assert score_result["overallScore"] == snapshot["overallScore"]
    assert score_result["dimensionScores"] == snapshot["dimensionScores"]
