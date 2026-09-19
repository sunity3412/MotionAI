---
id: 260919-mhl
title: 확대 비교 카드 짝 품질 — 시간 정렬 이탈 방출 (관측 전용)
date: 2026-09-19
status: done
tasks: 3/3
commits:
  - 3adef64f  feat  순수 계층 (warp 미러 + 이탈 산출 + 시험 22건)
  - 40fcf8de  feat  배선 (두 카드 경로 + 화이트리스트 매퍼 + 시험 8건)
  - 3ed5ac0b  docs  3-way lockstep 등재 (analysis.ts / models.py / contract §11.12 + 시험 7건)
gates:
  backend_pytest: 4872 passed / 0 failed / 20 skipped  (기준선 4835 + 신규 37, 회귀 0)
  app_tsc: clean
---

# 확대 비교 카드 짝 품질을 시간 정렬 이탈로 방출한다 — 실행 결과

**한 줄:** 카드마다 `pairDeviationSec`(+ `pairDeviationTier`) 한 값을 doc 까지 흘리는
계기를 달았다. 게이트·점수·카드 산출은 한 줄도 건드리지 않았다.

## 무엇을 했나

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | `motion_alignment.warp_time` (TS 정본 미러) + `pair_time_deviation_sec` (타임베이스 환산 + fail-closed) | `3adef64f` |
| 2 | `_attach_pair_time_deviation` 헬퍼 + 호출 2곳 + 화이트리스트 매퍼 복사 절 | `40fcf8de` |
| 3 | `analysis.ts` / `models.py` / `docs/contract.md §11.12` 등재 | `3ed5ac0b` |

**바뀐 파일 6개 / +852 −1** (−1 은 `app.py` 의 단일행 import 를 다중행으로 바꾼 것):

- `backend/shared/python/sunity_shared/analysis/motion_alignment.py` (+180, additive only)
- `backend/functions/pipeline/app.py` (+119)
- `backend/tests/test_pair_time_deviation.py` (신규, +459, 시험 37건)
- `app/src/types/analysis.ts` (+31 — **타입 선언만**, 런타임 코드 0)
- `backend/shared/python/sunity_shared/models.py` (+3 — **주석만**, 코드 0)
- `docs/contract.md` (+61 — §11.12 신설)

### 배선 경로

`result["motionAlignment"]` 는 `_attach_motion_alignment` 가 `complete_analysis` 직전에
붙이고, 카드 두 경로는 전부 그 뒤의 사후 스테이지라 **같은 `result` 객체**를 받는다
(재조회 0). 두 경로 모두 업로드 매퍼 호출 **직전**에 부착한다:

- `_render_fault_zoom` — `comps + adv_comps` (confirmed·advisory 둘 다). 최종 doc 은
  `items + stage1_keep + advisory_keep` 합집합이라 한쪽만 실으면 구멍이 생긴다.
- `_run_gated_card_inherit` — `gated_raw`. 이 경로는 실효 rate 판정 불가 시 이미
  early return 이라 `eff` 가 항상 유효하다.

`anchor_fps` 는 `_pipeline_frame_fps()` 단일 출처(리터럴 9.0 금지 — 테스트가 박제).
헬퍼 전체가 `try/except` 로 감싸여 있어 **어떤 실패도 카드를 죽이지 않는다.**

## 계획서와 달라진 것

### 1. `pairDeviationTier` 를 동반 필드로 추가했다 (계획서엔 필드 1개)

라이브 실측상 프로덕션 tier 는 `trim_only` 35 / `disabled` 1 / **`warped` 0** 이고
거의 모든 doc 에서 `us[0]=rs[0]=0` 이라 **warp 가 사실상 항등함수**다. 즉 지금 이
필드의 값은 "warp 보정된 이탈"이 아니라 **거의 생짜 시간차**다. tier 없이 값만 실으면
이름이 값보다 커 보여 **새 거짓 라벨**이 된다. 값이 실릴 때만 tier 를 동반한다
(짝 없는 라벨 방지). 세 곳 lockstep 에 함께 등재했다.

### 2. `tier` 미등재 값도 `None` 으로 거른다 (계획서는 `disabled` 만 명시)

`warped`/`trim_only` 가 아닌 tier 를 `warped` 분기로 오독하면 근거 없는 수가 나온다.
fail-closed 로 수렴시켰다 (`test_none_when_tier_unknown`).

### 3. 계획서 §타임베이스의 "순서는 보존된다" 문장은 **쓰지 않았다**

