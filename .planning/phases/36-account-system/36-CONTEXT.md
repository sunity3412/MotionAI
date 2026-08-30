# Phase 36 CONTEXT — 계정 시스템 (게스트 유지 + 소셜 로그인 4종)

> 결정과 실측만. 내 추정은 "내 해석:" 으로 표시.

---

## D-01 · belle 결정 (락인, 재론 금지)

| 일자 | 원문 | 귀결 |
|---|---|---|
| 08-28 | "게스트 유지 + 로그인 추가" | 게스트 동선은 한 걸음도 늘리지 않는다 |
| 08-28 | "디자인은 피그마를 따라줘" (카피는 논의 후) | UI 정본 = Figma. 문구는 **상수 1곳**으로 빼서 나중에 한 번에 교체 |
| 08-28 | "간편로그인은 같은 dev 폴더 funding 쪽에서 이미 하고 있어서 설계는 편할 거야" | funding 은 **참고본**. 코드 이식 불가(Next.js/Spring/EC2 vs RN/Lambda/Firebase) |
| 08-28 | "아이디는 같은 아이디를 쓰면 돼, 비즈니스 계정이니까" | funding 이 등록한 **콘솔 앱에 모바일 플랫폼만 추가**. 심사 없음. 사용자 계정 통합(sunity.ai SSO)은 이 phase 밖 — CLAUDE.md §3 상 Motion 은 funding EC2 를 호출하지 않는다 |
| 08-30 | 범위 = **소셜 4종만** | 이메일 가입 STEP01/02 · 비밀번호 찾기 · Face ID = 이번 범위 밖 |
| 08-30 | 인트로 = **Figma 레이아웃 그대로** | "시작하기" = 게스트 진입(현행 동작), "로그인하기" = 로그인 화면. 가입 진입점 = 로그인 화면 하단 + 마이 탭 |

---

## D-02 · Figma 실측 (fileKey `jrdI7kp245HkPfLB0nclsz`, page `0:1`)

계정 시스템 전체 화면 — **인계 노트(CONTINUE-2026-08-29)가 4개라 한 것보다 많다.**

### 이번 범위 (구현)

| 화면 | 노드 | 실측 내용 |
|---|---|---|
| 인트로 | `1:142` | 사진 배경(`athletic-man-jumping-air-steam 1`) + Sunity 로고 + 구분선 + "프로의 동작과 비교하는 / **나만의 AI 운동 코치**" + 반투명 "시작하기" + "이미 계정이 있으신가요? <brand>로그인하기</brand>" |
| 로그인(소셜) | `1:550` | 연분홍 배경 + 로고 + "희연님, 오늘도 한 발 더!" + "WELCOME BACK" + **정사각 아이콘 4개**(카카오/네이버/Google/Apple, 40.7pt) + 구분선 + "이메일 로그인" + 하단 "처음 오셨나요? <brand>회원가입</brand>" |
| 가입(소셜) | `1:961` | 흰 배경 + "시작해 볼까요?" + "3초만에 가입하고 / 나만의 AI 코치를 만나보세요." + **전폭 버튼 4개**(330×54, 72.24pt 간격) + 밑줄 "이메일로 가입하기" + 하단 "가입 시 서비스 <brand>이용약관</brand>과 <brand>개인정보 처리방침</brand>에 동의하게 됩니다." |

### 이번 범위 밖 (다음 기회 — 노드만 박제)

| 화면 | 노드 |
|---|---|
| 로그인(이메일) | `1:581` — 이메일/비번 + **자동로그인** 체크 + 비밀번호 찾기 |
| 로그인(Face ID) | `1:605` |
| 가입 STEP01 | `1:987`(기본) · `1:1005`(확인됨) · `1:1025`(오류) — **검증 3상태** |
| 가입 STEP02 | `1:1043`(미동의) · `1:1072`(전체동의) — 약관 5항목([필수]3 + [선택]2) |
| 비밀번호찾기 | `1:374` · `1:394` · `1:415` |

### 계정 아님 (온보딩 — phase 밖)

레벨 `1:611`(입문 `1:612` / 중급 `1:629`) · 종목선택 `1:646`(`1:650` / `1:675` / `1:694`).
현행 앱은 인트로 주석대로 "회원가입/로그인/레벨/플랜 스킵" 상태이며, 파일럿 요건
(CLAUDE.md §2)에도 레벨 입력이 없다.

