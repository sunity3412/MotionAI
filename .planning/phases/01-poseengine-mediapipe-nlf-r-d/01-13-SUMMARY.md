---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "13"
subsystem: ml-pose-engine
type: spike
tags:
  - spike
  - gemini-key-moment
  - ipsf-criteria
  - moment-list-sampling
  - score-01
  - pose-01
  - plan-12-dominant-a-resolution
  - parameter-store-securestring
  - no-human-scoring
  - belle_live_executed
  - measurement_unreliable_blocked
  - plan_14_entry_blocked
  - plan_16_required

dependency_graph:
  requires:
    - 01-11  # 5영상 sweep verdict gap_too_wide_blocked
    - 01-12  # 5가설 verdict (dominant (a) frame-mean + (e) 3D 분포)
    - 01-15  # IPSF GeometricCriterion 스키마 + ref-invert 1차 박제 (commit 861fb3a, 4264001)
  provides:
    - "sunity_shared.judging.gemini_moment_extractor — KeyMoment + GeminiMomentExtractor + assign_frame_indices + 좌표/점수/판단 정규식 가드"
    - "sunity_shared.judging.moment_dimensions — measure_moment_angles (8 joints 한정) / compute_criteria_gap / score_moment (line/angle 차원)"
    - "backend/research/spikes/spike_gemini_moment.py — report-only + live mode CLI (Plan 14 게이트 verdict 4 분기)"
    - "Plan 14 진입 게이트 정의 — minimum_failure 0 + line/angle ≥ 60"
  affects:
    - 01-14  # 5영상 재검증 sweep — Plan 13 live mode 통과 후 5영상 sweep 작성 진입
    - "Wave 3 진입 게이트 — Plan 13 belle Pod live mode + Plan 15 4영상 belle 라벨링 통과 후 Plan 04/05 진입 평가"

tech_stack:
  added:
    - "google-generativeai (Apache 2.0, lazy import) — Gemini 2.5 Pro multimodal key moment 추출 SDK. Lambda 런타임 미사용 (spike 전용)."
  patterns:
    - "Gemini lazy import — 모듈 로드 시점 0 import. _call_gemini override 로 단위 테스트 가능."
    - "API 키 = env GEMINI_API_KEY 우선 → AWS SSM Parameter Store /sunity/motion/gemini-api-key (SecureString) fallback. .env 하드코딩 금지 (CLAUDE.md §3)."
    - "응답 정규식 가드 3 카테고리 (좌표 / 점수 / 심사 판단) — SCORE-01 + memory analysis-objectivity-no-human-scores 1차 차단선."
    - "응답 캐시 — 같은 (video_uri, motion, model) 재호출 시 SDK 미호출 (비용 절감)."
    - "moment-list sampling — dimensions.py frame-mean path 와 격리. 운영 코드 진입은 Plan 14 통과 후 별 plan 책임."
    - "8 angle joints 한정 — measure_moment_angles 가 derive joint (hip/spine/thorax/neck_nose/head) 요청 시 ValueError. Plan 12 (d) keypoint mapping 회피."
    - "empty criteria 가드 — ref-climb 의도된 빈 list 같은 motion 입력 시 RuntimeError 'Plan 15 IPSF 라벨링 미진입'."

key_files:
  created:
    - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
    - backend/shared/python/sunity_shared/judging/moment_dimensions.py
    - backend/research/spikes/spike_gemini_moment.py
    - backend/tests/test_gemini_moment_extractor.py
    - backend/tests/test_moment_dimensions.py
    - backend/tests/test_spike_gemini_moment_smoke.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-PLAN.md
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-SUMMARY.md
  modified:
    - backend/shared/python/sunity_shared/judging/__init__.py   # append-only — KeyMoment / GeminiMomentExtractor / assign_frame_indices / CriteriaGap / measure_moment_angles / compute_criteria_gap / score_moment 재노출
    - backend/research/spikes/README.md                          # append-only — Plan 13 섹션 추가 (Plan 07/08/10/11/12 보존)

decisions:
  - "Plan 12 dominant 가설 (a) frame-mean 한계 (mean disagreement 45-52°) 해결 path = 'Gemini multimodal key moment + IPSF GeometricCriterion 비교'. dimensions.py frame-mean path 는 무수정, 본 plan 은 별도 moment-list sampling path 도입. 운영 코드 진입은 Plan 14 통과 후 별 plan 책임."
  - "8 angle joints (`skeleton.JOINT_KEYS`) 만 사용 — derive joint (hip/spine/thorax/neck_nose/head) 절대 사용 금지. Plan 12 (d) verdict (RTMPose H36M ordering vs NLF COCO ordering 17/17 다름) 회피. measure_moment_angles 가 8 외 joint 요청 시 ValueError."
  - "NLF 호출 0 — Plan 12 (c) verdict (NLF baseline span 23, var 60.56 strong) 후 영구 폐기. live mode spike 가 RTMPose+MB 단일 lift 사용 (NLF baseline 비교군 0). (c) 해결은 Plan 15 IPSF target 교체로 박제됨."
  - "(e) 두 엔진 3D 분포 차이 (root-relative distance 220+) → 본 plan scope 밖. RTMPose+MB 단일 lift 사용으로 우회. multi_engine_averaging 후속 spike 는 별 plan 책임."
  - "Gemini 역할 박제 = 시점 분류 + 자연어 번역만. 좌표 / 점수 / 심사 판단 출력 영구 금지 (SCORE-01 + memory analysis-objectivity-no-human-scores). 3 카테고리 정규식 가드 — _COORDINATE_REJECT_PATTERNS (x=/y=/keypoint/좌표/픽셀), _SCORE_REJECT_PATTERNS (score=/점수/X점/N/100), _JUDGMENT_REJECT_PATTERNS (심사/judgment/verdict/pass/fail)."
  - "API 키 = AWS SSM Parameter Store `/sunity/motion/gemini-api-key` (SecureString, STATE.md 2026-06-01 박제) + env GEMINI_API_KEY fallback. `.env` 하드코딩 영구 금지 (CLAUDE.md §3). boto3 lazy import — env 경로 사용 시 AWS 의존성 0."
  - "moment_key enum = VALID_MOMENT_KEYS (setup / hold / peak / release) — Plan 15 GeometricCriterion 과 동일 enum. KeyMoment.validate() 가드 + Gemini 응답 파싱 가드 + measure_moment_angles 입력 가드 3중 차단."
  - "Plan 14 진입 게이트 — minimum_failure 0 건 + line/angle 점수 ≥ 60. 기존 NLF 갭 baseline (D-14 ≤5) 영구 폐기 (Plan 15 commit), IPSF angle_target ± tolerance_full 갭 단일 기준."
  - "empty criteria 가드 — ref-climb (의도된 빈 list, IPSF Climbs 카테고리 = 각도 임계 X) 같은 motion 을 spike 입력 시 RuntimeError 'Plan 15 IPSF 라벨링 미진입'. silent skip 금지."
  - "T-6 belle Pod live mode 는 ref-invert 단독 시범 — Plan 15 1차 박제된 유일 motion (5 hold entries). 다른 4영상 시범은 belle 라벨링 완료 후 (Plan 15 T-5 belle 진입 후 Plan 14 sweep)."

