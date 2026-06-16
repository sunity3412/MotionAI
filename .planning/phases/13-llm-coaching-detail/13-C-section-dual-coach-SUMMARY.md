---
phase: 13-llm-coaching-detail
plan: C
subsystem: llm-coaching-detail
status: complete
completed: 2026-06-16
tags: [coach, dual-track, llm, section-report, gemini, cerebras, ui-modal]
requires: [13-A, 13-B]
provides:
  - assemble.assemble_dual_coach_sections (섹션 출처 태깅 조립 + cross-fill audit)
  - pipeline dual-track (둘 다 호출 + 재시도/타임아웃 + 계층형 폴백 + 섹션 출처 로깅)
  - 자세히 모달 4섹션 세로 스택 렌더 (원인/교정 처방/부상 위험/강사 확인)
affects:
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - app/src/types/analysis.ts
  - app/src/components/CoachingTipDetailModal.tsx
tech-stack:
  added: []
  patterns: [section-dual-coach, hierarchical-fallback, cross-fill, audit-logging]
key-files:
  created:
    - backend/tests/phase13/test_section_dual_coach.py
  modified:
    - backend/shared/python/sunity_shared/analysis/assemble.py
    - backend/functions/pipeline/app.py
    - app/src/types/analysis.ts
    - app/src/components/CoachingTipDetailModal.tsx
decisions:
  - "섹션 배분 LOCKED: 원인/강사확인=Gemini, 교정처방/부상위험=Cerebras"
  - "출처는 source 필드 아님 — 섹션 조립 결과 + audit dict 로만 표현 (벤더명 비노출, 3-way lockstep 최소)"
  - "계층형 폴백 3단: 양쪽 호출+재시도 → 한쪽 실패 cross-fill (빈 섹션 0) → 둘 다 실패 수치 폴백"
  - "UI 라벨 = 기능 라벨만 (원인/교정 처방/부상 위험/강사 확인), 벤더명 렌더 0"
requirements: [PERS-03]
metrics:
  duration: ~35m
  tasks: 3
  files: 5
  tests_added: 7
  commits: 3
---

# Phase 13 Plan C: 섹션형 듀얼 coach 보고서 Summary

coach LLM 보고서를 출처별 라벨 섹션으로 분리: 토글(택1)을 "둘 다 호출 + 섹션별 조립"으로 확장하고, 원인=Gemini / 교정 처방=Cerebras / 부상 위험=Cerebras / 강사 확인=Gemini 로 배분해 belle 핵심가치 "왜 안 되는지 + 무엇이 필요한지"를 자세히 모달 4섹션 세로 스택에 그대로 매핑했다.

## What was built

### Task 1 (`8ec9dc5`) — 섹션 출처 태깅 조립 + 계층형 cross-fill 폴백 (순수 로직)
- `assemble.py` 에 순수 함수 `assemble_dual_coach_sections(gemini_details, cerebras_details, joint_keys)` 추가 — `(merged_details, section_audit)` 튜플 반환.
  - 13-C locked 배분: 원인(causes title/explanation)=Gemini, 교정 처방(causes[].fix)=Cerebras, 부상 위험(injuryRisk)=Cerebras, 강사 확인(coachNote)=Gemini.
  - 한쪽 writer 가 해당 관절키를 비웠으면(빈 dict / causes 누락) → 다른 writer 의 같은 섹션으로 cross-fill (빈 섹션 0) + `crossFilled` audit 기록.
  - 양쪽 모두 누락 관절키 → detail2 생략 (`build_tips` 의 수치 폴백이 detail 만 채움).
  - `injuryRisk` 는 양쪽 다 없으면 키 자체 생략 (옵셔널 계약 정합).
- detail2 계약 형상 불변: `{causes:[{title,explanation,fix}], injuryRisk?, coachNote}`. **source 필드 추가 안 함** (벤더명 비노출 + 3-way lockstep 최소).
- `analysis.ts` `CoachingTipDetail` 주석에 4 기능 섹션 라벨 매핑 박제 (형상 동일, 3-way lockstep 유지).
- `test_section_dual_coach.py` 7 케이스: 정상 배분 / 형상 불변·source 부재 / Gemini 누락 cross-fill / Cerebras 누락 cross-fill / 둘 다 누락 detail2 생략 / injuryRisk 양쪽 부재 생략 / audit 형상.

