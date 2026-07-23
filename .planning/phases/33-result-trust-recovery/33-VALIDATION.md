---
phase: 33
slug: result-trust-recovery
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-23
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `33-RESEARCH.md` §Validation Architecture. Governing rule: **전수 not sample** (D-18/D-23) + **눈으로 확인 의무** (D-19). "코드 통과"는 확인이 아니다 — 산출물 자체를 연다.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest (`backend/requirements-dev.txt`, >=8,<9); phase suites under `backend/tests/phaseNN/` |
| **Framework (app)** | `tsc --noEmit` (`npm run typecheck`) — only static gate; no JS test runner. Render crash NOT caught by typecheck (D-21) |
| **6-motion re-analysis** | `backend/evals/phase25/run_sweep.py` (serial, in-process `_process`, Pod GPU + Gemini) + `assert_gates.py` |
| **Sim render** | iOS Simulator (Xcode 26.6) screenshot per D-21 |
| **Quick run command** | `pytest backend/tests/phase33 -q` (after Wave 0) + `cd app && npm run typecheck` |
| **Full suite command** | `pytest backend/tests -q` + 6-motion `run_sweep.py` + `assert_gates.py` |
| **Estimated runtime** | pytest ~tens of s; 6-motion sweep = minutes (Pod, serial — pipeline not concurrency-safe) |

---

## Sampling Rate

- **After every task commit:** `pytest backend/tests/phase33 -q` (backend tasks) / `npm run typecheck` (app tasks)
- **After every backend crop/voice wave:** 6-motion re-sweep (전수, D-23) — no per-motion sampling
- **Before belle UAT (phase gate):** all 6 fixtures re-analyzed + **every regenerated PNG/mp3 opened** (D-19) + Simulator render + screenshot (D-21)
- **Max feedback latency:** unit ~seconds; full sweep = minutes (accepted — serial mandatory)

---

## Per-Task Verification Map

*(Task IDs finalized by planner; rows track the deliverable→proof contract. Every row pairs a "틀리면 걸리는 장치" per D-18.)*

| Deliverable | Wave | Decision | Proof (test type) | Automated Command / Artifact | File Exists |
|-------------|------|----------|-------------------|------------------------------|-------------|
| A-0 evidence table (pointed vs measured vs shown joints, 6 motions) | A-0 | D-04 | data-dump + eyeball | read `phase25_sweep_report.json` + belle doc dump → D-04 branch verdict table | ❌ W0 (dump helper) |
| phrasebook 동작별 cueLine, no `__common__` fallback for registered combos | A-2 | D-14 | data + unit | `tests/phase33/test_phrasebook_motion_specific.py`: `assemble_phrases("ref-power-spin","split_angle") != __common__` + emit-value dump | ❌ W0 |
| 문구 방향 vs 기준영상 모순 0 (hard gate) | A-2 | D-14/D-18 | manual eyeball 전수 | open each authored cue vs ref frame; fail-closed on contradiction | procedure |
| crop item↔criterion joint-exact | A-5 | D-12/D-18 | unit + eyeball 전수 | assert join returns joint-matching card; open ALL regenerated PNGs | ❌ W0 |
| crop same-moment / same-scale / same-marking OR card dropped | A-5 | D-12 | eyeball 전수 | open user/ref PNG pairs side-by-side (all cards, all 6 motions) | procedure |
| angle number un-baked from crop PNG (defect #6, number only in 내역) | A-5 | D-12/D-16/D-18 | unit + eyeball 전수 | assert `_mark`/`_draw_leg_angle` number-text branch removed; open regenerated PNGs — no baked number | ❌ W0 |
| overlay/marker 표시 ↔ 지적 항목 two-way; no orphan marker | A-6 | D-13/D-18 | unit | extend `buildDeductionMarkers` / `selectedZoom` tests | ❌ W0 |
| voice pause + region highlight on cue start | A-6 | D-13 | sim render | Simulator recording of cue transition | procedure |
| illustration anatomy 전수 (limb count, joint direction); 1 fail → set unwired | A-7 | D-15/D-18 | eyeball 전수 | open every generated illustration | procedure |
| 6-motion 전수 re-sweep green | phase gate | D-23 | integration | `run_sweep.py` (cold+warm, Pod) + `assert_gates.py` | ✓ harness exists |
| every screen renders (no crash) before OTA | phase gate | D-21 | sim render | Simulator launch + screenshot per changed screen | procedure |

---

## Wave 0 Requirements

- [ ] `backend/tests/phase33/` — new test dir: phrasebook motion-specific (no `__common__` for registered combos), crop join joint-exact, un-baked-number assertion, orphan-marker two-way match. Analog: `backend/tests/phase32/`.
- [ ] Firestore doc-dump helper — none exists in `backend/scripts/`; small `firebase-admin` script keyed by uid/analysisId to eyeball real values (D-19). Serves A-0 + belle-doc mockup data (D-10).
- [ ] A-0 analysis step — read `phase25_sweep_report.json` (`visionVeto.faultJoints` pointed / `seedObservation.window_joints,fallback_joints` measured / `activatedCriteria` shown) + dumped belle doc → produce the D-04 evidence table and branch verdict.
- [ ] Fixture-less registered motions (ref-foxtop, ref-foxtop-split, ref-invert, ref-sideway-spin) — alternative verification per D-23 (no fixture mp4). Planner MUST name the substitute proof; silent skip forbidden (D-18).

*Existing infra: pytest + phase-suite convention, `run_sweep.py`/`assert_gates.py` sweep harness.*

---

## Manual-Only Verifications

*Heavy by design — this is an expression/copy phase; D-19 makes eyes-on mandatory, not fallback.*

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| crop PNG pair reads as "same moment/scale/marking" | D-12 | visual judgment; no numeric proxy for "reads as comparable" | open all card PNG pairs, all 6 motions; any mismatch → card must be dropped, not shipped |
| crop PNG has no baked angle number (defect #6) | D-12/D-16 | visual; number must live only in 내역 | open all regenerated crop PNGs; any baked number → fail (un-bake regressed) |
| coaching cue matches ref-motion actual direction | D-14 | domain-truth vs authored text; contradiction is semantic | dump each emitted cue, compare to ref frame direction; contradiction → fail-closed |
| illustration anatomy correct (limbs, joint direction) | D-15 | generative asset; anatomy errors (e.g. 3 legs) only visible on open | open every illustration; 1 fail → whole set unwired |
| voice-cue pauses video + highlights region | D-13 | timing/interaction behavior | Simulator recording; confirm pause→highlight→resume sequence |
| no screen renders blank/crashes; no status-bar overlap | D-17/D-21 | render-time only; typecheck blind to it | Simulator launch + screenshot every changed screen before OTA |
| mockup survivors pass judgment criteria D-07 | D-07/D-10 | design judgment | Claude pre-filters by D-07; only survivors → belle (1 touchpoint) |

---

## Validation Sign-Off

- [x] Every deliverable has an automated verify OR a named manual procedure + a D-18 "틀리면 걸리는 장치"
- [x] No silent skips: fixture-less motions have named substitute proof
- [x] Wave 0 covers all ❌-marked references (test dir, doc-dump helper) — 33-01
- [x] 6-motion sweep run serially (pipeline not concurrency-safe) — 33-16 (phase gate re-sweep)
- [x] Sim render + PNG/mp3 전수 열람 before belle UAT — 33-16 (phase gate)
- [x] `nyquist_compliant: true` set (plan-checker confirmed every task maps to a row)

**Approval:** approved 2026-07-23 (plan-checker verification passed, 0 blockers)
