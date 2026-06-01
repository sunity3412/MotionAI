---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "10"
subsystem: ml-pose-engine
tags:
  - spike
  - rtmpose
  - mmpose
  - apache-2.0
  - sideway-spin
  - lifter-evaluation
  - pending-belle-pod

dependency_graph:
  requires:
    - 01-07  # MotionBERT spike pattern
    - 01-08  # MP+MotionBERT production 4/5 PASS, ref-sideway-spin fail
    - 01-09  # AlphaPose license_blocked → RTMPose 대안 결정
  provides:
    - "RTMPose-l (Apache 2.0) 2D detector spike harness"
    - "COCO-17 → H3.6M 17 derive 패턴 RTMPose 변형 (Plan 08 mediapipe_to_h36m17 패턴 재사용)"
    - "ref-sideway-spin 1영상 측면 보강 검증 (belle Pod 실행 대기)"
    - "MMPose 스택 (mmpose / mmengine / mmcv / mmdet) Apache 2.0 박제"
  affects:
    - 01-11  # belle Pod 결과에 따라 분기 (5영상 sweep / HybrIK / 4/5 수용)

tech_stack:
  added:
    - "spike 의존성 (Pod 전용): mmpose>=1.3, mmengine, mmcv>=2.0, mmdet>=3.0 — Apache 2.0"
    - "RTMPose-l checkpoint (AIC+COCO, 256x192, AP 76.5, ~111 MB) — OpenMMLab CDN"
  patterns:
    - "spike 격리 — backend/research/spikes/, 운영 코드 무수정"
    - "lazy import — mmpose / torch 는 _run_rtmpose_2d 내부에서만 import"
    - "Plan 07 spike_motionbert pattern 재사용 — 2D detector 만 교체, lift/score chain 동일"

key_files:
  created:
    - backend/research/spikes/rtmpose_to_h36m17.py
    - backend/research/spikes/spike_rtmpose.py
    - backend/tests/test_spike_rtmpose_to_h36m17.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-10-SUMMARY.md
  modified:
    - backend/research/spikes/README.md  # append-only, Plan 07/08 섹션 보존

decisions:
  - "MMPose 스택 (mmpose / mmengine / mmcv / mmdet) 라이선스 Apache 2.0 확인 (2026-06-01). HALT condition 미발동, spike 코드 진행."
  - "RTMPose-l checkpoint = rtmpose-l_8xb256-420e_coco-256x192 (AIC+COCO 학습, AP 76.5). 가중치 Apache 2.0 (OpenMMLab project zoo). 다운로드 URL: download.openmmlab.com/mmpose/v1/projects/rtmposev1/."
  - "score_threshold 기본 0.3 — RTMPose keypoint score < 0.3 NaN 처리해 downstream temporal_fill 보간."
  - "image_size 정규화 — RTMPose pixel 좌표 → image (W, H) 로 [0, 1] 변환해 Plan 08 mediapipe_to_h36m17 출력 형식과 일치."
  - "spike 코드는 backend/research/spikes/ 내부만. 운영 코드 (functions/, pose_lifters/) 무수정 — Plan 08 production 안정 유지."

requirements_completed: []

metrics:
  duration: "~45 min (executor: T-1 라이선스 research + T-2 어댑터 + 36 tests + T-3 runner + T-4 README)"
  completed_date: "2026-06-01"
  tasks_completed: 4
  tasks_total: 5
  files_created: 4
  files_modified: 1
---

# Phase 01 Plan 10: RTMPose Spike (Apache 2.0) — Executor 완료, belle Pod 실행 대기

**One-liner:** AlphaPose 라이선스 차단 후속으로 RTMPose-l (MMPose, Apache 2.0) 2D detector 로 측면 자세 보강 spike. T-1~T-4 executor 완료, ref-sideway-spin 1영상 실행은 belle Pod (RTX 3090, Plan 08 setup 유지) 에서.

---

## TL;DR

