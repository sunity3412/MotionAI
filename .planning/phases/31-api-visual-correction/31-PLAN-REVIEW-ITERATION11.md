# Phase 31 계획 11차 리뷰 — ownership delete-fence closure 한정, 직접 수행

**리뷰 일자:** 2026-07-20  
**리뷰 기준 커밋:** `59f2fea` (`iteration10 targeted replan`)  
**리뷰 범위:** `visualInputObjects active|deleting` delete-fence 상태 머신과 §7의 6 barrier만  
**검토 파일:** `31-02-PLAN.md`, `31-09-PLAN.md`, `31-10-PLAN.md`, `31-VALIDATION.md`의 ownership 관련 계약·테스트  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 없이 직접 검토했다.  
**최종 판정:** **BLOCK / TARGETED OWNERSHIP REPLAN REQUIRED**

---

## 1. 범위 준수 선언

다음 축은 재검토하거나 BLOCK 근거로 사용하지 않았다.

- iteration 3~6 상태 머신/outbox/claim/dispatcher
- create acquisition, finalizer unconditional gate, cleanup_blocked 회복, dispatcher IAM/HeadObject
- 비-버저닝 VisualInputBucket 및 Never-versioned/Suspended 판정
- belle SETTLED: 즉시삭제 SLA 현행 유지, pair 단일 시도 손실 수용
- lifecycle, Firestore TTL policy, bucket name, alarm, 문구·명명·스타일

11차는 오직 아래 6 barrier의 실제 closure만 검토했다.

1. self-ref 소비
2. A-expired+B-live fence
3. deleting 중 acquire 차단
4. claim/delete 직후 crash 재claim
5. 전 종료경로 ref release
6. nested transaction 전부-또는-전무

BLOCK 판정은 아래에 적은 구체적인 실행 시간축 네 개만을 근거로 한다.

---

## 2. 6 barrier 판정 요약

| Barrier | 판정 | 근거 |
|---|---|---|
| self-ref 소비 | **해소** | `claim_key_for_delete`가 deleting_ref를 먼저 소비한 뒤 다른 ref를 판정 |
| A-expired+B-live | **부분 해소** | unexpired reservation ref는 보호. producer 직접 보상 delete와 expiring job ref가 fence를 우회 |
| deleting 중 acquire 차단 | **미해소** | 유효 lease 동안만 차단하고 expired deleting을 producer가 active로 회수 가능 |
| claim/delete 직후 crash 재claim | **부분 해소** | janitor 재claim은 정의됐지만 이전 claimant의 늦은 delete를 generation/lease로 차단하지 않음 |
| 전 종료경로 ref release | **미해소** | created=False 기존 진행 job 분기가 no-op으로 끝나 reservation ref가 남음 |
| nested tx 전부-또는-전무 | **해소** | reservation claim+두 object promote+job create의 read-all→write-all 및 commit-loss test 명시 |

따라서 6개 중 2개 해소, 2개 부분 해소, 2개 미해소다.

---

## 3. BLOCKER 반례

### B11-01 · expired `deleting`을 producer가 `active`로 회수하면 이전 janitor가 새 object를 삭제할 수 있다

**관련 계약**

- `31-02-PLAN.md:154`: `state=='deleting' AND deleteLeaseExpiresAt>now`일 때만 acquire 실패하고, **deleting lease가 만료되면 producer가 active로 회수해 acquire**한다.
- `31-02-PLAN.md:157-158`: janitor는 `claim_key_for_delete` 성공 뒤 외부 S3 delete를 수행한다. delete 직전 owner/generation/미만료 lease를 재검증하는 계약은 없다.
- 명시 불변식: deleting fence 동안 새 producer input은 janitor delete로부터 보호되어야 한다.

**깨지는 시간축**

