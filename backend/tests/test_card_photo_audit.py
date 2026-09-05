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


# ── 2단 판정 adjudicate (quick-260905-ota) — 표시가 놓인 부위로 경계를 가른다 ──────
#
# 관측값은 mvm 감사 run3/run4 (09-03 라이브 21장, gemini 3회 최빈) 의 1단 토큰을 그대로
# 하드코딩. 2단(mark_part) 토큰은 이 단위의 Task 3 가 잰다 — 여기서는 두 결말(표시가 허용
# 안/밖)이 순수 함수만으로 갈리는 것을 고정한다.

_SHOULDER = cpa.expected_parts("angle_vs_reference__right_shoulder", None)
_ELBOW = cpa.expected_parts("angle_vs_reference__right_elbow", None)
_HIP = cpa.expected_parts(None, "left_hip")
_KNEE = cpa.expected_parts("angle_vs_reference__left_knee", None)


def test_adjudicate_four_endings():
    """결말 4종이 서로 배타로 갈린다 — ok/by/reason 이 plan 표 그대로."""
    # 1단 통과 — 2단 토큰이 있어도 무시(불필요)
    assert cpa.adjudicate(_SHOULDER, "shoulder", None, marked=True) == {
        "ok": True, "by": "center", "reason": "center_in_expected"}
    assert cpa.adjudicate(_SHOULDER, "armpit", "head", marked=False)["by"] == "center"
    # 1단 탈락 + 표시가 허용 안 → 통과 by mark (정중앙은 인접 맥락)
    assert cpa.adjudicate(_SHOULDER, "neck", "shoulder", marked=True) == {
        "ok": True, "by": "mark", "reason": "mark_in_expected"}
    # 1단 탈락 + 표시가 허용 밖 → 확정 불일치
    assert cpa.adjudicate(_SHOULDER, "neck", "head", marked=True) == {
        "ok": False, "by": "mark", "reason": "mark_elsewhere"}
    # 1단 탈락 + 표시 없는 패널 → 확정 (2단 없이)
    assert cpa.adjudicate(_SHOULDER, "neck", None, marked=False) == {
        "ok": False, "by": "none", "reason": "no_mark_and_center_elsewhere"}
    assert all(r["by"] in cpa.ADJ_BY for r in (
        cpa.adjudicate(_SHOULDER, t, m, marked=mk)
        for t in ("shoulder", "neck", "unclear") for m in (None, "shoulder", "head")
        for mk in (True, False)))


def test_adjudicate_undecidables():
    """판정 불가 = ok None + 사유 — 눈이 못 본 것·doc 과 그림의 어긋남은 틀린 것이 아니다."""
    # 눈이 no_mark 인데 doc 은 표시 있음
    assert cpa.adjudicate(_ELBOW, "back_waist", "no_mark", marked=True) == {
        "ok": None, "by": "mark", "reason": "mark_disagreement"}
    # 반대 방향 — doc 은 표시 없음인데 눈이 표시를 봤다
    assert cpa.adjudicate(_ELBOW, "back_waist", "elbow", marked=False)["reason"] == "mark_disagreement"
    # 2단이 필요한데 아직 안 물었음
    assert cpa.adjudicate(_ELBOW, "back_waist", None, marked=True) == {
        "ok": None, "by": "mark", "reason": "mark_unobserved"}
    # 2단 못 읽음 (unclear/error/어휘 밖)
    for bad in ("unclear", "error", "bent"):
        assert cpa.adjudicate(_ELBOW, "back_waist", bad, marked=True) == {
            "ok": None, "by": "mark", "reason": "unreadable"}, bad
    # 1단 못 읽음: 표시 없으면 판정 불가, 표시 있으면 2단으로 (못 읽음은 통과가 아니다)
    assert cpa.adjudicate(_ELBOW, "unclear", None, marked=False) == {
        "ok": None, "by": "center", "reason": "unreadable"}
    assert cpa.adjudicate(_ELBOW, None, None, marked=False)["reason"] == "unreadable"
    assert cpa.adjudicate(_ELBOW, "unclear", "elbow", marked=True)["ok"] is True
    assert cpa.adjudicate(_ELBOW, "unclear", "thigh", marked=True) == {
        "ok": False, "by": "mark", "reason": "mark_elsewhere"}
    # 허용 집합 없음
    assert cpa.adjudicate(frozenset(), "elbow", "elbow", marked=True) == {
        "ok": None, "by": "none", "reason": "no_expectation"}


