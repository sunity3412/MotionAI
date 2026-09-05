"""card_photo_audit 순수 함수 단위 테스트 (quick-260905-mvm) — 네트워크 0, 관측값 하드코딩.

케이스 = 09-05 실측 대장의 알려진 불일치 5장 + 정상 3장 (수치 채우기 금지, CLAUDE.md §7):
불일치 5건은 belle 이 먼저 찾은 것(pdshape 오른팔꿈치·파워스핀 왼어깨)과 오케스트레이터
확인분(엘보 3장). 관측 토큰은 대장의 한국어 판독(등허리·허벅지·겨드랑이·머리)을
card_gates part enum 으로 옮긴 것. 정상 3장은 대장에서 이상 없음으로 본 카드 — 관측은
제목 부위(또는 그 인접 부위)로 기록. 각 카드의 상대 패널(대장에서 이상 없던 쪽)도 제목
부위로 둔다 — 대장의 "21장 중 5장" 은 패널 단위가 아니라 카드 단위 집계였다.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis import card_gates as cg
from sunity_shared.analysis import card_photo_audit as cpa

# (이름, criterion, joint, user_observed, ref_observed, user_marked, ref_marked, 기대 불일치)
_LEDGER_0905 = [
    # ── 알려진 불일치 5 ────────────────────────────────────────────────────────
    ("pdshape 6.1s 오른팔꿈치 = 등허리",
     "angle_vs_reference__right_elbow", "right_elbow", "back_waist", "elbow",
     True, True, True),
    ("파워스핀 왼어깨 = 허벅지",
     "angle_vs_reference__left_shoulder", "left_shoulder", "thigh", "shoulder",
     True, True, True),
    ("엘보 오른팔꿈치 기준 패널 = 겨드랑이",
     "angle_vs_reference__right_elbow", "right_elbow", "elbow", "armpit",
     True, True, True),
    ("엘보 왼어깨 = 양쪽 허벅지 (두 패널 다)",
     "angle_vs_reference__left_shoulder", "left_shoulder", "thigh", "thigh",
     True, True, True),
    ("엘보 참고 왼어깨 = 머리 (criterion 없음, 표시 없음)",
     None, "left_shoulder", "head", "shoulder",
     False, False, True),
    # ── 정상 3 ─────────────────────────────────────────────────────────────────
    ("pdshape 5.3s 왼팔꿈치 = 팔꿈치",
     "angle_vs_reference__left_elbow", "left_elbow", "elbow", "elbow",
     True, True, False),
    ("클라임 무릎 = 무릎 / 기준 허벅지 (인접 부위 허용)",
     "angle_vs_reference__left_knee", "left_knee", "knee", "thigh",
     True, True, False),
    ("피터팬 벌림각 = 엉덩이 / 허벅지",
     "split_angle", "left_hip", "hip", "thigh",
     True, True, False),
]


@pytest.mark.parametrize("case", _LEDGER_0905, ids=[c[0] for c in _LEDGER_0905])
def test_ledger_0905_case(case):
    name, crit, joint, uo, ro, um, rm, want_mismatch = case
    exp = cpa.expected_parts(crit, joint)
    assert exp, name
    res = cpa.audit_card(exp, uo, ro, user_marked=um, ref_marked=rm)
    assert cpa.is_mismatch(res) is want_mismatch, (name, res)
    if not want_mismatch:
        assert res == {"userOk": True, "refOk": True, "flags": []}


def test_ledger_0905_reproduces_five_mismatches():
    """순수 함수만으로 대장의 불일치 5건이 재현되고 정상 3건은 깨끗하다."""
    mism = []
    for name, crit, joint, uo, ro, um, rm, _ in _LEDGER_0905:
        res = cpa.audit_card(cpa.expected_parts(crit, joint), uo, ro,
                             user_marked=um, ref_marked=rm)
        if cpa.is_mismatch(res):
            mism.append(name)
    assert len(mism) == 5
    assert any("pdshape 6.1s 오른팔꿈치" in n for n in mism)   # belle 발견
    assert any("파워스핀 왼어깨" in n for n in mism)           # belle 발견
    assert not any(n.startswith(("pdshape 5.3s", "클라임", "피터팬")) for n in mism)


def test_mismatch_flag_side_and_marked_semantics():
    """표시 있는 측 = mark_mismatch, 표시 없는 측 = part_not_shown, 정상 측은 플래그 0."""
    exp = cpa.expected_parts("angle_vs_reference__right_elbow", "right_elbow")
    # 기준 패널만 틀림 (엘보 오른팔꿈치 기준=겨드랑이)
    res = cpa.audit_card(exp, "elbow", "armpit", user_marked=True, ref_marked=True)
    assert res == {"userOk": True, "refOk": False, "flags": ["ref:mark_mismatch"]}
    # 표시 없는 참고 카드 — 위치를 묻지 않고 "보이는가"만
    res = cpa.audit_card(exp, "back_waist", "elbow", user_marked=False, ref_marked=True)
    assert res["flags"] == ["user:part_not_shown"] and res["userOk"] is False
    # 양쪽 다 틀림
    res = cpa.audit_card(exp, "thigh", "head", user_marked=True, ref_marked=False)
    assert res["flags"] == ["user:mark_mismatch", "ref:part_not_shown"]


def test_expected_parts_derivations():
    """criterion 우선(벌림/뻗음 계열·angle_vs_reference__), 없으면 joint 로 같은 파생."""
    assert cpa.expected_parts("angle_vs_reference__left_elbow", None) == {"elbow", "hand", "shoulder"}
    assert cpa.expected_parts("angle_vs_reference__right_shoulder", "x") == {
        "shoulder", "armpit", "chest", "back_waist"}
    assert cpa.expected_parts("angle_vs_reference__left_hip", None) == {
        "hip", "thigh", "back_waist", "abdomen"}
    assert cpa.expected_parts("angle_vs_reference__right_knee", None) == {"knee", "thigh", "foot"}
    assert cpa.expected_parts("split_angle", "left_knee") == {"hip", "thigh"}
    assert cpa.expected_parts("leg_extension", None) == {"thigh", "hip", "knee"}
    assert cpa.expected_parts("arm_extension", None) == {"elbow", "hand", "shoulder"}
    # 참고 카드 (criterion 없음) → joint 파생
    assert cpa.expected_parts(None, "left_shoulder") == cpa.expected_parts(
        "angle_vs_reference__left_shoulder", None)
    assert cpa.expected_parts("", "right_knee") == {"knee", "thigh", "foot"}
    # 미지 criterion 은 joint 로 폴백, 둘 다 미지면 빈 집합
    assert cpa.expected_parts("pole_gap", "left_elbow") == {"elbow", "hand", "shoulder"}
    assert cpa.expected_parts("pole_gap", "split") == frozenset()
    assert cpa.expected_parts(None, None) == frozenset()
    assert cpa.expected_parts("angle_vs_reference__nose", None) == frozenset()
    # 좌/우 무관 — 같은 종류는 같은 집합
    assert cpa.expected_parts(None, "left_hip") == cpa.expected_parts(None, "right_hip")


def test_audit_card_unreadable_and_missing_are_not_mismatch():
    """눈이 못 본 것(unclear/error/어휘 밖/관측 없음)은 틀린 것이 아니다 — None + 사유."""
    exp = cpa.expected_parts(None, "left_knee")
    for bad in ("unclear", "error", "bent", "왼무릎"):
        res = cpa.audit_card(exp, bad, "knee", user_marked=True, ref_marked=True)
        assert res["userOk"] is None and res["refOk"] is True, bad
        assert res["flags"] == ["user:unreadable"]
        assert not cpa.is_mismatch(res)
    res = cpa.audit_card(exp, None, None, user_marked=True, ref_marked=True)
    assert res == {"userOk": None, "refOk": None,
                   "flags": ["user:unobserved", "ref:unobserved"]}
    assert not cpa.is_mismatch(res)


def test_audit_card_no_expectation():
    """허용 집합이 비면 감사 불가 — 불일치로 세지 않는다."""
    res = cpa.audit_card(frozenset(), "elbow", "elbow", user_marked=True, ref_marked=True)
    assert res == {"userOk": None, "refOk": None, "flags": ["no_expectation"]}
    assert not cpa.is_mismatch(res)
    assert cpa.audit_card(set(), "x", "y", user_marked=False, ref_marked=False)["flags"] == [
        "no_expectation"]


def test_vocab_lockstep_with_card_gates_part_enum():
    """토큰 어휘 = card_gates part enum − unclear. 허용 집합은 전부 어휘 안."""
    assert cpa.PART_VOCAB == cg.PART_TOKENS
    for kind in ("left_elbow", "right_shoulder", "left_hip", "right_knee"):
        assert cpa.expected_parts(None, kind) <= cpa.PART_VOCAB
    for crit in ("split_angle", "leg_extension", "arm_extension"):
        assert cpa.expected_parts(crit, None) <= cpa.PART_VOCAB
    assert cpa.UNREAD == {"unclear", "error"}


def test_module_is_pure_no_numpy_import():
    """순수 모듈 — numpy/boto3/card_gates 를 import 하지 않는다 (plan 제약)."""
    import importlib
    import sys

    src = importlib.import_module("sunity_shared.analysis.card_photo_audit").__file__
    text = open(src, encoding="utf-8").read()
    for banned in ("import numpy", "import boto3", "from .card_gates", "import card_gates",
                   "urllib"):
        assert banned not in text, banned
    assert "sunity_shared.analysis.card_photo_audit" in sys.modules
