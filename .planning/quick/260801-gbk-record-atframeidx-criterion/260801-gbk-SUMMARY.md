---
phase: quick-260801-gbk
plan: 01
subsystem: analysis-output
tags: [fault-zoom, deduction-record, contract, display-frame]
requires: [deductionBreakdown.records, faultZoomComparisons, windowMedianAngleDeltas]
provides: [DeductionRecord.atFrameIdx, DeductionRecord.atVideoSec, FaultZoomComparison.atMatched]
affects: [pipeline/app.py, fault_zoom.py, motiondtw.py, dimensions.py, models.py, analysis.ts, deductionSheet.ts, userAnalyses.ts, contract.md]
tech-stack:
  added: []
  patterns: [out-param seam, sibling function (SHA-256 박제 우회 금지), fail-closed 인증 scalar]
key-files:
  created:
    - backend/tests/test_record_measured_at.py
    - backend/tests/test_record_moment_engraving.py
    - backend/tests/test_fault_zoom_record_moment.py
    - .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_record_moment.py
    - .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_out.before.json
    - .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_out.json
  modified:
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/shared/python/sunity_shared/analysis/motiondtw.py
    - backend/shared/python/sunity_shared/analysis/dimensions.py
    - backend/shared/python/sunity_shared/models.py
    - backend/tests/test_deduction_engine.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/lib/deductionSheet.ts
    - app/src/lib/userAnalyses.ts
    - app/src/lib/__tests__/deductionSheet.test.ts
decisions:
  - "대표 프레임은 집계값 최근접 — argmax 금지 (jitter 프레임 확대 방지)"
  - "split_angle 은 fail-closed — 실동작 경로가 vision 주입이라 잰 프레임이 없다"
  - "앵커는 점이 아니라 2단(앵커 단독 → 붕괴 시 ±2 창) — 창만 주면 tie-break 가 중앙 앵커를 구조적으로 이긴다"
  - "atMatched 는 백엔드 인증 scalar — 앱이 초 차이로 추정 금지"
metrics:
  duration: 약 2시간
  completed: 2026-08-02
---

# quick-260801-gbk: 감점별 측정 순간 기록 Summary

감점 record 마다 "이 값을 어느 프레임에서 쟀는가"(`atFrameIdx`/`atVideoSec`)를 방출하고,
확대비교 카드가 그 순간을 프레임 앵커로 쓰게 했다. 채점 무접촉.

---

## ★ belle 이 먼저 알아야 할 것 — 킵업 다리 스플릿 카드는 이번에 안 풀린다

**킵업에서 카드 2장이 둘 다 0.9초였던 것 중, 어깨 카드는 풀리고 다리(split) 카드는 안 풀린다.**

`split_angle` 의 프로덕션 실동작 경로는 **Gemini 비전 주입**이고 거기엔 시계열이 없다.
그 record 의 `measuredValue` 는 Gemini 추정치이지 우리가 어느 프레임에서 잰 값이 아니다.
기하에서 뽑은 프레임을 "여기서 쟀다"는 계약 아래 붙이면, 앱이 다시 "위 사진은 그 값을
잰 순간이에요"라고 말하게 된다 — **이 플랜이 없애려는 거짓과 정확히 같은 종류다.**
그래서 필드를 비웠다(fail-closed). 킵업 split 카드는 여전히 `worst_seconds` 프레임을 쓴다.

| belle 이 본 증상 | 이번에 풀리나 |
|---|---|
| 킵업 카드 2장이 둘 다 0.9초 — **어깨** | ✅ 풀린다 |
| 킵업 카드 2장이 둘 다 0.9초 — **다리(split)** | ❌ 안 풀린다 (fail-closed) |
| 파워스핀 카드 4장 전부 프레임 38 | ✅ 풀린다 (전부 `angle_vs_reference`) |
| 엘보 카드 5장 전부 프레임 144 | ✅ 풀린다 (전부 `angle_vs_reference`) |

**확인 범위는 `tier=='confirmed'` 카드로 한정해야 한다.** advisory(참고) 카드는
구조적으로 제외된다 — `app.py:3223-3224` 의 advisory 배치는 `criterion_units` 를 전달하지
않으므로(소스 직접 확인) unit 이 legacy fan-out 으로 만들어지고 `at_frame_idx` 가 항상
None 이다. **advisory 카드끼리 같은 프레임인 것은 이 플랜의 실패가 아니다.**

---

## criterion 별 순간 산출 규칙 (실제 구현된 것)

