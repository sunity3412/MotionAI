# Phase 29 — D-02 mode3 tally 전환 게이트 (29-05)

29-02 는 mode3_held tally seam(등록 동작 md 보유 시 deductionBreakdown 방출 +
overallScore == final 항등)을 코드로만 랜딩했고 Pod 는 구코드다. 이 디렉터리는
정은지 페어셋(phase24 6페어)을 **mode3 단독 분석**으로 돌려 그 전환이 실영상에서
지는지 판정하는 최종 게이트다 — **게이트 PASS 후에만 Pod 서버를 재기동해
production 을 신코드로 전환한다** (D-02 전환 조건).

phase25 harness 복제-확장 (같은 계보 3대째). 규율 승계: SERIAL / EVAL_OUT_DIR /
baseline read-only / cold·warm / 점수 리터럴 0 / 자기 sweep 재보정 금지.

## 게이트 (`assert_gates.py` — exit 0 = PASS, artifact 부재 = SKIPPED)

| 함수 | 무엇을 증명 | 비고 |
|---|---|---|
| `check_success_members` | success 멤버 감점 record 0 AND overallScore >= 기존(preSeam) | ">= 기존" 은 clean tally 100 승격 허용 — 수용 여부는 정지 조건(belle)이 별도 판정 |
| `check_powerspin_fault` | power-spin fault 에 leg_extension 계열 record >= 1 | 유일한 criteria 보유 동작 — 변별 실증 |
| `check_fallback_identity` | kip-up/peter-pan/elbow-twist-sister/pdshape fault: breakdown 미방출 + 점수 항등 | Pitfall 1: 이 4동작 무감점 = 정상 (빈 criteria yaml) |
| `check_cold_warm_determinism` | cold vs warm 전 키 status/score/records 동일 | `*_warm.json` 부재 시 SKIPPED |
| `check_breakdown_identity` | 방출 키: overallScore == final == max(0, round(100 + Σ points)) | phase24 `check_traceability` import 재사용 |
| `check_mode3_held_status` (보조) | done 멤버 전원 visionVeto.status == 'mode3_held' | 'applied' 오염 0 (29-02 결정) |

**"기존 baseline" 소스:** mode3 는 커밋 baseline artifact 가 없다. run_sweep 의
read-only tee 가 `_apply_vision_veto_from_context` 진입 시점의 `overallScore`
(`preSeamOverall`)를 캡처한다 — 29-02 seam 은 종단 in-place 교체/byte-불변
passthrough 뿐이므로 이 값이 정확히 구코드가 저장했을 점수다 (자기 sweep 재보정
아님: 비교 기준은 seam 이전 단계 = 구코드 동일 경로의 값).

**특정 점수 리터럴 assert 금지 (locked):** 게이트 소스에 점수 타깃 하드코딩 0.
100/0 은 tally 항등식 상수로만 등장. 사람 점수 라벨 0. 밴드 0.

## mode3 전용 조정

- eval_keys.json: phase24 6페어 → `mode: "mode3"`, referenceMotionId 없음.
  **prev 없는 단독 분석**(절대 기준 채점)이 D-02 본체 — run_sweep 이 멤버별 고유
  uid 를 써서 `get_previous_analysis`(uid-scoped)가 prev 를 못 잡게 보장한다.
- not_pole 게이트는 mode3 미적용 — climb 관련 mode1 게이트는 포함하지 않는다.
- mode3 의 Gemini 호출 = recognizer 1회뿐 (collect 는 mode3_held 조기 bail).
  TechniqueCache(영상 hash, Firestore 영속) hit 시 0 call.

## 실행 (Pod — SERIAL 필수)

사전 확인:

1. **push 먼저** (gsd-pod-work-push-first): 29-02/29-03/29-05 커밋이 origin/main 에
   있는지 확인 후 Pod 에서 `cd /workspace/SunityMotion && git pull`.
2. **Gemini 크레딧** ([[gemini-credits-depleted-2026-06-20]]): recognizer 1회 x 12멤버
   x 2run 상한 (캐시 hit 시 0). 고갈이면 정지·보고 — sweep 강행 금지.
3. **repo clean 확인**: `git status --short backend/evals/` — modified 가 보이면
   과거 run 오염 → `git checkout -- backend/evals/` 로 커밋본 복원.

```bash
source /workspace/aws_env.sh && \
export CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key GEMINI_COACH_ENABLED=1 \
       RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx \
       YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx RTMW_DEVICE=cuda \
       FIREBASE_SA_PATH=/workspace/firebase-sa.json RECOGNIZER_BACKEND=gemini && \
export GEMINI_API_KEY=$(python3 -c "import boto3;print(boto3.client('ssm',region_name='ap-northeast-2').get_parameter(Name='/sunity/motion/gemini-api-key',WithDecryption=True)['Parameter']['Value'])") && \
cd /workspace/SunityMotion/backend && \
PYTHONPATH=shared/python:. python3 evals/phase29/run_sweep.py &&            # 1) cold
PYTHONPATH=shared/python:. python3 evals/phase29/run_sweep.py --tag warm && # 2) warm
PYTHONPATH=shared/python:. python3 evals/phase29/assert_gates.py            # 3) 게이트
```

- veto env 2종(`GEMINI_VISION_VETO_ENABLED=1`, `GEMINI_MAX_VETO_WALL_S=300`)은
  run_sweep 이 module-level setdefault 로 자동 주입 — production start_server.sh
  박제 구성 mirror (2026-07-05 신규 pod env 누락 사고 재발 방지).
- **동시 실행 절대 금지** — 파이프라인 동시성 비안전
  ([[pipeline-not-concurrency-safe-eval-serial]]). cold 완주 → warm 완주 → assert 순.
- 산출물: `$EVAL_OUT_DIR/phase29/` (기본 `/tmp/sunity_eval_out`) — repo 안이면
  run_sweep 이 즉시 중단 (커밋 baseline 오염 차단).

## PASS 이후 절차 — score-switch 가시성 + 정지 조건 (29-PLAN-REVIEW MEDIUM-1)

assert 후 PASS/FAIL 무관하게 29-05-SUMMARY.md 에 키별 대조표를 박제한다:

| 키 | 기존(preSeam) | 신(tally.final) | records 수 | criterion id | coverage/fallback | visionVeto | cold==warm |

**정지 조건:** clean(무감점) doc 의 final 이 단일 협소 criterion 통과 근거만으로
기존 대비 대폭 상승(예: 80대 → 100)하는 키가 있으면 — 게이트 PASS 여도 —
**Pod 재기동을 보류하고 checkpoint:decision 으로 belle 에 즉시 제시**한다
("criterion-clean = 100 수용" 여부는 제품 결정 — 무음 ship 금지). belle 승인
후에만 재기동.

재기동(PASS + 정지 조건 미발동/승인 후): `bash /workspace/start_server.sh`
(VETO 함정 영구 fix 경로 — 임의 uvicorn 직기동 금지) → `/health` 200 확인.

**FAIL 시:** 정지. 임계·criteria·게이트 기대치 수정 금지
(calibration-source-hard-gate + Pitfall 1) — FAIL 키·값·원인 가설을 SUMMARY 에
기록하고 blocker 보고. 서버 재기동 하지 않음 (구코드 유지 = 무회귀).
