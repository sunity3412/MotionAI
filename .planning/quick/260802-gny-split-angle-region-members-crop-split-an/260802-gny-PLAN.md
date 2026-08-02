---
phase: quick-260802-gny
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/functions/pipeline/app.py
  - app/src/lib/deductionLabels.ts
  - backend/tests/test_fault_zoom.py
  - .planning/quick/260802-gny-split-angle-region-members-crop-split-an/parity_probe.py
  - .planning/quick/260802-gny-split-angle-region-members-crop-split-an/before/
  - .planning/quick/260802-gny-split-angle-region-members-crop-split-an/after/
  - .planning/quick/260802-gny-split-angle-region-members-crop-split-an/parity_delta.md
  - .planning/quick/260802-gny-split-angle-region-members-crop-split-an/260802-gny-SUMMARY.md
autonomous: true
requirements: [S10, byte-identical-png, parity-32-03]

must_haves:
  truths:
    - "실 doc(power-spin)에서 split_angle 카드의 crop 멤버가 leg_extension 과 달라진다 — 저장 record·저장 faultJoints 로 프로덕션 함수를 돌려 4관절 → 6관절 확인"
    - "split_angle crop 이 학생 발목을 담는다 — 프로덕션 _pt_in_crop 이 그 카드 box 에서 ankle 에 True 를 준다"
    - "leg_extension·arm_extension·angle_vs_reference__* 카드의 crop box(left/top/side)와 PNG 해시가 1도 안 움직인다"
    - "8관절 doc(발목 부재)·저신뢰 발목(conf < _KP_CONF_MIN)에서는 crop box 가 수정 전과 완전히 같다 — fail-closed 보존"
    - "채점 산출이 불변 — 채점 모듈 diff 0, 실 fixture 4건 RECON 산출 문자열 동일, legacy_baseline verdict 불변"
    - "배율 parity(user_side_px / ref_side_px)의 이동분이 등재 10동작 전건 표로 기록된다 — 안 움직였다면 숫자로, 움직였으면 움직인 카드를 전부 적는다"
    - "파이썬 미러 2표(fault_zoom / pipeline)의 동등성이 단위 테스트로 강제된다"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "CRITERION_CROP_EXTRA_MEMBERS + criterion_units_from_records 분기-무관 적용"
      contains: "CRITERION_CROP_EXTRA_MEMBERS"
    - path: "backend/functions/pipeline/app.py"
      provides: "_MODE3_ZOOM_CRITERION_EXTRA_MEMBERS 미러 + mode3 unit joints 배선"
      contains: "_MODE3_ZOOM_CRITERION_EXTRA_MEMBERS"
    - path: "app/src/lib/deductionLabels.ts"
      provides: "crop 멤버 ↔ 마커 투영 의도적 분기 기록 (동작 무변경, 주석 전용)"
      contains: "quick-260802-gny"
    - path: "backend/tests/test_fault_zoom.py"
      provides: "vision/geometry 양분기 커버 + 미러 동등성 + fail-closed 무회귀 테스트"
    - path: ".planning/quick/260802-gny-split-angle-region-members-crop-split-an/parity_probe.py"
      provides: "실 doc 4건 crop 기하 계측 + 등재 10동작 parity 계측 + before/after diff 게이트"
    - path: ".planning/quick/260802-gny-split-angle-region-members-crop-split-an/parity_delta.md"
      provides: "배율 parity 이동 실측표 (belle 판단 재료)"
  key_links:
    - from: "criterion_units_from_records"
      to: "CRITERION_CROP_EXTRA_MEMBERS"
      via: "분기(vision/geometry) 뒤 공통 append — vision 분기 누락 시 실기기 증상 잔존"
      pattern: "CRITERION_CROP_EXTRA_MEMBERS.get"
    - from: "_build_mode3_fault_zoom_comparisons"
      to: "_MODE3_ZOOM_CRITERION_EXTRA_MEMBERS"
      via: "crit_units joints 조립"
      pattern: "_MODE3_ZOOM_CRITERION_EXTRA_MEMBERS.get"
    - from: "backend/tests/test_fault_zoom.py"
      to: "두 파이썬 표"
      via: "동등성 assert (드리프트 차단)"
      pattern: "_MODE3_ZOOM_CRITERION_EXTRA_MEMBERS"
---

<objective>
split_angle 카드의 **crop 멤버 집합**이 그 카드가 그리는 점 집합보다 좁아서 생긴
두 증상을 한 번에 없앤다.

- 증상 1: split_angle 카드에 다리 사이각(골반에서 양다리로 뻗는 선 2개 + 호)이
  안 그려진다.
- 증상 2: `zoom_split_angle.png` 와 `zoom_leg_extension.png` 가 sha256 동일이다.

Purpose: 두 증상은 원인이 하나다. split_angle 의 crop 멤버가 leg_extension 과
**완전히 같은 4관절**(hips+knees)이라 (a) 같은 프레임에서 같은 crop 이 나오고
(=증상 2), (b) 사이각 드로잉 점인 발목이 그 crop 밖으로 나가 `_pt_in_crop`
3점 게이트에서 탈락한다(=증상 1).

