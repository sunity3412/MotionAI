# RESEARCH — Phase 17: Gemini Vision Integration — 4 영역 통합

> Codebase 통합 path 분석. AI-SPEC.md (framework + domain + eval) 와 함께 planner 가 consume.
> 작성일: 2026-06-12. 작성자: orchestrator 직접 (gsd-phase-researcher API 에러로 우회).

---

## 1. 통합 path Overview

Phase 17 = **신규 인프라 0**. 기존 Lambda + RunPod Pod 위에 Gemini 호출 모듈을 신설하고, 기존 단일 진입점 (`_process`) 의 정해진 위치에서 호출하는 패턴.

```
┌─ Lambda (sync) ────────────────────────────────────────────┐
│  영역 A: Reference 자동 등록                                │
│    - 신규 endpoint POST /reference/auto-register           │
│    - 정은지 영상 S3 key 입력 → Gemini A 호출 → Firestore   │
│    - sync (belle UX: 등록 후 즉시 확인)                     │
└─────────────────────────────────────────────────────────────┘

┌─ RunPod Pod (async, 기존 _process 안) ──────────────────────┐
│  사용자 영상 분석 pipeline:                                  │
│    1. frame_extract → RTMW keypoint                         │
│    2. compute_joint_angles → DTW vs reference               │
│  ┌─ Phase 17 추가 (병렬 wave) ─────────────────────────┐   │
│  │  Wave 1 (asyncio.gather):                          │   │
│  │    A 영역: skip (Lambda 에서 별도 호출)              │   │
│  │    C 영역: Gemini Flash (finding flag)             │   │
│  │  Wave 2 (asyncio.gather):                          │   │
│  │    B 영역: Gemini Pro coach (Cerebras 와 dual)     │   │
│  │    D 영역: Gemini Pro keypoint 보강 (RTMW < 0.5)   │   │
│  └────────────────────────────────────────────────────┘   │
│    3. assemble result → Firestore                          │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 결정

| 영역 | 실행 위치 | sync/async | 이유 |
|---|---|---|---|
| A Reference 등록 | **Lambda** (신규 endpoint) | sync (HTTP 응답) | belle UX = 등록 직후 결과 확인. 정은지 영상만 호출 (빈도 낮음). RunPod 의존 X = belle 가 폰/노트북에서 직접 호출 가능. |
| B 코칭 멘트 | **Pod** (`_process` 안) | async (BackgroundTask) | 영상이 이미 Pod GPU 메모리. Cerebras 호출 자리 swap target. |
| C Finding flag | **Pod** (`_process` 안) | async (BackgroundTask) | 영상 frame 이미 있음. 빈도 = 모든 분석 1회. |
| D Keypoint 보강 | **Pod** (`_process` 안) | async (BackgroundTask) | RTMW 결과 + frame 둘 다 Pod 에. RTMW confidence < 0.5 frame 만 호출 (조건부, 빈도 낮음). |

---

## 2. 기존 모듈 → Phase 17 mapping

| 기존 모듈 (절대 경로) | Phase 17 작업 | 변경 형태 |
|---|---|---|
| `backend/functions/pipeline/app.py::_process` | wave 1+2 추가 — `_RTMWNlfCompat.estimate` 직후 + `kismam.assess` 직전 | 신규 코드 ~80 lines (asyncio.gather 2 wave) |
| `backend/functions/pipeline/app.py::_ensure_recognizer` | 그대로 유지 — 영역 A 는 별도 path (Phase 5 GeminiTechniqueRecognizer 는 그대로) | 변경 0 |
| `backend/shared/python/sunity_shared/analysis/coach_writer.py` | B 영역 swap — `CerebrasCoachWriter` interface 유지. `GeminiCoachWriter` 신설 → adapter 선택 env | 신규 클래스 1개, 기존 변경 0 (additive) |
| `backend/shared/python/sunity_shared/analysis/gemini_moment_extractor.py` | A/B/C/D 의 client init / Files API 패턴 직접 재사용. `_load_api_key` / `AQ.` 키 fallback 그대로 | 변경 0 (참조만) |
| `backend/shared/python/sunity_shared/firestore_admin.py::complete_analysis` | 결과 doc 에 `geminiC` / `geminiB` / `geminiD` 필드 추가 (Firestore nested array 금지 정합) | 함수 시그너처 확장 (kwarg 추가) |
| `backend/shared/python/sunity_shared/firestore_admin.py::set_reference_motion` | 영역 A 가 호출 — `clipRange` / `checkpointJoints` / `referenceKeypointReport` 필드 박힘 | 새 함수 또는 set kwargs 확장 |
| `backend/functions/upload-url/app.py` | 영역 A 의 신규 endpoint 와 별개 — 변경 0 | 변경 0 |
| 신규 endpoint Lambda `backend/functions/reference-auto-register/app.py` | A 영역 진입점. SAM template 추가 | 신규 함수 (SAM resource 박힘) |
| `app/scripts/seed-reference-motions.mjs` | 영역 A 가 자동화 → 수동 seed 보완 (편집/검증 toolling) | 변경 0 (영역 A 결과 검수 후 belle 가 manual override 필요시 그대로 사용) |
| `app/src/app/analysis/result.tsx` | B 영역 코칭 멘트 표시 — 기존 `tips[]` 그대로 / C 영역 finding badge 표시 가능 (신규 UI 카드) | 신규 카드 컴포넌트 (선택, MVP 박힘 박힘 박힘 박힘 → Phase 15 와 묶음) |

---

## 3. 신규 모듈 구조

```
backend/shared/python/sunity_shared/gemini/
├── __init__.py
├── client.py              # 공통 client + Files API + ACTIVE 폴링 + retry
├── schemas.py             # 4 영역 Pydantic 모델 (ReferenceRegistration / CoachPayload / FindingFlags / KeypointRefinement)
├── reference_extractor.py # 영역 A 호출
├── coach_writer_v2.py     # 영역 B 호출 (CerebrasCoachWriter interface 정합)
├── scene_finder.py        # 영역 C 호출
└── keypoint_augmenter.py  # 영역 D 호출

