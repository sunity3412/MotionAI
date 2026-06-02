---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: 19
subsystem: backend/pose_contract
tags: [rtmw-pivot, contract, adr, lockstep, gap-closure, wave-1]
requires:
  - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md D-17~D-25
  - /Users/kimtaesung/Downloads/Sunity_v1_개발지시_RTMW무료스택.md
provides:
  - backend/shared/python/sunity_shared/analysis/body_normalization.py
  - PoseFrame.body_shape nullable 필드 (Python + TS)
  - BodyNormalizationProfile interface (TS)
  - docs/contract.md §7 BodyNormalizationProfile 명세
  - docs/adr/ADR-0001-poseengine-interface-rtmw-pivot.md
affects:
  - app/src/types/analysis.ts (PoseFrame interface 10 필드, BodyNormalizationProfile 신설)
  - backend/shared/python/sunity_shared/models.py (BodyNormalizationProfile re-export)
  - backend/shared/python/sunity_shared/analysis/interfaces.py (PoseEngine docstring 보강)
  - backend/shared/python/sunity_shared/analysis/pose_frame.py (PoseFrame.body_shape)
  - backend/tests/test_pose_frame_contract.py (EXPECTED 9→10 필드 lockstep 갱신)
tech-stack:
  added: []
  patterns:
    - 3-way lockstep (TS ↔ Python ↔ contract.md)
    - Michael Nygard ADR 템플릿
    - Forward-ref (TYPE_CHECKING) 로 순환 import 차단
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/body_normalization.py
    - backend/tests/test_pose_engine_contract.py
    - backend/tests/test_body_normalization_profile.py
    - backend/tests/test_body_normalization_lockstep.py
    - docs/adr/ADR-0001-poseengine-interface-rtmw-pivot.md
  modified:
    - backend/shared/python/sunity_shared/analysis/interfaces.py
    - backend/shared/python/sunity_shared/analysis/pose_frame.py
    - backend/shared/python/sunity_shared/models.py
    - app/src/types/analysis.ts
    - docs/contract.md
    - backend/tests/test_pose_frame_contract.py
decisions:
  - D-17 운영 백본 = RTMW 133 wholebody (Apache-2.0). PoseEngine Protocol 호환 유지.
  - D-19 BodyNormalizationProfile = SMPL-X β 없이 segment 비율. dataclass 박제.
  - D-21 PoseFrame.body_shape nullable — RTMW=None / NLF_SMPLX=β path 양쪽 호환.
  - D-24 PoseEngine 인터페이스 추상화 필수. 다운스트림 무수정 보장 (interfaces.py 가 rtmlib/mediapipe/torch/ultralytics 직접 import 부재 — AST 검증).
metrics:
  duration_minutes: 35
  completed_date: 2026-06-02
  tasks_completed: 3
  files_created: 5
  files_modified: 6
  tests_added: 19
  tests_passed: 42
---

# Phase 1 Plan 19: PoseEngine 인터페이스 + BodyNormalizationProfile + ADR-0001 Summary

RTMW 무료 스택 pivot (D-17~D-25) 의 첫 작업으로 PoseEngine 인터페이스 + 공통 데이터 계약 (PoseFrame.body_shape nullable, BodyNormalizationProfile) 을 backend-agnostic 하게 박제하고 ADR-0001 로 결정 근거 + 다운스트림 무수정 약속 + 향후 NLF/SMPL-X 재도입 절차를 단일 문서로 추적 가능하게 만든 plan.

## Tasks Completed

| Task | Name | Commits | Status |
|------|------|---------|--------|
| 1 | PoseEngine Protocol 보강 + BodyNormalizationProfile dataclass + PoseFrame.body_shape nullable (D-19/D-21/D-24) | `487ebdc` (RED), `2377c21` (GREEN) | DONE |
| 2 | TS ↔ Python ↔ contract.md 3-way lockstep — BodyNormalizationProfile + PoseFrame.bodyShape 동기화 | `52f2da2` (RED), `a91f9ec` (GREEN) | DONE |
| 3 | ADR-0001 작성 — RTMW pivot 결정 + PoseEngine 인터페이스 약속 박제 | `1c4aad4` | DONE |

## Verification Results

