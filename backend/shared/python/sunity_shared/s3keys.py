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


def build_coach_audio_key(uid: str, analysis_id: str, record_id: str) -> str:
    """재생 중 큐 오디오 mp3 의 canonical S3 키 (Phase 32 Plan 32-16, D-18).

    **단일 출처** — pipeline(합성 저장)과 playback-url(서버 구성 canonical key +
    저장 key exact 비교, 리뷰 H-02)이 이 함수 하나를 공유해 drift 를 차단한다.
    record_id 는 contract.md §12.3 recordId('r{index:02d}:{criterion}') 를 그대로
    각인 — 32-12 audioCue prefetch 가 cueId(=recordId)로 mp3 와 안정 조인한다.
    """
    return f"{RESULT_PREFIX}/{uid}/{analysis_id}/coach_audio_{record_id}.mp3"


def build_discover_audio_key(uid: str, analysis_id: str, rid: str, joint: str) -> str:
    """발굴 채택 freeze 음성 mp3 의 canonical S3 키 (quick-260814-di7, D-di7-02).

    **단일 출처** — doc `result.discovery.items[].mp3Key` 는 반드시 이 함수
    산출값이어야 한다 (build_coach_audio_key 선례 — drift 차단).
    렌더 조인 규약 = **basename**: compare_render.build_timeline 주입 레이어가
    `audio_dir/<basename(mp3Key)>` 로 mp3 를 찾는다. 'discover_' 접두라 record
    큐 오디오 파일명(r{NN}.mp3)과 구조적으로 비충돌. 같은 rid+joint 복수 채택은
    validator 의 mp3Key 중복 거부로 fail-closed (키 규약 확장은 미래 의제).
    """
    return (
        f"{RESULT_PREFIX}/{uid}/{analysis_id}/discover_audio_{rid}_{joint}.mp3"
    )


# 합성 비교 영상 렌더 버전 — 표시 문법이 바뀌면 bump (키가 바뀌어 구 mp4 와
# 신 doc 가 절대 섞이지 않는다. 구 버전 객체는 앱이 참조하지 않게 됨).
RENDERED_COMPARE_RENDER_VERSION = 1


def build_rendered_compare_key(uid: str, analysis_id: str) -> str:
    """합성 비교 영상 mp4 의 canonical S3 키 (Phase 35, quick-260808-jix).

    **단일 출처** — pipeline(compare_render 스테이지 저장)과 playback-url(서버
    구성 canonical key + doc 저장 key exact 비교, H-02)이 이 함수 하나를 공유해
    drift 를 차단한다 (build_coach_audio_key 선례).
    """
    return (
        f"{RESULT_PREFIX}/{uid}/{analysis_id}/"
        f"compare_v{RENDERED_COMPARE_RENDER_VERSION}.mp4"
    )
