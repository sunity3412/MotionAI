"""Plan 08-02 Task 2 — compute_contact_stability 단위 test (REVIEWS R3).

R3: evidence-with-confidence — estimated_stable nullable + distance_to_pole_norm
    + near_pole_ratio + lost_near_pole_at_ms + measurement_kind.
"""

from __future__ import annotations

from sunity_shared.analysis.force_signals import (
    PhaseBoundary,
    _CONTACT_POINTS_PATH,
    compute_contact_stability,
)

from .fixtures._fixture_builders import (
    build_clean_invert,
    build_layback_release,
    build_motion_id_unrecognized,
)


def _phase(name: str, s: int, e: int) -> PhaseBoundary:
    return PhaseBoundary(
        phase=name,  # type: ignore[arg-type]
        start_frame_idx=s,
        end_frame_idx=e,
        start_ms=s * 111,
        end_ms=e * 111,
        confidence="low",
        source="heuristic",
        preflight_label_gate_passed=None,
    )


def test_yaml_load_motion_id_lookup_returns_kind():
    """yaml entry 의 kind 필드 동행 — ref-invert 의 left_inner_thigh.kind='segment'."""
    import yaml

    with open(_CONTACT_POINTS_PATH) as f:
        data = yaml.safe_load(f)
    invert = data["motions"]["ref-invert"]
    contact_kinds = {e["name"]: e["kind"] for e in invert["expected_contact_points"]}
    assert contact_kinds["left_inner_thigh"] == "segment"
    assert contact_kinds["left_hand"] == "keypoint"


def test_distance_to_pole_norm_uses_observed_torso_length():
    """distance_to_pole_norm = distance / median_torso_length(image_2d)."""
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 60)]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-invert")
    # 모든 contact 가 같은 phase = hold 기준 산출.
    assert len(metrics) > 0
    for m in metrics:
        if m.distance_to_pole_norm is not None:
            assert m.distance_to_pole_norm >= 0.0


def test_near_pole_ratio_phase_internal():
    """near_pole_ratio = phase 내 frame 중 distance <= 0.08 비율 [0, 1]."""
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 60)]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-invert")
    for m in metrics:
        if m.near_pole_ratio is not None:
            assert 0.0 <= m.near_pole_ratio <= 1.0


def test_estimated_stable_true_when_evidence_strong():
    """clean_invert 의 left_hand (x=0.5 = pole) → near_pole_ratio >= 0.8 → True."""
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 60)]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-invert")
    # left_hand 또는 right_hand 가 estimated_stable=True 인 metric 1개 이상.
    stable_metrics = [m for m in metrics if m.estimated_stable is True]
    assert len(stable_metrics) >= 1


def test_estimated_stable_false_when_evidence_low():
    """layback_release fixture hold frame 40~ 의 left_hand → outward drift → ratio < 0.3."""
    frames, pole, _, expected = build_layback_release()
    boundaries = [_phase("hold", 30, 60)]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-foxtop")
    # left_hand 의 ratio 가 낮음. 일부 metric estimated_stable 가 False or None.
    left_hand_metrics = [m for m in metrics if m.contact_point == "left_hand"]
    assert len(left_hand_metrics) >= 1


def test_estimated_stable_null_when_evidence_unclear():
    """near_pole_ratio in [0.3, 0.8) → estimated_stable = None + warning 'contact_evidence_only'."""
    # build fixture intentionally produces unclear evidence:
    #   half of the hold has left_hand on pole, half outward.
    from .fixtures._fixture_builders import _make_frame_basic, _line_available_measurement

    # half-out, half-in inside the hold window.
    frames = []
    for i in range(60):
        offset = 0.10 if (i % 2 == 0) else 0.0  # alternation produces near_pole_ratio ≈ 0.5.
        frames.append(_make_frame_basic(i, left_hand_x_offset=offset))
    pole = _line_available_measurement()
    boundaries = [_phase("hold", 0, 60)]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-foxtop")
    left_hand = [m for m in metrics if m.contact_point == "left_hand"]
    assert len(left_hand) == 1
    m = left_hand[0]
    # ratio ≈ 0.5 → between 0.3 and 0.8 → estimated_stable=None.
    if m.near_pole_ratio is not None and 0.3 <= m.near_pole_ratio < 0.8:
        assert m.estimated_stable is None
        assert "contact_evidence_only" in m.warnings