def test_needs_mark_query_only_for_marked_tier1_failures():
    """2단 질의 = 표시 있는 패널 중 1단이 통과가 아닌 것만 — 비용은 탈락분에만 붙는다."""
    assert cpa.needs_mark_query(_SHOULDER, "neck", marked=True)
    assert cpa.needs_mark_query(_SHOULDER, "unclear", marked=True)     # 못 읽음도 2단
    assert cpa.needs_mark_query(_SHOULDER, None, marked=True)
    assert not cpa.needs_mark_query(_SHOULDER, "shoulder", marked=True)  # 1단 통과
    assert not cpa.needs_mark_query(_SHOULDER, "armpit", marked=True)
    assert not cpa.needs_mark_query(_SHOULDER, "neck", marked=False)    # 표시 없음 = 확정
    assert not cpa.needs_mark_query(frozenset(), "neck", marked=True)   # 감사 불가


def test_card_verdict_precedence():
    """카드 결말: mismatch > unresolved > ok, 둘 다 감사 불가면 unaudited."""
    ok_c = cpa.adjudicate(_ELBOW, "elbow", None, marked=True)
    ok_m = cpa.adjudicate(_ELBOW, "back_waist", "elbow", marked=True)
    bad = cpa.adjudicate(_ELBOW, "back_waist", "thigh", marked=True)
    none_ = cpa.adjudicate(_ELBOW, "back_waist", "no_mark", marked=True)
    noexp = cpa.adjudicate(frozenset(), "elbow", None, marked=True)
    assert cpa.card_verdict(ok_c, ok_m) == "ok"
    assert cpa.card_verdict(ok_c, bad) == "mismatch"
    assert cpa.card_verdict(bad, none_) == "mismatch"
    assert cpa.card_verdict(ok_c, none_) == "unresolved"
    assert cpa.card_verdict(noexp, noexp) == "unaudited"
    assert cpa.card_verdict(noexp, ok_c) == "unresolved"   # 한쪽만 감사 불가 = 미결
    assert set(cpa.CARD_VERDICTS) == {"ok", "mismatch", "unresolved", "unaudited"}


@pytest.mark.parametrize("name, expected, center, marked, mark_in, mark_out", [
    # 목↔어깨: pdshape [3] 오른어깨 ref (run3·run4 neck 2:1). doc refMarked=False →
    # 2단 없이 확정 — 표시가 없고 정중앙도 어깨가 아니다.
    ("pdshape 오른어깨 ref = neck, 표시 없음", _SHOULDER, "neck", False, None, None),
    # 무릎↔엉덩이: 클라임 [1] 참고 왼골반 ref (mvm run3 thigh 2:1 / run4 knee 2:1, ota knee
    # 3/3 ×2런). 참고 카드 기준 측은 게이트 B 무마킹 — 눈도 no_mark 3/3 ×2런 → 2단 없이 확정.
    ("클라임 참고 왼골반 ref = knee, 정책상 표시 없음", _HIP, "knee", False, None, None),
    # 겨드랑이↔팔꿈치: 엘보 [0] 오른팔꿈치 ref — 대장은 armpit, 눈은 10/10 elbow. 대장값으로.
    ("엘보 오른팔꿈치 ref = armpit (대장)", _ELBOW, "armpit", True, "elbow", "armpit"),
    # 팔↔다리: pdshape [2] 왼무릎 ref (run2~4 elbow 3:0). 표시 있음.
    ("pdshape 왼무릎 ref = elbow", _KNEE, "elbow", True, "knee", "elbow"),
], ids=lambda v: v if isinstance(v, str) else "")
def test_borderline_0905_split_by_mark_measurement(name, expected, center, marked,
                                                   mark_in, mark_out):
    """09-05 경계 3종(+팔↔다리 1): 1단만으로는 전부 탈락 — 결말은 표시 측정이 정한다."""
    assert center not in expected, name
    if not marked:
        assert not cpa.needs_mark_query(expected, center, marked=False)
        assert cpa.adjudicate(expected, center, None, marked=False) == {
            "ok": False, "by": "none", "reason": "no_mark_and_center_elsewhere"}
        return
    assert cpa.needs_mark_query(expected, center, marked=True)
    assert cpa.adjudicate(expected, center, mark_in, marked=True) == {
        "ok": True, "by": "mark", "reason": "mark_in_expected"}, name
    assert cpa.adjudicate(expected, center, mark_out, marked=True) == {
        "ok": False, "by": "mark", "reason": "mark_elsewhere"}, name


