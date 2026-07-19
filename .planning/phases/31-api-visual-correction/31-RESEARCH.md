## Historical — do not implement (2026-07-19 supersede, 2차 리뷰 M2-03 격리)

아래 항목은 본문에 남아 있어도 **구현 금지** — 각 위치에 `[HISTORICAL]` 마커가 있다. 단일 기준은 31-CONTEXT.md [AMENDED 2026-07-19] + 31-01~31-12 PLAN 이다.

| Historical 내용 (본문 잔존) | 대체 (구현 기준) |
|---|---|
| R3F/PoseViewer3D/orbit 3D 뷰어 (책임 맵·Summary·diagram·dont-hand-roll·설치 표) | amended D-10: 2D 카메라 평면 뷰어 — 31-08 `PoseCompareViewer` (react-native-svg, three/R3F import 금지) |
| "silhouette" 명명 (필드·key·함수명) | L-02: `correctedPose` — key = `corrected_pose_{joint}.png` (31-02/31-04/31-09) |
| `_process` 내부/인라인 실루엣 생성 훅 | H-01/B2-03: enqueue-only + replay-safe reserve 분기 — 31-10 `_enqueue_corrected_pose_job` |
| 워커 단일 긴 폴링·fail_analysis 매핑·7일 presign 저장 | B-03/B2-02/H-02: action 단위 state machine + canonical key + 1h asset 재서명 — 31-09/31-10 |

충돌 시 PLAN.md 가 우선.

# Phase 31: 교정 시각물 — 기하 오버레이 + 외부 생성 API 실루엣 - Research

**Researched:** 2026-07-19
**Domain:** 시각 교정 출력 (backend PIL 렌더 확장 + DashScope 생성 API 통합 + R3F 3D 뷰어 활성화 + 학습 페어 적재)
**Confidence:** HIGH (코드베이스·spike 실측 기반) / MEDIUM (이미지 생성 모델 세부 스펙)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 스코프 구성
- **D-01:** 1단+2단 풀통합 — 오버레이 + 교정 실루엣(이미지) + 회전 참고코너 전부 이번 phase.
- **D-02:** 생성 엔진 = **Wan2.7-VideoEdit 확정** (2026-07-18 GEN3C 판정 완료). GEN3C(007b, 오픈)는 중앙 MAE 41.1°·이봉분포·역위/급격모션 인체붕괴로 부적격 — Wan2.7(spike 008 승자, MAE 중앙 9.9°) 유지. plan은 여전히 엔진 스왑 가능하게 추상화(VisualGenEngine 류) — GEN3C 는 depth 파이프라인 개선 후 재평가 후보(deferred). 키 = SSM `/sunity/motion/dashscope-api-key`.
- **D-03:** 교정 실루엣 = **정지 이미지 1장 먼저** (결함 top-1 부위의 순간 프레임 → 고친 폼). 영상 승격은 후속 phase. 이미지 생성 모델 사용 (수초~수십초, 수백원 내외 — Wan2.7-Image-Pro/Qwen-Image 등은 research 에서 선정).
- **D-04:** 회전 참고코너 = **하이브리드** — 기본 R3F 수학 3D 뷰어(환각 0·비용 0·즉시·인터랙티브, Spike 005 아키텍처) + Wan2.7 합성 영상은 옵션.

#### 생성 시점·비용 정책
- **D-05:** 교정 실루엣(이미지) = **분석 완료 시 자동 생성** (top-1 결함 부위만) — 첫 분석의 "전문가 수준" 인상(core value) 정합.
- **D-06:** 회전 합성 영상(건당 ~6-7분·과금) = **온디맨드 + 완료 알림** — 버튼 → 백그라운드 생성 → 카드 갱신. R3F 뷰어가 대기 중 즉시 대체재.
- **D-07:** 비용 가드 = **사용자당 일일 생성 한도** (구체 수치는 planner 재량, 파일럿 규모에서 사실상 무제한이되 남용 방지).
- **D-08:** 모더레이션 차단(실측 ~10%) 시 = **조용한 폴백** — 실패 미강조, R3F 뷰어/오버레이만 표시. "기능이 불안하다" 인상 방지.

#### 참고코너 UX
- **D-09:** 배치 = 결과 화면 **점수 내역 아래 "참고하세요" 섹션** — 채점과 시각적으로 분리 (점수 비반영 원칙이 레이아웃으로 드러나야 함).
- **D-10:** R3F 3D 뷰어 기본 표시 = **내 자세(실측 스켈레톤) + 목표 자세 반투명 중첩**, 손가락 드래그 회전.

#### 1단 오버레이
- **D-11:** **목표 각도 화살표부터** ("여기까지 올려야 함" 화살표 + 목표선) — 이상 궤적 선·힘 벡터는 후속.
- **D-12:** 적용 위치 = **기존 결함 줌 카드 위** — 기존 동선/컴포넌트 재사용, 신규 화면 0.

### Claude's Discretion
- 일일 한도 수치, 화살표/중첩 시각 스타일(단 theme 토큰·design.md 준수), R3F 씬 구성 상세, 이미지 생성 모델 선정(research 비교), 실루엣 프롬프트 설계.
- UI 작업 전 [[ux-propose-user-centric-screens-first]] — 최악 데이터 케이스 목업 선제시.

### 제약 (invariant)
- 카메라 앵글/실루엣 산출물은 **점수에 반영 금지** (stretch goal 게이트 미통과 상태 — spike 008 outlier 존재).
- 단일 카메라 UX 불변 — 다각도 촬영 요구 노출 절대 금지.
- 모더레이션 차단은 사용자에게 에러로 노출하지 않음 (D-08).
- Firestore nested-array 금지, 시크릿 Parameter Store, 브랜드 #FF4B33/Pretendard/라이트 전용.
- 페어 적재 = learningOptIn=true 사용자만, PII 정책 준수.

