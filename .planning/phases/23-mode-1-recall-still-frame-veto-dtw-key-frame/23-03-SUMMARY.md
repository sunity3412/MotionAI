---
phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame
plan: 03
subsystem: api
tags: [eval-harness, vision-veto, terminal-gate, faultkey, multi-arm, run-commit-ancestry, pod-bound, mode1]

# Dependency graph
requires:
  - phase: 23-01
    provides: FaultKey single owner (to_dict/from_dict + locked enum), VisionFaultContext.to_trace_dict, collect/apply 2-function seam, resource_limited/low_alignment_confidence statuses
  - phase: 23-02
    provides: collect-before-coach 라이브 배선 (geminiCallCount=1), build_quantification_result, to_audit_dict quantification attach
  - phase: 20-04
    provides: SEVERITY_CAP (50/75/90) regression subset 게이트 (정은지 95~100 / kip-up moderate≤75 / 결정론 / EVAL18 4쌍) — 23-03 이 still-frame 경로에서 OWN·supersede
provides:
  - still-frame veto eval harness (Pod-bound, 순차, FULL production seam, multi-arm result shape, run-commit ancestry 강제)
  - frozen manifest (JSON, stdlib only) + gate_policy + regression_pairs(4쌍) + canonical FaultKey expected_recall_keys
  - pre-Pod manifest freeze 스크립트 (clean-worktree 강제, lock.json owner)
  - non-zero exit assert gate (stdlib only, lock 정합 + run-commit ancestry + multi-arm shape + locked policy 재계산 + FaultKey recall)
  - mandatory behavioral test (14 fixture, 실제 subprocess exit code 검증)
affects: [pod-eval-execution, phase-20-04-supersede-marker]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "eval harness 가 어댑터 직접호출이 아니라 production seam(collect→coach→build_result→apply) 통과 측정 (H5)"
    - "multi-arm result shape: cases[]{row_id, arms:{production_still, whole_video_baseline, direct_adapter_still}} — 평면 (case,arm) row 아님 (D-17 HIGH-2)"
    - "run-commit ancestry: harness 가 시작 시 lock∈ancestor(run HEAD)+worktree clean 강제(아니면 실행 거부); assert 가 lock∈ancestor(result.run_git_commit)∈ancestor(HEAD) 검증 (D-17 HIGH-1)"
    - "terminal gate stdlib-only (json/hashlib/subprocess) — PyYAML 의존 0 으로 Pod-terminal assert 가 import 단계에서 죽지 않음 (D-16 HIGH-2)"
    - "manifest-owned policy: coverage 임계·case-class 그룹·EVAL18 pair margin 을 manifest gate_policy/regression_pairs 가 소유, assert 는 locked policy 에서만 재계산 (D-17 MED-1/MED-2)"
    - "canonical FaultKey 단일 owner recall: assert 가 FaultKey.from_dict/to_dict 정규화 4-tuple 로 대조 (한글 표시라벨 아님), import 불가 시 동일 locked enum fallback (D-17 MED-3)"

key-files:
  created:
    - backend/research/spikes/eval_stillframe_veto.py
    - backend/research/spikes/eval_stillframe_veto_manifest.json
    - backend/research/spikes/freeze_stillframe_veto_manifest.py
    - backend/research/spikes/assert_stillframe_veto_gate.py
    - backend/tests/test_assert_stillframe_veto_gate.py
  modified: []

key-decisions:
  - "eval harness 는 Pod-bound — production seam import(functions.pipeline.app)는 GPU/Gemini 의존이라 비-Pod 환경에서 호출 불가. 본 plan 의 Pod-free 부분(harness 코드/manifest/freeze/assert/behavioral test)만 로컬에서 검증, 실측은 Task 3 Pod checkpoint 가 수행"
  - "assert 의 FaultKey 정규화는 단일 owner(sunity_shared.analysis.vision_veto.FaultKey) import 우선, ImportError 시 동일 locked enum fallback — Pod-terminal 에서 sunity_shared 가 path 에 없어도 게이트가 import 단계에서 죽지 않게 함"
  - "behavioral test 는 temp git repo 에 A=lock/B=run/C=head 3-commit 체인을 만들고 cwd=repo 로 assert subprocess 를 실행해 git merge-base --is-ancestor 를 실제 해소 — fake monkeypatch 가 아니라 진짜 ancestry 로 검증"

