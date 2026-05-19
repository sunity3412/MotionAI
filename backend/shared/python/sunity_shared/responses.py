"""API Gateway (proxy 통합) 응답 포맷 헬퍼."""

from __future__ import annotations

import json
from typing import Any

# 앱은 Expo(웹/네이티브) — CORS 허용. 파일럿 단계라 *.
_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _resp(status: int, payload: Any) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps(payload, ensure_ascii=False),
    }


def ok(payload: Any, status: int = 200) -> dict:
    return _resp(status, payload)


def error(code: str, message: str, status: int = 400) -> dict:
    """contract 형태와 동일: { error: { code, message } }."""
    return _resp(status, {"error": {"code": code, "message": message}})


def parse_json_body(event: dict) -> dict:
    """API GW proxy event 의 body(JSON) 파싱. 실패 시 {}."""
    raw = event.get("body")
    if raw is None:
        return {}
    if isinstance(raw, (dict, list)):
        return raw  # 로컬 직접 호출 시
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}