### Deferred Ideas (OUT OF SCOPE)
- 교정 실루엣 **영상** 버전 (D-03 후속 승격)
- 이상 궤적 선·힘 방향 벡터 오버레이 (D-11 후속)
- GEN3C 오픈 모델 재평가 — 재도전 조건 = depth 소스 개선. 구동 스텁은 볼륨 박제(재현 가능)
- 카메라앵글 재렌더의 측정(점수) 투입 — phase 22 자체 학습 트랙과 동행 재도전
</user_constraints>

<phase_requirements>
## Phase Requirements

공식 REQUIREMENTS.md 매핑 ID 없음 (TBD) — CONTEXT.md D-01~D-12 를 요구사항으로 삼는다.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-11/D-12 | 목표 각도 화살표를 기존 결함 줌 카드 위에 | fault_zoom.py 는 이미 PIL 로 각도 호(`_draw_leg_angle`)·마커(`_mark`)를 crop-px 공간에 그린다 — 화살표는 동일 렌더러 확장. deficits/direction 데이터는 DeductionRecord + JointScore.direction 에 이미 존재 |
| D-03/D-05 | 실루엣 이미지 자동 생성 (top-1 결함 프레임) | `_process` 사후 단계 패턴 = faultZoomStatus 선례 (Phase 27 SPD-04). DashScope 이미지 편집 모델 후보 확정 (§Standard Stack). 프레임 소스 = cached_user_frames + fault frame 선택 로직 기존 재사용 |
| D-04/D-10 | **[HISTORICAL — 구현 금지, amended D-10 = 2D 뷰어]** R3F 뷰어 + 목표 자세 반투명 중첩 | PoseViewer3D.tsx **이미 구현·배포됨** (three/@react-three/fiber/drei/expo-gl 설치 완료). referenceJoints prop 예약석 존재 — 활성화만 필요. reference/{id} Firestore 문서에 joints3d 존재 (Wave 5 top-level mirror, 11개 전부 phase4_v1) |
| D-06 | 회전 영상 온디맨드 + 완료 알림 | wan_gate_batch.py 의 create task→폴링→다운로드 패턴 재사용. 신규 HTTP Lambda(202 즉답) + 비동기 워커(SQS) 필요 — API GW HTTP API 30s 한도 (§Pitfalls 1). 완료 알림 = Firestore onSnapshot 카드 갱신 (push 인프라 없음·불필요) |
| D-07 | 일일 생성 한도 | Firestore 사용자 문서 counter (transaction). 권장 수치 §Open Questions |
| D-08 | 조용한 폴백 | faultZoomStatus='failed' → 카드 숨김 선례 그대로. 상태 필드 방출로 앱이 조용히 미표시 |
| D-09 | 참고코너 섹션 배치 | result.tsx 섹션 스택 구조 확인 — ScoreBreakdownSection(line ~1422) 아래 신규 섹션 삽입 지점 명확 |
| D-01 페어 적재 | [틀린 폼→고쳐진 폼] 플라이휠 | training/phase22/ S3 선례 + enumerate_internal.consent_allows 게이트 계약(2026-07-13 컷오프 이후 = learningOptIn===true 엄격) 재사용 |
| D-02 | VisualGenEngine 추상화 | interfaces.py Protocol 어댑터 선례 (FrameExtractor/PoseEstimator/CoachWriter) 그대로 |
</phase_requirements>

## Summary

이 phase 는 신규 기술 도입이 거의 없다. **핵심 발견: 필요한 인프라의 대부분이 이미 존재한다.**
(1) 1단 오버레이(D-11/12)는 backend `fault_zoom.py` PIL 렌더러의 확장이다 — 앱은 crop-px 좌표를 모르므로 화살표는 반드시 backend 가 PNG 에 그려야 한다(앱 SVG 오버레이 아님). (2) **[HISTORICAL — 구현 금지]** R3F 3D 뷰어(D-04/10)는 PoseViewer3D.tsx 로 이미 완성·배포되어 있고, 의존성 4종(three/R3F/drei/expo-gl)도 설치돼 있다 — 남은 것은 referenceMotions.ts 가 reference 문서의 joints3d 를 normalize 해 흘리고 예약석 referenceJoints prop 을 활성화하는 배선뿐이다. (3) 실루엣/회전영상의 Firestore 방출은 faultZoomStatus(pending→done/failed) 사후 부분 업데이트 선례를 그대로 복제한다.

외부 API 통합은 spike 008 이 이미 실측을 마쳤다: `wan2.7-videoedit` (dashscope-intl, 비동기 task, 건당 6~7분, ~$0.8, watermark:false, 모더레이션 영구차단 ~10%). 이미지 실루엣용 모델은 동일 endpoint 의 `wan2.7-image-pro` (1순위 — 검증된 Wan 계열, 동일 키/모더레이션 특성) 또는 `qwen-image-edit-plus`(폴백, 동기 API) — 정확한 파라미터·가격은 미실측이므로 **plan 의 첫 작업으로 1건 스모크 테스트**를 권장한다.

가장 중요한 아키텍처 결정: **실루엣 자동 생성(D-05)은 `_process` 사후 단계**(RunPod/Lambda 공용 코드 1벌, 점수 완료를 블록하지 않음), **회전 영상 온디맨드(D-06)는 신규 Lambda 워커**(Pod 무관 — 순수 HTTP, 기존 분석 문서에 대해 Pod 없이도 동작해야 함). API Gateway HTTP API 의 30초 통합 한도 때문에 온디맨드 요청 엔드포인트는 즉답(202)하고 실제 생성은 SQS 경유 워커가 수행한다.

