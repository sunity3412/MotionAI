---
phase: 19
slug: vision-hybrid
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-18
revised: 2026-06-18 (reviews iter-4 — HIGH-1[Mode1 scoringBasis 직렬화 계약화]/HIGH-2[reference_motion enum-value 체크]/MEDIUM-1[smoke process.exitCode]; iter-3 HIGH-1/2 MEDIUM-1/2 유지; iter-2 BLOCKER-1/2, HIGH-1~4, MEDIUM-1/2/3 유지)
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 19-RESEARCH.md "## Validation Architecture" + 19-REVIEWS.md (iter-1 11 + iter-2 9 + iter-3 4 + iter-4 3 findings).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| **Config file** | `backend/tests/conftest.py` (pytest.ini 없음 — conftest + sys.path 패턴) |
| **Quick run command** | `cd backend && python -m pytest tests/test_kismam.py tests/test_dimensions.py -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q` |
| **App static gate** | `cd app && npm run typecheck` (tsc --noEmit — 유일한 정적 게이트, simulatedResult.ts 포함) |
| **App 3D smoke** | `node app/scripts/_smoke_joints_normalize.mjs` (LOCAL tsc 컴파일 + createRequire 로 production normalizeFrames import — maxAbsCoord<=3 + frame 수 보존, no-copy, thrown error + process.exitCode + finally cleanup) |
| **D-05 anchor gate** | `RUN_PHASE19_ANCHORS=1 pytest tests/test_anchor_known_answer.py -q` (실영상 6 페어 per-test @requires_anchor_env; synthetic above-cutoff 는 env 무관 항상 실행) |
| **Estimated runtime** | ~30–60 seconds (backend unit) |

---

## Sampling Rate

