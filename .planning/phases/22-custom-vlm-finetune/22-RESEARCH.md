# Phase 22: 자체 비전 모델 파인튜닝 (오픈 모델 전환) - Research

**Researched:** 2026-07-06
**Domain:** VLM 도메인 파인튜닝 (QLoRA SFT → Cascade RL) + 데이터 엔진 + shadow 배포/swap
**Confidence:** HIGH (프레임워크·서빙·패턴) / MEDIUM (하이퍼파라미터) / LOW (합성 교란 수치)

> 근거 우선순위 (belle 지시, 변경 불가): **22-NLM-EXTRACT.md(2026 노트북) > 이 문서의 실측 검증 > 24년 훈련데이터 지식.** 이 문서는 NLM 추출본의 "상충/불확실 9건"을 닫거나 planning decision 으로 명시 이관하는 역할이다. 본문에서 `[CITED: NLM §n]` = 22-NLM-EXTRACT.md 해당 절.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**v1 태스크 범위 (belle 직접 논의 — "단순 출력 금지" 푸시백 반영)**
- **D-01 (통합 리포트 v1):** Phase Boundary의 5출력(CoT 보정 좌표 / 결함 짚기·측정대상 / 시간 앵커+sub-action 구간 분할 / SVG 시각 스펙 / 코칭 shadow)을 단일 JSON 스키마로. temporal grounding·sub-action order·SVG 스펙·structured JSON dump는 v1 포함, 실루엣 이미지 편집·분할 마스크(<SEG>)·반복 카운팅은 v2, 하드웨어 행동 토큰·에이전틱 툴콜은 백로그(결정성 게이트와 충돌).
- **D-02 (코칭 단계적 소비):** 코칭 출력은 v1 학습에 포함하되 서비스 소비는 shadow(Cerebras와 병행 비교)로 시작, 품질 게이트(측정 사실 앵커 준수 + LLM judge + belle 확인) 통과 시 swap.
- **D-03 (v2 분리 근거 = 데이터 의존성):** 교정 실루엣 생성은 이미지 페어 0장이라 v1 불가. 외부 생성 API 운영(별도 phase) → 통과 품질분 적재 → v2 자체 생성 헤드(InternVL-U 아키텍처 차용, 자체 데이터 재학습). v1은 같은 백본에 어댑터/헤드 추가 가능한 구조로 설계.

**백본 선정·스케일**
- **D-04 (bake-off로 실측 결정):** Qwen 3.6 vs InternVL 3.5, 8B급 zero/few-shot 하네스로 좌표 보정+짚기 변별력 비교 후 확정. 둘 다 라이선스 클린(belle 2026-07-06 확정: InternVL 3.5 ≤38B = 코드 MIT+백본 Apache 2.0, Qwen 3.6 <35B = Apache 2.0, MMPose = Apache 2.0) — 성능만으로 선정. LLaVA 계열·InternVL-U 생성헤드 사용 금지.
- **D-05 (8B 시작, 27B 조건부 승급):** 8B급 시작. 27B는 8B가 정확도 게이트를 못 넘을 때만 승급.
- **D-06 (프레임워크 = ms-swift 주, Unsloth 보조):** QLoRA 4-bit, 전 선형 레이어 타겟, rank 64~128, gradient checkpointing, 8-bit AdamW. 배포 = 16-bit 병합 → AWQ/GPTQ 재양자화 → vLLM.
- **D-07 (SFT 먼저, RL 후속):** v1 = SFT까지. Cascade RL(MPO 웜업→GSPO 온라인, 보상 5종)은 SFT 게이트 통과 후 후속 plan.

**학습셋·라벨링 (Wave 0 — 모든 것의 선행)**
- **D-08 (시드 0기 = 보유 자산):** 정은지 13영상+일부러-실수 페어, 실사용 371건, 2026-07-06 실증 케이스(피터팬 위양성·power-spin), Phase 18 eval 라벨. **kip-up 편중 금지 — 학습셋·eval 모두 전 동작(+미보유 동작) 균등 구성.**
- **D-09 (유튜브 수집 확정):** 대회 영상=정타 버킷(IPSF 공식 아카이브 1순위), 튜토리얼 "흔한 실수" 세그먼트=fault 버킷. 출처 로그(provenance) + 학습 전용(재배포 금지).
- **D-10 (라벨 생성 3경로):** (a) 좌표 보정 = 합성 교란 주입 자가라벨, (b) 짚기/코칭 = Gemini 교사 증류 + LLM judge 필터(7점 미만 폐기) + 휴리스틱 필터, (c) **Gemini shadow 로깅 지금 시작.** 사람 숫자 점수 라벨 영구 금지(버킷만).
- **D-11 (JSON 규격 철칙):** 결측=Null 고정(키 삭제 금지)·키 알파벳 정렬·프롬프트 키 리스트 사전 바인딩·태스크 무관 관절 사전 필터·좌표 `<loc_NNN>` 이산화. T3 순수 텍스트 시간추론 합성 데이터 SFT 혼합 + 순수 텍스트 instruction 혼합.

**고객 데이터 플라이휠**
- **D-12 (동의 3겹):** 파일럿=학원 참가 동의서 포괄 / 정식=처리방침 고지+가명처리(얼굴 블러+식별자 제거) 후 학습 활용 / 출시 전 법률 검토 1회 문서화. 고지 문구는 온보딩 phase, 수집·가명처리·적재 파이프라인은 Phase 22 안.

**전환·서빙 전략**
- **D-13 (shadow 병행 기본):** 같은 입력을 양쪽에 태워 verdict 비교 로그 축적, 역할별 게이트 통과 시 swap. 순서: veto → recognizer → coach.
- **D-14 (서빙 위치):** 기존 4090 Pod에 vLLM(AWQ 4-bit) 추가가 기본, VRAM 충돌 시 별도 pod. 부수효과: Gemini File API 라운드트립 소멸 → Phase 27 기여.
- **D-15 (출하 게이트):** Phase 24의 4종(추적성·단조성·결정성·일반화) + EVAL18 6페어 무회귀 + 전 동작 균등 검증(미보유 포함) + shadow 대비 "Gemini 이상" 증명. eval/batch 순차 실행.

**실행 순서**
- **D-16:** Wave 0 데이터 엔진 → Wave 1 bake-off → Wave 2 SFT v1+eval 게이트 → Wave 3 shadow 배포→순차 swap → Wave 4 Cascade RL(후속 plan). 교정 시각물은 별도 phase(병렬, 앱 트랙).

### Claude's Discretion
- bake-off 하네스 설계, 프레임 샘플링/토큰 압축 파라미터, 학습 하이퍼파라미터, vLLM 서빙 구성, 수집 파이프라인 구현 세부. 학습 GPU 임대(RunPod)는 진행하며 belle 알림.

### Deferred Ideas (OUT OF SCOPE)
- 교정 시각물 phase (신규, 앱 트랙, Phase 22와 병렬) — 기하 오버레이 렌더 + 외부 생성 API 프로토타입.
- v2 — 자체 생성 헤드(InternVL-U 아키텍처 차용) / 분할 마스크 / 반복 카운팅.
- 백로그 — 하드웨어 행동 토큰, 에이전틱 툴콜, mmWave 레이더.
- 종목 확장(폴 외) — 스키마는 일반화형, 학습·검증은 폴 먼저.
</user_constraints>

<phase_requirements>
## Phase Requirements

phase 요구 ID는 plan에서 신설(FT-xx) 지시 — 아래는 연구가 지지하는 제안 골격이다. planner가 최종 mint한다.

