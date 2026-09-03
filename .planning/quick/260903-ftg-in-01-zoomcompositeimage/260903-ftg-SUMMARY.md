---
phase: quick-260903-ftg
plan: 01
status: complete
subsystem: app-result-fault-zoom
tags: [fault-zoom, in-01, attribution-unreliable, composite-png, estimated-area-cards, zoom-composite-image]
requires: [quick-260903-f2w, quick-260724-q6b, quick-260824-q6p]
provides:
  - components/ZoomCompositeImage — 합성 PNG 1장 프레임(정확 종횡비 ZOOM_COMPOSITE_ASPECT)+좌/우 태그+로딩 skeleton+실패 캡션+onError 재발급+pending placeholder (DeductionCard·IN-01 카드 공용, 사본 0)
  - lib/resultSections.selectEstimatedZoomEntries — IN-01 저신뢰 경로 확정 카드 전부 선택 순수 함수(primary 맨 앞·숨김 제외·같은 카드 dedupe)
  - result.tsx IN-01 블록 — 진입 링크 1개 → "예상 부위 (참고)" 사진 카드 목록(확정 카드 전부 인라인, 탭 → 각자 시트)
affects: [next-app-build-1.2.4, simulator-visual-check, belle-table-review]
key-files:
  created:
    - app/src/components/ZoomCompositeImage.tsx
  modified:
    - app/src/components/DeductionCard.tsx
    - app/src/lib/resultSections.ts
    - app/src/lib/__tests__/resultSections.test.ts
    - app/src/app/analysis/result.tsx
key-decisions:
  - "합성 PNG 렌더는 ZoomCompositeImage 한 컴포넌트가 소유 — DeductionCard 와 IN-01 카드가 같은 것을 소비(이동, 복제 아님). f2w 실행자 판단(실패 시 좌/우 태그 숨김) 승계"
  - "IN-01 카드 제목 = 시트 제목(ESTIMATED_AREA_TITLE)과 문자 동일한 '예상 부위 (참고)' — 관절명·statusLine·수치 0 (260724-q6b 락 유지). 접근성 라벨은 종전 ATTR_ZOOM_ESTIMATED_ENTRY_LABEL"
  - "카드 간격은 content 컨테이너 gap(14) — 종전 링크의 marginTop 4 제거 (카드 2장 스택 시 4pt 는 너무 촘촘, 별도 마진 도입 안 함)"
  - "primary(estimatedAreaRecordIndex)가 범위 밖이면 무시하고 원 순서 — 폴백 경로(windowMedian) 대비 방어"
requirements-completed: [quick-260903-ftg]
metrics:
  duration: 커밋 구간 4m (5f01d1bb 11:29:16 ~ 57c711ed 11:33:16 KST 실측) + 선행 읽기 ~15m 추정
  tasks: 3/3
  commits: [5f01d1bb, b5c13d52, 57c711ed]
completed: 2026-09-03
---

# quick-260903-ftg: IN-01 저신뢰 경로 확대비교 사진 인라인(확정 카드 전부) + ZoomCompositeImage 단일화 Summary

**역립 저신뢰(`attributionReliability.unreliable=true`) 문서에서 확정 확대비교 사진이
"예상 부위 (참고)" 카드로 전부 인라인 렌더된다 — belle pdshape 60점 doc 이면 왼팔꿈치·
왼엉덩이 2장, 탭하면 각자의 시트. 종전엔 링크 1개 뒤 |points| 최대 record 1건의
시트만 열려 두 번째가 도달 불가였다(belle 09-02 "왜 확대비교 사진이 하나밖에 없어").
합성 PNG 렌더는 `ZoomCompositeImage` 한 컴포넌트로 뽑아 DeductionCard(topFix)와 IN-01
카드가 같은 것을 소비한다. 관절명·statusLine·수치는 계속 내지 않는다(IN-01 락 유지).**

## 태스크별 결과

### Task 1 — ZoomCompositeImage 컴포넌트 추출 + DeductionCard 소비 (5f01d1bb)

- 신규 `app/src/components/ZoomCompositeImage.tsx`:
  `export const ZOOM_COMPOSITE_ASPECT = (360 * 2 + 6) / 360` (DeductionCard 에서
  이동, `fault_zoom._compose` lockstep 주석 유지) +
  `export function ZoomCompositeImage({ imageUrl, pending, leftLabel='내 영상', rightLabel, onError, accessibilityLabel })`.
  · `imageUrl` 있으면 프레임(width 100%, aspectRatio, radius.listItem, overflow hidden,
    softBg) + Image contain + 로딩 skeleton + 실패 캡션(태그 숨김 — f2w 판단 승계) +
    좌/우 태그 + `useEffect([imageUrl])` 리셋 + onError → 실패 상태 + `onError?.()`.
  · 없고 `pending` 이면 같은 프레임에 ActivityIndicator + '확대 비교 이미지를 준비하고
    있어요' (accessibilityRole progressbar). 둘 다 아니면 null. 훅은 조기 반환 전 호출.
  · 상수(IMG_FAILED_CAPTION/ZOOM_PENDING_CAPTION)·스타일(frame/image/skeleton/
    fallback*/pending*/tag*) 전부 DeductionCard 에서 **이동**.
