# Phase 1: PoseEngine 추상화 + MediaPipe 어댑터 + 폴 축 정렬 + NLF R&D 격리 - Research

**Researched:** 2026-05-31
**Domain:** 인체 포즈 추정 (3D), 컴퓨터 비전 (Hough line), 어댑터 아키텍처, Lambda/RunPod 배포
**Confidence:** HIGH (MediaPipe API·OpenCV·기존 코드 구조) / MEDIUM (배포 경로·회귀 검증 임계값) / LOW (BlazePose Heavy 정확한 추론 속도 Lambda CPU 실측치)

## Summary

이 Phase는 **상용 제품 코드의 포즈 엔진을 NLF → MediaPipe로 무중단 마이그레이션 + NLF/SMPL-X를 비상업 R&D 비교군으로 격리**하는 작업이다. 동시에 모든 다운스트림 분석(체형 정규화 / 힘 패턴 / 채점)의 공통 기반인 **`PoseEngine` 인터페이스 + `PoseFrame` 공통 계약 + 폴 축 자동 검출 + 기준 좌표계 정렬**을 도입한다.

기술 영역에 큰 함정이 하나 있다. **MediaPipe는 Linux ARM64(aarch64) wheel을 공식 제공하지 않는다** — 현재 `backend/template.yaml`이 `Architectures: [arm64]`로 설정되어 있어 Lambda 직접 배포는 불가능하다. 단 belle 결정에서 Lambda는 이미 "RunPod 위임 모드"로 운영 중이고(`pipeline/app.py:77`), 폴백 경로는 NaN 발산으로 시연만 가능했으므로 — **MediaPipe는 RunPod 서버 위에서 돌리고 Lambda는 위임 모드를 유지**하는 것이 가장 안전한 길이다(Pod base image가 Linux x86_64 + glibc≥2.28). RunPod GPU 처분은 deferred지만, MediaPipe는 CPU에서 충분히 돌므로 향후 CPU Pod 다운사이즈도 옵션이다.

기존 코드베이스는 이미 `interfaces.py:PoseEstimator` Protocol + lazy import + 어댑터 패턴이 잘 잡혀 있다 — 이 결을 따라 `MediaPipePoseEngine`을 추가하고, `NlfPoseEstimator`를 `backend/research/pose_engines/nlf/`로 이동하면 swap이 깔끔하다. 기존 `skeleton.py` / `JOINT_ANGLES` / `temporal.py` / `features.py`는 D-04 결정(스코어링 계약 = COCO-17 유지)으로 그대로 재사용된다 — 새로 만들어야 할 것은 ① `MediaPipePoseEngine` 어댑터, ② `MediaPipe33ToCOCO17Adapter`, ③ `PoleDetector` (Hough Line Transform + 수직 prior), ④ `PoleAxisAligner` (좌표계 변환), ⑤ `PoseFrame` 데이터 계약 lockstep, ⑥ R&D 평가 스크립트 `compare_engines.py`이다.

**Primary recommendation:** MediaPipe Tasks API(PoseLandmarker) Heavy variant + VIDEO RunningMode를 RunPod 서버 위에서 실행하고, Lambda는 위임 모드 그대로 유지한다. SAM template `Architectures`는 다음 phase에서 별도로 재검토. `pipeline/app.py:131`의 NLF import 1줄만 바꾸고 (그러나 격리·평가 스크립트 이동·계약 lockstep까지 함께) atomic swap.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**MediaPipe Variant 선택:**
- **D-01:** Variant = **BlazePose Heavy** (Tasks API). 폴 가림·접힌 자세에 최고 정확도 — 서버 inference라 속도 부담 적음
- **D-02:** API = **MediaPipe Tasks API** (PoseLandmarker, .task 모델 파일). Solutions(legacy) 비사용 — deprecated 예고됨
- **D-03:** 좌표 = **world landmarks(metric 3D)** 기본 분석용 + image landmarks도 함께 출력(UI 오버레이용). PoseFrame에 keypoints3D(world) + keypoints2D(image) 둘 다 저장
- **D-04:** 스키마 = **원본 저장은 MediaPipe 33 전체** (절대 17로 떨궈 저장 X). 스코어링/분석 계약은 **COCO-17 + 폴 확장(toe·heel·grip)** 유지. 어댑터 `MediaPipe33ToCOCO17Adapter`(+ 폴 확장 추출)로 변환. 엔진 교체 시 `SMPLXToCOCO17Adapter`로 swap. 폴 확장 landmark는 별도 feature set + confidence 게이트(가림 대응). 기존 `skeleton.py` / `JOINT_ANGLES` / `KEYPOINT_NAMES` / `features` / `temporal` 그대로 재사용.
- **D-05:** Confidence 변환 정책 (정책 수준 결정 — 모든 다운스트림이 따름):
  - 변환식: 둘 다 있으면 `confidence = visibility × presence`, `uncertainty_proxy = 1 - confidence`. visibility만 있으면 `confidence = visibility`.
  - 저장 필드: `raw_visibility`, `raw_presence`, `confidence`, `uncertainty_proxy` 모두 별도 저장
  - 사용처: keypoint 신뢰도 체크, 저신뢰 프레임 필터링, 각도 유효성 체크, temporal 스무딩, short-gap 보간, 리포트 신뢰도 경고
  - 규칙: 저신뢰 키포인트는 정확하다고 가정 금지. 각도에 필요한 키포인트가 저신뢰이면 그 각도 "low reliability" 마킹. 저신뢰 프레임 비율 높은 구간은 과분석 금지
  - 고객 리포트 정책: visibility·presence·uncertainty·landmark confidence·MediaPipe·COCO-17·NLF 등 기술 용어 노출 금지
  - 향후 호환: NLF 통합 시 동일 confidence/uncertainty 인터페이스로 매핑 (feature pipeline 재설계 금지)

**NLF R&D 격리:**
- **D-06:** NLF 위치 = **`backend/research/pose_engines/nlf/`** (제품 패키지 `sunity_shared` 밖). 평가 스크립트 = `backend/research/evaluations/`
- **D-07:** Import 차단 = **물리 경로 분리만** (lint rule·import-linter 없음). Lambda 레이어(`/opt/python`)에 미포함 — 배포 패키지에 NLF/torch/ultralytics 부재
- **D-08:** swap 전략 = **MediaPipe 구현 완성 + 회귀 검증 통과 후 atomic swap**. 중간 상태 없음. config 플래그 점진 롤아웃 안 함

**폴 축 검출:**
- **D-09:** 검출 = **Hough Line Transform + 수직 prior 자동**. OpenCV 전통 CV. UX 마찰 0
- **D-10:** 시간 안정 = **영상 전체 평균 축 1개** 산출 (confidence 가중평균). 스피닝 폴은 v1.5
- **D-11:** 검출 실패 폴백 = **수직 가정 + confidence='low' 표기**
- **D-12:** 좌표 저장 = **raw + pole-aligned 둘 다** PoseFrame에 저장. PoleAxis도 메타로 저장

**회귀 검증:**
- **D-13:** 검증 세트 = **정은지 영상 5개로 빠른 시작** (25개 다양성 세트는 belle에게 지속 요청)
- **D-14:** 점수 갭 허용 = **±5점 이내** (overall 100점 만점)
- **D-15:** 추가 검증 지표 4개: ① 정은지 영상 ≥70점 (SCORE-04 직결), ② Top-3 실패 원인 ≥2/3 겹침, ③ 키포인트 confidence 분포 임계값 이상, ④ 추론 속도 ms/frame
- **D-16:** 검증 실패 시 = **Phase 1 종료 보류, 원인 분석 후 재시도** (swap 안 됐으니 회귀 없음)

### Claude's Discretion

- 폴 확장 landmark(toe/heel/grip)의 정확한 MediaPipe 33 인덱스 매핑 — 본 RESEARCH §Pole 확장 매핑 참조
- `PoseEngine` 인터페이스 메서드 시그니처 세부 — 본 RESEARCH §Architecture Patterns 권장안
- `MediaPipe33ToCOCO17Adapter` / `SMPLXToCOCO17Adapter` 모듈 위치 — `sunity_shared/analysis/adapters/` 권장
- Hough Line Transform 파라미터 초기값 — 본 RESEARCH §Hough 권장 파라미터
- 회귀 검증 보고서 출력 포맷 — 본 RESEARCH §회귀 보고서 포맷
- `pose_landmarker_heavy.task` 배포 위치 — 본 RESEARCH §모델 파일 배포 권장
- MediaPipe 실패 시 `NoHumanError` 재사용 여부 — 재사용 권장 (이미 contract `no_human`으로 매핑)

### Deferred Ideas (OUT OF SCOPE)

- RunPod GPU pod 처분 (Phase 1 회귀 검증 + 속도 측정 후 결정)
- 기존 Firestore 분석 결과/정은지 기준 모션 본자이션 (Phase 14에서 다각도 재구축이 자연스러움)
- pose_landmarker_heavy.task 배포 위치 (Lambda 레이어 vs S3) — 본 RESEARCH 권장은 있음
- MediaPipe Heavy SLA 부적합 시 병렬화/캐싱 전략
- NLF/SMPL-X 상업 라이선스 협의 (belle 평행, 향후 NLF 재도입 시 게이트)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POSE-01 | 상용 제품 코드의 포즈 엔진이 NLF → MediaPipe로 마이그레이션되고 `PoseEngine` 인터페이스 + 공통 계약(`PoseFrame`)이 도입된다. `NlfPoseEngine` 어댑터는 R&D 비교군으로 격리되어 제품 파이프라인 import 경로에서 제거되고 사내 평가 스크립트에서만 호출된다 (라이선스 리스크 0) | §Standard Stack (MediaPipe Tasks API), §Architecture Patterns (PoseEngine 시그니처, Adapter 패턴), §Don't Hand-Roll (BlazePose), §NLF 격리 (제거 대상 코드 라인), §Code Examples (PoseLandmarker VIDEO 모드) |
| POSE-02 | 폴 축이 자동 검출되고 모든 키포인트가 폴 기준 좌표계로 정렬되며, 가림 프레임은 confidence 낮음으로 표기되어 후속 분석이 단정하지 않는다 (스피닝 폴은 v1.5) | §Standard Stack (OpenCV Hough), §Architecture Patterns (PoleDetector·PoleAxisAligner), §Hough 권장 파라미터, §Pole axis 변환 수학, §Code Examples (scipy align_vectors) |

## Project Constraints (from CLAUDE.md)

**Tech stack (변경 금지):**
- Expo+RN(TS), Lambda(Python 3.12)+SAM, Firestore, S3, **MediaPipe 기반 PoseEngine**(이 Phase에서 도입), Cerebras LLM, EAS Build
- 인프라: Motion AI는 별도 Lambda+S3 (기존 sunity.ai EC2 분리 유지)
- 시크릿: AWS Parameter Store. `.env` 하드코딩 금지

