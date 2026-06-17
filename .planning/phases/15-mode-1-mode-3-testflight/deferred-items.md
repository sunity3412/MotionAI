# Phase 15 — Deferred / Out-of-Scope Items

Logged during execution (Plan 15-01). These are pre-existing failures NOT caused by this
plan's changes — Plan 15-01 adds 3 import-only scripts under `backend/scripts/` that no test
in `backend/tests/` imports. Per the executor scope boundary rule, these are logged, not fixed.

## Pre-existing backend pytest failures (discovered 2026-06-17, Plan 15-01)

Verified unrelated to Plan 15-01: `grep -rl 'sweep_phase15|assert_falsepositive_gate|upload_phase15|phase15_keys' backend/tests/` returns nothing.

1. **`backend/tests/test_pole_detector.py` — collection ImportError**
   - `ModuleNotFoundError: No module named 'fixtures'` (line 21, `from fixtures.synthetic_frames import ...`).
   - Test-path/conftest issue (missing `backend/tests` on sys.path for the `fixtures` package). Pre-existing.

2. **`backend/tests/test_pipeline_geminid_wiring.py` — 4+ failures**
   - `assert hasattr(pipeline_app, "augment_low_confidence")` → False, plus related Gemini-D Wave 2 wiring asserts.
   - Pipeline Gemini-D symbol not present on current HEAD. Pre-existing, unrelated to Phase 15 tooling.

3. **`backend/tests/test_spike_gemini_moment_smoke.py` — failure(s)**
   - `TestReportOnlyMode::test_runs_when_labeled` and related. Pre-existing Gemini moment smoke breakage.

Aggregate at time of logging: `37 failed, 1858 passed, 13 skipped` (excluding the pole_detector
collection error). None touch `backend/scripts/` Phase 15 tooling.

Suggested owner: a separate quick/debug task for the Gemini-D wiring + test-path fix; not a
Phase 15 (validation-only) blocker.

## Cross-test pollution under broad `-k` (discovered 2026-06-17, Plan 15-04)

`pytest backend/tests -k "mode3 or assemble"` reports 3 FAILs:
- `test_pipeline_phase8.py::test_pipeline_phase8_mode3_force_signals_emitted`
- `test_pipeline_phase9.py::test_mode3_first_path_emits_mode3_first_context`
- `test_pipeline_phase9.py::test_mode3_progress_path_emits_mode3_progress_context`

NOT a regression — repo code unchanged by 15-04. These pass when run in isolation
(`pytest <file>::<test>` = PASS) and when the two files run together
(`pytest test_pipeline_phase8.py test_pipeline_phase9.py` = 16/16 PASS). The broad `-k`
selection collects tests across many files that mutate module-level singletons (pipeline
adapters / recognizer caches), so a cross-file test-ordering artifact surfaces only under the
wide selector. Suggested owner: a test-hygiene quick task to add per-test singleton reset
fixtures. Not a Phase 15 blocker.

## SCORE-04 all-low success-severity gate scope (discovered 2026-06-17, Plan 15-04 → Phase 18)

`assert_falsepositive_gate.py` success gate (all axis severity == 'low') is the 08.1 25/25-low
invariant measured on 정은지 **reference-motion** clips. Phase 15 success videos are 정은지
**student-practice success** clips whose real axis tilt exceeds 08.1 cutoffs in some phases
(e.g. pdshape sh/hip 90°, power-spin sh/hip 80-88°), so 4/6 success videos legitimately show
medium/high severity (NOT a 41-style false positive — lowest overall=55 reflects a real
detected deficit). Automated per-input-class severity gating (reference-motion vs
student-practice success) requires the labeled eval set → **deferred to Phase 18** alongside
the fail per-fault gate. Threshold NOT re-calibrated (D-02 / calibration-source-hard-gate;
yaml sha256 c94bb8 unchanged).

## pdshape/combo recognizer + line=None root cause (investigated 2026-06-17, belle-directed → follow-up phase)

belle directed a pause to investigate pdshape (Mode 1 line=None + Mode 3 success delta -28).
Confirmed ROOT CAUSE (not a code bug — pipeline runs crash-free, measurements objective):

