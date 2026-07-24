"""33-NEXT (역립 관절 귀속 정밀도) — attribution_unreliable 마커 테스트.

근거: .planning/debug/inversion-joint-attribution.md (H1 확정, magnitude-neutral fix),
33-NEXT-JOINT-ATTRIBUTION-SEED.md 가설3, reliability.py H-4 "단정형 금지".

검증 대상:
  1. 순수 함수 _assess_attribution_reliability — phase25 baseline 실측 5 fault fixture 값으로
     elbow-twist-sister / pdshape 만 발화, power-spin / peter-pan / kip-up 미발화(완전 변별).
  2. 마커는 seed_audit_out 에만 기록되고 md(점수 substrate)를 절대 변경하지 않는다
     (magnitude-neutral — 점수 record/final byte-불변).
  3. builder 통합 — 저신뢰-광범위-다관절 입력에서 unreliable=True + aggregateStatement 방출,
     비역립(over-tol 3) / vision-짚음 / 고정렬 입력에서 미발화.

전부 mock-based 순수 테스트 — 실 Gemini/Pod/S3/Firestore 호출 0.
# 보유 sweep 수치 타깃 아님 — 게이트 임계(≥5/vis0.70/dist60)는 5-fixture 로컬 유도이며,
# 일반화·비역립 무오발은 6-fixture serial GPU sweep 로 재검증한다(curve-fit 금지).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

import app  # noqa: E402
from sunity_shared.analysis import technique, vision_veto  # noqa: E402
from sunity_shared.analysis.motiondtw import MotionMatch  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402


# phase25 baseline (backend/evals/phase25/baseline/phase25_sweep_report.json) 실측 —
# (over_tol_count, visibility, dtw_distance, gemini_silent, expect_unreliable).
# over_tol_count = deductionBreakdown 의 angle_vs_reference__{jk} record 수(tol 20° 초과).
# gemini_silent = seedObservation.pointed 공집합. visibility/distance = visionVeto.alignment.
_RECORDED_FAULT_FIXTURES = {
    "power-spin":         (3, 0.708, 60.13, True,  False),
    "peter-pan":          (3, 0.815, 51.44, True,  False),
    "elbow-twist-sister": (7, 0.686, 62.90, True,  True),
    "pdshape":            (8, 0.448, 64.32, True,  True),
    "kip-up":             (2, 0.806, 26.94, False, False),  # pointed=4 → not silent
}


@pytest.mark.parametrize(
    "name,over_tol,vis,dist,silent,expect",
    [(k, *v) for k, v in _RECORDED_FAULT_FIXTURES.items()],
)
def test_recorded_fixture_discrimination(name, over_tol, vis, dist, silent, expect):
    """실측 5 fault fixture — 마커가 정확히 역립 2개(elbow-twist/pdshape)에만 발화."""
    marker = app._assess_attribution_reliability(
        gemini_silent=silent,
        over_tol_count=over_tol,
        visibility=vis,
        dtw_distance=dist,
    )
    assert marker["unreliable"] is expect, (
        f"{name}: over_tol={over_tol} vis={vis} dist={dist} silent={silent} "
        f"→ expected unreliable={expect}, got {marker['unreliable']}"
    )
    # 발화 시에만 다운스트림 강등용 clean aggregate 를 실어야 한다.
    assert ("aggregateStatement" in marker) is expect


def test_recorded_success_fixtures_never_fire():
    """success fixture(over-tol=0) — 결함 record 자체가 없으므로 절대 미발화."""
    for vis in (0.74, 0.784, 0.785, 0.793, 0.817):  # phase25 success alignment.visibility
        marker = app._assess_attribution_reliability(
            gemini_silent=True, over_tol_count=0, visibility=vis, dtw_distance=44.1
        )
        assert marker["unreliable"] is False


def test_each_gate_is_necessary():
    """3-조건 AND — 어느 한 조건이라도 빠지면 미발화(개별 게이트 필요성)."""
    base = dict(gemini_silent=True, over_tol_count=7, visibility=0.686, dtw_distance=62.9)
    assert app._assess_attribution_reliability(**base)["unreliable"] is True
    # 1) vision 이 짚으면(silent=False) 미발화 — 특정 결함이 있으므로 그대로 귀속.
    assert app._assess_attribution_reliability(
        **{**base, "gemini_silent": False}
    )["unreliable"] is False
    # 2) over-tol < 5 면 미발화 — 국소 결함(2~3관절)은 정당 귀속.
    assert app._assess_attribution_reliability(
        **{**base, "over_tol_count": 4}
    )["unreliable"] is False
    # 3) 고정렬(vis≥0.70 AND dist≤60)이면 미발화 — 측정 신뢰 가능.
    assert app._assess_attribution_reliability(
        **{**base, "visibility": 0.80, "dtw_distance": 40.0}
    )["unreliable"] is False


def test_distance_alone_can_trip_low_alignment():
    """visibility 없어도 DTW distance > 60 이면 저정렬 조건 성립(OR 게이트)."""
    marker = app._assess_attribution_reliability(
        gemini_silent=True, over_tol_count=8, visibility=None, dtw_distance=64.3
    )
    assert marker["unreliable"] is True


def test_none_signals_do_not_trip_alignment():
    """visibility/distance 둘 다 None → 저정렬 신호 없음 → 미발화(과발화 방지)."""
    marker = app._assess_attribution_reliability(
        gemini_silent=True, over_tol_count=8, visibility=None, dtw_distance=None
    )
    assert marker["unreliable"] is False


# ── builder 통합 (md byte-불변 + seedObservation 마커) ──────────────────────────


def _unregistered_profile():
    return technique.TechniqueProfile(
        name="미등록: inverted", category="unknown", joint_expectations={}
    )


def _match(T, distance):
    return MotionMatch(
        start=0, end=T, ref_start=0, ref_end=T,
        distance=distance, path=[(i, i) for i in range(T)],
    )


def _quant():
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="available", angleDeltas=None,
        bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=(),
    )


def _angles(T=10, deg=170.0):
    return np.full((T, len(JOINT_KEYS)), deg, dtype=float)


def _inversion_like_user(T=10, n_over_tol=7):
    """n_over_tol 관절을 ref 대비 25° 굽혀 광범위 다관절 over-tol 을 재현."""
    usr = _angles(T)
    for j in range(min(n_over_tol, len(JOINT_KEYS))):
        usr[:, j] = 145.0  # ref 170 대비 편차 25° (>tol 20°)
    return usr


def _build(
    usr, *, distance, visibility, pointed=(), seed_audit_out=None,
    visibility_measured=True, vision_status="no_fault",
):
    # vision_status 기본 = "no_fault"(역립 실측: vision severity=none = affirmative 침묵).
    # visibility_measured 기본 = True(실측 fixture 는 genuine keypoint confidence 측정값).
    return app._build_deduction_measured_deviations(
        angles=usr, profile=_unregistered_profile(), assessments=[],
        dimension_scores={}, quantification=_quant(),
        reference_dtw_match=_match(usr.shape[0], distance),
        reference_angles=_angles(usr.shape[0]),
        vision_pointed_joints=pointed,
        alignment_visibility=visibility,
        alignment_visibility_measured=visibility_measured,
        vision_status=vision_status,
        seed_audit_out=seed_audit_out,
    )


def test_marker_does_not_mutate_score_substrate():
    """md(점수 substrate)는 마커 계산 유무와 무관하게 byte-동일(magnitude-neutral)."""
    usr = _inversion_like_user(n_over_tol=7)
    md_no_audit = _build(usr, distance=62.9, visibility=0.686)
    audit: dict = {}
    md_with_audit = _build(usr, distance=62.9, visibility=0.686, seed_audit_out=audit)
    assert md_no_audit == md_with_audit  # 점수 record source 불변
    # 마커는 seed_audit_out 에만 기록된다(스키마 side-channel).
    assert audit["attributionReliability"]["unreliable"] is True
    assert "aggregateStatement" in audit["attributionReliability"]


def test_builder_fires_on_inversion_like_input():
    """광범위 다관절(7 over-tol) + silent + 저신뢰(vis<0.70) → unreliable=True."""
    audit: dict = {}
    _build(_inversion_like_user(n_over_tol=7), distance=62.9, visibility=0.686,
           seed_audit_out=audit)
    m = audit["attributionReliability"]
    assert m["unreliable"] is True
    assert m["overTolJointCount"] == 7
    assert m["geminiSilent"] is True


def test_builder_does_not_fire_on_narrow_fault():
    """국소 결함(3 over-tol) → 미발화(전역 부양 아님, 정당 per-joint 귀속 유지)."""
    audit: dict = {}
    _build(_inversion_like_user(n_over_tol=3), distance=62.9, visibility=0.686,
           seed_audit_out=audit)
    assert audit["attributionReliability"]["unreliable"] is False


def test_builder_does_not_fire_when_vision_pointed():
    """Gemini 가 관절을 짚으면(pointed 비어있지 않음) 광범위여도 미발화."""
    audit: dict = {}
    _build(_inversion_like_user(n_over_tol=7), distance=62.9, visibility=0.686,
           pointed=("left_shoulder",), seed_audit_out=audit)
    assert audit["attributionReliability"]["unreliable"] is False


def test_builder_does_not_fire_on_high_alignment():
    """고정렬(vis≥0.70 AND dist≤60)이면 광범위·silent 여도 미발화."""
    audit: dict = {}
    _build(_inversion_like_user(n_over_tol=7), distance=40.0, visibility=0.80,
           seed_audit_out=audit)
    assert audit["attributionReliability"]["unreliable"] is False


# ── WR-01 (WARNING fix) — vision 부재/오류 상태에서 pointed=∅ 은 침묵이 아니다 ─────────


@pytest.mark.parametrize("bad_status", ["skipped_error", "resource_limited"])
def test_builder_does_not_fire_on_vision_error_status(bad_status):
    """vision 실패/보류 상태(pointed=∅)에서는 광범위 편차 + 고 dtw 여도 미발화(WR-01).

    skipped_error / resource_limited 는 vision 이 부재/실패한 signal-absent 상태다. pointed=∅
    은 "짚을 게 없음(침묵)"이 아니라 "vision 이 못 봄"이므로, 저신뢰-역립으로 오인해 발화하면
    안 된다(vision 오류를 attribution-unreliable 로 잘못 라벨). 나머지 조건(over-tol 7, silent
    표면상 ∅, vis 0.686<0.70, dist 62.9>60)은 발화 임계를 전부 넘김에도 미발화여야 한다.
    """
    audit: dict = {}
    _build(_inversion_like_user(n_over_tol=7), distance=62.9, visibility=0.686,
           vision_status=bad_status, seed_audit_out=audit)
    m = audit["attributionReliability"]
    assert m["unreliable"] is False
    assert m["geminiSilent"] is False  # signal-absent → silent 로 승격하지 않음


def test_builder_fires_on_affirmative_no_fault_status():
    """대조군 — 동일 신호가 affirmative no_fault 상태에서는 정상 발화(WR-01 회귀 방어)."""
    audit: dict = {}
    _build(_inversion_like_user(n_over_tol=7), distance=62.9, visibility=0.686,
           vision_status="no_fault", seed_audit_out=audit)
    assert audit["attributionReliability"]["unreliable"] is True


# ── WR-02 (WARNING fix) — 미측정 visibility(0.0 sentinel)는 발화에 기여하지 않는다 ──────


def test_builder_treats_unmeasured_visibility_as_signal_absent():
    """미측정 visibility(0.0 sentinel)는 genuine worst 가 아니므로 발화에 기여 금지(WR-02).

    frame-pair 선택 실패 시 assess_alignment_confidence 가 keypoint confidence 를 0.0 으로
    collapse 한다. distance≤60(저정렬 아님)에서 유일한 저정렬 후보가 visibility 뿐일 때,
    미측정 0.0 을 genuine worst(0.0<0.70)로 읽으면 오발한다. visibility_measured=False 면
    None 으로 강등돼 저정렬 조건이 성립하지 않아야 한다.
    """
    audit: dict = {}
    _build(_inversion_like_user(n_over_tol=7), distance=50.0, visibility=0.0,
           visibility_measured=False, seed_audit_out=audit)
    m = audit["attributionReliability"]
    assert m["unreliable"] is False
    assert m["visibility"] is None  # 미측정 → 마커에 None 으로 전달(0.0 sentinel 아님)


def test_builder_fires_on_measured_terrible_visibility():
    """대조군 — 동일 0.0 이 실제 측정값(measured-and-terrible)이면 저정렬 성립 → 발화(WR-02).

    distance 50(저정렬 아님)이라 visibility 만이 저정렬 후보다. measured 0.0<0.70 이면
    genuine worst 이므로 정상 발화해야 한다(미측정과 측정-최악의 변별을 증명)."""
    audit: dict = {}
    _build(_inversion_like_user(n_over_tol=7), distance=50.0, visibility=0.0,
           visibility_measured=True, seed_audit_out=audit)
    m = audit["attributionReliability"]
    assert m["unreliable"] is True
    assert m["visibility"] == 0.0  # 측정값 그대로 전달
