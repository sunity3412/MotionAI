---
phase: 10
reviewers: [codex]
reviewed_at: 2026-06-29
plans_reviewed: [10-01-PLAN.md, 10-02-PLAN.md, 10-03-PLAN.md, 10-04-PLAN.md]
note: claude skipped (self — running inside Claude Code CLI); gemini/coderabbit/opencode/qwen/cursor not installed
---

# Cross-AI Plan Review — Phase 10

## Codex Review

## Overall

The plan set is well-structured and mostly aligned with SAFE-01: contract-first, deterministic backend computation, UI as read-only display, and explicit no-false-positive gates. The main weakness is that the core false-positive defense, "posture AND control-loss," is only as strong as the control-loss predicate. Several plans use broad phase-level instability, unclear time alignment, or unspecified joint mapping, which can still flag elite intentional poses if tracking noise or unrelated wobble is present. Overall risk is **MEDIUM**, with **HIGH-risk pockets** in D-05 cross-product hyperextension and Mode 3 reference plumbing.

---

## 10-01-PLAN.md

### Summary
Strong foundation plan: establishes the shared contract, pure module boundary, scalar-only Firestore shape, UI token, and test scaffold before behavior lands. Main issue is RED-test inconsistency: the elite no-FP test should pass against an empty stub, while positive-behavior tests should be xfail/RED.

### Strengths
- Good D-01 boundary: `SafetyFlag` separate from LLM `injuryRisk`.
- Contract 3-mirror explicitly planned.
- Scalar-only dataclass anticipates Firestore nested-array constraints.
- Early fixture/test scaffold useful for later waves.
- `warnAmberBg` additive, brand color unchanged.

### Concerns
- **MEDIUM:** "firing-rule tests are RED" conflicts with `compute_safety_flags` stub returning `[]`; elite no-FP should be GREEN immediately.
- **MEDIUM:** Full backend suite listed as GREEN, but future-behavior tests may fail unless all are `xfail`.
- **MEDIUM:** Re-exporting `SafetyFlag` from `models.py` could introduce circular-import risk if analysis modules already import `models`.
- **LOW:** "정은지 angles drawn from dataset" should be known-answer regression only — avoid implying fixture values drive thresholds.

### Suggestions
- Make `test_elite_posture_alone_no_flag` GREEN in Wave 0.
- Mark only positive future-behavior tests `xfail(strict=True)` or skip until implementation.
- Add an import-cycle check for `from sunity_shared.models import SafetyFlag`.
- Record fixture provenance: "regression fixture, not calibration input."

### Risk Assessment
**LOW-MEDIUM.** Mostly scaffold risk; biggest risk is test-suite ambiguity propagating unclear RED/GREEN to later waves.

---

## 10-02-PLAN.md

### Summary
The most important vertical slice, generally well designed: proves compute → persist → render end to end and locks the D-02 no-FP invariant. But the D-04 trunk rule is underspecified: control-loss may be too broad, posture and instability may not be time-aligned, and Mode 3 reference availability is assumed rather than proven.

### Strengths
- Correctly wires after `force_signals_report`, before persistence.
- Adds scoped `_validate_safety_flags`.
- UI copy possibility-framed, omits reassurance when empty.
- All four UI copy mappings planned early, reducing later churn.
- Preserves LLM `injuryRisk` separation.

### Concerns
- **HIGH:** Phase-level control-loss can still false-positive elite poses if unrelated instability/noise is medium/high.
- **HIGH:** AND-gate is not time-aligned — a trunk posture in one window plus instability elsewhere may fire incorrectly.
- **MEDIUM:** D-04 described as reference-anchored only, but original D-04 says absolute signal works in both modes — needs explicit resolution.
- **MEDIUM:** Mode 3 "previous-analysis angles already in scope" is assumed; if unavailable, trunk/asymmetry silently no-op.
- **MEDIUM:** `score_from_deviation(excess, tol=20) < threshold` does not name/justify the threshold.
- **LOW:** Both `result["safetyFlags"]` and a `complete_analysis(..., safety_flags=...)` kwarg may duplicate persistence paths.

