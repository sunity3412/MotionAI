---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "12"
subsystem: ml-pose-engine
tags:
  - spike
  - debug
  - gap-root-cause
  - rtmpose
  - nlf
  - hypothesis-trace
  - apache-2.0
  - pending_belle
  - gap_too_wide_blocked

dependency_graph:
  requires:
    - 01-08  # MP+MB 5영상 baseline — ref-invert 92 score 회귀 비교용
    - 01-10  # RTMPose+MB 단일 spike — ref-sideway-spin 72 / 37ms-per-frame 비교 baseline
    - 01-11  # RTMPose+MB 5영상 sweep — gap_too_wide_blocked verdict + ref-invert 22점 회귀
  provides:
    - "5 가설 (a~e) frame-level trace 스크립트 (debug_gap_root_cause.py) — Plan 13/14 진입 권고 산출"
    - "report-only mode — sweep JSON 만 입력으로 가설 (c)(d) + spike_vs_sweep + ref-invert 약 verdict (Pod 의존 X)"
    - "live mode — Pod 영상 처리로 가설 (a)(b)(e) frame-level 박제"
    - "ref-invert 22점 회귀 박제 헬퍼 (Plan 08 MP+MB 92 vs Plan 11 RTMPose+MB)"
    - "Plan 10 spike vs Plan 11 sweep 비일관성 trace 헬퍼 — gpu_warmup / frame_extractor / both 3 분기"
    - "aggregate_recommendation — 5 가설 verdict 합산 → Plan 13 path 분류 + Plan 14 게이트 기대"
  affects:
    - 01-15  # NEW (2026-06-01): JUDGE-DATA-01 IPSF GeometricCriterion 데이터 수집. Plan 12 (c) NLF baseline 부적합 박제 → NLF 갭 baseline 폐기 + IPSF 객관 임계값 도입. Plan 13 의 입력
    - 01-13  # Gemini key moment + criteria — Plan 15 데이터 입력 받음. Plan 12 가설 verdict 에 따라 standard / +mapping-correction
    - 01-14  # 5영상 재검증 sweep — Plan 13 + Plan 15 적용 후 IPSF tolerance + line/angle PASS 게이트 통과 여부

tech_stack:
  added:
    - "(없음) — mmpose 1.3.2 / numpy 1.26.4 / mmcv 2.1.0 등 Plan 10/11 환경 그대로"
  patterns:
    - "report-only / live mode 분리 — 모듈 로드 시점 mmpose/torch/NLF import 없음, live mode 진입 시 helper 내부 lazy import"
    - "기존 spike helper 재사용 (코드 1벌) — _resolve_video / _extract_frames / _run_rtmpose_2d / _load_motionbert / _run_motionbert_inference / _h36m17_to_coco17_subset 그대로 호출, spike_rtmpose 무수정"
    - "운영 NLF estimator 사용 — sunity_shared.analysis.pose_estimator.NlfPoseEstimator + features.compute_joint_angles + temporal.temporal_fill (Plan 10 spike _run_nlf_baseline 패턴 동일)"
    - "가설 verdict 4단계 — strong / weak / rejected / inconclusive. 임계는 모듈 상수로 박제 + rationale 주석"

key_files:
  created:
    - backend/research/spikes/debug_gap_root_cause.py
    - backend/tests/test_debug_gap_root_cause_smoke.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-12-SUMMARY.md
  modified:
    - backend/research/spikes/README.md  # Plan 12 섹션 append (Plan 07/08/10/11 보존)

