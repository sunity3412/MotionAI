---
plan: 33-03
title: S1 재추출 증거 — 11 reference @9fps + PR 인버전 → candidate versions (run1+run2)
status: complete
pod: k508k3lut0o3f1 (dedicated eval Pod)
commit: 8682c83acda0f9ba89e3ce7211954cc0d5c0bc48
updated: 2026-07-23
---

# 33-03 S1 재추출 증거 (SEED Task 1)

11 reference 모션을 **9.0 fps + PR 인버전 보정**으로 재추출하여 **불변 candidate 버전**
(`phase33-cm3-run1`, 재현성 대조용 `phase33-cm3-run2`)에 기록했다. 활성 포인터
(`activeVersion=phase4_v1`)는 **손대지 않았다** (flip 은 33-07). 채점 산식/임계 무접촉 (D-20/D-29).

## Task 1 — belle GPU greenlight (D-30 / D-32ⓐ ops 예외)

- belle 가 **"go — 전용 eval Pod"** 선택 후 직접 Pod `k508k3lut0o3f1` 생성 (2026-07-23).
- 33-02 백업 + 복원 리허설 PASS 선행 확인 (D-31): 11/11 doc, S3 SHA-256 메타, 재다운로드 바이트비교,
  에뮬레이터 복원 라운드트립 — 백업 없이는 어떤 write 도 금지 원칙 충족.

## Task 2 — Pod 핀 커밋 배포 + /health canary + 트래픽 격리

**GPU:** NVIDIA GeForce RTX 4090, 24564 MiB, driver 570.195.03
**Volume:** MooseFS `/workspace` (네트워크 스토리지, 생존) — rtmw-x-384.onnx (352M) + yolox_m.onnx (97M) 상주
**핀 커밋:** `8682c83acda0f9ba89e3ce7211954cc0d5c0bc48` (git reset --hard, bootstrap `git pull` no-op 확인)

**/health canary body (X-RunPod-Token 인증, 실제 응답):**

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

- canary 확인 (codex concern 6 — bare 200 불충분): `commitSha` == 핀 커밋 ✓, `envFlags` PR=1/deterministic=1 ✓,
  `modelInitCanary.modelLoaded=true` + poseEngine=RTMWPoseEngine ✓.
- 서버 기동 로그에서 `RTMW deterministic mode ON (RTMW_DETERMINISTIC=1, eval 전용)` 확인.
- `SUNITY_COMMIT_SHA` 는 start_server 부모 셸에서 주입 (start_server.sh 에 RTMW_DETERMINISTIC/SUNITY_COMMIT_SHA
  누락 → 부모 export 로 자식 uvicorn 상속).

**트래픽 격리 (codex concern 14):** **전용 eval Pod** — 프로덕션 Lambda 를 이 Pod 로 **재동기화하지 않음**
(`RUNPOD_ANALYZE_URL` 무접촉; Lambda 에서 `RUNPOD_AUTH_TOKEN` 만 READ). 외부 분석이 재추출 serial 과
동시 실행될 수 없음. isolation mode = dedicated (drain 아님).

## Task 3 — 재추출 11종 @9fps → candidate run1 + run2

**커맨드:** `reprocess_reference_motions_phase4.py --motions <11> --target-fps 9.0 --no-flip --version phase33-cm3-run1`
(run2 동일, `--version phase33-cm3-run2`). env: `PR_INVERSION_ENABLED=1 RTMW_DETERMINISTIC=1`.

**결과:** 11/11 → `reference/{id}/versions/phase33-cm3-run1` (및 `run2`), schema gate 전부 PASS,
`--no-flip` 로 active pointer flip 생략. 소요 run1 287.8s / run2 재추출 코어.

### 안전 (틀리면 걸리는 장치, D-18):
- **활성 포인터 불변 (전수 확인):** 11/11 `activeVersion=phase4_v1` 유지 (run1·run2 후 모두 재확인).
- candidate run1·run2 doc 11/11 존재. `versions/phase4_v1` 덮어쓰기 0 (33-17 refuse-overwrite + candidate!=active).
- **전역 릴리스 포인터 `reference/_release` 부재 (ABSENT)** — 활성화 소스 미생성 (flip 은 33-07).

