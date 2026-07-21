---
phase: 32-result-readability-3-omni
plan: 12
subsystem: ui, app, deploy
tags: [expo-audio, coach-audio, tts-playback, pretendard, expo-font, failure-ux, d18, d29, d30, d09, eas-build, testflight, ota, runtime-bump]

# Dependency graph
requires:
  - phase: 32-16
    provides: "coachAudio 계약(CoachAudio/CoachAudioItem) + playback-url coachAudio asset(H-02 재서명) + Polly 사후 합성 프로덕션 라이브 — 앱 오디오 재생의 백엔드 선행"
  - phase: 32-09
    provides: "records recordId·cueLine·coverageGaps 방출 + 6동작 스윕 실 doc — 자막 큐/오디오 조인/커버리지 고지 데이터"
  - phase: 32-11
    provides: "wave 6 요약/섹션 대배선 + cueWindows 소비 지점 + Pretendard 실제 로드 이월분"
provides:
  - "재생 중 큐 오디오 재생 — audioCue.ts(expo-audio) 가 coachAudio mp3 를 cueId(=recordId) 조인·prefetch 캐시·자막 큐 전환 시점 재생 (설정 게이트 기본 off)"
  - "Pretendard 실제 로드 — static TTF 4웨이트 번들 + expo-font _layout 로드 + typography 토큰 weight→family 매핑 (앱 전역 Pretendard)"
  - "실패 UX — 부분 실패 정직 고지(D-29, coverageGaps 조건)·전체 실패 카피 응원 톤(D-30) + 재업로드 동선 분석탭 고정"
  - "native 배포 경로 — 앱 1.0.0→1.1.0 bump(새 runtime) + EAS iOS production build(1.1.0/29) + TestFlight 제출 + 신규 runtime OTA(production·preview)"
affects: [32-13 (1.1.0 runtime OTA 경로 사용), 32-14, 32-15]

# Tech tracking
tech-stack:
  added: [expo-audio(~1.1.1), expo-font(~14.0.12), "Pretendard static TTF x4(SIL OFL)"]
  patterns:
    - "재생 중 오디오 큐 = 명령형 어댑터(audioCue.ts) — createAudioPlayer replace 로 이전 발화 중단, prefetch 로 presigned URL 선캐시(재생 시점 네트워크 0), 설정/미조인/실패 전부 자막-만 graceful"
    - "폰트 실제 로드 = useFonts 렌더 게이트(hang 위험 0) + 토큰 weight→family 매핑 + fontWeight 유지(미로드 시 시스템 폴백)"
    - "native 모듈 추가 = app 버전 bump(runtime 신설) → EAS build → TestFlight → 신규 runtime OTA (구 바이너리 보호 — 1.0.0 은 1.1.0 OTA 미수신)"

key-files:
  created:
    - app/src/lib/audioCue.ts
    - app/assets/fonts/Pretendard-Regular.ttf
    - app/assets/fonts/Pretendard-Medium.ttf
    - app/assets/fonts/Pretendard-SemiBold.ttf
    - app/assets/fonts/Pretendard-Bold.ttf
    - .planning/phases/32-result-readability-3-omni/32-HUMAN-UAT.md
    - .planning/phases/32-result-readability-3-omni/render-check/01-boot-intro.png
  modified:
    - app/package.json
    - app/package-lock.json
    - app/app.json
    - app/src/lib/api.ts
    - app/src/components/VideoCompare.tsx
    - app/src/app/analysis/result.tsx
    - app/src/theme/typography.ts
    - app/src/app/_layout.tsx
    - app/src/app/analysis/loading.tsx

