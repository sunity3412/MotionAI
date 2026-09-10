---
id: 260910-ovo
title: 붕괴 사지 판정불가 게이트
date: 2026-09-10
status: done
---

# 관측하지 못한 사지에는 감점을 매기지 않는다 (붕괴 축 한정)

한 줄: **감점의 측정 순간에 그 사지가 렌즈 축으로 포개져 있으면 감점 seed 자체를
방출하지 않는다** — 행도 확대 사진도 안 생기고, 없앤 사실은 `result.unjudgedJoints`
에 남는다.

## 임계 조정 여부

**조정하지 않았다.** PLAN 의 값을 그대로 썼다.

- `COLLAPSE_ASPECT_MAX = 0.10`
- `COLLAPSE_LENGTH_FRAC_MAX = 0.60`

결과를 보고 옮긴 적이 없다. 아래 §정립 fixture 에 PLAN 기준으로 "깨진" 항목이
하나 있고, 임계를 옮기는 대신 **깨진 그대로 보고**한다.

## 커밋

| 커밋 | Task | 바뀐 파일 |
|---|---|---|
| `c4d9eb0` | 1 | `backend/shared/python/sunity_shared/analysis/limb_collapse.py` (신설)<br>`backend/tests/test_limb_collapse.py` (신설, 27건) |
| `4c3cfc4` | 2 | `backend/functions/pipeline/app.py`<br>`backend/shared/python/sunity_shared/models.py`<br>`docs/contract.md`<br>`app/src/types/analysis.ts`<br>`backend/evals/realfixture/replay.py`<br>`backend/tests/test_collapse_gate_wiring.py` (신설, 7건) |
| `f2d5cd3` | 3 | `app/src/app/analysis/result.tsx` |

## 검증 숫자 (착수 전 / 후)

| 계기 | 착수 전 | 착수 후 |
|---|---|---|
| `backend` pytest | **4609 passed** · 12 failed · 27 skipped · **7 collection errors** | **4643 passed** (+34 = 신규 27+7) · 12 failed · 27 skipped · 7 collection errors |
| `app` `tsc --noEmit` | **0 에러** | **0 에러** |
| `app` `node --test` | **241 pass** / 0 fail | **241 pass** / 0 fail |

- 실행: `cd backend && python3 -m pytest -q --continue-on-collection-errors`
- **`--continue-on-collection-errors` 를 붙인 이유 (착수 전부터의 환경 결손)**:
  `imageio_ffmpeg` 가 로컬 python 어디에도 없어(`python3.12/3.13/3.14` 전부 확인)
  `compare_render` 를 import 하는 테스트 모듈 7개가 수집 단계에서 죽는다. 인계서의
  "4731 passed" 는 그 7모듈이 살아 있던 환경의 숫자다. **이 결손은 내가 만들지
  않았고 고치지도 않았다** — 패키지 설치는 이 실행자의 자동 수리 범위 밖이다.
- 착수 전/후 **실패 12건은 동일한 목록**이다 (`test_fault_zoom_ref_match` 3 ·
  `test_fault_zoom_ref_marked` 4 · `test_fault_zoom_deferred` 2 ·
  `test_caption_cause_layer` 2 · `phase34/test_measurement_window` 1). 전부 선행 결함.

## 재현 하네스 결과

실행: `python3 backend/evals/realfixture/replay.py --collapse-gate-report`
(신설 플래그. GPU 0 · Pod 0 · Gemini 0 · Firestore 쓰기 0 — 죽는 스텁이 실행으로 증명.)
산출물: `.planning/quick/260910-ovo-collapse-gate/collapse_gate_effect.json`

### (1) 수리 전/후 byte-동일 — 게이트를 안 켠 경로

`git show HEAD:` 로 수리 전 `app.py` + `replay.py` 를 별도 트리에 꺼내 같은 재생을
돌리고 diff 를 냈다. **md · measuredAt · records · points · final · RECON verdict
전부 byte-동일** (4 fixture 전건). 게이트는 켜야 켜진다.

### (2) 게이트 on/off 대조

| fixture | 판정 | final | record | 카드 unit | 사진0장멈춤 | **저장 record 소멸** |
|---|---|---|---|---|---|---|
| powerspinFault | **CHANGED** | 62 → 67 | 4 → 2 | 4 → 2 | **0** | **0** |
| kipupFault | BYTE-동일 | 99 → 99 | 1 → 1 | 1 → 1 | **0** | **0** |
| pdshapeCorrect | BYTE-동일 | 100 → 100 | 1 → 1 | 1 → 1 | **0** | **0** |
| elbowtwistsisterFault | BYTE-동일 | 63 → 63 | 8 → 8 | 8 → 8 | **0** | **0** |

- **사진 0장이 되는 멈춤 = 0건** (전 fixture). 멈춤은 record 에서 태어나므로
  (`compare_render.py:1227` records 루프 → `:1345` freezes.append) record 를 안
  만들면 멈춤도 같이 안 생긴다 — 구조적으로 0이고, 실측도 0이다.
