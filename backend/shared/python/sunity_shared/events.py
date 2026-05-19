"""SQS→S3 트리거 이벤트에서 객체 키를 뽑는 순수 파서 (AWS 무관, 테스트 가능).

S3 가 SQS 로 보내면 event['Records'][i]['body'] 안에 S3 이벤트 JSON 이 문자열로
중첩된다. 키는 URL 인코딩(공백→'+')될 수 있어 unquote_plus 필요.
"""

from __future__ import annotations

import json
from urllib.parse import unquote_plus


def iter_s3_keys_from_sqs(event: dict):
    """SQS 이벤트에서 (bucket, key) 들을 순서대로 yield. 깨진 레코드는 건너뜀."""
    for record in event.get("Records", []) or []:
        body = record.get("body")
        if not body:
            continue
        try:
            s3_event = json.loads(body)
        except (ValueError, TypeError):
            continue
        for s3rec in s3_event.get("Records", []) or []:
            s3 = s3rec.get("s3") or {}
            bucket = (s3.get("bucket") or {}).get("name")
            raw_key = (s3.get("object") or {}).get("key")
            if not bucket or not raw_key:
                continue
            yield bucket, unquote_plus(raw_key)