| criterion | 집계 (record 가 보고하는 값) | 순간 | 계획 대비 |
|---|---|---|---|
| `angle_vs_reference__{jk}` — Gemini pointed | `windowMedianAngleDeltas.deltas[].student_deg` | `sourceFrameIndices.user` **안에서** `abs(angles[t][j] − student_deg)` 최소 | 동일 |
| `angle_vs_reference__{jk}` — Gemini silent | `per_joint_deviation` = DTW path median | `match.start + path[k*][0]`, `k*` = median 최근접 스텝 | 동일 |
| `leg_extension` / `arm_extension` | 좌/우 중 max 관절의 `max(0, 180 − window mean)` | 그 관절의 `_select_window` 안 per-frame 부족분 최근접 | 동일 |
| `line` | 양수 부족분 EXTEND 관절 평균 | 같은 관절 집합 per-frame 평균 최근접 | 동일 |
| `body_relative_reach` | notch 부족분 | **필드 없음** (시계열 없음) | 동일 |
| `dimension_overall_fallback` | whole-score passthrough | **필드 없음** (특정 순간 없음) | 동일 |
| `split_angle` | vision 주입 편차 | **필드 없음** (잰 프레임 없음) | 동일 |

**argmax 를 쓰지 않았다.** 집계가 median/mean 인데 최대 편차 프레임을 가리키면 record 가
보고한 값과 다른 순간을 지목하고, jitter 프레임을 확대해 지금보다 나빠진다
(`motiondtw.py` 198-209행 근거). `test_moment_is_not_the_jitter_spike_frame` 이 이 회귀를 막는다.

pointed 경로는 **median 을 재계산하지 않는다** — `features._delta_entry` 가 emit 한
`student_deg` 를 그대로 읽는다. 재계산이 없으므로 drift 가 원리적으로 불가능하다.

---

## `atMatched` 가 실제로 몇 %의 카드에서 true 인가 — 측정값과 그 한계

**합성 스위프 실측: 30/30 카드 = 100.0%** (`sweep_out.json` 을 직접 열어 센 값).

```
ref-climb
   at= 4  card userFrameIdx= 4  atMatched=True  userVideoSec=0.4444  ref=4
   at= 9  card userFrameIdx= 9  atMatched=True  userVideoSec=1.0000  ref=9
   at=14  card userFrameIdx=14  atMatched=True  userVideoSec=1.5556  ref=14
```

**그러나 이 100% 를 실기기 기대치로 읽으면 안 된다.** 합성 report 는 모든 프레임 confidence
가 0.9 라 앵커가 항상 크롭 가능하다. 프로덕션에서 `atMatched=true` 의 조건은:

> 앵커 프레임의 그 카드 멤버 keypoint 중 최소 1개가 `_KP_CONF_MIN`(=0.5) 이상

앵커 keypoint 가 붕괴한 프레임(역립 구간 등)에서는 ±2 창으로 넓혀 다른 프레임을 고르고
`atMatched` 가 붙지 않는다 — 그 카드는 basis 절을 잃는다. **실 doc 에서의 비율은 재지 않았다.**
Pod 재분석 전에는 잴 방법이 없다(합성 fixture 로는 그 분포를 만들 수 없다).

**설계 이력 — 이 수치는 처음엔 0% 였다.** 최초 구현은 플랜대로 앵커 ±2 를 통째로 후보로
줬는데, `select_confident_frame` 의 동점 tie-break 가 **항상 가장 작은 프레임값**을 고르므로
(`fault_zoom.py` 429-432행) 중앙에 놓인 앵커가 구조적으로 이길 수 없었다. 스위프 실측
`atMatched=true` **0/30**. 그대로 출하했으면 basis 절이 사실상 영구 소멸해 belle 이
"문장이 없어졌다"고 읽었을 것이다. → 후보 구성을 2단으로 바꿨다(아래 Deviation 2).

---

## 채점 무접촉의 근거 — "통과했다"가 아니라 출력값

**① `deduction_engine.py` BASE 대비 diff 0 (구조적 증명)**

```
$ git diff dd3033f2 --stat -- backend/shared/python/sunity_shared/analysis/deduction_engine.py
(출력 없음)
$ git diff dd3033f2 --exit-code -- .../deduction_engine.py && echo "ENGINE-DIFF-0 (exit 0)"
ENGINE-DIFF-0 (exit 0)
```