**Primary recommendation:** 신규 패키지 0 으로 진행 — backend 는 stdlib urllib(스파이크 패턴), 앱은 **[HISTORICAL: "기설치 R3F 스택" 부분 구현 금지 — 31-08 은 react-native-svg 2D]** 기설치 R3F 스택. 계약 3면(analysis.ts + models.py + contract.md) 동시 수정 항목은 실루엣 필드·회전영상 상태·참고코너 데이터 3건.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 목표 각도 화살표 (D-11/12) | Backend ML 어댑터 (fault_zoom.py PIL) | — | crop-px keypoint 좌표는 backend 만 보유. 앱은 완성 PNG 소비 |
| 교정 실루엣 생성 (D-03/05) | Backend `_process` 사후 단계 (순수 HTTP) | Firestore 부분 업데이트 | 분석 완료 시 자동 = 파이프라인 후처리. 코드 1벌 원칙(Lambda/RunPod 공용) |
| 실루엣 품질 게이트 | Backend (Gemini 3.5-flash vision judge) | — | GPU 불필요·Pod OFF 에서도 동작하는 HTTP judge. RTMW 재추론 게이트는 Pod 의존이라 부적합 |
| 회전 영상 온디맨드 (D-06) | 신규 HTTP Lambda(요청 202) + SQS 워커 Lambda | Firestore 상태 머신 | 기존 분석 문서에 Pod 없이 동작 필수. 6~7분 > API GW 30s |
| **[HISTORICAL — 구현 금지]** R3F 3D 뷰어 (D-04/10) | App (PoseViewer3D 확장) | Firestore reference joints3d read | 이미 구현됨 — referenceJoints 활성화 + 반투명 중첩만 |
| 참고코너 섹션 (D-09) | App (result.tsx) | — | 점수 내역(ScoreBreakdownSection) 아래 신규 섹션 |
| 페어 적재 (플라이휠) | Backend (S3 `training/phase31/`) | Firestore learningOptIn read | phase22 training/ 레이아웃·동의 게이트 선례 |
| 일일 한도 (D-07) | Backend (Firestore counter) | — | 요청 Lambda 가 transaction 으로 검사·증가 |
| 계약 방출 | 3면 동시 (analysis.ts / models.py / contract.md) | — | 프로젝트 invariant |

## Standard Stack

### Core (전부 기존 — 신규 설치 0)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `three` | ^0.184.0 (설치됨) | 3D 스켈레톤 렌더 | Spike 005 VALIDATED, PoseViewer3D 운영 중 [VERIFIED: app/package.json] |
| `@react-three/fiber` | ^9.6.1 (설치됨) | RN 선언적 Three.js (`/native` 경로) | 동일 [VERIFIED: app/package.json] |
| `@react-three/drei` | ^10.7.7 (설치됨) | OrbitControls (native export 확인 완료) | 동일 [VERIFIED: app/package.json] |
| `expo-gl` | ~16.0.10 (설치됨) | GL 컨텍스트 | 동일 [VERIFIED: app/package.json] |
| `react-native-svg` | 15.12.1 (설치됨) | KeypointOverlay 등 기존 렌더 | 기존 [VERIFIED: app/package.json] |
| Pillow (PIL) | Lambda/Pod 기존 | 화살표·목표선 PNG 드로잉 | fault_zoom.py 가 이미 사용 [VERIFIED: codebase] |
| stdlib `urllib` | Python 3.12 내장 | DashScope HTTP 호출 | wan_gate_batch.py 실증 패턴 — `requests` 의존 회피 (프로젝트 관례) [VERIFIED: spike 008 코드] |
| `boto3` | Lambda 런타임 제공 | S3 put/presign, SSM read | 기존 [VERIFIED: codebase] |

### 외부 API 모델 (설치 아님 — 호출 대상)

| Model ID | Endpoint | Purpose | 실측/근거 |
|----------|----------|---------|-----------|
| `wan2.7-videoedit` | dashscope-intl.aliyuncs.com (비동기 task) | 회전 참고 영상 (D-06) | [VERIFIED: spike 008 — MAE 중앙 9.9°, 건당 6~7분·~$0.8, watermark:false, 영구차단 ~10%] |
| `wan2.7-image-pro` | dashscope-intl (국제 endpoint 등재 확인) | 교정 실루엣 이미지 1순위 (D-03) | [CITED: alibabacloud.com/help/en/model-studio/models — "Generate images and videos from text or images, with support for editing, reference"] 가격·지연·모더레이션 미실측 [ASSUMED] |
| `qwen-image-edit-plus` / `qwen-image-edit-max` | Model Studio (동기 API) | 실루엣 폴백 후보 | [CITED: alibabacloud.com/help/en/model-studio/qwen-image-edit-guide — 동기 호출, 입력 1~3장, 출력 URL 24h 유효, watermark optional·기본 off, 영어/중국어 프롬프트] 가격 ~$0.035/이미지(qwen-image-2.0 계열) [ASSUMED — 비공식 집계 출처] |
| `gemini-3.5-flash` | 기존 Gemini 통합 | 실루엣 품질 게이트 judge (얼굴/배경 왜곡·자세 타당성) | 기존 스택 (gemini_vision_scorer 선례). 메모리 [[gemini-latest-model-versions]] — 2.5 금지 [VERIFIED: codebase] |

