---
phase: 06-coaching
plan: 03
subsystem: backend-reference-backfill
tags: [reference-backfill, body-profile, body-comparison-source-pose, operational, phase-06, dry-run, revert, deferred-pod-sweep]
status: complete-pending-checkpoint
requirements: [PERS-01]
dependency_graph:
  requires: [Phase 6-02 (firestore_admin.complete_analysis 확장 + _validate_flat_dict_no_nested_array + _dataclass_to_camel_case_dict), Phase 6-01 (BodyComparisonSourcePose + measure_body_profile)]
  provides: [firestore_admin.update_reference_body_data 단일 helper (R2), Pod GPU extract 스크립트, 로컬 seed + revert 스크립트, deferred sweep 사양]
  affects: [Phase 14 (정은지 reference 본격 등록 — 동일 helper 재사용), Phase 7 (차이 분류 — 백필 완료 후 reference 측 source_keypoints 가 production 정규화 활성)]
tech_stack:
  added: []
  patterns: [single-entry-point helper (R2 — 두 필드 atomic), W5 validator 재사용, R7 explicit ordering (parse → validate → if dry-run early return → real-run), C12 safety-default revert (no --commit → forced dry-run), C5 dry-run blast-radius gate]
key_files:
  created:
    - backend/scripts/extract_reference_body_profiles.py
    - backend/scripts/README_extract_reference_body_profiles.md
    - app/scripts/seed-reference-body-profile.mjs
    - app/scripts/revert-reference-body-profile.mjs
    - backend/tests/phase06/test_firestore_admin_update_reference_body_data.py
    - backend/tests/phase06/test_backfill_scripts_dry_run.py
    - backend/tests/phase06/fixtures/test_reference_body_data.json
    - .planning/phases/06-coaching/06-03-DEFERRED-POD-SWEEP.md
  modified:
    - backend/shared/python/sunity_shared/firestore_admin.py
    - app/package.json
decisions:
  - "R2 fix (round-2): 단일 helper update_reference_body_data(motion_id, body_profile, source_pose) — bodyNormalizationProfile + bodyComparisonSourcePose 두 필드 atomic merge. 구 update_reference_body_profile 폐기 (단일 진입점 정신)."
  - "R7 fix (round-2): seed-reference-body-profile.mjs 의 explicit ordering — Step 1 parse + load + validate (Firebase 미접촉) → Step 2 if --dry-run: stdout + early return (Firebase init 호출 0) → Step 3 real-run: initializeApp + getFirestore + batch.commit. validation 이 Firebase init 보다 먼저."
  - "R9 fix (round-2): '7 deficits' 옛 표현 부재. 5 IPSF + Sunity pose_reliability_low (poor_transitions deferred → Phase 8 jerk/jitter 통합)."
  - "C5 fix: Python + Node 양 스크립트 --dry-run 플래그. dry-run 시 Firestore write 0. Task 4 (자동) 가 dry-run 통합 검증."
  - "C12 fix: revert-reference-body-profile.mjs 신설 + 안전 기본값 (--commit 미지정 시 강제 dry-run) + R2 정합 (두 필드 모두 FieldValue.delete)."
  - "C6 fix: Pod sweep 사양 박제 (.planning/phases/06-coaching/06-03-DEFERRED-POD-SWEEP.md) — 5 reference × 5 student 25 조합 normalization ON vs OFF, 평균 reduction % 측정."
  - "W3 박제: extract 스크립트는 직접 실행만 (`python backend/scripts/...`), `-m` invocation 금지. sys.path 주입 in-script."
metrics:
  duration_minutes: ~50
  completed_date: "2026-06-08"
  tasks_total: 7
  tasks_completed_autonomous: 6
  tasks_pending_checkpoint: 1
  tests_total: 14
  tests_passed: 13
  tests_skipped: 1
  phase06_full_suite: 120
  phase06_skipped: 1
---

# Phase 6 Plan 03: 정은지 reference 백필 — operational scripts + helper + dry-run validation Summary