Output: crop 멤버를 criterion 별로 가르는 표 1개(백엔드 2 미러) + 단위 테스트 +
배율 parity 이동 실측표.

**표시 전용, 채점 무접촉.** crop 은 사진 프레이밍일 뿐 점수 경로가 아니다.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

@backend/shared/python/sunity_shared/analysis/fault_zoom.py
@backend/functions/pipeline/app.py
@app/src/lib/deductionLabels.ts
@backend/tests/test_fault_zoom.py
@.planning/quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/260731-f5h-SUMMARY.md
@.planning/quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/sweep_leg_angle.py
@.planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/260802-czw-SUMMARY.md
@backend/evals/realfixture/replay.py
</context>

<established_facts>
플래너가 소스와 실 fixture 를 직접 열어 확인했다. 재조사하지 말고 전제로 쓸 것.
근거를 다시 보고 싶으면 아래 줄 번호를 직접 열어라.

**(F1) 오케스트레이터 가설은 절반만 맞다 — 그대로 구현하면 실기기 증상이 남는다.**
`criterion_units_from_records`(fault_zoom.py 147행)의 분기는 3갈래다.
`REGION_MEMBERS`(139행)는 **(4) 그 외(geometry)** 분기(215행)에서만 읽힌다.
그런데 저장된 실 doc 의 split_angle record 는 전부 `source='vision'` 이라
**(3) vision** 분기(202~210행)로 간다. 그 분기의 산출은
`faultJoints 교집합 _REGION_JOINTS[region]` 이고, faultJoints 는 vision veto 의
8-keypoint 이름공간이라 **발목을 원리적으로 담을 수 없다**.
따라서 REGION_MEMBERS 만 고치거나 (4) 분기에만 표를 붙이면 power-spin 과 kip-up 은
그대로 깨진 채 남는다. **추가 멤버는 분기와 무관하게 붙여야 한다.**

실 fixture 실측 (`backend/evals/realfixture/fixtures/*.json`):

| fixture | split_angle record | faultJoints |
|---|---|---|
| powerspinFault... | `source=vision`, `points=-12` | shoulders + hips + knees |
| kipupFault... | `source=vision`, `points=-20` | knees + hips + shoulders + right_hand |

**(F2) 증상 2의 원인이 실 doc 에 그대로 찍혀 있다.**
`powerspinFault...json` 의 저장 `faultZoomComparisons` 두 항목:

| criterion | userFrameIdx | refFrameIdx | region | joint | deficitDeg |
|---|---|---|---|---|---|
| leg_extension | 38 | 36 | legs | left_hip | 30 |
| split_angle | 38 | 36 | legs | left_hip | 30 |

같은 프레임 + 같은 멤버 집합이면 같은 crop 이 나오고 같은 PNG 가 나온다.
sha256 동일은 그 기계적 귀결이다. 멤버가 갈리면 crop 이 갈리고 증상 2는
**구조적으로** 사라진다.

**(F3) split_angle 은 33-G S9 정중앙 220px 경로에 들어가지 않는다.**
`_criterion_vertex_joint`(1198행)는 `angle_vs_reference__` 계열에만 꼭짓점을 준다.
따라서 split_angle 은 `u_vertex=r_vertex=None`(2757행) → `shared_side=None` →
`_side_crop`(1338행)의 **3단 강하 = 멤버 bbox 프레이밍**(`_box_for`, 1392행)을 탄다.
crop 크기의 단일 결정자가 **멤버 집합**이라는 뜻이다. 2749~2756행 주석이
"split 카드에 220px 를 씌우지 말라"고 못 박아 뒀으니 정중앙 경로 확대는 금지다.

**(F4) 발목을 뒤에 append 하면 표시 스칼라가 전부 불변이다.**
- `unit.joint = joints[0]`(2524행) → left_hip 유지.
- `_anchor_xy`(1141행) 기본값 `valid[0][1]` → 첫 valid 멤버 유지.
- `deficitDeg = max(member_deltas)`(2724행)는 joint_deltas 에서 오고,
  그 표(pipeline `_KISMAM_TO_KEYPOINT`, 3050행)에 **발목 키가 없다** →
  deficit 불변(F2 표의 30 그대로).
- `ARROW_JOINT_MAP`(1861행)에 발목 키 없음 → 화살표 증가 0.
- `item["kind"]` 는 `unit.joint` 로 조회 → 불변.

**(F5) 배율 parity 는 움직일 가능성이 높다. 이것이 이번 실측의 본론이다.**
학생 keypointReport = 12관절(발목 있음), 기준 = 8관절(발목 없음) — 실 fixture 4건
전건 확인했다. `_member_pts`(1114행)는 report 좌표를 직접 읽으므로 **학생 bbox 만
커지고 기준 bbox 는 그대로**다. `fault_zoom_crop` 로그(2823행)가 방출하는
`user_side_px` 대 `ref_side_px` 비가 움직일 수 있고, 32-03 판정 밴드는 0.8~1.25 다
(2813행 주석). **밴드를 넓히거나 임계를 고치는 것은 금지.** 움직이면 표에 적고
belle 판단으로 올린다.

