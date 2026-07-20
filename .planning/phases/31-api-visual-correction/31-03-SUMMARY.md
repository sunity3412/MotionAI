---
phase: 31-api-visual-correction
plan: 03
subsystem: ml
tags: [fault-zoom, overlay, geometry, pil, numpy, dtw, provenance]

# Dependency graph
requires:
  - phase: 28-dtw-motion-alignment
    provides: "_matched_ref_frame DTW 프레임 대응 + refMatch provenance (D-04)"
  - phase: 24-deduction-engine
    provides: "DeductionRecord(criterion/points signed-negative) + ipsf_criteria CRITERION_GROUPS"
provides:
  - "TargetArrowSpec — 목표 각도 화살표 스펙 (reference 3점 2D similarity 정합 기하)"
  - "joint_inner_angle_deg — 각도 산출 단일 출처 (arrow / CorrectedPoseTarget / 31-06 pose gate 공유)"
  - "_frame_mirror_parity — full-body topology 프레임 단위 미러 판정 + provenance"
  - "ARROW_JOINT_MAP — 화살표/target 대상 관절 명시 선언 (6 관절)"
  - "CorrectedPoseTarget + build_corrected_pose_target — 자동 교정 target 단일 immutable 계약"
  - "CRITERION_JOINT_MAP — 감점 criterion → joint_key 명시 선언 매핑"
  - "HISTORICAL_JOINT_REGISTRY — append-only 삭제 전용 안정 레지스트리 (31-07 pairId 재계산 근거)"
  - "줌 item 의 userFrameIdx/refFrameIdx/refMatched scalar (2D 비교 뷰어 프레임 정합 소스)"
affects: [31-04, 31-06, 31-08, 31-09, 31-10, 31-12]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "기하 단일 출처: joint_inner_angle_deg 를 arrow/target/pose gate 가 공유 — 각도 계산 이원화 금지"
    - "omission-first 렌더: 불확실하면 그리지 않는다 (omit_reason 6종, 드로잉 0)"
    - "채점 데이터 경계: 기하 함수가 DeductionRecord 를 인자로도 받지 않음 (시그니처로 고정)"
    - "선언적 매핑 게이트: ARROW_JOINT_MAP / CRITERION_JOINT_MAP 에 선언된 것만 렌더/후보"

key-files:
  created:
    - backend/tests/test_fault_zoom_arrow.py
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py

key-decisions:
  - "미러 반사 결정자 = full-body topology parity 단독. per-joint '가까운 후보' 휴리스틱 제거 (H2-03) — parity 불명이면 화살표 생략"
  - "target_deg 는 DTW matched reference 3점 내각에서만 산출. 감점 record 는 후보 우선순위(abs(points))에만 사용 (B2-01)"
  - "후보 정렬 = abs(points) 내림차순 + criterion key 오름차순 — signed-negative max(points) 함정 차단 + 결정론 tie-break (M3-06)"
  - "CRITERION_JOINT_MAP 은 per-joint criterion 6개만 선언. collective(line)/양측 묶음(leg_extension·arm_extension·split_angle)/reach 는 단일 COCO 관절로 환원 불가라 제외 = correctedPose 생략"
  - "draw_arrows 기본 False — 기존 호출 전부 PNG 바이트 동일 무회귀. pipeline 은 confirmed 배치만 True, advisory 는 False(확정 어조 오인 방지)"
  - "사이각을 그린 legs 카드에는 화살표 미드로잉 (호와 화살표가 발목 주변에서 시각 언어 충돌) — 병행 렌더는 31-12 실 fixture 시각 게이트 후 재검토"
  - "build_corrected_pose_target 에 ref_frame_shape 필수화 — 미상이면 None 반환(생성 생략). keypointReport 좌표가 W/H 로 각각 정규화돼 비정사각 프레임에서 내각이 왜곡되기 때문"

patterns-established:
  - "provenance 스칼라 방출: 렌더 계층이 판정 결과(mirror_parity/refMatched/frame idx)를 소비자에게 그대로 넘긴다"
  - "append-only 삭제 레지스트리: 렌더 계약(가변)과 삭제 계약(불변) 분리 — 고아 페어 방지"

