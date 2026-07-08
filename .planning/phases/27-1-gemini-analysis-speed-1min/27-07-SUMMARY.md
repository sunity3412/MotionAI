---
phase: 27-1-gemini-analysis-speed-1min
plan: 07
subsystem: ui
tags: [app, ux, loading, result, fault-zoom, progress, ota]

# Dependency graph
requires:
  - phase: 27-06
    provides: "faultZoomStatus 계약(analysis.ts) pending/done/failed scalar — 점수 complete 이후 zoom PNG 부분 업데이트로 도착"
  - phase: 27-02
    provides: "27-TIMING-BEFORE 실측 단계별 배분 — 진행률 재배분 근거"
provides:
  - "결과 화면 zoom pending placeholder — faultZoomStatus='pending' 시 확대카드 자리 로딩, onSnapshot 도착 자동 전환 (D-06)"
  - "FAULT_ZOOM_PENDING_TIMEOUT_MS(180s) 시간 상한 폴백 — pending 고아 방어(T-27-21, 무한 로딩 0)"
  - "로딩 화면 POLE_TIPS(12개) 폴스포츠 팁 로테이터 (D-07 v1)"
  - "PROGRESS_PCT/PROGRESS_CEIL 실측 기반 재배분 — comparison 구간 base 40→상한 97(85% 얼어붙음 해소, D-02). Math.max 단조 로직 무변경"
affects: [27-09]

# Tech tracking
tech-stack:
  added: []  # 신규 패키지 0 — 기존 RN 컴포넌트(ActivityIndicator)만 = OTA 가능
  patterns:
    - "사후 도착 UI: status='pending' 스칼라 + onSnapshot rerender 로 placeholder→콘텐츠 자동 전환(추가 폴링 0)"
    - "pending 고아 방어: doc.updatedAt 기준 setTimeout 상한 폴백(setInterval 폴링 아님) — 무한 로딩 차단"
    - "진행률 재배분: 값만 실측 비례로 조정, Math.max 단조 로직/creep 메커니즘 무변경(85% 멈춤 fix 이력 보존)"
    - "이중 로테이터 주기 어긋냄: COPY_ROTATE_MS(4000) vs TIP_ROTATE_MS(6000) — 동시 점프 방지"

key-files:
  created: []
  modified:
    - app/src/app/analysis/result.tsx
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/app/analysis/loading.tsx

key-decisions:
  - "zoom placeholder 렌더는 DeductionDetailSheet(zoom 소비처)에 두고, result.tsx 는 faultZoomStatus pending 판정 + 시간 상한 폴백을 계산해 zoomPending boolean 만 전달 — 26-02 wrapper/child 분리 미실행 상태의 현행 구조 반영(zoom 은 result.tsx 인라인이 아니라 별도 시트 컴포넌트가 렌더)."
  - "시간 상한 폴백은 setTimeout(updatedAt 기준 remaining) — setInterval 폴링 금지(acceptance zoom 신규 폴링 0). updatedAt 변경(zoom 부분 업데이트가 updatedAt 갱신)마다 타이머 재무장."
  - "comparison base 40→상한 97 로 폭넓게 — 실측상 comparison 이 전체의 ~80%(비전+coach+hook)라 낮은 base + 넓은 creep 범위로 긴 대기 내내 전진 표시. 85% 얼어붙음(실증 2026-07-06) 정면 해소."

patterns-established:
  - "사후 도착 필드(status scalar) 소비: pending=placeholder / done=콘텐츠 / failed·부재=graceful 숨김 + 시간 상한 폴백"

requirements-completed: [SPD-04, SPD-05]

# Metrics
duration: ~35min
completed: 2026-07-08
---

# Phase 27 Plan 07: 앱 대기 경험 (zoom pending placeholder + 팁 로테이터 + 진행률 재배분) Summary

**27-06 이 분리한 faultZoomStatus 계약을 앱이 소비 — 결과 화면이 점수/감점 내역을 먼저 보여주고 확대비교 이미지는 pending placeholder(ActivityIndicator+안내 카피)로 자리를 지키다 onSnapshot 도착 시 자동 전환하며, pending 고아는 180s 시간 상한으로 숨김 폴백해 무한 로딩을 0으로 만든다. 로딩 화면에는 폴스포츠 팁 12개 로테이터를 추가하고 진행률 배분을 27-TIMING-BEFORE 실측 기반으로 재조정해(comparison base 40→상한 97) "85%에서 멈춘 것 같다"는 체감을 해소했다. JS-only — OTA 가능(신규 패키지 0).**

