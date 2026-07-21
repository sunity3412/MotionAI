---
phase: 32-result-readability-3-omni
plan: 01
subsystem: analysis
tags: [motion-alignment, fault-zoom, dtw, crop, tdd, python, pytest, display]

# Dependency graph
requires:
  - phase: 28-dtw-motion-based-alignment
    provides: build_motion_alignment 초 단위 앵커 + tier 사다리 + _validate_motion_alignment 역불변식
  - phase: 25 (fault_zoom relaxed crop)
    provides: _side_crop 3단 강하(valid/relaxed/full) + _RELAXED_MARGIN + _box_for
provides:
  - "저신뢰(distance>T2) DTW 를 disabled 대신 trim_only(anchors 보존)로 방출 + 첫 anchor sanity 가드 (D-16)"
  - "fault_zoom relaxed 프레이밍을 valid 와 동일 배율(양측 1.8배)로 통일 + crop side px parity 로그 (D-20)"
  - "backend/tests/phase32/ 테스트 스캐폴드(conftest sys.path 3경로) — 이후 백엔드 플랜 재사용"
affects: [32-03 (6동작 전수 스윕 — 점수 diff 0 + crop parity 로그 판정 D-23), 32-06 (phase32 conftest 재사용), 32-15 (최종 전수 스윕)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED/GREEN per task (test 커밋 → fix 커밋)"
    - "phase32 테스트 스캐폴드 (phase31/conftest sys.path 주입 복제)"
    - "관측 전용 구조 로그(log.info key=value, 채점/방출 무접촉)"

key-files:
  created:
    - backend/tests/phase32/conftest.py
    - backend/tests/phase32/test_motion_alignment_ladder.py
    - backend/tests/phase32/test_fault_zoom_crop_parity.py
  modified:
    - backend/shared/python/sunity_shared/analysis/motion_alignment.py
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/tests/test_motion_alignment.py
    - backend/tests/test_fault_zoom_relaxed_crop.py

key-decisions:
  - "저신뢰 trim_only 방출은 계약 변경 0 경로 (trim_only 이미 MOTION_ALIGNMENT_TIERS enum, validator 역불변식 자동 충족)"
  - "첫 anchor sanity 가드는 신규 reason enum 0 — insufficient_anchors 재사용해 이상치 offset 유입 차단"
  - "fault_zoom analysis_id 는 옵셔널 kwarg (pipeline 배선은 out-of-scope 후속 — 로그 parity 데이터는 무관하게 방출)"
  - "_RELAXED_MARGIN 상수 보존(삭제 X) — 프레이밍 미사용, 향후 마커 게이트 튜닝 참조용"

patterns-established:
  - "프레이밍/마커 신뢰도 게이트 분리 — 프레이밍은 좌표 오차 둔감(통일), 마커는 민감(relaxed 생략 유지)"
  - "표시 전용 부가물 수리는 채점 모듈 diff 0 로 점수 불변 증명"

requirements-completed: [D-16, D-20]

# Metrics
duration: ~35min
completed: 2026-07-21
---

# Phase 32 Plan 01: Wave-1 백엔드 수리 2건 (동작 정렬 초맞춤 D-16 + 확대비교 크롭 배율 통일 D-20) Summary

**저신뢰 DTW 를 disabled 로 버리지 않고 sanity 검증된 trim_only(anchors 보존)로 방출하고(D-16), fault_zoom relaxed 크롭 프레이밍을 valid 와 동일 1.8배로 통일하면서 crop side px parity 로그를 심었다(D-20) — 둘 다 채점 무접촉, phase32 테스트 스캐폴드 신설**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-21T15:14Z (approx, 분석 시작)
- **Completed:** 2026-07-21T15:44:27+09:00
- **Tasks:** 2 (both TDD — 4 commits)
- **Files modified:** 7 (3 created + 4 modified)

## Accomplishments

- **D-16 백엔드부:** motion_alignment 사다리 else 분기(distance > DISTANCE_T2)를 `tier='disabled'`(anchors 폐기) → `tier='trim_only'` + `reason='low_global_confidence'` + anchors 보존으로 교체. "동작 비교 시작점 맞춤"이 저신뢰에서도 살아난다(belle 최우선 수리 "동작 비교 정렬 포기 보완"). 배속 워핑은 여전히 끔(trim_only), 시작 오프셋만 사용.
- **첫 anchor sanity 가드(리뷰 MEDIUM):** 방출 전 첫 anchor 쌍 (u0,r0)이 각 타임라인 범위 `[0, dur]` 밖이거나 non-finite 면 기존 degenerate 경로(`insufficient_anchors`, 신규 reason enum 0)로 낙하 — 이상치 offset 이 trim 기준으로 유입되는 것을 차단. 두 anchor 가 각자 범위 안이면 `|r0−u0| ≤ max(user_dur, ref_dur)` 자동 성립.
- **계약 변경 0:** trim_only 는 이미 MOTION_ALIGNMENT_TIERS enum 에 존재, validator 역불변식(trim_only → anchors ≥ 2쌍)은 else 분기가 `len(pairs) ≥ 2`를 이미 통과한 상태라 자동 충족 — models.py/analysis.ts/contract.md/validator 전부 무변경.
- **D-20:** fault_zoom `_side_crop` relaxed 분기의 `_box_for(relaxed_pts, _RELAXED_MARGIN=2.0)` → `_box_for(relaxed_pts, 1.0)`. 프레이밍이 valid 와 동일 배율(bbox×1.8)로 통일 — "정은지 crop 이 2배 넓어 비교와 안 맞음"(belle 실기기) 해소. `crop_kind='relaxed'` 유지 → `anchor_px=None` 마커 생략 게이트는 현행 보존(프레이밍/마커 분리).
- **crop side px parity 로그:** crop 산출 지점에 `log.info("fault_zoom_crop analysis_id=%s region=%s user_kind=%s user_side_px=%s ref_kind=%s ref_side_px=%s", ...)` 구조 로그 1줄 — 32-03 전수 스윕이 육안 비교에 더해 user/ref side 비(0.8~1.25)로 수치 parity 를 판정하는 재료. 관측 전용(채점/방출 무접촉).
- **phase32 테스트 스캐폴드:** `backend/tests/phase32/conftest.py`(sys.path 3경로 주입, phase31 선례) 신설 — 이후 모든 백엔드 phase32 플랜이 재사용.
- **점수 불변 1차 증거:** 채점 모듈(dimensions.py/kismam.py/deduction 계열) git diff 0. 최종 실측 증명은 32-03 6동작 전수 스윕 점수 diff 0(D-23)가 담당.

## Task Commits

TDD tasks — test → fix 사이클:

1. **Task 1 (D-16): phase32 스캐폴드 + motion_alignment 사다리 재배치 + anchor sanity**
   - RED: `39537b4` (test — ladder 6 behaviors, 4 fail/2 pass)
   - GREEN: `27eafe5` (fix — else 분기 trim_only + sanity 가드 + docstring + 25.1 기대값 갱신)
2. **Task 2 (D-20): fault_zoom relaxed 프레이밍 분리 + crop side 로그**
   - RED: `545dcdd` (test — parity 4 tests, 2 fail/2 pass)
   - GREEN: `b5afe29` (fix — margin 1.0 통일 + analysis_id kwarg + parity 로그 + 기존 테스트 재작성)

_Note: TDD tasks have test→fix commits per the tdd="true" 태스크 규율._

## Files Created/Modified

- `backend/tests/phase32/conftest.py` (created) — sys.path 3경로(_BACKEND/_LAYER/_SCRIPTS) 주입 스캐폴드. fake_firestore 는 이 플랜 불필요라 미포함(32-06 이 phase31 것 재사용).
- `backend/tests/phase32/test_motion_alignment_ladder.py` (created) — D-16 6 behaviors: 저신뢰 trim_only/degenerate 3종 유지/기존 사다리 무회귀/validator 통과/첫 anchor sanity 낙하/오프셋 경계.
- `backend/tests/phase32/test_fault_zoom_crop_parity.py` (created) — D-20 4 tests: 프레이밍 parity/kind+anchor 게이트 보존/valid 무회귀/crop side px 로그(caplog).
- `backend/shared/python/sunity_shared/analysis/motion_alignment.py` (modified) — else 분기 trim_only 방출 + 첫 anchor sanity 가드 + 모듈 docstring D-16 각주. `_disabled(` 호출 5(정의1+degenerate3+sanity낙하1).
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` (modified) — relaxed 프레이밍 margin 1.0 통일 + `import logging`/모듈 logger + build_fault_zoom_comparisons `analysis_id` 옵셔널 kwarg + crop side px 구조 로그 + `_RELAXED_MARGIN` 코멘트 갱신(보존).
- `backend/tests/test_motion_alignment.py` (modified) — test_tier_distance_boundaries 25.1 기대값 disabled→trim_only 갱신 + docstring.
- `backend/tests/test_fault_zoom_relaxed_crop.py` (modified) — test_relaxed_margin_widens → test_relaxed_framing_matches_valid_after_d20 재작성(구 "relaxed 가 더 넓음" 계약 폐기, parity 로 교체).

## Decisions Made

- **저신뢰 trim_only = 계약 변경 0 경로:** trim_only enum 기존재 + validator 역불변식 자동 충족이라 3면 계약(TS/Python/contract.md) 무변경으로 방출 tier 만 변경.
- **anchor sanity reason = insufficient_anchors 재사용:** 신규 reason enum 추가 없이 기존 degenerate reason 재사용 — validator/앱 normalizer 대칭 유지.
- **duration 정의:** user_dur = end_sec, ref_dur = max(path ref 인덱스)/ref_fps — 둘 다 함수 내 계산 가능. 실현되는 이상치는 음수 start(u0<0)/음수 ref 인덱스(r0<0)/non-finite. 정상 케이스는 u0≤uN=end_sec, r0≤max_ref 라 상한은 자동 충족, 하한/finite 가 실질 게이트.
- **_RELAXED_MARGIN 보존:** 플랜 1순위 옵션 채택 — 삭제 대신 상수 유지 + 코멘트로 "프레이밍 미사용, 마커 튜닝 참조용" 명기(import/참조 전수 확인 회피, 위험 최소).

## Deviations from Plan

플랜대로 실행. 아래는 플랜 의도를 충족하기 위한 구현 판단(스코프 내):

**1. [구현 판단] build_fault_zoom_comparisons 에 `analysis_id` 옵셔널 kwarg 신설**
- **Found during:** Task 2 (crop side 로그)
- **이유:** 플랜이 로그 필드로 "analysis 식별자"를 명시했으나 함수 시그니처에 식별자가 없었음. 옵셔널 키워드(default None)로 추가 — 기존 caller/테스트 전부 하위호환.
- **스코프 경계:** production 배선(pipeline/app.py 에서 실 analysis_id 전달)은 이 플랜 files_modified 밖(pipeline 은 다른 wave 플랜이 수정 — E-1)이라 미접촉. 프로덕션 로그는 배선 전까지 `analysis_id=None` 이지만 **parity 판정 재료인 user/ref side px 는 무관하게 방출**되고, 32-03 스윕은 SERIAL 실행이라 analysis_id 없이도 상관 가능. → Known follow-up(아래).
- **Committed in:** `b5afe29`

**2. [추가 검증] parity 테스트에 crop side 로그 caplog 테스트 1건 추가(플랜 3 behaviors → 4)**
- 플랜의 로그 요구를 grep(acceptance)뿐 아니라 런타임 caplog 로 증명 — 로거 이름/포맷 오류를 유닛 테스트로 차단.

---

**Total deviations:** 0 auto-fixed bugs (플랜 정상 실행). 2 구현 판단(스코프 내, 하위호환).
**Impact on plan:** scope creep 없음. 채점 모듈 diff 0(점수 불변) 유지.

## Issues Encountered

- **rtk pytest 미수집:** `rtk pytest`가 "No tests collected"로 실패 → 플랜 명시 `python -m pytest`(로컬은 `python3`)로 실행. 관찰 커맨드만 rtk 사용.
- **전체 suite `-k fault_zoom` 수집 중단(12 errors):** `.planning/spikes/*`·rtmpose/spike 파일들이 `ModuleNotFoundError: backend/fixtures.*`(rootdir 이슈, 로컬 heavy-dep 부재)로 collection error → **이 플랜 무관 pre-existing**(내가 건드린 파일 0). fault_zoom 테스트를 명시 파일 경로로 직접 실행해 115 pass 확인.
- **incidental .pyc 재컴파일:** 전체 수집 시도가 `.planning/spikes/001-.../__pycache__/{ipsf_criteria,metrics}.pyc`(tracked)를 재컴파일 → `git checkout --`로 원복(내 작업 무관, 채점 오인 방지). 이후 targeted 실행만 사용.

## Verification

- `python3 -m pytest tests/phase32 -x -q` → **10 passed** (ladder 6 + parity 4).
- 기존 motion_alignment/fault_zoom 계열 명시 파일 전체 → **160 passed** (phase32 10 + motion_alignment 20 + contract 12 + pipeline_motion_alignment 7 + fault_zoom 7파일 115 − 중복). 신규 실패 0.
- Acceptance greps: `_disabled(` 호출 5(≤5) / anchor sanity 가드(finite+duration) 존재 / `_box_for(relaxed_pts, 1.0)` / `side_px=` 로그 키 / 채점 모듈(dimensions/kismam/deduction) git diff 0.

## Known Follow-ups (not blocking this plan)

- **fault_zoom analysis_id 프로덕션 배선:** `build_fault_zoom_comparisons(analysis_id=...)` 를 pipeline/app.py(및 runpod server)의 fault_zoom 사후 스테이지에서 실 analysis_id 로 전달하면 parity 로그에 식별자가 채워짐. parity 데이터(side px)는 이미 방출되므로 32-03 스윕 판정에는 불요(SERIAL 실행). pipeline 이 다른 wave 플랜 스코프라 이 플랜은 미접촉.
- **점수 불변 실측 증명:** 로컬 diff 0 는 1차 증거. 최종은 32-03 6동작 전수 스윕 점수 diff 0(D-23) + Pod 실측 crop parity(육안+로그).

## Next Phase Readiness

- **32-03 준비 완료:** phase32 스캐폴드 가동, D-16/D-20 백엔드 수리 방출. 6동작 전수 스윕이 (a) 점수 diff 0(채점 무접촉 실증) (b) crop side px parity 로그 판정 (c) trim_only anchors 소비를 검증할 수 있음.
- **32-06 준비:** phase32 conftest 재사용 가능(fake_firestore 는 phase31 것 복제/import).
- **블로커 없음.** 새 분석부터 적용(기존 doc 재처리 금지 — 같은 RTMW 엔진).

## Self-Check: PASSED

- 생성/수정 파일 8종 전부 존재 (conftest/ladder/parity 신설 3 + motion_alignment/fault_zoom/test 2벌 수정 4 + SUMMARY).
- 커밋 5종 전부 존재: 39537b4(T1 RED)/27eafe5(T1 GREEN)/545dcdd(T2 RED)/b5afe29(T2 GREEN)/f00f653(SUMMARY).
- 검증 160 passed, 채점 모듈 diff 0.

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-21*
