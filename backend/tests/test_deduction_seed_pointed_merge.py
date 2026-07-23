"""Phase 25 (25-01 Task 2) — angle_vs_reference seed 관절 단위 2-source merge 테스트.

_build_deduction_measured_deviations 의 vision_pointed_joints kwarg:
  · pointed ∩ windowMedianAngleDeltas 관절만 worst-window median 값(abs) 방출,
  · Gemini-silent 관절은 기존 full-path DTW median(per_joint_deviation) 유지.

260702-o0c(f513587, reverted) FAIL 의 정확한 해소 — 경로 단위 either/or(wm 있으면
전 관절 window)가 silent 관절까지 window 편향 표집해 success 위양성 4건을 냈다.
관절 단위 merge 는 "짚기=Gemini / 측정=짚인 관절만 window / silent=full-path 유지"
(25-RESEARCH §2). pointed=None/빈 경로는 기존 동작과 동일(무회귀).

전부 mock-based 순수 builder 테스트 — 실 Gemini/Pod/S3/Firestore 호출 0.
# 보유 sweep 수치 타깃 아님 — 방향/구조 단언만 (curve-fit 금지).
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

_LEFT_SHOULDER = JOINT_KEYS.index("left_shoulder")
_RIGHT_SHOULDER = JOINT_KEYS.index("right_shoulder")
_LEFT_KNEE = JOINT_KEYS.index("left_knee")


def _unregistered_profile():
    """미등록 동작 profile — expects_extension 전부 False."""
    return technique.TechniqueProfile(
        name="미등록: ref-kip-up", category="unknown", joint_expectations={}
    )


def _extend_profile():
    """무릎/팔꿈치 EXTEND 프로파일 — cross-exclusion 대상."""
    exp = {
        k: technique.JOINT_EXTEND
        if k.endswith("elbow") or k.endswith("knee")
        else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(
        name="t", category="unknown", joint_expectations=exp
    )


def _identity_match(T):
    return MotionMatch(
        start=0, end=T, ref_start=0, ref_end=T,
        distance=0.0, path=[(i, i) for i in range(T)],
    )


def _quant(wm_deltas=None):
    """VisionQuantificationResult stub — wm_deltas 는 windowMedianAngleDeltas.deltas."""
    wm = None
    if wm_deltas is not None:
        wm = {
            "deltas": list(wm_deltas),
            "sourceFrameIndices": {"user": [3], "reference": [3]},
            "windowPolicy": "worst_pose_center±2",
        }
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="available",
        angleDeltas=None,
        bodyRelativeNotches=None,
        windowMedianAngleDeltas=wm,
        warnings=(),
    )


def _angles(T=10, deg=170.0):
    return np.full((T, len(JOINT_KEYS)), deg, dtype=float)


def _md(*, usr, ref, profile, quantification, T=10, **kw):
    return app._build_deduction_measured_deviations(
        angles=usr, profile=profile, assessments=[], dimension_scores={},
        quantification=quantification,
        reference_dtw_match=_identity_match(T), reference_angles=ref, **kw,
    )


# ── 관절 단위 merge (핵심) ────────────────────────────────────────────────────


def test_pointed_joint_window_silent_joint_dtw_fallback():
    """pointed=left_shoulder → window 값(abs Δ40.4), silent right_shoulder → DTW median.

    260702-o0c FAIL 의 정확한 해소 — 경로 either/or 아님, 관절 단위 선택."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0   # DTW 편차 40.0 (window 40.4 와 구별)
    usr[:, _RIGHT_SHOULDER] = 140.0  # DTW 편차 30.0 (window 31.0 과 구별)
    wm = [
        {"joint": "left_shoulder", "delta_deg": -40.4},  # SIGNED → abs
        {"joint": "right_shoulder", "delta_deg": 31.0},
    ]
    md = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(),
        quantification=_quant(wm),
        vision_pointed_joints=("left_shoulder",),
    )
    assert md["angle_vs_reference__left_shoulder"] == pytest.approx(40.4)
    # Gemini-silent 관절은 wm 에 있어도 window 값 금지 — full-path DTW median 유지.
    assert md["angle_vs_reference__right_shoulder"] == pytest.approx(30.0)


