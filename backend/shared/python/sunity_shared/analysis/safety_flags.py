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

import numpy as np

from . import skeleton
from .features import feature_vector
from .kismam import score_from_deviation
from .motiondtw import motion_dtw

# leaf 분석 모듈만 의존 (numpy + skeleton + features + kismam + motiondtw). models 는
# import 하지 않는다 (models → safety_flags 단방향). dimensions 는 _trunk_hyperextension_flag
# 안에서 lazy import (모듈 로드 비용 절감 + 순환 방지 보수).


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


# ── 임계 상수 (D-07: 출처 태그 필수) ─────────────────────────────────────────
# KISMAM tol — IPSF Code of Points 허용 범위. score_from_deviation 의 default 와 동일.
_KISMAM_TOL_DEG = 20.0  # [CITED: IPSF Code of Points tolerance band]
# trunk 과신전 발화 margin — "허용 범위를 substantially 넘음". reference-anchored 이라
# 보유 13영상 sweep 으로 fit 한 절대 cutoff 가 아니다 ([[calibration-source-hard-gate]],
# D-07). 1.5×tol = score_from_deviation < ~33 지점.
_TRUNK_EXCESS_MARGIN = 1.5  # [ASSUMED: reference-anchored "substantially beyond tol" margin]
_TRUNK_POSTURE_SCORE_CUTOFF = 33  # score_from_deviation(1.5*tol, tol) ≈ 32 → < 33
# 통제 상실로 인정하는 severity 집합 (low 는 정상 변동).
_CONTROL_LOSS_SEVERITIES = ("medium", "high")
# hold window → phase 매핑 최소 overlap 비율 (≥50% 미만이면 phase 미확정 → no-op).
_PHASE_OVERLAP_MIN = 0.5


# ── 윈도우 → phase 매핑 (MEDIUM-1) ───────────────────────────────────────────
def _phase_for_window(phase_boundaries, s: int, e: int):
    """frame window [s, e) 를 최대-overlap PhaseBoundary 의 phase 로 매핑.

    `phase_boundaries` = `ForceSignalsReport.phase_boundaries` (list[PhaseBoundary],
    각 PhaseBoundary 는 `phase` / `start_frame_idx` / `end_frame_idx`). 각 boundary 와
    [s, e) 의 정수 overlap 을 구해 MAX overlap boundary 를 고르고, 그 overlap 이
    `>= 0.5 * (e - s)` (선택 window 의 ≥50%) 일 때만 phase 를 반환한다.

    NO-OP 규약: 50% overlap 을 통과하는 boundary 가 없거나 phase_boundaries 가 비면
    None 반환 — phase-localize 불가한 window 를 "아무 phase" 로 넓히지 않는다 (그러면
    temporal 위양성이 다시 열린다, D-02). dimensions._select_window 프레임 인덱스 →
    StabilityMetric.phase 라벨의 결정론적 bridge.
    """
    if not phase_boundaries:
        return None
    window_len = int(e) - int(s)
    if window_len <= 0:
        return None
    best_phase = None
    best_overlap = 0
    for b in phase_boundaries:
        bs = getattr(b, "start_frame_idx", None)
        be = getattr(b, "end_frame_idx", None)
        if bs is None or be is None:
            continue
        overlap = max(0, min(int(e), int(be)) - max(int(s), int(bs)))
        if overlap > best_overlap:
            best_overlap = overlap
            best_phase = getattr(b, "phase", None)
    if best_phase is None:
        return None
    if best_overlap < _PHASE_OVERLAP_MIN * window_len:
        return None
    return best_phase


