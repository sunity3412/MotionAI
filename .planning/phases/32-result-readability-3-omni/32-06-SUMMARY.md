---
phase: 32-result-readability-3-omni
plan: 06
subsystem: backend-contract
tags: [mission-loop, contract-3way, scoped-validator, normalize, tdd]
requires:
  - 32-01 (phase32 테스트 스캐폴드 conftest)
  - 32-05 (phrasebook._ENTRY_SLOTS — DEDUCTION_PHRASE_KEYS 동형 기준)
provides:
  - "analysis/mission.py — build_fault_key/select_mission/derive_mission_outcome 순수 함수"
  - "계약 3면: Mission/MissionOutcome/SummaryPraise/CoachQuestion + DeductionRecord §12.3 확장"
  - "firestore_admin scoped validator 4종 (result 경유, complete_analysis kwarg 0)"
  - "userAnalyses normalize 4종 + record 확장 키 통과 파싱"
affects:
  - 32-07 (summarySource — summaryPraise 소비)
  - 32-09 (파이프라인 방출 배선 — recordId 각인·mission 체인·praise·질문)
  - 32-10 (감점 카드 3단 문구 렌더)
  - 32-11 (recordId 맵 buildRecordMaps)
  - 32-13 (스팟체크 — recordId 숨김·praise 교차검증)
tech-stack:
  added: []
  patterns:
    - "faultKey = motionId::ruleId::criterion 결정적 조합 (좌우 구분 criterion 승계)"
    - "streak doc 체인 전파 + 순수 함수 측 motionId 가드"
    - "scoped validator 화이트리스트+enum+finite+상한 (motionAlignment 선례)"
    - "DEDUCTION_RECORD_EXTENSION_KEYS 3-set 합집합 lockstep"
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/mission.py
    - backend/tests/phase32/test_mission_rules.py
    - backend/tests/phase32/test_mission_contract_lockstep.py
  modified:
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/lib/userAnalyses.ts
    - backend/tests/test_deduction_engine.py
decisions:
  - "select_mission 은 결함 0 + 안전 0 이면 None 반환 (미션 fabrication 금지 — validator None graceful 정합)"
  - "안전 prev 미션은 derive_mission_outcome 제외 (D-14 — baseline 0 의 '소멸=개선'은 공허한 칭찬, D-06 근거 없는 칭찬 금지 정합)"
  - "streak 상한 99 — 엔진 _STREAK_CAP ↔ validator ↔ models.MISSION_STREAK_MAX lockstep"
  - "coachQuestions validator 는 source='user' 거부 — 클라이언트 로컬 전용 경계를 저장층에서 강제"
  - "summaryPraise = 단일 객체 (32-09 방출 형상·32-07 SummaryInput 과 교차 확인)"
  - "record 확장 8키는 DEDUCTION_RECORD_EXTENSION_KEYS 로 명명 — 기존 필수 11/optional 2 와 disjoint 3-set lockstep"
metrics:
  duration: "24m"
  completed: "2026-07-21T11:26:11Z"
  tasks: 2
  tests-added: 48
---

# Phase 32 Plan 06: 미션 엔진 + 계약 3면 Summary

faultKey(motionId::ruleId::criterion) 기반 미션 선정·streak 체인·수치 outcome 순수 함수와 phase 32 신규 필드(mission/missionOutcome/summaryPraise/coachQuestions/record 3단 문구·recordId·tolerance)의 계약 3면 + scoped validator + 앱 normalize 를 확립.

## Task 1 — mission.py 순수 함수 (TDD)

