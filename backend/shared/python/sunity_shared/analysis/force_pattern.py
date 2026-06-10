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

from dataclasses import dataclass, field
from typing import Literal

from .force_signals import (  # noqa: F401 — _MOTION_PHASES re-uses Phase 8 source
    MetricConfidence,
    MotionPhase,
    _MOTION_PHASES,
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
]