patterns-established:
  - "frozen manifest = JSON (PyYAML 부재 Pod 환경 정합); freeze/assert 전부 stdlib only"
  - "harness D-14 게이트 필드(elite_clean_score_in_95_100/kipup_fault_moderate_le_75/score_determinism_cold·warm)를 result JSON top-level 에 박제하고 assert 가 final score 에서 재계산(precomputed 불신)"

requirements-completed: []  # VETO-06/SCORE-08/TRUST-06 은 Task 3 Pod 실측 통과 후 완료 — orchestrator 가 마킹

# Metrics
duration: ~70min
completed: 2026-06-23
---

# Phase 23 Plan 03: Still-Frame Veto Eval Harness + Terminal Gate Summary

**still-frame veto 구현(23-01/02)을 Pod GPU 에서 FULL production 경로로 실측할 순차 eval harness + tamper-proof terminal gate(pre-Pod freeze / run-commit ancestry / multi-arm result shape / manifest-owned policy / canonical FaultKey recall)와 14-fixture behavioral test 를 구축했다. Pod-free 부분(Tasks 1/1b/2)은 완료·로컬 검증; 라이브 GPU·Gemini·실 영상이 필수인 Task 3(POD terminal)은 belle 의 blocking-human 게이트 판정 대기 중.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 4 — Tasks 1/1b/2 완료 (Pod-free), Task 3 pending (POD terminal, blocking-human)
- **Files created:** 5
- **Tests:** behavioral test 14 fixture 전부 통과 (`python3 -m pytest tests/test_assert_stillframe_veto_gate.py -q` → 14 passed)

## Accomplishments

### Task 1 — still-frame veto eval harness + frozen manifest (`d0bb49a`, amended `98aa306`)
- `eval_stillframe_veto.py`: Pod-bound 순차 harness. **FULL production seam**(`_collect_vision_fault_context`(coach 전, Gemini 소유) → `to_coach_context` 소비 → `_build_vision_quantification_result` → `_apply_vision_veto(vision_fault_context=)`)을 통과해 측정하고, 어댑터 직접호출이 아닌 production 경로로 verdict 1회(geminiCallCount=1).
- **multi-arm result shape (D-17 HIGH-2):** `cases[]{row_id, arms:{production_still, whole_video_baseline, direct_adapter_still}}` — 평면 (case,arm) row 아님. production 게이트는 `arms.production_still` 만, baseline 비교는 `arms.whole_video_baseline` 만.
- **run-commit ancestry 강제 (D-17 HIGH-1):** 시작 시 lock 존재 / 현 manifest sha==lock.manifest_sha256 / `git merge-base --is-ancestor <lock_git_commit> HEAD` / worktree clean(출력 경로 제외)이 아니면 **실행 거부**. result 에 run_git_commit/worktree_dirty_at_run/manifest_lock_git_commit/manifest_sha256/eval_command/result_generated_at 기록.
- **3-way 분리 + completion + coverage (D-11/D-12 HIGH-2):** clean `arms.production_still` 을 applied(FP)/true_negative/alignment_abstention/resource_incomplete 로 분류. resource_limited 는 abstention 과 그룹화 안 됨(완료실패). coverage·case-class 그룹은 manifest `gate_policy` 에서 재계산.
- **EVAL18 4쌍 + D-14 흡수 게이트:** regression margin 은 manifest `regression_pairs` mapping 에서만 계산(row_id/motion 추론 0). `elite_clean_score_in_95_100`/`fault_cap_holds`/`kipup_fault_moderate_le_75`/`score_determinism_cold`/`score_determinism_warm` 를 실제 final score 에서 산출해 박제.
- `eval_stillframe_veto_manifest.json`: frozen 라벨 (JSON, stdlib only) — `gate_policy` + `regression_pairs`(4쌍) + 14 rows. kip-up row = `{expected_severity: moderate, max_score: 75, expected_recall_keys: [좌/우팔 arm + head_neck canonical FaultKey]}` (≤50/major 아님). SCORE-09 sensitivity 행 부재.

