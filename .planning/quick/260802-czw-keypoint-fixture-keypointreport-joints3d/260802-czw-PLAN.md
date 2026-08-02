---
phase: quick-260802-czw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/scripts/pull-real-fixtures.mjs
  - backend/evals/realfixture/replay.py
  - backend/evals/realfixture/fixtures/MANIFEST.json
  - backend/evals/realfixture/fixtures/*.json
  - backend/evals/realfixture/fixtures/reference/*.json
  - .planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json
autonomous: true
requirements: [CZW-01, CZW-02, CZW-03]
user_setup: []

must_haves:
  truths:
    - "저장된 Firestore doc 만으로 GPU 0 · Gemini 호출 0 · Pod 0 으로 채점·record·카드 프레임이 재현된다"
    - "러너가 재현본과 저장 records 의 일치 여부를 스스로 판정해 record 단위로 보고한다 — 불일치 fixture 는 판정을 내지 않는다"
    - "실 데이터에서 record 별 atFrameIdx 가 갈리는지에 대한 판정이 숫자로 산출된다 (뭉쳐도 정상 산출)"
    - "러너는 Firestore·S3 에 쓸 수 없다 — 쓰기 경로 호출 시 예외로 죽는다"
    - "프로덕션 코드(backend/functions, backend/shared, app/src) diff 0"
  artifacts:
    - path: "app/scripts/pull-real-fixtures.mjs"
      provides: "Firestore → 리포 JSON 박제 (읽기 전용, presigned URL 재귀 strip)"
    - path: "backend/evals/realfixture/fixtures/MANIFEST.json"
      provides: "출처·용량·strip 경로·파생 fps 와 그 정합 assert 기록"
      contains: "studentAnglesFps"
    - path: "backend/evals/realfixture/replay.py"
      provides: "fixture 어댑터 주입 재생 + RECON 게이트 + atFrameIdx 판정"
      min_lines: 200
    - path: ".planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json"
      provides: "판정 산출물 — record 별 atFrameIdx / 카드 userFrameIdx / atMatched"
  key_links:
    - from: "backend/evals/realfixture/replay.py"
      to: "pipeline app._build_deduction_measured_deviations"
      via: "measured_at_out out-param"
      pattern: "measured_at_out"
    - from: "backend/evals/realfixture/replay.py"
      to: "fault_zoom.criterion_units_from_records / build_fault_zoom_comparisons"
      via: "record → crop unit → 카드 프레임"
      pattern: "criterion_units_from_records"
    - from: "backend/evals/realfixture/replay.py"
      to: "app._pipeline_frame_fps"
      via: "주입 FrameExtractor 의 target_fps"
      pattern: "target_fps"
---

<objective>
저장된 분석 doc(`angles` / `keypointReport` / `joints3d` / `visionVeto` / Gemini 캐시)만으로
분석 파이프라인의 **채점 → record → 카드 프레임** 구간을 GPU 0 · Gemini 0 · Pod 0 · 결정적으로
재현하는 상설 하네스를 만든다. 그리고 그 하네스로 첫 판정을 낸다 —
**quick-260801-gbk 가 넣은 `atFrameIdx` 가 실 데이터에서 record 마다 갈리는가.**

Purpose: 검증 한 바퀴가 1시간 + belle 시간이라 한 번에 몰아 고치게 되고, 몰아 고치면 무엇이
효과였는지 못 가린다. 합성 fixture 는 두 번 거짓 통과를 냈다(07-31 `drawn 21→79`, 08-01
`[4,9,14]` + `atMatched` 100%). 이 하네스는 **실물 분포 위에서 초 단위로** 답을 낸다.

Output:
  · `app/scripts/pull-real-fixtures.mjs` — Firestore → 리포 JSON 박제 (읽기 전용)
  · `backend/evals/realfixture/fixtures/` — 4 분석 + 4 기준 doc + MANIFEST (커밋)
  · `backend/evals/realfixture/replay.py` — 재생 러너 + RECON 게이트 + 판정
  · `replay_out.json` — 판정 산출물
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/quick/260801-gbk-record-atframeidx-criterion/260801-gbk-SUMMARY.md
@.planning/quick/260801-gbk-record-atframeidx-criterion/sweep_record_moment.py
@backend/functions/pipeline/app.py
@backend/shared/python/sunity_shared/analysis/fault_zoom.py
@backend/shared/python/sunity_shared/analysis/vision_veto.py
@backend/shared/python/sunity_shared/analysis/interfaces.py
@backend/shared/python/sunity_shared/firestore_admin.py
@app/scripts/seed-reference-motions.mjs
</context>

<decisions_made>
플랜이 결정해야 했던 4건. 근거는 전부 소스·실측이다.

### D-1. 재현 깊이 = 저장 산출물 → builder → tally → 각인 → units → 카드. `_process` 전체 아님.

`atFrameIdx` 의 **유일한 writer** 는 `app.py:2439 _record_moment`(=`_build_deduction_measured_deviations`
안), **유일한 각인처**는 `app.py:5113 _attach_translation_emission`, **유일한 카드 전달 경로**는
`criterion_units_from_records → build_fault_zoom_comparisons`(`app.py:3389` / `3158`).
그 위 단계(S3 download / ffmpeg / RTMW / Gemini / coach / Firestore write)는 값에 **기여하지 않고**
입력 산출물(`angles`, `visionVeto`, `keypointReport`)만 만든다 — 그 산출물은 doc 에 저장돼 있다.
∴ `_process` 전체 재현은 GPU·Gemini·S3 를 되살릴 뿐 판정에 아무것도 더하지 않는다.

**단, 이 전제는 주장이 아니라 게이트가 증명한다.** RECON 게이트(Task 2)가 재현본과 저장
`deductionBreakdown.records` 의 일치를 record 단위로 확인하고, 불일치하면 그 fixture 의 판정을
내지 않는다. 재현하지 못한 것으로 판정하지 않는다.

### D-2. `angles` 와 `keypointReport` — 둘 다 진실. 하네스는 어느 쪽도 파생시키지 않는다.

실측(4 doc):

| doc | `angles` | `keypointReport` | 관계 |
|---|---|---|---|
| 학생 power-spin | 83 frames × 8 kismam 관절 | 166 frames · 12 관절 · fps 18 | 83 = 166/2 → angles 9fps |
| 학생 kip-up | 68 × 8 | 136 · 12 · 18 | 9fps |
| 학생 pdshape | 159 × 8 | 318 · 12 · 18 | 9fps |
| 학생 elbow-twist | 180 × 8 | 360 · 12 · 18 | 9fps |
| 기준 4건 | 159 / 118 / 237 / 329 × 8 | 동수 · fps 18 | 기준은 18fps |

`angles`(9fps · 8 kismam 관절) = **채점 도메인** — `atFrameIdx` 가 사는 곳.
`keypointReport`(18fps · 12 관절) = **표시·크롭 도메인** — fault_zoom 이 쓰는 곳.
둘 다 production 이 저장한 1급 산출물이고, 변환의 **유일 소유자는 production 의
`fault_zoom._to_rep_idx`**(`fault_zoom.py:350`)다. 하네스가 자체 fps 산술을 하는 순간 그 값이
판정에 섞인다 — 그러면 합성 fixture 와 같은 병이 재발한다. 하네스는 각 산출물을 production 이
주입하는 자리에 그대로 주입하고 변환은 production 에 맡긴다.

fps 리터럴은 쓰지 않는다. 박제 시점에 `krFps × anglesFrames ÷ krFrames` 로 파생하고 4 doc 전부
동일값인지 assert 한 뒤 MANIFEST 에 기록한다(실측 학생 9.0 / 기준 18.0). 러너는 그 값을
주입 FrameExtractor 의 `target_fps` 로 노출해 `app._pipeline_frame_fps()`(`app.py:4732`)가
**production 과 같은 경로로** 읽게 한다. 확인함: 스텁 주입 시 `_pipeline_frame_fps()` = 9.0 반환,
`imageio` 부재(venv 실측)에도 죽지 않는다.

### D-3. fixture 는 리포에 커밋한다. 전체 doc − URL 필드.

실측 용량: 분석 4건 = **1,308 KB**(231/193/409/475), 기준 4건 = **1,779 KB**(339/252/498/690).
**합 3.0 MB.** 영상은 받지 않는다(A 범위 밖).

커밋하는 이유: 이 사이클이 죽이려는 병이 "입력이 움직여서 무엇이 효과였는지 못 가리는 것"이다.
Firestore doc 은 재분석마다 덮어써진다 — 실제로 07-31 §C-4 재산출이 덮었고 그때 점수가
80→60 으로 움직였다(원인 미분리). 입력이 리포에 고정돼 있지 않으면 하네스가 같은 병을 물려받는다.
3.0 MB 텍스트는 이미 스위프 PNG 를 담고 있는 리포에서 문제되는 크기가 아니다.

**필드 화이트리스트는 쓰지 않는다.** 부분 박제는 "왜 이 필드가 없지"가 조용한 truncation 으로
바뀌는 경로이고 그게 이 사이클이 없애려는 실패 유형 그 자체다. 대신 **규칙 하나로 뺀다** —
`X-Amz-Signature` 를 포함하는 문자열 값은 재귀적으로 제거하고 제거 경로를 MANIFEST 에 남긴다.
(presigned URL 은 7일 만료라 무용하고, `X-Amz-Credential=AKIA…` 로 AWS access key ID 를
품고 있다 — 커밋하면 안 된다. T-czw-01.)

### D-4. 합성 스위프와의 역할 분담

> **합성(`sweep_record_moment.py`) = 내가 만든 경계값에서 규칙이 작동하는지 본다(통제).
> 실물(`replay.py`) = 내가 만들 수 없는 실제 분포에서 그 규칙이 무엇을 내는지 본다(대표성).
> 전자는 코드가 맞는지를, 후자는 답이 맞는지를 묻는다.**

합성 스위프는 지우지 않는다. 이 한 줄을 `replay.py` 모듈 docstring 과
`sweep_record_moment.py` 헤더 주석 양쪽에 박는다(파일 하나만 열어도 보이도록).
</decisions_made>

<baseline_facts>
착수 전에 오케스트레이터/플래너가 직접 조회해 확정한 값. 재조사 금지, 전제로 쓸 것.

**belle 계정 `csKWYvI3WCPYPysNQ9KkWecaUvq1` · 4 분석 · 전부 `mode1` · `visionVeto.status=applied`**

| 분석 | 기준 | 점수 | records | 카드 | 카드 `userFrameIdx` (저장값) |
|---|---|---|---|---|---|
| `powerspinFault1785373695` | ref-power-spin | 60 | 3 | 4 (advisory 1) | **38, 38, 38, 38** |
| `kipupFault1785373695` | ref-kip-up | 79 | 2 | 2 | **16, 16** |
| `pdshapeCorrect1785373695` | ref-pdshape | 100 | 1 | 1 (advisory) | **104** |
| `elbowtwistsisterFault1785373695` | ref-elbow-twist-sister | 63 | 8 | 5 (advisory 1) | **144 ×5** |

**belle 이 본 증상이 실 doc 에 그대로 있다.** 저장 record 중 `atFrameIdx` 를 가진 것은 **0건**
(doc 이 gbk 커밋보다 앞선다).

record criterion 분포 (총 14):
  · `angle_vs_reference__{jk}` **11건** (`source=geometry`) ← 판정의 본체
  · `leg_extension` 1건, `split_angle` 2건 (`source=vision` — **순간 fail-closed**, gbk 설계)

**판정의 무게중심 = elbow-twist.** record 8건이 전부 `angle_vs_reference__*` 이고 관절이 8개
전부 다르다. 여기서 뭉치면 gbk 는 실물에서 실패다.

**`vision_pointed_joints` 재구성 부담이 작다** — pdshape·elbow-twist 는
`collectionStatus=no_fault` · `rootCauseHypotheses=[]` 이고, power-spin·kip-up 의 hypothesis
`faultKey.keypoint_set` 은 `head_neck`/`torso`/`leg`/`arm` 이다. 그리고 pointed 집합이 틀리면
window 경로 ↔ DTW 경로 선택이 바뀌어 `measuredValue` 가 달라진다 — **RECON 게이트가 그것을
잡는다.** 추측이 아니라 게이트가 판별한다.

`visionVeto` 에 저장돼 있는 것: `windowMedianAngleDeltas{windowPolicy, sourceFrameIndices,
deltas[8]}`, `alignment{visibility, distance, adoption, refFramePresent, localPathCount}`,
`collectionStatus`, `faultJoints`, `faultJointDeficits`, `rootCauseHypotheses`, `angleDeltas[8]`.
**`result.quantification` 은 doc 에 없다** — builder 가 읽는 `windowMedianAngleDeltas` 는
`visionVeto` 안에 있다(`vision_veto.py:755-756` 이 거기로 복사).

**임포트 가능성 확인함** — `PYTHONPATH=backend/shared/python:backend/functions/pipeline`
로 `backend/.venv` 에서 `app.py` 가 그대로 import 된다. `_build_deduction_measured_deviations` /
`_deviation_against` / `_attach_translation_emission` 전부 도달 가능.
venv 실측: `numpy` OK · `PIL` OK · `yaml` OK · **`imageio` 없음** · `scipy` 없음 ·
`firebase_admin` **없음**(→ 박제는 Node, `app/node_modules/firebase-admin` 사용).

production DTW 진입점 = `app.py:5587 _deviation_against(angles, ref["angles"], num_joints,
ref_boundary=...)` → `(deviation, match, user_seg, a_ref)`. 순수 numpy · 결정적.
`result.motionAlignment.anchors`(flat, anchorCount 20) 가 그 match 의 저장된 흔적이다.
</baseline_facts>

<tasks>

<task type="auto">
  <name>Task 1: 실 doc fixture 박제 (Firestore → 리포, 읽기 전용)</name>
  <files>
app/scripts/pull-real-fixtures.mjs
backend/evals/realfixture/fixtures/{4개 analysisId}.json
backend/evals/realfixture/fixtures/reference/{4개 refId}.json
backend/evals/realfixture/fixtures/MANIFEST.json
  </files>
  <action>
`app/scripts/pull-real-fixtures.mjs` 를 신설한다. Node 를 쓰는 이유는 `backend/.venv` 에
`firebase_admin` 이 없고(실측) 신규 의존성 0 이 규약이기 때문이다 — `app/node_modules/
firebase-admin` + `firebase-sa.json` 이 이미 있고 `app/scripts/seed-reference-motions.mjs`
가 같은 선례다. **읽기만 한다** — `.set/.update/.delete/.create` 를 이 파일에 쓰지 않는다.

박제 대상(하드코딩이 아니라 스크립트 상단 상수 + `--uid/--ids` 인자로 노출):
uid `csKWYvI3WCPYPysNQ9KkWecaUvq1` 의 4 분석 + 각 분석의 `referenceMotionId` 로
`reference/{refId}` 4건. **기준 doc 은 분석 doc 에서 읽은 id 로 따라간다** — 기준 목록을
따로 적지 말 것(분석과 기준이 어긋나는 fixture 를 원천 차단).

박제 규칙:
 (1) **전체 doc 을 그대로 쓴다.** 필드 화이트리스트 금지 (D-3).
 (2) `X-Amz-Signature` 를 포함하는 문자열 값은 **재귀적으로** 제거하고, 제거한 dot-path 를
     MANIFEST `strippedPaths[]` 에 남긴다. AWS access key ID 가 URL 에 박혀 있다(T-czw-01).
     제거는 키 이름 기준이 아니라 **값 기준 규칙**이다 — 새 URL 필드가 생겨도 자동으로 잡힌다.
 (3) Firestore `Timestamp` 는 epoch ms 정수로 낮춘다(JSON 왕복 안정).
 (4) 부동소수는 **가공하지 않는다.** 반올림 금지 — 재현이 목적이므로 production 입력과
     비트가 같아야 한다.
 (5) 출력은 `JSON.stringify(doc, null, 1)` (diff 가능한 줄 단위).

MANIFEST.json 에 기록할 것:
 · `fetchedAt`, `sourceUid`, 분석/기준 각각의 `docPath` 와 `bytes`
 · `strippedPaths[]`
 · 분석마다 `anglesFrames` / `anglesJointKeys.length` / `keypointReport.{fps,frames,joints}` /
   `joints3d{Keys,Frames}` 실측값
 · **`studentAnglesFps`** = `krFps × anglesFrames ÷ krFrames`, **`referenceAnglesFps`** 동일식.
   4건 전부 동일값이 아니면 **exit 1 로 죽는다**(경고 아님). 이 값이 러너의 유일한 fps 출처다.
 · `sourceRecordCriteria[]`(저장 record 의 criterion·measuredValue·points) 와
   `sourceCardFrames[]`(저장 카드의 criterion·tier·userFrameIdx·refFrameIdx) —
   Task 2 의 RECON 게이트가 대조할 **정답지**다. doc 이 나중에 덮어써져도 정답지는 리포에 남는다.

주석은 한국어, `quick-260802-czw` 인용. 이모지 금지.
  </action>
  <verify>
    <automated>
set -o pipefail
BASE=$(git rev-parse HEAD)
node app/scripts/pull-real-fixtures.mjs
test -f backend/evals/realfixture/fixtures/MANIFEST.json
test "$(ls backend/evals/realfixture/fixtures/*.json | wc -l | tr -d ' ')" = "5"
test "$(ls backend/evals/realfixture/fixtures/reference/*.json | wc -l | tr -d ' ')" = "4"
test "$(grep -rl 'X-Amz-Signature' backend/evals/realfixture/fixtures/ | wc -l | tr -d ' ')" = "0"
test "$(grep -rl 'AKIA' backend/evals/realfixture/fixtures/ | wc -l | tr -d ' ')" = "0"
backend/.venv/bin/python -c "
import json,glob,pathlib
m=json.load(open('backend/evals/realfixture/fixtures/MANIFEST.json'))
assert m['studentAnglesFps']>0 and m['referenceAnglesFps']>0, m
tot=sum(pathlib.Path(p).stat().st_size for p in glob.glob('backend/evals/realfixture/fixtures/**/*.json',recursive=True))
print('fixtures total KB =', tot//1024)
print('studentAnglesFps =', m['studentAnglesFps'], 'referenceAnglesFps =', m['referenceAnglesFps'])
print('analyses =', len(m['analyses']), 'references =', len(m['references']))
print('sourceRecordCriteria total =', sum(len(a['sourceRecordCriteria']) for a in m['analyses']))
"
git diff $BASE --stat -- backend/functions backend/shared app/src && \
  git diff $BASE --exit-code -- backend/functions backend/shared app/src && echo "PROD-DIFF-0"
    </automated>
  </verify>
  <done>
fixture 9개 파일 + MANIFEST 존재. presigned URL·AKIA 잔재 0. `studentAnglesFps`/
`referenceAnglesFps` 가 4건 정합 assert 를 통과해 기록됨. `sourceRecordCriteria` 14건 ·
`sourceCardFrames` 12건 이 정답지로 박힘. 프로덕션 코드 diff 0.
  </done>
</task>

<task type="auto">
  <name>Task 2: replay.py 재생 + RECON 게이트 (판정 구현 전에 커밋)</name>
  <files>
backend/evals/realfixture/replay.py
  </files>
  <action>
`backend/evals/realfixture/replay.py` 를 신설한다. `backend/evals/` 는 SAM `CodeUri` 밖이라
(`template.yaml` 확인: 함수별 `functions/*/`, 레이어 `shared/python/`) Lambda 패키지에
들어가지 않는다.

모듈 docstring 에 **D-4 역할 분담 한 줄**과 D-1 깊이 근거, 그리고 "PNG 픽셀은 이 단계에서
의미 없다(합성 프레임) — 사진 판정은 B 단계"를 명시한다. 같은 한 줄을
`sweep_record_moment.py` 헤더에도 추가한다(파일 하나만 열어도 분담이 보이도록).

**(a) 파이프라인 모듈 로드 + 어댑터 주입**
`importlib.util.spec_from_file_location` 로 `backend/functions/pipeline/app.py` 를 로드한다
(RunPod `server.py` 의 `_load_pipeline_module` 과 같은 방식 — 사본 금지). 그 다음 모듈 전역을
fixture 어댑터로 갈아끼운다:
 · `_FRAME_EXTRACTOR` = `target_fps = MANIFEST.studentAnglesFps` 를 노출하고 `.extract()` 가
   호출되면 **RuntimeError 로 죽는** 스텁. 이 값 하나로 `_pipeline_frame_fps()` 가
   production 경로 그대로 동작한다(확인함).
 · `_POSE_ESTIMATOR` / `_RTMW_ENGINE` / `_POLE_DETECTOR` / `_COACH_WRITER` = `.estimate()` ·
   `.write()` 호출 시 **죽는** 스텁.
 · `_s3` = 어떤 속성 접근에도 죽는 스텁.
 · `firestore_admin` 의 쓰기 함수(`update_analysis_status` / `complete_analysis` /
   `fail_analysis` / `store_*` / `record_*`)를 **죽는 함수로 교체**.
"호출되면 죽는다"가 핵심이다 — GPU·네트워크·쓰기가 **안 일어났다**가 가정이 아니라
실행 결과로 증명된다.

**(b) 저장 산출물 → production 함수로 재생** (하네스가 규칙을 복제하지 않는다)
fixture 마다:
 1. `angles` = `np.asarray(doc['angles']).reshape(doc['anglesFrames'], len(doc['anglesJointKeys']))`
 2. `ref` = 기준 fixture dict 그대로 (production 이 `firestore_admin.get_reference_motion`
    으로 받는 형상). `num_joints = len(ref['anglesJointKeys'])`.
 3. `deviation, match, user_seg, a_ref = app._deviation_against(angles, ref['angles'],
    num_joints, ref_boundary=...)` — `ref_boundary` 산출은 `app.py:5577-5586` 의 조건
    (`sharedBaseMotionId` + `baseUntilS` + `clipRange`)을 그대로 따른다.
 4. `user_mean, ref_mean = app._angles_to_dtw_median_dicts(...)` → `assessments =
    kismam.assess(...)` — `app.py:5602-5609` 호출 형태 그대로.
 5. `profile` = production recognizer 경로가 등재 동작에 대해 만드는 `TechniqueProfile`
    (`technique` 모듈의 등재 조회 함수 사용 — 하네스가 dataclass 를 손으로 채우지 말 것.
    `doc['referenceMotionId']` / `result.mission.motionId` 가 동작 키다).
 6. `quantification` = `vision_veto` 의 **production 데이터클래스**를 저장
    `visionVeto.windowMedianAngleDeltas` 로 채워 만든다(가짜 클래스 금지).
 7. `vision_pointed_joints` = `vision_veto.pointed_joints_from_supported_differences(
    [{'_faultKey': h['faultKey']} for h in visionVeto.rootCauseHypotheses])` —
    production 매퍼 호출. `rootCauseHypotheses=[]` 면 자연히 빈 tuple.
 8. `measured_at = {}` 로 `app._build_deduction_measured_deviations(...)` 호출.
    `alignment_visibility` = `visionVeto.alignment.visibility`,
    `vision_status` = `visionVeto.collectionStatus`,
    `dimension_scores` = `result.dimensionScores`.
 9. tally → breakdown: production 경로(`_apply_vision_veto_from_context` 혹은 그것이 부르는
    `deduction_engine.tally`)를 **그대로** 탄다. 산식을 하네스가 다시 쓰지 않는다.

값을 구할 수 없는 입력이 있으면 **추정해서 채우지 말고** 그 fixture 를 `RECON: BLOCKED
(사유)` 로 기록한다. 빈칸을 메우는 순간 그 fixture 의 판정이 하네스의 창작이 된다.

**(c) RECON 게이트 — 이 하네스가 production 을 재현했는가**
재현 breakdown 을 MANIFEST 의 `sourceRecordCriteria` 정답지와 record 단위로 대조한다:
 · criterion 집합 동일 (누락/과잉을 각각 보고)
 · `measuredValue` |Δ| ≤ 1e-6
 · `points` 동일
 · `final` 동일
결과는 **record 단위 표**로 낸다: `MATCH` / `MISMATCH(Δ)` / `MISSING` / `EXTRA`.
`--recon-only` 인자로 이 게이트만 돌 수 있어야 한다.

**exit code 규약**: 전 fixture 의 전 record 가 `MATCH` 면 0, 아니면 1. **판정 결과는 exit
code 에 영향을 주지 않는다**(Task 3). 이 러너가 묻는 것은 "재현했는가"이고, 답이 마음에
드는가는 별개다.

**커밋 순서 강제**: 이 태스크(RECON 게이트)를 **Task 3 판정 구현 전에 커밋한다.**
판정 숫자를 본 뒤 게이트를 무르게 고치는 경로를 커밋 순서로 차단한다(T-czw-03).
gbk 가 "구현 전 대조군 먼저 캡처"로 쓴 것과 같은 규율이다.
  </action>
  <verify>
    <automated>
set -o pipefail
BASE=$(git rev-parse HEAD)
PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -3
PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 \
  | grep -E '^(FAILED|ERROR)' | sort > /tmp/czw-after.txt
diff /tmp/czw-before.txt /tmp/czw-after.txt && echo "PYTEST-NODEID-DIFF-0"
backend/.venv/bin/python backend/evals/realfixture/replay.py --recon-only; echo "recon-exit=$?"
backend/.venv/bin/python -c "
import subprocess,sys
# 쓰기·GPU 경로가 정말 막혀 있는지 — 스텁이 호출되면 죽어야 한다
import importlib.util
spec=importlib.util.spec_from_file_location('rf','backend/evals/realfixture/replay.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
app=m.load_pipeline_with_fixture_adapters()
for probe in ['_FRAME_EXTRACTOR.extract', '_POSE_ESTIMATOR.estimate', '_COACH_WRITER.write']:
    obj,meth=probe.split('.'); fn=getattr(getattr(app,obj),meth)
    try:
        fn('x'); print('LEAK', probe); sys.exit(1)
    except RuntimeError: print('BLOCKED', probe)
from sunity_shared import firestore_admin as fa
try:
    fa.complete_analysis('u','a',{}); print('LEAK complete_analysis'); sys.exit(1)
except RuntimeError: print('BLOCKED complete_analysis')
"
git diff $BASE --exit-code -- backend/functions backend/shared app/src && echo "PROD-DIFF-0"
    </automated>
  </verify>
  <done>
`--recon-only` 가 fixture 4건 · record 14건에 대해 MATCH/MISMATCH/MISSING/EXTRA 표를
출력하고 exit code 를 정직하게 낸다(전건 MATCH 만 0). 어댑터·쓰기 스텁 4종이 호출 시
RuntimeError 로 죽는 것이 실행으로 확인됨. pytest FAILED/ERROR node ID diff 0.
프로덕션 코드 diff 0. **Task 3 이전 커밋 완료.**

착수 시점 pytest 기준선을 `/tmp/czw-before.txt` 에 먼저 캡처해 둘 것:
`PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 |
grep -E '^(FAILED|ERROR)' | sort > /tmp/czw-before.txt`
(수치 하드코딩 금지 — 게이트는 diff 다. 2026-08-02 참고값 59 failed / 3802 passed.)
  </done>
</task>

<task type="auto">
  <name>Task 3: atFrameIdx 실물 판정 + 카드 프레임 산출</name>
  <files>
backend/evals/realfixture/replay.py
.planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json
  </files>
  <action>
RECON 게이트가 통과(또는 record 단위로 부분 통과)한 fixture에 한해 판정을 낸다.

**(a) record 각인** — `app._attach_translation_emission(result, mode=..., motion_id=...,
prev_doc=None, uid=..., analysis_id=..., measured_at=measured_at)` 를 호출해 record 에
`atFrameIdx`/`atVideoSec` 을 각인시킨다. production 과 같은 함수·같은 인자다.

**(b) 카드 프레임** — `fault_zoom.criterion_units_from_records(...)` 로 unit 을 만들고
`fault_zoom.build_fault_zoom_comparisons(...)` 를 호출한다. 인자 구성 규칙:
 · `user_report` / `ref_report` = 저장된 `keypointReport` / 기준 `keypointReport` **원본**.
 · `frames_fps` = MANIFEST `studentAnglesFps`, `dtw_ref_fps` = production 이 쓰는 값
   (`app.py:3588` 이 `_pipeline_frame_fps()`, `app.py:5594` 가 기준 `keypointReport.fps`).
   **하네스가 fps 를 계산하지 않는다.**
 · `dtw_match` = Task 2 의 `match`.
 · `user_frame_candidates` / `ref_frame_candidates` = 저장
   `visionVeto.windowMedianAngleDeltas.sourceFrameIndices.{user,reference}` — production 이
   주는 형상 그대로(power-spin 실측 user `[17,18,19,20,21]`).
 · `user_frames` / `ref_frames` = **합성 프레임 배열**. 길이는 fixture 에서 파생하고
   (`app.py:3305 _build_fault_zoom_comparisons` 가 production 에서 어떤 배열을 넘기는지
   소스로 확인해 그 관계를 따를 것 — 추측 금지), 프레임마다 1픽셀을 흔들어 **선택된
   프레임이 갈렸는지 픽셀로 구분 가능**하게 한다(`sweep_record_moment._load_frames` 선례).
   길이 관계를 소스에서 확정할 수 없으면 그 fixture 를 `CARD: BLOCKED(사유)` 로 남긴다.

**PNG 는 판정 근거가 아니다.** 합성 픽셀이므로 사진의 내용은 무의미하다. `replay_out.json`
에 PNG 바이트를 넣지 말고 sha256 만 남긴다(프레임 선택이 갈렸다는 방증). 사진이 실제로
다른 순간인지는 **B 단계**다 — 산출물과 SUMMARY 양쪽에 이 한계를 적는다.

**(c) `replay_out.json` 산출** — fixture 마다:
 · `recon`: record 단위 MATCH 표 (Task 2 산출 재사용)
 · `records[]`: criterion / measuredValue / points / **atFrameIdx** / atVideoSec
 · `distinctAtFrameIdx`: 순간 필드를 가진 record 들의 서로 다른 값 개수 / 그 record 수
 · `failClosed[]`: 순간이 비어 있는 record 와 그 criterion (`split_angle` 2건은 gbk 설계상
   여기 들어와야 정상)
 · `cards[]`: criterion / tier / **userFrameIdx** / refFrameIdx / **atMatched** / png_sha256
 · `storedCardFrames`: MANIFEST 정답지의 저장 카드 프레임 (대조용 — power-spin 38 ×4 등)
 · `atMatchedRatio`: 실 데이터에서의 true 비율 (합성 100% 와 **반드시 나란히** 적는다)

**(d) 판정 문장** — 러너가 stdout 에 fixture 별로 한 줄씩 낸다. 두 갈래를 미리 정해 둔다:
 · `distinctAtFrameIdx` 가 record 수와 같으면: 갈렸다.
 · 하나로 뭉치면: **"260801-gbk 는 실 데이터에서 실패"** 라고 그대로 적는다.
   그것도 정상 산출이다. **게이트를 통과시키려고 판정을 무르게 만들지 말 것** —
   판정은 exit code 에 영향을 주지 않는다(Task 2 규약).
 · elbow-twist(record 8, 전부 `angle_vs_reference__*`, 관절 8개 상이)가 판정의
   무게중심임을 출력에 명시한다.

산출물 경로는 `.planning/quick/260802-czw-.../replay_out.json` 고정 + `--out` 으로 override
가능. Firestore 쓰기 0(Task 2 스텁이 구조로 보장).
  </action>
  <verify>
    <automated>
set -o pipefail
BASE=$(git rev-parse HEAD)
backend/.venv/bin/python backend/evals/realfixture/replay.py \
  --out .planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json
backend/.venv/bin/python -c "
import json
p='.planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json'
d=json.load(open(p))
for f in d['fixtures']:
    recs=f['records']; withm=[r for r in recs if r.get('atFrameIdx') is not None]
    print(f\"{f['analysisId']:34} recon={f['reconVerdict']:8} records={len(recs)} \"
          f\"moment={len(withm)} distinct={f['distinctAtFrameIdx']} \"
          f\"cards={[c['userFrameIdx'] for c in f['cards']]} \"
          f\"stored={f['storedCardFrames']} atMatched={f['atMatchedRatio']}\")
    assert 'failClosed' in f and 'atMatchedRatio' in f, f['analysisId']
    assert all('png_sha256' in c for c in f['cards']), 'PNG sha256 누락'
    assert not any('png' in c for c in f['cards']), 'PNG 바이트가 산출물에 들어갔다'
et=[f for f in d['fixtures'] if 'elbowtwist' in f['analysisId']][0]
print('WEIGHT-CENTER elbow-twist:', et['distinctAtFrameIdx'], '/', len(et['records']))
print('VERDICT:', d['verdict'])
"
# 재실행 결정성 — 두 번째 실행이 byte 동일해야 한다
backend/.venv/bin/python backend/evals/realfixture/replay.py --out /tmp/czw-replay2.json
diff <(backend/.venv/bin/python -c "import json;print(json.dumps(json.load(open('.planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json')),sort_keys=True))") \
     <(backend/.venv/bin/python -c "import json;print(json.dumps(json.load(open('/tmp/czw-replay2.json')),sort_keys=True))") \
  && echo "DETERMINISTIC-OK"
PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 \
  | grep -E '^(FAILED|ERROR)' | sort > /tmp/czw-after3.txt
diff /tmp/czw-before.txt /tmp/czw-after3.txt && echo "PYTEST-NODEID-DIFF-0"
git diff $BASE --exit-code -- backend/functions backend/shared app/src && echo "PROD-DIFF-0"
    </automated>
  </verify>
  <done>
`replay_out.json` 이 fixture 4건에 대해 record 별 `atFrameIdx` · `distinctAtFrameIdx` ·
카드 `userFrameIdx` · `atMatched` 비율 · `failClosed` 목록을 담고 있고, 저장 카드 프레임
정답지(38 ×4 / 16 ×2 / 104 / 144 ×5)와 나란히 대조된다. elbow-twist 8 record 판정이
출력에 명시됨. 재실행 결정성 확인(2회 산출 동일). PNG 바이트 미포함(sha256 만).
pytest node ID diff 0, 프로덕션 코드 diff 0.

**판정이 "뭉쳤다"로 나와도 done 이다** — 이 태스크의 산출물은 PASS 가 아니라 판정이다.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore(운영 데이터) → 리포 커밋 | 운영 doc 내용이 git 이력에 영구 박제된다 |
| 러너 → Firestore / S3 | 검증 하네스가 운영 데이터를 변형할 수 있는 경로 |
| 러너 산출물 → 판정 문장 | 게이트를 사후에 무르게 만들어 자기기만이 가능한 경로 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-czw-01 | Information Disclosure | `pull-real-fixtures.mjs` → fixtures/*.json | mitigate | presigned URL 이 `X-Amz-Credential=AKIA…` 로 AWS access key ID 를 품는다. **값 기준 재귀 strip**(`X-Amz-Signature` 포함 문자열) + 커밋 전 `grep -rl 'AKIA'` = 0 게이트. 키 이름 화이트리스트가 아니라 값 규칙이라 새 URL 필드도 자동 포착 |
| T-czw-02 | Tampering | replay.py → firestore_admin / `_s3` | mitigate | 쓰기 함수(`complete_analysis`/`fail_analysis`/`update_analysis_status`/`store_*`/`record_*`)와 `_s3` 를 **호출 시 RuntimeError** 스텁으로 교체. Task 2 verify 가 실제 호출로 차단을 실증(가정 아님) |
| T-czw-03 | Repudiation | RECON 게이트 ↔ 판정 | mitigate | RECON 게이트를 **판정 구현 전 별도 커밋**(Task 2 → Task 3). 판정 숫자를 보고 게이트를 완화한 경로가 커밋 순서로 반증된다. 판정은 exit code 에 영향 0 |
| T-czw-04 | Information Disclosure | fixtures 내 uid·fileName | accept | uid 는 Firebase 가명 식별자, 대상은 belle 자신의 테스트 계정이고 영상 키는 `fixtures/phase15/*` 고정 자산이다. 인물 이미지·실명 0 (PNG 바이트 미커밋 — [[home-dir-is-git-repo-pii-hazard]] 정합) |
| T-czw-05 | Denial of Service | GPU/Gemini 오호출 | mitigate | `_POSE_ESTIMATOR`/`_RTMW_ENGINE`/`_COACH_WRITER`/`_FRAME_EXTRACTOR.extract` 전부 호출 시 죽는 스텁. Gemini 어댑터는 이 경로에서 생성되지 않는다 |
| T-czw-SC | Tampering | npm/pip 설치 | mitigate | **신규 의존성 0.** Node 는 기존 `app/node_modules/firebase-admin`, Python 은 기존 `backend/.venv`(numpy/PIL/yaml). 설치 커맨드가 등장하면 이 플랜 위반 |
</threat_model>

<verification>
**환경**
 · 백엔드 테스트는 반드시 `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q
   backend/tests`. `cd backend && .venv/bin/python -m pytest` 는 수집에서 중단돼 0개 실행하고
   거짓 통과한다.
 · 기준선은 착수 시점에 `/tmp/czw-before.txt` 로 캡처하고 **diff 로만** 비교(수치 하드코딩
   금지). 2026-08-02 참고값 = 59 failed / 3802 passed.
 · `git diff --exit-code` 는 `git add` 한 번에 무력화된다 → 각 태스크가 `BASE=$(git rev-parse
   HEAD)` 를 먼저 고정하고 `git diff $BASE` 로 비교.
 · 파이프가 있는 게이트는 `set -o pipefail`.
 · 앱 무접촉 — `app/src` diff 0. `app/scripts/` 신규 1파일만 추가(Node 박제 스크립트).

**부정 게이트 (이 사이클이 안 한 것을 증명)**
 · Pod/GPU 미기동 · Gemini 미호출 · Firestore 쓰기 0 — 스텁이 호출 시 죽는 것을 실행으로 확인.
 · `sweep_record_moment.py` 삭제 0 (헤더 주석 1줄 추가만).

**하네스 자체가 거짓말하지 못하게 하는 것**
 · RECON 게이트 = 재현본 ↔ 저장 records 대조. **불일치하면 그 fixture 의 판정을 내지 않는다.**
 · 정답지는 MANIFEST 에 박제 — Firestore doc 이 나중에 덮어써져도 대조 대상은 리포에 남는다.
 · 재실행 결정성 — 두 번째 실행 산출물이 첫 번째와 동일.
</verification>

<success_criteria>
1. `backend/evals/realfixture/fixtures/` 에 실 doc 8건 + MANIFEST 가 커밋돼 있고 presigned
   URL·AWS key ID 잔재 0. 총 용량이 MANIFEST 에 실측 기록됨(예상 ~3.0 MB).
2. `replay.py --recon-only` 가 record 14건에 대해 MATCH/MISMATCH/MISSING/EXTRA 를 표로 내고,
   전건 MATCH 일 때만 exit 0.
3. `replay_out.json` 에 fixture 별 `atFrameIdx` 분포 · `distinctAtFrameIdx` · 카드
   `userFrameIdx` · `atMatched` 비율 · `failClosed` 가 저장 정답지와 나란히 담겨 있다.
4. **`atFrameIdx` 가 실 데이터에서 갈리는지에 대한 판정이 나왔다.** 갈렸든 뭉쳤든
   판정 문장이 SUMMARY 최상단에 있다 — 뭉쳤으면 "quick-260801-gbk 는 실 데이터에서 실패"로
   그대로 적는다.
5. GPU 0 · Gemini 0 · Pod 0 · Firestore 쓰기 0 이 **실행 결과로** 증명됐다.
6. 프로덕션 코드 diff 0. pytest FAILED/ERROR node ID diff 0. 신규 의존성 0.
7. SUMMARY 에 **재보지 않은 것**이 명시돼 있다: PNG 픽셀 내용(합성 프레임) · 실기기 렌더 ·
   음성 큐 · mode3 경로 · Pod 재분석 후 실제 doc 의 값. 그리고 **B 단계 범위**(S3 영상 →
   프레임 추출 → 실제 PNG 렌더 → 사진이 다른 순간인지 육안·바이트 확인)가 다음 사이클로 적혀 있다.
</success_criteria>

<output>
Create `.planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/260802-czw-SUMMARY.md` when done
</output>
