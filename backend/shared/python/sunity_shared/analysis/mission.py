"""미션 루프 엔진 — 선정 규칙·faultKey·streak 체인·에스컬레이션·수치 outcome.

Phase 32 Plan 32-06 (32-CONTEXT 결정 인용):
  D-19 미션 선정 우선순위 — ① 위험 결함(안전 안내 우선) > ② 반복 미개선 결함
      (mode3 이력, belle "지속적으로 안 고쳐지는 부분") > ③ 감점 최대 결함.
  D-26 지난 미션 피드백 — mission 에 baseline 측정값(baselinePoints/
      baselineDeviation/targetValue/unit/motionId)을 저장해 다음 분석이
      개선량을 계산한다 (리뷰 blocker 1 해소).
  D-27 에스컬레이션 — streak 2회차 = 보완 운동 우회(exercise_detour),
      3회차+ = 코치 카드 전면 승격(coach_card).
  D-14 정합 각주 — **안전은 미션 선정 1순위 자리를 차지하되 게임·streak·
      에스컬레이션에서 제외된다: streak 1 고정 + escalation 'none' 강제.**
      안내와 코치 유도만 한다 (미션화·게임 금지). 같은 이유로 안전 미션은
      derive_mission_outcome 의 개선 추적 대상도 아니다 (baseline 0 의
      '소멸=개선' 은 공허한 칭찬 — D-06 근거 없는 칭찬 금지 정합).

faultKey 설계 (리뷰 blocker 1): criterion 단독 판별은 좌우 관절·동작을 병합하므로
motionId + ruleId + criterion 의 결정적 조합으로 동일 결함을 판별한다. criterion 이
관절·좌우를 내장하는 `angle_vs_reference__{joint}` 형태라 좌우 구분이 faultKey 에
그대로 승계된다.

motionId 가드: `firestore_admin.get_previous_analysis` 는 같은 mode 만 in-memory
필터하고 **motion 은 필터하지 않는다** (실측 확인). 본 모듈은 그 호출을 하지 않고
prev_mission dict 를 인자로 받되, `prev_mission.motionId != 현재 motion_id` 면
prev 를 무시(streak 리셋)해 다른 동작 간 체인 오염을 순수 함수 안에서 차단한다.

순수성 (exercise_map.py 패턴 정합 — Layer 2 boto3 영구 차단):
  - numpy/AWS-free, network-free. 단위 test 로 전부 검증.
  - 입력은 plain dict / list[dict] / str|None, 출력은 plain camelCase scalar dict
    (nested array/dict 0 — [[firestore-nested-array-flat]]).
  - **사람 문장 생성 0** — cueText/deltaSummary 류 문장은 phrasebook(32-05)·
    32-09 조립·앱 렌더 소관 (계산/카피 책임 분리, 리뷰 반영).

3-way lockstep: models.MISSION_KEYS / MISSION_OUTCOME_KEYS ↔
app/src/types/analysis.ts Mission/MissionOutcome ↔ docs/contract.md §12.
"""

from __future__ import annotations

import math

from .. import models

# streak 상한 — firestore_admin._validate_mission 의 1..99 검증과 lockstep.
_STREAK_CAP = 99

# 개선 판정 부동소수 여유 — currentPoints < baselinePoints - _EPS 일 때만 개선.
_IMPROVE_EPS = 0.01

# 안전 미션 폴백 criterion — safetyFlags 항목이 malformed(flagType 부재)여도
# 안전 우선순위 자체는 유지한다 (graceful, fail-open 방향은 '안내').
_SAFETY_FALLBACK_CRITERION = "safety"


def build_fault_key(
    motion_id: str | None, rule_id: str | None, criterion: str
) -> str:
    """안정 faultKey — `{motionId}::{ruleId}::{criterion}` 결정적 문자열.

    좌우 관절 구분은 criterion(`angle_vs_reference__left_knee` 형태)이 내장하므로
    faultKey 에 승계된다 (리뷰 blocker 1). motion/rule 부재는 'unknown'/'na' 로
    고정 폴백 — 같은 입력이면 언제나 같은 키 (조인·streak 판별 안정성).
    """
    return f"{motion_id or 'unknown'}::{rule_id or 'na'}::{criterion}"


