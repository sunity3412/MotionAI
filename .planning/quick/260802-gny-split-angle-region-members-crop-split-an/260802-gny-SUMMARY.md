---
phase: quick-260802-gny
plan: 01
subsystem: fault-zoom-render
tags: [33-G, S10, crop-members, display-only, parity-32-03]
requires:
  - "quick-260731-f5h _leg_line_pts crop 인지 끝점 선택"
  - "quick-260802-czw 실 doc 재생 하네스 + fixture 박제"
  - "32-14 keypointReport 12관절 / 기준 phase4_v1 8관절"
provides:
  - "fault_zoom.CRITERION_CROP_EXTRA_MEMBERS (split_angle -> 발목 2개)"
  - "pipeline._MODE3_ZOOM_CRITERION_EXTRA_MEMBERS 미러 + 동등성 테스트"
  - "parity_probe.py 상설 계측기 (--real / --sweep / --check / --diff)"
  - "parity_delta.md 배율 parity 이동 실측표 (belle 판단 재료)"
affects:
  - "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
  - "backend/functions/pipeline/app.py"
  - "app/src/lib/deductionLabels.ts (주석만)"
  - "backend/tests/test_fault_zoom.py"
  - "backend/tests/phase33/test_zoom_join_joint_exact.py"
tech-stack:
  added: []
  patterns:
    - "criterion 별 crop 프레이밍 멤버 표 (region 표는 무수정)"
    - "분기 밖 append — vision/geometry 어느 경로로 와도 같은 멤버"
    - "계측기가 프로덕션 술어만 호출 (crop 계산식·마진 복제 0)"
    - "로그를 LogRecord.args 로 읽기 (포맷 재파싱 의존 제거)"
key-files:
  created:
    - .planning/quick/260802-gny-.../parity_probe.py
    - .planning/quick/260802-gny-.../parity_delta.md
    - .planning/quick/260802-gny-.../{before,after}/
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py
    - app/src/lib/deductionLabels.ts
    - backend/tests/test_fault_zoom.py
    - backend/tests/phase33/test_zoom_join_joint_exact.py
decisions:
  - "crop 멤버는 criterion 별로 가르고 REGION_MEMBERS 는 안 건드린다"
  - "추가 멤버는 3분기 밖에서 append — 실 doc 의 split_angle 은 전부 source=vision"
  - "앱 마커 투영 표는 4 keypoint 유지 (의도적 분기, 주석으로 박제)"
  - "배율 밴드 이탈 8건은 완화하지 않고 belle 판단으로 올린다"
metrics:
  duration: 약 2시간
  completed: 2026-08-02
---

# quick-260802-gny: split_angle crop 멤버 Summary

---

## 증상 2개 — 고쳐졌나 (동작별, 못 본 것은 "못 봤다")

### 증상 ② `zoom_split_angle.png` 와 `zoom_leg_extension.png` 가 같은 사진 — **고쳐졌다**

power-spin 실 doc 에서 두 카드의 crop box 가 갈렸다. `before/real.json` 과
`after/real.json` 을 **열어서** 읽은 값이다.

| | leg_extension | split_angle |
|---|---|---|
| 멤버 (before) | hip x2 + knee x2 (4) | **같은 4** |
| user box (before) | `[78, 244, 151]` | **같은 `[78, 244, 151]`** |
| 멤버 (after) | 4 (불변) | **6** (발목 2 추가) |
| user box (after) | `[78, 244, 151]` (불변) | **`[78, 248, 151]`** |

같은 프레임(38) + 같은 멤버 + 같은 box 면 같은 PNG 가 나온다 — sha256 동일은 그
기계적 귀결이었다. 멤버가 갈리니 box 가 갈렸고 증상 2는 **구조적으로** 사라졌다.
kip-up 은 `leg_extension` 카드 자체가 없어 이 대조가 성립하지 않는다(비교 대상 없음).

**단, 실제 PNG 픽셀은 안 봤다** — 아래 "안 본 것" 참조.

