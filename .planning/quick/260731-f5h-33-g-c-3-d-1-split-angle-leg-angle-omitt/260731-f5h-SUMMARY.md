---
phase: quick-260731-f5h
plan: 01
subsystem: fault-zoom-render
tags: [33-G, C-3, D-1, S10, repair-cycle, display-only]
requires:
  - "quick-260730-l7t D-1 근본원인 실측 (crop 멤버 집합 ↔ 드로잉 점 집합 어긋남)"
  - "32-14 keypointReport 12관절"
  - "quick-260705-r6x 사이각 드로잉 + _pt_in_crop 게이트"
provides:
  - "_leg_line_pts crop 인지 끝점 선택 (ankle→knee, 측별 독립, in_crop 술어 주입)"
  - "_draw_side_leg_angle 이 자기 crop box 로 만든 _pt_in_crop 클로저를 주입"
  - "12관절 doc 에서 split_angle 다리 사이각 성립 (S10 합성 좌표 판정)"
affects:
  - "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
  - "backend/tests/test_fault_zoom.py"
tech-stack:
  added: []
  patterns:
    - "술어 주입(in_crop) — build_angle_bake_spec(resolver) 선례 따름"
    - "후보 순회 폴백 = 게이트 AND crop 포함 (기본값 None 이면 종전과 동치)"
    - "A/B 픽셀 오라클 검증 (임계값 0개) — 프로덕션 심볼 no-op 교체 후 byte 대조"
key-files:
  created:
    - .planning/quick/260731-f5h-.../sweep_leg_angle.py
    - .planning/quick/260731-f5h-.../sweep_out/{before,after,before-noladder,after-noladder}/
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/tests/test_fault_zoom.py
decisions: [deferred 2안 채택, 1안(REGION_MEMBERS 확대) 미채택, 3점 게이트 존치]
metrics:
  duration: "~1.5h"
  completed: 2026-07-31
---

# quick-260731-f5h: 33-G §C-3 D-1 다리 사이각 crop 인지 끝점 Summary

`split_angle`(legs) 카드에서 12관절 학생 doc 의 ankle 이 crop 밖으로 나가 사이각이
통째로 생략되던 것을, `_leg_line_pts` 의 다리 끝 선택을 **그 카드 crop 에 들어오는
관절**로 제한해 수리했다 (deferred 2안, crop 배율 무변경).

---

## 1. 수리 내용

**변경 = `fault_zoom.py` 함수 2개 + import 1줄.** 그 밖은 손대지 않았다.

- `_leg_line_pts(report, frame_idx, *, in_crop=None)` — 키워드 전용 술어를 받아
  다리 끝 후보를 `ankle → knee` 순으로 순회하고, 각 후보는 `_gated_kp`(conf ≥
  `_KP_CONF_MIN`) 통과 **AND** (`in_crop` 이 주어졌다면) `in_crop` 통과여야 채택한다.
  좌/오를 각각 독립 호출하므로 한쪽만 crop 밖이어도 그 측만 knee 로 내려간다(계약 6행).
  `in_crop=None` 이면 순회가 종전 `ankle or knee` 와 정확히 동치다(기본값 계약).
  골반(hips 중점) 로직은 무수정 — 골반은 폴백이 없다.
- `_draw_side_leg_angle` — `h, w` 와 `left, top, side` 언팩을 `_leg_line_pts` 호출
  **앞으로** 옮기고 `in_crop=lambda xy: _pt_in_crop(xy, left, top, side, w, h)` 를 넘긴다.
  포함 판정의 단일 출처는 계속 `_pt_in_crop` 이고 마진(`_CROP_INCLUSION_MARGIN_PX`)은
  그 함수만 소유한다 — 하네스에도 `_leg_line_pts` 에도 복제하지 않았다.
  그 뒤의 3점 AND 게이트와 `_draw_leg_angle` 의 `_MIN_LEG_VEC_PX` degenerate 검사는
  **존치**했다(골반 방어 + 이중 안전망, locked_spec 4).

**1안(`REGION_MEMBERS["legs"]` 에 ankle 추가) 미채택 사유** — crop 이 발끝까지 넓어져
"부위 확대" 성격이 약해지고 32-03 parity 수치가 이동한다. 2안은 crop 배율이 불변이라
파급이 없고, 선이 정강이(knee)까지만 그려지는 것은 2안의 의도된 귀결이며 승인 범위 안이다.

