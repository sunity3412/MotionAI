---
phase: quick-260705-fmg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
  - backend/tests/test_gemini_vision_scorer.py
autonomous: true
requirements: [QUICK-260705-FMG]
must_haves:
  truths:
    - "part_scope 제공 호출의 프롬프트가 해당 부위 전용 판정임을 배타적으로 강제한다 — 다른 부위 결함은 눈에 띄어도 방출 금지 문구 포함"
    - "PROMPT_VERSION 이 v11.2 로 bump 되어 기존 v11.1 캐시 verdict 가 무효화된다"
    - "기존 v10.0/v10.1/v11.0/v11.1 프롬프트 계약 테스트(구조화 강제·좌/우 기준·정타 방어·enum 정의·동작명 0)가 전부 GREEN 유지"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py"
      provides: "v11.2 배타 part_scope 프롬프트 블록 + PROMPT_VERSION bump"
      contains: 'PROMPT_VERSION = "v11.2"'
    - path: "backend/tests/test_gemini_vision_scorer.py"
      provides: "v11.2 배타 문구 존재 테스트 + 버전 pin 갱신"
  key_links:
    - from: "backend/tests/test_gemini_vision_scorer.py"
      to: "gvs._call_gemini_comparison part_scope 프롬프트"
      via: "_comparison_prompt_for_scope 캡처 helper (기존 fake-client 패턴 재사용)"
      pattern: "_comparison_prompt_for_scope"
---

<objective>
phase25 프롬프트 v11.2 — part_scope 배타(exclusive) 강제로 상체 결함 미짚김 fix.

Purpose: 2026-07-05 pod 진단(6회 fresh upper_body-scope 호출, kip-up fault 페어)에서 상체 언급 0/6 — 4회는 하체(양다리 split/왼쪽 무릎)만 방출, 2회는 빈 배열. 현행 v11.1 의 "특히 [상체] 부위에 집중" 문구가 부드러운 참고 수준이라 Gemini 가 무시하고 가장 눈에 띄는 결함(다리)만 반복 보고한다. 결과 (1) 기하 측정상 어깨 40° 편차가 영영 안 짚임 → 감점 0 → 앱에 "참고·감점 아님" 강등, (2) 3-scope 호출 전부가 다리를 중복 방출해 support 자기부풀림(supportCount 3). run5 게이트 kipup_upper (c) FAIL 근본원인. 집계층(agg4)은 이미 준비됨 — 단일 call 이라도 명시 각도쌍 동반 관측이면 지지 인정(WR-01 측정-동반 예외)이므로 방출만 되면 살아남는다. 메모리 교훈 "진짜 레버 = 프롬프트 특정성"(flash-beats-pro)과 정확히 같은 패턴 — scope-집중 특정성을 배타 수준으로 올린다.

Output: gemini_vision_scorer.py 프롬프트 문자열 + PROMPT_VERSION 상수 + 유닛 테스트만 변경. 집계/라우터/스키마 코드 무접촉 (SCHEMA_VERSION v8.1 / AGGREGATION_VERSION agg4 불변).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
@backend/tests/test_gemini_vision_scorer.py
@CLAUDE.md

핵심 위치 (2026-07-05 확인):
- `PROMPT_VERSION = "v11.1"` — gemini_vision_scorer.py:75 (긴 이력 주석 한 줄)
- `_PART_SCOPE_LABEL` dict — line 1623 (upper_body="상체(머리·목·어깨·양팔·팔꿈치·그립)", lower_body="하체(코어·허리·골반·양다리·무릎·발목)", line="전체 라인·정렬")
- part_scope 프롬프트 블록 — `_call_gemini_comparison` 내 line 1658-1677 (`if part_scope:` 분기, f-string suffix)
- 버전 pin 테스트 — test_gemini_vision_scorer.py:632-634 (`assert PROMPT_VERSION == "v11.1"`)
- 프롬프트 캡처 helper — test_gemini_vision_scorer.py `_comparison_prompt_for_scope(part_scope)` (fake client 로 최종 contents[-1] 캡처)

