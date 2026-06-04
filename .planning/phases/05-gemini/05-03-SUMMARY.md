---
phase: 05-gemini
plan: "03"
status: complete
wave: 2
completed_at: 2026-06-04
duration_seconds: 330
subsystem: backend
tags: [pipeline, env-switch, lazy-import, recognizer-swap, tdd]
requirements:
  - SCORE-01
dependency_graph:
  requires:
    - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py (Plan 5-01 산출물)
    - backend/shared/python/sunity_shared/analysis/technique_cache.py (Plan 5-02 산출물)
    - backend/shared/python/sunity_shared/firestore_admin.py — record_unregistered_keyword helper (Plan 5-02)
    - backend/shared/python/sunity_shared/analysis/technique.py — FallbackRecognizer + Protocol (기존 박제)
    - backend/runpod_inference/server.py — D-12 무수정 1pass 박제 (검증 대상)
  provides:
    - backend/functions/pipeline/app.py — env switch + _ensure_recognizer + _angles_and_video_path_from_video (Plan 5-04 Pod 의존성 + Plan 5-05 sweep 진입점)
    - GEMINI_RECOGNIZER_ENABLED / RECOGNIZER_BACKEND env switch contract
  affects:
    - Plan 5-04 (Pod requirements + setup.sh) — env var 정합 + 5-01/5-02 의존성 install path
    - Plan 5-05 (5영상 sweep 재실행) — RECOGNIZER_BACKEND=gemini 박제로 자동 활성
    - Plan 5-06 이상 (Lambda env var 동기화) — 운영 배포 시 env 박제 path
tech_stack:
  added: []  # 신규 install 0 (stdlib threading + pathlib 재사용)
  patterns:
    - 즉시 생성 → lazy creation 전환 박제 (D-16 정합)
    - double-checked locking (threading.Lock) — Pod 다중 SQS 메시지 동시 진입 보호
    - env switch case-insensitive truthy set (frozenset) — alias 박제
    - 별 helper 함수 신설 path — 기존 시그너처 무변경 (B8 fix)
    - try/finally tempfile cleanup — caller 책임 (delete=False NamedTemporaryFile)
key_files:
  created:
    - backend/tests/test_pipeline_recognizer_switch.py (250 lines, 13 unit tests)
    - backend/tests/test_pipeline_gemini_integration.py (410 lines, 4 integration tests)
  modified:
    - backend/functions/pipeline/app.py (+141 lines net; 420 → 507)
decisions:
  - "_RECOGNIZER 즉시 생성 → None + _RECOGNIZER_LOCK 박제 — D-16 lazy import 정합 (Gemini SDK / firebase_admin 모듈 로드 시점 0)"
  - "env switch 박제 truthy set = {'1','true','on','yes','gemini'} case-insensitive — alias 호환 (GEMINI_RECOGNIZER_ENABLED + RECOGNIZER_BACKEND 둘 다 인식)"
  - "default = FallbackRecognizer — 회귀 위험 최소 + A/B 비교 가능 (env 미설정 path 박제 보존)"
  - "B8 fix — _angles_from_video 시그너처 무변경 + 별 helper _angles_and_video_path_from_video 신설 (RunPod server.py D-12 무수정 박제 정합)"
  - "_process 안 try/finally — Gemini path local_video_path unlink (T-05-03-02 디스크 누수 방지)"
  - "unregistered_hook uid='anonymous-pipeline' 박제 — _ensure_recognizer 시점엔 uid 미상 (Pod 가 호출 시점에만 알음). 향후 hook 시그너처에 uid 주입 path 별 plan 책임"
metrics:
  tasks_completed: 2
  commits: 3  # RED + GREEN (Task 1) + integration tests (Task 2)
  tests_added: 17  # 13 unit + 4 integration
  tests_passed: 17
  lines_created: 660  # 250 + 410
  lines_modified: 141  # pipeline/app.py net 추가
---

# Phase 5 Plan 03: pipeline _RECOGNIZER lazy swap + env switch wiring Summary

