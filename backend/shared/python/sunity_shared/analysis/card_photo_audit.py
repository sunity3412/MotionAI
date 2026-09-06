"""확대 카드 사진 감사 — 사진이 제목의 부위를 보여주는가 (quick-260905-mvm). 순수 모듈.

2026-09-05 belle 이 확대 사진 대장에서 "6.1초 오른팔꿈치 카드가 5.3초 왼팔꿈치 카드와
같은 팔로 보인다"를 먼저 찾아냈다. 확인 결과 09-03 라이브 21장 중 **5장이 제목과 다른
부위**를 보여주고 있었다 (아래 알려진 정답 5건). 09-03 "6동작 6/6 PASS" 는
`expected_units == emitted`, 사진 **장수**만 셌고 사진이 제목의 부위를 보여주는지는
한 번도 세지 않았다 — 이 모듈이 그 검사의 순수 대조 층이다.

좌표로 감사하지 않는다 (09-05 확인): crop 중심의 출처가 경로마다 다르다(게이트 통과 카드
= align 17-kp, 폴백 카드 = rep12 keypointReport) 그런데 doc 에는 rep12 만 실려 rep12
신뢰도로 판정하면 오판이 난다(실제 3장 오판). 사람이 보는 그림은 경로가 뭐든 하나뿐이므로
**완성된 카드 사진**에서 검사한다 — 관측은 card_gates.eye_judge(claim="part", 좌우·기대
관절 0 질문), 대조는 여기서.

  · expected_parts(criterion, joint) — 카드가 약속한 부위의 허용 집합. crop 은 관절
    주변을 담으므로 "정중앙"이 인접 부위로 읽히는 것은 정상이다 — 잡으려는 것은
    **팔꿈치 카드가 등허리를 보여주는** 종류다.
  · audit_card(expected, user_observed, ref_observed, *, user_marked, ref_marked)
    — 패널별 대조. 표시가 없는 측(marked=False)은 "표시 위치" 불일치를 묻지 않고
    "그 부위가 보이는가"만 본다 (플래그 이름이 갈린다).
  · adjudicate(expected, center_token, mark_token, *, marked) — 2단 판정
    (quick-260905-ota). mvm 감사에서 걸린 8장 중 3장이 인접 경계(목↔어깨, 무릎↔엉덩이,
    겨드랑이↔팔꿈치)였다. 허용 집합을 넓히면 잡으려던 종류까지 놓치므로 경계는
    측정으로 가른다: 1단(정중앙, part)이 허용 밖이면 **표시가 있는 패널에만** 2단
    (표시가 놓인 부위, mark_part)을 묻고, 표시가 허용 안이면 통과(by=mark — 정중앙은
    인접 맥락이었을 뿐), 밖이면 확정 불일치(mark_elsewhere — 사진이 다른 부위를
    가리킨다). 표시가 없는 패널은 2단 없이 확정(no_mark_and_center_elsewhere).
    눈이 no_mark 라는데 doc 은 표시 있음이면 판정 불가(mark_disagreement) — doc 과
    그림이 어긋난 것 자체가 보고 대상. needs_mark_query 가 2단 필요 여부를,
    card_verdict 가 카드 단위 결말(ok/mismatch/unresolved/unaudited)을 정한다.

알려진 정답 (09-05 실측 대장 — 테스트 fixture 의 근거):
  1. pdshape 6.1s 오른팔꿈치 카드 = 등허리(back_waist)        → 불일치
  2. 파워스핀 왼어깨 카드 = 허벅지(thigh)                      → 불일치
  3. 엘보 트위스트 오른팔꿈치 카드 기준 패널 = 겨드랑이(armpit)  → 불일치 (기준 측)
  4. 엘보 트위스트 왼어깨 카드 = 양쪽 허벅지(thigh)             → 불일치
  5. 엘보 트위스트 참고 카드 왼어깨(criterion 없음) = 머리(head) → 불일치
정상 예: pdshape 5.3s 왼팔꿈치 = 팔꿈치, 클라임 무릎 = 무릎/허벅지, 피터팬 벌림 = 엉덩이.

numpy / boto3 / 네트워크 의존 0 — card_gates 를 import 하지 않는다 (numpy 를 끌어온다).
토큰 어휘는 card_gates._CLAIM_ENUM["part"] 와 lockstep — 테스트가 두 집합의 일치를
강제한다 (tests/test_card_photo_audit.py). 위의 감사 함수들(audit_card/adjudicate/
card_verdict)은 **파이프라인 무접촉** — 완성 사진 감사 스크립트 전용.

앵커 확인 (quick-260906-j8g):
  2026-09-06 실측(09-03 라이브 6문서 36패널, 관절 좌표에 짧은 변 18% 무마킹 크롭 → 기계
  눈 3회 최빈): 좌표 OK 15 / 좌표 틀림 14 / 못 읽음 7. 신뢰도(conf 0.872 판독불가, 0.749
  무릎 자리에 손)도 붕괴 검사(f4j 붕괴 14→4 인데 감점 카드 눈 불일치 4→4)도 이것을
  예측하지 못한다 — 카드 크롭(짧은 변 42%)은 몸 절반이 들어와 틀린 좌표를 가린다.
  그래서 카드를 내보내기 전에 앵커 좌표를 눈으로 본다. 이 모듈은 판정(modal_token /
  anchor_verdict)만, card_gates 가 눈·프레임, pipeline 이 처분(이동·표시 생략).
"""

