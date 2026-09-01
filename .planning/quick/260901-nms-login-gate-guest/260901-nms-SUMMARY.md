---
phase: quick-260901-nms
plan: 01
subsystem: auth
tags: [expo-router, firebase-auth, anonymous-auth, login-gate, onboarding]

requires:
  - phase: quick-260831-my-tab-login-entry
    provides: 마이 탭 로그인 입구 + 소셜(Google/Apple) 로그인 경로 (belle 실기기 확인)
provides:
  - 로그인 화면 = 앱의 첫 관문 (로그인 소셜 타일 / 회원가입 링크 / 게스트로 시작하기 3구성)
  - 인트로 시작하기 → /auth/login push (즉시 게스트 로그인 제거)
  - 익명 세션 자동 홈 진입 차단 — 멤버(비익명) 세션만 자동 진입
  - 게스트 진입 시 dismissAll 스택 위생 (튜토리얼 종료가 인트로로 새는 결함 차단)
affects: [계정 시스템(Phase 36), 온보딩, 튜토리얼]

tech-stack:
  added: []
  patterns:
    - "one-shot onAuthStateChanged 복원 판정 (handled 플래그, 자기-unsubscribe 대신)"
    - "push 된 화면에서의 게스트 진입 = canDismiss → dismissAll → replace 스택 위생"

key-files:
  created: []
  modified:
    - app/src/constants/authCopy.ts
    - app/src/app/auth/login.tsx
    - app/src/app/index.tsx

key-decisions:
  - "intro.ctaLoading/error 키 삭제를 Task 1 → Task 2 커밋으로 이동 — Task 1 시점 삭제는 소비처(index.tsx)가 남아 typecheck 가 깨짐. 최종 상태는 계획과 동일"
  - "게스트 버튼 busy 시 타일과 같은 pressed(opacity 0.6) dim 재사용 — 화면 내 일관성"
  - "uid 불변 검증은 육안(기록 표시) 대신 AsyncStorage authUser 직접 판독 — createdAt 이 세션 재사용/신규 생성을 구분하는 더 강한 증거"

patterns-established:
  - "게스트 진입 라우팅: canDismiss() → dismissAll() → replace(seen ? '/(tabs)' : '/tutorial')"

requirements-completed: []

duration: 22min
completed: 2026-09-01
---

# Quick 260901-nms: 로그인 게이트 + 게스트로 시작하기 Summary

**인트로 시작하기가 즉시 게스트 로그인 대신 로그인 화면(소셜/회원가입/게스트 3구성)으로 보내고, 익명 세션도 자동 홈 진입하지 않는 게이트를 시뮬레이터 7장 증적 + AsyncStorage uid 판독으로 실측 완료.**

## Performance

- **Duration:** 22min
- **Started:** 2026-09-01T08:13:58Z
- **Completed:** 2026-09-01T08:35Z
- **Tasks:** 3/3
- **Files modified:** 3 (코드) + 스크린샷 7장

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | 로그인 화면 게스트 버튼 + 카피 | a2a1f585 | authCopy.ts (guestCta 3키), auth/login.tsx (버튼+핸들러+dismissAll 라우팅) |
| 2 | 인트로 → 로그인 게이트 재배선 | 7d72dda6 | index.tsx (push 재배선, one-shot 멤버 한정 복원), authCopy.ts (intro.ctaLoading/error 삭제) |
| 3 | 시뮬레이터 스모크 + 증적 | ef07bb2a | screens/ 70~76 7장 |

## Machine Gates (실측 결과)

