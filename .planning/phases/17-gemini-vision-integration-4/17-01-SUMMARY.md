---
phase: 17-gemini-vision-integration-4
plan: 01
subsystem: infra
tags: [gemini, pydantic, guardrail, llm, vision, python]

# Dependency graph
requires:
  - phase: 05-gemini-technique-recognizer
    provides: gemini_moment_extractor._load_api_key + _enforce_no_coordinate_or_score 패턴 (Phase 17 client 가 lazy import 재사용)
  - phase: 06-rtmw-engine
    provides: skeleton.JOINT_KEYS 8개 (CheckpointJoint.joint_key Literal 동기화 source)
provides:
  - sunity_shared.gemini namespace — 4 영역 (A/B/C/D) 공통 진입점
  - GeminiVisionCall — Files API + retry + G1 가드 베이스 클라이언트
  - 4 영역 Pydantic schemas — ReferenceRegistration / CoachPayload / FindingFlags / KeypointRefinement
  - 객관성 reject regex (G1 hard fail) — graceful 우회 X
  - DEFAULT_*_MODEL + ALLOWED_MODELS — 영역별 model 단일 source (404 silent fallback 차단)
  - pipeline._gemini_vision_enabled + _safe_unlink_local_video — Phase 17 4 영역 OR-gate
affects:
  - 17-gemini-vision-integration-4 (후속 plan 02 영역 A / 03 영역 B / 04 영역 C / 05 영역 D)
  - 17-gemini-vision-integration-4 (eval/guardrail plan)

# Tech tracking
tech-stack:
  added:
    - sunity_shared.gemini namespace 신설 (5 모듈)
    - GeminiVisionCall Generic[T] dataclass 패턴
  patterns:
    - Schema-as-config (Pydantic response_schema 주입 + parsed 폴백 + model_validate 재시도)
    - 객관성 reject regex 단일 진입점 + 영역 D 좌표 우회 (allow_coords opt-in)
    - 영역별 default model string 단일 source — raw string 박제 grep 회귀 가드
    - keep_local_video OR-gate (Phase 5 recognizer ∪ Phase 17 4 영역)

key-files:
  created:
    - backend/shared/python/sunity_shared/gemini/__init__.py
    - backend/shared/python/sunity_shared/gemini/client.py
    - backend/shared/python/sunity_shared/gemini/schemas.py
    - backend/shared/python/sunity_shared/gemini/guardrails.py
    - backend/shared/python/sunity_shared/gemini/config.py
    - backend/tests/gemini/__init__.py
    - backend/tests/gemini/test_client.py
    - backend/tests/gemini/test_schemas.py
    - backend/tests/gemini/test_guardrails.py
    - backend/tests/gemini/test_config.py
    - backend/tests/test_pipeline_vision_gate.py
  modified:
    - backend/functions/pipeline/app.py

key-decisions:
  - "_load_api_key 는 lazy import 재사용 (Phase 5 sunity_shared.judging.gemini_moment_extractor._load_api_key) — env GEMINI_API_KEY → SSM 박제 fallback 패턴 재구현 0"
  - "객관성 가드는 4 영역 모두 단일 진입점 — guardrails._enforce_no_reject_patterns. 점수/판단 어휘는 영역 D 도 영구 차단 (allow_coords 는 좌표만 분기)"
  - "영역별 default model 은 config.py 단일 source + ALLOWED_MODELS 화이트리스트 — Plan 02~05 는 raw string 박지 않고 resolve_model 또는 DEFAULT_*_MODEL 만 import"
  - "_gemini_vision_enabled 는 별 helper (Phase 5 _gemini_enabled 시그니처 변경 0) — keep_local_video gate 는 두 helper 의 OR. B/C default '1' (Plan 03/04 default ON)"
  - "_safe_unlink_local_video wrapper 신설 — Path.unlink(missing_ok=True) 는 PermissionError 등에서 raise. 본 wrapper 가 흡수 (graceful + log.warning 1회) — B/C default ON 으로 모든 분석에서 keep_local_video=True 가 될 때 disk budget 차단"

