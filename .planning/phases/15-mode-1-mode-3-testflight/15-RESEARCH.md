# Phase 15: Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight - Research

**Researched:** 2026-06-17
**Domain:** End-to-end validation + delivery (no new features). RunPod GPU E2E orchestration, Firestore live-state, dual-LLM coach, EAS/TestFlight delivery.
**Confidence:** HIGH (almost everything verified against live codebase + git history; Pod liveness verified empirically)

## Summary

Phase 15 is a **validation + delivery** phase, not a build phase. Every capability it touches — Mode 1 comparison, Mode 3 session-delta, the false-positive (위양성) axis gate, the dual-LLM coach, and TestFlight delivery — is **already implemented in code** (verified file:line below). The planner's job is to sequence **operational tasks** (Pod restart, Lambda env sync, real-video upload + sweep, EAS preview build) and **assertion tasks** (compare new E2E output to the locked baseline) — not to write new features.

The single highest-risk operational fact: **the RunPod Pod is dead.** `https://xbdkj1g2ylnfwi-8000.proxy.runpod.net/health` returns HTTP 404 (a live pod returns 200 with `pipeline_loaded:true`). Real analysis is therefore **entirely down** right now. A new Pod must be created, RTMW/YOLOX/Gemini env restored, uvicorn started, and the `RUNPOD_ANALYZE_URL` Lambda env re-synced before any E2E can run. A second operational gotcha: the active AWS CLI credential is the `sunity-api` user, which is **not authorized for Lambda** (`AccessDeniedException` on `lambda:ListFunctions`); the `sunity-motion` credentials are required for the env-sync step (memory [[aws-keys-and-bucket]]).

