# quick-260930-o0u 배포 기록 — 수강생 강사 코드 입력 (instructorLinks 규칙 · 라이브 probe · 시뮬 · OTA)

> **상태: Task 5 끝 — 규칙 게시(belle 콘솔) 확인 + 라이브 probe 22/22 + 뒤처리 0건.**
> Task 6(시뮬 · OTA 사전 점검)은 §D · §E 에 이어 적는다. OTA 는 belle ○ 전에는 발행하지 않는다.

- 실행: 2026-09-30, 실행자 = gsd-executor (opus). `AWS_PROFILE=sunity-motion`.
- 코드 기준: Task 1 `6e4b2e1e` · Task 2 `5dc1789c` · Task 3 `aa78d126`.
- uid 는 앞 4자 + `…`, 메일은 가려 적는다. probe 일회용 uid(`o0uprobe*`)는 이미 지운 가짜라 원문으로 둔다.

## A. 규칙 게시 전·후

관측:

| 항목 | 게시 전 | 게시 후 |
|---|---|---|
| 라이브 ruleset | `rulesets/18587bf6-155f-43ae-aded-fdafdd7eabda` (38-09 게시분, updateTime 2026-09-30T00:58:37Z) | `rulesets/01f0a341-595d-40ae-a058-2a678837f1ce` (updateTime **2026-09-30T08:48:45.567Z**) |
| 내용 sha256 앞 8자 | `b5b63131` (= `firestore-rules-before.rules`, 38-09 CHANGESET 의 게시본 sha 와 같음) | `f348cb61` (= 리포 `firestore.rules`, 101줄) |

- belle 가 2026-09-30 콘솔 규칙 탭에 리포 규칙(101줄, sha256 `f348cb61…`, 77행 `match /instructorLinks/{uid}`)을 붙여 넣고 게시했다 — belle 답 "게시까지 누름" [확인 belle].
- 게시 뒤 `deploy_firestore_rules.py --current --out <scratchpad>/rules-live-after.rules` → `diff firestore.rules <그 파일>` 출력 없음, 두 파일 sha256 앞 8자 모두 `f348cb61` [확인]. 라이브 = 리포 바이트 동일.
- 게시 전 원본 `firestore-rules-before.rules` 의 sha256 `b5b63131…` 이 38-09 CHANGESET 에 적힌 게시본 sha 와 같다 [확인] → 게시 전 ruleset 은 `18587bf6-…` 였다 [확인 — sha 일치로 추론, 게시 직전 ruleset 이름을 따로 뜨지는 않았다].
- `--test` · `--release` 는 부르지 않았다(SA 403, 38-09 선택지 B) [확인].

```
$ FIREBASE_SA_PATH=<리포 SA json> backend/.venv/bin/python backend/scripts/deploy_firestore_rules.py --current --out <scratchpad>/rules-live-after.rules
current release name=projects/sunity-ai-coach/releases/cloud.firestore rulesetName=projects/sunity-ai-coach/rulesets/01f0a341-595d-40ae-a058-2a678837f1ce updateTime=2026-09-30T08:48:45.567441Z files=1
saved …/rules-live-after.rules (4540 chars)
$ diff firestore.rules …/rules-live-after.rules   → 출력 없음, exit 0
```

**롤백**: Firebase 콘솔 → sunity-ai-coach → Firestore Database → 규칙 탭에
`.planning/quick/260930-o0u-student-instructor-code-input/firestore-rules-before.rules` 내용을 붙여 넣고 게시
(실행기가 `pbcopy < 그 파일` 로 클립보드에 넣어 준다). 롤백하면 앱의 강사 코드 입력은 조회 단계에서 permission-denied
→ '연결하지 못했어요' 문구로 떨어진다 [미확인 — 롤백을 실제로 해 보지는 않았다, 코드 경로상 lookupInstructorCode 가 denied 를 failed 로 바꾼다].

## B. 라이브 probe 22행

관측: `rulesprobe_o0u.py`(이 디렉터리). Admin SA custom token → `signInWithCustomToken`(uid `o0uprobeS` 공급자 ·
`o0uprobeA` 학생 · `o0uprobeB` 다른 학생, ID 토큰 미출력) → Firestore REST v1. 생성은 `documents:commit`
write 하나(`currentDocument.exists=false` + `linkedAt` 은 `setToServerValue: REQUEST_TIME`).
준비 doc(Admin): `supplierCodes/QZPRBA` {S, '시험강사', active true} · `supplierCodes/QZPRBX` {같음, active false} · `suppliers/o0uprobeS`.
시작 전 probe 경로 10개 존재 = 전부 False [확인]. 행 1~20 = PLAN, 21~22 = 오케스트레이터 추가.

