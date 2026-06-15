# 14-BACKFILL-RUN — 정은지 11개 reference downstream 백필 실행 로그

**실행:** 2026-06-15 · Pod `qcf38vvsmub1y4` (RTX PRO 4500, RTMW rtmw-x-384x288 commercial_ok)
**결과:** SUCCESS — 11/11 seeded, active pose 바이트 단위 불변 증명. (belle 육안 확인 = Task 2 대기)

## 게이트 요약 (14-BACKFILL-RUN-SUMMARY.json)

| gate | 값 | 판정 |
|------|----|----|
| unchangedActivePoseCount | 11 | PASS (D-02/R4) |
| changedActivePoseCount | 0 | PASS |
| completeDownstreamFieldCount | 11 | PASS (SC#2) |
| seededMotionCount | 11 | PASS (R5 all-or-nothing) |

## 실행 순서 + 게이트 결과

1. **commit + push** (HEAD `0f03781`, [[gsd-pod-work-push-first]]) → Pod `git pull` 동기화.
2. **Pod /health 게이트:** `GET https://qcf38vvsmub1y4-8000.proxy.runpod.net/health` →
   `{"status":"ok","auth_configured":true,"pipeline_loaded":true}` (200). PASS — GPU 파이프라인 정상.
3. **Pod --check-firestore 게이트 (R2-3/R3-2):** 11개 전부 `activeVersion+angles+anglesJointKeys+anglesFrames`
   present + frame-count sanity. PASS (S3/RTMW 미실행). 프레임: climb 257 / foxtop 426 / foxtop-split 485 /
   invert 260 / sideway-spin 298 / combo 931 / elbow-twist-sister 329 / kip-up 118 / pdshape 237 /
   peter-pan 130 / power-spin 159.
   - 자격증명: `bash -ic` 로 Pod 세션 env(FIREBASE_SA / AWS) 로드 (비대화형 SSH 는 env 미상속 — RunPod 함정).
4. **PRE-SEED 스냅샷:** `snapshot-reference-phase14-state.mjs --mode pre` → 14-PRESEED-SNAPSHOT.json
   (gitignored, restore 용 value 포함). 11개 모두 activeVersion=phase4_v1, 사전 phase14Required=1/5.
5. **백필 (RTMW 재추론 11개):** `backfill_reference_downstream.py --motions <all 11> --bucket
   sunity-motion-pilot-videos --output ...` → `real-run 완료 — 11/11 motion` (43.4 KB fixture).
   stored phase4_v1.angles 에서 meanAngles/EXTEND, RTMW 재추론 pose_frames 에서 body/force
   (REFERENCE_V1_FORCE_CONFIG, motion_id=None, R4-2). angle-integrity 게이트 11/11 PASS.
6. **scp** fixture → local `reference-downstream-backfill.json` (seedPayload 11 ids × 5필드 + diagnostics).
7. **seeder dry-run → real-run:** `seed-reference-downstream.mjs` ADD-only merge.
   `skippedComplete=0 repairMissing=11 forceOverwrite=0`, batch.commit OK. activeVersion flip 없음.
8. **verify-read:** `--verify` + `audit-reference-fields.mjs` → completeRequiredSet **11/11**
   (meanAngles + techniqueProfile + bodyNormalizationProfile + forceDirectionPattern + captureViews 모두 present).
9. **POST-SEED 스냅샷 + byte-level hash 비교:** `--mode post` → unchangedActivePoseCount=11 /
   changedActivePoseCount=0. active phase4_v1 joints3d/angles/activeVersion 1바이트도 안 변함 (D-02 증명).

## 실행 중 발견·수정 (deviations)

1. **fps 불일치 (fix `0129f3e`):** 백필이 9fps(FfmpegFrameExtractor 기본)로 추출 → phase4_v1 은
   reprocess `--target-fps 18.0` 로 생성됨 → frame 수 불일치(ref-climb stored 257 vs rerun 172,
   257/172≈1.5=18/9). 백필을 18fps(REFERENCE_TARGET_FPS)로 정합. (학생 _process 9fps vs reference 18fps
   차이는 기존 조건 — Mode 1 비교 정합은 **Phase 15** 의 몫.)
2. **robust integrity gate (fix `0f03781`):** 18fps 후 9/11 은 평균 delta ~0.005° 로 일치, 그러나 RTMW 가
   길고 복잡한 동작의 단일 프레임에서 비결정적(ref-combo 한 실행 23.43° → 다음 0.193°). MAX 단일-프레임
   게이트가 transient spike 에 랜덤 실패. 게이트를 **mean>0.1° OR p99>1.0°** (systematic shift 만 차단,
   transient spike 허용)로 교체. 최종 실행 11/11 max<0.5° / mean~0.0025° / p99 0.005° / over1deg=0.
   향후 신규 전문가·동작에도 일관 (belle 2026-06-15 결정).

## 11-motion verify-read 표 (post-seed)

| motion | meanAngles | techniqueProfile | bodyNormProfile | forceDirPattern | captureViews | activeUnchanged |
|--------|:--:|:--:|:--:|:--:|:--:|:--:|
| ref-climb | Y | Y | Y | Y | Y | Y |
| ref-foxtop | Y | Y | Y | Y | Y | Y |
| ref-foxtop-split | Y | Y | Y | Y | Y | Y |
| ref-invert | Y | Y | Y | Y | Y | Y |
| ref-sideway-spin | Y | Y | Y | Y | Y | Y |
| ref-combo | Y | Y | Y | Y | Y | Y |
| ref-elbow-twist-sister | Y | Y | Y | Y | Y | Y |
| ref-kip-up | Y | Y | Y | Y | Y | Y |
| ref-pdshape | Y | Y | Y | Y | Y | Y |
| ref-peter-pan | Y | Y | Y | Y | Y | Y |
| ref-power-spin | Y | Y | Y | Y | Y | Y |

## angle-integrity (stored vs rerun, 최종 실행 — robust gate)

| motion | maxDelta° | meanDelta° | p99° | over1deg |
|--------|--:|--:|--:|--:|
| ref-climb | 0.005 | 0.0025 | 0.005 | 0/2056 |
| ref-foxtop | 0.463 | 0.0038 | 0.005 | 0/3408 |
| ref-foxtop-split | 0.049 | 0.0026 | 0.005 | 0/3880 |
| ref-invert | 0.005 | 0.0026 | 0.005 | 0/2080 |
| ref-sideway-spin | 0.005 | 0.0026 | 0.005 | 0/2384 |
| ref-combo | 0.045 | 0.0025 | 0.005 | 0/7448 |
| ref-elbow-twist-sister | 0.005 | 0.0025 | 0.005 | 0/2632 |
| ref-kip-up | 0.005 | 0.0025 | 0.005 | 0/944 |
| ref-pdshape | 0.005 | 0.0024 | 0.005 | 0/1896 |
| ref-peter-pan | 0.005 | 0.0025 | 0.005 | 0/1040 |
| ref-power-spin | 0.068 | 0.0027 | 0.005 | 0/1272 |

## 리스크 대응표 (stop / recover / propose)

> 실 백필+seed 표준 운영 정책. RESTORE-aware rollback (`rollback-reference-downstream.mjs`, active pose 절대 미접촉).

| 상황 | Stop / Recover / Propose |
|------|--------------------------|
| Pod `/health` 실패 | 즉시 STOP, health 실패만 기록, 백필/seed 금지, CPU fallback 금지(NaN). belle Pod 재시작(Network Storage) 후 health 게이트부터 재실행. |
| `--check-firestore` 실패 | S3/RTMW 전 STOP, 자격증명/불완전 doc 기록. Pod Firebase SA 마운트 또는 reference doc 복구 후 재실행. |
| S3 영상 누락 | seedable fixture 미생성. 누락 key/bucket/motion 기록, all-or-nothing 으로 나머지 10개도 미seed. S3 객체 복구 후 11개 재실행. |
| stored-vs-rerun angle gate 실패 (mean>0.1° OR p99>1.0°) | 전체 seed STOP (R1). systematic pose-version 변질. derived-field 백필 X — pose-version 재검증 phase 로 승급. (단일 프레임 spike 는 robust gate 가 허용.) |
| ForcePattern findings 조작 의심 | real-run 전: fixture 폐기 + diagnostics forceSignalsReportSummary 확인. real-run 후: `rollback-reference-downstream.mjs --confirm` 로 Phase-14 필드만 restore-aware 복원, active pose 미접촉. 빈 findings + umbrella warning 은 정상. |
| seeder dry-run 이 일부 필드 존재 보고 | blanket-skip 금지. complete/repair/overwrite 분기(R3): repair-missing 기본, --force 만 기존 valid 덮어씀. rollback 이 restore-aware 라 --force 도 가역. |
| 잘못된 필드 seed | pre-seed 스냅샷({present,valueHash,value?})으로 영향 범위 산정. `rollback-reference-downstream.mjs --confirm` 로 Phase-14 필드만 복원(없던 필드 delete, 있던 필드 restore). joints3d/angles/activeVersion 변경 시 → STOP, 별도 incident. |
| ADC/auth 로컬 실패 | dry-run 출력만 보존, real-run 금지. 콘솔 수동 편집 금지. `gcloud auth application-default login` (sunity3412@gmail.com) 후 같은 fixture 로 재시도. |
| belle spot-check 거부 | active pose 미접촉. 거부 motion 만 `rollback-reference-downstream.mjs --confirm`. 거부 motion id + 사유 기록 후 진단 재실행. |