**(F6) f5h 하네스는 재사용 가능하나 unit 조립을 그대로 쓰면 안 된다.**
`sweep_leg_angle.py` 는 이미 `_Capture` 로 `fault_zoom_crop` 로그를 잡아
`user_side_px`/`ref_side_px` 를 summary.json 에 적는다(455~465행). 실물
360x640 프레임을 쓰고 등재 10동작을 criteria yaml glob 에서 파생한다.
**단, `_units_for`(170행)가 `fz.REGION_MEMBERS` 를 직접 읽어 unit 을 만든다** —
그 경로로는 이번 수정이 실행되지 않는다. 이번 프로브는 그 모듈의 **fixture 와
헬퍼만** 빌려 쓰고 unit 은 프로덕션 `criterion_units_from_records` 로 만든다.

**(F7) czw 재생 하네스의 프레임은 8x8 이라 crop 기하 계측에 못 쓴다.**
`replay.py` `_synthetic_frames`(604행)가 `np.zeros((n, 8, 8, 3))` 이라
`_crop_box` 가 side 를 8 로 클램프한다. czw 하네스는 **채점·record 무회귀
증거**로만 쓰고(그 용도로는 유효), crop 기하는 이번 프로브가 직접 잰다.
</established_facts>

<locked_spec>
수정 후 아래 8행이 전부 성립해야 한다. 하나라도 못 지키면 완료가 아니다.

| # | 상황 | 기대 |
|---|---|---|
| 1 | split_angle, `source='vision'`, faultJoints 가 hips+knees | joints = hips+knees+**ankles** |
| 2 | split_angle, `source='geometry'` (mode3 seed) | joints = hips+knees+**ankles** |
| 3 | leg_extension (어느 분기든) | joints = hips+knees, **불변** |
| 4 | arm_extension / `angle_vs_reference__` 계열 | **불변** |
| 5 | 8관절 doc (발목 좌표 부재) | `_side_crop` box 가 수정 전과 **동일 값** |
| 6 | 발목 conf < `_KP_CONF_MIN` | 발목이 relaxed 로 분류 → valid box **동일 값** |
| 7 | joints[0] | 항상 left_hip (append 순서 계약) |
| 8 | 파이썬 두 표 | 항목 **동일** (테스트가 강제) |
</locked_spec>

<tasks>

<task type="auto">
  <name>Task 1: 계측기 작성 + 수정 전 기준선 캡처 (프로덕션 무접촉)</name>
  <files>
    .planning/quick/260802-gny-split-angle-region-members-crop-split-an/parity_probe.py
    .planning/quick/260802-gny-split-angle-region-members-crop-split-an/before/
  </files>
  <action>
착수 즉시 `BASE=$(git rev-parse HEAD)` 를 기록한다. 이 태스크에서는 프로덕션 파일을
한 줄도 건드리지 않는다. 산출은 전부 quick 디렉터리 안에 둔다.

**parity_probe.py — 모드 3개. 계산식 복제 0, 프로덕션 함수만 호출한다.**

(a) `--real --out {label}` : 실 doc 4건 계측.
`backend/evals/realfixture/fixtures/*.json` 과 `fixtures/reference/*.json` 을 읽는다
(리포에 박제된 JSON — Firestore·네트워크·GPU 접근 0). fixture 마다:
  - **unit 조립은 프로덕션이 한다.** `fault_zoom.criterion_units_from_records(
    저장 records, 저장 visionVeto.faultJoints, pipeline._KISMAM_TO_KEYPOINT)`.
    저장 record 를 그대로 쓰는 것이 핵심이다. 그 안에 split_angle 이 실제로
    들어 있고(F1 표), 이 함수는 record 의 수치를 읽지 않고 criterion 과 source
    로만 멤버를 정하므로 **채점 재현과 무관한 순수 표시 경로**다.
  - 카드가 실제로 쓴 프레임은 저장 `result.faultZoomComparisons[]` 에서 그
    criterion 항목의 `userFrameIdx` / `refFrameIdx` 를 그대로 가져온다(추정 0).
    그 criterion 의 저장 카드가 없으면 그 행은 `storedCard: null` 로 남기고
    프레임 값을 같은 fixture 의 다른 카드에서 빌려 오지 말 것 — 비워 둔다.
  - crop 기하 = `fault_zoom._member_pts(report, frame_idx, unit.members)` →
    `fault_zoom._side_crop(frame, [xy for _n, xy in valid], relaxed,
    anchor=..., center=None, side_override=None)` 를 직접 호출해 반환 4번째
    원소 `box=(left, top, side)` 를 기록한다.
  - frame 은 `np.zeros((H, W, 3), uint8)` 합성. **H/W 는 실 영상 해상도를 알
    수 없으므로 가정값**이며 `--frame-shape H W`(기본 640 360)로 노출하고 산출
    JSON 헤더에 그 값을 박아 둔다. 가정 의존을 줄이려고 **정규화 bbox extent**
    (valid 멤버 좌표의 x 폭 / y 폭)와 **비**(`user_side / ref_side`)를 함께
    적는다 — 비는 두 패널이 같은 shape 를 쓰는 한 shape 무관이다. 이 한계를
    파일 헤더 주석에 명시할 것.
  - 발목 포함 여부는 프로덕션 술어로만 판정한다.
    `fault_zoom._pt_in_crop(xy, left, top, side, w, h)` 를 그 카드 box 로 호출해
    pelvis 중점 / 좌우 knee / 좌우 ankle 각각 기록. 마진 상수 복제 금지.
  - 각 관절의 실측 conf 도 `fault_zoom._kp_conf` 로 읽어 같이 적는다(게이트 통과
    여부를 나중에 되짚을 재료).