requirements-completed: [D-05, D-10, D-11, D-12]

# Metrics
duration: 42min
completed: 2026-07-20
---

# Phase 31 Plan 03: 목표 각도 화살표 + correctedPose target 계약 Summary

**DTW 대응 reference 3점의 2D similarity 정합으로 목표 각도 화살표를 그리고, 자동 교정의 joint/targetDeg/source frame 을 CorrectedPoseTarget 단일 immutable 계약으로 고정 — 감점 record 수치가 화면 기하와 목표각에 유입될 경로를 시그니처 수준에서 제거**

## Performance

- **Duration:** 42 min
- **Tasks:** 3 / 3
- **Files modified:** 3 (1 created, 2 modified)
- **Tests:** 29 신규 (fault_zoom 계열 전체 111 green)

## Accomplishments

- **리뷰 B-02 해소** — 화살표 endpoint 를 (proximal, vertex, distal) 3점 + DTW 대응 reference 좌표의 similarity 정합으로만 산출. `_build_arrow_spec` 은 `DeductionRecord` 를 인자로 받지 않으며, 기하 함수 소스에 `measuredValue`/`baselineValue`/`deviation` 참조가 0임을 `inspect.getsource` 로 고정.
- **2차 리뷰 H2-03 해소** — 미러 반사 후보 선택 로직 자체를 제거. `_frame_mirror_parity` 가 어깨/힙 topology 로 프레임 단위 1회 판정하고, 어깨-힙 부호 불일치·좌우 분리 붕괴 시 `unknown` → 화살표 생략. **adversarial golden**(교정이 커서 틀린 반사 후보가 현재 distal 에 더 가까운 fixture) 포함 — 거리 기반 구현이면 실패한다.
- **2차 리뷰 B2-01 해소** — `CorrectedPoseTarget` 이 joint/targetDeg/user_frame_idx/ref_frame_idx/confidence/provenance_version 을 하나의 frozen dataclass 로 묶는다. record 수치를 999 로 오염시켜도 `target_deg` 불변 테스트로 미유입 증명.
- **리뷰 B-01 해소** — 줌 item 이 `userFrameIdx`/`refFrameIdx`/`refMatched` 를 `draw_arrows` 무관하게 항상 방출. 방출값이 `_matched_ref_frame` 산출과 일치함을 테스트로 고정 (T-31-11).
- **무회귀 증명** — `draw_arrows` 기본 False 경로의 PNG 바이트 동일. 기존 fault_zoom 테스트 82개 무수정 통과.

## Task Commits

1. **Task 1: TargetArrowSpec + parity + 정합 기하 + 드로잉** - `c140bf0` (feat)
2. **Task 2: CorrectedPoseTarget 단일 계약** - `573322e` (feat)
3. **Task 3: 줌 렌더 배선 + 프레임 쌍 방출 + 무회귀** - `62bd79d` (feat)

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — `joint_inner_angle_deg`, `TargetArrowSpec`, `ARROW_JOINT_MAP`, `_parity_pts`, `_facing_sign`, `_frame_mirror_parity`, `_omit_arrow`, `_build_arrow_spec`, `_draw_target_arrow`, `CorrectedPoseTarget`, `CRITERION_JOINT_MAP`, `HISTORICAL_JOINT_REGISTRY`, `CP_TARGET_PROVENANCE_VERSION`, `build_corrected_pose_target` 신설 + `build_fault_zoom_comparisons` 에 `draw_arrows` 파라미터/프레임 쌍 방출 추가
- `backend/functions/pipeline/app.py` — `_render_fault_zoom` 이 confirmed 배치에 `draw_arrows=True` 전달, advisory 는 False. item 조립부에 프레임 쌍 3종 scalar pass-through
- `backend/tests/test_fault_zoom_arrow.py` (신규, 795줄) — 기하 golden / parity adversarial / omission 6종 / CorrectedPoseTarget §8 gate / 배선·정렬 테스트 29개

## Decisions Made

