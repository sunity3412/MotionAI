# 38-04 측정 로그 — 공급자 페이지 호스팅 두 후보

test_account: cath***@gmail.com (belle 지정 테스트 계정, 본계정 아님) · provider google · uid `UmH3…`
(belle "테스트 계정으로 할게" [확인 belle]; 실제 로그인한 계정은 오케스트레이터가 Firebase Auth 를 Admin SDK 로 읽기 전용 조회 [확인]. 전체 이메일·uid 는 커밋하지 않는다.)

- 측정일: 2026-09-29 (Task 1 = 실행자 자동 측정, Task 2 = belle 손 측정, Task 3 = belle 결정)
- 규칙(리뷰 R14): 두 후보를 **같은 4가지 실험**(Google 팝업 로그인 · `.mov` 선택 · presigned PUT · onSnapshot)으로 잰다.
  후보 (1) 전체 앱 export 의 성패로 후보 (2) 의 가부를 추론하지 않는다.
- 이 문서의 스크린샷·로그·export 산출물은 세션 scratchpad
  (`/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/bac3cc51-f30f-4c8e-b085-075099fcd137/scratchpad/`)
  에 있다 — **휘발성**이다. 세션이 끝나면 사라질 수 있으니 경로가 안 열리면 이 문서의 서술이 유일한 기록이다.

## 관측

잰 값·코드 사실만. 전부 이 세션 실행자가 명령을 돌려 본 것이다.

### 설치 (Task 1 step 1) — 커밋 `2807a47b`

- `npm view react-native-web` → `version = '0.21.3'`, `repository.url = 'git+https://github.com/necolas/react-native-web.git'`,
  `time.modified = 2026-09-25T15:00:31Z`, `scripts` 에 install/postinstall 없음(build/clean 류만) [확인].
- `cd app && npx expo install react-native-web` → `package.json` 에 `"react-native-web": "^0.21.0"`, lock 해석 `0.21.3`,
  "added 14 packages", 9.1초 [확인]. `slopcheck install` 미사용.
- 직후 `git status --porcelain` = `app/package.json` · `app/package-lock.json` 두 개 + 기존 `.planning/TRAINING-DUE.md`(이 작업 무관, 전부터 있던 수정) [확인].
- 홈 디렉터리: `~/package.json` · `~/package-lock.json` · `~/node_modules` · `~/node_modules/.package-lock.json` 의 mtime 을
  설치 전/후 `stat` 으로 비교 → **차이 0**(전부 2026-09-26 15:24~15:39, RESEARCH Q8 사고 때 것) [확인].
  `npm prefix` = `/Users/kimtaesung/Dev/SunityMotion/app` [확인].
- lock 의 firebase = `12.13.0` [확인] → probe CDN 버전과 같다.

### export (Task 1 step 2)

| 회차 | 조건 | exit | 소요 | 출력 전체 `du -sh` | JS 번들 | 모듈 수 |
|---|---|---|---|---|---|---|
| 1 | 웹 분기 없음(설치 직후) | 0 | 16초 | 18M | `entry-6bc2….js` 2.87 MB | 972 |
| 2 | `socialAuth.web.ts` 추가 뒤 | 0 | 7초(Metro 캐시) | 18M (`_expo` 2.7M · `assets` 16M) | `entry-1ac8….js` 2.85 MB | 956 |

- 명령: `CI=1 npx expo export --platform web --output-dir <scratchpad>/web-export[-1]` [확인]. 로그 `web-export-1.log` · `web-export.log`.
- 두 회 모두 경고·오류 줄 0(로그에서 `error` 문자열은 에셋 파일명 `expo-router/assets/error.….png` 1건뿐) [확인 grep].
- `assets` 16M 의 내역: `assets/assets/fonts` 10M(Pretendard ttf 4종 각 ~2.7 MB) · `assets/node_modules` 4.0M(@expo/vector-icons 폰트 등) ·
  `auth` 640K · `motion-thumbs` 592K · `tutorial` 200K [확인 du].
- `app.json` `web` 키는 `favicon` 만 → 출력은 SPA `single`(`index.html` 1개 + 번들 1개) [확인 ls].
- 1회차 번들에 `"Web support is only available to sponsors"` 문자열 1건(= `@react-native-google-signin` 웹 구현이 번들에 들어감),
  2회차 0건 · `apple_web_unsupported` 1건(= `socialAuth.web.ts` 가 해석됨) [확인 grep].
