---
phase: quick-260705-r6x
plan: 01
subsystem: ui
tags: [fault-zoom, pillow, split, ipsf, display-render, mode1]

requires:
  - phase: quick-260702-sic
    provides: fault_zoom grouping(region legs/arms) + 3단 강하 crop + anchor 정밀화
  - phase: quick-260704-fz4
    provides: deficit 배지 라벨("N°") + advisory tier 배선
  - phase: quick-260705-ftn
    provides: select_confident_frame(측정-표시 정합) + _to_rep_idx 단일 출처
provides:
  - "legs(스플릿) 확대 카드 사이각 시각화 — 골반 중점→양 다리 선 2 + minor arc + 각도 수치"
  - "split_angle record(measuredValue/baselineValue) → 호 옆 수치 (측정-표시 정합)"
  - "_leg_line_pts / _draw_leg_angle / _to_crop_px / split_angle_degs_from_records"
affects: [fault-zoom, mode1, split-scoring, app-KeypointOverlay]

tech-stack:
  added: []
  patterns:
    - "display 전용 사이각 드로잉 — 채점/veto/게이트 무접촉 (선/호/숫자만, 한글은 앱)"
    - "측정-표시 정합 — 화면 수치 = 점수가 쓴 split_angle record 그 값"

key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/tests/test_fault_zoom.py
    - backend/tests/test_fault_zoom_relaxed_crop.py
    - backend/functions/pipeline/app.py

key-decisions:
  - "legs 카드는 동그라미 대신 다리 사이각(선+호)을 그린다 (belle 2026-07-05 실기기)"
  - "수치 출처 = deductionBreakdown.records 의 split_angle record (측정-표시 정합), 부재 시 선+호만"
  - "저신뢰(relaxed/full) 측은 사이각 생략 — 기존 폴백 유지(오인 방지)"
  - "user 측 사이각 그린 카드는 원 생략(배지 유지), ref 측은 _mark 없이 선+호+수치만"

patterns-established:
  - "_to_crop_px: 정규화→crop 픽셀 변환 단일 출처 (anchor_px 와 사이각 좌표 공유)"
  - "_MIN_LEG_VEC_PX degenerate 게이트 — 겹친 좌표는 드로잉 생략하고 기존 렌더 폴백"

requirements-completed: [QUICK-260705-r6x]

duration: ~35min
completed: 2026-07-05
---

# Quick 260705-r6x: 스플릿 확대 카드 다리 사이각 시각화 Summary

**legs(스플릿) fault-zoom 카드를 앵커 동그라미에서 "골반 중점→양 다리 선 2개 + 사이각 호 + 측정 각도 수치"로 교체 — 호 크기 차이가 곧 결함으로 보이고, 수치는 점수가 쓴 split_angle record 그 값(측정-표시 정합). 채점 무접촉 display 전용.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2 (Task 1 tdd, Task 2 wiring)
- **Files modified:** 4

## Accomplishments
- `_leg_line_pts` — 골반 중점 + 다리 끝(ankle 우선/knee 폴백) 3점 해석 (게이트 통과 필수, 하나라도 실패 시 None)
- `_draw_leg_angle` — 선 2 + PIL minor arc(atan2/시계방향 정합) + 각도 배지, degenerate(벡터<8px) 시 False 폴백
- `_to_crop_px` — 정규화→crop 픽셀 변환 단일 출처화 (기존 anchor_px 산출을 이 헬퍼로 교체, 산출 동일)
- `split_angle_degs_from_records` — 점수가 쓴 split_angle record(measuredValue=학생/baselineValue=180) 추출, 측별 defensive None + graceful
- `build_fault_zoom_comparisons` split_angle_degs keyword — legs valid 측만, 측별 독립, non-legs/legacy 완전 무접촉
- pipeline `_render_fault_zoom`/`_attach_fault_zoom_comparisons` 배선 — records 에서 수치 추출 → confirmed/advisory 두 배치 전달, Mode3 무접촉(선+호만)

## Task Commits

1. **Task 1: fault_zoom 렌더러 — legs 사이각 시각화** - `ea418a9` (feat, tdd)
2. **Task 2: pipeline split_angle record 배선** - `c33aadb` (feat)