Wave 1 산출물 (Plan 5-01 GeminiTechniqueRecognizer 어댑터 + Plan 5-02 TechniqueCache + firestore_admin helpers) 을 pipeline 본체에 wiring. env switch 박제로 A/B 비교 가능. RunPod server.py 무수정 — pipeline 모듈 import 만으로 자동 작동 (D-12 박제 정신).

## 박제 정신

Plan 5-03 = D-12 (RunPod server.py 무수정 1pass) + D-16 (lazy import) + D-09 case 3 (unregistered_hook wiring) + B8 fix (시그너처 무변경 회귀 보호) 박제. 박제 정신 의존 (memory):

- [[gsd-pod-work-push-first]] — pipeline 변경 후 commit 박제 (push 는 worktree 머지 후)
- [[feedback-analysis-first.md]] — env switch A/B 비교 가능 박제 → Gemini 도입 정확도 검증 path 열림
- [[mvp-simple-pilot-quality.md]] — "구조만 열어두기" → env switch 박제로 시연 직전 빠른 ON/OFF
- [[analysis-objectivity-no-human-scores]] — GeminiTechniqueRecognizer 의 reject patterns 2차 가드는 Plan 5-01 박제 (본 plan 은 wiring 만)

## Task 박제 흐름

### Task 1 — pipeline/app.py _RECOGNIZER lazy swap + env switch + B8 fix helper (RED `221e1e1` + GREEN `b0d203c`)

`backend/functions/pipeline/app.py` 박제 갱신 4 건:

**변경 1** — `_RECOGNIZER` 박제 갱신 (lines ~117-130):
- 즉시 생성 박제 X → `None` + `_RECOGNIZER_LOCK = threading.Lock()`
- 박제 사유 주석 — D-12 / D-16 / Plan 5-03 인용
- env switch 박제 값 frozenset `_GEMINI_ENV_TRUTHY = {"1", "true", "on", "yes", "gemini"}`

**변경 2** — 신설 함수 2개:
- `_gemini_enabled() -> bool` — env switch 체크 (case-insensitive). 두 env var 박제 (`GEMINI_RECOGNIZER_ENABLED`, `RECOGNIZER_BACKEND`). 미설정 / 다른 값 = False (회귀 0).
- `_ensure_recognizer() -> technique.TechniqueRecognizer` — lazy creation + double-checked locking. Gemini 선택 시:
  - lazy import (`from sunity_shared.analysis.gemini_technique_recognizer import GeminiTechniqueRecognizer`)
  - `TechniqueCache()` 자동 생성
  - `record_unregistered_keyword` hook 합성 (uid="anonymous-pipeline" 박제)
  - 로그 박제: `Recognizer = GeminiTechniqueRecognizer (env switch ON)` / `Recognizer = Fallback (env switch OFF — default)`

**변경 3** — `_angles_and_video_path_from_video(bucket, key) -> tuple[np.ndarray, str]` 신설 (B8 fix):
- `delete=False` `tempfile.NamedTemporaryFile` 박제 — caller (`_process` Gemini 분기) 가 finally 에서 unlink 책임
- 기존 `_angles_from_video` 시그너처 무변경 유지 — 호출처 갱신 0, RunPod server.py D-12 무수정 박제 정합

**변경 4** — `_process` 안 분기 박제 (lines ~340-456):
- `recognizer = _ensure_recognizer()`
- env switch ON → `angles, local_video_path = _angles_and_video_path_from_video(bucket, key)`
- env switch OFF → `angles = _angles_from_video(bucket, key)` (회귀 0)
- `profile = recognizer.recognize(angles, frames=local_video_path)` — Gemini 어댑터는 frames 사용, Fallback 은 ignore (Protocol 정합)
- `try/finally` 박제 — `Path(local_video_path).unlink(missing_ok=True)` (T-05-03-02 디스크 누수 방지)