### Suggestions
- Require control-loss to be relevant/local: trunk/hip/shoulder/core instability, not any phase wobble.
- Align posture condition and control-loss to the same hold/phase/window.
- Explicitly prove or add plumbing for Mode 3 previous-analysis angles.
- Define the KISMAM threshold numerically with provenance.
- Prefer one persistence path, or document why the kwarg overwrite is safe.

### Risk Assessment
**MEDIUM-HIGH.** End-to-end architecture good, but FP defense needs sharper locality and temporal alignment.

---

## 10-03-PLAN.md

### Summary
Targets the hardest algorithmic part. Intent correct, but D-05 is high risk: cross-product sign conventions in real pole-sport video are unstable under camera angle, inversion, side mirroring, noisy 3D joints, unclear body-plane references. Synthetic tests alone don't protect the 정은지 no-FP requirement.

### Strengths
- Recognizes dot-product magnitude is direction-blind.
- Uses D-02 + joint-localized control-loss, not posture alone.
- Plans boundary/noise/sign-convention tests.
- Avoids 13-video curve-fitting, tags external thresholds.
- Keeps UI unchanged via existing copy map.

### Concerns
- **HIGH:** Sign convention underspecified — "shoulder→hip projected" may not define a stable sagittal reference for inverted/spinning pole poses.
- **HIGH:** `compute_safety_flags` does not appear to receive a known-flexion reference frame, despite the plan saying the sign convention is established from one.
- **HIGH:** Synthetic flex/reverse fixtures may pass while real elite keypoints still misclassify.
- **MEDIUM:** Hyperextension amount should be explicitly `180 - included_angle` with reversed sign; otherwise threshold semantics easy to invert.
- **MEDIUM:** `unstable_body_parts` naming may not match `left_knee`/`right_elbow` keys exactly.
- **MEDIUM:** Wikipedia/Physiopedia citations are weak for locking medical thresholds.

### Suggestions
- Add real known-good elite keypoint fixture coverage, not only synthetic arrays.
- Emit D-05 only when body-plane confidence, segment lengths, frame consistency, keypoint confidence are acceptable.
- Define exact math for hyperextension amount and severity bands.
- Verify `unstable_body_parts` key names against actual `force_signals` output.
- Make D-05 conservative: no flag on ambiguous sagittal reference.

### Risk Assessment
**HIGH.** Algorithmically fragile; directly threatens the core no-FP value unless real-video validation and confidence gating are strengthened.

---

## 10-04-PLAN.md

### Summary
Completes SAFE-01 with reference-anchored asymmetry and Mode-1-only level mismatch. Direction sound (avoiding absolute asymmetry), but the asymmetry rule needs specificity on joint selection, aggregation, control-loss locality, and Mode 3 anchor plumbing.

### Strengths
- Avoids absolute L/R asymmetry in v1.
- Reference-anchored excess is right for intentional asymmetric pole moves.
- Mode-1-only level mismatch respects unknown Mode 3 difficulty.
- Spoofed-experience fail-safe planned.
- Reuses existing UI and contract.

### Concerns
- **HIGH:** Mode 3 asymmetry depends on previous-video/reference angles being available; not explicitly implemented in this plan.
- **MEDIUM:** "Relevant joints" unspecified — max/average/per-joint produce different FP profiles.
- **MEDIUM:** Control-loss for asymmetry left vague as `_control_loss_*`; should be pair/joint-localized.
- **MEDIUM:** Rank gap `>= 1` may over-warn intermediate users on advanced references unless severity/copy conservative and control-loss meaningful.
- **LOW:** "Do not re-validate user text" conflicts slightly with tests expecting non-enum values to omit safely.

### Suggestions
- Define asymmetry joint pairs and aggregation explicitly.
- Include the responsible joint/pair in scalar `posture_condition`.
- Add a task to verify or fetch Mode 3 previous-analysis angles.
- Make level-mismatch severity depend on rank gap and instability severity.
- Guard enum membership inside `safety_flags.py` even if upstream normalizes.