requirements_completed: []
# POSE-01 / SCORE-01 — Plan 13 belle Pod live mode 통과 + Plan 14 5영상 sweep 통과 후 1차 충족.
# 본 plan = data path + spike infra 박제, 미충족.

metrics:
  duration: "~80 min executor (T-1~T-5 + 87 unit/smoke 테스트 + README + SUMMARY) + belle Pod live mode (T-6) 단일 영상 ~10분 (SDK 마이그레이션 fix 4회 포함)"
  completed_date: "2026-06-01 belle Pod live mode 실행 — verdict measurement_unreliable_blocked"
  tasks_completed: 6
  tasks_total: 6
  files_created: 8
  files_modified: 2
---

# Phase 01 Plan 13: Gemini key moment + IPSF criteria spike — measurement unreliable, Plan 14 blocked

**One-liner:** Plan 12 dominant (a) frame-mean 한계 해결 path 도입은 통과했으나,
ref-invert 단독 live mode 실행 결과 = **`minimum_requirement_fail` 5/5 + 측정값 자체 의심**.
정은지 (폴스포츠 세계챔피언) invert split peak hold 자세에서 right_shoulder 18.2° / left_hip 54.9° 등
인체학적으로 비정상적 측정값 출력. Plan 11 sweep frame-mean 70 + Plan 08 MP+MB frame-mean **92** 와
4-5배 차이. Plan 12 (e) verdict ("두 엔진 3D 분포 strong, distance 220+") 와 직접 연결 — RTMPose+MB
lift 신뢰도 약점 + 단일 frame sampling 좌우 noise 폭주. **Plan 14 진입 차단 — Plan 16 신설로
측정 신뢰도 root cause 해소 후 진입.**

---

## TL;DR

| 항목 | 내용 |
|---|---|
| **Verdict** | **`measurement_unreliable_blocked`** (live mode 통과, 측정값 자체 의심 — Plan 14 차단) |
| **단계 도달** | T-1 ~ T-6 완료. ref-invert 단독 시범 결과 5/5 minimum fail + 측정값 의심 박제 |
| **scope** | 데이터 path + spike infra — moment-list sampling 모듈 + CLI spike + 87 단위/스모크 테스트 |
| **신규 파일** | 8 (judging 모듈 2 + spike 1 + 테스트 3 + PLAN 1 + SUMMARY 1) |
| **수정 파일** | 2 (judging/__init__.py append-only + spikes/README.md append-only) |
| **단위/스모크 테스트** | 87 PASS (52 + 20 + 15, 0.17s, mmpose/torch/Gemini SDK 미import) |
| **만든 커밋** | 6 (PLAN / T-1 / T-2 / T-3 / T-4 / SUMMARY 예정) |
| **운영 코드 수정** | 0 (functions / runpod_inference / shared/analysis / shared/pose_lifters / dimensions.py / technique.py / FallbackRecognizer / pose_estimator.py 모두 무수정) |
| **기존 spike 수정** | 0 (spike_rtmpose / sweep_rtmpose / debug_dimensions / debug_gap_root_cause / rtmpose_to_h36m17 / mediapipe_to_h36m17 / spike_motionbert 모두 무수정) |
| **Plan 15 데이터 무수정** | 0 (geometric_criterion.py / loader.py / 5영상 YAML 모두 무수정) |
| **NLF 호출** | 0 (Plan 12 (c) verdict 후 영구 폐기) |
| **이모지** | 0 |
| **사람 점수 라벨링** | 0 (Gemini 응답 정규식 차단 3 카테고리 + KeyMoment.validate() + score_moment 모든 점수 = `kismam.score_from_deviation` 객관 매핑) |
| **다음 행동** | T-6 belle Pod live mode (ref-invert 단독 시범) → 결과 적재 → SUMMARY status `belle_live_passed` → Plan 14 5영상 sweep PLAN 작성 |

---

## 5가설 verdict 매핑 (Plan 12 → Plan 13)

| Plan 12 verdict | dominant | Plan 13 해결 path |
|---|---|---|
| (a) frame-mean 한계 (mean disagree 45-52°) | **strong (dominant)** | **본 plan 직접 해결** — moment-list sampling 도입 (`moment_dimensions.score_moment`) |
| (b) RTMPose headdown 약점 | weak | 본 plan scope 외 — HybrIK 비교군 영구 후순위 (memory `license-blocklist-pose.md`) |
| (c) NLF baseline 편차 | strong | Plan 15 IPSF target 교체로 해결됨 — Plan 13 NLF 호출 0 |
| (d) keypoint mapping 차이 | strong | 본 plan 우회 — `measure_moment_angles` 가 8 angle joints (`skeleton.JOINT_KEYS`) 만 허용, derive joint ValueError |
| (e) 두 엔진 3D 분포 차이 | **strong** | 본 plan scope 외 — RTMPose+MB 단일 lift 사용, multi_engine_averaging 후속 spike 별 plan |

