---
phase: 38-supplier-link
plan: 05
subsystem: ml-analysis
tags: [registration, hold_height, rtmw_engine, pytest, tdd, pure-functions, supplier-link]

# Dependency graph
requires:
  - phase: 38-supplier-link (38-01)
    provides: models.REG_ERR_LOW_CONFIDENCE / REG_ERR_MULTIPLE_PEOPLE / REG_ERR_NO_STANDING_START (reason 문자열 정본)
  - phase: quick-260925-nnt / quick-260924-vj1
    provides: hold_height 바닥 규칙(창 낮은발 10% 분위 < −FLOOR_VIOLATION_BODY_LENGTH) · _arrays · _frame_series · MIN_CONF/MIN_STAND_FRAMES
  - phase: 32-15 / quick-260913-udr
    provides: rtmw_engine _infer_raw · _build_pose_frames · 2-pass 디스패처(rot180 / PR 워프)
provides:
  - "registration_checks.py: check_registration(person_counts, report, *, n_stand) -> RegistrationVerdict(ok, reason, joints, detail) · 순서 low_confidence → multiple_people → no_standing_start → ok"
  - "registration_checks: multiple_people_ratio · is_multiple_people(>= 0.30 경계, 순서 무관) · low_confidence_joints · standing_start_measurable · standing_start_ok · joint_labels_ko · KEYPOINT_LABEL_KO(12) · default_stand_frames(fps) · DETAIL_* 토큰 3개"
  - "registration_checks._require_mapping: report 비Mapping → TypeError(fail-loud, 차단 1); 형상 불량 dict → fail-closed(no_standing_start/no_floor_reference)"
  - "hold_height.floor_reference_valid(report, window) -> bool | None (공개) + _floor_reference_ok(low_foot) 통계 한 벌 — hold_window_heights 결과 byte-동일"
  - "rtmw_engine.RTMWPoseEngine.estimate_with_person_counts(frames, pole_axis) -> (list[PoseFrame], list[int]) — estimate() 와 같은 _estimate_impl, 사이드카 0"
