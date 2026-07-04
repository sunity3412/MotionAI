---
phase: 25-vision-pointed-upper-body
plan: 03
subsystem: analysis-display
tags: [fault-zoom, pil, numpy, crop, keypoint-confidence, display-only]

# Dependency graph
requires:
  - phase: quick-260702-sic
    provides: "_KP_CONF_MIN 게이트 + 전신 폴백 + 결함단위 grouping + sourceFrameIndices override"
  - phase: quick-260704-fz4
    provides: "confirmed/advisory 2단 시각 언어 + select_advisory_joints"
provides:
  - "_side_crop 3단 강하 (valid → relaxed → full) + crop_kind 신호"
  - "저신뢰-유한 좌표 부위-중심 완화(relaxed) crop — 카드별 차별화 (동일 전신 반복 해소)"
  - "_RELAXED_MARGIN=2.0 (display 전용, 채점 무접촉 신규 상수 1개)"
  - "앵커 circle = 결함 관절의 crop-내 상대 좌표 고정 (grouped 카드 = deficit 최대 대표 관절)"
  - "relaxed/full 측 circle 생략 (좌표 불확실 — 확정 표식 금지)"
affects: [25-04 sweep 재분석 (실 PNG 재생성 + belle 육안 확인), fault-zoom 후속 UI]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "3단 crop 강하: 신뢰 좌표 → 저신뢰-유한 완화 crop → 결측 전신 폴백"
    - "_crop_box(순수 기하) / _render_crop(렌더) 분리 — 관절→crop 상대좌표 산출 재사용"
    - "display 전용 상수는 채점 calibration gate 대상 아님을 주석으로 명시"

key-files:
  created:
    - backend/tests/test_fault_zoom_relaxed_crop.py
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py

key-decisions:
  - "카드 생성은 최소 한 측 valid 유지 (양측 비-valid = 기존 skip 보존) — 기존 21 테스트 무수정 PASS 하드 게이트 + 오인 방지"
  - "앵커 circle 은 기존처럼 user 측에만 (ref 측은 원래 무마킹 — 변경 없음)"
  - "_valid_kp_xy dead code 제거 (_member_pts 로 규칙 흡수), _crop_zoom → _crop_box+_render_crop 재구성"

patterns-established:
  - "crop_kind ∈ {valid, relaxed, full} 신호가 _mark 의 앵커 표시 여부를 결정"
  - "grouped 카드 anchor = deficit(|delta|) 최대 valid 멤버 (_anchor_xy)"

requirements-completed: [TRUST-08]

# Metrics
duration: 14min
completed: 2026-07-04
---

# Phase 25 Plan 03: 확대 카드 정밀도 (relaxed crop + 앵커 정밀화) Summary

**fault_zoom _side_crop 3단 강하(valid→relaxed→full)로 reference 저신뢰 시 카드별 부위-중심 완화 crop + 앵커 circle 을 결함 관절 좌표에 고정 (relaxed/full 은 생략)**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-07-04T05:16:00Z
- **Completed:** 2026-07-04T05:30:00Z
- **Tasks:** 2 (Task 1 TDD RED+GREEN, Task 2)
- **Files modified:** 2

## Accomplishments

- **동일 전신 반복 해소:** reference(정은지) 측 keypoint 가 저신뢰(<0.5)여도 좌표가 유한하면 그 좌표 중심의 완화(relaxed) crop — 카드마다 다른 부위가 나온다 (kip-up 류 "분석 안 한 것처럼 보임" 해소). 좌표 자체 결측(NaN/부재)만 기존 전신 폴백.
- **완화 crop 폭:** 기존 grouped 공식(max(bbox)×1.8, floor=_CROP_FRAC) × `_RELAXED_MARGIN=2.0` — display 전용 신규 상수 1개, "채점 무접촉" 주석 박제 (calibration-source-hard-gate 대상 아님).
- **앵커 정밀화:** valid crop 의 circle 이 crop 중심이 아닌 결함 관절의 crop-내 상대 좌표에 놓인다. grouped(2관절+) 카드는 deficit 최대 대표 관절 1개에 circle. relaxed/full 측은 circle 생략 (deficit 배지는 유지) — 불확실 좌표에 확정 표식 금지 (260702-sic belle 요구 3 정신).
- **무회귀:** 기존 `tests/test_fault_zoom.py` 21개 무수정 PASS. 신규 12개 포함 33 passed. 계약/스키마/S3 키 불변 (PNG 내부 구도만 변경).

## Task Commits

1. **Task 1 (RED): relaxed crop 3단 강하 실패 테스트** - `0c56a24` (test)
2. **Task 1 (GREEN): _side_crop 3단 강하 + relaxed crop 구현** - `a22c153` (feat)
3. **Task 2: 앵커 관절-좌표 고정 + relaxed/full circle 생략** - `67471ea` (feat)

## TDD Gate Compliance