| ID | Description | Research Support |
|----|-------------|------------------|
| FT-01 (모델선정) | Qwen 3.6 vs InternVL 3.5 8B zero/few-shot bake-off로 백본 확정, 변별력 4축(grounding L2/시계열/JSON 준수/코칭 논리) 계측 | §Bake-off 하네스 설계, ms-swift 4.4.0이 두 백본 모두 공식 지원 확인(README 명시), phase24 run_sweep 골격 재사용(PATTERNS analog 5) |
| FT-02 (학습셋) | Wave 0 데이터 엔진: 보유 자산 시드 + 유튜브 수집(provenance) + 전 동작 균등 매니페스트 | §유튜브 수집 파이프라인, yt-dlp 2026.7.4 검증, upload_phase15_dataset.py 비-notified prefix 패턴 |
| FT-03 (라벨링) | 3경로 라벨 생성(합성 교란/Gemini 증류+judge 필터/shadow 로깅), 사람 점수 라벨 0 | §합성 교란 설계(실 RTMW 오류 분포 우선), §Gemini 증류(File API 삭제 규율), D-11 JSON 규격 단일 owner 모듈 |
| FT-04 (학습·평가) | ms-swift QLoRA SFT(8B) + SFT 게이트(Phase 24 4종+EVAL18 무회귀) 통과 | §SFT 레시피(검증된 ms-swift 4.4.0 파라미터), §Validation Architecture, 4-bit 병합 함정 회피 수순 |
| FT-05 (swap 게이트) | shadow 병행 배선(veto→recognizer→coach) + 역할별 swap 게이트 + vLLM 동거 서빙 | §vLLM 동거 실행 순서, PATTERNS analog 2(env-switch seam)/4(shadow 로깅), 무음실패 금지 status enum |
| FT-06 (라이선스) | 학습셋 provenance 로그 + 모델/데이터 라이선스 감사 문서(DD 대비) | D-04 확정 라이선스(잠금), 수집 매니페스트 스키마, InternVL-U/LLaVA 금지 fence |
</phase_requirements>

## Summary

이 phase의 계획 리스크는 세 덩어리였다: (1) 프레임워크 정합(ms-swift가 MPO/GSPO를 실제 지원하는가), (2) 데이터 정합(9fps RTMW 좌표와 VLM 프레임 샘플의 시간 인덱스 정렬), (3) 운영 정합(4090 한 장에서 vLLM 동거). 이번 조사로 (1)은 **완전 해소** — ms-swift 4.4.0(2026-07-06 릴리스)은 MPO를 `rlhf_type=dpo` + 복수 `loss_type` + `loss_weights` 조합으로, GSPO를 GRPO의 `--importance_sampling_level sequence`로 공식 문서에 명시 지원한다. XTuner+verl 분기는 폐기 가능(폴백으로만 기록). D-07 "SWIFT 주" 전제는 SFT와 RL 양쪽에서 성립하며, v1=SFT까지이므로 RL 세부 레시피는 Wave 4 후속 plan으로 안전하게 미룬다.

(2)는 코드베이스 자체 실증이 정답을 이미 갖고 있다: 260705-h5z에서 "파이프라인 9fps 프레임 배열의 인덱스 페어 = 6/6 발화, 스코어러 자체 재추출+비율 근사 = 0/6(위상 불일치)"이 실측됐다. 따라서 VLM 입력 프레임은 **원 영상 재추출 금지, 기존 9fps 배열에서 인덱스 서브샘플**로 뽑고, RTMW JSON도 정확히 그 인덱스 행만 제공하며, `frame` 필드 = 9fps 원 인덱스를 시간의 canonical key로 삼는다(타임스탬프 = idx/9.0). 정렬은 설계상(by construction) 보장된다.

(3)은 vLLM 공식 플래그로 해결 경로 확인: `--gpu-memory-utilization`(기본 0.9 → 0.35~0.5로 제한), `--max-model-len` 상한 강제, `--limit-mm-per-prompt '{"video":1}'`, AWQ 양자화 공식 지원. 단 현행 Pod의 NLF+RTMW 상주 VRAM 실측치가 미지수이므로 "측정 먼저 → vLLM 예산 배정 → OOM 시 별도 pod(D-14 내장 폴백)" 순서를 plan에 박아야 한다. 유튜브 수집은 yt-dlp 2026.7.4(현행 유지보수 활발) + `--write-info-json` 메타데이터 사이드카를 provenance 원장으로 쓰고, 기존 `upload_phase15_dataset.py`의 비-notified prefix 규율을 그대로 복사한다.

**Primary recommendation:** Wave 0을 "데이터 스키마 단일 owner 모듈 + shadow 로깅 즉시 가동 + Pod VRAM 실측"으로 시작하고, SFT/RL은 ms-swift 4.4.0 단일 프레임워크로 통일하라. `<loc_NNN>` 어휘 확장은 v1 기본에서 제외(3자리 정수 이산화로 시작)하고 ablation으로만 검증하라 — QLoRA 병합·재양자화 파이프라인 복잡도가 이득을 앞선다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 유튜브 수집 + provenance 매니페스트 | 로컬/스크립트 (backend/scripts) | S3 (fixtures/ 계열 비-notified prefix) | 일회성 배치, 트리거 미발화 필수. upload_phase15 전례 |
| 합성 교란 라벨 생성 | 순수 모듈 (sunity_shared/analysis 규율) | 스크립트 껍데기 (JSONL I/O) | numpy 단독·네트워크 0 규율. 어댑터 경계 패턴 동일 |
| Gemini 교사 증류 / shadow 로깅 | pipeline Lambda·Pod (기존 Gemini 경로에 부가) | Firestore (`vlm_shadow` 류 컬렉션) | shadow는 기존 verdict의 복제 저장만 — Gemini 재호출 0 |
| SFT/RL 학습 | RunPod 학습 Pod (신규 임대, `backend/training/`) | — | 학습은 서빙 Pod와 분리(VRAM·수명 주기). belle 알림 후 임대 |
| bake-off / SFT 게이트 eval | Pod (serial) + pod-free 게이트 (로컬 pytest) | `backend/evals/phase22/` | phase24 run_sweep/assert_gates 골격. eval은 순차 필수 |
| vLLM 서빙 (자체 모델 추론) | 기존 4090 서빙 Pod (별도 프로세스, localhost 포트) | 별도 pod (VRAM 충돌 시) | D-14. FastAPI가 토큰 인증 프록시, vLLM은 비공개 포트 |
| shadow 배선 / swap 토글 | pipeline (`app.py` 단독 소유 env) | `interfaces.py` Protocol | 토글은 pipeline 단독 소유 규율(PATTERNS analog 2) |
| verdict 비교 로그 저장 | Firestore Admin (backend 전용) | — | flat-dict 검증 + ms epoch 규율 |
| 학습셋/시크릿 | AWS S3 + SSM Parameter Store | Pod env 주입 | .env 하드코딩 금지 (CLAUDE.md §3) |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ms-swift` | 4.4.0 (2026-07-06) | QLoRA SFT + MPO/GSPO RL + `swift export`(병합·양자화) | D-06 잠금. Qwen3.6·InternVL3.5 공식 지원 명시(GitHub README), MPO=dpo+복수 loss_type, GSPO=GRPO `importance_sampling_level sequence` 공식 문서 [VERIFIED: PyPI + swift.readthedocs.io] |
| `vllm` | 0.24.0 (2026-06-30) | AWQ 4-bit 서빙 + (Wave 4) GSPO rollout 백엔드 | D-06/D-14 잠금. `--quantization awq`, `--gpu-memory-utilization`, `--limit-mm-per-prompt` 공식 플래그 [VERIFIED: PyPI + docs.vllm.ai] |
| `yt-dlp` | 2026.7.4 (2026-07-04) | 유튜브 수집(D-09) + `--write-info-json` 메타데이터 사이드카 | 사실상 유일한 유지보수 활발 다운로더. 릴리스 주기 월 1회+ [VERIFIED: PyPI, slopcheck OK] |
| Qwen 3.6 VL 8B급 | bake-off 대상 | 백본 후보 A | D-04 잠금. Apache 2.0 <35B (belle 확정 — 재검토 금지). ms-swift 지원 모델 목록 등재 [CITED: NLM §5·§11 + D-04] |
| InternVL 3.5 8B | bake-off 대상 | 백본 후보 B | D-04 잠금. 코드 MIT+백본 Apache 2.0 (belle 확정). ViR 토큰 압축(-Flash) = 영상 태스크 가산점 [CITED: NLM Q2 + D-04] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lmms-eval` | 0.7.2 (2026-06-24) | 표준 VLM 벤치마크 러너 | bake-off 보조(MotionBench류 sanity). 주 하네스는 자체 run_bakeoff [VERIFIED: PyPI, slopcheck OK] |
| `unsloth` | 2026.6.9 | QLoRA 보조 프레임워크 (D-06 "보조") | ms-swift가 막힐 때 폴백. 멀티모달 커버리지는 ms-swift가 넓음 [VERIFIED: PyPI, slopcheck OK] |
| `autoawq` | 0.2.9 (2025-05-11) | AWQ 체크포인트 생성 (`swift export` 내부 의존) | 14개월 무릴리스 — 유지보수 정체 신호. `swift export --quant_method awq`로 간접 사용, 직접 의존 최소화 [VERIFIED: PyPI, slopcheck OK] [ASSUMED: 유지보수 상태] |
| `torch`/CUDA | Pod 베이스 이미지 제공 | 학습·추론 런타임 | 기존 규율(핀 안 함) 유지 |
| Gemini API (`gemini-3.1-pro-preview`/`gemini-3.5-flash`) | 기존 키 | 교사 증류 + shadow 비교 상대 | 기존 gemini_vision_scorer 인프라 재사용. 모델 string은 메모리 [[gemini-latest-model-versions]] 준수 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ms-swift (MPO/GSPO) | XTuner(MPO)+verl(GSPO) — InternVL 공식 경로 | ms-swift 단일화가 D-07과 정합·운영 단순. InternVL GitHub `internvl_chat/shell/.../mpo` 스크립트는 폴백으로만 기록 [CITED: NLM Q4] |
| 자체 run_bakeoff 하네스 | VLMEvalKit / lmms-eval 전면 채택 | 표준 벤치는 우리 태스크(좌표 보정 JSON)를 못 잼. 커스텀 태스크는 자체 하네스가 정답, 표준 툴킷은 sanity 보조 |
| autoawq 직접 호출 | `llm-compressor` (vLLM 계열 공식 양자화 툴) | autoawq 정체 시 대체 경로. Wave 2 배포 시점에 `swift export` 성공 여부로 판단 [ASSUMED] |
| vLLM 동거 (4090 한 장) | 별도 서빙 pod | D-14가 이미 폴백 내장. 동거 실패 판정 기준 = 실측 OOM/지연 |