1. `J1`이 K에 대해 `claim_key_for_delete(owner=J1)`를 성공시킨다. object doc은 `state=deleting, generation=7, deleteOwner=J1, deleteLeaseExpiresAt=T`다.
2. `J1`은 S3 delete 전 일시 정지된다. 아직 Lambda timeout 전일 수 있고 계획에는 `delete lease > dispatcher 최대 생존시간` 부등식이 없다.
3. 시각이 T를 지난다.
4. producer `P`가 `acquire_key_ownership(K)`를 호출한다. 현재 계약은 expired deleting을 producer가 회수하도록 허용하므로 `state=active`, ref=P가 되고 True를 반환한다.
5. `P`가 K를 PUT/reuse한다.
6. `J1`이 재개해 이미 받아둔 claim 성공 결과만 믿고 `DeleteObject(K)`를 호출한다.
7. P의 live input이 삭제된다.

**깨지는 불변식**

`deleting 중 acquire 차단`과 `A-expired+B-live 보존`이 모두 깨진다. generation 필드는 증가하지만 외부 delete 직전에 사용되지 않아 fencing token 역할을 하지 못한다.

**제가 처리한다면**

- producer `acquire_key_ownership`은 **lease 만료 여부와 무관하게 state=deleting이면 항상 False**로 만든다. expired deleting 회수는 janitor만 수행한다.
- `claim_key_for_delete`가 `{owner, generation, leaseExpiresAt}` token을 반환하게 하고 janitor는 delete 직전 같은 token+미만료 lease를 CAS 검증한다.
- `VISUAL_OBJECT_DELETE_LEASE_MS > VisualDispatchFunction Timeout×1000 + clock/network margin`을 build gate로 고정해 이전 claimant가 lease 만료 뒤 살아서 delete할 수 없게 한다.
- test는 `J1 claim → lease expiry → P acquire 시도=False → J2 reclaim/delete/close → 그 뒤 P acquire=True` 전체를 고정한다.

---

### B11-02 · producer 보상 삭제가 `claim_key_for_delete`를 거치지 않아 live B ref를 무시한다

**관련 계약**

- `31-10-PLAN.md:36`은 janitor만 delete claim 성공 후 외부 delete한다고 설명한다.
- 그러나 `31-10-PLAN.md:139`의 option-b 실패, terminal-replay, analysis_missing, reserve 예외 보상은 `created_keys`를 **직접 `delete_object`**한 뒤 release/close한다.
- 이 경로는 object doc의 다른 live ref나 state=deleting을 CAS하지 않는다.
- 명시 불변식: 동일 deterministic key의 모든 삭제는 live B가 있으면 차단돼야 한다.

**깨지는 시간축 — option-b 보상 예**

1. producer A와 B가 같은 src K와 training key를 expectedKeys로 갖는 별도 reservation을 만든다.
2. A가 K ownership ref A를 acquire하고 K PUT에 성공한다.
3. B가 K ownership ref B를 acquire하고 HEAD/hash 일치로 K를 reuse한다.
4. A의 두 번째 trainingSrc PUT이 실패한다.
5. A는 계획의 “첫 object 역순 delete 보상”에 따라 `DeleteObject(K)`를 직접 호출한다. `claim_key_for_delete(A)`를 호출하지 않으므로 live ref B를 보지 않는다.
6. B가 trainingSrc PUT과 reserve를 성공해 job ref로 승격한다.
7. B job의 src K는 이미 삭제돼 있다.

같은 반례는 `reserve 예외 → job 재read 부재` 직후 B가 acquire/reuse하고 A가 직접 보상 delete하는 순서로도 성립한다.

**깨지는 불변식**

`A-expired+B-live fence`가 janitor 경로에서만 성립하고 producer compensation 경로에서는 깨진다. ref release 자체는 되어도 S3 safety가 먼저 무너진다.

**제가 처리한다면**

- producer의 object 삭제도 기존 `claim_key_for_delete(deleting_ref=reservationId)`를 반드시 거치게 한다. 새 machinery는 필요 없다.
- claim 실패는 “다른 live owner가 K를 소유”한 정상 결과로 취급해 A ref를 release/close하되 K는 삭제하지 않는다.
- option-b, analysis_missing, reserve exception, terminal-replay 각각에 `A delete intent + B live ref → DeleteObject 0` barrier test를 추가한다.

