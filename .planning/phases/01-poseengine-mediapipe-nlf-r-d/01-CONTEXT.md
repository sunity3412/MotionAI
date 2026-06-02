# Phase 1: PoseEngine 추상화 + MediaPipe 어댑터 + 폴 축 정렬 + NLF R&D 격리 - Context

**Gathered:** 2026-05-31
**Updated:** 2026-06-02 — RTMW free-stack pivot 박제 (D-17~D-25 추가, D-01~D-08 일부 supersede)
**Status:** Ready for planning (RTMW pivot 반영 — 신규 plan 작성용 컨텍스트)

> **2026-06-02 Pivot 요약 (belle 결정):** v1 운영 백본을 **MediaPipe + MotionBERT** 에서 **RTMW 133 wholebody (Apache-2.0) 단일 백본** 으로 전환. 3D 는 RTMW3D / monocular 리프팅 (단일 카메라) + Pose2Sim (멀티 카메라). 체형 정규화는 SMPL-X 없이 세그먼트 길이 비율. NLF/SMPL-X 의존 영구 제거 (매출 검증 후 옵션 업그레이드로 deferred). **PoseEngine 인터페이스 추상화 필수** — 다운스트림 분석 레이어 무수정 박제 위해. 자세 사항은 `<decisions>` D-17 ~ D-25.
>
> **Plan 영향:** Plan 18 (multi-engine averaging spike) = **on hold** (abandoned 아님 — RTMW pivot 후 averaging target 두 path 자체가 메인 백본에서 빠짐, 의미 재평가 대상). Plan 04/05 (NLF R&D 격리 + atomic swap) 는 RTMW 구현체로 대상 변경 후 진행.
>
> **출처:** `/Users/kimtaesung/Downloads/Sunity_v1_개발지시_RTMW무료스택.md` + memory `rtmw-free-stack-pivot`, `plan-18-on-hold-rtmw-pivot`, `lifter-mp-motionbert-decision` (재평가 박제).

<domain>
## Phase Boundary

상용 제품 코드의 포즈 엔진을 **NLF → RTMW 133 wholebody (Apache-2.0)** 로 마이그레이션하고, `PoseEngine` 인터페이스 + 공통 계약(`PoseFrame`, `BodyNormalizationProfile`)을 도입한다. NLF/SMPL-X 는 R&D 비교군 어댑터로 격리(제품 import 경로에서 완전 제거). 동시에 폴 축 자동 검출 + 기준 좌표계 정렬을 RTMW 위에서 산출한다 — 모든 다운스트림 분석의 기반.

> **2026-06-02 pivot:** 원래 boundary 는 NLF→**MediaPipe** 마이그레이션이었으나, belle 결정으로 **MediaPipe + MotionBERT → RTMW** 로 재pivot. MediaPipe 코드 (Plan 02·03 결과물) 는 운영 경로에서 제거되거나 R&D 측 격리. 자세 사항 D-17~D-25.

**In scope:**
- `PoseEngine` 인터페이스 정의 + `PoseFrame` 공통 계약 (TS/Python lockstep)
- `MediaPipePoseEngine` 어댑터 구현 (제품 코드 경로)
- `NlfPoseEngine` 어댑터 격리 (R&D 비교군 전용, 제품 import 경로에서 제거)
- 폴 축 자동 검출 + 기준 좌표계 정렬
- 회귀 검증 (MediaPipe vs NLF 정확도 갭 측정 + 통과 기준)
- 기존 NLF 호출 제품 코드(`pipeline/app.py`, `runpod_inference/server.py`, `extract_reference_angles.py`, `verify_*.py`)의 atomic swap

**Out of scope (다른 phase 또는 deferred):**
- BodyNormalizationProfile 자동 측정 → Phase 2
- 자가입력 BodyProfileInput → Phase 3
- 다중 시점 촬영 UX → Phase 4
- Gemini 기술 인식기 → Phase 5
- RunPod GPU pod 처분 결정 → deferred
- 기존 Firestore 분석 결과/기준 모션 본자이션 → deferred
- pose_landmarker_heavy.task 배포 위치(Lambda 레이어 vs S3) → 플래너 판단

</domain>

<decisions>
## Implementation Decisions