**Task 1 단위 테스트 13개 PASS** (plan acceptance criteria ≥ 11):
- `TestEnvSwitch` (5): default fallback / `RECOGNIZER_BACKEND=gemini` / `GEMINI_RECOGNIZER_ENABLED=1` alias / case-insensitive (`TRUE`) / 멱등 (2회 호출 = 같은 instance)
- `TestLazyImport` (2): pipeline 모듈 import 시 `google.genai` / `google.generativeai` 미import + `firebase_admin` 미import (D-16 검증)
- `TestProtocolCompat` (2): `FallbackRecognizer.recognize(angles, frames=None)` + `frames='/tmp/x.mp4'` ignore 정합
- `TestGeminiComposition` (2): `cache` 인스턴스 = `TechniqueCache` + `unregistered_hook` callable
- `TestB8FixSignature` (2): `_angles_from_video` 시그너처 = `(bucket, key) -> np.ndarray` 무변경 + helper 신설 박제 (`(bucket, key) -> tuple`)

### Task 2 — _process 흐름 통합 테스트 (mock-based) (commit `31391b9`)

`backend/tests/test_pipeline_gemini_integration.py` 신설 (410 lines, 4 통합 테스트):

- **test_process_with_gemini_recognizer_uses_gemini** — env `RECOGNIZER_BACKEND=gemini` + mock `_StubExtractor` → `_process` 흐름 → `extract_key_moments` 1회 호출 검증 박제. cache=None 박제로 Firestore 호출 우회.
- **test_process_without_env_uses_fallback** — env 미설정 → FallbackRecognizer + Gemini SDK 호출 0 (회귀 검증 박제). sentinel flag 박제로 import 검증.
- **test_gemini_api_failure_falls_back_to_fallback** — Gemini `RuntimeError("Gemini quota exceeded")` → captured `profile.category == "api_failure"` (D-09 case 1 박제 정합). 분석 흐름 crash 0 — `dimensions.absolute_dimension_scores` 가 정상 호출됨.
- **test_tempfile_cleanup** — Gemini path `_angles_and_video_path_from_video` 가 실제 임시 파일 생성 → `_process` 종료 후 `fake_video.exists() == False` 검증 (T-05-03-02 박제).

박제 mocks:
- `firestore_admin.get_analysis` → `{"mode": MODE_SELF}` (Mode 3 박제, prev 없음 = 첫 분석)
- `firestore_admin.update_analysis_status / get_previous_analysis / complete_analysis` → no-op
- `_signed_get` → fake URL
- `_COACH_WRITER` → MagicMock (write returns dict)
- `_ensure_adapters` → no-op (어댑터 초기화 skip)
- `_angles_and_video_path_from_video` → factory stub (실제 파일 생성 박제 cleanup 검증용)

`_StubExtractor` 박제 패턴 — `test_gemini_technique_recognizer.py` 박제 정합 (Plan 5-01).

## env switch 박제 contract

| env var                         | 값                                | 결과                          |
|---------------------------------|-----------------------------------|-------------------------------|
| (미설정)                        | —                                 | FallbackRecognizer (회귀 0)   |
| `GEMINI_RECOGNIZER_ENABLED`     | `1` / `true` / `TRUE` / `on` / `yes` / `gemini` | GeminiTechniqueRecognizer |
| `RECOGNIZER_BACKEND`            | `gemini` (case-insensitive)       | GeminiTechniqueRecognizer (호환 alias) |
| 둘 다 ON 또는 둘 다 다른 값     | 박제 truthy = OR                  | OR 박제 (둘 중 하나라도 truthy → ON) |

박제 사유: alias 두 종 — Plan 5-03 신설 `GEMINI_RECOGNIZER_ENABLED` (직관) + 기존 `RUNPOD_*` env 패턴 정합의 `RECOGNIZER_BACKEND` (확장 가능). 향후 `RECOGNIZER_BACKEND=pole-arina` 박제 가능.

## lazy import 검증 박제

pipeline 모듈 import 시점 사전 import 0:
- `google.genai` / `google.generativeai` — Gemini SDK
- `firebase_admin` — Firestore Admin SDK (firestore_admin._db() 안 lazy)