| 항목 | 내용 |
|---|---|
| **Verdict** | `ready_for_belle_pod` |
| **단계 도달** | T-1 ~ T-4 완료 / T-5 belle Pod 실행 대기 |
| **라이선스** | MMPose 스택 전체 Apache 2.0 (HALT 미발동) |
| **라이선스 확인 일자** | 2026-06-01 |
| **라이선스 출처** | https://github.com/open-mmlab/mmpose/blob/main/LICENSE 외 3건 |
| **신규 파일** | 3 (어댑터, runner, 테스트) + 1 SUMMARY |
| **수정 파일** | 1 (README append) |
| **단위 테스트** | 36 PASS (mmpose 의존 없이 로컬 실행) |
| **만든 커밋** | 4 (T-2 / T-3 / T-4 / SUMMARY) — 본 SUMMARY commit 포함 시 4 |

---

## T-1 RTMPose Research 결과

### T-1-1 라이선스 검증 (HALT 게이트)

GitHub raw `LICENSE` 파일 직접 fetch 결과 (2026-06-01):

| 라이브러리 | 라이선스 | 출처 |
|---|---|---|
| MMPose | **Apache License 2.0** | https://github.com/open-mmlab/mmpose/blob/main/LICENSE |
| mmengine | **Apache License 2.0** | https://github.com/open-mmlab/mmengine/blob/main/LICENSE |
| mmcv | **Apache License 2.0** | https://github.com/open-mmlab/mmcv/blob/main/LICENSE |
| mmdetection | **Apache License 2.0** | https://github.com/open-mmlab/mmdetection/blob/main/LICENSE |

GitHub API `repos/open-mmlab/mmpose/license` metadata `apache-2.0` 확인.
MMPose README "License" 섹션 `This project is released under the Apache 2.0 license` 박제.

**HALT condition 미발동.** Plan 10 frontmatter `must_haves.truths[2]` ("RTMPose 라이선스 Apache 2.0 확인 후 진입. 안 맞으면 spike 중단 + belle 재검토") 통과 — spike 코드 작성 진행.

### T-1-2 RTMPose-l 가중치 라이선스

권장 checkpoint **`rtmpose-l_8xb256-420e_coco-256x192`** (AIC+COCO 학습, AP 76.5, ~111 MB):

| 항목 | 값 |
|---|---|
| 다운로드 URL | https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth |
| 가중치 라이선스 | MMPose project zoo (Apache 2.0) |
| 호스팅 | download.openmmlab.com (OpenMMLab 공식 CDN) |
| 입력 해상도 | 256 x 192 |
| AP (COCO val) | 76.5 |

ModelScope/OpenXLab 별도 호스팅이 아니라 OpenMMLab 공식 CDN 직접 호스팅 — MMPose 프로젝트의 Apache 2.0 라이선스가 가중치에도 적용됨.

대안 후보 (spike weak signal 시):
- `rtmpose-l_8xb256-420e_coco-384x288` — 해상도 ↑, AP 77.3
- `rtmpose-l_8xb256-420e_aic-coco-256x192` — AIC+COCO combined

### T-1-3 RTMPose 단일 영상 추론 API

`mmpose.apis.MMPoseInferencer` 사용 (top-down detector + pose estimator 자동 wire). 출력 구조:

```python
result = next(inferencer(frame_ndarray))
# result['predictions']: list[list[dict]] — batch x instances
# inst dict keys:
#   'keypoints': list[[x, y], ...]  shape (17, 2) pixel 좌표
#   'keypoint_scores': list[float]   shape (17,)  per-keypoint score
```

다중 person 영상은 본 spike 범위 밖 — 가장 confident person (instance[0]) 만 사용.

### T-1-4 Pod install 명령 (Plan 08 setup 상태 위에 추가)

```bash
pip install -U openmim
mim install mmengine "mmcv>=2.0" "mmdet>=3.0" "mmpose>=1.3"

mkdir -p /workspace/rtmpose_weights
cd /workspace/rtmpose_weights
mim download mmpose --config rtmpose-l_8xb256-420e_coco-256x192 --dest .
```

PyTorch 2.4 (Pod base) + mmcv 2.x 호환 확인 — mmcv 2.x release notes 에서 torch 2.0~2.4 지원 명시. PyTorch 다운그레이드 불요.

---

## T-2 어댑터 결과 (`rtmpose_to_h36m17.py`)

### 매핑 표

