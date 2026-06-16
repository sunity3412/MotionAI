# Phase 15: Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 15-mode-1-mode-3-testflight
**Areas discussed:** 위양성 게이트 증명, 실영상 검증 데이터셋, TestFlight 전달 경로, 듀얼 LLM 실 E2E 검증

---

## 위양성 게이트 증명

| Option | Description | Selected |
|--------|-------------|----------|
| 실 E2E 재측정 + 기존 기준선 대조 | 정은지 영상 실 Pod E2E 재측정 → 기존 확정 임계값(08.1 SWEEP-EVIDENCE + IPSF baseline)에 대조, 재calibrate 금지 | ✓ |
| 기존 evidence 재사용만 | 08.1 정은지 5/5 low PASS evidence + mock E2E로만 선언 (실 LLM/듀얼 coach 최신 path 재검증 안 됨) | |

**User's choice:** 실 E2E 재측정 + 기존 기준선 대조 (추천)
**Notes:** calibration-source-hard-gate 준수 — 신규 sweep으로 threshold 재조정하는 circular tuning 금지. 신규 실행은 "현 기준선 위에서 통과하는가" 확인 용도.

---

## 실영상 검증 데이터셋

| Option | Description | Selected |
|--------|-------------|----------|
| 정은지 5 + belle 본인 2영상 페어 | Mode1=정은지 reference + belle 따라한 영상, Mode3=belle 2영상 시간차 페어 | |
| 위 + 다양한 앵글/동작 추가 | SC4 크래시 테스트용 측면·사선·범위 밖 동작 belle 추가 제공 | |
| 정은지 5만 (belle 촬영 최소화) | Mode3도 정은지 reference 둘로 대용 | |
| (자유 응답) 정은지 성공+실패 페어 활용 | belle 제안: 정은지 성공영상 + 실패영상(같은 동작)으로 Mode3 동시 가능 | ✓ |

**User's choice:** (자유 응답) "왜 정은지 5야? 11 아닌가. 일부러 비교하라고 실패한 영상도 있는데 정은지 성공영상 + 실패영상(같은 동작)을 활용하면 Mode3도 함께 할 수 있는 거 아니냐"
**Notes:** belle 통찰 채택. reference는 11개(5 아님 — "5"는 위양성 calibration 영상 수). 정은지 성공/실패 페어 = 동일 인물·동일 동작 → Mode3 델타 + 위양성 게이트 한 셋으로 동시 충족. 영상 위치 `~/Downloads/정은지 선수 추가 영상/`, 6 성공/실패 페어 = 나중에 추가된 6개 reference. 분석결과 md는 정성 참고만(점수 라벨 금지).

---

## TestFlight 전달 경로

| Option | Description | Selected |
|--------|-------------|----------|
| SIGABRT fix → TestFlight preview 빌드 | letterSpacing SIGABRT(release native crash) 먼저 닫고 EAS preview 빌드+submit까지 내가 검증 → belle 실기기 게스트 완주만 핸드오프 | ✓ |
| Expo Go/dev 빌드 먼저 | belle dev client로 흐름 완주 먼저, 그 다음 TestFlight (단 release-only crash는 여기서 못 잡을 수 있음) | |

**User's choice:** SIGABRT fix → TestFlight preview 빌드 (추천)
**Notes:** —

---

## 듀얼 LLM 실 E2E 검증

| Option | Description | Selected |
|--------|-------------|----------|
| Gemini primary 유지 + cross-fill PASS | primary=Gemini(원인)+Cerebras(처방), 한쪽 drop도 cross-fill로 빈 섹션 0이면 PASS | ✓ |
| 둘 다 필수 (drop 시 FAIL) | Gemini·Cerebras 둘 다 정상 호출되어 고유 섹션 채워져야만 PASS, cross-fill 의존은 불합격 | |

**User's choice:** Gemini primary 유지 + cross-fill PASS (추천)
**Notes:** 13-B에서 belle가 고른 primary=Gemini 유지. graceful degrade 허용하되 실 LLM 호출 자체가 작동함은 확인 필요.

## Claude's Discretion

- Pod 작업(SSH/sweep/Lambda env 동기화/E2E 실행) 전부 내가 실행 (pod-ops-claude-runs).
- 검증 스크립트 구조, sweep 실행 방식, S3 업로드 경로, assert 구현, 영상 파일명 정규화는 내 판단.

## Deferred Ideas

- 영구 라벨 regression fixture + fault 자동 assert 하니스 = Phase 18.
- belle 다양한 앵글/동작 크래시 테스트 영상 대량 소싱 = 실증 단계.
- combo.mp4 (성공만, 페어 없음) = Mode 1 단독 분석에만.
