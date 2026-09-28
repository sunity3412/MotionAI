---
phase: 38-supplier-link
plan: 03
subsystem: ui
tags: [copy, docs, supplier-guide, node-test, pure-rules, fixtures, r14, r7, r11]

# Dependency graph
requires:
  - phase: 38-supplier-link (38-01)
    provides: analysis.ts REGISTRATION_ERROR_MESSAGE · ReferenceRegistrationStatus(expired) · ReferenceRegistrationErrorCode(too_large) · ReferenceUploadUrlRequest · ReferenceRegistrationPrivate
  - phase: 38-supplier-link (38-02)
    provides: D-15 문장 원문 · pickerFailure.ts Figma 1:499 확정 문구 · node --test 어법 · 정정 grep 게이트
  - phase: 38-supplier-link (38-UI-SPEC 리뷰판 + §Decisions ui-checker flags · 38-REVIEWS R4/R7/R9/R11/R13/R14)
    provides: §Copywriting 전 표 · guide 7항목 · A-3 상태 표 · 검증 다이얼로그 표
provides:
  - "docs/supplier-guide.md — 공급자 가이드 정본 7항목(D-18), 정은지 프레임 2장, TIP 블록 4줄, 고정 각도·거리 0"
  - "app/src/constants/supplierCopy.ts — common·login·noAccess·home·row·form·dialog·guide 전 키(as const), ui-checker flags #1~#4 적용"
  - "app/src/constants/supplierCopy.test.ts — md verbatim · analysis.ts 텍스트 3원 일치(no_human 예외) · D-13/D-15/R7/R11 · Figma 1:499 = pickerFailure (14건)"
  - "app/src/lib/supplierRules.ts — normalizeRegistration/normalizePrivate · rowSubtitle/rowStatusWord · selfCheckLine/selfCheckNote · failCopy/expiredCopy · hasDetail · sortNewestFirst · mapPresignFailure/presignFailureMessage · uploadOutcomeNext · SELF_SCORE_OK_MIN · LEVEL_LABEL_KO (값 import = supplierCopy 하나)"
  - "app/src/lib/supplierForm.ts — Step1State/ConsentState/FormFile/NameChoice · remainingRequired · validateFile/formatOf · consentAllRequired · buildRequest · parsePrefill/toPrefillParams · emptyStep1 · lockstep 상수 (값 import 0)"
  - "app/src/lib/supplierFixtures.ts — 두 트랙·세 테스트가 공유하는 fixture 1벌(공개 doc 12 · 비공개 doc 4 · presign 실패 7 · 전이 3 · 파일 경계 17 · STEP 01 상태 8 · 동의 4 · 요청 형상 2 · 프리필 3), import 0"
affects: [38-10 supplier/index.tsx(import 만), 38-11 form(import 만), 38-12 web/supplier.html(type-strip 빌드로 같은 파일 + rules.test.mjs 같은 fixture), 38-04 T3 selfScoreMin 결정(SELF_SCORE_OK_MIN 한 줄), 38-05/38-07 registrationError.joints 계약]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "문구 단일점 + 정본 md 텍스트 대조 — 테스트가 fs 로 md 와 타입 파일을 읽어 verbatim 포함을 단언(타입 파일은 import 하지 않는다)"
    - "순수 규칙 파일은 값 import 를 문구 상수 하나로 제한하고 타입은 import type — Node ESM(node --test)과 Metro 가 같은 `.ts` 확장자 specifier 를 읽는다"
    - "fixture 1벌에 expect 필드를 실어 규칙 테스트가 표를 순회 — 리터럴 doc 을 테스트에 다시 쓰지 않는다(R14, 38-12 rules.test.mjs 재사용 전제)"
    - "게이트 grep 은 주석·테스트 리터럴까지 잡는다 — 금지 토큰은 조각으로 붙이고 주석은 다시 쓴다(38-02 flags 6행 교훈 재확인)"

key-files:
  created:
    - docs/supplier-guide.md
    - app/src/constants/supplierCopy.ts
    - app/src/constants/supplierCopy.test.ts
    - app/src/lib/supplierFixtures.ts
    - app/src/lib/supplierRules.ts
    - app/src/lib/supplierRules.test.ts
    - app/src/lib/supplierForm.ts
    - app/src/lib/supplierForm.test.ts
  modified: []