**필수 패턴/원칙:**
- 데이터 계약 lockstep: `app/src/types/analysis.ts` ↔ `backend/shared/python/sunity_shared/models.py` ↔ `docs/contract.md` 항상 동시 변경
- Firestore nested-array 금지 — `(T, J)` 행렬은 flat 저장 + reshape (`firestore_admin.complete_analysis`, `AnalysisDoc.angles`)
- SAM 빌드 native deps: `sam build --use-container` 필수 (Mac native binary가 Lambda Linux에서 ImportError). Docker Desktop 켜둘 것
- GPU 의존: 현 NLF는 CUDA 필수. MediaPipe Heavy는 CPU OK — 이 Phase의 큰 운영 효과
- 작은 단위 작업, 의미있는 테스트만, 이모지·슬롭 코드 금지
- **분석 정확도 = Core value, 트레이드오프 시 정확도 우선** (비용 하한은 구독료 수준)
- Korean for user-facing copy and most comments; identifiers and code remain English
- "Cite the spec" in comments using project shorthand (`design.md §5-4`, `contract.md §2`, `01_체형차이_보정엔진_FINAL §0.7` 등)

**GSD Workflow Enforcement (CLAUDE.md):**
- Edit/Write 도구 사용 전 GSD 커맨드로 시작. 직접 repo 편집 금지

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 포즈 추정 (영상 → 33 landmarks) | RunPod GPU/CPU 서버 | — | 무거운 모델·image processing은 backend 전용. Lambda는 위임만 |
| 33→COCO-17+폴확장 어댑터 변환 | RunPod 서버 (`sunity_shared/analysis/adapters/`) | — | 순수 함수, Lambda CPU에서도 도는 가벼운 로직 (PoseFrame 자체는 양쪽 다 OK) |
| 폴 축 검출 (Hough) | RunPod 서버 (`sunity_shared/analysis/pole/`) | — | OpenCV가 영상 프레임 필요 — pipeline 안에서 frame extraction 직후 |
| 폴 좌표계 변환 (numpy/scipy) | RunPod 서버 (`sunity_shared/analysis/pole/`) | — | 순수 수학 — 어디서든 OK이나 데이터 가까이 |
| PoseFrame 데이터 계약 정의 | Backend `sunity_shared.models` ↔ App `app/src/types/analysis.ts` | docs/contract.md | Lockstep — 양쪽에 동시 정의 |
| Firestore 저장 (flat 변환) | Backend `firestore_admin` | — | App은 읽기 + reshape만 |
| R&D 평가 (NLF vs MediaPipe) | `backend/research/` (제품 import 경로 밖) | — | 제품 코드 비호출 — 사내 평가 전용 |
| 결과 화면 (PoseFrame 소비) | App `app/src/app/analysis/result.tsx` 등 | — | 키포인트 오버레이는 Phase 12 — Phase 1은 데이터 계약만 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mediapipe` | 0.10.35 [VERIFIED: PyPI registry · pip index versions] (릴리스 2026-04-27) [CITED: pypi.org/project/mediapipe/] | PoseLandmarker (BlazePose 33 landmarks, world+image, visibility+presence) | belle 결정 (D-01·D-02). Apache 2.0 라이선스 리스크 0. 공식 권장 신 Tasks API |
| `opencv-python-headless` | 4.13.0.92 [VERIFIED: PyPI registry · pip index versions] [CITED: pypi.org/project/opencv-python-headless/] | Canny edge + HoughLines/HoughLinesP (폴 축 자동 검출 D-09) | 표준 CV. headless = GUI 없음 → 서버 환경 적합. ARM64 wheel 있음(33.7MB) |
| `scipy` | 1.17.1 [VERIFIED: PyPI registry · pip index versions] [CITED: docs.scipy.org] | `scipy.spatial.transform.Rotation.align_vectors`(폴축→Z축 회전행렬) | 표준 과학 계산. numpy만으로 직접 짜면 edge case(평행/반대 방향) 잠재. align_vectors는 검증된 구현 |
| `numpy` | 1.26+ (이미 의존) | 기존 분석 코어 — features/temporal/motiondtw에서 사용 | 변경 없음 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `imageio` / `imageio-ffmpeg` | 이미 의존 (≥2.34 / ≥0.5.1) | 영상 → 프레임 추출 (`FfmpegFrameExtractor`) | 그대로 재사용 — MediaPipe Image 객체로 변환만 추가 |
| `boto3` / `firebase-admin` | 이미 의존 | S3 다운로드 + Firestore Admin | 변경 없음 |
| `pytest` | ≥8 (이미 의존) | 단위 테스트 | MediaPipe 어댑터 단위 테스트 (Heavy 모델 무거우니 mock + 통합 테스트 분리) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| MediaPipe Heavy | MediaPipe Full | belle가 Heavy 선택 (정확도 우선) — Full은 100~150ms/frame로 빠르지만 폴 가림 자세 약함 |
| Hough Line Transform | RANSAC + Sobel | 더 견고하나 OpenCV에 직접 함수 없음 (구현 부담). belle가 Hough 선택 (UX 마찰 0) |
| scipy align_vectors | numpy로 Rodrigues 직접 구현 | scipy는 ~30MB 추가 의존. 단 변환 수학 정확성·평행/반대 vector edge case 처리에 검증됨 → 정확도 우선 원칙으로 scipy 채택 권장 |
| `mediapipe.solutions.pose` (legacy) | MediaPipe Tasks API | D-02 결정 — Solutions는 deprecated. Tasks API는 .task 모델 + 명시적 RunningMode (장기 지원) |
| `opencv-python` | `opencv-python-headless` | 둘 다 같은 API. headless는 ~14MB 작음 + GUI deps 없음 → 서버 환경 표준 |

**Installation (RunPod requirements.txt에 추가):**
```bash
mediapipe==0.10.35
opencv-python-headless==4.13.0.92
scipy>=1.17,<2.0
```

**Version verification (이미 위에서 수행):**
- `python3 -m pip index versions mediapipe` → 0.10.35 (최신)
- `python3 -m pip index versions opencv-python-headless` → 4.13.0.92
- `python3 -m pip index versions scipy` → 1.17.1
- `pypi.org/project/mediapipe/` 페이지: 릴리스일 2026-04-27, Python 3.9~3.12 지원

**Lambda 레이어/배포 경고 (CRITICAL):**
- `mediapipe` PyPI wheel은 `manylinux_2_28_x86_64`만 제공. **Linux ARM64(aarch64) wheel 없음**. [CITED: pypi.org/project/mediapipe/]
- `backend/template.yaml` `Architectures: [arm64]` 그대로 두면 Lambda 직접 배포 차단 — 단 belle 결정상 운영은 RunPod 위임이므로 Lambda는 위임 코드만 (mediapipe import 안 함). RunPod base image는 x86_64 → mediapipe 정상.
- 향후 Lambda 폴백 경로에서 MediaPipe를 돌리려면: ① Architecture를 x86_64로 변경, ② Container Image 배포로 전환, 또는 ③ Lambda에서 폴백 경로 자체를 제거(RunPod 미설정 시 명확한 ConfigurationError로 fail-fast). 권장 = ③ (운영 단순성).

## Package Legitimacy Audit

> Phase 1이 추가 설치하는 외부 패키지 3개. slopcheck 통과 + PyPI registry 확인 완료.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `mediapipe` | PyPI | ~6년 (0.x 시리즈 2020+) | 수백만/월 | github.com/google-ai-edge/mediapipe | `[OK]` | **Approved** |
| `opencv-python-headless` | PyPI | ~10년 | 수천만/월 | github.com/opencv/opencv-python | `[OK]` | **Approved** |
| `scipy` | PyPI | 16+년 | 수억/월 | github.com/scipy/scipy | `[OK]` | **Approved** |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

검증 명령 출력 (요약):
```
slopcheck install mediapipe opencv-python-headless scipy
  [OK] mediapipe (pypi)
  [OK] scipy (pypi)
  [OK] opencv-python-headless (pypi)
==================================================
  scanned 3 packages
  3 OK
```

postinstall 스크립트: 모두 없음 (Python packages). 셋 다 공식 조직(Google, OpenCV, SciPy) 유지보수. **계약 위반(라이선스/postinstall 함정) 없음**.

## Architecture Patterns

### System Architecture Diagram

```
영상 업로드 (S3 PUT, 변경 없음)
        ↓
S3 ObjectCreated → SQS (변경 없음)
        ↓
Pipeline Lambda (위임 모드, 변경 없음)
        ↓ HTTP POST /analyze (X-RunPod-Token)
RunPod 서버 (server.py:_process_in_background)
        ↓ 새 코드 경로 ↓
  [1] FfmpegFrameExtractor.extract(video)  ─────── (재사용)
        ↓ frames (T,H,W,3) RGB uint8
  [2] PoleDetector.detect(frames) ────── NEW
        ↓ PoleAxis(direction_3d, confidence, source='hough'|'vertical_fallback')
  [3] PoseEngine.estimate(frames, pole_axis) ────── NEW (MediaPipePoseEngine)
        ↓ List[PoseFrame] (33 raw + COCO-17+pole_ext + visibility/presence/confidence)
  [4] PoleAxisAligner.align(pose_frames, pole_axis) ────── NEW
        ↓ pose_frames 에 keypoints3DPoleAligned 추가
  [5] MediaPipe33ToCOCO17Adapter ────── NEW (PoseFrame 내부에서 수행)
        ↓ COCO-17 좌표 + JOINT_ANGLES 8개
  [6] compute_joint_angles + joint_uncertainty ────── (재사용, confidence→uncertainty_proxy 매핑)
        ↓ angles (T, J)
  [7] temporal_fill(angles, uncertainty) ────── (재사용)
        ↓ filled angles
  [8] technique.recognize + dimensions.absolute_dimension_scores ────── (재사용)
        ↓
  [9] mode1 비교(motiondtw) 또는 mode3 (이전 분석 대비) ────── (재사용)
        ↓
  [10] Firestore Admin update (PoseFrame flat 저장 + 기존 angles flat)
        ↓
앱 onSnapshot → 결과 화면 (변경 없음, Phase 12에서 키포인트 오버레이 추가)

──────────────────────────────────────────────
R&D 평가 경로 (제품 import 경로와 완전 분리):

backend/research/evaluations/compare_engines.py
  ↓ 사용자 영상 N개
  ├── MediaPipePoseEngine (sunity_shared)  ──┐
  └── NlfPoseEngine (backend/research/pose_engines/nlf/) ──┘
        ↓
  같은 영상 → 두 엔진 결과 → 같은 다운스트림(features/dimensions) → 점수 비교
        ↓
  JSON 리포트 (motion_id별 두 점수 + Top-3 일치율 + confidence 분포 + ms/frame)
  Markdown 요약 (사람 읽기용)
