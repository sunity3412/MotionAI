---
phase: 26-onboarding-upload-guide
plan: 04
subsystem: ui
tags: [react-native, expo-router, kakao-compressed-video, figma-dialog-pattern, not-pole, upload-guide]

# Dependency graph
requires:
  - phase: 26-onboarding-upload-guide
    provides: "26-03 buildOptInRouteParams 순수 헬퍼 + lowQuality 승인 플래그 라우팅 (D-07 화질 우선 분기 배선)"
provides:
  - "isKakaoCompressedVideoName 순수 헬퍼 (named export) — _talkv_ 카톡 압축본 감지 단일점 (D-06)"
  - "카톡 압축본 경고 다이얼로그 (Figma Dialog Pattern) + talkv → lowQuality → bodyProfile 게이트 직렬 체인"
  - "continueTalkv 가 lowQuality:true 승인 플래그 심어 D-07 화질 우선 분기 연동 (신규 분기 0)"
  - "not_pole 실패 화면(플래그 없는) 구도/거리 원인 + 재촬영 안내 (D-01-ii)"
affects: [pilot-upload-flow, not-pole-failure-guidance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "카톡 압축본 감지: 순수 헬퍼(named export, React/expo import 무관) 단일점 — 인라인 includes 중복 금지 (리뷰 MEDIUM-2)"
    - "비차단 경고 게이트 직렬 체인: talkv → lowQuality → bodyProfile, 각 게이트가 다음을 건너뛰어 이중 모달 금지"
    - "카톡 경고 승인 = 기존 lowQuality 플래그 재사용(신규 분기 0)으로 D-07 화질 우선 분기 무료 연동"

key-files:
  created:
    - .planning/phases/26-onboarding-upload-guide/26-04-SUMMARY.md
  modified:
    - app/src/app/(tabs)/analyze.tsx
    - app/src/app/analysis/loading.tsx

key-decisions:
  - "신규 테마 토큰 0 — Figma Dialog Pattern 을 기존 토큰(brandBg 틴트 카드/brand 느낌표/cardBg+inputBorder 보조 버튼/brand filled 주액션)으로 전부 매핑, colors.ts/index.ts 무접촉 (인라인 hex 0)"
  - "기존 저화질 lqCard(흰 카드·세로 버튼) Figma 패턴 재정렬 생략 — 회귀 위험 대비 이득 낮음(재량, 플랜 step 5). talkv 다이얼로그만 Figma 패턴 신규 구현"
  - "카톡 경고 버튼 배치 = 좌 보조 [이대로 계속](secondary)/우 주액션 [다른 영상 선택](brand filled) — 원본 사용 유도가 주액션 (§S4 Copywriting)"
  - "not_pole 플래그 없는 분기(isPlainNotPole)만 구도 카피 — isLowQualityNotPole 조건·카피 문자 그대로 불변(D-07), 게이트/임계 백엔드 무접촉(D-01)"

patterns-established:
  - "advisory 파일명 감지는 하드 차단이 아닌 경고 + 진행 허용 (D-06) — 우회해도 기존 파이프라인 검증이 그대로 적용"

requirements-completed: [ONBD-03]

# Metrics
duration: ~20min
completed: 2026-07-07
---

# Phase 26 Plan 04: 카톡 압축본 감지 경고 + not_pole 구도 안내 Summary

**카톡 압축본(`_talkv_`) pick 시 Figma Dialog Pattern 경고 다이얼로그(D-06)를 띄우되 진행은 허용하고, [이대로 계속] 시 기존 lowQuality 승인 플래그를 심어 D-07 화질 우선 분기를 신규 분기 0 으로 연동하며, 플래그 없는 not_pole 실패 화면에 촬영 구도/거리 원인+재촬영 안내(D-01-ii)를 추가 — 백엔드/게이트 무접촉, JS-only OTA 가능.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 2 (analyze.tsx, loading.tsx)

## Accomplishments

- `isKakaoCompressedVideoName` 순수 헬퍼(named export, 모듈 스코프, React/expo import 무관)로 `_talkv_` 감지를 단일점화 (리뷰 MEDIUM-2) — handleResult 인라인 includes 중복 0
- handleResult 게이트 직렬 체인 구현: talkv 감지 → (미해당 시) checkLowQuality → maybePromptBeforeRoute. 카톡 경고가 화질 경고를 포함·상회하므로 같은 영상에 두 모달 금지 (이중 경고 금지)
- 카톡 압축본 경고 다이얼로그(Figma Dialog Pattern): 연한 브랜드 틴트 카드(brandBg) + 중앙 상단 빨간 원형 느낌표(brand) + 굵은 검정 타이틀 + 회색 본문(textMid) + 가로 2버튼. 전 값 토큰 — 인라인 hex 0
- `continueTalkv` 가 보류 picked 에 `{ ...p, lowQuality: true }` 를 심어 maybePromptBeforeRoute 재개 → quick-260704-fwb 의 not_pole 화질 우선 분기가 추가 코드 없이 연동 (D-07). native back/`cancelTalkv` = 영상 버림 (기존 lq 모달과 동일 안전 동작)
- loading.tsx: 플래그 없는 not_pole(`isPlainNotPole`)에 촬영 구도/거리 원인+재촬영 본문 + tipCard 거리(약 2~3m) 정면 촬영 확인 항목 보강 (D-01-ii). 화질 우선 분기(isLowQualityNotPole) 조건·카피 불변 (D-07)

## Task Commits

Each task was committed atomically:

1. **Task 1: analyze.tsx _talkv_ 감지 헬퍼 + Figma 패턴 경고 다이얼로그 + 게이트 직렬 체인** - `2934326` (feat)
2. **Task 2: loading.tsx not_pole 구도/거리 원인 안내 (D-01-ii)** - `dc0c13d` (feat)

_Plan metadata (SUMMARY): committed separately in worktree mode._

## Files Created/Modified

- `app/src/app/(tabs)/analyze.tsx` - `KAKAO_COMPRESSED_MARKER` 상수 + `isKakaoCompressedVideoName` named export 순수 헬퍼 + `talkvPicked` 보류 상태 + handleResult talkv 게이트(checkLowQuality 앞) + `continueTalkv`(lowQuality:true 심음)/`cancelTalkv` + Figma Dialog Pattern 다이얼로그(brandBg 카드·빨간 느낌표·가로 2버튼) + talkv* 스타일 (토큰만)
- `app/src/app/analysis/loading.tsx` - `isPlainNotPole` 파생 + errorBody 3-way(화질 우선 → 구도 안내 → 기본) + tipCard 플래그 없는 not_pole 분기에 거리/정면 촬영 확인 항목 추가. isLowQualityNotPole 조건식·화질 카피 diff 0

## Decisions Made

- **신규 테마 토큰 0:** Figma Dialog Pattern(26-UI-SPEC §Figma Dialog Pattern)의 요소를 전부 기존 토큰에 매핑했다 — 카드=`colors.brandBg`(연분홍 틴트), 느낌표=`colors.brand`(빨강, Ionicons alert-circle), 타이틀=`typography.sectionTitle`+`colors.textPrimary`, 본문=`typography.caption`+`colors.textMid`(lineHeight 19), 좌 보조 버튼=`colors.cardBg`+`colors.inputBorder` 보더+`typography.buttonSecondary`+`colors.textSecondary`, 우 주액션=`colors.brand` filled+`typography.button`+`colors.textWhite`, radius=`radius.modal`(20). 매핑 불가 토큰이 없어 colors.ts/index.ts 무접촉 (플랜 files_modified 의 colors.ts/index.ts 는 "토큰 신설 시" 조건부 — 신설 불필요로 미변경). 인라인 hex 신규 도입 0 (analyze.tsx diff grep 확인).
- **lqCard 재정렬 생략(플랜 step 5 재량):** 기존 저화질 경고 모달(lqCard, 흰 카드·세로 버튼)을 Figma 패턴으로 정렬하면 레이아웃 전면 교체(세로→가로 버튼)로 D-07 배선 인접 코드 회귀 위험이 이득 대비 크다고 판단해 미정렬 유지. talkv 다이얼로그만 Figma 패턴으로 신규 구현. D-07 로직(continueLowQuality 의 lowQuality:true·checkLowQuality 판정)은 문자 그대로 불변.
- **버튼 주/보조 배치:** §S4 Copywriting 계약대로 좌 보조 `이대로 계속`(secondary)/우 주액션 `다른 영상 선택`(brand filled) — 원본 사용 유도가 주액션. 하드 차단 없음(D-06): [이대로 계속] 시 lowQuality 플래그 심고 maybePromptBeforeRoute 재개.
- **not_pole 본문 카피 교체:** 플래그 없는 not_pole 본문을 §S6 구도 안내 카피로 설정(기존 ERROR_MESSAGE.not_pole_motion 의 "폴스포츠 동작이 맞는지" 취지는 tipCard "· 폴스포츠 연습 영상이 맞는지" 항목이 계속 커버). 타이틀 `기준 동작과 너무 달라요` 는 불변.

## Deviations from Plan

None (auto-fix). 플랜이 명시적으로 허용한 재량 2건(신규 토큰 미신설, lqCard 재정렬 생략)은 위 Decisions 에 사유 기록.

## Figma Frame Extraction Note

- 이 실행은 라이브 Figma MCP 프레임 추출을 수행하지 않았다 — 대상 노드 URL/데스크톱 선택이 주어지지 않아 특정 다이얼로그 프레임을 타깃할 수 없었다. 대신 belle 가 실물 확인(2026-07-07) 후 gsd-ui-researcher 가 26-UI-SPEC §Figma Dialog Pattern 으로 추출·박제한 계약(브랜드 틴트 카드 + 빨간 원형 느낌표 + 가로 2버튼, 토큰 매핑 포함)을 구현했다. UI-SPEC 이 "구조 요약이며 실물 프레임 추출이 요약보다 우선"이라 규정하나, 실물 프레임 접근 경로가 없는 상태에서 UI-SPEC 이 유일한 박제 계약이다. 실물 프레임과의 픽셀 정합 최종 확인은 26-06 실기기 checkpoint 에 위임.

## Threat Model Coverage

- **T-26-09 (Spoofing, _talkv_ 감지 우회):** accept 유지 — 감지는 경고용 advisory. 파일명 변경으로 우회해도 기존 validate/게이트가 그대로 적용, 하드 차단이 아니라 우회 이득 없음 (D-06 설계 의도).
- **T-26-10 (Tampering, D-07 분기 회귀):** mitigate 달성 — continueTalkv 가 기존 lowQuality 플래그 재사용(신규 분기 0), isLowQualityNotPole 조건식 diff 0(grep 확인), 감지 순수 헬퍼 단일점(인라인 includes 중복 0).
- **T-26-11 (DoS, 게이트 체인 데드락):** mitigate 달성 — 직렬 체인(talkv → lowQuality → bodyProfile), talkv 승인/취소 단일 함수 수렴, native back = 영상 버림(기존 안전 동작).
- **T-26-SC (패키지 설치):** 해당 없음 — 패키지 설치 0.

## Verification

- `npm --prefix app run typecheck` GREEN (두 태스크 모두 exit 0) — 워크트리 node_modules 부재로 메인 체크아웃 동일 의존성(package.json 무변경) 임시 심볼릭 링크 후 typecheck, 커밋 전 링크 제거 (커밋 미포함).
- backend/ diff 0 — D-01 게이트 불변.
- analyze.tsx: `_talkv_`(2) / `isKakaoCompressedVideoName`(2) / `talkvPicked`(3) / `lowQuality: true`(2) / `다른 영상 선택`(8) grep 통과, talkv 게이트(L299) < checkLowQuality(L304) 순서 확인, 신규 hex 0.
- loading.tsx: `구도`(3) / `isLowQualityNotPole`(6) grep 통과, `기준 동작과 너무 달라요`/`화질이 낮아 분석하지 못했을 수 있어요` 타이틀 불변, 신규 hex 0, backend diff 0.
- 실기기 확인(카톡 실파일 pick → 경고 → 진행 → 실패 시 화질/구도 문구)은 26-06 checkpoint 항목.

## Deferred Verification (scope fence)

- 앱 정적 게이트는 typecheck 뿐 (JS 테스트 러너 미구성). isKakaoCompressedVideoName 는 순수 함수로 추출돼 추후 테스트 하니스 도입 시 단위테스트 대상. talkv 경고 노출·진행·이중 경고 부재·D-07 화질 우선 문구의 행위 증거는 26-06 실기기 기록이 담당.

## Self-Check: PASSED

analyze.tsx + loading.tsx 수정 파일 존재, 두 커밋(2934326, dc0c13d) git log 존재, typecheck GREEN, backend diff 0.

---
*Phase: 26-onboarding-upload-guide*
*Completed: 2026-07-07*
