# Phase 28: 동작 기반 비교 정렬 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 28-dtw-motion-based-alignment
**Areas discussed:** 재생 워핑 방식, 정렬 실패 폴백, fault_zoom 시간비례 근사 처리, 기존 분석 소급

---

## 재생 워핑 방식

| Option | Description | Selected |
|--------|-------------|----------|
| 트림+구간별 가변속도 (Recommended) | 전역 트림 + DTW 경로를 구간별 playbackRate로(0.5~2배 클램프) — 중반 템포 차이까지 | ✓ |
| 트림+오프셋만 (v1 최소) | 단순하지만 템포 다르면 중반 재이탈 | |
| 키 모멘트 앵커 점프 | seek 동기화 — 끊김 | |

**User's choice:** 트림+구간별 가변속도

---

## 정렬 실패 폴백

**belle 사전 질문:** "너무 다르면 기준 동작과 다르다고 뜨면 되긴 하는데.. 그거 말고 경우의 수가 없으려나?" → 경우의 수 5가지 정리 제시: (1) 다른 동작 (2) 구간 부분 붕괴 (3) 키포인트 품질 저하 (4) 길이 극단 차이 (5) 반복 동작 모호성.

| Option | Description | Selected |
|--------|-------------|----------|
| 단계형 사다리 (Recommended) | 높음=워핑 / 부분 붕괴·극단=트림만 / 낮음=안내+절대시계 | ✓ |
| 이분법 | 정렬 or 안내 — 부분 붕괴에서 이상 워핑 노출 위험 | |
| 항상 워핑 | 클램프만 — 오도 리스크 | |

**User's choice:** 단계형 사다리

---

## fault_zoom 시간비례 근사 처리 (D2 재발 방지)

| Option | Description | Selected |
|--------|-------------|----------|
| 근사 제거 + 전신 폴백 (Recommended) | 실패 시 정은지 쪽 전신 + "자동 대응 실패" 캡션 — 오도 0, 260702-sic 선례 일관 | ✓ |
| 카드 숨김 | 학생 쪽 정보까지 사라짐 | |
| 근사 유지 + 배지 | D2 재발 여지 | |

**User's choice:** 근사 제거 + 전신 폴백

---

## 기존 분석 소급

| Option | Description | Selected |
|--------|-------------|----------|
| 새 분석부터 + legacy 현행 (Recommended) | 저비용, optional 필드 관례 | |
| 재분석 유도 배너 | legacy 결과 화면에 자동 정렬 안내 — 재분석은 사용자 선택 | ✓ |

**User's choice:** 재분석 유도 배너 (비권장안 선택 — belle 판단: 파일럿에서 정렬 개선 체감을 기존 사용자에게도 노출)

---

## Claude's Discretion

- 신뢰도 지표/임계 (calibration-source-hard-gate 준수, 고정 밴드 금지), 워핑 스무딩 세부, 정렬 계약 필드 설계(Phase 22 시간 앵커 상위 호환), 배너 문구/위치

## Deferred Ideas

- 키 모멘트 점프 (하이라이트 기능으로 후속 검토)
- 반복 동작 자동 분절
- D4 가로 비율 (별개 실기기 튜닝)
