---
phase: quick-260802-czw
plan: 01
subsystem: verification-harness
tags: [real-fixture, replay, recon-gate, fault-zoom, deduction-record]
requires: [DeductionRecord.atFrameIdx, faultZoomComparisons, windowMedianAngleDeltas, keypointReport]
provides: [backend/evals/realfixture, replay_out.json, RECON gate]
affects: []
tech-stack:
  added: []
  patterns: [죽는 어댑터 스텁, RECON 정답지 박제, 대조군/처리군 1변수 분리, 어댑터 경계만 치환]
key-files:
  created:
    - app/scripts/pull-real-fixtures.mjs
    - backend/evals/realfixture/replay.py
    - backend/evals/realfixture/fixtures/MANIFEST.json
    - backend/evals/realfixture/fixtures/{4 분석}.json
    - backend/evals/realfixture/fixtures/reference/{4 기준}.json
    - .planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json
  modified:
    - .planning/quick/260801-gbk-record-atframeidx-criterion/sweep_record_moment.py
decisions:
  - "재현 못 한 record 로는 판정하지 않는다 — RECON 게이트가 record 단위로 가린다"
  - "hold_window·vision differences 는 doc 밖 — 역산해 맞추지 않고 비워 둔다"
  - "카드는 production _build_fault_zoom_comparisons 를 그대로 돌리고 어댑터 2곳만 치환"
  - "대조군/처리군은 같은 record 집합에서 atFrameIdx 유무만 다르다 (처리 변수 1개)"
metrics:
  duration: 약 2시간
  completed: 2026-08-02
---

# quick-260802-czw: 실 doc 재생 하네스 + 첫 실물 판정 Summary

저장된 분석 doc 만으로 채점 → record → 카드 프레임 구간을 GPU 0 · Gemini 0 · Pod 0 ·
Firestore 쓰기 0 으로 재현하는 상설 하네스를 만들고, 그 하네스로 첫 판정을 냈다.

---

## ★ 판정 — quick-260801-gbk 는 실 데이터에서 **갈렸다**

**무게중심 = `elbowtwistsisterFault1785373695`.** record 8건이 전부
`angle_vs_reference__*`(geometry)이고 관절이 8개 전부 다르다. 이 fixture 는
**RECON 8/8 MATCH** — 재현본이 저장 record 와 measuredValue·points·final 까지 일치한다.
판정을 내릴 자격이 있는 유일한 fixture다(나머지 3건은 재현 record 가 1건씩이라
"갈렸는지"를 물을 대상이 없다).

| 관절 record | `atFrameIdx` | `atVideoSec` |
|---|---|---|
| `angle_vs_reference__left_elbow` | **27** | 3.000 |
| `angle_vs_reference__right_elbow` | **44** | 4.889 |
| `angle_vs_reference__left_shoulder` | **67** | 7.444 |
| `angle_vs_reference__right_shoulder` | **27** | 3.000 |
| `angle_vs_reference__left_hip` | **30** | 3.333 |
| `angle_vs_reference__right_hip` | **54** | 6.000 |
| `angle_vs_reference__left_knee` | **134** | 14.889 |
| `angle_vs_reference__right_knee` | **18** | 2.000 |

**서로 다른 프레임 7개 / record 8건** (left_elbow 와 right_shoulder 만 27 로 겹침).
0.0초부터 14.9초까지 흩어져 있다. **뭉치지 않았다.**

그리고 그 순간이 카드까지 도달한다:

| | 카드 `userFrameIdx` (keypointReport 18fps 공간) |
|---|---|
| 저장 doc (belle 이 본 것) | `144, 144, 144, 144, 144` |
| 대조군 (같은 record, `atFrameIdx` 제거) | `144, 144, 144, 144, 144` |
| **처리군 (`atFrameIdx` 있음)** | **`54, 88, 134, 54, 144`** |

**대조군이 저장 카드 프레임을 정확히 재현했다**(`cardRecon=REPRODUCED`, criterion 단위로
4/4 MATCH). 그러니 처리군의 델타는 하네스의 부작용이 아니라 `atFrameIdx` 하나의 효과다 —
두 팔의 처리 변수가 그것뿐이다. 마지막 144 는 advisory 카드로, `criterion_units` 를 받지
않아 구조적으로 앵커가 없다(gbk 가 이미 기록한 사실).

