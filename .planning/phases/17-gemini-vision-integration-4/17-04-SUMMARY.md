---
phase: 17-gemini-vision-integration-4
plan: 04
subsystem: backend
tags: [gemini, vision, coach, llm, guardrail, pipeline, python]

# Dependency graph
requires:
  - phase: 17-gemini-vision-integration-4
    plan: 01
    provides: GeminiVisionCall + CoachPayload + resolve_model("B", ...) + _gemini_vision_enabled
  - phase: 17-gemini-vision-integration-4
    plan: 02
    provides: find_scene_flags 결과 dict (영역 B 의 sceneFlags 입력) + scene_result 변수
  - phase: 06-rtmw-engine
    provides: kismam.JointAssessment + kismam.top_issues (deviation 수치 source)
  - phase: 12-keypoint-overlay
    provides: 기존 CerebrasCoachWriter.write(context: dict) -> dict (B3 시그니처 정합 source)
provides:
  - sunity_shared.gemini.coach_writer_v2.GeminiCoachWriter — 영역 B 진입점
  - GeminiCoachWriter.write(context: dict) -> dict — B3 100% Cerebras 동일 시그니처
  - pipeline._coach_enabled / _ensure_gemini_coach_writer / _build_coach_context /
    _strip_reserved_keys / _gemini_b_audit_payload (5 helper)
  - firestore_admin.complete_analysis gemini_b kwarg → Firestore top-level geminiB audit
affects:
  - app (사용자에게 보여지는 result.tips / result.coach.detail2) — Gemini 성공 path 에선
    원인-해결 순서 + 강사 보조 톤 코칭 박힘. fallback 시 기존 Cerebras 박제 그대로.
  - 후속 plan (Phase 17 eval / F1 judge / F6 A/B) — geminiB.judgeScore=null 박제 자리 +
    fallback / fallbackReason audit 박제 source.

# Tech tracking
tech-stack:
  added:
    - sunity_shared.gemini.coach_writer_v2 모듈 신설
    - pipeline app.py dual-track wiring (5 helper 신설)
  patterns:
    - "Dual-track LLM 패턴 — Gemini 우선 + fallback dict 분기로 Cerebras 폴백 (단일 context 공유)"
    - "Reserved key strip — `_fallbackReason` / `_meta` (`_` prefix) audit-only,
       user-visible result 에 leak 0 (WARNING-3 정합)"
    - "강사 보조 톤 schema 후처리 — 부위별 용어 14개 + coach_note 3 어휘 + blocklist
       + retry 1회 + fallback dict (`{}` 또는 `{\"_fallbackReason\": ...}`, R-W4 정합 — None 박제 0)"
    - "B3 hard gate — `.write(context: dict) -> dict` 시그니처 100% 동일 (inspect.signature 회귀)"
    - "B4 hard gate — `coach_context[\"videoPath\"]` (caller 의 local_video_path) 만 사용,
       boto3 S3 download / RTMW 재실행 0"

key-files:
  created:
    - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
    - backend/tests/gemini/test_coach_writer_v2.py
    - backend/tests/test_pipeline_geminib_wiring.py
    - .planning/phases/17-gemini-vision-integration-4/17-04-SUMMARY.md
  modified:
    - backend/shared/python/sunity_shared/gemini/__init__.py (GeminiCoachWriter export)
    - backend/shared/python/sunity_shared/firestore_admin.py (complete_analysis gemini_b kwarg)
    - backend/functions/pipeline/app.py (import GeminiCoachWriter + 5 helper + dual-track wiring)