**표시 전용, 채점 무접촉.** `git diff --name-only -- app/ backend/functions/ docs/` = 빈 문자열.

---

## 2. 검출 방법과 그 근거 (임계값 0개)

다리 사이각이 "실제로 픽셀에 그려졌는가"를 판정해야 하는데, 쓸 수 있어 보이는 두 방법이
**둘 다 부적격**이라 A/B 픽셀 오라클을 만들었다.

**(a) `_panel_has_angle` 재사용 불가 — 구조적으로 못 잡는다.**
그 함수는 패널 **정중앙(180,180) 반경 16px**(`_ANGLE_ARC_R_FRAC*_OUT`)의 흰 픽셀을 세는
S8 각도 호 판정이다. 다리 사이각 호는 반경 `int(_OUT*0.14)=50` 이고 중심이 정중앙이 아니라
**골반 픽셀**이다 (실측: ref-power-spin 학생 패널 골반 = (192, 87), 기준 패널 = (180, 86)).
색도 다르다 — S8 호는 흰색(`_HALO`), 다리 호는 브랜드색(`_BRAND`). 반경·중심·색이 전부
어긋나므로 재사용하면 항상 False 가 나온다.

**(b) 브랜드 픽셀 카운트 임계 불가 — 폴백 원 마커가 같은 색 링이다.**
미드로잉 시 폴백은 `_mark(circle=True)` 의 `_BRAND` 색 링(`r=int(_OUT*0.16)=57`, `width=4`)
이라 픽셀 수가 선+호와 같은 자릿수다. 이번 스위프에서 관측된 실제 값:

| 상태 | 학생 패널 `_BRAND` px | 기준 패널 `_BRAND` px |
|---|---|---|
| 폴백 원 마커 (before, 미드로잉) | 1356 | 1356 |
| 드로잉, 끝점 = knee (after) | 1646 | 1587 |
| 드로잉, 끝점 = ankle | 1903 / 2176 / 2339 | 1587 |

전역 임계를 두려면 (1356, 1587) 사이 **231 카운트 폭**에 선을 그어야 하는데, 그 폭은 지금
crop 내용물과 선 길이가 우연히 만든 값이지 근거가 있는 수가 아니다. 기준 패널의 **드로잉**
값(1587)이 학생 패널의 **폴백** 값(1356)보다 겨우 17% 클 뿐이고, 다리 벡터가 짧아지면
드로잉 값이 폴백 값 아래로 내려간다. 근거를 댈 수 없는 임계는 쓰지 않았다.

**(c) 채택 = A/B 픽셀 오라클.** 같은 카드를 두 번 렌더한다.
  - (A) 정상 렌더
  - (B) `fz._draw_leg_angle` 를 "인자 무시하고 False 반환"하는 no-op 로 교체한 렌더
  - `leg_drawn = (png_A != png_B)`

`_draw_leg_angle` 가 False 를 주면 `_draw_side_leg_angle` 도 False → 호출측이 원 마커로
폴백하므로 픽셀이 **반드시** 달라진다. 반대로 정상 렌더가 이미 폴백 중이었다면 두 산출이
byte-동일하다. 즉 `png_A != png_B` ⟺ 사이각이 실제로 그려졌다. **추정 0, 임계 0.**
교체는 컨텍스트 매니저(`__exit__`)로 원복하고, 디스크 PNG 는 (A) 정상 렌더분을 쓴다.

이 오라클이 성립하려면 렌더가 결정적이어야 하므로 **카드마다 (A) 를 한 번 더 렌더해
byte 동일을 확인**했다(`deterministic` 컬럼, 불변식 (5)). 110 카드 × 4 실행 전건 True.

**crop 기하 계측도 프로덕션 함수만 호출한다.** `_draw_side_leg_angle` 를 pass-through
스파이로 감싸 호출마다 `(box, frame 크기, 반환값)` 을 기록하고, 그 box 로 `fz._pt_in_crop`
과 `fz._gated_kp` 를 **직접** 호출해 `pelvis_in_crop`/`*_ankle_in_crop`/`*_knee_in_crop`/
`*_endpoint_expected` 를 산출했다. crop 계산식 복제 0, 마진 복제 0.
측 라벨은 호출 순서가 아니라 report 객체 identity 로 정했다(더 강한 판정).

---

## 3. 10동작 스위프 (before → after)

