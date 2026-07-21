---
phase: 32-result-readability-3-omni
plan: 09
subsystem: backend-pipeline
tags: [emission, phrasebook, mission-loop, coach-questions, summary-praise, pod-deploy, d23-sweep, tdd, python]

# Dependency graph
requires:
  - phase: 32-05
    provides: "승인 문구집 phrasebook.json + assemble_phrases/assemble_safety_phrases (D-08/D-11 골격 원천)"
  - phase: 32-06
    provides: "mission.py 순수 함수(D-19/D-26/D-27) + models 계약 상수 + scoped validator 4종"
  - phase: 32-03
    provides: "Pod 6seluxc43awmqi 가동 + 32-03 post 스윕 기준선 (runId 1784623086, /workspace/eval32/post)"
provides:
  - "_process 방출 배선 — 새 분석 result에 recordId·3단 문구·tolerance·mission(baseline)·missionOutcome·summaryPraise·coachQuestions (프로덕션 라이브)"
  - "phrasebook.assemble_praise — 잘한 점 단일 원천 (mission_improved > clean_dimension > criteria_met, D-09 무수치 헤드라인)"
  - "coach_writer 가변부 슬롯 한정 + FORBIDDEN 런타임 필터 (D-11 — LLM이 골격을 소유할 수 없는 구조)"
  - "6동작 전수 스윕 diff 0 실측 + mode3 연쇄 실데이터 doc (32-11 시뮬레이터·32-12 실기기 검증 입력)"