backend/functions/reference-auto-register/
├── app.py                 # 영역 A Lambda entry
└── requirements.txt
```

기존 `sunity_shared/analysis/gemini_*.py` (Phase 5 산출물) 은 그대로 — Phase 17 의 `sunity_shared/gemini/` 는 별도 namespace.

---

## 4. 4 영역 wave sequencing (Pod `_process` 안)

```python
# backend/functions/pipeline/app.py::_process 의 wave 추가 부분 박힘 박힘.
# RTMW estimate 직후 + scoring 직전.

import asyncio
from sunity_shared.gemini.scene_finder import find_scene_flags
from sunity_shared.gemini.coach_writer_v2 import write_coach_gemini
from sunity_shared.gemini.keypoint_augmenter import augment_low_confidence

# ── 기존: RTMW estimate ──
coco_array, profile = _POSE_ESTIMATOR.estimate_with_profile(frames)
# ... compute_joint_angles, DTW, KISMAM, dim_scores 등 — RTMW 원본 그대로 계산 ...

# ── Phase 17 wave 1: 영역 C (모든 분석 1회) ──
# 빈도 100%, latency-sensitive → Flash. wave 2 와 병렬 가능.
async def wave1():
    return await find_scene_flags(local_video_path)

# ── Phase 17 wave 2: 영역 B (조건부) ──
# (2차 R-B1 정합: D 는 별도 위치 — wave 2 와 분리)
async def wave2():
    # B 영역: 분석 결과 (joints + dim scores) + 영상. v1 에서는 geminiD context 포함 X.
    coach_context = _build_coach_context(
        angles=angles, dim_scores=dim_scores, mode=mode,
        local_video_path=local_video_path, scene_flags=scene_flags,
    )
    if GEMINI_COACH_ENABLED:
        return gemini_coach_writer.write(coach_context)
    return cerebras_coach_writer.write(coach_context)

# wave 1+2 병렬 실행
scene_flags, coach_result = await asyncio.gather(wave1(), wave2())

# ── 기존: assemble.build_result (RTMW 원본 dim_scores 박제) ──
result = assemble.build_result(assessments, dim_scores, overall_score, comparison, ...)