```

**중요:**
- Phase 1은 위 `[2]`~`[5]`를 새로 만들고 NLF→MediaPipe 1:1 교체. `[1]·[6]·[7]·[8]·[9]·[10]`은 모두 그대로 재사용.
- 폴 축 검출은 frame extraction 직후·pose estimation 전에 한다 (POSE-02 핵심). 폴 축이 pose alignment에 쓰이는 게 아니라 출력 PoseFrame을 **사후 변환**하는 데 쓴다 (raw + aligned 둘 다 저장 = D-12).
- Pipeline Lambda는 코드 변경 거의 없음 — RunPod 서버가 모든 처리. NLF 격리로 Lambda 폴백 경로의 `_POSE_ESTIMATOR` import 자체가 사라짐 (NLF 모듈이 sunity_shared 밖으로 이동) — 폴백 경로는 명시적 ConfigurationError로 fail-fast 처리 권장.

### Recommended Project Structure

```
backend/
├── shared/python/sunity_shared/analysis/
│   ├── interfaces.py             # PoseEngine 인터페이스 확장 (기존 PoseEstimator Protocol 진화)
│   ├── pose_engines/             # NEW — 어댑터 위치
│   │   ├── __init__.py
│   │   └── mediapipe_engine.py   # NEW — MediaPipePoseEngine 어댑터
│   ├── adapters/                 # NEW — 스키마 변환
│   │   ├── __init__.py
│   │   ├── mediapipe_to_coco17.py  # NEW — 33→17 + pole 확장 추출 (toe/heel/grip)
│   │   └── (smplx_to_coco17.py)  # 미구현 — Phase 후속에서 R&D 비교군 SMPL-X 결과 변환 시 추가
│   ├── pole/                     # NEW — 폴 축 검출 + 정렬
│   │   ├── __init__.py
│   │   ├── detector.py           # NEW — HoughPoleDetector
│   │   └── aligner.py            # NEW — PoleAxisAligner (좌표계 변환)
│   ├── skeleton.py               # 재사용 (KEYPOINT_NAMES, JOINT_ANGLES — 변경 없음)
│   ├── features.py / temporal.py # 재사용
│   └── pose_estimator.py         # 삭제 또는 NlfPoseEstimator만 남기고 backend/research/로 이동
│
├── research/                     # NEW — 제품 패키지 밖. Lambda 레이어 미포함
│   ├── README.md                 # NEW — "이 폴더는 R&D 비교군 전용. 제품 코드에서 import 금지"
│   ├── pose_engines/
│   │   └── nlf/
│   │       ├── __init__.py
│   │       └── nlf_engine.py     # 기존 pose_estimator.py 의 NlfPoseEstimator (PoseEngine 인터페이스 구현)
│   └── evaluations/
│       ├── __init__.py
│       ├── compare_engines.py    # NEW — MediaPipe vs NLF 비교 (정은지 5영상 → JSON+Markdown)
│       └── (existing scripts 이동)  # extract_reference_angles.py / verify_nlf_pipeline.py / verify_self_comparison.py 중 NLF 의존 부분
│
├── functions/pipeline/app.py     # 수정 — line 131 import 교체 (NlfPoseEstimator → MediaPipePoseEngine)
├── runpod_inference/
│   ├── server.py                 # 거의 변경 없음 — pipeline._process 그대로 재사용
│   └── requirements.txt          # 수정 — mediapipe·opencv·scipy 추가, ultralytics 제거 (NLF 격리)
└── scripts/
    ├── extract_reference_angles.py     # MediaPipe 버전 작성 또는 backend/research/로 이동
    ├── verify_nlf_pipeline.py          # backend/research/evaluations/로 이동 (이름 그대로)
    └── verify_self_comparison.py       # 이중 — MediaPipe 버전 새로 작성 + NLF 버전은 backend/research/로

app/src/types/analysis.ts          # 수정 — PoseFrame 타입 추가 (lockstep)
backend/shared/python/sunity_shared/models.py  # 수정 — PoseFrame 추가 (lockstep)
docs/contract.md                   # 수정 — PoseFrame + PoleAxis 섹션 추가
```

### Pattern 1: PoseEngine 인터페이스 (기존 PoseEstimator Protocol 확장)

**What:** 기존 `interfaces.py:PoseEstimator` Protocol (`estimate(frames) -> (T,17,4)`)을 **PoseFrame을 반환하도록 확장**. 이 인터페이스 하나가 MediaPipe·NLF·미래의 어떤 엔진이든 똑같이 보임.

**When to use:** 모든 포즈 엔진 어댑터의 Protocol 계약. 다운스트림(pipeline/_process)은 이 Protocol에만 의존.

**권장 시그니처:**
```python
# backend/shared/python/sunity_shared/analysis/interfaces.py

from __future__ import annotations
from typing import Protocol
import numpy as np
from .pose_frame import PoseFrame, PoleAxis  # 새 모듈


class PoseEngine(Protocol):
    """프레임 시퀀스 → PoseFrame 리스트. 미감지 시 NoHumanError.

    PoseFrame은 raw 33 landmarks (저장은 항상) + COCO-17 derived (스코어링용) +
    폴 확장 (toe/heel/grip) + pole-aligned 좌표 (D-12) + visibility/presence/
    confidence/uncertainty_proxy (D-05) 모두 포함.

    pole_axis 인자: 영상 전체 평균 축 (D-10). detector에서 산출돼 estimator로 주입.
    estimator가 pole alignment까지 직접 책임지면 어댑터별로 동일 로직 중복 방지.
    """

    def estimate(
        self,
        frames: np.ndarray,            # (T,H,W,3) RGB uint8
        pole_axis: PoleAxis,           # PoleDetector 산출
    ) -> list[PoseFrame]:
        ...
```

**기존 `PoseEstimator` Protocol과의 관계:** D-04 결정에 따라 다운스트림은 `compute_joint_angles((T,17,4))`을 그대로 받는다. **두 Protocol을 병존시키지 않고 PoseEngine 단일**로 가되, `PoseEngine.estimate()` 반환 PoseFrame 리스트에서 `(T, 17, 4)` 배열을 추출하는 헬퍼를 한 곳에 두는 것이 단순하다 (예: `pose_frame.to_coco17_array(pose_frames) -> (T,17,4)`). 이 헬퍼만 거치면 기존 `compute_joint_angles` → `features` → `temporal` 체인이 무변경.

### Pattern 2: PoseFrame 데이터 계약 (lockstep)

**What:** 모든 다운스트림이 합의하는 frame당 데이터 구조. CONTEXT.md D-04·D-05·D-12 결정을 모두 담는다.

**TS (`app/src/types/analysis.ts`):**
```typescript
// PoseFrame — 두 엔진(MediaPipe / NLF) 공통 출력 (01_체형차이_보정엔진 §4.3 PoseFrame 진화)
export interface PoseFrame {
  frameIndex: number;
  timestampMs: number;
  // 원본 33 landmarks (D-04: 원본 저장은 33 전체). 키 = MediaPipe landmark name (33개)
  rawLandmarks33?: Record<string, {
    x: number; y: number; z: number;
    visibility: number; presence: number;
  }>;
  // COCO-17 derived (스코어링/분석 계약 — D-04)
  keypoints3D: Record<string, {
    x: number; y: number; z: number;
    confidence: number;        // D-05: visibility×presence
    uncertaintyProxy: number;  // D-05: 1 - confidence
  }>;
  // 폴 기준 좌표계로 변환된 keypoints3D (D-12). 분석은 이걸 사용
  keypoints3DPoleAligned: Record<string, { x: number; y: number; z: number }>;
  // image 좌표 (UI 오버레이용 — D-03). normalized 0~1
  keypoints2D?: Record<string, { x: number; y: number; visibility: number }>;
  // 폴 확장 landmark (D-04). toe/heel/grip. confidence 게이트 후 사용
  poleExtensionLandmarks?: Record<string, {
    x: number; y: number; z: number;
    confidence: number;
  }>;
}

export interface PoleAxis {
  // 영상 전체 평균 축 (D-10). 단위 벡터 (정규화됨)
  direction3D: { x: number; y: number; z: number };
  // 검출 신뢰도 (Hough 결과 가중평균 + 수직성 점수). 0~1
  confidence: number;
  // 'hough' = 자동 검출 성공 / 'vertical_fallback' = D-11 폴백
  source: 'hough' | 'vertical_fallback';
}
```

**Python (`backend/shared/python/sunity_shared/models.py`) — 동등 정의** (dataclass 또는 TypedDict 권장).

**Firestore 저장 전략 (nested-array 금지):** PoseFrame 리스트는 frame index × landmark name × {x,y,z,vis,pres} 라는 깊이 3 nested array가 됨. Firestore 한도(문서 1MB) 부담도 큼. 권장: **PoseFrame 전체를 Firestore에 저장하지 않는다**. 기존 angles flat 저장 패턴 그대로 유지하고, PoseFrame는 RunPod 메모리에서만 살다가 분석 결과(`AnalysisResult`)에 필요한 부분만 추출해 저장. 키포인트 오버레이(Phase 12)는 별도 phase에서 필요한 만큼만 추가 저장 (예: keypoints2D 평균 + 대표 프레임 N개). 이번 phase에서는 PoseFrame 타입은 정의하되 Firestore 저장 필드는 추가하지 않는다 (기존 `angles`/`anglesJointKeys`/`anglesFrames`로 충분).

### Pattern 3: Adapter (33→COCO-17 + 폴 확장)

**MediaPipe 33 → COCO-17 매핑** (D-04, [CITED: developers.google.com/mediapipe — BlazePose landmark list]):

표준화된 공식 매핑 테이블은 MediaPipe 공식 문서에 없음 [ASSUMED — 다음 매핑은 명칭 기반 추론, 플래너가 수동 검증 권장]. MediaPipe 33 → COCO-17 (skeleton.KEYPOINT_NAMES 순서):

| COCO-17 (skeleton.py 순서) | MediaPipe 33 index | MediaPipe 명칭 |
|----------------------------|---------------------|------------------|
| 0 nose | 0 | nose |
| 1 left_eye | 2 | left eye (center) |
| 2 right_eye | 5 | right eye (center) |
| 3 left_ear | 7 | left ear |
| 4 right_ear | 8 | right ear |
| 5 left_shoulder | 11 | left shoulder |
| 6 right_shoulder | 12 | right shoulder |
| 7 left_elbow | 13 | left elbow |
| 8 right_elbow | 14 | right elbow |
| 9 left_wrist | 15 | left wrist |
| 10 right_wrist | 16 | right wrist |
| 11 left_hip | 23 | left hip |
| 12 right_hip | 24 | right hip |
| 13 left_knee | 25 | left knee |
| 14 right_knee | 26 | right knee |
| 15 left_ankle | 27 | left ankle |
| 16 right_ankle | 28 | right ankle |

**폴 확장 landmark** (D-04, 분석에 보조용):

| 폴 확장 키 | MediaPipe 33 index | 명칭 |
|------------|---------------------|------|
| left_heel | 29 | left heel |
| right_heel | 30 | right heel |
| left_foot_index (toe) | 31 | left foot index |
| right_foot_index (toe) | 32 | right foot index |
| left_pinky (grip 보조) | 17 | left pinky |
| right_pinky (grip 보조) | 18 | right pinky |
| left_index (grip 보조) | 19 | left index finger |
| right_index (grip 보조) | 20 | right index finger |
| left_thumb (grip 보조) | 21 | left thumb |
| right_thumb (grip 보조) | 22 | right thumb |

[CITED: developers.google.com/mediapipe — BlazePose 33 landmarks 0~32 indexing]. "grip"은 폴을 잡은 손 위치 — pinky/index/thumb 평균이 손 중심 근사. 폴 가림 영향이 큰 영역이므로 D-04 confidence 게이트 필수.

### Pattern 4: PoleDetector (Hough Line Transform + 수직 prior + 시간 안정)

**알고리즘:**
1. 각 프레임 → 그레이스케일 → Canny 엣지
2. `cv2.HoughLinesP`로 선분 검출
3. 수직성 필터: 선분 각도가 [85°, 95°] 또는 [-95°, -85°] 범위인 선분만 (≈±5° tolerance)
4. 선분 길이 가중치 부여 (긴 선분이 폴일 가능성 높음)
5. 프레임당 후보 선분 평균 방향 vector + 평균 위치
6. 영상 전체에 대해 confidence 가중평균 (D-10) → `PoleAxis` 1개

**프레임당 confidence (제안):** `min(filtered_segments_total_length / image_height, 1.0)`. 폴이 화면 높이의 ~80% 이상 차지하면 confidence≈0.8+. 임계값 미만 영상 비율이 50%↑이면 D-11 폴백 (수직 가정 + confidence='low').

### 권장 Hough 파라미터 (초기값)

OpenCV 공식 튜토리얼 [CITED: docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html] 권장값을 폴 검출 목적에 맞게 조정:

```python
# Canny 엣지 검출
canny_low = 50
canny_high = 200
canny_aperture = 3