- RED `1ba7444` → GREEN `1c26bf8`. 22 테스트 (behavior 8건 + 설계 엣지).
- `build_fault_key(motion_id, rule_id, criterion)` — 결정적 문자열, criterion 이 좌우 관절 내장(`angle_vs_reference__left_knee`)이라 좌우 구분 승계 (리뷰 blocker 1 해소).
- `select_mission(records, safety_flags, prev_mission, motion_id)` — D-19 ①안전 > ②반복(faultKey 동일성) > ③감점 최대. isSafety=True 는 **streak 1 고정 + escalation 'none' 강제** (D-14 정합 코드 강제). prev.motionId ≠ 현재 motion 이면 체인 리셋 (get_previous_analysis 가 motion 미필터인 실측 사실의 순수 함수 방어). baseline 4종(baselinePoints/baselineDeviation/targetValue/unit) 저장 → 다음 분석 개선량 계산 가능 (D-26).
- `derive_mission_outcome(prev_mission, records, mode, motion_id)` — 소멸(currentPoints 0·deltaPoints=baseline)/감소/악화 수치만. mode3 전용, 사람 문장 필드 0 (계산/카피 책임 분리). 에스컬레이션: streak 2 = exercise_detour, ≥3 = coach_card (D-27).
- 순수성: import = math + models 만 (boto3/firestore 0). 반환 전부 flat camelCase scalar.

## Task 2 — 계약 3면 + validator + normalize (atomic, `981f347`)

- **models.py**: MISSION_KEYS(13)/MISSION_SELECTED_BY/MISSION_ESCALATIONS/MISSION_OUTCOME_KEYS(9)/DEDUCTION_PHRASE_KEYS(6 — phrasebook._ENTRY_SLOTS 동형, lockstep 테스트로 고정)/SUMMARY_PRAISE_KEYS/SUMMARY_PRAISE_SOURCES/COACH_QUESTION_SOURCES + MISSION_STREAK_MAX(99) + **DEDUCTION_RECORD_EXTENSION_KEYS**(§12.3 additive optional 8키).
- **analysis.ts**: Mission/MissionOutcome/SummaryPraise/CoachQuestion interface + DeductionRecord 확장(recordId·statusLine·whyLine·cueLine·coachQuestion·exerciseId·exerciseReason·tolerance) + AnalysisResult 4필드. source 'user' 클라이언트 로컬 전용 경계 주석 1줄.
- **contract.md §12**: 미션 루프(faultKey·baseline 의미·streak 체인·D-14 정합)/outcome/record 확장(recordId 조인 규칙 `r{index:02d}:{criterion}`·fail-closed 슬롯 생략)/summaryPraise 단일 원천(백엔드 산출, 앱 소비+legacy 폴백)/coachQuestions('user' 경계)/§12.6 검증 규칙 + 방출 32-09 부터 명시.
- **firestore_admin**: `_validate_mission`/`_validate_mission_outcome`/`_validate_summary_praise`/`_validate_coach_questions` — 화이트리스트+enum+finite+상한(streak 1..99, headline·text ≤200, 문항 ≤10) + **'user' 방출 거부**. complete_analysis 의 `if result:` 블록 4줄 wiring — **시그니처 diff 0** (SP-1 "result 안으로 흐른다", 테스트로 고정). record 확장 키는 기존 `_validate_dict_only_scalars` 경로 자동 통과 (validator 본체 무변경 — 테스트 실증).
- **userAnalyses.ts**: normalizeMission/normalizeMissionOutcome/normalizeSummaryPraise/normalizeCoachQuestions (enum 강등·정수/유한 검증, malformed=undefined, 필드 drop 없음) + normalizeRecordPhraseFields (records map 통과 파싱).
- **lockstep 테스트** 26건: models↔TS 텍스트 대조 + contract.md 절 존재 + normalize 헬퍼 존재 + validator 행동 + 엔진 실산출물이 validator 통과하는 통합 대조 + complete_analysis 신규 kwarg 금지.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 기존 test_deduction_engine.py::test_contract_lockstep 확장**
- **Found during:** Task 2 (회귀 확인 — DeductionRecord TS 확장이 기존 lockstep 게이트를 깨뜨림)
- **Issue:** 게이트가 regex 로 TS interface 필드를 추출해 `필수 ∪ optional == TS 필드` 동등을 강제 — 신규 8키가 방정식에 없고, 주석의 `{index:02d}` 중괄호·`lockstep:` word-colon 패턴이 regex 캡처를 오염.
- **Fix:** models 에 `DEDUCTION_RECORD_EXTENSION_KEYS` 신설 → 게이트를 3-set 합집합 + disjoint 가드로 확장. TS interface 블록 주석에서 중괄호·word-colon 패턴 제거 + 금지 주석 명시. 이는 lockstep 메커니즘이 설계대로 동작한 것 — 계약 확장 시 게이트도 함께 확장.
- **Files modified:** backend/tests/test_deduction_engine.py, backend/shared/python/sunity_shared/models.py, app/src/types/analysis.ts
- **Commit:** 981f347

