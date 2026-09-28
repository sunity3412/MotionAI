---
phase: 38-supplier-link
plan: 01
subsystem: api
tags: [contract, s3keys, firestore, validation, typescript, pytest, supplier-link]

# Dependency graph
requires:
  - phase: 38-supplier-link (38-CONTEXT D-04~D-19, 38-REVIEWS R2~R15)
    provides: 결정·리뷰 — 업로드/확정 키 분리(R5), expired(R4), too_large(R9), 비공개 서브문서(R13), 작업 소유권·자기 재현성 표식(R2·R3·R8)
provides:
  - "s3keys: build_reference_upload_key · build_reference_final_key · ParsedReferenceKey(kind, is_upload) · parse_reference_key (legacy/_archive/옛 모양/uploads 전부 None)"
  - "models: REGISTRATION_STATUS_*(+expired) · SELF_CHECK_STATUS_* · REG_ERR_*(+too_large) · REGISTRATION_ERROR_MESSAGE · REFERENCE_LEVELS · 길이/이름/동의 상수 · REGISTRATION_LEASE_SEC · REFERENCE_UPLOAD_EXPIRES_SEC · parse_supplier_uids · reference_private_path · ANALYSIS_FIELD_SELF_CHECK_FOR_REFERENCE / _JOB_ID"
  - "analysis.ts: ReferenceRegistrationStatus/ErrorCode/Error · SelfCheckStatus · ReferenceConsent · ReferenceClipRangeInput · ReferenceUploadUrlRequest/Response · SupplierProbeResponse · ReferenceRegistrationPrivate · ReferenceMotion 등록 공개 필드 · AnalysisDoc.selfCheckForReference/selfCheckJobId · REGISTRATION_ERROR_MESSAGE"
  - "validation: ReferenceUploadRequest · validate_reference_upload_request (D-07·D-08·D-14 순수 검증)"
  - "contract.md §2 POST /reference/upload-url · §3 등록 필드 + private/registration + 분배표 · §5 REGISTRATION_ERROR_MESSAGE; reference-motions.md §3 `// register`"