| H3.6M idx | H3.6M joint | source |
|---|---|---|
| 0 | hip | derive: (COCO 11 l_hip + COCO 12 r_hip) / 2 |
| 1 | r_hip | COCO 12 |
| 2 | r_knee | COCO 14 |
| 3 | r_foot | COCO 16 (right ankle) |
| 4 | l_hip | COCO 11 |
| 5 | l_knee | COCO 13 |
| 6 | l_foot | COCO 15 (left ankle) |
| 7 | spine | derive: (hip[0] + thorax[8]) / 2 |
| 8 | thorax | derive: (COCO 5 l_sh + COCO 6 r_sh) / 2 |
| 9 | neck_nose | derive: (thorax[8] + COCO 0 nose) / 2 |
| 10 | head | COCO 0 (nose proxy) |
| 11 | l_shoulder | COCO 5 |
| 12 | l_elbow | COCO 7 |
| 13 | l_wrist | COCO 9 |
| 14 | r_shoulder | COCO 6 |
| 15 | r_elbow | COCO 8 |
| 16 | r_wrist | COCO 10 |

Plan 01-08 production `pose_lifters/mediapipe_to_h36m17.py` 의 derive 패턴 (12 직접 + 5 파생) 과 동일 — source 만 MediaPipe 33 → COCO 17 로 바뀜.

### 정규화 + threshold

- `image_size=(W, H)` 인자: RTMPose pixel 좌표 → `[0, 1]` 정규화 (Plan 08 mediapipe_to_h36m17 출력 형식 일치).
- `score_threshold=0.3` 기본: keypoint score < threshold → NaN 처리. downstream `temporal_fill` 이 보간.

### 단위 테스트

36 tests PASS:

| 테스트 클래스 | tests | 범위 |
|---|---|---|
| TestShape | 6 | (T, 17, 2\|3) shape, 단일 프레임 확장, 상수 검증 |
| TestDirectMapping | 13 | 12개 직접 매핑 + head (nose proxy) 정확성 |
| TestDerivedJoints | 5 | hip / thorax / spine / neck_nose 계산 |
| TestImageSizeNormalization | 4 | pixel → [0, 1] + invalid size ValueError |
| TestScoreThreshold | 4 | NaN 처리 + boundary + derived 전파 |
| TestNanPropagation | 1 | 미감지 프레임 NaN 보존 |
| TestInputValidation | 3 | 잘못된 형상 ValueError |

mmpose 의존 없이 로컬 실행:

```bash
PYTHONPATH=backend/shared/python:. python3 -m pytest backend/tests/test_spike_rtmpose_to_h36m17.py -v
# 36 passed in 0.27s
```

---

## T-3 spike runner 결과 (`spike_rtmpose.py`)

### 흐름 (Plan 07 spike_motionbert 패턴 그대로)

1. S3 영상 다운로드 (`--motion ref-sideway-spin` → `reference/ref-sideway-spin.mp4`)
2. `FfmpegFrameExtractor` 9 fps / 640px (Plan 07/08 동일)
3. `HoughPoleDetector` 호출 (현재 미사용, Plan 07 spike 동일)
4. `MMPoseInferencer` → per-frame COCO-17 (T, 17, 3=x,y,score)
5. `convert_rtmpose_coco17_to_h36m17(rtmpose_kp, image_size, score_threshold)` → H3.6M 17 정규화 (T, 17, 2)
6. MotionBERT DSTformer chunked inference (MAXLEN=243, FT_MB_lite_MB_ft_h36m_global_lite)
7. H3.6M 17 → COCO-17 limb subset (`_h36m17_to_coco17_subset` — Plan 08 production 어댑터와 동일 매핑)
8. `compute_joint_angles` → `temporal_fill` → `absolute_dimension_scores` → `overall_from_dimensions`
9. NLF baseline 동시 실행 (`compare_engines._run_nlf` 동일 경로)
10. 갭 계산 + 판정 → JSON + Markdown 보고서

### CLI 인자