산출 = `{label}/real.json`.

(b) `--sweep --out {label}` : 등재 10동작 parity 계측.
f5h 모듈을 **경로 import** 한다(`importlib.util.spec_from_file_location` 로
`.planning/quick/260731-f5h-.../sweep_leg_angle.py` 로드). 그 모듈에서
`_registered_motions` · `_criteria_joints` · `_USER_KP` · `_REF_KP` · `_user_kp_for` ·
`_report` · `_identity` · `_load_frames` · `_frame_sources` 를 빌려 쓴다
(10동작 합성과 실물 프레임 페어를 다시 만들지 않는다). **f5h 파일은 수정 금지.**
unit 만 이 프로브가 새로 만든다:
  - 각 criterion 에 대해 **records 를 실 fixture 모양으로 합성**한다.
    split_angle 은 `source='vision'`, 그 밖은 `source='geometry'`.
    fault_joints 는 8-keypoint 목록(F1 표의 power-spin 형상)을 쓴다.
  - 그 records 를 `criterion_units_from_records` 에 넣어 unit 을 얻는다.
    이렇게 해야 vision 분기가 실제로 실행된다(F6).
  - `fault_zoom.build_fault_zoom_comparisons` 를 f5h 의 호출 형태 그대로 부르고
    (`split_angle_present` 는 criterion 이 split_angle 일 때만 True),
    `sunity_shared.analysis.fault_zoom` 로거에 핸들러를 붙여 `fault_zoom_crop`
    레코드를 잡는다. **문자열 재파싱 대신 `LogRecord.args` 튜플을 읽어라** —
    로그 포맷이 바뀌어도 안 깨진다. 거기서 user_kind / user_side_px /
    ref_kind / ref_side_px / vertex_centered / shared_side_px 를 뽑고
    `ratio = user_side_px / ref_side_px`(둘 다 정수일 때만)를 계산해 적는다.
  - 방출 PNG 의 sha256 도 적는다(비-split 카드 무회귀 대조 재료).
산출 = `{label}/sweep.json`.

(c) `--check {label}` : 구조 완결성만 본다(판정 아님). 4 fixture 전건 로드,
동작 10건 이상, 카드 행마다 criterion 과 box 또는 명시적 null 사유가 있을 것.
빠진 게 있으면 exit 1.

**이 태스크에서 캡처할 기준선 4종** (전부 `before/` 아래):
  1. `--real --out before` + `--sweep --out before` + `--check before`
  2. pytest FAILED/ERROR node ID 집합.
     `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests`
     출력에서 `^(FAILED|ERROR) ` 행만 정렬 저장. 경고: `cd backend && pytest` 는
     수집에서 중단돼 거짓 통과하니 **절대 쓰지 말 것**. 총계도 같이 적어라
     (2026-08-02 관측 = 59 failed / 3801 passed. 하드코딩 게이트로 쓰지 말고
     방금 잰 값을 기준선으로 삼는다).
  3. f5h `legacy_baseline.py --verify` 를 **지금 HEAD 에서** 돌려 결과 문자열을
     저장. 이미 mismatch 라면 그것이 pre-existing 이라는 사실을 그대로 기록하고
     고치려 들지 말 것(이번 사이클 범위 밖).
  4. czw `backend/evals/realfixture/replay.py --recon-only` 표준출력을 저장.
     **exit code 1 이 정상**이다(czw 설계). 게이트는 exit code 가 아니라
     "Task 3 산출과 문자열 동일" 이다.

Rule 3(차단)이 나오면 멈추고 보고하라. 특히 f5h 모듈 import 가 안 되면 그 사유를
적고 대안(프로브가 10동작 합성을 자체 보유)을 제안한 뒤 진행한다.
  </action>
  <verify>
    <automated>set -o pipefail; cd /Users/kimtaesung/Dev/SunityMotion && Q=.planning/quick/260802-gny-split-angle-region-members-crop-split-an && backend/.venv/bin/python $Q/parity_probe.py --real --out before && backend/.venv/bin/python $Q/parity_probe.py --sweep --out before && backend/.venv/bin/python $Q/parity_probe.py --check before && git diff --quiet HEAD -- backend/ app/ && echo PROD-UNTOUCHED</automated>
  </verify>
  <done>
