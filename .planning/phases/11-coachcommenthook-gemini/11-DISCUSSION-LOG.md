# Phase 11: CoachCommentHook 데이터 구조 + Gemini 자연어 번역만 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 11-coachcommenthook-gemini
**Areas discussed:** Hook 구조 & 13 detail2 관계, AI 필드 생성 주체 & "번역만" 강제, v1 노출 범위, "강사 보조 도구" 포지셔닝 카피

---

## Hook 구조 & 기존 13 detail2 관계

| Option | Description | Selected |
|--------|-------------|----------|
| 공존 / 별도 유지 | detail2(수강생용 per-관절)는 그대로, CoachCommentHook(per-리포트 코치협업)을 새로 추가. 13 재작업 0. | ✓ |
| CoachCommentHook 단일 소스 | Hook 을 진실 소스로, detail2 파생. 13 파이프라인 큰 재작업. | |
| detail2 흡수/대체 | per-관절 detail2 제거, Hook 으로 통합. 자세히 모달 UX 재설계. | |

**User's choice:** 공존 / 별도 유지

| Option | Description | Selected |
|--------|-------------|----------|
| 리포트별 1개씩 | BodyComparisonReport·ForcePatternInference 각각에 부착(2개). 출처 보존. | ✓ |
| 분석당 top-level 1개 | 분석 최상위 1개, 두 리포트 종합. "모든 리포트에 부착" 문구와 어긋남. | |

**User's choice:** 리포트별 1개씩
**Notes:** 로드맵 success #2 "모든 리포트에 부착" 직접 충족 + 질문·큐 출처 보존.

---

## AI 필드 생성 주체 & "번역만" 강제

| Option | Description | Selected |
|--------|-------------|----------|
| 기존 GeminiCoachWriter 재사용/확장 | 13 의 GeminiCoachWriter 에 report-hook 메서드 추가. 인프라 재사용. | ✓ |
| Phase 11 전용 별도 writer | 전용 "번역만" 모듈. 책임 명확하나 LLM 호출 추가. | |
| You decide | planner 재량. | |

**User's choice:** 기존 GeminiCoachWriter 재사용/확장 (모델 = Gemini, 로드맵 고정)

| Option | Description | Selected |
|--------|-------------|----------|
| 프롬프트 + 단위테스트(금지패턴 0) | 시스템 프롬프트 제약 + 출력에 좌표/점수/판정 0 assert. | ✓ (재확인) |
| 프롬프트 제약만 | 가볍지만 누락 자동검출 불가. | |
| 프롬프트 + 런타임 sanitize | 가장 강하나 자연어 손상 위험. | |

**User's choice:** belle 가 "번역만/금지"의 의미를 질문 → 개념 설명 후 원칙 확정.
**Notes:** belle 혼동 = "숫자 말하는 AI 는 Gemini Vision + omni 아닌가?" → 측정엔진(점수 주인) / Phase 11 텍스트 레이어(영상 X) / Gemini Vision·omni(영상 직접, Phase 17) 세 겹 구분으로 해소. **핵심 결정: Phase 11 = Vision 독립 텍스트/데이터 레이어. 영상 직접 보는 Gemini Vision/omni 코칭 = Phase 17 이연.** 원칙 = Gemini 는 finding 번역만·새 수치/판정 안 만듦. 강제 메커니즘(프롬프트+단위테스트)은 Claude 재량.

---

## v1 노출 범위 (데이터 vs 화면)

| Option | Description | Selected |
|--------|-------------|----------|
| openQuestionsForCoach만 노출 | "강사에게 확인할 점" 섹션. 학원 도입·강사 보조 직접 지원. 나머지 데이터만. | ✓ |
| 데이터만 저장, 화면 0 | COACH-01 "UI는 v2" 문자 그대로. 화면은 13 detail2 로 충분. | |
| summary + openQuestions 둘 다 | 더 풍부하나 13 detail2 와 중복·복잡. | |

**User's choice:** openQuestionsForCoach만 노출
**Notes:** COACH-01 "UI/입력은 v2" 는 강사 입력 부분을 미루는 뜻 → AI 생성 읽기전용 필드 노출은 v1 가능. coachComment/reviewedBy 는 v2.

---

## "강사 보조 도구" 포지셔닝 카피 (FEED-03)

| Option | Description | Selected |
|--------|-------------|----------|
| 상단 1줄 + 코치섹션 헤더 | 가벼운 상단 1줄 + "강사에게 확인할 점" 섹션이 포지셔닝 강화. | ✓ |
| 점수 옆 각주만 | 최소. 포지셔닝 약함. | |
| 전용 강조 배너 | 강하나 매 분석 반복 노출 거슬림. | |

**User's choice:** 상단 1줄 + 코치섹션 헤더

---

## Claude's Discretion

- "기준 모션 = 하나의 참고일 뿐" 문구 위치 (Mode 1 비교 화면 기준모션 라벨 근처).
- CoachCommentHook 필드 세부 스키마 / Firestore flat 저장 / nullable.
- "번역만" 강제 단위테스트 fixture, fallback canned 카피 톤.
- autoFindingsSummary / suggestedCues 내용 길이·개수.

## Deferred Ideas

- Gemini Vision/omni 영상 직접 코칭 → Phase 17 (Vision Integration "coach" 영역, 본 phase 와 겹침 — 조율 필요).
- 코치 입력 UI(coachComment 작성, reviewedBy 배정) → v2.
- 마이페이지 코칭 글 스타일 선택([[coaching-tone-customization]]) → 본 phase 외.
