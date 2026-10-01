---
phase: quick-261001-thx
plan: 01
subsystem: supplier-intake (공급자 등록 입구)
tags: [phase-38, supplier-link, registration, review, ops-cli]
requires: [38-13 공급자 웹 · w9l 등록 경로 · 8c237bd8 multiple_people 기록만]
provides:
  - registration_checks.diagnose_registration (진단만, 실패 사유 없음)
  - registrationStatus 'review' + 실패 코드 'rejected' (계약 3벌)
  - firestore_admin.set_registration_review · approve_reference_registration · reject_reference_registration
  - playback-url review 소유자 예외
  - 공급자 홈 '검수 중' 행 · 반려 사유 실패 패널
  - backend/scripts/review_reference_registrations.py (list/show/approve/reject)
affects: [38-14 Task 3 재시도 순서, Pod 등록 경로, playback-url Lambda, 공급자 웹 번들]
tech-stack:
  added: []
  patterns: [진단 전용 판정(ast 구조 잠금) · 사람 검수 상태 · 상태 검사형 idempotent writer]
key-files:
  created:
    - backend/scripts/review_reference_registrations.py
    - backend/tests/test_review_reference_registrations_script.py
    - .planning/quick/261001-thx-supplier-intake-phase1a-block-only-unana/261001-thx-DEPLOY.md
  modified:
    - backend/shared/python/sunity_shared/analysis/registration_checks.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/shared/python/sunity_shared/models.py
    - backend/functions/pipeline/app.py
    - backend/functions/playback-url/app.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/constants/supplierCopy.ts
    - app/src/lib/supplierRules.ts
    - app/src/lib/supplierFixtures.ts
    - app/src/app/supplier/index.tsx
    - 테스트 7개 (backend 5 · app 2)
decisions:
  - "등록 판정 = 분석 불가만 막는다 — 저신뢰·서 있는 시작·여러 명은 diagnose_registration 이 한 번에 진단으로 내리고 사유를 낼 코드 경로 자체를 지웠다 (belle 10-01 '하나씩 고치면 절대 안돼')"
  - "판정 통과 = review(isActive false) → 운영 CLI approve 뒤에만 active. set_registration_active 는 운영 호출자가 파이프라인 하나라 set_registration_review 로 대체"
  - "승인/반려 writer 는 job 가드 없이 상태 검사만, 누가/언제는 비공개 doc review 에만, 반복 실행 already_* 쓰기 0, 승인 뒤 내리기는 범위 밖(ValueError)"
  - "playback-url: review ∧ supplierUid == ID 토큰 uid 일 때만 isActive false 예외 — 수강생에게는 같은 404"
  - "review 행 = 진행 점(isInProgress), 상세 패널 없음"
metrics:
  duration: "약 40분 (21:1x~21:55 KST) [추정 — 시작 시각 미기록]"
  completed: 2026-10-01
  tasks: "3/3 (Task 3 체크포인트 → belle 승인 10-01 → 문구 다듬기 + 배포 (1)(2)(6) 완료)"
---

# Quick 261001-thx: 공급자 등록 입구 1단계-가 — 분석 불가만 막기 · 검수 대기 · 승인/반려 CLI Summary

등록 판정을 진단 전용(`diagnose_registration`)으로 바꿔 저신뢰·서 있는 시작·여러 명이 어떤 조합이어도 등록을 막지 않게 했고, 통과한 등록은 `review`(수강생 비노출)로 두며 운영 CLI 로 승인/반려한다. belle 승인 뒤 공급자 가이드를 확인 흐름에 맞추고 공급자 문구를 다듬었으며, layer :24 · playback-url · 공급자 웹을 배포했다(Pod 는 38-14 재개 때).

## 판정

- **코드: 완료** — Task 1·2 커밋·push 완료, 게이트 전부 통과 [확인].
- **라이브: 배포 완료(2026-10-01 22:13~22:15 KST)** — layer **:24** 게시 · playback-url `:24` + 새 코드 **Successful** · 공급자 웹 무효화 **`IBUCA5QK6UNO7SLDR7CVATU667`** [확인]. reference-upload-url(3) 건너뜀, pipeline · Pod · OTA 안 함 [확인 — 명령 안 씀]. 배포 뒤 확인 P0~P5 · 웹 문구 · CLI list 전부 기대대로 [확인 — DEPLOY.md R-4].
- **아직 안 본 것**: 대역 등록이 실제로 review 까지 가는지 · review 소유자 썸네일 200 — Pod 새 코드가 필요하다 **[미확인 — 38-14 Task 3 재시도]**.
- **belle(10-01) 결정 반영**: 배포 (1)(2)(6) 승인 · 가이드 문구 교체 · "저렴한 문장이나 어색한 문장도 한번 봐주고" → 아래 '문구 다듬기'. **오케스트레이터 확인 필요 용어 4건**은 그 절 끝.

