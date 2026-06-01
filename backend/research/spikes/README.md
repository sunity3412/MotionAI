# Spike: MediaPipe 2D + MotionBERT 3D Lift

Plan 01-07 spike — ref-foxtop-split 1개 영상으로 MP+MotionBERT 조합이
NLF baseline 대비 stability 점수를 회복하는지 검증한다.

## 라이선스

| 라이브러리 | 라이선스 | 출처 |
|-----------|---------|------|
| MotionBERT | Apache 2.0 | https://github.com/Walter0807/MotionBERT/blob/main/LICENSE |
| HybrIK (백업 후보) | MIT | https://github.com/Jeff-sjtu/HybrIK/blob/main/LICENSE |
| GAST-Net (백업 후보) | MIT | https://github.com/fabro66/GAST-Net-3HPE |

MotionBERT 라이선스 확인 일자: 2026-05-31.
Apache 2.0 — 상업적 사용, 수정, 배포 모두 허용. 저작권 고지 필요.

## 배경

Plan 01-06 회귀 검증에서 MediaPipe avg_conf 0.79~0.89로 키포인트 검출 자체는
정확하지만, world_landmarks의 z 추정이 인버트/측면/폴 폐색 자세에서 노이즈가
커서 stability 차원이 NLF 대비 28~50점 깎였다.

| 모션 | MP stability | NLF stability |
|------|------------|-------------|
| ref-foxtop-split | 3 | 53 |
| ref-foxtop | 8 | 63 |
| ref-invert | 30 | 65 |
| ref-sideway-spin | 46 | 81 |
| ref-climb | 18 | 58 |

본 spike는 MediaPipe 2D 키포인트(신뢰도 높음)만 채용하고 z를 MotionBERT
(시간축 transformer, ICCV 2023, H3.6M pretrained)로 재구성해 stability 회복을
검증한다.

## 판정 기준

| 결과 | stability | overall | 다음 행동 |
|------|-----------|---------|---------|
| Strong pass | >= 55 | >= 60 | "approved, proceed to Plan 08" |
| Weak signal | 40~55 | 45~60 | "try HybrIK" |
| 실패 | < 40 | < 45 | "hold + reconsider path A" 또는 "hold + commercial license" |

현재 MP 단독: stability 3, overall 3.

## Pod 실행 절차

### 1. SunityMotion 저장소 최신화

```bash
cd /workspace/SunityMotion
git pull --ff-only origin main
```

### 2. MotionBERT clone (1회)

```bash
cd /workspace
git clone https://github.com/Walter0807/MotionBERT.git
```

### 3. 사전학습 가중치 다운로드 (1회, ~120MB)

MotionBERT inference 용 가중치는 **OneDrive** 에서 배포된다 (Google Drive 아님).

- 공식 inference 가이드: https://github.com/Walter0807/MotionBERT/blob/main/docs/inference.md
- OneDrive 폴더: https://1drv.ms/f/s!AvAdh0LSjEOlgT67igq_cIoYvO2y?e=bfEc73
- 다운로드 대상: **`FT_MB_lite_MB_ft_h36m_global_lite`** (Lite 버전 — MotionBERT 공식이 inference 에 권장. 정확도 거의 동일, 메모리/속도 가벼움)
- 배치 경로: `/workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/`

**RunPod Pod 에서 OneDrive 받는 방법** (둘 중 하나):

옵션 A — 브라우저에서 받아 scp:
```bash
# 로컬 머신에서 OneDrive 폴더 열고 FT_MB_lite_MB_ft_h36m_global_lite 디렉토리 통째로 다운로드.
# 그다음 belle 로컬 → Pod scp (Pod SSH 경로 확인):
scp -r FT_MB_lite_MB_ft_h36m_global_lite root@<pod-ip>:/workspace/MotionBERT/checkpoint/pose3d/
```

옵션 B — Pod 안에서 wget 직링크 (브라우저에서 한 번 클릭해 "직접 다운로드 URL" 추출):
```bash
mkdir -p /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite
cd /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite

# 1. 로컬 브라우저에서 OneDrive 폴더 열기:
#    https://1drv.ms/f/s!AvAdh0LSjEOlgT67igq_cIoYvO2y?e=bfEc73
# 2. 폴더 안에 best_epoch.bin 우클릭 → "Copy link" → 받은 URL 의 e1=... 부분을 download=1 로 바꿈
# 3. Pod 에서:
wget -O best_epoch.bin '<위에서 추출한 직접 다운로드 URL>'
```

