# Phase 10 — Deferred / Out-of-Scope Items

## RESOLVED (2026-06-30) — final no-FP eval on real 정은지 video

Both pod-deferred items are now CLOSED (pod `cuwgz2h059d1rl`, 2026-06-30):
1. **real-elite (T,17,4) fixture** — extracted, committed; 4 D-05 tests auto-activated
   (phase10 = 58 passed, 0 skipped). See the (formerly POD-DEFERRED) section below.
2. **final no-FP eval** — ran `scripts/eval_phase10_nofp.py` on the 7 정은지 success(mode1)
   videos through full `_process` (GPU RTMW + Gemini recognizer). Result:
   **FP videos: 0/7 (target 0), ERRORs: 0, clean: 7** — every flag type (D-02 AND-gate +
   D-03/04/05/06) yields ZERO SafetyFlags on correctly-performed elite moves, incl. the
   historically FP-prone kip-up. Log: `backend/evals/phase10/nofp_eval_2026-06-30.log`.

SAFE-01 is now fully validated on real video, not just synthetic fixtures. Phase 10 done.

## Pre-existing test failures (NOT introduced by Phase 10, out of scope)

Discovered during 10-01 execution while running the full `backend/tests` regression
suite. These fail identically against the pre-Phase-10 commit (`102fbfe`, original
`models.py` without the additive `SafetyFlag` re-export) — proven by reverting
`models.py` and re-running. They are unrelated to the SafetyFlag scaffold (Gemini /
vision-veto env-dependent pipeline-integration tests + heavy-dependency R&D spike
collection errors). Per the executor SCOPE BOUNDARY, they are logged here and NOT
fixed in this plan.

### Pipeline-integration FAILED (10)
- `tests/phase06/test_phase06_integration_smoke.py::test_full_pipeline_mode1_ref_source_pose_missing_smoke`
- `tests/phase06/test_pipeline_body_comparison.py::test_process_mode1_with_full_ref_returns_mode1_report`
- `tests/phase06/test_pipeline_body_comparison.py::test_process_mode1_missing_ref_body_profile_emits_canary_warning`
- `tests/phase06/test_pipeline_body_comparison.py::test_process_mode1_missing_ref_source_pose_emits_canary_warning`
- `tests/phase06/test_pipeline_body_comparison.py::test_process_mode1_fetches_both_profile_and_source_pose`
- `tests/phase06/test_pipeline_firestore_integration.py::test_process_calls_complete_analysis_with_body_comparison_report`
- `tests/phase08/test_gemini_model_env_driven.py::test_gemini_moment_extractor_default_is_non_eol`
- (plus 3 more pipeline cases in the same phase06/phase08 group)

Root cause sample: `NotPoleMotionError` raised inside `_process` under the mocked
mode1 flow — a domain/env path (Gemini recognizer / vision-veto), not a contract or
import issue.

### Collection ERRORS — R&D spike/smoke modules (11, heavy optional deps)
`tests/test_compare_engines_smoke.py`, `tests/test_debug_gap_root_cause_smoke.py`,
`tests/test_gemini_motion_classify_spike.py`, `tests/test_mapping_audit.py`,
`tests/test_pole_detector.py`, `tests/test_spike_gemini_moment_smoke.py`,
`tests/test_spike_measurement_trace.py`, `tests/test_spike_measurement_trace_smoke.py`,
`tests/test_spike_mediapipe_to_h36m17.py`, `tests/test_spike_rtmpose_to_h36m17.py`,
`tests/test_sweep_rtmpose_smoke.py` — ImportError on optional ML deps
(mediapipe / rtmpose / gemini), unchanged by Phase 10.

**Phase 10 scope (phase06/07/08/08_1/09/10 substrate suites) regression = 0** beyond
these pre-existing items.

---

## RESOLVED (2026-06-30) — was POD-DEFERRED: D-05 real-elite (T,17,4) regression fixture (10-03)

**RESOLVED on pod `cuwgz2h059d1rl` (2026-06-30):** ran the extractor below on the 3 pinned
정은지 clips → `backend/tests/phase10/fixtures/real_elite_coco17_4ch.npz` (278K;
ref-sideway-spin (298,17,4) / ref-invert (260,17,4) / ref-foxtop-split (485,17,4); ch3
uncertainty_proxy ∈ [0.03, 0.92]). The 4 skipif tests AUTO-ACTIVATED and pass:
`cd backend && python3 -m pytest tests/phase10 -q` = **58 passed, 0 skipped** — real elite
keypoints yield ZERO joint_hyperextension flags (D-05 no-FP confirmed on real video, not
just synthetic). Note: onnxruntime fell back to CPU EP (cuDNN9 missing on the fresh
container) — RTMW is a deterministic ONNX graph so CPU output is valid (NaN-divergence is
NLF-only); install cuDNN9 before the heavier final no-FP eval to restore GPU speed.

(original deferral context below, kept for provenance)

The D-05 joint-hyperextension detector (10-03) is fully implemented and GREEN against
all synthetic + helper-contract + per-branch-gate tests. The ONLY part deferred to a
later RunPod GPU run is the **real-elite 3D keypoint regression** — there is no checked-in
`(T,17,4)` 3D source (the only valid source is `to_coco17_array(pose_frames)` which
requires RTMW pose estimation on GPU; `reference-angles.json` is angle-only J=8 and
`referenceKeypointReport` is a 2D 8-keypoint overlay — both FORBIDDEN as 3D sources).

**Authorized deferral** (orchestrator directive 2026-06-30): build + unit-test GREEN
locally first; the pod opens later for the real-elite fixture + final no-FP eval.

### What is deferred
- 4 tests in `backend/tests/phase10/test_safety_flags_hyperextension.py` are
  `@pytest.mark.skipif(not REAL_ELITE_FIXTURE_PATH.exists(), ...)` gated and currently
  SKIPPED (show as `s` in pytest):
  - `test_real_elite_clips_no_hyperextension`
  - `test_real_elite_mirrored_no_flag`
  - `test_real_elite_spin_no_flag`
  - `test_d05_real_elite_fixture_schema`
- They AUTO-ACTIVATE the moment the fixture artifact lands at
  `backend/tests/phase10/fixtures/real_elite_coco17_4ch.npz`.

### Pinned source motion IDs (KNOWN-ANSWER regression, NOT a fit target — [[calibration-source-hard-gate]])
- `ref-sideway-spin` — spin-around-pole (rotational orientation)
- `ref-invert` — inverted / mirrored orientation
- `ref-foxtop-split` — extreme split (both left and right limbs)

### Exact extractor command (run on the pod)
```bash
cd backend && source pod.env && export PYTHONPATH=$PWD:$PWD/shared/python
python scripts/extract_reference_coco17_4ch.py \
    --motions ref-sideway-spin ref-invert ref-foxtop-split \
    --out tests/phase10/fixtures/real_elite_coco17_4ch.npz
```
The extractor `backend/scripts/extract_reference_coco17_4ch.py` runs
`frames -> RTMWPoseEngine.estimate -> pose_frames -> to_coco17_array(.npz)` and is the
single valid `(T,17,4)` extraction path. After the npz is committed, run
`cd backend && python3 -m pytest tests/phase10 -q` — the 4 tests flip from SKIPPED to
GREEN (the schema gate forbids 2D / 8-keypoint / wrong-order data from satisfying them).
