# quick-260802-gny — 배율 parity 이동 실측표

`parity_probe.py --sweep` 실측. 계산은 프로덕션 `fault_zoom_crop` 로그의
`user_side_px` / `ref_side_px` 를 `LogRecord.args` 로 읽은 값이고, 비는
`user_side_px / ref_side_px` 다. 밴드 `0.8~1.25` 는
`fault_zoom.py` 2813행 주석이 소유하는 기존 32-03 판정 밴드다 — **이 사이클은
읽기만 했고 넓히지 않았다.**

---

## belle 결정 필요

### 1. split 카드 배율 parity 가 밴드를 벗어난다 — 8 / 10 동작

합성 스위프 기준 `split_angle` 카드의 학생/기준 배율비가 0건 이탈(before) -> **8건 이탈(after)** 로 늘었다.

| motion | ratio before -> after | 밴드 |
|---|---|---|
| ref-climb | 0.952174 -> **1.091304** | 안 |
| ref-elbow-twist-sister | 0.952174 -> **1.243478** | 안 |
| ref-foxtop | 0.952174 -> **1.391304** | **밖** |
| ref-foxtop-split | 0.952174 -> **1.543478** | **밖** |
| ref-invert | 0.952174 -> **1.565217** | **밖** |
| ref-kip-up | 0.952174 -> **1.565217** | **밖** |
| ref-pdshape | 0.952174 -> **1.565217** | **밖** |
| ref-peter-pan | 0.952174 -> **1.565217** | **밖** |
| ref-power-spin | 0.952174 -> **1.565217** | **밖** |
| ref-sideway-spin | 0.952174 -> **1.565217** | **밖** |

**실 doc 에서도 이탈한다** (합성 사다리 탓이 아니다):

| 실 fixture | ratio before -> after | 밴드 |
|---|---|---|
| kipupFault1785373695 | 0.932099 -> **1.45679** | **밖** |
| powerspinFault1785373695 | 1.0 -> **1.0** | 안 |

power-spin 이 안 움직인 이유는 이 카드가 안전해서가 아니다 — 그 프레임의 왼무릎
(conf 0.388) · 왼발목(0.426) · 오른무릎(0.471)이 `_KP_CONF_MIN` 0.5 미만이라
**오른발목 하나만** valid 멤버가 됐고, 역립 자세라 그 점이 골반에서 30px 안쪽이었다.
관절 신뢰도가 정상인 프레임에서는 kip-up 쪽 값(1.46)이 실기기 기대치에 가깝다.

### 2. split 카드 6 건이 `min(h, w)` 상한에 클램프됐다

`user_side_px` 가 프레임 짧은 변에 닿았다 = 그 카드의 학생 패널 프레이밍이
**사실상 전신에 가깝다**. 부위 확대라는 성격이 그만큼 약해진다.

| motion | criterion | user_side_px | min(h,w) |
|---|---|---|---|
| ref-invert | split_angle | 360 | 360 |
| ref-kip-up | split_angle | 360 | 360 |
| ref-pdshape | split_angle | 360 | 360 |
| ref-peter-pan | split_angle | 360 | 360 |
| ref-power-spin | split_angle | 360 | 360 |
| ref-sideway-spin | split_angle | 360 | 360 |

### 3. 그 대가로 얻은 것 — 선이 정강이 대신 발목까지 간다 (7 / 10 동작)

배율을 내주고 얻은 쪽도 숫자로 적는다. crop 이 넓어지면서 사이각 선의 다리 끝점이
`knee` -> `ankle` 로 바뀐 동작이 7건이다 (`after/drawing_sweep_endpoints.txt`).

