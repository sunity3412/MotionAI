# Phase 20-04 — Reference-Anchored Veto: 6-Pair Generalization Eval

**Generated:** 2026-06-20
**Pod:** `2yz9zre7b4d2sp` (RTX 4090) · commit `c3f26a9` · PROMPT/SCHEMA v4.0
**Veto:** Mode1 reference-anchored comparison (정은지 ref 영상 vs 학생), Mode3 held (mode3_held)
**Cap (spec-anchored):** major=50 / moderate=75 / minor·none = no cap. belle spec "잘못된 동작 ≤50" + IPSF severity. NOT curve-fit (6페어는 derive 입력 아님).

> 객관성(D-06): 점수=채점기 출력. 사람 점수 라벨 아님. 비교 프롬프트는 동작명·정답 0 (짜맞추기 금지, [[scoring-redesign-must-generalize-no-overfit]]).

---

## §6pair — Mode1 정타 vs 잘못된 영상 (veto ON, reference-anchor)

| motion | correct overall | correct veto | fault overall | fault veto | margin | 비고 |
|--------|----------------|--------------|---------------|-----------|--------|------|
| kip-up | 100 | not_applicable | **75** | **moderate** | 25 | **#1 위양성 수정** — veto가 비-각도 결함 포착 |
| elbow-twist-sister | 100 | not_applicable | 63 | none | 37 | 각도 deduction이 포착 |
| pdshape | 100 | not_applicable | 60 | none | 40 | 각도 deduction |
| peter-pan | 100 | not_applicable | 79 | none | 21 | 각도 deduction |
| power-spin | 100 | not_applicable | 72 | none | 28 | 각도 deduction |
| climb | not_pole | gate | not_pool | gate | — | known_gate_blocked |

## 판정

- **over-penalization 해결**: 정타 5/5 → 100, veto not_applicable (정은지 정타를 결함으로 스탬프하지 않음). belle spec "같은 정은지 95~100" 충족. 일반화(kip-up 단일 아님).
- **#1 위양성 수정**: kip-up fault 100(angle DTW 맹점 가짜 100) → **75 (veto moderate)**. belle 육안("가벼운 결함, 50 아래는 아님")과 일치 — 무지성 ≤50 스탬프 아님([[vision-score-must-analyze-not-stamp]]).
- **상보 작동**: 각도형 결함(elbow/pdshape/peter-pan/power-spin)은 deduction이 60~79로 잡고 veto는 none(과잉 0). 비-각도형(kip-up)만 veto가 잡음.
- **변별 5/5** (margin 21~40). climb 게이트.

## 진화 (반복 — belle "정상까지 반복 + 짜맞추기 금지")

| 버전 | 방식 | 정타 | kip-up fault | 판정 |
|------|------|------|-------------|------|
| v2 | 단일영상 + leading 프롬프트 | 50 ❌ | 50 | 다 깎음(over) |
| v3 | 단일영상 + clean 선택지 | 100 ✅ | 100 ❌ | 다 봐줌(under) |
| **v4** | **reference-anchor 비교** | **100 ✅** | **75 ✅** | **변별 OK** |

## 남은 일

- belle 디바이스 육안 재확인 (kip-up ~75). 단 빌드 #21은 20-03 UI 미포함 → 헤드라인은 수정 반영되나 부제·세부 문구는 옛 100 기준(모순) → 새 EAS 빌드 필요.
- #4(b) 온라인 sensitivity 셋(미보유+above-cutoff)으로 일반화 추가 검증 (현재 = 보유 6페어).
- Mode3 veto = 보류(mode3_held). Mode3 위양성(#6)은 별도(미보유 게이트).
