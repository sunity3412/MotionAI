# Phase 5: Gemini 기술 인식기 (분류 한정) - Research

**Researched:** 2026-06-04
**Domain:** Gemini multimodal video → `TechniqueRecognizer` 어댑터 production wiring
**Confidence:** MEDIUM-HIGH (Plan 01-13 spike code 재사용 base + 운영 wiring 미검증 영역 잔존)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (16건, CONTEXT.md verbatim)

**Scope (인식 범위)**
- **D-01:** v1 인식 스코프 = 5영상 인버트 계열 우선 (ref-climb / ref-foxtop / ref-foxtop-split / ref-invert / ref-sideway-spin). Plan 23 sweep 5/5 PASS 게이트 직결. yaml 5개 박제됨, 입장 최소.
- **D-02:** Phase 16 AKA 매핑 13개 + 분기 2 정은지 reference 비등재 동작 확장은 v1 외. v2 또는 후속 plan.
- **D-03:** 스코프 밖 동작 = "미등재" 처리 → Page 9 절대 트랙 단독 채점 + TERM-COPY-01 분기 3 카피 노출 + 키워드 자동 박제.

**Output Shape (인식 출력 구조)**
- **D-04:** Gemini 호출 1회 → 출력 = 기술명 + 4단계 (setup/hold/peak/release) 라벨 + 4단계 timestamp. (Y+Z) 풀 버전. Plan 01-13 spike `KeyMoment` dataclass 재사용.
- **D-05:** v1 채점 = hold moment 라벨만 활성. setup/peak/release 라벨은 Firestore 박제만 (사용자 노출 X, dimensions.py 미소비). yaml 비어있어 v1 dead data.
- **D-06:** v2 자동 활성 path: yaml setup/peak/release criteria 가 채워지면 코드 변경 0 으로 자동 활성.
- **D-07:** timestamp 오차 = Gemini multimodal 시점 인식 ±1~2초 인정. hold (2~5초) windowing 으로 흡수.
- **D-08:** Gemini = EXTEND/BENT_OK/CONTACT 라벨러만. yaml 의 angle_target=180° / tolerance=±20° / minimum=160° 수치는 IPSF source 그대로 유지.

**Fallback Policy (3케이스 분리)**
- **D-09:** 3 케이스 분리 처리 — (1) API 실패 → FallbackRecognizer + 분석 진행, (2) Low confidence → angle/line skip + Page 9 절대 트랙만, (3) 미등록 → Page 9 단독 + 자동 수집 + TERM-COPY-01 카피.
- **D-10:** Low confidence 임계값 정의 = 별 plan. v1 박제만 ("confidence < threshold → case 2").
- **D-11:** "신뢰도 낮음" UI 카피 = design.md / Figma Phase 5 결과 화면 참조 (별 plan).

**Call Architecture**
- **D-12:** 호출 위치 = RunPod Pod 안 1pass. RTMW pose 산출 후 같은 Pod 안에서 Gemini 호출. GPU idle 1~3초 인정.
- **D-13:** 모델 = Gemini 3.1 Pro 단일 (3.0 삭제). belle 2026-06-04 확정. 3.5 Flash 는 후속 비용 분석 후 별 plan.
- **D-14:** 캡싱 = 영상 hash 기반 (S3 ETag 또는 SHA256). Firestore gemini_result 박제만 lookup.
- **D-15:** API 키 path = AWS Parameter Store `/sunity/motion/gemini-api-key` (SecureString). RunPod Pod env 주입 wiring = Phase 5 첫 plan 책임.
- **D-16:** `google-generativeai` + `boto3` lazy import 유지 — gemini_moment_extractor.py 박제 패턴 그대로.

### Claude's Discretion
- Firestore `gemini_result` 박제 schema 구체적 필드 (D-04 박제 → KeyMoment dataclass 직렬화).
- 영상 입력 형식 (전체 영상 vs sample frames) — Gemini multimodal SDK 권장 path.
- 프롬프트 설계 (좌표/판단/점수 거부 + JSON schema 강제) — 기존 reject patterns + response_mime_type=application/json 강제.

### Deferred Ideas (OUT OF SCOPE)
- Phase 16 AKA 매핑 13개 + 폭스탑 확장 — v2 또는 후속 plan.
- Cascade 비용 절감 (3.5 Flash → 3.1 Pro) — belle "비용보다 퀄리티" v1 미적용.
- setup/peak/release yaml criteria 박제 — JUDGE-DATA-01 v1 평행 (Phase 16).
- Low confidence 임계값 정의 (D-10) — v1 wiring 후 5영상 sweep 실측 후 박제.
- peak 채점 활성 시 timestamp 정확도 재평가 (D-07).
- HoughPoleDetector 미설치 fix (Plan 23 root cause 2) — Phase 1 잔여 또는 Plan 26.
- AKA 매핑 vs yaml criteria 정합 재검증 (Plan 23 root cause 3) — Phase 16 + belle/NotebookLM.
- Gemini API quota / 비용 모니터링 알람.
- 신뢰도 낮음 UI 카피 + Figma 컴포넌트 (D-11).
</user_constraints>

---

<phase_requirements>
## Phase Requirements (REQUIREMENTS.md 매핑)

| ID | Description | Research Support |
|----|-------------|------------------|
| SCORE-01 | 기술 인식기(Gemini 어댑터)가 영상에서 기술을 인식하고 관절별 EXTEND/BENT 프로파일을 반환. Gemini는 분류·자연어 번역만 (좌표·판단 출력 금지) | Plan 01-13 spike `GeminiMomentExtractor` + `_COORDINATE/SCORE/JUDGMENT_REJECT_PATTERNS` 3중 정규식 가드 박제됨. `TechniqueRecognizer` Protocol + `TechniqueProfile.joint_expectations` 박제됨 — Gemini 어댑터 = 두 박제의 결합 |
| SCORE-05 | 5트랙 채점 — Page 9 절대 공통 트랙 단독으로 채점 가능 (mode3 reference 없는 채점 근거) | D-09 케이스 2/3 Page 9 단독 fallback path 박제. `dimensions.absolute_dimension_scores` (stability + line) 가 reference 없이 동작 — Page 9 트랙의 실제 코드 path |
| TERM-COPY-01 | 분기 3 UX 카피 박제 — "공식 등재되어 있지 않은 기술명입니다..." 변경 금지 | D-09 케이스 3 (미등록 동작) wiring path. Firestore `gemini_result.scope_status="unregistered"` + TERM-DATA-01 분기 3 자동 수집 트리거 |
</phase_requirements>

---

## Summary

Phase 5 는 Plan 01-13 spike (`backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py`) 박제 코드를 **production wiring** 으로 승격하는 작업이다. spike 자체는 이미 작성됐고 belle Pod live mode 도 1회 실행됐다 (verdict `measurement_unreliable_blocked`, ref-invert 5/5 minimum fail). 그러나 Phase 5 는 다음 5가지를 새로 wiring 해야 한다:

1. **`TechniqueRecognizer` Protocol 에 `GeminiTechniqueRecognizer` 어댑터 구현** — 현재 `_RECOGNIZER` 는 `FallbackRecognizer` 고정 (pipeline/app.py:120). Gemini 어댑터가 `recognize(angles, frames=video_path) → TechniqueProfile` 으로 반환해야 `dimensions.py` (line 차원) 가 EXTEND 라벨을 소비.
2. **3-case fallback wiring** — D-09 박제. API 실패 / Low confidence / 미등록 3분기.
3. **영상 hash 캡싱 layer** — D-14 박제. Firestore `users/{uid}/analyses/{id}.gemini_result` 또는 `motion_cache/{hash}` 컬렉션 (어느쪽?).
4. **RunPod Pod env wiring** — D-15. `setup.sh` 에 Parameter Store fetch 또는 `GEMINI_API_KEY` env. `requirements.txt` 에 `google-genai` 추가.
5. **Plan 23 sweep 재실행 통합** — `compare_rtmw_vs_ipsf.py` 의 `compare_to_ipsf` 가 `FallbackRecognizer` 로 호출 (line 334) → `GeminiTechniqueRecognizer` 로 swap. 게이트 = ref-foxtop-split, ref-foxtop, ref-invert, ref-sideway-spin angle 4/4 PASS + (ref-climb IPSF 비해당 = PASS 그대로) = 5/5.

**Primary recommendation:** Plan 01-13 spike 의 `GeminiMomentExtractor` 를 wrapper 로 감싼 `GeminiTechniqueRecognizer` 어댑터 신설 + `pipeline._RECOGNIZER` 교체 + 영상 hash 캡싱 layer + Plan 23 sweep `--recognizer gemini` flag. spike 코드 0줄 수정 — 어댑터 박제 path 정신 유지.

**핵심 주의:** Plan 01-13 verdict 의 measurement_unreliable_blocked 는 *측정 chain (RTMPose+MB lift)* 의 약점이지 Gemini 자체의 약점이 아니다. Plan 21+22 RTMW pivot 후 측정 chain 이 RTMW wholebody (Plan 23 sweep 의 `rtmw_mean_score` 93~95) 로 교체됐으므로 Plan 13 의 RTMPose+MB inversion failure 와 본 Phase 5 의 RTMW 환경은 직접 비교 불가. 그러나 Plan 23 sweep verdict 의 root cause 1 (FallbackRecognizer 한계, IPSF target=180° 일률 가정) 은 Gemini 어댑터로 해결 가능 — measured 21~107° (사실은 BENT_OK 의도된 굽힘) 가 어떤 관절은 EXTEND, 어떤 관절은 BENT_OK 로 동적 라벨링 → dimensions.line_score 가 EXTEND 관절만 채점 → 위양성 0.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gemini API 호출 (multimodal video → 4단계 라벨) | API/Backend (RunPod Pod) | — | D-12 박제. Pod 안 1pass — RTMW pose 산출 후 같은 Pod context 안 |
| `TechniqueProfile` 생성 (joint_expectations dict) | API/Backend (sunity_shared.judging) | — | Plan 01-13 spike 코드 base. 어댑터 패턴으로 `TechniqueRecognizer` Protocol 구현 |
| 영상 hash 계산 + Firestore lookup | API/Backend (Pod 또는 firestore_admin) | — | D-14 박제. Pod 가 S3 영상 다운로드 후 SHA256 또는 ETag 사용 |
| `gemini_result` Firestore 박제 | Database/Storage | API/Backend (firestore_admin) | Firestore `users/{uid}/analyses/{id}` 또는 `gemini_cache/{hash}` |
| API 키 fetch | Configuration (Parameter Store) | API/Backend (Pod env) | D-15 박제. SecureString lazy boto3 fetch + env fallback |
| 3-case fallback routing | API/Backend (pipeline `_process`) | — | API 실패/Low conf/미등록 → 채점 path 분기. `dimensions.absolute_dimension_scores` (Page 9) 또는 `dimensions.line_score + angle_score` 선택 |
| TERM-DATA-01 분기 3 자동 수집 | Database/Storage (Firestore) | API/Backend (D-09 case 3 트리거) | Phase 16 데이터 박제. Phase 5 = trigger 만 (집계는 Phase 16) |
| Plan 23 sweep 재실행 (`compare_rtmw_vs_ipsf.py`) | Evaluation Script (research/evaluations) | — | Wave 3 gate 검증. Pod 에서만 실행 |