affects: [32-10 (3단 문구·tolerance 게이지 렌더), 32-11 (요약 카드·미션·질문 배선), 32-12 (실기기), 32-13 (recordId 스팟체크 조인)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "방출 배선 = complete_analysis 직전 단일 helper(_attach_translation_emission), 항목 단위 try 격리 + 상위 try (motionAlignment 선례 확장)"
    - "LLM 출력 사후 금지어 필터 = phrasebook FORBIDDEN 상수 단일 출처의 런타임 판 (grep 게이트와 동일 재료)"
    - "D-23 스윕 = 같은 Pod·같은 CPU EP 기질에서 32-03 post 기준선과 diff 비교 + fetch_docs 방출 필드 readback + mode3 연쇄(전용 uid)로 prev 체인 실측"

key-files:
  created:
    - backend/tests/phase32/test_pipeline_emission.py
  modified:
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/analysis/phrasebook.py
    - backend/shared/python/sunity_shared/analysis/coach_writer.py

key-decisions:
  - "clean_dimension 칭찬은 감점 record가 매핑된 차원을 제외 (criterion→dimension 매핑) — dimensionScores 100이어도 감점 내역과 모순되는 칭찬 차단 (D-06)"
  - "mode3의 angle 차원은 clean_dimension 칭찬 후보에서 제외 — 이전 영상 유사도라 '잘한 점' 근거 아님 ([[mode3-overall-exclude-angle-similarity]])"
  - "failClosed 마커는 record에 미방출 — record 계약(§12.3) 밖. fail-closed는 cueLine/exerciseId 부재로 판별"
  - "collect_unmeasured_signals 입력 = deductionBreakdown 전체 — 실측상 미측정 신호가 records가 아닌 coverageGaps에 실리기 때문 (docstring에 실존 필드 기록)"
  - "praise 헤드라인 상수를 rendered_copy_strings 게이트 scope에 포함 — 코드 상수 카피도 D-09 금지어 테스트 상시 커버"

patterns-established:
  - "새 result 필드 방출 = 골격 카피는 phrasebook 소유, 파이프라인은 조립·병합만 (LLM은 지정 슬롯 밖 접근 0)"

requirements-completed: [D-08, D-11, D-19, D-26, D-27, D-28, D-29, D-23]

# Metrics
duration: ~2h 30m (스윕 75분 + mode3 연쇄 2회 35분 대기 포함)
completed: 2026-07-21
---

# Phase 32 Plan 09: 파이프라인 방출 배선 + Pod 배포·전수 스윕 Summary

**32-05 문구집·32-06 미션 엔진을 `_process`에 배선해 새 분석부터 recordId·3단 문구·tolerance·미션(baseline)·summaryPraise·코치 질문이 result로 방출되게 하고(항목 단위 격리·LLM 무관 골격 성립), Pod 배포 후 6동작 전수 스윕 점수 diff 0 + mode3 연쇄(streak 1→2→3, coach_card, missionOutcome improved 양방향, praise 3원천 전부)로 프로덕션 실측 증명 — 리뷰 blocker 2 해소, 32-11/32-12가 실데이터 doc을 갖게 됨**

## Task Commits

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | _process 방출 배선 (recordId·3단·tolerance·미션·praise·질문, 항목 격리) + assemble_praise | `518b686` |
| 2 (RED) | 방출 통합 테스트 14건 + coach_writer 슬롯 게이트 RED 3건 | `793ce5b` |
| 2 (GREEN) | coach_writer 가변부 한정 프롬프트 + FORBIDDEN 런타임 필터 | `ee41ca3` |
| 3 | Pod 배포 + 전수 스윕 + mode3 연쇄 (코드 무수정 — 본 SUMMARY가 기록) | (docs 커밋) |

## Accomplishments

### Task 1 — 방출 배선 (`_attach_translation_emission`, complete_analysis 직전)

- **recordId 각인**: `r{i:02d}:{criterion}` 형식, 방출 시 1회 (문구 조립 실패와 독립).
- **3단 문구 병합**: `assemble_phrases(motion_id, criterion, ruleId)` 슬롯을 record 단위 try/except로 병합 — 한 record 실패는 그 record만 문구 없이 통과. 기존 키 무변경(setdefault), `failClosed` 마커는 계약 밖이라 미방출.
- **tolerance**: `ipsf_criteria.CRITERION_GROUPS` 실존 상수만 (미등재 criterion은 키 생략 — 자의 수치 0).
- **미션 체인**: prev = 기존 mode3 `get_previous_analysis` 결과 재사용 (신규 쿼리 0, where 절 추가 0). `select_mission`/`derive_mission_outcome` 순수 함수 호출만.
- **summaryPraise**: `phrasebook.assemble_praise` (신규) — mission_improved > clean_dimension > criteria_met > None. 헤드라인 무수치(D-09), 수치는 evidenceValue/evidenceUnit 분리.
- **coachQuestions**: safety(항상) + mission_stuck(coach_card 시 record coachQuestion, recordId 조인) + unmeasured(`collect_unmeasured_signals` adapter — 실존 신호 = coverageGaps 6필드 + `quantification_unavailable_dimension_overall` record, dimensionExplanation에는 미측정 서술 실존하지 않음을 docstring에 실측 기록). dedup + 상한 10.
- 전부 result 안 — complete_analysis kwarg diff 0. 상위 try로 방출 전체 실패에도 분석 완주 (SP-3/T-32-20).

### Task 2 — coach_writer 가변부 한정 (TDD)

- 시스템 프롬프트 `[가변부 슬롯 한정 — 문구집 골격 보호]` 조항: 골격=승인 문구집 소유 명시, 허용 가변부 3종(실측 수치 연결/조사·어미 자연화/응원 톤), 일반론·범용 표어 생성 금지 명문화.
- LLM 출력 사후 필터: `FORBIDDEN_PHRASES_PHRASEBOOK` + `FORBIDDEN_REGEX_PHRASEBOOK` 위반 entry 통째 폐기 → 골격/수치 폴백 (모듈 로드 시 1회 컴파일).
- 조립 순서 구조화: 골격 먼저(phrasebook), writer 산출은 tips/detail 지정 슬롯만 — records 3단 병합 경로 0.
- 테스트 17건 (behavior 6 + fail-closed/격리/전체실패/mode1 생략 + coach_writer 4): 전부 green. 기존 coach_writer 계열 57건 무회귀.

### Task 3 — Pod 배포 + D-23 전수 스윕 + mode3 연쇄 실측

**배포**: push `4a0c668..ee41ca3` → Pod `6seluxc43awmqi` git pull(`ee41ca3`) → `__pycache__` 청소 + 서버 재기동 → `/health` 200 (`pipeline_loaded: true`). 배포 전 `/health` 200 확인 완료.

**6동작 전수 스윕** (phase25 harness, 13멤버 SERIAL, uid=phase25eval, runId `1784636486`, CPU EP 기질 = 32-03 post와 동일, RTMW_DETERMINISTIC=1, Gemini 캐시 warm):

| motion | fault 점수 (기준→신규) | correct (기준→신규) | records 방출 (fault) | 3단/tol/cue | mission | praise (correct) | validator |
|---|---|---|---|---|---|---|---|
| power-spin | 55 → **55** | 100 → **100** | 3 (r00:leg_extension, r01:split_angle, r02:angle_vs_reference__left_shoulder) | 3/3 · 3 · 3 | max_deduction | clean_dimension | PASS |
| peter-pan | 79 → **79** | 100 → **100** | 3 | 3/3 · 3 · 3 | max_deduction | clean_dimension | PASS |
| elbow-twist-sister | 66 → **66** | 100 → **100** | 7 | 7/7 · 7 · 7 | max_deduction | clean_dimension | PASS |
| pdshape | 58 → **58** | 100 → **100** | 7 | 7/7 · 7 · 7 | max_deduction | clean_dimension | PASS |
| kip-up | 80 → **80** | 100 → **100** | 1 (r00:split_angle, cap −20) | 1/1 · 1 · 1 | max_deduction | clean_dimension (fault도 발화) | PASS |
| climb | gate → gate (NotPole) | gate → gate | — (failed doc, 방출 없음 — 정상) | — | — | — | PASS |

- **DIFF_MEMBERS=0** — 점수·verdict·activatedCriteria·errorCode·status 전 멤버 32-03 post 기준선과 동일 (방출은 additive, 채점 무접촉 실증). cold-rerun(pdshape) selection_identical=true.
- **타이밍**: 멤버별 timingsMs 합 기준선 대비 ±4% 이내 노이즈 (예: power-spin fault 224.5s→223.5s, pdshape fault 436.9s→453.3s — RTMW/네트워크 편차 범위. 방출 조립은 순수 dict 계산이라 유의미 기여 없음).
- fault 멤버 mission의 baseline 필드(baselinePoints/baselineDeviation/targetValue/unit) 전부 방출 확인. success 멤버 mission 없음 (결함 0 = 미션 fabrication 0).

**mode3 연쇄 실측** (uid=phase32emit, runId `1784641056`, power-spin fixture, SERIAL):

| run | doc | mission | missionOutcome | summaryPraise |
|---|---|---|---|---|
| fault#1 | `chainfault11784641056` | streak 1, max_deduction, baselinePoints 20.0, baselineDeviation 38.95, targetValue 180 | (첫 분석 — 생략) | None |
| fault#2 | `chainfault21784641056` | **streak 2, repeat, escalation exercise_detour** (D-27 2회차) | **improved=false**, deltaPoints 0.0 (결함 잔존 정직) | None (line 차원 감점 매핑 차단 — 모순 칭찬 0) |
| correct#1 | `chaincorrect11784641056` | None (결함 0) | **improved=true, deltaPoints 20.0** (지난 미션 faultKey 소멸) | **mission_improved** — 무수치 헤드라인 + evidenceValue 20.0/points 분리 (D-26 루프 닫힘) |
| correct#2 | `chaincorrect21784641056` | None | (prev 미션 없음 — 생략) | **criteria_met** |

**streak-3 연쇄** (uid=phase32emitb, runId `1784642411`, fault ×3):

| run | mission | coachQuestions |
|---|---|---|
| streak#1 | streak 1, escalation none | — |
| streak#2 | streak 2, **exercise_detour** | — |
| streak#3 | **streak 3, coach_card** (D-27 3회차 승격) | **[{text: "무릎을 끝까지 펴려면 어디에 힘을 줘야 하는지 강사님께 여쭤보고 싶어요", source: "mission_stuck", recordId: "r00:leg_extension"}]** (D-28 자동 등재 + recordId 조인 실측) |

- praise 3원천(mission_improved/clean_dimension/criteria_met) 전부 프로덕션 doc에서 실측. coachQuestions의 safety/unmeasured 원천은 이번 fixture 데이터에 트리거 조건(안전 플래그·커버리지 갭)이 없어 미발화 — 정직한 부재이며 단위 테스트(behavior 2·unmeasured adapter)가 커버.

**신규 계약 doc id 목록 (32-11 시뮬레이터 / 32-12 실기기 검증 입력)**:

- mode1 스윕 (`users/phase25eval/analyses/…`): `powerspinFault1784636486` · `powerspinCorrect1784636486` · `peterpanFault…` · `peterpanCorrect…` · `elbowtwistsisterFault…` · `elbowtwistsisterCorrect…` · `pdshapeFault…` · `pdshapeCorrect…` · `kipupFault…` · `kipupCorrect…` · `pdshapeColdCorrect…` (접미 전부 `1784636486`; climb 2건은 failed doc)
- mode3 연쇄 (`users/phase32emit/analyses/…`): `chainfault11784641056` · `chainfault21784641056` · `chaincorrect11784641056` · `chaincorrect21784641056`
- streak-3 (`users/phase32emitb/analyses/…`): `streak11784642411` · `streak21784642411` · `streak31784642411` (streak3 = coach_card + coachQuestions 보유 doc)
- 스윕 산출물: Pod `/workspace/eval32/emit/phase25/phase25_sweep_report.json` + `emit_docs.json` + `emit_mode3_chain.json` + `emit_streak3.json` + 로그 3종 (repo 밖 — 커밋 baseline 무접촉)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] clean_dimension 모순 칭찬 차단 (criterion→dimension 매핑)**
- **Found during:** Task 1 (스모크 — line 감점 record 존재 + dimensionScores.line=100 조합에서 line 칭찬 발화)
- **Issue:** vision-측정 substrate는 dimension 산식과 다른 경로로 감점할 수 있어, 점수 100 차원에도 감점 record가 실릴 수 있음 — "라인 감점 없음" 칭찬이 감점 내역과 모순 (D-06 위반)
- **Fix:** `_CRITERION_TO_DIMENSION` 매핑으로 실감점 record가 매핑된 차원을 칭찬 후보에서 제외 + mode3 angle 차원 제외
- **Files modified:** backend/functions/pipeline/app.py
- **Commit:** `518b686`

