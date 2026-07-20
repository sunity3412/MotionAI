---
phase: 31-api-visual-correction
plan: 09
subsystem: backend-visual-execution
tags: [lambda, sqs, state-machine, outbox, claim-lease, privacy, delete-fence, pose-gate]
requires:
  - "31-02 (visual job 데이터 계약 — claim 4상태 / transition snapshot / finalize privacy gate / delete-fence)"
  - "31-05 (visual_gen — Wan 어댑터 / download_vendor_asset / safe_decode_image / judge_corrected_pose)"
  - "31-06 (pose_gate — measure_generated_pose + preserved_targets)"
  - "31-07 (pair_store — caller-fixed pairId / validate_hmac_key_set)"
  - "31-13 (CALIBRATION.json — 현재 blocked, 임계값 미방출)"
provides:
  - "visual-worker Lambda — action 단위 state machine (create/poll/fetch/judge/pose_check/postprocess + iam_probe)"
  - "visual-dispatch Lambda — durable outbox 복구 발행 + privacy janitor(delete-fence)"
  - "list_stuck_visual_jobs.py — stuck 조회 + reconciler + cleanup_blocked remediation"
affects:
  - "31-10 (SAM template: 두 함수 정의 + env 주입 + build gate 부등식 + alarm)"
  - "31-12 (IAM canary — worker 의 iam_probe action 소비)"
tech-stack:
  added: []
  patterns:
    - "외부 side-effect 당 invocation 1개 + claim 반환 snapshot 만 handoff (B6-01)"
    - "전이 = transaction 원자 outbox; SQS send 는 best-effort, 복구 주체는 별도 dispatcher"
    - "delete 3단 fence: claim CAS → claim_key_for_delete → **delete 직전** commit_key_delete"
    - "임계값 전량 env 주입 + 부재 시 fail-closed (D-08) — 추측 기본값 금지"
key-files:
  created:
    - backend/functions/visual-worker/app.py
    - backend/functions/visual-worker/requirements.txt
    - backend/functions/visual-dispatch/app.py
    - backend/functions/visual-dispatch/requirements.txt
    - backend/scripts/list_stuck_visual_jobs.py
  modified:
    - backend/tests/phase31/test_visual_worker.py
    - backend/tests/phase31/test_visual_dispatcher.py
decisions:
  - "preserved_targets 의 원본 각도는 pose_gate 의 정규화/전송/각도추출 경로를 그대로 재사용해 얻는다 — 워커에서 keypoint→각도를 재구현하면 fault_zoom.joint_inner_angle_deg 단일 출처가 깨져 생성 지시와 검증 기준이 갈라진다(B2-01)"
  - "Content-Type 정확 일치를 호출자(worker)에서 다시 건다 — 31-05 의 startswith 판정은 'video/mp4foo' 를 통과시키는데, 공유 모듈은 타 플랜 소유라 수정 대신 caller 방어"
  - "calibration env 부재는 typed 실패로 종결(카드 미노출). CALIBRATION.json 이 blocked 라 기본값을 두면 근거 없는 교정 이미지가 노출된다"
metrics:
  duration: ~2h
  tasks: 3
  tests-added: 256
  completed: 2026-07-20
---

# Phase 31 Plan 09: visual 실행기(worker + dispatcher) Summary

유료 잡이 고아도 중복 과금도 영구 불일치도 임시 생체 프레임 잔존도 될 수 없는 비동기 실행기 — claim 4상태 + owner/lease CAS + 모든 terminal 의 postprocessing 경유 + delete-fence janitor 를 256개 테스트로 고정.

## 무엇을 만들었나

**Task 1 — 워커 골격** (commit `48d1d50`)
`lambda_handler` 의 claim 규율이 전부다. `busy` 를 **정상 ACK 하지 않는 것**이 핵심인데, ACK 하면 그 action 의 유일한 재전달 기회가 사라져 claim 을 쥔 worker 가 죽었을 때 복구가 lease 만료까지 지연된다. `change_message_visibility(남은 lease + jitter)` 로 반납해 재전달 시점을 lease 만료 직후에 맞춘다.

`begin_visual_job_create` 5상태 분기에서 `unconfirmed` 는 **자동 재생성하지 않는다**. create 가 벤더에 도달했는지 알 수 없으므로 재시도가 곧 이중 과금이다.

**Task 2 — correctedPose 체인** (commit `e7b314f`)
fetch → judge → pose_check → postprocess. 아래 "실제로 잡힌 것" 절에 핵심이 있다.

