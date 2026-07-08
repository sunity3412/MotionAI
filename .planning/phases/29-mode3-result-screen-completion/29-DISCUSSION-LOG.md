# Phase 29: 결과·비교 화면 완성 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 29-mode3-result-screen-completion
**Areas discussed:** Mode3 점수 내역의 감점 소스, Mode3 비교영상·확대비교 형태, 가로 방향 + EAS 빌드 전략, 부상 대응법 노출 형태

---

## Mode3 점수 내역의 감점 소스

| Option | Description | Selected |
|--------|-------------|----------|
| ipsf_absolute 측정 전용 | 등록 동작은 객관 IPSF 기준으로 tally, Gemini 없이 RTMW 측정값만 | ✓ |
| vision veto Mode3 확장 | belle 보류 해제, Gemini 단일 영상 절대 판정 | |
| 현행 점수 내역화만 | 채점 무접촉, 절대차원 구성만 풀어 표시 | |

**User's choice:** ipsf_absolute 측정 전용
**Notes:** belle이 "Gemini가 빠진다"는 점을 두 차례 재질문 — (1) Gemini 포함/미포함의 명확한 차이, (2) 별 변함이 없어서 안 쓰는 건지. 최종 정리: Mode3엔 Gemini가 원래 없었고(mode1은 그대로 사용), 안 넣는 핵심 이유 = **기준 영상 없는 진공 판정의 과단정 위험(veto는 reference-anchor 비교일 때만 유효하다는 기존 검증)** + 속도/비용 + 측정 없는 감점은 투명 원칙 위반. belle: "1번(과단정)이 좀 심각하구만... 오케이 진행". 기각 아닌 보류 — Phase 22 자체 VLM 시 재검토.

### 하위 결정

| 질문 | 선택 | 대안 |
|---|---|---|
| 점수 자체 변경? | overall = tally 전환 (정은지 페어셋 mode3 sweep 게이트 조건) | 표시 전용 / 2단계 |
| 미등록 동작? | 현행 유지 + "코치님 영상·이전 영상 비교" 행동 유도 안내 (belle: 친절 메시지가 짜여져야 함) | generic 기준 파생 / 등록 확대 선행 |
| legacy doc? | 재분석 유도 배너 (Phase 28 D-05 패턴) | 배너 없이 조용히 |
| 한계 고지 문구? | 측정 범위 안내형 + belle 제안 전진형 유도("새 영상 올리면 발전 분석 본격 시작") 결합. **"각도" 단어 금지** (belle: 기존 화면 "각도" 남발 지적, 사용자 이해 불가 + angle 차원 용어 충돌) | 기준 출처형 / 둘 다 2줄 |

## Mode3 비교영상·확대비교 형태

| 질문 | 선택 | 대안 |
|---|---|---|
| 첫 분석(이전 영상 없음)? | 숨김 + 안내 1줄 | 정은지 폴백 / 본인 영상 단독+마커 |
| 줌 카드 내용? | 결함 부위만 (이전 vs 이번 프레임 페어) | 결함+개선 / 영상만 |
| D1 Mode1 비교영상 회귀? | 진단 태스크로 플랜 포함 | UAT 항목으로만 |
| Phase 28 워핑 적용? | 동일 적용 (앱 소비만 확장) | 절대시계 동기화만 |

## 가로 방향 + EAS 빌드 전략

| 질문 | 선택 | 대안 |
|---|---|---|
| 가로 적용 범위? | 전체화면 비교 뷰어만 | 결과 화면 전체 / 회전 감지 자동 |
| 구빌드 호환? | 90도 핵 폴백 유지 (런타임 모듈 감지 분기) | 핵 폐기 + runtimeVersion bump |
| 빌드 타이밍? | Phase 29 마감 시 (iOS TestFlight + Android APK, F1 동승) | batch UAT 직전 / 즉시 선행 |

## 부상 대응법 노출 형태

| 질문 | 선택 | 대안 |
|---|---|---|
| recommendation 노출? | 카드 내 바로 표시 + "강사님과 점검" 톤 캡션 | 탭하면 상세 시트 |

## Claude's Discretion

- 안내·고지·배너 카피 세부 (뼈대·금지어 준수, "~해요" 체)
- 배너 통합 여부, mode 게이트 확장 구현, 가로 전환 상태 처리, 계약 필드 설계 (3-way lockstep + flat 규칙)

## Deferred Ideas

- Mode3 개선 부위 축하 카드 (시나리오 +α)
- 90도 회전 핵 코드 제거 (파일럿 이후)
- vision veto Mode3 확장 (Phase 22 자체 VLM 시 재검토)
- 미등록 동작 criteria 등록 확대 (도메인 기준 수립 별도 트랙)

## 진행 방식 교훈 (belle 피드백)

선택지 안에서 belle이 질문하면 **답변 먼저 → 이해 확인 → 그 다음 선택**. 질문을 답변으로 처리하고 다음 선택지로 넘어가는 것 금지. belle 원문: "너가 대답을 해줘야 내가 선택을 하지".
