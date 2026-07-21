---
phase: 32
slug: result-readability-3-omni
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-21
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 32-RESEARCH.md §Validation Architecture (2026-07-21).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest >=8,<9 (`backend/requirements-dev.txt`), 테스트 루트 `backend/tests/` (phase별 디렉터리 관례) |
| **Framework (app, 정적)** | `npm run typecheck` (tsc --noEmit, strict) — 유일한 앱 정적 게이트 |
| **Framework (app, 로직)** | `node --test app/src/lib/*.test.ts` (Node 24 type stripping, node:test/node:assert — 신규 러너 금지) |
| **Config file** | `backend/requirements-dev.txt`, `app/tsconfig.json` (기존 — Wave 0 설치 불필요) |
| **Quick run command** | `cd backend && python -m pytest tests/phase32 -x -q` (Wave 0 신설) |
| **Full suite command** | 백엔드 전체 baseline 대비 diff (FAILED/ERROR node-ID baseline 비교 — 57 failed/3366 passed baseline 초과 금지, 31-CLOSEOUT 기록) + `npm run typecheck` |
| **Estimated runtime** | quick ~10s / full ~수 분 (백엔드 전체) |

---

## Sampling Rate

- **After every task commit:** 영향 phase 디렉터리 pytest (`pytest tests/phase32 -x -q`) + `npm run typecheck` (+해당 시 `node --test`)
- **After every plan wave:** 백엔드 전체 baseline diff + typecheck + 시뮬레이터 화면 진입 확인 (UI wave)
- **Before `/gsd-verify-work`:** Full suite green (baseline 초과 0) + fixture 6동작 전수 스윕(엔진 웨이브, Pod 순차 — kip-up 편중 금지)
- **Max feedback latency:** ~60초 (quick run 기준)

---

## Per-Task Verification Map

> Task ID는 PLAN.md 확정 후 planner가 기입. 아래는 결정(D-XX) 기준 사전 맵.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 1 | D-16 사다리 재배치 (low_global_confidence → trim_only + anchors 보존, degenerate만 disabled) | — | N/A | unit | `pytest backend/tests/phase32/test_motion_alignment_ladder.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | D-16 수동 오프셋 클램프·warp 합성 순수 계산 | — | N/A | unit (app) | `node --test app/src/lib/__tests__/manualOffset.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | D-20 relaxed 프레이밍 margin=1.0·마커 게이트 유지 | — | N/A | unit | `pytest backend/tests/phase32/test_fault_zoom_crop_parity.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | D-03 겹침 수리 — lineHeight ≥ fontSize 정적 검사 | — | N/A | grep/unit + manual | 스타일 grep 게이트 + typecheck + 시뮬레이터/실기기 | ❌ W0 | ⬜ pending |
| TBD | TBD | 2+ | D-11/D-09 문구집 금지어(수치 헤드라인·% 환산·일반론 패턴) grep 게이트 | — | N/A | unit | `pytest backend/tests/phase32/test_phrasebook_forbidden.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 2+ | D-19/D-27 미션 선정 우선순위·streak 체인 순수 함수 | — | N/A | unit | `pytest backend/tests/phase32/test_mission_rules.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 엔진 | D-22 RTMW keypointReport 12관절 방출·validator·하위호환(8관절 doc) | — | N/A | unit | `pytest backend/tests/phase32/test_keypoint_report_expansion.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 엔진 | D-23 스팟체크 불일치 → 카드 숨김 플래그·로그 (graceful 실패 = no-op) | — | 외부 API 실패 시 분석 결과 훼손 금지 | unit + Pod | 로컬 unit + Pod fixture 6동작 순차 스윕 | ❌ W0 / Pod | ⬜ pending |
| TBD | TBD | 엔진 | D-22 PR 인버전 조건부 적용·비인버전 무회귀 | — | N/A | Pod sweep | fixture 6동작 순차 (kip-up 편중 금지) | Pod manual | ⬜ pending |
| TBD | TBD | 2+ | 계약 3면 신규 필드 lockstep (contract.md + analysis.ts + models.py) | — | N/A | unit | 기존 lockstep 테스트 패턴 확장 | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase32/` 디렉터리 + 위 표 unit 테스트 파일 일체
- [ ] 앱 순수 로직 테스트 파일 (`node --test` 규약 — .ts 확장자 import 명시)
- [ ] 문구집 fixture 스키마 + 금지어 목록 (copy_templates FORBIDDEN_PHRASES 확장)
- 프레임워크 설치: 불필요 (pytest·tsc·node --test 전부 기존)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 겹침 수리 실렌더 확인 | D-03 | Expo Go/typecheck가 렌더 겹침을 못 잡음 (실증: [[verify-ui-on-simulator-before-ota]]) | 시뮬레이터 결과 화면 진입 → 참고 지표 카드 줄겹침 없음 확인 → belle 실기기 |
| 동작 비교 형태·자세 카드 존폐·큐 밀도 | D-17 실물 게이트 | "고장난 현행 위에서 판단 불가" — wave-1 수리 후에만 판단 가능 | wave-1 수리 후 belle 실기기 리뷰에서 그 자리 확정 |
| TTS 목소리 방식 | D-18 샘플 게이트 | belle 청취 판단 필요 | 같은 코칭 문장 음성 샘플 2종(기기 TTS vs 클라우드 TTS) 제작 → belle 청취 |
| 일러스트 품질 | D-21 샘플 게이트 | belle 품질 판단 필요 | 샘플 제작 → belle 검수, 미달 시 실프레임+텍스트 폴백 |
| 상세 섹션 순서안 | D-02 리서치 게이트 | belle 확인 게이트 (RESEARCH.md 근거 제시 완료) | 순서안 + 근거 제시 → belle 확인 |
| 게임 프레임 적용 범위·강조 체계·참고 지표 형태 | D-03/D-05/D-10 목업 게이트 | belle 목업 비교 결정 필요 | sketch 목업 2~3안 + 추가 아이디어 → belle 결정 |
| PR 인버전·스팟체크 실영상 검증 | D-22/D-23 | GPU(Pod) 필수 — 로컬 CPU에서 NaN | Pod fixture 6동작 순차 스윕, 동시 호출 금지 |
| OTA 적용 확인 | 전 UI 변경 | expo-updates는 재실행 2회째 적용 | 시뮬레이터 확인 → OTA 발행 → 완전 종료 2회 재실행 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
