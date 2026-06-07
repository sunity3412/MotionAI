# Phase 2 PLAN-CHECK

**Reviewer:** plan-checker (goal-backward verification, FORCE stance)
**Date:** 2026-06-07
**Plan reviewed:** `.planning/phases/02-bodynormalizationprofile-rtmw-segment/02-01-PLAN.md`

## Overall Verdict: **PASS_WITH_CONCERNS**

PLAN 은 ROADMAP 5 Success Criteria, BODY-01, 3-way lockstep, R&D 격리, contract enum, AST gate 를 모두 실제 task 로 매핑한다. 의존 chain (T1+T2 → T3 → T4+T5 → T6) 도 일관적이고 numpy-only 정합도 명시되어 있다. 다만 **PASS 가 아닌 PASS_WITH_CONCERNS** 인 이유는 두 가지 비차단성 정합 문제 — (1) Task 5 의 R&D harness 가 NLF/SMPL-X 를 실제로 호출하지 않는 stub 으로 박제되어 Success Criterion 4 ("실제 갭 보고서 출력") 의 v1 완수 여부가 belle Pod 별도 PR 에 위임됨, (2) Task 6 의 AST isolation 검사가 `sunity_shared/` 만 대상으로 정의되어 있어 `backend/functions/pipeline/app.py` 운영 path 의 NLF/SMPL-X import 는 검출되지 않는다.

두 항목 모두 의도된 v1 scope 한계 (CONTEXT.md §1 out-of-scope + Plan 01-24 책임) 와 정합하나, PLAN 실행 전에 명시적으로 박제할 가치가 있어 PASS_WITH_CONCERNS 로 표시한다.

---

## Rubric Table

| # | Item | Pass/Fail | Evidence |
|---|------|-----------|----------|
| 1 | All 5 ROADMAP Success Criteria mapped to ≥1 task | PASS | `<success_criteria>` 표 (PLAN line 454-462) 가 5/5 매핑. SC1→T3, SC2→T3, SC3→T3+T1, SC4→T5+T6, SC5→T1. |
| 2 | BODY-01 REQUIREMENTS rename (MediaPipe→RTMW) | PASS | Task 6 action (PLAN line 389-393) 가 `.planning/REQUIREMENTS.md` line 30 의 "MediaPipe"→"RTMW" 갱신 명시 + footer note 추가. |
| 3 | Contract 3-way lockstep is one atomic commit | PASS | Task 1 (PLAN line 105-138) `<commit-template>` 한 commit 에 `docs/contract.md`+`analysis.ts`+`body_normalization.py` 동시 변경 박제. `<verify>` 가 `test_body_normalization_lockstep.py` 로 자동 검증. |
| 4 | R&D isolation has automated test (AST), not just comment | PASS | Task 6 (PLAN line 372-388) 가 `ast.parse` 로 `sunity_shared/**/*.py` 스캔 + `from backend.research` / `nlf` / `smplx` / `mediapipe` import 검출 시 fail 박제. 단위 테스트 2개 (`test_sunity_shared_does_not_import_research`, `..._does_not_import_nlf_or_smplx`). |
| 5 | confidence + warnings always output (verified by test) | PASS | Task 3 action (PLAN line 218-219) NaN 폴백 + finite 강제 박제. `<done>` (PLAN line 244-248) 가 "5 fixture 에서 NaN/inf 출력 X" + "정상 fixture warnings==[] / 4 비정상 fixture 정확 warning" 자동 검증. |
| 6 | Each task = one atomic commit with concrete message | PASS | 6 task 모두 `<commit-template>` 박제 (PLAN line 135, 182, 250, 301, 353, 411). 평균 2-3 파일/commit. |
| 7 | No "todo"/"investigate" task — concrete paths + algorithm sketch | PASS | Task 3 (PLAN line 197-222) 가 `SEGMENT_PAIRS`, `_robust_median`, MAD k=3, warning 5종 판정 임계값까지 구체. Task 5 의 stub 도 `NotImplementedError` 박제 위치 명시. |
| 8 | Dependencies between tasks explicit (blocked by IDs) | PASS | 6 task 모두 `<depends-on>` 박제 (PLAN line 138, 185, 253, 304, 356, 414). Chain: T1+T2 (병렬) → T3 → T4+T5 (병렬) → T6. |
| 9 | Total task count 5-7 (not bloated, not under-scoped) | PASS | 6 task (PLAN line 538-549 요약 표). 적정 범위. |
| 10 | No new dependencies (numpy only) | PASS | Task 3 action (PLAN line 195) "numpy only (scipy 의존 0)". `<done>` (PLAN line 247) `grep "import scipy" → 0` 검증. RESEARCH.md "Don't Hand-Roll" 표 정합. |
| 11 | Test fixture strategy concrete (synthetic generation task) | PASS | Task 2 (PLAN line 141-185) 가 `seed=42 멱등 generator + 5 fixture JSON` 신설. RESEARCH A6 sweep dump 부재 사실을 명시적으로 박제 (PLAN line 152-153). |
| 12 | No task assumes nonexistent code | PASS | `_RTMWNlfCompat` (verified pipeline/app.py:202), `BodyNormalizationProfile` (verified body_normalization.py:30), `temporal.py` MAD 패턴, `test_body_normalization_lockstep.py`, `compare_engines.py` 모두 디스크 존재 확인. |
| 13 | No MediaPipe references in product code path | PASS | PLAN 의 모든 MediaPipe 언급은 REQUIREMENTS.md 갱신 (Task 6 — 제거 작업), AST 차단 (Task 6 — `mediapipe` import 차단), 또는 RESEARCH.md/CONTEXT.md 인용 (역사적 맥락). 운영 코드 신설 X. |
| 14 | No NLF/SMPL-X imports in `sunity_shared/*` product modules | PASS | Task 5 R&D harness 는 `backend/research/` 디렉터리에 격리 (PLAN line 310). Task 6 AST gate 가 `sunity_shared` → `nlf`/`smplx` import 0 자동 강제 (PLAN line 384). |
| 15 | No human score labeling (belle/instructor scores as ground truth) | PASS | Task 3 의 fixture 검증은 algorithmic threshold (conf > 0.7, scale ∈ [0.8, 1.4]) 만 사용 (PLAN line 224-228). 정은지 hold-frame 은 "객관 측정값" reference 로 RESEARCH.md 에서 언급되나 PLAN Task 2 에서는 synthetic-only 선택 → 사람 점수 라벨링 0. memory `[analysis-objectivity-no-human-scores]` 정합. |

