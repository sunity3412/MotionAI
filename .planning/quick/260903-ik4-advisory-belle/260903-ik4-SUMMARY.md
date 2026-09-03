---
phase: quick-260903-ik4
plan: 01
status: complete
subsystem: app-result-fault-zoom
tags: [fault-zoom, advisory, tier, zoom-composite-image, belle-review-row-3, result-sections]
requires: [quick-260903-ftg, quick-260704-fz4, quick-260831-lcc, quick-260730-szk]
provides:
  - lib/resultSections.selectAdvisoryZooms — tier==='advisory' 카드만 doc 순서 보존, 불량 항목 제외, null 안전 (record 조인 없음)
  - result.tsx '참고 부위' 섹션 — '다른 감점 항목' 뒤·기준 모션 메타 카드 앞, 카드마다 승인 칩 + 부위 1줄 + 합성 PNG(ZoomCompositeImage), 끝에 ADVISORY_NOTE_KO
affects: [simulator-visual-check, belle-table-review-row-3, next-app-build-1.2.4]
key-files:
  created: []
  modified:
    - app/src/lib/resultSections.ts
    - app/src/lib/__tests__/resultSections.test.ts
    - app/src/app/analysis/result.tsx
key-decisions:
  - "참고 카드는 record 와 조인하지 않고 카드 자체를 보여준다 — 확정 카드 매칭(matchZoomForDeductionRecord)의 advisory 제외 규칙 무접촉, selectAdvisoryZooms 가 그 짝"
  - "섹션 키 체계(deriveResultSections)는 D-02 10항 가시성만 소유하고 배치 순서는 JSX 가 소유하므로(IN-01 블록·기준 모션 메타 카드도 키 없음) 'advisory' 키를 추가하지 않고 게이트 없이 렌더 — RESULT_SECTION_ORDER·Test 1 무접촉"
  - "칩 글자는 typography.badge(17/600) — 플랜의 caption(12) 대신. D-05 결과 화면 하한 17(typography.ts 주석: caption 12 가 belle '전반이 너무 작음'의 실체) + PartChipsRow 칩·DeductionCard badgePill 선례. 한 줄로 되돌릴 수 있음"
  - "카드는 styles.card 그대로 + advisoryCard{alignItems:'stretch', gap:10} — card 의 alignItems center 를 덮어 부위 줄·PNG 좌측 정렬·전폭 (refCard flex-start 선례)"
requirements-completed: [quick-260903-ik4]
metrics:
  duration: 커밋 구간 ed9f9bed → 7827ea74 (실측은 git log 참조) + 선행 읽기
  tasks: 2/2
  commits: [ed9f9bed, 7827ea74]
completed: 2026-09-03
---

# quick-260903-ik4: 참고(advisory) 확대 카드 '참고 부위' 섹션 — belle ○× 대기 Summary

**doc 에 `tier='advisory'` 확대 카드가 있으면 결과 화면 '다른 감점 항목' 뒤에 '참고 부위'
섹션이 뜨고, 카드마다 승인 칩(`ADVISORY_CHIP_KO`) + 부위 1줄 + 합성 PNG 가 인라인으로
보이며 끝에 `ADVISORY_NOTE_KO` 안내 1줄이 붙는다 — 저신뢰(IN-01)·일반 두 경로 공통.
종전엔 백엔드 `fault_zoom.select_advisory_joints` 가 만든 참고 카드(belle 계정 최근
6동작 8장)를 앱 어디에도 사진으로 보여주지 않았다(부위 칩 행은 이름만). 클라임 92점
(확정 0장·참고 2장)은 이 섹션이 결과 화면의 유일한 사진이 된다. 감점 수치·statusLine
0, 탭 없음, 색 중립(빨강·주황 0). 확정 카드 표면(topFix·IN-01 예상 부위·접힌 행·시트)과
매칭 규칙·계약·백엔드는 무접촉. belle ○× 대기(검토 표 3 행 3) — × 면 두 커밋 revert.**

## 태스크별 결과

### Task 1 — selectAdvisoryZooms 순수 함수 + 테스트 3건 (ed9f9bed)

