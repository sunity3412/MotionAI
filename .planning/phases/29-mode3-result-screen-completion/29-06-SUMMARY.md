---
phase: 29-mode3-result-screen-completion
plan: 06
subsystem: backend-api, app-result-screen
tags: [d1, playback-url, presigned-ttl, mode1, security-guard]
requires:
  - "29-04 (wave 3 의존 — 결과 화면 구조)"
provides:
  - "POST /playback-url referenceMotionId 재서명 변형 (가드 4종)"
  - "result.tsx mode1 rightUrl 재발급 훅 (freshRefUrl)"
  - "contract.md §2 POST /playback-url 절 (신설)"
affects:
  - "29-08 (HUMAN-UAT — 옛 doc 비교영상 재생 실기기 확인 적립)"
tech-stack:
  added: []
  patterns:
    - "reference 재서명 = Firestore doc videoS3Key 화이트리스트 경유만 (클라이언트 키 직접 수용 0)"
    - "가드 실패 전부 동일 404 — 숨김 doc 존재 leak 0"
key-files:
  created:
    - backend/tests/test_playback_url_reference.py
  modified:
    - backend/functions/playback-url/app.py
    - backend/template.yaml
    - app/src/lib/api.ts
    - app/src/app/analysis/result.tsx
    - docs/contract.md
decisions:
  - "D1 근본 원인 = presigned 7일 TTL 만료 (실측 확정, RESEARCH Pitfall 4 가설 1 적중)"
  - "fix = referenceMotionId 재발급 경로 (TTL 연장 금지 유지 — _PLAYBACK_EXPIRES diff 0)"
  - "requestReferencePlaybackUrl 신설 (기존 requestPlaybackUrl 시그니처 불변 쪽 선택)"
metrics:
  duration: "~25min (진단 포함, sam build 병행)"
  completed: "2026-07-16"
  tasks: 2
  tests: "11 신규 PASS / typecheck 0 err"
---

# Phase 29 Plan 06: D1 진단·fix — Mode1 비교영상 presigned TTL 재발급 Summary

**One-liner:** D1(Mode1 정은지 비교영상 안 뜸)의 근본 원인을 presigned 7일 TTL 만료로 실측 확정하고, /playback-url 에 referenceMotionId 재서명 변형(존재·isActive·videoS3Key·reference/ prefix 가드 4종, 실패 시 동일 404)을 신설 + result.tsx mode1 재발급 훅으로 해소.

## Task 1 — D1 재현·규명 (진단 증거)

**근본 원인 확정: presigned URL 7일 TTL 만료 (RESEARCH Pitfall 4 가설 1). "추정" 아님 — 아래 실측.**

진단 방법: Firebase Admin(로컬 스크립트, firebase-sa.json) 으로 Firestore 원격 조회 + S3 URL 검사. 코드 diff 0 (진단 전용). presigned URL 전문은 어디에도 기록하지 않음 (서명시각·만료초·상태코드만).

| 검사 | 대상 | 실측 결과 |
|------|------|-----------|
| 1. TTL 분리 (a) | 최신 mode1 done doc (age **8.1일**, ref-power-spin) | referenceVideoUrl GET → **403 AccessDenied "Request has expired"** (서명 20260708T130939Z + 604800s = 2026-07-15 만료) |
| 1. TTL 분리 (b) | 최구 mode1 done doc (createdAt 결손 → age 표기 20650일) | referenceVideoUrl GET → **403 AccessDenied "Request has expired"** (서명 20260630T063339Z) |
| 1. TTL 분리 (대조군) | 동일 S3 키 `reference/ref-power-spin.mp4` 를 **신규 서명** | GET(Range 0-0) → **206, content-type video/mp4** — 객체 정상·재생 가능. 죽은 것은 서명뿐 |
| 2. refMotion 폴백 | reference 컬렉션 **11 doc 전수** `videoUrl` | **전부 403 "Request has expired"** — 시드 시점(2026-06-11) 서명, 한 달 전 만료. 폴백 체인 사실상 항상 사망 (메모리 선례 적중) |
| 3. videoS3Key 부재 | reference 11 doc 전수 | **전부 존재**, 값 전부 `reference/{id}.mp4` — **allowlist prefix = `reference/` 실측 확정** (Task 2 가드 (d) 입력). isActive 전부 true |
| 4. Phase 28 워핑 회귀 | 최신 doc | motionAlignment 정상 방출 (alignment=true). 만료 URL 은 바이트 자체가 안 오므로 expo-video 무음 로드 실패 — 워핑과 무관한 "안 뜸". **회귀 아님** |