patterns-established:
  - "Generic[T] dataclass 패턴 — GeminiVisionCall[ReferenceRegistration] 등 schema 별 타입 추론"
  - "객관성 가드 = ValueError raise (graceful X). API/Network 실패 = return None (graceful)"
  - "Pydantic ConfigDict(extra='forbid') 박제 — 알려지지 않은 필드 통과 차단"
  - "테스트 외부 네트워크 호출 0 — genai.Client / files / models 전부 monkeypatch"

requirements-completed:
  - VISION-01
  - VISION-02
  - VISION-03
  - VISION-04

# Metrics
duration: ~75min
completed: 2026-06-12
---

# Phase 17 Plan 01: Gemini Vision 4 영역 베이스 신설 Summary

**4 영역 (reference/coach/finding/keypoint) 공통 진입점 신설 — GeminiVisionCall + Pydantic schemas + 객관성 G1 가드 + 영역별 model 단일 source + pipeline OR-gate**

## Performance

- **Duration:** ~75 min
- **Started:** 2026-06-12 (worktree start)
- **Completed:** 2026-06-12T01:53:13Z
- **Tasks:** 4 (TDD — RED/GREEN per task)
- **Files modified:** 12 (11 created + 1 modified)

## Accomplishments
- `sunity_shared.gemini` namespace 5 모듈 신설 (`__init__` / `client` / `schemas` / `guardrails` / `config`).
- `GeminiVisionCall` Generic[T] 베이스 — Files API upload + ACTIVE 폴링 (120s 상한) + response_schema 검증 + parsed/text 폴백 + ValidationError/JSONDecodeError 1회 retry + APIError 5xx 1회 backoff retry + APIError 4xx 즉시 graceful None.
- 4 영역 Pydantic schemas — `ReferenceRegistration` (A) / `CoachPayload` (B) / `FindingFlags` (C) / `KeypointRefinement` (D). `CheckpointJoint.joint_key` Literal 8개 = `skeleton.JOINT_KEYS` 동기화.
- 객관성 G1 reject regex — 점수 (`\d+(\.\d+)?\s*점`, `\d+/\d+`) + 좌표 (`좌표`, `x=`, `y=`) + 사람 판단 (`잘했다`, `훌륭(하다)?`, `완벽`) hard fail. 영역 D 만 `allow_coords=True` 로 좌표 우회 — 점수/판단은 영역 D 도 영구 차단.
- `config.py` 영역별 default model 단일 source — `DEFAULT_A_MODEL` / `B` / `D` = `gemini-3.1-pro-preview`, `DEFAULT_C_MODEL` = `gemini-3.5-flash`, `DEFAULT_C_MODEL_OVERRIDE` = `gemini-3.1-pro-preview`. `ALLOWED_MODELS = frozenset({Pro preview, Flash})` + `resolve_model(region, env_override)` 가 2.5/plain Pro/typo 차단.
- `pipeline._gemini_vision_enabled()` helper + `keep_local_video = _gemini_enabled() or _gemini_vision_enabled()` OR-gate — Phase 17 4 토글 (REFERENCE / COACH / FINDING / D) 중 하나만 ON 이어도 local_video_path 보존.
- `_safe_unlink_local_video()` finally cleanup wrapper — `Path.unlink(missing_ok=True)` 의 PermissionError/OSError 흡수 + `log.warning` 1회 (R-W6 정합). B/C default ON 으로 모든 분석에서 keep_local_video=True 가 될 때 disk budget 누수 차단.
- 72 unit tests (schemas 18 + guardrails 14 + client 11 + config 15 + pipeline gate 14) — 외부 네트워크 호출 0.

## Task Commits

각 task 가 atomic 으로 commit (TDD — RED → GREEN per task):

1. **Task 1: 4 영역 Pydantic schemas + 객관성 guardrail helper 정의** — `711d475` (feat)
2. **Task 2: GeminiVisionCall 베이스 클라이언트 + Files API 폴링 + retry** — `9486521` (feat)
3. **Task 3: gemini/config.py 단일 source + ALLOWED_MODELS 화이트리스트 (B1 정합)** — `208547f` (feat)
4. **Task 4: pipeline._gemini_vision_enabled() + keep_local_video gate 확장 (B4 정합)** — `508a25e` (feat)

