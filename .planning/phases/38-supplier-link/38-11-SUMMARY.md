---
phase: 38-supplier-link
plan: 11
subsystem: app-supplier-web
tags: [expo-router, web, supplier-link, upload-form, xhr-upload, consent, guide]

requires:
  - phase: 38-supplier-link (38-03)
    provides: supplierForm(remainingRequired · validateFile · formatOf · consentAllRequired · buildRequest · parsePrefill · emptyStep1) · supplierRules(mapPresignFailure · uploadOutcomeNext) · supplierCopy(form.* · dialog.* · guide.*)
  - phase: 38-supplier-link (38-10)
    provides: SupplierUi 프리미티브 · requestReferenceUploadUrl · uploadToS3WithProgress · probeSupplier · readVideoDurationSec · /supplier 홈(justUploaded 강조 · 다시 올리기 파라미터 계약)
provides:
  - "/supplier/upload — A-4 STEP 01(체크 5+확인 · 동작 이름 사전/새 이름 · 선수 · 레벨 · 선언 3 · 파일) / STEP 02(동의 필수 3 + 학습 선택 + 철회 고지) · A-5 진행/취소/실패"
  - "/supplier/guide — A-6 7섹션 + 예시 프레임 2장 + 실패 4형 TIP, ?section=s5 / #s5 스크롤"
  - "SupplierUi 폼 프리미티브 10종(StepHeader · FieldError · Helper · TextInput54 · SelectField · Segment · CheckboxRow · AllAgreeBox · FileCard · VideoPreview · ProgressBar · BottomBar) + PrimaryCta onDisabledPress"
  - "/supplier 홈: justUploaded 토스트(form.uploaded.toast) · ?expired=1 세션 만료 문구"
affects: [38-13 (배포 산출물에 두 라우트 포함 · Figma D-22 실측 이월 · 실기기 폼/업로드 검증), 38-09 (라우트 배포 전까지 제출은 '연결이 안 돼요' 인라인)]

tech-stack:
  added: []
  patterns:
    - "STEP 01/02 = 같은 라우트의 두 화면 인스턴스(param step=2). 입력은 모듈 범위 세션 초안에 적고 useFocusEffect 로 다시 읽는다"
    - "비활성 CTA 를 누르면(onDisabledPress) 빈 칸의 인라인 오류를 드러낸다 — 비활성 이유는 하단 바 '필수 항목 n개가 남았어요'"

key-files:
  created:
    - app/src/app/supplier/upload.tsx
    - app/src/app/supplier/guide.tsx
  modified:
    - app/src/components/SupplierUi.tsx
    - app/src/app/supplier/index.tsx

key-decisions:
  - "38-11: Figma MCP 가 이 실행기에도 없어 D-22 get_design_context 미실행 — UI-SPEC Component Inventory 값 그대로, 실측표는 [미확인] 으로 38-13 Task 3 이월(38-10 과 같은 처리)"
  - "38-11: 전체 동의 = 필수 3 만(D-08 · UI-SPEC Decisions 14 기본값 유지). Figma 1:1064 의미를 못 쟀으므로 belle 판정 요청은 아직 없음 — Open for belle 2 그대로"
  - "38-11: 가이드 예시 사진은 9:16 대신 1:1 — 자산이 512×512 정사각이라 9:16 cover 로 자르면 발끝이 잘린다"
  - "38-11: 홈 토스트·강조를 probe ok 뒤로 미룸 — 확인 중 화면엔 Toast 가 없어 3초 타이머가 먼저 끝났다"

requirements-completed: [REQ-38-3, REQ-38-6, REQ-38-8]

duration: 12min
completed: 2026-09-30
---

# Phase 38 Plan 11: 공급자 올리기 폼 + 상세 가이드 (후보 1) Summary

