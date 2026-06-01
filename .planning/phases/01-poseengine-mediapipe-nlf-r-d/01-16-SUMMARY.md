---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "16"
status: pending_belle_live   # T-1~T-5 executor 완료, T-6 belle Pod live mode 대기
subsystem: ml-pose-engine
type: spike
tags:
  - spike
  - measurement-reliability
  - frame-trace
  - cross-engine-trace
  - lr-asymmetry
  - lr-swap-detection
  - pose-01
  - plan-13-followup-path-a
  - rtmpose-mb
  - mediapipe-mb
  - no-nlf
  - single-camera
  - no-human-scoring
  - pending_belle_live

dependency_graph:
  requires:
    - 01-08  # MP+MB 5영상 baseline — ref-invert frame-mean 92 비교군
    - 01-11  # RTMPose+MB 5영상 sweep — ref-invert frame-mean 70 비교군
    - 01-12  # 5가설 verdict — (e) 두 엔진 3D 분포 strong distance 220+ 직접 연결
    - 01-13  # verdict measurement_unreliable_blocked — frame 88 단일 5/5 fail + 4 가설 trace 요청
  provides:
    - "backend/research/spikes/spike_measurement_trace.py — 4 가설 (a/b/c/d) frame-by-frame trace + cross-engine 재현 + verdict 6 분기"
    - "trace_angles_per_frame / compute_lr_asymmetry / compute_hold_window_lr — 단일 frame vs hold_window 평균 비교 + 좌우 비대칭"
    - "compute_cross_engine_disagreement / detect_lr_swap — RTMPose+MB vs MP+MB 두 path 비교"
    - "aggregate_verdicts — 4 가설 + dominant + next_path_recommendation (추가 view 옵션 0건 박제)"
    - "assert_live_helper_signatures — Plan 13 belle Pod 발견 차단 (mmpose 없이 ast 정합 점검)"
  affects:
    - 01-14  # 5영상 재검증 sweep — 본 plan + 후속 plan path 결과 후 진입
    - "후속 plan 후보 — path B multi-engine averaging / path D Gemini 직접 EXTEND/BENT / combined"

tech_stack:
  added: []  # 신규 라이브러리 없음 — Plan 08/10/13 setup 그대로 사용
  patterns:
    - "report-only mode (numpy-only) + live mode (lazy import mmpose/torch/mediapipe) — Plan 12/13 spike 패턴 동일"
    - "live helper signature ast 정합 가드 — Plan 13 belle Pod 발견 차단 (joint_uncertainty import / _run_rtmpose_2d kwargs / SDK 시그너처)"
    - "JSON + sibling Markdown (9 섹션) — Plan 13 spike 패턴 동일"
    - "verdict 임계 모듈 상수 (strong / weak / rejected / inconclusive 4 단계) — Plan 12 debug_gap_root_cause 패턴"
    - "4 LR pair tuple + skeleton.JOINT_KEYS 정합 module-load assertion — fail-loud"

key_files:
  created:
    - backend/research/spikes/spike_measurement_trace.py
    - backend/tests/test_spike_measurement_trace.py
    - backend/tests/test_spike_measurement_trace_smoke.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-16-PLAN.md
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-16-SUMMARY.md
  modified:
    - backend/research/spikes/README.md   # append-only — Plan 16 섹션 추가 (Plan 07/08/10/11/12/13 보존)

requirements_completed: []
# POSE-01 — 본 plan = 측정 신뢰도 trace + 4 가설 verdict + 후속 plan path 권고 박제만.
# 충족은 후속 plan (path B / path D / combined) 통과 + Plan 14 5영상 sweep 통과 후.

metrics:
  duration: "~45 min executor (T-1~T-5 + 42 unit/smoke 테스트 + README + SUMMARY placeholder)"
  completed_date: "2026-06-01 executor 완료 — T-6 belle Pod live mode 대기"
  tasks_completed: 5
  tasks_total: 6
  files_created: 5
  files_modified: 1
---

# Phase 01 Plan 16: Measurement reliability frame-by-frame trace spike