---

## Standard Stack

### Core (이미 박제됨 — 재사용)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | latest (≥1.0, 2025-Q2+) [VERIFIED: ai.google.dev/gemini-api/docs/migrate] | Gemini API client (신 SDK, `AQ.` 키 포맷 + v1 endpoint 지원) | Legacy `google-generativeai` 0.8.x 는 2025-말 새 AI Studio 키 포맷 미지원 (Plan 01-13 4 fix commit 569a076 박제). 신 SDK 필수 |
| `boto3` | ≥1.34,<2.0 | AWS SSM Parameter Store fetch (Gemini API 키) | 기존 `runpod_inference/requirements.txt` 박제 |
| `firebase-admin` | ≥6.5,<7.0 | Firestore `gemini_result` 박제 | 기존 박제 |
| `numpy` | ≥1.26,<3 | RTMW pose → angles 변환 | 기존 박제 |

### Supporting (Plan 01-13 spike 박제 코드 — 재사용)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sunity_shared.judging.GeminiMomentExtractor` | 박제됨 | Gemini 호출 + KeyMoment 파싱 + reject patterns 3중 가드 | 어댑터 wrapper 안에서 호출 |
| `sunity_shared.judging.KeyMoment` | 박제됨 | 4단계 라벨 dataclass (frozen) | Gemini 응답 → TechniqueProfile 변환 중간 표현 |
| `sunity_shared.judging.assign_frame_indices` | 박제됨 | timestamp_seconds → frame_index (fps 9.0 기반) | 영상 frame 시퀀스와 라벨 매핑 |
| `sunity_shared.analysis.technique.TechniqueProfile` | 박제됨 | `joint_expectations: dict[str, EXTEND/BENT_OK/CONTACT]` | Gemini 어댑터의 최종 출력 |
| `sunity_shared.analysis.technique.TechniqueRecognizer` Protocol | 박제됨 | 인식 어댑터 인터페이스 | Gemini 어댑터가 구현 |
| `sunity_shared.judging.load_grouped_criteria` | 박제됨 | yaml → moment 별 GeometricCriterion dict | 어댑터가 motion 인식 후 yaml lookup (미등록 = []) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `google-genai` (신 SDK) | `google-generativeai` 0.8.x (legacy) | **거부됨** — 2025-말 새 AI Studio `AQ.` 키 포맷 미지원 (Plan 01-13 commit 569a076 박제). 신 SDK 필수 |
| Pod 안 1pass (D-12) | Lambda 분리 → SQS chain | **거부됨** (D-12 박제). GPU idle 1-3초 < SQS overhead + 동기 path 단순성 우위 |
| Firestore 캡싱 (D-14) | Redis/DynamoDB | **거부됨** — 기존 인프라 재사용. belle 시연 재현 비용 0 만 충족하면 충분 |
| 비용 cascade (3.5 Flash → 3.1 Pro) | 단일 모델 | **거부됨** (D-13 박제). 분석 정확도 우선, 비용 하한 구독료 |

### Installation

Pod 1회 (`backend/runpod_inference/requirements.txt` append):
```bash
# Phase 5 추가 — Gemini 기술 인식기
google-genai>=1.0,<2.0  # Apache 2.0
```

Pod env 주입 (`setup.sh` 또는 belle 실행 시):
```bash
export GEMINI_API_KEY=$(aws ssm get-parameter \
  --name /sunity/motion/gemini-api-key \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text \
  --region ap-northeast-2)
```

### Version verification

```bash
pip index versions google-genai  # 신 SDK 명. 2025-Q2 출시
pip index versions google-generativeai  # legacy. 0.8.x → 1.x 마이그레이션 권고 [CITED: ai.google.dev/gemini-api/docs/migrate]
```

`google-genai` 는 본 research 시점 (2026-06-04) 안정판 [VERIFIED: googleapis.github.io/python-genai/]. 정확한 최신 마이너 버전은 planner 가 plan 작성 시 `pip index versions` 로 박제.

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `google-genai` | PyPI | ~1년 (2025-Q2+) | High (Google 공식) | github.com/googleapis/python-genai | [ASSUMED — slopcheck 미실행, Google 공식 GitHub 박제로 신뢰] | Approved (단, planner 가 `pip index versions` + `pip show google-genai` 으로 정합 확인 권장) |
| `boto3` | PyPI | 10+ yrs | Very high | github.com/boto/boto3 | [VERIFIED via 기존 박제] | Approved (기존 박제) |
| `firebase-admin` | PyPI | 5+ yrs | High | github.com/firebase/firebase-admin-python | [VERIFIED via 기존 박제] | Approved (기존 박제) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
**Note:** slopcheck 미실행 (research 환경 제약). 모든 [ASSUMED] 항목은 planner 가 plan 작성 시 `pip index versions <pkg>` + GitHub repo 확인으로 검증.

---

## Architecture Patterns

### System Architecture Diagram

```
[SQS 메시지: {bucket, key}]
        ↓
[Pipeline Lambda] ──── (RunPod 위임 모드 ON) ────→ [POST /analyze]
                                                          ↓
                                                  [RunPod Pod _process_in_background]
                                                          ↓
                          ┌───────────────────────────────┼───────────────────────────────┐
                          ↓                               ↓                               ↓
                  [S3 download video]          [Frame extract 9fps]                [영상 hash 계산
                                                                                    SHA256 또는 S3 ETag]
                                                          ↓                               ↓
                                                  [RTMW pose → angles (T,8)]    [Firestore lookup
                                                                                  gemini_cache/{hash}]
                                                          ↓                               ↓
                                                          ↓                       cache hit? ──→ ──┐
                                                          ↓                       cache miss       │
                                                          ↓                          ↓             │
                                                          ↓                  [GeminiMomentExtractor│
                                                          ↓                   .extract_key_moments]│
                                                          ↓                          ↓             │
                                                          ↓                  [3-case routing]      │
                                                          ↓                  ├ API 실패 → Fallback  │
                                                          ↓                  ├ Low conf → Page 9   │
                                                          ↓                  └ 미등록 → Page 9 + 수집│
                                                          ↓                          ↓             │
                                                          ↓                  [Firestore 박제] ──→ ─┘
                                                          ↓                          ↓
                                                          ↓                  [KeyMoment list +
                                                          ↓                   기술명 + confidence]
                                                          ↓                          ↓
                                                          ↓                  [GeminiTechniqueRecognizer
                                                          ↓                   .recognize(angles, frames)
                                                          ↓                   → TechniqueProfile
                                                          ↓                     (joint_expectations dict)]
                                                          └──────────────────────────┘
                                                                          ↓
                                                          [dimensions.line_score(angles, profile)]
                                                          [dimensions.stability_score(angles)]
                                                          [moment_dimensions.score_moment (yaml 진입 시)]
                                                                          ↓
                                                          [Firestore complete_analysis
                                                           + gemini_result 박제 (v1 dead label 포함)]
```

### Recommended Project Structure

```
backend/
├── shared/python/sunity_shared/
│   ├── judging/                                      # 기존 박제 (Plan 01-13)
│   │   ├── gemini_moment_extractor.py                # 재사용 (0줄 수정)
│   │   ├── moment_dimensions.py                      # 재사용 (D-05 v1 dead, D-06 v2 자동활성)
│   │   ├── geometric_criterion.py                    # 재사용
│   │   └── loader.py                                 # 재사용 (load_grouped_criteria)
│   └── analysis/
│       ├── technique.py                              # 신설 어댑터 추가 — GeminiTechniqueRecognizer
│       ├── technique_cache.py                        # 신설 — 영상 hash 캡싱 (D-14)
│       └── dimensions.py                             # 무수정 (Protocol 만 의존)
├── functions/pipeline/app.py                         # 1줄 수정 — _RECOGNIZER 교체 (env switch)
├── runpod_inference/
│   ├── server.py                                     # 무수정 (pipeline._process 재사용)
│   ├── requirements.txt                              # 1줄 추가 — google-genai
│   └── setup.sh                                      # GEMINI_API_KEY env 박제 안내 추가
├── research/evaluations/
│   └── compare_rtmw_vs_ipsf.py                       # --recognizer gemini flag 추가 (Plan 23 재실행 통합)
└── tests/
    ├── test_gemini_technique_recognizer.py           # 신설 — 어댑터 단위
    ├── test_technique_cache.py                       # 신설 — hash 캡싱
    └── test_pipeline_recognizer_switch.py            # 신설 — env switch
```

### Pattern 1: 어댑터 wrapper (Plan 01-13 spike 재사용)

**What:** `GeminiMomentExtractor` (spike 박제) 를 `GeminiTechniqueRecognizer` (Protocol 구현) 가 감싼다.
**When to use:** Phase 5 production wiring. spike 코드 0줄 수정 정신 박제.
**Example:**

```python
# Source: backend/shared/python/sunity_shared/analysis/technique.py (신설 어댑터)
# Plan 01-13 spike 박제 코드 재사용
from sunity_shared.judging import (
    GeminiMomentExtractor,
    KeyMoment,
    assign_frame_indices,
    load_grouped_criteria,
)
from .technique import (
    TechniqueProfile,
    TechniqueRecognizer,
    FallbackRecognizer,
    JOINT_EXTEND,
    JOINT_BENT_OK,
    JOINT_CONTACT,
)


class GeminiTechniqueRecognizer:
    """Gemini multimodal video → TechniqueProfile.

    어댑터 wrapper — GeminiMomentExtractor (Plan 01-13 spike) 호출 + 3-case fallback +
    영상 hash 캡싱. Fallback 은 FallbackRecognizer 위임.

    Returns TechniqueProfile.joint_expectations 에 EXTEND/BENT_OK 라벨링 — dimensions.py 의
    line_score 가 EXTEND 관절만 채점. measure_moment_angles 는 v1 dead (D-05), v2 자동 활성
    (D-06).
    """

    def __init__(
        self,
        extractor: GeminiMomentExtractor | None = None,
        cache: "TechniqueCache | None" = None,
        low_confidence_threshold: float = 0.5,  # D-10 후속 plan 갱신
        fallback: TechniqueRecognizer | None = None,
    ): ...

    def recognize(
        self,
        angles,
        frames=None,  # 영상 path 또는 hash — D-14 캡싱 lookup 키
    ) -> TechniqueProfile:
        # 1. 영상 hash → cache lookup
        # 2. cache miss → extractor.extract_key_moments(frames, motion=...)
        # 3. 3-case routing (API 실패/Low conf/미등록)
        # 4. KeyMoment + 기술명 → TechniqueProfile.joint_expectations
        # 5. Firestore 박제 + return
        ...
```

### Pattern 2: 3-case fallback routing

**What:** D-09 박제 3분기를 어댑터 내부에서 처리.
**When to use:** Gemini 응답 받은 후 confidence + scope_status 분기.

