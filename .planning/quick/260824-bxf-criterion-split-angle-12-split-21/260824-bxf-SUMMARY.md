---
phase: quick-260824-bxf
plan: 01
subsystem: ui
tags: [progress-caption, noise-threshold, split-angle, firestore-readonly, react-native]
requires:
  - phase: quick-260822-oe1
    provides: 발전 캡션 배선 + NOISE-MEASUREMENT.md (풀링 P95 11.60 → 문턱 12, split_angle P95 20.00)
provides:
  - SPLIT-FLIP-CROSSTAB.md — split_angle 같은-영상 플립 교차표 원장 (규칙 커밋 → 측정 커밋)
  - PROGRESS_NOISE_THRESHOLDS 구조 (기본 12 + byCriterion split_angle 21) + resolveProgressNoiseThresholdDeg
  - buildProgressCaption criterion 인자 + DefectIllustration/result.tsx 배선
affects: [progress-caption, ota-pending]
tech-stack:
  added: []
  patterns: ["criterion별 노이즈 문턱 = max(전역, ceil(P95_c)+1) — 오버라이드는 belle 승인 후 데이터로만 추가", "measure-first: 규칙 커밋이 측정 결과 커밋보다 선행 (git 이력 게이트)"]
key-files:
  created:
    - .planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md
    - .planning/quick/260824-bxf-criterion-split-angle-12-split-21/measure_split_flip.mjs
  modified:
    - app/src/lib/progressCaption.ts
    - app/src/components/DefectIllustration.tsx
    - app/src/app/analysis/result.tsx
    - app/src/lib/__tests__/progressCaption.test.ts
key-decisions:
  - "문턱 12/21 은 08-22 P95 표에서 유도 — 이번 재실측 수치(플립 비율 예측 불일치)로 바꾸지 않음 (규칙 사전 박제)"
  - "criterion 부재 = fail-closed (기본 문턱으로 덮지 않음) / defaultDeg null = 오버라이드보다 우선하는 전면 비활성"
  - "타 criterion 오버라이드(left_shoulder 15, leg_extension 63 기계 산출) 미추가 — belle 승인 범위 밖 (짜맞추기 방지)"
patterns-established:
  - "grep 쓰기 게이트와 표기가 겹치는 Map 채우기 메서드 대신 평범한 객체 집계 (measure_split_flip.mjs)"
requirements-completed: [QUICK-BXF-01]
duration: 14min
completed: 2026-08-24
---

# Quick 260824-bxf: 발전 캡션 문턱 criterion별 전환 (기본 12 + split_angle 21) Summary

**split_angle 플립 교차표 재실측·원장 박제(historical 플립 52.7%) 후 캡션 노이즈 문턱을 단일 상수 12 에서 criterion별 구조(기본 12 + split_angle 21)로 전환, criterion 을 result.tsx → DefectIllustration → buildProgressCaption 으로 배선**

## Performance

- **Duration:** 약 14 min
- **Started:** 2026-08-23T23:43:13Z
- **Completed:** 2026-08-23T23:57:00Z (UTC — KST 08-24)
- **Tasks:** 3/3
- **Files modified:** 6 (원장 2 + 앱 4)

## Accomplishments

- **Task 1 — 교차표 원장 박제 (measure-first):** 규칙 커밋(`78f9482`)이 측정 결과 커밋(`f0c90b5`)보다 먼저. Firestore 읽기 전용(select 마스크 + uid 6자 절단, 쓰기 API 0 — grep 게이트 PASS). 기존 NOISE-MEASUREMENT.md diff 0.
- **Task 2 — 문턱 맵 전환 + 배선 (`7d35700`):** `PROGRESS_NOISE_THRESHOLDS { defaultDeg: 12, byCriterion: { split_angle: 21 } }` (각 값 원장 경로·측정일·표본수 주석) + `resolveProgressNoiseThresholdDeg` + `buildProgressCaption(asset, criterion, ...)`. 구 상수명 app/src 에서 소멸.
- **Task 3 — 경계 테스트 (`bb69bfd`):** 프로덕션 맵 실값으로 split 20°/21°/30°, 타 criterion 11.9°/12°, defaultDeg null 우선, resolve 3분기.
- **전량 게이트 GREEN:** typecheck PASS + node --test 234개 중 233 pass / fail 1 = 기지 illustrationScene test 8 단 1건 (신규 실패 0).

## 교차표 실측 수치 (예측 대비 자평)

| 축 | 예측 (08-22 구두) | 실측 (08-24) | 판정 |
|----|------------------|--------------|------|
| same-video historical 플립 | ≈36.4% | **29/55 = 52.7%** | 불일치 — 그대로 박제 |
| same-video deterministic 플립 | 0 | 표본 0 페어 | 검증 불가 (08-22 의 deterministic 1페어는 양쪽 split 미보유) |
| session48h 플립 | 0 | **7/48 = 14.6%** (|Δdelta| 5~15°) | 불일치 — 그대로 박제 |

- **문턱 유도 재료는 재현됨:** 전체 |Δdelta| n=103 · median 0.00 · P95 20.00 · max 20.00 — 08-22 NOISE-MEASUREMENT.md split_angle 행과 정확히 일치. `max(12, ceil(20.00)+1) = 21` 불변.
- 신규 관측: delta 값은 25/30/40/45/50 — **5° 단위 양자화** (08-22 관측 노트의 "0 아니면 20" 은 |Δdelta| 요약의 과단순화). 같은-영상 최대 요동 20° (30↔50) 실측 성립 — 문턱 21 근거 유지.
- session48h 플립 전건이 |Δdelta| ≤ 15° < 21 — 문턱 21 아래라 캡션 오발동 없음.

