# NotebookLM Extract — Phase 22 (source: belle notebook "LLM, Finetunig Guide", extracted 2026-07-06)

- 노트북 ID: `b7710c85-8113-4086-89d6-8e3f65d15dab` (97 소스)
- belle 노트 26개 전문을 조건 없이 전수 요약 (컨텍스트의 "25개"는 실제 26개 — AWQ/GPTQ 노트 1건이 완전 중복이라 실질 25개)
- 이 문서가 Phase 22 planning의 2026 기준 근거. 24년 학습데이터 지식으로 대체 금지. 본문 중 [모델 지식 — 노트북 외] 표기가 없는 내용은 전부 노트북/노트 출처.

---

## belle 노트 전문 요지 (26 notes)

### 1. LLM 및 멀티모달 모델 구축과 최적화 전략
- 아키텍처: **"ViT-MLP-LLM" 패러다임** — 언어 백본(Qwen3 시리즈, GPT-OSS) + 시각 인코더(InternViT)를 프로젝션 층(MLP)으로 결합.
- 프레임워크: **Unsloth, SWIFT, LLaMA-Factory** 권장. 대규모 분산은 FSDP+FlashAttention-3 통합 **XTuner**, 온라인 RL은 **verl** 코드베이스.
- 사전학습: NTP(Next Token Prediction) 손실. 답변 길이 편향 방지를 위해 손실에 **Square Averaging(제곱 평균) 가중치 재조정**.
- 사후학습: SFT → RL(DPO, GRPO). 추론 능력 극대화 = **Cascade RL: 오프라인 RL(MPO) 웜업 → 온라인 RL(GSPO) 분포 미세조정**.
- 컨텍스트 확장: **YaRN** RoPE 스케일링 — `config.json`의 `rope_parameters.factor` 조정.

### 2. GSPO 기반 모션 데이터 최적화 및 JSON 규격 가이드
GSPO는 질의당 여러 롤아웃을 샘플링·평가하므로 토큰 길이 최적화와 구조 안정성이 수렴에 결정적.
- **태스크 무관 관절 사전 필터링**: 133관절 전부 넣으면 토큰 폭발. 분석 목적(예: 하체 킥)과 무관한 얼굴/이목구비/손가락 관절은 삭제.
- **JSON 규격 4철칙** (GSPO Format Compliance Reward 계산 시 파싱 에러 0 목표):
  1. 결측치 = **Null 바인딩 고정** (가려짐/블러여도 키 삭제 금지, 스키마 구조 고정)
  2. **키 알파벳 오름차순 정렬** (출력 구조 규칙성 인지 → 파싱 오류 영점화)
  3. **프롬프트 상단에 대상 관절 키 리스트 1회 사전 바인딩** → 배열에는 값(Value)만 나열
  4. (1~3의 결과로) 모델이 시각 추론에만 집중, 학습 효율 극대화

### 3. 멀티모달 모델 기반 픽셀 수준 이미지 합성 전략 (v2 시각물 트랙)
InternVL-U류 통합모델로 교정 가이드 합성 시 픽셀 일관성 유지 4팁:
1. **원본 이미지의 VAE latent를 시각 생성 헤드에 명시적 주입** — 원본 픽셀 구조 망각 방지.
2. CoT 프롬프트에 **"시각적 보존 제약"(보존할 속성) 명시** — 타겟 영역 지정 + visual-consistency constraints.
3. **MSRoPE + 해상도 보간(Resolution Interpolation)**: 저해상도(512px) 초기 훈련 시 위치 인덱스 전체 범위 유지 + 토큰 stride 확대 → 해상도 상승 시 왜곡 최소화.
4. **배경 우선(Background-First) 전략**: object removal로 빈 배경 확보 → 교정 자세 선수를 재렌더링해 합성 (maximal background consistency).

### 4. InternVL-U 기반 스포츠 분석 시각 생성 모델 학습 가이드 (v2 설계서)
ScaleEdit-12M(CC BY-NC-SA 4.0) 오염 때문에 상용화하려면 **시각 생성 헤드를 자체 데이터로 처음부터 재학습 필수**.
- **1단계 데이터**: SVG 기반 물리/공간 페어 합성 차용 — `[원본 프레임]` ↔ `[SVG 화살표/스켈레톤 라인이 그려진 타겟 이미지]` 쌍 + `<think>` 태그 내 생체역학 추론("오른쪽 팔꿈치가 좁으므로 팔 펴는 궤적을 빨간 화살표로") CoT 융합.
- **2단계 아키텍처**: InternVL 3.5 **2B** 언어 백본 + **1.7B MMDiT** 시각 생성 헤드. 이해=ViT, 생성=별도 VAE (표상 분리). 통합 손실 `L_Total = α·L_NTP + β·L_FM` (NTP=다음 토큰 예측, FM=플로우 매칭).
- **3단계 커리큘럼 (3-stage)**:
  1. 시각 생성 헤드 웜업 — MLLM 백본 **동결**, MMDiT+프로젝터만 학습
  2. 가변 해상도 지속 사전학습 — MLLM 동결 유지, 512px~1024px 다양한 종횡비 대응, **원본 VAE latent 주입**으로 픽셀 일관성
  3. Unified SFT — 전체 동결 해제, End-to-End, CoT 데이터 집중 주입
- **4단계 서빙**: `generation_mode` = **`text_image` 모드** (언어 백본이 관절 오차·화살표 궤적·레이아웃을 중간 텍스트로 먼저 계획 → MMDiT가 최종 이미지 생성).