## 커밋

| Task | 커밋 | 내용 |
|---|---|---|
| 1 | `79977722` | 진단 전용 판정 · review 상태 · set_registration_review · approve/reject writer · begin_self_check(review 허용) · 계약 3벌 · playback-url 소유자 예외 |
| 2 | `2989c191` | supplierCopy review/rejected · supplierRules(isInProgress · reason · failCopy) · 공급자 홈 배선 · 검수 CLI |
| 3 | — | DEPLOY.md 작성(커밋 안 함 — 문서 커밋은 오케스트레이터) · 체크포인트 → belle 승인 |
| 3+ | `656c9c99` | 가이드를 확인 흐름에 맞춤 + 공급자 문구 다듬기(rejected 문구는 models · analysis.ts · contract.md 3벌 같이) |
| 3+ | — | 배포 (1) layer :24 · (2) playback-url · (6) 웹 — DEPLOY.md '배포 기록' |

push: `git push origin main` → `6b9d98dc..2989c191` → `2989c191..656c9c99` [확인].

## 관측 (코드 사실 · 테스트 결과 — 다음 세션이 승계해도 된다)

### 게이트

| 게이트 | 결과 |
|---|---|
| backend 전체 `.venv/bin/python -m pytest tests -q` | **5833 passed, 20 skipped** [확인] (기준 5758 → **+75**) |
| app `npm run typecheck` | 0 오류 [확인] |
| app `node --test src/lib/*.test.ts src/constants/*.test.ts` | Task 2 뒤 **87/87** → 문구 다듬기 뒤 **88 tests, 88 pass, 0 fail** [확인] (기준 82 → +6: thx 규칙 5 + 문구 잠금 1) |
| backend 전체 (문구 다듬기 뒤, models.py rejected 문구 변경) | **5833 passed, 20 skipped** [확인] (수 무변경 — 기존 테스트의 기대 문자열만 바꿈) |
| app typecheck (문구 다듬기 뒤) | 0 [확인] |
| 웹 export (문구 다듬기 뒤) | 성공 — scratchpad `thx-web2` 확인 후 배포용 app/dist `entry-b1143791…js` [확인] |
| Task 1 verify 6파일 | 302 passed [확인] |
| CLI `--help` (FIREBASE_SA_PATH · AWS_PROFILE 해제) | exit 0 [확인] |
| 웹 번들 `CI=1 npx expo export --platform web` (scratchpad `thx-web`) | 성공, entry `entry-d28ff348…js`, 번들 안 '검수 중 · 확인 뒤 수강생에게 보여요' [확인] |
| Docker 스모크(새 layer + 새 playback-url) | `SMOKE_OK unauth=401` [확인] |

backend +75 내역(파일별 collect 수, 기준 커밋 `6b9d98dc` 임시 worktree 와 비교) [확인]:

| 파일 | 기준 → 지금 | 이유 |
|---|---|---|
| test_registration_checks.py | 53 → 51 (−2) | check_registration 판정 테스트 13개 → 진단 테스트 10개 + 구조 잠금 2개 + never-raises 1개(parametrize 7 → 7) |
| test_register_reference_pipeline.py | 44 → 47 (+3) | 실패 기대 3건 → review 3건 + 셋 동시 1건 + ast 잠금 1건, 재PUT 스킵을 review/active 2건으로 |
| test_firestore_reference_writers.py | 95 → 127 (+32) | set_registration_review(processing 요구 4상태 등) · approve/reject 상태표 · begin_self_check review · list review · 가드 writer 9 → 11 |
| test_registration_contract.py | 21 → 22 (+1) | rejected `{reason}` 자리 |
| test_playback_url_reference.py | 24 → 35 (+11) | review 소유자 200 · 타 uid 404 · 비review 비활성 404(4상태 × 2 asset) |
| test_review_reference_registrations_script.py | 0 → 30 (+30) | 신설 |

### 소비처 재대조 (착수 즉시, 지금 줄 번호)

