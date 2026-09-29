---
phase: 38-supplier-link
plan: 04
subsystem: supplier-hosting
tags: [react-native-web, expo-export, firebase-auth-popup, hosting-decision, measurement]
requires:
  - 38-01 (계약·키)
  - 38-03 (supplierRules SELF_SCORE_OK_MIN)
provides:
  - "호스팅 결정 option-1 (Expo Router web export → S3+CloudFront) — 38-10·38-11 실행, 38-12 skipped-by-decision"
  - "app/src/lib/socialAuth.web.ts — 웹 Google 팝업 로그인 분기"
  - "react-native-web 0.21.3 설치 (웹 export 가능)"
  - "38-04-MEASUREMENT.md — 두 후보 같은 4가지 실측 + 결정표 + 진단 D-0~D-3"
affects:
  - 38-10 (38-04 실측 이월 Task 0 · Task 4 추가, autonomous false)
  - 38-12 (skipped: true + SUMMARY skipped-by-decision)
  - 38-13 (depends_on ["38-09","38-11"] 확인)
tech-stack:
  added: [react-native-web ^0.21.0 (lock 0.21.3)]
  patterns: [".web.ts 플랫폼 분기 (Metro 가 웹 번들에서 socialAuth.web.ts 를 해석)", "결정 뒤 미선택 트랙을 파일로 스킵 (SUMMARY skipped-by-decision + PLAN skipped)"]
key-files:
  created:
    - app/src/lib/socialAuth.web.ts
    - .planning/phases/38-supplier-link/38-04-MEASUREMENT.md
    - .planning/phases/38-supplier-link/38-04-probe/{index.html,probe.js,README.md,.gitignore}
    - .planning/phases/38-supplier-link/38-12-SUMMARY.md
  modified:
    - app/package.json
    - app/package-lock.json
    - .planning/phases/38-supplier-link/38-10-PLAN.md
    - .planning/phases/38-supplier-link/38-12-PLAN.md
    - .planning/phases/38-supplier-link/38-VALIDATION.md
    - .planning/ROADMAP.md
key-decisions:
  - "belle 호스팅 결정 원문 \"option-1 앱을 웹으로\" — option-1 확정, 38-12 skipped-by-decision"
  - "belle selfScoreMin 원문 \"90 유지\" — SELF_SCORE_OK_MIN 무접촉 (문구 분기점, 통과 목표 아님)"
  - "firebase.web.ts 는 만들지 않음 — export 2회 오류 0 · 첫 화면 정상 렌더로 조건 불성립"
  - "38-04 실측 결함(웹 duration 초/ms)은 38-04 에서 고치지 않고 38-10 Task 0 으로 이월, 재측정은 38-10 Task 4 시뮬 체크포인트"
requirements-completed: []
duration: "약 41분 실행 (2026-09-29 23:35 → 2026-09-30 00:16 KST, belle 체크포인트 대기 포함)"
completed: 2026-09-30
---

# Phase 38 Plan 04: 공급자 페이지 호스팅 측정 → belle 결정 Summary

두 호스팅 후보를 같은 4가지 실험(Google 팝업 · 영상 선택 · presigned PUT · onSnapshot)으로 재고 belle 이 **option-1(같은 앱을 Expo web export 로)** 을 골랐다 — 38-12 는 파일로 건너뛰고, 측정에서 드러난 웹 영상 길이 단위 결함과 못 잰 행은 38-10 에 이월했다.

## 결정 (belle 원문)

- 호스팅: **"option-1 앱을 웹으로"** → option-1 (Expo Router web export → S3+CloudFront; 38-10 + 38-11 실행, 38-12 건너뜀). 이유 한 줄 없음. [확인 belle, 오케스트레이터 AskUserQuestion 2026-09-30]
- 재현성 문구 분기: **"90 유지"** → `selfScoreMin: 90 유지`. `app/src/lib/supplierRules.ts` 무접촉.

## Tasks

| Task | 내용 | 커밋 |
|---|---|---|
| 1a | react-native-web 설치 (`npm view` 재확인 → `npx expo install`) | `2807a47b` |
| 1b | `socialAuth.web.ts` + 후보 (2) probe + 측정 로그 | `ceb2b541` |
| 2 | belle 손 측정 8줄 기록 + 결정표 채움 + 진단 D-0~D-3 | `e8b4c665` |
| 3 | 결정 기록 + 스킵 절차 (a)~(e) + 38-10 실측 이월 (한 커밋) | `3ca714dd` |

