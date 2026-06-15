---
phase: 3
slug: bodyprofileinput
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 상세 per-task map 은 planner 가 03-RESEARCH.md "## Validation Architecture" 기준으로 PLAN.md 에 채운다.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | 앱: `tsc --noEmit` (유일한 static gate — JS test runner 없음). 백엔드: pytest 8.x (3-way contract lockstep 테스트) |
| **Config file** | `app/tsconfig.json` (strict) / `backend/requirements-dev.txt` |
| **Quick run command** | `cd app && npm run typecheck` |
| **Full suite command** | `cd app && npm run typecheck` + `cd backend && python -m pytest tests/ -q` |
| **Estimated runtime** | ~30–90s (typecheck 빠름, pytest 수초~수십초) |

---

## Sampling Rate

- **After every task commit:** `cd app && npm run typecheck` (TS 변경 시) 또는 해당 백엔드 pytest 모듈.
- **After every plan wave:** full suite (typecheck + pytest) green.
- **Before `/gsd-verify-work`:** full suite green + 3-way contract lockstep 테스트 통과.
- **Max feedback latency:** ~90s.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (planner fills) | — | — | BODY-02 | — | weightKg scoring 미유입 (grep 0) | unit/static | `npm run typecheck` / pytest | ❌ W0 | ⬜ pending |

*planner 가 RESEARCH Validation Architecture 의 게이트(예: weightKg grep gate over dimensions.py/kismam.py = 0 matches, 3-way contract lockstep, normalize() 방어 테스트)를 task 별로 전개.*
*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] 백엔드 BodyProfile 계약 검증 테스트 (models.py/validation.py mirror + nested-array 금지 확인)
- [ ] weightKg 비유입 grep gate (dimensions.py / kismam.py / body_normalization*.py = 0 matches) — D-05 박제
- [ ] 앱 typecheck gate (BodyProfile 타입 3-way 정합)

*기존 인프라(tsc/pytest)로 대부분 커버 — 신규 프레임워크 설치 불필요.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BodyProfile 입력 UX 흐름 (마이페이지 + 첫분석 권유 + 건너뛰기) | BODY-02 | UI 시각/제스처 검증은 자동화 한계 | belle TestFlight: 마이페이지 입력→저장→재진입 표시 / 첫분석 직전 권유 모달 dismiss(재권유 없음) / 부분입력 graceful |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