- **화살표 대상 관절 6개** (양 무릎·팔꿈치·힙). 어깨(`*_shoulder`)는 `JOINT_ANGLES` 에는 있으나 vertex 기하가 몸통-팔 혼합이라 v1 화살표 대상에서 제외. `CRITERION_JOINT_MAP` 도 같은 6개만 선언해 두 맵이 어긋나지 않게 했다 (target 은 있는데 화살표는 없는 불일치 방지).
- **반사는 내각을 바꾸지 않으므로** `build_corrected_pose_target` 은 parity 를 게이트로만 쓰고 reference 좌표에 반사를 적용하지 않는다 (불필요한 변환 제거).
- **advisory 카드에 화살표 미드로잉** — "여기까지 올려야 함"은 확정 지시라 "측정 초과·확인 권장" 카드에 얹으면 어조가 뒤집힌다. 기존 게이트 A(`split_angle_present=False`) 선례와 동일 취지.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `build_corrected_pose_target` 에 `ref_frame_shape` 추가 (fail-closed)**
- **Found during:** Task 2
- **Issue:** 플랜 시그니처 `(records, user_report, ref_report, dtw_pairs, ref_match_failed)` 만으로는 프레임 종횡비를 알 수 없다. `keypointReport` 좌표는 프레임 W/H 로 **각각** 정규화돼 있어(모듈 docstring), 비정사각 프레임(frame_extractor 는 긴 변 640 리사이즈 → 대부분 비정사각)에서 정규화 좌표를 그대로 내각에 넣으면 종횡비만큼 각도가 왜곡된다. 왜곡된 `target_deg` 는 31-09 의 프롬프트와 pose gate **양쪽**에 동시에 들어가 "잘못된 목표에 정확히 맞춘" 이미지가 gate 를 통과하게 만든다 — B2-01 이 막으려던 바로 그 실패 모드.
- **Fix:** keyword-only `ref_frame_shape: tuple[int, int] | None = None` 추가. `None` 이면 목표각을 신뢰할 수 없으므로 `None` 반환(생성 생략) — 플랜의 "불확실 = None 생략(legacy 숨김)" 규칙과 동일 처리. `joint_inner_angle_deg` docstring 에도 "등방 좌표계(frame px) 입력" 계약을 박제.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/fault_zoom.py`
- **Verification:** `test_none_when_uncertain` 의 "프레임 형상 미상 → None" 케이스 + `test_target_deg_tracks_reference_shape_not_record` (90도 reference → target_deg 90.0)
- **Committed in:** `573322e`

**2. [Rule 2 - Missing Critical] `degenerate_segment` omit_reason 추가**
- **Found during:** Task 1
- **Issue:** 플랜의 omission 목록(ref_match_failed / unmapped_joint / low_confidence / parity_unknown / negligible_delta)에 **proximal↔vertex 좌표가 겹치는 경우**가 없다. 이 경우 similarity 변환의 분모가 0 이라 `ZeroDivisionError` 또는 무의미한 방향의 화살표가 나온다.
- **Fix:** `_MIN_SEG_PX` 가드 + `omit_reason='degenerate_segment'`. 기존 `_MIN_LEG_VEC_PX` 드로잉 가드와 동일 취지로 문서화.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/fault_zoom.py`
- **Verification:** `test_degenerate_segment_omitted`
- **Committed in:** `c140bf0`

**3. [Rule 2 - Missing Critical] criterion id 오타 드리프트 lockstep 게이트 추가**
- **Found during:** Task 2
- **Issue:** `CRITERION_JOINT_MAP` 은 문자열 키라 `ipsf_criteria.CRITERION_GROUPS` 의 실제 id 와 조용히 어긋날 수 있다. 어긋나면 후보가 0 이 되어 correctedPose 가 **영구히 생성되지 않는데도** 에러가 없다(조용한 기능 무력화).
- **Fix:** 테스트에서 `CRITERION_JOINT_MAP` 키가 실제 채점 엔진 criterion id 의 부분집합인지 검증. 검증은 테스트 전용 import 라 `fault_zoom` 자체의 채점 모듈 무의존은 유지(별도 테스트로 고정).
- **Files modified:** `backend/tests/test_fault_zoom_arrow.py`
- **Verification:** `test_declared_criteria_exist_in_scoring_engine`, `test_arrow_target_path_does_not_import_scoring_modules`
- **Committed in:** `573322e`

---