| # | 요청 (클라이언트) | 기대 | 결과 |
|---|---|---|---|
| 1 | A get `supplierCodes/QZPRBA` | ALLOW | HTTP 200 |
| 2 | 무토큰 get `supplierCodes/QZPRBA` | DENY | HTTP 403 PERMISSION_DENIED |
| 3 | A list `supplierCodes` (pageSize=1) | DENY | HTTP 403 PERMISSION_DENIED |
| 4 | S create `instructorLinks/o0uprobeS` {QZPRBA, S, 시험강사} — 본인 코드 | DENY | HTTP 403 PERMISSION_DENIED |
| 5 | A create {QZNONE, …} — 없는 코드 | DENY | HTTP 403 PERMISSION_DENIED |
| 6 | A create {QZPRBX, …} — 비활성 코드 | DENY | HTTP 403 PERMISSION_DENIED |
| 7 | A create {QZPRBA, supplierUid=o0uprobeB, …} — supplierUid 위조 | DENY | HTTP 403 PERMISSION_DENIED |
| 8 | A create {QZPRBA, S, '가짜'} — displayName 위조 | DENY | HTTP 403 PERMISSION_DENIED |
| 9 | A create 정상 필드 + linkedAt 을 timestampValue 로 직접(변환 없음) | DENY | HTTP 403 PERMISSION_DENIED |
| 10 | A create `instructorLinks/o0uprobeB` — 남의 경로 | DENY | HTTP 403 PERMISSION_DENIED |
| 11 | A create 정상 | ALLOW | HTTP 200 |
| 12 | A 같은 doc commit(precondition 없음 = update) | DENY | HTTP 403 PERMISSION_DENIED |
| 13 | A DELETE `instructorLinks/o0uprobeA` | DENY | HTTP 403 PERMISSION_DENIED |
| 14 | A get `instructorLinks/o0uprobeA` | ALLOW | HTTP 200 — fields = code · displayName · linkedAt · supplierUid, linkedAt.timestampValue 있음 |
| 15 | B get `instructorLinks/o0uprobeA` | DENY | HTTP 403 PERMISSION_DENIED |
| 16 | A list `instructorLinks` | DENY | HTTP 403 PERMISSION_DENIED |
| 17 | S get `suppliers/o0uprobeS` | ALLOW | HTTP 200 |
| 18 | A get `suppliers/o0uprobeS` | DENY | HTTP 403 PERMISSION_DENIED |
| 19 | A create `users/o0uprobeA/analyses/probeo0u` + `selfCheckForReference:'x'` (38-09 회귀) | DENY | HTTP 403 PERMISSION_DENIED |
| 20 | A create `users/o0uprobeA/analyses/probeo0uok` {note} (본인 쓰기 회귀) | ALLOW | HTTP 200 |
| 21 | B create `instructorLinks/o0uprobeB` 정상 필드 + `credits:1` | DENY | HTTP 403 PERMISSION_DENIED |
| 22 | A PATCH `supplierCodes/QZPRBA` active=false | DENY | HTTP 403 PERMISSION_DENIED |

`RESULT 22/22 match; mismatched rows=[]`, 스크립트 exit 0 [확인].

진단(재검증 대상):
- 21행은 B 로 돌렸다 — A 는 11행 뒤 이미 연결 doc 이 있어 `credits` 가 아니라 "이미 있음" 때문에 막혀도 DENY 가 나오기 때문이다. B 에는 doc 이 없으므로 이 DENY 는 hasOnly(필드 넷) 때문이다 [추정 — 규칙은 어느 조건에서 막혔는지 알려 주지 않는다. 나머지 조건은 11행과 같은 값이라 hasOnly 외에 막을 조건이 없다].
- 4~10·12·13 도 같은 이유로 "어느 조건이 막았는지"는 응답에 없다. 행마다 한 값만 11행(정상)과 다르게 만들었으므로 그 값이 막은 것으로 본다 [추정].

## C. 뒤처리

관측(스크립트 finally):
- Admin delete: `instructorLinks/o0uprobeA`·`o0uprobeB`·`o0uprobeS` · `supplierCodes/QZPRBA`·`QZPRBX`·`QZNONE` · `suppliers/o0uprobeS` · `users/o0uprobeA/analyses/probeo0u`·`probeo0uok` · `users/o0uprobeA` [확인].
- 뒤처리 뒤 probe 경로 10개 존재 = 전부 False [확인].
- `instructorLinks` 컬렉션 문서 수 = 0 [확인].
- Firebase Auth `delete_user` — `o0uprobeS`·`o0uprobeA`·`o0uprobeB` 모두 성공, 이어서 `get_user` 로 셋 다 UserNotFound 재확인 [확인].
- Firestore 사용량(대략): 클라이언트 요청 22 · Admin 읽기 약 21 · 쓰기 3 · 삭제 10 — Spark 캡 무관 [확인 스크립트 코드 기준 셈].