from __future__ import annotations

# ── 토큰 어휘 (card_gates._CLAIM_ENUM["part"] 에서 unclear 를 뺀 것과 lockstep) ──
PART_VOCAB: frozenset[str] = frozenset({
    "head", "neck", "shoulder", "armpit", "elbow", "hand", "chest",
    "abdomen", "back_waist", "hip", "thigh", "knee", "foot",
})

# 눈이 "못 읽음"으로 돌려주는 값 — 불일치가 아니라 판정 불가 (눈이 못 본 것은 틀린 게
# 아니다: card_gates.eye_mismatch 와 같은 의미론). "error" 는 eye_judge 호출 실패.
UNREAD: frozenset[str] = frozenset({"unclear", "error"})

# 2단(mark_part) 어휘 = 13 부위 + no_mark (card_gates.MARK_PART_TOKENS 와 lockstep).
# no_mark 는 "표시가 없다"는 관측이지 못 읽음이 아니다 — quick-260905-ota.
NO_MARK = "no_mark"
MARK_VOCAB: frozenset[str] = PART_VOCAB | {NO_MARK}

# 관절 종류 → 허용 부위. 관절 이름 꼬리(split("_")[-1]) 관례는 card_gates.joint_limb 과
# 동일 — 좌/우는 여기서도 쓰지 않는다. 카드가 대표로 삼는 관절은 4종뿐
# (pipeline._KISMAM_TO_KEYPOINT: elbow/shoulder/hip/knee 좌우). 미등록 종류 = 허용
# 집합 없음(빈 집합 → 감사 불가, 불일치로 세지 않는다).
#
# 2026-09-05 (quick-260905-ota) — mvm 의 인접 경계 3종을 **표시 측정**(mark_part, 09-03
# 라이브 21장 × 2런, 3회 최빈)으로 가른 결과 **집합 무변경**. 넓힐 근거가 측정에 없다:
#   · 목↔어깨 (pdshape 오른어깨 ref, 정중앙 neck 2:1 ×2런): 그 패널은 refMarked=False —
#     잴 표시가 없다. 표시가 neck/head 로 읽힌 패널은 참고 왼어깨 2장(pdshape·엘보, 원이
#     얼굴 위 — 표시 neck 2:1→3:0 / head 2:1 ×2런)뿐이고 그것은 표시 전위 그 자체다.
#     shoulder 에 neck 을 넣으면 그 카드가 by=mark 로 통과한다 (테스트가 이를 고정).
#   · 무릎↔엉덩이 (클라임 참고 왼골반 ref, 정중앙 knee 3/3 ×2런): 참고 카드 기준 측은
#     게이트 B 로 무마킹이 정책 — 눈도 no_mark 3/3 ×2런. 지지할 표시가 없다.
#   · 겨드랑이↔팔꿈치 (엘보 오른팔꿈치 ref): 눈은 elbow 3/3 ×2런(mvm 포함 16/16) — 1단
#     통과. 대장의 armpit 은 사람 판독이었고 집합은 이미 맞다.
#   2단이 살린 카드 2장은 표시가 이미 집합 안(pdshape 왼무릎 ref elbow→mark knee, 엘보
#   오른어깨 ref elbow→mark shoulder). 표시 측정 패널 8 중 집합 밖 표시는 전부 원거리
#   (knee·thigh·hip·head/neck 이 어깨 카드에) — 인접 확장으로 구제될 사례 0.
#   증거: .planning/quick/260905-ota-mark-part-adjudication/evidence/ (run1·run2 + replay).
_KIND_PARTS: dict[str, frozenset[str]] = {
    "elbow": frozenset({"elbow", "hand", "shoulder"}),
    "shoulder": frozenset({"shoulder", "armpit", "chest", "back_waist"}),
    "hip": frozenset({"hip", "thigh", "back_waist", "abdomen"}),
    "knee": frozenset({"knee", "thigh", "foot"}),
}