**Installation (학습 Pod):**
```bash
pip install "ms-swift[all]" vllm lmms-eval
pip install yt-dlp   # 수집 머신(로컬 또는 Pod)
```

**Version verification:** 전 패키지 PyPI 실측 완료(2026-07-06): ms-swift 4.4.0 / vllm 0.24.0 / yt-dlp 2026.7.4 / unsloth 2026.6.9 / lmms-eval 0.7.2 / autoawq 0.2.9.

## Package Legitimacy Audit

slopcheck 0.6.1 실행 완료 (2026-07-06).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| ms-swift | PyPI | 2023~ (활발) | 대규모 | github.com/modelscope/ms-swift | [OK] | Approved |
| vllm | PyPI | 2023~ | 대규모 | github.com/vllm-project/vllm | [OK] | Approved |
| yt-dlp | PyPI | 2021~ | 초대규모 | github.com/yt-dlp/yt-dlp | [OK] | Approved |
| unsloth | PyPI | 2023~ | 대규모 | github.com/unslothai/unsloth | [OK] | Approved |
| lmms-eval | PyPI | 2024~ | 중규모 | github.com/EvolvingLMMs-Lab/lmms-eval | [OK] | Approved |
| autoawq | PyPI | 2023~ | 대규모 | github.com/casper-hansen/AutoAWQ | [OK] | Approved (유지보수 정체 주의 — 간접 사용) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[Wave 0 데이터 엔진]
  유튜브(yt-dlp + info.json) ──┐
  보유 자산(정은지 13 + still 페어 + 371건) ──┤
                                ▼
              S3 fixtures/phase22/ (비-notified prefix)
                                │ 매니페스트(JSON: key/motion/bucket/provenance)
                                ▼
  ┌─ (a) 합성 교란 생성기(순수 모듈) ─→ 좌표보정 JSONL (정답=원좌표)
  ├─ (b) Gemini 교사 증류(File API 업로드→호출→삭제) ─→ judge 필터(<7 폐기) ─→ 짚기/코칭 JSONL
  └─ (c) 프로덕션 shadow 로깅: _apply_vision_veto verdict 복제 ─→ Firestore vlm_shadow ─→ 증류 라벨 적재
                                │
                                ▼
[Wave 1 bake-off]  run_bakeoff.py (serial, Pod) : Qwen3.6-VL-8B vs InternVL3.5-8B
   zero/few-shot → 4축 계측(grounding L2 / 시계열 / JSON 준수 / 코칭 judge) → 백본 확정
                                │
                                ▼
[Wave 2 SFT]  ms-swift QLoRA(4-bit, 전 선형, r=64~128) on 학습 Pod
   → 16-bit 병합(--merge_lora true) → AWQ 재양자화 → 체크포인트 S3
   → assert_gates.py: Phase24 4종 + EVAL18 무회귀 + 전 동작 균등
                                │
                                ▼
[Wave 3 shadow → swap]
  앱 → Lambda(upload-url) → S3 uploads/ → SQS → pipeline _process (RunPod 위임)
       └ Pod: RTMW 9fps 좌표 ─→ ┌ Gemini (현행 판정 경로, 불변)
                                └ vLLM :8001 (localhost, AWQ 자체모델) ─ shadow
              verdict diff ─→ Firestore vlm_shadow (분석 실패 절대 유발 금지)
       swap 게이트 통과 → env 토글(pipeline 단독 소유): veto → recognizer → coach 순
                                │
                                ▼
