# quick-260930-o0u 배포 기록 — 수강생 강사 코드 입력 (instructorLinks 규칙 · 라이브 probe · 시뮬 · OTA)

> **상태: Task 6 끝 — 규칙 게시 확인 · probe 22/22 · 뒤처리 0 · 시뮬 8장 · OTA 사전 점검. belle 판정(Task 7) 대기.**
> OTA 는 belle ○ 전에는 발행하지 않는다. 시험 공급자 TESTB 는 **지금 active True** 다(§D-0) — belle 답이 오면 OTA 전에 먼저 끈다.

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

## D-0. 시험 공급자 TESTB 되살림 (시뮬 시험용 — 끌 때까지 열려 있는 창)

BELLE 대신 TESTB("테스트 공급자", 공급자 uid `UmH3…`)로 시험했다(오케스트레이터 지시 — 이름 있는 코드라 '이름 강사님' 모양을 볼 수 있다).

관측:
- 되살리기 전(08:52:00Z): `suppliers/UmH3…` active **False**, code TESTB, displayName '테스트 공급자' · `supplierCodes/TESTB` active **False** · instructorLinks 0건 [확인 Admin 읽기].
- `supplier_invite.py reactivate --uid UmH3…` → `reactivate uid=UmH3… code=TESTB revokedInvite=-`, exit 0 — **창 시작 2026-09-30 08:52:07Z** [확인].
- 되살린 뒤 다시 읽기: suppliers active **True** · supplierCodes/TESTB active **True** [확인]. 초대 doc 은 건드리지 않는다(revoked 로 남음 — set_supplier_active 코드) [확인 코드].
- **아직 끄지 않았다** — belle 가 시뮬에서 직접 볼 수 있게. 끄는 명령: `FIREBASE_SA_PATH=<리포 SA json> backend/.venv/bin/python backend/scripts/supplier_invite.py deactivate --uid <UmH3 전체 uid>`. OTA 전에 반드시 먼저 한다.
- 캐시 주의: `reference-upload-url` Lambda 는 공급자 판정을 컨테이너당 **60초** 캐시한다(`_SUPPLIER_CACHE_TTL_S = 60`, `_roster_cache`) [확인 코드 backend/functions/reference-upload-url/app.py:70·115]. 끈 뒤 최대 60초 동안 따뜻한 컨테이너는 UmH3 를 여전히 공급자로 볼 수 있다 [추정 — 코드 읽기, 실측 안 함]. 수강생 앱의 코드 조회는 Firestore 직접 get 이라 이 캐시와 무관하다 — 끄는 즉시 'TESTB' 는 "없는 코드" 가 된다 [확인 코드 — lookupInstructorCode 가 supplierCodes get 1회].

## D. 시뮬레이터 (Task 6 A)

관측:
- 기기: iPhone 16 Pro **iOS 18.6** (`873D7CB3-…`), Debug dev client(08-31 19:28 빌드, main.jsbundle 없음) + Metro `127.0.0.1:8081` [확인].
  - 처음엔 iOS 26.5 기기(`A20B95BE-…`)를 띄웠으나 그 앱은 번들 내장형(09-10 빌드, main.jsbundle 있음)이라 Metro 를 안 탔다(Metro 로그에 번들 요청 0) → Debug 빌드가 깔린 18.6 기기로 옮겼다 [확인].
  - 08-31 Debug 빌드 뒤 네이티브 변경 = `react-native-web` 추가(웹 전용)와 app.json `web.output`·version 뿐이다 [확인 git diff 3bdb66a7..HEAD app/package.json app/app.json] → 이 빌드로 현재 JS 를 돌려도 네이티브 모듈 불일치는 없다 [추정].
- 번들 신선도: Metro 로그 `iOS Bundled 20083ms … (1474 modules)` 뒤 01 에 새 행 문구 '입력하기' 가 보였다 [확인].
- 시뮬 게스트 uid = `k9fQ…wbm2`(기존 익명 사용자 — 분석 7회 기록 있음) [확인 화면·Admin].
- 시작 전 instructorLinks 0건 [확인 Admin, D-0 읽기].

스크린샷(`sim/`, 실행기가 한 장씩 열어 봤다):