- `DeductionCard.tsx`: 3) 블록을 `zoom ? <ZoomCompositeImage imageUrl rightLabel onError
  accessibilityLabel/> : zoomPending ? <ZoomCompositeImage pending rightLabel/> : null`
  로 교체. 상태 훅 2개·useEffect·상수 2개·ZOOM_COMPOSITE_ASPECT·스타일 11개 제거,
  `useState/useEffect/ActivityIndicator/Image` import 제거(`import React` 는 tsconfig
  `jsx: react-native` 라 유지). `zoomPill` 접힘 표시 그대로. 헤더 주석 1단락 추가.
- 게이트: tsc 0, node --test 215 / 0. 플랜 grep
  (`ZOOM_COMPOSITE_ASPECT|zoomSkeleton|zoomFallback` in DeductionCard) 0건.
  defined-but-unused 스타일 0 (두 파일 모두 정의/참조 대조).

### Task 2 — selectEstimatedZoomEntries 순수 함수 + 테스트 4건 (b5c13d52)

- `resultSections.ts`: `EstimatedZoomEntry<Z> { recordIndex; zoom }` +
  `selectEstimatedZoomEntries<R, Z>(records, matchZoom, zoomKey, isHidden, primaryIndex)`.
  규칙: 유효한 primaryIndex(정수·범위 내) 맨 앞, 나머지 원 순서 / 숨김 제외 / 매칭
  없음 제외 / `zoomKey` 동일 카드 첫 등장만 / records null·undefined·빈 배열 = 빈 배열
  (matchZoom 미호출). 제네릭 — RN/doc 타입 의존 0, record 내용(관절명·수치) 접근 불가.
- `resultSections.test.ts` Test 7-1~7-4 (node:test): primary 맨 앞(+ null 원 순서 +
  범위 밖 무시) / 숨김 제외(primary 가 숨김이어도) / 좌+우 묶음 dedupe(primary 가 r1
  이면 묶음 카드가 r1 에 붙고 r0 dedupe) / 매칭 0·빈 입력 = 빈 배열 + matchZoom
  호출 0 확인. 헤더 검증 축 목록에 7) 추가.
- 게이트: node --test **219 pass / 0 fail** (215 + 4), tsc 0.

### Task 3 — result.tsx IN-01 진입 링크 → 예상 부위 사진 카드 목록 (57c711ed)

- import: `ZoomCompositeImage`(components), `selectEstimatedZoomEntries`(기존
  resultSections import 줄에 합침), `zoomCardKey`(기존 faultZoomUrls import 줄에 합침).
- 상수: `ATTR_ZOOM_ESTIMATED_CARD_TITLE = '예상 부위 (참고)'` — 시트 제목과 문자
  동일, 관절명 없음 주석. `ATTR_ZOOM_ESTIMATED_ENTRY_LABEL` 은 accessibilityLabel 로 유지.
- `topFixZoom` 아래에 `estimatedZoomEntries = useMemo(() => attributionUnreliable ?
  selectEstimatedZoomEntries(records, matchZoomForRecord, zoomCardKey, isRecordHidden,
  estimatedAreaRecordIndex) : [], [attributionUnreliable, records,
  result.faultZoomComparisons, vetoFaultJoints, hiddenRecordIds, estimatedAreaRecordIndex])`
  — recordMaps memo 관례(eslint-disable 주석). `isRecordHidden`(1962)·
  `matchZoomForRecord`(2005) 정의 뒤라 참조 안전.
- IN-01 블록 교체: `attributionUnreliable && entries.length > 0` → `entries.map` Pressable
  카드(`estimatedZoomCard`: advisoryOrangeBg·radius.card·padding cardPadding·gap 10) 안에
  제목 행(`estimatedZoomTitleRow`: 제목 advisoryOrange bodyMdBold + chevron ›) +
  `<ZoomCompositeImage imageUrl={resolveZoomImageUrl(entry.zoom, freshZoomUrls)}
  rightLabel={mode1 ? '{선수} 선수' : '지난 영상'} onError={onZoomImageError}
  accessibilityLabel="예상 부위 (참고) 확대 비교 이미지"/>`. key = `zoomCardKey(entry.zoom)`,
  onPress → `setDetailRecordIndex(entry.recordIndex)`. else `zoomPending &&
  estimatedAreaRecordIndex != null` → 같은 카드 1개에 `<ZoomCompositeImage pending/>`
  (탭 → 종전 시트). 그 외 미렌더. **관절명·statusLine·수치 렌더 0.**
- 스타일: `estimatedZoomEntry`(링크 컨테이너, marginTop 4) → `estimatedZoomCard` +
  `estimatedZoomTitleRow`. `estimatedZoomEntryPressed/Text/Chevron` 재사용 유지.
  `styles.estimatedZoomEntry` 잔존 참조 0.
