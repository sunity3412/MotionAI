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
    - "순간을 신뢰 있게 못 정하는 감점(reach·whole-score fallback·vision split)은 필드가 비고, 그 카드는 지금과 동일하게 동작한다."
    - "overallScore·deductionBreakdown.final·record 의 points/measuredValue/deviation 이 이 변경 전후로 1도 움직이지 않는다."
    - "'위 사진은 그 값을 잰 순간(N.N초)이에요' 문장은 그 행에 사진이 있고 그 사진이 바로 그 순간일 때만 나온다."
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/motiondtw.py"
      provides: "DTW path 대표 프레임 산출 (per_joint_deviation 무접촉 sibling)"
      contains: "per_joint_representative_frames"
    - path: "backend/shared/python/sunity_shared/analysis/dimensions.py"
      provides: "_select_window 공유 window 안 대표 프레임 산출"
      contains: "extension_representative_frame"
    - path: "backend/functions/pipeline/app.py"
      provides: "criterion 별 측정 순간 산출(measured_at_out) + record 각인 + mode3 unit 미러"
      contains: "measured_at_out"
    - path: "backend/shared/python/sunity_shared/models.py"
      provides: "atFrameIdx/atVideoSec/atMatched 계약 키 집합"
      contains: "DEDUCTION_RECORD_MOMENT_KEYS"
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "unit 의 자기 순간을 프레임 앵커로 소비 + atMatched 인증 방출"
      contains: "at_frame_idx"
    - path: "app/src/types/analysis.ts"
      provides: "DeductionRecord.atFrameIdx?/atVideoSec? + FaultZoomComparison.atMatched? 계약 미러"
      contains: "atFrameIdx"
    - path: "app/src/lib/deductionSheet.ts"
      provides: "basis 문장을 사진-순간 일치 인증에 게이트 (fail-closed)"
      contains: "atMatched"
    - path: ".planning/quick/260801-gbk-record-atframeidx-criterion/sweep_record_moment.py"
      provides: "등재 10동작 일반화 스위프 (GPU 0) + HEAD 사전 캡처 대조군"
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
    - from: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      to: "app/src/lib/deductionSheet.ts"
      via: "atMatched 인증 → basis 절 방출 게이트"
      pattern: "atMatched"
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
프레임 앵커로 쓰는 fault_zoom 배선 + 사진-순간 일치가 인증될 때만 나오는 앱 basis 문장.
**채점 무접촉.**

**범위 한계 (D-gbk-07, 정직 고지):** `split_angle` 의 **프로덕션 실동작 경로는 vision 주입**이고
그 경로엔 시계열이 없다 → fail-closed. **킵업의 split 카드는 이 플랜으로 풀리지 않는다.**
킵업의 어깨 카드 2건, 파워스핀 4건, 엘보 5건은 풀린다.
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

<execution_preamble>
**모든 태스크 시작 전에 이 두 줄을 먼저 실행한다. 이후 모든 게이트가 이것에 의존한다.**

BASE 고정 (B3 — `git diff --exit-code` 는 `git add` 한 번에 무력화된다. 격리 리포 실측:
수정 후 `git add` 하면 `git diff --exit-code -- f.py` 가 **exit 0(clean)** 을 낸다):

    export GBK_BASE=$(git rev-parse HEAD)

pytest 기준선 캡처 (B1 — 하드코딩 금지, 착수 시점 값만 유효):

    PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 \
      | /usr/bin/grep -E '^(FAILED|ERROR)' | sort > /tmp/gbk-before.txt
    wc -l < /tmp/gbk-before.txt

**`cd backend && .venv/bin/python -m pytest -q` 를 쓰지 말 것.** 실측:
`!!! Interrupted: 12 errors during collection !!!` 로 **테스트를 0개 실행**한다
(`test_pole_detector.py:21` `ModuleNotFoundError: No module named 'fixtures'` 외 11건).
산출물에 `FAILED` 가 0줄이라 백엔드를 다 깨뜨려도 diff 가 비어 **거짓 통과**한다.
`PYTHONPATH=backend/tests` + repo 루트 실행이 수집 에러 0을 만든다 (실측:
`59 failed, 3767 passed, 26 skipped`). 이 59 는 **2026-08-01 착수 시점 캡처값**이며
게이트는 수치가 아니라 `diff /tmp/gbk-before.txt /tmp/gbk-after.txt` 가 비는 것이다.
(f5h 가 07-31 에 적은 58 은 이미 낡았다 — 수치를 상수로 박지 말 것.)
</execution_preamble>

<design_decisions>

오케스트레이터가 답을 정해두지 않은 열린 질문에 대한 결정과 근거. 실행자는 이 절을 스펙으로 삼는다.

**D-gbk-01 — 필드 이름·단위·도메인: `atFrameIdx`(int) + `atVideoSec`(float), 학생 9fps angles 도메인.**

`atFrameIdx` 는 **학생 angles 행 인덱스 = 9fps 추출 프레임 배열 인덱스**다. ① 감점을 만드는 모든
집계(`angles` 행렬, `windowMedianAngleDeltas.sourceFrameIndices.user`, `dimensions._select_window`,
`features.split_angle_series`)가 전부 이 한 도메인에 산다. ② `fault_zoom` 의 기존 프레임 override
(`user_frame_idx`, `user_frame_candidates`)가 정확히 이 도메인을 받는다(`fault_zoom.py:2322-2325`)
— 새 파이프가 아니라 있는 파이프에 값을 흘리는 일이 된다. ③ 학생 `keypointReport` 는
`build_keypoint_report(pose_frames, fps=9.0)`(`app.py:6085`)로 만들어져 rep 공간과 9fps 공간이
학생 측에서는 일치한다 — 그러나 **이름은 측정 도메인으로 붙인다.** rep 인덱스 이름을 붙이면
기준 측(phase4_v1 18fps)과 헷갈려 F-3 계열 버그가 재발한다.

`atVideoSec = atFrameIdx / frames_fps` 를 **함께 방출한다.** contract.md §11.8 이 이미 박제한 F-3
근본원인("앱이 rep 인덱스를 rep fps 로 나눠 초를 추정")을 되풀이하지 않기 위해서다. fps 는
`_pipeline_frame_fps()`(`app.py:4541`) 단일 출처에서 읽는다 — **리터럴 9.0 금지.**

**D-gbk-02 — 기준(정은지) 측 순간은 방출하지 않는다.**

`fault_zoom` 은 이미 학생 프레임에서 기준 프레임을 파생한다(`_matched_ref_frame` → `select_pose_
matched_ref_frame`). record 가 독립적인 기준 순간을 들고 오면 **경쟁하는 두 번째 출처**가 생겨,
카드 안에서 학생과 기준이 다른 순간을 보여주던 바로 그 버그(`fault_zoom.py:2495-2501` 가
고친 것)를 되살린다. record 는 **학생 측 순간 하나만** 나른다.

**D-gbk-03 — 대표 프레임은 언제나 "집계값에 가장 가까운 프레임". argmax 금지.**

