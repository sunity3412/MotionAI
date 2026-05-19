"""S3 객체 키 규칙. upload-url 이 발급하고 pipeline 이 역파싱한다.

원본 영상은 uploads/ 프리픽스 → 수명주기 정책으로 30일 후 자동 삭제
(backend_CLAUDE.md 비용 관리). 분석 결과/기준 모션은 별도 프리픽스.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

UPLOAD_PREFIX = "uploads"
RESULT_PREFIX = "results"
REFERENCE_PREFIX = "reference"

# uploads/{uid}/{analysisId}.{ext}
_UPLOAD_KEY_RE = re.compile(
    r"^uploads/(?P<uid>[^/]+)/(?P<analysis_id>[A-Za-z0-9]+)\.(?P<ext>mp4|mov)$"
)


def build_upload_key(uid: str, analysis_id: str, ext: str) -> str:
    """앱이 영상을 PUT 할 S3 키. uid·analysisId 가 키에 박혀 트리거가 역추적."""
    return f"{UPLOAD_PREFIX}/{uid}/{analysis_id}.{ext}"


@dataclass(frozen=True)
class ParsedUploadKey:
    uid: str
    analysis_id: str
    ext: str


def parse_upload_key(key: str) -> ParsedUploadKey | None:
    """S3 트리거가 받은 키에서 uid/analysisId 복원. 형식 불일치면 None."""
    m = _UPLOAD_KEY_RE.match(key)
    if not m:
        return None
    return ParsedUploadKey(
        uid=m.group("uid"),
        analysis_id=m.group("analysis_id"),
        ext=m.group("ext"),
    )
