---
phase: 33-result-trust-recovery
plan: 04
subsystem: infra
tags: [firestore, reference-versioning, rtmw, backfill, keypoint-report, body-normalization, index-exemption]

requires:
  - phase: 33-03
    provides: candidate versions/phase33-cm3-run1 (9fps + PR 인버전 재추출 angles/joints3d/keypointReport)
  - phase: 33-17
    provides: SUNITY_SHADOW_REFERENCE_VERSION overlay + candidate!=active 가드 + versions collection-group
  - phase: 33-18
    provides: /health commit-SHA canary (warm-Pod 전제)
provides:
  - candidate versions/phase33-cm3-run1 의 downstream 파생 필드 11/11 (9fps 내부 일관)
  - meanAngles/techniqueProfile/bodyNormalizationProfile/forceDirectionPattern/keypointReport/referenceKeypointReport/bodyComparisonSourcePose/captureViews
  - candidate-aware 백필 orchestrator (source+merge into versions/{candidate}, top-level 무접촉)
affects: [33-06, 33-07]

tech-stack:
  added: []
  patterns:
    - "candidate 버전에서 read + 같은 candidate 로 merge (top-level/activeVersion 무접촉, flip 분리)"
    - "live pose 1회 추론으로 bodyNorm/force/source_pose/keypointReport 동시 산출 (재추출본 재사용)"
    - "실존 producer 재사용: extract_reference_body_profiles._build_source_pose (bodyComparisonSourcePose)"

key-files:
  created:
    - .planning/phases/33-result-trust-recovery/33-S2-BACKFILL-EVIDENCE.md
  modified:
    - backend/scripts/backfill_reference_downstream.py
    - backend/scripts/extract_reference_keypoint_reports.py

key-decisions:
  - "fps 는 candidate keypointReport.fps(9.0) / --target-fps 에서 읽음 — REFERENCE_TARGET_FPS=18.0 하드코딩 제거"
  - "40k index-entry 한도 → belle 옵션 B: versions+reference collection-group 에 referenceKeypointReport 인덱스 면제 추가 (acceptance 원문 유지)"
  - "epsilon(0.1/1.0) + REFERENCE_V1_FORCE_CONFIG verbatim — gate 11/11 여유 20~200배, refit 0 (D-29)"

patterns-established:
  - "candidate 백필은 versions/{candidate} 를 source AND merge target 으로 명시 소유 (codex concern 2)"
  - "integrity gate 는 candidate angles vs live rerun (PR-on 9fps) systematic shift 만 차단"

requirements-completed: [D-18, D-19, D-20, D-25, D-27, D-29, D-30]

duration: 52min
completed: 2026-07-23
---

# Phase 33 Plan 04: candidate-aware reference downstream 백필 Summary

**정은지 reference 11종의 파생 필드(meanAngles·techniqueProfile·bodyNorm·force·keypointReport·referenceKeypointReport·bodyComparisonSourcePose)를 candidate 9fps angles 에서 재산출해 versions/phase33-cm3-run1 에만 MERGE — top-level/activeVersion 무접촉, 무결성 게이트 11/11 PASS(임계 refit 0)**

## Performance

- **Duration:** 52 min
- **Started:** 2026-07-23T12:37:06Z
- **Completed:** 2026-07-23T13:29Z
- **Tasks:** 3 (Task 0 warm-Pod canary, Task 1 재작성, Task 2 실행)
- **Files modified:** 3 (2 scripts + 1 evidence)

## Accomplishments
- `backfill_reference_downstream.py` 재작성 — TOP-LEVEL(18fps) source + "NEVER writes Firestore" → **candidate(9fps) source + 같은 candidate 로 MERGE**. fps 는 candidate 메타/CLI 에서 (18.0 하드코딩 제거).
- 실존 `bodyComparisonSourcePose` producer(`extract_reference_body_profiles._build_source_pose`) 재사용해 11/11 채움 (codex: concrete producer 없음 지적 해소).
- live pose 1회 추론으로 bodyNorm/force/source_pose/keypointReport/referenceKeypointReport 동시 산출 (fps 라벨 9.0).
- 무결성 게이트 **11/11 PASS** (meanΔ≈0.0025 vs 0.1, p99Δ≈0.005 vs 1.0 — 임계 무변경), ref-combo 결정론 유지.
- candidate 파생 필드 11/11 완주, **top-level content hash 11/11 무변경**(백필이 top-level 미접촉 증명), activeVersion=phase4_v1, `reference/_release` ABSENT 재확인.

## Task Commits

