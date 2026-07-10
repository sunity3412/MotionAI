# Phase 22: 자체 비전 모델 파인튜닝 (오픈 모델 전환) - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Gemini 의존 시각 판정(결함 짚기·동작 인식·veto)을 **우리가 가중치를 소유한 도메인 특화 오픈 VLM**으로 대체/병행한다. 모델의 v1 태스크 = **영상 + RTMW 133관절 시계열 좌표 JSON을 입력받아 통합 구조화 리포트 하나를 출력**: (1) CoT 진단 기반 보정 좌표, (2) 결함 짚기/측정대상(전 동작 균등), (3) 시간 앵커(결함 프레임/타임스탬프) + sub-action 구간 분할, (4) 렌더용 시각 스펙(목표 각도·힘 방향 벡터·이상 궤적 — SVG/기하 데이터, 픽셀 생성 아님), (5) 코칭 문장(학습은 포함, 소비는 shadow→게이트 후 swap).

**점수는 모델이 절대 내지 않는다** — 짚기/측정까지만, 점수는 Phase 24 감점 규칙 엔진(불변). 사업 프레임 = "스포츠 모션 분석의 힉스필드": 오픈모델 파인튜닝 + 고객 데이터 플라이휠로 자체 IP 확보.

이 작업은 시나리오 2·3단계(분석 정확도 = Core Value) 트랙이다.

</domain>

<decisions>
## Implementation Decisions

### v1 태스크 범위 (belle 직접 논의 — "단순 출력 금지" 푸시백 반영)
- **D-01 (통합 리포트 v1):** 위 Phase Boundary의 5출력을 단일 JSON 스키마로. belle이 검토한 고급 출력 8종 중 temporal grounding·sub-action order·SVG 스펙·structured JSON dump는 v1 포함, 실루엣 이미지 편집·분할 마스크(<SEG>)·반복 카운팅은 v2, 하드웨어 행동 토큰·에이전틱 툴콜은 백로그(결정성 게이트와 충돌).
- **D-02 (코칭 단계적 소비):** 코칭 출력은 v1 학습에 포함하되 서비스 소비는 shadow(Cerebras와 병행 비교)로 시작, 품질 게이트(측정 사실 앵커 준수 + LLM judge + belle 확인) 통과 시 swap. 이유: 7~8B 한국어 코칭 문체 리스크 + "일반적 답변" 환각(이탈 1순위) 방지.
- **D-03 (v2 분리 근거 = 데이터 의존성):** 교정 실루엣 생성은 `[틀린 폼→고쳐진 폼]` 이미지 페어가 0장이라 물리적으로 v1 불가. 외부 생성 API 운영(별도 phase) → 통과 품질분 적재 → v2 자체 생성 헤드(InternVL-U 아키텍처 차용, 자체 데이터 재학습) 순서가 강제됨. v1은 같은 백본에 어댑터/헤드 추가 가능한 구조로 설계해 v2에서 재사용.

### 백본 선정·스케일
- **D-04 (bake-off로 실측 결정):** Qwen 3.6 vs InternVL 3.5, 8B급 zero/few-shot 하네스로 우리 태스크(좌표 보정+짚기) 변별력 비교 후 확정. 둘 다 라이선스 클린(belle 2026-07-06 확정: InternVL 3.5 ≤38B = 코드 MIT+백본 Apache 2.0, Qwen 3.6 <35B = Apache 2.0, MMPose = Apache 2.0)이므로 성능만으로 선정. LLaVA 계열·InternVL-U 생성헤드 사용 금지.
- **D-05 (8B 시작, 27B 조건부 승급):** 8B급으로 시작(반복 빠름, 4090 서빙 가능). 27B는 8B가 정확도 게이트를 못 넘을 때만 승급(4090 QLoRA 학습 가능, 서빙 비용↑).
- **D-06 (프레임워크 = ms-swift 주, Unsloth 보조):** SWIFT(멀티모달 packing, ViT/LLM 모듈 독립 제어, GSPO/GRPO 지원). QLoRA 4-bit, 전 선형 레이어 타겟, rank 64~128, gradient checkpointing, 8-bit AdamW. 배포 = 16-bit 병합 → AWQ/GPTQ 재양자화 → vLLM.
- **D-07 (SFT 먼저, RL 후속):** v1 = SFT까지. Cascade RL(MPO 웜업→GSPO 온라인, 보상 5종: 시계열 물리 일관성·뼈길이 정합·CoT 논리·JSON 포맷·[미래]이종센서)은 SFT 게이트 통과 후 후속 plan. 보상 설계는 노트북 belle 노트에 완비.

