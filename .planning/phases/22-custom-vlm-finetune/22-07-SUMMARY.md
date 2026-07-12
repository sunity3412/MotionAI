# 22-07 SUMMARY — SFT v1/v2 학습 + D-15 게이트 판정

## v2 재학습 (처방 A — belle 승인 2026-07-12, perturb 주입)

- 학습셋 v2 = perturb 95 + distill 87 + text 28 = 210행 (S3 canonical 갱신, v1 은
  jsonl_v1_distill_only/ 백업). 배선 커밋: 7b34038(loader)+cee2f0e(슬러그 폴백)+
  dc18cfa(**균등 게이트 트랙별 독립** — 합산 균형이 distill 85→38 잠식 실증 fix).
- 학습: 52 steps 3h22m, **train 0.3338 / val 0.1754** (v1 0.9423/0.3778 대비 대폭 개선).
  best = v5-20260712-075922/checkpoint-52 (+-merged bf16).
- **v2 게이트 = 여전히 FAIL** (base/require-pass exit 1):
  · eval18 짚기 / svg = FAIL 유지 — 예상대로 (처방 B·교사 프롬프트 보강 없이는 불가).
  · few-shot 결함 스팸 76항목 → 4항목으로 급감 (형식 규율 개선).
  · synthetic_holdout FAIL 유지 (0.0422 vs 0.0407, n=10). stage 분해:
    stage1 0.0005/0.0003, stage2 0.0041/0.0000, stage3 0.1347/0.1354(동률).
- **게이트 설계 결함 발견 (v1.1 fix 대상)**: holdout 비교가 비대칭 마스크 —
  무보정 기준선은 가림(NaN) 관절을 계측 제외하는데 보정본은 모델 복원값 포함.
  공통 가시 마스크 비교 + 가림 복원 L2 별도 관측치로 분리해야 공정. 단, stage3
  동률이라 fix 후에도 판정이 뒤집히진 않음 — 변위 보정 능력 자체가 아직 약함.
- v2 처방 후보: perturb 트랙 강도 분포 재조정(변위 위주 stage 비중↑) + 학습
  좌표-전용 샘플(영상 없는 synth 형식 — 게이트 입력과 양식 일치) 추가.

---

# (v1 기록 — 아래 원문 보존)

> **판정: 게이트 FAIL (기본 exit 1 / --require-pass exit 1) — Wave 5(22-08 서빙) 진입 불가 (DR-03).**
> FAIL 근본원인 = 하이퍼파라미터가 아니라 **학습 데이터 공백 3종** (아래) — 전부 22-04
> SUMMARY 가 기록한 한계와 일치. 게이트가 설계 목적대로 red 를 냄. belle 논의 항목 있음.

## 학습 실행 (Task 2)

- 백본 = Qwen/Qwen3-VL-8B-Instruct (22-BAKEOFF-RESULT PROVISIONAL, belle 구두 확인 2026-07-12)
- QLoRA rank64/alpha128, all-linear, bnb 4-bit, LR 1e-5 / ViT 2e-6 / aligner 1e-5(unfreeze),
  batch 1×accum16, max_length 32768, 4 epochs = 28 steps, A100 80GB 1h12m
- **train_loss 0.9423 → val eval_loss 0.3778** (val 2행 — 얇음, 22-04 한계 승계)
- best ckpt = `/workspace/phase22_sft_out/v4-20260712-003814/checkpoint-28` (+`-merged` bf16 병합본)
- 학습셋 = S3 training/phase22/jsonl (train 99: distill 85+text 14 / val 2,
  validation_owner=explicit_val_jsonl → --val_dataset 명시 소비, 내부 재분할 0)