key-decisions:
  - "오디오 = B안 소비만 — 백엔드 TTS(Polly 합성·저장·계약·배포·스윕)는 32-16 에서 완결됨. 본 플랜 Task 2 는 '32-16 에서 수행'으로 skip, 백엔드 무접촉 (W-2 분리)"
  - "prefetchCueAudio 시그니처를 (analysisId, cues) 로 확장 — B안 재서명은 analysisId 로만 서버가 canonical key 구성(플랜 시그니처는 cues 만이라 Rule 3 보정)"
  - "일러스트(D-21) = 폴백 유지(앱 무산출) — 결함별 세트는 신규 생성 에셋이라 해부학 검수+belle 최종 승인 전 도입 금지(무검수 노출 0). 승인은 아침 UAT 이월"
  - "Pretendard = static TTF 4웨이트 전부 로드 + 전 토큰 매핑(전역 적용) — fontWeight 유지로 미로드 graceful. expo-splash-screen 미도입(렌더 게이트로 hang 위험 0)"
  - "expo-audio 플러그인 microphonePermission:false — 재생 전용(녹음 0), image-picker 한글 마이크 카피 보존"
  - "실기기 6-doc 렌더 = 아침 UAT 이월 — eval 스윕 doc 은 phase25eval uid 하 Firestore 규칙상 belle 계정 직접 열람 불가(백엔드 방출은 32-16-SWEEP 실증). 시뮬레이터 자동 tap 도 환경 제약(idb Python 3.14 파손·AppleScript 차단)"

patterns-established:
  - "보조 재생 채널(오디오)은 코어(자막·분석)와 완전 분리 — 어떤 실패도 자막·분석 흐름 무영향(graceful 폴백)"

requirements-completed: [D-18, D-29, D-30, D-09]

# Metrics
duration: ~1h 20m (EAS build/제출·시뮬레이터 빌드 포함)
completed: 2026-07-22
---

# Phase 32 Plan 12: UI 본체 마감 — 오디오 큐·Pretendard·실패 UX + native 배포 Summary

**재생 중 큐 오디오(음성 안내)를 coachAudio B안(32-16 백엔드) 소비로 배선하고(cueId 조인·prefetch·설정 게이트, 기본 off), Pretendard 를 실제 로드하고(TTF 4웨이트 + 토큰 매핑), 실패 UX(D-29 부분 정직 고지·D-30 응원 톤)를 정비한 뒤 — native 모듈 2종 추가를 올바른 배포 경로(1.0.0→1.1.0 runtime bump → EAS build 1.1.0(29) → TestFlight 제출 → 신규 runtime OTA)로 출시. 시뮬레이터 부팅·Pretendard 렌더 실증, 실기기 6-doc 확인은 아침 UAT 이월.**

## Performance

- **Duration:** ~1h 20m (원격 EAS build + 로컬 시뮬레이터 build 포함)
- **Tasks:** 3 실행(Task 1 오디오+빌드, Task 3 실패 UX, Task 4 검증) + Task 2 = 32-16 위임 skip
- **Files modified/created:** 14 (소스 10 + 폰트 4) + 계획 산출물 2

## Accomplishments

- **재생 중 큐 오디오 (D-18 B안 소비):** `audioCue.ts` — expo-audio 명령형 어댑터. `speakCue`/`stopCue`/`prefetchCueAudio`/`isAudioCueEnabled`/`setAudioCueEnabled`. cueId(=recordId) 로 Polly mp3 조인, prefetch 로 presigned URL 선캐시(재생 시점 네트워크 0 → 자막·음성 동기), 새 큐 replace 로 이전 발화 중단. VideoCompare 가 자막 큐 전환 지점에서 발화, 일시정지·seek·언마운트 시 중단. 설정 기본 off(학원 소음), "음성 안내" 토글. coachAudio done+items 일 때만 노출(failed/legacy=자막만).
- **Pretendard 실제 로드 (D-05, 32-11 이월):** 공식 v1.3.9 static TTF 4웨이트(Regular/Medium/SemiBold/Bold, SIL OFL) 번들 + `_layout` useFonts 렌더 게이트 + typography 전 토큰 weight→family 매핑. **시뮬레이터 부팅 스크린샷으로 실제 Pretendard 렌더 실증.**
- **실패 UX (D-29/D-30):** result.tsx 커버리지 갭 정직 고지(못 잰 부분 + 촬영 가이드 링크, 오버클레임 0). loading.tsx 전체 실패 카피 응원 톤 + 다음 행동 1개, 재업로드 CTA 를 `router.replace('/(tabs)/analyze')` 로 고정(두 플로우 모두 분석탭 확실 진입).
- **native 배포 경로 (리뷰 blocker 3):** app.json 1.0.0→**1.1.0**(runtime 신설) → EAS iOS production build **1.1.0(29)** FINISHED → TestFlight 제출 → 신규 runtime OTA production/preview. 구 1.0.0 바이너리는 1.1.0 OTA 미수신(native 부재 크래시 보호).