# HoughLinesP (확률적 Hough)
rho = 1                            # 픽셀 해상도
theta = np.pi / 180                # 1° 해상도
threshold = 80                     # 교차점 최소 (640x?? 영상 기준, 폴이 명확하면 ~100, 약하면 ~50)
min_line_length = 100              # 폴은 보통 화면 높이의 50%+ → 640px 기준 ~150 권장
max_line_gap = 20                  # 폴이 인체에 살짝 가려도 잇기

# 수직 필터링
vertical_tolerance_deg = 5         # ±5° (D-09 의도와 일치)
```

**튜닝 노트:** 정은지 5영상으로 빠르게 sweep. 검출 실패 시 `threshold` 낮추기(50→30) + `min_line_length` 짧게(100→60). 회귀 검증 D-15 ③ 결과를 보고 적응.

### Pattern 5: PoleAxisAligner (좌표계 변환 수학)

**입력:** PoseFrame keypoints3D (world 좌표, 미터 단위, 골반 중심 원점) + PoleAxis.direction3D (단위 벡터)
**출력:** 회전 적용된 좌표 (폴 축이 Z 축에 정렬됨) → keypoints3DPoleAligned

**수학 (scipy 사용 권장):**
```python
from scipy.spatial.transform import Rotation

# pole_axis: 단위 벡터 (x,y,z). target = [0, 0, 1] (Z 축 = 수직)
# scipy.align_vectors는 b를 a에 정렬 — a=target, b=pole_axis 순서
rot, _ = Rotation.align_vectors([target], [pole_axis_direction])
R = rot.as_matrix()  # (3, 3)

# 모든 keypoint에 R 적용
for kp_name, kp in keypoints3D.items():
    aligned = R @ np.array([kp.x, kp.y, kp.z])
    keypoints3DPoleAligned[kp_name] = {"x": aligned[0], "y": aligned[1], "z": aligned[2]}
