---
phase: 33-result-trust-recovery
plan: 02
subsystem: backend
tags: [firestore, backup, rollback, s3, sha256, restore-rehearsal, emulator, phase33, read-only]

# Dependency graph
requires:
  - phase: 33-result-trust-recovery
    plan: 01
    provides: "A-0 판정 '어긋남 큼' → C+M3 substrate 트랙 착수 승인 (재처리 전 롤백 원천 필요)"
provides:
  - "backend/scripts/backup_reference_docs.py — reference 11 doc 읽기전용 백업 + 4-check 게이트 + whole-file SHA-256 S3 metadata + 재다운로드 바이트 비교 + 격리 복원 리허설"
  - ".planning/debug/backups/reference-11-preC-20260723-203059.json (로컬 + S3, git-ignored) — 롤백 원천 D-31"
  - "reference-11-preC-20260723-203059.MANIFEST.json — PASS manifest (4-check + per-doc/whole-file SHA-256 + S3 검증)"
affects: [33-03, ref-student-substrate-gap, C+M3]

# Tech tracking
tech-stack:
  added:
    - "gcloud cloud-firestore-emulator component (호스트 환경 — 격리 복원 리허설용, 실 프로젝트 무접촉)"
    - "openjdk@21 (Homebrew — 에뮬레이터 Java 21+ 요건)"
  patterns:
    - "롤백 원천 = 존재 증명이 아니라 바이트 충실 + 복원 가능 증명 (temp→gate→atomic-rename, whole-file SHA-256 S3 metadata + 재다운로드 byte-compare, 격리 round-trip 리허설)"
    - "FAILED dump 은 백업 glob 미매칭 *.FAILED 로 격리 (concern 10) — 잘린 백업이 백업 행세 불가"
    - "격리 복원 리허설 = 에뮬레이터(40k index 한도 무적용) 또는 실 Firestore 격리 컬렉션(reference 면제 복제), 실 reference 절대 무접촉"

key-files:
  created:
    - backend/scripts/backup_reference_docs.py
  modified:
    - .gitignore

key-decisions:
  - "격리 복원 리허설은 Firestore 에뮬레이터로 실행 — 실 Firestore 격리 컬렉션은 40k index-entry 한도에 걸리고(대형 angles/joints3d/keypointReport 배열), 면제 설정은 SA 에 index-admin 권한이 없어 PERMISSION_DENIED. 에뮬레이터는 plan 명시 허용 경로이며 실 프로젝트 완전 무접촉"
  - "MANIFEST 파일명 = {stem}.MANIFEST.json (not {name}.MANIFEST.json) — 후자는 백업 glob reference-11-preC-*.json 에 매칭되어 sorted()[-1] 조회를 오염시킴 (Rule 1)"
  - "로컬 백업은 main repo .planning/debug/backups/ 에 기록 — worktree 는 실행 후 강제 제거되므로 S3 미러 + main-repo 로컬이 durable"

patterns-established:
  - "재처리 착수 전 롤백 게이트: 4-check(11/11 doc·isActive·activeVersion / frames triple / 배열 길이 / SHA-256) 전항 PASS 후에만 백업 glob 착지"

requirements-completed: [D-11, D-18, D-19, D-25, D-26, D-27, D-31]

# Metrics
duration: ~35min
completed: 2026-07-23
---

# Phase 33 Plan 02: Reference 11-doc 롤백 원천 백업 Summary

**reference/{id} 11 doc 전량을 읽기 전용으로 덤프해 temp→4-check 게이트→atomic-rename 로 백업 glob 에 착지시키고, whole-file SHA-256 을 S3 object metadata 로 올려 재다운로드 바이트 비교(PASS)한 뒤, 백업 JSON 을 Firestore 에뮬레이터 격리 컬렉션에 set(merge=False) 로 복원해 11/11 round-trip 바이트 일치를 증명 — 롤백 원천(D-31)이 '존재'만이 아니라 '바이트 충실 + 복원 가능'함을 백업 시점에 확정.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-23
- **Tasks:** 2/2

## What Was Built

