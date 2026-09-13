---
id: 260913-udr
slug: rot180-inversion-pass
title: rot180 inversion pass — 역립 프레임을 정립으로 돌려 다시 보고, 두 패스 불일치를 관절별로 기록한다
date: 2026-09-13
status: planned
mode: quick-full
phase: quick-260913-udr
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
files_modified:
  - backend/shared/python/sunity_shared/analysis/inversion_rot180.py
  - backend/tests/test_inversion_rot180.py
  - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py
  - backend/tests/test_rtmw_engine_rot180.py
  - backend/runpod_inference/start_server.sh
  - backend/runpod_inference/server.py
  - backend/runpod_inference/README.md
must_haves:
  truths:
    - 게이트 off(코드 기본)면 estimate 산출은 현행과 동일하다 — mock 추론기 호출 수 = T, rot180 경로 미진입
    - 게이트 on 이고 1차 결과로 detect_inversion 이 참일 때만 프레임 180° 회전 → 재검출·재추론 → 좌표 역매핑으로 2차가 돈다
    - 2차 미검출·비유한·범위 이탈 프레임은 1차를 그대로 쓴다 (프레임 단위 fail-safe, 전체 폐기 아님)
    - 좌우 관절 인덱스는 스왑되지 않는다 — 180° 회전은 det=+1 진짜 회전이라 손잡이가 보존된다
    - ROT180 과 PR 플래그가 동시에 켜지면 회전이 이기고 PR 워프는 돌지 않는다 (3패스 금지, 코드로 강제)
    - 관절별 불일치(‖p_orig − p_rot180‖ / torso)는 계산해 로그로만 남긴다 — 임계·감점 억제·점수 변경·계약 변경 0
    - Pod env 플래그는 off 로 박제되고 /health 가 그 상태를 보여준다 — 켜는 것은 이 작업이 아니다
  artifacts:
    - backend/shared/python/sunity_shared/analysis/inversion_rot180.py
    - backend/tests/test_inversion_rot180.py
    - backend/tests/test_rtmw_engine_rot180.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py
    - backend/runpod_inference/start_server.sh
    - backend/runpod_inference/server.py
  key_links:
    - rtmw_engine.estimate → (ROT180_INVERSION_ENABLED 판정) → _maybe_second_pass_rot180 | _maybe_second_pass_inversion
    - _maybe_second_pass_rot180 → inversion_warp.detect_inversion (게이트 판정 재사용, 1차 결과가 입력)
    - _maybe_second_pass_rot180 → inversion_rot180.rotate_frames_180 → self._infer_raw → inversion_rot180.unrotate_points_180 → inversion_rot180.choose_pass
    - server.py /health envFlags.ROT180_INVERSION_ENABLED ← start_server.sh export
---

# rot180 inversion pass — 제대로 보게 만들고, 계기를 기록한다

한 줄: **역립 클립이면 프레임을 180° 돌려 검출부터 다시 하고, 돌려서 얻은 좌표를 원본
공간으로 되돌려 쓴다. 두 패스가 얼마나 다른지는 관절별로 재서 로그에 남긴다. 감점은 건드리지
않는다.**

## 실측 근거 (`evidence/MEASUREMENTS.md` — 전제 전부가 여기 있다)

| 항목 | 실측 | 절 |
|---|---|---|
| 역립은 학습 분포 밖 (회전 증강 ±90°, crop rot=0 하드코딩) → 180° 는 zero-shot | 논리적 귀결 | §1 |
| belle 영상 181f: 붕괴 9→**0**, 뼈위반 p90 2.108→**0.776**(−63%), 평균 conf 0.567→**0.707** | 프레임 180° 회전(검출+포즈) | §2 |
| **검출기 몫이 크다** — bbox 고정 + crop rot=180 만 주면 conf 0.519, 뼈위반 2.163 (절반만) | `box_rot` | §2 |
| 기준 모션(정은지, 다른 촬영) 158f: conf 0.516→**0.716**, 붕괴 3→**0**, R전완 뼈위반 19.9→**0.83** | 재현 | §3 |
| 정립 프레임 무해: 0.635→0.644 (belle) / 0.582→0.670 (정은지) | 두 영상 | §2·§3 |
| 운영 ON 인 PR 원근 워프는 boneCV **−2%**, 회전은 **−23%**. `rot+pr` −28% 지만 3패스 | 정면 대결 | §4 |
| 두 패스 불일치: 동적범위 570배·**이봉**(골짜기 0.3~0.7 torso). conf: 2.7배·단봉 | 계기 | §5 |
| t=8.1s `right_elbow`(관측 실패) 불일치 0.75 torso vs `left_hip`(정상) 0.04 — conf 는 0.434 vs 0.504 로 못 가른다 | 대표 사례 | §5 |

