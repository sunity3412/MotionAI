---
phase: 23
reviewers: [codex]
reviewed_at: 2026-06-22
plans_reviewed: [23-01-PLAN.md, 23-02-PLAN.md, 23-03-PLAN.md]
note: claude skipped (executing runtime — independence); gemini/opencode/qwen/cursor/coderabbit not installed. Single external reviewer (codex).
---

# Cross-AI Plan Review — Phase 23

## Codex Review

**Overall — Risk: HIGH.** Direction is sound (still-frame granularity is the right lever; score-free/downward-cap architecture preserved; `low_alignment_confidence` instead of fabrication), but **not execution-ready as written**. Biggest risks: false-positive inflation from part/window union, under-specified DTW confidence, missing production data plumbing, and success criteria that say "display/coaching" while plans mostly only store backend audit fields.

**Strengths:** correct lever (input granularity, not prompt tweak); VisionVerdict stays score-free + cap downward-only; explicit `low_alignment_confidence`; tests for cache separation/status lockstep/Pod eval.

**Concerns (severity-tagged):**

- **[HIGH] Precision not protected.** Per-part × frame union can preserve a one-off hallucinated fault unless there is support/consensus gating. (Direct threat to the project's false-positive history / elite-low.)
- **[HIGH] Mode 3 in the phase goal but plans keep it held/ignored.** Either plan Mode 3 quantification or formally revise scope.
- **[HIGH] "Displayed" quantification/root-cause not actually planned in app UI or coach-report rendering.** SC#4/#5 say displayed/coaching; plans store backend audit fields only.
- **[HIGH] 23-01 API/data plumbing under-specified.** `_apply_vision_veto` (app.py:1662) does not currently receive `reference_dtw_match`/ref angles/frame reports; `assess_fault_severity` (gemini_vision_scorer.py:546) still has a video-path API. Signature/callsite change not made explicit.
- **[HIGH] "Side-by-side" is ambiguous.** Two separate Gemini image handles may not replicate a true side-by-side composite. Specify which (the spike fed frames; the comparison path uses separate ref+student handles).
- **[HIGH] `MotionMatch.distance` is GLOBAL.** It does not prove the LOCAL worst-pose frame is correctly aligned. Need local checks: path density near the selected frame, ref-frame availability, keypoint visibility/blur.
- **[HIGH] Body-relative notch under-specified + geometry/VLM conflation.** "칸/층" needs pole/floor/hip-line baseline + per-frame reach geometry computed DETERMINISTICALLY from keypoints — not Gemini inventing notch values. And the prompt's **"100%/percent" language conflicts with the `_SCORE_PATTERN` score-leak guard** → valid descriptive output could be discarded. Use "reference = 3칸" not "100%".
- **[MEDIUM] `MAX_VETO_CALLS` alone** doesn't bound uploads, wall time, retries, File API cleanup, or live-path UX. Cache key should include selector version/frame indices/top-K/window policy, not just `input_granularity`.
- **[MEDIUM] `worst_pose_timestamp` ≠ worst upper-body fault frame.** Selector may pick the wrong frame for upper-body faults.
- **[MEDIUM] 23-03 eval may bypass the production path** (call `assess_fault_severity` directly, skipping frame selection/DTW gating/cache/`_apply_vision_veto`); comparing to an OLD whole-video baseline JSON is not apples-to-apples if model/prompt/cache changed; 1 kip-up + 1 clean case is too thin to claim false-positive non-increase; determinism can be falsely proven by cache hits (need cold-cache repeats); no latency/cost gate; JSON should have machine-checkable pass/fail fields.

**Suggestions:** precision/support gate for unioned defects; explicit still-pair API (image paths, frame metadata, part scopes, selector version); local DTW confidence checks; compute notches deterministically from keypoints/pole-axis/baseline (avoid percent notation); add result-screen + coach-section rendering tasks; `source: geometry|vision_hypothesis` provenance fields; add Mode 3 task or formally defer; eval telemetry (`call_count`/`upload_count`/`duration_ms`/cache hit-miss/cost) + run both direct-adapter AND full-production-path tests + re-run whole-video baseline with the same model + bigger case matrix (elite clean / imperfect clean / occluded / tempo-shifted / spinning / known-fault) + cold vs warm determinism.

---

## Consensus Summary

Single external reviewer (codex) — gemini/others not installed, claude is the executing runtime. No cross-reviewer consensus available; treat below as codex's prioritized findings.

### Agreed Strengths
- Input-granularity is the correct lever (matches spike); objectivity architecture (score-free + downward-cap + no-fabrication) preserved.

### Top Concerns (priority order)
1. **[HIGH] Precision/false-positive protection** — union needs a support/consensus gate so a single-frame hallucination can't survive. (Aligns with the project's #1 value.)
2. **[HIGH] Display/coaching gap** — SC#4 "표시"/SC#5 coaching are not actually built (backend-only). Decide: build app/coach rendering tasks OR revise SC scope.
3. **[HIGH] Mode 3 coverage** — in the goal but unplanned. Add a task or formally defer (note: Mode 3 dual-2-video was Backlog B-15a; may belong there).
4. **[HIGH] Notch geometry vs VLM + percent/score-leak** — compute notches deterministically (pole/floor/hip baseline), drop "100%/percent" wording (collides with `_SCORE_PATTERN`).
5. **[HIGH] 23-01 plumbing + global-vs-local DTW confidence** — make the `_apply_vision_veto`/`assess_fault_severity` signature change explicit; add LOCAL alignment confidence, not just global `MotionMatch.distance`.
6. **[HIGH] 23-03 must test the real production path** (not just re-prove the spike), re-baseline with same model, widen the case matrix, separate cold/warm determinism, add cost/latency gates + machine-checkable pass/fail.

### Divergent Views
- N/A (single reviewer).

---

*To incorporate: `/gsd-plan-phase 23 --reviews` (replan folding this feedback), or convergence loop until no HIGH remains.*
