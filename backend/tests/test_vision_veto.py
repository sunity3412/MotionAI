"""v2 비전 거부권 순수 코어 단위테스트 (Phase 20-01/20-04, D-01/D-02/D-05 + HIGH-3).

이 모듈은 vision_veto.py 의 안전 성질을 코드로 못 박는다:
  - D-01 하향 전용: apply_downward_cap 은 점수를 절대 올리지 않는다 (위양성 재발 차단).
  - D-02 curve-fit 금지: SEVERITY_CAP 은 6페어에 curve-fit 되지 않는다 — 20-04 는
    spec-anchored(belle 스펙 + IPSF severity 의미) 로 cap 을 박는다. 6페어는 회귀
    검증 전용이며 derive 입력이 절대 아니다 (phase18_pairs_used_for_derivation==False).
  - HIGH-3 fail-closed (method-aware): SEVERITY_CAP_PROVENANCE 가 데이터(주석 아님)로
    박제된다. method=="sensitivity_derived" + cap 채움 → 실 sha 강제. method==
    "spec_anchored" → sha 없이 cap 가능하되 spec_basis 데이터가 출처를 박제.
    어떤 method 든 phase18 6페어 curve-fit 은 영구 fail-closed.
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

_SEVERITIES = (None, "none", "minor", "moderate", "major", "unknown")


def test_downward_only_property():
    """∀ (overall ∈ 0..100, severity) 에 대해 출력 ≤ 입력 (D-01 코어 invariant).

    비전은 점수를 절대 올리지 않는다. None/none/unknown 은 불변 (cap 미적용, 정타 보존).
    minor/moderate/major 는 cap 이 채워져도 min-only 이므로 invariant(≤ 입력)는 절대
    깨지지 않아야 한다 (하향 전용).
    """
    for overall in range(0, 101):
        for severity in _SEVERITIES:
            out = vision_veto.apply_downward_cap(overall, severity)
            assert out <= overall, (
                f"apply_downward_cap({overall}, {severity!r}) = {out} > {overall} "
                "— 비전이 점수를 올렸다 (D-01 위반)"
            )
            # None/none/unknown(미지 키) 만 무캡 — 정타 보존. minor 는 Phase 20 부터
            # 90 cap 이 붙으므로 무캡 목록에서 제외.
            if severity in (None, "none", "unknown"):
                assert out == overall, (
                    f"severity={severity!r} 는 점수를 깎으면 안 된다 (정타 보존)"
                )


def test_none_no_cap():
    """none / None / 미지 severity → 입력 그대로 (정타 95~100 보존, D-01).

    Phase 20: 무캡은 'none'(정타) 와 None/미지 키 뿐. minor 는 90 cap 으로 이동.
    """
    for overall in (95, 96, 97, 98, 99, 100):
        assert vision_veto.apply_downward_cap(overall, "none") == overall
        assert vision_veto.apply_downward_cap(overall, None) == overall
        assert vision_veto.apply_downward_cap(overall, "does_not_exist") == overall
    # none cap 은 미적용(None) — 정타 무캡 보존.
    assert vision_veto.SEVERITY_CAP["none"] is None


def test_minor_caps_at_90():
    """minor → 90 cap (Phase 20 robustify — 미세하지만 실재하는 결함 천장 해제).

    100 → 90 으로 내려가지만, 90 미만 입력은 더 내려가지 않는다 (min-only).
    정타(none)는 무캡으로 100 보존 — minor 와 none 의 차이를 명시 박제.
    """
    assert vision_veto.SEVERITY_CAP["minor"] == 90
    assert vision_veto.apply_downward_cap(100, "minor") == 90
    assert vision_veto.apply_downward_cap(95, "minor") == 90
    assert vision_veto.apply_downward_cap(90, "minor") == 90
    assert vision_veto.apply_downward_cap(85, "minor") == 85  # cap 미만 불변 (min-only)
    # 대조 — 정타(none)는 여전히 무캡 → 100 보존.
    assert vision_veto.apply_downward_cap(100, "none") == 100


def test_cap_lowers_for_major():
    """major cap=50, moderate cap=75 으로 spec-anchored 확정 (20-04, belle 스펙).

    major → overall=100 이 50 으로 내려간다 (belle 스펙 "잘못된 동작 ≤50").
    moderate → overall=100 이 75 로 내려간다 (IPSF moderate-fault 원칙적 상한).
    cap 보다 낮은 입력은 더 내려가지 않는다 (min-only). cap 수치가 미래에 바뀌어도
    min 동작 자체는 불변이어야 하므로 수치 단언과 min 동작 단언을 함께 둔다.
    """
    # spec-anchored 확정값 단언 (20-04).
    assert vision_veto.SEVERITY_CAP["major"] == 50
    assert vision_veto.SEVERITY_CAP["moderate"] == 75

    # major: 100 → 50, 그리고 cap 미만 입력은 불변 (min-only).
    assert vision_veto.apply_downward_cap(100, "major") == 50
    assert vision_veto.apply_downward_cap(49, "major") == 49
    assert vision_veto.apply_downward_cap(50, "major") == 50

    # moderate: 100 → 75, 그리고 cap 미만 입력은 불변 (min-only).
    assert vision_veto.apply_downward_cap(100, "moderate") == 75
    assert vision_veto.apply_downward_cap(74, "moderate") == 74
    assert vision_veto.apply_downward_cap(75, "moderate") == 75


def test_severity_cap_no_curve_fit_marker():
    """cap 이 채워졌으면 출처가 데이터로 박제되고 6페어 curve-fit 이 아님 (D-02 가드).

    spec_anchored 모드: spec_basis 가 cap 근거(belle 스펙)를 데이터로 박제하고,
    phase18 6페어는 derive 입력이 아니다. sensitivity_derived 모드: source 가
    phase20 sensitivity 출처여야 한다. 어떤 경우든 6페어 curve-fit 은 금지.
    """
    moderate = vision_veto.SEVERITY_CAP["moderate"]
    major = vision_veto.SEVERITY_CAP["major"]
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    method = prov.get("method")
    cap_filled = moderate is not None or major is not None

    if cap_filled:
        # 6페어 curve-fit 은 어떤 method 든 영구 금지.
        assert prov.get("phase18_pairs_used_for_derivation") is False, (
            "cap 이 채워졌는데 phase18 6페어를 derive 입력으로 썼다 (curve-fit, D-02)"
        )
        if method == "spec_anchored":
            spec_basis = prov.get("spec_basis")
            assert isinstance(spec_basis, str) and spec_basis.strip(), (
                "spec_anchored 모드에서 cap 이 채워졌다면 spec_basis 가 출처를 "
                "데이터로 박제해야 한다 (주석 아님, D-02)"
            )
        elif method == "sensitivity_derived":
            assert prov.get("source") == "phase20_sensitivity", (
                "sensitivity_derived 모드 cap 의 source 는 phase20_sensitivity 여야 한다"
            )
        else:
            raise AssertionError(
                f"cap 이 채워졌는데 provenance.method 가 미지값이다: {method!r}"
            )


def test_provenance_is_data_not_comment():
    """SEVERITY_CAP_PROVENANCE 가 module dict(주석 아님)로 존재 (HIGH-3).

    주석 grep 이 아니라 import 한 dict 를 직접 검사한다. method/spec_basis 포함.
    """
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    assert isinstance(prov, dict)
    assert {
        "method",
        "source",
        "spec_basis",
        "sensitivity_manifest_sha256",
        "phase18_pairs_used_for_derivation",
    } <= set(prov.keys())
    assert prov["method"] in ("spec_anchored", "sensitivity_derived")
    # spec_anchored(현재) → spec_basis 가 belle 스펙 출처를 데이터로 박제.
    if prov["method"] == "spec_anchored":
        assert isinstance(prov["spec_basis"], str)
        assert "≤50" in prov["spec_basis"], (
            "spec_basis 가 belle 스펙 '잘못된 동작 ≤50' 출처를 명시해야 한다"
        )
    # 6페어는 회귀 검증 전용 — derive 입력 아님. 영구 False (INVARIANT).
    assert prov["phase18_pairs_used_for_derivation"] is False


def test_phase18_pairs_never_derivation_input():
    """6 deliberate-fault 페어는 영구히 derive 입력이 아니다 (INVARIANT, 어떤 method 든).

    6페어는 known-answer 회귀 게이트 전용. cap 활성화 모드와 무관하게 이 값은
    영구 False — True 가 되면 단일 선수 curve-fit 으로 일반화가 깨진다 (D-02).
    """
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    assert prov["phase18_pairs_used_for_derivation"] is False


def test_cap_fill_requires_real_manifest_sha():
    """method-aware fail-closed: sensitivity_derived cap 은 실 sha 강제 (HIGH-3).

    - method=="sensitivity_derived" + cap 채움 → sensitivity_manifest_sha256 가
      실 sha 여야 한다 (TODO/None 금지). 원래 HIGH-3 fail-closed 보존.
    - method=="spec_anchored" → cap 을 sha 없이 채울 수 있되, spec_basis 가
      반드시 존재하고 phase18 6페어가 derive 입력이 아니어야 한다.
    어떤 method 든 6페어 curve-fit 은 영구 fail-closed.
    """
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    method = prov.get("method")
    sha = prov.get("sensitivity_manifest_sha256")
    sha_is_real = isinstance(sha, str) and sha not in ("", "TODO")
    cap_filled = any(
        vision_veto.SEVERITY_CAP[k] is not None for k in ("moderate", "major")
    )

    # 6페어 curve-fit 은 모든 경로에서 금지 (method 불문).
    assert prov.get("phase18_pairs_used_for_derivation") is False, (
        "phase18 6페어가 derive 입력으로 표시됨 — curve-fit fail-closed 위반"
    )

    if not cap_filled:
        return

    if method == "sensitivity_derived":
        assert sha_is_real, (
            "sensitivity_derived cap 이 채워졌는데 sensitivity_manifest_sha256 가 "
            f"실 sha 가 아니다 (sha={sha!r}) — curve-fit fail-closed 위반 (HIGH-3)"
        )
    elif method == "spec_anchored":
        spec_basis = prov.get("spec_basis")
        assert isinstance(spec_basis, str) and spec_basis.strip(), (
            "spec_anchored cap 이 채워졌는데 spec_basis 가 없다 — 출처 박제 위반"
        )
    else:
        raise AssertionError(
            f"cap 이 채워졌는데 provenance.method 가 미지값이다: {method!r}"
        )


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
    audit = ctx.to_audit_dict(final_status="applied", cap_applied=50, quantification=quant)
    assert audit["status"] == "applied"
    assert audit["capApplied"] == 50
    assert audit["quantificationStatus"] == "unavailable"
    # 인자 없이 호출 → final-audit 필드 미방출 (fail-fast 또는 생략).
    try:
        bare = ctx.to_audit_dict()
    except TypeError:
        bare = None  # fail-fast 도 허용.
    if bare is not None:
        assert "status" not in bare or bare.get("status") is None


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