유지해야 하는 기존 테스트 계약 (문구 assert — 새 프롬프트가 반드시 보존):
- "differences", "좌/우", "누락"+"금지", "신체 기준", "확실하지 않으면", "1·2번 규칙" (test_part_scope_prompt_forces_differences_structuring)
- 동작명 하드코딩 0 — kip-up/킵업/power-spin 등 15개 lower-case 검사 (test_part_scope_prompt_generic_no_motion_names). _PART_SCOPE_LABEL 의 해부학 부위 열거(어깨·팔꿈치·그립 등)는 동작-기대답이 아니므로 D-06 위반 아님 — 프롬프트에 세부 부위 예시로 활용 가능.
- part_scope=None 경로는 suffix 없이 `gvs._COMPARISON_PROMPT` 그대로 (test_part_scope_none_prompt_unchanged_no_structuring_suffix) — None 분기 무접촉.
</context>

<tasks>

<task type="auto">
  <name>Task 1: v11.2 배타 part_scope 프롬프트 + PROMPT_VERSION bump</name>
  <files>backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py</files>
  <action>
`_call_gemini_comparison`(line 1658-1677)의 `if part_scope:` 프롬프트 suffix 를 v11.2 로 강화한다. 변경은 이 f-string 문자열과 그 위 주석, 그리고 line 75 의 PROMPT_VERSION 상수뿐 — 함수 시그니처, None 분기, config, contents 순서, 그 외 모든 코드 무접촉.

(1) 배타 강제 (신규, 핵심): 현행 "참고: 이번에는 특히 [{label}] 부위에 집중해" 라는 부드러운 참고 문구를 배타 판정 지시로 교체. 담을 내용 — 이번 호출은 [{label}] 부위 **전용** 판정이며, differences[] 에는 [{label}] 에 속한 세부 부위 항목**만** 담을 것. 다른 부위(예: 이 부위가 상체라면 다리/스플릿)는 별도 호출이 담당하므로 여기서 방출 금지 — 다른 부위의 결함이 아무리 눈에 띄어도 이 호출에서는 무시하고 [{label}] 만 판정. 예시는 "다리/스플릿" 같은 generic 신체 부위 표현만 사용(동작명 금지). 이 문구가 support 자기부풀림(3-scope 가 같은 다리 결함을 중복 방출 → supportCount 3)도 함께 차단함을 주석에 명기.

(2) 순차 점검 강화: 기존 "이 부위에 속한 세부 부위를 하나씩 순서대로 점검" 문구를 유지하되, [{label}] 라벨 자체가 이미 세부 부위를 열거하고 있음(_PART_SCOPE_LABEL 값 — 예: 상체(머리·목·어깨·양팔·팔꿈치·그립))을 활용해 "라벨 괄호 안에 열거된 세부 부위를 하나씩 기준 영상과 대조" 수준으로 지시를 구체화한다. label 별 if/else 하드코딩 분기는 만들지 말 것 — 단일 generic 문구가 {label} 주입으로 전 scope 에 동작해야 함 (동작명/기대답 주입 금지 D-06 유지; 해부학 부위 열거는 동작-기대답이 아니므로 허용).

(3) 기존 계약 전부 보존 (테스트가 문구를 assert 함): 관찰-전량 differences[] 방출 강제("하나도 빠짐없이", primary_fault 서사-only "누락...금지...무효"), 좌/우 = 수행자 "신체 기준" + "확실하지 않으면" 생략 허용, 각도쌍 측정 rubric(student_angle_deg/reference_angle_deg/measurement_basis, 편차 계산은 코드 소관), "1·2번 규칙" 정타 방어("편차가 없으면 항목을 만들지 말고 빈 배열이 정답"). fault_category enum rule 은 base `_COMPARISON_PROMPT` 소관이라 suffix 에서 무접촉.

(4) PROMPT_VERSION line 75: "v11.1" → "v11.2" bump. 기존 이력 주석 형식대로 맨 앞에 v11.2 근거 1줄 추가 — "v11.2 (quick 260705-fmg): part_scope 배타 강제 — 2026-07-05 pod 진단 upper_body scope 6회 중 상체 방출 0/하체 중복 방출 4(2회 빈 배열), '집중' 참고 문구를 부위-전용 판정으로 교체(타 부위 방출 금지) + 3-scope 하체 중복 방출의 support 자기부풀림 차단" 취지. SCHEMA_VERSION/AGGREGATION_VERSION 은 절대 건드리지 말 것(스키마/집계 로직 무변경).