- **설명 안 되는 record 소멸 0 · 새 record 0.**

### (3) ★ 정립 fixture — PLAN 기준으로 powerspin 이 깨졌다

PLAN §Task 2 verify 는 "정립 fixture(powerspin / kipup): record 집합·points·카드
수 byte-동일. 하나라도 바뀌면 실패"다. powerspin 이 바뀌었으므로 **깨졌다고 보고한다.**

빠진 두 행과 실측 숫자:

| 관절 | 측정 프레임(9fps) | aspect | L/medL | 판정 |
|---|---|---|---|---|
| `left_hip` (다리) | 7 | 0.0082 | 0.5314 | 붕괴 |
| `right_hip` (다리) | 11 | 0.0000 | 0.4735 | 붕괴 |

내가 재서 확인한 것 두 가지:

1. **하네스 어댑터 탓이 아니다.** 결측 placeholder(0,0) 복원을 켜고 끄고 재도
   숫자가 같다(powerspin 에는 placeholder 가 0개). 좌표·중앙값 모두 저장값 그대로다.
2. **빠진 두 행은 저장 doc 에 없던 행이다.** MANIFEST 의 저장 record 는
   `leg_extension` · `split_angle` · `angle_vs_reference__left_shoulder` 셋뿐이고,
   hip 2행은 RECON 이 이미 **EXTRA** 로 찍어 둔 재현본 전용 행이다(하네스가 vision
   주입 `split_angle` 을 재현하지 못해 엔진 cross-exclusion 이 안 걸린 기계적 파생 —
   `_cause_for` 가 그렇게 설명한다). 즉 **저장 record 소멸은 4 fixture 전부 0**이다.

판단을 유보한 채 사실만 적는다: PLAN 문언대로면 실패, 저장 record 기준이면 무영향.
어느 쪽으로 볼지는 belle 판정 대상이다. 임계는 건드리지 않았다.

### (4) 대표 사례 계열 — 요구대로 나온다

fixture 4건에는 대표 사례(`c64afae6`)가 없다(라이브 Firestore doc). 그래서 그 doc
하나를 **읽기만** 해서(쓰기 0) 배포된 판정기로 직접 물어봤다.
증거: `.planning/quick/260910-ovo-collapse-gate/rep_case_judgement.txt`

| criterion | at(9fps) | rep | aspect | L/medL | 판정 |
|---|---|---|---|---|---|
| `angle_vs_reference__left_elbow` | 81 | 162 | 0.7476 | 1.1556 | 정상(감점 유지) |
| `angle_vs_reference__right_elbow` | 81 | 162 | **0.0522** | **0.4628** | **판정불가(미방출)** |
| `angle_vs_reference__right_shoulder` | 35 | 70 | 0.0095 | 0.6790 | 정상(감점 유지) |
| `angle_vs_reference__left_hip` | 45 | 90 | 0.0000 | 1.0253 | 정상(감점 유지) |
| `angle_vs_reference__left_knee` | 57 | 114 | 0.2306 | 1.2630 | 정상(감점 유지) |
| `angle_vs_reference__right_knee` | 59 | 118 | 0.0000 | 1.3554 | 정상(감점 유지) |

- **`right_elbow` 계열 1건만 빠지고 `left_elbow` 는 남는다** — 요구 그대로다.
- 숫자가 PLAN 의 실측표와 일치한다: 0.0522 vs 표 0.052, 0.4628 vs 표 0.46,
  왼팔 0.7476 vs 표 0.748.
- **AND 조건이 실제로 일한 자리 2곳**: `left_hip` 은 aspect 0.0000(완전 공선)인데
  길이비 1.03 이라 살아남았다 — 공선성만 썼으면 여기서 위양성이 났다.
- ★ **경계에 앉은 것 1건**: `right_shoulder` 는 aspect 0.0095 로 아주 납작한데
  길이비 0.679 가 임계 0.60 을 **0.079 차로** 넘겨 살아남았다. 표본이 늘면 이
  근처가 먼저 흔들린다. 임계 재검토 때 첫 번째로 볼 자리다.

## 계약 3벌

`docs/contract.md` §4 `unjudgedJoints` 절 신설 ↔ `models.UNJUDGED_REASONS` ↔
`analysis.ts` `UnjudgedReason` / `UnjudgedJoint` / `AnalysisResult.unjudgedJoints?`.

- 형상: `[{ joint, reason }]` = **map 의 배열**. Firestore 가 막는 것은 배열 안의
  배열이지 배열 안의 map 이 아니라서 평탄화하지 않았다(`faultZoomComparisons[]` 선례).
- `reason` 은 `'collapse'` 하나지만 **문자열 enum 으로 열어 뒀다** — 신뢰도 축이
  나중에 붙는다.
