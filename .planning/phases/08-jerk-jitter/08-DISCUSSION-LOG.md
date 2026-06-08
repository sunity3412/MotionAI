# Phase 8: 중심축 이탈 + 접촉점 안정성 + jerk/jitter - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 08-jerk-jitter
**Areas discussed:** A. 동작 구간 분할, B. ContactStability 추정, C. 흔들림 산식, D. 거리/임계값 기준

---

## A. 동작 구간 분할 — 'hold' 단일 vs 다단계

| Option | Description | Selected |
|--------|-------------|----------|
| 2단계 분할 (setup_transition/hold) | `_select_window` 재사용. 추가 인프라 0, mode3 first 작동, 잡는 순간 vs 버티는 순간 구분 가능 | |
| **5단계 (entry/lock/transition/final_shape/hold)** | research 원본 표준. Plan 01-13 Gemini key_moments 의존 (선택지 (a)) 또는 휴리스틱 (선택지 (c)) | ✓ |
| DTW base/extension (segments.py) | 기존 코드 재사용. reference 있는 동작에만 작동 — mode3 first blocking | |

**User's choice:** 5단계
**Notes:** belle 가 분석 정확도 우선 정신으로 5단계 채택. Phase 7 'hold' 단일이 실수 같다는 직관 표명 — Phase 8 force-pattern 추론 입력 신호에는 단일 hold 가 부족함 (잡는 순간 골반 흘러내림 vs 버틸 때만 흘러내림 구분 불가) 라는 점에 동의.

---

## A2. 5단계 분할 산출 방식

| Option | Description | Selected |
|--------|-------------|----------|
| (1) 휴리스틱 단독 | infra 의존 0, deterministic, motion-id 별 룰 박제 부담 | |
| (2) Gemini 재시도 단독 | Plan 01-13 blocker 가 Phase 8 use case 에 직접 적용 안 될 수도 있음. timestamp non-determinism 위험 잔존 | |
| **(3) 하이브리드 (motion-agnostic baseline + Gemini fallback)** | Layer 1 휴리스틱 + Layer 2 Gemini. 한 쪽 fail 해도 다른 쪽 살아있음. 모든 동작 cover. 새 동작 추가 박제 부담 0 | ✓ |
| 2단계로 되돌아가기 | scope 최소화 | |

**User's choice:** (3) 하이브리드
**Notes:** belle 의 "새 동작이든 뭐든 안 되는 게 있으면 안 됨" 정신 정합. motion-agnostic Layer 1 (발 vertical + 폴축 거리 + keypoint 변화율) baseline 이 모든 영상에 deterministic 작동 + Phase 5 motion_id 인식 시 Layer 2 Gemini 자동 보강. 새 동작군 추가 시 박제 변경 X (Gemini 자동 인식, Layer 1 항상 작동). Claude 가 처음 "범위 밖은 미지원" 으로 해석한 것을 belle 가 정정 — "분석이 죽지 않고 graceful degrade" 가 정답이라는 점 박제.

belle 의 추가 질문 1: "재시도 위험이 정확히 뭐냐? 오류가 난다는건가?" → 풀이: 크래시 X, "답을 신뢰할 수 없음" 이 진짜 위험. Plan 01-13 blocker 는 IPSF criteria 갭 chain 의심이지 key_moment 자체 의심은 아님 — Phase 8 use case 에는 직접 적용 안 될 수 있음.

belle 의 추가 질문 2: "레퍼런스 말고도 앞으로 새 영상 (수강생/프로) 업로드에도 다 작동해?" → 풀이: 모든 새 업로드가 동일 `pipeline/app.py::_process` 통과. Phase 8 metric 자동 산출. 정은지 새 reference 등록도 동일. 1회용 박제 X, universal pipeline 통합. `[[mvp-simple-pilot-quality]]` 정합.

---

## B. ContactStability 접촉 인식 깊이

| Option | Description | Selected |
|--------|-------------|----------|
| (1) Proximity 만 | motion_id 별 expected_contact_points + 폴축 거리 임계. deterministic | |
| (2) Proximity + Gemini 보강 | Gemini 가 화면상 거리 본 거라 cross-validation 약함. 비용/non-determinism 추가 | |
| **(3) Proximity + 시간 패턴 (수정 추천)** | 공간 (거리) + 시간 (5단계 내 적절 구간) 명확한 independent 신호. lostContactAtMs 의 phase 속성 검증. 추가 박제 부담 0 (5단계 분할 일반 룰 활용) | ✓ |
| ContactStability v1.5 로 미루기 | Phase 9 force pattern 추론 입력 1개 누락 | |