### 설계 재량 (plan 범위 내 Claude's discretion)

- `select_mission` 반환 `dict | None` — 결함 0 + 안전 0 분석은 미션 없음 (fabrication 금지). 32-09 는 None 시 키 생략 방출.
- 안전 prev 미션은 outcome 추적 제외 (D-14 해석 — docstring·테스트로 고정).
- 0 감점 record 는 미션 후보에서 제외.

## Verification

- `backend pytest tests/phase32` — **79 passed** (mission_rules 22 + contract_lockstep 26 + 기존 31).
- `tests/test_deduction_engine.py` + `test_motion_alignment_contract.py` 포함 회귀 selection(`-k "firestore or lockstep or contract or motion_alignment or deduction"`) — **425 passed / 1 failed**. 유일 실패 = `tests/phase06/test_pipeline_firestore_integration.py::test_process_calls_complete_analysis_with_body_comparison_report` (NotPoleMotionError, pipeline/app.py:4399 — 비교 스테이지의 not_pole 게이트, complete_analysis 도달 전 발생. 본 플랜 수정 파일과 무접촉인 **사전 실재 환경 실패**, 12 collection error 도 `No module named 'backend'` 사전 실재 환경 이슈). baseline 초과 실패 0.
- **앱 typecheck**: worktree 에 app/node_modules 부재로 `npm run typecheck` 불가 → **대체 검증**: 임시 tsconfig 하니스(main 리포 node_modules 의 tsc + firebase/react 실타입 참조, strict) 로 수정 파일 2종 + transitive 로컬 import(firebase.ts/bodyProfile.ts) 컴파일 — **exit 0 clean**. 하니스 파일은 검증 후 삭제(커밋 무포함). 변경이 additive optional 이라 타 소비 파일 파급 없음 — merge 후 main 에서 전체 `npm run typecheck` 1회 권장.

## Known Stubs

없음 — 본 플랜 산출물(순수 함수·계약·validator·normalize)은 전부 동작·검증 완료. **신규 필드의 실제 방출은 32-09 파이프라인 배선의 소관**(플랜 명시 경계 — contract.md §12 에 "방출은 32-09 부터" 명문화). 현행 doc 은 필드 부재 = legacy 하위호환으로 렌더 diff 0.

## 다음 플랜 인계

- 32-09: `select_mission(records, safety_flags, prev.get("result",{}).get("mission"), motion_id)` / `derive_mission_outcome(prev_mission, records, mode, motion_id)` 시그니처 그대로 배선. recordId 각인 형식 `r{i:02d}:{criterion}` (§12.3). coachQuestions 는 백엔드 소스 3종만 (validator 가 'user' 거부).
- 32-07: summaryPraise 단일 객체 {source, headline, evidenceValue, evidenceUnit} — SummaryInput 구조적 타이핑과 정합 확인됨.

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/mission.py
- FOUND: backend/tests/phase32/test_mission_rules.py
- FOUND: backend/tests/phase32/test_mission_contract_lockstep.py
- FOUND commits: 1ba7444 (RED), 1c26bf8 (GREEN), 981f347 (contract 3면)
- 79/79 phase32 tests green, 계약 3면 lockstep 테스트 통과