- **빈 배열 `[]` = 봤는데 붕괴 0 / 필드 부재 = 안 봤다**. 앱은 둘 다 아무것도 안
  그리지만 doc 에서는 구분된다 (quick-260802-nfd 가 `attributionReliability` 에서
  배운 것과 같은 이유 — 발화 때만 실으면 "발화해야 하는데 안 했나"를 검증 못 한다).

## 계획에서 벗어난 것 (Rule 2 — 없으면 게이트가 사문)

`dtw_frame_by_joint`(감점의 대표 프레임)를 채우는 조건이 **`measured_at_out` 이
dict 일 때뿐**이었다. 게이트는 그 프레임을 봐야 하므로, 표시용 out-param 을 안 준
호출자에게는 게이트가 **조용히 사문**이 된다. 조건을
`isinstance(measured_at_out, dict) or limb_collapsed is not None` 으로 넓혔다.
내 배선 테스트가 실제로 이 구멍을 잡아서 고쳤다(`limb_collapsed=lambda: True` 인데
감점이 하나도 안 사라졌다). `limb_collapsed=None` 이면 추가 계산 0 =
byte-동일이고, 위 §(1) 대조가 그것을 실행으로 확인한다.

계획에 없던 파일 2개를 더했다:
- `backend/tests/test_collapse_gate_wiring.py` — 배선 7건(미전달=종전 산출, 관절
  단위, 순간 미상 fail-open, 판정기 예외 fail-open, reason enum, result 부착).
- `backend/evals/realfixture/replay.py` 에 어댑터 + `--collapse-gate-report`
  (기존 `--noise-floor-report` 선례를 그대로 따랐다).

## PLAN "★ 하지 말 것" 준수

- 신뢰도(conf) 기준 **미도입**. `limb_collapse.py` 는 conf 를 읽지 않는다.
- `temporal.py` / `features.py` **무접촉** (`git show --stat` 로 확인 가능).
- 좌우(chirality) 코드 **무접촉**.
- `VideoCompare.tsx` · `RenderedComparePlayer.tsx` · `sourceSwapSeek.ts` ·
  `analysisDate.ts` · `ResultScoreDial.tsx` **무접촉**.
- `ROADMAP.md` **무수정**. 이 SUMMARY 는 **커밋하지 않았다**.
- 임계 **무조정** (위 §임계 조정 여부).

## 검증의 한계 (PLAN §검증의 한계 승계)

- ★ **이 수리는 새 분석에만 적용된다. belle 의 기존 doc 은 이미 저장된 값이라 안
  바뀐다.** 위 대표 사례 표는 "지금 그 doc 을 다시 분석하면 이렇게 나온다"는 예측
  이지, 화면에 그렇게 보인다는 뜻이 아니다. belle 이 눈으로 보려면 **Pod 을 띄워
  재분석**해야 한다 — 그건 이 작업 다음 단계다.
- 재현 하네스는 저장값 재조립이지 실제 추론이 아니다. 실제 파이프라인에서 같은
  판정이 나오는지는 Pod 실행으로만 확인된다.
- 하네스 어댑터의 알려진 차이(코드에 박제): 길이 중앙값을 production 은 9fps
  `pose_frames` 에서, 하네스는 18fps rep 프레임에서 낸다. 보간값이 이웃 사이에
  놓여 중앙값은 거의 같지만 byte-동일 보장은 아니다.
- **카드는 PNG 를 렌더해서 센 것이 아니다.** 이 환경에서 렌더 경로가 못 돈다
  (`_build_native_frame_provider` → `compare_render` → `imageio_ffmpeg` 부재 —
  pytest 수집 오류 7건과 같은 결손, 수리 전후 동일). 대신 카드 존재를 실제로
  정하는 순수 함수 `fault_zoom.criterion_units_from_records` 를 셌다. 픽셀 수준
  확인은 Pod/실기기 몫이다.
- **앱 한 줄은 시뮬레이터에서 렌더해 보지 않았다.** typecheck 와 node --test 만
  돌렸고, 그 둘은 렌더 크래시를 못 잡는다([[verify-ui-on-simulator-before-ota]]).
  OTA 전에 시뮬 확인이 남아 있다.
- 임계 2개는 표본 5대상에서 나왔다. **역립 동작이 더 들어오면 재검토 대상**이고,
  가장 먼저 흔들릴 자리는 위 §(4) 의 `right_shoulder`(0.679, 임계와 0.079 차)다.

## 남은 것 (belle 판정 대상)

1. **문구 확정** — `UNJUDGED_NOTE` 상수 한 줄. 지금은 초안
   "N곳 중 M곳은 가려져서 못 봤어요".
2. **powerspin hip 2행을 어떻게 볼 것인가** — PLAN 문언대로 실패로 볼지,
   저장 record 무영향으로 볼지 (§(3)).
3. **Pod 재분석** — 기존 doc 에 반영하려면 필요하다.