### Figma 자체 결함 (구현 시 정정)

- 약관 화면(`1:1043`/`1:1072`) 상단 라벨이 **"STEP 01 / 02"** 로 STEP01 과 같다 — 02 여야 함.
  (범위 밖이지만 다음 사람이 그대로 베끼지 않게 기록)

---

## D-03 · 현행 앱 실측

- `app/src/app/index.tsx` — 브랜드 그라디언트 전체화면 + "게스트로 시작하기" 단일 CTA.
  `onAuthStateChanged` 가 라우팅 담당(게스트 세션 복원 시 `bootstrapping` 으로 CTA 보류).
  진입 후 `hasSeenTutorial()` 로 `/tutorial` or `/(tabs)` 분기.
- `app/src/lib/firebase.ts` — firebase JS SDK v12, `initializeAuth` + AsyncStorage 영속,
  `globalThis.__sunityAuth` 캐시. **익명 인증만 사용 중.**
- `app/src/app/(tabs)/profile.tsx` — 헤더 부제가 "파일럿 게스트 모드" 고정.
- `app/src/theme/colors.ts` — **`sns` 토큰이 이미 있다**
  (`kakao #FEE500` / `naver #03C75A` / `google #FFFFFF+border` / `apple #000000`).
  디자인 시스템이 이 phase 를 미리 예약해 둔 상태 — 신규 컬러 토큰 불필요.
- `app/package.json` — 인증 관련 의존성 **0** (`expo-auth-session`·`expo-apple-authentication`·
  google-signin 모두 없음). `expo-dev-client` 는 있음 → 네이티브 모듈 추가 가능.
- `app/app.json` — `scheme: "sunityaicoach"`, bundle `com.sunity.aicoach`.

---

## D-04 · Firebase 실측 (2026-08-30, MCP `firebase_list_apps`)

```
projects/sunity-ai-coach/webApps/1:965554697584:web:77407108c7476e65b4cbb5  (WEB, ACTIVE)
```

**iOS 앱 미등록 · Android 앱 미등록 — 웹 앱 하나뿐.**

귀결 (내 해석): "Google·Apple 은 콘솔 대기 없이 착수 가능"이라던 인계 노트의 전제는
**부분적으로 틀리다**. 다음이 선행돼야 한다.

1. Firebase 프로젝트에 **iOS 앱 등록** (→ iOS OAuth client ID + reversed client ID URL 스킴).
   내가 MCP `firebase_create_app` 으로 실행 가능.
2. Firebase Authentication → **Google provider 활성화**. 콘솔 토글 또는 Identity Toolkit
   Admin API. 실패 시 belle 콘솔 작업으로 이관.
3. Firebase Authentication → **Apple provider 활성화**.
4. Apple Developer → App ID `com.sunity.aicoach` 에 **Sign in with Apple capability** —
   belle 소유 계정 작업 (memory `apple-dev-delegated-to-agency`).

---

## D-05 · funding 참고본 실측 (`/Users/kimtaesung/Dev/Sunityfunding`)

- 소셜 4종 실 OAuth 가 **웹에서 이미 작동 중** — `sunity-web/src/app/auth/page.tsx`
  (`provider`/`providerId` 계약, `naver`/`kakao`/`google`/`apple` 4분기, 팝업
  `window.opener.postMessage` 수신).
- 등록된 콘솔 앱 (env 키 이름으로 확인, 값은 읽지 않음):
  `NEXT_PUBLIC_KAKAO_APP_KEY` · `NEXT_PUBLIC_GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` ·
  `NEXT_PUBLIC_APPLE_SERVICE_ID` · 네이버는 코드 내 `LoginWithNaverId`
  (`callbackUrl: "https://sunity.ai/auth/naver"`).
  → **전부 웹 플랫폼 등록.** 모바일(iOS) 플랫폼 추가가 belle 콘솔 작업의 실체.
- 약관 원문이 funding 에 존재: `/terms?tab=terms` · `?tab=privacy` · `?tab=marketing`.
  가입 화면 하단 링크의 목적지 후보. **단, 폴 영상·자세 데이터 수집이 그 약관에
  덮여 있는지는 확인 안 됨(법무 항목, belle).**

---

## D-06 · 기술 경로 (내 해석 — 실행 중 검증)