### Task 1b — pre-Pod manifest freeze (`e9ccae4`)
- `freeze_stillframe_veto_manifest.py`: manifest freeze 를 Pod 측정과 **별도 pre-Pod 단계**로 분리 (D-16 HIGH-1). clean-worktree 강제(manifest uncommitted 또는 worktree dirty 면 non-zero REFUSE). lock.json 에 manifest_sha256 + lock_git_commit(HEAD) + created_at(주입) + row_ids + expected_policy + regression_pairs/gate_policy snapshot 박제.
- **stdlib only (D-16 HIGH-2):** json/hashlib/subprocess 만. PyYAML/벽시계 직접호출 0.
- 기능 검증: temp git repo 로 (1) manifest uncommitted → rc=3 REFUSE, (2) clean worktree → rc=0 freeze, (3) dirty worktree → rc=3 REFUSE 세 경로 전부 확인.

### Task 2 — non-zero assert gate + mandatory behavioral test (`d4ca1ce`)
- `assert_stillframe_veto_gate.py`: stdlib-only non-zero exit gate. 검사 — lock 정합 + **run-commit ancestry**(lock∈ancestor(result.run_git_commit)∈ancestor(HEAD) + worktree_dirty_at_run==false + manifest_lock/sha 정합), **multi-arm shape**(cases[].arms, required_arms 정확히 1회, unknown arm 0), 타입/스키마(`"true"` 문자열 거부), **재계산**(coverage/completion/determinism/arm 캐시격리/D-14 — precomputed 불신), **locked gate_policy/regression_pairs 에서 coverage·margin 재계산**, **canonical FaultKey 4-tuple recall**(단일 owner import + fallback, unknown fault_kind 사전 fail), kip-up moderate≤75 severity-misclassification vs cap-application **구분 메시지**, status 화이트리스트. 어떤 실패에서도 non-zero exit.
- `test_assert_stillframe_veto_gate.py`: 14 behavioral fixture — temp git repo 의 3-commit 체인으로 실제 subprocess exit code 검증. valid→0; hash mismatch / missing row / extra arm / `"true"` 문자열 / non-budget resource_limited / kip-up major+50(severity 오분류) / kip-up moderate+80(cap 실패) / EVAL18 fault≥success / lock∉ancestor(run) / worktree_dirty_at_run==true / missing required arm / unknown arm / unknown fault_kind → 각각 non-zero. **14 passed.**

## Task Commits

1. **Task 1: harness + frozen manifest** - `d0bb49a` (feat)
2. **Task 1b: pre-Pod freeze 스크립트** - `e9ccae4` (feat)
3. **Task 2: assert gate + behavioral test** - `d4ca1ce` (feat)
4. **Task 1 amend: D-14 게이트 필드 emit (Rule 2)** - `98aa306` (feat)

## Files Created

- `backend/research/spikes/eval_stillframe_veto.py` — Pod-bound 순차 eval harness (production seam, multi-arm shape, run-commit ancestry, 3-way 분리, D-14 게이트)
- `backend/research/spikes/eval_stillframe_veto_manifest.json` — frozen 라벨 manifest (gate_policy + regression_pairs + 14 rows, canonical FaultKey)
- `backend/research/spikes/freeze_stillframe_veto_manifest.py` — pre-Pod freeze (clean-worktree 강제, lock.json owner)
- `backend/research/spikes/assert_stillframe_veto_gate.py` — stdlib-only non-zero assert gate
- `backend/tests/test_assert_stillframe_veto_gate.py` — 14-fixture mandatory behavioral test

