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

MotionBERT H3.6M 가중치는 Google Drive에서 배포된다. README 링크 확인:
https://github.com/Walter0807/MotionBERT#readme

```bash
mkdir -p /workspace/MotionBERT/checkpoint/pose3d/MB_train_h36m

# gdown 사용 (Google Drive 직접 다운로드):
pip install gdown
gdown "https://drive.google.com/uc?id=<DRIVE_FILE_ID>" \
  -O /workspace/MotionBERT/checkpoint/pose3d/MB_train_h36m/best_epoch.bin

# 또는 MotionBERT README의 최신 링크 사용.
# 가중치 파일명: best_epoch.bin (~120MB)
```

가중치 파일은 git에 추적하지 않는다. `/workspace/` 경로에만 보관.

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
  --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/MB_train_h36m/best_epoch.bin \
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