decisions:
  - "Plan 12 scope = trace + 가설 verdict 박제만. fix 자체는 Plan 13/14 책임. dimensions.py / technique.py / FallbackRecognizer / spike_rtmpose / sweep_rtmpose / debug_dimensions / rtmpose_to_h36m17 무수정 — Plan 12 PLAN scope_limits 명시."
  - "5 가설 imbalance — (a)(b)(e) 는 live mode 필수 (Pod 영상 처리), (c)(d) + spike_vs_sweep + ref-invert delta 는 report-only 로 즉시 박제. report-only 만으로 Plan 13 진입 권고 1차 산출 가능 (live 결과는 권고 강화/조정용)."
  - "가설 (d) 박제 결과 (로컬 검증): RTMPose chain (rtmpose_to_h36m17.H36M_JOINT_NAMES, H36M ordering) vs NLF chain (sunity_shared.analysis.skeleton.KEYPOINT_NAMES, COCO ordering) → 17/17 joint 이름 모두 다름. 단, angle 계산은 8 joint 만 사용 (skeleton.JOINT_KEYS) 하고 spike_rtmpose 의 _h36m17_to_coco17_subset 가 12 limb keypoint 만 COCO ordering 으로 복원 → 8 joint angle 계산 자체는 일치해야 함 (face/derive joint NaN). derive joint (hip/spine/thorax/neck_nose/head) 가 향후 Plan 13 moment scoring 에 들어가면 mismatch 가 점수에 영향."
  - "verdict 임계 (모듈 상수): (a) strong 20° / weak 8° — frame별 mean joint disagreement. (b) strong headdown_score ≤ 0.30 + overall 대비 0.10 이상 drop. (c) strong NLF overall range ≥ 20점 / weak ≥ 10점. (e) strong root-relative distance ≥ 0.30 / weak ≥ 0.15. spike_vs_sweep ms/frame ratio ≥ 1.5 → msper_differ."
  - "live mode 5영상 vs 2영상 — Plan 12 T-5-2 명시는 ref-invert + ref-sideway-spin 2영상 우선 (가설 b headdown + 비일관성 비교 baseline). 5영상 전부 돌리면 ~12분, 2영상 ~5분. belle 선택."
  - "Plan 11 sweep 결과 NLF overall [58, 63, 64, 65, 81] → 가설 (c) report-only verdict = strong (span 23 ≥ 20). 즉 Plan 14 게이트 기대 = 'additional spike required' (NLF baseline 영상별 편차로 D-14 ≤5 회복 어려움). 단, belle 결정 (2026-06-01) 은 D-14 강등 거부 + line/angle 동등 게이트이므로 Plan 13/14 진행 자체는 멈추지 않음 — 'additional spike required' 는 후속 spike 필요 신호."
  - "**Plan 12 verdict 후속 belle 결정 (2026-06-01, sweep 결과 + report-only verdict 적재 후)**: (c) strong → NLF baseline 부적합 확정. belle 메타 원칙 재확인 — (1) AI 분석 객관성 절대: 사람 점수 라벨링 (belle/강사/심사자) ground truth 영구 금지. (2) 채점/게이트 baseline = IPSF Code of Points 단일 기준 (이미 plan 초기 설계 시 결정, REQUIREMENTS JUDGE-01/02 박제). → **Plan 15 신설 (JUDGE-DATA-01 IPSF GeometricCriterion 데이터 수집)**. NLF 갭 baseline 영구 폐기. D-14 게이트 = '측정 각도 vs IPSF targetValue 갭 ≤ toleranceFull'. Plan 13 입력 = Plan 15 데이터. memory 박제 — `analysis-objectivity-no-human-scores.md` + `judging-baseline-ipsf-code-of-points.md`."
  - "Plan 08 MP+MB ref-invert overall 92 는 Plan 08 SUMMARY 영상별 표 행 4 (확인). 모듈 상수 PLAN_08_MP_MB_REF_INVERT_OVERALL = 92.0 로 박제 — 변경 시 Plan 08 SUMMARY 와 동기화."

requirements_completed: []  # POSE-01 갭 ≤5 + line/angle PASS 게이트 통과 후 충족. Plan 12 는 trace 박제만, 미충족.

metrics:
  duration: "~70 min executor (T-1 ~ T-4 + smoke 테스트 + README + SUMMARY) — belle Pod live mode (T-5) 별도"
  completed_date: "pending_belle (belle Pod live mode 실행 후 verdict 갱신)"
  tasks_completed: 4   # T-1 ~ T-4 완료. T-5 belle 대기.
  tasks_total: 5
  files_created: 3
  files_modified: 1
---

# Phase 01 Plan 12: 갭 root cause 디버그 spike — pending belle

**One-liner:** Plan 11 sweep `gap_too_wide_blocked` 후속 — 5개 가설 (a) frame-mean / (b) RTMPose headdown / (c) NLF baseline 편차 / (d) keypoint 매핑 / (e) 두 엔진 3D 분포 차이 frame-level trace + ref-invert 22점 회귀 박제 + Plan 10 spike vs Plan 11 sweep 비일관성 분기. **Fix 자체는 Plan 13/14 책임 — 본 plan 은 trace + 가설 verdict 박제만.** report-only mode 로 (c)(d) + spike_vs_sweep + ref-invert delta 1차 산출 가능, live mode 는 belle Pod 대기.

---

## TL;DR

