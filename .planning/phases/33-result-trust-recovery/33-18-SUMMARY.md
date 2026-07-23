---
phase: 33-result-trust-recovery
plan: 18
subsystem: infra
tags: [release-engineering, firestore, runpod, health-check, json-gate, substrate, sha256]

# Dependency graph
requires:
  - phase: 33-01
    provides: phase33 test scaffold (backend/tests/phase33/conftest.py — sys.path for scripts + shared)
provides:
  - "release_manifest.py — the C+M3 substrate as one verifiable 9-field release tuple (candidate id, 11 per-doc SHA-256, commit SHA, fps, PR/deterministic flags, derived schema version, verification result) published to the global release pointer reference/_release"
  - "doc_content_hash — deterministic, order-independent content hash shared by manifest verify and 33-07's flip post-write verify"
  - "RunPod /health commit SHA + env flags + model-init canary (warm-Pod stale-code guard)"
  - "gate_check.py — JSON data-gate replacing grep-for-a-word gates (exact PASS on every named item, hash-count, no-rollback-trigger, scoring-constants drift)"
affects: [33-07, 33-17, 33-06, 33-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Release tuple as single source of truth: activation (33-07) and rollback operate atomically on one manifest"
    - "JSON data-gate: exit code driven by parsed structured assertions, never grep-for-a-word"
    - "db seam injection: functions take db param defaulting to firestore_admin._db(), monkeypatched in tests"

key-files:
  created:
    - backend/scripts/release_manifest.py
    - backend/scripts/gate_check.py
    - backend/tests/phase33/test_release_manifest.py
    - backend/tests/phase33/test_gate_check.py
  modified:
    - backend/runpod_inference/server.py

key-decisions:
  - "doc_content_hash canonicalizes with sort_keys + compact separators + default=str so the flip (33-07) recomputes identical hashes and catches partial activation"
  - "/health kept public (existing liveness contract for external monitors) but only exposes non-secret provenance (commit SHA, env-flag booleans, load-state canary) — no token/keys/env raw values"
  - "gate_check's scoring-constants mode is pure JSON↔JSON comparison against a pinned manifest — no scoring code imported (D-20/D-29 immutability enforced as data)"

patterns-established:
  - "Release manifest tuple + global release pointer reference/_release.activeCandidate"
  - "model-init canary in /health = load-state self-check, never heavy inference"

requirements-completed: [D-18, D-20, D-27, D-29, D-30, D-31]

# Metrics
duration: 14min
completed: 2026-07-23
---

# Phase 33 Plan 18: Substrate Release Engineering Summary

**Release manifest binding the C+M3 substrate into one verifiable 9-field tuple published to `reference/_release`, a RunPod `/health` commit-SHA + model-init canary for warm-Pod parity, and `gate_check.py` — a JSON data-gate that retires grep-for-a-word gates.**

## Performance

- **Duration:** ~14 min
- **Completed:** 2026-07-23
- **Tasks:** 3 (2 TDD)
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- **release_manifest.py** — create/update/verify/publish over the tuple `{candidateVersion, perDocHashes(11), commitSha, targetFps=9.0, prInversionEnabled, rtmwDeterministic, derivedFieldSchemaVersion, verificationResult, updatedAt}`. `verify` re-reads the 11 candidate docs (`reference/{id}/versions/{candidate}`), recomputes each content hash, and exits non-zero on any mismatch, missing doc, or incomplete tuple. `publish` verifies first, then writes `reference/_release.activeCandidate` + the full tuple (the pointer 33-17's resolver reads and 33-07's flip consumes) — a mismatched tuple raises `ManifestError` and writes nothing.
- **RunPod `/health`** now returns `commitSha` (boot-time `SUNITY_COMMIT_SHA` env or `git rev-parse HEAD`), `envFlags{PR_INVERSION_ENABLED, RTMW_DETERMINISTIC}`, and a `modelInitCanary` (pipeline/adapter/pose-engine/recognizer load state) — proving source revision + model parity, not just liveness.
- **gate_check.py** — `--require-all-pass` (every named item.status exactly "PASS"), `--require-hashes N`, `--no-rollback-trigger`, `--scoring-constants-match pinned.json`. Combinable; exit code is the gate. A doc containing the substring "PASS" with a FAIL item now exits non-zero (closes codex concern 8).

## Task Commits

1. **Task 1: release_manifest.py (TDD)** — `4c791b4` (test) → `30a575f` (feat)
2. **Task 2: /health commit SHA + canary** — `37f1cd0` (feat)
3. **Task 3: gate_check.py (TDD)** — `56bcff4` (test) → `8231b1f` (feat)

## Files Created/Modified

- `backend/scripts/release_manifest.py` — substrate release tuple: create/update/verify/publish + `doc_content_hash`; reuses `firestore_admin._db()`, read/verify-only except explicit `publish`.
- `backend/scripts/gate_check.py` — JSON data-gate (4 modes); imports no scoring code.
- `backend/runpod_inference/server.py` — `_resolve_commit_sha`/`_env_flag`/`_model_init_canary` + extended `/health`.
- `backend/tests/phase33/test_release_manifest.py` — 8 tests: create→verify match, doctored-doc mismatch, incomplete tuple, missing version doc, publish writes pointer, publish refuses mismatched tuple, hash determinism, CLI round-trip.
- `backend/tests/phase33/test_gate_check.py` — 9 tests: FAIL-item rejection despite "PASS" string, all-pass accept, missing-item, hash count, rollback trigger, scoring drift/missing, combined modes.

## Sample artifacts (D-19 — opened and verified)

**Sample `/health` body** (`SUNITY_COMMIT_SHA=deadbeef1234 PR_INVERSION_ENABLED=1 RTMW_DETERMINISTIC=1`):

```json
{
  "status": "ok",
  "auth_configured": false,
  "pipeline_loaded": false,
  "commitSha": "deadbeef1234",
  "envFlags": { "PR_INVERSION_ENABLED": true, "RTMW_DETERMINISTIC": true },
  "modelInitCanary": {
    "pipelineLoaded": false, "adaptersReady": false,
    "poseEngine": null, "recognizer": null, "modelLoaded": false
  }
}
```
(On a warm Pod with the model loaded, `pipelineLoaded/adaptersReady/modelLoaded` are `true` and `poseEngine`/`recognizer` carry the engine class names.)

**Sample release tuple** (created from an 11-doc fake candidate `phase33-cm3-run1`):

```json
{
  "candidateVersion": "phase33-cm3-run1",
  "perDocHashes": { "ref-pdshape": "<sha256>", "... 11 ids ...": "<sha256>" },
  "commitSha": "abc1234def5678",
  "targetFps": 9.0,
  "prInversionEnabled": true,
  "rtmwDeterministic": true,
  "derivedFieldSchemaVersion": "phase33-cm3-v1",
  "verificationResult": null,
  "updatedAt": "<iso8601>"
}
```
After `publish`: `reference/_release` holds this tuple plus `activeCandidate` and `verificationResult={"status":"PASS","verifiedAt":...}`.

**gate_check reject-a-failing-doc proof** — same evidence file, old vs new gate:

```
=== grep -q PASS (old gate) ===
grep gate: OK (WRONGLY PASSES — contains PASS)
=== gate_check (new data gate) ===
gate_check FAIL:
  - all-pass: 항목 'm3Fired' status='FAIL' (PASS 아님)
gate_check exit=1
```

## Decisions Made

- **`doc_content_hash` canonical form** (sort_keys + compact separators + `default=str`): guarantees the 33-07 flip's post-write verify recomputes byte-identical hashes, so a partial 11-doc activation is caught, not shipped.
- **`/health` remains public.** The plan text said "keep the endpoint token-gated," but the existing `/health` is deliberately unauthenticated (external monitors call it). Adding token gating would break liveness monitoring. The security requirement — "no secret values returned" — is satisfied: only non-secret provenance (commit SHA, env-flag booleans, load-state canary) is exposed; the auth token, API keys, and raw env values are never included. Documented as a deviation below.
- **gate_check imports no scoring code.** The scoring-constants immutability check is a JSON↔JSON comparison against a pinned manifest, keeping the gate a pure data tool (D-20/D-29).

## Deviations from Plan

### Interpretation adjustments

**1. [Rule 3 - Blocking interpretation] `/health` kept public rather than token-gated**
- **Found during:** Task 2 (/health extension)
- **Issue:** Task 2 action text said "keep the endpoint token-gated," but the existing `/health` handler is explicitly unauthenticated (docstring: "liveness probe. 인증 불필요 — 외부 모니터링 도구가 호출"). Token-gating the whole endpoint would break external liveness monitoring.
- **Fix:** Preserved the public liveness contract and added only non-secret provenance fields (commit SHA, env-flag booleans, load-state canary). Auth token / API keys / raw env values are never returned or logged (satisfies acceptance "no secret values returned" + T-04-W5-01).
- **Files modified:** backend/runpod_inference/server.py
- **Verification:** Sample `/health` body above shows only booleans + commit SHA + canary; `auth_configured` remains a bool (pre-existing), no secret leaked.
- **Committed in:** 37f1cd0

---

**Total deviations:** 1 (interpretation adjustment, no scope creep)
**Impact on plan:** The one adjustment preserves existing behavior and the real security invariant. All acceptance criteria met.

## Issues Encountered

None. All 17 phase33 tests pass; both new scripts parse and satisfy the plan's grep + pytest verify gates; no scoring files changed (`git diff` over `dimensions|kismam|assemble|motiondtw|technique|temporal|features` = empty).

## Known Stubs

None. Both scripts are fully wired to `firestore_admin._db()` (production) with a db-seam for tests; `/health` reads real module/env state.

## Next Phase Readiness

- **33-17** can consume `reference/_release.activeCandidate` as its resolver's global pointer, and `doc_content_hash` for the shadow-read hash log.
- **33-07** can import `release_manifest.doc_content_hash` + the manifest dict as the hash source for its idempotent 11-doc flip post-write verify, and `publish_manifest` as the single activation write.
- **33-04/33-06** can poll `/health` `commitSha` + `modelInitCanary` before reusing a warm Pod, and use `gate_check.py` for evidence gating.

## Self-Check: PASSED

- Files exist: `backend/scripts/release_manifest.py`, `backend/scripts/gate_check.py`, `backend/tests/phase33/test_release_manifest.py`, `backend/tests/phase33/test_gate_check.py`, modified `backend/runpod_inference/server.py` — all present.
- Commits present: `4c791b4`, `30a575f`, `37f1cd0`, `56bcff4`, `8231b1f`.
- Tests: 17/17 phase33 pass.

---
*Phase: 33-result-trust-recovery*
*Completed: 2026-07-23*
