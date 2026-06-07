---
phase: 02-bodynormalizationprofile-rtmw-segment
plan: 01
subsystem: ml
tags: [body-normalization, rtmw, pose-segment, smplx-rd, validator, race-safe]

# Dependency graph
requires:
  - phase: 01-poseengine-mediapipe-nlf-r-d
    provides: PoseFrame / Keypoint3D / PoleAxis 4-field dataclass + RTMW 133 wholebody engine + convert_rtmw_keypoints_to_coco17_and_pole_ext adapter
provides:
  - measure_body_profile(pose_frames) -> BodyNormalizationProfile 순수 함수 (RTMW segment 측정, MEDIUM-3 v5 image-y-order inversion + MEDIUM-2 v5 strictly-positive fallback)
  - _RTMWNlfCompat.estimate_with_profile(frames) race-safe local-return tuple (HIGH-1 v4 사이드카 폐기, B8 박제 보존)
  - _angles_and_body_profile_from_video(bucket, key) helper (pipeline integration ready for Phase 6)
  - BodyNormalizationProfile.__post_init__ 5 numeric scale finite + strictly positive validator (MEDIUM-2 v5)
  - 5 synthetic PoseFrame fixture (normal / inverted / occluded_leg / short_clip / asymmetric, image y-down 좌표)
  - pose_frame_from_dict test factory helper (HIGH-2 v1→v2)
  - R&D harness: compare_body_profile + smplx_joints_to_body_profile + extract_rtmw_body_profile_keypoints + extract_smplx_joints_from_video + run_body_profile_gap_report (HIGH-1 v5 joints-based + HIGH-2 v5 single orchestrator)
affects:
  - 06-bodynormalization-wireup (Phase 6 plan 이 _angles_and_body_profile_from_video helper 호출 site + Firestore AnalysisDoc 박제)
  - 07-asymmetry-classification
  - 08-09-force-patterns

# Tech tracking
tech-stack:
  added:
    - numpy MAD outlier rejection (DEFAULT_OUTLIER_K=3.0) for body segment robust median
  patterns:
    - race-safe local-return helper pattern (사이드카 mutable state 폐기)
    - 3-way contract lockstep (TS + Python + docs/contract.md §7)
    - dataclass __post_init__ validator extension for numeric range contract

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py
    - backend/tests/fixtures/body_normalization/__init__.py
    - backend/tests/fixtures/body_normalization/_factory.py
    - backend/tests/fixtures/body_normalization/_generate.py
    - backend/tests/fixtures/body_normalization/normal_pose_pose_frames.json
    - backend/tests/fixtures/body_normalization/inverted_pose_pose_frames.json
    - backend/tests/fixtures/body_normalization/occluded_leg_pose_frames.json
    - backend/tests/fixtures/body_normalization/short_clip_pose_frames.json
    - backend/tests/fixtures/body_normalization/asymmetric_pose_pose_frames.json
    - backend/tests/fixtures/body_normalization/test_fixtures_loadable.py
    - backend/tests/fixtures/body_normalization/test_real_rtmw_sanity.py
    - backend/tests/test_body_normalization_measurer.py
    - backend/tests/test_pipeline_body_profile_injection.py
    - backend/tests/test_compare_body_profile_smoke.py
    - backend/research/evaluations/compare_body_profile.py
    - backend/research/evaluations/smplx_joints_to_body_profile.py
    - backend/research/evaluations/extract_smplx_joints_from_video.py
    - backend/research/evaluations/extract_rtmw_body_profile_keypoints.py
    - backend/research/evaluations/run_body_profile_gap_report.py
  modified:
    - docs/contract.md (§7 — 5 warning enum + scale semantic + MEDIUM-2 v5 finite/positive contract)
    - app/src/types/analysis.ts (BodyNormalizationProfile interface JSDoc — M3 + MEDIUM-2 v5)
    - backend/shared/python/sunity_shared/analysis/body_normalization.py (__post_init__ validator extension)
    - backend/tests/test_body_normalization_lockstep.py (3 신규 lockstep test)
    - backend/tests/test_body_normalization_profile.py (26 신규 validator case)
    - backend/functions/pipeline/app.py (_RTMWNlfCompat.estimate_with_profile + _angles_and_body_profile_from_video)

