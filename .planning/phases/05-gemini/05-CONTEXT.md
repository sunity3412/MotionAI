# Phase 5: Gemini 기술 인식기 (분류 한정) - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 = `TechniqueRecognizer` Protocol 의 **Gemini 어댑터** 를 production wiring 해서 현 `FallbackRecognizer` 의 보수 정책 한계 (모든 관절 BENT_OK 또는 평가 제외) 를 대체한다. 입력 = 영상 + RTMW pose 결과, 출력 = (a) 기술명 분류, (b) 4단계 (setup/hold/peak/release) 각 단계별 관절 EXTEND/BENT_OK/CONTACT 라벨, (c) 각 단계 timestamp. Gemini 는 좌표·점수·심사 판단 출력 절대 금지 — reject patterns 이미 박제.

**해결하는 문제** = Plan 23 sweep (2026-06-03) verdict `phase1_ready_to_swap=False` 의 root cause 3종 중 **1번 (FallbackRecognizer 한계 → IPSF criteria 일률 180° 가정 → angle 게이트 0/5)**. Phase 5 통과 → Plan 23 sweep 재실행 → angle 5/5 PASS 가능성 회복 → Plan 24/25 (Wave 5/6) D-16 보류 해제 path.

**해결 안 하는 문제** (별 plan 책임):
- Root cause 2 (HoughPoleDetector 미설치) — Phase 1 잔여 또는 신설 Plan 26
- Root cause 3 (AKA 매핑 vs yaml criteria 정합 미검증) — Phase 16 + belle/NotebookLM IPSF CoP 2024-2025 재검증
- 자연어 코칭 번역 — Phase 11 Cerebras llama3.1 유지 (Gemini 역할 X)
- "돈 내겠는데?" 사용자 체감 게이트 — Phase 1 + 5 + 6 + 7 + 9 + 12 + 13 chain 완성 시점 (Phase 5 단독 = 위양성 0 + 수치 신뢰 1차 게이트만)

</domain>

<decisions>
## Implementation Decisions

### Scope (인식 범위)

- **D-01:** v1 인식 스코프 = **5영상 인버트 계열 우선** (`ref-climb` / `ref-foxtop` / `ref-foxtop-split` / `ref-invert` / `ref-sideway-spin`). **게이트 = "정은지 reference 측정값 기준 5/5 PASS"** (NotebookLM IPSF lookup 2026-06-04 박제 후 belle 승인 — IPSF 직접 채점 박제 path X, 분기 2 정은지 reference path 박제). 박제 [[studio-term-3branch-system.md]] 분기 2 + [[analysis-objectivity-no-human-scores.md]] 객관 측정값 정합.
- **D-02:** Phase 16 AKA 매핑 13개 + 분기 2 정은지 reference 비등재 동작 (폭스탑 등) 의 확장은 v1 외. v2 또는 Phase 5 후속 plan 으로 미룸. v1 = "5영상 게이트 통과" 단일 목표.
- **D-03:** 스코프 밖 동작 = "미등록" 처리 → Page 9 절대 트랙 단독 채점 + TERM-COPY-01 분기 3 카피 노출 + 키워드 자동 박제 (D-09 참조).

### Output Shape (인식 출력 구조)