key-decisions:
  - "B3 시그니처 hard gate — GeminiCoachWriter.write(context: dict) -> dict 가
     CerebrasCoachWriter.write 와 100% 동일. _process 가 단일 _build_coach_context()
     헬퍼로 양 writer 공유. inspect.signature 회귀 박제 (test 2건)."
  - "3차 R-B2 정합 — B 삽입 위치 = 기존 Cerebras coach writer 호출부 (assemble.build_result
     직전). Plan 03 D 는 build_keypoint_report 직후 박혀 B 보다 늦음 → v1 박제 geminiD
     context 박제 X. v2 후속 plan 에서 wave 순서 재조정 후 진입."
  - "3차 R-B1 (Option A) — wave 1 (find_scene_flags) 가 line ~1238 에서 종료된 후 B 호출
     (자연 박힘 — _process 본체 박제 순서). B 가 sceneFlags 를 prompt hint 박제 사용
     (occlusion_severe → '관련 부위 가시성 제한' / backbend_present → '흉추/요추 우선')."
  - "2차 R-W4 정합 — GeminiCoachWriter.write 반환 None 박제 0. graceful skip = `{}` 또는
     `{\"_fallbackReason\": ...}` (reserved key only). _process 가 reserved 키 strip 후
     assemble 전달 — user-visible result 에 leak 0."
  - "강사 보조 톤 후처리 schema (3종):
       1) 부위별 용어 14개 화이트리스트 — cause.explanation 결합 텍스트에 1개 이상 강제.
       2) coach_note 3 어휘 ('강사' / '함께' / '확인') 동시 포함 강제 — full_text 박제 검증.
       3) blocklist ('이렇게 하세요' / '틀렸습니다' / '당신은') 매치 시 ValueError.
     실패 시 1회 retry — 총 2회 실패 시 `{\"_fallbackReason\": \"tone_validation_failed\"}`."
  - "강사 보조 톤 coach_note 박제 — Pydantic schema (CoachDetail2) 에 coach_note 필드
     박제 X (Plan 17-01 schema 박제 누락). 후처리로 detail 또는 cause.fix 의 마지막 문장
     (강사/함께/확인 포함) 을 detail2.coachNote 박제 (_attach_coach_note 헬퍼)."
  - "dual-track 분기 = reserved 키 strip 후 joint 키 ≥ 1 여부:
       Gemini 성공 → coach_details = strip(gemini_result), audit fallback=null.
       Gemini fallback dict → cerebras.write(coach_context), audit fallback='cerebras'.
       GEMINI_COACH_ENABLED OFF → cerebras only, audit None (기존 path 그대로)."
  - "Firestore geminiB audit flat object — model / latencyMs / tokensUsed (0 placeholder) /
     judgeScore=null / fallback / fallbackReason. user-visible result.tips/coach 와 분리
     (WARNING-3 정합). W5 validator 재사용으로 nested-array 회귀 차단."
  - "B4 hard gate — coach writer 가 caller 의 local_video_path (`coach_context['videoPath']`)
     만 사용. videoPath 누락 시 즉시 `{\"_fallbackReason\": \"video_path_missing\"}` (Cerebras
     폴백 활성 — text-only 코칭은 Cerebras 책임). boto3 S3 download / RTMW 재실행 0."
  - "_ensure_gemini_coach_writer singleton — _COACH_WRITER (Cerebras) 와 별도. Gemini import
     가 boto3/SSM 의존성 부담 적음 → 항상 lazy 박제 (RunPod / Lambda 콜드스타트 1회만 박제)."

patterns-established:
  - "Dual-track LLM wiring — 단일 context dict 공유 + reserved 키 분리 audit/result.
     후속 plan (영역 A reference 등록 / 영역 D 3D 주입) 박제 시 동일 패턴 재사용."
  - "강사 보조 톤 후처리 schema — Pydantic schema 가 cover 못 하는 톤 검증 (어휘 화이트리스트
     + 3어휘 동시 포함 + blocklist) 박제 패턴. 후속 plan (Phase 17 eval E4 dimension)
     박제 시 동일 헬퍼 재사용."

requirements-completed:
  - VISION-02

# Metrics
duration: ~45min
completed: 2026-06-12
---

# Phase 17 Plan 04: Gemini Vision 영역 B 코칭 멘트 Summary

