# Phase 38: 공급자 링크 — 실증 최소 (supplier-link) - Pattern Map

**Mapped:** 2026-09-26
**Files analyzed:** 37 (backend 22 · app 10 · docs 5)
**Analogs found:** 34 / 37 (exact 19 · role-match 15 · 부분/없음 3)

> 보고 규칙(CLAUDE.md §7 ★): 이 문서의 `file:line` 은 **전부 이 세션에서 파일을 열어 읽은 것** [확인].
> 코드 발췌는 원문 그대로다(요약·의역 없음). 관측(코드 사실)과 진단(설계 제안)은 절을 나눴다 —
> `## Pattern Assignments` 는 관측, 각 항목의 "플래너 메모" 와 `## 관측 — 플래너가 알아야 할 코드 사실` 의
> 표시된 문장만 진단이다. 호스팅 후보(Expo web export vs 단일 HTML)는 RESEARCH §H 대로 **미결** —
> 두 후보의 analog 를 모두 적었다.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/functions/reference-upload-url/app.py` (신규) | controller (Lambda HTTP) | request-response | `backend/functions/upload-url/app.py` :1-72 + `backend/functions/reference-auto-register/app.py` :87-99 | exact |
| `backend/shared/python/sunity_shared/s3keys.py` (수정) | utility | transform (키 build/parse) | 자기 자신 :17-44 (`_UPLOAD_KEY_RE` · `ParsedUploadKey` · `parse_upload_key`) | exact |
| `backend/shared/python/sunity_shared/validation.py` (수정) | utility (validator) | transform | 자기 자신 :13-98 (`ValidationError` · `UploadRequest` · `validate_upload_request`) | exact |
| `backend/shared/python/sunity_shared/models.py` (수정) | config (contract 상수) | — | 자기 자신 :696-713 (status) · :746-768 (`COACH_STATUS_*` 별도 enum 선례) · :808-815 (`ERROR_MESSAGE`) · :829-836 (paths) | exact |
| `backend/shared/python/sunity_shared/firestore_admin.py` (수정) | model/repository (Admin writer) | CRUD | 자기 자신 `update_reference_body_data` :2173-2249 · `set_reference_motion_with_gemini` :2368-2443 · `fail_analysis` :2446-2455 · `update_analysis_status` :38-43 · `_validate_flat_dict_no_nested_array` :46-102 | exact |
| `backend/functions/pipeline/app.py` (수정: `lambda_handler` 분기 · `_handle_reference_upload` · `_register_reference` · selfScore 훅) | controller (SQS consumer) + service | event-driven + batch | 자기 자신 `lambda_handler` :10297-10348 · `_delegate_to_runpod` :210-236 · `_angles_from_video` :1575-1588 · `_download_analysis_video` :1666-1692 · `_ensure_adapters` :1514-1564 · complete_analysis 호출 :10109-10135 | exact |
| `backend/runpod_inference/server.py` (수정: `POST /register-reference`) | controller (FastAPI route) | request-response → background | 자기 자신 `/analyze` :433-456 · `_process_in_background` :184-215 · `AnalyzeRequest` :142-144 | exact |
| `backend/shared/python/sunity_shared/analysis/registration_checks.py` (신규) | service (pure) | transform | `analysis/hold_height.py` :63-80 (`_arrays`) · :96-134 (`_frame_series`) · :167-179 (바닥 위반 판정) + `rtmw_engine.py` :226-238 (NoHuman) · `keypoint_frame.py` :65-79 (`_KEYPOINT_NAMES` 12) · `skeleton.py` :53-62 (`JOINT_LABEL_KO`) | role-match |
| `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py` (수정: `estimate_with_person_counts`) | service (adapter) | transform | 자기 자신 `estimate` :195-252 · `_infer_raw` :254-285 · `_build_pose_frames` :287-320 | 부분 (N 을 버리는 코드는 있고 돌려주는 API 는 없다) |
| `backend/shared/python/sunity_shared/analysis/hold_height.py` (수정 선택: `floor_reference_valid` 공개) | service (pure) | transform | 자기 자신 :167-179 | exact |
| `backend/scripts/requeue_reference_registrations.py` (신규) | script | batch | `backend/scripts/e2e_app_path.py` :33-40 (`http_json`) · :56-61 (`firestore_client`) + `backend/infra/podwatch.yaml` :135-170 (`pod_expected_up` · `probe`) + `backend/scripts/pod_teardown.py` :124-127 (SSM 이름) | role-match (조합) |
| `backend/template.yaml` (수정: 함수·라우트·env·정책) | config (IaC) | — | 자기 자신 `UploadUrlFunction` :184-210 · `ReferenceAutoRegisterFunction` :261-299 · `PipelineFunction` :327-394 · Globals :101-112 | exact |
| `backend/README.md` (수정: 버킷 명령 정정) | docs | — | 자기 자신 :72-110 | exact |
| `backend/tests/test_reference_upload_url_handler.py` (신규) | test | — | `backend/tests/test_reference_auto_register_handler.py` :25-56 (fixture) · :94-115 (`_FakeS3`) · :121-175 (happy path monkeypatch) | exact |
| `backend/tests/test_pipeline_reference_dispatch.py` (신규) | test | — | `backend/tests/test_pipeline_dispatch.py` :17-65 (fixture) · :78-109 (위임) · :112-138 (실패 매핑) · :141-147 (스킵) | exact |
| `backend/tests/test_firestore_reference_writers.py` (신규) | test | — | `test_reference_auto_register_handler.py` :364-392 (`_FakeDoc` + `_doc` monkeypatch) · `backend/tests/test_analysis_provenance.py` :308-325 (`_FakeDocStore` path seam) | exact |
| `backend/tests/test_registration_checks.py` (신규) | test | — | `backend/tests/test_hold_height.py` :28-57 (`_report`/`_pose` 합성) · `backend/tests/test_rtmw_engine.py` :38-63 (mock inferencer · `create_with_inferencer`) | exact |
| `backend/tests/test_register_reference_pipeline.py` (신규) | test | — | `test_pipeline_dispatch.py` :33-65 (app 재로드 fixture) + `test_mode3_fault_zoom_selection.py` :105-110 (`app._s3`·`app._FRAME_EXTRACTOR` 교체) + `test_s3_download_accelerate.py` :51 | role-match |
| `backend/tests/test_self_score_hook.py` (신규) | test | — | `test_pipeline_dispatch.py` :33-65 + `_FakeDoc` (:364-392) | role-match |
| `backend/tests/test_runpod_server.py` (수정: `/register-reference`) | test | — | 자기 자신 :22-48 (fixture) · :63-86 (401/400) · :89-112 (202 + background 동기 실행) | exact |
| `backend/tests/test_s3keys.py` (수정) | test | — | 자기 자신 :6-29 | exact |
| `backend/tests/test_validation.py` (수정) | test | — | 자기 자신 :8-77 (`OK_MODE3` + parametrize 거부) | exact |
| `app/src/app/(tabs)/analyze.tsx` (수정: `validate()` duration) | component (screen) | request-response (pick → validate → route) | 자기 자신 :206-236 · :357-364 · :470-473 | exact |
| `app/src/lib/pickerFailure.ts` (수정: `tooShort`/`tooLong`) | utility (copy map) | transform | 자기 자신 :20-27 · :53-72 · :125-130 | exact |
| `app/src/app/analysis/loading.tsx` (수정: 문구 3자리) | component | — | 자기 자신 :490 · :519 · :546 | exact |
| `app/src/app/(tabs)/profile.tsx` (수정: 강사 코드 한 줄) | component | — | 자기 자신 :210-224 (`infoList` map) · :295-310 (`InfoRow`) · :399-416 (styles) | exact |
| `app/src/types/analysis.ts` (수정: `ReferenceMotion` 등록 필드 · 오류 코드) | config (contract 타입) | — | 자기 자신 :94-109 (unions) · :1302-1329 (`ReferenceMotion`) · :2220-2227 (`ERROR_MESSAGE`) | exact |
| `app/src/app/supplier/index.tsx` (신규, 후보 1) | component (screen) | CRUD (list + form upload + onSnapshot) | `app/src/app/analysis/reference.tsx` :27-181 (목록·카드·CTA) + `app/src/app/auth/login.tsx` :40-104 (busy/notice 상태) + `app/src/lib/api.ts` :51-95 · :327-343 (`authedJson`·`uploadToS3`) + `app/src/lib/referenceMotions.ts` :72-78 · :208-242 (normalize · onSnapshot) | role-match (조합) |
| `app/src/app/supplier/guide.tsx` (신규, 후보 1) | component (screen) | — | `app/src/app/help.tsx` :20-58 (`FAQ_ITEMS`) · :109-138 (`FaqCard` 접힘) · :140-196 (styles) | exact |
| `app/src/lib/firebase.web.ts` (신규, 후보 1·필요 시) | provider (init) | — | `app/src/lib/firebase.ts` :52-68 (`resolveAuth` try/catch + `getAuth` 폴백) | role-match |
| `app/src/lib/socialAuth.web.ts` (신규, 후보 1) | service (auth) | request-response | `app/src/lib/socialAuth.ts` :56-60 (`SocialAuthOutcome`) · :95-120 (`signInWithGoogle` 네이티브) | 부분 (웹 로그인 경로는 리포에 0건) |
| `web/supplier.html` (신규, 후보 2) | component (정적 SPA) | CRUD | `.planning/phases/33-result-trust-recovery/mockups/index.html` :7-9 (Pretendard CDN) · :113-116 (`:root` 토큰) · :161 (`.card`) + `app/src/lib/api.ts` :62-82 (fetch+Bearer) · :332-342 (PUT) | 부분 (운영 HTML 0건 — 목업만) |
| `docs/supplier-guide.md` (신규) | docs | — | `docs/reference-capture-guide.md` :1-63 (§0 원칙 · §1 표 · §2·§3 항목) + `help.tsx` :27-58 (쉬운 말 톤) | role-match |
| `docs/contract.md` (수정: §2 새 엔드포인트 · §3 ReferenceMotion 필드 · §5 문구) | docs (contract) | — | 자기 자신 :50-69 (`POST /upload-url`) · :285-300 · :812-819 | exact |
| `docs/ia.md` (수정: :189 · :191 · :200 행) | docs | — | 자기 자신 :185-200 | exact |
| `docs/reference-capture-guide.md` (수정: :27 · :47-48) | docs | — | 자기 자신 | exact |
| `docs/reference-motions.md` (수정: §3 스키마에 등록 필드) | docs | — | 자기 자신 :43-88 (필드 옆 `// seed` `// reprocess` `// backfill` 출처 주석) | exact |

---

## Pattern Assignments

### `backend/functions/reference-upload-url/app.py` (controller, request-response)

**Analog:** `backend/functions/upload-url/app.py` (72줄 전체) + `backend/functions/reference-auto-register/app.py` :49-51, :87-99

**Imports · 모듈 상수 패턴** (`upload-url/app.py` :12-30):
```python
from __future__ import annotations

import logging
import os
import uuid

import boto3  # Lambda 런타임 제공

from sunity_shared import responses
from sunity_shared.auth import AuthError, verify_request
from sunity_shared.s3keys import build_upload_key
from sunity_shared.validation import ValidationError, validate_upload_request

log = logging.getLogger()
log.setLevel(logging.INFO)

_BUCKET = os.environ["VIDEO_BUCKET"]
_EXPIRES = 900  # presigned URL 만료(초)
_s3 = boto3.client("s3")
```

**핸들러 골격 — 인증 → 검증 → 부작용 1 → 응답** (`upload-url/app.py` :33-72):
```python
def lambda_handler(event: dict, _context) -> dict:
    # 1. 인증 (Firebase Auth UID, 익명 포함)
    try:
        uid = verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)

    # 2. 입력 검증 (contract UploadUrlRequest)
    try:
        req = validate_upload_request(responses.parse_json_body(event))
    except ValidationError as e:
        return responses.error(e.code, e.message, status=e.http_status)

    # 3. analysisId = Firestore 문서 ID. S3 키에 uid/analysisId 박아 트리거가 역추적
    analysis_id = uuid.uuid4().hex
    s3_key = build_upload_key(uid, analysis_id, req.fmt)

    # 4. presigned PUT URL. ContentType 을 묶지 않아 RN 클라이언트가
    #    헤더 불일치로 서명 실패하는 일을 피한다(키 프리픽스로 권한 제한됨).
    try:
        upload_url = _s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": _BUCKET, "Key": s3_key},
            ExpiresIn=_EXPIRES,
        )
    except Exception:  # noqa: BLE001 - 서명 실패는 서버 오류로 통일
        log.exception("presigned URL 생성 실패 analysis_id=%s", analysis_id)
        return responses.error(
            "server_error", "업로드 URL 생성에 실패했어요.", status=500
        )

    log.info("upload-url ok uid=%s analysis_id=%s mode=%s", uid, analysis_id, req.mode)
    return responses.ok(
        {
            "analysisId": analysis_id,
            "uploadUrl": upload_url,
            "s3Key": s3_key,
            "expiresInSec": _EXPIRES,
        }
    )
```

**화이트리스트 패턴 — env 미설정도 거부** (`reference-auto-register/app.py` :49-51, :87-99):
```python
_BUCKET = os.environ.get("VIDEO_BUCKET", "")
_BELLE_UID = os.environ.get("BELLE_UID", "")
_s3 = boto3.client("s3")
```
```python
    # 2. BELLE_UID 화이트리스트 — belle 만 호출 가능.
    # env 미설정 시 reject (조용한 통과 금지 — 운영 실수 1차 차단).
    if not _BELLE_UID or uid != _BELLE_UID:
        log.warning(
            "reference-auto-register forbidden — uid=%s belle_uid_set=%s",
            uid,
            bool(_BELLE_UID),
        )
        return responses.error(
            "forbidden",
            "이 endpoint 는 reference 등록 권한이 박혀있는 계정만 호출 가능합니다.",
            status=403,
        )
```

**Firestore 부작용의 실패 매핑** (`reference-auto-register/app.py` :164-179):
```python
    # 6. Firestore upsert (idempotent).
    try:
        set_reference_motion_with_gemini(
            motion_id,
            gemini_a=gemini_a,
            idempotent=True,
        )
    except Exception:  # noqa: BLE001 - Firestore 실패 server_error 통일
        log.exception(
            "set_reference_motion_with_gemini 실패 motion_id=%s", motion_id
        )
        return responses.error(
            "server_error",
            "reference 등록에 실패했어요.",
            status=500,
        )
```

**플래너 메모 (진단):** 이 핸들러는 `upload-url` 골격에 (a) 화이트리스트 블록을 2단계 뒤에, (b) `firestore_admin.create_reference_registration(...)` 를 서명 **전** 부작용으로 끼운 것이다. 화이트리스트는 `_BELLE_UID` 단일 비교를 `{u.strip() for u in os.environ.get("SUPPLIER_UIDS","").split(",") if u.strip()} | ({_BELLE_UID} if _BELLE_UID else set())` 집합으로 일반화(RESEARCH §D). 키는 `build_reference_upload_key(uid, ref_id, req.fmt)` — uid 는 **토큰 uid 만**(RESEARCH §보안 V4). 응답 키는 `{refId, uploadUrl, s3Key, expiresInSec}` 로 `upload-url` 의 camelCase 응답과 같은 어법.

---

### `backend/shared/python/sunity_shared/s3keys.py` (utility, transform)

**Analog:** 자기 자신 :1-44

**정정 대상 헤더 주석** (:1-5 — D-17 "30일" 문장):
```python
"""S3 객체 키 규칙. upload-url 이 발급하고 pipeline 이 역파싱한다.

원본 영상은 uploads/ 프리픽스 → 수명주기 정책으로 30일 후 자동 삭제
(backend_CLAUDE.md 비용 관리). 분석 결과/기준 모션은 별도 프리픽스.
"""
```

**정규식 + build + frozen dataclass + parse 4종 세트** (:13-44):
```python
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
```

