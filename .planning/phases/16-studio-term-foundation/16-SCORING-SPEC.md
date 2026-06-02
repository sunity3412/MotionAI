# 16-SCORING-SPEC.md — IPSF 5-Track Scoring v1 Architectural Decision

**Phase**: 16 (Studio Terminology Foundation)
**Plan**: 16-01 (T-2 산출물)
**Mode**: spec / architectural decision (코드 변경 0)
**Created**: 2026-06-02
**Authority**: 본 문서는 채점 엔진 구현/리팩토링이 따르는 architectural decision. PROJECT.md Key Decisions + memory [[ipsf-5-track-scoring]] 와 lockstep.

---

## 1. Goal

서니티 채점 엔진이 IPSF Code of Points 의 **4공식 트랙 + 1 절대 공통 트랙 = 5트랙** 구조를 따른다는 architectural decision 박제. v1/v2 scope 분리 + 동작 인식 케이스별 활성 트랙 매트릭스를 명문화한다.

본 문서가 박제되는 이유: mode3 (reference 없는 채점) + 학원 용어 분기 2/3 (IPSF 비등재) 케이스에서 "왜 채점이 합법인가" 의 근거가 architectural decision 으로 박제되지 않으면 후속 plan (Phase 5/14/15) 에서 잃기 쉬움. Page 9 "all components" 절대 트랙이 모든 분기에서 단독 작동 가능하다는 게 핵심.

---

## 2. 5트랙 구조 (IPSF 공식)

NotebookLM lookup 2026-06-02 결과 (notebook `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3`):

### 4공식 트랙

| # | 트랙 | 평가 대상 | Max | Citation |
|---|---|---|---|---|
| (a) | Compulsory Criteria | 사전 선언한 등재 기술의 동작별 9~11개 기하학적 Criteria 점검 | 11점 (Senior Elite) | IPSF Pole Sports CoP 2025-2027 Page 18 |
| (b) | Technical Bonus | 연계 (Dynamic Combinations / Combining Spins) 가산 | +25점 | IPSF Mid-Cycle Update Appendix 2024 Page 5, CoP 2025-2027 Page 16 |
| (c) | Technical Deduction | 자세/정렬/실수 감점 | -25점 | IPSF Pole Sports CoP 2021-2024 Page 9 |
| (d) | Artistic & Choreography | Flow / 창작 / 전환 / 무대 장악 | 20점 | IPSF Pole Sports CoP 2025-2027 Page 4, IPSF Aerial Pole CoP 2024-2025 Page 12 |

총점 max 63점 (Senior Elite 기준).

### 5번째 트랙 — Page 9 "all components" 절대 감점 공통 트랙

IPSF Pole Sports CoP 2021-2024 **Page 9** 명시:
> "This applies to components performed both on the floor and on the pole."

→ (c) Technical Deduction 의 sub-set 이지만 **동작 코드와 무관하게 모든 움직임에 공통 적용**. 동작 인식 실패/hybrid/비등재/자유 루틴 케이스에서도 단독 작동 가능 → mode3 (reference 없음) + 분기 3 (미등재) 채점의 IPSF 공식 근거.

| 항목 | 감점 | 우리 파이프라인 측정 |
|---|---|---|
| Fall | -3.0 | 높이 급변 + 접촉 손실 |
| Slip | -1.0 | 그립 위치 jitter |
| Loss of Balance | -0.5 | 중심 흔들림 (스턴저티) |
| Poor Alignment (무릎-발끝, 굽은 어깨) | -0.2 ~ -0.5/회 | 관절각 직접 |
| Poor Transitions (거친 진입/탈출) | -0.5 | jerk/속도 불연속 |
| Poor Presentation (불리 각도) | -0.5 | 카메라축 vs 신체축 |
| Sickling (발끝 굽음 fail) | -0.2 | 발목 각도 |
| Toe Point 결여 | -0.2 | 발끝 포인트 각도 |

---

## 3. v1 / v2 Scope 결정

### v1 박제 (Phase 5~15 통합 대상)

- **(a) Compulsory Criteria** — 분기 1 등재 동작에서 정밀 채점 (Phase 5 Gemini 기술 인식기 + Phase 14 정은지 reference)
- **(c) Technical Deduction (Page 9 5번째 트랙 포함)** — 모든 분기에서 작동
- **5번째 절대 공통 트랙 단독 작동** — 분기 3 (미등재) + 동작 인식 실패 케이스에서 핵심

근거 요건:
- SCORE-05 (REQUIREMENTS.md) — "(a) Compulsory Criteria + (c) Technical Deduction 두 트랙 + Page 9 'all components' 절대 공통 트랙"
- TERM-01 — 분기 3 단독 작동 보장 (Page 9 트랙)

### v2 박제 (별 마일스톤)

- **(b) Technical Bonus** — Dynamic Combinations / Combining Spins 연계 인식 필요. v1 에서 연계 인식기 미구현 → 추후. (SCORE-V2-02 REQUIREMENTS.md)
- **(d) Artistic & Choreography** — Flow / 무대 장악 등 정성 평가. 사람 점수 라벨링 영구 금지 ([[analysis-objectivity-no-human-scores]]) → AI 객관 측정 가능 sub-set (예: Flow seamless 측정값) 만 후속 v2. (SCORE-V2-03 REQUIREMENTS.md)

---

## 4. 트랙별 측정 가능성 매핑 (현 NLF 3D 파이프라인)