## Performance
- **Duration:** ~35 min
- **Completed:** 2026-07-08
- **Tasks:** 2 (둘 다 type="auto")
- **Files modified:** 3

## Accomplishments
- **Task 1 — result.tsx zoom pending placeholder + 시간 상한 폴백:** `FAULT_ZOOM_PENDING_TIMEOUT_MS`(180s) 상수(근거 주석: 실측 fault_zoom 렌더 13~33s 상회 보수값). `AnalysisResultContent` 에 `updatedAt`(doc.updatedAt=complete 시점) prop 추가. `result.faultZoomStatus === 'pending'` + `updatedAt` 기준 setTimeout 상한 폴백 훅(early return 이전 배치) → `zoomPending` boolean 산출. `DeductionDetailSheet` 에 `zoomPending` prop 전달 → 이미지 카드 동일 컨테이너(imageWrap)에 `ActivityIndicator`+'확대 비교 이미지를 준비하고 있어요'(토큰만, 라이트, accessibilityRole="progressbar"). 'done'=onSnapshot rerender 자동 전환 / 'failed'·done-무매칭·legacy 부재=selectedZoom null → 기존 graceful 숨김. 신규 zoom 폴링(setInterval/fetch) 0.
- **Task 2 — loading.tsx 팁 로테이터 + 진행률 재배분:** `POLE_TIPS`(12개, 한국어, 이모지·부상/근력 단정 금지, 학원 통용 동작명) + `TIP_ROTATE_MS`(6000, 안심카피 4000과 어긋나게) + 별도 useState/useEffect interval(모든 early return 이전). 분석 중 렌더 stepLine 아래 tipLine(navy 위 가독 rgba(255,255,255,0.72), 음수 letterSpacing 회피). `PROGRESS_PCT`/`PROGRESS_CEIL` **값만** 27-TIMING-BEFORE 실측 비례로 재배분(각 값 근거 주석): comparison base 8→40·상한 별도 유지 아님 — comparison 40→97 로 폭넓게(비전+coach ~80% 구간의 긴 대기를 전진 표시). `Math.max` 단조 로직·`PROGRESS_CREEP_MS`(2500) 무변경.

## Task Commits
1. **Task 1: zoom pending placeholder + 시간 상한 폴백 (D-06)** — `ee70319` (feat)
2. **Task 2: 로딩 화면 팁 로테이터 + 진행률 재배분 (D-07/D-02)** — `c675223` (feat)

## Files Created/Modified
- `app/src/app/analysis/result.tsx` — FAULT_ZOOM_PENDING_TIMEOUT_MS 상수, updatedAt prop, pending 상한 폴백 훅, zoomPending 전달
- `app/src/components/DeductionDetailSheet.tsx` — zoomPending prop + 확대카드 자리 로딩 placeholder(ActivityIndicator+카피, 토큰만)
- `app/src/app/analysis/loading.tsx` — POLE_TIPS/TIP_ROTATE_MS + tip 로테이터 훅/렌더/스타일, PROGRESS_PCT/PROGRESS_CEIL 실측 재배분

## Decisions Made
- zoom placeholder 렌더 위치 = DeductionDetailSheet(실제 zoom 소비처). result.tsx 는 pending 판정+상한 폴백만 계산해 `zoomPending` boolean 전달. 자세한 근거는 Deviations 참조.
- 시간 상한 폴백 = setTimeout(updatedAt 기준 remaining), setInterval 폴링 금지(acceptance 준수). updatedAt 갱신마다 재무장.
- comparison base 를 크게 낮추고(40) 상한 97 로 넓혀 실측 시간 분포(comparison ~80%)에 맞춤 — 85% 얼어붙음 정면 해소.

## Deviations from Plan

### 계획 범위 내 판단