# ── DTW path-정렬 reference 비교 (HIGH-A) ────────────────────────────────────
def _dtw_aligned_joint_medians(student_angles, reference_angles, joint_keys):
    """student↔reference 각도를 DTW path 로 시간 정렬한 뒤 관절별 finite median 2 dict 반환.

    pipeline `_angles_to_dtw_median_dicts` (app.py:1563-1619) 를 MIRROR 한다 — 점수
    산출 per_joint_deviation 과 동일한 motion_dtw 정렬을 safety_flags 안에서 재계산한다
    (정렬 artifact 를 kwarg 로 받지 않음: compute_safety_flags 시그니처는 angles +
    reference_angles 만 전달하고, Mode3 의 DTW match 는 _mode3_comparison 안에서 폐기되어
    injection 시점에 scope 에 없으므로 재계산이 유일한 균일 path). DTW 정렬은 pipeline
    의 기존 motion_dtw 방식 그대로 — 결정론적이며 tuned offset 이 아니다 (D-07).

    raw same-index 비교는 student/reference 의 동작 timing 이 다를 때 정은지의 의도적
    신전을 위양성으로 찍는다. path-정렬은 student 의 극단 프레임을 reference 의 대응
    극단 프레임과 짝지어 reference-anchored excess 를 상쇄한다 (HIGH-A 위양성 방어).

    빈 path / None reference / 비2D → ({}, {}) (graceful, never raise).
    """
    if student_angles is None or reference_angles is None:
        return {}, {}
    a_user = np.asarray(student_angles, dtype=float)
    a_ref = np.asarray(reference_angles, dtype=float)
    if a_user.ndim != 2 or a_ref.ndim != 2 or a_user.shape[0] == 0 or a_ref.shape[0] == 0:
        return {}, {}
    try:
        match = motion_dtw(feature_vector(a_user), feature_vector(a_ref))
    except Exception:
        return {}, {}
    seg = a_user[match.start : match.end]
    path = match.path
    if not path or seg.shape[0] == 0:
        return {}, {}
    J = min(a_ref.shape[1], seg.shape[1], len(joint_keys))
    user_vals: list[list[float]] = [[] for _ in range(J)]
    ref_vals: list[list[float]] = [[] for _ in range(J)]
    for u, r in path:
        if u >= seg.shape[0] or r >= a_ref.shape[0]:
            continue
        for j in range(J):
            uv = seg[u, j]
            rv = a_ref[r, j]
            if np.isfinite(uv):
                user_vals[j].append(float(uv))
            if np.isfinite(rv):
                ref_vals[j].append(float(rv))
    user_median: dict[str, float] = {}
    ref_median: dict[str, float] = {}
    for j in range(J):
        if user_vals[j]:
            user_median[joint_keys[j]] = float(np.median(user_vals[j]))
        if ref_vals[j]:
            ref_median[joint_keys[j]] = float(np.median(ref_vals[j]))
    return user_median, ref_median


# ── D-02 LOCALITY + TEMPORAL 통제 상실 게이트 (HIGH-1) ───────────────────────
# TEMPORAL granularity (MEDIUM-2, KNOWN v1 LIMITATION): force_signals 의
# stability_metrics 는 PER-PHASE (StabilityMetric.phase) 이지 per-frame 이 아니다.
# 따라서 v1 temporal co-location 은 **phase-level** 이다 — qualifying StabilityMetric 의
# .phase 가 자세(posture)의 phase 와 같아야 한다. 같은 phase 안의 다른 frame 불안정은
# sub-window 자세와 여전히 co-locate 될 수 있다 (frame-level 통제 상실 = CONTEXT Deferred:
# 명시적 slip/regrip event 검출, v1 범위 밖).
def _control_loss_for_joint(fsr, joint_key, *, phase=None) -> bool:
    """joint/region-local + (옵션) phase-level temporal 통제 상실 여부.

    trunk/joint/asymmetry 등 관절-스코프 플래그의 REQUIRED path. 어떤 StabilityMetric 이
    (i) `joint_key in metric.unstable_body_parts` (region-local, 키는 JOINT_KEYS),
    (ii) `metric.severity in {'medium','high'}`,
    (iii) phase 가 주어지면 `metric.phase == phase` (temporal co-location)
    를 모두 만족할 때만 True. bare phase-level 폴백(`_control_loss_phase_level`)은
    localized joint 신호가 없는 플래그(D-06 whole-body overreach)에만 허용된다.
    """
    metrics = getattr(fsr, "stability_metrics", None) or []
    for m in metrics:
        parts = getattr(m, "unstable_body_parts", None) or []
        if joint_key not in parts:
            continue
        if getattr(m, "severity", None) not in _CONTROL_LOSS_SEVERITIES:
            continue
        if phase is not None and getattr(m, "phase", None) != phase:
            continue
        return True
    return False


def _control_loss_phase_level(fsr) -> bool:
    """joint/phase 무관 any-metric 통제 상실 — level_mismatch(D-06, 10-04) 전용 폴백.

    trunk/joint/asymmetry 는 이 경로를 쓰지 말 것 (반드시 `_control_loss_for_joint`).
    """
    metrics = getattr(fsr, "stability_metrics", None) or []
    for m in metrics:
        if getattr(m, "severity", None) in _CONTROL_LOSS_SEVERITIES:
            return True
    return False


