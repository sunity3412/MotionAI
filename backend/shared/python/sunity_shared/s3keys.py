"""S3 객체 키 규칙. upload-url 이 발급하고 pipeline 이 역파싱한다.

원본 영상은 uploads/ 프리픽스에 **영구 보관**(2026-09-26 belle 결정, Phase 38 D-17 —
버킷 수명주기 규칙 해제). 분석 결과/기준 모션은 별도 프리픽스.
기준 모션 키는 세 모양: 기존 11개 평면 `reference/{motionId}.mp4`(손 등록, 무접촉) ·
공급자 링크 업로드 `reference/{uid}/{refId}/upload.{ext}`(presign 전용, 덮어쓰기 가능) ·
공급자 링크 확정 `reference/{uid}/{refId}/v1.{ext}`(서버 복사, 불변 — Phase 38 R5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

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


# ---------------------------------------------------------------------------
# 공급자 링크 기준 모션 키 (Phase 38 D-04 + 리뷰 R5)
#
# 두 모양의 문자열은 여기 한 곳에서만 정한다.
#   upload.{ext} — presigned PUT 목적지. presigned URL 은 만료(900초) 전까지 같은
#                  키를 몇 번이든 덮어쓸 수 있으므로(R5) **presign 은 이 키에만**.
#   v1.{ext}     — 등록 파이프라인이 처리한 바이트를 서버 `copy_object` 로 옮긴
#                  불변 확정 키. 소비(mode1 `videoS3Key` · 재생 · 자기 재현성)는
#                  **이 키만**(38-07).
REFERENCE_KEY_KIND_UPLOAD = "upload"
REFERENCE_KEY_KIND_FINAL = "v1"

# reference/{uid}/{refId}/{upload|v1}.{ext}
#
# uid·refId 세그먼트를 영숫자로 제한하는 이유(D-19): 기존 평면 `reference/ref-*.mp4`
# 11개(하이픈)와 `reference/_archive/...`(밑줄)이 매치되지 않아 기존 객체·손 업로드가
# 새 등록 경로에 절대 들어오지 않는다. `..` 같은 경로 조작도 같은 이유로 불가.
# kind 를 upload/v1 두 값으로 닫는 이유(R5): `v2.mp4`·`original.mp4` 같은 임의
# 파일명이 파이프라인을 깨우지 못한다. 옛 모양 `reference/{uid}/{refId}.{ext}` 도
# 세그먼트 수가 달라 None — 리뷰 이전 설계의 키가 남아 있어도 무시된다.
_REFERENCE_KEY_RE = re.compile(
    r"^reference/(?P<uid>[A-Za-z0-9]+)/(?P<ref_id>[A-Za-z0-9]+)/"
    r"(?P<kind>upload|v1)\.(?P<ext>mp4|mov)$"
)


def build_reference_upload_key(uid: str, ref_id: str, ext: str) -> str:
    """공급자 링크 기준 영상의 **업로드** 키 `reference/{uid}/{refId}/upload.{ext}`
    (Phase 38 D-04 + 리뷰 R5).

    **단일 출처** — 발급(`reference-upload-url` Lambda, upload 키만 presign) ·
    역파싱(`pipeline.lambda_handler` · `runpod_inference/server.py /register-reference`,
    upload 키만 디스패치) · 확정(`pipeline._register_reference` 의 copy_object
    목적지 = `build_reference_final_key`) · 재개(`requeue_reference_registrations.py`,
    doc `uploadKey`)가 이 두 함수를 공유해 drift 를 차단한다(build_coach_audio_key
    선례). 이 키는 덮어쓰기 가능하므로 `videoS3Key` 에 적지 않는다.
    """
    return f"{REFERENCE_PREFIX}/{uid}/{ref_id}/{REFERENCE_KEY_KIND_UPLOAD}.{ext}"


def build_reference_final_key(uid: str, ref_id: str, ext: str) -> str:
    """공급자 링크 기준 영상의 **확정** 키 `reference/{uid}/{refId}/v1.{ext}`
    (Phase 38 D-04 + 리뷰 R5).

    **단일 출처** — `pipeline._register_reference` 가 처리한 바이트를 서버
    `copy_object` 로 이 키에 복사하고 `videoS3Key`·`videoETag` 에는 이 키/그 ETag 만
    적는다(38-07). presign 은 이 키에 절대 발급하지 않는다 — 등록 뒤 기준 영상이
    바뀌지 않는다는 보장이 이 분리 하나에 걸려 있다.
    """
    return f"{REFERENCE_PREFIX}/{uid}/{ref_id}/{REFERENCE_KEY_KIND_FINAL}.{ext}"


@dataclass(frozen=True)
class ParsedReferenceKey:
    uid: str
    ref_id: str
    kind: str
    ext: str

    @property
    def is_upload(self) -> bool:
        """upload 키면 True — 호출측이 v1 이벤트를 걸러 로그만 남기는 분기 재료."""
        return self.kind == REFERENCE_KEY_KIND_UPLOAD


def parse_reference_key(key: str) -> ParsedReferenceKey | None:
    """S3 이벤트 키에서 uid/refId/kind 복원. 형식 불일치면 None(예외 금지).

    upload·v1 두 모양 다 파싱한다 — 서버 copy_object 가 만드는 v1 객체도 같은
    ObjectCreated 이벤트로 큐에 오므로, 호출측이 `is_upload` 로 걸러 v1 은 로그만
    남기고 끝낸다. 평면 legacy · `_archive` · 옛 모양 · uploads/ · results/ 는 None.
    """
    m = _REFERENCE_KEY_RE.match(key)
    if not m:
        return None
    return ParsedReferenceKey(
        uid=m.group("uid"),
        ref_id=m.group("ref_id"),
        kind=m.group("kind"),
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


def build_fault_zoom_key(
    uid: str, analysis_id: str, tier: str | None, key_base: str, *, plain: bool = False
) -> str:
    """확대 비교(fault-zoom) PNG 의 canonical S3 키 (quick-260824-q6p).

    **단일 출처** — pipeline(`_fault_zoom_upload_items` 저장)과 playback-url
    (`_handle_fault_zoom` 재서명 — 서버 구성 canonical key + 저장/파싱 key
    **exact 비교**, H-02/M2-01)이 이 함수 하나를 공유해 drift 를 차단한다
    (build_coach_audio_key 선례).

    prefix 규칙 (기존 pipeline 인라인 규칙과 byte-동일):
      tier == 'advisory'          → 'zoom_adv_' (확정 카드와 S3 키 충돌 원천 차단)
      그 외(confirmed/None/legacy) → 'zoom_'
    key_base = criterion(있으면 — 33-12 A-5 record 별 카드 유일성) or joint.

    plain=True 는 belle 09-09 '관절선 끄기' 용 **표시 없는 판**의 키다. 같은 crop 을
    마커/각도선 없이 한 번 더 합성해 나란히 올린다 — 접미사만 다르므로 기존 키는
    byte-불변이고(기본값 False), 재서명측도 같은 함수로 구성한다(단일 출처 유지).
    """
    prefix = "zoom_adv_" if tier == "advisory" else "zoom_"
    suffix = "__plain" if plain else ""
    return f"{RESULT_PREFIX}/{uid}/{analysis_id}/{prefix}{key_base}{suffix}.png"


def parse_result_key_from_presigned_url(url: str) -> str | None:
    """presigned GET URL 에서 S3 key **후보**를 추출한다 (quick-260824-q6p 소급).

    기존 doc 의 faultZoomComparisons[] 는 imageKey 없이 7일 presigned imageUrl 만
    저장돼 있다 — 백필 없이 재서명하려면 서버가 저장 URL 에서 key 를 파싱해야
    한다. virtual-hosted(`{bucket}.s3.{region}.amazonaws.com/{key}`)와
    path-style(netloc 이 `s3.`/`s3-` 시작, path=`/{bucket}/{key}`) 둘 다 처리.

    파서는 관대해도 안전하다 — 출력은 신뢰되지 않으며, caller 가 서버 구성
    canonical key 와 **전체 문자열 exact 비교**를 통과한 것만 서명한다
    (M2-01 / T-q6p-03 — 파서는 후보 추출 전용, 서명 게이트가 아니다).
    비-str·빈 path·파싱 실패는 None.
    """
    if not isinstance(url, str) or not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    path = unquote(parsed.path or "")
    if not path.startswith("/"):
        return None
    path = path[1:]
    if not path:
        return None
    netloc = (parsed.netloc or "").lower()
    if netloc.startswith("s3.") or netloc.startswith("s3-"):
        # path-style — 첫 세그먼트는 bucket, 나머지가 key.
        _, _, key = path.partition("/")
        return key or None
    # virtual-hosted — path 전체가 key.
    return path


# 합성 비교 영상 렌더 버전 — 표시 문법이 바뀌면 bump (키가 바뀌어 구 mp4 와
# 신 doc 가 절대 섞이지 않는다. 구 버전 객체는 앱이 참조하지 않게 됨).
RENDERED_COMPARE_RENDER_VERSION = 1


def build_rendered_compare_key(uid: str, analysis_id: str, *, plain: bool = False) -> str:
    """합성 비교 영상 mp4 의 canonical S3 키 (Phase 35, quick-260808-jix).

    **단일 출처** — pipeline(compare_render 스테이지 저장)과 playback-url(서버
    구성 canonical key + doc 저장 key exact 비교, H-02)이 이 함수 하나를 공유해
    drift 를 차단한다 (build_coach_audio_key 선례).

    plain=True 는 belle 09-09 '관절선 끄기' 의 영상판이다 — 정지 프레임의 표시
    (관절 원·각도선·호·수치·폴 축선·몸 중심선)를 그리지 않은 두 번째 mp4.
    확대 사진의 `__plain` 규약(build_fault_zoom_key)과 **같은 접미사·같은 함수**를
    쓴다: 접미사만 다르므로 기존 키는 byte-불변이고(기본값 False), 재서명측도
    같은 함수로 구성해 단일 출처가 유지된다.
    """
    suffix = "__plain" if plain else ""
    return (
        f"{RESULT_PREFIX}/{uid}/{analysis_id}/"
        f"compare_v{RENDERED_COMPARE_RENDER_VERSION}{suffix}.mp4"
    )