- **D-04:** Gemini 호출 1회 → 출력 = **기술명 + 4단계 (setup/hold/peak/release) 라벨 + 4단계 timestamp**. (Y+Z) 풀 버전. 호출 구조 = Plan 01-13 spike `gemini_moment_extractor.py` 의 `KeyMoment` dataclass 재사용.
- **D-05:** **v1 채점 = hold moment 라벨만 활성**. setup/peak/release 라벨은 Firestore 분석 doc 에 박제만 (사용자 노출 X, dimensions.py 미소비). yaml `setup_moment` / `peak_moment` / `release_moment` 비어있어 v1 dead data — 정상.
- **D-06:** **v2 자동 활성 path**: yaml `setup_moment` / `peak_moment` / `release_moment` criteria 가 belle/강사/NotebookLM IPSF CoP lookup 으로 채워지면 코드 변경 0 으로 자동 활성. 박제 [[mvp-simple-pilot-quality.md]] "구조만 열어두기" 정신 정합.
- **D-07:** timestamp 오차 = Gemini multimodal 시점 인식 ±1~2초 인정. hold (2~5초 지속) 는 windowing 으로 흡수. v2 peak (0.5~1초 짧음) 활성 시 timestamp 정확도 재평가 (별 plan).
- **D-08:** Gemini = EXTEND/BENT_OK/CONTACT **라벨러만**. yaml 의 `angle_target` / `tolerance` / `minimum` 수치는 **정은지 reference 측정값 (분기 2 path)** 박제 — Gemini 가 수치 생성 X (좌표·점수·판단 출력 금지 정신 보호). NotebookLM IPSF lookup 2026-06-04 결과: 5영상 yaml 의 IPSF 직접 박제 source 없음 (ref-climb 도 hold angle 채점 X, ref-invert 도 Body Position 채점만, 나머지 3영상 미등재). yaml source_ref 정정 = Phase 5 첫 plan 책임 (D-17).

### Fallback Policy (3케이스 분리)