### 5. 상용 VLM 선정을 위한 라이선스 및 모델 비교 분석 (딥리서치 시점)
- **Qwen 3.6 전 오픈웨이트 = Apache 2.0** (GitHub/HF 확인). 상업 이용·파인튜닝·배포 전면 허용, Copyleft 없음, 특허 조항 포함 → DD 안전.
- InternVL 3.5: 논문은 CC BY 4.0이나 **이 딥리서치 시점에는 가중치/코드 라이선스 미확인**, InternVL-U는 공식 라인업에서 미발견.
- 결론(이 노트 시점): **Qwen 3.6 (VLM) + MMPose (Apache 2.0)** 조합이 법적 최적.
- ※ 주의: belle이 2026-07-06 최종 확정한 라이선스 판단(22-CONTEXT D-04: InternVL 3.5 ≤38B = 코드 MIT+백본 Apache 2.0으로 클린)이 이 노트보다 최신. 이 노트의 "InternVL 불확실" 결론은 시점상 과거 상태 — bake-off는 성능만으로 선정.

### 6. 스포츠 VLM 데이터 자동 라벨링 최적화 가이드 (D-10 근거)
1. **교사-학생 부트스트래핑**: 최상위 교사 모델(GPT-4V급)로 고품질 시드 캡션 **100K** 생성 → 경량 캡셔너(Share-Captioner) SFT → 나머지 대규모(**1.2M+**) 자동 생성.
2. **JSON 스키마 전처리**: Null 바인딩·알파벳 정렬·프롬프트 내 키 리스트 사전 바인딩 (노트 2와 동일 규칙).
3. **L2T(Learning to Instruct)**: 답변 생성만이 아니라 **영상만 보고 지시어(Instruction)를 역생성하도록 훈련에 포함** → 언어 프라이어 의존 단축키 학습·환각 방지, 시각 픽셀 집중 강화.
4. **다단계 품질 필터링**: (a) LLM judge 0~10점 채점, **7점 미만 폐기**; (b) 반복(Repetition) 루프 샘플 탐지·삭제; (c) 휴리스틱 — 바운딩박스 종횡비 정상범주(예: 0.9~1.1) 이탈, 물리적으로 불가능한 좌표 궤적 제거.
5. **일관성 투표(Consistency Voting)**: 다중 라벨 후보 생성 → 자기평가 + 합의(Consensus) 최다 결과를 최종 라벨로 채택.

### 7. LLM 관절 좌표 데이터 토큰 압축 및 최적화 전략 (D-11 근거)
1. **좌표 이산화 + 위치 토큰**: 해상도 좌표를 그리드(예: **1000x1000**)로 정규화·이산화, 어휘에 `<loc_000>`~`<loc_999>` 특수 토큰 추가. `{"right_elbow": [125.32, 45.21]}` → `<loc_125><loc_045>` **2토큰**으로 압축. Kosmos-2 방식. Spatial grounding 향상 + 시퀀스 단축.
2. **프롬프트 사전 바인딩 스키마 압축**: 키 리스트·순서를 시스템 프롬프트에 1회 선언, 데이터는 값만 나열. 알파벳 정렬 + Null 고정.
3. **텍스트 가이드 동적 피처 필터링(Text-Guided Routing)**: 태스크와 관련성 높은 부위만 남기고 무관 관절(표정·손가락 뼈대)은 입력 전 삭제.