**Plan 13 verdict `measurement_unreliable_blocked` 후속 path A — ref-invert 단독 4 가설
(a) Gemini frame_idx / (b) RTMPose+MB 좌우 noise / (c) lifter occlusion swap /
(d) cross-engine 부적합 의 frame-by-frame trace + cross-engine 재현 spike. T-1~T-5
executor 박제 완료, T-6 belle Pod live mode 대기 (~5분).**

---

## TL;DR

| 항목                                  | 값                                                          |
|---------------------------------------|-------------------------------------------------------------|
| verdict                               | `pending_belle_live` (T-6 belle Pod live mode 대기)         |
| scope                                 | path A (frame-by-frame trace + cross-engine 재현) 우선      |
| 신규 spike                            | 1 (spike_measurement_trace.py)                              |
| 신규 단위/스모크 테스트                | 42 PASS (30 unit + 12 smoke, 0.16s 실행)                    |
| 신규 모듈 상수                         | 14 (4 가설 strong/weak 임계 + Plan 13 박제 + engine tag)    |
| 신규 함수 (모듈 9개)                  | trace_angles_per_frame / compute_lr_asymmetry / compute_hold_window_lr / compute_cross_engine_disagreement / detect_lr_swap / verdict_hypothesis / aggregate_verdicts / generate_markdown / assert_live_helper_signatures |
| 운영 코드 수정                         | 0 줄 (functions / runpod_inference / shared/analysis / shared/judging) |
| Plan 13 모듈 수정                     | 0 줄 (gemini_moment_extractor / moment_dimensions)          |
| Plan 15 데이터 수정                   | 0 줄 (geometric_criterion / loader / 5영상 YAML)            |
| 기존 spike 수정                       | 0 줄 (spike_rtmpose / sweep_rtmpose / debug_dimensions / debug_gap_root_cause / spike_motionbert / rtmpose_to_h36m17 / mediapipe_to_h36m17 / spike_gemini_moment) |
| NLF 호출                              | 0 (Plan 12 (c) verdict 영구 폐기)                            |
| multi-view 옵션 / 다각도 키워드        | 0 건 (memory `single-camera-first-multi-view-last.md` 박제) |
| 사람 점수 라벨링 / Gemini 호출        | 0 건 (memory `analysis-objectivity-no-human-scores.md`)     |
| 이모지                                | 0 건 (CLAUDE.md §7)                                          |

---

## Plan 13 verdict 인용 (본 plan trace 책임)

ref-invert hold frame 88 단일 frame 측정 표 (Plan 13 SUMMARY 박제):

| joint           | measured | target | gap   | minimum_met |
|-----------------|----------|--------|-------|-------------|
| left_shoulder   | 88.2도   | 180도   | 91.8도 | False       |
| right_shoulder  | **18.2도** | 180도   | **161.8도** | False |
| left_hip        | 54.9도   | 180도   | 125.1도 | False       |
| right_hip       | 115.5도  | 180도   | 64.5도 | False       |
| right_knee      | 73.0도   | 180도   | 107.0도 | False       |

Cross-engine inconsistency (동일 ref-invert 영상):

| measure  | Plan 08 (MP+MB) | Plan 11 (RTMPose+MB) | Plan 13 (RTMPose+MB) |
|----------|-----------------|----------------------|----------------------|
| sampling | frame-mean      | frame-mean           | hold frame 88 단일   |
| overall  | **92**          | 70                   | 5/5 minimum fail     |

각도 컨벤션 (compute_joint_angles inner angle 0-180도, 180도 = 완전 신전) IPSF target
일치 확인됨 — **측정값 자체가 root cause**.

---

## 4 가설 매트릭스 (본 plan trace + T-6 결과 대기)

