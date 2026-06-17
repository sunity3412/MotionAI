---
phase: 15-mode-1-mode-3-testflight
plan: 04
subsystem: testing
tags: [mode3, mode-self, e2e, runpod, gpu, rtmw, deltaFromPrevious, falsepositive, score-04, dual-coach, gemini, cerebras, firestore, phase15]

# Dependency graph
requires:
  - phase: 08.1-axis-metric-redesign
    provides: tilt_thresholds.yaml frozen baseline (sha256 c94bb8…e87c) + 정은지 25/25 'low' (reference-motion) invariant
  - phase: 15-mode-1-mode-3-testflight (15-01)
    provides: sweep_phase15.py (--pair-sequential, direct-process, per-run uid, createdAt) + assert_falsepositive_gate.py + phase15_keys.json
  - phase: 15-mode-1-mode-3-testflight (15-02)
    provides: Pod 01emvodj1pdooe live + RUNPOD_ANALYZE_URL sync
provides:
  - "Mode 3 (MODE_SELF) 6 fail->success 페어 실 Pod GPU E2E — per-run 격리, 6/6 previousAnalysisId==paired fault, deltaFromPrevious 차원 점수(stability) 델타 non-empty"
  - "SCORE-04 (단독): frozen 08.1 checksum gate PASS(c94bb8) + fallback==0 12/12; SC3 41점-스타일 위양성 부재(최저 overall 55=실 결손)"
  - "all-low success-severity gate = 기준-모션 invariant → 학생-연습 success 미전이 → Phase 18 defer (재calibrate 0, D-02)"
  - "듀얼 coach 12/12 doc dualTrack=True + nonCrossFilledGemini 6(실 LLM) + 빈 cause 섹션 0 (D-12)"
  - "Mode 3 6-페어 status 카운트 (total12/done12/server_error0) — 15-05 SC4 집계 입력 PROVIDE-only"
  - "15-MODE3-DUALCOACH-EVIDENCE.md"
affects: [15-05, phase-18-fault-eval-set]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mode 3 페어 = first(fault, abs_dims only)/second(success, angle+abs_dims) — deltaFromPrevious 는 abs_dims(절대) 척도만 (build_mode3 line 1628)"
    - "위양성 gate 입력-클래스 명료화 — 08.1 all-low invariant = reference-motion 속성, student-practice success 는 별도 클래스 → Phase 18 defer (재calibrate 아님)"
    - "evidence = 실 Firestore doc read-back (geminiB.sectionAudit authoritative 섹션 출처) — dry-run 단독 불충분"

key-files:
  created:
    - .planning/phases/15-mode-1-mode-3-testflight/15-MODE3-DUALCOACH-EVIDENCE.md
  modified:
    - .planning/phases/15-mode-1-mode-3-testflight/deferred-items.md

key-decisions:
  - "deltaFromPrevious 는 차원 점수(stability) cur-prev 절대 척도 델타 — 6/6 페어 previousAnalysisId==paired fault, mode3Summary 'N점 발전' 형태(%일치 아님)"
  - "fault doc=first(dimensionScores={stability}, line=None recognizer 폴백) / success doc=second(angle 일관성 + abs_dims) → overall 척도 차이는 구조적(회귀 아님), delta 는 abs_dims 만으로 정합"
  - "all-low success severity FAIL 4/6 은 진짜 위양성 아님 — 학생-연습 success 의 실 tilt(pdshape 90°, power-spin 80-88°)가 08.1 reference-motion cutoff 초과한 정상 검출. SC3 위양성=overall 41점-스타일은 부재(최저 55)"
  - "success-severity 자동 gating + fail per-fault gating 둘 다 Phase 18(labeled eval set)로 defer. threshold 재calibrate 0 (D-02). 사람 점수 라벨 금지(D-06)"
  - "듀얼 coach best case(crossFilledJoints=[] 12/12) — 양쪽 LLM 발화, 빈 섹션 0. cross-fill 폴백 자체는 phase13 7/7 회귀 + 15-03 run 이 보강"

patterns-established:
  - "Pattern: Mode 3 evidence = 실 Firestore comparison.previousAnalysisId/deltaFromPrevious + dimensionScores (HIGH 2 per-run uid/analysisId/createdAt)"
  - "Pattern: 위양성 gate 입력-클래스 분리 — reference-motion(all-low) vs student-practice success(실 tilt 정상 검출), 후자 자동 gating Phase 18"
  - "Pattern: dual-coach 실 LLM 증거 = geminiB.sectionAudit nonCrossFilledGemini>0 (heuristic-only 차단)"

requirements-completed: [MODE-02, SCORE-04]

# Metrics
duration: ~75min
completed: 2026-06-17
---

# Phase 15 Plan 04: Mode 3 (MODE_SELF) deltaFromPrevious + 위양성 게이트(SCORE-04) + 듀얼 coach Summary