The letterSpacing SIGABRT (DELIV-01's hard blocker) is **already fixed in source** (`app/src/theme/typography.ts:15` `track = () => 0`). The remaining DELIV-01 work is: (1) close the `eas.json` **preview-profile env gap** (preview has no `env` block, production does — a preview build would ship with no Firebase/API config), (2) run an EAS preview build, (3) verify on real device, (4) hand belle the human-only real-device guest completion step (D-09).

**Primary recommendation:** Plan Phase 15 as roughly four operational waves — (W1) Pod bring-up + Lambda env sync + dual-coach env verification; (W2) Mode 1 real E2E across the 11 references + 위양성 gate assert against the 08.1 baseline; (W3) Mode 3 success/fail pair E2E (delta + 위양성 in one set); (W4) eas.json preview env fix → preview build → device verify → belle handoff. Use the existing `sweep_phase8_1.py` as the canonical real-E2E driver pattern; do not write a new analysis path.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Real analysis (NLF/RTMW pose → score) | RunPod GPU Pod | Lambda pipeline (delegates) | CUDA required; Lambda `_process` is CPU-NaN fallback only. `runpod_inference/server.py` reuses `_process` (분기 0). |
| Mode 1 comparison (정은지 reference) | API/Backend (pipeline `_process`) | Firestore (reference docs) | Comparison math + reference fetch is backend; app only selects `referenceMotionId`. |
| Mode 3 session delta | API/Backend (`assemble.build_mode3`) | Firestore (`get_previous_analysis`) | Delta computed backend-side; app renders `deltaFromPrevious`. |
| 위양성 (axis severity) gate | API/Backend (`force_signals.py` tilt) | — | Pure tilt-only algorithm; threshold yaml lazy-loaded. |
| Dual-LLM coach | API/Backend (pipeline) | Gemini API + Cerebras API | Both writers called in pipeline; cross-fill assembled backend-side. |
| Live status display | App (Firestore `onSnapshot`) | Firestore | App subscribes; never polls. |
| TestFlight delivery | EAS Build/Submit (cloud) | App (RN release build) | Native release crash surface; SIGABRT only reproduces in release build. |
| Result video playback | App (`expo-video`) + S3 presigned | `POST /playback-url` Lambda | 7-day presigned TTL; refresh Lambda exists. |

## Standard Stack

This phase introduces **no new packages**. The stack is locked (CLAUDE.md §3) and already installed. Operational tooling only.

### Core (already present, verified)
| Tool | Where | Purpose |
|------|-------|---------|
| `backend/scripts/sweep_phase8_1.py` | repo | Canonical real-E2E driver: S3 copy → Firestore analysis doc → `pipeline._process()` direct call → cleanup. `[VERIFIED: file read]` |
| `backend/functions/pipeline/app.py::_process` | repo | Single analysis path (Lambda + Pod share it). `[VERIFIED: file read]` |
| `backend/runpod_inference/server.py` | repo | Pod `/analyze` + `/health`; auth header `X-RunPod-Token`. `[VERIFIED: file read]` |
| `.claude/scripts/setup_pod_full.sh` | repo | Pod bootstrap (RTMW/YOLOX HF mirror, Firebase SA, env). `[VERIFIED: file exists]` |
| `app/scripts/seed-reference-motions.mjs` | repo | S3 presign + Firestore reference seeding (reusable for video upload). `[CITED: CONTEXT.md §code_context]` |
| EAS CLI ≥ 19.0.0 | `app/eas.json` | Build + submit (ASC API key auto-submit). `[VERIFIED: file read]` |
| AWS SAM CLI | `backend/samconfig.toml` | Stack `sunity-motion-pilot`, region `ap-northeast-2`. `[CITED: PROJECT.md]` |

**No `npm install` / `pip install` step.** Any plan task proposing a new dependency is out of scope.

## Package Legitimacy Audit

Not applicable — Phase 15 installs **no external packages**. It is validation + delivery using the existing locked stack. (Package Legitimacy Gate skipped: zero new packages.)

## Architecture Patterns

### System Architecture Diagram (real E2E data flow)

```
[belle local videos]                    [App on device (TestFlight)]
  6 fail + 7 success .mp4                  anon Firebase sign-in
        |                                        |
        | (Claude uploads via S3 PUT)            | pick video → POST /upload-url
        v                                        v
   S3 sunity-motion-pilot-videos  <----  presigned PUT (Content-Type set!)
        |                                        |
        | S3 ObjectCreated                       | app PUTs bytes directly to S3
        v                                        |
      SQS AnalysisQueue                          |
        |                                        |
        v                                        |
  pipeline Lambda  --RUNPOD_ANALYZE_URL-->  RunPod Pod /analyze (GPU)
   (delegates, no GPU)                       _process(): RTMW pose → DTW →
        |                                     KISMAM score → axis tilt →
        |                                     Gemini recognizer (line dim) →
        |                                     dual coach (Gemini+Cerebras)
        v                                        |
   Firestore users/{uid}/analyses/{id}  <-- complete_analysis() writes result
        |
        | onSnapshot (app subscribes, no poll)
        v
   result.tsx renders: dimensionScores, deltaFromPrevious (mode3),
   axis severity, dual-coach sections, video playback (presigned GET)
```

**For the sweep path** (Claude-driven, bypasses app/SQS): `sweep_phase8_1.py` copies S3 → writes analysis doc → calls `pipeline._process()` **directly on the Pod** (so it requires the Pod's GPU env, run over SSH). This is the proven pattern for the 위양성 sweep.

### Pattern 1: Real-E2E sweep (08.1 proven)
**What:** Drive `_process` over N videos directly on the Pod, write evidence to Firestore.
**When:** 위양성 gate re-measurement (D-01/D-03), Mode 1 11-reference run.
**Example:**
```bash
# Source: backend/scripts/sweep_phase8_1.py + 08.1-SWEEP-EVIDENCE.md §5
ssh -i ~/.ssh/id_ed25519 <pod> \
  "cd /workspace/SunityMotion && source /workspace/phase8_env.sh && \
   PYTHONPATH=backend/shared/python:. python3 backend/scripts/sweep_phase8_1.py \
     --sweep-uid sweep_phase15_<epoch_ms>"
```
Note: `sweep_phase8_1.py` copies from `reference/{name}.mp4` S3 keys and uses `MODE_SELF`. For Phase 15's *new* success/fail videos (not yet in S3 as `reference/`), a thin variant or pre-upload step is needed (Claude's discretion per CONTEXT D-05/discretion). The driver logic (S3 copy → doc → `_process` → cleanup) is reusable as-is.

### Pattern 2: Mode 3 delta (already implemented)
**What:** Same-user, same-mode previous analysis fetched, per-dimension absolute delta computed.
**Where:** `assemble.build_mode3()` (`assemble.py:539-562`) computes `deltaFromPrevious[dim] = cur - prev`; pipeline wires it at `app.py:1842` via `firestore_admin.get_previous_analysis(uid, id, mode=MODE_SELF)` (mode-scoped to avoid mode1-prev contamination — fixed 2026-06-07, commit `0bd6a48`). Frontend renders via `deltaFor(dim)` (`result.tsx:661`) + `mode3Summary` headline ("지난 분석보다 N점 발전했어요!", `result.tsx:189`). `[VERIFIED: file read]`

### Pattern 3: Dual-coach cross-fill (already implemented)
**What:** Gemini + Cerebras both called with retry; sections assembled; empty-section-0 guaranteed by cross-fill.
**Where:** `pipeline/app.py:1966-2024` calls both via `_call_coach_writer_with_retry`, then `assemble.assemble_dual_coach_sections(gemini, cerebras, top_keys)` (`assemble.py:404`). Gated by `GEMINI_COACH_ENABLED` (default "1", `app.py:211`). One-side-drop → cross-fill; both-fail → numeric fallback (`coach_details={}`). `[VERIFIED: file read]`

### Anti-Patterns to Avoid
- **Re-calibrating thresholds from the Phase 15 sweep.** D-02 + memory [[calibration-source-hard-gate]] forbid it. Compare to the existing `tilt_thresholds.yaml` (schema_v2, checksum in 08.1-SWEEP-EVIDENCE §1), do not regenerate it.
- **Declaring the gate PASS on mock E2E.** D-03: real LLM + dual coach must fire on a real video.
- **Writing a new analysis path.** `_process` is the single path. Reuse `sweep_phase8_1.py`.
- **Routing video bytes through Lambda.** App PUTs to S3 directly; sweep copies S3-to-S3.
- **Adding `RECOGNIZER_BACKEND`/`GEMINI_*` defaults to code.** They are Pod-env-driven (`app.py:198`); set on the Pod, not in source.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Real video E2E runner | New sweep script from scratch | `sweep_phase8_1.py` (copy/adapt) | Already handles S3 copy, doc write, `_process`, cleanup, commit-hash + checksum hygiene, non-zero exit on failure. |
| Mode 3 delta computation | New delta logic | `assemble.build_mode3` (wired) | Already mode-scoped + per-dimension; frontend already renders it. |
| Dual-coach orchestration | New writer-merge logic | `assemble_dual_coach_sections` + pipeline wiring | Cross-fill + audit already proven (13-C, 7 cases PASS). |
| Reference seeding/upload | Manual Firestore writes | `seed-reference-motions.mjs` / `reactivate_new6_motions.py` | Presign + validation + active-flip already encoded. |
| Presigned-URL refresh | New URL logic in app | `POST /playback-url` Lambda (`functions/playback-url`) | Handles 7-day TTL expiry refresh; app already wired (commit b1/b2). |
| TestFlight submit | Manual Transporter | EAS Submit (ASC API key registered) | Unattended submit already automated (memory [[asc-app-id-and-api-key]]). |

**Key insight:** Almost every "task" in this phase is operational orchestration of existing, tested code — the failure mode is *running it against the wrong/dead infra*, not missing implementation.

## Runtime State Inventory

This is a validation phase, not a rename, but it depends heavily on runtime state that grep cannot see. The planner MUST treat these as explicit tasks.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Live service config (Pod) | **RunPod Pod `xbdkj1g2ylnfwi` is DEAD** — `/health` returns HTTP 404 (verified 2026-06-17). RTMW+YOLOX+Gemini env lived only on that ephemeral pod (`/workspace/phase8_env.sh`, `.bashrc`), not in git. | **Create new Pod** (EU-RO-1 GPU priority per [[runpod-eu-ro1-gpu-priority]]) → run `.claude/scripts/setup_pod_full.sh` → restore env (RTMW_ONNX_PATH, YOLOX_ONNX_PATH, RECOGNIZER_BACKEND=gemini, GEMINI_API_KEY, RUNPOD_AUTH_TOKEN, GEMINI_COACH_ENABLED) → start uvicorn → verify `/health` `pipeline_loaded:true auth_configured:true`. Claude runs (pod-ops-claude-runs). |
| Live service config (Lambda) | `RUNPOD_ANALYZE_URL` Lambda env points to the dead pod's proxy URL. | `aws lambda update-function-configuration` with new Pod proxy `/analyze` URL **using `sunity-motion` creds** (active `sunity-api` cred = AccessDenied on Lambda — verified). |
| Stored data (Firestore) | 11 reference docs (`reference/{motionId}`) — all phase4_v1 RTMW active per STATE; `reference-downstream-backfill.json` (untracked, 2026-06-15) holds meanAngles/techniqueProfile/bodyNormalizationProfile/forceDirectionPattern seed. | **Verify** all 11 have the 4 Mode-1-required fields populated (bodyNormalizationProfile, EXTEND profile in techniqueProfile.jointExpectations, forceDirectionPattern, bodyComparisonSourcePose) before Mode 1 E2E. Check whether `backfill_reference_downstream.py` was actually applied to Firestore (file is untracked → possibly not committed/run). |
| Secrets/env | Gemini key in SSM `/sunity/motion/gemini-api-key`; Cerebras key via `CEREBRAS_KEY_PARAM`. Code reads lazily; graceful no-op if unset. | Inject into Pod env at bring-up. Verify both writers actually fire (D-03/D-12) — `GEMINI_COACH_ENABLED=1` + valid Gemini key + Cerebras key. |
| Build artifacts (app) | `eas.json` **preview profile has NO `env` block** (only production does — Firebase config + `EXPO_PUBLIC_API_BASE_URL`). app.json buildNumber "1" is overridden by EAS `appVersionSource: remote` + production `autoIncrement`. | **Add `env` block to preview profile** (copy from production) before preview build, or the preview build ships with missing Firebase/API config → app non-functional. This is a likely hidden blocker for D-08. |
| OS-registered state | None — no Task Scheduler/launchd/pm2 in this phase. | None (verified — pilot has no OS-registered jobs). |

## Common Pitfalls

### Pitfall 1: Building/running against the dead Pod
**What goes wrong:** All E2E silently fails or Lambda times out delegating to a 404 proxy.
**Why:** Pod is ephemeral (community cloud, no network volume mount — see STATE 2026-06-11); it terminated since 2026-06-08.
**How to avoid:** First plan task = Pod bring-up + `/health` 200 verification. Nothing downstream runs until green.
**Warning signs:** `curl <pod>/health` ≠ 200; Lambda CloudWatch shows connection errors.

### Pitfall 2: Wrong AWS credential for Lambda env sync
**What goes wrong:** `aws lambda update-function-configuration` → `AccessDeniedException`.
**Why:** Active env cred is `sunity-api` (funding-only); Motion AI needs `sunity-motion` creds (memory [[aws-keys-and-bucket]]).
**How to avoid:** Switch to `sunity-motion` profile/keys before any Lambda call. Verified: `sunity-api` is denied `lambda:ListFunctions`.

### Pitfall 3: Preview build ships with no env
**What goes wrong:** EAS preview build has no Firebase/API config → app can't auth or call backend.
**Why:** `eas.json` preview profile lacks the `env` block production has.
**How to avoid:** Copy production's `env` into preview before building.

### Pitfall 4: Recalibrating the threshold during the sweep (circular)
**What goes wrong:** Gate "passes" because thresholds were re-fit to the same data.
**Why:** Tempting to re-run `calibrate_tilt_thresholds.py` on Phase 15 sweep output.
**How to avoid:** Compare against the **frozen** `tilt_thresholds.yaml` (checksum `c94bb8...` in 08.1 evidence). D-02 + [[calibration-source-hard-gate]]. The sweep script's `--allow-fallback`/version-check guards already enforce schema_v2 match.

### Pitfall 5: presigned video playback expiry / Content-Type
**What goes wrong:** Result video doesn't play (octet-stream stored, or GET URL expired).
**Why:** PUT without Content-Type → S3 stores `application/octet-stream`; presigned GET TTL ≤ 7 days (memory [[s3-presigned-video-playback]]).
**How to avoid:** Ensure upload sets Content-Type; `POST /playback-url` refresh path already exists for expiry. Include in D-10 regression checklist.

### Pitfall 6: Dual-coach "fires" but is heuristic-only
**What goes wrong:** Coach sections render but Gemini never actually called (like 08.1 where `layer2_unavailable` 5/5).
**Why:** Recognizer/Gemini env not set on Pod → silent fallback.
**How to avoid:** Assert `gemini_ok=True` in pipeline logs (`app.py:1989` logs `gemini_ok cerebras_ok`), and verify `sectionAudit` shows non-cross-filled Gemini sections on at least one real video (D-12).

## Code Examples

### Verify a reference doc has all Mode-1 fields (Firestore)
```python
# Source: firestore_admin.py + backfill_reference_downstream.py field set
from sunity_shared import firestore_admin as fa
db = fa._db()
REQUIRED = ["bodyNormalizationProfile", "bodyComparisonSourcePose",
            "techniqueProfile", "forceDirectionPattern", "meanAngles"]
for snap in db.collection("reference").stream():
    d = snap.to_dict() or {}
    missing = [k for k in REQUIRED if k not in d]
    print(snap.id, "MISSING:", missing or "OK")
```

### Check dual-coach actually fired (pipeline log assertion)
```
# Source: pipeline/app.py:1989-1997 log line
grep "coach dual-track 섹션 조립" <cloudwatch-or-pod-log>
# expect: gemini_ok=True cerebras_ok=True ... cross_filled=[]   (best case)
# acceptable (D-12): one ok=False with cross_filled covering the gap → empty sections 0
```

### Lambda env sync (with correct creds)
```bash
# Source: STATE.md 함정 28 + memory aws-keys-and-bucket
# Use sunity-motion creds, NOT sunity-api
aws lambda update-function-configuration \
  --function-name <pipeline-fn> --region ap-northeast-2 \
  --environment "Variables={RUNPOD_ANALYZE_URL=https://<newpod>-8000.proxy.runpod.net/analyze,...}"
```

## State of the Art

| Old | Current | When | Impact |
|-----|---------|------|--------|
| Pod `xbdkj1g2ylnfwi` (RTX 4090) | DEAD (404) — new Pod needed | by 2026-06-17 | Real analysis fully down until bring-up |
| Cerebras `llama3.1-8b` | `gpt-oss-120b` | 2026-06-06 (commit 1110935) | Coach writer model; verified in `coach_writer.py:149` |
| 5 references | 11 references all phase4_v1 RTMW | 2026-06-15 | Mode 1 compares against 11 (D-04) |
| Single Cerebras coach | Dual Gemini+Cerebras sections + cross-fill | 13-C (2026-06-16) | Coach E2E is dual-track; verify both fire |
| letterSpacing `size*-0.04` | `track = () => 0` | 2026-06-06 (commit 787a901) | SIGABRT root cause fixed in source |

**Deprecated/outdated:**
- Pod `xbdkj1g2ylnfwi` SSH/proxy details in STATE.md — stale (pod dead). Do not reuse.
- `RUNPOD_ANALYZE_URL` currently in Lambda — stale (points to dead pod).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All 11 reference docs have the 4 Mode-1 fields populated in Firestore | Runtime State | Mode 1 falls back / fails for un-backfilled motions. **Verify before E2E** — `reference-downstream-backfill.json` is untracked, may not have been applied. Cannot confirm without Firestore read (needs SA creds). |
| A2 | The 6 success/fail dataset videos correspond to registered motion IDs for Mode 1 selection | Pattern 1 | Mode 1 needs a `referenceMotionId`; the new-6 motions (kip-up/peter-pan/power-spin/elbow-twist-sister/pdshape/combo) overlap but the *fail* videos' technique recognition must still route correctly. Dataset names map to motions but exact Mode-1 reference pairing per video is unverified. |
| A3 | Cerebras + Gemini SSM keys are still valid and funded | Pitfall 6 | Dual coach degrades to numeric fallback; D-12 still PASS (graceful) but D-03 (real LLM fires) needs at least one real call to succeed. |
| A4 | EAS production ASC API key auto-submit still works unattended | DELIV-01 | Submit step needs manual intervention; memory says automated but not re-verified this session. |
| A5 | New Pod can be created on a GPU meeting RTMW needs (EU-RO-1 priority) | Runtime State | Blocks all real E2E. Mitigated by [[runpod-eu-ro1-gpu-priority]] fallback ladder. |

## Open Questions

1. **Was `reference-downstream-backfill.json` actually applied to Firestore?**
   - Known: file exists untracked at repo root (2026-06-15), holds seed for all reference fields; `backfill_reference_downstream.py` exists.
   - Unclear: whether it was run against Firestore. STATE says all 11 are phase4_v1 active, but the *downstream* (meanAngles/forceDirectionPattern/bodyComparisonSourcePose) backfill state is not confirmed.
   - Recommendation: First Mode-1 task = Firestore field-presence verification (code example above). If missing, run backfill before E2E.

2. **Does Mode 1 need a reference for each of the 6 dataset motions, or is the 11-set the comparison library independent of the dataset?**
   - Known: D-04 = Mode 1 compares against all 11 registered references; D-05 = dataset is 6 success/fail pairs.
   - Unclear: the validation flow — does each dataset video get analyzed as a *student* against a chosen reference, or are references self-validated?
   - Recommendation: Treat as Mode 1 = (success video as student) vs (matching registered reference); 위양성 = success should score high+low-severity. Confirm pairing in plan.

3. **Will the new Pod's Gemini recognizer actually populate the `line` dimension?**
   - Known: 08.1 sweep had `layer2_unavailable` 5/5 (recognizer not initialized). line dim depends on Gemini EXTEND/BENT (SCORE-01, PROJECT 핵심 블로커).
   - Unclear: whether `RECOGNIZER_BACKEND=gemini` + valid key produces real line scores on these videos.
   - Recommendation: Make "Gemini recognizer fires (line dim non-None on ≥1 video)" an explicit assert, not assumed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| RunPod GPU Pod | All real E2E (W1-W3) | ✗ (404) | — | None — must create new Pod (blocking) |
| `sunity-motion` AWS creds | Lambda env sync | ✗ (active=sunity-api, denied) | — | None — must switch creds |
| Firebase SA creds | Firestore field verify + sweep | Partial (firebase-sa.json in repo per CLAUDE.md) | — | Pod has `/workspace/firebase-sa.json` |
| Gemini API key (SSM) | Recognizer + dual coach | Assumed (A3) | — | Coach: numeric fallback. Recognizer: line dim None. |
| Cerebras key (SSM) | Coach 처방/부상 sections | Assumed (A3) | — | Cross-fill from Gemini |
| EAS Build/Submit | TestFlight (W4) | Assumed available (cloud) | CLI ≥19 | None |
| Dataset videos | Mode 3 + 위양성 | ✓ (verified at `~/Downloads/정은지 선수 추가 영상/`) | — | — |

**Missing dependencies with no fallback (blocking):**
- RunPod Pod (dead) — blocks W1-W3 entirely.
- `sunity-motion` AWS credentials for Lambda env sync.

**Dataset confirmed present:** 7 success videos (`잘된 예시/fixtures:*-correct.mp4` incl. `combo` which has no fail-pair), 6 fail videos, 13 analysis `.md` docs (`분석결과/`). Double-extension typo confirmed: `fixtures:pdshape-correct.mp4  .mp4` (CONTEXT D-08 / discretion — normalize on upload). `combo` is Mode-1-only (no pair, per Deferred).

## Validation Architecture

> nyquist_validation: config not checked as explicitly false → section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest ≥8,<9 (`backend/requirements-dev.txt`) |
| Framework (app) | None — only `tsc --noEmit` (`app/package.json` `typecheck`). No JS test runner. |
| Config file | `backend/tests/conftest.py`; no app test config |
| Quick run (backend) | `PYTHONPATH=backend/shared/python python3 -m pytest backend/tests/phaseNN -x` |
| App gate | `cd app && npm run typecheck` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Command / Evidence |
|-----|----------|-----------|--------------------|
| MODE-01 | Mode 1 real E2E across 11 refs, expert-grade score | integration (real Pod sweep) | sweep variant → Firestore docs → manual assert score reflects quality |
| MODE-02 | Mode 3 session delta on same-user pair | integration (real E2E pair) | pair sweep → `deltaFromPrevious` present + sign correct |
| SCORE-04 | 위양성: success=high+low-severity, fail=fault-caught | integration + assert vs baseline | compare to `08.1-SWEEP-EVIDENCE.md` frozen thresholds |
| DELIV-01 | Guest completes Mode 1+3 on device, video plays | manual (device, belle) | EAS preview build → device → belle handoff (D-09) |

This phase is **validation-by-evidence**, not unit-test-driven. The "tests" are real-E2E sweeps producing Firestore evidence docs asserted against the locked baseline — mirroring 08.1's evidence-doc pattern. Phase 18 (deferred) will harness the fault-label auto-assert.

### Wave 0 Gaps
- [ ] Sweep variant for *new* (non-`reference/`) S3 keys — `sweep_phase8_1.py` assumes `reference/{name}.mp4` source keys; Phase 15 dataset needs an upload-then-sweep step (Claude's discretion, D-05).
- [ ] Mode-1 evidence assertion script (compare new run severity/score to 08.1 baseline) — light, evidence-doc-style.
- [ ] No app test framework — rely on `tsc --noEmit` + manual device verification (existing convention).

## Security Domain

> security_enforcement not explicitly false → included. This is a validation/delivery phase touching no new auth surface.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Firebase anonymous auth + ID-token verify in Lambdas (existing `sunity_shared.auth`). No change. |
| V3 Session Management | no | Anonymous; no sessions added. |
| V4 Access Control | yes | Presigned URLs scoped to uid (`playback-url` builds key from token uid). Verify no cross-uid leakage in test sweeps (use throwaway sweep_uid). |
| V5 Input Validation | yes | `validation.py` validators unchanged; no new input surface. |
| V6 Cryptography | yes | Secrets in SSM Parameter Store (never hardcoded). Pod env injection only — do not echo keys into logs/evidence docs. |

### Known Threat Patterns for this phase
| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| Pod proxy unauthenticated exposure | Info Disclosure | `RUNPOD_AUTH_TOKEN` required; server returns 503 if unset (`server.py:99`). Verify token set on new Pod. |
| Secret leakage into evidence/logs | Info Disclosure | Sweep evidence docs must not contain API keys; `setup_pod_full.sh` injects env, not committed. |
| Stale `sunity-api` exposed key | Elevation | Memory blocker: exposed `sunity-api` key deactivation still pending — unrelated to Phase 15 but note it is NOT the Motion AI cred. |

## Project Constraints (from CLAUDE.md)

- Tech stack locked — no new libs (Expo+RN/Lambda Python+SAM/Firestore/S3/RTMW→DTW/Cerebras/EAS).
- Infra separation — Motion AI on its own Lambda+S3; never the sunity.ai EC2.
- Secrets in AWS Parameter Store; `.env` hardcoding forbidden.
- Brand color `#FF4B33` immutable; Pretendard; light-theme only; theme tokens only (no hardcoded colors/spacing).
- No emojis anywhere in code or output; no slop.
- 3-way contract lockstep (`analysis.ts` ↔ `models.py` ↔ `contract.md`) — change together. (Phase 15 should not need contract changes — flag if a plan proposes one.)
- Korean for user-facing copy and comments; English identifiers.
- GPU/Pod ops run by Claude (pod-ops-claude-runs); belle does device + production approval only.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 위양성 게이트 = 정은지 영상 실 Pod E2E (RTMW + Gemini 인식 + 듀얼 coach 포함) 재측정 → 자세 품질 반영 + axis severity 기대대로 assert.
- **D-02:** 임계값 재calibrate 금지 ([[calibration-source-hard-gate]]). 기준선 = 08.1 SWEEP-EVIDENCE.md + Phase 1 IPSF GeometricCriterion baseline. circular tuning 금지.
- **D-03:** mock E2E만으로 게이트 충족 선언 금지 — 실 LLM/듀얼 coach 포함 최신 path 재검증이 게이트의 일부.
- **D-04:** Mode 1 비교 대상 = 등록된 11개 reference 전부 (phase4_v1 RTMW 재처리 완료). "5"는 위양성 calibration 영상 수였을 뿐.
- **D-05:** Mode 3 + 위양성 = 정은지 6 성공/실패 페어 (`~/Downloads/정은지 선수 추가 영상/`). 6 동작: pdshape · elbow-twist-sister · climb · kip-up · power-spin · peter-pan. 동일 인물·동일 동작이 Mode 3 델타 + 위양성 게이트를 한 셋으로 동시 충족.
- **D-06:** objectivity 하드가드 — `분석결과/*.md`는 fault 정성 참고만. "이 영상 N점" ground-truth 점수 라벨 영구 금지. fault 종류 라벨(영상 입력 라벨)은 OK.
- **D-07:** belle 본인 2영상 페어는 선택 — 있으면 보강, 없어도 정은지 페어로 진행 가능.
- **D-08:** SIGABRT fix → TestFlight preview 빌드 경로. release 빌드 native crash → EAS preview 빌드에서 잡고 검증.
- **D-09:** 핸드오프 규칙 ([[verify-before-handoff-even-final]]) — SIGABRT fix + EAS preview 빌드 + submit까지 PASS 확인 후 belle에게 "실기기 게스트 완주" 사람만 할 수 있는 단계만 넘김. 미검증 핸드오프 금지.
- **D-10:** 회귀 체크리스트 = presigned URL 만료/Content-Type 이슈 없음 ([[s3-presigned-video-playback]]) + letterSpacing SIGABRT 회귀 없음.
- **D-11:** 파일럿 primary = Gemini 유지. 섹션형 듀얼 coach = 원인=Gemini / 교정 처방=Cerebras / 부상위험=Cerebras / 강사확인=Gemini ([[section-dual-coach-report]]).
- **D-12:** 검증 기준 = 둘 다 채워지면 best, 한쪽 drop 시 cross-fill 폴백으로 빈 섹션 0이면 PASS. graceful degrade 허용 (단 D-03대로 실 LLM 호출 작동 확인).

### Claude's Discretion
- Pod 작업(SSH/sweep/Lambda env 동기화/mock·실 E2E 실행) Claude 실행 ([[pod-ops-claude-runs]]). 현 Pod = xbdkj1g2ylnfwi (RESEARCH: DEAD/404 — 신규 Pod 필요), RUNPOD_ANALYZE_URL Lambda env 동기화 필요.
- 검증 스크립트 구조, sweep 실행 방식, S3 업로드 경로, assert 구현 디테일 = Claude 판단.
- 영상 파일명 정규화(`fixtures:` prefix, 더블 확장자 오타 `pdshape-correct.mp4  .mp4`) = 업로드 시 Claude 정리.

### Deferred Ideas (OUT OF SCOPE)
- 영구 라벨 regression fixture + fault 자동 assert 하니스 = Phase 18 (Phase 15 의존). Phase 15 = 수동 실행 + assert까지만.
- belle 본인 다양한 앵글/동작 크래시 테스트 영상 대량 소싱 = SC4 강건성 확장, 실증 단계.
- `combo.mp4` (성공만, 페어 없음) — Mode 3 페어 미성립, Mode 1 단독 분석에만 사용.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODE-01 | 정은지 기준 모션 불러와 비교, 전문가 기준 점수 실영상 E2E | `assemble.build_mode1` + pipeline `_process` mode1 path (verified). Needs: new Pod + 11-ref field verification (A1) + real sweep. |
| MODE-02 | 본인 영상 2개 비교, 발전 progress 실영상 E2E | `assemble.build_mode3` deltaFromPrevious (verified, `assemble.py:539`) + `get_previous_analysis(mode=MODE_SELF)` (verified) + `result.tsx` deltaFor/mode3Summary (verified). Needs: same-user pair sweep. |
| SCORE-04 | 고수 영상 위양성 없이 신뢰 점수 (axis severity) | tilt-only `force_signals.py` + frozen `tilt_thresholds.yaml` (checksum c94bb8). Baseline = `08.1-SWEEP-EVIDENCE.md` (25/25 'low'). Assert against it, do not recalibrate (D-02). |
| DELIV-01 | TestFlight 게스트 모드 Mode 1+3 실기기 완주 | SIGABRT fixed (`typography.ts:15`). Needs: **eas.json preview `env` block** + preview build + device verify + belle handoff (D-09). Presigned/Content-Type regression (D-10). |
</phase_requirements>

## Sources

### Primary (HIGH confidence — live codebase, this session)
- `app/src/theme/typography.ts:15` — SIGABRT fix (`track = () => 0`)
- `app/src/app/analysis/result.tsx:189,661` — mode3 delta render
- `backend/shared/python/sunity_shared/analysis/assemble.py:404,521,539` — dual coach + build_mode1/mode3
- `backend/functions/pipeline/app.py:198,211,1842,1966-2024` — recognizer/coach env + mode3 + dual-coach wiring
- `backend/scripts/sweep_phase8_1.py` — real-E2E driver pattern
- `backend/scripts/reactivate_new6_motions.py`, `reprocess_reference_motions_phase4.py` — 11 motion IDs
- `app/eas.json` — preview env gap (verified)
- `.planning/phases/08.1-axis-metric-redesign/08.1-SWEEP-EVIDENCE.md` — frozen 위양성 baseline
- Pod `/health` HTTP 404 (curl, 2026-06-17) — Pod dead
- AWS `lambda:ListFunctions` AccessDenied for `sunity-api` (verified, 2026-06-17)
- `~/Downloads/정은지 선수 추가 영상/` directory listing — dataset present

### Secondary (MEDIUM)
- STATE.md Pod env / 남은 작업 / 함정 박제 — operational history (pod details now stale)
- Memory entries [[calibration-source-hard-gate]], [[pod-ops-claude-runs]], [[aws-keys-and-bucket]], [[s3-presigned-video-playback]], [[runpod-eu-ro1-gpu-priority]], [[section-dual-coach-report]], [[mode3-progress-not-similarity]], [[reference-library-phase4-all11]]

## Metadata

**Confidence breakdown:**
- Implementation state (what's built): HIGH — every claim file:line verified.
- Operational state (Pod/Lambda/creds): HIGH — Pod-dead and cred-denied both empirically verified this session.
- Reference field completeness (A1): MEDIUM — STATE says active, but downstream backfill application unconfirmed (needs Firestore read).
- LLM key validity (A3): LOW — assumed funded, not re-verified.

**Research date:** 2026-06-17
**Valid until:** ~7 days (Pod state and Lambda env are volatile; re-verify Pod liveness at plan/execute time).
