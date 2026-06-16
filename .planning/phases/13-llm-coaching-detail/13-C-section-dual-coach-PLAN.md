---
phase: 13-llm-coaching-detail
plan: C
type: execute
wave: 3
depends_on: [13-A, 13-B]
files_modified:
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - app/src/types/analysis.ts
  - app/src/components/CoachingTipDetailModal.tsx
  - backend/tests/phase13/test_section_dual_coach.py
autonomous: true
requirements: [PERS-03]
must_haves:
  truths:
    - "자세히 모달이 원인→처방→부상위험→강사확인 4개 라벨 섹션을 세로 스택으로 렌더한다"
    - "양쪽 writer(Gemini+Cerebras)를 한 분석에서 모두 호출해 섹션별로 조립한다"
    - "한쪽 writer가 재시도 후에도 실패하면 다른 writer가 그 섹션을 대신 채운다(빈 섹션 0)"
    - "둘 다 실패하면 기존 수치 기반 단일 폴백으로 떨어진다"
    - "coach 섹션별 성공/폴백 출처가 audit 로그로 남는다"
    - "출처 라벨은 기능 라벨만(원인/교정 처방/부상 위험/강사 확인) 노출 — AI 벤더명 비노출"
  artifacts:
    - path: "backend/functions/pipeline/app.py"
      provides: "dual-track toggle을 '둘 다 호출 + 섹션 조립'으로 확장 + 계층형 폴백 + 출처 로깅"
    - path: "backend/shared/python/sunity_shared/analysis/assemble.py"
      provides: "detail2 섹션별 출처 태깅 조립 (causes/coachNote=Gemini, fix/injuryRisk=Cerebras)"
    - path: "app/src/types/analysis.ts"
      provides: "CoachingTipDetail section source 계약 (3-way lockstep)"
    - path: "app/src/components/CoachingTipDetailModal.tsx"
      provides: "4개 라벨 섹션 세로 스택 렌더"
    - path: "backend/tests/phase13/test_section_dual_coach.py"
      provides: "섹션 조립 + 계층형 폴백 + 출처 태깅 단위테스트"
  key_links:
    - from: "backend/functions/pipeline/app.py::_process"
      to: "assemble.assemble_dual_coach_sections"
      via: "양쪽 writer 결과를 섹션별로 머지"
      pattern: "assemble_dual_coach_sections"
    - from: "app/src/components/CoachingTipDetailModal.tsx"
      to: "tip.detail2 (causes/injuryRisk/coachNote)"
      via: "섹션별 라벨 렌더"
      pattern: "detail2\\.(causes|injuryRisk|coachNote)"
---

<objective>
coach LLM 보고서를 출처별 라벨 섹션으로 분리한다. 토글(택1)을 "둘 다 호출 + 섹션별 조립"으로 확장: 원인(왜 안 되는지)=Gemini, 교정 처방(무엇이 필요한지)=Cerebras, 부상 위험=Cerebras, 강사 확인=Gemini. belle 핵심가치 "왜 + 무엇"을 자세히 모달에 그대로 매핑한다.

Purpose: 강사 위임 톤(Gemini)과 구체 처방(Cerebras)이 한 화면에 공존 → 강사 철학 충돌(수치만)도 수강생 이탈(일반론만)도 동시 회피. 13-C 결정 박제 [[section-dual-coach-report]].
Output: dual-track 확장 + detail2 섹션 출처 태깅 + 계층형 폴백 + 출처 로깅 + 자세히 모달 4섹션 세로 스택 렌더.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/phases/13-llm-coaching-detail/13-CONTEXT.md
@.planning/phases/13-llm-coaching-detail/13-B-SUMMARY.md

# 13-C 결정 박제 (MUST read)
@/Users/kimtaesung/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/section-dual-coach-report.md

