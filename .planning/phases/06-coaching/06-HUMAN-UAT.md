---
status: partial
phase: 06-coaching
source: [06-VERIFICATION.md]
started: 2026-06-08T06:05:25Z
updated: 2026-06-08T07:00:00Z
---

## Current Test

Task 2 (Pod sweep validation) — belle 운영 student 영상 수집 대기

## Tests

### 1. Plan 06-03 Task 5 — 정은지 5 reference 영상 실 Firestore 백필
expected: |
  Pod GPU 측정 (`backend/scripts/extract_reference_body_profiles.py`) → 로컬 dry-run
  (`app/scripts/seed-reference-body-profile.mjs --dry-run`) → real-run
  (`--commit`) → Firestore Console 에서 5 reference docs 모두 `bodyNormalizationProfile`
  + `bodyComparisonSourcePose` 필드가 채워졌는지 확인. 롤백 필요 시
  `app/scripts/revert-reference-body-profile.mjs --commit` 사용.
  자세한 단계 + 기대 출력 + verify 항목 8개는
  `.planning/phases/06-coaching/06-03-SUMMARY.md` 의 "Checkpoint: Task 5 — belle 운영" 섹션 참조.
result: passed
executed_at: 2026-06-08T07:00:00Z
executed_by: Claude via SSH (Pod xbdkj1g2ylnfwi RTX 4090) + 로컬 npm
evidence: |
  - Pod extract: 5/5 motion 측정 성공 (confidence 0.49~0.65, src frame conf 0.85~0.88)
  - 정은지 체형 정합: legScale 1.54~1.71, armScale 1.03~1.10, shoulderHipRatio 1.24~1.39 (5 motion 일관)
  - inversion warning: ref-foxtop / ref-foxtop-split 의 `pose_too_inverted` (의미상 정확 — 거꾸로 매달리는 트릭)
  - 로컬 dry-run PASS → `--commit`: `batch.commit OK queued=5 skipped=0`
  - 자동 verify: 5/5 docs bodyNormalizationProfile=true + bodyComparisonSourcePose=true
  - belle Firebase Console 시각 검증 OK (2026-06-08): "있다 두 필드 pose가 더 위에 있지만 있어"

### 2. Plan 06-03 Task 6 — Pod sweep validation (deferred, observational)
expected: |
  belle 운영 student 영상 수집 후 5 reference × 5 student = 25 조합 normalization
  ON vs OFF 측정. 평균 차이 reduction >= 50% PASS gate.
  Spec: `.planning/phases/06-coaching/06-03-DEFERRED-POD-SWEEP.md`.
result: [pending]

## Summary

total: 2
passed: 1
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