**정은지 6 fail→success 페어를 MODE_SELF per-run 격리로 실 Pod GPU E2E 돌려 6/6 previousAnalysisId==paired fault 페어링 + deltaFromPrevious 차원 점수(stability) 델타를 산출하고, frozen 08.1 checksum gate(c94bb8)+fallback==0 위에서 SC3 41점-스타일 위양성 부재(최저 overall 55=실 결손)를 객관 확인했으며, all-low success-severity gate 는 reference-motion invariant 라 학생-연습 success 에 미전이함을 raw tilt 로 입증해 Phase 18 로 defer(재calibrate 0)하고, 듀얼 coach 12/12 doc 실 LLM 발화 + 빈 섹션 0(D-12)을 박았다.**

## Performance

- **Duration:** ~75 min
- **Started:** 2026-06-17T10:05Z
- **Completed:** 2026-06-17T11:20Z
- **Tasks:** 3 auto tasks (운영/evidence, repo 코드 변경 0)
- **Files modified:** 1 created (evidence) + 1 modified (deferred-items.md)

## Accomplishments
- **Task 1 (MODE-02):** Mode 3 6 fail→success 페어 실 Pod GPU E2E (`sweep_phase15.py --mode mode3 --trigger direct-process --pair-sequential`, runId 1781690825384). invariant 자체검증 PASS(uploads-copy=0 _process=12 /analyze=0). 6/6 success `comparison.previousAnalysisId == paired fault analysisId`, `deltaFromPrevious` non-empty 차원 점수(stability) 델타 (climb+5/elbow+6/power-spin+6/kip-up−1/peter-pan0/pdshape−28, 부호 발전 방향 정합). mode3Summary 'N점 발전' 형태(%일치 아님). 관절 각도 델타 미검증(D-13 Deferred).
- **Task 2 (SCORE-04 단독 소유):** frozen checksum hard gate PASS (sha256 c94bb8, 12/12) + `tilt_thresholds_fallback==0` 12/12. SC3 41점-스타일 위양성 부재 — success overall 68/64/91/55/85/78, 최저 55(pdshape)는 실 stability 결손(transition sh/hip 90° 극단 실 tilt) 반영. all-low success severity gate 는 2/6 PASS / 4/6 FAIL 이나, FAIL 4 는 학생-연습 success 의 실 tilt 가 08.1 reference-motion cutoff 초과한 정상 검출(위양성 아님) → success-severity + fail per-fault 자동 gating 둘 다 Phase 18 defer (재calibrate 0).
- **Task 3 (D-12):** 듀얼 coach 12/12 doc `dualTrack=True`, `nonCrossFilledGeminiSections=6`(실 Gemini 발화, heuristic-only 아님), `crossFilledJoints=[]`(best case 양쪽 ok), `emptyCauseSections=0` + coachDetails 4 섹션 전부 채워짐. 벤더명 비노출 유지.
- **§Mode3status PROVIDE:** Mode 3 6-페어 total12/done12/no_human0/not_pole_motion0/server_error0 — 15-05 SC4 집계 입력 (13/13 통합은 15-05 단독 소유).

## Task Commits

각 태스크는 repo 코드 변경 없는 운영/evidence 작업이라 단일 evidence-doc commit 으로 atomically 기록 (15-03 패턴 정합):

1. **Task 1 + Task 2 + Task 3 (Mode 3 E2E + 위양성 gate + 듀얼 coach evidence)** - `39a63e2` (docs)

_sweep_phase15.py / assert_falsepositive_gate.py 는 15-01 산출물 그대로 사용(코드 변경 0). 모든 작업 = Pod SSH sweep + 실 Firestore read-back + assert 실행._

## Files Created/Modified
- `.planning/phases/15-mode-1-mode-3-testflight/15-MODE3-DUALCOACH-EVIDENCE.md` - §델타(6 페어 previousAnalysisId 매칭 + deltaFromPrevious 차원 점수 델타 + 부호) + §위양성assert(per-video severity/overall + checksum/fallback + all-low gate 다운그레이드 객관 근거 + raw tilt 부록) + §듀얼coach(12/12 dualTrack + nonCrossFilledGemini + 빈 섹션 0) + §Mode3status(15-05 입력) + 식별자 기록
- `.planning/phases/15-mode-1-mode-3-testflight/deferred-items.md` - cross-test pollution(broad -k) + SCORE-04 all-low success-severity gate scope(Phase 18 defer) 로깅

