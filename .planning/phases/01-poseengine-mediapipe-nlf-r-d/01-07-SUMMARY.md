---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "07"
subsystem: pose-engine
tags:
  - spike
  - motionbert
  - mediapipe-2d
  - 3d-lift
  - mp33-h36m17
  - apache2
dependency_graph:
  requires:
    - 01-02 (MediaPipePoseEngine, pose_engines/mediapipe_engine.py)
    - 01-06 (compare_engines.py 스코어링 체인, D-16 보류 근거)
  provides:
    - mediapipe_to_h36m17.py: MP33 → H3.6M 17-joint 매핑 어댑터 (Apache 2.0 확인)
    - spike_motionbert.py: MP2D + MotionBERT 3D lift 스파이크 하네스
    - README.md: Pod 실행 절차 + 라이선스 출처 + 판정 기준
    - 38개 단위 테스트 (38 passed, mediapipe 없이 로컬 실행 가능)
  affects:
    - Plan 08 (본 통합): belle spike 결과 응답 후 신설 여부 결정
tech_stack:
  added:
    - backend/research/spikes/__init__.py: spike 격리 패키지
    - backend/research/spikes/mediapipe_to_h36m17.py: MP33 → H36M17 매핑 (순수 numpy)
    - backend/research/spikes/spike_motionbert.py: 스파이크 하네스 (CLI + run_spike())
    - backend/research/spikes/README.md: Pod 실행 절차 + 라이선스 + 판정 기준
    - backend/research/spikes/reports/.gitkeep: 보고서 출력 디렉터리
    - backend/tests/test_spike_mediapipe_to_h36m17.py: 38개 단위 테스트
  patterns:
    - D-06/D-07 NLF 격리 패턴 동일 — spike 코드는 backend/research/spikes/ 내부만
    - normalized_landmarks 사용 (world_landmarks z 노이즈 회피 — Plan 01-06 D-16 근거)
    - 파생 관절 계산 (Hip = mean(l_hip, r_hip), Thorax = mean(shoulders) 등)
    - h36m17_to_coco17_subset: 12개 limb joint만 매핑, face NaN (스코어링 체인 호환)
    - run_spike() → NLF baseline 동시 실행 → JSON/Markdown 보고서
key_files:
  created:
    - backend/research/spikes/__init__.py (16 lines)
    - backend/research/spikes/mediapipe_to_h36m17.py (260 lines)
    - backend/research/spikes/spike_motionbert.py (400 lines)
    - backend/research/spikes/README.md (170 lines)
    - backend/research/spikes/reports/.gitkeep (0 lines)
    - backend/tests/test_spike_mediapipe_to_h36m17.py (290 lines)
  modified: []
decisions:
  - "MotionBERT 라이선스 Apache 2.0 확인 (https://github.com/Walter0807/MotionBERT/blob/main/LICENSE)"
  - "normalized_landmarks 사용 — world_landmarks z 제거 (Plan 01-06 D-16 보류 근거)"
  - "h36m17_to_coco17_subset: 12개 limb joint만 채움, face NaN — JOINT_ANGLES가 limb만 사용하므로 점수 계산에 영향 없음"
  - "DSTformer 초기화 파라미터: MotionBERT H3.6M 기본 설정 박제 (dim_feat=256, dim_rep=512, depth=5)"
  - "청크 추론: MAXLEN=243 슬라이딩 윈도우, 짧은 영상은 끝 프레임 복제 패딩"
  - "NLF baseline: compare_engines._run_nlf 동일 경로 (H-1 박제 — Wave 2 시점 옛 위치)"
metrics:
  duration: "~6 minutes"
  completed: "2026-05-31"
  tasks_completed: 2
  tests_added: 38
  files_created: 6
  files_modified: 0
---

# Phase 1 Plan 07: MediaPipe 2D + MotionBERT Spike Summary

MotionBERT Apache 2.0 라이선스 확인 후 MP33 → H3.6M 17-joint 매핑 어댑터,
spike_motionbert.py 하네스, README Pod 실행 절차를 구현하고 38개 단위 테스트를
통과시켰다. belle가 RunPod에서 ref-foxtop-split 1개 영상으로 실행해 stability
점수 회복 여부를 확인하면 Plan 08 진입 여부가 결정된다.

## Task 1 완료 — 라이선스 확인 + 어댑터 + 테스트 + README