1. **Task 1: candidate-aware 백필 재작성** - `25ba727` (feat)
2. **Task 0+2(부분): S2 증거 + 인덱스 한도 발견** - `924bd04` (docs)
3. **Task 2 완주 + 증거 갱신** - 본 docs 커밋에 포함

**Plan metadata:** 최종 docs 커밋 (SUMMARY + STATE + ROADMAP)

## Files Created/Modified
- `backend/scripts/backfill_reference_downstream.py` - candidate source+merge, fps candidate/CLI, 실존 source_pose producer, keypointReport+referenceKeypointReport@9fps, epsilon/FORCE_CONFIG verbatim
- `backend/scripts/extract_reference_keypoint_reports.py` - 기본 fps 18.0→9.0, MOTION_IDS 5→11 (standalone 재산출 정합)
- `.planning/phases/33-result-trust-recovery/33-S2-BACKFILL-EVIDENCE.md` - canary + baseline + per-candidate 표 + top-level 무변경 대조

## Decisions Made
- **fps 출처**: candidate `keypointReport.fps`(9.0) 또는 `--target-fps` — `REFERENCE_TARGET_FPS=18.0` 하드코딩 폴백 제거 (codex concern 2).
- **bodyComparisonSourcePose producer**: 신규 작성 대신 실존 `_build_source_pose`(대표 frame=평균 conf 최대) 재사용.
- **epsilon/FORCE_CONFIG**: 무변경 (0.1/1.0, REFERENCE_V1_FORCE_CONFIG). gate 여유 20~200배 — refit 불필요/금지.

## Deviations from Plan

### 계획 대비 편차 (1건 — belle 결정으로 해소)

**1. [Rule 4 - 아키텍처/인프라] Firestore 40k index-entry 한도 → 인덱스 면제 추가 (옵션 B)**
- **Found during:** Task 2 (candidate MERGE)
- **Issue:** 대형 배열 `referenceKeypointReport` 가 `versions` collection-group 에서 인덱스 면제되어 있지 않아, ref-combo(621f) candidate 문서가 40,000 index-entry 한도 초과 → MERGE 부분 실패(5/11 write, active pointer 무접촉).
- **Resolution:** belle 옵션 B 선택. 오케스트레이터가 single-field 인덱스 면제 2건 추가(`versions`·`reference` collection-group, field=`referenceKeypointReport`). 원래 acceptance("referenceKeypointReport in candidate 11/11") 원문 유지.
- **Fix:** 면제 추가 후 동일 백필 재실행 → 11/11 MERGE(멱등 merge 로 5개 부분 write 덮어쓰기), PY_EXIT=0, failures=[].
- **Verification:** probe 재실행 — 파생 필드 11/11 존재, keypointReport.fps=9.0, referenceKeypointReport 11/11, top-level hash 11/11 무변경.
- **Committed in:** 924bd04 (발견) + 본 docs 커밋 (해소 증거).

---

**Total deviations:** 1 (Rule 4 — checkpoint 후 belle 결정으로 해소). **Impact:** acceptance 원문 그대로 충족, 채점/코어 무접촉. scope creep 없음.

## Issues Encountered
- 로그 stdout(28KB JSON print, block-buffered) vs stderr(logging, line-buffered) 인터리브로 1차 판독 혼선 — Firestore 실측(probe) 을 ground truth 로 삼아 부분 write 정확 판정.

## User Setup Required
None - belle 는 옵션 B 결정만 제공, 인덱스 면제는 오케스트레이터가 실행.

## Next Phase Readiness
- **33-06 (검증)**: candidate phase33-cm3-run1 이 9fps 내부 일관(파생 필드 11/11) → self-comparison/전수 검증 준비 완료.
- **33-07 (flip)**: candidate consumer 필드 + referenceKeypointReport(면제 top-level 미러 예방 완료) 준비. active pointer 무접촉 상태 유지.
- Pod k508k3lut0o3f1 warm, 서버 2549 가동 중 (재시작 없음).

## Self-Check: PASSED

- Files: 33-04-SUMMARY.md ✓, 33-S2-BACKFILL-EVIDENCE.md ✓, backfill_reference_downstream.py ✓, extract_reference_keypoint_reports.py ✓
- Commits: 25ba727 ✓, 924bd04 ✓
- Firestore ground truth: 파생 필드 11/11, keypointReport.fps=9.0, referenceKeypointReport 11/11, top-level hash 11/11 무변경, activeVersion=phase4_v1, _release ABSENT
- D-20: sunity_shared 채점 파일 diff 0

---
*Phase: 33-result-trust-recovery*
*Completed: 2026-07-23*