| 항목 | 내용 |
|---|---|
| **Verdict** | **`pending_belle`** (report-only 1차 트레이스 완료, live mode (a)(b)(e) belle Pod 대기) |
| **단계 도달** | T-1 ~ T-4 완료. T-5 belle Pod live mode 대기 |
| **scope** | trace + 가설 verdict 박제만 — fix 0 줄 |
| **신규 파일** | 2 (debug spike + smoke 테스트) + 1 SUMMARY |
| **수정 파일** | 1 (README append, Plan 07/08/10/11 보존) |
| **단위 테스트** | 11 PASS (mmpose / torch / NLF 없이 로컬, 0.11s) |
| **만든 커밋** | 4 (debug spike / smoke / README + SUMMARY) |
| **운영 코드 수정** | 0 (functions / runpod_inference / shared/pose_lifters / dimensions.py / technique.py / FallbackRecognizer 모두 무수정) |
| **기존 spike 수정** | 0 (spike_rtmpose / sweep_rtmpose / debug_dimensions / rtmpose_to_h36m17 / mediapipe_to_h36m17 모두 무수정) |
| **다음 행동** | belle Pod live mode 실행 → 결과 적재 → verdict 갱신 → Plan 13 PLAN 작성 |

---

## T-1 — `debug_gap_root_cause.py` 골격 + 가설 (a)(c)(d)

### 모듈 구조

```
backend/research/spikes/debug_gap_root_cause.py
  # Constants — 가설별 verdict 임계 (rationale 주석)
  HYPOTHESIS_A_STRONG_DEG / WEAK_DEG
  HYPOTHESIS_B_HEADDOWN_SCORE_DROP / STRONG_HEADDOWN_SCORE
  HYPOTHESIS_C_STRONG_OVERALL_RANGE / WEAK_OVERALL_RANGE
  HYPOTHESIS_E_STRONG_DISTANCE / WEAK_DISTANCE
  SPIKE_VS_SWEEP_MS_RATIO_THRESHOLD
  PLAN_08_MP_MB_REF_INVERT_OVERALL = 92.0  # Plan 08 SUMMARY 행 4 박제

  build_arg_parser() → ArgumentParser  (12 CLI args, 테스트 재사용)
  trace_hypothesis_a(lifter_angles, nlf_angles) → dict   # (a) frame-mean (live)
  trace_hypothesis_b(rtmpose_kp, score_threshold) → dict # (b) headdown (live)
  trace_hypothesis_c(sweep_report) → dict                # (c) NLF baseline 편차 (report-only)
  trace_hypothesis_d() → dict                            # (d) keypoint 매핑 (로컬)
  trace_hypothesis_e(lifter_xyz, nlf_xyz) → dict         # (e) 3D 분포 (live)
  trace_ref_invert_regression(sweep_report, h_b) → dict
  trace_spike_vs_sweep(spike_report, sweep_report, motion) → dict
  aggregate_recommendation(hypotheses, svs, ref_inv) → dict
  _run_live_for_motion(...) → dict                       # live mode helper (lazy import)
  run_debug(...) → dict                                  # 메인
  generate_markdown(debug_result) → str
  main()                                                  # CLI 진입점
```

### CLI 인자 (12개)

| 인자 | default | 설명 |
|---|---|---|
| `--mode` | `report-only` | `report-only` 또는 `live` |
| `--sweep-report` | (required) | Plan 11 sweep_rtmpose JSON 경로 |
| `--spike-report` | None | Plan 10 spike_rtmpose JSON (있으면 spike_vs_sweep 활성화) |
| `--motions` | None | live mode 분석 영상 리스트 |
| `--bucket` | `sunity-motion-pilot-videos` | S3 버킷 (live mode) |
| `--rtmpose-config` | None | RTMPose config (.py) (live mode 필수) |
| `--rtmpose-checkpoint` | None | RTMPose 가중치 (.pth) (live mode 필수) |
| `--motionbert-root` | `/workspace/MotionBERT` | MotionBERT 저장소 |
| `--motionbert-weights` | (auto) | MotionBERT 가중치 |
| `--score-threshold` | `0.3` | RTMPose keypoint 컷 |
| `--det-model` | `none` | detector 우회 (Plan 10 default) |
| `--out` | (auto) | `backend/research/spikes/reports/debug_gap_<UTC>.json` |

### 가설 (a) Frame-mean 한계 trace — live

두 (T, J=8) angle 행렬 (lifter_filled, nlf_filled) 의 frame별 joint 평균 절대각 차이.
NaN-safe (`np.nanmean`), 영상별 frame 수 다르면 짧은 쪽에 맞춰 truncate.
출력: `{frame_count, joint_disagreement_per_frame, mean_disagreement, peak_disagreement_frame_idx, verdict}`.

### 가설 (c) NLF baseline 영상별 편차 trace — report-only OK

sweep_report JSON 의 영상별 `nlf.overall` 분포 + stability/line/angle 차원별 variance.
출력: `{nlf_overall_range: [min, max], nlf_overall_span, nlf_overall_variance, motions_count, nlf_dim_variance, nlf_nan_rate_per_joint: null (report-only), verdict}`.