확인:
```bash
ls -lh /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin
# ~120MB 이상이면 OK
```

가중치 파일은 git에 추적하지 않는다. `/workspace/` 경로에만 보관.

> **참고**: MotionBERT 공식 inference 워크플로우는 **AlphaPose** 2D keypoints 를 입력으로 받는다. 본 spike 는 그 자리를 MediaPipe 로 갈아끼우는 게 핵심 실험이라, MP→H3.6M 17-joint 매핑 어댑터(`mediapipe_to_h36m17.py`)가 spike 가설의 위험 지점이다. 결과가 weak signal 이면 AlphaPose 로 바꿔서 baseline 확인하는 게 다음 단계가 될 수 있다.

### 4. MotionBERT 의존성 설치

```bash
cd /workspace/MotionBERT
pip install -r requirements.txt
# 핵심 의존성: torch (Pod에 이미 설치), einops, timm
# torch는 RunPod base image에 포함 — requirements.txt에서 중복 설치 주의.
```

### 5. PYTHONPATH 설정 확인

```bash
export PYTHONPATH="/workspace/SunityMotion/backend/shared/python:/workspace/SunityMotion:$PYTHONPATH"
echo $PYTHONPATH
```

### 6. spike 실행

```bash
cd /workspace/SunityMotion

python3 -m backend.research.spikes.spike_motionbert \
  --motion ref-foxtop-split \
  --bucket sunity-motion-pilot-videos \
  --motionbert-root /workspace/MotionBERT \
  --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \
  --out backend/research/spikes/reports/spike_motionbert_$(date +%Y%m%d).json
```

실행 완료 후:
- `backend/research/spikes/reports/spike_motionbert_YYYYMMDD.json` — 상세 결과
- `backend/research/spikes/reports/spike_motionbert_YYYYMMDD.md` — Markdown 요약

### 7. 결과 보고

결과 파일을 Claude에 공유하고 다음 중 하나로 응답:

- "approved, proceed to Plan 08" — strong pass (stability >= 55, overall >= 60)
- "try HybrIK" — weak signal (stability 40~55)
- "hold + reconsider path A" — 실패 (stability < 40)
- "hold + commercial license" — Path D 전환

## 파일 목록

```
backend/research/spikes/
  __init__.py                  # 패키지 마커 (운영 import 경로 외부)
  mediapipe_to_h36m17.py       # MP33 → H3.6M 17 매핑 어댑터
  spike_motionbert.py          # 스파이크 하네스 (CLI 포함)
  README.md                    # 이 파일
  reports/
    .gitkeep                   # 보고서 디렉터리 (결과 파일은 gitignore)
    spike_motionbert_YYYYMMDD.json  # belle 실행 후 생성 (커밋 안 함)
    spike_motionbert_YYYYMMDD.md    # belle 실행 후 생성 (커밋 안 함)

backend/tests/
  test_spike_mediapipe_to_h36m17.py  # 매핑 어댑터 단위 테스트
```

## 로컬 테스트 (mediapipe 없이)

매핑 어댑터 단위 테스트는 mediapipe 없이 실행 가능:

```bash
cd /Users/kimtaesung/Dev/SunityMotion
PYTHONPATH=backend/shared/python:. pytest backend/tests/test_spike_mediapipe_to_h36m17.py -v
```

spike_motionbert.py 전체 실행은 RunPod GPU Pod에서만 가능 (mediapipe + torch CUDA 필요).

## 주의사항

- 가중치 파일(`best_epoch.bin`)은 git에 절대 커밋하지 않는다.
- 본 spike 코드는 `backend/research/spikes/` 내부에만 존재한다.
  운영 코드(`functions/`, `shared/`) import 경로를 침범하지 않는다.
- MotionBERT 의존성은 Pod 전용. Lambda에는 배포하지 않는다.

---

# Plan 10 — RTMPose 측면 자세 보강 spike (Apache 2.0)