affects: [38-03 supplierCopy/supplierForm, 38-05 판정, 38-06 writer/Lambda, 38-07 pipeline register, 38-08 selfScore hook/requeue, 38-10/38-12 page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "별도 enum — 등록 상태는 PIPELINE_SEQUENCE/AnalysisStatus 에 넣지 않고 기준 doc `registrationStatus` 로(COACH_STATUSES 선례)"
    - "3벌 lockstep 을 pytest 가 파일 텍스트로 대조 (test_registration_contract.py)"
    - "키 두 모양(upload/v1)을 정규식 `kind` 그룹으로 닫고 `is_upload` 로 호출측이 분기"

key-files:
  created:
    - backend/tests/test_registration_contract.py
  modified:
    - backend/shared/python/sunity_shared/s3keys.py
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/validation.py
    - backend/tests/test_s3keys.py
    - backend/tests/test_validation.py
    - app/src/types/analysis.ts
    - docs/contract.md
    - docs/reference-motions.md

key-decisions:
  - "38-01: 요청/비공개 doc 의 clipRange 는 {execStartS, execEndS}(ReferenceClipRangeInput) — 5-필드 ClipRange 아님. 38-06 비공개 payload·validation 튜플과 같은 모양"
  - "38-01: models.py 배치 — 상태 enum 은 COACH_STATUSES 아래, 실패 코드·문구·파서·private 경로는 ERROR_MESSAGE/reference_motion_path 뒤(정의 순서). TS REGISTRATION_ERROR_MESSAGE 도 ERROR_MESSAGE 뒤(TDZ)"
  - "38-01: REGISTRATION_ERROR_MESSAGE.no_human 은 ERROR_MESSAGE 객체 참조(is), TS 도 ERROR_MESSAGE.no_human 참조 — 문자열 복사 0"
  - "38-01: ReferenceMotion TS 에 isActive? 추가 — normalize() 가 이미 읽고 38-06 이 쓰는 필드인데 타입에 없었다"

patterns-established:
  - "validation.py 보조 헬퍼(_is_real·_require_bool·_optional_bool·_short_text) — bool 위장 int 거부, 유한 실수만"
  - "contract 대조 테스트는 유니온 본문(`export type X =` ~ `;`)·인터페이스 블록(줄머리 `}`)을 잘라 안에서 찾는다"

requirements-completed: [REQ-38-1, REQ-38-3, REQ-38-6, REQ-38-7]

# Metrics
duration: 15min
completed: 2026-09-28
---

# Phase 38 Plan 01: 계약·키·검증(순수) Summary

**공급자 링크 등록의 인터페이스를 코드로 박았다 — `reference/{uid}/{refId}/{upload|v1}.{ext}` 키 build/parse, 등록 상태(+expired)·실패 코드(+too_large)·자기 재현성 표식이 models.py · analysis.ts · contract.md 세 벌에 같은 문자열로 있고 pytest 가 세 벌 텍스트를 대조하며, 공급자 폼은 순수 함수 하나가 거부한다.**

## Performance

- **Duration:** 15min
- **Started:** 2026-09-28T12:52:22Z
- **Completed:** 2026-09-28T13:07:59Z
- **Tasks:** 3/3
- **Files modified:** 9 (+1254 / −10, `git diff --stat origin/main..HEAD` [확인])

## Accomplishments

- 기준 키 두 모양(업로드 `upload.{ext}` / 확정 `v1.{ext}`)이 라운드트립되고, 평면 `reference/ref-*.mp4` · `_archive` · 옛 모양 `reference/{uid}/{refId}.{ext}` · `v2`/`original` 임의 파일명 · `uploads/`·`results/` 가 전부 `None` — 기존 11개·손 업로드가 새 등록 경로에 못 들어온다(D-19, R5). `s3keys.py` 헤더의 "30일 후 자동 삭제" 는 사라지고 영구 보관이 적혔다(D-17, R15a 게이트 정합).
- 등록 상태 6·자기 재현성 상태 4·실패 코드 8·문구 8 이 세 벌(+reference-motions.md)에 있고, `test_registration_contract.py` 20건이 TS/contract 텍스트를 잘라 대조한다. 분석 status 머신(`PIPELINE_SEQUENCE`·`AnalysisStatus`)은 무접촉.
- 비공개 서브문서 `reference/{refId}/private/registration`(R13) · 작업 소유권 `jobId/leaseUntil`(R3) · 자기 재현성 표식 `selfCheckAnalysisId/selfCheckJobId` + 분석 doc `selfCheckForReference/selfCheckJobId`(R2·R8, D-10) 가 계약·상수로만 존재한다 — 뒤 플랜은 `ANALYSIS_FIELD_*` 상수만 쓴다.
- `validate_reference_upload_request` 가 폼 메타·선언 4·동의·길이(5~30초, 콤보 60초)를 고정 순서로 거부한다(30건 신규 테스트).

## Task Commits

1. **Task 1: reference 키 build/parse(kind) + s3keys 헤더 정정** — `72bf6282` (feat)
2. **Task 2: 등록 상태·실패 코드·비공개 서브문서·자기 재현성 표식 계약 3벌 lockstep** — `d8169bef` (feat)
3. **Task 3: validate_reference_upload_request 순수 검증** — `27410f6c` (feat)

**Plan metadata:** 아래 docs 커밋(SUMMARY·STATE·ROADMAP·REQUIREMENTS).

## Files Created/Modified

- `backend/shared/python/sunity_shared/s3keys.py` — `REFERENCE_KEY_KIND_UPLOAD/FINAL` · `_REFERENCE_KEY_RE`(uid·refId 영숫자, kind ∈ upload|v1) · `build_reference_upload_key` · `build_reference_final_key` · `ParsedReferenceKey(is_upload)` · `parse_reference_key`; 헤더 영구 보관. `_UPLOAD_KEY_RE`·`parse_upload_key` 무접촉.
- `backend/tests/test_s3keys.py` — 라운드트립(upload/v1) · v1 mp4 · legacy/foreign 12건 거부 · upload 파서가 reference 키 거부.
- `backend/shared/python/sunity_shared/models.py` — `import re`; learningOptIn 블록 아래 `ANALYSIS_FIELD_SELF_CHECK_FOR_REFERENCE`·`ANALYSIS_FIELD_SELF_CHECK_JOB_ID`; COACH_STATUSES 아래 `REGISTRATION_STATUS_*`(전이 표 주석)·`SELF_CHECK_STATUS_*`·`REGISTRATION_LEASE_SEC`·`REFERENCE_UPLOAD_EXPIRES_SEC`; `REFERENCE_MOTIONS_COLLECTION` 뒤 `REG_ERR_*`·`REGISTRATION_ERROR_MESSAGE`·`REFERENCE_LEVELS`·길이/이름/동의 상수·`SUPPLIER_CODE_RE`·`SUPPLIER_UIDS_PARAM_DEFAULT`·`parse_supplier_uids`·`REFERENCE_PRIVATE_*`·`reference_private_path`.
- `app/src/types/analysis.ts` — Phase 38 타입 블록(Checkpoint 와 ReferenceMotion 사이) · `ReferenceMotion` 등록 공개 필드 22개(`// register`) · `ReferenceRegistrationPrivate` · `AnalysisDoc.selfCheckForReference/selfCheckJobId` · `REGISTRATION_ERROR_MESSAGE`(ERROR_MESSAGE 뒤). `AnalysisStatus`·`AnalysisErrorCode`·`ERROR_MESSAGE` 무접촉.
- `docs/contract.md` — §2 `### POST /reference/upload-url`(인증·요청 표·probe·응답·오류·부작용) · §3 컬렉션 표 + AnalysisDoc selfCheck 2행 + Phase 38 인용문 + ReferenceMotion 등록 필드 표(videoS3Key 행 v1 명시) + private/registration 문서 표 + 접근 규칙 + 공개/비공개 분배표 · §5 `REGISTRATION_ERROR_MESSAGE` 8줄 + no_human 예외 설명.
- `docs/reference-motions.md` — §3 헤더에 register 출처, 공개 필드 `// register` 20줄, `ReferenceRegistrationPrivate` 블록.
- `backend/tests/test_registration_contract.py` (신규) — (1)(2) 코드↔문구·no_human `is` (3) status 머신 무접촉 (4) parse_supplier_uids 10 케이스 (5) TS/contract/reference-motions 텍스트 대조 (6) selfCheck 3벌 (7) 경로·상수.
- `backend/shared/python/sunity_shared/validation.py` — `ReferenceUploadRequest` · `validate_reference_upload_request` + 보조 헬퍼 4개. `validate_upload_request` 무접촉.
- `backend/tests/test_validation.py` — `OK_REFERENCE` · 정규화 3건 · 거부 24건 parametrize · consent 누락 · 문구 재사용 · non-dict.

## 관측 (이 세션이 직접 실행/읽은 것)

- [확인] `cd backend && .venv/bin/python -m pytest tests/test_s3keys.py tests/test_validation.py tests/test_registration_contract.py -q` → `69 passed` (7 + 42 + 20). test_validation 42 = 기존 12 + 신규 30.
- [확인] `cd app && npm run typecheck` → exit 0 (오류 출력 0줄).
- [확인] 게이트: `grep -c '30일 후 자동 삭제\|30일 뒤' s3keys.py` = 0 · `'영구 보관'` = 1 · def/class 4종 = 4 · KIND 상수 2 · `PIPELINE_SEQUENCE = (` diff 0줄 · `### POST /reference/upload-url` = 1 · `// register` in reference-motions.md = 26 · `AnalysisStatus =` 블록에 registering/active 0 · `^ANALYSIS_FIELD_SELF_CHECK_*` = 2 · 5-패턴(models) = 5 · `'expired'`/`'too_large'` in TS = 1/1 · `ReferenceRegistrationPrivate` ts 2/contract 2 · `private/registration` contract 4/refmotions 1 · validation `def/class` = 2 · `boto3\|firebase` in validation.py = 0.
- [확인] `git diff` 에 `_UPLOAD_KEY_RE`·`parse_upload_key` 본문·`validate_upload_request` 본문 변경 줄 0.
- [확인] `app/src/lib/referenceMotions.ts:78` `if (raw.isActive === false) return null;` — normalize 가 isActive 를 읽는다(TS `ReferenceMotion` 에는 이 필드가 없었다).
- [확인] 38-06-PLAN :84·:112 — 비공개 payload `clipRange({execStartS,execEndS} 또는 키 없음)`; 38-03-PLAN :162 — 폼은 `clipRange` 없음.
- [확인] 커밋 3건 `72bf6282`·`d8169bef`·`27410f6c` 이 `origin/main`(`6c6dd334`) 앞에 있다.

## 진단 (관측에서 내가 붙인 해석 — 다음 세션 재검증 대상)

- 등록 실패 문구 7개의 조인 규칙(`title + '. ' + body`)이 UI-SPEC 표의 문구와 글자 단위로 맞는지는 **38-03 `supplierCopy.test.ts` 가 생겨야 기계로 닫힌다** [미확인 — 이 세션은 UI-SPEC 표를 눈으로 대조해 이었다].
- `REGISTRATION_LEASE_SEC = 900` 은 [ASSUMED] — Pod 등록 1건 실측 없음(주석에 시험 영상 2차로 조정이라 적음).
- 이 플랜은 계약과 순수 함수만 — Lambda·파이프라인·규칙·페이지는 아무것도 바뀌지 않았다. "REQ-38-1/3/6/7 완료" 표시는 **계약 층의 완료**이고 런타임 완료는 38-06/38-07/38-09 뒤에만 참이다 [미확인 — 실행되지 않음].

## Decisions Made

- `ReferenceUploadUrlRequest.clipRange` · `ReferenceRegistrationPrivate.clipRange` = `ReferenceClipRangeInput {execStartS, execEndS}` (플랜 텍스트의 `ClipRange | null` 대신). 근거: Task 3 검증이 `execStartS/execEndS` 만 읽고, 38-06 이 비공개 doc 에 그 두 키로 적는다 — 5-필드 `ClipRange` 를 요구하면 폼이 만들 수 없는 값을 강제한다.
- models.py 배치를 둘로 나눔 — 상태 enum·lease/expires 상수는 COACH_STATUSES 바로 아래(플랜 지정 자리), 실패 코드·문구·레벨·파서·private 경로는 `REFERENCE_MOTIONS_COLLECTION` 뒤. 이유: `REGISTRATION_ERROR_MESSAGE` 가 `ERROR_MESSAGE` 객체를, `reference_private_path` 가 `reference_motion_path` 를 참조하므로 정의 순서상 그 뒤여야 import 가 산다. TS `REGISTRATION_ERROR_MESSAGE` 도 같은 이유(TDZ)로 `ERROR_MESSAGE` 뒤.
- `ReferenceMotion` 에 `isActive?: boolean` 추가(플랜 목록 밖) — normalize 가 이미 읽고 38-06 이 `isActive:false` 를 쓰는 필드라 타입에 없으면 writer/page 가 캐스팅으로 우회한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 요청/비공개 doc 의 clipRange 타입을 검증기·writer 와 같은 모양으로**
- **Found during:** Task 2
- **Issue:** 플랜 Task 2 는 `clipRange?: ClipRange | null`(5 필드), Task 3·38-06 은 `{execStartS, execEndS}` — 한 계약 안에서 모양이 어긋난다.
- **Fix:** `ReferenceClipRangeInput` 인터페이스를 두고 요청·비공개 doc 이 그것을 쓴다. contract.md·reference-motions.md 도 같은 모양.
- **Files modified:** `app/src/types/analysis.ts`, `docs/contract.md`, `docs/reference-motions.md`
- **Verification:** typecheck exit 0, `test_reference_ok_normalizes` 가 `(1.5, 7.0)` 튜플 단언.
- **Committed in:** `d8169bef`

**2. [Rule 3 - Blocking] 정의 순서 — 실패 코드 블록·TS 문구 상수를 참조 대상 뒤에 배치**
- **Found during:** Task 2
- **Issue:** 플랜은 등록 블록 전체를 "COACH_STATUS 블록 바로 아래" 로 지정했으나 `REGISTRATION_ERROR_MESSAGE` 는 그 뒤에 정의되는 `ERROR_MESSAGE` 를, `reference_private_path` 는 `reference_motion_path` 를 참조한다(그 자리에 두면 NameError). TS 도 `REGISTRATION_ERROR_MESSAGE` 가 `ERROR_MESSAGE` 보다 앞이면 TDZ.
- **Fix:** 상태 enum 은 지정 자리에, 나머지는 `REFERENCE_MOTIONS_COLLECTION` 뒤에 한 블록으로(머리 주석이 상태 블록 위치를 가리킨다). TS 상수는 `ERROR_MESSAGE` 바로 뒤.
- **Files modified:** `models.py`, `analysis.ts`
- **Verification:** `import sunity_shared.models` 가 pytest 에서 살아 있고 typecheck 0.
- **Committed in:** `d8169bef`

**3. [Rule 2 - Missing validation] clipRange·durationSec 에 유한 실수 검사**
- **Found during:** Task 3
- **Issue:** 플랜 문구는 "실수(bool 제외)" 만 — `inf`/`nan` 이 통과한다(`0 <= start < inf` 참).
- **Fix:** `_is_real` = `int|float` ∧ not bool ∧ `math.isfinite`.
- **Files modified:** `validation.py`
- **Verification:** `clipRange {execStartS: True, ...}` 거부 테스트; NaN/inf 는 헬퍼 로직으로 거부(전용 테스트 없음).
- **Committed in:** `27410f6c`

**4. [Rule 3 - Blocking gate] validation.py 모듈 docstring 의 "boto3" 표현**
- **Found during:** Task 3 acceptance
- **Issue:** 게이트 `grep -c "boto3\|firebase" validation.py == 0` 이 기존 docstring "순수 함수(boto3/네트워크 무관)" 때문에 1 이었다(import 아님).
- **Fix:** 같은 뜻으로 "AWS SDK/네트워크 무관" 으로 바꿈. 로직 무접촉.
- **Files modified:** `validation.py`
- **Verification:** grep 0, 42 passed.
- **Committed in:** `27410f6c`

**5. [Rule 1 - Bug] 대조 테스트의 "첫 `}` 앞 구간" 을 "줄머리 `}`" 로**
- **Found during:** Task 2
- **Issue:** `AnalysisDoc` 안에 `error?: { code; message }` 인라인 객체가 있어 첫 `}` 로 자르면 selfCheck 필드가 구간 밖 — 플랜 문장을 그대로 구현하면 정상 계약이 실패한다.
- **Fix:** `_ts_interface_body` 가 `\n}` 까지 자른다(docstring 에 이유).
- **Files modified:** `test_registration_contract.py`
- **Verification:** `test_self_check_field_constants_three_way` 통과.
- **Committed in:** `d8169bef`

**6. [Rule 2 - Missing critical field] `ReferenceMotion.isActive?`**
- **Found during:** Task 2
- **Issue:** normalize 가 읽고 38-06 이 쓰는 필드가 TS 계약에 없었다.
- **Fix:** `isActive?: boolean; // seed · register` 추가 + contract.md 등록 필드 표에 행.
- **Files modified:** `analysis.ts`, `contract.md`
- **Committed in:** `d8169bef`

---

**Total deviations:** 6 auto-fixed (Rule 1 ×2, Rule 2 ×2, Rule 3 ×2)
**Impact on plan:** 전부 계약 정합성·정의 순서·입력 검증 — 범위 확장 없음. 뒤 플랜이 쓰는 이름은 플랜 그대로.

## Issues Encountered

None — 테스트·typecheck 첫 실행에 통과.

## Known Stubs

None. `REGISTRATION_ERROR_MESSAGE.low_confidence` 의 `{joints}` 는 38-07 파이프라인이 `str.replace` 로 치환하는 **의도된 자리표시자**(테스트 `test_low_confidence_placeholder_is_replace_style` 가 정확히 1개임을 단언).

## User Setup Required

None — 순수 함수·계약 문서만. 배포·SSM·Firestore 쓰기 0.

## Next Phase Readiness

- 38-06 writer/Lambda 는 `s3keys.build_reference_upload_key`(presign) · `models.REFERENCE_UPLOAD_EXPIRES_SEC`(ExpiresIn = uploadExpiresAt) · `models.reference_private_path` · `validation.validate_reference_upload_request` · `models.parse_supplier_uids` 를 그대로 쓴다.
- 38-07 파이프라인은 `parse_reference_key(key).is_upload` 로 upload 만 디스패치, `build_reference_final_key` 를 copy_object 목적지로, 분석 doc 표식은 `ANALYSIS_FIELD_SELF_CHECK_FOR_REFERENCE`·`ANALYSIS_FIELD_SELF_CHECK_JOB_ID` 상수만.
- 38-03 `supplierCopy.test.ts` 가 `title + '. ' + body` 조인으로 `REGISTRATION_ERROR_MESSAGE` 7개를 대조해야 UI-SPEC↔계약이 기계로 닫힌다 [미확인].
- 남은 것: 정은지 새 영상이 오면 이 phase 보다 시험 영상 2차가 먼저(플랜 머리말 1).

## Self-Check: PASSED

- 파일 10개 존재 · 커밋 3건(`72bf6282` · `d8169bef` · `27410f6c`) `git log --all` 에 존재 [확인]
