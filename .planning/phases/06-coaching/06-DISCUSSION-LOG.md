# Phase 6: 체형 정규화 비교 엔진 (coaching 모드) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 6-coaching
**Areas discussed:** (A) 정규화 대상 / 좌표 변환 방향, (B) mode 분기

---

## Pre-discussion check — pivot conflict

| 사실 | 메모 |
|---|---|
| ROADMAP `.planning/ROADMAP.md:407-415` "Phase 2~11 보류 (파일럿 후 v1.5)" | belle 2026-06-07 이전 결정 |
| STATE.md line 51 "Phase 2 → 6 → 7 → 12 → 13" 진입 chain | belle 2026-06-07 이후 결정 (Phase 2 close-out 박제) |
| belle 2026-06-08 명시: "오버레이, 체형 정규화 힘 패턴은 필수적이지. 어떻게든 기필코 개발하려고 하는 게 지금" | v1 으로 끌어올림. 보류 reasoning 갱신 필요 (deferred) |

**최초 응답 박제 사항** — Claude 가 직전 세션 끝에 "Phase 6 진입" 박제 후 본 세션 시작에서 pivot 의문을 다시 띄운 echo 잘못. belle 짚어줌. 박제 정정 후 진행.

---

## Area (A) — 정규화 대상 / 좌표 변환 방향 / 세그먼트 적용 / OFF 분기

### Q1 — Phase 6 출력 본체 (점수 보정 vs 좌표 재투영)

| Option | Description | Selected |
|--------|-------------|----------|
| 점수만 보정 (deficit 차감) — 키포인트 무수정 | minimal change. Phase 12 오버레이는 raw 키포인트 표시. | |
| 키포인트 재투영 — 점수 + 시각화 모두 정규화 | normalizeStudentPoseToProReference 가 좌표 자체 변환. 직관적이지만 복잡. | |
| 둘 다 산출 — 점수 보정 + scale ratio 메타 (책임 분리) | Phase 6 본체 = 점수 보정, Phase 12 가 메타 소비해 좌표 재투영 별도 수행 | ✓ |

**User's choice:** 둘 다 산출.
**Notes:** belle — "당연히 3번인데 변환 방향 짚고 넘어가". 추가 시나리오 설명 요청 → 시나리오 박제 + Q2 confirm.

### Q2 — 좌표 변환 방향 confirm (시나리오 박제 후)

| Option | Description | Selected |
|--------|-------------|----------|
| 방향 B (프로 → 수강생 체형) | Phase 12 오버레이 = "내 키로 환산된 정은지 자세". belle intent 정합. | ✓ |
| 방향 A (수강생 → 프로 체형) | 오버레이 = "프로 체형으로 환산된 자기 자세". 자기 영상에서 직관 떨어짐. | |
| 둘 다 메타 출력 (Phase 12 에서 선택) | 유연성 ↑ 자원/스코프 ↑. | |

**User's choice:** 방향 B 확정.
**Notes:** belle 가 시나리오 (160cm 정은지 vs 140cm 지영) 박제 본 다음 확정. 함수 이름 (normalizeStudentPoseToProReference) 과 변환 방향이 같지 않음 — 박제.

### Q3 — 세그먼트별 정규화 적용 단위

| Option | Description | Selected |
|--------|-------------|----------|
| 상체/하체 분리 (armScale + legScale + torsoScale, 폭 제외) | MVP 단순 + 좌우 비대칭 박제 정합. | |
| 5 필드 모두 + 하이브리드 게이트 | shoulderHipRatio 는 reproject 만 (점수 차원 미적용). confidence 낮으면 폭 보정 자동 OFF. | ✓ |
| 단순 estimatedHeightScale 하나만 | success #2 "단순 확대/축소 아님" 박제 모순. | |

**User's choice:** 5 필드 모두 + 하이브리드 게이트.
**Notes:** belle — "2번이 좋아보이는데 1번을 추천하는 이유는?" 박제. Claude 추천 사유 (MVP 단순 + 좌우 대칭 박제 + 측정 안정성 검증 부족) 박제 후 belle 가 정확도 우선으로 옵션 2 선택. 단 [[scoring-dimensions-ipsf]] 좌우 대칭 박제는 점수 차원 미적용 형태로 유지.

### Q4 — 체형 정규화 OFF 분기 조건