## Task Commits

1. **Task 1a: deps 설치 + 버전 bump** — `165e287` (chore)
2. **Task 1b: 재생 중 큐 오디오 재생** — `29eefdb` (feat)
3. **Task 1c: Pretendard 실제 로드** — `ed280fb` (feat)
4. **Task 3: 실패 UX (D-29/D-30)** — `85f7e9e` (feat)

**배포 산출물:** EAS build `429dd072` (1.1.0/29, runtime 1.1.0) · IPA 아티팩트 · TestFlight 제출 · OTA production `713a28d8` / preview `e821ea7b` (runtime 1.1.0) · 롤백 대상 `2cf7b6af` (runtime 1.0.0).

## Files Created/Modified

- `app/src/lib/audioCue.ts` (신규) — expo-audio 오디오 큐 어댑터(5 export + hydrate)
- `app/src/lib/api.ts` — `fetchCoachAudioUrl(analysisId, recordId)` (H-02 재서명)
- `app/src/components/VideoCompare.tsx` — 자막 큐 전환 지점 오디오 트리거 + "음성 안내" 토글 + prefetch 마운트 효과
- `app/src/app/analysis/result.tsx` — coachAudio 게이트(audioAnalysisId 전달) + D-29 커버리지 정직 고지 블록
- `app/src/app/analysis/loading.tsx` — D-30 실패 카피 응원 톤 + 재업로드 분석탭 고정
- `app/src/theme/typography.ts` — 전 토큰 weight→family(Pretendard) 매핑
- `app/src/app/_layout.tsx` — useFonts 로드 + 렌더 게이트
- `app/assets/fonts/Pretendard-{Regular,Medium,SemiBold,Bold}.ttf` (신규)
- `app/{package.json,package-lock.json,app.json}` — expo-audio·expo-font + 1.1.0 bump + 플러그인
- `.planning/.../32-HUMAN-UAT.md` (신규) — 아침 몰아보기 점검 목록
- `.planning/.../render-check/01-boot-intro.png` (신규) — 시뮬레이터 부팅 Pretendard 렌더 실증

## Decisions Made

- **Task 2(백엔드 TTS) = 32-16 에서 수행 (skip):** W-2 분리대로 32-16 이 Polly 합성·계약·playback asset·SAM/Pod 배포·6동작 스윕(DIFF=0)·mp3 스모크(200)를 완결. 본 플랜은 백엔드 무접촉, 앱 오디오 재생만.
- 상세 = frontmatter key-decisions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - 차단 해소] prefetchCueAudio 시그니처 확장 (analysisId 동반)**
- **Found during:** Task 1 (audioCue.ts 구현)
- **Issue:** 플랜 시그니처 `prefetchCueAudio(cues)` 는 B안 재서명에 필요한 analysisId 부재 — playback-url 은 analysisId 로만 서버가 canonical key 를 구성(H-02).
- **Fix:** `prefetchCueAudio(analysisId, cues)` 로 확장. api.ts 에 `fetchCoachAudioUrl(analysisId, recordId)` 신설(플랜 files 밖이나 오디오 조인에 필수 — 32-16 계약 소비).
- **Files modified:** app/src/lib/audioCue.ts, app/src/lib/api.ts
- **Verification:** typecheck clean + Metro 번들 성공
- **Committed in:** `29eefdb`

