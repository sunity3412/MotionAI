# Phase 5: Gemini 기술 인식기 (분류 한정) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-04
**Phase:** 5-gemini
**Areas discussed:** Scope, Output Shape, Fallback Policy, Call Architecture

---

## Pre-discussion clarifications (belle 요청)

belle 가 의논 시작 전 두 차례 ground 정렬 요청:

1. **"Gemini 로 하고자 했던 게 뭐지? 어제 실패한 부분 사용한다고 했던 것?"** → Gemini = FallbackRecognizer 한계 (IPSF criteria 일률 180° 가정) 의 대체. Plan 23 angle 0/5 root cause 1번 해결. 좌표·점수·심사 출력 절대 금지. ground 박제 일치 확인 완료.
2. **"EXTEND/BENT 동적 산출 이 구체적으로 무슨 뜻인가"** → ref-foxtop yaml hold_moment 6관절 일률 180° 가정 vs Gemini 영상별 관절별 동적 라벨링 비교 + 정지 사진/동영상 비유 + 학원 일상어 (들어가기/포즈/정점/마무리) 풀이.
3. **"내가 원하는 분석의 퀄리티 최우선에서 지금 뭐가 실패해서 제미나이를 사용해야하는데, 제미나이를 사용하면 이게 기대된다"** → 3컬럼 정리: 실패 = Plan 23 angle 0/5 위양성 폭주 / Gemini 필요 = 자세 의도 판단 자동화 / 기대 = yaml IPSF 임계값 + 라벨만 동적 → 위양성 0 + 진짜 실패만 잡기.
4. **"MVP가 됬든 이정도면 돈 내겟는데? 이런 느낌은 들어야 실증의 의미가 있을테니까"** → "돈 내겠는데?" 게이트 = Phase 1 + 5 + 6 + 7 + 9 + 12 + 13 chain 완성 시점. Phase 5 단독 = 위양성 0 + 수치 신뢰 1차 게이트만 박제 (specifics 박제됨).
5. **"우리가 최고 목적으로 하는 완벽한 분석 결과물(코치가 껴야하는 부분은 제외)은 언제쯤 도달하지?"** → 분석 정확도 chain 의 5 핵심 단계 박제 (측정 / 라벨링 / 체형 보정 / 실패 원인 / 기준 모션) + 약 20~30 plans 추정 + Phase 5 = chain 1차 게이트.

---

## Scope (인식 범위)

| Option | Description | Selected |
|--------|-------------|----------|
| 5영상 인버트 계열 우선 | ROADMAP 3~5 동작군. Plan 23 sweep 게이트 직결. yaml 5개 이미 박제. | ✓ |
| Phase 16 AKA 13개 전부 | TERM-DATA-01 13 매핑 전부 v1 에 포함. yaml 8개 신규 작성 + IPSF source_ref 검증 필요. | |
| 5영상 + 폭스탑 하이브리드 | sweep 5영상 + 분기 2 정은지 reference 1~2개. yaml 1개 신규 + 시연 다양성. | |
| 무제한 인식 (catalog 없음) | Gemini 가 모르면 fallback, 알면 라벨링. 실용 scope = yaml 있는 5개와 동등. | |

**User's choice:** "5영상 인버트 계열 우선 (Plan 23 sweep 게이트 직결)"
**Notes:** chain 1차 게이트 통과 최단 경로. belle "돈 내겠는데?" 게이트는 별도 박제 (Phase chain 매핑만, Phase 5 게이트 X) — D-01.

---

## Output Shape (인식 출력 구조)

| Option | Description | Selected |
|--------|-------------|----------|
| (X) hold 라벨 1세트 | 영상 전체 = 1 TechniqueProfile. 정지 사진 평가. v2 확장 시 코드 변경 필요. | |
| (Y) KeyMoment 4세트 라벨 | setup/hold/peak/release 4단계 라벨. v1 = hold 채점, 나머지 박제만. v2 yaml 채우면 자동 활성. | (의논 중) |
| (Z) hold 라벨 + timestamp | hold 정확 시점 + 라벨. Plan 12 frame-mean 한계 해결. 시간축 흐름 평가 X. | |
| (Y+Z) 4단계 라벨 + 각 단계 timestamp | (Y)+(Z) 통합. 최대 파워. 호출 1회 동일, JSON 4 fields 추가, 코드 3~5줄 추가. | ✓ |