| 인자 | 필수 | 설명 |
|---|---|---|
| `--motion` 또는 `--video` | yes (xor) | 모션 ID (S3) 또는 로컬 경로 |
| `--bucket` | no (기본 sunity-motion-pilot-videos) | S3 버킷 |
| `--rtmpose-config` | yes | RTMPose config .py 경로 |
| `--rtmpose-checkpoint` | yes | RTMPose .pth 경로 |
| `--det-model` | no (기본 `rtmdet-nano`) | mmpose detector alias |
| `--score-threshold` | no (기본 0.3) | NaN 임계값 |
| `--motionbert-root` | no (기본 `/workspace/MotionBERT`) | |
| `--motionbert-weights` | no (기본 `{root}/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin`) | |
| `--out` | no | JSON 보고서 경로 |

### 보고서 구조

```json
{
  "generated_at": "ISO 8601 UTC",
  "motion": "ref-sideway-spin",
  "frames_total": <int>,
  "detector": "rtmpose-l",
  "rtmpose_config": "<path>",
  "rtmpose_checkpoint": "<path>",
  "score_threshold": 0.3,
  "image_size": [W, H],
  "lifter": {
    "engine": "rtmpose_2d+motionbert",
    "overall": <float>,
    "dimensions": {"stability": <float>, "line": <float>, "angle": <float>},
    "ms_per_frame": <float>,
    "avg_rtm_score": <float>
  },
  "nlf": {...},
  "gap": {"overall": <float>, "dimensions": {...}},
  "verdict": "strong_pass" | "weak_signal" | "fail",
  "thresholds": {"strong_pass_overall": 70.0, "weak_signal_overall": 60.0}
}
```

### 로컬 import 검증

torch / mmpose 미설치 로컬 환경에서 module import 만 성공:

```bash
python3 -c "import sys; sys.path.insert(0, 'backend/shared/python'); sys.path.insert(0, '.'); \
  from backend.research.spikes import spike_rtmpose; \
  print('run_spike:', hasattr(spike_rtmpose, 'run_spike'))"
# OK
```

lazy import 패턴 — `torch`, `mmpose`, `boto3` 모두 함수 내부에서만 import.

---

## T-4 README 결과

`backend/research/spikes/README.md` 끝에 "Plan 10 — RTMPose 측면 자세 보강 spike" 섹션 append (Plan 07/08 MotionBERT 섹션 위쪽 그대로 보존).

추가 섹션:
- 배경 (Plan 09 license_blocked → option-b-1)
- 라이선스 표 (4건 + 모델 가중치, 확인 일자 박제)
- RTMPose-l checkpoint 정보 + 다운로드 URL
- Pod 실행 절차 (5단계, Plan 08 setup 상태 가정)
- 판정 기준 표 + belle 응답 옵션
- Plan 10 파일 목록 + 주의사항

---

## belle Pod checkpoint Payload (T-5)

> **belle 가 Pod (RTX 3090, Plan 08 setup 유지) 에서 다음 명령을 그대로 실행하세요.**

### 0. Pod 상태 확인

```bash
# Pod 에 SSH 접속 후
nvidia-smi  # RTX 3090 인식 + CUDA OK
ls /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin
# ~120 MB 이상이면 OK. 없으면 Plan 08 setup 가이드 참조해 scp 복원.
```

### 1. SunityMotion 최신화

```bash
cd /workspace/SunityMotion
git pull --ff-only origin main
```

### 2. MMPose 스택 install (Plan 10 신규, 1회)

```bash
pip install -U openmim
mim install mmengine "mmcv>=2.0" "mmdet>=3.0" "mmpose>=1.3"
```

설치 확인:
```bash
python3 -c "import mmpose; print('mmpose:', mmpose.__version__)"
python3 -c "import mmcv; print('mmcv:', mmcv.__version__)"
```

### 3. RTMPose-l checkpoint 다운로드

```bash
mkdir -p /workspace/rtmpose_weights
cd /workspace/rtmpose_weights
mim download mmpose --config rtmpose-l_8xb256-420e_coco-256x192 --dest .
ls -lh
# 기대:
#   rtmpose-l_8xb256-420e_coco-256x192.py
#   rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth  (~111 MB)
```

### 4. 환경변수

