---
phase: 31-api-visual-correction
plan: 10
subsystem: backend
tags: [lambda, iac, s3, privacy, sqs, firestore]
requires:
  - 31-02 (visualJobs substrate — reserve/reservation/key-ownership/orphan)
  - 31-03 (CorrectedPoseTarget)
  - 31-05 (judge payload)
  - 31-09 (visual-worker / visual-dispatch)
  - 31-13 (CALIBRATION 스윕 — blocked 로 종결)
provides:
  - POST /visual/rotation (visual-request Lambda)
  - POST /playback-url asset 확장 (correctedPose | rotation)
  - pipeline _enqueue_corrected_pose_job (D-05 자동 생성 진입점)
  - SAM IaC — VisualQueue/DLQ, 함수 3종, 알람 8종, build gate 4종
  - backend/scripts/visual_infra_dryrun.py + lifecycle 산출 4파일
affects:
  - backend/functions/pipeline/app.py (additive — 훅 + 호출부)
  - backend/template.yaml (신규 Parameter 6 + 리소스 다수)
tech-stack:
  added: []
  patterns:
    - upload-first + producer preflight (B3-03 / B6-03)
    - per-invocation immutable reservation (B8-05)
    - active|deleting delete-fence + claim/commit fencing token (B11-01/B11-02)
    - fail-closed env parsing (M-06) / fail-open 금지 Parameter (H10-05)
key-files:
  created:
    - backend/functions/visual-request/app.py
    - backend/functions/visual-request/requirements.txt
    - backend/scripts/visual_infra_dryrun.py
    - .planning/phases/31-api-visual-correction/infra/visual_input_lifecycle_before.json
    - .planning/phases/31-api-visual-correction/infra/visual_input_lifecycle_merged.json
    - .planning/phases/31-api-visual-correction/infra/video_lifecycle_before.json
    - .planning/phases/31-api-visual-correction/infra/video_lifecycle_merged.json
  modified:
    - backend/shared/python/sunity_shared/validation.py
    - backend/functions/playback-url/app.py
    - backend/functions/pipeline/app.py
    - backend/template.yaml
    - backend/tests/phase31/test_visual_url.py
    - backend/tests/phase31/test_visual_request.py
    - backend/tests/phase31/test_visual_dispatch.py
decisions:
  - "4 게이트 env 를 Default 없는 Parameter 로 선언 — CALIBRATION 이 blocked 라 chosen 값이 존재하지 않으며, 값을 발명하는 대신 배포가 실패하게 두었다"
  - "VisualDispatchFunction Timeout 을 플랜의 60 대신 120 으로 — models.py 의 lease 부등식 주석이 120 을 전제한다"
  - "option-b(trainingSrcKey 2차 PUT) 미구현 — pair_store.BLUR_OPTION='none'(belle option-a) 이라 분기 자체가 채택되지 않았다"
  - "correctedPose 호출부는 mode1 전용 — target_deg 의 출처가 DTW 매칭된 reference 3점 내각이라 비교 기준 없는 mode3 에는 목표각이 없다"
metrics:
  tasks: 3
  commits: 5
  duration: ~1 세션
  completed: 2026-07-20
---

# Phase 31 Plan 10: HTTP 표면 · 분석측 dispatch · IaC Summary

요청(POST /visual/rotation)과 자동생성(pipeline 훅) 두 진입점을 동일 durable substrate 로 배선하고, 임시 생체 프레임을 **비-버저닝 전용 버킷**에 upload-first + delete-fence 로 다루는 IaC 까지 배포 직전 상태로 완성했다. 배포는 하지 않았다.

## 무엇을 만들었나

**Task 1 — playback-url asset 재서명 (commit e988448)**

`validate_analysis_id_format` 를 `validation.py` 로 이관해 세 진입점이 같은 규칙을 쓰게 했다 (L-03). asset 경로의 핵심은 M2-01 이다: 저장된 key 를 그대로 서명하지 않고 **서버가 canonical key 를 새로 구성해 전체 문자열 일치**를 요구한다. 생성이 실패해 status 가 `failed` 로 돌아간 뒤에도 이전 성공분 key 필드가 문서에 남을 수 있는데, prefix/basename 부분일치만 보면 그 stale key 가 계속 서명되기 때문이다. `status=='done'` 강제와 exact equality 두 가지를 모두 요구한다. 위반은 전부 동일 404 (leak 0). asset 미지정 요청은 검증 순서까지 그대로 두어 응답이 바뀌지 않는다.