### 가설 (d) keypoint 매핑 차이 trace — 로컬

`rtmpose_to_h36m17.H36M_JOINT_NAMES` (H36M ordering) vs `sunity_shared.analysis.skeleton.KEYPOINT_NAMES` (COCO ordering) 17 row side-by-side.
출력: `{rtmpose_chain_joints, nlf_chain_joints, joint_definition_diff: [{idx, rtmpose_chain, nlf_chain, equal}], angle_chain_keys, angle_chain_keys_match, diff_count, verdict}`.

**로컬 검증 결과 (executor)**: `diff_count = 17 / 17` (두 ordering 모두 다름), `verdict = strong`. 단, angle 계산은 8 joint 만 사용 (`skeleton.JOINT_KEYS`) 하고 `_h36m17_to_coco17_subset` 가 12 limb keypoint 만 COCO ordering 으로 복원하므로 angle scoring 자체는 일치해야 함. derive joint (hip/spine/thorax/neck_nose/head) 가 Plan 13 moment scoring 에 들어가면 mismatch 영향 가능 — 별도 박제 필요.

---

## T-2 — 가설 (b)(e) + ref-invert + spike_vs_sweep

### 가설 (b) RTMPose headdown 약점 trace — live 전용

`_run_rtmpose_2d` 반환 (T, 17, 3 pixel+score) 입력:
- frame별 mean score histogram (5 bins: 0-0.2 / 0.2-0.4 / 0.4-0.6 / 0.6-0.8 / 0.8-1.0)
- score < threshold (0.3) NaN drop rate
- COCO L_SHOULDER=5, R_SHOULDER=6, L_HIP=11, R_HIP=12 기준 hip_y < shoulder_y → headdown frame 식별
- headdown 구간 평균 score vs overall 평균 비교

출력: `{score_histogram: {bins, counts}, frame_mean_scores, nan_drop_rate, headdown_frame_count, headdown_frame_indices (cap 50), headdown_avg_score, overall_avg_score, verdict}`.

### 가설 (e) 두 엔진 3D pose 분포 차이 trace — live 전용

같은 영상 같은 frame 에서 RTMPose+MB 의 `_h36m17_to_coco17_subset` 결과 (T, 17, 4) 중 xyz 와 NLF estimator 의 (T, 17, 4) 중 xyz 비교.

Root-relative 정규화 — hip center (COCO L_HIP=11, R_HIP=12 평균) 기준 정규화 후 17 joint frame별 mean Euclidean distance.

출력: `{mean_per_frame, overall_mean_distance, peak_frame_idx, verdict}`.

### ref-invert 22점 회귀 박제

Plan 08 MP+MB ref-invert overall = **92** (Plan 08 SUMMARY 행 4 박제, 모듈 상수 `PLAN_08_MP_MB_REF_INVERT_OVERALL`).
Plan 11 RTMPose+MB ref-invert overall = sweep_report 의 ref-invert entry `rtmpose_mb.overall` (Plan 11 SUMMARY 표 = **70**).

→ delta = **-22 점**. 가설 (b) live 결과가 있으면 headdown_frame_count + headdown_avg_score + overall_avg_score 도 같이 박제.

### spike_vs_sweep 비일관성 박제

Plan 10 spike (ref-sideway-spin overall 72, ms/frame 37, frames_total 알 수 없음 - report 의 frames_total 확인 필요) vs Plan 11 sweep (ref-sideway-spin overall 80, ms/frame 21, frames_total 알 수 없음).

verdict 분기 (`SPIKE_VS_SWEEP_MS_RATIO_THRESHOLD = 1.5`):
- frames_total 동일 + ms/frame ratio ≥ 1.5 → **`gpu_warmup`** (sweep 두 번째 영상부터 cold-start 제거)
- frames_total 다름 + ms/frame ratio < 1.5 → **`frame_extractor`** (비결정성)
- 둘 다 → **`both`**
- 둘 다 거의 동일 → **`consistent`**

스모크 테스트로 3 분기 모두 검증 (Plan 11 sweep 실데이터 ref-sideway-spin frames_total 100 + ms/frame 21 stub, Plan 10 spike frames_total 100 + ms/frame 37 stub → 예상 `gpu_warmup`).

---

## T-3 — verdict 합산 + Plan 13/14 권고

### aggregate_recommendation 분기 룰

