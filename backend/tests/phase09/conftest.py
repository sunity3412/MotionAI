"""Phase 09 단위 테스트 공통 fixture — Phase 8 frozen dataclass 직접 instantiate.

D-09-D1 / D-09-U3 / RESEARCH Open Q 4 정합 — Wave 0 부터 Wave 1 모든 test 가
공통으로 쓰는 factory helper 5 개. Phase 8 dataclass 의 __post_init__ 검증을
통과하려면 verified field signatures (force_signals.py:330-352, 355-397, 400-436,
440-490, 493-514) 와 1:1 매칭 강제.

R1 (Codex iteration-3) — factory signature 가 Phase 8 dataclass 의 actual
constructor 와 일치하지 않으면 ValueError 가 __post_init__ 단계에서 raise 되어
Phase 9 logic 자체 가 시험 못 됨. 본 conftest 는 그 위험을 한 곳에서 차단한다.

주의:
  - PhaseBoundary.source ∈ {"heuristic", "gemini_assisted", "heuristic_fallback"} —
    'pose' 같은 임의 값 InValidationError.
  - ContactStabilityMetric 의 class name 은 'ContactStabilityMetric' (Phase 8
    verified) — 'ContactMetric' 같은 줄임표 X.
  - StabilityMetric.jerk_unit 은 항상 'deg_per_sec_cubed' (단일 enum) — REVIEWS R5.
"""

from __future__ import annotations

from sunity_shared.analysis import force_signals as fs


def _make_phase_boundary(
    *,
    phase: str = "lock",
    start_frame_idx: int = 0,
    end_frame_idx: int = 10,
    start_ms: int = 0,
    end_ms: int = 1000,
    confidence: str = "high",
    source: str = "heuristic",
    preflight_label_gate_passed: bool | None = None,
) -> fs.PhaseBoundary:
    """Phase 8 PhaseBoundary frozen dataclass — D-09-A4 phase 미인식 fallback 테스트 source.

    source MUST be one of force_signals._PHASE_SOURCES = {"heuristic",
    "gemini_assisted", "heuristic_fallback"} — Phase 8 enum, 'pose' 등 임의 값
    ValueError.
    """
    return fs.PhaseBoundary(
        phase=phase,
        start_frame_idx=start_frame_idx,
        end_frame_idx=end_frame_idx,
        start_ms=start_ms,
        end_ms=end_ms,
        confidence=confidence,
        source=source,
        preflight_label_gate_passed=preflight_label_gate_passed,
    )


def _make_axis_metric(
    *,
    phase: str = "lock",
    shoulder_tilt: float | None = 10.0,
    hip_tilt: float | None = 10.0,
    confidence: str = "high",
    warnings: tuple[str, ...] = (),
    severity: str = "low",
    tilt_unavailable: bool = False,
) -> fs.AxisDeviationMetric:
    """Phase 8.1 AxisDeviationMetric frozen dataclass — D-09-A2 raw signal source.

    severity 인자는 Phase 8 dataclass __post_init__ 통과용 — Phase 9 detection
    coverage 가 axis severity 직접 trust 영구 차단 (D-09-A2 / RESEARCH Anti-Pattern).
    Test 는 raw shoulder_tilt + hip_tilt + warnings 만 검증.

    tilt_unavailable=True 시 R4 None-guard 테스트용 transitional 표식 박제:
    shoulder_tilt=None / hip_tilt=None / warnings=('phase_8_1_wave_0_transitional',).
    """
    if tilt_unavailable:
        shoulder_tilt = None
        hip_tilt = None
        warnings = ("phase_8_1_wave_0_transitional",)
    return fs.AxisDeviationMetric(
        phase=phase,
        shoulder_tilt=shoulder_tilt,
        hip_tilt=hip_tilt,
        severity=severity,
        confidence=confidence,
        warnings=list(warnings),
    )


def _make_stability_metric(
    *,
    phase: str = "lock",
    jitter_score: float = 0.0,
    jerk_score: float = 0.0,
    jerk_unit: str = "deg_per_sec_cubed",
    hold_stability_score: float | None = None,
    unstable_body_parts: tuple[str, ...] = (),
    severity: str = "low",
    confidence: str = "high",
    warnings: tuple[str, ...] = (),
) -> fs.StabilityMetric:
    """Phase 8 StabilityMetric frozen dataclass — D-09-A1 high_jitter/high_jerk source.

    jerk_unit MUST be 'deg_per_sec_cubed' — Phase 8 enum (REVIEWS R5 FPS-normalized).
    """
    return fs.StabilityMetric(
        phase=phase,
        jitter_score=jitter_score,
        jerk_score=jerk_score,
        jerk_unit=jerk_unit,
        hold_stability_score=hold_stability_score,
        unstable_body_parts=list(unstable_body_parts),
        severity=severity,
        confidence=confidence,
        warnings=list(warnings),
    )


def _make_contact_metric(
    *,
    phase: str = "lock",
    contact_point: str = "left_hand",
    measurement_kind: str | None = "keypoint",
    estimated_stable: bool | None = True,
    distance_to_pole_norm: float | None = None,
    near_pole_ratio: float | None = 1.0,
    lost_near_pole_at_ms: int | None = None,
    coordinate_space: str = "image_2d",
    severity: str = "low",
    confidence: str = "high",
    warnings: tuple[str, ...] = (),
) -> fs.ContactStabilityMetric:
    """Phase 8 ContactStabilityMetric frozen dataclass (class name verified).

    Phase 8 dataclass 의 11 필드 모두 박제 — measurement_kind ∈ {keypoint, segment,
    region_proxy, None}. coordinate_space ∈ {image_2d, pole_aligned, world_3d,
    unavailable}.

    abnormal_release 검출 테스트 시 warnings=('abnormal_release_during_hold',)
    박제 shortcut.
    """
    return fs.ContactStabilityMetric(
        phase=phase,
        contact_point=contact_point,
        measurement_kind=measurement_kind,
        estimated_stable=estimated_stable,
        distance_to_pole_norm=distance_to_pole_norm,
        near_pole_ratio=near_pole_ratio,
        lost_near_pole_at_ms=lost_near_pole_at_ms,
        coordinate_space=coordinate_space,
        severity=severity,
        confidence=confidence,
        warnings=list(warnings),
    )


def _make_force_signals_report(
    *,
    version: str = "1.0",
    overall_confidence: str = "low",
    warnings: tuple[str, ...] = (),
    phase_boundaries: tuple = (),
    axis_metrics: tuple = (),
    stability_metrics: tuple = (),
    contact_metrics: tuple = (),
) -> fs.ForceSignalsReport:
    """Phase 8 ForceSignalsReport umbrella — Phase 9 inference 의 단일 입력 source."""
    return fs.ForceSignalsReport(
        version=version,
        overall_confidence=overall_confidence,
        warnings=list(warnings),
        phase_boundaries=list(phase_boundaries),
        axis_metrics=list(axis_metrics),
        stability_metrics=list(stability_metrics),
        contact_metrics=list(contact_metrics),
    )