**Gemini 3.1 Pro Preview Vision 으로 RTMW 8 관절 deviation + 영상 결합 → causes 3~5 +
injuryRisk + coachNote 산출. 기존 CerebrasCoachWriter 와 dual-track (GEMINI_COACH_ENABLED
default ON) — Gemini 우선 + fallback dict 시 Cerebras 폴백 + 강사 보조 톤 schema 강제
(부위별 용어 14개 + 3 어휘 + blocklist) + Firestore geminiB audit 분리 박제**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-12 (Plan 17-03 직후)
- **Completed:** 2026-06-12T02:50:14Z
- **Tasks:** 2 (TDD — atomic commit per task)
- **Files modified:** 7 (4 created + 3 modified)
- **Tests added:** 35 (14 coach_writer_v2 + 21 pipeline wiring)

## Accomplishments

- `sunity_shared.gemini.coach_writer_v2.GeminiCoachWriter` 신설 — 영역 B 진입점.
  **`.write(context: dict) -> dict` 시그니처 = `CerebrasCoachWriter.write` 와 100% 동일
  (B3 hard gate)**. context dict 의 기존 키 (`mode` / `joints`) 는 Cerebras 와 공유,
  신규 키 (`videoPath` / `dimensionScores` / `sceneFlags`) 는 Gemini 전용 (Cerebras 는
  graceful 무시).
- **GeminiVisionCall 박제** — `schema=CoachPayload`, `model=resolve_model("B", env_override=...)`,
  `temperature=0.4`, `max_output_tokens=2500`, `thinking_budget=4096`,
  `enforce_object_guard=True`. coach_writer.py L132~133 정합.
- **강사 보조 톤 schema 후처리 (3종 강제, AI-SPEC §5 E4 dimension)**:
    1. 부위별 용어 14개 화이트리스트 — `고관절/후굴/코어/내전근/외회전/햄스트링/견갑/
       엉덩이 굴곡/회전근개/요추/흉추/슬괵/장요근/대퇴직근`. 각 joint 의 cause.explanation
       결합 텍스트에 1개 이상 포함 강제.
    2. coach_note 3 어휘 동시 포함 — `강사` + `함께` + `확인`. detail + 모든 cause
       (title/explanation/fix) 결합 full_text 에서 검증.
    3. 단정/지시형 blocklist — `이렇게 하세요` / `잘못됐습니다` / `틀렸습니다` / `당신은`.
       매치 시 ValueError → 1회 retry → 2회 실패 시 `{"_fallbackReason":
       "tone_validation_failed"}` 반환.
- **2차 R-W4 정합 — None 반환 박제 0**: 성공 = `{joint_key: {detail, detail2: {causes,
  injuryRisk, coachNote}}}` + reserved `_meta`. 실패 = `{}` (joints 누락 — Cerebras 와
  동일 graceful) 또는 `{"_fallbackReason": <reason>}` (reserved key only). `_process` 가
  `_` prefix 키 strip 후 `assemble.build_result` 전달 — user-visible result 에 leak 0.
- **3차 R-B2 정합** — B 삽입 위치 = 기존 Cerebras coach writer 호출부 (`_process` 의
  `assemble.build_result` 직전). Plan 03 D 는 build_keypoint_report 직후 박혀 B 보다
  늦음 → v1 박제 `geminiD` context 박제 X (v2 후속 plan).