**단, 이 판정은 "belle 이 실기기에서 다른 사진을 본다"가 아니다.** 프레임 배열이 합성이라
PNG 픽셀 내용은 무의미하다. 여기서 증명된 것은 **선택된 프레임 인덱스가 갈렸다**는 것뿐이다.
사진이 실제로 다른 순간인지는 B 단계(아래).

---

## 실 데이터 `atMatched` 비율 — 재봤다

`replay_out.json` 을 열어 센 값이다.

| 분모 | 값 |
|---|---|
| 전체 카드 | **8 / 13 = 61.5%** |
| confirmed 카드만 | **8 / 10 = 80.0%** |
| (참고) 합성 스위프 | 30 / 30 = 100% |

두 분모를 다 적는 이유: advisory 카드 3장은 `criterion_units` 미전달로 **구조적으로**
`atMatched` 를 가질 수 없다. 전체 비율만 내면 그 구조적 제외가 실패처럼 읽힌다.

앵커를 놓친 confirmed 카드 2장:
- `powerspin / angle_vs_reference__right_hip` — 앵커 11, 채택 13 (앵커 keypoint 붕괴 → ±2 창 구제).
  이 record 는 RECON 미일치라 판정에서도 빠져 있다.
- `pdshape / angle_vs_reference__right_knee` — 앵커 81, 채택 80.

**합성 100% 는 역시 실기기 기대치가 아니었다.** gbk SUMMARY 의 경고가 실측으로 확인됐다.

---

## RECON 게이트 결과 — 무엇을 재현했고 무엇을 못 했나

`replay.py --recon-only` exit code **1** (전건 MATCH 가 아니므로). record **11/16 MATCH**.

| fixture | 저장 final | 재현 final | record 결과 |
|---|---|---|---|
| `elbowtwistsisterFault…` | 63 | **63** | **MATCH 8/8** (PASS) |
| `pdshapeCorrect…` | 100 | **100** | **MATCH 1/1** (PASS) |
| `kipupFault…` | 79 | 99 | MATCH 1 · MISSING 1(`split_angle`) |
| `powerspinFault…` | 60 | 62 | MATCH 1 · MISMATCH 1(`leg_extension`) · MISSING 1(`split_angle`) · EXTRA 2 |

**재현하지 못한 3종과 그 이유 — 전부 입력이 doc 밖이다. 역산해 맞추지 않았다.**

1. **`split_angle` 2건 (MISSING).** vision 주입 record 다. 산출 입력은
   `supported_differences` 의 명시 각도쌍인데, doc 에 남은 것은 fold 된
   `rootCauseHypotheses`(`faultKey` + 텍스트 + supportCount)뿐이라 각도가 없다.
   추정으로 채우면 그 fixture 의 판정이 하네스의 창작이 된다.

2. **`leg_extension` 1건 (MISMATCH, 79.34 → 141.04).** `dimensions._select_window` 창
   의존 criterion 이다. 창은 `profile.hold_window`(Gemini KeyMoment 파생)가 정하는데
   그 값이 분석 doc 에 없다. 자동 창(63,83)으로 돌면 141.04 가 나온다.
   **진단은 했다**(아래 "다음 사이클로" §1) — 그러나 창을 역산해 맞추는 것은 하지 않았다.

3. **`angle_vs_reference__{left,right}_hip` 2건 (EXTRA).** 이건 별개의 편차가 아니라
   위 1번의 **기계적 파생**이다. `split_angle.joint_keys = (left_hip, right_hip)` 이고
   `deduction_engine.py:306-311` 이 활성 `split_angle` 이 claim 한 관절의
   `angle_vs_reference__{jk}` 를 discard 한다. `split_angle` 을 재현하지 못하니
   cross-exclusion 이 걸리지 않아 hip record 2건이 살아남았다.
   (러너가 이 원인을 계약에서 파생해 출력에 붙인다 — fixture 별 하드코딩 0.)

**카드 경로는 criterion 단위로는 4/4 fixture 전부 재현됐다.**