> 본 섹션은 Plan 01-10 에서 추가됨. Plan 07/08 MotionBERT 섹션은 위쪽 그대로 보존.

## 배경 (Plan 10)

Plan 01-08 5영상 회귀 결과 — ref-sideway-spin (측면 자세) 만 overall 64 점으로
D-15① ≥70 게이트 fail. MotionBERT 가 H3.6M (대부분 정면 walking/sitting) 학습
이라 측면 z 복원이 약하다는 점은 알고 있었으나, 1차 가설은 **2D detector
단계가 측면에서 keypoint 분포가 좁아져 lift 가 어려워졌다**는 것.

- Plan 09 (AlphaPose spike) — 라이선스 Noncommercial Only 로 차단됨.
- **Plan 10 = belle 결정 (2026-06-01) option-b-1**: MMPose **RTMPose-l**
  (Apache 2.0, COCO 학습 — 정면/측면/occlusion 분포 더 균등) 로 2D detector
  교체 spike. MotionBERT lift 그대로 유지.

## 라이선스 (Plan 10 추가)

| 라이브러리 | 라이선스 | 확인 일자 | 출처 |
|---|---|---|---|
| MMPose | Apache 2.0 | 2026-06-01 | https://github.com/open-mmlab/mmpose/blob/main/LICENSE |
| mmengine | Apache 2.0 | 2026-06-01 | https://github.com/open-mmlab/mmengine/blob/main/LICENSE |
| mmcv | Apache 2.0 | 2026-06-01 | https://github.com/open-mmlab/mmcv/blob/main/LICENSE |
| mmdet | Apache 2.0 | 2026-06-01 | https://github.com/open-mmlab/mmdetection/blob/main/LICENSE |
| RTMPose-l 가중치 | Apache 2.0 | 2026-06-01 | https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth (MMPose project zoo) |

스택 전체 Apache 2.0 — 상업 파일럿 MVP 도입 가능. GitHub API license metadata
(`apache-2.0`) 도 확인.

## RTMPose-l 권장 checkpoint

| 항목 | 값 |
|---|---|
| Config 이름 | `rtmpose-l_8xb256-420e_coco-256x192` |
| Training 데이터 | AIC + COCO (combined) |
| 입력 해상도 | 256 x 192 |
| AP (COCO val) | 76.5 |
| 가중치 크기 | ~111 MB |
| 다운로드 URL | https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth |

Spike 실패 시 다음 후보:
- `rtmpose-l_8xb256-420e_coco-384x288` (해상도 ↑, AP 77.3)
- `rtmpose-l_8xb256-420e_aic-coco-256x192` (AIC+COCO combined, AP 76.3 — Pipeline 표 권장)

## Pod 실행 절차 (Plan 08 setup 상태에서 시작)

> 전제: Plan 08 `bash runpod_inference/setup.sh` 가 이미 실행됨.
> MotionBERT clone + 가중치 (`best_epoch.bin`) + MediaPipe pose_landmarker_heavy.task
> 모두 이미 존재. RTMPose 만 추가 install.

### 1. SunityMotion 저장소 최신화

```bash
cd /workspace/SunityMotion
git pull --ff-only origin main
```

### 2. MMPose 스택 install (Plan 10 신규)

```bash
pip install -U openmim
mim install mmengine "mmcv>=2.0" "mmdet>=3.0" "mmpose>=1.3"
```

mmcv 2.x 는 PyTorch 2.4 (Pod base image) 와 호환. PyTorch 다운그레이드 불요.

### 3. RTMPose-l checkpoint 다운로드

옵션 A — `mim download` (권장):
```bash
mkdir -p /workspace/rtmpose_weights
cd /workspace/rtmpose_weights
mim download mmpose --config rtmpose-l_8xb256-420e_coco-256x192 --dest .
ls -lh
# 결과:
#   rtmpose-l_8xb256-420e_coco-256x192.py  (config, 수 KB)
#   rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth  (~111 MB)
```

옵션 B — wget 직접:
```bash
mkdir -p /workspace/rtmpose_weights
cd /workspace/rtmpose_weights
wget https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth
# config 는 mmpose 가 검색 가능 (이름으로 지정 가능)
```