---

## T-1 — `gemini_moment_extractor.py` (judging 모듈 확장)

### 모듈 구조

```
backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
  # Constants
  GEMINI_API_KEY_PARAM_NAME = "/sunity/motion/gemini-api-key"  # AWS SSM SecureString
  DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"
  _COORDINATE_REJECT_PATTERNS  # 8 regex (x=, y=, keypoint, kp[, 좌표, 픽셀, pixel)
  _SCORE_REJECT_PATTERNS       # 5 regex (score=, 점수, X점, out of, N/100)
  _JUDGMENT_REJECT_PATTERNS    # 6 regex (심사, judgment, judging, verdict, pass, fail)

  @dataclass(frozen=True) class KeyMoment
    motion / moment_key / timestamp_seconds / frame_index / confidence / source_response_excerpt
    validate() — moment_key ∈ VALID_MOMENT_KEYS, timestamp ≥ 0, frame_index ≥ 0,
                 0 ≤ confidence ≤ 1, source_excerpt 좌표/점수/판단 차단

  _enforce_no_coordinate_or_score(text, context) — 3 카테고리 정규식 가드 1차 차단선
  _load_api_key() — env GEMINI_API_KEY 우선 → AWS Parameter Store fallback → RuntimeError
  _parse_gemini_response(motion, raw_text) — JSON 파싱 + markdown fence 흡수 + 가드
  _strip_markdown_fence(text) — ```json ... ``` 제거

  @dataclass class GeminiMomentExtractor
    model_name / api_key_loader / _cache
    extract_key_moments(video_uri, motion) → list[KeyMoment]
    _call_gemini(video_uri, motion) → str  # lazy import google.generativeai

  assign_frame_indices(moments, fps, frames_total) — timestamp → frame_index 후처리 + validate
```

### 좌표/점수/판단 정규식 가드 매트릭스

| 카테고리 | 패턴 예시 | rationale |
|---|---|---|
| 좌표 | `x=120`, `y=80`, `keypoint`, `kp[0]`, `좌표`, `픽셀`, `pixel` | 좌표는 측정 엔진 (RTMPose+MB) 의 책임 — Gemini 가 출력하면 SCORE-01 위반 |
| 점수 | `score=85`, `점수`, `85점`, `out of 100`, `85/100` | 사람 점수 ground truth 영구 금지 (memory analysis-objectivity-no-human-scores) |
| 심사 판단 | `심사`, `judgment`, `judging`, `verdict`, `pass`, `fail` | 심사 판단 = IPSF GeometricCriterion + 측정값 비교로만, Gemini 금지 |

3 카테고리 위반 시 ValueError 메시지에 어느 카테고리인지 명시 + 매치된 패턴 출력 → 디버그 박제.

### API 키 로드 우선순위

1. **env `GEMINI_API_KEY`** — Pod / 로컬 dev 편의 (CLI export, 셸 세션 한정).
2. **AWS SSM Parameter Store `/sunity/motion/gemini-api-key`** (SecureString) — Lambda 기본.
3. 둘 다 없으면 RuntimeError 명확 메시지 + boto3 미설치 시 별도 hint.

boto3 lazy import — env 경로 사용 시 AWS 의존성 0 (테스트 monkeypatch 가능).

### 응답 캐시

`(video_uri, motion, model_name)` 키로 `_cache` dict 보관. 같은 호출 재시 SDK 미호출 → Pod 시간/
비용 절감. 다른 motion 호출은 새 API 호출.

### 단위 테스트 (52 PASS)

```bash
PYTHONPATH=backend/shared/python:. /Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python3 \
  -m pytest backend/tests/test_gemini_moment_extractor.py -v
# 52 passed in 0.05s
```

| 클래스 | tests | 범위 |
|---|---|---|
| TestKeyMomentValidate | 9 | valid + 5 가드 위반 + excerpt 좌표/점수 차단 |
| TestRejectPatterns | 18 | 좌표 7 + 점수 5 + 판단 4 + clean text + 빈 문자열 |
| TestLoadApiKey | 3 | env 우선 / boto3 미설치 RuntimeError / 상수 |
| TestParseResponse | 11 | 정상 + fence + JSON 오류 + 필수 키 누락 + 좌표/점수 차단 |
| TestStripMarkdownFence | 3 | plain / ```json / ``` 흡수 |
| TestExtractor | 4 | extract + cache + 모델 상수 |
| TestAssignFrameIndices | 5 | 기본 + clamp + invalid fps/frames + validate 후처리 |

---

## T-2 — `moment_dimensions.py` (moment-list sampling 점수)

### 모듈 구조

```
backend/shared/python/sunity_shared/judging/moment_dimensions.py
  _FULL_EXTENSION_DEG = 180.0  # IPSF Fully Extended Criteria

  measure_moment_angles(angles_TJ, frame_index, joint_keys=None) → dict[str, float]
    # 8 joints 만 허용 (derive joint ValueError)
    # frame_index 범위 가드 + NaN/inf 거부

  @dataclass(frozen=True) class CriteriaGap
    joint_key / measured_angle / angle_target / gap / beyond_tolerance /
    deduction / minimum_met / score

  compute_criteria_gap(measured_angle, criterion) → CriteriaGap
    # gap = |measured - target|
    # beyond_tolerance = max(0, gap - tolerance_full)
    # deduction = beyond_tolerance * deduction_per_step
    # minimum_met = measured >= minimum_requirement
    # score = kismam.score_from_deviation(gap, tolerance_full)

  score_moment(measured_angles_by_joint, criteria) → dict
    # line: angle_target == 180° entry 평균 신전 부족분 → score_from_deviation
    # angle: 전 entry 평균 갭 → score_from_deviation
    # minimum_failures: minimum 미달 joint_key list (Plan 14 게이트 baseline)
    # per_joint: CriteriaGap list
```

