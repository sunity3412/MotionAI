---
phase: 4
slug: ux-occlusion-confidence
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-13
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `04-RESEARCH.md` §Validation Architecture (Spike 001 evaluate_4way + IPSF gate).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) + `npm run typecheck` (app/ TypeScript) |
| **Config file** | `backend/tests/conftest.py` (기존) + `backend/tests/phase04/conftest.py` (Wave 0 신설) |
| **Quick run command** | `pytest backend/tests/phase04/ -x -q` |
| **Full suite command** | `pytest backend/tests/ -q` |
| **Estimated runtime** | ~15s (phase04 단위) / ~수십초 (full backend) |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/phase04/ -x -q` (< 15초)
- **After every plan wave:** Run `pytest backend/tests/ -q` + (app 변경 시) `npm run typecheck`
- **Before `/gsd-verify-work`:** Full suite green + `npm run typecheck` + belle 정은지 5영상 재처리 시각 검증
- **Max feedback latency:** 15 seconds (단위), wave merge 시 full suite

---

## Per-Task Verification Map

> Task ID 는 planner 산출 후 확정. 아래는 요구사항 단위 매핑(POSE-03 a~h) — planner 가 각 task 에 배정한다.

| Req (POSE-03 sub) | Behavior | Wave | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|---|
| POSE-03-a | confidence 미달 frame 식별 → synthesis_needed_mask 정확 | 1 | unit | `pytest backend/tests/phase04/test_confidence_gate.py -x` | ❌ W0 | ⬜ pending |
| POSE-03-b | Gemini view reasoning graceful degrade (API 실패 시 1차 결과 반환) | 1 | unit | `pytest backend/tests/phase04/test_synthesis_adapter.py::test_gemini_degrade -x` | ❌ W0 | ⬜ pending |
| POSE-03-c | temporal 병합 (primary + synth, higher confidence wins) | 1 | unit | `pytest backend/tests/phase04/test_synthesis_merge.py -x` | ❌ W0 | ⬜ pending |
| POSE-03-d | `ai_synthesis_failed` / `ai_synthesis_partial` warning = models.py frozenset 3-way lockstep | 1 | unit | `pytest backend/tests/phase04/test_warning_lockstep.py -x` | ❌ W0 | ⬜ pending |
| POSE-03-e | Firestore synthesis meta flat 저장 (nested-array 0) | 1 | unit | `pytest backend/tests/phase04/test_synthesis_firestore_flat.py -x` | ❌ W0 | ⬜ pending |
| POSE-03-f | G4 is_reference=True 시 합성 트리거 발동 안 함 | 1 | unit | `pytest backend/tests/phase04/test_synthesis_g4_guard.py -x` | ❌ W0 | ⬜ pending |
| POSE-03-g | Spike 001 evaluate_4way: cylindrical mesh path vs baseline IPSF 감점 비교 | 3 | integration | `pytest backend/tests/phase04/test_evaluate_4way.py -x` (RunPod) | ❌ W3 | ⬜ pending |
| POSE-03-h | PoseViewer3D 컴포넌트 TypeScript 타입 체크 통과 | 2 | static | `npm run typecheck` (app/) | ❌ W2 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase04/` 디렉토리 + `__init__.py` 신설
- [ ] `backend/tests/phase04/conftest.py` — synthetic joint sequence fixtures (Spike 002d 패턴 재사용)
- [ ] `backend/tests/phase04/test_confidence_gate.py` — POSE-03-a
- [ ] `backend/tests/phase04/test_synthesis_adapter.py` — POSE-03-b (GeminiViewReasoner mock + CylindricalMeshAdapter mock)
- [ ] `backend/tests/phase04/test_synthesis_merge.py` — POSE-03-c (temporal.py 재사용 검증)
- [ ] `backend/tests/phase04/test_warning_lockstep.py` — POSE-03-d
- [ ] `backend/tests/phase04/test_synthesis_firestore_flat.py` — POSE-03-e
- [ ] `backend/tests/phase04/test_synthesis_g4_guard.py` — POSE-03-f

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 사용자 3D 뷰어 손가락 360° 회전·핀치 줌 동작 | POSE-03 (UI-SPEC Stage 3) | R3F 제스처는 실 기기 인터랙션 — 자동화 비효율 | EAS preview 빌드 → 결과 화면 진입 → 3D 캔버스 드래그/핀치 → 측면·후면 각도 확인 |
| 정은지 5영상 재처리 정확도 향상 (occlusion 감점 감소) | POSE-03-g | RunPod GPU + 시각 판단 필요 | Pod 에서 5영상 재처리 → evaluate_4way 점수 + belle 시각 검증 |
| occlusion "추정" 표기 + 정확도 제한 배지 노출 | POSE-03 (UI-SPEC #2) | UX 카피 톤 — 시각 확인 | 가림 포함 영상 분석 → 결과 화면 배지/카피 확인 (Phase 12.5 톤 일관성) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (POSE-03 a~h 전부 매핑)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (phase04 test 디렉토리 — 04-00 신설)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-13 (계획 단계 검증 — Wave 0 실행 시 wave_0_complete 갱신)