# 코드 통합 지점
@backend/functions/pipeline/app.py
@backend/shared/python/sunity_shared/analysis/coach_writer.py
@backend/shared/python/sunity_shared/analysis/assemble.py
@app/src/types/analysis.ts
@app/src/components/CoachingTipDetailModal.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 섹션 출처 태깅 조립 + 계층형 폴백 (백엔드 순수 로직)</name>
  <files>backend/shared/python/sunity_shared/analysis/assemble.py, backend/shared/python/sunity_shared/analysis/coach_writer.py, app/src/types/analysis.ts, backend/tests/phase13/test_section_dual_coach.py</files>
  <behavior>
    - 양쪽 writer 결과(gemini_details dict, cerebras_details dict)를 받아 관절키별 detail2 를 섹션 출처에 따라 조립한다: causes=Gemini, coachNote=Gemini, fix(각 cause의 처방)=Cerebras, injuryRisk=Cerebras. 13-C locked 배분.
    - 한쪽 writer 가 해당 관절키를 비웠으면(빈 dict 또는 키 누락) → 다른 writer 의 같은 섹션으로 cross-fill (빈 섹션 0). cross-fill 발생 시 섹션 출처를 audit 에 기록.
    - 양쪽 모두 해당 관절키 비었으면 → 기존 build_tips 수치 기반 폴백 문장(detail만, detail2 생략)으로 떨어진다 (둘 다 실패 = 최후 바닥).
    - detail2 계약은 변경하지 않는다: {causes:[{title,explanation,fix}], injuryRisk?, coachNote}. 출처는 별도 데이터가 아니라 섹션 조립 결과로만 표현(UI 라벨은 기능 라벨 고정). source 필드 추가 금지 — 벤더명 비노출(13-C locked) + 3-way lockstep 최소 변경.
    - 반환값에 섹션별 출처 audit(예: {joint: {causes:"gemini", fix:"cerebras", coachNote:"gemini", injuryRisk:"cerebras", crossFilled:[...]}}) 동봉 — Task 2 로깅이 소비.
  </behavior>
  <action>
    `assemble.py` 에 순수 함수 `assemble_dual_coach_sections(gemini_details, cerebras_details, top_assessments)` 추가. 13-C locked 섹션 배분(causes/coachNote=Gemini, fix/injuryRisk=Cerebras)으로 관절키별 detail2 를 머지한다. 한쪽 섹션 누락 시 다른 writer 의 같은 섹션으로 cross-fill 하고 cross-fill 사실을 audit dict 에 기록한다. 양쪽 모두 누락 관절키는 detail2 를 생략(build_tips 의 기존 수치 폴백이 detail 만 채우게 둠). detail2 형상은 기존 계약 {causes,injuryRisk?,coachNote} 그대로 유지하고 source 필드를 추가하지 않는다(벤더명 비노출 + lockstep 최소화, 13-C locked). 함수는 (merged_details, section_audit) 튜플을 반환한다. `coach_writer.py` 는 detail2 스키마 변경 없으므로 프롬프트/구조 수정 없음 — 기존 호출 인터페이스만 재사용한다. `app/src/types/analysis.ts` `CoachingTipDetail` 주석에 4개 기능 섹션(원인=causes / 교정 처방=cause.fix / 부상 위험=injuryRisk / 강사 확인=coachNote) 라벨 매핑을 박제하되 형상 변경은 없음(주석만, 3-way lockstep 유지). 단위테스트 `test_section_dual_coach.py` 작성: (1) 양쪽 정상 → 섹션 배분 정확, (2) Gemini 한쪽 누락 → Cerebras cross-fill + audit crossFilled 기록, (3) 둘 다 누락 → detail2 생략 + 수치 폴백, (4) audit 출처 dict 형상.
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/phase13/test_section_dual_coach.py -x -q && cd ../app && npm run typecheck</automated>
  </verify>
  <done>섹션 조립 + cross-fill 폴백 + audit 반환이 단위테스트 4케이스 통과, app tsc clean, detail2 계약 형상 불변.</done>
</task>