### dimensions.py frame-mean 와의 격리

| 차원 | dimensions.py (frame-mean) | moment_dimensions.py (moment-list) |
|---|---|---|
| sampling | hold_window (분산 최소 구간) 의 frame-mean | Gemini KeyMoment.frame_index 단일 |
| line tol | `_LINE_TOL_DEG = 20°` 박제 | `tolerance_full` 평균 (per criterion) |
| angle | reference 영상 필요 (kismam.overall_score) | criterion `angle_target` 갭 (reference 0) |
| 의미 | hold 구간 평균 자세 | IPSF 규정 시점 정확 매칭 |

두 path 격리 — dimensions.py 무수정. 운영 코드 진입은 Plan 14 통과 후 별 plan 책임.

### 단위 테스트 (20 PASS)

```bash
PYTHONPATH=backend/shared/python:. /Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python3 \
  -m pytest backend/tests/test_moment_dimensions.py -v
# 20 passed in 0.16s
```

| 클래스 | tests | 범위 |
|---|---|---|
| TestMeasureMomentAngles | 7 | 8 joints / subset / derive 거부 / frame 범위 / NaN / inf / shape |
| TestComputeCriteriaGap | 6 | perfect / within tol / beyond / minimum fail / dataclass / NaN |
| TestScoreMoment | 7 | all extension / minimum 누적 / empty / missing joint / non-180 / mixed / deduction |

---

## T-3 — `spike_gemini_moment.py` (CLI)

### CLI 인자 (11개)

| 인자 | default | 설명 |
|---|---|---|
| `--mode` | `report-only` | report-only / live |
| `--motion` | (required) | Plan 15 IPSF 라벨링 진입된 motion (ref-invert 1차 박제) |
| `--bucket` | `sunity-motion-pilot-videos` | S3 버킷 (live mode) |
| `--gemini-model` | `gemini-2.5-pro` | Gemini 모델 명 (live mode) |
| `--rtmpose-config` | None | RTMPose config (.py) (live mode 필수) |
| `--rtmpose-checkpoint` | None | RTMPose 가중치 (.pth) (live mode 필수) |
| `--motionbert-root` | `/workspace/MotionBERT` | MotionBERT 저장소 |
| `--motionbert-weights` | None | MotionBERT best_epoch.bin (live mode 필수) |
| `--score-threshold` | `0.3` | RTMPose keypoint 컷 |
| `--fps` | `9.0` | frame_index 후처리 (spike_rtmpose 와 동일) |
| `--out` | (auto) | `backend/research/spikes/reports/spike_gemini_moment_<UTC>.json` |

### report-only mode (로컬 OK)

stub angles (T=20, J=8) + stub KeyMoment (frame=10 hold) 으로 measure_moment_angles +
score_moment 흐름 검증. mmpose / torch / Gemini API 의존성 0.

```bash
PYTHONPATH=backend/shared/python:. python3 -m backend.research.spikes.spike_gemini_moment \
  --mode report-only \
  --motion ref-invert
```

- ref-invert (Plan 15 1차 박제, 5 hold entries) → 5 per_joint gap + line/angle 점수 산출.
- ref-climb (IPSF Climbs 카테고리 빈 list) → `Plan 15 IPSF 라벨링 미진입` RuntimeError.

### live mode (belle Pod 전용)

spike_rtmpose 헬퍼 lazy import 재사용 (spike_rtmpose 무수정). pipeline:

```
1. _resolve_video (S3 download)
2. _extract_frames (imageio, 9fps / 640px)
3. _run_rtmpose_2d → (T, 17, 3 pixel+score)
4. convert_rtmpose_coco17_to_h36m17 → (T, 17, 3 H36M)
5. _load_motionbert / _run_motionbert_inference → (T, 17, 3 xyz)
6. _h36m17_to_coco17_subset → (T, 17, 4 xyz+score)
7. features.compute_joint_angles → (T, 8) angles
8. temporal.temporal_fill → (T, 8) filled
9. GeminiMomentExtractor.extract_key_moments(video, motion) → list[KeyMoment]
10. assign_frame_indices(moments, fps, T)
11. for each KeyMoment:
    - measure_moment_angles(filled, frame_index, joint_keys)
    - score_moment(measured, criteria) → line/angle/minimum_failures
12. _evaluate_plan_14_gate → verdict
```

### Plan 14 게이트 verdict 4 분기

| verdict | 조건 | Plan 14 진입 |
|---|---|---|
| `plan_14_gate_pass` | minimum_failure 0 + line ≥ 60 + angle ≥ 60 | 진입 가능 → Plan 14 5영상 sweep PLAN 작성 |
| `minimum_requirement_fail` | minimum_failure ≥ 1 | 진입 보류 — measurement chain 또는 IPSF minimum 임계 재검토 |
| `below_target_score` | line < 60 또는 angle < 60 | 진입 보류 — Gemini 시점 정확도 또는 measurement chain 개선 |
| `no_criteria` | per_moment 빈 list | 부적합 — Plan 15 belle 라벨링 미진입 |

### 스모크 테스트 (15 PASS)

```bash
PYTHONPATH=backend/shared/python:. /Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python3 \
  -m pytest backend/tests/test_spike_gemini_moment_smoke.py -v
# 15 passed in 0.17s
```

| 클래스 | tests | 범위 |
|---|---|---|
| TestCli | 4 | mode default / motion required / model default / fps default |
| TestDefaultOutPath | 1 | reports/ 아래 경로 |
| TestEmptyCriteriaGuard | 2 | empty grouped RuntimeError / non-empty 통과 |
| TestPlan14Gate | 4 | no_criteria / full_pass / minimum_fail / below_target |
| TestReportOnlyMode | 2 | ref-invert e2e (JSON+MD sibling 박제) / ref-climb 빈 list |
| TestLiveModeGuards | 2 | rtmpose-config 누락 / motionbert-weights 누락 |