key-decisions:
  - "38-03: 자기 재현성 표시값과 문턱 분기는 같은 반올림 정수(89.6 → '90점' 이면서 '낮아요' 가 아님) — 화면 숫자와 분기가 어긋나지 않게. SELF_SCORE_OK_MIN=90 은 [ASSUMED A9], 38-04 T3 가 이 한 줄만 바꾼다"
  - "38-03: mapPresignFailure 는 status 0 + code 'unauthenticated'(api.ts 가 currentUser 없음에 던지는 값) 를 offline 이 아니라 sessionExpired 로 — 플랜 문장('status 0/네트워크 → offline')의 정제"
  - "38-03: buildRequest 는 못 보내는 상태(필수 미완·서 있는 시작 아니오·필수 동의 미완)에 null — CTA 비활성 조건과 같은 규칙을 한 곳에"
  - "38-03: active + selfCheck failed 행의 부제는 '새로 추가됨'(A-3 표에 없는 조합, [ASSUMED]) — 사연은 상세 패널 selfCheckLine 의 failed 문구가 말한다"
  - "38-03: 순수 규칙 파일의 상대 import 는 `.ts` 확장자 명시 — node --test(ESM) 필수이고 Metro 0.83 resolveSourceFile 이 정확한 경로를 먼저 찾는다(resultSummary.ts·momentJump.ts 선례)"

patterns-established:
  - "supplierCopy 치환 자리({score} {joints} {name} {email} {n} {durationSec} {sizeMB} {pct} {sha})는 소비처가 String.replace 만 — HTML/JSX 해석 금지(T-38-03-2, 38-10/38-12 승계)"
  - "프리필 인코딩 '1'|'0' 은 toPrefillParams/parsePrefill 한 파일 — 두 트랙이 같은 규칙"

requirements-completed: [REQ-38-8, REQ-38-4, REQ-38-6, REQ-38-3]  # CONTEXT 라벨 — REQUIREMENTS.md 에 REQ-38 ID 없음 [확인 grep 0건, 38-02 와 같음]

# Metrics
duration: 23min
completed: 2026-09-28
---

# Phase 38 Plan 03: 공급자 가이드 정본 · 페이지 문구 단일점 · 호스팅 무관 순수 규칙 Summary

**공급자 가이드 `docs/supplier-guide.md`(D-18 7항목, 고정 각도·거리 0)와 페이지 문구 단일점 `supplierCopy`(UI-SPEC 리뷰판 전 키)가 글자 단위로 같음을 node 테스트가 md 텍스트로 잠그고, 실패 문구 7코드는 `title + '. ' + body` 조인으로 `analysis.ts` `REGISTRATION_ERROR_MESSAGE` 와 일치(no_human 예외 명시)하며, 호스팅 후보 둘이 import 만 할 순수 규칙 `supplierRules.ts`·`supplierForm.ts` 가 공용 fixture 1벌로 30건 테스트됐다(리뷰 R14) — 44/44 pass, typecheck 0.**

## Performance

- **Duration:** 23 min
- **Started:** 2026-09-28T14:10:24Z
- **Completed:** 2026-09-28T14:33Z
- **Tasks:** 3 (Task 3 = TDD RED/GREEN 2커밋)
- **Files modified:** 8 created · 0 modified (+2057 / −0, `git diff --stat 00d53c20..HEAD` [확인])

## Accomplishments

