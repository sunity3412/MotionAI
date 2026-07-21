"""Plan 32-06 Task 1 — 미션 엔진 순수 함수 단위 테스트 (D-19/D-26/D-27/D-14).

행동 명세 (32-06-PLAN behavior 8건 + 설계 확정 엣지):
  1. faultKey — motionId+ruleId+criterion 결정적 문자열, 좌/우 관절 구분 승계
     (리뷰 blocker 1 — criterion 단독 판별은 좌우·동작을 병합)
  2. 우선순위 ① 안전 — selectedBy='safety' + isSafety + streak 1 고정 +
     escalation 'none' 강제 (D-14 미션화·게임 금지 + D-19 ① 안전 안내 우선 정합)
  3. 우선순위 ② 반복 — 동일 faultKey 잔존 시 streak+1, prev motionId 불일치 시
     체인 리셋 (get_previous_analysis 가 motion 미필터인 실측 사실의 순수 함수 방어)
  4. 우선순위 ③ 감점 최대 (records |points| 최대)
  5. baseline 저장 — 다음 분석의 개선량 계산 재료 (D-26, 리뷰 blocker 1)
  6. 에스컬레이션 — 2회차 exercise_detour / 3회차+ coach_card (D-27)
  7. outcome 수치 — 소멸/감소/증가/None 조건. 사람 문장 필드 0 (책임 분리)
  8. flat scalar + camelCase 키 ([[firestore-nested-array-flat]])
"""

from __future__ import annotations

from sunity_shared.analysis import mission

# ── 헬퍼 — 실계약 형상 재현 (DeductionRecord 11키 / SafetyFlag 7키) ──────────


def _rec(
    criterion: str = "angle_vs_reference__left_knee",
    rule_id: str = "angle_vs_reference_over_tol_linear",
    points: float = -8.0,
    measured: float | None = 141.0,
    target: float | None = 180.0,
    unit: str = "deg",
    record_id: str | None = None,
) -> dict:
    rec = {
        "criterion": criterion,
        "measuredValue": measured,
        "baselineValue": target,
        "baselineKind": None,
        "deviation": (
            abs(target - measured)
            if measured is not None and target is not None
            else 0.0
        ),
        "ruleId": rule_id,
        "points": points,
        "unit": unit,
        "ipsfAnchor": "IPSF CoP Page 9",
        "source": "geometry",
        "deviationSource": "ipsf_absolute",
    }
    if record_id is not None:
        rec["recordId"] = record_id
    return rec


def _safety_flag(flag_type: str = "trunk_hyperextension") -> dict:
    return {
        "flagType": flag_type,
        "bodyRegion": "trunk",
        "severity": "high",
        "confidence": "high",
        "modeScope": "both",
        "postureCondition": "hold",
        "controlLossSignal": "none",
    }


def _prev(
    fault_key: str,
    streak: int = 1,
    motion_id: str = "kip-up",
    baseline_points: float = 8.0,
    baseline_deviation: float | None = 39.0,
    criterion: str = "angle_vs_reference__left_knee",
    is_safety: bool = False,
) -> dict:
    return {
        "faultKey": fault_key,
        "criterion": criterion,
        "ruleId": "angle_vs_reference_over_tol_linear",
        "recordId": None,
        "selectedBy": "safety" if is_safety else "max_deduction",
        "streak": streak,
        "isSafety": is_safety,
        "escalation": "none",
        "motionId": motion_id,
        "baselinePoints": baseline_points,
        "baselineDeviation": baseline_deviation,
        "targetValue": 180.0,
        "unit": "deg",
    }


# ── Test 1: faultKey ─────────────────────────────────────────────────────────


def test_fault_key_deterministic() -> None:
    fk = mission.build_fault_key(
        "kip-up", "ipsf_absolute", "angle_vs_reference__left_knee"
    )
    assert fk == "kip-up::ipsf_absolute::angle_vs_reference__left_knee"


def test_fault_key_side_joints_distinct() -> None:
    left = mission.build_fault_key("kip-up", "r", "angle_vs_reference__left_knee")
    right = mission.build_fault_key("kip-up", "r", "angle_vs_reference__right_knee")
    assert left != right


def test_fault_key_none_fallbacks() -> None:
    assert mission.build_fault_key(None, None, "line") == "unknown::na::line"


# ── Test 2: 우선순위 ① 안전 (D-14 정합) ─────────────────────────────────────


