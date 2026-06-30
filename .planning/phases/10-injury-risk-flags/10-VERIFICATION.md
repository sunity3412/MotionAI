---
phase: 10-injury-risk-flags
verified: 2026-06-30T02:15:00Z
status: passed
score: 4/4 success-criteria verified (locally); 2 pod-deferred validation items accepted
overrides_applied: 0
verdict: SAFE-01 achieved locally (all deterministic gates GREEN, full wiring + 3-mirror contract + amber UI verified). Final real-video no-FP eval + D-05 real-elite (T,17,4) regression remain pod-deferred (accepted, documented, properly gated — NOT failures).
pod_deferred:
  - item: "D-05 real-elite (T,17,4) regression fixture"
    artifact: "backend/tests/phase10/fixtures/real_elite_coco17_4ch.npz (absent)"
    gating: "4 tests skipif-gated on REAL_ELITE_FIXTURE_PATH.exists(); schema gate forces (T,17,4)+ch3∈[0,1]; un-fakeable by 2D/J=8 data"
    extractor: "backend/scripts/extract_reference_coco17_4ch.py (staged, present)"
    pinned_ids: [ref-sideway-spin, ref-invert, ref-foxtop-split]
  - item: "Final no-FP eval against real 정은지 video"
    note: "Headline elite-no-FP is proven against SYNTHETIC elite fixtures locally; real-video eval needs RunPod GPU"
---

# Phase 10: 부상 위험 신호 플래그 (injury-risk-flags) — Verification Report

**Phase Goal:** 좌우 비대칭·요추 과신전·레벨 대비 무리한 동작 신호를 위험도 스코어로 플래그하고 결과 화면에 경고로 표시한다 (SAFE-01)
**Verified:** 2026-06-30
**Status:** passed (local) — pod-eval pending
**Re-verification:** No — initial verification

## Verdict

SAFE-01 is **achieved locally**. All four deterministic SafetyFlag types are implemented as real firing rules behind the D-02 (posture AND control-loss) AND-gate, wired end-to-end (`_process` → `result['safetyFlags']` → scoped validator → Firestore → `normalize()` → `result.tsx` → amber `InjuryRiskSection`), the 3-mirror contract is intact, and the headline elite-no-FP gate is GREEN against synthetic elite fixtures. The phase10 suite = **54 passed, 4 skipped (pod-deferred), 0 failed/xfailed/xpassed**; app `tsc --noEmit` clean.

Two items remain pod-deferred and constitute the entire remaining validation surface: (1) the D-05 real-elite `(T,17,4)` regression fixture, and (2) the final no-FP eval against real 정은지 video. Both are accepted, documented (`deferred-items.md`), and properly gated — they are NOT verification failures.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria 1–4)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 좌우 비대칭 임계값 초과 시 위험 신호 플래그가 출력에 추가된다 | VERIFIED (local) | `_asymmetry_flag` `safety_flags.py:411-484` — DTW-aligned reference-anchored excess, explicit L/R pairs + MAX agg, KISMAM `score_from_deviation` threshold. 7 tests incl. positive fire + MAX-pair audit + timing-shift-cancel (`test_safety_flags_asymmetry.py`) |
| 2 | 요추 과신전 패턴 감지 시 "허리 부담 가능성" 경고 | VERIFIED (local) | `_trunk_hyperextension_flag` `safety_flags.py:345-407` (reference-anchored DTW + hip-local control-loss); UI copy `허리 부담 가능성` `InjuryRiskSection.tsx:35`; firing-rule tests GREEN |
| 3 | `poleExperienceLevel` × 동작 난이도 매핑으로 "레벨 대비 무리" 경고 동작 | VERIFIED (local) | `_level_mismatch_flag` `safety_flags.py:488-528` — Mode-1-only, enum-guarded `_LEVEL_LADDER`, rank-gap × instability severity, spoof/None fail-safe. Plumbed in `_process` from `bodyProfile.experience` + `ref.level` (`app.py:3509-3514`). 7 tests incl. spoof/None/mode3/severity-scaling (`test_safety_flags_level.py`) |
| 4 | 결과 화면에 위험 경고가 시각적으로 구분 + "전문가 확인 권유" 카피 | VERIFIED | `InjuryRiskSection.tsx` amber `warnAmberBg #FFF6E5`/`warnAmber #E6A300`, NO brand red; disclaimer + `정확한 판단은 강사 또는 전문가와 함께 확인` referral; omit-when-empty; rendered at `result.tsx:878` `<InjuryRiskSection flags={result.safetyFlags} />`. No "부상 확정" string present |

**Score:** 4/4 truths verified (local). The 4th (UI) is fully code-verified; visual rendering on device is the usual human-eyeball item but the structural contract (color tokens, copy, no-brand-red, omit-when-empty) is verified in source.