- `models.py:826` `REGISTRATION_STATUS_REVIEW` · `:949` `REG_ERR_REJECTED` · 전이 표 주석 갱신 [확인].
- `firestore_admin.py:4621` `claim_registration` 화이트리스트 = registering/queued(`:4666-4667`) + lease 만료 processing — **review 는 claim 불가** [확인 코드, 무변경]. `:4484` `_REGISTRATION_TERMINAL` 에 review 추가(소비처 0) [확인 grep]. `:4774` `set_registration_review` · `:4979` `begin_self_check`(review ∨ active) · `:5121` approve · `:5169` reject · `:5258` list(review 통과) [확인].
- `set_registration_active` 의 다른 호출자 0 — 운영 호출자는 `pipeline/app.py` 하나였다 [확인 grep backend app/src docs] → 지웠다.
- `requeue_reference_registrations.py` 는 queued/processing/registering 만 조회 → review 무접촉 [확인 코드].
- `pipeline/app.py:332` `_handle_reference_upload` — registering 아니면 skip, `_register_reference` 를 직접 돌리지 않는다 [확인 코드 + 테스트 `[review]`]. `:10678` `diagnose_registration` · `:10761` `set_registration_review` [확인].
- `playback-url/app.py:351` `_visible_to` — `:387`(영상) · `:426`(썸네일) 두 가드가 쓴다 [확인]. 호출자 uid = `verify_request(event)` 값 [확인 코드].
- `app/src/lib/referenceMotions.ts:79` `if (raw.isActive === false) return null;` **무변경** [확인].
- `pipeline/app.py` · `runpod_inference/*.py` 의 isActive 읽기 0, `get_reference_motion` 가드 없음 — 플래너 grep 승계 [미확인 — 재grep 은 pipeline 쪽만 했다: `_register_reference`/`_trigger_self_check` 에 isActive 0 확인].
- GET /reference(`reference-api`)는 `list_reference_motions` 로 **모든** doc 을 돌려준다(필터 없음) — review 만의 새 노출이 아니라 registering/failed doc 과 같은 기존 동작이고, 앱은 이 엔드포인트를 부르지 않는다 [확인 grep app/src].

### 동작 (테스트로 잠근 것)

- 저신뢰(발목 conf 0.2) · 바닥 위반 · 사람 둘 · 셋 동시 → failed 0, `set_registration_review` 1회, `begin_self_check` 호출, 로그 `register-reference diagnostics ref_id=… person_ratio= low_conf= stand_unreadable= standing_start= n_stand=` [확인 테스트].
- NoHumanError → no_human · 0 프레임 → server_error · keypointReport None → server_error · too_large/too_short/too_long 그대로 [확인 테스트].
- `_register_reference` 와 registration_checks 의 코드 식별자에 `REG_ERR_LOW_CONFIDENCE` · `REG_ERR_NO_STANDING_START` · `REG_ERR_MULTIPLE_PEOPLE` 0 (ast) — 세 상수와 문구는 models 에 남음 [확인 테스트].
- review 쓰기 = isActive False 명시(doc 이 True 였어도) + 비공개 registrationDiagnostics 한 트랜잭션, read-after-write 0 [확인 FakeFirestore].
- CLI: ref-* · 형식 밖 id · 빈/마침표만/201자 사유 · 빈 --by → Firestore 호출 전 종료 2, --dry-run writer 0 · 커밋 0, 실제 writer 왕복에서 두 번째 approve = already_approved [확인 테스트].

## 진단 (승계 전에 재검증할 것)

- **"실영상 대역 등록이 이제 review 까지 간다"** — 38-14 의 두 실패(화분 multiple_people · 대각선 no_standing_start)는 진단으로 내려갔으니 통과할 것이다 [미확인 — 38-14 Task 3 재시도]. 다른 분석 불가(포즈 재료 없음 등)에 걸릴 가능성은 재보지 않았다.
- **"review 중 자기 재현성 selfScore 가 기록된다"** — 코드 경로상 막는 것은 `begin_self_check` 하나였고 그걸 열었다. 실제 Pod `_process` 에서 review 기준으로 mode1 이 끝까지 도는지는 [미확인 — 38-14].
- **no_floor_reference 경고**: 재료(발목·어깨) 신뢰도가 충분한데도 바닥을 못 세웠을 때만 남기게 좁혔다(저신뢰 재료로 인한 no_floor_reference 는 버그 신호가 아니라서). 옛 코드는 저신뢰를 먼저 실패시켜 같은 조건이었다 [확인 코드 비교] — 실영상에서 이 경고가 뜨는지는 [미확인].

