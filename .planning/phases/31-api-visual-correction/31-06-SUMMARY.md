---
phase: 31-api-visual-correction
plan: 06
subsystem: ml
tags: [pose-gate, fail-closed, decompression-bomb, runpod, geometry, provenance]

# Dependency graph
requires:
  - phase: 31-api-visual-correction
    provides: "joint_inner_angle_deg / ARROW_JOINT_MAP 각도 산출 단일 출처 (31-03)"
  - phase: 31-api-visual-correction
    provides: "VISUAL_FAILURE_REASONS typed 실패 사유 (31-02)"
provides:
  - "POST /pose-image — 단일 이미지 COCO-17 keypoint 추정 (Pod 기존 estimator 재사용, 채점 무접촉)"
  - "measure_generated_pose — 생성물 목표 관절각 재측정 + 허용오차 판정 (fail-closed)"
  - "_normalize_for_pose — 전송 전 decode-cap 정규화 (31-05 safe_decode_image 동일 계약)"
  - "derive_pose_url — RUNPOD_ANALYZE_URL 파생 /pose-image URL (env 이원화 방지)"
  - "PoseGateResult — typed 판정 결과 (passed/measured_deg/error_deg/reason/preserved_violation)"
affects: [31-09, 31-12, 31-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "fail-closed 2분류: 전송·서버 계층 실패=pose_gate_unavailable(재시도), 측정 불신뢰=pose_gate_failed(종결)"
    - "좌표계 복원 계약: 정규화 keypoint 는 서버 보고 width/height 로 등방 px 복원 후에만 각도 산출"
    - "decode-cap 이중 검사: MAX_IMAGE_PIXELS + 명시 w*h 검사 병행 (PIL 은 MAX~2*MAX 구간을 경고만 냄)"
    - "상한 lockstep 테스트: 측정측 상수와 server.py 상수를 소스에서 파싱해 대조"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/pose_gate.py
  modified:
    - backend/runpod_inference/server.py
    - backend/tests/phase31/test_pose_gate.py

key-decisions:
  - "/pose-image 응답에 width/height 동봉 — 정규화 좌표만으로는 종횡비를 알 수 없어 각도가 왜곡된다 (31-03 ref_frame_shape 필수화와 동일 규칙)"
  - "원본 바이트 상한 = 워커 허용치 20MB, endpoint 8MB 는 재인코딩 후 만족. 원본에 8MB 를 걸면 정규화의 존재 이유가 사라진다"
  - "인체 미검출·추정 실패는 5xx 가 아니라 ok:false — 재시도 대상(unavailable)과 종결(no_person)을 호출측이 구분해야 한다"
  - "각도 재구현 금지 검사를 문자열이 아닌 AST 호출 검사로 — 문자열이면 docstring 을 검열하고 정작 변수명 바꾼 재구현은 놓친다"
  - "preserved_targets 는 optional keyword — 플랜 시그니처를 깨지 않으면서 전체 포즈 재생성 실패 모드를 닫는다"

requirements-completed: [D-03, D-05]

# Metrics
duration: 38min
completed: 2026-07-20
---

# Phase 31 Plan 06: 결정론 pose 게이트 Summary

**생성된 교정 이미지의 목표 관절각을 Pod 기존 estimator 로 재측정해 허용오차와 대조하는 결정론 백스톱 — 각도 공식·관절 트리플·payload 상한을 전부 단일 출처에서 가져와 "게이트가 자기 기준으로 자신을 통과시키는" 경로를 제거**

## Performance

- **Duration:** 38 min
- **Tasks:** 2 / 2
- **Files modified:** 3 (1 created, 2 modified)
- **Tests:** 35 신규 (phase31 전체 139 green)

## Accomplishments

- **리뷰 H-03 해소** — 생성형 judge 단독 판정을 결정론 재측정이 뒤에서 받친다. `measure_generated_pose` 가 목표 관절 3점을 실제 pose 추정으로 다시 재고 `|measured − target|` 을 호출측 주입 허용오차와 대조한다.
- **B2-01 provenance 고정** — `joint_inner_angle_deg` / `ARROW_JOINT_MAP` 을 `fault_zoom` 에서 import. 검사를 문자열이 아닌 **AST 호출 검사**로 해서 `acos`/`arccos`/`atan2` 자체 호출 0 + `joint_inner_angle_deg` 실호출을 동시에 고정했다.
- **종횡비 왜곡 봉쇄** — `/pose-image` 가 width/height 를 응답에 싣고 게이트가 등방 px 로 복원한 뒤에만 각도를 낸다. 회귀 테스트는 같은 3점이 px 에서 110.56도, 정규화 직입력이면 126.87도가 되는 fixture 로 두 경로를 구분한다 (right angle 만으로는 축 스케일링에 불변이라 잡히지 않는다 — 비직각 fixture 를 쓴 이유).
- **H3-04 payload 계약 명시** — b64 문자열 / decoded bytes / 픽셀·변 3중 상한 + `MAX_IMAGE_PIXELS` + format allowlist. PIL 이 `pixels > 2*MAX` 에서만 예외를 던지고 `MAX~2*MAX` 는 경고만 낸다는 점 때문에 **명시적 `w*h` 검사를 병행**한다.
- **H4-06 동일 계약** — 측정측 `_normalize_for_pose` 가 31-05 `safe_decode_image` 와 같은 cap 집합을 decode 전/직후로 검사한다. bomb fixture(IHDR 만 20000x20000)는 서버 호출 0 으로 거부됨을 테스트가 고정.
- **fail-closed 2분류 고정** — 연결 실패/타임아웃/비200/파싱 불가 → `pose_gate_unavailable`, 저신뢰·결측·종횡비 미상·미매핑 관절 → `pose_gate_failed`, 사람 없음 → `no_person`. 전부 `passed=False`.
- **상한 drift 게이트** — 측정측 상수와 `server.py` 의 `_POSE_IMG_*` 를 소스에서 파싱해 대조하는 테스트. 값이 갈라지면 "보냈는데 413" 이 조용한 unavailable 로 둔갑하는데, 이 실패는 로그만 보면 Pod 장애와 구분되지 않는다.

## Task Commits

1. **Task 1: Pod POST /pose-image (명시 상한 + bomb 방어)** - `5b32e52` (feat)
2. **Task 2: pose_gate.py 정규화 + 재측정 + fail-closed 판정** - `9a6ed17` (feat)

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/pose_gate.py` (신규) — `PoseGateResult`, `measure_generated_pose`, `_normalize_for_pose`, `_post_pose_image`, `_angle_from_payload`, `derive_pose_url`, payload 상한 상수 6종, typed reason 3종
- `backend/runpod_inference/server.py` — `PoseImageRequest`/`PoseImageResponse`, `_decode_pose_image`, `POST /pose-image`, `_POSE_IMG_*` 상한 상수 5종. 기존 `/analyze`·`/health`·인증·모듈 로딩 lock 무변경
- `backend/tests/phase31/test_pose_gate.py` — 31-02 스캐폴드(30줄)를 실제 검증 35개로 교체

## Decisions Made

- **estimator 접근 경로** — `_load_pipeline_module()` → `_ensure_adapters()` → `mod._RTMW_ENGINE.estimate(frames, mod._POSE_ESTIMATOR._default_pole)`. vertical pole_axis fallback 을 새로 만들지 않고 `_RTMWNlfCompat` 의 것을 재사용해 fallback 정의가 두 곳에 생기는 것을 막았다. 2D keypoint 는 `PoseFrame.keypoints_2d`(정규화 0~1 + visibility)를 그대로 쓴다 — 채점이 쓰는 COCO-17 3D 배열 경로는 건드리지 않는다.
- **display 전용 invariant 를 주석이 아닌 구조로** — `/pose-image` 는 `dimensions`/`kismam`/`assemble`/`firestore_admin` 을 호출하지 않고 Firestore 도 만지지 않는다. `pose_gate` 쪽은 소스에 해당 이름이 등장하지 않는지 테스트가 검사한다. 생성 이미지에서 뽑은 좌표가 점수를 움직이는 경로 자체를 없앤다.
- **timeout 기본 60초** — 플랜 명시값. 동기 엔드포인트라 워커 lease(360초) 안에 여러 번 호출해도 여유가 있다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] 원본 바이트 상한을 endpoint 상한(8MB)이 아닌 워커 허용치(20MB)로 분리**

- **Found during:** Task 2
- **Issue:** 처음 구현에서 `_normalize_for_pose` 가 원본 bytes 를 `POSE_IMG_MAX_DECODED_BYTES`(8MB)로 선검사했다. 그런데 플랜이 정규화를 두는 이유가 정확히 **"워커의 20MB 허용 이미지도 endpoint 상한을 항상 만족"** 시키는 것이다. 원본에 8MB 를 걸면 정상 벤더 산출물(8~20MB)이 측정도 못 해보고 `pose_gate_failed` 로 종결된다 — 게이트가 생성물을 검증하는 게 아니라 큰 파일을 전부 떨어뜨리는 필터가 된다. D-08 상 이 실패는 조용한 미노출이라 운영에서 "왜 카드가 안 뜨지"로만 보인다.
- **Fix:** `POSE_SOURCE_MAX_BYTES = 20_000_000` 을 별도 선언해 원본 상한으로 쓰고, 8MB/12M-chars 는 **재인코딩 후** 만족해야 하는 전송 상한으로 남겼다. 두 상한의 역할 차이를 상수 주석에 박제.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/pose_gate.py`
- **Verification:** `test_oversized_source_is_normalized_under_endpoint_caps`(8MB 초과 원본 → 통과 + 전송분 상한 이하), `test_source_over_worker_allowance_rejected`(20MB 초과 → 서버 미호출 거부)
- **Committed in:** `9a6ed17`

**2. [Rule 2 - Missing Critical] `preserved_targets` 옵션 — 전체 포즈 재생성 차단**

- **Found during:** Task 2
- **Issue:** 플랜 시그니처는 목표 관절 하나만 검사한다. 그런데 wave-1 실측 스모크의 **지배적 실패 모드**가 "모델이 포즈를 통째로 다시 그리면서 목표 관절만 맞은" 산출물이었다(8개 중 2개만 목표 관절 교정 + 나머지 보존). 목표 관절만 보는 게이트는 이런 산출물을 통과시킨다 — 사용자에게는 자기 교정 이미지가 아니라 다른 자세의 사람이 노출되고, training pair 에도 그대로 적재된다.
- **Fix:** keyword-only `preserved_targets: Mapping[str, float] | None` + `preserve_tolerance_deg` 추가(기본 None = 플랜 계약 그대로). 주어지면 목표 외 관절이 허용오차 안에 남아 있는지 같은 `joint_inner_angle_deg` 로 검사하고, 벗어나면 `passed=False` + `preserved_violation` 에 위반 관절을 담는다. `preserved_targets` 를 줬는데 tolerance 가 없으면 기준 없는 검사이므로 통과시키지 않는다.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/pose_gate.py`
- **Verification:** `test_whole_pose_regeneration_fails_even_when_target_joint_correct`(목표 관절 90도 정확 + 오른 무릎 180→90 변형 → 불통과), `test_preserved_joints_within_tolerance_still_passes`(보존 시 정상 통과 — 과차단 아님), `test_preserved_targets_without_tolerance_rejected`
- **Committed in:** `9a6ed17`

**3. [Rule 1 - Bug] 각도 재구현 금지 검사를 문자열 → AST 호출 검사로**

- **Found during:** Task 2
- **Issue:** `assert "arccos" not in src` 가 모듈 docstring 의 "자체 arccos 를 재구현하면…" 이라는 **설명 문장에** 걸려 실패했다. 문자열 검사는 두 방향으로 다 틀렸다 — 주석을 검열하면서(위양성), 변수명만 바꾼 진짜 재구현은 놓친다(위음성).
- **Fix:** `ast.walk` 로 실제 `Call` 노드의 함수명만 수집해 `acos`/`arccos`/`atan2`/`arctan2` 호출 0 을 검사하고, 동시에 `joint_inner_angle_deg` 가 **실제로 호출되는지**도 확인한다(import 만 해두고 안 쓰는 위장 차단).
- **Files modified:** `backend/tests/phase31/test_pose_gate.py`
- **Verification:** `test_angle_math_is_single_source`
- **Committed in:** `9a6ed17`

---

**Total deviations:** 3 (2 missing critical, 1 bug)
**Impact on plan:** 범위 확장 없음 — 신규 패키지 0, 앱 파일 0, 채점 경로 0. 전부 플랜이 명시한 불변식(생성물이 기하 검증 없이 노출/적재되지 않는다 / fail-closed)을 실제로 성립시키기 위한 보강.

## Issues Encountered

- **직각 fixture 로는 종횡비 버그가 안 잡힌다** — 처음 비정사각 테스트를 90도로 짰는데, 축별 스케일링에서 수직은 수직으로 유지돼 정규화 직입력이든 px 복원이든 똑같이 90도가 나왔다. 비직각(110.56도) fixture 로 바꿔야 두 경로가 갈라진다(126.87도). 왜곡 회귀 테스트는 반드시 비직각으로 짜야 한다.
- **bomb fixture 메모리** — 실제 20000x20000 배열은 1.2GB 라 테스트에서 만들 수 없다. PNG 시그니처 + IHDR 청크만 손으로 조립했다. PIL 이 `open()` 시점에 IHDR 로 크기를 읽고 bomb 검사를 하므로 IDAT 없이도 방어 경로가 그대로 재현된다.

## 무회귀 검증 (pre-existing 실패 분리)

`python3 -m pytest backend/tests -q` (pre-existing collection error 2건 제외) 결과 **41 failed / 3050 passed / 20 skipped**. 실패 41건은 전부 `test_gemini_*` / `test_pipeline_gemini*_wiring` / `phase06` 계열의 **Gemini wiring 심볼 부재**로, 31-03 이 기록한 pre-existing 베이스라인(41 failed)과 건수·파일이 동일하다. `pose_gate` / `runpod_inference` / `phase31` 경로의 실패는 0.

- `backend/tests/phase31` — 139 passed (기준선 105 + 신규 34 net)
- `backend/tests/phase31/test_pose_gate.py` — 35 passed
- `backend/tests/test_runpod_server.py` + `test_runpod_startup_gemini.py` — 9 passed (엔드포인트 추가로 인한 회귀 0)

## Lambda 반입 검증

`sunity_shared.analysis.pose_gate` 를 import 한 뒤 `sys.modules` 를 검사해 `torch`/`onnxruntime`/`rtmlib`/`ultralytics`/`cv2` 가 **하나도 로드되지 않음**을 확인했다. GPU 의존은 Pod 엔드포인트 뒤에만 있고 게이트는 stdlib `urllib` + PIL + fault_zoom 뿐이다.

## Next Phase Readiness

- **31-09 (워커 배선):** `derive_pose_url(RUNPOD_ANALYZE_URL)` 로 URL 을 얻고 `measure_generated_pose(..., tolerance_deg=<env>)` 를 display/training 각각 호출하면 된다. **허용오차 하드코딩 금지** — 31-13 calibration 채택값을 env 로 주입하는 것이 계약이다. `preserved_targets` 를 쓰려면 원본 사용자 프레임에서 같은 `joint_inner_angle_deg` 로 잰 각도를 넘길 것(다른 공식으로 재면 보존 검사 자체가 이원화된다).
- **31-12 (Pod 재생성 + E2E):** `/pose-image` 는 실기동 미검증이다. Pod 재생성 후 (1) `X-RunPod-Token` 스모크, (2) 실제 생성 이미지 1장으로 keypoints 응답 형상 확인, (3) `RUNPOD_ANALYZE_URL` 갱신 시 파생 URL 이 새 proxy 호스트를 따라가는지 확인이 필요하다.
- **31-13 (calibration):** `measured_deg`/`error_deg` 가 결과에 실려 있으므로 tolerance sweep 의 입력으로 그대로 쓸 수 있다. `preserve_tolerance_deg` 도 별도 calibration 대상 후보다(현재 채택값 없음 — 호출측이 주입하지 않으면 검사 자체가 비활성).

### 미해소 (설계상 의도)

- **실기동 검증 전무** — 현재 Pod 가 없어 `/pose-image` 는 AST/계약 수준까지만 고정했다. estimator 가 생성 이미지(실사진이 아닌 합성물)에서 어떤 신뢰도를 내는지는 31-12 실측이 필요하다. `MIN_KEYPOINT_VISIBILITY = 0.3` 은 생성물 특성에 따라 31-13 에서 재조정될 수 있다.
- **31-05 `safe_decode_image` 와 물리적 함수 공용화는 미실행** — wave 순서상 31-05 가 병렬이라 계약 동등성(같은 cap 집합, decode 전/직후 검사)으로만 맞췄다. 상한 drift 는 `test_caps_match_pod_endpoint_contract` 가 server.py 방향으로만 잡으므로, 31-05 확정 후 judge 쪽 상수와도 대조하는 테스트를 추가하면 좋다.

---
*Phase: 31-api-visual-correction*
*Completed: 2026-07-20*

## Self-Check: PASSED

- 산출물 4개 파일 전부 존재 확인
- 태스크 커밋 2개(`5b32e52`, `9a6ed17`) git 이력 확인
- `python3 -m pytest backend/tests/phase31 -q` → 139 passed
- 전체 스위트 실패 41건이 pre-existing 베이스라인과 동일(파일·건수) 확인
- `pose_gate` import 시 torch/onnxruntime/rtmlib/ultralytics/cv2 로드 0 확인
- STATE.md / ROADMAP.md 미변경 (오케스트레이터 소유)