`before/real.json` 과 `before/sweep.json` 이 존재하고 `--check` exit 0.
`before/` 에 pytest node ID 집합 · legacy_baseline verdict · czw recon 출력이
각각 파일로 남아 있다. `git diff HEAD -- backend/ app/` 이 빈 출력.
그리고 `before/real.json` 을 **직접 열어** power-spin 의 split_angle 과
leg_extension 의 joints 와 box 가 같은 값임을 눈으로 확인해 보고에 적는다
(증상 2의 실 데이터 근거이자 Task 3 대조 기준).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: crop 멤버를 criterion 별로 가른다 (백엔드 2 미러 + 앱 분기 기록)</name>
  <files>
    backend/shared/python/sunity_shared/analysis/fault_zoom.py
    backend/functions/pipeline/app.py
    app/src/lib/deductionLabels.ts
    backend/tests/test_fault_zoom.py
  </files>
  <behavior>
locked_spec 8행이 그대로 테스트다. **테스트를 먼저 쓰고 RED 를 눈으로 확인한 뒤**
구현한다. 최소 6개:

- `test_split_angle_crop_members_vision_branch` — `source='vision'` + faultJoints =
  hips+knees 인 record 로 `criterion_units_from_records` 호출 → joints 에
  left_ankle / right_ankle 포함. (1행. 이 테스트가 오케스트레이터 가설의 구멍을
  막는 자물쇠다. 이게 없으면 (4) 분기만 고치고 끝날 수 있다.)
- `test_split_angle_crop_members_geometry_branch` — `source='geometry'` 로 같은 확인. (2행)
- `test_leg_extension_and_arm_extension_members_unchanged` — 두 분기 모두에서
  leg_extension joints == `REGION_MEMBERS["legs"]`, arm_extension 동일. (3·4행)
- `test_split_angle_unit_joint_order_contract` — joints[0] == left_hip, 발목이
  **끝 2칸**. (7행. `_CropUnit.joint` 와 `_anchor_xy` 기본값 불변의 근거)
- `test_split_angle_crop_box_unchanged_without_ankles` — 발목 좌표가 아예 없는
  8관절 report 와, 발목 conf 를 `_KP_CONF_MIN` 미만으로 준 report 두 케이스에서
  `_member_pts` → `_side_crop` 의 box 가 **4관절 멤버로 부른 결과와 완전 동일**.
  (5·6행 = fail-closed 무회귀. 튜플 동등 비교, 근사 금지.)
- `test_mode3_zoom_extra_members_mirror` — pipeline `_MODE3_ZOOM_CRITERION_EXTRA_MEMBERS`
  == fault_zoom `CRITERION_CROP_EXTRA_MEMBERS`, 그리고
  `_MODE3_ZOOM_REGION_MEMBERS == REGION_MEMBERS`,
  `_MODE3_ZOOM_CRITERION_REGION == CRITERION_REGION`. (8행. 드리프트 자물쇠)
  </behavior>
  <action>
**(1) fault_zoom.py — 표 1개 추가 + 적용 1줄.**
`REGION_MEMBERS`(139~142행) 바로 아래에 `CRITERION_CROP_EXTRA_MEMBERS:
dict[str, tuple[str, ...]]` 를 신설하고 `"split_angle": ("left_ankle",
"right_ankle")` 만 등재한다. **REGION_MEMBERS 는 한 글자도 고치지 않는다**
(leg_extension·arms·vision 폴백·앱 미러가 전부 그 값을 공유한다).

주석에 담을 근거 — 임의 확대가 아니라 **"그 criterion 이 그리는 점의 누락분"** 임을
쓸 것. 이 카드의 드로잉 점은 `_leg_line_pts`(974행)가 고르는 (골반 중점, 왼 다리 끝,
오른 다리 끝)이고 다리 끝 후보는 ankle 다음 knee 다. 멤버 집합이 그보다 좁으면
`_pt_in_crop`(1315행) 3점 게이트가 탈락해 그림이 통째로 사라진다.
region 을 안 건드리는 이유(앱 칩·캡션 grouping 이 region 을 쓴다)와 **뒤에
append 하는 이유**(joints[0] = `_CropUnit.joint`, `_anchor_xy` 기본값 valid[0])를
함께 적는다. leg_extension 이 대상이 아닌 이유도 한 줄(무릎 신전 criterion 이라
골반과 무릎이 계측 부위 전부).

적용은 `criterion_units_from_records` 의 **if/elif/else 3분기 뒤, dedupe(217행)
직전** 한 줄이다: `joints = list(joints) + list(
CRITERION_CROP_EXTRA_MEMBERS.get(crit, ()))`. **분기 안에 넣지 말 것** — 실 doc 의
split_angle 은 vision 분기로 가고 그쪽 산출은 faultJoints 교집합이라 발목을 담을
수 없다(F1). 그 사유를 주석 2줄로 남겨라. 뒤이은 dedupe 루프가 중복을 자동
제거하므로 faultJoints 에 발목이 들어오는 미래 케이스도 안전하다.