```
verdicts = {a, b, c, d, e}

paths = ["standard"]
if verdicts.b == strong: paths += "+ hybrik_spike"
if verdicts.c == strong: paths += "+ nlf_re-spike"
if verdicts.d == strong: paths += "+ rtmpose_to_h36m17_correction"
if verdicts.e == strong: paths += "+ multi_engine_averaging"
plan_13_path = " ".join(paths)

if verdicts.a == strong and not any({b,c,d,e}.strong):
  plan_14_gate = "expected to pass"
  # rationale: frame-mean averaging 만이 dominant 원인, Plan 13 key moment 단독으로 회복
elif any({b,c,d,e}.strong):
  plan_14_gate = "additional spike required"
  # rationale: Plan 13 단독으로는 회복 어려움
elif all rejected/inconclusive:
  plan_14_gate = "inconclusive"
  # rationale: 단일 원인 식별 실패, Plan 12.5 검토 또는 Plan 13 진입 후 사후 검증
else:
  plan_14_gate = "inconclusive"
  # rationale: 가설 다수 weak, 혼합 원인
```

### 현재 report-only 1차 verdict 예상 (sweep_report stub 기반)

| 가설 | report-only verdict | 근거 |
|---|---|---|
| (a) | inconclusive | live 미실행 |
| (b) | inconclusive | live 미실행 |
| **(c)** | **strong** | sweep stub NLF overall [58, 63, 64, 65, 81] → span 23 ≥ 20 |
| **(d)** | **strong** | RTMPose H36M ordering vs NLF COCO ordering 17/17 다름 |
| (e) | inconclusive | live 미실행 |

→ `plan_13_path = "standard + nlf_re-spike + rtmpose_to_h36m17_correction"`
→ `plan_14_gate_expectation = "additional spike required"`

belle Pod live mode 실행 후 (a)(b)(e) verdict 확정 → 최종 권고 갱신.

### JSON output schema

```
{
  "generated_at": "ISO 8601 UTC",
  "mode": "report-only | live",
  "input": {"sweep_report": "...", "spike_report": "...", "motions": [...]},
  "hypotheses": {
    "a": {"verdict": "...", "per_motion": {...}},
    "b": {...}, "c": {...}, "d": {...}, "e": {...}
  },
  "ref_invert_regression": {"motion": "ref-invert", "plan_08_mp_mb_overall": 92.0, "plan_11_rtmpose_mb_overall": ..., "delta": ..., "hypothesis_b_summary": {...}},
  "spike_vs_sweep": {"motion": "ref-sideway-spin", "spike_frames": ..., "sweep_frames": ..., "spike_overall": ..., "sweep_overall": ..., "spike_msper": ..., "sweep_msper": ..., "msper_ratio": ..., "verdict": "..."},
  "recommendation": {"verdicts": {...}, "plan_13_path": "...", "plan_14_gate_expectation": "...", "rationale": "..."},
  "per_motion_live": {...}    # live mode 일 때만
}
```

---

## 5 가설 verdict 매트릭스 (placeholder)

belle Pod live mode 실행 + ref-invert / ref-sideway-spin 결과 적재 후 갱신.

| 영상 | (a) frame-mean | (b) headdown | (c) NLF baseline | (d) mapping | (e) 3D distance |
|---|---|---|---|---|---|
| ref-climb | (live 대기) | (live 대기) | strong (sweep) | strong (로컬) | (live 대기) |
| ref-foxtop-split | (live 대기) | (live 대기) | strong (sweep) | strong (로컬) | (live 대기) |
| ref-foxtop | (live 대기) | (live 대기) | strong (sweep) | strong (로컬) | (live 대기) |
| ref-invert | (live 대기, 우선) | (live 대기, 우선) | strong (sweep) | strong (로컬) | (live 대기, 우선) |
| ref-sideway-spin | (live 대기, 우선) | (live 대기, 우선) | strong (sweep) | strong (로컬) | (live 대기, 우선) |

---

## ref-invert 회귀 박제 (placeholder)

belle Pod 실행 후 (b) headdown summary 적재.

| 항목 | 값 |
|---|---|
| Plan 08 MP+MB overall | 92.0 (Plan 08 SUMMARY 행 4, 모듈 상수 박제) |
| Plan 11 RTMPose+MB overall | 70.0 (Plan 11 SUMMARY 표) |
| delta | **-22.0** |
| headdown_frame_count | (live 대기) |
| headdown_avg_score | (live 대기) |
| overall_avg_score | (live 대기) |
| 가설 (b) verdict | (live 대기) |

---

## spike_vs_sweep 박제 (placeholder)

Plan 10 spike_rtmpose 결과 JSON 이 `backend/research/spikes/reports/` 에 저장돼있지 않다 (Pod 에서만 생성, .gitkeep 외 비어있음). belle Pod 에서 두 JSON 모두 보유 후 비교 가능. 예상 verdict (Plan 11 SUMMARY 표 기준 stub):