| Option | Description | Selected |
|--------|-------------|----------|
| mode + confidence 병행 게이트 | coaching + conf ≥ 0.5 → ON. judging or conf < 0.5 → OFF + warning. judging plumbing 은 v1 박제. | ✓ |
| confidence 게이트만 (mode 무관) | mode 분기 X — judging 모드 도입 시 Phase 6 재수정. | |
| Always ON (분기 X) | fallback 구현 제로. 단정 차단 박제 어김. | |

**User's choice:** mode + confidence 병행 게이트.
**Notes:** -

---

## Area (B) — mode1 / mode3 first / mode3 second+ 3 케이스 분기

### Q1 — mode3 first (수강생 첫 분석) 처리

| Option | Description | Selected |
|--------|-------------|----------|
| Page 9 절대 트랙 단독 | [[ipsf-5-track-scoring]] 정합. reference 없이도 IPSF Page 9 'all components' 절대 트랙으로 채점. | ✓ |
| 정은지 reference 자동 매칭 fallback | Gemini 인식 → reference 자동 호출. 사용자 명시 선택 X — mode3 의도 충돌 가능. | |
| BodyProfile 만 산출, 점수는 raw 절대값 | Page 9 트랙 미적용 — [[ipsf-5-track-scoring]] 박제 소온 가능. | |

**User's choice:** Page 9 절대 트랙 단독 (기본).
**Notes:** belle 새 메시지 — "지금 하이브리드로 가되 confidence 가 높아질 경우 분석할 수 있는 데로 분석하는 게 좋겠지?" → Universal principle (D-06-U1) 박제. mode3 first 도 confidence 높음 + motion 인식 성공 시 자동 매칭 reference fallback 활성화로 확장.

### Q2 — mode1 정은지 reference BodyProfile 박제 위치

| Option | Description | Selected |
|--------|-------------|----------|
| reference-motions 컬렉션에 BodyProfile 필드 추가 | Phase 14 등록 시 BodyProfile 동시 박제. Phase 6 시점 = 일회 백필 fixture. | ✓ |
| 분석 시점 실시간 측정 | 매 mode1 분석마다 reference video 다운로드 + measure 호출. 비용 ↑. | |
| 하드코드 fixture (JSON 박제) | 최소 의존. 영상 추가 시 갱신 누락 위험. | |

**User's choice:** reference-motions 컬렉션 + BodyProfile 필드 추가.
**Notes:** -

### Q3 — Phase 6 출력 schema (통합 vs 분기)

| Option | Description | Selected |
|--------|-------------|----------|
| 통합 schema + comparisonType field | 같은 BodyComparisonReport. comparisonType 으로 분기. Phase 12.5 dimensionExplanation 패턴 정합. | ✓ |
| 케이스별 dataclass 3개 분기 | 타입 안전 ↑ downstream 분기 처리 복잡. contract 조작 3x. | |
| 모든 필드 nullable 확장 schema | comparisonType field 없이 필드 존재 여부로 추정. type-narrowing 어려움. | |

**User's choice:** 통합 schema + comparisonType field.
**Notes:** -

---

## Claude's Discretion

- 점수 보정 산식 magnitude (researcher detail) — [[scoring-dimensions-ipsf]] + [[analysis-objectivity-no-human-scores]] 박제 유지
- 세그먼트별 정규화 알고리즘 (`normalizeByBodySegments`) 수학적 정의 — researcher
- `shoulderHipRatio` confidence 임계값 정확한 수치 — researcher (belle Pod sweep 데이터)
- `bodyNormalizationConfidence` UI 노출 방식 — Phase 12 / 12.5 와 협업 영역

---

## Deferred Ideas

- (C) 점수 보정 magnitude detail — researcher 가 영상 데이터 분석 후 결정
- (D) bodyNormalizationConfidence UI 노출 — Phase 12 / 12.5 결정
- judging 모드 정규화 OFF 실제 구현 — v1.5
- 다각도 입력 통합 — Phase 4 dep
- `shoulderHipRatio` 측정 안정성 검증 — researcher 가 sweep 재실행
- **ROADMAP / PROJECT.md / STATE.md 박제 갱신** — `.planning/ROADMAP.md:407-415` 의 "Phase 2~11 보류 (파일럿 후 v1.5)" reasoning 이 belle 2026-06-08 결정과 모순. 본 phase commit 후 별도 작업으로 처리.