- `app/src/lib/resultSections.ts` 끝에
  `export function selectAdvisoryZooms<Z extends { tier?: string | null; imageUrl?: string; joint?: string }>(comparisons: readonly Z[] | null | undefined): Z[]`.
  규칙: `Array.isArray` 아니면 `[]` / 비객체·null 항목 제외 / `tier === 'advisory'` 만 /
  빈 `imageUrl` 제외 / `joint` 부재·빈 문자열 제외 / doc 순서 보존, 항목은 원본 참조
  (복제 아님 — result.tsx 가 `resolveZoomImageUrl`/`zoomCardKey` 에 같은 객체를 넘긴다).
  헤더 주석: 백엔드 select_advisory_joints 배경, 확정 카드 매칭의 advisory 제외와 짝
  (record 조인 없음), 제네릭이라 수치·statusLine 접근 불가.
- `resultSections.test.ts` Test 8-1~8-3 (node:test) + 헤더 검증 축 8) 추가:
  8-1 advisory 만·doc 순서·원본 참조·입력 무변형 / 8-2 confirmed·tier 부재(legacy)·
  `tier: null` 제외, 확정만 있는 doc = `[]` / 8-3 빈 imageUrl·빈 joint·joint 부재·null
  항목 제외 + `null`/`undefined`/`[]` → `[]`.
- 게이트: tsc 0, node --test **222 pass / 0 fail** (기준선 219 + 3).

### Task 2 — result.tsx '참고 부위' 섹션 (7827ea74)

- import: `selectAdvisoryZooms`(resultSections 기존 줄), `REGION_LABEL_KO`(deductionLabels
  기존 줄 — `JOINT_LABEL_KO` 는 이미 import), `ADVISORY_CHIP_KO`·`ADVISORY_NOTE_KO`
  (deductionSheet 기존 줄). `ZoomCompositeImage`·`resolveZoomImageUrl`·`zoomCardKey`·
  `useMemo` 는 기존 import 재사용.
- 상수 `ADVISORY_SECTION_TITLE = '참고 부위'` (ATTR_ZOOM_ESTIMATED_CARD_TITLE 직후) —
  ADVISORY_NOTE_KO 첫 어절과 같은 말, 승인 문구 2종은 deductionSheet 단일 소스 주석.
- `estimatedZoomEntries` memo 직후
  `const advisoryZooms = useMemo(() => selectAdvisoryZooms(result.faultZoomComparisons), [result.faultZoomComparisons]);`
  — 게이트 없음(저신뢰·일반 공통).
- 섹션(신규 3235-3283, `{/* mode1 전용: 기준 모션 메타 카드` 직전):
  `advisoryZooms.length > 0 ? (<> sectionTitle '참고 부위' + map(z → <View key={zoomCardKey(z)} style={[card, advisoryCard]}> 칩(ADVISORY_CHIP_KO) · 부위 1줄(`z.region ? REGION_LABEL_KO[z.region] : JOINT_LABEL_KO[z.joint] ?? z.joint`) · <ZoomCompositeImage imageUrl={resolveZoomImageUrl(z, freshZoomUrls)} rightLabel={mode1 ? '{선수} 선수' : '지난 영상'} onError={onZoomImageError} accessibilityLabel="{부위} 참고 확대 비교 이미지"/>) + advisoryNote(ADVISORY_NOTE_KO) </>) : null`.
  Pressable 아님(시트는 record 기반 — PartChipsRow N-6 동일). 감점 수치·statusLine·초
  표기 0. 주석에 quick-260903-ik4·belle ○× 대기·왜 여기·클라임 유일 사진·게이트 없는
  이유 명시.
- 스타일(`estimatedZoomEntryChevron` 직후): `advisoryCard{alignItems:'stretch', gap:10}`,
  `advisoryChip{alignSelf:'flex-start', softBg, radius.listItem, padding 3/8}`,
  `advisoryChipText{typography.badge, textSecondary}`, `advisoryJoint{bodyMdBold, textPrimary}`,
  `advisoryNote{bodySm, textSecondary}`. 토큰만, 신규 색 0.
- 무접촉 확인(`git diff -U0` 훅 위치): import 54/67/80-81 · 상수 193-197 · memo
  2063-2073 · 섹션 3235-3283 · 스타일 3961-3991 뿐. topFix 블록(2677)·IN-01 예상 부위
  블록(3125-3190)·'다른 감점 항목' 블록(3192-3233) 훅 0. 추가 행 스캔: hex 리터럴 0,
  `colors.brand`/`advisoryOrange` 사용 0(주석에서 제거 선례 언급만), 이모지 0.
- 게이트: tsc 0, node --test 222 / 0.

## 최종 게이트

