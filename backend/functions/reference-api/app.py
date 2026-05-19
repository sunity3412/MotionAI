"""GET /reference — 기준 모션(정은지) 목록.

contract.md §2: 앱 기준 모션 선택 화면(#9)이 호출. 응답 ReferenceMotion[].
firestore.rules 상 reference/** 는 인증 읽기 전용 — 여기선 Admin SDK 로 읽되
엔드포인트 자체도 Firebase 인증을 요구(upload-url 과 동일 정책).
"""

from __future__ import annotations

import logging

from sunity_shared import firestore_admin, responses
from sunity_shared.auth import AuthError, verify_request

log = logging.getLogger()
log.setLevel(logging.INFO)


def lambda_handler(event: dict, _context) -> dict:
    try:
        verify_request(event)  # 인증만 확인 (uid 자체는 불필요 — 공용 데이터)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)

    try:
        motions = firestore_admin.list_reference_motions()
    except Exception:  # noqa: BLE001
        log.exception("기준 모션 조회 실패")
        return responses.error(
            "server_error", "기준 모션을 불러오지 못했어요.", status=500
        )

    return responses.ok(motions)
