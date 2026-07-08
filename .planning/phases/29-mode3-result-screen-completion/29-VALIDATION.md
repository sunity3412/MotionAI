---
phase: 29
slug: mode3-result-screen-completion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-09
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend/requirements-dev.txt) / 앱은 tsc만 (JS 테스트 러너 없음) |
| **Config file** | backend/tests/conftest.py (별도 pytest.ini 없음) |
| **Quick run command** | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/pipeline -q -x` |
| **Full suite command** | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` (기존 54 failures 알려짐 — 게이트 = 신규 실패 0) |
| **App gate** | `cd app && npm run typecheck` (유일한 정적 게이트) |
| **Estimated runtime** | quick ~30s / full ~2min / typecheck ~15s |

---

## Sampling Rate

- **After every task commit:** 백엔드 변경 시 관련 `tests/pipeline` 서브셋 `-x`, 앱 변경 시 `npm run typecheck`
- **After every plan wave:** backend full suite (신규 실패 0 기준) + typecheck
- **Before `/gsd-verify-work`:** full suite + Pod sweep 게이트(D-02) + HUMAN-UAT 적립 완료 확인
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | D-01 mode3_held+md → tally·breakdown 방출 (Gemini 0회) | — | N/A | unit | `pytest tests/pipeline -k mode3 -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | D-01/D-03 md 빈 dict → breakdown 미방출+점수 불변 | — | N/A | unit | 위와 동일 파일 | ❌ W0 | ⬜ pending |
| TBD | — | — | D-02 overallScore == breakdown.final 항등 (mode3) | — | N/A | unit + Pod sweep | unit + `evals/phase29/assert_gates.py` | ❌ W0 (+Pod manual) | ⬜ pending |
| TBD | — | — | D-08 mode3 zoom joint = 감점 record 소스 | — | N/A | unit | `pytest tests/ -k "mode3_fault_zoom" -q` | 확인 필요 | ⬜ pending |
| TBD | — | — | D-04~07/14 앱 카피·게이트 렌더 분기 | — | N/A | typecheck + manual | `npm run typecheck` + HUMAN-UAT | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*(Task ID는 플랜 확정 후 planner가 매핑)*

---

## Wave 0 Requirements

- [ ] `backend/tests/pipeline/test_mode3_tally_seam.py` — D-01/D-02/D-03 (md 유/무 × 등록/미등록 × breakdown 방출/점수 항등)
- [ ] `backend/evals/phase29/` — run_sweep.py + assert_gates.py + eval_keys (phase24 6페어 mode3 변형)
- [ ] mode3 zoom joint 선택 교체분 회귀 테스트 (기존 fault_zoom 테스트 위치 확인 후)
- 앱 신규 테스트 프레임워크 도입은 하지 않음 (프로젝트 컨벤션 — typecheck + 실기기)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 가로 전환 + 구빌드 폴백 무크래시 | D-11/D-12 | 네이티브 회전 — 자동화 불가 | HUMAN-UAT.md 적립 (batch UAT 원칙 — 즉시 belle 호출 금지) |
| D1 비교영상 미표시 재현·규명 | D-09 | 진단 태스크 (Pitfall 4 체크리스트) | 재현 → presigned TTL 등 원인 규명 → fix |
| EAS 빌드·제출 성공 | D-13 | 빌드 체인 자체가 검증 | `eas build/submit --non-interactive` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