**(2) pipeline/app.py — 미러 1개 + 배선 1곳.**
`_MODE3_ZOOM_REGION_MEMBERS`(3483~3486행) 아래에
`_MODE3_ZOOM_CRITERION_EXTRA_MEMBERS` 를 같은 내용으로 두고, `crit_units.append`
의 `"joints"`(3547행)를 `_MODE3_ZOOM_REGION_MEMBERS[region] +
_MODE3_ZOOM_CRITERION_EXTRA_MEMBERS.get(crit, ())` 로 바꾼다.
`fault_joints`(3557행)와 `kinds`(3558행)는 **손대지 않는다** — `item["kind"]` 는
`unit.joint`(=left_hip)로 조회되므로 영향이 없고, 건드리면 mode3 fan-out 폴백
경로의 산출이 흔들린다. 미러인 이유와 동등성 테스트 위치를 주석에 적을 것.

**(3) app/src/lib/deductionLabels.ts — 주석만. 동작 변경 0.**
`CRITERION_REGION_KEYPOINTS`(159행) 위에 **의도적 분기**를 기록한다.
백엔드는 split_angle 의 **crop 프레이밍 멤버**에만 발목을 더했고, 이 표는
**마커·칩 투영**이라 4 keypoint 를 유지한다. 유지 사유를 근거와 함께 적어라.
`KeypointName` 에 발목이 있으므로 타입 제약이 아니라 **판단**이고, 여기에 발목을
넣으면 33-G S1 승인 그룹 마커의 centroid 가 아래로 이동하고 오버레이에 미승인
점이 생긴다. 백엔드 표 이름(`CRITERION_CROP_EXTRA_MEMBERS`)과 `quick-260802-gny`
를 인용해 다음 사람이 이것을 드리프트로 오해하고 되돌리지 못하게 할 것.
파이썬 2표의 동등성은 테스트가 지킨다는 사실도 적는다.

**(4) 테스트** — `backend/tests/test_fault_zoom.py` 에 behavior 6종. 기존 테스트는
**한 줄도 수정하지 않는다**(수정이 필요해지면 그건 회귀 신호다. 멈추고 보고).
`test_split_angle_crop_box_unchanged_without_ankles` 는 반드시 프로덕션
`_member_pts` 와 `_side_crop` 을 호출해 box 튜플을 비교할 것(기하 재계산 금지).

**금지사항 재확인:** 새 docstring/주석에 (a) 프레임 fps 수치 리터럴, (b) 등재
모션 id 문자열(criteria yaml 파일명 형태)을 쓰지 말 것 — 산문에 있어도 게이트가
위반으로 잡는다. 근거는 **줄 번호로** 인용한다. 이모지 0. 새 튜닝 상수·임계 0.
채점 모듈(`deduction_engine.py`·`dimensions.py`·`kismam.py`)은 열지 말 것.
  </action>
  <verify>
    <automated>set -o pipefail; cd /Users/kimtaesung/Dev/SunityMotion && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_fault_zoom.py && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/phase33 && git diff --quiet HEAD -- backend/shared/python/sunity_shared/analysis/deduction_engine.py backend/shared/python/sunity_shared/analysis/dimensions.py backend/shared/python/sunity_shared/analysis/kismam.py && (cd app && npm run typecheck)</automated>
  </verify>
  <done>
6개 신규 테스트가 RED 를 거쳐 GREEN 이 됐고, **RED 시점의 실패 메시지를 보고에
그대로 옮겨 적었다**(특히 vision 분기 테스트 — 그게 이번 수리의 존재 이유다).
`test_fault_zoom.py` 와 `phase33` 전건 pass, 기존 테스트 수정 0.
채점 모듈 3종 diff 0. `npm run typecheck` clean.
`git diff HEAD --name-only` 결과가 이 태스크의 files 4개뿐이다.
  </done>
</task>

<task type="auto">
  <name>Task 3: 수정 후 실측 + parity 이동표 + 무회귀 게이트</name>
  <files>
    .planning/quick/260802-gny-split-angle-region-members-crop-split-an/after/
    .planning/quick/260802-gny-split-angle-region-members-crop-split-an/parity_delta.md
    .planning/quick/260802-gny-split-angle-region-members-crop-split-an/parity_probe.py
  </files>
  <action>
Task 1 프로브를 그대로 다시 돌려 `after/` 를 만들고, `--diff before after` 모드를
프로브에 추가해 판정한다. **임계 신설 0. 이미 있는 것만 쓴다.**