**"단일 출처" docstring 관례** (:47-55 — 새 키 함수의 docstring 은 이 형식):
```python
def build_coach_audio_key(uid: str, analysis_id: str, record_id: str) -> str:
    """재생 중 큐 오디오 mp3 의 canonical S3 키 (Phase 32 Plan 32-16, D-18).

    **단일 출처** — pipeline(합성 저장)과 playback-url(서버 구성 canonical key +
    저장 key exact 비교, 리뷰 H-02)이 이 함수 하나를 공유해 drift 를 차단한다.
    ...
    """
    return f"{RESULT_PREFIX}/{uid}/{analysis_id}/coach_audio_{record_id}.mp3"
```

**플래너 메모 (진단):** `REFERENCE_PREFIX` 는 이미 있다(:15) — 새 상수 대신 재사용. RESEARCH 코드 예시 A 의 `_REFERENCE_KEY_RE = ^reference/(?P<uid>[A-Za-z0-9]+)/(?P<ref_id>[A-Za-z0-9]+)\.(?P<ext>mp4|mov)$` 는 위 `_UPLOAD_KEY_RE` 와 **uid 세그먼트만 다르다**(`[^/]+` → `[A-Za-z0-9]+`, 평면 `reference/ref-*.mp4` 와 `reference/_archive/` 배제 목적). `ParsedReferenceKey(uid, ref_id, ext)` frozen dataclass.

---

### `backend/shared/python/sunity_shared/validation.py` (utility/validator, transform)

**Analog:** 자기 자신 :1-98 (98줄 전체)

**모듈 docstring — "순수 함수" 선언** (:1-4):
```python
"""POST /upload-url 입력 검증. contract.md §2 UploadUrlRequest 기준.

순수 함수(boto3/네트워크 무관) — AWS 없이 유닛 테스트 가능해야 한다.
"""
```

**`ValidationError` (code · message · http_status)** (:13-24):
```python
class ValidationError(Exception):
    """검증 실패. http_status + (가능하면) contract 오류 code 를 실어 보낸다.

    code 가 ERROR_MESSAGE 에 있으면 앱이 동일 문구를 재사용(size_exceeded 등).
    그 외(bad_request)는 앱이 일반 처리.
    """

    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
```

**id 형식 가드 (재사용)** (:27-36):
```python
def validate_analysis_id_format(analysis_id) -> bool:
    """analysisId 형식 가드 (uuid hex 32자 전제 — 영숫자 + 길이 16 이상).
    ...
    """
    return isinstance(analysis_id, str) and analysis_id.isalnum() and len(analysis_id) >= 16
```

**frozen dataclass + 검증 함수 본체 — 타입·enum·bool 위장 int 거부·contract 코드 재사용** (:39-98):
```python
@dataclass(frozen=True)
class UploadRequest:
    mode: str
    file_name: str
    file_size_bytes: int
    fmt: str
    reference_motion_id: str | None


def validate_upload_request(body: dict) -> UploadRequest:
    """contract UploadUrlRequest 검증 후 정규화. 실패 시 ValidationError.

    - format 불가  → unsupported_format (앱이 ERROR_MESSAGE 재사용)
    - 100MB 초과   → size_exceeded
    - mode1 인데 referenceMotionId 없음 → bad_request
    """
    if not isinstance(body, dict):
        raise ValidationError("bad_request", "요청 본문이 올바르지 않습니다.")

    mode = body.get("mode")
    if mode not in models.MODES:
        raise ValidationError("bad_request", "mode 는 mode1 또는 mode3 이어야 합니다.")

    file_name = body.get("fileName")
    if not isinstance(file_name, str) or not file_name.strip():
        raise ValidationError("bad_request", "fileName 이 필요합니다.")

    fmt = body.get("format")
    if fmt not in models.VIDEO_FORMATS:
        raise ValidationError(
            models.ERR_UNSUPPORTED_FORMAT,
            models.ERROR_MESSAGE[models.ERR_UNSUPPORTED_FORMAT],
        )

    size = body.get("fileSizeBytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValidationError("bad_request", "fileSizeBytes 가 올바르지 않습니다.")
    if size > models.MAX_VIDEO_BYTES:
        raise ValidationError(
            models.ERR_SIZE_EXCEEDED,
            models.ERROR_MESSAGE[models.ERR_SIZE_EXCEEDED],
        )

    ref_id = body.get("referenceMotionId")
    if mode == models.MODE_EXPERT:
        if not isinstance(ref_id, str) or not ref_id.strip():
            raise ValidationError(
                "bad_request", "mode1 은 referenceMotionId 가 필수입니다."
            )
        ref_id = ref_id.strip()
    else:
        ref_id = None  # mode3 은 비교 대상 없음

    return UploadRequest(
        mode=mode,
        file_name=file_name.strip(),
        file_size_bytes=size,
        fmt=fmt,
        reference_motion_id=ref_id,
    )
```

**플래너 메모 (진단):** `ReferenceUploadRequest` frozen dataclass(name · athlete_name · level · technique_name · is_split · has_hold · standing_start · clip_range · consent_* · fmt · file_size_bytes · duration_sec) + `validate_reference_upload_request(body)`. bool 필드는 `isinstance(v, bool)` 로만(위 :74 의 "bool 은 int 로 위장" 거부와 반대 방향의 같은 원칙). `level` 은 앱 picker 가 버리지 않게 `{'basic','intermediate','advanced'}` 상수를 `models.py` 에 두고 3벌 lockstep. 동의 필수 3 = `True` 강제, `training` 기본 `False`.

---

### `backend/shared/python/sunity_shared/models.py` (config, contract 상수)

**Analog:** 자기 자신 :1-12 · :692-713 · :746-768 · :800-815 · :824-836

**헤더 — lockstep 선언** (:1-5):
```python
"""Firestore 문서 모양 + 상수. docs/contract.md §3~5, app/src/types/analysis.ts 미러.

이 파일이 바뀌면 contract.md 와 app 타입도 같이 맞춰야 한다(계약 단일 진실).
PoseFrame/PoleAxis 는 analysis/pose_frame.py 에 정의 (lockstep with app/src/types/analysis.ts).
"""
```

**★ 별도 status enum 선례 — `PIPELINE_SEQUENCE` 에 넣지 않는다** (:746-768, `COACH_STATUS_*`; 등록 상태는 이 블록을 그대로 미러):
```python
# ── coach 텍스트 사후 분리 상태 (quick-260901-wbo — fault_zoom D-06 패턴 미러) ──
#   ...
#   **PIPELINE_SEQUENCE / status enum 에는 절대 추가 금지** — status 머신에 넣으면
#   3-way lockstep(analysis.ts AnalysisStatus + models.py + contract.md §3) 비용이
#   발생한다 (FAULT_ZOOM_STATUSES 블록 서술 미러). coach 상태는 status 진행과 독립된
#   result 내부 scalar 필드(result.coachStatus)로 유지한다. 3-way lockstep 은
#   analysis.ts AnalysisResult.coachStatus? +
#   firestore_admin.update_analysis_coach_text + contract.md coachStatus 절.
COACH_STATUS_PENDING = "pending"
COACH_STATUS_DONE = "done"
COACH_STATUS_FAILED = "failed"
COACH_STATUSES = (
    COACH_STATUS_PENDING,
    COACH_STATUS_DONE,
    COACH_STATUS_FAILED,
)
```

**오류 코드 튜플 + UI 고정 문구 dict** (:800-815):
```python
ANALYSIS_ERROR_CODES = (
    ERR_NO_HUMAN,
    ERR_SIZE_EXCEEDED,
    ERR_UNSUPPORTED_FORMAT,
    ERR_SERVER_ERROR,
    ERR_NOT_POLE_MOTION,
)

# UI 고정 문구. app/src/types/analysis.ts ERROR_MESSAGE 와 동일 문자열.
ERROR_MESSAGE = {
    ERR_NO_HUMAN: "영상에서 사람을 찾지 못했어요. 전신이 보이게 다시 촬영해주세요.",
    ERR_SIZE_EXCEEDED: "100MB 이하 영상만 분석할 수 있어요.",
    ERR_UNSUPPORTED_FORMAT: "mp4, mov 형식의 영상만 분석할 수 있어요.",
    ERR_SERVER_ERROR: "분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
    ERR_NOT_POLE_MOTION: "선택한 기준 동작과 너무 달라요. 폴스포츠 동작이 맞는지 확인하고 다시 시도해주세요.",
}
```

**경로 헬퍼 + 컬렉션 상수** (:824-836):
```python
def analysis_doc_path(uid: str, analysis_id: str) -> str:
    """Firestore: users/{uid}/analyses/{analysisId} (보안 규칙 격리 경로)."""
    return f"users/{uid}/analyses/{analysis_id}"


def reference_motion_path(motion_id: str) -> str:
    """Firestore: reference/{motionId} (앱 읽기 전용)."""
    return f"reference/{motion_id}"


# Firestore 컬렉션 경로는 홀수 segment 여야 함. "reference/motions" 같은 2-segment는
# invalid path 라 collection() 호출 시 ValueError. → reference 단일 컬렉션 채택.
REFERENCE_MOTIONS_COLLECTION = "reference"
```

**플래너 메모 (진단):** `REGISTRATION_STATUS_{REGISTERING,QUEUED,PROCESSING,FAILED,ACTIVE}` + `REGISTRATION_STATUSES` 튜플, `REGISTRATION_ERROR_{NO_HUMAN,MULTIPLE_PEOPLE,NO_STANDING_START,LOW_CONFIDENCE}` + `REGISTRATION_ERROR_MESSAGE` dict(`no_human` 은 `ERROR_MESSAGE[ERR_NO_HUMAN]` 재사용, D-09). `REFERENCE_LEVELS = ("basic","intermediate","advanced")` 도 여기(앱 `LEVEL_ORDER` 미러). 블록 위 주석에 COACH_STATUS 와 같은 "PIPELINE_SEQUENCE 추가 금지" 문장.

---

### `backend/shared/python/sunity_shared/firestore_admin.py` (repository, CRUD)

**Analog:** 자기 자신 — 5개 함수

**클라이언트 seam + 최소 status writer** (:19-43 — 테스트가 `_doc` 을 갈아끼우는 자리):
```python
_client = None


def _db():
    """firestore 클라이언트 1회 생성 (firebase-admin 초기화 재사용)."""
    global _client
    if _client is not None:
        return _client
    _auth._ensure_firebase()  # firebase_admin app 보장
    from firebase_admin import firestore

    _client = firestore.client()
    return _client


def _doc(path: str):
    return _db().document(path)


def update_analysis_status(uid: str, analysis_id: str, status: str) -> None:
    """진행 단계 갱신. status 는 models.PIPELINE_SEQUENCE 중 하나."""
    _doc(models.analysis_doc_path(uid, analysis_id)).set(
        {"status": status, "updatedAt": int(time.time() * 1000)},
        merge=True,
    )
```

**★ ADD-only writer 정본 — 빈 id 거부 → 필수 키 → flat 검증 → `*UpdatedAt` → `set(merge=True)` → 로그** (:2173-2249 `update_reference_body_data`, 본체):
```python
def update_reference_body_data(
    motion_id: str,
    body_profile: dict,
    source_pose: dict | None = None,
) -> None:
    """...
    Raises:
      ValueError: motion_id 빈 / 필수 필드 누락 / values 길이 불일치.
      TypeError: nested-array 위반 (W5 validator 재사용).
    """
    if not motion_id:
        raise ValueError("motion_id required")

    # body_profile 필수 필드 검증.
    missing_bp = [k for k in _REF_BODY_PROFILE_REQUIRED if k not in body_profile]
    if missing_bp:
        raise ValueError(
            f"body_profile missing required fields: {missing_bp}"
        )
    _validate_flat_dict_no_nested_array(
        body_profile, path="bodyNormalizationProfile"
    )

    # source_pose 검증 — None-aware.
    if source_pose is not None:
        ...
        joint_keys = source_pose["jointKeys"]
        values = source_pose["values"]
        expected_len = 4 * len(joint_keys)
        if len(values) != expected_len:
            raise ValueError(
                f"source_pose.values length must be 4 × len(jointKeys) = "
                f"{expected_len}, got {len(values)}"
            )
        # nested-array gate — values 가 list[float] flat 임을 보장.
        _validate_flat_dict_no_nested_array(
            source_pose, path="bodyComparisonSourcePose"
        )

    now_ms = int(time.time() * 1000)
    payload: dict = {
        "bodyNormalizationProfile": body_profile,
        "bodyNormalizationProfileUpdatedAt": now_ms,
    }
    if source_pose is not None:
        payload["bodyComparisonSourcePose"] = source_pose
        payload["bodyComparisonSourcePoseUpdatedAt"] = now_ms

    _doc(models.reference_motion_path(motion_id)).set(payload, merge=True)

    import logging

    log = logging.getLogger(__name__)
    log.info(
        "update_reference_body_data ok motion_id=%s body_conf=%s "
        "source_pose_present=%s",
        motion_id,
        body_profile.get("confidence"),
        source_pose is not None,
    )
```

**"ADD-only — angles 는 절대 payload 에 안 넣는다" 선언** (:2252-2261, `update_reference_downstream_data` 블록 주석 — 새 `set_reference_angles` 는 이 금지의 **유일한 예외**임을 같은 자리 어법으로 선언):
```python
# ── Plan 14-02 (Phase 14) — downstream 4필드 ADD-only merge helper ───────────
# ...
# 3개 flat dict (meanAngles / techniqueProfile / bodyNormalizationProfile) 는 generic
# `_validate_flat_dict_no_nested_array`. ...
# project-wide [[firestore-nested-array-flat]] 정책을 약화시키지 않는다. ADD-only —
# joints3d/angles/activeVersion 은 절대 payload 에 포함하지 않는다 (Pitfall 4 / D-02).
```

**존재 확인 후 분기 — 새 doc vs 기존 doc 보존** (:2402-2431 `set_reference_motion_with_gemini`; `create_reference_registration` 의 "존재하면 실패" 가드의 가장 가까운 선례):
```python
    doc = _doc(models.reference_motion_path(motion_id))
    snap = doc.get()
    exists = snap.exists if snap else False

    now_ms = int(time.time() * 1000)
    is_g3 = routing_branch == "branch_3_auto"

    payload: dict = {
        "motionId": motion_id,
        "geminiA": gemini_a,
        "geminiAUpdatedAt": now_ms,
    }

    if not exists or not idempotent:
        # 새 doc 또는 force override — 분기 라우팅에 따라 isActive/inactiveReason 결정.
        payload["isActive"] = not is_g3
        payload["inactiveReason"] = (
            gemini_a.get("inactive_reason") if is_g3 else None
        )
    else:
        # 기존 doc + idempotent — belle 검수 결과 보존.
        existing = snap.to_dict() or {}
        ...
        if "isActive" in existing:
            payload["isActive"] = existing["isActive"]

    doc.set(payload, merge=True)
```

**실패 doc 형상** (:2446-2455 `fail_analysis` — `registrationError` 형상의 선례):
```python
def fail_analysis(uid: str, analysis_id: str, code: str, message: str) -> None:
    """status='failed' + error{code,message} (contract.md §5)."""
    _doc(models.analysis_doc_path(uid, analysis_id)).set(
        {
            "status": models.STATUS_FAILED,
            "error": {"code": code, "message": message},
            "updatedAt": int(time.time() * 1000),
        },
        merge=True,
    )
```

**nested-array 검증기 규칙** (:72-102 `_validate_flat_dict_no_nested_array` 본체 — `referenceKeypointReport` · `consent` dict 에 그대로 적용):
```python
    for key, value in payload.items():
        sub_path = f"{path}.{key}" if path else key
        if value is None or isinstance(value, (str, int, float, bool)):
            continue
        if isinstance(value, dict):
            _validate_flat_dict_no_nested_array(value, path=sub_path)
            continue
        if isinstance(value, list):
            for i, item in enumerate(value):
                item_path = f"{sub_path}[{i}]"
                if item is None or isinstance(item, (str, int, float, bool)):
                    continue
                if isinstance(item, list):
                    raise TypeError(
                        f"{item_path} contains nested list "
                        f"(firestore-nested-array-flat): got nested list"
                    )
                if isinstance(item, dict):
                    _validate_dict_only_scalars(item, path=item_path)
                    continue
                ...
```

