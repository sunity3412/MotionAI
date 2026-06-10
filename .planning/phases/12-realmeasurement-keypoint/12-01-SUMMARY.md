---
phase: 12-realmeasurement-keypoint
plan: 12-01
subsystem: backend/python + app/typescript + docs
status: PASS
wave: 0B
commit: 1bc62eb
files_changed: 17
files_created: 8
tests_added: 7
metrics:
  duration: ~45min
  completed_date: 2026-06-10
  phase12_tests_total: 106
  phase12_tests_new: 78
  regression_phases: [06, 07, 08, 08_1, 09]
  regression_pass: 534
  regression_fail: 0
  size_budget_worst_case_kib: 170.1
  size_budget_typical_30s_kib: 37.7
  size_budget_limit_kib: 700
key-decisions:
  - "KeypointReport 3-way atomic commit (TS + Python + docs §9.12 + Firestore validator + frontend null-guard) per D-12-U1 / Phase 9 D-09-U1 mirror"
  - "axisData + axisMask 별도 field — UI 자체 계산 차단 (D-12 §12 안티 패턴), backend compute_axis_frames 단일 산출 source (A7 해소)"
  - "referenceKeypointReport field naming (NOT keypointReport) on ReferenceMotion — 의미 분리 강제 (R3 iter-2)"
  - "pipeline mode1 reference mirror 폐기 (H2 iter-4) — UI 가 useReferenceMotion 직접 read, Firestore 1 MiB 안전 마진"
  - "H3 iter-4 strict validation — data/confidence finite, confidence ∈ [0, 1], axisMask type(item) is bool strict"
---

# Phase 12 Plan 12-01: Wave 0B — KeypointReport 3-way schema lockstep Summary

KeypointReport frozen dataclass + scoped Firestore validator + axisData polyline 신설 — Wave 1 의 KeypointOverlay (Plan 12-02+) 가 받을 schema 를 단일 atomic commit 으로 TS interface + Python dataclass + docs §9.12 세 곳에 박제.

## Commit

- **SHA:** `1bc62eb`
- **Type:** `feat(12-01)`
- **Message prefix:** "feat(12-01): Wave 0B — KeypointReport 3-way schema lockstep + Firestore validator + axisData polyline"
- **Files changed:** 17 (8 신설 + 9 수정)
- **Insertions:** 2234 / Deletions: 3

## Files Created (8)

| File | Purpose |
|------|---------|
| `backend/shared/python/sunity_shared/analysis/keypoint_frame.py` | `KeypointReport` frozen dataclass + `KeypointName` Literal + `NUM_KEYPOINTS_PHASE12` + `__post_init__` validator (10 필드, H3 iter-4 strict) |
| `backend/tests/phase12/test_keypoint_report_dataclass.py` | dataclass validation (length / finite / range / strict bool / enum) — 19 test |
| `backend/tests/phase12/test_keypoint_report_lockstep.py` | docs §9.12 + TS interface + Python dataclass 3-way 정합 검증 — 9 test |
| `backend/tests/phase12/test_dataclass_to_camel_case_dict_phase12.py` | `axis_data` → `axisData` / `axis_mask` → `axisMask` 변환 검증 — 4 test |
| `backend/tests/phase12/test_firestore_lockstep_phase12.py` | `_validate_keypoint_report` 1 PASS + 18 reject + 3 wiring test |
| `backend/tests/phase12/test_build_joints_with_real_angles.py` | `assemble.build_joints` 의 currentAngle/targetAngle 채움 검증 — 4 test |
| `backend/tests/phase12/test_assemble_wiring_all_joints.py` | `build_keypoint_report` integration — axisData/axisMask invariant — 11 test |
| `backend/tests/phase12/test_keypoint_report_firestore_size_budget.py` | 9 fps × 60 s worst-case size measurement — 2 test |

## Files Modified (9)