- 두 회 모두 번들에 `getReactNativePersistence` 문자열 1건 [확인 grep].

### 웹 분기 파일

- `app/src/lib/socialAuth.web.ts` — 만들었다. `signInWithGoogle`: 익명이면 `linkWithPopup` → `linked`; `auth/credential-already-in-use`·
  `auth/email-already-in-use` 면 `GoogleAuthProvider.credentialFromError` → `signInWithCredential` → `switched`; 아니면 `signInWithPopup` →
  `signed_in`; `auth/popup-closed-by-user`·`auth/cancelled-popup-request` → `cancelled`; 그 외(`auth/popup-blocked` 포함)는 FirebaseError 를
  그대로 throw(`code` 보존). `signInWithApple` → `throw new Error('apple_web_unsupported')`. `signInWithRedirect` 0건(주석 포함). `npm run typecheck` 통과 [확인].
- `app/src/lib/firebase.web.ts` — **만들지 않았다.** 근거 [확인]: export 두 회 exit 0 · 오류 줄 0, 시뮬레이터 Safari 에서 `/` 와
  `/auth/login` 이 오류 배너 없이 그려졌다(아래 스크린샷). 조건("export 또는 런타임에서 `getReactNativePersistence` 부재가 문제로 확인될 때만")
  이 성립하지 않았다. 런타임 auth 가 실제로 로그인 상태를 유지하는지는 Task 2 에서 본다 [미측정].

### 후보 (2) probe

- `.planning/phases/38-supplier-link/38-04-probe/` = `index.html` · `probe.js` · `README.md` · `.gitignore`(`config.js`) [확인].
- `probe.js`: gstatic `firebasejs/12.13.0` import 3줄, `signInWithPopup`, `/upload-url`, `setDoc`, `XMLHttpRequest` PUT, `onSnapshot` 포함;
  `signInWithRedirect`·`innerHTML` 0건; `node --check` 통과 [확인].
- `config.js` = `app/.env` 에서 `node -e` 한 줄로 생성(README.md) — Firebase 웹 config 6키 + `EXPO_PUBLIC_API_BASE_URL`. `git status` 에 안 나온다
  (`.gitignore`) [확인]. 측정 끝나면 삭제한다.

### 서빙 (Task 1 step 4)

- 후보 (1): `npx expo serve <scratchpad>/web-serve/web-export --port 8082`.
  - 첫 시도 `npx expo serve <scratchpad>/web-export` 는 `CommandError: Project root directory not found` 로 실패 [확인] — `expo serve` 는 인자 디렉터리에서
    위로 `package.json` 을 찾는다(`@expo/cli/build/src/serve/serveAsync.js` `findUpProjectRootOrAssert`) [확인 소스]. 그래서 scratchpad 에
    `web-serve/package.json`(빈 shim) 을 두고 그 아래로 export 사본을 옮겨 서빙했다.
  - `expo serve` 의 정적 서버는 SPA 폴백이 없다(`send` 404 → `Not Found`) [확인 소스] → `curl http://localhost:8082/auth/login` = **404** [확인].
    배포(CloudFront 404→index.html)를 흉내 내려고 **서빙 사본에만** `auth/login.html` = `index.html` 복사본을 넣었다 → 200 [확인].
    다른 딥링크는 여전히 404 다(앱 안 이동은 클라이언트 라우팅이라 무관).
- 후보 (2): `python3 -m http.server 8083 --directory .planning/phases/38-supplier-link/38-04-probe` [확인].
- 자동 스모크 [확인]:
  - `curl -s http://localhost:8082/ | grep -c 'id="root"'` = 1
  - `curl -s http://localhost:8083/ | grep -c 'id="log"'` = 1
  - `http://localhost:8082/_expo/static/js/web/entry-1ac8….js` = 200, 2,853,362 bytes
- CORS(브라우저 경로 전제) [확인]:
  - API `OPTIONS /upload-url` (Origin `http://localhost:8083`, 요청 헤더 authorization,content-type) → `204`, `access-control-allow-origin: *`.
  - S3 `get-bucket-cors sunity-motion-pilot-videos` → `AllowedMethods [PUT]`, `AllowedOrigins [*]`, `AllowedHeaders [*]`.

### 시뮬레이터 첫 화면 (스크린샷을 직접 열어 본 것)

