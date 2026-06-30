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


# ── D-05 관절 과신전 상수 (D-07: 출처 태그 필수) ─────────────────────────────
# 절대 검출 floor — 중립(180°) 넘어 역꺾인 정도. 외부 임상/생체역학 문헌 출처이며
# 보유 13영상 sweep 으로 fit 한 값이 아니다 (D-07, [[calibration-source-hard-gate]]).
_KNEE_HYPEREXT_FLOOR_DEG = 5.0   # [CITED: genu recurvatum — 무릎 중립 초과 >5° (물리치료/생체역학 문헌)]
_ELBOW_HYPEREXT_FLOOR_DEG = 10.0  # [CITED: Beighton hypermobility — 팔꿈치 과신전 >10°]
# severity 밴드 — 과신전 magnitude(중립 초과 도) 기준. knee 10°/20° (D-05 plan).
_HYPEREXT_SEVERITY_HIGH_DEG = 20.0   # [CITED: 무릎 과신전 심도 밴드 상한 (genu recurvatum severity)]
_HYPEREXT_SEVERITY_MEDIUM_DEG = 10.0  # [CITED: 무릎 과신전 심도 밴드 하한]

# fail-conservative 게이트 상수 — 전부 no-flag 영역을 넓히는 보수 임계(검출 임계 아님,
# fit 대상 아님). 각 상수 [ASSUMED conservative gate].
_CLEAR_FLEXION_MAX = 90.0     # [ASSUMED conservative gate] calibration 프레임 included 상한 (이보다 작아야 명백한 굽힘)
_MAX_KP_UNCERTAINTY = 0.5     # [ASSUMED conservative gate] uncertainty_proxy 상한 (app.py:452 ">0.5 = 저신뢰" 정합)
_COLLINEAR_COS = 0.9          # [ASSUMED conservative gate] |dot(frontal,longitudinal)| 이 넘으면 방위 미해결(spin/inversion)
_SEGMENT_RATIO_MAX = 2.5      # [ASSUMED conservative gate] hold 윈도우 내 세그먼트 길이 max/min 비 상한
_HYPEREXT_EPS = 1e-6          # [ASSUMED conservative gate] 영벡터/공선 판정 수치 epsilon
_HYPEREXT_MAJORITY = 0.5      # [ASSUMED conservative gate] hold 윈도우에서 reverse-bend 가 일치해야 하는 프레임 비율

# D-05 후보 평가 순서 (consolidation tie-break 의 FIXED 순서이기도 함).
_HINGE_ORDER = ("left_knee", "right_knee", "left_elbow", "right_elbow")
_HINGE_LABEL_KO = {
    "left_knee": "왼쪽 무릎",
    "right_knee": "오른쪽 무릎",
    "left_elbow": "왼쪽 팔꿈치",
    "right_elbow": "오른쪽 팔꿈치",
}
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}

