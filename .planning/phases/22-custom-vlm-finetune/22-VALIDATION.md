---
phase: 22
slug: custom-vlm-finetune
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-06
revised: 2026-07-07
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Revised 2026-07-07 (plan-checker revision pass — filled from each plan's `<automated>` verify; F1/F2/F3/F5 findings reflected).
> 2026-07-07 ITERATION2 fixup 반영 (태스크 그래프 싱크 — DR-02/03/05/06/07 검증 경로 현행화)

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (>=8,<9 — `backend/requirements-dev.txt`) |
| **Config file** | none — `backend/tests/phase22/conftest.py` created by 22-01 Task 1 (shared-layer sys.path fixture) |
| **Quick run command** | `python3 -m pytest backend/tests/phase22 -x -q` |
| **Full suite command** | `python3 -m pytest backend/tests -q` |
| **Estimated runtime** | phase22 unit subset ~5-15s (pod-free); full suite ~1-2 min |

Pod/cloud-effecting tasks (Pod SSH, S3, Firestore, vLLM serve) are verified by acceptance_criteria + SUMMARY, not by the local unit runner — listed under **Manual-Only Verifications**.

---

## Sampling Rate

- **After every task commit:** `python3 -m pytest backend/tests/phase22 -x -q`
- **After every plan wave:** `python3 -m pytest backend/tests -q` (baseline FAILED diff must stay IDENTICAL — regression-0 rule)
- **Before `/gsd-verify-work`:** full suite green (pre-existing baseline failures excepted, diff IDENTICAL)
- **Max feedback latency:** ~15s (phase22 subset)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Req | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-----|-----------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-1 | 01 | 1 | FT-03 | T-22-02 | schema whitelist + score-absence + faults ⊇ deduction contract (F1) | unit | `pytest backend/tests/phase22/test_schema.py -x -q` | ❌ W1 | ⬜ pending |
| 22-01-2 | 01 | 1 | FT-03 | T-22-01 | error-profile artifact has no PII (histograms only) | unit | `python3 -c "…rtmw_error_profile.json _meta…"` | ❌ W1 | ⬜ pending |
| 22-01-3 | 01 | 1 | FT-03 | T-22-01 | perturb pure (no net), original preserved | unit | `pytest backend/tests/phase22/test_perturb.py -x -q` | ❌ W1 | ⬜ pending |
| 22-02-1 | 02 | 1 | FT-02 | T-22-03/05 | non-notified prefix + provenance + no score labels | unit | `collect…--dry-run && pytest test_provenance test_manifest_consistency` | ❌ W1 | ⬜ pending |
| 22-02-2 | 02 | 1 | FT-02 | T-22-04 | anonymize-before-load + hard-negative isolation | unit | `pytest test_manifest_consistency && python3 -c "…hard_negative>=2…"` | ❌ W1 | ⬜ pending |
| 22-02-3 | 02 | 1 | FT-06 | T-22-05 | license audit + forbidden-model fence | unit+manual | `pytest … && grep Apache LICENSE-AUDIT.md` | ❌ W1 | ⬜ pending |
| 22-03-1 | 03 | 1 | FT-05 | T-22-07 | shadow store: flat-dict, PII whitelist | unit | `pytest test_shadow_wiring.py -k "store_vlm_shadow or helper"` | ❌ W1 | ⬜ pending |
| 22-03-2 | 03 | 1 | FT-03 | T-22-09 | silent-fail-forbidden status enum, Gemini re-call 0 | unit | `pytest test_shadow_wiring.py -x -q && full-suite FAILED/ERROR → 22-03-BASELINE-FAILED.txt diff (exit 0)` | ❌ W1 | ⬜ pending |
| 22-03-3 | 03 | 1 | FT-05 | T-22-07 | production Pod 변형 승인 + rollback 블록 (DR-02) | **checkpoint** | (human gate) | n/a | ⬜ pending |
| 22-03-4 | 03 | 1 | FT-05 | T-22-07 | Pod 배포 + shadow 스모크 + peak-VRAM artifact (A5) | **manual** (Pod) | `grep -E '^peak_vram_gb: [0-9.]+' 22-POD-VRAM.md` (numeric 필드) | ❌ W1 | ⬜ pending |
| 22-04-1 | 04 | 2 | FT-03 | T-22-12 | File API delete-in-finally, judge<7 discard, measurement fields preserved (F1) | static+unit | `python3 -c "…files.delete…gemini-3.1-pro-preview…" && pytest backend/tests/phase22/test_gemini_teacher.py -x -q` (delete-in-finally unit — DR-07) | ❌ W1 | ⬜ pending |
| 22-04-2 | 04 | 2 | FT-03 | T-22-10 | 3-way consistency, no score keys, svg_spec label wellformed (F2), faults ⊇ contract (F1), collection_complete fail-closed (DR-06) | unit | `pytest test_build_jsonl.py -x -q` | ❌ W1 | ⬜ pending |
| 22-04-3 | 04 | 2 | FT-02 | T-22-12 | 증류 full-batch 비용 승인 (DR-05) | **checkpoint** | (human gate) | n/a | ⬜ pending |
| 22-04-4 | 04 | 2 | FT-02 | T-22-12 | distill batch, files.list residue 0, balanced counts | unit+manual | `pytest … && aws s3api head-object train.jsonl && validation_owner 계약 assert (DR-07/DR-04)` | ❌ W1 | ⬜ pending |
| 22-05-1 | 05 | 2 | FT-01 | T-22-14 | eval mini-set: balanced + trap + hard-negative | static | `python3 -c "…manifest.yaml 4 types…"` | ❌ W1 | ⬜ pending |
| 22-05-2 | 05 | 2 | FT-01 | T-22-14 | 4-axis + svg wellformedness (F2), guided JSON, SERIAL | static | `python3 -c "…run_bakeoff importable…"` | ❌ W1 | ⬜ pending |
| 22-05-3 | 05 | 2 | FT-01 | T-22-14 | metric fns pod-free correctness | unit | `pytest test_bakeoff_harness.py -x -q` | ❌ W1 | ⬜ pending |
| 22-06-1 | 06 | 3 | FT-01 | — | Pod-rental cost belle approval | **checkpoint** | (human gate) | n/a | ⬜ pending |
| 22-06-2 | 06 | 3 | FT-01 | T-22-17 | idempotent setup, pinned model IDs, SERIAL bake-off | static+manual | `bash -n setup_training_pod.sh && grep ms-swift\|vllm` | ❌ W3 | ⬜ pending |
| 22-06-3 | 06 | 3 | FT-01 | — | backbone selection belle decision + provenance | **checkpoint** | (human gate) | n/a | ⬜ pending |
| 22-07-1 | 07 | 4 | FT-04 | — | SFT training cost belle notify | **checkpoint** | (human gate) | n/a | ⬜ pending |
| 22-07-2 | 07 | 4 | FT-04 | T-22-21 | 16-bit→AWQ (no 4-bit direct merge), vLLM load smoke | static+manual | `bash -n run_sft.sh merge_and_quant.sh && grep "merge_lora true"` | ❌ W3 | ⬜ pending |
| 22-07-3 | 07 | 4 | FT-04 | T-22-20 | D-15 gate incl. svg_spec_validity (F2), SKIPPED≠FAIL; post-Pod 게이트 = --require-pass exit 0, FAIL/SKIPPED 잔존 시 통과 불가 (DR-03) | unit+manual | `pytest test_assert_gates.py -x -q` (로컬 unit) | ❌ W1 | ⬜ pending |
| 22-08-1 | 08 | 5 | FT-05 | T-22-24 | Protocol graceful no-op, REPORT_KEYS lockstep parser | unit | `pytest test_vlm_judge.py -x -q` | ❌ W1 | ⬜ pending |
| 22-08-2 | 08 | 5 | FT-05 | T-22-25 | vLLM 동거 승인 canary-first + rollback 블록 (DR-02) | **checkpoint** | (human gate) | n/a | ⬜ pending |
| 22-08-3 | 08 | 5 | FT-05 | T-22-23/25 | localhost bind, measured gpu-mem-util, boot order | static+manual | `bash -n setup_vllm.sh && grep 127.0.0.1 vllm_loaded` | ❌ W3 | ⬜ pending |
| 22-08-4 | 08 | 5 | FT-05 | T-22-25 | cohab verdict: OOM 0, latency ≤+20%, EVAL18 survives | **manual** (Pod) | `grep 동거판정 22-POD-VRAM.md` | ❌ W3 | ⬜ pending |
| 22-09-1 | 09 | 6 | FT-05 | T-22-28 | shadow after complete_analysis, silent-fail-forbidden | unit | `pytest test_shadow_wiring.py -x -q` | ❌ W1 | ⬜ pending |
| 22-09-2 | 09 | 6 | FT-05 | T-22-28 | shadow accumulation ≥20 docs (F5 real assertion) | **manual** (Firestore) | `python3 -c "…vlm_shadow stream; assert n>=20"` | ❌ W3 | ⬜ pending |
| 22-09-3 | 09 | 6 | FT-05 | T-22-27 | role match-rate + Gemini-이상 report, no score labels | static | `python3 -c "…shadow_report build_report…"` | ❌ W1 | ⬜ pending |
| 22-10-1 | 10 | 7 | FT-05/04 | T-22-30 | role-wise swap toggle, own→VisionVerdict→deduction (F1), score-free | unit | `pytest test_swap_toggle.py test_shadow_wiring.py -x -q` | ❌ W1 | ⬜ pending |
| 22-10-2 | 10 | 7 | FT-05 | T-22-30 | veto swap belle approval → EVAL18 no-regression | **checkpoint**+manual | (human gate + Pod EVAL18) | ❌ W3 | ⬜ pending |
| 22-10-3 | 10 | 7 | FT-04 | T-22-33 | coach D-02 gate, RL follow-on boundary only | static | `test -f 22-SWAP-LOG.md && grep GSPO\|MPO D-02` | ❌ W1 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · File Exists: ❌ W1/W3 = created by that wave*

---

## Wave 0 (data-engine, exec-wave 1) Requirements

- [ ] `backend/tests/phase22/conftest.py` — shared-layer sys.path fixture (22-01 T1)
- [ ] `backend/tests/phase22/test_schema.py` — REPORT_KEYS + score-absence + discretize + faults⊇deduction lockstep (F1)
- [ ] `backend/tests/phase22/test_perturb.py` — purity + self-label preservation
- [ ] `backend/tests/phase22/test_provenance.py`, `test_manifest_consistency.py` — provenance + balance gate
- [ ] `backend/tests/phase22/test_shadow_wiring.py` — store helper + pipeline wiring
- [ ] pytest already installed (`backend/requirements-dev.txt`) — no framework install needed

---

## Manual-Only Verifications

| Behavior | Req | Why Manual | Test Instructions |
|----------|-----|-----------|-------------------|
| production Pod 변형 승인 checkpoint (22-03-3) | FT-05 | belle blocking gate (DR-02) | canary 경로(a) vs 현재 Pod 직접(b) 택일 자료 + rollback 블록(env revert/start_server.sh revert/재기동/health/Lambda env sync) 제시 → "approved"/"current-pod" resume-signal |
| Pod shadow smoke + peak VRAM (22-03 T4) | FT-05 | Live Pod SSH + Firestore write | Run 1 fixture analysis on Pod, confirm `vlm_shadow/{hash}` doc + `status=completed`, poll nvidia-smi peak → 22-POD-VRAM.md에 `peak_vram_gb:` 등 라인 단위 파싱 필드(peak_vram_gb/total_vram_gb/model_variant/pod_type/pod_id/measured_at/vllm_gpu_mem_util_recommended) 기록 |
| 증류 비용 checkpoint (22-04-3) | FT-02 | belle blocking gate (DR-05) | manifest 증류 대상 행 수 + teacher/judge 예상 call 수 + quota/credit probe + 첫 run max rows=10 + abort threshold 제시 → 10-rows 필터 통계/File API 잔여물 확인 후 "approved" resume-signal |
| Distill batch execution (22-04 T4) | FT-02 | Gemini File API + S3 | Run gemini_teacher over manifest, assert `files.list` residue 0, upload JSONL — validation_owner 계약 확인(explicit_val_jsonl=train+val 둘 다 / phase22_eval_gate=train만), log filter stats |
| bake-off SERIAL run (22-06 T2) | FT-01 | Training Pod GPU | vllm serve candidate A → run_bakeoff → cold re-run x2 → candidate B; 2 reports + ALLDONE |
| SFT + AWQ export (22-07 T2) | FT-04 | Training Pod GPU | swift sft → merge_lora(16-bit) → AWQ → vllm load smoke returns REPORT_KEYS JSON |
| D-15 gate Pod eval (22-07 T3) | FT-04 | Pod inference on mini-set + EVAL18 | run SFT model over mini-set/EVAL18/held-out SERIAL → post-Pod `assert_gates.py --require-pass` exit 0 (DR-03) — FAIL/SKIPPED 잔존 시 통과 불가 |
| vLLM 동거 승인 checkpoint (22-08-2) | FT-05 | belle blocking gate (DR-02) | 22-POD-VRAM.md 실측 예산 + gpu-memory-utilization 제안값 + canary 경로(a) vs 현재 Pod 직접(b) rollback 블록(vLLM 중지/start_server.sh revert/재기동/health/Lambda env sync) 제시 → "approved"/"current-pod" resume-signal |
| vLLM cohabitation (22-08 T3/T4) | FT-05 | Serving Pod VRAM | boot order (NLF warm → vLLM), OOM 0 + latency ≤+20% + EVAL18 survives, else D-14 fallback |
| shadow accumulation ≥20 (22-09 T2) | FT-05 | Firestore live | F5 command asserts ≥20 `vlm_shadow` docs; motion-coverage ≥7 confirmed via shadow_report / SUMMARY |
| role-wise swap + EVAL18 (22-10 T2) | FT-05 | belle gate + Pod | belle approval → env swap → EVAL18 6-pair no-regression (변별 4 + known 2) |

---

## Validation Sign-Off

- [x] All `auto` tasks have `<automated>` verify (no `MISSING`); Pod/cloud tasks have local artifact verify + Manual-Only row
- [x] Sampling continuity: no 3 consecutive auto tasks without automated verify (every auto task carries one; 22-09 T2 no-op replaced with real Firestore assertion — F5)
- [x] Wave 0 covers all test stubs created in exec-wave 1
- [x] No watch-mode flags (`--watchAll` absent); no full-E2E-only gating
- [x] Feedback latency < 15s (phase22 unit subset)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** plan-checker revision pass 2026-07-07 — nyquist-compliant. `wave_0_complete` flips true after exec-wave 1 lands.