| motion | box 4멤버 -> 6멤버 | 끝점 4멤버 -> 6멤버 |
|---|---|---|
| ref-climb | 219 -> 251 | ankle -> ankle (불변) |
| ref-elbow-twist-sister | 219 -> 286 | ankle -> ankle (불변) |
| ref-foxtop | 219 -> 320 | ankle -> ankle (불변) |
| ref-foxtop-split | 219 -> 355 | knee -> **ankle** |
| ref-invert | 219 -> 360 | knee -> **ankle** |
| ref-kip-up | 219 -> 360 | knee -> **ankle** |
| ref-pdshape | 219 -> 360 | knee -> **ankle** |
| ref-peter-pan | 219 -> 360 | knee -> **ankle** |
| ref-power-spin | 219 -> 360 | knee -> **ankle** |
| ref-sideway-spin | 219 -> 360 | knee -> **ankle** |

**belle 이 저울질할 것:** 다리 전체가 보이는 선(정확) vs 학생 패널이 전신에 가까워진
프레이밍(배율 불일치). 두 값이 같은 방향으로 움직인다 — 선을 길게 만드는 것과
사진을 넓히는 것이 같은 원인(멤버 집합)에서 나온다.

### 4. 구조적 사실 — 기준 패널은 커질 수 없다

학생 `keypointReport` 는 12관절(발목 있음), 기준은 8관절(발목 없음)이다 —
실 fixture 4건 전건 확인. `_member_pts` 는 report 좌표를 직접 읽으므로
**학생 bbox 만 커지고 기준 bbox 는 그대로**다. 위 표에서 `ref_side_px` 가
전건 불변인 것이 그 귀결이다. 기준이 12관절이 되면(33-G §C-4) 비가 스스로
되돌아올 수 있다 — 그때 재측정할 것.

---

## 움직인 카드는 split_angle 뿐인가

**예.** 이동 카드 10 건, criterion = ['split_angle'].
나머지 100 카드는 `user_side_px`·`ref_side_px`·
`png_sha256`·멤버 수 4개 필드 전건 동일이다 (`--diff before after` 하드 게이트).

---

## 등재 10동작 x 카드 전건 (110행)

`png` 열: PNG sha256 이 움직였는가. `-` = 그 카드가 방출되지 않음
(기준 8관절이라 elbow 카드는 D-12 (2) 로 떨어진다 — before/after 동일).