def test_ledger_0905_mismatches_survive_adjudication():
    """대장 5건은 표시가 정중앙과 같은 부위에 있으면 2단 뒤에도 불일치 — 2단이 진짜 불일치를 씻지 않는다."""
    for name, crit, joint, uo, ro, um, rm, want in _LEDGER_0905:
        exp = cpa.expected_parts(crit, joint)
        u = cpa.adjudicate(exp, uo, uo if cpa.needs_mark_query(exp, uo, marked=um) else None,
                           marked=um)
        r = cpa.adjudicate(exp, ro, ro if cpa.needs_mark_query(exp, ro, marked=rm) else None,
                           marked=rm)
        assert (cpa.card_verdict(u, r) == "mismatch") is want, (name, u, r)


def test_mark_vocab_lockstep_with_card_gates():
    """2단 어휘 = card_gates.MARK_PART_TOKENS (13 부위 + no_mark), no_mark 문자열 동일."""
    assert cpa.MARK_VOCAB == cg.MARK_PART_TOKENS
    assert cpa.NO_MARK == cg.NO_MARK
    assert cpa.MARK_VOCAB == cpa.PART_VOCAB | {"no_mark"}
    assert "unclear" not in cpa.MARK_VOCAB


# ── 09-05 ota 표시 측정 실측값 (run1·run2, 3회 최빈) — 허용 집합 무변경의 근거 ─────────
#
# (카드, 허용 집합, 정중앙, 표시, 기대 결말). 표시가 집합 밖인 것은 전부 원거리 —
# 인접 확장으로 구제될 사례가 없다. 두 런에서 표시 토큰이 같은 패널만 박제한다
# (엘보 [1] ref 는 run1 hip 3/3, run2 3자 동률 → 제외).
_OTA_0905_MARKS = [
    ("pdshape [5] 참고 왼어깨 user: 원이 얼굴", _SHOULDER, "head", "neck", "mark_elsewhere"),
    ("파워스핀 [1] 왼어깨 user: 각도선이 든 다리", _SHOULDER, "knee", "knee", "mark_elsewhere"),
    ("엘보 [1] 왼어깨 user: 꺾인 선이 허벅지", _SHOULDER, "thigh", "thigh", "mark_elsewhere"),
    ("엘보 [5] 참고 왼어깨 user: 원이 얼굴", _SHOULDER, "head", "head", "mark_elsewhere"),
    ("pdshape [2] 왼무릎 ref: 정중앙 팔꿈치, 표시는 무릎", _KNEE, "elbow", "knee", "mark_in_expected"),
    ("엘보 [2] 오른어깨 ref: 정중앙 팔꿈치, 표시는 어깨", _SHOULDER, "elbow", "shoulder",
     "mark_in_expected"),
]


@pytest.mark.parametrize("case", _OTA_0905_MARKS, ids=[c[0] for c in _OTA_0905_MARKS])
def test_ota_0905_measured_marks(case):
    name, expected, center, mark, reason = case
    assert cpa.needs_mark_query(expected, center, marked=True), name
    adj = cpa.adjudicate(expected, center, mark, marked=True)
    assert adj["by"] == "mark" and adj["reason"] == reason, (name, adj)
    assert adj["ok"] is (reason == "mark_in_expected")


def test_widening_shoulder_to_neck_would_pass_face_circle_cards():
    """shoulder 에 neck 을 넣으면 얼굴 위 원(pdshape·엘보 참고 왼어깨)이 by=mark 로 통과한다 —
    그 결함이 이 감사가 잡으려는 종류라 넓히지 않는다 (quick-260905-ota Task 4 판단)."""
    assert "neck" not in _SHOULDER and "head" not in _SHOULDER
    widened = _SHOULDER | {"neck"}
    assert cpa.adjudicate(widened, "head", "neck", marked=True)["ok"] is True   # 통과해 버림
    assert cpa.adjudicate(_SHOULDER, "head", "neck", marked=True)["ok"] is False
    # hip 에 knee 를 넣으면 참고 왼골반 ref 가 by=center 로 통과해 버린다 — 그 패널은 표시가
    # 없어(게이트 B, 눈 no_mark 3/3 ×2런) 표시 측정이 넓힘을 지지할 길이 없다. 이번 1벌을
    # 깨끗하게 보이려는 조정이 정확히 이것이라 하지 않는다.
    assert cpa.adjudicate(_HIP | {"knee"}, "knee", None, marked=False)["ok"] is True
    assert cpa.adjudicate(_HIP, "knee", None, marked=False)["reason"] == "no_mark_and_center_elsewhere"