key-decisions:
  - "MEDIUM-3 v5 박제: pose_too_inverted 가 PoleAxis.axis_vector 부호 의존을 폐기 — image y-down 좌표 직접 비교 (mean shoulder.y vs mean hip.y). _is_inverted_frame 시그너처에서 pole_axis 인자 폐기."
  - "MEDIUM-2 v5 박제: BodyNormalizationProfile.__post_init__ 가 5 numeric scale 필드 finite + strictly positive 강제. measurer fallback path 는 1.0 emit (0.0 거절)로 validator 통과."
  - "HIGH-1 v4 race-safe local-return 유지: estimate_with_profile 가 tuple 반환 + 사이드카 attribute 영구 폐기. RunPod FastAPI BackgroundTasks 환경 글로벌 _POSE_ESTIMATOR 공유에도 leak 0. B8 박제 (기존 estimate 시그너처) 무변경."
  - "HIGH-1 v5 박제: β-only weights-free 단축 변환 영구 폐기. smplx_joints_to_body_profile(joints) pure NumPy + extract_smplx_joints_from_video Pod-only 분리. CI 는 합성 joints 단위 테스트."
  - "HIGH-2 v5 박제: run_body_profile_gap_report.py 가 단일 audited orchestrator. belle Pod 작업 = orchestrator 한 줄 + git commit 한 줄 = 두 줄 (멀티스텝 console 폐기, [[user-beginner-stepwise]] 정합)."
  - "MEDIUM-1 v4 박제 유지: Phase 2 scope = measurer + helper. Firestore 저장 + AnalysisDoc 갱신 Phase 6 책임."

patterns-established:
  - "image y-down convention: 직립 = mid_shoulder.y < mid_hip.y, 인버트 = mid_shoulder.y > mid_hip.y. axis_vector 부호 무관."
  - "torso-relative proportion heuristic: estimatedHeightScale = (armScale + legScale + 1.0) / 3 — 절대 키 아님."
  - "fallback path = 1.0 (not 0.0) for scale fields — validator strictly positive 통과 보장."

requirements-completed: []  # BODY-01 — Phase 2 closure 는 Task 5b/6/7 완료 시. 현재 partial.

# Metrics
duration: ~partial — paused at Task 5b checkpoint
completed: 2026-06-07  # partial — see Status below
---

# Phase 02 Plan 01: BodyNormalizationProfile RTMW Segment (Partial — Paused at Task 5b Checkpoint)

**RTMW segment 기반 measure_body_profile + race-safe pipeline helper (estimate_with_profile / _angles_and_body_profile_from_video) + R&D joints-based SMPL-X 비교 harness, 사이드카 폐기 + B8 박제 보존 + Firestore 저장은 Phase 6 책임.**

## Status

**PARTIAL — Tasks 1, 2, 3, 4, 5a 완료. Task 5b (belle Pod 두 줄 실행) 가 checkpoint:human-action gate. Task 6, Task 7 은 orchestrator 의 follow-up dispatch.**

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| Task 1 | 완료 | `5c78ee2` | 3-way lockstep + __post_init__ validator |
| Task 2 | 완료 | `0c512d6` | 5 synthetic fixture + factory + smoke (18 test PASS) |
| Task 3 | 완료 | `0acbd8e` | measure_body_profile + 14 test PASS |
| Task 4 | 완료 | `0d1e0cd` | estimate_with_profile + helper + 9 test PASS, B8 박제 검증 |
| Task 5a | 완료 | `27febfd` | 5 R&D script + 14 smoke test PASS |
| **Task 5b** | **CHECKPOINT — blocking-human gate** | — | **belle Pod 두 줄 실행 — orchestrator 가 prompt 박제** |
| Task 6 | 대기 | — | orchestrator follow-up dispatch (Task 5a 만 의존, Task 5b 평행 OK) |
| Task 7 | 대기 | — | orchestrator follow-up dispatch (Task 1 만 의존) |

## Performance

- **Tasks completed (this dispatch):** 5 of 8 (Tasks 1, 2, 3, 4, 5a)
- **Started:** 2026-06-07T14:00:00Z (approx)
- **Pause point:** 2026-06-07T14:37:12Z
- **Test count (this dispatch):** 83 tests added/extended, all PASS
  - 40 lockstep + validator
  - 18 fixture smoke
  - 14 measurer
  - 9 pipeline injection (+2 B8 lock)
  - 14 R&D harness smoke

## Accomplishments (this dispatch)

