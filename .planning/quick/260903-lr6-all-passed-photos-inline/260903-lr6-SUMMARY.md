---
phase: quick-260903-lr6
plan: 01
status: complete
subsystem: app-result-fault-zoom
tags: [fault-zoom, deduction-card, collapsed-row, zoom-composite-image, all-passed-photos-inline]
requires: [quick-260903-ftg, quick-260903-f2w]
provides:
  - components/DeductionCard 접힘 모드 — zoom 이 오면 헤드라인 행 아래 ZoomCompositeImage 인라인(pill 미렌더), zoom 없이 hasZoom 만이면 종전 pill(하위호환)
  - result.tsx '다른 감점 항목' 행 — rowZoom = matchZoomForRecord(rec) 단일 출처로 zoom={resolveZoomImageUrl(rowZoom, freshZoomUrls)} + onZoomImageError 전달
affects: [next-app-build-1.2.4, simulator-visual-check, belle-table-review]
key-files:
  created: []
  modified:
    - app/src/components/DeductionCard.tsx
    - app/src/app/analysis/result.tsx
key-decisions:
  - "접힌 행의 사진은 pill 을 대체한다 — zoom 이 오면 pill 미렌더(사진이 있으니 중복). zoom 없이 hasZoom 만 오는 호출부(현재 0곳)는 종전 pill 그대로 (하위호환)"
  - "접힘 행에서는 zoomPending placeholder 를 내지 않는다 — 플랜 범위 밖. pending 은 종전대로 topFix 카드 1곳"
  - "접근성 라벨 '확대 사진 있음' 은 hasZoom || zoom 일 때 — 문구 신규 0, 조건만 넓힘"
requirements-completed: [quick-260903-lr6]
metrics:
  duration: 편집~커밋 구간 2m (06:42:26Z ~ 06:44:05Z 실측) + 선행 읽기 ~4m
  tasks: 2/2
  commits: [cf5ee317, 79885d83]
completed: 2026-09-03
---

# quick-260903-lr6: 통과한 확정 확대 사진 동작별 전부 인라인 Summary

**일반 경로(저신뢰 아님)에서 확정 확대 사진이 있는 '다른 감점 항목' 행은 접혀 있어도
헤드라인 아래 합성 PNG 가 바로 보인다 — 탭 없이 전부. 종전엔 topFix 카드 1장만
인라인(f2w)이고 나머지는 접힌 행의 "확대 사진" pill 뒤(탭 → 시트)였다(belle 09-03
"동작별로 확장 사진에 들어갈 동작들 통과한거 다 넣고"). 사진 없는 행은 종전 한 줄
그대로, 사진 있는 행 탭은 종전대로 시트. topFix 인라인(f2w)·IN-01 저신뢰 카드(ftg)·
시트·매칭 규칙·계약·백엔드 무접촉.**

## 태스크별 결과

### Task 1 — DeductionCard 접힘 모드 사진 인라인 (cf5ee317)

- `app/src/components/DeductionCard.tsx` 접힘 블록(`expanded === false`):
  `collapsedZoom = zoom ?? null` / `showZoomPill = hasZoom && collapsedZoom == null` /
  `announceZoom = hasZoom || collapsedZoom != null`.
  · 헤드라인 행(헤드라인 + chevron) 아래 `collapsedZoom` 이면
    `<ZoomCompositeImage imageUrl rightLabel onError={onZoomImageError}
    accessibilityLabel={`내 영상과 ${rightLabel} 확대 비교 이미지`}/>` (펼침 모드 3) 블록과
    같은 props).
  · pill 은 `showZoomPill` 일 때만(= zoom 없이 hasZoom 만) — 하위호환.
  · Pressable 전체가 탭 대상 그대로(onToggle → 시트). 간격은 `styles.card` 의 gap 12
    (신규 스타일 0).
- 헤더 주석 1줄(quick-260903-lr6 belle "통과한거 다 넣고") + 접힘 블록 주석 3줄 +
  `zoom` prop 주석(펼침·접힘) 갱신. 상수·스타일·import 변경 0. 문구 신규 0.
- 게이트: tsc 0, node --test 219 / 0. 플랜 artifact `contains: "collapsedZoom"` 충족.

### Task 2 — result.tsx '다른 감점 항목' 행에 zoom 전달 (79885d83)

