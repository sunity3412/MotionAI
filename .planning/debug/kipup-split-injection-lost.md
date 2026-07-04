---
status: awaiting_human_verify
trigger: "Phase 25 sweep FAIL 근본원인 #1: kip-up split_angle 감점 주입이 실경로에서 유실되는데 유닛테스트(실형상 왕복 포함)는 GREEN인 갭"
created: 2026-07-04T00:00:00+09:00
updated: 2026-07-04T21:30:00+09:00
---

## Current Focus

hypothesis: CONFIRMED — criteria_for_fault rule 1 inspects body_part only for _SPLIT_KEYWORDS; v10.1 Gemini output puts split vocabulary in fault_state, so no member routes to split_angle and belle-A vision injection never executes.
test: verbatim cache-doc fixture through _rich_from_doc → ctx → tally; assert md["split_angle"] injection (RED pre-fix, GREEN post-fix)
expecting: pre-fix md stays empty; post-fix md["split_angle"]==20.0
next_action: apply fix (combined check in rule 1) + verbatim-artifact regression test + full suite

reasoning_checkpoint:
  hypothesis: "criteria_for_fault rule 1 (_contains(body_part, _SPLIT_KEYWORDS)) never fires for kip-up v10.1 members because split tokens live only in fault_state — so split_angle is never activated and md['split_angle'] is never injected, yielding 99/100 instead of split deduction."
  confirming_evidence:
    - "Live Firestore cache doc 8c206887 (the exact Run 2 cache-hit input): all 5 member body_parts = 양다리/오른쪽 다리/왼쪽 무릎/오른쪽 무릎 — zero split tokens in body_part; '스플릿' present in fault_state of 2 members; approx_angle_deviation_deg=20 present on representative AND members (payload NOT missing — 87978fe targeted wrong link)."
    - "phase24 production-good artifact: body_part '양다리 (스플릿 각도)' contains the token → rule 1 fired, dev 30 → split record -12 → 88. Vocabulary drift came with PROMPT_VERSION v10.1."
    - "Observed Run 2 shape fully explained: members route to leg_extension (rule 3/8) → kip-up has no leg_extension md substrate → honest 0 → coverageGaps=[] and records=[left_shoulder only]."
  falsification_test: "Feed the verbatim cache doc through _rich_from_doc → VisionFaultContext → tally(md={}) on pre-fix code: if md['split_angle'] gets injected or a split record appears, hypothesis is wrong."
  fix_rationale: "Route split on combined (body_part + fault_state) — the fault description is where Gemini places the split vocabulary; criterion-selection stays a pure function of (body_part, fault_state, substrate), no motion-specific matching (generalization principle), no cache/prompt shape change (no version bump needed — cache stays valid), injection+inheritance seam untouched."
  blind_spots: "(1) split vocabulary only in correct_state/ipsf_note would still not route — deliberately excluded (ipsf_note boilerplate mentions 스플릿 for knee-bend members; including it would over-route). (2) Score on this exact cache stays 99: vision measured dev=20 == tol 20 → over 0 (transparent dead-zone). Return to 88-level requires dev>tol from Gemini — that variance is sweep root cause #2 (nondeterminism), separate track."

## Symptoms

expected: kip-up fault video scores 88 (split_angle deduction -12 injected from vision-measured split deviation, as in pre-phase25 production)
actual: Run 2 (87978fe): cold 99 (only left_shoulder silent), warm 100 (crit=[]). activatedCriteria has NO split_angle despite collectObservation having supportedFaultKeys=[{leg/line/pole_gap_or_bent, supportCount 3}], pointedJoints=[knees]
errors: none (silent loss)
reproduction: pod sweep Run 2 with 87978fe; artifacts at backend/evals/phase25/baseline/
started: Phase 25 Wave 1 (CR-01 member routing). 87978fe added parent-dev inheritance but real path still loses it. Run 2 was agg3 cache HIT (Run 1 stored cache with 7a598df = pre-inheritance code)

## Eliminated

- hypothesis: "A: ctx(VisionFaultContext) field drop strips _memberFaults/approx_angle_deviation_deg"
  evidence: _collect_vision_fault_context passes supported dicts through unmodified (list(rich.get(...))); tally reads them via _supported_differences getattr. No field filtering at ctx boundary.
  timestamp: 2026-07-04

## Evidence

- timestamp: 2026-07-04
  checked: phase25_sweep_report.json kip-up fault member (Run 2 cold, ground truth)
  found: rootCauseHypotheses[0] text = "양다리: 기준 영상에 비해 두 다리 사이의 벌어짐(스플릿) 각도가 눈에 띄게 좁으며, 무릎이 미세하게 굽어 있어..." → representative body_part = "양다리", 스플릿 keyword ONLY in fault_state. coverageGaps=[], records=[angle_vs_reference__left_shoulder only], final 99.
  implication: fold representative body_part contains NO split keyword.

- timestamp: 2026-07-04
  checked: phase24_sweep_report.json kip-up fault (production-good, 88)
  found: rootCauseHypotheses[0] text = "양다리 (스플릿 각도): 기준 영상 대비 다리 벌어짐 각도가 좁아..." → body_part = "양다리 (스플릿 각도)" CONTAINS "스플릿". split_angle record deviation 10, measuredValue 30 (dev 30, tol 20), source vision.
  implication: in production the split keyword was in body_part, so criteria_for_fault rule 1 (_contains(body_part, _SPLIT_KEYWORDS)) fired. Prompt v10.1 changed Gemini phrasing so split keyword moved to fault_state.