기각된 가설(회전 메타데이터 버그 / 엉뚱한 사람 선택 / "붕괴 25프레임")은 §6 에 박제돼 있다.
**다시 열지 말 것.**

## ★ 왜 이번엔 측정·기록만 하는가 (반드시 승계)

조사 실측 결과 감점이 사라지면 **점수가 올라간다**:
`final = max(25, round(100 − min(40, Σ|실행|) − Σ|치명|))` 이라 record 0 이면 100점이다.
실측 powerspin 62→67(quick-260910-ovo §(2)), 산술 elbow-twist 63→100. 즉 "못 봤다"가
"완벽하다"로 번역된다. 불일치로 감점을 막으려면 `wouldBePoints` 동반이 **필수**이고 그건
별건(후속)이다. 그래서 이번엔 **아무것도 지우지 않는다.** 계기 값만 낸다.

## 결정 사항 (계획 시점에 고정 — 실행자는 재논의하지 않는다)

| # | 결정 | 이유 |
|---|---|---|
| R-1 | 새 모듈 이름 = `inversion_rot180.py` (`inversion_warp.py` 옆) | 본보기이자 경쟁자와 나란히. 이름으로 관계가 읽힌다 |
| R-2 | 새 env = `ROT180_INVERSION_ENABLED`, 코드 기본 **off**, 판정 문자열은 PR 선례와 동일(`"1"`/`"true"`) | `PR_INVERSION_ENABLED` 선례 그대로 |
| R-3 | **두 플래그 동시 on 이면 회전이 이긴다.** `estimate()` 가 rot180 플래그를 먼저 보고, 켜져 있으면 PR 훅을 호출하지 않는다 (경고 로그 1줄). 3패스 금지 | §4: 회전 −23% vs PR −2%. `rot+pr` 은 후속 검토 대상이지 지금 붙일 것이 아니다 |
| R-4 | 채택 규칙 = **클립 게이트(detect_inversion 참) + 프레임 유효성** 뿐. 불일치 크기로 채택을 정하지 않는다 | 임계는 범위 밖. 모듈은 임계를 정의하지 않는다 (§5 표본 = 영상 2편, 곡선맞춤 위험) |
| R-5 | 1차 미검출 프레임은 2차가 검출해도 **채택하지 않는다** (PR 선례 동일). 대신 `first_missing` 건수를 로그에 남긴다 | `NoHumanError`·`detected_count` 가 1차 기준으로 이미 확정됐다. 검출 집합을 바꾸는 것은 범위 밖. 크기는 로그로 알 수 있게 |
| R-6 | 불일치는 **로그만**. `PoseFrame`·산출 doc 에 싣지 않는다 | `PoseFrame` 은 TS/contract 3벌 lockstep 인 frozen dataclass. 읽는 소비처가 없다 — 소비처가 생길 때 계약을 연다 |
| R-7 | 채택 시 좌표는 133 전량을 역매핑하고, 유효성 판정은 body-17 범위 + 133 전량 유한으로 본다 | PR 선례(`unwarp_frame_keypoints` body-17 + 나머지 유한) 그대로. 좌표공간 혼합 금지 |
| R-8 | 새 모듈은 `inversion_warp` 를 import 하지 않는다 (상수는 같은 값으로 자체 선언, 주석으로 선례 인용). `skeleton.KEYPOINT_NAMES` 는 import 해도 된다 | PR 워프가 나중에 빠져도 회전 모듈이 살아야 한다 |