핵심 정황: **7일 미만 mode1 done doc 이 0건** — 현존 모든 mode1 doc 의 우측 영상이 확정적으로 죽어 있음. "재분석하면 뜨는데 옛 분석은 안 뜸" 패턴과 정합 (Pitfall 4 Warning sign).

방법론 주의 (후속 진단자용): presigned **GET** URL 에 `curl HEAD` 를 치면 만료와 무관하게 403 (서명에 HTTP method 포함 — SignatureDoesNotMatch 오탐). 반드시 GET + `Range: bytes=0-0` 로 검사하고 XML `<Code>` 를 읽을 것. 이번 진단도 초기 HEAD 검사를 GET 재검으로 교정한 뒤 "Request has expired" 를 확정했다.

## Task 2 — fix (TTL 확정 → 명세 그대로)

커밋: `5b20058`

1. **backend/functions/playback-url/app.py** — `referenceMotionId` 변형 신설 (analysisId 와 상호 배타, 동시 제공 400). canonical 경로 = `firestore_admin.get_reference_motion` (models.reference_motion_path 경유, 리터럴 컬렉션 문자열 0 — `grep reference_motions` 매치 0). 가드 4종 전부 통과해야 서명, 하나라도 실패 → 동일 `404 not_found` (inactive/부재/무영상 응답 구분 불가 — leak 0): (a) doc 존재 (b) `isActive is not False` (c) videoS3Key 존재 (d) `videoS3Key.startswith("reference/")`. id 형식 화이트리스트 `^[A-Za-z0-9-]{1,64}$`. `_PLAYBACK_EXPIRES` diff 0 (7일 유지). 기존 analysisId 경로 byte-불변.
2. **backend/tests/test_playback_url_reference.py** — 11 케이스 전부 PASS: 정상 200 / 부재 404 / **inactive 404 (부재와 body 동일 검증)** / **prefix 밖 키(uploads/...) 404** / videoS3Key 부재 404 / 동시 제공 400 / **임의 s3Key 류 body 무시 (서명 Key = doc videoS3Key 검증)** / id 형식 거부 400 / analysisId 무회귀 (키·응답 스키마) / bad ext 400 / 빈 body 400.
3. **backend/template.yaml** — PlaybackUrlFunction `s3:GetObject` 에 `reference/*` 추가 (uploads/* 유지, 그 외 prefix 불허). presigned URL 은 서명 role 권한으로 GET 되므로 이 정책 없이는 재발급 URL 이 403. FIREBASE_SA_PARAM env(Globals)·SSM 정책은 **기존 존재** — 추가 불필요 확인.
4. **app/src/lib/api.ts** — `requestReferencePlaybackUrl(referenceMotionId)` 신설 (기존 `requestPlaybackUrl` 시그니처 불변).
5. **app/src/app/analysis/result.tsx** — mode1 rightUrl 재발급 훅 (mode3 prev 훅 미러, SAFE_TTL_MS 6일 margin). doc `createdAt` 을 wrapper → Content prop 으로 전달. rightUrl 조립 = `freshRefUrl || result.referenceVideoUrl || refMotion?.videoUrl` (재발급 최우선, 실패 시 기존 폴백 체인 + __DEV__ warn). **VideoCompare.tsx 무접촉** (29-07 소유).
6. **docs/contract.md §2** — `POST /playback-url` 절 신설: 두 변형 상호 배타, 가드 4종, 404 통합, 임의 키 서명 불가, 응답 스키마 불변(playbackUrl/expiresInSec).

검증: `pytest tests/test_playback_url_reference.py -q` → **11 passed**. `npm run typecheck` → **exit 0**. 수용 grep 전부 충족 (canonical 헬퍼 ≥1, `reference_motions` 리터럴 0, isActive ≥1, 클라이언트 키 직접 수용 0).

## SAM Deploy — 미수행 (권한 게이트, 오케스트레이터 이관)

- `sam build --use-container` **성공** (Docker, arm64).
- `sam deploy` 는 **실행 권한 거부** (Claude Code 권한 시스템 — production 스택 배포는 사용자 승인 필요). 우회하지 않고 이관한다.
- 이관이 plan 의 선호 순서와도 정합: "배포는 가능하면 29-05 Task 2 PASS 이후로 순서화" — 29-05 가 작업 말미에 pipeline Lambda env 를 boto3 로 패치하므로, **CFN deploy 가 그 drift 를 template 값으로 되돌릴 수 있음**. 29-05 종료 후 배포 + env 동기화 재확인이 안전한 순서.
- 배포 시 참고: samconfig parameter_overrides 에 RunpodAnalyzeUrl/Token 없음 → sam 이 이전 스택 값 유지 (파라미터는 안전). 단 pipeline 함수 env 의 직접 패치(drift)는 재확인 필요.
- **배포 커맨드** (backend/ 에서): `AWS_PROFILE=sunity-motion sam deploy --no-confirm-changeset`
- **배포 후 스모크 (필수, 아직 미실행):** 유효 Firebase ID 토큰으로 `POST {API_BASE}/playback-url` body `{"referenceMotionId":"ref-power-spin"}` → 200 + playbackUrl GET(Range) 206 video/mp4. 추가: 부재 id → 404, analysisId+referenceMotionId 동시 → 400, 무토큰 → 401.
- RunPod-위임 근거 (plan 명세): deploy 는 pipeline Lambda 도 29-02/03 코드로 재배포하지만 production 채점 경로는 RunPod 위임(delegation-only)이라 미검증 채점 코드 미노출 — Pod 는 29-05 게이트 PASS 전까지 구코드 서빙.

## Deviations from Plan

### Auto-fixed / adapted

**1. [Rule 3 - 문서 구조] contract.md 에 playback-url 절이 원래 부재 → 절 신설**
- **Found during:** Task 2 step 9 (plan 은 기존 절에 "변형 서술 추가" 가정)
- **Fix:** §2 에 `POST /playback-url` 절 전체 신설 (기존 analysisId 변형 + 신규 referenceMotionId 변형 함께 문서화)
- **Files:** docs/contract.md — **Commit:** 5b20058

**2. [Rule 1 - 진단 방법론] HEAD 검사 오탐 교정**
- **Found during:** Task 1 — presigned GET URL 에 HEAD 는 만료 무관 403 (method 가 서명에 포함)
- **Fix:** GET + Range 0-0 + XML `<Code>` 검사로 재검 후 "Request has expired" 확정. SUMMARY 에 방법론 주의 기록

**3. [적응] `result.createdAt` → `doc.createdAt` prop 전달**
- **Found during:** Task 2 step 8 — createdAt 은 AnalysisResult 가 아니라 AnalysisDoc 필드
- **Fix:** wrapper 가 `storedDoc.createdAt` 을 Content prop 으로 전달 (updatedAt 선례 미러). 시맨틱 동일 (분석 doc 생성 시각 기준 보수적 margin)

### Deferred Issues

- **SAM deploy + 배포 후 스모크** — 위 "SAM Deploy" 절. 코드·테스트·계약 완결, 배포만 권한 게이트로 오케스트레이터/belle 이관.
- **백엔드 전체 suite 사전 실패 57건** (gemini/pipeline/rtmw 계열, 로컬 homebrew Python 3.14 환경 — Lambda 런타임 3.12 과 불일치 + Gemini env 기대) — 이 plan 의 diff 와 무관 (playback 관련 실패 0, 신규 실패 0). 수정하지 않음 (scope boundary).

## Known Stubs

None — 재발급 훅은 실 endpoint 에 배선, 데이터 소스 완결. (단 endpoint 의 reference 변형은 deploy 전까지 production 미반영 — 앱 훅은 실패 시 기존 폴백 체인이라 deploy 전에도 무해.)

## Threat Flags

None — 신규 표면(referenceMotionId → S3 서명)은 plan threat_model T-29-06-01/-04/-06 이 이미 등재, 전부 mitigate 구현 (unit 테스트 고정).

## Verification

- [x] 재현 → 원인 확정 → fix 순서 준수 (D-09), 증거 실측 기록
- [x] presigned URL 전문 기록 0 (상태코드·서명시각·만료초만)
- [x] pytest 신규 11 PASS / typecheck exit 0 / 수용 grep 4종 충족
- [x] TTL 7일 유지 (연장 0), analysisId 경로 무회귀
- [ ] sam deploy + 스모크 curl 200 — 권한 게이트로 이관 (위 커맨드)
- [ ] 실기기 D1 재확인 — 29-08 HUMAN-UAT.md 적립 대상

## Self-Check: PASSED

- 7/7 산출 파일 존재, 커밋 5b20058 존재 확인.