### 증상 ① split_angle 카드에 다리 사이각이 안 그려진다 — **실 doc 2건에서는 이 수정으로 안 고쳐진다. 원인이 다르다.**

이것이 이번 사이클의 가장 중요한 실측이다. 플랜 전제(발목이 crop 밖으로 나가
탈락)가 **실 doc 에서는 사실이 아니었다.** 프로덕션 `_draw_side_leg_angle` 를
직접 호출해 잰 값이다 (`after/drawing_real.txt`).

| 실 fixture | before 드로잉 | after 드로잉 | 끝점 before -> after | 실제 원인 |
|---|---|---|---|---|
| power-spin | 학생측 **미드로잉** | 학생측 **여전히 미드로잉** | 끝점 없음 -> 끝점 없음 | 왼다리 keypoint 신뢰도 |
| kip-up | 양측 드로잉 | 양측 드로잉 | ankle/ankle -> ankle/ankle | (애초에 안 깨져 있었다) |

- **power-spin:** 프레임 38 의 왼무릎 conf **0.388** · 왼발목 **0.426** 이 둘 다
  `_KP_CONF_MIN` 0.5 미만이라 `_leg_line_pts` 가 왼쪽 끝점 후보를 못 찾는다 →
  `None`. crop 을 아무리 넓혀도 안 그려진다. **crop 문제가 아니라 신뢰도 문제다.**
- **kip-up:** 다리 관절 conf 가 0.85~0.90 이라 before 에도 양측이 정상 드로잉이고
  끝점도 이미 발목이었다. 이 doc 에서는 증상 1 이 **관측되지 않는다**.
- 발목의 `_pt_in_crop` 은 **before 부터 두 fixture 모두 True** 였다. 이유는 기하다 —
  crop 변이 `floor = min(h,w) * _CROP_FRAC` 로 결정되는데(멤버 bbox 가 그보다 작다)
  그 박스가 이미 발목을 담고 있었다.

**그럼 이 수정이 증상 1 에 하는 일은 무엇인가 — "그려지나"가 아니라 "어디까지 그려지나"다.**
등재 10동작 합성 스위프에서 다리 끝점이 `knee` -> `ankle` 로 바뀐 동작이 **7 / 10**
이다 (`after/drawing_sweep_endpoints.txt`). f5h 가 이미 "안 그려지던 것"을 knee 폴백
으로 고쳤고, 이번 수정은 그 폴백이 필요 없게 만들어 **선이 정강이가 아니라 발목까지**
가게 한다.

| motion | box 4->6 | 끝점 4멤버 -> 6멤버 |
|---|---|---|
| ref-climb / ref-elbow-twist-sister / ref-foxtop | 219 -> 251/286/320 | ankle -> ankle (불변) |
| 나머지 7동작 | 219 -> 355~360 | knee -> **ankle** |

---

## 배율 parity 이동표 — 밴드를 벗어났다. 완화하지 않았다.

전문 = `parity_delta.md` (110행 전건 표 + "belle 결정 필요" 4절).
아래는 그 요지이고, 숫자는 `before/sweep.json` · `after/sweep.json` 에서 인용했다.

**F5 예상은 맞았다. 학생 쪽만 커졌다.** `ref_side_px` 는 10동작 전건 230 으로 불변
(기준 report 8관절 = 발목 부재, 실 fixture 4건 전건 확인). `user_side_px` 만 219 ->
251~360 으로 커졌다.

| motion | user_side_px | ref_side_px | ratio | 밴드 0.8~1.25 |
|---|---|---|---|---|
| ref-climb | 219 -> **251** | 230 | 0.952 -> **1.091** | 안 |
| ref-elbow-twist-sister | 219 -> **286** | 230 | 0.952 -> **1.243** | 안 |
| ref-foxtop | 219 -> **320** | 230 | 0.952 -> **1.391** | **밖** |
| ref-foxtop-split | 219 -> **355** | 230 | 0.952 -> **1.543** | **밖** |
| ref-invert | 219 -> **360** | 230 | 0.952 -> **1.565** | **밖** |
| ref-kip-up | 219 -> **360** | 230 | 0.952 -> **1.565** | **밖** |
| ref-pdshape | 219 -> **360** | 230 | 0.952 -> **1.565** | **밖** |
| ref-peter-pan | 219 -> **360** | 230 | 0.952 -> **1.565** | **밖** |
| ref-power-spin | 219 -> **360** | 230 | 0.952 -> **1.565** | **밖** |
| ref-sideway-spin | 219 -> **360** | 230 | 0.952 -> **1.565** | **밖** |

