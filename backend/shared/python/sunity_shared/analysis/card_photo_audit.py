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

알려진 정답 (09-05 실측 대장 — 테스트 fixture 의 근거):
  1. pdshape 6.1s 오른팔꿈치 카드 = 등허리(back_waist)        → 불일치
  2. 파워스핀 왼어깨 카드 = 허벅지(thigh)                      → 불일치
  3. 엘보 트위스트 오른팔꿈치 카드 기준 패널 = 겨드랑이(armpit)  → 불일치 (기준 측)
  4. 엘보 트위스트 왼어깨 카드 = 양쪽 허벅지(thigh)             → 불일치
  5. 엘보 트위스트 참고 카드 왼어깨(criterion 없음) = 머리(head) → 불일치
정상 예: pdshape 5.3s 왼팔꿈치 = 팔꿈치, 클라임 무릎 = 무릎/허벅지, 피터팬 벌림 = 엉덩이.

numpy / boto3 / 네트워크 의존 0 — card_gates 를 import 하지 않는다 (numpy 를 끌어온다).
토큰 어휘는 card_gates._CLAIM_ENUM["part"] 와 lockstep — 테스트가 두 집합의 일치를
강제한다 (tests/test_card_photo_audit.py). **파이프라인 무접촉** — 분석 시점 게이트로
승격하는 것은 별도 단위 (카드마다 눈 호출이 늘고, 불일치 시 처분이 별도 결정).
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

# 관절 종류 → 허용 부위. 관절 이름 꼬리(split("_")[-1]) 관례는 card_gates.joint_limb 과
# 동일 — 좌/우는 여기서도 쓰지 않는다. 카드가 대표로 삼는 관절은 4종뿐
# (pipeline._KISMAM_TO_KEYPOINT: elbow/shoulder/hip/knee 좌우). 미등록 종류 = 허용
# 집합 없음(빈 집합 → 감사 불가, 불일치로 세지 않는다).
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


__all__ = [
    "ANGLE_CRIT_PREFIX",
    "MISMATCH_FLAGS",
    "PART_VOCAB",
    "UNREAD",
    "audit_card",
    "expected_parts",
    "is_mismatch",
    "joint_kind",
]