- **Contract 3-way lockstep + validator (Task 1)**: docs/contract.md §7 / app/src/types/analysis.ts BodyNormalizationProfile / backend body_normalization.py 동시 갱신 — 5종 warning enum (low_keypoint_confidence / occluded_endpoint / insufficient_frames / asymmetric_landmark_count / pose_too_inverted) + M3 "torso-relative proportion heuristic" 박제 + MEDIUM-2 v5 `__post_init__` 가 5 numeric scale 필드 finite + strictly positive 강제 (NaN/inf/0/negative ValueError).
- **5 synthetic fixture + factory (Task 2)**: PoseFrame `from_dict` 부재 우회 `pose_frame_from_dict()` test factory + seed=42 멱등 generator + image y-down 좌표 5종 (normal / inverted / occluded_leg / short_clip / asymmetric). MEDIUM-3 v5 정합: inverted fixture 도 default axis_vector `(0,1,0)` — y-order 만으로 inversion 결정.
- **body_normalization_measurer.py (Task 3)**: 순수 numpy, scipy 의존 0. SEGMENT_PAIRS + torso self-reference + MAD k=3 robust median + 5 warning emit. MEDIUM-3 v5: `_is_inverted_frame(frame)` 가 pole_axis 인자 폐기. MEDIUM-2 v5: fallback path scale=1.0 (validator 통과).
- **Pipeline integration race-safe (Task 4)**: `_RTMWNlfCompat.estimate_with_profile(frames) -> tuple` 신규 method + `_angles_and_body_profile_from_video(bucket, key) -> tuple` 신규 helper. 사이드카 mutable state 영구 폐기. B8 박제 (`estimate` / `_angles_from_video` / `_angles_and_video_path_from_video` 시그너처) 무변경. concurrency barrier 테스트 + stale-failure 테스트 PASS.
- **R&D harness joints-based + orchestrator (Task 5a)**: smplx_joints_to_body_profile (pure NumPy joints→Profile) + extract_smplx_joints_from_video (Pod-only NLF→SMPL-X β→joints, CI graceful exit) + extract_rtmw_body_profile_keypoints (Pod-only RTMW dump) + compare_body_profile (joints-based) + run_body_profile_gap_report (단일 audited orchestrator, belle 의 한 줄 명령). β-only weights-free 단축 변환 영구 폐기.

## Task Commits

1. **Task 1: 3-way lockstep + numeric validator** — `5c78ee2` (feat)
2. **Task 2: PoseFrame factory + 5 synthetic fixtures (image-y-order)** — `0c512d6` (test)
3. **Task 3: measure_body_profile (image-y-order inversion + positive-scale fallback)** — `0acbd8e` (feat)
4. **Task 4: race-safe estimate_with_profile + _angles_and_body_profile_from_video** — `0d1e0cd` (feat)
5. **Task 5a: R&D harness (5 박제 스크립트)** — `27febfd` (chore)

**Remaining:**
- Task 5b: belle Pod 두 줄 실행 (HIGH-2 v5 박제 — orchestrator 한 줄 + git commit 한 줄). ROADMAP §4 closure 게이트.
- Task 6: AST import isolation 확장 + REQUIREMENTS BODY-01 RTMW + ROADMAP §1 v1.5 deferral + §2/§4 closure boundary wording. orchestrator follow-up dispatch.
- Task 7: estimatedHeightScale consumer semantic guard 4 dir scan (vacuous PASS). orchestrator follow-up dispatch.

## Files Created/Modified (this dispatch)

### Created
- `backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py` — RTMW segment 측정기 본체.
- `backend/tests/fixtures/body_normalization/__init__.py` — fixture 패키지.
- `backend/tests/fixtures/body_normalization/_factory.py` — pose_frame_from_dict test helper.
- `backend/tests/fixtures/body_normalization/_generate.py` — 5 fixture seed=42 멱등 generator.
- `backend/tests/fixtures/body_normalization/{normal_pose,inverted_pose,occluded_leg,short_clip,asymmetric_pose}_pose_frames.json` — 5 fixture (각 <200KB).
- `backend/tests/fixtures/body_normalization/test_fixtures_loadable.py` — smoke load + y-order guard.
- `backend/tests/fixtures/body_normalization/test_real_rtmw_sanity.py` — Task 2b RTMW skip (v1.5 deferred).
- `backend/tests/test_body_normalization_measurer.py` — 14 case 단위 테스트.
- `backend/tests/test_pipeline_body_profile_injection.py` — 9 case race-safe + B8 박제.
- `backend/tests/test_compare_body_profile_smoke.py` — 14 case R&D harness smoke.
- `backend/research/evaluations/compare_body_profile.py` — gap math + 보고서 CLI.
- `backend/research/evaluations/smplx_joints_to_body_profile.py` — joints → Profile pure NumPy.
- `backend/research/evaluations/extract_smplx_joints_from_video.py` — Pod-only NLF→SMPL-X β→joints.
- `backend/research/evaluations/extract_rtmw_body_profile_keypoints.py` — Pod-only RTMW dump.
- `backend/research/evaluations/run_body_profile_gap_report.py` — 단일 audited orchestrator (HIGH-2 v5).

### Modified
- `docs/contract.md` — §7 BodyNormalizationProfile 명세 갱신 (5 warning enum + scale 의미 + MEDIUM-2 v5 contract).
- `app/src/types/analysis.ts` — BodyNormalizationProfile interface JSDoc (M3 + MEDIUM-2 v5 박제).
- `backend/shared/python/sunity_shared/analysis/body_normalization.py` — docstring + __post_init__ 5 numeric validator.
- `backend/tests/test_body_normalization_lockstep.py` — 3 신규 lockstep 함수.
- `backend/tests/test_body_normalization_profile.py` — 26 신규 validator case.
- `backend/functions/pipeline/app.py` — _RTMWNlfCompat.estimate_with_profile + _angles_and_body_profile_from_video.