---

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 순수 모듈 inversion_rot180.py — 회전·역매핑·불일치 계기 + 테스트</name>
  <files>backend/shared/python/sunity_shared/analysis/inversion_rot180.py, backend/tests/test_inversion_rot180.py</files>
  <behavior>
    - 회전 두 번 = 항등. 한 번 = 프레임별 np.rot90(f, 2) 와 동일. 반환은 C-contiguous, dtype 보존
    - 픽셀 규약과 좌표 규약이 일치한다: (H=4,W=6) 프레임의 (x=2,y=1) 한 점을 켜고 돌리면 켜진 픽셀은 (3,2) 에 있고, unrotate_points_180([[3,2]], 6, 4) == [[2,1]]
    - unrotate_points_180 는 자기역원 — 두 번 적용하면 원좌표 (프레임 밖 좌표·NaN 포함, NaN 은 NaN 으로 통과)
    - 불일치는 torso 정규화라 해상도 무관 — 두 골격을 3.7배 스케일해도 벡터 동일
    - torso 가 두 패스 모두 비유한/0 이면 불일치 전부 NaN (inf 금지). 한 패스만 비유한이면 나머지 패스 torso 로 계산 (nanmean)
    - 대표 사례 재현: 한 관절만 421px 벌어지고 torso 가 561px 이면 그 관절 불일치 = 0.75 (MEASUREMENTS §5)
    - choose_pass 사유 5종이 순서대로 난다: first_missing / second_missing / second_nonfinite / second_out_of_bounds / adopted
    - 180° 회전은 손잡이를 보존하고 수평 flip 은 뒤집는다 — 비대칭 골격에 unrotate_points_180 를 적용해도 어깨벡터×몸통벡터 부호가 같고, x→W-1-x 만 적용하면 부호가 뒤집힌다 (좌우 인덱스 스왑이 필요 없는 이유를 테스트가 박제)
    - 순수성: 모듈 소스에 torch / cv2 / onnxruntime / rtmlib / boto3 import 0
  </behavior>
  <action>
`limb_collapse.py:1-37` 의 형식을 그대로 따라 모듈 독스트링을 쓴다 — **위 실측표(§2 4변형, §3 일반화, §4 정면 대결, §5 계기 동적범위·이봉·대표 사례)를 옮겨 박제**하고, 이어서 ★ 곡선맞춤 위험(표본 = 영상 2편, 그래서 이 모듈은 임계를 정의하지 않고 불일치 값만 낸다), 왜 프레임을 돌려 검출부터 다시 하는가(§2 분해: 검출기 몫), 왜 좌우 인덱스 스왑이 없는가(det=+1), 왜 1차 미검출은 채택하지 않는가(R-5)를 한국어로 적는다. `MEASUREMENTS.md` 절 번호를 인용한다. 순수 모듈 규약: numpy 만, AWS/모델/네트워크/cv2/torch 의존 0.

공개 API (이름·시그니처 고정 — Task 2 가 이 계약에 배선한다):

- `rotate_frames_180(frames)` — `(T,H,W,C)` 배열을 프레임별 180° 회전. 구현은 `frames[:, ::-1, ::-1]` 을 `np.ascontiguousarray` 로 감싼 것 (onnxruntime/rtmlib 입력이 contiguous 여야 한다 — `evidence/decompose.py:44` 가 `np.ascontiguousarray(np.rot90(img, 2))` 를 쓴 이유). ndim != 4 면 `ValueError`.
- `unrotate_points_180(points_xy, image_width, image_height)` — `(N,2)` 에 `x' = (W-1) - x`, `y' = (H-1) - y`. 자기역원이라 회전공간→원본, 원본→회전공간 둘 다 이 함수 하나. 규약은 `evidence/tta_disagree.py:47` 과 **자릿수까지 동일**해야 실측과 같은 좌표가 나온다. NaN 은 마스킹하지 않고 NaN 으로 통과.
- `torso_length(kps_xy)` — `(K,2)`, K ≥ 13. 어깨(5,6) 중점과 엉덩이(11,12) 중점 거리. 4점 중 비유한이 있으면 nan.
- `joint_disagreement(kps_a_xy, kps_b_xy)` — 같은 좌표공간(원본 프레임)의 두 패스 좌표 `(K,2)` → body-17 불일치 `(17,)`. 분모 torso = 두 패스 torso 의 nanmean (`tta_disagree.py:55-59` 와 같은 정의). torso 가 비유한이거나 `_TORSO_EPS`(1e-6) 미만이면 전부 NaN. 관절 좌표가 비유한이면 그 관절만 NaN. **inf 를 내지 않는다** — 실측 스크립트의 `+1e-9` 대신 NaN 으로 떨어뜨리는 이유(0 나눗셈이 "매우 큰 불일치"로 둔갑하면 계기가 거짓말한다)를 주석에 쓴다.
- `disagreement_summary(d)` — `(T,17)` → dict: `valid_pairs`, `p50`, `p90`, `max`(전체 유효 쌍), `per_joint`(`skeleton.KEYPOINT_NAMES` 순으로 `{name: (p50, p90)}`). 유효 쌍 0 이면 `valid_pairs=0` 에 나머지 nan. 로그 전용 — 판정하지 않는다.
- `@dataclass(frozen=True) class PassChoice: use_second: bool; reason: str` 과 사유 문자열 상수 `REASON_ADOPTED = "adopted"`, `REASON_FIRST_MISSING = "first_missing"`, `REASON_SECOND_MISSING = "second_missing"`, `REASON_SECOND_NONFINITE = "second_nonfinite"`, `REASON_SECOND_OUT_OF_BOUNDS = "second_out_of_bounds"`.
- `choose_pass(first, second_back, image_width, image_height)` — `first` = `(kps, scores) | None`, `second_back` = `(kps_back, scores) | None` (**이미 역매핑된** 좌표). 판정 순서: first None → first_missing; second None → second_missing; 133 전량 중 비유한 → second_nonfinite; body-17 이 `[-tol, W+tol] × [-tol, H+tol]` 밖 → second_out_of_bounds (tol = 각 변의 `BOUNDS_TOLERANCE = 0.25`, PR 선례 `UNWARP_BOUNDS_TOLERANCE` 와 같은 값을 자체 선언 — R-8); 그 외 adopted. 근거(reason)를 항상 함께 돌려준다 — 왜 그 패스를 골랐는지 로그가 집계한다.