**2. [Rule 2 - 필수/보안 표면 최소화] expo-audio 마이크 권한 제거**
- **Found during:** Task 1 (expo install 후 app.json 플러그인 확인)
- **Issue:** expo-audio 플러그인 기본값이 NSMicrophoneUsageDescription 을 추가 → image-picker 의 한글 마이크 카피를 영문 기본값으로 덮어씀. 앱은 재생 전용(녹음 0)이라 마이크 권한 불필요.
- **Fix:** 플러그인 `microphonePermission: false` — 재생 전용 권한 표면 유지, image-picker 카피 보존.
- **Files modified:** app/app.json
- **Verification:** `expo config --type prebuild` OK + EAS build 성공
- **Committed in:** `165e287`

**3. [Rule 1 - 동선 신뢰성] 실패 재업로드 CTA 라우팅 고정**
- **Found during:** Task 3 (D-30 재업로드 동선 점검)
- **Issue:** loading 진입은 두 플로우 모두 `push('/analysis/loading')` — `router.back()` 은 mode1(reference 경유)에서 분석탭이 아닌 기준선택 화면으로 떨어짐. 플랜 명시 의도 = "버튼 → analyze 화면 라우팅".
- **Fix:** CTA 를 `router.replace('/(tabs)/analyze')` 로 — 실패 스택 정리 + 어느 모드든 분석탭 확실 진입(result.tsx 재분석 upsell 과 동일 패턴). 구조 재설계 아님(라우팅 목적지만).
- **Files modified:** app/src/app/analysis/loading.tsx
- **Verification:** typecheck clean + 두 진입 플로우 코드 추적
- **Committed in:** `85f7e9e`

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 필수/보안, 1 bug/신뢰성)
**Impact on plan:** 전부 정확성·계약·동선 신뢰성에 필수. scope creep 0.

## Issues Encountered

- **일러스트(D-21) 도입 보류(무검수 노출 0):** 게이트 확정 스타일=2안 준실사이나 결함별 일러스트 세트는 신규 생성 에셋 → **해부학 검수 + belle 최종 승인 게이트가 아침 이월**. 승인 전 무검수 노출 금지대로 앱 코드 무산출(현행 실프레임+텍스트 폴백 유지). 아침 승인 목록 = 32-HUMAN-UAT §B.
- **실기기 6-doc 렌더 = 아침 UAT 이월:** 32-16/32-09 스윕 doc 은 `users/phase25eval/...` uid 하라 Firestore 규칙상 belle 계정 직접 열람 불가(백엔드 방출·조인·score diff 0 은 32-16-SWEEP 실증). 시뮬레이터 자동 네비게이션도 환경 제약 — **idb Python 3.14 파손(asyncio.get_event_loop RuntimeError) + AppleScript System Events 차단** 으로 tap 자동화 불가. 대신 **로컬 시뮬레이터 native build(Build Succeeded) + 앱 부팅 + Pretendard 인트로 렌더를 스크린샷(render-check/01)으로 실증**, 전 화면 컴파일은 Metro production 번들로 실증. 실데이터 6-doc 결과 화면 육안 = belle 아침 UAT(본인 신규 분석 = 실 doc, 32-HUMAN-UAT §A).

## Verification

