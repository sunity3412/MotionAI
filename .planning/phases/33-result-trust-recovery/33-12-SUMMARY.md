---
phase: 33-result-trust-recovery
plan: 12
subsystem: fault-zoom
tags: [fault-zoom, criterion-keyed, joint-exact, d-12, seam-1, contract-lockstep]

# Dependency graph
requires:
  - phase: 33-result-trust-recovery (33-10, A-3)
    provides: seam #1 결정 — backend criterion-keyed crops (재론 금지 범위)
  - phase: 33-result-trust-recovery (33-11, A-4)
    provides: belle 확인 ① 승인 확정 규칙 (마커=record 부위, 회전류 초 표기, 텍스트-장면 일치 게이트)
provides:
  - "criterion-keyed crop 파이프라인 — crop 단위가 deductionBreakdown.records[]에서 출생 (fault_zoom.criterion_units_from_records)"
  - "FaultZoomComparison.criterion scalar 계약 (analysis.ts + models.py 주석 + contract.md §11.7)"
  - "앱 join 키 일치 단일 출처 (deductionLabels.matchZoomForDeductionRecord — selectedZoom/matchZoomForRecord 공용)"
  - "D-12 카드 불변식 강제 (criterion 카드 한정): 같은 순간·배율 불가 drop + 기준측 같은 표시"
  - "회전류 기준측 실영상 초 표기 (stamp_ref — technique category 데이터 키잉)"