동작 목록은 `backend/judging_data/criteria/*.yaml` glob 파생 — 하드코딩 0.
학생 12관절의 **ankle 좌표만** 정렬 인덱스 파생 사다리로 흩어 벌림 크기를 동작축에 실었다
(동작명 문자열 분기 0). hips/knees/상체 및 기준 8관절은 불변.

| motion | ankle y | L ankle in crop | endpoint L/R | before `leg_drawn` | after `leg_drawn` | PNG changed |
|---|---|---|---|---|---|---|
| ref-climb | 0.68 | True | ankle/ankle | True | True | **False** |
| ref-elbow-twist-sister | 0.71 | True | ankle/ankle | True | True | **False** |
| ref-foxtop | 0.74 | True | ankle/ankle | True | True | **False** |
| ref-foxtop-split | 0.77 | False | knee/knee | False | **True** | True |
| ref-invert | 0.80 | False | knee/knee | False | **True** | True |
| ref-kip-up | 0.83 | False | knee/knee | False | **True** | True |
| ref-pdshape | 0.86 | False | knee/knee | False | **True** | True |
| ref-peter-pan | 0.89 | False | knee/knee | False | **True** | True |
| ref-power-spin | 0.92 | False | knee/knee | False | **True** | True |
| ref-sideway-spin | 0.95 | False | knee/knee | False | **True** | True |

- **after = 10/10 드로잉.** 미드로잉 잔여 0.
- **끝점이 동작축에서 ankle/knee 로 갈린다** — 계약 1행(ankle 유지)과 2행(knee 폴백)이
  같은 실행에서, **같은 규칙 하나**로 처리됐다는 실증. 갈림의 기준은 좌표와 crop 기하뿐이다.
- **ankle 이 crop 안인 3동작은 PNG 해시가 before 와 byte-동일**(changed=False) —
  "지금 그려지는 것은 그대로"라는 단조 추가 계약이 픽셀 수준에서 지켜졌다.
- `--compare before after`: 변경 카드 **7건 전부 `split_angle`**, 단일관절 각도 카드
  (`angle_vs_reference__*`)·`leg_extension`·`arm_extension` 전건 해시 동일.
- after 실행에서 **비-split 카드 `leg_drawn` = 0** (게이트 A 무손상).
- 기존 4 불변식(동작명 분기 0 / 정중앙 배율 동일 / parity / 각도 대칭) 위반 0.
- INV-D1(`leg_drawn == (user 측 성립 AND ref 측 성립)`) after 전건 성립.

### 사다리 정의와 재조정 여부

```
ankle_y = 0.68 + 0.03*i      ankle_x = 0.505 ∓ (0.10 + 0.02*i)      i = 정렬 인덱스 0..9
```

**재조정 없음 — 플랜 사다리를 그대로 썼다.** 실측 legs crop box = `(73, 247, 219)`
@360x640 이고 (l7t 기록치와 **정확히 동일**), 그 box 의 ankle y 허용 상한이 0.76(in)/
0.77(out) 이라 위 사다리가 i=0..2 / i=3..9 로 갈린다.

> 절차상의 사실 1건: 처음에 나는 crop box 를 "pelvis 중심 220px 정중앙 박스"로 손계산해
> 사다리가 전건 crop 밖이 될 거라 오판하고 `y = 0.60 + 0.02*i` 로 **먼저 바꿔서** 돌렸다
> (9/10 드로잉). 실제 box 를 스파이로 재보니 `(73, 247, 219)` 였고 플랜 사다리가 맞았다 →
> 플랜 값으로 되돌리고 before 를 재캡처했다. 프로덕션 상수는 어느 시점에도 건드리지 않았다.

### 대조군 — 사다리 없는 원본 형상 (`--no-ladder`)

플랜 (3-2) 은 "before 0건"을 예상했는데 **사다리를 적용한 before 는 3건**이 나왔다.
그 3건은 사다리가 ankle 을 crop **안**에 넣은 동작들(계약 1행)이라 지금도 정상 드로잉이
맞다 — 즉 D-1 의 반증이 아니라 사다리 ④ 의 귀결이다. 그래도 플랜이 말한 전제를 직접
재보려고 `_USER_KP` 원본(ankle y 0.828/0.848 = l7t 가 D-1 을 실측한 그 좌표)으로 대조
스위프를 한 벌 더 돌렸다:

| 실행 | split_angle 드로잉 | 변경 카드 |
|---|---|---|
| before-noladder (수정 전, 원본 좌표) | **0 / 10** | — |
| after-noladder (수정 후, 원본 좌표) | **10 / 10** | split_angle 10건뿐 |

플랜의 "before 0 → after 전건"은 원본 형상에서 **정확히 그대로** 재현됐다.
(상세 보고 = §6)

---

## 4. 4층 검증 결과

각 항목 뒤에 **그것을 성립시킨 행위**를 적었다.

### (1) 무회귀 해시 — PASS
`python3 legacy_baseline.py --verify` 를 **돌려서** `PASS — 9 case / 9 card 해시 동일`,
`legacy_baseline.json` `match: true` 를 **확인했다**. legacy/advisory/mode3 9케이스는
한 장도 바뀌지 않았다. (수정 전에도 같은 커맨드로 `match: true` 를 먼저 확인해 복사한
`legacy_baseline_before.json` 이 HEAD 에서 유효함을 실증한 뒤 코드에 손댔다.)

### (2) 10동작 일반화 스위프 — PASS
`sweep_leg_angle.py --out after --assert` 와 `--compare before after` 를 **돌렸다**.
결과는 §3 표. `--assert` exit 0, `--compare` exit 0(`변경 카드 = split_angle 뿐`).

### (3) 단위 테스트 — PASS (RED 선행 확인)
새 테스트 2개를 **먼저 쓰고 돌려서 RED 를 확인했다**:
- `test_leg_line_pts_crop_aware_endpoint_selection` → `TypeError: _leg_line_pts() got an
  unexpected keyword argument 'in_crop'`
- `test_draw_side_leg_angle_uses_knee_when_ankle_outside_crop` → `assert False is True`
  (ankle 이 crop 밖일 때 미드로잉 = D-1 버그 그 자체)

구현 후 `pytest backend/tests/test_fault_zoom.py -q` = **70 passed**,
`PYTHONPATH=backend/tests pytest backend/tests/phase33 -q` = **122 passed**.
기존 테스트(`test_leg_line_pts_pure` · `test_pt_in_crop_pure` ·
`test_draw_side_leg_angle_skips_when_hip_outside_crop` · `test_legs_valid_side_draws_angle` ·
`phase33/test_criterion_vertex_crop.py` 의 2-인자 `_leg_line_pts(rep, 0)`)는 **한 줄도
수정하지 않고** 통과했다 — 기본값 계약이 지켜졌다는 뜻.

### (4) 회귀 스위트 — PASS (node ID 집합 diff 0)
HEAD 에서 먼저 캡처한 `pytest_baseline_before.txt`(58 node ID)와 수정 후 산출을
`diff` **로 대조했다** → 출력 없음.

```
before: 58 failed, 3763 passed, 26 skipped
after : 58 failed, 3765 passed, 26 skipped      (passed +2 = 이번 신규 테스트)
FAILED/ERROR node ID diff = 빈 출력 → 회귀 0
```
기존 실패 58건은 pre-existing (quick-260730-l7t deferred D-2).

### (5) 육안 — PASS (PNG 를 Read 도구로 직접 열었다)

| 파일 | 본 것 |
|---|---|
| `before/ref-power-spin__split_angle.png` | 두 패널 모두 **브랜드색 원 마커**. 다리 선/호 없음 |
| `after/ref-power-spin__split_angle.png` | 두 패널 모두 골반 꼭짓점에서 양다리로 뻗는 **선 2개**, 원 마커 사라짐 |
| `after/…` 골반 ±90px 3배 확대 (학생·기준 각각) | 두 선 사이에 **사이각 호**가 실제로 그려져 있음 (r=50, 중심=골반 픽셀). "A" 자 가로획으로 보인다 |
| `before/ref-sideway-spin__split_angle.png` | 두 패널 모두 원 마커 |
| `after/ref-sideway-spin__split_angle.png` | 두 패널 모두 선 2개 + 호 |
| `before/ref-climb__split_angle.png` ↔ `after/…` | **육안 차이 없음** (해시도 동일). ankle 이 crop 안이라 선이 종전대로 발목까지 내려간다 |
| `after-noladder/ref-foxtop-split__split_angle.png` | 원본(l7t 실측) 좌표에서도 두 패널 선 2개 + 호 |