# 관절이 아닌 criterion → 허용 부위 (벌림·뻗음 계열은 카드 대표 관절이 아니라
# 사지 전체를 담는다).
_CRIT_PARTS: dict[str, frozenset[str]] = {
    "split_angle": frozenset({"hip", "thigh"}),
    "leg_extension": frozenset({"thigh", "hip", "knee"}),
    "arm_extension": frozenset({"elbow", "hand", "shoulder"}),
}

ANGLE_CRIT_PREFIX = "angle_vs_reference__"


def joint_kind(joint: str | None) -> str | None:
    """관절 이름 → 종류 꼬리 ('left_elbow' → 'elbow'). 빈 값은 None."""
    if not joint:
        return None
    return str(joint).split("_")[-1]


def expected_parts(criterion: str | None, joint: str | None) -> frozenset[str]:
    """카드(제목)가 약속한 부위의 허용 집합. 파생 불가 = 빈 집합(감사 불가, 불일치 아님).

    우선순위: criterion 이 있으면 criterion 에서 (벌림/뻗음 계열은 _CRIT_PARTS,
    `angle_vs_reference__{jk}` 는 jk 의 관절 종류에서), 그 밖의 criterion 이나
    criterion 없는 참고 카드는 joint 의 관절 종류에서 같은 파생.
    """
    crit = str(criterion or "")
    if crit in _CRIT_PARTS:
        return _CRIT_PARTS[crit]
    if crit.startswith(ANGLE_CRIT_PREFIX):
        parts = _KIND_PARTS.get(joint_kind(crit[len(ANGLE_CRIT_PREFIX):]) or "")
        if parts:
            return parts
    parts = _KIND_PARTS.get(joint_kind(joint) or "")
    return parts if parts else frozenset()


def _audit_side(name: str, observed: str | None, marked: bool,
                expected: frozenset[str], flags: list[str]) -> bool | None:
    """한 패널 대조. ok True/False, 판정 불가 None (flags 에 사유 추가)."""
    if observed is None:
        flags.append(f"{name}:unobserved")
        return None
    obs = str(observed)
    if obs in UNREAD or obs not in PART_VOCAB:
        flags.append(f"{name}:unreadable")
        return None
    if obs in expected:
        return True
    # 표시가 있는 패널: 마크 위치가 제목 부위에 없다(mark_mismatch). 표시가 없는 패널:
    # 표시 위치를 물을 수 없으니 "그 부위가 보이는가"만 — 안 보인다(part_not_shown).
    flags.append(f"{name}:mark_mismatch" if marked else f"{name}:part_not_shown")
    return False


def audit_card(expected: frozenset[str] | set[str],
               user_observed: str | None, ref_observed: str | None, *,
               user_marked: bool, ref_marked: bool) -> dict:
    """카드 한 장 대조 → {userOk, refOk, flags}.

    · userOk / refOk: 관측 부위 ∈ expected 이면 True, 아니면 False, 판정 불가
      (관측 없음·unclear·error·어휘 밖) 는 None.
    · flags: `user:mark_mismatch` / `user:part_not_shown` / `user:unreadable` /
      `user:unobserved` (ref 도 같은 형상), expected 가 비면 `no_expectation` 하나.
    불일치 = flags 에 mark_mismatch 또는 part_not_shown 이 있는 것 (is_mismatch).
    """
    exp = frozenset(expected or ())
    if not exp:
        return {"userOk": None, "refOk": None, "flags": ["no_expectation"]}
    flags: list[str] = []
    user_ok = _audit_side("user", user_observed, bool(user_marked), exp, flags)
    ref_ok = _audit_side("ref", ref_observed, bool(ref_marked), exp, flags)
    return {"userOk": user_ok, "refOk": ref_ok, "flags": flags}