### 학습셋·라벨링 (Wave 0 — 모든 것의 선행)
- **D-08 (시드 0기 = 보유 자산):** 정은지 13영상+일부러-실수 페어, 실사용 371건, 2026-07-06 실증 케이스(피터팬 위양성·power-spin), Phase 18 eval 라벨. **kip-up 편중 금지 — 학습셋·eval 모두 전 동작(+미보유 동작) 균등 구성** (belle 2026-07-06 재확인).
- **D-09 (유튜브 수집 확정):** 로드맵 원안대로 공개 폴 영상 수집 — 대회 영상=정타 버킷(IPSF 공식 아카이브 1순위), 튜토리얼 "흔한 실수" 세그먼트=fault 버킷. 출처 로그(provenance, 실사 대비) + 학습 전용(재배포 금지).
- **D-10 (라벨 생성 3경로):** (a) 좌표 보정 = 깨끗한 시퀀스에 합성 교란 주입(정답=원좌표, 자가 생성), (b) 짚기/코칭 = Gemini 교사 증류 + LLM judge 필터(7점 미만 폐기) + 반복/물리불가 궤적 휴리스틱 필터, (c) **Gemini shadow 로깅 지금 시작** — 프로덕션 판정 로그가 그대로 증류 라벨로 적재됨. 사람 숫자 점수 라벨 영구 금지(버킷만).
- **D-11 (JSON 규격 철칙):** 결측=Null 고정(키 삭제 금지)·키 알파벳 정렬·프롬프트 키 리스트 사전 바인딩(값만 나열)·태스크 무관 관절 사전 필터·좌표 `<loc_NNN>` 이산화. T3(순수 텍스트 시간추론 합성 데이터) SFT 혼합으로 LLM 백본 시간추론 각성 + 순수 텍스트 instruction 혼합(언어능력 감퇴 방지).

### 고객 데이터 플라이휠 (동의 구조 — belle "옵트인 체크 안 눌러줌" 반영)
- **D-12 (동의 3겹, 개별 옵트인 강제 없음):** (1) 파일럿 = 학원 참가 동의서 1장에 학습 활용 포함(오프라인 포괄), (2) 정식 = 처리방침 고지 + **가명처리(얼굴 블러+식별자 제거) 후 학습 활용** — 가명정보의 과학적 연구 목적 활용 구조로 동의 의존 최소화(모델은 포즈/모션만 학습, 얼굴 픽셀 불필요), (3) 출시 전 법률 검토 1회 문서화(DD 대비). 고지 문구는 온보딩 phase(SCENARIO 0.5)에서 구현, 수집·가명처리·적재 파이프라인은 Phase 22 안.

### 전환·서빙 전략
- **D-13 (shadow 병행 기본):** 같은 입력을 Gemini와 자체 모델 양쪽에 태워 verdict 비교 로그 축적, 역할별 게이트 통과 시 swap. 순서: veto(결함 짚기) → recognizer(인식/구간 분할) → coach(D-02 품질 게이트 후).
- **D-14 (서빙 위치):** 기존 4090 Pod에 vLLM(AWQ 4-bit) 추가가 기본, NLF/RTMW와 VRAM 충돌 시 별도 pod. 부수효과: Gemini File API 업로드/폴링 라운드트립 소멸 → Phase 27(속도 1분) 기여.
- **D-15 (출하 게이트):** Phase 24의 4종(추적성·단조성·결정성·일반화) + EVAL18 6페어 무회귀 + **전 동작 균등 검증(미보유 동작 포함)** + shadow 대비 "Gemini 이상" 증명. eval/batch는 순차 실행(동시성 오염 금지).

### 실행 순서 (Wave 구조 — belle "1~8 모두, 네가 잘 잡아라")
- **D-16:** Wave 0 데이터 엔진(수집+스키마+합성라벨+shadow 로깅) → Wave 1 bake-off → Wave 2 SFT v1+eval 게이트 → Wave 3 shadow 배포→순차 swap → Wave 4 Cascade RL(후속 plan). 교정 시각물은 별도 phase(병렬, 앱 트랙).

### Claude's Discretion
- bake-off 하네스 설계, 프레임 샘플링/토큰 압축 파라미터, 학습 하이퍼파라미터, vLLM 서빙 구성, 수집 파이프라인 구현 세부. 학습 GPU 임대(RunPod)는 진행하며 belle 알림(로드맵 원안 유지).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 근거 자료 (belle 지시: 24년 자료 금지, 이 노트북이 기준)
- NotebookLM "LLM, Finetunig Guide" — https://notebooklm.google.com/notebook/b7710c85-8113-4086-89d6-8e3f65d15dab (97 소스 + **belle 노트 25개 = 실질 설계서**; nlm MCP `note` action=list 로 접근)
- 메모리 요약: `~/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/phase22-vlm-notebook-2026-guide.md`

### 채점 철학·게이트 (변경 금지)
- `.planning/phases/24-transparent-deduction-scoring/24-CONTEXT.md` — ND-01~07 (모델은 점수 X, 감점 엔진·eval 4종 게이트)
- `.planning/PILOT-FEEDBACK-2026-07-06.md` — A2 피터팬 위양성·A3 power-spin 싱크 = 학습/검증 케이스
- `.planning/SCENARIO.md` — 여정 중심축 (본 phase = 2·3단계 태깅)