- **After every task commit:** `cd backend && python -m pytest tests/test_kismam.py tests/test_dimensions.py -x` (+ `cd app && npm run typecheck` + smoke for 앱 task)
- **After every plan wave:** `cd backend && python -m pytest tests/ -q` (full backend suite, pre-existing 실패는 isolation 제외)
- **Before `/gsd-verify-work`:** Full suite green + (Pod 재개 시) `RUN_PHASE19_ANCHORS=1` D-05 앵커 방향검증
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| SCORE-06 | 단일 major fault가 종합 지배 (한 관절 큰 편차 → 종합 급락 <70, 평균 희석 X) | unit | `pytest tests/test_kismam.py::test_single_major_fault_dominates -x` | ❌ W0 |
| SCORE-06 | above-cutoff: 모든 관절 편차<tol → 종합 high (위양성 없음) | unit | `pytest tests/test_kismam.py::test_clean_pose_high_score -x` | ❌ W0 |
| SCORE-06 | within-tolerance 잔류 high + 0/30/60° 단조성 (dead-zone 인지) | unit | `pytest tests/test_kismam.py::test_within_tolerance_remains_high tests/test_kismam.py::test_score_monotonic_decreasing_with_deviation -x` | ⚠ W0 갱신 |
| SCORE-07 | 신전요구 관절 160° 미달 → line 차원 0점(요소 무효) | unit | `pytest tests/test_dimensions.py::test_micro_bent_zero_track -x` | ❌ W0 |
| SCORE-07 | 의도적 굽힘(expects_extension False) → 0점 트랙 미적용 | unit | `pytest tests/test_dimensions.py::test_intentional_bend_not_penalized -x` | ❌ W0 |
| SCORE-07 | core(angle/line) min, stability 비기여, no-core fallback | unit | `pytest tests/test_dimensions.py::test_overall_from_dimensions_uses_core_dimensions -x` | ⚠ W0 갱신 |
| TRUST-01 | 표시 각도 = 점수 source(DTW path-정렬 양측 median), user/ref 동일 구간 | unit | `pytest tests/test_pipeline_mode3.py::test_display_matches_score_source -x` | ✅파일 ❌케이스 |
| TRUST-02 | DIM_STABILITY 높아도 angle/line 낮으면 종합 낮음 (stability 인플레 X) | unit | `pytest tests/test_dimensions.py::test_stability_does_not_inflate -x` | ❌ W0 |
| TRUST-02 | 어깨 COACHING_FOCUS 라벨 'STATIC POSE' 의미로 정정 | unit | `pytest tests/test_kismam.py::test_shoulder_focus_label -x` | ❌ W0 |
| TRUST-02 | stability 비기여 = contributesToOverall=false(OPTIONAL) / weightPercent=0 + simulatedResult 정합 | unit + static(앱) | `pytest tests/test_dimensions.py::test_stability_does_not_inflate -x` (build_dimension_explanation 출력 단언) + `cd app && npm run typecheck` | ❌ W0 |
| TRUST-03 | Mode1(MODE_EXPERT) → build_mode1 직렬화 Mode1Comparison.scoringBasis="reference_motion" (Mode1 전용 OPTIONAL 계약 필드, Mode3 게이트와 분리; ITER-4 HIGH-1) | unit | `pytest tests/test_pipeline_mode3.py::test_mode1_scoring_basis_reference_motion -x` | ❌ W0 |
| TRUST-03 | MODE_SELF 미보유 = is_reference_free_motion → scoringBasis="reference_free_absolute" + label + 절대트랙(line+stability) (copyBranch 단독 분기 금지) | unit | `pytest tests/test_pipeline_mode3.py::test_unknown_move_gate -x` | ✅파일 ❌케이스 |
| TRUST-03 | scoringBasis = 실제 채점 source, **Mode3 = 4-value (reference_motion 미등장 invariant)**, composite=previous_analysis_plus_reference_free_absolute | unit | `pytest tests/test_pipeline_mode3.py::test_unknown_move_gate -x` (Mode3 4-value parametrize + reference_motion 미등장) | ✅파일 ❌케이스 |
| TRUST-03 | build_mode3(is_first=True, basis 미전달) == {"mode":"mode3","isFirst":True} EXACT + build_mode3(scoring_basis="reference_motion") → ValueError | unit | `pytest tests/test_pipeline_mode3.py::test_build_mode3_backward_compat -x` | ❌ W0 |
| TRUST-03 | scoringBasisLabel 이 result 화면 + DimensionDetailModal 에 표시 + contributesToOverall=false 보조지표 카피 (백엔드 only 아님) | static(앱) | `cd app && npm run typecheck` (JS 러너 부재 — 수동 육안 보조) | ⚠ 러너 없음 |
| TRUST-04 | reshapePose3dData → normalizeFrames(single source) COCO-17 indexOf recenter + torso/bbox, raw passthrough 0, frame 수 보존 | smoke | `node app/scripts/_smoke_joints_normalize.mjs` (LOCAL tsc 컴파일 + createRequire production import, maxAbsCoord<=3, frame 수 == 입력, no-copy, process.exitCode + finally cleanup) | ❌ W0/W1B |
| TRUST-05 | v1 vision hook = SAME-object identity pass-through (out is score_result, mutation 0) | unit | `pytest tests/test_pipeline_mode3.py::test_vision_hook_passthrough -x` | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ 갱신/러너없음*

---

## Contract Lockstep (3중 계약 — scoringBasis)

| 필드 | TS (analysis.ts) | Python (assemble.py / models.py) | Docs (contract.md) | 검증 방식 |
|------|-------------------|----------------------------------|--------------------|-----------|
| Mode1Comparison.scoringBasis | `scoringBasis?: 'reference_motion'` + `scoringBasisLabel?` (OPTIONAL) | build_mode1 이 항상 emit `"reference_motion"` + label; models.py Mode1 상수/주석 | Mode1Comparison 정의에 `scoringBasis? 'reference_motion'` + "Mode1 전용" | ENUM/VALUE — Mode1Comparison.scoringBasis 유일 리터럴 = 'reference_motion' (ITER-4 HIGH-1) |
| Mode3Comparison.scoringBasis | union 정확히 4 Mode3 리터럴, reference_motion ∉ union | `_MODE3_SCORING_BASES` frozenset = 4 값; build_mode3 enum 가드 (reference_motion → ValueError) | Mode3 테이블 = 4 값, reference_motion row/value 없음, "5-enum" 표기 0 | ENUM/VALUE — union 멤버 4개 + reference_motion ∉ Mode3; `_MODE3_SCORING_BASES == {4}`; Mode3 테이블 4 값 (ITER-4 HIGH-2 — raw prose grep 0 금지, 설명 주석의 reference_motion 언급은 허용) |