[Wave 4 후속 plan]  Cascade RL: MPO(rlhf_type=dpo + loss_type 혼합) → GSPO(GRPO + importance_sampling_level=sequence, vLLM rollout)
```

### Recommended Project Structure

```
backend/
├── training/                     # 신규 — 학습 코드 (PATTERNS 제안 승인: /ml 은 문서 전용, 코드 금지)
│   ├── datagen/
│   │   ├── perturb.py            # 합성 교란 순수 모듈 (numpy 단독, D-10a)
│   │   ├── schema.py             # D-11 JSON 규격 단일 owner (Null 고정·알파벳 정렬·관절 필터·이산화)
│   │   └── build_jsonl.py        # JSONL 조립 스크립트 껍데기 (I/O 분리)
│   ├── distill/
│   │   └── gemini_teacher.py     # 교사 증류 배치 (File API 업로드→삭제 규율)
│   ├── sft/
│   │   └── run_sft.sh            # ms-swift CLI 호출 (Pod 실행 헤더 docstring 규율)
│   └── export/
│       └── merge_and_quant.sh    # 16-bit 병합 → AWQ → vLLM 검증
├── scripts/
│   └── collect_phase22_youtube.py  # yt-dlp 수집 + provenance 매니페스트 (upload_phase15 골격)
├── evals/phase22/
│   ├── run_bakeoff.py            # Wave 1 (run_sweep 골격, SERIAL, EVAL_OUT_DIR repo-밖)
│   ├── assert_gates.py           # D-15 게이트 (phase24 확장, importable check_*)
│   └── fixtures/manifest.yaml    # 전 동작 균등 매니페스트 (pairs.yaml 전례)
├── shared/python/sunity_shared/analysis/
│   ├── interfaces.py             # 수정 — VLM judge Protocol 추가
│   └── vlm_judge.py              # 신규 — 자체 모델 어댑터 (vLLM HTTP, graceful)
└── functions/pipeline/app.py     # 수정 — shadow 배선 + env 토글 (단독 소유)
```

### Pattern 1: 시간 인덱스 정렬 — "9fps 배열 인덱스 서브샘플" (연구 focus #2의 답)

**What:** VLM 입력 프레임과 RTMW 좌표 JSON의 시간 정렬을 설계상 보장하는 방법.
**When to use:** 학습 JSONL 생성·bake-off·서빙 추론 전부 (단일 규칙).

핵심 규칙 — **원 영상 재추출 절대 금지. 기존 파이프라인 9fps 프레임 배열에서 인덱스로만 선택한다.**

- 근거 (코드베이스 실증): 260705-h5z — 파이프라인 9fps 배열의 window/DTW 인덱스 페어는 6/6 발화, 스코어러 자체 raw 추출+비율 근사는 VFR 위상 불일치로 0/6. `_build_selected_frame_pair` 재사용이 fix였다. [VERIFIED: STATE.md quick task 260705-h5z]
- 설계:
  1. 파이프라인 frame_extractor 산출(9fps, 640px)이 유일한 프레임 소스. 10~30초 클립 = 90~270 프레임.
  2. VLM 프레임 예산 32~64장 [CITED: NLM Q2 — MotionBench 근거] → stride = ceil(T/64) 균등 서브샘플. 결함 시간 앵커가 이미 있으면(veto sourceFrameIndices) 해당 구간 밀도 가중은 ablation.
  3. RTMW JSON은 **선택된 인덱스의 행만** 제공(1:1). 각 행의 `frame` 필드 = 9fps 원 인덱스(canonical time key). 타임스탬프 = `frame / 9.0`.
  4. 모델 출력(보정 좌표·시간 앵커·구간 분할)도 같은 `frame` 인덱스 체계로 방출 → 파이프라인 역매핑 무손실.
  5. confidence 채널은 반드시 포함(occlusion CoT 진단 + Wave 4 보상 #4의 입력).
- 해상도: 프레임당 448×448 리사이즈(타일링 없음), Qwen 계열은 `longest_edge` 토큰 캡 필수 [CITED: NLM Q2].

이로써 NLM 상충 #6(9fps vs 32~64f 정합 미해결)은 **닫힘** — 서로 다른 시계가 아니라 같은 배열의 부분집합이므로 정렬 문제가 소거된다.

### Pattern 2: 좌표 이산화 — v1 = 3자리 정수, `<loc_NNN>` 어휘 확장은 ablation (NLM 상충 #4의 답)

**What:** D-11의 좌표 이산화를 QLoRA 파이프라인과 충돌 없이 구현하는 방식.
**Decision logic:**
- `<loc_NNN>` 특수 토큰 방식은 `modules_to_save=["embed_tokens","lm_head"]` 풀 학습이 필수(신규 토큰은 저랭크 어댑터만으로 학습 불가) [CITED: NLM Q5 — 단 이 부분은 NLM이 "노트북 외 지식"으로 자인한 절차] → 병합·AWQ 재양자화 파이프라인이 어댑터 단독보다 복잡해지고 VRAM도 증가.
- CogVLM은 어휘 확장 없이 **상대좌표×1000 = 000~999 3자리 정수 텍스트**로 grounding SOTA를 달성 [CITED: NLM Q5 — 소스 기반 부분]. 이산화(그리드 1000분할)의 이득은 유지하면서 토크나이저는 건드리지 않는다.
- **v1 기본 = 3자리 정수 이산화** (`"right_elbow": [125, 45]` 정규화 그리드). `<loc_NNN>` 어휘 확장은 Wave 2에서 소규모 ablation 1회로 토큰 수·정확도 차이를 실측한 뒤에만 승격.
- D-11의 나머지 철칙(Null 고정·알파벳 정렬·키 리스트 사전 바인딩·관절 필터)은 `training/datagen/schema.py` 단일 owner로 구현 — enum 단일-owner 규율(gemini_vision_scorer FAULT_CATEGORIES 전례)과 동일 정신.

### Pattern 3: MPO/GSPO ms-swift 경로 (연구 focus #1의 답 — RESOLVED)

**What:** D-07 Cascade RL의 프레임워크 분기 해소.
- **MPO:** ms-swift 공식 문서 — "여러 loss를 혼합(MPO 학습 등)하려면 복수 `loss_type`을 지정하고 `loss_weights`로 가중치 설정". 즉 `rlhf_type=dpo` 기반에 InternVL MPO 구성(선호 DPO + 품질 BCO + 생성 LM 손실)을 loss 혼합으로 재현한다. [VERIFIED: swift.readthedocs.io/en/latest/Instruction/RLHF.html]
- **GSPO:** ms-swift에 전용 문서 페이지 존재 — GRPO 학습에서 `--importance_sampling_level sequence` (기본 token=GRPO, sequence=GSPO). [VERIFIED: swift.readthedocs.io GSPO 페이지]
- **결론:** XTuner+verl 이중 스택 불필요. v1은 SFT까지(D-07)이므로 plan은 "RL은 ms-swift 내 검증된 경로 존재"만 박제하고 세부 레시피는 Wave 4 후속 plan으로. 폴백(InternVL 공식 `internvl_chat/shell/.../mpo` 스크립트)은 문서에만 기록.

### Pattern 4: vLLM 동거 실행 순서 (연구 focus #4의 답)

**What:** 4090 24GB 한 장에서 NLF/RTMW + vLLM(AWQ 8B) 동거.
**실행 순서 (plan의 태스크 순서로 그대로):**
1. **실측 먼저:** 현행 서빙 Pod에서 분석 1건 돌리는 동안 `nvidia-smi` 피크 VRAM 기록 (NLF TorchScript + RTMW onnxruntime + YOLO 상주분). 이 수치가 vLLM 예산의 입력.
2. vLLM을 **별도 프로세스**로 기동 (FastAPI `--workers 1` 불변): `vllm serve <awq-model> --quantization awq --gpu-memory-utilization 0.35~0.5 --max-model-len 32768 --limit-mm-per-prompt '{"video":1}' --port 8001` (localhost 바인드, 외부 비공개 — FastAPI가 토큰 인증 프록시). AWQ 8B ≈ 로드 6~7GB + KV 캐시 [CITED: NLM Q6] [VERIFIED: 플래그 자체는 docs.vllm.ai].
3. 기동 순서: 기존 파이프라인 웜업(NLF 로드) **후** vLLM 기동 — vLLM은 기동 시점 가용 VRAM 기준으로 선점하므로 순서가 바뀌면 NLF가 OOM.
4. health 통합: server.py `/health`에 `vllm_loaded` 필드 추가(기존 패턴), start_server.sh 수정은 **Volume 쪽에 반영** (Pod 재생성 함정 — [[current-pod-hbpvhedq2bu01i]]).
5. 실패 판정 기준을 수치로 박제: 분석 1건+shadow 추론 동시 수행 시 OOM 발생 또는 분석 지연이 shadow 없음 대비 +20% 초과 → D-14 폴백(별도 pod) 즉시 전환.

### Pattern 5: shadow 배선 (PATTERNS 승계 — 요지만)

- 토글은 pipeline `app.py` 단독 소유 (`VLM_JUDGE_SHADOW=1`, `VLM_JUDGE_BACKEND=own|gemini`), 어댑터는 토글 정의 금지.
- shadow는 기존 Gemini verdict의 **복제 저장만** — Gemini 재호출 0, 판정 경로 무변경.
- **shadow는 절대 분석을 실패시키지 않는다** — 예외 삼키고 log.exception + status 필드.
- status enum 규율(disabled/skipped_error/not_applicable/applied) 복사 — 무음실패 방지 (TRUST-08 정신).
- Firestore `vlm_shadow/{video_hash}` top-level 컬렉션, flat-dict 검증 + ms epoch, (T,J) 행렬 flat 저장. 대형 배열 저장 시 index 면제 필요 ([[firestore-index-entry-limit]]).

### Anti-Patterns to Avoid

- **원 영상에서 프레임 재추출:** 위상 불일치 실증(0/6). 9fps 배열 인덱스만 사용.
- **모델이 점수 방출:** 출력 스키마에 score 필드 영구 부재 (VisionVerdict 전례). 짚기·측정·앵커까지만.
- **uploads/ prefix에 학습 영상 적재:** ObjectCreated→SQS→pipeline 발화. fixtures/·training/ 비-notified prefix만.
- **4-bit 베이스에 어댑터 직접 병합:** 불가. 16-bit 원본 경유 필수 [CITED: NLM §22·§26].
- **eval 동시 실행:** 파이프라인 동시성 비안전. SERIAL 고정.
- **kip-up 편중 학습셋/eval:** belle 재확인 invariant. 매니페스트에 동작별 카운트 게이트.
- **보유 13영상 curve-fit:** 합성 교란 파라미터를 보유 영상 점수에 맞추는 것 금지 ([[scoring-redesign-must-generalize-no-overfit]]).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 학습 루프/분산/packing | 자체 PyTorch 학습 스크립트 | ms-swift CLI (`swift sft` / `swift rlhf`) | 멀티모달 packing·모듈 독립 제어·병합·양자화까지 원스톱. D-06 잠금 |
| LoRA 병합·양자화 | 수동 state_dict 수술 | `swift export --merge_lora true` → `--quant_method awq` | 4-bit 병합 함정을 프레임워크가 회피 |
| 영상 다운로드/메타데이터 | requests+파싱 자작 | yt-dlp + `--write-info-json` | 포맷 협상·스로틀·메타데이터 추출 전부 내장. 월간 유지보수 |
| 추론 JSON 포맷 강제 | 후처리 재시도 루프만 | vLLM guided decoding (`response_format`/guided JSON) + 방어적 normalize | bake-off 포맷 변수 통제 + 서빙 파싱 에러 0 목표 [CITED: NLM Q7] |
| 시간 정렬/DTW | 새 정렬 알고리즘 | 기존 `motiondtw` + `_build_selected_frame_pair` | 실증 완료 코드. A3 power-spin 싱크도 이 뿌리 ([[d2-crop-and-sync-one-root-motion-alignment]]) |
| eval 하네스 골격 | 새 러너 | `evals/phase24/run_sweep.py`·`assert_gates.py` 복사 확장 | EVAL_OUT_DIR·SERIAL·ARTIFACT-GATED·_meta provenance 규율 내장 |
| Gemini 업로드 생명주기 | 새 File API 코드 | `gemini_vision_scorer` 업로드→ACTIVE 폴링→**삭제** 헬퍼 | 20GB 적체 누수 fix 이력 — 증류 대량 배치에서 치명적 |
| 표준 VLM 벤치 | 자체 재구현 | lmms-eval | MotionBench류 sanity 비교는 표준 러너로 |

**Key insight:** 이 phase의 신규성은 "학습 코드"가 아니라 **데이터 규격과 게이트**에 있다. 학습·서빙·다운로드는 전부 성숙한 도구가 있고, 우리가 소유해야 하는 것은 schema.py(D-11 규격)·매니페스트(균등+provenance)·assert_gates(D-15)다.

## Common Pitfalls

### Pitfall 1: 4-bit 병합 함정
**What goes wrong:** QLoRA 어댑터를 4-bit 베이스에 병합 시도 → 실패 또는 품질 붕괴.
**Why:** 양자화 가중치에는 저랭크 델타를 수치적으로 흡수 불가.
**How to avoid:** FP16/BF16 원본 준비 → `--merge_lora true` → AWQ/GPTQ 재양자화 → vLLM. 학습 Pod 디스크에 16-bit 베이스(8B ≈ 16GB+) 공간 확보를 plan에 명시.
**Warning signs:** 병합 후 perplexity 폭증, vLLM 로드 실패.

### Pitfall 2: 교사 라벨이 교사의 결함을 상속
**What goes wrong:** Gemini 증류 라벨에 A2 피터팬 위양성 같은 Gemini 자체 오류가 그대로 들어가 자체 모델이 "Gemini 이상" 게이트를 원리적으로 못 넘음.
**Why:** 증류는 상한이 교사 품질.
**How to avoid:** (1) LLM judge 7점 미만 폐기 + 물리 불가능 궤적 휴리스틱 [CITED: NLM §6], (2) 합성 교란 트랙(a)은 교사 무관 — 정답이 원좌표라 자가 검증 가능, (3) 2026-07-06 실증 케이스(피터팬 위양성·power-spin)를 **hard negative eval 셋**으로 격리(학습셋 오염 금지), (4) 일관성 투표(다중 후보→합의).
**Warning signs:** shadow 비교에서 자체 모델과 Gemini의 오답이 동일 케이스에 몰림.

### Pitfall 3: vLLM VRAM 선점으로 기존 분석 경로 붕괴
**What goes wrong:** vLLM 기본 gpu-memory-utilization 0.9 → NLF/RTMW OOM → 프로덕션 분석 전면 장애.
**How to avoid:** Pattern 4의 실행 순서(실측→예산→기동 순서→실패 기준). shadow 도입 직후 기존 EVAL18 스모크 1회로 분석 경로 생존 확인.
**Warning signs:** /health 200이지만 /analyze에서 CUDA OOM, 분석 시간 급증.

### Pitfall 4: 합성 교란이 실제 RTMW 오류 분포와 동떨어짐 (sim-to-real)
**What goes wrong:** NLM 제안 수치(3~5프레임 Null, 5% 지터 등)는 소스 직접 근거 없음 [CITED: NLM 상충 #2 — 명시적 자인]. 그대로 쓰면 모델이 "합성 교란 스타일"만 보정.
**How to avoid:** Wave 0 첫 태스크로 **실 오류 분포 측정** — 371건 실사용 + still 페어에서 confidence 급락 구간 길이·관절별 튐 크기 히스토그램 추출 → 교란 파라미터를 이 분포에서 샘플. NLM 커리큘럼 3단계(비핵심 1프레임 → 연속 5~10프레임 핵심 관절 → L/R 스왑+복합)는 구조로만 차용, 수치는 자체 ablation.
**Warning signs:** 합성 eval 정확도 높은데 실영상 shadow 일치율 낮음.

### Pitfall 5: 증류 배치의 Gemini 스토리지/크레딧 소진
**What goes wrong:** File API 20GB 적체(과거 실증: power-spin 0점 사고) / 크레딧 고갈 ([[gemini-credits-depleted-2026-06-20]]).
**How to avoid:** 업로드→호출→**즉시 삭제** 규율 강제 + 배치 전 크레딧 확인 태스크 + video_hash 캐시 재사용(같은 영상 재업로드 0).
**Warning signs:** files.list 누적 증가, 429/quota 에러.

### Pitfall 6: bake-off가 언어 프라이어 단축키를 못 잡음
**What goes wrong:** 모델이 영상을 안 보고 JSON 키·프롬프트 텍스트만으로 답을 맞혀 변별력이 허수.
**How to avoid:** 역재생·순서 섞기 함정 데이터 포함(MotionBench 방식) + few-shot 2~3개 동일 제공 + CircularEval(객관식) [CITED: NLM Q7]. 좌표 정답이 프롬프트에 새지 않게 입력 JSON과 정답 JSON 분리 검증.
**Warning signs:** 함정 데이터 정답률이 정상 데이터와 동일하게 높음.

### Pitfall 7: 학습셋 매니페스트와 실 적재분 드리프트
**What goes wrong:** S3 적재분·매니페스트·JSONL이 어긋나 재현 불능 + 균등성 게이트 무의미화.
**How to avoid:** phase18 `assert_baseline.py` self-consistency 패턴(셋 일치 + known_issue silent-통과 금지)을 매니페스트↔적재분↔JSONL 3자 검사로 확장. 매니페스트에 `_meta` provenance 블록(runId·yt-dlp 버전·PROMPT/SCHEMA_VERSION).

### Pitfall 8: 결정성 게이트의 범위 혼동
**What goes wrong:** temperature 0으로 "결정적"이라 선언 — 실제로는 GPU 비결정성·서버 배칭으로 bit-비결정.
**How to avoid:** phase24 독트린 승계 — MATH-determinism과 (V)LM 샘플링 결정성을 명시 분리. 자체 모델은 temp 0 + greedy + video_hash 캐시(TechniqueCache 전례)로 "같은 입력=같은 verdict" 보장. cold re-run 2회 비교(run_sweep 전례).

## Code Examples

### 학습 JSONL 원형 (belle 노트 — 데이터 포맷의 canonical seed)
```json
// Source: 22-NLM-EXTRACT.md §8 (belle 노트 verbatim) — system/user(video+RTMW_Data)/assistant(<thought>+보정JSON+코칭)
{"messages": [
  {"role": "system", "content": "당신은 스포츠 모션 분석 전문가입니다. ... 반드시 분석 과정을 먼저 서술해야 합니다."},
  {"role": "user", "content": [
    {"type": "video", "video": "s3://.../clip.mp4"},
    {"type": "text", "text": "RTMW_Data: [{'frame': 12, 'right_elbow': [120.5, 45.2, 0.8], ...}]"}]},
  {"role": "assistant", "content": "<thought>\n프레임 12에서 right_wrist 신뢰도 0.2 ... 가려짐 진단 ...\n</thought>\n\n**[보정된 좌표 데이터]**\n{...}\n\n**[모션 분석 및 코칭 피드백]**\n..."}
]}
```
v1 확장: assistant 출력을 D-01 통합 리포트 스키마(보정좌표+faults+time_anchors+segments+svg_spec+coaching)로 교체. `frame` = 9fps 원 인덱스 (Pattern 1).

### ms-swift QLoRA SFT (검증된 초기 설정)
```bash
# Source: swift.readthedocs.io RLHF/SFT docs + 22-NLM-EXTRACT Q1 (LR은 스윕 대상 — NLM 상충 #7)
swift sft \
  --model <bake-off 승자 8B> \
  --dataset train.jsonl --split_dataset_ratio 0.02 \
  --train_type lora --lora_rank 64 --lora_alpha 128 \
  --target_modules all-linear \
  --quant_bits 4 --torch_dtype bfloat16 \
  --gradient_checkpointing true --optim paged_adamw_8bit \
  --packing true --max_length 32768 \
  --per_device_train_batch_size 1 --gradient_accumulation_steps 16 \
  --learning_rate 1e-5 --vit_lr 2e-6 --aligner_lr 1e-5
