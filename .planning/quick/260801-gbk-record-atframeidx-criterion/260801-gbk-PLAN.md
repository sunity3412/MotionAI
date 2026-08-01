---
phase: quick-260801-gbk
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/motiondtw.py
  - backend/shared/python/sunity_shared/analysis/dimensions.py
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/shared/python/sunity_shared/models.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_deduction_engine.py
  - backend/tests/test_record_measured_at.py
  - backend/tests/test_fault_zoom_record_moment.py
  - docs/contract.md
  - app/src/types/analysis.ts
  - app/src/lib/userAnalyses.ts
  - app/src/lib/deductionSheet.ts
  - app/src/lib/__tests__/deductionSheet.test.ts
autonomous: true
requirements: [QUICK-260801-GBK]

must_haves:
  truths:
    - "감점 record 마다 '이 값을 어느 프레임에서 쟀는가'가 doc 에 남는다 (측정 가능한 criterion 한정)."
    - "확대비교 카드가 카드마다 서로 다른 프레임을 쓴다 — 같은 분석의 두 카드가 같은 프레임이면 그 두 감점의 측정 순간이 실제로 같을 때뿐이다."
    - "순간을 신뢰 있게 못 정하는 감점(reach·whole-score fallback)은 필드가 비고, 그 카드는 지금과 동일하게 동작한다."
    - "overallScore·deductionBreakdown.final·record 의 points/measuredValue/deviation 이 이 변경 전후로 1도 움직이지 않는다."
    - "'위 사진은 그 값을 잰 순간(N.N초)이에요' 문장이 record 자신의 측정 초에서 나오고, 근거가 없으면 문장 자체가 사라진다."
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/motiondtw.py"
      provides: "DTW path 대표 프레임 산출 (per_joint_deviation 무접촉 sibling)"
      contains: "per_joint_representative_frames"
    - path: "backend/shared/python/sunity_shared/analysis/dimensions.py"
      provides: "_select_window 공유 window 안 대표 프레임 산출"
      contains: "representative_frame_in_window"
    - path: "backend/functions/pipeline/app.py"
      provides: "criterion 별 측정 순간 산출(measured_at_out) + record 각인 + mode3 unit 미러"
      contains: "measured_at_out"
    - path: "backend/shared/python/sunity_shared/models.py"
      provides: "atFrameIdx/atVideoSec 계약 키 집합"
      contains: "DEDUCTION_RECORD_MOMENT_KEYS"
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "unit 의 자기 순간을 프레임 선택 앵커로 소비"
      contains: "at_frame_idx"
    - path: "app/src/types/analysis.ts"
      provides: "DeductionRecord.atFrameIdx?/atVideoSec? 계약 미러"
      contains: "atFrameIdx"
    - path: "app/src/lib/deductionSheet.ts"
      provides: "basis 문장의 초를 record 측정 순간에 결속 (fail-closed)"
      contains: "atVideoSec"
    - path: ".planning/quick/260801-gbk-record-atframeidx-criterion/sweep_record_moment.py"
      provides: "등재 10동작 일반화 스위프 (GPU 0)"
      min_lines: 120
  key_links:
    - from: "backend/functions/pipeline/app.py::_build_deduction_measured_deviations"
      to: "backend/functions/pipeline/app.py::_attach_translation_emission"
      via: "measured_at out-param → record dict 각인"
      pattern: "measured_at"
    - from: "backend/functions/pipeline/app.py::_attach_translation_emission"
      to: "backend/shared/python/sunity_shared/analysis/fault_zoom.py::criterion_units_from_records"
      via: "record['atFrameIdx'] → unit['at_frame_idx']"
      pattern: "atFrameIdx"
    - from: "backend/shared/python/sunity_shared/analysis/fault_zoom.py::build_fault_zoom_comparisons"
      to: "backend/shared/python/sunity_shared/analysis/fault_zoom.py::_matched_ref_frame"
      via: "unit 앵커 ±W 후보 → 기준 프레임 DTW 대응"
      pattern: "_matched_ref_frame"
    - from: "app/src/lib/deductionSheet.ts"
      to: "app/src/types/analysis.ts::DeductionRecord"
      via: "rec.atVideoSec → basis 문장"
      pattern: "atVideoSec"
---

<objective>
감점 record 마다 **그 감점을 잰 순간**을 방출하고, 확대비교 카드가 자기 순간을 쓰게 한다.

지금은 모든 카드·마커·자막·음성이 `worst_seconds = vision_veto.worst_pose_timestamp` 라는
**한 시각**에서 잘린다. 그 시각의 정의는 "Gemini key_moments 중 hold > peak > 전체 우선순위로
가장 이른 시각"(`vision_veto.py:1012-1049`) — **동작 국면의 시각이지 감점이 난 시각이 아니다.**
그런데 앱은 사진 밑에 "위 사진은 그 값을 잰 순간(N.N초)이에요"(`deductionSheet.ts:544`)라고 적는다.
데이터가 뒷받침하지 않는 문장이다.

Purpose: 킵업 카드 2장이 둘 다 `userFrameIdx=16`, 파워스핀 4장 전부 38, 엘보 5장 전부 144 인
증상의 단일 원인을 제거한다. 큐 창이 완전히 동일해져 `activeCue` tie-break 에서 두 번째 음성이
발화되지 않는 파생 증상도 원인 소멸로 함께 닫힌다.

Output: record 의 `atFrameIdx`/`atVideoSec` scalar 2개(측정 가능한 criterion 한정) + 그것을
프레임 앵커로 쓰는 fault_zoom 배선 + 그 초에 결속된 앱 basis 문장. **채점 무접촉.**
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/CLAUDE.md
@app/AGENTS.md
@.planning/STATE.md

