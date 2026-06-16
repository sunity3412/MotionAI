# Phase 13 Deferred Items

Out-of-scope discoveries during execution. Not fixed by the executor (SCOPE BOUNDARY).

## Pre-existing test failure (out of scope for Plan 13-A)

- **`backend/tests/phase08/test_gemini_model_env_driven.py::test_gemini_moment_extractor_default_is_non_eol`**
  - Status: FAILING on base commit (unrelated to Plan 13-A changes).
  - Cause: quick-task `260615-cxe` set the Gemini moment-extractor default to `gemini-2.5-pro`,
    but this phase08 test asserts the default must be a non-EOL model and rejects `gemini-2.5-pro`
    (memory `gemini-latest-model-versions` bans 2.5; recommended Pro = `gemini-3.1-pro-preview`).
  - Not touched by Plan 13-A (corrective exercises) — no Gemini model edits in this plan.
  - Suggested follow-up: align the moment-extractor default with the non-EOL model policy
    (`gemini-3.1-pro-preview`) or update the test/quick-task decision. Owner: belle.