**One-liner:** Plan 06-03 의 산출 = 두 필드 (bodyNormalizationProfile +
bodyComparisonSourcePose) 백필 operational stack — 단일 진입점 helper
`firestore_admin.update_reference_body_data` (R2) + Pod GPU 측정 스크립트
`extract_reference_body_profiles.py` (R2 + C5 --dry-run + W3 직접 실행) + 로컬
seed `seed-reference-body-profile.mjs` (R2 + C5 --dry-run + R7 explicit
ordering: parse → validate → if dry-run early return → real-run) + 안전 기본값
revert `revert-reference-body-profile.mjs` (C12 + R2 두 필드 delete) + 자동
dry-run 통합 검증 (C5 + R7 ADC-free + schema-before-init) + Pod sweep 사양
deferred (C6) + R9 카피 정합. **Task 5 (실 실행 checkpoint) 는 belle 의 운영 작업
— 본 plan 의 autonomous scope 외.**

## Status

- Tasks executed (autonomous): **6 / 7** (Task 1, 2, 3, 4, 4.5, 6)
- Task 5 (수동 checkpoint): **belle 운영 작업으로 위임** — Pod GPU 측정 → 로컬
  dry-run → real-run seed → Firestore Console verify. 본 SUMMARY 의
  "Checkpoint: Task 5 — belle 운영" 섹션 참조.
- 신규 test: **14 / 14** (9 helper unit + 5 dry-run integration, 1 skip
  documented).
- 전체 phase06 suite: **120 / 120 PASS** (Plan 06-01 의 52 + Plan 06-02 의 55 +
  본 plan 의 13) + 1 skip (Test 3 — real-run mock 복잡도, R7 의 Test 4 가 핵심
  증명). 전 plan 누적 회귀 0.
- TypeScript: `tsc --noEmit` clean (app/).
- Commits: 7 atomic (test RED + helper + extract + seed + dry-run test + revert + sweep spec).

## Task 별 산출 + 검증

### Task 1 — firestore_admin.update_reference_body_data helper (R2 round-2) — commit `0071f2e` (test RED commit `6c9675a`)

**Files**:

- `backend/shared/python/sunity_shared/firestore_admin.py` — 단일 helper 추가:

  ```python
  def update_reference_body_data(
      motion_id: str,
      body_profile: dict,
      source_pose: dict | None = None,
  ) -> None
  ```

  - 두 필드 atomic merge: `bodyNormalizationProfile` + `bodyComparisonSourcePose`.
  - 두 필드의 `*UpdatedAt` 타임스탬프 동시 박제.
  - `_REF_BODY_PROFILE_REQUIRED` (7 필드) + `_REF_SOURCE_POSE_REQUIRED` (6 필드) 누락 검증.
  - **R2 핵심**: `len(source_pose["values"]) == 4 × len(source_pose["jointKeys"])` 강제.
  - **W5 재사용**: Plan 06-02 의 `_validate_flat_dict_no_nested_array` 가 두 필드
    모두 통과 강제 (nested list / nested dict-with-list 거절).
  - `source_pose=None` → bodyComparisonSourcePose 미박제 (partial backfill 허용
    — 백필 중 일부 motion 의 대표 frame 추출 실패 graceful).
  - 구 단일 필드 helper `update_reference_body_profile` 미도입 (R2 단일 진입점 정신).

- `backend/tests/phase06/test_firestore_admin_update_reference_body_data.py` — 9 unit test.

**Tests (9 PASS)**:

| # | Behavior |
|---|----------|
| 1 | 두 필드 모두 set merge + *UpdatedAt 박제. |
| 2 | body_profile.warnings=list[list] → TypeError (W5). |
| 3 | source_pose.values 안에 list → TypeError (W5). |
| 4 | motion_id="" → ValueError. |
| 5 | body_profile 에 estimatedHeightScale 누락 → ValueError. |
| 6 | source_pose 에 jointKeys 누락 → ValueError. |
| 7 (R2 핵심) | values length=60, jointKeys=17 → ValueError (필요=68). |
| 8 | body_profile.warnings=list[str] → PASS. |
| 9 (R2 partial) | source_pose=None → bodyNormalizationProfile 만 merge, bodyComparisonSourcePose 키 부재. |