### 4. PYTHONPATH 확인 (Plan 08 setup 과 동일)

```bash
export PYTHONPATH="/workspace/SunityMotion/backend/shared/python:/workspace/SunityMotion:$PYTHONPATH"
export CUDA_VISIBLE_DEVICES=0
echo $PYTHONPATH
```

### 5. spike 실행 (ref-sideway-spin 1영상)

```bash
cd /workspace/SunityMotion

python3 -m backend.research.spikes.spike_rtmpose \
  --motion ref-sideway-spin \
  --bucket sunity-motion-pilot-videos \
  --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \
  --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \
  --motionbert-root /workspace/MotionBERT \
  --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \
  --score-threshold 0.3 \
  --out backend/research/spikes/reports/spike_rtmpose_$(date +%Y%m%d_%H%M).json
```

실행 완료 후:
- `backend/research/spikes/reports/spike_rtmpose_YYYYMMDD_HHMM.json`
- `backend/research/spikes/reports/spike_rtmpose_YYYYMMDD_HHMM.md`

## 판정 기준 (Plan 10)

| 결과 | overall | 다음 행동 |
|---|---|---|
| Strong pass | ≥ 70 | "approved, proceed to Plan 11" (5영상 sweep + 게이트 룰 재정의 + Wave 3 진입) |
| Weak signal | 60~70 | "try other checkpoint" (RTMPose-x / 384x288) |
| 실패 | < 60 | "accept limitation, proceed to Plan 11 with 4/5 rule" 또는 "try HybrIK" (Option A, MIT) |

AlphaPose 는 라이선스 차단 (Noncommercial) — 어떤 결과여도 후보 제외.

## Plan 10 파일 목록 (추가분)

```
backend/research/spikes/
  rtmpose_to_h36m17.py            # RTMPose COCO-17 → H3.6M 17 매핑 어댑터
  spike_rtmpose.py                # RTMPose + MotionBERT spike 하네스 (CLI)

backend/tests/
  test_spike_rtmpose_to_h36m17.py # 36 tests PASS (mmpose 의존 없이 로컬 실행 가능)
```

기존 Plan 07/08 파일 (`mediapipe_to_h36m17.py`, `spike_motionbert.py`,
`test_spike_mediapipe_to_h36m17.py`) 은 5영상 sweep 시 비교군으로 보존.

## 주의사항 (Plan 10)

- RTMPose checkpoint (.pth, ~111 MB) 는 git 에 절대 커밋하지 않는다.
  `/workspace/rtmpose_weights/` Pod 경로에만 보관.
- mmpose 의존성은 Pod 전용. Lambda 에 배포하지 않는다 (Plan 08 RunPod 격리 원칙).
- spike 코드 (`backend/research/spikes/`) 는 운영 코드 (`functions/`, `shared/pose_lifters/`)
  import 경로를 침범하지 않는다.

---

# Plan 11 — 5영상 sweep + line/angle root cause

> 본 섹션은 Plan 01-11 에서 추가됨. Plan 07/08/10 섹션은 위쪽 그대로 보존.

## 목적 (Plan 11)

Plan 10 = ref-sideway-spin 단일 영상 STRONG_PASS (overall 72.0). Plan 11 은
같은 spike 를 Plan 08 5영상 (ref-climb / ref-foxtop-split / ref-foxtop /
ref-invert / ref-sideway-spin) 에 회귀 실행 + line/angle N/A 정확한 원인
박제 + 게이트 룰 (D-14 / D-15①~③) 적정성 재검토. Wave 3 (Plan 04 NLF R&D
격리 + Plan 05 atomic swap) 진입 게이트 verdict 까지 한 번에 본다.

본 plan 에서 운영 코드 (functions/, runpod_inference/, shared/pose_lifters/)
는 1줄도 변경하지 않는다. FallbackRecognizer / dimensions.py 도 박제만,
실제 변경은 belle 결정 + Phase 5 Gemini 통합 시점.

## Plan 11 추가 파일

```
backend/research/spikes/
  sweep_rtmpose.py                # 5영상 batch sweep 하네스 (CLI 9 args)
  debug_dimensions.py             # line/angle N/A 원인 trace 스크립트

backend/tests/
  test_sweep_rtmpose_smoke.py     # 12 tests PASS (mmpose 없이 로컬)
```