| File | Change |
|------|--------|
| `backend/shared/python/sunity_shared/analysis/assemble.py` | `build_keypoint_report` 신설 — axis_data + axis_mask flat, missing 좌표 placeholder (0,0) + reliability "low" fallback |
| `backend/shared/python/sunity_shared/firestore_admin.py` | `_validate_keypoint_report` scoped validator + `complete_analysis(keypoint_report=)` kwarg + H3 iter-4 strict finite/range |
| `backend/shared/python/sunity_shared/models.py` | `KeypointReport / KeypointName / NUM_KEYPOINTS_PHASE12` re-export |
| `backend/functions/pipeline/app.py` | `build_keypoint_report` 호출 + `complete_analysis(keypoint_report=_dataclass_to_camel_case_dict(...))` wiring |
| `app/src/types/analysis.ts` | `KeypointName` Literal + `KeypointReport` interface + `AnalysisResult.keypointReport?` + `ReferenceMotion.referenceKeypointReport?` |
| `app/src/lib/userAnalyses.ts` | `normalize()` `keypointReport` null-guard (Phase 9 forcePatternInference mirror) |
| `app/src/lib/referenceMotions.ts` | `normalize()` `referenceKeypointReport` null-guard (R3 iter-2) |
| `app/scripts/seed-reference-motions.mjs` | `--keypoint-reports` 인자 + `referenceKeypointReport` doc 박제 (Option A scope) |
| `docs/contract.md` | §9.12 신설 (10 필드 표 + axisData/axisMask spec + frame index lookup 산식 + Phase 책임 경계) |

## Verification Gates

| Gate | Command | Result |
|------|---------|--------|
| Phase 12 전수 | `pytest backend/tests/phase12/ -x -q` | **106 PASS** (28 existing + 78 신설) |
| Regression — Phase 06/07/08/08.1/09 | `pytest backend/tests/phase06/ phase07/ phase08/ phase08_1/ phase09/ -q` | **534 PASS, 1 skipped, 0 regression** |
| AST gate (kismam wiring 회귀 차단) | `pytest backend/tests/phase12/test_kismam_assess_with_angles.py::test_kismam_assess_ast_all_calls_have_user_angles -x` | **PASS** (3 call site 모두 `user_angles=` + `reference_angles=` + `target_source=` kwarg 박제) |
| TS typecheck | `cd app && npm run typecheck` | **clean (0 error)** |
| Firestore size budget — worst case (9fps × 60s) | size measurement | **170.1 KiB ≤ 700 KiB** |
| Firestore size budget — typical 30s | size measurement | **37.7 KiB** |
| 3-way lockstep | `grep "§9.12"` docs/contract.md + TS `export interface KeypointReport` + Python `class KeypointReport` | **PASS** (10 필드 모두 일치) |

## Key Decisions (Codex 직접 리뷰 2026-06-10 반영)

1. **R1** — RTMW adapter `keypoints_2d` 채움 (Wave 0A 책임, T1 통과).
2. **R2** — `axisData` 별도 field (T × 3 × 2 polyline), `_KEYPOINT_NAMES` 8 entry 에서 axis 제외 (R11).
3. **R3** — `fps` required (default 제거), 운영 값 `9.0` single source (`frame_extractor.FRAME_RATE_FPS` 정합).
4. **R6** — confidence source = `clamp(Keypoint2D.visibility, 0, 1)`. visibility None → 0.0 + reliability "low" 강제.
5. **R7 iter-2** — `axisData` finite only (NaN 0회), `axisMask` flat T × 3 bool. knee_mid 미가용 frame 은 `(0.0, 0.0)` placeholder + `mask[2] = false`.
6. **R10** — 10 필드 (version / joints / frames / fps / data / confidence / reliability / axisData / axisMask / warnings).
7. **R11** — 8 body keypoint (axis 제외, axisData 별도). `left_hand` / `right_hand` 는 COCO-17 `left_wrist` / `right_wrist` 매핑.
8. **H2 iter-4** — pipeline mode1 reference mirror **폐기**. UI 가 `useReferenceMotion(motionId).referenceKeypointReport` 직접 read (Firestore 1 MiB 안전 마진 + single source-of-truth + drift 위험 제거).
9. **H3 iter-4** — finite + range strict validation. `data`: finite only. `confidence`: finite + `[0, 1]`. `axisMask`: `type(item) is bool` strict (int 0/1 reject).
10. **H4 iter-4** — `build_keypoint_report` early-return 조건 완화. 첫 frame `keypoints_2d=None` 단독은 drop 사유 X. 빈 list 또는 모든 frame None 만 None 반환. 개별 missing frame 은 placeholder + reliability "low".

## Deviations from Plan

**None — plan executed exactly as written.**