```

**Edge case:** `pole_axis_direction ≈ [0, 0, ±1]`이면 회전 무필요 (식별). `pole_axis_direction ≈ [0, 0, -1]`이면 180° 회전 (scipy align_vectors가 안전하게 처리). [CITED: docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.align_vectors.html]

### Anti-Patterns to Avoid

- **MediaPipe 33을 처음부터 17로 떨궈 저장:** D-04 직접 위반. 후속 phase(폴 확장·grip 분석)에서 정보 손실 — 재추출 필요. **원본 33 전체 저장 + 변환은 런타임에**.
- **Lambda 폴백 경로에서 MediaPipe 직접 import:** mediapipe wheel은 Lambda ARM64 미지원. ImportError 발생. 폴백 경로는 명시적 ConfigurationError로 fail-fast 권장.
- **import-linter / lint 룰로 NLF import 차단:** D-07 직접 위반. 물리 경로 분리(`backend/research/`)만으로 충분 — 도구 오버헤드 추가 금지.
- **Config 플래그로 점진 롤아웃 (POSE_ENGINE=nlf|mediapipe):** D-08 직접 위반. atomic swap이 결정. 이중 모드 운영 부담 회피.
- **PoseFrame 전체를 Firestore에 저장:** nested-array + 용량 폭주. flat angles 저장 패턴 유지 + 시각화 필요한 데이터만 별도 저장(Phase 12 결정).
- **폴 축 검출 실패 → 분석 실패 처리:** D-11 직접 위반. 수직 폴백 + confidence='low' 표기. 사용자 친화 카피로 "카메라 기울어져 세부 각도 해석에 주의" 안내.
- **고객 리포트에 기술 용어 노출 (visibility/MediaPipe/COCO-17/uncertainty 등):** D-05 직접 위반. "이 구간은 무릎 위치가 영상에서 명확하게 보이지 않아..." 톤만.
- **각 어댑터(MediaPipe/NLF)에서 폴 alignment 각자 구현:** DRY 위반. Aligner는 PoseEngine 외부 (또는 estimate 내부에서 공통 헬퍼 호출).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 3D 인체 포즈 추정 | 자체 keypoint 검출 모델 | MediaPipe PoseLandmarker (Heavy) | 십수 년의 BlazePose GHUM 학습 데이터. 자체 학습은 수개월 + GPU 비용 |
| 직선 검출 | 자체 edge → grouping 알고리즘 | `cv2.HoughLinesP` | 1962년부터 검증된 알고리즘. OpenCV 구현 + Canny가 산업 표준 |
| 벡터-벡터 회전행렬 | numpy로 Rodrigues 수동 구현 | `scipy.spatial.transform.Rotation.align_vectors` | 평행/반대 vector edge case 처리 검증됨. ~30LOC 수동 코드 대신 1줄 |
| 영상 프레임 추출 | ffmpeg subprocess 직접 호출 | `FfmpegFrameExtractor` (이미 있음, 재사용) | 다운샘플 + start_s/end_s 이미 구현 — 변경 불필요 |
| Firestore Admin 호출 | requests로 REST API 직접 | `firebase-admin` (이미 있음) | 인증·재시도·페이지네이션 모두 처리 |
| 시간축 보간 + 가림 처리 | 자체 outlier detection | `temporal.temporal_fill` + `occluded_mask` (이미 있음) | NLF uncertainty 신호 흐름과 동일 (uncertainty_proxy로 호환) |
| KISMAM 채점 / DTW 정렬 | 처음부터 | `motiondtw` + `kismam` (이미 있음) | Phase 1은 포즈 엔진만 교체. 다운스트림 무변경 |
| Visibility×Presence 가중 변환 | 임의 공식 | D-05 명시 변환식 | belle 정책 결정 — 변경 금지 |

**Key insight:** Phase 1의 본질은 **포즈 엔진 1개 교체 + 새 데이터 계약 도입 + 폴 축 산출/정렬 추가**이며, 기존 알고리즘 코어(features/temporal/motiondtw/kismam/dimensions/assemble)는 변경 0이어야 한다. 변경이 다른 곳까지 번지면 회귀 검증(D-13~16)이 무의미해진다. **"PoseEngine 어댑터 + Adapter + PoleDetector + PoleAxisAligner + 4개 모듈"만이 새 코드**.

## Runtime State Inventory

Phase 1은 **포즈 엔진 교체 + 모듈 격리 작업**이므로 rename/refactor에 해당 — 이 inventory가 결정적이다.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Firestore `users/{uid}/analyses/{id}.angles` (flat) + `reference/{motionId}.angles`(flat). NLF 기반으로 추출됨 — MediaPipe로 재추출하면 수치가 다름 (특히 폴 가림 자세) | **코드 edit + 데이터 마이그레이션 deferred** (Phase 14에서 다각도 재캡처와 함께 재구축이 자연스러움 — CONTEXT.md deferred). 그 사이 호환 정책: Phase 1 swap 후 신규 분석은 MediaPipe로, 기존 reference 5개는 NLF 추출치 유지 — 점수 비교는 같은 엔진끼리만 (회귀 검증 D-13에서 두 엔진 결과 격차 측정해 belle 인지) |
| Live service config | RunPod env `RUNPOD_AUTH_TOKEN`, AWS keys 그대로. **추가:** RunPod 서버에 mediapipe model 파일 위치 env (e.g., `MEDIAPIPE_POSE_MODEL_PATH`) — Pod 재생성 시 모델 재다운로드 필요. SAM Parameter `RunpodAnalyzeUrl` 그대로 (URL 안 바뀜) | RunPod 서버 setup.sh 또는 README에 model 다운로드 단계 추가. 모델은 GitHub release 또는 S3 또는 Pod 부팅 시 `wget`로 가져오기 |
| OS-registered state | None found — Lambda 함수명/SQS 큐명/SAM stack명 모두 그대로 유지 | None |
| Secrets/env vars | 신규 환경변수 없음 (mediapipe는 키 불필요). 기존 secret 모두 그대로 | None |
| Build artifacts / installed packages | RunPod Pod의 기존 설치: `torch`, `ultralytics`, NLF torchscript 파일 (`backend/scripts/nlf_l_multi.torchscript`, `backend/yolo11n.pt`). Lambda 레이어의 `sunity_shared` 패키지에서 `pose_estimator.py` 모듈 삭제 시 `.aws-sam/build/` cache가 stale | 1) RunPod requirements.txt 갱신 후 Pod에 `pip install -r requirements.txt` 재실행 (ultralytics·torch 유지는 NLF R&D용 — 또는 분리). 2) `sam build --use-container` 재실행. 3) NLF 모델 파일(`nlf_l_multi.torchscript`)은 `backend/research/pose_engines/nlf/models/`로 이동 |

**Nothing found in category:** OS-registered state는 명시적으로 없음 (확인했음 — pm2/launchd/systemd 미사용, Lambda는 자체 관리).

## Common Pitfalls

### Pitfall 1: MediaPipe ARM64 wheel 부재
**What goes wrong:** SAM template `Architectures: [arm64]` 그대로 두고 `pipeline/requirements.txt`에 `mediapipe` 추가 → `sam build --use-container`가 `ERROR: Could not find a version that satisfies the requirement mediapipe`
**Why it happens:** mediapipe PyPI wheels는 `manylinux_2_28_x86_64`, `macosx_11_0_arm64`, `win_amd64`, `win_arm64`만 있음. **Linux aarch64 wheel 미제공** [CITED: pypi.org/project/mediapipe/, github.com/google-ai-edge/mediapipe/issues/5965]
**How to avoid:**
- 권장: **Lambda 폴백 경로에서 MediaPipe 미사용**. RunPod 위임이 운영. Lambda 폴백은 ConfigurationError로 fail-fast (메시지: "RunPod 위임 미설정 — 분석 불가").
- 대안 1: SAM template `Architectures`를 `x86_64`로 변경 (그러나 다른 Lambda 함수에 영향 — 별 phase에서 검토)
- 대안 2: Lambda Container Image 배포 + Mac에서 Docker `--platform linux/amd64` 빌드 [CITED: repost.aws/articles/ — Apple Silicon Lambda 함정]
**Warning signs:** `sam build` 출력에 `No matching distribution found for mediapipe`. `pip install mediapipe` 직접 실행이 aarch64 wheel을 못 찾음.

### Pitfall 2: MediaPipe Tasks API의 timestamp 단조 증가 강제
**What goes wrong:** VIDEO RunningMode에서 `detect_for_video(image, timestamp_ms)` 호출 시 timestamp가 이전 호출보다 작거나 같으면 silently 잘못된 결과 또는 예외 [CITED: developers.google.com/mediapipe/api/solutions/python/mp/tasks/vision/PoseLandmarker]
**Why it happens:** MediaPipe 내부 tracking이 timestamp 기반.
**How to avoid:** frame_extractor의 source FPS·target FPS 기반으로 timestamp를 명시적으로 단조 증가하게 생성. `timestamp_ms = int(frame_index * 1000 / target_fps)` 또는 `int((1000/src_fps) * source_frame_index)`. 9 fps 다운샘플이라면 frame 0 → 0ms, frame 1 → 111ms, frame 2 → 222ms.
**Warning signs:** 같은 영상에서 일부 프레임만 미감지 + 일부는 timestamp 관련 경고 로그.

### Pitfall 3: World landmarks 좌표 원점 = 골반 중심 (hip midpoint)
**What goes wrong:** "world landmarks가 미터 단위 절대 좌표"라고 생각하고 폴 축 검출과 같은 좌표계로 가정 — alignment 의미 없음
**Why it happens:** MediaPipe world landmarks 원점은 **hip midpoint** [CITED: developers.google.com/mediapipe — "Real-world 3-dimensional coordinates in meters, with the midpoint of the hips as the origin"]. 폴은 영상 좌표계(픽셀)에서 검출됨.
**How to avoid:** 폴 축 검출은 image 좌표(픽셀)에서 → 2D 방향 vector. world keypoints에는 이 방향을 그대로 적용하지 말고 **수직 prior(D-09)를 기준으로 image 평면에서 폴 기울기각 산출 → camera 좌표계 회전으로 변환**. 단순화: image에서 폴이 수직과 얼마나 기울어졌는지(degree)만 측정 → world 좌표계에서 그만큼 회전 (assumed: 카메라 roll=0). 더 엄밀한 처리는 image landmarks의 2D 폴 위치와 keypoints2D를 결합해 카메라 모델 추정 — Phase 1 범위 밖.
**Warning signs:** pole-aligned 좌표가 raw와 거의 같거나, 비정상적으로 회전.

### Pitfall 4: protobuf 의존성 버전 충돌
**What goes wrong:** mediapipe는 protobuf 의존. firebase-admin도 protobuf 의존. 다른 버전이면 `TypeError: Descriptors cannot not be created directly` 등
**Why it happens:** mediapipe ~0.10.x는 protobuf>=3.20, firebase-admin은 보통 더 새 버전 허용 — 충돌 가능.
**How to avoid:** `pip install` 후 `pip check` 실행. 충돌 시 mediapipe가 요구하는 protobuf 버전 고정. RunPod requirements.txt에 명시적 버전 (e.g., `protobuf>=4.25,<5`) 추가.
**Warning signs:** Pod 부팅 로그에 protobuf 관련 ImportError 또는 deprecation warning.

### Pitfall 5: BlazePose Heavy 추론 속도가 RunPod CPU에서 SLA 초과
**What goes wrong:** Heavy variant는 belle 추정 200~400ms/frame. 30초 영상×9fps=270프레임 → 54~108초/분석. RunPod 위임 응답(202)은 즉시지만, 사용자 결과 화면 대기 시간이 길어짐
**Why it happens:** Heavy는 더 큰 모델 (~26MB) + 더 많은 연산.
**How to avoid:**
- D-15 ④ 회귀 검증에서 측정. SLA 초과 시 옵션: (a) Full로 다운그레이드 (정확도 트레이드오프), (b) GPU CPU 모두 가능 — Heavy도 GPU에서 30-60ms/frame, (c) target_fps 더 낮춤 (9→6).
- 본 phase에선 측정만. 대응은 deferred (CONTEXT.md: "병렬화·캐싱 전략 후속 검토").
**Warning signs:** `/analyze` 호출 후 결과 doc `done` 상태까지 60초+.

### Pitfall 6: NLF 격리 후 기존 reference angles 무효화
**What goes wrong:** `reference/{motionId}.angles`가 NLF 추출치인데 신규 사용자 분석은 MediaPipe 기반 → mode1 비교(motion_dtw)에서 두 다른 엔진 결과를 비교 → 점수 신뢰성 떨어짐
**Why it happens:** 두 엔진 좌표 정확도·noise 특성 다름.
**How to avoid:**
- 권장: **회귀 검증에서 reference 5개도 MediaPipe로 재추출**(원하는 효과 = "사용자도 MediaPipe, reference도 MediaPipe" 일관성). 새 `extract_reference_angles.py` MediaPipe 버전 작성 후 `app/scripts/seed-reference-motions.mjs`로 reseed.
- Phase 14 재캡처와 별개 — 단순 재추출은 같은 영상으로 가능.
**Warning signs:** atomic swap 후 같은 정은지 영상 self-comparison 점수가 NLF 시절보다 크게 다름.

### Pitfall 7: docs/contract.md lockstep 누락
**What goes wrong:** `analysis.ts` + `models.py`만 갱신하고 `docs/contract.md` 빠뜨림. 다음 contract 변경 작업자가 stale 문서 참조 → 새 필드 누락
**Why it happens:** CLAUDE.md의 "single source of truth for the API contract" 룰 — 세 곳 동시 변경 강제.
**How to avoid:** PR/Plan에 세 파일 모두 명시. 코드 리뷰 시 lockstep 확인. CLAUDE.md "Cross-cutting" 섹션 인용.

## Code Examples

### Example 1: MediaPipe PoseLandmarker VIDEO 모드 + Heavy 모델 [CITED: ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python]

```python
# backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_engine.py

from __future__ import annotations
import os
from pathlib import Path
import numpy as np

from ..interfaces import NoHumanError
from ..pose_frame import PoseFrame, PoleAxis  # 새 모듈
from ..adapters.mediapipe_to_coco17 import convert_landmarks_to_coco17_and_pole_ext


class MediaPipePoseEngine:
    """MediaPipe Tasks API (PoseLandmarker, Heavy variant, VIDEO 모드) 어댑터.

    D-01: BlazePose Heavy
    D-02: Tasks API (.task 모델)
    D-03: world landmarks + image landmarks 둘 다 출력
    D-04: 원본 33 전체 저장 + COCO-17 변환은 adapter에 위임
    D-05: confidence = visibility × presence, uncertainty_proxy = 1 - confidence
    """

    def __init__(
        self,
        model_path: str | None = None,
        target_fps: float = 9.0,
    ) -> None:
        # 무거운 import (lazy — Lambda 폴백 경로 회피)
        import mediapipe as mp

        self._mp = mp
        path = model_path or os.environ.get("MEDIAPIPE_POSE_MODEL_PATH")
        if path is None or not Path(path).exists():
            raise RuntimeError(
                f"pose_landmarker_heavy.task 모델 파일 없음: {path}. "
                "MEDIAPIPE_POSE_MODEL_PATH env 또는 명시적 경로 필요."
            )

        BaseOptions = mp.tasks.BaseOptions
        VisionRunningMode = mp.tasks.vision.RunningMode
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=path),
            running_mode=VisionRunningMode.VIDEO,
            num_poses=1,                          # 단독 동작 분석
            min_pose_detection_confidence=0.5,    # 기본값 — 튜닝 가능
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,      # 사용 안 함 — 메모리 절약
        )
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self._target_fps = target_fps

    def estimate(
        self,
        frames: np.ndarray,
        pole_axis: PoleAxis,
    ) -> list[PoseFrame]:
        """(T,H,W,3) RGB uint8 → List[PoseFrame] (length T). 미감지 시 NoHumanError."""
        mp = self._mp
        T = len(frames)
        pose_frames: list[PoseFrame] = []
        any_detection = False

        for t, frame_np in enumerate(frames):
            # VIDEO 모드: timestamp_ms는 단조 증가 (Pitfall 2)
            timestamp_ms = int(t * 1000 / self._target_fps)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_np)
            result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

            if not result.pose_landmarks or not result.pose_world_landmarks:
                # 미감지 — temporal_fill이 인접 프레임에서 메움
                pose_frames.append(PoseFrame.empty(
                    frame_index=t, timestamp_ms=timestamp_ms
                ))
                continue

            any_detection = True
            # 33 raw landmarks (D-04: 원본 보존)
            image_lm = result.pose_landmarks[0]   # normalized 0~1 image 좌표
            world_lm = result.pose_world_landmarks[0]  # 미터, hip-midpoint 원점

            # adapter: 33 → COCO-17 + 폴 확장 + confidence(=vis×pres) 계산
            pose_frame = convert_landmarks_to_coco17_and_pole_ext(
                frame_index=t,
                timestamp_ms=timestamp_ms,
                world_landmarks=world_lm,
                image_landmarks=image_lm,
                pole_axis=pole_axis,  # alignment를 adapter 내부에서 수행
            )
            pose_frames.append(pose_frame)

        if not any_detection:
            raise NoHumanError("영상 전체에서 사람을 찾지 못했습니다 (MediaPipe).")

        return pose_frames
```

### Example 2: Hough Line Transform 폴 검출 [CITED: docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html]

```python
# backend/shared/python/sunity_shared/analysis/pole/detector.py