**`/supplier/upload`(STEP 01 체크·정보·선언·파일 → STEP 02 동의 → presign → XHR PUT 진행/취소 → 홈 토스트 또는 실패 패널)와 `/supplier/guide`(7섹션)가 38-03 규칙 import · supplierCopy · theme 토큰만으로 섰다. 공급자 API 가 아직 배포 전이라 실제 제출은 `연결이 안 돼요` 인라인으로 끝나고, 폼 화면 실물 확인은 38-13 belle 몫이다.**

## Performance

- **Duration:** 약 12분 (08:16 착수 → 08:28 SUMMARY)
- **Tasks:** 3 / 3
- **Files:** 생성 2 · 수정 2 (app 전부, backend 무접촉)

## Task Commits

| Task | 내용 | Commit |
|---|---|---|
| 1 | 폼 프리미티브 + STEP 01 | `685f02ce` (feat) |
| 2 | STEP 02 동의 · 제출 · 업로드 · 결과 + 홈 토스트/만료 문구 | `b51e9fbc` (feat) |
| 3 | 가이드 화면 A-6 | `4d66855d` (feat) |

## 관측 (다음 세션이 승계해도 되는 것)

- **[확인] 게이트 (08:25, HEAD `4d66855d`):**
  - `cd app && npm run typecheck` → exit 0
  - `node --test` 6파일(supplierCopy · pickerFailure · supplierForm · supplierRules · videoDuration · videoMeta) → **tests 65 · pass 65 · fail 0** (38-10 뒤와 같은 수 — 이 플랜은 순수 규칙을 새로 만들지 않았다)
  - backend pytest 는 돌리지 않았다 — 이 플랜 backend 파일 무접촉 [확인 `git diff --stat`: app 4파일만]
- **[확인] 웹 export:** `CI=1 npx expo export --platform web --output-dir <scratchpad>/web-export-11` exit 0, **15초**. `web.output` 설정 없음 → SPA(`index.html` 1개, `supplier/guide.html` 없음). 번들 안에 `"./supplier/index.tsx"` · `"./supplier/upload.tsx"` · `"./supplier/guide.tsx"` 각 1회 [확인 grep]. 예시 사진 `ref-kip-up`·`ref-power-spin` 이 `assets/` 로 복사됨.
- **[확인] 시뮬 Safari (iPhone 16 Pro, iOS 18.6, 로그인 안 한 새 세션, 파이썬 SPA 서버 :8082):**
  - `/supplier/guide` → 제목·부제·섹션 1 카드·예시 사진 두 장 윗부분이 보임 — `38-11-web-guide.png`
  - `/supplier/guide?section=s5` → 섹션 4 TIP 카드 끝과 `권리와 동의` 카드가 한 화면에 보임(섹션 5 제목이 화면 맨 위가 아니라 중간) — `38-11-web-guide-s5.png`
  - `/supplier/upload` → A-1 로그인 화면(`시작해 볼까요?`)으로 돌아감 = 인증 가드 동작 — `38-11-web-upload-guard.png`
  - 스크린샷 경로 = 휘발 scratchpad `/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/ef3648dc-db87-4310-a2aa-b555fa84c027/scratchpad/`. 측정 뒤 서버 종료 · 시뮬레이터 종료(측정 전에도 꺼져 있었다).
- **[미확인] 폼 화면 자체(STEP 01/02 · 다이얼로그 · 진행 패널)** — 로그인 + 화이트리스트가 필요해 이 실행에서 한 번도 그려 보지 않았다. 타입검사와 grep 게이트만 통과. 38-13 Task 3 실기기에서 belle 확인.
- **[미확인] 제출 → 오류 분기 실동작.** `POST /reference/upload-url` 은 404 · CORS 없음 [38-10 확인]이라 지금 제출하면 fetch 실패 → `status 0` → `mapPresignFailure` = `offline` → 인라인 `common.offline` + `다시 시도` 가 될 것 [추정 — 38-10 홈 probe 와 같은 경로, 폼에서는 안 눌러 봤다]. 401/403/5xx/PUT 실패 분기는 38-03 `supplierRules.test.ts` 가 매핑 표를 잠그고, 화면은 그 결과를 switch 로 받기만 한다.
- **[확인] 링크:** 홈 `common.guideLink` → `/supplier/guide` (index.tsx 1곳), 폼 `form.sec1.guideLink` → `/supplier/guide`, 학습 사용 chevron → `/supplier/guide?section=s5` (upload.tsx 2곳).
- **[확인] 규칙 재작성 0:** `grep "function validateFile\|function remainingRequired\|function buildRequest" upload.tsx` = 0, `from '../../lib/supplierForm'` = 1, `mapPresignFailure\|uploadOutcomeNext` = 4, `from 'firebase/firestore'` = 0, 색 리터럴(`#xxxxxx`) = 0 (upload · guide · SupplierUi · index).

