---
phase: 13
slug: llm-coaching-detail
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-16
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 13-RESEARCH.md "## Validation Architecture". Planner fills the per-task map.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend, `backend/requirements-dev.txt`) · `tsc --noEmit` (app, `npm run typecheck`) |
| **Config file** | none dedicated — tests under `backend/tests/` (per-phase subdirs e.g. `backend/tests/phase13/`) |
| **Quick run command** | `cd backend && python -m pytest tests/phase13 -q` |
| **Full suite command** | `cd backend && python -m pytest -q` |
| **Estimated runtime** | ~30-60 seconds (pure-function analysis tests, no GPU/network) |

---

## Sampling Rate

- **After every task commit:** `cd backend && python -m pytest tests/phase13 -q`
- **After every plan wave:** `cd backend && python -m pytest -q`  (+ `cd app && npm run typecheck` for contract/UI tasks)
- **Before `/gsd-verify-work`:** Full suite green + typecheck clean
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-A-* | A | — | PERS-03 | — | BodyProfile painAreas never feeds scoring (D-05) | unit | `pytest tests/phase13 -q` | ❌ W0 | ⬜ pending |
| 13-B-* | B | — | studio-term-3branch-system | — | ipsfCode branch copy split (분기1/분기2) | unit | `pytest tests/phase13 -q` | ❌ W0 | ⬜ pending |

*Planner expands per task. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase13/` — new test dir + `conftest.py` shared fixtures (sample Firestore doc with `forcePatternInference.findings[]` + `bodyProfile.painAreas`, sample TechniqueProfile with/without ipsfCode)
- [ ] Exercise-library fixture under test (`corrective_exercises.json` per RESEARCH Plan A)
- [ ] IPSF angle fixture under test (criteria 7) — registered-move angles flagged for human-verify before lock (RESEARCH Open Q1)

*Existing pytest infrastructure covers the framework; only fixtures/dirs are new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실 영상 → 실 Cerebras `tip.detail2` → Firestore 저장 → 결과화면 표시 (criteria 5) | PERS-03 | GPU Pod + Cerebras key + 실제 분석 필요 (단위테스트 불가) | Pod 기동 + CEREBRAS_KEY_PARAM 주입 + uvicorn 재시작 후 실 영상 1건 분석, Firestore doc `tips[].detail2` 채워짐 + 결과화면 "코칭 팁 자세히" 표시 확인 |
| 결과화면 보완운동 카드 + "다른 운동 보기" 표시 (criteria 2,4) | PERS-03 | RN UI 렌더 | 실기기/시뮬레이터에서 분석 결과 화면 확인 |

*Registered-move IPSF angle numbers (criteria 7): re-verify via NotebookLM/belle before locking (RESEARCH Open Q1).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-16 (gsd-plan-checker PASS — plans nyquist-sound: Wave 0 = 13-A T1, every autonomous task carries an automated command, no 3-consecutive-unverified window. Per-task verification lives in each PLAN.md `<acceptance_criteria>`.)