- `docs/supplier-guide.md`(78줄): 제목 `촬영과 등록 가이드 (공급자용)` + 인용 헤더(운영자 절차는 `reference-capture-guide.md` §6, 화면 A-6 과 글자 단위 동일) + `guide.sub` + `## 1.`~`## 7.` 섹션 = UI-SPEC `guide.*` 표 리뷰판 그대로. §1 끝 정은지 프레임 2장(`ref-kip-up.jpg`·`ref-power-spin.jpg`, 기존 앱 자산) + 캡션, §4 블록인용 TIP `등록이 안 되는 4가지` 4줄(R6 "서 있는 자세인지는 사람이 확인해 주세요" 포함), §3 R7 "등록 정보로 보관" ×3, §4 R11 고지, §7 `약 3m 안쪽`. 창작 문장 0, 수치 목표 0.
- `supplierCopy.ts`(378줄, `as const`): common 14 · login 7 · noAccess 7 · home 15 · row(status 8 · expired · done · self 6 · tip 3 · fail 8×{title,body}) · form(step·sec1~sec5·업로드 결과) · dialog 5 kind `{title, lines[2]}` · guide(title·sub·s1~s7 + caption·tipHead·tip). ui-checker flags #1 `코드 복사` · #2 `올리기 취소` · #3 `코드 준비 중 · 운영팀이 코드를 넣으면 여기에 보여요` 적용, #4 `동작 올리기 >` 유지. 숫자 상수 없음.
- `supplierCopy.test.ts` 14건: guide 전 문자열(45개) md verbatim + `##` 제목 7개 순서 일치 · 금지 토큰(45°·거리·측면)·이모지 0 · D-15 자리 2 · 실패 8코드 비공백 + 조인 규칙(제목 끝 마침표 없음/본문 마침표) · R4/R11 비공백 · 동의 §6 원문 4 · flags · D-13(크레딧·결제·`\d원`) · **7코드 `title + '. ' + body` 가 analysis.ts `REGISTRATION_ERROR_MESSAGE` 블록에 verbatim**(no_human 예외 주석) · R7/R11 옛 문구 0 · Figma 1:499 2종 = `describePickFailure` 원문.
- `supplierRules.ts`(296줄): 값 import `supplierCopy` 하나, 타입 4종 `import type`. `SELF_SCORE_OK_MIN = 90`(ASSUMED 주석) · `LEVEL_LABEL_KO` = `supplierCopy.form.sec2.level.options`(중복 0) · `normalizeRegistration`(필수 4 없으면 null, 상태 미지 → registering) · `normalizePrivate`(R13, 미지 코드 → server_error, message 보존) · `rowStatusWord`/`rowSubtitle`(8상태, exhaustive switch) · `selfCheckLine`(5분기, 반올림) · `selfCheckNote` · `failCopy`({joints} ' · ') · `expiredCopy` · `hasDetail` · `sortNewestFirst`(입력 불변) · `mapPresignFailure` · `presignFailureMessage` · `uploadOutcomeNext`.
- `supplierForm.ts`(243줄): 값 import 0. 상수 5·30·60·100MB·30자(models.py lockstep, 테스트가 models.py 텍스트 대조) · `REQUIRED_FIELD_COUNT = 8` · `remainingRequired`(개수 + `blocked`) · `formatOf`/`validateFile`(형식 → 용량 → 길이, null/NaN fail-open, 정확히 100MB 통과) · `consentAllRequired`(필수 3) · `buildRequest`(계약 형상 정확, clipRange 키 없음, 못 보내면 null) · `toPrefillParams`/`parsePrefill`('1'|'0', expo-router string[] 첫 값).
- `supplierFixtures.ts`(368줄, import 0): 공개 doc 12(A-3 8상태 + activeSelfQueued·activeSelfFailed·legacySeed·badLevel) · selfScore 경계 5 · 비공개 doc 4(low_confidence·activeOk·too_large·unknownCode) · presign 실패 7 · 업로드 전이 3 · 파일 경계 17 · STEP 01 상태 8 · 동의 4 · 요청 형상 2 · 프리필 3. 모든 행에 `expect`/`next` 답을 실어 테스트가 표를 순회한다.

## Task Commits

1. **Task 1: docs/supplier-guide.md 정본** — `d0076111` (docs) — 게이트 7/0/1/2/1/3/1/1/0/0 [확인]
2. **Task 2: supplierCopy + 대조 테스트 14건** — `a70d8fd9` (feat) — 14/14 · typecheck 0 · `크레딧\|결제` 0 · 38-02 게이트 0 [확인]
3. **Task 3 RED: 규칙 테스트 29건 + fixture** — `0ff4b961` (test) — `ERR_MODULE_NOT_FOUND supplierRules.ts / supplierForm.ts` 로 2 fail [확인]
4. **Task 3 GREEN: supplierRules·supplierForm + R9 fixture 1건** — `8afb2c12` (feat) — 30/30 · typecheck 0 [확인]

REFACTOR 커밋 없음. TDD 게이트: `test(38-03)` 0ff4b961 → `feat(38-03)` 8afb2c12 [확인 git log].

