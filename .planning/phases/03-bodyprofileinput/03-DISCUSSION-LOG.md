# Phase 3: 자가입력 BodyProfileInput - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 3-bodyprofileinput
**Areas discussed:** 입력 진입점/시점, 필드 입력 방식, 분석 활용, 미입력 처리

---

## 입력 진입점 / 시점

| Option | Description | Selected |
|--------|-------------|----------|
| 마이페이지 + 첫분석 권유 | 마이페이지 상시 편집 + 첫 분석 직전 1회 가벼운 권유(건너뛰기 가능) | ✓ |
| 마이페이지에만 | 분석 플로우 안 건드림 | |
| 첫 분석 직전에만 | 첫 업로드 전 1회 안내 | |

**User's choice:** 마이페이지 + 첫분석 권유 (추천)
**Notes:** belle 원 고민 = "지금 받나 vs 회원가입 후 큐레이션 때 받나". 파일럿 게스트 우선(회원가입 강제 없음, CLAUDE.md §2)이라 회원가입 게이트는 충돌 → "지금·선택 입력"으로 확정. 큐레이션 온보딩은 정식 출시 후속(deferred).

---

## 필드 입력 방식

| Option | Description | Selected |
|--------|-------------|----------|
| 빠른 선택형 | 경력=초/중/고급, 통증부위=신체부위 칩 다중선택, 우세손=좌/우/양, 키·몸무게=숫자 | ✓ |
| 정밀형 | 경력=연차 숫자, 통증=부위+자유텍스트 메모 | |
| 최소형 | 키·몸무게+우세손만, 경력·통증은 나중 | |

**User's choice:** 빠른 선택형 (추천)
**Notes:** 입력 부담 최소 — 탭 몇 번으로 끝. 통증부위 칩 목록은 plan/research 에서 폴스포츠 도메인 참조로 확정.

---

## 분석 활용

| Option | Description | Selected |
|--------|-------------|----------|
| 저장+표기 + LLM 컨텍스트 훅 | 결과화면 표기 + coach_writer 컨텍스트 주입 훅(실 활성은 Phase 13) | ✓ |
| 저장+결과화면 표기만 | LLM 연동은 Phase 13 때 전부 | |
| 저장만 | 데이터 수집 우선, 분석 미연동 | |

**User's choice:** 저장+표기 + LLM 컨텍스트 훅 (추천)
**Notes:** 키·몸무게는 SC#3 상 보조만. 통증부위·경력은 coach 컨텍스트로(점수 직접 가중 X). 실 LLM 소비/검증은 Phase 13.

---

## 미입력 처리

| Option | Description | Selected |
|--------|-------------|----------|
| 건너뛰기+부분입력 허용 | 명확한 건너뛰기 + 일부만 적어도 OK + 재권유 안 함 | ✓ |
| 건너뛰기 + 가끔 재권유 | 미입력이면 가끔 다시 권유 | |
| 전부 or skip | 부분입력 막음 | |

**User's choice:** 건너뛰기+부분입력 허용 (추천)
**Notes:** 미입력도 분석 graceful (SC#4). 마이페이지에서 언제든 입력/수정.

---

## Claude's Discretion

- 통증부위 칩 정확한 부위 목록 (폴스포츠 도메인).
- BodyProfile Firestore 저장 위치 + 분석 요청 전달 메커니즘 (3-way contract lockstep 준수).
- 결과화면 BodyProfile 표기 위치/형식 (design.md + Figma 우선).

## Deferred Ideas

- 회원가입 후 큐레이션 온보딩 (정식 출시 후속).
- 유연성·근력 자가입력 (ROADMAP 제외 — 부정확).
- 통증부위 → 부상위험 신호 연동 (Phase 10 SAFE-01).
- 실 LLM 코칭에서 BodyProfile 소비 (Phase 13).
