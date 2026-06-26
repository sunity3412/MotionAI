---
phase: 24-transparent-deduction-scoring
plan: 260626-f3u
subsystem: scoring / vision-veto (diagnostic instrumentation)
tags: [kip-up, alignment-gate, gemini-probe, diagnostic, observation-only, objectivity, pod-only]
requires: [24-04, 24-05, 24-06-DIRECTION]
provides: ["alignment 텔레메트리 collect/apply/audit 보존·방출", "sweep clip 별 visionVeto 캡처", "kip-up Gemini still-pair probe (pod-only)"]
affects: [backend/shared/python/sunity_shared/analysis/vision_veto.py, backend/functions/pipeline/app.py, backend/evals/phase24/run_sweep.py, backend/evals/phase24/probe_kip_up_gemini.py]
tech-stack:
  added: []
  patterns: ["순수 dict-shaping 헬퍼(새 import 0)", "monkeypatch capturing wrapper inline probe", "관찰 메타데이터 분기-밖 방출"]
key-files:
  created: [backend/evals/phase24/probe_kip_up_gemini.py]
  modified: [backend/shared/python/sunity_shared/analysis/vision_veto.py, backend/functions/pipeline/app.py, backend/tests/test_vision_veto.py, backend/evals/phase24/run_sweep.py]
decisions: ["alignment 진단은 관찰 전용 — score/tally 한 바이트도 불변", "probe 는 진단 출력만, 채점 경로 미주입(객관성)"]
metrics:
  duration: ~25m
  completed: 2026-06-26
---

# Phase 24 Plan 260626-f3u: (B) 진단 계측 — alignment 텔레메트리 + kip-up Gemini probe Summary

24-06 DIRECTION §3 이 옵션 선택(B1/B2/B3)의 선결 조건으로 지목한 두 미지수를 다음 pod-run 에서 캡처하도록, alignment 진단을 collect/apply/audit 3개 seam 에 보존·방출하고 kip-up still-pair Gemini probe 를 추가했다 — 채점/tally/score 출력은 한 바이트도 변하지 않는 순수 추가 관찰.

## What was built

**Task 1 — alignment 텔레메트리 보존·방출 (commit 335ed8f):**
- `vision_veto.alignment_summary(alignment) -> dict | None` 순수 헬퍼 — 빈 dict/None → None(audit 키 미방출), 채워진 dict → 관찰 키만 `{adoption, distance, visibility, localPathCount, refFramePresent}`. 새 import 0 (analysis core 순수성 보존).
- `to_audit_dict` 가 `collectionStatus` 직후 · `if final_status == "applied":` 분기 **이전**에 alignment 진단을 붙여 applied/not_applicable **양쪽** 방출.
- app.py `_collect_vision_fault_context` low_alignment bail 에 `alignment=alignment` 한 줄 보강 — 다른 adoption return 은 이미 넘기던 텔레메트리를 이 bail 만 drop 했었다.
- app.py `_apply_vision_veto_from_context` not_applicable early-return 이 `ctx.alignment` 요약을 직접 부착(to_audit_dict 미경유 직접 dict).
- 단위 테스트 3건 추가: `test_alignment_summary_observation_keys_only`, `test_to_audit_dict_emits_alignment_both_final_statuses`, `test_to_audit_dict_omits_alignment_when_empty`.

**Task 2 — eval-side 진단 계측 (commit 2761d79):**
- `run_sweep._run_member` 가 `vv = r.get("visionVeto")` 를 rec 에 캡처 + per-clip print 에 `vv={collectionStatus}/{alignment.adoption}` 토큰 추가.
- `backend/evals/phase24/probe_kip_up_gemini.py` 신설 — low_alignment bail 우회 capturing wrapper(monkeypatch)로 inline probe: selection→pair→alignment 를 bail 없이 재현 후 `gemini_vision_scorer.assess_fault_context` 를 app.py:1842 와 동일 시그니처로 호출. 출력 (a) alignment dict 전체 (b) Gemini status/verdict 유무 (c) support 게이트 통과 여부 (d) 각 difference body_part/fault_state (e) 명시 verdict 라인("Gemini CAN/CANNOT see kip-up fault from still-pair"). pod run command 도크스트링 박제, 객관성 명시.

## Verification (local gates)

| Gate | Result |
|---|---|
| `pytest test_vision_veto.py test_pipeline_deduction_seam.py test_deduction_engine.py -q` | **83 passed** |
| `pytest test_vision_veto.py test_pipeline_vision_gate.py -q` (Task 1 verify) | **70 passed** |
| 밴드 grep `apply_downward_cap\|SEVERITY_CAP\|capApplied` over shared/python + functions | **0** |
| ast-parse app.py / vision_veto.py / run_sweep.py / probe_kip_up_gemini.py | clean |
| probe grep `assess_fault_context` + `VETO_PART_SCOPES` | present |
| run_sweep grep `"visionVeto": vv` | present |

**Tally/score path byte-unchanged 확인:** Task 1 production diff(app.py)는 (1) bail `_ctx` 에 `alignment=` kwarg 추가 — `collection_status`/`cap_would_apply`(scoring/coach 게이트 입력) 불변, (2) not_applicable return 에 optional `alignment` audit sub-key 추가 — `**score_result`/`deductionBreakdown`/`overallScore` 불변. vision_veto.py 는 헬퍼 추가 + audit 분기-밖 metadata 방출만. scoring-logic 라인 변경 0(`git show` grep `tallyFinal|breakdown\.|overallScore|deduction_engine|.final` → 주석 1줄만 매치).

## Deviations from Plan

None - 플랜을 정확히 실행했다. 기존 `to_audit_dict` shape assert(test_vision_veto.py:341/367)는 `alignment={}` 라 무영향 — 조정 불필요.

## Pod-run readiness (24-06 §3 두 미지수)

다음 pod-run 1회(=(A) 검증 sweep + (B) 진단 캡처 묶음)에서:
1. **발화 조건** — sweep 리포트가 kip-up clip 의 `visionVeto.alignment.{distance, visibility, localPathCount}` 를 캡처 → distance>25 인지 visibility<0.35 인지 확정(B1/B3 갈림).
2. **Gemini 가시성** — `probe_kip_up_gemini.py` 가 still-pair 에서 Gemini 가 결함을 짚는지(support 게이트 통과) 확정.

probe/sweep/pod/GPU/Gemini/network 는 **로컬 미실행** — import-parse 만 검증.

## Self-Check: PASSED

- backend/evals/phase24/probe_kip_up_gemini.py — FOUND
- backend/shared/python/sunity_shared/analysis/vision_veto.py (alignment_summary) — FOUND
- commit 335ed8f — FOUND
- commit 2761d79 — FOUND