# 주의: 정확한 인자명은 Wave 2 착수 시 `swift sft --help`로 재확인 (4.x 인자 개편 이력) [ASSUMED: 인자명 세부]
```

### 병합 → 재양자화 → 서빙
```bash
# Source: 22-NLM-EXTRACT §22 + docs.vllm.ai (플래그 검증)
swift export --adapters <ckpt> --merge_lora true            # 16-bit 병합 (4-bit 직접 병합 불가)
swift export --model <merged> --quant_method awq --quant_bits 4
vllm serve <awq-model> --quantization awq \
  --gpu-memory-utilization 0.4 --max-model-len 32768 \
  --limit-mm-per-prompt '{"video":1}' --port 8001           # localhost, FastAPI가 인증 프록시
```

### GSPO (Wave 4 참고 — ms-swift 공식 경로)
```bash
# Source: swift.readthedocs.io/en/latest/Instruction/GRPO/AdvancedResearch/GSPO.html
swift rlhf --rlhf_type grpo --importance_sampling_level sequence \
  --reward_funcs <custom_python>   # 보상 5종 파이썬 연결 (NLM §21·§24)
# MPO 웜업: --rlhf_type dpo + 복수 --loss_type + --loss_weights (공식 RLHF 문서)
```

### 유튜브 수집 + provenance
```python
# Source: upload_phase15_dataset.py 골격 + yt-dlp --write-info-json [ASSUMED: 플래그 세부 — 착수 시 yt-dlp --help 확인]
# yt-dlp --write-info-json --no-playlist -f "bv*[height<=720]+ba/b" <url>
# → <id>.info.json (uploader/webpage_url/license/upload_date) = provenance 원장의 원천
MANIFEST_ROW = {
    "s3_key": "fixtures/phase22/<motion>/<id>.mp4",   # 비-notified prefix — uploads/ 절대 금지
    "motion": "...", "label_bucket": "정타|fault",     # 사람 점수 라벨 금지 — 버킷만
    "source_url": "...", "channel": "...", "license_evidence": "info.json 보관",
    "usage": "training-only-no-redistribution", "collected_at_ms": 0,
    "yt_dlp_version": "2026.7.4",
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Qwen2.5-VL-7B 후보 ([[finetune-open-model-phase22]] 구 메모) | Qwen 3.6 세대 (<35B Apache 2.0) | 2026 (belle 노트북) | 구 메모의 모델명 인용 금지 — bake-off는 3.6 세대로 |
| InternVL 라이선스 불확실 (NLM 노트 5·11) | InternVL 3.5 ≤38B 클린 확정 (belle 2026-07-06) | 2026-07-06 | bake-off는 성능만으로. 라이선스 재조사 금지 |
| XTuner(MPO)+verl(GSPO) 이중 스택 | ms-swift 단일 (MPO=loss 혼합, GSPO=importance_sampling_level) | ms-swift 3.x~4.x | D-07 "SWIFT 주" 성립 — 본 조사로 확정 |
| GRPO token-level | GSPO sequence-level importance sampling | 2025~ | 긴 구조화 출력(JSON)의 RL 안정성 |
| 프레임 과압축(0.2fps급) | 짧은 클립 32~64프레임 집중 + ViR/토큰 압축 | MotionBench 이후 | 미세 동작 인식률 임계 — 프레임 수가 1차 레버 |

**Deprecated/outdated:**
- LLaVA 계열: 상업 불가 — 사용 금지 (잠금).
- InternVL-U 생성 헤드: ScaleEdit-12M(CC BY-NC-SA) 오염 — 아키텍처 차용만, v2에서 자체 재학습.
- `gemini-2.5-*` 모델 string: 금지 — 3.1-pro-preview/3.5-flash ([[gemini-latest-model-versions]]).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | yt-dlp `--write-info-json` 등 플래그 세부와 info.json 필드 구성 | 유튜브 수집 | 낮음 — 초안정 기능. 착수 시 `yt-dlp --help` 1회 확인 |
| A2 | autoawq 유지보수 정체 → `swift export` awq 경로가 최신 백본에서 막힐 수 있음; llm-compressor 대체 | Standard Stack | 중간 — Wave 2 배포 시 실측, GPTQ 폴백 존재 |
| A3 | 합성 교란 수치(Null 구간 길이·지터 크기·커리큘럼 비율) | Pitfall 4 | 높음 — NLM 자인 미검증. 실 371건 분포 측정으로 대체 (Wave 0 태스크) |
| A4 | LR 값(ViT 2e-6 / LLM 1e-5 / 4e-5) — 서로 다른 세팅 출처 | SFT 레시피 | 낮음 — 스윕 대상으로만 사용 |
| A5 | 현행 4090 Pod의 NLF+RTMW 상주 VRAM 실측치 (동거 가능성의 전제) | Pattern 4 | 높음 — Wave 0/3 첫 태스크로 실측. 실패 시 D-14 폴백 |
| A6 | Qwen3.6-VL 8B / InternVL3.5-8B의 정확한 HF/ms-swift 모델 ID | bake-off | 중간 — Wave 1 착수 시 ms-swift Supported-Models 문서에서 확정 |
| A7 | `<loc_NNN>` mean-init·modules_to_save 절차 (NLM이 외부 지식으로 자인) | Pattern 2 | 낮음 — v1 기본에서 제외했으므로 ablation 시에만 재검증 |
| A8 | ms-swift 4.4.0 SFT 인자명 세부(`--vit_lr`/`--aligner_lr` 등 4.x 개편 가능성) | Code Examples | 낮음 — `swift sft --help` 1회로 해소 |
| A9 | 유튜브 콘텐츠 학습 이용의 법적 지위 (D-09는 belle 잠금 — 실행만; provenance 로그가 완화책) | 수집 | 중간 — D-12 법률 검토 1회에 포함시킬 것 |
| A10 | lmms-eval이 커스텀 비디오+JSON 태스크를 무개조로 수용하는지 | bake-off | 낮음 — 주 하네스는 자체 run_bakeoff라 영향 국소 |

## Open Questions

1. **bake-off 정답 좌표(ground truth)의 출처**
   - What we know: 좌표 보정 태스크의 zero-shot 변별은 "교란 주입 전 원좌표"가 정답인 합성 트랙으로 가능(교사 무관).
   - What's unclear: 실영상(교란 아님)의 "진짜 정답 좌표"는 존재하지 않음 — grounding L2는 합성 트랙에서만 계측 가능.
   - Recommendation: bake-off 4축 중 (A) grounding은 합성 교란 셋으로, (B)(C)(D)는 실영상으로 계측한다고 plan에 명시. 실영상 좌표 정확도는 shadow 일치율+물리 일관성(속도/가속도)으로 대리 측정.
2. **shadow 트래픽 볼륨과 vLLM 상시 가동 비용**
   - What we know: 파일럿 트래픽은 소량(일 수십 건). Pod는 이미 상시 가동.
   - What's unclear: shadow 추론이 분석 지연에 주는 영향(같은 GPU에서 RTMW/NLF와 경합).
   - Recommendation: shadow를 BackgroundTasks 후순위로 배치(분석 완료 후 실행) — 지연 영향 0 설계. Pattern 4의 +20% 기준은 동시 실행 시나리오용.
3. **D-12 가명처리(얼굴 블러) 파이프라인의 배치 위치**
   - What we know: 수집·가명처리·적재는 Phase 22 scope. 얼굴 픽셀은 학습에 불필요(포즈/모션만).
   - What's unclear: 블러 도구 선정(YOLO 얼굴 검출 재사용 vs 별도) — 코드베이스 전례 없음.
   - Recommendation: 기존 YOLO11 인프라로 얼굴 bbox 검출 + Gaussian blur 순수 모듈이 최소 경로. plan에서 소태스크로 배치, 고객 영상 트랙(c)에만 적용(유튜브 공개 영상은 D-12 범위 밖 — provenance만).
4. **T3 순수 텍스트 시간추론 합성 데이터의 규모/혼합비**
   - What we know: D-11이 혼합을 요구. NLM은 원리만 제공.
   - Recommendation: SFT 혼합비(예: 10~20%)를 ablation 축으로 두고 수치 단언 금지.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| ffmpeg (로컬) | 수집 클립 트리밍 | ✓ | 설치됨 | — |
| aws CLI + sunity-motion 프로필 | S3 적재·SSM | ✓ | 2.34.53 | — |
| python3 (로컬) | 수집·매니페스트 스크립트 | ✓ | 3.14.5 | — |
| yt-dlp (로컬) | D-09 수집 | ✗ | — | `pip install yt-dlp` (slopcheck OK) — plan에 설치 태스크 |
| 서빙 Pod (4090+Volume) | shadow 서빙·eval | ✓ (원격, 메모리 기준) | svn31pzja7uay0, SSH root@213.173.102.233:12729 | Pod 재생성 시 proxy URL→Lambda env 동기화 필수 |
| 학습 Pod (신규 임대) | Wave 1~2 bake-off·SFT | ✗ (미임대) | — | RunPod 임대 진행+belle 알림 (Claude's Discretion 명시). EU-RO-1 우선순위 [[runpod-eu-ro1-gpu-priority]], Network Storage 필수 |
| ms-swift / vllm / lmms-eval (Pod) | 학습·서빙·eval | ✗ (미설치) | 4.4.0 / 0.24.0 / 0.7.2 | Wave 착수 시 설치 (setup.sh 멱등 골격) |
| Gemini API 키+크레딧 | 증류·shadow 비교 | ✓ (SSM) | 3.1-pro-preview / 3.5-flash | 배치 전 크레딧 확인 필수 ([[gemini-credits-depleted-2026-06-20]]) |
| Firebase SA / Firestore | shadow 로그 저장 | ✓ | 기존 | — |
| 16-bit 베이스 디스크 (학습 Pod) | 병합 단계 | 확인 필요 | 8B FP16 ≈ 16GB+ | Volume 용량 산정 태스크 |

**Missing dependencies with no fallback:** 없음 (학습 Pod 임대는 belle 승인된 진행 항목).
**Missing dependencies with fallback:** yt-dlp(설치), ms-swift/vllm(설치), autoawq 경로(GPTQ/llm-compressor 폴백).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) + `tsc --noEmit` (앱 접점 발생 시) |
| Config file | 없음 (관례 기반) — phase22 tests는 `backend/tests/phase22/` 신설 |
| Quick run command | `python3 -m pytest backend/tests/phase22 -x -q` |
| Full suite command | `python3 -m pytest backend/tests -q` (기존 baseline FAILED diff IDENTICAL 규율) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FT-01 | bake-off 4축 계측 + 변별력 리포트 + cold re-run 결정성 | eval (Pod, serial) | `EVAL_OUT_DIR=/tmp/... python backend/evals/phase22/run_bakeoff.py` | ❌ Wave 1 (run_sweep 골격 복사) |
| FT-02 | 매니페스트↔S3 적재분↔JSONL 3자 self-consistency + 전 동작 균등 카운트 | unit (pod-free) | `pytest backend/tests/phase22/test_manifest_consistency.py -x` | ❌ Wave 0 |
| FT-03 | schema.py D-11 규격(Null 고정·알파벳 정렬·이산화 왕복 무손실) + 교란 생성 순수성(numpy 단독) + judge 필터 임계 | unit | `pytest backend/tests/phase22/test_schema.py backend/tests/phase22/test_perturb.py -x` | ❌ Wave 0 |
| FT-04 | SFT 게이트: Phase24 4종(추적성·단조성·결정성·일반화) 확장 + EVAL18 6페어 무회귀 | eval gate (importable check_*) | `python backend/evals/phase22/assert_gates.py` (exit 0 = PASS; Pod artifact 없으면 SKIPPED≠FAIL) | ❌ Wave 2 |
| FT-05 | shadow 무음실패 방지(status enum) + 분석 실패 절대 미유발 + Firestore flat-dict 검증 + swap 토글 pipeline 단독 소유 | unit + integration | `pytest backend/tests/phase22/test_shadow_wiring.py -x` | ❌ Wave 3 |
| FT-06 | provenance 필드 필수 검증(source_url·license_evidence·usage) + 금지 모델(LLaVA/InternVL-U) grep fence | unit + grep gate | `pytest backend/tests/phase22/test_provenance.py -x` | ❌ Wave 0 |

### Wave별 산출 검증 (Nyquist)
- **Wave 0 (데이터 엔진):** 매니페스트 3자 정합 + 균등 카운트 게이트 + 교란 파라미터의 실분포 근거 문서(371건 히스토그램 artifact) + shadow 로깅 스모크(분석 1건 → vlm_shadow doc 생성 + 분석 성공 불변).
- **Wave 1 (bake-off):** 변별력 리포트(4축 표) + 함정 데이터(역재생) 변별 확인 + cold re-run 2회 동일성. 선정 근거를 `_meta` provenance로 박제. **모델 선정 = belle 확인 checkpoint.**
- **Wave 2 (SFT):** assert_gates exit 0 — Phase24 4종 + EVAL18 6페어 무회귀 + 전 동작 균등(+미보유 동작 억제 확인) + 합성 교란 held-out 정확도. eval은 Pod SERIAL.
- **Wave 3 (shadow→swap):** shadow 비교 로그 N건 누적 → 역할별(veto 먼저) "Gemini 이상" 증명 리포트(일치율+불일치 케이스 belle 리뷰) → swap 토글 후 EVAL18 재실행 무회귀. swap은 역할당 1회 belle 확인.
- **Wave 4 (RL, 후속 plan):** 본 phase에서는 게이트 정의만 이월.

### Sampling Rate
- **Per task commit:** `pytest backend/tests/phase22 -x -q` (< 30s, pod-free)
- **Per wave merge:** full suite + 해당 wave eval 스크립트 (Pod serial)
- **Phase gate:** assert_gates 전 게이트 GREEN + EVAL18 무회귀 + belle 실기기/shadow 리포트 확인

### Wave 0 Gaps
- [ ] `backend/tests/phase22/` 신설 (conftest + schema/perturb/manifest/provenance 테스트)
- [ ] `backend/evals/phase22/` 신설 (run_bakeoff / assert_gates / fixtures manifest)
- [ ] 실 RTMW 오류 분포 히스토그램 artifact (교란 설계의 입력)
- [ ] Pod VRAM 실측 기록 (vLLM 동거 판단 입력)

## Security Domain

`security_enforcement: true`, ASVS L1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | vLLM 포트는 localhost 바인드 + FastAPI shared-secret 헤더(`_verify_token` 전례, 미설정=503). Lambda→Pod는 기존 `X-RunPod-Token` 체계 재사용 |
| V3 Session Management | no | 세션 없음 (토큰 헤더 단발 호출) |
| V4 Access Control | yes | S3 학습 prefix는 sunity-motion 키 전용. Firestore `vlm_shadow`는 backend Admin 전용(클라이언트 rules 차단 확인). 매니페스트에 PII 필드 금지 |
| V5 Input Validation | yes | 자체 모델 출력 = 신뢰 불가 입력 — coach_writer `_normalize_entry` 수준 방어적 파싱(지원 키만 추출) + flat-dict 사전검증 후 Firestore 기록. vLLM guided JSON은 보조, 파서 방어가 본체 |
| V6 Cryptography | yes (간접) | 시크릿은 SSM Parameter Store(WithDecryption), 키 로그 금지(T-20-06 전례). 자작 암호화 0 |
| V12 Files & Resources | yes | 유튜브 다운로드 파일 = 외부 신뢰불가 미디어 — ffmpeg/imageio 파싱은 Pod 격리 환경에서만, 로컬 실행 시 최신 ffmpeg 유지. 파일명 정규화(ASCII-safe 전례) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 학습 데이터 오염(악의/저품질 유튜브 세그먼트) | Tampering | provenance 매니페스트 + judge/휴리스틱 필터 + belle 리뷰 샘플링. 학습셋은 버전 고정(재현 가능) |
| 모델 출력 주입(스키마 밖 키/거대 배열로 Firestore 오염) | Tampering | 화이트리스트 키만 추출 + nested-array 사전검증 + 크기 상한 |
| vLLM 엔드포인트 노출(무인증 추론 탈취) | Elevation | localhost 바인드 + 프록시 인증. RunPod proxy로 직접 노출 금지 |
| 시크릿 유출(Pod env·로그) | Info Disclosure | SSM 단일 소스, 키 값 로그 금지, 매니페스트/`_meta`에 키 미포함 |
| 고객 영상 PII(얼굴) 학습 유입 | Info Disclosure | D-12 가명처리(블러+식별자 제거)를 적재 전 단계에 강제 — 적재 후 소급 불가 |
| 프롬프트 주입(영상 내 텍스트/자막이 지시로 해석) | Tampering | 시스템 프롬프트에 출력 스키마 강제 + guided decoding + 방어 파서 (완전 차단 불가 — shadow 단계에서 불일치로 검출) |

## Project Constraints (from CLAUDE.md)

- 기술 스택 변경 금지 (§3) — 본 phase는 ML 레이어 확장이며 앱/백엔드 스택 불변. Motion AI 인프라는 기존 EC2에 얹지 말 것(신규 학습 Pod는 RunPod — 정합).
- 시크릿 = AWS Parameter Store, `.env` 하드코딩 금지 (§3) — Gemini 키·vLLM 토큰 모두 SSM/env 주입.
- 작은 단위 작업 / 의미있는 테스트만 / 이모지·슬롭 코드 금지 (§7).
- 막히면 "Do not work yet" 후 질문 먼저 (§7) — Wave 1 모델 선정·Wave 3 swap은 belle checkpoint.
- 작업 완료 시 plan.md 업데이트 (§7).
- 코드 컨벤션: 한국어 docstring+결정 근거(D-번호) 인용, `from __future__ import annotations`, 순수 함수(분석 모듈 numpy 단독), 어댑터 lazy-import, 3-way 계약 lockstep(스키마가 앱에 닿는 순간), Firestore nested-array 금지.
- `/ml` 은 문서 전용 — 학습 코드는 `backend/training/` 배치.
- 파이프라인 동시성 비안전 — eval/batch 순차 실행.

## Sources

### Primary (HIGH confidence)
- swift.readthedocs.io — [RLHF (MPO = 복수 loss_type + loss_weights)](https://swift.readthedocs.io/en/latest/Instruction/RLHF.html), [GSPO 전용 페이지 (importance_sampling_level)](https://swift.readthedocs.io/en/latest/Instruction/GRPO/AdvancedResearch/GSPO.html)
- [ms-swift GitHub](https://github.com/modelscope/ms-swift) — README에 Qwen3.6·InternVL3.5 지원 명시
- docs.vllm.ai — [Conserving Memory](https://docs.vllm.ai/en/latest/configuration/conserving_memory/), [Engine Arguments](https://docs.vllm.ai/en/stable/configuration/engine_args/), [vllm serve CLI](https://docs.vllm.ai/en/stable/cli/serve/) (`--gpu-memory-utilization`/`--max-model-len`/`--limit-mm-per-prompt`/`--quantization awq`)
- PyPI 실측 (2026-07-06): ms-swift 4.4.0 / vllm 0.24.0 / yt-dlp 2026.7.4 / unsloth 2026.6.9 / lmms-eval 0.7.2 / autoawq 0.2.9 + slopcheck 6/6 OK
- 코드베이스: `22-PATTERNS.md`(12/13 analog), STATE.md quick tasks(260705-h5z 인덱스 정렬 실증, 260702-o0c window-median FP 교훈, k8h cap)

### Secondary (MEDIUM confidence)
- `22-NLM-EXTRACT.md` — belle 노트 26건 + NLM 질의 7건 (이 phase의 승인 근거. 단 상충 #2·#4·#7은 본 문서에서 등급 하향/대체)

### Tertiary (LOW confidence — 검증 대기)
- NLM 합성 교란 수치(상충 #2 자인) — 실분포 측정으로 대체
- LR/글로벌 배치 수치(상충 #7·#9) — 스윕 대상
- autoawq 유지보수 상태 추정

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 전 패키지 PyPI+slopcheck 실측, 프레임워크 기능은 공식 문서 확인
- Architecture (정렬·shadow·서빙): HIGH — 코드베이스 실증(6/6 vs 0/6) + 공식 플래그 + 기존 패턴 12/13 analog
- 하이퍼파라미터: MEDIUM — NLM 출처 혼재, 초기값+스윕으로만 사용
- 합성 교란 설계: LOW — 소스 근거 없음(NLM 자인), 실분포 측정이 선행 태스크

**Research date:** 2026-07-06
**Valid until:** 2026-07-20 (ms-swift/vllm 릴리스 주기 빠름 — Wave 2 착수 시 버전 재확인)
