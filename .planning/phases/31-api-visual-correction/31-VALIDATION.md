---
phase: 31
slug: api-visual-correction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-19
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 31-RESEARCH.md `## Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend) / tsc --noEmit (app) |
| **Config file** | backend/requirements-dev.txt (pytest 설정 파일 없음 — 디렉터리 관례) |
| **Quick run command** | `python -m pytest backend/tests/<file>.py -x` |
| **Full suite command** | `python -m pytest backend/tests` + `cd app && npm run typecheck` |
| **Estimated runtime** | ~60 seconds (backend suite) + ~30 seconds (typecheck) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/<touched-file>.py -x` (해당 테스트 단건)
- **After every plan wave:** Run `python -m pytest backend/tests` (+ `cd app && npm run typecheck`, 앱 wave 시)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

> Task ID 는 plan 확정 후 planner 가 채움. Req 행은 RESEARCH `Phase Requirements → Test Map` 기준.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | D-11/12 화살표 드로잉 순수 함수 | — | N/A | unit | `python -m pytest backend/tests/test_fault_zoom*.py -x` | ✅ (기존 확장) | ⬜ pending |
| TBD | TBD | TBD | D-02 VisualGenEngine 어댑터 (HTTP mock, 멱등, 24h URL→S3) | — | 키는 SSM 로드, 로그 비노출 | unit | `python -m pytest backend/tests/phase31/test_visual_gen.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-05/08 silhouetteStatus 상태 머신 + 조용한 폴백 | — | N/A | unit | `python -m pytest backend/tests/phase31/test_silhouette_flow.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-06/07 요청 Lambda auth·한도·202 + 워커 dispatch | — | Firebase 토큰 auth 필수, 한도 transaction | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | 페어 적재 learningOptIn===true 엄격 게이트 | — | opt-in false/부재 = 적재 금지 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-04/09/10 앱 계약 normalize + 섹션 렌더 타입 | — | N/A | typecheck | `cd app && npm run typecheck` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase31/` 디렉터리 + test_visual_gen.py / test_silhouette_flow.py / test_visual_request.py / test_pair_store.py 스텁 (phase22/ 디렉터리 선례)
- [ ] DashScope HTTP mock fixture (urllib 레벨 monkeypatch — 스파이크 코드가 순수 stdlib 라 mock 용이)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실기기 UX — D-09/10 반투명 중첩·회전 카드 렌더/제스처 | D-09/D-10 | 실기기 렌더/제스처는 자동화 불가 | HUMAN-UAT.md 적립 — 즉시 belle 호출 금지, phase 31 후 배치 UAT ([[batch-uat-after-phase-31]]) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
