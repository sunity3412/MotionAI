---
phase: quick-260627-9dh
plan: 01
status: complete
date: 2026-06-26
commits:
  - 26d479e feat(quick-260627-9dh): add clean-residual + sensitivity eval gates
  - 7023be8 test(quick-260627-9dh): unit cases for clean-residual + sensitivity gates
---

# Quick 260627-9dh — eval 게이트 강화 (clean-residual + above-cutoff sensitivity)

## 무엇을 했나
P1(분석 정확도 부채) 검증 토대 강화. `backend/evals/phase24/assert_gates.py` 에 pod-free 순수 게이트 2개 추가, main() 러너에 등록(이제 7 게이트).

- **check_clean_residual** (artifact-gated): 각 motion 의 `correct`(정타) 멤버 record 들에 대해 `raw = abs(baselineValue - measuredValue)` 를 재구성, criterion tolerance(`ipsf_criteria.CRITERION_GROUPS`)를 초과하면 FAIL. 기존 generalization 은 "fault > success" 상대 속성만 봤음 — 이 게이트는 정타의 **절대** 잔차가 깨끗한지(감점 0) 검증. `dimension_overall_fallback` 는 CRITERION_GROUPS 에 없어 자연 skip(정직-0 폴백은 측정 잔차 아님). 아티팩트 없으면 단일 SKIPPED.
- **check_sensitivity** (synthetic, 항상 실행): leg/arm_extension 각각 `above = 2×tol` → 비-자명 감점(final<baseline + points<0) 강제, `deadzone = tol/2`(nonzero, plan-checker 권고 반영) → 감점 0 강제. tolerance 위에서 무감각하거나 합법 소편차를 over-penalize 하면 FAIL. elite-low 만으로 metric validity 미증명 원칙 충족.

임계는 전부 `CRITERION_GROUPS` tolerance 에서 파생 — curve-fit/매직넘버 없음(grep 가드 통과).

## 검증 결과
- `pytest tests/test_phase24_gates.py -q` → **21 passed** (신규 7개 포함: clean/contaminated/skip/fallback-ignored, sensitivity real-engine-pass/dead-engine-catch).
- 신규 게이트 단독 동작: clean_residual(현 커밋 아티팩트)=깨끗(`[]`), sensitivity(실엔진)=`[]`, clean_residual(오염 40°>20° 합성)=정확히 FAIL.
- `assert_gates.py` main() = **exit 1** — 단, 이 red 는 **기존 generalization 게이트가 kip-up 의 structural false-negative 를 잡고 있는 PRE-EXISTING red**(이 task 전 6b8c9d4 에서도 exit 1 확인). 이 task 는 regression 무도입. exit 1 = 미해결 P1(kip-up 100/100)의 정직한 현 상태.

## P1 흐름에서의 의미 (false-close 차단)
- **kip-up**: generalization 게이트가 이미 red 로 잡고 있음 → P1 fix 가 GREEN 으로 바꿔야 닫힘.
- **정타 오염(14~18°)**: clean-residual 게이트가 대기 중. 현재 커밋된 아티팩트는 clean-fallback 이라 깨끗하지만, **24-07 granular reference-relative 아티팩트가 pod sweep 으로 갱신되면** 오염된 정타 잔차에서 red 발화 → P1(객관 IPSF 채점)이 이걸 GREEN 으로 바꾸는 것으로 검증.
- **민감도**: sensitivity 게이트가 metric 이 above-cutoff 에서 살아있음을 합성으로 상시 보증.

## 파일
- `backend/evals/phase24/assert_gates.py` (+2 게이트, main 등록, 도크스트링)
- `backend/tests/test_phase24_gates.py` (+7 테스트)

## 다음 (P1 흐름)
step (2) `/gsd-debug` — recognizer 가 동작별 IPSF 기하 요건을 왜 등록 못 하나(코드 갭 vs IPSF 데이터 부재) 근본 못박기.