Task 3 스킵 절차 (a)~(e) [확인 — 자동 verify `VERIFY_PASS`]:
- (a) `38-12-SUMMARY.md` status `skipped-by-decision`, decision `option-1`, decided_at `2026-09-30T00:14:02+09:00`.
- (b) `38-12-PLAN.md` frontmatter `skipped: true` (frontmatter 파싱으로 `skipped: true` 확인; 38-10/38-11 의 같은 문자열은 원래 있던 주석 줄이고 frontmatter 값은 없다).
- (c) `38-13-PLAN.md` depends_on 이 이미 `["38-09", "38-11"]` — 확인만, 수정 0.
- (d) `38-VALIDATION.md` 38-12-01~03 → `⏭ skipped-by-decision` (+ Wave 0 체크리스트의 `rules.test.mjs` 항목 같은 표시).
- (e) MEASUREMENT 결정 절 · ROADMAP 플랜 목록(38-10·38-11 "option-1 확정", 38-12 `[x]` skipped). STATE `stopped_at` 은 이 SUMMARY 커밋에서 갱신.

## 38-04 실측 이월 → 38-10 (배치와 이유)

`38-10-PLAN.md` 에 "38-04 실측 이월" 표식으로 두 task 를 더했다. 다른 task 본문은 무수정.
- **Task 0 (auto, tdd, 맨 앞)** — 진단 D-1 수리: expo-image-picker 웹 `duration` = 초(`ExponentImagePicker.web.js:137` `video.duration`) → 앱은 ms 로 읽음(`videoDuration.ts:28` MIN 3000 · `analyze.tsx:231-234` 비트레이트). 웹 경로만 초→ms(순수 헬퍼에 OS 를 인자로 — `node --test` 성질 유지), 네이티브 불변, **수리 전 실패하는 테스트 먼저**. 공급자 페이지는 `readVideoDurationSec`(초)→`validateFile(durationSec)` 이라 결함 없음 — 단 picker `asset.duration` 을 길이로 쓰는 곳이 생기면 같은 헬퍼를 거치도록 명시.
- **Task 4 (checkpoint:human-verify, 맨 끝)** — 시뮬레이터 Mobile Safari 에서 belle 손 재측정: 후보 (1) 앱 흐름 PUT(uid 접두 `aws s3` 대조) · 로딩 onSnapshot · `.mov`/`.mp4` · D-3 공급자 `/reference/upload-url` probe CORS · `reference` 구독. 결과는 MEASUREMENT 새 절 "## 38-10 재측정".
- **배치 선택 이유:** 38-10·38-11 에는 기존 사람 체크포인트가 없다 [확인 grep]. 38-13 Task 3(실기기)에 접으면 새 정지가 없지만 Task 0 수리의 런타임 확인이 wave 6 까지 밀린다. 그래서 38-10 끝에 체크포인트 하나를 붙였고, 그 결과 38-10 frontmatter `autonomous: true → false` (주석으로 이유 표기). 38-13 Task 3 의 공급자 PUT 실기기 단계는 그대로 — 공급자 PUT 은 38-11 폼이 생긴 뒤 거기서 한 번 더 잰다.
- ROADMAP 38-10 줄에 "체크포인트" 표기를 더했다.

## 관측 (승계해도 되는 것)

- react-native-web 0.21.3, install 스크립트 없음, 홈 디렉터리 npm 파일 mtime 변화 0 [확인 — MEASUREMENT 설치 절].
- `expo export --platform web` 2회 exit 0 (16초/7초), 출력 18M (JS 2.85 MB + Pretendard 폰트 10M) [확인].
- `socialAuth.web.ts` 가 웹 번들에 해석됨(`apple_web_unsupported` 1건, google-signin 웹 구현 0건) [확인 grep].
- belle 측정: 후보 (1) 1~3 ○, 4 [미측정]("후보1 3번까지 오케이"); 후보 (2) 5~8 ○("후보2 모두 오케이") [확인 belle].
- 후보 (2) PUT 5객체가 `uploads/UmH3…/`(로그인 테스트 계정 uid) 아래 [확인 S3]; Firestore doc 5개 `failed/server_error` (Pod 꺼짐) [확인 오케스트레이터 Admin 읽기].
- 후보 (2) 에서 고른 파일은 `.mp4` → `.mov` 는 두 후보 모두 [미측정].
- 이번 continuation 끝 `cd app && npm run typecheck` exit 0 [확인].