## 38-14 재개 순서 변화

옛: 서 있는 시작 판정 수리 → 재업로드 → active → picker.
새: **DEPLOY (1)(2)(6) → Pod 새 코드(5) → 대역 재업로드 → review(공급자 홈 '검수 중') → `review_reference_registrations.py list` → `show` 사진 → belle OK → `approve` → picker → mode1.** 서 있는 시작 판정 수리 단계는 없어졌다(진단으로 내림). 기존 실패 doc `dc7812c6…` · `fc4a393d…` · TESTB 정리는 38-14 Task 4 그대로.

## Deviations from Plan

### Auto-fixed / 판단

1. **[Rule 2 - 테스트 가능성] `isInProgress` 를 supplierRules 로 뺐다** — 플랜 behavior 는 `rowTrailing(review) = 'progress'` 인데 rowTrailing 은 화면 파일(react import)에 있어 node --test 로 못 잡는다. 진행 판정을 순수 규칙 `isInProgress` 로 옮기고 rowTrailing 이 그걸 부르게 했다(파일 머리 규율 "화면 파일에 규칙을 다시 쓰지 않는다"). 커밋 `2989c191`.
2. **[판단] no_floor_reference 경고 조건** — 위 "진단" 3번. 커밋 `79977722`.
3. **[판단] CLI list 에 전체 refId 블록** — 플랜 열은 "refId 앞 8자" 인데 approve/reject 는 전체 id 가 필요하다. 표 아래에 `앞8자 = 전체id` 줄을 덧붙였다(접두사 해석 같은 추가 동작은 넣지 않았다). show 는 썸네일·영상·프레임 5줄 앞에 요약 1줄을 더 찍는다.
4. **[판단] 반려 writer 가 기계 실패(failed + 다른 코드) doc 에 ValueError** — 플랜 표는 "이미 rejected 로 failed → already_rejected" 만 정했다. 기계 실패 doc 을 already_rejected 로 위장하지 않게 비공개 `review.decision == rejected` 일 때만 already 로 봤다. approve 도 같은 규칙(비공개 review.decision == approved 인 active 만 already).
5. **[절차] CLI 는 테스트보다 스크립트를 먼저 썼다** — 백엔드 Task 1 과 앱 쪽은 RED 확인 뒤 구현했지만(백엔드 68 failed + 40 errors → 302 passed, node 실패 → 87 pass), CLI 는 구현 뒤 테스트를 붙였다.
6. **[환경] Docker Desktop 을 켰다** — DEPLOY (2) 스모크를 위해 `open -a Docker`(로컬). 배포 아님.

## 문구 다듬기 (belle 10-01 "저렴한 문장이나 어색한 문장도 한번 봐주고") — 커밋 `656c9c99`

규칙: 해요체 · 담백하고 정중하게(읽는 사람 = 선수·강사) · 느낌표·이모지·과장어 없음 · 한 문장에 한 뜻 · 오류는 원인 + 다음 행동 ·
공급자에게 보이는 말은 **'확인'** 하나(내부어 '검수'는 화면에 안 씀 — 기존 라벨에 '검수'가 없었고, 지시받은 가이드 문장이 '확인'을 썼다).
가이드(`guide.*`)는 `docs/supplier-guide.md` 와 글자 단위로 같이 바꿨다(테스트가 대조).

### A. 확인 흐름에 맞춘 내용 변경 (지시받은 것)