상수는 모듈 상단에 이름 붙여 선언하고 값 옆에 근거를 주석으로: `_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP = 5, 6, 11, 12`(COCO body, RTMW 133 선두 17), `_TORSO_EPS`, `BOUNDS_TOLERANCE`. **임계 상수는 없다.** `inversion_warp` 를 import 하지 않는다 (R-8).

테스트는 `backend/tests/test_inversion_rot180.py` 신설 — 위 `<behavior>` 9개 축을 각각 한 테스트로. 좌우 손잡이 테스트는 `test_rotation_preserves_handedness_flip_does_not` 이름으로, 어깨벡터(오른어깨−왼어깨)와 몸통벡터(엉덩이중점−어깨중점)의 2D 외적 부호를 비교한다. 순수성 테스트는 `phase32/test_inversion_warp.py:306-324` `TestPurity` 형식. 수치 채우기 금지 — 위 축 외의 테스트를 늘리지 않는다.

착수 전에 기준선을 잰다: `cd backend && python3 -m pytest -q --continue-on-collection-errors 2>&1 | tail -3` 의 passed/failed/errors 숫자를 SUMMARY 에 적을 것 (수집오류 7건 = 로컬 `imageio_ffmpeg` 미설치, 기존 결손 — 고치지 않는다).

커밋: `feat(quick-260913-udr): rot180 inversion 순수 모듈 — 회전·역매핑·불일치 계기`
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/test_inversion_rot180.py -q && grep -v '^\s*#' shared/python/sunity_shared/analysis/inversion_rot180.py | grep -c -E "^(import|from) (torch|cv2|onnxruntime|rtmlib|boto3)" | grep -qx 0 && grep -v '^\s*#' shared/python/sunity_shared/analysis/inversion_rot180.py | grep -c "inversion_warp" | grep -qx 0</automated>
  </verify>
  <done>신규 테스트 9건 전건 통과. 모듈에 heavy import 0, inversion_warp import 0, 임계 상수 0. 독스트링에 MEASUREMENTS §2·§3·§4·§5 실측표와 곡선맞춤 경고가 박제됨. 원자 커밋 1건.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: RTMWPoseEngine 배선 — ROT180_INVERSION_ENABLED 게이트, 회전 2차, 프레임 fail-safe, 불일치 로그</name>
  <files>backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py, backend/tests/test_rtmw_engine_rot180.py</files>
  <behavior>
    - 두 플래그 다 off: mock 호출 수 = T. `_maybe_second_pass_rot180` 를 raise 하도록 monkeypatch 해도 estimate 가 정상 반환 (경로 미진입 증명)
    - rot180 on + 정립(mock 이 정립 골격 반환): detect False → 호출 수 = T, 산출이 off 기준선과 `==` 이고 `pickle.dumps` 바이트도 같다
    - rot180 on + 역립 + 마커 인식 mock(회전 프레임을 받으면 같은 골격의 회전공간 좌표를 돌려줌): 호출 수 = 2T, 산출이 off 기준선과 `==` — 역매핑이 좌표를 정확히 되돌리고 **이름별 좌표가 동일(좌우 스왑 없음)**
    - rot180 on + 역립 + 회전 패스가 회전공간 x 에 +5 를 더해 돌려줌: 채택된 프레임의 원본공간 x 는 기준선보다 **−5** (역매핑 방향이 옳다는 배선 증명), 산출 != 기준선
    - 회전 패스가 t∈{2,5} 에서 미검출(빈 배열) → 그 두 프레임은 기준선과 같고 나머지는 채택됨
    - 회전 패스가 t=3 의 body 관절 하나에 NaN → t=3 은 기준선과 같음
    - 회전 패스가 예외를 던짐 → estimate 는 예외 없이 off 기준선과 `==` 를 돌려줌
    - 두 플래그 동시 on: `inversion_warp.warp_frames` 를 raise 로 monkeypatch 해도 호출되지 않고(3패스 없음), 호출 수 = 2T, caplog 에 `rot180_inversion both_flags_on` 경고 1줄
    - 기존 `tests/phase32/test_inversion_warp.py` 의 `TestEngineSecondPassHook` 5건과 `tests/test_rtmw_engine.py` 가 그대로 통과 (PR 경로 무회귀)
  </behavior>
  <action>
