---
phase: 31-api-visual-correction
plan: 02
subsystem: backend-data-contract
tags: [firestore, visual-job, outbox, claim-lease, privacy, delete-fence]
requires: []
provides:
  - "models.VISUAL_* 상수 계약 (상태 10 / 실패 10 / privacy blocker / lease·TTL 숫자)"
  - "firestore_admin visual job 함수 9종 (reserve/transition/claim/begin_create/finalize/read/mark/list_dispatch_pending/update_analysis_visual)"
  - "reservation(5) · orphan(4) · key-ownership(6) state machine helpers"
  - "backend/tests/phase31/conftest.py — in-memory Firestore(진짜 optimistic concurrency) + 주입 시계 + DashScope urllib mock"
affects:
  - "31-04 (TS 계약 lockstep: correctedPose*/rotation* 표시 필드)"
  - "31-05~31-11 (전 구현 wave 가 본 계약 위에서 동작)"
tech-stack:
  added: []
  patterns:
    - "firestore_admin 최초의 @firestore.transactional 도입 — seam 4종(_collection/_field_filter/_query_start_after_name/_run_in_transaction)으로 분리해 테스트가 in-memory 로 교체"
    - "등가 쿼리 1개 + __name__ 정렬 + durable cursor 순환 = composite index 회피 (STATE.md phase-33 3f6681f 선례)"
key-files:
  created:
    - backend/tests/phase31/conftest.py
    - backend/tests/phase31/test_visual_jobs.py
    - backend/tests/phase31/test_visual_gen.py
    - backend/tests/phase31/test_pose_gate.py
    - backend/tests/phase31/test_pair_store.py
    - backend/tests/phase31/test_visual_worker.py
    - backend/tests/phase31/test_visual_dispatcher.py
    - backend/tests/phase31/test_visual_request.py
    - backend/tests/phase31/test_visual_url.py
    - backend/tests/phase31/test_visual_dispatch.py
  modified:
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/firestore_admin.py
decisions:
  - "begin_visual_job_create: 같은 owner 의 미만료 creating lease 도 'busy' 로 반납 (플랜 미명시 구간). stale(정상 ACK)이면 job 이 dispatcher 복구까지 멈추고, 재진입 허용이면 vendor create 이중 호출 여지가 생긴다"
  - "list_dispatch_pending cursor 는 스캔 끝이 아니라 **발행한 마지막 문서**까지만 전진 — 그래야 max_scan 초과 backlog 가 전량 drain 된다"
  - "reserve 는 key 승격 가능성을 모두 확인한 뒤에야 첫 write 를 버퍼링 (H10-01 all-or-nothing)"
metrics:
  duration: ~50min
  tasks: 3
  tests-added: 105
  completed: 2026-07-20
---

# Phase 31 Plan 02: visual job 데이터 계약 Summary

실루엣(correctedPose)·회전(rotation)이 공유하는 단일 durable visual job 계약을 상수·transaction 함수·105개 테스트로 고정 — outbox instance CAS, claim 4상태 + owner/lease CAS, 원자 finalize(unconditional privacy gate), active|deleting delete-fence 까지.

## 무엇을 만들었나

**Task 1 — 테스트 스캐폴드** (commit `5e2db75`)
`backend/tests/phase31/conftest.py` + 9개 테스트 파일 골격. 핵심은 mock 의 품질이다:
- in-memory Firestore 가 **문서 version 을 실제로 검사**한다. `run_contended(fn_a, fn_b)` 는 둘 다 commit 전 상태를 read → A commit → B 가 진짜 conflict 를 맞고 자동 재시도한다. "테스트가 통과하도록 짠 mock" 이 아니라 진짜 경쟁 재현이다.
- fake query 가 **등가 아닌 연산자와 `__name__` 외 order_by 를 거부**한다. composite index 가 필요한 쿼리를 코드가 쓰면 운영(FAILED_PRECONDITION) 이전에 테스트에서 죽는다.
- `commit_lost` 모드(commit 성사 + 호출측 예외), 주입 시계, DashScope urllib mock.