- timestamp: 2026-07-04
  checked: ipsf_criteria.criteria_for_fault rule 1 (line 313)
  found: rule 1 tests body_part ONLY against _SPLIT_KEYWORDS ("스플릿","split","스트래들","straddle"); fault_state is not consulted. Rule 3 (다리+굽 markers in combined) then routes such members to leg_extension, which has no md substrate for kip-up → honest 0.
  implication: representative-as-member ("양다리" + fault_state with 스플릿/굽어) demonstrably routes to leg_extension, not split_angle.

- timestamp: 2026-07-04
  checked: 87978fe test fixture _kipup_like_supported_via_rich_roundtrip
  found: fixture invents member body_part "다리 스플릿" (contains 스플릿) → rule 1 fires in test. Real v10.1 artifact shows body_part without split keyword.
  implication: hypothesis D confirmed as the test/real gap; underlying bug is routing (B-variant: keyword lives in fault_state, rule reads body_part only).

- timestamp: 2026-07-04
  checked: run_sweep.py activatedCriteria derivation
  found: activatedCriteria = criteria of EMITTED records only (bd.records). An activated-but-honest-0 criterion would not appear.
  implication: artifact alone cannot distinguish "never routed" vs "routed but no dev payload" — need cache doc members to confirm.

- timestamp: 2026-07-04
  checked: Firestore gemini_cache doc "vision_veto:8c206887...:v10.1:v7.0:agg3:whole_fanout:whole:n3" (Run 2 kip-up cache hit — root cause text byte-identical to sweep artifact)
  found: |
    Representative: body_part="양다리", fault_state="기준 영상에 비해 두 다리 사이의 벌어짐(스플릿) 각도가...", approx_angle_deviation_deg=20 (PRESENT). _memberFaults fully preserved (5 members, each with approx_angle_deviation_deg 10-20).
    Members: [양다리/스플릿-in-fault_state dev20], [오른쪽 다리/"...스플릿 각도가 좁게 형성됨" dev20], [왼쪽 무릎/굽어 dev10], [오른쪽 무릎/굽어 dev20], [왼쪽 무릎/굽어 dev10].
    NO member has any _SPLIT_KEYWORDS token ("스플릿","split","스트래들","straddle") in body_part. Split vocabulary appears ONLY in fault_state.
  implication: |
    Hypothesis A ELIMINATED (approx_angle_deviation_deg present on rep+members after cache roundtrip).
    Hypothesis C ELIMINATED (_memberFaults + all payload fields survive _rich_to_doc/_rich_from_doc).
    ROOT CAUSE = routing: criteria_for_fault rule 1 checks body_part ONLY; v10.1 Gemini phrasing moved split keyword into fault_state → no member routes to split_angle → all route to leg_extension (rule 3 or rule 8) which has no md substrate for kip-up → honest 0 → no injection → 99/100.
    87978fe inheritance fix was aimed at the wrong link (dev payload was never missing — routing never reached the injection branch). Its test invented body_part="다리 스플릿" which real output doesn't produce (hypothesis D).
  note_on_expected_score: Even with routing fixed, Run 2's vision-measured dev=20 == tol 20 → over 0 → no deduction (kip-up stays 99 on this cache). Score delta vs phase24's 88 (dev 30) is Gemini measurement nondeterminism = sweep root cause #2 (separate track). Fix restores the injection PATH (belle decision A), rule stays transparent.

## Resolution

root_cause: ipsf_criteria.criteria_for_fault rule 1 tests only body_part against _SPLIT_KEYWORDS; Gemini v10.1 output places split vocabulary in fault_state (body_part="양다리"/"오른쪽 다리") so split_angle is never routed and vision-measured deviation is never injected. 87978fe (parent dev inheritance) targeted a link that was never reached — the payload (approx_angle_deviation_deg=20) was present all along; routing never got there. Its test passed because the fixture invented body_part="다리 스플릿".
fix: rule 1 now tests combined (body_part + fault_state) against _SPLIT_KEYWORDS. correct_state/ipsf_note deliberately excluded (knee-bend members' ipsf_note boilerplate habitually mentions 스플릿 — would over-route). No AGGREGATION/PROMPT_VERSION bump — cache shape untouched, cache stays valid (cause was routing, not cache contamination; hypothesis C eliminated with live cache doc evidence).
verification: |
  - New regression tests use the VERBATIM Firestore cache doc (the exact doc Run 2 hit) as fixture via the real cache-hit path (_rich_from_doc → VisionFaultContext → tally). RED pre-fix (md['split_angle'] None — exact sweep failure), GREEN post-fix (md injected 20.0; final 99 reproduced byte-equal to artifact: dev 20 == tol 20 dead-zone, left_shoulder -0.7 only).
  - test_deduction_engine.py 54 passed; related suites (pipeline seam / scorer / phase25 gates / pointed mapper / seed merge) 192 passed.
  - Full suite FAILED+ERROR set with vs without fix: byte-identical (65 entries, all pre-existing env-dependent — 25-02/25-03 SUMMARY documented). Zero regression.
  - NOTE for pod re-sweep: on this exact cache, kip-up stays 99 because Gemini measured dev=20 (== tol). Restoration to ~88 requires dev>tol from Gemini (phase24 measured 30) — that variance is sweep root cause #2 (cold/warm nondeterminism), separate track. The belle-decision-A injection PATH is what this fix restores.
files_changed:
  - backend/shared/python/sunity_shared/analysis/ipsf_criteria.py
  - backend/tests/test_deduction_engine.py
  - backend/tests/fixtures/gemini_responses/phase25_kipup_agg3_rich_cache_doc.json