| 파일 | 관측 |
|---|---|
| `01-row-empty.png` | 마이 탭. 로그인 카드 아래 '강사 코드' 카드 — 왼쪽 회색 라벨, 오른쪽 '입력하기' 브랜드 굵게 + 브랜드 쉐브론. 카드 아래 힌트 '수업에서 받은 코드를 넣으면 강사님과 연결돼요.' [확인] |
| `02-sheet-empty.png` | 행 누름 → 아래 시트: 그랩바 · '강사 코드 입력' · 설명 · 브랜드 테두리 입력칸(포커스) · 흐린 '확인'(AX enabled=false). **화면 키보드는 안 떴다**(아래 미확인) [확인] |
| `03-error-notfound.png` | 'zzzz' 입력 → 확인 → 입력칸 테두리 틸 · 아래 틸 글자 '없는 코드예요. 강사님께 받은 코드를 다시 확인해 주세요.' [확인]. 입력칸에는 'ZZzz' 로 보인다(아래 관측 2) |
| `04-confirm-testb.png` | 칸을 비우고(비우는 순간 오류 사라짐 · '확인' 다시 흐림 — AX 로 확인) ' testb ' → 확인 → 같은 시트가 강사 확인으로: 분홍 원 + 사람 아이콘 · '테스트 공급자 강사님' · '코드 TESTB' · 회색 면 '연결은 한 번만 할 수 있어요. 나중에 바꾸려면 cs@sunity.ai 로 알려 주세요.' · [연결하기] · 밑줄 '취소' [확인] — 소문자·앞뒤 공백 정규화됨 |
| `05-cancel-back.png` | 취소 → 입력 단계, 값 ' testb ' 그대로, '확인' 활성 [확인] |
| `06-toast.png` | 다시 확인 → 연결하기 → 시트 닫힘 · 탭바 위 검은 토스트 '테스트 공급자 강사님과 연결됐어요' · 행이 이미 연결됨으로 바뀜 [확인] |
| `07-row-linked.png` | 토스트 사라진 뒤: 행 오른쪽 두 줄 '테스트 공급자 강사님'(굵게) / 'TESTB'(작은 회색) · 쉐브론 없음 · 힌트 '바꾸려면 cs@sunity.ai 로 알려 주세요.' 행을 눌러도 시트가 안 열림(AX 에 시트 요소 0) [확인] |
| `08-relaunch-linked.png` | 앱 terminate → 재실행 → 인트로 → 게스트로 시작하기 → 마이: 연결됨 행 그대로 [확인] |

Admin 확인(연결 직후):
- instructorLinks **1건**, doc id = 시뮬 uid `k9fQ…wbm2` [확인].
- 필드 = code · displayName · linkedAt · supplierUid **넷뿐**(크레딧 필드 없음) · code `TESTB` · supplierUid `UmH3…` · displayName '테스트 공급자' · linkedAt `2026-09-30 09:07:03.398Z`(서버 시각 — 연결하기 누른 직후 셸 시각 09:07:05Z) [확인].

그 밖 관측:
1. 분석 탭(38-02 이후 바뀐 analyze.tsx 가 같이 실리므로)도 한 번 열어 렌더 확인 — '어떻게 분석할까요?' · 전문가와 비교 · 내 자세 분석 카드 정상 [확인]. 영상 고르기·업로드는 안 눌렀다 [미확인].
2. idb 로 친 소문자는 입력칸에 소문자로 남는다('ZZzz', 'testb'). `autoCapitalize='characters'` 는 화면 키보드에만 작동한다 [확인 화면 / 원인은 추정]. 조회는 정규화로 대문자가 되므로 결과는 맞다 [확인 04].
3. 01 의 힌트 글자가 바로 위 로그인 힌트보다 크다(15 대 로그인 힌트의 작은 글자). 명세(38-DESIGN-v2 §W2) 값 15 그대로 옮긴 것이다 [확인 코드 text.auxFaint]. 보기에 어색한지는 belle 판정.

시뮬에서 재현 못 한 것 [미확인]:
- **화면 키보드가 뜬 상태의 모양** — 시뮬레이터 설정(하드웨어 키보드 끔, 소프트웨어 키보드 토글, 기기 재부팅)을 다 해도 이 시뮬에선 키보드가 뜨지 않았다. 그래서 "키보드가 입력칸·확인 버튼을 가리지 않는다"(KeyboardAvoidingView)는 **확인 못 했다**. belle 폰에서 봐야 한다.
- 본인 코드 오류('본인 코드는 넣을 수 없어요.') — 시뮬 uid 는 공급자가 아니다. probe 4행(규칙) + reducer 테스트가 덮는다.
- 네트워크 오류 문구 — 오프라인 전환 수단 없음. reducer 테스트가 덮는다.
- reduced motion 모습.

뒷정리 메모: 시뮬레이터 키보드 설정 원본은 scratchpad `simprefs.backup.plist`(휘발) — 시뮬레이터 동작에만 영향, 앱·리포와 무관.

## E. OTA 사전 점검 (쓰기 0 — 발행 안 함)