```bash
export PYTHONPATH="/workspace/SunityMotion/backend/shared/python:/workspace/SunityMotion:$PYTHONPATH"
export CUDA_VISIBLE_DEVICES=0
# AWS 자격증명은 Pod 환경에 이미 박제됨 (Plan 08)
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

### 6. 결과 파일 위치

- `backend/research/spikes/reports/spike_rtmpose_YYYYMMDD_HHMM.json`
- `backend/research/spikes/reports/spike_rtmpose_YYYYMMDD_HHMM.md`

`.md` 파일을 Claude 에 공유해 다음 단계 결정.

---

## 판정 기준 + belle 응답 옵션

| 결과 | overall | 다음 plan (Plan 11) |
|---|---|---|
| Strong pass | ≥ 70 | "approved, proceed to Plan 11" → 5영상 sweep + 게이트 룰 재정의 + Wave 3 진입 |
| Weak signal | 60~70 | "try other checkpoint" → RTMPose-x / 384x288 해상도 재시도 |
| Weak signal (path 전환) | 60~70 | "try HybrIK" → Plan 09 SUMMARY Option A (MIT, SMPL prior) |
| 실패 | < 60 | "accept limitation, proceed to Plan 11 with 4/5 rule" → D-15① 4/5 수용 + Wave 3 진입 |

AlphaPose 는 라이선스 차단 (Noncommercial) — 어떤 결과여도 후보 제외 (`.claude/projects/.../memory/license-blocklist-pose.md` 박제됨).

---

## Deviations from Plan

없음 — Plan 10 frontmatter 와 본 SYSTEM PROMPT 의 task 정의대로 실행됨.

T-1 라이선스 검증 결과 HALT 미발동 (Apache 2.0). T-2~T-4 정상 수행.

운영 코드 (`functions/`, `runpod_inference/`, `shared/pose_lifters/`) 수정 0 — Plan 08 production 안정 유지.

**Total deviations:** 0. **Impact:** spike 단독 추가, 운영 코드 회귀 없음.

---

## Known Stubs

없음 — spike 코드는 belle Pod 에서 즉시 실행 가능한 완전한 구현. 단위 테스트 36 PASS.

---

## Threat Flags

없음 — 신규 네트워크 엔드포인트 / auth path / Firestore 스키마 변경 없음.

`mmpose` Lambda 배포 없음 (RunPod 격리 원칙 유지) — `functions/` 미수정으로 자동 보장.

---

## Self-Check: PASSED

파일 존재 확인:
- `backend/research/spikes/rtmpose_to_h36m17.py` FOUND
- `backend/research/spikes/spike_rtmpose.py` FOUND
- `backend/research/spikes/README.md` FOUND (modified, append-only)
- `backend/tests/test_spike_rtmpose_to_h36m17.py` FOUND
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-10-SUMMARY.md` FOUND (이 파일)

운영 코드 무수정 확인:
- `backend/functions/pipeline/app.py` UNCHANGED
- `backend/runpod_inference/server.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/pose_lifters/` UNCHANGED
- `backend/research/spikes/mediapipe_to_h36m17.py` UNCHANGED (Plan 07/08 비교군 보존)
- `backend/research/spikes/spike_motionbert.py` UNCHANGED

커밋 존재 확인:
- `19310ae` feat(01-10): T-2 rtmpose_to_h36m17 adapter + 36 tests FOUND
- `3b38e15` feat(01-10): T-3 spike_rtmpose runner FOUND
- `5a823a5` docs(01-10): T-4 README RTMPose section (Apache 2.0) FOUND

라이선스 출처 fetch 확인:
- MMPose: Apache 2.0 (raw + GitHub API metadata 일치)
- mmengine: Apache 2.0
- mmcv: Apache 2.0
- mmdetection: Apache 2.0

---

## Verdict 요약 — orchestrator 에게

- **verdict**: `ready_for_belle_pod`
- **one-liner**: RTMPose-l (Apache 2.0) spike harness + 어댑터 + 36 tests + README executor 완료. ref-sideway-spin 1영상 실행은 belle Pod 에서 SUMMARY 의 "belle Pod checkpoint Payload" 시퀀스 그대로 실행.
- **commits**: 4 (T-2 / T-3 / T-4 / SUMMARY) — SUMMARY commit 은 다음 단계.
- **next action**: belle 가 Pod 에서 install + checkpoint download + spike 실행 → 결과 `.md` 공유 → 판정 기준 표에 따라 Plan 11 분기 결정.