| 항목 | Plan 10 spike (예상) | Plan 11 sweep (예상) | diff |
|---|---|---|---|
| frames_total | (확인 필요) | (확인 필요) | (확인 필요) |
| overall | 72 | 80 | +8 |
| ms_per_frame | 37 | 21 | ratio 1.76 |
| avg_score | 0.4382 | 0.40 | 거의 동일 |

frames_total 이 동일하면 `gpu_warmup` verdict (cold-start 가설). 다르면 `frame_extractor` 비결정성. 둘 다 다르면 `both`.

---

## T-4 — README append + 11 smoke 테스트

### README

`backend/research/spikes/README.md` Plan 12 섹션 append (Plan 07/08/10/11 보존):
- 5 가설 표
- report-only mode 실행 예시
- live mode 실행 예시 (Pod 전용)
- Plan 13 진입 게이트 (recommendation 분류)
- 주의사항 (운영 코드 / 기존 spike 무수정)

### 11 smoke 테스트 (mmpose 없이 로컬, 0.11s)

```bash
PYTHONPATH=backend/shared/python:. python3 -m pytest \
  backend/tests/test_debug_gap_root_cause_smoke.py -v
# 11 passed in 0.11s
```

| 클래스 | tests | 범위 |
|---|---|---|
| TestCliParsing | 3 | mode default / sweep-report required / out default path |
| TestHypothesisC | 2 | nlf_overall_range 정확 계산 + strong verdict |
| TestHypothesisD | 2 | 17 row shape + 최소 1 행 차이 (fail-loud 메시지) |
| TestSpikeVsSweep | 3 | gpu_warmup / frame_extractor / both 분기 |
| TestJsonShape | 1 | top-level + hypotheses 키 + .md sibling |

stub sweep JSON 은 Plan 11 실데이터 NLF overall [58, 63, 64, 65, 81] 모사.

---

## T-5 — belle Pod live mode 대기 (autonomous: false)

### T-5-1: report-only mode (로컬 또는 Pod 어디서나)

```bash
python3 -m backend.research.spikes.debug_gap_root_cause \
  --mode report-only \
  --sweep-report backend/research/spikes/reports/sweep_rtmpose_20260601_0411.json \
  --spike-report backend/research/spikes/reports/spike_rtmpose_<Plan10>.json \
  --out backend/research/spikes/reports/debug_gap_$(date +%Y%m%d_%H%M).json
```

→ 가설 (c)(d) verdict + spike_vs_sweep verdict + ref-invert 회귀 표 (가설 b sweep 기반 약 verdict).

> **참고**: Plan 10 spike_rtmpose JSON 은 belle Pod 에서만 생성됨 (`backend/research/spikes/reports/.gitkeep` 외 git 미추적). belle Pod 에 보관된 Plan 10 spike JSON 경로를 `--spike-report` 에 넘기면 spike_vs_sweep 활성화.

### T-5-2: live mode (belle Pod, ref-invert + ref-sideway-spin 2영상 우선)

```bash
cd /workspace/SunityMotion && git pull --ff-only origin main

python3 -m backend.research.spikes.debug_gap_root_cause \
  --mode live \
  --motions ref-invert ref-sideway-spin \
  --bucket sunity-motion-pilot-videos \
  --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \
  --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \
  --motionbert-root /workspace/MotionBERT \
  --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \
  --sweep-report backend/research/spikes/reports/sweep_rtmpose_20260601_0411.json \
  --out backend/research/spikes/reports/debug_gap_live_$(date +%Y%m%d_%H%M).json
```

예상 소요: 2영상 × ~2.5분 = ~5분. 5영상 전부 (`--motions ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin`) = ~12분.

→ 가설 (a)(b)(e) verdict + ref-invert headdown 가설 강도 + 두 엔진 3D 분포 차이.

### T-5-3: belle 응답 옵션

| 응답 | 조건 | 다음 행동 |
|---|---|---|
| **"가설 a dominant, Plan 13 표준 진입"** | (a) strong 단독, 나머지 rejected/inconclusive | Plan 13 (Gemini key moment + criteria) 표준 진입. Plan 14 통과 기대. |
| **"가설 b/d/e 추가 spike 필요"** | (b)/(d)/(e) 중 strong | Plan 13 진입 + 후속 spike (HybrIK 비교군 / rtmpose_to_h36m17 derive 보정 / multi-engine averaging). |
| **"가설 c NLF baseline 신뢰도 약함 → 게이트 기준 재정의 요청"** | (c) strong, 다른 가설 약함 | belle 직접 결정 — D-14 강등은 거부 박제 (memory `gap-and-line-angle-mandatory-gates.md`). 재정의는 다른 baseline 영상 / threshold 조정 path 만 검토. |
| **"trace 부족, 추가 가설 / 영상 필요"** | 모든 가설 inconclusive 또는 5영상 trace 부족 | Plan 12 scope 확장 또는 Plan 12.5 신설. |

