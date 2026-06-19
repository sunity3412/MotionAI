# Phase 20: v2 비전 점수 (Gemini 시각 거부권) - Research

**Researched:** 2026-06-19
**Domain:** LLM-vision-as-downward-veto over a deterministic rule-based pole-sports scorer (Python 3.12 Lambda + RunPod GPU `_process`, Gemini multimodal)
**Confidence:** HIGH (integration points verified against live code; Gemini SDK patterns verified against existing in-repo spike; threshold *numbers* intentionally undefined per D-02)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 ~ D-08 — non-negotiable)
- **D-01 — 거부권/캡, 하향 전용.** Vision deducts from the v1 deduction score; it can **never raise** it. kip-up major fault → ≤50; fault-free elite → v1 untouched (95~100 preserved). No weighted blend, no upward floor (both re-introduce the false-positive).
- **D-02 — Cap/deduction numbers must NOT be curve-fit to the 6 known pairs.** Only the *principle* (downward-only, severity grades) is locked; the actual threshold numbers come from a generalization-tested eval. No human score-label ground truth (vision outputs fault location/type/geometric estimate; threshold numeric labels OK).
- **D-03 — Scope = Mode1 AND Mode3.** Faults are reference-independent → vision sees both. Downward veto applies to Mode1 false-positives (kip-up) and Mode3 absolute scores.
- **D-04 — Trigger = ALWAYS call vision in the scoring path** for both modes. No "high score so skip" heuristic gating (that is exactly how the false-positive slipped through). Cost = external Gemini API (pod-free, belle-approved).
- **D-05 — Unit = dominant-fault pose (worst-pose).** The single worst fault pose dominates the overall (matches D-01 deduction). **Reject averaging across IPSF phases** — averaging is the exact Phase-19 dilution bug. Reuse existing `key_moments` (Phase 8/11 technique profile hold/peak) → zero new Gemini moment calls.
- **D-06 — Gemini recognizer determinism = temperature 0 + per-reference profile caching.** Same reference → same classification.
- **D-07 — Mode3 unknown-move gate = Gemini recognizer 3-branch.** (1) IPSF-listed (ipsfCode exists) → IPSF criteria eval; (2) no IPSF but 정은지-held → 정은지 comparison; (3) neither → validity gate.
- **D-08 — Branch-3 display = suppress confident score + "기준 없음".** No confident 97 for unheld moves. Expose scoring basis (IPSF/정은지/미보유) on the Mode3 first-analysis screen.

### Claude's Discretion
- D-08 exact UX strength (fully hide score vs grey-out vs banner) decided in plan/Figma — only the principle (no confident number) is locked. belle chose "suppress score + 기준 없음" direction.
- D-02/D-05 exact cap/deduction formula + worst-pose aggregation rule are derived in research/plan + eval (principle only here).

### Deferred Ideas (OUT OF SCOPE)
- **Upper-band discrimination** (within-20°=100 → good vs perfect): needs vision to RAISE score → conflicts with D-01 downward-only. Re-examine in a follow-up phase or a downward-safe variant.
- **climb not_pole gate:** correct-climb itself scores <25 vs ref-climb → ref-climb reference quality/camera-angle problem. Separate reference-fix track (re-register/re-shoot, Phase 14 seeder reuse). NOT in this phase's code scope.
- **Sensitivity set construction (unheld + above-cutoff):** generalization asset; needed as this phase's eval generalization gate, but the asset *collection* is a separate effort.

### Hard objectivity constraint (cross-cutting)
NO human-assigned score labels as ground truth, ever. Vision outputs fault location/type/geometric estimate only. Threshold numeric labels are OK.
</user_constraints>

<phase_requirements>
## Phase Requirements

Phase 20 has no pre-assigned req IDs. Derived from D-01~D-08, following the existing `SCORE-NN` / `TRUST-NN` taxonomy in `.planning/REQUIREMENTS.md` (§점수 신뢰도). **Recommended new IDs** (planner to confirm before locking into Traceability):

| ID (proposed) | Description | Source decision | Research support |
|----|-------------|------|------------------|
| **SCORE-08** | Gemini 시각 거부권이 채점 path 에 통합되어 v1 감점식 종합점수를 **하향만** 조정한다 (절대 못 올림). worst-pose 단위, Mode1+Mode3 둘 다, 항상 호출. | D-01/03/04/05 | `_apply_vision_veto` pre-wired slot at `app.py:1631`/call-site `app.py:2226`; downward-clamp pattern §"Vision-as-Downward-Veto" |
| **SCORE-09** | Gemini 시각 거부권의 cap/감점 수치가 6페어 curve-fit 이 아니라 generalization-tested eval(미보유+above-cutoff sensitivity 셋 포함)로 도출된다. | D-02 | Validation Architecture §; `backend/evals/phase18/` known-answer gate + sensitivity set (Deferred asset) |
| **TRUST-06** | Gemini 시각 거부권 호출이 결정론적이다 (temp 0 + reference-profile 캐싱 재사용). 같은 입력 = 같은 하향 cap. | D-06 | `technique_cache` SHA256+yaml_version pattern; determinism caveat §Pitfall 2 |
| **TRUST-07** | Mode3 미보유동작이 Gemini 인식기 3분기로 판정되어, 미보유(분기3) 시 confident 점수가 억제되고 "기준 없음" 근거가 노출된다. | D-07/08 | recognizer category enum already exists (`unregistered`/`low_confidence`); `is_reference_free_motion` at `assemble.py:130`; scoringBasis pipe at `app.py:1693` |
| **TRUST-08** | 위 거부권/게이트가 결과 화면에 투명하게 표시된다 (점수 억제 UX + scoringBasisLabel). | D-08 | `result.tsx:682` already renders `scoringBasisLabel`; contract `analysis.ts:267` 4-value enum |