**Score: 15/15 PASS** — 하지만 두 가지 비차단성 정합 우려가 있음 (아래 risks 참조).

---

## Specific Fixes Required if FAIL

해당 없음 (모든 rubric PASS). 실행 진입 가능.

---

## Risks Not Blocking But Worth Flagging

### R-1 — Success Criterion 4 의 v1 완수가 belle Pod 별 PR 에 위임 (PLAN line 325-331, 351)

- ROADMAP SC4: "R&D 비교군: NLF→SMPL-X β로 추출한 BodyNormalizationProfile 과의 갭을 보고서로 출력"
- PLAN Task 5 가 `load_nlf_smplx_keypoints` 를 `NotImplementedError("belle pod 에서 NLF mock 실데이터로 교체")` stub 으로 박제 — 본 PR 에서 실 보고서 산출 0.
- 정당화: RESEARCH.md "R&D 비교 Harness" 가 belle 사내 Pod 실행을 가정 (D-23 + license-blocklist-pose memory) + CONTEXT.md "v1 scope = 측정기 본체" 정신.
- 권장: PLAN 실행 후 SUMMARY.md 에 "SC4 v1 = harness + smoke 박제만, 실 갭 보고서는 별도 PR (belle Pod task)" 명시. 외부에서 보면 SC4 가 부분 완수.

### R-2 — AST isolation 검사 scope 가 `sunity_shared/` 만 (PLAN line 386)

- Task 6 가 "운영 path 만 검증 — `backend/tests/` / `backend/research/` / `backend/functions/` 는 검증 대상 X" 박제.
- 문제: `backend/functions/pipeline/app.py` 는 실제 운영 Lambda path 임 (RTMW 운영 entry). 만약 향후 누군가 pipeline 에 NLF import 추가 시 본 plan 의 AST 검사가 못 잡음.
- 정당화: Plan 01-24 (NLF + MediaPipe + 비선택 3D path R&D 격리, `.samignore` + import 차단) 가 정확히 이 범위를 책임. 본 phase 가 Plan 01-24 책임을 침범하지 않는 게 정합.
- 권장: Task 6 검증 scope 의견을 `<action>` 끝에 한 줄 명시 — "Plan 01-24 가 `backend/functions/` import 차단 책임. 본 task 는 `sunity_shared/` 만." 현재 PLAN line 386 에 이미 박혀 있어 단순 noted.