`motiondtw.per_joint_deviation` docstring(193-220)이 박제한 사실: RTMW 가 inverted/occluded 폴
자세에서 인접 프레임 간 10°+ jitter 를 만들고 p99 이 35~50° 다. 평균을 버리고 median 을 쓰는
이유가 정확히 그것이다. **편차 argmax 프레임을 고르면 그 jitter 프레임을 "여기가 감점 부분"
이라고 확대해 보여주게 된다 — 지금보다 나빠진다.** 규칙은 하나로 통일한다:

> 그 record 가 **실제로 보고한 집계값**에, 자기 per-frame 값이 **가장 가까운** 프레임.

criterion 별 산출 (집계가 다르므로 순간도 각자의 집계에서 파생한다):

| criterion | 집계 (record 가 보고하는 값) | 순간 |
|---|---|---|
| `angle_vs_reference__{jk}` — Gemini pointed | `windowMedianAngleDeltas.deltas[].student_deg` = worst-window 안 학생 각도의 median | `sourceFrameIndices.user` 안에서 `abs(angles[t][j] - student_deg)` 최소 프레임 |
| `angle_vs_reference__{jk}` — Gemini silent | `per_joint_deviation` = DTW path 전체 median of `abs(Δ)` | `match.start + path[k*][0]`, `k*` = `abs(diffs[k][j] - median_j)` 최소 |
| `leg_extension` / `arm_extension` | 관절쌍 중 max 인 관절의 `max(0, 180 - mean_over_window)` | 그 **argmax 관절**에 대해 `_select_window` 구간 안에서 per-frame 부족분이 집계값에 가장 가까운 프레임 |
| `line` | 양수 부족분 EXTEND 관절들의 평균 | 같은 관절 집합의 per-frame 평균 부족분이 집계값에 가장 가까운 프레임 |
| `split_angle` | **D-gbk-07 참조 — fail-closed** | — |
| `body_relative_reach` | notch 부족분 | **fail-closed — 필드 없음.** notches 에 시계열이 없다 |
| `dimension_overall_fallback` | whole-score passthrough | **fail-closed — 필드 없음.** 특정 순간이 없는 record 다 |

pointed 경로는 **median 을 재계산하지 않는다** — `features._delta_entry`(185)가 이미 emit 한
`student_deg` 를 그대로 읽는다. 재계산이 없으므로 drift 가 원리적으로 불가능하다.

**`extension_deviation` 이 max 가 아니라 mean 인 근거(재확인):** `dimensions.py:277-282` 는
`rep = np.mean(sliced, axis=0)` 후 `max(0, 180 - rep[i])` 다. 시간축 집계는 **mean** 이고, "관절별
max" 는 좌/우 관절쌍 축의 max(`app.py:2394-2399` `_max_dev`)다. window 안 **최대 부족 프레임**을
고르면 record 가 보고한 값과 다른 순간을 가리키고 argmax 함정에도 걸린다.

**★ sibling 함수가 필수인 이유 (SHA-256 박제):**
`backend/tests/phase33/test_m3_alignment_only.py::test_m3_constants_hash_unchanged`(170-180행)이
`inspect.getsource(per_joint_deviation)` 의 **SHA-256 을 박제**한다(소스 직접 열어 확인). 그 함수 본체를 한 글자라도 고치면 그
게이트가 깨진다. 시계열을 되돌려 받으려고 반환값을 확장하거나 out-param 을 다는 방식은 전부
그 해시를 건드린다 — **sibling 함수 추가가 게이트를 우회하지 않고 통과하는 유일한 길이다.**
`dimensions` 쪽도 같은 이유로 `extension_deviation` 본체를 고치지 않고 helper 를 추가한다.

**D-gbk-04 — seam: tally **뒤**에서 각인한다. `deduction_engine.py` 는 diff 0.**

채점 엔진을 건드리지 않는다. 측정 순간은 `_build_deduction_measured_deviations` 의
**out-param**(`seed_audit_out` 과 정확히 같은 선례 — `app.py:2360`/`2511`)으로 빠져나와,
`_attach_translation_emission`(`app.py:4890-4914`)에서 record dict 에 각인된다. 그 함수의 계약은
이미 "기존 키 무변경(setdefault), 채점 무접촉"(4876-4877)이다.

이 선택으로 **불변식 1이 테스트가 아니라 구조로 증명된다** — points 를 계산하는 코드가 이 값을
볼 수 없다.

**게이트는 `git diff --exit-code` 가 아니라 `git diff "$GBK_BASE"` 다 (B3).** 격리 리포 실측:
파일 수정 후 `git add` 하면 `git diff --exit-code -- f.py` 가 exit 0(clean)을 내고, 같은 상태에서
`git diff "$BASE" --exit-code -- f.py` 는 exit 1(dirty)을 낸다. 스테이징 한 번에 무효가 되는
게이트로는 "구조로 증명된다"는 선언이 성립하지 않는다.

**D-gbk-05 — 큐 창 겹침·`activeCue` tie-break 는 이 플랜 범위 밖. 명시적으로 남긴다.**

"두 카드의 큐 창이 완전히 동일해져 두 번째 음성이 영원히 발화되지 않는다"는 **동일 프레임의
결과**이지 tie-break 로직의 결함이 아니다. 프레임이 갈리면 창이 갈리고 증상이 사라진다.
이미 사라진 원인 위에 tie-break 보정을 얹으면 두 번째 수리가 되어 회귀 표면만 넓힌다.

남은 "창이 0.089초에 열려 플레이어 준비 전에 영상을 멈춘다"는 **재생 준비 문제**다 — 진짜로
이른 감점에서는 이 플랜 이후에도 발생한다. F-6 자체 사이클로 남긴다.
**`cueTrack.ts` / `VideoCompare.tsx` 무접촉.**