### MediaPipe Variant 선택
- **D-01:** Variant = **BlazePose Heavy** (Tasks API). 폴 가림·접힌 자세에 최고 정확도 — 서버 inference라 속도(200~400ms/frame) 부담 적음
- **D-02:** API = **MediaPipe Tasks API** (PoseLandmarker, .task 모델 파일). Solutions(legacy) 비사용 — deprecated 예고됨
- **D-03:** 좌표 = **world landmarks(metric 3D)** 기본 분석용 + image landmarks도 함께 출력(UI 오버레이용). PoseFrame에 keypoints3D(world) + keypoints2D(image) 둘 다 저장
- **D-04:** 스키마 = **원본 저장은 MediaPipe 33 전체** (절대 17로 떨궈 저장 X). 스코어링/분석 계약은 **COCO-17 + 폴 확장(toe·heel·grip)** 유지. 어댑터 `MediaPipe33ToCOCO17Adapter`(+ 폴 확장 추출)로 변환. 엔진 교체 시 `SMPLXToCOCO17Adapter`로 swap. 폴 확장 landmark는 별도 feature set + confidence 게이트(가림 대응). 기존 `skeleton.py` / `JOINT_ANGLES` / `KEYPOINT_NAMES` / `features` / `temporal` 그대로 재사용.
- **D-05:** Confidence 변환 정책 (정책 수준 결정 — 모든 다운스트림이 따름):
  - 변환식: 둘 다 있으면 `confidence = visibility × presence`, `uncertainty_proxy = 1 - confidence`. visibility만 있으면 `confidence = visibility`.
  - 저장 필드: `raw_visibility`, `raw_presence`, `confidence`, `uncertainty_proxy` 모두 별도 저장
  - 사용처: keypoint 신뢰도 체크, 저신뢰 프레임 필터링, 각도 유효성 체크, temporal 스무딩, short-gap 보간, 리포트 신뢰도 경고
  - 규칙: 저신뢰 키포인트는 정확하다고 가정 금지. 각도에 필요한 키포인트가 저신뢰이면 그 각도 "low reliability" 마킹. 저신뢰 프레임 비율 높은 구간은 과분석 금지
  - 고객 리포트 정책: visibility·presence·uncertainty·landmark confidence·MediaPipe·COCO-17·NLF 등 기술 용어 노출 금지. 예: "이 구간은 무릎 위치가 영상에서 명확하게 보이지 않아, 세부 각도보다는 전체 중심축 흐름을 중심으로 분석했습니다."
  - 향후 호환: NLF 통합 시 동일 confidence/uncertainty 인터페이스로 매핑 (feature pipeline 재설계 금지)

### NLF R&D 격리 방식
- **D-06:** NLF 위치 = **`backend/research/pose_engines/nlf/`** (제품 패키지 `sunity_shared` 밖으로 완전 분리). 평가 스크립트 = `backend/research/evaluations/`
- **D-07:** Import 차단 = **물리 경로 분리만** (lint rule·import-linter 도입 안 함). `backend/research/`는 `sunity_shared`와 별개 경로라 자연스럽게 import 불가. Lambda 레이어(`/opt/python`)에도 미포함 — 배포 패키지에 NLF/torch/ultralytics 부재
- **D-08:** swap 전략 = **MediaPipe 구현 완성 + 회귀 검증 통과 후 atomic swap**. 중간 상태 없음. config 플래그 점진 롤아웃 안 함

### 폴 축 검출 방법
- **D-09:** 검출 = **Hough Line Transform + 수직 prior 자동**. OpenCV 전통 CV. 수직에 가까운 긴 직선 탐지. UX 마찰 0
- **D-10:** 시간 안정 = **영상 전체 평균 축 1개** 산출 (confidence 가중평균). 일반 폴(고정)은 영상 내 이동 없음 가정. 스피닝 폴은 v1.5
- **D-11:** 검출 실패 폴백 = **수직 가정 + confidence='low' 표기**. 분석은 진행하되 결과 화면에 "카메라 기울어져 세부 각도 해석에 주의" 안내 (사용자 친화 카피)
- **D-12:** 좌표 저장 = **raw + pole-aligned 둘 다** PoseFrame에 저장 (`keypoints3D`, `keypoints3DPoleAligned`). 분석은 aligned, 디버그/렌더링은 raw. PoleAxis도 메타로 저장