**2. [Rule 2 - 계약 준수] collect_unmeasured_signals 시그니처 조정**
- **Found during:** Task 1 (실존 신호 코드 실측 — 플랜의 "records의 coverage_gap 계열" 서술과 달리 커버리지 갭은 records가 아닌 `deductionBreakdown.coverageGaps`에 실림)
- **Fix:** 첫 인자를 records가 아닌 breakdown 전체로 받아 coverageGaps+records 양쪽 신호를 소비. 실존 필드(coverageGaps 6키, fallback record ruleId, dimensionExplanation 미측정 서술 부재)를 docstring에 기록 — 플랜의 "실존 신호를 코드 실측·기록" 지시 그대로 이행
- **Files modified:** backend/functions/pipeline/app.py
- **Commit:** `518b686`

**3. [테스트 스펙 정정] Test 6 기대값 수정 (RED 중)**
- 결함 잔존 입력에서 mission_improved를 기대한 내 테스트 스펙 오류 → improved=false + clean_dimension 폴백이 정답 (구현 정상). 테스트만 수정.

### 플랜 외 추가 실측 (additive)

- **streak-3 연쇄 1회 추가** — 플랜 acceptance는 mode3 1건의 outcome·praise면 충족이나, coach_card 미션 + coachQuestions를 보유한 **프로덕션 doc**이 없으면 32-11 UI 검증 실데이터가 비므로 fault ×3 연쇄(uid phase32emitb)로 생성. 코드 무접촉.