def _is_finite_number(value) -> bool:  # noqa: ANN001
    """bool 제외 유한 숫자 판정 (Firestore scalar 방어)."""
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _fault_candidates(
    deduction_records: list | None, motion_id: str | None
) -> list[tuple[str, dict, float]]:
    """실감점 record 만 후보로 — (faultKey, record, abs_points) 목록.

    |points| == 0 record 는 결함이 아니므로 제외 (미션 fabrication 금지).
    malformed 항목(비-dict/criterion 부재/points 비수치)은 조용히 skip
    (graceful — exercise_map 관례).
    """
    out: list[tuple[str, dict, float]] = []
    for rec in deduction_records or []:
        if not isinstance(rec, dict):
            continue
        criterion = rec.get("criterion")
        if not isinstance(criterion, str) or not criterion:
            continue
        points = rec.get("points")
        if not _is_finite_number(points):
            continue
        abs_points = abs(float(points))
        if abs_points <= 0.0:
            continue
        rule_id = rec.get("ruleId")
        fault_key = build_fault_key(
            motion_id, rule_id if isinstance(rule_id, str) else None, criterion
        )
        out.append((fault_key, rec, abs_points))
    return out


def _record_deviation(rec: dict) -> float | None:
    """|measuredValue − baselineValue| — 둘 다 유한 숫자일 때만, 아니면 None."""
    measured = rec.get("measuredValue")
    target = rec.get("baselineValue")
    if _is_finite_number(measured) and _is_finite_number(target):
        return round(abs(float(measured) - float(target)), 2)
    return None


def _escalation_for(streak: int, is_safety: bool) -> str:
    """D-27 에스컬레이션 사다리. isSafety 는 항상 'none' (D-14)."""
    if is_safety:
        return "none"
    if streak >= 3:
        return "coach_card"
    if streak == 2:
        return "exercise_detour"
    return "none"


def _mission_from_record(
    fault_key: str,
    rec: dict,
    abs_points: float,
    *,
    selected_by: str,
    streak: int,
    motion_id: str | None,
) -> dict:
    """선정 record → 미션 dict (MISSION_KEYS 13키 전부 포함, flat scalar)."""
    rule_id = rec.get("ruleId")
    record_id = rec.get("recordId")
    unit = rec.get("unit")
    target = rec.get("baselineValue")
    return {
        "faultKey": fault_key,
        "criterion": rec["criterion"],
        "ruleId": rule_id if isinstance(rule_id, str) else None,
        "recordId": record_id if isinstance(record_id, str) else None,
        "selectedBy": selected_by,
        "streak": int(streak),
        "isSafety": False,
        "escalation": _escalation_for(streak, False),
        "motionId": motion_id,
        "baselinePoints": round(abs_points, 2),
        "baselineDeviation": _record_deviation(rec),
        "targetValue": float(target) if _is_finite_number(target) else None,
        "unit": unit if isinstance(unit, str) else None,
    }


def select_mission(
    deduction_records: list | None,
    safety_flags: list | None,
    prev_mission: dict | None,
    motion_id: str | None,
) -> dict | None:
    """오늘의 미션 선정 — D-19 우선순위 ①안전 > ②반복 미개선 > ③감점 최대.

    Args:
        deduction_records: result.deductionBreakdown.records (camelCase dict list).
        safety_flags: result.safetyFlags (camelCase dict list) 또는 None.
        prev_mission: 직전 분석 doc 의 result.mission 또는 None. 호출자는
            get_previous_analysis 결과에서 꺼내 전달한다 — motion 가드는 여기서.
        motion_id: 현재 분석의 인식 동작 id 또는 None.

    Returns:
        MISSION_KEYS 13키 flat scalar dict. 안전 결함도 실감점도 없으면 None
        (미션 fabrication 금지 — 결함 0 분석은 미션 없음).
    """
    # ── ① 안전 (D-19 ① + D-14 정합: streak 1 고정·escalation 'none' 강제) ──
    flags = [f for f in (safety_flags or []) if isinstance(f, dict)]
    if flags:
        flag_type = flags[0].get("flagType")
        criterion = (
            flag_type
            if isinstance(flag_type, str) and flag_type
            else _SAFETY_FALLBACK_CRITERION
        )
        return {
            "faultKey": build_fault_key(motion_id, None, criterion),
            "criterion": criterion,
            "ruleId": None,
            "recordId": None,
            "selectedBy": "safety",
            "streak": 1,  # D-14 — 게임·streak 제외 (고정)
            "isSafety": True,
            "escalation": "none",  # D-14 — 에스컬레이션 강제 제외
            "motionId": motion_id,
            "baselinePoints": 0.0,  # 안전은 감점 항목이 아님 (안내 전용)
            "baselineDeviation": None,
            "targetValue": None,
            "unit": None,
        }

    candidates = _fault_candidates(deduction_records, motion_id)
    if not candidates:
        return None

    # ── ② 반복 미개선 — motionId 가드 후 동일 faultKey 잔존 판정 ──────────
    prev = prev_mission if isinstance(prev_mission, dict) else None
    if prev is not None and prev.get("motionId") != motion_id:
        prev = None  # 다른 동작 체인 오염 차단 (streak 리셋)
    if prev is not None:
        prev_fault_key = prev.get("faultKey")
        if isinstance(prev_fault_key, str) and prev_fault_key:
            matches = [c for c in candidates if c[0] == prev_fault_key]
            if matches:
                fault_key, rec, abs_points = max(matches, key=lambda c: c[2])
                prev_streak = prev.get("streak")
                base = (
                    prev_streak
                    if not isinstance(prev_streak, bool)
                    and isinstance(prev_streak, int)
                    and prev_streak >= 1
                    else 1
                )
                streak = min(base + 1, _STREAK_CAP)
                return _mission_from_record(
                    fault_key,
                    rec,
                    abs_points,
                    selected_by="repeat",
                    streak=streak,
                    motion_id=motion_id,
                )

    # ── ③ 감점 최대 ────────────────────────────────────────────────────────
    fault_key, rec, abs_points = max(candidates, key=lambda c: c[2])
    return _mission_from_record(
        fault_key,
        rec,
        abs_points,
        selected_by="max_deduction",
        streak=1,
        motion_id=motion_id,
    )