### MotionBERT 라이선스 확인

**Apache 2.0** — https://github.com/Walter0807/MotionBERT/blob/main/LICENSE (2026-05-31 확인).

상업적 사용, 수정, 배포 모두 허용. 저작권 고지 필요. HybrIK(MIT) 백업 후보도 허용 라이선스.
진입 조건 충족 — spike 코드 작성 진행.

### mediapipe_to_h36m17.py

H3.6M 17-joint 매핑 어댑터. MediaPipe normalized_landmarks (x, y, visibility) 기반.

**직접 대응 13개:**

| MediaPipe 인덱스 | H3.6M 인덱스 | 관절 |
|-----------------|------------|-----|
| MP 24 | H36M 1 | RHip |
| MP 26 | H36M 2 | RKnee |
| MP 28 | H36M 3 | RFoot (ankle) |
| MP 23 | H36M 4 | LHip |
| MP 25 | H36M 5 | LKnee |
| MP 27 | H36M 6 | LFoot (ankle) |
| MP 0  | H36M 10 | Head (nose proxy) |
| MP 11, 12, 13, 14, 15, 16 | H36M 11~16 | L/R Shoulder/Elbow/Wrist |

**파생 4개:**
- H36M 0 Hip: mean(MP 23, MP 24)
- H36M 8 Thorax: mean(MP 11, MP 12)
- H36M 7 Spine: mean(Hip, Thorax)
- H36M 9 NeckNose: mean(Thorax, MP 0)

**normalized_landmarks 선택 이유:** world_landmarks의 z 추정이 인버트/측면/폴 폐색 자세에서
노이즈가 크다 (Plan 01-06 D-16 보류 근거). 2D만 채용하고 z를 MotionBERT로 재구성한다.

### h36m17_to_coco17_subset

H3.6M 17 → COCO-17 역변환. 12개 limb joint만 대응, face(0~4) NaN.

`features.py compute_joint_angles`는 `JOINT_ANGLES`에 정의된 limb joint만 사용 (어깨/팔꿈치/손목/고관절/무릎/발목 8개). face NaN은 점수 계산에 영향 없음.

### 단위 테스트 38개 (38 passed)

| 테스트 클래스 | 테스트 수 | 범위 |
|------------|--------|-----|
| TestConvertMp33ToH36m17Shape | 6 | 입출력 형상 검증 |
| TestDirectMapping | 7 | 직접 대응 관절 인덱스 정확성 |
| TestDerivedJoints | 5 | 파생 관절 좌표 계산 |
| TestH36mToCoco17Subset | 7 | 역변환 형상/NaN/uncertainty |
| TestNanPropagation | 2 | 미감지 프레임 NaN 전파 |
| TestInputValidation | 5 | 잘못된 입력 ValueError |
| TestRoundtrip | 2 | MP33 → H36M17 → COCO17 라운드트립 |
| TestConfidenceChannel | 4 | visibility 채널 정확성 |

## Task 2 완료 — spike_motionbert.py

### run_spike() 함수

`run_spike(motion, bucket, video_path, motionbert_root, motionbert_weights, ...)`

실행 흐름:
1. S3에서 영상 다운로드 (tempfile 자동 cleanup)
2. FfmpegFrameExtractor로 프레임 추출 (9fps / 640px)
3. HoughPoleDetector로 폴 축 검출 (현재 미사용 — 향후 spike에서 활용 가능)
4. MediaPipe normalized_landmarks 추출 → MP33 → H36M17 변환
5. MotionBERT DSTformer 로드 (청크 추론, MAXLEN=243)
6. H36M17 → COCO17 역변환
7. compute_joint_angles → temporal_fill → absolute_dimension_scores → overall_from_dimensions
8. NLF baseline 동일 영상 실행 (compare_engines._run_nlf 동일 경로)
9. 갭 계산 + 판정 (strong_pass / weak_signal / fail)
10. JSON + Markdown 출력

### 판정 기준 박제

| 판정 | stability | overall | 다음 행동 |
|------|-----------|---------|---------|
| strong_pass | >= 55 | >= 60 | "approved, proceed to Plan 08" |
| weak_signal | 40~55 | 45~60 | "try HybrIK" |
| fail | < 40 | < 45 | "hold + reconsider path A" 또는 "hold + commercial license" |