| #   | 가설                                                | 임계 (strong / weak)  | 측정 path                                                  | T-6 결과     |
|-----|-----------------------------------------------------|-----------------------|------------------------------------------------------------|--------------|
| (a) | Gemini frame_idx=88 정확도 (hold 정점 아닌 transition) | ≥30도 / ≥10도          | RTMPose+MB frame 88 단일 vs hold_window (88±5) 평균        | (대기)       |
| (b) | RTMPose+MB 단일 lift 좌우 noise 폭주                  | ≥40도 / ≥15도          | RTMPose+MB 영상 평균 4 pair |L - R|                         | (대기)       |
| (c) | lifter occlusion 좌우 keypoint 매핑 swap              | ≥30% / ≥10%            | RTMPose+MB vs MP+MB 두 path 부호 반대 frame 비율           | (대기)       |
| (d) | RTMPose+MB vs MP+MB cross-engine 부적합               | ≥30도 / ≥10도          | RTMPose+MB vs MP+MB frame-by-frame 평균 disagreement       | (대기)       |

dominant 가설별 후속 plan path 권고는 spike `next_path_recommendation` 6 분기 산출
(추가 view 옵션 0건 박제 — memory `single-camera-first-multi-view-last.md`).

---

## 모듈 구조 박제

신규 모듈 `backend/research/spikes/spike_measurement_trace.py` (770줄):

함수 9개:

1. `trace_angles_per_frame(angles_tj, frame_index, hold_window) -> dict` — 가설 (a)
2. `compute_lr_asymmetry(angles_tj) -> dict` — 가설 (b)
3. `compute_hold_window_lr(angles_tj, frame_index, hold_window) -> dict` — (a)+(b) 결합
4. `compute_cross_engine_disagreement(rtmpose, mp) -> dict` — 가설 (d)
5. `detect_lr_swap(rtmpose, mp, lr_pairs) -> dict` — 가설 (c)
6. `verdict_hypothesis(value, strong, weak) -> str` — utility (4 단계)
7. `aggregate_verdicts(trace_a, b, c, d) -> dict` — dominant + next_path_recommendation
8. `generate_markdown(trace_result) -> str` — 9 섹션 sibling .md
9. `assert_live_helper_signatures() -> dict` — Plan 13 belle Pod 발견 차단 (ast 정합)

모듈 상수 14개 (rationale 주석 박제):

- `HYPOTHESIS_A_FRAME_VS_WINDOW_STRONG_DEG = 30.0` / `HYPOTHESIS_A_WEAK_DEG = 10.0`
- `HYPOTHESIS_B_LR_ASYMMETRY_STRONG_DEG = 40.0` / `HYPOTHESIS_B_WEAK_DEG = 15.0`
- `HYPOTHESIS_C_LR_SWAP_FRAME_RATIO_STRONG = 0.30` / `HYPOTHESIS_C_WEAK_RATIO = 0.10`
- `HYPOTHESIS_D_CROSS_ENGINE_DISAGREEMENT_STRONG_DEG = 30.0` / `HYPOTHESIS_D_WEAK_DEG = 10.0`
- `PLAN_13_FRAME_INDEX = 88` / `PLAN_13_HOLD_WINDOW = 5`
- `PLAN_08_MP_MB_REF_INVERT_OVERALL = 92.0` / `PLAN_11_RTMPOSE_MB_REF_INVERT_OVERALL = 70.0`
- `DEFAULT_MOTION = "ref-invert"`
- `ENGINE_RTMPOSE_MB` / `ENGINE_MEDIAPIPE_MB`

LR_PAIRS = 4 tuple ((left_elbow, right_elbow), (left_shoulder, right_shoulder),
(left_hip, right_hip), (left_knee, right_knee)) — skeleton.JOINT_KEYS 8 joint 와
module-load assertion.

---

## 단위/스모크 테스트 (42 PASS, 0.16s)

| 파일                                                        | 클래스 수 | tests | 비고                                  |
|-------------------------------------------------------------|-----------|-------|---------------------------------------|
| `backend/tests/test_spike_measurement_trace.py`             | 7         | 30    | T-2/T-3 — numpy-only                  |
| `backend/tests/test_spike_measurement_trace_smoke.py`       | 5         | 12    | T-4 — mmpose/torch/mediapipe 미import |