검증 path: `test_pipeline_recognizer_switch.TestLazyImport` 2 tests PASS — `sys.modules` 검사 박제로 import 미발생 보장.

## RunPod server.py D-12 무수정 박제 검증

```bash
$ git diff main..HEAD --stat -- backend/runpod_inference/server.py
(empty — no changes)
```

박제 정합 PASS — server.py 가 pipeline 모듈을 import 만 함 (`_load_pipeline_module()`). `_RECOGNIZER` 가 lazy 박제로 전환됐어도 server.py 의 `_process` 호출 시 `_ensure_adapters` + `_ensure_recognizer` 가 모두 호출되어 자동 작동. server.py code path 0 변경.

## 박제 spec 정합 확인

| spec | 박제 path | 검증 |
|------|----------|------|
| D-12 RunPod 무수정 1pass | `git diff backend/runpod_inference/server.py` | empty diff 박제 PASS |
| D-16 lazy import | `google.genai` / `firebase_admin` 미import | `TestLazyImport` 2 tests PASS |
| D-09 case 1 graceful degrade | Gemini RuntimeError → `api_failure` category | `test_gemini_api_failure_falls_back_to_fallback` PASS |
| D-09 case 3 unregistered hook | `record_unregistered_keyword` 합성 | `test_gemini_recognizer_has_unregistered_hook` PASS |
| B8 fix 시그너처 무변경 | `inspect.signature(_angles_from_video)` | `test_angles_from_video_signature_unchanged` PASS |
| B8 fix 별 helper 신설 | `_angles_and_video_path_from_video` 존재 | `test_angles_and_video_path_helper_exists` PASS |
| Protocol 호환 | `FallbackRecognizer.recognize(angles, frames=None/path)` | `TestProtocolCompat` 2 tests PASS |
| env alias 호환 | `GEMINI_RECOGNIZER_ENABLED` + `RECOGNIZER_BACKEND` | `TestEnvSwitch` 5 tests PASS |
| 멱등 lazy | 2회 호출 = 같은 instance | `test_ensure_recognizer_idempotent` PASS |
| T-05-03-02 cleanup | tempfile unlink 검증 | `test_tempfile_cleanup` PASS |
| 회귀 0 | env OFF → Gemini SDK import 0 | `test_process_without_env_uses_fallback` PASS |

## Deviations from Plan

### Implementation deviation (Rule 외)

**None** — 플랜 박제 그대로 구현. B8 fix 박제 4 case (시그너처 무변경, 별 helper 신설, RunPod 무수정 검증, tempfile cleanup) 정합. 박제 정신 정합 모두 PASS.

### Out-of-scope discovery

**test_gemini_technique_recognizer::TestAdapterPromptHygiene::test_spike_prompt_template_clean** — pre-existing failure introduced by Plan 5-01 commit `b86fb0d`. Import `from backend.research.spikes...` fails because `backend` is not a package (no `__init__.py`) when pytest is invoked from `cd backend && pytest`. Untouched by Plan 5-03 (`git diff HEAD -- backend/tests/test_gemini_technique_recognizer.py` = empty). Logged to `.planning/phases/05-gemini/deferred-items.md`. Fix path = Plan 5-01 follow-up (refactor import or install backend as editable package).

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `backend/functions/pipeline/app.py` | +141 (lazy swap + env switch + B8 helper + try/finally) | 366 → 507 |
| `backend/tests/test_pipeline_recognizer_switch.py` | created | 250 (13 tests) |
| `backend/tests/test_pipeline_gemini_integration.py` | created | 410 (4 tests) |
| `.planning/phases/05-gemini/deferred-items.md` | created | 9 lines (pre-existing failure log) |

## Verification