> **ITER-4 HIGH-2:** "reference_motion 은 Mode1 전용" 같은 설명 주석/문서가 그 리터럴을 포함하므로, Mode3 섹션의 raw `reference_motion` grep-zero 는 자기모순(false fail). 검증은 ENUM/VALUE(union 멤버십 / frozenset 동등 / 테이블 row 부재)로만 한다. 설명 prose 의 reference_motion 언급은 허용.

---

## Known-Answer Anchor Validation (D-05 — per-test @requires_anchor_env)

| Anchor | Expected (방향, curve-fit 아님) | Test | Gate |
|--------|-------------------------------|------|------|
| climb (등 말림 line ~25°) | line 차원 지배 → 종합 낮음. fault < correct | `test_anchor_fault_lower_than_correct` parametrize | @requires_anchor_env (실영상/GPU) |
| kip-up (무릎 ~35° angle) | angle 차원 지배 → 종합 낮음 | 동일 parametrize | @requires_anchor_env |
| 6/6 fault 페어 | 모두 종합 낮음 (94 같은 위양성 0건) | 6 페어 parametrize | @requires_anchor_env |
| above-cutoff (미보유 고득점) | 정상 동작 high 유지 (sensitivity gate) | `test_above_cutoff_synthetic_stays_high` | **마커 없음 — 항상 실행** (synthetic angles, GPU 불필요) |

> 실영상 6 페어 활성: `RUN_PHASE19_ANCHORS=1 pytest tests/test_anchor_known_answer.py -q` (+ S3/GPU). env 부재 시 실영상 6 페어만 skip.
> **module-level `pytestmark` 금지** (ITER-2 HIGH-1) — synthetic above-cutoff 는 env 무관 항상 실행 (sensitivity gate 보존).
> 앵커는 **방향 판정**(fault<정상 + major 차원 지배)이지 점수 수치 타깃 아님
> ([[calibration-source-hard-gate]] [[scoring-redesign-must-generalize-no-overfit]]).
> skip 본문에 real fixture key + 페어별 dominant-dimension 메타 상수 보존 (활성화 mechanical).

---

## Wave 0 Requirements

- [ ] `backend/tests/test_kismam.py` — 신규 SCORE-06(single_major_fault_dominates, clean_pose_high_score, within_tolerance_remains_high) + TRUST-02(shoulder_focus_label) + **갱신** test_score_monotonic_decreasing_with_deviation(0/30/60°)
- [ ] `backend/tests/test_dimensions.py` — 신규 SCORE-07(micro_bent_zero_track, intentional_bend_not_penalized) + TRUST-02(stability_does_not_inflate) + **갱신** is_mean→uses_core_dimensions(40/99/0)
- [ ] `backend/tests/test_pipeline_mode3.py` — TRUST-01(display_matches_score_source) + TRUST-03(**Mode1 분리: mode1_scoring_basis_reference_motion = build_mode1 직렬화 필드 단언** + unknown_move_gate Mode3 4-value parametrize + build_mode3_backward_compat[reference_motion ValueError 포함]) + TRUST-05(vision_hook_passthrough = SAME-object identity)
- [ ] `backend/tests/test_anchor_known_answer.py` — D-05 6 앵커 방향검증 (실영상 per-test @requires_anchor_env) + synthetic above-cutoff(마커 없음, 항상 실행) + 활성 path 명시
- [ ] `backend/tests/test_assemble.py` **갱신** (ITER-5) — build_mode1 always-emit 회귀: test_mode1_shape_and_clamp 기대 dict 에 scoringBasis/scoringBasisLabel 추가 (Plan 04 Task 2). test_mode1_segment_scores_included_only_when_given 영향 없음 확인
- [ ] 신규 pipeline/core 케이스 단독 실행 시 **behavior RED** (collection 아님), 19-01-SUMMARY 에 실패 케이스명 기록

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3D 골격 실기기 GL 렌더 (카메라 내 표시 + timeline scrub desync 0) | TRUST-04 | 앱 JS 러너 부재 — RN 디바이스 GL 렌더 자동화 불가 (smoke 는 수치+frame 수만 검증) | 실기기/시뮬레이터 result 화면 3D 골격이 화면 안에 표시 + timeline scrub 시 frame 누락/점프 없는지 육안 (과거 doc + occlusion 케이스 포함) |
| scoringBasisLabel 화면 표시 + contributesToOverall=false 보조지표 카피 | TRUST-03 | 앱 JS 러너 부재 — 렌더 자동화 불가 (tsc 는 타입만) | result 헤더 + DimensionDetailModal 에 "기준 동작 없음 — 절대 자세 기준 평가" + stability detail "종합점수에는 직접 합산하지 않는 보조 지표입니다" 노출 확인 |
| D-05 앵커 실영상 정량검증 | SCORE-06/07 | RTMW 3D pose = GPU 필요, Pod 크레딧 소진 자동종료 | belle 크레딧 충전 + 새 Pod → `RUN_PHASE19_ANCHORS=1` 6 페어 방향검증 |

