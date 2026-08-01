"""quick-260801-gbk Task 1 — 감점 criterion 별 "어느 프레임에서 쟀는가" 산출 게이트.

_build_deduction_measured_deviations(measured_at_out=...) 가 채우는 순간이
**record 가 실제로 보고한 집계값**에서 파생되는지, 그리고 순간을 정할 수 없는
criterion 이 조용히 채워지지 않는지를 본다.

핵심 회귀 가드는 argmax 금지다 — 집계가 median/mean 인데 최대 편차 프레임을
가리키면 각도 jitter 프레임을 "여기가 감점 부분"이라며 확대하게 된다
(motiondtw.per_joint_deviation docstring 198-209행이 그 jitter 를 박제한다).

전부 순수 builder 테스트 — Pod/S3/Firestore/Gemini 호출 0.
방향·구조 단언만. 보유 sweep 수치 타깃 아님(curve-fit 금지).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

import app  # noqa: E402
from sunity_shared.analysis import technique, vision_veto  # noqa: E402
from sunity_shared.analysis.motiondtw import (  # noqa: E402
    MotionMatch,
    per_joint_deviation,
    per_joint_representative_frames,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402

_LEFT_SHOULDER = JOINT_KEYS.index("left_shoulder")
_RIGHT_SHOULDER = JOINT_KEYS.index("right_shoulder")
_LEFT_KNEE = JOINT_KEYS.index("left_knee")
_RIGHT_KNEE = JOINT_KEYS.index("right_knee")

# 테스트 stub 어댑터의 target_fps. **일부러 프로덕션 기본 fps 가 아닌 값**을 쓴다 —
# video_sec 이 _pipeline_frame_fps() 단일 출처에서 나오는지, 아니면 코드가 기본 fps 를
# 가정하고 있는지를 값으로 구분하기 위해서다.
_STUB_FPS = 12.0


class _Ext:
    """frame_extractor stub — _pipeline_frame_fps 의 단일 출처를 테스트에 공급."""

    target_fps = _STUB_FPS


@pytest.fixture(autouse=True)
def _stub_fps(monkeypatch):
    monkeypatch.setattr(app, "_FRAME_EXTRACTOR", _Ext())


# ── fixtures ────────────────────────────────────────────────────────────────


def _unregistered_profile():
    """미등록 동작 — expects_extension 전부 False (angle_vs_reference 경로)."""
    return technique.TechniqueProfile(
        name="미등록", category="unknown", joint_expectations={}
    )


def _knee_extend_profile(hold_window=None):
    """무릎만 EXTEND — leg_extension / line 경로."""
    exp = {
        k: technique.JOINT_EXTEND if k.endswith("knee") else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(
        name="t", category="unknown", joint_expectations=exp,
        hold_window=hold_window,
    )


def _identity_match(T, start=0):
    return MotionMatch(
        start=start, end=start + T, ref_start=0, ref_end=T,
        distance=0.0, path=[(i, i) for i in range(T)],
    )


def _quant(wm_deltas=None, user_frames=None):
    wm = None
    if wm_deltas is not None:
        wm = {
            "deltas": list(wm_deltas),
            "sourceFrameIndices": {
                "user": list(user_frames if user_frames is not None else [3]),
                "reference": [3],
            },
            "windowPolicy": "worst_pose_center_pm_2_median",
        }
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="available",
        angleDeltas=None,
        bodyRelativeNotches=None,
        windowMedianAngleDeltas=wm,
        warnings=(),
    )


def _angles(T=10, deg=170.0):
    return np.full((T, len(JOINT_KEYS)), deg, dtype=float)


def _build(*, usr, ref=None, profile, quantification, match=None, out=None, **kw):
    return app._build_deduction_measured_deviations(
        angles=usr, profile=profile, assessments=[], dimension_scores={},
        quantification=quantification,
        reference_dtw_match=match, reference_angles=ref,
        measured_at_out=out, **kw,
    )


# ── (1) pointed 관절 — window 안에서 student_deg 에 가장 가까운 프레임 ────────


def test_pointed_joint_moment_is_closest_to_student_deg_inside_window():
    """pointed 관절의 순간은 sourceFrameIndices.user 안, student_deg 최근접 프레임."""
    T = 12
    ref = _angles(T)
    usr = _angles(T)
    # window = [4,5,6]. 그 안의 학생 어깨 각도가 서로 다르게 흩어져 있고,
    # record 가 보고한 student_deg(=130.0) 와 정확히 같은 프레임은 5 뿐이다.
    usr[:, _LEFT_SHOULDER] = 170.0
    usr[4, _LEFT_SHOULDER] = 120.0
    usr[5, _LEFT_SHOULDER] = 130.0
    usr[6, _LEFT_SHOULDER] = 145.0
    wm = [{"joint": "left_shoulder", "delta_deg": -40.0, "student_deg": 130.0}]
    out: dict = {}
    md = _build(
        usr=usr, ref=ref, profile=_unregistered_profile(),
        quantification=_quant(wm, user_frames=[4, 5, 6]),
        match=_identity_match(T), out=out,
        vision_pointed_joints=("left_shoulder",),
    )
    assert md["angle_vs_reference__left_shoulder"] == pytest.approx(40.0)
    moment = out["angle_vs_reference__left_shoulder"]
    assert moment["frame_idx"] == 5
    assert moment["video_sec"] == pytest.approx(5 / _STUB_FPS)


def test_pointed_joint_moment_never_leaves_the_window():
    """window 밖에 student_deg 와 더 가까운 프레임이 있어도 고르지 않는다.

    record 가 보고한 값은 그 window 의 median 이다 — 밖을 가리키면 "쟀다"는
    계약 자체가 깨진다.
    """
    T = 12
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 170.0
    usr[4, _LEFT_SHOULDER] = 120.0
    usr[5, _LEFT_SHOULDER] = 128.0  # window 안 최근접
    usr[6, _LEFT_SHOULDER] = 145.0
    usr[9, _LEFT_SHOULDER] = 130.0  # window 밖 완전 일치 — 유혹
    wm = [{"joint": "left_shoulder", "delta_deg": -40.0, "student_deg": 130.0}]
    out: dict = {}
    _build(
        usr=usr, ref=ref, profile=_unregistered_profile(),
        quantification=_quant(wm, user_frames=[4, 5, 6]),
        match=_identity_match(T), out=out,
        vision_pointed_joints=("left_shoulder",),
    )
    assert out["angle_vs_reference__left_shoulder"]["frame_idx"] == 5


# ── (2) silent 관절 — DTW 대표 프레임이 절대 인덱스 + median 정합 ────────────


def test_dtw_moment_is_absolute_index_offset_by_match_start():
    """path 는 구간-로컬이므로 match.start 를 더해 절대 학생 프레임이 되어야 한다."""
    T = 8
    start = 5
    ref = _angles(T)
    usr = _angles(T + start)
    usr[start:, _RIGHT_SHOULDER] = 140.0
    out: dict = {}
    _build(
        usr=usr, ref=ref, profile=_unregistered_profile(),
        quantification=_quant(), match=_identity_match(T, start=start), out=out,
    )
    frame = out["angle_vs_reference__right_shoulder"]["frame_idx"]
    assert frame >= start, "구간-로컬 인덱스를 그대로 쓰면 앞쪽 프레임을 가리킨다"
    assert frame < start + T


def test_sibling_median_matches_per_joint_deviation_exactly():
    """sibling 이 고른 스텝의 편차 = per_joint_deviation 이 보고한 median.

    두 함수가 같은 diffs 를 본다는 것을 값으로 확인한다 — 이 등식이 깨지면
    '보고한 값을 잰 순간'이라는 계약이 성립하지 않는다.
    """
    rng = np.random.default_rng(7)
    T = 21
    J = len(JOINT_KEYS)
    a_user = rng.uniform(90.0, 180.0, size=(T, J))
    a_ref = rng.uniform(90.0, 180.0, size=(T, J))
    path = [(i, i) for i in range(T)]
    med = per_joint_deviation(path, a_user, a_ref)
    reps = per_joint_representative_frames(path, a_user, a_ref, 0)
    for j in range(J):
        t = reps[j]
        step_dev = abs(a_user[t][j] - a_ref[t][j])
        # T 가 홀수라 median 은 실제로 존재하는 스텝 값 — 정확히 일치해야 한다.
        assert step_dev == pytest.approx(float(med[j]))


def test_representative_frames_empty_path_returns_empty():
    """path 가 비면 빈 dict — 순간 없음(fail-closed)."""
    a = _angles(4)
    assert per_joint_representative_frames([], a, a, 0) == {}


# ── (3) argmax 회귀 가드 — jitter 프레임을 고르지 않는다 ─────────────────────


def test_moment_is_not_the_jitter_spike_frame():
    """한 프레임만 편차가 폭주하는 시계열에서 대표 프레임이 그 프레임이 아니다.

    argmax 로 구현하면 이 테스트가 정확히 실패한다.
    """
    T = 9
    J = len(JOINT_KEYS)
    a_ref = np.full((T, J), 170.0, dtype=float)
    a_user = np.full((T, J), 165.0, dtype=float)  # 정상 편차 5도
    spike_t = 4
    a_user[spike_t, _LEFT_SHOULDER] = 130.0  # 이 프레임만 편차 40도
    path = [(i, i) for i in range(T)]
    reps = per_joint_representative_frames(path, a_user, a_ref, 0)
    assert reps[_LEFT_SHOULDER] != spike_t
    chosen_dev = abs(a_user[reps[_LEFT_SHOULDER]][_LEFT_SHOULDER] - 170.0)
    spike_dev = abs(a_user[spike_t][_LEFT_SHOULDER] - 170.0)
    assert chosen_dev < spike_dev


# ── (4) leg_extension — 이긴 관절의 window 안 대표 프레임 ────────────────────


def test_leg_extension_moment_follows_the_winning_joint():
    """좌/우 중 부족분이 큰 관절이 집계값을 만들고, 순간도 그 관절에서 나온다."""
    T = 10
    usr = _angles(T, deg=180.0)
    # 왼무릎은 window 내내 175도(부족 5), 오른무릎은 프레임마다 달라 평균 부족이 크다.
    usr[:, _LEFT_KNEE] = 175.0
    usr[:, _RIGHT_KNEE] = 180.0
    usr[2, _RIGHT_KNEE] = 120.0
    usr[3, _RIGHT_KNEE] = 140.0
    usr[4, _RIGHT_KNEE] = 160.0
    profile = _knee_extend_profile(hold_window=(2, 5))
    out: dict = {}
    md = _build(
        usr=usr, profile=profile, quantification=_quant(), out=out,
    )
    # 집계값은 오른무릎이 만든다 (window mean 부족분 = 180 - (120+140+160)/3 = 40).
    assert md["leg_extension"] == pytest.approx(40.0)
    frame = out["leg_extension"]["frame_idx"]
    assert 2 <= frame < 5, "순간은 _select_window 구간 안이어야 한다"
    # 집계값 40 에 per-frame 부족분이 가장 가까운 프레임 = 140도인 3번.
    assert frame == 3


def test_extension_moment_is_not_the_worst_frame():
    """window 안 최대 부족 프레임(argmax)이 아니라 집계값 최근접 프레임."""
    T = 10
    usr = _angles(T, deg=180.0)
    usr[:, _LEFT_KNEE] = 180.0
    usr[:, _RIGHT_KNEE] = 180.0
    usr[2, _RIGHT_KNEE] = 120.0  # 최대 부족(60) — argmax 유혹
    usr[3, _RIGHT_KNEE] = 140.0
    usr[4, _RIGHT_KNEE] = 160.0
    out: dict = {}
    _build(
        usr=usr, profile=_knee_extend_profile(hold_window=(2, 5)),
        quantification=_quant(), out=out,
    )
    assert out["leg_extension"]["frame_idx"] != 2


# ── (5) line — 기여 관절 집합의 per-frame 평균 부족분 최근접 ─────────────────


def test_line_moment_uses_the_contributing_joint_set_mean():
    """line 순간 = 집계에 기여한 관절들의 per-frame 평균 부족분이 집계값에 최근접."""
    T = 10
    usr = _angles(T, deg=180.0)
    # 두 무릎 모두 EXTEND 이고 둘 다 양수 부족분을 낸다 → line 집계는 둘의 평균.
    usr[2, _LEFT_KNEE], usr[2, _RIGHT_KNEE] = 100.0, 120.0   # 평균 부족 70
    usr[3, _LEFT_KNEE], usr[3, _RIGHT_KNEE] = 150.0, 160.0   # 평균 부족 25
    usr[4, _LEFT_KNEE], usr[4, _RIGHT_KNEE] = 170.0, 178.0   # 평균 부족 6
    out: dict = {}
    md = _build(
        usr=usr, profile=_knee_extend_profile(hold_window=(2, 5)),
        quantification=_quant(), out=out,
    )
    line_val = md["line"]
    frame = out["line"]["frame_idx"]
    assert 2 <= frame < 5
    # 그 프레임의 평균 부족분이 다른 후보들보다 집계값에 가깝다.
    def _frame_mean_deficit(t):
        return (
            max(0.0, 180.0 - usr[t][_LEFT_KNEE])
            + max(0.0, 180.0 - usr[t][_RIGHT_KNEE])
        ) / 2.0

    best_gap = abs(_frame_mean_deficit(frame) - line_val)
    for t in (2, 3, 4):
        assert abs(_frame_mean_deficit(t) - line_val) >= best_gap - 1e-9


# ── (6) fail-closed — 순간을 정할 수 없는 criterion 은 항목 자체가 없다 ──────


def test_reach_and_split_and_fallback_have_no_moment():
    """body_relative_reach / dimension_overall_fallback / split_angle 은 out 에 없다."""
    T = 10
    usr = _angles(T)
    quant = vision_veto.VisionQuantificationResult(
        quantificationStatus="available",
        angleDeltas=None,
        bodyRelativeNotches=[
            {"axis": "hip_height", "student_notches": 1, "reference_notches": 3,
             "delta_notches": -2},
        ],
        windowMedianAngleDeltas=None,
        warnings=(),
    )
    out: dict = {}
    md = _build(
        usr=usr, profile=_unregistered_profile(), quantification=quant,
        out=out, split_deficit_deg=12.0,
    )
    # 값은 방출되지만 순간은 없다.
    assert "body_relative_notches" in md
    assert md["split_angle"] == pytest.approx(12.0)
    assert "body_relative_reach" not in out
    assert "body_relative_notches" not in out
    assert "split_angle" not in out
    assert "dimension_overall_fallback" not in out


def test_split_angle_has_no_moment_even_with_geometry_seed():
    """split 은 기하 seed 가 있어도 순간을 얻지 못한다 (프로덕션 경로는 vision 주입).

    vision record 의 measuredValue 는 Gemini 추정이고 우리가 그 프레임에서 잰
    값이 아니다 — 기하 프레임을 "여기서 쟀다" 계약 아래 붙이면 이 필드가
    없애려는 거짓과 같은 종류가 된다.
    """
    T = 10
    usr = _angles(T)
    out: dict = {}
    _build(
        usr=usr, profile=_unregistered_profile(), quantification=_quant(),
        out=out, split_deficit_deg=30.0,
    )
    assert "split_angle" not in out


# ── (7) md 불변 — out-param 유무가 점수 substrate 를 흔들지 않는다 ───────────


def test_md_is_identical_with_and_without_out_param():
    """measured_at_out 전달 유무와 무관하게 md 가 키·값 모두 동일하다.

    이 등식이 불변식 1(채점 무접촉)의 함수 단위 증명이다.
    """
    T = 12
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    usr[:, _RIGHT_SHOULDER] = 140.0
    usr[:, _LEFT_KNEE] = 150.0
    wm = [{"joint": "left_shoulder", "delta_deg": -40.4, "student_deg": 130.0}]

    def _run(out):
        return _build(
            usr=usr.copy(), ref=ref, profile=_knee_extend_profile(),
            quantification=_quant(wm, user_frames=[3, 4, 5]),
            match=_identity_match(T), out=out,
            vision_pointed_joints=("left_shoulder",),
            split_deficit_deg=7.0,
        )

    md_without = _run(None)
    captured: dict = {}
    md_with = _run(captured)
    assert set(md_without) == set(md_with)
    for k in md_without:
        assert md_without[k] == md_with[k], f"{k} 가 out-param 때문에 움직였다"
    assert captured, "out-param 을 줬는데 아무 순간도 기록되지 않았다"


# ── (8) 하위호환 — 기본 호출 크래시 0 ────────────────────────────────────────


def test_default_call_without_out_param_does_not_crash():
    """measured_at_out 기본값(None) 호출은 종전과 동일하게 동작한다."""
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    md = app._build_deduction_measured_deviations(
        angles=usr, profile=_unregistered_profile(), assessments=[],
        dimension_scores={}, quantification=_quant(),
        reference_dtw_match=_identity_match(T), reference_angles=ref,
    )
    assert md["angle_vs_reference__left_shoulder"] == pytest.approx(40.0)


def test_moment_omits_video_sec_when_fps_unavailable(monkeypatch):
    """fps 를 못 구하면 초를 추측하지 않는다 — frame_idx 만 남는다."""
    monkeypatch.setattr(app, "_FRAME_EXTRACTOR", None)
    monkeypatch.setattr(
        app, "_pipeline_frame_fps",
        lambda: (_ for _ in ()).throw(ModuleNotFoundError("frame_extractor")),
    )
    T = 10
    ref = _angles(T)
    usr = _angles(T)
    usr[:, _LEFT_SHOULDER] = 130.0
    out: dict = {}
    _build(
        usr=usr, ref=ref, profile=_unregistered_profile(),
        quantification=_quant(), match=_identity_match(T), out=out,
    )
    moment = out["angle_vs_reference__left_shoulder"]
    assert "frame_idx" in moment
    assert "video_sec" not in moment
