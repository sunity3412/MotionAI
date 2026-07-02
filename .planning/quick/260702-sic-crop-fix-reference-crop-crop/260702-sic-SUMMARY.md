---
phase: quick-260702-sic
plan: 01
subsystem: fault-zoom (문제 부위 확대 비교)
tags: [fault-zoom, vision-veto, crop, region-grouping, confidence-fallback]
requires: [visionVeto.windowMedianAngleDeltas.sourceFrameIndices (Phase 24 D-10 HIGH-3 저장분)]
provides:
  - "fault_zoom 명시 프레임 override (측정 프레임 = 표시 프레임)"
  - "결함단위(region) grouping — 스플릿 좌+우 4관절 = 카드 1장 '양다리'"
  - "keypoint 저신뢰(<0.5)/결측 측 전신 contain-fit 폴백"
affects: [result 화면 확대비교 carousel]
tech-stack:
  added: []
  patterns: ["_CropUnit grouping (순수 helper)", "confidence 게이트 + 전신 폴백"]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/tests/test_fault_zoom.py
    - backend/functions/pipeline/app.py
    - app/src/types/analysis.ts
    - app/src/lib/deductionLabels.ts
    - app/src/components/FaultZoomCompare.tsx
decisions:
  - "grouping 은 kind 전원 동일한 non-None 값일 때만 (아래 Deviation 1)"
  - "override 는 vv.faultJoints 경로에만 — 편차 top-2 폴백은 기존 worst_seconds 유지"
metrics:
  duration: "~25min"
  completed: "2026-07-02"
---

# Quick 260702-sic: fault-zoom crop 정합 fix (reference crop / grouping / 폴백) Summary

**One-liner:** 확대비교 crop 프레임을 vision 측정 프레임(sourceFrameIndices median)과 일치시키고, 스플릿 좌+우 4관절을 "양다리" 카드 1장으로 묶고, 저신뢰 keypoint 측은 엉뚱한 부위 확대 대신 전신을 보여준다 — 점수/분석 로직 0라인 무접촉.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | fault_zoom.py 코어 재작업 (override + grouping + bbox crop + 폴백 + 테스트) | 9feeaf1 | fault_zoom.py, test_fault_zoom.py |
| 2 | pipeline 배선 + TS 계약/캡션 | 026c0e5 | pipeline/app.py, analysis.ts, deductionLabels.ts, FaultZoomCompare.tsx |

## What Changed

**Backend (fault_zoom.py):**
- `build_fault_zoom_comparisons` 에 keyword-only `user_frame_idx`/`ref_frame_idx` (9fps frames 인덱스 공간) — 주어지면 worst_seconds/DTW 선택을 대체. 둘 다 None(default) = 기존 경로 100% 보존 (기존 테스트 6개 무수정 PASS).
- `_group_fault_joints`: 같은 region(`_REGION_JOINTS` legs/arms) 좌+우 kind-동일 fault joints → `_CropUnit` 1개 (대표 joint = fault_joints 순서 첫 멤버, deficit = 멤버 max, scalar `region` 방출). kip-up 스플릿 {hips+knees, 전원 'deficit'} → legs 1장.
- `_KP_CONF_MIN = 0.5` confidence 게이트 (프론트 `KEYPOINT_LOW_CONFIDENCE_THRESHOLD=0.5` 선례 정합). valid 0개 측 = `_full_frame_fit` 전신 폴백 (중앙 원 마커 생략 — 오인 방지, deficit 배지 유지). 양측 다 무효만 skip.
- grouped crop = 멤버 bbox 기반 (변 = max(bbox)*1.8, floor = 기존 `_CROP_FRAC` 줌, 상한 = 프레임) — 촬영거리 불일치는 bbox 가 측별 스케일을 따라가며 자연 해소.

**Backend (pipeline/app.py — `_render_fault_zoom` / `_attach_fault_zoom_comparisons` 만):**
- `vv.windowMedianAngleDeltas.sourceFrameIndices` 의 user/reference 각-측 median 을 crop 프레임 override 로 전달. `vv.faultJoints` 경로에만 적용 — 편차 top-2 폴백/legacy doc(부재) 은 None = 기존 worst_seconds+DTW 경로 (하위호환).
- item 에 scalar `region` 방출 (`_validate_dict_only_scalars` flat 제약 통과, list 필드 0).
- `_attach_mode3_fault_zoom` 무변경 (default None → 기존 경로, mode3 improved/worsened 혼재 시 grouping 자동 비활성).

