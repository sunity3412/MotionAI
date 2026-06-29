# Phase 10: 부상 위험 신호 플래그 (injury-risk-flags) - Research

**Researched:** 2026-06-29
**Domain:** Deterministic biomechanical safety-flag layer over an existing numpy pose-analysis pipeline (Python Lambda/RunPod) + React Native warning UI
**Confidence:** HIGH (substrate verified by source read) / MEDIUM (external anatomical thresholds — cited but require user confirmation)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Separate **deterministic SafetyFlag layer** — independent data structure + dedicated UI banner. LLM-free, temp-independent, cache-stable. The existing LLM `injuryRisk` prose (`CoachingTipDetail.injuryRisk`, Cerebras-assembled, optional) stays as a SEPARATE coaching aid — Phase 10 does NOT replace it or inject into it. The two layers are independent.
- **D-02:** Each risk signal fires only as **(extreme/hyperextension/asymmetry posture condition) AND (loss-of-control indicator)**. Posture-alone flagging is FORBIDDEN (정은지 false-positive prevention). Loss-of-control reuses Phase 8 jerk/jitter temporal signals + the `stability` dimension (instability = loss-of-control proxy).
- **D-03:** Asymmetry = **reference-relative**. Mode 1: 정은지's own L/R deviation is the baseline; flag only if student is significantly MORE asymmetric. Mode 3: vs. previous video. **Absolute L/R asymmetry is NOT flagged in v1** (too many false positives). Quantify with KISMAM Z-score `D=(x−μ)/σ` (`kismam.py` reuse).
- **D-04:** Trunk (lumbar) hyperextension = **trunk-femur angle proxy** (shoulder-hip-knee 3D angle). **Absolute signal → both modes.** Always labeled "estimate/possibility." Hard limitation (locked): single-rigid-body trunk model cannot separate lumbar hyperlordosis from pure hip extension (no mid-spine keypoint). Must combine with D-02 to fire.
- **D-05:** Knee/elbow hyperextension (reverse-bend) detected **in 3D with direction**. **Absolute signal → both modes** (the Mode 3 core "if my posture is like this, injury risk is high"). Method: dot-product gives only 0–180° magnitude (direction-blind) → **track cross-product sign in the segment-local sagittal plane** to distinguish normal flexion from reverse hyperextension. Knee/elbow are 1-DOF hinges so this is valid. Fires via D-02 rule.
- **D-06:** Level mismatch = **Mode 1 only** — `reference.level` (basic/intermediate/advanced) × user `experience` (beginner/intermediate/advanced). Mode 3 does not apply this rule; Mode 3's "overreach" is caught by D-02 control-loss instead.
- **D-07:** No fixed single angle. **Normal-range `[T_min, T_max]`** (elite/reference distribution, KISMAM tol = allowed deviation). Asymmetry is reference-anchored. Absolute anatomical joint/trunk thresholds MUST come from external biomechanics/PT literature (IPSF has no medical injury numbers). **13-video curve-fit FORBIDDEN** ([[scoring-redesign-must-generalize-no-overfit]], [[calibration-source-hard-gate]]).
- **D-08:** Result-screen visually distinct warning banner + "expert referral" copy. Brand color #FF4B33 / Pretendard / light theme. Word "부상 확정" forbidden. (UI specifics owned by `10-UI-SPEC.md`, already approved.)

### Claude's Discretion
- Risk-score numeric scale, number of severity tiers, SafetyFlag field names, per-flag code identifiers — planner/executor's discretion, PROVIDED the contract 3-mirror rule holds (`analysis.ts` ↔ `models.py` ↔ `contract.md`).

### Deferred Ideas (OUT OF SCOPE)
- **Explicit slip/regrip/balance-loss event detection** — v1 uses jerk/jitter+stability instability as the control-loss proxy. Precise event detection (pole-contact tracking, fall detection) = follow-up phase. (This research confirms the proxy is adequate for v1 — see Open Question 4.)
- **Dedicated lumbar spine keypoint** — overcoming the rigid-body trunk limitation via 133-keypoint wholebody or self-trained mid-spine estimation = separate track ([[ml-pose-3d-pivot]]).
- **Dynamic knee valgus (ACL) indicator** — NotebookLM flagged it but it is landing/cutting-centric; pole relevance unverified. Out of v1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAFE-01 | 좌우 비대칭·요추 과신전·레벨 대비 무리한 동작 신호가 위험도 플래그로 결과 화면에 표시되고 "전문가 확인 권유" 카피가 함께 표시된다. "부상 확정" 단정 금지. | New `safety_flags.py` pure module (numpy-only) computes flags from the existing angle matrix + `force_signals_report` control-loss substrate; assembled into `result["safetyFlags"]` at the verified `_process` injection point (after force_signals, before `complete_analysis`); rendered by the approved `10-UI-SPEC.md` amber banner on `result.tsx`. All four flag types (D-03/04/05/06) map to verified substrate below. |
</phase_requirements>

## Summary

Phase 10 adds a deterministic SafetyFlag layer. Every substrate it needs already exists and is unit-tested: the (T, J) angle matrix, KISMAM Z-score scoring (`kismam.score_from_deviation`), the `stability` dimension, per-frame 3D pole-aligned coordinates (`to_coco17_array` → (T, 17, 4)), and — critically — a rich **loss-of-control substrate** in `force_signals.py` (`StabilityMetric` per-phase with `jitter_score`, `jerk_score`, `severity ∈ {low,medium,high}`, and `unstable_body_parts`). The phase is therefore **wiring + a small set of pure firing-rule functions**, not new ML.

