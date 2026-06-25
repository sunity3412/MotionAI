# Phase 24 Plan Direct Review - Iteration 5

**Scope:** 4차 리뷰 반영 후의 `24-01-PLAN.md`, `24-02-PLAN.md`, `24-03-PLAN.md`, `24-PATTERNS.md`, `24-VALIDATION.md`와 현재 live code seam.

**Method:** 외부 리뷰 없이 자체 코드-플랜 대조. 특히 4차 HIGH-1/HIGH-2 반영분이 실제 `_process` 제어흐름과 맞는지 재검토.

## Verdict

4차의 큰 두 블로커였던 branch-aware quantification flow와 legacy path 정리는 상당히 좋아졌다. `24-02-PLAN.md`는 이제 `baseline_kind`를 seam에서 계산하고, context branch에서만 `_build_deduction_measured_deviations(...)`를 호출하며, legacy path는 quantification-unavailable fallback으로 제한한다.

다만 production에서 "Gemini가 no fault / silent인데 measured geometry는 결함을 보유"한 케이스가 아직 passthrough로 빠질 수 있다. 이건 Phase 24의 핵심 방어선인 `test_gemini_silent_not_100`을 production 상태 머신에서 무력화할 수 있으므로, Plan 02 실행 전에 닫는 게 맞다.

## Findings

### HIGH-1: production `no_fault` status가 measured-seed tally를 우회할 수 있다

Plan 01의 핵심 요구는 Gemini가 아무 supported difference를 주지 않아도, quantification이 available이고 measured deviation이 tolerance 밖이면 seed criterion이 활성화되어 `final < 100`이어야 한다는 것이다(`24-01-PLAN.md:201`, `24-01-PLAN.md:221`, `24-01-PLAN.md:276`). 이게 Phase 20 false-negative 방어다.

하지만 current production collect는 still-pair path에서 `verdict.severity == "none"`이면 `collection_status="no_fault"`로 반환한다(`backend/functions/pipeline/app.py:1874-1876`). 현재 `_apply_vision_veto_from_context`는 `status != "candidate_verdict"` 전체를 passthrough audit으로 돌려보낸다(`backend/functions/pipeline/app.py:2100-2122`). Plan 02도 "tally always runs on a candidate_verdict"라고만 수정한다(`24-02-PLAN.md:169`) and keeps early passthrough branches. 그래서 production-shaped Gemini-silent case는:

1. `_process` context branch로 들어감
2. selected pair가 있어서 quantification은 available
3. measured_deviations도 만들 수 있음
4. 그런데 `_apply_vision_veto_from_context`가 `no_fault`라서 tally를 실행하지 않고 passthrough

즉 Plan 01의 measured seed가 실행될 기회가 없다. Task 4의 `Mode1 Gemini-silent-with-measured-deviation` 테스트도 현재 문구대로면 synthetic `candidate_verdict` + empty supported_differences로 작성될 수 있어, production `no_fault` 경로를 놓칠 가능성이 있다(`24-02-PLAN.md:262`, `24-02-PLAN.md:284`).

**Fix:** Plan 02에서 `no_fault` with selected frame / available quantification을 tally-eligible status로 명시한다. 구현 선택지는 둘 중 하나면 된다.

- `_apply_vision_veto_from_context`에서 `status in {"candidate_verdict", "no_fault"}`는 tally를 실행한다. `no_fault`는 supported_differences empty로 engine에 들어가고, measured seed만으로 records/final을 결정한다. measured deduction이 없으면 `not_applicable`, 있으면 `applied` + `tallyFinal`.
- 또는 `_collect_vision_fault_context`가 severity none verdict도 score-free passthrough가 아니라 tallyable context로 반환하되, `cap_would_apply=False`라 coach injection은 계속 꺼둔다.

그리고 Task 4 테스트는 반드시 production-shaped fixture를 써야 한다: `collection_status="no_fault"`, `verdict.severity=="none"`, `supported_differences=[]`, `selected_frame_pairs=[pair]`, available quantification, measured leg deviation beyond tolerance -> `deductionBreakdown.records` contains `leg_extension` and `overallScore < 100`.

### MEDIUM-1: "severity is a criterion pointer" 문구가 frontmatter에 아직 남아 있다

4차에서 지적한 표현은 action 본문에서는 거의 정리됐다. Plan 02 line 118/169는 "verdict/differences carry the criterion pointer; severity is non-scoring label"로 맞다. 그런데 frontmatter truth/artifact에는 아직 severity 자체를 criterion pointer로 설명한다(`24-02-PLAN.md:24`, `24-02-PLAN.md:37`).

이 문구는 구현자가 `severity`를 selection signal로 읽는 방향으로 오해하게 만들 수 있다. 실제 invariant는 `supported_difference.body_part/fault_state`와 fault label이 criterion을 locate하고, `severity`는 scoring/selection에서 읽지 않으며 coach eligibility continuity에만 남는 것이다.

**Fix:** frontmatter도 아래 표현으로 통일한다.

> verdict/differences carry the criterion pointer; severity is a non-scoring label used only for coachRootCauseEligible continuity.

### LOW-1: exact grep count for `_build_deduction_measured_deviations` is still brittle

Plan 02는 `grep -n "_build_deduction_measured_deviations" backend/functions/pipeline/app.py`가 정확히 2 hits(def + one seam call)여야 한다고 한다(`24-02-PLAN.md:185`). 같은 acceptance에 source-test도 추가되어 있어 4차보다는 낫지만, 단순 grep count는 helper docstring/comment에 이름이 한 번만 들어가도 실패한다.

**Fix:** acceptance는 source-test/AST-style range check를 canonical으로 두고, grep은 `rg -n "^(def _build_deduction_measured_deviations|\\s+measured_deviations = _build_deduction_measured_deviations\\()"`처럼 def/call 형태만 세도록 좁힌다.

## Recommended Patch Order

1. Plan 02에 `no_fault` tally-eligible rule을 추가하고, passthrough status 목록에서 `no_fault`를 분리한다.
2. Task 4의 Gemini-silent integration test를 production-shaped `no_fault` fixture로 고정한다.
3. Plan 02 frontmatter의 "severity criterion pointer" 문구를 `verdict/differences criterion pointer`로 치환한다.
4. `_build_deduction_measured_deviations` exact-count acceptance를 def/call 형태 또는 source-test 중심으로 좁힌다.

## Close

Plan 24는 이제 실행 가능한 수준에 가까워졌다. 위 HIGH-1만 닫으면 Plan 01의 measured-seed 설계와 Plan 02 production state machine이 같은 말을 하게 된다. 그 다음은 구현으로 넘어가도 된다.
