"""부상 위험 신호(SafetyFlag) — 결정론(LLM 무관) 측정 기반 레이어.

Phase 10 (injury-risk-flags) 신설. CONTEXT D-01 박제: 본 레이어는 기존 LLM
`CoachingTipDetail.injuryRisk` 프로즈와 **독립**이다 — 대체하거나 입력으로 주입하지
않는다. 측정 기반 플래그를 frozen dataclass + 전용 UI 배너로 산출해 temp 무관·캐시
안정의 객관성을 보장한다 (CLAUDE.md "결정론 우선").

발화 규칙(D-02): 각 위험 신호는 **(극단/과신전/비대칭 자세 조건) AND (통제 상실
지표)** 의 조합으로만 발화한다. 자세 단독 플래그 금지 — 정은지가 의도적으로 수행하는
180° 스플릿·완전 신전이 위양성으로 찍히는 것을 막는다. 통제 상실 지표는 Phase 8
`force_signals.py` 의 StabilityMetric severity / unstable_body_parts 를 재사용한다
(재계산 금지 — drift 방지).

임계값 출처 규칙(D-07): 본 모듈이 향후 도입할 절대/상대 임계는 module-level 상수로
선언하고 반드시 [CITED](외부 생체역학/IPSF 문헌) 또는 [ASSUMED](v1 휴리스틱, 근거
명시) 태그를 단다 (kismam.py 헤더 convention 정합). 보유 13영상 sweep 으로
재calibrate 하는 curve-fit 은 금지한다 ([[scoring-redesign-must-generalize-no-overfit]],
[[calibration-source-hard-gate]]). 현 Wave 0 = stub 라 실 임계 없음 — 규칙만 박제.

채널 의미(D-05, review HIGH — 이후 모든 fixture/게이트가 따라야 함):
`keypoints_4ch[:, :, 3]` 은 **`uncertainty_proxy`** 이며 confidence 가 **아니다**.
pose_frame.py:326 (`to_coco17_array` → `(x, y, z, uncertainty_proxy)`),
pose_frame.py:335 (미감지 default = `1.0`), pose_frame.py:115
(`uncertainty_proxy = 1 - confidence`), app.py:452 (ch3 `> 0.5` = 저신뢰/보정 대상)
정합. HIGH uncertainty(≈1.0) = 최악/미감지, LOW uncertainty(≈0.05) = 양호.
D-05 게이팅(10-03)은 `confidence = 1 - uncertainty` 로 변환하거나
`uncertainty <= MAX_KP_UNCERTAINTY` 로 게이트하며, 그 게이트는 **그 side 계산에
실제로 쓰이는 keypoint 에만**(hinge triplet + frontal-axis pair + longitudinal-axis
centers) 스코프한다 — 절대 ch3 를 confidence 로 읽지 말 것, 절대 안 쓰는(예: face)
keypoint 의 NaN/uncertainty 로 no-op 하지 말 것. "저신뢰 ch3 를 거부" 하는 게이트는
의미가 뒤집혀 미감지 keypoint 를 고위험 경고에 끌어들이므로 금지.

D-05 helper contract (review HIGH round-5 — 10-03 helper 가 callable 하도록 박제):
D-05 발화 함수는 `_joint_hyperextension_flags(*, angles, keypoints_4ch, fsr, profile)
-> list[SafetyFlag]` (keyword-only, plural 반환). `angles` + `profile` 을 요구하는
이유는 공유 `dimensions._select_window(angles, profile)` hold-window 선택기를 구동해
window (s,e) → phase P 를 산출하기 때문이다 (keypoints 만으로 window 를 만들 수 없음).
최대 4 candidate (left_knee/right_knee/left_elbow/right_elbow) 를 worst severity +
고정 tie-break 순서로 ONE consolidated `joint_hyperextension` 플래그로 합친다.

이 모듈은 순수 함수(numpy only, boto3/네트워크 무관)이며 models 를 import 하지 않는다
(models → safety_flags 단방향 의존, force_signals 재export 패턴 정합 — import cycle 방지).
"""

