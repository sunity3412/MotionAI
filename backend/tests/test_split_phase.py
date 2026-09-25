"""quick-260925-nnt — 벌림 규칙(split_phase.final_phase_split) + 스플릿 라인 요소 게이트.
belle 2026-09-25: "다리 벌림 = 1자로 쫙 벌려졌는가, 조금만 벌려졌는가". 이 테스트가 단언하는 것 (수치 채우기 아님):
  (1) 기준 창 마지막 1/3 의 사이각 중앙값과 DTW 로 짝지어진 학생 구간의 중앙값 차가 부족분이다
  (2) 정타(같은 시계열)는 부족분 0 · 덜 벌린 학생은 양수 · 더 벌린 학생은 음수(호출측이 0 으로 자른다)
  (3) 회전 중 사이각이 0 으로 떨어지는 프레임이 끼어도 중앙값은 흔들리지 않는다(peak 포화·최소값 함정 회피)
  (4) 순간 = 학생 중앙값 최근접 프레임 · path 없으면 학생 창 마지막 1/3 · 표본 부족·형상 이상은 None
  (5) 게이트 = technique.SPLIT_LINE_ELEMENTS (power-spin 만) — kip-up 등은 이 경로를 타지 않는다
실 Gemini/Pod/S3/Firestore 호출 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import split_phase as sp  # noqa: E402
from sunity_shared.analysis import technique  # noqa: E402
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES  # noqa: E402

_LH, _RH, _LK, _RK = (KEYPOINT_NAMES.index(n) for n in ("left_hip", "right_hip", "left_knee", "right_knee"))


def _kp(split_deg_per_frame) -> np.ndarray:
    """프레임별 두 허벅지 사이각(도)을 만드는 17점 좌표. 엉덩이는 원점 근처, 무릎은 사이각의 반씩 벌린 방향."""
    T = len(split_deg_per_frame)
    X = np.zeros((T, 17, 3), dtype=float)
    X[:, :, 0] = 0.5
    X[:, :, 1] = 0.5
    for t, deg in enumerate(split_deg_per_frame):
        h = np.deg2rad(float(deg) / 2.0)
        X[t, _LH] = (0.49, 0.50, 0.0)
        X[t, _RH] = (0.51, 0.50, 0.0)
        X[t, _LK] = (0.49 - 0.2 * np.sin(h), 0.50 + 0.2 * np.cos(h), 0.0)
        X[t, _RK] = (0.51 + 0.2 * np.sin(h), 0.50 + 0.2 * np.cos(h), 0.0)
    return X


def _pairs(u0, u1, r0, r1):
    """학생 [u0,u1) ↔ 기준 [r0,r1) 를 선형으로 잇는 절대 짝."""
    n = max(u1 - u0, r1 - r0)
    return [(u0 + int(i * (u1 - u0) / n), r0 + int(i * (r1 - r0) / n)) for i in range(n)]


def test_deficit_is_reference_minus_student_over_the_final_third():
    ref = _kp([20.0] * 60 + [170.0] * 30)          # 창 (0, 90): 마지막 1/3 = [60, 90) 에서 1자
    stu = _kp([20.0] * 40 + [40.0] * 20)           # 학생은 끝에서 조금만 벌린다
    out = sp.final_phase_split(stu, ref, (0, 90), _pairs(0, 60, 0, 90))
    assert out is not None
    assert out["referencePhase"] == (60, 90) and out["studentPhase"] == (40, 60)
    assert out["referenceDeg"] == pytest.approx(170.0, abs=1.0)
    assert out["studentDeg"] == pytest.approx(40.0, abs=1.0)
    assert out["deficitDeg"] == pytest.approx(130.0, abs=2.0)


def test_same_take_is_zero_and_wider_student_is_negative():
    ref = _kp([20.0] * 60 + [170.0] * 30)
    same = sp.final_phase_split(ref, ref, (0, 90), _pairs(0, 90, 0, 90))
    assert same is not None and abs(same["deficitDeg"]) < 1.0
    wider = _kp([20.0] * 60 + [178.0] * 30)
    out = sp.final_phase_split(wider, ref, (0, 90), _pairs(0, 90, 0, 90))
    assert out["deficitDeg"] < 0.0


def test_median_ignores_rotation_frames_that_drop_to_zero():
    """기준 마지막 국면에 0° 프레임(두 허벅지가 화면과 나란한 순간)이 1/4 끼어도 중앙값은 1자다."""
    tail = ([165.0] * 3 + [0.0]) * 8   # 32 프레임, 1/4 이 0
    ref = _kp([20.0] * 64 + tail)
    stu = _kp([20.0] * 40 + [40.0] * 20)
    out = sp.final_phase_split(stu, ref, (0, 96), _pairs(0, 60, 0, 96))
    assert out["referenceDeg"] == pytest.approx(165.0, abs=1.0)
    assert out["deficitDeg"] == pytest.approx(125.0, abs=2.0)


def test_moment_is_the_student_frame_nearest_the_student_median():
    stu_series = [20.0] * 40 + [30.0, 50.0, 40.0, 41.0, 39.0] + [45.0] * 15
    stu = _kp(stu_series)
    ref = _kp([20.0] * 60 + [170.0] * 30)
    out = sp.final_phase_split(stu, ref, (0, 90), _pairs(0, 60, 0, 90))
    med = out["studentDeg"]
    seg = np.asarray(stu_series[40:60])
    assert out["studentFrame"] == 40 + int(np.argmin(np.abs(seg - med)))


def test_without_path_the_student_window_last_third_is_used():
    ref = _kp([20.0] * 60 + [170.0] * 30)
    stu = _kp([20.0] * 40 + [40.0] * 20)
    out = sp.final_phase_split(stu, ref, (0, 90), None, u_win=(0, 60))
    assert out is not None and out["studentPhase"] == (40, 60)
    assert sp.final_phase_split(stu, ref, (0, 90), None) is None


@pytest.mark.parametrize(
    "student, reference, r_win, pairs",
    [
        (_kp([40.0] * 60), _kp([170.0] * 90), (0, 3), _pairs(0, 60, 0, 3)),          # 창이 짧다
        (_kp([40.0] * 60), _kp([170.0] * 90), (0, 200), _pairs(0, 60, 0, 90)),       # 창이 기준 길이를 넘는다
        (_kp([40.0] * 60), _kp([170.0] * 90), (0, 90), _pairs(0, 60, 0, 30)),        # 짝이 마지막 1/3 에 없고 u_win 도 없다
        (np.zeros((60, 12, 3)), _kp([170.0] * 90), (0, 90), _pairs(0, 60, 0, 90)),   # 17점이 아니다
        (_kp([np.nan] * 60), _kp([170.0] * 90), (0, 90), _pairs(0, 60, 0, 90)),      # 학생 표본 전부 비유한
    ],
)
def test_fail_closed_cases_return_none(student, reference, r_win, pairs):
    assert sp.final_phase_split(student, reference, r_win, pairs) is None


def test_split_line_elements_is_power_spin_only():
    assert "ref-power-spin" in technique.SPLIT_LINE_ELEMENTS
    for other in ("ref-kip-up", "ref-climb", "ref-peter-pan", "ref-pdshape", "ref-elbow-twist-sister"):
        assert other not in technique.SPLIT_LINE_ELEMENTS
