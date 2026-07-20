---
phase: 31-api-visual-correction
plan: 07
subsystem: training-data-privacy
tags: [d-01, privacy, hmac, idempotency, s3, deletion, flywheel]
requires: [31-01, 31-02]
provides:
  - "sunity_shared.analysis.pair_store — 동의 게이트·가명·commit-marker 적재 + payload 검증 consumer"
  - "backend/scripts/delete_training_pair.py — 전 키 버전 x historical registry x versionId 완전 삭제"
affects:
  - "31-09 postprocess (caller-fixed pairId/keyVersion 을 고정해 store_training_pair 호출)"
  - "31-12 lifecycle (RETENTION_DAYS=180 Expiration/NoncurrentVersionExpiration 적용)"
  - "phase 22 datagen (list_committed_pairs/load_committed_pair 만으로 학습 소비)"
tech-stack:
  added: []
  patterns:
    - "commit marker — before/after 먼저, meta.json 이 마지막 확정 표식"
    - "meta-read 선행 멱등 — 쓰기 전에 marker 를 읽어 재시도/충돌을 구분"
    - "조건부 PUT(IfNoneMatch='*') + 412 시 payload size/sha256 검증 후에만 resume"
    - "strict validator 단일 출처 — store/delete 가 같은 validate_hmac_key_set 사용"
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/pair_store.py
    - backend/scripts/delete_training_pair.py
  modified:
    - backend/tests/phase31/test_pair_store.py
decisions:
  - "HMAC key 인코딩/버전 ID 형식을 실제 배포 파라미터(k1 + base64)에 맞춰 확장 — 플랜 초안(v1 + hex)대로면 fail-closed 로 적재 자체가 불가능했다"
  - "get_bucket_versioning 분기 제거 — list_object_versions 를 무조건 사용하면 never-versioned 버킷에서도 완전 삭제가 성립한다"
  - "blur 분기 미구현 — belle option-a 확정이므로 'pod_blur' 는 상수 문서화만, 실행 코드 0"
metrics:
  tasks: 2
  commits: 2
  tests: 65
  duration: ~50m
  completed: 2026-07-20
---

# Phase 31 Plan 07: 학습 페어 적재·삭제 Summary

D-01 플라이휠 부산물(교정 페어)을 동의 게이트·HMAC 가명·commit-marker 멱등 적재로 제조하고,
키 회전·버킷 versioning 에 안전한 완전 삭제 경로까지 단위 테스트로 고정했다.

## 무엇을 만들었나

**`pair_store.py`** — 적재/소비 helper. 통제 축 5개가 전부 테스트로 잠겨 있다:

| 축 | 구현 | 리뷰 추적 |
|----|------|-----------|
| 동의 | `learning_opt_in is True` strict, 비통과 시 **S3 호출 0** | D-01 |
| 가명 | pairId = HMAC-SHA256(key, `uid:analysisId:joint`)[:24], key/meta 에 원문 0 | H-04 / H2-06 |
| 멱등 | caller-fixed pairId + **meta 선행 read** → 일치 PUT 0 'committed' / 불일치 'conflict' | 5차 B5-03 |
| 재개 | meta 부재 + 412 → HEAD size + GET sha256 일치 시만 resume, 아니면 marker 미기록 'conflict' | 6차 H6-04 |
| 소비 | `list_committed_pairs` 가 marker + payload hash 검증분만 반환, 나머지는 quarantine | H4-11 / H5-08 / M5-05 |

반환은 4상태(`skipped_consent` / `committed` / `conflict` / `failed`)로 닫혀 있고, 적재 실패가
예외로 새어나가 분석 전체를 깨뜨리지 않는다.