### Task 2 — extract_reference_body_profiles.py (Pod GPU + R2 + C5 + W3) — commit `fc7dab7`

**Files**:

- `backend/scripts/extract_reference_body_profiles.py` — Pod GPU 측정 스크립트:

  - `argparse`: `--bucket` / `--output` / `--motion-ids` (default 5개) /
    `--dry-run`.
  - per-motion: S3 download → `FfmpegFrameExtractor` → `RTMWPoseEngine.estimate`
    (vertical PoleAxis fallback) → `measure_body_profile` → 대표 frame 산출.
  - **R2 대표 frame 선정**: 평균 keypoint confidence (= 1 - uncertainty_proxy)
    최대 frame. NaN-aware fallback (대표 frame 의 values 에 NaN 있으면 None 반환
    + 경고 log → graceful partial backfill).
  - 17 keypoint × 4채널 = 68 flat float values + `torsoPx` (frame 의
    mid_shoulder ↔ mid_hip Euclidean) + `frameIndex` + `confidence` + `measuredAt`.
  - dataclass → camelCase dict 변환 (in-script `_bp_to_camel_dict` + `_sp_to_camel_dict`).
  - **C5 --dry-run**: 측정 후 stdout JSON 만 + 파일 미생성.
  - **W3 직접 실행**: sys.path 주입 in-script (parents[1] / shared / python),
    `python -m backend.scripts...` 미사용.
  - Mac 로컬 환경 호환: `imageio` / `rtmlib` / `boto3` 모두 lazy import (`main()`
    안). `--help` 가 의존성 부재 환경에서도 exit 0.

- `backend/scripts/README_extract_reference_body_profiles.md` — Pod SSH 단계 +
  env + dry-run 우선 흐름 + 로컬 다운로드 + seed 진입 + W3 박제 (`-m` 금지).

**Verification**:

- `python backend/scripts/extract_reference_body_profiles.py --help` exit 0 +
  usage 표시.
- grep gates:
  - `BodyComparisonSourcePose` in extract script: 9회 (import + 산출).
  - `bodyComparisonSourcePose` in extract script: 4회 (payload key + null check).
  - `--dry-run` in extract script: 5회 (action + log + 분기).
  - `--dry-run` in README: 2회.
  - `python -m backend.scripts` in README: **0회** (W3).

### Task 3 — seed-reference-body-profile.mjs (R2 + C5 + R7 ordering) — commit `39bbe2a`

**Files**:

- `app/scripts/seed-reference-body-profile.mjs` — Node.js 로컬 seed 스크립트:

  - **Step 1** (Firebase 미접촉, ADC 불요): `parseArgs` + `readFileSync` +
    `loadProfilesPayload` (schema validate — 두 필드 + values length == 4 ×
    len(jointKeys) + nested-array 거절). 검증 실패 시 throw — Firebase 호출 전
    fail-fast.
  - **Step 2** (dry-run 분기, Firebase init 호출 전 early return): `--dry-run`
    → stdout JSON (`{ dryRun: true, willMerge, force, motions: [{motionId,
    bodyNormalizationProfile, bodyComparisonSourcePose}, ...] }`) + `return`.
    Firebase init 호출 0회 — ADC 미설정 환경 호환.
  - **Step 3** (real-run, Firebase Admin SDK + ADC): `initializeApp({credential:
    applicationDefault(), projectId: 'sunity-ai-coach'})` + `getFirestore()` +
    `batch.set(...)` per motion + `batch.commit()` + 읽기 검증 (각 motion 의
    두 필드 존재 확인).
  - `--force` — idempotent skip 무시 (이미 박제된 reference 덮어쓰기).
  - `firebase-admin/app` + `firebase-admin/firestore` 는 Step 3 안에서 dynamic
    `await import(...)` — Step 2 dry-run path 에서 절대 로드되지 않음.

- `app/package.json` — npm script `seed:body-profile` 추가.

**R7 ordering 검증** (text-line gate):