def test_pointed_none_or_empty_is_byte_identical_to_legacy():
    """pointed=None/빈 tuple → 전 관절 DTW fallback (기존 24-05/260626-e5k 동작과 동일)."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    wm = [{"joint": "left_shoulder", "delta_deg": -40.4}]
    baseline = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(wm),
    )
    md_none = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(wm),
        vision_pointed_joints=None,
    )
    md_empty = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(wm),
        vision_pointed_joints=(),
    )
    assert baseline == md_none == md_empty
    # window 40.4 가 아닌 DTW 40.0 — wm 존재만으로는 window 표집 금지.
    assert baseline["angle_vs_reference__left_shoulder"] == pytest.approx(40.0)


def test_pointed_joint_missing_from_wm_falls_back_to_dtw():
    """pointed 관절인데 wm 에 해당 joint 없음 → 그 관절은 DTW fallback (경로 either/or 아님)."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    wm = [{"joint": "right_shoulder", "delta_deg": 31.0}]  # left_shoulder 부재
    md = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(wm),
        vision_pointed_joints=("left_shoulder",),
    )
    assert md["angle_vs_reference__left_shoulder"] == pytest.approx(40.0)  # DTW


def test_expects_extension_excluded_from_both_paths():
    """expects_extension(jk)=True 관절 → window/DTW 양 경로 모두 미방출 (§3-2 cross-exclusion)."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_KNEE] = 130.0  # EXTEND 소유 — ipsf_absolute 가 채점
    wm = [{"joint": "left_knee", "delta_deg": 40.0}]
    md = _md(
        usr=usr, ref=ref, profile=_extend_profile(), quantification=_quant(wm),
        vision_pointed_joints=("left_knee",),
    )
    assert "angle_vs_reference__left_knee" not in md


def test_wm_nan_zero_malformed_entries_fall_back_to_dtw():
    """wm delta NaN/0/형상불량 entry → 그 관절 fallback 강하 (honest skip)."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    usr[:, _RIGHT_SHOULDER] = 140.0
    wm = [
        {"joint": "left_shoulder", "delta_deg": float("nan")},
        {"joint": "right_shoulder", "delta_deg": 0.0},
        "garbage-entry",
        {"joint": "left_hip"},  # delta_deg 부재
        {"joint": "right_hip", "delta_deg": "notanumber"},
    ]
    md = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(wm),
        vision_pointed_joints=("left_shoulder", "right_shoulder"),
    )
    assert md["angle_vs_reference__left_shoulder"] == pytest.approx(40.0)   # DTW
    assert md["angle_vs_reference__right_shoulder"] == pytest.approx(30.0)  # DTW


def test_deterministic_merge():
    """동일 입력 2회 → 동일 md (결정성)."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    wm = [{"joint": "left_shoulder", "delta_deg": -40.4}]
    kwargs = dict(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(wm),
        vision_pointed_joints=("left_shoulder",),
    )
    assert _md(**kwargs) == _md(**kwargs)


# ── seed_audit_out 관측 파라미터 ──────────────────────────────────────────────


def test_seed_audit_out_records_pointed_window_fallback():
    """seed_audit_out dict 전달 시 {pointed, window_joints, fallback_joints} 기록."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    usr[:, _RIGHT_SHOULDER] = 140.0
    wm = [{"joint": "left_shoulder", "delta_deg": -40.4}]
    audit: dict = {}
    md = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(wm),
        vision_pointed_joints=("left_shoulder",), seed_audit_out=audit,
    )
    assert audit["pointed"] == ["left_shoulder"]
    assert audit["window_joints"] == ["left_shoulder"]
    assert "right_shoulder" in audit["fallback_joints"]
    assert "left_shoulder" not in audit["fallback_joints"]
    # audit 기록이 md 산출을 바꾸지 않는다.
    md_no_audit = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(wm),
        vision_pointed_joints=("left_shoulder",),
    )
    assert md == md_no_audit


def test_seed_audit_out_absent_no_side_effects():
    """seed_audit_out 미전달(default None) → 기존 시그니처 호출 그대로 동작 (무회귀)."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    md = _md(
        usr=usr, ref=ref, profile=_unregistered_profile(), quantification=_quant(None),
    )
    assert md["angle_vs_reference__left_shoulder"] == pytest.approx(40.0)
