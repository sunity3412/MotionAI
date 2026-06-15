---
phase: 03-bodyprofileinput
plan: 01
subsystem: api
tags: [bodyprofile, firestore, contract-lockstep, typescript, python, coach-context, data-hook]

# Dependency graph
requires:
  - phase: existing
    provides: AnalysisDoc contract + userAnalyses normalize + loading.tsx setDoc seam + pipeline _build_coach_context
provides:
  - 3-way BodyProfile 계약 lockstep (analysis.ts union/interface + models.py 상수/normalizer + contract.md 섹션)
  - AnalysisDoc.bodyProfile snapshot 필드 (분석-당시 재현성, R1)
  - bodyProfile.ts 데이터소스 hook (normalizeBodyProfile/useBodyProfile/getBodyProfileOnce/saveBodyProfile/dismissBodyProfilePrompt)
  - userAnalyses normalize 의 bodyProfile snapshot 보존
  - loading.tsx snapshot-at-creation (client normalize)
  - pipeline _build_coach_context bodyProfile 키 (D-04 coach seam)
affects: [03-02 (BodyProfileForm 폼), 03-03 (권유 모달 + 결과 표기), Phase 13 (LLM coach context 소비)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "3-way contract lockstep single-source (TS union/interface + Python 상수/normalizer + contract.md)"
    - "단일 normalizer 공유 (client normalizeBodyProfile = userAnalyses snapshot 보존 + getBodyProfileOnce snapshot 기록)"
    - "all-empty → null (omit snapshot) 규칙을 normalizer 안에 박제 (R5)"
    - "snapshot-at-creation (live cross-read 아님 — 결과 화면 재현성 R1)"
    - "writer-ignores-unknown-context-keys (D-04 zero-behavior-change seam)"
    - "이중 정규화 (client + server normalize_body_profile)"

key-files:
  created:
    - app/src/lib/bodyProfile.ts
    - backend/tests/test_body_profile.py
  modified:
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - app/src/lib/userAnalyses.ts
    - app/src/app/analysis/loading.tsx
    - backend/functions/pipeline/app.py

key-decisions:
  - "Task 1 RED 테스트 + 3-way 계약 GREEN 을 단일 atomic commit (계약은 atomic, plan 명시)"
  - "weightKg 보조 ONLY — scoring consumer 6 모듈 grep gate 로 유입 차단 (D-05/R4)"
  - "getBodyProfileOnce()(client normalize) 만 loading snapshot 에 사용 — raw getDoc spread 금지 (R5)"
  - "bodyProfile.ts 가 userAnalyses 를 import 하지 않고 onSnapshot 직접 구현 (순환 import 회피)"

patterns-established:
  - "3-way contract lockstep: analysis.ts + models.py + contract.md 동시 갱신"
  - "단일 normalizer 공유 (snapshot 보존 + snapshot 기록 동일 함수)"
  - "snapshot-at-creation + writer-ignores-unknown-keys (Phase 13 seam, zero-risk)"

requirements-completed: [BODY-02]

# Metrics
duration: 9min
completed: 2026-06-15
---

# Phase 3 Plan 01: BodyProfile 계약 토대 + thin E2E 슬라이스 Summary

**BodyProfile 자가입력 타입을 TS·Python·contract.md 3-way lockstep 으로 신설하고, input→Firestore→snapshot→AnalysisDoc→pipeline→coach context 까지 관통하는 thin slice 완성 (graceful normalize + 재현성 snapshot + D-05 weightKg 차단)**

## Performance

- **Duration:** 9 min
- **Started:** 2026-06-15T02:29:09Z
- **Completed:** 2026-06-15T02:37:13Z
- **Tasks:** 3
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments
- BodyProfile 타입 3-way lockstep (ExperienceLevel/DominantHand/PainArea union + BodyProfile interface + EXPERIENCE_LEVELS/DOMINANT_HANDS/PAIN_AREAS 상수 + normalize_body_profile + contract.md 섹션)
- AnalysisDoc.bodyProfile snapshot 필드 — 결과 화면 재현성 (live 프로필 아님, R1)
- bodyProfile.ts 데이터소스 hook 5종 export (normalizeBodyProfile/useBodyProfile/getBodyProfileOnce/saveBodyProfile/dismissBodyProfilePrompt) — 화면 Firestore 직접 접근 격리
- loading.tsx 가 getBodyProfileOnce() 로 분석 시작 시점 snapshot (client normalize + all-empty→null)
- pipeline _build_coach_context 에 bodyProfile 키 (D-04 seam) — Phase 13 LLM 소비 예정, 현 writer graceful 무시
- D-05 확장 grep gate: 6 scoring-consumer 모듈에 weightKg 0 matches (위조 height/weight 로 점수 game 불가)
- 17 backend 테스트 GREEN (14 normalize_body_profile + 3 coach-context graceful)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 — 3-way BodyProfile 계약 lockstep + AnalysisDoc.bodyProfile** - `cdfdfdb` (feat) — TDD RED 테스트 + GREEN 계약 단일 atomic
2. **Task 2: bodyProfile.ts 데이터소스 hook + userAnalyses snapshot 보존** - `439ae79` (feat)
3. **Task 3: loading.tsx snapshot + pipeline coach seam (D-04) + D-05 grep gate** - `d523cdf` (feat)

_Note: Task 1 은 tdd="true" 였으나 plan 이 "3-way 계약을 단일 atomic 으로 신설" 을 명시 — RED 테스트와 GREEN 계약(3 파일)을 함께 단일 commit. 별도 test commit 없음._

## Files Created/Modified
- `app/src/lib/bodyProfile.ts` (created) - 자가입력 프로필 데이터소스 hook (normalizer + 라이브 구독 + one-shot read + merge-write)
- `backend/tests/test_body_profile.py` (created) - normalize_body_profile 14 케이스 + coach-context 3 케이스
- `app/src/types/analysis.ts` (modified) - ExperienceLevel/DominantHand/PainArea union + BodyProfile interface + AnalysisDoc.bodyProfile
- `backend/shared/python/sunity_shared/models.py` (modified) - EXPERIENCE_LEVELS/DOMINANT_HANDS/PAIN_AREAS 상수 + normalize_body_profile graceful helper
- `docs/contract.md` (modified) - "BodyProfile (자가입력)" 섹션 (필드표 + 저장 위치 + graceful + D-05)
- `app/src/lib/userAnalyses.ts` (modified) - normalize 가 normalizeBodyProfile(raw.bodyProfile) 로 snapshot 보존
- `app/src/app/analysis/loading.tsx` (modified) - getBodyProfileOnce() snapshot-at-creation
- `backend/functions/pipeline/app.py` (modified) - _build_coach_context body_profile kwarg + "bodyProfile" 키 + caller normalize_body_profile 전달

## Decisions Made
- Task 1 의 RED 테스트와 GREEN 3-way 계약을 단일 atomic commit — plan 이 "3-way 계약을 단일 atomic 으로 신설" 을 명시. TDD 분할 commit 보다 계약 atomicity 우선.
- client(normalizeBodyProfile) + server(normalize_body_profile) 이중 정규화 — owner-write client 값이라 둘 다 raise 안 하고 None 반환 (D-06 graceful).
- bodyProfile.ts 는 onSnapshot 을 직접 구현 (useAnalysisDoc 재사용 X) — userAnalyses→bodyProfile 단방향 import 유지로 순환 import 회피.

## Deviations from Plan

None - plan executed exactly as written. (Task 1 의 단일 atomic commit 은 plan 의 "단일 atomic" 지시 정합 — TDD 분할 미적용이 의도된 동작.)

## Issues Encountered
- **로컬 `python` alias 부재** — `python` 미설치, `python3` 사용. 검증 흐름에 영향 없음.
- **pre-existing 회귀 실패 (out-of-scope, NOT fixed)**: `tests/phase08/test_gemini_model_env_driven.py::test_gemini_moment_extractor_default_is_non_eol` 는 03-01 변경 전 HEAD(`d3e2821`)에서도 실패 — quick task 260615-cxe 의 Gemini default model 변경으로 인한 stale test. 또한 spike/smoke 테스트 다수 collection error(`No module named 'backend'`/`'fixtures'`) 도 사전 존재. 둘 다 `deferred-items.md` 에 기록, SCOPE BOUNDARY 규칙에 따라 미수정. 03-01 verify scope(`test_body_profile.py` + 인접 phase 스위트 584/584 pass)는 전부 GREEN.

## User Setup Required
None - no external service configuration required. (referenceMotionId 와 동일 free-read 메커니즘 재사용 — 새 HTTP endpoint/validation.py/upload-url Lambda/Firestore rules 변경 없음.)

## Next Phase Readiness
- 03-02 (BodyProfileForm 폼) + 03-03 (권유 모달/결과 표기) 가 올라설 계약·저장·snapshot-보존 경로 박제 완료.
- saveBodyProfile/dismissBodyProfilePrompt/useBodyProfile 가 03-02/03-03 에서 바로 사용 가능.
- Phase 13 LLM 이 coach context 의 bodyProfile 키 (통증부위 회피·경력별 톤) 소비 가능 — 현재는 graceful 무시.
- 차단/우려: 없음. 단, EAS native build 시점에 실기기 smoke 는 03-02/03-03 UI 슬라이스에서 belle 검증 필요 (본 plan 은 UI 없음).

---
*Phase: 03-bodyprofileinput*
*Completed: 2026-06-15*

## Self-Check: PASSED

- All 8 key files verified present on disk (2 created, 6 modified).
- All 3 task commits verified in git log: cdfdfdb, 439ae79, d523cdf.
- 3-way parity grep: interface BodyProfile (analysis.ts) + def normalize_body_profile (models.py) + "BodyProfile (자가입력)" (contract.md) all present.
- test_body_profile.py 17 passed; app typecheck clean; D-05 grep gate 0 matches.