| 키 | 전 | 후 |
|---|---|---|
| guide.s3.items[3] | 서 있는 자세에서 시작했는지는 따로 묻지 않아요. 올린 영상에서 자동으로 확인하고, 서 있는 시작이 없으면 등록되지 않아요. | (삭제) |
| guide.s4.items[0] | 올리면 관절을 자동으로 읽어서 기준 동작이 돼요. 몇 분 걸려요. | 올리면 관절을 자동으로 읽은 뒤, 운영팀이 확인하고 기준 동작으로 올려요. 확인 전에는 수강생에게 보이지 않아요. |
| guide.s4.items[1] | 분석 서버가 꺼져 있으면 '대기 중'으로 있다가, 켜지면 이어서 처리돼요. | (그대로) |
| guide.s4.items[2] | 끝나면 '자기 영상 재분석 N점'이 보여요. 회원님 영상을 … 다시 찍는 게 좋아요. | 확인이 끝나면 앱의 기준 동작 목록에 올라가요. 다시 올려야 하면 이유를 함께 알려 드려요. **※ 지시문과 다름 — 아래 확인 필요 1** |
| guide.s4.items[3] | 재현성 점수는 동작이 맞는지의 점수가 아니에요. 동작 정확도는 시험 영상으로 따로 봐요. | (삭제) |
| guide.s4.tipHead | 등록이 안 되는 4가지 | 잘 찍는 팁 |
| guide.s4.tip | · 사람을 찾지 못함 → … / · 여러 사람이 나옴 → … / · 서 있는 시작이 없음 → … / · 일부 관절을 못 읽음 → … | · 전신이 보이게, 밝은 곳에서(사람을 찾지 못하면 등록되지 않아요) / · 한 사람만 나오게 / · 폴 전체와 전신이 들어오는 거리에서, 옷과 배경이 구분되게 |
| row.tip[2] (촬영 팁 카드) | · 5초~2분, 서 있는 자세에서 시작 | · 길이는 5초~2분 |
| form.sec1.items[3] (촬영 전 체크) | · 서 있는 자세에서 시작했어요. | (삭제) |
| form.sec1.confirm | 위 4가지를 확인했어요 | 위 3가지를 확인했어요 |
| form.sec4.pill[1] | 5초~2분 · 1GB 이하 · 서 있는 자세에서 시작 · 소리는 자동으로 지워요 | 5초~2분 · 1GB 이하 · 소리는 자동으로 지워요 |
| guide.s2.items[1] | 폴 옆에 서서 1초쯤 있다가 시작해요. 서 있는 순간이 발 높이를 재는 기준이 돼요. | 가능하면 폴 옆에 서서 1초쯤 있다가 시작해 주세요. 서 있는 순간이 발 높이를 재는 기준이 돼요. **※ 요구 → 권장으로만, 아래 확인 필요 2** |
| home.motionsSub | 올린 동작이 앱의 기준 동작 목록에 올라가요. | 올린 동작은 운영팀 확인 뒤 앱의 기준 동작 목록에 올라가요. |
| home.emptyBody | 올린 동작은 앱의 기준 동작 목록에 올라가요. 촬영 전 체크 4가지를 먼저 확인해요. | 올린 동작은 운영팀 확인 뒤 앱의 기준 동작 목록에 올라가요. 올리기 전에 촬영 전 체크 3가지를 확인해 주세요. |
| form.uploaded.toast | 동작을 올렸어요. 등록이 끝나면 목록에 표시돼요. | 동작을 올렸어요. 운영팀 확인이 끝나면 앱에 보여요. (행은 올리자마자 목록에 생기므로 옛 문장이 틀렸다) |
| row.status.review | 검수 중 · 확인 뒤 수강생에게 보여요 | 운영팀 확인 중 · 끝나면 수강생에게 보여요 |
| row.fail.rejected.title | 검수에서 반려됐어요 | 운영팀 확인에서 등록되지 않았어요 |
| row.fail.rejected.body | 사유: {reason}. 고쳐서 다시 올려 주세요. | 이유: {reason}. 고쳐서 다시 올려 주세요. |
| REGISTRATION_ERROR_MESSAGE.rejected (models.py · analysis.ts · contract.md §5) | 검수에서 반려됐어요. 사유: {reason}. 고쳐서 다시 올려 주세요. | 운영팀 확인에서 등록되지 않았어요. 이유: {reason}. 고쳐서 다시 올려 주세요. (조인 규칙 유지 · 배포 전이라 layer :24 에 새 글자로 들어갔다) |

`row.fail.no_standing_start` · `multiple_people` · `low_confidence` 는 2026-10-01 전 실패 doc 용으로 그대로 뒀다(서버가 더 내지 않는다). 테스트가 그 셋을 뺀 공급자 문구 전부에 '서 있는 자세에서 시작했' · '서 있는 시작이 없' · '검수' · '!' 가 없음을 잠근다.

### B. 문장 다듬기 (뜻 무변경)