- 기기: iPhone 17 Pro (iOS 26.5, `BE524358-9D29-4046-A91E-E5AF167CC06E`), Mobile Safari [확인].
- `38-04-web-root.png` (`http://localhost:8082/`, 12초 뒤): 인트로 — 어두운 적갈색 배경 사진 위 흰 `Sunity` 워드마크, "프로의 동작과 비교하는 /
  나만의 AI 운동 코치". 하단에 버튼 테두리 일부가 보이고 그 위를 Safari 의 "북마크, 공유 메뉴 및 열린 탭 보기" 안내 말풍선이 덮고 있다.
  흰 화면·오류 배너 없음 [확인].
- `38-04-web-login.png` (`http://localhost:8082/auth/login`, 10초 뒤): 연분홍 배경, 좌상단 뒤로 화살표, 빨간 `Sunity` 워드마크, "오늘도 / 한 발 더!",
  "WELCOME BACK", Google · Apple 아이콘 버튼 2개, "게스트로 시작하기" 외곽선 버튼, 하단 "처음 오셨나요? 회원가입". 흰 화면·오류 배너 없음 [확인].
  Apple 버튼도 웹에 그려진다 — 누르면 `apple_web_unsupported` 가 throw 되는 코드다 [확인 코드], 화면 반응은 [미측정].
- `38-04-probe-root.png` (`http://localhost:8083/`, 8초 뒤): 버튼 `1. Google 로그인`, `2. 영상 선택` + 파일 선택, `3. 업로드`, 로그
  `[14:41:25] firebase init ok · project=sunity-ai-coach` / `[14:41:25] auth: 로그인 안 됨`(시각은 UTC) [확인].
  서버 로그: `GET /` · `/probe.js` · `/config.js` 200, `/favicon.ico` 404 [확인].
- 경로(휘발): `<scratchpad>/38-04-web-root.png` · `<scratchpad>/38-04-web-login.png` · `<scratchpad>/38-04-probe-root.png`.

### 시험 영상

- 사람이 나오지 않는 합성 클립 2개를 `xcrun simctl addmedia booted` 로 사진 앱에 넣었다 [확인]:
  - `38-04-test-clip-8s.mov` — ffmpeg `testsrc2`+노이즈, 720x1280, 8.0초, 8.1 MB(~8 Mbps). **측정에 쓸 것**(앨범에서 가장 최근).
  - `38-04-test-clip.mov` — `testsrc`, 5.0초, 62 KB. 먼저 넣은 것 — 저비트레이트라 앱 품질 안내가 끼어들 수 있어 쓰지 않는다.

### Task 2 — belle 손 측정 (2026-09-29 밤, 계정 = `test_account`)

belle 원문 [확인 belle]: 후보 (1) "후보1 3번까지 오케이" / "영상을 선택했고, 올바르지 않은 영상이라고 잘 해주고 넘어간건데? 여기서 진행이 안되는게 당연하지" /
"후보1은 영기서 어떻게 4번으로 넘어가냐고" · 후보 (2) "후보2 모두 오케이".

| # | 항목 | 결과 | 본 문구 / 근거 |
|---|---|---|---|
| 1 | 후보 (1) `/` 첫 화면 · 익명 진입 | ○ [확인 belle] | "후보1 3번까지 오케이" |
| 2 | 후보 (1) Google 팝업 로그인 | ○ [확인 belle] | "후보1 3번까지 오케이" |
| 3 | 후보 (1) 앨범에서 영상 선택 | ○ [확인 belle] — 영상이 선택되고 안내 창이 떴다 | belle 스크린샷의 창: 제목 "영상이 너무 짧아요", 본문 "동작 전체가 담긴 영상이 필요해요. 3초 이상인 영상을 다시 선택해주세요.", 버튼 "닫기" / "다른 파일 선택" |
| 4 | 후보 (1) PUT → 로딩 `queued` | **미측정** — 선택 영상이 3 에서 거절돼 업로드 단계에 도달 불가(× 아님) [확인 belle] | "후보1은 영기서 어떻게 4번으로 넘어가냐고" |
| 5 | 후보 (2) Google 팝업 로그인 → uid | ○ [확인 belle] | "후보2 모두 오케이" |
| 6 | 후보 (2) 파일 선택 → 이름/크기 | ○ [확인 belle] | "후보2 모두 오케이" |
| 7 | 후보 (2) 업로드 → PUT 200 | ○ [확인 belle] | "후보2 모두 오케이" |
| 8 | 후보 (2) onSnapshot `status` 로그 | ○ [확인 belle] | "후보2 모두 오케이" |