추가 minor 수정 (Rule 1/2 범주 아님, 단순 메시지 형식 정합):
- KeypointReport `__post_init__` 의 ValueError 메시지를 test regex (`"data finite"`, `"confidence range"`) 와 1:1 매칭하도록 reorder. 로직/검증 동일.
- `test_keypoint_report_lockstep.py` 의 section slice 가 `---` separator 가 docs 안에 등장 — `*Phase 12 Wave 0B 추가:` footer 까지 slice 변경. 검증 의도 동일.
- `test_ts_interface_has_ten_fields` 의 interface body 끝 매칭을 `"}"` → `"\n}"` 로 narrow. TS interface body 안의 `'high' | 'medium' | 'low'}` literal 의 `}` false-positive 차단.

## Threat Surface Scan

본 plan 의 모든 신설 surface 는 `<threat_model>` 의 T-12-01-V5 / T2 / T3 / V11 / S1 에 이미 mitigate disposition 박제 — 신규 threat flag 0.

| Threat ID | Mitigation 확인 |
|-----------|----------------|
| T-12-01-V5 | `__post_init__` 10 필드 length + finite + range + enum 검증 — test 19 case PASS |
| T-12-01-T2 | `_validate_keypoint_report` nested list reject — test 18 case PASS |
| T-12-01-T3 | AST gate (12-00 Wave 0A) PASS — 3 call site kwarg 박제 회귀 차단 |
| T-12-01-V11 | `build_keypoint_report` 가 `compute_axis_frames` 결과 박제 — UI 자체 계산 X (test_assemble_wiring_all_joints) |
| T-12-01-S1 | `_validate_keypoint_report` 화이트리스트 외 key reject — test_unknown_key_rejects PASS |

## Known Stubs

**None.** Wave 0B 는 schema + wiring only. Wave 1 (Plan 12-02+) 에서 KeypointOverlay 컴포넌트 + UI 소비 박제 시 stub 검증 별도.

`referenceKeypointReport` field 의 Firestore 실 채움은 belle 가 Wave 0B close-out 직후 production 정은지 영상 1 회 실 분석 후 `--keypoint-reports <path>` 인자로 seed script 재실행 (follow-up — 본 plan 책임 범위 외, seed script 자체는 박제 완료).

## TDD Gate Compliance

본 plan 은 `type: execute` (not `type: tdd` plan-level gate) — 개별 task `tdd="true"` 모드. RED/GREEN 별도 commit X (single atomic per Phase 9 mirror 정합). test 와 implementation 이 동일 commit 안 박제 — Wave 0 schema lockstep 의 정합 요구사항 (D-12-U1).

## Self-Check: PASSED

**Created files check:**
- `backend/shared/python/sunity_shared/analysis/keypoint_frame.py` — FOUND
- `backend/tests/phase12/test_keypoint_report_dataclass.py` — FOUND
- `backend/tests/phase12/test_keypoint_report_lockstep.py` — FOUND
- `backend/tests/phase12/test_dataclass_to_camel_case_dict_phase12.py` — FOUND
- `backend/tests/phase12/test_firestore_lockstep_phase12.py` — FOUND
- `backend/tests/phase12/test_build_joints_with_real_angles.py` — FOUND
- `backend/tests/phase12/test_assemble_wiring_all_joints.py` — FOUND
- `backend/tests/phase12/test_keypoint_report_firestore_size_budget.py` — FOUND

**Commit check:**
- `1bc62eb feat(12-01): Wave 0B — KeypointReport 3-way schema lockstep + Firestore validator + axisData polyline` — FOUND in `git log`

**Gate evidence:**
- 106 phase12 PASS / 534 regression PASS / tsc clean / 170.1 KiB ≤ 700 KiB.

## Next Wave Entry Gate

**Wave 1 (Plan 12-02+) 진입 조건:**
- [x] 12-00-SUMMARY.md exists (Wave 0A close-out)
- [x] 12-01-SUMMARY.md exists (본 문서)
- [ ] 12-WAVE0-AUDIT.md `STATUS: PASS` (Task T2 — keypoints_2d 가용성 grep audit, 별도 commit)
- [ ] production-like analysis 1 건의 `result.keypointReport.frames > 0` 실 확인 (mock or staging, belle UAT)

Task T2 (audit doc) + Task T3 (reference seed script extension) 은 본 commit 에 schema lockstep 만 박제. 별도 audit run + production 1 회 실 분석 follow-up 은 Wave 0B close-out 직후 belle 수행 (자동화 영역 외).