- `npm run typecheck` clean (오디오·폰트·실패 UX 전 커밋).
- `node --test` 기존 lib 33건 pass / 0 fail (cueTrack·summarySource·resultSections·manualOffset·gaugeGeometry — 무회귀).
- **Metro production 번들(`expo export -p ios`) 성공** — 전 화면 컴파일 + Pretendard 4 TTF 번들 + expo-audio/expo-font 해소(render-blocking 0, typecheck 미검출 영역 방어).
- **로컬 시뮬레이터 native build "Build Succeeded" + install** (iPhone 16 Pro, Release) — expo-audio/expo-font/Pretendard native 링크 실증.
- **앱 부팅 실증** — `simctl launch` → 인트로 화면 Pretendard 렌더(render-check/01-boot-intro.png), 폰트 게이트 _layout 흰화면/크래시 0 (verify-ui-on-simulator-before-ota 핵심 리스크 해소).
- **D-09 게이트:** 1차 grep(결과 화면 8파일) — 헤드라인 수치·% 일치율 위반 0(신규 추가분 audioToggle·coverageCard·실패 카피 전부 수치 0, 잔여 매치는 주석·레이아웃 %·영상 타임라벨·기존 근거 표기). 백엔드 문구집 금지어 테스트 25 pass.
- **EAS build FINISHED** 1.1.0(29) runtime 1.1.0 (id 429dd072, 자격증명 유효 ~2027-05).
- **OTA 발행** production `713a28d8` + preview `e821ea7b` (runtime 1.1.0), commit 85f7e9e. 롤백 대상 = production `2cf7b6af`(runtime 1.0.0, 별 runtime 이라 구 바이너리 무영향).
- **TestFlight 제출 확인:** `eas submit` — 무인 ASC API Key(ASM44H4TB4, [Expo] EAS Submit), ASC App **6772934567**, build **1.1.0(29)**. **iOS submission SCHEDULED** (submission id `9d88066e-438b-4975-a5a9-4931ae04a5c5`, 상태 "Submitting" → ASC 전달·Apple 처리 진행). 제출 확인까지 완료 — TestFlight 처리 완료·설치 가능 여부는 아침 belle 확인(checkpoint 프로토콜: "Apple 처리 대기는 제출 확인까지만").
- STATE.md/ROADMAP.md 무접촉 (orchestrator 소관).

## Known Stubs

없음 — 오디오/커버리지/실패 UX 는 실 계약(coachAudio 32-16, coverageGaps 32-09) 소비. 일러스트는 stub 이 아니라 폴백 유지(도입은 belle 승인 게이트) — 32-HUMAN-UAT §B 항목화.

## Threat Flags

없음 — 신규 표면(오디오 재생, 폰트 로드, native 빌드/OTA)은 전부 플랜 threat_model(T-32-SC/28/29) mitigate 경계 안. 오디오 = expo 공식 1개 설치(npx expo install, lock diff 1개), 발화 텍스트=문구집 cueLine(PII 0), URL=서버 canonical key 재서명(H-02), runtime bump 로 구 바이너리 보호.

## Next Phase Readiness

- runtime 정책 확립 — 이후 앱 OTA 는 **1.1.0 대상**(32-13 이 경로 사용).
- 아침 UAT(32-HUMAN-UAT): ①새 1.1.0 빌드 설치 후 belle 실기기 확인(음성·커버리지·폰트·실패·실데이터) ②일러스트 도입 최종 승인 ③Polly 음성 최종 청취(32-16 이월).

## Self-Check: PASSED

- FOUND: app/src/lib/audioCue.ts
- FOUND: app/assets/fonts/Pretendard-{Regular,Medium,SemiBold,Bold}.ttf (4)
- FOUND: .planning/phases/32-result-readability-3-omni/32-HUMAN-UAT.md
- FOUND: .planning/phases/32-result-readability-3-omni/render-check/01-boot-intro.png
- FOUND: .planning/phases/32-result-readability-3-omni/32-12-SUMMARY.md
- FOUND commits: 165e287 / 29eefdb / ed280fb / 85f7e9e (git log 확인)
- 파일 삭제 0 (전 커밋 add/modify만)
- EAS build 429dd072 FINISHED (1.1.0/29) + OTA production 713a28d8·preview e821ea7b (runtime 1.1.0) + TestFlight submission 9d88066e SCHEDULED

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-22 (실기기 6-doc 확인·일러스트 승인·Polly 음성 최종 = 아침 UAT 이월)*