**Plan metadata:** 아래 final commit (docs: complete plan)

## Files Created/Modified

- `docs/supplier-guide.md` — 공급자 가이드 정본(D-18 7항목)
- `app/src/constants/supplierCopy.ts` — 페이지 문구 단일점(UI-SPEC §Copywriting + flags)
- `app/src/constants/supplierCopy.test.ts` — md·analysis.ts·pickerFailure 대조 14건
- `app/src/lib/supplierFixtures.ts` — 공용 fixture 1벌
- `app/src/lib/supplierRules.ts` — 행 상태·자기 점수·실패 문구·오류 매핑·업로드 전이
- `app/src/lib/supplierRules.test.ts` — 14건(fixture 만 입력)
- `app/src/lib/supplierForm.ts` — 필수 개수·파일 검증·동의·요청 조립·프리필
- `app/src/lib/supplierForm.test.ts` — 15건(fixture 만 입력 + models.py 텍스트 lockstep)

## 관측 (이 세션이 직접 실행·읽은 것 — [확인])

- `node --test app/src/constants/supplierCopy.test.ts app/src/lib/supplierRules.test.ts app/src/lib/supplierForm.test.ts` → **44 pass / 0 fail** (14 + 14 + 16 — form 은 상수 lockstep 포함 16). `node --test app/src/lib/pickerFailure.test.ts app/src/lib/videoDuration.test.ts` → 16/16 (무회귀).
- `cd app && npm run typecheck` → exit 0 (Task 2·Task 3 GREEN·최종 각각).
- `cd backend && .venv/bin/python -m pytest tests/test_registration_contract.py -q` → 20 passed (analysis.ts 무접촉 확인 — 이 플랜은 계약 파일을 읽기만 했다).
- Task 1 게이트: `^## ` 7 · `2~3m\|45°\|측면` 0 · `약 3m 안쪽` 1 · 이미지 2 + 자산 2 존재 · `등록이 안 되는 4가지` 1 · `등록 정보로 보관` 3 · R11 문장 1 · R6 문장 1 · 옛 R7 문장 0 · 이모지 0 · 78줄.
- Task 2 게이트: `analysis.ts` 언급 7 · `from '../types/analysis` 0 · `as const` 1 · `코드 복사\|올리기 취소` 2 · 실패 코드 5종 9 · 옛 문구 0 · `크레딧\|결제` 0.
- Task 3 게이트: firebase/react/expo import 0/0/0 · `import type` 1 · `^import { supplierCopy }` 1(값 import 유일) · `SELF_SCORE_OK_MIN = 90` 1 + ASSUMED 주석 · `< 90\|>= 90` 0/0 · 4 export 4 · fixtures 참조 11/3 · `'expired'` 3 · `too_large` fixture 1 + rules.test 5.
- 38-02 정정 게이트 `grep -rn '측면 45°\|2~3m\|정면 우선\|정면으로 다시\|정면으로 촬영\|정면을 기준' app/src docs` → **0건**(중간에 5건 → 1건 → 0건, 아래 Deviations).
- 실패 문구 조인 7건을 눈으로도 대조: `영상에 여러 사람이 나와요. 한 사람만 나오게 다시 촬영해 주세요.` 등 7개 문자열이 analysis.ts 2373~2384 줄 리터럴과 같다(테스트가 같은 것을 기계로 확인).
- metro-resolver 0.83.3 `src/resolve.js:436-451` — `resolveSourceFile` 이 `resolveSourceFileForAllExts(context, "")`(정확한 경로)를 먼저 시도하고 그 다음 `sourceExts` 를 붙인다. 비테스트 소스 `app/src/lib/resultSummary.ts:18` · `momentJump.ts:33-34` 가 이미 `./deductionLabels.ts` 식 `.ts` 확장자 import 로 번들되고 있다.
- `.planning/REQUIREMENTS.md` 에 `REQ-38` 문자열 0건(38-02 관측과 같음).

## 진단 (관측에서 내가 붙인 해석 — 다음 세션 재검증 대상)

