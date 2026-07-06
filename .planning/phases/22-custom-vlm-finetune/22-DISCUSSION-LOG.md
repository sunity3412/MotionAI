# Phase 22: 자체 비전 모델 파인튜닝 (오픈 모델 전환) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 22-자체 비전 모델 파인튜닝 (오픈 모델 전환)
**Areas discussed:** v1 태스크 범위, 백본 선정·스케일, 학습셋·라벨링, 전환·서빙 전략

---

## 사전 입력 (discuss 전)

- belle 지시로 NotebookLM "LLM, Finetunig Guide"(97 소스 + belle 노트 25개, 2026 최신)를 정독 — Phase 22 근거 자료로 확정 ("내 리서치는 24년 자료를 제시" 지적).
- belle 라이선스 확정: InternVL 3.5 ≤38B 상용 무제한(코드 MIT+백본 Apache 2.0), Qwen 3.6·MMPose Apache 2.0 — "같이 써도 됨". 비상업 리스크는 InternVL-U(생성 파생모델) 단 하나.
- belle: Phase 21보다 22 먼저 진행.
- belle: kip-up 중심 사고 탈피 — 검증뿐 아니라 설계 프레임에도 전 동작 균등 (메모리 확장 반영).
- belle 비전: "스포츠 분석 앱 업계의 힉스필드" (외부 API/오픈모델 파인튜닝으로 자체 플랫폼 성장).

## v1 태스크 범위

| Option | Description | Selected |
|--------|-------------|----------|
| 좌표 보정 + 결함 짚기 | belle 노트 아키텍처, 코칭은 Cerebras 유지 (초기 권고) | |
| 결함 짚기/인식만 | 기존 인터페이스 drop-in, 좌표 붕괴 미해결 | |
| 코칭 생성까지 포함 | 풀 자체 모델 | ✓ (확장 형태로) |

**User's choice:** "3번으로 하고 싶은데 많이 어렵나?" → 난이도 분해 제시(코칭 증류 데이터·주관 eval이 추가 비용) → 3번 학습 + 단계적 소비 절충.
**Notes:** belle이 "너무 단순한 출력 아닌가" 푸시백하며 고급 출력 8종 목록(SVG 렌더링·이미지 편집·분할 마스크·temporal grounding·동작 순서·카운팅·행동 토큰·구조화 리포트) 제시. 재평가 결과 v1 = 통합 구조화 리포트(보정 좌표+짚기+시간 앵커/구간 분할+SVG 시각 스펙+코칭). temporal grounding은 fault_zoom·D2 정렬이 정확히 필요로 하던 것. 실루엣·마스크·카운팅=v2, 하드웨어·에이전트 토큰=백로그.

"v2 왜 분리? 지금 MVP에도 쓰고 싶다" 질문 2회 → 직답: **페어 데이터 0장이라 순서가 강제됨.** 기능 자체는 (1) 기하 오버레이=지금 데이터로 즉시, (2) 외부 생성 API=지금 MVP에 프로토타입 가능(힉스필드 방식) + 그 산출물이 v2 학습 페어가 됨. → 교정 시각물 별도 phase로 deferred.

중간에 belle 질책("자꾸 질문만 하고 답변은 안 한다") → 이후 기술 결정은 Claude가 확정 8건(D-01~16 원형)으로 제시하는 방식으로 전환.

## 백본 선정·스케일

**Claude 확정(belle 위임):** Qwen 3.6 vs InternVL 3.5 8B급 bake-off 실측 선정 / 8B 시작·27B 조건부 승급 / ms-swift 주 프레임워크 / SFT 먼저·Cascade RL 후속.

## 학습셋·라벨링

**User's input:** "유튜브 좀 긁어오기로 했었지?" → 확인: 로드맵 원안(대회=정타, 튜토리얼 흔한 실수=fault) 유지 + provenance 로그 + 학습 전용.
**Claude 확정:** 시드=보유 자산(정은지 페어·실사용 371건·실증 케이스·EVAL18 라벨), 좌표 라벨=합성 교란 자가생성, 짚기/코칭=Gemini 교사 증류+judge 필터, shadow 로깅 즉시 시작, JSON 규격 철칙+T3 혼합.

## 고객 데이터 플라이휠 (동의)

**User's input:** "업로드 재학습 동의를 꼭 받아야 하나... 대부분 안 해주던데"
**Claude 권고(채택):** 개별 옵트인 강제 없음 — (1) 파일럿=학원 참가 동의서 포괄, (2) 정식=처리방침 고지+가명처리(얼굴 블러) 후 활용, (3) 출시 전 법률 검토 1회. 고지 문구는 온보딩 phase.

## 전환·서빙 전략

**Claude 확정(belle 위임):** shadow 병행 기본, swap 순서 veto→recognizer→coach, 기존 Pod에 vLLM(AWQ), 출하 게이트=Phase 24 4종+EVAL18+전 동작 균등+shadow 우위 증명. Wave 0~4 실행 구조.

## Claude's Discretion

bake-off 하네스, 샘플링/압축 파라미터, 하이퍼파라미터, vLLM 구성, 수집 파이프라인 세부.

## Deferred Ideas

- 교정 시각물 phase (기하 오버레이 + 외부 생성 API 실루엣, Gemini MVP 트랙 병렬) — 로드맵 등재 필요
- v2: 자체 생성 헤드·분할 마스크·반복 카운팅
- 백로그: 하드웨어 행동 토큰, 에이전틱 툴콜, mmWave, 타 종목 확장