### MediaPipe vs NLF 회귀 검증 기준
- **D-13:** 검증 세트 = **정은지 영상 5개로 빠른 시작**. 다양성 25개 세트(다양한 경력/체형 10 + 고의 평이 5 + 정은지 10)는 데이터 확보에 시간 소요 → belle에게 지속 요청해 인지 유지
- **D-14:** 점수 갭 허용 = **±5점 이내** (overall 100점 만점). 결정·리포트 톤은 변하지 않을 수준
- **D-15:** 추가 검증 지표 4개:
  1. 고수 위양성 없음 — 정은지 영상이 ≥70점 (SCORE-04 직결, 41점 같은 위양성 절대 재발 금지)
  2. Top-3 실패 원인 일치 — 두 엔진이 도출한 Top-3 원인 중 ≥2/3 겹침
  3. 키포인트 confidence 분포 — 정상 영상에서 MediaPipe 평균 confidence 임계값 이상
  4. 추론 속도 — 프레임당 ms. MediaPipe Heavy가 Lambda CPU에서 일정 안에 도는지 확인
- **D-16:** 검증 실패 시 = **Phase 1 종료 보류, 원인 분석 후 재시도**. Hough·keypoint 매핑·confidence 계산 튜닝 재시도. swap 안 됐으니 제품 회귀 없음. 시간 소요 허용

### RTMW Pivot (2026-06-02 belle 결정 — D-01~D-08 일부 supersede)

- **D-17 [supersedes D-01/D-02/D-03]:** 운영 백본 = **rtmlib RTMW 133 키포인트 wholebody (Apache-2.0)**. MediaPipe BlazePose Heavy 는 운영 백본에서 제외 (R&D 비교군 또는 폐기 — 플래너 판단). RTMW Tasks API / Solutions 비교는 무의미 (RTMW 는 mmpose/rtmlib 직접 호출).
- **D-18:** 3D 산출 = **단일 카메라는 RTMW3D 또는 monocular 리프팅** (RTMW + MotionBERT 류), **멀티 카메라는 Pose2Sim** (스포츠 특화 무료). 단일 카메라 우선, 다각도는 occlusion/측정오류 해결 시 자동 제외 ([[single-camera-first-multi-view-last]] 정책 그대로 적용).
- **D-19:** 체형 정규화 = **SMPL-X 없이 세그먼트 길이 비율**. 파라미터형 메시 없음. Phase 2 (`BodyNormalizationProfile`) 는 RTMW 세그먼트 기반으로 재정의 — SMPL-X β 의존 제거.
- **D-20 [supersedes D-04]:** 원본 저장 = **RTMW 133 풀 키포인트**. COCO-17 으로 떨궈 저장 X. 스코어링/분석 계약은 **COCO-17 + 폴 확장(toe·heel·grip)** 유지 (다운스트림 무수정). 어댑터 `RTMW133ToCOCO17Adapter` (+폴 확장 추출) — `MediaPipe33ToCOCO17Adapter` 는 사용 안 함 (작성 안 함 또는 R&D 측 격리).
- **D-21:** 엔진 선택 config 플래그 `POSE_ENGINE = RTMW | NLF_SMPLX`. `NLF_SMPLX` 는 R&D 비공개 평가 전용. 기본값 = `RTMW`. `PoseFrame.bodyShape` 필드 nullable (RTMW = null, NLF_SMPLX = β 채움).
- **D-22 [supersedes D-05 보완]:** Confidence 변환 정책은 RTMW 의 키포인트 score(0~1) 로 매핑 — `confidence = rtmw_score`, `uncertainty_proxy = 1 - confidence`. visibility/presence 두 필드 가정 제거 (RTMW 단일 score). 기존 D-05 의 사용처·규칙·고객 리포트 정책·NLF 통합 시 동일 인터페이스 매핑은 그대로 유지.
- **D-23 [supersedes D-06/D-07]:** **NLF 위치 = `backend/research/pose_engines/nlf/`** 유지 (제품 패키지 `sunity_shared` 밖). **새로 RTMW 도 동일 패턴으로 격리 X** — RTMW 는 제품 운영 백본이라 `sunity_shared/analysis/pose_engines/rtmw/` 로 들어옴. 기존 `pose_engines/` 디렉터리 신설 가능 (계획 수립 시 플래너 판단). MediaPipe 코드 (Plan 02·03 결과물) 는 폐기 또는 R&D 격리 — 운영 import 경로에서 제거.
- **D-24:** **PoseEngine 인터페이스 추상화 필수** — `PoseEngine` Protocol + `PoseFrame` 공통 계약 + `BodyNormalizationProfile` 공통 입력. 모든 다운스트림 분석 레이어(`features`/`temporal`/`motiondtw`/`kismam`/`dimensions`/`assemble`/`technique`)는 **인터페이스에만 의존**. RTMW→NLF→SMPL-X 도입 시 **구현체만 교체**, 다운스트림 재작성 금지. belle 명시: "대량 코딩 전 모듈 구조 / PoseEngine 인터페이스 / 공통 타입 먼저 제안 + 질문 단계" — 인터페이스 합의 전에 RTMW 코드 직진 금지.
- **D-25:** **라이선스 위생** — RTMW 코드 자체는 Apache-2.0 이지만 **모델 가중치별 학습 데이터 상업 사용 가능 여부 확인 필수** (일부 wholebody 가중치 데이터셋 제약 가능). 고객 대면/상업 배포 전 가중치 라이선스 확정 + 박제. [[license-blocklist-pose]] 유효 (RTMPose OK 박제 그대로).