| fixture | 저장 카드 criterion | 저장 프레임 | 대조군 | 판정 |
|---|---|---|---|---|
| powerspin | `leg_extension` | 38 | 38 | MATCH |
| powerspin | `angle_vs_reference__left_shoulder` | 38 | 38 | MATCH |
| powerspin | `split_angle` | 38 | — | ABSENT (record 미재현) |
| kipup | `angle_vs_reference__left_shoulder` | 16 | 16 | MATCH |
| kipup | `split_angle` | 16 | — | ABSENT |
| pdshape | (advisory, criterion 없음) | 104 | 104 | 전체 일치 |
| elbowtwist | `angle_vs_reference__{4종}` | 144 ×4 | 144 ×4 | MATCH ×4 |

`cardRecon` 플래그가 powerspin·kipup 에서 `NOT_REPRODUCED` 인 것은 **프레임 값이 틀려서가
아니라 카드 장수가 달라서**다(재현 못 한 record 가 카드 수를 바꾼다). 값은 전부 맞았다.

---

## GPU 0 · Gemini 0 · Pod 0 · Firestore 쓰기 0 — "안 불렀다"가 아니라 "불렸으면 죽었다"

어댑터와 쓰기 경로는 **호출되면 RuntimeError 로 죽는** 스텁으로 갈아끼웠고, 실제로 불러서
죽는 것을 확인했다:

```
BLOCKED _FRAME_EXTRACTOR.extract      BLOCKED complete_analysis
BLOCKED _POSE_ESTIMATOR.estimate      BLOCKED update_analysis_status
BLOCKED _COACH_WRITER.write           BLOCKED fail_analysis
BLOCKED _RTMW_ENGINE.infer            BLOCKED store_gemini_cache
BLOCKED _POLE_DETECTOR.detect         BLOCKED record_unregistered_keyword
BLOCKED _s3.put_object                BLOCKED update_analysis_fault_zoom
                                      BLOCKED _db
```

`firestore_admin` 차단 24종(쓰기 함수 전부 + `_db`/`_doc`). `_db` 까지 막은 이유는 쓰기 0 을
"쓰기 함수를 안 불렀다"가 아니라 **"Firestore 에 닿지 않았다"**로 증명하기 위해서다.
그 스텁을 단 채 전체 재생이 완주했다 = 재생 경로가 GPU·네트워크·Firestore 를 한 번도
타지 않았다.

**예외 1곳 (명시):** 카드 렌더 구간에서만 `_s3` 를 "죽는 스텁"에서 **메모리 기록 스텁**으로
바꾼다. production `_render_fault_zoom` 의 매퍼(여기에 `atMatched` pass-through 가 있다)를
실제로 실행시키기 위해서다. 기록 스텁은 `put_object`/`generate_presigned_url` 외의 모든
속성 접근에서 죽고, 구간이 끝나면 `finally` 가 즉시 원래 스텁으로 되돌린다. 네트워크 0.

**Gemini 는 이 경로에서 어댑터가 생성조차 되지 않는다** — recognizer 는 죽는 스텁이고,
기술 프로파일은 `GeminiTechniqueRecognizer._build_profile`(yaml 조회만 하는 순수 조립기)로
만든다. Pod 은 기동하지 않았다.

**Firestore 읽기는 Task 1 박제 때 1회만** (`pull-real-fixtures.mjs`, 읽기 전용). 그 뒤로는
리포에 박제된 JSON 만 읽는다.

---

## fixture 박제 — 무엇을 어떻게 뺐나

- 분석 4건 + 기준 4건 + MANIFEST, **총 3854 KB** (플랜 예상 ~3.0 MB 대비 +28%).
- **필드 화이트리스트 없음.** 전체 doc 을 그대로 쓴다.
- presigned URL 은 **값 기준 재귀 strip** — `X-Amz-Signature` 를 포함하는 문자열 값
  전부(24 경로: `videoUrl`, `result.myVideoUrl`, `result.referenceVideoUrl`,
  `result.faultZoomComparisons[*].imageUrl`). 키 이름 기준이 아니라 값 기준이라 새 URL
  필드가 생겨도 자동으로 잡힌다. **커밋 전 확인: `grep -rl 'AKIA'` = 0,
  `grep -rl 'X-Amz-Signature'` = 0** (T-czw-01 해소).