`rtmw_engine.py` 에 다음을 더한다. **`_maybe_second_pass_inversion` 본문은 한 줄도 바꾸지 않는다.**

(a) 모듈 상수 `_ROT180_INVERSION_ENV = "ROT180_INVERSION_ENABLED"` 를 `_PR_INVERSION_ENV`(:59) 바로 아래에, 같은 형식의 주석(코드 기본 off, 켜는 곳은 Pod `start_server.sh`, quick-260913-udr, MEASUREMENTS §2-§4 요약 한 줄)과 함께 선언한다. 판정 헬퍼 `_env_on(name)` 을 하나 두고 PR 선례와 같은 문자열(`"1"`/`"true"`, strip+lower)을 쓴다 — 새 플래그에만 쓰고 PR 의 기존 판정 줄은 건드리지 않는다.

(b) `estimate()` 의 `:223-226` 반환부를 디스패처로 바꾼다: rot180 플래그가 켜져 있으면 — PR 플래그도 켜져 있을 때 `log.warning("rot180_inversion both_flags_on pr_warp_skipped=true")` 1줄 — `_maybe_second_pass_rot180(...)` 를 돌려주고, 아니면 기존대로 `_maybe_second_pass_inversion(...)`. 이것이 R-3(회전이 이긴다, 3패스 금지)의 코드 강제다. `estimate` 독스트링 `:194-197` 에 디스패처 설명을 덧붙인다.

(c) `_maybe_second_pass_rot180(self, frames, raw_first, pose_frames_first, pole_axis, image_width, image_height)` 를 `_maybe_second_pass_inversion` **바로 다음 자리**에 같은 시그니처로 만든다. 독스트링에 구조와 안전 규약을 PR 선례 형식으로 쓰고 MEASUREMENTS §2(검출부터 다시), §4(PR 대비), §5(계기)를 인용한다. 순서:
  1. `from ...inversion_warp import detect_inversion` 과 `from ...inversion_rot180 import (rotate_frames_180, unrotate_points_180, joint_disagreement, disagreement_summary, choose_pass, REASON_*)` 를 함수 내부 lazy import (어댑터 관례, off 경로 import 비용 0).
  2. `raw_first` 로 `(T,133,2)` kxy / `(T,133)` ks 를 채우고 `detect_inversion` → `log.info("rot180_inversion detect is_inverted=%s ratio=%.3f run=%d valid=%d/%d", ...)`. 거짓이면 `pose_frames_first` 그대로.
  3. `t0 = time.perf_counter()`. `try:` `rotated = rotate_frames_180(np.asarray(frames))` → `raw_second = self._infer_raw(rotated)` `except Exception:` `log.exception("rot180_inversion 2차 추론 실패 — 1차 결과 유지")` 후 1차 반환 (`# noqa: BLE001` + 이유). 2차는 보너스다 — 실패가 분석을 죽이면 안 된다.
  4. 프레임 루프: `raw_second[t]` 가 있으면 `kps2` 를 copy 해 `[:, :2]` 전량을 `unrotate_points_180(..., W, H)` 로 원본공간에 되돌린 뒤 `choose_pass(raw_first[t], (kps_back, scores2), W, H)`. 사유별 카운터 dict 를 누적. `use_second` 면 `merged[t] = (kps_back_full, scores2)` (신뢰도 = 2차 것, PR 선례). 아니면 1차 유지.
  5. 계기: 1차와 역매핑된 2차가 **둘 다 존재**하는 프레임마다 body-17 `joint_disagreement` 를 `(T,17)` 배열(기본 NaN)에 채운다 — 채택 여부와 무관하게 잰다(계기는 판정이 아니다). `disagreement_summary` 로 `log.info("rot180_inversion disagreement valid_pairs=%d p50=%.3f p90=%.3f max=%.3f", ...)` 1줄과 `log.info("rot180_inversion disagreement_by_joint %s", ...)` 1줄 (`name=p50/p90` 17쌍, 소수 3자리). 어디에도 저장하지 않는다 (R-6). 이 값을 쓰는 곳이 생기면 그때 `PoseFrame` 계약을 연다는 주석을 남긴다.
  6. `log.info("rot180_inversion applied=true replaced=%d/%d adopted=%d first_missing=%d second_missing=%d second_nonfinite=%d second_out_of_bounds=%d second_pass_ms=%d", ...)`. `replaced == 0` 이면 1차 반환. 아니면 `self._build_pose_frames(merged, W, H, pole_axis)`.

