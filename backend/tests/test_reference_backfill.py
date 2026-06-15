"""Phase 14 Wave-0 백필 테스트 하니스 (14-01 Task 2).

목적 (D-01 / D-02 / R2 / R3-1 / R4-1 / R4-2):
  reference 백필은 학생 `_process` 가 호출하는 SAME `sunity_shared` 함수들을 거치되,
  PINNED config (REFERENCE_V1_FORCE_CONFIG) 로 거친다. 이유: 운영 `_process` 는
  env-driven `_preflight_label_gate_passed()` 와 Layer-2-조건부 `technique_profile`
  을 넘긴다 — 따라서 올바른 contract 는 "reference-v1 pinned config 하의 동일 함수"
  이지 "student path exact" 가 아니다 (R2).

이 하니스가 박제하는 것:
  · D-01 reference-v1 pinned-config parity (REFERENCE_V1_FORCE_CONFIG 하에서 provably
    exact) — Plan 14-02 가 만들 `backfill_reference_downstream.compute_reference_downstream`
    의 RED target. R4-1 env-gated strict import 로 gate.
  · env-flip divergence (R2) — preflight_label_gate_passed=True 면 결과가 달라짐을 증명.
  · R4-2 motion_id=None propagation parity — fallback/null force-config 선택을 machine-check.
  · R3-1 forceDirectionPattern scoped-validator fixtures — valid findings[].warnings:str[]
    accepted / nested-or-unknown rejected (production `_validate_force_pattern_inference`).
  · SC#4 single-view graceful — vertical-fallback line=None → contact metrics None +
    'pole_line_missing' warning, no raise.
  · D-02 verdict — STORED-SUFFICIENT (EXTEND/meanAngles from angles alone) vs HYBRID-NEEDED
    (measure_body_profile 는 raw keypoints_3d 필요, from-flat 재구성은 degraded).
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

# pipeline import-by-path + sunity_shared layer 경로 주입
# (test_pipeline_body_profile_injection.py 패턴 정합 — conftest.py 가 layer 를
#  이미 sys.path 에 넣지만 명시적으로도 안전하게 둔다).
_LAYER = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared.analysis import force_pattern as fp  # noqa: E402
from sunity_shared.analysis import force_signals as fs  # noqa: E402
from sunity_shared.analysis import skeleton  # noqa: E402
from sunity_shared.analysis.body_normalization_measurer import (  # noqa: E402
    measure_body_profile,
)
from sunity_shared.analysis.features import (  # noqa: E402
    compute_joint_angles,
    joint_uncertainty,
)
from sunity_shared.analysis.pole_geometry import (  # noqa: E402
    build_pole_axis_measurement,
)
from sunity_shared.analysis.pose_frame import (  # noqa: E402
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
    to_coco17_array,
)
from sunity_shared.analysis.technique import FallbackRecognizer  # noqa: E402
from sunity_shared.analysis.temporal import temporal_fill  # noqa: E402
from sunity_shared.firestore_admin import (  # noqa: E402
    _validate_force_pattern_inference,
)


# ── REFERENCE_V1_FORCE_CONFIG ──────────────────────────────────────────────
# R2 + R4-2 — reference v1 의 PINNED force-config 를 config 객체에 박제한다
# (behavior 가 아니라 명시 값으로 기록). 학생 _process 의 env-driven 값과 의도적으로
# 다르다: recognizer=FallbackRecognizer, technique_profile=None,
# preflight_label_gate_passed=None, Layer-2 off, fallback/null motion_id.
# Phase 15 비교 시 reference force 필드는 이 config 하에서 생성된 것으로 취급해야 한다.
REFERENCE_V1_FORCE_CONFIG = {
    "recognizer": "FallbackRecognizer",
    "techniqueProfileForForceSignals": None,
    "preflightLabelGatePassed": None,
    "forceSignalsLayer2Enabled": False,
    # R4-2 — fallback/null force motion_id 선택을 config 에 기록.
    # FallbackRecognizer.recognize 는 motion_id 를 set 하지 않으므로 None 으로 귀결.
    "forceMotionIdSource": "fallback_profile_motion_id",
    "forceMotionId": None,
}


# ── R4-1 env-gated strict import (D-01 parity RED target gate) ─────────────
# PHASE14_REQUIRE_BACKFILL_HELPER UNSET → importorskip (Wave-0 scaffold/RED 보존;
#   helper 가 아직 없으므로 parity 테스트만 skip). 14-02 의 검증 커맨드는
#   PHASE14_REQUIRE_BACKFILL_HELPER=1 로 실행되어 helper 가 생긴 뒤에는
#   parity 가 skip 될 수 없다 (missing → FAIL, not skip). R4-1.
#
# 중요: 이 gate 는 helper 를 실제로 쓰는 D-01 parity 테스트에만 적용한다. SC#4 /
# D-02 / R3-1 / env-flip / motion_id 테스트는 production sunity_shared 함수와
# validator 를 직접 검증하므로 env gate 와 무관하게 항상 실행된다 (no skip).
_REQUIRE = os.environ.get("PHASE14_REQUIRE_BACKFILL_HELPER")


def _load_helper():
    """parity 테스트 진입 시점에 helper 를 로드한다 (R4-1).

    _REQUIRE == "1" → 정상 import; helper 부재 시 ImportError 가 그대로 전파되어
      테스트가 FAIL (skip 아님). 14-02 의 검증 커맨드가 이 모드로 돈다.
    _REQUIRE != "1" → importorskip; helper 부재 시 이 parity 테스트만 SKIP.
    """
    if _REQUIRE == "1":
        from backfill_reference_downstream import (  # type: ignore
            compute_reference_downstream,
        )
        return compute_reference_downstream
    return pytest.importorskip(
        "backfill_reference_downstream"
    ).compute_reference_downstream


# ── 합성 fixture (GPU 없이 deterministic PoseFrame list) ────────────────────


def _vertical_pole() -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )


def _build_pose_frame(frame_index: int) -> PoseFrame:
    """raw keypoints_3d (+ confidence) + pole-aligned + reliability 가 모두 있는
    합성 PoseFrame. body/force 입력에 충분 (HYBRID live-frames 대표)."""
    # 명백히 신전(EXTEND, ≥150°) 인 팔꿈치/무릎이 되도록 일직선 배치.
    coords = {
        "nose": (500.0, 40.0, 0.0),
        "left_eye": (490.0, 30.0, 0.0),
        "right_eye": (510.0, 30.0, 0.0),
        "left_ear": (480.0, 35.0, 0.0),
        "right_ear": (520.0, 35.0, 0.0),
        "left_shoulder": (450.0, 100.0, 0.0),
        "right_shoulder": (550.0, 100.0, 0.0),
        "left_elbow": (450.0, 230.0, 0.0),
        "right_elbow": (550.0, 230.0, 0.0),
        "left_wrist": (450.0, 360.0, 0.0),
        "right_wrist": (550.0, 360.0, 0.0),
        "left_hip": (470.0, 320.0, 0.0),
        "right_hip": (530.0, 320.0, 0.0),
        "left_knee": (470.0, 500.0, 0.0),
        "right_knee": (530.0, 500.0, 0.0),
        "left_ankle": (470.0, 680.0, 0.0),
        "right_ankle": (530.0, 680.0, 0.0),
    }
    kp3d = {
        name: Keypoint3D(
            x=x, y=y, z=z, confidence=0.9, uncertainty_proxy=0.1
        )
        for name, (x, y, z) in coords.items()
    }
    aligned = {
        name: Keypoint3DAligned(x=x, y=y, z=z)
        for name, (x, y, z) in coords.items()
    }
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=frame_index * 111,
        raw_landmarks_33={},
        keypoints_3d=kp3d,
        keypoints_3d_pole_aligned=aligned,
        keypoints_2d=None,
        pole_extension_landmarks=None,
        pole_axis=_vertical_pole(),
        reliability="high",
        body_shape=None,
    )


@pytest.fixture
def pose_frames() -> list[PoseFrame]:
    return [_build_pose_frame(i) for i in range(30)]


@pytest.fixture
def stored_angles(pose_frames: list[PoseFrame]) -> np.ndarray:
    """STORED active angles 와 동등 — to_coco17_array → compute_joint_angles →
    temporal_fill 1회 (Pitfall 3 / REVIEWS R5 — double-smoothing 금지: 여기서
    딱 1회만 temporal_fill 적용하고, 이후 compute_force_signals 에 그대로 전달)."""
    kp = to_coco17_array(pose_frames)
    return temporal_fill(compute_joint_angles(kp), joint_uncertainty(kp))


# ── R4-1 / R4-2 / R2 / R6: D-01 reference-v1 pinned-config parity ──────────


def test_d01_reference_v1_pinned_config_parity(pose_frames, stored_angles):
    """D-01 — 백필 helper 가 SAME 함수를 REFERENCE_V1_FORCE_CONFIG 로 거쳐
    직접 호출 reference 와 동일한 force-signals report 를 낸다 (provably exact
    FOR THAT CONFIG, NOT student-path-exact). R6 — production call boundary:
    orchestrator-built vertical-fallback pole_axis_measurement + STORED angles 를
    주입 인자로 받는다 (_process 가 inputs.pole_axis_measurement + angles 를
    넘기는 것과 동일). R4-1 gate 로 helper 부재 시 이 테스트는 skip(unset)/FAIL(=1)."""
    compute_reference_downstream = _load_helper()  # R4-1 — gate at test entry.

    # orchestrator 가 만드는 vertical-fallback measurement (line=None → unavailable).
    pole_meas = build_pole_axis_measurement(_vertical_pole(), line=None)

    # 직접 호출 reference (REFERENCE_V1_FORCE_CONFIG):
    #   recognizer=Fallback, technique_profile=None, preflight=None, motion_id=None.
    body_profile = measure_body_profile(pose_frames)
    ref_fsr = fs.compute_force_signals(
        pose_frames,
        pole_meas,
        body_profile,
        angles=stored_angles,
        fps=9.0,
        motion_id=None,  # R4-2 — fallback/null
        technique_profile=None,  # REFERENCE_V1_FORCE_CONFIG layer-2 off
        preflight_label_gate_passed=None,  # pinned None
    )

    # helper 산출 (Plan 14-02 구현). REFERENCE_V1_FORCE_CONFIG + 주입 call boundary.
    result = compute_reference_downstream(
        pose_frames,
        pole_axis_measurement=pole_meas,
        angles=stored_angles,
        fps=9.0,
        motion_id=None,
        mode_context="mode1",
        force_config=REFERENCE_V1_FORCE_CONFIG,
    )
    helper_fsr = result.force_signals_report

    # provably exact for the pinned config — top-level warnings + confidence 동일.
    assert helper_fsr.overall_confidence == ref_fsr.overall_confidence
    assert helper_fsr.warnings == ref_fsr.warnings
    assert [b.phase for b in helper_fsr.phase_boundaries] == [
        b.phase for b in ref_fsr.phase_boundaries
    ]


def test_r4_2_motion_id_none_propagation_parity(pose_frames, stored_angles):
    """R4-2 — FallbackRecognizer profile 의 motion_id 는 None 이고, force motion_id
    boost 는 fire 하지 않는다 (reference v1 force 필드는 known-reference contact/boost
    의미 없이 생성). Phase 15 는 reference 가 selected-referenceMotionId force semantics
    를 썼다고 가정하면 안 된다."""
    profile = FallbackRecognizer().recognize(stored_angles)
    # FallbackRecognizer 는 motion_id 를 set 하지 않으므로 None.
    assert getattr(profile, "motion_id", "SENTINEL") is None

    pole_meas = build_pole_axis_measurement(_vertical_pole(), line=None)
    body_profile = measure_body_profile(pose_frames)
    fsr = fs.compute_force_signals(
        pose_frames,
        pole_meas,
        body_profile,
        angles=stored_angles,
        fps=9.0,
        motion_id=None,
        technique_profile=None,
        preflight_label_gate_passed=None,
    )
    # motion_id=None → infer_force_direction_pattern 의 _apply_motion_id_boost 미발동
    # (force_pattern.py:721 — motion_id is not None 일 때만 boost).
    fpi = fp.infer_force_direction_pattern(fsr, motion_id=None, mode_context="mode1")
    # 산출은 fabrication-gated — finding 들의 confidence 가 임의로 1.05 boost 되지 않음.
    for finding in fpi.findings:
        assert 0.0 <= finding.confidence <= 1.0
    # config 가 fallback/null force motion_id 를 명시 기록.
    assert REFERENCE_V1_FORCE_CONFIG["forceMotionIdSource"] == "fallback_profile_motion_id"
    assert REFERENCE_V1_FORCE_CONFIG["forceMotionId"] is None


def test_r2_env_flip_divergence(pose_frames, stored_angles):
    """R2 — preflight_label_gate_passed=True (env PREFLIGHT_LABEL_GATE_PASSED=1 이
    낼 값) 면 force-signals 결과가 pinned None reference 와 달라진다. 따라서 테스트는
    config divergence 를 숨기지 않는다. Phase 15 는 reference force 필드를
    REFERENCE_V1_FORCE_CONFIG 산출로 취급해야 한다."""
    pole_meas = build_pole_axis_measurement(_vertical_pole(), line=None)
    body_profile = measure_body_profile(pose_frames)

    pinned = fs.compute_force_signals(
        pose_frames, pole_meas, body_profile,
        angles=stored_angles, fps=9.0, motion_id=None,
        technique_profile=None, preflight_label_gate_passed=None,
    )
    flipped = fs.compute_force_signals(
        pose_frames, pole_meas, body_profile,
        angles=stored_angles, fps=9.0, motion_id=None,
        technique_profile=None, preflight_label_gate_passed=True,
    )
    # 분기: None → 'preflight_gate_pending' warning, True → 그 warning 없음
    # (force_signals._layer1_confidence_from_preflight). 따라서 top-level warnings
    # 가 달라져야 한다 (divergence 가 테스트에 인코딩됨).
    assert pinned.warnings != flipped.warnings
    assert "preflight_gate_pending" in pinned.warnings
    assert "preflight_gate_pending" not in flipped.warnings


# ── R3-1: forceDirectionPattern scoped-validator fixtures ──────────────────


def _valid_force_pattern_payload() -> dict:
    """contract 정합 valid payload — top-level + finding 필드 (warnings:list[str])."""
    return {
        "version": "1.0",
        "findings": [
            {
                "pattern": "pull",
                "phase": "hold",
                "sourceSignal": "axis_tilt",
                "reason": "shoulder tilt exceeds tolerance during hold",
                "interpretation": "광배가 당기는 힘이 부족할 가능성",
                "confidence": 0.6,
                "jointHint": "광배",
                "warnings": ["axis_signal_unavailable"],
            }
        ],
        "overallConfidence": "medium",
        "modeContext": "mode1",
        "warnings": ["fps_normalization_applied"],
    }


def test_r3_1_valid_force_pattern_accepted():
    """R3-1 (a) — VALID forceDirectionPattern (findings[0].warnings:list[str]) 는
    scoped validator 가 accept (no raise). 일반 flat validator 였다면 findings[].warnings
    의 list[str] 를 거부했을 것 — 따라서 reference mirror 는 scoped validator 를 써야 한다.
    14-02 helper: forceDirectionPattern 에는 _validate_force_pattern_inference,
    meanAngles/techniqueProfile/bodyNormalizationProfile 에는 generic flat validator."""
    # no raise.
    _validate_force_pattern_inference(_valid_force_pattern_payload())


def test_r3_1_nested_warning_rejected():
    """R3-1 (b1) — findings[0].warnings 안 nested list 는 reject (ValueError)."""
    payload = _valid_force_pattern_payload()
    payload["findings"][0]["warnings"] = [["nested"]]
    with pytest.raises(ValueError):
        _validate_force_pattern_inference(payload)


def test_r3_1_unknown_finding_key_rejected():
    """R3-1 (b2) — finding 에 whitelist 밖 key (unexpectedScalar) 면 reject."""
    payload = _valid_force_pattern_payload()
    payload["findings"][0]["unexpectedScalar"] = 1
    with pytest.raises(ValueError):
        _validate_force_pattern_inference(payload)


# ── SC#4: single-view graceful (vertical-fallback line=None) ───────────────


def test_sc4_single_view_graceful(pose_frames, stored_angles):
    """SC#4 — vertical-fallback PoleAxis + build_pole_axis_measurement(line=None)
    → compute_force_signals 의 contact metrics 가 graceful None + 'pole_line_missing'
    warning 을 내고 예외를 던지지 않는다."""
    pole_meas = build_pole_axis_measurement(_vertical_pole(), line=None)
    assert pole_meas.line is None
    body_profile = measure_body_profile(pose_frames)
    fsr = fs.compute_force_signals(
        pose_frames, pole_meas, body_profile,
        angles=stored_angles, fps=9.0, motion_id=None,
        technique_profile=None, preflight_label_gate_passed=None,
    )
    # contact metrics 가 존재한다면 graceful — line=None 이라 'pole_line_missing'.
    contact_warnings = [w for cm in fsr.contact_metrics for w in (cm.warnings or [])]
    assert any("pole_line_missing" in w for w in contact_warnings) or not fsr.contact_metrics
    # distance/stable 계열 evidence 는 None (graceful).
    for cm in fsr.contact_metrics:
        assert cm.distance_to_pole_norm is None
        assert cm.estimated_stable is None


# ── D-02 verdict: STORED-SUFFICIENT vs HYBRID-NEEDED ───────────────────────


def test_d02_stored_sufficient_extend_and_mean(pose_frames, stored_angles):
    """D-02 STORED-SUFFICIENT — EXTEND(FallbackRecognizer) 와 meanAngles(nanmean)
    는 STORED angles 만으로 산출되며 full pose_frames path 와 일치한다. (14-02 에서는
    reference.phase4_v1.angles 로 산출, 재추론 angles 가 아님.)"""
    # path A — stored_angles (이미 temporal_fill 1회) 에서 직접.
    profile_a = FallbackRecognizer().recognize(stored_angles)
    mean_a = np.nanmean(stored_angles, axis=0)

    # path B — full pose_frames 에서 다시 angles 도출 후 (동일 1회 smoothing).
    kp = to_coco17_array(pose_frames)
    angles_b = temporal_fill(compute_joint_angles(kp), joint_uncertainty(kp))
    profile_b = FallbackRecognizer().recognize(angles_b)
    mean_b = np.nanmean(angles_b, axis=0)

    # EXTEND joint_expectations 동일.
    assert profile_a.joint_expectations == profile_b.joint_expectations
    # meanAngles 동일 (finite 위치).
    np.testing.assert_allclose(
        np.nan_to_num(mean_a), np.nan_to_num(mean_b), rtol=1e-6, atol=1e-6
    )
    # JOINT_KEYS 매핑 sanity.
    assert len(skeleton.JOINT_KEYS) == mean_a.shape[0]


def test_d02_hybrid_needed_body_profile(pose_frames):
    """D-02 HYBRID-NEEDED — measure_body_profile 는 raw keypoints_3d (+confidence) 를
    읽는다. STORED flat (pole-aligned, confidence 없음) 에서 재구성한 frame
    (keypoints_3d 비움) 은 provably insufficient — live-frames 결과와 발산한다
    (degraded confidence + insufficient warning). 따라서 body/force 입력은 재추론 필요."""
    # live frames — keypoints_3d 채워짐.
    live = measure_body_profile(pose_frames)
    assert live.confidence > 0.0  # 충분한 측정.

    # from-flat 재구성 — pole-aligned 만 있고 keypoints_3d 는 비어있음 (confidence 손실).
    from_flat = [
        PoseFrame(
            frame_index=f.frame_index,
            timestamp_ms=f.timestamp_ms,
            raw_landmarks_33={},
            keypoints_3d={},  # ← flat 재구성은 raw keypoints_3d 를 못 살림.
            keypoints_3d_pole_aligned=f.keypoints_3d_pole_aligned,
            keypoints_2d=None,
            pole_extension_landmarks=None,
            pole_axis=f.pole_axis,
            reliability=f.reliability,
            body_shape=None,
        )
        for f in pose_frames
    ]
    degraded = measure_body_profile(from_flat)
    # 발산 증명 — confidence 0 (insufficient) 또는 live 대비 명백히 낮음.
    assert degraded.confidence < live.confidence
    assert degraded.confidence == 0.0 or not math.isfinite(degraded.armScale) or degraded.armScale == 1.0
