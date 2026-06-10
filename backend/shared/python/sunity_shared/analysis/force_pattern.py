"""ForceDirectionPattern 추론 layer (Phase 9 D-09-A1~U6).

Schema only — 본체 함수 (`infer_force_direction_pattern`) + 6 signal detector +
Top-3 ranking + 18 canned KO interpretation 은 Wave 1 (Plan 09-02) 박제.

force_signals.py (Phase 8/8.1 진단 신호) 와 분리된 신설 모듈
(D-08-C3 패턴 정합). Pure function + numpy only (Layer 2 영구 차단 — D-09-C1).

Phase 9 책임 경계:
  - 산출: 6 signal × 5 phase 후보 → Top-3 ForcePatternFinding 카드 (Wave 1)
  - 영역 X: 자연어 풍부화 (Phase 11) / 영상 위 오버레이 (Phase 12) / 부상 위험 (Phase 10)

3-way contract lockstep (D-09-U1): TS `app/src/types/analysis.ts` ↔ 본 모듈 ↔
`docs/contract.md §9.11` 단일 atomic commit.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Literal

from .force_signals import (  # noqa: F401 — _MOTION_PHASES re-uses Phase 8 source
    AxisDeviationMetric,
    ContactStabilityMetric,
    ForceSignalsReport,
    JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED,
    JITTER_SEVERITY_THRESHOLDS,
    MetricConfidence,
    MotionPhase,
    PhaseBoundary,
    StabilityMetric,
    _MOTION_PHASES,
)
from .force_pattern_copy import (
    fallback_body,
    force_pattern_canned_text,
    joint_hint_for,
)


# ── Literal aliases (D-09-D1) ─────────────────────────────────────────────

ForceDirectionPattern = Literal[
    "pull", "push", "brace", "rotate", "release", "unknown"
]
"""6 force direction pattern enum — research 02 §4.1 정합. v1 scope:
- `rotate` = enum 박제만, 자동 검출 X (angular velocity 별도 산출 필요 — v2).
- `unknown` = 6 signal 모두 미통과 시 fallback (D-09-B4).
"""

ForceSourceSignal = Literal[
    "axis_tilt",
    "pelvis_drop",
    "late_contact",
    "high_jitter",
    "high_jerk",
    "abnormal_release",
]
"""6 source signal enum — D-09-A1 v1 scope (어깨 elevation / elbow lock 절대 joint
angle 패턴은 v2 deferred)."""

ModeContext = Literal["mode1", "mode3_first", "mode3_progress"]
"""3 mode context — D-09-D6. pipeline `_process` 가 `_mode3_comparison.isFirst`
재사용 (Phase 12.5 패턴)."""


# ── 검증 frozensets ───────────────────────────────────────────────────────

_FORCE_PATTERNS: frozenset[str] = frozenset(
    {"pull", "push", "brace", "rotate", "release", "unknown"}
)
_FORCE_SOURCE_SIGNALS: frozenset[str] = frozenset(
    {
        "axis_tilt",
        "pelvis_drop",
        "late_contact",
        "high_jitter",
        "high_jerk",
        "abnormal_release",
    }
)
_MODE_CONTEXTS: frozenset[str] = frozenset(
    {"mode1", "mode3_first", "mode3_progress"}
)
_METRIC_CONFIDENCES: frozenset[str] = frozenset({"low", "medium", "high"})


# ── Wave 1 ranking 상수 (D-09-B2 / D-09-B3) ───────────────────────────────
#
# Wave 1 (Plan 09-02) 의 본체 함수가 ranking score / tie-break 산출 시 사용.
# Wave 0 시점 박제 이유: schema lockstep + 단위 test 가 본 상수의 존재를
# 참조 가능 (drift 차단).

_PHASE_PRIORITY: dict[str, int] = {
    # 낮은 값 = 높은 우선 (lock = 자세 형성 결정 구간).
    "lock": 0,
    "hold": 1,
    "transition": 2,
    "final_shape": 3,
    "entry": 4,
}

_SIGNAL_PRIORITY: dict[str, int] = {
    # axis > contact > stability (도메인 객관성 순서, D-09-B3).
    "axis_tilt": 0,
    "pelvis_drop": 0,
    "abnormal_release": 1,
    "late_contact": 1,
    "high_jerk": 2,
    "high_jitter": 2,
}

_SIGNAL_WEIGHT: dict[str, float] = {
    # D-09-B2 — score = confidence × signal_weight.
    # abnormal_release 가 release 직접 신호로 priority 가장 높음.
    "axis_tilt": 1.0,
    "pelvis_drop": 1.0,
    "late_contact": 0.95,
    "abnormal_release": 1.1,
    "high_jerk": 0.85,
    "high_jitter": 0.80,
}

_BASE_CONFIDENCE: dict[str, float] = {
    # D-09-A5 — research §8 정합. base × phase_metric_confidence_factor → [0, 1].
    "axis_tilt": 0.72,
    "pelvis_drop": 0.72,
    "late_contact": 0.70,
    "high_jitter": 0.63,
    "high_jerk": 0.63,
    "abnormal_release": 0.75,
}

_CONFIDENCE_TO_FACTOR: dict[str, float] = {
    # RESEARCH Pitfall 4 — Phase 8 RELIABILITY_WEIGHT 동일 매핑 (drift 차단).
    # 'low'/'medium'/'high' enum → float factor.
    "low": 0.3,
    "medium": 0.7,
    "high": 1.0,
}

# D-09-C2 — motion_id 인식 시 confidence × _MOTION_ID_BOOST, cap 1.0.
_MOTION_ID_BOOST: float = 1.05

# RESEARCH Open Q 2 — IPSF tolerance 20° fixed const (Aerial Pole CoP Page 63 S55).
# Wave 1 axis_tilt detection 임계는 `force_signals._get_tilt_thresholds()` 가
# operational source — 본 상수는 RESEARCH 정합 기록 목적 (lookup table 동행).
_IPSF_TOLERANCE_DEG: float = 20.0


# ── frozen dataclass (D-09-U3) ────────────────────────────────────────────


@dataclass(frozen=True)
class ForcePatternFinding:
    """Phase 9 Top-3 finding 카드 1건 (D-09-D1 — 8 필드).

    Phase 8 frozen dataclass 박제 패턴 정합 (force_signals.AxisDeviationMetric 등).

    필드:
      pattern: ForceDirectionPattern (D-09-A1 매핑).
      phase: MotionPhase — force_signals._MOTION_PHASES 정합.
      source_signal: ForceSourceSignal (D-09-A1 6 종 중 1).
      reason: EN 1 sentence — LLM input 용 (Phase 11 풍부화 source).
      interpretation: KO canned — D-09-D2 18 mapping, '가능성' 언어 (D-09-D3 grep gate).
      confidence: [0, 1] — D-09-A5 base × phase_metric_confidence_factor (motion_id
                  boost 적용 후).
      joint_hint: 부위 키워드 (코어 / 고관절 / 광배 / 내전근 / null) — D-09-D1.
      warnings: signal-specific list[str].
    """

    pattern: ForceDirectionPattern
    phase: MotionPhase
    source_signal: ForceSourceSignal
    reason: str
    interpretation: str
    confidence: float
    joint_hint: str | None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # enum 검증.
        if self.pattern not in _FORCE_PATTERNS:
            raise ValueError(
                f"pattern must be one of {_FORCE_PATTERNS}, got {self.pattern!r}"
            )
        if self.source_signal not in _FORCE_SOURCE_SIGNALS:
            raise ValueError(
                f"source_signal must be one of {_FORCE_SOURCE_SIGNALS}, "
                f"got {self.source_signal!r}"
            )
        # R1 iter-4 — phase 는 Phase 8 _MOTION_PHASES 정합 (downstream
        # _PHASE_PRIORITY[f.phase] KeyError 차단).
        if self.phase not in _MOTION_PHASES:
            raise ValueError(
                f"phase must be one of {_MOTION_PHASES}, got {self.phase!r}"
            )
        # numeric 검증.
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )
        # interpretation non-empty.
        if not isinstance(self.interpretation, str) or not self.interpretation:
            raise ValueError(
                "interpretation must be non-empty str (canned KO sentence)"
            )
        # joint_hint = str | None.
        if self.joint_hint is not None and not isinstance(self.joint_hint, str):
            raise ValueError(
                f"joint_hint must be str | None, got {type(self.joint_hint).__name__}"
            )
        # warnings = list[str] strict (R2 iter-3 empty str reject + R2 iter-4 tuple reject).
        if not isinstance(self.warnings, list):
            raise ValueError(
                f"warnings must be list (contract list[str]), "
                f"got {type(self.warnings).__name__}"
            )
        for i, w in enumerate(self.warnings):
            if not isinstance(w, str) or not w:
                raise ValueError(
                    f"warnings[{i}] must be non-empty str, "
                    f"got {type(w).__name__}={w!r}"
                )


@dataclass(frozen=True)
class ForcePatternInference:
    """Phase 9 추론 layer 의 단일 산출 (D-09-D1 — 5 필드).

    Firestore 저장 경로: `users/{uid}/analyses/{analysisId}.result.forcePatternInference`
    (D-09-U5). `_validate_force_pattern_inference` scoped validator 가 nested-array
    차단.

    필드 순서: non-default → default (Codex R1 회귀 가드 — Python dataclass rule
    상 default 이후 non-default 필드 금지).

    필드:
      version: "1.0" 초기 (non-empty).
      findings: ForcePatternFinding[] (Top-3, length [0, 3]). D-09-B4 fabrication 금지.
      overall_confidence: MetricConfidence — 0 finding 시 'low' + warning.
      mode_context: ModeContext — pipeline `_process` 산출 (D-09-D6).
      warnings: list[str] umbrella (예: 'no_significant_force_pattern_signal',
                'phase_unavailable_for_inference', 'axis_signal_unavailable').
    """

    version: str
    findings: list[ForcePatternFinding]
    overall_confidence: MetricConfidence
    mode_context: ModeContext
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # version non-empty (R6).
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be non-empty str")
        # mode_context enum.
        if self.mode_context not in _MODE_CONTEXTS:
            raise ValueError(
                f"mode_context must be one of {_MODE_CONTEXTS}, "
                f"got {self.mode_context!r}"
            )
        # overall_confidence enum.
        if self.overall_confidence not in _METRIC_CONFIDENCES:
            raise ValueError(
                f"overall_confidence must be one of {_METRIC_CONFIDENCES}, "
                f"got {self.overall_confidence!r}"
            )
        # findings = list[ForcePatternFinding] strict (R2 iter-4 tuple reject + R7
        # internal misuse 차단).
        if not isinstance(self.findings, list):
            raise ValueError(
                f"findings must be list (contract list[ForcePatternFinding]), "
                f"got {type(self.findings).__name__}"
            )
        if not all(isinstance(f, ForcePatternFinding) for f in self.findings):
            offenders = [
                (i, type(f).__name__)
                for i, f in enumerate(self.findings)
                if not isinstance(f, ForcePatternFinding)
            ]
            raise ValueError(
                f"findings element must be ForcePatternFinding instance, "
                f"got non-conforming: {offenders}"
            )
        # findings length cap (D-09-B4).
        if len(self.findings) > 3:
            raise ValueError(
                f"findings length must be in [0, 3] (D-09-B4 fabrication 금지), "
                f"got {len(self.findings)}"
            )
        # warnings = list[str] strict (Firestore scoped validator 와 동일 strictness).
        if not isinstance(self.warnings, list):
            raise ValueError(
                f"warnings must be list (contract list[str]), "
                f"got {type(self.warnings).__name__}"
            )
        for i, w in enumerate(self.warnings):
            if not isinstance(w, str) or not w:
                raise ValueError(
                    f"warnings[{i}] must be non-empty str, "
                    f"got {type(w).__name__}={w!r}"
                )


# ── Wave 1 inference body (D-09-A1~A5 / B1~B5 / C2 / D6) ──────────────────


# Axis warning surface — two-tier (R4 정합, verified against force_signals.py
# 1670-1677). force_signals 가 모든 axisMetric 의 'phase_8_1_wave_0_transitional'
# 동행 시 top-level 'axis_metric_transitional' emit.
_AXIS_IGNORE_WARNINGS_PER_METRIC: frozenset[str] = frozenset(
    {
        "phase_8_1_wave_0_transitional",
        "tilt_unavailable",
        "tilt_thresholds_fallback",
    }
)
"""per-axisMetric warnings — 검사 대상 = `axis.warnings`. hit 시 해당 phase
의 axis 계열 detector skip + umbrella warning emit."""

_AXIS_IGNORE_WARNINGS_REPORT: frozenset[str] = frozenset(
    {"axis_metric_transitional"}
)
"""top-level report warning — 검사 대상 = `force_signals_report.warnings`.
hit 시 모든 phase 의 axis 계열 detector 전체 차단."""

# Wave 1 의 phase iteration 순서 — _PHASE_PRIORITY 정합 (정렬 ASC). lock 가
# 최우선 (자세 형성 결정 구간).
_PHASE_ITERATION_ORDER: tuple[str, ...] = (
    "lock",
    "hold",
    "transition",
    "final_shape",
    "entry",
)


def _phase_metric_confidence_factor(
    axis: AxisDeviationMetric | None,
    stab: StabilityMetric | None,
) -> float:
    """D-09-A5 — cf = min(_CONFIDENCE_TO_FACTOR[axis.confidence],
    _CONFIDENCE_TO_FACTOR[stab.confidence]).

    axis or stab is None → fallback _CONFIDENCE_TO_FACTOR['low'] (=0.3) —
    never raise (RESEARCH Pitfall 4).

    R11 (conservative v1) — 본 global-min 룰은 contact-only / stability-only
    finding 도 axis 가 없으면 cf=0.3 으로 capped 시킨다. Phase 9 의 모든 finding
    이 "Phase 8 신호 신뢰도가 부분적이면 전체 신뢰도도 보수적" 도메인 가정.
    """
    low_factor = _CONFIDENCE_TO_FACTOR["low"]
    axis_factor = _CONFIDENCE_TO_FACTOR.get(
        axis.confidence if axis is not None else "low", low_factor
    )
    stab_factor = _CONFIDENCE_TO_FACTOR.get(
        stab.confidence if stab is not None else "low", low_factor
    )
    if axis is None:
        axis_factor = low_factor
    if stab is None:
        stab_factor = low_factor
    return min(axis_factor, stab_factor)


def _detect_axis_tilt(
    axis: AxisDeviationMetric | None,
    phase: MotionPhase,
    cf: float,
    mode_context: ModeContext,
) -> list[ForcePatternFinding]:
    """D-09-A1 — axis_tilt detection (max(shoulder, hip) > 20° IPSF tol).

    axis is None → []. per-metric warning ignore set hit → []. caller 가 이미
    상위 단계에서 axis warning 가드를 검사한다 (infer_force_direction_pattern).
    """
    if axis is None:
        return []
    if any(w in _AXIS_IGNORE_WARNINGS_PER_METRIC for w in axis.warnings):
        return []
    shoulder = axis.shoulder_tilt if axis.shoulder_tilt is not None else 0.0
    hip = axis.hip_tilt if axis.hip_tilt is not None else 0.0
    if max(shoulder, hip) > _IPSF_TOLERANCE_DEG:
        confidence = min(1.0, _BASE_CONFIDENCE["axis_tilt"] * cf)
        return [
            ForcePatternFinding(
                pattern="release",
                phase=phase,
                source_signal="axis_tilt",
                reason="Axis tilt exceeds IPSF tolerance (20°)",
                interpretation=force_pattern_canned_text(
                    "axis_tilt", mode_context
                ),
                confidence=confidence,
                joint_hint=joint_hint_for("axis_tilt"),
                warnings=[],
            )
        ]
    return []


def _detect_pelvis_drop(
    axis: AxisDeviationMetric | None,
    phase: MotionPhase,
    cf: float,
    mode_context: ModeContext,
) -> list[ForcePatternFinding]:
    """D-09-A1 — pelvis_drop: hip_tilt > 20° AND (hip - shoulder) > 10°.

    R4 (Codex iter-3) None guard — shoulder_tilt or hip_tilt is None → [].
    Phase 8.1 compute_axis_deviation 가 sample 부재 phase 에서 None 박제 가능
    (force_signals.py:1132-1153). guard 없을 시 TypeError raise.
    """
    if axis is None:
        return []
    if any(w in _AXIS_IGNORE_WARNINGS_PER_METRIC for w in axis.warnings):
        return []
    if axis.shoulder_tilt is None or axis.hip_tilt is None:
        # R4 None guard — TypeError 차단.
        return []
    hip = axis.hip_tilt
    shoulder = axis.shoulder_tilt
    if hip > _IPSF_TOLERANCE_DEG and (hip - shoulder) > 10.0:
        confidence = min(1.0, _BASE_CONFIDENCE["pelvis_drop"] * cf)
        return [
            ForcePatternFinding(
                pattern="release",
                phase=phase,
                source_signal="pelvis_drop",
                reason="Hip tilt drops below shoulder line by >10° while >20°",
                interpretation=force_pattern_canned_text(
                    "pelvis_drop", mode_context
                ),
                confidence=confidence,
                joint_hint=joint_hint_for("pelvis_drop"),
                warnings=[],
            )
        ]
    return []


def _detect_late_contact(
    contacts: list[ContactStabilityMetric],
    phase: MotionPhase,
    cf: float,
    mode_context: ModeContext,
) -> list[ForcePatternFinding]:
    """D-09-A1 — late_contact: phase='lock' only + estimated_stable=False OR
    near_pole_ratio < 0.5.

    여러 contact 매치 시 첫 번째 1개만 emit (D-09-B5 dedup 단계가 동일 phase
    중복 차단).
    """
    if phase != "lock":
        return []
    for cm in contacts:
        unstable = cm.estimated_stable is False
        far_from_pole = (
            cm.near_pole_ratio is not None and cm.near_pole_ratio < 0.5
        )
        if unstable or far_from_pole:
            confidence = min(1.0, _BASE_CONFIDENCE["late_contact"] * cf)
            return [
                ForcePatternFinding(
                    pattern="brace",
                    phase=phase,
                    source_signal="late_contact",
                    reason=(
                        "Lock-phase contact unstable or near_pole_ratio < 0.5"
                    ),
                    interpretation=force_pattern_canned_text(
                        "late_contact", mode_context
                    ),
                    confidence=confidence,
                    joint_hint=joint_hint_for("late_contact"),
                    warnings=[],
                )
            ]
    return []


def _detect_high_jitter(
    stab: StabilityMetric | None,
    phase: MotionPhase,
    cf: float,
    mode_context: ModeContext,
) -> list[ForcePatternFinding]:
    """D-09-A1 — high_jitter: jitter_score > JITTER_SEVERITY_THRESHOLDS[0] (=8.0)."""
    if stab is None or stab.jitter_score is None:
        return []
    if stab.jitter_score > JITTER_SEVERITY_THRESHOLDS[0]:
        confidence = min(1.0, _BASE_CONFIDENCE["high_jitter"] * cf)
        return [
            ForcePatternFinding(
                pattern="unknown",
                phase=phase,
                source_signal="high_jitter",
                reason="Jitter score exceeds medium threshold 8.0",
                interpretation=force_pattern_canned_text(
                    "high_jitter", mode_context
                ),
                confidence=confidence,
                joint_hint=joint_hint_for("high_jitter"),
                warnings=[],
            )
        ]
    return []


def _detect_high_jerk(
    stab: StabilityMetric | None,
    phase: MotionPhase,
    cf: float,
    mode_context: ModeContext,
) -> list[ForcePatternFinding]:
    """D-09-A1 — high_jerk: jerk_score > JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED[0]
    (=5000.0).
    """
    if stab is None or stab.jerk_score is None:
        return []
    if stab.jerk_score > JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED[0]:
        confidence = min(1.0, _BASE_CONFIDENCE["high_jerk"] * cf)
        return [
            ForcePatternFinding(
                pattern="unknown",
                phase=phase,
                source_signal="high_jerk",
                reason="Jerk score exceeds medium threshold 5000 deg/s^3",
                interpretation=force_pattern_canned_text(
                    "high_jerk", mode_context
                ),
                confidence=confidence,
                joint_hint=joint_hint_for("high_jerk"),
                warnings=[],
            )
        ]
    return []


def _detect_abnormal_release(
    contacts: list[ContactStabilityMetric],
    phase: MotionPhase,
    cf: float,
    mode_context: ModeContext,
) -> list[ForcePatternFinding]:
    """D-09-A1 — abnormal_release: contactMetric.warnings 안
    'abnormal_release_during_hold' 포함 시 1 finding emit.
    """
    for cm in contacts:
        warnings = cm.warnings or []
        if "abnormal_release_during_hold" in warnings:
            confidence = min(1.0, _BASE_CONFIDENCE["abnormal_release"] * cf)
            return [
                ForcePatternFinding(
                    pattern="release",
                    phase=phase,
                    source_signal="abnormal_release",
                    reason=(
                        "Contact lost during lock/hold phase "
                        "(abnormal_release_during_hold)"
                    ),
                    interpretation=force_pattern_canned_text(
                        "abnormal_release", mode_context
                    ),
                    confidence=confidence,
                    joint_hint=joint_hint_for("abnormal_release"),
                    warnings=[],
                )
            ]
    return []


def _apply_motion_id_boost(
    candidates: list[ForcePatternFinding],
) -> list[ForcePatternFinding]:
    """D-09-C2 / Pitfall 5 — motion_id 인식 시 confidence × _MOTION_ID_BOOST,
    cap 1.0. BEFORE ranking 적용 (score sort 가 boosted 값 반영).

    Frozen dataclass 라 dataclasses.replace 로 신규 instance 박제.
    """
    boosted: list[ForcePatternFinding] = []
    for c in candidates:
        new_conf = min(1.0, c.confidence * _MOTION_ID_BOOST)
        boosted.append(dataclasses.replace(c, confidence=new_conf))
    return boosted


def _overall_confidence_from_findings(
    findings: list[ForcePatternFinding],
) -> MetricConfidence:
    """top finding.confidence 기준 단순 매핑. Phase 8 패턴 정합."""
    if not findings:
        return "low"
    top = max(f.confidence for f in findings)
    if top >= 0.7:
        return "high"
    if top >= 0.4:
        return "medium"
    return "low"


def _rank_top3(
    candidates: list[ForcePatternFinding],
) -> list[ForcePatternFinding]:
    """Stub for T2 — T3 (Plan 09-02 Task 3) 가 본체 박제.

    Wave 1 T2 단위 test 는 ranking 무관 케이스 (단일 phase / 단일 signal /
    0-finding fallback / phase 미인식 / confidence 산식) 만 검증. Top-3 정렬 +
    tie-break + dedup 검증은 T3 의 책임.
    """
    return candidates[:3]


def infer_force_direction_pattern(
    force_signals_report: ForceSignalsReport,
    motion_id: str | None,
    mode_context: ModeContext,
) -> ForcePatternInference:
    """Layer 1 deterministic inference. D-09-A1~A5 / B1~B5 / C2 / D6 정합.

    Layer 2 (Gemini) 영구 차단 — D-09-C1.
    fabrication 금지 — 0 finding 시 빈 list + umbrella warning 만 (D-09-B4).
    raw signal only — axis severity 직접 trust 금지 (D-09-A2,
    test_force_pattern_no_severity_use.py 가 회귀 차단).
    """
    boundaries_by_phase: dict[str, PhaseBoundary] = {
        b.phase: b for b in force_signals_report.phase_boundaries
    }
    axis_by_phase: dict[str, AxisDeviationMetric] = {
        m.phase: m for m in force_signals_report.axis_metrics
    }
    stability_by_phase: dict[str, StabilityMetric] = {
        m.phase: m for m in force_signals_report.stability_metrics
    }
    contact_by_phase: dict[str, list[ContactStabilityMetric]] = {}
    for cm in force_signals_report.contact_metrics:
        contact_by_phase.setdefault(cm.phase, []).append(cm)

    umbrella_warnings: list[str] = []
    candidates: list[ForcePatternFinding] = []

    # R4 top-level report axis warning 가드. force_signals.py:1670-1677 가 모든
    # axisMetric 의 'phase_8_1_wave_0_transitional' 동행 시 top-level
    # 'axis_metric_transitional' emit. 그 경우 axis tier 전체 신뢰 X.
    report_axis_unavailable = any(
        w in _AXIS_IGNORE_WARNINGS_REPORT
        for w in (force_signals_report.warnings or [])
    )
    if report_axis_unavailable:
        umbrella_warnings.append("axis_signal_unavailable")

    for phase in _PHASE_ITERATION_ORDER:
        if phase not in boundaries_by_phase:
            if "phase_unavailable_for_inference" not in umbrella_warnings:
                umbrella_warnings.append("phase_unavailable_for_inference")
            continue

        axis = axis_by_phase.get(phase)
        stab = stability_by_phase.get(phase)
        contacts = contact_by_phase.get(phase, [])
        cf = _phase_metric_confidence_factor(axis, stab)

        # axis warning ignore 룰 hit 검사 — D-09-A2 / Pitfall 2 / R4 per-metric.
        # axis is None 이거나 per-metric warnings 무시 set 와 교차 시 axis
        # 계열 detector skip + umbrella warning emit. 또한 top-level report 가
        # unavail 이면 모든 phase 의 axis 도 차단.
        per_metric_blocked = axis is None or any(
            w in _AXIS_IGNORE_WARNINGS_PER_METRIC for w in axis.warnings
        )
        axis_blocked = report_axis_unavailable or per_metric_blocked
        if axis is not None and per_metric_blocked:
            if "axis_signal_unavailable" not in umbrella_warnings:
                umbrella_warnings.append("axis_signal_unavailable")

        if not axis_blocked:
            candidates.extend(
                _detect_axis_tilt(axis, phase, cf, mode_context)
            )
            candidates.extend(
                _detect_pelvis_drop(axis, phase, cf, mode_context)
            )

        candidates.extend(
            _detect_late_contact(contacts, phase, cf, mode_context)
        )
        candidates.extend(_detect_high_jitter(stab, phase, cf, mode_context))
        candidates.extend(_detect_high_jerk(stab, phase, cf, mode_context))
        candidates.extend(
            _detect_abnormal_release(contacts, phase, cf, mode_context)
        )

    # D-09-C2 motion_id boost — BEFORE ranking (Pitfall 5).
    if motion_id is not None:
        candidates = _apply_motion_id_boost(candidates)

    # Ranking + tie-break + dedup — T3 가 본체 박제. T2 stub: slice top-3
    # unsorted.
    findings = _rank_top3(candidates)

    if not findings:
        umbrella_warnings.append("no_significant_force_pattern_signal")
        overall: MetricConfidence = "low"
    else:
        overall = _overall_confidence_from_findings(findings)

    return ForcePatternInference(
        version="1.0",
        findings=findings,
        overall_confidence=overall,
        mode_context=mode_context,
        warnings=umbrella_warnings,
    )


__all__ = [
    "ForceDirectionPattern",
    "ForceSourceSignal",
    "ModeContext",
    "ForcePatternFinding",
    "ForcePatternInference",
    "_FORCE_PATTERNS",
    "_FORCE_SOURCE_SIGNALS",
    "_MODE_CONTEXTS",
    "_PHASE_PRIORITY",
    "_SIGNAL_PRIORITY",
    "_SIGNAL_WEIGHT",
    "_BASE_CONFIDENCE",
    "_CONFIDENCE_TO_FACTOR",
    "_MOTION_ID_BOOST",
    "_IPSF_TOLERANCE_DEG",
    "_AXIS_IGNORE_WARNINGS_PER_METRIC",
    "_AXIS_IGNORE_WARNINGS_REPORT",
    "infer_force_direction_pattern",
    "fallback_body",
]