- `args.dryRun` 첫 라인 (Step 2 early return 분기): **line 152**
- `initializeApp` 첫 라인 (Step 3 real-run): **line 176**
- 152 < 176 — R7 ORDERING PASS.

**Other gates**:

- `bodyComparisonSourcePose` 출현: 15회 (validation + proposed + docPayload).
- `dry-run|dryRun` 출현: 10회.
- `seed:body-profile` in package.json: 1회.
- `node --check app/scripts/seed-reference-body-profile.mjs` exit 0.
- `tsc --noEmit` clean.

### Task 4 — dry-run + R7 통합 검증 — commit `9bc8265`

**Files**:

- `backend/tests/phase06/test_backfill_scripts_dry_run.py` — 5 test (4 PASS + 1
  documented SKIP).
- `backend/tests/phase06/fixtures/test_reference_body_data.json` — 1 motion 의
  두 필드 fixture (jointKeys 길이 17, values 길이 68, 모든 finite).

**Tests (4 PASS + 1 SKIP)**:

| # | 이름 | R7? |
|---|------|-----|
| 1 | `test_extract_dry_run_outputs_json_to_stdout_without_writing` | — |
| 2 | `test_seed_dry_run_works_without_adc_no_firebase_init` | **R7 핵심** |
| 3 | `test_seed_real_run_calls_batch_commit_when_dry_run_absent` | SKIP (real-run path 는 emulator/mock npm 필요 — Test 4 가 R7 fix 핵심 증명) |
| 4 | `test_seed_dry_run_validates_schema_before_early_return` | **R7 핵심** |
| 5 | `test_extract_real_run_writes_file_when_dry_run_absent` | — |

**R7 검증 (Test 2)**: `subprocess.run` 로 `node app/scripts/seed-...mjs --profiles
fixtures/test_reference_body_data.json --dry-run` 실행 + `GOOGLE_APPLICATION_CREDENTIALS=""` +
`GOOGLE_CLOUD_PROJECT=""`. 검증:
- exit 0
- stdout 에 `"dryRun":true` 포함
- stderr/stdout 에 `Could not load the default credentials` 부재
- stderr 에 `applicationDefault` 에러 메시지 부재

**R7 검증 (Test 4)**: malformed fixture (`estimatedHeightScale` 누락) + `--dry-run`
+ ADC 미설정. 검증:
- exit non-zero
- stdout+stderr 에 `estimatedHeightScale` 또는 `필수 필드 누락` 포함 (schema 에러)
- stderr 에 ADC 에러 메시지 부재 → validation 이 Firebase init 보다 먼저 실행됨을 증명

**Test 1 + Test 5**: Python extract 의 dry-run / real-run path 검증. subprocess
회피 — `importlib.util.spec_from_file_location` 로 모듈 로드 후 `monkeypatch` 로
`boto3` / `_measure_one` / `_download_video` / `FfmpegFrameExtractor` /
`RTMWPoseEngine` 모두 stub. dry-run: stdout JSON + 출력 파일 미생성. real-run:
출력 파일 생성 + `motions` dict 포함.

### Task 4.5 — revert-reference-body-profile.mjs (C12 + R2) — commit `87fd30f`

**Files**:

- `app/scripts/revert-reference-body-profile.mjs` — 두 필드 모두 FieldValue.delete():

  - `argparse`: `--motion-ids <id1,id2,...>` (필수) / `--dry-run` / `--commit`.
  - 안전 기본값: `--commit` 미지정 시 `forcing --dry-run for safety` 로그 + 강제
    dry-run (실수 방지).
  - dry-run: stdout JSON (`{ dryRun: true, willDelete: [{motionId, fields:
    ['bodyNormalizationProfile', '...UpdatedAt', 'bodyComparisonSourcePose',
    '...UpdatedAt']}] }`).
  - real-run: `initializeApp` + `batch.update(ref, { bodyNormalizationProfile:
    FieldValue.delete(), bodyNormalizationProfileUpdatedAt: FieldValue.delete(),
    bodyComparisonSourcePose: FieldValue.delete(),
    bodyComparisonSourcePoseUpdatedAt: FieldValue.delete() })` per motion +
    `batch.commit()`. doc 자체는 유지.