# ── 기존: build_keypoint_report (RTMW 원본 + assemble) ──
keypoint_report = build_keypoint_report(pose_frames, fps=9.0)

# ── Phase 17 영역 D (B2 정합 — KeypointReport.data/confidence 만 보강) ──
# 위치: build_keypoint_report 직후 + complete_analysis 직전. coco_array mutate 0.
# 식별: uncertainty_proxy (4번째 채널) max > 0.5 — pose_frame.py to_coco17_array 정합.
if GEMINI_D_ENABLED and local_video_path and not scene_flags.get("occlusion_severe"):
    low_uncertainty_frames = [
        i for i, u in enumerate(coco_array[:, :, 3].max(axis=1)) if u > 0.5
    ]
    if low_uncertainty_frames:
        # augment_low_confidence 시그니처: KeypointReport 입력/출력 — coco_array 인자 0.
        d_result = augment_low_confidence(
            local_video_path, low_uncertainty_frames, keypoint_report, frame_w, frame_h,
        )
        # KeypointReport dataclass replace (frozen 정합) — data/confidence/reliability/warnings 만 갱신.
        keypoint_report = dataclasses.replace(
            keypoint_report,
            data=apply_refined_to_data(keypoint_report.data, d_result["refined"]),
            confidence=apply_refined_to_confidence(keypoint_report.confidence, d_result["refined"]),
            reliability=recompute_reliability(...),
            warnings=keypoint_report.warnings + ["gemini_d_augmented"],
        )