테스트 클래스:

- `TestTraceAnglesPerFrame` (5) — 가설 (a) helper
- `TestComputeLrAsymmetry` (4) — 가설 (b) helper
- `TestComputeHoldWindowLr` (3) — (a)+(b) 결합
- `TestComputeCrossEngineDisagreement` (4) — 가설 (d) helper
- `TestDetectLrSwap` (4) — 가설 (c) helper
- `TestVerdictHypothesis` (4) — 4 단계 분기
- `TestAggregateVerdicts` (6) — 6 분기 + 추가 view 옵션 키워드 0건 assertion
- `TestCli` (4) — argparse defaults
- `TestDefaultOutPath` (1) — UTC ISO 8601 박제
- `TestReportOnlyMode` (2) — JSON top-level 9 keys + sibling .md 9 섹션
- `TestVerdictBranches` (3) — dominant a/b/모두 rejected
- `TestLiveModeGuards` (1) — rtmpose-config 누락 ValueError
- `TestLiveHelperSignatures` (1) — Plan 13 belle Pod 발견 차단 (ast 정합)

---

## T-6 belle Pod live mode 실행 절차 (5단계)

1. 코드 최신화:
   ```
   cd /workspace/SunityMotion && git pull --ff-only origin main
   ```

2. 환경 확인 (Pod 환경 보존 — STATE.md 2026-06-01 박제):
   ```
   python3 -c "import torch; import mmpose; import mediapipe; print(torch.__version__, mmpose.__version__, mediapipe.__version__)"
   ```
   기대값: torch 2.4.1+cu124 / mmpose 1.3.2 / mediapipe 0.10.x. 정합 안 맞으면 STOP.

3. spike 실행 (ref-invert 단독, ~5분):
   ```
   python3 -m backend.research.spikes.spike_measurement_trace \
     --mode live --motion ref-invert --frame-index 88 --hold-window 5 \
     --bucket sunity-motion-pilot-videos \
     --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \
     --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \
     --motionbert-root /workspace/MotionBERT \
     --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \
     --out backend/research/spikes/reports/spike_measurement_trace_live_$(date +%Y%m%d_%H%M).json
   ```

4. 결과 파일 확인:
   - `.json` + `.md` 둘 다 존재.
   - JSON top-level keys 9개 (`generated_at` / `mode` / `motion` / `frame_index` /
     `hold_window` / `engines` / `cross_engine` / `verdicts` / `baseline_inconsistency`).
   - 4 가설 verdict 모두 strong / weak / rejected / inconclusive 중 1 산출.
   - `next_path_recommendation` 6 분기 중 1 산출.
   - 추가 view 옵션 관련 키워드 0건 (memory filename 인용 라인만 허용).

5. 결과 Claude 공유 → SUMMARY 갱신:
   - frontmatter status `pending_belle_live` → `belle_live_complete` (dominant tag 추가).
   - 본문 `belle Pod live mode 결과` 섹션 신설 — verdict 표 + dominant +
     next_path_recommendation + Plan 14 진입 결정 박제.

---

## belle 응답 옵션 (T-6 결과 후, 6 분기)

| dominant       | 응답 옵션                                                 | 후속 plan path                                    |
|----------------|----------------------------------------------------------|----------------------------------------------------|
| (a) 단독       | "Plan 17 path D 조기 진입" 또는 "Plan 17 path B-light"   | Gemini frame 정확도 개선 또는 window 평균 채택    |
| (b) 단독       | "Plan 17 path B 진입"                                    | multi-engine averaging (MP+MB / RTMPose+MB 평균)  |
| (c) 단독       | "좌우 매핑 sanity check + path B 검토"                   | RTMPose+MB lift 좌우 sign correction 또는 MP+MB 단독 |
| (d) 단독       | "Plan 17 path B 진입 강제"                               | multi-engine averaging 필수 (Plan 12 (e) 일치)     |
| (a)+(b) combined | "Plan 17 path B + path D combined"                    | 단일 frame + 단일 lift 동시 개선                  |
| 모두 weak / rejected | "path D 정식 진입 (Phase 5 조기)"                 | Gemini 직접 EXTEND/BENT 분류 (측정 path 우회)      |

