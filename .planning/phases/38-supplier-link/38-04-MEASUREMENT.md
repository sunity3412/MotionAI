# 38-04 측정 로그 — 공급자 페이지 호스팅 두 후보

test_account: [belle 지정 대기] — 테스트용 Google 계정(belle 본계정 금지). Task 2 체크포인트 첫 줄에서 belle 이 정한다.

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

### Task 2 — belle 손 측정 (대기)

(belle 의 8줄 ○/× 와 본 문구 원문을 `[확인 belle]` 로 여기에 옮긴다. 로그인 uid 앞 4자 마스킹 · `aws s3 ls …/uploads/<uid>/` 대조는 `[확인]`.)

## 미측정

| # | 실험 | 후보 (1) Expo web export `:8082` | 후보 (2) probe `:8083` |
|---|---|---|---|
| 1 | Google 팝업 로그인(→ uid) | [미측정 — Task 2 항목 2] | [미측정 — Task 2 항목 5] |
| 2 | `.mov` 파일 선택 | [미측정 — Task 2 항목 3] | [미측정 — Task 2 항목 6] |
| 3 | presigned PUT (+ `uploads/<uid>/` 대조) | [미측정 — Task 2 항목 4] | [미측정 — Task 2 항목 7] |
| 4 | onSnapshot `queued` | [미측정 — Task 2 항목 4] | [미측정 — Task 2 항목 8] |

- 후보 (1) 의 익명 자동 로그인(인트로 → 홈) [미측정 — Task 2 항목 1].
- 실기기 HTTPS: 로컬에선 못 잰다. Firebase OAuth 는 Authorized domain 만 허용하고 기본 허용은 `localhost` 뿐이다
  [CITED firebase.google.com/docs/auth/web/google-signin] — 폰에서 LAN IP 로 열면 팝업 로그인이 거부된다. 실기기 측정은 38-13 배포(HTTPS 도메인 등록) 뒤.
- 번들 첫 로딩 시간(실망) [미측정].

## 결정표 (Task 3 에서 채운다 — 두 후보 열은 같은 4가지 실험값만)

| 행 | 후보 (1) Expo Router web export | 후보 (2) 정적 단일 페이지 |
|---|---|---|
| export 성공·시간 | exit 0, 16초(첫 회) / 7초(캐시) [확인] | 해당 없음(빌드 없음) |
| 산출 크기 | 18M(JS 2.85 MB + 폰트 10M 등) [확인] | probe 3파일 ~10 KB + CDN SDK(크기 [미측정]) |
| 시뮬 Safari 첫 화면 | 인트로·로그인 정상 렌더 [확인 스크린샷] | probe 정상 렌더 + firebase init ok [확인 스크린샷] |
| Google 팝업 | [Task 2 대기] | [Task 2 대기] |
| .mov 선택 | [Task 2 대기] | [Task 2 대기] |
| PUT (uid 대조) | [Task 2 대기] | [Task 2 대기] |
| onSnapshot | [Task 2 대기] | [Task 2 대기] |
| 남은 일 | [Task 3] | [Task 3] |
| 배포 경로 | [Task 3] | [Task 3] |
| 비용 | [Task 3] | [Task 3] |
| "같은 앱" 문자 그대로 | 예 | 아니오 |

## 진단

(Task 3 에서 채운다 — 관측이 아니다, 승계 전 재검증 대상.)

- Task 1 실행자 메모 [미확인]: `firebase.ts` 는 `getReactNativePersistence` 호출을 `try` 로 감싸고 실패 시 `getAuth(app)` 로 간다. 웹 번들에서
  그 이름이 undefined 라 호출이 TypeError 로 떨어져 `getAuth` 경로(웹 기본 persistence)를 탄다고 **추정**한다 — 시뮬레이터 콘솔을 열어 보지 않았으므로
  기제는 확인되지 않았다. 확인된 것은 "첫 화면이 오류 없이 그려진다" 까지다.

## 결정

(Task 3 — belle 선택 원문 인용 · `selfScoreMin:`)