- **D-09:** **3 케이스 분리 처리** — 박제 SCORE-05 (5트랙) + TERM-COPY-01 (분기 3 카피) 정합.

  | 케이스 | Trigger | 처리 | 사용자 노출 |
  |---|---|---|---|
  | (1) API 실패 | 네트워크 timeout / API key 만료 / Gemini 서비스 중단 | FallbackRecognizer + 분석 진행 (success #2 정신) | "분석 신뢰도 낮음" 결과 화면 표기 |
  | (2) Low confidence | Gemini 응답 받지만 confidence 낮음 | angle/line 차원 채점 skip + Page 9 절대 트랙만 (SCORE-05 정합) | "분석 신뢰도 낮음" 표기 |
  | (3) 미등록 동작 | Gemini "scope 밖" 또는 "분류 불가" 응답 | Page 9 절대 트랙 단독 + 키워드/영상 익명 박제 (TERM-DATA-01 분기 3 자동 수집) | TERM-COPY-01 카피 그대로 노출 ("공식 등재되어 있지 않은...") |

- **D-10:** Low confidence 임계값 정의 = 별 plan 책임 (v1 박제 = "confidence < threshold → case 2", threshold 값은 5영상 sweep 실측 후 박제).
- **D-11:** "신뢰도 낮음" UI 카피 = design.md / Figma fileKey jrdI7kp245HkPfLB0nclsz 의 Phase 5 결과 화면 컴포넌트 참조 (별 plan 또는 Phase 12 책임).

### Call Architecture (호출 위치 · Cascade · 캡싱)

- **D-12:** **호출 위치 = RunPod Pod 안 1pass**. RTMW pose 산출 후 같은 Pod 안에서 Gemini 호출 → label 산출 → 분석 흐름 그대로. 박제 [[gsd-pod-work-push-first.md]] Pod 작업 단위 정합. GPU idle 1~3초 (Gemini 대기) 인정.
- **D-13:** **모델 = Gemini 3.1 Pro 단일** (3.0 삭제). belle 2026-06-04 확정 — 비용 cascade (Flash → Pro) 미적용. 박제 [[feedback-analysis-first.md]] "분석 정확도 우선, 비용 하한 구독료 수준" 정합. 3.5 Flash 는 후속 비용 분석 후 별 plan 평가.
- **D-14:** **캡싱 = 영상 hash 기반 (S3 ETag 또는 SHA256)**. 같은 영상 재분석 시 Gemini 호출 0, Firestore 의 `gemini_result` 박제만 lookup. Plan 23 sweep 재실행 + belle 시연 시 비용 0 + 지연 0 효과. 박제 [[mvp-simple-pilot-quality.md]] "시연 화면 마감까지" 정합.
- **D-15:** API 키 path = AWS Parameter Store `/sunity/motion/gemini-api-key` (SecureString, belle 박제 완료 2026-06-01). RunPod Pod env 주입 wiring = Phase 5 첫 plan 책임. env `GEMINI_API_KEY` fallback 유지 (`gemini_moment_extractor.py` 기존 구현).
- **D-16:** `google-generativeai` + `boto3` lazy import 유지 — 모듈 로드 시점 0 import (`gemini_moment_extractor.py` 박제 패턴 그대로). 로컬 단위 테스트 + Lambda 콜드스타트 보호.

### yaml Source 정정 (NotebookLM IPSF lookup 후 박제, 2026-06-04 belle 승인)

- **D-17:** **Phase 5 첫 plan = yaml source 정은지 reference 측정값 정정 작업** (5영상 reference 영상 측정 → yaml hold_moment 6관절 angle_target / tolerance / minimum 정은지 실측값으로 갱신 + source_ref = "정은지 reference 측정값 (분기 2 path)" 박제). Gemini wiring (D-04~D-16) 은 yaml 정정 후 plan. 박제 [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" 정신 = "정은지 reference 기준 5/5 PASS" 게이트 (D-01) 박제 정합.
- **D-18:** yaml 정정 path = (1) 정은지 reference 영상 5개 (각 motion 1개) RTMW pose 산출 → (2) hold moment timestamp 박제 (수동 또는 belle 직접 시점 박제) → (3) 6관절 angle 측정값 박제 → (4) tolerance / minimum 수치 박제 룰 (예: tolerance = 측정값 ±15°, minimum = 측정값 - 25°). 룰 자체는 첫 plan 안에서 belle 승인.
- **D-19:** ref-invert 의 Body Position Inverted (골반-머리 상대 위치 ±20°) 차원 신규 추가는 Phase 5 scope 외 — 별 phase 또는 Phase 8 (중심축 이탈) 책임 박제. v1 ref-invert = 6관절 angle 박제 (정은지 측정값) 단독 채점.
- **D-20:** ref-climb 의 "이동 횟수 2회 이상" 차원 신규 추가는 Phase 5 scope 외 — 별 phase 책임 박제. v1 ref-climb = 6관절 angle 박제 (정은지 측정값) 단독 채점.

### Claude's Discretion

- Firestore `gemini_result` 박제 schema 구체적 필드 = 출력 구조 D-04 박제로 자연 결정 (gemini_moment_extractor.py 의 KeyMoment dataclass 직렬화).
- 영상 입력 형식 (전체 영상 vs sample frames) = Gemini multimodal SDK API 권장 path (10~30초 폴 영상 전체 입력이 표준, sample 필요 시 별 plan).
- 프롬프트 설계 (좌표/판단/점수 거부 강제 + JSON schema 강제) = 기존 `_COORDINATE_REJECT_PATTERNS` / `_SCORE_REJECT_PATTERNS` / `_JUDGMENT_REJECT_PATTERNS` 박제 + response_mime_type=application/json 강제 — 구체 prompt 문구는 planner 자유.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### NotebookLM IPSF lookup (2026-06-04 박제, belle 승인 후)

- `.planning/phases/05-gemini/05-IPSF-LOOKUP.md` — **MANDATORY** NotebookLM IPSF Code of Points 2024-2025 lookup 결과. 5영상 catalog 분석 + IPSF source 박제 X 결론 + 옵션 (가+다) 박제 정신 정합 path. Phase 5 첫 plan (yaml 정정 작업) source.

### REQUIREMENTS & ROADMAP

- `.planning/REQUIREMENTS.md` §"점수 신뢰도 (Scoring)" SCORE-01 — Phase 5 단일 요구사항. Gemini 어댑터 + 좌표·판단 출력 금지.
- `.planning/REQUIREMENTS.md` §"학원 용어" TERM-COPY-01 — 미등록 동작 분기 3 카피 박제 (D-09 케이스 3).
- `.planning/REQUIREMENTS.md` SCORE-05 — 5트랙 채점 v1 scope. Page 9 절대 트랙 = D-09 fallback path 의 채점 단독 가능 근거.
- `.planning/ROADMAP.md` §"Phase 5: Gemini 기술 인식기 (분류 한정)" — Goal, Success Criteria 4개, Depends on Phase 1, External dependency.

### 기존 Gemini 인프라 (Plan 01-13 spike 박제)

- `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` — `KeyMoment` dataclass + `GeminiMomentExtractor` + `VALID_MOMENT_KEYS` enum + reject patterns. Phase 5 production wiring 의 코드 재사용 base.
- `backend/shared/python/sunity_shared/judging/geometric_criterion.py` — `VALID_MOMENT_KEYS` 정의. 4단계 moment enum 공유.
- `backend/shared/python/sunity_shared/judging/moment_dimensions.py` — `measure_moment_angles` / `compute_criteria_gap` / `score_moment` (line/angle 차원). Phase 5 결과 소비 path.
- `backend/research/spikes/spike_gemini_moment.py` — Plan 01-13 spike CLI. live mode 미실행 (measurement_unreliable_blocked verdict). Phase 5 wiring 의 reference 코드.

### TechniqueRecognizer 인터페이스 (대체 대상)

- `backend/shared/python/sunity_shared/analysis/technique.py` — `TechniqueProfile` dataclass + `TechniqueRecognizer` Protocol + `FallbackRecognizer` 보수 정책. Phase 5 = 이 Protocol 의 Gemini 어댑터 구현.
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — IPSF criteria 채점 본체. hold_moment EXTEND 가정 의존성 박제 — D-08 의 라벨러 출력 소비처.

### yaml criteria (5영상 박제, v1 채점 source)

- `backend/judging_data/criteria/ref-climb.yaml`
- `backend/judging_data/criteria/ref-foxtop.yaml` — D-04 출력 구조 예시 (hold_moment 6관절 박제, setup/peak/release 비어있음 — v1 dead label 박제 정신 박제)
- `backend/judging_data/criteria/ref-foxtop-split.yaml`
- `backend/judging_data/criteria/ref-invert.yaml`
- `backend/judging_data/criteria/ref-sideway-spin.yaml`
- `backend/judging_data/README.md` — yaml 작성 가이드. v2 setup/peak/release 채울 시 참조.

### 의존 박제 (memory)

- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/feedback-analysis-first.md` — "분석 정확도 우선, 비용 하한 구독료 수준". D-13 모델 선택 + D-14 캡싱 근거.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/mvp-simple-pilot-quality.md` — "구조만 열어두기 + 시연 화면 마감까지". D-06 v2 자동 활성 + D-14 캡싱 근거.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/gap-and-line-angle-mandatory-gates.md` — "강등/우회 금지". D-01 5영상 sweep 게이트 정신.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/analysis-objectivity-no-human-scores.md` — "사람 점수 라벨링 금지, 객관 수치 라벨링 OK". D-08 Gemini 라벨러만 + reject patterns 정신.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/scoring-dimensions-ipsf.md` — "신체부위 아님, 기술 조건부 전환". Phase 5 = 기술 조건부 라벨링의 자동화.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/studio-term-3branch-system.md` — D-09 케이스 3 분기 3 자동 수집 + TERM-COPY-01 카피.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/ipsf-5-track-scoring.md` — D-09 케이스 2/3 Page 9 절대 트랙 단독 채점 근거.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/gsd-pod-work-push-first.md` — D-12 Pod 안 1pass 호출 정신.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/runpod-gpu-env.md` — D-15 Pod env 박제 누적. 현 Pod (RTX 3090, Plan 11 진입 준비됨) 환경에 Gemini API 키 주입 path.
- `.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/notebook-lm-pole-sports.md` — D-06 v2 yaml 채우기 작업 시 NotebookLM IPSF CoP 2024-2025 lookup.

### 인접 Phase 의존성

- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-23-SUMMARY.md` — Plan 23 sweep verdict (angle 0/5 root cause 3종). Phase 5 가 푸는 정확한 실패 박제.
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-SUMMARY.md` — Plan 13 spike verdict (measurement_unreliable_blocked). Phase 5 와 Plan 13 의 차이 박제 path.
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-15-SUMMARY.md` — IPSF GeometricCriterion 스키마 + ref-foxtop yaml 1차 박제 (commit 861fb3a, 4264001). D-08 yaml source 박제.
- `.planning/phases/16-studio-term-foundation/` — TERM-DATA-01 + TERM-COPY-01 박제. Phase 5 D-09 케이스 3 처리의 카피/데이터 source.

### 외부 의존

- AWS Parameter Store `/sunity/motion/gemini-api-key` (SecureString) — belle 박제 2026-06-01. Pod env 주입 wiring 첫 plan 책임.
- Google AI Studio (belle 계정) — Gemini 3.1 Pro API quota 모니터링. 별도 박제 path.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`gemini_moment_extractor.py`** (Plan 01-13 spike): `KeyMoment` dataclass + `GeminiMomentExtractor` 클래스 + reject patterns 박제됨. Phase 5 production wiring 의 직접 재사용 base. 단 spike 코드 → production 코드 승격 시 lazy import 패턴 / Pod 안 호출 path / hash 캡싱 layer 추가.
- **`TechniqueRecognizer` Protocol + `FallbackRecognizer`** (technique.py): Phase 5 = 이 Protocol 의 새 어댑터 구현. dimensions.py 가 Protocol 만 의존 — 어댑터 교체 시 채점 코드 변경 0.
- **`KeyMoment` + `VALID_MOMENT_KEYS`** (judging/geometric_criterion.py): 4단계 moment enum 이미 정의. D-04 출력 구조 그대로 매칭.
- **`measure_moment_angles` + `score_moment`** (judging/moment_dimensions.py): hold moment 채점 본체 박제. D-05 v1 채점 소비처.
- **`AWS Parameter Store SecureString` lazy boto3 lookup** (gemini_moment_extractor.py 박제 패턴): API 키 path 재사용.

### Established Patterns

- **Lazy import (D-16)**: `google-generativeai` + `boto3` 모듈 로드 시점 0 import. 단위 테스트 + Lambda 콜드스타트 보호 박제 패턴.
- **Reject patterns (D-08)**: `_COORDINATE_REJECT_PATTERNS` / `_SCORE_REJECT_PATTERNS` / `_JUDGMENT_REJECT_PATTERNS` 박제됨. 응답 좌표·점수·판단 감지 시 `ValueError` 발생 — analysis-objectivity 정신 강제.
- **Protocol-based adapter (D-08)**: `TechniqueRecognizer` Protocol + `FallbackRecognizer` / `GeminiRecognizer` 어댑터 교체. dimensions.py 의존 인터페이스만 — 어댑터 swap 비용 0.
- **RunPod Pod 단일 흐름 (D-12)**: pose_estimator → analysis 본체 → `_process` 일관 흐름 박제. Gemini 호출 = `_process` 안 한 단계 추가, Pod env / requirements / setup.sh wiring 필요.

### Integration Points

- **`backend/shared/python/sunity_shared/analysis/dimensions.py`** — `TechniqueRecognizer` Protocol 호출처. Phase 5 Gemini 어댑터 박제 후 dimensions.py 가 hold_moment EXTEND 라벨을 소비 → angle 차원 채점 동적화.
- **`backend/functions/pipeline/app.py` + `backend/runpod_inference/server.py`** — Pod `_process` 흐름. Phase 5 = `_process` 안 Gemini 호출 단계 추가 + 결과 Firestore 박제 schema 확장.
- **`backend/runpod_inference/requirements.txt`** — `google-generativeai` 추가. Pod 재기동 후 `pip install` 1회.
- **`backend/runpod_inference/setup.sh`** — Pod env 변수 `GEMINI_API_KEY` 주입 또는 Parameter Store lazy fetch path.
- **Firestore `users/{uid}/analyses/{id}` 분석 doc** — `gemini_result` 필드 신설 (4단계 라벨 + timestamp + confidence + model_version + cache_hit 메타). app `useAnalysisDoc` 가 읽음 (단 v1 사용자 노출 X — 박제 데이터 only).

</code_context>

<specifics>
## Specific Ideas

- **"돈 내겠는데?" 사용자 체감 게이트 박제**: belle 2026-06-04 의논 — 분석 정확도 chain 의 7 phase (1 + 5 + 6 + 7 + 9 + 12 + 13) 완성 시점이 진정한 "실증 의미" 도달. Phase 5 단독 = 위양성 0 + 수치 신뢰 1차 게이트만. Phase 5 게이트 정의는 (A) 수치 신뢰만 박제 — ROADMAP phase 경계 존중.
- **Gemini 3.1 Pro 모델 박제 (3.0 삭제)**: belle 2026-06-04 확정. STATE.md "Phase 5 권장 모델" 갱신 — 이전 박제 (3.0/3.1 Pro 양옵션) 의 3.0 폐기. 3.5 Flash 는 v1 미사용, 후속 비용 분석 plan 후 평가.
- **timestamp 오차 ±2초 수용** (D-07): hold 2~5초 지속 → 오차 흡수. peak 0.5~1초 짧음 — v2 활성 시 timestamp 정확도 재평가 별 plan.
- **Plan 23 sweep 재실행 = Phase 5 통과 게이트**: 5영상 (ref-climb / foxtop / foxtop-split / invert / sideway-spin) angle 5/5 PASS 목표. 통과 시 Plan 24/25 (Wave 5/6) D-16 보류 해제.
- **v1 dead label 박제 정신**: setup/peak/release 라벨 받지만 v1 사용 X — Firestore 박제만. 분석 비용 0, 미래 yaml 작업 후 자동 활성 path 박제.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 16 AKA 매핑 13개 + 분기 2 정은지 reference 비등재 동작 (폭스탑) 확장** — Phase 5 v2 또는 후속 plan. v1 = 5영상 게이트 단일 목표 (D-02).
- **Cascade 비용 절감 (3.5 Flash → 3.1 Pro)** — belle "비용보다 퀄리티" 박제로 v1 미적용. v2 비용 모니터링 분석 후 별 plan 평가.
- **setup/peak/release yaml criteria 박제 (belle/강사/NotebookLM IPSF CoP lookup)** — JUDGE-DATA-01 v1 평행 작업. Phase 5 D-06 v2 자동 활성 path 준비. Phase 16 또는 별 데이터 박제 plan.
- **Low confidence 임계값 정의** (D-10) — Phase 5 v1 wiring 후 5영상 sweep 실측 confidence 분포 기반 박제. 별 plan 또는 Phase 5 마지막 plan.
- **peak 채점 활성 시 timestamp 정확도 재평가** (D-07) — peak 0.5~1초 짧아 ±2초 오차 영향 큼. v2 peak yaml 채워지면 timestamp 추출 정확도 재평가 plan.
- **HoughPoleDetector 미설치 fix** (Plan 23 root cause 2) — Phase 1 잔여 또는 신설 Plan 26. Phase 5 와 평행 가능, 합산하면 Plan 23 sweep 게이트 통과 확률↑.
- **AKA 매핑 vs yaml criteria 정합 belle/NotebookLM 재검증** (Plan 23 root cause 3) — Phase 16 + belle 협업. Phase 5 D-04 라벨 출력으로 일부 자동 해소, 그러나 catalog 자체 정합은 별 검증.
- **Gemini API quota / 비용 모니터링 알람** — belle "비용보다 퀄리티" 정신상 v1 후순위. Pod env 박제 후 별 plan.
- **"신뢰도 낮음" UI 카피 + Figma 컴포넌트** (D-11) — Phase 5 데이터 박제 후 design.md / Figma fileKey jrdI7kp245HkPfLB0nclsz 의 Phase 5 결과 화면 컴포넌트 별 plan 또는 Phase 12 책임.

</deferred>

---

*Phase: 5-gemini*
*Context gathered: 2026-06-04*