- fps 리터럴 0. `studentAnglesFps = krFps × anglesFrames ÷ krFrames` 로 파생하고
  4건 정합 assert 통과 시에만 기록 — 실측 **학생 9.0 / 기준 18.0**.
  러너는 이 값을 주입 FrameExtractor 의 `target_fps` 로 노출해
  `app._pipeline_frame_fps()` 가 production 경로 그대로 읽게 한다.
- 정답지(`sourceRecordCriteria` 14건 / `sourceCardFrames` 12건)를 MANIFEST 에 함께 박제 —
  Firestore doc 이 재분석으로 덮어써져도 대조 대상은 리포에 남는다.

---

## Deviations from Plan

### 1. [Rule 3 - Blocking] `hold_window` 를 doc 에서 구할 수 없다 → 채우지 않았다

- **발견:** Task 2 RECON. power-spin `leg_extension` 79.34 vs 141.04.
- **플랜 전제와의 차이:** 플랜 D-1 은 "저장 산출물만으로 채점 구간이 재현된다"를 게이트로
  증명하겠다고 했다. 게이트가 **그 전제의 부분 반증**을 냈다 — 창 의존 criterion 은
  저장 산출물만으로 재현되지 않는다.
- **조치:** 플랜의 "추정해서 채우지 말 것" 규칙대로 비워 두고 record 단위 MISMATCH 로
  표기 + 구조적 원인을 출력에 첨부. 판정에서 그 record 를 제외.
- **왜 역산하지 않았나:** 창을 역산해 맞추면 게이트는 통과하지만 그 fixture 의 판정이
  하네스의 창작이 된다. 게이트의 존재 이유와 정반대다.

### 2. [계획 조정] `split_angle` 재현 불가가 밝혀져 `failClosed` 관측이 성립하지 않았다

- **플랜 기대:** `replay_out.json.failClosed[]` 에 `split_angle` 2건이 들어와야 정상
  (gbk 설계상 순간이 없는 record).
- **실제:** `failClosed` 는 4 fixture 전부 **빈 배열**이다. 그 record 자체가 재현되지
  않았기 때문이다.
- **조치:** 산출물 `limits` 에 "failClosed 가 빈 것은 fail-closed 가 깨졌다는 뜻이
  **아니다** — 관측 범위 밖이다"를 명시. **`split_angle` 의 fail-closed 는 이 사이클에서
  확인되지 않았다.**

### 3. [계획 조정] 판정 문장을 3갈래로 (플랜은 2갈래)

- 플랜은 "`distinctAtFrameIdx` == record 수 → 갈렸다 / 1개로 뭉침 → 실패" 두 갈래만
  정의했다. 실측은 **7 distinct / 8 record**(겹친 쌍 1건)로 중간에 떨어졌다.
- **조치:** `distinct == 1` → 뭉쳤다(실패), `distinct == judged` → 전부 갈렸다,
  그 사이 → **갈렸다(부분 중복) + 정확한 수치**. belle 이 본 증상은 "전부 같은 프레임"
  이므로 실패 기준은 `distinct == 1` 이 맞다. 어느 갈래든 원시 수치를 그대로 낸다.
- **게이트 완화 아님:** 판정은 exit code 에 영향을 주지 않는다(플랜 Task 2 규약).
  exit code 는 여전히 RECON 전건 MATCH 만 0 이고, 실제로 1 이 나왔다.

### 4. [계획 조정] 카드 렌더를 `build_fault_zoom_comparisons` 직접 호출이 아니라 어댑터 치환으로

- **플랜:** `fault_zoom.criterion_units_from_records` + `build_fault_zoom_comparisons` 를
  하네스가 직접 인자 조립해 호출.
- **문제:** 그러면 `_build_fault_zoom_comparisons`(fault_joints·deficits·advisory·
  split 게이트·`stamp_ref`·`motion_id` 조립)와 `_render_fault_zoom`(item 매퍼 —
  **`atMatched` pass-through 가 사는 곳**)을 하네스가 복제하게 된다. 플랜 자신의
  "하네스가 규칙을 복제하지 않는다" 규율 위반이고, gbk Deviation 3 이 "매퍼 화이트리스트
  누락"으로 데였던 바로 그 코드가 검증에서 빠진다.
- **조치:** production `app._build_fault_zoom_comparisons` 를 **그대로** 부르고,
  영상→프레임 어댑터(`FfmpegFrameExtractor`)와 S3 업로드 두 곳만 치환. 인자 조립은 전부
  production 이 한다.