| Gate | 결과 |
| ---- | ---- |
| `npx tsc --noEmit` | PASS — 0 에러 (Task 1 커밋 시점, Task 2 커밋 시점 각각) |
| `node --test src/lib/__tests__/*.test.ts src/lib/__tests__/*.test.mjs` | PASS — **212 passed / 0 failed** (변경 전 기준선도 212/0 — 아래 주 1) |
| grep: index.tsx `router.push('/auth/login')` 있음 / `signInAnonymously` 없음 / `isAnonymous` 있음 | PASS |
| grep: login.tsx `signInAnonymously`·`dismissAll`·`hasSeenTutorial` 있음 | PASS |
| grep: authCopy.ts `guestCta` 있음, `^\s+ctaLoading:`·`^\s+error:` 없음 | PASS (Task 2 커밋 후 시점) |
| 소셜 로그인 경로(onProviderPress) diff | 0줄 (import 정렬 컨텍스트 외 변경 없음) |
| 하드 제약: 이모지 0 / 화면 파일 한국어 리터럴 0 / 색·간격 하드코딩 0(토큰만, marginTop 32 는 계획 명시값) / '/' 경로 리터럴 0 | PASS |
| screens/ PNG >= 4장 | PASS — 7장 |

**주 1 — 테스트 기준선 수치:** 실행 프롬프트의 "191 passed" 는 낡은 수치. 변경 전 실측 기준선이 이미 **212 passed / 0 failed** 였고(테스트가 이후 추가됨), 변경 후에도 212/0 유지 — 회귀 0. 또한 `node --test src/lib/__tests__` (디렉터리 인자) 형태는 Node v24.15.0 에서 MODULE_NOT_FOUND 로 실패한다 — 명시적 glob 인자로 실행해야 한다.

## 시뮬레이터 실측 (iPhone 16 Pro, iOS 18.6, 2026-08-31자 dev build + 현재 번들)

screens/ 증적 7장:

| 파일 | 검증 내용 | 판정 |
| ---- | -------- | ---- |
| 70-intro.png | 인트로 레이아웃 불변 (시작하기 + 하단 로그인 링크) | PASS |
| 71-login-gate.png | 시작하기 탭 → 로그인 화면. 소셜 타일(Google/Apple) + 게스트로 시작하기 버튼 + 하단 회원가입 링크 **3구성 한 화면**, 뒤로가기 화살표 존재 | PASS |
| 72-back-to-intro.png | 화살표 탭 → 인트로 복귀 | PASS |
| 73-after-guest.png | 게스트로 시작하기 1탭 → 홈 진입 (튜토리얼 기시청 기기) | PASS |
| 74-relaunch-gate.png | 앱 종료 후 재기동 → **익명 세션이 있는데도 인트로 게이트 노출** (자동 홈 진입 없음) — belle 불만의 직접 검증 | PASS |
| 75-first-run-guest-tutorial.png | 초기화 상태에서 게스트 진입 → 튜토리얼 표시 (첫 실행 분기) | PASS |
| 76-tutorial-exit-home.png | 튜토리얼 건너뛰기 → **홈 도착** (인트로로 새지 않음 — dismissAll 스택 위생 검증) | PASS |

**uid 불변 (게스트 기록 유지) — AsyncStorage 직접 판독:**

