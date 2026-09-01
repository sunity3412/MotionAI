---
phase: quick-260901-nms
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/constants/authCopy.ts
  - app/src/app/auth/login.tsx
  - app/src/app/index.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "세션 없는 첫 실행: 인트로 '시작하기' 탭 → 로그인 화면으로 이동한다 (즉시 게스트 로그인되지 않는다)"
    - "로그인 화면에 로그인(소셜 타일) / 회원가입 링크 / '게스트로 시작하기' 버튼 3요소가 모두 보인다"
    - "'게스트로 시작하기' 1탭 → 익명 로그인 → 튜토리얼 미시청이면 /tutorial, 시청했으면 /(tabs) 진입 — 가입 벽 없음 (CLAUDE.md §2)"
    - "영속 익명(게스트) 세션이 있는 기기에서 재실행해도 자동 홈 진입하지 않고 인트로→로그인 게이트가 보인다"
    - "게스트가 게이트를 다시 통과해도 uid 가 바뀌지 않는다 (기존 익명 세션 재사용 — 분석 기록 유지)"
    - "멤버(소셜 연동/로그인) 세션은 기존대로 인트로에서 자동 홈 진입한다"
    - "첫 실행 게스트가 튜토리얼을 끝내면 홈으로 간다 — 인트로로 되돌아가지 않는다"
  artifacts:
    - path: "app/src/app/auth/login.tsx"
      provides: "게스트로 시작하기 버튼 + 게스트 진입 라우팅(튜토리얼 분기 포함)"
      contains: "signInAnonymously"
    - path: "app/src/app/index.tsx"
      provides: "시작하기 → /auth/login push, 멤버 세션만 자동 진입하는 one-shot 복원 판정"
      contains: "router.push('/auth/login')"
    - path: "app/src/constants/authCopy.ts"
      provides: "게스트 버튼 카피 (guestCta / guestCtaLoading / guestError)"
      contains: "guestCta"
  key_links:
    - from: "app/src/app/index.tsx"
      to: "/auth/login"
      via: "CTA onPress router.push"
      pattern: "router\\.push\\('/auth/login'\\)"
    - from: "app/src/app/auth/login.tsx"
      to: "firebase/auth signInAnonymously"
      via: "게스트 버튼 핸들러"
      pattern: "signInAnonymously"
    - from: "app/src/app/auth/login.tsx"
      to: "app/src/lib/onboarding.ts"
      via: "hasSeenTutorial 튜토리얼 분기"
      pattern: "hasSeenTutorial"
---

<objective>
로그인 화면을 앱의 첫 관문으로 만든다. 인트로(Figma 1:142, 레이아웃 불변)의 "시작하기"가
즉시 게스트 로그인하는 대신 로그인 화면(Figma 1:550)으로 보내고, 로그인 화면에
"게스트로 시작하기" 버튼을 추가해 로그인(소셜)/회원가입/게스트 3개 구성을 완성한다.

