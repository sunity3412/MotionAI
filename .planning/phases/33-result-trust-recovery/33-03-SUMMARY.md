---
phase: 33-result-trust-recovery
plan: 03
subsystem: infra
tags: [runpod, rtmw, reference-versioning, pr-inversion, release-manifest, firestore]

requires:
  - phase: 33-02
    provides: 롤백 소스(백업+복원 리허설 PASS) — write 전제
  - phase: 33-17
    provides: candidate version id refuse-overwrite + candidate!=active 가드
  - phase: 33-18
    provides: /health commit-SHA canary + release_manifest.py
provides:
  - 11 reference 모션 9fps + PR 인버전 재추출본 (candidate versions/phase33-cm3-run1 + run2)
  - candidate 당 release manifest (run1/run2, verify PASS)
  - R-1/R-2/R-4 재추출 위험도 실측 증거
affects: [33-04, 33-06, 33-07]

tech-stack:
  added: []
  patterns:
    - "immutable candidate 버전 재추출 (active pointer 무접촉, flip 분리)"
    - "root-logger 부착으로 pr_inversion detect 로그 캡처(재추출 스크립트 미로깅 보완)"

key-files:
  created:
    - .planning/phases/33-result-trust-recovery/33-S1-REPROCESS-EVIDENCE.md
  modified: []

key-decisions:
  - "전용 eval Pod(k508k3lut0o3f1) — 프로덕션 Lambda 미재동기화로 트래픽 격리 (belle go)"
  - "SUNITY_COMMIT_SHA/RTMW_DETERMINISTIC 은 start_server.sh 미포함 → 부모 셸 export 로 주입"
  - "매니페스트 해시는 doc 전체(candidate id+reprocessedAt) 대상 → run1≠run2 정상, 데이터는 bit-identical"

patterns-established:
  - "재추출 재현성 증거는 매니페스트 해시가 아니라 angles/joints3d 직접 Δ 비교로 판정"
---

# 33-03 SUMMARY — S1 재추출 (11 reference @9fps + PR 인버전 → candidate run1+run2)

## 무엇을 했나

정은지 기준영상 11종을 **9.0fps + PR 인버전 보정**으로 재추출해 **불변 candidate 버전**
`phase33-cm3-run1`(+ 재현성 대조 `run2`)에 기록. 활성 데이터(`phase4_v1`)는 무접촉 —
flip 은 33-07. 채점 산식/임계 무접촉 (D-20/D-29). 전 과정 전용 eval Pod에서 실행.

## Task 별 결과

- **Task 1 (belle GPU greenlight):** belle "go — 전용 eval Pod" 선택 후 Pod `k508k3lut0o3f1` 생성.
  33-02 백업+복원 리허설 PASS 선행 확인.
- **Task 2 (Pod 배포 + canary):** RTX 4090, 핀 커밋 `8682c83`, `/health` canary PASS
  (commitSha == 핀, PR=1/deterministic=1, modelInitCanary green). 트래픽 격리 = dedicated
  (Lambda `RUNPOD_ANALYZE_URL` 무접촉, `RUNPOD_AUTH_TOKEN` 만 READ).
- **Task 3 (재추출):** 11/11 → `versions/phase33-cm3-run1`+`run2`, schema gate 전부 PASS,
  `--no-flip`. active pointer 11/11 `phase4_v1` 유지, `reference/_release` 부재.

## 검증 (게이트 전수)

| 항목 | 결과 |
|------|------|
| R-1 인버전 검출 6종 = 예측 6종 (combo/elbow-twist-sister/foxtop/foxtop-split/invert/pdshape) | PASS |
| R-2 power-spin(run=1,0.015)·peter-pan(run=0) 미검출 → 추적 파괴 없음 | PASS |
| R-4 11종 max\|Δangle\|=0.000000° / max\|Δjoints3d\|=0 (combo 요동 이력 해소) | PASS |
| 매니페스트 run1·run2 create+verify (11/11 해시) | PASS |
| active pointer 불변 + refuse-overwrite | PASS |
| 임계 refit (D-20/D-29) | 0 |

증거 전문(canary body, detect 로그, perDocHashes 등): `33-S1-REPROCESS-EVIDENCE.md`.

## 편차/주의

- 재추출 스크립트가 `pr_inversion detect` 를 자체 로깅하지 않아(rtmw_engine 로거 non-propagated),
  run2 를 root-logger 부착 래퍼로 재실행해 R-1/R-2 증거를 캡처. run1 데이터에는 영향 없음(결정론 동일).
- 재추출 완료 tail 의 "active flip 완료" 는 스크립트 하드코딩 메시지 — `--no-flip` 하에선 부정확.
  실제 flip 미수행은 active pointer 전수 확인 + `_release` 부재로 검증.

## 다음

33-04 (candidate-aware 백필: versions/{candidate} read+merge, real bodyComparisonSourcePose, warm-Pod).
Pod `k508k3lut0o3f1` + 서버 가동 중 — 33-04 도 이 Pod 재사용 가능.
