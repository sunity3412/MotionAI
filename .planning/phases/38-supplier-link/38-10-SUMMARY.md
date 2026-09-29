---
phase: 38-supplier-link
plan: 10
subsystem: app-supplier-web
tags: [expo-router, web, supplier-link, firestore, onSnapshot, xhr-upload, tdd, video-duration]

# Dependency graph
requires:
  - phase: 38-supplier-link (38-01)
    provides: ReferenceUploadUrlRequest/Response · SupplierProbeResponse · ReferenceRegistrationStatus/Error (types/analysis.ts)
  - phase: 38-supplier-link (38-03)
    provides: supplierRules(normalizeRegistration · normalizePrivate · rowSubtitle · hasDetail · failCopy · expiredCopy · selfCheckLine · selfCheckNote · SELF_SCORE_OK_MIN) · supplierCopy
  - phase: 38-supplier-link (38-04)
    provides: socialAuth.web.ts 팝업 로그인 · 진단 D-1(웹 duration 초) · 미측정 행 · D-3 · 웹 서빙 방식
provides:
  - "pickerDurationMs(duration, os) — 웹 초→ms, 네이티브 불변 (videoDuration.ts)"
  - "probeSupplier · requestReferenceUploadUrl · uploadToS3WithProgress (api.ts, uploadToS3 무접촉)"
  - "useSupplierMotions(uid) where supplierUid 단일 onSnapshot + retry · useSupplierRegistrationPrivate(refId) 비공개 doc 1건 (supplierMotions.ts)"
  - "readVideoDurationSec(src) (videoMeta.ts)"
  - "SupplierUi.tsx 프리미티브 18종 + FailurePanel · DonePanel"
  - "/supplier 라우트 — A-1 로그인 · A-2 권한 없음 · A-3 홈(내 동작 + 내 코드) · ?detail= 실패/만료/등록됨 상세 · 다시 올리기 → /supplier/upload 파라미터 계약"
affects: [38-11 (올리기 폼·가이드가 /supplier/upload 파라미터 name·athleteName·level·isSplit·hasHold·standingStart 를 읽는다), 38-13 (배포 산출물 app/dist · Figma D-22 이월 · probe CORS/구독 이월), 38-09 (라우트 배포 전까지 페이지는 '연결이 안 돼요')]

tech-stack:
  added: []
  patterns:
    - "picker duration 은 한 번 ms 로 바꾼 값을 길이 판정·비트레이트 두 곳이 같이 쓴다(값이 갈리지 않게)"
    - "상세는 URL param(?detail=refId) — 브라우저 뒤로가기 = router.back()"
    - "비공개 doc 은 상세가 열릴 때만 구독(행 N 개 × 읽기 방지, Spark 5만/일)"

key-files:
  created:
    - app/src/app/supplier/index.tsx
    - app/src/components/SupplierUi.tsx
    - app/src/lib/supplierMotions.ts
    - app/src/lib/videoMeta.ts
    - app/src/lib/videoMeta.test.ts
  modified:
    - app/src/lib/videoDuration.ts
    - app/src/lib/videoDuration.test.ts
    - app/src/app/(tabs)/analyze.tsx
    - app/src/lib/api.ts
    - app/src/components/PickErrorDialog.tsx
    - app/src/constants/supplierCopy.ts
    - .planning/phases/38-supplier-link/38-04-MEASUREMENT.md
    - .planning/phases/38-supplier-link/38-09-PLAN.md
    - .planning/phases/38-supplier-link/38-13-PLAN.md

key-decisions:
  - "38-10: Figma MCP 를 열 수 없어 D-22 get_design_context 실측 미실행 — UI-SPEC 값 그대로, ≈ 네 칸은 코드 주석 '(≈, 실측 대기)' → 38-13 Task 1/3 으로 이월"
  - "38-10: /reference/upload-url 라우트 미배포(404) → Task 4 항목 4·5(probe CORS · reference 구독)는 belle 에게 묻지 않고 38-09 라이브 curl + 38-13 Task 3 으로 이월"
  - "38-10: supplierCopy.row.done.info 7키 추가 — UI-SPEC A-3c 가 정보 표 항목만 정하고 문구 키가 없었다"

requirements-completed: [REQ-38-3, REQ-38-4, REQ-38-5]