## Decisions Made

- **eval harness 는 Pod-bound:** `run_production_arm` 이 `functions.pipeline.app`(GPU/Gemini/pipeline 의존)을 lazy import 한다. 비-Pod 환경에서는 호출 불가하므로, 본 plan 의 Pod-free 부분(harness 코드 ast-parse/serial/run-commit grep, manifest JSON, freeze 기능 테스트, assert + behavioral test)만 로컬에서 검증. 실측은 Task 3 Pod checkpoint 가 수행.
- **assert FaultKey 정규화:** 단일 owner import(권장) 우선, ImportError 시 동일 locked enum fallback. Pod-terminal 에서 `sunity_shared` 가 sys.path 에 없어도 게이트가 import 단계에서 죽지 않게 — `_normalize_faultkey` 가 양쪽 경로 모두 unknown enum 을 GateFail 로 거부.
- **behavioral test ancestry:** temp git repo 에 A/B/C 3-commit 체인을 만들고 assert subprocess 를 `cwd=repo` 로 실행해 `git merge-base --is-ancestor` 를 실제 해소. fake/monkeypatch 가 아니라 진짜 commit ancestry 로 lock∈ancestor(run)∈ancestor(HEAD) 를 검증.

## Deviations from Plan

**1. [Rule 2 - 누락 보완] harness 가 D-14 named 게이트 필드를 emit 하지 않음**
- **Found during:** Task 1 final 검증 (acceptance "D-14 게이트 필드 산출").
- **Issue:** 초기 harness 는 EVAL18/aggregates 만 산출하고 `elite_clean_score_in_95_100`/`kipup_fault_moderate_le_75`/`fault_cap_holds`/`score_determinism_cold`/`score_determinism_warm` 를 result JSON 에 박지 않았다. assert gate 가 재계산으로 검증하나, Task 1 (H) acceptance 는 harness 가 이 필드를 **산출**할 것을 요구.
- **Fix:** `compute_d14_gates` 추가 — elite final score 95~100 / kip-up severity==moderate AND score<=75 를 실제 final score 에서 산출해 top-level 박제. cold/warm 결정론은 단일 cold0 run 에서 trivially true(Pod 가 warm 반복 추가 시 byte-stable 비교로 채움).
- **Files modified:** `backend/research/spikes/eval_stillframe_veto.py`
- **Commit:** `98aa306`

## Pending — Task 3 (POD terminal, blocking-human)

Task 3 는 라이브 GPU·Gemini·실 영상이 필수인 `checkpoint:human-verify` `gate="blocking-human"` 다. **이 executor 는 Pod SSH/실측을 수행하지 않았다** — orchestrator 가 merge→push→Pod-pull→SSH-eval→assert→belle-judgment 순서를 상호작용으로 조율한다(Pod 생명주기 수동, Gemini 크레딧 확인 필요, 게이트는 belle 의 blocking-human 판정).

### orchestrator 가 Pod 에서 실행할 명령 시퀀스 (D-16 HIGH-1 + D-17 HIGH-1 워크플로)
선행 (로컬, push 전):
1. `eval_stillframe_veto_manifest.json` 의 `case.student_video`/`reference_video` 경로를 Pod 에서 접근 가능한 실 영상 경로로 확정(현재는 `~/Downloads/정은지 선수 추가 영상/...` placeholder — Pod S3/로컬 경로로 교체 후 commit).
2. (freeze) **clean worktree 에서** `cd backend && python3 research/spikes/freeze_stillframe_veto_manifest.py --manifest research/spikes/eval_stillframe_veto_manifest.json --created-at <ISO8601>` → `eval_stillframe_veto_manifest.lock.json` 생성.
3. lock.json + manifest + 23-01/02 코드 commit → **push** ([[gsd-pod-work-push-first]]).