### Task 2 (`4f7f7aa`) — pipeline dual-track 확장
- `_process` coach 호출부를 "양쪽 호출 + 섹션 조립"으로 확장:
  - `_call_coach_writer_with_retry`: 시도당 재시도 1회 래퍼 (`_COACH_RETRY_ATTEMPTS=2`). 예외/fallback dict → 재시도, None 반환 0.
  - gemini/cerebras 둘 다 호출 (단일 `_build_coach_context` 공유, B3 정합) → `assemble.assemble_dual_coach_sections(top 3 키)`.
  - 한쪽 실패 → cross-fill 자동, 둘 다 실패 → `coach_details={}` → `build_result` 수치 폴백 (최후 바닥).
  - 섹션별 출처 + cross-fill 관절 + 양쪽 실패 사유를 `log.info` audit (성공/폴백률 실측 전환 근거).
  - `gemini_b` audit 에 `dualTrack` / `sectionAudit` / `crossFilledJoints` 동봉 — Firestore flat-dict 검증 통과 확인 (runtime 검증).
- `GEMINI_COACH_ENABLED=0` 시 기존 Cerebras-only path 보존 (회귀 0).

### Task 3 (`340d0c9`) — 자세히 모달 4섹션 세로 스택 렌더
- `CoachingTipDetailModal.tsx` 의 `CausesSection` 을 4섹션 세로 스택으로 재구성: 원인(causes title+explanation) → 교정 처방(각 cause.fix 모음) → 부상 위험(injuryRisk 있을 때만) → 강사 확인(coachNote).
- 섹션 헤더 = 기능 라벨 한글 고정 문자열만. **벤더명(Gemini/Cerebras) 렌더 텍스트 0** (코멘트 2곳 외 JSX 0).
- 탭/아코디언 기각 (원인+처방 동시 비교가 핵심, 13-C locked). 색/radius/spacing = theme 토큰 (`colors`, `radius`) + 신규 섹션 간격 스타일.
- detail2 없을 때 기존 `noDetail` 폴백 유지 (회귀 0). 13-A 보완운동 카드는 별도 유지 (통합 X).

## Verification

- `tests/phase13` **88 passed** (81 baseline + 7 신규, 회귀 0).
- `test_section_dual_coach.py` 7/7 통과 (배분 / cross-fill 양방향 / 둘 다 누락 수치폴백 / audit 형상).
- pipeline + geminib wiring + dispatch 회귀: `phase13 + pipeline + geminib + dispatch` **131 passed**.
- `app npm run typecheck` clean (tsc --noEmit).
- 자세히 모달 벤더명 렌더 텍스트 0 (grep 확인 — 잔여 2건은 코드 주석).
- `gemini_b` dual-track audit dict Firestore flat-dict 검증 통과 (runtime).
- `GEMINI_COACH_ENABLED=0` 시 기존 Cerebras-only path 분기 보존.

## Deviations from Plan

None — plan executed exactly as written. 신규 패키지 install 0 (기존 cerebras-cloud-sdk / Gemini 어댑터 재사용, T-13C-SC accept 정합).

## Scope boundary (13-C 빌드 종료점)

13-C 빌드는 단위/타입 게이트(pytest + tsc)까지. **실 영상 → 실 dual-LLM 섹션 조립 E2E 라이브 검증 = Phase 15(실증) scope** — Pod 기동 / 라이브 LLM 호출은 본 빌드에서 수행하지 않음. "실증 시 둘 중 하나 drop 여부" = Phase 15 검증 기준 (13-C 빌드 ≠ drop 결정).

## Known Stubs

None — 모든 섹션이 실 writer 결과 또는 cross-fill/수치 폴백으로 채워짐 (빈 섹션 0 by construction).

## Pre-existing (out of scope)

- `backend/tests/test_spike_*.py` / `test_sweep_*.py` 11개 collection ImportError = 사전 존재 (mediapipe/rtmpose 등 heavy ML deps 미설치). 본 plan 변경과 무관 — 수정하지 않음.

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/assemble.py (assemble_dual_coach_sections)
- FOUND: backend/tests/phase13/test_section_dual_coach.py
- FOUND: backend/functions/pipeline/app.py (_call_coach_writer_with_retry, dual-track block)
- FOUND: app/src/types/analysis.ts (CoachingTipDetail 13-C 주석)
- FOUND: app/src/components/CoachingTipDetailModal.tsx (4섹션 세로 스택)
- FOUND commit: 8ec9dc5 (Task 1)
- FOUND commit: 4f7f7aa (Task 2)
- FOUND commit: 340d0c9 (Task 3)
