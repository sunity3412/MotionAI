---
phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame
plan: 02
subsystem: api
tags: [gemini-vision, vision-veto, quantification, body-relative-notch, dual-coach, root-cause, mode1]

# Dependency graph
requires:
  - phase: 23-01
    provides: collect/apply 2-function seam, VisionFaultContext/VisionQuantificationResult/SelectedFramePair typed owners, _build_vision_quantification_result named seam, cap_would_apply pre-coach computation, FaultKey/RootCauseHypothesis, _derive_root_causes_from_supported_differences support gate
  - phase: 20-mode-1-vision-veto
    provides: apply_downward_cap (downward-only invariant), VisionVerdict, _COMPARISON_PROMPT, VisionVetoCache
provides:
  - frame-specific per-joint 각도 (features.frame_pair_angle_deltas) + window median 분리 (window_median_angle_deltas)
  - 결정적 칸/층 기하 (vision_veto.body_relative_notches) + FramePairMeasurementContext same-frame 계약
  - build_quantification_result (frame-specific 각도 + 칸 → VisionQuantificationResult, 결측 시 unavailable)
  - build_schema root_cause_hypothesis + source provenance DESCRIPTIVE 필드 (score-free, percent-free)
  - to_audit_dict 가 rootCauseHypotheses + angleDeltas/bodyRelativeNotches/windowMedianAngleDeltas 직렬화 (applied, quantificationStatus 필수)
  - collect-before-coach 라이브 파이프라인 배선 (eligible_for_coach 게이트, geminiCallCount=1)
  - 양쪽 coach writer(Cerebras/Gemini)가 to_coach_context()의 visionFault root-cause 를 프롬프트 causes 에 실제 렌더
  - 3-way 정량화 audit 계약 (models.py VISION_VETO_KEYS + analysis.ts VisionVeto + contract.md §4)
affects: [23-03, future-quantification-ui-phase]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "frame-specific 표시 각도 = verdict 프레임 쌍(user/ref_frame_idx) 행 값만; DTW window median 은 별도 키(windowMedianAngleDeltas) (D-10 HIGH-3)"
    - "칸/층 = keypoint + baseline(floor/pole_vertical/hip_line) 결정적 기하 — Gemini 미산출, source=geometry (D-08 H2)"
    - "geometry 는 VisionQuantificationResult(post-geometry) 소유; apply 의 final cap 후 to_audit_dict(quantification=) 로만 audit 주입 (D-12 HIGH-1)"
    - "coach root-cause 주입 게이트 = eligible_for_coach(collection_status==candidate_verdict AND cap_would_apply); writer 양쪽이 visionFault 키를 프롬프트에 실제 렌더 (graceful 무시 아님)"

key-files:
  created:
    - backend/tests/test_coach_writer.py
  modified:
    - backend/shared/python/sunity_shared/analysis/features.py
    - backend/shared/python/sunity_shared/analysis/vision_veto.py
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/shared/python/sunity_shared/analysis/coach_writer.py
    - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/models.py
    - app/src/types/analysis.ts
    - docs/contract.md

key-decisions:
  - "baseline_kind 기본 hip_line — 엉덩이중점 baseline 은 floor_y/pole_line 입력 없이 keypoint 만으로 결정적 산출 가능(공중 동작 다수). floor/pole_vertical 은 입력 있을 때만"
  - "칸 reach keypoint = left/right_hand(=손목 proxy) + left/right_knee; torso(어깨중점↔엉덩이중점) 길이를 1칸 보조 단위로 정규화 (체형 차이 흡수)"
  - "칸 분수 = ⅓ 단위 양자화 (정수 또는 ⅓/⅔ 분수 칸), percent 절대 0"
  - "_build_vision_quantification_result 가 SelectedFramePair → FramePairMeasurementContext 구성 후 build_quantification_result 호출; keypoint 가 ndarray 로 강제 불가하면 graceful unavailable"

patterns-established:
  - "vision_veto.py downward-only invariant 보존 (apply_downward_cap 본체 미변경, max() 재도입 0)"
  - "정량화 산출 실패는 crash·강등 없이 quantificationStatus=unavailable (applied 유지, root-cause/capApplied 보존)"

requirements-completed: [VETO-04, VETO-05]

# Metrics
duration: ~95min
completed: 2026-06-23
---

# Phase 23 Plan 02: 기준선 정량화 레이어 + 증상→root-cause 묶음 코칭 Summary

**결함 출력에 frame-specific 관절각 직접 수치(무릎 145° vs 178°)와 keypoint+baseline 결정적 칸/층(정은지 3칸/너 2칸 ⅔)을 백엔드에서 산출·저장하고, support-gated root-cause 가설을 collect-before-coach 배선으로 양쪽 coach writer 의 detail2.causes 에 실제 생성한다 (verdict Gemini 호출 1회, score-free·percent-free).**

## Performance