**Supersede 정리:**
- D-01/D-02/D-03 (MediaPipe variant·API·world landmarks 선택) → D-17 로 대체. MediaPipe 운영 도입 안 함.
- D-04 (MediaPipe 33 원본 저장) → D-20 (RTMW 133 원본 저장) 으로 대체.
- D-05 (Confidence 변환식) → D-22 (RTMW 단일 score 로 매핑) 로 변환식 수정. 사용처·정책은 유지.
- D-06/D-07 (NLF 격리 위치·import 차단) → D-23 (RTMW 운영 경로 신설 + MediaPipe 폐기 또는 R&D 격리) 로 확장.
- D-08 (atomic swap) → 대상 변경 (NLF → RTMW). swap 전략 자체는 유지. Plan 04/05 가 atomic swap 수행.

**유효 유지 (변경 없음):**
- D-09/D-10/D-11/D-12 (폴 축 검출·시간 안정·폴백·좌표 저장) — RTMW 위에서도 동일 적용.
- D-13/D-14/D-15/D-16 (회귀 검증 영상 5개·점수 갭·추가 지표·실패 대응) — 비교 대상이 RTMW vs NLF 로 변경. NotebookLM lookup 기준 + IPSF GeometricCriterion baseline (Plan 12 verdict 박제) 그대로.

### Claude's Discretion
- 폴 확장 landmark(toe/heel/grip)의 정확한 MediaPipe 33 인덱스 매핑 — 플래너가 MediaPipe 문서 참고해 확정
- `PoseEngine` 인터페이스 메서드 시그니처 세부 (estimate 반환 타입, 에러 매핑 등)
- `MediaPipe33ToCOCO17Adapter` / `SMPLXToCOCO17Adapter` 모듈 위치 (`sunity_shared/analysis/adapters/` 추천)
- Hough Line Transform 파라미터(rho, theta, threshold, minLineLength, maxLineGap) 초기값
- 회귀 검증 보고서 출력 포맷 (JSON + Markdown 요약 추천)
- 모델 파일 `pose_landmarker_heavy.task` 배포 위치 (Lambda 레이어 vs S3 다운로드)
- 에러 매핑 — MediaPipe 실패 시 기존 `NoHumanError` 재사용 여부

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 시스템 아키텍처·결정 (필수)
- `.planning/ROADMAP.md` — Overview 섹션의 belle 결정 7건 + Phase 1·2 상세 (RTMW pivot 반영 갱신 진행)
- `/Users/kimtaesung/Downloads/Sunity_v1_개발지시_RTMW무료스택.md` — **2026-06-02 belle pivot 지시문 (필독)**. RTMW 무료 스택 채택 이유·범위·인터페이스 요구사항. 다른 ROADMAP/CONTEXT 문구와 충돌 시 이 문서 우선.
- `.planning/REQUIREMENTS.md` — POSE-01, POSE-02, POSE-03, BODY-01, COACH-01 등 v1 18개. belle 결정 박스 (라이선스·모드·UX)
- `.planning/STATE.md` — current decisions 9건, blockers (Phase 1 마이그레이션 HIGH)
- `.planning/PROJECT.md` — Core value (분석 정확도), 폴스포츠 도메인 컨텍스트

