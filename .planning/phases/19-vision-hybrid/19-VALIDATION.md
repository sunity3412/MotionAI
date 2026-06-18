---
phase: 19
slug: vision-hybrid
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-18
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 19-RESEARCH.md "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| **Config file** | `backend/tests/conftest.py` (pytest.ini 없음 — conftest + sys.path 패턴) |
| **Quick run command** | `cd backend && python -m pytest tests/test_kismam.py tests/test_dimensions.py -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q` |
| **App static gate** | `cd app && npm run typecheck` (tsc --noEmit — 유일한 정적 게이트; JS 테스트 러너 부재) |
| **Estimated runtime** | ~30–60 seconds (backend unit) |

---

## Sampling Rate

- **After every task commit:** `cd backend && python -m pytest tests/test_kismam.py tests/test_dimensions.py -x` (+ `cd app && npm run typecheck` for 앱 task)
- **After every plan wave:** `cd backend && python -m pytest tests/ -q` (full backend suite, pre-existing 실패는 isolation 제외)
- **Before `/gsd-verify-work`:** Full suite green + (Pod 재개 시) D-05 앵커 방향검증
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| SCORE-06 | 단일 major fault가 종합 지배 (한 관절 큰 편차 → 종합 급락, 평균 희석 X) | unit | `pytest tests/test_kismam.py::test_single_major_fault_dominates -x` | ❌ W0 |
| SCORE-06 | above-cutoff: 모든 관절 편차<tol → 종합 high (위양성 없음) | unit | `pytest tests/test_kismam.py::test_clean_pose_high_score -x` | ❌ W0 |
| SCORE-07 | 신전요구 관절 160° 미달 → line 차원 0점(요소 무효, 비례감점 아님) | unit | `pytest tests/test_dimensions.py::test_micro_bent_zero_track -x` | ❌ W0 |
| SCORE-07 | 의도적 굽힘(expects_extension False) 관절 → 0점 트랙 미적용 | unit | `pytest tests/test_dimensions.py::test_intentional_bend_not_penalized -x` | ❌ W0 |
| TRUST-01 | 표시 각도 = 점수 source(DTW-정렬 median), user/ref 동일 구간 | unit | `pytest tests/test_pipeline_mode3.py::test_display_matches_score_source -x` | ✅파일 ❌케이스 |
| TRUST-02 | DIM_STABILITY 높아도 angle/line 낮으면 종합 낮음 (stability 인플레 X) | unit | `pytest tests/test_dimensions.py::test_stability_does_not_inflate -x` | ❌ W0 |
| TRUST-02 | 어깨 COACHING_FOCUS 라벨 'STATIC POSE' 의미로 정정 | unit | `pytest tests/test_kismam.py::test_shoulder_focus_label -x` | ❌ W0 |
| TRUST-03 | MODE_SELF 미보유 동작 → confident 점수 대신 근거 플래그 + 절대트랙 | unit | `pytest tests/test_pipeline_mode3.py::test_unknown_move_gate -x` | ✅파일 ❌케이스 |
| TRUST-04 | reshapePose3dData → hip-center recenter + torso normalize (origin-centered) | unit(앱) | `cd app && npm run typecheck` (JS 러너 부재 — 순수함수 수동검증) | ⚠ 러너 없음 |
| TRUST-05 | v1 vision hook = pass-through (점수 불변, OFF 시 입력 그대로) | unit | `pytest tests/test_pipeline_*.py::test_vision_hook_passthrough -x` | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Known-Answer Anchor Validation (D-05 — Pod 재개 후 게이트)

| Anchor | Expected (방향, curve-fit 아님) | Test |
|--------|-------------------------------|------|
| climb (등 말림 line ~25°) | line 차원 지배 → 종합 낮음. fault < correct | `test_anchor_known_answer.py::test_climb_fault_lower` (GPU skip marker) |
| kip-up (무릎 ~35° angle) | angle 차원 지배 → 종합 낮음 | 동일 (parametrize) |
| 6/6 fault 페어 | 모두 종합 낮음 (94 같은 위양성 0건) | 6 페어 parametrize |
| above-cutoff (미보유 고득점) | 정상 동작 high 유지 (sensitivity gate) | synthetic above-cutoff angles |

> 앵커는 **방향 판정**(fault<정상 + major 차원 지배)이지 점수 수치 타깃 아님
> ([[calibration-source-hard-gate]] [[scoring-redesign-must-generalize-no-overfit]]).

---

## Wave 0 Requirements

- [ ] `backend/tests/test_kismam.py` — SCORE-06(single_major_fault_dominates, clean_pose_high_score) + TRUST-02(shoulder_focus_label) 케이스 추가
- [ ] `backend/tests/test_dimensions.py` — SCORE-07(micro_bent_zero_track, intentional_bend_not_penalized) + TRUST-02(stability_does_not_inflate) 케이스 추가
- [ ] `backend/tests/test_pipeline_mode3.py` — TRUST-01(display_matches_score_source) + TRUST-03(unknown_move_gate) 케이스 추가
- [ ] `backend/tests/test_anchor_known_answer.py` — D-05 6 앵커 방향검증 (GPU skip marker — Pod 재개 후 활성)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3D 골격 실기기 렌더 (origin-centered, 카메라 내 표시) | TRUST-04 | 앱 JS 테스트 러너 부재 (CLAUDE.md: no JS test runner) — RN 디바이스 렌더는 자동화 불가 | 실기기/시뮬레이터에서 result 화면 3D 골격이 화면 안에 표시되는지 육안 확인 |
| D-05 앵커 실영상 정량검증 | SCORE-06/07 | RTMW 3D pose = GPU 필요, Pod 크레딧 소진 자동종료 | belle 크레딧 충전 + 새 Pod → mock E2E 6 페어 방향검증 |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] Pre-existing 실패(test_pole_detector / test_pipeline_geminid_wiring / test_spike_gemini_moment_smoke) isolation 제외 확인
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