- **`backend/tests/test_pose_engine_contract.py`** — 9 contract 테스트 PASS (Protocol 시그니처, backend-agnostic AST 검증, BodyNormalizationProfile 필드/SMPL-X 잔여 부재/confidence range/warnings 타입, PoseFrame.body_shape nullable, 기존 9 필드 회귀 없음, pose_engines `__all__` 노출).
- **`backend/tests/test_body_normalization_profile.py`** — 5 validator behavior 테스트 PASS (필드 필수, confidence 경계, warnings 타입).
- **`backend/tests/test_body_normalization_lockstep.py`** — 5 lockstep 테스트 PASS (TS bodyShape 필드, TS interface 7 필드, Python models.py mirror, contract.md 7 필드 명시, TS↔Python 필드명 1:1).
- **회귀 — `test_pose_frame_contract.py` + `test_pose_engine_interface.py` + `test_reliability_gate.py`** — 23 기존 테스트 PASS.
- **총 42 backend tests PASS.**
- **`cd app && npm run typecheck`** — no errors (TS strict mode).
- **Acceptance grep counts** — bodyShape in TS = 3 (≥2 통과), BodyNormalizationProfile in TS = 4 (≥3 통과), in contract.md = 7 (≥2 통과), body_shape/BodyNormalizationProfile in models.py = 4 (≥2 통과).
- **ADR-0001** — D-17~D-25 9개 모두 등장, 25 섹션 헤더, RTMW(46)·MediaPipe(13)·NLF(30)·SMPL-X(17)·Apache-2.0(9)·IPSF(8) 키워드 전부 존재.

## Key Decisions Made

- **D-19 박제**: `BodyNormalizationProfile` dataclass = `estimated_height_scale / arm_scale / leg_scale / torso_scale / shoulder_hip_ratio / confidence / warnings` 7 필드. `beta / smplx_beta / shape_params / betas` 같은 SMPL-X 잔여 필드는 영구히 contract 에 도입하지 않는다. `test_body_normalization_profile_no_smplx_beta` (T-19-02 mitigation) 가 잔여 부재를 강제.
- **D-21 박제**: `PoseFrame.body_shape: Optional[BodyNormalizationProfile] = None` — RTMW 운영 path = None, NLF_SMPLX R&D path = `BodyNormalizationProfile` 채움. 양쪽 호환.
- **D-24 운영 강제**: `test_pose_engine_protocol_backend_agnostic` 가 `interfaces.py` AST 를 walk 하여 `rtmlib / mediapipe / torch / ultralytics` 직접 import 부재를 검증 (T-19-01 mitigation). PoseEngine Protocol 이 RTMW 와 NLF_SMPLX 양쪽 구현체 모두에서 만족 가능하도록 backend-agnostic 유지.
- **lockstep 패턴 박제**: `models.py` 의 `analysis.body_normalization` re-export + TS interface 신설 + contract.md §7 신설. `test_ts_python_field_name_lockstep` 가 drift 방어.
- **ADR-0001 박제**: Michael Nygard 8 섹션 형식. D-17~D-25 결정 + supersede 정리 (Plan 04/05/14 + 02/03/07/08/10/11/16/17 R&D 격리 + Plan 18 on hold) + 향후 NLF/SMPL-X 재도입 절차. `[[rtmw-free-stack-pivot]]`, `[[plan-18-on-hold-rtmw-pivot]]`, `[[license-blocklist-pose]]`, `[[analysis-objectivity-no-human-scores]]`, `[[judging-baseline-ipsf-code-of-points]]` 메모리 cross-reference.

## Files Created

- `backend/shared/python/sunity_shared/analysis/body_normalization.py` — `BodyNormalizationProfile` frozen dataclass (D-19 segment 비율 + confidence + warnings + `__post_init__` validator).
- `backend/tests/test_pose_engine_contract.py` — 9 contract 테스트 (Protocol 시그니처, backend-agnostic AST 검증, BodyNormalizationProfile/PoseFrame 필드 검증, pose_engines `__all__`).
- `backend/tests/test_body_normalization_profile.py` — 5 validator behavior 테스트.
- `backend/tests/test_body_normalization_lockstep.py` — 5 TS↔Python↔contract.md lockstep 테스트.
- `docs/adr/ADR-0001-poseengine-interface-rtmw-pivot.md` — RTMW pivot ADR (D-17~D-25 박제).

## Files Modified

- `backend/shared/python/sunity_shared/analysis/interfaces.py` — `PoseEngine` Protocol docstring 보강 (D-17/D-20/D-21/D-24 RTMW pivot 인용). `estimate()` 시그니처 변경 없음.
- `backend/shared/python/sunity_shared/analysis/pose_frame.py` — `body_shape: Optional[BodyNormalizationProfile] = None` 필드 추가 (10번째 필드). `TYPE_CHECKING` forward-ref 로 순환 차단. `empty()` classmethod 에 `body_shape` 인자 추가. docstring 9 → 10 필드 갱신.
- `backend/shared/python/sunity_shared/models.py` — `BodyNormalizationProfile` re-export (TS lockstep 위치 명시).
- `app/src/types/analysis.ts` — `BodyNormalizationProfile` interface 신설 (camelCase 7 필드) + `PoseFrame.bodyShape: BodyNormalizationProfile | null` 필드 추가 + docstring 9 → 10 필드 갱신.
- `docs/contract.md` — §6 PoseFrame 표에 `bodyShape` 행 추가, §7 BodyNormalizationProfile 신설 (7 필드 표 + D-19/D-21 요약 + Phase 2 BODY-01 consumer 예고 + NLF_SMPLX 재도입 절차).
- `backend/tests/test_pose_frame_contract.py` — `EXPECTED_POSE_FRAME_FIELDS` 9 → 10 필드 lockstep 갱신 + docstring 정정.