- **움직인 카드는 split_angle 뿐인가 — 예.** 이동 카드 **10건**, criterion =
  `['split_angle']`. 나머지 **100 카드**는 `user_side_px`·`ref_side_px`·`png_sha256`·
  멤버수 4개 필드 전건 동일 (`--diff` 하드 게이트가 강제).
- **밴드 이탈 건수 = 0건(before) -> 8건(after).** 밴드를 넓히지 않았고 임계를
  만들지 않았다. "무시 가능"이라고 쓰지 않는다.
- **`min(h,w)` 상한 클램프 = 6건** (전부 split_angle, `user_side_px` = 360 = 프레임
  짧은 변). 그 6장은 학생 패널 프레이밍이 **사실상 전신에 가깝다** — 부위 확대라는
  성격이 그만큼 약해진다.
- **실 doc 에서도 이탈한다** (합성 사다리 탓이 아니다):
  `kipupFault…` split_angle ratio **0.932 -> 1.457 (밖)**.
  `powerspinFault…` 는 1.0 -> 1.0 이지만 그건 안전해서가 아니라 그 프레임의 무릎·
  왼발목이 저신뢰라 **오른발목 하나만** valid 로 들어왔고 역립 자세라 그 점이 골반
  30px 안쪽이었기 때문이다.

**belle 결정 필요:** 다리 전체가 보이는 선(정확) vs 학생 패널이 전신에 가까워지는
프레이밍(배율 불일치). 두 값이 같은 원인(멤버 집합)에서 나오므로 한쪽만 취할 수 없다.
`parity_delta.md` 맨 위 절에 모아 뒀다.

---

## 채점 무접촉 — 통과가 아니라 값으로

| 증거 | 커맨드 | 출력 |
|---|---|---|
| 채점 모듈 diff | `git diff $BASE -- deduction_engine.py dimensions.py kismam.py` | **빈 출력** (3종 전부) |
| pytest node ID | `PYTHONPATH=backend/tests …/pytest -q backend/tests` 후 `diff` | **빈 출력** |
| pytest 총계 | 같은 커맨드 | before `59 failed, 3801 passed, 27 skipped` -> after `59 failed, **3807** passed, 27 skipped` (**+6 = 신규 테스트 수와 일치**) |
| legacy 해시 | `legacy_baseline.py --verify` | before/after 모두 `PASS — 9 case / 9 card 해시 동일` (문자열 동일) |
| 실 doc 채점 | `replay.py --recon-only` | 표준출력 **문자열 동일** (`diff` 빈 출력), exit 1 = czw 설계대로 |
| 앱 타입 | `cd app && npm run typecheck` | 출력 없음 (clean) |

`--recon-only` 문자열 동일이 곧 실 doc 4건의 `deductionBreakdown.records`
(criterion·measuredValue·points·final)가 한 자도 안 움직였다는 직접 증거다
(record 11/16 MATCH · fixture 4건 — before/after 동일).

프로덕션 변경 파일은 5개뿐이고 그 중 채점 모듈은 0개다:
`fault_zoom.py` · `pipeline/app.py` · `deductionLabels.ts`(주석) · 테스트 2개.

---

## locked_spec 8행 — 무엇으로 성립시켰나