`--exit-code` 단독이 아니라 **BASE(`dd3033f2`) 고정 비교**를 썼다 — `git add` 한 번에
무력화되지 않는다. 각인은 `tally` 가 끝난 뒤 `_attach_translation_emission` 이
`setdefault` 로 하므로 **점수를 계산하는 코드가 이 값을 볼 수 없다.**

**② pytest 기준선 diff (착수 시점 캡처 대비)**

착수 캡처(2026-08-02, `PYTHONPATH=backend/tests` + repo 루트):
```
59 failed, 3766 passed, 27 skipped, 42 warnings in 45.59s
수집 에러 0 (grep -c 'errors during collection' = 0)
FAILED/ERROR node ID 59줄
```
종료 시:
```
59 failed, 3801 passed, 27 skipped, 42 warnings in 40.08s
$ diff gbk-before.txt gbk-after.txt ; echo "diff-exit=$?"
diff-exit=0
```
**FAILED/ERROR node ID diff 완전히 빔.** passed 3766 → 3801 (+35 = 신규 테스트 35건:
14 + 8 + 13). before/after 파일 =
`<scratchpad>/gbk-before.txt`, `<scratchpad>/gbk-after.txt`.
(플랜이 적은 착수 수치 `59 failed / 3767 passed / 26 skipped` 와 skipped 가 1 다르다 —
환경 의존 skip. 게이트는 수치가 아니라 diff 이고 그 diff 는 비었다.)

**③ `legacy_baseline.py --verify`**
```
PASS — 9 case / 9 card 해시 동일
```

**④ `md` 불변 단위 게이트** — `test_md_is_identical_with_and_without_out_param` 이
`measured_at_out` 전달 유무에 따른 `md` 키·값 동등을 단정한다(PASS).

**⑤ `per_joint_deviation` SHA-256 박제** — `test_m3_constants_hash_unchanged` PASS.
sibling 함수를 추가했을 뿐 본체는 한 글자도 고치지 않았다.

---

## 스위프 게이트 (a)~(e) 실측 — `sweep_out.json` 에서 직접 읽은 값

**구현 전 대조군을 먼저 캡처했다**(순서 강제). 캡처 시점의 스위프는 **실제로 FAIL 했다** —
게이트가 결함을 탐지할 수 있음이 증명된 상태에서 대조군이 만들어졌다:

```
(구현 전) 동작 10개 · (a) 카드 프레임 상이: 0/10 · FAIL 20건
  - (a) ref-climb: record 순간이 다른데 카드 프레임이 같다 [8, 8, 8]
  ... 10동작 전부 동일 (belle 이 본 증상 그대로 재현)
```

구현 후:
```
동작 10개 · (a) 카드 프레임 상이: 10/10
(b) fail-closed 대조군: sweep_out.before.json 과 대조 완료
PASS — 게이트 (a)~(e) 전부 통과
```

| 게이트 | 실측 |
|---|---|
| (a) 순간이 다르면 카드 프레임도 다름 | **10/10 동작**. 30 카드 전부 `userFrameIdx == atFrameIdx` (4/9/14) |
| (b) `atFrameIdx` 제거 대조군 byte-동일 | 10동작 PNG sha256 일치. 대조군 프레임은 여전히 `[8, 8, 8]` |
| (c) 앵커 붕괴 시 창 구제 + 인증 없음 | `[('av_left_shoulder', 2, None), ('av_right_shoulder', 7, None), ('av_left_hip', 12, None)]` — 앵커(4/9/14) 아닌 프레임 채택, `atMatched` 전부 부재 |
| (d) 앵커 채택 카드 정확 일치 | 30/30, `atMatched=True` |
| (e) override(`ref_frame_idx`) 스모크 | 10동작 각 3카드, `override_error: None` |

재실행 결정성도 확인 — 두 번째 실행이 `sweep_out.json` 과 byte-동일(`git diff` 빔).

---

## fail-closed 로 남긴 것과 이유

| 대상 | 이유 |
|---|---|
| `body_relative_reach` | `bodyRelativeNotches` 에 시계열이 없다 |
| `dimension_overall_fallback` | whole-score passthrough — 특정 순간이 존재하지 않는 record |
| `split_angle` | 실동작 경로가 vision 주입 — **우리가 잰 프레임이 없다** |
| pointed 관절 중 `student_deg` 비유한 | 근거값이 없으면 최근접 판정이 불가 |
| DTW median 이 NaN 인 관절 | 그 관절은 record 자체가 방출되지 않는다 |
| fps 를 못 구함 | `video_sec` 생략, `frame_idx` 만 (초를 추측하지 않는다) |
| 앵커 DTW 대응 실패 | 합성 후보 통째 폐기 → 종전 경로 |
| advisory 카드 | `criterion_units` 미전달 (구조적) |