from __future__ import annotations
import math
import numpy as np
import cv2


VERTICAL_TOLERANCE_DEG = 5.0
CANNY_LOW = 50
CANNY_HIGH = 200
HOUGH_RHO = 1
HOUGH_THETA = np.pi / 180
HOUGH_THRESHOLD = 80
HOUGH_MIN_LINE_LENGTH = 100  # 640px 기준 — 가변
HOUGH_MAX_LINE_GAP = 20


class HoughPoleDetector:
    """수직 prior + Hough Line Transform 기반 폴 축 검출 (D-09, D-10, D-11).

    영상 전체 평균 축 1개 산출 (D-10). 검출 실패 시 수직 가정 폴백 (D-11).
    """

    def detect(self, frames: np.ndarray) -> 'PoleAxis':
        """(T,H,W,3) RGB → PoleAxis. confidence 가중평균."""
        from ..pose_frame import PoleAxis

        directions = []
        confidences = []
        for frame_rgb in frames:
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, CANNY_LOW, CANNY_HIGH, apertureSize=3)
            lines = cv2.HoughLinesP(
                edges, HOUGH_RHO, HOUGH_THETA, HOUGH_THRESHOLD,
                minLineLength=HOUGH_MIN_LINE_LENGTH,
                maxLineGap=HOUGH_MAX_LINE_GAP,
            )
            if lines is None:
                continue
            # 수직 필터링 + 길이 가중
            h = frame_rgb.shape[0]
            for line in lines:
                x1, y1, x2, y2 = line[0]
                dx, dy = x2 - x1, y2 - y1
                angle_deg = math.degrees(math.atan2(abs(dy), abs(dx)))
                # 수직 = 90°에 가까움
                if abs(angle_deg - 90.0) > VERTICAL_TOLERANCE_DEG:
                    continue
                length = math.hypot(dx, dy)
                if length < HOUGH_MIN_LINE_LENGTH:
                    continue
                # 2D 방향 vector (image 좌표) — 항상 y+ 쪽으로 정규화
                vy = abs(dy)
                vx = math.copysign(abs(dx), dx)
                norm = math.hypot(vx, vy)
                directions.append((vx / norm, vy / norm))
                confidences.append(min(length / h, 1.0))

        if not directions:
            # D-11 폴백: 수직 가정
            return PoleAxis(
                direction3D=(0.0, 1.0, 0.0),  # image y+ = 수직 (2D 가정)
                confidence=0.3,
                source='vertical_fallback',
            )

        # confidence 가중평균
        dirs = np.array(directions)        # (N, 2)
        weights = np.array(confidences)
        avg_dir = (dirs * weights[:, None]).sum(axis=0) / weights.sum()
        avg_dir /= np.linalg.norm(avg_dir)
        # 2D image 방향 → 3D camera 좌표 가정 (z=0, 카메라 roll≈0)
        # 더 엄밀한 처리는 §Pitfall 3 참조
        return PoleAxis(
            direction3D=(float(avg_dir[0]), float(avg_dir[1]), 0.0),
            confidence=float(min(weights.mean(), 1.0)),
            source='hough',
        )
```

### Example 3: scipy로 폴 축 → Z 축 회전행렬 [CITED: docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.align_vectors.html]

```python
# backend/shared/python/sunity_shared/analysis/pole/aligner.py

from __future__ import annotations
import numpy as np
from scipy.spatial.transform import Rotation


TARGET_AXIS = np.array([0.0, 0.0, 1.0])  # 수직 = Z+


def compute_alignment_matrix(pole_axis_direction: tuple[float, float, float]) -> np.ndarray:
    """폴 축 → Z 축 정렬 회전행렬 (3x3). scipy의 align_vectors 사용 (edge case 처리됨)."""
    pole = np.array(pole_axis_direction, dtype=float)
    pole /= np.linalg.norm(pole)
    rot, _rssd = Rotation.align_vectors([TARGET_AXIS], [pole])
    return rot.as_matrix()


def apply_alignment(keypoints3D: dict[str, dict], R: np.ndarray) -> dict[str, dict]:
    """모든 키포인트에 회전행렬 R 적용 → pole-aligned 좌표."""
    aligned = {}
    for name, kp in keypoints3D.items():
        v = np.array([kp['x'], kp['y'], kp['z']])
        v_aligned = R @ v
        aligned[name] = {'x': float(v_aligned[0]), 'y': float(v_aligned[1]), 'z': float(v_aligned[2])}
    return aligned
```

### Example 4: 회귀 비교 스크립트 골격

```python
# backend/research/evaluations/compare_engines.py

"""MediaPipe vs NLF 회귀 검증 (D-13, D-14, D-15).

사용: python -m backend.research.evaluations.compare_engines \
        --motions ref-sideway-spin ref-climb ref-invert ref-foxtop ref-foxtop-split \
        --out backend/research/evaluations/reports/compare_2026XXXX.json
"""

from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from dataclasses import dataclass


@dataclass
class EngineResult:
    overall_score: int
    dimension_scores: dict[str, int]
    top3_failures: list[str]                # joint key 또는 finding key
    avg_keypoint_confidence: float
    ms_per_frame: float


def run_engine(engine_name: str, video_path: str) -> EngineResult:
    """sunity_shared 파이프라인 + 엔진 선택. 다운스트림은 동일."""
    # ... pipeline._process 와 동일하나 PoseEngine만 교체
    ...


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--motions', nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()

    results = {}
    for motion_id in args.motions:
        video = f"s3://sunity-motion-pilot-videos/reference/{motion_id}.mp4"
        mp_res = run_engine('mediapipe', video)
        nlf_res = run_engine('nlf', video)
        score_gap = mp_res.overall_score - nlf_res.overall_score
        top3_overlap = len(set(mp_res.top3_failures) & set(nlf_res.top3_failures))
        results[motion_id] = {
            'mediapipe': mp_res.__dict__,
            'nlf': nlf_res.__dict__,
            'score_gap': score_gap,
            'within_tolerance_5pt': abs(score_gap) <= 5,                         # D-14
            'mediapipe_score_ge_70': mp_res.overall_score >= 70,                 # D-15 ①
            'top3_overlap_2_of_3': top3_overlap >= 2,                            # D-15 ②
            'avg_confidence_ok': mp_res.avg_keypoint_confidence >= 0.5,         # D-15 ③ (임계값 belle와 확정)
            'mediapipe_ms_per_frame': mp_res.ms_per_frame,                       # D-15 ④
            'nlf_ms_per_frame': nlf_res.ms_per_frame,
        }

    payload = {
        'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'criteria': {
            'score_tolerance_pt': 5,                                             # D-14
            'min_mediapipe_score': 70,                                           # D-15 ①
            'min_top3_overlap': 2,                                               # D-15 ②
        },
        'results': results,
        'summary': {
            'all_within_tolerance': all(r['within_tolerance_5pt'] for r in results.values()),
            'all_mediapipe_ge_70': all(r['mediapipe_score_ge_70'] for r in results.values()),
            'all_top3_overlap_ok': all(r['top3_overlap_2_of_3'] for r in results.values()),
            'phase1_ready_to_swap': all([
                all(r['within_tolerance_5pt'] for r in results.values()),
                all(r['mediapipe_score_ge_70'] for r in results.values()),
                all(r['top3_overlap_2_of_3'] for r in results.values()),
            ]),  # D-16: 모두 PASS여야 atomic swap
        },
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    # Markdown 요약 생성 (사람용)
    md = generate_markdown_report(payload)
    args.out.with_suffix('.md').write_text(md)


if __name__ == '__main__':
    main()