오케스트레이터 실측이 그 문장을 반증했다 (아래 §"증명하지 못하는 것" 참조).
`contract.md` 와 본 SUMMARY 어디에도 그 서술이 없고, 테스트가 금지어로 박제한다
(`test_contract_md_records_reproduction_failure_not_a_baseline` 의
`assert "순서는 보존된다" not in sec`).

## 경계 — 지켰는지 실측

`git diff 76c305ea..HEAD` 기준:

- `card_gates.py` · `dimensions.py` · `kismam.py` · `assemble.py` ·
  `deduction_engine.py` · `fault_zoom.py` — **diff 0** (파일이 변경 목록에 없다).
- `app.py` diff 에서 `refMatched` / `refMatch` / `pair_gate` / `PAIR_POSE_MAX` /
  `pair_state` 를 포함하는 추가·삭제 줄은 **주석 2줄뿐**이고 코드 줄은 0.
- 게이트 표면 카운트를 테스트가 박제한다: `PAIR_POSE_MAX` 2회 · `pair_state` 1회 ·
  `pairState` 3회 · `c["pairState"] = decision.pair_state` 존재
  (`test_existing_pair_gate_surface_unchanged`).
- 앱 런타임 `.ts`/`.tsx` 변경 0 — 바뀐 앱 파일은 타입 선언 파일 `analysis.ts` 하나.
- **삭제된 파일 0** (`git diff --diff-filter=D` 빈 출력).
- 새 필드를 **읽는** 코드는 리포에 0건이다 (선언 3곳 + 방출 3곳 + 시험 + 계약 문서뿐).
  `pairDeviationSec >`, `<`, `>=`, `<=`, `abs(pairDeviation`, `PAIR_DEVIATION_MAX`
  전부 부재를 테스트가 단언한다.
- `ROADMAP.md` 무접촉.

## 게이트 (backend/.venv 인터프리터로 직접 실측)

```
$ backend/.venv/bin/python -m pytest -q      # 착수 전 기준선
4835 passed, 20 skipped, 42 warnings in 48.58s

$ backend/.venv/bin/python -m pytest -q      # 3 Task 완료 후
4872 passed, 20 skipped, 42 warnings in 47.68s     # = 4835 + 신규 37, 회귀 0

$ cd app && npx tsc --noEmit
(무출력, exit 0)
```

인터프리터: `backend/.venv/bin/python` = Python 3.14.6.
[[dont-trust-subagent-gate-numbers]] 대로 서브에이전트 수치를 인용하지 않고 직접 돌렸다.

## 이 단위가 증명하지 못하는 것 (정직하게)

### ★ 인계서 §6 의 4행 표는 재현되지 않는다 — 기준값으로 인용 금지

계획서는 그 표(팔꿈치 −4.28 / 오른무릎 +0.67 / 왼골반 −0.13 / 오른어깨 −0.20)를
"belle 눈 4/4 순서 일치로 검증된 것"으로 다뤘지만, 계획 수립 **이후** 라이브 Firestore
실측(doc 47건 / 카드 192장, belle doc `01668c02…`)에서 **네 가지 해석 전부로 재현에
실패했다**: (a) 계약 warp(카드 초 그대로) · (b) 앵커 곡선 보간 · (c) rep 공간
`refFrameIdx/18` · (d) 양측 앵커축 정정판(본 단위 공식에 가장 가까운 것).
산출에 쓰인 세션 스크립트는 scratchpad 와 함께 사라졌다.

| 카드 | 인계서 §6 (**재현 실패 — 기준값 아님**) | (d) 실측 |
|---|---|---|
| 팔꿈치 8.1초 | −4.28초 | −5.33초 |
| 오른무릎 5.7초 | +0.67초 | −1.11초 |
| 왼골반 16.7초 | −0.13초 | −6.00초 |
| 오른어깨 3.4초 | −0.20초 | −2.00초 |

**크기뿐 아니라 순서도 일치하지 않는다.** `|이탈|` 내림차순이
§6 = 팔꿈치 > 오른무릎 > 오른어깨 > **왼골반**(왼골반이 최선)인데
(d) = **왼골반** > 팔꿈치 > 오른어깨 > 오른무릎(왼골반이 최악)으로,
왼골반이 정확히 반대 끝으로 간다. 오차가 전 카드 공통 절편이 **아니라는** 뜻이다 —
보정항이 `t` 에 비례하는 항을 포함하고 왼골반 카드만 시각이 다른 카드의 2~5배다.
그래서 `contract.md §11.12` 는 절 머리에 **잠정(provisional)** 을 달고, 이 공식이
**코드에서 유도한 것이고 belle 눈으로 재검증되지 않았다**고 명시한다.
([[handoff-observation-not-diagnosis]] — 진단을 관측처럼 적으면 다음 세션이 승계한다.)