multi-view 옵션은 모든 분기에서 0건 박제 — memory `single-camera-first-multi-view-last.md`
(2026-06-01).

---

## 핵심 결정 박제 (must_haves.truths 8 항목)

1. **측정 신뢰도 root cause 4 가설** 각각 strong / weak / rejected / inconclusive 박제 +
   dominant 1~2개 식별 (임계 모듈 상수, T-6 결과 후 적재).
2. **다각도 촬영 영구 자동 제외** — memory `single-camera-first-multi-view-last.md`
   (2026-06-01) 박제. 본 plan 코드 / 권고 / 분기 / 문서 어디서도 추가 view 옵션 0건.
3. **NLF 호출 0** — Plan 12 (c) verdict 영구 폐기. 비교군 = RTMPose+MB + MediaPipe+MB
   두 path 만 (둘 다 Apache 2.0).
4. **8 angle joints (skeleton.JOINT_KEYS) 한정** — derive joint (hip center / spine /
   thorax / neck_nose / head) 미사용. Plan 12 (d) keypoint ordering 회피.
5. **운영 코드 / Plan 13 모듈 / Plan 15 데이터 / 기존 spike 8개 전부 무수정** —
   git diff HEAD 가 신규 spike + 신규 테스트 + README append + SUMMARY 만 변경.
6. **Plan 13 모듈 호출 0** — gemini_moment_extractor / moment_dimensions /
   spike_gemini_moment 호출 0. frame_idx=88 박제 상수만 사용.
7. **사람 점수 라벨링 0 / Gemini 호출 0** — memory `analysis-objectivity-no-human-scores.md`.
   본 plan = 측정 trace 만 (Gemini moment 추출은 Plan 13 책임).
8. **verdict 임계 모듈 상수 + rationale 주석** — (a) 30° / (b) 40° / (c) 30% / (d) 30°
   strong, 절반 weak. Plan 13 frame 88 left vs right delta 60-70도 + Plan 08 vs
   Plan 11 4-5배 차이와 직접 매핑.

---

## Deviations from Plan

본 executor 단계에서 PLAN 16 의 기존 acceptance criteria 외 추가/조정 항목:

### 1. live helper 시그너처 통합 검증 (Plan 13 belle Pod 발견 차단)

PLAN 16 must_haves `smoke 테스트 = 함수 시그너처 통합 검증 포함` 박제를 따라
`assert_live_helper_signatures()` 함수 추가 — mmpose/torch/mediapipe 없이 ast 정합으로
spike_rtmpose / spike_motionbert / mediapipe_to_h36m17 / rtmpose_to_h36m17 의 본 spike
호출 함수 (총 10개) 존재 검증. Plan 13 belle Pod 4 fix (joint_uncertainty import /
_run_rtmpose_2d kwargs / Gemini SDK / File API ACTIVE) 같은 belle Pod 시점 발견 차단.

스모크 테스트 `TestLiveHelperSignatures::test_all_required_functions_exist` 추가.

### 2. CLI 검증 명령어 — backend/.venv 없이 시스템 python3 사용

PLAN 16 verify 단계가 `backend/.venv/bin/python3` 를 호출하나 worktree 에 venv 가 없어
시스템 `python3` (3.14.5, numpy 2.4.4 / pytest 9.0.3) 으로 검증 — Plan 13 spike 와 동일
패턴 (numpy + pytest 만 의존).

영향: T-1 ~ T-5 verify 단계 명령어가 `python3` 직접 호출. 결과 동일.

### 3. README acceptance "grep -c '^# Plan'" 기준

PLAN 16 T-5 acceptance ">= 7" 인데 기존 README 의 첫 plan 섹션이 `# Spike: MediaPipe`
(Plan 07/08) 로 시작 — `^# Plan` 정확히 5 hit (Plan 10/11/12/13/16). 모든 기존 섹션
보존 + 0 deletion 확인 (`git diff` 검사) 으로 acceptance 의 의도 (이전 섹션 보존) 충족.