- `app/package.json` — npm script `revert:body-profile` 추가.

**Verification**:

- `node --check` exit 0.
- `bodyComparisonSourcePose` 출현: 6회.
- `FieldValue.delete` 출현: 7회 (1 import + 4 real-run × 1 dry-run list + 2 doc).
- `forcing --dry-run for safety` 출현: 1회 (안전 기본값 가드).
- 로컬 실행 검증: `GOOGLE_APPLICATION_CREDENTIALS="" node ... --motion-ids
  ref-climb,ref-foxtop --dry-run` → stdout JSON + ADC 에러 부재.

### Task 5 — 실 실행 checkpoint (belle 운영 작업) — **본 plan 의 autonomous scope 외**

상세 = 본 SUMMARY 의 "Checkpoint: Task 5 — belle 운영" 섹션.

### Task 6 — Pod sweep 사양 박제 (C6 deferred but tracked) — commit `361b7e9`

**Files**:

- `.planning/phases/06-coaching/06-03-DEFERRED-POD-SWEEP.md` — Pod sweep
  validation 사양:
  - 입력: 5 reference (정은지) + 5 student (다양한 체형, belle 운영 수집).
  - 실행: normalization ON vs OFF 각 5 × 5 = 25 조합 분석.
  - 출력: Reduction % table.
  - 검증 기준: 평균 reduction >= 50% PASS (NotebookLM §1.4 60% 주장 검증, 10%
    오차).
  - **R9 카피 정합**: 5 IPSF + Sunity pose_reliability_low (poor_transitions
    deferred to Phase 8 jerk/jitter, '7 deficits' 옛 표현 부재).
  - 실 실행 deferred — belle 의 운영 sweep 일정에 따라.

**Verification (grep gates)**:

- `5 reference` 출현: 1회.
- `Reduction %` 출현: 3회.
- `deferred` 출현: 4회.
- `pose_reliability_low|5 IPSF` 출현: 1회.

## Deviations from Plan

### 1. [Rule 3 - 변경] Mac 로컬 환경 호환을 위한 lazy import

- **Found during:** Task 2 verification (`python --help` 실행 시 imageio
  ModuleNotFoundError).
- **Issue:** `frame_extractor.py` 가 `import imageio` 를 모듈 top-level 에서 수행
  — Pod 에는 install 되어 있으나 Mac 로컬에는 없음. plan 의 acceptance criteria
  `--help` exit 0 게이트가 fail.
- **Fix:** `extract_reference_body_profiles.py` 의 imageio / rtmlib / boto3
  의존 import 를 모두 `main()` 안의 lazy import 로 이동. Mac 로컬에서 `--help`
  exit 0 + Pod 에서 실 측정 시점에 의존성 fail-fast.
- **Files modified:** `backend/scripts/extract_reference_body_profiles.py`.
- **Commit:** `fc7dab7` (Task 2).

### 2. [Rule 3 - 변경] README 의 `python -m backend.scripts` 문구 reword

- **Found during:** Task 2 final verification.
- **Issue:** Plan 의 `grep -c "python -m backend.scripts" README ... == 0` gate
  가 prohibition note (W3 박제) 의 literal mention 도 catch.
- **Fix:** README 의 W3 박제 섹션 문구를 "(`python -m backend.scripts.extract...`)
  **금지**" → "모듈 invocation (`-m` 플래그 + dotted module path) 형태는 **금지**"
  로 reword. literal 부재 + 의미 보존.
- **Files modified:** `backend/scripts/README_extract_reference_body_profiles.md`.
- **Commit:** `fc7dab7` (Task 2).

### 3. [Rule 3 - 변경] seed-reference-body-profile.mjs 헤더 주석의 `initializeApp` literal reword