- 무접촉 확인: result.tsx diff 훅 = import 3·상수 1·memo 1·IN-01 블록·스타일 블록뿐
  (topFix 블록 2636 부근, '다른 감점 항목' 블록 3085 이후 훅 0). 저신뢰 아닌 경로는
  `estimatedZoomEntries=[]` + `attributionUnreliable=false` 라 렌더 diff 0.
- 게이트: tsc 0, node --test 219 / 0. `git diff --stat` 이 태스크에서 result.tsx 만.

## 최종 게이트

| 게이트 | 기준선 | 최종 |
|---|---|---|
| `cd app && npx tsc --noEmit` | 0 오류 | 0 오류 |
| `cd app && node --test "src/lib/__tests__/*.test.*"` | 215 pass / 0 fail | **219 pass / 0 fail** |
| `grep -rn "ZOOM_COMPOSITE_ASPECT" app/src` | — | ZoomCompositeImage.tsx 정의 1 + 자체 소비 1 (다른 파일 0) |
| `grep -n "ZOOM_COMPOSITE_ASPECT\|zoomSkeleton\|zoomFallback" DeductionCard.tsx` | — | 0건 |
| 무접촉 목록 diff (analysis.ts / deductionLabels.ts / deductionSheet.ts / DeductionDetailSheet.tsx / app.json / backend/) | — | 0 |

## 플랜 대비 편차

플랜 태스크·파일·검증 전부 그대로 실행. 판단 사항:

1. **[실행자 판단 — 플랜 미지정]** 카드 간격: 종전 링크의 `marginTop: 4` 를 카드에
   승계하지 않았다. IN-01 블록의 부모(`styles.content`)가 `gap: 14` 라 카드 2장이
   자연히 14pt 로 쌓이고, 안내줄과의 간격도 다른 섹션과 같은 14 가 된다(종전 18).
2. **[실행자 판단 — 플랜 미지정]** `selectEstimatedZoomEntries` 의 primaryIndex 는
   정수·범위 내일 때만 맨 앞으로, 아니면 무시하고 원 순서 (테스트 7-1 에 고정).
   estimatedAreaRecordIndex 는 records 에서 유도되므로 실제로는 항상 범위 내다 —
   방어만.
3. **[실행자 판단 — 플랜 미지정]** `ZoomCompositeImage` 의 accessibilityLabel 기본값은
   `'{left} · {right} 확대 비교 이미지'` (조사 과/와 문제 회피). 두 소비처 모두
   플랜대로 명시 라벨을 넘기므로 기본값은 실제 경로에서 쓰이지 않는다.
4. **[STATE/ROADMAP 무접촉]** quick 태스크라 `state.advance-plan` 등 페이즈 카운터
   갱신은 실행하지 않았다 (오케스트레이터 지시: docs 커밋·STATE 는 오케스트레이터 몫,
   ROADMAP 갱신 금지). SUMMARY/PLAN/STATE 미커밋.
5. **[관측 — 무접촉]** `.planning/research/report-restructure-review-2026-09-02.md` 가
   시작 시점부터 modified 상태였다(이 작업이 만든 것 아님). 스테이징하지 않음.

## 남은 것 (이 작업 범위 밖)

- 시뮬레이터 실물 확인 — 오케스트레이터 후속 (Metro Fast Refresh, belle pdshape 60점
  doc 복사본). 확인 포인트: "예상 부위 (참고)" 카드 2장(왼팔꿈치·왼엉덩이 합성 PNG)
  인라인, 각 탭 → 각자의 시트(estimatedArea hedge), 저신뢰 아닌 doc 은 topFix 카드
  인라인(f2w) 그대로. 스크린샷 `screens/`.
- advisory 카드(belle 판정 대기)·매칭 규칙·계약·백엔드·문구 재배치(표 1·2) 무접촉.

## Known Stubs

없음 — 카드 목록은 실제 `result.faultZoomComparisons` 매칭 결과(`matchZoomForRecord`
단일 출처)에서 채워지고, 부재 시 종전과 같이 생략/pending placeholder 만 렌더한다.

## Threat Flags

없음 — 신규 네트워크 경로·권한·스키마 변경 0. 이미지 URL 은 기존 presigned/재발급
경로(quick-260824-q6p, `resolveZoomImageUrl`) 그대로.

## Self-Check: PASSED

- FOUND: app/src/components/ZoomCompositeImage.tsx (`export function ZoomCompositeImage`, `export const ZOOM_COMPOSITE_ASPECT`)
- FOUND: app/src/components/DeductionCard.tsx (`ZoomCompositeImage` 소비, 이동 심볼 0)
- FOUND: app/src/lib/resultSections.ts (`export function selectEstimatedZoomEntries`)
- FOUND: app/src/lib/__tests__/resultSections.test.ts (Test 7-1~7-4)
- FOUND: app/src/app/analysis/result.tsx (`selectEstimatedZoomEntries`, `ZoomCompositeImage`, `ATTR_ZOOM_ESTIMATED_CARD_TITLE`)
- FOUND commits: 5f01d1bb, b5c13d52, 57c711ed