**`delete_training_pair.py`** — 삭제/철회 이행 스크립트. `pair_id` / `validate_hmac_key_set` /
`HISTORICAL_PAIR_JOINTS` 를 pair_store 에서 import 해 재구현이 없다. 활성+retired 전 키 버전 ×
append-only joint registry 로 pairId 를 재계산하고, `list_object_versions` 를
NextKeyMarker+NextVersionIdMarker **쌍**으로 끝까지 열거해 Versions+DeleteMarkers 를 versionId
삭제한 뒤 재조회 0 을 확인한다. inventory gate 가 재계산 불가능한 keyVersion 을 발견하면
부분 삭제 대신 중단한다.

## belle 결정 반영

- **option-a (blur 없음)** — B 분기를 구현하지 않고 **제거**했다. `BLUR_OPTION = "none"` 은 배포
  상수로만 존재하고 blur 실행 코드는 0. meta 의 `blurApplied` 는 항상 False, `anonymizerVersion` 은 None.
- **retentionDays = 180** — `RETENTION_DAYS` 는 **우리(Sunity) S3 페어의 삭제 SLA** 로만 기술했다.
  벤더 보존 일수는 미공개이며 코드·주석·문서 어디에도 벤더 숫자를 쓰지 않았다. 테스트
  `test_retention_is_our_deletion_sla_not_vendor_retention` 이 결정 JSON 의 `vendorRetention.retentionDays is None`
  과 `retentionDaysScope == "sunity_training_pairs_only"` 를 함께 단언해 이 구분을 고정한다.
- **배포 상수 대조** — `CONSENT_VERSION`/`BLUR_OPTION`/`RETENTION_DAYS` 를 build 테스트가
  `privacy_decision.json` 과 대조한다. 소스에 `.planning` 문자열이 없음을 테스트가 확인하므로
  런타임 결정파일 읽기는 구조적으로 0 (M2-05 / M3-02).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] HMAC key set 스키마가 실제 배포 파라미터와 불일치**

- **Found during:** Task 1
- **Issue:** 플랜은 키 버전 `^v[0-9]+$` + `bytes.fromhex` 를 명시했으나, 31-01 이 실제로 만든
  `/sunity/motion/pair-id-hmac-keys` 는 버전 ID 가 `k1` 이고 키가 **base64** 다. 플랜대로 구현하면
  validator 가 fail-closed 되어 **페어 적재 자체가 영구 불가능**해진다(동의한 사용자의 데이터가
  한 건도 안 쌓이는데 실패가 조용하다).
- **Fix:** 버전 ID 정규식을 `^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$`(경로·구분자 문자 배제)로 넓히고,
  키 디코딩은 hex(64자) 선판정 후 strict base64 순으로 처리했다. 64자 hex 는 base64 로 해석하면
  48바이트라 32바이트 게이트에서 탈락하므로 두 경로에 모호성이 없고, **어느 쪽이든 정확히
  32바이트만** 통과한다. 플랜이 의도한 strictness(단일 validator, fail-closed)는 유지된다.
- **Files modified:** `pair_store.py` (`_decode_key_material`, `_KEY_VERSION_RE`)
- **Commit:** c9ba728

**2. [Rule 3] `get_bucket_versioning` 분기 제거**

- **Found during:** Task 2
- **Issue:** 플랜 Task 2 는 `get-bucket-versioning` 으로 분기해 versioned/일반 삭제를 나누라고
  했으나, 오케스트레이터 제약은 이 버킷에 **S3 versioning API 호출 0** 이다(never-versioned 상태가
  31-12 hard gate). 두 요구가 정면 충돌한다.
- **Fix:** 분기를 없애고 `list_object_versions` 를 **무조건** 사용한다. never-versioned 버킷도
  versionId `"null"` 을 돌려주므로 동일 코드로 완전 삭제가 성립한다 — 분기가 하나 줄고
  삭제 완전성(T-31-26)도 유지된다. 버킷 versioning **설정** API(`put_bucket_versioning` /
  `get_bucket_versioning`)는 읽기·쓰기 모두 호출하지 않으며, 두 모듈 소스에 대해 테스트가
  부재를 단언한다.