- **Duration:** ~95 min (resume — Task 1 was pre-committed)
- **Tasks:** 5 (all TDD); Tasks 2-5 executed this session, Task 1 inherited from base
- **Files modified:** 9 (+1 created: test_coach_writer.py)
- **Tests:** 159 passing across the plan suite (test_features, test_vision_veto, test_gemini_vision_scorer, test_pipeline_vision_gate, test_coach_writer, gemini/test_coach_writer_v2); app `tsc --noEmit` clean

## Accomplishments

- **Task 1 (inherited, base commit 3bcd8bd):** `features.frame_pair_angle_deltas` computes per-joint display angles from a single user_frame_idx/ref_frame_idx row pair only (frame-specific, not DTW median); `window_median_angle_deltas` keeps the robustness median behind a separately-named field with sourceFrameIndices/windowPolicy so a window median is never mistaken for a still-frame exact angle (D-10 HIGH-3). NaN-guarded, angle-only (no cm/px/percent).
- **Task 2:** `body_relative_notches` produces deterministic integer/⅓-fraction notches from keypoints + a motion-context baseline (floor / pole_vertical / hip_line) with `source='geometry'` — Gemini never fabricates notches (H2), percent always 0 (D-08). `FramePairMeasurementContext` enforces the same-frame contract (verdict frame pair only). `build_quantification_result` packs frame-specific angles (Task 1) + notches into a `VisionQuantificationResult`, returning `unavailable` (no crash, no demotion) on missing per-frame inputs.
- **Task 3:** `build_schema` gains `root_cause_hypothesis` + `source` (geometry|vision_hypothesis) DESCRIPTIVE fields on each difference (score-free, percent-free, no notch-output field — code computes notches). `_COMPARISON_PROMPT` adds a generic "~로 보임" root-cause hypothesis instruction + explicit cm/m·notch·percent prohibition. PROMPT_VERSION v9.0 / SCHEMA_VERSION v7.0 (cache invalidation). `_parse_verdict` passes the new fields through descriptively.
- **Task 4:** `to_audit_dict` now serializes `rootCauseHypotheses` (support-gated) + `windowMedianAngleDeltas` (separate key) alongside `angleDeltas`/`bodyRelativeNotches`; `quantificationStatus` is mandatory on applied audit, and `unavailable` preserves `status='applied'`+`capApplied`+root-cause while omitting geometry (no demotion). 3-way lockstep: `models.VISION_VETO_KEYS` + `analysis.ts VisionVeto` applied branch (score-free DESCRIPTIVE types + `never` on other branches) + `contract.md §4`.
- **Task 5:** Live pipeline now runs `overall → collect → coach → build_result → _build_vision_quantification_result → apply`. `_collect_vision_fault_context` is called right after `overall` and before `_build_coach_context`; root-cause is injected into coach context **only when `eligible_for_coach`** (candidate_verdict AND cap_would_apply). Both Cerebras and Gemini writers explicitly read `context['visionFault']` and render the root-cause into their prompt causes section (the BLOCKER fix — proven at the prompt-building stage, not the assembled tip). The named seam now produces real geometry; the same `VisionFaultContext` is reused at apply (geminiCallCount=1).

## Task Commits

1. **Task 1: frame-specific 표시 각도 + window median 분리** - `3bcd8bd` (feat) — inherited (base)
2. **Task 2: 결정적 칸/층 기하 + FramePairMeasurementContext + VisionQuantificationResult** - `9d06de0` (feat)
3. **Task 3: build_schema 원인 가설 + source provenance + 비교 프롬프트** - `bc80b73` (feat)
4. **Task 4: 정량화 audit attach (to_audit_dict) + 3-way lockstep** - `90dbf43` (feat)
5. **Task 5: collect-before-coach 배선 + 양쪽 writer visionFault 소비 + 순서** - `7b11075` (feat)