def test_safety_priority_overrides_repeat_and_max() -> None:
    rec = _rec(points=-12.0)
    prev_fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    prev = _prev(prev_fk, streak=4)
    m = mission.select_mission([rec], [_safety_flag()], prev, "kip-up")
    assert m["selectedBy"] == "safety"
    assert m["isSafety"] is True
    assert m["streak"] == 1  # D-14 — 게임·streak 제외 (고정)
    assert m["escalation"] == "none"  # D-14 — 에스컬레이션 강제 제외
    assert m["criterion"] == "trunk_hyperextension"
    assert m["motionId"] == "kip-up"


# ── Test 3: 우선순위 ② 반복 미개선 + motionId 가드 ─────────────────────────


def test_repeat_priority_increments_streak() -> None:
    rec = _rec(points=-6.0)
    fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    m = mission.select_mission([rec], None, _prev(fk, streak=1), "kip-up")
    assert m["selectedBy"] == "repeat"
    assert m["streak"] == 2
    assert m["faultKey"] == fk


def test_repeat_motion_mismatch_resets_chain() -> None:
    rec = _rec(points=-6.0)
    fk_other = mission.build_fault_key("shoulder-mount", rec["ruleId"], rec["criterion"])
    prev = _prev(fk_other, streak=3, motion_id="shoulder-mount")
    m = mission.select_mission([rec], None, prev, "kip-up")
    assert m["selectedBy"] == "max_deduction"  # 다른 동작 체인 오염 0
    assert m["streak"] == 1


# ── Test 4: 우선순위 ③ 감점 최대 ────────────────────────────────────────────


def test_max_deduction_priority_picks_largest() -> None:
    small = _rec(criterion="angle_vs_reference__left_elbow", points=-3.0)
    big = _rec(criterion="angle_vs_reference__right_knee", points=-15.5)
    m = mission.select_mission([small, big], None, None, "kip-up")
    assert m["selectedBy"] == "max_deduction"
    assert m["criterion"] == "angle_vs_reference__right_knee"
    assert m["baselinePoints"] == 15.5
    assert m["streak"] == 1


# ── Test 5: baseline 저장 (D-26 계산 가능성) ────────────────────────────────


def test_baseline_fields_saved_for_next_analysis() -> None:
    rec = _rec(
        points=-8.0,
        measured=141.0,
        target=180.0,
        record_id="r00:angle_vs_reference__left_knee",
    )
    m = mission.select_mission([rec], None, None, "kip-up")
    assert m["baselinePoints"] == 8.0
    assert m["baselineDeviation"] == 39.0
    assert m["targetValue"] == 180.0
    assert m["unit"] == "deg"
    assert m["motionId"] == "kip-up"
    assert m["recordId"] == "r00:angle_vs_reference__left_knee"


def test_baseline_deviation_none_when_measured_missing() -> None:
    m = mission.select_mission([_rec(measured=None)], None, None, "kip-up")
    assert m["baselineDeviation"] is None
    assert m["recordId"] is None  # record 에 recordId 부재 시 None


def test_mission_keys_exact() -> None:
    m = mission.select_mission([_rec()], None, None, "kip-up")
    assert set(m) == {
        "faultKey", "criterion", "ruleId", "recordId", "selectedBy", "streak",
        "isSafety", "escalation", "motionId", "baselinePoints",
        "baselineDeviation", "targetValue", "unit",
    }


# ── Test 6: 에스컬레이션 (D-27) ─────────────────────────────────────────────


def test_escalation_second_round_exercise_detour() -> None:
    rec = _rec()
    fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    m = mission.select_mission([rec], None, _prev(fk, streak=1), "kip-up")
    assert m["streak"] == 2
    assert m["escalation"] == "exercise_detour"


def test_escalation_third_round_coach_card() -> None:
    rec = _rec()
    fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    m3 = mission.select_mission([rec], None, _prev(fk, streak=2), "kip-up")
    assert m3["streak"] == 3
    assert m3["escalation"] == "coach_card"
    m4 = mission.select_mission([rec], None, _prev(fk, streak=3), "kip-up")
    assert m4["streak"] == 4
    assert m4["escalation"] == "coach_card"


def test_escalation_streak_cap_99() -> None:
    rec = _rec()
    fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    m = mission.select_mission([rec], None, _prev(fk, streak=99), "kip-up")
    assert m["streak"] == 99  # firestore_admin streak 1..99 상한 lockstep


# ── Test 7: outcome 수치 (D-26) ─────────────────────────────────────────────


def test_outcome_fault_resolved() -> None:
    prev_fk = mission.build_fault_key(
        "kip-up", "angle_vs_reference_over_tol_linear", "angle_vs_reference__left_knee"
    )
    prev = _prev(prev_fk, baseline_points=8.0)
    other = _rec(criterion="angle_vs_reference__left_elbow", points=-2.0)
    out = mission.derive_mission_outcome(prev, [other], "mode3", "kip-up")
    assert out["improved"] is True
    assert out["currentPoints"] == 0.0
    assert out["deltaPoints"] == 8.0
    assert out["faultKey"] == prev_fk