### Task 1 — `backend/scripts/backup_reference_docs.py` (읽기 전용, 하드닝)
- 11 reference/{id} doc 을 기존 `firestore_admin.get_reference_motion` (read-only get) 으로 fetch — firebase-admin 직접 init 없음, reference 컬렉션에 어떤 set/update/delete 도 없음.
- **temp-then-atomic-rename**: canonical 직렬화(sort_keys)를 `{out}.tmp` 에 먼저 쓰고, 4-check 게이트 PASS 시에만 `os.replace` 로 백업 glob `reference-11-preC-*.json` 에 착지. FAIL 시 `*.FAILED` (glob 미매칭) + non-zero — 잘린 백업이 백업 행세 불가 (codex concern 10).
- **4-check 무결성 게이트**: (1) 11/11 doc·isActive=True·activeVersion=='phase4_v1' (2) anglesFrames==joints3dFrames==keypointReport.frames (3) len(angles)==frames×keys, len(joints3d)==frames×keys×3 (4) per-doc + whole-file SHA-256.
- **whole-file SHA-256 → S3 metadata → 재다운로드 바이트 비교**: `put_object(Metadata={sha256})` 후 `get_object` 로 재다운로드해 로컬 바이트와 비교, 저장 metadata sha256 도 대조 (codex suggestion 8).
- **`--rehearse-restore`**: 백업 JSON 을 격리 컬렉션 `reference_restore_rehearsal/{id}` 에 `set(merge=False)` 복원 → 읽어 canonical 바이트 비교 → 정리(삭제). 실 reference 무접촉 (guard: collection != 'reference').
- 별도 PASS manifest `{stem}.MANIFEST.json`. `.planning/debug/backups/` git-ignore.

### Task 2 — 백업 실행 + S3 검증 + 복원 리허설 + 산출물 열기
- 백업: **4-check 전항 PASS**, 11/11 doc. 로컬 `.planning/debug/backups/reference-11-preC-20260723-203059.json` (7,289,182 B).
- **whole-file SHA-256** = `0305275804797c9e002cb50c9b7eef2d06865c88929845c6d390b44615734122`.
- **S3**: `s3://sunity-motion-pilot-videos/backups/reference-11-preC-20260723-203059.json` — 저장 metadata sha256 == 재다운로드 sha256 == 로컬 sha256 (**byte-compare PASS**), size 7,289,182 B 일치 (live `head_object` 재확인).
- **복원 리허설**: 에뮬레이터 모드 (FIRESTORE_EMULATOR_HOST=localhost:8890) — **11/11 round-trip 바이트 일치**, 격리 doc 삭제 완료, 실 프로젝트 무접촉.
- **산출물 열기 (D-19)**: PASS manifest + per-doc SHA-256 + whole-file SHA-256 + doc 별 frames triple(anglesFrames/joints3dFrames/keypointReport.frames 전 11개 일치) + 배열 길이 항등식 + S3-vs-local checksum MATCH 를 stdout 으로 확인 — "script returned 0" 아님.

## Per-doc frames triple (열어서 확인, 전 11개 anglesFrames==joints3dFrames==keypointReport.frames)