## Task Commits (규칙 → 측정 → 코드 순서 = 게이트)

1. **Task 1a: 판정 규칙 박제 (측정 전)** — `78f9482` (docs)
2. **Task 1b: 측정 결과 박제** — `f0c90b5` (docs)
3. **Task 2: 문턱 criterion별 전환 + 배선** — `7d35700` (feat)
4. **Task 3: 경계 테스트** — `bb69bfd` (test)

## Files Created/Modified

- `.planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md` — 판정 규칙(측정 전 박제) + 교차표 실측 결과 원장
- `.planning/quick/260824-bxf-criterion-split-angle-12-split-21/measure_split_flip.mjs` — 읽기 전용 재측정 도구 (select 마스크·uid 절단·쓰기 0)
- `app/src/lib/progressCaption.ts` — `ProgressNoiseThresholds` 구조 + `PROGRESS_NOISE_THRESHOLDS` + `resolveProgressNoiseThresholdDeg` + criterion 인자 시그니처
- `app/src/components/DefectIllustration.tsx` — `criterion` prop (prevHow 와 같은 값이어야 한다는 docstring) → `buildProgressCaption(matched, criterion, how, prevHow)`
- `app/src/app/analysis/result.tsx` — `criterion={sheetView?.primaryCriterion ?? null}` (prevHow 산출과 같은 값 — 두 번째 규칙 0)
- `app/src/lib/__tests__/progressCaption.test.ts` — 기존 테스트 thresholds 객체 주입 정합 갱신 + 섹션 6 경계 7케이스

## Decisions Made

- 플립 비율이 예측과 달랐지만 규칙(사전 박제)대로 수치 무조작 박제 — 문턱 12/21 은 08-22 P95 표 유도값이므로 불변.
- criterion 부재/빈 문자열 = 캡션 null (fail-closed) 을 섹션 4 fail-closed 축에 테스트로 추가 (Task 2 시그니처 변화의 정합 갱신 범위).

## Deviations from Plan

None — plan executed exactly as written. (측정 수치가 예측과 다른 것은 deviation 이 아니라 계획된 관측 박제.)

## Issues Encountered

- Task 1 verify 의 grep 쓰기 게이트(`\.set(|\.update(|\.delete(`)가 measure_noise.mjs 의 `Map.set` 표기와 겹침 — 스크립트 집계를 평범한 객체(`Object.create(null)`)로 작성해 회피 (기능 동일, 쓰기 API 와 무관한 표기 충돌 예방).

## Known Stubs

None — 스텁·플레이스홀더·하드코딩 빈 값 도입 0. 사용자 노출 문구 변경 0.

## belle 보고 항목

1. **예측 불일치 (관측):** 08-22 구두 수치 "historical 플립 36.4%" 는 재현되지 않음 — 실측 52.7%. session48h 도 예측 0 대비 실측 14.6% (|Δdelta| 5~15°, 전건 문턱 21 미만이라 캡션 오발동은 없음). 문턱 유도 재료(P95 20.00)는 08-22 원장과 정확히 일치 — **규칙·문턱 12/21 은 그대로**.
2. **OTA 발행 결정 대기 유지** — 이번 작업은 코드·원장만. eas update 미실행 (belle 결정 대기, 08-22 이월). 시뮬 실증은 오케스트레이터 후속.
3. 타 criterion 오버라이드(규칙 기계 적용 시 left_shoulder→15, leg_extension→63)는 belle 결정 없이 추가하지 않음 (SPLIT-FLIP-CROSSTAB.md 관측 노트).

## Next Readiness

- 시뮬 실증(오케스트레이터) → belle OTA 결정.
- 재측정 도구 상비: `measure_split_flip.mjs` (교차표) + `measure_noise.mjs` (P95 표) — 캡션 대상 앵커 추가 시 재실행.

## Self-Check: PASSED

- 산출 파일 7/7 존재 (원장 2 + SUMMARY + 앱 4)
- 커밋 4/4 존재 (`78f9482` → `f0c90b5` → `7d35700` → `bb69bfd` — 규칙→측정→코드 순서)
- key_link 3/3 성립 (`criterion={sheetView` / `buildProgressCaption(matched, criterion` / `SPLIT-FLIP-CROSSTAB` 출처 주석)
- NOISE-MEASUREMENT.md diff 0 · 전량 게이트 233 pass / 기지 실패 1

---
*Phase: quick-260824-bxf*
*Completed: 2026-08-24 (KST)*

## 시뮬 실증 (오케스트레이터 후속 — 2026-08-24)

iPhone 16 Pro 시뮬(873D7CB3) + Metro 신선 번들, 시뮬 uid(`fvcNXz…`, belle uid 아님 assert) 아래
현행 킵업 doc(`kipupFault1785373695`, split delta 50°)의 직전 시드 doc 을 넣고 다리 부위 상세
시트를 실렌더 — 양면 모두 라이브 확인:

- **(a) 개선 20° → 캡션 없음** `sim_split21_no_caption_at_20.png` — 구 문턱 12 에서는 표시됐을
  시드(08-22 `sim_progress_caption_v2.png` 가 그 증거)가 신규 문턱 21 에서 닫힘.
- **(b) 개선 30° → 캡션 표시** `sim_split21_caption_at_30.png` — "저번보다 나아졌어요" 가 pill
  아래 표시. (b) 가 뜨므로 (a) 의 부재는 시드 미발견이 아니라 문턱 판정임이 함께 증명됨.
- 시드 삭제 후 캡션 라이브 소멸 재확인 — 시뮬 계정 복원, 잔류 0. belle uid 쓰기 0.
