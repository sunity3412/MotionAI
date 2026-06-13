# Phase 4: 다중 시점 촬영 UX + occlusion confidence 게이트 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 4-ux-occlusion-confidence (재정의: Camera Angle AI)
**Areas discussed:** Phase 4 정체성, 합성 트리거 정책, 사용자 노출 정책, Fallback 실패 처리, 정은지 5영상 재처리, Spike 선행

---

## Pre-discussion: ROADMAP vs memory 충돌 박제

**Claude 가 먼저 flag:** ROADMAP.md Phase 4 ("정면+측면 2시점 업로드 UX") 가 belle 의 2026-06-01 박제 [[single-camera-first-multi-view-last]] + 2026-06-10 박제 [[camera-angle-ai-single-view-synth]] 와 직접 모순. 메모리 [[plan-vs-pivot-cross-check]] 정합.

코드에 이미 occlusion / confidence 인프라 존재 박제 (temporal / body_normalizer / force_signals / scene_finder).

---

## Phase 4 방향 (foundational)

| Option | Description | Selected |
|--------|-------------|----------|
| Camera Angle AI 로 redesign | 단일 영상 → AI 가상 다각도 합성 (Higgsfield 류) + occlusion confidence 게이트. 다중 시점 UX 완전 제거. | ✓ |
| Occlusion 게이트만 좁힘 | 단일 카메라 confidence 게이트 + "추정" 표기 UX 만. AI 합성은 후속 phase. | |
| ROADMAP 원안 유지 | 정면+측면 2시점 업로드 UX 그대로. | |
| Phase 4 자체 보류 | Phase 13 우선 끝내고 Phase 4 는 나중. | |

**User's choice:** Camera Angle AI 로 redesign
**Notes:** 2026-06-10 pivot 박제 정합. ROADMAP.md SC #2 폐기 + 후속 plan-phase 에서 SC 갱신 필요.

---

## 재확인 (혼동 해소)

belle 가 첫 multiSelect 답에서 "사용자에게 여러 각도 촬영하라 하는건 없애는거 아님? 왜 백엔드 처리로 남기는겨?" 라고 검증.

**Claude 해명:** "백엔드 처리" = 사용자 1 영상 → 서버에서 AI 합성 (사용자 무관). 사용자 UX 에는 다각도 요구 0.

| Option | Description | Selected |
|--------|-------------|----------|
| AI 합성 (추천) | 사용자 1 영상 → 서버에서 AI 가상 다각도 합성 → occlusion 보완. 사용자는 합성 여부도 모름. | ✓ |
| Confidence 게이트만 | AI 합성 없이 단일 카메라 영상만 분석. 저신뢰 프레임 "추정" 표기 + 경고. AI 합성은 후속 phase. | |

**User's choice:** AI 합성
**Notes:** 2026-06-10 belle pivot 재확인.

---

## 영역 선택 + belle 의 4가지 본질적 질문

belle 4개 영역 모두 multiSelect + 다음 4가지 질문 첨부:

1. "지금 신규 업로드 영상도 있는데 왜 5영상만 이야기하는지? 5영상 중에서도 지금 분석 이상한거 많음."
2. "품질 좋은 영상이면 카메라 앵글 기능이 없어도 되는건지?"
3. "영상 카메라 앵글의 경우 초가 늘어날 수록 비용인데 자주 돌린다고 했을 때 비용 절감 방법이 있는지?"
4. "키포인트 불일치 부분만 백단에서 돌리고 신뢰를 높이는 방법을 말하는건지?"

**Claude 답변 정리:**
- Q1: 신규 영상 = default 새 파이프라인. 5영상은 reference, 재처리 여부가 별도 결정.
- Q2: 예 — 합성은 보완 도구, default 아님. 깔끔한 영상은 합성 안 돌림.
- Q3: 4가지 절감 (조건부 트리거 / 부분 합성 / 캐싱 / 다운샘플). belle 직관 (조건부 + 부분 합성) = 비용 효율 최고.
- Q4: 예 — 영상 전체 합성 X, 신뢰도 낮은 구간/관절만 핀포인트 보완.

**박제된 D-3:** 합성 = 조건부 + 부분 합성. 영상 전체 합성 X.

---

## Q1. 사용자에게 AI 보완 적용을 알릴까?

