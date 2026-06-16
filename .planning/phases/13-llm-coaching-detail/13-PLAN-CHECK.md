# Phase 13 — Plan Check (Pre-Execution Goal-Backward Verification)

**Phase:** 13 — 보완 운동 추천 + LLM 분기 카피 + coaching detail 완성
**Plans:** 13-A (Wave 1, autonomous) · 13-B (Wave 2, non-autonomous)
**Checked:** 2026-06-16
**Mode:** Goal-backward. Starting hypothesis: plans will NOT achieve the goal until evidence proves otherwise.

All file/line anchors cited by the plans were verified against the live codebase (PAIN_AREAS 8-tuple, ForceSourceSignal enum 6 values, force_signals lazy-loader pattern L229+, _validate_force_pattern_inference precedent, FORBIDDEN_PHRASES_PHASE9_REGEX precedent, CoachingTipDetailModal, result.tsx 코칭 팁 L854, build_dimension_explanation L63, _build_prompt L49). `fitness_norms_kspo.yaml` confirmed NOT imported anywhere in backend — D-02 honored.

---

## Coverage: ROADMAP criteria 1-8

| # | Criterion | Plan / Task | Verdict |
|---|-----------|-------------|---------|
| 1 | exercise library fixture exists + schema-valid | A T1 (corrective_exercises.json + schema gate test) | COVERED |
| 2 | result screen shows 3~5 matched exercises | A T2 (3~5 cap) + A T3 (section render) | COVERED |
| 3 | mapping uses motion + failure-cause + painAreas | A T2 (`map_exercises(force_pattern_inference, pain_areas, motion_id)`) | COVERED |
| 4 | "다른 운동 보기" library browse | A T3 (RecommendedExerciseModal) | COVERED |
| 5 | real Cerebras detail2 E2E in Firestore | B T4 (checkpoint:human-verify, Pod) — **not auto-claimed** | COVERED (honest) |
| 6 | ipsfCode branch1 vs branch2 copy split | B T2 (build_dimension_explanation `branch_info.copyBranch` branch via `lookup_motion_branch`; is_registered boolean superseded — see 13-REVIEW-FIXES.md) | COVERED |
| 7 | coach prompt cites correct IPSF angles | B T1 (angle fixture human-verify) + B T2/T3 (fixture + prompt inject) | COVERED |
| 8 | branch-2 avoids "세계 심사 기준" | B T2 (test_branch2_forbidden_phrase_gate) | COVERED |

All 8 criteria map to a task and a must_have truth.

**Requirements frontmatter:** PERS-03 present in both plans. `studio-term-3branch-system` present in Plan B `requirements`. ✓

---

## must_verify checklist

1. **Coverage / requirements frontmatter** — PASS. All 8 criteria + PERS-03 + studio-term-3branch present.
2. **2-plan split (D-05)** — PASS. Plan A = criteria 1-4 (autonomous, fixture unit tests); Plan B = criteria 5-8. Exact CONTEXT D-05 boundary.
3. **Locked-decision compliance:**
   - D-01/D-02 (국민체력100 v2, not consumed): PASS. Plan A objective has explicit negative-scope fence; no task reads `fitness_norms_kspo.yaml`; codebase grep confirms zero imports.
   - D-03 (mapping = Phase9 failure-cause + painAreas + motion_id only): PASS. `map_exercises` signature matches exactly; no fitness-norm input.
   - 3-way lockstep in one atomic commit: PASS. A T3 action explicitly states "단일 atomic commit 으로 3-way 계약" (analysis.ts + models.py + contract.md §4).
4. **Constraint gates present as tasks:**
   - D-05 grep-gate (painAreas never feeds scoring): PASS. A T2 → `test_exercise_map_no_scoring_leak.py` (AST/grep, precedent test_force_pattern_no_severity_use.py).
   - criteria-8 forbidden-phrase gate: PASS. B T2 → `test_branch2_forbidden_phrase_gate.py` (FORBIDDEN_PHRASES regex precedent).
   - criteria-7 registered-move angle human-verify (Open Q1): PASS. B T1 is `checkpoint:human-verify gate="blocking-human"` before angle fixture lock.
5. **Pod / criteria-5 honesty:** PASS. B T4 is `checkpoint:human-verify`; Plan B verification states "Pod 없이 PASS 주장 금지"; VALIDATION.md lists criteria 5 as Manual-Only.
6. **Task quality:** PASS (with one nit below). Every auto task has `<read_first>` + `<acceptance_criteria>` that are checkable; `<action>` is concrete prose with no fenced code blocks.
7. **`<threat_model>` block present in each plan:** PASS. Plan A = 4 STRIDE entries (T-13A-01..04); Plan B = 6 (T-13B-01..05 + SC). Covers prompt-injection via motion names (T-13B-02), SSM secret handling (T-13B-01), no-medical-claims (T-13A-03 / T-13B-04).
8. **Waves / dependencies:** PASS. Plan B `depends_on: ["13-A"]`, wave 2. Justified by shared file overlap — both edit `backend/functions/pipeline/app.py` and the phase13 test dir; sequential is correct.