### R-1 — detect_inversion 로그 vs 재처리 위험도 표 (프레임수로 모션 매핑, run2 root-logger 캡처):

| 모션 | frames | is_inverted | ratio | 예측(위험도 표) | 판정 |
|------|--------|-------------|-------|----------------|------|
| ref-climb | 172 | False | 0.000 | 미검출 | ✓ |
| ref-combo | 621 | **True** (applied 621/621) | 0.283 | 검출 | ✓ |
| ref-elbow-twist-sister | 220 | **True** (applied 220/220) | 0.667 | 검출 | ✓ |
| ref-foxtop | 284 | **True** (applied 284/284) | 0.609 | 검출 | ✓ |
| ref-foxtop-split | 324 | **True** (applied 324/324) | 0.651 | 검출 | ✓ |
| ref-invert | 174 | **True** (applied 174/174) | 0.341 | 검출 | ✓ |
| ref-kip-up | 79 | False | 0.000 | 미검출 | ✓ |
| ref-pdshape | 159 | **True** (applied 159/159) | 0.721 | 검출 | ✓ |
| ref-peter-pan | 87 | False (run=0) | 0.000 | 미검출 | ✓ (R-2) |
| ref-power-spin | 106 | False (run=1) | 0.015 | 미검출 | ✓ (R-2) |
| ref-sideway-spin | 199 | False | 0.000 | 미검출 | ✓ |

- **검출 6종 = 예측 6종 정확 일치** (combo, elbow-twist-sister, foxtop, foxtop-split, invert, pdshape).
  프록시(pole_aligned) ratio 와 실측(픽셀 x,y+score) ratio 는 값이 다르나 검출 여부 6/6 일치 (R-1 프록시 한계 노트대로).

### R-2 — 경계 동작 오검출 방지:
- **power-spin: run=1, ratio 0.015** — 임계(INVERSION_MIN_RUN=5) 훨씬 하회, PR 미발동.
  spike 실측상 power-spin 오검출 시 추적 파괴(boneCV 1.03→7.0) → **파괴 없음 확인**.
- **peter-pan: run=0, ratio 0.000** — PR 미발동.

### R-4 — ref-combo(및 11종 전체) 재현성 run1 vs run2:
- **11종 전체 max|Δangle| = 0.000000° / max|Δjoints3d| = 0** — 채점 소비 데이터 bit-identical.
- ref-combo(931→621 frame, 과거 23.43°→0.193° 요동 이력): **max|Δangle| 0.000000°** — 결정론 완벽, 요동 해소.
- doc field diff (run1 vs run2): **`pipelineVersion`(candidate id) + `reprocessedAt`(타임스탬프) 2개만 상이**,
  angles/joints3d/keypointReport 등 데이터 필드 전부 동일.

### No threshold refit (D-20/D-29):
- pose 재추출 + PR env(PR_INVERSION_ENABLED) 만 변경. 채점 임계/산식 코드 무접촉 (git diff scoring files 없음).

## 릴리스 매니페스트 (33-18 release_manifest.py) — candidate 당 1행

두 candidate 매니페스트 `create` + `verify` PASS (11/11 해시 일치, verify exit 0):

**공통 튜플:** commit `8682c83…`, targetFps 9.0, prInversionEnabled True, rtmwDeterministic True,
derivedFieldSchemaVersion `phase33-cm3-v1`, verificationResult None (검증은 33-06).