---

## Deviations from Plan

### 1. [Rule 3 - Blocking] `_pipeline_frame_fps()` 가 테스트 환경에서 죽는다

- **발견:** Task 1. `_FRAME_EXTRACTOR` 미초기화 시 `frame_extractor` 를 import 하는데
  venv 에 `imageio` 가 없어 `ModuleNotFoundError`. 플랜대로 `_moment_fps = _pipeline_frame_fps()`
  를 무방비로 부르면 out-param 을 준 순간 빌더가 죽는다.
- **조치:** try/except 로 감싸 실패 시 `fps=0` → `video_sec` 생략, `frame_idx` 는 유지.
  플랜의 "fps <= 0 이면 video_sec 생략" 규정과 같은 처분이다. 초를 추측해 채우지 않는다.
- **커밋:** c00ebb1b

### 2. [Rule 1 - Bug] 앵커 후보를 창으로만 주면 `atMatched` 가 영영 성립하지 않는다

- **발견:** Task 3, 스위프 실행 후. 플랜 (3) 대로 `at_frame_idx ± _MOMENT_ANCHOR_RADIUS`
  를 후보로 줬더니 카드 프레임은 갈렸지만(게이트 a 통과) **`atMatched=true` 가 0/30**.
  원인: `select_confident_frame` 이 동점에서 **가장 작은 프레임값**을 고르므로
  (`fault_zoom.py` 429-432행) 중앙에 놓인 앵커가 구조적으로 이길 수 없다. 선택된 것은
  항상 `anchor - 2` 였다.
- **왜 그냥 두면 안 되는가:** basis 절이 사실상 영구 소멸한다. belle 관점에서는 "설명
  문장이 통째로 없어진" 것으로 보인다 — 플랜이 명시적으로 경계한 실패 모드.
- **조치:** 후보 구성을 2단으로. ① 앵커 프레임의 멤버 keypoint 가 크롭 가능하면
  (`_member_pts` valid 비어있지 않음 — 카드가 학생 패널을 그릴 때 쓰는 **기존 프로덕션
  술어**, 새 임계 0) 후보를 앵커 하나로 좁힌다. ② 붕괴 시에만 ±2 창으로 넓힌다.
  공유 선택 로직(`select_confident_frame`/`select_pose_matched_pair`)은 무접촉 —
  후보 목록만 바꿨다. 플랜의 (c)(d) 의도와 정확히 일치한다.
- **커밋:** 03dcffdc

### 3. [Rule 2 - Missing critical] `_render_fault_zoom` 매퍼에 `atMatched` pass-through 누락

- **발견:** Task 3. 플랜은 `fault_zoom` 방출과 앱 소비만 명시했는데, 그 사이 매퍼
  (`app.py:3276` 부근)가 **화이트리스트**다. 추가하지 않으면 doc 에 `atMatched` 가 아예
  안 실려 Task 4 의 basis 절이 100% 사라진다(no-op 출하).
- **조치:** `refMatched` 선례와 같은 형식으로 조건부 복사 추가.
- **커밋:** 03dcffdc

### 4. [계획 조정] 스위프 record criterion 을 "양쪽 report 에 있는 관절"로 한정

- **발견:** 최초 대조군 캡처에서 10동작 중 5동작이 카드 1장만 냈다. 원인은 합성 기준
  report 가 phase4_v1 legacy **8관절**이라 팔꿈치 criterion 카드가 crop 단계에서 통째로
  떨어진 것. 그 상태에서는 게이트 (a)가 "카드 1장이라 자명하게 상이"로 **거짓 통과**한다.
- **조치:** record criterion 을 두 report 에 모두 있는 관절로 한정(동작명 분기가 아니라
  **report 관절 집합 파생** 규칙). 결과: 10동작 전부 3카드 → 게이트가 10동작 모두에서
  실질 판정. 대조군은 이 상태로 재캡처했다(fault_zoom 미변경 시점이라 유효).
- **커밋:** 03dcffdc

### 5. [계획 조정] 테스트 fixture fps 를 비기본값으로