```python
# (1) API 실패 — 네트워크 timeout / 401 / 503
try:
    moments = self._extractor.extract_key_moments(video_uri, motion=motion_query)
except (RuntimeError, ValueError) as exc:
    log.warning("Gemini API 실패: %s — FallbackRecognizer 위임", exc)
    return self._fallback.recognize(angles, frames=frames)  # 분석 진행, "신뢰도 낮음" 박제

# (2) Low confidence — confidence < threshold
mean_conf = sum(m.confidence for m in moments) / len(moments) if moments else 0.0
if mean_conf < self._low_confidence_threshold:
    log.info("Gemini 응답 low conf=%.2f < %.2f — Page 9 절대 트랙 단독",
             mean_conf, self._low_confidence_threshold)
    # joint_expectations 비워서 dimensions.line_score 가 None 반환 → Page 9 stability 만 채점
    return TechniqueProfile(
        name="신뢰도 낮음",
        category="low_confidence",
        joint_expectations={},  # 빈 dict → line 차원 미산출
        requires_hold=True,
        is_symmetric=False,
    )

# (3) 미등록 — Gemini 기술명이 yaml scope 밖 (D-01 5영상 외)
recognized_motion = self._classify_motion(moments)  # Gemini description 또는 별도 호출
if recognized_motion not in REGISTERED_MOTIONS:  # {ref-climb, ref-foxtop, foxtop-split, invert, sideway-spin}
    # TERM-COPY-01 분기 3 — 자동 수집 트리거
    firestore_admin.record_unregistered_keyword(recognized_motion, uid=...)
    return TechniqueProfile(
        name=f"미등록: {recognized_motion}",
        category="unregistered",
        joint_expectations={},  # Page 9 단독
        requires_hold=True,
        is_symmetric=False,
    )

# (정상) — KeyMoment → joint_expectations 변환
return self._build_profile(moments, recognized_motion)
```

### Pattern 3: 영상 hash 캡싱 (D-14)

**What:** 같은 영상 재분석 시 Gemini 호출 0.
**When to use:** belle 시연 + Plan 23 sweep 재실행 시 비용/지연 0.

```python
# Source: backend/shared/python/sunity_shared/analysis/technique_cache.py (신설)
import hashlib

def compute_video_hash(video_path: Path) -> str:
    """영상 SHA256 — Plan 23 sweep 재실행 + belle 시연 캡싱 키."""
    h = hashlib.sha256()
    with video_path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class TechniqueCache:
    """Firestore 캡싱 — gemini_cache/{hash} 컬렉션 (또는 doc field).

    옵션 A: 별 컬렉션 `gemini_cache/{hash}` — 전역 공유 (다른 사용자도 같은 영상 재분석 시 hit).
    옵션 B: `users/{uid}/analyses/{analysis_id}.gemini_result` 단독 — 사용자 단위 (재분석 X).

    권장 = 옵션 A (D-14 의 belle 시연 + sweep 재실행 정신은 전역 공유 효과 큼).
    """

    def lookup(self, video_hash: str) -> dict | None: ...
    def store(self, video_hash: str, gemini_result: dict) -> None: ...
```

### Anti-Patterns to Avoid

- **`_RECOGNIZER` 모듈 로드 시 Gemini 어댑터 즉시 생성**: Lambda 콜드스타트 비용 + boto3/google-genai import 비용. D-16 lazy import 박제 정신 위반. → `_ensure_recognizer()` lazy creation 패턴 사용 (`_ensure_adapters()` 패턴과 동일).
- **Gemini 응답을 `joint_expectations` 에 그대로 박제 후 측정 각도와 비교 X**: D-08 박제 위반 (수치는 IPSF source). Gemini = 라벨러만, yaml 의 target/tolerance/minimum 은 그대로 사용.
- **`compare_rtmw_vs_ipsf.py` 의 `FallbackRecognizer` 를 영구 교체**: 회귀 테스트 + A/B 비교 가능성 보존. `--recognizer {fallback,gemini}` flag 로 선택 가능하게 유지.
- **`dimensions.py` 수정**: 박제 정신 위반. `TechniqueRecognizer` Protocol 만 의존하도록 박제됨 — Gemini 어댑터 swap 시 변경 0.
- **Cache key 에 motion 또는 model_name 미포함**: 다른 모델 (v2 3.5 Flash) 비교 시 cache 오염. key = `(video_hash, motion_query, model_name)` (Plan 01-13 spike 의 `_cache` 키 패턴 그대로).
- **KeyMoment 의 frame_index 를 caller (어댑터) 가 직접 채우지 않음**: `assign_frame_indices(moments, fps, T)` 호출 누락 시 frame_index=0 placeholder 그대로 → measure_moment_angles 가 frame 0 만 측정. spike CLI 패턴 그대로 사용.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gemini 응답 좌표/점수/판단 거부 | 한 줄 정규식 | Plan 01-13 박제 `_COORDINATE/SCORE/JUDGMENT_REJECT_PATTERNS` (3 카테고리 19 regex) | 박제됨, 8/5/6 패턴 박제 + 위반 시 ValueError 메시지에 어느 카테고리 + 매치 패턴 명시 |
| JSON 응답 파싱 + markdown fence 제거 | `json.loads(text)` | Plan 01-13 박제 `_parse_gemini_response` + `_strip_markdown_fence` | 박제됨, Gemini 응답이 ` ```json ... ``` ` 로 감싸는 경우 자동 흡수 |
| API 키 fetch (env / Parameter Store) | `os.environ.get(...) or boto3.client('ssm').get_parameter(...)` | Plan 01-13 박제 `_load_api_key()` | 박제됨, env 우선 → Parameter Store fallback + boto3 lazy import + 명확한 RuntimeError 메시지 |
| Gemini File API 업로드 + PROCESSING/ACTIVE 폴링 | `client.files.upload + while loop` | Plan 01-13 박제 `_call_gemini` (commit 9f011d2) | 박제됨, 2초 간격 max 120초 폴링 + FAILED 거부 |
| timestamp_seconds → frame_index 변환 | `int(round(ts * fps))` | Plan 01-13 박제 `assign_frame_indices` | 박제됨, clamp + validate() 통과 보장 |
| 4단계 moment_key enum | 자체 정의 | `sunity_shared.judging.VALID_MOMENT_KEYS` | `("setup", "hold", "peak", "release")` 박제 — 3중 가드 (KeyMoment.validate + 응답 파싱 + measure_moment_angles) |
| 영상 hash 계산 | 자체 SHA256 wrapper | `hashlib.sha256()` stdlib + S3 ETag fallback | S3 ETag 가 multipart upload 시 hex 아님 — SHA256 권장. S3 ETag 단일 upload 만 hex md5 |
| Firestore 트랜잭션 lookup | `firebase-admin` 직접 사용 | 기존 `firestore_admin` 모듈 + 신규 helper (`get_gemini_cache`, `store_gemini_cache`) | 기존 `complete_analysis`/`fail_analysis` 박제 패턴 그대로 |

**Key insight:** Plan 01-13 spike 코드는 production-ready (87 unit/smoke tests PASS, 0.17s). Phase 5 의 진짜 작업은 **어댑터 wrapper + wiring** 이지 Gemini 호출 코드 새로 작성 X. 박제 코드 0줄 수정 정신 = 회귀 위험 최소.

---

## Runtime State Inventory

이 phase 는 신규 기능 wiring 이지 rename/refactor 가 아니지만, 박제 코드 + Pod 환경 의존성이 있어 점검 필요.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | (1) Firestore `users/{uid}/analyses/{id}` 분석 doc — `gemini_result` 필드 신설 (4단계 라벨 + timestamp + confidence + model_version + cache_hit 메타). (2) Firestore `gemini_cache/{hash}` 또는 `motion_cache/{hash}` 컬렉션 신설 — D-14 캡싱 layer. (3) Firestore `term_collection/{keyword}` (TERM-DATA-01) — D-09 case 3 자동 수집. | 모두 신규 — 데이터 마이그레이션 불필요. Firestore rules 갱신 권장 (write = backend Admin SDK 만, read = 사용자 본인) |
| Live service config | (1) AWS Parameter Store `/sunity/motion/gemini-api-key` (SecureString, belle 박제 2026-06-01). 키 자체는 등록되어 있음 — Pod env 주입 wiring 만 추가. (2) Pod `RUNPOD_AUTH_TOKEN` / `AWS_ACCESS_KEY_ID` / `FIREBASE_SA_PATH` — 기존 박제. | Pod `setup.sh` 또는 belle 실행 스크립트에 `export GEMINI_API_KEY=$(aws ssm get-parameter ...)` 추가. Pod 재기동 또는 새 env 주입 1회 |
| OS-registered state | None — 현 Pod (RTX 3090, RunPod PyTorch 2.4 template) 에 추가 OS-level 등록 불필요. | None |
| Secrets/env vars | (1) `GEMINI_API_KEY` env 신규 (또는 Parameter Store fetch). (2) `GEMINI_RECOGNIZER_ENABLED` 같은 env switch 신설 권장 — A/B (Fallback vs Gemini) 비교 가능. (3) `GEMINI_MODEL_OVERRIDE` env (선택, 기본 `gemini-3.1-pro`). | Pod 환경 1회 export. AWS Lambda 측 env 는 Phase 5 RunPod 위임 모드 한정 — Lambda 측 직접 호출 path 는 v1 미사용 (D-12 Pod 1pass) |
| Build artifacts | (1) Plan 01-13 spike `backend/research/spikes/spike_gemini_moment.py` — 무수정 보존. (2) Plan 23 sweep `backend/research/evaluations/compare_rtmw_vs_ipsf.py` — `--recognizer gemini` flag 추가 박제. | Plan 23 sweep 재실행 시 새 보고서 `sweep_rtmw_<timestamp>_gemini/report.md` 생성 — git 박제 권장 (belle 검토) |

**Nothing found in category:** "OS-registered state" — Pod 가 stateless container 라 등록물 없음 (verified by `runpod-gpu-env.md` 박제).

---

## Common Pitfalls

### Pitfall 1: Plan 01-13 spike `_cache` 가 인스턴스 단위 — Pod 재기동 시 휘발

**What goes wrong:** `GeminiMomentExtractor._cache` 는 인스턴스 dict — Pod 재기동 시 사라짐. belle 시연 + Plan 23 sweep 재실행 비용 0 효과 X.
**Why it happens:** spike 단계에서는 단일 영상 호출 → 인스턴스 캐시 충분. Production wiring 에서는 영상-수준 영구 캐시 (Firestore) 필요.
**How to avoid:** **`GeminiTechniqueRecognizer` 가 별 캡싱 layer** (`TechniqueCache` Firestore) 사용. spike `_cache` 는 Pod 단일 분석 내 중복 호출만 흡수.
**Warning signs:** Pod 재기동 후 같은 영상 재분석 시 Gemini 호출 발생 = 캡싱 layer 미동작.

### Pitfall 2: Gemini timestamp 이 hold 가 아니라 transition frame 으로 분류 → 측정값 오류

**What goes wrong:** Plan 01-13 ref-invert live mode verdict 에서 hold frame_idx=88 → measured right_shoulder 18.2° (인체학적 비정상). Gemini 가 transition 시점을 hold 로 분류 가능성 박제.
**Why it happens:** Gemini multimodal 의 시점 분류 정확도 ±1~2초 (D-07 박제). hold (2~5초 지속) 는 windowing 으로 흡수 가능하지만 *단일 frame sampling* 시 timing 약점 노출.
**How to avoid:** **windowed measurement** — `measure_moment_angles` 호출 시 frame_index 단일 대신 `frame_index - W//2 ~ + W//2` 의 median 또는 mean 사용 (W = hold 지속 frame 수 추정). 또는 `dimensions.hold_window` (분산 최소 구간) 와 Gemini KeyMoment 의 overlap 검증.
**Warning signs:** 같은 영상의 Plan 01-13 live mode (단일 frame) vs Plan 23 sweep (`hold_window` frame-mean) 측정값 차이 > 30°.