def _maybe_flag(posture_met: bool, control_lost: bool, **flag_kwargs) -> SafetyFlag | None:
    """posture AND control-loss 둘 다 True 일 때만 SafetyFlag 반환 (Pitfall 2).

    자세 단독은 절대 발화하지 않는다 — 정은지 위양성 방어의 핵심.
    """
    if posture_met and control_lost:
        return SafetyFlag(**flag_kwargs)
    return None


# ── D-04 trunk-femur 과신전 (reference-anchored, hip-local) ──────────────────
def _trunk_hyperextension_flag(angles, reference_angles, fsr, profile) -> SafetyFlag | None:
    """D-04 요추 과신전 — reference-anchored (DTW-aligned) + hip-local 통제 상실.

    A3 / Pitfall 4 / MEDIUM-3: 절대 lumbar cutoff 없음 (방어 가능한 절대 생체역학
    수치 부재 — IPSF 의료 수치 없음, trunk-femur 프록시는 lumbar+hip 혼재). reference-
    anchored 만 — 정은지(mode1) / 이전 영상(mode3) 기준 대비 초과분으로 발화. 절대 trunk
    규칙은 명시적으로 DEFERRED (요추 전용 키포인트 필요). 양 모드에서 발화한다 (mode_scope
    ='both') — 모드가 제공하는 reference 에 anchor.

    reference_angles=None / 정렬 dict 빈 / phase 미확정 → None (graceful no-op).
    """
    if reference_angles is None:
        return None
    student_med, ref_med = _dtw_aligned_joint_medians(
        angles, reference_angles, skeleton.JOINT_KEYS
    )
    if not student_med or not ref_med:
        return None
    # hold window (공유 selector — drift 금지) → phase 매핑.
    from . import dimensions  # lazy import (모듈 로드 비용 절감).

    try:
        _sliced, (s, e) = dimensions._select_window(angles, profile)
    except Exception:
        return None
    phase = _phase_for_window(getattr(fsr, "phase_boundaries", None), s, e)
    if phase is None:
        return None
    # trunk-femur 프록시 = left_hip/right_hip 관절각 (JOINT_ANGLES). 양측 중 최대 excess.
    best_excess = 0.0
    best_side: str | None = None
    for hip in ("left_hip", "right_hip"):
        sv = student_med.get(hip)
        rv = ref_med.get(hip)
        if sv is None or rv is None:
            continue
        excess = max(0.0, float(sv) - float(rv))
        if excess > best_excess:
            best_excess = excess
            best_side = hip
    if best_side is None:
        return None
    # posture_met = 기준 대비 초과분이 허용 범위를 substantially 넘음 (1.5×tol ≈ score<33).
    posture_met = score_from_deviation(best_excess, _KISMAM_TOL_DEG) < _TRUNK_POSTURE_SCORE_CUTOFF
    control_lost = _control_loss_for_joint(
        fsr, "left_hip", phase=phase
    ) or _control_loss_for_joint(fsr, "right_hip", phase=phase)
    confidence = getattr(fsr, "overall_confidence", None) or "low"
    side_ko = "왼쪽" if best_side == "left_hip" else "오른쪽"
    return _maybe_flag(
        posture_met,
        control_lost,
        flag_type="trunk_hyperextension",
        body_region="허리",
        severity="medium",
        posture_condition=(
            f"{side_ko} 고관절(trunk-femur 프록시) 신전이 기준 대비 "
            f"{best_excess:.0f}° 초과 (phase={phase})"
        ),
        control_loss_signal=f"{phase} 구간 고관절 통제 흔들림 (hip-local)",
        confidence=confidence,
        mode_scope="both",
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
    """결정론 SafetyFlag 산출 진입점.

    이 시그니처는 LOCK 되어 있다 (10-02 의 pipeline `_process` 가 그대로 호출).
    참고:
      (a) D-05 시상면 기준 프레임은 `keypoints_4ch`(pole-aligned 3D, ch3 =
          uncertainty_proxy)에서 INTERNAL 로 도출한다 (10-03) — 추가 kwarg 가 아니다.
      (b) D-03/D-04 reference 비교의 DTW 시간 정렬도 `angles` + `reference_angles`
          에서 INTERNAL 로 재계산한다 (`_dtw_aligned_joint_medians`).

    10-02 = D-04 trunk 규칙. 다른 규칙(D-05/D-03/D-06)은 10-03/10-04 에서 append.
    numpy-only, NaN/malformed → no-flag (never raise).
    """
    fsr = force_signals_report
    if fsr is None:
        return []
    try:
        trunk = _trunk_hyperextension_flag(angles, reference_angles, fsr, profile)
    except Exception:
        trunk = None
    return [f for f in (trunk,) if f is not None]