| 트랙 | v1/v2 | 측정 가능성 | 현 파이프라인 구현 위치 |
|---|---|---|---|
| (a) Compulsory Criteria | v1 | ✓ (Gemini 기술 인식 + GeometricCriterion lookup) | Phase 5 + technique.py |
| (b) Technical Bonus | v2 | ✗ (연계 인식기 미구현) | TBD |
| (c) Technical Deduction (일반) | v1 | ✓ (각도/라인/jerk 등 직접 측정) | dimensions.py + temporal.py |
| (c) Page 9 5번째 트랙 | v1 | ✓ (Fall/Slip/Balance/Alignment/Toe Point 모두 NLF 3D 키포인트로 측정 가능) | dimensions.py (각도/라인) + features.py (안정성) + temporal.py (jerk) |
| (d) Artistic Flow seamless | v2 | △ (jerk/속도 연속성으로 부분 측정 가능, 정성 평가 X) | 후속 |
| (d) Artistic 창작 / 무대 장악 | v2 / 영구보류 | ✗ (사람 점수 라벨링 영구 금지) | 영구 보류 |

---

## 5. 동작 인식 케이스별 활성 트랙 매트릭스

채점 엔진은 동작 인식 결과 + 학원 용어 분기에 따라 다음 트랙을 활성화한다:

| 케이스 | 활성 트랙 | mode | 분기 |
|---|---|---|---|
| **인식됨 + IPSF 등재 (분기 1)** | (a) Compulsory + (c) + Page 9 트랙 (+ (d) v2) | mode1 reference 채점 | 분기 1 |
| **인식됨 + IPSF 비등재 + 정은지 reference 있음 (분기 2)** | (c) + Page 9 트랙 + 정은지 측정값 기준 비교 | mode1 reference 채점 | 분기 2 |
| **인식 실패 또는 미등재 + reference 없음 (분기 3)** | **Page 9 절대 트랙 단독** | mode3 (reference 없는 발전 표시) | 분기 3 |
| **mode3 (자기 영상 2개 비교, 분기 무관)** | Page 9 트랙 절대지표 세션 간 델타 | mode3 | 분기 1/2/3 모두 |

**핵심 결정**: Page 9 트랙이 모든 케이스에서 작동하므로 **"동작 인식이 실패해도 채점 자체는 합법"** — mode3 + 분기 3 의 IPSF 공식 근거.

---

## 6. PROJECT.md / REQUIREMENTS.md / Memory Cross-Reference 정합성

본 문서가 일관성을 유지해야 하는 source:

| Source | 위치 | 정합 항목 |
|---|---|---|
| PROJECT.md Active Requirements "점수 신뢰도" | `.planning/PROJECT.md` | "IPSF 5트랙 채점 시스템 v1 박제" 항목 |
| REQUIREMENTS.md SCORE-05 | `.planning/REQUIREMENTS.md:37` | (a) + (c) + Page 9 트랙 |
| REQUIREMENTS.md TERM-01 | `.planning/REQUIREMENTS.md:41` | 분기 3 = Page 9 단독 작동 |
| REQUIREMENTS.md JUDGE-01 | `.planning/REQUIREMENTS.md:80` | judging 모드 (a) Compulsory 정밀 채점 |
| REQUIREMENTS.md JUDGE-DATA-01 | `.planning/REQUIREMENTS.md:81` | GeometricCriterion 데이터 형식 = (a) 정밀 채점 입력 |
| memory [[ipsf-5-track-scoring]] | `~/.claude/.../memory/ipsf-5-track-scoring.md` | 5트랙 구조 박제 원본 |
| memory [[judging-baseline-ipsf-code-of-points]] | `~/.claude/.../memory/` | IPSF 단일 기준 |
| memory [[scoring-dimensions-ipsf]] | `~/.claude/.../memory/` | angle/line/stability 차원 = 5번 트랙 측정 항목 |
| memory [[mode3-progress-not-similarity]] | `~/.claude/.../memory/` | mode3 의 reference 없는 채점 → Page 9 트랙 단독 작동 근거 |
| memory [[analysis-objectivity-no-human-scores]] | `~/.claude/.../memory/` | (d) Artistic 정성 부분 영구 보류 근거 |

---

## 7. Architectural Decision (박제)

**서니티 AI 코치 채점 엔진은 IPSF 5트랙 구조를 따른다. v1 = (a) Compulsory Criteria + (c) Technical Deduction + Page 9 절대 공통 트랙. v2 = (b) Technical Bonus + (d) Artistic & Choreography. Page 9 트랙은 모든 동작 인식 케이스 (등재/비등재/실패/자유 루틴) 에서 단독 작동 가능하며, mode3 + 분기 3 채점의 IPSF 공식 근거다.**

**불변 원칙**:
1. 채점 엔진의 점수는 IPSF Code of Points 임계값 기반 — 사람 점수 라벨링 (belle/강사/심사자) 영구 금지 ([[analysis-objectivity-no-human-scores]]).
2. (b)/(d) v2 진입 시에도 객관 측정 가능 sub-set 만 — (d) 의 정성 평가 부분 (창작 / 무대 장악) 은 영구 보류.
3. Page 9 트랙은 **항상 활성** — 등재 동작에서도 (a) 와 동시 작동.

---

## 8. v1 진입 위치 (후속 plan)

| Phase | 통합 항목 |
|---|---|
| Phase 5 | (a) Compulsory Criteria 정밀 채점 (Gemini 기술 인식 + GeometricCriterion lookup) |
| Phase 8 / Phase 12 | (c) 일반 + Page 9 트랙 (jerk / 안정성 / 각도 / 라인 차원 통합) |
| Phase 14 | 정은지 reference 측정값 → 분기 2 채점 입력 |
| Phase 15 | 5트랙 통합 점수 합성 + 신뢰도 게이트 (고수 위양성 방지) |

---

*Created 2026-06-02 (Plan 16-01 T-2 산출물 — IPSF 5-Track architectural decision 박제)*
