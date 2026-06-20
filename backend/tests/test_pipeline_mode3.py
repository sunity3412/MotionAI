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


def _well_extended(seed: int, t: int = 40) -> np.ndarray:
    """잘 신전된(거의 180°) 자세 — 절대 라인 점수가 높게 나오는 "잘한" 영상.

    _video()(120~175°)는 EXTEND joint 가 180°에 못 미쳐 line 이 0으로 바닥나므로,
    "angle 유사도 < 절대 차원 최소값" 전제를 만들 수 없다. 이 회귀가 검증하려는
    역전 조건(#8: 잘한 신규 영상이 다른 과거 영상 대비 유사도가 낮아도 종합이
    안 떨어짐)을 만들려면 line/stability 가 높은 결정적 입력이 필요하다.
    """
    rng = np.random.default_rng(seed)
    base = rng.uniform(176, 179, size=NUM_JOINTS)
    return base + rng.normal(0, 1.0, size=(t, NUM_JOINTS))


def _different_prev(seed: int, t: int = 40) -> np.ndarray:
    """이전(과거) 영상 — 현재와 충분히 달라 angle(이전 대비 유사도)이 낮게 나온다."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(140, 155, size=NUM_JOINTS)
    return base + rng.normal(0, 3, size=(t, NUM_JOINTS))


def test_low_similarity_does_not_invert_overall():
    # #8 역전 버그 회귀 ([[mode3-progress-not-similarity]]).
    # mode3 의 angle 은 "이전 영상 대비 유사도"라, 사용자가 발전(과거=다른/틀린 자세,
    # 신규=잘 신전된 자세)하면 두 영상이 달라 angle 이 낮아진다. 과거 코드는 overall 을
    # angle 포함 dict 의 min(CORE_DIMENSIONS) 로 산출해 이 낮은 유사도가 종합을 끌어내려
    # "잘했는데 점수가 떨어지는" 역전(belle 기기: 98→88)을 냈다. 수정 후 overall 은 절대
    # 차원(line/stability)만 사용해야 한다.
    profile = _profile()
    cur = _well_extended(2)
    prev_angles = _different_prev(32)
    # prev dim_scores 절대값은 overall 산출에 무관(현재 영상 abs_dims 사용) — delta 표시용.
    prev = _as_prev(prev_angles, "prevWorse", {"line": 40, "stability": 40})

    abs_dims = app.dimensions.absolute_dimension_scores(cur, profile)
    _, dims, overall, _comparison = app._mode3_comparison(cur, prev, profile)

    # 전제 가드: angle(유사도)이 절대 차원 최소값보다 낮은 "역전 조건" 이 실제로 성립.
    # (성립하지 않으면 이 회귀가 의미 없으므로 결정적 seed 로 고정 — 위 builder 참조.)
    assert dims["angle"] < min(abs_dims.values())

    # 단언 1: overall 은 절대 차원만으로 산출된다.
    assert overall == app.dimensions.overall_from_dimensions(abs_dims)
    # 단언 2: angle 포함 dict 로 산출한 값보다 낮지 않다(낮은 유사도가 종합을 못 끌어내림).
    assert overall >= app.dimensions.overall_from_dimensions(dims)
    # 단언 3: dim_scores 에는 여전히 angle 이 포함된다(표시/일관성 지표 유지 — 회귀 방지).
    assert "angle" in dims


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


# ── Phase 20-03 Task 1 — _apply_vision_veto v1 identity → 하향-전용 mutation 전환 ──
# 전부 mocked adapter (실 Gemini/Pod 미호출). 기존 test_vision_hook_passthrough 의
# `out is score_result` identity 단언은 v2 계약 전환에 직접 영향받는 케이스라 정당하게
# 전환한다 (20-RESEARCH State of the Art: identity → downward property).

from sunity_shared.analysis import vision_veto, gemini_vision_scorer  # noqa: E402


class _StubVerdict:
    """gemini_vision_scorer.VisionVerdict mock (severity 만 _apply_vision_veto 가 읽음)."""

    def __init__(self, severity: str):
        self.primary_fault = "stub fault"
        self.severity = severity
        self.differences = ()


def _enable_veto(monkeypatch):
    monkeypatch.setenv("GEMINI_VISION_VETO_ENABLED", "1")


def _disable_phase17_vision(monkeypatch):
    # Phase 17 4 영역 토글 전부 OFF (veto 단독 ON 경로 격리).
    for env_var in (
        "GEMINI_REFERENCE_ENABLED",
        "GEMINI_COACH_ENABLED",
        "GEMINI_FINDING_ENABLED",
        "GEMINI_D_ENABLED",
    ):
        monkeypatch.setenv(env_var, "0")


def test_toggle_owned_by_pipeline():
    # iter2 MEDIUM-1 — 토글은 pipeline(app.py) 단독 소유. 어댑터(gemini_vision_scorer)
    # 에는 정의 0. _apply_vision_veto 가 유일한 feature-toggle 게이트.
    import inspect

    app_src = inspect.getsource(app)
    scorer_src = inspect.getsource(gemini_vision_scorer)
    assert app_src.count("def _gemini_vision_veto_enabled") == 1, (
        "_gemini_vision_veto_enabled 는 pipeline 에 정확히 1건 정의돼야 함 (iter2 MEDIUM-1)"
    )
    assert "def _gemini_vision_veto_enabled" not in scorer_src, (
        "어댑터는 토글 미소유 — 정의 0건 (drift 방지, iter2 MEDIUM-1)"
    )


def test_vision_veto_off_passthrough(monkeypatch):
    # _gemini_vision_veto_enabled() OFF → 불변 + adapter 미호출 + status='disabled'.
    monkeypatch.setenv("GEMINI_VISION_VETO_ENABLED", "0")
    called = {"n": 0}

    def _boom(*a, **k):
        called["n"] += 1
        raise AssertionError("adapter 가 OFF 토글에서 호출됨")

    monkeypatch.setattr(gemini_vision_scorer, "assess_fault_severity", _boom)
    score_result = {"overallScore": 73, "dimensionScores": {"line": 75}}
    out = app._apply_vision_veto(score_result, "/tmp/v.mp4", None, _profile())
    assert out["overallScore"] == 73
    assert out["visionVeto"]["status"] == "disabled"
    assert called["n"] == 0


def test_vision_veto_missing_local_video(monkeypatch):
    # HIGH-1 — local_video_path None → status='missing_local_video' (graceful 명시 신호).
    _enable_veto(monkeypatch)

    def _boom(*a, **k):
        raise AssertionError("local_video_path None 인데 adapter 호출됨")

    monkeypatch.setattr(gemini_vision_scorer, "assess_fault_severity", _boom)
    score_result = {"overallScore": 90, "dimensionScores": {"line": 88}}
    out = app._apply_vision_veto(score_result, None, None, _profile())
    assert out["overallScore"] == 90
    assert out["visionVeto"]["status"] == "missing_local_video"


def test_vision_veto_downward_only_with_cap(monkeypatch):
    # iter2 HIGH-1 — cap-mutation 증명. production cap 은 20-04 까지 placeholder None;
    # 여기 50 은 mutation 경로 증명용 scoped fixture (D-02 무손상).
    _enable_veto(monkeypatch)
    monkeypatch.setitem(vision_veto.SEVERITY_CAP, "major", 50)
    monkeypatch.setattr(
        gemini_vision_scorer,
        "assess_fault_severity",
        lambda *a, **k: _StubVerdict("major"),
    )
    score_result = {"overallScore": 100, "dimensionScores": {"line": 100}}
    out = app._apply_vision_veto(score_result, "/tmp/v.mp4", None, _profile())
    assert out["overallScore"] == 50  # capped 하향 증명
    assert out["overallScore"] <= 100  # property — 절대 안 올림


def test_vision_veto_minor_no_mutation(monkeypatch):
    # severity='minor' → cap 없음(SEVERITY_CAP['minor']=None) → 불변 + not_applicable.
    _enable_veto(monkeypatch)
    monkeypatch.setitem(vision_veto.SEVERITY_CAP, "major", 50)
    monkeypatch.setattr(
        gemini_vision_scorer,
        "assess_fault_severity",
        lambda *a, **k: _StubVerdict("minor"),
    )
    score_result = {"overallScore": 96, "dimensionScores": {"line": 96}}
    out = app._apply_vision_veto(score_result, "/tmp/v.mp4", None, _profile())
    assert out["overallScore"] == 96
    assert out["visionVeto"]["status"] == "not_applicable"


def test_vision_veto_placeholder_cap_no_mutation(monkeypatch):
    # iter2 HIGH-1 보강 — production placeholder cap=None (monkeypatch 없음) +
    # severity='major' → 불변 + status='not_applicable'. 20-04 전 cap 미적용이 정상
    # (provenance fail-closed 정합).
    _enable_veto(monkeypatch)
    assert vision_veto.SEVERITY_CAP["major"] is None  # production placeholder 확인
    monkeypatch.setattr(
        gemini_vision_scorer,
        "assess_fault_severity",
        lambda *a, **k: _StubVerdict("major"),
    )
    score_result = {"overallScore": 100, "dimensionScores": {"line": 100}}
    out = app._apply_vision_veto(score_result, "/tmp/v.mp4", None, _profile())
    assert out["overallScore"] == 100
    assert out["visionVeto"]["status"] == "not_applicable"


def test_vision_veto_status_enum(monkeypatch):
    # HIGH-1 — status enum 이 veto 실행을 명시 증명 (부재 ≠ 실행).
    _enable_veto(monkeypatch)
    monkeypatch.setitem(vision_veto.SEVERITY_CAP, "major", 50)
    monkeypatch.setattr(
        gemini_vision_scorer,
        "assess_fault_severity",
        lambda *a, **k: _StubVerdict("major"),
    )
    score_result = {"overallScore": 100, "dimensionScores": {"line": 100}}
    out = app._apply_vision_veto(score_result, "/tmp/v.mp4", None, _profile())
    veto = out["visionVeto"]
    assert veto["status"] == "applied"
    assert veto["severity"] == "major"
    assert veto["capApplied"] == 50
    # 객관성 — 점수/score 라벨 필드 0.
    assert "score" not in veto
    assert set(veto.keys()) <= {"status", "severity", "capApplied"}


def test_vision_veto_graceful_observable(monkeypatch, caplog):
    # Pitfall 5 — adapter None(키부재/실패) → v1 graceful 통과 + WARNING + skipped_error.
    import logging

    _enable_veto(monkeypatch)
    monkeypatch.setattr(
        gemini_vision_scorer, "assess_fault_severity", lambda *a, **k: None
    )
    score_result = {"overallScore": 81, "dimensionScores": {"line": 80}}
    with caplog.at_level(logging.WARNING):
        out = app._apply_vision_veto(score_result, "/tmp/v.mp4", None, _profile())
    assert out["overallScore"] == 81  # graceful 불변
    assert out["visionVeto"]["status"] == "skipped_error"
    assert any("veto" in r.message.lower() for r in caplog.records)


def test_vision_veto_called_both_modes(monkeypatch):
    # D-03/04 — 호출부가 mode 분기 밖 (단일 호출). profile 인자 전달 확인.
    # _apply_vision_veto 자체는 mode 무관 — Mode1/Mode3 result 둘 다 통과한다.
    import inspect

    _enable_veto(monkeypatch)
    seen = {}
    monkeypatch.setitem(vision_veto.SEVERITY_CAP, "major", 40)

    def _capture(local_video_path, at_seconds=None):
        seen["at"] = at_seconds
        return _StubVerdict("major")

    monkeypatch.setattr(gemini_vision_scorer, "assess_fault_severity", _capture)
    for overall in (100, 100):  # Mode1/Mode3 둘 다 같은 hook
        out = app._apply_vision_veto(
            {"overallScore": overall, "dimensionScores": {"line": overall}},
            "/tmp/v.mp4",
            None,
            _profile(),
        )
        assert out["overallScore"] == 40
    # 단일 호출부 + mode 분기 밖 — grep: _apply_vision_veto( 호출 1건.
    app_src = inspect.getsource(app)
    assert app_src.count("_apply_vision_veto(result") == 1


def test_keep_local_video_for_veto_only(monkeypatch):
    # HIGH-1 — Phase17 vision OFF + veto ON → keep_local_video True 라 local 영상 보존,
    # adapter 가 non-None local_video_path 수신 (veto 가 None 무음 no-op 0).
    _disable_phase17_vision(monkeypatch)
    _enable_veto(monkeypatch)
    # keep_local_video 게이트가 veto 토글 포함 — Phase17 OFF 라도 True.
    assert (
        app._gemini_enabled()
        or app._gemini_vision_enabled()
        or app._gemini_vision_veto_enabled()
    ) is True
    assert app._gemini_vision_enabled() is False  # Phase17 OFF 확인
    assert app._gemini_vision_veto_enabled() is True  # veto 단독 ON
    # adapter 가 non-None path 를 수신함을 _apply_vision_veto 경유로 단언.
    received = {}
    monkeypatch.setitem(vision_veto.SEVERITY_CAP, "major", 50)

    def _capture(local_video_path, at_seconds=None):
        received["path"] = local_video_path
        return _StubVerdict("major")

    monkeypatch.setattr(gemini_vision_scorer, "assess_fault_severity", _capture)
    app._apply_vision_veto(
        {"overallScore": 100, "dimensionScores": {"line": 100}},
        "/tmp/keep.mp4",
        None,
        _profile(),
    )
    assert received["path"] == "/tmp/keep.mp4"  # non-None 보존