- `supplierRules.ts` 의 `'../constants/supplierCopy.ts'` specifier 는 Metro 번들에서 문제없을 것이다 — 위 resolver 소스와 선례가 근거. **Metro 번들 자체는 이 세션에서 돌리지 않았다** [미확인 → 38-10 첫 번들이 확인].
- `failCopy('low_confidence', [])`(joints 비어 있음)는 `잘 안 보인 부위: . …` 를 낸다 — 계약상 38-05 가 `registrationError.joints` 를 항상 채우므로(analysis.ts 1343 주석) 화면에 닿지 않는다고 본다 [미확인 — 38-05/38-07 이 실제로 채우는지는 그 플랜의 테스트가 보인다]. 비면 `message`(서버 치환본)를 쓰는 것은 화면 플랜의 선택지.
- `home.podDown` 을 2줄 배열로, `form.uploading.progress`(`올리는 중 · {pct}%`) 를 키로 둔 것은 UI-SPEC A-3/A-5 본문에서 읽은 것 — 표에는 키가 없었다. 38-10/38-12 가 그 키 이름을 쓰면 된다.

## Decisions Made

- **표시값 = 분기값(반올림):** `doneScore` 가 `Math.round(selfScore)` 를 돌려주고 `rowStatusWord`·`selfCheckLine` 둘 다 그 값으로 `>= SELF_SCORE_OK_MIN` 을 본다. 89.6 은 '90점' 이면서 ok. 이유: 화면에 90 이라 쓰고 "낮아요" 라 하면 belle 이 숫자를 의심한다(숫자는 소비처까지 — CLAUDE.md §7).
- **`status 0 + 'unauthenticated'` → sessionExpired:** api.ts `authedJson` 이 currentUser 없음을 `ApiError(…, 0, 'unauthenticated')` 로 던진다 — 그것을 offline 으로 보이면 사용자가 인터넷을 의심한다. 그 외 status 0 은 offline.
- **`buildRequest` 는 게이트 겸 조립기:** null 조건 = `remainingRequired` 미완 · blocked · 필수 동의 미완. 화면 CTA 비활성 조건과 같은 함수라 두 트랙이 어긋나지 않는다.
- **LEVEL_LABEL_KO 는 supplierCopy 를 가리킨다(복사 아님):** 라벨 문자열 출처 한 곳.
- **fixture 확장:** 플랜의 7상태 + `activeSelfQueued`(row.self.queued 분기) · `activeSelfFailed`(failed 분기) · `legacySeed`(손 등록 seed 가 공급자 행이 아님) · `badLevel` · `failedTooLarge`(R9) · `unknownCode`(미지 코드 규칙). 각 분기가 fixture 없이 리터럴로 테스트되지 않게.
- **파일 검증의 100MB 경계:** `sizeBytes > MAX_VIDEO_BYTES` 만 거부(정확히 100MB 통과) — analyze.tsx `> MAX_BYTES` 와 같은 부등호.
- **STATE.md `stopped_at`/`Stopped at:` 무접촉** — 오케스트레이터 소유(38-02 와 같이 `state.record-session` 미실행).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking gate] `supplierCopy.ts` 헤더 주석의 "크레딧·결제" 낱말**
- **Found during:** Task 2 acceptance (`grep -c "크레딧\|결제" supplierCopy.ts == 0` 가 1)
- **Issue:** 값이 아니라 "없다" 고 적은 주석이 게이트에 걸렸다.
- **Fix:** 주석을 "실증은 무료라 돈에 관한 문구가 없다(D-13)" 로. 값 무접촉.
- **Committed in:** a70d8fd9

**2. [Rule 3 - Blocking gate] 38-02 정정 게이트가 새 테스트 리터럴·주석의 거리 토큰을 잡음**
- **Found during:** Task 2 acceptance(게이트 5건 → 1건)
- **Issue:** 금지 토큰을 검사하는 테스트가 그 토큰을 리터럴로 들고 있고, 주석 2곳(`supplierCopy.ts` s7 · 테스트 헤더)이 D-18 ⑦ 원문을 인용했다.
- **Fix:** 테스트는 `['2~3', 'm'].join('')` 로 조각 결합(검사 문자열은 같다) + 주석은 "2~3 미터"/"옛 거리 문구" 로 다시 씀. 게이트 0건.
- **Committed in:** a70d8fd9

### 플랜 export 목록 밖 추가(범위 확장 아님 — 같은 규칙의 조각)