(5) suffix 블록 위 코드 주석(현행 v11.0 주석, line 1660-1663)에 v11.2 변경 근거를 이어서 1-2줄 추가(한국어 why, 진단 근거 "2026-07-05 pod 6/6" 인용). 이모지 금지, 점수 리터럴/사람 라벨 금지.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_gemini_vision_scorer.py -q 2>&1 | tail -5</automated>
  </verify>
  <done>PROMPT_VERSION == "v11.2". part_scope 프롬프트에 부위-전용/타-부위 방출 금지 배타 문구 포함. 기존 문구 계약(differences/좌·우/신체 기준/확실하지 않으면/1·2번 규칙/각도쌍 rubric) 보존. None 경로 byte-동일. Task 1 시점에는 버전 pin 테스트(line 633) 1건만 FAIL 허용 — Task 2 에서 정합.</done>
</task>

<task type="auto">
  <name>Task 2: 테스트 정합 + v11.2 배타 문구 존재 테스트 추가</name>
  <files>backend/tests/test_gemini_vision_scorer.py</files>
  <action>
(1) 버전 pin 테스트(line 632-634) 갱신: `assert PROMPT_VERSION == "v11.2"` 로 변경, docstring 을 v11.2 근거로 갱신, stale 방지 negative assert 튜플에 "v11.1" 추가 (`not in ("v9.0", "v10.0", "v10.1", "v11.0", "v11.1")`).

(2) v11.2 배타 문구 존재 테스트 1개 신규 추가 (과잉 금지 — 문구 존재 확인 수준): 기존 `_comparison_prompt_for_scope` helper 를 재사용해 `gvs.VETO_PART_SCOPES` 각 scope 에 대해 (a) 부위-전용 판정 문구(예: "전용") 존재, (b) 타 부위 방출 금지 문구(예: "다른 부위" + "무시" 또는 "방출 금지" — 구현한 실제 문구에 맞춰 substring 선택) 존재를 assert. docstring 에 근거 1줄(2026-07-05 pod 진단: upper_body scope 6회 중 상체 방출 0 — 배타 강제로 fix). 기존 25-04/25-05 섹션 구분 주석 스타일(`# ───...` 헤더) 따라 배치.

(3) 기존 프롬프트 계약 테스트 3종(test_part_scope_prompt_forces_differences_structuring / test_part_scope_prompt_generic_no_motion_names / test_part_scope_none_prompt_unchanged_no_structuring_suffix)은 Task 1 이 문구를 보존했으면 무수정 GREEN 이어야 함 — FAIL 시 테스트를 고치지 말고 Task 1 프롬프트 문구를 교정할 것 (계약 완화 금지).

전체 검증 게이트 실행: test_gemini_vision_scorer.py + test_deduction_engine.py + test_phase25_eval_gates.py 모두 GREEN.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_gemini_vision_scorer.py tests/test_deduction_engine.py tests/test_phase25_eval_gates.py -q 2>&1 | tail -5</automated>
  </verify>
  <done>3개 테스트 파일 전부 GREEN (0 failed). 버전 pin = v11.2. 신규 배타 문구 테스트 1개 PASS. 기존 프롬프트 계약 테스트 무수정 PASS. 집계/라우터/스키마 파일 diff 0.</done>
</task>

</tasks>

<verification>
- `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_gemini_vision_scorer.py tests/test_deduction_engine.py tests/test_phase25_eval_gates.py -q` GREEN
- `git diff --stat` 이 gemini_vision_scorer.py + test_gemini_vision_scorer.py 2개 파일만 표시 (집계/라우터/스키마 무접촉 증명)
- `grep -c 'SCHEMA_VERSION = "v8.1"' backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` == 1, `grep -c 'AGGREGATION_VERSION = "agg4"'` == 1 (불변 확인)
</verification>

<success_criteria>
- part_scope 호출 프롬프트가 부위-전용 배타 판정을 강제한다 (타 부위 결함 방출 금지 문구 포함)
- PROMPT_VERSION v11.2 bump 로 v11.1 캐시 verdict 무효화 (SCHEMA/AGGREGATION 버전 불변)
- 지정 3개 테스트 파일 GREEN, 기존 프롬프트 계약(정타 방어·좌/우 기준·측정 rubric·enum rule·D-06 generic) 완전 보존
- 실효 검증(kip-up 페어에서 상체 실제 방출)은 pod sweep 필요 — 본 quick 범위 밖, SUMMARY 에 pod 검증 PENDING 으로 박제
</success_criteria>

<output>
Create `.planning/quick/260705-fmg-phase25-v11-2-part-scope-fix/260705-fmg-SUMMARY.md` when done
</output>
