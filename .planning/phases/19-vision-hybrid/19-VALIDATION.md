---
phase: 19
slug: vision-hybrid
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-18
revised: 2026-06-18 (reviews — BLOCKER/HIGH/MEDIUM 반영)
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 19-RESEARCH.md "## Validation Architecture" + 19-REVIEWS.md 11 findings.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| **Config file** | `backend/tests/conftest.py` (pytest.ini 없음 — conftest + sys.path 패턴) |
| **Quick run command** | `cd backend && python -m pytest tests/test_kismam.py tests/test_dimensions.py -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q` |
| **App static gate** | `cd app && npm run typecheck` (tsc --noEmit — 유일한 정적 게이트) |
| **App 3D smoke** | `node app/scripts/_smoke_joints_normalize.mjs` (maxAbsCoord<=3 — JS 러너 부재 우회) |
| **D-05 anchor gate** | `RUN_PHASE19_ANCHORS=1 pytest tests/test_anchor_known_answer.py -q` (env + S3/GPU 필요) |
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
| TRUST-02 | stability 비기여 = contributesToOverall=false / weightPercent=0 | unit | `pytest tests/test_dimensions.py::test_stability_does_not_inflate -x` (+ build_dimension_explanation 출력 단언) | ❌ W0 |
| TRUST-03 | MODE_SELF 미보유 = is_reference_free_motion → scoringBasis="reference_free_absolute" + label + 절대트랙 (copyBranch 단독 분기 금지) | unit | `pytest tests/test_pipeline_mode3.py::test_unknown_move_gate -x` | ✅파일 ❌케이스 |
| TRUST-03 | scoringBasisLabel 이 result 화면 + DimensionDetailModal 에 표시 (백엔드 only 아님) | static(앱) | `cd app && npm run typecheck` (JS 러너 부재 — 수동 육안 보조) | ⚠ 러너 없음 |
| TRUST-04 | reshapePose3dData → COCO-17 indexOf recenter + torso/bbox normalize, raw passthrough 0 | smoke | `node app/scripts/_smoke_joints_normalize.mjs` (maxAbsCoord<=3) | ❌ W0/W1B |
| TRUST-05 | v1 vision hook = pass-through (점수 불변, OFF 시 입력 그대로) | unit | `pytest tests/test_pipeline_mode3.py::test_vision_hook_passthrough -x` | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ 갱신/러너없음*

---

## Known-Answer Anchor Validation (D-05 — RUN_PHASE19_ANCHORS env-gate)

| Anchor | Expected (방향, curve-fit 아님) | Test |
|--------|-------------------------------|------|
| climb (등 말림 line ~25°) | line 차원 지배 → 종합 낮음. fault < correct | `test_anchor_known_answer.py` parametrize (env-gate skip) |
| kip-up (무릎 ~35° angle) | angle 차원 지배 → 종합 낮음 | 동일 parametrize |
| 6/6 fault 페어 | 모두 종합 낮음 (94 같은 위양성 0건) | 6 페어 parametrize |
| above-cutoff (미보유 고득점) | 정상 동작 high 유지 (sensitivity gate) | synthetic angles — env-gate 무관, 항상 실행 |

> 활성: `RUN_PHASE19_ANCHORS=1 pytest tests/test_anchor_known_answer.py -q` (+ S3/GPU). env 부재 시 전부 skip.
> 앵커는 **방향 판정**(fault<정상 + major 차원 지배)이지 점수 수치 타깃 아님
> ([[calibration-source-hard-gate]] [[scoring-redesign-must-generalize-no-overfit]]).
> skip 본문에 real fixture key + 페어별 dominant-dimension 메타 상수 보존 (활성화 mechanical).

---

## Wave 0 Requirements

- [ ] `backend/tests/test_kismam.py` — 신규 SCORE-06(single_major_fault_dominates, clean_pose_high_score, within_tolerance_remains_high) + TRUST-02(shoulder_focus_label) + **갱신** test_score_monotonic_decreasing_with_deviation(0/30/60°)
- [ ] `backend/tests/test_dimensions.py` — 신규 SCORE-07(micro_bent_zero_track, intentional_bend_not_penalized) + TRUST-02(stability_does_not_inflate) + **갱신** is_mean→uses_core_dimensions(40/99/0)
- [ ] `backend/tests/test_pipeline_mode3.py` — TRUST-01(display_matches_score_source) + TRUST-03(unknown_move_gate parametrize 3-way) + TRUST-05(vision_hook_passthrough)
- [ ] `backend/tests/test_anchor_known_answer.py` — D-05 6 앵커 방향검증 (RUN_PHASE19_ANCHORS env-gate + 활성 path 명시)
- [ ] 신규 pipeline/core 케이스 단독 실행 시 **behavior RED** (collection 아님 — HIGH-5), 19-01-SUMMARY 에 실패 케이스명 기록

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3D 골격 실기기 GL 렌더 (카메라 내 표시) | TRUST-04 | 앱 JS 러너 부재 — RN 디바이스 GL 렌더 자동화 불가 (smoke 는 수치만 검증) | 실기기/시뮬레이터 result 화면 3D 골격이 화면 안에 표시되는지 육안 (과거 doc + occlusion 케이스 포함) |
| scoringBasisLabel 화면 표시 | TRUST-03 | 앱 JS 러너 부재 — 렌더 자동화 불가 (tsc 는 타입만) | result 헤더 + DimensionDetailModal 에 "기준 동작 없음 — 절대 자세 기준 평가" 노출 확인 |
| D-05 앵커 실영상 정량검증 | SCORE-06/07 | RTMW 3D pose = GPU 필요, Pod 크레딧 소진 자동종료 | belle 크레딧 충전 + 새 Pod → `RUN_PHASE19_ANCHORS=1` 6 페어 방향검증 |

---

## Validation Sign-Off

- [ ] 신규 케이스 단독 실행 시 behavior RED (collection 아님 — HIGH-5)
- [ ] 모순 케이스 2건(is_mean / 15° monotonic) 새 계약으로 갱신 (BLOCKER-3)
- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] D-05 anchor env-gate (RUN_PHASE19_ANCHORS) + 활성 path 명시 (MEDIUM-3)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] Pre-existing 실패(test_pole_detector / test_pipeline_geminid_wiring / test_spike_gemini_moment_smoke) isolation 제외 확인

**Approval:** pending