**advisory 카드는 구조적으로 제외된다 (W2).** `app.py:3025-3053` 의 advisory 배치는
`criterion_units` 를 **전달하지 않는다**(그 자리 주석: "advisory 는 record 없는 참고 카드 —
criterion_units 미전달"). advisory 는 record 가 없으므로 측정 순간도 없다 — legacy fan-out
경로가 그대로 유지된다. belle 확인 항목은 `tier=='confirmed'` 카드로 한정해야 하며,
advisory 카드가 서로 같은 프레임인 것은 **이 플랜의 실패가 아니다.**

**D-gbk-06 — basis 문장은 "그 행에 사진이 있고, 그 사진이 바로 그 순간일 때"만 나온다.**

원안(출처를 `rec.atVideoSec` 으로 단순 교체)은 **없애려던 결함을 역방향으로 재생산한다.**
현행 `deductionSheet.ts:529` 는 `blockZoom?.userVideoSec` 을 쓰므로 **그 record 가 카드를 가질
때만** 절을 낸다 — 지금은 "문장의 초 == 독자가 보는 사진의 초"가 항상 성립하고, 진짜 문제는
*사진 자체의 순간이 틀린 것*이다. 출처만 바꾸면 카드 없는 행까지 절을 얻는다:
- `criterion_units_from_records(..., max_units: int = 4)`(`fault_zoom.py:151`) — 카드는 최대 4장인데
  `angle_vs_reference__{jk}` 는 최대 8건 → 5번째부터 사진 없음.
- `CRITERION_REGION` = `{split_angle, leg_extension, arm_extension}` 뿐(`fault_zoom.py:129-133`) →
  **`line` 은 `region is None → continue`(207-209)로 카드가 아예 없다.** 그런데 D-gbk-03 은
  `line` 에 순간을 준다.
- Task 3 앵커가 **채택되지 않은** 카드(창 전원 저신뢰/후보 폐기)는 worst_seconds 프레임으로
  남는데 `atVideoSec` 은 그대로 인쇄된다.

→ **방출 조건 = `blockZoom != null` AND `blockZoom.atMatched === true`.**
`atMatched` 는 앱이 재계산하는 값이 아니라 **프레임을 실제로 고른 코드가 인증한 scalar** 다
(`fault_zoom` 이 최종 채택 학생 프레임 `u_idx_unit` 이 `unit.at_frame_idx` 와 **같을 때만** true).
앱이 두 초를 빼서 비교하게 두면 앱이 fps 를 알아야 하고, 그게 정확히 F-3 을 만든 구조다.
`refMatched`(`fault_zoom.py:2923`) 선례와 같은 형상·같은 의미(이 카드가 그 대응을 실제로
세웠는가)라 새 개념 0. 불성립 시 기존 `if (blockUserSecLabel)` fail-closed 가 절을 생략한다.
**새 카피 0.**

**D-gbk-07 (신규) — `split_angle` 은 fail-closed. 킵업 split 카드는 이 플랜으로 안 풀린다.**

`split_angle` 의 생산자가 둘인데 **프로덕션에서 사는 쪽은 시계열이 없는 쪽**이다:
- ① 기하 빌더 `md["split_angle"]=d_split`(`app.py:2428`) — 게이트가
  `profile.required_split_deg is not None`(`app.py:5311`)인데 **어떤 recognizer 도 이 값을 설정하지
  않는다.** 실측: `technique.py:115`, `gemini_technique_recognizer.py:233/257/364/431` 전부 `None`
  이고 `app.py:5308` 주석도 같은 진술이다 → **사문(dead).** `features.max_split()` 의 idx 를 살리는
  원안은 **실행되지 않는 코드에 배선하는 것**이었다.
- ② vision 주입(`deduction_engine.py:289-292`, `source="vision"`) → **유일한 실동작 경로.**

**"학생 최대 벌림 프레임을 vision record 에 붙이면 되지 않나"에 대한 답: 안 된다.** 이 필드의
계약은 "이 감점을 **어느 프레임에서 쟀는가**"다. vision record 의 `measuredValue` 는 Gemini
추정이고 우리는 그 프레임에서 재지 않았다. 기하에서 뽑은 프레임을 "여기서 쟀다" 계약 아래
방출하면, 앱이 다시 "위 사진은 그 값을 잰 순간이에요"라고 말한다 — **이 플랜이 없애려는
결함과 정확히 같은 종류의 거짓**이다. `[[state-evidence-act-or-mark-unverified]]`: 동사는 그
주장을 성립시킨 행위가 결정한다. 재지 않았으면 "쟀다"고 쓸 수 없다.

→ vision `split_angle` record 는 **필드 부재(fail-closed)**. out-param 이 빌더에 있고 엔진
주입보다 먼저 도므로 이 fail-closed 는 추가 코드 없이 자동 성립한다(Task 1 이 단정한다).

**따라서 `<done>` 의 주장은 "criterion 5종"이 아니라 4계열이다** — `angle_vs_reference`(window /
DTW 두 경로), `leg_extension`, `arm_extension`, `line`. 킵업의 **어깨 카드는 풀리고 split 카드는
안 풀린다.** 파워스핀 4건·엘보 5건은 전부 `angle_vs_reference` 라 풀린다. SUMMARY 는 이것을
그대로 적는다 — "풀린다"고 뭉뚱그리지 말 것.

**앱 변경은 0 이 아니다 — 3곳** (오케스트레이터의 "확인할 것"에 대한 답):
1. `app/src/types/analysis.ts` — 계약 3자 미러는 강제다. `backend/tests/test_deduction_engine.py::
   test_contract_lockstep` 이 TS 필드 집합과 `models.DEDUCTION_RECORD_*_KEYS` 합집합의 동등을
   검사하므로, TS 를 빼면 **테스트가 깨진다.**
2. `app/src/lib/userAnalyses.ts:368` — 방어적 정규화 관례상 신규 키도 정규화한다.
3. `app/src/lib/deductionSheet.ts` — D-gbk-06.

`cueTrack.ts` / `VideoCompare.tsx` / `result.tsx` = **0 diff.** 큐 창은 `zoom.userFrameIdx` 로
만들어지므로 카드가 각자 프레임을 잡는 순간 창도 자동으로 갈린다.
</design_decisions>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 순수 helper 3종 + 측정 순간 산출 (out-param)</name>
  <files>
backend/shared/python/sunity_shared/analysis/motiondtw.py,
backend/shared/python/sunity_shared/analysis/dimensions.py,
backend/functions/pipeline/app.py,
backend/tests/test_record_measured_at.py
  </files>
  <behavior>
    - pointed 관절: `sourceFrameIndices.user` 안에서 `student_deg` 에 가장 가까운 프레임을 고른다. 그 window 밖 프레임은 절대 고르지 않는다.
    - silent 관절: DTW 대표 프레임이 `match.start + path[k][0]` 로 절대 인덱스가 되고, sibling 이 낸 median 이 `per_joint_deviation` 결과와 정확히 일치한다.
    - jitter 방어: 한 프레임만 편차가 폭주하는 합성 시계열에서 대표 프레임이 그 폭주 프레임이 **아니다** (argmax 회귀 가드).
    - `leg_extension`: 좌/우 무릎 중 부족분이 큰 쪽이 집계값을 만들고, 순간은 그 관절의 window 안 대표 프레임이다.
    - `line`: 양수 부족분 EXTEND 관절 집합의 per-frame 평균이 집계값에 가장 가까운 프레임.
    - fail-closed: `body_relative_reach` / `dimension_overall_fallback` / **vision 주입 `split_angle`** 은 out-param 에 항목이 없다.
    - `md` 불변: `measured_at_out` 전달 유무와 무관하게 반환 `md` 가 키·값 모두 동일하다.
    - 하위호환: `measured_at_out=None`(기본)으로 호출해도 크래시 0.
  </behavior>
  <action>
D-gbk-01/02/03/07 의 **산출부**만 만든다. 각인·계약·소비는 Task 2~4.

**(1) `motiondtw.py` — sibling 함수 추가. `per_joint_deviation` 본체는 한 글자도 고치지 않는다.**
`backend/tests/phase33/test_m3_alignment_only.py::test_m3_constants_hash_unchanged` 가 그 함수
소스의 **SHA-256 을 박제**하므로
반환값 확장·out-param 추가는 전부 게이트를 깬다 (D-gbk-03 ★ 참조).
`per_joint_representative_frames(path, A_user_seg, A_ref, start)` 를 추가한다. 같은
`diffs = (len(path), J)` 순회로 관절별 median 을 구한 뒤, 관절 j 마다 `abs(diffs[:, j] - median_j)`
최소인 path 스텝 k 를 골라 `start + path[k][0]`(절대 9fps 학생 프레임)을 돌려준다. 반환
`dict[int, int]`, `path` 빈 경우 빈 dict.

**docstring 토큰 금지 (W5):** 게이트 grep 은 `#` 주석만 걷어내고 삼중따옴표 본문은 못 걷는다.
신규 docstring 에 `9.0` 과 등재 동작명(kip-up/power-spin/peter-pan/elbow-twist/pdshape/
ref-climb/ref-combo)을 **쓰지 말 것.** jitter 근거는 **줄 번호로 인용**한다 — 예: "근거는 이
파일 198-209행". 문장을 복사해 오면 게이트가 튄다.

**(2) `dimensions.py` — `_select_window` 를 공유하는 대표 프레임 helper 2개.**
`extension_representative_frame(angles, profile, joint_key, target_deficit)` — `_select_window`
가 돌려주는 `(s, e)` 구간 안에서 `max(0, _FULL_EXTENSION_DEG - angles[t][j])` 가 `target_deficit`
에 가장 가까운 t 를 절대 인덱스로. `line_representative_frame(angles, profile, joint_keys,
target_deficit)` — 같은 구간에서 `joint_keys` per-frame 부족분 평균이 target 에 가장 가까운 t.
둘 다 유한값 없으면 None. **windowing 은 반드시 `_select_window` 경유**(이 파일 286-297 의
"drift 방지, 전부 이 함수 하나만 호출" 규율). 새 windowing 상수 0. `extension_deviation` 본체
무접촉. docstring 토큰 금지 동일 적용.

**(3) `app.py::_build_deduction_measured_deviations` — `measured_at_out` out-param.**
`seed_audit_out` 과 같은 자리·같은 방식으로 `measured_at_out=None` 키워드 추가. docstring 에
"md(점수 substrate)는 여기서 절대 mutate 하지 않는다 — 순간은 out-param 에만 기록된다"를
2368-2369 문구와 같은 취지로. 값 형상 `{criterion_id: {"frame_idx": int, "video_sec": float}}`.

- extension: `_max_dev` 가 **어느 관절이 이겼는지**도 반환하도록 지역 helper 확장(반환 형상만
  변경, md 값 불변) → 그 관절로 `extension_representative_frame`.
- `line`: `extend_devs` 구성에 쓴 관절 키 목록을 보관해 `line_representative_frame` 에 전달.
- pointed 경로: `wm_by_joint` 구성 시 그 entry 의 `student_deg` 도 보관하고,
  `sourceFrameIndices.user` 안에서 `abs(angles[t][j] - student_deg)` 최소 t. **median 재계산 금지.**
  `student_deg` 부재/비유한이면 그 관절 fail-closed(순간 미기록, md 는 그대로).
- DTW 경로: 기존 `per_joint_deviation` 호출 옆에서
  `per_joint_representative_frames(path, user_seg, reference_angles, start)`.
- `_emit_reference_relative` 가 **False 를 반환한 관절**은 순간도 기록하지 않는다 — 방출 md 키와
  순간 키가 정확히 대응해야 한다.
- **`split_angle` 에는 순간을 넣지 않는다 (D-gbk-07).** `split_deficit_deg` 경로는
  `profile.required_split_deg` 게이트(`app.py:5311`)가 항상 False 라 **사문**이고, 실동작 경로는
  엔진 vision 주입(`deduction_engine.py:289-292`)이라 시계열이 없다. `split_peak_frame_idx`
  키워드를 **추가하지 말 것** — 실행되지 않는 코드에 배선하는 일이다.
- `video_sec` 은 `_pipeline_frame_fps()`(4541) 로 나눈다. **리터럴 9.0 금지.** fps <= 0 이면
  `video_sec` 생략(frame_idx 만).

**(4) `app.py::_process` — 배선.**
`split_deficit_deg = None` 초기화(5245) 옆에 `measured_at: dict = {}` 를 같은 자리에서 초기화한다
(mode3/legacy 에서도 이름이 존재해야 Task 2 의 6287 호출부가 안전). 5779 builder 호출에
`measured_at_out=measured_at` 추가.

**(5) 테스트 `backend/tests/test_record_measured_at.py` (신규).**
`<behavior>` 8항목에 1:1 대응하는 테스트만 쓴다(수치 채우기 금지, CLAUDE.md §7). argmax 회귀
가드는 "한 프레임만 40° 폭주 + 나머지 5°" 시계열에서 대표가 폭주 프레임이 아님을 단정한다.
vision split fail-closed 는 vision 주입 형태의 fault_context 로 tally 를 태워 그 record 에
순간이 없음을 단정한다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && set -o pipefail && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_record_measured_at.py backend/tests/phase33/test_m3_alignment_only.py 2>&1 | tail -5</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff "$GBK_BASE" --exit-code -- backend/shared/python/sunity_shared/analysis/deduction_engine.py && echo ENGINE-DIFF-0</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff "$GBK_BASE" -- backend/ | /usr/bin/grep '^+' | /usr/bin/grep -v '^+++' | /usr/bin/sed 's/^+//' | /usr/bin/grep -Ev '^[[:space:]]*#' | /usr/bin/grep -Ec '(^|[^_a-zA-Z])9\.0([^0-9]|$)' | { read n; test "$n" = "0" && echo NO-FPS-LITERAL || { echo FPS-LITERAL-ADDED=$n; exit 1; }; }</automated>
  </verify>
  <done>
helper 3종이 존재하고 `per_joint_deviation`·`extension_deviation` 본체 diff 0
(`test_m3_constants_hash_unchanged` SHA-256 게이트 PASS). `measured_at_out` 이 4계열에 순간을 채우고
reach·fallback·vision split 에는 항목이 없다. `md` 가 out-param 유무와 무관하게 동일.
`deduction_engine.py` diff 0 (BASE 대비). 신규 코드에 `9.0` 리터럴 0.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: record 각인 + 계약 3자 미러</name>
  <files>
backend/functions/pipeline/app.py,
backend/shared/python/sunity_shared/models.py,
backend/tests/test_deduction_engine.py,
docs/contract.md,
app/src/types/analysis.ts
  </files>
  <behavior>
    - 각인 additive: `_attach_translation_emission` 전후로 record 의 필수 11키 + cap 2키 + track 값이 완전히 동일하다.
    - `measured_at` 항목이 있는 record 만 `atFrameIdx`/`atVideoSec` 을 얻는다.
    - `measured_at=None`/빈 dict 로 호출해도 크래시 0, 방출 record 는 종전 형상.
    - 값 타입: `atFrameIdx` 는 int, `atVideoSec` 은 float — 중첩 배열·dict 0.
    - `test_contract_lockstep` 이 4-set 합집합으로 TS 필드 집합과 동등을 확인한다.
  </behavior>
  <action>
**(1) `app.py::_attach_translation_emission` — 각인.**
`measured_at: dict | None = None` 키워드 추가, 6287 호출부에서 `measured_at=measured_at` 전달.
record 루프(4891-4914) 안에서 `criterion` 으로 조회해 `rec.setdefault("atFrameIdx", ...)`,
`rec.setdefault("atVideoSec", ...)` 로만 넣는다 — **기존 키 절대 무변경**. 값이 없으면 키를
만들지 않는다(fail-closed). `int()` / `float()` 캐스팅으로 Firestore flat scalar 제약 통과.

**(2) `models.py` — 계약 키.**
`DEDUCTION_RECORD_MOMENT_KEYS = ("atFrameIdx", "atVideoSec")` 를 `DEDUCTION_RECORD_EXTENSION_KEYS`
아래에 추가하고 기존 3집합과 **disjoint** 임을 주석에 명시. 주석에 fail-closed 조건(reach·
whole-score fallback·vision split)과 도메인(학생 9fps angles, rep 아님)을 적는다.

**(3) `test_deduction_engine.py::test_contract_lockstep` 확장.**
3-set 합집합을 4-set 으로 넓힌다.

**(4) `app/src/types/analysis.ts` — 두 인터페이스 동시 선언 (interface-first).**
- `DeductionRecord` 에 `atFrameIdx?: number;` / `atVideoSec?: number;`
- `FaultZoomComparison` 에 `atMatched?: boolean;` — Task 3 이 방출할 인증 필드를 **미리** 선언해
  Task 4 가 계약을 기다리지 않게 한다(D-gbk-06).
주석에 (a) 학생 9fps angles 도메인이고 `userFrameIdx`(rep 공간)와 **다른 축**, (b) `atVideoSec`
을 rep fps 로 재계산 금지(§11.8 F-3 교훈), (c) 부재 = 순간 미확정 criterion 또는 legacy doc,
(d) `atMatched` = 표시 프레임이 그 record 의 측정 프레임과 **동일함을 fault_zoom 이 인증** —
앱이 초 차이를 계산해 추정하지 말 것.
**`analysis.ts:710-711` 경고 준수: 이 주석 블록에 word-colon 패턴·중괄호 금지**(lockstep regex 충돌).

**(5) `docs/contract.md` §10.2 / §11.**
D-gbk-03 표(criterion → 집계 → 순간)와 D-gbk-07(split fail-closed 근거)을 그대로 박제한다.
`atMatched` 는 §11 `refMatched` 옆에 같은 형식으로.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && set -o pipefail && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_deduction_engine.py backend/tests/test_record_measured_at.py 2>&1 | tail -5</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff "$GBK_BASE" --exit-code -- backend/shared/python/sunity_shared/analysis/deduction_engine.py && echo ENGINE-DIFF-0</automated>
  </verify>
  <done>
계약 3자(models.py / analysis.ts / contract.md) 동시 갱신 + `test_contract_lockstep` PASS.
각인이 additive 임을 테스트가 단정. `npm run typecheck` clean. 엔진 diff 0 유지.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: fault_zoom 이 자기 순간을 앵커로 쓰고 일치를 인증 (+ 10동작 스위프)</name>
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
    - `atMatched` 는 **최종 채택 학생 프레임이 `at_frame_idx` 와 같을 때만** true. 선택이 앵커를 벗어나면 false.
    - 기준 프레임은 여전히 DTW 대응에서 나온다 — record 는 기준 순간을 나르지 않는다(D-gbk-02).
    - DTW 대응이 한 후보라도 실패하면 합성 후보 전체를 버리고 기존 경로로 떨어진다(fail-closed).
    - override 경로(`ref_frame_idx` 지정)에서도 UnboundLocalError 0.
  </behavior>
  <action>
**★ 순서 강제 (W7 — 대조군이 먼저다).** fail-closed 무회귀 게이트는 "HEAD 산출물과 byte-동일"
인데 스위프 자체가 이 태스크에서 새로 생기므로, **스위프를 먼저 작성하고 구현 전에 1회
캡처**해야 대조군이 존재한다. `legacy_baseline.py` 는 docstring(94행)이 "legacy/advisory/mode3
경로만"이라 mode1 criterion-units 를 덮지 않는다 — 대체재가 아니다.
  ① `sweep_record_moment.py` 작성 → ② `--out sweep_out.before.json` 으로 **HEAD 에서 캡처**
  (PNG sha256 포함) → ③ 구현 → ④ 재실행 후 대조.
`<verify>` 의 스위프 명령은 ④ 를 가정한다.

**(1) `fault_zoom.criterion_units_from_records` — 순간을 unit 에 싣는다.**
반환 항목에 `at_frame_idx` 추가: `rec.get("atFrameIdx")` 가 int 이고 >= 0 이면 그 값, 아니면 None.
`_CropUnit` dataclass 에 `at_frame_idx: int | None = None` additive default 필드 추가.
**★ 생성부도 반드시 고칠 것 (W4):** `fault_zoom.py:2472-2483` 의 `_CropUnit(...)` 생성에
`at_frame_idx=cu.get("at_frame_idx")` 를 넣는다. 빠지면 `unit.at_frame_idx` 가 항상 None 인
**no-op 출하**가 된다.

**(2) `_dtw_ref_fps` / `_dtw_ref_frames` 스코프 끌어올리기 (W3 — 선행 필수).**
두 이름은 현재 `ref_frame_idx is None` 분기(2430-2466) **안에서만** 바인딩된다. unit 루프에서
쓰면 override 경로(`ref_frame_idx` 지정)에서 **UnboundLocalError** 가 난다 — fail-closed 규칙은
NameError 를 막지 못한다. 두 값의 계산을 그 분기 **위로** 끌어올려 항상 바인딩되게 하고,
기존 분기는 끌어올린 값을 읽기만 하도록 바꾼다(값·순서 불변 — 기존 산출 byte-동일).

**(3) unit 앵커 → 후보 창.**
unit 루프 안, 기존 candidates 블록(2506) **앞**에 지역 변수 `u_cands_unit = user_frame_candidates`,
`r_cands_unit = ref_frame_candidates` 를 만든다. `unit.at_frame_idx is not None` 이고 `dtw_match`
가 있으면 합성 후보로 교체:
- 학생 후보 = `at_frame_idx ± _MOMENT_ANCHOR_RADIUS` 를 `[0, u_n-1]` clamp 후 중복 제거(순서 보존).
- 기준 후보 = 각 학생 후보에 대해 기존 2단 변환 재사용:
  `_matched_ref_frame(dtw_match, u_cand, _dtw_ref_frames)` → `_to_rep_idx(r_matched, _dtw_ref_fps,
  frames_fps, r_n)`. 이 식은 2452-2460 에 이미 있다 — **새 매핑 공식을 쓰지 말고 helper 로 뽑아
  양쪽이 공유**하게 한다(`_matched_ref_frame` 본체는 864-865 가 "수정 금지" 박제 — 호출만).
- 하나라도 None 이면 합성 후보 전체를 버리고 원래 파라미터로 복귀(fail-closed).
그 아래 기존 선택 블록(2506/2553)의 파라미터 참조를 `u_cands_unit`/`r_cands_unit` 으로 교체.
**선택·pose 매칭·crop·S9 정중앙·S10 다리선·S8 각도 베이크 로직은 한 줄도 건드리지 않는다.**

**★ 상수 이름 (W10):** `_POSE_TRAJ_RADIUS = 2`(`fault_zoom.py:460`)가 이미 있고 주석이
`features.window_median_angle_deltas window=2` 를 관행 출처로 인용한다. 그러나 **궤적 평균
반경**과 **앵커 후보 반폭**은 다른 개념이다 — 재사용하지 말고 `_MOMENT_ANCHOR_RADIUS` 를
별도 모듈 상수로 두고, 주석에 "값은 같은 관행 출처를 따르되 의미가 다르므로 별도 이름"을
적는다. 리터럴 2 를 코드에 흩지 말 것.

**(4) `atMatched` 인증 방출 (D-gbk-06).**
item dict(2911-2955)에 `item["atMatched"] = True` 를 **최종 채택 `u_idx_unit` 이
`unit.at_frame_idx` 와 정확히 같을 때만** 넣는다(불일치·앵커 부재는 키 생략 — `refMatch`/
`criterion` 의 additive 관례). `refMatched` 옆에 두고 주석에 "앱은 이 값만 보고 basis 절을
낸다 — 초 차이를 앱이 계산하면 F-3 이 재발한다"를 적는다.

**(5) `app.py` mode3 crit_units 미러.**
3340-3361 부근 인라인 `crit_units` 에도 `at_frame_idx` 를 같은 규칙으로 채운다. 한쪽만 고치면
mode3 가 조용히 구 동작으로 남는다.

**(6) 스위프 게이트** — `sweep_leg_angle.py` 구조를 따른다(합성 keypoint report + 등재 10동작 축 +
프로덕션 함수 직접 호출, GPU 0):
  (a) record 2건 이상·`atFrameIdx` 상이 → 카드 `userFrameIdx` 상이, 10/10.
  (b) `atFrameIdx` 전부 제거한 대조군 PNG sha256 == `sweep_out.before.json` (fail-closed 무회귀).
  (c) 앵커 프레임 confidence 를 0 으로 눌러도 창 안 다른 프레임 채택 + 그 카드 `atMatched` 부재.
  (d) 앵커 채택 카드는 `atMatched=true` 이고 `userFrameIdx` 가 `atFrameIdx` 와 **정확히 일치**.
  (e) override 경로(`ref_frame_idx` 지정) 스모크 — UnboundLocalError 0.
실행자는 **`sweep_out.json` 을 직접 열어 값을 확인한 뒤** 완료를 주장한다(코드 통과 != 확인,
`[[open-the-artifact-before-claiming-done]]`).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && set -o pipefail && PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_fault_zoom_record_moment.py 2>&1 | tail -5</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && set -o pipefail && backend/.venv/bin/python .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_record_moment.py --out .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_out.json --compare-before .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_out.before.json 2>&1 | tail -20</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python .planning/quick/260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt/legacy_baseline.py --verify</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff "$GBK_BASE" -- backend/ app/src/ | /usr/bin/grep '^+' | /usr/bin/grep -v '^+++' | /usr/bin/sed 's/^+//' | /usr/bin/grep -Ev '^[[:space:]]*(#|//|\*|/\*)' | /usr/bin/grep -Ec 'kip-up|power-spin|peter-pan|elbow-twist|pdshape|ref-climb|ref-combo' | { read n; test "$n" = "0" && echo NO-MOTION-BRANCH || { echo MOTION-LITERAL-ADDED=$n; exit 1; }; }</automated>
  </verify>
  <done>
스위프 게이트 (a)~(e) 전부 통과하고 실행자가 `sweep_out.json` 을 직접 열어 값을 확인.
`legacy_baseline.py --verify` = `PASS — 9 case / 9 card 해시 동일`.
`atFrameIdx` 제거 대조군이 `sweep_out.before.json` 과 byte-동일.
mode1/mode3 두 crit_units 생산자가 같은 규칙 보유. `_CropUnit` 생성부에 `at_frame_idx` 전달됨.
추가 비주석 줄에 동작명 리터럴 0.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: 앱 — 계약 수용 + basis 절을 사진-순간 일치에 게이트</name>
  <files>
app/src/lib/userAnalyses.ts,
app/src/lib/deductionSheet.ts,
app/src/lib/__tests__/deductionSheet.test.ts
  </files>
  <behavior>
    - `atMatched===true` 인 카드를 가진 record 만 "위 사진은 그 값을 잰 순간(N.N초)이에요" 절을 얻고, 그 초는 `rec.atVideoSec` 이다.
    - 카드가 없는 record(`line`·4장 초과분)는 `atVideoSec` 이 있어도 절이 없다.
    - `atMatched` 부재/false(앵커 미채택) 카드는 `atVideoSec` 이 있어도 절이 없다.
    - 절이 빠져도 앞 절("이 항목은 ...을 재요.")은 남고, 둘 다 불성립이면 basis 행 자체가 null.
    - malformed `atFrameIdx`/`atVideoSec`/`atMatched` 는 undefined 강등되고 record 자체와 기존 필드는 보존된다.
    - legacy doc(키 전부 부재)에서 크래시 0, 렌더 diff 0.
  </behavior>
  <action>
D-gbk-06 을 구현한다. 앱 변경은 이 3파일뿐이며 `cueTrack.ts`/`VideoCompare.tsx`/`result.tsx` 는
**diff 0** 이어야 한다(D-gbk-05).

**(1) `userAnalyses.ts::normalizeRecordPhraseFields`(368).**
`atVideoSec: normalizeFiniteNumber(raw.atVideoSec)` 추가. `atFrameIdx` 는
`normalizeFiniteNumber` 결과에 `Number.isInteger && >= 0` 게이트를 얹어 아니면 `undefined`.
함수 상단 주석(365-367)의 "malformed 는 undefined 강등하되 record 자체와 기존 필드는 보존"
규율을 그대로 따른다. `FaultZoomComparison.atMatched` 는 boolean 화이트리스트(`true` 만 통과,
그 외 undefined)로 zoom 정규화 경로에 추가한다.

**(2) `deductionSheet.ts` basis 게이트 교체(529·535·542-550).**
현행은 `blockZoom?.userVideoSec` 을 초 출처로 쓴다. 이것을 다음으로 바꾼다:
- 절 방출 조건 = `blockZoom != null && blockZoom.atMatched === true && rec.atVideoSec != null`
- 표시 초 = `rec.atVideoSec`
변수명을 `blockMeasuredSec` 등으로 바꿔 "표시 프레임의 초"가 아니라 "이 감점을 잰 초"임을
코드에서도 읽히게 한다. **문구는 손대지 않는다** — 승인본 카피 그대로, 새 카피 0.
주석에 quick-260801-gbk 와 "카드 없는 행·앵커 미채택 카드에 절을 내면 없애려던 거짓을 역방향
으로 재생산한다(D-gbk-06)"를 한국어로 적는다.

**주의 — `refSec`/`methodLine`/`pairCap` 은 건드리지 않는다.** method 행의 "기준 사진은 그
정렬이 실제로 짝지은 순간"(566)은 **기준 패널 표시 프레임**을 말하는 문장이라
`blockRefSec`(=`refVideoSec`)이 정확한 출처다. paircap 좌/우 초(488-495)도 두 패널의 **표시**
초라 그대로 둔다.

**(3) `deductionSheet.test.ts` 확장.**
`<behavior>` 6항목을 기존 관례(433-452행 형식)로 추가한다. 기존 433-452 테스트는
`userVideoSec` 기반이므로 `atMatched` + `atVideoSec` 조합으로 기대값을 옮긴다 — **문장 자체는
불변이고 방출 조건과 출처만 바뀐다.**
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npm run typecheck</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && set -o pipefail && node --test src/lib/__tests__/deductionSheet.test.ts 2>&1 | tail -10</automated>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && git diff "$GBK_BASE" --exit-code -- app/src/lib/cueTrack.ts app/src/components/VideoCompare.tsx app/src/app/analysis/result.tsx && echo CUE-UNTOUCHED</automated>
  </verify>
  <done>
basis 절이 `atMatched===true` 인 카드에서만 나오고 초는 `rec.atVideoSec`.
카드 없는 record·앵커 미채택 카드는 절 없음. `npm run typecheck` clean, `node --test` PASS.
`cueTrack.ts`/`VideoCompare.tsx`/`result.tsx` diff 0 (BASE 대비).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 앱 파싱 | 백엔드가 쓴 record/zoom 확장 키를 앱이 읽는다. 구 doc·malformed 값이 섞인다 |
| record dict → fault_zoom 인덱싱 | `atFrameIdx` 가 프레임 배열 인덱스로 쓰인다 — 범위 밖 값은 인덱싱 사고 |
| 산출 helper → 채점 substrate | 순간 산출 코드가 md/points 를 오염시키면 점수가 움직인다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-gbk-01 | Tampering | `_attach_translation_emission` 각인 | mitigate | `setdefault` 만 사용, 기존 키 무변경. `git diff "$GBK_BASE"` 로 `deduction_engine.py` diff 0 강제 (D-gbk-04) |
| T-gbk-02 | Denial of Service | `fault_zoom` 프레임 인덱싱 | mitigate | `atFrameIdx` 를 `max(0, min(idx, n-1))` clamp. 비정수/음수는 `criterion_units_from_records` 에서 None 강등 |
| T-gbk-03 | Information Disclosure | doc 신규 필드 | accept | 프레임 인덱스·초는 이미 `userFrameIdx`/`userVideoSec` 로 노출된 축의 값. PII 0 |
| T-gbk-04 | Tampering | 앱 malformed 값 소비 | mitigate | 유한·정수·비음수 + `atMatched` boolean 화이트리스트, 실패 시 undefined 강등 (Task 4) |
| T-gbk-05 | Elevation of Privilege | Firestore nested array | mitigate | scalar int/float/bool 3개만 방출 — 중첩 배열·dict 금지. `_validate_dict_only_scalars` 기존 경로 통과 |
| T-gbk-06 | Repudiation | 거짓 단정 재생산 | mitigate | basis 절을 `atMatched` 인증에 게이트 — 사진 없는 행·앵커 미채택 카드는 절 생략 (D-gbk-06) |
| T-gbk-SC | Tampering | 패키지 설치 | N/A | 신규 의존성 0 — npm/pip/cargo install 없음 |
</threat_model>

<verification>
## 플랜 전체 게이트

**0. 인터프리터·기준선** — `<execution_preamble>` 참조. `python` 은 PATH 에 없다.
   `cd backend && .venv/bin/python -m pytest -q` 는 **수집 에러 12건으로 테스트를 0개 실행**하므로
   회귀 게이트로 쓸 수 없다(실측). `PYTHONPATH=backend/tests` + repo 루트 실행만 유효.

**1. 채점 무접촉 (불변식 1)**
   - `git diff "$GBK_BASE" --exit-code -- backend/.../deduction_engine.py` = 0.
     (`--exit-code` 단독은 `git add` 한 번에 무력화된다 — 격리 리포 실측. BASE 고정 필수.)
   - `per_joint_deviation` / `extension_deviation` 본체 diff 0 →
     `backend/tests/phase33/test_m3_alignment_only.py::test_m3_constants_hash_unchanged`
     SHA-256 게이트가 이것을 강제한다 (현 트리 실측: 그 파일 + test_deduction_engine 85 passed).
   - fixture 대조: `measured_at` 주입 전/후로 record 의 `points`/`measuredValue`/`deviation` 과
     `breakdown.final` 동일 (Task 1·2 테스트).
   - 실 doc 재분석 시 `overallScore` 불변 (human-check 6번).

**2. 회귀 0 (착수 시점 캡처 대비)**

       PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 \
         | /usr/bin/grep -E '^(FAILED|ERROR)' | sort > /tmp/gbk-after.txt
       diff /tmp/gbk-before.txt /tmp/gbk-after.txt

   비어 있을 것. **수치를 상수로 박지 말 것** — 2026-08-01 실측은 `59 failed / 3767 passed /
   26 skipped, 수집 에러 0` 이고 이 값은 시간이 지나면 달라진다. 게이트는 diff 다.

**3. 일반화 (불변식 2)** — 등재 10동작 스위프 (a)~(e) + 동작명 리터럴 게이트.
   두 grep 게이트는 **BASE 대비 추가된 비주석 줄만** 본다. 전수 grep 은 쓸 수 없다 —
   실측(`git ls-files backend/functions backend/shared app/src | grep -E '\.(py|ts|tsx)$' |
   xargs grep -Eoh '<동작명>' | wc -l`) = **178회**(추적 파일 전체는 810회)이고,
   **총계는 스코프에 따라 달라진다** — git-추적 소스 확장자 한정이 178, 미추적/파생 포함
   재귀 grep 은 193~1977 로 튄다. 검증자 계측(145/681)과 수치가 다른 이유도 스코프다.
   **게이트 동작에는 영향이 없다**(diff 의 추가 줄만 보므로). 중요한 것은 성격이다 —
   **"전부 주석"도 아니다** — `gemini_motion_classifier.py:35-39`, `:88` 은 코드 리터럴이다.
   (직전 리비전이 "37회, 전부 주석"이라고 적은 것은 2개 파일만 세고 성격까지 단정한
   **오측이다** — `[[state-evidence-act-or-mark-unverified]]`.)
   `frames_fps=9.0` 2회(`app.py:2993`/`3033`, pre-existing)는 확인된 사실이다.
   스위프 하네스는 `backend/`·`app/src/` 밖(quick 디렉터리)이라 게이트 스코프 밖 —
   하네스는 10동작 id 를 당연히 쓴다.

**4. fail-closed (불변식 3)** — `atFrameIdx` 제거 대조군이 **HEAD 사전 캡처**
   (`sweep_out.before.json`)와 byte-동일. 구현 전에 캡처하지 않으면 대조군이 존재하지 않는다(W7).

**5. 계약 3자 (불변식 4)** — `test_contract_lockstep` PASS + contract.md §10.2/§11 갱신.

**6. 하위호환 (불변식 6)** — 신규 키 부재 legacy doc 에서 백엔드/앱 크래시 0.

**7. GPU 0** — 모든 자동 검증이 Pod 없이 로컬에서 돈다. 재추론이 필요한 설계면 잘못된 설계다
   (시계열은 이미 `per_joint_deviation` 안에 만들어졌다가 버려지고 있다).

**8. 범위 규율** — `cueTrack.ts` / `VideoCompare.tsx` / `result.tsx` diff 0 (BASE 대비, D-gbk-05).

**9. 종료코드 규율 (W8)** — `| tail` 로 끝나는 게이트는 파이프라인 종료코드가 tail 의 0 이라
   **실패할 수 없다.** 실측: `python -c 'sys.exit(3)' | tail` → rc 0, `set -o pipefail` 추가 시
   rc 3. 파이프가 있는 모든 `<automated>` 에 `set -o pipefail` 을 붙였다.
   같은 함정의 실사례가 직전 리비전의 `legacy_baseline.py --compare` 였다 — 그 플래그는
   존재하지 않아 `error: unrecognized arguments` 로 죽는데 게이트는 통과로 보였다.
   실측 확인된 올바른 호출은 `--verify` (→ `PASS — 9 case / 9 card 해시 동일`, rc 0).

## belle 실기기 확인 (done 조건 아님 — 오케스트레이터가 belle 에게 넘길 목록)

<human-check>
**선행:** Pod 기동 → 실 영상 재분석 → OTA 발행. 시뮬레이터와 합성 스위프로는 실 doc 의
카드 프레임 분산도, 음성 발화도 볼 수 없다 — 실행자는 이 6항목을 스스로 통과 처리하지 않는다.

**★ 확인 범위:** `tier=='confirmed'` 확대비교 카드만. **advisory(참고) 카드는 구조적으로
제외**된다(`app.py:3025-3053` 이 `criterion_units` 미전달 — record 가 없는 카드라 측정 순간도
없다). advisory 카드끼리 같은 프레임인 것은 이 플랜의 실패가 아니다.

**★ split 은 이번에 안 풀린다 (D-gbk-07):** 킵업의 **split 카드**는 프로덕션 경로가 vision
주입이라 시계열이 없어 fail-closed 다. 킵업에서 볼 것은 **어깨 카드**다.

1. 재분석 doc 의 `deductionBreakdown.records[]` 를 조회한다.
   - `angle_vs_reference__*` / `leg_extension` / `arm_extension` / `line` record 에
     `atFrameIdx`/`atVideoSec` 이 있는가.
   - **서로 다른 record 의 `atFrameIdx` 가 실제로 다른가** — 킵업 2건이 둘 다 16, 파워스핀
     4건 전부 38, 엘보 5건 전부 144 였던 것이 증상이다.
   - `body_relative_reach` / `dimension_overall_fallback` / `split_angle` record 에는 키가 **없는가**.
2. 같은 doc 의 `faultZoomComparisons[]`(confirmed)에서 `userFrameIdx` 가 카드마다 다른가.
3. 결과 화면에서 확대비교 카드를 항목별로 열어, 사진이 항목마다 다른 순간인가.
4. 시트의 "어디서 재나요" 행에서 — 사진이 있는 항목만 "잰 순간" 절이 있고 그 초가 record 별로
   다른가. 사진 없는 항목(`line` 등)에 그 절이 **없는가**.
5. 재생하면서 **두 번째 음성 큐가 발화되는가** — 종전엔 두 창이 완전히 겹쳐 영원히 묻혔다.
   (F-6 의 다른 무음 원인은 범위 밖 — 여기서 보는 것은 "두 번째 큐가 창을 갖는가"뿐이다.)
6. 회귀: 같은 영상의 `overallScore` 가 재분석 전후로 동일한가.
</human-check>
</verification>

<success_criteria>
- 4계열(`angle_vs_reference` window/DTW, `leg_extension`, `arm_extension`, `line`)의 record 가
  자기 측정 순간을 나른다 — reach·whole-score fallback·**vision split** 은 비어 있다.
- 확대비교 카드가 카드마다 자기 순간을 쓴다. 프레임이 같으면 측정 순간이 실제로 같을 때뿐이다.
- basis 절이 `atMatched===true` 인 카드에서만 나온다 — 사진 없는 행에 "위 사진은…" 이 없다.
- `deduction_engine.py` diff 0(BASE 대비), pytest FAILED/ERROR node ID diff 0, `npm run typecheck` clean.
- 등재 10동작 스위프 전 게이트 통과 + 실행자가 산출 JSON 을 직접 열어 확인.
- belle 실기기 확인 6항목은 `<human-check>` 로 분리 — **done 조건 아님**(Pod·OTA 선행 필요).
</success_criteria>

<output>
Create `.planning/quick/260801-gbk-record-atframeidx-criterion/260801-gbk-SUMMARY.md` when done.

SUMMARY 에 반드시 포함:
- criterion 별 순간 산출 규칙 표 (실제 구현된 것 — 계획과 다르면 다른 이유)
- 채점 무접촉 증거 (BASE 대비 엔진 diff 0 출력 + fixture 전/후 대조 실측값)
- pytest node ID diff 결과 (before/after 파일 경로 + 착수 시점 캡처 수치)
- 스위프 게이트 (a)~(e) 실측 결과 + `sweep_out.json` 에서 직접 읽은 값 인용
- **`split_angle` 이 안 풀렸다는 것을 명시** (D-gbk-07) — 킵업 split 카드는 여전히
  worst_seconds 프레임이다. "풀린다"고 뭉뚱그리지 말 것.
- fail-closed 로 남긴 criterion 과 그 이유
- 검증하지 못한 것과 그 이유 (실기기 음성·실 doc 카드 분산 등) — "안 재봤다"를 명시
</output>
</content>