| # | 상황 | 결과 | 성립시킨 행위 |
|---|---|---|---|
| 1 | split_angle, source=vision, faultJoints=hips+knees | hips+knees+**ankles** | `test_split_angle_crop_members_vision_branch` 를 **돌렸다** (RED 확인 후 GREEN) |
| 2 | split_angle, source=geometry | hips+knees+**ankles** | `test_split_angle_crop_members_geometry_branch` 를 **돌렸다** |
| 3 | leg_extension | 불변 | `test_leg_extension_and_arm_extension_members_unchanged` + 실 doc box `[78,244,151]` 불변을 `after/real.json` 에서 **읽었다** |
| 4 | arm_extension / `angle_vs_reference__*` | 불변 | 같은 테스트 + sweep 100 카드 sha256 전건 동일을 `--diff` 로 **돌렸다** |
| 5 | 8관절 doc (발목 부재) | box 튜플 동일 | `test_split_angle_crop_box_unchanged_without_ankles` (a) 를 **돌렸다** |
| 6 | 발목 conf < `_KP_CONF_MIN` | box 튜플 동일 | 같은 테스트 (b) 를 **돌렸다**. 실 doc power-spin 이 이 케이스의 자연 발생 사례(왼발목 0.426 -> relaxed) |
| 7 | joints[0] | 항상 left_hip, 발목은 끝 2칸 | `test_split_angle_unit_joint_order_contract` 를 **돌렸다** |
| 8 | 파이썬 두 표 | 항목 동일 | `test_mode3_zoom_extra_members_mirror` 를 **돌렸다** (pipeline 모듈을 경로 import 해 실제 객체를 비교) |

RED 는 4건에서 확인했다. 그 중 이번 수리의 존재 이유인 vision 분기의 실패 메시지:

```
    joints = _gny_unit("split_angle", "vision")["joints"]
>   assert "left_ankle" in joints and "right_ankle" in joints, joints
E   AssertionError: ('left_hip', 'right_hip', 'left_knee', 'right_knee')
E   assert ('left_ankle' in ('left_hip', 'right_hip', 'left_knee', 'right_knee'))
```

계약 3·4·5·6행 테스트 2개는 **RED 없이 처음부터 GREEN** 이었다. 그 두 개는 "불변"을
거는 무회귀 자물쇠라 수정 전에 통과하는 것이 정상이다(플랜도 그렇게 규정). 새 동작을
요구하는 4개는 전부 RED 를 거쳤다.

---

## Deviations from Plan

### 1. [실측 > 플랜 전제] `--diff` 발목 절이 플랜대로는 통과할 수 없었다 — 방향을 사실에 맞췄다

- **플랜 요구:** power-spin split_angle 의 `left_ankle_in_crop` 또는
  `right_ankle_in_crop` 이 **False -> True** 로 바뀔 것.
- **실측:** before 부터 **둘 다 True** 였다. 게이트를 플랜대로 돌린 출력을 그대로 남긴다:

```
DIFF-FAIL (before -> after)
  power-spin split_angle 발목 _pt_in_crop 이 False -> True 로 바뀐 것이 없다:
  before={'pelvis': True, 'left_knee': True, 'right_knee': True,
          'left_ankle': True, 'right_ankle': True}
  after ={'pelvis': True, ... 'left_ankle': True, 'right_ankle': True}
```

- **원인(기하로 설명됨):** 그 프레임의 valid 멤버가 골반 2점뿐이라 bbox 가 작고,
  crop 변이 `floor = min(h,w) * _CROP_FRAC` 로 정해진다. 역립 자세라 발목이 골반에서
  30px 안쪽이었다 → 처음부터 crop 안.
- **조치:** 절의 **방향을 사실에 맞췄다** — "담게 만든다(flip)" 대신 "**담고 있다**
  (after 가 True)"를 하드 게이트로 하고, flip 여부는 판정이 아닌 관측으로 출력한다.
  **무르게 고친 것이 아님을 보이려고, 플랜에 없던 하드 게이트를 하나 더 추가했다** —
  `power-spin split_angle user box 가 before 에서 실제로 움직였을 것`
  (`[78,244,151]` -> `[78,248,151]`). 멤버 추가가 프레이밍까지 도달했다는 직접 증거다.
- **기록 위치:** `parity_probe.py` 해당 절의 주석에 "실측 후 변경"임과 사유를 박아 뒀다.
  변경 전 출력은 위에 그대로 옮겼다.