핵심 소스 (읽기 순서):
@backend/functions/pipeline/app.py
@backend/shared/python/sunity_shared/analysis/fault_zoom.py
@backend/shared/python/sunity_shared/analysis/features.py
@backend/shared/python/sunity_shared/analysis/motiondtw.py
@backend/shared/python/sunity_shared/analysis/dimensions.py
@backend/shared/python/sunity_shared/models.py
@app/src/types/analysis.ts
@app/src/lib/deductionSheet.ts
@docs/contract.md
</context>

<design_decisions>

오케스트레이터가 답을 정해두지 않은 열린 질문에 대한 결정과 근거. 실행자는 이 절을 스펙으로 삼는다.

**D-gbk-01 — 필드 이름·단위·도메인: `atFrameIdx`(int) + `atVideoSec`(float), 학생 9fps angles 도메인.**

`atFrameIdx` 는 **학생 angles 행 인덱스 = 9fps 추출 프레임 배열 인덱스**다. 이 도메인을 고른
이유는 세 가지다. ① 감점을 만드는 모든 집계(`angles` 행렬, `windowMedianAngleDeltas.
sourceFrameIndices.user`, `dimensions._select_window`, `features.split_angle_series`)가 전부
이 한 도메인에 산다 — 변환 없이 산출된다. ② `fault_zoom` 의 기존 프레임 override
(`user_frame_idx`, `user_frame_candidates`)가 정확히 이 도메인을 받는다(`fault_zoom.py:2322-2325`)
— 새 파이프가 아니라 있는 파이프에 값을 흘리는 일이 된다. ③ 학생 `keypointReport` 는
`build_keypoint_report(pose_frames, fps=9.0)`(`app.py:6085`)로 만들어져 rep 공간과 9fps 공간이
학생 측에서는 일치한다 — 그러나 **이름은 측정 도메인으로 붙인다.** rep 인덱스 이름을 붙이면
기준 측(phase4_v1 18fps)과 헷갈려 F-3 계열 버그가 재발한다.