**Task 2 — models.py 상수 계약** (commit `4aba21a`)
`VISUAL_JOB_STATES` 10종(retry_ready/postprocessing 포함, dispatch_failed 부재), `VISUAL_FAILURE_REASONS` 10종 terminal, `VISUAL_PRIVACY_BLOCKERS`(비-terminal), lease/TTL/skew concrete 숫자 + 31-10 build gate 부등식 근거, reservation/orphan/key-ownership path·state.

**Task 3 — firestore_admin** (commit `bf4f141`)
핵심 9종 + reservation(5)·orphan(4)·key-ownership(6) helper. 본 모듈 최초의 `@firestore.transactional` 도입이라 seam 4종을 분리했다.

## 검증 중 실제로 잡힌 것 2건

계약이 아니라 **내 구현/mock 이 틀렸던** 지점이다. 둘 다 조용히 통과할 수 있는 종류라 기록한다.

1. **fake 의 `update()` 를 deep-merge 로 모사한 게 틀렸다.** 실 Firestore 는 `update({"refs": {...}})` 로 맵 전체를 교체한다. deep-merge 로 두면 **"ref 를 제거하는 write" 가 전부 no-op** 이 되어 ownership fence 의 핵심(자기 ref 소비 B10-01, release B10-03)이 거짓 통과한다. field-path 교체 의미로 수정했고, 그 뒤 4개 테스트가 진짜로 실패하며 버그를 드러냈다.

2. **dispatcher cursor starvation.** cursor 를 "스캔한 끝" 까지 밀면 window 당 `limit` 개만 발행되고 나머지 `max_scan - limit` 개는 매 순환마다 같은 자리에서 다시 건너뛰어진다. 1,200 backlog 재현 테스트에서 240개에 수렴하고 멈췄다. **발행한 마지막 문서까지만** 전진하도록 고쳐 전량 drain 을 확인했다 (H4-08 의도).

## 계약 고정 지점 (테스트로 강제)

| 리뷰 | 계약 | 테스트 |
|---|---|---|
| B4-01 | 늦은 mark 가 다음 continuation 을 덮지 못함 | `test_late_mark_from_previous_action_cannot_clobber_next_continuation` |
| B5-01 | claim 4상태 — claimedOutboxSeq 단독 판정 금지 | `test_claim_does_not_judge_on_claimed_seq_alone` 외 5 |
| B6-01 | 새 seq 시 claim clear + audit seq ≠ 새 seq | `test_transition_clears_claim_fields_on_new_outbox_seq` |
| H6-07 | owner 일치해도 lease 만료면 write 거부 | `test_transition_rejects_write_after_lease_expiry_even_for_same_owner` |
| H6-01 | same-seq expired claim 만 재발행 (정상 sent 0) | `test_sent_recovery_only_reissues_same_seq_expired_claims` |
| H4-07 | uid/analysisId 를 job 문서에서 파생 | `test_finalize_derives_identity_from_job_not_caller` |
| B8-01 | 동시 same-seq 2건 → acquired 1, vendor create 1 | `test_concurrent_begin_create_yields_exactly_one_acquire` |
| B8-02 | correctedPose (done\|failed)×(inputSealed False\|cleanup 0) 4조합 전부 거부 | `test_corrected_pose_terminal_gate_is_unconditional` (4 params) |
| B8-03 | cleanup 재확인 + blocker clear + terminal 이 한 transaction | `test_cleanup_blocked_recovers_in_one_transaction` |
| B8-06 | janitor 확인 → producer reserve → janitor claim 실패 → delete 0 | `test_janitor_cannot_delete_input_of_a_job_that_reserved_it` |
| B9-01 | janitor claim 직후 crash → lease 후 재claim | `test_janitor_claim_crash_is_recovered_after_lease_expiry` |
| H9-04 | reserve read-all-before-write (nested tx 금지) | `test_reserve_reads_everything_before_writing_anything` |
| H10-01 | 두 key 승격 + job 전부-또는-전무 | `test_reserve_creates_nothing_when_one_key_is_being_deleted` |
| B11-01 | 만료 deleting 도 producer acquire False + 늦은 J1 token 차단 | `test_producer_never_reclaims_a_deleting_key_even_after_lease_expiry` |
| B11-04 | job ref 는 expireAt 무시 항상 live | `test_job_ref_stays_live_forever_until_explicit_release` |

## Deviations from Plan