**Frontend:**
- `FaultZoomComparison.region?: 'legs' | 'arms' | null` (옵션 — normalize 변경 불요, legacy doc 호환).
- `REGION_LABEL_KO = { legs: '양다리', arms: '양팔' }` (deductionLabels.ts 단일 출처).
- `FaultZoomCompare.caption()`: region 라벨 우선 → "양다리 · 기준보다 30° 부족해요".

## Verification (gates)

- `backend pytest tests/test_fault_zoom.py`: **15 passed** (기존 6 무수정 + 신규 9: override 2 / grouping 3 / 저신뢰 폴백 3 / `_group_fault_joints` 직접 1)
- `app npm run typecheck`: **clean**
- `git diff` 스코프: fault_zoom.py + pipeline `_render_fault_zoom`/`_attach_fault_zoom_comparisons` hunk 만 + 프론트 3파일. deduction/veto/kismam/dimensions 등 채점 모듈 0라인.

## Deviations from Plan

### 1. [Rule 1 - Bug] grouping 조건에서 "전원 kind 없음" 절 제외

- **Found during:** Task 1
- **Issue:** 플랜의 grouping 조건 "(또는 전원 kind 없음)" 은 플랜 자체의 하드 게이트 "기존 테스트 6개 무수정 PASS 필수" 와 모순 — `joint_kinds=None` 인 기존 테스트 1·3 (left+right knee) 이 grouping 돼 카드 수 assert 가 깨짐.
- **Fix:** grouping 은 **전원 동일한 non-None kind** 일 때만. Production 은 항상 kind 를 세팅 (Mode1='deficit' 전원 / Mode3=improved/worsened) 하므로 kip-up fix 목표에 영향 0 — "전원 부재" 절은 production 에서 도달 불가 dead clause 였음. legacy(무 kind) 호출은 기존 관절당 1장 동작 보존.
- **Files modified:** fault_zoom.py (`_group_fault_joints`), test_fault_zoom.py (`test_group_fault_joints_pure_helper` 에 무 kind → 비grouping 검증 포함)
- **Commit:** 9feeaf1

### 2. [Minor] `_REGION_JOINTS` 에 실 keypoint 이름공간 반영

- 플랜 문구는 "hip·knee·ankle / shoulder·elbow·wrist 6개" 였으나 실제 `KeypointName` enum 은 8개 (ankle/elbow/wrist 없음, wrist 는 `left_hand`/`right_hand` 매핑). legs 에 ankle, arms 에 elbow/wrist + **hand** 를 함께 등재 — 현 이름공간에서 arms grouping 이 실제로 동작하고 향후 확장 이름도 커버. 주석에 출처 박제.

## Known Stubs

None — 데이터 배선 완결. region 부재 doc(legacy)은 기존 관절 캡션으로 자연 폴백.

## belle 실기기 체크리스트 (pod 재분석 필요 — 저장된 PNG 는 재생성 안 됨)

1. **kip-up fault 영상 Mode1 재분석** → 확대비교 확인:
   - (a) 스플릿 결함 = "양다리" 카드 1장 (dot 4개 → 1~2개)
   - (b) 좌/우 crop 이 같은 측정 모먼트 (user 프레임 ~20 / ref 프레임 ~37, 9fps)의 다리 부위, keypoint 저신뢰 측은 전신 표시
   - (c) 캡션 "양다리 · 기준보다 30° 부족해요"
2. **정은지 success 영상 1개 재분석** → 확대비교 섹션 회귀 없음 (veto 미발동이면 편차 top-2 경로 = 기존 worst_seconds 프레임)
3. **기존 분석(af8fb8c8...) 결과 화면 재진입** → crash 없음 (region·windowMedianAngleDeltas 부재 호환)

## Self-Check: PASSED

- [x] backend/shared/python/sunity_shared/analysis/fault_zoom.py — FOUND (region/override/폴백 포함)
- [x] backend/tests/test_fault_zoom.py — FOUND (15 passed)
- [x] backend/functions/pipeline/app.py — FOUND (sourceFrameIndices 배선)
- [x] app/src/types/analysis.ts — FOUND (region 필드)
- [x] app/src/lib/deductionLabels.ts — FOUND (REGION_LABEL_KO)
- [x] app/src/components/FaultZoomCompare.tsx — FOUND (region 캡션)
- [x] commit 9feeaf1 — FOUND
- [x] commit 026c0e5 — FOUND
