---
phase: 27
slug: analysis-speed-1min
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-07
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 27-RESEARCH.md §Validation Architecture (2026-07-07).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend) / `tsc --noEmit` (app) |
| **Config file** | `backend/requirements-dev.txt` (별도 pytest.ini 없음 — 기존 관례) |
| **Quick run command** | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q -k "phase27 or fault_zoom or vision"` (신설 테스트 네이밍에 따라 조정) |
| **Full suite command** | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` + `cd app && npm run typecheck` |
| **Estimated runtime** | quick ~30s / full ~3min |

---

## Sampling Rate

- **After every task commit:** 관련 unit quick run + `npm run typecheck` (앱 변경 시)
- **After every plan wave:** backend full pytest — 기존 pre-existing failure 기준선 대비 신규 FAILED/ERROR 0 (node-ID diff)
- **Before `/gsd-verify-work`:** full suite green(신규 기준) + Pod phase gate 통과
- **Max feedback latency:** ~180s (full)

---

## Per-Task Verification Map

> requirement ID 미발급 시점 작성 — CONTEXT 결정(D-NN) 기준 매핑. 플랜 생성 후 태스크 ID로 구체화.

| 결정 | Behavior | Test Type | Automated Command | File Exists | Status |
|------|----------|-----------|-------------------|-------------|--------|
| D-01 | EVAL18 6페어 점수·verdict·faults 무회귀 | Pod eval (SERIAL, artifact-gated) | `sweep_phase15.py --pair-sequential` → `evals/phase18/assert_baseline.py` 대조 (EVAL_OUT_DIR 리포 밖) | ✅ 기존 하니스 | ⬜ pending |
| D-03 | 병렬화 후 결정론 — cold/warm 동일, fan-out 집계 순서 불변 | Pod eval + unit | phase25 `check_cold_warm_determinism` 패턴 + fan-out 순서보존 unit (fake client) | ❌ W0 (unit) | ⬜ pending |
| D-04 | 핸들 세션 — 학생 영상 업로드 1회, 종료 일괄 delete, 누수 0 | unit | fake genai client로 upload/delete 호출 수 assert | ❌ W0 | ⬜ pending |
| D-06 | complete 후 zoom 부분 업데이트 + pending→done 전이 | unit + manual | firestore_admin mock unit + belle 실기기 onSnapshot 확인 | ❌ W0 (unit) | ⬜ pending |
| D-02/D-07 | 진행률/로딩 재미 요소 | typecheck + manual | `npm run typecheck` + belle 실기기 | ✅ (typecheck) | ⬜ pending |
| 계측 | stage_timing 로그 방출 + timingsMs flat 저장 | unit | caplog로 stage_timing 라인 assert + flat validator | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] stage-timing 계측 코드 + `backend/tests/test_stage_timing.py` (로그 라인/flat dict 검증)
- [ ] **cold baseline 실측 1회 (변경 전)** — Pod EVAL18 1페어 이상, before 수치 확보 (cacheHit=false 확인)
- [ ] fake genai client fixture — upload/delete 카운트 + fan-out 순서 결정론용 (기존 test_client.py monkeypatch 패턴 확장)
- [ ] `backend/tests/test_fault_zoom_deferred.py` (D-06 부분 업데이트 + validator)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| zoom pending→done 앱 반영 | D-06 | onSnapshot UI 전이는 실기기에서만 관찰 | belle 실기기: 결과 진입 직후 확대카드 로딩 표시 → 수십 초 내 PNG 도착 확인 |
| 로딩 재미 요소/진행률 체감 | D-02/D-07 | 체감 품질은 사람 판단 | belle 실기기: 분석 대기 중 텍스트 로테이션 표시·진행률 전진 확인 |
| before/after 총 소요 실측 | D-01 목표치 | 벽시계는 Pod 실측 필요 | 동일 페어 cold run 전/후 stage-timing 표 대조 (분석 간 SERIAL) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---

## 불변 제약 (검증 실행 시)

- **분석 간 SERIAL 필수** — 파이프라인 동시성 비안전. eval/sweep 순차만. (단일 분석 내부 병렬은 이 phase의 변경 대상이며 D-03 결정론 게이트로 검증)
- Gemini File API delete 규율 보존 — 20GB 적체 사고 재발 금지. 핸들 세션 도입 시에도 종료 일괄 delete가 게이트.
- Pod sweep 전 Gemini 크레딧 잔액 확인 (고갈 이력).