---

### B11-03 · `created=False` 기존 진행 job 분기가 reservation ref를 release하지 않아 worker terminal gate를 막는다

**관련 계약**

- `31-10-PLAN.md:139`은 reserve 결과가 기존 진행 job이고 inputSealed=False면 `no-op`으로 종료한다.
- 같은 action의 “모든 종료 경로” release 목록과 `31-VALIDATION.md:240,261`에는 collision/put 실패/option-b/analysis_missing/reserve 예외만 있고, **concurrent reserve loser의 created=False 진행 job 분기**가 없다.
- worker terminal gate는 `S3 remainingObject==0 AND ownership liveRefs==0`이다(`31-09-PLAN.md:136`).
- 명시 불변식: producer 전 종료경로에서 reservation ref가 release되어야 한다.

**깨지는 시간축**

1. producer A와 B가 모두 job preflight 부재를 보고 같은 K에 reservation ref A/B를 acquire한다.
2. A가 먼저 `reserve_visual_job`을 성공시켜 reservation ref A를 job ref J로 승격한다.
3. B의 reserve는 `created=False`, existing job state=reserved/creating/polling, inputSealed=False를 반환한다.
4. B는 명시 action대로 no-op return한다. B ref release와 B reservation close는 실행되지 않는다.
5. job J가 postprocessing까지 진행해 K를 삭제하고 job ref J를 release한다.
6. object doc에는 B의 아직 미만료 reservation ref가 남는다.
7. worker는 ownership liveRefs가 0이 아니므로 cleanupVerified terminal gate를 통과하지 못하고 postprocessing에 남는다.

**깨지는 불변식**

`전 종료경로 ref release`가 깨지고, 정상 job이 concurrent reserve loser의 ref TTL이 끝날 때까지 terminal에 도달하지 못한다.

**제가 처리한다면**

- created=False 기존 job 분기에서 payload key/sourceHash가 일치하면 S3는 건드리지 않고 B reservation을 close하며 B ref를 즉시 release한다. job ref J가 소유권을 유지한다.
- key가 불일치해도 B가 만든/획득한 ref는 release+close하되 기존 job object는 삭제하지 않는다.
- `A reserve winner / B reserve loser / worker cleanup` barrier에서 B return 직후 refs가 `{jobRef}`만 남고, worker 뒤 0이 되는지 검증한다.

---

### B11-04 · job ref의 `expireAt` 의미가 없어 live nonterminal job을 orphan janitor가 삭제할 수 있다

**관련 계약**

- `31-02-PLAN.md:153`은 reservation과 job ref 모두 `{kind, generation, expireAt}`를 갖는다고 정의한다.
- `claim_key_for_delete`는 **미만료 live ref만** 세어 나머지가 0이면 deleting claim을 허용한다(`:157`).
- `_promote_key_ownership_to_job_tx`는 job ref의 expireAt 값, 갱신 규칙, nonterminal 동안 비만료 보장을 정의하지 않는다.
- orphan janitor는 reservation janitor의 “matching nonterminal unsealed job” predicate를 사용하지 않고 object ref fence만 사용한다(`31-09-PLAN.md:158`).
- 명시 불변식: nonterminal job의 input ref는 worker가 명시적으로 release하기 전까지 live여야 한다.

**깨지는 시간축**

1. producer B가 K reservation을 job J로 승격한다. job ref에는 schema상 expireAt=T가 기록된다.
2. 같은 deterministic K에 대한 기존 orphan O가 open/due 상태로 남아 있다.
3. vendor polling 또는 복구가 길어져 J는 T 이후에도 nonterminal/inputSealed=False다. ownership 계약에는 job 최대시간이나 ref heartbeat가 없다.
4. orphan janitor가 O를 claim하고 `claim_key_for_delete(K, deleting_ref=O)`를 호출한다.
5. helper는 job ref J를 expired로 보아 “미만료 live ref 0”으로 판정하고 deleting claim을 성공시킨다.
6. orphan janitor가 K를 삭제한다.
7. 아직 실행 중인 J의 input이 사라진다.