### Pitfall 3: `google-genai` SDK 버전 불일치 — `client.files.upload` 시그너처 변경

**What goes wrong:** Plan 01-13 commit 569a076 = legacy `google-generativeai` 0.8.x → 신 `google-genai` 마이그레이션. SDK 가 빠르게 진화 중이라 시그너처 변경 가능.
**Why it happens:** Gemini API 가 2025-Q1~Q2 사이 v1 endpoint 안정화 + Pydantic schema 지원 추가. SDK 도 동시 변경.
**How to avoid:** `pip install google-genai==X.Y.Z` 형태로 정확 버전 pin + `pip freeze | grep google-genai` Pod 박제. `requirements.txt` upper bound 보수적 (`<2.0`) 유지. `pip index versions google-genai` 로 박제 시점 정확 버전 확인.
**Warning signs:** Pod 재기동 후 `client.files.upload` 또는 `client.models.generate_content` AttributeError / TypeError.

### Pitfall 4: Pod env `GEMINI_API_KEY` 미설정 시 boto3 fallback 이 실패하는데 fail-loud 부재

**What goes wrong:** Plan 01-13 박제 `_load_api_key()` 는 env → Parameter Store fallback → RuntimeError. Pod 가 IAM 권한 없으면 Parameter Store get_parameter 실패 → RuntimeError 발생하지만 Pod 처음 가동 후 첫 분석에서만 발현 (lazy import).
**Why it happens:** Pod env 박제 누락 (예: belle 가 새 Pod 재생성 후 setup.sh 만 실행하고 GEMINI_API_KEY export 빼먹음).
**How to avoid:** **Pod startup hook** (`server.py` `@app.on_event("startup")` 의 `_warmup`) 에서 `_load_api_key()` 명시 호출 — 시작 시점에 fail-loud. 키 없으면 Pod 자체가 503 으로 응답 (어댑터가 동작 안 함을 명시).
**Warning signs:** Pod 첫 분석에서 갑작스러운 `RuntimeError: Gemini API 키가 비어있음` — 사용자 노출 X (firestore_admin.fail_analysis 가 ERR_SERVER_ERROR 로 흡수).

### Pitfall 5: Plan 23 sweep `--recognizer gemini` 실행 시 Pod 내부에서 모든 영상마다 Gemini 호출 → 5영상 × 5~15초 폴링 = 25~75초 대기 + API quota 소모

**What goes wrong:** Plan 23 sweep 재실행 5영상 × Gemini 호출 = 약 1~2분 추가. belle 가 매번 재실행 시 API quota 누적.
**Why it happens:** D-14 캡싱이 첫 sweep 만 비용 발생 — 두 번째 이후 cache hit. 그러나 sweep 1회 차에는 캡싱 효과 0.
**How to avoid:** sweep 진입 전 Firestore `gemini_cache` 미리 fill 하는 batch 스크립트 1회 실행 → 이후 sweep 은 cache hit. 또는 sweep 실행 시 `--use-cache` flag 명시 → 미존재 시 silent skip + 로그 박제.
**Warning signs:** belle Pod sweep `time` 출력에서 Gemini wait 가 50% 이상 차지.

### Pitfall 6: `joint_expectations` 가 빈 dict — D-09 case 2 (Low conf) / case 3 (미등록) 에서 line_score=None → 사용자 화면에 점수 누락

**What goes wrong:** `dimensions.line_score` 가 EXTEND 관절이 0 개면 None 반환 → `dimension_scores` dict 에서 누락 → 사용자 화면에 line 차원 0 표시 또는 누락.
**Why it happens:** 박제 정신 ("가짜 점수 안 만듦") 정합 — 그러나 사용자 입장에서는 "분석 실패" 처럼 보일 수 있음.
**How to avoid:** `dimensions.absolute_dimension_scores` 가 stability 만 반환 → app `useAnalysisDoc` 가 line=null 인지 확인 후 "신뢰도 낮음" 카피 노출. **D-11 박제와 정합** — UI 카피는 별 plan (Phase 12), Phase 5 는 데이터 박제만.
**Warning signs:** Firestore `result.dimensionScores` 에 `line` 키 자체가 없음 — app 가 panic 또는 0 표시.

---

## Code Examples

Verified patterns from official sources + Plan 01-13 spike 박제.

### Common Operation 1: google-genai 신 SDK 영상 업로드 + ACTIVE 폴링

```python
# Source: ai.google.dev/gemini-api/docs/video-understanding + Plan 01-13 commit 9f011d2 박제
from google import genai
import time

client = genai.Client(api_key=api_key)

# 영상 업로드 — Files API (로컬 path 만, 20GB 한도 paid / 2GB free)
# 형식: MP4 / MPEG / QuickTime / AVI / FLV / MPG / WebM / WMV / 3GPP
uploaded = client.files.upload(file=video_path)

# PROCESSING → ACTIVE 폴링 — 2초 간격 max 120초 (Plan 01-13 박제)
start = time.monotonic()
while uploaded.state.name == "PROCESSING":
    if time.monotonic() - start > 120.0:
        raise RuntimeError("File API processing 120초 초과")
    time.sleep(2.0)
    uploaded = client.files.get(name=uploaded.name)

if uploaded.state.name == "FAILED":
    raise RuntimeError(f"File API processing 실패: {uploaded.name}")

# generate_content — 1FPS sampling 기본, MM:SS timestamp 형식
# [VERIFIED: ai.google.dev/gemini-api/docs/video-understanding]
response = client.models.generate_content(
    model="gemini-3.1-pro",  # D-13 박제
    contents=[uploaded, prompt],
)
text = response.text
```

### Common Operation 2: JSON Schema 강제 (response_mime_type)

```python
# Source: ai.google.dev/gemini-api/docs/structured-output
# [CITED: mintlify.com/googleapis/python-genai/guides/json-response]
from pydantic import BaseModel
from typing import Literal


class GeminiMomentEntry(BaseModel):
    moment_key: Literal["setup", "hold", "peak", "release"]  # enum 강제
    timestamp_seconds: float
    confidence: float
    description: str  # Plan 01-13 _enforce_no_coordinate_or_score 가드 통과 필요


class GeminiResponse(BaseModel):
    motion_name: str
    moments: list[GeminiMomentEntry]


response = client.models.generate_content(
    model="gemini-3.1-pro",
    contents=[uploaded, prompt],
    config={
        "response_mime_type": "application/json",
        "response_schema": GeminiResponse,  # Pydantic class 직접 전달
    },
)

# response.parsed 로 자동 변환됨 [CITED: googleapis.github.io/python-genai/]
parsed: GeminiResponse = response.parsed
# 또는 response.text 로 JSON 문자열 — Plan 01-13 박제 _parse_gemini_response 호환
```

**중요 — 박제 정합:** Plan 01-13 spike 는 `response_mime_type` 미사용 (SDK 버전 의존성 회피). Phase 5 production wiring 시 **structured output 도입 권장** — JSON 파싱 실패 위험 감소 + moment_key enum 강제 + description 필드 reject patterns 와 평행. 단, `response_schema` 가 video file input 과 같이 사용 가능한지 docs 미명시 [CITED: ai.google.dev/gemini-api/docs/structured-output 의 (4) Structured Output with Video Files = "documentation does not explicitly address"]. → **plan 작성 시 작은 spike 또는 fallback path (mime_type 없이 prompt 만) 박제 권장**.

### Common Operation 3: TechniqueProfile.joint_expectations 빌드 (Gemini 응답 → EXTEND/BENT_OK)

```python
# Source: backend/shared/python/sunity_shared/analysis/technique.py 박제 패턴
from sunity_shared.analysis.technique import (
    TechniqueProfile,
    JOINT_EXTEND,
    JOINT_BENT_OK,
    JOINT_CONTACT,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS  # 8 angle joints

def _build_profile_from_gemini(
    motion_name: str,
    gemini_moments: list[KeyMoment],
    yaml_criteria: list[GeometricCriterion],  # load_grouped_criteria[hold] 결과
) -> TechniqueProfile:
    """Gemini moment + yaml criteria → joint_expectations dict.

    D-08 박제 — Gemini = 라벨러만, 수치는 yaml (IPSF source) 그대로.
    yaml 에 등재된 joint = EXTEND (target=180° 이면), 그 외 = BENT_OK (의도된 굽힘).
    CONTACT 는 v1 미사용 (grip 관절 추정 필요 — 후속 plan).
    """
    expectations: dict[str, str] = {}
    yaml_extend_joints = {
        c.joint_key for c in yaml_criteria
        if c.angle_target == 180.0  # Fully Extended Criteria
    }
    for joint_key in JOINT_KEYS:
        if joint_key in yaml_extend_joints:
            expectations[joint_key] = JOINT_EXTEND
        else:
            expectations[joint_key] = JOINT_BENT_OK  # 미등재 = 평가 제외 (보수)

    return TechniqueProfile(
        name=motion_name,  # 기술명 박제
        category="recognized",  # Gemini 인식 성공
        joint_expectations=expectations,
        required_split_deg=None,  # v1 미사용
        requires_hold=True,
        is_symmetric=False,
    )
```

### Common Operation 4: pipeline `_process` 안 어댑터 swap (env switch)