**(3-1) `--diff before after` 게이트 (exit 0 조건 — 전부 하드).**
  - `sweep.json` 에서 criterion 이 split_angle 이 **아닌** 모든 카드:
    `user_side_px` · `ref_side_px` · `png_sha256` 전건 동일. 1건이라도 다르면
    exit 1 이고, 다른 카드를 전부 나열한다. (다른 카드에 번진 것 = 과잉 일반화)
  - `real.json` 에서 split_angle 이 아닌 모든 행: box 튜플 동일.
  - `real.json` 의 power-spin split_angle: joints 가 4 → 6, box 가 leg_extension
    box 와 **달라짐**, 그리고 `left_ankle_in_crop` 또는 `right_ankle_in_crop`
    중 하나 이상이 False → True.
  - 이 세 항목은 판정이지 튜닝이 아니다. 실패하면 코드로 돌아가라. 게이트를
    무르게 고치지 말 것.

**(3-2) parity 이동표 — `parity_delta.md`.**
등재 10동작 x 카드 전건을 표로 낸다. 컬럼 =
`motion | criterion | user_side_px before→after | ref_side_px before→after |
ratio before→after | png 변경 여부`. 그리고 아래를 **명시적으로** 적는다:
  - 움직인 카드가 split_angle 뿐인가(예/아니오 + 목록).
  - split_angle 카드의 ratio 가 32-03 밴드 0.8~1.25 를 벗어난 건이 몇 건인가.
    벗어났으면 **그 사실을 그대로 적는다.** 밴드를 넓히지 말고, 임계를 만들지
    말고, "무시 가능"이라고 쓰지 말 것.
  - `user_side_px` 가 `min(h, w)` 상한에 클램프된 카드가 있는가(있으면 그 카드는
    프레이밍이 사실상 전신에 가까워졌다는 뜻이니 별도 줄로 적는다).
  - 기준 패널이 8관절이라 커지지 않는다는 구조적 사실(F5)을 표 밑에 1줄로.
belle 판단이 필요한 항목은 표 맨 위에 "belle 결정 필요" 절로 모아 둔다.

**(3-3) 채점 무접촉 증명 4종.**
  - 채점 모듈 3종 `git diff $BASE` 빈 출력 (Task 2 게이트 재확인).
  - pytest FAILED/ERROR node ID 집합을 다시 잡아 `before/` 것과 `diff` → 빈 출력.
    총계(passed 수)도 같이 적는다. 신규 테스트만큼 passed 가 늘어야 정상이고,
    줄었으면 회귀다.
  - f5h `legacy_baseline.py --verify` 를 다시 돌려 **verdict 문자열이 before 와
    동일**한지 확인(before 가 PASS 였으면 PASS, mismatch 였으면 같은 mismatch).
  - czw `replay.py --recon-only` 를 다시 돌려 표준출력이 `before/` 것과 **문자열
    동일**. exit code 는 여전히 1 이 정상이다. 이것이 실 doc 4건에서
    `deductionBreakdown.records`(criterion·measuredValue·points·final)가 한 자도
    안 움직였다는 직접 증거다.

**(3-4) 산출물을 직접 열어보고 완료 선언.**
`after/real.json` 과 `after/sweep.json` 을 **열어서** 값을 눈으로 읽고, 보고의
숫자는 그 파일에서 인용한 것이어야 한다(요약문 재인용 금지). "쟀다/열었다/
돌렸다"를 각 주장 옆에 붙여라.

**미검증은 미검증이라고 적어라.** 최소한 아래는 이번 사이클에서 확인되지 않는다:
  - 실 영상 프레임 해상도(프로브는 가정 shape 를 쓴다).
  - PNG 픽셀 내용과 사이각이 실제로 다시 그려지는지 — 그건 §C-4 재생성 또는 Pod
    재분석이 있어야 본다. 이번 사이클은 **crop 이 발목을 담는가**까지다.
  - 앱 화면·실기기 렌더.
  이것들을 "PASS" 로 적으면 안 된다.
  </action>
  <verify>
    <automated>set -o pipefail; cd /Users/kimtaesung/Dev/SunityMotion && Q=.planning/quick/260802-gny-split-angle-region-members-crop-split-an && backend/.venv/bin/python $Q/parity_probe.py --real --out after && backend/.venv/bin/python $Q/parity_probe.py --sweep --out after && backend/.venv/bin/python $Q/parity_probe.py --diff before after && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 | grep -E '^(FAILED|ERROR) ' | sort > $Q/after/pytest_nodes.txt; diff $Q/before/pytest_nodes.txt $Q/after/pytest_nodes.txt && backend/.venv/bin/python backend/evals/realfixture/replay.py --recon-only > $Q/after/recon.txt 2>&1; diff $Q/before/recon.txt $Q/after/recon.txt && test -s $Q/parity_delta.md && echo GATES-OK</automated>
    <human-check>
belle 확인 (done 조건 아님 — 이번 사이클은 여기까지 못 간다):
§C-4 재생성 또는 Pod 재분석으로 새 doc 이 나온 뒤 실기기에서
(1) split_angle 카드 사진이 leg_extension 카드와 **다른 사진**인지,
(2) 그 카드에 골반에서 양다리로 뻗는 선 2개와 사이각 호가 보이는지,
(3) 두 패널(학생·정은지)의 확대 배율이 어색하지 않은지 — parity_delta.md 의
    ratio 이동표를 같이 보고 판단.
    </human-check>
  </verify>
  <done>
