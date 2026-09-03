---
phase: quick-260903-f2w
plan: 01
status: complete
subsystem: app-result-fault-zoom
tags: [fault-zoom, topfix-card, composite-png, fresh-url-single-source, collapsed-row-pill]
requires: [quick-260824-q6p-fresh-zoom-urls, phase-27-fault-zoom-deferred, phase-32-deduction-card]
provides:
  - faultZoomUrls.resolveZoomImageUrl(zoom, freshMap) — 시트·카드 공용 fresh 우선/저장 imageUrl 폴백 단일 출처
  - DeductionCard zoom {imageUrl} 합성 PNG 1장 모델 + ZOOM_COMPOSITE_ASPECT(726x360 lockstep) + pending placeholder 1개 + hasZoom 접힘 pill
  - result.tsx topFix 카드 인라인 확대비교 배선(히스토리 첫 연결) + '다른 감점 항목' 접힌 행 hasZoom 배선
affects: [next-app-build-1.2.4, simulator-visual-check, belle-table3-review]
key-files:
  created: []
  modified:
    - app/src/lib/faultZoomUrls.ts
    - app/src/lib/__tests__/faultZoomUrls.test.ts
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/components/DeductionCard.tsx
    - app/src/app/analysis/result.tsx
key-decisions:
  - "카드 인라인 이미지 URL 조회는 resolveZoomImageUrl 한 곳 — 시트 renderCrop 의 인라인 조회식을 그 함수 소비로 교체(동작 동일, 규칙 사본 0)"
  - "카드 컨테이너 종횡비는 백엔드 fault_zoom._compose 정확값 (360*2+6)/360 — 시트의 imgW/2 근사와 달리 레터박스 0"
  - "이미지 로드 실패 상태에서는 좌/우 태그를 숨김 — 실패 캡션 위에 '내 영상/정은지 선수' 라벨이 남는 모순 표시 회피 (플랜 미지정, 실행자 판단)"
requirements-completed: [quick-260903-f2w]
metrics:
  duration: ~15m (커밋 2026-09-03T01:57Z ~ 02:01Z, 읽기 포함 추정)
  tasks: 3/3
  commits: [d4926299, ca41216f, ce6e6c20]
completed: 2026-09-03
---

# quick-260903-f2w: topFix 카드 확대비교 합성 PNG 인라인 + 접힌 행 사진 유무 Summary

**DeductionCard 가 doc 모양 그대로 합성 PNG 1장(`zoom {imageUrl}`)을 정확 종횡비로
인라인 렌더하고, result.tsx 가 topFix 카드에 그것을 처음 배선했다 (표 3 행 4 유령
스피너 결함 해소). '다른 감점 항목' 접힌 행마다 "확대 사진" pill 로 사진 유무를
보인다 (표 3 행 1). fresh 재발급 규칙은 `resolveZoomImageUrl` 한 곳으로 시트·카드가
공유한다.**

## 태스크별 결과

### Task 1 — faultZoomUrls: resolveZoomImageUrl 단일 출처 + 테스트 (d4926299)

- `app/src/lib/faultZoomUrls.ts`: `resolveZoomImageUrl(zoom, freshMap)` 추가 —
  `freshMap?.[zoomCardKey(zoom)]` 가 비어있지 않은 문자열일 때만 fresh, 아니면
  `zoom.imageUrl`. 빈 문자열 fresh 값은 무시(저장값 폴백).
- `app/src/components/DeductionDetailSheet.tsx` `renderCrop`: 인라인
  `freshZoomUrls?.[zoomCardKey(zoom)] ?? zoom.imageUrl` → `resolveZoomImageUrl(zoom,
  freshZoomUrls)`. `zoomCardKey` import 제거(주석 1곳의 설명 언급만 남음).
- `app/src/lib/__tests__/faultZoomUrls.test.ts`: 3건 추가 — fresh 우선 /
  부재·미등재 키·빈 문자열 = 저장 imageUrl / advisory·confirmed 같은 joint 키 분리.