### 8. MLLM 기반 스포츠 모션 분석 및 좌표 보정 가이드 (핵심 태스크 원형 — D-01/명세서)
**학습 JSONL 예시 (Qwen 3.6 / OpenAI 호환 포맷) — 데이터 포맷의 원형 (verbatim):**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "당신은 스포츠 모션 분석 전문가입니다. 선수의 운동 영상과 RTMW 비전 모델이 추출한 시계열 관절 좌표(JSON)를 입력받습니다. 영상의 실제 움직임과 비교하여 가려짐(Occlusion)이나 모션 블러로 인해 잘못 추출된 좌표 오차를 찾아 보정하고, 교정된 자세를 바탕으로 정밀한 코칭 피드백을 제공하세요. 반드시 분석 과정을 먼저 서술해야 합니다."
    },
    {
      "role": "user",
      "content": [
        {"type": "video", "video": "s3://path/to/sports_swing_001.mp4"},
        {"type": "text", "text": "RTMW_Data: [{'frame': 12, 'right_elbow': [120.5, 45.2, 0.8], 'right_wrist': [130.1, 80.5, 0.2]}, ...]"}
      ]
    },
    {
      "role": "assistant",
      "content": "<thought>\n프레임 12에서 right_wrist의 신뢰도(Confidence) 점수가 0.2로 낮게 나타났다. 영상을 확인하면 이 시점에 선수의 손목이 몸통에 가려져(Occlusion) RTMW 모델이 좌표를 [130.1, 80.5]로 잘못 추정하여 튀는 현상이 발생했다. 프레임 11과 13의 궤적 및 영상의 실제 팔 각도를 고려할 때, 손목의 올바른 위치는 [125.0, 50.3] 부근이어야 타당하다.\n</thought>\n\n**[보정된 좌표 데이터]**\n{'frame': 12, 'right_elbow': [120.5, 45.2, 0.8], 'right_wrist': [125.0, 50.3, 0.9]}\n\n**[모션 분석 및 코칭 피드백]**\n다운스윙 구간(프레임 12 부근)에서 오른쪽 팔꿈치가 몸통에 너무 붙어 내려오며 손목이 과도하게 꺾이는 현상이 확인됩니다. 이는 클럽 페이스가 열려 맞는 슬라이스를 유발할 수 있습니다. 다운스윙 시 양팔의 간격을 유지하며 공간을 확보하는 연습이 필요합니다."
    }
  ]
}
```
- 팁: 133관절 전부 대신 **핵심 관절 필터링 + 소수점 둘째 자리 반올림**으로 토큰 압축.
- 파이프라인: (1) 프레임워크 = **SWIFT / LLaMA-Factory / Unsloth**. Qwen 3.6 긴 영상 = `video_preprocessor_config.json`의 `longest_edge`를 **`469,762,048`** (최대 **224k 비디오 토큰**)로 설정. (2) SFT = LoRA로 Attention+MLP 타겟, `<thought>` 태그 내 시공간 추론 강제 학습, 길이 편향 방지 = Square Averaging 손실 가중. (3) **Cascade RL**: MPO(잘못 보정=Reject / 올바른 보정=Chosen) → GSPO/GRPO(규칙 기반 보상: JSON 포맷 정확성, 보정 좌표가 전후 프레임 물리 궤적(속도/가속도) 범위 내인지). (4) 배포 = **vLLM** + **DvD(Decoupled Vision-Language Deployment)**: 비전 서버(피처 추출)와 랭귀지 서버(분석·코칭) 분리 비동기.

### 9·10. AWQ와 GPTQ 양자화 비교 (완전 중복 2건)
- INT4에서 AWQ·GPTQ 모두 프로덕션급: 품질 저하(Perplexity 증가) **1~3% 내외**, VRAM **FP16 대비 최대 75% 절약**.
- 클라우드 서버(vLLM/SGLang/LMDeploy): 둘 다 공식 지원, 차이 체감 없음.
- 에지/저사양(모바일, x86/ARM CPU, Jetson Orin Nano): **AWQ 유리** — VILA+AWQ 4bit+TinyChat(TinyChatEngine) 파이프라인 권장, 저사양에서 초당 수십 토큰.
- 결론: 서버만 쓰면 자유 선택, 온디바이스 확장 계획 있으면 AWQ.

### 11. 스포츠 분석 SaaS를 위한 파운데이션 모델 라이선스 가이드
- Qwen 3.6/3.5 (Alibaba): **Apache 2.0**, 특허권 부여(Patent Grant) 포함, Copyleft 없음 → Tech DD 최적.
- InternVL 3.5 (OpenGVLab): 논문 CC BY 4.0, (이 노트 소스 기준) 가중치 라이선스 미명시 → 추가 확인 필요였음 (노트 5와 동일한 시점 한계, D-04로 해소).
- **MMPose = Apache 2.0** — 포즈 추정 결합에 법적 리스크 최소.

### 12. InternVL-U 분석: 멀티모달 기술 특징과 상용화 전략
- InternVL-U = **4B** 통합 멀티모달 모델(UMM): 이해·추론·이미지 생성/편집 단일 아키텍처.
- 구조: InternVL 3.5 **2B** 언어 백본 + **1.7B MMDiT** 헤드. 이해=ViT(**InternViT-300M**), 생성=별도 VAE — **Decoupled Visual Representations**.
- CoT 기반 추론 중심 생성: 공간·기하 조작, 과학 논리 작업에 강함. 텍스트 렌더링/편집(Text-centric Image Editing)에서 14B급 BAGEL 압도.
- **라이선스 리스크**: 코드/가중치는 MIT지만 핵심 학습 데이터셋 **ScaleEdit-12M = CC BY-NC-SA 4.0(비상업)** → 모델이 파생 저작물로 해석될 소지 → 상용 배포 금지 대상.
- 전략: 텍스트 코칭 메인 상용 = MMPose+Qwen 3.6, 시각 합성 프리미엄 = **InternVL-U 아키텍처만 차용해 자체 데이터로 생성 헤드 재학습**하는 투트랙 (D-03/v2 근거).

### 13. mmWave 레이더와 VLM 결합 (백로그 트랙)
- mmWave 레이더는 가려짐/저조도에서도 자세·미세 제스처 감지. **mmCLIP** 프레임워크 방식으로 레이더 신호를 vision-language 임베딩 공간에 직접 정렬(Alignment)해 VLM 입력.
- '이종 센서 기반 교차 검증 보상' 단계에서 mmWave 데이터를 절대 좌표 기준으로 제공하면 가려짐 좌표 튐을 모델이 자가 교정 가능. (Phase 22 백로그 — D-07 보상 5종 중 [미래] 항목)

### 14. VRAM 효율 극대화 LoRA 파인튜닝 최적화 가이드
1. **QLoRA 4-bit**: 7B 기준 16-bit LoRA **15~16GB** → 4-bit QLoRA **5~6GB**.
2. **Unsloth**: 활성화·그래디언트 VRAM 최대 **60%** 절감, 속도 **2배**. + FlashAttention-2/3, Liger-Kernel.
3. **Gradient Checkpointing**: 연산 +30% 대신 활성화 메모리 **60~70% 절약** — 저VRAM 필수.
4. **8-bit Adam / Adafactor**: 32-bit AdamW의 파라미터당 12바이트(모멘텀+분산) 절감. 다중 GPU면 DeepSpeed ZeRO-2/3 샤딩·오프로드 (CPU 오프로드는 지연 페널티).
5. **배치/시퀀스**: 활성화 메모리는 시퀀스 길이·배치에 비례, **4K→8K 시 self-attention 메모리 4배**. 부족하면 batch 1~2 + gradient accumulation.
6. **혼합 정밀도**: FP16/BF16으로 메모리 절반.

### 15. 스포츠 모션 분석 특화 LLM 구축 및 상용화 가이드 (종합 파이프라인)
- 1단계 아키텍처: ViT-MLP-LLM. 언어 백본 = Qwen 3.6 (**27B 또는 35B-A3B**) 또는 GPT-OSS(20B), 시각 = InternViT-300M/6B. **MMPose Codec 모듈**로 133관절 2D/3D 좌표를 텍스트 토큰(JSON) 또는 조건부 임베딩으로 변환.
- 2단계 데이터: `<think>\n...\n</think>\n\n` 태그 CoT (좌표 튐의 논리적 모순 분석). **ViR(Visual Resolution Router)/ViCO**: 정보 적은 배경 패치 = **64토큰**, 세밀한 동작 패치 = **256토큰**. **MaPE**: 시각 토큰의 시간(Temporal) 차원에만 오프셋 부여.
- 3단계 학습: SFT — Square Averaging 손실(토큰 수 N의 제곱근 `1/N^0.5` 가중) → Cascade RL — MPO 웜업(정답/오답 쌍 보상 모델) → GSPO(자체 생성 답변 분포 정밀 조정, 환각 제거).
- 4단계 서빙: **DvD 분리 배포** (비전 전용 서버 → TCP/RDMA 비동기 → 언어 전용 서버), **YaRN**으로 Qwen 3.6 기본 **262K → 최대 100만+ 토큰**, **프롬프트 캐싱**으로 반복 시스템 프롬프트/영상 컨텍스트 비용 **최대 90% 절감**, MXFP4/INT4 양자화 시 35B도 단일 24GB~80GB VRAM 구동.

### 16. MMPose와 Qwen 3.6 기반 스포츠 분석 SaaS 구축 가이드
- 1단계 추출: 단일 선수 정밀(폴/골프/투구) = **RTMW(2D) / RTMW3D(3D 전신)** 133 키포인트, 다인원 = **RTMO**.
- 2단계 추론: Qwen 3.6에 영상 프레임 + 좌표 JSON 동시 입력. **`enable_thinking: True`** (Thinking mode)로 생체역학 비교 추론 후 교정 피드백.
- 3단계 에이전트: **Qwen-Agent** 프레임워크로 MMPose 추론 모듈을 Tool로 등록, 업로드→분석→리포트 자동화. (Phase 22 백로그 — 에이전틱 툴콜은 결정성 게이트와 충돌)
- 4단계 배포: MMPose = **MMDeploy** 경량화, Qwen 3.6 = vLLM/SGLang (OpenAI 호환 API). 둘 다 Apache 2.0.

### 17. 고객 데이터 기반 자가 발전형 VLM 학습 전략 (D-10c/D-12 플라이휠 근거)
1. 수집·필터링: LLaVA 사례 — 실사용자 업로드에서 **15K** 고품질 visual instruction 구축. PII/유해 콘텐츠 엄격 필터링 선행.
2. 자동 라벨링: 교사 모델(GPT-4V급) 답변 생성 → 학습 쌍. **L2T 자가 생성**: 모델이 이미지만 보고 지시어+답변 쌍을 대량 자동 생성 → 병합 지속 파인튜닝 = Self-improving.
3. 정형화: 모든 JSON 정답은 동일 최상위 키 세트, Null 유지, 알파벳 정렬. LLM 품질 채점 **7점 미만 삭제** + 휴리스틱 필터.
4. 온라인 RL 연계: 서비스 중 모델의 실제 **롤아웃 풀 수집** → MPO 안정화 → 고객 질의+자체 롤아웃으로 **GSPO** → 사용량 증가 = 분석 능력 정밀화 (데이터 플라이휠).

### 18. Unsloth 기반 4비트 QLoRA 훈련 최적화 전략
1. **모든 선형 레이어 타겟팅** (q, k, v, o, gate, up, down) → full fine-tuning 수준 정확도.
2. **8-bit 건너뛰고 4-bit**: 8-bit는 양자화/역양자화 + int32 누적→FP16 캐스팅 메모리 이동으로 4-bit보다 오히려 느림.
3. **rank 확장**: full FT 수준 원하면 **r=128**급으로 상향 (Unsloth 메모리 최적화로 부담 적음).
4. **시퀀스 길이 통제**: `max_seq_length` 2048 등 타이트하게 — Mistral 7B 기준 일반 파인튜닝 **32.8GB → 12.4GB**.
5. **CPU 오프로딩 지양**: PCIe 전송 지연으로 심각한 속도 저하.
6. FlashAttention 2/3 결합.

### 19. Lance MaPE: 멀티모달 정렬 위치 인코딩
- MaPE = MMPose 코덱 아님. 최신 통합모델 **Lance**의 위치 인코딩: ViT 시맨틱 토큰 / Clean VAE 토큰 / Noisy VAE 토큰이 한 시퀀스에 섞일 때 3D-RoPE의 위치 모호성 해결.
- 원리: 시간 차원에만 모달리티별 오프셋 — `p^(m)_{t,h,w} = [t + Δ_m, h, w]`. 공간(h,w) 불변, 시간축만 shift.
- 시사점: **"비디오 토큰 + RTMW 시계열 JSON 텍스트 토큰"을 한 시퀀스로 넣을 때, 좌표 텍스트 토큰의 시간 축에 고유 오프셋을 주면 모델이 영상 위치와 JSON 역할을 혼동하지 않고 정렬** → 보정 정확도 향상 아이디어.

### 20. MMPose 기반 실시간 스포츠 모션 분석 SaaS 구축 전략
- RTMO(다인원 SOTA) / RTMW·RTMW3D(단일 선수 정밀). RTMW는 **RTMW-m~RTMW-x** 크기, 입력 해상도 **256x192, 384x288** 지원 — 속도/정확도 트레이드오프 조절.
- 133 키포인트(얼굴 방향·손가락·발 포함), 3D human mesh recovery(2D 영상→3D 복원, 360도 프리미엄 기능 가능).
- 자체 커스터마이징: PyTorch 기반, Codecs/Transforms 모듈 결합으로 독자 프레임워크 구축 가능. 배포 = MMDeploy. 라이선스 Apache 2.0.

### 21. 스포츠 동작 보정 VLM을 위한 GSPO 학습 가이드라인 (D-07 RL 환경)
- GSPO: 참조 모델(Reference Model) 제약 없이 질의당 G개 응답 샘플링 → 그룹 내 보상 정규화로 Advantage(Â_i) 계산 → 클리핑 포함 목적 함수로 정책 업데이트.
- **프레임워크 = ms-swift (SWIFT)**: 멀티모달 GSPO/GRPO/DAPO + 멀티노드 분산 기본 지원.
- **필수 소프트웨어**: Python 3.10~3.12, PyTorch 2.0+, **DeepSpeed 0.14+** (ZeRO-2/3), **vLLM 0.5.1+ 또는 LMDeploy** (롤아웃 생성 가속 백엔드).
- Cascade 구성: 1단계 MPO 웜업(보상 해킹 방지 + 롤아웃 품질 상향) → 2단계 GSPO("스포츠 영상 + RTMW 오류 JSON" 입력, G개 보정 결과 샘플링, **사용자 정의 보상 함수 파이썬 스크립트를 ms-swift에 연결**).
- 하드웨어: GSPO는 SFT보다 VRAM 소모 훨씬 큼(배치 내 다중 응답 생성·검증). AdamW 파라미터당 12바이트 + 활성화 메모리. FSDP/DeepSpeed 샤딩, ms-swift는 Megatron 병렬화(TP/PP/CP/EP) 지원. **데이터 패킹(Data Packing) + FlashAttention-3**로 패딩 낭비·연산 병목 제거.

### 22. Qwen 27B QLoRA 가중치 병합 및 재양자화 기술 지침 (배포 경로 — D-06)
- **핵심 원칙: 4비트 베이스에 LoRA 어댑터 직접 병합 불가** — 반드시 16비트 원본 경유.
- 수순: (1) FP16/BF16 원본 베이스 준비 → (2) 병합: SWIFT는 **`--merge_lora true`**, LLaMA-Factory는 Export 탭 → (3) PTQ 재양자화: 서버(vLLM/SGLang/LMDeploy) = **AWQ 또는 GPTQ** (27B 기준 16비트 약 **60GB+ → 20GB 초반**), 로컬/엣지(llama.cpp) = **GGUF Q4_K_M** (성능 저하 약 3~5%, 스위트스팟) → (4) 서빙: `--infer_backend vllm` / `--infer_backend sglang`, FlashAttention-2/3 확인.

### 23. InternVL-U 시각 생성 헤드 재학습 전략 및 통합 손실 함수 (v2)
- `L_Total = α·L_NTP + β·L_FM`.
- L_NTP = 표준 다음 토큰 예측 (언어 추론·지시어 추종 보존). L_FM = **플로우 매칭** — 노이즈→이미지 latent 분포로 이동하는 **속도 벡터 필드(velocity vector field) 회귀**, 예측 속도 vs 선형 궤적 순간 목표 속도의 MSE 최소화.
- 단계별 가중치: **1~2단계(헤드 웜업·지속 사전학습, MLLM 동결) = NTP:FM = 0:1** / **3단계(Unified SFT, 전체 해제) = NTP:FM = 1:20** (언어 추론 궤도 유지 + 시각 합성 품질 극대화 최적 비율).

### 24. 스포츠 영상 가려짐 해결을 위한 MLLM 강화학습 보상 설계 가이드 (D-07 보상 5종 완비 노트)
GSPO/GRPO에서 응답(보정 좌표+텍스트)을 다음 5개 보상의 합으로 평가:
1. **물리적 역학·시계열 일관성 보상**: 보정 좌표의 프레임 간 속도(Velocity)·가속도(Acceleration) 계산 → 생체역학 한계 벗어나면 큰 감점, 매끄러운 궤적 복원 시 가산.
2. **기하학적 정합성·공간 grounding 보상**: 보정 JSON에서 '어깨-팔꿈치', '팔꿈치-손목' **뼈 길이(Bone Length)** 계산 → 가려짐 이전 프레임 뼈 길이와 오차 적을수록 높은 보상.
3. **이종 센서 교차 검증 보상 [미래]**: mmWave/IMU 절대 좌표 vs 모델 예측 좌표의 **L2 거리** 오차 — 가장 강력한 보상 신호 (센서 병행 수집 시).
4. **CoT 논리성 보상**: `<think>` 내 "가려짐(Occlusion)"·"시야 차단"·"궤적 예측" 키워드 **정규식 검사** + 모델이 지목한 가려짐 프레임 번호가 **RTMW Confidence Score 급락 구간과 일치**하는지 비교.
5. **JSON 포맷 준수 보상**: 133관절 스키마·알파벳 정렬·Null 바인딩 위반 시 **강한 페널티(-1)**.
- 적용: G개 후보의 총 보상 r(x, y_i) → 그룹 내 평균·표준편차로 정규화된 Advantage Â_i 계산.

### 25. 상용 API 대 오픈소스 VLM 파인튜닝 비교 분석 (사업 근거 — 힉스필드 프레임)
1. 프라이버시: 자체 = 가중치·데이터·트래픽 전부 내부망, 데이터 주권 + IP 보호.
2. 정확도: 도메인 특화 **7B~13B 소형 모델이 범용 거대 모델 정확도를 압도** 가능. 엄격한 JSON 스키마 완벽 준수, 시간적 추론(Temporal Reasoning) 한계 직접 교정 가능. 상용 API는 fine-grained 결함 판정·133관절 기하 추론 한계 + JSON 구문 오류 잦음.
3. 비용: API = OpEx 종량제(스케일 시 기하급수), 자체 = CapEx — **하루 8시간+ 가동 시 6~14개월에 손익 역전(Break-even)**.
4. 지연: 자체 = DeepStream+vLLM/PagedAttention으로 극단 최적화 가능. API = rate limit·네트워크 종속.
5. IP: 파인튜닝 결과물 = 독자 기술 자산. L2T+GSPO로 고객 데이터 기반 지속 진화 = 해자.
- 전략: **MVP = 상용 API(Gemini)로 가설 검증 → 상용화/스케일업 = 자체 파인튜닝(SFT+RL) 내재화** (현 Gemini→자체 전환 순서와 일치).

### 26. Qwen 3.6 27B 모델 4비트 QLoRA 파인튜닝 가이드 (D-05 27B 승급 경로)
- 16비트 full FT는 **280~300GB+** VRAM. QLoRA(4-bit 동결 베이스 + 고정밀 어댑터)로 **30B급 = 약 20~24GB** → **RTX 3090/4090(24GB), 5090(32GB) 단일 GPU 학습 가능**.
- 프레임워크: **Unsloth**(최강 추천, VRAM -60%·속도 2배) / **LLaMA-Factory**(웹 UI, AQLM·AWQ·GPTQ·bitsandbytes 백엔드) / **SWIFT**(멀티모달+RLHF/GRPO, CLI·Python 정밀 제어).
- 필수 설정: 전 선형 레이어(Q,K,V,O,gate,up,down) LoRA 부착 / batch 1~2 + `gradient_accumulation_steps` / `--gradient_checkpointing true` / 8-bit Adam 또는 PagedAdamW.
- 배포 주의: 4비트 학습 어댑터는 4비트 베이스에 병합 불가 → **16비트 병합 → GPTQ/AWQ 재양자화 → vLLM** (노트 22와 동일).

---

## NLM 질의 응답 (gap-fill queries, 2026-07-06 실행 7건)

### Q1. ms-swift로 8B급 비디오+좌표 JSON QLoRA SFT 구체 설정 (4090)
- **VRAM**: 7B/8B 4-bit QLoRA 기본 소모 약 5~9GB. Unsloth 최적화 기준 seq 2048 + batch 2에서 7B 약 12.4GB. `--gradient_checkpointing true`(ms-swift 기본) 유지 시 24GB 내 비디오 SFT 충분.
- **ViT/Aligner 제어**: ms-swift는 **`lora_llm_full_vit`** (LLM=LoRA, ViT/Aligner=풀 파라미터) 방식 지원. 권장 = ViT 완전 동결보다 **비전 인코더 후반부(latter half) 블록 unfreeze** 또는 전체 학습이 모달리티 정렬 최적. **Aligner(프로젝터)는 반드시 unfreeze**.
- **LoRA**: 전 선형 레이어(q,k,v,o,gate,up,down) 타겟. **r=128** 고랭크 또는 널리 쓰이는 **r=64, alpha=128** 조합.
- **LR 분리**: **ViT = 2e-6, LLM+어댑터 = 1e-5** (AdamW, LongVA 사례). 참고: InternVL 2.5 8B SFT 기본 LR = **4e-5**.
- **Packing**: 짧은 클립+JSON 다수 환경에서 `--packing` 필수 — `max_length` 시퀀스에 샘플 병합, 패딩 제거로 GPU 활용 극대화.
- **Batch**: per-device **1~2** + gradient accumulation으로 글로벌 배치 **128**(일반) 또는 **512**(packing 적용 사례, InternVL) 유지.

### Q2. 비디오 프레임 샘플링·토큰 예산 (10~30초 스포츠 클립)
- **프레임 수: 총 32~64 프레임** (10~30초 기준 약 2~6 fps). 근거 = MotionBench: VLM이 프레임을 과압축(~0.2fps)하면 미세 동작 인식률 60% 미만으로 폭락 — 짧은 클립에 프레임을 집중 할당해야 임팩트 순간 결함 포착.
- **해상도**: 비디오는 타일링 없이(`n_max=1`) **프레임당 448x448 고정 리사이즈** (InternVL 표준). 448 프레임 = pixel shuffle 후 **256토큰**.
- **ViR 압축**: InternVL 3.5-**Flash**의 ViR 활성화 시 패치별 의미 밀도 동적 라우팅 — 핵심 패치 256토큰(1/4), 정적 배경 64토큰(1/16) → **전체 비주얼 토큰 50% 삭감, 성능 저하 없음** (InternVL3.5 논문: DocVQA 80.2 vs 79.8).
- **Qwen3.6-VL**: 네이티브 동적 해상도이므로 `video_preprocessor_config.json`의 `longest_edge`로 토큰 캡 필수.
- **토큰 예산**: 64프레임 × 256 = 16,384 비주얼 토큰, ViR 적용 시 약 8,192. 두 백본 8B의 SFT/권장 컨텍스트 = **32K** → 비주얼 8~16K 써도 관절 JSON 스키마+코칭 출력 여유. M-RoPE가 시간·높이·너비 독립 연산으로 장문맥 프레임 순서 안정.

### Q3. 합성 교란(synthetic perturbation) 주입·커리큘럼 (D-10a)
NLM 명시: **소스에 좌표 교란의 직접적 수치(노이즈 분산·드롭 비율)는 없음** — BPO 오류 주입·Null 규격·커리큘럼 학습·GSPO 원리를 조합한 설계 제안임 (신뢰도 주의, 아래 상충 절 참조).
- **교란 종류**: (a) 가려짐 시뮬레이션 = 연속 3~5프레임 특정 부위 좌표 Null 덮어쓰기 + confidence 0.1 미만 강제 드롭 (키 삭제 금지, Null 바인딩), (b) 논리 오류 주입(BPO 방식) = 좌/우 관절 스왑으로 생체역학 불가능 상태 생성, (c) 시간 역전(MotionBench 방식) = 궤적 순서 reverse, (d) 가우시안 지터 = RTMW 프레임별 떨림 모방.
- **커리큘럼 3단계**: Stage 1(초급) = 비핵심 관절 1~2개, 1프레임 Null 또는 픽셀 ~5% 가우시안 → 선형 보간 수준 복원 학습 / Stage 2(중급) = 연속 5~10프레임 핵심 관절(무릎·발목) 영역 Null → 뼈 길이·물리 한계 기반 기하 추론 / Stage 3(고급) = L/R 스왑 + 프레임 랜덤 드롭(저fps 시뮬) + 복합 가려짐 → CoT로 오류 언어화 후 전면 재수정.
- **Sim-to-Real 갭 극복**: (1) 교란 데이터에 다중 보정 롤아웃 생성 → 자기평가/교사모델로 물리 법칙 부합 최다 합의 결과를 positive sample로 정제(일관성 투표), (2) MPO 웜업 후 실서비스 영상 롤아웃 + 생체역학 페널티 보상으로 GSPO 온라인 정렬.

### Q4. MPO 웜업 구체 레시피 (D-07 Cascade RL 1단계)
- **손실 구성**: `L_MPO = w_p·L_p + w_q·L_q + w_g·L_g` — **선호 손실 L_p = DPO**, **품질 손실 L_q = BCO(Binary Classifier Optimization)**, **생성 손실 L_g = LM 손실**(언어 능력 보존).
- **데이터 규모**: InternVL 사례 = **약 200K 샘플 쌍(MMPR-v1.2)**. 생성법 = 질의당 다수 롤아웃 생성 → 정답 일치(Accuracy) 채점 → Chosen/Rejected 쌍 구성. 오프라인이므로 보상 해킹 원천 차단.
- **GSPO 전환 기준**: MPO는 1 에피소드 **약 0.3K GPU hours**로 **+3.5%** 달성(극히 저비용) → 이후 GSPO(**약 5.5K GPU hours**)로 상한 돌파. GSPO 투입 데이터는 **롤아웃 정답률 0.2~0.8 구간 질의만 선별**(너무 쉽/어려운 것 배제) → 200K를 **약 70K 쿼리(MMPR-Tiny)**로 압축.
- **프레임워크**: ms-swift는 DPO/ORPO/SimPO/GRPO/KTO 등 10+종 지원하나 **'MPO' 단일 명령 지원은 소스상 미확인**. InternVL 공식 = 오프라인 MPO는 **XTuner**(DeepGEMM·FlashAttention-3), GSPO는 **verl**. MPO 파이프라인·쉘 스크립트는 InternVL GitHub(`internvl_chat/shell/internvl3.0/mpo`)에 오픈소스 — 직접 실행 권장.

### Q5. <loc_NNN> 좌표 이산화 토큰의 실무 학습 절차
- [소스 기반] **그리드 1000분할 근거**: CogVLM은 grounding 좌표를 상대 비율×1000 = **000~999 3자리 정수**로 출력(이미지 0.1% 정밀도). KOSMOS-2는 이미지를 p×p 패치로 나눠 연속 좌표를 어휘 내 위치 토큰으로 이산화 — 표준 규격.
- [소스 기반] **이산화의 효과**: 좌표를 위치 토큰으로 변환하면 텍스트·시각 요소가 동일 구조로 연결(Linked) → 숫자 회귀 대신 NTP 본연의 학습 방식 사용, CogVLM/KOSMOS-2가 RefCOCO 등 grounding SOTA(RefCOCO val 92.76 등). FERRET류 하이브리드(이산 좌표+연속 시각 특징)는 자유 형태 미세 영역까지 정밀도 상승.
- [모델 지식 — 노트북 외] (NLM이 스스로 "소스에 코드 레벨 지침 없음, 외부 지식"으로 답변한 부분): `tokenizer.add_tokens([...])` + `model.resize_token_embeddings(len(tokenizer))`; 신규 임베딩은 랜덤 대신 숫자 토큰 임베딩 평균으로 초기화(mean init) 권장; **LoRA 시 `modules_to_save=["embed_tokens", "lm_head"]`로 두 레이어는 풀 파라미터 학습 필수** (신규 토큰은 기존 가중치가 없어 저랭크 어댑터만으로 학습 불가).

### Q6. vLLM AWQ 4-bit 8B 서빙 on 4090 (RTMW 동거) — D-14
- **VRAM**: 8B INT4 가중치 약 4GB(파라미터당 0.5B) + 프레임워크 오버헤드(CUDA 컨텍스트 등 0.5~2GB) + 기본 활성화 = **로드·기동 약 6~7GB**.
- **동거 구성**: vLLM은 기본으로 가용 VRAM ~90% 선점(PagedAttention pre-allocate) → RTMW OOM. **`--gpu-memory-utilization 0.5`** 로 12GB만 점유(모델 7GB + KV캐시 5GB), 나머지 12GB를 RTMW(onnxruntime)+시스템에 할당.
- **비디오 입력 주의**: 프레임마다 수백 비주얼 토큰이 KV캐시에 주입, KV캐시는 컨텍스트 길이·동시 요청 수에 선형 증가 → **`--max-model-len` 안전 상한 강제**(기본 262K는 메모리 과다, 예: 128K 이하), **`--async-scheduling`** 권장. 이미지 전용이면 `--limit-mm-per-prompt.video 0`.
- **프롬프트 캐싱**: Radix 트리 prefix-aware caching(vLLM/SGLang RadixAttention)으로 반복 시스템 프롬프트·동일 영상 prefix KV 재사용 → 입력 연산 최대 ~90% 절감, TTFT 극단 단축.

### Q7. bake-off zero/few-shot 평가 하네스 설계 — D-04/Wave 1
- **평가 4축·지표**:
  - (A) 좌표 grounding: 예측-정답 **L2 거리** + IoU (제로샷 "오른쪽 팔꿈치 좌표 추출" 질의).
  - (B) 시계열 추론(MotionBench/MLVU/TempCompass 방법론): **동작 순서(Action Order)** 정렬 정확도, **반복 카운팅(Repetition Count)**, 속도/방향(가속·감속) 판별.
  - (C) JSON 준수: **파싱 성공률**, **Exact Match(키 이름·구조 100% 일치)**, **CER(레벤슈타인 편집거리)**.
  - (D) 코칭 논리: **LLM-as-a-Judge** — `<think>` 내 결함 분석의 생체역학 타당성을 외부 최상위 모델이 1~5점 블라인드 채점.
- **미니셋**: **100~500개** 클립+정답 JSON. 정상/미세결함/심한 가려짐/조도·앵글 변화 코너케이스 혼합 + **역재생·순서 섞기 함정 데이터**(언어 프라이어 shortcut 검출, MotionBench 방식).
- **프롬프트 통제**: 양 모델 동일 시스템 프롬프트(133관절 키 리스트 + 알파벳 정렬·Null 규칙 명시). few-shot = "프레임+완성 JSON" 예시 **2~3개** (JSON 스키마 준수 유도에 zero-shot보다 우수). 객관식은 **CircularEval**(선택지 순서 셔플, 전 조합 정답 시만 1점 — MMBench 방식).
- **툴킷**: **VLMEvalKit 또는 LMMS-Eval**(통일 인터페이스·자동 스케줄링·judge 통합). 순수 추론력만 보려면 vLLM/NIM **`response_format`(guided JSON schema)** 강제로 포맷 변수 통제.
- **선정 기준**: Qwen3.6-VL 우세 신호 = 시계열 순서·궤적 추적 오답률 낮음(M-RoPE 강점) / InternVL 3.5 우세 신호 = 다중 프레임 OOM 적음·처리 속도·픽셀 단위 미세 인식(타일 동적 해상도+ViR 압축 강점).

---

## Planner가 주의할 상충/불확실 지점

1. **라이선스 노트의 시점 격차**: 노트 5·11은 "InternVL 3.5 가중치 라이선스 미확인 → Qwen 단독 추천"이라 기록되어 있으나, belle의 2026-07-06 최종 확정(22-CONTEXT D-04)은 InternVL 3.5 ≤38B = 코드 MIT + 백본 Apache 2.0 클린. **최신 확정이 우선 — bake-off는 성능만으로 결정**. 노트 5의 "InternVL-U 미발견"도 노트 12(딥리서치 후속)에서 해소됨(MIT 코드 + ScaleEdit-12M 비상업 오염). InternVL-U 자체는 여전히 상용 배포 금지(아키텍처 차용만, D-03/v2).
2. **합성 교란 레시피는 소스 직접 근거 없음**: Q3에서 NLM이 명시적으로 "구체 수치 미명시, 원리 조합 제안"이라 답변. 교란 강도·비율(5% 노이즈, 3~5프레임 Null 등)은 방향성 참고치이지 검증된 수치가 아님 — Wave 0에서 자체 ablation으로 확정해야 함. 우리 파이프라인의 실제 RTMW 오류 분포(pilot 371건·still 페어)를 교란 설계의 1차 기준으로 삼을 것.
3. **MPO의 ms-swift 지원 불확실**: D-07은 "SWIFT 주"로 잡았으나 NLM 소스상 ms-swift의 MPO 단일 명령 지원은 미확인. InternVL 공식 경로는 XTuner(MPO)+verl(GSPO), 스크립트는 InternVL GitHub 공개. plan 단계에서 ms-swift 현행 버전의 MPO/GSPO 지원을 실측 확인하고, 미지원 시 InternVL 공식 스크립트 차용 또는 DPO로 대체하는 분기 필요. (노트 21은 ms-swift가 GSPO 지원한다고 명시 — GSPO 쪽은 안전.)
4. **<loc_NNN> 구현 절차는 절반이 노트북 외 지식**: 그리드 1000분할·이산화 효과는 소스(CogVLM/KOSMOS-2/FERRET) 근거가 있으나, 토크나이저 확장·mean init·`modules_to_save` 실무 절차는 NLM이 외부 지식으로 답한 것. 구현 시 ms-swift/transformers 최신 문서로 재검증 필요. 또한 **`<loc_NNN>` 어휘 확장(embed_tokens/lm_head 풀 학습) vs D-06의 QLoRA 경량 학습은 VRAM·병합 파이프라인에 상호작용** — modules_to_save 포함 시 병합·재양자화 절차가 어댑터 단독보다 복잡해짐. plan에서 명시적으로 다룰 것.
5. **RL 비용 수치의 스케일 주의**: Q4의 0.3K/5.5K GPU hours는 InternVL 계열(대규모 클러스터) 사례 수치 — 우리 8B 단일/소수 GPU 환경의 절대치가 아니라 "MPO는 GSPO 대비 ~18분의 1 비용" 비율 감각으로만 쓸 것. D-07대로 v1은 SFT까지이므로 즉시 영향은 없음.
6. **프레임 수(32~64) vs 현행 파이프라인(9fps)의 정합**: 현행 분석 파이프라인은 9fps 추출인데 VLM 입력 권장은 클립당 32~64프레임(2~6fps). RTMW 좌표(9fps)와 VLM 프레임 샘플(2~6fps)의 시간 인덱스 정렬 설계가 필요 — 노트·NLM 모두 이 정합 문제는 다루지 않음.
7. **LR 권장값의 출처 다양성**: Q1의 ViT 2e-6 / LLM 1e-5는 LongVA(텍스트→비디오 전이), 4e-5는 InternVL 2.5 8B SFT 기본 — 서로 다른 세팅의 수치이므로 초기값 후보로만 쓰고 스윕 대상.
8. **중복·미세 상충**: 노트 9·10(AWQ/GPTQ)은 완전 중복. 노트 18 "rank 128 권장" vs Q1 "r=64/alpha=128도 통용" — 상충 아닌 옵션 폭. 노트 15의 27B/35B-A3B 백본 언급은 D-05(8B 시작, 27B 조건부 승급)로 이미 조정됨.
9. **글로벌 배치 128 vs 512**: Q1에서 128(일반)과 512(packing, InternVL 사례)가 병기 — 우리 데이터셋 규모(시드 수백~수천)에선 훨씬 작은 글로벌 배치가 현실적일 수 있음. 소스 수치는 대규모 코퍼스 기준임을 감안.

---

*Extracted 2026-07-06 — 노트 26건 전수 + NLM 라이브 질의 7건. Phase 22 gsd-phase-researcher/gsd-planner 입력용.*