duration: 51min
completed: 2026-09-30
---

# Phase 38 Plan 10: 공급자 페이지 핵심(후보 1) + 웹 영상 길이 수리 Summary

**웹에서 expo-image-picker 가 초로 주는 `duration` 을 ms 로 바꿔 8초 클립이 "영상이 너무 짧아요" 로 막히던 결함(38-04 D-1)을 고쳤고 belle 이 시뮬레이터에서 "1번 오케이" 로 확인했다. `/supplier` 라우트(로그인 · 권한 없음 · 홈 두 카드 · 실패/만료/등록됨 상세)가 supplierRules/supplierCopy import 와 테마 토큰만으로 섰다. 공급자 API 라우트가 아직 배포 전(404)이라 페이지의 실제 probe · 구독은 38-09/38-13 에서 잰다.**

## Performance

- **Duration:** 51 min (00:35 첫 커밋 → 01:26 마감; belle 측정 대기 포함)
- **Tasks:** 5 (Task 0 RED/GREEN · 1 · 2 · 3 · 4 체크포인트)
- **Files:** 생성 5 · 수정 9 (app 11 + .planning 3)

## Task Commits

| Task | 내용 | Commit |
|---|---|---|
| 0 RED | 웹 8초 클립 길이 판정 실패 테스트 | `55f8eae6` (test) |
| 0 GREEN | `pickerDurationMs` + analyze.tsx 한 번 변환 | `0c902e29` (fix) |
| 1 | 데이터 층 api · supplierMotions · videoMeta | `efd48193` (feat) |
| 2 | SupplierUi 프리미티브 + A-1/A-2/A-3 | `61c46a65` (feat) |
| 3 | 실패(비공개 doc)/만료/등록됨 상세 + 다시 올리기 | `8593792f` (feat) |
| 4 준비 | 재측정 절 · 라우트 404 확인 · 4·5 이월 | `a4ba62d2` (docs) |
| 4 결과 | belle 측정 기록 + 이 SUMMARY | 이 커밋 |

## 관측 (다음 세션이 승계해도 되는 것)

- **[확인 belle] Task 4 원문:** *"1번 오케이, 2번은.. 한 8% 가다가 이렇게 문제가 있어요 실패. 3번도 마찬가지."* + 앱 실패 화면 스크린샷(`잠깐 문제가 있었어요` · `다시 분석하기` · `문의하기`). Pod 을 일부러 끈 측정이라 1·2·3 모두 ○ — 표는 `38-04-MEASUREMENT.md` "## 38-10 재측정".
- **[확인 S3]** 측정 창(≥ 2026-09-29T15:46Z) `uploads/` 객체 2개, uid 앞 4자 `UmH3` = 로그인 테스트 계정과 일치, 둘 다 `.mov` 8,108,834 bytes. **[확인 Firestore]** 같은 시간대 `users/UmH3…/analyses` 2건 = mode3 · failed · `server_error` · `learningOptIn true`. → 후보 (1) presigned PUT · onSnapshot 은 잰 값이 됐다.
- **[미확인] `.mp4` 형식 경로:** 두 객체 크기가 `.mov` 시험 클립(8,108,834)과 바이트 단위로 같고 `.mp4` 시험 클립은 8,402,632 [확인 로컬 stat]. 같은 `.mov` 를 두 번 골랐을 수 있다 — 38-13 Task 3 실기기에서 다시.
- **[확인] 게이트 (2026-09-30 01:2x, 마감 직전 재실행):**
  - `cd app && npm run typecheck` → exit 0
  - `node --test` 6파일(supplierCopy · pickerFailure · supplierForm · supplierRules · videoDuration · videoMeta) → **tests 65 · pass 65 · fail 0**
  - 웨이브 4 마감 게이트 `cd backend && .venv/bin/python -m pytest tests -q` → **5566 passed, 20 skipped, 98 warnings in 58.85s** (38-08 뒤 5566 과 같다 — 이 플랜 backend 무접촉)
