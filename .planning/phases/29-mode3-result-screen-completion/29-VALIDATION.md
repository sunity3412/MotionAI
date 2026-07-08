---
phase: 29
slug: mode3-result-screen-completion
status: synced
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-09
updated: 2026-07-09
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 2026-07-09 planner revision: Task ID 매핑·경로·커맨드를 플랜 실체(29-01~29-08)와 동기화.
> 2026-07-09 reviews revision (29-PLAN-REVIEW 반영): HIGH-1 — 29-03 테스트가 criterion→region 소스로 확장(케이스 5종), 29-04 에 T1(투영 helper 단일화) 신설로 T1~T4. HIGH-2 — 29-06 테스트에 inactive 404·prefix 거부 케이스 추가 + canonical 컬렉션 grep 게이트. MEDIUM-1 — 29-05 sweep 에 score-switch 대조표·정지 조건. MEDIUM-2 — 29-08 UAT verify 를 per-token grep 으로 교체.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (backend/requirements-dev.txt) / 앱은 tsc만 (JS 테스트 러너 없음) |
| **Config file** | backend/tests/conftest.py (별도 pytest.ini 없음) |
| **Quick run command** | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_mode3_tally_seam.py tests/test_mode3_fault_zoom_selection.py tests/pipeline -q -x` (phase 29 신규 seam 테스트는 `backend/tests/` 루트 — `tests/pipeline` 서브셋만으론 수집되지 않음) |
| **Full suite command** | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` (기존 54 failures 알려짐 — 게이트 = 신규 실패 0) |
| **App gate** | `cd app && npm run typecheck` (유일한 정적 게이트 — 투영 helper 매핑은 grep 소스 단언으로 보강) |
| **Estimated runtime** | quick ~30s / full ~2min / typecheck ~15s |

---

## Sampling Rate