**User's choice:** "(Y+Z) 4단계 라벨 + 각 단계 시점 timestamp (추천 재확인)"
**Notes:** belle 가 처음 (Y) 와 (Y+Z) 사이 고민 — "(Y+Z) 너무 무거운가? 폴댄서한테 불필요한가?" 질문. 부담 평가 박제 (실제 무거움 작음, timestamp 오차 ±2초만 새 위험) + yaml 박제 부담 분산 효용 + Plan 12 frame-mean 한계 자연 해결 → (Y+Z) 재추천. belle 수락. D-04 ~ D-08.

---

## Fallback Policy (3케이스 분리)

| Option | Description | Selected |
|--------|-------------|----------|
| (A) 3케이스 통합 — FallbackRecognizer 공통 | 세 케이스 모두 FallbackRecognizer + "신뢰도 낮음" 공통 표기. 단순, 단 TERM-COPY-01 카피 path X. | |
| (B) 3케이스 분리 — 박제 변 정합 | API 실패 / Low conf / 미등록 각각 다른 path. SCORE-05 + TERM-COPY-01 정합. | ✓ |
| (C) 2케이스 분리 — Gemini 실패 vs 미등록 | (1)+(2) 묶음, (3) 별. 중간 복잡도. low conf 계측 임계 로직 필요. | |

**User's choice:** "(B) 3케이스 분리 — 박제 변 정합 (추천)"
**Notes:** D-09 ~ D-11. Low confidence 임계값 정의 = 별 plan 책임 (5영상 sweep 실측 후 박제).

---

## Call Architecture (호출 위치 · Cascade · 캡싱)

| Option | Description | Selected |
|--------|-------------|----------|
| (A,A,A) Pod 안 + 3.1 Pro 일관 + hash 캡싱 | 박제 정신 모두 정합. 시연 비용 0, sweep 재실행 효율, 퀄리티 일관. | ✓ |
| (B,B,A) Lambda 이동 + Flash→Pro cascade + hash 캡싱 | Pod GPU 효율 + 비용 절감 결합. 코드 복잡도 증가. low conf 임계값 강세 박제 필요. | |
| 일부 변경 | 3 sub-area 중 1개만 다른 방향. | |
| 다른 조합 | belle 추가 입장 | |

**User's choice:** "(A,A,A) — 단, 3.0은 아니고 3.1이네 지금 다시 확인함. 1번으로 진행하되 3.0은 삭제해도 될 듯"
**Notes:** D-12 ~ D-16. **belle 박제 갱신**: Gemini 3.1 Pro 단일 (3.0 삭제). 이전 STATE.md "Phase 5 권장 모델" 3.0/3.1 Pro 양옵션 박제 → 3.1 Pro 단일로 갱신. specifics 박제됨.

---

## Claude's Discretion

- Firestore `gemini_result` 박제 schema 구체적 필드 = 출력 구조 D-04 박제로 자연 결정 (gemini_moment_extractor.py 의 KeyMoment dataclass 직렬화).
- 영상 입력 형식 (전체 영상 vs sample frames) = Gemini multimodal SDK API 권장 path (10~30초 폴 영상 전체 입력이 표준).
- 프롬프트 설계 (좌표/판단/점수 거부 강제 + JSON schema 강제) = 기존 reject patterns + response_mime_type=application/json — 구체 prompt 문구는 planner 자유.

## Deferred Ideas

- Phase 16 AKA 매핑 13개 + 정은지 reference 비등재 동작 확장 — v2 또는 후속 plan
- Cascade 비용 절감 (3.5 Flash → 3.1 Pro) — v2 비용 모니터링 후 별 plan
- setup/peak/release yaml criteria 박제 — JUDGE-DATA-01 v1 평행 (belle/강사/NotebookLM)
- Low confidence 임계값 정의 — 5영상 sweep 실측 후 별 plan
- peak 채점 활성 시 timestamp 정확도 재평가 — v2 plan
- HoughPoleDetector 미설치 fix — Phase 1 잔여 또는 Plan 26
- AKA 매핑 vs yaml criteria 정합 belle/NotebookLM 재검증 — Phase 16
- Gemini API quota / 비용 모니터링 알람 — v1 후순위
- "신뢰도 낮음" UI 카피 + Figma 컴포넌트 — Phase 12 또는 별 plan