**Task 3 — rotation + dispatcher + 운영 스크립트** (commit `d8e5cdc`)
dispatcher 를 별도 Lambda(reserved concurrency 1)로 둔 이유는 worker 가 backlog 로 동시성을 다 먹었을 때 복구가 굶지 않게 하기 위함이다 — 정확히 복구가 필요한 순간에 복구가 멈추는 구조를 피한다.

## 상류 배선 2건 (놓치면 조용히 무력화되는 것)

**1. `preserved_targets` 는 넘기지 않으면 존재하지 않는 것과 같다.**
31-06 의 게이트는 이 인자가 없으면 **목표 관절만** 검사한다. 그러면 "목표 관절은 맞췄는데 나머지 포즈를 통째로 새로 그린" 산출물이 통과한다 — 31-01 실측 스모크에서 8건 중 6건이 그 실패 모드였다. 즉 배선을 빠뜨리면 게이트는 켜져 있는데 지배적 실패를 하나도 막지 못한다.

원본 각도는 **pose_gate 의 정규화/전송/각도추출 경로를 그대로 재사용**해 구한다(`_source_preserved_angles`). 워커에서 keypoint→각도를 다시 구현하면 `fault_zoom.joint_inner_angle_deg` 단일 출처가 깨지고, 생성 지시(target_deg)와 검증 기준이 서로 다른 계산이 되어 B2-01 이 막으려던 실패 모드가 되살아난다. 원본 측정 실패는 fail-closed(`pose_gate_unavailable`) — 보존 여부를 판정할 수 없으면 통과가 아니다.

**배선이 진짜인지 mutation 으로 확인했다.** `preserved_targets=`/`preserve_tolerance_deg=` 두 줄을 지우고 돌리면 `test_pose_gate_receives_preserved_targets_from_source_frame` 과 `test_whole_pose_regeneration_is_rejected` 가 실패한다. 통과하는 테스트가 아니라 **빠지면 깨지는** 테스트다.

**2. Pillow 는 judge 를 실제로 호출하는 함수에 있어야 한다.**
`pipeline/requirements.txt` 는 Pillow 를 의도적으로 제외한다(250MB 한도, 실측 262MB 초과가 파일에 박제돼 있다). 그 제약은 pipeline 함수의 것이고, `prepare_judge_payload`/`safe_decode_image` 를 호출하는 주체는 새 visual-worker 다. **pipeline 은 손대지 않고** worker 쪽에 Pillow 를 넣었다. dispatcher 는 이미지를 열지 않으므로 넣지 않았다.

## calibration blocked 를 fail-closed 로 소비

`smoke/CALIBRATION.json` 은 `blocked: true` 이고 임계값을 하나도 방출하지 않는다(PASS fixture 3<4, pose 축 12/12 미측정, confidence 축 비변별). 이건 결함이 아니라 측정 결과다.

그래서 임계값 5종(`DISPLAY_JUDGE_CONFIDENCE` / `TRAINING_JUDGE_CONFIDENCE` / `DISPLAY_POSE_TOL_DEG` / `TRAINING_POSE_TOL_DEG` / `PRESERVE_POSE_TOL_DEG`)은 전부 `_required_float_env` 로만 읽고, **부재/파싱 불가 시 typed 실패로 종결**한다. 기본값 fallback 은 코드에 없고 테스트가 그 부재를 강제한다. 결과적으로 채택값이 주입되기 전까지 교정 카드는 노출되지 않는다 — 근거 없는 이미지를 보여주는 것보다 안 보여주는 쪽이 항상 낫다. 블록 해소는 31-12 배포 시점 몫이다.

**실 Pod 호출 0건.** 운영 Pod 는 phase-31 이전 코드로 belle 의 분석 서비스를 서빙 중이라 전부 mock 으로 검증했다.

## 검증 중 실제로 잡힌 것 2건

**1. janitor 가 claim 직후 crash 한 건을 영원히 놓치고 있었다 (Rule 1).**
초판 `_scan_reservations`/`_scan_orphans` 는 `state == "open"` 만 훑었다. 그런데 janitor 가 claim 하면 state 가 `claimed_by_janitor`/`claimed` 로 바뀐다 — **claim 된 순간 스캔 대상에서 사라진다.** 그 직후 crash 하면 `claim_reservation_for_janitor` 의 재claim 로직(B9-01)이 멀쩡히 있어도 호출될 기회가 없어 임시 생체 프레임이 영구 잔존한다. `test_janitor_claim_crash_is_recovered_after_lease` 가 잡았고, 두 state 를 각각 독립 cursor 로 훑도록 고쳤다. orphan 쪽도 같은 함정이라 같이 고치고 테스트를 추가했다.

