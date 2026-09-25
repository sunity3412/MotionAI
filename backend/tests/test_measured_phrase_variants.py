"""quick-260924-vj1 — 잰 값 조건부 승인 문장(phrasebook `measuredVariants`)의 선택과 병합.

belle 2026-09-24: kip-up 실수 카드 판정지 4/4 ○ → *"짜맞추는거면 이게 무슨 소용일지"*. 그래서 문장은
분석마다 잰 값(유지 구간 몸 높이 + 겨드랑이 창 상수 부호)이 고르고, 못 재거나 어긋나면 지금 문구 그대로다.
이 테스트가 단언하는 것:
  (1) 승인 문장은 판정지 그대로(글자 단위) — 바꾸려면 새 판정이 필요하다
  (2) 새 문장도 화면 카피 게이트(숫자·%·내부 용어) 안에 있다
  (3) 방출은 승인 문장을 먼저 채우고 나머지 슬롯은 문구집 그대로, 변형이 없으면 byte-동일
  (4) 파이프라인 선택기: 패턴 성립 → 대체 + 대표 짝 순간 / 조건 하나라도 빠지면 {} (mode3·동작 불일치·
      상수 경로 밖·창 없음·프레임 불일치·몸이 안 낮음·팔이 닫힘·대표 짝 없음·fps 없음)
  (5) 방출이 순간의 출처 하나를 record 에 박는다(measuredPattern · atFrameIdx/atVideoSec · atRefVideoSec)
실 Gemini/Pod/S3/Firestore 호출 0.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared import models  # noqa: E402
from sunity_shared.analysis import phrasebook  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402

_KEY = "angle_vs_reference__left_shoulder"
_MOTION = "ref-kip-up"
_PATTERN = "body_low_arm_open"
# belle 2026-09-24 판정지(quick-260924-uff judge_kipup_card.png) ○ 문장 — 글자 단위 그대로.
_APPROVED = {
    "statusLine": "돌기 시작해서 끝날 때까지 몸이 정은지 선수보다 낮게 떠 있어요",
    "whyLine": "손 높이는 같은데 몸이 손 아래로 처졌고, 왼팔이 몸통에서 더 벌어져 있어요",
    "cueLine": "왼팔을 굽혀 옆구리에 붙인 채 돌아보세요",
}
_NJ = len(JOINT_KEYS)
_LS = JOINT_KEYS.index("left_shoulder")
_KP_JOINTS = [
    "left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee",
    "left_hand", "right_hand", "left_ankle", "right_ankle", "left_elbow", "right_elbow",
]


# ── (1)(2) 데이터 ────────────────────────────────────────────────────────────


def test_approved_sentences_are_verbatim():
    assert phrasebook.assemble_measured_variant(_MOTION, _KEY, _PATTERN) == _APPROVED


@pytest.mark.parametrize(
    "motion, criterion, pattern",
    [
        ("ref-power-spin", _KEY, _PATTERN),
        (_MOTION, "angle_vs_reference__right_shoulder", _PATTERN),
        (_MOTION, _KEY, "no_such_pattern"),
        (None, _KEY, _PATTERN),
        ("__common__", _KEY, _PATTERN),
    ],
)
def test_other_combinations_have_no_variant(motion, criterion, pattern):
    assert phrasebook.assemble_measured_variant(motion, criterion, pattern) == {}


def test_variant_sentences_are_under_the_screen_copy_gates():
    rendered = phrasebook.rendered_copy_strings()
    pb = json.loads((Path(__file__).resolve().parents[1] / "data" / "phrasebook.json").read_text(encoding="utf-8"))
    banned = pb["_meta"]["screenVocabularyGate"]["words"]
    for text in _APPROVED.values():
        assert text in rendered  # 금지어·% 게이트(test_phrasebook_forbidden)가 이 문장도 본다
        assert not re.search(r"[0-9%]", text)
        assert not [w for w in banned if w in text]


# ── (3) 방출 병합 ────────────────────────────────────────────────────────────


def _result() -> dict:
    return {
        "deductionBreakdown": {
            "records": [
                {"criterion": _KEY, "ruleId": "angle_vs_reference_over_tol_linear", "points": -16.6,
                 "measuredValue": 33.86, "deviation": 13.86, "deviationSource": "reference_relative"},
            ]
        }
    }


def _variant(**over):
    v = {"slots": dict(_APPROVED), "pattern": _PATTERN, "atFrameIdx": 21, "atVideoSec": 2.106,
         "atRefVideoSec": 2.533}
    v.update(over)
    return v


def _emit(measured_phrases):
    result = _result()
    app._attach_translation_emission(
        result, mode=models.MODE_EXPERT, motion_id=_MOTION, prev_doc=None,
        uid="u", analysis_id="a", measured_phrases=measured_phrases,
    )
    return result["deductionBreakdown"]["records"][0]


def test_variant_fills_the_three_slots_and_keeps_the_rest_from_the_phrasebook():
    rec = _emit({_KEY: _variant()})
    base = phrasebook.assemble_phrases(_MOTION, _KEY)
    for slot, text in _APPROVED.items():
        assert rec[slot] == text
    for slot in ("coachQuestion", "exerciseId", "exerciseReason"):
        assert rec[slot] == base[slot]


@pytest.mark.parametrize("measured", [None, {}, {"angle_vs_reference__right_elbow": _variant()}])
def test_without_a_variant_for_this_record_nothing_changes(measured):
    assert _emit(measured) == _emit(None)
    assert _emit(None)["statusLine"] == phrasebook.assemble_phrases(_MOTION, _KEY)["statusLine"]


def test_variant_stamps_the_single_moment_source_on_the_record():
    """영상 멈춤·카드가 물려받을 순간 = 대표 짝. measured_at(집계값 최근접)보다 우선한다."""
    result = _result()
    app._attach_translation_emission(
        result, mode=models.MODE_EXPERT, motion_id=_MOTION, prev_doc=None, uid="u", analysis_id="a",
        measured_at={_KEY: {"frame_idx": 14, "video_sec": 1.40}},
        measured_phrases={_KEY: _variant()},
    )
    rec = result["deductionBreakdown"]["records"][0]
    assert rec["measuredPattern"] == _PATTERN
    assert (rec["atFrameIdx"], rec["atVideoSec"], rec["atRefVideoSec"]) == (21, 2.106, 2.533)


def test_without_variant_the_moment_rule_is_unchanged():
    result = _result()
    app._attach_translation_emission(
        result, mode=models.MODE_EXPERT, motion_id=_MOTION, prev_doc=None, uid="u", analysis_id="a",
        measured_at={_KEY: {"frame_idx": 14, "video_sec": 1.40}}, measured_phrases=None,
    )
    rec = result["deductionBreakdown"]["records"][0]
    assert (rec["atFrameIdx"], rec["atVideoSec"]) == (14, 1.40)
    assert "measuredPattern" not in rec and "atRefVideoSec" not in rec


# ── (4) 파이프라인 선택기 ────────────────────────────────────────────────────


def _angles(T: int = 60, arm_offset: float = 34.0):
    t = np.arange(T, dtype=float)
    ref = np.stack([120.0 + 25.0 * np.sin(0.11 * (j + 1) * t + 0.5 * j) for j in range(_NJ)], axis=1)
    stu = ref.copy()
    stu[:, _LS] += arm_offset
    return stu, ref


def _kp(T: int, *, hip: float, low_ankle: float, hand: float, stand: int = 10) -> dict:
    """앞 `stand` 프레임은 서 있음(어깨 0.5 · 발목 0.8), 이후 창 자세. 오른손이 그립(위) 손."""
    X = np.zeros((T, len(_KP_JOINTS), 2))
    X[:, :, 0] = 0.45
    X[:, _KP_JOINTS.index("right_hand"), 0] = 0.55   # 그립(위) 손 = 폴 위치
    X[:, _KP_JOINTS.index("left_hand"), 0] = 0.55

    def put(name, standing, window):
        v = np.full(T, window, dtype=float)
        v[:stand] = standing
        X[:, _KP_JOINTS.index(name), 1] = v

    put("left_shoulder", 0.5, 0.35); put("right_shoulder", 0.5, 0.35)
    put("left_hip", 0.65, hip); put("right_hip", 0.65, hip)
    put("left_ankle", 0.8, low_ankle); put("right_ankle", 0.8, low_ankle - 0.05)
    put("left_hand", 0.6, hand + 0.1); put("right_hand", 0.3, hand)
    C = np.full((T, len(_KP_JOINTS)), 0.9)
    return {"joints": list(_KP_JOINTS), "frames": T, "data": X.reshape(-1).tolist(), "confidence": C.reshape(-1).tolist()}


def _select(**over):
    stu, ref = over.pop("angles", None) or _angles()
    _dev, match, _seg, _a = app._deviation_against(stu, ref, _NJ)
    kw = dict(
        mode=models.MODE_EXPERT, motion_id=_MOTION, reference_motion_id=_MOTION,
        result=_result(), angles=stu, reference_angles=ref, reference_exec_window=(10, 50),
        reference_dtw_match=match,
        student_keypoint_report=_kp(len(stu), hip=0.605, low_ankle=0.795, hand=0.325),
        reference_keypoint_report=_kp(len(ref), hip=0.56, low_ankle=0.73, hand=0.32),
        constant_joints=["left_shoulder"], uid="u", analysis_id="a",
        student_fps=9.9733, reference_fps=15.0,
    )
    kw.update(over)
    return app._measured_phrase_variants(**kw)


def test_measured_pattern_selects_the_approved_sentences(caplog):
    caplog.set_level("INFO")
    out = _select()
    assert list(out) == [_KEY]
    v = out[_KEY]
    assert v["slots"] == _APPROVED and v["pattern"] == _PATTERN
    assert 10 <= v["atFrameIdx"] < 50  # 창 안의 짝
    assert v["atVideoSec"] == pytest.approx(v["atFrameIdx"] / 9.9733)
    assert 10 / 15.0 <= v["atRefVideoSec"] < 50 / 15.0
    assert any("hold heights reference=ref-kip-up" in r.getMessage() for r in caplog.records)
    assert any("measured variant applied criterion=angle_vs_reference__left_shoulder" in r.getMessage()
               for r in caplog.records)


@pytest.mark.parametrize(
    "override",
    [
        {"mode": models.MODE_SELF},
        {"reference_motion_id": "ref-power-spin"},
        {"motion_id": None},
        {"constant_joints": []},                      # 그 관절을 상수 경로가 안 쟀다
        {"reference_exec_window": None},
        {"reference_dtw_match": None},
        {"student_fps": 0.0},                         # 초를 못 정하면 순간도 문장도 없다
        {"reference_fps": None},
    ],
)
def test_missing_precondition_keeps_the_current_copy(override):
    assert _select(**override) == {}


def test_frame_count_mismatch_keeps_the_current_copy():
    stu, _ref = _angles()
    assert _select(student_keypoint_report=_kp(len(stu) - 1, hip=0.605, low_ankle=0.795, hand=0.325)) == {}


def test_body_not_low_keeps_the_current_copy():
    assert _select(student_keypoint_report=_kp(60, hip=0.56, low_ankle=0.73, hand=0.32)) == {}


def test_arm_closed_keeps_the_current_copy():
    assert _select(angles=_angles(arm_offset=-34.0)) == {}


def test_no_representative_pair_means_no_variant_at_all():
    """몸이 그립 손과 **같은 x** (쪽을 못 정함) → 대표 짝 없음 → 문장도 안 바꾼다(반쪽 카드 금지)."""
    kp = _kp(60, hip=0.605, low_ankle=0.795, hand=0.325)
    X = np.asarray(kp["data"]).reshape(60, len(_KP_JOINTS), 2)
    X[:, :, 0] = 0.5
    kp["data"] = X.reshape(-1).tolist()
    assert _select(student_keypoint_report=kp) == {}


def test_selector_never_touches_the_score_fields():
    result = _result()
    before = copy.deepcopy(result)
    stu, ref = _angles()
    _dev, match, _seg, _a = app._deviation_against(stu, ref, _NJ)
    app._measured_phrase_variants(
        mode=models.MODE_EXPERT, motion_id=_MOTION, reference_motion_id=_MOTION, result=result,
        angles=stu, reference_angles=ref, reference_exec_window=(10, 50), reference_dtw_match=match,
        student_keypoint_report=_kp(60, hip=0.605, low_ankle=0.795, hand=0.325),
        reference_keypoint_report=_kp(60, hip=0.56, low_ankle=0.73, hand=0.32),
        constant_joints=["left_shoulder"], uid="u", analysis_id="a",
        student_fps=9.9733, reference_fps=15.0,
    )
    assert result == before


# ── (6) 몸 전체 패턴 — power-spin "낮은 위치에서 돈다" (quick-260925-nnt) ─────────────────────
# belle 09-25 봉인 정답: "도는 위치의 높이가 다르고, 다리 벌림이 다르다". 문장 3줄은 belle ○× 대기(초안).

_PS_MOTION = "ref-power-spin"
_PS_KEY = "leg_extension"
_PS_PATTERN = "body_low"
_PS_DRAFT = {
    "statusLine": "정은지 선수보다 낮은 위치에서 돌고 있어요",
    "whyLine": "돌기 시작해서 끝날 때까지 엉덩이가 정은지 선수보다 눈에 띄게 아래에 있고, 무릎도 덜 펴져 있어요",
    "cueLine": "몸을 더 높이 끌어올린 채로, 무릎을 끝까지 편 채 돌아보세요",
}


def test_power_spin_sentences_are_verbatim_and_under_the_gates():
    assert phrasebook.assemble_measured_variant(_PS_MOTION, _PS_KEY, _PS_PATTERN) == _PS_DRAFT
    rendered = phrasebook.rendered_copy_strings()
    pb = json.loads((Path(__file__).resolve().parents[1] / "data" / "phrasebook.json").read_text(encoding="utf-8"))
    banned = pb["_meta"]["screenVocabularyGate"]["words"]
    for text in _PS_DRAFT.values():
        assert text in rendered
        assert not re.search(r"[0-9%]", text)
        assert not [w for w in banned if w in text]
    # 관절 패턴 문장은 power-spin 에 없고, 몸 전체 패턴 문장은 kip-up 에 없다 — 동작 단위 승인.
    assert phrasebook.assemble_measured_variant(_PS_MOTION, _KEY, _PATTERN) == {}
    assert phrasebook.assemble_measured_variant(_MOTION, _KEY, _PS_PATTERN) == {}


def _ps_result() -> dict:
    return {"deductionBreakdown": {"records": [
        {"criterion": _PS_KEY, "ruleId": "leg_extension_over_tol_linear", "points": -20.0,
         "measuredValue": 140.95, "deviation": 19.05, "deviationSource": "ipsf_absolute"},
    ]}}


def _ps_select(**over):
    # 학생: 엉덩이 0.15 몸길이 낮음(몸길이 0.3, 바닥 0.8) — 09-24 실측(−0.184)의 방향. 손 높이는 조건 밖.
    kw = dict(
        motion_id=_PS_MOTION, reference_motion_id=_PS_MOTION, result=_ps_result(), constant_joints=[],
        student_keypoint_report=_kp(60, hip=0.605, low_ankle=0.795, hand=0.42),
        reference_keypoint_report=_kp(60, hip=0.56, low_ankle=0.73, hand=0.32),
    )
    kw.update(over)
    return _select(**kw)


def test_whole_body_pattern_hosts_on_a_non_angle_record(caplog):
    caplog.set_level("INFO")
    out = _ps_select()
    assert list(out) == [_PS_KEY]
    v = out[_PS_KEY]
    assert v["pattern"] == _PS_PATTERN and v["slots"] == _PS_DRAFT
    assert isinstance(v["atFrameIdx"], int) and v["atVideoSec"] > 0 and v["atRefVideoSec"] > 0
    assert "measured variant applied criterion=leg_extension pattern=body_low signed=-" in caplog.text


def test_whole_body_pattern_needs_the_hip_low_for_the_whole_window():
    """엉덩이가 기준과 같은 높이면 power-spin 문장을 얻지 않는다(손·발 높이는 조건 밖)."""
    assert _ps_select(student_keypoint_report=_kp(60, hip=0.56, low_ankle=0.795, hand=0.42)) == {}


def test_whole_body_pattern_needs_a_determinable_grip_side():
    stu = _kp(60, hip=0.605, low_ankle=0.795, hand=0.42)
    X = np.asarray(stu["data"]).reshape(60, len(_KP_JOINTS), 2)
    X[:, _KP_JOINTS.index("left_hand"), 1] = X[:, _KP_JOINTS.index("right_hand"), 1]  # 두 손 같은 높이 → 동률
    stu["data"] = X.reshape(-1).tolist()
    assert _ps_select(student_keypoint_report=stu) == {}


def test_kip_up_selection_is_unchanged_by_the_new_pattern():
    """관절 패턴 경로 byte-동일 — kip-up 실수는 여전히 왼어깨 record 에 body_low_arm_open 하나."""
    out = _select()
    assert list(out) == [_KEY] and out[_KEY]["pattern"] == _PATTERN


def test_whole_body_emission_stamps_pattern_and_moment_on_the_leg_record():
    result = _ps_result()
    app._attach_translation_emission(
        result, mode=models.MODE_EXPERT, motion_id=_PS_MOTION, prev_doc=None, uid="u", analysis_id="a",
        measured_phrases={_PS_KEY: {"slots": dict(_PS_DRAFT), "pattern": _PS_PATTERN, "atFrameIdx": 30,
                                    "atVideoSec": 3.0, "atRefVideoSec": 2.9}},
    )
    rec = result["deductionBreakdown"]["records"][0]
    assert rec["measuredPattern"] == _PS_PATTERN
    assert (rec["statusLine"], rec["whyLine"], rec["cueLine"]) == tuple(_PS_DRAFT.values())
    assert (rec["atFrameIdx"], rec["atVideoSec"], rec["atRefVideoSec"]) == (30, 3.0, 2.9)