_Note: 각 task 의 test 와 implementation 은 동일 commit 에 묶음 — pure 모듈 (schemas/guardrails/config) 은 RED 와 GREEN 간 의미 있는 분리가 적고, plan 의 `must_haves` 가 단위 묶음을 박제했음._

## Files Created/Modified

- `backend/shared/python/sunity_shared/gemini/__init__.py` — 4 영역 공통 진입점 (12 symbol export)
- `backend/shared/python/sunity_shared/gemini/client.py` — GeminiVisionCall Generic[T] 베이스 (Files API + retry + G1 가드)
- `backend/shared/python/sunity_shared/gemini/schemas.py` — 4 영역 Pydantic 모델 (CheckpointJoint / JointCoaching / CoachDetail2 / CoachCause / RefinedKeypoint 보조 포함)
- `backend/shared/python/sunity_shared/gemini/guardrails.py` — `_enforce_no_reject_patterns` G1 hard fail
- `backend/shared/python/sunity_shared/gemini/config.py` — DEFAULT_*_MODEL 단일 source + ALLOWED_MODELS frozenset + resolve_model 함수
- `backend/functions/pipeline/app.py` — `_gemini_vision_enabled()` + `_safe_unlink_local_video()` helper 추가 + keep_local_video OR-gate + finally 박제 safe wrapper
- `backend/tests/gemini/__init__.py` + 4개 test 모듈 + `backend/tests/test_pipeline_vision_gate.py` — 72 unit tests (외부 네트워크 0)

## Decisions Made

- **`_load_api_key` 박제 재사용 (lazy import)**: `sunity_shared.judging.gemini_moment_extractor._load_api_key` 가 이미 env → SSM 박제 fallback 박제. 본 client.py 의 `_default_api_key_loader` 는 그 함수를 lazy import — 중복 0 + boto3 의존 path 동기화. caller 가 `api_key_loader=...` 박제로 override 가능 (테스트에서 사용).
- **객관성 가드는 단일 진입점**: `gemini_moment_extractor._enforce_no_coordinate_or_score` 와 별도 박제 (`gemini/guardrails.py`). 기존 Phase 5 path 의 reject patterns 와 의미적으로 동일하지만, Phase 17 4 영역 plan 이 단일 진입점만 import 하도록 분리 — Phase 5 모듈 변경이 Phase 17 에 leak 0.
- **점수/판단은 영역 D 도 영구 차단**: `allow_coords=True` 는 좌표 패턴 (`x=`, `y=`, `좌표`) 만 우회 — 점수 (`87점`, `9/10`) 와 사람 판단 (`잘했다`, `훌륭`, `완벽`) 은 `[[analysis-objectivity-no-human-scores]]` 헌장 정합으로 4 영역 모두 영구 차단.
- **`_safe_unlink_local_video` wrapper 신설**: 기존 `Path(local_video_path).unlink(missing_ok=True)` 박제는 FileNotFoundError 만 흡수 — PermissionError/OSError 는 raise. B/C default ON 으로 모든 분석에서 keep_local_video=True 가 될 때 unlink 실패가 분석 흐름 차단할 risk. 본 wrapper 가 흡수 (graceful + log.warning 1회).
- **`_gemini_vision_enabled` 의 falsy 박제 분리**: Phase 5 `_gemini_enabled` 은 truthy 박제 (`_GEMINI_ENV_TRUTHY = {"1", "true", "on", "yes", "gemini"}`). Phase 17 은 falsy 박제 (`_VISION_FALSY = {"0", "false", ""}`) — B/C default "1" path 박제 정합 (env 미설정 = default = ON, "0"/"false" = OFF). 두 helper 의 시그니처/동작 분리 정합.

## Deviations from Plan

None — plan 박제 정신 정확히 따라 실행. 다음은 plan 의 "박제" 부분 정합 보조 박제:

