---
phase: 31
slug: api-visual-correction
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-19
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 31-RESEARCH.md `## Validation Architecture`. Task IDs filled by planner 2026-07-19.

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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 31-01/T1 | 31-01 | 1 | Wave 0 스캐폴드 + DashScope mock | — | N/A | unit | `python -m pytest backend/tests/phase31 -x -q` | 생성 대상 | ⬜ pending |
| 31-01/T2 | 31-01 | 1 | D-05/06 상태 머신 상수·부분 업데이트 | T-31-01 | flat scalar validator 강제 | unit | `python -m pytest backend/tests/phase31/test_silhouette_flow.py -x -q` | 생성 대상 | ⬜ pending |
| 31-01/T3 | 31-01 | 1 | 계약 3면 동기 + /visual/rotation 계약 | T-31-02 | 단일 404 계약 명시 | typecheck | `cd app && npm run typecheck` | ✅ | ⬜ pending |
| 31-02/T1~T2 | 31-02 | 1 | D-03 이미지 모델 실측 선정 | T-31-04/05/06 | 키 리터럴 0, 호출 상한 4 | script+assert | `python -c "import json; ..."` (RESULTS.json 스키마) | 생성 대상 | ⬜ pending |
| 31-03/T1 | 31-03 | 1 | D-11/12 화살표 드로잉 순수 함수 | T-31-08 | degenerate 생략 | unit | `python -m pytest backend/tests/test_fault_zoom_arrow.py -x -q` | 생성 대상 | ⬜ pending |
| 31-03/T2 | 31-03 | 1 | arrow_specs 배선 + 무회귀 | T-31-07 | 채점 read-only | unit | `python -m pytest backend/tests/test_fault_zoom_arrow.py backend/tests/test_fault_zoom*.py -x -q` | ✅ 기존+신규 | ⬜ pending |
| 31-04/T1 | 31-04 | 2 | D-02 어댑터 (HTTP mock, 멱등, 화이트리스트) | T-31-09/10/11 | 키 비로깅, URL 화이트리스트, 재시도 1회 | unit | `python -m pytest backend/tests/phase31/test_visual_gen.py -x -q` | W0 | ⬜ pending |
| 31-04/T2 | 31-04 | 2 | 실루엣 품질 judge (보수 FAIL) | T-31-12 | 불확실=FAIL | unit | `python -m pytest backend/tests/phase31/test_visual_gen.py -x -q` | W0 | ⬜ pending |
| 31-05/T1 | 31-05 | 2 | 목업 선제시 + Open Q3 (checkpoint) | — | N/A | manual (decision) | — | — | ⬜ pending |
| 31-05/T2~T3 | 31-05 | 2 | D-04/10 뷰어 중첩 + 참고코너 컴포넌트 | T-31-14/15 | 에러 배너 0, 점수 미표시 | typecheck | `cd app && npm run typecheck` | ✅ | ⬜ pending |
| 31-06/T1 | 31-06 | 3 | 블러 결정 (checkpoint, Open Q2) | T-31-18 | N/A | manual (decision) | — | — | ⬜ pending |
| 31-06/T2 | 31-06 | 3 | 페어 적재 learningOptIn===true 엄격 | T-31-16 | opt-in strict, uid 미포함 | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x -q` | W0 | ⬜ pending |
| 31-06/T3 | 31-06 | 3 | D-05/08 실루엣 사후 훅 + 조용한 폴백 | T-31-17/19 | 1h presign, judge PASS 필수 | unit | `python -m pytest backend/tests/phase31/test_silhouette_flow.py -x -q` | W0 | ⬜ pending |
| 31-07/T1 | 31-07 | 3 | D-06/07 요청 Lambda auth·한도·202 | T-31-20/21/22 | 토큰 필수, 단일 404, 한도 transaction | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x -q` | W0 | ⬜ pending |
| 31-07/T2 | 31-07 | 3 | 워커 멱등·URL 이관·조용한 폴백 | T-31-23/24/26 | 1h presign, 화이트리스트, 재검증 | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x -q` | W0 | ⬜ pending |
| 31-07/T3 | 31-07 | 3 | IaC (Queue/함수/LogGroup/resolve:ssm) | T-31-25 | SSM SecureString만 | lint | `cd backend && sam validate --lint` | ✅ | ⬜ pending |
| 31-08/T1 | 31-08 | 3 | 회전 요청 클라이언트 (429 daily_limit) | T-31-27 | 인증 fetch | typecheck | `cd app && npm run typecheck` | ✅ | ⬜ pending |
| 31-08/T2 | 31-08 | 3 | D-08/09 섹션 통합 + 상태 소비 (폴링 0) | T-31-28/29 | busy 이중 방어, 조용한 실패 | typecheck | `cd app && npm run typecheck` | ✅ | ⬜ pending |
| 31-09/T1 | 31-09 | 4 | 전체 suite + sam build | — | N/A | full suite | `sam validate --lint && python -m pytest backend/tests -q` | ✅ | ⬜ pending |
| 31-09/T2 | 31-09 | 4 | belle sam deploy (checkpoint) | T-31-30 | 수동 배포 게이트 | manual (human-action) | — | — | ⬜ pending |
| 31-09/T3 | 31-09 | 4 | 배포 후 401 + 워커 실호출 + OTA + UAT 적립 | T-31-31/32 | 무토큰 401 실검증 | integration | `test -f 31-HUMAN-UAT.md && grep D-10` | 생성 대상 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase31/` 디렉터리 + test_visual_gen.py / test_silhouette_flow.py / test_visual_request.py / test_pair_store.py 스텁 (phase22/ 디렉터리 선례) — **31-01/T1**
- [ ] DashScope HTTP mock fixture (urllib 레벨 monkeypatch — 스파이크 코드가 순수 stdlib 라 mock 용이) — **31-01/T1 conftest**

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실기기 UX — D-09/10 반투명 중첩·회전 카드 렌더/제스처 | D-09/D-10 | 실기기 렌더/제스처는 자동화 불가 | HUMAN-UAT.md 적립 — 즉시 belle 호출 금지, phase 31 후 배치 UAT ([[batch-uat-after-phase-31]]) — 31-09/T3 |
| 실루엣 자동 생성 실 E2E | D-05 | 신규 분석은 GPU Pod 필요 (전부 OFF — 의도적) | Pod 재생성 + DASHSCOPE_API_KEY env 주입 후 신규 분석 1건 — 31-09 SUMMARY 에 이월 박제 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (checkpoint 3건은 belle 게이트)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (31-01/T1)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner 2026-07-19 (task map filled)
