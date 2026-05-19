"""Firebase Auth ID 토큰 검증 → uid.

contract.md §2: /upload-url 인증은 Firebase Auth UID(익명 포함).
앱(firebase JS SDK)이 Authorization: Bearer <idToken> 헤더로 전달.

검증은 firebase-admin 으로 수행. 서비스 계정 키는 Parameter Store 에 두고
환경변수 FIREBASE_SA_PARAM 로 파라미터명을 주입(.env/코드 하드코딩 금지 —
backend_CLAUDE.md 보안 원칙). 미설정 환경에서는 명확한 401 을 던진다(조용한
통과 금지).
"""

from __future__ import annotations

import json
import os
import threading

_lock = threading.Lock()
_initialized = False


class AuthError(Exception):
    def __init__(self, message: str = "인증이 필요합니다."):
        super().__init__(message)
        self.message = message


def _bearer_token(event: dict) -> str:
    headers = event.get("headers") or {}
    # API GW 는 헤더 케이스를 보존하지 않을 수 있어 둘 다 확인
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    if not auth.startswith("Bearer "):
        raise AuthError()
    token = auth[len("Bearer ") :].strip()
    if not token:
        raise AuthError()
    return token


def _ensure_firebase():
    """firebase-admin 1회 초기화. 서비스 계정은 Parameter Store 에서 로드."""
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        try:
            import boto3  # Lambda 런타임 제공
            import firebase_admin
            from firebase_admin import credentials
        except ImportError as e:  # pragma: no cover - 배포 환경에선 존재
            raise AuthError("인증 모듈이 구성되지 않았습니다.") from e

        param_name = os.environ.get("FIREBASE_SA_PARAM")
        if not param_name:
            raise AuthError("FIREBASE_SA_PARAM 미설정 — 배포 시 Parameter Store 연결 필요.")

        ssm = boto3.client("ssm")
        sa_json = ssm.get_parameter(Name=param_name, WithDecryption=True)[
            "Parameter"
        ]["Value"]
        cred = credentials.Certificate(json.loads(sa_json))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        _initialized = True


def verify_request(event: dict) -> str:
    """요청에서 Firebase ID 토큰을 검증하고 uid 반환. 실패 시 AuthError."""
    token = _bearer_token(event)
    _ensure_firebase()
    from firebase_admin import auth as fb_auth

    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as e:  # firebase_admin.auth 의 다양한 예외
        raise AuthError("유효하지 않은 인증 토큰입니다.") from e
    uid = decoded.get("uid")
    if not uid:
        raise AuthError()
    return uid