**1. [설계 판단] zoom pending placeholder 렌더를 DeductionDetailSheet.tsx 에 배치 (files_modified 3번째 파일)**
- **Found during:** Task 1
- **Issue:** 계획 files_modified 는 result.tsx + loading.tsx 2개. 그러나 확대비교 이미지는 result.tsx 인라인이 아니라 별도 `DeductionDetailSheet` 컴포넌트가 `zoom` prop 으로 렌더한다(선행 확인: 26-02 wrapper/child 분리는 미실행이나, zoom 소비는 이미 이 시트로 추출돼 있음). "확대카드 자리에 로딩 placeholder"를 그리려면 시트 컴포넌트가 pending 상태를 알아야 한다.
- **Fix:** result.tsx 에서 `result.faultZoomStatus === 'pending'` + 시간 상한을 계산해 `zoomPending` boolean 을 시트로 전달하고, 시트는 기존 imageWrap 컨테이너에 ActivityIndicator+카피를 렌더. faultZoomStatus 판정/상한 로직은 계획대로 result.tsx 에 존재(acceptance grep ≥2 충족, 실측 8회).
- **Files modified:** app/src/components/DeductionDetailSheet.tsx (신규 prop + placeholder 분기 + 2 style)
- **Verification:** `npm run typecheck` exit 0. 신규 하드코딩 컬러 0(토큰만). 신규 zoom 폴링 0.
- **Committed in:** ee70319 (Task 1 commit)

---

**Total deviations:** 1 설계 판단 (files_modified 에 없던 DeductionDetailSheet.tsx 1파일 — zoom 실제 렌더 위치 반영). Scope creep 0.
**Impact on plan:** 계획 의도(zoom pending placeholder)를 현행 코드 구조에 맞게 구현. faultZoomStatus 분기/폴백은 계획대로 result.tsx 에 위치. must_haves 전부 충족.

## Issues Encountered
- 선행 확인(계획 명시): Phase 26(26-02 wrapper/child, 26-03/04 loading) **미실행 상태**로 착수. result.tsx 는 wrapper/child 분리 없이 현행 구조(AnalysisResultContent 단일 child)라 `selectedZoom` 심볼 기준으로 위치 확인 후 작업. loading.tsx 도 26-03/04 미반영이라 라인 이동 없이 REASSURANCE_COPIES/PROGRESS_PCT 심볼 그대로. 겹침 충돌 없음(파일이 base 상태) — orchestrator 참고용으로 보고.

## Verification Evidence
- `cd app && npm run typecheck`(tsc --noEmit) exit 0 — Task 1·2 결합 상태 최종 typecheck green (worktree node_modules 심볼릭 링크, 실행 후 제거 — tracked 파일 무변경).
- result.tsx grep: `faultZoomStatus` = 8(pending 판정 + 상한 폴백 + 주석). 신규 `#FF4B33`/`#FFFFFF` 하드코딩 증가 0(HEAD 1 = mine +0). `setInterval`/`fetch(` = 0(zoom 신규 폴링 없음, setTimeout 만 사용).
- loading.tsx grep: `POLE_TIPS` = 3(상수 + 렌더 + 훅). `Math.max` = 2(단조 로직 잔존, diff 상 Math.max 라인 무변경). POLE_TIPS 배열 = 12 항목(≥8).
- git diff --diff-filter=D HEAD~2 HEAD = 삭제 파일 0.

## User Setup Required
None — 신규 패키지 0, JS-only 변경. OTA 배포 가능(EAS 재빌드 불필요). OTA 발행은 batch-UAT 정책에 따라 phase 마감 시 orchestrator 소관.

## Next Phase Readiness
- 27-09: faultZoomStatus pending→done 전이 체감·팁 로테이션·진행률 전진은 27-VALIDATION Manual-Only(belle 실기기) 검증 항목. EVAL18 time-to-first-result before/after 와 함께 확인.
- 앱 소비 완결: 27-06 백엔드 사후 분리 ↔ 27-07 앱 소비 배선 종결. 남은 것은 실기기 체감 확인뿐.

---
*Phase: 27-1-gemini-analysis-speed-1min*
*Completed: 2026-07-08*

## Self-Check: PASSED
- 수정 파일 3개 전부 존재 + 커밋 반영: result.tsx / DeductionDetailSheet.tsx (ee70319), loading.tsx (c675223).
- 커밋 2개 존재: ee70319(feat Task1) / c675223(feat Task2).
- typecheck exit 0(결합 상태). result.tsx faultZoomStatus=8·신규 하드코딩 0·zoom 폴링 0. loading.tsx POLE_TIPS 12항목·Math.max 무변경.
- STATE.md/ROADMAP.md 무접촉(orchestrator 소관).