1. **pdshape (and combo) are IPSF-UNREGISTERED academy combination moves** —
   `app/scripts/seed-reference-motions.mjs:386` explicitly: "정식 명칭 없는 연계 동작 …
   IPSF 미등재 (Inverted Torso Hook/Butterfly + Scorpio variation 결합)". No canonical
   joint-extension technique profile exists for them, so `joint_expectations={}` →
   `dimensions.line_score()` returns None (designed anti-false-positive omission).

2. **Mode 1 DOES pass a hint** `recognizer.motion_query_hint = "ref-pdshape"`
   (pipeline/app.py:1693-1699), but recognizer classification is driven by Gemini's OWN
   visual read (`raw_motion_name`, gemini_technique_recognizer.py:185,237), not the hint —
   the hint only biases key-moment extraction. So a known referenceMotionId does NOT force a
   registered profile.

3. **line=None on ALL 7 Mode-1 student videos** (not just pdshape) — Gemini does not
   confidently classify 정은지's *student-practice* clips into a registered scope. angle
   resolved 7/7; server_error 0. Recognizer-accuracy limitation on practice footage.

4. **pdshape Mode 3 -28** = fault doc `{stability:87}` vs success doc `{stability:59,angle:51}`;
   delta on common dim (stability) = 59-87. Success clip has a real extreme transition tilt
   (sh/hip 90° → stability 59). "success" file label != better absolute stability.

Follow-up phase scope (NOT Phase 15 — validation-only):
- Recognizer accuracy on student-practice footage (Phase 5 recognizer track).
- Author joint-extension profiles for IPSF-unregistered academy moves (pdshape/combo) OR a
  Mode-1 design change to derive student line expectation from the reference's techniqueProfile
  (since referenceMotionId is known in Mode 1). Note: unregistered refs have no extension
  profile either, so authoring is still required for pdshape/combo.
- Demo guidance: prefer IPSF-registered moves (climb/kip-up/peter-pan/power-spin/elbow) for
  expert-comparison demos; pdshape/combo line dimension unavailable until authored.
Related memory: [[studio-term-3branch-system]], [[terminology-multimap-future]].

## In-simulator verification findings (belle-driven, 2026-06-17)

belle drove a genuine in-app Mode 1 run in the iOS Simulator (Xcode 26, debug build off
local main incl. the expo-three removal fix). Results:
- Mode 1 wrong-video → correctly detected as far-from-reference. Mode 1 correct kip-up video
  → overallScore 98, coaching tip "정은지 선수와 거의 동일한 자세 / 관절각 일치도 99점".
  Score + coaching report + 보완운동 section render CORRECTLY in-app.
- **3D skeleton viewer (PoseViewer3D) renders BLANK in the Simulator** — header + controls
  (정면/측면/후면/위 + slider) show, but the 3D area is empty gray. Diagnosis: iOS Simulator
  expo-gl (~16.0.10) / react-three-fiber GL-render limitation, NOT a data or code bug:
  the section only renders when joints3d exists (joints.length===0 → return null), and a GL
  init failure would show the R8 ErrorBoundary fallback "3D 뷰어를 불러오지 못했어요" — neither
  occurred, so data is present and GL context initialized. The expo-three removal is NOT the
  cause (PoseViewer3D imports @react-three/fiber+drei, never expo-three; a break would throw
  to the fallback). **The skeleton must be verified on a real device (TestFlight build 20)** —
  the simulator cannot render it. This is now the primary real-device handoff item.

## UX follow-up: motion-name + supplementary-exercise naming intuitiveness (belle, 2026-06-17)