- Plan 박제 `gemini/__init__.py` 의 `_load_api_key` import 박제 path 가 `sunity_shared.analysis.gemini_moment_extractor` 로 박혀 있으나 실제 모듈은 `sunity_shared.judging.gemini_moment_extractor` (Phase 5 의 module relocation). client.py 의 `_default_api_key_loader` 가 lazy import 박제로 정확한 path 사용. 박제 정신 (재사용) 그대로.
- Plan task 2 의 test case 박제 "10개" — 실제 박제 11개 (1개 추가: `test_first_validation_error_then_success` — retry 후 성공 path 박제). plan 의 ≥ 10개 박제 조건 정합.
- Plan task 3 의 test case 박제 "7개" — 실제 박제 15개 (DEFAULT_* 회귀 박제 별도 + None env path + empty env path 박제). plan 의 ≥ 7개 정합.
- Plan task 4 의 test case 박제 "6 + 2 = 8개" — 실제 박제 14개 (4 영역 토글 케이스 각각 박제 + falsy 박제 + grep 회귀 + finally cleanup 정상/예외 path + unlink 실패 graceful). plan 의 ≥ 6 정합.

## Issues Encountered

- 기존 pre-existing test failure 3건 (`tests/test_gemini_moment_extractor.py::TestExtractor::test_default_model_constant` + 2건) — `DEFAULT_GEMINI_MODEL` source 박제가 `gemini-2.5-flash` 인데 test 가 `gemini-3.1-pro-preview` 박제 (Phase 5 Plan 08-03 env-driven 박제 vs Plan 5-05 verify 박제 mismatch). Plan 17-01 scope 외 — `deferred-items.md` 박제 안 함 (Phase 5 자체 박제 책임). 회귀 0.
- 외부 라이브러리 `google.genai` 의 `UploadFileConfig` 미존재 환경 대비 — client.py 의 `files.upload` 호출에 `TypeError` 박제 후 kwargs-only fallback 박제 (실 환경 + 테스트 monkeypatch stub 둘 다 호환).

## Known Stubs

None — 본 plan 의 베이스는 후속 plan (02~05) 이 schema + prompt 만 교체해서 호출하는 단일 진입점. 베이스 자체에 "데이터 없음" placeholder UI 박제 X.

## User Setup Required

None — 후속 plan (02~05) 이 env 박제 (`GEMINI_REFERENCE_ENABLED` / `GEMINI_COACH_ENABLED` 등) 를 운영자 박제 요청 시 Lambda/Pod env 박제 동기화 필요. 본 plan 은 코드 베이스만 박제.

## Self-Check: PASSED

- 11 expected files 모두 FOUND.
- 4 commits (711d475, 9486521, 208547f, 508a25e) 모두 git log 에 FOUND.
- 72 unit tests 모두 PASSED — `pytest backend/tests/gemini/ backend/tests/test_pipeline_vision_gate.py -q`.
- `python3 -c "from sunity_shared.gemini import GeminiVisionCall, ReferenceRegistration, CoachPayload, FindingFlags, KeypointRefinement, _enforce_no_reject_patterns, resolve_model, ALLOWED_MODELS"` 통과.
- `grep -rn "gemini-3\\.1-pro[^-]" backend/shared/python/sunity_shared/gemini/ backend/functions/` 결과 0건 (plain Pro suffix 박제 0).
- `grep -n "keep_local_video=_gemini_enabled() or _gemini_vision_enabled()" backend/functions/pipeline/app.py` 1건.
- `grep -n "_gemini_vision_enabled" backend/functions/pipeline/app.py` 정의 + 호출 ≥ 2건.

## Next Phase Readiness

- Plan 02 (영역 A reference 등록) / 03 (영역 B 코칭) / 04 (영역 C finding) / 05 (영역 D keypoint refinement) 가 본 plan 의 `GeminiVisionCall` + region별 schema + `resolve_model("X", env_override=...)` 만 박제하면 즉시 진입.
- Plan 02~05 의 default ON 분기 (B/C) 는 `_gemini_vision_enabled` 박제로 자동 트리거 — 별도 wiring 박제 0.
- 후속 plan 들의 schema 재정의는 영구 차단 (단일 source).

---
*Phase: 17-gemini-vision-integration-4*
*Completed: 2026-06-12*