| 키 | 전 | 후 | 이유 |
|---|---|---|---|
| common.copyFallback | 길게 눌러 복사하세요 | 길게 눌러 복사해 주세요 | 해요체 통일 |
| noAccess.body | 공급자 페이지는 Sunity 가 초대한 강사·선수만 쓸 수 있어요. 초대받으셨다면 초대받은 Google 계정으로 로그인해 주세요. | 공급자 페이지는 Sunity가 초대한 강사·선수만 쓸 수 있어요. 초대 메일을 받은 Google 계정으로 로그인해 주세요. | '초대받으셨다면 초대받은' 반복 · 띄어쓰기 |
| row.status.failed | 실패 · 눌러서 확인 | 등록 안 됨 · 눌러서 이유 보기 | '실패' 딱딱함 · 누르면 무엇이 나오는지 |
| row.self.okBody | 추출·저장이 일관돼요. | 관절 읽기와 저장이 일관돼요. | 기술어 '추출' |
| row.self.lowBody | 낮아요. 다시 찍어 주세요. | 점수가 낮아요. 관절을 잘못 읽었을 수 있으니 다시 찍어 주세요. | 주어 없는 단독 문장 · 원인 + 다음 행동 |
| row.tipHead | 촬영 TIP! | 촬영 팁 | 느낌표 · 영문 대문자 |
| form.sec2.name.helper | 동작 이름은 등록 정보로 보관해요. 채점은 지금은 정은지 기준과 같은 기본 비교 방식으로만 해요. 동작별 채점 규칙은 다음 단계에서 붙어요. | 동작 이름은 등록 정보로 보관해요. 지금은 정은지 선수 기준 영상과 같은 기본 비교 방식으로 채점해요. 동작별 채점 규칙은 다음 단계에서 더해요. | '채점은 지금은' 이중 조사 · '붙어요' 구어 · '정은지 기준' 호칭 |
| form.sec2.level.error | 레벨을 고르세요. | 레벨을 골라 주세요. | 해요체 |
| form.sec4.card.sub | 저장된 영상 업로드 mp4, mov 등 | 저장된 영상(mp4, mov) | 명사 나열 · '등' 은 사실과 다름(두 형식만 받는다) |
| form.sec4.previewHint | 미리보기에서 폴 전체와 몸 전체가 보이는지 확인하세요. | … 확인해 주세요. | 해요체 |
| form.presignFail | 잠깐 문제가 있었어요. 잠시 후 다시 시도해주세요. | 요청을 보내지 못했어요. 잠시 후 다시 시도해 주세요. | '잠깐 … 잠시' 반복 · 무엇이 안 됐는지 |
| form.uploadFail.body | 인터넷이 끊겼거나 시간이 지났어요. 다시 올려주세요. | 인터넷 연결이 끊겼거나 올리는 시간이 너무 오래 걸렸어요. 다시 올려 주세요. | '시간이 지났어요' 모호 |
| dialog.tooLarge.lines | 1GB 이하 영상만 업로드 할 수 있어요. / 영상을 잘라서 다시 시도해주세요. | 1GB 이하 영상만 올릴 수 있어요. / 영상을 잘라서 다시 시도해 주세요. | 용어 '올리기' 통일 · 띄어쓰기 |
| guide.s1.items[4] | 밝은 실내에서 찍어요. 창을 등지면 몸이 검게 나와서 못 읽어요. | … 몸이 검게 나와서 관절을 못 읽어요. | 목적어 빠짐 |
| guide.s1.items[5] | 화면에는 한 사람만 나와요. 뒤로 지나가는 사람도 없어야 해요. | 화면에는 한 사람만 나오게 해요. … | 사실 진술처럼 읽힘 → 안내 |
| guide.s3.items[0] | 동작 이름: 사전에 있는 동작을 고르거나 … 채점은 지금은 기본 비교 방식으로만 해요(동작별 규칙은 다음 단계). | 동작 이름: 목록에 있는 동작을 고르거나 새 이름을 적어요. 이름은 등록 정보로 보관해요. 지금은 기본 비교 방식으로 채점하고, 동작별 채점 규칙은 다음 단계에서 더해요. | '사전' 은 화면에 없는 말 · 괄호 메모체 |
| guide.s6.h | 내 코드를 수강생에게 알려주는 법 | 내 강사 코드를 수강생에게 알려 주는 법 | 화면 라벨 '내 강사 코드'(home.codeRow.label)와 맞춤 |
| guide.s6.items[0] | 페이지의 '내 코드'를 수업 때 불러 주세요. | 페이지 위쪽의 '내 강사 코드'를 수업 때 알려 주세요. | 화면에 없는 라벨 '내 코드' · 위치 안내 |

