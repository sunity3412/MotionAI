---
phase: 38-supplier-link
plan: 02
subsystem: ui
tags: [expo, react-native, expo-image-picker, node-test, copy, ia, simulator, idb]

# Dependency graph
requires:
  - phase: 38-supplier-link (38-CONTEXT D-12~D-16 · 38-UI-SPEC §B/§C · 리뷰 R15c)
    provides: 문구 정본(§C 표 14행 + 길이 검사 2건 + profileCopy 표) · 길이 검사 보장 범위 문장
  - phase: 26-onboarding-upload-guide
    provides: analyze.tsx validate()/pickerFailure.ts 종류→문구 단일점 + exhaustiveness 게이트 + node --test 어법
provides:
  - "app/src/lib/videoDuration.ts — classifyDurationMs(ms) → 'tooShort' | 'tooLong' | null (fail-open) + MIN/MAX_DURATION_MS 3000/90000 (순수, RN import 0)"
  - "pickerFailure.ts PickFailureKind 'tooShort' | 'tooLong' + 1:499 양식 문구 2건"
  - "analyze.tsx validate() 길이 분기(format → tooLarge → duration) + launchCameraAsync videoMaxDuration: 90"
  - "촬영 문구 정정 14자리(loading.tsx ×5 · analyze.tsx ×2 · help.tsx · docs/ia.md ×3 · docs/reference-capture-guide.md ×3) — 정제 grep 게이트 0건"
  - "app/src/constants/profileCopy.ts + 마이 탭 '강사 코드 · 미입력' InfoRow 1행(표시만, D-12)"
  - "시뮬레이터 실물 2장: 38-02-simulator-profile.png · 38-02-simulator-tips.png"
