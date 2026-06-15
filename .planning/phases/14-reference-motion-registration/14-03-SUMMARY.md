# 14-03 SUMMARY — 실 백필 실행 + 무결성 게이트 + belle 승인

**Status:** COMPLETE (belle approved 2026-06-15 — 디테일 검증은 앱에서 후속 확인하기로)
**Plan:** 14-03 (Wave 3) · autonomous: false (human-verify checkpoint)

## 무엇을 했나

11개 정은지 reference 의 downstream 필드(meanAngles + EXTEND/techniqueProfile +
BodyNormalizationProfile + ForceDirectionPattern + captureViews)를 실제 프로덕션 Firestore 에
ADD-only 머지로 백필하고, active phase4_v1 pose 가 바이트 단위로 불변임을 증명했다.

- Pod `qcf38vvsmub1y4` 에서 /health → --check-firestore(11) → RTMW 재추론 11/11 → split fixture.
- 로컬 seeder real-run: `repairMissing=11`, ADD-only, activeVersion flip 없음.
- pre/post byte-level sha256 비교: **unchangedActivePoseCount=11, changedActivePoseCount=0**.
- verify-read: completeRequiredSet **11/11** (라이브 Firestore 재확인 포함).

## key-files

### created
- `app/scripts/snapshot-reference-phase14-state.mjs` — pre/post 스냅샷 + active-pose byte-level
  hash 비교 → 14-BACKFILL-RUN-SUMMARY.json (active 변경 시 exit 1). (commit `ccaee7a`)
- `app/scripts/rollback-reference-downstream.mjs` — RESTORE-aware 롤백 (없던 필드 delete, 있던 필드
  restore; active pose 미접촉). (commit `ccaee7a`)
- `.planning/phases/14-reference-motion-registration/14-BACKFILL-RUN.md` — 실행 로그 + 리스크 런북. (`1016c31`)
- `.planning/phases/14-reference-motion-registration/14-BACKFILL-RUN-SUMMARY.json` — 머신 게이트
  (unchangedActivePoseCount=11 / changedActivePoseCount=0 / completeDownstreamFieldCount=11 /
  seededMotionCount=11). (`1016c31`)

### modified (실데이터로 발견한 deviation 2건)
- `backend/scripts/backfill_reference_downstream.py`
  - `0129f3e` — fps 9→18 정합 (REFERENCE_TARGET_FPS): phase4_v1 은 reprocess --target-fps 18.0 로
    생성됨. 9fps 추출 시 frame 수 불일치(ref-climb 257 vs 172)로 게이트가 항상 abort. 18fps 로 정합.
  - `6789f86` — angle-delta 분포 진단 로깅(mean/p95/p99/argmax).
  - `0f03781` — robust integrity gate: MAX>1.0° → (mean>0.1° OR p99>1.0°). RTMW 단일프레임 비결정성
    (ref-combo 23.43°→0.193° 재현 불가)을 허용하고 systematic pose-version shift 만 차단.

## Self-Check

- [x] 11/11 seeded, completeRequiredSet 11/11 (seeder --verify + audit + 라이브 재확인)
- [x] active pose 불변 증명 (14-BACKFILL-RUN-SUMMARY.json: unchanged=11 / changed=0)
- [x] all-or-nothing (seededMotionCount=11), no activeVersion flip
- [x] node --check + 14-01/14-02 pytest 9 passed (helper/contract 회귀 0)
- [x] Pod 정리(잉여 프로세스 kill), git clean
- [x] belle 승인 (Task 2 human-verify) — 디테일은 앱에서 후속 확인

## 후속 (belle 박제)
- **fps 정합 (reference 18 vs student 9)**: Mode 1 비교 정합은 Phase 15 의 몫.
- **일부러-실수 reference 활용**: 신규 phase 후보 ([[jeongeunji-deliberate-mistake-refs]]) — belle 와 협의 중.