**Task 2 — visual-request Lambda (commit e096db0)**

이 함수의 write 는 `reserve_visual_job` 하나뿐이다. 표시 pending 도 초기 outbox 도 그 transaction 안에서 기록된다 (B3-03) — 별도 pending write 가 없음을 grep 테스트로 고정했다. SQS send 는 best-effort 이고 실패해도 202 를 준다 (H3-09): 500 을 주면 사용자는 quota 를 태운 채 실패를 보고, 재요청은 기존 job 을 만나 no-op 이 되어 영영 생성되지 않는다. 한도 env 는 fail-closed 파싱이다 — 오타 하나로 과금 상한이 조용히 사라지느니 전부 429 가 되는 쪽을 택했다 (M-06).

**Task 3A — pipeline enqueue 훅 (commit 5150752)**

`_enqueue_corrected_pose_job` 는 enqueue 만 한다(벤더 호출 0). 순서는 preflight → reservation+ownership → 조건부 PUT → reserve → 정리다. 삭제와 관련해 지킨 계약이 이 훅의 본체다:

- producer 의 **모든** 객체 삭제가 `claim_key_for_delete` + `commit_key_delete` 를 지난다 (B11-02). 직접 `delete_object` 를 부르면 같은 deterministic key 를 쓰는 다른 live job 의 입력이 사라진다. 테스트가 `delete_object(` 등장 횟수 1을 고정한다.
- 모든 종료 경로(collision / PUT 실패 / terminal-replay / loser / reservation_lost)가 `release_key_ownership` + reservation close 를 수행한다 (B10-03 / B11-03).
- `state=='deleting'` 이면 lease 만료 여부와 무관하게 acquire 가 막힌다 (B11-01).

호출부 `_maybe_enqueue_corrected_pose` 는 **flag 를 가장 먼저 본다** — OFF(기본)면 프레임 인코딩도 reference 재추출도 하지 않아 운영 분석 경로 비용이 0 이다. Pillow 는 lazy import 라 `pipeline/requirements.txt` 는 손대지 않았다(250MB 한도 유지).

**Task 3B — SAM template (commit aee7d17)**

큐 1 + 함수 3 + 알람 8 + LogGroup 3. build gate 4종을 테스트로 강제한다: claim lease 부등식(H6-07), strict ordering(B4-05), reservation TTL ≥ pipeline timeout+보상+margin(H9-01), delete lease > dispatcher timeout+skew(B11-01). worker 에는 Schedule 이 없고(H3-09) dispatcher 는 동시성 1이다. IAM 에 버전 액션(`s3:DeleteObjectVersion`/`ListBucketVersions`)이 없음과 존재하지 않는 `s3:HeadObject` 를 쓰지 않음을 파싱 단언으로 고정했다.

**Task 3C — 인프라 dry-run (commit c631cc5)**

read-only 스크립트를 1회 실행해 실측을 남겼다. 산출 4파일은 31-12 의 전제다.

## 실측 결과 (dry-run 1회, mutation 0)

| 항목 | 관측 |
|------|------|
| visual-input 버킷 versioning | `Status` key 부재 = **Never-versioned** (통과) |
| visual-input 잔여 version | Versions 0 / DeleteMarkers 0 |
| visual-input Object Lock | 미설정 |
| videos(페어) 버킷 | versioning null + Object Lock 없음 → **canary 불필요** |
| SSM pair-id-hmac-keys | 존재 + 형식 유효 |
| lifecycle 산출 | 4파일, 각 `{"Rules":[...]}` shape validation 통과 |

`video_lifecycle_merged.json` 은 기존 `expire-raw-uploads-30d` 를 보존한 채 pairs 180일 규칙을 추가했다 (T-31-55).

## 테스트

| 파일 | 건수 |
|------|------|
| test_visual_url.py | 18 |
| test_visual_request.py | 24 |
| test_visual_dispatch.py | 71 |

- `python -m pytest backend/tests/phase31 -q` → **433 passed**
- `python -m pytest backend/tests -q --continue-on-collection-errors` → **57 failed / 3366 passed / 2 collection errors**
  - 사전 baseline(57 failed / 3256 passed / 2 errors)과 실패·에러 수 **동일**. 통과 +110 = 이 플랜 신규분.