- 재사용 런(73/74): 판독된 authUser = uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2`, isAnonymous true, **createdAt 2026-07-30** — 게스트 버튼 탭 후에도 7월 생성 세션이 그대로 (신규 생성이면 createdAt 이 당일이어야 함) → `signInAnonymously` 세션 재사용 실증.
- 대조 런(75/76, 데이터 초기화 후): 신규 uid `k9fQlhw2Picwql31ooLlmmAcwbm2`, **createdAt 2026-09-01T08:28Z** (버튼 탭 순간) → 신규 게스트 생성 경로도 정상.
- 계획의 "홈/마이 탭 기록 표시 육안 확인" 대신 이 판독을 썼다 — uid 동일성이 쟁점이고 저장된 authUser 가 그 사실 자체다.

**관측(결함 아님):** 73 캡처 시점 홈의 기준 동작 리스트가 빈 폴백("기준 동작이 곧 추가돼요")이었으나, 76 에서 동일 홈이 기준 동작 3건 + NEW 배너를 정상 표시 — 73 은 진입 ~5초 시점의 로딩 중 상태였을 뿐. 이 계획의 변경 범위(라우팅/게이트)와 무관.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] intro.ctaLoading/error 삭제를 Task 2 커밋으로 이동**
- **Found during:** Task 1 착수 시 계획 내적 모순 발견
- **Issue:** Task 1 이 authCopy.intro 키 2개를 삭제하는데 소비처 index.tsx 는 Task 2 에서야 갱신됨 — Task 1 자체의 verify(tsc)가 깨지는 순서
- **Fix:** 삭제(및 intro 섹션 주석 갱신)를 소비처가 사라지는 Task 2 커밋에 포함. 최종 상태는 계획과 동일하며 두 커밋 모두 typecheck 녹색 유지
- **Files modified:** app/src/constants/authCopy.ts
- **Commit:** 7d72dda6

### 관측/우회 (코드 무변경)

**2. 시뮬 증적용 2번째 기기(iPhone 16) 포기 — 구식 빌드**
- 첫 실행 시나리오(75)를 iPhone 16(7B3A411E)에서 하려 했으나 설치된 dev build 가 7월 24일자로 `ExpoCrypto` 네이티브 모듈 부재(소셜 로그인 08-31 추가분) → 현재 번들 로드 시 Uncaught Error. 메모리의 "네이티브 모듈 추가 = 재빌드 필요" 그대로.
- 대신 계획이 명시한 "앱 데이터 초기화 ... uid 확인과는 별 런으로"에 따라 **iPhone 16 Pro 의 AsyncStorage 를 uid 검증 완료 후 초기화**해 75/76 을 같은 기기에서 실행.
- 부작용(공개): (a) 16 Pro 의 7월 게스트 세션(fvcNX...)은 초기화로 소멸, 현재 기기 상태 = 신규 게스트(k9fQ..., tutorial_seen=true). (b) iPhone 16(7B3A411E)의 AsyncStorage 도 시도 과정에서 초기화됨 — 해당 기기는 구식 빌드라 어차피 현재 번들 실행 불가, 실사용 상태 아님.

또한 실행 프롬프트가 지목한 `mcp__ios-simulator__*` 툴은 이 에이전트 환경에 노출되지 않아 `idb`(tap) + `xcrun simctl`(boot/launch/screenshot) 로 동일 검증을 수행했다.

## Known Stubs

None — 이 계획이 추가한 UI 는 전부 실동작에 배선됨 (게스트 버튼 → signInAnonymously → 라우팅). 하드코딩 빈 값/placeholder 신설 없음.

## Threat Flags

없음 — 신규 네트워크 표면/의존성 0. 계획 threat_model 그대로: T-q260901-02(스택 위생)는 dismissAll 구현으로 mitigate 완료(76 증적), T-q260901-01(세션 재사용)은 accept(AsyncStorage 판독으로 signOut/재발급 없음 확인).

## Next Steps / belle 확인 대기

- 계획 human-check: **71(3구성)·74(재실행 게이트) 스크린샷이 belle 이 요청한 모습인지 확인** 필요.
- push 여부는 belle 승인 후 (미푸시 푸시 여부 항목이 이미 belle 몫으로 열려 있음 — 이번 3커밋도 로컬에만 있음).

## Self-Check: PASSED

- [x] app/src/constants/authCopy.ts — FOUND (guestCta 3키, intro 2키 삭제 확인)
- [x] app/src/app/auth/login.tsx — FOUND (게스트 버튼/핸들러/dismissAll)
- [x] app/src/app/index.tsx — FOUND (push 재배선/one-shot/isAnonymous)
- [x] screens/ 7장 — FOUND (70~76)
- [x] 커밋 a2a1f585 — FOUND
- [x] 커밋 7d72dda6 — FOUND
- [x] 커밋 ef07bb2a — FOUND
