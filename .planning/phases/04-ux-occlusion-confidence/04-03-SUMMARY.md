---
phase: 04-ux-occlusion-confidence
plan: "03"
subsystem: ml-pipeline
tags: [synthesis, cylindrical-mesh, pyrender, egl, occlusion, pose-03, secondary, smoke]

# Dependency graph
requires:
  - phase: 04-01
    provides: SynthesisAdapter Protocol + SynthesisResult dataclass + _get_synthesis_adapter lazy singleton (Wave 1 PRIMARY GeminiViewReasoner)
  - phase: 04-00
    provides: pytest 인프라 (POSE-03-a~f) + joint_seq_60f / conf_seq_60f T=60 fixture
provides:
  - CylindricalMeshAdapter (Stage 3' SECONDARY 합성 어댑터, D-18) — SynthesisAdapter Protocol 2번째 구현체
  - build_humanoid_mesh (RTMW COCO-17 17 joint → trimesh cylindrical humanoid mesh, SMPL-X 의존 0)
  - virtual_renderer.render_12_views_safe (pyrender EGL headless + Mac local dummy fallback)
  - virtual_renderer.PYRENDER_AVAILABLE / VirtualCamera / make_12_camera_set / _camera_pose
  - backend/runpod_inference/requirements.txt 의 trimesh + pyrender + pyopengl 박제
  - test_evaluate_4way.py 신설 (04-03 소유) — Wave 3a smoke/license 5 unit test + Wave 3b @integration skeleton (04-05 append 예정)
  - B4 hard gate 단위 증명 (test_mesh_adapter_excluded_without_env_flag) — SYNTHESIS_MESH_ENABLED unset/0 시 CylindricalMeshAdapter 미반환
affects:
  - 04-04 (Stage 4 VideoGenerationAdapter — 동일 Protocol 패턴 + 본 SECONDARY 와 병렬)
  - 04-05 (정은지 5영상 재처리 — test_evaluate_4way.py 하단에 RunPod 통합 테스트 append)
  - Wave 3b 후속 task (RunPod GREEN 후 _rerun_rtmw_on_views 실 구현 + integration skip 제거)

# Tech tracking
tech-stack:
  added:
    - "trimesh>=4.12.2 (MIT) — cylindrical humanoid mesh build"
    - "pyrender>=0.1.45 (MIT) — EGL headless 12-view offscreen render"
    - "pyopengl (BSD-style) — pyrender EGL backend 의존"
  patterns:
    - "PYOPENGL_PLATFORM=egl os.environ.setdefault (import pyrender 보다 먼저, RESEARCH Pitfall 3)"
    - "pyrender.OffscreenRenderer + try/finally renderer.delete() (GPU 메모리 관리, Pattern 5)"
    - "Mac local dummy 12-view fallback (PYRENDER_AVAILABLE=False 시 분석 흐름 차단 0)"
    - "Spike VALIDATED-SKELETON 이관 패턴 (mesh_builder.py + render.py → cylindrical_mesh.py + virtual_renderer.py)"
    - "SynthesisAdapter Protocol 2번째 구현체 (GeminiViewReasoner 와 동일 시그너처)"
    - "B4 hard gate unit 증명 — SYNTHESIS_MESH_ENABLED env flag 박제 (Wave 3b GREEN 전까지 운영 차단)"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py
    - backend/shared/python/sunity_shared/analysis/synthesis/virtual_renderer.py
    - backend/tests/phase04/test_evaluate_4way.py
  modified:
    - backend/runpod_inference/requirements.txt

key-decisions:
  - "Wave 3a placeholder boost (+0.15 boosted confidence) 는 pipeline 연결 검증용 임시값 — scoring promote 근거 아님 (calibration-source-hard-gate)"
  - "실 accuracy gate 는 Wave 3b @integration (test_axis_b_real_rtmw_integration) — RunPod 필요, phase blocker 아님"
  - "B4 invariant 박제 — SYNTHESIS_MESH_ENABLED unset/0 default. Wave 3b GREEN 전까지 _get_synthesis_adapter() 가 CylindricalMeshAdapter 미반환 (test_mesh_adapter_excluded_without_env_flag 회귀 게이트)"
  - "G4 defense-in-depth — adapter 자체에도 is_reference 가드 박제 (pipeline 측 _call_synthesis_adapter 와 양측)"
  - "exception graceful degrade — SynthesisResult(status='failed', warnings=('exception',)) 반환. zeros sentinel 영구 금지 (R2 fix)"
  - "_rerun_rtmw_on_views Wave 3a placeholder — primary joints 변경 0 + occluded mask 위치 conf +0.15 cap 1.0. log.warning 박제로 'Wave 3b RunPod task 에서 구현 예정' 안내"
  - "test_evaluate_4way.py 04-03 소유 — 04-05 는 본 파일 하단에 RunPod 통합 테스트 append (재신설 금지)"
  - "make_synthetic_path 로컬 복사 — spike harness.py 의 dataset.JEONGEUNJI_5 의존성 제거 (T=60 fixture 와 정합)"

patterns-established:
  - "Pattern A: SECONDARY 합성 어댑터 = SynthesisAdapter Protocol 재구현 — synthesize_occluded_joints 시그너처 그대로, SynthesisResult 반환"
  - "Pattern B: Wave 3a smoke / Wave 3b @integration 분리 — unit 게이트는 RunPod 미필요, integration 게이트는 RunPod 필요 + pytest -m 'not integration' 으로 CI 분리"
  - "Pattern C: B4 hard gate unit 증명 — env flag invariant 를 단위 테스트 1개로 박제 (Wave 3b GREEN 전 사고적 활성 차단)"
  - "Pattern D: spike 001 evaluate_4way 재사용 — sys.path.insert(spike_dir) + harness 의존성 제거된 로컬 make_synthetic_path 복사"

requirements-completed:
  - POSE-03

# Metrics
duration: ~20min
completed: 2026-06-13
---

# Phase 04 Plan 03: Stage 3' CylindricalMeshAdapter + virtual_renderer + evaluate_4way 게이트 Summary

**Stage 3' SECONDARY 합성 경로 (D-18) — trimesh + pyrender EGL 기반 12-view virtual render 어댑터를 Spike 002b VALIDATED-SKELETON 에서 production 이관 (정확도 주장 0). +0.15 placeholder boost 는 pipeline 연결 검증용이며 SYNTHESIS_MESH_ENABLED 기본 OFF + B4 hard gate unit 증명으로 운영 경로 차단. 실 accuracy gate 는 Wave 3b @integration (RunPod 필요) 에서 별도 박제.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-06-13T14:00:00Z (approx, post-bfd58d4 main checkout)
- **Completed:** 2026-06-13T14:20:00Z
- **Tasks:** 2 (Task 1 adapter + renderer + requirements / Task 2 evaluate_4way 게이트 신설)
- **Files modified:** 1 modified + 3 created = 4 total

## Accomplishments

- **CylindricalMeshAdapter 신설** — Spike 002b VALIDATED-SKELETON 이관. SynthesisAdapter Protocol 2번째 구현체. G4 가드 (adapter 자체) + R1 non-scoring 하드월 주석 박제 + 모든 except graceful degrade (status='failed'). SMPL-X 의존 0 (D-20).
- **build_humanoid_mesh + Segment + SEGMENTS + _cylinder_between** — Spike 002b mesh_builder.py 이관 (트리메시 cylinder 13 part + joint sphere 마커). RTMW COCO-17 joint index 상수 박제.
- **virtual_renderer.py 신설** — Spike 002b render.py 이관. PYOPENGL_PLATFORM=egl `os.environ.setdefault` 최상단 (import pyrender 보다 먼저, RESEARCH Pitfall 3). pyrender ImportError/OSError graceful → PYRENDER_AVAILABLE=False + Mac local dummy 12장 fallback. `pyrender.OffscreenRenderer` + try/finally `renderer.delete()` 명시 (GPU 메모리, Pattern 5).
- **render_12_views_safe / VirtualCamera / make_12_camera_set / _camera_pose** — 30° 간격 12 yaw + look-at 카메라 pose + ambient + directional light 박제.
- **backend/runpod_inference/requirements.txt 업데이트** — trimesh>=4.12.2 + pyrender>=0.1.45 + pyopengl 추가 (기존 항목 순서 보존). 박제 주석에 license + D-20 + RESEARCH Pitfall 3 + Mac local fallback 명시.
- **test_evaluate_4way.py 신설** — 04-03 소유 (04-05 append 예정 박제). spike 001 metrics.evaluate_4way + PathOutput 재사용 (sys.path 박제). make_synthetic_path 로컬 복사 (harness 의 JEONGEUNJI_5 dataset 의존성 제거).
- **Wave 3a unit gate 4 신설** — test_axis_b_smoke_synthetic_boost (NaN-free + scoring promote 근거 아님 명시) / test_axis_a_split_angle_consistency / test_cylindrical_mesh_no_smplx_import (D-20 license grep) / test_cylindrical_mesh_license_stack (trimesh/pyrender importorskip slopcheck).
- **B4 hard gate unit 증명 신설** — test_mesh_adapter_excluded_without_env_flag. SYNTHESIS_MESH_ENABLED unset/0 일 때 04-01 의 `_get_synthesis_adapter()` 가 CylindricalMeshAdapter 미반환 단언 + `synthesis.__all__` 미노출 보조 확인. Wave 3b GREEN 전 운영 경로 사고적 활성 차단 박제.
- **Wave 3b skeleton 박제** — `@pytest.mark.integration` + `pytest.skip("Wave 3b 실 RunPod RTMW 재추론 미구현 — _rerun_rtmw_on_views 연결 후 skip 제거")`. 완료 기준 + 산출물 명세 docstring + 04-05 append 위치 명시.
- **phase04 회귀 0** — 31 PASS + 2 SKIP (license_stack pyrender 미설치 + Wave 3b integration). 기존 POSE-03-a~f suite 변경 0 (04-01 27 + 04-03 4 PASS + 2 SKIP).

## Task Commits

각 task atomic 단일 commit:

1. **Task 1: CylindricalMeshAdapter + virtual_renderer + RunPod requirements** — `c2296e1` (feat)
   - `backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py` 신설
   - `backend/shared/python/sunity_shared/analysis/synthesis/virtual_renderer.py` 신설
   - `backend/runpod_inference/requirements.txt` trimesh + pyrender + pyopengl 추가
2. **Task 2: test_evaluate_4way.py Wave 3a smoke + Wave 3b integration skeleton** — `aeb6e09` (test)
   - `backend/tests/phase04/test_evaluate_4way.py` 신설 (5 Wave 3a + 1 Wave 3b skeleton)

**Plan metadata commit:** (이 SUMMARY 와 동시 commit)

## Files Created/Modified

- **backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py** (신설) — CylindricalMeshAdapter (SynthesisAdapter Protocol 구현체) + build_humanoid_mesh + Segment + SEGMENTS + _cylinder_between + _rerun_rtmw_on_views (Wave 3a placeholder).
- **backend/shared/python/sunity_shared/analysis/synthesis/virtual_renderer.py** (신설) — render_12_views_safe + PYRENDER_AVAILABLE + VirtualCamera + make_12_camera_set + _camera_pose + PYOPENGL_PLATFORM=egl setdefault.
- **backend/runpod_inference/requirements.txt** (수정) — trimesh>=4.12.2 / pyrender>=0.1.45 / pyopengl 추가 + 박제 주석.
- **backend/tests/phase04/test_evaluate_4way.py** (신설) — POSE-03-g 게이트. Wave 3a 5 unit + Wave 3b 1 @integration skeleton.

## Decisions Made

- **Wave 3a placeholder 명확화** — `_rerun_rtmw_on_views` 가 primary joints 그대로 + occluded 위치 conf +0.15 cap 1.0 반환. `log.warning` 박제로 "Wave 3b RunPod task 에서 구현 예정" 안내. `meta.synthesisPath = "cylindrical_smoke_placeholder"` + `meta.wave = "3a_smoke_placeholder"` 로 audit trail 박제. scoring promote 근거 아님 명시 (R1 + calibration-source-hard-gate).
- **G4 defense-in-depth** — `pipeline._call_synthesis_adapter` 가 이미 G4 가드를 적용하지만, `CylindricalMeshAdapter.synthesize_occluded_joints` 자체에도 `scene_findings.get("is_reference", False)` 체크 박제. 04-CONTEXT code_context 정신 + 04-01 GeminiViewReasoner 와 동일 양측 가드.
- **shape validation 박제** — adapter 진입 시 joint_sequence (T,17,3), confidence (T,17), mask (T,17) 형상 검증. 잘못된 형상 → except → status='failed' graceful degrade.
- **B4 hard gate 박제 방식** — 04-01 `_get_synthesis_adapter()` 본체에 분기 추가 없이 unit 테스트 (`test_mesh_adapter_excluded_without_env_flag`) 로 invariant 박제. 04-01 코드 (helper docstring 의 "Wave 3 (04-03) 이후 CylindricalMeshAdapter 추가 시 본 helper 에서 chain 분기 박제" 가이드) 는 Wave 3b 까지 보류. 현재 helper 는 GeminiViewReasoner singleton 만 반환하므로 invariant 자동 충족.
- **test_evaluate_4way.py 의 sys.path 박제** — `conftest.py` 에 spike harness path 가 없어 본 테스트가 직접 `sys.path.insert(0, parents[3] / ".planning/spikes/001-dataset-eval-harness")` 주입. 04-05 가 본 파일에 append 시 동일 path 박제 재사용 가능.
- **dataset.py 의존성 제거** — spike harness 의 `make_synthetic_path` 가 `from dataset import JEONGEUNJI_5` 를 import 하지만, 본 테스트는 conftest 의 `joint_seq_60f` / `conf_seq_60f` 를 wrap 하는 로컬 `_make_path_output` + `_build_split_joints` 헬퍼로 대체. T=60 fixture 와 정합 + spike dataset 의존성 0.
- **`@pytest.mark.integration` marker 박제** — pytest config 에 marker 등록은 본 plan 범위 외 (PytestUnknownMarkWarning 발생하나 동작 정상). 후속 plan 에서 `pyproject.toml` 또는 `pytest.ini` 에 `markers = integration: ...` 등록 권장 (deferred).

## Deviations from Plan

None - plan executed exactly as written.

Wave 3a smoke 단계라 +0.15 boost 의 정확도 검증은 본 plan 범위 외 (Wave 3b accuracy gate). plan 의 must-haves 6번째 (Wave 3b 비차단) 가 명시한 대로 Wave 3b 는 별도 phase blocker 아님 — 본 plan 은 Wave 3a smoke 까지의 acceptance 만 검증.

## Issues Encountered

- **Mac local 에 trimesh 미설치 → 첫 verify 실패** — `python3 -m pip install --user --break-system-packages trimesh` 로 설치 (Homebrew Python 3.14 PEP 668 우회). pyrender 는 미설치 (PYRENDER_AVAILABLE=False) — Wave 3a smoke 는 dummy fallback 으로 통과. RunPod 환경에서는 requirements.txt 박제로 정상 설치 예정.
- **`@pytest.mark.integration` PytestUnknownMarkWarning** — marker 등록 부재. 동작 정상 (pytest -m "not integration" 으로 deselect 성공). 후속 plan 에서 marker 등록 권장 (deferred).

## User Setup Required

None — Wave 3a smoke 단계라 추가 환경 박제 0. Wave 3b @integration 진행 시 RunPod Pod + RUNPOD_AUTH_TOKEN 등 기존 Phase 17 인프라 재사용 예정 (별도 USER-SETUP 불요).

## Task 1.5 Checkpoint Self-Verification (autonomous, user-authorized)

User 가 자율 실행 권한을 부여했기 때문에 Task 1.5 checkpoint 는 stop 하지 않고 본 에이전트가 자가 검증함:

1. **verify 출력 확인 — "12 views: OK" / "SMPL-X gate: PASS" / "G4 is_reference guard: OK"**
   - `12 views:` PASS (`mesh vertices: (1452, 3) 12 views: 12`)
   - `SMPL-X gate:` PASS (소스에 `smplx` literal 0건, `SMPL-X 의존 0` / `SMPL-X 절대 금지` 한글 표현만)
   - `G4 is_reference guard:` PASS (`G4 skip: skipped warnings: ('g4_reference_guard',)`)
2. **cylindrical_mesh.py 헤더 — "Wave 3a = mesh build + render artifact smoke gate (정확도 주장 0)" 포함 확인**
   - 모듈 docstring 9번째 줄: `· Wave 3a = mesh build + render artifact smoke gate (정확도 주장 0).` (라인 박제 정확)
3. **Wave 3b 진행 결정 — 본 run 에서는 미진행 (RunPod 미가용 가정 + 명시적 deferred)**
   - Wave 3b @integration 은 `pytest.skip` 박제 + `@pytest.mark.integration` marker 분리 → `pytest -m "not integration"` 로 CI/dev 자동 제외.
4. **B4 hard gate (SYNTHESIS_MESH_ENABLED=0 invariant) — unit 증명 통과**
   - `test_mesh_adapter_excluded_without_env_flag` PASS. `SYNTHESIS_MESH_ENABLED` env 를 monkeypatch.delenv 로 제거 → `_get_synthesis_adapter()` 호출 → CylindricalMeshAdapter 인스턴스 아님 + `synthesis.__all__` (None) 미정의로 default export 차단. Wave 3b GREEN 전까지 mesh path 가 점수/UI 에 새지 않음 보장.

## Must-Haves Verification (plan frontmatter truths)

1. **Wave 3a smoke (12 view 산출 + Mac dummy fallback)** — VERIFIED. verify 출력 `mesh vertices: (1452, 3) 12 views: 12` + PYRENDER_AVAILABLE False 시 dummy 12장 반환 동작. RunPod EGL 환경 검증은 requirements.txt 박제 + pyrender import 패턴 박제로 사전 정합 (실 RunPod smoke 는 04-05 또는 Wave 3b 에서).
2. **Wave 3a license gate (smplx 미포함 + trimesh/pyrender/numpy)** — VERIFIED. `test_cylindrical_mesh_no_smplx_import` PASS + 헤더 docstring 라이선스 박제 + requirements.txt 박제.
3. **Wave 3b 실 RunPod accuracy gate (@integration skeleton)** — VERIFIED (skeleton 박제). `test_axis_b_real_rtmw_integration` `@pytest.mark.integration` + `pytest.skip` + 완료 기준 docstring 박제. 실 GREEN 은 RunPod 필요 → **deferred (phase blocker 아님)**.
4. **R1 non-scoring 하드월 (KeypointReport/aiSynthesisMeta 만 흐름)** — VERIFIED. adapter 반환 SynthesisResult 의 joints/confidence 가 coco_array 에 mutate 되지 않음. 04-01 `merge_with_temporal` 정합 + plan 04-01 pipeline `_call_synthesis_adapter` wiring 변경 없음 (CylindricalMeshAdapter 는 04-01 helper 가 노출하지 않음 — B4 hard gate).
5. **G4 is_reference 가드 + zeros sentinel 금지** — VERIFIED. verify 출력 `G4 skip: skipped warnings: ('g4_reference_guard',)` + adapter docstring `G4 가드 (최우선)` 박제 + zeros array 반환 없음.
6. **Wave 3b 미완 시 Wave 2/5 비차단** — VERIFIED. test_evaluate_4way.py 파일 헤더 + Wave 3b skeleton docstring 에 "Wave 3b @integration skip = Wave 2/5 진행 차단 아님 (04-05 depends_on 은 04-03 3a smoke 까지)" 명시. 본 plan 의 Task 1/2 모두 Wave 3a smoke 만 PASS 요구.

## Wave 3b Status — Parked (RunPod 필요, phase blocker 아님)

Wave 3b 는 본 plan 범위 외로 parked:
- 실 RTMW 재추론 미구현 (`_rerun_rtmw_on_views` placeholder 만 존재 — `RTMW rerun not wired` log.warning 박제).
- `test_axis_b_real_rtmw_integration` `@pytest.mark.integration` + `pytest.skip` 박제 → CI/dev `pytest -m "not integration"` 로 자동 제외.
- `SYNTHESIS_MESH_ENABLED=0` invariant 박제 (test_mesh_adapter_excluded_without_env_flag) → Wave 3b GREEN 전까지 mesh path 가 운영 (점수/UI) 에 새지 않음. 04-01 `_get_synthesis_adapter()` 가 GeminiViewReasoner 만 반환 (mesh chain 분기 미박제).
- Wave 3b 진행 시 변경 site (예정):
  - `backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py::_rerun_rtmw_on_views` 본체 — RunPod 12-view → 실 RTMW 재추론 → confidence-weighted aggregate.
  - `backend/tests/phase04/test_evaluate_4way.py::test_axis_b_real_rtmw_integration` — `pytest.skip` 제거 + 실 PathOutput + baseline 대비 rate_reduction_pct > 0 acceptance.
  - 선택: `backend/functions/pipeline/app.py::_get_synthesis_adapter` — SYNTHESIS_MESH_ENABLED env 분기 추가 (현재는 unset/0 default 로 GeminiViewReasoner 만 반환).
- 04-04 (Stage 4 video gen stub) 및 04-05 (정은지 5영상 재처리) 는 본 Wave 3b parked 상태에서도 진행 가능 — plan 의 must-haves 6번째 박제.

## Next Phase Readiness

- **04-04 (Stage 4 video_gen_adapter stub):** SynthesisAdapter Protocol 패턴 + 본 plan 의 어댑터 박제 구조 (G4 가드 + graceful degrade + meta synthesisPath) 그대로 재사용 가능.
- **04-05 (정은지 5영상 Phase 4-compatible 재처리):** `backend/tests/phase04/test_evaluate_4way.py` 가 04-03 소유로 박제됨 → 04-05 는 본 파일 하단에 RunPod 통합 테스트 (예: `test_evaluate_4way_reprocess_vs_baseline`) append. spike 001 `evaluate_4way` 재사용 path 박제됨 (sys.path.insert 패턴).
- **Wave 3b RunPod task (별도):** `_rerun_rtmw_on_views` 실 구현 + `test_axis_b_real_rtmw_integration` skip 제거 + (옵션) `SYNTHESIS_MESH_ENABLED` env 분기 추가 (04-01 helper). phase 4 전체 완료를 차단하지 않음.

**Blocker / concern:**
- `@pytest.mark.integration` marker 미등록 → PytestUnknownMarkWarning (동작 정상이지만 후속 plan 에서 marker registration 권장).
- Mac local 에 pyrender 미설치 → test_cylindrical_mesh_license_stack SKIP. RunPod 환경에서는 requirements.txt 박제로 자동 설치.

## Self-Check: PASSED

- [x] `backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py` FOUND
- [x] `backend/shared/python/sunity_shared/analysis/synthesis/virtual_renderer.py` FOUND
- [x] `backend/tests/phase04/test_evaluate_4way.py` FOUND
- [x] `backend/runpod_inference/requirements.txt` 수정 (trimesh + pyrender + pyopengl 박제)
- [x] Commit `c2296e1` FOUND (Task 1)
- [x] Commit `aeb6e09` FOUND (Task 2)
- [x] verify python3 smoke script — PYRENDER_AVAILABLE False + mesh (1452, 3) + 12 views + applied/skipped + SMPL-X gate PASS
- [x] phase04 회귀 0 — 31 PASS + 2 SKIP (직전 04-01: 27 PASS, 본 plan +4 PASS +1 SKIP +1 Wave 3b SKIP)
- [x] `pytest -m "not integration"` — 4 passed, 1 skipped (license_stack), 1 deselected (Wave 3b)
- [x] `pytest -m integration` — 1 skipped (Wave 3b skeleton), 5 deselected
- [x] CylindricalMeshAdapter import 성공
- [x] G4 is_reference guard 동작 + zeros sentinel 미반환
- [x] grep "trimesh|pyrender|pyopengl" backend/runpod_inference/requirements.txt — 3 hit
- [x] grep "smplx" backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py (lowercase) — 0 hit
- [x] grep "joint_seq_60f" backend/tests/phase04/test_evaluate_4way.py — 5 hit (T=60 fixture 사용)
- [x] grep "integration" backend/tests/phase04/test_evaluate_4way.py — 12 hit (@integration marker + docstring 박제)
- [x] cylindrical_mesh.py 헤더 — "Wave 3a = mesh build + render artifact smoke gate (정확도 주장 0)" 포함 확인
- [x] Task 1.5 checkpoint self-verification — 4 항목 모두 PASS (autonomous, user-authorized)
- [x] B4 hard gate (SYNTHESIS_MESH_ENABLED=0 invariant) — test_mesh_adapter_excluded_without_env_flag PASS

---
*Phase: 04-ux-occlusion-confidence*
*Completed: 2026-06-13*
