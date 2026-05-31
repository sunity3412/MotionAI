---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "08"
subsystem: ml-pose-engine
tags:
  - motionbert
  - mediapipe
  - pose-lifter
  - production-promotion
  - compare-engines

dependency_graph:
  requires:
    - 01-02  # PoseEngine Protocol, PoseFrame
    - 01-03  # pole axis + aligner
    - 01-06  # MediaPipePoseEngine production
    - 01-07  # MotionBERT spike STRONG_PASS
  provides:
    - pose_lifters package (MotionBertLifter + MP33→H36M17)
    - MediaPipeWithLifterEngine composite engine
    - RunPod setup for MotionBERT + MediaPipe
    - compare_engines --engine flag (nlf-vs-mediapipe-lifter)
  affects:
    - backend/runpod_inference/  # setup.sh, requirements.txt, README.md
    - backend/research/evaluations/  # compare_engines.py --engine option
    - backend/shared/python/sunity_shared/analysis/pose_lifters/  # new package
    - backend/shared/python/sunity_shared/analysis/pose_engines/  # composite engine

tech_stack:
  added:
    - MotionBERT DSTformer (Apache 2.0) — lazy import via sys.path insert
    - einops>=0.7,<1.0, timm>=0.9,<2.0 (MotionBERT deps)
    - mediapipe>=0.10,<0.11, opencv-python-headless>=4.13,<5 (RunPod)
  patterns:
    - DI factory (create_with_model, create_with_engines) for test injection
    - lazy module-level import (torch, mediapipe, scipy — never at module load)
    - chunked inference: MAXLEN=243, tail-frame padding

key_files:
  created:
    - backend/shared/python/sunity_shared/analysis/pose_lifters/__init__.py
    - backend/shared/python/sunity_shared/analysis/pose_lifters/mediapipe_to_h36m17.py
    - backend/shared/python/sunity_shared/analysis/pose_lifters/motionbert_lifter.py
    - backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_lifter_engine.py
    - backend/tests/test_motionbert_lifter.py
    - backend/tests/test_pose_lifters_mediapipe_to_h36m17.py
    - backend/tests/test_mediapipe_lifter_engine.py
  modified:
    - backend/shared/python/sunity_shared/analysis/pose_engines/__init__.py
    - backend/runpod_inference/requirements.txt
    - backend/runpod_inference/setup.sh
    - backend/runpod_inference/README.md
    - backend/research/evaluations/compare_engines.py
    - backend/tests/test_compare_engines_smoke.py
    - backend/research/spikes/mediapipe_to_h36m17.py  # deprecation note
    - backend/research/spikes/spike_motionbert.py       # deprecation note
    - .gitignore  # best_epoch.bin, FT_MB_lite checkpoint dir

decisions:
  - "MotionBertLifter._ensure_loaded() + norm_layer 명시 금지 — DSTformer 기본값 nn.LayerNorm (Plan 07 commit c164700 박제)"
  - "MediaPipeWithLifterEngine._extract_mp_2d_from_pose_frames: COCO-17 역매핑 + 0.5 패딩 (MP33 원본 불복원 불가 — keypoints_2d는 COCO-17만 저장)"
  - "compare_engines engine_a/engine_b 구조 — backward compat: nlf-vs-mediapipe 모드에서 nlf/mediapipe 키 추가 제공"
  - "MotionBERT 가중치 git 미포함 — scp 수동 배치. OneDrive 직링크 불안정으로 자동 다운로드 금지 (scope_limits 박제)"

metrics:
  duration: "session resumed from prior context"
  completed_date: "2026-05-31"
  tasks_completed: 4
  tasks_total: 5
  files_created: 7
  files_modified: 8
---

# Phase 01 Plan 08: MediaPipe + MotionBERT Production Promotion Summary

**One-liner:** MotionBertLifter + MediaPipeWithLifterEngine production promotion from Plan 07 spike, with RunPod setup update and compare_engines `--engine nlf-vs-mediapipe-lifter` for belle's 5-video regression gate.

## What Was Built

### Task 1 — pose_lifters/ Package (commit 15b9641)

`backend/shared/python/sunity_shared/analysis/pose_lifters/` 신규 패키지:

- `mediapipe_to_h36m17.py`: spike 이전, MP33 → H3.6M 17-joint 매핑. 13개 직접 매핑 + 4개 파생 관절(Hip, Thorax, Spine, NeckNose). `convert_mp33_to_h36m17()` + `h36m17_to_coco17_subset()`.
- `motionbert_lifter.py`: `MotionBertLifter` — `(T,17,2|3)` → `(T,17,3)`. DSTformer lazy load, env var fallback (MOTIONBERT_ROOT, MOTIONBERT_WEIGHTS), chunked inference (MAXLEN=243). `norm_layer` 미명시 (DSTformer 기본 nn.LayerNorm — Plan 07 c164700 박제).
- `__init__.py`: Apache 2.0 라이선스 메타 docstring + 클래스 re-export.
- 단위 테스트: 38 (mediapipe_to_h36m17) + 14 (motionbert_lifter) = 52 tests PASS.
- Spike 원본: deprecation note 추가, 삭제 안 함 (Plan 09 정리 단계 예정).

### Task 2 — MediaPipeWithLifterEngine Composite (commit d91373c)

`backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_lifter_engine.py`:

- `MediaPipeWithLifterEngine` — PoseEngine Protocol 호환 (`estimate(frames, pole_axis) → list[PoseFrame]`).
- 흐름: MP estimate → COCO-17 keypoints_2d → COCO-to-MP 역매핑 (T,33,2) → H36M17 → MotionBERT lift → COCO17 subset → PoseFrame 교체.
- `create_with_engines()` DI factory — mediapipe/torch 없이 단위 테스트 가능.
- `_replace_keypoints()`: limb joints 교체, face NaN 제외, pole_axis 보존 (H-3), reliability 재계산 (H-4).
- `pose_engines/__init__.py`: `MediaPipeWithLifterEngine` lazy __getattr__ export 추가.
- 단위 테스트: 19 tests PASS.

### Task 3 — RunPod Setup Update (commit e39b656)

- `requirements.txt`: mediapipe>=0.10,<0.11, opencv-python-headless>=4.13,<5, einops>=0.7,<1.0, timm>=0.9,<2.0 추가.
- `setup.sh`: 6단계 구조 (apt libgl1/libglib2.0-0, pip, NLF, MotionBERT clone, MediaPipe task wget, CUDA check). MotionBERT 가중치 미존재 시 scp 절차 안내 (자동 다운로드 금지).
- `README.md`: MOTIONBERT_ROOT/MOTIONBERT_WEIGHTS env var 문서화, scp 절차, sanity check 명령 추가.
- `.gitignore`: `best_epoch.bin`, `FT_MB_lite_MB_ft_h36m_global_lite/` 추가 (가중치 git 추적 금지).

### Task 4 — compare_engines.py --engine Option (commit 84c249a)

- `--engine` 옵션 (choices: `nlf-vs-mediapipe`, `nlf-vs-mediapipe-lifter`, `mediapipe-vs-mediapipe-lifter`). 기본값 `nlf-vs-mediapipe` (기존 호환).
- `_run_mediapipe_lifter()`: `MediaPipeWithLifterEngine` 호출, 기존 score 체인 재사용.
- `compare_engines()`: `engine_mode` 인자, `engine_a/engine_b` 구조 통합. `nlf-vs-mediapipe` 모드에서 backward compat `nlf`/`mediapipe` 키 제공.
- `generate_markdown_report()`: 엔진 모드별 헤더/레이블 분기 (MP+MotionBERT, NLF, MediaPipe).
- smoke tests: 7개 신규 (17 total PASS).

### Task 5 — belle Pod Regression (checkpoint: awaiting human action)

5영상 회귀 검증은 belle RunPod Pod 에서 실행. 본 plan executor 는 GPU/S3 미접근으로 실행 안 함.

## Test Summary