**2. 공유 다운로더의 Content-Type 판정이 prefix 매칭이다.**
`visual_gen.download_vendor_asset` 은 `content_type.startswith(t)` 로 판정해서 `video/mp4foo` 가 통과한다. M5-02 는 exact membership 을 요구한다. `visual_gen.py` 는 31-05 소유라 수정하지 않고 호출자에서 `_assert_exact_content_type` 로 다시 걸었다. 테스트 fixture 는 31-05 의 실제(startswith) 동작을 그대로 모사하므로, worker 방어가 없으면 `video/mp4foo` 케이스가 실패한다.

## 계약 고정 지점 (테스트로 강제)

| 리뷰 | 계약 | 테스트 |
|---|---|---|
| B5-01/M6-03 | busy → change_visibility + batchItemFailures (정상 ACK 금지) | `test_same_seq_active_lease_is_busy_not_acked` |
| B6-01 | claim 이후 inbound msg 재사용 0 (정적) | `test_worker_never_reconstructs_job_from_inbound_message` |
| H6-07 | owner 같아도 lease 만료면 write 거부 | `test_late_worker_with_lost_lease_cannot_write` |
| B8-01 | reserved → acquired → 즉시 create 1회 / 동시 2건도 1회 | `test_reserved_acquire_creates_exactly_one_vendor_task` 외 1 |
| B2-02 | create_unconfirmed 자동 재생성 0 | `test_create_unconfirmed_never_recreates` |
| B4-02 | sync succeeded 거부 | `test_sync_succeeded_is_rejected_async_only` |
| B4-03/H5-03 | moderation retry → generation+1 + 새 gen requestKey | `test_moderation_retry_promotes_generation_and_request_key` |
| H7-01 | creating 내부 전이 SQS 발행 0 | `test_creating_internal_transition_emits_no_sqs_message` |
| **31-06 preserve** | preserved_targets 전달 + 전면 재생성 차단 | `test_pose_gate_receives_preserved_targets_from_source_frame`, `test_whole_pose_regeneration_is_rejected` |
| **D-08** | 임계값 5종 부재 → 카드 미노출 | `test_missing_calibration_never_shows_the_card` (5 params) |
| H6-03 | staging/canonical hash 불일치 overwrite 0 | `test_staging_hash_conflict_blocks_overwrite` |
| H7-08 | canonical copy REPLACE + sha256 보존 | `test_canonical_copy_preserves_sha_metadata` |
| H5-01 | PUT 직전 consent 재read | `test_consent_revoked_between_pose_check_and_postprocess` |
| B5-03 | pairId pose_check 고정 + postprocess 재선택 0 | `test_pair_id_fixed_at_pose_check_not_reselected` |
| H6-05 | HMAC config 실패가 display 를 막지 않음 | `test_hmac_config_failure_does_not_block_display` |
| H7-07/H8-02 | pair 실패는 self-loop 0 + 즉시 cleanup/finalize | `test_pair_network_failure_does_not_delay_cleanup_or_finalize` |
| B6-04 | cleanup 미완 → terminal finalize 0 + blocker | `test_cleanup_blocked_never_finalizes_terminal` |
| B7-04 | failed 도 cleanup 증명 요구 | `test_failed_terminal_also_requires_cleanup_proof` |
| B10-03 | worker cleanup 후 ownership release | `test_worker_releases_key_ownership_after_cleanup` |
| H6-01 | sent-recovery 는 same-seq expired claim 만 | `test_sent_recovery_only_reissues_same_seq_expired_claims` |
| B5-01 | CAS 직후 crash → dispatcher 가 다음 action 발행 | `test_worker_crash_after_cas_is_recovered` |
| H4-08 | backlog 전량 drain (cursor starvation 0) | `test_backlog_drains_across_cycles` |
| B11-01 | 늦은 claimant 의 delete 차단 + commit 이 delete 직전 | `test_late_claimant_cannot_delete_after_lease_expiry`, `test_commit_is_rechecked_immediately_before_delete` |
| B11-04 | job ref 는 영구 live | `test_live_job_ref_blocks_deletion`, `test_orphan_never_deletes_input_of_a_live_job` |
| B9-01 | janitor claim crash 복구 (reservation + orphan) | `test_janitor_claim_crash_is_recovered_after_lease` 외 1 |
| M5-02 | content-type exact membership | `test_rotation_content_type_exact_membership` (4 params) |
| H3-01/M3-04 | job/analysis/SQS 3면 URL 부재 | `test_no_urls_anywhere_in_serialized_state` |

## Deviations from Plan