affects: [38-03 supplierCopy(같은 D-15 문장 재사용), 38-10/38-11/38-12 공급자 페이지(pickerFailure 양식·길이 다이얼로그 형식), 강사 코드 입력·귀속(다음 phase — profileCopy.instructorCode.value 가 그때 데이터로 바뀐다)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "순수 판정 모듈 + node --test (Node 24 type stripping, 의존성 0) — videoDuration.ts 는 pickerFailure.ts 와 같은 규율"
    - "검증은 종류만 반환·문구는 단일점(pickerFailure.ts)·exhaustiveness 게이트가 누락을 typecheck 로 잡는다"
    - "화면 문구 상수 파일(profileCopy.ts = authCopy.ts 규율 미러) — 화면 파일 한국어 리터럴 0"
    - "시뮬레이터 실물 확인 = 접근성 트리(idb ui describe-all)로 요소 존재 확인 + 스크린샷을 눈으로"

key-files:
  created:
    - app/src/lib/videoDuration.ts
    - app/src/lib/videoDuration.test.ts
    - app/src/constants/profileCopy.ts
    - .planning/phases/38-supplier-link/38-02-simulator-profile.png
    - .planning/phases/38-supplier-link/38-02-simulator-tips.png
  modified:
    - app/src/app/(tabs)/analyze.tsx
    - app/src/lib/pickerFailure.ts
    - app/src/lib/pickerFailure.test.ts
    - app/src/app/analysis/loading.tsx
    - app/src/app/help.tsx
    - app/src/app/(tabs)/profile.tsx
    - docs/ia.md
    - docs/reference-capture-guide.md

key-decisions:
  - "길이 검사의 보장 범위 = 클라이언트 fail-open 하나. duration 없음/0 은 통과하고 수요자 uploads/ 경로에 서버 측 길이 상한은 없다(범위 밖 — 공급자 경로만 38-01/38-07 서버 2차 방어). 코드 헤더·위협표·이 SUMMARY 가 같은 문장 (리뷰 R15c)"
  - "loading.tsx 확인 체크리스트 행은 '~찍었는지' 문법 변형 — deliberate deviation from D-15 sentence (grammar only), UI-SPEC ui-checker flags 5행"
  - "시뮬레이터 확인은 iOS 26.5 sim 의 09-10 빌드(main.jsbundle 내장·OTA 설정 — Metro 를 안 본다) 대신 iOS 18.6 sim 의 08-31 dev client 빌드 + Metro 로 했다. expo run:ios 재빌드는 하지 않았다(기존 dev client 가 있었으므로 플랜 (2) 분기의 '있으면' 경로)"
  - "STATE.md 의 stopped_at / Stopped at 은 오케스트레이터 소유라 state.record-session 을 건너뛰었다(그 명령이 Stopped At 을 덮는다)"

patterns-established:
  - "videoDuration.ts 헤더 = 보장 범위 선언의 정본. 길이 상한을 서버로 옮기면 이 헤더와 위협표를 같이 고친다"
  - "정정 게이트 명령(정제판): grep -rn '측면 45°\\|2~3m\\|정면 우선\\|정면으로 다시\\|정면으로 촬영\\|정면을 기준' app/src docs → 0건. 주석까지 잡으므로 주석은 다시 쓴다(추가만으로는 실패)"

requirements-completed: [REQ-38-5, REQ-38-6]  # CONTEXT 라벨 — REQUIREMENTS.md 에는 없는 ID (UI-SPEC "REQUIREMENTS.md 에 Phase 38 시각 요구 없음" [확인 grep 0건])

# Metrics
duration: 19min
completed: 2026-09-28
---

# Phase 38 Plan 02: 앱 길이 검사 3~90초 + 촬영 문구 정정 14자리 + 마이 탭 강사 코드 한 줄 Summary

**수요자 영상 길이 3~90초를 순수 함수 `classifyDurationMs` 로 즉시 판정(fail-open, node 테스트 16/16)하고, '측면 45°·2~3m·정면' 문구 14자리를 "기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)" 계열로 바꿨으며(게이트 0건), 마이 탭에 `강사 코드 · 미입력` InfoRow 한 줄을 profileCopy 단일 출처로 붙여 iOS 시뮬레이터 실물로 확인했다.**

## Performance

- **Duration:** 19 min
- **Started:** 2026-09-28T13:46:26Z
- **Completed:** 2026-09-28T14:05Z
- **Tasks:** 3 (Task 1 = TDD RED/GREEN 2커밋)
- **Files modified:** 13 (created 5 · modified 8)

## Accomplishments

- `app/src/lib/videoDuration.ts`: `MIN_DURATION_MS=3000` · `MAX_DURATION_MS=90000` · `classifyDurationMs(ms)` — 값 없음/0/NaN → `null`(fail-open), `< 3000 → 'tooShort'`, `> 90000 → 'tooLong'`, 경계 포함. RN/expo import 0. 헤더에 리뷰 R15c 보장 범위 문장.
- `analyze.tsx validate()`: `format → tooLarge` 뒤에 `classifyDurationMs(asset.duration)` (기존 분기 순서 불변, 리터럴 상수 0). `launchCameraAsync` 에 `videoMaxDuration: 90`.
- `pickerFailure.ts`: `'tooShort' | 'tooLong'` + `copyFor` 2건(UI-SPEC §C 표 글자 단위, `다른 파일 선택`/`repick`). 기존 Figma 확정 문구·순서 무접촉. exhaustiveness 게이트가 두 kind 매핑을 typecheck 로 요구한다.
- 촬영 문구 정정 14자리 — UI-SPEC §C "최종" 열 그대로(창작 0). 정제 게이트 `grep -rn '측면 45°\|2~3m\|정면 우선\|정면으로 다시\|정면으로 촬영\|정면을 기준' app/src docs` → **0건** [확인].
- 마이 탭: 계정 카드 바로 아래 `styles.infoList` + `InfoRow label="강사 코드" value="미입력" isLast` + `styles.guestHint` 캡션. Pressable 없음, 신규 StyleSheet 0, 색·간격 리터럴 0, 화면 한국어 리터럴 0(문구는 `profileCopy.ts`). 게스트·회원 모두.

## Task Commits

1. **Task 1 RED: 길이 분기·문구 실패 테스트** — `197e60e2` (test) — `videoDuration.ts` 부재 `ERR_MODULE_NOT_FOUND`, `tooShort`/`tooLong` 문구 `undefined` 로 실패 확인 [확인]
2. **Task 1 GREEN: classifyDurationMs + tooShort/tooLong + videoMaxDuration 90** — `88b75fde` (feat) — `node --test` 16/16 · typecheck clean [확인]
3. **Task 2: 촬영 문구 정정 14자리** — `ab4cdf2a` (docs) — 게이트 0건 · 스타일 무접촉 · `git diff --stat` 5파일 [확인]
4. **Task 3: 마이 탭 강사 코드 한 줄 + profileCopy + 시뮬레이터 실물 2장** — `fab5d4b7` (feat)

REFACTOR 커밋 없음(정리할 것 없었다). TDD 게이트: `test(38-02)` → `feat(38-02)` 순서 [확인 git log].

**Plan metadata:** 아래 final commit (docs: complete plan)

## Files Created/Modified

- `app/src/lib/videoDuration.ts` — 길이 판정 순수 함수 + 상수 + 보장 범위 헤더
- `app/src/lib/videoDuration.test.ts` — 7 테스트(fail-open 3 · 경계 4 · 상수)
- `app/src/lib/pickerFailure.ts` — kind 2 + 문구 2 (Phase 38 D-14 블록, Figma 블록 밖)
- `app/src/lib/pickerFailure.test.ts` — tooShort/tooLong 원문 고정 2 테스트 + ALL_KINDS 확장
- `app/src/app/(tabs)/analyze.tsx` — validate() 길이 분기 · videoMaxDuration · 안내 문단/주석 정정
- `app/src/app/analysis/loading.tsx` — not_pole 본문(:490) · 촬영 TIP 3줄 · 확인 체크리스트 행
- `app/src/app/help.tsx` — 촬영 FAQ 본문 + 길이 3~90초 한 줄
- `app/src/app/(tabs)/profile.tsx` — instructorCode 행 + 캡션 (import profileCopy)
- `app/src/constants/profileCopy.ts` — `profileCopy.instructorCode {label,value,hint,a11y}` (as const)
- `docs/ia.md` — AC-VID-002-1/2 Condition 정정 + `AC-VID-003-1X`(90초 초과) 행 신설
- `docs/reference-capture-guide.md` — §1 표 시점 2행 + §2 "정면성" → "시작 방향"(고정 각도 없음). §6 운영자 절차 무접촉(D-18) [확인 diff hunk @@27,@@47 만]
- `.planning/phases/38-supplier-link/38-02-simulator-profile.png` · `38-02-simulator-tips.png` — 시뮬레이터 실물

## 관측 (이 세션에서 실행·읽은 것 — [확인])

### 시뮬레이터 실물 확인 (Task 3)

- 환경: iPhone 16 Pro (iOS 18.6, udid `873D7CB3…`) 의 **08-31 dev client 빌드**(main.jsbundle 없음, 기동 화면 "Development Build") + `CI=1 npx expo start --port 8081`(Metro `packager-status:running`). Metro 로그 `iOS Bundled 10884ms node_modules/expo-router/entry.js (1462 modules)`.
- 진입 경로: 인트로 `시작하기` → 로그인 게이트 `게스트로 시작하기` → 홈 탭(탭 바 `홈/분석/기록/마이, tab, n of 4`) → `마이` 탭 / `분석` 탭 → `내 자세 분석` 카드(소스 선택 단계).
- `mcp__ios-simulator__ui_find_element` 는 이 실행자에 노출되지 않아 **idb `ui describe-all`(같은 접근성 트리 덤프)** 로 대신했다. 발췌:
  - 마이 탭 (`tree_profile.json`):
    - `GenericElement | 강사 코드 미입력. 입력은 다음 업데이트에서 열려요 | x=20 y=259 w=362 h=47`
    - `StaticText | 수업에서 받은 코드를 넣는 자리예요. 입력은 다음 업데이트에서 열려요. | x=20 y=315 w=362 h=14`
  - 분석 소스 단계 (`tree_tips.json`):
    - `StaticText | 가장 정확한 분석을 위해 앱에서 직접 촬영하거나 원본 화질 영상을 올려주세요. 카톡 등으로 받은 영상은 압축돼 정확도가 낮을 수 있어요 (카톡은 '원본'으로 전송). 기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정). 너무 가까우면 폴 전체가 안 들어와 분석에 실패할 수 있어요. | x=20 y=412 w=362 h=72`
- 스크린샷을 눈으로 열어 봤다: `38-02-simulator-profile.png` — 계정 카드("게스트 · ID k9fQ…wbm2 · 로그인") 와 그 캡션 아래에 `강사 코드 | 미입력` 1행 카드 + 캡션, 그 아래 "내 몸 정보". 기존 InfoRow 양식(라벨 회색·값 굵게)과 같다. `38-02-simulator-tips.png` — 소스 선택 화면 안내 문단에 정정 문구가 보인다. 렌더 크래시 없음. 둘 다 `PNG image data, 1206 x 2622`.
- 부작용: 이 sim 의 게스트 세션은 **기존 uid**(`k9fQ…wbm2`, 분석 7회·평균 69점이 화면에 있었다)였다 — 새 익명 사용자가 만들어졌는지는 [미확인]. 내가 한 Firestore 쓰기·스캔·배포·Pod 기동은 0. Metro 종료·두 sim shutdown 으로 원복.
- iOS 26.5 sim (`A20B95BE…`) 의 09-10 빌드는 `main.jsbundle` 내장 + `EXUpdatesEnabled=true/CheckOnLaunch ALWAYS` — 딥링크로 열어도 Metro 요청 0건이라 확인 수단으로 쓰지 않았다.

### Figma 실측 (D-22)

- `get_design_context`(fileKey `jrdI7kp245HkPfLB0nclsz`, nodeId `1:754`) — **[미확인 — 도구 부재]**. `mcp__plugin_figma_figma__get_design_context` · `mcp__figma__get_design_context` 둘 다 "No such tool available"(MCP 도구가 이 실행자에 노출되지 않음, 업스트림 #13898 계열). 폴백도 없었다: 환경변수에 Figma 토큰 0, 로컬 Figma Desktop MCP(127.0.0.1:3845) 응답 없음.
- 대신 문서 사실: UI-SPEC "Figma 참조" B 행 "마이 화면 본체는 Figma 에 없음 — 탭 `1:754` 만" · design.md §8 "피그마에 아직 없는 화면들 … [구현됨] 마이페이지" [확인 읽음]. 구현은 이 전제(신규 시각 0, 기존 InfoRow 재사용)대로이고 Figma 원격 이미지 URL 은 코드에 넣지 않았다. **Figma 노드 자체를 열어 본 것은 아니다.**

### 게이트·검사 결과

- `node --test app/src/lib/videoDuration.test.ts app/src/lib/pickerFailure.test.ts` → 16/16 pass.
- `cd app && npm run typecheck` → exit 0 (Task 1·2·3 각각).
- Task 1 grep: `classifyDurationMs` in analyze.tsx 2 · `videoMaxDuration: 90` 1 · `3 \* 1000\|90 \* 1000` in analyze.tsx 0 · `'tooShort'\|'tooLong'` in pickerFailure.ts 4 · `서버 2차 방어` in analyze.tsx 0 · `서버 측 길이 상한이 없다` in videoDuration.ts 1.
- Task 2 grep: 게이트 0 · 정정 문구 count loading 2 / analyze 1 / help 1 · `찍었는지` 변형 1 · `AC-VID-003-1X` 1 · `시작 방향:` 1.
- Task 3 grep: `profileCopy.instructorCode` in profile.tsx 4 · `'강사 코드'` in profileCopy.ts 1 · `강사 코드` in profile.tsx 0 · diff 추가분 hex 색 0 · StyleSheet 항목 추가 0(diff hunk 는 import 1 + JSX 블록 1).

## Decisions Made

- **길이 검사 보장 범위(리뷰 R15c, 위협표 T-38-02-1):** 90초 상한으로 duration 이 있는 픽은 앱에서 차단한다. **duration 부재 픽은 통과(fail-open)하고 수요자 `uploads/` 경로에 서버 측 길이 상한은 없다** — Phase 38 범위 밖(38-01 validation 은 공급자 경로만). 이 위험은 수용한다. 같은 문장이 `videoDuration.ts` 헤더에 있고 `analyze.tsx` 에는 "서버 2차 방어" 라는 말을 쓰지 않았다.
- `loading.tsx` 확인 체크리스트 행 `· 기준 영상처럼 찍었는지(폴 전체와 전신이 들어오는 거리, 세로, 고정)` — **deliberate deviation from D-15 sentence (grammar only)**: "~했는지" 체크리스트 문법(UI-SPEC §Decisions ui-checker flags 5행). 다른 13자리는 §C 표 최종 문자열 그대로.
- `analyze.tsx` 안내 문단 주석은 `2~3m` 가 남지 않게 다시 썼다(flags 6행) — 게이트가 주석까지 잡는다.
- `videoMaxDuration: 90` 은 초 단위 리터럴(플랜 acceptance 가 리터럴을 요구) + 주석으로 `MAX_DURATION_MS` 와 같은 값임을 표시. 촬영 뒤 `validate()` 가 같은 상한을 한 번 더 본다.
- **실기기 미반영(OTA/EAS 미실행 — belle 결정 대기).** 이 phase 의 확인은 시뮬레이터까지(ROADMAP 38 Not in scope).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 시뮬레이터 확인 경로 변경 — 부팅한 sim 의 앱이 dev client 로 동작하지 않았다**
- **Found during:** Task 3 (시뮬레이터 실물 확인)
- **Issue:** 플랜 (2) 는 "`listapps` 에 앱이 있으면 `expo start --ios`" 인데, iOS 26.5 sim 의 09-10 빌드는 `main.jsbundle` 내장·OTA 설정이라 Metro 를 보지 않았다(딥링크 뒤 Metro 요청 0건, iOS 는 "열겠습니까?" 확인창에서 멈춤).
- **Fix:** 다른 sim(iPhone 16 Pro iOS 18.6)의 08-31 dev client 빌드를 부팅해 Metro 서버 행을 탭 → 번들 로드 → 확인. `expo run:ios` 재빌드 없음.
- **Files modified:** 없음(코드 무접촉)
- **Verification:** Metro `iOS Bundled … (1462 modules)` + 접근성 트리에 두 텍스트 존재 + 스크린샷 눈 확인
- **Committed in:** fab5d4b7 (스크린샷)

**2. [Rule 1 - Bug] profile.tsx JSX 주석의 '강사 코드' 리터럴 제거**
- **Found during:** Task 3 acceptance grep (`grep -c "강사 코드" profile.tsx == 0` 가 1)
- **Issue:** 렌더 문자열은 아니지만 주석에 라벨 원문을 적어 게이트에 걸렸다.
- **Fix:** 주석을 `instructorCode 행` 어법으로 바꿈. 화면 리터럴 0 유지.
- **Committed in:** fab5d4b7

---

**Total deviations:** 2 auto-fixed (1 blocking 경로 변경, 1 게이트 정정)
**Impact on plan:** 산출물·문구·구조는 플랜 그대로. 스코프 확장 0.

## Issues Encountered

- Figma MCP 도구 미노출 → D-22 실측 [미확인] (위 "관측 — Figma 실측" 절). 다음 세션에서 Figma 를 열 수 있으면 `1:754` 를 실측해 이 절을 `[확인]` 으로 바꾸면 된다 — 구현 변경 가능성은 낮다(마이 본체가 Figma 에 없다는 것이 두 문서의 관측).
- `mcp__ios-simulator__*` 도 미노출 → idb 접근성 트리로 대체(같은 정보: type/label/frame).
- STATE.md 의 `stopped_at`·`Stopped at:` 은 오케스트레이터 소유라 `state.record-session` 을 실행하지 않았다(그 명령이 Stopped At 을 덮는다 — 38-01 뒤 3ee2c58b 가 그 복구 커밋).
- `requirements.mark-complete REQ-38-5 REQ-38-6`: 두 ID 는 REQUIREMENTS.md 에 없는 CONTEXT 라벨 — 결과는 아래 State/Roadmap 절.

## Known Stubs

| Stub | File | Reason / resolves in |
|---|---|---|
| `profileCopy.instructorCode.value = '미입력'` 고정 — 데이터 소스 없음, 탭 동작 없음 | `app/src/constants/profileCopy.ts` · `app/src/app/(tabs)/profile.tsx` | **의도된 표시 전용**(CONTEXT D-12: 이 phase 는 표시만, 입력·귀속·크레딧 지급은 §10 단계 2 이후 belle 승인). 힌트 문구가 "입력은 다음 업데이트에서 열려요" 로 사용자에게 상태를 말한다(UI-SPEC Open for belle 4). 해소 = 강사 코드 입력·귀속 phase |

## Threat Flags

없음 — 새 네트워크 엔드포인트·인증 경로·파일 접근·스키마 변경 0. 위협표 T-38-02-1(길이 검사 fail-open 수용)은 위 Decisions 에 같은 문장으로 적었다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 38-03 `supplierCopy` 의 D-15 문장(`row.tip[0]`, `form.sec4.pill[0]`)은 이 플랜의 앱 문자열과 글자 단위로 같다 — 복사해 쓰면 된다.
- 공급자 페이지 길이 다이얼로그(5~30초/콤보 60)는 `pickerFailure.ts` `tooShort`/`tooLong` **양식**(제목 + 2줄 + 다른 파일 선택)을 따르되 문구는 UI-SPEC "검증 다이얼로그" 표의 공급자판.
- 앱 변경 3건(REQ-38-5/6)은 **실기기 미반영(OTA/EAS 미실행 — belle 결정 대기)**.

## Self-Check: PASSED

- 생성 파일 6개 존재 [확인 `[ -f ]`]: videoDuration.ts · videoDuration.test.ts · profileCopy.ts · 38-02-simulator-profile.png · 38-02-simulator-tips.png · 이 SUMMARY
- 커밋 4개 존재 [확인 `git log --all`]: 197e60e2 (test) · 88b75fde (feat) · ab4cdf2a (docs) · fab5d4b7 (feat)
- TDD 게이트 순서 [확인]: `test(38-02)` 197e60e2 → `feat(38-02)` 88b75fde

---
*Phase: 38-supplier-link*
*Completed: 2026-09-28*