`--diff before after` exit 0. pytest node ID diff 빈 출력이고 passed 증감이
신규 테스트 수와 일치. legacy_baseline verdict before 와 동일. czw recon 출력
before 와 문자열 동일. `parity_delta.md` 에 10동작 전건 표와 "belle 결정 필요"
절이 있고, ratio 밴드 이탈 건수가 **숫자로** 적혀 있다(0 이면 0 이라고 적는다).
SUMMARY 에 미검증 3종이 "안 봤다"로 남아 있다.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 표시 경로 → 채점 경로 | crop 멤버 표가 점수 산출로 새는 것 |
| 백엔드 표 ↔ 앱 표 | 3면 미러가 조용히 어긋나는 것 |
| 프로덕션 ↔ 로컬 하네스 | 하네스가 프로덕션 규칙을 복제해 거짓 통과하는 것 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-gny-01 | Tampering | `criterion_units_from_records` | mitigate | 채점 모듈 3종 `git diff` 빈 출력 + czw `--recon-only` 출력 문자열 동일(실 doc 4건 records 불변) + legacy_baseline verdict 불변 |
| T-gny-02 | Denial of Service | `_side_crop` `_box_for` | mitigate | split 카드 `user_side_px` 를 10동작 전건 기록. `min(h,w)` 클램프 도달 카드를 `parity_delta.md` 에 별도 줄로 명시하고 belle 판단으로 올린다. 임계 신설·밴드 완화 금지 |
| T-gny-03 | Repudiation | 파이썬 2표 미러 | mitigate | `test_mode3_zoom_extra_members_mirror` 가 3표 동등성을 강제. 앱측 분기는 주석으로 명문화해 "드리프트로 오해 후 되돌림"을 차단 |
| T-gny-04 | Tampering | `_member_pts` fail-closed | mitigate | 8관절 doc·저신뢰 발목 두 케이스에서 `_side_crop` box 튜플이 4관절 호출과 완전 동일함을 단위 테스트로 고정 |
| T-gny-05 | Spoofing | 하네스 자체 계산 | mitigate | crop 기하·포함 판정을 프로브가 계산하지 않고 `_member_pts`/`_side_crop`/`_pt_in_crop`/`_kp_conf` 프로덕션 함수만 호출. 로그는 `LogRecord.args` 로 읽어 포맷 파싱 의존 제거 |
| T-gny-06 | Information disclosure | 실 fixture 재사용 | accept | czw 가 이미 presigned URL·AWS 키를 값 기준 strip 했고 인물 이미지 0. 프로브는 그 JSON 을 읽기만 한다 |
| T-gny-SC | Tampering | npm/pip 설치 | accept | **신규 설치 0** — numpy·PIL·pyyaml 전부 기존 의존성. 설치 태스크가 없으므로 legitimacy 게이트 대상 아님 |
</threat_model>

<verification>
- 백엔드 회귀: `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests`
  의 FAILED/ERROR node ID 집합이 착수 시점 캡처와 diff 0.
  (`cd backend && pytest` 금지 — 수집 중단으로 거짓 통과한다.)
- 앱: `cd app && npm run typecheck` clean.
- 무회귀 해시: f5h `legacy_baseline.py --verify` verdict 가 착수 시점과 동일.
- 실 doc 채점 불변: czw `replay.py --recon-only` 표준출력 문자열 동일.
- 표시 무회귀: `--diff before after` 가 비-split 카드 side_px·sha256 전건 동일을 강제.
- diff 범위: `BASE=$(git rev-parse HEAD)` 고정 후 `git diff $BASE --name-only` 가
  이 플랜의 files_modified 밖으로 나가지 않을 것. `git diff --exit-code` 단독 사용
  금지(`git add` 로 무력화된다).
- 파이프 있는 게이트는 전부 `set -o pipefail`.
- 카운트 grep 을 쓸 일이 있으면 `grep -v '^#' | grep -c` 형태로 주석을 걸러낼 것.
</verification>

<success_criteria>
- locked_spec 8행 전건 성립, 각 행마다 그것을 성립시킨 행위(돌렸다/열었다/쟀다)가
  SUMMARY 에 적혀 있다.
- 실 doc power-spin 에서 split_angle 멤버 4 → 6, box 가 leg_extension 과 갈림,
  발목 `_pt_in_crop` False → True 가 `after/real.json` 실측으로 확인된다.
- 비-split 카드 표시 산출 이동 0 (side_px + sha256).
- 채점 무접촉 4종 증명 전부 통과.
- `parity_delta.md` 에 배율 parity 이동이 숫자로 적혀 있고, 밴드 이탈이 있으면
  숨기지 않고 "belle 결정 필요"로 올라와 있다.
- 미검증 항목(실 영상 해상도 가정 · PNG 픽셀 · 실기기)이 "안 봤다"로 남아 있다.
</success_criteria>

<output>
Create `.planning/quick/260802-gny-split-angle-region-members-crop-split-an/260802-gny-SUMMARY.md` when done.
</output>
