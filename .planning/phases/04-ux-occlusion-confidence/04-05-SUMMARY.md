---
phase: "04"
plan: "05"
subsystem: backend-scripts
tags: [reference-reprocess, versioned-write, g4-guard, runpod-integration, phase4]
dependency_graph:
  requires:
    - "04-01: synthesis interfaces + is_reference G4 guard"
    - "04-03: evaluate_4way harness + cylindrical mesh Wave 3a smoke"
  provides:
    - "reprocess_reference_motions_phase4.py: 정은지 5영상 Phase 4 재처리 스크립트 (RunPod GPU 전용)"
    - "rollback_reference_motions_phase4.py: active pointer rollback 스크립트"
    - "test_reprocess_reference_g4.py: G4 guard behavioral + dry-run schema + versioned write 검증 (4 GREEN)"
    - "test_evaluate_4way.py: RunPod 통합 테스트 append (harness_smoke_60f GREEN, reprocess_vs_baseline SKIP/XFAIL)"
  affects:
    - "Firestore reference/{id}/versions/phase4_v1 (RunPod 실행 후)"
    - "Firestore reference/{id} top-level (active flip 후)"
tech_stack:
  added: []
  patterns:
    - "versioned/atomic write: reference/{id}/versions/phase4_v1 → schema gate → active pointer flip"
    - "FakeSynthesisAdapter behavioral test: 합성 adapter 호출 0 행위 증명 (AST 검색 폐기)"
    - "FakeFirestoreClient behavioral test: write path 정확 일치 단언 (HIGH-2)"
key_files:
  created:
    - backend/scripts/reprocess_reference_motions_phase4.py
    - backend/scripts/rollback_reference_motions_phase4.py
    - backend/tests/phase04/test_reprocess_reference_g4.py
  modified:
    - backend/tests/phase04/test_evaluate_4way.py
decisions:
  - "G4 가드 행위 테스트 패턴: FakeSynthesisAdapter 주입 — AssertionError raise = G4 위반 감지, 미발생 = G4 정상 작동 (D-10, BLOCKER-1)"
  - "FakeFirestoreClient 주입으로 write path == reference/{id}/versions/phase4_v1 행위 단언 — AST constant 검색 폐기 (HIGH-2)"
  - "test_evaluate_4way_harness_smoke_60f 에 @pytest.mark.runpod 미부여 — 로컬에서 GREEN 필수 (-m 'not runpod' 통과)"
  - "dry-run 모드: S3/GPU 없이 schema 구조만 검증 (behavioral test 주입용 _dry_run=True 파라미터)"
metrics:
  duration: "~15 min"
  completed_date: "2026-06-14"
  tasks_completed: 2
  tasks_pending: 1
  files_created: 3
  files_modified: 1
---

# Phase 4 Plan 05: Reference Reprocess + Versioned Write + G4 Guard Tests Summary

정은지 5영상 Phase 4-compatible 재처리 스크립트 (versioned/atomic write + rollback) 및 G4 가드 behavioral 테스트 작성. reprocess 스크립트는 RunPod GPU 전용이며 is_reference=True G4 가드로 합성 트리거 0, joints3d flat BLOCKER-2 정합, 5개 전부 schema gate 통과 시에만 active pointer flip.

## Tasks Completed

### Task 1: reprocess + rollback 스크립트 + G4 behavioral 테스트

**Commit:** `daf6803`
**Files:**
- `backend/scripts/reprocess_reference_motions_phase4.py` (신규)
- `backend/scripts/rollback_reference_motions_phase4.py` (신규)
- `backend/tests/phase04/test_reprocess_reference_g4.py` (신규)

**핵심 구현:**

`reprocess_reference_motions_phase4.py`:
- `MOTION_IDS = ["ref-sideway-spin", "ref-climb", "ref-invert", "ref-foxtop", "ref-foxtop-split"]` (5개)
- `_validate_payload_schema(payload, motion_id)`: 11개 키 검증 (BLOCKER-2)
- `_reprocess_one(...)`: `synthesis_adapter=None` 기본값 + `is_reference=True` 박제 주석 (D-10, BLOCKER-1). dry-run=True 시 S3/GPU 생략.
- `_write_versioned(fs_client, motion_id, payload)`: `reference/{id}/versions/phase4_v1` canonical path. `referenceMotions` 사용 0 (HIGH-2/HIGH-3).
- `_flip_active_pointer(fs_client, motion_ids, completed)`: `len(completed) == len(motion_ids)` gate + top-level mirror (BLOCKER-2 핵심) + `pre_phase4` 백업.
- `main()`: `--dry-run` / `--no-flip` / `--motions` argparse. 순서: reprocess → schema gate → versioned write → flip.

`rollback_reference_motions_phase4.py`:
- `--to-version pre_phase4` (기본). top-level mirror 복원 (BLOCKER-2 대칭 — activeVersion 만 되돌리면 consumer 가 phase4 값 계속 봄).
- 실행 전 현재 activeVersion 출력 (T-04-W5-05 확인 가능).