확인 항목별:
- (a) 골반 중점에서 양다리로 뻗는 선 2개 + 사이각 호 — **보인다** (확대 컷에서 호까지 확인).
- (b) 선이 몸과 무관한 방향으로 폭주하지 않는가 — **폭주 없음**. 두 선이 골반 한 점에서
  아래로 벌어지는 정상 "∧" 형상이고 캔버스 경계에 눌린 흔적이 없다.
- (c) 두 패널(학생·기준) 모두에 그려졌는가 — **양쪽 다** (both-or-neither 유지).
- (d) before 에는 그 자리가 원 마커였는가 — **그렇다** (7건 전부).

**끝점이 좌표로 키잉된다는 시각 증거를 픽셀로도 재봤다** — 학생 패널 `_BRAND` 픽셀의
최하단 y 를 각 카드에서 측정해 `_to_crop_px` 예측치와 대조했다:

| 끝점 | 동작 | 측정 최하단 y | 예측 끝점 y |
|---|---|---|---|
| ankle | ref-climb / elbow-twist-sister / foxtop | 309 / 341 / 359 | 309 / 341 / 359 (일치) |
| knee | 나머지 7동작 | 281 전건 | 280 (= right_knee, +선폭) |

ankle 케이스는 최하단 y 가 사다리를 **따라 움직이고**, knee 케이스는 knee 좌표가 고정이라
7동작 전부 281 로 **고정된다**. 선이 발목까지 가느냐 정강이까지 가느냐가 동작 이름이 아니라
좌표로 갈린다는 직접 측정.

---

## 5. 계약 6행 대조 (locked_spec 표)

| # | 상황 | 수정 후 | 무엇으로 확인했나 |
|---|---|---|---|
| 1 | ankle 게이트 통과 + crop 안 | ankle 유지 | 단위 테스트 + 스위프 3동작 PNG **해시 byte-동일** |
| 2 | ankle 통과 + crop 밖, knee crop 안 | knee 로 그림 | 단위 테스트 + 스위프 7동작 False→True |
| 3 | ankle 부재(8관절 doc) | knee (종전 동일) | 단위 테스트 + legacy 9케이스 해시 불변 |
| 4 | ankle·knee 둘 다 crop 밖 | 미드로잉 유지 | 단위 테스트(술어가 둘 다 배제 → None) |
| 5 | 골반 crop 밖 | 미드로잉 유지 | 단위 테스트(끝점은 전부 crop 안인데 골반만 밖 → False, `_draw_leg_angle` 호출 0) + 기존 테스트 무수정 통과 |
| 6 | 좌우 비대칭 | 측별 독립 | 단위 테스트(왼 ankle 만 배제 → 왼=knee, 오른=ankle) |

계약 6행은 **단위 테스트로 갈렸다**. 스위프에서는 1·2·3행이 실물 렌더로 겹쳐 확인됐다.
4·5·6행은 스위프 합성 좌표에서 발생하지 않는 조합이라 **스위프로는 안 봤다**(단위 테스트만).

---

## 6. 데이터가 플랜과 안 맞은 것 (보고, 재논의 아님)

**플랜 (3-2) 판정 기준은 "before 0건"이었는데 사다리 적용 before 는 3건이었다.**