---

## Findings by severity

### Blocking
None.

### Warning

**W-1 [task_completeness / nyquist] — VALIDATION.md `nyquist_compliant: false`, per-task map not expanded.**
13-VALIDATION.md frontmatter still has `nyquist_compliant: false` and `wave_0_complete: false`, and the Per-Task Verification Map has only two placeholder rows (`13-A-*`, `13-B-*`) rather than the per-task expansion the template demands. The PLANS themselves are nyquist-sound (Wave 0 = A T1 creates conftest + fixtures + first gate; every auto task carries an `<automated>` pytest command; no 3-consecutive-unverified window), so this is a stale-artifact bookkeeping gap, not a planning defect. Recommend the planner flip `nyquist_compliant: true` and expand the per-task rows so the execution contract matches the plans. Does not block execution.

**W-2 [scope / criteria-7 dependency ordering] — Plan B T1 checkpoint output feeds T2 fixture; if belle defers, T2 cannot lock content.**
B T1 (human-verify angle fixture) gates B T2's `registered_move_angles.json` content ("content = checkpoint 승인 값(임의 생성 금지)"). This is correct sequencing, but the plan should make explicit what happens if belle chooses "범위 표기로 완화" (RESEARCH A4 / Open Q1 resume-signal option) — T2 acceptance still says "Task 1 승인 값". As written it is resolvable (the resume-signal already enumerates the "range-only" fallback), so this is a clarity nit on T2 acceptance wording, not a gap. Recommend T2 acceptance criteria reference "Task 1 승인 값 또는 승인된 범위 표기" to stay consistent with the checkpoint's own options.

### Nit

**N-1 [key_links] — Plan A key_link pattern `recommendedExercises` is broad.**
The `result.tsx → result.recommendedExercises` key_link uses pattern `recommendedExercises`, which the frontend normalize() guard also matches. Both are intended wiring so it is fine, but a more specific pattern (e.g. the modal mount) would make the link check sharper. Cosmetic.

**N-2 [line anchors] — A few line anchors in Plan B (e.g. assemble L98-99, app.py L1819-1862/L1900-1950) are approximate.**
Spot-checked anchors (build_dimension_explanation L63, _build_prompt L49, coaching section L854) all resolved correctly; the remaining ranges are within the right regions. Execution reads `<read_first>` so drift is self-correcting. No action needed.

---

## Cross-cutting compliance

- **CLAUDE.md:** PASS. No emojis; theme-token-only UI mandated in A T3 (#FF4B33 / radius / spacing, no hardcoding); contract-first 3-way lockstep honored; secrets via SSM SecureString (B user_setup + T-13B-01); SAM/Parameter Store path respected.
- **Architectural Responsibility Map (RESEARCH §):** PASS. Exercise storage = committed backend fixture; mapping = pure backend fn; display = RN; Cerebras activation = Pod/Lambda env; ipsfCode branch = assemble (copy-only, not scoring). Every task lands in its assigned tier. Security-sensitive items (painAreas, Cerebras key, objectivity) correctly kept out of scoring/client tiers.
- **Deferred-ideas exclusion:** PASS. No task implements age/gender norms (D-01), SAFE full UI, growth graph, or branch-3 auto-collection. injuryRisk explicitly kept to one LLM line (T-13B-04 accept).
- **Cross-plan data contracts:** PASS. Plan B's pipeline edits mirror Plan A's `recommended_exercises` wiring without conflicting transforms; both consume `bodyProfile`/`motion_id` read-only for non-scoring paths.
- **Research resolution:** PASS. RESEARCH Open Q1 (registered-move angles) is explicitly converted into B T1 blocking checkpoint; Open Q2 (which 3~5 동작군) resolved by defect-keyed (motion-agnostic) coverage — 5 defect groups cover all moves.

---

## Verdict

Both plans deliver all 8 ROADMAP success criteria, honor every locked decision (D-01..D-06), carry the required constraint gates as real tasks (D-05 no-scoring-leak grep, criteria-8 forbidden-phrase, criteria-7 angle human-verify, criteria-5 Pod checkpoint), include `<threat_model>` blocks, and have a sound wave/dependency graph. The only issues are a stale VALIDATION.md flag (W-1) and minor wording/clarity items — none block execution.

## PLAN CHECK COMPLETE — VERDICT: PASS
