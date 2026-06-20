# Phase 18 — Live Sweep ↔ Baseline Drift 재확정 (Pod 의존 잔여분)

**Generated:** 2026-06-20
**Pod:** `2yz9zre7b4d2sp` (RTX 4090) · commit `5d67d94` · scorer `phase19_vision_hybrid_deduction`
**Run:** serial (`sweep_phase15.py --trigger direct-process`, RUN A mode1 correct + RUN B mode1 fault)
**Baseline:** `backend/evals/phase18/baseline/eval18_serial_baseline.json` (2026-06-18 박제)

> 객관성(D-06 / [[analysis-objectivity-no-human-scores]]): 아래 점수는 채점기 출력 스냅샷이지
> 사람이 매긴 ground-truth 라벨이 아니다. fault 라벨 = 영상 파생(OK).

---

## §drift-table — Mode 1 (vs 정은지 reference) live vs baseline

| motion | live fault | base fault | live success | base success | live margin | base margin | verdict | drift |
|--------|-----------|-----------|--------------|--------------|-------------|------------|---------|-------|
| power-spin | 73 | 72 | 100 | 100 | 27 | 28 | discriminate | fault +1 |
| peter-pan | 79 | 79 | 100 | 100 | 21 | 21 | discriminate | 0 |
| elbow-twist-sister | 61 | 59 | 100 | 100 | 39 | 41 | discriminate | fault +2 |
| pdshape | 60 | 58 | 100 | 100 | 40 | 42 | discriminate | fault +2 |
| kip-up | 100 | 100 | 100 | 100 | 0 | 0 | known_false_positive | 0 |
| climb | not_pole | not_pole | not_pole | not_pole | — | — | known_gate_blocked | 0 |

- **verdict drift = 0/6** — 6개 판정(discriminate ×4 / known_false_positive ×1 / known_gate_blocked ×1)이 baseline 과 100% 일치.
- **score drift = fault 채널 +0~+2** (success 채널·climb 게이트·kip-up 위양성은 정확히 0).
- 모든 discriminate 페어가 fault < success 유지(margin 21~40). regression 아님.

### 판정: Phase 18 regression intact (verdict-level drift 0)

±2 fault drift 는 **byte-identical 아님** — vision-hybrid fault 채널이 Gemini 시각 추론에 의존하고
recognizer/scorer 결정성이 아직 미보장이기 때문(baseline `_meta` 가 "Gemini 인식기 결정성
temp 0 + reference profile 캐싱"을 **Phase 20 과제**로 명시). 즉 이 drift 는 회귀가 아니라
Phase 20 결정성 작업의 동기다. success 채널(정은지=ceiling 100)은 0 drift 로 안정.

---

## §sweep-status — 25 분석 (3 run)

| run | mode | items | OK | failed | 비고 |
|-----|------|-------|----|--------|------|
| A | mode1 correct | 7 | 6 | 1 | climb not_pole (known) |
| B | mode1 fault | 6 | 5 | 1 | climb fault not_pole (known) |
| C | mode3 paired | 12 | 7 | 5 | **Gemini 크레딧 고갈(429) — item 8(pdshape success)부터** |

- Phase 18 scope(Mode1 RUN A+B)는 크레딧 고갈 **전**에 완료 → 데이터 온전.
- RUN C(Mode3, Phase 20 before-baseline)는 부분 — climb/elbow-twist-sister/kip-up 페어만 완료.

---

## §phase20-before-baseline — Mode 3 완전 결과 (Phase 20 입력)

크레딧 충전 후 RUN C2(runId 1781938518415)로 잔여 3페어 재실행 완료 — 6/6 페어 확보.
페어 = prev(fault) → current(success). overall = 절대차원(stability)만, angle(이전 유사도) **제외**.

| motion | fault overall | success overall | success dims | delta(stability) | 비고 |
|--------|--------------|-----------------|--------------|------------------|------|
| climb | 86 | 91 | stability 91 (angle 47 제외) | +5 | 개선 방향 OK |
| elbow-twist-sister | 78 | 83 | stability 83 (angle 43 제외) | +5 | 개선 방향 OK |
| power-spin | 91 | 97 | stability 97 (angle 80 제외) | +6 | 개선 방향 OK |
| kip-up | **98** | 97 | stability 97 (angle 85 제외) | -1 | **#6 위양성**(fault 98, 게이트 부재) |
| peter-pan | **98** | 98 | stability 98 (angle 90 제외) | 0 | fault 98 高 — 변별 약함 |
| pdshape | 87 | **59** | stability 59 (angle 64 제외) | **-28** | success<fault (아래 주) |

- **#8 역전 fix 확인 (6/6)**: 모든 success overall = stability 값, angle 채널 제외 → min() 역전 없음 ([[mode3-overall-exclude-angle-similarity]]).
- **#6 재현**: kip-up·peter-pan fault Mode3 overall 98 (Mode3 는 not_pole/정확성 게이트 없음 — Phase 20 미보유동작 게이트 대상).
- **#1 재현**: kip-up fault Mode1 overall 100 (angle DTW 맹점 — Phase 20 Gemini 시각 거부권 대상).
- **pdshape 주의**: success stability 59 < fault 87 → Mode3 가 "퇴보(-28)" 표시. #8 역전(angle 제외)은 정상 작동했고, pdshape correct 영상의 실제 stability 가 낮은 것(Mode1 에서도 pdshape success stability=59 동일 → 채점 일관). "절대 stability 만으론 동작 품질을 못 가린다"는 Phase 20 Gemini 시각 보강 사례.

---

## 블로커 (해소됨)

**Gemini API 선불 크레딧 고갈 (429 RESOURCE_EXHAUSTED, 2026-06-20)** — sweep RUN C item 8 부터
연쇄 실패. **belle 충전 완료(2026-06-20) → Gemini LIVE 재확인 → RUN C2 로 잔여 3페어 재실행 완료.**
recognizer + coach + vision-hybrid scorer 가 전부 Gemini 의존이므로 Phase 20 개발/eval 전
크레딧 잔량 확인 권장 ([[gemini-credits-depleted-2026-06-20]]).

---

## 종합 판정

- **Phase 18 = verdict-level closed.** Mode1 6/6 verdict baseline 일치, fault 점수 +0~2(Gemini 비결정성, Phase 20 동기). exact-score drift 0 은 Phase 20 결정성 작업 후 재평가.
- **Phase 20 before-baseline 확보** — Mode1(킵업 위양성 100, 변별 4쌍) + Mode3(6/6, 킵업·피터팬 fault 高, pdshape stability 한계). 다음: Phase 20 착수.