- 게이트: tsc 0 오류, node --test 215 pass / 0 fail (기준선 212 + 3).

### Task 2 — DeductionCard: 합성 PNG 1장 모델 + 접힘 행 사진 표시 (ca41216f)

- `DeductionCardZoomPair {userUri, refUri}` 삭제 → `export interface DeductionCardZoom
  { imageUrl: string }`. props `zoomPair?` → `zoom?`, 신규 `onZoomImageError?`,
  `hasZoom?`. (zoomPair 는 리포 어디서도 넘겨진 적 없음 — grep 으로 확인 후 제거.)
- `ZOOM_COMPOSITE_ASPECT = (360 * 2 + 6) / 360` — 주석에 `fault_zoom._compose`
  lockstep 출처(`_OUT=360`, `gap=6`, 캔버스 726x360).
- 펼침 3) 블록: `zoomFrame`(width 100%, aspectRatio 상수, radius.listItem,
  overflow hidden, softBg) 안에 `Image` 1장 `contain` + 기존 zoomSkeleton 오버레이 +
  onError 시 IMG_FAILED_CAPTION 렌더 및 `onZoomImageError?.()` 호출. 좌상단 "내 영상",
  우상단 `rightLabel` 태그(zoomTagLeft/Right). accessibilityLabel "내 영상과 {rightLabel}
  확대 비교 이미지".
- 이미지 상태 훅 1쌍(loading/failed) + `zoom?.imageUrl` 변경 시 `useEffect` 리셋.
- `zoomPending`: 스피너 2개 정사각 → 같은 종횡비 컨테이너 1개 + ActivityIndicator +
  ZOOM_PENDING_CAPTION 텍스트. accessibilityRole progressbar 유지.
- 접힘 모드: `hasZoom` 이면 헤드라인과 chevron 사이에 pill(`image-outline` 14 +
  "확대 사진", caption/textSecondary/softBg/radius.listItem). accessibilityLabel 에
  " — 확대 사진 있음" 접미.
- 죽은 스타일 `zoomRow/zoomHalf` 제거 — 정의/참조 대조로 defined-but-unused 0,
  used-but-undefined 0. 토큰만, 이모지 0.
- 모듈 헤더 주석의 "결함 확대쌍(내 vs 정은지 crop)" 서술을 합성 PNG 1장으로 정정.
- 게이트: tsc 0 오류, node --test 215 / 0.

### Task 3 — result.tsx: topFix 카드 zoom 배선 + 접힌 행 hasZoom 배선 (ce6e6c20)

- import 에 `resolveZoomImageUrl` (기존 `useFreshFaultZoomUrls` import 줄에 합침).
- `matchZoomForRecord` 정의 아래(2015)에 `const topFixZoom = topFixRecord ?
  matchZoomForRecord(topFixRecord) : null;` (useMemo 없이 렌더마다 — 다른 호출부와 동일).
- topFix `<DeductionCard>`: `zoom={topFixZoom ? { imageUrl: resolveZoomImageUrl(topFixZoom,
  freshZoomUrls) } : undefined}` + `onZoomImageError={onZoomImageError}`.
  `zoomPending` 유지(카드가 zoom 우선).
- "확대 비교 자세히 보기" 링크 조건 `matchZoomForRecord(topFixRecord) || zoomPending`
  → `topFixZoom || zoomPending` (동일 값, 중복 호출 제거). 문구·시트 진입 그대로.
- '다른 감점 항목' 접힌 행: `hasZoom={matchZoomForRecord(rec) != null}`.
- 무접촉 확인: recordMaps/cueWindows/시트 배선/estimatedArea 진입점(3044 링크)/문구.
- 게이트: tsc 0 오류, node --test 215 / 0. `grep zoomPair` 는 result.tsx 2107
  recordMaps 주석 1건만(resultSections 타입 필드 서술), DeductionCard 0.
  `grep -rn "DeductionCardZoomPair\|userUri\|refUri" app/src` 0건.