| 게이트 | 기준선 | 최종 |
|---|---|---|
| `cd app && npx tsc --noEmit` | 0 오류 | **0 오류** |
| `cd app && node --test "src/lib/__tests__/*.test.*"` | 219 pass / 0 fail | **222 pass / 0 fail** |
| 무접촉 목록 (analysis.ts / deductionLabels.ts / deductionSheet.ts / faultZoomUrls.ts / components/* / app.json / backend/) | — | diff 0 (커밋 2개의 파일 = 플랜 3파일뿐) |
| result.tsx topFix·IN-01·'다른 감점 항목' 블록 | 훅 0 | 훅 0 |

## 플랜 대비 편차

플랜 태스크·파일·검증 그대로 실행. 판단 사항:

1. **[실행자 판단 — 플랜 토큰 변경] 칩 글자 `typography.caption` → `typography.badge`.**
   근거: `theme/typography.ts` D-05 블록(32-07 게이트 결정, "결과 화면 하한 17 —
   caption 12 가 belle '전반이 너무 작음'의 실체") + 같은 성격의 칩·배지(PartChipsRow
   칩, DeductionCard badgePill)가 badge 를 쓴다. 이번 산출이 belle 스크린샷 ○× 용이라
   "너무 작음" 재발 위험을 줄였다. 색은 플랜대로 textSecondary. 되돌리려면
   `advisoryChipText` 의 `typography.badge` 한 줄만 `caption` 으로.
2. **[플랜 조건 분기 — 섹션 키 미추가]** 플랜 "isVisible 섹션 체계가 이 화면 순서를
   소유하면 'advisory' 키 추가, 없으면 게이트 없이": `deriveResultSections` 는 D-02
   10항의 **가시성**만 소유하고 배치 순서는 JSX 가 소유한다(IN-01 블록·기준 모션 메타
   카드·구간 점수도 키 없이 렌더). 키를 넣으면 `RESULT_SECTION_ORDER` 와 Test 1 의
   deepEqual 을 함께 바꿔야 해 범위가 커진다 → 게이트 없이 렌더(IN-01 선례).
3. **[실행자 판단 — 플랜 미지정]** `advisoryCard` 에 `alignItems: 'stretch'` 추가 —
   `styles.card` 가 `alignItems: 'center'` 라 부위 Text 가 가운데 정렬되고 PNG 프레임
   폭이 흔들릴 수 있어 refCard(flex-start) 선례대로 덮었다.
4. **[관측 — 무접촉]** 작업 중 `app/scripts/copy-analysis-to-sim.mjs`(이후 ce8eff0f 로
   별도 커밋됨)·`.planning/CONTINUE-2026-09-03.md` 가 modified 로 보였다 — 이 작업이
   만든 것 아님, 스테이징 0.
5. **[STATE/ROADMAP 무접촉]** quick 태스크 — 페이즈 카운터·ROADMAP·docs 커밋은
   오케스트레이터 몫(지시). SUMMARY/PLAN 미커밋.

## 남은 것 (이 작업 범위 밖)

- 시뮬레이터 실물 확인 — 오케스트레이터 후속(Metro Fast Refresh). pdshape 복사본
  (참고 1장 왼쪽 어깨): '예상 부위 (참고)' 카드 2장 아래 '참고 부위' 섹션 1장.
  클라임(참고 2장)은 belle 이 doc 복사 후. 스크린샷으로 belle ○×.
- × 면 `git revert 7827ea74 ed9f9bed` (코드 2커밋).

## Known Stubs

없음 — 카드 목록은 실제 `result.faultZoomComparisons` 의 advisory 항목에서 채워지고,
부재 시 섹션 자체를 렌더하지 않는다.

## Threat Flags

없음 — 신규 네트워크 경로·권한·스키마 변경 0. 이미지 URL 은 기존 presigned/재발급
경로(quick-260824-q6p, `resolveZoomImageUrl`/`onZoomImageError`) 그대로.

## Self-Check: PASSED

- FOUND: app/src/lib/resultSections.ts (`export function selectAdvisoryZooms`)
- FOUND: app/src/lib/__tests__/resultSections.test.ts (Test 8-1~8-3)
- FOUND: app/src/app/analysis/result.tsx (`selectAdvisoryZooms`, `ADVISORY_SECTION_TITLE`, `advisoryZooms`)
- FOUND commits: ed9f9bed, 7827ea74
