---
phase: 28
slug: dtw-motion-based-alignment
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-07
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 28-RESEARCH.md §Validation Architecture (2026-07-07).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8 (backend) / `tsc --noEmit` (app — JS 테스트 러너 없음) |
| **Config file** | 없음 (관례 실행) |
| **Quick run command** | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_motion_alignment.py -q` |
| **Full suite command** | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` (pre-existing failure ~54건 — affected-tests 스코프 비교 판정) + `cd app && npm run typecheck` |
| **Estimated runtime** | quick ~20s / full ~3min |

---

## Sampling Rate

- **After every task commit:** 해당 신규 테스트 quick run + `npm run typecheck` (앱 변경 시)
- **After every plan wave:** `pytest tests/ -q -k "alignment or fault_zoom or pipeline"` (affected 스코프, 신규 FAILED/ERROR 0)
- **Before `/gsd-verify-work`:** affected 스코프 green + typecheck green + 실기기 manual 항목 belle 확인
- **Max feedback latency:** ~180s

---

## Per-Task Verification Map

> REQ ID 미발급 시점 작성 — CONTEXT 결정(D-NN) 기준. 플랜 생성 후 태스크 ID로 구체화.

| 결정 | Behavior | Test Type | Automated Command | File Exists | Status |
|------|----------|-----------|-------------------|-------------|--------|
| D-01/계약 | build_motion_alignment: 앵커 단조·초 단위·결정론·identity path→기울기 1.0 | unit (순수) | `pytest tests/test_motion_alignment.py -q` | ❌ W0 | ⬜ |
| D-01 fps | user 9fps/ref 18fps 합성 path → rSec = idx/18 정확 (fps 도메인 회귀 가드) | unit | 동일 파일 | ❌ W0 | ⬜ |
| D-02/D-03 | tier 사다리: distance 8.0/25.0 경계 + 기울기 클램프 위반 → trim_only 강등 + 임계 출처 주석 grep | unit + grep | 동일 파일 + `grep -c "vision_veto\|_ALIGN_GLOBAL"` ≥1 | ❌ W0 | ⬜ |
| D-04 | 시간비례 근사 제거(grep 0) + 대응 실패 시 전신 폴백 + refMatch 플래그 | unit | `pytest tests/test_fault_zoom*.py -q -k match` | 기존 확장 | ⬜ |
| 채점 무접촉 | alignment 방출 유무 무관 overallScore/deductionBreakdown 동일 | unit (pipeline mock) | `pytest tests/ -q -k "alignment and score"` | ❌ W0 | ⬜ |
| 계약 | validator: 앵커 길이 상한·flat scalar + 3-way lockstep grep | unit + grep | `grep -c motionAlignment analysis.ts models.py docs/contract.md` 각 ≥1 | ❌ W0 | ⬜ |
| 워핑 수학(앱) | warpTime/segmentRate 순수 함수 | typecheck | `cd app && npm run typecheck` | ✅ 명령 존재 | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_motion_alignment.py` — 앵커/tier/fps/결정론/채점무접촉 스텁
- [ ] D-04 회귀 가드 테스트 — `test_fault_zoom_deferred.py` 확장 또는 신규 (**27-06 실행 시 같은 파일 존재 — 조율 필수**)
- [ ] **reference doc 1개 실측**: `anglesFrames / keypointReport.fps ≈ 영상초` (fps 도메인 가정 A1 해소 — 1회성 Admin 읽기 스크립트)
- [ ] `app/src/lib/alignmentWarp.ts` 골격 (typecheck 진입)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| power-spin 페어 워핑 재생 체감 | D-01 | expo-video rate 반응성은 기기 의존 (문서 미명세) | belle 실기기: 중반 템포 추종·rate 경계 stutter 없음·스크럽 후 동기 유지 |
| legacy 배너 / 신규 tier 배지 | D-05/D-02 | UI 노출·라우팅은 실기기 관찰 | legacy doc → 배너+CTA / 신규 doc → tier별 카피 확인 |

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

## 불변 제약

- **채점 무접촉 hard** — 이 phase는 표현/재생 정렬만. veto still 경로(`_build_selected_frame_pair`)의 fps fix는 채점 인접이라 **이번 phase 제외** (belle 통지 항목 — 28-RESEARCH Open Question 2).
- 정렬 데이터는 complete_analysis 페이로드 동승 (27-06의 "complete 후 result.* write 금지" 게이트와 정합).
- Firestore flat + 앵커 길이 상한 (40k index-entry 한도 회피).