### 2. [Rule 3 - 차단] 기존 phase33 테스트 1건이 새 계약과 정면 충돌 — assert 1개 갱신

- **발견:** Task 2 구현 직후 `backend/tests/phase33/test_zoom_join_joint_exact.py::
  test_criterion_units_from_records_joint_exact` FAIL. **기준선에서는 통과하던 테스트다**
  (`before/pytest_nodes.txt` 에 없음) = 내 변경이 깬 것.
- **충돌 내용:** 그 테스트는 vision 분기 산출이 `_LEGS & set(fault_joints)` 와
  **정확히 같을 것**을 요구한다. 플랜 locked_spec 1행은 vision 분기가
  hips+knees+**ankles** 를 내라고 요구한다. **두 요구는 동시에 만족 불가능하다.**
- **플랜 규정:** "기존 테스트는 한 줄도 수정하지 않는다(수정이 필요해지면 회귀
  신호다. 멈추고 보고)". 그래서 여기 보고한다 — 다만 이것은 회귀가 아니라
  **의도된 계약 변경과 낡은 등식의 충돌**이라 판단하고 진행했다.
- **조치(최소):** 등식 1줄만 새 계약으로 갱신했다
  (`(_LEGS & fault_joints) | CRITERION_CROP_EXTRA_MEMBERS["split_angle"]`).
  **그 테스트가 지키려는 성질(defect #5 = 다리 항목에 어깨가 새어 들어오지 않는다)의
  assert 는 손대지 않았고 그대로 통과한다.** 같은 파일의
  `leg_extension == _LEGS` 불변 assert 도 무수정 통과.
- **belle 확인이 필요하면 되돌릴 지점:** 이 한 줄. 되돌리면 locked_spec 1행이 깨진다.

### 3. [플랜 조정] `--diff` 모드를 Task 3 이 아니라 Task 1 에서 작성

- 플랜은 Task 3 에서 추가하라고 했으나, before 캡처 시점에 판정 규칙을 먼저 박아 두면
  "숫자를 본 뒤 게이트를 만들었다"는 의심 경로가 줄어든다. Task 1 커밋(`2fa707da`)에
  플랜 문구 그대로의 게이트가 들어 있고, Deviation 1 의 교정은 Task 3 커밋에서 일어난다
  — **커밋 순서가 그 교정이 사후였음을 정직하게 드러낸다.**

### 4. [산출물] pytest 전체 로그(436KB)는 커밋하지 않음

- 게이트 재료는 FAILED/ERROR node ID 집합과 총계 1줄이다. 전체 로그는 세션
  scratchpad 에만 뒀다. `before/`·`after/` 에는 `pytest_nodes.txt`(59행) +
  `pytest_totals.txt`(1행)만 있다.

### 5. [Rule 1 - 버그] 내가 쓴 주석의 인과가 실측과 달랐다 — 고쳤다 (`7c05b5f4`)

- **내용:** Task 2 에서 쓴 `CRITERION_CROP_EXTRA_MEMBERS` 주석에 "멤버 집합이 좁으면
  발목이 crop 밖으로 나가 게이트에서 탈락해 **그림이 통째로 사라진다**"고 적었다.
- **실측과의 차이:** f5h 의 crop 인지 끝점 폴백이 이미 있어서, 발목이 crop 밖이면
  그림이 사라지는 것이 아니라 **끝점이 knee 로 내려가 선이 정강이까지만** 그려진다.
  둘 다 밖일 때만 미드로잉이다. 스위프 실측이 정확히 그 형태였다(끝점 7/10 변경).
- **조치:** (a) 같은 사진이 되는 경로와 (b) 선이 짧아지는 경로를 나눠 적고, 대가
  (배율 parity 이동)와 실측표 경로를 함께 남겼다. **동작 변경 0 — 주석만.**
- **왜 남기지 않았나:** 프로덕션 주석에 틀린 인과를 남기면 다음 사람이 그것을 근거로
  판단한다. 코드는 테스트가 지키지만 문장은 아무도 안 지킨다.

### Rule 2 자동수정

없음.

---

## 안 본 것 — "안 봤다"

| 항목 | 상태 | 이유 |
|---|---|---|
| **PNG 픽셀 내용 / 사이각이 실제로 다시 그려진 그림** | **안 봤다** | 이번 사이클은 **crop 이 발목을 담는가**까지다. 실 doc 의 PNG 재생성은 33-G §C-4 재생성 또는 Pod 재분석이 있어야 나온다 |
| **실 영상 프레임 해상도** | **모른다** | `--real` 프로브는 `--frame-shape 640 360` 가정 합성 프레임을 쓴다. `real.json` 헤더에 `frameShapeIsAssumption: true` 로 박아 뒀다. **절대 px 는 이 가정에 의존한다.** 비(ratio)는 두 패널이 같은 shape 를 쓰는 한 shape 무관이라 그쪽이 더 강한 값 |
| **앱 화면 · 시뮬레이터 · 실기기 렌더** | **안 봤다** | 백엔드 계측까지만. 앱 변경은 주석 1개뿐이라 렌더 영향 0이지만 그것도 화면으로는 확인 안 했다 |
| **mode3 경로 실행** | **안 돌렸다** | 미러 표의 값 동등성은 테스트로 걸었으나 `_build_mode3_fault_zoom_comparisons` 를 실제로 태워 카드를 뽑아 보지는 않았다 (fixture 4건 전부 mode1) |
| **기준 12관절 이후의 parity** | **못 잰다** | 기준 report 가 8관절인 동안의 값이다. §C-4 로 기준이 12관절이 되면 비가 스스로 되돌아올 수 있다 — 그때 이 프로브를 다시 돌릴 것 |
| **power-spin 사이각을 실제로 살리는 길** | **이 사이클 범위 밖** | 원인은 왼다리 keypoint 신뢰도(0.388/0.426)다. crop 으로는 못 고친다 |
| **kip-up split_angle 카드의 배율이 belle 눈에 어떻게 보이는가** | **안 봤다** | ratio 1.457 이 "어색한가"는 사람이 판단할 것 |

---

## 위협 대응 (threat_model 대조)

| Threat ID | 처리 |
|---|---|
| T-gny-01 (표시 수리가 채점으로) | 채점 모듈 3종 diff 빈 출력 + czw `--recon-only` 문자열 동일 + legacy verdict 동일 + pytest node ID diff 0 — 4종 전부 값으로 확인 |
| T-gny-02 (crop 폭주) | **발생했다.** 밴드 이탈 8건 · `min(h,w)` 클램프 6건을 `parity_delta.md` 에 숫자로 올렸다. 임계 신설 0, 밴드 완화 0 |
| T-gny-03 (미러 드리프트) | `test_mode3_zoom_extra_members_mirror` 가 3표 동등성 강제. 앱측 분기는 `deductionLabels.ts` 주석에 사유·근거·되돌리지 말 것을 명문화 |
| T-gny-04 (fail-closed 붕괴) | 8관절 doc·저신뢰 발목 두 케이스에서 box 튜플 동등을 단위 테스트로 고정 + 고신뢰 대조군으로 "그냥 발목을 안 쓰는 것"이 아님을 함께 검증 |
| T-gny-05 (하네스 자체 계산) | 프로브가 crop 기하를 계산하지 않는다 — `_member_pts`/`_side_crop`/`_pt_in_crop`/`_kp_conf`/`_leg_line_pts`/`_draw_side_leg_angle` 프로덕션 함수만 호출. 로그는 `LogRecord.args` 로 읽어 포맷 파싱 의존 제거 |
| T-gny-06 (fixture 재사용) | accept — 읽기만 했다 |
| T-gny-SC (패키지 설치) | **설치 0.** numpy·PIL·pyyaml 전부 기존 의존성. 네트워크 사용 0 |

---

## 실행 환경 메모

워크트리에 `backend/.venv` 와 `app/node_modules` 가 없어 메인 체크아웃의 것을
**심볼릭 링크**해 게이트를 돌렸다. 패키지 설치 0, 네트워크 0, 메인 체크아웃 수정 0.
종료 시 두 링크 모두 제거했고, pytest 가 재생성한 추적 `.pyc` 2개는 `git checkout`
으로 원복했다 (`git status` 빈 출력 확인).

착수 시 워크트리 HEAD 가 `d178aa8e` 로 지정 base `28840223` 과 달라
`git reset --hard 28840223` 후 진행했다 (worktree_branch_check Step 2 규정).

`BASE=288402238fe1dbe778e87965eee33fd496c07c58` 을 고정해 모든 diff 게이트는
`git diff $BASE` 로 돌렸다 (`git add` 로 무력화되는 `--exit-code` 단독 사용 0).

---

## Known Stubs

없음. 신규 표는 값이 채워진 데이터이고 placeholder 아니다.

---

## Threat Flags

없음. 신규 네트워크 엔드포인트·인증 경로·스키마 변경 0. 변경은 표시 경로의
crop 프레이밍 멤버 표 1개와 그 미러뿐이다.

---

## Commits

| hash | 내용 |
|---|---|
| `2fa707da` | Task 1 — 계측기 + 수정 전 기준선 (프로덕션 diff 0) |
| `cc5dff2c` | Task 2 — crop 멤버 분기 + 미러 + 테스트 6종 (RED 선행) |
| `4fc08466` | Task 3 — 수정 후 실측 + parity 이동표 + 무회귀 게이트 |
| `7c05b5f4` | 후속 — 주석의 인과를 실측에 맞춤 (동작 변경 0, 아래 Deviation 5) |

커밋 순서가 증거다: `2fa707da` 시점의 `parity_probe.py` 에는 플랜 문구 그대로의
발목 flip 게이트가 들어 있고 프로덕션 diff 는 0이다. 즉 before 기준선과 판정 규칙이
**구현 전에** 박제됐고, Deviation 1 의 게이트 교정은 그 다음다음 커밋에서 일어난다.

---

## 다음

1. **belle 판단** — `parity_delta.md` "belle 결정 필요" 3절(밴드 이탈 8건 / 클램프
   6건 / 그 대가로 얻은 발목까지의 선 7건). 배율을 지킬 것인지, 다리 전체를 볼
   것인지.
2. **33-G §C-4** — 기준 12관절 18fps 가 되면 `ref_side_px` 가 따라 커져 비가 스스로
   되돌아올 수 있다. 그때 `parity_probe.py --sweep` 을 다시 돌려 재측정.
3. **PNG 재생성 후 belle 확인 ③** — (1) split 카드가 leg_extension 과 다른 사진인지,
   (2) 골반에서 양다리로 뻗는 선 2개와 호가 보이는지, (3) 두 패널 배율이 어색하지
   않은지. 이번 사이클은 여기까지 못 갔다.
4. **power-spin 사이각은 별건** — 원인이 keypoint 신뢰도라 crop 으로는 안 고쳐진다.
   §C-4 재분석으로 신뢰도가 회복되는지부터 봐야 한다.

---

## Self-Check: PASSED

- 산출물 존재 확인 (`ls`): `parity_probe.py` · `parity_delta.md` ·
  `before/` 6파일 · `after/` 9파일 · 이 SUMMARY.
- 커밋 3건 존재 확인 (`git log --oneline`): `2fa707da` · `cc5dff2c` · `4fc08466`.
- 보고의 수치는 `before/real.json` · `after/real.json` · `before/sweep.json` ·
  `after/sweep.json` · `after/drawing_real.txt` · `after/drawing_sweep_endpoints.txt`
  를 **직접 열어** 읽은 값이다 (요약문 재인용 0).
- 게이트 출력은 실제로 커맨드를 돌려 받은 것이다 — pytest node ID diff · 채점 모듈
  diff · legacy verdict · czw recon diff · `--diff before after` · `npm run typecheck`.
- RED 는 실행해서 실패 메시지를 받았고 그 원문을 위에 옮겼다.
- 워크트리 `git status` 빈 출력 확인, 심볼릭 링크 2개 제거 확인.