## Files Created/Modified
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` - _gated_kp/_leg_line_pts/_to_crop_px/_draw_leg_angle/_draw_side_leg_angle/split_angle_degs_from_records 추가, _side_crop 4-tuple(box), build split_angle_degs keyword
- `backend/tests/test_fault_zoom.py` - 신규 8 테스트(순수 3점/드로잉 분기/수치 표기·생략/저신뢰 폴백/non-legs 무변경/record 추출/픽셀 smoke)
- `backend/tests/test_fault_zoom_relaxed_crop.py` - anchor 테스트 4-tuple 언팩 + grouped-circle 테스트 arms 로 재표적(legs→사이각 이전, 계약 보존)
- `backend/functions/pipeline/app.py` - _render_fault_zoom split_angle_degs passthrough + _attach_fault_zoom_comparisons split record 추출

## Decisions Made
- 계약 이전: grouped 카드 circle=deficit 최대 관절 규칙은 non-legs(arms)에 여전히 유효 → 기존 legs 테스트를 arms 로 재표적(삭제 0). legs 는 사이각 드로잉으로 이전.
- `test_grouping_legs_single_card`(전 좌표 겹침)는 degenerate 폴백으로 기존 산출 유지 → 무수정 GREEN 회귀 가드로 보존.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] _side_crop 3-tuple 언팩 테스트 조정**
- **Found during:** Task 1
- **Issue:** 계획 point 7 은 "[0]/[:2]/[2] 인덱싱이라 하위호환"이라 했으나 `test_side_crop_anchor_maps_to_joint_pixel` 은 3-tuple 직접 언팩(`_img, kind, anchor_px = ...`)이라 4-tuple 반환 시 ValueError.
- **Fix:** 해당 언팩을 `_img, kind, anchor_px, _box = ...` 로 조정 (형상 계약 변경의 필연적 동반, 삭제 0)
- **Files modified:** backend/tests/test_fault_zoom_relaxed_crop.py
- **Verification:** 45 passed
- **Committed in:** ea418a9 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** _side_crop 4-tuple 계약 확장의 필연적 동반 조정. 스코프 확장 없음.

## Issues Encountered
- 전체 스위트에 pre-existing 실패 54건 + collection error 11건 존재 (torch/rtmlib/mediapipe/`fixtures` 미설치, gemini env, phase06/08 통합 의존). base(ac54ca8, Task2 미적용) 실행과 **동일 카운트(54 failed / 2233 passed / 11 errors)** 확인 → 본 작업 회귀 0. 채점 파일(dimensions/deduction_engine/vision_veto/kismam) diff 0.

## Verification
- `pytest tests/test_fault_zoom.py tests/test_fault_zoom_relaxed_crop.py -q` → **45 passed** (요구 검증 명령)
- `pytest tests/ -q --continue-on-collection-errors` → 2233 passed (신규/재표적 포함), 실패 54건 = base 동일 pre-existing
- `grep _draw_leg_angle fault_zoom.py` → 렌더러 4회 참조, `grep split_angle_degs_from_records app.py` → 배선 존재
- 채점 무접촉: dimensions/deduction_engine/vision_veto/kismam diff 0

## Follow-up Fix — pod PNG 1차 검증 결함 2건 (commit 19ac673)
belle pod 재분석(kip-up fault) PNG 육안 검증에서 결함 2건 발견 → 같은 날 수정:

**1. 라벨 값 오류 (학생 50°=deficit / 기준 0°)**
- 근본원인: plan 의 record 형상 가정(ipsf_absolute, measuredValue=180−deficit/baselineValue=180)이 현행과 불일치. 현행 split_angle criterion 은 **reference_relative**(ipsf_criteria.py:106, split_vs_reference_over_tol_linear) — record = measuredValue=정은지-대비 편차(50), baselineValue=0.0. 추출기가 그대로 표기해 오독 발생.
- fix: `split_angle_degs_from_records` 가 `deviationSource=='ipsf_absolute'`(벌림각 semantics)만 수치화, 반환=(학생 벌림각, None). 기준 측 수치는 **항상 생략** — baselineValue 180 은 IPSF 목표치지 정은지 실측각이 아님(미측정 수치 부착 금지). reference_relative(현행 vision-주입 kip-up 경로 포함) → 전체 None(선+호만). 결과: 현행 프로덕션 split record 로는 수치 없이 선+호만 — honest. ipsf_absolute split 경로(per-move expects_split, ipsf_criteria 후속 예정)가 생기면 학생 벌림각 수치가 자동 점등.

**2. 기준 측 선 폭주 (몸과 무관한 방향)**
- 근본원인: `_gated_kp` 가 confidence 부재(legacy report)를 통과 취급(crop 게이트 선례 답습) → confidence 없는 reference report 의 미증명 좌표로 드로잉.
- fix: 사이각 드로잉 게이트를 **conf >= _KP_CONF_MIN 명시 증명 좌표만**으로 조임(conf 부재도 불허). crop 게이트(_member_pts, 부재=통과)는 무접촉 — 기존 crop 산출 불변, 드로잉만 보수적.

검증: 46 passed(기존 45 + conf부재 ref 가드 1) / 전체 2234 passed·54 pre-existing(base 동일, 회귀 0). 채점 무접촉 유지.

## Follow-up Fix 2 — 기준 측 선 폭주 잔존 (commit 53d7484)
belle pod 2차 PNG 재확인: 라벨 오표기는 해결됐으나 **기준(정은지) 측 선이 여전히 crop 밖으로 폭주**. belle 가 좌표로 근본원인 특정 — ref-kip-up matched frame(~37)의 legs conf 는 0.55~0.80 으로 _KP_CONF_MIN(0.5) 통과(그래서 conf 게이트만으로는 못 막음). 그러나 (1) 그 순간 정은지는 다리를 모은 상태(스플릿 아님), (2) 정은지 측 crop box 가 정강이/발 하단만 잘라 **hip(선 시작점)이 crop 영역 밖** → _to_crop_px 의 [0,_OUT-1] clamp 가 hip 을 crop 상단 경계로 당겨 선이 몸과 무관하게 뻗음.
- fix: **crop-포함 기하 게이트** 추가. `_pt_in_crop` 이 드로잉 3점(hip 중점+양 knee/ankle)의 crop-내 raw 픽셀(clamp 전)이 crop 박스 [−margin, _OUT+margin] 안인지 검사. `_draw_side_leg_angle` 이 conf 게이트 **AND** crop-포함 게이트 — 하나라도 crop 밖이면 그 측 사이각 생략, 기존 선 없는 crop 폴백. margin = `_CROP_INCLUSION_MARGIN_PX`(int(_OUT*0.10)=36px, display 전용).
- 학생 측 무영향: crop 이 다리를 포함하므로 3점 전부 in-crop → 정상 드로잉 (regression 유닛 `test_legs_valid_side_draws_angle` 2 calls 유지 확인).

검증: 48 passed(+2: _pt_in_crop 순수 / crop 밖 hip 생략·대조) / 전체 2236 passed·54 pre-existing(base 동일, 회귀 0). 채점 무접촉 유지.

## PENDING — 실 PNG 재검증 (fix 2 후)
**실 PNG 재검증 = pod 재분석 PENDING (belle 수행).** fix 2 후 확인 포인트:
1. kip-up fault: 기준(정은지) 측 선 폭주 소멸 — crop 이 hip 을 안 담는 프레임에서 사이각 생략(선 없는 crop), 학생 측 라벨 50°/기준 0° 소멸(reference_relative → 수치 없이 선+호만)
2. 학생/기준 양측이 모두 스플릿 자세 + crop 이 골반~다리 전체 포함하는 valid 프레임에서만 선+호 렌더, 호 크기 차이가 벌림 각도 차이를 반영
3. (향후 ipsf_absolute split 경로 도입 시) 학생 측 벌림각 수치 표기 확인

## Next Phase Readiness
- 렌더러 + 배선 + 유닛테스트 완료. 앱(KeypointOverlay/카드 캡션)은 이미지 위 숫자만 소비하므로 TS 계약 변경 불필요(선/호/수치는 PNG 내 픽셀).
- 미결 = fix 후 실 PNG 재검증(pod, belle 수행 — 위 PENDING).
- 관찰: 현행 split 감점 경로가 reference_relative 뿐이라 프로덕션 legs 카드는 당분간 수치 없음. 벌림각 수치를 원하면 ipsf_absolute split(expects_split flag) 경로 도입이 선행 조건 — ipsf_criteria.py §split 주석의 "후속" 그것.

## Self-Check: PASSED
- commit ea418a9 (Task 1) — FOUND
- commit c33aadb (Task 2) — FOUND
- commit 19ac673 (Follow-up fix 1: 라벨 semantics + conf 게이트) — FOUND
- commit 53d7484 (Follow-up fix 2: crop-포함 게이트) — FOUND
- 260705-r6x-SUMMARY.md — FOUND

---
*Phase: quick-260705-r6x*
*Completed: 2026-07-05*