**Total deviations:** 3 auto-fixed (3 missing critical)
**Impact on plan:** 전부 플랜이 명시한 불변식(잘못된 target 으로 생성하지 않는다 / 기하가 채점에 오염되지 않는다)을 실제로 성립시키기 위한 보강. 범위 확장 없음 — 신규 화면 0, 앱 파일 변경 0, 채점 경로 변경 0.

## Issues Encountered

- **합성 fixture 의 torso 덮어쓰기** — 초기 테스트가 `left_hip`/`right_hip` 을 몸통 좌표와 별개로 덮어써 parity 판정이 깨졌다(`parity_unknown` 오검출). hip 은 몸통 keypoint 이기도 하다는 점을 반영해 fixture 를 "torso 가 정한 hip 기준 offset 으로 knee/ankle 을 얹는" 구조로 재작성. 실제로 parity 게이트가 작동한다는 방증이기도 하다.

## 무회귀 검증 (pre-existing 실패 분리)

`python -m pytest backend/tests -q` 는 리포지토리 기준 상태에서 이미 **41 failed / 2911 passed** + 2 collection error(`fixtures.*` import 경로 문제)를 낸다. 본 플랜의 변경을 되돌리고(`backend/functions/pipeline/app.py` 원복) 동일 명령을 실행한 결과가 **41 failed / 2911 passed 로 완전히 동일**함을 확인해, 잔여 실패가 전부 pre-existing 이며 본 플랜과 무관함을 증명했다. 관련 실패는 `find_scene_flags` 등 Gemini wiring 심볼 부재로, fault_zoom / 오버레이 경로와 접점이 없다.

- `backend/tests/test_fault_zoom_arrow.py` — 29 passed
- fault_zoom 계열 6개 파일 — 111 passed

## Next Phase Readiness

- **31-04 (TS 계약):** `FaultZoomComparison` 에 optional `userFrameIdx`/`refFrameIdx`/`refMatched` 추가 필요. 백엔드는 이미 방출 중이며 부재=legacy doc 취급이라 순서 의존 없음.
- **31-06 (pose gate):** `joint_inner_angle_deg` 를 import 해 각도를 계산해야 한다 — 자체 각도 계산 구현 금지(계산 이원화 시 생성 지시와 검증 기준이 갈라진다).
- **31-08 (2D 비교 뷰어):** 프레임 정합 소스 준비 완료. `refMatched=False` 인 카드는 `refFrameIdx` 가 전신 폴백의 중앙 프레임이라 정합 근거가 아님에 유의.
- **31-09 / 31-10 (correctedPose):** 리뷰 §7 Step 1 계약 확정 조건 충족. `CorrectedPoseTarget.to_payload()` 의 스칼라만 소비할 것. `sourceHash` (프레임 PNG sha256 full hex) 산출·병합은 31-10 pipeline 책임이며 S3 srcKey 세그먼트는 `sourceHash[:16]`.
- **31-12 (E2E):** 실 fixture 시각 게이트에서 (1) 화살표 방향 육안 확인, (2) legs 카드의 호/화살표 병행 렌더 여부 재검토가 필요하다 (현재 v1 은 한 카드에 하나만).

### 미해소 (설계상 의도)

- 실 영상 기반 시각 확인은 Pod 가 필요해 31-12 로 이월 (플랜 `<verification>` 명시). 본 플랜의 게이트는 합성 fixture golden 까지다.

---
*Phase: 31-api-visual-correction*
*Completed: 2026-07-20*

## Self-Check: PASSED

- 산출물 4개 파일 전부 존재 확인
- 태스크 커밋 3개(`c140bf0`, `573322e`, `62bd79d`) git 이력 확인
- 계약 심볼 10종(TargetArrowSpec / CorrectedPoseTarget / ARROW_JOINT_MAP / CRITERION_JOINT_MAP / HISTORICAL_JOINT_REGISTRY / joint_inner_angle_deg / _frame_mirror_parity / _build_arrow_spec / build_corrected_pose_target / _draw_target_arrow) 존재 확인
- `test_fault_zoom_arrow.py` 29 passed / fault_zoom 계열 111 passed
- STATE.md / ROADMAP.md 미변경 (오케스트레이터 소유)