The architectural spine is: a new pure module `backend/shared/python/sunity_shared/analysis/safety_flags.py` (numpy-only, like `kismam`/`dimensions`), called from `pipeline/app.py::_process` **immediately after `force_signals_report` is computed** (line ~3467) and **before `complete_analysis`**, writing `result["safetyFlags"]`. The contract gets a new `SafetyFlag` type mirrored across `analysis.ts` ↔ `models.py` ↔ `contract.md`, and `result.tsx` renders it via the already-approved amber UI-SPEC.

**Primary recommendation:** Build `safety_flags.compute_safety_flags(...)` as a pure function returning a flat `list[SafetyFlag]`. Each flag = **posture-condition AND control-loss** (the control-loss boolean is derived from `force_signals_report` severity/`unstable_body_parts`). Thin-slice the work: scaffold + one flag end-to-end first (recommend D-04 trunk proxy — it reuses the already-computed `left_hip`/`right_hip` angle, so it de-risks the wiring with near-zero new math), then layer D-05 (the novel cross-product algorithm, belle's Mode-3 priority), then D-03 (asymmetry), then D-06 (level, Mode 1 only). Absolute anatomical thresholds (D-07) come from cited external literature (knee >5° genu recurvatum clinical threshold; elbow >10° Beighton hypermobility criterion); the trunk proxy has no clean absolute cutoff and must stay reference-anchored.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Posture-condition measurement (angles, asymmetry, hyperextension direction) | API/Backend — pure analysis core (`safety_flags.py`) | — | Deterministic geometry must live with the other pure scoring modules (numpy-only, unit-testable, runs identically on Lambda + RunPod). |
| Loss-of-control derivation | API/Backend — reuse `force_signals.py` | — | Control-loss substrate (jerk/jitter/stability severity) already computed in pipeline; SafetyFlag consumes it, does not recompute. |
| SafetyFlag assembly into result | API/Backend — `pipeline/app.py::_process` | Firestore (`complete_analysis`) | Single analysis path (Lambda+RunPod share `_process`); result persisted via existing `complete_analysis`. |
| Contract type (`SafetyFlag`) | Shared contract (3-mirror) | — | `analysis.ts` ↔ `models.py` ↔ `contract.md` must change in lockstep. |
| Warning banner render | Frontend (RN screen `result.tsx`) | — | Read-only derived display; no client-side computation. UI owned by approved `10-UI-SPEC.md`. |
| Level-mismatch mapping (D-06) | API/Backend — needs `experience` + `reference.level` | — | Both inputs verified reachable at assembly time (see Open Question 3 — RESOLVED). |

## Standard Stack

**No new packages.** This phase is built entirely from existing, in-repo substrate.

### Core (reuse — verified by source read)
| Module / Symbol | Location | Purpose for Phase 10 | Why standard |
|---------|----------|---------|--------------|
| `kismam.score_from_deviation(dev, tol=20.0)` | `analysis/kismam.py:111` | Z-score `100·exp(-½·(dev/tol)²)` — quantify asymmetry deviation & convert any posture excess into a 0–100 severity proxy. `[VERIFIED: source read]` | The single normal-range scoring primitive shared across all dimensions (consistent scale). tol=20° is `[CITED: IPSF CoP]`. |
| `force_signals.ForceSignalsReport` / `.stability_metrics` | `analysis/force_signals.py:402,495` | **Loss-of-control substrate (D-02).** Per-phase `StabilityMetric{jitter_score (deg/frame), jerk_score (deg/sec³), severity, unstable_body_parts}`. `[VERIFIED: source read]` | Already computed in `_process` (line 3458) and persisted; the canonical instability signal. |
| `dimensions.stability_wobble_by_joint(angles, profile)` | `analysis/dimensions.py:342` | Per-joint inter-frame median wobble (deg) dict — control-loss localized to a joint. `[VERIFIED: source read]` | Same algorithm `force_signals._compute_unstable_body_parts` already uses (drift-free). |
| `to_coco17_array(pose_frames)` → (T,17,4) | `analysis/pose_frame.py:326` | Per-frame 3D pole-aligned `[x,y,z]` (+ uncertainty ch) — **the 3D coordinates for D-05 cross-product**. Available in `_process` as `inputs.keypoints_4ch`. `[VERIFIED: source read]` | Already produced upstream; `[:, :, :3]` is the pole-aligned 3D used for `joints3d`. |
| `skeleton.JOINT_ANGLES` / `JOINT_KEYS` | `analysis/skeleton.py:39` | Joint triplets: `left_hip=(shoulder,hip,knee)` = **trunk-femur proxy (D-04)**; `left_knee=(hip,knee,ankle)`, `left_elbow=(shoulder,elbow,wrist)` = **hyperextension joints (D-05)**. `[VERIFIED: source read]` | The contract-fixed 8-joint definition the whole pipeline shares. |
| `models.normalize_body_profile(meta.bodyProfile)` → `{experience, painAreas}` | `models.py:247` | **User experience (D-06)** — `experience ∈ EXPERIENCE_LEVELS`. Reaches `_process` (already used for painAreas at line 3573). `[VERIFIED: source read]` | Single sanitizer; drops spoofed values. |
| `ref.get("level")` (reference doc) | seeded `app/scripts/seed-reference-motions.mjs` (all 11 refs carry `level`) | **Reference skill level (D-06)** — `SkillLevel ∈ basic/intermediate/advanced`. Fetched in MODE_EXPERT via `get_reference_motion`. `[VERIFIED: source read + seed grep]` | Already seeded and returned by admin. |

### Supporting
| Module | Location | When to use |
|--------|----------|-------------|
| `assemble.lookup_motion_branch` / `is_reference_free_motion` | `analysis/assemble.py:106,130` | If a flag should be suppressed for unrecognized motions (e.g., absolute trunk proxy may want recognized-motion gating). Optional. |
| `firestore_admin._validate_force_signals_report` (pattern) | `firestore_admin.py:223` | **Copy this scoped-validator pattern** for a new `_validate_safety_flags` — `result["safetyFlags"]` is a `list[dict]` and the generic nested-array validator will reject/garble it. See Pitfall 1. |
| `@expo/vector-icons` Ionicons (`warning`,`information-circle`), `app/src/theme/` tokens, `highlightNumbers()` | app | UI render per approved `10-UI-SPEC.md`. No new UI deps. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `safety_flags.py` module | Extend `dimensions.py` | Rejected — SafetyFlag is not a score dimension; it's an orthogonal warning layer (D-01). Keep it isolated like `force_pattern.py`. |
| Storing flags inside `result["safetyFlags"]` | New `complete_analysis(safety_flags=…)` kwarg | Either works; `forceSignalsReport` is stored *inside* result yet still passed as a kwarg. Recommend **inside `result`** (set in `_process`) for minimal `firestore_admin` change, with a scoped validator. |
| Cross-product direction (D-05) | Signed angle via `atan2` of projected vectors | Equivalent math; cross-product sign is the clearer expression of "which side of the sagittal plane." Pick one, document the sign convention. |

**Installation:** none.

## Package Legitimacy Audit

> Not applicable — this phase installs **no external packages** (Python: numpy-only reuse; RN: existing tokens + Ionicons already in `package.json`). No registry surface. slopcheck/registry verification N/A.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                       pipeline/app.py :: _process  (single path: Lambda CPU fallback + RunPod GPU)
                       ──────────────────────────────────────────────────────────────
 S3 video ─► extract ─► RTMW pose ─► angles (T,J), pose_frames, keypoints_4ch (T,17,4)
                                          │
                                          ├─► recognizer.recognize ─► profile (TechniqueProfile)
                                          ├─► dimensions.absolute_dimension_scores ─► stability, line
                                          ├─► kismam.assess / overall ─► assessments, dimension_scores
                                          ├─► assemble.build_result ─────────────────► result{} (overallScore, dimensions, joints, tips, comparison)
                                          │
   reference doc (MODE_EXPERT) ───────────┤  ref.angles (asymmetry baseline, D-03)
   meta.bodyProfile.experience (D-06) ────┤  ref.level (D-06)
                                          │
                                          ▼
                       fs.compute_force_signals ─► force_signals_report
                                          │        (StabilityMetric[].severity, jitter, jerk, unstable_body_parts)  ◄── CONTROL-LOSS SUBSTRATE (D-02)
                                          │
              ┌───────────────────────────┴─── NEW (Phase 10) injection point (~line 3467) ───┐
              ▼                                                                                 │
   safety_flags.compute_safety_flags(                                                           │
       angles, keypoints_4ch, force_signals_report,                                             │
       dimension_scores, reference_angles=ref.angles|None,                                      │
       experience=…, reference_level=…|None, mode, profile)                                     │
              │   each flag = POSTURE-CONDITION  AND  CONTROL-LOSS  (D-02 combination)           │
              ▼                                                                                  │
   list[SafetyFlag]  ─►  result["safetyFlags"] = [scalar-only dicts]  ─────────────────────────┘
                                          │
                                          ▼
                       firestore_admin.complete_analysis(uid, id, result, …)
                       (NEW: _validate_safety_flags scoped validator — Pitfall 1)
                                          │
                                          ▼  onSnapshot
                       app/src/app/analysis/result.tsx  ─►  InjuryRiskSection (amber banner, 10-UI-SPEC)
                       rendered only if safetyFlags non-empty; omitted silently otherwise
```

### Component Responsibilities
| Component | Responsibility | File (new/existing) |
|-----------|----------------|---------------------|
| `safety_flags.py` | Pure firing-rule functions + `SafetyFlag` dataclass(es). numpy-only, no AWS/network. | NEW `backend/shared/python/sunity_shared/analysis/safety_flags.py` |
| `_process` injection | Call `compute_safety_flags`, set `result["safetyFlags"]`, derive `experience`/`reference_level`. | EXISTING `backend/functions/pipeline/app.py` (~3467) |
| `_validate_safety_flags` | Scoped Firestore validator (list[dict] scalar-only). | EXISTING `backend/shared/python/sunity_shared/firestore_admin.py` |
| `SafetyFlag` contract type | 3-mirror type. | `app/src/types/analysis.ts`, `models.py`, `docs/contract.md` |
| `InjuryRiskSection`/`InjuryRiskFlagCard` | Amber banner render. | `app/src/app/analysis/result.tsx` (+ new RN components) |

### Recommended Project Structure
```
backend/shared/python/sunity_shared/analysis/
└── safety_flags.py          # NEW — pure: dataclass + compute_safety_flags + per-flag helpers
backend/tests/phase10/
├── test_safety_flags_firing_rule.py     # posture-AND-control gate, elite=no-FP
├── test_safety_flags_hyperextension.py  # D-05 cross-product sign convention
├── test_safety_flags_asymmetry.py       # D-03 reference-anchored
├── test_safety_flags_level.py           # D-06 mode1-only mapping
└── test_safety_flags_contract.py        # scalar-only / nested-array validator
app/src/app/analysis/result.tsx          # + InjuryRiskSection block (10-UI-SPEC)
```

### Pattern 1: Pure firing-rule module (mirror `kismam`/`force_pattern`)
**What:** `compute_safety_flags(...)` is a pure function returning `list[SafetyFlag]` (frozen dataclasses). No boto3/network. Each per-flag helper is independently unit-testable.
**When to use:** Always — matches the established "pure analysis core (numpy only)" pattern (`CLAUDE.md`, `validation.py` precedent).
```python
# Source: pattern mirrors backend/shared/python/sunity_shared/analysis/kismam.py
@dataclass(frozen=True)
class SafetyFlag:
    flag_type: str          # 'asymmetry' | 'trunk_hyperextension' | 'joint_hyperextension' | 'level_mismatch'
    body_region: str        # KO region for copy (e.g. '무릎·팔꿈치', '허리')
    severity: str           # 'low' | 'medium' | 'high'  (mirror force_signals SeverityLevel)
    posture_condition: str  # short audit string — which geometric condition was met
    control_loss_signal: str# short audit string — which instability fired (D-02 partner)
    confidence: str         # 'low' | 'medium' | 'high'
    mode_scope: str         # 'both' | 'mode1_only'  (D-06 is mode1_only)
    # NO nested lists — Firestore flat (Pitfall 1)
```

### Pattern 2: Posture-AND-control-loss gate (D-02 — the core invariant)
**What:** A flag is emitted **iff** a posture condition AND a control-loss indicator are both true. Posture-alone NEVER fires.
```python
# Source: derived from force_signals.StabilityMetric (analysis/force_signals.py:402)
def _control_loss_for_joint(fsr, joint_key) -> bool:
    # instability proxy (D-02): phase-level severity OR joint in unstable_body_parts
    sev_hit = any(m.severity in ("medium", "high") for m in fsr.stability_metrics)
    joint_hit = any(joint_key in m.unstable_body_parts for m in fsr.stability_metrics)
    return sev_hit or joint_hit

def _maybe_flag(posture_met: bool, control_lost: bool, ...) -> SafetyFlag | None:
    if posture_met and control_lost:      # D-02 — both required
        return SafetyFlag(...)
    return None                            # posture alone → no flag (정은지 FP guard)
```
> Tune the exact control-loss predicate during planning (joint-localized `unstable_body_parts` is more specific than phase-level severity; prefer joint-localized where the flag is joint-specific, e.g. D-05).

### Pattern 3: D-05 cross-product hyperextension direction (concrete math)
**What:** Dot-product of the two limb segments gives only the 0–180° magnitude (direction-blind: a knee bent 30° and hyperextended 30° both read ~150°). The sign of the cross product, evaluated against a segment-local sagittal normal, separates flexion from reverse hyperextension.
```python
# Source: standard 1-DOF hinge geometry; coords from to_coco17_array (pose_frame.py:326)
# Knee:  A=hip, V=knee, C=ankle.   Elbow: A=shoulder, V=elbow, C=wrist.
#   u = A - V   (proximal segment, knee→hip)
#   w = C - V   (distal segment, knee→ankle)
#   magnitude = degrees(arccos( dot(u,w) / (|u||w|) ))     # 0..180, direction-blind
#   n = u × w   (cross product, the hinge axis normal in pole-aligned 3D)
#   sagittal_ref = pole_aligned frontal axis (e.g. shoulder→hip vector projected) — the body's
#                  flexion plane normal for that limb side.
#   sign = dot(n, sagittal_ref)
#   NORMAL FLEXION  : sign matches the side's flexion convention (joint folds forward)
#   HYPEREXTENSION  : sign reversed AND magnitude near 180° (segment passes the straight line
#                     toward the back) → reverse-bend (genu recurvatum / elbow hyperextension)
```
**Sign convention (lock in plan):** establish per-side (left/right) which sign = anatomical flexion using a known-flexion reference frame (e.g. 정은지 reference where the move flexes the joint), then hyperextension = opposite sign with magnitude > (180° − tol). Validate on elite videos (must read as flexion/straight, not hyperextension) before trusting.

### Pattern 4: D-03 asymmetry, reference-anchored (D-07-safe)
```python
# Source: kismam.score_from_deviation (analysis/kismam.py:111)
# student_LR = |mean(student_left_joint) - mean(student_right_joint)|   (over hold window)
# ref_LR     = |mean(ref_left_joint)     - mean(ref_right_joint)|       (mode1; mode3 = prev video)
# excess     = max(0.0, student_LR - ref_LR)    # intentional asymmetry in ref auto-cancels
# posture_met = score_from_deviation(excess, tol=20.0) < SOME_THRESHOLD   # i.e. excess >> tol
# Mode3: ref_LR from previous analysis angles (already fetched for DTW). Absolute L/R NOT flagged (D-03).
```

### Anti-Patterns to Avoid
- **Posture-alone flag.** Any flag that fires without a control-loss partner violates D-02 and will false-positive 정은지. Tests must assert this.
- **Recomputing instability.** Do NOT recompute jerk/jitter — consume `force_signals_report`. (Avoids drift, matches R5 double-smoothing ban.)
- **Curve-fitting thresholds on the 13 videos.** D-07/[[calibration-source-hard-gate]] — absolute cutoffs from external literature only; relative cutoffs from reference/KISMAM tol only.
- **Treating the trunk proxy as a true lumbar measurement.** D-04 — always parenthesize the rigid-body limitation in copy (UI-SPEC already does).
- **Nested lists inside a SafetyFlag.** Firestore forbids nested arrays (Pitfall 1).
- **Injecting SafetyFlag into the LLM `injuryRisk` prose, or vice versa.** D-01 — strictly independent layers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Loss-of-control detection | New slip/jerk detector | `force_signals_report` (`StabilityMetric.severity`, `jerk_score`, `unstable_body_parts`) | Already computed, persisted, unit-tested; recomputing causes drift (R5). |
| Normal-range scoring / Z-score | New deviation→severity curve | `kismam.score_from_deviation(dev, tol)` | Single shared scale; tol=20° is the IPSF-cited tolerance. |
| Per-joint wobble localization | New per-joint variance loop | `dimensions.stability_wobble_by_joint` | Same windowing as the score path (`_select_window`), drift-free. |
| 3D coordinate extraction | New keypoint reshaping | `inputs.keypoints_4ch` = `to_coco17_array(pose_frames)` | Pole-aligned 3D already produced; `[:, :, :3]`. |
| Firestore nested-array safety | New flattener | Copy `_validate_force_signals_report` → `_validate_safety_flags` | Established scoped-validator pattern; generic validator mishandles list[dict]. |
| Amber warning UI | New design tokens/colors | `10-UI-SPEC.md` (approved) + `app/src/theme/` + `warnAmberBg` additive token | UI contract already checker-approved; hardcoding colors forbidden. |

**Key insight:** Phase 10's hard part is **policy** (which threshold, which AND-combination), not computation — every numeric signal it needs already flows through `_process`.

## Runtime State Inventory

> Greenfield-additive within an existing pipeline — no rename/migration. This is included for completeness because the phase persists a new field.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | New `result.safetyFlags` field written to `users/{uid}/analyses/{id}`. No existing records carry it. | None — additive; UI omits the section when absent (graceful, matches `bodyProfileSummary` pattern). No backfill needed (pilot re-runs analysis). |
| Live service config | None — no new env vars required (no feature toggle mandated; planner may add an optional `SAFETY_FLAGS_ENABLED` default-ON for kill-switch parity with other layers). | Optional toggle decision at plan time. |
| OS-registered state | None. | None — verified: no scheduler/daemon touches this. |
| Secrets/env vars | None — deterministic, LLM-free (D-01). No Gemini/Cerebras/SSM key needed. | None. |
| Build artifacts | New module ships in the Lambda layer (`sunity_shared`) + RunPod (shared import). `sam build --use-container` already required. | Redeploy Lambda layer + ensure RunPod pulls latest `sunity_shared` (standard push-first, [[gsd-pod-work-push-first]]). |

## Common Pitfalls

### Pitfall 1: Firestore nested-array rejection of `safetyFlags`
**What goes wrong:** `result["safetyFlags"]` is a `list[dict]`. The generic `_validate_flat_dict_no_nested_array` / `_validate_dict_only_scalars` path will reject it or a nested `list[str]` inside a flag will throw at write time → analysis fails as `server_error`.
**Why:** Firestore forbids nested arrays ([[firestore-nested-array-flat]]); the codebase enforces it strictly except via scoped validators.
**How to avoid:** Add `_validate_safety_flags` mirroring `_validate_force_signals_report` (firestore_admin.py:223) — allow the top-level `safetyFlags` list of scalar-only dicts; forbid any nested list. Keep each `SafetyFlag` field scalar (no `causes[]`-style nesting).
**Warning signs:** Local write test passes but Pod write throws `INVALID_ARGUMENT`/`TypeError` on a list field.

### Pitfall 2: Posture-alone false positive on 정은지 (the project's core value)
**What goes wrong:** An absolute-angle flag (D-04/D-05) fires on 정은지's intentional 180° split / deep backarch / hyperextension — the exact regression the project must never ship ([[score-spec-95-100-elite-vision-fix]]).
**Why:** IPSF treats hyperextension as a point-scoring element; absolute angle alone cannot distinguish elite control from injury.
**How to avoid:** Enforce the D-02 AND-gate in code AND in tests — a dedicated test feeds 정은지 reference angles + their (low) control-loss and asserts **zero flags**. This is the phase's headline validation gate.
**Warning signs:** Any flag emitted when `force_signals_report` severity is all `low`.

### Pitfall 3: Threshold provenance leak (curve-fit)
**What goes wrong:** Tuning the knee/elbow/asymmetry cutoff until the 13 held videos "look right."
**Why:** Violates [[calibration-source-hard-gate]] / [[scoring-redesign-must-generalize-no-overfit]] — overfits, won't generalize.
**How to avoid:** Absolute joint cutoffs cite external literature (this doc's State-of-the-Art table); relative cutoffs = reference-anchored or KISMAM tol (20°). Document each threshold's source in the module header (mirror `kismam.py` `[CITED]`/`[ASSUMED]` tagging). The 13 videos are a **known-answer regression set, not a fit target**.
**Warning signs:** A threshold constant whose only justification is "matches our videos."

### Pitfall 4: D-04 trunk proxy over-claim
**What goes wrong:** Reporting "lumbar hyperextension" as fact when the shoulder-hip-knee angle conflates lumbar extension with hip extension (no mid-spine keypoint).
**Why:** Single-rigid-body trunk model (D-04 locked limitation).
**How to avoid:** Keep the absolute trunk cutoff out of v1 (reference-anchored only) and keep the UI-SPEC parenthetical ("몸통을 한 덩어리로 추정한 값이라 정확하지 않을 수 있어요"). Require D-02 control-loss to fire.

### Pitfall 5: Control-loss substrate is `low`-confidence on unrecognized motions
**What goes wrong:** `force_signals` Layer-1 confidence defaults to `low` when there's no preflight gate / `motion_id`; flags may under- or over-fire if you read severity without confidence.
**Why:** `compute_phase_boundaries` ceiling is `low` until preflight passes (R4).
**How to avoid:** Treat `force_signals_report.overall_confidence` as a gate — emit `SafetyFlag.confidence` accordingly and let the UI's possibility-framing absorb it (UI-SPEC already frames everything as 가능성). Do not hard-fail on low confidence (graceful, [[motion-routing-generalize-principle]]).

## Code Examples

### Injection point in `_process` (verified surroundings)
```python
# Source: backend/functions/pipeline/app.py  — AFTER force_signals (line ~3467), BEFORE complete_analysis (line ~3785)
force_signals_report = fs.compute_force_signals(... )           # existing, line 3458
force_signals_dict = _dataclass_to_camel_case_dict(force_signals_report)

# NEW (Phase 10):
experience = (models.normalize_body_profile(meta.get("bodyProfile")) or {}).get("experience")
reference_level = ref.get("level") if mode == models.MODE_EXPERT and ref else None   # ref fetched at line 2971
reference_angles_for_sym = ...  # mode1: from ref["angles"] reshaped; mode3: prev analysis angles (already in scope)

safety_flags = safety_flags_mod.compute_safety_flags(
    angles=angles,
    keypoints_4ch=inputs.keypoints_4ch,
    force_signals_report=force_signals_report,
    dimension_scores=dimension_scores,
    reference_angles=reference_angles_for_sym,
    experience=experience,
    reference_level=reference_level,
    mode=mode,
    profile=profile,
)
result["safetyFlags"] = [ _safety_flag_to_camel(f) for f in safety_flags ]  # scalar-only dicts
# ... existing complete_analysis(...) — result now carries safetyFlags
```

### Contract mirror (the 3-way edit)
```typescript
// Source: app/src/types/analysis.ts — add NEAR AnalysisResult (sibling of forceSignalsReport, line 518)
export type SafetyFlagType = 'asymmetry' | 'trunk_hyperextension' | 'joint_hyperextension' | 'level_mismatch';
export interface SafetyFlag {
  flagType: SafetyFlagType;
  bodyRegion: string;     // KO region label
  severity: 'low' | 'medium' | 'high';
  confidence: 'low' | 'medium' | 'high';
  modeScope: 'both' | 'mode1_only';
  postureCondition: string;   // audit
  controlLossSignal: string;  // audit (D-02 partner)
}
// AnalysisResult: add `safetyFlags?: SafetyFlag[] | null;`  (optional → legacy docs + graceful-omit)
```
Mirror in `models.py` (validation literals + a `normalize`/builder if desired) and document in `docs/contract.md`. Per [[mode3-progress-not-similarity]] and objectivity ([[analysis-objectivity-no-human-scores]]): the flag carries **threshold-derived severity, never a human score label**.

## State of the Art

> External anatomical thresholds for D-07. IPSF has **no** medical injury numbers (NotebookLM confirmed), so absolute joint cutoffs are sourced from clinical/biomechanics literature. **All MEDIUM confidence — confirm with belle before locking.**

| Signal | Defensible external threshold | Source | Phase-10 usage |
|--------|-------------------------------|--------|----------------|
| Knee hyperextension (genu recurvatum) | Clinical threshold = **>5°** beyond 0° neutral is "hyperextension"; 5–10° common benign variation; **moderate/severe >10–15°, severe >20°**. | `[CITED: en.wikipedia.org/wiki/Genu_recurvatum + clinical PT sources]` | Posture condition for D-05 knee. Use >5° as detection floor, but **only fires with control-loss** (D-02). Severity tiers can map to the 10°/20° bands. |
| Elbow hyperextension | **>10°** beyond neutral = Beighton hypermobility criterion (1 pt/elbow); 5–15° natural variant (esp. women). | `[CITED: physio-pedia.com/Beighton_Score, orthofixar Beighton]` | Posture condition for D-05 elbow. Use >10° detection floor; D-02 gate required. |
| Lumbar/trunk hyperextension | Lumbar extension ROM ≈ 25–30°; **no clean single anatomical injury cutoff exists**, and the trunk-femur proxy conflates lumbar+hip. | `[ASSUMED — general PT ROM knowledge]` | **Conclusion: NO defensible absolute cutoff for v1.** D-04 trunk stays **reference-anchored** (student vs 정은지/prev) + D-02. Absolute lumbar threshold = deferred. |
| Asymmetry | Reference-anchored only (KISMAM tol = 20° `[CITED: IPSF CoP]`). | repo artifact | D-03 — `max(0, student_LR − ref_LR)`. |

**Deprecated/outdated:** none — this is a net-new layer.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Knee >5° (detection) / >10–20° (severity bands) is the right genu-recurvatum cutoff for pole athletes | State of the Art (D-07) | Too low → 정은지 trips posture condition (mitigated by D-02 AND-gate, but tune); too high → misses genuine risk. Confirm with belle. |
| A2 | Elbow >10° (Beighton) is the right hyperextension floor | State of the Art (D-07) | Same as A1 for elbow. |
| A3 | No defensible absolute lumbar cutoff exists → trunk D-04 reference-anchored only in v1 | State of the Art (D-07) | If belle wants an absolute trunk number, needs a sourced value; otherwise trunk fires only relative + control-loss. |
| A4 | `force_signals_report` severity/`unstable_body_parts` is a sufficient v1 control-loss proxy | Open Q4 | If insufficient, some genuine slips/regrips go undetected (acceptable per CONTEXT deferral; flag as known v1 limit). |
| A5 | Storing `result["safetyFlags"]` (vs new kwarg) with a scoped validator is the chosen persistence path | Architecture | Wrong → Firestore write failure (Pitfall 1); low risk, validator pattern proven. |
| A6 | Optional `SAFETY_FLAGS_ENABLED` toggle is not required (no LLM, deterministic) | Runtime State | If belle wants a kill-switch for parity, add default-ON env flag. |

**If A1–A3 are confirmed/adjusted by belle, they graduate from `[ASSUMED]`/`[CITED-MEDIUM]` to locked thresholds.**

## Open Questions

1. **Thin-slice ordering — which flag goes end-to-end first?**
   - What we know: All four flag types share the same scaffold + AND-gate. D-04 trunk reuses the already-computed `left_hip`/`right_hip` angle (least new math → fastest wiring de-risk). D-05 is belle's stated Mode-3 priority but has the novel cross-product algorithm (highest algorithm risk).
   - Recommendation: **Slice 1 = scaffold + D-04 trunk** (proves data-structure → AND-gate → assembly → render with minimal algorithm), **Slice 2 = D-05 joint hyperextension** (the cross-product, must land in v1), **Slice 3 = D-03 asymmetry**, **Slice 4 = D-06 level (mode1-only)**. If the planner prefers to lead with belle's priority, swap Slices 1↔2 but accept higher slice-1 risk.

2. **Control-loss predicate granularity (phase-level vs joint-level).**
   - What we know: `StabilityMetric.severity` is per-phase; `unstable_body_parts`/`stability_wobble_by_joint` is per-joint.
   - Recommendation: For joint-specific flags (D-05, D-03) use joint-localized control-loss (`unstable_body_parts` containing that joint) for precision; for trunk (D-04) use phase-level severity (hold-phase instability). Lock in plan.

3. **D-06 data-flow precondition — RESOLVED (feasible).**
   - `experience` reaches `_process` via `models.normalize_body_profile(meta.bodyProfile)["experience"]` (already consumed at line 3573). `reference.level` reaches `_process` via `ref.get("level")` in MODE_EXPERT (`get_reference_motion`; all 11 reference docs seed `level`). **No new plumbing needed.** `[VERIFIED: source read + seed grep]`

4. **D-02 v1 control-loss proxy sufficiency — adequate for v1.**
   - The jerk/jitter + stability-severity substrate captures "rebound/momentum, wobble, unstable hold" — the literature's loss-of-control markers that CONTEXT maps to the AND-gate. Explicit slip/regrip/balance-loss event detection is genuinely deferred (needs pole-contact tracking, `ContactStabilityMetric` is currently `low`-confidence Layer-1). **Conclusion: the proxy is a defensible v1**; document that precise event detection is a follow-up (CONTEXT already defers it). Do NOT block Phase 10 on it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| numpy | `safety_flags.py` core | ✓ | >=1.26 (Lambda+dev) | — |
| `force_signals` / `dimensions` / `kismam` / `pose_frame` modules | substrate | ✓ | in-repo | — |
| `experience` + `reference.level` data | D-06 | ✓ | seeded + sanitized | D-06 simply omits its flag if either is absent (graceful) |
| pytest >=8 | validation tests | ✓ | backend/requirements-dev.txt | — |
| Ionicons / theme tokens | UI | ✓ | app/package.json | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none material.

## Validation Architecture

> `nyquist_validation: true` — section required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| Config file | `backend/tests/conftest.py` (no pytest.ini; phase dirs `backend/tests/phaseNN/`) |
| Quick run command | `python -m pytest backend/tests/phase10 -x -q` |
| Full suite command | `python -m pytest backend/tests -q` |
| App static gate | `cd app && npm run typecheck` (tsc --noEmit) — only app gate; covers the `SafetyFlag` 3-mirror addition |

### Phase Requirements → Test Map
| Req | Behavior | Test type | Automated command | File |
|-----|----------|-----------|-------------------|------|
| SAFE-01 / D-02 | **Elite no-FP:** 정은지 reference angles + all-`low` control-loss → **zero flags** | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py::test_elite_posture_alone_no_flag -x` | ❌ Wave 0 |
| SAFE-01 / D-02 | Posture met AND control-loss → flag emitted; posture met + no control-loss → no flag | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py -x` | ❌ Wave 0 |
| D-05 | Cross-product: synthetic flexed knee → no hyperext; synthetic reverse-bend knee + control-loss → flag | unit | `pytest backend/tests/phase10/test_safety_flags_hyperextension.py -x` | ❌ Wave 0 |
| D-03 | student_LR >> ref_LR (with control-loss) → asymmetry flag; equal asymmetry → none (reference-anchored) | unit | `pytest backend/tests/phase10/test_safety_flags_asymmetry.py -x` | ❌ Wave 0 |
| D-06 | Mode1 advanced ref × beginner experience + control-loss → level_mismatch flag; same in Mode3 → no flag (mode1-only) | unit | `pytest backend/tests/phase10/test_safety_flags_level.py -x` | ❌ Wave 0 |
| SAFE-01 contract | `result["safetyFlags"]` scalar-only; `_validate_safety_flags` rejects nested list | unit | `pytest backend/tests/phase10/test_safety_flags_contract.py -x` | ❌ Wave 0 |
| SAFE-01 determinism | Same input → identical flags (LLM-free, D-01) | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py::test_deterministic -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/phase10 -x -q` (+ `npm run typecheck` for contract/UI tasks).
- **Per wave merge:** `pytest backend/tests -q` (full backend — guards no regression in `force_signals`/`dimensions`/`assemble`).
- **Phase gate:** full backend suite green + `npm run typecheck` green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `backend/tests/phase10/__init__.py` + the 6 test files above (no Phase-10 tests exist yet).
- [ ] Shared fixture: 정은지 reference angle matrix + low control-loss `ForceSignalsReport` (the elite-no-FP fixture). Reuse the success/fail pair dataset ([[jeongeunji-success-fail-pair-dataset]]) as the **known-answer regression set, not a fit target** ([[calibration-source-hard-gate]]).
- [ ] Synthetic hyperextension fixtures (hand-built (T,17,4) arrays for flexed vs reverse-bent knee/elbow) — avoids needing real injury videos and keeps thresholds literature-sourced.
- No framework install needed (pytest present).

## Security Domain

> `security_enforcement: true`, ASVS L1 — section required.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new endpoints; SafetyFlag is computed in the already-authenticated pipeline. |
| V3 Session Management | no | n/a. |
| V4 Access Control | yes (inherited) | Flags written under `users/{uid}/analyses/{id}` via Firestore Admin (bypasses rules server-side); client reads are already gated by existing `firestore.rules` for own-user docs. No rule change needed (additive field). |
| V5 Input Validation | **yes** | `experience`/`reference.level` already sanitized (`normalize_body_profile`, enum membership). New `_validate_safety_flags` enforces scalar-only shape before Firestore write (Pitfall 1). No user-supplied free text enters flags (copy is template-driven). |
| V6 Cryptography | no | No secrets, no crypto (deterministic, LLM-free — D-01). |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Spoofed `bodyProfile.experience` to suppress/trigger a flag | Tampering | `normalize_body_profile` already drops non-enum values → None → D-06 flag simply omitted (fail-safe, no crash). |
| Firestore nested-array injection via malformed flag dict | Tampering/DoS (write failure → analysis marked `server_error`) | `_validate_safety_flags` scoped validator (mirror `_validate_force_signals_report`); flags are backend-built, not user-supplied. |
| Over-claiming "부상 확정" (reputational/medical-claim risk) | (Info disclosure / liability) | Copy contract (`10-UI-SPEC.md`) forbids confirmed-injury language; possibility-only framing + expert-referral enforced; objectivity ([[analysis-objectivity-no-human-scores]]) bars human score labels — flags carry only threshold-derived severity. |
| Silent no-op (flag layer fails, user assumes "safe") | (Availability/trust) | UI-SPEC mandates **no reassurance text** when no flags — absence ≠ safety. Backend graceful-omit on malformed data matches `result.tsx` convention. |

## Sources

### Primary (HIGH confidence — source read this session)
- `backend/shared/python/sunity_shared/analysis/{skeleton,kismam,dimensions,temporal,force_signals,assemble}.py` — substrate, signatures, firing-rule reuse.
- `backend/functions/pipeline/app.py::_process` (lines 2828–3875) — injection point, data-in-scope, force_signals call, complete_analysis.
- `backend/shared/python/sunity_shared/{models.py,firestore_admin.py}` — `normalize_body_profile`, `complete_analysis`, scoped-validator pattern.
- `app/src/types/analysis.ts` — `CoachingTipDetail.injuryRisk`, `ExperienceLevel`, `SkillLevel`, `reference.level`, `AnalysisResult.forceSignalsReport`, `BodyProfile.experience`.
- `app/scripts/seed-reference-motions.mjs` — all 11 reference docs carry `level` (D-06 feasibility).
- `.planning/phases/10-injury-risk-flags/{10-CONTEXT.md,10-UI-SPEC.md}`, `.planning/REQUIREMENTS.md` (SAFE-01).

### Secondary (MEDIUM confidence — external, verify with belle)
- [Genu recurvatum — Wikipedia](https://en.wikipedia.org/wiki/Genu_recurvatum) — knee hyperextension >5° clinical threshold, severity bands.
- [Beighton Score — Physiopedia](https://www.physio-pedia.com/Beighton_Score) / [OrthoFixar](https://orthofixar.com/special-test/beighton-score/) — elbow hyperextension >10° hypermobility criterion.

### Tertiary (LOW confidence — flagged)
- Lumbar extension ROM ≈25–30° (general PT knowledge) — used only to conclude **no defensible absolute trunk cutoff for v1**.

## Metadata

**Confidence breakdown:**
- Standard stack / substrate reuse: HIGH — every module/signature read directly.
- Architecture / injection point / data flow (incl. D-06): HIGH — verified in `_process` source.
- D-05 cross-product method: MEDIUM-HIGH — standard hinge geometry; 3D coords confirmed available; sign convention must be calibrated against elite reference in plan.
- Absolute anatomical thresholds (D-07): MEDIUM — externally cited but require belle confirmation (Assumptions A1–A3).
- Pitfalls / validation / security: HIGH — derived from existing codebase conventions.

**Research date:** 2026-06-29
**Valid until:** 2026-07-29 (stable internal substrate; external thresholds are settled clinical knowledge). Re-verify if `force_signals.py` or the contract changes.
