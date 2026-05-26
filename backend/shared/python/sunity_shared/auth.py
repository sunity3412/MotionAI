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


def _load_service_account_dict() -> dict:
    """서비스 계정 JSON 로드. 우선순위:
      1. FIREBASE_SA_JSON   — JSON 원문 (RunPod/Pod 등 AWS SSM 접근 불가 환경)
      2. FIREBASE_SA_PATH   — 파일 경로 (RunPod 마운트 시드)
      3. FIREBASE_SA_PARAM  — AWS SSM Parameter Store (Lambda 기본)

    1·2 는 비-AWS 환경(#7-follow GPU Pod) 지원 목적. Lambda 는 3 그대로.
    """
    sa_json_inline = os.environ.get("FIREBASE_SA_JSON")
    if sa_json_inline:
        return json.loads(sa_json_inline)

    sa_path = os.environ.get("FIREBASE_SA_PATH")
    if sa_path:
        with open(sa_path, encoding="utf-8") as f:
            return json.load(f)

    param_name = os.environ.get("FIREBASE_SA_PARAM")
    if not param_name:
        raise AuthError(
            "FIREBASE_SA_JSON / FIREBASE_SA_PATH / FIREBASE_SA_PARAM 중 하나 필요."
        )
    import boto3  # Lambda 런타임 제공
    ssm = boto3.client("ssm")
    sa_json = ssm.get_parameter(Name=param_name, WithDecryption=True)[
        "Parameter"
    ]["Value"]
    return json.loads(sa_json)


def _ensure_firebase():
    """firebase-admin 1회 초기화. SA 키 소스는 _load_service_account_dict 참조."""
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError as e:  # pragma: no cover - 배포 환경에선 존재
            raise AuthError("인증 모듈이 구성되지 않았습니다.") from e

        sa_dict = _load_service_account_dict()
        cred = credentials.Certificate(sa_dict)
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
