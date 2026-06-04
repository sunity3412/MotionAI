# Phase 05-gemini Deferred Items

Out-of-scope discoveries during execution that should be addressed in a future plan.

## Plan 5-03 execution (2026-06-04)

**test_gemini_technique_recognizer.py::TestAdapterPromptHygiene::test_spike_prompt_template_clean** — pre-existing failure introduced by Plan 5-01 commit `b86fb0d`. Test imports `backend.research.spikes.spike_gemini_motion_classify` but `backend` is not a package (pytest invocation from `cd backend && pytest` has no `backend` parent in sys.path). Out of scope for Plan 5-03 (which does not touch test_gemini_technique_recognizer.py or spike modules).

Fix path: either (a) refactor import to use relative path from a discoverable package root, or (b) install backend as editable package in dev requirements. Both are Plan 5-01 follow-up territory, not a Plan 5-03 regression.

Verified untouched: `git diff HEAD -- backend/tests/test_gemini_technique_recognizer.py` = empty.