### phase33-cm3-run1 perDocHashes (SHA-256):
```
ref-climb                189818749ceb9e6ac60ce3326a93840dd080a07ad3a9dd9279bf1ad8fba3fd31
ref-combo                962858007db729a7a3493b94040c0a2d78ccd43c2bc68a0387bd750f8ee99cdf
ref-elbow-twist-sister   ab405e277e9a99244f511b0667051d2ebec77627494377b79447e8fb391b902c
ref-foxtop               772fc74583e083be60c2064d1a675743da219ff88612443f5559ad3b81b86c35
ref-foxtop-split         b7ace7bf652b0ece2f1c6fbe60fb218a2d4e4b3ef6bc2316db1673a96478eba6
ref-invert               4675914993a5bbfcc06805070162eb8eaf4fd98774eb6430bfab56eeacc81922
ref-kip-up               b9a30db6698a60b1325634a32c1315e18d6736c39339aec52d09024f025fe44d
ref-pdshape              8705f364e818c8f9ec50ed637d70a9e4263a835b41a6d2caa681effd9fb6b19e
ref-peter-pan            0acce03f4e7d88f38bf6a23cde7699ea23b1dbf6a2154a31340be99a3b64e636
ref-power-spin           f6eb4a22c3ecf5451ae10c5241a7ba0ef6bd857f43d064fd9e0c3edb6f85164a
ref-sideway-spin         27786be791bdf6a3da35b8548f39703434d3cf9ad3e1a6bc1bd2da9b05dd7db2
```

### phase33-cm3-run2 perDocHashes (SHA-256):
```
ref-climb                599350d4ad6546db4a79fc79fb281392e930bdf6bf07d32fb83a77e585e51750
ref-combo                7bd064cd7f3442d851340a467b796a0faa40c9fe752462d381276fbae2135c11
ref-elbow-twist-sister   df4ac7892db5ef9f8766ec6bba06f15e79e8181a11ca56a0f427bc2440b1f0a1
ref-foxtop               73fffab15a1472660b1ebc74d7e751b0f10b48d91c06f46c497a91752962abf1
ref-foxtop-split         d4b19647e588353a2f72aeaf0bf6da221748140c544efdd489c833bd9398e8b4
ref-invert               e369e4158f85fb7363eba6a95ede7c659d8257565d2c7eb6056812ea8486decc
ref-kip-up               4dab9567687edc0593f630b16625defe7d4b0caf5eb8f78dd3d71951a53e25d9
ref-pdshape              7cea2f8e9df8306b5ea15173fbd416ea740deaa44f8a3530179af4aed40585d9
ref-peter-pan            1e964705520a9e9e8a149ea4efa8aa2bd66c6ce2d15f00bd85ddb1250be812c8
ref-power-spin           13c02ccdc1fbb51ddab739f6a27b15fb14db80001cd846e265c5e302c7865e6f
ref-sideway-spin         875fbdaaa1958ad76d8f99ca0ead0060650bfbddef875412891325ef7936146b
```

**run1 vs run2 매니페스트 해시 상이 설명:** `doc_content_hash` 는 doc 전체(candidate id
`pipelineVersion` + `reprocessedAt` 타임스탬프 포함)를 해시하므로 run1≠run2. **데이터 자체는
bit-identical** (angles/joints3d Δ=0, 위 R-4). flip(33-07) post-write verify 는 candidate 자신을
top-level 에 미러 후 같은 함수로 재해시 → self-consistent (부분 활성화 검출은 유효).

**매니페스트 파일 위치 (Pod, 네트워크 스토리지 생존):** `/workspace/_manifest_run1.json`, `/workspace/_manifest_run2.json`.

## 종합

| 항목 | 결과 |
|------|------|
| 11종 candidate 기록 (run1+run2, no-flip) | PASS |
| active pointer 불변 (phase4_v1) | PASS (전수) |
| /health canary (commit + flags + model) | PASS |
| 트래픽 격리 (dedicated eval Pod) | PASS |
| R-1 인버전 검출 6종 = 예측 6종 | PASS |
| R-2 power-spin/peter-pan 미검출 | PASS |
| R-4 run1↔run2 재현성 (Δangle=0) | PASS |
| 매니페스트 run1·run2 verify | PASS (11/11) |
| 임계 refit (D-20/D-29) | 0 (무접촉) |

active pointer flip 은 33-07 (C+M3 원자 tuple flip). 다음: 33-04 (candidate-aware 백필).
