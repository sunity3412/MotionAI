"""공급자 메일 초대 — 순수 함수 (boto3·firebase 무관, quick-260930-lfw).

38-DESIGN-v2 §W1 "데이터" · "서버 — 확인(probe) 한 곳에서 수락".
260930-lfw-PLAN 플래너 결정:
  (b) 명단 판정 순서 — `suppliers/{uid}` doc 이 **있으면 그 active 가 결정**한다(SSM·BELLE_UID
      보다 우선). doc 이 없을 때만 SSM ∪ BELLE_UID. 합집합만으로는 deactivate 가 SSM 에 남은
      uid 를 못 막는다.
  (c) 새 코드 규칙(models.SUPPLIER_INVITE_CODE_RE)은 새 초대에만. SSM 옛 코드는 옛 규칙.
  (h) 회수·되살리기 — 이 모듈은 판정 재료만 준다. 트랜잭션은 firestore_admin 이 한다.

이 모듈의 함수는 입력만 보고 답한다 — 네트워크·시계 0(now_ms 는 호출측이 넘긴다).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import models

# 메일 = doc id. '/' 는 경로 구분자라 반드시 거부한다. 공백·'@' 두 개도 거부.
_EMAIL_RE = re.compile(r"^[^@\s/]+@[^@\s/]+\.[^@\s/]+$")
_EMAIL_MAX_LEN = 254


@dataclass(frozen=True)
class SupplierEntry:
    """명단 판정 결과 — 통과한 공급자의 강사 코드와 표시 이름(없으면 None)."""

    code: str | None
    display_name: str | None


class SupplierCodeConflict(Exception):
    """수락하려는 초대의 코드가 이미 다른 uid 의 supplierCodes doc 이다(쓰기 0, 핸들러 500)."""


def normalize_invite_email(email) -> str:
    """strip + lower. 메일 모양이 아니거나 doc id 로 못 쓰면 ValueError.

    Firestore doc id 규칙: '/' 금지, '.'·'..' 금지, `__.*__` 금지. 정규식이 앞의 둘을 막고
    '__' 로 시작하거나 끝나는 값은 따로 거부한다.
    """
    if not isinstance(email, str):
        raise ValueError("메일은 문자열이어야 해요.")
    value = email.strip().lower()
    if not value or len(value) > _EMAIL_MAX_LEN or not _EMAIL_RE.match(value):
        raise ValueError(f"메일 형식이 아니에요: {mask_email(value)}")
    if value.startswith("__") or value.endswith("__"):
        raise ValueError("메일을 문서 이름으로 쓸 수 없어요.")
    return value


def validate_invite_code(code) -> str:
    """공백 전부 제거 + 대문자 → SUPPLIER_INVITE_CODE_RE. 통과하면 정규화한 코드를 돌려준다."""
    if not isinstance(code, str):
        raise ValueError("코드는 문자열이어야 해요.")
    value = "".join(code.split()).upper()
    if not models.SUPPLIER_INVITE_CODE_RE.match(value):
        raise ValueError(
            "코드는 A-Z·2-9 로 4~8자예요. O·0·I·1·L 은 쓸 수 없어요."
        )
    return value


def invite_acceptable(invite, now_ms: int) -> bool:
    """pending 이고 만료 전(expiresAt > now, 경계 = 만료)이고 코드가 새 규칙이면 True.

    필드 누락·타입 이상은 False(던지지 않는다 — 수락 경로에서 이상한 doc 이 500 이 되지 않게).
    """
    if not isinstance(invite, dict):
        return False
    if invite.get("status") != models.INVITE_STATUS_PENDING:
        return False
    expires = invite.get("expiresAt")
    if isinstance(expires, bool) or not isinstance(expires, (int, float)):
        return False
    code = invite.get("code")
    if not isinstance(code, str) or not models.SUPPLIER_INVITE_CODE_RE.match(code):
        return False
    return expires > now_ms


def _str_or_none(value) -> str | None:
    return value if isinstance(value, str) and value else None


def roster_decision(doc, ssm_map: dict, belle_uid: str, uid: str) -> SupplierEntry | None:
    """명단 판정(결정 (b)) — doc 우선 → SSM ∪ BELLE_UID. 밖이면 None.

    doc 은 `suppliers/{uid}` 의 dict 또는 None. active 가 정확히 True 일 때만 통과한다.
    빈 uid·빈 belle_uid 는 통과 재료가 아니다(env 미설정 = 거부).
    """
    if not uid:
        return None
    if doc is not None:
        if isinstance(doc, dict) and doc.get("active") is True:
            return SupplierEntry(
                code=_str_or_none(doc.get("code")),
                display_name=_str_or_none(doc.get(models.SUPPLIER_FIELD_DISPLAY_NAME)),
            )
        return None
    if uid in ssm_map:
        return SupplierEntry(code=ssm_map.get(uid), display_name=None)
    if belle_uid and uid == belle_uid:
        return SupplierEntry(code=None, display_name=None)
    return None


def mask_email(email) -> str:
    """로그·기록용 — 첫 글자 + *** + @도메인. 메일 모양이 아니면 '***'."""
    if not isinstance(email, str):
        return "***"
    local, sep, domain = email.partition("@")
    if not sep or not local or not domain:
        return "***"
    return f"{local[0]}***@{domain}"