- **발견:** `9.0` 리터럴 게이트가 신규 테스트의 `_FPS = 9.0` 을 잡았다.
- **조치:** 12.0 으로 변경. 게이트 회피가 아니라 **더 강한 검사**다 — 프레임/초 변환이
  인자로 받은 fps 를 실제로 쓰는지, 기본값을 가정하는지를 값으로 구분한다.
- **커밋:** c00ebb1b(Task 1분), fe07774c(Task 3분)

### 6. [계획 조정] Task 2 테스트를 별도 파일로

- 플랜은 Task 2 테스트 파일을 명시하지 않고 `test_deduction_engine.py` 확장만 적었다.
  각인 additive 단정은 성격이 달라 `test_record_moment_engraving.py` 를 신설했다.
  `test_contract_lockstep` 4-set 확장은 계획대로 기존 파일에서 했다.
- vision split record-level fail-closed 단정은 플랜이 Task 1 에 배치했으나, record 는
  Task 2 에서야 생기므로 **빌더 단위(Task 1) + record 단위(Task 2) 두 곳**에 나눠 넣었다.

---

## 검증하지 못한 것 — "안 재봤다"

실기기·실 doc 검증은 **하나도 하지 않았다.** 아래는 전부 미측정이다.

| 항목 | 상태 | 이유 |
|---|---|---|
| 실 doc 의 `atMatched` true 비율 | **안 쟀다** | Pod 재분석 필요. 합성 fixture 로는 keypoint 붕괴 분포를 만들 수 없다 |
| 실 doc 카드 프레임이 실제로 갈리는지 | **안 봤다** | 합성 스위프는 프로덕션 함수를 직접 호출하지만 실 keypointReport 가 아니다 |
| 결과 화면 렌더 (시뮬레이터) | **안 봤다** | 이번 사이클에서 시뮬레이터를 띄우지 않았다. `npm run typecheck` 는 렌더 크래시를 못 잡는다 |
| 두 번째 음성 큐 발화 | **안 들었다** | 재생 화면 문제. F-6 의 다른 무음 원인은 범위 밖이고, 여기서 만든 것은 "두 번째 큐가 창을 갖는가"의 **전제**(프레임 분리)뿐이다 |
| 실 영상 `overallScore` 재분석 전후 동일 | **안 돌렸다** | 코드 게이트(엔진 diff 0 + pytest diff + `md` 불변 + legacy_baseline)로만 방어했다 |
| mode3 실경로 | **안 돌렸다** | `crit_units` 미러는 넣었지만 mode3 doc 으로 확인하지 않았다 |

**코드 게이트 통과 ≠ belle 확인.** 위 6항목은 Pod 기동 → 실 영상 재분석 → OTA 발행 후
belle 이 실기기에서 봐야 한다.

---

## Known Stubs

없음. 이번 변경에 하드코딩 빈값·placeholder·미배선 데이터 소스는 없다.

---

## Threat Flags

없음. 신규 네트워크 엔드포인트·인증 경로·파일 접근·신뢰경계 스키마 변경 0.
방출한 3필드는 이미 노출된 축(`userFrameIdx`/`userVideoSec`)의 값이고 PII 0.
신규 의존성 0 (npm/pip install 없음).

---

## 실행 환경 메모

워크트리에 `backend/.venv` 와 `app/node_modules` 가 없어 메인 체크아웃
(`/Users/kimtaesung/Dev/SunityMotion`)의 것을 **심볼릭 링크**해 게이트를 돌렸다.
패키지 설치 0, 네트워크 0, 메인 체크아웃 수정 0. **작업 종료 시 두 링크 모두 제거**했고
워크트리는 clean 이다. pytest 가 재생성한 추적 `.pyc` 2개도 원복했다.

---

## Commits

| hash | 내용 |
|---|---|
| `c00ebb1b` | Task 1 — helper 3종 + `measured_at_out` out-param |
| `8e55b387` | Task 2 — record 각인 + 계약 3자 미러 |
| `03dcffdc` | Task 3 — fault_zoom 앵커 + `atMatched` + 스위프 |
| `fe07774c` | Task 3 후속 — 테스트 fps 리터럴 제거 |
| `ab9da85e` | Task 4 — 앱 basis 절 게이트 |

---

## Self-Check: PASSED

- 신규 파일 7종 전부 존재 확인 (`ls` 로 직접 확인 — 3 test + 3 sweep 산출 + SUMMARY).
- 커밋 5개 전부 `git cat-file -t` 로 `commit` 확인 + `git log` 에 존재.
- 워크트리 clean (`git status --short` 빈 출력), 심볼릭 링크 제거 완료.