### 5. [계획 조정] 대조군을 "저장 record" 가 아니라 "재현 record − atFrameIdx" 로

- 저장 record 를 대조군으로 쓰면 power-spin 에서 record 집합 자체가 달라져 처리 변수가
  둘이 된다. 대조군/처리군을 **같은 재현 record 집합**에서 `atFrameIdx` 유무로만 가르고,
  저장 카드와의 대조는 **별도 축**(`cardReconByCriterion`)으로 뒀다.

### 6. [환경] pytest 기준선 파일을 `/tmp` 대신 세션 scratchpad 에

- 플랜 verify 는 `/tmp/czw-before.txt` 를 적었으나 이 실행 환경 규약이 scratchpad 사용을
  요구한다. 경로만 다르고 게이트(diff)는 동일하다.

---

## 게이트 실측

| 게이트 | 결과 |
|---|---|
| fixture 파일 수 | `fixtures/*.json` 5 · `reference/*.json` 4 |
| presigned URL 잔재 | `X-Amz-Signature` 0 · `AKIA` 0 |
| `studentAnglesFps` / `referenceAnglesFps` | 9.0 / 18.0 (4건 정합 assert 통과) |
| RECON exit code | **1** (전건 MATCH 아님 — 정직) |
| 어댑터·쓰기 차단 실증 | 13종 호출 → 전부 RuntimeError |
| 재실행 결정성 | 2회 산출 byte-동일 (`DETERMINISTIC-OK`) |
| PNG 바이트 미포함 | 산출물에 `png` 키 0 · `png_sha256` 만 |
| pytest FAILED/ERROR node ID diff | **0** (착수 59 → 종료 59, 3801 passed) |
| 프로덕션 코드 diff (`backend/functions`·`backend/shared`·`app/src`) | **0** |
| 신규 의존성 | 0 (npm/pip install 0) |

---

## 재보지 않은 것 — "안 재봤다"

| 항목 | 상태 | 이유 |
|---|---|---|
| PNG 픽셀 내용 | **안 봤다** | 프레임 배열이 합성이다. sha256 은 "선택이 갈렸다"의 방증일 뿐 |
| 실기기 렌더 | **안 봤다** | 시뮬레이터·기기 미기동 |
| 음성 큐 발화 | **안 들었다** | 재생 화면 문제, 범위 밖 (F-6 은 이미 아는 미해결) |
| mode3 경로 | **안 돌렸다** | fixture 4건 전부 mode1 |
| Pod 재분석 후 실제 doc 값 | **안 돌렸다** | Pod 미기동. 이 하네스는 **저장된 07-31 시점 doc** 을 재생한 것이지 새 분석이 아니다 |
| `split_angle` fail-closed | **확인 안 됨** | 그 record 자체가 재현되지 않아 관측 범위 밖 (Deviation 2) |
| `leg_extension` 순간의 정확성 | **확인 안 됨** | 그 record 가 RECON 미일치 |
| power-spin / kip-up / pdshape 의 "갈림" | **물을 수 없었다** | 재현 record 가 1건씩 |

---

## 다음 사이클로 (B 단계 + 부산물)

**B 단계 = 사진이 실제로 다른 순간인지.** S3 영상 → ffmpeg 프레임 추출 → 실제 PNG 렌더 →
육안·바이트 확인. 이 사이클은 **프레임 인덱스**까지만 답했다.

**§1. `hold_window` 를 fixture 에 넣으면 power-spin 도 판정 대상이 된다 (진단 완료).**
production 의 `_hold_window_from_moments` 는 hold moment 1개일 때 `±2초` 창을 만든다.
power-spin 에서 `leg_extension` 79.34 를 내는 창은 **(1, 37) 단 하나**로 유일하고
(전 구간 스캔, 오차 0.01 이내 1개), 길이 36 = 9fps × 4초 = 그 규칙의 산출 형상이며,
그 중심 19 는 저장된 `windowMedianAngleDeltas.sourceFrameIndices.user = [17..21]` 의
중앙과 정확히 일치한다. 저장 doc 의 `dimensionExplanation.line.deficitSummary` 가
"오른쪽 무릎 신전 부족"인 것도 이 창에서만 성립한다(자동 창에서는 왼쪽 무릎이 최대).
**→ `gemini_cache/{video_hash}` 를 fixture 에 추가하면 재현된다.** 단 `video_hash` 는
영상 파일 sha256 이라 S3 영상이 필요하다 = B 단계와 같은 전제.
**이번 사이클에서는 이 창을 쓰지 않았다** — 진단일 뿐 입력이 아니다.

