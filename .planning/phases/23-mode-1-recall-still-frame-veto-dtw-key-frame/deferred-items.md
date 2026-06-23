# Deferred Items — Phase 23-02

Out-of-scope discoveries logged during 23-02 execution (not fixed — SCOPE BOUNDARY).

## Pre-existing test failures (NOT caused by 23-02)

`tests/test_pipeline_geminic_wiring.py` and `tests/test_pipeline_geminid_wiring.py`
have 14 failing tests on the 23-02 base (Task 4 HEAD) **before any Task 5 change**.
Confirmed by checking out the base `app.py`/coach writers and re-running — identical
14 failures. Root cause: the tests assert module-level attributes
(`hasattr(app, "find_scene_flags")`, `augment_low_confidence` import symbol) that the
current pipeline imports function-locally inside `_process` rather than at module scope.
This is unrelated to the vision-veto / quantification / coaching wiring 23-02 touches.

- Disposition: out of scope for 23-02. Track in a follow-up phase that owns the
  geminic/geminid wave-helper module surface.