### 사전 실재 환경 실패 (본 플랜 무접촉 — baseline 동일)

- `tests/pipeline/test_pipeline_phase{8,9}.py` 15건: `ModuleNotFoundError: imageio` (로컬 dev env에 어댑터 의존성 미설치 — requirements-dev 범위 밖, Pod에서는 실행됨)
- 회귀 selection(`-k "firestore or lockstep or contract or motion_alignment or deduction"`) = **425 passed / 1 failed / 12 collection errors** — 32-06 기록과 정확히 동일 (baseline 초과 실패 0)

## Verification

- `pytest tests/phase32` → **93 passed** (기존 79 + 신규 14) ✓
- coach_writer 계열 회귀 (test_coach_writer/gemini v2/phase13/assemble) → 57 passed ✓
- Pod `/health` 200 (배포 전·후·스윕 후) ✓
- 6동작 스윕 DIFF_MEMBERS=0 + 전 doc validator PASS + recordId·3단·tolerance 방출 ✓
- mode3 연쇄: mission streak 체인 + missionOutcome 양방향 + praise 3원천 + coach_card 질문 실측 ✓
- STATE.md/ROADMAP.md 무접촉 (orchestrator 소관) ✓

## Self-Check: PASSED

- FOUND: backend/tests/phase32/test_pipeline_emission.py
- FOUND: .planning/phases/32-result-readability-3-omni/32-09-SUMMARY.md
- FOUND commits: 518b686 / 793ce5b / ee41ca3 (git log 확인)
- 파일 삭제 0 (커밋 3건 전부 add/modify만)

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-21*