**소비처가 읽는 top-level 폴백** (:2600-2609 `get_reference_motion` 꼬리 — 새 doc 은 `versions/` 하위가 없으므로 여기로 떨어진다):
```python
        # candidate 버전 문서가 없으면 안전하게 top-level 로 폴백 (조용한 무효화 방지 로깅).
        log.warning(
            "reference %s: resolved version=%s (source=%s) 문서 부재 → top-level 폴백",
            motion_id, resolved_version, source,
        )

    if base is None:
        return None
    base.setdefault("motionId", motion_id)
    return base
```

**플래너 메모 (진단):** 신설 5개 = `create_reference_registration(ref_id, *, supplier_uid, form, consent, video_s3_key)` (**`doc.create(payload)`** — 존재하면 firebase-admin 이 예외, 기존 11개 구조적 무접촉; 리포에 `create()` 선례 0건이라 위 :2402-2404 의 `snap.exists` 검사와 달리 원자적임을 docstring 에 적을 것) · `set_reference_angles(...)` (RESEARCH 코드 예시 C, `ref_id.startswith("ref-")` 거부 + `len(angles_flat) == frames * len(joint_keys)` 길이 검사 = 위 :2218-2223 의 `4 × len(jointKeys)` 검사 미러) · `set_reference_registration_status(ref_id, status, *, error=None, queued_reason=None)` (`fail_analysis` 형상 미러, 필드명 `registrationStatus`/`registrationError`/`registrationUpdatedAt`) · `set_reference_self_score(ref_id, score, analysis_id)` · `create_analysis_doc(uid, analysis_id, payload)` (앱 `loading.tsx` :160-178 형상 미러 — 아래 supplier/index 항목 참조).

---

### `backend/functions/pipeline/app.py` (SQS consumer + register service + selfScore 훅)

**Analog:** 자기 자신 — 6자리

**s3keys import 자리** (:115-120 — `parse_reference_key` 를 여기 추가):
```python
from sunity_shared.s3keys import (
    build_coach_audio_key,
    build_fault_zoom_key,
    build_rendered_compare_key,
    parse_upload_key,
)
```

**★ `lambda_handler` 루프 — 분기 삽입 자리 :10309 앞** (:10297-10348 전체):
```python
def lambda_handler(event: dict, _context) -> dict:
    """SQS 이벤트 → 메시지마다 RunPod 위임 또는 직접 처리.

    RunPod 위임 분기: _runpod_enabled() True 시 status=queued 로 일단 표시하고
    HTTP POST. Pod 가 202 를 반환하면 그 이후 status 갱신은 RunPod 서버가 책임.
    위임 호출 자체가 실패하면(타임아웃·5xx) ERR_SERVER_ERROR 로 매핑.
    """
    processed = 0
    delegated = _runpod_enabled()
    if delegated:
        log.info("RunPod 위임 모드 ON url=%s", _RUNPOD_URL)
    for bucket, key in iter_s3_keys_from_sqs(event):
        parsed = parse_upload_key(key)
        if parsed is None:
            log.warning("스킵: 인식 불가 S3 키 %s", key)
            continue
        uid, analysis_id = parsed.uid, parsed.analysis_id
        try:
            if delegated:
                # 위임 시 Lambda 는 queued 까지만 갱신. 그 이후 단계는 RunPod 책임.
                firestore_admin.update_analysis_status(
                    uid, analysis_id, models.STATUS_QUEUED
                )
                _delegate_to_runpod(bucket, key)
            else:
                _process(bucket, key, uid, analysis_id)
            processed += 1
        except NoHumanError:
            log.info("인체 미감지 uid=%s analysis_id=%s", uid, analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_NO_HUMAN,
                models.ERROR_MESSAGE[models.ERR_NO_HUMAN],
            )
        except NotPoleMotionError:
            log.info("비폴 영상 차단 uid=%s analysis_id=%s", uid, analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_NOT_POLE_MOTION,
                models.ERROR_MESSAGE[models.ERR_NOT_POLE_MOTION],
            )
        except Exception:  # noqa: BLE001
            log.exception("분석 실패 analysis_id=%s", analysis_id)
            firestore_admin.fail_analysis(
                uid,
                analysis_id,
                models.ERR_SERVER_ERROR,
                models.ERROR_MESSAGE[models.ERR_SERVER_ERROR],
            )
    return {"processed": processed}
```

**RunPod 위임 — urllib · UA 헤더 · 10s · 200/202 외 예외** (:187-236; `/register-reference` 위임은 URL 인자만 다른 같은 함수):
```python
# RunPod 위임 환경 — 운영에서만 set. 미설정 시 폴백(_process) 이라 개발은 그대로.
_RUNPOD_URL = os.environ.get("RUNPOD_ANALYZE_URL", "").strip()
_RUNPOD_TOKEN = os.environ.get("RUNPOD_AUTH_TOKEN", "").strip()
_RUNPOD_TIMEOUT_S = 10  # HTTP 위임 응답 대기 (Pod 은 202 즉시 반환 — 늦으면 장애)


def _runpod_enabled() -> bool:
    return bool(_RUNPOD_URL and _RUNPOD_TOKEN)
```
```python
def _delegate_to_runpod(bucket: str, key: str) -> None:
    """RunPod /analyze 로 위임. 202/200 외 응답은 예외 → Lambda 가 fail_analysis 매핑.
    urllib 표준 라이브러리만 사용(requests 의존성 X — Layer 추가 부담 없음).
    ..."""
    payload = json.dumps({"bucket": bucket, "key": key}).encode("utf-8")
    req = urllib.request.Request(
        _RUNPOD_URL,
        method="POST",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "sunity-motion-pilot/1.0 (+aws-lambda)",
            "X-RunPod-Token": _RUNPOD_TOKEN,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_RUNPOD_TIMEOUT_S) as resp:
            if resp.status not in (200, 202):
                body = resp.read()[:512]
                raise RuntimeError(f"runpod {resp.status}: {body!r}")
    except urllib.error.HTTPError as e:
        body = e.read()[:512] if hasattr(e, "read") else b""
        raise RuntimeError(f"runpod HTTPError {e.code}: {body!r}") from e
```

**★ 각도 산출 원형 — 기준 11개와 같은 함수 순서** (:1575-1588 `_angles_from_video`; `_register_reference` 는 이 4줄을 **그대로** 쓴다):
```python
def _angles_from_video(bucket: str, key: str) -> np.ndarray:
    """S3 영상 → 프레임 → NLF 3D keypoints → 관절각(T,J), 시간축 폐색 보간.
    ..."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        _s3_download(bucket, key, tmp.name)
        frames = _FRAME_EXTRACTOR.extract(tmp.name)
    keypoints = _POSE_ESTIMATOR.estimate(frames)  # (T,17,4) — 미감지 시 NoHumanError
    angles = compute_joint_angles(keypoints)
    return temporal_fill(angles, joint_uncertainty(keypoints))
```

**다운로드 helper (delete=False, 예외 시 unlink)** (:1666-1692):
```python
def _download_analysis_video(
    bucket: str,
    key: str,
    *,
    timings_ms: dict[str, int] | None = None,
    analysis_id: str = "",
) -> str:
    """...delete=False
    NamedTemporaryFile — caller(또는 keep_local_video=False 분기) 가 unlink 책임.
    다운로드 예외 시 임시 파일 정리 후 raise (현행 계약 정합).
    """
    if timings_ms is None:
        timings_ms = {}
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        with _stage(timings_ms, analysis_id, "s3_download"):
            _s3_download(bucket, key, tmp_path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    return tmp_path
```

**`_s3_download` — 테스트가 `app._s3` 를 갈아끼우는 seam** (:174-180):
```python
def _s3_download(bucket: str, key: str, dest: str) -> None:
    """영상 다운로드 — 가속 클라이언트가 있으면 그것, 없으면 `_s3`.

    `_s3` 는 **호출 시점**에 본다(모듈 로드 때 묶지 않는다) — 테스트가 `app._s3` 를
    가짜로 바꿔 끼우는 관례(49건)가 그대로 살아야 한다.
    """
    (_s3_dl if _s3_dl is not None else _s3).download_file(bucket, key, dest)
```

**어댑터 싱글턴 + 락** (:1529-1551 `_ensure_adapters`/`_ensure_adapters_locked` 핵심):
```python
    with _ADAPTERS_LOCK:
        _ensure_adapters_locked()
```
```python
    global _FRAME_EXTRACTOR, _POSE_ESTIMATOR, _COACH_WRITER, _RTMW_ENGINE, _POLE_DETECTOR
    if _FRAME_EXTRACTOR is None:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        _FRAME_EXTRACTOR = FfmpegFrameExtractor()
    if _POSE_ESTIMATOR is None:
        _POSE_ESTIMATOR = _RTMWNlfCompat()
    if _RTMW_ENGINE is None:
        # _POSE_ESTIMATOR._engine 재사용 — 동일 RTMW instance.
        # _POSE_ESTIMATOR (RTMWNlfCompat) 의 _engine attribute 가 RTMWPoseEngine.
        _RTMW_ENGINE = _POSE_ESTIMATOR._engine  # type: ignore[attr-defined]
```

**`_RTMWNlfCompat` — 수직 폴백 폴 축 + 사이드카 금지 선언** (:1462-1471, :1484-1495):
```python
    def __init__(self) -> None:
        from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
        from sunity_shared.analysis.pose_frame import PoleAxis
        self._engine = RTMWPoseEngine()
        self._default_pole = PoleAxis(
            axis_vector=(0.0, 1.0, 0.0),
            confidence_level="low",
            source="vertical_fallback",
            frame_index=None,
        )
```
```python
        HIGH-1 v4 박제: 본 method 는 local-return tuple 반환. 사이드카
        mutable instance attribute (v3 의 stale-cache pattern) 영구 폐기.
        RunPod FastAPI BackgroundTasks (server.py:198, 213) 환경에서
        concurrent analyses 가 _POSE_ESTIMATOR 글로벌 공유해도 profile
        leak 0 — caller 가 자기 frame 의 profile 만 local tuple 로 받음.
```

**`_process` 첫 줄 — 등록 경로가 `_process` 를 못 쓰는 이유** (:8595-8606):
```python
def _process(bucket: str, key: str, uid: str, analysis_id: str) -> None:
    _ensure_adapters()
    ...
    firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_QUEUED)

    meta = firestore_admin.get_analysis(uid, analysis_id)
    if meta is None:
        raise RuntimeError(f"분석 문서 없음 users/{uid}/analyses/{analysis_id}")
    mode = meta.get("mode")
```

**mode1 이 `angles` 를 요구하는 줄 — 이 phase 가 없애려는 RuntimeError** (:8901-8905):
```python
        if mode == models.MODE_EXPERT:
            with _stage(timings_ms, analysis_id, "ref_fetch_download"):  # Phase 27 SPD-01
                ref = firestore_admin.get_reference_motion(meta.get("referenceMotionId"))
            if ref is None or "angles" not in ref:
                raise RuntimeError("기준 모션 또는 keyframe 데이터 없음")
```

**★ selfScore 훅 자리 — `complete_analysis` 직후, `meta`·`result` 스코프** (:10109-10135):
```python
        with _stage(timings_ms, analysis_id, "firestore_complete"):  # Phase 27 SPD-01
            firestore_admin.complete_analysis(
                uid,
                analysis_id,
                result,
                angles=np.asarray(angles, dtype=float).reshape(-1).tolist(),
                angles_joint_keys=list(skeleton.JOINT_KEYS),
                angles_frames=int(np.asarray(angles).shape[0]),
                ...
            )
        log.info("분석 완료 uid=%s analysis_id=%s mode=%s", uid, analysis_id, mode)
```
(같은 자리의 "실패해도 분석은 이미 complete" 어법 :10137-10140 — 훅의 try/except 가 따를 문장:)
```python
        # Phase 31 D-05 — correctedPose 자동 생성 enqueue. **fault-zoom 조건부 밖**
        # (H-01): 줌 카드 유무와 무관하게 판단되어야 하고, 여기서 실패해도 분석은
        # 이미 complete 라 사용자 결과에 영향이 없다.
```

**기존 `reference/` 접두사 상수 (재사용 가능, 소비처는 G4 플래그뿐)** (:411-437):
```python
_MODE_REFERENCE_REGISTER: str = "mode1_register"

# S3 key prefix 박제 — 정은지 reference 영상 업로드 위치.
_REFERENCE_KEY_PREFIX: str = "reference/"


def _resolve_is_reference(key: str, meta: dict | None) -> bool:
    ...
    if key.startswith(_REFERENCE_KEY_PREFIX):
        return True
    if meta is not None and meta.get("mode") == _MODE_REFERENCE_REGISTER:
        return True
    return False
```

**플래너 메모 (진단):** RESEARCH 코드 예시 B 대로 `for` 첫 줄에 `ref = parse_reference_key(key)` → `_handle_reference_upload(bucket, key, ref)` → `continue`. `_handle_reference_upload` 는 예외를 **삼키고 doc 만** 갱신(메시지 소비 → 재시도·DLQ 없음, D-20). Pod 부재 판정은 아래 `podwatch.yaml` 의 `pod_expected_up`/`probe` 를 옮겨 온다(SSM 이름은 `## 관측` 절 참조). `_register_reference(bucket, key, uid, ref_id)` 는 `_ensure_adapters()` → `_download_analysis_video(bucket, key, analysis_id=ref_id)` → `_FRAME_EXTRACTOR.extract(path)` → `_POSE_ESTIMATOR._engine.estimate_with_person_counts(frames, _POSE_ESTIMATOR._default_pole)` → `registration_checks.check_registration(...)` → `to_coco17_array` → `compute_joint_angles` → `temporal_fill(..., joint_uncertainty(...))` → `build_keypoint_report(pose_frames, fps=_FRAME_EXTRACTOR.effective_fps_for(path) or effective_fps(src, 9.0))` → `firestore_admin.set_reference_angles(...)` → status `active`+`isActive: True` → 자기 재현성 트리거. `finally: Path(path).unlink(missing_ok=True)`.

---

### `backend/runpod_inference/server.py` (FastAPI route, request-response → background)

**Analog:** 자기 자신 :142-144 · :173-215 · :433-456

**Pydantic 요청 모델** (:142-144 — `RegisterReferenceRequest` 는 같은 두 필드):
```python
class AnalyzeRequest(BaseModel):
    bucket: str = Field(..., description="S3 버킷명")
    key: str = Field(..., description="S3 객체 키 (uploads/{uid}/{analysisId}.{ext})")
```

**토큰 검증 Depends** (:173-181):
```python
def _verify_token(x_runpod_token: str = Header(default="", alias="X-RunPod-Token")) -> None:
    """shared secret 검증. 토큰 미설정 환경은 외부 공개 위험이라 503."""
    if not _AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RUNPOD_AUTH_TOKEN 미설정 — 서버가 비공개 모드로 동작 중.",
        )
    if x_runpod_token != _AUTH_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
```

**background 본체 — 예외 → Firestore 실패 매핑** (:184-215):
```python
def _process_in_background(bucket: str, key: str, uid: str, analysis_id: str) -> None:
    """pipeline.lambda_handler 의 try/except 와 동일 매핑.
    NoHumanError → ERR_NO_HUMAN, NotPoleMotionError → ERR_NOT_POLE_MOTION,
    그 외 → ERR_SERVER_ERROR."""
    try:
        pipeline_app = _load_pipeline_module()
        pipeline_app._process(bucket, key, uid, analysis_id)
        log.info("분석 완료 uid=%s analysisId=%s", uid, analysis_id)
    except NoHumanError:
        log.info("인체 미감지 uid=%s analysisId=%s", uid, analysis_id)
        firestore_admin.fail_analysis(
            uid,
            analysis_id,
            models.ERR_NO_HUMAN,
            models.ERROR_MESSAGE[models.ERR_NO_HUMAN],
        )
    except NotPoleMotionError:
        ...
    except Exception:  # noqa: BLE001
        log.exception("분석 실패 uid=%s analysisId=%s", uid, analysis_id)
        firestore_admin.fail_analysis(
            uid,
            analysis_id,
            models.ERR_SERVER_ERROR,
            models.ERROR_MESSAGE[models.ERR_SERVER_ERROR],
        )
```

