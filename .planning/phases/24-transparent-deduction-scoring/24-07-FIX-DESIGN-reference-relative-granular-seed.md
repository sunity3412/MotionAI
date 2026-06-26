---
phase: 24-transparent-deduction-scoring
plan: 07 (DESIGN — belle 인지용, 구현 직행 가능)
subsystem: scoring / deduction-engine
tags: [granular, reference-relative, per-joint-deviation, recognizer-unregistered, md-empty, kismam-calibration]
status: DESIGN — pod 진단으로 확정된 ① 결함 fix. calibration 기존 재사용(새 결정 불요), belle 인지 후 구현.
---

# Phase 24 Plan 07 (DESIGN): ① granular 미실현 — reference-relative 측정 seed 배선

> pod 재-sweep(2026-06-26)로 확정된 결함 ① fix. **(A)(24-05)는 엔진 게이트를 고쳤지만 md(seed)가 비어 inert**했다. 이 plan 은 비는 md 를 reference-relative 각도 편차로 채워 belle 핵심 wish(−X−Y−Z 항목별 내역)를 실현한다.

---

## 1. 확정된 root cause (pod 실측)

power-spin fault instrumentation 덤프:
```
profile_move          = "미등록: ref-power-spin"   # 인식기가 동작 미등록
expects_extension     = NONE
extension_deviation   = ALL ZERO/NaN
md_keys               = []                          # seed 빔 → 폴백
dimension_scores      = {angle: 72, stability: 91}  # 각도 편차는 측정됨!
```

- 인식기가 reference 동작을 **미등록**으로 반환 → `TechniqueProfile.expects_extension()` 전부 False → `dimensions.extension_deviation()`(profile-gated)가 전부 0 → `_build_deduction_measured_deviations` md 빔.
- **그러나 각도 편차는 측정 가능** — v1 `angle` 차원이 72 로 감점됨. 이건 `per_joint_deviation`(학생↔정은지 DTW-정렬 per-joint median |Δ각도|) substrate에서 나온다. 즉 **측정값은 있는데 deduction 엔진으로 안 흘러간다**(엔진은 IPSF-절대 profile-gated seed 만 먹음).
- = [[phase15-recognizer-student-video-line-none]] 뿌리(미등재 동작 = 신전프로파일 부재). recognizer/IPSF 등록을 고치는 건 도메인 난제 → **우회: 이미 있는 reference-상대 편차를 엔진 seed 로 배선.**

## 2. substrate + calibration (둘 다 기존 — 새로 안 만듦)

- **substrate:** `motiondtw.per_joint_deviation(match.path, user_seg, a_ref)` → `(J,)` per-joint median |Δ각도|(도). climb 5°/elbow-twist 12° 등 noise-robust median(Phase 17-debug). reference angles(`a_ref`)는 apply seam 에 이미 존재(`reference_angles_for_veto`, app.py:3290).
- **calibration:** `kismam._IPSF_TOLERANCE_DEG = 20.0`(관절별 허용편차) + `penalty_per_deg`(Phase 19 D-01 IPSF 감점식). **이 plan 은 이 값을 그대로 재사용** — 자체 sweep 재calibrate 금지([[calibration-source-hard-gate]]). 새 임계/슬로프 picking 0.
- **철학 정합:** ref-상대 편차 감점 = belle "점수=정은지100−측정편차×명시규칙"([[scoring-must-be-transparent-deduction-tally]]) 그 자체. IPSF-절대보다 오히려 더 직접적("정은지 대비").

## 3. Fix 설계

### 3-1. 새 criterion (reference_relative, per-joint)
`ipsf_criteria.CRITERION_GROUPS` 에 reference_relative 각도 criterion 추가. 옵션:
- **(권고) per-joint 단일 family `angle_vs_reference`** — 활성 시 `per_joint_deviation` 의 관절별 편차에서 tol(20°) 초과분마다 record 1개씩 방출 → 리포트가 "−X 왼무릎 −Y 오른팔꿈치" 로 펼침(granular wish 직격).
  - `deviation_source = "reference_relative"`, `ipsf_anchor = "expert_reference_deviation"`(정은지 대비), `tolerance = 20°`(kismam 재사용), rule = kismam penalty_per_deg 동등.
  - 관절 라벨 = JOINT_KEYS(왼/오 무릎·팔꿈치·고관절·어깨 등). UX 카피는 design.md 규칙.

### 3-2. seam 배선
`_build_deduction_measured_deviations` 에 reference angles + DTW match(또는 사전계산 per-joint dev dict)를 threaded → IPSF-절대 seed 가 빈 경우(미등록 동작) reference-relative per-joint 편차를 md 에 주입.
- **중복 차단(중요):** 동작이 등록돼 IPSF-절대(leg/arm/line) seed 가 있으면 reference-relative 는 **그 관절에 대해 추가하지 않음**(double-count 금지). 즉 reference-relative 는 절대-신전 프로파일이 없는 관절/동작의 **보완 seed**. 엔진의 HIGH-5 cross-exclusion 패턴 재사용/확장.
- 엔진(`deduction_engine.tally`)은 이미 reference_relative 를 지원(body_relative_reach 선례) → criterion 추가 + seed 만 하면 동작.

### 3-3. 무엇이 안 바뀌나
- slope/cap/tolerance 상수 **재calibrate 금지**(kismam 값 재사용). 엔진 게이트(24-05) 불변. ipsf_absolute 경로 불변. 순수 함수 유지.

## 4. Edge / 일반화
- 등록 동작(신전프로파일 보유) → 기존 ipsf_absolute granular 그대로(reference-relative 미중복).
- 미등록 동작(power-spin/pdshape 등) → reference-relative per-joint granular **신규 실현**.
- self-compare(같은 영상) → per_joint_deviation median=0 → 감점 0(위양성 0, Phase 17-debug 보장).
- **score-shift:** Mode1 미등록 동작 final 이 dimension_overall(72) → granular reference-relative 합산으로 바뀜. ND-01/05 의도지만 **pod sweep 재검증 필수**: elite/success 95-100 유지, fault 변별 유지, 일반화 게이트(`assert_gates.py`), self-compare 0.

## 5. belle 인지 (새 결정 불요 — 확인만)
1. **calibration 출처 = kismam 기존값(20° tol + penalty_per_deg).** 새 임계 picking 없음([[calibration-source-hard-gate]] 준수). 이의 없으면 그대로.
2. **점수 의미 = "정은지 대비 per-joint 편차 합산"** — belle 철학과 일치. Mode1 헤드라인이 reference-relative 가 됨.
3. **객관성 불변** — per_joint_deviation = 결정론 측정. 사람 점수 라벨 0([[analysis-objectivity-no-human-scores]]).

## 6. Scope / 순서
- **In:** ipsf_criteria 에 reference_relative 각도 criterion + `_build_deduction_measured_deviations` 배선(reference angles thread) + cross-exclusion + 엔진 단위테스트(미등록→per-joint granular, self-compare 0, 등록 동작 미중복) + pod 검증.
- **Out:** recognizer/IPSF 동작 등록(Phase 15 도메인 난제, 별도), kismam 재calibration(금지), kip-up 촬영거리(별개 ③).
- **순서:** ② visibility fix(수술적, 병행) → ① 구현(이 설계) → pod 1회 검증(① 점수shift + ② Gemini 회복 동시).

---
*Phase 24 · Plan 07 DESIGN · 2026-06-26 · pod 진단 확정 ① fix · calibration 기존 재사용*