**User's choice:** (3) Proximity + 시간 패턴
**Notes:** belle 의 "보강이 왜 안 좋아? 몰라서 물어봄" 질문에 Claude 가 처음 (1) 추천한 이유 + 그 추천이 부정확했음 정정. 핵심 = "신호의 독립성" — (2) Gemini 는 같은 화면 정보의 다른 시각이라 진짜 보강 X. (3) 시간 패턴은 공간 + 시간 다른 차원이라 진짜 보강. 5단계 분할이 이미 박제되므로 motion-id 별 expected_timing yaml 박제 불필요 (일반 룰 "lock 이후 release 전 stable" 활용). belle 정신 "분석 정확도 우선" 정합.

---

## C. 흔들림 산식 정책

| Option | Description | Selected |
|--------|-------------|----------|
| **기존 helpers 재사용 + jerk 만 신설 + 새 파일 따로** | `stability_score` / `stability_wobble_by_joint` 재사용. force_signals.py 신규 (진단). 점수 vs 진단 분리 명확 | ✓ |
| 전신 신설 force_signals.py 별도 | 도구 복제, 코드 중복 | |
| 한 파일에 다 넣기 | 점수 + 진단 혼재 위험 | |

**User's choice:** 기존 helpers 재사용 + jerk 만 신설 + 새 파일 따로
**Notes:** belle 가 "무슨 말인지 잘 모르겠어" 한 1차에 부엌 비유로 풀이 (음식 맛 점수 vs 음식 성분 분석 — 같은 칼/저울 도구 쓰되 출력 다름) 후 확정. `[[mvp-simple-pilot-quality]]` "코드 재사용 + 명확한 경계" 정합.

---

## D. 거리/임계값 기준

| Option | Description | Selected |
|--------|-------------|----------|
| **도메인 룰 fixed 임계 (수정 추천)** | body-scale 정규화 + IPSF 각도 tolerance + research 02 도메인 정의. 영상/선수/동작 추가 무관 일관성 영구. reference sweep = sanity check 만 | ✓ |
| 정은지 5영상 분포 baseline | 영상 추가 시 임계 변동 → 과거 분석 비교 불가능 / 박제 고정 시 신규 데이터 반영 X. 확장 깨짐 | |
| per-motion 분포 (동작별) | 새 동작 = 새 reference 필요. blocker | |

**User's choice:** 도메인 룰 fixed 임계
**Notes:** belle 의 "근데 정은지 영상은 더 늘어날 수도 있고, 다른 선수들도 올릴 수 있는데 맞는 방안인가?" 직관이 정확. Claude 가 처음 정은지 분포 baseline 으로 추천한 것 정정. 도메인 룰 fixed 임계 = `[[scoring-dimensions-ipsf]]` "IPSF 절대 기준" + `[[analysis-objectivity-no-human-scores]]` "사람 점수 라벨링 X" 정합. 정은지 영상 추가/교체, 다른 선수 등록, 새 동작군 추가 모두 임계 변동 X.

---

## Claude's Discretion

- `force_signals.py` 모듈의 정확한 함수 시그니처 (researcher / planner)
- 5단계 분할 휴리스틱의 정확한 룰 (발 vertical / 폴 거리 / keypoint 변화율 cutoff) — researcher 박제
- jerk 산식의 정확한 정의 (3차 미분 vs 가속도 RMS) — researcher 박제
- expected_contact_points yaml 의 motion_id 별 박제 내용 (인버트/후굴/숄더마운트/기본 포징) — researcher + belle 검증
- Layer 2 Gemini 호출 비용 / latency / cache / retry 박제 — planner
- 5단계 분할 windowing (각 phase 별 frame range) — researcher
- AnalysisDoc Firestore 저장 키 (`forceSignals` 박스 / 평탄화) — planner

## Deferred Ideas

- v1.5+ Plan 01-13 Gemini key_moments 본격화 (Phase 8 Layer 2 spike 검증 후 별도 plan)
- motion-id 별 미세 튜닝 (v2 — Layer 1 baseline 정확도 부족 시)
- EMG 기반 근육 힘 방향 단정 (v2 — research 02 §0)
- 카메라 앵글 합성 / 다각도 시점 (v2 — Phase 4 v2)
- forceSignalsByPhase aggregate (v2)
- per-motion expected_timing yaml (v2)
- release phase 자연 확장 (v1.5)
- 임계 sweep dashboard (belle 운영 작업)