**라우트 — 키 파싱 400 · 202 즉시 · BackgroundTasks** (:433-456):
```python
@app.post("/analyze", status_code=202, response_model=AnalyzeResponse)
def analyze(
    req: AnalyzeRequest,
    background: BackgroundTasks,
    _: None = Depends(_verify_token),
) -> AnalyzeResponse:
    parsed = parse_upload_key(req.key)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid key format: {req.key}",
        )
    log.info(
        "/analyze accepted bucket=%s uid=%s analysisId=%s",
        req.bucket,
        parsed.uid,
        parsed.analysis_id,
    )
    background.add_task(
        _process_in_background, req.bucket, req.key, parsed.uid, parsed.analysis_id
    )
    return AnalyzeResponse(
        status="accepted", uid=parsed.uid, analysisId=parsed.analysis_id
    )
```

**플래너 메모 (진단):** `POST /register-reference` = 위 3블록 복제, `parse_upload_key` → `parse_reference_key`, `_process` → `pipeline_app._register_reference`, 실패 매핑은 `firestore_admin.fail_analysis` 대신 `set_reference_registration_status(ref_id, "failed", error=...)`. `NoHumanError` 는 `registration_checks` 가 `reason='no_human'` 으로 바꾸므로 여기서는 `Exception` 하나만(그 외 = `server_error`). `/analyze` 는 byte-무접촉. `server.py` :51 `from sunity_shared.s3keys import parse_upload_key` 에 `parse_reference_key` 추가.

---

### `backend/shared/python/sunity_shared/analysis/registration_checks.py` (pure service, transform)

**Analog:** `hold_height.py` + `rtmw_engine.py` + `keypoint_frame.py` + `skeleton.py`

**모듈 헤더 어법 — 왜/어떻게/fail-closed/채점 무접촉** (`hold_height.py` :1-26 골격):
```python
"""유지 구간 몸 높이 — ... (quick-260924-vj1).

왜 있나
───────
...
어떻게 재나 (ig3 유지 구간 상수와 같은 규율)
──────────────────────────────────────────
...
fail-closed (None)
──────────────────
보고서 형상 이상 · 창 이전 프레임 부족 · 창이 짧음 · 서 있는 자세로 볼 수 없음(몸길이 ≤ 0) ·
신뢰도 하한 미만 관절만 남음. None 이면 호출측은 아무 문장도 만들지 않는다(지금 문구 byte-동일).

채점 무접촉: 산출은 카드 문장 선택(`body_low_arm_open`)과 로그에만 쓰인다. 감점 md·record 값·순간에 닿지 않는다.
"""

from __future__ import annotations

import math
import warnings
from typing import Mapping

import numpy as np
```

**상수 선언 어법 — 이웃 모듈과 같은 값 + 테스트 대조** (`hold_height.py` :36-55):
```python
# 좌표 신뢰 하한 — card_gates.HOLD_CONF_MIN(0.35, "각도 측정 좌표 신뢰 하한")과 같은 층.
# 값만 같게 두는 이유: card_gates 는 Gemini 설정·렌더러를 끌어와 순수 모듈이 import 하면 무거워진다.
# 두 값이 갈라지지 않게 test_hold_height.py 가 대조한다(신규 튜닝 상수 0).
MIN_CONF = 0.35
...
NOISE_BODY_LENGTH = 0.05
# 바닥 기준 위반 폭(몸길이 비) — 창 낮은발 10% 분위가 이보다 아래면 "창 이전 = 서 있음"이 거짓(hold_window_heights 주석).
FLOOR_VIOLATION_BODY_LENGTH = 2 * NOISE_BODY_LENGTH
```

**keypointReport dict → 배열 (형상 어긋나면 None)** (`hold_height.py` :63-80 `_arrays` — `low_confidence` 판정의 입력 파서로 그대로 재사용):
```python
def _arrays(report: Mapping | None):
    """keypointReport(dict) → (X (T,J,2), C (T,J), 이름→열) | None. 형상이 어긋나면 None."""
    if not isinstance(report, Mapping):
        return None
    try:
        joints = list(report.get("joints") or [])
        T = int(report.get("frames") or 0)
        J = len(joints)
        data = np.asarray(report.get("data") or [], dtype=float)
        conf = np.asarray(report.get("confidence") or [], dtype=float)
    except (TypeError, ValueError):
        return None
    if T <= 0 or J == 0 or data.size != T * J * 2 or conf.size != T * J:
        return None
    idx = {name: i for i, name in enumerate(joints)}
    if any(n not in idx for n in _NEEDED):
        return None
    return data.reshape(T, J, 2), conf.reshape(T, J), idx
```

**★ 서 있는 시작 — 바닥·몸길이는 창 이전 프레임, 위반 판정은 10% 분위** (`hold_height.py` :96-122, :167-179):
```python
def _frame_series(report, window):
    """한 영상 → **전체 길이** 프레임별 높이 5종 + 짝 선택 재료. 창 이전(서 있는) 프레임이 바닥·몸길이. 못 재면 None."""
    arr = _arrays(report)
    if arr is None:
        return None
    X, C, idx = arr
    T = X.shape[0]
    try:
        w0, w1 = int(window[0]), int(window[1])
    except (TypeError, ValueError, IndexError):
        return None
    if w0 < MIN_STAND_FRAMES or w1 > T or w1 - w0 < MIN_WINDOW_FRAMES:
        return None
    ank = np.vstack([_y(X, C, idx, "left_ankle"), _y(X, C, idx, "right_ankle")]).T
    sho = np.vstack([_y(X, C, idx, "left_shoulder"), _y(X, C, idx, "right_shoulder")]).T
    ...
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        ank_mean = np.nanmean(ank, axis=1)
        sho_mean = np.nanmean(sho, axis=1)
        floor = _nanmedian(ank_mean[:w0])
        body = _nanmedian((ank_mean - sho_mean)[:w0])
        if not (math.isfinite(floor) and math.isfinite(body)) or body <= 0.0:
            return None
```
```python
    # quick-260925-nnt — 바닥 기준 검증(fail-closed). 창 안 낮은발이 바닥 **아래**로 내려가면 "창 이전 = 서 있음" 가정이
    # 깨진 것이다(발이 바닥 밑에 있을 수 없다). ...
    # 판정 통계 = 창의 10% 분위(한 프레임 튐은 무시). ... 문턱 = 잡음 폭 2배(−0.10) — 그 사이.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for side in (s, r):
            v = np.asarray(side["lowFoot"], dtype=float)
            v = v[np.isfinite(v)]
            if v.size == 0 or float(np.percentile(v, 10)) < -FLOOR_VIOLATION_BODY_LENGTH:
                return None
```

**사람 미검출 — 엔진 예외 원형** (`rtmw_engine.py` :226-238):
```python
        T = len(frames)
        if T == 0:
            return []

        _, H, W, _ = frames.shape
        raw_first = self._infer_raw(frames)
        pose_frames, detected_count = self._build_pose_frames(raw_first, W, H, pole_axis)

        if detected_count == 0:
            raise NoHumanError(
                f"RTMW 전 프레임 미감지 ({T}개 중 0개). "
                "영상에 사람이 없거나 카메라 각도를 확인하세요."
            )
```

**12관절 이름 (report `joints` 순서)** (`keypoint_frame.py` :65-79):
```python
_KEYPOINT_NAMES: tuple[KeypointName, ...] = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_hand",
    "right_hand",
    # ── 32-14 (D-22 1단) 신규 — legacy 8 뒤에 append (기존 8 순서 불변) ──
    "left_ankle",
    "right_ankle",
    "left_elbow",
    "right_elbow",
)
```

**한국어 라벨 dict 어법 (8개뿐 — 12개용 신설 필요)** (`skeleton.py` :53-62):
```python
JOINT_LABEL_KO: dict[str, str] = {
    "left_elbow": "왼쪽 팔꿈치",
    "right_elbow": "오른쪽 팔꿈치",
    "left_shoulder": "왼쪽 어깨",
    "right_shoulder": "오른쪽 어깨",
    "left_hip": "왼쪽 고관절",
    "right_hip": "오른쪽 고관절",
    "left_knee": "왼쪽 무릎",
    "right_knee": "오른쪽 무릎",
}
```

**플래너 메모 (진단):** `RegistrationVerdict(ok, reason, detail)` frozen dataclass + `check_registration(pose_frames, person_counts, report, *, n_stand, fps)`; 하위 순수 함수 `multiple_people(person_counts, ratio=0.30)` · `standing_start_ok(report, n_stand)` (위 `_frame_series` 를 `(n_stand, T)` 창으로 부르고 None 또는 10% 분위 위반이면 False — `FLOOR_VIOLATION_BODY_LENGTH` 는 **import 해서 쓰고 옮기지 않는다**) · `low_confidence_joints(report, min_conf=0.5)` (관절별 중앙값 < 문턱 목록, `_arrays` 재사용). 라벨은 `_KEYPOINT_NAMES` 12개 전부 덮는 `KEYPOINT_LABEL_KO` 를 이 모듈에(`left_hand` → "왼손", `left_ankle` → "왼쪽 발목" 어법은 `JOINT_LABEL_KO` 따라). 문턱 3개(0.30 · 첫 1.0초 · 0.5)는 RESEARCH A5~A7 [ASSUMED] — 상수 하나씩, 시험 영상으로만 조정.

---

### `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py` (adapter — `estimate_with_person_counts`)

**Analog:** 자기 자신 :254-285 · :287-320 (부분 — N 이 버려지는 자리)

**★ 사람 수가 버려지는 줄** (:262-285 `_infer_raw`):
```python
        out: list[tuple[np.ndarray, np.ndarray] | None] = []
        for t in range(len(frames)):
            # rtmlib inferencer 호출 — (keypoints, scores) 반환.
            # rtmlib Wholebody 0.0.15 는 단일 (H,W,3) frame 만 받음 — batch 미지원.
            # output = ((N,133,2or3), (N,133)) — N 명 사람.
            result = self._inferencer(frames[t])
            kps_batch, scores_batch = result  # (N, 133, 2/3), (N, 133)

            if kps_batch is None or len(kps_batch) == 0:
                out.append(None)  # 미감지 → PoseFrame.empty (build 단계)
                continue

            # 첫 번째 사람(인덱스 0) 사용 (폴스포츠 = 1인 영상)
            kps = kps_batch[0]   # (133, 2/3)
            scores = scores_batch[0]  # (133,)
```

**local-return tuple 선례** (:287-320 `_build_pose_frames` 시그니처 `-> tuple[list[PoseFrame], int]` 와 :232 `pose_frames, detected_count = ...`):
```python
    def _build_pose_frames(
        self,
        raw: list[tuple[np.ndarray, np.ndarray] | None],
        image_width: int,
        image_height: int,
        pole_axis: PoleAxis,
    ) -> tuple[list[PoseFrame], int]:
        """원시 추론 결과 → list[PoseFrame] + 감지 프레임 수 (기존 변환부 분리, 32-15)."""
```

**DI factory (테스트가 mock 주입)** (:169-193):
```python
    @classmethod
    def create_with_inferencer(
        cls,
        inferencer: Any,
        manifest_path: Path | str | None = None,
        target_fps: int = 30,
    ) -> "RTMWPoseEngine":
        """DI factory — 단위 테스트가 mock inferencer 주입.
        ...
        """
        resolved = Path(manifest_path) if manifest_path else _DEFAULT_MANIFEST_PATH
        selected_weight = _load_eligible_weight(resolved)

        instance = cls.__new__(cls)
        instance._inferencer = inferencer
        instance._selected_weight = selected_weight
        instance._target_fps = target_fps
        return instance
```

**플래너 메모 (진단):** `estimate()` 는 byte-동일 유지. 신설 `estimate_with_person_counts(frames, pole_axis) -> tuple[list[PoseFrame], list[int]]` — `_infer_raw` 를 복제하지 말고 `_infer_raw_with_counts` 로 분리해 `(out, counts)` 를 돌려주고 `_infer_raw` 는 `return self._infer_raw_with_counts(frames)[0]` 로 위임(회귀 0). 2-pass(rot180/PR) 는 등록 경로에서 `estimate()` 와 같은 디스패처를 타야 좌표가 같아진다 — `estimate` 의 :240-252 를 그대로 호출하는 구조로.

---

### `backend/scripts/requeue_reference_registrations.py` (script, batch)

**Analog:** `e2e_app_path.py` + `podwatch.yaml` + `pod_teardown.py` (조합)

**스크립트 헤더·사용법 어법** (`e2e_app_path.py` :1-14):
```python
#!/usr/bin/env python3
"""E2E — 앱과 동일 경로 (upload-url → Firestore 문서 먼저 → S3 PUT → 완료 폴링).

memory demo-only-pod-bring-up-procedure 의 순서 규율 그대로:
문서를 PUT 뒤에 쓰면 파이프라인이 meta 를 못 읽어 조용히 mode3 로 떨어진다.
계약: {mode, fileName, format, fileSizeBytes, referenceMotionId} camelCase.

사용: backend/.venv/bin/python backend/scripts/e2e_app_path.py --video <path> --mode mode1|mode3 [--reference <refId>] [--uid <uid>]
...
"""
```

**urllib JSON helper + Admin Firestore 클라이언트** (`e2e_app_path.py` :33-40, :56-61):
```python
def http_json(url: str, body: dict | None = None, headers: dict | None = None, method: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())
```
```python
def firestore_client():
    import firebase_admin
    from firebase_admin import credentials, firestore
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json")))
    return firestore.client()
```

**Pod 존재 판정 원형** (`backend/infra/podwatch.yaml` :135-170 — Lambda `_handle_reference_upload` 의 Pod 판정도 이것):
```python
          def pod_expected_up():
              """Pod 이 켜져 있어야 하는 시간대인가.
              ...
              파라미터가 없으면 up 으로 본다 — 파일럿 중에는 켜져 있는 것이 기본이고,
              모르는 상태를 조용히 넘기면 감시가 아니게 된다.
              """
              try:
                  v = _ssm.get_parameter(Name=POD_EXPECTED_PARAM)["Parameter"]["Value"]
                  return v.strip().lower() != "down"
              except Exception:  # noqa: BLE001 - 미등록/조회실패는 up 으로 (fail-loud)
                  return True


          def health_url(analyze_url):
              """.../analyze -> .../health"""
              u = analyze_url.strip()
              if u.endswith("/analyze"):
                  return u[: -len("/analyze")] + "/health"
              return u.rstrip("/") + "/health"


          def probe(url):
              """(healthy, detail). 200 만으로는 부족하다 — 모델이 올라온 상태여야 분석이 된다."""
              req = urllib.request.Request(url, headers={"User-Agent": "sunity-podwatch/1"})
              with urllib.request.urlopen(req, timeout=12) as r:
                  body = r.read(4096).decode("utf-8", "replace")
                  if r.status != 200:
                      return 0, "http %s" % r.status
                  try:
                      d = json.loads(body)
                  except ValueError:
                      return 0, "non-json: %s" % body[:120]
                  ok = d.get("status") == "ok" and bool(d.get("pipeline_loaded"))
                  return (1 if ok else 0), body[:200]
```

**SSM 파라미터 이름 (쓰기 측)** (`pod_teardown.py` :124-127):
```python
    for name, val in (("/sunity/motion/runpod-analyze-url", PLACEHOLDER),
                      ("/sunity/motion/runpod-pod-expected", "down")):
        ssm.put_parameter(Name=name, Value=val, Type="String", Overwrite=True)
    print("SSM 되돌림 (pod-expected=down)")
```

