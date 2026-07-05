# Phase 25 — vision-pointed 상체 감점 게이트 (SCORE-09 + SCORE-15)

Phase 25 는 감점 seed 를 관절 단위 2-source merge 로 바꿨다: Gemini 가 짚은(pointed)
관절만 worst-window median 으로 감점하고, silent 관절은 full-path DTW median 을 유지한다
(25-01). 이 디렉터리는 그 구조가 실영상 6페어에서 지는지(성공 위양성 0 + kip-up 상체
감점 실효 + 무퇴행 + 결정론) 판정하는 최종 게이트다.

phase24 harness 복제-확장. phase24 의 7 게이트(traceability / monotonicity / determinism /
criterion-selection / generalization / clean_residual / sensitivity)는 **import 재사용**.

## 신규 게이트 (`assert_gates.py`, importable — tests/test_phase25_eval_gates.py 가 unit-test)

| 함수 | 무엇을 증명 | scope |
|---|---|---|
| `check_success_100` | success 멤버 전원 `overallScore == 100` (위양성 0 — 260702-o0c FAIL 재발 금지). phase24 generalization 의 within-tolerance 허용보다 강함 | artifact-gated. climb 은 known not_pole 게이트라 제외 |
| `check_pointed_only_window` | 전 멤버 `seedObservation.window_joints ⊆ pointed_joints` — window 감점은 vision 이 짚은 관절에서만 (SCORE-15 구조 assert) | artifact-gated. done 멤버의 seedObservation 부재 = harness 배선 결함 FAIL |
| `check_kipup_upper_structure` | kip-up fault: (a) overall < **phase24 baseline**(방향 비교 — 고정 타깃 아님) (b) 상체(shoulder/elbow) `angle_vs_reference` record ≥ 1 (c) 그 record 관절 ∈ pointed set | artifact-gated (phase24 baseline artifact 필요) |
| `check_fault_no_regression` | 5 fault 멤버 각각 `overallScore <= phase24 baseline` (방향 비교, 무퇴행) + climb not_pole 유지 | artifact-gated. baseline 부재 시 SKIPPED |
| `check_cold_warm_determinism` | cold sweep vs warm 재실행(캐시 hit, Gemini 0 call) — status/errorCode/overallScore/activatedCriteria/deductionBreakdown 동일 | `phase25_sweep_report_warm.json` 부재 시 SKIPPED |

**특정 점수 assert 금지 (locked):** kip-up "< 88" 은 phase24 baseline artifact 실측값 대비
**방향 비교**(fault 변별 개선)이지 고정 타깃이 아니다. 게이트 소스에 점수 리터럴 타깃
하드코딩 금지 (테스트가 grep assert). 사람 점수 라벨 0. 밴드 0.

## 짚기-FP 관측 (게이트 아님 — OD-2)

success 멤버의 Gemini collect status(짚은 관절 목록)를 harness tee 가 처음으로 캡처한다
(기존 na_audit 는 collect 산출을 버림 — 리서치 §3 관측 공백). `pointingFpObservation`
섹션 + `summarize_pointing_fp` 출력 = "clean 영상 짚기 빈도" 최초 관측치. **감점 판정은
window 측정 + tol 20° 게이트가 지므로 짚기 자체는 FAIL 이 아니다** — 관측 지표만.

## harness tee (read-only — 리서치 함정 ③)

`run_sweep.py` 가 `_load_pipeline()` 직후 wrapper 2개를 설치한다:

1. `_collect_vision_fault_context` tee — kwargs **무변경** 통과(at_seconds 는 collect 내부
   full-video 호출 소관, **at_seconds=None 불변**), 반환 ctx 에서 collection_status +
   supported `_faultKey` + pointed 관절만 캡처. **전 12 멤버** (success 포함).
2. `_build_deduction_measured_deviations` tee — `seed_audit_out` dict 주입(25-01 관측
   전용 kwarg, production 미전달·부작용 0) → `{pointed, window_joints, fallback_joints}`
   캡처. measured substrate/채점 경로 무접촉.

## 실행

```bash
# pod-free 게이트 (exit 0 = PASS; artifact 부재 게이트는 SKIPPED)
cd backend && PYTHONPATH=shared/python:. python3 evals/phase25/assert_gates.py

# 게이트 단위 테스트 (합성 fixture, AWS/GPU/Gemini 불필요)
cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_phase25_eval_gates.py -q
```

### Pod 운영 절차 (repo 오염 방지 — 25-SWEEP-EVIDENCE 근본원인 4)

2026-07-02 FAIL run 의 sweep 산출물이 pod network volume 의 `evals/phase24/baseline/*.json`
을 덮어써(kip-up 50, peter-pan 0), 이후 게이트가 **오염된 기준**으로 판정했다. 재발 방지
구조 + 절차:

1. **신규 산출물 = repo 밖.** `run_sweep.py` 는 `$EVAL_OUT_DIR`(기본
   `/tmp/sunity_eval_out`) 아래 `phase25/` 에만 쓴다. `EVAL_OUT_DIR` 이 repo 안을
   가리키면 run_sweep 이 즉시 중단한다.
2. **비교 기준 = git 커밋본.** `assert_gates.py` 는 신규 산출물(phase25 report/
   breakdowns/warm)을 같은 `$EVAL_OUT_DIR` 에서 읽고, 방향-비교 기준(phase24 baseline)은
   **항상 repo 내 `evals/phase24/baseline/phase24_sweep_report.json`(커밋본, read-only)**
   에서 읽는다 — 신규 산출물과 기준의 물리적 분리.