`TestReportOnlyMode.test_runs_when_labeled` 가 ref-invert YAML 디스크 fixture 로 e2e 검증 — Plan 15
1차 박제 5 entries → 5 per_joint gap + line/angle 점수 산출 + JSON+MD sibling 실제 생성 확인.

---

## T-4 — README append-only (Plan 13 섹션)

`backend/research/spikes/README.md` 끝에 Plan 13 섹션 append:
- 목적 (Plan 12 dominant (a) 해결 path).
- 라이선스 — google-generativeai Apache 2.0 + Gemini API 약관.
- Plan 13 추가 파일 5개 + 테스트 3개 박제.
- report-only mode 로컬 실행 예시.
- live mode belle Pod 5단계 절차 (pull / API 키 export / SDK install / spike 실행 / 결과 공유).
- Plan 14 진입 게이트 verdict 4 매트릭스.
- 주의사항 8항목 (Parameter Store / 8 joint 한정 / empty criteria / 사람 점수 0건 등).

`git diff` 검증 — 148 insertions, 0 deletions. Plan 07/08/10/11/12 섹션 18개 `#` heading 모두 보존
확인.

---

## T-5 — 본 SUMMARY (status `pending_belle_live`)

### 박제 내용

1. T-1~T-4 박제 + T-6 placeholder.
2. 5가설 verdict 매핑 (Plan 12 → Plan 13).
3. 모든 critical landmines 가드 확인 (frontmatter + 본문).
4. Plan 14 진입 게이트 정의 (minimum_failure 0 + line/angle ≥ 60).

### Status 변경 흐름

```
T-1~T-5 executor 완료 → status `pending_belle_live`
  → belle Pod ref-invert 단독 live mode (~3분)
  → 결과 적재 (Claude 공유 .json + .md)
  → 본 SUMMARY frontmatter status `belle_live_passed` 또는 `belle_live_blocked` 갱신
  → Plan 14 PLAN 작성 진입 게이트
```

---

## T-6 — belle Pod live mode (autonomous: false, pending)

**현재 status = `pending_belle_live`**.

### belle 실행 절차 (ref-invert 단독 시범)

```bash
# 1. 코드 최신화
cd /workspace/SunityMotion
git pull --ff-only origin main

# 2. Gemini API 키 주입 (Parameter Store SecureString)
export GEMINI_API_KEY=$(aws ssm get-parameter \
  --name /sunity/motion/gemini-api-key \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text \
  --region ap-northeast-2)

# 3. google-generativeai 설치 (1회)
pip install google-generativeai

# 4. spike 실행 (ref-invert 단독, ~3분)
python3 -m backend.research.spikes.spike_gemini_moment \
  --mode live \
  --motion ref-invert \
  --bucket sunity-motion-pilot-videos \
  --gemini-model gemini-2.5-pro \
  --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \
  --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \
  --motionbert-root /workspace/MotionBERT \
  --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \
  --score-threshold 0.3 \
  --out backend/research/spikes/reports/spike_gemini_moment_live_$(date +%Y%m%d_%H%M).json
```

### 적재 형식

결과 `.json` + `.md` 둘 다 Claude 에 공유. 본 SUMMARY 갱신:

- frontmatter `tags` 에 verdict 추가 (`belle_live_passed` / `belle_live_blocked_minimum` /
  `belle_live_blocked_below_target` / `belle_live_blocked_other`).
- frontmatter `metrics.completed_date` 갱신.
- `## belle Pod live mode 결과` 섹션 신설 (이 SUMMARY 본문 끝에 append):
  - per-moment line/angle 점수 표.
  - per-joint gap 상세 (5 entries, ref-invert 1차 박제).
  - Plan 14 진입 verdict.
  - Gemini 응답 raw excerpt (좌표/점수/판단 0건 확인).

### Plan 14 진입 게이트

| 결과 | 다음 행동 |
|---|---|
| `plan_14_gate_pass` | Plan 14 PLAN 작성 진입 (5영상 sweep) — 단, Plan 15 4영상 belle 라벨링 (T-5) 가 선행되어야 함 |
| `minimum_requirement_fail` | belle Pod 결과 + Plan 15 minimum_requirement 임계 belle 재검토 (현재 160°, IPSF 기본). 후속 spike 또는 임계 조정 검토. |
| `below_target_score` | Gemini 시점 정확도 + measurement chain (RTMPose+MB) 정확도 분석. 후속 spike (multi-frame averaging / 시점 보정) 검토. |
| `belle_live_blocked_other` | Gemini API 응답 거부 / 정규식 가드 차단 등. raw 응답 확인 후 가드 조정 또는 belle 재발급. |

---

## 핵심 결정 박제 (frontmatter decisions 중복, 본문 명시)

### 1. dimensions.py frame-mean 격리

운영 dimensions.py / kismam.py / features.py / temporal.py 0줄 수정. 본 plan 은 별도 모듈
`sunity_shared.judging.moment_dimensions` 에 moment-list sampling 도입. 운영 코드 진입은 Plan 14
통과 후 별 plan 책임.

이유: Plan 13 single shot 으로 운영 코드 변경 시 회귀 위험 + Plan 14 5영상 sweep 통과 전 fix 코드
박제 부적합. dimensions.py 의 `hold_window` (분산 최소 구간) frame-mean path 는 reference DTW
모드3 등 다른 경로에서 계속 사용됨.

### 2. 8 angle joints 한정

`measure_moment_angles` 가 8 외 joint 요청 시 ValueError. derive joint (hip / spine / thorax /
neck_nose / head) 사용 시 Plan 12 (d) keypoint mapping 차이 (RTMPose H36M ordering vs NLF COCO
ordering 17/17 다름) 가 점수에 영향. 본 plan 우회 = 8 angle joints 만 사용 (skeleton.JOINT_KEYS
= left/right × elbow/shoulder/hip/knee).