### 교체 대상 코드 (plan 단계에서 현재 코드 재확인 필수)
- `backend/shared/python/sunity_shared/analysis/interfaces.py` — Protocol 어댑터 경계 (swap 지점)
- `backend/shared/python/sunity_shared/analysis/` 의 gemini_vision_scorer·recognizer(technique.py)·coach_writer — Gemini 의존 3역할
- `backend/functions/pipeline/app.py::_process` + `backend/runpod_inference/server.py` — 단일 분석 경로 (shadow 배선 지점)
- `backend/evals/phase18/` — known-answer eval baseline

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- PoseEngine/recognizer 인터페이스 추상화(rtmw-free-stack-pivot) — 판정기를 인터페이스 뒤에서 swap 가능하게 이미 설계됨
- `gemini_vision_scorer` 출력 계약(faultKey/measurement target enum) — 자체 모델 출력 스키마의 시드
- KeypointOverlay/fault_zoom 렌더 체계 — D-01 시각 스펙(SVG/벡터)의 소비처
- Phase 18/24/25 eval 하네스(run_sweep, assert_gates) — bake-off·SFT 게이트에 재사용
- Gemini File API 삭제/캐시 인프라 — shadow 로깅 파이프라인 기반

### Established Patterns
- 어댑터 lazy-import + Protocol 경계, 계약 3-way lockstep(TS/Python/contract.md) — 리포트 스키마 확장 시 준수
- 파이프라인 동시성 비안전 — eval 순차 실행

### Integration Points
- RunPod Pod(4090+Volume): vLLM 서빙 추가 지점. Lambda env `RUNPOD_ANALYZE_URL` 체계 재사용
- Firestore `users/{uid}/analyses` — shadow verdict 비교 로그 저장 위치 후보

</code_context>

<specifics>
## Specific Ideas

- belle: "폴스포츠+종목별 스포츠 모션 분석 최고 앱만 생각해라" — 태스크 정의를 폴스포츠 전용으로 좁히지 말고 종목 일반화 가능한 스키마로(동작 프로파일/criterion 주입형).
- belle: "스포츠 분석 업계의 힉스필드" — 외부 API로 시작해 자체 파인튜닝으로 대체하며 플랫폼화. 교정 실루엣도 이 순서(외부 생성 API → 자체 헤드).
- belle 노트의 학습 JSONL 예시(system: 스포츠 모션 분석 전문가 / user: video+RTMW_Data / assistant: `<thought>`+보정 JSON+코칭)가 데이터 포맷의 원형.

</specifics>

<deferred>
## Deferred Ideas

- **교정 시각물 phase (신규, 앱 트랙, Phase 22와 병렬)** — 1단: 기하 오버레이 렌더(목표 각도 화살표·이상 궤적, 지금 데이터로 Gemini MVP에 즉시). 2단: 외부 이미지 생성/편집 API로 교정 실루엣 프리미엄 프로토타입 + 통과 품질분을 v2 학습 페어로 적재. 로드맵 등재 필요.
- **v2 (같은 백본에 추가)** — 자체 생성 헤드(InternVL-U 아키텍처 차용, NTP:FM 손실, 3단계 커리큘럼) / 분할 마스크(<SEG>+LISA류 디코더) / 반복 카운팅.
- **백로그** — 하드웨어 행동 토큰(짐벌/로봇 트레이너), 에이전틱 툴콜(SQL/시뮬레이터), mmWave 레이더 결합(가려짐 보상).
- 종목 확장(폴 외 스포츠) — 스키마는 일반화형으로 두되 학습·검증은 폴 먼저.

</deferred>

---

## Addendum — 2026-07-10 belle: v2 생성 헤드 후보 확대 (D-03 관련, 원문 무변경)

- belle 이 build.nvidia.com 에서 Cosmos3 세대(Nano/Super) 발견 → 검토 결과 **v1 분석엔진 bake-off 부적합**(`cosmos3_omni` 신규 아키텍처 = ms-swift 미지원, 디퓨전 타워 동반) → **v2 생성 엔진 후보로 등재** 확정 (사용 아님, 등재만).
- 실측 사실:
  - `nvidia/Cosmos3-Nano`: safetensors 34.9GB, cosmos3_omni(텍스트·이미지·비디오·오디오·액션 생성 옴니), gated 아님, license:other(NVIDIA), **A100 80GB 단일 탑재 가능** → v2 실전 배포형 후보.
  - `nvidia/Cosmos3-Super`: safetensors 132.6GB → **A100 80GB 단일 로드 불가(멀티 GPU 필수)**. 품질 상한 참조용 / 양자화·프리미엄 배치 생성 검토 대상.
- **결정 원칙**: v2 승부는 v2 설계 시점에 **InternVL-U(아키텍처 차용) vs Cosmos3-Nano (+Super 참조)** 병렬 후보로 장당 생성 원가·지연 실측 비교. 지금 확정 아님 — D-03 의 "InternVL-U 아키텍처 차용" 원문은 유지하되 후보군이 확대된 것.
- 라이선스: NVIDIA Open Model License 계열 추정 — **v2 착수 시 재확인 필요** (LICENSE-AUDIT §2-1 플래그 참조).

---

*Phase: 22-자체 비전 모델 파인튜닝 (오픈 모델 전환)*
*Context gathered: 2026-07-06 (addendum 2026-07-10)*