### R-3 — fixture seed=42 synthetic 만으로 RTMW 실측 분포 근사 정확도 미검증 (PLAN line 165, A6 정합)

- Task 2 가 synthetic-only fixture (Phase 1 sweep dump 부재 사실 확인 후). RESEARCH.md A6 가 v1.5 에서 실 영상 fixture 1종 재추출 권장.
- v1 PASS gate (5 fixture warning 발화 검증) 는 synthetic 만으로 충족되나, Phase 6 통합 시점 실 영상에서 측정기가 실제로 정확히 동작할지 검증되지 않음.
- 권장: Task 2 `_generate.py` TODO 주석 (PLAN line 165) 이 v1.5 plan 작성 시 자동 trigger 되도록 STATE.md 또는 별도 backlog 박제 권장.

### R-4 — `estimatedHeightScale` v1 의미가 [ASSUMED] (PLAN line 210, A2)

- 공식 `(arm_scale + leg_scale + 1.0) / 3` 가 placeholder. Phase 6 통합 시점 belle 검토 대상.
- 영향: Phase 6 가 본 필드를 실 의미로 사용 시 재정의 필요할 수 있음 — 본 phase 의 BodyNormalizationProfile 산출값과 Phase 6 가 기대하는 형태가 갭이 날 가능성.
- 정당화: RESEARCH.md A2 + CONTEXT.md "v1 estimatedHeightScale 의미 = 체형 비율 균형 지표" 박제.
- 권장: Task 3 docstring 에 "v1 placeholder, Phase 6 검토 대상" 명시 (PLAN line 210 의 노트가 docstring 으로 따라가는지 확인 필요).

### R-5 — `pose_too_inverted` 임계값 50% 가 [ASSUMED] (PLAN line 217, A3)

- 정상 자세 vs 인버트 자세의 frame 비율 cutoff 가 belle 실 sweep 검토 전 결정.
- 영향: 정은지 영상 ref-invert-butterfly-combo 같은 인버트 reference 에서 warning 이 잘못 발화될 수 있음.
- 권장: Phase 5 또는 Phase 6 통합 시점 belle 실측 데이터로 재튜닝. Task 3 fixture 가 synthetic 이라 실측 검증은 belle Pod 가서 별도 확인 필요.

---

## Sources Verified Against Disk

- `backend/functions/pipeline/app.py:202` `_RTMWNlfCompat` 존재 확인 (PLAN line 259 통합 지점 valid)
- `backend/shared/python/sunity_shared/analysis/body_normalization.py:30` BodyNormalizationProfile 박제 확인 (현 docstring 이 "Phase 2 측정기가 채움" 박제 — PLAN Task 1 의 docstring 갱신 대상 정합)
- `docs/contract.md:342` 의 `warnings` 행이 "`short_arm_clip`, `occluded_torso`" placeholder 박제 확인 (Task 1 의 교체 대상 정확)
- `app/src/types/analysis.ts:386` 의 `warnings` 주석이 동일 placeholder 박제 확인
- `backend/tests/test_body_normalization_lockstep.py` 박제 확인 (Task 1 의 자동 drift 차단 valid)
- `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/` 디렉터리에 `report.json` + `report.md` 만 존재, `.npz`/keypoint dump 부재 확인 — PLAN line 153 의 RESEARCH.md A6 risk 명시가 실제 상황과 정합

---

## Decision

PLAN 은 `gsd-execute-phase 02` 실행 가능. 5 ROADMAP Success Criteria + BODY-01 + D-02-01~06 모두 task 매핑 완료. 의존 chain 일관, atomic commit 6개 적정, scope 정합.

R-1, R-2 두 정합 risk 는 모두 의도된 v1 scope 한계로 CONTEXT.md / Plan 01-24 정합. 실행 후 SUMMARY.md 에서 SC4 의 v1 부분 완수를 명시적으로 박제하면 충분.

**다음 단계:** `/gsd-execute-phase 02`