| Option | Description | Selected |
|--------|-------------|----------|
| 완전 블랙박스 | 사용자는 AI 보완 일어난 지 모름. 점수 / 설명만 보임. | ✓ (default) |
| confidence 표기만 | "이 구간은 추정" 같은 메시지. Phase 12.5 자세히 모달 정합. | |
| 투명히 명시 | 자세히 모달에 "AI 보완 적용됨" 설명 추가. | |

**User's choice:** 완전 블랙박스 + "사용자가 평소 못 보는 자기 각도 보고 싶어할 수도 — 구글맵 뷰 같은"
**Notes:** MVP 블랙박스 박제. belle 의 "구글맵 뷰" 비유는 v2 deferred ("다각도 뷰 사용자 노출 — 스트리트뷰 식").

---

## Q2. 합성 실패 / 시간초과 시 어떻게?

| Option | Description | Selected |
|--------|-------------|----------|
| 단일 카메라 결과로 graceful degrade (추천) | 합성 안 되면 1차 RTMW 결과로 분석 계속. 결과 화면에 정확도 제한 표기. | ✓ (Claude 판단) |
| 분석 자체 실패 | 합성 안 되면 분석 안 함. 채점 품질 안 좋을 바엔 아예 차단. | |

**User's choice:** "지금 단일 카메라 결과가 엉망인데 실패시 바로 1번으로 가는게 좋을지... 모르겠네."
**Claude reasonable call:** graceful degrade (옵션 1) + 결과 화면에 "AI 보완 실패 — 가림 구간 정확도 제한적" 명시.
**Notes:** belle 의 "분석 정확도 최우선" 메모리 [[feedback-analysis-first]] 와 "전혀 못 받는 것보단 부정확하게 받는 게 나음" 균형. confidence warning code 신규 (`ai_synthesis_failed` 후보) — plan-phase 박제.

---

## Q3. 정은지 5영상 재처리할까?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 4 에서 재처리 (추천) | 파이프라인 완성 후 자동 재처리. mode1 비교 양쪽 원터필. belle 지적 "5영상 분석 이상" 도 해결 가능성. | ✓ |
| Phase 14 에서 재처리 | Phase 14 (정은지 reference 등록) 에서 재등록 시 재처리. Phase 4 는 신규 영상만. | |
| 재처리 안 함 | 5영상 = 이미 품질 좋은 영상이니까 스킵. | |

**User's choice:** Phase 4 에서 재처리
**Notes:** belle 가 지적한 "5영상 분석 이상" (Phase 17 G4 occlusion FP, Phase 8.1 axis severity) 해결 가능성 동시 검증.

---

## Q4. AI 합성 신기술 PoC 필요한가?

| Option | Description | Selected |
|--------|-------------|----------|
| Spike 먼저 (추천) | Phase 4 본격 진입 전 /gsd:spike 로 Higgsfield / Magnific / Gemini Vision 등 PoC. 검증 후 plan-phase. | ✓ |
| Spike 없이 바로 plan | plan-phase 의 phase-researcher 가 리서치 → 바로 구현. 빠르지만 기술 검증 없이 risk. | |

**User's choice:** Spike 먼저 + "Gemini Vision 은 지금 사용하고 있으니 이걸 기준으로 비교한 다음 다른 API가 월등히 좋으면 변경으로. 그럴 경우 그 API가 앵글변환, AI합성 뿐 아니라 분석에도 효과적인지 파악"
**Notes:** D-12, D-13 박제 — Gemini Vision = 기준선. 비교 API 평가 3축 (앵글 변환 / 합성 품질 / RTMW 재추론 정확도 향상) 모두 PASS 시에만 교체.

---

## Claude's Discretion

다음 영역은 spike + plan-phase researcher 가 처리:
- 구체 confidence 임계값 (RTMW score N% cutoff)
- 부분 합성 윈도우 길이 (몇 프레임)
- 캐싱 키 / TTL 전략
- 비용 dashboard / 예산 알람 구체화
- 신규 warning code 명명 (`ai_synthesis_failed` 등 가후보)

## Deferred Ideas

- 다각도 뷰 사용자 노출 (구글맵 스트리트뷰 식) — v2 별도 phase
- 사선/뒤 시점 합성 — v2
- 스피닝 폴 핸들링 — v1.5 (Phase 1 D-10)
- 합성 결과 캐싱 + 재사용 — Phase 4 plan-phase deferred
- 비용 dashboard / 예산 알람 — 별도 운영 phase
- transparency 모달 ("AI 가 보완했어요") — v2
- G4 정은지 occlusion FP 가드 — Phase 17 Plan 17-02 협업 (별도 plan X)