```

### 회귀 보고서 포맷 권장 (JSON + Markdown)

- **JSON:** 위 코드 출력 — 자동 비교/CI 통합.
- **Markdown:** belle 사람 검토용. 각 motion_id 표 + summary 표 + PASS/FAIL 게이트 + 추론 속도 비교 그래프(텍스트 ASCII bar 또는 별도 PNG는 옵션).

## NLF 격리 — atomic swap 대상 코드 라인

| File | Line | Current | Change |
|------|------|---------|--------|
| `backend/functions/pipeline/app.py` | 131 | `from sunity_shared.analysis.pose_estimator import NlfPoseEstimator` | `from sunity_shared.analysis.pose_engines.mediapipe_engine import MediaPipePoseEngine` |
| `backend/functions/pipeline/app.py` | 132 | `_POSE_ESTIMATOR = NlfPoseEstimator()` | `_POSE_ESTIMATOR = MediaPipePoseEngine(model_path=os.environ.get("MEDIAPIPE_POSE_MODEL_PATH"))` |
| `backend/functions/pipeline/app.py` | 146-153 | `_angles_from_video()` — 기존 흐름 | PoseEngine.estimate(frames, pole_axis) + adapter 호출 + temporal_fill 흐름으로 갱신. 또는 `_POSE_ENGINE`을 통해 PoseFrame 리스트 → COCO-17 array 헬퍼 거쳐 기존 compute_joint_angles 그대로 |
| `backend/runpod_inference/server.py` | (전체) | pipeline 모듈 그대로 import | **변경 없음** — `_process` 재사용. RunPod requirements.txt만 갱신 |
| `backend/runpod_inference/requirements.txt` | 전체 | `ultralytics`, (PyTorch from base) | 추가: `mediapipe==0.10.35`, `opencv-python-headless==4.13.0.92`, `scipy>=1.17,<2.0`. 제거: `ultralytics` (NLF용이었음 — backend/research에서만 필요시 별도 설치) |
| `backend/scripts/extract_reference_angles.py` | (전체) | NLF로 reference 추출 | 2개로 분기 가능: (a) 같은 위치에 MediaPipe 버전 작성 (제품 reference 재추출용), (b) NLF 버전은 `backend/research/evaluations/extract_reference_angles_nlf.py`로 이동 |
| `backend/scripts/verify_nlf_pipeline.py` | (전체) | NLF 단독 검증 | `backend/research/evaluations/verify_nlf_pipeline.py`로 이동 (이름 그대로 — NLF임이 명백) |
| `backend/scripts/verify_self_comparison.py` | 207, 79 | `NlfPoseEstimator` import | 옵션 1: MediaPipe로 교체 + 위치 유지. 옵션 2: NLF 버전은 backend/research로 이동 + MediaPipe 버전 새로 작성. **권장: 옵션 2** (회귀 검증 D-13 핵심 도구이므로 두 엔진 모두 verify_self_comparison이 필요) |
| `backend/shared/python/sunity_shared/analysis/pose_estimator.py` | (전체 파일) | NlfPoseEstimator + COCO17 SMPL 매핑 + lazy import | **파일 자체를 `backend/research/pose_engines/nlf/nlf_engine.py`로 이동**. sunity_shared 패키지에서 사라짐 (D-06, D-07 격리) |
| `backend/scripts/nlf_l_multi.torchscript` | — | NLF 모델 파일 | `backend/research/pose_engines/nlf/models/nlf_l_multi.torchscript`로 이동 |
| `backend/yolo11n.pt` | — | YOLO11 weights (NLF 전용) | `backend/research/pose_engines/nlf/models/yolo11n.pt`로 이동 (NLF 격리에 포함) |

## 모델 파일 배포 권장 (`pose_landmarker_heavy.task`)

| 옵션 | Pros | Cons | 권장 |
|------|------|------|------|
| Lambda 레이어 (~26MB) | 콜드스타트 즉시 사용 가능 | Lambda 250MB unzipped 한도 — 다른 deps와 합쳐 봐야 함. ARM64 wheel 부재로 어차피 Lambda에서 못 돎 | ❌ |
| RunPod base image에 포함 (Dockerfile WORKDIR) | 콜드스타트 빠름. 환경 일관성 | Pod 재생성마다 이미지 빌드 | ⭕ (Pod base image가 stable하면) |
| RunPod Pod 부팅 시 setup.sh로 wget | 이미지 가볍게 유지 | Pod 생명주기 수동 — belle 메모 일치. 부팅 시간 +몇 초 | ⭕ (현 워크플로 일관, **권장**) |
| S3 다운로드 (런타임) | 모델 버전 관리 쉬움 | 첫 분석에 +5~10초 (26MB 다운로드) | △ (덜 자주 변경) |

**권장:** RunPod Pod 부팅 시 setup.sh에서 wget. URL: `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task` [CITED: ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker]. env: `MEDIAPIPE_POSE_MODEL_PATH=/workspace/models/pose_landmarker_heavy.task`. 모델 파일 size ~26MB [VERIFIED: google cloud storage public link, 다중 소스 일치].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MediaPipe Solutions (legacy) `mp.solutions.pose` | MediaPipe Tasks API `mp.tasks.vision.PoseLandmarker` | 2023~ (Tasks API GA) | Solutions deprecated 예고. Tasks API는 명시적 .task 모델 + RunningMode + 더 일관된 API |
| BlazePose 3D (legacy) | BlazePose GHUM 3D (Heavy/Full/Lite) | 2021~ | GHUM(GHUM Body) 모델로 더 정확한 3D + world landmarks |
| NLF + SMPL-X (NeurIPS 2024) — 제품 사용 | MediaPipe Heavy — 제품 사용. NLF는 R&D 비교군 격리 | 2026-05-31 belle 결정 | 라이선스 리스크 0 + GPU 의존 제거 + Lambda CPU 가능 (architecture 조정 필요) |
| Lambda CPU 폴백 + RunPod GPU 운영 | Lambda 폴백 비활성화 (또는 fail-fast) + RunPod CPU 충분 | Phase 1 swap 후 | RunPod GPU 다운사이즈 옵션 발생 (deferred) |

**Deprecated/outdated:**
- `mediapipe.solutions.pose` (legacy API): D-02 결정 — 사용 안 함
- NLF/SMPL-X in production: D-08 결정 — atomic swap 후 R&D만
- COCO-17 only 저장: D-04 결정 — 원본 33도 함께 저장

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MediaPipe 33 → COCO-17 매핑 (특히 eye/ear) — 명칭 기반 추론 | Pattern 3 표 | 일부 매핑이 잘못되면 각도 계산 정확도 떨어짐. **플래너가 MediaPipe 공식 docs로 수동 검증 권장** (현재까진 명확한 official 매핑 테이블 미발견) |
| A2 | BlazePose Heavy 추론 속도 "200~400ms/frame" (belle 추정치 그대로 인용) | CONTEXT.md D-01 | 실측치 차이 시 SLA·운영 비용 영향. D-15 ④에서 측정 — 실측 확정 |
| A3 | mediapipe와 firebase-admin protobuf 버전 충돌 가능성 | Pitfall 4 | 충돌하지 않으면 단순. 충돌 시 protobuf 버전 명시 필요 |
| A4 | scipy 추가 ~30MB가 RunPod 환경에 영향 없음 (Pod 디스크 여유 충분) | Standard Stack alternatives | Pod 디스크 부족 시 numpy로 직접 Rodrigues 구현 필요 |
| A5 | RunPod Pod x86_64 base image 사용 — mediapipe wheel 호환 | Standard Stack Lambda 경고 | Pod이 ARM64면 mediapipe wheel 없음 — belle와 Pod arch 확인 필요 |
| A6 | World landmarks → image 픽셀 폴 축 변환에서 카메라 roll≈0 가정 | Pitfall 3 | 카메라가 기울어졌으면 alignment 오차. D-11 폴백("카메라 기울어져 세부 각도 해석에 주의")이 일부 보완 |
| A7 | mediapipe 0.10.35 Python 3.12 호환 ([CITED: pypi]) — Lambda(3.12)/RunPod 모두 OK | Standard Stack | RunPod base가 다른 Python 버전이면 wheel 호환 재확인 |
| A8 | `cv2.HoughLinesP` 권장 초기값 (threshold=80, minLineLength=100 등) | Hough 권장 파라미터 | 초기값 — 정은지 5영상으로 sweep 후 확정. 검출 실패 시 D-11 폴백으로 graceful |
| A9 | 'avg_confidence_ok' 임계값 0.5 (D-15 ③) — 분명한 belle 확정값 부재 | Code Example 4 | belle와 임계값 확정 필요 (e.g., 0.5? 0.6? 0.7?). 현재는 placeholder |
| A10 | "grip"용 손가락 (pinky/index/thumb) 평균이 손 중심으로 충분 | Pole 확장 매핑 | 폴 그립 분석은 v1.5 가까이 — 본 phase는 데이터 저장만, 분석 사용은 후속 |

**Phase 1 시작 전 belle 확정 권장:**
- A1: MediaPipe 매핑 공식 docs 검증 또는 belle 승인
- A2: 정은지 5영상 추론 속도 실측 후 SLA 확인
- A9: avg_keypoint_confidence 임계값

## Open Questions

1. **`backend/research/`가 SAM 빌드에 포함되지 않음을 보장하는 방법**
   - What we know: SAM `ContentUri: shared/` (template.yaml line 63) — 레이어 빌드는 `backend/shared/` 만 포함. `backend/research/`는 자연스럽게 제외됨.
   - What's unclear: `samconfig.toml`이나 `.samignore`로 명시적 차단 필요한지.
   - Recommendation: 명시적 `.samignore`에 `research/` 추가 (방어적). 빌드 결과물(`.aws-sam/build/`)에 NLF 모듈이 안 들어가는지 spot-check.

2. **Lambda 폴백 경로의 실질적 처리 방식 — fail-fast vs MediaPipe x86_64 Container Image**
   - What we know: 현재 Lambda 폴백은 NLF NaN 발산으로 작동 안 함. D-08 + ARM64 wheel 부재로 Lambda에서 MediaPipe 직접 추론 불가.
   - What's unclear: belle가 fail-fast OK인지, 아니면 Lambda Container Image 전환을 원하는지.
   - Recommendation: Phase 1은 fail-fast (RUNPOD env 미설정 → ConfigurationError + 명확한 로그). Container Image 전환은 별 phase에서 별도 결정.

3. **MediaPipe Pod CPU 추론 속도가 SLA 초과 시 즉시 대응 vs deferred**
   - What we know: D-15 ④에서 측정만. Belle 톤은 "정확도 우선, 비용 하한 = 구독료 수준".
   - What's unclear: 사용자가 결과를 1분~2분 기다리는 게 acceptable한지 (Mode 3는 두 분석 필요 → 누적).
   - Recommendation: 실측 후 belle와 짧게 합의. SLA 초과 시 Phase 1 종료 보류 (D-16) — 또는 Full variant로 즉시 다운그레이드.

4. **A1 (MediaPipe → COCO-17 매핑) 공식 출처**
   - What we know: 명칭 기반 매핑은 합리적. 단 official mapping 테이블 미발견.
   - Recommendation: 플래너가 MediaPipe 샘플 코드(github.com/google-ai-edge/mediapipe-samples) 또는 mediapipe holistic landmark enum source code에서 정확한 enum 확인. 핵심 위험은 코·눈·귀 (5점) — JOINT_ANGLES에 안 쓰이지만 PoseFrame.rawLandmarks33에는 저장됨.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Lambda/RunPod 분석 코드 | ✓ (Lambda runtime) | 3.12 | — |
| numpy | 기존 분석 코어 | ✓ | 1.26+ | — |
| imageio + imageio-ffmpeg | frame_extractor | ✓ | 2.34+ / 0.5.1+ | — |
| boto3 | S3 다운로드 | ✓ (Lambda 런타임 / Pod) | 1.34+ | — |
| firebase-admin | Firestore | ✓ | 6.5~7.0 | — |
| **mediapipe (NEW)** | MediaPipePoseEngine | ✗ → 설치 필요 | 0.10.35 | **Lambda ARM64 호환 wheel 없음** — RunPod 서버 위 (x86_64 가정)에서만 |
| **opencv-python-headless (NEW)** | HoughPoleDetector | ✗ → 설치 필요 | 4.13.0.92 | ARM64 wheel 있음 (RunPod·Lambda 모두 OK) |
| **scipy (NEW)** | PoleAxisAligner align_vectors | ✗ → 설치 필요 | 1.17.1 | ARM64 wheel 있음 |
| Docker Desktop | sam build --use-container | △ (belle 로컬에 있어야 함) | latest | belle 환경 — 메모리 일치 |
| RunPod GPU Pod | 운영 추론 환경 | ✓ (이미 운영 중) | x86_64 base | Pod 재생성 시 setup.sh로 mediapipe·model 자동 설치 |
| GPU (CUDA) | NLF 평가 (R&D만) | ✓ (RunPod Pod) | — | MediaPipe는 GPU 불필요 |
| **pose_landmarker_heavy.task** | MediaPipe Heavy 추론 | ✗ → wget 필요 | float16 latest | https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task |

**Missing dependencies with no fallback:**
- 없음 — 위 모든 항목 설치 가능

**Missing dependencies with fallback:**
- Lambda ARM64 mediapipe → Lambda 폴백 비활성화(fail-fast) 또는 x86_64 Container Image (별 phase)

## Validation Architecture

> nyquist_validation enabled (config.json `workflow.nyquist_validation: true` 확인)

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8 (이미 의존 — `backend/requirements-dev.txt`) |
| Config file | 없음 (`pytest` 기본). `backend/tests/conftest.py` 존재 |
| Quick run command | `cd backend && pytest tests/ -x` |
| Full suite command | `cd backend && pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POSE-01 | PoseEngine Protocol 정의 + MediaPipePoseEngine.estimate() 반환 shape/타입 | unit | `pytest backend/tests/test_pose_engine_interface.py -x` | ❌ Wave 0 |
| POSE-01 | MediaPipe33ToCOCO17Adapter 17 키포인트 정확 추출 + 폴 확장 (toe/heel/grip) | unit | `pytest backend/tests/test_adapter_mediapipe_to_coco17.py -x` | ❌ Wave 0 |
| POSE-01 | NoHumanError 발생 (전 프레임 미감지 mock) | unit | `pytest backend/tests/test_pose_engine_interface.py::test_no_human -x` | ❌ Wave 0 |
| POSE-01 | NLF 격리 — `from sunity_shared.analysis.pose_engines.nlf` ImportError | unit (구조 검증) | `pytest backend/tests/test_nlf_isolation.py -x` | ❌ Wave 0 |
| POSE-01 | pipeline._process MediaPipe 경로로 동작 (mock PoseEngine) | integration | `pytest backend/tests/test_pipeline_dispatch.py -x` | ✅ 존재 — MediaPipe mock 추가 필요 |
| POSE-02 | HoughPoleDetector.detect() 수직 폴 영상에서 PoleAxis 반환 | unit | `pytest backend/tests/test_pole_detector.py -x` | ❌ Wave 0 |
| POSE-02 | HoughPoleDetector 검출 실패 시 PoleAxis(source='vertical_fallback', confidence='low') | unit | `pytest backend/tests/test_pole_detector.py::test_fallback -x` | ❌ Wave 0 |
| POSE-02 | PoleAxisAligner.align() 회전행렬 적용 + 항등성 (이미 Z 축이면 변경 없음) | unit | `pytest backend/tests/test_pole_aligner.py -x` | ❌ Wave 0 |
| POSE-02 | confidence (= visibility×presence) 변환식 정확 + 임계값 미만 프레임 표기 | unit | `pytest backend/tests/test_pose_engine_interface.py::test_confidence_conversion -x` | ❌ Wave 0 |
| Success #5 (회귀) | compare_engines.py가 5영상 처리 + JSON 출력 + summary.phase1_ready_to_swap 계산 | manual + script | `python -m backend.research.evaluations.compare_engines --motions ...` (RunPod에서 NLF 측 필요 → smoke test는 mock 가능) | ❌ Wave 0 |
| Success #6 (lockstep) | TS PoseFrame ↔ Python PoseFrame field 일치 (수동 grep) | manual | `grep "interface PoseFrame" app/src/types/analysis.ts && grep "class PoseFrame\|PoseFrame =" backend/shared/python/sunity_shared/models.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/ -x` (현재 ~20개 테스트, MediaPipe 어댑터 단위 테스트 추가 시 +5-10개)
- **Per wave merge:** 같은 전체 suite
- **Phase gate:** 전체 suite 통과 + `compare_engines.py` 실행 + summary.phase1_ready_to_swap == true (D-13~D-16)

