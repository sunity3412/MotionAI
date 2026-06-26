"""v2 비전 코어 단위테스트 (Phase 20-01 + Phase 24 밴드 제거, ND-01/ND-02/D-05).

이 모듈은 vision_veto.py 의 안전 성질을 코드로 못 박는다:
  - Phase 24: severity→고정천장 밴드(옛 severity-cap 상수/함수)는 제거됐다 —
    채점은 deduction_engine.tally(측정편차→명시규칙 감점) 로 옮겨졌고 그 seam 테스트는
    test_pipeline_deduction_seam.py 가 소유한다. 여기서는 measurement/FaultKey/baseline/
    worst-pose helper + 정량화(칸/각도) substrate 만 검증한다.
  - to_audit_dict 는 밴드-free — applied 시 tallyFinal(deduction tally final)만 방출.
  - D-05 worst-pose: key_moments(hold/peak) 재사용 — IPSF phase 평균 거부.

전부 pod-free 순수 단위테스트 (numpy 외 의존 0). PYTHONPATH=shared/python.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# PYTHONPATH=backend/shared/python 컨벤션 (test_pipeline_mode3 정합) 보강.
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import vision_veto  # noqa: E402


def test_band_layer_removed():
    """Phase 24 (ND-01) — severity→고정천장 밴드는 제거됐다 (자의적 밴드 금지).

    옛 severity-cap 상수/함수/provenance 가 더 이상 존재하지 않는다(literal 토큰을
    소스에 남기지 않으려 동적 attr 이름으로 검사). measurement/baseline helper 는 보존된다.
    """
    _retired_attrs = ("apply_downward" + "_cap", "SEVERITY" + "_CAP", "SEVERITY" + "_CAP_PROVENANCE")
    for attr in _retired_attrs:
        assert not hasattr(vision_veto, attr), f"{attr} 가 아직 존재 (밴드 미제거)"
    # 보존 helper.
    for attr in (
        "body_relative_notches", "build_quantification_result",
        "worst_pose_timestamp", "fault_key_from_difference", "BASELINE_KINDS",
        "FramePairMeasurementContext",
    ):
        assert hasattr(vision_veto, attr), f"{attr} 보존 위반"


def _km(moment_key: str, ts: float):
    """KeyMoment 호환 가짜 객체 (moment_key/timestamp_seconds 속성만 사용)."""
    return SimpleNamespace(moment_key=moment_key, timestamp_seconds=ts)


def test_worst_pose_prefers_hold():
    """hold > peak > 전체 우선순위로 key_moments 재사용, None/빈 → None (D-05)."""
    # hold + peak 혼재 → hold 우선 (가장 이른 hold).
    p = SimpleNamespace(
        key_moments=(_km("setup", 0.0), _km("peak", 3.0), _km("hold", 5.0), _km("hold", 7.0))
    )
    assert vision_veto.worst_pose_timestamp(p) == 5.0

    # hold 없음 → peak.
    p2 = SimpleNamespace(key_moments=(_km("setup", 1.0), _km("peak", 4.0), _km("peak", 2.0)))
    assert vision_veto.worst_pose_timestamp(p2) == 2.0

    # hold/peak 둘 다 없음 → 첫 moment (가장 이른).
    p3 = SimpleNamespace(key_moments=(_km("setup", 6.0), _km("release", 2.0)))
    assert vision_veto.worst_pose_timestamp(p3) == 2.0

    # key_moments None / 빈 / 속성 부재 → None (graceful).
    assert vision_veto.worst_pose_timestamp(SimpleNamespace(key_moments=None)) is None
    assert vision_veto.worst_pose_timestamp(SimpleNamespace(key_moments=())) is None
    assert vision_veto.worst_pose_timestamp(SimpleNamespace()) is None


def test_worst_pose_no_new_moment_call():
    """worst_pose_timestamp 가 profile.key_moments 만 읽고 외부 호출 0 (순수).

    소스에 Gemini/네트워크 import 가 0 임을 검증 (모듈은 순수 코어).
    """
    src = Path(vision_veto.__file__).read_text(encoding="utf-8")
    for forbidden in ("genai", "google", "requests", "boto3", "firestore"):
        assert f"import {forbidden}" not in src, (
            f"vision_veto.py 가 {forbidden} 를 import — 순수 모듈 위반"
        )
    # 올림 경로 0 — max( 금지 (min 만 허용).
    assert "max(" not in src, "vision_veto.py 에 max( 가 있다 — 하향-전용 위반 (D-01)"


# ─────────── #3 (2026-06-21) fault_joints_from_differences 매핑 ───────────


def test_fault_joints_maps_korean_body_part_to_keypoints():
    """body_part(한국어 자유텍스트) → 정식 keypoint. 좌/우 추정 + 다리/라인 확장."""
    # 왼팔 → 같은 쪽 손(elbow proxy) + 어깨.
    assert vision_veto.fault_joints_from_differences(
        [{"body_part": "왼팔", "severity": "moderate"}]
    ) == ["left_hand", "left_shoulder"]
    # 오른쪽 무릎 → 우측 무릎만.
    assert vision_veto.fault_joints_from_differences(
        [{"body_part": "오른쪽 무릎"}]
    ) == ["right_knee"]
    # 스트래들 = 양 다리 벌림 → 양쪽 무릎+엉덩이 (side 무관 확장).
    out = vision_veto.fault_joints_from_differences([{"body_part": "스트래들 부족"}])
    assert set(out) == {"left_knee", "left_hip", "right_knee", "right_hip"}


def test_fault_joints_empty_and_unmappable():
    """결함 없음/빈 body_part/모호 → 빈 list (앱이 편차-기반 폴백)."""
    assert vision_veto.fault_joints_from_differences([]) == []
    assert vision_veto.fault_joints_from_differences([{"body_part": ""}]) == []
    # keypoint 매핑 불가능한 순수 모호 표현(키워드 0) → 빈 list.
    assert vision_veto.fault_joints_from_differences(
        [{"body_part": "전반적인 느낌"}]
    ) == []


def test_fault_joints_output_subset_of_highlight_keypoints():
    """출력은 앱이 강조 가능한 8 keypoint 부분집합 — 미표시 keypoint 누출 0."""
    allowed = set(vision_veto._HIGHLIGHT_KEYPOINTS)
    out = vision_veto.fault_joints_from_differences(
        [{"body_part": "발목"}, {"body_part": "허리 라인"}, {"body_part": "left elbow"}]
    )
    assert out, "최소 1개는 매핑돼야"
    assert set(out) <= allowed
    assert len(out) == len(set(out)), "중복 0 (순서 안정 dedup)"


# ─────────────── Task 2 — FaultKey 단일 직렬화 owner (D-17 MED-3) ───────────────


def test_faultkey_to_dict_from_dict_roundtrip():
    """FaultKey.to_dict() ↔ from_dict() round-trip + 정규화 dict 형태 (D-17 MED-3)."""
    fk = vision_veto.FaultKey(
        part_scope="upper_body", side="left", keypoint_set="arm",
        fault_kind="pole_gap_or_bent",
    )
    d = fk.to_dict()
    assert d == {
        "part_scope": "upper_body",
        "side": "left",
        "keypoint_set": "arm",
        "fault_kind": "pole_gap_or_bent",
    }
    # round-trip 항등.
    assert vision_veto.FaultKey.from_dict(d) == fk


def test_faultkey_from_dict_rejects_unknown_enum():
    """from_dict 가 locked enum 밖 값(unknown fault_kind 등)을 raise (D-17 MED-3)."""
    with pytest.raises((ValueError, KeyError)):
        vision_veto.FaultKey.from_dict({
            "part_scope": "upper_body", "side": "left",
            "keypoint_set": "arm", "fault_kind": "banana",
        })
    with pytest.raises((ValueError, KeyError)):
        vision_veto.FaultKey.from_dict({
            "part_scope": "nonsense", "side": "left",
            "keypoint_set": "arm", "fault_kind": "extension_or_alignment",
        })


def test_faultkey_enum_vocabularies_locked():
    """part_scope/side/keypoint_set/fault_kind 의 locked enum 존재 (D-17 MED-3)."""
    assert "upper_body" in vision_veto.FAULT_PART_SCOPES
    assert "core" in vision_veto.FAULT_PART_SCOPES
    assert "lower_body" in vision_veto.FAULT_PART_SCOPES
    assert "line" in vision_veto.FAULT_PART_SCOPES
    assert set(vision_veto.FAULT_SIDES) >= {"left", "right", "unknown"}
    assert "head_neck" in vision_veto.FAULT_KEYPOINT_SETS
    assert "grip" in vision_veto.FAULT_KEYPOINT_SETS


def test_faultkey_from_body_part_normalizes_aliases():
    """좌/우팔 한·영 alias 가 같은 canonical FaultKey 로 정규화 (HIGH-2)."""
    k1 = vision_veto.fault_key_from_difference(
        {"body_part": "왼팔", "fault_state": "폴에서 떨어짐"}, part_scope_hint="upper_body"
    )
    k2 = vision_veto.fault_key_from_difference(
        {"body_part": "left arm", "fault_state": "폴에서 떨어짐"}, part_scope_hint="upper_body"
    )
    k3 = vision_veto.fault_key_from_difference(
        {"body_part": "왼쪽 팔꿈치", "fault_state": "폴에서 떨어짐"}, part_scope_hint="upper_body"
    )
    # 셋 다 같은 정규화 키 (side=left, keypoint_set=arm).
    assert k1.to_dict() == k2.to_dict() == k3.to_dict()
    assert k1.side == "left"
    assert k1.keypoint_set == "arm"


def test_faultkey_ambiguous_arm_is_unknown_side():
    """모호한 '팔'은 side='unknown' — 양쪽 부풀림 방지 (HIGH-2)."""
    k = vision_veto.fault_key_from_difference(
        {"body_part": "팔", "fault_state": "굽음"}, part_scope_hint="upper_body"
    )
    assert k.side == "unknown"


def test_part_keywords_head_neck_grip_expansion():
    """머리/목→어깨, 그립→손 최근접 keypoint 매핑 (ankle→knee 선례)."""
    head = vision_veto._keypoints_for_part("고개 젖힘")
    assert head, "머리/목은 최근접 keypoint(어깨)로 매핑"
    assert set(head) <= set(vision_veto._HIGHLIGHT_KEYPOINTS)
    neck = vision_veto._keypoints_for_part("목 정렬")
    assert neck
    grip = vision_veto._keypoints_for_part("그립 풀림")
    assert grip, "그립은 최근접 keypoint(손)로 매핑"
    assert "left_hand" in grip or "right_hand" in grip


# ─────────────── Task 3 — DTW-confidence 게이팅 + 부위별 worst selector (D-03, H4) ───────────────


def _match(distance, path):
    return SimpleNamespace(start=0, end=len(path), distance=distance, path=path)


def test_alignment_confidence_both_good_single():
    """글로벌 distance 양호 + 로컬 양호 → 'single' 채택 (H4)."""
    # dense path around selected frame + ref-frame 존재 + 가시성 양호.
    path = [(i, i) for i in range(20)]
    out = vision_veto.assess_alignment_confidence(
        match=_match(0.5, path), selected_user_frame=10,
        keypoint_visibility=0.9,
    )
    assert out["adoption"] == "single"


def test_alignment_global_good_local_weak_not_single():
    """글로벌 양호 + 로컬 약함(path sparse/ref-frame 부재) → single 채택 안 함 (H4)."""
    # 선택 프레임 주변 path 가 sparse — 대응 ref-frame 부재.
    path = [(0, 0), (1, 1)]  # 선택 프레임 10 주변 대응 없음.
    out = vision_veto.assess_alignment_confidence(
        match=_match(0.5, path), selected_user_frame=10,
        keypoint_visibility=0.9,
    )
    assert out["adoption"] != "single"
    assert out["adoption"] in ("window_union", "low_alignment_confidence")


def test_alignment_both_bad_low_confidence():
    """글로벌·로컬 모두 실패 → low_alignment_confidence (보류, D-03)."""
    out = vision_veto.assess_alignment_confidence(
        match=_match(50.0, []), selected_user_frame=10,
        keypoint_visibility=0.05,
    )
    assert out["adoption"] == "low_alignment_confidence"


def test_partwise_worst_candidates_exposes_selector_version():
    """부위별 worst 후보 selector + selector_version 노출 (H4/MEDIUM)."""
    prof = SimpleNamespace(
        key_moments=(_km("hold", 5.0), _km("peak", 3.0))
    )
    out = vision_veto.select_worst_frame_candidates(prof)
    assert "selector_version" in out
    assert isinstance(out["selector_version"], str) and out["selector_version"]
    assert "candidates" in out
    # 부위별(상체/하체/라인) 후보 list — 글로벌 worst 1개만이 아님.
    assert isinstance(out["candidates"], (list, tuple))


def test_new_statuses_in_models():
    """low_alignment_confidence + resource_limited 가 VISION_VETO_STATUSES 에 추가 (lockstep)."""
    import sunity_shared.models as models

    assert "low_alignment_confidence" in models.VISION_VETO_STATUSES
    assert "resource_limited" in models.VISION_VETO_STATUSES


# ─────────────── Task 4 — VisionFaultContext / VisionQuantificationResult 분리 ───────────────


def _verdict(severity="moderate"):
    from sunity_shared.analysis.gemini_vision_scorer import VisionVerdict

    return VisionVerdict(primary_fault="다리 신전 부족", severity=severity, differences=())


def test_vision_fault_context_pre_apply_only_fields():
    """VisionFaultContext 가 pre-apply/pre-coach 필드만 — final-audit status·geometry 부재 (D-12 HIGH-1)."""
    import dataclasses

    fields = {f.name for f in dataclasses.fields(vision_veto.VisionFaultContext)}
    # pre-apply/pre-coach 필드 존재.
    assert "collection_status" in fields
    assert "verdict" in fields
    assert "supported_differences" in fields
    assert "root_cause_hypotheses" in fields
    assert "selected_frame_pairs" in fields
    assert "alignment" in fields
    assert "telemetry" in fields
    assert "cap_would_apply" in fields
    # final-audit status / geometry payload 부재.
    assert "status" not in fields, "final-audit status 는 VisionFaultContext 에 없어야 (D-12)"
    assert "angleDeltas" not in fields
    assert "bodyRelativeNotches" not in fields
    assert "windowMedianAngleDeltas" not in fields


def test_collection_status_rejects_final_values():
    """collection_status 는 pre-final enum 만 — applied/not_applicable 거부 (D-13 MED-2)."""
    # candidate_verdict 는 허용.
    ctx = vision_veto.VisionFaultContext(
        collection_status="candidate_verdict", verdict=_verdict(),
        supported_differences=[], root_cause_hypotheses=[],
        selected_frame_pairs=[], alignment={}, telemetry={}, cap_would_apply=True,
    )
    assert ctx.collection_status == "candidate_verdict"
    # applied / not_applicable 로 생성 불가.
    for bad in ("applied", "not_applicable"):
        with pytest.raises((ValueError, TypeError)):
            vision_veto.VisionFaultContext(
                collection_status=bad, verdict=None, supported_differences=[],
                root_cause_hypotheses=[], selected_frame_pairs=[], alignment={},
                telemetry={}, cap_would_apply=False,
            )


def test_eligible_for_coach_property():
    """eligible_for_coach = collection_status==candidate_verdict AND cap_would_apply (D-13 MED-2)."""
    ctx_ok = vision_veto.VisionFaultContext(
        collection_status="candidate_verdict", verdict=_verdict(),
        supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
        alignment={}, telemetry={}, cap_would_apply=True,
    )
    assert ctx_ok.eligible_for_coach is True
    ctx_no_cap = vision_veto.VisionFaultContext(
        collection_status="candidate_verdict", verdict=_verdict(),
        supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
        alignment={}, telemetry={}, cap_would_apply=False,
    )
    assert ctx_no_cap.eligible_for_coach is False
    ctx_held = vision_veto.VisionFaultContext(
        collection_status="mode3_held", verdict=None, supported_differences=[],
        root_cause_hypotheses=[], selected_frame_pairs=[], alignment={},
        telemetry={}, cap_would_apply=False,
    )
    assert ctx_held.eligible_for_coach is False


def test_low_alignment_collect_status_coach_ineligible_audit_provenance():
    """24-04(Option A) — low_alignment_confidence 는 collect-side status 로 남고
    eligible_for_coach 는 False(apply seam 이 measured-eligible 로 라우팅해도 코치 root-cause
    주입 0). to_audit_dict('applied') 는 collectionStatus=low_alignment_confidence 를 보존해
    리포트가 측정-only 감점임을 투명하게 보여준다."""
    assert "low_alignment_confidence" in vision_veto.VISION_FAULT_COLLECTION_STATUSES
    ctx = vision_veto.VisionFaultContext(
        collection_status="low_alignment_confidence", verdict=None,
        supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
        alignment={}, telemetry={}, cap_would_apply=False,
    )
    # candidate_verdict-only 코치 게이트 — low_alignment 은 코치 root-cause 부재.
    assert ctx.eligible_for_coach is False
    quant = vision_veto.VisionQuantificationResult(
        quantificationStatus="available", angleDeltas=None,
        bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=[],
    )
    audit = ctx.to_audit_dict(
        final_status="applied", breakdown_final=62, quantification=quant
    )
    assert audit["status"] == "applied"
    assert audit["collectionStatus"] == "low_alignment_confidence"
    # verdict None → Gemini-located severity/primaryFault 부재(측정-only).
    assert "primaryFault" not in audit


def test_to_audit_dict_requires_final_args():
    """to_audit_dict 는 final_status 인자 받아야 final-audit 필드 방출. 인자 없으면 미방출 (D-12 HIGH-1)."""
    ctx = vision_veto.VisionFaultContext(
        collection_status="candidate_verdict", verdict=_verdict("major"),
        supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
        alignment={}, telemetry={}, cap_would_apply=True,
    )
    quant = vision_veto.VisionQuantificationResult(
        quantificationStatus="unavailable", angleDeltas=None,
        bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=[],
    )
    audit = ctx.to_audit_dict(
        final_status="applied", breakdown_final=50, quantification=quant
    )
    assert audit["status"] == "applied"
    # Phase 24 (밴드 제거): tallyFinal 만 방출, 옛 밴드 필드 부재.
    assert audit["tallyFinal"] == 50
    assert ("cap" + "Applied") not in audit
    assert audit["quantificationStatus"] == "unavailable"
    # 인자 없이 호출 → final-audit 필드 미방출 (fail-fast 또는 생략).
    try:
        bare = ctx.to_audit_dict()
    except TypeError:
        bare = None  # fail-fast 도 허용.
    if bare is not None:
        assert "status" not in bare or bare.get("status") is None


def test_alignment_summary_observation_keys_only():
    """24-06 §3 진단 — alignment_summary 는 빈 dict/None → None, 채워진 dict → 관찰 키만."""
    assert vision_veto.alignment_summary(None) is None
    assert vision_veto.alignment_summary({}) is None
    full = {
        "adoption": "low_alignment_confidence",
        "global_ok": False, "local_ok": False,
        "localPathCount": 0, "refFramePresent": False,
        "visibility": 0.2, "distance": 42.0,
        "selector_version": "v1",
    }
    out = vision_veto.alignment_summary(full)
    assert out == {
        "adoption": "low_alignment_confidence",
        "distance": 42.0,
        "visibility": 0.2,
        "localPathCount": 0,
        "refFramePresent": False,
    }
    # 비-관찰 키(global_ok/local_ok/selector_version)는 제외 — 관찰 전용 메타데이터.
    assert "global_ok" not in out
    assert "selector_version" not in out


def test_to_audit_dict_emits_alignment_both_final_statuses():
    """24-06 §3 진단 — ctx.alignment 존재 시 audit['alignment'] 가 applied/not_applicable
    양쪽에서 방출(관찰 전용, score 불변). low_alignment bail 의 발화 조건을 캡처한다."""
    alignment = {
        "adoption": "low_alignment_confidence",
        "distance": 42.0, "visibility": 0.2,
        "localPathCount": 0, "refFramePresent": False,
    }
    ctx = vision_veto.VisionFaultContext(
        collection_status="low_alignment_confidence", verdict=None,
        supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
        alignment=alignment, telemetry={}, cap_would_apply=False,
    )
    quant = vision_veto.VisionQuantificationResult(
        quantificationStatus="unavailable", angleDeltas=None,
        bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=[],
    )
    applied = ctx.to_audit_dict(
        final_status="applied", breakdown_final=62, quantification=quant
    )
    assert applied["alignment"]["adoption"] == "low_alignment_confidence"
    assert applied["alignment"]["distance"] == 42.0
    assert applied["alignment"]["visibility"] == 0.2
    na = ctx.to_audit_dict(final_status="not_applicable")
    assert na["alignment"]["adoption"] == "low_alignment_confidence"
    assert na["alignment"]["distance"] == 42.0


def test_to_audit_dict_omits_alignment_when_empty():
    """ctx.alignment={} 면 audit 에 'alignment' 키 미방출 (기존 shape 무영향)."""
    ctx = vision_veto.VisionFaultContext(
        collection_status="candidate_verdict", verdict=_verdict("major"),
        supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
        alignment={}, telemetry={}, cap_would_apply=True,
    )
    quant = vision_veto.VisionQuantificationResult(
        quantificationStatus="unavailable", angleDeltas=None,
        bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=[],
    )
    audit = ctx.to_audit_dict(
        final_status="applied", breakdown_final=50, quantification=quant
    )
    assert "alignment" not in audit


def test_to_coach_context_and_trace_dict_standalone():
    """to_coach_context/to_trace_dict 는 ctx 단독 (final 인자 불요, D-12)."""
    fk = vision_veto.FaultKey("upper_body", "left", "arm", "pole_gap_or_bent")
    rc = vision_veto.RootCauseHypothesis(
        text="왼팔: 폴에서 떨어짐", fault_key=fk, source_difference_ids=(1,), support_count=2,
    )
    ctx = vision_veto.VisionFaultContext(
        collection_status="candidate_verdict", verdict=_verdict(),
        supported_differences=[{"body_part": "왼팔", "severity": "moderate", "_faultKey": fk}],
        root_cause_hypotheses=[rc], selected_frame_pairs=[], alignment={"adoption": "single"},
        telemetry={"completedCalls": 3}, cap_would_apply=True,
    )
    coach = ctx.to_coach_context()
    assert "rootCauseHypotheses" in coach
    trace = ctx.to_trace_dict()
    # to_trace_dict 가 FaultKey.to_dict 와 동일 어휘 방출 (D-17 MED-3).
    keys = trace.get("faultKeys") or []
    assert {"part_scope": "upper_body", "side": "left", "keypoint_set": "arm",
            "fault_kind": "pole_gap_or_bent"} in keys


def test_quantification_result_fields():
    """VisionQuantificationResult 가 post-geometry 필드 소유 (D-12 HIGH-1)."""
    import dataclasses

    fields = {f.name for f in dataclasses.fields(vision_veto.VisionQuantificationResult)}
    assert "quantificationStatus" in fields
    assert "angleDeltas" in fields
    assert "bodyRelativeNotches" in fields
    assert "windowMedianAngleDeltas" in fields
    assert "warnings" in fields


def test_selected_frame_pair_fields():
    """SelectedFramePair 가 student/reference frame path + idx + keypoints/conf + cleanup (D-10 HIGH-2)."""
    import dataclasses

    fields = {f.name for f in dataclasses.fields(vision_veto.SelectedFramePair)}
    assert "student_frame_path" in fields
    assert "reference_frame_path" in fields
    assert "user_frame_idx" in fields
    assert "ref_frame_idx" in fields
    assert "student_keypoints" in fields
    assert "reference_keypoints" in fields
    assert "cleanup_paths" in fields


# ─────────────── Task 2 (23-02) — 결정적 칸/층 기하 (FramePairMeasurementContext) ───────────────
#
# 칸은 keypoint + baseline 만으로 코드가 결정적으로 산출한다 (Gemini 미산출, H2). percent
# 표기 0 (D-08 _SCORE_PATTERN 누수). same-frame 강제 (D-09/D-10 HIGH-3).

import numpy as np  # noqa: E402

from sunity_shared.analysis import skeleton  # noqa: E402


def _coco_keypoints(overrides: dict | None = None) -> np.ndarray:
    """기준 COCO-17 keypoints (x,y) — 어깨/엉덩이/손/무릎 배치. overrides 로 일부 교체."""
    kp = np.zeros((skeleton.NUM_KEYPOINTS, 2), dtype=float)
    base = {
        "left_shoulder": (0.40, 0.30),
        "right_shoulder": (0.60, 0.30),
        "left_hip": (0.42, 0.60),
        "right_hip": (0.58, 0.60),
        "left_knee": (0.43, 0.80),
        "right_knee": (0.57, 0.80),
        "left_wrist": (0.35, 0.20),
        "right_wrist": (0.65, 0.20),
        "left_ankle": (0.44, 0.95),
        "right_ankle": (0.56, 0.95),
    }
    if overrides:
        base.update(overrides)
    for name, (x, y) in base.items():
        i = skeleton.kp_index(name)
        kp[i] = (x, y)
    return kp


def test_notches_deterministic_floor_baseline():
    """칸이 keypoint + 바닥 baseline 만으로 결정적 산출 — 같은 입력=같은 칸 (H2, Gemini 부재)."""
    student = _coco_keypoints()
    reference = _coco_keypoints()
    ctx = vision_veto.FramePairMeasurementContext(
        user_frame_idx=3, ref_frame_idx=5,
        student_keypoints=student, reference_keypoints=reference,
        baseline_kind="floor", floor_y=1.0,
    )
    notches1 = vision_veto.body_relative_notches(ctx)
    notches2 = vision_veto.body_relative_notches(ctx)
    assert notches1 is not None and len(notches1) > 0
    # 결정적 — 같은 입력은 같은 칸.
    assert notches1 == notches2
    # 각 항목에 student/reference 칸 + delta + source=geometry.
    for n in notches1:
        assert "student_notches" in n and "reference_notches" in n
        assert "delta_notches" in n
        assert n["source"] == "geometry"


def test_notches_no_percent_only_notches():
    """칸 출력에 % / 100% / percent 문자 0 — 칸(정수/분수) 표기만 (D-08)."""
    student = _coco_keypoints()
    reference = _coco_keypoints({"left_wrist": (0.30, 0.10)})  # 손=손목 proxy
    ctx = vision_veto.FramePairMeasurementContext(
        user_frame_idx=0, ref_frame_idx=0,
        student_keypoints=student, reference_keypoints=reference,
        baseline_kind="floor", floor_y=1.0,
    )
    notches = vision_veto.body_relative_notches(ctx)
    text = repr(notches)
    for forbidden in ("%", "100%", "percent", "퍼센트"):
        assert forbidden not in text, f"칸 출력에 {forbidden!r} 누출 (D-08 _SCORE_PATTERN)"


def test_notches_baseline_branches_by_motion_context():
    """baseline 이 동작 맥락에 따라 floor/pole_vertical/hip_line 으로 분기 (H2)."""
    student = _coco_keypoints()
    reference = _coco_keypoints()
    # floor.
    floor_ctx = vision_veto.FramePairMeasurementContext(
        user_frame_idx=0, ref_frame_idx=0,
        student_keypoints=student, reference_keypoints=reference,
        baseline_kind="floor", floor_y=1.0,
    )
    assert vision_veto.body_relative_notches(floor_ctx) is not None
    # hip_line (엉덩이중점 baseline — pole_line/floor 불요).
    hip_ctx = vision_veto.FramePairMeasurementContext(
        user_frame_idx=0, ref_frame_idx=0,
        student_keypoints=student, reference_keypoints=reference,
        baseline_kind="hip_line",
    )
    assert vision_veto.body_relative_notches(hip_ctx) is not None
    # pole_vertical (image-2D PoleLine2D baseline).
    from sunity_shared.analysis import pole_geometry

    line = pole_geometry.PoleLine2D(
        point_image=(0.5, 0.5), direction_image=(0.0, 1.0),
        confidence=0.9, source="detected",
    )
    pole_ctx = vision_veto.FramePairMeasurementContext(
        user_frame_idx=0, ref_frame_idx=0,
        student_keypoints=student, reference_keypoints=reference,
        baseline_kind="pole_vertical", pole_line=line,
    )
    assert vision_veto.body_relative_notches(pole_ctx) is not None


def test_notches_mismatch_frame_changes_value():
    """다른 ref keypoints(틀린 프레임)면 다른 칸 — same-frame 계약 (D-09/D-10 HIGH-3)."""
    student = _coco_keypoints()
    reference_same = _coco_keypoints()
    reference_diff = _coco_keypoints({"right_knee": (0.57, 0.50)})  # 무릎이 위로 → 다른 reach
    ctx_same = vision_veto.FramePairMeasurementContext(
        user_frame_idx=0, ref_frame_idx=0,
        student_keypoints=student, reference_keypoints=reference_same,
        baseline_kind="floor", floor_y=1.0,
    )
    ctx_diff = vision_veto.FramePairMeasurementContext(
        user_frame_idx=0, ref_frame_idx=0,
        student_keypoints=student, reference_keypoints=reference_diff,
        baseline_kind="floor", floor_y=1.0,
    )
    assert vision_veto.body_relative_notches(ctx_same) != vision_veto.body_relative_notches(ctx_diff)


def test_quantification_result_unavailable_on_missing_inputs():
    """결측 입력 시 crash·강등 없이 VisionQuantificationResult(unavailable) 반환 (D-11 MED-1 + D-12 HIGH-1)."""
    # measurement 자체 None.
    q0 = vision_veto.build_quantification_result(measurement=None)
    assert q0.quantificationStatus == "unavailable"
    assert q0.angleDeltas is None and q0.bodyRelativeNotches is None
    # keypoint 결측 (baseline 있지만 keypoints None).
    ctx = vision_veto.FramePairMeasurementContext(
        user_frame_idx=0, ref_frame_idx=0,
        student_keypoints=None, reference_keypoints=None,
        baseline_kind="floor", floor_y=1.0,
    )
    q1 = vision_veto.build_quantification_result(measurement=ctx)
    assert q1.quantificationStatus == "unavailable"
    assert q1.warnings  # 사유 기록.


def test_quantification_result_available_packs_geometry():
    """available 시 angleDeltas + bodyRelativeNotches 가 VisionQuantificationResult 로 묶임 (D-12 HIGH-1)."""
    student = _coco_keypoints()
    reference = _coco_keypoints()
    ctx = vision_veto.FramePairMeasurementContext(
        user_frame_idx=1, ref_frame_idx=1,
        student_keypoints=student, reference_keypoints=reference,
        baseline_kind="floor", floor_y=1.0,
    )
    # 각도 행렬 (T, NUM_JOINTS) — frame-specific 각도 입력.
    s_ang = np.full((3, skeleton.NUM_JOINTS), 150.0)
    r_ang = np.full((3, skeleton.NUM_JOINTS), 178.0)
    q = vision_veto.build_quantification_result(
        measurement=ctx, student_angles=s_ang, reference_angles=r_ang,
    )
    assert q.quantificationStatus == "available"
    assert q.angleDeltas is not None and len(q.angleDeltas) > 0
    assert q.bodyRelativeNotches is not None and len(q.bodyRelativeNotches) > 0
    # frame-specific 각도 (Task 1) 와 칸 (Task 2) 가 같은 user/ref_frame_idx 를 씀.
    for a in q.angleDeltas:
        assert a["source"] == "geometry"


def test_notches_no_heavy_imports():
    """body_relative_notches 본문에 boto3/google.genai/requests import 0 (순수)."""
    import inspect

    src = inspect.getsource(vision_veto.body_relative_notches)
    src += inspect.getsource(vision_veto._reach_to_baseline)
    src += inspect.getsource(vision_veto._baseline_unit_length)
    for forbidden in ("import boto3", "google.genai", "import requests", "from google"):
        assert forbidden not in src