## 진단 (승계 전 재검증 대상)

- D-1 후보 (1) "영상이 너무 짧아요" = 웹 길이 단위(초/ms) 결함 [확인 코드 · 런타임 재현 미실시] → 38-10 Task 0.
- D-2 D-1 을 고치면 후보 (1) PUT 도 될 가능성이 높다 [추정 — 운반 부품(CORS)은 후보 (2) 와 같음, 앱 고유 `blob:` 바디·로딩 흐름은 미측정] → 38-10 Task 4.
- D-3 공급자 경로 `/reference/upload-url` CORS · reference 구독은 두 후보 모두 미측정 [미측정] → 38-10 Task 4 + 38-13 Task 3.
- D-0 웹 번들에서 `getReactNativePersistence` 가 undefined → `try` 실패 → `getAuth` 경로라고 추정 [미확인 — 콘솔 미열람].

## Deviations from Plan

1. **[Rule 3 - Blocking] `expo serve` 프로젝트 루트 shim** — `npx expo serve <scratchpad>/web-export` 가 `CommandError: Project root directory not found` [확인]. `expo serve` 가 인자 디렉터리 위로 `package.json` 을 찾기 때문(`serveAsync.js findUpProjectRootOrAssert`) [확인 소스] → scratchpad `web-serve/package.json`(빈 shim `{"name":"web-serve-shim","private":true}`) 아래로 export 사본을 옮겨 서빙. 또 `expo serve` 에 SPA 폴백이 없어 **서빙 사본에만** `auth/login.html` = `index.html` 복사본. 저장소 파일 변경 0. 38-10 Task 4 에 같은 절차를 적어 두었다.
2. **[Rule 2 - Security] probe `.gitignore` 추가** — `38-04-probe/.gitignore` = `config.js` (Firebase 웹 config + API URL 을 `app/.env` 에서 생성, 공개값이지만 커밋 금지 — 위협 T-38-04-4). 이번 continuation 에서 `config.js` 삭제 [확인 ls — 커밋된 적 없음, `git ls-files` 에 없음].
3. **app/dist 실수와 복구 (Task 1)** — 오케스트레이터 전달: Task 1 중 `app/dist` 를 잘못 건드렸다가 복구했다. 이 continuation 실행자는 원 경위를 보지 못했다 [미확인 경위]. 지금 관측 [확인]: `app/dist` 는 `app/.gitignore` 의 `dist/` 로 추적 밖, 내용물(`_expo` · `assets` · `assetmap.json` · `metadata.json`, 29M) mtime 은 전부 2026-09-20 23:27(이전 export), 디렉터리 자체 mtime 만 2026-09-29 23:39 KST(scratchpad 서빙 shim 생성 시각과 같은 분). git 추적 파일 영향 0 (`git status` 에 없음).
4. **push 안 함** — 플랜 `<verification>` 은 "플랜 끝 push" 지만 오케스트레이터 지시로 push 하지 않았다. push 방식은 belle 결정 대기(38-PLAN-CHECK '다음' 절). origin/main = `ca739390`, 로컬 미push 커밋 = 이 SUMMARY 커밋 포함 25개.
5. **측정 잔여물 정리** — 정적 서버 8082(`npm exec expo serve` PID 12845 + 자식 node 12876) · 8083(`python -m http.server` PID 12509) 종료, `lsof` 재확인 LISTEN 0 [확인]. 시뮬레이터 iPhone 17 Pro 는 켜 둠(38-10 Task 4 재사용).

## Known Stubs

없음 — 이 플랜의 코드 산출물은 `socialAuth.web.ts` 하나이고 UI 를 만들지 않는다.

## Threat Flags

없음 — 새 표면은 플랜 위협표(T-38-SC · T-38-04-1~4) 안이다. 측정 업로드 5건은 테스트 계정 uid 아래(T-38-04-2 accept 범위).

## Self-Check: PASSED

- FOUND: app/src/lib/socialAuth.web.ts · 38-04-MEASUREMENT.md · 38-12-SUMMARY.md · 38-04-probe/{index.html,probe.js,README.md,.gitignore}
- FOUND commits: 2807a47b · ceb2b541 · e8b4c665 · 3ca714dd
- MISSING (의도): 38-04-probe/config.js (삭제됨)