동의·권리(s5 · sec5) 문구: **바꾸지 않았다.** 다듬을 후보만 적는다(오케스트레이터/belle 판단) —
s5[0] "…사진(프레임)과 썸네일을 만드는 것만 허락받아요" (주어가 Sunity 인데 '허락받아요' 가 어색 — 후보: "Sunity가 쓸 수 있는 범위는 분석 기준 · 앱 표시 · 사진(프레임)과 썸네일 만들기예요").

Figma 원문을 바꾼 키(D-22 "Figma 문자열은 그대로" 예외 — 문구 규칙이 우선이라 판단): `row.tipHead`(1:482) · `row.self.okBody` · `row.self.lowBody`(282:506) · `form.sec4.card.sub`(1:407). Figma 쪽 갱신은 안 했다.
안 바꾼 Figma 원문(후보): `login.title` '시작해 볼까요?'(약간 가벼운 말투) · `dialog.format`(수강생 화면 pickerFailure.ts 와 글자 단위로 묶여 있다) · `row.tip[0]`/`form.sec4.pill[0]` '기준 영상처럼 찍으세요(…)'(D-15 결정 문장 — 하세요체지만 테스트로 잠긴 결정).
띄어쓰기 '올려주세요/올려 주세요' 섞임: 새로 쓰거나 고친 문장은 '~해 주세요'로 썼고, 계약 3벌에 묶인 실패 문구(too_short · too_long · too_large · server_error)는 reference-upload-url 400 문구와 같아야 해서 그대로 뒀다(둘 다 맞춤법상 허용).

### 오케스트레이터 확인 필요 (용어 · 내가 정하지 않은 것)

1. **guide.s4.items[2]** — 지시문 "확인이 끝나면 '새로 추가됨'으로 바뀌어요" 를 그대로 쓰지 않았다. 승인 뒤 행 문구는 자기 재현성 점수가 이미 있으면 '재현성 N점', 없으면 '새로 추가됨' 이다(review 중에도 자기 재현성이 돈다 — `supplierRules.rowStatusWord`) [확인 코드]. 그래서 "확인이 끝나면 앱의 기준 동작 목록에 올라가요" 로 썼다. 또 '다시 찍어야 하면' → '다시 올려야 하면'(반려 사유가 촬영 문제가 아닐 수도 있어서). 지시문 글자를 원하면 되돌린다.
2. **guide.s2.items[1]** — 서 있는 시작은 등록 조건이 아니게 됐지만, 서 있는 창이 발 높이 기준·썸네일 순간으로 여전히 분석에 쓰인다 [확인 코드 `_stand_frames` · `hold_height`]. 지우지 않고 '가능하면 … 시작해 주세요'(권장)로 남겼다.
3. **'회원님'** — 가이드 s5 · s6 이 공급자(선수·강사)를 '회원님'이라 부른다. 수강생 앱 말투라 어색할 수 있다(후보: 호칭 없이 쓰기 · '선수님'). 범위가 커서 안 바꿨다.
4. **review 상태 문구 '운영팀 확인 중'** — registering 문구 '올린 영상 확인 중'(기계 처리)과 '확인' 이 겹친다. 그래서 review 쪽에 '운영팀'을 붙여 갈랐다. registering 을 '영상 처리 중' 등으로 바꿀지는 판단 대기.

## 확인 필요 (belle / 다음 세션)

1. ~~공급자 가이드 문구가 사실과 다르다~~ → belle 승인 뒤 `656c9c99` 로 고쳤다(위 '문구 다듬기').
2. ~~DEPLOY.md 승인~~ → (1)(2)(6) 배포 완료, (3) 건너뜀. **(5) Pod 는 38-14 재개 때** — 그 전까지 라이브 등록은 옛 판정이다.
3. `runpod_inference/server.py:258` 주석 "이미 active 인 doc" — 이제 review 도 해당. 동작 무관, 손대지 않았다.

## Threat Flags

없음 — 새 표면은 플랜 threat register(T-thx-01~08) 안이다. playback-url 예외(T-thx-02)는 테스트로 타 uid 404 를 잠갔다.

## Known Stubs

없음.

## Self-Check: PASSED