- 원인: 플랜 ④ 사다리가 i=0..2 의 ankle 을 crop **안**에 넣는다. 그 3동작은 수정 전에도
  정상 드로잉이 맞다(계약 1행). 플랜 ⑥ 의 사다리 캘리브레이션 게이트("`left_ankle_in_crop`
  에 True 와 False 가 둘 다 있어야 한다")를 만족시키면 before 드로잉이 0 일 수 없으므로,
  플랜 ④ 와 (3-2) 의 "0건"은 서로 양립하지 않는다.
- 처리: 임계를 조정하거나 baseline 을 재캡처하지 않았다. 대신 사다리를 끈 대조군
  (`--no-ladder`, `_USER_KP` 원본 = l7t 가 D-1 을 실측한 바로 그 좌표)을 **한 벌 더 돌려**
  플랜이 말한 전제를 직접 측정했다 → **before 0/10 → after 10/10**, 변경 카드 split_angle 뿐.
- 결론: D-1 근본원인과 수리 효과는 플랜대로다. 어긋난 것은 플랜 내부의 두 서술(④ 와 3-2)
  사이이고, 실측은 양쪽을 각각 재현했다.

**crop box 실측이 l7t 기록과 일치했다** — 스위프가 스파이로 잡은 legs crop box =
`(73, 247, 219)`, 원본 좌표의 `left_end` out = `(78.8, 465.1)`. 플랜 locked_spec 에 적힌
l7t 기록치와 소수점까지 같다. 재조사 없이 그 기록을 이 하네스가 독립적으로 재현한 셈이다.

---

## 7. 한계 · 미검증 (조용히 PASS 처리 금지)

| 항목 | 왜 못 봤나 | 어디서 볼 것 |
|---|---|---|
| **기준 패널 좌표가 합성** | 기준 영상이 로컬에 없다(§C-4 Pod 이관). 프레임은 실물 360x640 을 쓰되 keypointReport 는 형상만 맞춘 합성(학생 12관절 / 기준 8관절 phase4_v1) | §C-4 Pod 재스위프 |
| **실 12관절 doc 판정** | 위와 같은 이유. 이번 판정은 전부 합성 좌표 위의 것이다 | §C-4 Pod 실 doc |
| **앱 화면에서 본 것 아님** | 백엔드 PNG 산출까지만 확인했다. 앱 확대비교 카드 렌더는 이번에 **안 봤다** | 일괄 OTA 후 시뮬/실기기 |
| 계약 4·5·6행의 스위프 실증 | 합성 좌표에서 그 조합이 발생하지 않는다 | 단위 테스트로만 확인함 (실 doc 에서 자연 발생 시 §C-4) |
| 선이 실제 다리와 겹치는가 | 좌표가 합성이라 사진 속 인물과 정렬되지 않는다. "선 2개 + 호가 기하적으로 정상"까지만 봤고 **해부학적 정합은 안 봤다** | §C-4 실 doc PNG |

---

## 8. 33-G 표 S10 갱신 제안

현재 단서 = "12관절 doc 미검증". 아래로 갱신을 제안한다 (§C-4 에서 최종 판정):

> **S10 — PARTIAL → PASS(합성) / 실 doc 판정 대기.** 근본원인(crop 멤버 집합 ↔ 드로잉 점
> 집합 어긋남) 수리 완료(quick-260731-f5h, deferred 2안). 등재 10동작 합성 스위프에서
> 다리 사이각 드로잉 0/10 → 10/10, ankle 이 crop 안인 형상은 PNG byte-불변.
> **실 12관절 doc 판정은 §C-4 Pod 재스위프에서.** 선이 정강이까지만 그려지는 경우가
> 있는 것은 2안의 의도된 귀결(crop 배율 불변)이며 승인 범위 안.

---

## Deviations from Plan

### 1. [절차] 사다리를 먼저 바꿨다가 실측 후 플랜 값으로 되돌림
- **발견 시점:** Task 1 (1-b)
- **내용:** crop box 를 손계산으로 오판해 사다리 시작점을 낮춰 돌렸다(9/10 드로잉).
  스파이로 실제 box `(73, 247, 219)` 를 재보니 플랜 사다리가 맞아 되돌리고 before 재캡처.
- **영향:** 프로덕션 상수 변경 0. before 산출은 플랜 사다리로 재생성된 것만 남아 있다.

### 2. [플랜 확장] `--no-ladder` 대조군 추가
- **이유:** 플랜의 "before 0건" 전제를 직접 측정해 사다리 효과와 D-1 자체를 분리하기 위해.
- **영향:** 하네스에 플래그 1개 + 게이트 조건 1줄. 프로덕션 무접촉.

### 3. [보고] 측 라벨을 호출 순서 대신 report identity 로
- **이유:** 플랜은 "ref→user 호출 순서로 라벨링" 을 제시했으나, 객체 identity 비교가
  순서 가정 없이 성립하는 더 강한 판정이다.
- **영향:** 하네스 내부만. 판정 결과는 동일(ref 가 먼저 호출되는 것도 관측으로 확인됨).

### 4. [보고] Task 2 verify 의 동결 심볼 grep 게이트가 false positive
- **내용:** 게이트 정규식이 `#` 주석만 제외해서, 내가 새로 쓴 **docstring 산문**에 등장한
  `REGION_MEMBERS` / `_CROP_INCLUSION_MARGIN_PX` 문자열 2줄을 위반으로 잡았다.
- **처리:** 임의 판단으로 넘기지 않고 AST 로 재검증했다 — HEAD 와 작업트리에서
  `_box_for`(중첩) · `_crop_box` · `_crop_box_centered` · `_render_crop` ·
  `_render_crop_padded` · `_gated_kp` · `_pt_in_crop` · `_draw_leg_angle` · `_to_crop_px` ·
  `_side_crop` · `REGION_MEMBERS` · `_CROP_INCLUSION_MARGIN_PX` · `_REGION_JOINTS` ·
  `_BBOX_MARGIN` · `_CROP_FRAC` · `_CRITERION_CROP_FRAC` · `_MIN_LEG_VEC_PX` ·
  `_KP_CONF_MIN` · `CRITERION_REGION` 의 소스 세그먼트를 추출해 **전건 byte-동일** 확인.
  변경된 최상위 심볼은 `_leg_line_pts` 와 `_draw_side_leg_angle` **둘뿐**이다.

### Rule 1/2/3 자동수정
없음 — 플랜 범위 안에서 버그/누락/차단 발생 0.

---

## 위협 대응 (threat_model 대조)

| Threat ID | 처리 |
|---|---|
| T-f5h-01 (저신뢰 좌표로 선) | `_gated_kp` 를 후보 순회 **안에서** 유지 — crop 인지는 게이트 위에 얹는 필터일 뿐 완화가 아니다. 단위 테스트가 conf 게이트 거동 불변을 지킨다(`test_leg_line_pts_pure` 무수정 통과) |
| T-f5h-02 (표시 수리가 채점으로) | `git diff --name-only -- app/ backend/functions/ docs/` 빈 출력 + 동결 심볼 AST 대조 전건 동일 |
| T-f5h-03 (교체한 심볼 미원복) | `_LegSpy`/`_NoLegAngle` 둘 다 컨텍스트 매니저 `__exit__` 로 원복. 하네스는 quick 디렉터리 로컬 |
| T-f5h-04 (과다 렌더) | accept. 로컬 오프라인, 실행당 카드 110 × 3렌더, ~40초 |
| T-f5h-SC (패키지 설치) | **신규 설치 0** — numpy/PIL/yaml 전부 기존 의존성 |

---

## 산출물

- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — 함수 2개 + import 1줄
- `backend/tests/test_fault_zoom.py` — 계약 6행 신규 테스트 2개
- `sweep_leg_angle.py` — 10동작 스위프 (A/B 오라클 · crop 기하 스파이 · 해시 대조 · INV-D1)
- `sweep_out/{before,after}/` — 사다리 적용 실측 (각 110 카드 + summary.json)
- `sweep_out/{before-noladder,after-noladder}/` — 원본 좌표 대조군

> **커밋된 PNG는 대표 페어 6장뿐이다.** 4실행 × 90장 = 360장(72MB)은 재현 가능한 로컬
> 산출물이라 `sweep_out/.gitignore`로 제외했다. 판정 재료인 `summary.json` 4건은 전건
> 커밋돼 있어 위 표는 그것만으로 재확인된다. 전량 재생성 =
> `python3 sweep_leg_angle.py --out after --assert` (before는 수정 전 코드에서).
- `legacy_baseline.py` · `legacy_baseline_before.json` · `legacy_baseline.json` — 해시 게이트
- `pytest_baseline_before.txt` — HEAD 시점 FAILED/ERROR node ID 58건

## 다음

**§C-4 Pod** — 기준 12관절 18fps 표시 보고서 · crop/각도 베이크 전수 재생성 ·
어깨/팔꿈치 일러스트 생성 · **S10 실 doc 판정** → 일괄 OTA → belle 확인 ③.

---

## Self-Check: PASSED

- 산출물 12개 존재 확인(`test -f`) — SUMMARY · 하네스 3 · baseline 3 · summary.json 4 · PNG 페어
- 스위프 PNG 각 실행 90장 × 4실행 = 360장
- 코드 커밋 `f05bc98d` 존재 확인(`git log --oneline --all | grep`)
- 커밋 포함 파일 = `fault_zoom.py` · `test_fault_zoom.py` **둘뿐**, 삭제 파일 0
- 프로덕션 diff 이모지 스캔 0 (CLAUDE.md §7)
- l7t 디렉터리 tracked 파일 변경 0
- `.planning/` 산출물 스테이징 0 (docs 커밋은 오케스트레이터 담당)