```python
# Source: backend/functions/pipeline/app.py:120 (현재 박제, 수정 권장 path)
# 현재:
#   _RECOGNIZER: technique.TechniqueRecognizer = technique.FallbackRecognizer()
#
# 신설 path (Phase 5):
import os

_RECOGNIZER: technique.TechniqueRecognizer | None = None
_RECOGNIZER_LOCK = threading.Lock()

def _ensure_recognizer() -> technique.TechniqueRecognizer:
    """D-16 박제 — lazy creation. env GEMINI_RECOGNIZER_ENABLED 로 swap."""
    global _RECOGNIZER
    if _RECOGNIZER is not None:
        return _RECOGNIZER
    with _RECOGNIZER_LOCK:
        if _RECOGNIZER is not None:
            return _RECOGNIZER
        if os.environ.get("GEMINI_RECOGNIZER_ENABLED", "").lower() in ("1", "true", "on"):
            from sunity_shared.analysis.gemini_technique_recognizer import (
                GeminiTechniqueRecognizer,
            )
            _RECOGNIZER = GeminiTechniqueRecognizer()
            log.info("Recognizer = Gemini (env switch ON)")
        else:
            _RECOGNIZER = technique.FallbackRecognizer()
            log.info("Recognizer = Fallback (env switch OFF — default)")
        return _RECOGNIZER

# _process 안에서:
recognizer = _ensure_recognizer()
profile = recognizer.recognize(angles, frames=video_local_path)  # frames 인자 추가
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `google-generativeai` 0.8.x (legacy) | `google-genai` (신 SDK, Client + files + models) | 2025-Q2 | 새 AI Studio `AQ.` 키 포맷 지원, v1 endpoint, Pydantic schema 지원 |
| JSON 응답 수동 파싱 + markdown fence 흡수 | `response_mime_type=application/json` + `response_schema=PydanticModel` | 2025-Q1+ | 파싱 실패 0, enum 강제, response.parsed 자동 변환 |
| Frame-by-frame Gemini 호출 (image input) | Files API 단일 video upload + 1FPS 자동 sampling | 2024-Q4+ | 토큰 비용 감소 (~300 token/sec @ 표준 vs 영상 길이별 frame 개별 호출 = O(T) 비용) |
| Lambda + Step Functions 비동기 chain (Gemini polling) | Pod 안 1pass 동기 호출 + BackgroundTask | Phase 5 신설 (D-12 박제) | GPU idle 1-3초 < SQS overhead, debug 단순화 |

**Deprecated/outdated:**
- `gemini-2.5-pro` (Plan 01-13 spike default): belle 2026-06-04 결정 박제로 `gemini-3.1-pro` 단일 — STATE.md 갱신 박제. Phase 5 코드는 `DEFAULT_GEMINI_MODEL` 상수 갱신 + 기존 인자 override path 보존.
- `gemini-2.5-flash` / `gemini-3.5-flash` (cascade 후보): v1 미사용. v2 비용 분석 plan 평가.
- Plan 01-13 `GeminiMomentExtractor.model_name` default 가 `gemini-2.5-pro` — Phase 5 wiring 시 `DEFAULT_GEMINI_MODEL = "gemini-3.1-pro"` 갱신 필요 (spike 코드 1줄 수정 = 박제 갱신 정당).

---

## Plan 01-13 spike `measurement_unreliable_blocked` 원인 분석 → Phase 5 차별점

### Plan 01-13 verdict 원인 (3증거 박제)

| # | 증거 | 원인 |
|---|---|---|
| 1 | right_shoulder 18.2° (정은지 invert split) — 인체학적 비정상 | RTMPose+MB lift 약점 (Plan 12 (e) verdict "두 엔진 3D 분포 strong, distance 220+") |
| 2 | 좌우 비대칭 폭주 (left_shoulder 88 vs right 18, Δ=70°) | lifter 가 occlusion 자세 (거꾸로 매달림) 에서 좌우 keypoint 헷갈림 |
| 3 | Cross-engine inconsistency (MP+MB 92 vs RTMPose+MB 70 vs 단일 frame 5/5 fail) | 단일 frame sampling 좌우 noise 폭주 |

### Phase 5 production wiring 의 차별점 (RTMW pivot 이후)

| 항목 | Plan 01-13 시점 (2026-06-01) | Phase 5 시점 (2026-06-04+) |
|---|---|---|
| 측정 chain | RTMPose+MB (Plan 11 박제) | RTMW wholebody (Plan 21+22 박제) — 단일 백본 |
| sweep 백본 | Plan 11 sweep_rtmpose | Plan 23 sweep_rtmw (`compare_rtmw_vs_ipsf.py`) |
| Plan 23 rtmw_mean_score | N/A (RTMPose+MB) | 93.0~95.4 (5영상, 박제) |
| 각도 sampling | 단일 frame (Plan 13 spike) | `hold_window` frame-mean (`compare_to_ipsf` 박제) — Plan 13 함정 회피 |
| FallbackRecognizer 한계 | 영향 X (Plan 13 = yaml 직접 비교) | Plan 23 sweep root cause 1 — Phase 5 가 해결 |

**핵심 결론:**
- Plan 01-13 verdict 는 **RTMPose+MB lift 약점** + **단일 frame sampling** 의 결합 효과. Phase 5 의 측정 chain 은 RTMW + frame-mean 박제 — Plan 13 두 약점 모두 해소된 환경.
- Phase 5 의 진짜 위험은 Plan 13 의 측정 chain 약점 재현 X, **Gemini timestamp 정확도 ±1~2초** (D-07 박제) + **Low confidence 분포 미실측** (D-10 deferred) 두 가지. 두 위험은 Phase 5 5영상 sweep 실측 후에만 박제 가능.
- Plan 23 sweep 의 angle 0/5 PASS root cause 1 (FallbackRecognizer 한계) 은 Phase 5 wiring 으로 직접 해결 — ref-foxtop-split 의 measured left_shoulder=21° (within FallbackRecognizer EXTEND 가정 = 위양성 점수 0) → Gemini 가 BENT_OK 로 라벨링 시 line 차원에서 평가 제외 → angle 차원만 yaml target 과 비교 → tolerance 통과 가능성 회복.

---

## Production Wiring Path

### 1. RunPod Pod 변경

**`backend/runpod_inference/requirements.txt`** — append 1줄:
```
# Phase 5 (D-13) — Gemini 기술 인식기, Apache 2.0
google-genai>=1.0,<2.0
```

**`backend/runpod_inference/setup.sh`** — Step [7/7] 신설:
```bash
echo "[7/7] Gemini API 키 박제 (Parameter Store SecureString)"
echo "  Pod env 주입 예시:"
echo "    export GEMINI_API_KEY=\$(aws ssm get-parameter \\"
echo "      --name /sunity/motion/gemini-api-key \\"
echo "      --with-decryption --query 'Parameter.Value' \\"
echo "      --output text --region ap-northeast-2)"
echo "  또는 env GEMINI_API_KEY=<key> 직접 export (Plan 01-13 박제 fallback)"
```

**`backend/runpod_inference/server.py`** — 무수정 (pipeline `_process` 재사용 박제 정신).
**`@app.on_event("startup")` 의 `_warmup`** — `_ensure_recognizer()` 추가 호출 권장 (Pod 시작 시 API 키 fail-loud 검증).

### 2. Lambda 변경

**`backend/functions/pipeline/app.py`** — 박제 수정:
- `_RECOGNIZER` 즉시 생성 → `_ensure_recognizer()` lazy
- env switch `GEMINI_RECOGNIZER_ENABLED` 박제
- `_process` 안 `recognizer = _ensure_recognizer()` + `profile = recognizer.recognize(angles, frames=video_local_path)`

Lambda 측 직접 호출 path 는 v1 미사용 (D-12 박제) — RunPod 위임 모드만. 그러나 `GEMINI_RECOGNIZER_ENABLED` env 자체는 RunPod 위임 path 에서도 Pod 가 읽음 (`_load_pipeline_module()` 가 pipeline.py 의 모듈 변수 그대로 사용).

### 3. 신설 어댑터 + 캡싱 모듈

```
backend/shared/python/sunity_shared/analysis/
├── gemini_technique_recognizer.py  (신설)
└── technique_cache.py              (신설)
```

`gemini_technique_recognizer.py` 의 구조:
- `GeminiTechniqueRecognizer` 클래스 — `TechniqueRecognizer` Protocol 구현
- `recognize(angles, frames=None)` 메서드 — frames = 영상 local path
- 의존성 lazy import (`google.genai`, `boto3`) — D-16 박제 정신
- `extractor`, `cache`, `fallback`, `low_confidence_threshold` 인자 — DI 패턴

`technique_cache.py` 의 구조:
- `compute_video_hash(video_path) → str` — SHA256
- `TechniqueCache.lookup(video_hash) → dict | None`
- `TechniqueCache.store(video_hash, gemini_result)`
- Firestore `gemini_cache/{hash}` 컬렉션 (전역 공유 권장 — belle 시연 + sweep 재실행 최적)

### 4. Firestore schema 신설

`firestore_admin.py` 에 helper 추가:
- `get_gemini_cache(video_hash) → dict | None`
- `store_gemini_cache(video_hash, gemini_result, motion, model_name)`
- `record_unregistered_keyword(keyword, uid, video_hash)` — TERM-DATA-01 분기 3 트리거

`users/{uid}/analyses/{id}.gemini_result` schema (v1 박제 + v2 자동 활성):
```json
{
  "gemini_result": {
    "model": "gemini-3.1-pro",
    "motion_name": "ref-invert",  // 또는 "미등록: 인버트 버터플라이"
    "scope_status": "recognized" | "low_confidence" | "unregistered" | "api_failure",
    "moments": [
      {"moment_key": "setup", "timestamp_seconds": 2.1, "frame_index": 19, "confidence": 0.82},
      {"moment_key": "hold", "timestamp_seconds": 5.5, "frame_index": 49, "confidence": 0.88},
      {"moment_key": "peak", "timestamp_seconds": 6.0, "frame_index": 54, "confidence": 0.85},
      {"moment_key": "release", "timestamp_seconds": 8.2, "frame_index": 73, "confidence": 0.78}
    ],
    "joint_expectations": {
      "left_shoulder": "extend", "right_shoulder": "extend",
      "left_hip": "extend", "right_hip": "extend",
      "left_knee": "extend", "right_knee": "extend",
      "left_elbow": "bent_ok", "right_elbow": "bent_ok"
    },
    "video_hash": "abc123...",
    "cache_hit": false,
    "elapsed_ms": 5234,
    "low_confidence_threshold": 0.5,  // D-10 박제 후 실측 갱신
    "fallback_used": null  // "api_failure" 시 "fallback_recognizer", "low_confidence" 시 "page9_only"
  }
}
```

### 5. Plan 23 sweep 통합

`backend/research/evaluations/compare_rtmw_vs_ipsf.py` 변경:
- `--recognizer {fallback,gemini}` argparse flag 추가 (default = `fallback` 박제 보존)
- `compare_to_ipsf` 가 recognizer 인자 받음 — 현재 `FallbackRecognizer` 고정 (line 334).
- `--recognizer gemini` 시 `GeminiTechniqueRecognizer` 주입.
- 보고서 `report.md` 에 recognizer 종류 박제 + Gemini 응답 raw excerpt (좌표/점수/판단 0건 확인).

게이트 변경:
- 현재: IPSF within_tolerance 5/5 + line 5/5 + angle 5/5 = phase1_ready_to_swap True.
- Phase 5 통과 후 기대치: **angle 4~5/5 PASS** (ref-climb 는 IPSF criteria 0건 — PASS 그대로). Plan 23 verdict 의 0/5 → 4~5/5 회복 = Phase 5 success.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| Config file | `backend/pyproject.toml` 또는 `backend/pytest.ini` (미존재 시 Wave 0 신설) |
| Quick run command | `cd backend && pytest tests/ -x --no-header -q` (87 spike + 신설 약 30 = 117) |
| Full suite command | `cd backend && pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCORE-01 (좌표/판단 거부) | Gemini 응답에 좌표/점수/판단 detect 시 ValueError | unit | `pytest backend/tests/test_gemini_moment_extractor.py -x` | YES (Plan 01-13 박제, 18 patterns × 52 tests) |
| SCORE-01 (어댑터 → TechniqueProfile) | GeminiTechniqueRecognizer.recognize() 가 joint_expectations dict 반환 + EXTEND/BENT_OK 라벨링 정합 | unit | `pytest backend/tests/test_gemini_technique_recognizer.py -x` | NO — Wave 0 신설 필요 |
| SCORE-01 (API 실패 fallback) | Gemini 호출 RuntimeError 시 FallbackRecognizer 위임 | unit | `pytest backend/tests/test_gemini_technique_recognizer.py::test_api_failure_falls_back -x` | NO — Wave 0 |
| SCORE-01 (Low conf fallback) | mean confidence < threshold 시 joint_expectations 빈 dict + scope_status="low_confidence" | unit | `pytest backend/tests/test_gemini_technique_recognizer.py::test_low_confidence_returns_empty_expectations -x` | NO — Wave 0 |
| SCORE-01 (미등록 fallback) | 인식 motion 이 5영상 scope 밖 시 scope_status="unregistered" + TERM-DATA-01 트리거 | unit | `pytest backend/tests/test_gemini_technique_recognizer.py::test_unregistered_triggers_term_collection -x` | NO — Wave 0 |
| SCORE-05 (Page 9 단독 채점) | joint_expectations 빈 dict + dimensions.line_score=None → dimensions.absolute_dimension_scores 가 stability 만 반환 | unit | `pytest backend/tests/test_dimensions_page9_only.py -x` | NO — Wave 0 |
| TERM-COPY-01 (분기 3 카피) | scope_status="unregistered" 시 Firestore term_collection 박제 + 카피 (Phase 5 = trigger only, UI = Phase 12) | unit | `pytest backend/tests/test_firestore_admin_term_collection.py -x` | NO — Wave 0 |
| D-14 (영상 hash 캡싱) | 같은 video_hash 재호출 시 Gemini 호출 0 + cache_hit=True | unit | `pytest backend/tests/test_technique_cache.py -x` | NO — Wave 0 |
| D-14 (cache miss store) | 첫 분석 시 Firestore store + 두 번째 호출 시 hit | unit | `pytest backend/tests/test_technique_cache.py::test_lookup_then_store -x` | NO — Wave 0 |
| D-16 (lazy import) | google-genai / boto3 module-level import 0 (Lambda 콜드스타트 보호) | unit | `pytest backend/tests/test_pipeline_recognizer_switch.py::test_no_module_level_gemini_import -x` | NO — Wave 0 |
| D-12 (Pod 1pass wiring) | RunPod 위임 모드에서 _process 가 GeminiTechniqueRecognizer 호출 (mock 가능) | integration | `pytest backend/tests/test_pipeline_gemini_integration.py -x` | NO — Wave 0 |
| Phase 5 게이트 (Plan 23 sweep 재실행 angle 4/5+ PASS) | belle Pod sweep `compare_rtmw_vs_ipsf.py --recognizer gemini` 5영상 모두 within_tolerance/angle 측정 | manual-only | belle Pod 실행 (`backend/research/evaluations/compare_rtmw_vs_ipsf.py --recognizer gemini --videos ref-climb ref-foxtop ref-foxtop-split ref-invert ref-sideway-spin`) | sweep 스크립트 박제됨, `--recognizer gemini` 인자만 Wave 0 신설 |
| Gemini 라벨 정확도 측정 | KeyMoment timestamp 와 실제 hold 시점 일치 확인 — IPSF Code of Points 와 belle 검토 | manual-only | belle 검토 (sweep 결과 .md 의 per-joint gap 표) | — |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_gemini_technique_recognizer.py -x backend/tests/test_technique_cache.py -x` (어댑터 + 캡싱 신설 테스트만, < 5초)
- **Per wave merge:** `cd backend && pytest tests/ -x --no-header -q` (전체 117+ 테스트, < 30초)
- **Phase gate:** belle Pod `compare_rtmw_vs_ipsf.py --recognizer gemini` 5영상 sweep + belle 검토 (수동, blocking checkpoint)

### Wave 0 Gaps

- [ ] `backend/tests/test_gemini_technique_recognizer.py` — 어댑터 단위 테스트 (recognize/3-case fallback/lazy import) — covers SCORE-01
- [ ] `backend/tests/test_technique_cache.py` — Firestore 캡싱 layer 단위 — covers D-14
- [ ] `backend/tests/test_dimensions_page9_only.py` — joint_expectations 빈 dict 시 stability 단독 — covers SCORE-05
- [ ] `backend/tests/test_firestore_admin_term_collection.py` — TERM-DATA-01 분기 3 trigger — covers TERM-COPY-01 (Phase 5 데이터 부분)
- [ ] `backend/tests/test_pipeline_recognizer_switch.py` — env switch + lazy import — covers D-16
- [ ] `backend/tests/test_pipeline_gemini_integration.py` — mock-based integration — covers D-12
- [ ] `backend/research/evaluations/compare_rtmw_vs_ipsf.py` — `--recognizer {fallback,gemini}` flag 추가 (sweep 재실행 통합)
- [ ] Framework install: 기존 박제됨 (`pyyaml>=6` 이미 `backend/requirements-dev.txt`)

*(기존 87 PASS Plan 01-13 spike 테스트 + Plan 23 11 PASS sweep 테스트 = 98 PASS 보존)*

---

## Security Domain

> security_enforcement: true, security_asvs_level: 1, block_on: high.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Pod `RUNPOD_AUTH_TOKEN` (기존 박제). Gemini API 키 = SecureString (D-15) |
| V3 Session Management | no | Phase 5 는 stateless Pod 호출 |
| V4 Access Control | yes | Firestore rules — `gemini_cache/{hash}` write = backend Admin 만, read = public (영상 hash 노출 시 hash 자체로 영상 재구성 불가 — SHA256). `term_collection` write = backend, read = backend 전용 (TERM-DATA-01 분기 3 데이터 보호) |
| V5 Input Validation | yes | (1) Gemini 응답 좌표/점수/판단 reject patterns (박제 19 regex). (2) KeyMoment.validate() (timestamp/confidence 범위). (3) GeometricCriterion.validate() (target 범위 + source_ref 비어있음 거부). (4) Pydantic schema (response_mime_type) — moment_key Literal enum |
| V6 Cryptography | yes | (1) Gemini API 키 = SecureString (AWS KMS 자동). (2) SHA256 영상 hash — stdlib `hashlib` (절대 hand-roll 금지). (3) S3 ETag = MD5 등가 — single-part upload 만 사용 가능 (multipart 시 non-hex). |

### Known Threat Patterns for {Pod + Gemini API + Firestore Admin}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Gemini API 키 노출 (env / 로그) | Information Disclosure | `log.debug("Gemini API 키 로드: SSM ...")` 에서 키 자체 미출력 (박제됨). Pod env dump 금지 (`env | grep -v KEY` 등). |
| Gemini 응답 prompt injection (사용자 영상에 텍스트 포함) | Tampering | reject patterns 19 regex (Plan 01-13 박제) + Pydantic schema 강제 + response.parsed 타입 검증 |
| Gemini 응답 좌표/점수/판단 우회 시도 (SCORE-01 위반) | Tampering | _enforce_no_coordinate_or_score 3 카테고리 ValueError + 위반 패턴 메시지 명시 |
| Firestore `gemini_cache` write 권한 우회 | Elevation of Privilege | Admin SDK 단독 write — Firestore rules `match /gemini_cache/{hash} { allow write: if false; }` (client 차단) + Admin SDK 가 server 측에서만 write |
| 영상 hash collision (이론적 SHA256 무시 가능) | Tampering | 무시 가능 — 2^128 시도 필요. 그러나 추가 안전망으로 cache 에 `motion_name` 함께 박제 (lookup 시 `(hash, motion_query)` 두 필드 일치 확인) |
| Pod 가 Gemini API 응답 비-JSON 처리 시 crash → Pod 전체 die | Denial of Service | Plan 01-13 박제 try/except → ValueError → fail_analysis (`ERR_SERVER_ERROR`). Pod 자체는 살아있음 (FastAPI BackgroundTask 격리) |
| TERM-DATA-01 분기 3 자동 수집 시 PII 노출 (사용자 입력 키워드에 개인정보) | Information Disclosure | 박제 `record_unregistered_keyword` 가 anonymous_id (Firebase Auth uid 가 anonymous) + keyword 만 저장 — 영상/얼굴 미저장 |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| RunPod Pod (RTX 3090) | D-12 Pod 안 1pass | ✓ | RunPod PyTorch 2.4 template, Python 3.11 | — (실분석 의존) |
| AWS Parameter Store `/sunity/motion/gemini-api-key` | D-15 SecureString | ✓ | belle 박제 2026-06-01 | env `GEMINI_API_KEY` 직접 export (Plan 01-13 박제) |
| Pod IAM 권한 (ssm:GetParameter) | D-15 boto3 fallback | ✓ (기존 박제) | — | env 직접 export |
| `google-genai` Python SDK | D-13 신 SDK | ✗ (Pod 미설치) | — | `pip install google-genai` 1회 (setup.sh Step [2/7] 이후) |
| Firestore Admin SDK | gemini_cache 박제 | ✓ | `firebase-admin>=6.5,<7.0` 박제 | — |
| RTMW pose engine (Plan 21+22 박제) | 측정 chain | ✓ | Plan 23 sweep 통과 verdict (rtmw_mean_score 93~95) | — |
| Plan 23 sweep script | Phase 5 게이트 | ✓ | `compare_rtmw_vs_ipsf.py` 박제 | `--recognizer gemini` flag 추가 필요 (Wave 0) |
| 5영상 yaml criteria (`ref-climb` / `ref-foxtop` / `ref-foxtop-split` / `ref-invert` / `ref-sideway-spin`) | D-01 인식 scope | ✓ | Plan 15 박제 (`backend/judging_data/criteria/*.yaml`) | — (ref-climb 는 의도된 빈 list — IPSF Climbs 카테고리 비해당) |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** `google-genai` Pod 1회 install — `pip install google-genai` (~5초)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Gemini 3.1 Pro 가 1FPS 자동 sampling → MM:SS timestamp 정확도 ±1~2초 | D-07 박제 + Common Pitfall 2 | hold 2~5초 지속이라 windowing 으로 흡수 가능. peak (0.5~1초) 활성 시 별 plan |
| A2 | `response_schema=PydanticModel` 가 video file input 과 함께 작동 | Code Examples 2 + State of the Art | docs 미명시 [CITED: ai.google.dev/gemini-api/docs/structured-output (4)]. 작동 안 하면 prompt-only fallback path 사용 (Plan 01-13 spike 방식 그대로) |
| A3 | `google-genai` 최신 안정판 (≥1.0) 이 Plan 01-13 spike API (`client.files.upload`, `client.models.generate_content`, `client.files.get`) 호환 | Standard Stack + Common Pitfall 3 | SDK 빠른 진화 — planner 가 `pip index versions` + 시그너처 확인 후 박제 |
| A4 | Firestore `gemini_cache/{hash}` 컬렉션 (전역 공유) 가 D-14 박제 정신 정합 | Pattern 3 + Production Wiring 4 | 대안 = `users/{uid}/analyses/{id}.gemini_result` 단독 (사용자 단위) — belle 결정 필요. **권장 = 전역 공유** (sweep 재실행 + belle 시연 효과 큼) |
| A5 | `compute_video_hash` SHA256 이 D-14 박제 정신 정합 (S3 ETag 대체) | Pattern 3 | S3 ETag = single-part upload 시 MD5 hex, multipart 시 비-hex — Pod 가 영상 다운로드 후 SHA256 계산이 가장 안전 + 영상 정합 검증 효과 추가 |
| A6 | Low confidence threshold 0.5 (예시) — D-10 박제 후 실측 갱신 | Pattern 2 + Test Map | v1 wiring 후 5영상 sweep confidence 분포 실측 후 박제 (별 plan 또는 Phase 5 마지막 plan) |
| A7 | Gemini 가 5영상 (D-01 scope) 의 motion_name 을 정확히 분류 (한국어 또는 영어로) | Pattern 2 (case 3 routing) | prompt 에 5영상 scope 박제 + 응답 motion_name 정규화 (단순 string match 또는 fuzzy) — planner 가 작은 spike 후 박제 권장 |
| A8 | Pod startup 시 `_load_api_key()` 명시 호출이 fail-loud 효과 (Pitfall 4) | Common Pitfall 4 | startup 실패 시 Pod 가 503 응답 — Lambda 측 retry 또는 fail_analysis 매핑 |
| A9 | `compare_rtmw_vs_ipsf.py` 의 `compute_to_ipsf` 가 `recognizer` 인자 추가 후에도 기존 11 PASS 테스트 회귀 X | Production Wiring 5 + Wave 0 | argparse 기본값 `fallback` 박제 + 기존 호출 path 무수정 — 회귀 위험 낮음 |
| A10 | Plan 23 sweep verdict 의 root cause 1 (FallbackRecognizer 한계) 해결 시 angle 0/5 → 4~5/5 PASS 회복 | Summary + 차별점 | belle Pod 실측 후에만 확정 — root cause 2 (HoughPoleDetector 미설치) + root cause 3 (yaml criteria 정합) 는 별 plan 책임 (Phase 5 외) |

**If this table is empty:** N/A — 10건 박제. planner 가 plan 작성 시 A1~A10 각각에 대한 처리 path (확인/spike/별 plan) 박제 권장.

---

## Open Questions

1. **Gemini motion_name 분류 path** — Gemini 응답에 motion_name 이 한국어 / 영어 / IPSF Code 어떤 형태로 오는지? Plan 01-13 spike 의 prompt `{motion}` 인자는 caller (CLI) 가 명시 — production wiring 시 caller (어댑터) 가 motion 을 모름 (분류 자체가 목적).
   - 무엇을 모르나: Gemini 가 "이건 invert 다" / "ref-invert" / "인버트 버터플라이" / "K-pose 같은 게 보임" 중 어느 형태로 응답?
   - 권장: 작은 spike — 5영상 each 에 prompt "이 동작의 IPSF 등재 명칭 또는 한국 학원 통용 명칭을 한국어로 답하라" → 응답 분석 → motion_name 정규화 path 박제 (fuzzy match 또는 enum mapping table)

2. **`response_schema` 가 video file input 과 작동하는가** — docs [CITED: ai.google.dev/gemini-api/docs/structured-output (4)] 가 명시 X.
   - 무엇을 모르나: video file + response_schema=PydanticModel 시 작동 / 일부 작동 / 미작동?
   - 권장: planner 가 spike 1회 — 작동 시 신 path 사용, 미작동 시 Plan 01-13 spike 방식 그대로 (prompt 만, JSON 수동 파싱)

3. **Low confidence 분포 — D-09 case 2 threshold** — 5영상 sweep 실측 후 박제 (D-10 deferred).
   - 무엇을 모르나: 정상 인식 시 confidence 분포 vs 미인식 시 분포 차이.
   - 권장: Phase 5 마지막 plan 또는 별 plan — 5영상 sweep 후 결과 분석 → threshold 박제

4. **영상 hash 캡싱의 cache invalidation** — yaml 갱신 시 (예: ref-foxtop hold 추가) cache 가 stale.
   - 무엇을 모르나: cache key 에 yaml content hash 포함? 또는 yaml 갱신 시 cache 전체 삭제?
   - 권장: cache 에 `yaml_version` (yaml 파일 SHA256 또는 git commit) 박제 — lookup 시 mismatch 면 cache miss

5. **TERM-DATA-01 분기 3 자동 수집 schema** — Phase 16 책임이지만 Phase 5 가 trigger 만 호출.
   - 무엇을 모르나: `record_unregistered_keyword(keyword, uid, video_hash)` 가 어느 컬렉션에 어느 schema 로 저장하나? Phase 16 박제 vs 별 plan?
   - 권장: planner 가 Phase 16 박제 spec 확인 후 박제 — Phase 5 는 trigger 코드만, schema 정합은 Phase 16 책임

---

## Project Constraints (from CLAUDE.md)

| Constraint | Source | Impact on Phase 5 |
|------------|--------|-------------------|
| 작은 단위로 작업 | §7 코드 품질 | Phase 5 = 어댑터 신설 + wiring — task 단위 분리 (어댑터 / 캡싱 / pipeline switch / sweep 통합) |
| 의미있는 테스트만, 수치 채우기 금지 | §7 | Plan 01-13 spike 87 PASS + Phase 5 신설 약 30 = 의미있는 테스트 단위 |
| 이모지 금지, 슬롭 코드 금지 | §7 | RESEARCH.md / 코드 / 테스트 / 박제 문서 모두 이모지 0 |
| 막히면 "Do not work yet" 후 질문 먼저 | §7 | Open Questions 1~5 박제 — planner 가 답하거나 spike 후 박제 |
| 작업 완료 시 plan.md 업데이트 | §7 | Phase 5 종료 시 STATE.md / ROADMAP.md / plan.md 갱신 |
| AWS Parameter Store 사용 (`.env` 하드코딩 금지) | §3 | D-15 박제 정합 — `/sunity/motion/gemini-api-key` SecureString + env fallback |
| 인프라 = Lambda + S3 (sunity.ai EC2 와 분리) | §3 | Phase 5 의 Gemini 호출은 RunPod Pod 단독 (D-12) — Lambda 측 미사용. EC2 영향 0 |
| Motion AI = 별도 인프라 | §3 | Firestore `gemini_cache`, `term_collection` 모두 sunity-ai-coach 프로젝트 (기존) — 새 프로젝트 신설 X |
| ML 파이프라인 = YOLO11 → ViTPose-S → MotionDTW | §3 (outdated) | 실제 박제 = RTMW wholebody (Plan 21+22) — CLAUDE.md 갱신 권장 (Phase 5 외 작업) |
| LLM = Cerebras 빠른 추론 | §3 | Phase 5 = Gemini 3.1 Pro (분류만), Phase 11 = Cerebras llama3.1 (자연어 코칭) — 역할 분리 박제 정합 |

---

## Sources

### Primary (HIGH confidence)

- `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` — Plan 01-13 spike 박제 코드 (KeyMoment + GeminiMomentExtractor + reject patterns + assign_frame_indices + lazy import)
- `backend/shared/python/sunity_shared/judging/geometric_criterion.py` — IPSF Code of Points 기반 GeometricCriterion + VALID_MOMENT_KEYS
- `backend/shared/python/sunity_shared/judging/moment_dimensions.py` — measure_moment_angles + score_moment (D-05 v1 dead, D-06 v2 자동 활성)
- `backend/shared/python/sunity_shared/judging/loader.py` — yaml 로더 (load_grouped_criteria)
- `backend/shared/python/sunity_shared/analysis/technique.py` — TechniqueProfile + TechniqueRecognizer Protocol + FallbackRecognizer
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — line_score / stability_score / absolute_dimension_scores (Page 9 코드 path)
- `backend/functions/pipeline/app.py` — _process + _RECOGNIZER + _ensure_adapters
- `backend/runpod_inference/server.py` — Pod 1pass + _process_in_background + _warmup
- `backend/runpod_inference/requirements.txt` + `setup.sh` — Pod 환경 박제
- `backend/research/evaluations/compare_rtmw_vs_ipsf.py` — Plan 23 sweep 백본 (수정 대상)
- `backend/research/spikes/spike_gemini_moment.py` — Plan 01-13 CLI 참조
- `backend/judging_data/criteria/ref-foxtop.yaml` (+ 5영상 yaml) — 출력 구조 예시
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-13-SUMMARY.md` — Plan 13 verdict measurement_unreliable_blocked + 3증거 박제
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-23-SUMMARY.md` — Plan 23 sweep verdict phase1_ready_to_swap=False + root cause 3
- `.planning/REQUIREMENTS.md` — SCORE-01 / SCORE-05 / TERM-COPY-01 박제
- `.planning/STATE.md` — Phase 5 권장 모델 Gemini 3.1 Pro 단일 (belle 2026-06-04 확정) + Plan 23 verdict + Pod 환경 박제
- [Google Gen AI Python SDK docs](https://googleapis.github.io/python-genai/) — `google-genai` 신 SDK 공식 docs [CITED]
- [Gemini API: Video Understanding](https://ai.google.dev/gemini-api/docs/video-understanding) — Files API + 1FPS sampling + MM:SS timestamp [CITED]
- [Gemini API: Structured Output](https://ai.google.dev/gemini-api/docs/structured-output) — response_mime_type + response_schema + Pydantic [CITED]
- [Gemini API: Files](https://ai.google.dev/gemini-api/docs/files) — PROCESSING/ACTIVE 폴링 [CITED]
- [Gen AI SDK Migration Guide](https://ai.google.dev/gemini-api/docs/migrate) — legacy `google-generativeai` → 신 `google-genai` [CITED]

### Secondary (MEDIUM confidence)

- [JSON Response Schema - Mintlify python-genai guide](https://mintlify.com/googleapis/python-genai/guides/json-response) — Pydantic schema + response.parsed 자동 변환 [CITED]
- [Gemini 3.1 Pro Model Card - DeepMind](https://deepmind.google/models/model-cards/gemini-3-1-pro/) — 모델 capability + video benchmark [CITED]
- [Gemini 3 Pro Testing Multimodal](https://www.allaboutai.com/resources/tested-gemini-performance/) — video-MMMU 87.6% [CITED]
- [Gemini 3 Pro for YouTube Video Understanding](https://chatlyai.app/blog/gemini-3-pro-for-video-analysis) — temporal stream + timestamp 처리 [CITED]
- [google-genai · PyPI](https://pypi.org/project/google-genai/0.7.0/) — 패키지 정합 확인 [CITED]
- [Gen AI SDK GitHub repo](https://github.com/googleapis/python-genai) — 공식 source [CITED]

### Tertiary (LOW confidence — needs validation)

- Plan 23 sweep verdict 의 root cause 1 (FallbackRecognizer 한계) 해결 시 angle 회복률 — belle Pod 실측 필요
- Gemini 3.1 Pro 의 5영상 motion_name 분류 정확도 — Phase 5 작은 spike 후 박제
- Pod startup 시 `_load_api_key()` 명시 호출의 실제 효과 — Pod 환경 1회 실험 후 박제

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `google-genai` 공식 docs + Plan 01-13 spike 박제 검증
- Architecture (3-case fallback + 캡싱): MEDIUM — D-09/D-14 박제 정신은 명확, 구체 schema (gemini_cache vs analyses 단독) 는 planner 결정
- Pitfalls: MEDIUM-HIGH — Plan 01-13 spike 실측 박제 (3증거) + 신 SDK 마이그레이션 함정 박제
- Production wiring path: MEDIUM — 기존 박제 인프라 (Pod / Lambda / Firestore) 재사용이지만 신설 모듈 2개 (gemini_technique_recognizer + technique_cache) + 변경 영역 3 (pipeline / sweep / requirements)
- Validation Architecture: HIGH — Plan 01-13 87 PASS + Plan 23 11 PASS 박제 + Wave 0 신설 약 30 = 의미있는 단위
- Security: MEDIUM-HIGH — 박제 reject patterns 19 + Plan 01-13 객관성 가드 + Pod 인증 박제. Firestore rules 갱신 필요 (Wave 0 또는 planner 박제)

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (Gemini SDK fast-moving — 30일 후 재검증 권장)

---

## SUPPLEMENT — NotebookLM IPSF Lookup 결과 통합 (2026-06-04, researcher 작성 후 orchestrator 박제)

본 RESEARCH.md 작성 중 orchestrator 가 평행으로 NotebookLM IPSF Code of Points 2024-2025 lookup 수행. 결과 = `.planning/phases/05-gemini/05-IPSF-LOOKUP.md` 박제. **Critical finding 박제 — 본 RESEARCH.md 의 D-08 가정 (yaml IPSF source 그대로 유지) 무효**:

### Lookup 결과 요약

| 모션 | IPSF 등재 | yaml hold_moment angle 박제 source |
|---|---|---|
| ref-climb | ✓ Transitions & Climbs (hold = 이동 2회, angle 채점 X) | **IPSF 출처 X** |
| ref-foxtop | ✗ 미등재 (P9 절대 트랙만) | **IPSF 출처 X** |
| ref-foxtop-split | ✗ 미등재 (P9 절대 트랙만) | **IPSF 출처 X** |
| ref-invert | ✓ Body Position Inverted (관절 angle X, body position ±20°) | **IPSF 출처 X** |
| ref-sideway-spin | ✗ 미등재 (P9 절대 트랙만) | **IPSF 출처 X** |

→ 현 `backend/judging_data/criteria/*.yaml` 의 `angle_target=180°` 박제 5개 전부 IPSF source 박제 X. Plan 23 sweep verdict root cause 3 (yaml 정합 미검증) 의 정확한 실증.

### belle 박제 결정 (2026-06-04)

- **D-01 게이트 재정의** = "정은지 reference 측정값 기준 5/5 PASS" (IPSF 직접 박제 X → 분기 2 정은지 reference path 박제). 박제 [[studio-term-3branch-system.md]] 분기 2 + [[analysis-objectivity-no-human-scores.md]] 정합.
- **D-08 갱신** = yaml 의 angle_target / tolerance / minimum 수치 = 정은지 reference 측정값 박제 (IPSF source 박제 X 명시). source_ref 정정 = D-17 책임.
- **D-17 신설** = Phase 5 첫 plan = yaml source 정은지 reference 측정값 정정 작업 (5영상 reference 영상 측정 → yaml 갱신). Gemini wiring (researcher 의 Plan 5-01 ~ 5-05) 은 yaml 정정 후 plan.
- **D-19 신설** = ref-invert 의 Body Position Inverted 차원 추가 = Phase 5 scope 외 (별 phase 또는 Phase 8 책임). v1 ref-invert = 6관절 angle 박제 (정은지 측정값) 단독 채점.
- **D-20 신설** = ref-climb 의 "이동 횟수" 차원 추가 = Phase 5 scope 외 (별 phase 책임). v1 ref-climb = 6관절 angle 박제 (정은지 측정값) 단독 채점.

### Plan Decomposition 영향

기존 researcher 제안 (Plan 5-01 ~ 5-06) 에 **새 Plan 5-00 선행** 추가 박제:

- **Plan 5-00 (NEW, 선행 필수):** yaml source 정은지 reference 측정값 정정 작업 — 5영상 정은지 reference 영상 RTMW pose 산출 + hold moment timestamp 박제 + 6관절 angle 측정 + yaml `angle_target` / `tolerance` / `minimum` / `source_ref` 갱신 + belle 승인 박제. D-17 / D-18.
- Plan 5-01 ~ 5-05 = researcher 박제 그대로 (Gemini 어댑터 + 캡싱 + Pod wiring + sweep 통합)
- Plan 5-06 (선택) = Low confidence threshold 박제

Plan 5-00 통과 후 = yaml 박제 source 정합 → Gemini 어댑터 wiring (5-01~) 진입 정합. Plan 23 sweep 재실행 게이트 = "정은지 reference 기준 5/5 PASS" 로 자연 정의.

### 박제 정신 정합 확인

- [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" → 게이트 기준이 IPSF 가 아니라 **정은지 reference** 로 박제 변경 = 우회 X (다른 객관 기준 박제). 박제 정합.
- [[analysis-objectivity-no-human-scores.md]] → 정은지 reference **측정값** (객관 수치) 박제 OK. "정은지가 좋다고 판단" (사람 점수) 박제 X. 박제 정합.
- [[studio-term-3branch-system.md]] 분기 2 = "한국 학원 통용 + 정은지 reference 비등재 동작". foxtop / sideway-spin = 분기 2 정합. ref-invert (IPSF 등재) 도 yaml 박제 source = 정은지 reference 측정값 = 분기 2 path 정합.
- [[mvp-simple-pilot-quality.md]] "MVP 가볍게" → scope 5영상 유지 + yaml 박제 source 만 정정. 정합.

### Open Questions (NotebookLM lookup 후 갱신)

기존 5개 + 새 2개:
6. yaml `angle_target` / `tolerance` 산출 룰 (정은지 측정값 ±15° tolerance? minimum = 측정값 - 25°?) — Plan 5-00 안에서 belle 박제.
7. ref-invert 의 Body Position Inverted 차원 추가 = 별 phase / Phase 8 / 신설 phase 중 어디 — belle 박제 (Phase 5 scope 외).

### 후속 NotebookLM lookup 추천 (Plan 5-00 후속)

- Basic Invert Hold IPSF element code + angle criteria
- Inverted Split / Inverted Thigh Hook element code (ref-foxtop 변형 가능성)
- Page 9 정확 인용 (CoP 2025-2027 page) — D-09 P9 routing 박제 source
- Element Code Matching p.138-139 (Gemini 분류 → element code 매핑 path)

---

## RESEARCH COMPLETE

**Phase:** 5 - Gemini 기술 인식기 (분류 한정)
**Confidence:** MEDIUM-HIGH

### Key Findings

- Plan 01-13 spike `GeminiMomentExtractor` + `KeyMoment` + reject patterns 19 + lazy import 패턴 모두 박제 — Phase 5 의 실제 작업은 어댑터 wrapper + 3-case fallback wiring + 영상 hash 캡싱 + Plan 23 sweep 통합 4건. spike 코드 0줄 수정 정신 유지 가능.
- Plan 01-13 verdict `measurement_unreliable_blocked` 의 root cause = RTMPose+MB lift 약점 + 단일 frame sampling. Phase 5 는 RTMW pivot (Plan 21+22) + frame-mean sampling (`hold_window`) 후 환경이라 Plan 13 함정 회피된 새 환경.
- Plan 23 sweep angle 0/5 root cause 1 (FallbackRecognizer 한계, IPSF target=180° 일률) → Gemini 어댑터 가 동적 EXTEND/BENT_OK 라벨링 → `dimensions.line_score` 가 EXTEND 관절만 채점 → 위양성 0 → angle 4~5/5 PASS 회복 예상 (실측 필요).
- Gemini 3.1 Pro multimodal video = Files API 업로드 + 1FPS sampling + MM:SS timestamp 정확도 ±1~2초 [CITED]. hold (2~5초) windowing 으로 흡수 가능. peak (0.5~1초) 활성 시 별 plan.
- `google-genai` 신 SDK + `response_mime_type=application/json` + Pydantic `response_schema` 가 video file input 과 작동하는지 docs 미명시 — planner 가 작은 spike 후 박제 권장 (A2).
- Pod env 박제 path = `setup.sh` Step [7/7] 신설 + Pod startup 시 `_load_api_key()` fail-loud + `GEMINI_RECOGNIZER_ENABLED` env switch (A/B 비교 가능).

### File Created

`/Users/kimtaesung/Dev/SunityMotion/.planning/phases/05-gemini/05-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | `google-genai` 공식 docs [CITED] + Plan 01-13 spike 박제 |
| Architecture (어댑터 + 3-case fallback) | MEDIUM-HIGH | D-09 / D-12 / D-14 박제 정신 명확, 구체 schema (gemini_cache 컬렉션 vs analyses 단독) 는 planner 결정 |
| Pitfalls | MEDIUM-HIGH | Plan 01-13 spike 3증거 + SDK 마이그레이션 함정 박제 |
| Production wiring path | MEDIUM | 기존 박제 재사용 + 신설 모듈 2 + 변경 영역 3 — 의미있는 단위 분리 가능 |
| Validation | HIGH | 87 + 11 PASS 박제 + Wave 0 약 30 신설 path 명확 |
| Security | MEDIUM-HIGH | reject patterns 19 + 객관성 가드 + Pod 인증 박제. Firestore rules 1건 신설 필요 |

### Open Questions (planner 처리)

1. **Gemini motion_name 분류 path** — 작은 spike 후 박제 (5영상 each 에 prompt → 응답 분석 → 정규화 path)
2. **`response_schema` + video input** — planner spike 1회 (작동 시 신 path, 미작동 시 Plan 01-13 박제 방식)
3. **Low confidence threshold (D-10)** — Phase 5 마지막 plan 또는 별 plan
4. **영상 hash 캡싱 invalidation** — cache 에 yaml_version 박제 권장
5. **TERM-DATA-01 분기 3 schema** — Phase 16 박제 spec 확인 후 박제

### Ready for Planning

Research 완료. Planner 가 Phase 5 plan 들을 작성할 수 있습니다:
- Plan 5-01: 어댑터 신설 (GeminiTechniqueRecognizer + 3-case fallback + 단위 테스트)
- Plan 5-02: 영상 hash 캡싱 (technique_cache + Firestore wiring + 단위 테스트)
- Plan 5-03: pipeline `_RECOGNIZER` swap + env switch + 통합 테스트
- Plan 5-04: Pod env / requirements / setup.sh wiring + Pod 시작 fail-loud
- Plan 5-05: Plan 23 sweep `--recognizer gemini` flag + belle 검토 checkpoint
- Plan 5-06 (선택): Low confidence threshold 5영상 실측 + 박제 (또는 별 plan)

Sources:
- [Gemini API: Video Understanding](https://ai.google.dev/gemini-api/docs/video-understanding)
- [Gemini API: Structured Output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini API: Files](https://ai.google.dev/gemini-api/docs/files)
- [Gen AI SDK Migration Guide](https://ai.google.dev/gemini-api/docs/migrate)
- [Google Gen AI Python SDK docs](https://googleapis.github.io/python-genai/)
- [JSON Response Schema - Mintlify python-genai guide](https://mintlify.com/googleapis/python-genai/guides/json-response)
- [Gemini 3.1 Pro Model Card - DeepMind](https://deepmind.google/models/model-cards/gemini-3-1-pro/)
- [Gemini 3 Pro for YouTube Video Understanding](https://chatlyai.app/blog/gemini-3-pro-for-video-analysis)
- [google-genai · PyPI](https://pypi.org/project/google-genai/0.7.0/)
- [Gen AI SDK GitHub repo](https://github.com/googleapis/python-genai)