(d) 테스트 `backend/tests/test_rtmw_engine_rot180.py` 신설 — `phase32/test_inversion_warp.py:203-303` `TestEngineSecondPassHook` 의 골격(`create_with_inferencer` DI, `_pole()`, W=72/H=128, `monkeypatch.delenv/setenv`, `out == baseline`)을 그대로 따른다. 마커 인식 mock: 원본 프레임은 `frames[t, 0, 0, 0] = 255`, 회전 프레임에선 그 마커가 `(H-1, W-1)` 에 온다 — mock 은 마커 위치로 "회전 프레임이냐"를 판단하고, 회전 프레임이면 **테스트 안에서 직접 계산한** `x→W-1-x, y→H-1-y` 좌표(모듈 함수를 쓰지 않는다 — 독립 검증)를 돌려준다. 비대칭 골격(왼어깨 x < 오른어깨 x, 역립: 엉덩이 y < 어깨 y, 마진 ≥ torso 0.3 배, 8프레임 이상 지속)을 쓴다. `<behavior>` 9개 축을 각각 한 테스트로; 좌우 스왑 없음은 `keypoints_2d["left_shoulder"]` 등 **이름으로** 기준선과 대조한다.

커밋: `feat(quick-260913-udr): RTMW 엔진 rot180 2-pass 배선 — ROT180_INVERSION_ENABLED, 기본 off`
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && python3 -m pytest tests/test_rtmw_engine_rot180.py tests/phase32/test_inversion_warp.py tests/test_rtmw_engine.py tests/test_inversion_rot180.py -q && git diff --quiet HEAD~1 HEAD -- shared/python/sunity_shared/analysis/inversion_warp.py && git diff --quiet HEAD -- shared/python/sunity_shared/analysis/inversion_warp.py</automated>
  </verify>
  <done>배선 테스트 9건 + 기존 phase32 엔진 훅 5건 + test_rtmw_engine 전건 통과. `_maybe_second_pass_inversion` 본문·`inversion_warp.py` 무수정 (`git show --stat` 로 확인). 두 플래그 off 경로는 rot180 함수에 진입하지 않는다. 원자 커밋 1건.</done>
</task>

<task type="auto">
  <name>Task 3: Pod env 자리 — start_server.sh off 박제 + /health 노출 + README 플래그 목록</name>
  <files>backend/runpod_inference/start_server.sh, backend/runpod_inference/server.py, backend/runpod_inference/README.md</files>
  <action>
**켜지 않는다.** 자리만 만든다 (Pod 은 belle 승인 때만 띄운다 — 지금 Pod 0대).

(a) `start_server.sh:23` (`PR_INVERSION_ENABLED=1`) 바로 아래에 `export ROT180_INVERSION_ENABLED=0` 을 명시적 **0** 으로 박제한다 (주석 처리가 아니라 값 0 — `/health` 가 false 를 보여줘야 "안 켠 것"과 "줄이 없는 것"을 구분한다). 같은 줄 주석: quick-260913-udr · 실측(MEASUREMENTS §2-§4: 붕괴 9→0, boneCV −23%)은 **로컬 CPU** 이고 GPU 실경로는 미검증이라 off · 켜기 = 이 값을 1 로 바꾸고 재기동 (belle 승인 후) · 켜지면 `PR_INVERSION_ENABLED` 보다 우선하고 PR 워프는 돌지 않는다 (3패스 금지). 이 파일의 다른 줄은 건드리지 않는다. Pod 사본 `/workspace/start_server.sh` 와 md5 동일 규칙(README:27-28)은 그대로다 — 이번 작업으로 리포 정본이 바뀌었으니 다음 Pod 기동 때 사본을 갱신해야 한다는 사실을 SUMMARY 에 적는다.