관측:
- `eas whoami` = sunity3412 [확인].
- 가장 최근 스토어(TestFlight) iOS 빌드: profile **testflight-preview** · channel **preview** · appVersion 1.2.4 (build 40) · runtimeVersion **1.2.4** · gitCommit `d95f2885` · 2026-09-03T10:53Z [확인 eas build:list]. 그 앞 네 빌드도 전부 testflight-preview / preview [확인].
- 채널 `preview` → 브랜치 **`preview`** 하나(branchMappingLogic true) [확인 eas channel:view]. 메모리의 `--branch production` 은 이 빌드에 닿지 않는다 [확인 — production 채널은 다른 채널].
- app.json version 1.2.4 · runtimeVersion policy appVersion → 발행 runtime = 1.2.4 = TestFlight 빌드 runtime **일치** [확인]. (PLAN 은 "현재 1.1.0" 이라 적었으나 실물은 1.2.4 — PLAN 쪽이 낡았다.)
- 직전 preview 발행: group **`b59f97ae-3b1f-4b67-9819-7a5c8a592ed1`** · 2026-09-20T14:27Z · **ios 만** · runtime 1.2.4 · gitCommit `2b8b2d23` · 메시지 "09-10~09-20 누적: …" [확인 eas update:view]. 그 앞 두 개(`0dddb65f…`, `b9b151af…`)는 android+ios [확인].
- app/.env 의 EXPO_PUBLIC_* 7개 = eas.json testflight-preview env 7개와 **전부 같음** (production 도 같음) [확인 — 값은 적지 않음].
- 발행할 때 쓸 명령(아직 안 함): `cd app && npx eas update --branch preview --platform ios --message "quick-260930-o0u: 마이 탭 강사 코드 입력 (38-DESIGN-v2 W2)" --non-interactive`. 롤백: `npx eas update:republish --group b59f97ae-3b1f-4b67-9819-7a5c8a592ed1 --message "ROLLBACK: quick-260930-o0u"`.

**같이 나갈 앱 변경** — `git log 2b8b2d23..HEAD -- app/` 32커밋 [확인]. 수강생 앱 화면에 닿는 것만 추리면:

| 묶음 | 커밋 | 수강생 앱에서 바뀌는 것 |
|---|---|---|
| 이번 W2 | `6e4b2e1e` `5dc1789c` `aa78d126` | 마이 탭 강사 코드 입력(이 문서) |
| 38-02 영상 길이 | `88b75fde` (+테스트 `197e60e2`) | 영상 고를 때 3~90초 밖이면 바로 막고 tooShort/tooLong 문구, 고르기 최대 90초 (`analyze.tsx`, `pickerFailure.ts`, `videoDuration.ts`) |
| 38-02 촬영 문구 | `ab4cdf2a` | '측면 45°·2~3m·정면' → '기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)' (`analyze.tsx`, `analysis/loading.tsx`, `help.tsx`) |
| 38-02 마이 탭 | `fab5d4b7` | '강사 코드 · 미입력' 한 줄 — 이번 W2 가 그 자리를 대체했다 |
| 강사 질문 말투 | `3f9a88a3` | 보완운동 쪽 강사 질문 6줄 말투 '…강사님과 이 화면을 함께 확인해보세요' (`InjuryRiskSection.tsx`) |
| 공용 API 모듈 | `efd48193` `61c46a65` `eaef58f3` 등 | `api.ts` 오류 본문 해석 함수가 `parseErrorCode` → `parseErrorBody` 로 바뀜(공급자 기능과 공유) — 수강생 업로드 오류 경로도 이 함수를 탄다 [확인 diff / 실제 업로드 오류는 시뮬에서 안 눌러 봄 — 미확인]. `PickErrorDialog.tsx`·`videoMeta.ts` 도 38-10 에서 조금 바뀜 |
| 타입만 | `d8169bef` `0c39163a` `c83700d6` | `analysis.ts` 타입 추가 — 화면 변화 없음 [추정] |
| 공급자(웹) 페이지 | 38-03·04·10·11·13, quick eal·lfw | `app/src/app/supplier/*` 라우트·공급자 문구·색 토큰. 번들에는 들어가지만 수강생 탭에서 가는 길은 없다 [추정 — 라우트 파일이 번들에 포함되는 것은 expo-router 구조상 확인, "가는 길 없음"은 탭·버튼을 다 따라가 보진 않았다]. `socialAuth.web.ts` 는 웹 전용 파일 |

진단(재검증 대상): 직전 발행(09-20) 뒤 수강생 앱에 한 번도 폰으로 안 나간 38-02 변경(영상 길이 검사·촬영 문구)이 W2 와 함께 처음 나간다. 38-02 는 당시 시뮬 실물 2장을 찍었다고 커밋 메시지에 적혀 있다 [확인 fab5d4b7 메시지] — 폰에서 본 적은 없다 [미확인].
