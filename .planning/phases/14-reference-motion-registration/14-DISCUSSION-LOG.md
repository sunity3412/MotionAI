# Phase 14: 정은지 기준 모션 등록 (다각도 캡처 가이드) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 14-reference-motion-registration
**Areas discussed:** 데이터 소스 / RunPod 여부, 다각도 가이드 vs 단일시점 pivot, 등록 주체 / 경로, 대상 동작 세트

---

## 데이터 소스 — reference 엔진 출력 채우기

| Option | Description | Selected |
|--------|-------------|----------|
| 저장된 joints3d 재사용 + 동일 _process 함수 | phase4_v1 3D pose 재사용, Phase 6/9/EXTEND 만 학생과 동일 함수로 계산 (분기 0). 빠름, pose 이미 학생과 동일 RTMW | ✓ |
| 영상부터 전체 _process 재실행 | RTMW 재추론 포함 전체 다시. 가장 보수적이나 오늘 재처리 중복 + 재검증 부담 | |

**User's choice:** Option 1 + research 게이트 하이브리드
**Notes:** belle 이 "옵션2가 재검증이라 더 정확하지 않냐"고 물음 → 정정: 같은 RTMW +
같은 영상 = 같은 pose 라 독립 재검증이 아니며 정확도가 더 높아지지 않음. 옵션2의 유일한
실익 = "저장 데이터가 downstream 입력에 부족할 때". 그 구멍은 research 게이트(입력 충족
검증 → 부족분만 재추론)로 메움. belle: "너가 추천하는대로 리서치 게이트 하이브리드."

---

## 다각도 가이드 vs 단일시점 pivot

| Option | Description | Selected |
|--------|-------------|----------|
| 단일시점 통일 + 다각도는 촬영 가이드 문서만 | reference 도 단일시점 기준 통일, graceful single-view. Phase 4 pivot 정합 | ✓ |
| reference 는 실제 다각도 촬영 | reference 만 다각도로 품질↑ (학생은 단일). 비대칭 + Phase 4 pivot 충돌 | |

**User's choice:** 단일시점 통일 + 다각도는 촬영 가이드 문서만
**Notes:** Phase 4 의 단일시점+AI 합성 pivot 과 정합.

---

## 등록 주체 / 경로

| Option | Description | Selected |
|--------|-------------|----------|
| admin CLI 스크립트 (기존 seed/extract 확장) | 운영자(belle) CLI 등록. Phase 6 패턴 확장. MVP 충분 | ✓ |
| 앱 내 등록 화면 | 앱에서 영상 올려 등록. MVP 범위 초과 | |

**User's choice:** admin CLI 스크립트 (1번)
**Notes:** belle: "나중엔 선수와 학원에서 업로드 가능하게 + 동작 신청도 가능해야 함. MVP
범위 아니고 일단 기술 실증 후 생각할 일." → 셀프 업로드/동작 신청은 deferred.

---

## 대상 동작 세트

| Option | Description | Selected |
|--------|-------------|----------|
| 기존 11개 reference 백필 (신규 촬영 0) | phase4_v1 11개에 force/EXTEND 채워 완결. Mode 1 v1 = 11개 | ✓ |
| 초기 3~5개 동작군만 선별 백필 | scope 제약에 맞춰 핵심만 | |
| 신규 정은지 영상 촬영부터 | 새 세션 촬영 → 등록. 촬영 의존 + 시간 | |

**User's choice:** 기존 11개 reference에 백필 (신규 촬영 0)
**Notes:** 오늘 11개 전부 phase4_v1 재처리 완료 상태를 그대로 활용.

## Claude's Discretion

- 백필 스크립트 entrypoint 구조 / 버전 쓰기 전략 / atomic write·rollback 메커니즘 —
  단 D-01(동일 함수 재사용) + Firestore flat-array 규약 준수.

## Deferred Ideas

- 선수·학원 셀프 업로드 + 동작 신청 플로우 (기술 실증 후 후속 phase)
- 실제 다각도 촬영 기반 reference (단일/AI 합성 path 한계 시 최후 수단)
- 신규 정은지 영상 촬영 등록 (Phase 14 는 기존 11개 백필로 한정)