def derive_mission_outcome(
    prev_mission: dict | None,
    current_records: list | None,
    mode: str,
    motion_id: str | None,
) -> dict | None:
    """지난 미션의 수치 outcome — 개선/잔존/악화를 숫자로만 산출 (D-26).

    반환 dict 는 MISSION_OUTCOME_KEYS 9키 전부 포함, 전부 수치·키·bool.
    **사람 문장(deltaSummary 류)은 생성하지 않는다** — 문장은 32-09 가
    phrasebook·summaryPraise 조립에서, 앱이 렌더에서 만든다 (리뷰 반영).

    None 조건:
      · mode != mode3 (self) — 미션 루프는 자기 성장 추적 전용.
      · prev_mission 부재 / motionId 불일치 (다른 동작 체인 오염 차단).
      · prev 가 안전 미션 (D-14 — 안내 전용, 개선 추적 제외).
      · prev 에 baselinePoints 부재(legacy) — 개선량 계산 불가 (리뷰 blocker 1).
    """
    if mode != models.MODE_SELF:
        return None
    prev = prev_mission if isinstance(prev_mission, dict) else None
    if prev is None:
        return None
    if prev.get("motionId") != motion_id:
        return None
    if prev.get("isSafety") is True:
        return None  # D-14 — 안전은 게임·개선 추적 제외
    prev_fault_key = prev.get("faultKey")
    if not isinstance(prev_fault_key, str) or not prev_fault_key:
        return None
    baseline_points_raw = prev.get("baselinePoints")
    if not _is_finite_number(baseline_points_raw) or baseline_points_raw < 0:
        return None  # baseline 없는 prev(legacy) — 계산 불가
    baseline_points = round(float(baseline_points_raw), 2)

    baseline_deviation_raw = prev.get("baselineDeviation")
    baseline_deviation = (
        round(float(baseline_deviation_raw), 2)
        if _is_finite_number(baseline_deviation_raw)
        else None
    )
    criterion = prev.get("criterion")
    if not isinstance(criterion, str) or not criterion:
        # 결정적 폴백 — faultKey 마지막 세그먼트가 criterion (build_fault_key 형식).
        criterion = prev_fault_key.split("::")[-1]

    matches = [
        c
        for c in _fault_candidates(current_records, motion_id)
        if c[0] == prev_fault_key
    ]
    if not matches:
        # 소멸 — 결함이 이번 분석에서 사라짐 (0 감점 record 포함).
        return {
            "improved": True,
            "faultKey": prev_fault_key,
            "criterion": criterion,
            "baselinePoints": baseline_points,
            "currentPoints": 0.0,
            "deltaPoints": baseline_points,
            "baselineDeviation": baseline_deviation,
            "currentDeviation": None,  # 측정 record 부재 — 편차 없음
            "deltaDeviation": None,
        }

    # 잔존 — 최악(|points| 최대) record 기준 보수 비교.
    _fk, rec, abs_points = max(matches, key=lambda c: c[2])
    current_points = round(abs_points, 2)
    current_deviation = _record_deviation(rec)
    delta_deviation = (
        round(baseline_deviation - current_deviation, 2)
        if baseline_deviation is not None and current_deviation is not None
        else None
    )
    return {
        "improved": current_points < baseline_points - _IMPROVE_EPS,
        "faultKey": prev_fault_key,
        "criterion": criterion,
        "baselinePoints": baseline_points,
        "currentPoints": current_points,
        "deltaPoints": round(baseline_points - current_points, 2),
        "baselineDeviation": baseline_deviation,
        "currentDeviation": current_deviation,
        "deltaDeviation": delta_deviation,
    }