| provider | 경로 | 서버 필요 |
|---|---|---|
| Google | `@react-native-google-signin/google-signin` → idToken → `GoogleAuthProvider.credential` → `signInWithCredential` | 없음 |
| Apple | `expo-apple-authentication` → identityToken + rawNonce → `OAuthProvider('apple.com')` → `signInWithCredential` | 없음 |
| 카카오 | `expo-auth-session` 인가코드 → **신규 Lambda `POST /auth/social`** → 토큰 검증 → `createCustomToken` → `signInWithCustomToken` | 있음 |
| 네이버 | 동일 | 있음 |

근거: Expo 공식 문서가 Google 은 `expo-auth-session` 대신
`@react-native-google-signin/google-signin` 을 권장한다 ("AuthSession 은 브라우저 기반
범용 OAuth 도구"). Apple 은 `expo-apple-authentication` + config plugin 이 정본.

**미검증 (실행 중 확인할 것):** 카카오·네이버가 커스텀 스킴(`sunityaicoach://`)을
Redirect URI 로 받는지. 안 되면 (a) https 중계 페이지 or (b) 네이티브 SDK
(`@react-native-seoul/kakao-login` 등)로 우회. 이 갈래가 카카오·네이버 plan 의 첫 태스크.

**게스트 승계:** `linkWithCredential(auth.currentUser, credential)` — uid 불변이라
`users/{uid}/analyses` 기록이 그대로 살아난다. 예외 경로 `auth/credential-already-in-use`
(이미 가입된 소셜 계정으로 로그인) 의 처분은 plan 에서 정의.

---

## D-07 · belle 판정 (2026-08-30 3건 해소, 2건 잔여)

### 해소

1. **인트로 배경 = Figma 를 따른다** — "피그마를 따르자. 근데 이미지가 폴스포츠가 아니기
   때문에 magnific 한번 연결해서 폴스포츠로 쓸만한걸로 변경해도 좋을 듯."
   → 사진 배경 유지, **사진만 교체**. 후보 6장(생성 4 + 스톡 실사 2)을 실제 앱 화면에
   걸어 찍어 비교 → **C 확정**(커밋 1f124579). 출처·프롬프트·비용 = `36-ASSETS.md`.
   ※CLAUDE.md §4 "다크 배경 금지"와의 충돌은 belle 이 이 화면에 한해 Figma 우선으로 판정.
   튜토리얼 화면의 같은 충돌은 **아직 별건으로 남아 있다**.
2. **로그인 배경 = Figma 그대로** — "로그인 배경 : 피그마로 쫙" → `#FFEDEA` 유지.
   구현이 이미 그러해서 변경 0.
3. **인사말 "희연" 자리 = 가입한 실명 또는 아이디** — "3번은 나중에 회원가입한 실명 또는
   아이디로 반영하는 거이 '희연' 자리는". → `authCopy.login.greetingWithName`
   (`{name}님, 오늘도 한 발 더!`) 템플릿 유지, **36-02 에서 로그인 표시 이름을 물려 넣는다**.
   계정이 없는 상태(게스트/최초 진입)에서만 `greetingNoName` 이 나간다.

### 잔여

4. **약관 링크 목적지** — funding 에 `/terms?tab=terms|privacy|marketing` 이 있다.
   **영상·자세 데이터를 그 약관이 덮는지 미확인**(법무). 확인 전까지 링크는 강조만 하고
   이동하지 않는다.
5. **나머지 카피** — 가입 부제 "3초만에 가입하고…"(마케팅 톤) vs 현재 앱 기대설정 톤.
   전량 `authCopy.ts` 한 곳이라 배선 후 한 번에 봐도 비용 0.
6. **`credential-already-in-use`** — 이미 가입된 소셜 계정으로 로그인할 때 게스트 기록
   처분. 36-02 에서 정의.

## D-08 · 범위 밖 링크 처분 (내 결정)

Figma 의 "이메일 로그인"(`1:550`) · "이메일로 가입하기"(`1:961`) 는 이번 범위 밖이다.
**비활성 링크로 남기지 않고 렌더하지 않는다** — Phase 33 원칙 "표시마다 답 or 없앰"
(눌러도 아무 일 없는 것이 가장 나쁘다). 범위가 열리면 그 자리에 되살린다.