### 3. NLF 호출 0

Plan 12 (c) verdict NLF baseline 편차 strong (span 23, var 60.56) → NLF 갭 baseline 영구 폐기
(Plan 15 commit 박제). 본 plan live mode 는 RTMPose+MB 단일 lift 사용. NLF 비교군 0.

### 4. Gemini 역할 박제

시점 분류 + 자연어 번역만. 좌표 / 점수 / 심사 판단 출력 영구 금지. 3 카테고리 정규식 가드가 1차
차단선 — 위반 시 ValueError + 어느 카테고리 + 매치된 패턴 박제.

### 5. API 키 = Parameter Store

`/sunity/motion/gemini-api-key` (SecureString, STATE.md 2026-06-01 박제) 우선. env
`GEMINI_API_KEY` fallback (Pod / 로컬 dev). `.env` 하드코딩 영구 금지 (CLAUDE.md §3).

### 6. moment_key enum 통일

VALID_MOMENT_KEYS (`setup`, `hold`, `peak`, `release`) — Plan 15 GeometricCriterion 과 동일.
KeyMoment.validate() + Gemini 응답 파싱 가드 + measure_moment_angles 입력 가드 3중 차단.

### 7. empty criteria 가드

ref-climb 의도된 빈 list (IPSF Climbs 카테고리 = 각도 임계 X) 같은 motion 입력 시 RuntimeError.
silent skip 금지 — Plan 15 belle 라벨링 완료 motion 만 본 spike 입력 가능.

### 8. Plan 14 진입 게이트

기존 NLF 갭 baseline (D-14 ≤5) 영구 폐기. 신규 게이트 = `minimum_failure 0 건 + line/angle 점수
≥ 60`. IPSF angle_target ± tolerance_full 갭 단일 기준.

---

## Deviations from Plan

### 1. Gemini SDK 라이선스 추가 박제 (README Plan 13 섹션)

PLAN T-4 명세는 "라이선스 (Gemini API)" 만 명시. 실 구현은 google-generativeai (Python SDK)
Apache 2.0 + Gemini API 약관 둘 다 박제. README 라이선스 표 2 줄로 명확화.

### 2. report-only mode test 가 디스크 fixture 의존

PLAN T-3 명세는 "report-only e2e + stub guard + empty criteria 가드". 실 구현은
`TestReportOnlyMode.test_runs_when_labeled` 가 디스크의 `backend/judging_data/criteria/ref-invert.yaml`
(Plan 15 1차 박제) 을 직접 fixture 로 사용 → 5 entries 정확성까지 검증. Plan 15 ref-invert 박제가
회귀하면 본 테스트가 fail-loud 로 잡음.

`test_ref_climb_empty_criteria_raises` 도 디스크 ref-climb 빈 템플릿 직접 사용 → Plan 15 의도된
빈 list 정합 회귀 방지.

### 3. CLI 인자 11개 (PLAN 명세 10개 → 실 11개)

PLAN T-3 명세는 10개 인자. 실 구현은 11개 — `--fps` 추가 (default 9.0, spike_rtmpose frame
extractor 와 동일). `assign_frame_indices` 가 fps 인자 필요 → CLI 노출이 명시적이라 디버그 편의.

### 4. score_moment 의 line 차원 — angle_target == 180° 한정

PLAN T-2 명세는 "line·angle score" 만 명시. 실 구현은 line 차원 = `angle_target == 180.0` entry
만 (IPSF Fully Extended Criteria). 다른 angle_target (예: 90°) 은 line 에 기여하지 않고 angle
차원에만 반영. dimensions.py `line_score` 의 `_FULL_EXTENSION_DEG = 180.0` 패턴과 일관성.

`TestScoreMoment.test_non_180_target_not_in_line` + `test_mixed_180_and_other_target` 가 회귀 방지.

---

## Known Stubs

없음. 본 plan 의 spike 스크립트는 belle Pod 에서 즉시 실행 가능한 완전한 구현. report-only mode
는 stub angles + stub KeyMoment 이지만 이는 "stub 데이터로 코드 path 검증" 의도 — Plan 13 spike
인프라 자체의 stub 아님. live mode 실 호출 시 실 Gemini 응답 + 실 RTMPose+MB 측정값 사용.

---

## Threat Flags

없음 — 신규 네트워크 엔드포인트 (외부 Gemini API 호출은 spike 한정, 운영 코드 진입 0) + auth
path (Gemini API 키는 Parameter Store SecureString + IAM 권한 + env fallback 안전 path) + Firestore
스키마 변경 없음 + S3 버킷 변경 없음.

Gemini API 가 외부 서비스라는 점은 후속 plan (운영 코드 진입 시) 평가 대상이지만 본 plan 은
spike 한정.

---

## Self-Check

**파일 존재 확인** (executor 작성):

- `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` FOUND
- `backend/shared/python/sunity_shared/judging/moment_dimensions.py` FOUND
- `backend/research/spikes/spike_gemini_moment.py` FOUND
- `backend/tests/test_gemini_moment_extractor.py` FOUND
- `backend/tests/test_moment_dimensions.py` FOUND
- `backend/tests/test_spike_gemini_moment_smoke.py` FOUND
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-PLAN.md` FOUND
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-SUMMARY.md` FOUND (이 파일)
- `backend/shared/python/sunity_shared/judging/__init__.py` MODIFIED (append-only)
- `backend/research/spikes/README.md` MODIFIED (append-only)

**운영 코드 무수정 확인** (git diff HEAD~5 = empty):

- `backend/functions/pipeline/app.py` UNCHANGED
- `backend/functions/upload-url/app.py` UNCHANGED
- `backend/functions/reference-api/app.py` UNCHANGED
- `backend/runpod_inference/server.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/dimensions.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/technique.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/features.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/temporal.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/pose_estimator.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/pose_lifters/` UNCHANGED

