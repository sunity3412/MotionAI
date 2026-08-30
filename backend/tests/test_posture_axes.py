"""belle 08-17 판독 축 2종 — 상체 꼿꼿함 + 머리-척추 1자 (quick-260831-bjj).

정본 근거 (memory belle-readings-20260817-discovery + CONTINUE-2026-08-31 #1):
  · 피터팬: "오른팔 어깨가 딱 곧게 펴지면서 상체의 꼿꼿해짐이 전체적 영향" —
    상체 꼿꼿함(torso_uprightness_series) 축의 정의 근거.
  · elbow r02cand03: "고개 — 학생은 안 들어 머리카락이 오른팔 안쪽, 기준은 들어
    몸-머리가 1자" — 머리-척추 1자(head_spine_alignment_series) 축의 정의 근거.

합성 정답 좌표로 방향을 결정적으로 검증한다 (test_split_angle.py 선례 — 점수 밴드
단언 0, 구조적/기하 단언만). AWS/네트워크/모델 불필요. 좌표 규약 = 이미지/카메라
y-down (align.json 정규화 xy / RTMW 카메라 좌표 공통).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis.features import (  # noqa: E402
    POSTURE_DELTA_SIGNIFICANT_DEG,
    head_spine_alignment_series,
    posture_axis_summary,
    torso_uprightness_series,
)
from sunity_shared.analysis.skeleton import kp_index  # noqa: E402

TOL_DEG = 2.0


def _frame(points):
    """1프레임 (1,17,3) keypoint. points = {keypoint_name: (x, y)} (z=0, y-down)."""
    kp = np.zeros((1, 17, 3), dtype=float)
    for name, (x, y) in points.items():
        kp[0, kp_index(name)] = [float(x), float(y), 0.0]
    return kp


# 일직선 합성 자세 — 골반중점 (0,0) → 어깨중점 (0,-1) → 귀중점 (0,-2) 일렬 (y-down
# 이라 위로 갈수록 y 감소). 척추도 수직이라 uprightness 0° 겸용.
_STRAIGHT = {
    "left_hip": (-0.2, 0.0), "right_hip": (0.2, 0.0),
    "left_shoulder": (-0.2, -1.0), "right_shoulder": (0.2, -1.0),
    "left_ear": (-0.1, -2.0), "right_ear": (0.1, -2.0),
}

# 고개 숙인 자세 — 귀중점이 척추 연장선에서 앞으로 이탈 (어깨중점 기준 45° 굽음).
_HEAD_BOWED = {
    "left_hip": (-0.2, 0.0), "right_hip": (0.2, 0.0),
    "left_shoulder": (-0.2, -1.0), "right_shoulder": (0.2, -1.0),
    "left_ear": (0.6, -1.7), "right_ear": (0.8, -1.7),
}


# ─────────────── head_spine_alignment_series — 1자 vs 고개 숙임 ───────────────


def test_head_spine_straight_line_is_180():
    """골반중점-어깨중점-귀중점 일렬 → 머리-척추 1자 = 약 180° (belle elbow 원문)."""
    out = head_spine_alignment_series(_frame(_STRAIGHT))
    assert out.shape == (1,)
    assert float(out[0]) == pytest.approx(180.0, abs=TOL_DEG)


def test_head_spine_bowed_head_decreases():
    """고개 숙임(귀중점 이탈) → 180° 미만으로 감소 (방향 검증)."""
    straight = float(head_spine_alignment_series(_frame(_STRAIGHT))[0])
    bowed = float(head_spine_alignment_series(_frame(_HEAD_BOWED))[0])
    assert bowed < straight - TOL_DEG
    assert bowed < 180.0 - TOL_DEG


# ─────────────── torso_uprightness_series — 수직/수평/도립 ───────────────


def test_torso_vertical_is_zero():
    """y-down 에서 수직 척추(어깨 y < 골반 y) → 약 0° (꼿꼿함)."""
    out = torso_uprightness_series(_frame(_STRAIGHT))
    assert float(out[0]) == pytest.approx(0.0, abs=TOL_DEG)


def test_torso_horizontal_is_ninety():
    """수평 척추 → 약 90°."""
    pose = {
        "left_hip": (0.0, -0.2), "right_hip": (0.0, 0.2),
        "left_shoulder": (1.0, -0.2), "right_shoulder": (1.0, 0.2),
    }
    out = torso_uprightness_series(_frame(pose))
    assert float(out[0]) == pytest.approx(90.0, abs=TOL_DEG)


def test_torso_inverted_is_180():
    """도립(어깨 y > 골반 y — 화면 아래가 머리) → 약 180°."""
    pose = {
        "left_hip": (-0.2, 0.0), "right_hip": (0.2, 0.0),
        "left_shoulder": (-0.2, 1.0), "right_shoulder": (0.2, 1.0),
    }
    out = torso_uprightness_series(_frame(pose))
    assert float(out[0]) == pytest.approx(180.0, abs=TOL_DEG)


def test_torso_tilt_monotonic():
    """척추를 수직→수평으로 기울일수록 uprightness 단조 증가 (기울어짐 척도)."""
    vals = []
    for deg in range(0, 91, 15):
        rad = np.radians(deg)
        pose = {
            "left_hip": (-0.2, 0.0), "right_hip": (0.2, 0.0),
            "left_shoulder": (-0.2 + np.sin(rad), -np.cos(rad)),
            "right_shoulder": (0.2 + np.sin(rad), -np.cos(rad)),
        }
        vals.append(float(torso_uprightness_series(_frame(pose))[0]))
    diffs = np.diff(vals)
    assert np.all(diffs > 0), f"단조 증가 위반: {vals}"


# ─────────────── 입력 수용 — (T,17,2|3|4) ───────────────


def test_2d_input_equals_3d_zero_z():
    """(T,17,2) 입력 == (T,17,3) z=0 입력과 결과 동일 (align.json 2D 규약 수용)."""
    kp3 = np.concatenate([_frame(_STRAIGHT), _frame(_HEAD_BOWED)], axis=0)
    kp2 = kp3[:, :, :2]
    np.testing.assert_allclose(
        head_spine_alignment_series(kp2), head_spine_alignment_series(kp3)
    )
    np.testing.assert_allclose(
        torso_uprightness_series(kp2), torso_uprightness_series(kp3)
    )


def test_fourth_channel_ignored():
    """(T,17,4=xyz+불확실도) → 4번째 채널 무시 (split_angle_series 선례)."""
    kp3 = _frame(_STRAIGHT)
    kp4 = np.zeros((1, 17, 4), dtype=float)
    kp4[0, :, :3] = kp3[0]
    kp4[0, :, 3] = 9.9  # 불확실도 — 결과에 영향 없어야
    np.testing.assert_allclose(
        head_spine_alignment_series(kp4), head_spine_alignment_series(kp3)
    )
    np.testing.assert_allclose(
        torso_uprightness_series(kp4), torso_uprightness_series(kp3)
    )


def test_rejects_bad_shape():
    with pytest.raises(ValueError):
        head_spine_alignment_series(np.zeros((17, 3)))
    with pytest.raises(ValueError):
        torso_uprightness_series(np.zeros((1, 5, 3)))


# ─────────────── NaN 전파 ───────────────


def test_nan_keypoint_makes_frame_nan_others_finite():
    """정의 keypoint(귀/어깨/골반) NaN 프레임 → 그 프레임만 NaN, 나머지 정상."""
    kp = np.concatenate(
        [_frame(_STRAIGHT), _frame(_STRAIGHT), _frame(_STRAIGHT)], axis=0
    )
    kp[1, kp_index("left_ear")] = [np.nan, np.nan, np.nan]
    head = head_spine_alignment_series(kp)
    assert np.isnan(head[1])
    assert np.isfinite(head[0]) and np.isfinite(head[2])

    kp2 = np.concatenate(
        [_frame(_STRAIGHT), _frame(_STRAIGHT), _frame(_STRAIGHT)], axis=0
    )
    kp2[1, kp_index("right_shoulder")] = [np.nan, np.nan, np.nan]
    upright = torso_uprightness_series(kp2)
    assert np.isnan(upright[1])
    assert np.isfinite(upright[0]) and np.isfinite(upright[2])


def test_nan_ear_does_not_break_torso():
    """귀 NaN 은 torso_uprightness 정의 keypoint 가 아니므로 전파되지 않는다."""
    kp = _frame(_STRAIGHT)
    kp[0, kp_index("left_ear")] = [np.nan, np.nan, np.nan]
    assert np.isfinite(torso_uprightness_series(kp)[0])


# ─────────────── posture_axis_summary — nanmedian 델타 요약 ───────────────


def test_summary_delta_is_student_minus_reference():
    """delta = student - reference (frame_pair_angle_deltas 부호 선례)."""
    out = posture_axis_summary([10.0, 10.0, 10.0], [2.0, 2.0, 2.0])
    assert out is not None
    assert out["studentDeg"] == pytest.approx(10.0)
    assert out["referenceDeg"] == pytest.approx(2.0)
    assert out["deltaDeg"] == pytest.approx(8.0)
    assert out["significant"] is True


def test_summary_below_threshold_not_significant():
    """|delta| < POSTURE_DELTA_SIGNIFICANT_DEG(5.0) → 잡음 취급 (지시 미승격)."""
    out = posture_axis_summary([4.0, 4.0], [0.0, 0.0])
    assert out is not None
    assert out["significant"] is False


def test_summary_threshold_boundary_inclusive():
    """|delta| == 임계(5.0) → significant True (>= 경계 포함)."""
    assert POSTURE_DELTA_SIGNIFICANT_DEG == 5.0
    out = posture_axis_summary([5.0], [0.0])
    assert out is not None
    assert out["significant"] is True


def test_summary_negative_delta_significant():
    """음의 델타(학생 < 기준)도 |delta| 기준으로 판정 — 부호는 보존."""
    out = posture_axis_summary([170.0], [178.0])
    assert out is not None
    assert out["deltaDeg"] == pytest.approx(-8.0)
    assert out["significant"] is True


def test_summary_median_robust_to_single_frame_jitter():
    """median 요약 — 한 프레임 jitter(peak)가 판정을 오염시키지 않는다."""
    out = posture_axis_summary([10.0, 10.0, 10.0, 90.0], [10.0, 10.0, 10.0])
    assert out is not None
    assert out["studentDeg"] == pytest.approx(10.0)
    assert out["significant"] is False


def test_summary_ignores_nan_frames():
    """NaN 프레임은 nanmedian 이 무시 (폐색 프레임 혼입 허용)."""
    out = posture_axis_summary([np.nan, 20.0, np.nan, 20.0], [10.0, np.nan])
    assert out is not None
    assert out["studentDeg"] == pytest.approx(20.0)
    assert out["referenceDeg"] == pytest.approx(10.0)


def test_summary_all_nan_side_returns_none():
    """한쪽이라도 유한값 0개 → None (요약 불가 fail-closed)."""
    assert posture_axis_summary([np.nan, np.nan], [10.0]) is None
    assert posture_axis_summary([10.0], [np.nan]) is None
    assert posture_axis_summary([], [10.0]) is None


# ─────────────── pipeline 배선 — _reference_keypoints_coco17 (Task 2) ───────────────
# pipeline app 모듈 로드 = test_body_profile.py 선례 (sys.path + importorskip("app")).

_PIPELINE_DIR = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from sunity_shared.analysis.skeleton import KEYPOINT_NAMES  # noqa: E402


def _ref_doc_from_kp(kp, keys):
    """(T,K,3) → ref doc dict {joints3d flat, joints3dKeys} (Firestore flat 저장 규약)."""
    arr = np.asarray(kp, dtype=float)
    return {
        "joints3d": [float(v) for v in arr.ravel()],
        "joints3dKeys": list(keys),
    }


def test_reference_keypoints_restores_shape_order_and_sentinel():
    """flat joints3d → (T,17,3) KEYPOINT_NAMES 재배열 + 전-0 sentinel → NaN 복원."""
    pipeline_app = pytest.importorskip("app")
    # 저장 키 순서를 일부러 KEYPOINT_NAMES 와 다르게 — 재배열 검증.
    keys = ["left_hip", "nose", "right_hip"]
    kp = np.zeros((2, 3, 3), dtype=float)
    kp[:, 0] = [1.0, 2.0, 3.0]   # left_hip
    kp[0, 1] = [4.0, 5.0, 6.0]   # nose 프레임0
    kp[1, 1] = [0.0, 0.0, 0.0]   # nose 프레임1 — 전-0 sentinel (NaN 저장분)
    kp[:, 2] = [7.0, 8.0, 9.0]   # right_hip
    out = pipeline_app._reference_keypoints_coco17(_ref_doc_from_kp(kp, keys))
    assert out is not None
    assert out.shape == (2, 17, 3)
    np.testing.assert_allclose(out[0, kp_index("nose")], [4.0, 5.0, 6.0])
    # sentinel 0,0,0 → NaN (side_match.py 규약 — 실좌표 오인 금지).
    assert np.isnan(out[1, kp_index("nose")]).all()
    np.testing.assert_allclose(out[:, kp_index("left_hip")], [[1, 2, 3], [1, 2, 3]])
    np.testing.assert_allclose(out[:, kp_index("right_hip")], [[7, 8, 9], [7, 8, 9]])
    # 키 누락 관절(left_knee 등) → NaN 행.
    assert np.isnan(out[:, kp_index("left_knee")]).all()


def test_reference_keypoints_malformed_returns_none():
    """형상/키 malformed → None (방어적 파싱 — threat T-quick-01)."""
    pipeline_app = pytest.importorskip("app")
    assert pipeline_app._reference_keypoints_coco17({}) is None
    assert pipeline_app._reference_keypoints_coco17(
        {"joints3d": [1.0, 2.0], "joints3dKeys": ["nose"]}  # 3의 배수 아님
    ) is None
    assert pipeline_app._reference_keypoints_coco17(
        {"joints3d": [1.0, 2.0, 3.0], "joints3dKeys": []}
    ) is None
    assert pipeline_app._reference_keypoints_coco17(
        {"joints3d": None, "joints3dKeys": ["nose"]}
    ) is None


def _full_ref_doc(pose_points):
    """{name: (x,y)} 자세 1프레임 → 17관절 전부 채운 ref doc (미지정 관절은 sentinel 0)."""
    kp = np.zeros((1, 17, 3), dtype=float)
    for name, (x, y) in pose_points.items():
        kp[0, kp_index(name)] = [float(x), float(y), 0.1]  # z=0.1 — 전-0 sentinel 회피
    return _ref_doc_from_kp(kp, KEYPOINT_NAMES)


def test_compute_posture_axes_produces_both_axes():
    """학생(4ch) vs ref doc → headSpine/uprightness 요약 dict (features 산출값 그대로)."""
    pipeline_app = pytest.importorskip("app")
    # 학생: 상체를 기울인 자세 / 기준: 수직 꼿꼿 자세 → uprightness delta > 0.
    student4 = np.zeros((1, 17, 4), dtype=float)
    student4[0, :, :3] = 0.1
    for name, (x, y) in {
        "left_hip": (-0.2, 0.0), "right_hip": (0.2, 0.0),
        "left_shoulder": (0.8, -0.6), "right_shoulder": (1.2, -0.6),  # 기울어짐
        "left_ear": (1.4, -1.0), "right_ear": (1.6, -1.0),
    }.items():
        student4[0, kp_index(name), :3] = [x, y, 0.1]
    ref = _full_ref_doc(_STRAIGHT)
    axes = pipeline_app._compute_posture_axes(student4, ref)
    assert axes is not None
    assert set(axes.keys()) == {"headSpine", "uprightness"}
    assert axes["uprightness"] is not None
    assert axes["uprightness"]["deltaDeg"] > 0  # 학생이 더 기울어짐
    assert axes["headSpine"] is not None


def test_compute_posture_axes_malformed_ref_graceful_none():
    """ref malformed / None → None (코칭 보조 실패는 분석 중단 금지)."""
    pipeline_app = pytest.importorskip("app")
    student4 = np.zeros((1, 17, 4), dtype=float)
    assert pipeline_app._compute_posture_axes(student4, {}) is None
    assert pipeline_app._compute_posture_axes(student4, None) is None


# ─────────────── _build_coach_context postureAxes seam (Task 2) ───────────────


def _mk_assessments():
    """kismam.top_issues 소비용 최소 assessment (test_body_profile 선례)."""
    from sunity_shared.analysis.kismam import JointAssessment

    return [
        JointAssessment(
            key="left_elbow",
            label_ko="왼팔꿈치",
            score=70,
            deviation_deg=23.0,
            part="상체",
            direction="extend",
        ),
    ]


def test_build_coach_context_posture_axes_passthrough():
    """posture_axes kwarg → context['postureAxes'] 그대로 전달 (양 writer 공유 B3)."""
    pipeline_app = pytest.importorskip("app")
    from sunity_shared import models

    axes = {
        "uprightness": {"studentDeg": 25.0, "referenceDeg": 10.0,
                        "deltaDeg": 15.0, "significant": True},
        "headSpine": None,
    }
    ctx = pipeline_app._build_coach_context(
        mode=models.MODE_EXPERT,
        assessments=_mk_assessments(),
        dim_scores=None,
        local_video_path=None,
        scene_flags=None,
        posture_axes=axes,
    )
    assert ctx["postureAxes"] == axes


def test_build_coach_context_posture_axes_defaults_none():
    """kwarg 미전달 → None (기존 키·프롬프트 불변 — bodyProfile graceful 선례)."""
    pipeline_app = pytest.importorskip("app")
    from sunity_shared import models

    ctx = pipeline_app._build_coach_context(
        mode=models.MODE_SELF,
        assessments=_mk_assessments(),
        dim_scores=None,
        local_video_path=None,
        scene_flags=None,
    )
    assert "postureAxes" in ctx
    assert ctx["postureAxes"] is None