근거: belle 2026-09-01 — "아예 로그인화면에서 게스트 로그인을 달고 진행해야할거 같아",
"보통 로그인과 회원가입이 있을거아녀". 이 지시는 belle 08-30 결정("'시작하기'=게스트
진입 그대로", index.tsx 헤더 주석·STATE.md에 기록됨)을 **명시적으로 대체**한다.
실측 우선 원칙: 새 belle 지시 > 이전 결정 기록. 관련 파일의 낡은 주석도 같이 갱신한다.

설계 지점 3건의 결론 (이 계획이 답):
1. **영속 게스트 세션** — 익명 세션은 더 이상 인트로를 자동 통과하지 않는다. 복원 판정:
   비익명(멤버) 세션만 자동 홈 진입, 익명/무세션은 인트로 CTA 노출. 게스트 불이익 없음:
   `signInAnonymously` 는 익명 세션이 이미 있으면 **그 사용자를 그대로 반환**(Firebase JS
   SDK 문서 명시 동작)하므로 uid 불변 = `users/{uid}/analyses` 기록 유지. signOut 절대 금지.
   CLAUDE.md §2 충족: 게스트는 게이트에서 버튼 1탭, 가입 벽 없음.
2. **뒤로가기 화살표** — 유지. 로그인 화면은 여전히 push 로만 진입한다(인트로 또는 마이 탭).
   문자 그대로의 첫 화면은 인트로가 유지되므로 router.back() 대상이 항상 존재한다.
3. **튜토리얼 분기** — 게스트 진입 경로를 따라 로그인 화면으로 이동한다. 게스트 버튼 성공 시
   `hasSeenTutorial()` 분기(미시청 → /tutorial, 시청 → /(tabs)). 인트로에는 멤버 복원용
   분기만 남는다. 소셜 로그인 성공 라우팅(`replace('/(tabs)')`)은 **건드리지 않는다** —
   어제(260831-my-tab-login-entry) belle 이 실기기로 확인한 경로다 (과잉 일반화 금지).

인트로 하단 "이미 계정이 있으신가요? 로그인하기" 링크: **유지**. CTA 와 같은 목적지로
수렴하지만 Figma 1:142 충실도(belle "디자인은 피그마를 따라줘")가 우선이고, 계정 보유자
멘탈모델에 맞는 문구라 해롭지 않다. 코드 주석으로 의도적 수렴임을 남긴다.

Output: 수정된 3파일 + 시뮬레이터 스크린샷 증적 (.planning/quick/260901-nms-login-gate-guest/screens/)
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@design.md (§5-3 CTA, §9 버튼 피드백 opacity 0.4, 스피너 금지)
@app/src/app/index.tsx
@app/src/app/auth/login.tsx
@app/src/constants/authCopy.ts
@app/src/lib/onboarding.ts
@app/src/app/tutorial.tsx (종료 로직 canGoBack 분기 — 아래 스택 위생 절 참조)
</context>

<critical_routing_facts>
실측된 함정 2건 — 위반하면 눈에 보이는 결함이 된다:

1. **경로 '/' 금지.** 인트로와 홈이 '/' 를 공유하며 `router.replace('/')` 는 홈으로 간다
   (2026-08-31 실측). 이 계획의 어떤 코드에도 '/' 경로 리터럴을 쓰지 말 것.
   인트로 명시 이동이 필요한 경우는 이 계획에 없다.

2. **스택 위생 — 튜토리얼 이탈 결함.** `app/src/app/tutorial.tsx` 종료 로직은
   `router.canGoBack() ? router.back() : router.replace('/(tabs)')` 다. 게스트 진입이
   push 된 로그인 화면에서 일어나면 스택이 [intro, login] 이고, 여기서 그냥
   `replace('/tutorial')` 하면 스택이 [intro, tutorial] 이 되어 canGoBack()===true →
   **첫 실행 게스트가 튜토리얼을 끝내면 홈이 아니라 인트로로 떨어진다.** 그래서 게스트
   라우팅은 replace 전에 `router.canDismiss()` 이면 `router.dismissAll()` 로 스택을
   루트(인트로)까지 걷어낸 뒤 replace 한다 → 스택 [tutorial] 단독, canGoBack false →
   튜토리얼 종료가 홈으로 간다. tutorial.tsx 자체는 수정하지 않는다.
</critical_routing_facts>

<tasks>

<task type="auto">
  <name>Task 1: authCopy 게스트 카피 + 로그인 화면에 게스트로 시작하기 버튼</name>
  <files>app/src/constants/authCopy.ts, app/src/app/auth/login.tsx</files>
  <action>
  **authCopy.ts** — `login` 섹션에 3키 추가: `guestCta: '게스트로 시작하기'`,
  `guestCtaLoading: '시작하는 중...'`, `guestError: '연결에 실패했어요. 잠시 후 다시 시도해주세요.'`
  (guestCtaLoading/guestError 문구는 기존 intro.ctaLoading/intro.error 를 그대로 승계 —
  게스트 로그인 행위가 인트로에서 로그인 화면으로 옮겨가는 것이므로 문구도 따라간다).
  `intro` 섹션에서 `ctaLoading` 과 `error` 키를 **삭제**한다 — Task 2 이후 소비처가 없다
  (소비처 전수: index/login/signup/profile/legal 5파일, 테스트는 authCopy 미참조 — 실측 완료).
  intro/login 섹션 주석에 belle 2026-09-01 결정(로그인 화면=첫 관문, 게스트 포함 3구성)을
  1-2줄로 기록하고 08-30 결정을 대체한다고 명시.

  **login.tsx** — 변경 4건:
  1. import 추가: `signInAnonymously`(firebase/auth), `auth`(../../lib/firebase),
     `hasSeenTutorial`(../../lib/onboarding), 테마의 `layout`.
  2. 게스트 라우팅 helper `routeAfterGuest` (컴포넌트 내부 async 함수): `hasSeenTutorial()`
     결과 seen 을 받아, 먼저 `router.canDismiss()` 이면 `router.dismissAll()` 호출(위
     critical_routing_facts #2 — 인트로가 스택에 남아 튜토리얼 종료가 인트로로 새는 결함
     차단), 그 뒤 `router.replace(seen ? '/(tabs)' : '/tutorial')`. 주석으로 스택 위생
     이유를 남긴다.
  3. 게스트 버튼 핸들러 `onGuestPress`: `setNotice(null)`, `setBusy(true)`, try 에서
     `await signInAnonymously(auth)` 후 `await routeAfterGuest()`, catch 에서
     `setNotice(authCopy.login.guestError)`, finally 에서 `setBusy(false)`.
     주석 2건 필수: (a) 익명 세션이 이미 있으면 signInAnonymously 가 같은 사용자를
     반환한다(Firebase JS SDK 문서 동작) — uid 불변이라 게스트 기록이 유지된다는 사실,
     (b) 멤버 세션 방어 분기를 두지 않는 이유 — 멤버는 인트로에서 자동 진입하고 마이 탭은
     멤버에게 로그아웃만 노출하므로 이 화면에 멤버 상태로 도달하는 경로가 없다.
  4. UI: `tileRow` 아래(notice 위)에 전폭 아웃라인 보조 버튼. 스타일은 화면 로컬 StyleSheet
     에 토큰만으로: height `layout.ctaHeight`, borderRadius `radius.button`, borderWidth 1,
     borderColor `colors.inputBorder`, 배경 transparent, `alignSelf: 'stretch'`,
     alignItems/justifyContent center, marginTop 32(타일 리듬 48 과 하단 여백 사이 중간값 —
     미설계 요소라 화면 기존 톤 안에서 자체 판단, design.md 근거). 라벨은
     `typography.boxLabel` + `colors.textPrimary`, busy 이면 `authCopy.login.guestCtaLoading`
     아니면 `authCopy.login.guestCta`. Pressable 은 기존 `pressed`(opacity 0.6) 스타일 재사용,
     `disabled={busy}`, `accessibilityRole="button"`,
     `accessibilityLabel={authCopy.login.guestCta}`, `accessibilityState={{ disabled: busy }}`.
     위계 근거: 소셜 타일(주 행동)보다 낮고 하단 caption 링크보다 높은 3번째 요소 —
     파일럿에서 수강생 대부분이 게스트로 들어오므로 텍스트 링크로 숨기지 않는다.
  5. 파일 헤더 주석의 "Figma 대비 의도적 차이" 목록에 3번 항목 추가: 게스트 버튼은
     Figma 1:550 에 없는 신규 요소 — belle 2026-09-01 결정(로그인 화면=첫 관문, 3구성).
     뒤로가기 화살표 항목(#2)의 근거 문장은 그대로 유효하므로 유지(인트로가 여전히 첫
     화면이고 이 화면은 push 로만 진입).

  소셜 로그인 성공/switched 라우팅과 onProviderPress 는 **한 줄도 바꾸지 않는다**
  (어제 belle 실기기 확인 경로). 이모지 금지, 한국어 리터럴은 authCopy 로만, 색·간격
  하드코딩 금지(토큰만).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npx tsc --noEmit && grep -q "guestCta" src/constants/authCopy.ts && ! grep -qE "^\s+ctaLoading:" src/constants/authCopy.ts && ! grep -qE "^\s+error:" src/constants/authCopy.ts && grep -q "signInAnonymously" src/app/auth/login.tsx && grep -q "dismissAll" src/app/auth/login.tsx && grep -q "hasSeenTutorial" src/app/auth/login.tsx</automated>
  </verify>
  <done>typecheck 0 오류. login.tsx 에 게스트 버튼(핸들러+접근성+busy 상태) 존재, 게스트 성공 경로가 dismissAll 후 tutorial/(tabs) 분기. authCopy.login 에 guestCta 3키, authCopy.intro 에서 ctaLoading/error 제거. 소셜 로그인 경로 diff 0줄.</done>
</task>

<task type="auto">
  <name>Task 2: 인트로 시작하기 → 로그인 게이트, 멤버 세션만 자동 진입</name>
  <files>app/src/app/index.tsx</files>
  <action>
  index.tsx 변경 3건 (Figma 1:142 레이아웃·스타일은 불변):

  1. **CTA 재배선**: `startAsGuest`/`signInAnonymously` import/`status` state 를 제거하고
     CTA onPress 를 `router.push('/auth/login')` 로 바꾼다. push 인 이유(주석 필수):
     로그인 화면의 뒤로가기 화살표가 인트로로 복귀할 수 있어야 한다. CTA 는 더 이상
     비동기가 아니므로 loading 라벨·disabled 분기 삭제, 라벨은 `authCopy.intro.cta` 단독.
     pressed dim 스타일(ctaDimmed)은 눌림 피드백으로 유지.
  2. **복원 판정을 one-shot + 멤버 한정으로**: onAuthStateChanged 콜백을 첫 발화 1회만
     처리한다(effect 클로저에 `let handled = false` 가드 — 자기-unsubscribe 패턴은 초기화
     전 참조(TDZ) 위험이 있어 쓰지 않는다; useEffect 반환값의 unsubscribe 는 언마운트
     정리용으로 유지). 첫 발화에서: `user && !user.isAnonymous`(멤버)면 기존
     `hasSeenTutorial().then(seen => router.replace(seen ? '/(tabs)' : '/tutorial'))` 실행,
     그 외(익명 세션 또는 무세션)면 `setBootstrapping(false)` 로 CTA 노출.
     one-shot 이유(주석 필수): 로그인 화면이 push 로 위에 얹힌 동안 인트로가 살아있으므로,
     이후의 auth 변화(소셜 로그인·switched)에 인트로가 반응해 라우팅을 가로채면
     로그인 화면의 notice(특히 switched 안내)를 선점 이탈시킨다 — 진입 후 라우팅의
     소유권은 로그인 화면에 있다.
  3. **주석 갱신**: 파일 헤더의 08-30 결정 기록("'시작하기' = 게스트 진입 그대로")을
     belle 2026-09-01 결정으로 대체 — "시작하기 = 로그인 게이트로 이동(게스트 버튼은
     로그인 화면에), 익명 세션은 자동 진입하지 않음(로그인 입구 상시 노출), 멤버 세션만
     자동 진입". 다크 배경 belle 판정 대기 항목(D-07 #1) 문단은 그대로 둔다.
     하단 "이미 계정이 있으신가요? 로그인하기" 링크는 유지하되, CTA 와 같은 목적지로
     의도적으로 수렴한다는 1줄 주석 추가(Figma 1:142 충실도 우선).

  bootstrapping state 와 CTA 숨김(스플래시 패턴, 스피너 금지 §0)은 유지 — 멤버 자동
  진입 판정 전 깜빡임 방지가 여전히 필요하다. '/' 경로 리터럴 사용 금지
  (critical_routing_facts #1). status==='error' 표시 블록은 CTA 가 비동기 작업을 잃으므로
  함께 제거(하단 줄은 haveAccount+loginLink 상시 표시로 단순화).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npx tsc --noEmit && grep -q "router.push('/auth/login')" src/app/index.tsx && ! grep -q "signInAnonymously" src/app/index.tsx && grep -q "isAnonymous" src/app/index.tsx && node --test src/lib/__tests__</automated>
  </verify>
  <done>typecheck 0 오류, 앱 단위 테스트 191 passed / 0 failed 유지. index.tsx 에서 signInAnonymously 소멸, CTA 가 /auth/login push, 복원 판정이 isAnonymous 로 멤버만 자동 진입. 인트로 스타일 diff 는 error 블록 제거 외 0.</done>
</task>

<task type="auto">
  <name>Task 3: 시뮬레이터 스모크 + 증적 캡처</name>
  <files>.planning/quick/260901-nms-login-gate-guest/screens/</files>
  <action>
  실측 원칙(메모리: "UI 변경은 시뮬 확인 후 배포 — typecheck 는 렌더 크래시 못 잡음",
  260831-my-tab-login-entry 의 screens/ 증적 선례)에 따라 iOS 시뮬레이터로 스모크:

  1. `cd app && npx expo start` 로 iOS 시뮬레이터 기동 (기존 개발 빌드/Expo Go 중 이 앱이
     실행 가능한 쪽 — 어제 세션과 같은 방법).
  2. 검증 시나리오와 캡처(`xcrun simctl io booted screenshot` → 계획 디렉터리 screens/):
     - 70-intro.png: 인트로 — 레이아웃 불변(시작하기 + 하단 로그인 링크).
     - 71-login-gate.png: 시작하기 탭 → 로그인 화면 — 소셜 타일 / 게스트로 시작하기 버튼 /
       하단 회원가입 링크 3구성이 한 화면에 보임. 뒤로가기 화살표 존재.
     - 72-back-to-intro.png: 화살표 탭 → 인트로 복귀.
     - 73-after-guest.png: 게스트로 시작하기 탭 → 홈(기시청 기기) 진입.
     - 74-relaunch-gate.png: 앱 재실행(시뮬레이터 앱 종료 후 재기동) → 익명 세션이
       있는데도 인트로가 다시 보임(자동 홈 진입 없음) — belle 불만의 직접 검증.
     - 75-tutorial-exit.png (가능하면): AsyncStorage 튜토리얼 플래그가 없는 상태
       (앱 데이터 초기화 또는 신규 시뮬레이터)에서 게스트 진입 → 튜토리얼 표시 →
       종료 → 홈 도착(인트로로 새지 않음 — 스택 위생 검증). 초기화가 세션까지 지우므로
       uid 확인과는 별 런으로.
  3. uid 보존 확인: 73 진입 전후로 같은 uid 인지 — 홈/마이 탭 기록 표시가 유지되는지
     육안 확인(기록이 비면 uid 가 바뀐 것 — 즉시 결함).

  시뮬레이터 자동화가 막히면(개발 빌드 부재 등) 막힌 지점을 SUMMARY 에 관측 그대로 적고
  typecheck/테스트/그렙 게이트 결과만으로 마감하되 "시뮬 미검증" 을 명시한다 — 검증 안 된
  것을 검증됐다고 적지 않는다.
  </action>
  <verify>
    <automated>ls /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260901-nms-login-gate-guest/screens/*.png | wc -l | awk '{exit ($1>=4)?0:1}'</automated>
    <human-check>belle: 71(3구성) 과 74(재실행에도 게이트 노출) 스크린샷이 요청한 모습인지 확인</human-check>
  </verify>
  <done>스크린샷 4장 이상 저장(최소 70/71/73/74). 재실행 시 게이트 노출과 게스트 기록 유지가 육안 확인되거나, 불가 시 미검증 사실이 SUMMARY 에 명시됨.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 앱 → Firebase Auth | 익명/소셜 세션 생성·복원 (클라이언트 SDK 경유) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-q260901-01 | Spoofing | 게스트 세션 재사용 (login.tsx onGuestPress) | accept | Firebase 익명 인증 표준 동작. signOut/재발급 없이 기존 세션 재사용 — uid 탈취 표면 추가 없음 |
| T-q260901-02 | Tampering | 라우팅 상태 (스택 위생) | mitigate | dismissAll 후 replace 로 잔여 스택 제거 — 인증 전 화면(인트로)이 인증 후 스택에 남지 않음 |
| T-q260901-SC | Tampering | 패키지 설치 | n/a | 신규 의존성 0 (기존 firebase/auth, expo-router 만 사용) |
</threat_model>

<verification>
- `cd app && npx tsc --noEmit` → 0 오류
- `cd app && node --test src/lib/__tests__` → 191 passed / 0 failed (기준선 유지)
- grep 게이트: index.tsx 에 signInAnonymously 없음 + push('/auth/login') 있음,
  login.tsx 에 signInAnonymously·hasSeenTutorial·dismissAll 있음, 소셜 핸들러 diff 0
- 시뮬레이터 증적 screens/ 4장 이상 (막히면 미검증 명시)
- 하드 제약 준수 육안 점검: 이모지 0, 화면 파일 내 한국어 사용자 문자열 리터럴 0(전부
  authCopy 경유), 색/간격 하드코딩 0(토큰만), '/' 경로 리터럴 0
</verification>

<success_criteria>
- 세션 없음/익명 세션 기기 모두: 인트로 → 시작하기 → 로그인 화면(3구성) → 게스트 1탭 진입
- 멤버 세션: 기존대로 자동 홈 진입 (회귀 0)
- 게스트 uid 불변(기록 유지), 첫 실행 튜토리얼 종료가 홈으로 수렴
- 어제 belle 확인 경로(마이 탭 → 로그인 → 소셜) 코드 변경 0
</success_criteria>

<output>
완료 시 `.planning/quick/260901-nms-login-gate-guest/260901-nms-SUMMARY.md` 작성.
커밋 분리: Task 1 = feat(quick-260901-nms): 로그인 화면 게스트 버튼 + 카피,
Task 2 = feat(quick-260901-nms): 인트로 시작하기를 로그인 게이트로 재배선,
Task 3 = docs(quick-260901-nms): 시뮬 증적. (belle 승인 전 push 여부는 물어볼 것 —
미푸시 푸시 여부는 belle 몫 항목이 이미 열려 있음)
</output>