### Risk Assessment
**MEDIUM.** Concepts right; implementation details decide whether it generalizes or becomes noisy.

---

## Final Verdict (Codex)

Plans are strong enough to execute after tightening three things:
1. Make the AND-gate **local and time-aligned**, not just "any posture plus any instability."
2. Resolve Mode 3 reference/previous-angle plumbing before relying on D-03/D-04 there.
3. Treat D-05 as high-risk: add real elite keypoint regression, confidence gates, conservative no-flag on ambiguous geometry.

With those changes, the phase should meet SAFE-01 without undermining the project's core trust requirement.

---

## Consensus Summary

Only one independent external reviewer was available (Codex). Claude was skipped (this session is Claude Code — a self-review is not independent); Gemini, CodeRabbit, OpenCode, Qwen, and Cursor are not installed. The synthesis below is Codex's review distilled against the project's core value (정은지 no-false-positive), not a multi-reviewer consensus.

### Agreed Strengths
- Contract-first, deterministic, LLM-free SafetyFlag layer with a clean D-01 boundary (LLM `injuryRisk` untouched).
- MVP vertical-slice structure: 10-02 proves compute→persist→render end-to-end; later waves are backend-only auto-rendering additions.
- Correct domain instincts: reference-anchored asymmetry (no absolute L/R), Mode-1-only level mismatch, no 13-video curve-fit, scalar-only Firestore shape + scoped validator.

### Agreed Concerns (highest priority — feed into `--reviews` replan)
1. **[HIGH] AND-gate locality + temporal alignment.** The false-positive defense is only as strong as the control-loss predicate. Phase-level / non-time-aligned instability can still flag an elite intentional pose (a trunk posture in one window + unrelated wobble elsewhere). Fix: require control-loss to be **joint/region-local AND co-located in the same hold/phase window** as the posture condition. This is the single most important change — it is the mechanism that protects 정은지.
2. **[HIGH] D-05 cross-product fragility.** Sign convention is underspecified for inverted/spinning pole poses; `compute_safety_flags` may not actually receive the known-flexion reference frame the plan assumes; synthetic fixtures can pass while real elite keypoints misclassify. Fix: define the sagittal reference + `180 - included_angle` math exactly, add **real elite keypoint regression** (not just synthetic), gate on body-plane/keypoint confidence, and **fail conservative (no flag) on ambiguous geometry**.
3. **[HIGH/MEDIUM] Mode 3 reference/previous-angle plumbing.** Both D-03 (asymmetry) and D-04 (trunk, Mode 3) assume previous-analysis/reference angles are in scope; if absent they silently no-op. Fix: prove the plumbing or add an explicit task — otherwise the Mode-3 "내 자세가 이러면 위험" promise (belle's explicit requirement) quietly does nothing.
4. **[MEDIUM] Underspecified thresholds & joint selection.** Name the KISMAM threshold numerically with provenance; define asymmetry joint-pairs + aggregation (max vs average changes the FP profile); verify `unstable_body_parts` key names match `left_knee`/`right_elbow` exactly.
5. **[MEDIUM] Wave-0 RED/GREEN clarity.** elite no-FP should be GREEN against the empty stub immediately; only positive future-behavior tests should be `xfail(strict=True)`/skipped — otherwise later waves inherit ambiguous test state. Add an import-cycle check for the `SafetyFlag` re-export.

### Divergent Views
- **D-04 mode applicability:** Codex flags a tension between the plan (trunk = reference-anchored only) and the original D-04 wording (absolute signal, both modes). This was a deliberate research decision (RESEARCH A3: no defensible absolute lumbar cutoff for v1 → reference-anchored only). Not a contradiction, but the plan should state the resolution inline so it doesn't read as a silent scope reduction.

### Recommendation
Concern #1 (AND-gate locality + temporal alignment) and #2 (D-05 conservatism + real-keypoint regression) are the two that directly defend the project's core value and align with the plan-checker's W-1 (production no-FP needs real-data validation). Worth a targeted `/gsd-plan-phase 10 --reviews` pass before execution, or carry them as hardening constraints into execution + the verify-work pod eval.