- belle 스크린샷 모양: 넓은(데스크톱 폭) 레이아웃이었다 [확인 오케스트레이터가 belle 스크린샷을 보고 전달 — 실행자는 원본 미열람]. 그 창이 iOS 시뮬레이터 Mobile Safari 였는지 데스크톱 브라우저였는지는 [미확인]
  (belle 에게 묻지 않았다). 후보 (2) 를 어느 브라우저에서 했는지도 [미확인].

**교차 대조 (실행자·오케스트레이터가 읽기 전용으로 돌린 것):**

- S3 [확인 `aws s3api list-objects-v2 --bucket sunity-motion-pilot-videos --prefix uploads/`, LastModified ≥ 2026-09-29T12:00Z, 이 세션 재실행]:
  객체 5개, 전부 `uploads/UmH3…/` 아래, 각 2,521,622 bytes, `.mp4`, 2026-09-29T15:00:55Z ~ 15:01:00Z.
  → PUT 이 **로그인한 테스트 계정 uid** 아래에 들어갔다(R15d 대조 일치; 익명 uid 아님).
- Firestore `users/UmH3…/analyses` [확인 오케스트레이터 Admin SDK 읽기]: 같은 시간대에 doc 5개 — 전부 `mode=mode3`, `learningOptIn=false`,
  `status=failed`, `error.code=server_error`. `fileName` = belle 선택 클립(2.5MB mp4). mode3·learningOptIn false 는 probe 가 하드코딩한 값과 같다.
  `failed/server_error` 는 Pod 가 꺼져 있어 나오는 예상 결과다(분석 Pod = 시연 때만).
- 후보 (1) 은 같은 시간대에 Firestore doc·S3 객체를 남기지 않았다 [확인] — belle 이 본 클라이언트 쪽 거절과 맞는다.
- 후보 (2) 에서 고른 파일은 `.mp4` 다(S3 키 확장자·fileName) [확인] → 후보 (2) 의 `.mov` 선택·PUT 은 [미측정].
  후보 (1) 에서 고른 파일의 형식은 흔적이 없어 [미확인].
- 5건이 약 6초 사이에 올라갔다 [확인 타임스탬프]. probe 의 업로드 버튼을 여러 번 누른 것으로 [추정 — belle 에게 묻지 않음]. probe 에는 중복 제출 막기가 없다 [확인 코드].

## 미측정

Task 2 뒤에도 남은 미측정 (Task 1 때 적은 4 × 2 표는 위 Task 2 표로 대체):

- 후보 (1) presigned PUT · onSnapshot — 영상이 길이 검사에서 거절돼 도달 불가 [미측정].
- `.mov` 선택·PUT — 후보 (2) 는 `.mp4` 로 쟀다, 후보 (1) 은 고른 형식 [미확인] → `.mov` 는 두 후보 모두 [미측정].
- 실기기 HTTPS: 로컬에선 못 잰다. Firebase OAuth 는 Authorized domain 만 허용하고 기본 허용은 `localhost` 뿐이다
  [CITED firebase.google.com/docs/auth/web/google-signin] — 폰에서 LAN IP 로 열면 팝업 로그인이 거부된다. 실기기 측정은 38-13 배포(HTTPS 도메인 등록) 뒤.
- 번들 첫 로딩 시간(실망) [미측정].

## 결정표 (두 후보 열의 4가지 행 = Task 2 의 같은 실험값만 — R14)