### Figma 실측 (D-22)

Figma MCP 도구가 이 실행기의 도구 목록에 없어 `get_design_context` 를 한 번도 부르지 못했다 [확인 — 도구 목록]. 값은 UI-SPEC Component Inventory 그대로 넣었다. 아래는 **잰 값이 아니라 넣은 값**이다.

| 노드 | 자리 | 넣은 값 (UI-SPEC) | 실측 |
|---|---|---|---|
| `1:960` | 입력 높이/반경/테두리 · 포커스 · 오류 | 54 / 13 / 1px inputBorder → brand → inputError | [미확인] |
| `1:960` | STEP 라벨 | 13.8 / 700 / brand (38-10 `text.step`) | [미확인] |
| `1:960` | CTA 비활성 | brandButtonDisabled 채움, 글자 흰색 | [미확인] |
| `1:1064` | 동의 행 높이 · 체크박스 · 태그 색 | 최소 48 · 22/반경 8 · `[필수]` brand / `[선택]` resultTextSub | [미확인] |
| `1:1064` | 전체 동의 박스 · **전체 동의 의미** | 54/13 테두리 divider · 필수 3 만 켬 | [미확인] — 의미를 못 쟀으니 belle 판정 요청 근거 없음(Open for belle 2 그대로) |
| `1:407` | 파일 카드 아이콘/간격 | images-outline 32 brand · 간격 16(ui-checker flag 11행) | [미확인] |
| `1:399` | 안내 알약 | 38-10 NoticePill 재사용(반경 15 ≈) · 문구는 정정본 `form.sec4.pill` | [미확인] |
| `1:499` | 검증 다이얼로그 | 기존 `PickErrorDialog` 그대로(토큰 박제본) | 대조 안 함 [미확인] |
| `1:482`/`1:483` · `1:709` | TIP 카드 · 가이드 카드 | 38-10 TipCard(8/4) · Card | [미확인] |

→ 38-13-PLAN Task 3 의 38-10 이월 문단(`≈` 네 칸)과 같은 자리에서 이 표도 재면 된다. 이 플랜은 38-13-PLAN 을 고치지 않았다.

## 진단 (승계 전 재검증)

- 가이드 `?section=s5` 스크롤이 섹션 5 제목을 화면 맨 위가 아니라 중간쯤에 둔 것 = 예시 사진이 로드되며 섹션 1 높이가 늘어난 뒤에도 첫 onLayout 좌표로 스크롤했기 때문 [추정 — 좌표 로그 안 봄]. 섹션 5 는 보이므로 기능은 됨.
- `/supplier/upload` 에서 A-1 이 뜬 것 = 폼의 `ready && !signedIn → replace('/supplier')` 가드 [추정 — 주소창 URL 은 스크린샷에 `localhost` 만 보여 경로를 못 읽었다].

## Deviations from Plan

1. **[Rule 3 - Blocking] Figma D-22 실측 미실행** — Figma MCP 없음. 위 표 [미확인], 38-13 으로 이월. 38-10 과 같은 처리.
2. **[Rule 2 - Missing] 홈(index.tsx) 두 군데 수정** (`b51e9fbc`, 플랜 files_modified 밖):
   - `justUploaded` 에 토스트 `form.uploaded.toast` 가 없었다(38-10 은 강조만). 플랜이 "홈이 param 으로 띄운다 — 38-10 계약" 이라 했으나 그 배선이 없어서 추가. 강조와 함께 **probe ok 뒤**에 띄우게 바꿈 — 확인 중 화면엔 Toast 가 없어 3초가 먼저 끝났다(38-10 강조에도 있던 문제, Rule 1).
   - `?expired=1` → A-1 에 `form.sessionExpired` 문구. 폼이 401 을 받으면 `replace('/supplier?expired=1')` 뒤 signOut.