- RED gate: `0c56a24` — 5/6 신규 테스트 FAIL 확인 (1개 통과분은 기존 NaN→전신 폴백 동작을 못 박는 회귀 가드로 의도된 통과, truth #4).
- GREEN gate: `a22c153` — 신규 6 + 기존 21 = 27 passed.
- REFACTOR: Task 2 커밋에 포함 (_crop_box/_render_crop 분리, dead code 제거) — 33 passed 유지.

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` - `_RELAXED_MARGIN` 상수, `_member_pts`(valid/relaxed 분류), `_anchor_xy`(대표 관절 선택), `_crop_box`/`_render_crop`(기하/렌더 분리), `_side_crop` 3단 강하 + anchor_px 반환, `_mark(anchor_px=)`, 호출부 정합
- `backend/tests/test_fault_zoom_relaxed_crop.py` - 합성 gradient 프레임(위치-인코딩 픽셀) + per-joint 위치/confidence 합성 report 로 3단 강하·카드별 차별화·앵커 위치·circle 생략 12 테스트

## Decisions Made

1. **양측 비-valid skip 보존:** 플랜 문구 "relaxed 는 skip 대상이 아니다"를 "반대측이 valid 인 카드에서 relaxed 가 전신 폴백을 대체한다(카드 유지)"로 한정 해석. 양측 모두 valid 0(양측 relaxed 포함)은 기존 skip 유지. 근거: (a) 하드 게이트 "기존 21 테스트 무수정 PASS"의 `test_both_sides_low_confidence_skipped`(양측 저신뢰→skip)와 문자적 해석이 충돌, (b) 양측 다 불확실 crop 카드는 오인 위험(260702-sic 요구 3 정신), (c) 본 플랜의 실제 버그 시나리오(학생 valid + reference 저신뢰)는 완전 커버됨.
2. **앵커는 user 측 전용 (기존 유지):** ref 측은 원래 `_mark` 미호출(무마킹)이라 "고신뢰 측 앵커"는 실제 앵커가 그려지는 user 측에 적용. ref 측 시각 마킹 신설은 스코프 밖.
3. **dead code 정리:** `_valid_kp_xy` 는 `_member_pts` 가 동일 규칙을 흡수해 미사용 → 제거. `_crop_zoom` 은 anchor 상대좌표 산출을 위해 `_crop_box`(순수 기하, 기존 clamp 경계 처리 보존 — T-25-07 재사용) + `_render_crop` 으로 재구성.

## Deviations from Plan

**1. [해석 조정] 양측 비-valid 카드 skip 유지 (플랜 문구 대비 한정 해석)**
- **Found during:** Task 1 설계
- **Issue:** 플랜 "relaxed 는 skip 대상이 아니다" 문자적 구현 시 기존 `test_both_sides_low_confidence_skipped` 가 깨져 "기존 21 무수정 PASS" 게이트와 충돌
- **Fix:** relaxed 는 반대측 valid 카드의 전신 폴백 대체로 한정, 양측 valid 0 은 기존 skip
- **Files modified:** fault_zoom.py (skip 규칙 주석 박제)
- **Verification:** 기존 21 + 신규 12 전부 PASS
- **Committed in:** a22c153

**2. [Rule 1 - 정리] _valid_kp_xy dead code 제거**
- **Found during:** Task 2
- **Issue:** `_member_pts` 도입 후 미사용 (규칙 중복)
- **Fix:** 제거 + 규칙/근거 docstring 을 `_member_pts` 로 이전
- **Files modified:** fault_zoom.py
- **Verification:** grep 참조 0 + 전 테스트 PASS
- **Committed in:** 67471ea

---

**Total deviations:** 2 (해석 조정 1, 정리 1)
**Impact on plan:** 스코프 확장 없음. 플랜의 must_have truths 4개 전부 충족 (truth #1~4 모두 테스트로 증명).

## Issues Encountered

- Task 2 verify 명령(`pytest tests/ -k "fault_zoom or zoom"`)에서 collection error 11건 — 전부 pre-existing env-의존 spike/smoke 파일(rtmpose/gemini/mediapipe deps, fault_zoom 무관·본 diff 무접촉). `--continue-on-collection-errors` 로 zoom 대상 33 passed 확인. 범위 밖이라 미수정 (scope boundary).

## Verification (plan gates)

- `pytest tests/test_fault_zoom_relaxed_crop.py -q` → 12 passed
- `pytest tests/test_fault_zoom.py -q` → 기존 21 passed (무수정)
- 채점 무접촉: `git diff --stat 535b190..HEAD` = fault_zoom.py + 신규 테스트 파일만. fault_zoom.py import = io/dataclass/numpy/PIL 뿐 (deduction_engine/dimensions/kismam import 0)
- 계약/스키마 diff 0 (방출 dict 키 불변: joint/deficitDeg/png/kind/region)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Follow-up (플랜 명시):** 실 PNG 육안 확인은 25-04 sweep 재분석 산출물로 belle 확인 필요 — 본 플랜은 Pod-free 단위 테스트까지 (저장된 PNG 는 재분석 전까지 구 버전).
- crop_kind 신호는 현재 모듈 내부 전용 — 앱 노출(예: "위치 추정" 캡션) 필요 시 별도 계약 작업.

## Self-Check: PASSED

- 커밋 3개 존재 확인 (0c56a24 / a22c153 / 67471ea, base 535b190)
- 생성/수정 파일 존재 확인 (fault_zoom.py, test_fault_zoom_relaxed_crop.py, 본 SUMMARY)
- 의도치 않은 파일 삭제 0 (`git diff --diff-filter=D` 빈 출력)
- 최종 게이트: test_fault_zoom.py + test_fault_zoom_relaxed_crop.py = 33 passed

---
*Phase: 25-vision-pointed-upper-body*
*Completed: 2026-07-04*
