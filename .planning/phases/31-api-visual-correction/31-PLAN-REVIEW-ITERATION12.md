# Phase 31 계획 12차 리뷰 — ownership delete-fence closure 한정, 직접 수행

**리뷰 일자:** 2026-07-20  
**리뷰 기준 커밋:** `12939b4` (`iteration11 targeted ownership replan`)  
**리뷰 범위:** `visualInputObjects active|deleting` delete-fence 상태 머신과 §7의 6 barrier만  
**검토 파일:** `31-02-PLAN.md`, `31-09-PLAN.md`, `31-10-PLAN.md`, `31-VALIDATION.md`의 ownership 관련 계약·테스트  
**외부 리뷰어:** 사용하지 않음. 외부 AI, cross-AI, 서브에이전트 없이 직접 검토했다.  
**최종 판정:** **APPROVE**

---

## 1. 범위 준수 선언

12차는 11차에서 제시한 네 개의 구체적 반례와 아래 6 barrier만 재검증했다.

1. self-ref 소비
2. A-expired+B-live fence
3. deleting 중 acquire 차단
4. claim/delete 직후 crash 재claim
5. 전 종료경로 ref release
6. nested transaction 전부-또는-전무

다음 축은 재검토하거나 판정 근거로 사용하지 않았다.

- iteration 3~6 상태 머신/outbox/claim/dispatcher
- create acquisition, finalizer unconditional gate, cleanup_blocked 회복, dispatcher IAM/HeadObject
- 비-버저닝 VisualInputBucket 및 Never-versioned/Suspended 판정
- belle SETTLED: 즉시삭제 SLA 현행 유지, pair 단일 시도 손실 수용
- lifecycle, Firestore TTL policy, bucket name, alarm, 문구·명명·스타일

새 축이나 새 machinery도 제안하지 않았다.

---

## 2. 11차 BLOCKER 시간축 재실행

### B11-01 · expired `deleting` 회수와 이전 claimant의 late delete — 차단됨

1. `J1`이 K를 claim해 `{owner=J1, generation=7, leaseExpiresAt=T}` token을 얻는다.
2. `J1`이 멈추고 T가 지난다.
3. producer `P`가 K를 acquire하려 해도 `state=deleting`이면 lease 만료와 무관하게 False다. P는 K를 PUT/reuse할 수 없다.
4. janitor `J2`만 expired deleting을 `generation=8`로 재claim한다.
5. `J1`의 generation 7 token은 `commit_key_delete`의 owner/generation/미만료 lease 검증에서 실패하므로 `DeleteObject`는 호출되지 않는다.
6. `J2`만 generation 8 token으로 delete/HEAD 404/close한 뒤 producer acquire가 가능하다.

따라서 이전 claimant가 새 producer input을 삭제하는 시간축이 성립하지 않는다. 또한 delete lease가 dispatcher 최대 생존시간과 clock/network margin보다 길어야 한다는 build gate가 late execution의 경계를 고정한다.

### B11-02 · producer 보상 delete가 live B ref를 우회 — 차단됨

1. producer A와 B가 같은 K를 참조한다.
2. A가 K를 생성하고 B가 K를 acquire/reuse한다.
3. A가 option-b 실패, terminal replay, `analysis_missing`, reserve 예외 중 하나로 보상 삭제 경로에 진입한다.
4. 새 계약상 producer direct delete는 금지되어 A는 반드시 `claim_key_for_delete(K, deleting_ref=A)`를 호출한다.
5. helper는 A의 self-ref를 소비한 뒤 live B ref를 발견해 claim을 None으로 반환한다.
6. A는 자기 ref만 release/close하고 `DeleteObject(K)`는 호출하지 않는다.

따라서 A의 종료 원인과 무관하게 B의 live input은 유지된다. 네 producer 종료 계열 모두 같은 fence를 사용하도록 계약과 검증 항목이 함께 고정됐다.

### B11-03 · `created=False` reserve loser의 ref 누수 — 차단됨

