"""Plan 08-01 Task 3 — 3-way contract lockstep drift defense (REVIEWS Cycle 1 반영).

TS analysis.ts ↔ Python models.py placeholder ↔ docs/contract.md §9 — Phase 8
ForceSignalsReport schema 박제 필드 grep 검증.

REVIEWS Cycle 1 신설 필드 박제 검증:
  R1/R2: coordinateSpace + scaleDenominator (AxisDeviationMetric)
  R3:    estimatedStable nullable + measurementKind + distanceToPoleNorm +
         nearPoleRatio + lostNearPoleAtMs (ContactStabilityMetric)
  R4:    preflightLabelGatePassed (PhaseBoundary)
  R5:    jerkUnit='deg_per_sec_cubed' (StabilityMetric)
  Cycle 2 §3 MEDIUM: preflight_gate_pending warning code

per Plan 07-01 lockstep 패턴 정합 + Plan 08-00 박제 contract 위에 박제.
"""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_PATH = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_PY_MODELS_PATH = (
    _REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "models.py"
)
_CONTRACT_PATH = _REPO_ROOT / "docs" / "contract.md"


# (ts_field, py_or_doc_field, label) — TS / Python placeholder / docs §9 모두 grep 검증.
_FIELD_MAP: list[tuple[str, str, str]] = [
    # ── 5 type alias ──
    ("MotionPhase", "MotionPhase", "type alias"),
    ("DeviationDirection", "DeviationDirection", "type alias"),
    ("SeverityLevel", "SeverityLevel", "type alias"),
    ("MetricConfidence", "MetricConfidence", "type alias"),
    ("ContactPoint", "ContactPoint", "type alias"),
    # ── 5 interface/dataclass 이름 ──
    ("PhaseBoundary", "PhaseBoundary", "dataclass"),
    ("AxisDeviationMetric", "AxisDeviationMetric", "dataclass"),
    ("StabilityMetric", "StabilityMetric", "dataclass"),
    ("ContactStabilityMetric", "ContactStabilityMetric", "dataclass"),
    ("ForceSignalsReport", "ForceSignalsReport", "dataclass"),
    # ── AnalysisResult field ──
    ("forceSignalsReport", "forceSignalsReport", "AnalysisResult field"),
    # ── camelCase ↔ snake_case 박제 ──
    ("phaseBoundaries", "phase_boundaries", "camelCase ↔ snake_case"),
    ("axisMetrics", "axis_metrics", "camelCase ↔ snake_case"),
    ("stabilityMetrics", "stability_metrics", "camelCase ↔ snake_case"),
    ("contactMetrics", "contact_metrics", "camelCase ↔ snake_case"),
    ("overallConfidence", "overall_confidence", "camelCase ↔ snake_case"),
    ("startFrameIdx", "start_frame_idx", "camelCase ↔ snake_case"),
    ("endFrameIdx", "end_frame_idx", "camelCase ↔ snake_case"),
    ("startMs", "start_ms", "camelCase ↔ snake_case"),
    ("endMs", "end_ms", "camelCase ↔ snake_case"),
    ("shoulderTilt", "shoulder_tilt", "camelCase ↔ snake_case"),
    ("hipTilt", "hip_tilt", "camelCase ↔ snake_case"),
    ("jitterScore", "jitter_score", "camelCase ↔ snake_case"),
    ("jerkScore", "jerk_score", "camelCase ↔ snake_case"),
    ("holdStabilityScore", "hold_stability_score", "camelCase ↔ snake_case"),
    ("unstableBodyParts", "unstable_body_parts", "camelCase ↔ snake_case"),
    ("contactPoint", "contact_point", "camelCase ↔ snake_case"),
    # ── REVIEWS Cycle 1 신설 필드 ──
    # Phase 8.1 박제 (Plan 08.1-00 Wave 0, D-01): coordinateSpace / scaleDenominator
    # / deviationDirection / pelvisDistanceFromPoleAxis / chestDistanceFromPoleAxis
    # 5 entry 영구 제거 (AxisDeviationMetric distance 차원 hard break). coordinateSpace
    # 는 ContactStabilityMetric (§9.5) 에서 사용 유지 → camelCase mirror entry 보존.
    ("coordinateSpace", "coordinate_space", "REVIEWS R1 (ContactStabilityMetric 박제 유지)"),
    ("measurementKind", "measurement_kind", "REVIEWS R3"),
    ("preflightLabelGatePassed", "preflight_label_gate_passed", "REVIEWS R4"),
    ("jerkUnit", "jerk_unit", "REVIEWS R5"),
    ("estimatedStable", "estimated_stable", "v1 박제"),
    ("distanceToPoleNorm", "distance_to_pole_norm", "REVIEWS R3 신설"),
    ("nearPoleRatio", "near_pole_ratio", "REVIEWS R3 신설"),
    ("lostNearPoleAtMs", "lost_near_pole_at_ms", "REVIEWS R3 — lostContactAtMs 명칭 변경"),
    # ── warning code enum (기존 13 + Cycle 1 신설 5 + Cycle 2 신설 1 + Phase 8.1 신설 2) ──
    # Phase 8.1 박제 (Plan 08.1-00 Wave 0): coordinate_space_unavailable 박제 제거 +
    # axis_metric_transitional / phase_8_1_wave_0_transitional 박제 신설 (C-B1/C-H1).
    ("pole_line_missing", "pole_line_missing", "warning code REVIEWS R1"),
    ("scale_unavailable", "scale_unavailable", "warning code REVIEWS R2"),
    ("preflight_label_gate_failed", "preflight_label_gate_failed", "warning code REVIEWS R4"),
    ("preflight_gate_pending", "preflight_gate_pending", "warning code REVIEWS Cycle 2 §3 MEDIUM"),
    ("fps_normalization_applied", "fps_normalization_applied", "warning code REVIEWS R5"),
    ("contact_evidence_only", "contact_evidence_only", "warning code REVIEWS R3"),
]


def test_ts_interface_has_all_fields() -> None:
    src = _TS_PATH.read_text(encoding="utf-8")
    missing = [
        (ts_field, label)
        for ts_field, _py, label in _FIELD_MAP
        if ts_field not in src
    ]
    assert not missing, (
        "TS analysis.ts 에 Phase 8 신설 필드 누락:\n"
        + "\n".join(f"  - {f} ({label})" for f, label in missing)
    )


def test_python_placeholder_has_all_fields() -> None:
    """Python placeholder = forward-declare 주석. Plan 08-02 가 실제 import 활성화 시 grep 유지."""
    src = _PY_MODELS_PATH.read_text(encoding="utf-8")
    missing = [
        (py_field, label)
        for _ts, py_field, label in _FIELD_MAP
        if py_field not in src
    ]
    assert not missing, (
        "Python models.py placeholder 에 Phase 8 신설 필드 누락:\n"
        + "\n".join(f"  - {f} ({label})" for f, label in missing)
    )


def test_contract_md_has_all_fields() -> None:
    """docs/contract.md §9 에 ts_field 또는 py_field 둘 중 하나라도 등장."""
    src = _CONTRACT_PATH.read_text(encoding="utf-8")
    missing = [
        (ts_field, py_field, label)
        for ts_field, py_field, label in _FIELD_MAP
        if ts_field not in src and py_field not in src
    ]
    assert not missing, (
        "docs/contract.md §9 에 Phase 8 신설 필드 누락:\n"
        + "\n".join(f"  - {ts} / {py} ({label})" for ts, py, label in missing)
    )