| motion | frames | isActive | activeVersion | len(angles)=f×8 | len(joints3d)=f×17×3 |
|---|---|---|---|---|---|
| ref-climb | 257 | True | phase4_v1 | 2056 | 13107 |
| ref-foxtop | 426 | True | phase4_v1 | 3408 | 21726 |
| ref-foxtop-split | 485 | True | phase4_v1 | 3880 | 24735 |
| ref-invert | 260 | True | phase4_v1 | 2080 | 13260 |
| ref-sideway-spin | 298 | True | phase4_v1 | 2384 | 15198 |
| ref-combo | 931 | True | phase4_v1 | 7448 | 47481 |
| ref-elbow-twist-sister | 329 | True | phase4_v1 | 2632 | 16779 |
| ref-kip-up | 118 | True | phase4_v1 | 944 | 6018 |
| ref-pdshape | 237 | True | phase4_v1 | 1896 | 12087 |
| ref-peter-pan | 130 | True | phase4_v1 | 1040 | 6630 |
| ref-power-spin | 159 | True | phase4_v1 | 1272 | 8109 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 격리 복원 리허설 40k index-entry 한도 → 에뮬레이터 경로 추가**
- **Found during:** Task 2 (첫 실행)
- **Issue:** 실 Firestore 격리 컬렉션 `reference_restore_rehearsal` 에 대형 배열 doc 을 `set(merge=False)` 하자 `400 INDEX_ENTRIES_COUNT_LIMIT_EXCEEDED` — 실 reference 컬렉션은 angles/joints3d/keypointReport 인덱스 면제가 있으나 신규 격리 컬렉션엔 없음. 면제를 SA 로 프로그램 설정 시도 → `403 PERMISSION_DENIED` (firebase-adminsdk SA 에 Firestore index-admin 권한 없음, 콘솔 owner 전용).
- **Fix:** 스크립트에 에뮬레이터 모드 추가 — `FIRESTORE_EMULATOR_HOST` 설정 시 40k 한도 미적용 + 인덱스 면제 불요 + 실 프로젝트 완전 무접촉. 미설정 시엔 실 reference 면제(angles/joints3d/keypointReport)를 격리 컬렉션에 복제하는 `_ensure_rehearsal_exemptions` 경로 유지. plan 이 "isolated collection (or emulator)" 을 명시 허용 → 에뮬레이터로 리허설 완료.
- **환경 설치 (호스트, Rule 3 blocking):** `gcloud components install cloud-firestore-emulator` (first-party Google 컴포넌트) + `brew install openjdk@21` (에뮬레이터 Java 21+ 요건). 슬롭스쿼트 위험 없는 신뢰 원천만 설치. 실 Firestore/S3 프로덕션 데이터는 무변경.
- **Files modified:** backend/scripts/backup_reference_docs.py
- **Commit:** 9723c3b

**2. [Rule 1 - Bug] MANIFEST 파일명이 백업 glob 을 가림**
- **Found during:** Task 2 verify
- **Issue:** manifest 를 `{out.name}.MANIFEST.json` (= `...json.MANIFEST.json`) 로 저장하면 백업 glob `reference-11-preC-*.json` 에 매칭되고 백업 뒤로 정렬되어 plan 의 `sorted(glob(...))[-1]` 이 백업 대신 manifest 를 잡음 (KeyError 'docs').
- **Fix:** manifest 를 `{out.stem}.MANIFEST.json` 로 — 'M'<'j' 라 백업보다 먼저 정렬돼 조회 오염 없음. `*.MANIFEST.json` 검사도 동시 충족. 기존 산출 manifest 파일은 동일 내용으로 rename (데이터 무변경).
- **Files modified:** backend/scripts/backup_reference_docs.py
- **Commit:** 9723c3b

## Rollback Source (D-31) — 상태
- **로컬:** `/Users/kimtaesung/Dev/SunityMotion/.planning/debug/backups/reference-11-preC-20260723-203059.json` (+ `.MANIFEST.json`), git-ignored.
- **S3 (canonical):** `s3://sunity-motion-pilot-videos/backups/reference-11-preC-20260723-203059.json`, whole-file SHA-256 을 object metadata 로 보유, byte-compare PASS.
- **복원 절차 (SEED):** 즉시 차단 → activeVersion rollback → 부족 시 백업 JSON `set(merge=False)` 통째 복원 → measure_reference_fps 재검증 → 채점 재현 → M3 코드 revert. 리허설이 3단계(set merge=False round-trip)를 이미 증명함.

## Known Stubs
None — 백업 스크립트는 실 Firestore/S3 를 실제로 read/write(격리)하며 stub/mock 데이터 없음.

## Threat Flags
None — 신규 네트워크 엔드포인트/인증 경로 없음. reference 좌표는 PII 아님(T-33-23), 로컬 git-ignored + S3 private bucket. 격리 리허설은 에뮬레이터(in-memory) 로 프로덕션 무접촉.

## Self-Check: PASSED
- FOUND: backend/scripts/backup_reference_docs.py
- FOUND: .planning/phases/33-result-trust-recovery/33-02-SUMMARY.md
- FOUND commit 8ebc74d (Task 1), 9723c3b (Task 2)
- FOUND rollback backup json (main repo, git-ignored) + S3 mirror byte-compare PASS