**기존 spike 무수정 확인**:

- `backend/research/spikes/spike_rtmpose.py` UNCHANGED (Plan 10 본체)
- `backend/research/spikes/sweep_rtmpose.py` UNCHANGED (Plan 11 본체)
- `backend/research/spikes/debug_dimensions.py` UNCHANGED (Plan 11)
- `backend/research/spikes/debug_gap_root_cause.py` UNCHANGED (Plan 12)
- `backend/research/spikes/rtmpose_to_h36m17.py` UNCHANGED (Plan 10 adapter)
- `backend/research/spikes/mediapipe_to_h36m17.py` UNCHANGED (Plan 07/08 adapter)
- `backend/research/spikes/spike_motionbert.py` UNCHANGED (Plan 07/08 본체)

**Plan 15 데이터 무수정 확인**:

- `backend/shared/python/sunity_shared/judging/geometric_criterion.py` UNCHANGED
- `backend/shared/python/sunity_shared/judging/loader.py` UNCHANGED
- `backend/judging_data/criteria/ref-*.yaml` 5 파일 모두 UNCHANGED
- `backend/judging_data/README.md` UNCHANGED

**테스트 결과 확인**:

- `test_gemini_moment_extractor.py`: **52 PASS** (mmpose / torch / google.generativeai / boto3 미import, 0.05s)
- `test_moment_dimensions.py`: **20 PASS** (numpy 만 의존, 0.16s)
- `test_spike_gemini_moment_smoke.py`: **15 PASS** (mmpose 미import, 0.17s)
- 합계 **87 PASS** (0.17s 실행 시간 within 1 batch)
- 기존 backend 테스트 회귀 없음 (Plan 15 23 + 본 plan 87 = 110 PASS, ref-invert 라벨링 회귀 0건).

**critical landmines 가드 확인** (frontmatter decisions 와 본문 §1~§8 모두 박제):

- (1) dimensions.py frame-mean 격리 — 무수정 박제 ✓
- (2) 8 angle joints 한정 — measure_moment_angles ValueError 박제 ✓
- (3) NLF 호출 0 — live mode RTMPose+MB 단일 lift ✓
- (4) Gemini 좌표/점수/판단 정규식 차단 — 3 카테고리 박제 ✓
- (5) API 키 = Parameter Store SecureString — env fallback 박제 ✓
- (6) moment_key enum 통일 — VALID_MOMENT_KEYS 3중 가드 ✓
- (7) empty criteria 가드 — RuntimeError 박제 ✓
- (8) Plan 14 진입 게이트 — minimum_failure 0 + line/angle ≥ 60 박제 ✓

**이모지 확인**: 0건 (코드 + 테스트 + 문서 모두).
**사람 점수 라벨링 확인**: 0건 (Gemini 응답 정규식 차단 + score_moment 점수 = `kismam.score_from_deviation` 객관 매핑).

---

## Verdict 요약 — orchestrator 에게

- **verdict**: `measurement_unreliable_blocked`
- **one-liner**: T-1~T-5 executor 인프라 통과 + T-6 belle Pod live mode (ref-invert 단독, 2026-06-01) 실행 완료.
  Gemini File API ACTIVE 대기 / 새 AI Studio AQ. 키 포맷 SDK 마이그레이션 / _run_rtmpose_2d kwargs / temporal/features
  import 4 fix 박제 후 pipeline 진입 성공. **결과 = 5/5 minimum fail + 측정값 자체 의심.** 정은지
  invert split peak hold 에서 right_shoulder 18.2° 같은 인체학적 비정상 값 + Plan 08 MP+MB 92 vs
  Plan 11 RTMPose+MB 70 vs Plan 13 단일 frame 5/5 fail 의 cross-engine inconsistency. Plan 12 (e)
  verdict ("두 엔진 3D 분포 strong, distance 220+") 와 직접 연결. **Plan 14 진입 차단 — Plan 16
  신설 (측정 신뢰도 root cause trace + 다른 기술 도입 검토).**
- **commits (executor + fix)**: 11 (PLAN / T-1 / T-2 / T-3 / T-4 / SUMMARY / STATE+ROADMAP / 4 SDK fix).
- **next action**: Plan 16 PLAN 작성 진입 (`/gsd:plan-phase 1 --plan 16`). Plan 14 5영상 sweep 은
  Plan 16 통과 후 진입 (Wave 3 gate chain 갱신).

---

## belle Pod live mode 결과 (2026-06-01, ref-invert 단독)

**실행 보고서**: `spike_gemini_moment_live_20260601_0927.json` + `.md` (belle 공유).

### Plan 14 진입 게이트 (spike 자동 분기)

- **verdict 표면**: `minimum_requirement_fail` (5/5 minimum 미달)
- **본 SUMMARY 박제 verdict**: `measurement_unreliable_blocked` (측정 신뢰도 의심으로 인한
  표면 verdict 무효화 — Plan 14 진입 불가)

| 항목 | 값 | 임계 | 통과 |
|---|---|---|---|
| minimum 미달 entry | 5 | ≤ 0 | False |
| line 차원 (hold) | 0 | ≥ 60 | False |
| angle 차원 (hold) | 0 | ≥ 60 | False |

### per-joint gap (hold moment, frame_idx=88)

| joint | measured | target | gap | beyond_tol | deduction | minimum_met | score |
|---|---|---|---|---|---|---|---|
| left_shoulder | 88.2° | 180° | 91.8° | 71.8° | 14.36 | False | 0 |
| right_shoulder | **18.2°** | 180° | **161.8°** | **141.8°** | **28.37** | False | 0 |
| left_hip | 54.9° | 180° | 125.1° | 105.1° | 21.01 | False | 0 |
| right_hip | 115.5° | 180° | 64.5° | 44.5° | 8.90 | False | 1 |
| right_knee | 73.0° | 180° | 107.0° | 87.0° | 17.40 | False | 0 |