<task type="auto">
  <name>Task 2: pipeline dual-track 확장 — 둘 다 호출 + 재시도/타임아웃 + 출처 로깅</name>
  <files>backend/functions/pipeline/app.py</files>
  <action>
    `_process` 의 coach 호출부(현재 `if _coach_enabled():` Gemini→Cerebras 토글 분기, L1906 부근)를 "양쪽 호출 + 섹션 조립"으로 확장한다. 13-C 계층형 폴백: (1) `_ensure_gemini_coach_writer().write(coach_context)` 와 `_COACH_WRITER.write(coach_context)` 를 둘 다 호출하되 각 호출에 재시도 1회 + 짧은 타임아웃을 건다(기존 writer 가 자체 타임아웃을 갖지 않으면 호출부에서 1회 재시도 래퍼로 감싼다 — 둘 다 같은 `coach_context` 공유, B3 정합). (2) 두 결과를 Task 1 의 `assemble.assemble_dual_coach_sections(gemini_result, cerebras_result, top_assessments)` 로 섹션 조립해 `coach_details` 산출. (3) 한쪽 writer 가 fallback dict(`{}` 또는 `_fallbackReason`) 면 cross-fill 이 자동 처리(빈 섹션 0). (4) 둘 다 fallback 이면 `coach_details = {}` 로 두어 `build_result` 의 수치 폴백 진입. 기존 `_strip_reserved_keys` / `_gemini_b_audit_payload` 패턴을 재사용해 섹션별 출처 + 재시도 + cross-fill + 최종 폴백 사유를 `log.info` 로 audit 기록(coach 성공/폴백률 실측 전환 근거, 13-C 합의). `GEMINI_COACH_ENABLED` 토글은 유지하되 13-C 에서는 섹션용으로 양쪽 활성이 기본 동작 — env OFF 시 기존 Cerebras-only path 보존(회귀 0). `coach_context` 는 단일 `_build_coach_context` 결과를 두 writer 가 공유(중복 빌드 금지).
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/phase13 -q && python -c "import ast,sys; ast.parse(open('functions/pipeline/app.py').read()); print('parse ok')"</automated>
  </verify>
  <done>pipeline 이 양쪽 writer 호출→섹션 조립→계층형 폴백을 수행하고 섹션별 출처/폴백 로그를 남긴다. phase13 단위테스트 회귀 0, GEMINI_COACH_ENABLED=0 시 기존 Cerebras-only path 보존.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: 자세히 모달 4섹션 세로 스택 렌더 (기능 라벨만)</name>
  <files>app/src/components/CoachingTipDetailModal.tsx, app/src/types/analysis.ts</files>
  <behavior>
    - detail2 가 있으면 자세히 모달이 4개 라벨 섹션을 세로 스택(스크롤)으로 순서대로 렌더한다: "원인"(causes title+explanation) → "교정 처방"(각 cause.fix) → "부상 위험"(injuryRisk, 없으면 섹션 자체 생략) → "강사 확인"(coachNote).
    - 라벨은 기능 라벨만(원인/교정 처방/부상 위험/강사 확인) — AI/벤더명(Gemini/Cerebras) 텍스트 0.
    - 라이트 테마 + brand #FF4B33 토큰만 사용(하드코딩 색/spacing 0). Phase 12.5 modal/sheet 패턴 재사용.
    - detail2 없으면 기존 noDetail 안내 문구 유지(회귀 0).
  </behavior>
  <action>
    `CoachingTipDetailModal.tsx` 의 `CausesSection` 을 4섹션 세로 스택으로 재구성한다(탭/아코디언 기각 — 원인+처방 동시 비교가 핵심, 13-C locked). 섹션 순서: 원인(causes 각 항목 title+explanation) → 교정 처방(각 cause.fix 를 모아 한 섹션, 13-A 큐레이션 보완운동 카드와 자연 연결되는 동적 텍스트) → 부상 위험(injuryRisk 있을 때만) → 강사 확인(coachNote). 섹션 헤더는 기능 라벨 한글 고정 문자열만 — 벤더명 노출 금지(13-C locked). 색/radius/spacing 은 `../theme` 토큰만(`colors`, `radius`) 사용. 기존 ScrollView/sheet 구조와 noDetail 폴백 유지. `analysis.ts` 는 Task 1 에서 주석만 갱신했으므로 추가 변경 없음(형상 동일).
  </action>
  <verify>
    <automated>cd app && npm run typecheck</automated>
  </verify>
  <done>자세히 모달이 원인→처방→부상위험→강사확인 4섹션을 세로 스택으로 렌더, 벤더명 텍스트 0, 토큰만 사용, tsc clean. injuryRisk 없을 때 섹션 생략, detail2 없을 때 기존 폴백 유지.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pipeline→LLM(Gemini/Cerebras) | LLM JSON 출력은 untrusted — 형상 파싱 실패 시 폴백 |
| LLM 출력→Firestore→app | detail2 텍스트가 사용자 화면에 그대로 렌더 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-13C-01 | Tampering | LLM JSON 출력 형상 | mitigate | `_normalize_entry`/섹션 조립이 누락/잘못된 섹션을 cross-fill 또는 수치 폴백으로 흡수(빈 섹션 0) |
| T-13C-02 | Denial of Service | provider rate-limit/타임아웃 | mitigate | 재시도 1회 + 짧은 타임아웃 + 한쪽 실패 시 다른 writer cross-fill, 둘 다 실패 시 수치 폴백 |
| T-13C-03 | Information Disclosure | 벤더명 노출 | mitigate | UI 라벨 기능 라벨 고정, source 필드 미추가 — 응답에 벤더명 비포함(13-C locked) |
| T-13C-SC | Tampering | npm/pip 신규 install | accept | 신규 패키지 install 없음(기존 cerebras-cloud-sdk/Gemini 어댑터 재사용) |
</threat_model>

<verification>
- `backend/tests/phase13` 전체 회귀 0 (13-A/13-B 81 passed 유지).
- `test_section_dual_coach.py` 4케이스: 정상 배분 / Gemini 누락 cross-fill / 둘다 누락 수치폴백 / audit 형상.
- `app npm run typecheck` clean.
- `GEMINI_COACH_ENABLED=0` 시 기존 Cerebras-only path 보존(회귀 0).
- 자세히 모달에 벤더명(Gemini/Cerebras) 텍스트 0.
- 실 영상→실 LLM 섹션 조립 E2E 라이브 검증은 Phase 15(실증) scope — 13-C 빌드는 단위/타입 게이트까지.
</verification>

<success_criteria>
- 자세히 모달이 원인→처방→부상위험→강사확인 4섹션 세로 스택으로 렌더(기능 라벨만).
- pipeline 이 한 분석에서 양쪽 writer 호출 + 섹션별 조립.
- 한쪽 실패(재시도 후) → 다른 writer cross-fill(빈 섹션 0), 둘 다 실패 → 수치 폴백.
- 섹션별 성공/폴백 출처가 audit 로그로 남는다.
- detail2 계약 형상 불변(3-way lockstep), 벤더명 비노출.
</success_criteria>

<output>
Create `.planning/phases/13-llm-coaching-detail/13-C-section-dual-coach-SUMMARY.md` when done
</output>