| Test File | Count | Status |
|-----------|-------|--------|
| test_pose_lifters_mediapipe_to_h36m17.py | 38 | PASS |
| test_motionbert_lifter.py | 14 | PASS |
| test_mediapipe_lifter_engine.py | 19 | PASS |
| test_compare_engines_smoke.py | 17 | PASS |
| **Total** | **88** | **PASS** |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| T-1 | 15b9641 | pose_lifters 패키지 생성 — MotionBertLifter + MP33→H36M17 production 승격 |
| T-2 | d91373c | MediaPipeWithLifterEngine composite — MP 2D + MotionBERT 3D lift |
| T-3 | e39b656 | RunPod requirements + setup.sh + README — MotionBERT + MediaPipe 셋업 |
| T-4 | 84c249a | compare_engines.py --engine 옵션 — nlf-vs-mediapipe-lifter 추가 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] torch import before input validation in lift()**
- Found during: Task 1 test run
- Issue: `lift()` method ran `import torch` before input shape validation. DI factory injects model directly (skips `_ensure_loaded()`), but `import torch` in the loop body ran unconditionally, crashing when torch is absent.
- Fix: Moved input shape validation (`if arr.ndim != 3...`) before `_ensure_loaded()` and `import torch`. Validation is pure numpy — safe without torch.
- Files modified: `pose_lifters/motionbert_lifter.py`
- Commit: 15b9641

**2. [Rule 1 - Bug] MagicMock(spec=ModuleType) AttributeError for torch.device**
- Found during: Task 1 unit test development
- Issue: `spec=ModuleType` restricts mock attributes to those present in Python's `ModuleType`. `torch.device` is not in `ModuleType`, causing `AttributeError` on access.
- Fix: Removed `spec=ModuleType` from `_make_torch_mock_module()`. Use plain `MagicMock()` without spec.
- Files modified: `tests/test_motionbert_lifter.py`
- Commit: 15b9641

**3. [Rule 2 - Missing] interfaces.py docstring update not needed**
- Plan T-2-3 stated "interfaces.py 에 변경 없음 확인 — 단 docstring에 composite engine 사용 가이드 추가"
- Confirmed PoseEngine Protocol already documents composite engine pattern implicitly via its existing Protocol definition. No docstring gap requiring action.
- Action: No change made (docstring already sufficient).

### Design Decision — _extract_mp_2d_from_pose_frames

Plan T-2-1 specified reconstructing MP normalized_landmarks for the H36M converter. Since `PoseFrame.keypoints_2d` stores only COCO-17 subset (not full MP33), full MP33 reconstruction is impossible. Implemented COCO-17 → MP index reverse mapping with 0.5 padding for unmapped joints (nose, 12 limb joints). This is lossless for the limb joints that MotionBERT uses; face joints (0-4 COCO) map to NaN in `h36m17_to_coco17_subset()` anyway.

## Known Stubs

None. All data flows are wired or explicitly gated (Task 5 checkpoint awaits belle GPU execution).

## Threat Flags

None found. No new network endpoints, auth paths, or schema changes introduced in this plan.

## Task 5 Checkpoint — Belle Pod Execution

Task 5 requires belle to run on the RunPod GPU Pod. The plan executor cannot run 5-video regression (no GPU, no S3 access).

Belle must execute on the RunPod Pod after this code is deployed:

```bash
cd /workspace/SunityMotion && git pull
cd backend
bash runpod_inference/setup.sh   # installs new deps, clones MotionBERT, checks weights
# (scp best_epoch.bin if first time on new Pod)

# Wave 2 regression — nlf vs MP+MotionBERT
python3 -m backend.research.evaluations.compare_engines \
  --engine nlf-vs-mediapipe-lifter \
  --motions ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin \
  --out backend/research/evaluations/reports/compare_lifter_$(date +%Y%m%d_%H%M).json \
  --bucket sunity-motion-pilot-videos
```

**Gate re-judgment criteria (D-14/D-15 + Plan 08 추가 항목):**

| Item | Gate | Criterion |
|------|------|-----------|
| D-14 | all_within_tolerance | score gap ≤5pt per video |
| D-15 ① | all_mediapipe_ge_70 | MP+lifter overall ≥70 (no false negative) |
| D-15 ② | all_top3_overlap_ok | Top-3 failures ≥2/3 overlap with NLF |
| D-15 ③ | all_avg_confidence_ok | avg_keypoint_confidence ≥0.5 |
| Plan 08 extra | over-smoothing check | stability scores vary across videos (not all 80+) |
| Plan 08 extra | line recovery | line dimension present in ≥3/5 videos |

**Belle response options:**
- "approved, proceed to Wave 3" → Plan 04 (NLF R&D isolation) + Plan 05 (atomic swap)
- "hold + over-smoothing concern" → stability too uniform → correction plan
- "hold + line issue" → line recovery < 50% vs NLF → recognizer tune plan
- "hold + partial pass" → some videos fail → threshold re-definition or video augmentation