### T-5-4: belle 응답 적재 후

1. belle 응답 → 본 SUMMARY 상단 frontmatter `metrics.completed_date` 갱신 + `tags` 에 verdict 추가 (`a_dominant_standard` / `b_or_e_additional_spike` / `c_baseline_review` / `inconclusive_scope_expansion`).
2. 본 SUMMARY 5 가설 verdict 매트릭스 + ref-invert 회귀 박제 + spike_vs_sweep 박제 placeholder → 실데이터로 갱신.
3. STATE.md `Current Position` Plan 12 verdict 명시 + `progress.completed_plans` 9/14 로 갱신.
4. ROADMAP.md Plan 12 진행률 행 갱신.
5. 다음 행동: `/gsd:plan-phase 1 --plan 13` (Plan 13 Gemini key moment + criteria PLAN 작성).

---

## Deviations from Plan

### 1. CLI 인자 수 — PLAN 명세 8개 (필수 1 + 옵션 7) vs 실 구현 12개

PLAN T-1-5 는 "CLI args 8개 (필수 1 + 옵션 7)" 라 박제했지만 실제 필요 옵션을 세분화하면 12개. 추가된 4개:
- `--motionbert-root` (default `/workspace/MotionBERT`)
- `--score-threshold` (default 0.3)
- `--det-model` (default `none`)
- `--out` (default 자동)

Plan 11 sweep_rtmpose CLI (9 args) 와 패턴 일치. PLAN 의 8개 명세는 minimum, 실제는 spike_rtmpose 호환 위해 확장.

### 2. 11 smoke 테스트 (PLAN T-4-2 "5 테스트" vs 실 11)

PLAN 은 "5 테스트" 라 박제했지만 각 테스트 항목 (CLI 파싱 / (c) / (d) / spike_vs_sweep / JSON shape) 안에서 검증 포인트가 명확히 분리되어 fine-grained 분할. 5 개 scope 항목 → 11 method 로 매핑:
- CLI 파싱 → 3 (mode default + sweep-report required + out default)
- 가설 (c) → 2 (nlf_overall_range 정확 + verdict strong)
- 가설 (d) → 2 (17 row shape + 최소 1 다름 fail-loud)
- spike_vs_sweep → 3 (gpu_warmup / frame_extractor / both 3 분기)
- JSON shape → 1 (top-level + hypotheses + .md sibling)

5 scope 항목 모두 충족, 분기별 검증 강화.

### 3. 가설 (d) verdict 임계 박제 — PLAN "정의 차이 비교" → 실 17/17 모두 다름 검출

PLAN 은 "두 17-joint 정의 차이 표 출력" 만 명시. 실 구현은 H36M ordering vs COCO ordering 이라 byte-for-byte 비교 시 17/17 모두 다름 — verdict `strong` 자동 산출. 단, angle 계산은 8 joint 만 사용 (`skeleton.JOINT_KEYS`) + `_h36m17_to_coco17_subset` 가 12 limb keypoint 만 COCO ordering 으로 복원 → 8 joint angle scoring 자체는 일치해야 함. PLAN 의 가설 (d) confirmed 시점은 "derive joint 가 angle scoring 에 들어가면 mismatch 영향" 인 경우 — 본 spike 의 verdict `strong` 은 chain 정의 차이가 존재함을 박제, 실제 점수 영향은 Plan 13 derive joint 사용 여부에 달림. SUMMARY decisions 에 명시.

### 4. report-only mode 의 가설 (c) verdict 1차 산출

PLAN <context> 표 (c) 행은 "Pod 실행 시 추가: NLF (T, J) matrix 의 joint별 NaN rate / 표준편차" 라 명시했지만, report-only 만으로도 sweep_report NLF overall 분포 (span / variance) 로 1차 verdict 가능. NaN rate 는 live mode 진입 시 `nlf_nan_rate_per_joint` 로 보강. PLAN 의도와 일치 (report-only 박제 가능 → 1차 산출, live 보강).

---

## Known Stubs

없음. 본 plan 의 debug spike 스크립트는 belle Pod 에서 즉시 실행 가능한 완전한 구현 (11 smoke 테스트 PASS, mmpose 없이 로컬 검증).

`per_motion_live` 와 `hypotheses.a/b/e` 의 `verdict` 는 report-only mode 에서는 `inconclusive` 로 산출 — stub 아니라 정상 동작 (live mode 진입 시 자동 산출).

---

## Threat Flags