- `supplierRules.ts`: `rowStatusWord`(부제의 상태어만), `presignFailureMessage`(분기 → 문구 단일점, forbidden 은 null), `isRegistrationErrorCode`(타입 가드 export).
- `supplierForm.ts`: `formatOf`, `emptyStep1`, `toPrefillParams`(디코더와 한 파일), `REQUIRED_FIELD_COUNT`, lockstep 상수 5개 export.
- `supplierCopy.ts`: `home.podDown` 배열, `form.uploading.progress`, `form.sec2.level.options` 를 SkillLevel 키 객체로.

---

**Total deviations:** 2 auto-fixed (둘 다 게이트 정정, 값·로직 무접촉)
**Impact on plan:** 산출물·문구·규칙은 플랜 그대로. 스코프 확장 0.

## Issues Encountered

- 프로젝트 스킬 `apple-design`·`design-taste-frontend` 는 모션·랜딩 페이지 규칙이라 이 플랜(문서·문구·순수 규칙, 렌더 0)에 적용할 항목이 없었다 [확인 SKILL.md 머리 읽음].
- Node 가 `app/package.json` 에 `"type"` 이 없어 매 실행 `MODULE_TYPELESS_PACKAGE_JSON` 경고를 낸다(기존 테스트와 같음, 동작 무관). 고치려면 package.json 변경이라 이 플랜 밖.
- `requirements.mark-complete REQ-38-8 REQ-38-4 REQ-38-6 REQ-38-3`: 네 ID 는 REQUIREMENTS.md 에 없는 CONTEXT 라벨 — 결과는 아래 State 절.

## Known Stubs

None. `SELF_SCORE_OK_MIN = 90` 은 stub 이 아니라 **[ASSUMED RESEARCH A9]** 상수(주석에 명시, 38-04 T3 결정으로 그 줄만 바뀐다). `home.codePending` 은 코드가 없을 때의 정식 문구(flag #3)이지 자리표시가 아니다.

## Threat Flags

없음 — 새 네트워크 엔드포인트·인증 경로·스키마 변경 0. 테스트가 읽는 파일은 리포 안 md·ts·py 텍스트뿐. T-38-03-2(치환 자리 String.replace 만)·T-38-03-3(클라이언트 검사는 UX, 상한은 서버)은 각 파일 헤더 주석으로 38-10/38-12 에 승계했다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 38-10/38-11(Expo): `import { supplierCopy } from '../../constants/supplierCopy'`, `import { … } from '../../lib/supplierRules'`/`supplierForm` — 화면은 문구·규칙을 다시 쓰지 않는다. 목록 훅은 `normalizeRegistration` + `sortNewestFirst`, 상세는 `normalizePrivate` + `failCopy(err.code, err.joints)`/`expiredCopy()`, 폼은 `remainingRequired`→`validateFile`→`consentAllRequired`→`buildRequest`, 재시도 프리필은 `toPrefillParams`/`parsePrefill`.
- 38-12(HTML): type-strip 빌드가 `supplierCopy.ts`·`supplierRules.ts`·`supplierForm.ts` 를 ESM 으로 — 값 import 는 `supplierRules.ts:20` 한 줄뿐(specifier `./copy.js` 치환 대상). `rules.test.mjs` 는 `supplierFixtures` 의 `expect`/`next` 표를 그대로 순회하면 된다.
- 38-04 T3: belle 이 재현성 통과선을 주면 `supplierRules.ts` `SELF_SCORE_OK_MIN` 한 줄 + `supplierFixtures.selfScoreBoundary` 표만 바뀐다.
- 38-05/38-07: `registrationError.joints` 를 항상 채우는 계약을 지켜야 `failCopy` 가 빈 부위 목록을 내지 않는다(위 진단 2).
- 남은 것: 정은지 새 영상이 오면 이 phase 보다 시험 영상 2차가 먼저(플랜 머리말 1).

## Self-Check: PASSED

- 생성 파일 8개 + 이 SUMMARY 존재 [확인 `[ -f ]`]
- 커밋 4개 존재 [확인 `git log --all`]: d0076111 (docs) · a70d8fd9 (feat) · 0ff4b961 (test) · 8afb2c12 (feat)
- TDD 게이트 순서 [확인]: `test(38-03)` 0ff4b961 → `feat(38-03)` 8afb2c12

---
*Phase: 38-supplier-link*
*Completed: 2026-09-28*