Pod (SSH):
4. Pod 살아있는지 확인 + **Gemini 크레딧 잔량 확인** ([[gemini-credits-depleted-2026-06-20]]).
5. `git pull` 로 manifest+lock 포함 commit 받기 (측정 전 라벨 frozen·committed).
6. (eval) `PYTHONPATH=backend/shared/python:. python3 backend/research/spikes/eval_stillframe_veto.py --manifest backend/research/spikes/eval_stillframe_veto_manifest.json --out backend/research/spikes/reports/eval_stillframe_veto_phase23.json --created-at <ISO8601>` 순차 실행. harness 가 시작 시 lock∈ancestor(run HEAD)+worktree clean 을 강제하므로 freeze 전 실행은 거부됨.
7. (assert) `cd backend && python3 research/spikes/assert_stillframe_veto_gate.py --results research/spikes/reports/eval_stillframe_veto_phase23.json --manifest research/spikes/eval_stillframe_veto_manifest.json`. **exit 0 이어야만 JSON 수락.** assert 는 stdlib 만 써 Pod 에서 PyYAML 없이 실행.
8. result JSON 을 repo `backend/research/spikes/reports/eval_stillframe_veto_phase23.json` 로 commit.

### Pod 측정 전제 (prerequisites)
- Pod alive (RunPod GPU pod, NLF/Gemini wiring 준비).
- Gemini 크레딧 잔량 (sweep 중 429 고갈 위험).
- manifest case 영상 경로가 Pod 에서 접근 가능한 실 영상.

### belle 가 판정할 게이트 (assert report 기준 — raw JSON 아님)
- **recall (W2):** `arms.production_still.recall_set` ⊇ {왼팔, 오른팔, 고개·목} canonical FaultKey; 동일-모델 `arms.whole_video_baseline` 상체 recall = ∅/다리만.
- **특이도 (D-11/D-12 HIGH-2):** evaluable 분모(elite/imperfect clean/occluded/spinning)에서 false_positive_count=0 AND coverage_pass=true AND completion_pass=true. tempo-shifted 는 alignment abstention 카운트.
- **결정론·arm 격리:** determinism_cold/warm=true; 같은 case 내 whole_video_baseline cacheKey ≠ production_still cacheKey.
- **호출 소유권 (D-10 HIGH-1):** contextCollectedBeforeCoach=true + contextReusedForAudit=true + geminiCallCount=1.
- **Phase 20-04 흡수 (D-14):** elite_clean_score_in_95_100=true + kipup_fault_moderate_le_75=true(moderate/≤75) + score_determinism_cold/warm=true + eval18_discrimination_regression_count=0 (4쌍 margin>=min_margin).
- **assert gate exit 0** (run-commit ancestry / multi-arm shape / locked policy / FaultKey recall 전부 PASS).

회귀 시 → 23-01 또는 23-02 gap 으로 환류 (recall 미복구/위양성 증가/coverage 미달/completion 미달/결정론 깨짐/arm 캐시 누수/D-14 위반/assert 실패).

## Self-Check: PASSED

- SUMMARY file exists: `.planning/phases/23-mode-1-recall-still-frame-veto-dtw-key-frame/23-03-SUMMARY.md`
- Task 1/1b/2 commits found: d0bb49a, e9ccae4, d4ca1ce, 98aa306
- Created files exist: eval_stillframe_veto.py, eval_stillframe_veto_manifest.json, freeze_stillframe_veto_manifest.py, assert_stillframe_veto_gate.py, test_assert_stillframe_veto_gate.py
- Behavioral test: 14 passed (stdlib/pytest, no live Pod)
- freeze + assert + harness 전부 ast-parse + stdlib-only(PyYAML 0) 확인

---
*Phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame*
*Completed (Tasks 1/1b/2): 2026-06-23 — Task 3 POD terminal pending belle judgment*