### 라이브 doc 에서의 값은 못 봤다

Pod 이 내려가 있고 실증은 10월 중순으로 밀렸다([[pilot-postponed-to-mid-october]]).
이 단위는 **합성 입력 단위 시험까지**다. 실제 이탈값이 belle 눈과 같은 자리에
떨어지는지는 **다음 Pod 때 라이브 doc 1건으로** 확인해야 한다.
[[wiring-claims-need-log-evidence]] — "배선했다"를 "값이 맞다"로 말하지 말 것.
부착 로그 문자열은 `pair_time_deviation attached cards=… emitted=… tier=…` 이고,
다음 Pod 때 이것으로 회수한다.

### 통과선은 여전히 없다

표본 4개(0.2 통과 / 0.7 경계 / 4.3 실패)로는 경계선을 못 정한다 — belle 판정 대기.
게다가 그 표본 자체가 위 재현 실패 대상이다. **이 값으로 카드를 숨기거나 문구를 내면
안 된다.**

### 현재 값은 사실상 생짜 시간차다

`warped` tier 가 프로덕션에 0건이라 warp 보정이 실질적으로 일어나지 않는다.
`warped` 분기는 계약상 존재하고 시험도 있지만 **지금 데이터에는 없다.**
`pairDeviationTier` 가 이 사실을 값과 함께 운반한다.

### `refMatched=true` 거짓 보증은 그대로 살아 있다

인계서 §7 고칠 것 2번. 이 필드는 그 거짓말을 **고치지 않는다** — 사후에 짝 품질을
알 수단을 하나 만들 뿐이다. 관련 실측(확정 수치): 카드 192장 전수에서
`refMatched` True 163 / 키 부재 29(legacy) / **False 0**, `refMatch` `'dtw'` 163 /
부재 29 / **`'failed'` 0**. 즉 `refMatch='failed'` 는 프로덕션 0건이다.

## 막힌 곳 / 추측으로 채운 곳

없다. 계획서가 "읽어보니 유도가 성립하지 않으면 멈추고 물을 것"이라고 단 ref 축 수렴
(`rSec = ref9_idx / 9.0`)은 코드에서 성립을 확인했다:

- `_attach_motion_alignment` 가 mode1 은 `ref_fps=reference_kp_fps`(ref doc
  keypointReport fps = rep 공간 18.0), mode3 는 `ref_fps=_pipeline_frame_fps()`(9.0)
  로 넘긴다.
- DTW path 의 ref 인덱스가 사는 공간은 `fault_zoom` docstring 이 명시하듯
  mode1 = `r_rep_fps`, mode3 = 9fps 다.
- `_to_rep_idx = round(idx / frames_fps * rep_fps)` 이므로
  `rep_idx ≈ ref9_idx × rep_fps/9.0` → `rSec = rep_idx / rep_fps = ref9_idx / 9.0`.
  mode3 는 `rep_fps = 9.0` 이라 항등이고 같은 결론.

이 유도는 `test_timebase_conversion_changes_the_value` +
`test_exact_alignment_match_is_zero_after_conversion` +
`test_no_label_drift_reduces_to_plain_subtraction` 세 시험이 박제한다.

## 다음 단위 후보 (이번엔 하지 않았다)

1. **라이브 doc 1건으로 belle 눈 대조** → 통과선 판정 요청. (§11.12 의
   provisional 딱지를 떼는 유일한 길 — 다음 Pod 가동 시 최우선.)
2. `refMatched` 거짓 보증 제거 — 형제 규칙(`atMatched`) 적용.
3. 통과선 확정 후 게이트 축 교체(`PAIR_POSE_MAX` → 시간 이탈).

## Self-Check

- 커밋 3건 존재 확인: `3adef64f` / `40fcf8de` / `3ed5ac0b` (`git log --oneline -3`).
- 변경 파일 6개 전부 디스크에 존재하고 `git diff --stat 76c305ea HEAD` 로 대조 완료.
- 게이트 수치는 `backend/.venv/bin/python` 으로 직접 실행한 출력을 그대로 옮겼다.
- **Self-Check: PASSED**
