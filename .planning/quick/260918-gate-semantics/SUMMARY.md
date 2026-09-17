---
id: 260918-gate
title: 재학습 승격 게이트 — SKIPPED 와 DESCOPED 를 가른다
date: 2026-09-17
status: complete
---

# 요약 — 재학습 게이트 수리

belle 승인: **"게이트부터 고쳐"**.

**판정: 됐다. 그리고 이건 정책 결정이 아니라 설계-구현 불일치였다.**

## 무엇이 고장나 있었나

2026-09-14 실측: 데이터 임계를 넘겨 재학습을 돌려도 **구조적으로 NOT PROMOTED** 로
끝난다. `--require-pass` 가 SKIPPED 하나라도 남으면 exit 3 인데, SKIPPED 가 **설계상
반드시 남기** 때문이다.

그런데 한 통에 **의미가 다른 세 가지**가 섞여 있었다:

| 유형 | 예 | 학습으로 PASS 가능? |
|---|---|---|
| ① 데이터셋이 선언한 한계 | eval18 kip-up `known_false_positive` · climb `known_gate_blocked` | **불가** |
| ② belle 이 끈 트랙 | perturb 0행 (C1, 2026-07-15 descope) | **불가** |
| ③ 못 잰 것 | `SFT bake-off run1 artifact absent` | 가능 |

①②에 승격을 막으면 **어떤 모델도 통과할 수 없다.**

## ★ 이건 정책이 아니라 구현이 선언을 어긴 것이다

두 곳이 이미 정답을 적어두고 있었다:

- `assert_gates.py` 모듈 독트린:
  > 변별 4페어만 **hard 게이트**, kip-up/climb 은 **명시 추적만**(pairs.yaml).
- 같은 파일 perturb 주석:
  > **안 가르친 능력을 요구하는 게이트는 어떤 모델도 통과시킬 수 없다.**
  > 느슨하게 만드는 것이 아니다 — perturb 를 되살리면 게이트도 같이 되살아난다.

**선언은 "추적만"인데 구현이 차단 게이트로 쓰고 있었다.** 그래서 belle 에게 "설계상
SKIPPED 를 PASS 로 볼 것인가"를 다시 물을 일이 아니었다 — 이미 정해진 것을 코드가
안 지키고 있었다.

## 수리

`SKIPPED` 와 `DESCOPED` 를 가른다.

- **DESCOPED** = 선언된 범위 밖. 승격을 **막지 않는다.** 표시는 **항상** 한다.
- **SKIPPED** = 쟀어야 하는데 못 쟀다. **그대로 막는다.**
  "못 쟀다"를 "통과"로 번역하지 않는다.

`--require-pass` 는 FAIL + SKIPPED 만 막는다.
범위를 넓히려면 `pairs.yaml` 의 `expected` 를 `discriminate` 로 바꾸거나
`SFT_WITH_PERTURB=1` 로 perturb 를 되살리면 **그 순간 자동으로 hard 게이트가 된다.**

### 소비자 계약 무접촉

`run_all_checks()` 의 `{label: (fails, skips)}` 형태를 유지했다 —
`promotion.parse_gate_verdict` 는 `fails` 만 읽으므로 1바이트도 안 바뀐다.
DESCOPED 는 `skips` 통 안의 접두어로만 구분하고, 판정은 `blocking_skips()` 한 곳에서만 한다.

## 이게 느슨해진 것인가 — 아니다

- 변별 4페어(power-spin·peter-pan·elbow-twist-sister·pdshape)는 **그대로 hard 게이트**
- 나머지 4게이트(motion_balance·determinism·traceability/monotonicity·synthetic_holdout)
  도 그대로
- **artifact 부재는 그대로 차단** (`test_unmeasured_still_blocks_promotion`)
- DESCOPED 항목은 FAIL/PASS/require-pass 세 경로 **전부에서 출력**된다 (은폐 0)

## 검증

신규 테스트 4건. 그중 핵심:

```
test_require_pass_reaches_exit0_with_only_descoped
  — 실제 manifest.yaml / pairs.yaml 을 읽는다(fixture 장난 아님)
  — 범위 안을 다 재면 --require-pass 가 **exit 0 에 도달**한다
  — 고치기 전에는 같은 조건에서 항상 exit 3 이었다
  — DESCOPED 항목이 출력에 **보이는지**까지 단언
```

```
pytest 4831 passed / 20 skipped / 0 failed   (기준선 4827 + 신규 4)
```

## 남은 것 — 이걸로 재학습이 되는 건 아니다

게이트는 이제 **도달 가능**해졌을 뿐이다. 실제 승격은 4개 hard 게이트를 모델이
통과해야 한다. 직전 판(v38, 2026-08-28)까지 **승격 이력 0건**이다.

★ 그리고 `.planning/TRAINING-DUE.md` 의 "직전 판(v29)" 기준선은 낡았다 —
실제 직전은 **v38** 이고 v28/v29/v35/v36/v38 전부 `promoted=false`.