**Note:** TRUST-05 (Phase 19, Complete) already shipped the *hook slot*. Phase 20 = filling the slot. SCORE-08 is the "fill" of TRUST-05.
</phase_requirements>

---

## Summary

Phase 19 left this phase a **fully pre-wired integration seam**. The v2 vision veto does not require any new plumbing in `_process` — it requires replacing the body of one already-existing function, `_apply_vision_veto(score_result, local_video_path, angles)` at `backend/functions/pipeline/app.py:1631`, called once at `app.py:2226` immediately after `assemble.build_result(...)` for BOTH modes (the call site is outside the `if mode == MODE_EXPERT / else` branch, so it already covers Mode1 and Mode3 — satisfying D-03/D-04 structurally). The v1 contract is `out is score_result` (same-object identity, zero mutation), asserted by `backend/tests/test_pipeline_mode3.py:246`. v2 deliberately transitions that contract to a downward-only mutation of `score_result["overallScore"]` (the function's own docstring at `app.py:1653-1655` names the exact key to read/write).

The score to veto is computed by `dimensions.overall_from_dimensions()` (`dimensions.py:384`) = **min-of-core(angle, line)** — Phase 19 already abandoned averaging for min-of-core so a single major dimension dominates. This is structurally aligned with D-01/D-05: a downward cap on the already-min overall is the natural composition. The kip-up false-positive (`fault_overall=100, success_overall=100, margin=0`, baseline JSON) survives because its fault is non-angular (timing/completion absorbed by the DTW band) and non-line — so min-of-core stays 100. Gemini vision is the orthogonal channel that sees what the geometry misses.

**Primary recommendation:** Implement v2 as a **severity→cap deterministic lookup** applied inside `_apply_vision_veto`: call a new objectivity-safe Gemini "fault severity at the dominant pose" adapter (a direct refactor of `backend/research/spikes/spike_vision_grounding_pair.py` into `backend/shared/python/sunity_shared/analysis/`), map its `severity` enum (`minor/moderate/major`) of the `primary_fault` to a cap ceiling, and clamp `result["overallScore"] = min(result["overallScore"], cap)`. The cap *table* is the only curve-fit-risk surface (D-02) — derive its numbers from the Phase-18 known-answer gate + a sensitivity set, never tune-to-fit the 6 pairs. Mode3 unknown-move (D-07/08) reuses the recognizer's existing `unregistered`/`low_confidence` categories and the already-wired `scoringBasis` enum + `result.tsx:682` display surface; the gap is routing branch-3 → score suppression, not new UI.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Vision fault-severity judgment | ML adapter boundary (`analysis/*.py`, Gemini) | — | External multimodal call; lazy-imported behind Protocol, like `coach_writer`/`gemini_technique_recognizer` |
| Downward cap application | Pipeline `_process` (`_apply_vision_veto`) | ML analysis core | Single code path shared by Lambda+RunPod (zero branching) — same as v1 hook |
| Severity→cap mapping | ML analysis core (pure fn) | — | Deterministic, unit-testable without AWS/network (mirror `dimensions`/`kismam` purity) |
| Worst-pose selection | ML analysis core (reuse `key_moments`) | technique profile | D-05 reuse — zero new moment calls |
| Mode3 3-branch gate | Pipeline `_mode3_comparison` + `assemble` (`is_reference_free_motion`, `_mode3_scoring_basis`) | recognizer category | Branch already exists; extend routing, not invent |
| Recognizer determinism cache | ML adapter (`technique_cache`) | Firestore | SHA256 video hash + yaml_version key already implemented |
| Score-basis / suppression display | App result screen (`result.tsx`) | contract (`analysis.ts`) | Display surface (`scoringBasisLabel`) already shipped Phase 19 |

---

## Standard Stack

### Core (all already in repo — no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | 2.8.0 (local) / pinned `>=1.0,<2.0` in Lambda/Pod reqs | Gemini multimodal (Files API video upload + `generate_content`) | Already the project's Gemini SDK (recognizer, coach, finding, spike). `[VERIFIED: pip show google-genai → 2.8.0; backend/runpod_inference/requirements.txt:41]` |
| `numpy` | `>=1.26,<3` | angles `(T,J)` matrix, worst-pose math | Analysis core backbone `[CITED: project CLAUDE.md Key Dependencies]` |
| stdlib `hashlib` | — | Video SHA256 for cache key | `compute_video_hash` already implemented `[VERIFIED: technique_cache.py:46]` |

**No new installs required.** This phase is pure code: a new analysis-core module + adapter + one function body swap + Mode3 routing + (optional) result-screen suppression copy.

### Supporting (reuse, do not rebuild)
| Asset | Location | Purpose | Reuse for v2 |
|-------|----------|---------|-------------|
| `spike_vision_grounding_pair.py` | `backend/research/spikes/` | Objectivity-safe Gemini fault-judgment prompt + `response_schema` (no score fields) + `_SCORE_PATTERN` leak guard + ASCII-path workaround | Direct template for the production fault-severity adapter |
| `GeminiTechniqueRecognizer` | `analysis/gemini_technique_recognizer.py` | recognize() w/ 3-case fallback + `category` enum (`recognized`/`api_failure`/`low_confidence`/`unregistered`) + cache wiring | Branch-3 (`unregistered`/`low_confidence`) drives Mode3 gate |
| `TechniqueCache` | `analysis/technique_cache.py` | SHA256 video hash + yaml_version stale-invalidation cache (Firestore-backed) | Determinism (D-06) — same reference → same classification |
| `key_moments` (hold/peak) | `TechniqueProfile.key_moments` (`technique.py:71`) | Phase 8/11 extracted hold timestamps | D-05 worst-pose unit (zero new moment calls) |
| Phase 18 eval | `backend/evals/phase18/` | Known-answer gate (`pairs.yaml` + `eval18_serial_baseline.json` + `assert_baseline.py`) + Pod runner `sweep_phase15.py --pair-sequential` | SCORE-09 regression + generalization gate |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| severity→cap lookup table | continuous regression severity→penalty | Continuous mapping is *more* curve-fit-prone (D-02 violation risk). Discrete `minor/moderate/major`→cap is auditable + generalizes. |
| Gemini Files API video upload | frame sampling at worst-pose timestamp → image input | Image-at-pose is cheaper/faster and matches D-05 "dominant pose" unit better than whole-video. Viable optimization; whole-video (spike pattern) is the safe default. **Open Question 1.** |
| temp 0 only | temp 0 + cache + (optional) self-consistency vote | LLM vision is not bit-deterministic even at temp 0 (see Pitfall 2). Cache is the real determinism guarantee for *re-runs of the same input*. |

**Installation:** none.

**Version verification:**
```bash
pip show google-genai        # → 2.8.0 [VERIFIED locally 2026-06-19]
grep -n google-genai backend/runpod_inference/requirements.txt backend/functions/*/requirements.txt
```

## Package Legitimacy Audit

> This phase installs **no new external packages**. All Gemini/numpy/hashlib dependencies are already present and exercised in production (recognizer, coach, finding adapters). slopcheck/registry verification is therefore N/A for new packages.

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| google-genai | PyPI | Already pinned `>=1.0,<2.0`, in production use since Phase 5 | No change — reuse |
| numpy | PyPI | Already pinned `>=1.26,<3` | No change — reuse |

**Packages removed due to slopcheck [SLOP] verdict:** none (no new packages).
**Packages flagged [SUS]:** none.

---

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────── _process (Lambda CPU-fallback OR RunPod GPU — ONE code path) ──────────────────────────┐
 S3 video ──► frame      │                                                                                                                    │
 (ObjectCreated)  extract│   recognize(angles, frames=local_video)  ──►  TechniqueProfile {motion_id, key_moments[hold/peak], joint_expects}  │
        │         + RTMW │            │  (Gemini recognizer, temp 0 + cache)        │                                                          │
        ▼         pose   │            ▼                                             ▼                                                          │
   SQS ─► pipeline ──────│   branch_info = lookup_motion_branch(motion_id)   D-07 3-branch routing (Mode3):                                    │
                         │   is_reference_free = is_reference_free_motion(...)   IPSF-listed / 정은지-held / neither→suppress                  │
                         │            │                                                                                                        │
                         │   ┌── mode1: DTW vs 정은지 ref ─► angle_dim ─► not_pole gate(<25) ─► dimension_scores ──┐                          │
                         │   └── mode3: abs_dims (+ prev delta) ──────────────────────────────────────────────────┤                          │
                         │                                                                                          ▼                          │
                         │                                            overall = overall_from_dimensions = MIN-OF-CORE(angle, line)  ← v1       │
                         │                                                                                          │                          │
                         │   result = assemble.build_result(..., overall, ...)                                     │                          │
                         │                                                                                          ▼                          │
   Gemini Vision  ◄──────│──────────────  _apply_vision_veto(result, local_video, angles)  ◄── D-01/03/04/05 SLOT (app.py:2226)                │
   (fault severity        │                     │  1. select worst-pose frame from key_moments (D-05, reuse — 0 new moment calls)             │
    at worst pose,        │                     │  2. Gemini fault-severity adapter (objectivity-safe schema, temp 0)                         │
    minor/mod/major)      │                     │  3. cap = SEVERITY_CAP[severity]   (deterministic table, D-02 generalize)                   │
                          │                     │  4. result["overallScore"] = min(result["overallScore"], cap)   ← DOWNWARD ONLY            │
                          │                     ▼                                                                                              │
                          │   complete_analysis(...) ─► Firestore users/{uid}/analyses/{id}.result                                            │
                          └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼  onSnapshot
                                            App result.tsx ── renders overallScore + scoringBasisLabel (suppression for branch-3)
```

### Recommended file layout (additions only)
```
backend/shared/python/sunity_shared/analysis/
├── vision_veto.py            # NEW — pure: SEVERITY_CAP table + apply_downward_cap() + worst-pose selection
├── gemini_vision_scorer.py   # NEW — Gemini fault-severity adapter (Protocol; refactor of spike); lazy-import
backend/functions/pipeline/app.py
└── _apply_vision_veto(...)   # SWAP body (line 1631) — call adapter + apply cap; keep graceful-boundary try/except
backend/evals/phase20/        # NEW — v2 gate: extends phase18 + sensitivity set manifest
```

### Pattern 1: Downward-only clamp (D-01 structural guarantee)
**What:** Vision can only lower. Encode it as `min()`, never a weighted blend.
**When:** Always, in `_apply_vision_veto`.
**Example (pure, unit-testable):**
```python
# Source: composition of dimensions.overall_from_dimensions (dimensions.py:384, min-of-core)
#         + _apply_vision_veto docstring (app.py:1653 — key is 'overallScore')
SEVERITY_CAP = {            # D-02: NUMBERS are placeholders — derive from eval, do NOT curve-fit the 6 pairs
    "minor":    100,        # no cap (fault-free elite path untouched → 95~100 preserved, D-01)
    "moderate":  None,      # TBD by eval
    "major":     None,      # TBD by eval (kip-up target ≤50 per belle spec — but value from generalization, not fit)
}

def apply_downward_cap(overall: int, severity: str | None) -> int:
    """v1 overall 을 vision severity 로 하향만. cap None/미지/minor → 불변 (raise 금지)."""
    cap = SEVERITY_CAP.get(severity)
    if cap is None:
        return overall
    return min(overall, cap)   # ← downward-only invariant. property test: result <= input ALWAYS.
```
**Invariant test (objectivity + D-01):** for all (overall, severity), `apply_downward_cap(overall, sev) <= overall`. This is the v2 analog of the v1 `out is score_result` test — it makes "vision never raises" a code-enforced property, not a hope.

### Pattern 2: Objectivity-safe Gemini schema (reuse spike)
**What:** Structured fault assessment, never a score. The spike's `build_schema()` (`spike_vision_grounding_pair.py:167`) has NO score field; `primary_fault` (string) + `severity` enum + `approx_*_deg` geometric estimates only. A regex leak-guard (`_SCORE_PATTERN`, line 233) flags any numeric score in the response.
**When:** The production adapter's response contract.
**Key change from spike:** `temperature=0.1` → `temperature=0.0` (D-06). Keep `response_mime_type="application/json"` + `response_schema` + `thinking_config(thinking_budget=-1)`.

### Pattern 3: Worst-pose unit, NOT phase average (D-05)
**What:** Score the single dominant-fault pose. Reuse `profile.key_moments` (hold/peak) — already on `TechniqueProfile` (`technique.py:71`), populated by the recognizer (`gemini_technique_recognizer.py:323`).
**Why:** Averaging across IPSF phases is the exact Phase-19 dilution bug (the reason `overall_from_dimensions` became min-of-core). The veto must compose with min-of-core, not re-average.

### Pattern 4: Mode3 3-branch via existing category enum (D-07/08)
**What:** The recognizer already returns `category ∈ {recognized, api_failure, low_confidence, unregistered}` and `is_reference_free_motion(branch_info)` (`assemble.py:130`) already distinguishes registered vs unheld. `_mode3_scoring_basis(is_first, is_reference_free)` (`app.py:1693`) already routes to `reference_free_absolute` etc. **Branch-3 (unheld) is `is_reference_free=True`** → emit a suppression flag + the existing `scoringBasisLabel` "기준 동작 없음 — 절대 자세 기준 평가". The display already exists at `result.tsx:682`.
**Gap to build:** (a) score *suppression* (not just label) for branch-3 — currently branch-3 still emits a confident absolute score; (b) ensure recognizer `unregistered`/`low_confidence` categories propagate to `is_reference_free` (today `is_reference_free` keys off `branch_info` from `motion_ipsf_map`, not recognizer category — verify these agree).

### Anti-Patterns to Avoid
- **Weighted blend `α·v1 + β·vision`:** can raise score → D-01 violation, false-positive recurrence. Forbidden.
- **Floor/`max()` that raises:** same. Only `min()`.
- **Gating the vision call on "score is high":** the false-positive WAS high-scoring → D-04 forbids skip-when-high.
- **Averaging severity across multiple poses:** dilution bug (D-05). Take dominant/worst.
- **Tuning `SEVERITY_CAP` until the 6 pairs pass:** D-02 violation. Numbers come from a generalization gate (sensitivity set), the 6 pairs are *known-answer regression*, not fit targets.
- **`raise` on unheld move (fail-closed):** memory `motion-routing-generalize-principle` + `is_reference_free_motion` design — unheld → safe absolute track + label, never raise.
- **Re-downloading video / re-running RTMW inside the adapter:** B4 hard-gate. Use the caller's `local_video_path` (already kept when `_gemini_vision_enabled()`; see `app.py:1833 keep_local_video=...`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gemini video upload + poll | custom Files API client | spike's `upload_and_wait()` + ASCII-path workaround (`spike_vision_grounding_pair.py:100,120`) | Korean filenames break HTTP headers; PROCESSING-poll already solved |
| Score-label leak detection | manual review | `_SCORE_PATTERN` regex guard (spike:233) + recognizer `_adapter_reject_guard` (`gemini_technique_recognizer.py:54`) | Objectivity hard-gate; double-defense already exists |
| Determinism cache | new cache | `TechniqueCache` SHA256+yaml_version (`technique_cache.py`) | Stale-invalidation + Firestore-backed already solved (B4 absolute-path fix) |
| Worst-pose timestamp | new Gemini moment call | `profile.key_moments` hold/peak | D-05 explicit: zero new moment calls |
| Mode3 score-basis routing | new branch logic | `_mode3_scoring_basis` + `is_reference_free_motion` + `scoringBasis` enum | Phase 19 already built the 4-value pipe + UI display |
| Eval harness | new sweep | `sweep_phase15.py --pair-sequential` + `assert_baseline.py` | Serial-safe (concurrency-unsafe pipeline) + known-answer gate already built |

**Key insight:** Phase 19 deliberately pre-built every seam this phase needs (the hook, the min-of-core, the scoring-basis enum, the UI label, the eval gate, the recognizer category enum, the determinism cache). Phase 20 is **composition + threshold derivation**, not new infrastructure. The single largest risk is the threshold table (D-02) — keep it in a pure module behind a generalization gate.

---

## Runtime State Inventory

> This is not a rename/refactor phase (it adds a scoring channel). Inventory limited to state that the new channel touches.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Firestore `users/{uid}/analyses/{id}.result.overallScore` — v2 will write a *lower* value than v1 for fault videos. No schema change (same `overallScore` key per `_apply_vision_veto` docstring `app.py:1654`). Optionally add an audit field (e.g. `visionVeto: {severity, capApplied}`) — requires 3-way contract lockstep (`analysis.ts` + `models.py` + `contract.md`). | Code edit (write path); contract change only if audit field added |
| Live service config | Gemini API key in SSM `/sunity/motion/gemini-api-key`; Pod env `GEMINI_API_KEY`, `RECOGNIZER_BACKEND=gemini`. **No new secret.** A new toggle env var (e.g. `GEMINI_VISION_VETO_ENABLED`) follows the `_VISION_ENV_DEFAULTS` pattern (`app.py:209`) — env-only flip, zero code change to enable. | Add env default to `_VISION_ENV_DEFAULTS`; document Pod/Lambda env |
| OS-registered state | None — verified: no Task Scheduler / launchd / pm2 in pipeline path. | None |
| Secrets/env vars | Reuse existing `GEMINI_API_KEY`. Local SSM lookup requires `--profile sunity-motion` (memory `gemini-key-local-ssm-profile`). | None new |
| Build artifacts | None — no package rename, no egg-info. New `.py` modules deploy via SAM layer + Pod git pull. | `sam build --use-container` on deploy (existing requirement) |

## Common Pitfalls

### Pitfall 1: Composing the veto with the WRONG aggregate (raising via averaging)
**What goes wrong:** Implementing the veto as "average vision penalty into dimension scores" re-introduces dilution — a clean angle dim averages away the vision fault.
**Why:** Phase 19 already proved averaging hides faults (that's why `overall_from_dimensions` is min-of-core).
**How to avoid:** Apply the cap to the *already-computed* `result["overallScore"]` (post-`build_result`), as a terminal `min()`. Never feed vision back into `dimension_scores` before aggregation.
**Warning sign:** Any code path where vision changes a value that is later passed through `overall_from_dimensions`.

### Pitfall 2: Assuming temp=0 makes Gemini vision bit-deterministic
**What goes wrong:** D-06 says "temp 0 + determinism." LLM vision is NOT guaranteed bit-identical across calls even at temp 0 (model-side nondeterminism; thinking models especially — see GitHub issues googleapis/python-genai#782, go-genai#196 where temp-0 zero-value is ignored). The Phase-19 spike used temp 0.1 precisely because it's a research anchor, not a determinism guarantee.
**Why:** The real determinism guarantee in D-06 is the **per-reference cache** (same reference → same stored classification), not the LLM temperature.
**How to avoid:** (a) For the *recognizer* (line dimension), rely on `TechniqueCache` keyed by video SHA256 — same input returns the *stored* result, fully deterministic. (b) For the *vision veto severity*, cache the severity verdict keyed by the same video hash (extend `TechniqueCache` or a sibling). (c) Set `temperature=0.0` explicitly (Pydantic config serializes the zero value, unlike the Go zero-value bug — but verify in eval). (d) The eval determinism gate (Validation §) must assert byte-identical re-runs *with cache warm*, and tolerate small variance *cache-cold* (document the boundary).
**Warning sign:** Eval determinism check fails cache-cold but passes cache-warm — expected; gate on cache-warm.

### Pitfall 3: Curve-fitting `SEVERITY_CAP` to the 6 pairs (D-02 violation)
**What goes wrong:** Tuning cap numbers until kip-up=50 and the 4 discriminating pairs stay split — overfits to 정은지/elite-low.
**Why:** 6 pairs are single-athlete, all-fault. They are a *known-answer regression*, not a fit target (memory `scoring-redesign-must-generalize-no-overfit`, `sensitivity-gate-not-just-elite-low`).
**How to avoid:** Derive caps from IPSF severity semantics + a **sensitivity set** (unheld move + above-cutoff videos that should stay high). Gate on BOTH directions: false-positive (fault must drop) AND false-negative (above-cutoff must NOT drop). The 6 pairs only *verify* (regression), never *calibrate*.
**Warning sign:** Cap numbers change every time a new pair is added — that's chasing, not generalizing.

### Pitfall 4: Mode3 branch-3 emits a confident score despite the label
**What goes wrong:** Today `is_reference_free=True` still produces a confident absolute `overallScore` + the "기준 없음" label — the label says no basis while the number looks authoritative (belle: confident 97 destroys trust).
**Why:** Phase 19 added the *label* (TRUST-03) but not score *suppression*.
**How to avoid:** Branch-3 must suppress the headline number (Claude's-discretion UX: hide/grey/banner, principle = no confident number). Wire it through the same `_apply_vision_veto`/assemble path so there is one suppression decision.
**Warning sign:** A reference-free Mode3 result shows a bold octagon score with "기준 없음" underneath.

### Pitfall 5: Graceful boundary swallowed — veto silently no-ops in production
**What goes wrong:** `_apply_vision_veto` wraps everything in `try/except` returning the input on any error (`app.py:1657`). A misconfigured key / Files API timeout → veto silently disabled → false-positive returns with NO signal.
**Why:** Graceful degradation is correct for availability but dangerous for a TRUST-critical gate.
**How to avoid:** On adapter failure, still graceful-return v1 score, but **log at WARNING + set an audit/warning field** so operators (and the eval) can detect "veto did not run." D-04 ("always called") needs observability, not just a try/except.
**Warning sign:** kip-up scores 100 in production but the eval (cache-warm, key present) shows ≤50 — the prod path silently skipped vision.

## Code Examples

### Worst-pose frame selection from key_moments (D-05, reuse)
```python
# Source: TechniqueProfile.key_moments (technique.py:71) populated at gemini_technique_recognizer.py:323
def worst_pose_timestamp(profile) -> float | None:
    """D-05 — dominant-fault pose. Reuse hold/peak key_moments (0 new Gemini calls).
    fps = 9.0 (frame_extractor target). Prefer 'hold' (completion pose); fall back to 'peak'."""
    kms = getattr(profile, "key_moments", None) or ()
    holds = [m for m in kms if getattr(m, "moment_key", "") == "hold"]
    peaks = [m for m in kms if getattr(m, "moment_key", "") == "peak"]
    chosen = holds or peaks or list(kms)
    return min((m.timestamp_seconds for m in chosen), default=None)
```

### Adapter call inside _apply_vision_veto (body swap)
```python
# Source: refactor of spike_vision_grounding_pair.py prompt+schema; key from app.py:1654 ('overallScore')
def _apply_vision_veto(score_result, local_video_path=None, angles=None, profile=None):
    try:
        if not _gemini_vision_veto_enabled() or local_video_path is None:
            return score_result                     # graceful + observable (Pitfall 5: log if expected-on)
        verdict = _vision_scorer.assess_fault_severity(   # objectivity-safe schema, temp 0, cache-keyed by video hash
            local_video_path, at_seconds=worst_pose_timestamp(profile)
        )
        capped = vision_veto.apply_downward_cap(score_result["overallScore"], verdict.severity)
        if capped < score_result["overallScore"]:
            score_result = {**score_result, "overallScore": capped,
                            "visionVeto": {"severity": verdict.severity, "capApplied": capped}}  # audit (contract lockstep)
        return score_result
    except Exception:
        log.exception("vision veto 실패 — v1 점수 통과 (graceful) + 운영 가시성 필요")
        return score_result
```
*(Note: `_apply_vision_veto` currently takes `(score_result, local_video_path, angles)` — adding `profile` requires updating the one call site at `app.py:2226`, which is in scope.)*

## State of the Art

| Old Approach (v1, Phase 19) | Current Approach (v2, Phase 20) | When | Impact |
|--------------|------------------|--------------|--------|
| `_apply_vision_veto` = same-object pass-through (`out is score_result`) | Downward-only cap mutation of `overallScore` | this phase | Closes kip-up false-positive without touching angle-channel discrimination |
| Vision used for recognizer + coach + finding only (NOT score path) | Vision injected into the score path as a veto | this phase | belle 2026-06-12 spec (HANDOFF Stage C) realized |
| Mode3 unheld → confident absolute score + "기준 없음" label only | unheld → score suppression + label | this phase | TRUST-03 label → TRUST-07/08 actual gate |
| `overall = mean(dimensions)` | `overall = min-of-core(angle, line)` | Phase 19 (already shipped) | Composes cleanly with a terminal vision `min()` cap |

**Deprecated/outdated:**
- Phase 19 v1 hook's "score must not change" contract is *intentionally* transitioned in v2 — the test at `test_pipeline_mode3.py:246` (`out is score_result`) must be updated to assert the downward-only property instead (`capped <= original`), not identity.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `temperature=0.0` in `google-genai` Pydantic config IS serialized (not dropped like the Go zero-value bug) | Pitfall 2 | If dropped, recognizer/veto less deterministic cache-cold — mitigated by cache; verify in eval determinism gate `[ASSUMED — verify: googleapis/python-genai#196 is Go-only]` |
| A2 | Recognizer `category` (`unregistered`/`low_confidence`) and `is_reference_free_motion(branch_info)` agree on "unheld" | Pattern 4 / Pitfall 4 | If they disagree, branch-3 routing may misfire. **Planner must verify** the two signals are reconciled (one keys off recognizer output, the other off `motion_ipsf_map.json`). `[ASSUMED]` |
| A3 | Frame-at-worst-pose image input is acceptable to Gemini vs whole-video | Alternatives / Open Q1 | Whole-video (spike pattern) is the safe fallback; frame-input is an unverified optimization. `[ASSUMED]` |
| A4 | Adding `profile` arg to `_apply_vision_veto` + updating the single call site (`app.py:2226`) is the full wiring change | Code Examples | If other callers exist, more sites. Verified: grep shows ONE call site + the def. `[VERIFIED: grep app.py:1631,2226]` |
| A5 | kip-up's fault is invisible to BOTH angle AND line (min-of-core stays 100) so only vision can catch it | Summary | baseline JSON shows kip-up `fault_overall=100` under min-of-core scorer → confirmed. `[VERIFIED: eval18_serial_baseline.json]` |

## Open Questions

1. **Vision input granularity: whole-video vs worst-pose frame.**
   - What we know: spike uploads whole video via Files API; D-05 unit is the dominant pose.
   - What's unclear: whether to upload whole video (proven, slower/costlier) or sample the frame at `worst_pose_timestamp` (cheaper, matches D-05, unproven).
   - Recommendation: Start whole-video (de-risked by spike) for the eval; spike frame-input as an optimization once caps are validated. Decide in plan.

2. **Audit field in contract (`visionVeto`)?**
   - What we know: writing a lower `overallScore` needs no schema change; an audit field improves observability (Pitfall 5) but triggers 3-way lockstep.
   - Recommendation: Add a minimal `visionVeto: { severity, capApplied }` optional field — worth the lockstep for TRUST observability. Confirm with planner.

3. **Severity granularity sufficient?** `minor/moderate/major` → 3 caps. Is `major` one bucket enough to hit ≤50 across diverse faults, or is a 4th (`severe`) needed? Derive from sensitivity set, not the 6 pairs.

4. **Determinism gate boundary (cache-cold variance).** How much cache-cold variance is acceptable before it's a defect? Recommendation: gate on cache-warm byte-identity; report cache-cold variance as informational.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `google-genai` | Gemini vision adapter + recognizer | ✓ (local) / pinned in reqs | 2.8.0 local | — |
| Gemini API key (SSM `/sunity/motion/gemini-api-key`) | all Gemini calls | ✓ (SSM; local needs `--profile sunity-motion`) | — | spike supports env `GEMINI_API_KEY` |
| RunPod RTMW GPU pod | **eval/implementation run** (real pose + DTW) | ✗ (currently DOWN per CONTEXT) | — | Research is pod-free; eval blocked until pod resumes |
| Gemini Files API | video upload | ✓ (external, pod-free) | — | frame-image input |
| `pytest` | unit tests (pure modules) | ✓ | `>=8,<9` | — |

**Missing dependencies with no fallback (blocking the EVAL only, not the plan/code):**
- RunPod RTMW GPU pod is DOWN. Code authoring, unit tests (pure `vision_veto.py` + adapter mock), and `assert_baseline.py` self-check are pod-free. The **generalization/regression eval run** (real scores through `sweep_phase15.py`) is blocked until the pod resumes. Plan should structure tasks so all pod-free work (pure modules, unit tests, adapter w/ mocked Gemini, contract changes, UX) completes first; the pod-gated eval is a clearly-marked terminal gate.

## Validation Architecture

> nyquist_validation is enabled (config.json `workflow.nyquist_validation: true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest `>=8,<9` (`backend/requirements-dev.txt`) |
| Config file | none committed (convention; tests under `backend/tests/`) |
| Quick run command | `PYTHONPATH=backend/shared/python pytest backend/tests/test_vision_veto.py -x` (new) |
| Full suite command | `PYTHONPATH=backend/shared/python pytest backend/tests/ -q` |
| App typecheck | `cd app && npm run typecheck` (only if contract `analysis.ts` changes for `visionVeto`) |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCORE-08 | downward-only invariant: `cap(overall, sev) <= overall` ∀ inputs | unit (property) | `pytest backend/tests/test_vision_veto.py::test_downward_only_property -x` | ❌ Wave 0 |
| SCORE-08 | minor/no-fault severity → score unchanged (95~100 preserved) | unit | `pytest backend/tests/test_vision_veto.py::test_minor_no_cap -x` | ❌ Wave 0 |
| SCORE-08 | `_apply_vision_veto` called for BOTH modes (call site outside mode branch) | unit (pipeline, Gemini mocked) | `pytest backend/tests/test_pipeline_mode3.py -k vision_veto -x` | ⚠️ exists (asserts v1 identity — must update to downward property) |
| SCORE-09 (a) | kip-up fault drops to ≤50 | eval (POD) | `sweep_phase15.py --mode mode1 --pair-sequential` → `assert_baseline.py` | ⚠️ runner exists; baseline must be re-snapshotted post-v2 |
| SCORE-09 (b) | 4 discriminating pairs do NOT regress (margin stays >0) | eval (POD) | same | ⚠️ |
| SCORE-09 (c) | 정은지 정타(correct) stays 95~100 | eval (POD) | same (success_overall column) | ⚠️ |
| SCORE-09 (e) | generalization: sensitivity set (unheld + above-cutoff) does NOT wrongly drop | eval (POD) | new `backend/evals/phase20/` manifest | ❌ Wave 0 (asset = Deferred — gate documents the requirement) |
| TRUST-06 | determinism: cache-warm re-run byte-identical | unit (cache mock) + eval (POD) | `pytest ...::test_severity_cache_deterministic` + repeat sweep | ❌ Wave 0 |
| TRUST-07 | Mode3 branch-3 (unheld) → `is_reference_free` + suppression flag | unit (pure `_mode3_*`) | `pytest backend/tests/test_pipeline_mode3.py -k reference_free -x` | ⚠️ partial (Phase 19 covers label) |
| TRUST-08 | result screen suppresses score + shows scoringBasisLabel for branch-3 | typecheck + manual UAT | `npm run typecheck`; manual (end-of-phase human verify) | ⚠️ label rendered (`result.tsx:682`); suppression new |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_vision_veto.py -x` (pod-free, < 5s)
- **Per wave merge:** full pod-free suite `pytest backend/tests/ -q` + `python backend/evals/phase18/assert_baseline.py` (snapshot self-consistency)
- **Phase gate (POD required):** `sweep_phase15.py --pair-sequential` SERIAL run → re-snapshot baseline → `assert_baseline.py` green with kip-up verdict flipped `known_false_positive`→`discriminate`, 4 pairs still discriminate, climb still `known_gate_blocked`, + sensitivity set passes.

### Concurrency constraint (hard)
`_process` is concurrency-unsafe (global singletons: recognizer, adapters, pipeline module — memory `pipeline-not-concurrency-safe-eval-serial`). ALL eval runs MUST be serial (`--pair-sequential`, one `done` before the next). Concurrent triggers = result cross-contamination = phantom regressions.

### Wave 0 Gaps
- [ ] `backend/shared/python/sunity_shared/analysis/vision_veto.py` — pure `SEVERITY_CAP` + `apply_downward_cap` + `worst_pose_timestamp`
- [ ] `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` — Gemini fault-severity adapter (Protocol; spike refactor; temp 0; cache)
- [ ] `backend/tests/test_vision_veto.py` — downward-only property test + minor-no-cap + cache determinism
- [ ] Update `backend/tests/test_pipeline_mode3.py:246` — `out is score_result` → downward-only property (contract transition)
- [ ] `backend/evals/phase20/` — sensitivity-set manifest + post-v2 baseline re-snapshot
- [ ] (if audit field) `analysis.ts` + `models.py` + `contract.md` 3-way lockstep for `visionVeto`

## Security Domain

> security_enforcement enabled (config), ASVS level 1, block_on high.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (internal pipeline; Gemini key auth) | Key in SSM, never hardcoded (CLAUDE.md) |
| V3 Session Management | no | — |
| V4 Access Control | no | pipeline runs server-side post-auth |
| V5 Input Validation | yes | Gemini response validated against `response_schema`; `_SCORE_PATTERN` + `_adapter_reject_guard` enforce no-score/no-coordinate output; `apply_downward_cap` clamps to `[0,100]` already via `build_result` |
| V6 Cryptography | no (uses stdlib hashlib SHA256 for cache key — not security-sensitive) | — |
| V9 / secrets | yes | `GEMINI_API_KEY` from SSM `/sunity/motion/gemini-api-key`; NEVER log key (spike never prints key); PII guard — `unregistered_hook` uses video_hash, not path (`gemini_technique_recognizer.py:27`) |

### Known Threat Patterns for {Gemini-vision + scoring pipeline}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt-injection via video metadata/filename | Tampering | Filename sanitized to ASCII temp copy (spike:100); prompt is fixed template, video is data not instruction |
| Objectivity breach (human/AI score label leaks as ground truth) | Tampering/Repudiation | `_SCORE_PATTERN` regex guard + `_enforce_no_coordinate_or_score` double-defense; schema has NO score field |
| Secret exposure in logs | Info Disclosure | Never log `GEMINI_API_KEY`; `RUNPOD_AUTH_TOKEN` redaction precedent in `sweep_phase15.py:558` |
| Vision call fails → silent gate bypass (false-positive returns) | Denial of Service / integrity | Graceful return BUT log WARNING + audit field (Pitfall 5) so bypass is observable |
| PII in unregistered-move collection | Info Disclosure | `unregistered_hook(keyword, video_hash)` — no video path/PII |

---

## Sources

### Primary (HIGH confidence — read this session)
- `backend/functions/pipeline/app.py` — `_apply_vision_veto` def (1631), call site (2226), `_mode3_scoring_basis` (1693), `_mode3_comparison` (1711), Mode1 not_pole gate (1992), `overall` (2002), `build_result` (2207), `_gemini_vision_enabled`/`_VISION_ENV_DEFAULTS` (209/220), `keep_local_video` (1833)
- `backend/shared/python/sunity_shared/analysis/assemble.py` — `is_reference_free_motion` (130), `lookup_motion_branch` (106), `build_mode1/3` (610/641), `build_result` (686), scoringBasis enum (582-607)
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — `overall_from_dimensions` min-of-core (384), `CORE_DIMENSIONS` (381), `absolute_dimension_scores` (365)
- `backend/shared/python/sunity_shared/analysis/technique.py` — `TechniqueProfile.key_moments` (71), `FallbackRecognizer` (83)
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — recognize() 3-case fallback + category enum, cache wiring (115-226), reject guard (54), key_moments build (256-324)
- `backend/shared/python/sunity_shared/analysis/technique_cache.py` — `compute_video_hash` SHA256 (46), yaml_version stale-invalidation (B4 absolute-path fix)
- `backend/research/spikes/spike_vision_grounding_pair.py` — objectivity-safe prompt (146), `build_schema` no-score (167), `_SCORE_PATTERN` (233), Files API upload (120), ASCII workaround (100), `MODEL=gemini-3.1-pro-preview` (57), temp 0.1 (263)
- `backend/evals/phase18/{pairs.yaml, baseline/eval18_serial_baseline.json, assert_baseline.py, README.md}` — known-answer gate; kip-up `fault=100/success=100/margin=0/known_false_positive`; climb `known_gate_blocked`; 4 discriminating pairs margins 28/21/41/42
- `backend/tests/test_pipeline_mode3.py:229-246` — v1 `out is score_result` identity test (to be transitioned)
- `app/src/app/analysis/result.tsx:682` — `scoringBasisLabel` already rendered; `app/src/types/analysis.ts:247-272` — scoringBasis 4-value enum
- `.planning/phases/20-v2-gemini/20-CONTEXT.md`, `.planning/HANDOFF-score-accuracy.md`, `.planning/REQUIREMENTS.md` (SCORE/TRUST taxonomy)
- `pip show google-genai` → 2.8.0; `backend/runpod_inference/requirements.txt:41` pin `>=1.0,<2.0`

### Secondary (MEDIUM — web, verified against repo usage)
- [googleapis/python-genai (GitHub)](https://github.com/googleapis/python-genai) — `GenerateContentConfig` temperature/response_schema/thinking_config support
- [google-genai · PyPI](https://pypi.org/project/google-genai/) — current SDK
- [Generating content | Gemini API](https://ai.google.dev/api/generate-content) — response_schema + thinking config

### Tertiary (LOW — flagged)
- [genai GenerateContentConfig ignores temperature 0.0 · go-genai#196](https://github.com/googleapis/go-genai/issues/196) — Go-specific zero-value bug; Python relevance unverified (A1) — informs Pitfall 2 caution
- [thinking budget unreliable with max_output_tokens · python-genai#782](https://github.com/googleapis/python-genai/issues/782) — thinking determinism caveat

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all deps in production, versions verified locally + in reqs
- Architecture / integration points: HIGH — every anchor read from live code this session (def + single call site verified by grep)
- Pitfalls: HIGH (composition/objectivity/curve-fit grounded in code + locked memories); MEDIUM on determinism (LLM-side nondeterminism is real but cache mitigates — A1)
- Threshold numbers: INTENTIONALLY ABSENT (D-02) — derivation method (generalization gate) specified, not the values

**Research date:** 2026-06-19
**Valid until:** ~2026-07-19 (stable — internal code anchors; re-verify `app.py` line numbers at plan time per CONTEXT instruction, as the file is large and actively edited)

## Sources

- [googleapis/python-genai](https://github.com/googleapis/python-genai)
- [google-genai · PyPI](https://pypi.org/project/google-genai/)
- [Generating content | Gemini API | Google AI for Developers](https://ai.google.dev/api/generate-content)
- [genai.GenerateContentConfig ignores temperature 0.0 · go-genai#196](https://github.com/googleapis/go-genai/issues/196)
- [thinking budget unreliable with max_output_tokens · python-genai#782](https://github.com/googleapis/python-genai/issues/782)

## RESEARCH COMPLETE