- **After every task commit:** 백엔드 변경 시 해당 plan 의 신규 테스트 파일 + `tests/pipeline` 서브셋 `-x`, 앱 변경 시 `npm run typecheck`
- **After every plan wave:** backend full suite (신규 실패 0 기준) + typecheck
- **Before `/gsd-verify-work`:** full suite + Pod sweep 게이트(D-02, 29-05 — score-switch 대조표·정지 조건 판정 포함) + HUMAN-UAT 적립 완료 확인 (per-token grep)
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 29-02/T1 | 29-02 | 1 | D-01/D-02/D-03 매트릭스 테스트 작성 (RED) | T-29-02-01 | mode1 무회귀 케이스 포함 | unit | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_mode3_tally_seam.py -q` (RED 게이트: exit 1) | ✅ W0 — 이 태스크가 생성 | ⬜ pending |
| 29-02/T2 | 29-02 | 1 | D-01 mode3_held+md → tally·breakdown 방출 (Gemini 0회) | T-29-02-02 | seam try/except passthrough | unit | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_mode3_tally_seam.py tests/test_pipeline_deduction_seam.py -q` | ✅ W0 (T1 산출) | ⬜ pending |
| 29-02/T2 | 29-02 | 1 | D-01/D-03 md 빈 dict → breakdown 미방출+점수 byte-불변 | T-29-02-01 | 기준 없는 감점 0=100 위양성 차단 | unit | 위와 동일 파일 (케이스 3) | ✅ W0 (T1 산출) | ⬜ pending |
| 29-02/T2 + 29-05/T2 | 29-02, 29-05 | 1, 3 | D-02 overallScore == breakdown.final 항등 (mode3) + 성장 델타 tally 일관 (sub-clause, 케이스 7) | T-29-02-03 | 100−Σ=final 항등 단언 | unit + Pod sweep | unit(케이스 2·7) + Pod: `PYTHONPATH=shared/python:. python3 evals/phase29/assert_gates.py` (SERIAL, cold/warm 후) | ✅ W0 unit / Pod manual | ⬜ pending |
| 29-03/T1 | 29-03 | 2 | D-08 zoom criterion→region 소스 테스트 작성 (RED — 케이스 5종: leg_extension→legs·arm_extension→arms, improved 억제, record 0, 비매핑 line/fallback 카드 0, 인자 보존) | T-29-03-01 | mock-based, 실 S3/렌더 0 | unit | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_mode3_fault_zoom_selection.py -q` (RED 게이트: exit 1) | ✅ W0 — 이 태스크가 생성 | ⬜ pending |
| 29-03/T2 | 29-03 | 2 | D-08 zoom = 감점 record criterion→region 매핑 소스 (keypoint 필드 아님 — HIGH-1), improved 미방출, record 0/비매핑 → 카드 0, 앱 매핑과 표 일치 | T-29-03-01 | mode1 zoom 무회귀 + cross-side 매핑 SUMMARY 대조 | unit | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_mode3_fault_zoom_selection.py -q && PYTHONPATH=shared/python:. python3 -m pytest tests/ -k "fault_zoom" -q` | ✅ W0 (T1 산출) | ⬜ pending |
| 29-01/T1·T2 | 29-01 | 1 | D-14 부상 대응법 권고 행 + 캡션 | T-29-01-02 | 부상 확정 단정 금지 카피 | typecheck + grep gate | `cd app && npm run typecheck && ! (sed 's/심각도//g' src/components/InjuryRiskSection.tsx \| grep -q "각도")` | ✅ | ⬜ pending |
| 29-04/T1 | 29-04 | 2 | HIGH-1 투영 helper 1벌 (projectDeductionRecordKeypoints) + ipsf_absolute 매핑 (leg_extension→legs·arm_extension→arms·split_angle→legs·line 무투영) | T-29-04-01 | 규칙 사본 0 + fixture-level grep 소스 단언 (JS 러너 부재) | typecheck + grep gate | `cd app && npm run typecheck && grep -q "projectDeductionRecordKeypoints" src/lib/deductionLabels.ts && grep -q "projectDeductionRecordKeypoints" src/app/analysis/result.tsx && ! grep -q "function recordProjectedKeypoints" src/app/analysis/result.tsx && grep -q "leg_extension" src/lib/deductionLabels.ts` | ✅ | ⬜ pending |
| 29-04/T2~T4 | 29-04 | 2 | D-03~07/10 앱 카피·게이트 렌더 분기 | T-29-04-01~03 | 저장 record 그대로 표기 | typecheck + manual | `cd app && npm run typecheck` + HUMAN-UAT (29-08 적립 — power-spin 드릴다운 end-to-end 포함) | ✅ | ⬜ pending |
| 29-06/T2 | 29-06 | 3 | D-09 playback-url reference 재서명 (조건부 fix) — canonical `reference` 컬렉션 + isActive/prefix 가드 (HIGH-2) | T-29-06-01·04·06 | 임의 S3 키 서명 불가 + inactive ref 404 + `reference/` prefix allowlist + 리터럴 컬렉션 0 | unit | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_playback_url_reference.py -q` + `! grep -q "reference_motions" backend/functions/playback-url/app.py` | ✅ W0 — 이 태스크가 생성 | ⬜ pending |
| 29-08/T3 | 29-08 | 4 | D-13 HUMAN-UAT 적립 완결성 (MEDIUM-2) | T-29-08-01 | per-token grep — 약한 집계 grep 금지 | grep gate | `UAT=.planning/phases/29-mode3-result-screen-completion/29-HUMAN-UAT.md; test -f "$UAT" && for t in D-14 D-01 D-06 D-08 D-09 D-10 D-11 D-12 F1 iPad power-spin; do grep -q -- "$t" "$UAT" \|\| exit 1; done` | ✅ (해당 태스크 산출) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_mode3_tally_seam.py` — D-01/D-02/D-03 매트릭스 (md 유/무 × breakdown 방출/점수 항등 × Gemini 무호출 × 델타 소스, 29-02 Task 1 산출)
- [ ] `backend/tests/test_mode3_fault_zoom_selection.py` — D-08 criterion→region 소스·improved 억제·비매핑 카드 0 (29-03 Task 1 산출 — 기존 fault_zoom 테스트 존재 시 확장하고 파일명 SUMMARY 기록)
- [ ] `backend/evals/phase29/` — run_sweep.py + assert_gates.py + eval_keys.json (phase24 6페어 mode3 변형, 29-05 Task 1 산출)
- [ ] `backend/tests/test_playback_url_reference.py` — D-09 조건부 fix unit (29-06 Task 2 산출, TTL 확정 경로 시 — inactive 404·prefix 거부·raw s3Key 무시·analysisId byte-호환 포함)
- 앱 신규 테스트 프레임워크 도입은 하지 않음 (프로젝트 컨벤션 — typecheck + 실기기). HIGH-1 투영 매핑의 fixture-level 검증은 grep 소스 단언(29-04/T1) + 29-03/29-04 SUMMARY 매핑 표 상호 대조 + HUMAN-UAT power-spin 드릴다운으로 3중 커버.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 가로 전환 + 구빌드 폴백 무크래시 | D-11/D-12 | 네이티브 회전 — 자동화 불가 | HUMAN-UAT.md 적립 (batch UAT 원칙 — 즉시 belle 호출 금지) |
| power-spin mode3 드릴다운 end-to-end (내역 행 번호 → 그룹 마커 → legs zoom 매칭) | D-08 + HIGH-1 | 실분석 렌더 경로 — JS 러너 부재로 자동화 불가 | 29-08 HUMAN-UAT 항목 4 (criterion→region 투영 전 구간) |
| D1 비교영상 미표시 재현·규명 | D-09 | 진단 태스크 (Pitfall 4 체크리스트, 29-06 Task 1) | 재현 → presigned TTL 등 원인 규명 → fix |
| Pod sweep 실행 (cold/warm/게이트) | D-02 | 실영상 + GPU Pod — 로컬 자동화 불가 | 29-05 Task 2 절차 (SERIAL, PASS 후에만 서버 재기동 — score-switch 대조표 + 정지 조건 판정 필수, MEDIUM-1) |
| EAS 빌드·제출 성공 | D-13 | 빌드 체인 자체가 검증 | `eas build/submit --non-interactive` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (29-01~29-08 전 태스크 `<automated>` 보유 — 29-06/T1 진단 태스크는 원격 조회 스모크 + 수기 증거 기록)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (신규 테스트 4파일 전부 해당 plan 의 첫/해당 태스크가 생성)
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-synced 2026-07-09 (checker feedback revision + 29-PLAN-REVIEW reviews revision) — 실행 중 Status 열 갱신은 executor 몫