| 행 | 후보 (1) Expo Router web export | 후보 (2) 정적 단일 페이지 |
|---|---|---|
| export 성공·시간 | exit 0, 16초(첫 회) / 7초(캐시) [확인] | 해당 없음(빌드 없음) |
| 산출 크기 | 18M(JS 2.85 MB + 폰트 10M 등) [확인] | probe 3파일 10,407 bytes + gstatic SDK 3모듈 709,292 bytes(app 103,070 · auth 154,340 · firestore 451,882, curl 무압축) [확인] |
| 시뮬 Safari 첫 화면 | 인트로·로그인 정상 렌더 [확인 스크린샷] | probe 정상 렌더 + firebase init ok [확인 스크린샷] |
| Google 팝업 | ○ [확인 belle 항목 2] | ○ [확인 belle 항목 5] |
| 영상 선택 | ○ — 선택됨, 이어 "영상이 너무 짧아요" 창 [확인 belle 항목 3]; 형식 [미확인], `.mov` [미측정] | ○ `.mp4` [확인 belle 항목 6 + S3 키]; `.mov` [미측정] |
| PUT (uid 대조) | [미측정 — 길이 단위 결함으로 도달 불가] | ○ [확인 belle 항목 7]; `uploads/UmH3…/` 5객체 = 로그인 uid 일치 [확인 S3] |
| onSnapshot | [미측정 — 길이 단위 결함으로 도달 불가] | ○ [확인 belle 항목 8]; doc 5개 `failed/server_error`(Pod 꺼짐 예상) [확인 Firestore] |
| 남은 일 | 38-10·38-11 = 공급자 라우트 3개 + 데이터 훅 + 웹 분기 마무리. **+ 실측에서 깨진 것 1건**: 웹 영상 길이 단위(초→ms) 수리(진단 D-1) — 수리 뒤 PUT·onSnapshot 재측정 필요. 서빙 SPA 폴백(딥링크 404) 은 배포 CloudFront 404→index.html 로 [확인 로컬 404, 배포 동작 미측정] | 38-12 = HTML/CSS/JS 3파일 + copy/rules 내보내기 스크립트. 로그인·파일 선택·PUT·구독 4가지는 probe 로 **측정됨**(단 `.mov` 는 [미측정]). probe 에는 중복 제출 막기가 없다 [확인 probe 코드] — 38-12 는 제출 뒤 진행 패널로 바뀌는 설계 [확인 38-12-PLAN 문구] |
| 배포 경로 | S3 정적 버킷 + CloudFront OAC, HTTPS 필수, SPA 404→index.html. Google 팝업 = 배포 도메인을 Firebase Authorized domain 에 등록(belle 콘솔 1회). CloudFront 생성 권한 [미확인] | 같음(S3 + CloudFront OAC, HTTPS, Authorized domain 등록). SPA 폴백 불필요(파일 1장) |
| 비용 | S3 저장·전송 센트 단위 [RESEARCH §H]; CloudFront 과금 방식 [미확인 — 38-13 이 계정에서 관측] | 같음 [미확인 CloudFront] |
| "같은 앱" 문자 그대로 | 예 | 아니오 (디자인 토큰은 CSS 로 재현) |

## 진단

관측이 아니다 — 승계 전 재검증 대상.

**D-1. 후보 (1) "영상이 너무 짧아요" 의 원인 — 웹의 길이 단위 결함** [확인 코드, 런타임 재현 미실시]

- belle 의 관측(선택 → 안내 창)은 그대로다. 다만 "고른 영상이 올바르지 않았다" 는 해석은 코드가 받쳐 주지 않는다 —
  웹에서는 **어떤 영상이든** 이 창이 뜨는 구조다.
- `app/node_modules/expo-image-picker/build/ExponentImagePicker.web.js:137` 은 웹에서 `duration: video.duration` 을 넘긴다.
  `HTMLVideoElement.duration` 은 **초** 단위다. 네이티브는 밀리초를 넘긴다.
- `app/src/lib/videoDuration.ts:28` `classifyDurationMs` 는 이 값을 **밀리초**로 보고 `MIN_DURATION_MS = 3000` 과 비교한다
  (`analyze.tsx:215` 에서 호출). → 8초 영상 = 8 < 3000 → `tooShort`. 90초 영상도 90 < 3000 → `tooShort`.
- 같은 가정이 `analyze.tsx:232-233`(비트레이트 = `fileSize*8 / (duration/1000)`) 에도 있다 — 웹에서 분모가 1000배 작아져
  비트레이트가 1000배 크게 계산되므로 저품질 안내가 **안 뜨는** 쪽으로 틀린다(막지는 않는다).
- 네이티브(iOS/Android 앱)는 ms 를 받으므로 이 결함에 해당하지 않는다.
- 수리 크기(추정): 웹에서만 초→ms 로 바꾸는 한 곳(예: `Platform.OS === 'web'` 분기 또는 `.web.ts` 헬퍼). **이 플랜(38-04)에서는 고치지 않는다** —
  페이지 구현 플랜이 아니다. 후보 (1) 이 선택되면 38-10/38-11 의 남은 일에 들어간다.

**D-2. 후보 (1) PUT·onSnapshot 에 대한 추론 (결정표 행에는 쓰지 않았다 — R14)**