### Core Defense: D-02 LOCAL+TEMPORAL AND-Gate (정은지 elite-no-FP)

| Check | Status | Evidence |
|-------|--------|----------|
| Posture alone never fires | VERIFIED | `_maybe_flag` requires `posture_met AND control_lost` `safety_flags.py:334-341`; `test_posture_without_control_loss_no_flag`, `test_elite_posture_alone_no_flag` GREEN |
| Temporal co-location required (same phase) | VERIFIED | `_control_loss_for_joint(..., phase=)` `safety_flags.py:282-302`; `test_and_gate_requires_temporal_colocation`, `test_and_gate_wrong_phase_no_flag` GREEN |
| Region-local required (same body part) | VERIFIED | `joint_key in metric.unstable_body_parts` gate; `test_d05_wrong_joint_no_flag` GREEN |
| Intentional extension cancels (DTW path-aligned, not raw same-index) | VERIFIED | `_dtw_aligned_joint_medians` `safety_flags.py:222-272` mirrors pipeline `_angles_to_dtw_median_dicts`; `test_trunk_timing_shifted_same_extension_no_flag`, `test_timing_shifted_same_asymmetry_no_flag` GREEN |
| Elite-no-FP (synthetic) | VERIFIED (local) | `test_elite_posture_alone_no_flag` GREEN; D-05 `test_elite_extension_no_joint_flag` GREEN |
| Elite-no-FP (REAL video) | POD-DEFERRED | Real-video eval needs RunPod GPU — accepted deferral |

### Objectivity (no human-score curve-fit)

| Check | Status | Evidence |
|-------|--------|----------|
| Thresholds tagged with provenance | VERIFIED | All constants carry `[CITED]` (IPSF/clinical: knee>5° genu recurvatum, elbow>10° Beighton, KISMAM tol) or `[ASSUMED conservative gate]` tags `safety_flags.py:114-181` |
| Reference-anchored, not 13-video fit | VERIFIED | D-03/D-04 use `_dtw_aligned_joint_medians` reference excess; D-07 / `[[calibration-source-hard-gate]]` cited in docstrings; no sweep-derived cutoffs |
| Deterministic (LLM-independent) | VERIFIED | Pure numpy module, no Cerebras/Gemini import; `injuryRisk` LLM prose untouched (D-01 boundary preserved) |
| No human-score labels | VERIFIED | Flags carry numeric/categorical severity from measurement, no human ground-truth labels |

### Contract 3-Mirror Integrity

| Mirror | Status | Evidence |
|--------|--------|----------|
| `app/src/types/analysis.ts` | VERIFIED | `SafetyFlagType` (4 values) + `SafetyFlag` interface (7 fields, reuses SeverityLevel/MetricConfidence) `analysis.ts:1042-1056`; `AnalysisResult.safetyFlags?` `:522` |
| `backend/.../models.py` | VERIFIED | `SAFETY_FLAG_TYPES` + `SAFETY_FLAG_MODE_SCOPES` tuples + one-directional `SafetyFlag` re-export `models.py:486-496` (no import cycle) |
| `docs/contract.md` | VERIFIED | §9.13 table (7 fields scalar-only) + `AnalysisResult.safetyFlags` + changelog `contract.md:1394-1416` |
| Field consistency across mirrors | VERIFIED | flag_type values, mode_scope (`both`/`mode1_only`), severity domain all consistent |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `safety_flags.py` | 4-flag firing rules + D-02 gate | VERIFIED | 810 lines, all 4 rules + `_maybe_flag` + `_dtw_aligned_joint_medians` + `_hyperextension_candidate` (cross-product + 8 fail-conservative gates) — substantive, no stubs |
| `pipeline/app.py` injection | `compute_safety_flags` call + persist | VERIFIED | `app.py:3505-3529` — mode-aware reference plumbing, `result['safetyFlags']` set, graceful try/except |
| `firestore_admin._validate_safety_flags` | scalar-only validator | VERIFIED | `firestore_admin.py:288-305` + wired call `:909-913` (nested-array ban enforced) |
| `InjuryRiskSection.tsx` | amber UI, 4-type copy map | VERIFIED | 133 lines, all 4 flagType copy entries, omit-when-empty, accessibilityRole=alert |
| `extract_reference_coco17_4ch.py` | pod (T,17,4) extractor | VERIFIED (staged) | present (5545 bytes) — runs on pod for deferred fixture |

### Data-Flow Trace (Level 4)

| Stage | Source | Real Data? | Status |
|-------|--------|-----------|--------|
| `result.safetyFlags` (UI prop) | `userAnalyses.normalize()` `:179-182` passes through `result.safetyFlags` | Yes — from Firestore doc | FLOWING |
| Firestore write | `_process` `result['safetyFlags']` = camelCase dicts of computed flags `app.py:3527` | Yes — `compute_safety_flags` output | FLOWING |
| Flag computation | `compute_safety_flags` consumes real `angles`/`keypoints_4ch`/`force_signals_report` | Yes — pipeline analysis inputs | FLOWING |