- `cd backend && sam validate --lint` → valid

## 계획과 달라진 점

**1. [Rule 3 — 계약 불일치] VisualDispatchFunction Timeout 60 → 120**
플랜 (B) 는 Timeout 60 을 적었으나 `models.py` 의 `VISUAL_OBJECT_DELETE_LEASE_MS` 주석이 부등식 계약을 `VisualDispatchFunction Timeout(120s)*1000 + margin < 180,000` 으로 명시한다. 상수 쪽 주석을 단일 출처로 보고 120 을 채택했다. 두 값 모두 부등식은 만족하지만, 주석과 IaC 가 어긋난 채 남으면 다음 리뷰가 어느 쪽을 믿을지 알 수 없다.

**2. [Rule 2 — 설계 보존] 4 게이트 env 에 SAM Default 미부여**
플랜은 "CALIBRATION chosen 값 주입" 을 적었으나 `smoke/CALIBRATION.json` 은 `blocked: true` 이고 chosen 필드가 **없다**(pass 표본 3<4, pose 미측정 12/12, confidence 축 비변별). 값을 지어내면 31-09 의 fail-closed 설계가 무력화되고 미보정 임계값으로 카드가 사용자에게 나간다. Default 없는 Parameter 로 선언해 **override 없이는 배포가 실패**하게 했다. 지금 배포 불가인 것이 정상이며, 이는 결함이 아니라 측정 결과다. 테스트가 `blocked is True` 와 `"chosen" not in calib` 를 고정해 값 발명을 차단한다.

**3. [Rule 3 — 미채택 분기] option-b trainingSrcKey 2차 PUT 미구현**
플랜은 blur option-b 의 두 번째 조건부 PUT 과 그 보상 경로를 기술하나, `pair_store.BLUR_OPTION = "none"`(belle option-a 확정)이라 해당 분기는 채택되지 않았다. `pair_store` 자신도 "'pod_blur' 분기는 채택되지 않아 구현하지 않는다" 고 박제한다. `created_keys` 는 리스트로 일반화해 두어 option-b 채택 시 확장 지점만 남겼다.

**4. [범위 판단] correctedPose 호출부는 mode1 전용**
`build_corrected_pose_target` 의 `target_deg` 는 DTW 매칭된 **reference 3점의 내각**이다. 비교 기준이 없는 mode3 에는 목표각의 출처가 없어 호출부를 mode1 로 한정했다.

## 알려진 제약 (스텁 아님 — 후속 플랜 소유)

- **배포·라이브 적용 0.** `sam deploy`, lifecycle put, IAM simulate, 실 role canary 는 전부 31-12 소유다 (H5-07 / M8-01). 이 플랜은 코드와 제안 JSON 까지만 만든다.
- **4 게이트 값 미주입.** 위 항목 2. 보정을 다시 돌려 chosen 을 얻기 전에는 배포할 수 없다 — 의도된 차단이다.
- **producer 훅 E2E 미검증.** flag 기본 OFF 라 실제 흐름은 31-12 가 Pod env(`VISUAL_QUEUE_URL`/`VISUAL_JOBS_ENABLED`/`VISUAL_INPUT_BUCKET`) 와 credential 을 붙여 확인한다. 코드에 그 전제를 주석으로 박아 두었다.

## Threat Flags

없음 — 이 플랜이 만든 표면(2 HTTP 라우트 + SQS consumer + producer 훅)은 전부 플랜 `<threat_model>` 의 T-31-38~55/73/76/80/81 에 등재돼 있고, 각 mitigation 을 테스트로 고정했다.

## Self-Check: PASSED

생성 파일 존재 확인:
- FOUND: backend/functions/visual-request/app.py
- FOUND: backend/functions/visual-request/requirements.txt
- FOUND: backend/scripts/visual_infra_dryrun.py
- FOUND: .planning/phases/31-api-visual-correction/infra/visual_input_lifecycle_{before,merged}.json
- FOUND: .planning/phases/31-api-visual-correction/infra/video_lifecycle_{before,merged}.json

커밋 존재 확인:
- FOUND: e988448 / e096db0 / 5150752 / aee7d17 / c631cc5