# ── 기존: complete_analysis — 보강된 keypoint_report + audit geminiD ──
firestore_admin.complete_analysis(
    uid, analysis_id, ...,
    keypoint_report=keypoint_report,  # user-visible (D 보강 반영)
    gemini_c=scene_flags, gemini_b=coach_audit, gemini_d=d_result,  # top-level audit
)
```

**Phase 17 v1 wave 순서 박제 (2차 R-B1 정정):**
1. RTMW estimate (`coco_array`, `pose_frames`)
2. compute_joint_angles / DTW / KISMAM / dim_scores — 모두 RTMW 원본
3. wave 1 (C) + wave 2 (B) 병렬 (asyncio.gather)
4. `assemble.build_result(dim_scores, ...)` — RTMW 원본 dim_scores
5. `build_keypoint_report(pose_frames)` — RTMW 원본 KeypointReport
6. **영역 D (B2-v1)** — KeypointReport.data/confidence 보강 + mirror hint
7. `complete_analysis(..., keypoint_report=augmented, gemini_d=audit)`

**D-v2 deferred** (좌표계 계약 박은 후 별도 plan): coco_array 주입 + DTW/KISMAM/dim_scores 재계산. v2 진입 시 wave 순서 재조정 — D 가 B/build_result 보다 먼저, B context 에 geminiD 박제 가능.

**왜 wave 1+2 분리?** wave 1 (C) 는 모든 분석. wave 2 (B/D) 는 조건부 / feature flag. 분리하면 wave 2 가 실패해도 C 결과 손실 0.

---

## 5. Firestore schema 변경

### 5-1. `users/{uid}/analyses/{id}` (사용자 분석 결과)

기존 + 신규 필드:

```json
{
  // 기존 그대로
  "status": "done",
  "result": { "overallScore": 90, "joints": [...], ... },

  // Phase 17 신규 (전부 optional, missing 시 fallback)
  "geminiC": {
    "gripVisible": true,
    "backbendPresent": false,
    "occlusionSevere": false,
    "cameraAngleProblematic": false,
    "notesKo": "...",
    "model": "gemini-3.5-flash",  // E5 auto-escalation 시 "gemini-3.1-pro-preview"
    "tokensUsed": 384,
    "latencyMs": 3200
  },
  "geminiB": {
    "causes": [{"title": "...", "explanation": "...", "fix": "..."}, ...],
    "coachNote": "...",
    "model": "gemini-3.1-pro-preview",
    "judgeScore": null  // F1 flywheel 이 채움
  },
  "geminiD": {
    "augmentedFrames": [12, 13, 14],  // 보강된 frame index
    "originalConfidence": [0.21, 0.18, 0.25],
    "model": "gemini-3.1-pro-preview"
  }
}
```

### 5-2. `reference/{motionId}` (정은지 reference)

영역 A 가 자동 채우는 필드 박힘:

```json
{
  // 기존 (seed-reference-motions.mjs 가 박는 거)
  "motionId": "ref-elbow-twist-sister",
  "name": "엘보 트위스트 시스터",
  "videoUrl": "...",
  "angles": [...],  // RTMW 또는 NLF 추출
  "referenceKeypointReport": {...},

  // Phase 17 영역 A 자동 채움 (수동 seed 가 override 가능)
  "geminiA": {
    "motionNameIpsf": "Inverted Thigh Hook Side (변형)",  // 또는 null (분기 2/3)
    "routingBranch": "branch_2_studio",  // "branch_1_ipsf" | "branch_2_studio" | "branch_3_auto"
    "clipRange": {
      "prepStartS": 0,
      "execStartS": 1.5,
      "execPeakS": 8.0,
      "landEndS": 21.5,
      "recommendedRecordS": 25
    },
    "checkpointJoints": [
      {"joint": "left_shoulder", "weight": 0.2, "rule": "EXTEND", "note": "..."},
      ...
    ],
    "rawJsonResponse": "...",  // 원본 Gemini 출력 (review용)
    "reviewRequired": false,  // G3 guardrail = true 면 belle 검수 필요
    "model": "gemini-3.1-pro-preview",
    "registeredAt": "2026-06-12T..."
  },
  "isActive": true,  // belle 검수 후 true. G3 fallback 시 false 유지.
  "inactiveReason": null  // G3 시 "ipsf_whitelist_miss"
}
```

### 5-3. nested array 금지 정합

- `geminiC` / `geminiB` / `geminiA` = flat object (nested array 없음)
- `geminiD.augmentedFrames` / `geminiD.originalConfidence` = 1D array OK
- `geminiA.checkpointJoints` = array of object (각 object 의 field 는 scalar) — Firestore 허용

---

## 6. 신규 6 motion (UAT 2026-06-12 finding) 해소 path

신규 6 의 NLF↔RTMW 호환 깨짐 finding (현재 isActive=false 박혀있음) → 영역 A + D 가 해소:

| 단계 | 작업 |
|---|---|
| 1 | 영역 A endpoint 호출 — 신규 6 영상 → Gemini A → `motionNameIpsf` + `clipRange` + `checkpointJoints` 자동 산출 |
| 2 | belle 검수 (`reviewRequired=false` 인지 확인, 분기 라벨 검토) |
| 3 | RTMW 로 신규 6 영상의 angles 재추출 — 운영과 동일 engine (extract_reference_angles.py 의 NlfPoseEstimator → `_RTMWNlfCompat` swap 필요) |
| 4 | Firestore seed 재실행 — angles + bodyComparisonSourcePose + geminiA |
| 5 | isActive=true |
| 6 | 사용자 분석 시 D 영역 (keypoint 보강) 이 RTMW 저신뢰 frame 박혀있는 거 fallback — inverted/twist 자세 정확도 회복 |

**Phase 17 의 진짜 가치** = "신규 reference 영상 추가 시 NLF↔RTMW 호환 박는 과정이 사라짐" — 영역 A 가 RTMW-native angles + Gemini 의 IPSF 명칭 자동 산출.

---

## 7. env variable 설계

| Env | 위치 | 값 | 용도 |
|---|---|---|---|
| `GEMINI_API_KEY` | Lambda + Pod 양쪽 | `AQ.xxx` (기존) | client init |
| `GEMINI_MODEL` | (deprecated) | — | Phase 17 후 영역별 분리 |
| `GEMINI_A_MODEL` | Lambda | `gemini-3.1-pro-preview` | A 영역 model |
| `GEMINI_B_MODEL` | Pod | `gemini-3.1-pro-preview` (또는 `cerebras` 로 swap) | B 영역 model |
| `GEMINI_C_MODEL` | Pod | `gemini-3.5-flash` | C 영역 model (기본) |
| `GEMINI_C_MODEL_OVERRIDE` | Pod | `gemini-3.1-pro-preview` (E5 manual emergency override; auto-escalation 은 runtime config) | C 영역 Pro 승급 우회 |
| `GEMINI_D_MODEL` | Pod | `gemini-3.1-pro-preview` | D 영역 model |
| `GEMINI_COACH_ENABLED` | Pod | `1` (default) / `0` (Cerebras fallback) | B 영역 toggle |
| `PHOENIX_OTLP_ENDPOINT` | Lambda + Pod | (optional) | tracing self-host endpoint |

기존 `GEMINI_MODEL` (Lambda env `gemini-2.5-flash`) = Phase 17 진입 시점에 영역별 env 4개로 split. Phase 5 GeminiTechniqueRecognizer 는 `GEMINI_MODEL` 그대로 사용 → backward compat 위해 deprecated 단계 거침.

---

## 8. App (React Native) 측 변경

**MVP scope 결정 (memory [[mvp-simple-pilot-quality]] 정합)**:

| 영역 | App 변경 필요? | scope |
|---|---|---|
| A Reference 등록 | belle 가 endpoint 직접 호출 (curl 또는 별도 admin 페이지) → App 변경 0 | Phase 17 |
| B 코칭 멘트 | 기존 `tips[]` 그대로 표시 → App 변경 0 | Phase 17 (백엔드만) |
| C Finding flag | 기존 `forcePatternInference.findings[]` 표시 자리 — 신규 카드 X (Phase 11 의 CoachCommentHook 데이터 구조 활용) | Phase 17 (백엔드만) |
| D Keypoint 보강 | 기존 KeypointOverlay 자동 활용 (보강된 좌표가 keypointReport 에 들어감) → App 변경 0 | Phase 17 (백엔드만) |

→ **Phase 17 = 백엔드 전용**. App UI 변경 0. OTA 도 X (Lambda + Pod 코드만). 영역 A 만 신규 SAM endpoint.

---

## 9. 실행 순서 (planner 용 입력)

**Wave 0 (선행)**: 공통 client + schemas 모듈 신설.
- `sunity_shared/gemini/client.py` (Files API 폴링 + retry + cost log)
- `sunity_shared/gemini/schemas.py` (4 영역 Pydantic 모델)
- Test: client 단위 테스트 (mock Files API)

**Wave 1**: 영역 C (Finding 인식) — 가장 단순.
- `sunity_shared/gemini/scene_finder.py`
- `_process` 안에 wave 1 추가
- Firestore `geminiC` 필드 박힘
- Test: 정은지 영상 5건 → occlusion_severe FP=0 (E6 hard gate)

**Wave 2**: 영역 D (keypoint 보강) — RTMW 약점 보강.
- `sunity_shared/gemini/keypoint_augmenter.py`
- `_process` 안에 wave 2 추가 (조건부)
- KeypointReport 의 보강 marker 박힘
- Test: 신규 6 motion 영상에서 RTMW < 0.5 frame 의 augment 결과 sanity

**Wave 3**: 영역 B (코칭 멘트) — Cerebras swap.
- `sunity_shared/gemini/coach_writer_v2.py`
- `coach_writer.py` interface 정합
- env toggle `GEMINI_COACH_ENABLED`
- Test: belle 검수 binary label 10건 (F6 A/B test 시작)

**Wave 4**: 영역 A (Reference 자동 등록) — 신규 Lambda.
- `backend/functions/reference-auto-register/app.py`
- SAM template 박힘 (신규 HTTP API route `POST /reference/auto-register`)
- `firestore_admin.set_reference_motion` 확장
- Test: 정은지 신규 6 영상 → Gemini A → Firestore seed → 검수

**Wave 5**: Eval + Guardrail wiring.
- Arize Phoenix self-host (Pod 또는 별도 EC2)
- Promptfoo CI/CD config
- §6 guardrail 6개 코드 박힘 (G1 객관성 reject regex 가 가장 critical)
- 60-example reference dataset 박는다
- Test: G1 hard fail 회귀 (정은지 영상 5건 객관성 검사)

**Wave 6**: 신규 6 motion 재활성화.
- `extract_reference_angles.py` 의 NLF → `_RTMWNlfCompat` swap
- 신규 6 영상 RTMW 재추출 + Firestore seed (angles + geminiA)
- isActive=true
- mock e2e 분석 (belle 폰 또는 mock script) — F4 finding 해소 검증

---

## 10. Test 전략 매핑

| Wave | Test 종류 | Critical Gate |
|---|---|---|
| Wave 0 | 단위 (client mock) | 0 dependency |
| Wave 1 | 정은지 5건 + calibration 30건 | E5 정확도, E6 정은지 FP=0 |
| Wave 2 | 신규 6 영상 RTMW < 0.5 frame | E7 인접 frame 거리 < 0.15 |
| Wave 3 | belle binary label 10건 | E4 톤 (LLM judge calibration ≥ 0.7) |
| Wave 4 | 정은지 신규 6 영상 | E2 IPSF 정합, E3 분기 라우팅, G3 fallback |
| Wave 5 | reference dataset 60건 전체 | G1 hard fail 0, E1~E8 baseline |
| Wave 6 | 신규 6 e2e 분석 | F4 finding 해소 (not_pole_motion 안 뜸) |

---

## 11. Open Questions (planner 가 결정)

1. **영역 A endpoint 인증** — belle 만 호출하는 admin endpoint. Firebase Admin SDK 인증? 또는 별도 admin secret?
2. **영역 D 조건 임계값** — confidence < 0.5 가 가설값. 실제 RTMW 출력 통계로 calibrate 필요 (Wave 2 에서 sweep).
3. **영역 B A/B test 비율** — F6 (Pro-vision vs Flash-text) 분석 50/50 무작위 vs 점진적 ramp?
4. **Phoenix self-host 위치** — Pod 안 in-process (간단) vs 별도 EC2 micro (영구). belle 의 비용 신경X + 효율 잡기 → EC2 micro 가 production 정합.
5. **Wave 6 의 신규 6 RTMW 재추출** — Phase 17 안에 박힐지, 별도 Phase 박힐지. Task #26 이 박혀있음.

---

## 12. Source 박힘

**Codebase (직접 read)**:
- `backend/functions/pipeline/app.py` L156, 237-258, 862-947, 1192-1297 (`_process` + `_ensure_recognizer` + `_RTMWNlfCompat`)
- `backend/runpod_inference/server.py` L63-196 (`_load_pipeline_module` + `/analyze` endpoint)
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` (전체 — `CerebrasCoachWriter` interface)
- `backend/shared/python/sunity_shared/analysis/technique.py` L40-92 (`TechniqueProfile` + `TechniqueRecognizer` Protocol + `FallbackRecognizer`)
- `backend/shared/python/sunity_shared/analysis/gemini_moment_extractor.py` (Phase 5 — Files API + `AQ.` 키)
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` L92-160 (`recognize` + cache)
- `backend/shared/python/sunity_shared/firestore_admin.py` (`complete_analysis` + `set_reference_motion` 검색)
- `app/scripts/seed-reference-motions.mjs` (수동 seed pattern — A 영역 자동화 대상)

**AI-SPEC.md**: §3 Framework Quick Reference (Files API 패턴), §4 Implementation Guidance (4 영역 model config), §4b AI Systems Best Practices (Pydantic + async + cost), §5 Evaluation Strategy (8 dimension), §6 Guardrails, §7 Production Monitoring.

**Memory**:
- [[gemini-latest-model-versions]] — 3.1 Pro / 3.5 Flash
- [[gemini-vision-active-use]] — 적극 활용, 비용 신경X, 효율 잡기
- [[feedback-analysis-first]] — 분석 정확도 최우선
- [[mvp-simple-pilot-quality]] — App 단순, 백엔드만 우선
- [[firestore-nested-array-flat]] — nested array 금지
- [[studio-term-3branch-system]] — 분기 1/2/3 라우팅
- [[scoring-dimensions-ipsf]] — IPSF Code of Points
- [[analysis-objectivity-no-human-scores]] — G1 hard fail

**Roadmap dep**: Phase 9 (ForceDirectionPattern), Phase 11 (CoachCommentHook), Phase 14 (정은지 reference) — 모두 close-out 또는 in-flight. Phase 17 = dep 박혀있음 (status: Pending).
