# Phase 16 — Studio Terminology Foundation (3-branch + 5-Track v1 평행)

## Goal

학원 용어 3분기 시스템 (AKA 매핑 / 정은지 reference / 자동 수집) + IPSF 5트랙 채점 v1 scope (a + c + Page 9 절대 트랙) 의 **데이터/스펙/UX 카피를 박제**한다. 코드 통합은 후속 plan, 박제만 v1.

**왜 v1 평행 진행 가능한가**:
- Phase 1~15 의존성 없음 (데이터/스펙/카피 박제는 코드 진척과 독립적)
- Phase 5 (Gemini 기술 인식기) / Phase 14 (정은지 reference) 가 Phase 16 데이터를 소비하는 구조 (의존 역전: Phase 16 이 데이터/스펙 공급)
- belle 결정 2026-06-02: "MVP 가볍게 + 실증 시 확장 + 한 번에"

## Why now

학원 사용자 1차 진입 시 (파일럿 학원 수강생) 학원 용어 (폭스탑, 폭스탑 스플릿, 나비, 큐피드 등) 그대로 입력 가능해야 함. 처리 path 가 v1 에 없으면:
- 분기 1 AKA 매핑 없음 → IPSF 정밀 채점 못 함
- 분기 2 정은지 reference 비등재 동작 없음 → 폭스탑 같은 동작 채점 못 함
- 분기 3 자동 수집 없음 → 신규 키워드 누적 데이터 잃음 (KPSA 미작성 한국어 표준 작성 path 차단)
- 5트랙 v1 scope 미박제 → mode3 reference 없는 채점이 IPSF 룰상 합법인지 불명확

## Decision context

- belle 결정 (2026-06-02): 3분기 시스템 + UX 카피 직접 작성. 변경/요약/재가공 금지.
- 사람 점수 라벨링 영구 금지 ([[analysis-objectivity-no-human-scores]]) — 모든 데이터는 IPSF Code of Points 임계값 + 정은지 영상 측정값 기준만.
- IPSF 단일 기준 ([[judging-baseline-ipsf-code-of-points]]) — KPSA 도 IPSF 따름.

## Scope (MVP 가볍게)

### 포함 (v1 박제):
1. AKA 매핑 13개 데이터 파일 (NotebookLM lookup 2026-06-02 출처)
2. 분기 2 정은지 reference 비등재 동작 1~2개 (폭스탑 우선 — 운영자 설문 직접 예시 `폴스포츠 수강생의 설문조사.md` 운영자 5-2)
3. 분기 3 자동 수집 데이터 스키마 (저장 구조 정의만)
4. 분기 3 UX 카피 박제 위치 결정 (코드 통합은 후속 plan)
5. 5트랙 채점 v1 spec architectural decision 박제 (PROJECT.md Key Decisions + memory cross-reference)
6. 실증 검증 게이트 threshold belle 협의 후 박제

### 제외 (v1 박제 안 함):
- 분기 1/2/3 코드 통합 (Phase 5/14 진입 시 통합)
- 분기 3 자동 수집 실제 수집 로직 (스키마만 박제, 수집 wiring 은 후속 plan)
- 분기 1/2 AKA 매핑 확장 (실증 데이터로 확장 시점 결정)
- (b) Tech Bonus 연계 / (d) Artistic 정성 = v2 (SCORE-V2-02/03)

## External dependency

- NotebookLM (IPSF Code of Points 2024-2025 / 2025-2027 lookup, notebook `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3`)
- 정은지 영상 (이미 보유 가정)
- belle/강사 협업 **없이** 박제 가능 (사람 점수 라벨링 X)

## References

### NotebookLM lookup 결과 (2026-06-02)

| 출처 | 내용 |
|---|---|
| IPSF Pole Sports CoP 2021-2024 **Page 9** | "all components" 절대 감점 트랙 명시 |
| IPSF Pole Sports CoP 2025-2027 **Page 138-139** | Element Code Matching 룰 (동작 인식 필수) |
| IPSF Pole Sports CoP 2025-2027 **Page 18** | Compulsory 11점 (Senior Elite) |
| IPSF Pole Sports CoP 2025-2027 **Page 4** | 4트랙 동시 가동 |
| IPSF Pole Sports CoP 2025-2027 **Page 197** | 동작별 Criteria 표 |
| IPSF Mid-Cycle Update Appendix 2024 **Page 5** | Dynamic Combinations 가산 |
| IPSF Aerial Pole CoP 2024-2025 **Page 12** | Flow 평가 |
| IPSF Aerial Hoop CoP 2024-2025 **Page 15** | Passé 90° 굽힘 정답 명시 |

### 박제된 memory

- [[studio-term-3branch-system]] — 3분기 시스템 + UX 카피 (2026-06-02)
- [[ipsf-5-track-scoring]] — 5트랙 채점 + v1 scope (2026-06-02)
- [[judging-baseline-ipsf-code-of-points]] — IPSF 단일 기준
- [[scoring-dimensions-ipsf]] — IPSF 4차원 (angle/line/balance/stability)
- [[analysis-objectivity-no-human-scores]] — 사람 점수 라벨링 영구 금지
- [[mode3-progress-not-similarity]] — mode3 절대지표 발전 표시
- [[notebook-lm-pole-sports]] — NotebookLM 자동 lookup path
- [[terminology-multimap-future]] — v2+ 다국 alias 풀 (Phase 16 = MVP 진입로)
- [[research-pole-sports-techniques]] — 폴스포츠 비전 분석 기술

### 현장 설문 직접 매칭

- `docs/research/폴스포츠 수강생의 설문조사.md` 강사 5-1 "기본기 표준화 부재" — Phase 16 이 한국어 학원 용어 표준 작성 path 시작
- 운영자 5-2 "기술 데이터 기반 표준화" — 분기 3 자동 수집 → 표준화 path
- 운영자 5-2 "폭스탑 3회 분석 예시" — 분기 2 정은지 reference 비등재 동작 정확히 충족

## Plans

- [ ] 16-01-PLAN.md — AKA 매핑 13개 + 5트랙 spec + 정은지 reference 1~2개 + 자동 수집 스키마 + UX 카피 박제 위치 + 실증 검증 게이트 threshold belle 협의

---
*Created 2026-06-02 (belle 결정 박제 — 학원 용어 3분기 + 5트랙 채점 v1 평행 진행)*
