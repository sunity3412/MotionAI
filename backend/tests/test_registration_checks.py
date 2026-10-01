"""Phase 38 (38-05) — 등록 실패 판정 순수 함수(registration_checks) + hold_height.floor_reference_valid.

Phase 38 D-09 / Success ②: 실패 4형(사람 미검출 · 여러 명 · 서 있는 시작 없음 · 저신뢰) 이 각각 **합성 입력**으로
강제된다 — 이 파일은 그중 셋(저신뢰 · 여러 명 · 서 있는 시작 없음)을, 사람 미검출은 엔진 예외라
test_rtmw_engine.py 가 맡는다. Pod · Firestore · S3 호출 0.

이 테스트가 단언하는 것 (수치 채우기 아님 — 구조와 판정):
  (1) 여러 명 비율은 순서 무관 — 2/10 통과 · 3/10 실패(>= 경계) · 4/10 실패, 섞어도 같다 (리뷰 R15b)
  (2) 저신뢰는 관절별 신뢰도 중앙값 < 문턱인 관절을 report joints 순서로 낸다 (12관절 한국어 라벨)
  (3) 서 있는 시작의 "측정 불가"(재료 신뢰도 미달) 와 "측정 결과 위반"(바닥 아래) 이 분리된다 (리뷰 R6)
  (4) check_registration 순서 = low_confidence → no_standing_start → ok (리뷰 R6). 여러 명은 2026-10-01 부터
      기록만(38-14 실물: 정적 화분이 사람으로 잡혀 legacy 11개 중 9개가 0.30 을 넘음, belle 결정) — verdict.person_ratio
  (5) 입력 계약(plan-checker 차단 1): report 는 keypointReport dict — 비Mapping 은 TypeError(fail-loud),
      형상 불량 dict 는 예외 없이 fail-closed(T-38-05-1)
  (6) 바닥 규칙은 서 있음의 PROXY — 웅크린 합성 좌표도 통과한다는 반례 박제 (리뷰 R6)
  (7) hold_height.floor_reference_valid 공개 함수 True / False / None
합성 헬퍼 `_report`/`_pose` 는 test_hold_height.py 의 것을 그대로 복제 (같은 형상 = 38-07 이 만드는 dict).
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared import models  # noqa: E402
from sunity_shared.analysis import hold_height as hh  # noqa: E402
from sunity_shared.analysis import registration_checks as rc  # noqa: E402
from sunity_shared.analysis.keypoint_frame import _KEYPOINT_NAMES, KeypointReport  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_LABEL_KO  # noqa: E402

_JOINTS = [
    "left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee",
    "left_hand", "right_hand", "left_ankle", "right_ankle", "left_elbow", "right_elbow",
]

T, STAND = 40, 10


def _report(ys: dict, T: int, conf: dict | None = None) -> dict:
    """관절별 y 배열(또는 상수)로 keypointReport dict 를 만든다. x 는 0.5 고정, 신뢰도 기본 0.9 (test_hold_height 복제)."""
    X = np.zeros((T, len(_JOINTS), 2))
    C = np.full((T, len(_JOINTS)), 0.9)
    X[:, :, 0] = 0.5
    for name, y in ys.items():
        X[:, _JOINTS.index(name), 1] = y
    for name, c in (conf or {}).items():
        C[:, _JOINTS.index(name)] = c
    return {"joints": list(_JOINTS), "frames": T, "data": X.reshape(-1).tolist(), "confidence": C.reshape(-1).tolist()}


def _pose(T: int, stand: int, *, hip: float, low_ankle: float, high_ankle: float, hand: float) -> dict:
    """앞 `stand` 프레임은 서 있음(어깨 0.5 · 발목 0.8 → 몸길이 0.3, 바닥 0.8), 이후는 창 자세 (test_hold_height 복제)."""
    def seq(standing, window):
        v = np.full(T, window, dtype=float)
        v[:stand] = standing
        return v
    return {
        "left_shoulder": seq(0.5, 0.35), "right_shoulder": seq(0.5, 0.35),
        "left_hip": seq(0.65, hip), "right_hip": seq(0.65, hip),
        "left_ankle": seq(0.8, low_ankle), "right_ankle": seq(0.8, high_ankle),
        "left_hand": seq(0.6, hand + 0.1), "right_hand": seq(0.3, hand),
    }


def _standing_report(conf: dict | None = None) -> dict:
    """서 있다가 창 자세로 — 정상 등록 영상의 합성판 (test_hold_height 학생 쌍과 같은 값)."""
    return _report(_pose(T, STAND, hip=0.605, low_ankle=0.795, high_ankle=0.74, hand=0.325), T, conf)


def _floor_violation_report(conf: dict | None = None) -> dict:
    """창 30프레임 중 10프레임에서 발목이 바닥(0.8)보다 0.20 몸길이 아래 → 10% 분위 위반 (test_hold_height (9) 와 같은 값)."""
    ys = _pose(T, STAND, hip=0.56, low_ankle=0.73, high_ankle=0.70, hand=0.32)
    ys["left_ankle"][20:30] = 0.8 + 0.3 * 0.20
    return _report(ys, T, conf)


def _set_conf(report: dict, name: str, value: float, frames=slice(None)) -> dict:
    """report 의 한 관절 신뢰도를 (일부 프레임만) 바꾼다."""
    C = np.asarray(report["confidence"]).reshape(T, len(_JOINTS))
    C[frames, _JOINTS.index(name)] = value
    report["confidence"] = C.reshape(-1).tolist()
    return report


def _crouch_report() -> dict:
    """웅크린 채 시작해 웅크린 채 있는 합성 — 어깨 0.62 · 엉덩이 0.70 · 발목 0.80(세로 몸길이 0.18 > 0), 창에서도 같은 자세."""
    ys = {
        "left_shoulder": 0.62, "right_shoulder": 0.62, "left_hip": 0.70, "right_hip": 0.70,
        "left_ankle": 0.80, "right_ankle": 0.80, "left_hand": 0.75, "right_hand": 0.75,
    }
    return _report({n: np.full(T, v) for n, v in ys.items()}, T)


COUNTS_2_OF_10 = [1] * 8 + [2] * 2
COUNTS_3_OF_10 = [2] * 3 + [1] * 7
COUNTS_4_OF_10 = [2] * 4 + [1] * 6


def _shuffled(counts: list[int]) -> list[int]:
    out = list(counts)
    random.Random(0).shuffle(out)
    return out


# ── (1) 여러 명 — 비율은 순서 무관, 경계 2/10 · 3/10 · 4/10 (리뷰 R15b) ──────────────────────────


def test_multiple_people_ratio_definition():
    assert rc.multiple_people_ratio(COUNTS_2_OF_10) == pytest.approx(0.2)
    assert rc.multiple_people_ratio([]) == 0.0


@pytest.mark.parametrize(
    "counts, expected",
    [(COUNTS_2_OF_10, False), (COUNTS_3_OF_10, True), (COUNTS_4_OF_10, True)],
    ids=["2of10-pass", "3of10-fail-at-boundary", "4of10-fail"],
)
def test_multiple_people_boundaries(counts, expected):
    """3/10 = 0.30 은 `>=` 경계라 실패 — 문턱 상수 자체는 [ASSUMED A6], 시험 영상 2차로만 조정."""
    assert rc.is_multiple_people(counts) is expected


@pytest.mark.parametrize(
    "counts, expected",
    [(COUNTS_2_OF_10, False), (COUNTS_3_OF_10, True), (COUNTS_4_OF_10, True)],
    ids=["2of10", "3of10", "4of10"],
)
def test_multiple_people_is_order_independent(counts, expected):
    """같은 목록을 random.Random(0) 으로 섞어도 같은 판정 — 비율 함수는 순서를 읽지 않는다."""
    shuffled = _shuffled(counts)
    assert shuffled != counts
    assert rc.is_multiple_people(shuffled) is expected
    assert rc.multiple_people_ratio(shuffled) == pytest.approx(rc.multiple_people_ratio(counts))


def test_multiple_people_empty_and_zero_counts_are_false():
    assert rc.is_multiple_people([]) is False
    assert rc.is_multiple_people([0, 0, 1]) is False   # 0 은 N>=2 가 아니다 (미검출 프레임)


# ── (2) 저신뢰 — 관절별 중앙값, report 순서, 12관절 한국어 라벨 ──────────────────────────────────


def test_low_confidence_joints_lists_low_median_joints_in_report_order():
    rep = _standing_report(conf={"right_ankle": 0.2, "left_ankle": 0.2})
    assert rc.low_confidence_joints(rep) == ["left_ankle", "right_ankle"]   # dict 삽입 순서가 아니라 joints 순서


def test_low_confidence_joints_empty_when_all_confident():
    assert rc.low_confidence_joints(_standing_report()) == []


def test_joint_labels_ko():
    assert rc.joint_labels_ko(["left_ankle", "right_hand"]) == ["왼쪽 발목", "오른쪽 손목"]


def test_keypoint_label_ko_covers_the_12_keypoints():
    assert set(rc.KEYPOINT_LABEL_KO) == set(_KEYPOINT_NAMES)
    assert len(rc.KEYPOINT_LABEL_KO) == 12
    for name, label in JOINT_LABEL_KO.items():   # 8개 어법은 skeleton 그대로 (문자열 복사 0)
        assert rc.KEYPOINT_LABEL_KO[name] == label


# ── (3) 서 있는 시작 — 측정 가능성(재료 신뢰도) 과 측정 결과(바닥 위반) 분리 (리뷰 R6) ─────────────


def test_standing_start_measurable_normal():
    assert rc.standing_start_measurable(_standing_report(), n_stand=STAND) == (True, [])


def test_standing_start_measurable_flags_ankles_when_stand_window_ankles_unreadable():
    rep = _standing_report()
    _set_conf(rep, "left_ankle", 0.2, slice(0, STAND))
    _set_conf(rep, "right_ankle", 0.2, slice(0, STAND))
    assert rc.standing_start_measurable(rep, n_stand=STAND) == (False, ["left_ankle", "right_ankle"])


def test_standing_start_measurable_flags_shoulders_only():
    rep = _standing_report()
    _set_conf(rep, "left_shoulder", 0.2, slice(0, STAND))
    _set_conf(rep, "right_shoulder", 0.2, slice(0, STAND))
    assert rc.standing_start_measurable(rep, n_stand=STAND) == (False, ["left_shoulder", "right_shoulder"])


def test_standing_start_measurable_short_window_is_not_a_confidence_problem():
    """창이 MIN_STAND_FRAMES 미만이면 신뢰도 문제가 아니라 창 문제 — no_standing_start 쪽으로 간다."""
    assert hh.MIN_STAND_FRAMES > 2
    assert rc.standing_start_measurable(_standing_report(), n_stand=2) == (True, [])


def test_standing_start_ok_true_for_standing_start():
    assert rc.standing_start_ok(_standing_report(), n_stand=STAND) is True


def test_standing_start_ok_false_when_window_foot_goes_below_the_stand_floor():
    """서 있는 프레임 발목 0.6(어깨 0.3, 몸길이 0.3) · 창 낮은발 0.83 → lowFoot = (0.6-0.83)/0.3 < -0.10."""
    ys = _pose(T, STAND, hip=0.605, low_ankle=0.83, high_ankle=0.74, hand=0.325)
    for n in ("left_shoulder", "right_shoulder"):
        ys[n][:STAND] = 0.3
    for n in ("left_ankle", "right_ankle"):
        ys[n][:STAND] = 0.6
    assert rc.standing_start_ok(_report(ys, T), n_stand=STAND) is False


def test_standing_start_ok_false_when_stand_window_too_short():
    assert rc.standing_start_ok(_standing_report(), n_stand=2) is False


def test_standing_start_ok_false_when_everything_is_unreadable():
    """신뢰도 전부 0.1 → 바닥을 못 세워 False(fail-closed). check_registration 은 이 입력을 먼저 low_confidence 로 잡는다."""
    rep = _standing_report(conf={n: 0.1 for n in _JOINTS})
    assert rc.standing_start_ok(rep, n_stand=STAND) is False


def test_floor_rule_is_a_proxy_crouch_passes():
    """자세 분류기가 아니라는 반례 박제(리뷰 R6) — 이 테스트가 깨지면 규칙이 바뀐 것.

    바닥 일관성 규칙은 "어깨~발목 세로 길이 양수 + 창에서 발이 바닥 아래로 안 내려감" 만 본다. 웅크린 채
    시작해 웅크린 채 있는 합성 좌표도 그 둘을 만족하므로 통과한다 — 서 있음의 PROXY 이지 서 있음의 증명이
    아니다. 실영상 오분류율은 [미확인]. 이 phase 는 분류기를 더하지 않고 가이드 ④ 문구("서 있는 자세인지는
    사람이 확인해 주세요") 로 한계를 남긴다.
    """
    assert rc.standing_start_ok(_crouch_report(), n_stand=STAND) is True
    assert rc.check_registration([1] * T, _crouch_report(), n_stand=STAND).ok is True


# ── (4) check_registration — 순서 low_confidence → no_standing_start → ok · 여러 명은 기록만(38-14) ─────────


def test_check_registration_low_confidence_beats_multiple_people_and_floor_violation():
    """발목 0.2 + 바닥 위반 형상 + N=2 30% → low_confidence(발목 2개) — 다른 두 사유보다 먼저 (리뷰 R6)."""
    rep = _floor_violation_report(conf={"left_ankle": 0.2, "right_ankle": 0.2})
    v = rc.check_registration(COUNTS_3_OF_10, rep, n_stand=STAND)
    assert v.ok is False
    assert v.reason == models.REG_ERR_LOW_CONFIDENCE
    assert v.joints == ("left_ankle", "right_ankle")


def test_check_registration_stand_material_below_min_conf_is_low_confidence_not_no_standing_start():
    """관절 중앙값은 문턱 위(0.9)지만 서 있는 창의 발목만 MIN_CONF 미만 — 옛 순서라면 바닥을 못 구해
    no_standing_start 로 오분류됐다(리뷰 R6 로컬 재현). 지금은 low_confidence + 발목 목록."""
    rep = _standing_report()
    _set_conf(rep, "left_ankle", hh.MIN_CONF - 0.01, slice(0, STAND))
    _set_conf(rep, "right_ankle", hh.MIN_CONF - 0.01, slice(0, STAND))
    assert rc.low_confidence_joints(rep) == []            # 전체 중앙값은 0.9 — 이 검사만으로는 안 잡힌다
    v = rc.check_registration([1] * T, rep, n_stand=STAND)
    assert v.reason == models.REG_ERR_LOW_CONFIDENCE
    assert v.joints == ("left_ankle", "right_ankle")


def test_check_registration_floor_violation_is_no_standing_start():
    v = rc.check_registration([1] * T, _floor_violation_report(), n_stand=STAND)
    assert v.ok is False
    assert v.reason == models.REG_ERR_NO_STANDING_START
    assert v.detail == "floor_violation"
    assert v.joints == ()


def test_check_registration_multiple_people_is_recorded_not_failed():
    """38-14 (belle 2026-10-01): N>=2 프레임 40% 여도 등록은 통과 — 비율만 person_ratio 로 실린다.
    실물 근거: ref-sideway-spin 원본의 둘째 상자 = 매 프레임 같은 자리의 화분(ratio 0.538)."""
    v = rc.check_registration(COUNTS_4_OF_10, _standing_report(), n_stand=STAND)
    assert v.ok is True
    assert v.reason is None
    assert v.person_ratio == pytest.approx(0.4)


def test_check_registration_ratio_at_old_boundary_does_not_fail():
    """옛 경계 3/10 = 0.30(>= 라 실패였다) 도 이제 실패가 아니다 — 판정은 바닥 규칙만 본다."""
    v = rc.check_registration(COUNTS_3_OF_10, _standing_report(), n_stand=STAND)
    assert v.ok is True
    assert v.person_ratio == pytest.approx(0.3)


def test_check_registration_no_standing_start_carries_person_ratio():
    """여러 명이면서 바닥 위반이면 no_standing_start — 비율은 그 verdict 에도 기록으로 실린다."""
    v = rc.check_registration(COUNTS_3_OF_10, _floor_violation_report(), n_stand=STAND)
    assert v.reason == models.REG_ERR_NO_STANDING_START
    assert v.person_ratio == pytest.approx(0.3)


def test_check_registration_never_returns_multiple_people():
    """REG_ERR_MULTIPLE_PEOPLE 상수는 앱 문구 매핑 때문에 남지만 판정에서는 나오지 않는다."""
    for counts in (COUNTS_4_OF_10, [2] * T, [3] * T):
        for rep in (_standing_report(), _floor_violation_report()):
            assert rc.check_registration(counts, rep, n_stand=STAND).reason != models.REG_ERR_MULTIPLE_PEOPLE


def test_check_registration_low_confidence_has_no_person_ratio():
    rep = _standing_report(conf={n: 0.1 for n in _JOINTS})
    assert rc.check_registration([2] * T, rep, n_stand=STAND).person_ratio is None


def test_check_registration_ok():
    v = rc.check_registration(COUNTS_2_OF_10, _standing_report(), n_stand=STAND)
    assert v == rc.RegistrationVerdict(ok=True, reason=None, person_ratio=pytest.approx(0.2))
    assert v.joints == () and v.detail == ""


def test_check_registration_short_stand_window_detail():
    v = rc.check_registration([1] * T, _standing_report(), n_stand=2)
    assert v.reason == models.REG_ERR_NO_STANDING_START
    assert v.detail == "stand_window_too_short"


def test_check_registration_all_unreadable_is_low_confidence_with_all_joints():
    rep = _standing_report(conf={n: 0.1 for n in _JOINTS})
    v = rc.check_registration([1] * T, rep, n_stand=STAND)
    assert v.reason == models.REG_ERR_LOW_CONFIDENCE
    assert v.joints == tuple(_JOINTS)


def test_verdict_reasons_are_models_constants():
    """reason 문자열은 models.REG_ERR_* 그대로 — 38-07 이 REGISTRATION_ERROR_MESSAGE 키로 바로 쓴다."""
    assert models.REG_ERR_LOW_CONFIDENCE == "low_confidence"
    assert models.REG_ERR_MULTIPLE_PEOPLE == "multiple_people"
    assert models.REG_ERR_NO_STANDING_START == "no_standing_start"
    for reason in (
        rc.check_registration([1] * T, _floor_violation_report(conf={"left_knee": 0.1}), n_stand=STAND).reason,
        rc.check_registration([1] * T, _floor_violation_report(), n_stand=STAND).reason,
    ):
        assert reason in models.REGISTRATION_ERROR_MESSAGE


# ── (5) 입력 계약 — 비Mapping 은 TypeError(fail-loud), 형상 불량 dict 는 fail-closed (차단 1 · T-38-05-1) ──


def _real_keypoint_report() -> KeypointReport:
    """build_keypoint_report 가 돌려주는 타입 그대로 — 38-07 이 _dataclass_to_camel_case_dict 를 빼먹으면 이 값이 들어온다."""
    return KeypointReport(
        version="1.1", joints=list(_JOINTS), frames=1, fps=10.0, data=[0.0] * 24, confidence=[0.9] * 12,
        reliability=["high"], axis_data=[0.0] * 6, axis_mask=[False] * 3, warnings=[],
    )


def test_non_mapping_report_raises_type_error():
    kr = _real_keypoint_report()
    calls = (
        lambda r: rc.check_registration([1], r, n_stand=STAND),
        lambda r: rc.low_confidence_joints(r),
        lambda r: rc.standing_start_measurable(r, n_stand=STAND),
        lambda r: rc.standing_start_ok(r, n_stand=STAND),
    )
    for call in calls:
        with pytest.raises(TypeError) as ei:
            call(kr)
        assert "Mapping" in str(ei.value) and "_dataclass_to_camel_case_dict" in str(ei.value)
        with pytest.raises(TypeError):
            call(None)
    # hold_height 쪽은 손대지 않았다 — 비Mapping 에 조용히 None (카드 문장 소비처와 공유하는 _arrays 그대로)
    assert hh.floor_reference_valid(kr, (STAND, T)) is None
    assert hh.floor_reference_valid(None, (STAND, T)) is None


def test_malformed_dict_is_fail_closed_without_raising():
    """형상 불량 dict 는 예외 없이 ok=False (T-38-05-1). low_confidence 가 아니다 — 38-03 문구의 {joints} 가 비지 않게."""
    bad = {"joints": [], "frames": 0}
    assert rc.low_confidence_joints(bad) == []
    assert rc.standing_start_measurable(bad, n_stand=STAND) == (True, [])
    assert rc.standing_start_ok(bad, n_stand=STAND) is False
    v = rc.check_registration([1, 1, 1], bad, n_stand=STAND)
    assert v.ok is False
    assert v.reason == models.REG_ERR_NO_STANDING_START
    assert v.detail == "no_floor_reference"
    truncated = _standing_report()
    truncated["data"] = truncated["data"][:-2]
    assert rc.check_registration([1] * T, truncated, n_stand=STAND).ok is False


@pytest.mark.parametrize(
    "report",
    [
        _standing_report(),
        _standing_report(conf={"left_ankle": 0.2, "right_ankle": 0.2}),
        _standing_report(conf={n: 0.1 for n in _JOINTS}),
        _set_conf(_standing_report(), "left_shoulder", 0.2, slice(0, STAND)),
        _floor_violation_report(),
        _crouch_report(),
        {"joints": [], "frames": 0},
    ],
    ids=["normal", "ankles-low", "all-low", "one-shoulder-stand-low", "floor-violation", "crouch", "malformed"],
)
def test_low_confidence_verdict_always_names_at_least_one_joint(report):
    """low_confidence 는 항상 부위 목록이 있다 — 38-03 페이지가 "잘 안 보인 부위: {joints}" 를 그대로 찍는다."""
    for counts in ([1] * T, COUNTS_3_OF_10):
        v = rc.check_registration(counts, report, n_stand=STAND)
        if v.reason == models.REG_ERR_LOW_CONFIDENCE:
            assert len(v.joints) >= 1
        else:
            assert v.joints == ()


# ── (6) 문턱·창 상수 — [ASSUMED] 이지만 이웃 값과의 관계는 잠근다 ────────────────────────────────


def test_thresholds_are_coherent_with_hold_height():
    """저신뢰 중앙값 문턱이 측정 신뢰 하한보다 낮으면 "측정 불가를 먼저" 순서가 무너진다."""
    assert rc.LOW_CONFIDENCE_MEDIAN_MIN >= hh.MIN_CONF
    assert 0.0 < rc.MULTI_PERSON_FRAME_RATIO <= 1.0
    assert rc.STANDING_START_DEFAULT_SEC > 0.0


@pytest.mark.parametrize(
    "fps, expected",
    [(9.0, 9), (10, 10), (29.97, 30), (0.0, 0), (-5.0, 0), (float("nan"), 0), (None, 0)],
)
def test_default_stand_frames_from_fps(fps, expected):
    """서 있는 구간 기본 = 첫 STANDING_START_DEFAULT_SEC 초(1.0, [ASSUMED A5]) 를 프레임 수로 — fps 를 못 믿으면 0."""
    assert rc.default_stand_frames(fps) == expected


def test_zero_stand_frames_fails_closed_as_stand_window_too_short():
    v = rc.check_registration([1] * T, _standing_report(), n_stand=rc.default_stand_frames(0.0))
    assert v.reason == models.REG_ERR_NO_STANDING_START and v.detail == "stand_window_too_short"


# ── (7) hold_height.floor_reference_valid — 공개 함수 True / False / None ──────────────────────────


def test_floor_reference_valid_true_false_none():
    assert hh.floor_reference_valid(_standing_report(), (STAND, T)) is True
    assert hh.floor_reference_valid(_floor_violation_report(), (STAND, T)) is False
    assert hh.floor_reference_valid({"joints": [], "frames": 0}, (STAND, T)) is None       # 형상 불량
    assert hh.floor_reference_valid(_standing_report(), (hh.MIN_STAND_FRAMES - 1, T)) is None   # 창 이전 부족
    assert hh.floor_reference_valid(_standing_report(), (STAND, STAND + hh.MIN_WINDOW_FRAMES - 1)) is None  # 창 짧음
    unreadable = _standing_report()
    _set_conf(unreadable, "left_ankle", hh.MIN_CONF - 0.01, slice(0, STAND))
    _set_conf(unreadable, "right_ankle", hh.MIN_CONF - 0.01, slice(0, STAND))
    assert hh.floor_reference_valid(unreadable, (STAND, T)) is None                        # 재료 신뢰도 미달


def test_floor_reference_valid_uses_the_same_statistic_as_hold_window_heights():
    """한 프레임 튐(10% 분위 무시) 과 잡음 폭 2배 안(-0.06) 은 통과 — hold_window_heights 와 같은 판정."""
    one = _pose(T, STAND, hip=0.56, low_ankle=0.73, high_ankle=0.70, hand=0.32)
    one["left_ankle"][20] = 0.8 + 0.3 * 0.20
    assert hh.floor_reference_valid(_report(one, T), (STAND, T)) is True
    ok = _pose(T, STAND, hip=0.56, low_ankle=0.73, high_ankle=0.70, hand=0.32)
    ok["left_ankle"][20:30] = 0.8 + 0.3 * 0.06
    assert hh.floor_reference_valid(_report(ok, T), (STAND, T)) is True
    stu = _standing_report()
    for rep in (one, ok):
        assert hh.hold_window_heights(stu, _report(rep, T), (STAND, T), (STAND, T)) is not None
    assert hh.hold_window_heights(stu, _floor_violation_report(), (STAND, T), (STAND, T)) is None
    assert math.isfinite(hh.hold_window_heights(stu, _report(one, T), (STAND, T), (STAND, T))["lowFoot"]["diff"])