**플래너 메모 (진단):** `reference` 컬렉션 `where("registrationStatus","==","queued")` 단일 쿼리(Spark 캡 — Pitfall 8) → 각 doc 의 `videoS3Key` 로 Pod `POST {base}/register-reference {bucket,key}` (헤더 `X-RunPod-Token` — `_delegate_to_runpod` :222-227 과 같은 4개). 순차. `--dry-run` 플래그(`intake_clips.py` :32 관례). 이 스크립트가 없으면 만든 기능은 안 돈 것(메모리 build-it-and-schedule-it) — Pod 기동 절차 6단계로 문서화.

---

### `backend/template.yaml` (IaC)

**Analog:** 자기 자신 :101-112 · :184-210 · :255-299 · :389-394

**Globals — 모든 함수가 상속하는 env** (:101-112):
```yaml
Globals:
  Function:
    Runtime: python3.12
    Architectures: [arm64]
    Timeout: 15
    MemorySize: 256
    Layers:
      - !Ref SharedLayer
    Environment:
      Variables:
        VIDEO_BUCKET: !Ref VideoBucketName
        FIREBASE_SA_PARAM: !Ref FirebaseSaParam
```

**★ 새 함수 블록의 정본 — PutObject 접두사 정책 + SSM 명시 Statement + HttpApi 이벤트** (:184-210 `UploadUrlFunction`):
```yaml
  UploadUrlFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub sunity-motion-${Stage}-upload-url
      CodeUri: functions/upload-url/
      Handler: app.lambda_handler
      Timeout: 10
      Policies:
        - Statement:
            - Effect: Allow
              Action: s3:PutObject
              Resource: !Sub arn:aws:s3:::${VideoBucketName}/uploads/*
        - Statement:
            # SAM SSMParameterReadPolicy 가 leading slash 가 있는 ParameterName 을
            # 잘못 변환해 `parameter//sunity/...` 이중 슬래시 ARN 으로 박는 버그가
            # 있어 명시적 Statement 로 작성. ARN 은 `parameter${name}` 형식이라
            # FirebaseSaParam(`/sunity/motion/firebase-sa`) 의 leading slash 가 그대로 ARN 의 `/` 와 합쳐진다.
            - Effect: Allow
              Action: ssm:GetParameter
              Resource: !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter${FirebaseSaParam}
      Events:
        Post:
          Type: HttpApi
          Properties:
            ApiId: !Ref MotionHttpApi
            Method: POST
            Path: /upload-url
```

**SSM 동적 참조 env + `reference/*` 정책 + 헤더 주석 어법** (:255-299 `ReferenceAutoRegisterFunction`):
```yaml
  # ── POST /reference/auto-register : 정은지 영상 → Gemini A → reference 자동 등록 ──
  # Plan 17-05. AI-SPEC §1b 영역 A. belle 만 호출 가능 (BELLE_UID 이중 인증).
  # ...
  ReferenceAutoRegisterFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub sunity-motion-${Stage}-reference-auto-register
      CodeUri: functions/reference-auto-register/
      Handler: app.lambda_handler
      Timeout: 240
      MemorySize: 512
      Environment:
        Variables:
          ...
          # BELLE_UID — belle Firebase uid 박제. 비박힘 시 403 강제 reject.
          BELLE_UID: "{{resolve:ssm:/sunity/motion/belle-uid}}"
          ...
      Policies:
        - Statement:
            - Effect: Allow
              Action: s3:GetObject
              Resource: !Sub arn:aws:s3:::${VideoBucketName}/reference/*
        - Statement:
            ...
            - Effect: Allow
              Action: ssm:GetParameter
              Resource: !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter${FirebaseSaParam}
      Events:
        Post:
          Type: HttpApi
          Properties:
            ApiId: !Ref MotionHttpApi
            Method: POST
            Path: /reference/auto-register
```

**pipeline — SQS 이벤트 + `${VideoBucketName}/*` Get/Put + RunPod env** (:337-343, :349-353, :389-394):
```yaml
      Environment:
        Variables:
          ...
          RUNPOD_ANALYZE_URL: "{{resolve:ssm:/sunity/motion/runpod-analyze-url}}"
          RUNPOD_AUTH_TOKEN: "{{resolve:ssm:/sunity/motion/runpod-auth-token}}"
```
```yaml
      Policies:
        - Statement:
            - Effect: Allow
              Action: [s3:GetObject, s3:PutObject]
              Resource: !Sub arn:aws:s3:::${VideoBucketName}/*
```
```yaml
      Events:
        Queue:
          Type: SQS
          Properties:
            Queue: !GetAtt AnalysisQueue.Arn
            BatchSize: 1
```

**플래너 메모 (진단):** `ReferenceUploadUrlFunction` = `UploadUrlFunction` 복제 + `Resource: .../reference/*` + `Environment.Variables.SUPPLIER_UIDS: "{{resolve:ssm:/sunity/motion/supplier-uids}}"` + `BELLE_UID` 동일 참조 + `Path: /reference/upload-url`. SSM 파라미터는 deploy **전**에 만들어야 동적 참조가 해석된다(RESEARCH Q7). pipeline 은 이미 `${VideoBucketName}/*` Get/Put 이라 `reference/` 다운로드·`uploads/` 로의 `copy_object`(자기 재현성) 모두 정책 추가 0 — 단 `ssm:GetParameter` 가 `FirebaseSaParam` 하나로 한정돼 있어 Pod 판정용 `pod-expected` 읽기는 **Statement 추가 필요**. 새 라우트는 CFN 변경 = `sam deploy` 체크포인트(RESEARCH §I).

---

### 테스트 6종 (pytest, AWS/Firestore/GPU 0)

**Analog 1 — 핸들러 모듈 fixture (sys.path + env + 모듈 캐시 리셋)** (`test_reference_auto_register_handler.py` :25-46):
```python
_HANDLER_DIR = (
    Path(__file__).resolve().parents[1]
    / "functions"
    / "reference-auto-register"
)


@pytest.fixture
def handler_module(monkeypatch):
    """app.py 를 모듈로 import — sys.path 박제 후 reload 로 env 재평가."""
    sys.path.insert(0, str(_HANDLER_DIR))
    monkeypatch.setenv("VIDEO_BUCKET", "test-bucket")
    monkeypatch.setenv("BELLE_UID", "belle-uid-001")
    # 모듈 cache reset — 다른 테스트가 env 다르게 박은 경우 차단.
    if "app" in sys.modules:
        del sys.modules["app"]
    import app  # noqa: PLC0415 — 동적 import 의도.
    yield app
    if "app" in sys.modules:
        del sys.modules["app"]
    sys.path.remove(str(_HANDLER_DIR))
```

**Analog 1 — Bearer 이벤트 + 외부 호출 전부 monkeypatch + 응답 봉투 단언** (:52-56, :124-131, :158-172):
```python
def _bearer_event(body: dict, token: str = "valid-token") -> dict:
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "body": json.dumps(body),
    }
```
```python
    def test_happy_path_200(self, handler_module, monkeypatch) -> None:
        # verify_request → belle uid.
        monkeypatch.setattr(
            handler_module, "verify_request", lambda evt: "belle-uid-001"
        )
        # S3 mock.
        fake_s3 = _FakeS3()
        monkeypatch.setattr(handler_module, "_s3", fake_s3)
        ...
        resp = handler_module.lambda_handler(event, None)

        assert resp["statusCode"] == 200, resp
        body = json.loads(resp["body"])
        assert body["motionId"] == "ref-butterfly"
```

**Analog 2 — pipeline dispatch fixture (SQS 이벤트 · env 삭제 · `_process`/`_delegate` 교체)** (`test_pipeline_dispatch.py` :17-65):
```python
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _sqs_event(bucket: str, key: str) -> dict:
    """S3 → SQS 메시지 모양 (sunity_shared.events.iter_s3_keys_from_sqs 형식)."""
    body = {
        "Records": [
            {"s3": {"bucket": {"name": bucket}, "object": {"key": key}}}
        ]
    }
    return {"Records": [{"body": json.dumps(body)}]}


@pytest.fixture
def pipeline(monkeypatch):
    """app 모듈을 환경변수 클리어 + monkeypatch 상태로 재로드."""
    for k in ("RUNPOD_ANALYZE_URL", "RUNPOD_AUTH_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    # 어댑터 import 비용 회피 — boto3 만 가짜로
    sys.modules.pop("app", None)
    import app  # noqa: WPS433

    importlib.reload(app)

    calls = {"process": [], "delegate": [], "queued": [], "failed": [], "noHuman": 0}

    def fake_process(bucket, key, uid, analysis_id):
        calls["process"].append((bucket, key, uid, analysis_id))

    def fake_delegate(bucket, key):
        calls["delegate"].append((bucket, key))
    ...
    monkeypatch.setattr(app, "_process", fake_process)
    monkeypatch.setattr(app, "_delegate_to_runpod", fake_delegate)
    monkeypatch.setattr(app.firestore_admin, "update_analysis_status", fake_update_status)
    monkeypatch.setattr(app.firestore_admin, "fail_analysis", fake_fail)

    app._test_calls = calls
    return app
```

**Analog 2 — 위임 실패가 handler 를 죽이지 않는다 / 잘못된 키는 스킵** (:112-147):
```python
    out = pipeline.lambda_handler(_sqs_event("b", "uploads/u3/a3.mp4"), None)

    # 위임 실패해도 lambda_handler 자체는 정상 종료(메시지 1개 처리 = processed:0).
    # 실패 매핑은 ERR_SERVER_ERROR 로.
    assert out == {"processed": 0}
    assert calls["failed"] == [("u3", "a3", pipeline.models.ERR_SERVER_ERROR)]


def test_invalid_key_is_skipped(pipeline):
    out = pipeline.lambda_handler(_sqs_event("b", "results/u/a.mp4"), None)
    assert out == {"processed": 0}
    # 잘못된 키는 fail 도 안 함 — uid 를 모르므로 그냥 스킵.
    assert pipeline._test_calls["failed"] == []
```

**Analog 3 — Firestore writer 단위: `_FakeDoc` 로 `_doc` 교체 + payload 캡처** (`test_reference_auto_register_handler.py` :364-392):
```python
    def test_creates_new_doc_when_missing(self, monkeypatch) -> None:
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeSnap:
            exists = False

        class _FakeDoc:
            def get(self):  # noqa: D401
                return _FakeSnap()

            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload
                captured["merge"] = merge

        monkeypatch.setattr(firestore_admin, "_doc", lambda _p: _FakeDoc())

        gemini_a = _ok_gemini_result(routing_branch="branch_3_auto")
        firestore_admin.set_reference_motion_with_gemini(
            "ref-butterfly", gemini_a=gemini_a, idempotent=True
        )

        payload = captured["payload"]
        # geminiA 박힘.
        assert "geminiA" in payload
```

**Analog 3 — path 별 저장소 (여러 doc 을 한 테스트에서)** (`test_analysis_provenance.py` :308-325):
```python
class _FakeDocStore:
    """firestore_admin._doc path seam (phase33/test_candidate_staging.py 선례)."""

    def __init__(self, store: dict):
        self.store = store

    def __call__(self, path: str):
        outer = self

        class _Ref:
            def get(self):
                return _Snap(outer.store.get(path))

        return _Ref()


def _patch_doc(monkeypatch, store: dict):
    monkeypatch.setattr(firestore_admin, "_doc", _FakeDocStore(store), raising=True)
```

**Analog 4 — 합성 keypointReport 헬퍼 (실패 4형 c·d 강제)** (`test_hold_height.py` :28-57):
```python
_JOINTS = [
    "left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee",
    "left_hand", "right_hand", "left_ankle", "right_ankle", "left_elbow", "right_elbow",
]


def _report(ys: dict, T: int, conf: dict | None = None) -> dict:
    """관절별 y 배열(또는 상수)로 keypointReport dict 를 만든다. x 는 0.5 고정, 신뢰도 기본 0.9."""
    X = np.zeros((T, len(_JOINTS), 2))
    C = np.full((T, len(_JOINTS)), 0.9)
    X[:, :, 0] = 0.5
    for name, y in ys.items():
        X[:, _JOINTS.index(name), 1] = y
    for name, c in (conf or {}).items():
        C[:, _JOINTS.index(name)] = c
    return {"joints": list(_JOINTS), "frames": T, "data": X.reshape(-1).tolist(), "confidence": C.reshape(-1).tolist()}


def _pose(T: int, stand: int, *, hip: float, low_ankle: float, high_ankle: float, hand: float) -> dict:
    """앞 `stand` 프레임은 서 있음(어깨 0.5 · 발목 0.8 → 몸길이 0.3, 바닥 0.8), 이후는 창 자세."""
    def seq(standing, window):
        v = np.full(T, window, dtype=float)
        v[:stand] = standing
        return v
    return {
        "left_shoulder": seq(0.5, 0.35), "right_shoulder": seq(0.5, 0.35),
        "left_hip": seq(0.65, hip), "right_hip": seq(0.65, hip),
        "left_ankle": seq(0.8, low_ankle), "right_ankle": seq(0.8, high_ankle),
        "left_hand": seq(0.6, hand + 0.1), "right_hand": seq(0.3, hand),
    }
```

**Analog 4 — mock inferencer (실패 4형 a·b 강제 — N 을 0 또는 2 로)** (`test_rtmw_engine.py` :38-63):
```python
@pytest.fixture(scope="module")
def default_pole_axis():
    from sunity_shared.analysis.pose_frame import PoleAxis
    return PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )


@pytest.fixture
def mock_inferencer():
    """Mock rtmlib wholebody inferencer — (133, 3) keypoints + (133,) scores 반환."""
    mock = MagicMock()
    # rtmlib Wholebody 반환 형식: (keypoints, scores) 튜플
    # keypoints: (N_person, 133, 2또는3), scores: (N_person, 133)
    kps = np.zeros((1, 133, 2), dtype=np.float32)  # 1명, 133키포인트, xy
    scores = np.full((1, 133), 0.9, dtype=np.float32)
    mock.return_value = (kps, scores)
    return mock


@pytest.fixture
def mock_frames():
    """Mock (T, H, W, 3) RGB uint8 프레임 배열."""
    return np.zeros((3, 480, 640, 3), dtype=np.uint8)
```

**Analog 5 — RunPod 라우트 (TestClient 가 background 를 동기 실행)** (`test_runpod_server.py` :22-48, :89-112):
```python
@pytest.fixture
def server_mod(monkeypatch):
    monkeypatch.setenv("RUNPOD_AUTH_TOKEN", "test-token")
    if "runpod_inference.server" in sys.modules:
        del sys.modules["runpod_inference.server"]
    import runpod_inference.server as server  # noqa: WPS433

    importlib.reload(server)

    calls: list[tuple[str, str, str, str]] = []

    def fake_load_pipeline():
        class FakeMod:
            @staticmethod
            def _process(bucket, key, uid, analysis_id):
                calls.append((bucket, key, uid, analysis_id))

        return FakeMod()

    monkeypatch.setattr(server, "_load_pipeline_module", fake_load_pipeline)
    server._calls = calls  # 테스트에서 접근하기 위해 부착
    return server
```
```python
    assert resp.status_code == 202
    body = resp.json()
    assert body == {
        "status": "accepted",
        "uid": "uid42",
        "analysisId": "analysis99",
    }
    # TestClient 는 background task 도 동기 실행해줘서 _process 가 1회 호출됨.
    assert server_mod._calls == [
        ("sunity-motion-pilot-videos", "uploads/uid42/analysis99.mp4", "uid42", "analysis99")
    ]
```

**Analog 6 — 키/검증 확장 테스트 어법** (`test_s3keys.py` :21-29, `test_validation.py` :60-72):
```python
def test_rejects_foreign_keys():
    for bad in [
        "results/u/a.mp4",
        "uploads/u/a.avi",
        "uploads/a.mp4",
        "uploads/u/a/b.mp4",
        "random",
    ]:
        assert parse_upload_key(bad) is None
```
```python
@pytest.mark.parametrize(
    "patch",
    [
        {"mode": "modeX"},
        {"fileName": "  "},
        {"fileSizeBytes": 0},
        {"fileSizeBytes": "10"},
        {"fileSizeBytes": True},  # bool 은 int 로 위장 — 거부돼야 함
    ],
)
def test_bad_inputs_rejected(patch):
    with pytest.raises(ValidationError):
        validate_upload_request({**OK_MODE3, **patch})
```

**플래너 메모 (진단):** `FakeMod` 에 `_register_reference` 를 추가하면 `/register-reference` 테스트가 같은 fixture 로 된다. `test_register_reference_pipeline.py` 는 `app._s3`(`test_s3_download_accelerate.py` :51 `monkeypatch.setattr(app, "_s3", _Fake())`)·`app._FRAME_EXTRACTOR`(`test_mode3_fault_zoom_selection.py` :110)·`app._POSE_ESTIMATOR` 를 가짜로 끼우고 `firestore_admin.set_reference_angles` 호출 인자만 단언(같은 함수 순서 = `compute_joint_angles → joint_uncertainty → temporal_fill`). 실행은 반드시 `cd backend && .venv/bin/python -m pytest ...`(메모리 dont-trust-subagent-gate-numbers — worktree 에 .venv 없음).

---

### `app/src/app/(tabs)/analyze.tsx` (screen — `validate()` duration)

**Analog:** 자기 자신 :46-47 · :206-236 · :357-364 · :470-473

**상수 어법** (:46-47):
```typescript
const MAX_BYTES = 100 * 1024 * 1024; // design.md: 100MB 초과 불가
const ALLOWED = ['mp4', 'mov']; // design.md: mp4, mov만 지원
```

**★ `validate()` — 종류만 반환, 문구는 `pickerFailure.ts` 소유** (:204-214):
```typescript
  // [quick-260720-hn8] 문구가 아니라 원인 종류만 반환한다 — 사용자 문구 소유권은
  // pickerFailure.ts 단일점(해결단계까지 함께 관리). 화면은 종류→안내 변환만 한다.
  const validate = (
    asset: ImagePicker.ImagePickerAsset,
  ): PickFailureKind | null => {
    const source = asset.fileName ?? asset.uri;
    const ext = source.split('.').pop()?.toLowerCase() ?? '';
    if (!ALLOWED.includes(ext)) return 'format';
    if (asset.fileSize != null && asset.fileSize > MAX_BYTES) return 'tooLarge';
    return null;
  };
```

**`duration` (ms) 을 이미 "유효할 때만" 쓰는 선례** (:216-236 `checkLowQuality`):
```typescript
  // [#20 입력 화질] 저화질 휴리스틱 — 짧은 변이 720p 미만이거나(해상도 부족),
  // 추정 비트레이트가 ~6Mbps 미만(과압축)이면 저화질로 본다. width/height/fileSize/
  // duration 은 시스템이 0/누락으로 줄 수 있으므로 값이 유효할 때만 판정한다(거짓 경고
  // 방지). 막지 않고 경고만 — boolean + 짧은 사유 반환.
  const checkLowQuality = (
    asset: ImagePicker.ImagePickerAsset,
  ): { low: boolean; reason: string } => {
    ...
    const durationSec =
      asset.duration != null && asset.duration > 0 ? asset.duration / 1000 : 0;
```

**wiring — `validate` 결과 → `setFailure(describePickFailure(kind))`** (:357-365):
```typescript
  const handleResult = (result: ImagePicker.ImagePickerResult) => {
    if (result.canceled || !result.assets?.[0]) return;
    const asset = result.assets[0];
    const problem = validate(asset);
    if (problem) {
      setFailure(describePickFailure(problem));
      return;
    }
    setFailure(null);
```

**카메라 옵션 자리 (`videoMaxDuration: 90` 추가)** (:470-473):
```typescript
      const shot = await ImagePicker.launchCameraAsync({
        mediaTypes: ['videos'],
        videoQuality: ImagePicker.UIImagePickerControllerQualityType.High,
      });
```

**플래너 메모 (진단):** `MIN_DURATION_SEC = 3` · `MAX_DURATION_SEC = 90` 상수를 :46-47 옆에 (주석에 `IA 3-3 AC-VID-003-1L` 인용). `validate` 에 `checkLowQuality` 와 같은 `asset.duration != null && asset.duration > 0` 가드 아래 `sec < 3 → 'tooShort'`, `sec > 90 → 'tooLong'` (fail-open, RESEARCH §F).

---

### `app/src/lib/pickerFailure.ts` (copy map — `tooShort` / `tooLong`)

**Analog:** 자기 자신 :20-27 · :53-72 · :125-130

**kind 유니온** (:20-27):
```typescript
export type PickFailureKind =
  | 'permissionCamera'
  | 'permissionLibrary'
  | 'format'
  | 'tooLarge'
  | 'libraryOpen'
  | 'cameraOpen'
  | 'processFailed';
```

**copy 항목 — title + lines(2줄) + 주 버튼** (:51-72):
```typescript
const REPICK_LABEL = '다른 파일 선택';

function copyFor(kind: PickFailureKind): PickFailureCopy {
  switch (kind) {
    // ── Figma 확정 문구 (변경 금지) ──────────────────────────────────────
    case 'tooLarge':
      return {
        title: '용량이 너무 커요',
        lines: [
          '100MB 이하 영상만 업로드 할 수 있어요.',
          '영상을 잘라서 다시 시도해주세요.',
        ],
        primaryLabel: REPICK_LABEL,
        primaryAction: 'repick',
      };
```

**exhaustiveness 게이트 — kind 추가하고 매핑 빠뜨리면 typecheck 가 깨진다** (:125-130):
```typescript
    default: {
      // 컴파일 타임 exhaustiveness 게이트 — PickFailureKind 에 값을 추가하고
      // 매핑을 빠뜨리면 `npm run typecheck` 가 깨진다 (안내 없는 실패 = 회귀).
      const _exhaustive: never = kind;
      return _exhaustive;
    }
```

**플래너 메모 (진단):** `tooShort` lines = IA `AC-VID-003-1L` 원문 `'영상이 너무 짧아요. 동작 전체가 담긴 영상이 필요해요.'` 를 2줄로(`docs/ia.md:200`), `tooLong` 은 신규 [ASSUMED 문구] + IA 표에 행 추가(A14). 둘 다 `primaryAction: 'repick'`.

---

### `app/src/app/analysis/loading.tsx` (문구 3자리 정정)

**Analog:** 자기 자신 — 원문 verbatim

(:490)
```typescript
          ? '촬영 구도나 거리가 기준 영상과 많이 다르면 이렇게 나올 수 있어요. 몸 전체가 화면에 들어오는 거리에서 정면으로 다시 찍어보면 좋아요.'
```
(:519-521)
```typescript
              <Text style={styles.tipItem}>· 측면 45°, 2~3m 거리</Text>
              <Text style={styles.tipItem}>· 밝은 환경, 폴 전체로 보이게</Text>
              <Text style={styles.tipItem}>· 3초 이상, 동작 전체 포함</Text>
```
(:545-547)
```typescript
                  <Text style={styles.tipItem}>
                    · 몸 전체가 화면에 들어오는 거리(약 2~3m)에서 정면으로 촬영했는지
                  </Text>
```

**플래너 메모:** D-15 문장 "기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)" 로 치환. 게이트 = `rtk grep -n '45°\|2~3m\|정면 우선' app/src docs` → 0건 (RESEARCH 테스트 맵). `help.tsx` :46 `'몸 전체가 화면에 잘 들어오는 거리(약 2~3m)에서 정면을 기준으로 촬영해 주세요. …'` 도 같은 grep 에 걸린다 — CONTEXT 5곳 밖이지만 게이트가 잡으므로 함께 정정 대상 [확인 원문].

---

### `app/src/app/(tabs)/profile.tsx` (강사 코드 한 줄)

**Analog:** 자기 자신 :210-224 · :295-310 · :399-416

**정보 리스트 — 배열 map + `InfoRow`** (:210-224):
```typescript
        {/* 정보 리스트 */}
        <View style={styles.infoList}>
          {[
            { label: '주 종목', value: '폴스포츠' },
            { label: '레벨', value: '입문 (기본값)' },
            { label: '앱 버전', value: appVersion },
          ].map((row, i, arr) => (
            <InfoRow
              key={row.label}
              label={row.label}
              value={row.value}
              isLast={i === arr.length - 1}
            />
          ))}
        </View>
