"""quick-260802-tie Task 1 — 대표 프레임 **동점** 판정에 keypoint 신뢰도를 넣는 게이트.

quick-260801-gbk 가 정한 규칙("record 가 보고한 집계값에 가장 가까운 프레임")은 그대로다.
여기서 잠그는 것은 셋:

  ① 동점이 아니면 종전과 **byte-동일** (신뢰도가 최근접 규칙을 이기지 못한다).
  ② 동점일 때만 신뢰도가 가르고, 그 동점 폭은 **record 가 값을 publish 하는 해상도**다
     — 임의 상수가 아님을 엔진 출력에서 되읽어 대조한다.
  ③ argmax 금지 — 창 어딘가에 신뢰도가 훨씬 높은 프레임이 있어도, 집계값에서 멀면
     절대 뽑히지 않는다.

전부 순수 함수/빌더 테스트 — Pod/S3/Firestore/Gemini 호출 0.
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
from sunity_shared.analysis import (  # noqa: E402
    deduction_engine,
    dimensions,
    moment,
    technique,
    vision_veto,
)
from sunity_shared.analysis.motiondtw import (  # noqa: E402
    MotionMatch,
    per_joint_representative_frames,
)
from sunity_shared.analysis.pose_frame import Keypoint2D  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_ANGLES, JOINT_KEYS  # noqa: E402

_LEFT_SHOULDER = JOINT_KEYS.index("left_shoulder")
_LEFT_KNEE = JOINT_KEYS.index("left_knee")

# 테스트 stub 어댑터의 target_fps — **일부러 프로덕션 기본값이 아닌 수**(gbk 선례).
_STUB_FPS = 12.0


class _Ext:
    target_fps = _STUB_FPS


@pytest.fixture(autouse=True)
def _stub_fps(monkeypatch):
    monkeypatch.setattr(app, "_FRAME_EXTRACTOR", _Ext())


# ── 허용오차의 출처 — 상수를 손으로 맞춰 둔 것이 아님을 엔진 출력으로 증명 ──────


class _AvailableQuant:
    """엔진의 quant-unavailable 폴백을 피하기 위한 최소 stub (record 경로 진입용)."""

    quantificationStatus = "available"
    bodyRelativeNotches = None


def test_tie_eps_is_the_record_published_resolution():
    """`moment.TIE_EPS` == 감점 record 가 `measuredValue` 를 내보내는 해상도.

    상수를 문서로 주장하지 않고 **엔진에 소수점 아래가 긴 값을 먹여** 방출된 자릿수를
    센다. 엔진이 반올림 자릿수를 바꾸면 이 게이트가 먼저 깨진다 — 그때는 허용오차의
    근거가 사라진 것이므로 tie-break 폭도 함께 다시 정해야 한다.
    """
    # 소수 아래가 길고 자릿수가 우연히 짧아지지 않는 입력.
    md = {"leg_extension": 41.23456789}
    breakdown = deduction_engine.tally(
        _AvailableQuant(), None,
        dimension_overall=80.0,
        measured_deviations=md,
        dimension_scores={},
        baseline_kind=None,
    )
    recs = [r.to_dict() for r in breakdown.records]
    legs = [r for r in recs if r["criterion"] == "leg_extension"]
    assert legs, "leg_extension record 가 방출되지 않으면 이 게이트는 성립하지 않는다"

    def _kept_decimals(v: float) -> int:
        """방출값이 실제로 유지한 소수 자릿수 (문자열 파싱 없이 반올림 동등으로)."""
        return next(d for d in range(0, 12) if round(v, d) == v)

    # measuredValue 와 deviation 은 같은 해상도로 방출된다 — 둘 다 본다.
    decimals = {
        _kept_decimals(legs[0]["measuredValue"]),
        _kept_decimals(legs[0]["deviation"]),
    }
    assert decimals == {moment.RECORD_VALUE_DECIMALS}
    assert moment.TIE_EPS == pytest.approx(10.0 ** -moment.RECORD_VALUE_DECIMALS)


# ── select_moment_index — 순수 규칙 ────────────────────────────────────────────


def test_no_confidence_source_is_plain_argmin():
    """신뢰도 출처가 없으면 종전 argmin(동점=첫 index) 그대로."""
    gaps = [0.5, 0.0, 0.0, 0.2]
    assert moment.select_moment_index(gaps) == 1


def test_confidence_never_beats_a_strictly_closer_candidate():
    """집계값에서 먼 후보는 신뢰도가 아무리 높아도 뽑히지 않는다 (argmax 금지).

    허용오차(0.01°) 바깥이면 index 3 의 신뢰도 1.0 이 index 1 의 0.10 을 이기지 못한다.
    이 단언이 깨지면 tie-break 가 창 전체를 훑는 argmax 로 번진 것이다.
    """
    gaps = [5.0, 0.0, 5.0, 0.05]
    conf = {0: 0.9, 1: 0.10, 2: 0.9, 3: 1.0}
    assert moment.select_moment_index(gaps, confidence=conf.get) == 1


def test_confidence_breaks_an_exact_tie():
    gaps = [0.0, 0.0, 0.0]
    conf = {0: 0.18, 1: 0.46, 2: 0.75}
    assert moment.select_moment_index(gaps, confidence=conf.get) == 2


def test_tie_window_is_exactly_tie_eps_wide():
    """허용오차 경계 — 안쪽(<=)은 동점, 바깥쪽은 아니다."""
    inside = [0.0, moment.TIE_EPS]
    outside = [0.0, moment.TIE_EPS * 2]
    conf = {0: 0.10, 1: 0.99}
    assert moment.select_moment_index(inside, confidence=conf.get) == 1
    assert moment.select_moment_index(outside, confidence=conf.get) == 0


def test_equal_confidence_keeps_the_closest_candidate():
    """동률이면 최근접(=종전 선택)을 유지한다 — 엄격 부등호."""
    gaps = [0.0, 0.0]
    assert moment.select_moment_index(gaps, confidence=lambda _i: 0.7) == 0


def test_unknown_confidence_is_not_low_confidence():
    """신뢰도 미상(None)은 0 이 아니다 — 모를 때는 종전 선택을 유지한다."""
    gaps = [0.0, 0.0]
    # 최근접 후보의 신뢰도를 모르면 비교 기준점이 없다 → 종전 그대로.
    assert moment.select_moment_index(
        gaps, confidence=lambda i: None if i == 0 else 0.99
    ) == 0
    # 도전자 쪽이 미상이면 그 후보가 이길 수 없다.
    assert moment.select_moment_index(
        gaps, confidence=lambda i: 0.30 if i == 0 else None
    ) == 0


def test_out_of_range_confidence_is_rejected():
    """0..1 밖·비유한 신뢰도는 판정에 쓰이지 않는다(오염된 출처 방어)."""
    gaps = [0.0, 0.0]
    for bad in (1.5, -0.2, float("nan"), float("inf"), "0.9", True, None):
        assert moment.select_moment_index(
            gaps, confidence=lambda i, b=bad: 0.30 if i == 0 else b
        ) == 0


def test_all_non_finite_gaps_is_fail_closed():
    assert moment.select_moment_index([np.inf, np.nan]) is None
    assert moment.select_moment_index([]) is None


# ── 신뢰도 집계 — 관절각을 이루는 keypoint 의 최솟값 ──────────────────────────


def _pose_frame(conf_by_kp: dict):
    class _PF:
        keypoints_2d = {
            name: Keypoint2D(x=0.5, y=0.5, visibility=v)
            for name, v in conf_by_kp.items()
        }

    return _PF()


def test_joint_confidence_is_the_worst_constituent_keypoint():
    """평균이 아니라 최솟값 — 표시 게이트가 3점 전부를 요구하기 때문이다.

    무릎각은 hip·knee·ankle 3점으로 이뤄진다. 발목만 무너진 프레임을 평균으로 재면
    골반의 높은 신뢰도가 그것을 가려, 고른 프레임에서 정작 각이 안 그려진다.
    """
    a, v, c = JOINT_ANGLES["left_knee"]
    conf = joint = None  # noqa: F841 — 아래 dict 가 실제 입력
    frames = [_pose_frame({a: 0.95, v: 0.60, c: 0.18})]
    f = moment.joint_confidence_from_pose_frames(frames)
    assert f(0, ("left_knee",)) == pytest.approx(0.18)


def test_joint_confidence_spans_every_joint_of_the_criterion():
    """여러 관절을 쓰는 criterion(line)은 그 관절 전체의 최솟값."""
    lk = JOINT_ANGLES["left_knee"]
    rk = JOINT_ANGLES["right_knee"]
    conf = {n: 0.90 for n in (*lk, *rk)}
    conf[rk[2]] = 0.22
    f = moment.joint_confidence_from_pose_frames([_pose_frame(conf)])
    assert f(0, ("left_knee", "right_knee")) == pytest.approx(0.22)


def test_missing_keypoint_is_unknown_not_zero():
    """keypoint 가 없으면 None — 0.0 으로 보정하면 그 프레임을 '나쁘다'고 단정하게 된다."""
    a, v, _c = JOINT_ANGLES["left_knee"]
    f = moment.joint_confidence_from_pose_frames([_pose_frame({a: 0.9, v: 0.9})])
    assert f(0, ("left_knee",)) is None
    assert f(99, ("left_knee",)) is None  # 범위 밖
    assert f(0, ("not_a_joint",)) is None


# ── 무회귀 — 신뢰도 미전달이면 세 산출 지점 모두 종전과 동일 ─────────────────


def _knee_extend_profile():
    exp = {
        k: technique.JOINT_EXTEND if k.endswith("knee") else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(
        name="t", category="unknown", joint_expectations=exp
    )


def test_representative_frames_unchanged_without_confidence():
    """dimensions/motiondtw 두 helper 는 frame_confidence 미전달 시 종전 산출."""
    T = 12
    ang = np.full((T, len(JOINT_KEYS)), 170.0, dtype=float)
    ang[5, _LEFT_KNEE] = 150.0
    prof = _knee_extend_profile()
    dev = dimensions.extension_deviation(ang, prof)
    target = float(dev[_LEFT_KNEE])
    assert dimensions.extension_representative_frame(
        ang, prof, "left_knee", target
    ) == dimensions.extension_representative_frame(
        ang, prof, "left_knee", target, frame_confidence=None
    )
    ref = np.full((T, len(JOINT_KEYS)), 170.0, dtype=float)
    path = [(i, i) for i in range(T)]
    assert per_joint_representative_frames(path, ang, ref, 0) == (
        per_joint_representative_frames(path, ang, ref, 0, frame_confidence=None)
    )


# ── 빌더 배선 — pointed window 의 median 짝수 동점을 신뢰도가 가른다 ──────────


def _quant(wm_deltas, user_frames):
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="available",
        angleDeltas=None,
        bodyRelativeNotches=None,
        windowMedianAngleDeltas={
            "deltas": list(wm_deltas),
            "sourceFrameIndices": {"user": list(user_frames), "reference": [5]},
            "windowPolicy": "worst_pose_center_pm_2_median",
        },
        warnings=(),
    )


def _identity_match(T):
    return MotionMatch(
        start=0, end=T, ref_start=0, ref_end=T, distance=0.0,
        path=[(i, i) for i in range(T)],
    )


def _unregistered_profile():
    return technique.TechniqueProfile(
        name="미등록", category="unknown", joint_expectations={}
    )


def _build(usr, ref, quant, out, **kw):
    return app._build_deduction_measured_deviations(
        angles=usr, profile=_unregistered_profile(), assessments=[],
        dimension_scores={}, quantification=quant,
        reference_dtw_match=_identity_match(usr.shape[0]), reference_angles=ref,
        measured_at_out=out, vision_pointed_joints=("left_shoulder",), **kw,
    )


def _shoulder_even_tie_case():
    """window 유한 프레임이 짝수 → median 이 가운데 두 값의 평균 = 구조적 동점.

    student_deg 는 그 median 이고, 두 후보(4, 5)는 그 값에서 정확히 같은 거리에 있다.
    어느 쪽도 그 값을 갖지 않는다 — 그래서 프레임 번호가 정하던 자리다.
    """
    T = 12
    ref = np.full((T, len(JOINT_KEYS)), 170.0, dtype=float)
    usr = np.full((T, len(JOINT_KEYS)), 170.0, dtype=float)
    usr[4, _LEFT_SHOULDER] = 120.0
    usr[5, _LEFT_SHOULDER] = 140.0
    student_deg = 130.0  # (120 + 140) / 2
    wm = [{
        "joint": "left_shoulder", "delta_deg": -40.0, "student_deg": student_deg,
    }]
    return usr, ref, _quant(wm, [4, 5])


def test_window_median_even_tie_is_broken_by_confidence():
    a, v, c = JOINT_ANGLES["left_shoulder"]
    usr, ref, quant = _shoulder_even_tie_case()

    out_plain: dict = {}
    _build(usr, ref, quant, out_plain)
    assert out_plain["angle_vs_reference__left_shoulder"]["frame_idx"] == 4

    # 프레임 5 의 어깨 keypoint 가 더 신뢰할 만하다 → 같은 값을 더 잘 보여준다.
    frames = [
        _pose_frame({a: 0.9, v: 0.9, c: 0.9 if t != 4 else 0.20})
        for t in range(usr.shape[0])
    ]
    out_tie: dict = {}
    _build(
        usr, ref, quant, out_tie,
        frame_confidence=moment.joint_confidence_from_pose_frames(frames),
    )
    assert out_tie["angle_vs_reference__left_shoulder"]["frame_idx"] == 5


def test_tiebreak_does_not_touch_the_score_substrate():
    """md(점수 substrate)는 tie-break 유무와 무관하게 키·값 모두 같다."""
    a, v, c = JOINT_ANGLES["left_shoulder"]
    usr, ref, quant = _shoulder_even_tie_case()
    frames = [
        _pose_frame({a: 0.9, v: 0.9, c: 0.9 if t != 4 else 0.20})
        for t in range(usr.shape[0])
    ]
    md_plain = _build(usr, ref, quant, {})
    md_tie = _build(
        usr, ref, quant, {},
        frame_confidence=moment.joint_confidence_from_pose_frames(frames),
    )
    assert md_plain.keys() == md_tie.keys()
    for k in md_plain:
        assert md_plain[k] == md_tie[k], k


def test_tiebreak_does_not_move_a_non_tied_moment():
    """동점이 아니면 신뢰도가 있어도 프레임이 움직이지 않는다 (빌더 경로 무회귀)."""
    a, v, c = JOINT_ANGLES["left_shoulder"]
    T = 12
    ref = np.full((T, len(JOINT_KEYS)), 170.0, dtype=float)
    usr = np.full((T, len(JOINT_KEYS)), 170.0, dtype=float)
    # 유한 프레임 3개(홀수) → median 은 가운데 값 자체 = 동점 없음.
    usr[4, _LEFT_SHOULDER] = 120.0
    usr[5, _LEFT_SHOULDER] = 130.0
    usr[6, _LEFT_SHOULDER] = 145.0
    wm = [{"joint": "left_shoulder", "delta_deg": -40.0, "student_deg": 130.0}]
    quant = _quant(wm, [4, 5, 6])
    # 신뢰도는 오히려 프레임 6 이 최고 — 그래도 5 를 벗어나면 안 된다.
    frames = [
        _pose_frame({a: 0.9, v: 0.9, c: 0.99 if t == 6 else 0.20})
        for t in range(T)
    ]
    out: dict = {}
    _build(
        usr, ref, quant, out,
        frame_confidence=moment.joint_confidence_from_pose_frames(frames),
    )
    assert out["angle_vs_reference__left_shoulder"]["frame_idx"] == 5