affects: [38-07 pipeline _register_reference(check_registration · estimate_with_person_counts · default_stand_frames · joint_labels_ko), 38-14 Pod 실물 실패 관측(문턱 3개 조정 근거), 38-03 supplierRules.failCopy({joints} 항상 비어 있지 않음)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "판정 순서 = 측정 불가(저신뢰) 먼저, 측정 결과 위반(서 있는 시작) 나중 — 재료 신뢰도 미달이 다른 실패로 위장되지 않게(리뷰 R6)"
    - "입력 계약 fail-loud: 공유 파서(hold_height._arrays)가 조용히 None 을 내는 자리 **앞에서** TypeError — 배선 실수는 테스트에서 드러나고, 형상 불량은 그대로 fail-closed"
    - "엔진 API 확장 = 공통 본문(_estimate_impl / _infer_raw_with_counts) + 기존 공개 함수는 한 줄 위임 — 회귀 0 을 구조로 보장, 반환값(local-return tuple)로만 새 정보"
    - "통계·문턱은 소유 모듈(hold_height) 한 벌, 소비처는 import 만 — 상수 복제 0 (grep 게이트)"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/registration_checks.py
    - backend/tests/test_registration_checks.py
  modified:
    - backend/shared/python/sunity_shared/analysis/hold_height.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py
    - backend/tests/test_rtmw_engine.py

key-decisions:
  - "38-05: no_standing_start detail 토큰은 셋 — stand_window_too_short · floor_violation + no_floor_reference(바닥·몸길이를 못 세움: 형상 불량 dict · 몸길이 ≤ 0 · 창이 T 에 비해 짧음). 못 잰 것을 floor_violation 이라 부르지 않는다"
  - "38-05: low_confidence 는 항상 joints ≥ 1 (구조 + 7형상×2목록 테스트) — 38-03 failCopy 의 '잘 안 보인 부위: .' 경로는 이 계약으로 닫힌다. 형상 불량 dict 는 low_confidence 가 아니라 no_standing_start/no_floor_reference"
  - "38-05: hold_window_heights 는 공개 floor_reference_valid 가 아니라 같은 통계 함수 _floor_reference_ok(이미 계산한 series) 를 부른다 — report 를 두 번 파싱하지 않고 통계는 한 벌. 출력 byte-동일(합성 10쌍 JSON 대조)"
  - "38-05: standing_start_measurable 은 바닥 재료 4관절을 **관절별**로 본다(한쪽 발목만 안 읽혀도 그 발목이 오른다) — hold_height 가 다른 쪽 발목으로 바닥을 세울 수 있어도 기준 영상 등록에는 더 엄격한 쪽을 택했다"
  - "38-05: default_stand_frames(fps) = round(fps × STANDING_START_DEFAULT_SEC), fps 를 못 믿으면 0 → stand_window_too_short — 38-07 이 같은 식을 다시 쓰지 않게 상수에 소비처를 붙였다"
  - "38-05: 사람 수는 1차 추론의 N 만 센다 — rot180/PR 2차 추론은 같은 사람을 다시 검출한 것이라 세지 않는다"

patterns-established:
  - "registration_checks 헤더 어법 = hold_height 어법 + 판정 순서와 이유 + PROXY 한계 + 입력 계약 절 (뒤 판정 모듈이 따를 골격)"
  - "합성 강제 테스트: test_hold_height._report/_pose 를 복제해 같은 형상으로 실패형을 만든다 — Pod 0"

requirements-completed: [REQ-38-4]

# Metrics
duration: 10min
completed: 2026-09-28
---

# Phase 38 Plan 05: 등록 실패 판정(순수) + 엔진 사람 수 API Summary

**등록 실패 4형 중 셋(저신뢰 · 여러 명 · 서 있는 시작 없음)이 `registration_checks.check_registration` 순수 함수 하나로 — 측정 불가를 먼저 잡는 순서(리뷰 R6), 비율 경계 2/10·3/10·4/10 순서 무관(R15b), 비Mapping 은 TypeError·형상 불량은 fail-closed(차단 1) — 합성 입력 pytest 50건으로 강제되고, 넷째(사람 미검출)의 재료인 프레임별 사람 수는 `RTMWPoseEngine.estimate_with_person_counts` 가 `estimate()` 와 같은 경로에서 반환값으로 낸다(좌표 동일, 사이드카 0). Pod · Firestore · S3 호출 0.**

## Performance

- **Duration:** 10min (실행 시작 → 마지막 검증 실행)
- **Started:** 2026-09-28T14:44:06Z
- **Completed:** 2026-09-28T14:54:05Z (마지막 검증 실행 시각, 관측)
- **Tasks:** 2/2 (TDD — test → feat 커밋 각 2)
- **Files modified:** 5 (+887 / −21, `git diff --stat ca739390..HEAD` [확인])

## Accomplishments

- `registration_checks.py`(신규, 266줄): `check_registration` ① `low_confidence`(관절 중앙값 < 0.5 **또는** 서 있는 창의 바닥 재료(발목·어깨) < `hold_height.MIN_CONF`) → joints = 두 목록 합집합(report 순서, 항상 ≥ 1) ② `multiple_people`(N≥2 프레임 비율 ≥ 0.30, 경계 포함, 순서 무관) ③ `no_standing_start`(detail `stand_window_too_short` / `no_floor_reference` / `floor_violation`) ④ ok. reason 은 `models.REG_ERR_*` 그대로. `no_human` 은 판정하지 않고 엔진 예외를 38-07 이 매핑한다(docstring).
- `hold_height.floor_reference_valid(report, window) -> bool | None` 공개 — quick-260925-nnt 바닥 규칙의 통계·문턱을 `_floor_reference_ok` 한 벌로 옮기고 `hold_window_heights` 가 그것을 부른다. `_arrays` 무접촉, 상수 이동 0. 리팩터 전후 `hold_window_heights` 출력 byte-동일(합성 10쌍 JSON 대조) + `test_hold_height` 56건 통과.
- `rtmw_engine`: `_infer_raw_with_counts`(kps_batch[0] 가 버리던 N 을 counts 로) · `_estimate_impl(with_counts)` 공통 본문 · `estimate_with_person_counts`. `estimate()` 는 시그니처·예외·2-pass 순서 무변경(한 줄 위임). N=1 에서 두 API 의 PoseFrame 이 프레임마다 dataclass 동등(keypoints_2d · confidence 포함).
- 문턱 3개 상수 `MULTI_PERSON_FRAME_RATIO = 0.30` · `STANDING_START_DEFAULT_SEC = 1.0` · `LOW_CONFIDENCE_MEDIAN_MIN = 0.5` — 전부 **[ASSUMED RESEARCH A6/A5/A7]**, 주석에 "시험 영상 2차로만 조정, 목표 숫자 금지" + conf-05-gate 메모리 인용. 테스트는 값이 아니라 관계만 잠근다(`LOW_CONFIDENCE_MEDIAN_MIN >= hold_height.MIN_CONF` — 이보다 낮추면 "측정 불가를 먼저" 순서가 무너진다).

## Task Commits

1. **Task 1: hold_height.floor_reference_valid 공개 + registration_checks.py + 합성 강제 테스트** — `bc171b61` (test, RED: ImportError 확인) → `2afca8db` (feat, GREEN 106 passed)
2. **Task 2: RTMWPoseEngine.estimate_with_person_counts (사이드카 0, estimate() 같은 경로)** — `84d89eda` (test, RED: 5 failed AttributeError / 10 passed) → `c12e754c` (feat, GREEN 24 passed)

**Plan metadata:** 아래 docs 커밋(SUMMARY · STATE · ROADMAP · REQUIREMENTS).

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/registration_checks.py` (신규) — 헤더(왜/어떻게/판정 순서와 이유/PROXY 한계/입력 계약/fail-closed/채점 무접촉) · 문턱 3 상수 · `_FLOOR_JOINTS` · `KEYPOINT_LABEL_KO`(skeleton 8개 값 참조 + 손목·발목 4) · `DETAIL_*` 3 · `RegistrationVerdict` · `_require_mapping` · `default_stand_frames` · `multiple_people_ratio` · `is_multiple_people` · `low_confidence_joints` · `standing_start_measurable` · `_standing_start_detail` · `standing_start_ok` · `joint_labels_ko` · `check_registration`. import = stdlib · hold_height · keypoint_frame · skeleton · models (numpy 는 hold_height 경유).
- `backend/tests/test_registration_checks.py` (신규, 50 tests) — (1) 비율 경계·shuffle (2) 저신뢰 목록·라벨 12 (3) 측정 가능성/위반 분리 (4) 순서 4 + 결정적 케이스 3 (5) `test_non_mapping_report_raises_type_error`(실제 `KeypointReport` 인스턴스 + None → TypeError, 메시지에 Mapping·_dataclass_to_camel_case_dict) · 형상 불량 dict fail-closed · low_confidence joints ≥ 1 (7형상×2목록) (6) 문턱 관계 · `default_stand_frames` (7) `floor_reference_valid` True/False/None + `hold_window_heights` 같은 판정 · `test_floor_rule_is_a_proxy_crouch_passes`.
- `backend/shared/python/sunity_shared/analysis/hold_height.py` — `_floor_reference_ok(low_foot)` · `floor_reference_valid(report, window)` 신설(PROXY 명시), `hold_window_heights` 의 바닥 판정 블록을 `_floor_reference_ok` 호출로. 나머지 무접촉.
- `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py` — `estimate()` 본문 → `_estimate_impl(with_counts=False)`, `estimate_with_person_counts` 신설, `_infer_raw` → `_infer_raw_with_counts(...)[0]`. 모듈 전역·인스턴스 카운트 저장 0.
- `backend/tests/test_rtmw_engine.py` — 신규 5: N=2 → [2]*5 · N=0 → NoHumanError · None/1/1 → [0,1,1] · N=1 좌표 동등 · T==0 → ([], []).

## 관측 (이 세션이 직접 실행/읽은 것)

- [확인] `cd backend && .venv/bin/python -m pytest tests/test_registration_checks.py tests/test_hold_height.py tests/test_rtmw_engine.py tests/test_rtmw_engine_rot180.py -q` → `130 passed` (50 + 56 + 15 + 9). 인터프리터 = `backend/.venv` Python 3.14.6.
- [확인] 착수 전 기준선 `tests/test_hold_height.py tests/test_rtmw_engine.py tests/test_rtmw_engine_rot180.py` → `75 passed` (test_rtmw_engine 이 rtmlib 없이 `create_with_inferencer` 경로로 로컬에서 돈다).
- [확인] RED: Task 1 = 수집 단계 `ImportError: cannot import name 'registration_checks'`; Task 2 = `5 failed, 10 passed`(전부 `AttributeError: ... no attribute 'estimate_with_person_counts'`).
- [확인] hold_height 리팩터 전후 대조: 합성 10쌍(정상 · 바닥 위반 · 한 프레임 튐 · 잡음 폭 안 · 창 짧음 · 창 이전 부족 · 무작위 잡음 3 · 부분 NaN)의 `hold_window_heights` JSON 이 `cmp` byte-동일. None 3건(violation · short_window · no_stand) 도 동일.
- [확인] 게이트: `def floor_reference_valid` = 1 · `FLOOR_VIOLATION_BODY_LENGTH =` in registration_checks = 0 · `PROXY` hold_height 1 / registration_checks 2 · `def standing_start_measurable` = 1 · `import boto3\|firebase\|firestore` = 0(대소문자 무시도 0) · `def _require_mapping` = 1 · `_require_mapping(report)` = 5 · `check_registration` 안 return 순서 low_confidence :257 < multiple_people :261 < no_standing_start :265 · `git diff -U0 hold_height.py | grep -c _arrays` = 0 · `len(KEYPOINT_LABEL_KO) == 12`, 키 순서 == `_KEYPOINT_NAMES` · 엔진 3 def = 3 · `self._person_counts\|self.person_counts` = 0 · `def estimate(` diff 줄 0 · 모듈 상단 rtmlib import 0.
- [확인] 이웃 회귀: hold_height/rtmw_engine/pose_engines/registration_checks 를 import 하는 테스트 파일 14개 → `262 passed, 1 warning`(경고는 의존 패키지의 Python 3.14 typing 관련, 이 플랜 무관).
- [확인] `3/10 >= 0.30` 은 Python float 에서 True(`3/10 == 0.3` True) — 경계 케이스가 부동소수로 갈리지 않는다.
- [확인] 38-03 `app/src/lib/supplierRules.ts:218-229` `failCopy(code, joints)` 는 `joints.join(' · ')` 로 `{joints}` 를 치환하고 빈 목록이면 `''` — "잘 안 보인 부위: ." 이 나올 수 있는 자리(38-03 SUMMARY :122 가 [미확인]으로 남긴 것).
- [확인] 38-07-PLAN :173-175 는 `estimate_with_person_counts(frames, pole)` → `(pose_frames, counts)` · `check_registration(counts, report, n_stand=n_stand)` · `n_stand = int(round(... * real_fps))` · joints 를 라벨로 바꿔 `{joints}` 치환 — 이 플랜의 시그니처와 일치.
- [확인] 커밋 4건 `bc171b61` · `2afca8db` · `84d89eda` · `c12e754c`, 삭제 파일 0, 미추적 파일 0(`.planning/TRAINING-DUE.md` 의 기존 미커밋 변경은 손대지 않음).

## 진단 (관측에서 내가 붙인 해석 — 다음 세션 재검증 대상)

- "REQ-38-4 완료" 는 **순수 판정 층의 완료**다 — 런타임에서 실패 4형이 실제 doc 에 남는 것은 38-07(파이프라인 배선) + 38-14(Pod 실물) 뒤에만 참이다 [미확인 — 실행되지 않음].
- 문턱 3개가 실영상에서 어디에 놓이는지(지나가는 사람 · 조명 · 옷) 는 [미확인] — 상수는 잠정이고 시험 영상 2차(38-14 실물 실패 관측)로만 움직인다.
- `person_counts` 길이와 `report["frames"]` 의 일치는 검사하지 않는다 — 둘 다 같은 `pose_frames` 에서 나오므로 같다고 본다 [미확인 — 38-07 배선에서 temporal 보간이 프레임 수를 바꾸지 않는지 그쪽 테스트가 보인다].

## 한계 (리뷰 R6 — 필수 절)

**바닥 일관성 규칙은 서 있음의 PROXY 다.** 규칙이 보는 것은 "창 이전 프레임의 어깨~발목 세로 길이가 양수" + "창 안 낮은발 10% 분위가 그 바닥보다 −0.10 몸길이 아래로 안 내려감" 둘뿐이라, 웅크린 채 시작해 웅크린 채 있는 합성 좌표(어깨 0.62 · 엉덩이 0.70 · 발목 0.80, 세로 몸길이 0.18)도 통과한다 — [확인 `test_floor_rule_is_a_proxy_crouch_passes`: `standing_start_ok` True · `check_registration(...).ok` True]. 이 테스트는 반례 박제라 깨지면 규칙이 바뀐 것이다. 실영상 오분류율은 [미확인]. 자세 분류기 추가는 이 phase 범위 밖 — 가이드 ④ 문구("서 있는 자세인지는 사람이 확인해 주세요", D-16)와 시험 영상 2차 실측이 이 한계를 받는다(T-38-05-4 accept).

같은 규칙의 반대쪽 한계: 몸길이 ≤ 0(시작부터 거꾸로 매달림)은 `_frame_series` 가 None 을 내므로 `no_standing_start/no_floor_reference` 로 잡힌다 — 이것은 진짜 "서 있는 시작 없음" 이지만 detail 은 위반이 아니라 "못 세움" 이다(reason 은 맞다).

## Decisions Made

- **detail 토큰 셋째 `no_floor_reference`** — 플랜은 둘(`stand_window_too_short` · `floor_violation`)만 적었지만 `floor_reference_valid` 가 None 을 내는 경우(형상 불량 dict · 몸길이 ≤ 0 · 창이 T 에 비해 짧음 · 재료 NaN)를 `floor_violation` 이라 부르면 관측을 거짓으로 적는 것이다. reason 은 플랜 그대로 `no_standing_start`(fail-closed), detail 만 셋. 38-07 은 reason 만 문구에 쓴다.
- **`hold_window_heights` 는 `_floor_reference_ok(series)` 호출** — 플랜 문장은 "블록을 이 함수(floor_reference_valid) 호출로" 였으나 그러면 이미 계산한 `_series` 를 다시 파싱한다. 통계·문턱은 `_floor_reference_ok` 한 곳에만 있고 공개 함수는 그것을 감싼다 — 플랜의 목적(복제 0 · 같은 통계) 을 더 좁게 만족. 출력 byte-동일 확인.
- **`low_confidence` 는 항상 joints ≥ 1** — reason 이 나오는 조건이 곧 "이름 있는 관절이 있다" 이고, 형상 불량 dict 는 저신뢰가 아니라 `no_standing_start` 로 보낸다. 38-03 의 `failCopy` 빈 목록 경로가 계약으로 닫힌다.
- **`standing_start_measurable` 관절별 판정** — 한쪽 발목만 서 있는 창에서 MIN_CONF 미만이어도 그 발목을 저신뢰로 올린다. hold_height 는 다른 쪽 발목으로 바닥을 세울 수 있지만 기준 영상 등록은 "안 읽힌 부위를 사람에게 말해 주는" 쪽이 맞다고 봤다(플랜은 양쪽 발목 케이스만 정의).
- **`low_confidence_joints` 는 NaN 중앙값도 저신뢰** — 플랜의 `np.nanmedian < min_conf` 그대로면 전부 NaN 인 관절이 통과한다(NaN < x 는 False). `hold_height._nanmedian` 을 써서 비유한이면 목록에 올린다(fail-closed).
- **`default_stand_frames(fps)` 추가**(플랜 목록 밖, 4줄) — `STANDING_START_DEFAULT_SEC` 의 소비처를 이 모듈에 두어 38-07 이 같은 식을 다시 쓰지 않게. fps 를 못 믿으면 0 → `stand_window_too_short`.
- **`detail` 에 관측을 남긴다** — `low_confidence` 는 어느 갈래(중앙값 / 서 있는 창 재료)가 잡았는지, `multiple_people` 은 `person_ratio=0.300` 처럼 잰 값. 문구에는 쓰지 않는다(RegistrationVerdict docstring).
- **사람 수는 1차 추론만** — rot180/PR 2차 추론의 N 은 같은 사람의 재검출이라 세지 않는다. `_maybe_second_pass_*` 는 그대로 `_infer_raw` 를 부른다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] `no_standing_start` 의 "못 잼" 을 위반과 구분하는 detail 토큰**
- **Found during:** Task 1 (check_registration 설계)
- **Issue:** 플랜의 두 토큰만으로는 형상 불량 dict · 몸길이 ≤ 0 · 창 부족(전부 `floor_reference_valid` None)을 `floor_violation` 이라 적게 된다 — 로그가 잰 적 없는 위반을 주장한다.
- **Fix:** `DETAIL_NO_FLOOR_REFERENCE = "no_floor_reference"` 추가, `_standing_start_detail` 이 None → 이 토큰, False → `floor_violation`. reason 은 플랜 그대로.
- **Files modified:** `registration_checks.py`, `test_registration_checks.py`
- **Verification:** `test_malformed_dict_is_fail_closed_without_raising` (`detail == "no_floor_reference"`), `test_check_registration_floor_violation_is_no_standing_start` (`detail == "floor_violation"`).
- **Committed in:** `2afca8db`

**2. [Rule 2 - Missing validation] 신뢰도 중앙값이 NaN 인 관절을 저신뢰로**
- **Found during:** Task 1 (low_confidence_joints)
- **Issue:** `np.nanmedian(...) < min_conf` 는 전부 NaN 인 열에서 False — 읽은 값이 하나도 없는 관절이 "괜찮다" 로 통과한다.
- **Fix:** `hold_height._nanmedian` + `not (isfinite and >= min_conf)`.
- **Files modified:** `registration_checks.py`
- **Verification:** 로직 검토 + 전부 0.1 케이스(`test_check_registration_all_unreadable_is_low_confidence_with_all_joints`). 전부 NaN 인 report 전용 테스트는 없다(`_arrays` 가 `dtype=float` 로 NaN 을 받으므로 경로는 살아 있다).
- **Committed in:** `2afca8db`

**3. [Rule 3 - Blocking gate] 엔진 docstring 의 `self._person_counts` 문구가 사이드카 grep 게이트에 걸림**
- **Found during:** Task 2 acceptance
- **Issue:** "사이드카(self._person_counts 등) 금지" 라는 설명문이 `grep -c "self._person_counts" == 0` 게이트를 1 로 만들었다(38-01 의 boto3 docstring 과 같은 종류).
- **Fix:** 속성 이름 없이 "사람 수를 인스턴스 속성이나 모듈 전역에 저장" 으로 바꿈. 로직 무접촉.
- **Files modified:** `rtmw_engine.py`
- **Verification:** grep 0, `24 passed`.
- **Committed in:** `c12e754c`

---

**Total deviations:** 3 auto-fixed (Rule 2 ×2, Rule 3 ×1)
**Impact on plan:** 전부 판정의 정직성(관측을 위반으로 적지 않기) · fail-closed 보강 · 게이트 문구. 뒤 플랜이 쓰는 이름(`check_registration` · `RegistrationVerdict` · `estimate_with_person_counts` · `floor_reference_valid` · `STANDING_START_DEFAULT_SEC`)은 플랜 그대로. 범위 확장은 `default_stand_frames` 4줄뿐.

## Issues Encountered

- 이웃 회귀 sweep 첫 실행이 `no tests ran` — zsh 가 unquoted `$FILES` 를 단어 분리하지 않아 pytest 가 경로 하나로 받았다. `xargs -0` 로 재실행해 262 passed 를 얻었다(첫 결과는 폐기).

## Known Stubs

None. 문턱 3개는 stub 이 아니라 [ASSUMED] 상수(주석·본 SUMMARY 명시). `RegistrationVerdict.detail` 은 로그용이며 UI 에 닿지 않는다.

## Threat Flags

None — 새 네트워크 endpoint · 인증 경로 · 파일 접근 · 스키마 변경 0. `_require_mapping` 은 T-38-05-1(형상 불량으로 통과 못 함) 의 앞단 보강이고, T-38-05-4(PROXY 오분류) 는 위 "한계" 절에 그대로 accept.

## User Setup Required

None — 순수 함수 · 엔진 어댑터 · 테스트만. Pod · 배포 · SSM · Firestore · S3 쓰기 0.

## 다음 플랜 주의 (38-07 · 38-14 · 38-03)

- **`low_confidence` 의 `joints` 는 절대 비지 않는다** [확인 — 구조 + `test_low_confidence_verdict_always_names_at_least_one_joint` 7형상×2목록]. 38-03 `failCopy(code, [])` 의 "잘 안 보인 부위: ." 경로는 이 플랜 계약으로는 발생하지 않는다. 단 38-07 이 `registrationError.joints` 에 넣는 값은 **`joint_labels_ko(verdict.joints)`** 여야 한다(verdict 의 joints 는 영문 키 튜플) — 38-07-PLAN :142 의 기대값 `['왼쪽 발목','오른쪽 발목']` 이 그것이다.
- 형상 불량 report dict(파이프라인 버그)는 `no_standing_start/no_floor_reference` 로 나간다 — 공급자 문구로는 "서 있는 자세로 시작하지 않았어요" 가 보인다. 38-07 은 `verdict.detail == "no_floor_reference"` 를 warning 로그로 남겨 두면 실물 관측(38-14)에서 버그와 진짜 실패를 가를 수 있다 [권장, 계약 변경 아님].
- `n_stand` 는 38-07 이 `default_stand_frames(real_fps)` 또는 `int(round(execStartS × real_fps))` 로 넘긴다. 0 이나 `MIN_STAND_FRAMES`(3) 미만이면 `stand_window_too_short` — 9fps 기준 1.0초 = 9프레임.
- `person_counts` 는 `estimate_with_person_counts` 의 1차 추론 N 목록(길이 = 엔진에 넣은 프레임 수). `check_registration` 은 report frames 와 길이를 대조하지 않는다.
- 문턱 3개(0.30 · 1.0초 · 0.5)는 [ASSUMED] — 38-14 에서 실물 실패가 나오면 코드·문구만 기록하고 숫자를 그 영상에 맞추지 말 것(플랜 머리말 · 메모리 chasing-the-number).
- PROXY 한계(위 절): 웅크린 시작은 통과한다. 가이드 ④ 문구는 38-03 `docs/supplier-guide.md` 몫 — 이 플랜은 문구를 건드리지 않았다.

## Next Phase Readiness

- 38-07 은 `registration_checks.check_registration` · `RegistrationVerdict` · `joint_labels_ko` · `default_stand_frames` · `STANDING_START_DEFAULT_SEC` 와 엔진 `estimate_with_person_counts` 를 그대로 쓴다. 판정 순서는 이 모듈 소유(38-07 은 `no_human` 만 앞에 둔다).
- 채점 경로(`dimensions` · `assemble.build_mode1` · `_process`) 무접촉 — `git diff` 에 그 파일 0.
- 남은 것: 정은지 새 영상이 오면 이 phase 보다 시험 영상 2차가 먼저(플랜 머리말 1).

## Self-Check: PASSED

- 파일 6개 존재 · 커밋 4건(`bc171b61` · `2afca8db` · `84d89eda` · `c12e754c`) `git log --all` 에 존재 [확인]