## Deviations from Plan

### Rule 1 (Auto-fixed regression)

**1. [Rule 1 - Bug] 기존 `test_pose_frame_contract.py::test_pose_frame_lockstep_fields` 회귀**
- **Found during:** Task 1 GREEN 후 회귀 검증.
- **Issue:** 기존 lockstep 테스트가 `EXPECTED_POSE_FRAME_FIELDS = {9 필드}` 로 고정 — PoseFrame 에 `body_shape` 추가 (D-21) 시 set 비교 실패.
- **Fix:** `EXPECTED_POSE_FRAME_FIELDS` 에 `body_shape` 추가 (10번째) + docstring 9 → 10 필드 갱신 + 2026-06-02 Plan 01-19 갱신 주석 박제.
- **Files modified:** `backend/tests/test_pose_frame_contract.py`
- **Commit:** `2377c21` (Task 1 GREEN 함께 포함)
- **Justification:** 본 plan 의 의도된 lockstep 갱신 — D-21 (body_shape nullable) 박제의 직접 결과. Plan PLAN.md `<files>` 절에 해당 파일 명시 안 됨이지만 contract 변경 시 동일 contract 를 검증하는 회귀 테스트도 동일 commit 에 갱신해야 lockstep 이 유지됨 (CLAUDE.md Cross-cutting 룰).

## Known Stubs

None — 본 plan 은 contract 박제 plan 으로 사용자 가시 슬라이스 산출 없음. Phase 2 BODY-01 측정기가 본 contract 를 채울 때까지 `PoseFrame.body_shape` 는 RTMW 운영 path 에서 항상 `None` 으로 유지 (의도된 nullable). 이는 Plan 21 (RTMW 통합) 의 진입 게이트.

## Threat Flags

None — 본 plan 은 contract 박제만으로 새 네트워크 endpoint / auth path / file access / schema 변경 없음. 기존 threat register (T-19-01/02/03) 는 Task 1/2 의 테스트로 mitigation 완료.

## TDD Gate Compliance

- Task 1: `test(01-19): add failing PoseEngine + BodyNormalizationProfile contract tests` (`487ebdc`, RED) → `feat(01-19): PoseEngine 인터페이스 + BodyNormalizationProfile + PoseFrame.body_shape` (`2377c21`, GREEN). RED → GREEN 순서 commit 게이트 통과.
- Task 2: `test(01-19): add failing TS↔Python↔contract.md lockstep tests` (`52f2da2`, RED) → `feat(01-19): TS↔Python↔contract.md lockstep` (`a91f9ec`, GREEN). RED → GREEN 순서 commit 게이트 통과.
- Task 3: `auto` (non-TDD) — ADR 문서 작성, behavior 없음. `docs(01-19)` 단일 commit.

## Self-Check: PASSED

- `[ -f backend/shared/python/sunity_shared/analysis/body_normalization.py ]` — FOUND.
- `[ -f backend/tests/test_pose_engine_contract.py ]` — FOUND.
- `[ -f backend/tests/test_body_normalization_profile.py ]` — FOUND.
- `[ -f backend/tests/test_body_normalization_lockstep.py ]` — FOUND.
- `[ -f docs/adr/ADR-0001-poseengine-interface-rtmw-pivot.md ]` — FOUND.
- Commits `487ebdc / 2377c21 / 52f2da2 / a91f9ec / 1c4aad4` — all present in `git log --oneline -10`.

## Plan 21 진입 게이트 통과

본 plan 의 산출물은 plan 21 (RTMW 통합) 의 입력. PoseEngine Protocol + PoseFrame + BodyNormalizationProfile 3 contract 가 RTMW 와 NLF_SMPLX 양쪽 호환으로 박제됨. belle 명시 "대량 코딩 전 모듈 구조 / PoseEngine 인터페이스 / 공통 타입 먼저 제안 + 질문" 요구 충족 — Plan 21 의 RTMWPoseEngine 이 본 contract 를 직접 import 해서 사용 가능. ADR-0001 이 Phase 1 의 후속 plan 22~25 의 결정 근거 단일 진실로 박제됨.