No hollow props; UI renders genuine pipeline output.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full phase10 suite | `python3 -m pytest tests/phase10 -q` | 54 passed, 4 skipped | PASS |
| Elite-no-FP (synthetic) | `pytest ...::test_elite_posture_alone_no_flag` (in suite) | GREEN | PASS |
| App typecheck | `npm run typecheck` (app) | clean | PASS |
| Pod-deferred genuinely skipped | `ls tests/phase10/fixtures/` | No such directory → 4 tests SKIP | PASS (not faked) |

### Pod-Deferred Validation Surface (accepted, documented — NOT failures)

| # | Item | Gating Evidence | Pod Action Required |
|---|------|-----------------|---------------------|
| 1 | D-05 real-elite `(T,17,4)` no-FP regression (4 tests) | `skipif(not REAL_ELITE_FIXTURE_PATH.exists())` `test_..._hyperextension.py:259-262`; fixtures dir absent; schema gate `:296-311` forces (T,17,4)+ch3∈[0,1]+NaN-coord⇒ch3==1.0 (2D/J=8 data cannot satisfy) | Run `extract_reference_coco17_4ch.py --motions ref-sideway-spin ref-invert ref-foxtop-split` → npz lands → 4 tests auto-flip GREEN |
| 2 | Final no-FP eval against real 정은지 video | Headline gate currently proven on synthetic elite fixtures only | Run pipeline on real elite clips, confirm ZERO flags |

**Hygiene confirmed:** No synthetic `.npz` is committed masquerading as real-video coverage (fixtures dir does not exist). The schema gate is un-fakeable. Pinned source IDs are KNOWN-ANSWER regression targets, not fit targets (`[[calibration-source-hard-gate]]`).

### Requirements Coverage

| Requirement | Source | Status | Evidence |
|-------------|--------|--------|----------|
| SAFE-01 | Phase 10 (all 4 plans) | SATISFIED (local) | 4-flag set complete behind D-02 gate, deterministic, elite-no-FP (synthetic) preserved, UI with expert-referral + no "부상 확정"; real-video eval pod-deferred |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `analysis.ts:1032,1034`, `models.py:483-485` | comment `§N` placeholder | doc nit | ℹ️ Info | TS/Python mirror comments reference `§N` instead of the resolved `§9.13`; the actual `docs/contract.md` section IS `§9.13` and all field values match. Cosmetic only — does not affect contract integrity. |

No debt markers (TBD/FIXME/XXX) in phase10 files. No stub returns in firing-rule paths. The `return []`/`return None` paths in `safety_flags.py` are intentional graceful no-ops (documented), not unimplemented stubs.

### Documented Limitations (surfaced, not silent)

- **D-04 absolute lumbar cutoff DEFERRED** — implemented reference-anchored ONLY (no absolute trunk-femur cutoff); needs mid-spine keypoint. Documented in module + 10-02-SUMMARY. SC2 satisfied via reference-anchored path.
- **First Mode-3 video** (no baseline) → `reference_angles=None` → trunk/asymmetry no-op gracefully; belle's Mode-3 "내 자세가 이러면 위험" promise carried by absolute D-05 (reference-free). Documented `app.py:3501-3504`.
- **Temporal co-location is phase-level** (StabilityMetric substrate is phase-scoped), not per-frame — documented v1 limitation `safety_flags.py:276-281`.

### Human / Pod Verification Required

1. **Real-video elite-no-FP eval** — Run pipeline on real 정은지 clips; expect ZERO flags. Why pod: needs RunPod GPU (RTMW pose). 
2. **D-05 real-elite regression fixture** — Run the staged extractor on pod; 4 skipif tests auto-activate. Why pod: only valid (T,17,4) source is `to_coco17_array(pose_frames)` requiring GPU.
3. **On-device UI render** — Confirm amber section renders visually distinct (no brand red) with expert-referral copy. Why human: visual appearance.

### Gaps Summary

No blocking gaps. SAFE-01's four success criteria are each implemented as substantive firing rules, gated by the D-02 posture-AND-control-loss rule, wired through the full pipeline → Firestore → UI path, mirrored across the 3-way contract, and proven by 54 passing deterministic tests with the elite-no-FP headline GREEN on synthetic fixtures. The only outstanding work is the two explicitly-authorized, properly-gated pod-deferred validations (real-elite (T,17,4) regression + real-video no-FP eval), which per orchestrator directive are accepted deferrals and do not block phase completion.

---

_Verified: 2026-06-30_
_Verifier: Claude (gsd-verifier)_