## Self-Check: PASSED

Files confirmed present:
- backend/shared/python/sunity_shared/analysis/pose_lifters/__init__.py: FOUND
- backend/shared/python/sunity_shared/analysis/pose_lifters/motionbert_lifter.py: FOUND
- backend/shared/python/sunity_shared/analysis/pose_lifters/mediapipe_to_h36m17.py: FOUND
- backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_lifter_engine.py: FOUND
- backend/tests/test_motionbert_lifter.py: FOUND
- backend/tests/test_mediapipe_lifter_engine.py: FOUND
- backend/tests/test_pose_lifters_mediapipe_to_h36m17.py: FOUND

Commits confirmed:
- 15b9641: FOUND (feat T-1)
- d91373c: FOUND (feat T-2)
- e39b656: FOUND (chore T-3)
- 84c249a: FOUND (feat T-4)

---

## belle 5영상 Pod 검증 결과 — 4/5 PASS (2026-05-31)

**보고서 위치 (Pod 안)**: `backend/research/evaluations/reports/compare_lifter_20260531_*.json` / `.md`

### Wave 2 핵심 진전

| 모션 | Plan 06 MP 단독 | Plan 08 MP+lifter | NLF baseline | NLF 대비 |
|---|---|---|---|---|
| ref-climb | 18 | **85** | 58 | +27 |
| ref-foxtop-split | 3 | **75** | 62 | +13 |
| ref-foxtop | 8 | **90** | 64 | +26 |
| ref-invert | 33 | **92** | 65 | +27 |
| ref-sideway-spin | 52 | 64 | 81 | -17 |

평균: MP 단독 22.8 → MP+lifter 81.2 (3.5배). D-15① 0/5 → 4/5 PASS.

### 게이트 판정 (원래 룰 기준)

| 게이트 | 결과 | 해석 |
|---|---|---|
| D-14 all_within_tolerance ±5pt | FAIL | MP+lifter 가 NLF 보다 +13~+27 **높음** (잘못된 방향이 아니라 desired 방향) |
| D-15① all_mediapipe_ge_70 | FAIL (4/5) | ref-sideway-spin 만 64 |
| D-15② all_top3_overlap_ok | FAIL | NLF 진단을 ground truth 로 본 게이트 — Plan 06 도 0/5, 룰 한계 |
| D-15③ all_avg_confidence_ok | PASS | avg_conf 0.82~0.85 |

### Plan 07 의 over-smoothing 우려 — 완전히 기각

영상별 점수 차등 64~92 (분산 큼). MotionBERT 가 quality 차이를 제대로 평가 중. 5영상 모두 80+ 로 일정했으면 over-smoothing.

### belle 의사결정 — Path B

ref-sideway-spin 64 점이 진짜 약점 (측면 자세에서 MotionBERT lifter 가 H3.6M 정면 학습 한계). AlphaPose 2D 어댑터로 측면 보강 후 재실행 → 5영상 재측정 → 게이트 룰 재정의 (음방향 갭만 fail, 4/5 또는 80% threshold) → Wave 3 진입.

다음 plan: **01-09 AlphaPose spike (ref-sideway-spin 1영상)** → 통과 시 01-10 5영상 sweep + Wave 3 진입.

### Plan 08 belle 검증 중 발견한 코드 fix

| 커밋 | 내용 |
|---|---|
| `f8266ff` | RunPod requirements — numpy<2.0 → numpy<3 (opencv-python-headless 4.13 가 numpy 2.x 요구). Lambda 측 functions/ 는 numpy<2.0 유지 |

### Pod 환경 잔존물 (Plan 09 에서 재사용 — Terminate 후 새 Pod 셋업 시 setup.sh 가 복원)

- `/workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin` (belle Mac 백업 있음)
- `/workspace/models/pose_landmarker_heavy.task` (setup.sh 가 wget 으로 자동 다운로드)
- `backend/scripts/nlf_l_multi.torchscript` (setup.sh 가 GitHub release 자동 다운로드)
- `backend/yolo11n.pt` (ultralytics 가 첫 실행 시 자동)
- apt: libgles2 libegl1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 (setup.sh 박제)
- pip: mediapipe + opencv-python-headless + scipy + protobuf + einops + timm (setup.sh 박제)