## Decisions Made
- **deltaFromPrevious = 절대 차원(stability) 척도:** build_mode3(assemble.py:1628)이 `cur_dimension_scores=abs_dims` 로 산출 — fault doc 의 공통 차원이 stability 뿐이라 델타도 stability. 절대 척도라 세션 간 진짜 발전 신호(mode3-progress-not-similarity). 관절 각도 델타는 현 계약 외(D-13 Deferred).
- **overall vs delta 척도 분리(구조적, 회귀 아님):** success overall(angle 일관성 dim 포함)이 fault overall(stability-only)보다 낮은 것은 각 doc 의 dimension 구성 차이 — belle 2026-06-06 박제(overall=모든 차원 평균, delta=abs_dims만). recognizer line=None(15-03 finding 동일 폴백)로 fault 가 stability-only.
- **all-low success gate 다운그레이드(핵심):** 08.1 25/25-low 는 정은지 *기준 모션* 클립(ref-*, tilt 10-52°) 속성. Phase 15 success 는 *학생 연습* success(correct.mp4)로 실 tilt 가 cutoff(sh63.28/hip54.62°) 초과(pdshape 90°, power-spin 80-88°) → medium/high 는 정상 검출이지 41점-스타일 위양성 아님. 자동 success-severity gating 은 입력-클래스 라벨 필요 → Phase 18 defer. plan Task 2 MEDIUM 6 가 사전 승인한 manual-review/Phase18-defer 경로. threshold 재calibrate 0(D-02).
- **objectivity(D-06):** fail per-fault 는 manual evidence review(REVIEW 6/6), 사람 점수 라벨 ground truth 미사용. SC3 위양성 판정은 overall 점수(객관 numeric) 기준.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - 블로킹 환경 fix] sweep runner env 누락(RTMW_ONNX_PATH/YOLOX_ONNX_PATH) → full-environ source**
- **Found during:** Task 1 (1차 sweep 실행)
- **Issue:** sweep runner 가 좁은 화이트리스트로 env 를 source 해 `RTMW_ONNX_PATH`/`YOLOX_ONNX_PATH`/`RTMW_DEVICE`/`FIREBASE_SA_PATH` 누락 → `RTMWPoseEngine().__init__` `RuntimeError: RTMW_ONNX_PATH 미설정` → `_load_pipeline()` 크래시(per-item 루프 진입 전이라 Firestore doc write 0).
- **Fix:** runner 가 live uvicorn proc(`/proc/<pid>/environ`)의 **전체 키**를 NUL-delimited 로 export(키 값 비노출). onnxruntime providers = CUDA 확인 후 재실행. (15-03 의 full-env source 패턴 정합.)
- **Files modified:** Pod-side 실행 runner 만 (repo 변경 0).
- **Verification:** `ort providers: [Tensorrt, CUDA, CPU]`, RTMW/YOLOX onnx 로드 OK, 12/12 _process OK.
- **Committed in:** `39a63e2` (evidence 문서에 기록)

---

**Total deviations:** 1 auto-fixed (1 블로킹 환경/GPU)
**Impact on plan:** full-environ source 는 GPU 분석 구동에 필수. scope creep 0. 임의 numeric/threshold fit 0(D-02 정합).

## Issues Encountered
- **all-low success-severity gate 4/6 FAIL (입력-클래스 mismatch):** 진짜 위양성 아님 — raw tilt 로 입증(학생-연습 success 의 실 tilt 가 reference-motion cutoff 초과). plan 의 manual-review/Phase18-defer 경로로 해소, 재calibrate 0. 상세 = §위양성assert MEDIUM 6 + deferred-items.md.
- **pytest cross-test pollution(broad -k 3 FAIL):** repo 코드 변경 0 이므로 회귀 아님 — 격리/쌍 실행 시 PASS(phase8+phase9 16/16). deferred-items.md 로깅, 미수정(scope boundary).
- **dual-track 로그 미캡처:** 파이프라인 logger 가 sweep stdout 에 INFO 미전달(uvicorn 만 설정) → 더 강한 증거인 실 Firestore `geminiB.sectionAudit`(authoritative 섹션 출처)로 대체 — nonCrossFilledGemini>0 로 실 LLM 발화 입증.
- **SSM/secret 비노출:** Firebase/Gemini/Cerebras 키는 uvicorn proc env 재사용(값 한 번도 출력/commit 0).

## User Setup Required
None — 모든 SSH/sweep/Firestore read-back/assert 는 Claude 가 sunity-motion + Firebase SA 자격으로 자동 실행(pod-ops-claude-runs).

## Next Phase Readiness
- **15-05 (DELIV-01 + 13/13 SC4):** Mode 3 6-페어 status(total12/done12/server_error0)를 §Mode3status 로 PROVIDE 완료 → 15-05 가 15-03 Mode 1(7 done) + 15-04 Mode 3(12 doc) read-only 합산 가능. 13/13 통합 SC4 단독 소유 = 15-05.
- **Phase 18 (Expert deliberate-fault eval set):** success-severity 자동 gating(입력-클래스 라벨) + fail per-fault gating(labeled fault) 둘 다 Phase 18 의존 — labeled eval set 으로 객관 자동화. threshold 재calibrate 0 유지.
- Pod ephemeral — 재생성 시 RUNPOD_ANALYZE_URL/SSM 재동기화(15-02 절차 재사용).

## Self-Check: PASSED

- FOUND: `.planning/phases/15-mode-1-mode-3-testflight/15-MODE3-DUALCOACH-EVIDENCE.md`
- FOUND: commit `39a63e2` (evidence)
- 6/6 페어 previousAnalysisId==paired fault + deltaFromPrevious non-empty (실 Firestore, runId 1781690825384)
- checksum hard gate c94bb8 PASS + fallback==0 12/12 + 듀얼 coach 빈 섹션 0 12/12

---
*Phase: 15-mode-1-mode-3-testflight*
*Completed: 2026-06-17*