### Wave 0 Gaps
- [ ] `backend/tests/test_pose_engine_interface.py` — PoseEngine Protocol + MediaPipePoseEngine 단위 (mock mediapipe library 사용 — 실 모델 무거움)
- [ ] `backend/tests/test_adapter_mediapipe_to_coco17.py` — 33→17 + 폴 확장 변환 정확성 (fixture 데이터)
- [ ] `backend/tests/test_pole_detector.py` — HoughPoleDetector 정상·실패 케이스 (synthetic 영상 fixture)
- [ ] `backend/tests/test_pole_aligner.py` — 회전행렬 적용 (numerical 테스트)
- [ ] `backend/tests/test_nlf_isolation.py` — `import` 시 ImportError (구조 검증)
- [ ] `backend/tests/fixtures/` — 작은 synthetic frames (~3 frames, 64x64) — MediaPipe 호출 없이 어댑터/변환 테스트
- [ ] `backend/research/evaluations/compare_engines.py` (Code Example 4 기반)
- [ ] 기존 `test_pipeline_dispatch.py`에 MediaPipe mock case 추가

*Framework install: 이미 설치됨 (pytest>=8 in requirements-dev.txt). MediaPipe·OpenCV·scipy는 `backend/runpod_inference/requirements.txt`에 추가 (Pod용). 로컬 테스트는 mock 사용 (mediapipe 무거우니 import 시 mock으로 대체).*

## Security Domain

> `security_enforcement: true` (config.json) — ASVS Level 1

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | RunPod `X-RunPod-Token` shared secret (이미 구현 — `runpod_inference/server.py:_verify_token`). 변경 없음 |
| V3 Session Management | no | 분석 파이프라인은 비동기 — 세션 없음 |
| V4 Access Control | yes | Firestore security rules `users/{uid}/analyses/{id}` 사용자별 격리 (이미 구현). Phase 1 변경 없음 |
| V5 Input Validation | yes | S3 키 파싱 (`parse_upload_key`, 이미 구현). PoleAxis confidence 범위 검증 추가 권장 (0~1) |
| V6 Cryptography | no | 새 암호화 사용처 없음 |
| V9 Communications | yes | RunPod TLS (Cloudflare proxy — 이미 구현). 변경 없음 |
| V10 Malicious Code | yes | **새 패키지 3개 (mediapipe·opencv·scipy) 모두 slopcheck [OK] + 공식 조직 패키지** (§Package Legitimacy Audit) |
| V11 Business Logic | yes | "고객 리포트에 기술 용어 노출 금지" (D-05 정책) — Phase 1은 데이터 계약만 — 표시 phase에서 검증 |
| V14 Configuration | yes | `MEDIAPIPE_POSE_MODEL_PATH` env 신규 — Parameter Store 또는 Pod env에 명시 |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 악성 모델 파일 (poison `pose_landmarker_heavy.task`) | Tampering | 공식 Google CDN URL (storage.googleapis.com)에서만 다운로드. SHA256 hash 검증 권장 (Google이 공식 hash 제공) |
| MediaPipe wheel hijack (Typosquat e.g. `medipipe`) | Tampering | slopcheck `[OK]` 확인 (이미 수행). pip 설치 시 exact name `mediapipe` |
| OpenCV CVE | Tampering | 4.13.0.92 = 최신. CVE 추적은 dependabot 또는 별 phase |
| Adversarial input video → MediaPipe DoS | DoS | Lambda 폴백 fail-fast + RunPod timeout. 영상 100MB 한도 (이미 enforce) |
| Pole 검출 결과 user-controlled trust (사용자가 영상 조작 → 잘못된 axis) | Spoofing | confidence='low' 표기 + 사용자 친화 카피. 점수 영향은 안내 |

## Sources

### Primary (HIGH confidence)
- `pypi.org/project/mediapipe/` — version 0.10.35, Python 3.9~3.12, platform tags (x86_64 only Linux), Apache 2.0 — [https://pypi.org/project/mediapipe/](https://pypi.org/project/mediapipe/)
- `ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python` — PoseLandmarker Python API, VIDEO mode, configuration options — [https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python)
- `ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker` — BlazePose 33 landmark layout, model variants, download URLs — [https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
- `docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html` — HoughLinesP signature, Canny preprocessing — [https://docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html](https://docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html)
- `docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.align_vectors.html` — align_vectors API + edge case — [https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.align_vectors.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.align_vectors.html)
- 기존 코드베이스 (verified by direct file read): `backend/shared/python/sunity_shared/analysis/{interfaces,pose_estimator,skeleton,temporal,features,frame_extractor}.py`, `backend/functions/pipeline/app.py`, `backend/runpod_inference/server.py`, `backend/template.yaml`, `app/src/types/analysis.ts`, `backend/shared/python/sunity_shared/models.py`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md` — belle 결정 16건 (D-01~D-16)
- `docs/research/00_시스템_아키텍처_FINAL.md` §1·§3·§4 — 마스터 아키텍처, 공통 계약, 두 모드 분기
- `docs/research/01_체형차이_보정엔진_FINAL.md` §0.7·§4.3·§5.2 — 포즈 엔진 라이선스/리스크, PoseFrame 스키마 진화 기원
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §0.7 — occlusion 리스크, 다중 시점 권장
- `CLAUDE.md` (프로젝트 + /app) — 인프라 분리, 데이터 계약 lockstep, Firestore nested-array 금지, SAM 빌드 함정, 라이트 테마

### Secondary (MEDIUM confidence)
- `pypi.org/project/opencv-python-headless/` — 4.13.0.92, ARM64 manylinux2014_aarch64 33.7MB
- `github.com/google-ai-edge/mediapipe/issues/5965` — Linux ARM64 wheel 미지원 공식 인지 (unresolved) — [https://github.com/google-ai-edge/mediapipe/issues/5965](https://github.com/google-ai-edge/mediapipe/issues/5965)
- `storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf` — Heavy ~26MB
- `developers.google.com/mediapipe/solutions/vision/pose_landmarker/python` — VIDEO mode + detect_for_video monotonic timestamps

### Tertiary (LOW confidence — needs validation)
- MediaPipe 33→COCO-17 매핑 표 (§Pattern 3) — 명칭 기반 추론, 공식 매핑 테이블 미발견. A1 assumption. 플래너가 mediapipe samples github에서 검증 권장
- `brndusic.github.io/aws/2021/12/31/running-mediapipe-on-aws-lambda.html` — AWS Lambda MediaPipe 배포 사례 (2021, 오래됨 — 참고만)
- `businesscompassllc.com/scaling-media-processing-deploying-mediapipe-on-aws-lambda-with-docker/` — Container Image 배포 가이드 (검증 안 함)
- BlazePose Heavy "200~400ms/frame" 추정치 — belle 추정. A2 — D-15 ④에서 실측

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyPI verified, slopcheck OK, version·age·downloads 모두 강한 signal
- Architecture (PoseEngine·Adapter·PoleDetector 패턴): HIGH — 기존 코드 결을 따름 + 공식 docs 일치
- Pole 좌표계 변환 수학: HIGH (scipy align_vectors는 공식 검증) — 단 image→camera 좌표 변환에 카메라 roll≈0 가정(A6)이 약한 부분
- MediaPipe 33→COCO-17 매핑: MEDIUM-LOW — 명칭 기반 추론 (A1). 플래너 검증 필요
- Lambda 폴백 운영 전략: MEDIUM — ARM64 wheel 부재가 확정사실이라 fail-fast 권장이 자명하나, belle 확정 필요
- 회귀 검증 임계값 (avg_confidence): MEDIUM — D-15 ③ 임계값은 belle 확정 필요(A9)
- BlazePose Heavy Lambda CPU 추론 속도: LOW — 실측 없음, belle 추정치만(A2)
- Pitfalls: HIGH (특히 Pitfall 1 ARM64) — 공식 PyPI + GitHub issue 다중 검증

**Research date:** 2026-05-31
**Valid until:** 2026-06-14 (~2주). MediaPipe 0.10.x는 stable 시리즈. 단 ARM64 wheel issue가 해결되면 (PR #6172) 본 phase 핵심 결정(Lambda 폴백 fail-fast) 재검토 필요 — GitHub issue 추적 권장.
