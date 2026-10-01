"""Phase 38 (38-05) — 등록 진단 순수 함수(registration_checks) + hold_height.floor_reference_valid.

2026-10-01 belle 결정(quick-261001-thx): 등록은 **분석 불가만** 막는다 — 저신뢰 · 서 있는 시작 · 여러 명은
어떤 조합이어도 등록을 막지 않고 진단으로만 남는다("하나씩 고치면 절대 안돼"). 사람 미검출은 엔진 예외라
test_rtmw_engine.py 와 test_register_reference_pipeline.py 가 맡는다. Pod · Firestore · S3 호출 0.

이 테스트가 단언하는 것 (수치 채우기 아님 — 구조와 진단 값):
  (1) 여러 명 비율은 순서 무관 — 2/10 · 3/10(>= 경계) · 4/10, 섞어도 같다 (리뷰 R15b, 원시 함수 유지)
  (2) 저신뢰는 관절별 신뢰도 중앙값 < 문턱인 관절을 report joints 순서로 낸다 (12관절 한국어 라벨)
  (3) 서 있는 시작의 "측정 불가"(재료 신뢰도 미달) 와 "측정 결과 위반"(바닥 아래) 이 분리된다 (리뷰 R6)
  (4) diagnose_registration — 세 진단을 동시에 정확히 싣고, 실패 사유 필드 자체가 없다. 구조 잠금:
      모듈 코드 식별자에 세 실패 상수(low_confidence · no_standing_start · multiple_people)가 없다
  (5) 입력 계약(plan-checker 차단 1): report 는 keypointReport dict — 비Mapping 은 TypeError(fail-loud),
      형상 불량 dict 는 예외 없이 no_floor_reference 진단
  (6) 바닥 규칙은 서 있음의 PROXY — 웅크린 합성 좌표도 통과한다는 반례 박제 (리뷰 R6)
  (7) hold_height.floor_reference_valid 공개 함수 True / False / None
합성 헬퍼 `_report`/`_pose` 는 test_hold_height.py 의 것을 그대로 복제 (같은 형상 = 38-07 이 만드는 dict).
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
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
    """신뢰도 전부 0.1 → 바닥을 못 세워 False. 진단에서는 저신뢰 관절 전부 + no_floor_reference 로 함께 남는다."""
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
    assert rc.diagnose_registration([1] * T, _crouch_report(), n_stand=STAND).standing_start == rc.STANDING_START_OK


# ── (4) diagnose_registration — 진단만, 실패 사유 없음 (belle 2026-10-01, quick-261001-thx) ─────────────


def test_diagnosis_carries_all_three_at_once_without_raising():
    """저신뢰(발목 0.2) + 바닥 위반 형상 + N=2 30% — 옛 판정이면 low_confidence 하나로 끝났다.
    진단은 셋을 동시에 싣는다(하나만 고치는 수리가 아니라 사유를 낼 길 자체를 지웠다)."""
    rep = _floor_violation_report(conf={"left_ankle": 0.2, "right_ankle": 0.2})
    d = rc.diagnose_registration(COUNTS_3_OF_10, rep, n_stand=STAND)
    assert d.person_ratio == pytest.approx(0.3)
    assert d.low_confidence_joints == ("left_ankle", "right_ankle")
    assert d.stand_material_unreadable == ("left_ankle", "right_ankle")
    # 발목 재료가 MIN_CONF 미만이라 바닥을 못 세운다 — 기존 _standing_start_detail 과 같은 값.
    assert d.standing_start == rc._standing_start_detail(rep, STAND) == rc.DETAIL_NO_FLOOR_REFERENCE
    assert d.n_stand == STAND


def test_diagnosis_has_no_failure_field():
    """ok / reason / joints / detail 같은 실패 필드가 없다 — 호출측이 실패로 분기할 재료가 없다."""
    names = {f.name for f in dataclasses.fields(rc.RegistrationDiagnostics)}
    assert names == {"person_ratio", "low_confidence_joints", "stand_material_unreadable", "standing_start", "n_stand"}
    assert not hasattr(rc, "check_registration")
    assert not hasattr(rc, "RegistrationVerdict")


def test_diagnosis_values_equal_the_raw_functions():
    """진단 값 = 기존 원시 함수 결과 그대로(문턱 숫자 무변경)."""
    rep = _standing_report()
    _set_conf(rep, "left_ankle", hh.MIN_CONF - 0.01, slice(0, STAND))
    d = rc.diagnose_registration(COUNTS_4_OF_10, rep, n_stand=STAND)
    assert d.person_ratio == pytest.approx(rc.multiple_people_ratio(COUNTS_4_OF_10))
    assert list(d.low_confidence_joints) == rc.low_confidence_joints(rep) == []
    assert list(d.stand_material_unreadable) == rc.standing_start_measurable(rep, STAND)[1] == ["left_ankle"]


def test_diagnosis_floor_violation_token():
    d = rc.diagnose_registration([1] * T, _floor_violation_report(), n_stand=STAND)
    assert d.standing_start == rc.DETAIL_FLOOR_VIOLATION == "floor_violation"
    assert d.low_confidence_joints == () and d.stand_material_unreadable == ()


def test_diagnosis_ok_token_for_standing_start():
    d = rc.diagnose_registration(COUNTS_2_OF_10, _standing_report(), n_stand=STAND)
    assert d.standing_start == rc.STANDING_START_OK == "ok"
    assert d.person_ratio == pytest.approx(0.2)


def test_diagnosis_short_stand_window_token():
    d = rc.diagnose_registration([1] * T, _standing_report(), n_stand=2)
    assert d.standing_start == rc.DETAIL_STAND_WINDOW_TOO_SHORT


def test_diagnosis_all_unreadable_lists_all_joints():
    rep = _standing_report(conf={n: 0.1 for n in _JOINTS})
    d = rc.diagnose_registration([2] * T, rep, n_stand=STAND)
    assert d.low_confidence_joints == tuple(_JOINTS)
    assert d.person_ratio == pytest.approx(1.0)


def test_diagnosis_log_fields_and_firestore_dict():
    rep = _floor_violation_report(conf={"left_ankle": 0.2})
    d = rc.diagnose_registration(COUNTS_3_OF_10, rep, n_stand=STAND)
    line = d.as_log_fields()
    for key in ("person_ratio=0.300", "low_conf=left_ankle", "stand_unreadable=left_ankle",
                "standing_start=", "n_stand=10"):
        assert key in line, (key, line)
    clean = rc.diagnose_registration([1] * T, _standing_report(), n_stand=STAND).as_log_fields()
    assert "low_conf=- " in clean and "stand_unreadable=- " in clean and "standing_start=ok" in clean

    fd = d.as_firestore_dict()
    assert fd == {
        "personRatio": pytest.approx(0.3),
        "lowConfidenceJoints": ["left_ankle"],
        "standMaterialUnreadable": ["left_ankle"],
        "standingStart": d.standing_start,
        "nStand": STAND,
    }
    # 중첩 배열 없음 — 리스트 원소는 전부 문자열(Firestore nested-array 금지).
    for v in fd.values():
        if isinstance(v, list):
            assert all(isinstance(x, str) for x in v)


def _code_identifiers(source: str) -> set[str]:
    """코드 식별자만 — ast.Name · ast.Attribute · import 이름. docstring · 주석의 이력 언급은 세지 않는다."""
    out: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, ast.alias):
            out.add(node.name)
            if node.asname:
                out.add(node.asname)
    return out


_BLOCK_CODES = ("REG_ERR_LOW_CONFIDENCE", "REG_ERR_NO_STANDING_START", "REG_ERR_MULTIPLE_PEOPLE")


def test_module_code_cannot_emit_the_three_old_failure_codes():
    """구조 잠금 — 진단 모듈은 세 실패 상수를 코드에서 참조하지 않는다(사유를 낼 길 자체가 없다)."""
    idents = _code_identifiers(inspect.getsource(rc))
    for name in _BLOCK_CODES:
        assert name not in idents, name


def test_three_codes_stay_in_models_for_app_copy_and_old_docs():
    """상수와 문구는 지우지 않는다 — 앱 문구 매핑과 2026-10-01 이전 실패 doc 이 읽는다."""
    for name in _BLOCK_CODES:
        code = getattr(models, name)
        assert code in models.REGISTRATION_ERROR_CODES
        assert code in models.REGISTRATION_ERROR_MESSAGE


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
        lambda r: rc.diagnose_registration([1], r, n_stand=STAND),
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


def test_malformed_dict_is_diagnosed_without_raising():
    """형상 불량 dict 는 예외 없이 no_floor_reference 진단 (T-38-05-1). 부위를 댈 수 없으니 저신뢰 목록은 비어 있다."""
    bad = {"joints": [], "frames": 0}
    assert rc.low_confidence_joints(bad) == []
    assert rc.standing_start_measurable(bad, n_stand=STAND) == (True, [])
    assert rc.standing_start_ok(bad, n_stand=STAND) is False
    d = rc.diagnose_registration([1, 1, 1], bad, n_stand=STAND)
    assert d.standing_start == rc.DETAIL_NO_FLOOR_REFERENCE
    assert d.low_confidence_joints == () and d.stand_material_unreadable == ()
    truncated = _standing_report()
    truncated["data"] = truncated["data"][:-2]
    assert rc.diagnose_registration([1] * T, truncated, n_stand=STAND).standing_start != rc.STANDING_START_OK


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
def test_diagnosis_never_raises_on_any_mapping(report):
    """어떤 dict 입력·사람 수 조합에서도 진단이 나온다 — 판정이 등록을 막을 예외 경로가 없다."""
    for counts in ([1] * T, COUNTS_3_OF_10, [], [3] * T):
        d = rc.diagnose_registration(counts, report, n_stand=STAND)
        assert d.standing_start in (
            rc.STANDING_START_OK, rc.DETAIL_FLOOR_VIOLATION, rc.DETAIL_NO_FLOOR_REFERENCE,
            rc.DETAIL_STAND_WINDOW_TOO_SHORT,
        )
        assert 0.0 <= d.person_ratio <= 1.0


# ── (6) 문턱·창 상수 — [ASSUMED] 이지만 이웃 값과의 관계는 잠근다 ────────────────────────────────


def test_thresholds_are_coherent_with_hold_height():
    """저신뢰 중앙값 문턱이 측정 신뢰 하한보다 낮으면 두 저신뢰 진단(중앙값 · 서 있는 창 재료)의 뜻이 뒤집힌다."""
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


def test_zero_stand_frames_is_diagnosed_as_stand_window_too_short():
    d = rc.diagnose_registration([1] * T, _standing_report(), n_stand=rc.default_stand_frames(0.0))
    assert d.standing_start == rc.DETAIL_STAND_WINDOW_TOO_SHORT and d.n_stand == 0


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