1. producer A와 B가 같은 K에 reservation ref를 acquire한다.
2. A가 reserve winner가 되어 A reservation ref를 job ref J로 승격한다.
3. B는 `created=False`와 기존 진행 job을 받는다.
4. B는 반환 전에 자기 reservation ref를 release하고 reservation을 close하며 S3 object는 삭제하지 않는다.
5. 이 시점의 유일한 ownership은 job ref J다.
6. worker 종료 cleanup이 J를 release하면 live refs는 0이 되어 terminal gate를 통과한다.

따라서 concurrent reserve loser가 정상 job의 종료를 TTL까지 지연시키는 시간축이 성립하지 않는다. `31-VALIDATION.md`의 winner/loser barrier가 B의 반환 전 release를 명시적으로 검증한다.

### B11-04 · job ref expiry로 orphan janitor가 nonterminal input 삭제 — 차단됨

1. reservation ref가 job ref J로 승격된다.
2. job ref에는 `expireAt`이 없으며 worker/reconciler의 명시적 release 전까지 항상 live다.
3. 기존 reservation ref가 만료되고 orphan이 due가 되어도 `claim_key_for_delete`는 job ref J를 live로 센다.
4. orphan janitor의 claim은 None이고 `DeleteObject(K)`는 호출되지 않는다.
5. worker/reconciler가 J를 명시적으로 release한 뒤에만 이후 janitor가 K를 claim할 수 있다.

따라서 긴 polling이나 복구 중에도 시간 경과만으로 job ownership이 사라지지 않는다.

---

## 3. 6 barrier 최종 판정

| Barrier | 판정 | closure 근거 |
|---|---|---|
| self-ref 소비 | **해소** | delete claimant의 ref를 먼저 소비한 뒤 나머지 live ref를 판정한다. |
| A-expired+B-live fence | **해소** | reservation은 expiry로, job ref는 explicit release로 live 여부를 정하며 janitor와 producer 보상 삭제가 모두 동일 claim fence를 통과한다. |
| deleting 중 acquire 차단 | **해소** | producer는 lease 만료와 무관하게 모든 `deleting`에서 acquire False이며 janitor만 expired deleting을 재claim한다. |
| claim/delete 직후 crash 재claim | **해소** | owner+generation+unexpired lease token의 delete 직전 검증과 janitor-only generation 재claim이 stale claimant를 차단한다. |
| 전 종료경로 ref release | **해소** | 성공, 실패, replay, 예외, `created=False`를 포함한 producer 종료경로와 worker/reconciler 종료경로가 자기 ref를 release/close한다. |
| nested transaction 전부-또는-전무 | **해소** | reservation claim, 두 object ref 승격, job create가 동일 transaction의 read-all→write-all이며 conflict/commit-loss 검증을 유지한다. |

---

## 4. 승인 근거와 실행 gate

11차의 네 반례를 수정된 계약에 대입했을 때 모두 명시된 guard에서 중단된다. 그 밖에도 제한된 6 barrier 안에서 명시 불변식을 깨는 구체적 interleaving을 만들지 못했다. 따라서 판정 규칙에 따라 승인한다.

구현 시 아래 `31-VALIDATION.md` barrier는 승인 조건의 실행 증거로 유지한다.

1. J1 generation 7 claim 뒤 lease expiry, producer acquire=False, J2 generation 8 재claim 성공, J1 late commit/delete=0.
2. producer A 보상 의도와 B live ref 공존 시 A claim=None, delete=0, A ref만 release.
3. A reserve winner와 B `created=False` loser에서 B 반환 전 B ref release/close, worker 종료 뒤 refs=0.
4. nonterminal job ref는 시간 경과로 만료되지 않고 orphan claim/delete=0, explicit release 뒤에만 claim 가능.
5. delete lease가 dispatcher timeout과 clock/network margin을 초과한다는 build gate.

이 문서는 계획 계약의 승인이며 구현 테스트를 대신하지 않는다. 위 검증이 구현 단계에서 통과해야 closure가 실행 증거까지 완성된다.

---

## 5. 최종 판정

**APPROVE**

- BLOCKER: 0
- 제한 범위 내 미해소 barrier: 0
- 11차 반례 재발: 0

Phase 31 계획은 현재 명시된 `active|deleting` delete-fence 계약으로 구현을 진행할 수 있다. 해소된 기존 축은 재개하지 않았고, 새 설계 축이나 machinery를 추가하지 않았다.