**1. [Rule 2 - 누락된 필수 기능] `PRESERVE_POSE_TOL_DEG` env 추가**
- 플랜은 임계값 env 4종만 명시한다(B4-05). 그런데 31-06 의 `measure_generated_pose` 는 `preserved_targets` 를 주면서 `preserve_tolerance_deg` 를 안 주면 **기준 없는 검사이므로 통과시키지 않는다**. 4종만으로는 preserve 검사를 켤 수 없다.
- 5번째 env 로 추가하고 나머지와 같은 fail-closed 규율(부재 → `pose_gate_unavailable`)을 적용했다. 31-10 template 이 주입해야 한다.

**2. [설계 판단] pose_gate 내부 헬퍼 3종을 워커가 재사용**
- `_normalize_for_pose` / `_post_pose_image` / `_angle_from_payload` 는 `_` 접두 private 이다. 공개 헬퍼를 pose_gate 에 추가하는 편이 형식상 깔끔하지만, 31-06 소유 파일을 병렬 wave 에서 수정하면 충돌 위험이 있고 무엇보다 **각도 계산을 워커에 재구현하는 쪽이 훨씬 위험하다**(B2-01 이 막으려던 계산 이원화).
- private 재사용을 택하고 이유를 코드 주석에 박았다. 31-06 이 이 헬퍼들의 시그니처를 바꾸면 워커 테스트가 즉시 깨진다.

**3. [Rule 1 - 버그] janitor 스캔 state 누락** — 위 "실제로 잡힌 것" 1번. 커밋 `d8e5cdc`.

**4. [Rule 2 - 누락된 방어] Content-Type exact membership 을 caller 에서 재검** — 위 "실제로 잡힌 것" 2번.

## Known Stubs

없음. 다만 **미배선 상태 2건**은 후속 플랜 소유임을 명시한다:
- 두 Lambda 의 SAM 정의/env 주입/EventBridge rule/alarm 은 31-10 몫이다. 그전까지 배포되지 않는다.
- 임계값 env 는 31-13 CALIBRATION 이 blocked 이므로 아직 **주입할 값 자체가 없다**. 이건 의도된 fail-closed 상태이며, 값이 정해질 때까지 correctedPose 카드는 노출되지 않는다.

## Threat Flags

없음. 플랜의 `<threat_model>` 밖 신규 공격면(신규 엔드포인트/인증 경로/스키마 변경)을 만들지 않았다. 두 Lambda 모두 인바운드는 SQS/EventBridge 이고 사용자 문서는 31-02 의 transaction 함수를 통해서만 만진다.

## 다음 플랜이 알아야 할 것

- **31-10 이 주입해야 하는 env**: `VISUAL_QUEUE_URL`, `VISUAL_INPUT_BUCKET`, `VIDEO_BUCKET`, `PAIRS_BUCKET`, `DASHSCOPE_API_KEY`, `RUNPOD_ANALYZE_URL`, `RUNPOD_AUTH_TOKEN`, `PAIR_ID_HMAC_KEYS`, `VISUAL_MODEL_ID`, 그리고 임계값 5종.
- **build gate 부등식 3개**는 31-02 가 `models.py` 주석에 박제했다. worker Timeout < `VISUAL_CLAIM_LEASE_MS` < visibility / pipeline+보상 <= `VISUAL_INPUT_RESERVATION_TTL_MS` / dispatch Timeout < `VISUAL_OBJECT_DELETE_LEASE_MS`.
- **dispatcher 는 reserved concurrency 1** 이어야 한다(cursor 경쟁 방지 + 복구 굶김 방지).
- **alarm 대상 metric**: `ScannedOutboxMaxAgeMs`, `OutboxScanTruncated`, `VisualCleanupBlocked`, `VisualPairConflict`, `Visual{Reservation,Orphan}{OldestAgeMs,SweepFailed}`.
- **31-12 canary** 는 `action="iam_probe"` 메시지를 보내면 된다 — 외부 side-effect 0 으로 소비된다.

## 테스트

- `python3 -m pytest backend/tests/phase31 -q` → **361 passed** (31-02 의 105 + 본 플랜 256)
- `python3 -m pytest backend/tests -q` → 41 failed / 3272 passed / 20 skipped
  - **41 failures + 2 collection error 는 전부 pre-existing** (31-02-SUMMARY 가 기록한 baseline 과 동일 수치). 원인은 누락된 optional dep(`cv2` 등)이며 본 플랜 범위 밖이라 손대지 않았다. 실패 목록에 phase31/visual 항목은 **0건**이다.

## Self-Check: PASSED
- 생성 파일 5개 전부 존재 확인
- 커밋 3개 존재 확인 (`48d1d50`, `e7b314f`, `d8e5cdc`)
- `backend/functions/pipeline/**` 미수정 확인 (`git diff --stat` 0 lines)
- STATE.md / ROADMAP.md 미수정 확인
