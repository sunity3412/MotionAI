---
phase: 33-result-trust-recovery
plan: 01
subsystem: testing
tags: [firestore, firebase-admin, fault-zoom, a0-gate, phase33, observation-only]

# Dependency graph
requires:
  - phase: 25-scoring-sweep
    provides: "backend/evals/phase25/baseline/phase25_sweep_report.json (12-member pointed/shown/measured 데이터)"
  - phase: 32-result-readability
    provides: "belle 실 doc 071df… (ref-power-spin fault, faultZoomComparisons 3장, 2026-07-22 crop)"
provides:
  - "backend/tests/phase33/conftest.py — phase33 백엔드 테스트 sys.path scaffold"
  - "backend/scripts/dump_analysis_doc.py — Firestore 분석 doc 덤프 CLI (get_analysis 재사용, --download-pngs)"
  - "33-A0-EVIDENCE.md — 6동작 전수 대조 + D-04 판정 '어긋남 큼' (HALT)"
affects: [33-02, 33-03, 33-04, 33-05, ref-student-substrate-gap, C+M3, phase33-replan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "관찰 전용 Firestore 덤프 = 기존 firestore_admin.get_analysis 재사용, firebase-admin 직접 init 금지"
    - "산출물 눈으로 확인(D-19) = presigned URL crop PNG 를 디스크로 내려 실제로 엶"

key-files:
  created:
    - backend/tests/phase33/conftest.py
    - backend/scripts/dump_analysis_doc.py
    - .planning/phases/33-result-trust-recovery/33-A0-EVIDENCE.md
  modified: []

key-decisions:
  - "A-0 D-04 판정 = 어긋남 큼 → phase 33 HALT + C+M3 substrate 트랙 편입 re-plan (측정 판정, belle 질문 아님)"
  - "empty window_joints 를 정합으로 세지 않음 (Pitfall 3) — 측정 기반 부재 자체가 어긋남 신호"

patterns-established:
  - "A-0 게이트: pointed(faultJoints) / shown(criterion) / measured(window_joints) 3집합 + crop PNG 눈확인으로 substrate vs 표현 분기"

requirements-completed: [D-03, D-04, D-11, D-18, D-19, D-20]

# Metrics
duration: ~20min
completed: 2026-07-23
---

# Phase 33 Plan 01: A-0 분석 출력 정확성 게이트 Summary

**belle 실 doc + baseline sweep 전수 대조 결과 pointed/shown/measured 3집합이 전 fault 멤버에서 불일치하고 실측 substrate 가 부재하며 crop PNG 3장의 기준-학생 국면이 어긋나 있어 D-04 판정 = "어긋남 큼" → phase 33 HALT + C+M3 substrate 편입 재계획**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-23 (Phase 33 execution)
- **Completed:** 2026-07-23
- **Tasks:** 2
- **Files modified:** 3 created, 0 modified

## Accomplishments
- Wave 0 substrate 구축: `backend/tests/phase33/conftest.py`(phase32 선례 복사) + `backend/scripts/dump_analysis_doc.py`(get_analysis 재사용 관찰 덤프 CLI, `--download-pngs`).
- belle 실 doc(`ref-power-spin` fault, mode1, overall 51)을 값으로 덤프: pointed=[LS,RS,LH,RH,LK,RK], shown=[leg_extension, split_angle, a_v_r\_\_left_shoulder], measured(`seedObservation`)=**통째 null**, crop 3장(left_shoulder/left_hip/left_hand).
- crop PNG 3장 실제로 열어 확인(D-19): 기준(정은지)측 마커 0(결함①), 국면 어긋남(결함④), 세 카드 같은 프레임 쌍 34/90(결함③), 배지 픽셀 구움(결함⑥), 결함⑤(split source=vision → faultJoints 전체 투영 → 어깨 크롭) 구조 재현.
- D-04 분기 판정 문서화: **어긋남 큼** → HALT.

## Task Commits

1. **Task 1: Wave 0 substrate — conftest + doc-dump helper** - `d074182` (feat)
2. **Task 2: A-0 gate — 6동작 전수 대조 + D-04 판정** - `669d4aa` (docs)

## Files Created/Modified
- `backend/tests/phase33/conftest.py` - phase33 백엔드 테스트 sys.path scaffold(_LAYER 주입)
- `backend/scripts/dump_analysis_doc.py` - uid/analysisId 키 Firestore 덤프; faultJoints/criterion/faultZoomComparisons 원문 방출 + presigned crop PNG 다운로드
- `.planning/phases/33-result-trust-recovery/33-A0-EVIDENCE.md` - 6동작 전수 대조 표 + belle crop 3장 눈확인 + D-04 판정

## A-0 D-04 판정 (verbatim)

> **어긋남 큼**
>
> 세 집합(pointed/shown/measured)이 전 fault 멤버에서 불일치하고, 대조 기준선인 실측(window_joints)이
> 사실상 부재하며(belle 실 doc 은 seedObservation 통째 null), belle 실 doc crop 3장을 실제로 열어보니
> 기준(정은지) 프레임이 학생과 다른 국면으로 쌍지어져 있다(국면 어긋남 = ref↔student substrate 결함).
> 이는 표현 계층(joint-exact join·캡션·phrasebook)으로 치유되지 않는 분석 substrate 문제다.

## HALT + 재계획 권고 (BRANCH CONTROL, D-04)

**이 phase 는 여기서 HALT 한다.** 33-02+ 표현 계층 플랜(기준자세 표·코칭 문구·확대비교·영상 표시·
일러스트)으로 진행하지 말 것. planner 로 돌아가 **C+M3 substrate 트랙
(`.planning/debug/ref-student-substrate-gap.md`)을 phase 33 에 편입**한 뒤, 어떤 표현 작업보다 먼저
ref↔student 정합(기준 프레임 국면 대응 + 실측 window substrate 복원)을 해결해야 한다. 이 분기는
belle 질문이 아니라 Claude 실측 판정이다(D-01/D-04). C+M3 편입도 채점 산식·임계값 무접촉(D-20) —
substrate(프레임 정합·window 측정) 복원 트랙이다.

## Decisions Made
- **empty-window 를 "정합"으로 세지 않음(Pitfall 3):** 측정 substrate 붕괴로 pointed·measured 가 fallback 상위집합으로 우연히 겹쳐 보이는 것은 정합이 아니라 어긋남 신호. 이 규칙이 없었다면 belle doc 의 seedObservation=null 을 무시하고 "작음"으로 오판할 수 있었음.
- **판정을 belle 에 묻지 않고 측정으로 결정(D-04):** crop 3장을 직접 열어 국면 어긋남을 눈으로 확인한 것이 판정의 결정적 증거.

## Deviations from Plan

None - plan executed exactly as written. 두 태스크 모두 계획대로 실행. 채점/분석 코드(`backend/shared/.../analysis/`) 무접촉 확인(D-20): 커밋 diff 는 `backend/tests/phase33/`, `backend/scripts/`, `.planning/` 만 포함.

## Issues Encountered
- climb 동작은 sweep 에서 status=`comparison`(mode3)라 채점 substrate 부재 → 전수 대조에서 joint-set 을 얻을 수 없음. 표에 "empty (source: mode3 comparison)"로 명시하고 D-23 대체 검증 필요로 기록(조작·추정 없음, D-18).
- `seedObservation` 이 belle 실 doc 에서 통째 부재 → measured 를 null 로 노출(삼키지 않음, D-18). 이것 자체가 A-0 finding.

## User Setup Required
None - no external service configuration required. (Firestore admin creds `FIREBASE_SA_PATH=firebase-sa.json` 로컬 존재, 하드코딩 0.)

## Next Phase Readiness
- **BLOCKED (의도된 HALT):** 33-02+ 는 A-0 판정 "어긋남 큼"으로 인해 진행 불가. planner 재진입 필요.
- **재계획 입력 준비 완료:** `ref-student-substrate-gap.md`(C+M3 트랙) + `33-A0-EVIDENCE.md`(근거) + `dump_analysis_doc.py`(재사용 가능 관찰 도구).
- Pod `rbpnmxhbfoeg35` OFF — C+M3 재분석/재-sweep 은 Pod 재기동 전제(belle-gated, D-25).

## Self-Check: PASSED

- Files: conftest.py / dump_analysis_doc.py / 33-A0-EVIDENCE.md / 33-01-SUMMARY.md — all FOUND.
- Commits: d074182 (Task 1) / 669d4aa (Task 2) — all FOUND.
- D-20: `git diff --stat` under `backend/shared/**/analysis/**` = empty (채점/분석 산식 무접촉 확인).

---
*Phase: 33-result-trust-recovery*
*Completed: 2026-07-23*