3. **[Rule 2] 콤보 체크를 바꾸면 이미 고른 파일을 새 길이 상한으로 다시 검사** — 45초 파일을 콤보로 고른 뒤 콤보를 끄면 30초 상한을 우회하던 구멍. 걸리면 파일을 비우고 `tooLong` 다이얼로그.
4. **[Rule 2] 화이트리스트 가드 = probe 1회** — 403/401 이면 `/supplier` 로. 네트워크 실패는 폼을 막지 않는다(제출 때 서버가 다시 본다). 화이트리스트 밖 사용자가 probe 응답 전 잠깐 빈 폼을 볼 수 있다 — 데이터 없는 화면이라 둠.
5. **[UI-SPEC 편차] 가이드 예시 사진 1:1** — 자산 512×512 [확인 sips], 9:16 cover 면 발끝이 잘린다 [확인 이미지 열람]. 캡션 `이 정도 거리와 높이면 돼요` 는 고정 문구인데 정사각 썸네일 자체가 폴 윗부분을 자른 프레임이라, 거리 예시로 충분한지는 belle 눈 판정 대상(메모리 "문법 승인 ≠ 그림 승인").
6. **[UI-SPEC 편차] `unreadable` 다이얼로그 kind** — `PickFailureKind` 에 없어 `processFailed` 자리로 넣고 문구는 `supplierCopy.dialog.unreadable`. 길이 metadata 를 못 읽는 경우는 다이얼로그가 아니라 통과(fail-open) — unreadable 은 picker 자체가 던질 때만.
7. **[설계] STEP 전이 = `router.push(step=2)` + 모듈 범위 세션 초안** — 두 인스턴스가 상태를 공유해야 해서. 올리기 성공 뒤 `router.replace('/supplier?justUploaded=')` 라 스택에 STEP 01 인스턴스가 남는다 → 초안을 비우고(촬영 전 체크 확인만 유지, Decisions 11) STEP 01 이 포커스 때 초안을 다시 읽게 해 옛 파일로 재제출되지 않게 함.
8. **플랜 끝 push 안 함** — push 방식 belle 결정 대기(오케스트레이터 지시).

## TDD Gate Compliance

Task 1 이 `tdd="true"` 이나 새 순수 규칙이 없다 — 규칙은 38-03 에서 테스트와 함께 이미 있고 이 플랜은 import 만 한다(R14). 그래서 RED `test(...)` 커밋 없음. task 게이트 `node --test app/src/lib/supplierForm.test.ts` 16/16 통과.

## Known Stubs

없음. 폼의 동작 이름 사전은 `useReferenceMotions()` 실데이터, 선수 이름은 Google 표시 이름 프리필.

## Threat Flags

None — 새 표면(폼 페이지의 probe 1회 · presign · XHR PUT · 401 시 signOut)은 T-38-11-1~6 · T-38-10 범위 안. 설치 0(T-38-SC).

## Next

- 웨이브 5 남은 것 = 38-09 Task 2 belle 체크포인트(인프라·rules 배포). 그 뒤 웨이브 6 = 38-13(배포 + 실기기 — 폼 화면 첫 실물 확인, Figma 실측 표 두 개).

## Self-Check: PASSED

- 생성 파일 2개 존재(`app/src/app/supplier/upload.tsx` 701줄 · `guide.tsx` 152줄) · 커밋 3건(`685f02ce` · `b51e9fbc` · `4d66855d`) `git log` 존재 · 플랜 커밋 범위 삭제 파일 0 [확인 `git diff --diff-filter=D`].