- [x] `_ensure_recognizer` + `_gemini_enabled` 박제 grep 2건 PASS
- [x] `_RECOGNIZER: technique.TechniqueRecognizer | None = None` 박제 PASS
- [x] `_RECOGNIZER_LOCK = threading.Lock()` 박제 PASS
- [x] B8 fix — `_angles_from_video(bucket, key) -> np.ndarray` 시그너처 무변경 PASS
- [x] B8 fix — `_angles_and_video_path_from_video(bucket, key) -> tuple[np.ndarray, str]` 신설 PASS (`grep -c '_angles_and_video_path_from_video' backend/functions/pipeline/app.py` = 4 — 정의 + helper docstring 인용 + _process 분기 호출 + 단위 테스트 import)
- [x] RunPod server.py D-12 무수정 박제 — `git diff main..HEAD --stat backend/runpod_inference/server.py` empty
- [x] `_process` 안 `recognizer.recognize(angles, frames=local_video_path)` 호출 (Gemini path) + tempfile finally cleanup 박제
- [x] `pytest tests/test_pipeline_recognizer_switch.py` 13 tests PASS
- [x] `pytest tests/test_pipeline_gemini_integration.py` 4 tests PASS
- [x] `pytest tests/test_pipeline_dispatch.py` 6 tests PASS (회귀 0)
- [x] `pytest tests/test_pipeline_mode3.py` PASS (회귀 0)
- [x] lazy import 검증 PASS — pipeline 모듈 import 시 google.genai / firebase_admin 미import
- [x] FallbackRecognizer Protocol 호환 검증 PASS (frames=None / frames=path 둘 다 동작)

총 23 tests PASS (13 unit + 4 integration + 6 dispatch regression).

## Commits

- `221e1e1` — test(05-03): add failing tests for pipeline _RECOGNIZER lazy swap + env switch [RED]
- `b0d203c` — feat(05-03): pipeline _RECOGNIZER lazy swap + env switch + B8 fix helper [GREEN]
- `31391b9` — test(05-03): _process integration tests (mock-based, Lambda fallback path)

## TDD Gate Compliance

- Task 1: RED (`221e1e1` test commit, all 13 fail with `AttributeError: _ensure_recognizer`) → GREEN (`b0d203c` feat commit, 13 PASS) ✓
- Task 2: integration tests on Task 1's production code (`31391b9`). Tests would FAIL on a revert of `b0d203c` — single RED→GREEN cycle covers both tasks since plan-level feature is one swap point.
- REFACTOR phase 미적용 — try/finally cleanup 박제는 GREEN 분기 안에 포함, 별 refactor 불필요.

## Plan 5-04 wiring path 박제

- **Plan 5-04** (Pod requirements + setup.sh) — Pod env 박제 `RECOGNIZER_BACKEND=gemini` + `pip install google-genai` 박제 (Plan 5-01 의존성 install). pipeline/app.py 수정 0 — env 변경만으로 Gemini path 자동 활성 (D-12 박제 정합).
- **Plan 5-05** (5영상 sweep) — Pod env switch ON 박제 → TechniqueCache 자동 hit (in-memory + Firestore 영구 박제). Plan 5-02 캡싱 효과 검증 + sweep 결과 박제.
- **Plan 5-06 이상** (Lambda env var 동기화) — 운영 배포 시 `RECOGNIZER_BACKEND` SAM template 박제 + Parameter Store key 정합. 본 plan 박제 = swap path 완성 → Plan 5-06 이상 배포 책임.

## Self-Check: PASSED

- All 3 created files verified present:
  - `backend/tests/test_pipeline_recognizer_switch.py` (250 lines)
  - `backend/tests/test_pipeline_gemini_integration.py` (410 lines)
  - `.planning/phases/05-gemini/deferred-items.md`
- All 3 commit hashes verified in `git log main..HEAD`:
  - `221e1e1` test(05-03) RED
  - `b0d203c` feat(05-03) GREEN
  - `31391b9` test(05-03) integration
- All 17 Plan 5-03 tests PASS (13 unit + 4 integration) + 0 regression in 6 pipeline_dispatch tests + N regression in pipeline_mode3
- B8 fix invariant: `git diff main..HEAD --stat -- backend/runpod_inference/server.py` = empty (D-12 박제 정합)
- Lazy import 검증 PASS (google.genai / firebase_admin not in sys.modules at pipeline import)