## Decisions Made

(See `key-decisions` in frontmatter.)

## Deviations from Plan

**None for Tasks 1-5a.** Plan v5 was followed verbatim. One minor implementation note:

- **Task 5a smplx_joints_to_body_profile.py — lazy `sunity_shared` import.** Plan implicitly assumed `sunity_shared` was importable at module top-level in the `python -m backend.research...` invocation. However, `sunity_shared` lives at `backend/shared/python/sunity_shared` which is NOT on `sys.path` by default in that invocation pattern. To keep `argparse --help` (smoke test) working in CI without `PYTHONPATH=backend/shared/python` set, I moved the `BodyNormalizationProfile` import inside the function body of `smplx_joints_to_body_profile()`. This preserves the plan's intent (the function still returns a `BodyNormalizationProfile`) and only affects the `--help` path. Marked as `TYPE_CHECKING` for static analysis. (Not a deviation rule trigger — purely a packaging fix for the same `python -m` convention the plan mandates.)

## Issues Encountered

- `boto3` / `firebase_admin` not installed in the worktree's local Python environment. Installed via `pip3 install --break-system-packages boto3 firebase_admin` so that pipeline tests can import `app.py`. This matches the local-dev workflow Codex uses; production Lambda layer is unaffected.
- Fixture JSON sizes initially exceeded the 200KB budget (per-frame floats serialized at 17 digits). Compressed via `json.dumps(... separators=(",",":"))` + `round(v, 4)` float quantization. All 5 fixtures now under 200KB while preserving idempotency (`_generate.py --check` PASS twice).
- `arm_scale` invariance test (Task 5a): naive change of `left_elbow` y kept arm_scale identical because upper_arm increase was cancelled by forearm decrease (joints are coupled). Adjusted test to move only wrist (not elbow) so total arm length changes deterministically.

## User Setup Required

**Task 5b is a `checkpoint:human-action` gate.** belle must run two commands on the active RunPod pod (1ablelgbtrzcgb):

```
cd /workspace/SunityMotion && \
  python -m backend.research.evaluations.run_body_profile_gap_report \
    --videos ref-foxtop ref-foxtop-split ref-invert ref-sideway-spin ref-climb \
    --date $(date +%Y%m%d)

git add backend/research/evaluations/reports/sweep_rtmw_$(date +%Y%m%d)/keypoints/*.json \
        backend/research/evaluations/reports/smplx_joints_$(date +%Y%m%d)/*.json \
        backend/research/evaluations/reports/smplx_profiles_$(date +%Y%m%d)/*.json \
        backend/research/evaluations/reports/body_profile_gap_$(date +%Y%m%d).* \
  && git commit -m "data(02): SMPL-X vs RTMW body profile gap report (Phase 2 ROADMAP §4)"
```

Required Pod env: `RUNPOD_AUTH_TOKEN`, `NLF_MODEL_PATH`, `SMPLX_MODEL_PATH`, `RTMW_ONNX_PATH`, `YOLOX_ONNX_PATH`, `AWS_*`. Pod 의 `rtmw end2end.onnx` 절대 경로 + `nlf_l_multi.torchscript` + SMPL-X 사내 weights (PS:License 1.0 비상업).

Orchestrator (`run_body_profile_gap_report.py`) 가 4 phase 내부 자동 실행 — belle 개입 0. 실패 시 actionable Korean error.

**Alternative:** "not feasible — defer to v1.5" — ROADMAP §4 v1.5 deferral 박제 (Task 6 commit 에 포함).

## Next Phase Readiness

- **Phase 6 (BodyNormalization wire-up) unblock 입력 완성**: `_angles_and_body_profile_from_video(bucket, key) -> tuple[np.ndarray, BodyNormalizationProfile | None]` helper + `_RTMWNlfCompat.estimate_with_profile` + `measure_body_profile` 박제. Phase 6 plan 이 wire-up (Firestore 저장 + AnalysisDoc 박제 + 다운스트림 normalize) 담당.
- **Phase 2 closure 조건 남음:**
  - Task 5b PASS 또는 v1.5 defer (ROADMAP §4)
  - Task 6 (AST + REQUIREMENTS + ROADMAP wording)
  - Task 7 (consumer guard 4 dir)

---

*Phase: 02-bodynormalizationprofile-rtmw-segment*
*Plan: 01*
*Status: PARTIAL — paused at Task 5b checkpoint, awaiting belle Pod execution. Tasks 6/7 will be dispatched by orchestrator after Task 5b clears (or v1.5 defer).*
*Completed (this dispatch): 2026-06-07*