- **판단 근거:** 제약의 보호 대상은 "never-versioned 상태가 바뀌지 않는 것"이고 이를 깨뜨릴 수
  있는 것은 PUT 뿐이다. `list_object_versions` 는 읽기 전용 object 열거라 상태를 바꾸지 못한다.
  **오케스트레이터 성공 기준에 "versioning API 호출 0" 이 문자 그대로 적혀 있으므로 이 판단은
  검수 대상으로 명시 보고한다.**
- **Files modified:** `delete_training_pair.py`
- **Commit:** da81eff

**3. [Rule 2] `read_pair_meta_raw` 추가**

- **Found during:** Task 2
- **Issue:** inventory gate 는 저장소의 **모든** meta 를 봐야 하는데, 소비용
  `list_committed_pairs` 는 검증 실패분을 quarantine 으로 걸러낸다. 소비 helper 를 그대로 쓰면
  quarantine 된 페어(실제 이미지를 들고 있다)가 gate 와 삭제 대상에서 조용히 빠진다.
- **Fix:** pair_store 에 공개 `read_pair_meta_raw` 를 추가해 검증 이전 meta 를 읽게 했다
  (private 함수를 모듈 밖에서 호출하지 않기 위함). `test_inventory_gate_counts_quarantined_pairs`
  가 quarantine 된 페어의 keyVersion 이 gate 에 잡히는지 확인한다.
- **Files modified:** `pair_store.py`, `delete_training_pair.py`
- **Commit:** da81eff

### 플랜 문구와 다르게 간 것 (의도적)

- meta 필드명은 플랜 원문을 그대로 따랐다(`model_id`/`judge_confidence`/`pose_error_deg` 는 snake,
  리뷰가 지정한 `hmacKeyVersion`/`beforeSha256` 등은 camel). 혼용이지만 31-09/31-10 이 이 문구로
  리뷰됐으므로 임의 통일보다 계약 충실을 택했다.
- 테스트의 "재PUT 0" 단언은 **실제 기록된 object** 기준이다. 조건부 PUT 시도 자체는 존재를
  원자적으로 판정하는 수단이라 시도 횟수로 세면 계약을 잘못 표현한다.

## Known Stubs

없음. 두 산출물 모두 실행 가능하며 stub/placeholder 반환 경로가 없다.

## Threat Flags

없음 — 이 플랜은 신규 네트워크 엔드포인트나 인증 경로를 만들지 않는다. S3 쓰기는 동의
게이트 뒤에만 있고, 삭제 스크립트는 로컬 CLI(AWS_PROFILE)로만 실행된다.

## 범위 밖 발견 (수정하지 않음)

`python3 -m pytest backend/tests` 를 repo root 에서 돌리면 **기존** 실패 41건 + 수집 오류 2건이
있다(전부 Gemini/pipeline/phase06/phase08 계열, 예: `test_pipeline_geminid_wiring.py`,
`test_gemini_vision_scorer.py`, 수집 오류 `test_pole_detector.py` / `test_rtmw_133_to_coco17_adapter.py`).
`pair_store` 를 import 하는 파일은 이 플랜의 3개뿐이라 본 플랜과 인과가 없다. 범위 경계 규칙에
따라 손대지 않았다.

## Verification

- `python3 -m pytest backend/tests/phase31/test_pair_store.py -q` → **65 passed**
- `python3 -c "import ast; ast.parse(...)"` → AST OK
- `python3 backend/scripts/delete_training_pair.py --help` → CLI 정상 (joint choices = historical registry 6)
- STATE.md / ROADMAP.md 미수정, 병렬 에이전트 소유 파일 미접촉

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/pair_store.py
- FOUND: backend/scripts/delete_training_pair.py
- FOUND: backend/tests/phase31/test_pair_store.py
- FOUND: c9ba728 (Task 1)
- FOUND: da81eff (Task 2)