MISMATCH_FLAGS = ("mark_mismatch", "part_not_shown")


def is_mismatch(audit: dict) -> bool:
    """audit_card 결과가 **실제 불일치**인가 — 판정 불가(unreadable 등)는 불일치 아님."""
    return any(f.split(":", 1)[-1] in MISMATCH_FLAGS for f in audit.get("flags", ()))


# ── 2단 판정 — 표시가 놓인 부위로 경계를 가른다 (quick-260905-ota) ─────────────
#
# 결말 4종 (+ 판정 불가):
#   ok True  by center  center_in_expected            1단 통과 — 2단 불필요
#   ok True  by mark    mark_in_expected              정중앙은 인접 맥락, 표시는 제목 부위
#   ok False by mark    mark_elsewhere                표시가 다른 부위에 — 확정 불일치
#   ok False by none    no_mark_and_center_elsewhere  표시 없고 정중앙도 아님 — 확정
#   ok None  by mark    mark_disagreement             doc 표시 유무 ≠ 눈 (그 자체가 보고 대상)
#   ok None  by center|mark  unreadable               눈이 못 읽음 (unclear/error/어휘 밖)
#   ok None  by mark    mark_unobserved               2단이 필요한데 아직 안 물었음
#   ok None  by none    no_expectation                허용 집합 없음 — 감사 불가

ADJ_BY = ("center", "mark", "none")


def _readable(token: str | None) -> bool:
    return token is not None and str(token) not in UNREAD and str(token) in PART_VOCAB


def modal_token(observed, vocab: frozenset[str] = PART_VOCAB) -> str:
    """토큰 다수결 — 읽어낸 토큰(vocab 안) 중 최빈값. 동률·전부 못 읽음 = 'unclear'.

    스크립트(scripts/audit_card_photos.py)에서 이관(quick-260906-j8g) — 파이프라인
    앵커 확인(card_gates.eye_part_token)과 감사 스크립트가 **같은 최빈 규칙**을 쓴다.
    vocab 은 claim 의 "읽어냈다" 집합 — part = PART_VOCAB, mark_part = MARK_VOCAB
    (no_mark 도 표다: 표시가 없다는 관측). 동률을 unclear 로 닫는 이유: 09-05 실측
    (같은 21장 2회, temperature 0)에서 42패널 중 4패널의 토큰이 바뀌었다 — 표가
    갈리면 확정하지 않는다 (fail-closed).
    """
    counts: dict[str, int] = {}
    for tok in observed:
        if tok in vocab:
            counts[tok] = counts.get(tok, 0) + 1
    if not counts:
        return "unclear"
    best = max(counts.values())
    winners = [t for t, n in counts.items() if n == best]
    return winners[0] if len(winners) == 1 else "unclear"


# 앵커 판정 결말 4종 — 서로 배타 (quick-260906-j8g)
ANCHOR_VERDICTS = ("ok", "mismatch", "unreadable", "no_expectation")


def anchor_verdict(observed: str | None, expected) -> str:
    """앵커 좌표의 좁은 크롭을 눈이 읽은 부위(observed) 가 제목의 허용 집합(expected) 안인가.

    · no_expectation — 허용 집합 없음(expected_parts 가 빈 집합): 감사 불가.
    · unreadable    — 눈이 못 읽음(unclear/error/어휘 밖). **불일치가 아니다** — 눈이
                      못 본 것은 틀린 게 아니다 (card_gates.eye_mismatch 의미론과 동형:
                      frame_missing/no_api_key 가 표시를 지우지 않는 것과 같은 이유).
                      좁은 크롭(짧은 변 18%)은 축소본 폴백에서 60px 대라 못 읽음이
                      잦을 수 있고, 그것으로 표시를 지우면 카드가 운으로 사라진다.
    · ok / mismatch — 읽어낸 부위가 허용 안/밖.

    판정만 하고 처분(이동/생략)은 하지 않는다 — 처분은 비용(눈 호출 상한)과 프레임
    후보를 아는 호출측(card_gates.verify_anchor_side → pipeline)의 결정이고, 이 함수는
    순수(numpy/네트워크 0)라 스크립트·테스트가 같은 규칙을 재사용한다.
    """
    exp = frozenset(expected or ())
    if not exp:
        return "no_expectation"
    if not _readable(observed):
        return "unreadable"
    return "ok" if str(observed) in exp else "mismatch"