**§2. `split_angle` 재현에는 `supported_differences` 박제가 필요하다.** 현재 doc 은
fold 된 `rootCauseHypotheses` 만 남긴다. 파이프라인이 `supportedDifferences` 를
audit 에 남기면(계약 확장) 이 하네스가 vision record 까지 재현할 수 있다.

**§3. pdshape 에서 confirmed 카드가 새로 생긴다 — belle 확인 대상.** 저장 doc 은
advisory 1장뿐인데, `atFrameIdx` 앵커가 붙으면 `angle_vs_reference__right_knee`
confirmed 카드가 추가된다(D-12 카드 불변식이 앵커 프레임에서 통과). 카드 장수가 1 → 2 로
늘어나는 표시 변화다. 채점 무관.

---

## Known Stubs

없음. 이 사이클은 검증 하네스만 만들었고 프로덕션 코드 diff 0 이다. 하네스 안의
"죽는 스텁"은 placeholder 가 아니라 **의도된 차단 장치**다(호출되면 죽는 것이 사양).

---

## Threat Flags

없음. 신규 네트워크 엔드포인트·인증 경로 0. T-czw-01(AWS key ID 노출)은 값 기준 재귀
strip + 커밋 전 grep 게이트로 해소했다(`AKIA` 0건). T-czw-04(uid·fileName)는 플랜대로
accept — belle 자신의 테스트 계정 가명 식별자이고 인물 이미지 0 이다.

---

## 실행 환경 메모

워크트리에 `backend/.venv` 와 `app/node_modules` 가 없어 메인 체크아웃의 것을 **심볼릭
링크**해 게이트를 돌렸다. 패키지 설치 0, 메인 체크아웃 수정 0. 종료 시 두 링크 모두 제거.
pytest 가 재생성한 추적 `.pyc` 2개는 원복했다.

네트워크 사용은 **Task 1 의 Firestore 읽기 1회**뿐이다(플랜이 명시한 예외). S3·Gemini·
RunPod 접속 0.

---

## Commits

| hash | 내용 |
|---|---|
| `e85299ed` | Task 1 — 실 doc 8건 fixture 박제 + MANIFEST 정답지 |
| `18bc9145` | Task 2 — 재생 + RECON 게이트 (**판정 구현 전**, `build_verdict` = NotImplementedError) |
| `2935771a` | Task 3 — `atFrameIdx` 실물 판정 + 카드 프레임 |
| `9878f43d` | Task 3 후속 — `atMatched` 분모 2종 + `failClosed` 공란의 의미 명시 |

**커밋 순서가 증거다** (T-czw-03): `18bc9145` 시점의 `replay.py` 는 판정 코드를 담고 있지
않다(`build_verdict` 가 `NotImplementedError` — `git show 18bc9145:…/replay.py` 561행에서
직접 확인). 판정 숫자를 본 뒤 게이트를 무르게 고친 경로가 이 순서로 반증된다.
RECON 게이트의 비교 규칙(`|Δ| ≤ 1e-6`, criterion 집합, points, final)은 `18bc9145` 이후
한 글자도 바뀌지 않았다 — `recon()` 함수 본문을 두 시점에서 추출해 문자열 비교했고
`RECON-FN-UNCHANGED` 였다.

---

## Self-Check: PASSED

- 신규 파일 13종 전부 `ls` 로 존재 확인(스크립트 1 · 러너 1 · fixture 9 · 산출물 1 · SUMMARY 1).
- 커밋 4개 전부 `git cat-file -t` 로 `commit` 확인 + `git log` 에 존재.
- 판정 수치는 `replay_out.json` 을 직접 열어 읽은 값이다(요약문 인용 아님).
- 차단 실증 13종은 실제로 호출해 RuntimeError 를 받은 출력이다.
- pytest node ID diff·프로덕션 diff·결정성은 각각 커맨드를 돌려 받은 출력이다.