### Research 문서 (시스템 아키텍처 기반)
- `docs/research/00_시스템_아키텍처_FINAL.md` — 마스터 아키텍처, 두 모드 분기, 컴포넌트 책임, AI vs 코치 경계
- `docs/research/01_체형차이_보정엔진_FINAL.md` §0.7 — 포즈 엔진 선택 & 라이선스/리스크. §4.3 (PoseFrame 스키마), §5.2 (BodyNormalizationProfile)
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §0.7 — occlusion 리스크, 다중 시점 권장
- `docs/research/폴스포츠-지식.md` — 도메인 지식 (동작군·관절·기술)

### 코드 컨텍스트 (현 상태)
- `backend/shared/python/sunity_shared/analysis/interfaces.py` — `PoseEstimator` Protocol (이미 존재, 확장 대상)
- `backend/shared/python/sunity_shared/analysis/pose_estimator.py` — `NlfPoseEstimator` (R&D 격리 대상). COCO-17 ↔ SMPL 매핑 로직 참고
- `backend/shared/python/sunity_shared/analysis/skeleton.py` — `KEYPOINT_NAMES`, `JOINT_ANGLES`, `JOINT_KEYS` (재사용)
- `backend/shared/python/sunity_shared/analysis/temporal.py` — confidence 기반 시간 보간 (재사용)
- `backend/shared/python/sunity_shared/analysis/features.py` — uncertainty 사용처 (재사용)
- `backend/functions/pipeline/app.py:131` — NLF 직접 import (swap 대상)
- `backend/runpod_inference/server.py` — RunPod GPU 추론 (swap 후 처분 검토 → deferred)
- `backend/scripts/extract_reference_angles.py`, `backend/scripts/verify_nlf_pipeline.py`, `backend/scripts/verify_self_comparison.py` — 기존 NLF 호출 스크립트 (R&D 측 이동 또는 MediaPipe 버전 작성)
- `app/src/types/analysis.ts` — TS 데이터 계약 (PoseFrame lockstep 갱신 필요)
- `backend/shared/python/sunity_shared/models.py` — Python 데이터 계약 (PoseFrame lockstep 갱신 필요)