_Note: each TDD task is a single feat commit containing the failing tests and the implementation that makes them pass (RED→GREEN within the task)._

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/features.py` - (Task 1) `frame_pair_angle_deltas`, `window_median_angle_deltas`
- `backend/shared/python/sunity_shared/analysis/vision_veto.py` - (Task 2/4) `FramePairMeasurementContext`, `body_relative_notches`, `build_quantification_result`, `_kp_xy`/`_baseline_unit_length`/`_reach_to_baseline`/`_quantize_notches`; `to_audit_dict` rootCause + windowMedian serialization
- `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` - (Task 3) `root_cause_hypothesis` + `source` schema fields, `_COMPARISON_PROMPT` rules 8-10, version bumps
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` - (Task 5) `_format_vision_fault_lines` + `_build_prompt(vision_fault=)` causes injection + `write` passthrough
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` - (Task 5) same vision-fault prompt injection for the Gemini writer
- `backend/functions/pipeline/app.py` - (Task 5) collect-before-coach wiring, eligible-gate injection, build_result→quantification→apply ordering; `_build_vision_quantification_result` now produces real geometry
- `backend/shared/python/sunity_shared/models.py` - (Task 4) VISION_VETO_KEYS += quantification fields + contract comment
- `app/src/types/analysis.ts` - (Task 4) VisionVeto applied branch + VisionAngleDelta/VisionBodyRelativeNotch/VisionWindowMedianAngleDeltas/VisionRootCauseHypothesis interfaces
- `docs/contract.md` - (Task 4) §4 quantification field definitions
- `backend/tests/test_coach_writer.py` - (Task 5, NEW) Cerebras prompt-building verification

## Decisions Made

- `baseline_kind` defaults to `hip_line` in the pipeline seam because the hip-midpoint baseline is deterministic from keypoints alone (no floor_y / pole_line dependency), making quantification available for the common aerial-move case without extra inputs. floor/pole_vertical remain available when the caller supplies floor_y/pole_line.
- Notch reach keypoints map `left/right_hand`→`left/right_wrist` (visual proxy, consistent with the existing `fault_joints` mapping) so the COCO-17 array resolves; torso length (shoulder-mid↔hip-mid) is the per-body 1-notch unit to normalize physique differences while keeping the output in notches.
- The named quantification seam constructs `FramePairMeasurementContext` from the `SelectedFramePair` and calls `build_quantification_result`; if the pipeline's keypoints aren't coercible to an `(K,2)` ndarray, the seam degrades gracefully to `unavailable` rather than crashing (the safe behavior — polished-but-wrong numbers are worse than absent ones).

## Deviations from Plan

None - plan executed exactly as written. All five task contracts were implemented as specified; no auto-fix rules (1-3) were triggered and no architectural checkpoints (Rule 4) were needed. Version-pinning tests for PROMPT_VERSION/SCHEMA_VERSION were updated in lockstep with the intentional Task 3 bump (that is the task's own change, not a deviation).

## Issues Encountered

- **Worktree file paths:** This agent runs in a git worktree; the initial reads resolved against the main checkout. Switched all Edit/Write operations to the worktree-relative paths and used the worktree's absolute path for Bash.
- **`python` not on PATH:** the worktree shell only has `python3`; used `python3 -m pytest` throughout.
- **App typecheck has no node_modules in the worktree:** symlinked the main repo's gitignored `node_modules` for the duration of `npm run typecheck`, then removed the symlink (exit 0, clean) — same approach noted in the 23-01 summary.
- **Notch override keyname:** the first Task 2 test used `left_hand` directly as a COCO override (not a valid COCO key). Fixed `_kp_xy` to alias `left/right_hand`→`left/right_wrist` and corrected the test override to `left_wrist`.
- **Pre-existing geminic/geminid wiring failures:** `tests/test_pipeline_geminic_wiring.py` + `tests/test_pipeline_geminid_wiring.py` have 14 failures on the 23-02 base (Task 4 HEAD) **before any Task 5 change** — confirmed by reverting app.py/coach writers to base and re-running (identical 14 failures). They assert module-level attributes (`find_scene_flags`, `augment_low_confidence`) that the pipeline imports function-locally. Out of scope; logged to `deferred-items.md`. The dual-coach signature regression (`test_pipeline_geminib_wiring.py`) passes — both writers kept the `write(context: dict)` signature.

## User Setup Required

None - no external service configuration required. (Gemini API key + Pod env injection are pre-existing Phase 20 dependencies. The prompt/schema version bump invalidates the vision-veto cache automatically — no manual cache flush needed.)

## Next Phase Readiness

- The still-frame collect→coach→build_result→quantification→apply ordering is now wired into the live pipeline body — the still-frame veto path runs in production (the 23-01 blocker is resolved). 23-03 recall matching can consume `to_trace_dict` fault-key vocabulary and the now-live verdict path unchanged.
- Quantification geometry is computed and stored in the visionVeto audit (frame-specific angles + deterministic notches + root-cause). A follow-up UI phase can render these from the audit; the existing `CoachingTipDetailModal` already surfaces `detail2.causes` (auto-display, no UI change), so root-cause coaching reaches the user without new render components (S2 boundary honored — `result.tsx`/coach-report render components/`fault_zoom.py` are 0-diff).
- Objectivity hard gate intact: no score/0-100/percent fields anywhere (build_schema, VisionVerdict, visionVeto audit, TS union); downward-only cap invariant unchanged.

## Self-Check: PASSED

- SUMMARY file exists: `.planning/phases/23-mode-1-recall-still-frame-veto-dtw-key-frame/23-02-SUMMARY.md`
- All key files found: features.py, vision_veto.py, gemini_vision_scorer.py, coach_writer.py, coach_writer_v2.py, app.py, models.py, analysis.ts, contract.md, test_coach_writer.py
- All task commits found: 3bcd8bd (Task 1, inherited), 9d06de0, bc80b73, 90dbf43, 7b11075
- Plan suite: 159 passing; app `tsc --noEmit` exit 0

---
*Phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame*
*Completed: 2026-06-23*
