---
plan: 33-04
title: S2 candidate-aware 백필 증거 — 11 reference downstream @9fps → versions/phase33-cm3-run1
status: in_progress
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

## Task 2 — candidate 백필 실행 (warm Pod) — integrity gate 전수 PASS + 인덱스 한도 발견

### 무결성 게이트 (11/11 PASS, 임계 재fit 0 — D-29)

warm Pod 에서 `--reference-version phase33-cm3-run1 --write-candidate` 실행. candidate angles vs
live rerun angles(9fps, PR-on) integrity gate 는 **11/11 전부 통과** — meanAngleDelta 0.0025 /
p99AngleDelta 0.005 (임계 0.1 / 1.0 대비 20~200배 여유). frame 수 candidate 정합, keypointReport.fps=9.0,
bodyNormalizationProfile non-NaN (body_conf 0.49~0.64), bodyComparisonSourcePose 산출 성공.

| motion | frames(9fps) | meanΔ | p99Δ | maxΔ | body_conf | srcPose repFrame/conf | keypointReport.fps |
|--------|------|-------|------|------|-----------|----------------------|--------------------|
| ref-climb | 172 | 0.0025 | 0.005 | 0.005 | 0.593 | — / — | 9.0 |
| ref-foxtop | 284 | 0.0025 | 0.005 | 0.005 | 0.504 | — | 9.0 |
| ref-foxtop-split | 324 | 0.0025 | 0.005 | 0.005 | 0.526 | — | 9.0 |
| ref-invert | 174 | 0.0025 | 0.005 | 0.005 | 0.529 | — | 9.0 |
| ref-sideway-spin | 199 | 0.0025 | 0.005 | 0.005 | 0.639 | — | 9.0 |
| ref-combo | 621 | 0.0025 | 0.005 | 0.005 | 0.497 | — | 9.0 |
| ref-power-spin | 106 | 0.0025 | 0.005 | 0.005 | 0.487 | 15 / 0.843 | 9.0 |
| (나머지 4종 elbow-twist-sister/kip-up/pdshape/peter-pan) | 정상 처리 | 0.0025 | 0.005 | 0.005 | non-NaN | 산출 | 9.0 |

- **R-4 재현성 재확인**: ref-combo(과거 23.43°→0.193° 요동 이력) meanΔ=0.0025 / maxΔ=0.005 — 결정론 유지.
- 산출 artifact: Pod `/workspace/reference-downstream-backfill.json` (28.9 KB, perCandidateDump 11/11 + diagnostics).

### ★ 발견 — Firestore 40k index-entry 한도 (candidate MERGE 부분 실패)

candidate 버전 문서에 MERGE 하는 단계에서 `ref-combo` 부터 실패:

```
grpc._channel._InactiveRpcError: status = INVALID_ARGUMENT
  details = "too many index entries for entity /reference/ref-combo/versions/phase33-cm3-run1"
```

- 원인 = [[firestore-index-entry-limit]] (문서당 40,000 index-entry 한도). 신규 대형 배열 필드
  `referenceKeypointReport`(data/confidence flat, combo 621f × 12관절 ≈ 2.2만 entry)가
  **`versions` collection-group 에서 인덱스 면제되어 있지 않아** 대형 candidate 문서를 한도 초과시킴.
- 33-03 이 `angles`/`joints3d`/`keypointReport` 를 combo candidate 에 정상 write 한 사실 →
  이 3개는 versions 에서 이미 인덱스 면제됨. **면제 목록에 없는 `referenceKeypointReport` 만이 초과 유발.**
  (top-level `reference` 컬렉션엔 referenceKeypointReport 면제 존재 — 현행 top-level 18fps refKR 이 그 증거.)
- **부분 MERGE 상태** (active pointer 무접촉, `_release` ABSENT — 프로덕션 무영향):
  MERGE 성공 5종 = climb·foxtop·foxtop-split·invert·sideway-spin (전 파생 필드 + referenceKeypointReport).
  MERGE 미실행 6종 = combo·elbow-twist-sister·kip-up·pdshape·peter-pan·power-spin.
- **선택 필요 (아래 33-04 SUMMARY / 오케스트레이터 결정)**:
  · (A) candidate 엔 `keypointReport`@9fps(이미 면제·존재) + 소형 파생 필드 + bodyComparisonSourcePose 만
    MERGE 하고, 대형 `referenceKeypointReport`@9fps 는 인덱스 면제가 이미 존재하는 **top-level flip(33-07)**
    에서 투영. → owner 인프라 불필요, candidate lean. (부분 write 된 5종의 referenceKeypointReport 는 삭제해 균일화.)
  · (B) belle(owner)이 `versions` collection-group 에 `referenceKeypointReport` 단일필드 인덱스 면제를
    추가 → 33-04 재실행해 11/11 candidate 에 referenceKeypointReport 포함 write.

