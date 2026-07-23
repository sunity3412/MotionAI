---
plan: 33-04
title: S2 candidate-aware 백필 증거 — 11 reference downstream @9fps → versions/phase33-cm3-run1
status: complete
pod: k508k3lut0o3f1 (dedicated eval Pod)
commit: 8682c83acda0f9ba89e3ce7211954cc0d5c0bc48
candidate: phase33-cm3-run1
updated: 2026-07-23
---

# 33-04 S2 candidate-aware 백필 증거 (SEED Task 2)

33-03 이 기록한 **candidate 버전**(`phase33-cm3-run1`, 9fps + PR 인버전)에서 파생 필드를
전부 재산출해 **같은 candidate 버전 문서**에 MERGE. 활성 포인터(`activeVersion=phase4_v1`)와
top-level 은 무접촉 — flip 은 33-07. 채점 산식/임계 무접촉 (D-20/D-29).

## Task 0 — warm-Pod canary 재확인 (blocking, D-30 / codex concern 6·15)

**Pod:** `k508k3lut0o3f1` (RTX 4090, dedicated eval — 프로덕션 Lambda 미재동기화, 트래픽 격리).
**Pod repo HEAD:** `8682k3lut...` → `git rev-parse HEAD` = `8682c83acda0f9ba89e3ce7211954cc0d5c0bc48` (핀 커밋).
**uvicorn:** PID 2549 가동 중 (재시작 안 함 — 33-04 는 backend/scripts/* 만 수정, 인메모리 모듈 무영향).

**/health canary body (X-RunPod-Token 인증, 재확인 실제 응답):**

```json
{
  "status": "ok",
  "auth_configured": true,
  "pipeline_loaded": true,
  "commitSha": "8682c83acda0f9ba89e3ce7211954cc0d5c0bc48",
  "envFlags": { "PR_INVERSION_ENABLED": true, "RTMW_DETERMINISTIC": true },
  "modelInitCanary": {
    "pipelineLoaded": true,
    "adaptersReady": true,
    "poseEngine": "RTMWPoseEngine",
    "recognizer": "GeminiTechniqueRecognizer",
    "modelLoaded": true
  }
}
```

- canary 확인 (bare 200 불충분, concern 6): `commitSha` == 핀 커밋 ✓, `envFlags` PR=1/deterministic=1 ✓,
  `modelInitCanary.modelLoaded=true` + poseEngine=RTMWPoseEngine ✓ → **warm + 핀 커밋 확인, cold/wrong-commit 아님**.
- reprocess env(`/workspace/_reprocess_env.sh`) 존재 확인: RTMW cuda + PR_INVERSION_ENABLED=1 + RTMW_DETERMINISTIC=1 + FIREBASE_SA_PATH + PYTHONPATH.

## 백필 착수 전 baseline (top-level 무변경 증명용, read-only probe)

`probe_state.py` (읽기 전용, Pod SSH, firestore_admin 경유):

| 항목 | baseline |
|------|----------|
| `reference/_release` | **ABSENT** (전역 활성화 포인터 미생성 — flip 은 33-07) |
| candidate `phase33-cm3-run1` 존재 | **11/11** |
| top-level `activeVersion` | **phase4_v1** (11/11) |
| top-level `keypointReport.fps` | 18.0 (11/11) |
| candidate `keypointReport.fps` | **9.0** (11/11 — 33-03 재추출본) |
| candidate 파생 필드 (meanAngles/techniqueProfile/bodyNormalizationProfile/forceDirectionPattern/referenceKeypointReport/bodyComparisonSourcePose/captureViews) | **전부 부재** (백필 대상) |
| candidate `keypointReport` | 존재 (33-03 재추출본, fps 9.0) |

**top-level content hash (backfill 후 무변경 증명 기준):**

```
ref-climb                3493d684a0ae
ref-combo                6e8a2835fb56
ref-elbow-twist-sister   dc942b49a91b
ref-foxtop               3651527007f7
ref-foxtop-split         70c21c1b2f50
ref-invert               ecd93da39b8e
ref-kip-up               0a33d3327420
ref-pdshape              60a32eaa1fda
ref-peter-pan            518c115b4d4f
ref-power-spin           d0bd66afcfab
ref-sideway-spin         45d198f120ec
```

(hash 대상 = {angles, joints3d, activeVersion, pipelineVersion, keypointReport,
referenceKeypointReport, meanAngles} — 백필이 top-level 을 건드리면 이 hash 가 바뀐다.)

## Task 1 — candidate-aware 백필 재작성 (코드)

`backfill_reference_downstream.py` 재작성 요지:
- **source = candidate**: `reference/{id}/versions/phase33-cm3-run1` 직접 read (`_read_candidate_doc`) —
  top-level `get_reference_motion` 미사용. angles/keypointReport 는 33-03 재추출본 재사용.
- **fps = candidate/CLI**: `_resolve_target_fps` 가 candidate `keypointReport.fps`(9.0) 또는 `--target-fps`
  에서 읽는다. `REFERENCE_TARGET_FPS=18.0` 하드코딩 폴백 **제거** (둘 다 없으면 에러).
- **merge back into candidate**: `_merge_into_candidate` 가 파생 필드를 같은 `versions/{candidate}` 문서에
  set(merge=True). top-level/activeVersion/joints3d/angles **미접촉**.
- **bodyComparisonSourcePose 실존 producer**: `extract_reference_body_profiles._build_source_pose`
  (대표 frame = 평균 keypoint confidence 최대 → to_coco17_array 단일 frame 슬라이스, 17×4=68 flat, torso_px).
  None 산출 시 해당 motion FAIL (11/11 필수 — T-33-30).
- **keypointReport + referenceKeypointReport**: `build_keypoint_report(live pose, fps=9.0)` — 라벨 9.0.
- **epsilons/FORCE_CONFIG 무접촉**: `MEAN_EPSILON_DEG=0.1`, `P99_EPSILON_DEG=1.0`, `REFERENCE_V1_FORCE_CONFIG` verbatim.
  gate 걸리면 임계 재fit 금지 — 원인 조사 (D-29).
- `compute_reference_downstream` 시그니처/동작 무변경 (test_reference_backfill.py 9/9 PASS).

`extract_reference_keypoint_reports.py`: 기본 fps 18.0 → **9.0**, MOTION_IDS 5 → 11 (standalone 재산출 경로 정합).

**로컬 게이트:** ast.parse OK, test_reference_backfill.py 9 passed, 채점 파일 diff 0 (D-20).

## Task 2 — candidate 백필 실행 (warm Pod) — 11/11 완주 (옵션 B 채택)

### ★ 실행 이력 — Firestore 40k index-entry 한도 → 옵션 B(인덱스 면제) 해소

1차 `--write-candidate` 실행에서 candidate MERGE 가 `ref-combo` 부터 실패:

```
grpc._channel._InactiveRpcError: status = INVALID_ARGUMENT
  details = "too many index entries for entity /reference/ref-combo/versions/phase33-cm3-run1"
```

- 원인 = [[firestore-index-entry-limit]] (문서당 40,000 index-entry 한도). 신규 대형 배열 필드
  `referenceKeypointReport`(data/confidence flat, combo 621f × 12관절 ≈ 2.2만 entry)가
  **`versions` collection-group 에서 인덱스 면제되어 있지 않아** 대형 candidate 문서(combo 621f)를 초과시킴.
  33-03 이 `angles`/`joints3d`/`keypointReport` 를 combo candidate 에 정상 write 한 사실 → 이 3개는
  versions 에서 이미 면제됨. 면제 목록에 없던 `referenceKeypointReport` 만이 초과 유발 (combo 단일).
- **belle 결정 = 옵션 B.** 오케스트레이터가 Firestore single-field 인덱스 면제 2건 추가 (둘 다 exit 0, `--disable-indexes`):
  · `collectionGroup=versions, field=referenceKeypointReport`
  · `collectionGroup=reference, field=referenceKeypointReport` (33-07 flip 의 top-level 미러 시 combo 재초과 예방)
  → 원래 acceptance("referenceKeypointReport in candidate 11/11")를 **그대로 충족**한다.
- 면제 추가 후 동일 백필 재실행 → **11/11 MERGE 성공, PY_EXIT=0, failures=[]** (combo 포함).

### 무결성 게이트 + per-candidate 덤프 (11/11 PASS, 임계 재fit 0 — D-29)

candidate angles vs live rerun angles(9fps, PR-on) integrity gate **11/11 전부 통과** — meanΔ/p99Δ 가
임계(0.1 / 1.0) 대비 20~200배 여유. bodyNormalizationProfile non-NaN, bodyComparisonSourcePose values=68
(=4×17 COCO-17), keypointReport.fps=9.0, referenceKeypointReport 11/11 존재.

| motion | meanΔ | p99Δ | maxΔ | bodyNorm conf(non-NaN) | keypointReport.fps | referenceKeypointReport | srcPose vals/conf | force findings |
|--------|-------|------|------|------------------------|--------------------|-------------------------|-------------------|----------------|
| ref-climb | 0.0025 | 0.0049 | 0.0050 | 0.593 | 9.0 | ✓ | 68 / 0.859 | 1 |
| ref-foxtop | 0.0025 | 0.0049 | 0.0050 | 0.504 | 9.0 | ✓ | 68 / 0.832 | 3 |
| ref-foxtop-split | 0.0025 | 0.0050 | 0.0050 | 0.526 | 9.0 | ✓ | 68 / 0.837 | 2 |
| ref-invert | 0.0025 | 0.0049 | 0.0050 | 0.529 | 9.0 | ✓ | 68 / 0.837 | 3 |
| ref-sideway-spin | 0.0025 | 0.0050 | 0.0050 | 0.639 | 9.0 | ✓ | 68 / 0.854 | 0 |
| ref-combo | 0.0025 | 0.0049 | 0.0050 | 0.497 | 9.0 | ✓ | 68 / 0.868 | 3 |
| ref-elbow-twist-sister | 0.0025 | 0.0050 | 0.0050 | 0.385 | 9.0 | ✓ | 68 / 0.827 | 3 |
| ref-kip-up | 0.0024 | 0.0050 | 0.0050 | 0.667 | 9.0 | ✓ | 68 / 0.842 | 0 |
| ref-pdshape | 0.0024 | 0.0049 | 0.0050 | 0.450 | 9.0 | ✓ | 68 / 0.802 | 3 |
| ref-peter-pan | 0.0026 | 0.0049 | 0.0050 | 0.574 | 9.0 | ✓ | 68 / 0.872 | 2 |
| ref-power-spin | 0.0025 | 0.0049 | 0.0050 | 0.487 | 9.0 | ✓ | 68 / 0.843 | 3 |

- meanAngles: 11/11 finite (JOINT_KEYS 8매핑), techniqueProfile: FallbackRecognizer EXTEND (name='미상' — fallback 정상, Gemini 아님).
- **R-4 재현성 재확인**: ref-combo(과거 23.43°→0.193° 요동 이력) meanΔ=0.0025 / maxΔ=0.005 — 결정론 유지.
- 산출 artifact: Pod `/workspace/reference-downstream-backfill.json` (perCandidateDump 11/11 + diagnostics).

### versions/{candidate} 에만 기록 + top-level 무접촉 (probe 전후 대조)

| 항목 | baseline | 백필 후 |
|------|----------|---------|
| candidate 파생 필드 (meanAngles/techniqueProfile/bodyNormalizationProfile/forceDirectionPattern/keypointReport/referenceKeypointReport/bodyComparisonSourcePose/captureViews) | 부재(keypointReport 제외) | **11/11 전부 존재** |
| candidate keypointReport.fps | 9.0 | 9.0 (불변) |
| top-level content hash (angles/joints3d/activeVersion/pipelineVersion/keypointReport/referenceKeypointReport/meanAngles) | 위 baseline 표 | **11/11 동일 (무변경)** |
| top-level activeVersion | phase4_v1 (11/11) | **phase4_v1 (11/11 불변)** |
| `reference/_release` | ABSENT | **ABSENT (재확인)** |

top-level content hash 가 11/11 전부 baseline 과 동일 → 백필이 top-level 을 **한 번도 write 하지 않음**을 증명.
파생 필드는 `versions/phase33-cm3-run1` 에만 MERGE 됨 (activeVersion/flip 무접촉 — flip 은 33-07).

## 종합

| 항목 | 결과 |
|------|------|
| Task 0 warm-Pod canary (commit+flags+model) | PASS |
| Task 1 candidate-source+merge / fps candidate / real bodyComparisonSourcePose producer / epsilon·FORCE_CONFIG 무접촉 | PASS |
| Task 2 integrity gate 11/11 (임계 0.1/1.0 무변경, refit 0) | PASS |
| Task 2 파생 필드 11/11 versions/{candidate} MERGE (referenceKeypointReport 포함, 옵션 B) | PASS |
| keypointReport.fps=9.0 (11/11) | PASS |
| bodyNormalizationProfile non-NaN (11/11) | PASS |
| bodyComparisonSourcePose 존재 (values=68, 11/11) | PASS |
| top-level/activeVersion 무접촉 (hash 11/11 동일) | PASS |
| reference/_release ABSENT | PASS |
| 채점 파일 diff / epsilon refit (D-20/D-29) | 0 |