`test_reprocess_reference_g4.py` 4개 테스트 (모두 GREEN):
1. `test_g4_guard_no_synthesis_for_reference_reprocess`: `FakeSynthesisAdapter` 주입 → 호출 0 행위 증명 (D-10, BLOCKER-1).
2. `test_dry_run_schema_validation_all_5`: 5개 motionId × 11키 schema gate (BLOCKER-2).
3. `test_versioned_write_path_uses_versions_subpath`: `FakeFirestoreClient` 주입 → write path 정확 일치 + `referenceMotions` 미등장 + flip 전 top-level write 0 (HIGH-2).
4. `test_active_pointer_flip_requires_all_5`: 4개 미만 완료 시 flip 차단 (T-04-W5-03).

**Verification:**
```
pytest backend/tests/phase04/test_reprocess_reference_g4.py -x -q → 4 passed
grep -c "referenceMotions" backend/scripts/reprocess_reference_motions_phase4.py → 0
len(MOTION_IDS) → 5 (reprocess + rollback 양쪽)
```

### Task 2: test_evaluate_4way.py RunPod 통합 테스트 append

**Commit:** `969a2c6`
**Files:**
- `backend/tests/phase04/test_evaluate_4way.py` (수정 — 04-03 기존 내용 보존 + 04-05 append)

**추가 내용:**

`_runpod_available()` 헬퍼: `RUNPOD_ANALYZE_URL` env 감지.

`test_evaluate_4way_harness_smoke_60f` (GREEN, RunPod 불필요):
- `joint_seq_60f` fixture (T=60, conftest.py) 명시 재사용.
- `split_frame_indices=[10,20,30,40,50]` (T=60 정합).
- `PathOutput` 3개 (rtmw_mirror / gemini_view / cylindrical_mesh) + `evaluate_4way` 호출 성공.
- 3개 path key 포함 + NaN-free 단언.

`test_evaluate_4way_reprocess_vs_baseline` (local SKIP/XFAIL — 정상):
- `@pytest.mark.xfail(strict=False)` + `@pytest.mark.skipif(not _runpod_available())` + `@pytest.mark.runpod`.
- RunPod 실행 시: D-22 baseline (-7.60pts/video) 대비 cylindrical_mesh axis_b 비교.
- G4 악화 0 조건 (D-10): `mesh_rate <= baseline_rate` assert.

**Verification:**
```
pytest backend/tests/phase04/test_evaluate_4way.py -x -q -m "not runpod" → 5 passed, 2 skipped, 1 deselected
python3 -c "... assert 'evaluate_4way' in src and 'axis_b' in src and 'RUNPOD_ANALYZE_URL' in src and 'joint_seq_60f' in src" → PASS
pytest backend/tests/phase04/ -q → 41 passed, 3 skipped (regression 0)
```

## Task 3: RunPod 재처리 실행 (Checkpoint Pending — Orchestrator 담당)

**Status:** checkpoint:human-verify — orchestrator 가 RunPod Pod 에서 실행.

Task 3 는 본 executor 가 실행하지 않는다 (SSH/RunPod = orchestrator 전담). 스크립트와 테스트는 Task 1+2 에서 완성됨.

**Orchestrator 실행 지침 (how-to-verify 정합):**

1. Pod 에서 `git pull origin main` (최신 커밋 2개 확인).
2. `python scripts/reprocess_reference_motions_phase4.py --out /workspace/reference-phase4-reprocess.json --target-fps 18.0`
   - 순서: 5개 reprocess → schema gate → `versions/phase4_v1` write → active flip.
3. `export RUNPOD_ANALYZE_URL=http://localhost:8000 && python -m pytest backend/tests/phase04/test_evaluate_4way.py -x -q 2>&1 | tail -20`
4. `scp pod:/workspace/reference-phase4-reprocess.json /tmp/` — JSON 5개 motionId + `pipelineVersion: "phase4_v1"` 확인.
5. belle 시각 검증: mode1 result 화면에서 ref-sideway-spin 재처리 점수 비악화.
6. rollback 경로: `python scripts/rollback_reference_motions_phase4.py --to-version pre_phase4`.

**Wave 5 완료 기준 (HIGH-4):**
- (A) hard gate: Task 1+2 로컬 GREEN ✓ + RunPod 재처리 실행 (Task 3 pending).
- (B) optional: evaluate_4way axis_b RunPod evidence (Wave 3b 가용 시).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical test] test_evaluate_4way_harness_smoke_60f @pytest.mark.runpod 미부여**
- **Found during:** Task 2
- **Issue:** 플랜 스펙은 `@pytest.mark.runpod` 부여를 명시했으나, acceptance_criteria 는 `-m "not runpod"` 실행 시 GREEN 필수. 두 요건이 충돌.
- **Fix:** `@pytest.mark.runpod` 미부여 (로컬 GREEN 우선 — synthetic fixture 기반이므로 RunPod 불필요). plan 의도는 RunPod 환경에서도 동작 확인이었으나 acceptance_criteria 가 최우선.
- **Files modified:** `backend/tests/phase04/test_evaluate_4way.py`