**모델 선정 권고 (D-03 Claude's discretion):** 1순위 `wan2.7-image-pro` — spike 008 로 검증된 Wan2.7 계열과 동일 벤더/키/모더레이션 특성, D-02 의 "Wan2.7 확정" 과 계열 정합. 폴백 `qwen-image-edit-plus` (동기 API 라 파이프라인 통합이 더 단순). **plan 첫 태스크로 두 모델 각 1건 스모크**(정은지 fixture 프레임 → "correct the left knee to full extension" 류 프롬프트) 후 확정 — 미실측 파라미터를 계약에 굳히기 전 검증.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| wan2.7-image-pro | Gemini 이미지 생성 (nano-banana 계열) | 벤더 분산·SynthID 워터마크 강제 — Wan watermark:false 가 사용자 노출에 유리 |
| Lambda 워커 (D-06) | Step Functions | 파일럿 규모에 과설계. 900s Lambda + SQS 로 충분 (pipeline 선례) |
| Gemini judge 품질 게이트 | RTMW 재추론 기하 게이트 | GPU Pod 필수 — Pod OFF 상태에서 기능 마비. Gemini judge 는 HTTP 로 항상 동작. RTMW 게이트는 phase 22 동행 트랙(deferred)과 정합 |

**Installation:** 없음 (신규 패키지 0).

## Package Legitimacy Audit

이 phase 는 **신규 패키지를 설치하지 않는다.** 앱 R3F 스택 4종은 기설치·운영 중, backend 는 stdlib urllib + 기존 boto3/Pillow. slopcheck 실행 불필요.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[분석 완료 (_process, RunPod/Lambda 공용)]
   │  점수·faultZoom 기존 흐름 무접촉
   ├─→ (D-05 자동) 실루엣 사후 단계:
   │     top-1 결함 프레임(cached_user_frames) ─→ S3 임시 put + presign
   │       ─→ DashScope wan2.7-image-pro (VisualGenEngine 어댑터)
   │       ─→ Gemini 3.5-flash judge (얼굴/배경/자세 게이트)
   │       ├─ PASS → S3 results/{uid}/{aid}/silhouette_{joint}.png
   │       │         + Firestore 부분 업데이트 (silhouetteStatus='done')
   │       │         + (learningOptIn===true 만) S3 training/phase31/pairs/ 적재
   │       └─ FAIL/차단 → silhouetteStatus='failed' (조용한 폴백 D-08)
   │
[결과 화면 result.tsx]
   ├─ 결함 줌 카드 (기존) ←─ fault_zoom.py PIL 에 목표각 화살표+목표선 추가 (D-11/12)
   ├─ 점수 내역 (ScoreBreakdownSection)
   └─ "참고하세요" 섹션 (신규, D-09 — 비채점 시각 분리)
        ├─ 교정 실루엣 카드 (silhouetteStatus 구독, pending 자리표시/failed 숨김)
        ├─ [HISTORICAL] R3F 3D 뷰어 → 실제 구현 = 2D PoseCompareViewer (31-08)
        │     data: result.joints3d + reference doc joints3d (모두 Firestore 기존)
        └─ [회전 영상 생성] 버튼 (D-06)
              │ POST /visual/rotation (신규 Lambda: auth→한도검사→SQS→202)
              ▼
        [SQS visual-queue] → 워커 Lambda (timeout 900s):
              S3 presign → wan2.7-videoedit task 생성 → 15s 폴링(6~7분)
              → 24h URL 즉시 S3 다운로드 → Firestore rotationStatus='done'
              → 앱 onSnapshot 카드 갱신 (= "완료 알림", push 아님)
```

### Recommended Project Structure

```
backend/
├── functions/
│   ├── pipeline/app.py            # 실루엣 사후 단계 훅 추가 (_render_fault_zoom 선례)
│   ├── visual-request/app.py      # 신규: POST 요청 → 한도 검사 → SQS 발행 → 202
│   └── visual-worker/app.py       # 신규: SQS 소비 → Wan 영상 생성 → S3 → Firestore
├── shared/python/sunity_shared/
│   ├── analysis/fault_zoom.py     # 목표각 화살표/목표선 드로잉 함수 추가
│   ├── analysis/visual_gen.py     # 신규: VisualGenEngine Protocol + Wan/Qwen 어댑터 + judge 게이트
│   └── firestore_admin.py         # update_analysis_silhouette / update_analysis_rotation
app/src/
├── components/ReferenceCornerSection.tsx  # 신규: 참고코너 (실루엣 카드+뷰어+버튼)
├── components/PoseViewer3D.tsx            # referenceJoints 활성화 + 반투명 중첩
├── lib/referenceMotions.ts                # joints3d normalize 추가
└── app/analysis/result.tsx                # 섹션 삽입 (점수 내역 아래)
```

### Pattern 1: 사후 부분 업데이트 (faultZoomStatus 선례 — 그대로 복제)

**What:** 점수는 status='done' 에서 확정, 무거운 시각물은 이후 부분 업데이트로 도착. 상태 3값 'pending'|'done'|'failed', 부재=legacy 하위호환.
**When to use:** silhouetteStatus (D-05), rotationStatus (D-06).
**Example (기존 코드, 방출측):**

```python
# Source: backend/functions/pipeline/app.py _render_fault_zoom (Phase 27 SPD-04)
skey = f"results/{uid}/{analysis_id}/zoom_{c['joint']}.png"
_s3.put_object(Bucket=bucket, Key=skey, Body=c["png"], ContentType="image/png")
item = {"joint": c["joint"], "imageUrl": _signed_get(bucket, skey), "tier": tier}
# 호출측이 update_analysis_fault_zoom 로 사후 부착 — result mutation 금지
```

### Pattern 2: DashScope 비동기 task (spike 008 실증 — 워커 Lambda 이식)

```python
# Source: .planning/spikes/004-gemini-omni-view-editing/wan_gate_batch.py (2026-07-17 실측)
BASE = "https://dashscope-intl.aliyuncs.com"
CREATE = f"{BASE}/api/v1/services/aigc/video-generation/video-synthesis"
body = {
    "model": "wan2.7-videoedit",
    "input": {"prompt": PROMPT, "media": [{"type": "video", "url": presigned_url}]},
    "parameters": {"resolution": "720P", "watermark": False,
                   "prompt_extend": False, "seed": 42},
}
# 헤더: Authorization Bearer + X-DashScope-Async: enable
# 생성: task_id 즉답 → GET /api/v1/tasks/{task_id} 15s 폴링 → SUCCEEDED 시 video_url
# video_url 은 24h 유효 — 즉시 S3 다운로드 (spike 박제)
# journal 멱등: task_id 저장 → 크래시 시 재과금 없이 이어 폴링
```

### Pattern 3: Protocol 어댑터 (D-02 VisualGenEngine)

**What:** `typing.Protocol` 로 엔진 인터페이스 선언, 구체 어댑터(WanVideoEdit/WanImagePro)는 형제 모듈, lazy import.
**When to use:** visual_gen.py — GEN3C 재평가(deferred) 시 스왑 지점.
**근거:** `sunity_shared/analysis/interfaces.py` 의 FrameExtractor/PoseEstimator/CoachWriter 선례 [VERIFIED: codebase].

### Pattern 4: 학습 동의 게이트 (페어 적재)

```python
# Source: backend/training/datagen/enumerate_internal.py consent_allows (2026-07-13 belle 결정)
# · learningOptIn is False → 무조건 제외
# · learningOptIn is True  → 통과
# · 부재 → 컷오프(2026-07-13) 이후 신규 데이터는 strict 제외 (fail-safe = 미동의)
# Phase 31 페어는 전부 신규 생성물 → learningOptIn === True 엄격 필터만 사용
```

### Anti-Patterns to Avoid

- **화살표를 앱 SVG 로 그리기:** 결함 줌 카드는 backend 합성 PNG — 앱은 crop-px keypoint 좌표가 없다. UI 단 좌표 산출 금지(D-12 §12 안티패턴)와도 충돌. 화살표는 fault_zoom.py PIL 확장.
- **실루엣/회전 데이터를 채점 모듈에 유입:** dimensions/deduction_engine/kismam 에 생성물 유입 절대 금지 (invariant — 점수 반영 금지).
- **RunPod-delegate 경로에서 ML 어댑터 호출:** 기존 안티패턴 준수 — 회전 워커는 Pod 무관 Lambda 로 분리.
- **Firestore nested array:** 실루엣/회전 필드는 flat scalar 만 (`_validate_dict_only_scalars` 통과 형상).
- **모더레이션 차단 무한 재시도:** spike 실측 — 확률적 차단은 1회 재시도로 일부 회복, 결정적 차단(power-spin 2/2)은 재시도 무의미. 재시도 1회 상한 후 'failed' 확정.
- **다각도 촬영 유도 카피:** 참고코너 어디에도 "다른 각도로 찍어보세요" 류 노출 금지 (단일 카메라 UX invariant).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| **[HISTORICAL — 구현 금지]** 3D 뷰어/회전 제스처 | 자체 3D 수학·PanResponder 카메라 | 기존 PoseViewer3D (R3F+drei OrbitControls) | 이미 구현·UAT 통과. degenerate-depth 축 재매핑 등 함정 해소 완료 |
| 결함 프레임 선택 | 새 프레임 선택 로직 | fault_zoom.select_confident_frame + vision sourceFrameIndices 기존 경로 | crop 프레임과 vision 측정 프레임 정합 이슈 이미 해결됨 (quick-260702-sic) |
| DTW ref 프레임 대응 | 재계산 | fault_zoom._matched_ref_frame (dtw_match 재사용) | "DTW 재계산 금지" 기존 계약 |
| 이미지 품질 판정 | 자체 얼굴 검출/왜곡 측정 CV 코드 | Gemini 3.5-flash 구조화 judge | 기존 vision judge 인프라(structured JSON 파싱·재시도) 재사용. CV 자체 구현은 위양성 튜닝 수렁 |
| 사용 한도 | 자체 rate-limit 미들웨어 | Firestore transaction counter | 파일럿 규모. 인프라 추가 0 |
| S3 락/멱등 | 새 멱등 프레임워크 | task_id Firestore 저장 + 상태 머신 (journal 패턴 이식) | spike 008 실증 |

**Key insight:** 이 도메인의 실패 비용은 "생성 품질" 이 아니라 "신뢰 인상" 이다 (D-08). 기존에 검증된 조용한 폴백·사후 업데이트·어댑터 경계 패턴을 벗어난 자체 구현은 전부 신뢰 리스크를 늘린다.

## Common Pitfalls

### Pitfall 1: API Gateway HTTP API 30초 통합 한도
**What goes wrong:** 회전 영상(6~7분)을 요청 Lambda 에서 동기 처리하면 API GW 가 30s 에 504 를 던진다 (Lambda 는 백그라운드에서 계속 돌아 과금만 됨).
**Why it happens:** HTTP API 통합 타임아웃 상한 30s — Lambda timeout(900s)과 무관.
**How to avoid:** 요청 Lambda 는 검증+SQS 발행+202 즉답. 생성은 워커 Lambda(SQS 트리거, timeout 900s, VisibilityTimeout > 900 — AnalysisQueue 선례 960)가 수행.
**Warning signs:** plan 에 "요청 엔드포인트가 폴링까지 수행" 이 보이면 잘못된 설계.

### Pitfall 2: DashScope 산출 URL 24h 만료
**What goes wrong:** video_url/이미지 URL 을 Firestore 에 그대로 저장하면 24h 후 죽은 링크.
**How to avoid:** SUCCEEDED 즉시 S3 다운로드 → 자체 presign(7일, `_PLAYBACK_EXPIRES`) 방출. **S3 key 도 함께 저장** (myVideoKey 선례 — 7일 후 playback-url 재발급 경로 재사용 가능).
**Warning signs:** Firestore 에 `dashscope.aliyuncs.com` URL 이 저장되면 실패.

### Pitfall 3: 모더레이션 차단 (실측 ~10% 영구)
**What goes wrong:** 폴스포츠 복장 오탐으로 Alibaba Green net 이 차단 (spike: power-spin 2/2 결정적). 이미지 모델의 차단율은 미실측 — 영상보다 높을 수도 있음.
**How to avoid:** 재시도 1회 → 실패 시 status='failed' + 조용한 폴백 (D-08). 사용자 카피에 "차단/불가" 뉘앙스 금지 — 카드 자체를 숨김 (faultZoomStatus='failed' 선례).
**Warning signs:** 실패 상태에 에러 배너/토스트가 있으면 D-08 위반.

### Pitfall 4: Pod OFF 전제
**What goes wrong:** 실루엣 자동 생성을 "분석 파이프라인 안" 에 두는 것은 옳지만(신규 분석은 Pod 가 있어야만 발생), 회전 온디맨드를 Pod 에 의존시키면 기존 분석 문서에 대해 기능이 죽는다.
**How to avoid:** 회전 워커 = 순수 HTTP Lambda (GPU 0). RTMW 재추론류 품질 게이트 금지 (Gemini judge 로 대체). 실기기 E2E 검증 태스크는 Pod 재생성+SSM/Lambda env 재동기화가 선행 조건임을 plan 에 명시.
**Warning signs:** plan 태스크가 "RunPod 서버에 실루엣 엔드포인트 추가" 라면 재설계.

### Pitfall 5: 계약 3면 lockstep 누락
**What goes wrong:** analysis.ts 만 고치고 models.py/contract.md 를 빠뜨림 — normalize() 가 새 필드를 drop.
**How to avoid:** 신규 필드(silhouette*/rotation* 등) 마다 3면 동시 수정 + `firestore_admin` validator(flat scalar) + 앱 normalize 방어적 파싱. faultZoomStatus 방출부의 주석 스타일(lockstep 명시)을 그대로 따른다.

### Pitfall 6: D-10 목표 자세 데이터의 mode 격차
**What goes wrong:** 반투명 중첩의 "목표 자세" = reference joints3d 는 mode1 에서만 자명. mode3 는 reference 개념이 없다.
**How to avoid:** mode1 = referenceMotionId 의 joints3d. mode3 = recognizedMotionId(Phase 30 신설 필드) 있으면 그 reference 를 fetch, 없으면 **내 자세 단독 뷰어로 강등** (중첩 없이 — 조용한 강등). 시간 대응은 execPeakS/피크 프레임 1장 중첩이 v1 로 충분 (전 구간 DTW warp 동기화는 과설계 — deferred 성격).
**Warning signs:** mode3 첫 분석에서 중첩 뷰어가 빈 화면이면 강등 처리 누락.

### Pitfall 7: sam deploy 승인 게이트
**What goes wrong:** 신규 Lambda 2개+SQS+route 추가는 sam deploy 필요 — 현재 잔여 sam deploy 는 belle 승인 대기 상태(메모리).
**How to avoid:** plan 에 배포 태스크를 checkpoint(belle 승인)로 분리. `sam build --use-container` 필수 (Mac native binary 함정).

### Pitfall 8: 실루엣 프레임의 개인정보
**What goes wrong:** 사용자 프레임이 Alibaba 로 전송된다 (Gemini 전송과 동일 성격이나 신규 벤더).
**How to avoid:** 서비스 기능 수행 목적 전송은 D-01/D-05 결정에 내재하나, **학습 페어 적재는 별개** — learningOptIn===true 엄격 + PII 정책(원본측 프레임 포함 여부, 얼굴 블러 anonymize_batch 선례 적용 여부)을 plan 에서 명시. §Open Questions 참조.

## Code Examples

### 목표각 화살표 데이터 소스 (이미 존재 — 신규 산출 0)

```python
# DeductionRecord (models.py / contract.md §10) — 화살표에 필요한 전부:
#   criterion, measuredValue(현재 각), baselineValue(목표 각: 180/160/reference),
#   deviation, points, unit='deg'
# JointScore.direction ('extend'|'flex'|'raise'|'lower'|'open'|'close')
#   → 화살표 방향 어휘. fault_zoom 은 이미 deficits: dict[str, float] 를 받는다.
# 화살표 = 결함 관절 keypoint px 에서 direction 벡터로 목표선까지 PIL 드로잉
#   (_draw_leg_angle / _mark 의 crop-px 변환 헬퍼 _to_crop_px 재사용).
```

### Firestore 사후 업데이트 신규 함수 (선례 시그니처)

```python
# Source: firestore_admin.update_analysis_fault_zoom (line 1138) 선례
# 신규: update_analysis_silhouette(uid, analysis_id, status, item: dict | None)
#      update_analysis_rotation(uid, analysis_id, status, video_url=None, s3_key=None, task_id=None)
# flat scalar 만 — _validate_dict_only_scalars 통과 형상. 실패 시 status 만 'failed'.
```

### 앱 참고코너 상태 소비 (faultZoomStatus 선례)

```tsx
// Source: app/src/app/analysis/result.tsx lines 1056-1083 (Phase 27 D-06)
// 'pending' = 자리표시 + 타임아웃 가드 / 'done' = 카드 표시 / 'failed' = 숨김(조용).
// silhouetteStatus / rotationStatus 도 동일 3값 + 부재=legacy 판정 규칙 복제.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Gemini Omni 앵글 편집 (spike 004) | Wan2.7-VideoEdit 확정 | 2026-07-17 spike 008 | MAE 2.3배 우수·watermark off. Omni 는 SynthID 강제로 탈락 |
| GEN3C 오픈 트랙 | 부적격 판정 (중앙 41.1°, 이봉) | 2026-07-18 spike 007b | depth 개선 후 재평가 (deferred) — plan 은 어댑터 스왑 여지만 |
| "3D 뷰어는 후속" (spike 005 로드맵) | PoseViewer3D 배포 완료 | Phase 4 Wave 2 | D-04 기본 뷰어는 신규 개발이 아니라 확장 |
| 점수 완료 후 zoom 동기 렌더 | faultZoomStatus 사후 분리 | Phase 27 SPD-04 | 실루엣/회전도 동일 패턴 — 점수 지연 0 |

**Deprecated/outdated:**
- Higgsfield API·Veo 3.1 트랙: spike 체계에서 전부 탈락/대체 — 참조 금지.
- ReCamMaster(007a): 폐기 박제 — 오픈 트랙 검증은 GEN3C 로 일원화됐고 그마저 deferred.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `wan2.7-image-pro` 가 dashscope-intl 에서 이미지 편집(입력 이미지+지시) 모드를 지원하고 기존 키로 호출 가능 | Standard Stack | 스모크 태스크에서 즉시 판명 — 폴백 qwen-image-edit-plus 로 전환. plan 이 스모크를 첫 태스크로 두면 리스크 흡수 |
| A2 | 이미지 생성 비용 "수백원 내외"(~$0.035~0.4/장) 및 수초~수십초 지연 | Standard Stack | 비용 초과 시 D-07 한도 수치 조정으로 흡수 (아키텍처 불변) |
| A3 | 이미지 모델의 모더레이션 차단율이 영상(~10%)과 유사 | Pitfalls 3 | 더 높으면 실루엣 노출률 하락 — 조용한 폴백이라 UX 붕괴는 없음. 스모크+초기 관측으로 판정 |
| A4 | reference 문서 joints3d 가 11개 모션 전부 존재 (Wave 5 + [[reference-library-phase4-all11]]) | D-10 | 일부 부재 시 해당 모션은 중첩 강등 (Pitfall 6 경로가 이미 강등 처리) |
| A5 | Gemini 3.5-flash judge 가 얼굴/배경 왜곡을 실용 수준으로 판정 | 품질 게이트 | 판정력이 부족하면 게이트 기준 완화 + 페어 적재만 보수적으로 (사용자 노출과 적재 게이트 분리 가능) |

## Open Questions (RESOLVED)

1. **일일 한도 수치 (D-07 재량)**
   - What we know: 실루엣 자동 = 분석당 1장 (분석 자체가 한도 역할). 회전 영상 ~$0.8/건·6~7분.
   - Recommendation: 회전 영상 사용자당 3건/일, 실루엣은 분석당 1 자동(별도 한도 불필요) + 전역 안전핀(일 총 생성 30건, env 조정 가능). 파일럿 규모에서 사실상 무제한.
   - **RESOLVED:** 31-07 채택 — 회전 영상 사용자당 3건/일 + 전역 안전핀 30건/일 (env 조정 가능).
2. **페어 적재 시 원본측 프레임의 얼굴 블러 여부**
   - What we know: anonymize_batch.py (얼굴 블러) 선례 존재, LICENSE-AUDIT 는 anonymize 강제를 내부 데이터에 적용.
   - What's unclear: learningOptIn=true 신규 페어에도 블러 강제인지 (블러하면 생성 헤드 학습 품질에 영향 가능).
   - Recommendation: v1 은 블러 없이 적재하되 S3 `training/phase31/pairs/` 접근을 학습 파이프라인으로 한정 + manifest 에 consent provenance 기록. plan 의 checkpoint:decision 으로 belle 확인.
   - **RESOLVED:** 31-06/T1 checkpoint:decision 으로 belle 게이트 (블러 여부는 그 게이트에서 확정).
3. **실루엣 카드의 위치 — 참고코너 안 vs 결함 줌 캐러셀 안**
   - What we know: D-09 는 참고코너를 정의하지만 실루엣이 "참고코너 소속" 인지 명시가 없다. 실루엣은 결함 교정물이라 줌 카드 옆이 동선상 자연스럽고, 점수 비반영 원칙상 참고코너도 논리적.
   - Recommendation: 참고코너 배치 (비채점 시각물 일관 원칙). UI 목업 선제시([[ux-propose-user-centric-screens-first]]) 때 belle 확인.
   - **RESOLVED:** 31-05/T1 checkpoint:decision 으로 belle 게이트 (목업 선제시 때 위치 확정).
4. **회전 영상의 입력 = 원본 전체 vs 트림 클립**
   - What we know: spike 는 8초 트림 사용. 비용/지연은 길이 비례(usage duration 16/클립).
   - Recommendation: 분석 구간(execStartS~landEndS 또는 앞 8초) 트림 후 전송 — ffmpeg 는 Lambda 에 없음 → **imageio-ffmpeg 바이너리 동봉 or 트림 없이 원본 전송** 중 택1. 원본 전송이 단순(파일럿 영상은 짧음) — 워커에 ffmpeg 의존 추가는 피하는 쪽 권장.
   - **RESOLVED:** 31-07/T2 원본 전송 채택 (ffmpeg 의존 없음 — 파일럿 영상 길이 짧음).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| DashScope 키 (SSM `/sunity/motion/dashscope-api-key`) | Wan 호출 | ✓ (spike 008/007b 실사용) | SecureString | — |
| Gemini 키 (SSM) | 품질 judge | ✓ (운영 중) | — | judge 생략 시 게이트 통과 보수화 |
| RunPod GPU Pod | 신규 분석 (실루엣 자동생성의 전제) | ✗ (전부 OFF — 의도적) | — | 코드/배선은 Pod 무관 진행, E2E 는 Pod 재생성 후 |
| AWS SAM CLI + Docker | 신규 Lambda 배포 | ✓ (기존 워크플로) | — | 배포는 belle 승인 checkpoint |
| **[HISTORICAL — phase 31 미사용]** R3F 스택 (three/fiber/drei/expo-gl) | D-04/10 | ✓ 설치·운영 | ^0.184/^9.6.1/^10.7.7/~16.0.10 | — |
| ffmpeg (Lambda 워커) | 영상 트림(선택) | ✗ (Lambda 기본 없음) | — | 트림 없이 원본 전송 (권장) |
| S3 버킷 `sunity-motion-pilot-videos` | 산출물/페어 저장 | ✓ | — | — |

**Missing dependencies with no fallback:** 없음 (Pod 는 E2E 검증만 지연시키고 구현은 막지 않음).
**Missing dependencies with fallback:** ffmpeg → 원본 전송, Pod → 코드 우선/E2E 후행.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (backend) / tsc --noEmit (app) |
| Config file | backend/requirements-dev.txt (pytest 설정 파일 없음 — 디렉터리 관례) |
| Quick run command | `python -m pytest backend/tests/<file>.py -x` |
| Full suite command | `python -m pytest backend/tests` + `cd app && npm run typecheck` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-11/12 | 화살표 드로잉 순수 함수 (좌표 변환·방향 벡터) | unit | `python -m pytest backend/tests/test_fault_zoom*.py -x` | 기존 파일 확장 (fault_zoom 테스트 존재) |
| D-02 | VisualGenEngine 어댑터 (HTTP mock, journal 멱등, 24h URL→S3 이관) | unit | `python -m pytest backend/tests/phase31/test_visual_gen.py -x` | ❌ Wave 0 |
| D-05/08 | silhouetteStatus 상태 머신 (pending→done/failed, 조용한 폴백, validator flat) | unit | `python -m pytest backend/tests/phase31/test_silhouette_flow.py -x` | ❌ Wave 0 |
| D-06/07 | 요청 Lambda (auth·한도 transaction·202) + 워커 dispatch | unit | `python -m pytest backend/tests/phase31/test_visual_request.py -x` | ❌ Wave 0 |
| 페어 적재 | learningOptIn===true 엄격 게이트 (false/부재 제외) | unit | `python -m pytest backend/tests/phase31/test_pair_store.py -x` | ❌ Wave 0 |
| D-04/09/10 | 앱 계약 normalize + 섹션 렌더 타입 | typecheck | `cd app && npm run typecheck` | ✅ |
| 실기기 UX (D-09/10 중첩·회전 카드) | manual-only — 실기기 렌더/제스처는 자동화 불가. HUMAN-UAT.md 적립([[batch-uat-after-phase-31]]) | manual | — | — |

### Sampling Rate
- **Per task commit:** 해당 테스트 파일 `-x` 단건
- **Per wave merge:** `python -m pytest backend/tests` (+ app typecheck, 앱 wave 시)
- **Phase gate:** 전체 backend suite green + typecheck green

### Wave 0 Gaps
- [ ] `backend/tests/phase31/` 디렉터리 + 상기 4개 테스트 파일 (phase22/ 디렉터리 선례)
- [ ] DashScope HTTP mock fixture (urllib 레벨 monkeypatch — 스파이크 코드가 순수 stdlib 라 mock 용이)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | 신규 엔드포인트도 Firebase ID token 검증 (`sunity_shared.auth` 기존 경로, AuthError→401) |
| V3 Session Management | no (토큰 per-request) | — |
| V4 Access Control | yes | uid 스코프 강제 — 요청자는 자기 analysisId 만 (Firestore users/{uid} 격리 + Lambda 측 uid==doc owner 검증) |
| V5 Input Validation | yes | 기존 ValidationError 패턴 (analysisId 형식, 모드, 한도). SQS 메시지도 파싱 방어적 |
| V6 Cryptography | yes | 키는 SSM SecureString 만 (`/sunity/motion/dashscope-api-key`), 하드코딩·로그 노출 금지 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| presigned URL 과다 노출 (사용자 영상이 외부 벤더로) | Information Disclosure | presign TTL 최소화 (생성용은 24h 아닌 1h 수준으로 별도 발급 가능), S3 key 는 `_eval-tmp` 아닌 전용 prefix |
| 온디맨드 엔드포인트 남용 (과금 공격) | DoS/과금 | D-07 Firestore transaction 한도 + 전역 안전핀 + 요청당 분석 문서 존재·소유 검증 |
| 생성물 URL 위조/타 사용자 접근 | Tampering | 산출물은 `results/{uid}/{analysisId}/` 하위 — 기존 zoom 과 동일 경계. Firestore rules 는 이미 uid 격리 |
| 페어 적재 동의 우회 | Privacy | consent_allows 단위 테스트 고정 (false 무조건 제외 선례), 적재 코드에 strict True 검사 |
| DashScope 응답 신뢰 | Injection | 응답 JSON 방어적 파싱 (spike 패턴), video_url 도메인 화이트리스트 후 다운로드 |

## Project Constraints (from CLAUDE.md)

- 기술 스택 변경 금지 (Expo+RN TS / Lambda Python+SAM / Firestore / S3) — 신규 프레임워크 도입 없음 확인.
- Motion AI 는 별도 Lambda+S3 — 신규 Lambda 도 `sunity-motion-pilot` 스택 내.
- 시크릿 = Parameter Store, `.env` 하드코딩 금지.
- 브랜드 #FF4B33 변경 금지, Pretendard, 라이트 전용, theme 토큰만 (하드코딩 금지). UI 는 Figma 우선(fileKey jrdI7kp245HkPfLB0nclsz).
- 이모지 금지, 작은 단위 작업, 의미있는 테스트만, 사용자 카피 한국어.
- GSD 워크플로 경유 (직접 편집 금지), 작업 완료 시 plan.md 갱신.
- 계약 3면(analysis.ts/models.py/contract.md) 동시 수정.
- 서브에이전트 Bash read-only 우회 주의 — 리뷰/검증 에이전트 파일 변형 차단 명시.

## Sources

### Primary (HIGH confidence)
- `.planning/spikes/004-gemini-omni-view-editing/README.md` + `wan_gate_batch.py` — Wan2.7 실측 (2026-07-17/18): API 형상·비용·지연·차단율·멱등 패턴
- 코드베이스 직접 확인: `fault_zoom.py`, `pipeline/app.py` (`_render_fault_zoom`, `_signed_get`, `_PLAYBACK_EXPIRES`), `firestore_admin.update_analysis_fault_zoom`, `KeypointOverlay.tsx`, `PoseViewer3D.tsx`, `analysis.ts`, `result.tsx`, `template.yaml`, `enumerate_internal.py`, `app/package.json`
- `.planning/spikes/005-frontend-3d-viewer/README.md` — R3F 아키텍처·라이선스
- `.planning/phases/31-api-visual-correction/31-CONTEXT.md` + `31-DISCUSSION-LOG.md`

### Secondary (MEDIUM confidence)
- [Alibaba Cloud Model Studio — Qwen-Image-Edit guide](https://www.alibabacloud.com/help/en/model-studio/qwen-image-edit-guide) — 모델 ID 군, 동기 API, 24h URL, watermark 기본 off
- [Alibaba Cloud Model Studio — Supported Models](https://www.alibabacloud.com/help/en/model-studio/models) — `wan2.7-image-pro` 국제 endpoint 등재

### Tertiary (LOW confidence — 검증 필요)
- 이미지 생성 가격 집계(비공식 블로그, ~$0.035/장 qwen-image-2.0 계열) — 스모크 usage 실측으로 대체할 것

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 신규 패키지 0, 전부 코드베이스/스파이크 검증
- Architecture: HIGH — faultZoomStatus/SQS/어댑터 선례가 전부 운영 코드에 존재
- 이미지 모델 세부(가격·지연·차단율): MEDIUM~LOW — 스모크 태스크로 plan 초반 해소 (A1~A3)
- Pitfalls: HIGH — 대부분 프로젝트 실측 박제에서 도출

**Research date:** 2026-07-19
**Valid until:** 2026-08-19 (안정 영역) / DashScope 모델 라인업은 ~2주 (fast-moving — 스모크 시점 재확인)