### 학습 성립까지 걷어낸 잔돌 (전부 fix 커밋)
1. packing=flash-attn 필수 → packing off (샘플 ~20-30K tok = 32K 근접, packing 이득 0) — 0384c41
2. ms-swift 기본 ModelScope 허브 → USE_HF=1 (HF 캐시 17GB 재다운로드 차단) — 6871639
3. bitsandbytes 미설치 → 설치 0.49.2 (**T-22-SC "신규 pip 0" 이탈 #1** — QLoRA=D-06 잠금의 필수 의존)
4. 신형 torchvision read_video 제거 → FORCE_QWENVL_VIDEO_READER=decord (**이탈 #2**: decord 설치)
5. decord EAGAIN 코덱 21영상 → 로컬라이즈 h264/yuv420p 균일 재인코딩 (멱등) — a6d5087
6. JSONL content 타입 혼합(str/list/dict)이 Arrow 라운드트립에서 스키마 뒤틀림 →
   로컬라이즈가 ms-swift 표준형(전 content str + <video> + top-level videos, assistant=
   sort_keys 직렬화)으로 변환 — a6a750e. **후속: build_jsonl 이 처음부터 표준형을 방출하게
   수정 후보(v1.1)**

## 병합/양자화 (Task 2 후반)

- 16-bit 병합 = 완료 (swift 규약 경로 `<ckpt>-merged` 소비 fix — 4-bit 직접 병합 경로 없음 유지)
- **AWQ = 미완**: autoawq 가 `qwen3_vl isn't supported yet` (신 아키텍처 미지원, autoawq 는
  공식 deprecated·llm-compressor 로 이관). gptq 폴백도 optimum 부재로 불가.
  → **게이트는 bf16 병합본으로 실행** (순서 변경 deviation — 양자화는 배포 효율 문제로
  게이트 판정과 직교. AWQ 재시도 경로 = llm-compressor, 게이트 처방 결정 후).
- S3 체크포인트 업로드 = AWQ 산출 후로 이연 (acceptance 미충족 항목).

## D-15 게이트 판정 (Task 3)

artifact = bf16 병합본으로 run_bakeoff run1/run2 (judge 생략 — coaching 축 미소비, 과금 0).
`assert_gates --model <merged>` 기본/require-pass 둘 다 exit 1.

| 게이트 | 판정 | 근거 |
|---|---|---|
| synthetic_holdout | **FAIL** | 보정 L2 0.0462 vs 무보정 0.0452 — 개선 없음 (n=12) |
| motion_balance | PASS | 전 동작 계측 존재, kip-up 단독 아님 |
| eval18_no_regression | **FAIL** | 변별 4페어 전부 fault 멤버 결함 0건 (짚기 실패). kip-up/climb known 추적 유지 |
| determinism | PASS | run1/run2 verdict 동일 |
| traceability+monotonicity | **FAIL** | few-shot 에서 결함 스팸(1건 76항목)·라우팅 키 전무 |
| svg_spec_validity | **FAIL** | 결함 리포트 4건 중 wellformed 0건 |

### 근본원인 — 데이터 공백 3종 (전부 기지(旣知) 한계)

1. **fault 트랙 0행**: 수집 112영상 = 전부 정타(유튜브 정타 + IG 스튜디오) — 모델이
   "faults=[]" 만 학습. 결함 짚기 능력의 감독 신호 자체가 없음. (내부 371 fault 이월분)
2. **perturb 트랙 0행**: 좌표 보정 시범 부재 → corrected_coords 능력 없음.
   (22-01 perturb 엔진은 코드 완성 — assemble 주입만 안 됨)
3. **svg 감독 0/87**: 교사 리포트가 svg_spec 을 채우지 않았음 (22-04 기록).

### 하이퍼파라미터 스윕 1회 = 의도적 SKIP (deviation, 근거 기록)

플랜의 "FAIL 시 스윕 1회(LR/rank)"는 능력-경계 FAIL 전제다. 본 FAIL 은 감독 신호
부재(구조적)라 LR/rank 로 교정 불가 — 스윕 실행은 GPU 낭비이므로 생략하고 데이터
처방을 belle 논의로 승격한다.

## belle 논의 항목 (자동 진행 금지 — DR-03)

- **처방 A (추천)**: perturb 트랙 주입 재조립(코드 완성, 추가 라벨링 비용 0) + 재학습
  (~1.5h GPU) → synthetic_holdout/grounding 계열 해소 기대.
- **처방 B**: 내부 371 fault 영상 교사 라벨링(22-04 체인 재사용, Gemini 비용 발생)
  → eval18 짚기 능력의 유일한 데이터 처방. A 와 병행 가능.
- **처방 C (27B 승급, D-05)**: 비추천 — 데이터 공백은 모델 크기로 해소 안 됨.
- svg 감독: 교사 프롬프트에 svg_spec 작성 지시 보강 후 배치 재판독(부분) 또는 v1.1 이월.
- AWQ: llm-compressor 로 재시도 (게이트 처방 결정 후 — 배포 아티팩트 확정 시점에).

## 산출물

- backend/training/sft/run_sft.sh (9fa0a6c→a6a750e) / run_sft_gates.sh (878225c→113f7ff)
- backend/training/export/merge_and_quant.sh (dc50be9→725cff3 계열)
- backend/evals/phase22/assert_gates.py + tests 23건 (d1d8f95) — 전체 스위트 179 pass
- 게이트 artifact = Pod /workspace/eval_out/phase22/bakeoff_*checkpoint-28-merged*_run{1,2}.json
- 로그: /workspace/sft_run1.log, merge_quant.log, sft_gates.log