```

**`InfoRow` 컴포넌트 (inline prop type)** (:295-310):
```typescript
function InfoRow({
  label,
  value,
  isLast,
}: {
  label: string;
  value: string;
  isLast?: boolean;
}) {
  return (
    <View style={[styles.infoRow, isLast && styles.infoRowLast]}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}
```

**테마 토큰 스타일 (하드코딩 색 0)** (:399-416):
```typescript
  infoList: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    paddingHorizontal: spacing.cardPadding,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  infoRowLast: { borderBottomWidth: 0 },
  infoLabel: { ...typography.caption, color: colors.textSecondary },
  infoValue: { ...typography.boxLabel, color: colors.textPrimary },
```

**계정 카드 바로 아래 자리 (D-12 "계정 카드 아래 한 줄")** — 카드 블록 :137-174 끝 `)}` 다음, "내 몸 정보" :176 앞. 가장 싼 구현 = `{ label: '강사 코드', value: '—' }` 행을 위 배열에 추가(표시만, 데이터 없음). 계정 카드 직하가 요구면 `styles.guestHint` (:348-353, `marginTop: -6`) 와 같은 caption 한 줄.

---

### `app/src/types/analysis.ts` (contract 타입)

**Analog:** 자기 자신 :94-109 · :1302-1329 · :2220-2227

**status / error 유니온 (등록 상태는 여기 **추가하지 않는다** — 별도 타입)** (:94-109):
```typescript
export type AnalysisStatus =
  | 'uploading' // 앱이 S3 업로드 중 (앱이 설정)
  | 'queued' // S3 트리거됨, 파이프라인 대기
  | 'frame_extraction' // 프레임 추출
  | 'pose_analysis' // YOLOX 사람검출 + RTMW-x 133 wholebody → COCO-17
  | 'comparison' // MotionDTW 비교 + 점수
  | 'done'
  | 'failed';

// ml/CLAUDE.md 분석 오류 처리 = design.md §6 오류 4종 + 비폴 차단(belle P1 #8)
export type AnalysisErrorCode =
  | 'no_human'
  | 'size_exceeded'
  | 'unsupported_format'
  | 'server_error'
  | 'not_pole_motion'; // mode1 비교 similarity 가 임계값 미만
```

**`ReferenceMotion` — 필드 옆 출처 주석 어법** (:1302-1329):
```typescript
export interface ReferenceMotion {
  motionId: string;
  name: string; // 동작명
  athleteName: string; // '정은지'
  level: SkillLevel;
  ...
  updatedAt?: number; // epoch ms — 시드/관리자 등록 시 갱신. NEW 배너 정렬용