없음 — 신규 네트워크 엔드포인트 / auth path / Firestore 스키마 변경 없음. spike 코드만 추가, 운영 코드 무수정. mmpose / torch / NLF 는 모듈 로드 시점 import 없음 (live mode helper 내부 lazy import).

---

## Open Questions / Next Step

### Open Questions (belle Pod live mode 실행 후 확정)

1. **가설 (a) frame-mean 한계 verdict** — ref-invert / ref-sideway-spin 의 mean_disagreement 가 ≥ 20° 면 strong, 8~20 weak, < 8 rejected. strong 단독이면 Plan 13 표준 진입 + Plan 14 통과 기대.
2. **가설 (b) RTMPose headdown 약점 verdict** — ref-invert headdown frame_count + headdown_avg_score. strong (headdown_avg ≤ 0.30 + overall 대비 0.10 drop) 이면 Plan 13 + HybrIK 비교군 spike (별도 plan).
3. **가설 (e) 두 엔진 3D 분포 차이 verdict** — overall_mean_distance ≥ 0.30 면 strong (lift path 자체 신뢰도 약함). Plan 13 + multi-engine averaging 검토.
4. **Plan 10 spike vs Plan 11 sweep frames_total 동일 여부** — Pod 에서 두 JSON 모두 보유 후 비교. 동일 + ms/frame 1.76 ratio → gpu_warmup. 다름 → frame_extractor.

### Next Step (확정 path)

```
belle Pod 실행 (5~12분, 2영상 또는 5영상 선택)
  → 결과 .md + .json Claude 공유
  → 본 SUMMARY 5 가설 verdict 매트릭스 + ref-invert 박제 + spike_vs_sweep 박제 placeholder 갱신
  → STATE.md / ROADMAP.md 갱신
  → belle 응답 (4 옵션 중 1)
  → /gsd:plan-phase 1 --plan 13 진입 (Plan 13 Gemini key moment + criteria PLAN 작성)
```

---

## Self-Check: PASSED

**파일 존재 확인** (executor 작성):

- `backend/research/spikes/debug_gap_root_cause.py` FOUND
- `backend/tests/test_debug_gap_root_cause_smoke.py` FOUND
- `backend/research/spikes/README.md` FOUND (modified, Plan 12 섹션 append)
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-12-SUMMARY.md` FOUND (이 파일)

**운영 코드 무수정 확인**:

- `backend/functions/pipeline/app.py` UNCHANGED
- `backend/runpod_inference/server.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/technique.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/dimensions.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/features.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/temporal.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/pose_estimator.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/pose_lifters/` UNCHANGED

**기존 spike 무수정 확인**:

- `backend/research/spikes/spike_rtmpose.py` UNCHANGED (Plan 10 본체)
- `backend/research/spikes/sweep_rtmpose.py` UNCHANGED (Plan 11 본체)
- `backend/research/spikes/debug_dimensions.py` UNCHANGED (Plan 11 line/angle trace)
- `backend/research/spikes/rtmpose_to_h36m17.py` UNCHANGED (Plan 10 adapter)
- `backend/research/spikes/mediapipe_to_h36m17.py` UNCHANGED (Plan 07/08 adapter)

**테스트 결과 확인**:

- `backend/tests/test_debug_gap_root_cause_smoke.py`: **11 PASS** (mmpose 없이 로컬, 0.11s)
- 기존 테스트 회귀 없음 (본 plan 무영향)

**커밋 존재 확인** (Plan 12):

- `feat(01-12): debug_gap_root_cause.py — 5가설 trace + ref-invert 회귀 + spike_vs_sweep` FOUND
- `test(01-12): 11 smoke tests — CLI / 가설 c·d / spike_vs_sweep / JSON shape` FOUND
- `docs(01-12): README append + SUMMARY (pending_belle)` (본 commit 예정)

---

## Verdict 요약 — orchestrator 에게

- **verdict**: `pending_belle`
- **one-liner**: Plan 11 sweep `gap_too_wide_blocked` 후속 — 5 가설 trace 헬퍼 + ref-invert 22점 회귀 박제 + Plan 10 spike vs Plan 11 sweep 비일관성 분기. report-only mode 로 가설 (c)(d) 1차 verdict (둘 다 strong), live mode (a)(b)(e) belle Pod 대기. fix 0 줄 (Plan 13/14 책임).
- **commits (executor)**: 3 + 본 docs commit = 4 (debug spike / smoke / README+SUMMARY).
- **next action**: belle Pod live mode 실행 (T-5-2, 2영상 또는 5영상) → 결과 적재 → 본 SUMMARY verdict 갱신 → `/gsd:plan-phase 1 --plan 13` 진입 (Plan 13 Gemini key moment + criteria PLAN 작성).