### Measurement unreliability 박제 (3 증거)

1. **인체학적 비정상**: right_shoulder 18.2° = 손을 옆구리에 거의 붙인 자세에서만 나오는 값. invert
   split 자세 (어깨가 폴을 잡고 매달림) 에서는 80~180° 가 정상. 정은지 = 폴스포츠 세계챔피언이므로
   IPSF minimum (160°) 못 가는 자세 불가능.

2. **좌우 비대칭 폭주**: left_shoulder 88 vs right_shoulder 18 (Δ=70°), left_hip 55 vs right_hip 116
   (Δ=61°). 정은지 invert split 은 IPSF Code of Points 상 좌우 대칭이 정합 — 한쪽 occlusion 또는
   lifter 좌우 매핑 헷갈림 의심.

3. **Cross-engine inconsistency**: 동일 ref-invert 영상에서
   - Plan 08 (MP+MB) frame-mean → overall **92** (정은지 수준)
   - Plan 11 (RTMPose+MB) frame-mean → overall 70 (Plan 11 sweep)
   - **Plan 13 (RTMPose+MB) hold frame 88 → 5/5 minimum fail** (단일 frame sampling)
   Plan 12 (e) verdict ("두 엔진 3D 분포 strong, distance 220+") 와 직접 일치 — RTMPose+MB lift
   신뢰도 약점이 단일 frame 에서 폭주.

### 측정 신뢰도 root cause 가설 (4)

| # | 가설 | 디버그 path |
|---|---|---|
| **a** | Gemini 가 hold frame_idx=88 을 정점 아닌 transition 으로 분류 | 동일 영상 다른 frame (peak / setup / release) 의 측정값 비교 |
| **b** | RTMPose+MB lift 가 단일 frame 좌우 noise 폭주 (Plan 12 (e) 직접 연결) | hold_window (88±5) 평균 또는 좌우 평균 산출 |
| **c** | lifter 가 occlusion 자세 (거꾸로 매달림) 에서 좌우 keypoint 헷갈림 | raw 2D keypoint visualization (frame 88) + Plan 08 MP+MB lift 결과와 비교 |
| **d** | RTMPose+MB 단일 lift path 자체가 invert family 부적합 — multi-engine averaging 필요 | Plan 12 (e) 후속 spike — MP+MB / RTMPose+MB / NLF 3 lift voting 또는 ensemble |

### 각도 컨벤션 검증 결과 (NOT root cause)

- `compute_joint_angles` (`backend/shared/python/sunity_shared/analysis/features.py:36`) = `arccos(dot(ba, bc) / (|ba|·|bc|))`
- → **inner joint angle**, range [0°, 180°], 180° = 두 segment 가 일직선 = 완전 신전
- IPSF Code of Points Fully Extended Criteria target=180° (tolerance ±20°, minimum 160°) 정의와 **컨벤션 일치**
- → **각도 컨벤션 미스매치 아님**. 측정값 자체가 root cause.

### 사람 점수 라벨링 / Gemini 좌표·점수·판단 출력 확인

- 사람 점수 라벨링: 0건 (메모리 박제 `analysis-objectivity-no-human-scores` 준수).
- Gemini 응답 raw excerpt: 좌표 / 점수 / 심사 판단 키워드 0건 (정규식 가드 미발동 = 응답이 정책 준수).

### Plan 14 진입 차단 + Plan 16 신설 박제

belle 결정 (2026-06-01, "분석 정확도 최우선 + 갭/line/angle 동등 게이트 무조건" memory 박제 일관) —
표면 verdict `minimum_requirement_fail` 박제하되 root cause = 측정 신뢰도 약점. Plan 14 5영상 sweep
진입은 Plan 16 (측정 신뢰도 spike) 통과 후로 chain 갱신.

memory `feedback-analysis-first.md` + `gap-and-line-angle-mandatory-gates.md` 박제 일관 — "다른 기술
반영해서라도 잡아야 한다". Plan 16 spike scope = path A (frame-by-frame trace) 우선 + path B
(multi-engine averaging) / path C (multi-view 조기 도입) / path D (Gemini 직접 EXTEND/BENT 분류
SCORE-01 정식 path 조기 진입) 옵션 박제. belle Plan 16 PLAN 작성 시 path 결정.

---

## SDK 마이그레이션 + bugfix 박제 (T-6 실행 차단 4건 해소)

belle Pod live mode 진입 전 4건 차단 해소 — executor smoke 테스트가 live mode 함수 시그너처
미검증으로 발생. 모든 fix smoke 87 PASS 유지 (regression 0).

| # | commit | 차단 사유 | 해결 |
|---|---|---|---|
| 1 | `56b5577` | `joint_uncertainty` 를 `temporal` 에서 import 시도 (실제 `features` 모듈) | 한 줄 분리 import |
| 2 | `5d867a8` | `_run_rtmpose_2d` 에 `config_path`/`checkpoint_path`/`score_threshold` kwargs hallucinate (실제 positional `frames, rtmpose_config, rtmpose_checkpoint`) | positional 호출로 수정 |
| 3 | `569a076` | legacy `google-generativeai` 0.8.x 가 새 AI Studio AQ. 키 포맷 미지원 (2025-말 갱신) → 401 ACCESS_TOKEN_TYPE_UNSUPPORTED | 신 `google-genai` SDK 마이그레이션 (Client + files.upload + models.generate_content) |
| 4 | `9f011d2` | Gemini File API 가 upload 후 PROCESSING 상태에서 즉시 generate_content 시 FAILED_PRECONDITION | `client.files.get(name=...)` polling (2s 간격, max 120s) |

**Plan 16 PLAN 박제 권장 사항**:
- live mode 함수 시그너처 smoke 추가 (현 smoke 가 mock 만 검증해서 4건 모두 belle Pod 에서 처음 발견)
- 또는 live mode 자체를 별 통합 테스트로 분리 (단위 mock 과 격리)
