# phase22 v6 — SFT 실행 런북 + 게이트 판정선 (belle Pod 기동 후)

> 작성: 2026-07-16 (assemble 진행 중 병행 준비). 목적 = assemble 끝나는 즉시 belle이 Pod
> 켜면 대기시간 0으로 SFT→판정. **이 문서는 판정 규칙이 핵심** — v6는 게이트 종료코드만
> 보면 설계상 오FAIL 난다(아래 §3).

---

## 1. Pod 기동 (belle 몫 — Claude는 RunPod API 키 없음)

- **GPU 우선순위** (EU-RO-1): 4090 → PRO 4500 → 5090 → PRO 6000 → A4500. (8B QLoRA는 4090 충분.)
- **Network Storage 필수** — 기존 볼륨(SFT v5 학습셋/HF 캐시/train_venv 생존분) 재부착.
  볼륨 붙이면 `/workspace/SunityMotion`, `/workspace/train_venv`, `/workspace/hf_cache` 재사용 → 셋업 시간 절약.
- 기동 후 belle이 **SSH 접속 정보(host/port)** 를 Claude에 전달 → 이하 Claude가 실행.

## 2. SFT 실행 (Claude가 SSH로)

```
cd /workspace/SunityMotion && git pull            # v6 코드(wq9)+assemble 스크립트 동기화
cd /workspace/SunityMotion/backend
# 학습셋은 S3 canonical(training/phase22/jsonl/)에서 run_sft.sh가 자동 동기화 — 이미 v6로 교체됨(260716-jg6).
nohup bash training/sft/run_sft.sh > /workspace/sft_v6.log 2>&1 &
```

- 백본 = `Qwen/Qwen3-VL-8B-Instruct` (bake-off 우승, PROVISIONAL). QLoRA 4bit(bnb).
- 프레임 예산: `FPS_MAX_FRAMES=32`, `VIDEO_MAX_PIXELS=448^2`. packing=false.
- 입력 계약: `train.jsonl`/`val.jsonl`/`_meta.json`, `_meta.validation_owner=explicit_val_jsonl`
  (val.jsonl 명시 소비, 내부 재분할 0). run_sft가 assert함 — v6 assemble이 이 owner 유지.
- 소요 ~3.5h. 산출 = `/workspace/phase22_sft_out/{run_id}/checkpoint-*` (LoRA 어댑터).
- **주의(과거 함정)**: `USE_HF=1`(ModelScope 재다운로드 회피), `FORCE_QWENVL_VIDEO_READER=decord`,
  S3 다운로드 단일스레드(MooseFS futex 데드락 회피, 커밋 17624d7) — run_sft.sh에 이미 반영.
- 시크릿 echo 금지. `/workspace/aws_env.sh` 자격 사용.

## 3. 병합/양자화 + 게이트 (SFT 완료 후)

```
bash training/export/merge_and_quant.sh   # 4bit 직접병합 금지, 이 스크립트가 병합/AWQ
# bake-off 하네스를 SFT 모델로 run1/run2(SERIAL) 재실행 → EVAL_OUT_DIR/phase22/bakeoff_*.json
# 그 후:
python3 evals/phase22/assert_gates.py            # base 모드
```
> vLLM flashinfer 오탐 회피(과거): `VLLM_USE_FLASHINFER_SAMPLER=0 TORCH_CUDA_ARCH_LIST=12.0`.

---

## ★ v6 게이트 판정선 (belle certainty — 이대로 읽을 것)

게이트는 7개 check. **종료코드(exit)만 보면 안 된다** — per-check로 해석:

| check | v5 결과 | v6 판정 규칙 |
|---|---|---|
| **eval18_no_regression** ★핵심 | **FAIL** — power-spin/peter-pan/elbow-twist-sister/pdshape 전부 "fault 멤버 결함 0건"(칭찬만) | **v6의 진짜 승부처.** 이 4페어가 `fault > success`로 결함을 짚으면 **v6 성공.** B+C1 재균형(결함신호 22%→40%)+terra가 정확히 이걸 targets. kip-up/climb는 known SKIP(추적만). |
| **synthetic_holdout** | FAIL — 보정 L2 0.0422 vs 무보정 0.0407(항등 echo, 개선 0) | **C1이 좌표교사(perturb)를 껐으므로 v6는 corrected_coords를 안 냄 → 이 check는 설계상 FAIL(또는 "보정 L2 0건"). "v6 실패"로 오독 금지 = 예상된 descope.** belle 결정(C1)의 직접 귀결. |
| **svg_spec_validity** | FAIL — wellformed 0/1 (<0.5) | v6가 특별히 targets하진 않음. 통과하면 보너스, FAIL이면 **2차 과제**(eval18만 뚫려도 v6는 방향 성공). 별도 판단. |
| **traceability/monotonicity** | (v1 로그: 라우팅 키 전무 다수) | 결함 항목에 body_part/fault_category 존재 + stage↑→faults 비감소. eval18과 연동해 봄. |
| **determinism** | — | cold 2회 verdict(fault_category set) 동일. 통과 기대. |
| **motion_balance** | — | 계측 동작 2+ (kip-up 단독 금지). 통과 기대. |

### 한 줄 판정
> **v6 성공 = eval18 4페어가 결함을 짚는다(fault>success).** synthetic_holdout FAIL은
> C1의 예상된 귀결이라 무시. svg_spec은 2차. → assert_gates 종료코드가 아니라
> **eval18 라인을 직접 읽어 판정.**

### v6가 eval18도 FAIL이면 (진단 분기)
데이터 조정(밀도/재균형/terra)으로도 결함 인지가 안 뚫린 것 = 어젯밤 결론("데이터로는
크게 못 올린다")의 최종 확증. 다음 후보 = 용량↑(30~32B, 볼륨 디스크쿼터 이슈 있음) 또는
감독 방식 재formulation(H2: 감독>용량). belle 도메인 결정 필요.

---

## 4. 산출물 보존
- SFT 어댑터 → S3 `training/phase22/checkpoints/sft-v6-*/`
- 게이트 리포트/로그 → S3 `training/phase22/{eval_out,logs}/`
- v6 학습셋 = 이미 canonical `jsonl/` (pre-v6는 `jsonl_v5_backup/`).

## 5. Pod 정리
- 판정 끝나면 belle 콘솔에서 Stop(Claude는 Stop 불가). 네트워크 볼륨은 생존.