## 최종 게이트

| 게이트 | 기준선 | 최종 |
|---|---|---|
| `cd app && npx tsc --noEmit` | 0 오류 | 0 오류 |
| `cd app && node --test "src/lib/__tests__/*.test.*"` | 212 pass / 0 fail | 215 pass / 0 fail |
| `grep -rn "DeductionCardZoomPair\|userUri\|refUri" app/src` | — | 0건 |
| 무접촉 목록 diff (app.json / analysis.ts / deductionLabels.ts / deductionSheet.ts / backend/) | — | 0 |

## 플랜 대비 편차

플랜 태스크·파일·검증 전부 그대로 실행. 편차/판단 사항:

1. **[실행자 판단 — 플랜 미지정]** 이미지 로드 실패 상태에서는 좌/우 태그("내 영상"/
   rightLabel)를 숨긴다. 종전 코드는 실패 캡션 위에도 태그를 그렸는데, 실패 박스 위에
   비교 라벨이 남으면 모순 표시라 실패 캡션만 남겼다. 로드 성공/로딩 중에는 태그 표시.
2. **[Task 3 검증 grep 정합]** DeductionCard 헤더 주석에 종전 모양을 `zoomPair {userUri,
   refUri}` 로 인용했다가 플랜 검증(`userUri|refUri` 0건)에 걸리지 않게 "사진 2장 분리
   URI 쌍" 서술로 바꿨다 (Task 2 커밋 전 정정, 코드 영향 0).
3. **[STATE/ROADMAP 무접촉]** quick 태스크라 `state.advance-plan` 등 페이즈 카운터
   갱신은 실행하지 않았다 (오케스트레이터 지시: docs 커밋·STATE 는 오케스트레이터 몫,
   ROADMAP 갱신 금지). SUMMARY/PLAN/STATE 미커밋.
4. **[관측 — 무접촉]** 실행 도중 `app/scripts/copy-analysis-to-sim.mjs` 가 untracked 로
   나타났다 (초기 status 에 없던 파일, 이 작업이 만든 것 아님). 스테이징하지 않고 그대로 둠.

## 남은 것 (이 작업 범위 밖)

- 시뮬레이터 실물 확인 — 오케스트레이터 후속 (개발 빌드 셸 + Metro, 확대 카드가 있는
  doc 필요). 확인 포인트: topFix 카드 인라인 PNG 종횡비(레터박스 0), pending →
  done 전환 시 이미지 교체, 접힌 행 "확대 사진" pill, 7일 넘은 doc fresh 재발급.
- 앱 문구/네이티브 → 빌드는 belle 확정분 모아 1.2.4 한 빌드 (버전 범프 없음).
- 표 3 행 2(클라임 eye)·행 3(advisory 노출)·행 5(스테이지 순서) 는 belle ○× 대기 — 무접촉.

## Known Stubs

없음 — 카드 `zoom` 은 실제 `result.faultZoomComparisons` 매칭 결과에서 채워지고,
부재 시 종전과 같이 생략/pending placeholder 만 렌더한다.

## Threat Flags

없음 — 신규 네트워크 경로·권한·스키마 변경 0. 이미지 URL 은 기존 presigned/재발급
경로(quick-260824-q6p) 그대로.

## Self-Check: PASSED

- FOUND: app/src/lib/faultZoomUrls.ts (`export function resolveZoomImageUrl`)
- FOUND: app/src/lib/__tests__/faultZoomUrls.test.ts
- FOUND: app/src/components/DeductionDetailSheet.tsx
- FOUND: app/src/components/DeductionCard.tsx (`ZOOM_COMPOSITE_ASPECT`, `726`)
- FOUND: app/src/app/analysis/result.tsx (`resolveZoomImageUrl` 3건)
- FOUND commits: d4926299, ca41216f, ce6e6c20