## Pod 실행 절차 (Plan 11 sweep — belle Pod 전용)

> 전제: Plan 10 belle Pod 환경 유지 (mmpose 1.3.2 / numpy 1.26.4 / mmcv 2.1.0,
> RTMPose-l 가중치 + MotionBERT 가중치 이미 위치). 추가 install 불필요.

### 1. SunityMotion 저장소 최신화

```bash
cd /workspace/SunityMotion
git pull --ff-only origin main
```

### 2. 5영상 sweep 실행

```bash
cd /workspace/SunityMotion

python3 -m backend.research.spikes.sweep_rtmpose \
  --motions ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin \
  --bucket sunity-motion-pilot-videos \
  --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \
  --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \
  --motionbert-root /workspace/MotionBERT \
  --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \
  --score-threshold 0.3 \
  --det-model none \
  --out backend/research/spikes/reports/sweep_rtmpose_$(date +%Y%m%d_%H%M).json
```

예상 소요: 5영상 × ~2분/영상 ≈ 10분. lifter 37ms/frame, NLF baseline
665ms/frame (영상당 NLF ~2분 차지).

### 3. 결과 파일

- `backend/research/spikes/reports/sweep_rtmpose_YYYYMMDD_HHMM.json`
- `backend/research/spikes/reports/sweep_rtmpose_YYYYMMDD_HHMM.md`

`.md` 의 "5영상 종합표" + "게이트 verdict" 섹션을 Claude 에 공유.

## line / angle N/A 원인 박제 절차 (Plan 11 T-2)

sweep 결과 JSON 을 `debug_dimensions.py` 에 입력해 원인 분류:

```bash
python3 -m backend.research.spikes.debug_dimensions \
  --report backend/research/spikes/reports/sweep_rtmpose_YYYYMMDD_HHMM.json \
  --out backend/research/spikes/reports/debug_dimensions_YYYYMMDD_HHMM.md
```

출력:
- FallbackRecognizer default profile (expected_extend / expected_bent /
  applicable_joints)
- 영상별 line N/A 원인 (expected_extend 빈 집합 vs default 다름)
- 영상별 angle N/A 원인 (spike 의 정상 동작 — reference 없이 호출)
- Fix candidates 3 (score_threshold / FallbackRecognizer default / 임계 완화) —
  박제만, 실제 적용은 belle 결정 + Phase 5 Gemini 통합 진입 시

## 판정 기준 (Plan 11)

| sweep 결과 | passed/total | belle 응답 | 다음 행동 |
|---|---|---|---|
| Strong pass | 5/5 (overall ≥70) | `approved, proceed to Wave 3` | Plan 04 / Plan 05 진입 |
| Conditional pass | 4/5 | `accept limitation, proceed to Wave 3 with known gap` | Plan 04/05 진입 + Phase 5 우선순위 ↑ |
| Regression | 3/5 이하 | `regression in RTMPose, evaluate path` | Plan 12 추가 검토 (HybrIK 또는 MP+MB 유지) |
| line/angle 전부 N/A 차단 | — | `Wave 3 보류, Phase 5 선행` | Phase 5 Gemini 통합 우선 |

게이트 룰 적정성 (D-14 / D-15①~③) + Wave 3 진입 조건 자세한 분석은
`.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-11-SUMMARY.md` 참조.

## 주의사항 (Plan 11)

- 본 plan 은 spike 디렉터리 (`backend/research/spikes/`) 외 어떤 파일도
  수정하지 않는다. 운영 코드 (`functions/`, `runpod_inference/`,
  `shared/pose_lifters/`) 무수정.
- FallbackRecognizer (`shared/.../analysis/technique.py`) / dimensions.py
  무수정. line/angle 회복은 Phase 5 (Gemini 기술 인식기 어댑터) 진입 시.
- AlphaPose 는 라이선스 차단 (Noncommercial). 본 plan 어떤 task 에서도
  도입 시도 금지 (memory `license-blocklist-pose.md`).
- mmpose / numpy 추가 install 금지 — Plan 10 환경 그대로.