- **3차 R-B1 (Option A) 정합** — wave 1 (`find_scene_flags`, line ~1238) 가 await 종료
  후 B 호출 (자연 박힘 — `_process` 본체 박제 순서). B 가 sceneFlags 박제 prompt hint
  (`occlusion_severe` → "관련 부위 가시성 제한" / `backbend_present` → "흉추/요추 우선
  살피세요") 박제 사용.
- **B4 hard gate** — caller 의 `local_video_path` (Plan 01 Task 4 의 `_gemini_vision_enabled()`
  가 `GEMINI_COACH_ENABLED` 포함 → keep_local_video=True) 만 사용. boto3 S3 download /
  RTMW 재실행 0. videoPath 누락 시 즉시 `{"_fallbackReason": "video_path_missing"}` →
  Cerebras 폴백 (text-only).
- **pipeline `_process` dual-track wiring** — 5 helper 신설:
    - `_coach_enabled()` — `GEMINI_COACH_ENABLED` env (default "1") falsy 검사 (`_VISION_FALSY`).
    - `_ensure_gemini_coach_writer()` — GeminiCoachWriter singleton lazy init.
    - `_build_coach_context(mode, assessments, dim_scores, local_video_path, scene_flags)` —
      Cerebras/Gemini 양쪽 공유 단일 dict (geminiD 키 v1 박제 X).
    - `_strip_reserved_keys(d)` — `_` prefix 키 strip.
    - `_gemini_b_audit_payload(writer_result, cerebras_used, fallback_reason)` — Firestore
      `geminiB` audit dict (성공/폴백 양쪽 분기).
- **dual-track 분기 로직** — `_process` 안에서:
    - Gemini 우선 호출 → reserved 키 strip 후 joint 키 ≥ 1 → 성공 (audit fallback=null).
    - Gemini fallback dict (`{}` 또는 `{"_fallbackReason": ...}`) → Cerebras 폴백 (같은
      context 재사용, audit fallback="cerebras" + fallbackReason 박제).
    - GEMINI_COACH_ENABLED OFF → Cerebras only (기존 path 그대로, audit None).
- **`firestore_admin.complete_analysis(gemini_b=...)` kwarg 박제** — Firestore top-level
  `geminiB` audit (flat object — model / latencyMs / tokensUsed / judgeScore=null /
  fallback / fallbackReason). W5 validator 재사용으로 nested-array 회귀 차단. user-visible
  `result.tips/coach` 와 audit 분리 (WARNING-3 정합).
- 35 unit/통합 test 박제 (외부 네트워크 / Gemini API / Firestore 호출 0).

## Task Commits

각 task atomic commit:

1. **Task 1**: `5e6971d` — `feat(17-04): GeminiCoachWriter + 강사 보조 톤 schema + Firestore geminiB`
2. **Task 2**: `84042c9` — `feat(17-04): pipeline _process 영역 B dual-track wiring + env toggle`

## Files Created/Modified

**Created (4):**
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` — 영역 B 진입점
  (GeminiCoachWriter + _build_prompt + _validate_tone + _attach_coach_note +
  _coach_payload_to_dict)
- `backend/tests/gemini/test_coach_writer_v2.py` — 14 단위 test
- `backend/tests/test_pipeline_geminib_wiring.py` — 21 통합 test (단위 helper + dual-track
  분기 시뮬레이션 + source grep 회귀 + B3 시그니처 회귀)
- `.planning/phases/17-gemini-vision-integration-4/17-04-SUMMARY.md` (본 파일)

**Modified (3):**
- `backend/shared/python/sunity_shared/gemini/__init__.py` — GeminiCoachWriter export
- `backend/shared/python/sunity_shared/firestore_admin.py` — `complete_analysis` 시그너처에
  `gemini_b: dict | None = None` kwarg 추가 + `geminiB` payload 박제 + W5 validator 호출
- `backend/functions/pipeline/app.py` — `from sunity_shared.gemini.coach_writer_v2 import
  GeminiCoachWriter` + 5 helper 신설 + dual-track wiring + `complete_analysis(gemini_b=...)`
  호출 박제

## Decisions Made

- **B3 시그니처 hard gate**: `GeminiCoachWriter.write(context: dict) -> dict` =
  `CerebrasCoachWriter.write` 와 100% 동일. `_process` 가 단일 `_build_coach_context()`
  헬퍼로 양 writer 공유. `inspect.signature` 회귀 박제 2건 (test_coach_writer_v2 +
  test_pipeline_geminib_wiring).
- **3차 R-B2 (B 삽입 위치)**: 기존 Cerebras 호출부 = `_process` 의 `assemble.build_result`
  직전. Plan 03 D 가 `build_keypoint_report` 직후 박혀 B 보다 늦음 → v1 박제 `geminiD`
  키 박제 X (B 가 D 결과 받을 수 없음). v2 후속 plan 에서 wave 순서 재조정 후 진입.
- **3차 R-B1 (B/C ordering, Option A)**: wave 1 (`find_scene_flags`) 가 line ~1238 에서
  await 종료 후 B 호출 (자연 박힘). B/C 병렬 박제 X — B 가 `sceneFlags` 박제 prompt hint
  로 사용.
- **2차 R-W4 (None 박제 0)**: GeminiCoachWriter.write 가 절대 None 반환 X. graceful skip =
  `{}` (joints 누락 — Cerebras 와 동일 graceful) 또는 `{"_fallbackReason": <reason>}`
  (reserved key only).
- **강사 보조 톤 후처리 schema (3종)**: Pydantic schema (Plan 17-01 CoachDetail2) 가 cover
  못 하는 톤 검증을 후처리 박제. 부위별 용어 화이트리스트 14개 + 3 어휘 동시 포함 +
  blocklist 매치. 1회 retry — Plan 17-01 GeminiVisionCall retry 와 별개로 GeminiCoachWriter
  내부 retry. worst case 4 호출 (GeminiVisionCall retry 1 + 본 writer retry 1 = attempt 2).
- **coach_note 박제 (schema 누락 보강)**: Plan 17-01 CoachDetail2 에 coach_note 필드 박제 X.
  후처리 `_attach_coach_note` 헬퍼가 detail 또는 cause.fix 의 마지막 문장 (3 어휘 포함)
  추출 → `detail2.coachNote` 박제. assemble.build_result 가 그대로 사용.
- **dual-track 분기 = reserved 키 strip 후 joint 키 ≥ 1 여부**: Gemini 결과 dict 에서
  `_` prefix 키 (`_fallbackReason` / `_meta`) 제외하고 user-visible joint 키가 1개라도
  있으면 성공 path. 빈 dict 또는 `_fallbackReason` 만 박힌 dict → Cerebras 폴백.
- **Firestore `geminiB` audit flat object**: 성공/폴백 양쪽 박제. flat scalar 만 박힘 —
  `model` / `latencyMs` / `tokensUsed` (0 placeholder) / `judgeScore=null` / `fallback`
  / `fallbackReason`. W5 validator 재사용으로 nested-array 회귀 차단 (geminiB 박제 path
  strict 유지).
- **`tokens_used=0` placeholder**: GeminiVisionCall.call() 시그너처는 parsed 결과만 반환.
  usage_metadata 박제는 후속 plan (Phase 17 eval/F8 — Phoenix trace join) 에서 client
  시그너처 확장 시 박힘. 본 plan 박제 scope 는 latency_ms 만 실측.
- **B4 hard gate (S3 재다운로드 / RTMW 재실행 0)**: GeminiCoachWriter 가 caller 의
  `local_video_path` (context["videoPath"]) 만 사용. videoPath 누락 시 즉시
  `{"_fallbackReason": "video_path_missing"}` → Cerebras 폴백 (text-only).
- **`_ensure_gemini_coach_writer` singleton 별도**: `_COACH_WRITER` (Cerebras) 의
  `_ensure_adapters()` 와 분리. Gemini import 가 boto3/SSM 의존성 부담 적음 → 항상 lazy
  박제 가능 (RunPod / Lambda 콜드스타트 1회 박제).

## Deviations from Plan

다음은 plan 정신 정합 보조 박제 — 박제 정신 변경 0:

1. **[Rule 2 - 누락된 critical functionality 보강] coach_note 추출 후처리 (_attach_coach_note)**
   - **Found during:** Task 1 GREEN 단계 — Plan 17-01 CoachDetail2 schema 에 `coach_note`
     필드 박제 X (Plan 17-01 schema 박제 누락). Plan 17-04 의 `coach_note` 강사 보조 톤 강제
     박제 적용 source 누락 — Pydantic 응답에 coach_note 가 직접 없음.
   - **Fix:** `_attach_coach_note` 헬퍼 박제 — detail 또는 cause.fix 의 마지막 문장 중
     "강사" + "함께" + "확인" 3 어휘 동시 포함 박제를 detail2.coachNote 로 박제. assemble
     이 user-visible 카드에 박을 수 있게.
   - **Justification:** Rule 2 — Plan 17-04 must_haves 의 "coach_note 3 어휘 schema 단계
     강제" 박제가 hard requirement. Plan 17-01 schema 박제 보강 (RefinedKeypoint.joint_key
     박제 정합 — Plan 17-03 SUMMARY 의 Rule 2 deviation 동형) 대신 후처리 박제 박제 (Plan
     17-01 schema 박제는 v1 schema 박제 stable — schema 확장보다 후처리 박제 박제 정합).
   - **Files modified:** backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
   - **Commit:** 5e6971d

2. **[Rule 3 - 박제 박힌 변수명 정합] dim_scores → dimension_scores (_process 본체 박제 정합)**
   - **Found during:** Task 2 회귀 sweep — Phase 8/9 test 15건 NameError 박힘.
   - **Issue:** plan 박제 `_build_coach_context(dim_scores=dim_scores, ...)` 박제는 plan
     박힌 변수명 `dim_scores` 사용. `_process` 본체 박제 박힌 실제 변수명은 `dimension_scores`
     (line 1517 / 1541 박제 정합). 박제 mismatch 시 NameError.
   - **Fix:** `_process` 박제 박힌 호출 박제를 `dim_scores=dimension_scores` 박제 박제.
   - **Justification:** Rule 3 — 회귀 차단 박제. 변수명 박제 mismatch 는 plan 박제 정신 변경 X
     (helper 시그너처 박제 `dim_scores` 박제 박제, 박힌 변수만 정합).
   - **Files modified:** backend/functions/pipeline/app.py (line 1644)
   - **Commit:** 84042c9 (Task 2 commit 안 박제 박힘)

## Issues Encountered

- **Plan 17-01 CoachDetail2 schema 박제 누락 (deviation #1)**: `coach_note` / `injury_risk`
  필드 박제 X. 후처리 박제 (`_attach_coach_note`) 박제 보강. Plan 17-04 박제 검증 박힘.
- **Pre-existing test failures (Plan 17-04 scope 외)**: `tests/test_gemini_moment_extractor.py`
  의 `DEFAULT_GEMINI_MODEL` 박제 mismatch (Phase 5 박제), `tests/test_compare_engines_smoke.py`
  / `tests/test_spike_*` collection error (다른 phase 박제). 본 plan 회귀 sweep (200 test PASS)
  에서 검증 — Plan 17-04 박제 회귀 0.

## Known Stubs

- `tokens_used = 0` placeholder — GeminiVisionCall.call() 박제 시그너처 (parsed 결과만 반환)
  박제 한계. usage_metadata 박제는 후속 plan (Phase 17 eval/F8) 에서 client 시그너처 확장
  시 박힘. Plan 17-02 / 17-03 의 동일 placeholder 박제 정합.
- `judgeScore = null` placeholder — F1 flywheel (LLM judge ≥ 0.7) 박제 후속 plan 박제 자리.
  Firestore audit 박힐 자리만 박제 박제.

## Threat Flags

None — 본 plan 의 변경은 기존 trust boundary 안에서만 박제. 신규 외부 통신 path 는 Plan
17-01 의 GeminiVisionCall 박제 재사용. geminiB Firestore 박제는 기존 result 박제 path 박제
정합 (auth/network surface 변경 0). Plan 박제 `threat_model` (T-17-16 ~ T-17-21) 6 박제 모두
박제 박힘:
  - T-17-16 (강사 대체 톤) — `_validate_tone` 3 어휘 + blocklist 박제.
  - T-17-17 (generic 어휘) — 부위별 용어 14개 화이트리스트 박제.
  - T-17-18 (객관성 우회) — enforce_object_guard=True (Plan 17-01 G1) 박제 + Pydantic
    schema extra='forbid' 박제.
  - T-17-19 (LLM 출처 audit) — geminiB.model / geminiB.fallback / fallbackReason 박제.
  - T-17-20 (retry 무한) — GeminiCoachWriter.write retry max 2 + GeminiVisionCall retry max 1
    = worst case 4 호출 박제. 그 후 즉시 Cerebras 폴백.
  - T-17-21 (env spoofing) — env 박제는 Lambda/Pod 배포 시 박제 — 외부 접근 박제 X (accept).

## User Setup Required

- 운영 시 `GEMINI_COACH_ENABLED=1` (default) Lambda env (또는 Pod env) 박제 시 영역 B 활성.
  코드 변경 0.
- `GEMINI_API_KEY` 박제는 Plan 17-01 의 `_load_api_key` 박제 정합 — env / SSM fallback 박제.
  본 plan 추가 박제 0.
- 운영 대응 시 `GEMINI_B_MODEL_OVERRIDE=gemini-3.5-flash` 박제 manual override 가능 (예:
  비용 폭증 시 일시 강등). 본 plan 박제 검증 — `resolve_model("B", env_override=...)` 박제
  단일 source.
- Firestore: 기존 `users/{uid}/analyses/{id}` doc 에 `geminiB` 필드 자동 박힘 — 별도 schema
  박제 0.

## Self-Check: PASSED

- 4 expected created files 모두 FOUND:
  - `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py`
  - `backend/tests/gemini/test_coach_writer_v2.py`
  - `backend/tests/test_pipeline_geminib_wiring.py`
  - `.planning/phases/17-gemini-vision-integration-4/17-04-SUMMARY.md`
- 3 expected modified files 모두 git diff 박제 확인.
- 2 commits (`5e6971d`, `84042c9`) 모두 git log 박제.
- 35 단위/통합 test 모두 PASSED — `pytest backend/tests/gemini/test_coach_writer_v2.py
  backend/tests/test_pipeline_geminib_wiring.py -x -q`.
- 200 directly impacted test 모두 PASSED — Phase 17 + pipeline 회귀 sweep.
- Plan verification grep 회귀 PASS:
  - `grep -n "GeminiCoachWriter" backend/functions/pipeline/app.py | grep -v '^[0-9]*:#'` = 5건
    (import + singleton + 호출, ≥ 2 박제 정합).
  - `grep -n "GEMINI_COACH_ENABLED" backend/functions/pipeline/app.py | grep -v '^[0-9]*:#'` = 4건
    (default 박제 + helper + 호출, ≥ 1 박제 정합).
  - `grep -n "gemini_b" backend/shared/python/sunity_shared/firestore_admin.py | grep -v '^[0-9]*:#'`
    = 4건 (kwarg + 박제 박힘 ≥ 1 박제 정합).
- B3 시그니처 회귀 직접 검증:
  - `inspect.signature(GeminiCoachWriter.write).parameters` = `['self', 'context']`
  - `inspect.signature(CerebrasCoachWriter.write).parameters` = `['self', 'context']`
  - PASS (정확히 동일).

## Next Phase Readiness

- 본 plan 의 영역 B 박제는 운영자 `GEMINI_COACH_ENABLED=1` (default) + `GEMINI_API_KEY`
  박제만으로 활성 — 코드 변경 0.
- result.tips / result.coach.detail2 박제 → app 의 기존 Coach 카드 / 자세히 모달 (Phase 12.5
  T9 박제) 가 자동 소비 — UI 변경 0.
- Firestore `geminiB` audit 박제 → eval/guardrail plan 박제 (별도 plan) 이 fallback rate /
  fallbackReason 추적 가능. F6 A/B 분석 입력.
- **후속 plan 박제 readiness — geminiD context 박제 (v2)**: wave 순서 재조정 (D → B) 박은
  후, `_build_coach_context` 박제에 `geminiD` 키 박제 → B 가 D 결과 받아 keypoint 좌표
  참조 가능. ROADMAP 박제 시 진입.

---
*Phase: 17-gemini-vision-integration-4*
*Completed: 2026-06-12*