(b) `server.py:323-326` `envFlags` 에 `"ROT180_INVERSION_ENABLED": _env_flag("ROT180_INVERSION_ENABLED")` 를 더한다. 값은 bool 만 (env 원문 노출 금지 — `:69-71` 기존 규약). `:65` 의 주석 목록에도 플래그를 추가한다.

(c) `README.md:32` 의 플래그 열거에 `ROT180_INVERSION_ENABLED` 를 추가한다 (맨손 uvicorn 기동 시 빠지는 플래그 목록 — 이 플래그는 off 가 기본이라 누락돼도 "조용한 OFF 함정"은 아니지만, 켠 뒤에는 같은 함정이 된다는 한 줄).

SUMMARY 에 반드시 적을 것:
  - **켜는 절차**: 리포 `start_server.sh` 의 0→1 → Pod 사본 갱신(md5 대조) → 재기동 → `GET /health` 의 `envFlags.ROT180_INVERSION_ENABLED == true` 확인 → 역립 영상 1편 분석 후 `/tmp/runpod_server.log` 에서 `rot180_inversion detect` / `disagreement` / `applied` 3줄 확인. 이 절차는 **이번 작업이 아니다.**
  - **GPU 실경로 미검증** — 이 코드의 실제 경로는 RunPod GPU Pod 이고 지금 Pod 은 0대다. 로컬에서 검증한 것 = 순수 모듈 단위테스트 + mock 추론기 배선 테스트. 실측 §2-§5 는 로컬 CPU onnxruntime 이었고, CUDA EP 에서 같은 수치가 나오는지는 Pod 실행으로만 확인된다. "완료"라고 적지 않는다.
  - 착수 전/후 pytest 숫자 (Task 1 에서 잰 기준선 대비 증가분 = 신규 18건, 실패 목록 동일).

커밋: `chore(quick-260913-udr): Pod env 자리 — ROT180_INVERSION_ENABLED off 박제 + /health 노출`
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && bash -n runpod_inference/start_server.sh && grep -v '^\s*#' runpod_inference/start_server.sh | grep -c "^export ROT180_INVERSION_ENABLED=0" | grep -qx 1 && grep -c "ROT180_INVERSION_ENABLED" runpod_inference/server.py | grep -qvx 0 && grep -c "ROT180_INVERSION_ENABLED" runpod_inference/README.md | grep -qvx 0 && python3 -m pytest tests/test_runpod_server.py -q && python3 -m pytest -q --continue-on-collection-errors 2>&1 | tail -1</automated>
  </verify>
  <done>start_server.sh 에 `=0` 한 줄, /health envFlags 에 bool 키 1개, README 목록 1건. `test_runpod_server.py` 통과. 전체 pytest 가 기준선 대비 +18 passed, 실패 목록 동일, 수집오류 7건 동일. SUMMARY 에 켜는 절차·GPU 미검증·숫자가 적힘. 원자 커밋 1건.</done>
</task>

</tasks>

---

## ★ 하지 말 것

- **감점 억제·`unjudgedJoints` 확장·점수 변경 — 전부 후속.** 이 작업은 아무것도 지우지 않는다.
- **임계 상수를 두지 마라.** 불일치 값만 낸다. 골짜기 0.3~0.7 은 영상 2편의 관측이지 규칙이 아니다.
- **`temporal.py` / `features.py` 무접촉.** 별건.
- **`inversion_warp.py` 와 `_maybe_second_pass_inversion` 본문 무수정.** PR 경로는 바이트 동일해야 한다.
- **`PoseFrame`·`models.py`·`contract.md`·`analysis.ts` 무접촉.** 소비처가 없는 계약을 열지 않는다 (R-6).
- **`sam deploy`·Pod 기동·플래그 on 금지.**
- **`.planning/` 문서는 커밋하지 않는다** — 오케스트레이터가 커밋한다.
- 좌우 인덱스 스왑 코드를 넣지 마라. 180° 는 det=+1 이다 (§ settled 4). 09-10 좌우 팔꿈치 건은 종결됐다.
- 이모지 금지. 주석은 한국어로 **왜**를 적고 `MEASUREMENTS.md` 절을 인용.