---

## Validation Sign-Off

- [ ] 신규 케이스 단독 실행 시 behavior RED (collection 아님)
- [ ] 모순 케이스 2건(is_mean / 15° monotonic) 새 계약으로 갱신
- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] D-05 anchor: 실영상 per-test @requires_anchor_env + synthetic above-cutoff always-on (module-level pytestmark 0 — ITER-2 HIGH-1)
- [ ] **Mode1 케이스 분리 + 직렬화 단언 (ITER-4 HIGH-1)** — test_mode1_scoring_basis_reference_motion 가 build_mode1 직렬화 comparison["scoringBasis"]=="reference_motion" 단언, test_unknown_move_gate 는 Mode3 4-value + reference_motion 미등장 invariant (ITER-3 MEDIUM-1)
- [ ] **Mode1 scoringBasis 3중 계약화 (ITER-4 HIGH-1)** — Mode1Comparison OPTIONAL scoringBasis?:'reference_motion' + scoringBasisLabel? / build_mode1 emit / models.py / contract.md lockstep
- [ ] scoringBasis = 실제 채점 source, **Mode3 enum = 4-value (reference_motion 부재, Mode1 전용)**, composite enum 처리 (ITER-2 HIGH-2/HIGH-3 + ITER-3 HIGH-2)
- [ ] **reference_motion 검증 = ENUM/VALUE 체크 (ITER-4 HIGH-2)** — Mode3 union 4 멤버 + reference_motion ∉ / `_MODE3_SCORING_BASES`=={4} / Mode3 테이블 row 부재. raw prose grep-zero 요구 0 (설명 주석의 reference_motion 언급 허용)
- [ ] build_mode3 backward-compat + reference_motion ValueError 가드 (ITER-2 MEDIUM-2 + ITER-3 HIGH-2) + _apply_vision_veto SAME-object identity (ITER-2 MEDIUM-3)
- [ ] reference-free 트랙 = line+stability 만 (posture 점수 차원 아님 — future evidence 레이어, ITER-3 MEDIUM-2)
- [ ] contributesToOverall OPTIONAL + simulatedResult.ts 갱신 + typecheck WITH simulatedResult green (ITER-2 BLOCKER-1)
- [ ] smoke = LOCAL tsc 컴파일 + createRequire production normalizeFrames import (single source, no-copy) + frame 수 보존 (ITER-2 BLOCKER-2/HIGH-4 + ITER-3 HIGH-1) + **thrown error + process.exitCode + finally cleanup, inline process.exit 0 (ITER-4 MEDIUM-1)**
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] Pre-existing 실패(test_pole_detector / test_pipeline_geminid_wiring / test_spike_gemini_moment_smoke) isolation 제외 확인

**Approval:** pending
</content>
</invoke>