| motion | criterion | n | user_side_px | ref_side_px | ratio | png |
|---|---|---|---|---|---|---|
| ref-climb | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-climb | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-climb | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-climb | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-climb | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-climb | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-climb | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-climb | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-climb | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-climb | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-climb | split_angle | 4 -> **6** | 219 -> **251** | 230 | 0.952174 -> **1.091304** | **변경** |
| ref-elbow-twist-sister | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-elbow-twist-sister | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-elbow-twist-sister | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-elbow-twist-sister | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-elbow-twist-sister | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-elbow-twist-sister | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-elbow-twist-sister | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-elbow-twist-sister | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-elbow-twist-sister | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-elbow-twist-sister | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-elbow-twist-sister | split_angle | 4 -> **6** | 219 -> **286** | 230 | 0.952174 -> **1.243478** | **변경** |
| ref-foxtop | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-foxtop | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-foxtop | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-foxtop | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-foxtop | split_angle | 4 -> **6** | 219 -> **320** | 230 | 0.952174 -> **1.391304** | **변경** |
| ref-foxtop-split | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-foxtop-split | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop-split | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop-split | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop-split | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-foxtop-split | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop-split | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop-split | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-foxtop-split | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-foxtop-split | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-foxtop-split | split_angle | 4 -> **6** | 219 -> **355** | 230 | 0.952174 -> **1.543478** | **변경** |
| ref-invert | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-invert | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-invert | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-invert | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-invert | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-invert | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-invert | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-invert | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-invert | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-invert | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-invert | split_angle | 4 -> **6** | 219 -> **360** | 230 | 0.952174 -> **1.565217** | **변경** |
| ref-kip-up | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-kip-up | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-kip-up | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-kip-up | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-kip-up | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-kip-up | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-kip-up | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-kip-up | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-kip-up | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-kip-up | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-kip-up | split_angle | 4 -> **6** | 219 -> **360** | 230 | 0.952174 -> **1.565217** | **변경** |
| ref-pdshape | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-pdshape | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-pdshape | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-pdshape | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-pdshape | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-pdshape | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-pdshape | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-pdshape | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-pdshape | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-pdshape | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-pdshape | split_angle | 4 -> **6** | 219 -> **360** | 230 | 0.952174 -> **1.565217** | **변경** |
| ref-peter-pan | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-peter-pan | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-peter-pan | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-peter-pan | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-peter-pan | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-peter-pan | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-peter-pan | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-peter-pan | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-peter-pan | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-peter-pan | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-peter-pan | split_angle | 4 -> **6** | 219 -> **360** | 230 | 0.952174 -> **1.565217** | **변경** |
| ref-power-spin | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-power-spin | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-power-spin | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-power-spin | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-power-spin | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-power-spin | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-power-spin | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-power-spin | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-power-spin | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-power-spin | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-power-spin | split_angle | 4 -> **6** | 219 -> **360** | 230 | 0.952174 -> **1.565217** | **변경** |
| ref-sideway-spin | angle_vs_reference__left_elbow | 1 | None | None | None | - |
| ref-sideway-spin | angle_vs_reference__left_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-sideway-spin | angle_vs_reference__left_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-sideway-spin | angle_vs_reference__left_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-sideway-spin | angle_vs_reference__right_elbow | 1 | None | None | None | - |
| ref-sideway-spin | angle_vs_reference__right_hip | 1 | 220 | 220 | 1.0 | 동일 |
| ref-sideway-spin | angle_vs_reference__right_knee | 1 | 220 | 220 | 1.0 | 동일 |
| ref-sideway-spin | angle_vs_reference__right_shoulder | 1 | 220 | 220 | 1.0 | 동일 |
| ref-sideway-spin | arm_extension | 4 | 245 | 230 | 1.065217 | 동일 |
| ref-sideway-spin | leg_extension | 4 | 219 | 230 | 0.952174 | 동일 |
| ref-sideway-spin | split_angle | 4 -> **6** | 219 -> **360** | 230 | 0.952174 -> **1.565217** | **변경** |

---

## 실 doc 4건 crop box (프레임 shape 가정 = {'h': 640, 'w': 360})

**절대 px 는 가정 의존이다** — 실 영상 해상도를 알 수 없어 합성 프레임을 썼다.
비(`ratio`)는 두 패널이 같은 shape 를 쓰는 한 shape 무관이라 그쪽이 더 강한 값이다.

| fixture | criterion | 멤버 수 | user box | ref box | ratio |
|---|---|---|---|---|---|
| elbowtwistsisterFault1785373695 | angle_vs_reference__left_elbow | 1 | [107, 313, 151] | None | None |
| elbowtwistsisterFault1785373695 | angle_vs_reference__left_shoulder | 1 | [81, 273, 151] | [113, 270, 151] | 1.0 |
| elbowtwistsisterFault1785373695 | angle_vs_reference__right_elbow | 1 | [107, 313, 151] | None | None |
| elbowtwistsisterFault1785373695 | angle_vs_reference__right_shoulder | 1 | [110, 270, 151] | [113, 270, 151] | 1.0 |
| kipupFault1785373695 | angle_vs_reference__left_shoulder | 1 | [149, 243, 151] | [156, 249, 151] | 1.0 |
| kipupFault1785373695 | split_angle | 4 -> **6** | [156, 353, 151] -> **[124, 338, 236]** | [155, 348, 162] | 0.932099 -> **1.45679** |
| pdshapeCorrect1785373695 | angle_vs_reference__right_knee | 1 | None | None | None |
| powerspinFault1785373695 | angle_vs_reference__left_shoulder | 1 | [120, 177, 151] | [152, 160, 151] | 1.0 |
| powerspinFault1785373695 | leg_extension | 4 | [78, 244, 151] | [90, 201, 151] | 1.0 |
| powerspinFault1785373695 | split_angle | 4 -> **6** | [78, 244, 151] -> **[78, 248, 151]** | [90, 201, 151] | 1.0 |