## 검증의 한계 (SUMMARY 가 승계할 것)

- 이 코드의 실제 경로는 RunPod GPU Pod 이고 지금 Pod 은 0대다. 로컬 검증 = 순수 모듈 단위테스트 + mock 추론기 배선 테스트뿐. **GPU 실경로는 미검증.**
- 실측 §2-§5 는 로컬 CPU onnxruntime 재현이다. 같은 가중치·같은 전처리이므로 CUDA EP 에서도 같은 방향이 기대되지만, 수치 동일은 Pod 실행으로만 확인된다 (CUDA EP 결정론 한계는 `ort_determinism.py` 참조).
- 마커 인식 mock 은 픽셀을 보지 않는 상수 골격이라 "회전이 검출기를 돕는가"는 증명하지 못한다 — 그건 §2 실측이 답한 것이고 테스트는 **배선의 좌표 정합**만 증명한다.
- 표본은 영상 2편이다. 불일치 분포의 이봉성과 골짜기 위치는 표본이 늘면 움직일 수 있다. 그래서 임계를 정하지 않았다.

## 커밋 규약

태스크마다 원자 커밋 1건, 접두 `feat|chore(quick-260913-udr): ...`. 마지막 줄에 지정된 Co-Authored-By / Claude-Session 트레일러.

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Pod env → 엔진 플래그 | `ROT180_INVERSION_ENABLED` 문자열을 bool 로 해석. 운영자만 쓴다 |
| /health (무인증) → 외부 모니터 | 플래그 bool 노출. 값 원문·토큰·키는 싣지 않는다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-udr-01 | Information Disclosure | `server.py` `/health.envFlags` | mitigate | `_env_flag` 로 bool 만 노출 (기존 T-04-W5-01 규약 그대로). env 원문 값 금지 |
| T-udr-02 | Denial of Service | `_maybe_second_pass_rot180` 2차 추론 (GPU 2배 부하) | accept | 클립 게이트(detect_inversion)가 참일 때만 1회. 역립 클립 한정이고 Pod 은 단일 워커·순차 처리. 3패스는 코드로 금지 |
| T-udr-03 | Tampering | 2차 좌표가 1차를 대체 | mitigate | 프레임 단위 유효성(유한·범위)·1차 미검출 미채택·예외 시 1차 유지. off 경로는 rot180 함수 미진입 (테스트가 박제) |
| T-udr-SC | Tampering | 패키지 설치 | accept | 신규 패키지 0 (numpy 만). 설치 태스크 없음 |
</threat_model>

<verification>
- `cd backend && python3 -m pytest tests/test_inversion_rot180.py tests/test_rtmw_engine_rot180.py tests/phase32/test_inversion_warp.py tests/test_rtmw_engine.py tests/test_runpod_server.py -q` 전건 통과
- `cd backend && python3 -m pytest -q --continue-on-collection-errors` — 기준선 대비 +18 passed, 실패 목록·수집오류 7건 동일
- `git show --stat HEAD~2..HEAD` 에 `inversion_warp.py`, `temporal.py`, `features.py`, `pose_frame.py`, `models.py`, `contract.md`, `analysis.ts` 가 없다
- `grep -n "ROT180_INVERSION_ENABLED" backend/runpod_inference/start_server.sh` 가 `=0` 한 줄
</verification>

<success_criteria>
- 순수 모듈이 회전·역매핑·불일치·채택 사유를 numpy 만으로 내고, 독스트링에 실측표가 박제됨
- 엔진이 플래그 on + 역립 검출 시에만 2차를 돌리고, off/정립/실패 경로는 1차 그대로
- 회전 플래그가 PR 플래그를 이기고 3패스가 없음을 테스트가 증명
- 좌우 인덱스가 스왑되지 않음을 순수 테스트(손잡이 부호)와 배선 테스트(이름별 대조) 둘 다 증명
- Pod env 자리가 off 로 박제되고 /health 가 보여줌. SUMMARY 에 켜는 절차와 GPU 미검증이 명시됨
- 3 원자 커밋, `.planning/` 미커밋
</success_criteria>

<output>
실행 완료 시 `.planning/quick/260913-udr-rot180-inversion-pass/260913-udr-SUMMARY.md` 작성 (quick-260910-ovo SUMMARY 형식: 커밋표 · 착수 전/후 숫자 · 검증의 한계 · 남은 것). 커밋은 오케스트레이터가 한다.
</output>
