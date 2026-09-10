"""감점 부위 → 보완 운동 종류 배선 (quick-260910-pbs Task 2).

belle 2026-09-10: "분석마다 다른 개수 다른 **종류**가 될 수도 있지."

착수 전 실측(대표 doc c64afae6, ref-pdshape, 감점 6건): 팔꿈치 −15.1/−10.7, 어깨
−6.7, 엉덩이 −4.0, 무릎 −7.8/−6.7 을 갖고도 보완 운동은 어깨 5개뿐이었다. 감점
record 의 관절이 운동 선정에 **전혀 들어가지 않았기 때문**이다.

여기서 검증하는 것 둘:
  (1) pipeline._deduction_keypoint_sets — record criterion 을 부위 어휘로 접고
      감점 큰 순으로 정렬. 새 어휘를 만들지 않고 vision_veto.match_keypoint_set 를
      쓴다(어휘 단일 owner).
  (2) exercise_map.map_exercises(deduction_keypoint_sets=...) — 그 부위가 운동
      종류·순서에 실제로 반영된다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

import app  # noqa: E402

from sunity_shared.analysis import vision_veto  # noqa: E402
from sunity_shared.analysis.exercise_map import map_exercises  # noqa: E402


def _rec(criterion: str, points: float) -> dict:
    return {"criterion": criterion, "points": points, "ruleId": "x"}


# ── (1) record → 부위 어휘 접기 ───────────────────────────────────────────────


def test_angle_criterion_folds_to_body_part_vocabulary() -> None:
    """`angle_vs_reference__{jk}` 는 관절명만 떼어 기존 어휘로 접힌다."""
    got = app._deduction_keypoint_sets(
        {
            "records": [
                _rec("angle_vs_reference__left_knee", -8.0),
                _rec("angle_vs_reference__left_elbow", -5.0),
                _rec("angle_vs_reference__right_shoulder", -3.0),
                _rec("angle_vs_reference__left_hip", -1.0),
            ]
        }
    )
    assert got == ["leg", "arm", "shoulder", "hip"]


def test_split_angle_criterion_folds_via_existing_leg_keyword() -> None:
    """비-각도 criterion 은 id 자체를 조회 — leg 행의 'split' 키워드가 이미 그 용도."""
    assert app._deduction_keypoint_sets({"records": [_rec("split_angle", -12.0)]}) == [
        "leg"
    ]


def test_ordered_by_total_deduction_desc() -> None:
    """부위별 |points| 합 내림차순 — 감점이 큰 부위가 앞에 온다."""
    got = app._deduction_keypoint_sets(
        {
            "records": [
                _rec("angle_vs_reference__right_shoulder", -6.7),
                _rec("angle_vs_reference__left_elbow", -15.1),
                _rec("angle_vs_reference__right_elbow", -10.7),
                _rec("angle_vs_reference__left_knee", -7.8),
                _rec("angle_vs_reference__right_knee", -6.7),
                _rec("angle_vs_reference__left_hip", -4.0),
            ]
        }
    )
    # arm 25.8 > leg 14.5 > shoulder 6.7 > hip 4.0 (대표 doc c64afae6 실측 입력).
    assert got == ["arm", "leg", "shoulder", "hip"]


def test_unknown_criterion_is_dropped_not_defaulted_to_torso() -> None:
    """어휘가 못 알아본 criterion 은 버린다 — 'torso' 기본값이면 근거 없는 코어 운동."""
    assert app._deduction_keypoint_sets({"records": [_rec("mystery_metric", -9.0)]}) is None
    assert vision_veto.match_keypoint_set("mystery_metric") is None
    # 기존 FaultKey 집계 경로의 기본값은 그대로 'torso' (회귀 가드).
    assert vision_veto._keypoint_set_for("mystery_metric") == "torso"


def test_no_records_returns_none() -> None:
    """감점 0건 / breakdown 부재 → None (기존 경로 byte-동등)."""
    assert app._deduction_keypoint_sets(None) is None
    assert app._deduction_keypoint_sets({}) is None
    assert app._deduction_keypoint_sets({"records": []}) is None


def test_malformed_records_are_graceful() -> None:
    """비-dict / criterion 부재 / points 비수치 → 크래시 0."""
    got = app._deduction_keypoint_sets(
        {
            "records": [
                "not a dict",
                {"points": -3.0},
                {"criterion": "", "points": -3.0},
                {"criterion": "angle_vs_reference__left_knee", "points": None},
            ]
        }
    )
    assert got == ["leg"]


def test_collapse_gate_removes_the_part_because_record_is_gone() -> None:
    """붕괴 게이트(quick-260910-ovo)와의 결합 — 판정 불가 관절은 record 자체가 없다.

    record 가 빠지면 그 부위 운동도 자동으로 사라진다. 별도 처리가 필요 없다는 것을
    박제한다 (근거 없는 감점에서 나온 운동은 근거가 없다).
    """
    with_knee = app._deduction_keypoint_sets(
        {
            "records": [
                _rec("angle_vs_reference__left_shoulder", -9.0),
                _rec("angle_vs_reference__left_knee", -8.0),
            ]
        }
    )
    without_knee = app._deduction_keypoint_sets(
        {"records": [_rec("angle_vs_reference__left_shoulder", -9.0)]}
    )
    assert with_knee == ["shoulder", "leg"]
    assert without_knee == ["shoulder"]
    knee_names = {e["name"] for e in map_exercises(
        None, pain_areas=[], motion_id=None, deduction_keypoint_sets=with_knee
    )}
    no_knee_names = {e["name"] for e in map_exercises(
        None, pain_areas=[], motion_id=None, deduction_keypoint_sets=without_knee
    )}
    assert "허벅지 뒤 스트레칭" in knee_names
    assert "허벅지 뒤 스트레칭" not in no_knee_names


# ── (2) 부위가 운동 종류에 반영되는가 ─────────────────────────────────────────


def test_representative_doc_gets_leg_exercises_not_only_shoulder() -> None:
    """대표 doc c64afae6 재현 — 종전엔 어깨 5개뿐이었다."""
    deduction_sets = app._deduction_keypoint_sets(
        {
            "records": [
                _rec("angle_vs_reference__left_elbow", -15.1),
                _rec("angle_vs_reference__right_elbow", -10.7),
                _rec("angle_vs_reference__right_shoulder", -6.7),
                _rec("angle_vs_reference__left_hip", -4.0),
                _rec("angle_vs_reference__left_knee", -7.8),
                _rec("angle_vs_reference__right_knee", -6.7),
            ]
        }
    )
    names = [
        e["name"]
        for e in map_exercises(
            {"findings": [{"sourceSignal": "high_jerk", "jointHint": None}]},
            pain_areas=[],
            motion_id=None,
            deduction_keypoint_sets=deduction_sets,
        )
    ]
    assert names == ["팔굽혀펴기", "허벅지 뒤 스트레칭", "스쿼트", "옆으로 다리 들기"]
    # 무릎(leg) 계열이 실제로 들어왔다 — 어깨 일색이 아니다.
    assert {"허벅지 뒤 스트레칭", "스쿼트"} <= set(names)


def test_deduction_parts_lead_over_vision_fault_parts() -> None:
    """감점 record 부위가 vision faultKey 부위보다 앞선다 (점수를 깎은 쪽이 1순위)."""
    names = [
        e["name"]
        for e in map_exercises(
            None,
            pain_areas=[],
            motion_id=None,
            fault_keypoint_sets=["grip"],
            deduction_keypoint_sets=["leg"],
        )
    ]
    assert names[0] in {"허벅지 뒤 스트레칭", "스쿼트"}
    # vision fault 유래 운동은 제거되지 않고 후순위 유지.
    assert "파머스 워크" in names


def test_deduction_sets_none_is_byte_identical() -> None:
    """deduction_keypoint_sets=None → 기존 결과와 동일 (회귀 가드)."""
    base = map_exercises(
        None, pain_areas=["wrist"], motion_id=None, fault_keypoint_sets=["leg"]
    )
    explicit = map_exercises(
        None,
        pain_areas=["wrist"],
        motion_id=None,
        fault_keypoint_sets=["leg"],
        deduction_keypoint_sets=None,
    )
    assert base == explicit


def test_defect_not_duplicated_across_sources() -> None:
    """같은 defect 가 감점/fault/findings 어디서 와도 운동은 한 번만."""
    result = map_exercises(
        {"findings": [{"sourceSignal": "late_contact", "jointHint": "손목"}]},
        pain_areas=[],
        motion_id=None,
        fault_keypoint_sets=["leg"],
        deduction_keypoint_sets=["leg"],
    )
    names = [e["name"] for e in result]
    assert len(names) == len(set(names))
    assert names.count("허벅지 뒤 스트레칭") == 1