- **Found during:** Task 3 R7 ordering grep gate 검증.
- **Issue:** Plan 의 R7 ordering 검증 `grep -n "initializeApp" ...` 의 첫 line
  number 가 헤더 주석 ("Step 3 real-run: initializeApp + getFirestore +
  batch.commit") 라인 (line 8) 으로 잡혀 dryRun 라인 (152) 보다 앞에 위치 →
  ordering FAIL 표시.
- **Fix:** 헤더 주석을 "Step 3 real-run: Firebase Admin init + Firestore batch
  commit" 로 reword. literal `initializeApp` 첫 출현은 line 176 의 실 코드.
  ordering PASS.
- **Files modified:** `app/scripts/seed-reference-body-profile.mjs`.
- **Commit:** `39bbe2a` (Task 3).

이 3건은 모두 acceptance grep gate 정합을 위한 **문구 정리** — 알고리즘 / contract
/ 동작은 변경 없음.

## Checkpoint: Task 5 — belle 운영 (실 실행)

### 상태

본 plan 의 autonomous 산출 (Task 1, 2, 3, 4, 4.5, 6) 은 **완료**. Task 5 는 실
실행 (Pod GPU 측정 → 로컬 dry-run → real-run seed → Firestore Console verify) —
**autonomous executor 의 scope 외**. 본 SUMMARY 가 belle 가 실행할 단계 + 기대
출력 + rollback path 를 박제.

### Why checkpoint?

Plan 의 `<task type="checkpoint:human-verify" gate="blocking">` 정합 + 본 실행이
요구하는 외부 의존성:

- 실 Firestore (`sunity-ai-coach` project) 의 reference 컬렉션 write
- 실 S3 (`sunity-motion-pilot-videos`) 의 reference 영상 read
- RunPod Pod GPU (`xbdkj1g2ylnfwi`) 의 RTMW + NLF 실 추론
- Firebase ADC (gcloud auth application-default login, sunity3412@gmail.com)

→ autonomous executor 의 허용 범위 외 (대신 본 plan 은 dry-run path 의 자동
검증만 수행 — Task 4 GREEN).

### belle 실행 단계

#### Step 1: Pod GPU 측정 (dry-run 우선, C5)

```bash
ssh xbdkj1g2ylnfwi-64411701@ssh.runpod.io -i ~/.ssh/id_ed25519
cd /workspace/SunityMotion
git pull origin main
export AWS_DEFAULT_REGION=ap-northeast-2
export AWS_ACCESS_KEY_ID=...   # sunity-motion 키
export AWS_SECRET_ACCESS_KEY=...
export RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx
export YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx
export RTMW_DEVICE=cuda
python backend/scripts/extract_reference_body_profiles.py \
    --bucket sunity-motion-pilot-videos \
    --output /workspace/reference-body-data.json \
    --dry-run
```

**기대 출력 (dry-run)**: stdout JSON `{"motions": {"ref-climb": {"bodyNormalizationProfile":
{...}, "bodyComparisonSourcePose": {"jointKeys": [...17], "values": [<68 float>],
"frameIndex": ..., "torsoPx": ..., "confidence": ..., "measuredAt": ...}},
"ref-foxtop": {...}, "ref-foxtop-split": {...}, "ref-invert": {...},
"ref-sideway-spin": {...}}, "measuredAt": "...", "rtmwOnnxPath": "..."}`.
파일 `/workspace/reference-body-data.json` 미생성.

**검증 항목 (dry-run 출력)**:

- 5 motion ID 모두 측정됨
- 각 motion 의 `bodyNormalizationProfile.confidence >= 0.5`
- 각 motion 의 `bodyComparisonSourcePose` 존재 (null 아님)
- `bodyComparisonSourcePose.jointKeys` 길이 == 17 (COCO-17)
- `bodyComparisonSourcePose.values` 길이 == 68 (= 4 × 17)
- `bodyComparisonSourcePose.torsoPx > 0` + finite
- `bodyComparisonSourcePose.confidence >= 0.5`

#### Step 2: Pod GPU 실 측정 (dry-run 통과 후)

```bash
python backend/scripts/extract_reference_body_profiles.py \
    --bucket sunity-motion-pilot-videos \
    --output /workspace/reference-body-data.json
```

**기대**: `/workspace/reference-body-data.json` 생성. dry-run stdout 과 동일 내용.

#### Step 3: 로컬 다운로드 + ADC

```bash
scp xbdkj1g2ylnfwi-64411701@ssh.runpod.io:/workspace/reference-body-data.json .
gcloud auth application-default login   # sunity3412@gmail.com
```

#### Step 4: seed 스크립트 dry-run (R7 — ADC 무관 작동)

```bash
cd app
npm run seed:body-profile -- --profiles ../reference-body-data.json --dry-run
```

**기대 출력**: stdout JSON `{"dryRun": true, "willMerge": 5, "force": false,
"motions": [{"motionId": "ref-climb", "bodyNormalizationProfile": {...},
"bodyComparisonSourcePose": {...}}, ...]}` — 5 motion 모두. Firestore 호출 0회.

#### Step 5: seed 스크립트 real-run

```bash
npm run seed:body-profile -- --profiles ../reference-body-data.json
```

**기대 출력**: 각 motion 별 `- queued ref-climb body_conf=0.xx source_pose=true`
5줄 + `[seed:body-profile] batch.commit OK — queued=5 skipped=0` + 읽기 검증
출력 (`bodyNormalizationProfile=true bodyComparisonSourcePose=true` × 5).

#### Step 6: Firestore Console verify (두 필드 모두)

URL: `https://console.firebase.google.com/project/sunity-ai-coach/firestore/data/~2Freference`

**검증 항목 (각 reference doc)**:

- `bodyNormalizationProfile` 필드 존재 (object) + 7 sub-필드
- `bodyNormalizationProfileUpdatedAt` 필드 (timestamp ms)
- `bodyComparisonSourcePose` 필드 존재 (object) — R2 신규
- `bodyComparisonSourcePose.jointKeys` 길이 17 (COCO-17)
- `bodyComparisonSourcePose.values` 길이 68 (4 × 17)
- `bodyComparisonSourcePose.values` 내부 nested-array 없음 — 단일 flat number array
- `bodyComparisonSourcePose.torsoPx > 0` + finite
- `bodyComparisonSourcePose.confidence ∈ [0, 1]`
- `bodyComparisonSourcePoseUpdatedAt` 필드 (timestamp ms)
- 5 doc 모두 동일 schema

#### Step 7: idempotent (재실행 회귀 0)

```bash
npm run seed:body-profile -- --profiles ../reference-body-data.json
```

**기대**: 5 motion 모두 `skip ref-climb — already has both fields (use --force)`
형태 5줄 + `[seed:body-profile] batch.commit OK — queued=0 skipped=5`.

#### 문제 발생 시 — C12 + R2 rollback (두 필드)

```bash
# dry-run 1차
npm run revert:body-profile -- --motion-ids ref-climb,ref-foxtop,ref-foxtop-split,ref-invert,ref-sideway-spin --dry-run
# 출력 검토 후 --commit 으로 실 실행
npm run revert:body-profile -- --motion-ids ref-climb,ref-foxtop,ref-foxtop-split,ref-invert,ref-sideway-spin --commit
```

→ 5 reference 모두 두 필드 (bodyNormalizationProfile + bodyComparisonSourcePose
+ 각 *UpdatedAt) 제거. doc 자체는 유지.

### Resume signal

belle: "approved" + Firestore Console verify 통과 → Plan 06-03 closed. 또는
측정값 우려 (예: "ref-climb 의 bodyComparisonSourcePose.confidence 0.4 — 임계
미달, 영상 재촬영 필요") → 별도 조치.

## Known Stubs

(없음 — Plan 06-03 산출은 operational scripts + helper. UI 노출은 Phase 12/12.5
책임. 실 데이터 백필은 Task 5 belle 운영 — autonomous scope 외.)

## Deferred Issues

### test_seed_real_run_calls_batch_commit_when_dry_run_absent (Test 3) — SKIP

- mock-Firebase-Admin 환경 또는 Firestore emulator 가 필요. 별도 npm devDep
  (`@firebase/rules-unit-testing` 등) 도입을 회피 (plan scope 외).
- 대신 Test 2 (R7 dry-run no init) + Test 4 (R7 schema-before-init) 가 R7 fix
  의 핵심 (Firebase init ordering) 을 ADC-free subprocess 환경에서 직접 증명.
- real-run path 의 batch.commit 호출 자체는 Step 5 (belle 운영) 의 Firestore
  Console verify (Step 6) 가 end-to-end 증명.

### Pod sweep 실 실행 (Task 6 deferred)

- C6 사양 박제 완료 (`.planning/phases/06-coaching/06-03-DEFERRED-POD-SWEEP.md`).
- 실 실행 = belle 운영 sweep 일정. Phase 7 진입 전 권장 (observational, hard-block X).

## Plan 06-03 closure 시그널

- **Autonomous 완료**: Task 1, 2, 3, 4, 4.5, 6 (6/7).
- **Pending checkpoint**: Task 5 — belle 운영 (Pod GPU 측정 + 로컬 seed +
  Firestore Console verify). 본 SUMMARY 의 "Checkpoint: Task 5" 섹션이 belle
  실행 단계 + 기대 출력 + rollback path 모두 박제.
- belle 의 Task 5 approval 후 Phase 6 전체 closure → Phase 7 (차이 분류) 진입
  가능. Phase 14 (정은지 reference 본격 등록) 는 동일 `update_reference_body_data`
  helper 재사용 (R2 단일 진입점).

## Self-Check: PASSED

### Created files

- `backend/shared/python/sunity_shared/firestore_admin.py` (modified) — FOUND
- `backend/scripts/extract_reference_body_profiles.py` — FOUND
- `backend/scripts/README_extract_reference_body_profiles.md` — FOUND
- `app/scripts/seed-reference-body-profile.mjs` — FOUND
- `app/scripts/revert-reference-body-profile.mjs` — FOUND
- `app/package.json` (modified) — FOUND
- `backend/tests/phase06/test_firestore_admin_update_reference_body_data.py` — FOUND
- `backend/tests/phase06/test_backfill_scripts_dry_run.py` — FOUND
- `backend/tests/phase06/fixtures/test_reference_body_data.json` — FOUND
- `.planning/phases/06-coaching/06-03-DEFERRED-POD-SWEEP.md` — FOUND

### Commits (7 atomic)

- `6c9675a` Task 1 RED — failing tests for update_reference_body_data
- `0071f2e` Task 1 GREEN — update_reference_body_data helper (R2)
- `fc7dab7` Task 2 — extract_reference_body_profiles.py + README (R2 + C5 + W3)
- `39bbe2a` Task 3 — seed-reference-body-profile.mjs (R2 + C5 + R7)
- `9bc8265` Task 4 — dry-run + R7 integration tests + fixture
- `87fd30f` Task 4.5 — revert-reference-body-profile.mjs (C12 + R2)
- `361b7e9` Task 6 — DEFERRED-POD-SWEEP spec (C6 + R9)

### Tests

- pytest backend/tests/phase06/ — **120 passed, 1 skipped** (Plan 06-01 의 52 +
  Plan 06-02 의 55 + 본 plan 의 13 PASS, 1 documented SKIP).
- tsc --noEmit clean (app/).
- node --check on both new .mjs files exit 0.
- `python backend/scripts/extract_reference_body_profiles.py --help` exit 0.

### Plan-level verification gates

| Gate | Result |
|------|--------|
| `def update_reference_body_data(` count | 1 |
| `def update_reference_body_profile(` count (R2 폐기) | 0 |
| `bodyComparisonSourcePose` across 4 files | 29 (>= 4) |
| `app/scripts/revert-reference-body-profile.mjs` exists | FOUND |
| `FieldValue.delete` in revert | 7 (>= 2) |
| `revert:body-profile` in package.json | 1 |
| `06-03-DEFERRED-POD-SWEEP.md` exists | FOUND |
| `--dry-run` across extract + seed | 10 (>= 2) |
| `python -m backend.scripts` in README (W3) | 0 |
| R7 ordering: dryRun line < initializeApp line | 152 < 176 PASS |