affects: [33-13, 33-15, 33-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "criterion-keyed 출생 정합 — 항목↔크롭 대응을 조인이 아니라 생성 시점에 보장 (D-03 원천 수정)"
    - "criterion 경로/legacy 경로 이원 불변식 — 신규 D-12 drop 은 criterion 카드에만, legacy 는 D-04 정직 폴백 byte-보존"
    - "베이스라인 대조 검증 — 전체 스위트 실패 세트를 변경 전/후 diff 로 신규 깨짐 0 입증"

key-files:
  created:
    - backend/tests/phase33/test_zoom_join_joint_exact.py
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py
    - app/src/lib/deductionLabels.ts
    - app/src/app/analysis/result.tsx
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md

key-decisions:
  - "seam = 백엔드 criterion-keyed crops (33-A3 §4 확정 그대로 — 재결정 없음), 앱 키 일치 join 은 백엔드안의 앱측 반쪽으로 흡수"
  - "D-12 drop 은 criterion 카드 한정 — legacy 경로의 D-04 정직 폴백(refMatch='failed')은 28-05 확정·기존 테스트 박제라 byte-보존"
  - "defect #6 은 faultzoom debug(79221f0)에서 선해결 확인 — RED 대신 회귀 핀으로 박제 (T-33-47)"
  - "vision record 투영 = faultJoints ∩ criterion 부위 (앱·백엔드 동일 미러) — 29 무회귀 가드('vision 전체 투영 불변')는 A-3 결정이 의도적 대체"

# Metrics
duration: 약 80분 (2026-07-29 01:17~02:40 UTC, 워치독 정지 1회 포함)
completed: 2026-07-29
---

# Phase 33 Plan 12: A-5 확대비교 구현 Summary

**확대비교 crop 이 화면 감점 항목(records[])에서 태어나 criterion 키로 조인되도록 seam #1 을 구현 — "다리 스플릿 항목에 어깨 크롭"(defect #5)을 출생 시점에 제거하고, D-12 카드 불변식(같은 순간·배율·표시 아니면 미방출)을 criterion 카드에 강제**

## 구현한 seam (plan output 요구 명시)

**백엔드 criterion-keyed crops** (33-A3-ZOOM-DESIGN §4 확정 그대로 — 재론 없음):

- `fault_zoom.criterion_units_from_records(records, fault_joints, angle_key_to_keypoint)` 순수 헬퍼 신설 — 앱 `projectDeductionRecordKeypoints` 규칙의 백엔드 미러: `a_v_r__{jk}`→단일 관절 / vision→**faultJoints ∩ criterion 부위**(전체 투영 금지) / ipsf geometry→region 멤버 / line·fallback→미생성. 중복 criterion dedupe + 상한 4.
- `build_fault_zoom_comparisons(criterion_units=...)` — 주어지면 `_group_fault_joints` fan-out 대신 record-파생 unit 으로 카드 생성, item 에 `criterion` scalar 방출. None = legacy 경로 byte-보존 (advisory·legacy doc·mode 폴백).
- pipeline: mode1 `_build_fault_zoom_comparisons` 이 records 존재 시 criterion_units 전달, mode3 는 기존 region 파생(29 D-08)에 criterion 라벨만 부착. S3 키 = `zoom_{criterion}.png` (record 별 유일 — 대표 관절 충돌 방지).
- 앱: `FaultZoomComparison.criterion?` + `matchZoomForDeductionRecord` 단일 출처 join (criterion 키 일치 1차, criterion 보유 카드는 교집합 조인 제외, legacy 카드만 교집합 폴백). `selectedZoom`/`matchZoomForRecord` 양쪽 교체.

## 8개 실측 결함 대응 현황

| Defect | 처리 | 어디서 |
|---|---|---|
| #5 항목↔크롭 관절 불일치 | **이번 플랜 해결** — criterion-keyed 출생 + 키 일치 join + vision 투영 좁힘(마커도 동일 수리) | fault_zoom.py + deductionLabels.ts |
| #2/#3 같은 순간·배율·표시 or drop | **이번 플랜 해결** — criterion 카드: ref 대응 실패·한측 full 폴백 → drop, 위상은 기존 unit 별 프레임 선택이 카드별 분산 | build 루프 D-12 ①② |
| #1 기준(정은지) 측 미드로잉 | **이번 플랜 해결** — criterion 카드: valid 시 원 마커(결함 관절 앵커), legs 사이각은 양측 모두 게이트 통과 시에만 둘 다(both-or-neither, 게이트 B 완화) | build 루프 |
| #4 fps 하드코딩 | 선행 debug 에서 해결 확인 — 전 인덱스 `_to_rep_idx` 단일 공식 경유 (이번 플랜 무접촉 검증) | fault_zoom.py:196 |
| #7 크롭 인물 이탈 | 선행 debug 에서 해결 확인 — `_side_crop` 3단 강하 + `select_confident_frame` (무접촉 검증) | fault_zoom.py |
| #6 각도 숫자 베이크 | **선행 debug(79221f0)에서 해결 — 이번 플랜이 회귀 핀 박제** (아래 Deviations) | test 5 (텍스트 스파이) |
| #8 advisory 시트 도달 불가 | **구조 해결** — record 보유 항목은 전부 confirmed criterion 카드로 출생 (구 candidate 실측의 a_v_r__right_elbow ↔ advisory-only 크롭 케이스 소멸). advisory tier 분리는 33-A3 지침대로 현행 유지 | criterion_units 경로 |
| (6R 규칙 3) 회전류 기준측 초 | **이번 플랜 해결** — `stamp_ref` 파라미터, technique `category=='spin'` 데이터 키잉 (mode1/mode3/advisory 비교쌍 공통) | _stamp_time + pipeline |

## 검증 결과 (수치)

- **신규 테스트**: `tests/phase33/test_zoom_join_joint_exact.py` 6/6 passed (RED→GREEN — RED 시점 5 fail/1 pass, 1 pass = 문서화된 회귀 핀).
- **fault_zoom 클러스터 + lockstep**: 181 passed (test_fault_zoom 계열 7파일 + mission/terminology lockstep).
- **전체 백엔드 스위트**: 변경 후 45 failed / 3490 passed ↔ 변경 전 베이스라인 45 failed / 3484 passed — **실패 테스트 이름 세트 완전 동일**(diff 0) = **신규 깨짐 0**. (+6 = 본 플랜 신규 테스트. 45건은 전부 기존·환경 기인 — 아래 Deferred.)
- **앱**: `npm run typecheck` (tsc --noEmit) clean.
- **채점 무접촉 (D-20/D-29)**: git diff 파일 목록 = 계획된 7파일뿐 — dimensions/kismam/motiondtw/deduction_engine 무접촉. fault_zoom.py 변경은 crop 선택·드로잉·방출 한정 (deficit 수치는 payload 로만 흐름).
- **un-bake grep**: fault_zoom.py 의 `draw.text` 호출 = `_stamp_time` 타임스탬프 1곳뿐.
- **lockstep grep**: `faultZoomComparisons` — analysis.ts(3)·models.py(3)·contract.md(3) 3면 모두 존재, criterion 절은 contract.md §11.7 신설.

## 10동작 일반화 성립 확인 (blocking anti-pattern 대조)

동작명 하드코딩 0. 모든 신규 규칙의 키잉 데이터:

- crop 단위 = `record.criterion`/`record.source`(doc 데이터) + `visionVeto.faultJoints`(doc 데이터)
- criterion→부위 = `CRITERION_REGION`/`REGION_MEMBERS` (criteria 이름공간 — 동작 무관, 앱·mode3 표와 3면 미러)
- 회전류 판정 = `technique.TechniqueProfile.category == 'spin'` (recognizer 가 동작별 데이터로 공급 — 등재 11동작 중 spin 카테고리 전부에 자동 적용, power-spin 특정 아님)
- D-12 drop/같은 표시 = crop_kind·ref 대응 상태(런타임 데이터) 조건 — 동작 무관

`grep -rn "power.spin\|powerspin"` 신규 diff 내 0건.

## Deviations from Plan

**1. [계획-코드 드리프트] defect #6 은 이미 해결된 상태였음 — RED 대신 회귀 핀**
- **Found during:** Task 1 (git 이력 대조)
- **Issue:** 플랜은 `_mark` 배지·`_draw_leg_angle` 수치 라벨 제거를 이 플랜 소관으로 기술(참조 라인 :606-633 도 구버전)했으나, faultzoom debug 커밋 `79221f0`("remove angle badges from zoom crops — timestamps only")이 이미 언베이크를 랜딩함
- **Fix:** TDD fail-fast 규약대로 조사 후, 해당 어서션을 RED 가 아닌 **회귀 핀**으로 전환 — ImageDraw.text 전수 스파이로 "타임스탬프 패턴 외 텍스트 0"을 박제 (T-33-47 완화 장치는 계획대로 존재). 테스트 헤더와 본 SUMMARY 에 드리프트 기록
- **Commit:** 333b5ac

**2. [해석 결정] D-12 drop 을 criterion 카드 한정으로 적용**
- **Found during:** Task 2 설계
- **Issue:** 플랜의 "mismatched pair dropped"를 전 경로에 적용하면 28-05 확정 D-04 정직 폴백(refMatch='failed' 전신 비교 — 33-A3 2(c)-4 가 "정직 전략"으로 박제 + 기존 테스트 2파일이 고정 + A-4 목업 ③ 최악 케이스 화면 설계 존재)과 정면 충돌
- **Fix:** D-12 불변식은 **criterion 카드(A-5 신규 물량)에 강제**, legacy 경로(구 doc·advisory)는 D-04 정직 폴백 byte-보존. 신규 테스트 3(c)가 이 이원 구조 자체를 박제. 새 mode1 분석은 records 존재 시 항상 criterion 경로이므로 실효적으로 D-12 가 표준
- **Files modified:** fault_zoom.py build 루프
- **Commit:** 76770a8

**3. [Rule 2 - 승인 규칙 편입] 회전류 기준측 초 표기 (stamp_ref)**
- **Found during:** Task 2 (33-11 SUMMARY 의 A-5 입력 목록 대조)
- **Issue:** 플랜 태스크 본문에는 없으나 belle 확인 ① 확정 규칙(6R 규칙 3 — "회전류 비교쌍 기준측 실영상 초 상시 표기")이 A-5(33-12) 소비 항목으로 명시돼 있어 미구현 시 승인 계약 위반
- **Fix:** `stamp_ref` 렌더러 파라미터 + pipeline 에서 technique category 데이터 키잉. `_stamp_time` docstring 에 07-25 제거 결정의 amendment 이력 기록
- **Commit:** 76770a8 (테스트 6 포함)

**4. [프로세스 오류 - 자가 복구] git stash 오용 1회**
- **Found during:** Task 2 검증 중 베이스라인 확인 명령 조립 실수
- **Issue:** 명령 체인에 `git stash -q` 가 포함돼 미커밋 구현이 일시 스태시됨 (금지 명령)
- **Fix:** 즉시 감지(stash list 1건 = 직전 본인 WIP 확인) 후 `git stash pop` 으로 원상 복구 — 편집 무손실 검증(criterion 참조 카운트 대조). 이후 베이스라인 대조는 patch 저장 + `git checkout -- <file>` + `git apply` 의 승인된 절차로 수행
- **Impact:** 데이터 손실 0, 커밋 이력 무영향

**Total deviations:** 1 계획 드리프트 기록, 1 해석 결정, 1 승인 규칙 편입, 1 프로세스 오류(자가 복구)

## 무엇을 열어서 확인했는가 (D-19) — PNG 재생성은 33-16 소관

**이 플랜의 코드 변경만으로는 저장된 crop PNG 가 재생성되지 않는다** (33-RESEARCH Runtime State). 실제 PNG 전수 열람(6동작 전수 — joint-exact 성립 + 숫자 미베이크 + 기준측 마킹·초 표기 실물 확인)은 **33-16 페이즈 게이트의 Pod 재스위프 후** 수행한다. 이번 플랜에서 직접 연 것: 합성 fixture 기반 방출 item 의 criterion/joint 값, 합성 PNG 의 우측(기준) 패널 브랜드 픽셀 존재(테스트 4 — 디코딩 후 픽셀 어서션), ImageDraw 호출 전수 스파이 로그. 실 Pod 분석 실행은 이번 플랜 동안 금지(스위프 직렬 진행 중)라 수행하지 않음.

## 틀리면 걸리는 장치 (D-18)

- 항목↔크롭 불일치: `test_criterion_units_from_records_joint_exact`(어깨 누출 시 즉발) + criterion 키 일치 join(불일치 카드는 조인 자체가 불가) + 내부 provenance 로그(`fault_zoom_crop ... criterion=`) 전수 대조 재료
- 불일치 쌍 방출: `test_mismatched_pair_dropped_criterion_path` (drop 미작동 시 즉발)
- 숫자 재베이크: 회귀 핀 테스트 (타임스탬프 외 텍스트 발생 시 즉발)
- 앱측 자동화 불가분: JS 러너 부재 — 테스트 헤더에 명시, 대체 = tsc + 33-16 D-19 전수 열람

## Deferred Issues (이 플랜 밖 — 수정하지 않음)

- `backend/tests/` 수집 오류 12모듈 (`backend.research.*` import — research/spike 계열, rootdir 관례 문제) + 기존 실패 45건 (phase06 통합 스모크 등 — HoughPoleDetector lazy init 실패·Gemini 키 부재 등 로컬 환경 기인). 변경 전 베이스라인과 세트 동일함을 확인만 하고 무접촉.
- legacy doc 의 crop 은 재분석 전까지 구 형상(criterion 부재) — 앱 교집합 폴백이 커버 (의도된 하위호환, no migration).

## Known Stubs

없음 — 신규 코드에 placeholder/빈 데이터 배선 없음. criterion 카드는 33-16 재분석 후 실데이터로 도착하며, 그 전까지 앱은 legacy 폴백 경로로 기존 카드를 정상 렌더 (스텁 아닌 하위호환).

## Task Commits

1. **Task 1: RED — joint-exact join 테스트** — `333b5ac` (test)
2. **Task 2: criterion-keyed 구현 + 계약 lockstep** — `76770a8` (feat)

## Next Phase Readiness

- **33-13 (A-6 카피)** — criterion 키가 카드에 실리므로 카피↔카드 국면 일치 검수(승인 불변식 ①)의 조인 재료 확보
- **33-15 (앱 Wave B)** — 상세 시트가 criterion 카드 전제로 진행 가능 (수치 단일 거처 = 내역, 크롭엔 미베이크 확정)
- **33-16 (페이즈 게이트)** — Pod 재스위프로 crop 재생성 → record.criterion == crop.criterion 전수 assert + PNG 전수 열람 (이 플랜의 D-19 완결 지점)

## Self-Check: PASSED

- 생성 파일 존재: test_zoom_join_joint_exact.py, 33-12-SUMMARY.md
- 커밋 존재: 333b5ac (Task 1), 76770a8 (Task 2), 79221f0 (defect #6 선행 랜딩 참조)
- 코드 앵커 존재: criterion_units_from_records(fault_zoom.py), matchZoomForDeductionRecord(deductionLabels.ts)