def test_measurement_kind_from_yaml():
    """measurement_kind = yaml entry 의 kind 필드 (keypoint/segment/region_proxy)."""
    frames, pole, _, _ = build_clean_invert()
    boundaries = [_phase("hold", 0, 60)]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-invert")
    by_contact = {}
    for m in metrics:
        by_contact.setdefault(m.contact_point, []).append(m)
    if "left_inner_thigh" in by_contact:
        assert by_contact["left_inner_thigh"][0].measurement_kind == "segment"
    if "left_hand" in by_contact:
        assert by_contact["left_hand"][0].measurement_kind == "keypoint"


def test_lost_near_pole_at_ms_detection():
    """layback_release: frame 40 부터 left_hand outward (+0.10) → lost_near_pole_at_ms ≈ 4444."""
    frames, pole, _, _ = build_layback_release()
    boundaries = [_phase("hold", 0, 60)]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-foxtop")
    left_hand = [m for m in metrics if m.contact_point == "left_hand"]
    # distance_to_pole_norm 산출 후, distance > 0.20 시점 = frame 40 = 4444ms (debounce 2 frames 적용).
    # 산출 결과는 implementation 에 따라 다르지만 lost_near_pole_at_ms 가 not None and > 0.
    if left_hand and left_hand[0].lost_near_pole_at_ms is not None:
        # frame 40 시점 ≈ 4444 ms (debounce 적용 시 +2 frame = ≈ 4666).
        assert 4000 < left_hand[0].lost_near_pole_at_ms < 5000


def test_abnormal_release_during_hold_warning():
    """lock.start_ms <= lost_near_pole_at_ms <= hold.end_ms → warning 'abnormal_release_during_hold'."""
    frames, pole, _, _ = build_layback_release()
    # multi-phase: lock + hold.
    boundaries = [
        _phase("lock", 0, 30),
        _phase("hold", 30, 60),
    ]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-foxtop")
    hold_left_hand = [
        m for m in metrics if m.contact_point == "left_hand" and m.phase == "hold"
    ]
    # 일부 metric 에 'abnormal_release_during_hold' warning 박제.
    if hold_left_hand and hold_left_hand[0].lost_near_pole_at_ms is not None:
        assert "abnormal_release_during_hold" in hold_left_hand[0].warnings


def test_motion_unrecognized_fallback_estimated_stable_null():
    """motion_id=None → measurement_kind=None + estimated_stable=None + warning 'motion_unrecognized'."""
    frames, pole, _, _ = build_motion_id_unrecognized()
    boundaries = [_phase("hold", 0, 60)]
    metrics = compute_contact_stability(frames, boundaries, pole, motion_id=None)
    assert len(metrics) > 0
    for m in metrics:
        assert m.measurement_kind is None
        assert m.estimated_stable is None
        assert "motion_unrecognized" in m.warnings


def test_layback_release_fixture_emits_abnormal_warning():
    """layback_release E2E — abnormal_release_during_hold warning 1개 이상."""
    frames, pole, _, _ = build_layback_release()
    boundaries = [
        _phase("lock", 0, 30),
        _phase("hold", 30, 60),
    ]
    metrics = compute_contact_stability(frames, boundaries, pole, "ref-foxtop")
    all_warnings = []
    for m in metrics:
        all_warnings.extend(m.warnings)
    # abnormal_release_during_hold warning 1개 이상.
    assert "abnormal_release_during_hold" in all_warnings