  // RTMW 추출 시퀀스 (extract_reference_angles.py 결과를 seed-reference-motions
  // 가 Firestore 에 채움). nested-array 금지 회피로 flat 저장 — 백엔드/앱에서
  // anglesJointKeys 길이로 reshape. ...
  anglesJointKeys?: string[]; // 길이 = J (보통 8)
  anglesFrames?: number; // T (디버깅용; angles.length === T*J 인지 확인)
```

**UI 고정 문구 Record (models.py 와 동일 문자열)** (:2220-2227):
```typescript
export const ERROR_MESSAGE: Record<AnalysisErrorCode, string> = {
  no_human: '영상에서 사람을 찾지 못했어요. 전신이 보이게 다시 촬영해주세요.',
  size_exceeded: '100MB 이하 영상만 분석할 수 있어요.',
  unsupported_format: 'mp4, mov 형식의 영상만 분석할 수 있어요.',
  server_error: '분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.',
  not_pole_motion:
    '선택한 기준 동작과 너무 달라요. 폴스포츠 동작이 맞는지 확인하고 다시 시도해주세요.',
};
```

**플래너 메모 (진단):** `export type ReferenceRegistrationStatus = 'registering'|'queued'|'processing'|'failed'|'active'` · `ReferenceRegistrationErrorCode` 4종 · `REGISTRATION_ERROR_MESSAGE: Record<…>` · `ReferenceMotion` 에 `registrationStatus? · registrationError? · queuedReason? · supplierUid? · techniqueName? · isSplit? · hasHold? · standingStart? · consent? · selfScore? · selfCheckStatus? · selfCheckAnalysisId? · anglesRealFps?` (각 필드 옆 `// register` 출처 주석 — `reference-motions.md` §3 어법). `referenceMotions.ts normalize()` :72-78 는 무접촉(새 필드는 strip 되어도 picker 에 영향 0; 공급자 페이지가 자기 doc 을 `useReferenceMotionDoc` 식 단일 구독으로 읽는다).

---

### 공급자 페이지 — 후보 (1) Expo Router 라우트 `app/src/app/supplier/index.tsx` · `guide.tsx`

**Analog (조합):** `analysis/reference.tsx` + `auth/login.tsx` + `help.tsx` + `lib/api.ts` + `lib/referenceMotions.ts` + `lib/authUser.ts` + `_layout.tsx`

**라우트 등록 — 루트 Stack 은 파일 추가만으로 라우트가 생긴다** (`_layout.tsx` :66-71):
```typescript
  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
```

**화면 골격 — 뒤로가기 · heading · sub · 목록 · CTA** (`analysis/reference.tsx` :109-122, :143-179):
```typescript
  return (
    <View style={styles.container}>
      {/* 루트 Stack 이 headerShown:false 라 화면마다 직접 배치 (design.md §9) */}
      <Pressable
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel="뒤로 가기"
        hitSlop={10}
        style={({ pressed }) => [styles.backBtn, pressed && styles.backBtnPressed]}
      >
        <Ionicons name="chevron-back" size={26} color={colors.textPrimary} />
      </Pressable>
      <Text style={styles.heading}>비교할 프로 동작을{'\n'}골라주세요.</Text>
      <Text style={styles.sub}>정은지 선수의 동작 중 하나를 기준으로 분석해요.</Text>
```
```typescript
      <ScrollView
        style={styles.list}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
      >
        {loading && <Text style={styles.placeholder}>불러오는 중...</Text>}
        {!loading && error && <Text style={styles.error}>{error}</Text>}
        {!loading && !error && byLevel.length === 0 && (
          <Text style={styles.placeholder}>
            아직 등록된 기준 동작이 없어요.
          </Text>
        )}
        {byLevel.map((m) => (
          <MotionCard
            key={m.motionId}
            motion={m}
            selected={m.motionId === selectedId}
            onPress={() => setSelectedId(m.motionId)}
          />
        ))}
      </ScrollView>

      <Pressable
        onPress={startAnalysis}
        disabled={!selectedId}
        accessibilityRole="button"
        accessibilityState={{ disabled: !selectedId }}
        style={({ pressed }) => [
          styles.cta,
          (!selectedId || pressed) && styles.ctaDimmed,
        ]}
      >
        <Text style={styles.ctaText}>
          {selected ? `${selected.name}으로 분석 시작` : '동작을 먼저 골라주세요'}
        </Text>
      </Pressable>
```

**카드 컴포넌트 + 카드/CTA 스타일 (토큰만)** (`analysis/reference.tsx` :183-219, :270-315):
```typescript
function MotionCard({
  motion,
  selected,
  onPress,
}: {
  motion: ReferenceMotion;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={({ pressed }) => [
        styles.card,
        selected && styles.cardSelected,
        pressed && styles.cardPressed,
      ]}
    >
      <View style={styles.cardText}>
        <Text style={styles.cardTitle}>{motion.name}</Text>
        <Text style={styles.cardAthlete}>{motion.athleteName}</Text>
```
```typescript
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  cardSelected: { borderColor: colors.brand, backgroundColor: colors.brandTint },
  ...
  cta: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaDimmed: { opacity: 0.4 },
  ctaText: { ...typography.button, color: colors.textWhite },
```

**busy / notice 상태 + try/catch/finally (로그인·업로드 버튼)** (`auth/login.tsx` :42-43, :53-71):
```typescript
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
```
```typescript
    setNotice(null);
    setBusy(true);
    try {
      // provider 별 차이는 자격증명을 얻는 방법뿐 — 그 뒤(게스트 승계·결과 분기)는
      // socialAuth 안에서 같은 헬퍼를 지나므로 여기서는 outcome 만 본다.
      const { outcome } =
        id === 'apple' ? await signInWithApple() : await signInWithGoogle();
      if (outcome === 'cancelled') return; // 사용자가 닫은 것 — 오류가 아니다
      if (outcome === 'switched') {
        // 게스트 기록이 다른 uid 에 남는다는 사실을 알린 뒤 넘어간다.
        setNotice(authCopy.result.switched);
        return;
      }
      router.replace('/(tabs)');
    } catch {
      setNotice(authCopy.result.failed);
    } finally {
      setBusy(false);
    }
```

**HTTP 클라이언트 — `authedJson` (Bearer idToken · ApiError code 보존) + `uploadToS3` (Content-Type 필수)** (`lib/api.ts` :51-95, :318-343):
```typescript
async function authedJson<T>(
  path: string,
  init: { method: 'GET' | 'POST'; body?: unknown },
): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(
      'EXPO_PUBLIC_API_BASE_URL 미설정. app/.env 확인.',
      0,
      'config_missing',
    );
  }
  const user = auth.currentUser;
  if (!user) throw new ApiError('로그인이 필요합니다.', 0, 'unauthenticated');
  const token = await user.getIdToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: init.method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: init.body == null ? undefined : JSON.stringify(init.body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    // 메시지 포맷 불변 (기존 소비처 무회귀) — 분기용 code 만 추가로 실어 보낸다.
    throw new ApiError(
      `${init.method} ${path} ${res.status}: ${text.slice(0, 200)}`,
      res.status,
      parseErrorCode(text),
    );
  }
  return res.json() as Promise<T>;
}

// POST /upload-url — S3 presigned PUT URL + analysisId 발급.
// 응답을 받은 뒤 앱이: (1) Firestore users/{uid}/analyses/{analysisId} 에
// status='uploading' 문서 생성 (2) uploadUrl 로 영상 PUT.
export function requestUploadUrl(
  req: UploadUrlRequest,
): Promise<UploadUrlResponse> {
  return authedJson<UploadUrlResponse>('/upload-url', {
    method: 'POST',
    body: req,
  });
}
```
```typescript
// S3 presigned PUT 으로 영상 업로드. Content-Type 은 서명에 묶지 않지만
// (upload-url Lambda 가 Params 에서 제외) PUT 헤더로 보내면 S3 가 그 값을 객체
// 메타데이터로 저장한다. 이걸 안 박으면 binary/octet-stream 으로 저장돼서
// 나중에 결과 화면의 expo-video 가 영상으로 인식 못 한다(P0 #6).
const CONTENT_TYPE_BY_FORMAT: Record<VideoFormat, string> = {
  mp4: 'video/mp4',
  mov: 'video/quicktime',
};

export async function uploadToS3(
  uploadUrl: string,
  fileUri: string,
  format: VideoFormat,
): Promise<void> {
  const file = await fetch(fileUri);
  const blob = await file.blob();
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    body: blob,
    headers: { 'Content-Type': CONTENT_TYPE_BY_FORMAT[format] },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`s3 PUT ${res.status}: ${text.slice(0, 200)}`);
  }
}
```

**데이터 소스 훅 — `onSnapshot` 컬렉션 구독 + `normalize` + 에러 문구** (`lib/referenceMotions.ts` :208-242; 단일 doc 판은 :313-359 `useReferenceMotionDoc`):
```typescript
export function useReferenceMotions(): ReferenceMotionsState {
  const [motions, setMotions] = useState<ReferenceMotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const q = query(collection(db, 'reference'));
    const unsub = onSnapshot(
      q,
      (snap) => {
        const list: ReferenceMotion[] = [];
        snap.forEach((d) => {
          const m = normalize(d.id, d.data() as Record<string, unknown>);
          if (m) list.push(m);
        });
        ...
        setMotions(list);
        setLoading(false);
        setError(null);
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[referenceMotions] onSnapshot error', err);
        setLoading(false);
        setError('기준 동작을 불러오지 못했어요. 잠시 후 다시 시도해주세요.');
      },
    );
    return unsub;
  }, []);

  return { motions, loading, error };
}
```

**picker 필수 필드 (새 doc 이 이걸 채우면 무접촉으로 뜬다)** (`lib/referenceMotions.ts` :71-78):
```typescript
// Firestore 문서를 앱 타입으로 정규화. 필수 필드 누락 시 null → 화면에서 무시.
function normalize(id: string, raw: Record<string, unknown>): ReferenceMotion | null {
  const name = typeof raw.name === 'string' ? raw.name : null;
  const athleteName =
    typeof raw.athleteName === 'string' ? raw.athleteName : null;
  const level = raw.level as SkillLevel | undefined;
  if (!name || !athleteName || !level || !(level in LEVEL_ORDER)) return null;
  if (raw.isActive === false) return null;
```

**로그인 상태 훅 (네이티브 모듈 import 0)** (`lib/authUser.ts` :37-51):
```typescript
export function useAuthUser(): AuthUserState {
  const [user, setUser] = useState<User | null>(auth.currentUser);
  // currentUser 가 이미 있으면 복원이 끝난 것이므로 처음부터 ready.
  const [ready, setReady] = useState(!!auth.currentUser);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setReady(true);
    });
    return unsub;
  }, []);

  return { user, isGuest: !!user?.isAnonymous, ready };
}
```

**가이드 화면 — 접힘 목록 + 쉬운 말 항목 데이터** (`help.tsx` :20-31, :109-138):
```typescript
type FaqItem = {
  id: string;
  title: string;
  body: string;
};

// 기대설정 최소 6항목 (UI-SPEC §Copywriting S2). 수치는 보조, 원인·행동이 핵심.
const FAQ_ITEMS: readonly FaqItem[] = [
  {
    id: 'what-measured',
    title: '무엇을 측정하나요?',
    body: '관절 각도와 기준 모션을 비교해 자세를 분석해요. ...',
  },
```
```typescript
function FaqCard({
  item,
  expanded,
  onToggle,
}: {
  item: FaqItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <View style={styles.card}>
      <Pressable
        onPress={onToggle}
        accessibilityRole="button"
        accessibilityLabel={item.title}
        accessibilityState={{ expanded }}
        hitSlop={6}
        style={styles.cardHeader}
      >
        <Text style={styles.cardTitle}>{item.title}</Text>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={20}
          color={colors.textSecondary}
        />
      </Pressable>
      {expanded && <Text style={styles.cardBody}>{item.body}</Text>}
    </View>
  );
}
```

**앱이 분석 doc 을 만드는 형상 — 자기 재현성 `create_analysis_doc` 의 정본** (`analysis/loading.tsx` :159-178):
```typescript
  const now = Date.now();
  await setDoc(doc(db, 'users', uid, 'analyses', analysisId), {
    analysisId,
    mode: input.mode,
    status: 'uploading',
    fileName: input.fileName,
    createdAt: now,
    updatedAt: now,
    ...(input.referenceMotionId
      ? { referenceMotionId: input.referenceMotionId }
      : {}),
    ...(bodyProfile ? { bodyProfile } : {}),
    // Phase 26 (D-09) — 학습활용 opt-in 동의값을 항상 boolean 으로 기록한다
    //   (조건부 spread 아님: 부재≠false 를 없애 동의 증거를 명시적으로 남긴다).
    ...
    learningOptIn: input.learningOptIn,
  });
```

**플래너 메모 (진단):** `supplier/index.tsx` = 두 카드(내 동작 목록 + 올리기 폼 · 내 코드) — 목록은 `useReferenceMotions()` 의 결과를 `supplierUid === user.uid` 로 필터하지 말고(normalize 가 새 필드를 strip) **`query(collection(db,'reference'), where('supplierUid','==',uid))` 전용 훅**을 `lib/supplierMotions.ts` 에 (데이터소스 격리 규율, Pitfall 8). 업로드 = `requestReferenceUploadUrl(form)` (api.ts 에 `authedJson('/reference/upload-url')` 추가) → `uploadToS3(...)`. 웹에서 `file:` URI 대신 `<input type=file>` File 객체 → `expo-image-picker` 웹의 `file` 필드 [CITED RESEARCH Q8] — 여기가 후보 (1) 의 실측 항목이다.

---

### 후보 (1) 웹 분기 `app/src/lib/firebase.web.ts` · `socialAuth.web.ts`

**Analog:** `lib/firebase.ts` :52-68 (역할 일치) · `lib/socialAuth.ts` :56-60, :95-120 (부분 — 웹 경로 0건)

**auth 초기화 — RN persistence, `Platform` 분기 없음** (`firebase.ts` :52-68):
```typescript
function resolveAuth(): Auth {
  if (globalThis.__sunityAuth) return globalThis.__sunityAuth;
  try {
    globalThis.__sunityAuth = initializeAuth(app, {
      persistence: getReactNativePersistence(ReactNativeAsyncStorage),
    });
  } catch {
    // 이미 초기화된 경우 — firebase 내부에 등록된 기존 인스턴스를 재사용.
    globalThis.__sunityAuth = getAuth(app);
  }
  return globalThis.__sunityAuth;
}

const auth: Auth = resolveAuth();
const db: Firestore = getFirestore(app);

export { app, auth, db };
```

**Google 로그인 (네이티브 SDK · outcome 규율)** (`socialAuth.ts` :56-60, :95-120):
```typescript
export type SocialAuthOutcome =
  | 'linked'
  | 'signed_in'
  | 'switched'
  | 'cancelled';
```
```typescript
export async function signInWithGoogle(): Promise<SocialAuthResult> {
  try {
    // iOS 는 항상 true 를 돌려주지만, Android 에서 Play 서비스가 없으면 여기서 걸린다.
    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });

    const response = await GoogleSignin.signIn();

    // v16 부터 취소가 예외가 아니라 type: 'cancelled' 로 온다.
    if (response.type === 'cancelled') {
      return { outcome: 'cancelled', user: null };
    }

    const idToken = response.data?.idToken;
    if (!idToken) {
      throw new Error('Google 로그인에서 idToken 을 받지 못했습니다.');
    }

    return await attachOrSignIn(GoogleAuthProvider.credential(idToken));
  } catch (e) {
    // 구형 경로: 취소가 예외로 오는 경우도 오류로 올리지 않는다.
    if (isErrorWithCode(e) && e.code === statusCodes.SIGN_IN_CANCELLED) {
      return { outcome: 'cancelled', user: null };
    }
    throw e;
  }
}
```

**플래너 메모 (진단):** `socialAuth.web.ts` 는 같은 `SocialAuthOutcome`/`SocialAuthResult` 를 export 하고 `signInWithGoogle` 만 `signInWithPopup(auth, new GoogleAuthProvider())` 로(RESEARCH §D — 리다이렉트 금지), `signInWithApple` 은 throw. `firebase.web.ts` 는 `getAuth(app)` 만(웹 기본 persistence local [CITED]). `.web.ts` 는 `src/lib` 이라 허용 [CITED platform-specific-modules]. 둘 다 **후보 (1) 이 실측에서 살아남을 때만** 만든다.

---

### 후보 (2) `web/supplier.html` (단일 정적 HTML)

**Analog:** `.planning/phases/33-result-trust-recovery/mockups/index.html` (부분 — 운영 HTML 은 리포에 0건, 이 목업이 유일한 CSS 토큰 선례) + `lib/api.ts` 로직을 vanilla 로

**Pretendard 로드 + 브랜드 토큰 `:root`** (`mockups/index.html` :7-9, :113-116, :128):
```html
<!-- Pretendard (design.md §2) — 오프라인이면 시스템 폰트 폴백 -->
<link rel="stylesheet" as="style" crossorigin
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" />
```
```css
:root{
  --brand:#FF4B33;            /* design.md §4 브랜드 (변경 금지) */
  --brand-tint:rgba(255,75,51,.10);
  --brand-tint-2:rgba(255,75,51,.16);
```
```css
  font-family:'Pretendard',-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',system-ui,sans-serif;
```

**카드 · 탭 · 칩 CSS (design.md 카드 15pt)** (:137-139, :161, :172-173):
```css
.tabs button{border:0; border-radius:999px; padding:8px 12px; font-size:13px; font-weight:700;
.tabs button.on{background:var(--brand); color:#fff;}
```
```css
.card{background:var(--card); border:0.9px solid var(--line-2); border-radius:15px; padding:14px; margin:12px 0;}
```
```css
.chip{display:inline-block; font-size:12px; font-weight:800; padding:3px 10px; border-radius:999px;}
.chip.brand{background:var(--brand-tint); color:var(--brand);}
```

**플래너 메모 (진단):** JS 는 `lib/api.ts` :62-82 (`getIdToken` → `fetch` + `Authorization: Bearer`) 와 :334-338 (PUT + `Content-Type`) 를 그대로 vanilla ESM(`firebase/app`·`firebase/auth`·`firebase/firestore` CDN ESM) 으로 옮긴다. 길이 검사는 `<video>` `loadedmetadata` 의 `duration` (A12). 상태는 `onSnapshot(doc(db,'reference',refId))`. 이 후보는 의존성 0 이라 지금 만들 수 있지만 "같은 앱" 문자 그대로는 아니다(RESEARCH §H 판정 기준).

---

### `docs/supplier-guide.md` (신규) · docs 4종 정정

**Analog:** `docs/reference-capture-guide.md` (구조) + `help.tsx` :27-58 (톤)

**구조 어법 — 헤더 인용문 · §0 핵심 원칙 · 표 · 항목** (`reference-capture-guide.md` :1-19, :23-28):
```markdown
# 정은지 기준 모션 촬영 가이드 (Reference Capture Guide)

> Phase 14 SC#3 산출물. 정은지 세션의 권장 촬영 조건을 문서화해 기준 모션 등록 정확도가
> **재현 가능**하도록 한다. 본 가이드는 등록 운영자(belle/촬영 담당)를 위한 것이며, ...

---

## 0. 핵심 원칙 (먼저 읽을 것)

- **단일시점이 v1 baseline 이다.** ...
```
```markdown
## 1. 시점 수 (Views)

| 항목 | v1 권장 | 비고 |
|------|---------|------|
| 기본 시점 | **단일시점 1개** (정면 우선) | 학생 입력과 동일 조건. `captureViews=1` 로 등록. |
```

**정정 대상 원문** (`reference-capture-guide.md` :27, :47-48):
```markdown
| 기본 시점 | **단일시점 1개** (정면 우선) | 학생 입력과 동일 조건. `captureViews=1` 로 등록. |
```
```markdown
- **정면성:** 정면(또는 동작이 가장 잘 드러나는 단일 각도)을 기본으로 한다. 비스듬한 사각(斜角)은
  좌우 occlusion 을 키운다.
```

**쉬운 말 톤 ("~해요", 원인 1줄 + 행동 1줄)** (`help.tsx` :44-47):
```typescript
  {
    id: 'how-to-film',
    title: '어떻게 촬영하면 좋나요?',
    body: '몸 전체가 화면에 잘 들어오는 거리(약 2~3m)에서 정면을 기준으로 촬영해 주세요. 너무 가깝거나 멀면 분석에 실패할 수 있어요.',
  },
```

**contract.md — 엔드포인트 절 어법 + ReferenceMotion 필드 표 + 문구 절** (:50-69 골격 인용 위치, :285-300, :812-819):
```
`ReferenceMotion` (스키마 단일 진실: docs/reference-motions.md §3)
```
```
motionId           string
name               string                 동작명
athleteName        string                 '정은지'
level              'basic'|'intermediate'|'advanced'
...
videoS3Key?        string                 'reference/{motionId}.mp4' — 백엔드 pipeline mode1 비교 영상 서명 URL 발급에 사용
```
```
`ERROR_MESSAGE` (ml/CLAUDE.md = design.md §6 오류 4종 + 비폴 차단 안전망)
no_human            영상에서 사람을 찾지 못했어요. 전신이 보이게 다시 촬영해주세요.
```

**reference-motions.md §3 — 필드 옆 출처 주석 (`// seed` `// reprocess` `// backfill` → `// register` 추가)** (:69-75):
```typescript
  // reprocess_reference_motions_phase4.py (Pod GPU) 산출.
  // Firestore 는 nested array 를 금지하므로 (T, J) 행렬을 flat 으로 저장하고
  // anglesJointKeys 길이로 reshape 한다.
  angles?: number[];            // reprocess — 길이 = anglesFrames * anglesJointKeys.length
  anglesJointKeys?: string[];   // reprocess — 길이 J (보통 8, skeleton.JOINT_KEYS)
  anglesFrames?: number;        // reprocess — T
  referenceKeypointReport?: KeypointReport | null;  // reprocess
```

**ia.md 정정 행 원문** (:189, :191, :200):
```markdown
| AC-VID-002-1 | Pole sports angle guide | 전신 / 폴 전체 / 측면 45° | 완벽해요! 분석을 시작합니다. | AI 분석으로 이동 |
| AC-VID-002-2 | Lighting / distance guide | 밝은 환경 / 2~3m 거리 | 환경이 좋아요. 분석 정확도가 높아집니다. | 촬영 계속 |
| AC-VID-003-1L | Duration check | Fail | 3초 미만 | 영상이 너무 짧아요. 동작 전체가 담긴 영상이 필요해요. | 재업로드 |
```

**README 버킷 명령 (교체-전체 주의)** (`backend/README.md` :78-82, :101-109):
```bash
# 1) Lifecycle (uploads/ 30일 만료 — 비용 관리)
aws s3api put-bucket-lifecycle-configuration \
  --bucket sunity-motion-pilot-videos \
  --lifecycle-configuration '{"Rules":[{"ID":"expire-raw-uploads-30d","Status":"Enabled","Filter":{"Prefix":"uploads/"},"Expiration":{"Days":30}}]}'
```
```bash
aws s3api put-bucket-notification-configuration \
  --bucket sunity-motion-pilot-videos \
  --notification-configuration "{
    \"QueueConfigurations\": [{
      \"QueueArn\": \"$QUEUE_ARN\",
      \"Events\": [\"s3:ObjectCreated:*\"],
      \"Filter\": {\"Key\": {\"FilterRules\": [{\"Name\": \"prefix\", \"Value\": \"uploads/\"}]}}
    }]
  }"
```
(→ RESEARCH 코드 예시 F 의 2항목 판으로 교체 + lifecycle 은 `delete-bucket-lifecycle` 로 "해제됨(2026-09, D-17)" 표기.)

---

## Shared Patterns

### 1. Lambda 인증 → 검증 → 부작용 1 → 응답 (얇은 핸들러)
**Source:** `backend/functions/upload-url/app.py` :33-72 · `sunity_shared/auth.py` :91-104 · `sunity_shared/responses.py` :24-43
**Apply to:** `reference-upload-url/app.py`
```python
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
```
```python
def ok(payload: Any, status: int = 200) -> dict:
    return _resp(status, payload)


def error(code: str, message: str, status: int = 400) -> dict:
    """contract 형태와 동일: { error: { code, message } }."""
    return _resp(status, {"error": {"code": code, "message": message}})


def parse_json_body(event: dict) -> dict:
    """API GW proxy event 의 body(JSON) 파싱. 실패 시 {}."""
```

### 2. uid 화이트리스트 — env 미설정 = 거부
**Source:** `reference-auto-register/app.py` :49-51, :87-99 (위 발췌)
**Apply to:** `reference-upload-url/app.py`(필수) · 미래 공급자 API 전부. `SUPPLIER_UIDS` 는 쉼표 구분 SSM 값 → 순수 파서 `models.py` 에.

### 3. 오류 경계 — `# noqa: BLE001` + `log.exception` + `server_error` 통일
**Source:** `upload-url/app.py` :58-62 · `pipeline/app.py` :10340-10347 · `server.py` :208-215
**Apply to:** 모든 Lambda/Pod 경계. 등록 경로의 `_handle_reference_upload` 는 **예외를 삼키고 doc 만** 갱신(메시지 소비).

### 4. 구조화 로그 key=value
**Source:** `upload-url/app.py` :25-26, :64 · `pipeline/app.py` :127-128, :10135
```python
log = logging.getLogger()
log.setLevel(logging.INFO)
...
log.info("upload-url ok uid=%s analysis_id=%s mode=%s", uid, analysis_id, req.mode)
```
**Apply to:** 신설 Python 전부. 비밀값·env 원문 로그 금지(`server.py` :303 어법).

### 5. Firestore ADD-only writer 골격 + nested-array 검증
**Source:** `firestore_admin.py` :2196-2249 · :46-102 (위 발췌)
**Apply to:** `create_reference_registration` · `set_reference_angles` · `set_reference_registration_status` · `set_reference_self_score` · `create_analysis_doc`. 규칙: 빈 id `ValueError` → 필수 키 → `_validate_flat_dict_no_nested_array(payload, path=...)` → `now_ms = int(time.time() * 1000)` → `*UpdatedAt` → `set(merge=True)` (선작성만 `create()`) → `log.info(... ok ...)`.

### 6. 계약 3벌 lockstep + 별도 enum
**Source:** `models.py` :1-5, :746-768 · `analysis.ts` :94-109, :2220-2227 · `contract.md` :243-277, :800-819 · `reference-motions.md` :43-88
**Apply to:** `REGISTRATION_STATUS_*` · `REGISTRATION_ERROR_*` · `ReferenceMotion` 등록 필드 · 새 엔드포인트 절. `AnalysisStatus`/`PIPELINE_SEQUENCE` 무접촉.

### 7. 순수 판정 함수 + 합성 입력 강제
**Source:** `hold_height.py` :20-25 (fail-closed 선언) · `validation.py` :3 · `test_hold_height.py` :34-57 · `test_rtmw_engine.py` :48-57
**Apply to:** `registration_checks.py` · `validation.validate_reference_upload_request` · `s3keys.parse_reference_key`. numpy/stdlib 만, Pod·Firestore·boto3 import 0.

### 8. 테스트 모듈 로딩 — sys.path 주입 + env monkeypatch + 모듈 캐시 리셋
**Source:** `tests/conftest.py` :9-17 · `test_reference_auto_register_handler.py` :33-46 · `test_pipeline_dispatch.py` :17-42 · `test_runpod_server.py` :16-34
**Apply to:** 신설 테스트 6종. 외부 호출은 전부 `monkeypatch.setattr(module, "name", fake)`; `firestore_admin._doc` 은 `_FakeDoc`/`_FakeDocStore`.

### 9. RunPod 위임 HTTP (urllib · UA · 토큰 헤더 · 10s)
**Source:** `pipeline/app.py` :210-236 (위 발췌) · `podwatch.yaml` :158-170 (`probe`)
**Apply to:** `_handle_reference_upload` 위임 · `requeue_reference_registrations.py` · Pod `/health` 판정.

### 10. 앱 — 테마 토큰만 · 접근성 props · 인라인 한국어 오류 상태 · 데이터소스 훅 격리
**Source:** `profile.tsx` :399-416 · `reference.tsx` :112-120, :165-178 · `login.tsx` :42-71 · `referenceMotions.ts` :1-10, :208-242 · `authUser.ts` :1-12
**Apply to:** `supplier/index.tsx` · `supplier/guide.tsx` · `profile.tsx` 한 줄. `colors/layout/radius/spacing/typography` 외 리터럴 색·간격 금지(`app/CLAUDE.md`). 화면은 `firebase/firestore` 를 직접 부르지 않고 `lib/*.ts` 훅 경유.

### 11. 앱 — 검증은 종류만 반환, 문구는 단일점 + exhaustive 게이트
**Source:** `analyze.tsx` :204-214 · `pickerFailure.ts` :1-18, :125-130
**Apply to:** `validate()` duration · `tooShort`/`tooLong`. (등록 실패 4형 문구도 같은 규율 — 백엔드 `REGISTRATION_ERROR_MESSAGE` 가 단일점, 페이지는 code→문구 변환만.)

### 12. 주석 어법 — 왜(why) 한국어 + 출처 인용 (`design.md §5-4` · `contract.md §2` · `belle 09-26` · `quick-…`)
**Source:** 위 모든 발췌의 docstring/주석
**Apply to:** 신설 파일 전부. 새 파일 헤더 docstring 에 phase 라벨(`Phase 38 D-05`) 과 계약 절 인용.

---

## No Analog Found

리포에 같은 역할·같은 흐름의 코드가 없어 **RESEARCH 의 설계(§A~§F) 와 [CITED] 문서를 따라야 하는** 것:

| File / Piece | Role | Data Flow | Reason |
|---|---|---|---|
| `rtmw_engine.estimate_with_person_counts` | adapter | transform | 엔진이 `kps_batch[0]` 로 N 을 **버린다**(:274-276). 프레임별 사람 수를 돌려주는 API 가 어디에도 없다. `_build_pose_frames` 의 `(list, int)` local-return 형이 유일한 형태 선례 |
| `socialAuth.web.ts` (`signInWithPopup`) | service | request-response | 웹 로그인 경로 0건. `socialAuth.ts` 는 네이티브 SDK 전용(`GoogleSignin` 웹은 throw [확인 RESEARCH Q7]), `firebase.ts` 에 `Platform` 분기 없음. 팝업이 폰 브라우저에서 되는지 [미확인] — RESEARCH §H ③ |
| `web/supplier.html` | component (정적) | CRUD | 운영 HTML 0건. `.planning/.../mockups/index.html` 은 CSS 토큰 선례일 뿐 인증·업로드 로직이 없다 |
| `firestore_admin.create_reference_registration` 의 `doc.create()` | repository | CRUD | 리포의 writer 는 전부 `set(merge=True)`; `create()` 호출 0건. 가장 가까운 것은 `set_reference_motion_with_gemini` 의 `snap.exists` 분기(:2402-2404) — 원자적이지 않다 |
| 강사 코드 (`supplierCode`) | — | — | `supplier|instructor|studioCode|referral` 0건 [확인 RESEARCH Q10]. 표시만이므로 `profile.tsx` `InfoRow` 로 충분 |

---

## 관측 — 플래너가 알아야 할 코드 사실 (이 세션 [확인], 진단은 표시)

1. **Pod-expected SSM 파라미터 이름이 갈린다.** 쓰기 측 `start_server.sh:95` 와 `pod_teardown.py:125` 는 `/sunity/motion/runpod-pod-expected` 에 `up`/`down` 을 쓴다. 읽기 측 `podwatch.yaml:35` 의 기본값은 `/sunity/motion/pod-expected` 다. SSM 에는 두 이름이 **둘 다** 있다(RESEARCH Q1 목록: `pod-expected`, `runpod-pod-expected`). 배포된 podwatch 스택이 `PodExpectedParam` 을 override 했는지는 [미확인]. → (진단) 등록 경로의 Pod 부재 판정은 **쓰기 측이 실제로 갱신하는 `runpod-pod-expected`** 를 읽어야 값이 살아 있다. 플랜에 `aws ssm get-parameter` 두 이름 실측 task 를 넣을 것.
2. `_KEYPOINT_NAMES` 는 12개이고 손은 `left_hand`/`right_hand`(COCO `wrist` 매핑, `keypoint_frame.py:60-61`). `skeleton.JOINT_LABEL_KO` 는 각도 관절 8개(팔꿈치·어깨·고관절·무릎)만 — 발목·손 라벨이 없다. 저신뢰 부위 목록 문구에는 12개 라벨 dict 신설 필요.
3. `hold_height._frame_series` 는 `w0 < MIN_STAND_FRAMES(3)` 이면 None(:107) — 서 있는 구간이 3프레임 미만이면 판정 자체가 불가. 등록 영상 실효 fps ~10 이면 "첫 1.0초"(A5) = 약 10프레임으로 충분하다 [확인 상수, 진단은 A5].
4. `pipeline/app.py` 의 `ssm:GetParameter` 정책은 `FirebaseSaParam` ARN 하나뿐(`template.yaml:386-388`). Lambda 에서 pod-expected 를 읽으려면 Statement 추가가 CFN 변경에 포함돼야 한다.
5. `test_runpod_server.py` 의 TestClient 는 background task 를 **동기 실행**한다(:109 주석) — `/register-reference` 테스트도 같은 방식으로 호출 인자를 단언할 수 있다.
6. `help.tsx:46` 에 "약 2~3m ... 정면을 기준으로" 문구가 있다 — CONTEXT 정정 5곳 밖이지만 RESEARCH 의 grep 게이트(`45°|2~3m|정면 우선`)에 걸린다. 게이트 패턴이 `2~3m` 을 포함하는 한 이 줄도 정정하거나 게이트 패턴을 좁혀야 한다.
7. `referenceMotions.ts normalize()` (:72-78) 는 등록 필드를 strip 한다 — picker 는 무접촉(D-19 충족)이지만, 공급자 페이지가 `registrationStatus`/`selfScore` 를 보려면 `useReferenceMotions()` 를 재사용할 수 없다(별도 훅 필요 — 위 supplier/index 메모).
8. `e2e_app_path.py:110` 은 완료 상태를 `("completed","failed","done","error")` 로 폴링한다 — 계약상 종료 status 는 `done`/`failed` 뿐(`models.py:703-704`). requeue/E2E 스크립트를 새로 쓸 때 이 4값 목록을 복사하지 말 것.

---

## Metadata

**Analog search scope:** `backend/functions/{upload-url,reference-auto-register,pipeline}/`, `backend/runpod_inference/`, `backend/shared/python/sunity_shared/{s3keys,validation,models,firestore_admin,responses,auth,events}.py`, `backend/shared/python/sunity_shared/analysis/{hold_height,assemble,keypoint_frame,skeleton,frame_extractor,interfaces,pose_frame}.py`, `analysis/pose_engines/rtmw/rtmw_engine.py`, `backend/scripts/{e2e_app_path,intake_clips,extract_reference_angles,pod_teardown}.py`, `backend/infra/podwatch.yaml`, `backend/template.yaml`, `backend/README.md`, `backend/tests/{conftest,test_s3keys,test_validation,test_pipeline_dispatch,test_reference_auto_register_handler,test_hold_height,test_rtmw_engine,test_analysis_provenance,test_runpod_server,test_intake_clips,test_auth_env}.py`, `app/src/app/{_layout,help}.tsx`, `app/src/app/(tabs)/{analyze,profile}.tsx`, `app/src/app/analysis/{loading,reference}.tsx`, `app/src/app/auth/login.tsx`, `app/src/lib/{api,referenceMotions,firebase,authUser,socialAuth,pickerFailure}.ts`, `app/src/types/analysis.ts`, `app/src/constants/motionThumbs.ts`, `app/scripts/seed-reference-motions.mjs`, `docs/{contract,ia,reference-capture-guide,reference-motions}.md`, `firestore.rules`, `.planning/phases/33-result-trust-recovery/mockups/index.html`
**Files scanned:** 58 (읽은 파일 52 + grep 전용 6)
**Standalone HTML 검색:** `find . -name "*.html"` (node_modules/.venv 제외) → 운영 코드 0건, 기획 목업 4건(`.planning/quick/260816-ill2…/board.html`, `phases/32…/samples/illust_gallery.html`, `phases/32…/mockups/index.html`, `phases/33…/mockups/index.html`). `.planning/quick/260925-nnt-three-fixes/` 에 `pick.html` 은 **없다**(디렉터리 실측: HANDOFF/PLAN/PREDICTION/SUMMARY + e2e/ + scripts/).
**Pattern extraction date:** 2026-09-26
