# Phase 7: 차이 분류 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 07-difference-classification
**Areas discussed:** 분류 룰, 결과 카피 출처, 동작 단계 분할, 카피 톤 + 금지/권장 표현

---

## Gray-area menu

belle 첫 응답 = "쉬운 설명이 필요하다 용어들을 다 모르겠어". 기술 용어 (schema / category enum / phase granularity) 제거 후 평어 (vision-level) 로 4 영역 재제시 → 4 가지 모두 의논 선택.

---

## Area 1 — 분류 룰 (allowed / needs_adjustment / uncertain 결정 기준)

### Q1 분류 룰 선정

| Option | Description | Selected |
|--------|-------------|----------|
| body_type_adjusted 플래그 기반 | Phase 6 박제 boolean 단독 룰 | |
| scaleProfile 축 매칭 | 부위별 deficit + scaleProfile 매칭, 정교 but 룰 폭발 | |
| deduction 크기 단독 | abs(deduction) ≤ 0.2 → allowed, 단순하지만 부정확 | |

**User's choice:** "당연 1번이긴 한데 한가지 궁금한점... 체형을 보정해주잖아 기술로? 160cm와 140cm라 한다면 140cm(수강생 기준)에 맞춰 분석해준다잖아? 근데 체형이 안 맞아서 남은 진짜 차이... 라는게 이해가 잘 안가"

**Notes:** Claude 가 160 vs 140 비유로 body_type_adjusted 의미 설명 (raw 좌표 = 키 차이 섞임 = allowed, 정규화 좌표 = 키 뺀 후 차이 = needs_adjustment). 또한 5 IPSF deficit 대부분이 정규화 좌표 측정이라 단순 플래그만으로는 needs_adjustment 과다 위험을 박제 — deduction 크기 보조 룰 추가 필요.

### Q1-followup 조합 룰 최종

| Option | Description | Selected |
|--------|-------------|----------|
| body_type_adjusted + deduction 크기 조합 (Recommended) | True + abs ≤ 0.2 → allowed, True + > 0.2 → needs, False → uncertain | ✓ |
| 단순 플래그 룰 유지 | 분류 단순화 but allowed 빈 리스트 위험 | |
| belle 추가 아이디어 | 자유 입력 | |

**User's choice:** 조합 룰 (Recommended) 선택

### Q2 uncertain 임계

| Option | Description | Selected |
|--------|-------------|----------|
| 0.5 임계 + per-finding 0.5 동시 적용 (Recommended) | Phase 6 D-06-U1 정합, 일관성 | ✓ |
| 0.5 + uncertain 카피 별도 박제 | 동일 임계 + 별도 카피 박스 | |
| 0.7 임계 (엄격) | 잘못 가르침 차단 우선, but 절반 uncertain 가능 | |

**User's choice:** "사용자 피로감이 드는 상황이 어떤 상황인지 한번 제시 해보고 결정하자 2번이 나은거 같은디... 피로감이 생긴다고 하니" → Claude 가 0.5 / 0.7 시나리오 박제 후 0.5 임계 + per-finding 0.5 동시 적용 (Recommended) 선택

**Notes:** belle 박제 정신 = 분석 정확도 우선 but uncertain 카피로 정직성 박제 ("가림/회전으로 AI 가 확신 못 했어요").

---

## Area 2 — 결과 카피 출처

### Q1 카피 출처

| Option | Description | Selected |
|--------|-------------|----------|
| 백엔드 캔드 템플릿 (Recommended) | deficit_code + category + joint_key → Korean canned mapping table | ✓ |
| Phase 11 LLM 완전 위임 | Phase 7 = key 만, Phase 11 Cerebras = 한국어. Phase 11 dep 추가 | |
| 프런트 매핑 | 백엔드 = enum, 프런트 = 한국어. Phase 12.5 패턴 | |

**User's choice:** 백엔드 캔드 템플릿 (Recommended)

### Q2 카피 작성 주체

| Option | Description | Selected |
|--------|-------------|----------|
| Claude 가 research §10.1 박제 + belle 검수 (Recommended) | Claude 초안 + plan 단계 belle 검수 | ✓ |
| belle 직접 모든 카피 작성 | 100% 강사/클라이언트 톤 정합, but belle 시간 증가 | |
| belle + Claude 다음 틴 함께 작성 | plan 단계 함께 박제 | |

**User's choice:** Claude 가 research §10.1 박제 + belle 검수 (Recommended)

---

## Area 3 — 동작 단계 분할

### Q1 v1 phase 분할 포함 여부

| Option | Description | Selected |
|--------|-------------|----------|
| v1 = 단일 hold moment, phase 필드 nullable (v2 확장) (Recommended) | Phase 5 우회, 분석 정확도 손실 적음, v2 자연 확장 | ✓ |
| Gemini key_moments 의존 추가 (4 phase v1) | Phase 5 박제 확장 필요, dep 늘어남 | |
| Phase 8 통합 대기 | Phase 7 본찰 축소, schema 재도입 회귀 위험 | |

**User's choice:** v1 = 단일 hold moment (Recommended)

---

## Area 4 — 카피 톤 + 금지/권장 표현 룰

### Q1 카피 룰 박제

| Option | Description | Selected |
|--------|-------------|----------|
| research §10.1/§10.3 + memory 박제 3종 추가 (Recommended) | 가능성 언어 + AI 보조 톤 + 부위별 원인 언어 추가 | ✓ |
| research 그대로만 박제 | 권장 4종 + 금지 6종 만 박제 | |
| belle 가 추가할 표현 직접 제시 | 자유 입력 | |

**User's choice:** research §10.1/§10.3 + memory 박제 3종 추가 (Recommended)

---

## Claude's Discretion

- 18 canned string 본문 작성 (5 IPSF × 3 category + pose_reliability_low × 3) — Claude 가 research §10.1 톤 박제 + 톤 정합 확장, belle 가 plan 단계 검수
- uncertain 화면 표시 방식 (recommendedFocus 통합 vs 별도 uncertainFindings) — researcher / planner 가 Phase 12 와 책임 경계 박제 시 결정
- deduction 임계 0.2 의 5 영상 sweep 검증 — researcher 영역
- 카피 매핑 키 차원 (joint_key 폭발 완화 위한 부위 그룹화) — researcher / planner 박제

## Deferred Ideas

- 동작 단계 (entry/lock/transition/final_shape/hold) v2 확장 — Phase 8 또는 Plan 13 통합 시
- 카피 LLM 풍부화 — Phase 11 (CoachCommentHook + Cerebras) 책임
- categoryByPhase aggregate (v2) — phase × category cross-tabulation summary
- CoachCommentHook 의 openQuestionsForCoach 자동 populate — Phase 11 wiring
- mode3_first Page 9 단독 분류 룰 변형 — researcher 영역