**2. [Rule 1 - Bug] reprocess 스크립트 `referenceMotions` 주석 제거**
- **Found during:** Task 1 acceptance gate 검증
- **Issue:** `grep -c "referenceMotions"` gate = 0 필수인데 주석에 `referenceMotions` substring 포함.
- **Fix:** 주석 문구를 `reference-lib` / `reference/{id}` 로 변경.
- **Files modified:** `backend/scripts/reprocess_reference_motions_phase4.py`

## Known Stubs

- `test_evaluate_4way_reprocess_vs_baseline`: 실 RunPod 재처리 결과 없으므로 synthetic fixture(base_conf 낮은 confidence) 로 대체. RunPod 실행 시 실 PathOutput 으로 교체 예정 (Task 3 orchestrator 담당).

## Threat Flags

task_3_mitigation: T-04-W5-01 (로그 키 마스킹), T-04-W5-02 (G4 guard behavioral gate), T-04-W5-03 (flip gate 5개 강제), T-04-W5-05 (rollback 전 activeVersion 출력) 모두 Task 1+2 코드에 구현됨. RunPod 실행(Task 3) 시 실 검증.

## Self-Check: PASSED

**Created files:**
- `backend/scripts/reprocess_reference_motions_phase4.py` ✓
- `backend/scripts/rollback_reference_motions_phase4.py` ✓
- `backend/tests/phase04/test_reprocess_reference_g4.py` ✓
- `backend/tests/phase04/test_evaluate_4way.py` (modified) ✓

**Commits:**
- `daf6803` ✓ (git log 확인)
- `969a2c6` ✓ (git log 확인)

**pytest gates:**
- `backend/tests/phase04/test_reprocess_reference_g4.py -x -q` → 4 passed ✓
- `backend/tests/phase04/test_evaluate_4way.py -x -q -m "not runpod"` → 5 passed, 2 skipped, 1 deselected ✓
- `backend/tests/phase04/ -q` → 41 passed, 3 skipped ✓
- `grep -c "referenceMotions" backend/scripts/reprocess_reference_motions_phase4.py` → 0 ✓
- `len(MOTION_IDS)` → 5 (reprocess + rollback) ✓

**Task 3 Status:** checkpoint pending — orchestrator RunPod 담당. SUMMARY.md 는 Task 1+2 박제 + Task 3 checkpoint 명시로 작성.

---

## Task 3 — Orchestrator RunPod Closeout (2026-06-14) ✓ COMPLETE

RunPod Pod `d9xxudi1i6xlpz` (RTX PRO 4500 Blackwell sm_120, Network Volume) 에서 orchestrator 실행:

1. **GPU 재처리 5/5** — RTMW(rtmlib/onnxruntime-gpu 1.19.2) sm_120 cuda ~50fps, 150s, NaN 0.
   schema gate 5/5 PASS → `reference-phase4-reprocess.json` (로컬 /tmp + Pod /workspace 보존).
   RTMWPoseEngine 은 torch/mmpose 불필요 (rtmlib 단독) → lean bootstrap. [[rtmw-blackwell-lean-bootstrap]]
2. **Firestore 40k index-entry 한도 BLOCKER 해결** — versioned write 가 joints3d(T*17*3)+angles+keypointReport
   대형 배열 auto-index 로 ref-sideway-spin ~55k > 40k 차단. belle 승인 후 옵션(a) field 면제:
   `gcloud firestore indexes fields update {joints3d,angles,keypointReport} --collection-group={reference,versions}
   --disable-indexes` 6개 (owner sunity3412 login). composite mode3 index 무영향. [[firestore-index-entry-limit]]
3. **versioned write 5/5** → `reference/{id}/versions/phase4_v1` (`--no-flip` 단계, prod 무영향).
4. **belle 시각 검증 PASS** — 현 active 대비 관절각 평균 Δ 0~6° (max 5.9° ref-invert), NaN 0,
   프레임 1.5x↑ (fps 18 더 촘촘). 점수 비악화 확인.
5. **active flip 5/5** — `_flip_active_pointer`: pre_phase4 백업(rollback 소스) → activeVersion=phase4_v1
   → top-level mirror 11필드(joints3d/keypointReport 포함). 검증: 5/5 top-level activeVersion=phase4_v1,
   anglesFrames=298/257/260/426/485, joints3d+keypointReport+pre_phase4 백업 all present.

**Rollback:** `python backend/scripts/rollback_reference_motions_phase4.py --to-version pre_phase4`

**잔여(optional, phase blocker 아님):** Wave 3b @integration `test_evaluate_4way_reprocess_vs_baseline`
axis_b RunPod 증거 = parked (cylindrical mesh path / RunPod 3b accuracy gate). 04-05 hard gate (A) 7항 전부 PASS.

**Wave 5 = COMPLETE. Phase 04 = 6/6 plan 완료.**