### 라이선스
- https://is.mpg.de/ps/code — NLF/SMPL-X 입수처 (PS:License 1.0 비상업)
- https://smpl-x.is.tue.mpg.de — SMPL-X 공식
- `info@max-planck-innovation.de` — 향후 NLF/SMPL-X 상업 라이선스 한 채널 (belle 평행 진행)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PoseEstimator` Protocol** (`interfaces.py:26`): 이미 정의됨. `MediaPipePoseEngine`은 이걸 확장한 `PoseEngine` 인터페이스로 구현 (또는 그대로 사용 + PoseFrame 반환 타입 추가)
- **`skeleton.py`** (`KEYPOINT_NAMES`, `JOINT_ANGLES`, `JOINT_KEYS`): COCO-17 유지 결정으로 그대로 재사용. 다운스트림 모든 코드 영향 없음
- **`temporal.py`**: NLF uncertainty 기반 보간 로직. MediaPipe `uncertainty_proxy = 1 - confidence` 변환으로 그대로 사용 가능
- **`_fill_missing_boxes` 로직** (`pose_estimator.py:56`): 시간적 보완 패턴 — MediaPipe 어댑터에도 유사 적용 가능
- **lazy import 패턴** (`pose_estimator.py:78`): 무거운 import(`torch`, `ultralytics`)를 `__init__`에서 지연 로드. MediaPipe도 `import mediapipe`를 lazy로

### Established Patterns
- **Protocol 기반 어댑터** (`interfaces.py`): `FrameExtractor` / `PoseEstimator` / `CoachWriter` 모두 Protocol + 구현. PoseEngine도 동일 패턴
- **Lambda 레이어 분리** (`sunity_shared` → `/opt/python`): 무거운 모델은 함수별 requirements.txt. MediaPipe도 같은 방식
- **GPU 자동 감지** (`pose_estimator.py:83`): `torch.cuda.is_available()`. MediaPipe는 CPU 기본 — Lambda·온디바이스 모두 OK
- **데이터 계약 lockstep** (`analysis.ts` ↔ `models.py` ↔ `assemble.py`): 새 타입 추가 시 양쪽 동시 갱신 — 코드 주석에 명시 (CLAUDE.md "Cross-cutting")

### Integration Points
- **`pipeline/app.py:131-132`** — `_POSE_ESTIMATOR` 싱글톤. MediaPipe로 교체 + import 경로 변경. `_ensure_adapters()` 함수가 lazy 인스턴스화
- **`runpod_inference/server.py`** — RunPod GPU 추론 경로. MediaPipe로 swap 후 RunPod 자체 처분 여부 검토(deferred)
- **`extract_reference_angles.py`** — 정은지 기준 모션 추출. swap 후 기존 추출 결과 본자이션 필요 여부 검토(deferred)
- **`PoseFrame` 데이터 계약** — `app/src/types/analysis.ts` + `backend/shared/python/sunity_shared/models.py`에 lockstep으로 새 타입 추가
- **`adapters/` 모듈** (제안 위치 `sunity_shared/analysis/adapters/`) — `MediaPipe33ToCOCO17Adapter`, `SMPLXToCOCO17Adapter` 한 곳에 모아 엔진 교체 시 swap 단순화

</code_context>

<specifics>
## Specific Ideas

- **D-04 (스키마)와 D-05 (Confidence)는 belle가 정책 수준으로 명확히 결정** — 플래너·실행자는 이 두 결정을 수정 금지. 특히 D-05의 고객 리포트 정책 (기술 용어 노출 금지)은 결과 화면 카피 전반에 적용되어야 함
- **회귀 검증 영상 5개부터 시작**, 25개 다양성 세트는 belle에게 지속 요청 — belle 인지 유지 (검증 단계마다 요청)
- **NLF 격리는 atomic** — config 플래그 점진 롤아웃 없이 한 번에 swap (중간 상태 단순성 우선)
- belle 톤: 분석 정확도가 최우선. 트레이드오프 발생 시 정확도 선택. "AI가 모른다" 반응을 만들지 않는 것이 핵심

</specifics>

<deferred>
## Deferred Ideas

### Phase 2~15 또는 후속 결정

- **RunPod GPU pod 처분** — MediaPipe Heavy가 Lambda CPU에서 적정 속도로 돌면 RunPod 불필요. R&D 비교군용으로 유지(월 비용) vs 즉시 종료(필요 시 재생성) vs Stop 후 필요할 때 재시작. Phase 1 회귀 검증 완료 + 추론 속도 측정 후 결정
- **기존 Firestore 분석 결과/정은지 기준 모션 본자이션** — NLF 기반으로 저장된 데이터(meanAngles, EXTEND 프로파일 등)는 MediaPipe 기반으로 재추출 필요. Phase 14 (정은지 기준 모션 등록)에서 다각도 캡처와 함께 재구축이 자연스러움. 그 사이 기존 데이터 호환 정책 필요
- **`pose_landmarker_heavy.task` 모델 파일 배포 위치** — Lambda 레이어(~50MB 추가) vs S3 다운로드(콜드스타트 +1~2s). 플래너 판단
- **MediaPipe Heavy 추론 속도가 SLA 부적합 시** — 다중 시점 동시 분석에서 누적될 수 있음. 병렬화·캐싱 전략 후속 검토
- **NLF/SMPL-X 상업 라이선스 협의** — Max Planck Innovation `info@max-planck-innovation.de`. belle 평행 진행. R&D 격리로 Phase 진행은 블로킹 안 됨, 단 향후 NLF를 제품에 재도입하려면 클리어 필수

</deferred>

---

*Phase: 1-PoseEngine 추상화 + MediaPipe 어댑터 + 폴 축 정렬 + NLF R&D 격리*
*Context gathered: 2026-05-31*
*Pivot update: 2026-06-02 (RTMW free-stack pivot — D-17~D-25 추가, D-01~D-08 일부 supersede)*