from __future__ import annotations

from dataclasses import dataclass

# numpy / skeleton 등 leaf 모듈만 의존 (firing 로직은 10-02/03/04 에서 추가).
# 현 Wave 0 stub 는 외부 의존 없음 — 추후 firing rule 이 numpy + skeleton +
# kismam + dimensions + motiondtw 를 lazy import 한다.


# ── enum tuples (frozen dataclass __post_init__ 검증용) ──────────────────────
_FLAG_TYPES = ("asymmetry", "trunk_hyperextension", "joint_hyperextension", "level_mismatch")
_SEVERITY_LEVELS = ("low", "medium", "high")
_CONFIDENCE_LEVELS = ("low", "medium", "high")
_MODE_SCOPES = ("both", "mode1_only")


@dataclass(frozen=True)
class SafetyFlag:
    """결정론 부상 위험 신호 — scalar-only (Firestore nested-array 금지, Pitfall 1).

    RESEARCH Pattern 1 필드 정합. 모든 필드는 scalar str — nested list 금지
    (causes[]-스타일 중첩 금지).

    필드:
      flag_type          : 'asymmetry' | 'trunk_hyperextension' |
                           'joint_hyperextension' | 'level_mismatch'
      body_region        : 코칭 카피용 KO 부위 (예: '무릎·팔꿈치', '허리')
      severity           : 'low' | 'medium' | 'high' (force_signals SeverityLevel 미러)
      posture_condition  : 충족된 기하 조건 audit 문자열
      control_loss_signal: 발화한 통제 상실 audit 문자열 (D-02 partner)
      confidence         : 'low' | 'medium' | 'high'
      mode_scope         : 'both' | 'mode1_only' (D-06 = mode1_only)
    """

    flag_type: str
    body_region: str
    severity: str
    posture_condition: str
    control_loss_signal: str
    confidence: str
    mode_scope: str

    def __post_init__(self) -> None:
        if self.flag_type not in _FLAG_TYPES:
            raise ValueError(
                f"flag_type must be one of {_FLAG_TYPES}, got {self.flag_type!r}"
            )
        if self.severity not in _SEVERITY_LEVELS:
            raise ValueError(
                f"severity must be one of {_SEVERITY_LEVELS}, got {self.severity!r}"
            )
        if self.confidence not in _CONFIDENCE_LEVELS:
            raise ValueError(
                f"confidence must be one of {_CONFIDENCE_LEVELS}, "
                f"got {self.confidence!r}"
            )
        if self.mode_scope not in _MODE_SCOPES:
            raise ValueError(
                f"mode_scope must be one of {_MODE_SCOPES}, got {self.mode_scope!r}"
            )


def compute_safety_flags(
    *,
    angles,
    keypoints_4ch,
    force_signals_report,
    dimension_scores,
    reference_angles=None,
    experience=None,
    reference_level=None,
    mode,
    profile,
) -> list[SafetyFlag]:
    """결정론 SafetyFlag 산출 진입점 — Wave 0 stub (빈 list 반환).

    이 시그니처는 LOCK 된다 (10-02 의 pipeline `_process` 가 그대로 호출).
    참고:
      (a) D-05 시상면 기준 프레임은 `keypoints_4ch`(pole-aligned 3D, ch3 =
          uncertainty_proxy)에서 INTERNAL 로 도출한다 — 추가 kwarg 가 아니다.
          D-05 helper `_joint_hyperextension_flags(*, angles, keypoints_4ch,
          fsr, profile)` 는 이미 시그니처에 있는 `angles` + `profile` 로
          `dimensions._select_window` 를 구동해 hold window/phase 를 얻는다.
      (b) D-03/D-04 reference 비교의 DTW 시간 정렬도 `angles` + `reference_angles`
          에서 INTERNAL 로 재계산한다 (정렬 artifact kwarg 없음 — 10-02/10-04 참조).
    이 시그니처는 final 이다.

    Wave 0 stub — firing rules land in 10-02/03/04.
    """
    return []
