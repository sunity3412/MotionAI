# Phase 26: 온보딩·기대설정 + 원본 업로드 가이드 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 26-onboarding-upload-guide
**Areas discussed:** not_pole 게이트 완화 병행 여부, 온보딩 진입·여정 편입 방식, 카톡 압축본 감지 시 동작, 프라이버시·학습활용 고지 수위

---

## not_pole 게이트 완화 병행 여부

| Option | Description | Selected |
|--------|-------------|----------|
| 안내만, 게이트 불변 (Recommended) | 업로드 전 촬영 거리 안내 + 실패 화면 원인·재촬영 가이드. 앱만, 위양성 리스크 0. 완화는 파일럿 측정 후 별도 결정 | ✓ |
| 임계 완화 병행 | NOT_POLE_SIMILARITY_THRESHOLD 완화 포함. 오반려 즉시 감소하나 스코프 확장 + 위양성 리스크 + eval 필요 | |
| 구도 보정 별도 과제로 | 안내는 이번에, torso ratio 스케일 정규화는 채점 트랙 별도 phase 백로그 | |

**User's choice:** 안내만, 게이트 불변
**Notes:** 구도 보정(스케일 정규화)은 deferred로 함께 기록 (CONTEXT D-02).

---

## 온보딩 진입·여정 편입 방식

| Option | Description | Selected |
|--------|-------------|----------|
| 첫 실행 1회 + 스킵 가능 (Recommended) | 게스트 첫 진입 시 튜토리얼, 스킵 버튼, 이용방법/FAQ 재접근 | ✓ |
| 첫 실행 강제 완주 | 스킵 없이 끝까지. 기대설정 확실하나 현장 빠른 시작 막음 | |
| 첫 업로드 직전 노출 | 분석 시작 순간에만. 홈 첫인상 깔끔하나 캘리브레이션 늦음 | |

**User's choice:** 첫 실행 1회 + 스킵 가능

---

## 카톡 압축본 감지 시 동작

| Option | Description | Selected |
|--------|-------------|----------|
| 경고 + 진행 허용 (Recommended) | 화질 손상 경고 후 계속 선택 가능. 기존 저화질 분기(260704-fwb)와 연동 | ✓ |
| 하드 차단 | 압축본 업로드 불가. 원천 차단이나 원본 없는 수강생 막힘 | |
| 차단 + 예외 허용 | 기본 차단 + "그래도 분석" 2차 확인 | |

**User's choice:** 경고 + 진행 허용

---

## 프라이버시·학습활용 고지 수위

| Option | Description | Selected |
|--------|-------------|----------|
| 1줄 고지 + 학습활용 opt-in (Recommended) | 업로드 직전 보관·삭제 1줄 + AI 개선 활용 동의 별도 체크(기본 off). Phase 22 D-12 정합 | ✓ |
| 1줄 고지만 | 마찰 최소지만 학습 활용 동의 근거 없음 → 플라이휠 불가 | |
| 가입/시작 시 포괄 동의 | 이후 마찰 0이나 법적 근거 약함 + 신뢰 이슈 | |

**User's choice:** 1줄 고지 + 학습활용 opt-in

---

## Claude's Discretion

- UI 화면 순서 재배치: 실행 중 목업 선제시(AskUserQuestion preview) 후 확정 — belle 기존 지시 승계로 별도 질문 생략
- 이용방법/FAQ 위치·구성, 경고/고지 문구 카피, F3(기타 자유입력)·F4(공지 간격) 세부

## Deferred Ideas

- torso ratio 스케일 정규화(구도 보정) — 채점 트랙 별도 phase 백로그
- 게이트 임계 완화 — 파일럿 안내 효과 측정 후 재결정
- 셀프촬영 심화 가이드(삼각대 등) — 이번엔 촬영 거리 안내까지만