**1. [Rule 2 - 누락된 필수 기능] `visual_quota_doc_path()` 추가**
- 발견 시점: Task 2
- 플랜의 artifact 목록에 quota counter path 가 없는데 `reserve_visual_job` 은 `user_limit`/`global_limit` 을 원자 소비해야 한다(T-31-05). path helper 없이는 구현 불가.
- 조치: `models.visual_quota_doc_path(uid, date_key)` 추가. global 한도는 `_global` uid 로 같은 helper 재사용.

**2. [Rule 3 - 차단 이슈] reservation 문서에 `bucket` 필드 추가**
- 플랜의 reservation 필드 목록에 bucket 이 없는데, `visual_input_object_doc_path(bucket, key)` 로 ownership 을 찾으려면 bucket 이 필요하다. reserve 가 caller 인자 없이 reservation 문서만으로 key 승격을 하려면 문서가 bucket 을 알아야 한다.
- 조치: `create_input_reservation(..., bucket=...)` 로 기록. caller 인자 추가 없이 자립.

**3. [설계 판단] `begin_visual_job_create` — 같은 owner 의 미만료 lease → `busy`**
- 플랜은 (b) `leaseOwner != owner` 만 busy 로 명시하고 나머지는 (e) catch-all `stale` 이다. 같은 owner 가 미만료 lease 를 들고 재진입하는 경우가 명시되지 않았다.
- `stale`(정상 ACK)이면 job 이 dispatcher 복구까지 멈추고, 재진입 허용이면 vendor create 이중 호출 여지가 생긴다. `busy` 는 batchItemFailures → visibility 뒤 재전달이라 둘 다 없다.
- 플랜과 모순되지 않는(미명시 구간) 보수적 선택. 리뷰어 확인 필요 시 `firestore_admin.py` 의 해당 주석 참조.

**4. [관례 차이] payload nested 거부는 `ValueError` 가 아니라 `TypeError`**
- 플랜 Task 3 테스트 목록은 "payload nested ValueError" 라고 적혀 있으나, 기존 `_validate_dict_only_scalars` 는 `TypeError` 를 던진다([[firestore-nested-array-flat]] 관례, validator 본체 무수정 원칙).
- 기존 관례를 따라 `TypeError` 로 두고 테스트도 그에 맞췄다. validator 본체를 건드리는 쪽이 더 위험하다.

## Known Stubs

없음. 본 플랜 산출물은 전부 실 구현이다. 다른 8개 테스트 파일은 **의도된 골격**이며(담당 플랜 docstring + `_require()` importorskip 가드), 대상 모듈이 생기면 자동 활성화된다.

## 다음 플랜이 알아야 할 것

- **claim 성공 호출자는 `claim` 이 반환한 snapshot 만 써야 한다.** pre-claim job 재사용은 정적 검사 대상(31-09 grep).
- **`update_analysis_visual` 은 운영 reconciler 전용.** production worker 경로 호출 금지 — 31-09 acceptance grep 이 강제.
- **31-10 build gate 부등식 3개**가 `models.py` 주석에 근거와 함께 박제돼 있다: worker timeout < `VISUAL_CLAIM_LEASE_MS` < visibility / pipeline timeout + 보상구간 <= `VISUAL_INPUT_RESERVATION_TTL_MS` / dispatch timeout < `VISUAL_OBJECT_DELETE_LEASE_MS`.
- **31-04 TS lockstep 필드**: `correctedPoseStatus/Key/Joint/UpdatedAtMs`, `rotationStatus/VideoKey/UpdatedAtMs`. **URL 필드 없음.**

## 테스트

- `python3 -m pytest backend/tests/phase31 -q` → **105 passed**
- `python3 -m pytest backend/tests -q` → 41 failed / 2987 passed / 20 skipped
  - **41 failures 와 2건의 collection error 는 전부 pre-existing** (착수 전 baseline 동일: 41 failed / 2882 passed). 원인은 누락된 optional dep(`fixtures`, cv2 계열)이며 본 플랜 범위 밖이라 손대지 않았다. 순증은 +105 passed 뿐이다.

## Self-Check: PASSED
- 생성 파일 10개 전부 존재 확인
- 커밋 3개 존재 확인 (`5e2db75`, `4aba21a`, `bf4f141`)
- STATE.md / ROADMAP.md 미수정 확인