belle feedback: motion names (엘보 트위스트 시스터 / 폭스탑 / 콤보 — transliteration/jargon) and
supplementary-exercise English names (Farmer's Walk, Hand Grippers) are not intuitive; prefer
easier Korean descriptions. Out of Phase 15 (validation-only) scope → follow-up UX/terminology
phase. Connects to [[studio-term-3branch-system]] / [[terminology-multimap-future]].

## Mode 3 scoring-basis transparency + unknown-move validity gate (belle insight, 2026-06-17) — HIGH-VALUE follow-up

belle ran Mode 3 first-analysis (kip-up, score 97) and surfaced a core-value gap: the score
shows no explanation of its BASIS, and there is no branching by move-class. Confirmed in code:

- **Mode 3 (MODE_SELF) has NO unknown-move / validity gate.** The `not_pole_motion` safety
  gate (app.py:1812, `angle_dim < NOT_POLE_SIMILARITY_THRESHOLD`) lives ONLY inside the
  `mode == MODE_EXPERT` branch — it works by similarity to the 정은지 reference, so it cannot
  apply to MODE_SELF (which is reference-independent, app.py:1839). Therefore Mode 3 produces
  a confident absolute score (IPSF Page-9 absolute + line/stability/angle) for ANY video —
  including a move not in our data, or even a non-pole video. belle is right to doubt that a
  97 for an ungrounded move is trustworthy.
- **Score basis is not surfaced on the Mode-3 result screen.** assemble.py HAS branch-aware
  per-dimension copy ("IPSF 실행 기준 참고" vs "정은지 선수 기준"), but the headline
  (97 + "첫 분석이에요" + 입문/중급/고급 levels) does not tell the user what the score is
  grounded in or which case applies.

belle's target design (the right follow-up): classify the move, then branch the basis +
explanation + progress contract:
  1. IPSF-official move  → judge by IPSF criteria, explain that basis, then compare progress.
  2. Not IPSF but 정은지-reference → compare to 정은지, explain the basis, then progress.
  3. Neither (not in our data) → validity gate / uncertainty flag; do NOT emit a confident
     score as if grounded (today it emits 97 like cases 1/2).

This directly serves the core value (점수가 믿을 만해야 + 왜/무엇 제시). Scope = a dedicated
follow-up phase: Mode-3 move-classification routing + scoring-basis transparency UI +
unknown-move validity gate. Connects to [[ipsf-5-track-scoring]] (mode3 reference-free 채점 근거),
[[motion-routing-generalize-principle]] (새 동작 분기2 안전기본), [[studio-term-3branch-system]],
and the pdshape/combo IPSF-unregistered finding above.

## CRITICAL — score trustworthiness root cause (belle real-device test, 2026-06-17)

belle uploaded a 정은지 FAULT video (Mode 1) → overallScore 94, "정은지 선수와 관절각 89%
일치 — 거의 다 왔어요!", yet coaching tips listed 3 real deviations incl. 왼쪽 어깨 65°→36°
(29° off). This is the inverse of the 41-point false positive: a FAULT scores near-perfect.
Score does NOT reflect quality. Confirmed mechanism in code (NOT a tuning tweak — a design flaw):

- **overall = plain MEAN of dimensions** (`dimensions.overall_from_dimensions` = mean). For this
  result overall 94 = (angle 89 + stability 99)/2 (line absent — kip-up unrecognized).
- **angle dim = equal-weight MEAN over all joints** (`kismam.overall_score`, DEFAULT_WEIGHT all
  1.0). A few severe faults are diluted by many fine joints.
- **per-joint score = 100·exp(-½·(dev/20)²), tolerance 20° for ALL joints.** 20° dev → 61,
  29° → 35. Tolerance is loose; even a big joint error scores mid.
- **stability (99) inflates overall** — stability = tremor/jitter ("hold 구간 떨림 작음"), NOT
  correctness. A smooth fault scores 99 and pulls the average up.
- **coaching tips use top_issues (worst joints)** while the score AVERAGES them away → the
  세부점수-vs-코칭 contradiction belle saw is structural.

ROOT: the scoring philosophy is MEAN-based (faults dilute), the OPPOSITE of the project's
judging baseline IPSF Code of Points (DEDUCTION-based: faults deduct). [[judging-baseline-ipsf-code-of-points]]

Distinct workstreams for a dedicated score-trustworthiness rework phase:
A. Deduction/worst-fault-weighted aggregation (replace double-mean) aligned to IPSF.
B. Tighten/justify per-joint tolerance (20° too loose for elite/expert comparison).
C. Separate stability from the quality headline (smooth ≠ correct; don't let it inflate overall).
D. Headline copy: "거의 다 왔어요" must not fire on a fault.
E. Measurement accuracy: belle saw right shoulder visually identical to 정은지 yet flagged
   (171°→152°) — verify 3D angle measurement vs reality (separate from aggregation).
F. Start-point/timing alignment (belle): same move, different start → analyze from the
   posture-alignment point; for expert compare, give a FILMING TIP (watch expert first, match
   start point). Check DTW alignment behavior.
G. 입문/중급/고급 level UI feels crude (single-select) — UX.
H. 3D skeleton viewer BLANK on REAL DEVICE (not just simulator — prior sim-limitation hypothesis
   was WRONG). Header+controls render, 3D empty. Real bug — investigate joints3d render on device.

This supersedes the "Phase 15 validation passed" framing: the automated sweeps deferred
fault-detection to Phase 18 and never checked score-vs-quality, so they gave false confidence.

## Deep investigation results (3 parallel agents, 2026-06-17) — evidence confirmed

### E. Measurement / display artifact (right shoulder "171°→152°" visually-identical-yet-flagged) — CONFIRMED
- Shoulder angle = 3D vector angle (elbow→shoulder, hip→shoulder), arm-to-torso elevation
  (skeleton.py:42-43, features.py:22-55). Geometrically valid, camera/translation invariant —
  NOT a projection/mirror bug.
- MISLABELED "안정성": COACHING_FOCUS hardcodes shoulder→"안정성" (kismam.py:53-62), but the
  value is a STATIC POSE ANGLE, not stability/wobble (there is a separate real DIM_STABILITY).
  Genuine labeling artifact (locked by a 2026-06-06 screenshot note).
- ROOT of "visually identical yet flagged 19°": the DISPLAYED "현재/기준" angles come from
  plain whole-clip np.nanmean (_angles_to_mean_dict, app.py:1515-1538), NOT the DTW-aligned
  MEDIAN that drives the score (motiondtw.py:103-130). Worse, NOT apples-to-apples: user side =
  mean over the DTW-MATCHED sub-window (user_seg), reference side = mean over the ENTIRE
  reference clip (a_ref, app.py:1800-1801). Mismatched temporal extents + mean (jitter/occlusion
  sensitive) → multi-degree gap even when the held pose is visually identical. The display path
  still uses the very mean-vs-median footgun the score path already abandoned (motiondtw.py:108-119).

### F. DTW alignment (belle: "find the alignment point first") — ALREADY IMPLEMENTED
- find_action_segment (motiondtw.py:80-91) searches all start offsets → min-distance window =
  exactly "find where postures align, then compare." Then banded DTW warps (radius 12, global
  fallback motiondtw.py:52-54). Score = DTW-aligned per-joint MEDIAN deviation. Whole-clip means
  are display-only. Start-point + duration mismatch handled.
- BUT residual bias is the OPPOSITE of belle's fear: DTW over-eager alignment seeks the most
  favorable match → tends to INFLATE similarity (a contributor to fault-scores-high #1).
- Filming-tip (watch expert first, match start point) still valuable as UX, but alignment itself
  is not the bug. find_action_segment offset granularity is coarse (~60 windows) — minor.

### H. 3D skeleton BLANK on real device — CONFIRMED BUG (coordinate scale/centering), NOT expo-three
- joints3d is stored in RAW RTMW PIXEL coords (x,y ~0-640 uncentered; z MotionBert-scale) —
  only rotated (pole_aligned), never recentered/rescaled (app.py:2328-2337,
  rtmw_133_to_coco17.py:247-256, lifter_pipeline.py:288 "keypoints_3d xy = RTMW 픽셀 좌표").
- Viewer camera is at distance 3, fov 50, sphere r=0.04 — expects NORMALIZED origin-centered
  coords (PoseViewer3D.tsx:51-56,157-158,346-350). Real skeleton centers ~(320,240,z) with
  hundreds of units spread → entirely outside the camera frustum → GL clears to #F5F5F5 = blank
  gray. Section header/buttons/slider are plain RN → still render.
- The smoke screen "worked" because it used hand-authored normalized coords [-0.4,1.0]
  (PoseViewer3DSmokeScreen.tsx:69-84). Real data ~100-1000× larger → blank.
- expo-three removal NOT implicated (verified: fiber/native imports expo-gl not expo-three;
  bug predates the removal). Fix = recenter (subtract hip midpoint) + normalize (÷ torso length)
  before render, in reshapePose3dData (app/src/lib/joints.ts) or a <group> transform.