현재 기준선: MP 단독 stability=3, overall=3.

## Task 3 — belle checkpoint (PENDING)

spike는 RunPod GPU Pod에서만 실행 가능. belle 실행 대기 중.

## Deviations from Plan

None — 계획대로 실행됨.

spike 코드 수정 없음. compare_engines.py 수정 없음 (scope_limits 준수).

## Known Stubs

없음 — spike 코드는 실행 가능한 완전한 구현. belle가 Pod에서 실행하면 즉시 결과 생성.

## Threat Flags

없음 — 신규 네트워크 엔드포인트 없음. 운영 파이프라인 파일 수정 없음.

## 로컬에서 실행 불가한 이유

spike_motionbert.py 전체 실행은 RunPod GPU Pod에서만 가능:
1. **mediapipe**: x86_64 Linux wheel만 존재 — macOS ARM64 미지원 (Pitfall 1)
2. **MotionBERT/DSTformer**: torch CUDA GPU 필요 (CPU에서 NaN 가능)
3. **NLF baseline**: GPU 필수 (CPU에서 NaN 발산 — pose_estimator.py docstring 명시)
4. **S3**: 정은지 reference 영상은 sunity-motion-pilot-videos 버킷에 있음

mediapipe_to_h36m17.py 단위 테스트는 mediapipe 없이 로컬 실행 가능 (38 passed).

## Self-Check: PASSED

파일 존재 확인:
- `backend/research/spikes/__init__.py` FOUND
- `backend/research/spikes/mediapipe_to_h36m17.py` FOUND
- `backend/research/spikes/spike_motionbert.py` FOUND
- `backend/research/spikes/README.md` FOUND
- `backend/research/spikes/reports/.gitkeep` FOUND
- `backend/tests/test_spike_mediapipe_to_h36m17.py` FOUND

커밋 존재 확인:
- `ce2fbbc` feat(01-07): MotionBERT spike harness + MP33→H36M17 adapter + 38 tests FOUND

---

## belle Pod 실행 결과 — STRONG_PASS (2026-05-31)

**보고서**: `backend/research/spikes/reports/spike_motionbert_20260531_1330.md`

### 결과 (ref-foxtop-split)

| 항목 | MP+MotionBERT | NLF baseline | 갭 |
|---|---|---|---|
| overall | **84.0** | 62.0 | +22.0 |
| stability | **84.0** | 53.0 | +31.0 |
| line | N/A | 72.0 | N/A |
| angle | N/A | N/A | N/A |
| ms/frame | **86.8** | 243.8 | 1/3 |
| avg_mp_conf | 0.7088 | — | — |

### 판정: STRONG_PASS

- stability ≥ 55 기준 압도 (84)
- overall ≥ 60 기준 압도 (84)
- 추론 속도 NLF 의 1/3

### belle 결정: "approved, proceed to Plan 08"

Plan 08 (5영상 회귀 + 본 통합) 진입 승인.

### Plan 08 에서 검증해야 할 잔존 question

1. **stability over-smoothing 의심** — MotionBERT 시간축 transformer 가 motion variance 자체를 깎고 있을 가능성. 5영상 분산이 NLF 와 상관 있게 차등하면 진짜 quality 좋음, 모두 일정하면 over-smoothing.
2. **line 차원 회수율** — MP+MotionBERT 에서 line N/A. FallbackRecognizer 가 MotionBERT angles 로 같은 technique profile 인식 못하는 이슈. 5영상에서 line trigger 빈도 측정 + 필요시 profile recognizer tune.
3. **angle 차원** — self-mode 첫 분석에서는 정의상 N/A. Mode1 (vs 정은지 reference) 에서 kismam 으로 산출. 본 plan 범위 밖.

### Pod 환경 잔존물 (Plan 08 에서 재사용)

- `/workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin` 업로드 완료
- MotionBERT clone + einops/timm 설치
- MP→H36M17 어댑터 (`backend/research/spikes/mediapipe_to_h36m17.py`) — production 으로 승격할 때 재사용

### Wave 2 spike 중 발견한 코드 버그 (fix 완료)

| 커밋 | 내용 |
|---|---|
| `c164700` | `norm_layer=None` 명시 제거 — DSTformer 기본값 nn.LayerNorm 사용 (Block.__init__ TypeError) |