`atVideoSec = atFrameIdx / frames_fps` 를 **함께 방출한다.** 초를 앱이 재계산하게 두지 않는
이유는 contract.md §11.8 이 이미 박제한 F-3 근본원인("앱이 rep 인덱스를 rep fps 로 나눠 초를
추정")과 같다. fps 는 `_pipeline_frame_fps()`(`app.py:4541`) 단일 출처에서 읽는다 — **리터럴 9.0
금지.**

**D-gbk-02 — 기준(정은지) 측 순간은 방출하지 않는다.**

`fault_zoom` 은 이미 학생 프레임에서 기준 프레임을 파생한다(`_matched_ref_frame` → `select_pose_
matched_ref_frame`). record 가 독립적인 기준 순간을 들고 오면 **경쟁하는 두 번째 출처**가 생겨,
카드 안에서 학생과 기준이 다른 순간을 보여주던 바로 그 버그(`fault_zoom.py:2495-2501` 가
고친 것)를 되살린다. record 는 **학생 측 순간 하나만** 나른다.

**D-gbk-03 — 대표 프레임은 언제나 "집계값에 가장 가까운 프레임". argmax 금지.**

`motiondtw.per_joint_deviation` docstring(193-220)이 박제한 사실: RTMW 가 inverted/occluded 폴
자세에서 인접 프레임 간 10°+ jitter 를 만들고 p99 이 35~50° 다. 평균을 버리고 median 을 쓰는
이유가 정확히 그것이다. **편차 argmax 프레임을 고르면 그 jitter 프레임을 "여기가 감점 부분"
이라고 확대해 보여주게 된다 — 지금보다 나빠진다.** 그래서 규칙은 하나로 통일한다:

> 그 record 가 **실제로 보고한 집계값**에, 자기 per-frame 값이 **가장 가까운** 프레임.

criterion 별 산출 (집계가 다르므로 순간도 각자의 집계에서 파생한다):

| criterion | 집계 (record 가 보고하는 값) | 순간 |
|---|---|---|
| `angle_vs_reference__{jk}` — Gemini pointed | `windowMedianAngleDeltas.deltas[].student_deg` = worst-window 안 학생 각도의 median | `sourceFrameIndices.user` 안에서 `abs(angles[t][j] - student_deg)` 최소 프레임 |
| `angle_vs_reference__{jk}` — Gemini silent | `per_joint_deviation` = DTW path 전체 median of `abs(Δ)` | `match.start + path[k*][0]`, `k*` = `abs(diffs[k][j] - median_j)` 최소 |
| `leg_extension` / `arm_extension` | 관절쌍 중 max 인 관절의 `max(0, 180 - mean_over_window)` | 그 **argmax 관절**에 대해 `_select_window` 구간 안에서 per-frame 부족분이 집계값에 가장 가까운 프레임 |
| `line` | 양수 부족분 EXTEND 관절들의 평균 | 같은 관절 집합의 per-frame 평균 부족분이 집계값에 가장 가까운 프레임 |
| `split_angle` | `max(0, 기준 max-split - 학생 max-split)` | 학생 **최대 벌림 프레임** — `features.max_split()` 이 이미 `(값, idx)` 를 반환하고 `app.py:5313` 이 idx 를 버리고 있다. 원래부터 단일 프레임이라 대표 선택 불필요 |
| `body_relative_reach` | notch 부족분 | **fail-closed — 필드 없음.** notches 에 시계열이 없다 |
| `dimension_overall_fallback` | whole-score passthrough | **fail-closed — 필드 없음.** 특정 순간이 없는 record 다 |

pointed 경로는 **median 을 재계산하지 않는다** — `features._delta_entry`(185)가 이미 emit 한
`student_deg` 를 그대로 읽는다. 재계산이 없으므로 drift 가 원리적으로 불가능하다.

**D-gbk-04 — seam: tally **뒤**에서 각인한다. `deduction_engine.py` 는 diff 0.**

채점 엔진을 건드리지 않는다. 측정 순간은 `_build_deduction_measured_deviations` 의
**out-param**(`seed_audit_out` 과 정확히 같은 선례 — `app.py:2360`/`2511`)으로 빠져나와,
`_attach_translation_emission`(`app.py:4890-4914`)에서 record dict 에 각인된다. 그 함수의 계약은
이미 "기존 키 무변경(setdefault), 채점 무접촉"(4876-4877)이다.

이 선택으로 **불변식 1이 테스트가 아니라 구조로 증명된다** — points 를 계산하는 코드가 이 값을
볼 수 없다. 게이트는 `git diff --exit-code -- backend/shared/python/sunity_shared/analysis/
deduction_engine.py` 가 0 을 반환하는 것이다.

**D-gbk-05 — 큐 창 겹침·`activeCue` tie-break 는 이 플랜 범위 밖. 명시적으로 남긴다.**

"두 카드의 큐 창이 완전히 동일해져 두 번째 음성이 영원히 발화되지 않는다"는 **동일 프레임의
결과**이지 tie-break 로직의 결함이 아니다. 프레임이 갈리면 창이 갈리고 증상이 사라진다.
이미 사라진 원인 위에 tie-break 보정을 얹으면 두 번째 수리가 되어 회귀 표면만 넓힌다.
`CUE_WINDOW_SEC=1.6` 이라 0.3초 차이면 창은 여전히 겹치지만, `activeCue` 는 시작이 늦은 큐를
고르므로 이른 큐도 자기 진입 구간을 갖는다.

남은 "창이 0.089초에 열려 플레이어 준비 전에 영상을 멈춘다"는 **재생 준비 문제**이지 프레임
문제가 아니다 — 진짜로 이른 감점에서는 이 플랜 이후에도 발생한다. F-6 자체 사이클로 남긴다.
**`cueTrack.ts` / `VideoCompare.tsx` 무접촉.**

**D-gbk-06 — 앱의 "잰 순간" 문장은 record 에 결속한다 (fail-closed).**

`deductionSheet.ts:529`/`544` 는 지금 그 문장의 초를 `blockZoom.userVideoSec`(카드의 **표시**
프레임)에서 가져온다. 출처를 `rec.atVideoSec`(그 record **자신의 측정 순간**)로 바꾼다.
부재(fail-closed criterion / legacy doc)면 기존 `if (blockUserSecLabel)` 게이트가 절을 통째로
생략한다 — 앱이 근거 없는 단정을 그만둔다. 새 카피 0, 한 줄 출처 교체.

**앱 변경은 0 이 아니다 — 3곳** (오케스트레이터의 "확인할 것"에 대한 답):
1. `app/src/types/analysis.ts` — 계약 3자 미러는 강제다. `backend/tests/test_deduction_engine.py::
   test_contract_lockstep` 이 TS 필드 집합과 `models.DEDUCTION_RECORD_*_KEYS` 합집합의 동등을
   검사하므로, TS 를 빼면 **테스트가 깨진다.**
2. `app/src/lib/userAnalyses.ts:368` — 방어적 정규화 관례상 신규 2키도 정규화한다.
3. `app/src/lib/deductionSheet.ts` — D-gbk-06.

`cueTrack.ts` / `VideoCompare.tsx` / `result.tsx` = **0 diff.** 큐 창은 `zoom.userFrameIdx` 로
만들어지므로 카드가 각자 프레임을 잡는 순간 창도 자동으로 갈린다.
</design_decisions>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 감점마다 자기 순간을 산출해 record 에 각인 (산출 + 계약 3자)</name>
  <files>
backend/shared/python/sunity_shared/analysis/motiondtw.py,
backend/shared/python/sunity_shared/analysis/dimensions.py,
backend/shared/python/sunity_shared/models.py,
backend/functions/pipeline/app.py,
backend/tests/test_record_measured_at.py,
backend/tests/test_deduction_engine.py,
docs/contract.md,
app/src/types/analysis.ts
  </files>
  <behavior>
    - pointed 관절: `sourceFrameIndices.user` 안에서 `student_deg` 에 가장 가까운 프레임을 고른다. 그 window 밖 프레임은 절대 고르지 않는다.
    - silent 관절: DTW path 대표 프레임이 `match.start + path[k][0]` 로 절대 인덱스가 되고, 같은 함수가 낸 median 이 `per_joint_deviation` 과 정확히 일치한다.
    - jitter 방어: 한 프레임만 편차가 폭주하는 합성 시계열에서 대표 프레임이 그 폭주 프레임이 **아니어야** 한다 (argmax 회귀 가드).
    - `split_angle`: `max_split` 이 돌려준 idx 가 그대로 순간이 된다.
    - `leg_extension`: 좌/우 무릎 중 부족분이 큰 쪽이 집계값을 만들고, 순간은 그 관절의 window 안 대표 프레임이다.
    - fail-closed: `body_relative_reach` / `dimension_overall_fallback` record 에는 `atFrameIdx` 키가 아예 없다.
    - 각인 additive: `_attach_translation_emission` 전후로 record 의 필수 11키 + cap 2키 + track 값이 완전히 동일하다.
    - 하위호환: `measured_at` 이 빈 dict 여도 크래시 0, 방출 record 는 종전과 동일 형상.
  </behavior>
  <action>
D-gbk-01/02/03/04 를 구현한다. 순수 helper 를 먼저 만들고, 파이프라인이 그것을 호출해
out-param 으로 순간을 실어 나른 뒤 tally 뒤에서 record 에 각인한다.

**(1) `motiondtw.py` — sibling 함수 추가. `per_joint_deviation` 본체는 한 글자도 고치지 않는다.**
`per_joint_representative_frames(path, A_user_seg, A_ref, start)` 를 추가한다. `per_joint_deviation`
과 동일한 `diffs = (len(path), J)` 순회로 관절별 median 을 구한 뒤, 관절 j 마다
`abs(diffs[:, j] - median_j)` 최소인 path 스텝 k 를 골라 `start + path[k][0]` (절대 9fps 학생
프레임)을 돌려준다. 반환은 `dict[int, int]` (관절 인덱스 → 절대 프레임). `path` 빈 경우 빈 dict.
docstring 에 quick-260801-gbk 인용 + "argmax 가 아니라 median 근접인 이유"를 이 파일 193-220 의
jitter 근거로 적는다. median 이 짝수 길이에서 보간값이라 표본과 정확히 일치하지 않을 수 있으므로
**"가장 가까운"이 옳은 표현**임을 명시한다.

**(2) `dimensions.py` — `_select_window` 를 공유하는 대표 프레임 helper 추가.**
`representative_frame_in_window(angles, profile, per_frame_values_fn, target)` 대신, 서명 단순화를
위해 두 함수를 둔다. `extension_representative_frame(angles, profile, joint_key, target_deficit)` —
`_select_window(angles, profile)` 가 돌려주는 `(s, e)` 구간 안에서 `max(0, _FULL_EXTENSION_DEG -
angles[t][j])` 가 `target_deficit` 에 가장 가까운 t 를 찾아 절대 인덱스로 돌려준다.
`line_representative_frame(angles, profile, joint_keys, target_deficit)` — 같은 구간 안에서
`joint_keys` 에 대한 per-frame 부족분 평균이 target 에 가장 가까운 t. 둘 다 유한값 없으면 None.
**windowing 은 반드시 `_select_window` 를 통해서만** — 이 파일 286-297 이 박제한 "drift 방지,
전부 이 함수 하나만 호출" 규율이다. 새 windowing 상수 0.

**(3) `app.py::_build_deduction_measured_deviations` — `measured_at_out` out-param.**
`seed_audit_out` 과 같은 자리·같은 방식으로 `measured_at_out=None` 키워드를 추가한다.
docstring 에 "md(점수 substrate)는 여기서 절대 mutate 하지 않는다 — 순간은 out-param 에만
기록된다"를 `seed_audit_out` 문구(2368-2369)와 같은 취지로 적는다. 값 형상은
`{criterion_id: {"frame_idx": int, "video_sec": float}}`.

criterion 별 채움:
- extension(`leg_extension`/`arm_extension`): `_max_dev` 가 max 를 고를 때 **어느 관절이 이겼는지**를
  같이 반환하도록 지역 helper 를 확장하고(반환 형상만 바꾸고 md 값은 불변), 그 관절로
  `extension_representative_frame` 호출.
- `line`: `extend_devs` 를 만들 때 쓴 관절 키 목록을 보관해 `line_representative_frame` 에 넘긴다.
- `split_angle`: 새 키워드 `split_peak_frame_idx=None` 을 받아 그대로 쓴다(대표 선택 없음).
- `angle_vs_reference__{jk}` window 경로: `wm_by_joint` 를 만들 때 그 entry 의 `student_deg` 도 같이
  보관하고, `sourceFrameIndices.user` 리스트 안에서 `abs(angles[t][j] - student_deg)` 최소 t 를 고른다.
  **median 재계산 금지** — emit 된 `student_deg` 를 읽는다. `student_deg` 가 없거나 비유한이면
  그 관절은 fail-closed(순간 미기록, md 는 그대로).
- `angle_vs_reference__{jk}` DTW 경로: 이미 계산 중인 `per_joint_deviation` 호출 옆에서
  `per_joint_representative_frames(path, user_seg, reference_angles, start)` 를 호출해 관절별 절대
  프레임을 얻는다.
- `_emit_reference_relative` 가 **False 를 반환한 관절**(cross-exclusion 등)은 순간도 기록하지 않는다 —
  방출된 md 키와 순간 키가 정확히 대응해야 한다.
- `video_sec` 은 `_pipeline_frame_fps()` 로 나눈다. **리터럴 9.0 금지**(4541-4548 규율).
  fps <= 0 이면 `video_sec` 생략(frame_idx 만).

**(4) `app.py::_process` — 배선.**
`split_deficit_deg = None` 초기화(5245) 옆에 `split_peak_frame_idx = None` 과 `measured_at: dict = {}`
를 같은 자리에서 초기화한다(mode3/legacy 에서도 이름이 존재해야 6287 호출부가 안전).
5313 의 `student_split, _ = max_split(...)` 에서 버려지는 idx 를 `split_peak_frame_idx` 로 받는다.
5779 의 builder 호출에 `split_peak_frame_idx=`, `measured_at_out=measured_at` 을 넘긴다.

**(5) `app.py::_attach_translation_emission` — 각인.**
`measured_at: dict | None = None` 키워드를 추가하고, 6287 호출부에서 `measured_at=measured_at` 을
넘긴다. record 루프(4891-4914) 안에서 `criterion` 으로 조회해 `rec.setdefault("atFrameIdx", ...)`,
`rec.setdefault("atVideoSec", ...)` 로만 넣는다 — **기존 키 절대 무변경**. 값이 없으면 키를 만들지
않는다(fail-closed). `atFrameIdx` 는 `int`, `atVideoSec` 은 `float` 로 캐스팅해 Firestore flat scalar
제약을 통과시킨다. 중첩 배열·dict 금지(D-gbk 불변식 5).

**(6) `models.py` — 계약 키.**
`DEDUCTION_RECORD_MOMENT_KEYS = ("atFrameIdx", "atVideoSec")` 를 `DEDUCTION_RECORD_EXTENSION_KEYS`
아래에 추가하고, 기존 3집합과 **disjoint** 임을 주석에 명시한다. 주석에 fail-closed 조건(reach·
whole-score fallback 은 부재)과 도메인(학생 9fps angles, rep 아님)을 적는다.

**(7) `test_deduction_engine.py::test_contract_lockstep` 확장.**
지금 3-set 합집합을 TS 필드 집합과 비교하는 부분을 4-set 으로 넓힌다. TS 쪽 주석은
`analysis.ts:710-711` 이 경고한 대로 **word-colon 패턴과 중괄호를 넣지 않는다** — 그 regex 필드
추출과 충돌한다.

**(8) `app/src/types/analysis.ts` + `docs/contract.md` §10.2.**
`DeductionRecord` 에 `atFrameIdx?: number;` / `atVideoSec?: number;` 를 additive optional 로 추가.
주석에 (a) 학생 9fps angles 도메인이고 `FaultZoomComparison.userFrameIdx`(rep 공간)와 **다른 축**
이라는 것, (b) `atVideoSec` 을 `atFrameIdx` 나 rep fps 로 재계산하지 말 것(§11.8 F-3 교훈),
(c) 부재 = 순간을 신뢰 있게 못 정한 criterion 또는 legacy doc 임을 적는다. contract.md 에는 위
D-gbk-03 표(criterion → 집계 → 순간)를 그대로 옮겨 근거를 박제한다.

**(9) 테스트 `backend/tests/test_record_measured_at.py` (신규).**
`<behavior>` 8항목을 합성 각도 행렬로 검증한다. 특히 argmax 회귀 가드는 "한 프레임만 40° 폭주
+ 나머지 5°" 시계열에서 대표 프레임이 폭주 프레임이 아님을 단정한다. 수치 채우기 금지 —
각 테스트는 위 behavior 한 줄에 1:1 대응한다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_record_measured_at.py tests/test_deduction_engine.py -q 2>&1 | tail -5</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff --exit-code -- backend/shared/python/sunity_shared/analysis/deduction_engine.py && echo "ENGINE-DIFF-0"</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff -U0 -- backend/ | /usr/bin/grep '^+' | /usr/bin/grep -v '^+++' | /usr/bin/sed 's/^+//' | /usr/bin/grep -Ev '^[[:space:]]*#' | /usr/bin/grep -Ec '(^|[^_a-zA-Z])9\.0([^0-9]|$)' | { read n; test "$n" = "0" && echo NO-FPS-LITERAL || { echo FPS-LITERAL-ADDED=$n; exit 1; }; }</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck</automated>
  </verify>
  <done>
`atFrameIdx`/`atVideoSec` 이 measurable criterion 5종(angle_vs_reference window/DTW,
leg_extension, arm_extension, line, split_angle)에서 방출되고 reach·fallback 에서는 키가 부재.
`deduction_engine.py` git diff 0. `per_joint_deviation` 반환값 불변(테스트로 단정).
계약 3자(models.py / analysis.ts / contract.md) 동시 갱신 + `test_contract_lockstep` PASS.
`npm run typecheck` clean.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 확대비교 카드가 자기 순간을 프레임 앵커로 쓰게 배선 (소비 + 10동작 일반화)</name>
  <files>
backend/shared/python/sunity_shared/analysis/fault_zoom.py,
backend/functions/pipeline/app.py,
backend/tests/test_fault_zoom_record_moment.py,
.planning/quick/260801-gbk-record-atframeidx-criterion/sweep_record_moment.py
  </files>
  <behavior>
    - record 마다 다른 `atFrameIdx` 를 가진 breakdown 을 넣으면 카드마다 `userFrameIdx` 가 서로 다르다.
    - 두 record 의 `atFrameIdx` 가 실제로 같으면 카드도 같은 프레임 — 인위적 분산 주입 없음.
    - `atFrameIdx` 없는 unit 은 종전 경로와 **byte-동일** 산출 (fail-closed 무회귀).
    - 앵커 ±W 안에서 confidence 선택이 여전히 작동한다 — 앵커 프레임 keypoint 가 붕괴돼 있으면 창 안의 더 나은 프레임이 선택된다.
    - 기준 프레임은 여전히 DTW 대응에서 나온다 — record 는 기준 순간을 나르지 않는다(D-gbk-02).
    - DTW 대응이 한 후보라도 실패하면 합성 후보 전체를 버리고 기존 경로로 떨어진다(fail-closed).
    - `atVideoSec`/`userVideoSec` 이 서로 다른 축을 가리키지 않는다 — 앵커가 채택된 카드에서 두 값의 차이가 프레임 1개 미만.
  </behavior>
  <action>
D-gbk-02 를 지키면서, record 의 순간을 **프레임 앵커**로 소비한다. 하드 override 가 아니라
앵커인 이유: `app.py:3164-3166` 이 박제한 규율("측정-표시 정합은 window 안에서 유지하면서
keypoint 붕괴 프레임 회피")을 깨지 않기 위해서다. 순간 프레임의 keypoint 가 붕괴돼 있으면
그 프레임을 확대해봐야 오도만 된다.

**(1) `fault_zoom.criterion_units_from_records` — 순간을 unit 에 실어 나른다.**
반환 항목에 `at_frame_idx` 를 추가한다: `rec.get("atFrameIdx")` 가 int 이고 >= 0 이면 그 값,
아니면 `None`. docstring 에 quick-260801-gbk 와 "표시 전용, 채점 무접촉 — records 는 읽기만"
(기존 171행 문장) 유지를 적는다. `_CropUnit` dataclass 에도 `at_frame_idx: int | None = None`
필드를 additive default 로 추가(기존 생성부 무수정 호환 — `criterion` 필드 선례 그대로).

**(2) `fault_zoom.build_fault_zoom_comparisons` — unit 앵커 → 후보 창.**
unit 루프(2486~) 안, 기존 candidates 블록(2506) **앞**에 지역 변수 두 개를 만든다:
`u_cands_unit = user_frame_candidates`, `r_cands_unit = ref_frame_candidates`.
`unit.at_frame_idx is not None` 이고 `dtw_match` 가 있으면 합성 후보로 교체한다:
- 학생 후보 = `at_frame_idx` ± W 를 `[0, u_n-1]` 로 clamp 후 중복 제거(순서 보존).
  **W 는 `features.window_median_angle_deltas` 의 `window` 기본값과 같은 값을 쓴다** — 새 튜닝
  상수 0. 리터럴 2 를 쓰지 말고 그 기본값을 참조하거나 모듈 상수 1개로 단일 출처화한다.
- 기준 후보 = 각 학생 후보에 대해 기존 2단 변환을 **그대로 재사용**한다:
  `_matched_ref_frame(dtw_match, u_cand, _dtw_ref_frames)` → `_to_rep_idx(r_matched, _dtw_ref_fps,
  frames_fps, r_n)`. 이 두 줄은 2452-2460 에 이미 있는 식이다 — **새 매핑 공식을 쓰지 말고 그
  코드를 helper 로 뽑아 양쪽이 공유**하게 한다(`_matched_ref_frame` 본체는 864-865 가 "수정 금지"
  라고 박제했으므로 호출만 한다).
- 하나라도 `None` 이면 합성 후보 전체를 버리고 `u_cands_unit`/`r_cands_unit` 을 원래 파라미터로
  되돌린다(fail-closed — 반쪽 대응으로 카드를 만들지 않는다).
그 아래 기존 선택 블록(2506/2553)의 `user_frame_candidates`/`ref_frame_candidates` 참조를
`u_cands_unit`/`r_cands_unit` 으로 바꾼다. **선택·pose 매칭·crop·S9 정중앙·S10 다리선·S8 각도
베이크 로직은 한 줄도 건드리지 않는다.**

**(3) `app.py` mode3 crit_units 미러.**
3340-3361 부근에서 인라인으로 만드는 `crit_units` 에도 `at_frame_idx` 를 같은 규칙으로 채운다.
mode1/mode3 두 생산자가 같은 규칙을 갖게 한다 — 한쪽만 고치면 mode3 가 조용히 구 동작으로 남는다.

**(4) 일반화 스위프 `sweep_record_moment.py` (신규, GPU 0).**
`.planning/quick/260731-f5h-.../sweep_leg_angle.py` 의 구조를 그대로 따른다 — 합성 keypoint
report + 등재 10동작 축 + 프로덕션 함수 직접 호출. 게이트:
  (a) 동작마다 record 2건 이상, `atFrameIdx` 가 서로 다를 때 카드 `userFrameIdx` 도 서로 다름 — 10/10.
  (b) `atFrameIdx` 를 전부 제거한 대조군에서 산출 PNG 바이트가 HEAD 와 동일 (fail-closed 무회귀).
  (c) 앵커 프레임 keypoint confidence 를 0 으로 눌러도 카드가 창 안 다른 프레임을 고름 — 붕괴
      프레임 확대 0.
  (d) 동작명 문자열 분기 0 — 변경 파일에서 등재 동작 id 리터럴 grep 0.
  (e) 카드가 채택한 앵커에서 `abs(atVideoSec - userVideoSec) * frames_fps < 1.0`.
스위프는 `--out` 으로 결과 JSON 을 quick 디렉터리에 남기고, 실행자가 **JSON 값을 직접 열어
확인한 뒤** 완료를 주장한다(코드 통과 != 확인).

**(5) legacy 해시 무회귀.**
`.planning/quick/260731-f5h-.../legacy_baseline.py` 를 그대로 재실행해 legacy/advisory/mode3
9케이스 해시가 불변임을 확인한다. 새 baseline 파일을 만들지 말고 기존 것과 대조한다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_fault_zoom_record_moment.py -q 2>&1 | tail -5</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_record_moment.py --out .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_out.json 2>&1 | tail -20</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python .planning/quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/legacy_baseline.py --compare .planning/quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/legacy_baseline.json 2>&1 | tail -10</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff -U0 -- backend/ app/src/ | /usr/bin/grep '^+' | /usr/bin/grep -v '^+++' | /usr/bin/sed 's/^+//' | /usr/bin/grep -Ev '^[[:space:]]*(#|//|\*|/\*)' | /usr/bin/grep -Ec 'kip-up|power-spin|peter-pan|elbow-twist|pdshape|ref-climb|ref-combo' | { read n; test "$n" = "0" && echo NO-MOTION-BRANCH || { echo MOTION-LITERAL-ADDED=$n; exit 1; }; }</automated>
  </verify>
  <done>
스위프 게이트 (a)~(e) 전부 통과하고 실행자가 `sweep_out.json` 을 직접 열어 값을 확인.
legacy 9케이스 해시 불변. `atFrameIdx` 부재 대조군 산출 byte-동일.
mode1/mode3 두 crit_units 생산자가 같은 규칙 보유. 동작명 리터럴 grep 0.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: 앱 — 계약 수용 + "잰 순간" 문장을 record 에 결속</name>
  <files>
app/src/lib/userAnalyses.ts,
app/src/lib/deductionSheet.ts,
app/src/lib/__tests__/deductionSheet.test.ts
  </files>
  <behavior>
    - `atVideoSec` 보유 record 의 basis 문장 초가 그 record 의 값이다 (카드 표시 초가 아니라).
    - `atVideoSec` 부재 record 는 "잰 순간" 절이 통째로 사라지고 앞 절("이 항목은 ...을 재요.")만 남는다.
    - 부재이면서 subject 도 없으면 basis 행 자체가 null (기존 fail-closed 유지).
    - malformed `atFrameIdx`/`atVideoSec`(문자열·NaN·음수)은 undefined 로 강등되고 record 자체와 기존 필드는 보존된다.
    - legacy doc(두 키 부재) 에서 크래시 0, 렌더 diff 0.
  </behavior>
  <action>
D-gbk-06 을 구현한다. 앱 변경은 이 3파일뿐이며 `cueTrack.ts`/`VideoCompare.tsx`/`result.tsx` 는
**diff 0** 이어야 한다(D-gbk-05).

**(1) `userAnalyses.ts::normalizeRecordPhraseFields`(368).**
`atVideoSec: normalizeFiniteNumber(raw.atVideoSec)` 를 추가한다. `atFrameIdx` 는 정수·음수 아님
까지 요구하므로 기존 `normalizeFiniteNumber` 결과에 `Number.isInteger && >= 0` 게이트를 얹어
아니면 `undefined`. 함수 상단 주석(365-367)의 "malformed 는 undefined 강등하되 record 자체와
기존 필드는 보존" 규율을 그대로 따른다.

**(2) `deductionSheet.ts` basis 출처 교체(529·535·542-550).**
`blockUserSec` 의 출처를 `blockZoom?.userVideoSec` 에서 `rec.atVideoSec` 으로 바꾼다.
`videoSecOf` 는 그대로 재사용. 변수명을 `blockMeasuredSec` 등으로 바꿔 "표시 프레임의 초"가
아니라 "이 감점을 잰 초"임을 코드에서도 읽히게 한다. 문구는 손대지 않는다 — 승인본 카피 그대로.
`if (blockUserSecLabel)` 게이트가 이미 fail-closed 이므로 부재 시 절이 생략되는 동작은 자동.
주석에 quick-260801-gbk 와 "표시 프레임 != 측정 순간이라 근거 없는 단정이었다"를 한국어로 적는다.

**주의 — `refSec`/`methodLine` 은 건드리지 않는다.** method 행의 "기준 사진은 그 정렬이 실제로
짝지은 순간"(566)은 **기준 패널 표시 프레임**을 말하는 문장이라 `blockRefSec`(=`refVideoSec`)이
정확한 출처다. paircap 좌/우 초(488-495)도 두 패널의 **표시** 초라 그대로 둔다.

**(3) `deductionSheet.test.ts` 확장.**
`<behavior>` 5항목을 기존 테스트 관례(433-452행 형식)로 추가한다. 기존 433-452 테스트는
`userVideoSec` 기반이므로 `atVideoSec` 로 기대값을 옮긴다 — 문장 자체는 불변이고 출처만 바뀐다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && node --test src/lib/__tests__/deductionSheet.test.ts 2>&1 | tail -10</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff --exit-code -- app/src/lib/cueTrack.ts app/src/components/VideoCompare.tsx app/src/app/analysis/result.tsx && echo "CUE-UNTOUCHED"</automated>
  </verify>
  <done>
basis 문장의 초가 `rec.atVideoSec` 에서 나오고 부재 시 절이 사라진다.
`npm run typecheck` clean, `node --test` PASS.
`cueTrack.ts`/`VideoCompare.tsx`/`result.tsx` diff 0.
  </done>
</task>


</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 앱 파싱 | 백엔드가 쓴 record 확장 키를 앱이 읽는다. 구 doc·malformed 값이 섞인다 |
| record dict → fault_zoom 인덱싱 | `atFrameIdx` 가 프레임 배열 인덱스로 쓰인다 — 범위 밖 값은 인덱싱 사고 |
| 산출 helper → 채점 substrate | 순간 산출 코드가 md/points 를 오염시키면 점수가 움직인다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-gbk-01 | Tampering | `_attach_translation_emission` 각인 | mitigate | `setdefault` 만 사용, 기존 키 무변경. `deduction_engine.py` git diff 0 을 게이트로 강제 (D-gbk-04) |
| T-gbk-02 | Denial of Service | `fault_zoom` 프레임 인덱싱 | mitigate | `atFrameIdx` 를 `max(0, min(idx, n-1))` clamp 후 사용. 비정수/음수는 `criterion_units_from_records` 에서 None 강등 |
| T-gbk-03 | Information Disclosure | doc 신규 필드 | accept | 프레임 인덱스·초는 이미 `userFrameIdx`/`userVideoSec` 로 노출된 축의 값. PII 0 |
| T-gbk-04 | Tampering | 앱 malformed 값 소비 | mitigate | `normalizeRecordPhraseFields` 에서 유한·정수·비음수 게이트, 실패 시 undefined 강등 (Task 3) |
| T-gbk-05 | Elevation of Privilege | Firestore nested array | mitigate | scalar int/float 2개만 방출 — 중첩 배열·dict 금지 (불변식 5). `_validate_dict_only_scalars` 기존 경로 통과 |
| T-gbk-SC | Tampering | 패키지 설치 | N/A | 이 플랜은 신규 의존성 0 — npm/pip/cargo install 없음 |
</threat_model>

<verification>
## 플랜 전체 게이트

0. **인터프리터** — `python` 은 PATH 에 없다. 백엔드 명령은 `backend/.venv/bin/python` 을
   쓴다(venv pytest 8.4.2). 시스템 `python3` 는 pytest 9.x 라 node ID 집합이 달라져
   회귀 기준선 대조가 무의미해진다.

1. **채점 무접촉 (불변식 1)**
   - `git diff --exit-code -- backend/shared/python/sunity_shared/analysis/deduction_engine.py` = 0.
   - `per_joint_deviation` 반환값 불변 테스트 PASS.
   - fixture 대조: `atFrameIdx` 주입 전/후로 record 의 `points`/`measuredValue`/`deviation` 과
     `breakdown.final` 이 동일 (Task 1 테스트).
   - 실 doc 재분석 시 `overallScore` 불변 (checkpoint 6번).

2. **회귀 0 (pre-existing 58건 기준)**
   ```
   cd backend && .venv/bin/python -m pytest -q 2>&1 | grep -E '^(FAILED|ERROR)' | sort > /tmp/after.txt
   ```
   착수 **전에** 같은 명령으로 `/tmp/before.txt` 를 만들어 두고 `diff /tmp/before.txt /tmp/after.txt`
   가 비어 있을 것. **전체 통과를 요구하지 않는다** — node ID 집합 diff 0 이 게이트다.

3. **일반화 (불변식 2)** — 등재 10동작 스위프 (a)~(e) + 동작명 리터럴 게이트.
   두 grep 게이트는 **추가된 비주석 줄만** 본다. 현 트리에 이미 동작명 37회(전부 주석·
   docstring: "kip-up keypoint saturate" 등)와 `frames_fps=9.0` 2회(app.py:2993/3033,
   pre-existing)가 있어서 전수 grep 은 착수 즉시 거짓 실패한다. `git diff` 의 `+` 줄에서
   주석을 걷어낸 뒤 세는 형태로만 유효하다. 스위프 하네스는 `backend/`·`app/src/` 밖
   (quick 디렉터리)에 두므로 이 게이트에 걸리지 않는다 — 하네스는 10동작 id 를 당연히 쓴다.

4. **fail-closed (불변식 3)** — `atFrameIdx` 제거 대조군 산출 byte-동일.

5. **계약 3자 (불변식 4)** — `test_contract_lockstep` PASS + contract.md §10.2 갱신.

6. **하위호환 (불변식 6)** — 두 키 부재 legacy doc 에서 백엔드/앱 크래시 0.

7. **GPU 0** — 모든 자동 검증이 Pod 없이 로컬에서 돈다. 재추론이 필요한 설계면 잘못된 설계다
   (시계열은 이미 `per_joint_deviation` 안에 만들어졌다가 버려지고 있다).

8. **범위 규율** — `cueTrack.ts` / `VideoCompare.tsx` / `result.tsx` diff 0 (D-gbk-05).

## belle 실기기 확인 (done 조건 아님 — 오케스트레이터가 belle 에게 넘길 목록)

<human-check>
**선행:** Pod 기동 → 실 영상 재분석 → OTA 발행. 시뮬레이터와 합성 스위프로는 실 doc 의
카드 프레임 분산도, 음성 발화도 볼 수 없다 — 실행자는 이 6항목을 스스로 통과 처리하지 않는다.

1. 재분석 doc 의 `deductionBreakdown.records[]` 를 조회한다.
   - measurable criterion record 에 `atFrameIdx`/`atVideoSec` 이 있는가.
   - **서로 다른 record 의 `atFrameIdx` 가 실제로 다른가** — 킵업 2건이 둘 다 16, 파워스핀
     4건 전부 38, 엘보 5건 전부 144 였던 것이 증상이다.
   - `body_relative_reach` / `dimension_overall_fallback` record 에는 키가 **없는가**.
2. 같은 doc 의 `faultZoomComparisons[]` 에서 `userFrameIdx` 가 카드마다 다른가.
3. 결과 화면에서 확대비교 카드를 항목별로 열어, 사진이 항목마다 다른 순간인가.
4. 시트의 "어디서 재나요" 행 초가 record 별로 다른가.
5. 재생하면서 **두 번째 음성 큐가 발화되는가** — 종전엔 두 창이 완전히 겹쳐 영원히 묻혔다.
   (F-6 의 다른 무음 원인은 이 플랜 범위 밖이다 — 여기서 보는 것은 "두 번째 큐가 창을
   갖는가"뿐이다.)
6. 회귀: 같은 영상의 `overallScore` 가 재분석 전후로 동일한가.
</human-check>
</verification>

<success_criteria>
- 측정 가능한 criterion 5종의 record 가 자기 측정 순간을 나른다 — reach/whole-score fallback 은 비어 있다.
- 확대비교 카드가 카드마다 자기 순간을 쓴다. 프레임이 같으면 측정 순간이 실제로 같을 때뿐이다.
- `deduction_engine.py` diff 0, pytest node ID diff 0, `npm run typecheck` clean.
- 등재 10동작 스위프 전 게이트 통과 + 실행자가 산출 JSON 을 직접 열어 확인.
- 앱 basis 문장이 record 자신의 초를 말하고, 근거 없으면 말하지 않는다.
- belle 실기기 확인 6항목은 `<human-check>` 로 분리 — **done 조건 아님**(Pod·OTA 선행 필요).
</success_criteria>

<output>
Create `.planning/quick/260801-gbk-record-atframeidx-criterion/260801-gbk-SUMMARY.md` when done.

SUMMARY 에 반드시 포함:
- criterion 별 순간 산출 규칙 표 (실제 구현된 것 — 계획과 다르면 다른 이유)
- 채점 무접촉 증거 (엔진 diff 0 출력 + fixture 전/후 대조 실측값)
- pytest node ID diff 결과 (before/after 파일 경로 포함)
- 스위프 게이트 (a)~(e) 실측 결과 + `sweep_out.json` 에서 직접 읽은 값 인용
- fail-closed 로 남긴 criterion 과 그 이유
- 검증하지 못한 것과 그 이유 (실기기 음성·실 doc 카드 분산 등) — "안 재봤다"를 명시
</output>
</content>
</invoke>