- **[확인] 웹 번들:** `CI=1 npx expo export --platform web` exit 0, 10초(Metro 캐시), 번들 안 `pickerDurationMs(e.duration,"web")` 인라인. 38-04 첫 회 16초 / 캐시 7초.
- **[확인] 라우트 미배포:** `POST /reference/upload-url` 무인증 = 404, CORS 헤더 없음(`/upload-url` 은 401 + `access-control-allow-origin: *`). 시뮬 `/supplier` 는 `연결이 안 돼요` 화면.
- **[확인] TDD RED:** `55f8eae6` 시점 RED 는 `pickerDurationMs` 미export 로 실패(커밋 메시지 "RED: pickerDurationMs not exported yet (web 8s clip currently read as 8ms -> tooShort)") — 테스트 이름·단언이 웹 8초 통과를 말한다(플랜이 허용한 형태). 실패 출력 원문은 이 세션에 남아 있지 않다.
- 스크린샷(휘발 scratchpad): `38-10-web-root.png` · `38-10-web-supplier-a1.png`.
- 측정 뒤 8082 `expo serve` 종료 [확인 `lsof -i :8082` 빈 결과]. 시뮬레이터는 그대로.

## 진단 (승계 전 재검증)

- "~8% 뒤 실패" = Pod 부재로 Pipeline Lambda 가 `failed/server_error` 를 썼다 [추정 — CloudWatch 미열람].
- `/supplier` 의 `연결이 안 돼요` = 미배포 404 에 CORS 헤더가 없어 fetch TypeError → `status 0` → offline 문구 [추정 — 브라우저 콘솔 미열람]. 38-09 배포 뒤에는 A-2/A-3 이어야 한다.

## Deviations from Plan

1. **[Rule 3 - Blocking] Figma D-22 실측 미실행** — Task 2·3 에서 Figma MCP 를 열 수 없어 `get_design_context` 를 못 돌렸다. `SupplierUi.tsx` 는 UI-SPEC 값 그대로, `≈` 네 칸(outline 48 · google 48 · STEP 라벨 13.8 · noticePill 15)은 주석 `(≈, 실측 대기)`. 플랜이 요구한 "노드 → 실측값" 표는 **없다**. → 38-13-PLAN Task 3 에 이월 문단 추가(이 커밋).
2. **[Rule 2 - Missing] `supplierCopy.row.done.info` 7키 추가** (`8593792f`) — UI-SPEC A-3c 정보 표에 문구 키가 없어 화면 리터럴 0 규칙을 지키려고 추가.
3. **[Rule 3 - Blocking] `PickErrorDialog` 의 `AlertIcon` export + 선택적 size** (`61c46a65`) — 1:399 안내 알약에 재사용. 기본값 불변(기존 다이얼로그 무변화).
4. **[TDD] Task 1 은 단일 커밋** (`efd48193`) — `videoMeta.test.ts`(document 부재 경로)를 구현과 한 커밋에 넣었다. RED/GREEN 분리 커밋 없음.
5. **[Rule 4 아님 · 범위] `/reference/upload-url` 404** — Task 4 항목 4·5 를 belle 에게 묻지 않고 38-09(라이브 curl 한 줄 추가) · 38-13 Task 3(단계 1·4) 으로 이월(`a4ba62d2`).
6. **플랜 끝 push 안 함** — push 방식 belle 결정 대기.

## TDD Gate Compliance

- Task 0: `test(38-10)` `55f8eae6` → `fix(38-10)` `0c902e29` 순서 존재. GREEN 커밋 type 이 `feat` 가 아니라 `fix`(결함 수리라서).
- Task 1: 분리 커밋 없음(위 편차 4).

## Known Stubs

- `index.tsx` 의 `common.guideLink` → `/supplier/guide`, `PillCta` → `/supplier/upload` 는 38-11 이 만들 라우트로의 링크만 있다(의도, 플랜 명시).

## Threat Flags

None — 새 표면(팝업 로그인 · where supplierUid 구독 · 비공개 doc 읽기 · XHR PUT)은 플랜 T-38-10-1~5 안. 설치 0(T-38-SC).

## Next

- 웨이브 5 = 38-09(인프라 + rules 배포, belle 체크포인트) + 38-11(올리기 폼 · 가이드).

## Self-Check: PASSED

- 생성 파일 5개 존재 · 커밋 6건(`55f8eae6` · `0c902e29` · `efd48193` · `61c46a65` · `8593792f` · `a4ba62d2`) `git log` 존재 · 플랜 커밋 범위 삭제 파일 0 [확인].