def test_outcome_fault_reduced() -> None:
    rec = _rec(points=-5.0, measured=160.0, target=180.0)
    prev_fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    prev = _prev(prev_fk, baseline_points=8.0, baseline_deviation=39.0)
    out = mission.derive_mission_outcome(prev, [rec], "mode3", "kip-up")
    assert out["improved"] is True
    assert out["currentPoints"] == 5.0
    assert out["deltaPoints"] == 3.0
    assert out["currentDeviation"] == 20.0
    assert out["deltaDeviation"] == 19.0


def test_outcome_not_improved_when_equal_or_worse() -> None:
    rec_same = _rec(points=-8.0)
    prev_fk = mission.build_fault_key("kip-up", rec_same["ruleId"], rec_same["criterion"])
    prev = _prev(prev_fk, baseline_points=8.0)
    out = mission.derive_mission_outcome(prev, [rec_same], "mode3", "kip-up")
    assert out["improved"] is False
    out2 = mission.derive_mission_outcome(prev, [_rec(points=-11.0)], "mode3", "kip-up")
    assert out2["improved"] is False
    assert out2["deltaPoints"] == -3.0  # 악화 = 음수 델타 (수치 진실 그대로)


def test_outcome_none_conditions() -> None:
    rec = _rec()
    prev_fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    prev = _prev(prev_fk)
    assert mission.derive_mission_outcome(None, [rec], "mode3", "kip-up") is None
    assert mission.derive_mission_outcome(prev, [rec], "mode1", "kip-up") is None
    assert (
        mission.derive_mission_outcome(prev, [rec], "mode3", "shoulder-mount") is None
    )


def test_outcome_none_for_safety_prev() -> None:
    # D-14 — 안전 미션은 게임·개선 추적 제외 (안내 전용). baseline 0 인 안전
    # 미션의 '소멸=개선' 은 공허한 칭찬이라 outcome 자체를 만들지 않는다.
    prev = _prev(
        "kip-up::na::trunk_hyperextension",
        is_safety=True,
        baseline_points=0.0,
        criterion="trunk_hyperextension",
    )
    assert mission.derive_mission_outcome(prev, [], "mode3", "kip-up") is None


def test_outcome_none_when_prev_baseline_missing() -> None:
    # 리뷰 blocker 1 — baseline 없는 prev(legacy)는 개선량 계산 불가 → None.
    rec = _rec()
    prev_fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    prev = _prev(prev_fk)
    del prev["baselinePoints"]
    assert mission.derive_mission_outcome(prev, [rec], "mode3", "kip-up") is None


def test_outcome_numeric_only_no_sentence_fields() -> None:
    rec = _rec(points=-5.0)
    prev_fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    out = mission.derive_mission_outcome(_prev(prev_fk), [rec], "mode3", "kip-up")
    expected = {
        "improved", "faultKey", "criterion", "baselinePoints", "currentPoints",
        "deltaPoints", "baselineDeviation", "currentDeviation", "deltaDeviation",
    }
    assert set(out) == expected  # 사람 문장 필드 0 — 수치·enum·키만


# ── Test 8: flat scalar + camelCase ─────────────────────────────────────────


def _assert_flat_camel(d: dict) -> None:
    for key, value in d.items():
        assert isinstance(key, str) and "_" not in key, f"camelCase 위반 키: {key}"
        assert not isinstance(value, (list, dict, tuple)), f"nested 값 금지: {key}"
        assert value is None or isinstance(value, (str, int, float, bool))


def test_mission_and_outcome_flat_scalar_camel_case() -> None:
    rec = _rec(points=-5.0)
    fk = mission.build_fault_key("kip-up", rec["ruleId"], rec["criterion"])
    _assert_flat_camel(mission.select_mission([rec], None, _prev(fk, streak=2), "kip-up"))
    _assert_flat_camel(
        mission.derive_mission_outcome(_prev(fk), [rec], "mode3", "kip-up")
    )
    _assert_flat_camel(mission.select_mission([], [_safety_flag()], None, "kip-up"))


# ── 설계 확정 엣지 — 결함 0 이면 미션 fabrication 금지 ──────────────────────


def test_select_mission_none_when_clean() -> None:
    assert mission.select_mission([], None, None, "kip-up") is None
    assert mission.select_mission(None, None, None, "kip-up") is None
    # 0 감점 record 는 결함이 아님 — 미션 후보 제외 (fabrication 금지).
    assert mission.select_mission([_rec(points=0.0)], None, None, "kip-up") is None