def needs_mark_query(expected: frozenset[str] | set[str], center_token: str | None, *,
                     marked: bool) -> bool:
    """이 패널에 2단(mark_part) 질의가 필요한가 — 허용 집합 있음 + 표시 있음 + 1단이 통과가
    아님(정중앙이 허용 밖이거나 못 읽음). 표시 없는 패널은 2단 없이 확정되므로 False.

    못 읽음(unclear 동률 등)도 2단으로 보낸다 — 못 읽음은 통과가 아니고, 표시 질문이
    정중앙 질문보다 카드가 가리키는 지점에 정확하다 (plan 의 2단 근거 그대로).
    """
    exp = frozenset(expected or ())
    if not exp or not marked:
        return False
    return not (_readable(center_token) and str(center_token) in exp)


def adjudicate(expected: frozenset[str] | set[str], center_token: str | None,
               mark_token: str | None = None, *, marked: bool) -> dict:
    """패널 한 장의 2단 판정 → {ok, by, reason} (순수).

    center_token = 1단(part) 최빈 토큰, mark_token = 2단(mark_part) 최빈 토큰 —
    2단을 안 물었으면 None. marked = doc 의 userMarked/refMarked (09-05 감사에서 21장
    전부 실제 그림과 일치 확인). 분기는 모듈 상단 표 그대로 — 결말은 서로 배타.
    """
    exp = frozenset(expected or ())
    if not exp:
        return {"ok": None, "by": "none", "reason": "no_expectation"}
    center = None if center_token is None else str(center_token)
    center_read = _readable(center)
    if center_read and center in exp:
        return {"ok": True, "by": "center", "reason": "center_in_expected"}
    mark = None if mark_token is None else str(mark_token)
    if not marked:
        if mark is not None and mark in PART_VOCAB:
            # doc 은 표시 없음인데 눈이 표시를 봤다 — 반대 방향 어긋남도 같은 보고 대상
            return {"ok": None, "by": "mark", "reason": "mark_disagreement"}
        if not center_read:
            return {"ok": None, "by": "center", "reason": "unreadable"}
        return {"ok": False, "by": "none", "reason": "no_mark_and_center_elsewhere"}
    if mark is None:
        return {"ok": None, "by": "mark", "reason": "mark_unobserved"}
    if mark == NO_MARK:
        return {"ok": None, "by": "mark", "reason": "mark_disagreement"}
    if mark in UNREAD or mark not in PART_VOCAB:
        return {"ok": None, "by": "mark", "reason": "unreadable"}
    if mark in exp:
        return {"ok": True, "by": "mark", "reason": "mark_in_expected"}
    return {"ok": False, "by": "mark", "reason": "mark_elsewhere"}


CARD_VERDICTS = ("ok", "mismatch", "unresolved", "unaudited")


def card_verdict(user_adj: dict, ref_adj: dict) -> str:
    """카드 단위 결말 — 어느 패널이든 ok False 면 mismatch, 아니면 어느 패널이든 판정 불가
    (no_expectation 제외) 면 unresolved, 둘 다 no_expectation 이면 unaudited, 그 외 ok."""
    adjs = (user_adj, ref_adj)
    if any(a.get("ok") is False for a in adjs):
        return "mismatch"
    if all(a.get("reason") == "no_expectation" for a in adjs):
        return "unaudited"
    if any(a.get("ok") is None for a in adjs):
        return "unresolved"
    return "ok"


__all__ = [
    "ADJ_BY",
    "ANCHOR_VERDICTS",
    "ANGLE_CRIT_PREFIX",
    "CARD_VERDICTS",
    "MARK_VOCAB",
    "MISMATCH_FLAGS",
    "NO_MARK",
    "PART_VOCAB",
    "UNREAD",
    "adjudicate",
    "anchor_verdict",
    "audit_card",
    "card_verdict",
    "expected_parts",
    "is_mismatch",
    "joint_kind",
    "modal_token",
    "needs_mark_query",
]