- 후보 (1) 의 업로드가 쓰는 운반 부품 — `POST /upload-url` CORS(`OPTIONS` 204, allow-origin `*`), S3 버킷 CORS(PUT, 모든 origin) —
  은 후보 (2) probe 가 실제로 통과한 것과 같다 [확인 Task 1 CORS 조회 + 항목 7]. 그래서 D-1 을 고치면 후보 (1) 도 PUT 이 될 **가능성이 높다고 추정**한다.
  그러나 앱 경로 고유 부분(웹 picker 가 주는 `blob:` uri → 앱 `uploadToS3` 의 바디 생성, 로딩 화면의 onSnapshot 흐름)은 아무도 안 쟀다 → [미측정].

**D-3. 후보 (2) probe 측정 범위**

- probe 는 수요자 경로(`POST /upload-url` → `uploads/{uid}/`, mode3, 앱처럼 `setDoc` 선작성) 로 PUT 했다. 38-12 본 페이지는
  `POST /reference/upload-url` 로 올리고 `reference` 컬렉션을 구독하며 Firestore 쓰기 0 이다 [확인 38-12-PLAN 문구]. 그 라우트의 CORS·권한·
  구독 규칙은 이 측정 밖이다 [미측정] — 후보 (1) 의 공급자 라우트(38-10/38-11)도 같은 백엔드를 쓰므로 두 후보에 공통인 미측정이다 [추정].
- 5건 연속 업로드 = 버튼 반복 탭 [추정]. 어느 후보든 본 페이지는 제출 중 버튼 잠금이 필요하다(38-12 는 진행 패널 설계로 이미 들어 있다).

**D-0. Task 1 실행자 메모** [미확인]: `firebase.ts` 는 `getReactNativePersistence` 호출을 `try` 로 감싸고 실패 시 `getAuth(app)` 로 간다. 웹 번들에서
  그 이름이 undefined 라 호출이 TypeError 로 떨어져 `getAuth` 경로(웹 기본 persistence)를 탄다고 **추정**한다 — 시뮬레이터 콘솔을 열어 보지 않았으므로
  기제는 확인되지 않았다. 확인된 것은 "첫 화면이 오류 없이 그려진다" 까지다.

## 결정

- 결정 시각: 2026-09-30T00:14+09:00 (오케스트레이터 AskUserQuestion 으로 belle 이 고름) [확인 belle]
- 호스팅 — belle 원문: **"option-1 앱을 웹으로"** → **option-1 확정** (후보 (1) Expo Router web export → S3+CloudFront; 38-10 + 38-11 실행, 38-12 건너뜀). 이유 한 줄은 주지 않았다.
- 재현성 문구 분기 — belle 원문: **"90 유지"** →
  `selfScoreMin: 90 유지` (`app/src/lib/supplierRules.ts` `SELF_SCORE_OK_MIN` 무접촉. 문구 분기점일 뿐 통과 목표가 아니다.)

결정 뒤 기계적 스킵 (Task 3 (a)~(e), 한 커밋 `docs(38-04): hosting decision option-1 — skip 38-12 by decision`):

- (a) `38-12-SUMMARY.md` — `status: skipped-by-decision`, `skipped_by: "38-04 Task 3"`, `decision: option-1`.
- (b) `38-12-PLAN.md` frontmatter `skipped: true` (`autonomous:` 아래 한 줄).
- (c) `38-13-PLAN.md` `depends_on: ["38-09", "38-11"]` — 이미 그 값이라 확인만, 수정 0 [확인 grep].
- (d) `38-VALIDATION.md` 38-12-01~03 → `⏭ skipped-by-decision`.
- (e) 이 절 + ROADMAP Phase 38 플랜 목록(38-10·38-11 "option-1 확정", 38-12 "skipped-by-decision").

실측 이월 (후보 (1) 이 선택됐으므로 위 진단 D-1 · 미측정 행 · D-3 을 38-10 이 받는다 — `38-10-PLAN.md` "38-04 실측 이월" 표식):

- D-1 웹 영상 길이 단위(초 → ms) 수리 — 웹 경로만, 수리 전 실패하는 테스트 포함 → 38-10 Task 0.
- 후보 (1) PUT(uid 대조) · onSnapshot · `.mov` 선택 재측정 + D-3(`/reference/upload-url` probe CORS · `reference` 구독) → 38-10 Task 4 (시뮬레이터, belle 체크포인트).