**깨지는 불변식**

`A-expired+B-live fence`에서 B가 reservation이 아니라 live job일 때 보호가 깨진다.

**제가 처리한다면**

- typed ref를 이미 도입했으므로 **reservation ref만 expireAt 판정**, job ref는 explicit worker/reconciler release 전까지 항상 live로 취급한다고 고정한다.
- `_promote_key_ownership_to_job_tx`는 reservation expiry를 job ref에 복사하지 않는다.
- orphan janitor test에 `expired reservation ref + nonterminal job ref + orphan due → claim_key_for_delete False, DeleteObject 0`을 추가한다.

---

## 4. 해소된 barrier 재확인

### self-ref 소비 — 해소

`claim_key_for_delete` transaction이 deleting_ref 자신을 refs에서 먼저 소비한 뒤 다른 live ref를 판정한다. A-only expired에서 자신의 ref 때문에 count가 영원히 1이 되는 10차 반례는 더 이상 성립하지 않는다.

### nested transaction 전부-또는-전무 — 해소

`reserve_visual_job`이 `_claim_reservation_for_job_tx(transaction, ...)`와 `_promote_key_ownership_to_job_tx(transaction, ...)`에 동일 transaction을 전달하고, job+reservation+두 object doc을 read-all→write-all로 처리한다고 명시한다. 두 key conflict/retry/commit response loss의 전부 이전/전부 승격 test도 있어 이 범위에서 깨지는 시간축을 만들지 못했다.

---

## 5. 최소 targeted 수정 범위

새 축이나 새 상태 머신을 제안하지 않는다. 현재 `active|deleting` 계약 안에서 다음 네 수정만 필요하다.

1. producer는 expired를 포함해 모든 `deleting`에서 acquire False. expired deleting은 janitor만 generation token으로 회수한다.
2. janitor delete는 claim token owner/generation/미만료 lease 검증을 거치고 delete lease를 dispatcher 최대 생존시간보다 길게 고정한다.
3. janitor뿐 아니라 producer 보상 delete도 `claim_key_for_delete`를 사용한다.
4. created=False 기존 job 분기도 reservation close/ref release하며, job ref는 explicit release 전까지 만료되지 않는다.

수정 대상은 ownership 계약이 있는 `31-02`, dispatcher/worker의 `31-09`, producer의 `31-10`, 6 barrier test의 `31-VALIDATION`뿐이다.

---

## 6. 12차 승인 조건

다음 네 반례를 정확히 뒤집는 test가 추가되면 승인할 수 있다.

1. `J1 deleting claim → lease expiry → P acquire=False → J2 reclaim → close → P acquire=True`, J1 late delete 0.
2. A producer compensation delete intent + B live reservation/job ref → A delete claim False, `DeleteObject(K)==0`.
3. A reserve winner + B created=False loser → B return 전에 B ref 0/closed, worker cleanup 뒤 전체 refs 0.
4. job ref는 시간이 지나도 nonterminal 동안 live: orphan due여도 delete claim False, worker explicit release 뒤에만 delete 가능.

기존 self-ref와 nested tx test는 유지한다.

---

## 7. 최종 판정

**BLOCK / TARGETED OWNERSHIP REPLAN REQUIRED**

이 판정은 “더 나은 설계” 선호가 아니라 현재 명시 계약이 허용하는 네 개의 구체적 interleaving에 근거한다. 네 반례 모두 11차의 유일한 검토 대상인 ownership 6 barrier 안에 있으며, 각각 deleting fence 또는 ref lifecycle 불변식을 직접 깨뜨린다.

SETTLED 제품 결정과 기존 해소 축은 재개하지 않았다. 수정 후 12차에서는 위 네 시간축만 재검증하고, 더 이상 깨지는 시간축이 없으면 APPROVE한다.