- `app/src/app/analysis/result.tsx` `records.map` 안(3188~3213):
  `const rowZoom = matchZoomForRecord(rec);` → `hasZoom={rowZoom != null}` +
  `zoom={rowZoom ? { imageUrl: resolveZoomImageUrl(rowZoom, freshZoomUrls) } : undefined}` +
  `onZoomImageError={onZoomImageError}` — topFix 블록(2668~2674)과 같은 규칙. 주석 2줄.
- diff 훅 2개 모두 '다른 감점 항목' 블록 안. topFix 블록·IN-01 블록·시트 배선(3768) 훅 0.
- 게이트: tsc 0, node --test 219 / 0. 플랜 artifact `contains: "zoom={"` 충족(result.tsx
  2곳 — topFix 기존 1 + 이번 1).

## 최종 게이트

| 게이트 | 기준선 | Task 1 후 | Task 2 후 |
|---|---|---|---|
| `cd app && npx tsc --noEmit` | 0 오류 | 0 오류 (exit 0, 출력 0줄) | 0 오류 (exit 0, 출력 0줄) |
| `cd app && node --test "src/lib/__tests__/*.test.*"` | 219 pass / 0 fail | 219 / 0 | 219 / 0 |
| 커밋별 파일 | 태스크당 1파일 | cf5ee317 = DeductionCard.tsx 만 | 79885d83 = result.tsx 만 |
| 삭제 파일 | 0 | 0 | 0 |
| 무접촉 목록(analysis.ts / lib/* / ZoomCompositeImage.tsx / DeductionDetailSheet.tsx / app.json / backend / .planning) | diff 0 | 0 | 0 |
| 이모지 (추가 행 스캔) | 0 | 0 | 0 |

## 플랜 대비 편차

플랜 태스크·파일·검증 전부 그대로 실행. 판단 사항(플랜 미지정):

1. **[실행자 판단]** 접근성 라벨 '확대 사진 있음' 조건을 `hasZoom` → `hasZoom || zoom`
   으로 넓혔다. result.tsx 는 둘을 같은 `rowZoom` 에서 내므로 실제 경로에서 차이 0 —
   zoom 만 넘기는 미래 호출부 방어. 문구 신규 0.
2. **[실행자 판단]** 접힘 행에서 `zoomPending` placeholder 는 내지 않는다(플랜에 없음).
   pending 은 종전대로 topFix 카드 1곳. 사후 도착(done)하면 onSnapshot 으로
   `faultZoomComparisons` 가 채워져 접힌 행에도 사진이 뜬다.
3. **[관측 — 무접촉]** 다른 실행자 커밋 `7090a317`(backend/functions/pipeline/app.py)이
   내 두 커밋 사이에 들어왔다. `HEAD~2..HEAD` 범위 diff-stat 에 그 파일이 보이지만 내
   커밋 각각은 지정 1파일만 담는다(`git show --stat` 로 확인).
4. **[STATE/ROADMAP/.planning 무접촉]** 오케스트레이터 지시대로 SUMMARY 만 생성, 커밋 안
   함. `state.advance-plan`·`roadmap.update-plan-progress`·requirements 갱신 미실행.

## 남은 것 (이 작업 범위 밖)

- 시뮬레이터 실물 확인 — 오케스트레이터 후속(Metro Fast Refresh 붙어 있음). 확인
  포인트: 파워스핀 60점 복사본(확정 3) → topFix 1 + '다른 감점 항목' 접힌 행 2 각각
  사진 인라인(pill 없음, 헤드라인 + chevron 아래 합성 PNG); 클라임 복사본(확정 1) diff 0
  (행 없음); 사진 없는 행은 종전 한 줄; 사진 있는 행 탭 → 종전 시트.
- advisory 카드(belle 판정 대기)·매칭 규칙·계약·백엔드·문구 재배치 무접촉.

## Known Stubs

없음 — 접힌 행 사진은 실제 `result.faultZoomComparisons` 매칭 결과(`matchZoomForRecord`
단일 출처)에서 채워지고, 매칭 없으면 종전 한 줄 행 그대로.

## Threat Flags

없음 — 신규 네트워크 경로·권한·스키마 변경 0. 이미지 URL 은 기존 presigned/재발급
경로(`resolveZoomImageUrl` + `onZoomImageError`) 그대로.

## Self-Check: PASSED

- FOUND: app/src/components/DeductionCard.tsx (`collapsedZoom`, 접힘 ZoomCompositeImage 소비)
- FOUND: app/src/app/analysis/result.tsx (`rowZoom`, `zoom={` 2곳)
- FOUND commits: cf5ee317, 79885d83
