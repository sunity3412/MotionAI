---
status: partial
phase: 06-coaching
source: [06-VERIFICATION.md]
started: 2026-06-08T06:05:25Z
updated: 2026-06-08T06:05:25Z
---

## Current Test

[awaiting human testing]

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
result: [pending]

### 2. Plan 06-03 Task 6 — Pod sweep validation (deferred, observational)
expected: |
  belle 운영 student 영상 수집 후 5 reference × 5 student = 25 조합 normalization
  ON vs OFF 측정. 평균 차이 reduction >= 50% PASS gate.
  Spec: `.planning/phases/06-coaching/06-03-DEFERRED-POD-SWEEP.md`.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