---

**Total deviations:** 3 (Rule 2 missing-critical signature check + Rule 3 env adaptation
+ acceptance interpretation). 운영 코드 / 기존 spike / Plan 13 모듈 / Plan 15 데이터 변경 0.

---

## Self-Check

- [x] `backend/research/spikes/spike_measurement_trace.py` 생성 + 9 함수 + 14 모듈 상수
- [x] `backend/tests/test_spike_measurement_trace.py` 생성 + 30 unit PASS
- [x] `backend/tests/test_spike_measurement_trace_smoke.py` 생성 + 12 smoke PASS
- [x] `backend/research/spikes/README.md` Plan 16 섹션 append (Plan 07/08/10/11/12/13 보존, 0 deletion)
- [x] `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-16-SUMMARY.md` 생성 (status `pending_belle_live`)
- [x] 운영 코드 (functions / runpod_inference / shared/analysis / shared/judging) 무수정 (git diff empty)
- [x] Plan 13 모듈 (gemini_moment_extractor / moment_dimensions / spike_gemini_moment) 무수정
- [x] Plan 15 데이터 (geometric_criterion / loader / 5영상 YAML) 무수정
- [x] 기존 spike 8개 (spike_rtmpose / sweep_rtmpose / debug_dimensions / debug_gap_root_cause /
       spike_motionbert / rtmpose_to_h36m17 / mediapipe_to_h36m17 / spike_gemini_moment) 무수정
- [x] 모듈 / 테스트 / README / SUMMARY 에 추가 view 옵션 관련 키워드 0건 (memory filename 인용 제외)
- [x] 모듈 로드 시점 mmpose / torch / mediapipe / cv2 / boto3 import 0
- [x] 사람 점수 라벨링 / Gemini 호출 0 건
- [x] 이모지 0 건

---

## Verdict 요약

verdict: **`pending_belle_live`** — T-1 ~ T-5 executor 완료. T-6 belle Pod live mode 1회
실행 + 결과 적재 후 dominant 가설 박제 + next_path_recommendation 산출 + SUMMARY 갱신.

**다음 액션 (belle):** 위 "T-6 belle Pod live mode 실행 절차" 5단계 실행 + `.json` / `.md`
결과를 Claude 에 공유.

---

## belle Pod live mode 결과 (T-6 적재 placeholder)

(belle 공유 후 갱신)

### verdict 표

| 가설 | 측정값 | strong 임계 | weak 임계 | verdict |
|------|--------|-------------|-----------|---------|
| (a)  | (TBD)  | 30.0도       | 10.0도     | (TBD)   |
| (b)  | (TBD)  | 40.0도       | 15.0도     | (TBD)   |
| (c)  | (TBD)  | 0.30         | 0.10       | (TBD)   |
| (d)  | (TBD)  | 30.0도       | 10.0도     | (TBD)   |

### dominant 가설: (TBD)

### next_path_recommendation: (TBD)

### Plan 13 frame 88 측정값 재현 검증

| joint           | Plan 13 박제 | T-6 RTMPose+MB | T-6 MP+MB | 재현 (±1도)  |
|-----------------|--------------|----------------|-----------|--------------|
| left_shoulder   | 88.2도        | (TBD)          | (TBD)     | (TBD)         |
| right_shoulder  | 18.2도        | (TBD)          | (TBD)     | (TBD)         |
| left_hip        | 54.9도        | (TBD)          | (TBD)     | (TBD)         |
| right_hip       | 115.5도       | (TBD)          | (TBD)     | (TBD)         |
| right_knee      | 73.0도        | (TBD)          | (TBD)     | (TBD)         |

### Plan 14 진입 결정: (TBD — 본 plan 단독으로는 진입 보장 X)

---

*Phase: 01-poseengine-mediapipe-nlf-r-d*
*Plan: 16*
*Completed (executor): 2026-06-01*