# ── D-03 좌우 비대칭 상수 (D-07: 출처 태그 필수) ─────────────────────────────
# EXPLICIT L/R joint pairs — MAX aggregation 으로 단일 최악 pair 가 플래그를 구동한다.
# 한 관절의 심한 비대칭이 actionable 위험 신호이며, pair 평균은 그 하나를 대칭 pair
# 들 아래로 희석해 위험을 숨긴다 (MEDIUM).
_ASYMMETRY_PAIRS = (
    ("left_elbow", "right_elbow"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
)
_ASYMMETRY_PAIR_LABEL = {
    ("left_elbow", "right_elbow"): "좌우 팔꿈치",
    ("left_shoulder", "right_shoulder"): "좌우 어깨",
    ("left_hip", "right_hip"): "좌우 고관절",
    ("left_knee", "right_knee"): "좌우 무릎",
}
# 비대칭 excess severity 상한 밴드 — KISMAM tol 배수 (reference-anchored, 13영상 fit
# 아님; trunk margin 과 동일 provenance, D-07 / [[calibration-source-hard-gate]]).
_ASYMMETRY_SEVERITY_HIGH_DEG = 3.0 * _KISMAM_TOL_DEG  # 60° 이상 excess → high

# ── D-06 레벨 대비 무리 상수 ─────────────────────────────────────────────────
# MODE_EXPERT mirror — models import 회피 (models → safety_flags 단방향 의존).
_MODE_EXPERT = "mode1"
# 경력/난이도 ladder — basic/beginner 동급(0), intermediate(1), advanced(2). 비-멤버
# (None/위조)는 키 부재 → level flag omit (fail-safe enum guard, T-10-02).
_LEVEL_LADDER = {"basic": 0, "beginner": 0, "intermediate": 1, "advanced": 2}


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


def _max_control_loss_severity(fsr) -> str | None:
    """통제 상실 metric 중 최대 severity('medium'/'high') — D-06 강도 스케일링용.

    low(정상 변동)는 무시. qualifying metric 이 없으면 None. level_mismatch 의
    severity 가 rank-gap 과 instability 강도 둘 다에 스케일하도록 후자를 제공한다.
    """
    metrics = getattr(fsr, "stability_metrics", None) or []
    best: str | None = None
    for m in metrics:
        sev = getattr(m, "severity", None)
        if sev not in _CONTROL_LOSS_SEVERITIES:
            continue
        if best is None or _SEVERITY_RANK[sev] > _SEVERITY_RANK[best]:
            best = sev
    return best


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


# ── D-03 좌우 비대칭 (DTW-aligned reference-anchored, explicit pairs, MAX agg) ─
def _asymmetry_flag(angles, reference_angles, fsr, profile) -> SafetyFlag | None:
    """D-03 좌우 비대칭 — DTW-path-aligned reference-anchored + pair-local·phase-co-located 통제 상실.

    `excess = max(0, student_LR − ref_LR)` 를 `_dtw_aligned_joint_medians` 의 DTW-정렬
    per-joint median 에서 계산한다 (raw same-index 아님 — HIGH-A). 정렬은 student 의 극단
    프레임을 reference 의 대응 프레임과 짝지어, reference(또는 mode3 이전 영상)에 baked-in
    된 의도적 비대칭이 SHIFTED timing 에서도 상쇄된다. EXPLICIT L/R pair set + MAX
    aggregation — 단일 최악 pair 가 플래그를 구동하고 audit 문자열에 명시된다. 절대 L/R
    비대칭은 v1 에서 절대 발화하지 않는다 (D-03). pair-local + phase-co-located 통제 상실
    AND-gate (D-02): worst pair 두 관절의 통제 상실을 _control_loss_for_joint 로 검사한다.

    reference_angles=None / 정렬 dict 빈 / phase 미확정 → None (graceful no-op — first
    Mode-3 video 의 surfaced limitation 포함, T-10-11).
    """
    if reference_angles is None:
        return None
    student_med, ref_med = _dtw_aligned_joint_medians(
        angles, reference_angles, skeleton.JOINT_KEYS
    )
    if not student_med or not ref_med:
        return None
    # EXPLICIT PAIRS + MAX AGGREGATION — 단일 최악 pair 가 플래그를 구동.
    best_excess = 0.0
    best_pair: tuple[str, str] | None = None
    for left_key, right_key in _ASYMMETRY_PAIRS:
        sl = student_med.get(left_key)
        sr = student_med.get(right_key)
        rl = ref_med.get(left_key)
        rr = ref_med.get(right_key)
        if sl is None or sr is None or rl is None or rr is None:
            continue
        student_lr = abs(float(sl) - float(sr))
        ref_lr = abs(float(rl) - float(rr))
        excess_pair = max(0.0, student_lr - ref_lr)
        if excess_pair > best_excess:
            best_excess = excess_pair
            best_pair = (left_key, right_key)
    if best_pair is None:
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
    left_key, right_key = best_pair
    # posture_met = excess 가 허용 범위를 substantially 넘음 (1.5×tol ≈ score<33).
    posture_met = (
        score_from_deviation(best_excess, _KISMAM_TOL_DEG) < _TRUNK_POSTURE_SCORE_CUTOFF
    )
    left_lost = _control_loss_for_joint(fsr, left_key, phase=phase)
    right_lost = _control_loss_for_joint(fsr, right_key, phase=phase)
    control_lost = left_lost or right_lost
    severity = "high" if best_excess >= _ASYMMETRY_SEVERITY_HIGH_DEG else "medium"
    label = _ASYMMETRY_PAIR_LABEL[best_pair]
    side_ko = "왼쪽" if left_lost else "오른쪽"
    confidence = getattr(fsr, "overall_confidence", None) or "low"
    return _maybe_flag(
        posture_met,
        control_lost,
        flag_type="asymmetry",
        body_region=label,
        severity=severity,
        posture_condition=(
            f"{label} 비대칭이 기준 대비 {best_excess:.0f}° 초과 (phase={phase})"
        ),
        control_loss_signal=f"{phase} 구간 {side_ko} 통제 흔들림 (pair-local)",
        confidence=confidence,
        mode_scope="both",
    )


# ── D-06 레벨 대비 무리 (Mode 1 전용, rank-gap×instability severity, enum-guarded) ─
def _level_mismatch_flag(mode, experience, reference_level, fsr) -> SafetyFlag | None:
    """D-06 레벨 대비 무리 — Mode 1 전용. reference.level 이 입력 경력을 상회 AND 통제 상실.

    Mode 1(MODE_EXPERT)에서만 발화한다 — Mode 3 는 move 난이도 미상이라 D-02 control-loss
    가 overreach 를 대신 잡는다. ENUM GUARD: upstream normalize_body_profile 이 비-enum 을
    이미 drop 하지만 모듈 안에서 ladder 멤버십을 재검사한다 (upstream 맹신 금지, T-10-02) —
    experience/reference_level 이 ladder 키가 아니면(None/위조) None 반환 (fail-safe).
    SEVERITY = RANK-GAP × INSTABILITY: gap==1 + medium instability → 'low' (gap=1
    over-warn 방지); gap>=2 + high → 'high'; 그 외 → 'medium'. control-loss partner 는
    whole-body overreach 의 정당한 phase-level 케이스(_control_loss_phase_level) — D-06 은
    10-02 가 phase-level 폴백을 허용한 유일한 플래그다.
    """
    if mode != _MODE_EXPERT:
        return None
    if experience not in _LEVEL_LADDER or reference_level not in _LEVEL_LADDER:
        return None
    gap = _LEVEL_LADDER[reference_level] - _LEVEL_LADDER[experience]
    posture_met = gap >= 1
    instability = _max_control_loss_severity(fsr)
    control_lost = _control_loss_phase_level(fsr)
    if gap >= 2 and instability == "high":
        severity = "high"
    elif gap == 1 and instability == "medium":
        severity = "low"
    else:
        severity = "medium"
    confidence = getattr(fsr, "overall_confidence", None) or "low"
    return _maybe_flag(
        posture_met,
        control_lost,
        flag_type="level_mismatch",
        body_region="전신 (레벨 대비)",
        severity=severity,
        posture_condition=(
            f"기준 동작 난이도({reference_level})가 입력 경력({experience}) 대비 "
            f"{gap}단계 높음"
        ),
        control_loss_signal=f"반동·흔들림 통제 신호 ({instability or 'none'})",
        confidence=confidence,
        mode_scope="mode1_only",
    )


# ── D-05 관절 과신전 (cross-product 방향 판별 + 결정론 frontal-axis 좌표계) ───
# RESEARCH Pattern 3: 내적(dot)은 0~180° 굽힘 크기만 줘 방향 미상. 무릎·팔꿈치는
# 1자유도 시상면 힌지라 hinge cross product `n = u×w` 가 medial-lateral(frontal) 축과
# 평행하고, `dot(n, frontal)` 의 부호가 정상 굴곡 vs 역꺾임(genu recurvatum / elbow
# hyperextension)을 변별한다. frontal 좌표계와 per-side flexion 부호는 ONE 결정론 규칙
# 으로 못박는다 (review HIGH-B — 'e.g.' 금지): frontal = unit(right_hip - left_hip)[무릎]
# / unit(right_shoulder - left_shoulder)[팔꿈치]; flexion 부호 s_flex 는 clip 전체의
# MIN included-angle(명백히 굽힌) calibration 프레임에서 sign(dot(n, frontal)).


def _unit(v):
    """단위벡터 — |v| < EPS 면 None (영벡터 방어)."""
    n = float(np.linalg.norm(v))
    if n < _HYPEREXT_EPS:
        return None
    return v / n


def _hyperextension_candidate(kp, s: int, e: int, joint_key: str):
    """단일 hinge side 의 과신전 후보 → (amount_deg, severity) | None.

    fail-conservative: 어떤 ambiguity 브랜치라도 걸리면 None (never raise). 게이트는
    그 side 가 실제로 쓰는 keypoint(hinge triplet + frontal-axis pair + longitudinal
    centers)에만 스코프된다 — 안 쓰는(face/대측) keypoint 의 NaN/uncertainty 는 무시.
    """
    a_name, v_name, c_name = skeleton.JOINT_ANGLES[joint_key]
    ia = skeleton.kp_index(a_name)
    iv = skeleton.kp_index(v_name)
    ic = skeleton.kp_index(c_name)
    if "knee" in joint_key:
        fl = skeleton.kp_index("left_hip")
        fr = skeleton.kp_index("right_hip")
        floor = _KNEE_HYPEREXT_FLOOR_DEG
    else:
        fl = skeleton.kp_index("left_shoulder")
        fr = skeleton.kp_index("right_shoulder")
        floor = _ELBOW_HYPEREXT_FLOOR_DEG
    # longitudinal centers — frontal↔longitudinal 방위 게이트용.
    lhc = skeleton.kp_index("left_hip")
    rhc = skeleton.kp_index("right_hip")
    lsc = skeleton.kp_index("left_shoulder")
    rsc = skeleton.kp_index("right_shoulder")

    # USED-KEYPOINT SET — NaN/inf + uncertainty 게이트가 검사하는 유일한 컬럼 집합.
    used_idx = sorted({ia, iv, ic, fl, fr, lhc, rhc, lsc, rsc})

    T = kp.shape[0]
    s = max(0, int(s))
    e = min(T, int(e))
    if e - s <= 0:
        return None

    # GATE (h) NaN/inf — USED keypoint 만 (face/대측 NaN 은 무시). calibration 이
    # clip 전체 argmin 을 쓰므로 전체 프레임 used 컬럼의 좌표·ch3 finite 를 요구한다.
    used_coords = kp[:, used_idx, :3]
    used_unc = kp[:, used_idx, 3]
    if not np.all(np.isfinite(used_coords)):
        return None
    if not np.all(np.isfinite(used_unc)):
        return None
    # GATE (a) uncertainty_proxy — HIGH(>MAX) 면 신뢰 불가 → no candidate. ch3 는
    # uncertainty_proxy(1.0=미감지/최악), confidence 가 아니다 (review HIGH).
    if float(np.max(used_unc)) > _MAX_KP_UNCERTAINTY:
        return None

    # 프레임별 included angle / signed projection / 세그먼트 길이 (clip 전체).
    included = np.full(T, np.nan, dtype=float)
    signed = np.full(T, np.nan, dtype=float)
    len_u = np.full(T, np.nan, dtype=float)
    len_w = np.full(T, np.nan, dtype=float)
    collinear = np.zeros(T, dtype=bool)
    frontal_long_cos = np.full(T, np.nan, dtype=float)
    frontal_degenerate = np.zeros(T, dtype=bool)
    for t in range(T):
        u = kp[t, ia, :3] - kp[t, iv, :3]
        w = kp[t, ic, :3] - kp[t, iv, :3]
        nu = float(np.linalg.norm(u))
        nw = float(np.linalg.norm(w))
        len_u[t] = nu
        len_w[t] = nw
        if nu < _HYPEREXT_EPS or nw < _HYPEREXT_EPS:
            continue
        cos = float(np.clip(np.dot(u, w) / (nu * nw), -1.0, 1.0))
        included[t] = float(np.degrees(np.arccos(cos)))
        n = np.cross(u, w)
        # GATE (f) 공선 hinge 세그먼트 — |u×w| < EPS*|u||w| → 굽힘축 미정의.
        collinear[t] = float(np.linalg.norm(n)) < _HYPEREXT_EPS * nu * nw
        frontal_raw = kp[t, fr, :3] - kp[t, fl, :3]
        frontal = _unit(frontal_raw)
        # GATE (d) frontal 축 퇴화 — hip/shoulder 가 한 점.
        frontal_degenerate[t] = frontal is None
        if frontal is None:
            continue
        signed[t] = float(np.dot(n, frontal))
        hip_center = 0.5 * (kp[t, lhc, :3] + kp[t, rhc, :3])
        sh_center = 0.5 * (kp[t, lsc, :3] + kp[t, rsc, :3])
        longitudinal = _unit(sh_center - hip_center)
        if longitudinal is not None:
            frontal_long_cos[t] = abs(float(np.dot(frontal, longitudinal)))

    # GATE (g) calibration — clip 전체 MIN included 프레임이 명백한 굽힘이어야 함.
    if not np.any(np.isfinite(included)):
        return None
    cal_frame = int(np.nanargmin(included))
    min_angle = float(included[cal_frame])
    if min_angle >= _CLEAR_FLEXION_MAX:
        return None
    s_flex_val = signed[cal_frame]
    if not np.isfinite(s_flex_val) or s_flex_val == 0.0:
        return None
    s_flex = 1.0 if s_flex_val > 0 else -1.0

    # ── 이하 게이트/판정은 hold 윈도우 [s:e] 프레임에서 ──
    win = range(s, e)
    valid = [t for t in win if np.isfinite(included[t]) and np.isfinite(signed[t])]
    if not valid:
        return None
    # GATE (d) frontal 퇴화 — 윈도우 프레임에 하나라도 → no candidate.
    if any(frontal_degenerate[t] for t in win):
        return None
    # GATE (e) 방위 미해결(spin/inversion) — frontal 이 longitudinal 과 거의 공선.
    cos_vals = [frontal_long_cos[t] for t in valid if np.isfinite(frontal_long_cos[t])]
    if cos_vals and float(np.median(cos_vals)) > _COLLINEAR_COS:
        return None
    # GATE (f) 공선 hinge — 윈도우 qualifying 프레임 다수가 공선.
    if sum(1 for t in valid if collinear[t]) > _HYPEREXT_MAJORITY * len(valid):
        return None
    # GATE (b) 세그먼트 길이 비일관 — hold 윈도우 내 max/min 비 상한 초과.
    lu = [len_u[t] for t in valid if np.isfinite(len_u[t]) and len_u[t] > _HYPEREXT_EPS]
    lw = [len_w[t] for t in valid if np.isfinite(len_w[t]) and len_w[t] > _HYPEREXT_EPS]
    for seg in (lu, lw):
        if seg and (max(seg) / min(seg)) > _SEGMENT_RATIO_MAX:
            return None

    # 과신전 판정 — 부호가 calibration 과 반대 AND 중립 초과분 > floor.
    amounts = []
    for t in valid:
        amount = max(0.0, 180.0 - included[t])
        reversed_sign = (1.0 if signed[t] > 0 else -1.0) == -s_flex
        if reversed_sign and amount > floor:
            amounts.append(amount)
    # GATE (c) 단일 프레임 노이즈 — 윈도우 다수가 일치해야 함 (한 스파이크 무시).
    if len(amounts) <= _HYPEREXT_MAJORITY * len(valid):
        return None

    amount = float(np.median(amounts))
    if amount >= _HYPEREXT_SEVERITY_HIGH_DEG:
        severity = "high"
    elif amount >= _HYPEREXT_SEVERITY_MEDIUM_DEG:
        severity = "medium"
    else:
        severity = "low"
    return amount, severity


def _joint_hyperextension_flags(*, angles, keypoints_4ch, fsr, profile) -> list[SafetyFlag]:
    """D-05 발화 — 최대 4 hinge 후보 → ONE consolidated joint_hyperextension 플래그.

    keyword-only, plural 반환. angles+profile 은 공유 `dimensions._select_window` hold
    선택기를 구동해 window (s,e) → phase P 를 ONCE 산출하기 위해 필수다 (keypoints 만
    으론 window 불가 — review HIGH round-5). 각 후보는 cross-product 방향 검출 + per-
    branch fail-conservative 게이트(used keypoint 스코프) + D-02 joint-local·phase-co-
    located 통제 상실 AND-gate 를 통과해야 한다. multi-joint 는 worst severity + 고정
    tie-break(left_knee,right_knee,left_elbow,right_elbow)로 ONE 플래그로 합친다.
    """
    if keypoints_4ch is None or angles is None:
        return []
    kp = np.asarray(keypoints_4ch, dtype=float)
    ang = np.asarray(angles, dtype=float)
    if kp.ndim != 3 or kp.shape[0] == 0 or ang.ndim != 2 or ang.shape[0] == 0:
        return []
    # FRAME-ALIGN GUARD — angles 에서 도출한 window 인덱스가 keypoints 를 유효하게
    # 인덱싱하려면 두 배열의 row 수가 같아야 한다 (face-keypoint NaN 은 여기서 검사 X —
    # scoped 게이트 (h) 담당).
    if kp.shape[0] != ang.shape[0]:
        return []

    # WINDOW ONCE — 공유 selector (drift 금지, 10-02 trunk helper 와 동일 호출).
    from . import dimensions  # lazy import.

    try:
        _sliced, (s, e) = dimensions._select_window(angles, profile)
    except Exception:
        return []
    P = _phase_for_window(getattr(fsr, "phase_boundaries", None), s, e)
    if P is None:
        return []

    candidates: list[tuple[str, float, str]] = []
    for joint_key in _HINGE_ORDER:
        try:
            cand = _hyperextension_candidate(kp, s, e, joint_key)
        except Exception:
            cand = None
        if cand is None:
            continue
        amount, severity = cand
        if not _control_loss_for_joint(fsr, joint_key, phase=P):
            continue
        candidates.append((joint_key, amount, severity))
    if not candidates:
        return []

    # MULTI-JOINT CONSOLIDATION — worst by (severity desc, then FIXED hinge order asc).
    candidates.sort(key=lambda c: (-_SEVERITY_RANK[c[2]], _HINGE_ORDER.index(c[0])))
    joint_key, amount, severity = candidates[0]
    label = _HINGE_LABEL_KO[joint_key]
    confidence = getattr(fsr, "overall_confidence", None) or "low"
    return [
        SafetyFlag(
            flag_type="joint_hyperextension",
            body_region="무릎·팔꿈치",
            severity=severity,
            posture_condition=(
                f"{label} 역꺾임(과신전) 중립 대비 {amount:.0f}° 초과 (phase={P})"
            ),
            control_loss_signal=f"{P} 구간 {label} 통제 흔들림 (joint-local)",
            confidence=confidence,
            mode_scope="both",
        )
    ]


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
    try:
        asymmetry = _asymmetry_flag(angles, reference_angles, fsr, profile)
    except Exception:
        asymmetry = None
    flags = [f for f in (trunk, asymmetry) if f is not None]
    # D-05 관절 과신전 — list 반환이라 extend (trunk/asymmetry 는 singular append).
    try:
        flags.extend(
            _joint_hyperextension_flags(
                angles=angles,
                keypoints_4ch=keypoints_4ch,
                fsr=fsr,
                profile=profile,
            )
        )
    except Exception:
        pass
    # D-06 레벨 대비 무리 — Mode 1 전용 (singular append).
    try:
        level = _level_mismatch_flag(mode, experience, reference_level, fsr)
    except Exception:
        level = None
    if level is not None:
        flags.append(level)
    return flags