- FOUND: backend/scripts/review_reference_registrations.py · backend/tests/test_review_reference_registrations_script.py · 261001-thx-DEPLOY.md [확인 ls]
- FOUND: 커밋 `79977722` · `2989c191` · `656c9c99` (origin/main 포함) [확인 git log]
- FOUND: 보존 폴더 `/Users/Shared/sunity-motion-rollback/thx/` (700) · layer :24 · playback-url Successful [확인 — DEPLOY.md R-0~R-2]
- STATE.md 는 갱신하지 않았다 — quick 작업이라 오케스트레이터가 문서 커밋과 함께 처리(지시). ROADMAP 무접촉.

## 보완(belle 답 3건) — 커밋 `e1a74f51`, 웹 무효화 `I417VO9JEK2NZQZXH2OHWZZEJ2`

belle 10-01: *"1. 회원님으로 일단 진행하자 2. 올리는거에 실패가 있으려나? 두개는 겹치느거 같은데 3. 승인을 했는데 내려야할 일이 뭐가 있을까? 아주 심플하게 만들면 돼"*

1. **'회원님' 유지** — 변경 없음.
2. **승인 전 한 문구** — registering · queued · processing · review 를 `row.status.checking` = '확인 중 · 끝나면 수강생에게 보여요' 하나로(진행 점 그대로) [확인 테스트]. 옛 키 registering · queued · processing · review 는 supplierCopy 에서 지웠다(테스트가 잠금). 가이드 §4 '대기 중' 줄 삭제(supplierCopy · docs/supplier-guide.md 같이). 백엔드 상태는 그대로 — 행 문구 매핑만.
   - 같이 고친 것 1줄: 서버 꺼짐 알약 `home.podDown[1]` '켜지면 대기 중인 동작을 이어서 처리해요.' → '켜지면 올린 동작을 이어서 처리해요.' — 행에서 '대기 중' 이 사라져 그 말이 가리킬 곳이 없어졌다.
3. **내리기 명령 하나** — `review_reference_registrations.py deactivate <refId> [--reason] [--by] [--dry-run]` + `firestore_admin.deactivate_reference_registration`.
   - active ∧ isActive True → isActive False(picker `referenceMotions.ts:79` 가 숨김) · 상태는 active 그대로 · 누가/언제/사유는 비공개 doc `deactivation` 에만 · 이미 내렸으면 already_inactive 쓰기 0 · ref-* 는 CLI 종료 2 + writer ValueError · active 아니면 ValueError(종료 1) [확인 테스트].
   - 계약: analysis.ts `ReferenceRegistrationPrivate.deactivation?` · contract.md §3 비공개 doc 줄 추가(테스트 대조).
   - **공급자 행 문구 판단**: 내린 doc 은 registrationStatus 가 active 그대로라 승인 뒤 문구('재현성 N점' / '새로 추가됨')가 그대로 보인다 — 새 공급자 문구를 만들지 않았다(가장 단순한 기존 매핑, 테스트로 잠금). 공급자 홈 썸네일은 playback-url 가드상 404(아이콘 자리)가 된다 [확인 코드 `_visible_to` — isActive false ∧ review 아님]. 공급자가 "내려졌다" 는 걸 화면으로 알 길은 없다 — 운영팀이 따로 알린다는 전제. **오케스트레이터 확인 필요.**
   - 되살리기 명령 없음(범위 밖). 내린 doc 에 approve 를 다시 부르면 비공개 review.decision 이 approved 라 'already_approved' 만 나오고 isActive 는 False 그대로다 [확인 코드] — 되살리려면 다시 올려 새 refId.
   - **layer 재게시 안 함** — 새 writer 의 호출자는 로컬 CLI 뿐(Lambda · Pod 호출 0 [확인 grep]), CLI 는 리포 코드를 직접 import. models.py 무변경. 상세 = DEPLOY.md '배포 기록 2'.

게이트 [확인]: backend 전체 **5855 passed, 20 skipped**(5833 → +22: writer 10 + 가드 parametrize 2 + CLI 10) · node **89/89**(88 → +1) · typecheck 0 · 웹 export 성공.
배포 [확인]: 웹만 — 보존 `/Users/Shared/sunity-motion-rollback/thx/web-before-2/`(60개, 700) → s3 sync → 무효화 `I417VO9JEK2NZQZXH2OHWZZEJ2` 완료 → `/supplier` 200 · entry `entry-394e74ae…` · 새 문구 '확인 중 · 끝나면 수강생에게 보여요' 1 · 옛 '올린 영상 확인 중' · '운영팀 확인 중' 0.