3. **sweep 전 repo clean 확인 (pod 필수).**

   ```bash
   cd /workspace/SunityMotion && git status --short backend/evals/
   # modified 가 보이면 = 과거 run 오염 → 커밋본 복원:
   git checkout -- backend/evals/
   ```

4. **승격(커밋 baseline 갱신)은 명시적으로만.** 게이트 PASS + belle 승인 후:

   ```bash
   cp $EVAL_OUT_DIR/phase25/phase25_*.json backend/evals/phase25/baseline/
   # 이후 로컬에서 검토 + 커밋 (sweep 이 자동으로 커밋본을 건드리는 경로는 없음)
   ```

### Pod sweep (RTMW GPU + Gemini env — phase24 헤더 승계, SERIAL 필수)

```bash
source /workspace/aws_env.sh && \
export CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key GEMINI_COACH_ENABLED=1 \
       RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx \
       YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx RTMW_DEVICE=cuda \
       FIREBASE_SA_PATH=/workspace/firebase-sa.json RECOGNIZER_BACKEND=gemini && \
export GEMINI_API_KEY=$(python3 -c "import boto3;print(boto3.client('ssm',region_name='ap-northeast-2').get_parameter(Name='/sunity/motion/gemini-api-key',WithDecryption=True)['Parameter']['Value'])") && \
cd /workspace/SunityMotion/backend && \
PYTHONPATH=shared/python:. python3 evals/phase25/run_sweep.py &&            # 1) cold
PYTHONPATH=shared/python:. python3 evals/phase25/run_sweep.py --tag warm && # 2) warm 재실행
PYTHONPATH=shared/python:. python3 evals/phase25/assert_gates.py            # 3) 게이트
```

vision veto env 2종(`GEMINI_VISION_VETO_ENABLED=1`, `GEMINI_MAX_VETO_WALL_S=300`)은
run_sweep 이 module-level setdefault 로 자동 주입하므로 별도 export 불필요 —
production `/workspace/start_server.sh` 박제 구성(2026-07-02 FP 재발 사고 fix) mirror.
함정: 2026-07-05 신규 pod(svn31pzja7uay0)에서 이 env 누락으로 veto 경로가 조용히 OFF
되어 sweep 1차가 통째로 무효(visionVeto disabled + deductionBreakdown 없음 + 레거시
min-of-core 점수)가 됐다 — setdefault 가 그 재발을 구조적으로 차단한다. 명시 export
시 그 값이 우선한다 (아래 "RTMW 결정론 모드" 섹션의 setdefault 패턴과 동일).

### cold / warm 구분 + 크레딧 요건 (T-25-10)

- **cold** (기본): PROMPT_VERSION v10.1 + AGGREGATION_VERSION agg3 bump 로 rich 캐시
  **전량 miss** → 12 멤버 × 3 call = **36 Gemini pro call** + 멤버당 영상 2 업로드.
  실행 전 belle 크레딧 확인 필수 ([[gemini-credits-depleted-2026-06-20]] — 429 고갈 이력).
  429/resource_limited 발생 시 **fail-closed 중단** 후 belle 보고.
- **warm** (`--tag warm`): 동일 커맨드 재실행 — 캐시 hit 로 Gemini **0 call**.
  `*_warm.json` 기록 → `check_cold_warm_determinism` 입력 (verdict/breakdown 동일성 =
  결정론 게이트).

### RTMW 결정론 모드 (근본원인 #2 엔지니어링 해법)

run_sweep 은 module-level 에서 `RTMW_DETERMINISTIC=1` 을 **스스로 setdefault** 한다 —
eval 은 항상 결정론 모드 (pod 에서 별도 export 불필요). RTMWPoseEngine 이 이 env 를
보고 onnxruntime CUDA EP 의 비결정 요소를 세션 생성 시점에 고정한다
(`cudnn_conv_algo_search=DEFAULT` 로 EXHAUSTIVE 벤치마크의 run-to-run conv algo flip
제거 + `CUBLAS_WORKSPACE_CONFIG=:4096:8` + intra/inter_op 스레드 1 —
근거/한계는 `sunity_shared/analysis/pose_engines/rtmw/ort_determinism.py` docstring).
프로덕션(env 미설정)은 patch 0 으로 기존과 byte-동일. 명시적으로
`export RTMW_DETERMINISTIC=0` 하면 비결정 baseline A/B 재현 가능.
**한계**: CUDA EP 는 완전 bitwise 결정론 미보장 — 잔여 변동은 cold/warm 실측
(`check_cold_warm_determinism`)으로 판단한다.

산출물은 `$EVAL_OUT_DIR/phase25/` 에 기록된다 (`phase25_sweep_report.json` +
`phase25_breakdowns.json` + `*_warm.json`) — repo 내 `baseline/` 은 승격 절차(위
"Pod 운영 절차" 4)로만 갱신·커밋한다.

## 객관성 (D-06 / [[analysis-objectivity-no-human-scores]])

게이트는 사람 점수 라벨을 ground truth 로 절대 쓰지 않는다. fault 라벨=영상 파생.
점수 비교는 전부 채점기 자신의 결정론 출력(phase24 baseline artifact) 대비 방향
비교이며, 보유 영상에 점수를 짜맞추는 curve-fit 수정은 금지 — FAIL 시 구조 원인
(짚기 미발화/과확장/캐시)만 후속 대상으로 박제하고 belle 판단을 요청한다.
