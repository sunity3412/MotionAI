---
phase: quick-260930-lfw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/models.py
  - backend/shared/python/sunity_shared/auth.py
  - backend/shared/python/sunity_shared/responses.py
  - backend/shared/python/sunity_shared/supplier_invites.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/functions/reference-upload-url/app.py
  - backend/scripts/supplier_invite.py
  - backend/tests/test_supplier_invites.py
  - backend/tests/test_supplier_invite_script.py
  - backend/tests/test_reference_upload_url_handler.py
  - docs/contract.md
  - app/src/types/analysis.ts
  - app/src/lib/api.ts
  - app/src/lib/supplierRules.ts
  - app/src/lib/supplierRules.test.ts
  - app/src/lib/supplierFixtures.ts
  - app/src/constants/supplierCopy.ts
  - app/src/constants/supplierCopy.test.ts
  - app/src/components/SupplierUi.tsx
  - app/src/app/supplier/index.tsx
  - app/src/app/supplier/upload.tsx
  - .planning/quick/260930-lfw-supplier-email-invite/260930-lfw-DEPLOY.md
autonomous: false
requirements: [REQ-38-1, REQ-38-5]

must_haves:
  truths:
    - "초대(supplierInvites/{메일})가 pending 이고 만료 전인 Google 계정이 /supplier 에 처음 로그인하면, ID 를 주고받지 않고 곧바로 공급자 홈이 열린다(probe 한 번에 수락)"
    - "명단(suppliers/{uid} active, 또는 doc 이 없고 SSM supplier-uids ∪ BELLE_UID)에 있는 사람은 초대 상태와 무관하게 항상 홈으로 간다. suppliers doc 이 active=false 면 SSM 에 있어도 막힌다"
    - "명단에 없고 수락할 초대도 없으면(없음·만료·취소·메일 미인증) 403 not_invited 가 로그인 메일을 싣고 오고, 화면은 A-2 '초대받은 분만 쓸 수 있어요' 하나다(지금 로그인한 메일 + 다른 계정으로 로그인 + 카카오/메일 문의 행 2개)"
    - "deactivate 된 uid 는 예전에 수락한 초대가 있어도 다시 들어오지 못한다 — deactivate 가 같은 트랜잭션에서 그 uid 의 accepted 초대를 revoked 로 바꾸고, 멱등 수락 분기는 suppliers/{uid}.active 가 True 일 때만 통과한다. 되살리기는 reactivate --uid 로만 된다(수락했던 메일로 다시 초대하는 길은 없다)"
    - "공급자 홈에 '내 코드' 큰 카드와 '빌드' 라벨이 없고, 코드가 있으면 시트 맨 위에 '내 강사 코드 {CODE} [복사][크게 보기]' 한 줄이 있다. 크게 보기는 흰 전체 화면에 코드를 크게 보여 주고 X·ESC 로 닫힌다(투명도만 바뀜)"
    - "운영자는 backend/scripts/supplier_invite.py 로 초대를 만들고(create)·연장(extend)·취소(revoke)·조회(list)·SSM 이관(migrate-ssm)·권한 회수(deactivate)·되살리기(reactivate)할 수 있고, create 는 코드 규칙(A-Z·2-9, 4~8자, O·0·I·1·L 금지)과 중복을 막는다. 이 스크립트는 SSM 을 읽기만 한다"
    - "라이브: 무토큰 401, 초대 없는 검증 메일 403 not_invited(메일 포함), 초대 있는 검증 메일 200 + suppliers/supplierCodes 생성 + 초대 accepted, deactivate 뒤 403(초대 revoked), reactivate 뒤 200 — 일회용 계정으로 확인되고 뒤처리로 흔적 0"
    - "SSM supplier-uids 는 배포 때 v1(FDJr…:BELLE)로 되돌려지고(v2 값은 롤백 파일에 보존) 이관은 BELLE 1건뿐이다. belle 두 번째 계정(UmH3…)은 이관하지 않는다 — 폰에서 A-2 를 본 뒤 오케스트레이터가 그 메일로 TESTB 초대를 만들고, 새로고침에서 홈이 열리는지(진짜 Google 수락) 본다. 확인 뒤 그 uid 는 deactivate 되어 TESTB 가 막힌다. 본 계정(BELLE)은 홈 코드 줄·크게 보기를 본다"
  artifacts:
    - path: "backend/shared/python/sunity_shared/supplier_invites.py"
      provides: "순수 함수 — 메일 정규화·코드 검증(새 규칙)·초대 수락 가능 판정·명단 판정(doc 우선 → SSM ∪ BELLE_UID)·메일 가림"
      exports: ["normalize_invite_email", "validate_invite_code", "invite_acceptable", "roster_decision", "mask_email"]
    - path: "backend/shared/python/sunity_shared/firestore_admin.py"
      provides: "get_supplier · accept_supplier_invite(트랜잭션, 멱등 분기는 active True 만) · create/extend/revoke/list_supplier_invites · upsert_supplier · set_supplier_active(False = 수락 초대 revoked 같은 트랜잭션, True = reactivate)"
      contains: "def accept_supplier_invite"
    - path: "backend/functions/reference-upload-url/app.py"
      provides: "claims(uid·email·email_verified) → 명단 판정 → 초대 수락 → 403 not_invited(email) — probe·업로드 같은 판정"
      contains: "not_invited"
    - path: "backend/scripts/supplier_invite.py"
      provides: "운영 CLI create/extend/revoke/list/migrate-ssm/deactivate/reactivate"
      contains: "reactivate"
    - path: "backend/tests/test_supplier_invite_script.py"
      provides: "스크립트 main 테스트 — 코드 규칙 exit 2·안내 두 줄·deactivate/reactivate 위임·migrate-ssm 재실행 skip"
    - path: "app/src/app/supplier/index.tsx"
      provides: "A-2 v2 · 홈 강사 코드 줄 · 크게 보기 모달 · 빌드 라벨 제거"
      contains: "BigCodeModal"
    - path: "app/src/components/SupplierUi.tsx"
      provides: "CodeRow · BigCodeModal · ContactRow · AccountBox (CodeCard·IdBox 삭제)"
      exports: ["CodeRow", "BigCodeModal", "ContactRow", "AccountBox"]
    - path: ".planning/quick/260930-lfw-supplier-email-invite/260930-lfw-DEPLOY.md"
      provides: "Lambda·layer 배포 전후 값 · SSM v2→v1 되돌림(가림) · 롤백 명령 · 이관 결과(메일 가림) · 웹 재배포 sha · 라이브 확인 표 · 폰 확인 절(TESTB 초대·회수)"
  key_links:
    - from: "backend/functions/reference-upload-url/app.py"
      to: "firestore_admin.accept_supplier_invite"
      via: "명단 판정이 None + email_verified + 메일 있음일 때마다 호출(음성 캐시가 수락을 막지 않는다)"
      pattern: "accept_supplier_invite\\("
    - from: "backend/functions/reference-upload-url/app.py"
      to: "auth.verify_request_claims"
      via: "토큰 email·email_verified 를 읽는 유일한 입구"
      pattern: "verify_request_claims\\("
    - from: "backend/shared/python/sunity_shared/firestore_admin.py (set_supplier_active)"
      to: "supplierInvites/{email}"
      via: "active False 트랜잭션 안에서 acceptedUid == uid 인 accepted 초대를 revoked 로"
      pattern: "INVITE_STATUS_REVOKED"
    - from: "app/src/app/supplier/index.tsx"
      to: "ApiError.email"
      via: "403 not_invited → A-2 의 '지금 로그인한 계정' 메일"
      pattern: "\\.email"
    - from: "app/src/app/supplier/index.tsx"
      to: "SupplierProbeResponse.displayName"
      via: "크게 보기 제목 '{name} 강사님의 코드'"
      pattern: "displayName"
---

<objective>
W1 — 공급자 메일 초대. 명세 정본 = `.planning/phases/38-supplier-link/38-DESIGN-v2.md` §W1(Figma v2 값이 옮겨 적혀 있다. 실행기는 Figma 를 열지 않는다). 결정 근거 = `38-SCENARIOS.md` 맨 위 "리서치 반영판" + "belle 결정 (2026-09-30, 확정)". belle 2026-09-30 "오케이 일단 고".

바뀌는 것:
1. 서버 — `POST /reference/upload-url {probe:true}` 한 곳에서 메일 초대를 수락한다(`suppliers/{uid}` + `supplierCodes/{CODE}` 생성, 초대 accepted). SSM 명단은 하위 호환 합집합. 403 은 `not_invited`(로그인 메일 포함) 하나. 회수(deactivate)는 수락 초대까지 revoked 로 바꾸고, 되살리기는 reactivate 로만.
2. 공급자 페이지 — A-2 "초대받은 분만" v2, 홈 코드 카드 제거 → 강사 코드 한 줄 + [복사][크게 보기] + 크게 보기 모달, 빌드 라벨 제거.
3. 운영 스크립트 `supplier_invite.py`(create/extend/revoke/list/migrate-ssm/deactivate/reactivate).
4. 계약 3벌 동기(contract.md · models.py · analysis.ts).
5. 배포 — Lambda 코드+layer(38-09 zip 보존·롤백 절차) → SSM supplier-uids v1 되돌림(v2 보존) → 이관(BELLE 1건) → 웹 재배포(38-13 DEPLOY 재배포 절차) → 라이브 확인 → belle 폰 확인(두 번째 계정으로 진짜 Google 수락까지).

Purpose: 정은지 선수(38-14)에게 "링크 하나 + 이 Google 계정으로 로그인"만 보내면 되게 한다. 지금은 첫 로그인 뒤 uid 를 운영에 보내야 하는 닭-달걀 절차(A-2 옛판)가 있다.
Output: 서버·스크립트·앱 변경 + pytest/node 테스트 + 라이브 배포 + DEPLOY 기록.

태스크 모양: T1 서버 핵심 + 계약 3벌(한 커밋) · T2 운영 스크립트 · T3 공급자 페이지 · T4 배포 · T5 belle 폰 확인(체크포인트).

플래너 확정 사항(38-DESIGN-v2 "데이터(제안)" 를 코드와 대조한 결과 — 설계와 다른 곳은 이유를 적는다):
- (a) probe 200 응답은 **기존 모양을 넓힌다**: `{probe:true, uid, supplierCode, displayName}`. 설계 제안 `{status:'supplier', code, displayName}` 대신이다. 이유: 지금 배포된 웹 번들이 `supplierCode` 를 읽고, 403 분기는 상태코드로 한다(`supplierRules.mapPresignFailure`). 이렇게 하면 Lambda 를 먼저 올려도 웹 재배포 전까지 옛 번들이 깨지지 않는다.
- (b) 명단 판정 순서: `suppliers/{uid}` doc 이 **있으면 그 `active` 가 결정**한다(SSM·BELLE_UID 보다 우선). doc 이 없을 때만 SSM ∪ BELLE_UID. 이유: 설계의 "합집합"만으로는 `deactivate`(S9) 가 SSM 에 남은 uid 를 못 막는다.
- (c) 새 코드 규칙(`^[A-HJKMNP-Z2-9]{4,8}$`)은 **새로 만드는 초대에만** 건다. migrate-ssm 은 옛 규칙(`SUPPLIER_CODE_RE`)에 맞는 기존 코드를 그대로 옮긴다. 이유: 기존 `BELLE` 에 L 이 들어 있다. belle 코드를 바꾸는 것은 이 범위 밖이다.
- (d) 시각 필드는 프로젝트 관례대로 epoch ms 정수(`createdAt`·`expiresAt`·`acceptedAt`·`since`·`revokedAt`). reference doc 의 `createdAt` 과 같다.
- (e) Firestore 규칙은 **바꾸지 않는다**. W1 은 세 컬렉션을 서버(Admin SDK)만 읽고 쓴다. 지금 규칙의 맨 끝 `match /{document=**} { allow read, write: if false; }` 가 클라이언트 접근을 이미 막는다. `suppliers` 본인 읽기·`supplierCodes` 로그인 읽기는 W2 규칙 게시(belle 콘솔) 때 연다(38-DESIGN-v2 "순서" 2). 그래서 이 플랜에는 규칙 게시 체크포인트가 없다.
- (f) (오케스트레이터 결정 — 이전 판의 "UmH3 이관 뒤 deactivate" 를 대체) belle 두 번째 계정(uid `UmH3…`)은 **이관하지 않는다**. 배포 Task 4 E0 에서 SSM `/sunity/motion/supplier-uids` 를 v1 값(`FDJr…:BELLE`, `get-parameter-history` 버전 1)으로 되돌린 뒤 이관한다 → suppliers 는 BELLE 1건. v2 값(`FDJr…:BELLE, UmH3…`)은 DEPLOY.md 에 가려 적고, 정확한 롤백 명령은 리포 밖 `/Users/Shared/sunity-motion-rollback/lfw/` 파일에 둔다. 이 SSM 쓰기는 배포 절차의 한 번뿐이고 운영 스크립트는 SSM 을 쓰지 않는다. 그 결과 두 번째 계정은 명단 밖이라 폰에서 A-2 를 보고, 체크포인트(Task 5) 안에서 오케스트레이터가 그 메일로 `TESTB` 초대를 만들어 진짜 Google 계정 수락을 [확인] 대상으로 삼는다. 확인 뒤 그 uid 를 deactivate 해서 W2 에서 실제 수강생이 `TESTB` 를 쓰지 못하게 한다.
- (g) CFN·IAM 변경은 필요 없다. Firestore 쓰기는 Admin SA(SSM `firebase-sa`)로 하고, 이 함수는 이미 reference doc 을 쓴다. SSM 읽기 권한(`firebase-sa`·`supplier-uids`)도 이미 있다(`backend/template-38-09-deploy.yaml:203-206`). 따라서 38-09 의 "코드만" 절차(zip 보존 + 롤백 명령)를 쓴다. SSM 되돌림은 로컬 사용자 자격(AWS_PROFILE=sunity-motion)으로 하며 함수 역할과 무관하다.
- (h) (오케스트레이터 결정 — 체커 BLOCKER 1) 회수 의미: `set_supplier_active(uid, False)` 는 한 트랜잭션에서 suppliers active False · supplierCodes active False · 그 uid 가 수락한 초대(acceptedUid == uid, status accepted) → revoked 를 같이 쓴다. `accept_supplier_invite` 의 멱등 분기(초대 accepted 이고 acceptedUid == uid)는 `suppliers/{uid}.active is True` 일 때만 entry 를 돌려준다. suppliers/{uid} 가 active False 로 있으면 어떤 초대든 수락하지 않는다. 되살리기는 새 스크립트 명령 `reactivate --uid …`(suppliers active True + supplierCodes active True) 로만 한다. 한 번 수락된 메일(acceptedUid 가 있는 초대)에는 create 가 새 초대를 만들지 않는다.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@app/CLAUDE.md
@.planning/STATE.md
@.planning/phases/38-supplier-link/38-DESIGN-v2.md
@.planning/phases/38-supplier-link/38-SCENARIOS.md
@.planning/phases/38-supplier-link/38-DESIGN.md
@.planning/phases/38-supplier-link/38-09-SUMMARY.md
@.planning/phases/38-supplier-link/38-09-CHANGESET.md
@.planning/phases/38-supplier-link/38-13-DEPLOY.md
@.planning/quick/260930-eal-supplier-figma-design-align/260930-eal-SUMMARY.md
@backend/functions/reference-upload-url/app.py
@backend/shared/python/sunity_shared/auth.py
@backend/shared/python/sunity_shared/responses.py
@backend/tests/test_reference_upload_url_handler.py
@app/src/app/supplier/index.tsx
@.claude/skills/apple-design/SKILL.md

<interfaces>
지금 코드에서 뽑은 계약(탐색 없이 이것을 쓴다):

backend/shared/python/sunity_shared/auth.py
- verify_request(event) -> str   # uid. 내부에서 fb_auth.verify_id_token(token) 결과 dict 의 "uid" 만 쓴다. 이 dict 에 "email"·"email_verified" 클레임도 들어 있다.
- 리포에서 verify_request 를 부르는 함수는 reference-upload-url 말고 5개다: upload-url · playback-url · reference-api · reference-auto-register · visual-request(`grep -n verify_request backend/functions/*/app.py`). 배포 스택 template-38-09-deploy.yaml 에는 visual-request 가 없다.
- AuthError(message)

backend/shared/python/sunity_shared/responses.py
- ok(payload, status=200) / error(code, message, status=400) -> {"error": {"code", "message"}} / parse_json_body(event)

backend/shared/python/sunity_shared/models.py (:979-1007)
- SUPPLIER_CODE_RE = ^[A-Z0-9]{3,8}$  (옛 규칙 — SSM 파싱용, 그대로 둔다)
- SUPPLIER_UIDS_PARAM_DEFAULT = "/sunity/motion/supplier-uids"
- parse_supplier_uids(value) -> dict[uid, code|None]

backend/shared/python/sunity_shared/firestore_admin.py
- _db() :23 · _doc(path) :35 · _collection · _field_filter · _run_in_transaction(fn) :2938(fn(transaction) 를 transactional 로 실행. 중첩 transactional 금지) · _now_ms() · _snap_dict(snap)
- create_reference_registration(ref_id, *, supplier_uid, form, upload_key, upload_expires_at_ms, consent_at_ms, supplier_code=None) :4503
- 테스트 가짜: backend/tests/phase31/conftest.py `fake_firestore` — `_db`/`_doc`/`_collection`/`_run_in_transaction` 네 seam 을 바꾼다. 트랜잭션은 get/set/update/delete 만 된다(create 없음 → 존재 여부를 읽은 뒤 set 으로 쓴다). `run_contended(fn_a, fn_b)` (:326) 로 경합 재시도를 재현한다. 사용 예 = backend/tests/test_firestore_reference_writers.py:30-90, :365-380.

backend/functions/reference-upload-url/app.py
- 모듈 전역: _BELLE_UID, _SUPPLIER_UIDS_PARAM, _SUPPLIER_CACHE_TTL_S=60, _supplier_cache(:60), _load_supplier_map()(:63), _is_supplier(uid, map)(:86)
- 테스트는 app.verify_request 를 monkeypatch 한다(test_reference_upload_url_handler.py:107, :126, :377, :380) → 입구를 verify_request_claims 로 바꾸면 이 네 곳도 바뀐다.

app/src/lib/api.ts
- class ApiError(message, status, code) :30 · parseErrorCode(text) · authedJson · probeSupplier(): Promise<SupplierProbeResponse> :352

app/src/lib/supplierRules.ts
- type PresignFailureKind = 'sessionExpired' | 'forbidden' | 'offline' | 'presignFail' :69 · mapPresignFailure({status, code}) :~262(403 → 'forbidden') · presignFailureMessage(kind) :~276
- 소비처: app/src/app/supplier/index.tsx:185 · upload.tsx:176, :342

app/src/lib/supplierFixtures.ts :239-247 apiFailures
- 지금 `{ status: 403, code: 'forbidden', expect: 'forbidden' }` 한 행이 있다(:242). supplierRules.test.ts :228-229 가 이 표를 돌린다(테스트 이름에 'forbidden' 문구).

app/src/types/analysis.ts :1391
- interface SupplierProbeResponse { probe: true; uid: string; supplierCode: string | null }

app/src/components/SupplierUi.tsx
- space{xxs 2, xs 4, s6 6, sm 8, s10 10, row 12, s13 13, s14 14, md 16, screen 20, lg 24, xl 32, s40 40, xxl 48} · text{label, labelBold, title, heading, display, caption, mid, sub, center, aux(15 textMid), auxFaint, body15, body15Bold, caption13(13 textMid), num13, chipText, code, step}
- R{button 13, card 15, ...} · H{cta 54, ...} · s.pressed {opacity 0.7}
- 삭제 대상: CodeCard :542, IdBox :511(+ 그 스타일, H.photo 등 소비처가 0 이 되는 값)
- 있는 것: PrimaryCta · OutlineButton · Toast · Card · TextLink · BrandMark · AlertIcon(PickErrorDialog) · SocialIcon(id 'kakao' 글리프, components/SocialIcon.tsx)

theme 토큰(colors.ts): divider #D9D9D9 · softBg #F5F5F5 · textMid #5A5A5A · inputBorder/textDisabled #B1B6BE · resultTextSub #767676 · brand #FF4B33 · infoTeal #2C7C8C · kakao {bg #FEE500, text #0C0C0C}(이미 있다 — 카카오 노랑 토큰을 새로 만들지 않는다)

react-native-web Modal: node_modules/react-native-web/dist/exports/Modal/ModalContent.js 가 Escape 키에서 onRequestClose 를 부른다(grep 'Escape' 확인됨) → ESC 닫힘은 onRequestClose 로 된다.

배포 값(38-09 · 38-13 기록):
- 함수 `sunity-motion-pilot-reference-upload-url`, 현재 layer `arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared:21`, AWS_PROFILE=sunity-motion
- 38-09 뒤 backend/shared · backend/functions 커밋 0(`git log d50cf39f..HEAD`) → layer :21 의 sunity_shared 는 이 플랜 전 HEAD 와 같아야 한다(Task 4 에서 파일 sha 로 확인).
- 웹: 버킷 `sunity-motion-pilot-supplier-web`, distribution `E16SR4IPFYH46Q`, 링크 `https://d2ivnoigym2xlu.cloudfront.net/supplier`
- Admin SA 파일: 리포 루트 `sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json`(backend/scripts/snapshot_reference_baseline.py:47 관례 — FIREBASE_SA_PATH 로 넘긴다)
- SSM: `/sunity/motion/supplier-uids` 현재 = v2 `FDJr…:BELLE, UmH3…` · v1 = `FDJr…:BELLE`(Task 4 E0 에서 v1 로 되돌린다 — 결정 (f)). `/sunity/motion/belle-uid` = FDJr…(E0 dry-run 에서 확인).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 서버 핵심 — 초대 데이터·수락·회수·not_invited + 계약 3벌 (pytest 먼저)</name>
  <files>backend/shared/python/sunity_shared/supplier_invites.py, backend/shared/python/sunity_shared/models.py, backend/shared/python/sunity_shared/auth.py, backend/shared/python/sunity_shared/responses.py, backend/shared/python/sunity_shared/firestore_admin.py, backend/functions/reference-upload-url/app.py, backend/tests/test_supplier_invites.py, backend/tests/test_reference_upload_url_handler.py, docs/contract.md, app/src/types/analysis.ts</files>
  <behavior>
    순수(supplier_invites.py):
    - normalize_invite_email('  Eun.Ji@Gmail.com ') == 'eun.ji@gmail.com'. '@' 없음·공백 포함·'/' 포함·빈 값 → ValueError(doc id 로 쓰므로 '/' 는 반드시 거부).
    - validate_invite_code 는 정규화(공백 제거 + 대문자) 뒤 규칙을 검사한다: ' mx kr ' → 'MXKR' · 'QZ2TEST' → 'QZ2TEST' · 'eunji' → ValueError(I 포함) · 'ABC'(3자)·'ABCDEFGHJ'(9자)·'AB0C'·'AB1C'·'ABOC'·'ABLC'·'ABIC' → ValueError.
    - invite_acceptable({'status':'pending','expiresAt':T+1}, now_ms=T) is True. expiresAt == now → False(만료 경계 포함). status 'accepted'/'revoked' → False. 필드 누락·타입 이상 → False(던지지 않는다).
    - roster_decision(doc, ssm_map, belle_uid, uid): doc={'active':True,'code':'MXKR','displayName':'정은지'} → SupplierEntry(code='MXKR', display_name='정은지'). doc={'active':False} + uid 가 ssm_map 에 있음 → None(doc 우선). doc None + ssm_map {uid:'BELLE'} → SupplierEntry('BELLE', None). doc None + uid == belle_uid(비지 않음) → SupplierEntry(None, None). doc None + 없음 → None. belle_uid 가 '' 이면 통과 재료가 아니다.
    - mask_email('catharina@gmail.com') == 'c***@gmail.com'. 이상한 값 → '***'.
    Firestore(fake_firestore):
    - create_supplier_invite(email, code, display_name, days=14, now_ms=T) → supplierInvites/{email} = {email, code, displayName, createdAt:T, expiresAt:T+14일ms, status:'pending', acceptedUid:None, acceptedAt:None}. supplierCodes/{code} 가 이미 있으면 ValueError. 다른 메일의 pending 초대가 같은 코드를 쓰면 ValueError. 같은 메일의 초대가 pending 이면 ValueError('extend 를 쓰세요'). 같은 메일의 초대에 acceptedUid 가 있으면(accepted 든, deactivate 로 revoked 됐든) ValueError('이미 수락된 메일 — 되살리기는 reactivate')(결정 (h): 재초대 길 없음). acceptedUid 없이 revoked 된 초대(수락 전 취소)는 새 pending 으로 덮어쓸 수 있다.
    - extend_supplier_invite(email, days, now_ms): pending → expiresAt = now + days·86400000, 다른 필드 무변화. days > SUPPLIER_INVITE_MAX_DAYS 또는 < 1 → ValueError. accepted·revoked·없음 → ValueError, 쓰기 0.
    - revoke_supplier_invite(email): pending → status 'revoked'(acceptedUid None 유지). accepted → ValueError('권한 회수는 deactivate'), 쓰기 0. 없음 → ValueError.
    - upsert_supplier(uid, *, email, code, display_name, active, since_ms): 없으면 suppliers/{uid} 와(코드가 있으면) supplierCodes/{code} 를 만들고 True. 이미 있으면 둘 다 한 글자도 바꾸지 않고 False(migrate-ssm 재실행 안전 — 두 번 불러 doc 내용·개수 동일 단언).
    - accept_supplier_invite(uid, email, now_ms): pending·만료 전 + suppliers/{uid} 없음 → suppliers/{uid}={email, code, displayName, active:True, since:now}, supplierCodes/{code}={supplierUid:uid, displayName, active:True}, 초대 {status:'accepted', acceptedUid:uid, acceptedAt:now}, 반환 SupplierEntry. 초대 없음/만료/revoked → None, 쓰기 0. 이미 accepted 이고 acceptedUid == uid 이고 suppliers/{uid}.active is True → 같은 SupplierEntry(멱등, 쓰기 0). **accepted 초대 + suppliers/{uid} active False → None, 쓰기 0**(BLOCKER 1). accepted 초대 + suppliers/{uid} 없음 → None, 쓰기 0. accepted 인데 다른 uid → None. suppliers/{uid} 가 active False 로 있는 uid 가 새 pending 초대를 수락하려 함 → None, 쓰기 0(되살리기는 reactivate 로만 — 결정 (h)). supplierCodes/{code} 가 다른 uid 것 → SupplierCodeConflict 예외, 쓰기 0. 경합 2 트랜잭션(같은 uid, run_contended) → 둘 다 같은 entry, suppliers doc 하나.
    - set_supplier_active(uid, False): 한 트랜잭션. doc 이 없으면 {active: False} 로 만든다(SSM uid 를 막기 위해). code 가 있으면 supplierCodes/{code}.active 도 False. doc 에 email 이 있고 supplierInvites/{email} 이 status accepted · acceptedUid == uid 이면 {status:'revoked', revokedAt:now} 로 바꾼다(acceptedUid·acceptedAt 은 이력으로 남긴다). 반환 {code, revokedInvite: 가린 메일|None}. **테스트: 초대 수락 → deactivate → 초대 status revoked · accept_supplier_invite 가 None · 쓰기 0.**
    - set_supplier_active(uid, True)(= reactivate): suppliers/{uid} 가 없으면 ValueError(되살릴 대상 없음). 있으면 active True, code 가 있으면 supplierCodes/{code}.active True. 초대 doc 은 건드리지 않는다(revoked 로 남는다). 테스트: deactivate → reactivate → get_supplier 가 active True, roster_decision 이 entry.
    핸들러(test_reference_upload_url_handler.py — verify_request_claims 를 monkeypatch):
    - suppliers doc active → probe 200 {probe:True, uid, supplierCode, displayName}.
    - doc 없음 + SSM 'uid:BELLE' → 200 supplierCode 'BELLE', displayName None.
    - doc active False + SSM 에 uid → 403 not_invited.
    - 명단 밖 + email_verified True + accept 가 entry 반환 → 200. 곧바로 두 번째 호출은 get_supplier 를 다시 부르지 않고 200(수락 직후 캐시 갱신).
    - 음성 캐시 경로(W3): 첫 호출 get_supplier None · accept None → 403(캐시에 None 이 들어감) → accept 가 entry 를 돌려주도록 바꿈(초대가 생김) → TTL 을 기다리지 않은 두 번째 호출 200. get_supplier 호출 1회, accept 호출 2회.
    - 회수·되살리기 끝-끝(BLOCKER 1, fake_firestore 위에서 진짜 firestore_admin 함수로, _load_supplier_map 은 {} 로 monkeypatch, 단계마다 app._roster_cache.clear()): pending 초대 x@y.com 시드 → probe 200 → set_supplier_active(uid, False) → probe 403 not_invited(초대 status revoked) → set_supplier_active(uid, True) → probe 200 supplierCode 같음.
    - 명단 밖 + email_verified False → accept 호출 0, 403 body {"error":{"code":"not_invited","message":…,"email":"x@y.com"}}.
    - 이메일 클레임 없음 → 403, error.email None.
    - get_supplier 예외 → 500 server_error(403 으로 강등하지 않는다). accept 가 SupplierCodeConflict → 500.
    - 비-probe 업로드: 수락된 entry 의 code 가 create_reference_registration(supplier_code=…) 로 간다.
    - 403 로그 한 줄에 원문 메일이 없다(caplog 에 'x@y.com' 없음, 'x***@y.com' 있음).
    - 기존 21 테스트는 입구 이름만 바꿔 그대로 통과(forbidden 단언은 not_invited 로).
  </behavior>
  <action>
RED 먼저: backend/tests/test_supplier_invites.py 를 새로 만들고(순수·fake Firestore) test_reference_upload_url_handler.py 를 behavior 대로 고친 뒤 `cd backend && .venv/bin/python -m pytest tests/test_supplier_invites.py tests/test_reference_upload_url_handler.py -q` 실패 출력 한 줄을 SUMMARY 에 인용한다. 그다음 GREEN. 운영 스크립트는 Task 2 다(이 태스크에서 만들지 않는다).

1) models.py(계약, 38-DESIGN-v2 §W1 데이터): SUPPLIER_CODE_RE 옆에 다음을 둔다. SUPPLIER_INVITE_CODE_RE = `^[A-HJKMNP-Z2-9]{4,8}$`(주석: O·0·I·1·L 금지 — Classting 오타 원인, 리서치 [확인]. 새 초대에만. SSM 옛 코드는 SUPPLIER_CODE_RE — 플래너 결정 (c)). SUPPLIER_INVITE_DEFAULT_DAYS = 14, SUPPLIER_INVITE_MAX_DAYS = 60. INVITE_STATUS_PENDING/ACCEPTED/REVOKED = 'pending'/'accepted'/'revoked'. SUPPLIER_ERR_NOT_INVITED = 'not_invited' 과 한국어 메시지 '초대받은 계정만 쓸 수 있어요.'. 컬렉션 이름 상수 3개(SUPPLIERS_COLLECTION = 'suppliers', SUPPLIER_CODES_COLLECTION = 'supplierCodes', SUPPLIER_INVITES_COLLECTION = 'supplierInvites'). 경로 헬퍼 supplier_path(uid) = f"suppliers/{uid}", supplier_code_path(code) = f"supplierCodes/{code}", supplier_invite_path(email) = f"supplierInvites/{email}". 필드 이름 상수 SUPPLIER_FIELD_DISPLAY_NAME = 'displayName'(firestore_admin 이 이 상수로 쓴다 — 계약 게이트가 models.py 에서 displayName 을 찾는다).

2) supplier_invites.py(새 파일, 순수 — boto3·firebase 무관, 모듈 docstring 에 38-DESIGN-v2 §W1 · 플래너 결정 (b)(c)(h) 인용): behavior 의 다섯 함수 + frozen dataclass SupplierEntry(code: str | None, display_name: str | None) + 예외 SupplierCodeConflict(Exception). validate_invite_code 는 공백 전부 제거 + upper 뒤 SUPPLIER_INVITE_CODE_RE 검사. normalize_invite_email 은 strip + lower, 정규식 `^[^@\s/]+@[^@\s/]+\.[^@\s/]+$` 와 길이 ≤ 254, '.'·'..'·'__' 로 시작/끝나는 doc id 금지 규칙에 걸리지 않게 검사.

3) auth.py: verify_request_claims(event) -> dict 추가. 반환 {"uid", "email"(str|None), "email_verified"(bool — 클레임이 정확히 True 일 때만 True)}. verify_request 는 이 함수를 불러 uid 만 돌려주도록 바꿔 동작을 그대로 둔다(리포의 다른 5 함수 — upload-url · playback-url · reference-api · reference-auto-register · visual-request — 가 verify_request 를 쓴다).

4) responses.py: error(code, message, status=400, extra: dict | None = None) — extra 의 키를 error 객체에 합친다(code·message 는 덮지 못한다). 기존 호출 무변화.

5) firestore_admin.py(파일 끝 Phase 38 공급자 절 근처, 기존 seam 만 사용): get_supplier(uid) -> dict|None · accept_supplier_invite(uid, email, now_ms) -> SupplierEntry|None(트랜잭션 하나: 초대·suppliers/{uid}·supplierCodes 를 먼저 다 읽고 → 판정 → set/update. 트랜잭션에 create 가 없으므로 존재 여부를 읽은 뒤 set. 판정 순서 = ① suppliers/{uid} 가 active False 로 있으면 None ② 초대가 accepted 면 acceptedUid == uid 이고 suppliers/{uid}.active is True 일 때만 멱등 entry, 아니면 None ③ invite_acceptable 이 아니면 None ④ 코드 doc 이 다른 uid 것이면 SupplierCodeConflict ⑤ 세 doc 쓰기 — 결정 (h)) · create_supplier_invite(email, code, display_name, days, now_ms)(코드 doc 존재·다른 메일 pending 같은 코드·같은 메일 pending·같은 메일 acceptedUid 있음은 트랜잭션 밖 사전 조회로 검사 — 운영자 1명이라 경합 무시, 이유를 주석에) · extend_supplier_invite(email, days, now_ms)(pending 만) · revoke_supplier_invite(email)(pending 만 → revoked, accepted 면 ValueError '권한 회수는 deactivate') · list_supplier_invites() · list_suppliers() · upsert_supplier(uid, *, email, code, display_name, active, since_ms)(이미 있으면 덮지 않고 False 반환 — 이관 멱등) · set_supplier_active(uid, active, now_ms=None)(behavior 대로. False 는 suppliers·supplierCodes·수락 초대 revoked 를 한 트랜잭션에서, True 는 doc 없으면 ValueError — 결정 (h)). 모든 입력 메일은 normalize_invite_email 을 거친다. 로그에는 mask_email 만.

6) functions/reference-upload-url/app.py(얇은 핸들러 규율 유지): 입구를 verify_request_claims 로. `_authorize(claims, supplier_map) -> SupplierEntry | None` 하나를 probe·업로드가 같이 쓴다(38-DESIGN-v2 "업로드도 같은 명단 판정"). 순서: ① 명단 캐시 `_roster_cache`(60초, dict[uid → (entry|None, t)] — get_supplier + roster_decision 결과만 담는다) → 없으면 firestore_admin.get_supplier(uid) → roster_decision(doc, supplier_map, _BELLE_UID, uid). ② 결과가 None 이고 email_verified 이고 email 이 있으면 **캐시 적중 여부와 무관하게** accept_supplier_invite(uid, email, now_ms) 를 부른다(음성 캐시가 방금 생긴 초대를 60초 막지 않게 — 체커 W3). 수락되면 `_roster_cache[uid] = (entry, now)`(38-DESIGN-v2 "수락 직후 무효화"). ③ 그래도 None → 403 `responses.error(models.SUPPLIER_ERR_NOT_INVITED, 메시지, status=403, extra={"email": email})`, 로그 `reference-upload-url not_invited uid=%s email=%s verified=%s` 에 mask_email. get_supplier·accept 예외는 log.exception + 500 server_error(조용히 403 으로 바꾸지 않는다). probe 200 = {"probe": True, "uid": uid, "supplierCode": entry.code, "displayName": entry.display_name}(플래너 결정 (a)). 업로드 경로 create_reference_registration 의 supplier_code 는 entry.code. firestore_admin 함수는 모듈 속성으로 부른다(fake_firestore 끝-끝 테스트가 seam 을 바꿀 수 있게). `_is_supplier` 는 roster_decision 으로 대체하고 지운다. 'forbidden' 코드는 이 파일에서 사라진다. 모듈 docstring 흐름 설명을 새 순서로 고친다. 캐시 때문에 deactivate 는 최대 60초 늦게 닿는다(주석 — 라이브 7행이 65초 기다리는 이유).

7) 계약 3벌(같은 커밋): docs/contract.md §2 `POST /reference/upload-url` — 인증 문단을 명단 판정 순서(doc 우선 → SSM ∪ BELLE_UID → 초대 수락)로, probe 응답에 displayName, 오류 표의 `403 forbidden` 을 `403 not_invited  명단 밖·초대 없음/만료/취소/메일 미인증·회수됨 — error.email = 토큰 메일(없으면 null)` 로. §3 에 세 컬렉션 필드 표(`suppliers/{uid}` · `supplierCodes/{code}` · `supplierInvites/{email}`, revokedAt 포함)와 회수·되살리기 의미(결정 (h)) 한 문단, "클라이언트 접근: 지금은 전부 거부(기본 차단). suppliers 본인 읽기·supplierCodes 로그인 읽기는 W2 규칙에서". app/src/types/analysis.ts — SupplierProbeResponse 에 `displayName: string | null`(옛 서버 응답엔 없을 수 있어 소비처가 `?? null`), `SupplierNotInvitedError { code: 'not_invited'; message: string; email: string | null }`, `SupplierDoc`(주석에 `suppliers/{uid}`)·`SupplierCodeDoc`(주석에 `supplierCodes/{code}`) 인터페이스(W2 소비 예정 — 주석), 초대 doc 은 클라이언트가 못 읽으므로 TS 타입을 두지 않는다는 주석 한 줄(`supplierInvites/{email}` 이름을 적는다 — 계약 게이트가 찾는다).

금지: Firestore 규칙 파일 변경 · 새 pip 의존성 · SSM 쓰기 코드.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests -q && grep -v '^[[:space:]]*#' functions/reference-upload-url/app.py | grep -c '"forbidden"' | grep -qx 0 && cd .. && for f in docs/contract.md backend/shared/python/sunity_shared/models.py app/src/types/analysis.ts; do for t in not_invited displayName 'suppliers/' supplierCodes supplierInvites; do grep -q "$t" "$f" || { echo "MISSING $t in $f"; exit 1; }; done; done && echo CONTRACT_OK && cd app && npm run typecheck</automated>
  </verify>
  <done>backend 전체 pytest fail 0(통과 수·새 테스트 수를 SUMMARY 에) · RED 출력 한 줄 인용 · app.py 주석 밖 "forbidden" 0 · 계약 게이트 CONTRACT_OK(세 파일 각각에 not_invited · displayName · suppliers/ · supplierCodes · supplierInvites) · 회수 테스트 3종(accepted 초대 + active False → accept None 쓰기 0 · 핸들러 회수 뒤 403 · deactivate 가 초대 revoked) 과 reactivate 200 테스트가 통과 · 음성 캐시 테스트 통과 · extend/revoke/upsert 멱등 fake 테스트 통과 · typecheck exit 0(analysis.ts 만 바뀐 상태). 커밋 `feat(quick-260930-lfw): supplier email invite — accept on probe, not_invited, deactivate revokes, contract` — 이 태스크 10파일만 명시 스테이징.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 운영 스크립트 supplier_invite.py — create/extend/revoke/list/migrate-ssm/deactivate/reactivate</name>
  <files>backend/scripts/supplier_invite.py, backend/tests/test_supplier_invite_script.py</files>
  <behavior>
    - main(['create','--email','A@B.com','--code','eunji','--name','정은지']) → exit 2, Firestore 호출 0(코드 규칙 위반). 메일 규칙 위반도 exit 2, 호출 0.
    - 정상 create(firestore_admin.create_supplier_invite monkeypatch) → exit 0, stdout 에 링크 줄 `https://d2ivnoigym2xlu.cloudfront.net/supplier` 과 안내 문장 줄(메일·만료 날짜 포함) 2줄.
    - create 에서 firestore_admin 이 ValueError('이미 수락된 메일 …') → exit 1, stderr 에 그 문구(reactivate 안내 포함).
    - deactivate --uid X → set_supplier_active('X', False) 1회, 반환의 code·revokedInvite(가린 메일)을 출력. 
    - reactivate --uid X → set_supplier_active('X', True) 1회, exit 0. 함수가 ValueError(doc 없음) → exit 1.
    - migrate-ssm --dry-run(SSM 읽기·firebase auth.get_user 를 monkeypatch): SSM 두 uid + belle-uid 를 읽어 `belle-uid: <uid>` 줄과 uid 별 계획 줄을 찍고, upsert_supplier 호출 0.
    - migrate-ssm 실행을 fake_firestore 위에서 두 번 → 두 번째는 모든 uid 가 'skip', suppliers·supplierCodes doc 개수와 내용 동일.
    - `--help` 가 Firestore·SSM 초기화 없이 일곱 서브커맨드 이름을 모두 보여 준다.
  </behavior>
  <action>
테스트 먼저(backend/tests/test_supplier_invite_script.py — 스크립트를 importlib 로 경로 로드, firestore_admin 함수와 SSM 읽기 함수를 monkeypatch, migrate 재실행은 phase31 conftest 의 fake_firestore). 실패 한 줄을 SUMMARY 에 인용한 뒤 구현.

scripts/supplier_invite.py(새 파일, argparse 서브커맨드, snapshot_reference_baseline.py 관례 — 리포 루트 기준 sys.path 에 backend/shared/python, SA 파일을 FIREBASE_SA_PATH 로. Firebase·boto3 초기화는 서브커맨드 실행 안에서만 — `--help` 가 자격 없이 돈다):
- create --email --code --name [--days 14](코드·메일 검증 실패 = exit 2, Firestore 호출 전. firestore_admin ValueError = exit 1. 성공 시 두 줄: 링크 `https://d2ivnoigym2xlu.cloudfront.net/supplier` / `이 링크를 열고 {email} Google 계정으로 로그인해 주세요. {YYYY-MM-DD}까지 유효해요.`)
- extend --email [--days 14] · revoke --email
- list(초대와 공급자 표. 운영 터미널이므로 메일 원문 출력 — SUMMARY·DEPLOY 에 옮길 때는 가린다)
- migrate-ssm [--dry-run](boto3 SSM `/sunity/motion/supplier-uids` + `/sunity/motion/belle-uid` 를 **읽기만** 해서 합집합. `belle-uid: <uid>` 줄을 먼저 찍는다(Task 4 E0 가 이 줄로 FDJr 를 확인). 각 uid 의 Firebase Auth 레코드(firebase_admin.auth.get_user)에서 email·display_name 을 읽고 upsert_supplier(active True, code 는 parse_supplier_uids 결과 그대로 — 결정 (c)). 코드가 있으면 supplierCodes/{code} 도 만든다. 코드 없는 uid 는 코드 없이. 이미 있는 doc 은 건너뛰고 'skip' 출력)
- deactivate --uid(set_supplier_active False — 수락 초대 revoked 까지 같은 트랜잭션, 결정 (h))
- reactivate --uid(set_supplier_active True — 되살리기의 유일한 길, 결정 (h))
모듈 docstring 에 "이 스크립트는 SSM 을 쓰지 않는다(읽기만). SSM 되돌림은 배포 절차(260930-lfw-DEPLOY.md E0)에서 AWS CLI 로 한 번 했다" 와 서브커맨드 일곱 개 요약. 한국어 안내 문구는 스크립트 안 상수로(운영 도구 — 앱 문구 규율 밖).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_supplier_invite_script.py tests/test_supplier_invites.py -q && H="$(.venv/bin/python scripts/supplier_invite.py --help)" && for c in create extend revoke list migrate-ssm deactivate reactivate; do echo "$H" | grep -q -- "$c" || { echo "MISSING $c"; exit 1; }; done && grep -v '^[[:space:]]*#' scripts/supplier_invite.py | grep -c 'put_parameter' | grep -qx 0 && echo SCRIPT_OK</automated>
  </verify>
  <done>두 테스트 파일 fail 0 · `--help` 에 일곱 서브커맨드 · 스크립트 코드에 put_parameter 0(SSM 쓰기 없음) · SCRIPT_OK. 커밋 `feat(quick-260930-lfw): supplier_invite ops script — create/extend/revoke/list/migrate-ssm/deactivate/reactivate` — 이 태스크 2파일만 명시 스테이징.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: 공급자 페이지 — A-2 v2 · 강사 코드 줄 · 크게 보기 · 빌드 라벨 제거</name>
  <files>app/src/constants/supplierCopy.ts, app/src/constants/supplierCopy.test.ts, app/src/lib/supplierRules.ts, app/src/lib/supplierRules.test.ts, app/src/lib/supplierFixtures.ts, app/src/lib/api.ts, app/src/components/SupplierUi.tsx, app/src/app/supplier/index.tsx, app/src/app/supplier/upload.tsx</files>
  <behavior>
    - supplierCopy.noAccess 가 38-DESIGN-v2 A-2 문구와 글자 단위로 같다: title '초대받은 분만 쓸 수 있어요' · body '공급자 페이지는 Sunity 가 초대한 강사·선수만 쓸 수 있어요. 초대받으셨다면 초대받은 Google 계정으로 로그인해 주세요.' · accountLabel '지금 로그인한 계정' · helpTitle '초대가 필요하거나 계정이 헷갈리면' · helpBody '아래로 알려 주세요. 운영팀이 확인해 드려요.' · kakaoTitle '카카오톡 채널로 문의' · kakaoSub 'pf.kakao.com/_CyNxkn' · kakaoUrl 'http://pf.kakao.com/_CyNxkn' · mailTitle '메일로 문의' · mailSub 'cs@sunity.ai' · mailUrl 'mailto:cs@sunity.ai' · checking(유지).
    - 지운 키가 없다: noAccess.idLabel/copyId/refresh/stillNo/refreshHint · home.codeTitle/athlete/sport/codeHow/codePendingTitle/codePendingBody · common.build · common.copy · common.copiedShort.
    - 새 키: home.codeRow = { label '내 강사 코드', copy '복사', big '크게 보기' } · bigCode = { title '{name} 강사님의 코드', titleNoName '내 강사 코드', how 'Sunity 앱 → 마이 → 강사 코드에\n이 코드를 넣어 주세요' }. common.copied '복사됐어요' 유지.
    - supplierFixtures.apiFailures 의 403 행이 `{ status: 403, code: 'not_invited', expect: 'notInvited' }` 다(체커 W1). 표를 도는 supplierRules.test.ts 테스트 이름에서 'forbidden' 을 'notInvited' 로.
    - mapPresignFailure({status:403, code:'not_invited'}) === 'notInvited', ({status:403, code:'unknown'}) === 'notInvited'(상태코드 기준 유지), presignFailureMessage('notInvited') === null. 'forbidden' 종류는 없다.
    - bigCodeFontSize(5, 350) === 72 · bigCodeFontSize(8, 350) === 56 · bigCodeFontSize(8, 200) === 32(하한) — 식 min(72, max(32, floor(maxWidth / (len * 0.78)))).
  </behavior>
  <action>
테스트 먼저(supplierCopy.test.ts · supplierRules.test.ts · supplierFixtures.ts 를 behavior 대로 고치고 `node --test` 실패 한 줄을 SUMMARY 에 인용), 그다음 구현. 한국어 리터럴·색 리터럴·이모지는 화면 파일과 SupplierUi 에 0(eal 과 같은 게이트). 문구 값은 38-DESIGN-v2 §W1 화면 절에서 그대로 옮긴다.

1) supplierCopy.ts: behavior 의 키 추가·삭제. 파일 머리 치환 자리 목록에서 `{sha}` 를 빼고 `{name}` 은 둔다. home.codeRow·bigCode·noAccess 키에 `// 38-DESIGN-v2 A-2` / `A-3` / `크게 보기` 출처 주석.

2) supplierRules.ts: PresignFailureKind 의 'forbidden' → 'notInvited'(38-DESIGN-v2 "기존 forbidden 을 받는 앱 코드도 함께 정리"). 판정은 계속 status 403 기준(옛 서버·새 서버 모두). bigCodeFontSize(codeLength, maxWidth) 순수 함수 추가(상수 BIG_CODE_MAX_PT 72 · BIG_CODE_MIN_PT 32 · BIG_CODE_CHAR_EM 0.78 — 8자 코드가 390 폭 폰에서 넘치지 않게).

3) supplierFixtures.ts(:242): apiFailures 의 403 행을 `{ status: 403, code: 'not_invited', expect: 'notInvited' }` 로. 표 주석이 'forbidden' 을 말하면 같이 고친다. supplierRules.test.ts :228 테스트 이름 '403 forbidden' → '403 notInvited', :233 근처 presignFailureMessage 테스트 이름 'forbidden 은 문구 없이 A-2 로' → 'notInvited 는 문구 없이 A-2 로'.

4) api.ts: ApiError 에 `readonly email: string | null`(생성자 4번째 선택 인자, 기본 null — 기존 호출 무변화). parseErrorCode 를 본문에서 code 와 error.email(문자열일 때만)을 같이 뽑는 함수로 바꾸고 authedJson 이 넘긴다. probeSupplier 주석의 '403 forbidden' → '403 not_invited(error.email = 로그인 메일)'.

5) upload.tsx: 'forbidden' 두 곳(:176, :342 근처)을 'notInvited' 로. 동작 변화 없음.

6) SupplierUi.tsx: CodeCard·IdBox 와 그들만 쓰던 스타일·상수(H.photo, 사진 음영 사용 등)를 지운다. 새 부품(색·간격은 theme 토큰과 이 파일 `space`/`R` 만, 눌림은 기존 `pressed && s.pressed` 문법 — apple-design press-down):
   - AccountBox({label, email}): softBg · 반경 R.button(13) · 패딩 14 16 · label text.aux · email 17/700(text.labelBold, selectable).
   - ContactRow({kind: 'kakao'|'mail', title, sub, onPress}): 1px colors.divider · 반경 13 · 패딩 12 16 · 가로. 왼쪽 아이콘 32 정사각 반경 8 — kakao = colors.kakao.bg 바탕 + SocialIcon id 'kakao' 글리프 약 18, mail = colors.softBg 바탕 + Ionicons 'mail-outline' 18 textMid. 가운데 세로 title 17/700 / sub text.aux. 오른쪽 chevron-forward 20 colors.inputBorder. accessibilityRole 'link', accessibilityLabel = title.
   - CodeRow({label, code, copyLabel, onCopy, bigLabel, onBig}): 흰 면 · 1px divider · 반경 R.card(15) · 패딩 12 12 12 16 · 가로 정렬. 왼쪽 세로 label text.caption13 / code 20/700 brand 자간 1.2(+6%). 오른쪽 알약 두 개 간격 8: 높이 36 · 반경 18 · 1px inputBorder · 라벨 15/700 textPrimary · 좌우 패딩 14 · hitSlop 로 터치 44 확보.
   - BigCodeModal({visible, title, code, how, closeLabel, onClose}): RN Modal `animationType="fade"`, `transparent={false}`, onRequestClose=onClose(웹 ESC 는 react-native-web ModalContent 가 이 콜백을 부른다). 흰 바탕, 오른쪽 위 X(Ionicons 'close' 28, 터치 44, accessibilityLabel closeLabel), 세로 가운데 정렬: title 20/700 textMid → 16 → code(글자 크기 = bigCodeFontSize(code.length, min(창폭, 430) - 40), 700, brand, 자간 = 크기 × 0.08, numberOfLines 1) → 24 → how 17 textMid 가운데. 움직임은 fade(투명도)뿐이다. 슬라이드·확대가 없어 reduced-motion 과 같은 모습이다(38-DESIGN-v2 "투명도만").
   파일 머리 주석의 "새 애니메이션 0" 문장을 "크게 보기 모달 fade 하나(투명도만)" 로 고친다.

7) supplier/index.tsx:
   - Probe 타입: ok { code, displayName } · notInvited { email: string | null } · 나머지 그대로. runProbe: 성공이면 displayName = res.displayName ?? null. 실패 kind 'notInvited' 면 email = e instanceof ApiError ? e.email : null.
   - A-2(phase 'noAccess') 를 38-DESIGN-v2 A-2 순서로 다시 그린다: 워드마크(mt40) → 32 → AlertIcon 44 → 16 → text.display 제목 → 8 → 본문 17 textMid(text.label + text.mid) → 24 → AccountBox(label, email = probe.email ?? user?.email ?? '–') → 12 → PrimaryCta(common.signOut '다른 계정으로 로그인', onSignOut) → 40 → helpTitle 17/700 → 4 → helpBody text.aux → 12 → ContactRow kakao · 8 · ContactRow mail. Linking.openURL(kakaoUrl / mailUrl) — react-native-web 은 새 창으로 연다. 카드 래퍼·identity 줄·내 ID 상자·ID 복사·등록 확인하기·힌트·recheckBusy/stillNo/onRecheck 상태는 지운다.
   - 홈: CodeCard 블록 전체를 지우고, Sheet 맨 위(내 동작 카드/StepCard 위, 간격 12)에 `supplierCode` 가 있을 때만 CodeRow. 복사 = 기존 onCopy(토스트 common.copied '복사됐어요', 실패면 copyFallback 문구). 크게 보기 = bigOpen 상태 → BigCodeModal(title = displayName 이 있으면 bigCode.title 의 {name} 치환, 없으면 bigCode.titleNoName, closeLabel = common.close). codeCopied·COPIED_LABEL_MS 는 소비처가 없어지면 지운다. 내 동작 카드의 onLayout 스크롤 오프셋 계산은 CodeRow 가 위에 생겨도 맞게 둔다(카드 y 는 Sheet 안 상대값이라 그대로 동작하는지 확인).
   - 빌드 라벨: A-1 아래와 홈 맨 아래 두 곳, BUILD_SHA·buildLabel·expo-constants import 를 지운다(38-SCENARIOS §4, belle ○).
   - 파일 머리 상태기계 주석: noAccess = "A-2 v2: 403 not_invited — 로그인 메일 + 다른 계정 + 문의 2"(ID 닭-달걀 문장 삭제), home 의 '내 코드' → '강사 코드 줄 + 크게 보기'.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && node --test src/constants/supplierCopy.test.ts src/lib/pickerFailure.test.ts src/lib/supplierForm.test.ts src/lib/supplierRules.test.ts src/lib/videoDuration.test.ts src/lib/videoMeta.test.ts 2>&1 | grep -E '^# (tests|pass|fail)' && npm run typecheck && grep -rn "CodeCard\|IdBox\|buildLabel\|common\.build\|'forbidden'" src/app/supplier src/components/SupplierUi.tsx src/lib/supplierRules.ts src/lib/supplierFixtures.ts | grep -v ':[0-9]*:\s*//' | wc -l | tr -d ' ' | grep -qx 0 && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist >/dev/null && grep -l 'pf.kakao.com/_CyNxkn' dist/_expo/static/js/web/*.js && echo EXPORT_OK</automated>
  </verify>
  <done>node 6파일 fail 0(pass 수 변화를 SUMMARY 에) · typecheck exit 0 · supplier 화면·SupplierUi·supplierRules·supplierFixtures 에서 CodeCard/IdBox/buildLabel/common.build/'forbidden' 0 · 웹 export 성공 + 번들에 카카오 URL · 주석 밖 색 리터럴·한국어 리터럴·이모지 0(eal 의 ko-check 방식으로 supplier 3파일 + SupplierUi 확인, 결과를 SUMMARY 에). 로그인 뒤 화면은 이 태스크에서 그리지 못한다 → A-2·홈·크게 보기는 [미확인 — Task 5 belle 폰]. 커밋 `feat(quick-260930-lfw): supplier page A-2 v2, code row + big view, drop build label` — 이 태스크 9파일만 명시 스테이징(app/dist 는 스테이징 금지).</done>
</task>

<task type="auto">
  <name>Task 4: 배포 — Lambda layer+코드(zip 보존·롤백) → SSM v1 되돌림 → 이관(BELLE 1건) → 라이브 확인 → 웹 재배포</name>
  <files>.planning/quick/260930-lfw-supplier-email-invite/260930-lfw-DEPLOY.md</files>
  <action>
모든 AWS 명령은 `AWS_PROFILE=sunity-motion`. 시각·명령·결과를 DEPLOY.md 에 순서대로 적는다(38-13-DEPLOY.md 형식: 리소스 · 읽기 먼저 · 명령 원문 · 검증 표 · 롤백). 메일은 DEPLOY.md·SUMMARY 에 전부 가려 적는다(c***@gmail.com — 홈 디렉터리 git PII 규칙). uid 는 앞 4자 + '…'. 롤백 보존물은 전부 리포 밖 `/Users/Shared/sunity-motion-rollback/lfw/` 한 곳에 둔다.

A. 멈춤 조건 확인(쓰기 전): Task 1~3 변경으로 CFN·IAM 이 필요해졌으면(예: 새 SSM 파라미터 읽기, 새 AWS 리소스) 여기서 멈추고 체크포인트로 belle 에게 돌려준다(38-DESIGN-v2 "CFN 변경이 있으면 belle 체크포인트"). 플래너 판단 (g) 로는 필요 없다. 필요 없음의 근거(함수 역할의 ssm 리소스 2개 = firebase-sa·supplier-uids, 새 코드가 읽는 SSM = 그 둘뿐, belle-uid 는 env 로 이미 들어옴)를 DEPLOY.md 에 적는다. migrate-ssm 과 E0 의 SSM 되돌림은 로컬 사용자 자격으로 돈다.

B. 보존(쓰기 전): `/Users/Shared/sunity-motion-rollback/lfw/` 에 현재 함수 zip(`get-function` Code.Location)과 layer :21 zip(`get-layer-version --version-number 21`)을 받는다. `get-function-configuration` 의 Layers·CodeSha256·LastModified·env 키 이름만 → `.planning/quick/260930-lfw-supplier-email-invite/lambda-before.json`. layer :21 zip 안의 `python/sunity_shared/{models,firestore_admin,auth,responses}.py` 네 파일 sha256 을 이 플랜 전 커밋(`git show <Task1 커밋>^:backend/shared/python/sunity_shared/<f>`)과 비교한다. 하나라도 다르면 멈추고 보고한다(드리프트 — 메모리 lambda-code-update-without-sam-deploy).

C. 새 zip: layer = :21 zip 복사본에 리포의 위 네 파일 + `supplier_invites.py` 를 덮어쓴다(다른 파일·의존성 무접촉). 함수 = 현재 함수 zip 복사본에 `app.py` 만 덮어쓴다. 스모크: 새 zip 둘을 scratchpad 에 풀고 `backend/.venv/bin/python` 으로 PYTHONPATH=<풀린 layer>/python, cwd=<풀린 함수>, env VIDEO_BUCKET=x·BELLE_UID=x·AWS_DEFAULT_REGION=ap-northeast-2 에서 `import app; assert hasattr(app,'lambda_handler')` 가 통과해야 한다(firebase import 는 지연이라 venv 로 된다).

D. 배포(layer 먼저 — 새 layer 는 옛 app.py 와 호환되므로 중간 상태가 안전하다): `publish-layer-version --layer-name sunity-motion-pilot-shared --zip-file fileb://… --compatible-runtimes python3.12 --compatible-architectures arm64` → 새 ARN(:22 예상). `update-function-configuration --function-name sunity-motion-pilot-reference-upload-url --layers <새 ARN>` → `aws lambda wait function-updated`. `update-function-code --zip-file fileb://<새 함수 zip>` → wait. 이 함수 **하나만** 새 layer 로 바꾼다(배포 스택의 다른 5함수는 :21 그대로 — 반경 최소, CFN 밖 드리프트로 DEPLOY.md 에 적는다). 롤백 명령 두 줄(layers :21 로 · 보존 zip 으로 update-function-code)을 DEPLOY.md 롤백 절에 원문으로.

E0. SSM supplier-uids v1 되돌림(결정 (f), 오케스트레이터 결정 — UmH3 은 이관하지 않는다):
   1) `aws ssm get-parameter --name /sunity/motion/supplier-uids --query 'Parameter.[Value,Version,Type]' --output text` → 값·버전·타입을 DEPLOY.md 에 가려 적는다(uid 앞 4자). 값이 `FDJr…:BELLE, UmH3…` 두 항목(v2)이 아니면 멈추고 보고한다.
   2) 롤백 파일 `/Users/Shared/sunity-motion-rollback/lfw/ssm-supplier-uids-rollback.sh` 에 정확한 명령 `aws ssm put-parameter --name /sunity/motion/supplier-uids --type String --overwrite --value '<v2 원문>'` 를 적고 `chmod 600`. DEPLOY.md 롤백 절에는 같은 명령을 값만 가려(`'FDJr…:BELLE, UmH3…'`) 원문 그대로 적고 파일 경로를 적는다.
   3) `aws ssm get-parameter-history --name /sunity/motion/supplier-uids --output json` → 출력에서 Version 1 항목의 Value 를 v1 값으로 쓴다(터미널에만, 문서에는 가림). `FDJr…:BELLE` 한 항목이 아니거나 UmH3 가 들어 있으면 멈추고 보고한다.
   4) `aws ssm put-parameter --name /sunity/motion/supplier-uids --type String --overwrite --value '<v1 원문>'` → 새 버전 번호와 되돌린 시각(UTC, 초 단위)을 DEPLOY.md 에 적는다.
   5) 다시 `get-parameter` → 값이 v1 과 같음을 표에 적는다.
   6) Lambda SSM 캐시 주의(DEPLOY.md 에 한 줄): 되돌림 직전 60초 안에 v2 를 읽은 warm 컨테이너는 되돌림 뒤 최대 60초 UmH3 을 통과시킬 수 있다 → Task 5 는 4) 시각 + 60초 이후에 시작한다(그 시각을 DEPLOY.md 에 계산해 적는다).
E. 이관: `backend/.venv/bin/python backend/scripts/supplier_invite.py migrate-ssm --dry-run` → uid 1개(FDJr…, 코드 BELLE)이고 `belle-uid:` 줄이 같은 FDJr uid 인지 확인한다. 둘 중 하나라도 어긋나면(uid 2개 이상, belle-uid 가 다른 uid) 멈추고 보고한다. 맞으면 `migrate-ssm` 실행 → `list` 로 suppliers **1건**(BELLE 코드, active True) · supplierCodes/BELLE 1건 확인. 두 번째 계정(UmH3…)에는 deactivate 도 이관도 하지 않는다(suppliers doc 없음 — 명단 밖이라 A-2 를 본다).

F. 라이브 확인(일회용 계정 — 38-09 regress 계정 선례): Admin SDK 로 Auth 사용자 3개를 만든다. uid `lfwtest-a`·`lfwtest-b`·`lfwtest-c`, 메일 `lfw-a@sunity-test.invalid` 등. a·c 는 email_verified True, b 는 False. 각자 custom token → Identity Toolkit REST `accounts:signInWithCustomToken?key=<app/.env EXPO_PUBLIC_FIREBASE_API_KEY, 출력 금지>` 로 ID 토큰을 받는다. 먼저 ID 토큰 payload 를 base64 로 풀어 email·email_verified 클레임이 있는지 확인한다. 없으면 수락 라이브 확인은 [미확인]으로 적고 1·2 행만 한다. 스크립트는 scratchpad 에 둔다(커밋 안 함). 표에 적을 행:
   1) 무토큰 POST → 401 + `access-control-allow-origin: *`.
   2) a, 초대 없음 → 403, error.code not_invited, error.email = a 메일.
   3) 2행 뒤 60초 안에 `supplier_invite.py create --email lfw-a@… --code QZTEST --name 시험` → 두 줄 출력 확인 → a probe → 200 supplierCode QZTEST displayName '시험'(음성 캐시가 수락을 막지 않음 — W3 라이브) → Firestore suppliers/lfwtest-a active True · supplierCodes/QZTEST supplierUid lfwtest-a · 초대 accepted·acceptedUid.
   4) a 다시 probe → 200(명단 경로).
   5) b(미인증) + b 메일 초대(코드 QZTSTB) → 403 not_invited, 초대는 pending 그대로.
   6) c 초대(코드 QZTSTC) create 후 revoke → c probe 403.
   7) `deactivate --uid lfwtest-a` → 초대 lfw-a status revoked · supplierCodes/QZTEST active False 를 읽어 확인 → 65초 기다린 뒤(명단 캐시 60초) a probe → 403 not_invited(BLOCKER 1 라이브).
   8) `reactivate --uid lfwtest-a` → 65초 기다린 뒤 a probe → 200 supplierCode QZTEST. 같은 메일로 `create` → exit 1(재초대 길 없음).
   9) CloudWatch 로그에서 이 시간대 not_invited 줄에 원문 메일이 없고 가린 메일만 있음을 확인.
   뒤처리: 일회용 Auth 사용자 3개 삭제, suppliers/lfwtest-*·supplierCodes/QZTEST·QZTSTB·QZTSTC(수락 안 된 코드는 doc 이 없을 수 있다)·supplierInvites 의 lfw-* 메일 doc 삭제 → 다시 읽어 전부 없음을 표에 적는다.

G. 웹 재배포(38-13-DEPLOY "재배포 = 1 빌드 → 6 sync → 7 무효화"): `git rev-parse --short HEAD` 를 DEPLOY.md 에 기록(= 빌드 기준 코드) → `cd app && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist` → `aws s3 sync app/dist s3://sunity-motion-pilot-supplier-web --delete --only-show-errors` → `aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"` → `aws cloudfront wait invalidation-completed`. 확인: `/supplier` 200 text/html · index.html 이 가리키는 entry 번들 이름이 이번 export 와 같음 · 그 번들에 `pf.kakao.com/_CyNxkn` 있음. 가능하면 시뮬 Safari 로 A-1 한 장(빌드 라벨 없음)을 scratchpad 에 찍어 열어 본다.

H. 라이브 규칙 무접촉 확인: `firestore.rules` git diff 0.

I. DEPLOY.md 끝에 빈 "폰 확인(Task 5)" 절을 만들어 둔다 — 오케스트레이터가 TESTB 초대·회수를 가려 적는 자리(두 번째 계정 uid 앞 4자 · 메일 가림 · 시각). SSM v2 롤백 주의 한 줄: Task 5 의 deactivate 뒤에는 v2 로 되돌려도 UmH3 은 suppliers doc(active False) 이 우선해 막힌다(결정 (b)).

커밋: DEPLOY.md 와 lambda-before.json 만 명시 스테이징 → `docs(quick-260930-lfw): deploy record — layer/code, ssm v1 revert, migrate-ssm, web redeploy`. 롤백 폴더(리포 밖)는 커밋 대상이 아니다. `.planning/TRAINING-DUE.md` 스테이징 금지 · push 금지 · PLAN/SUMMARY/STATE 커밋 금지.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && AWS_PROFILE=sunity-motion aws lambda get-function-configuration --function-name sunity-motion-pilot-reference-upload-url --query '[Layers[0].Arn, LastUpdateStatus]' --output text && V="$(AWS_PROFILE=sunity-motion aws ssm get-parameter --name /sunity/motion/supplier-uids --query Parameter.Value --output text)" && [ "$(echo "$V" | tr ',' '\n' | grep -c '[^[:space:]]')" = 1 ] && ! echo "$V" | grep -q UmH3 && echo SSM_V1_OK && test -s /Users/Shared/sunity-motion-rollback/lfw/ssm-supplier-uids-rollback.sh && echo ROLLBACK_FILE_OK && curl -s -o /dev/null -w '%{http_code}\n' -X POST "$(grep EXPO_PUBLIC_API_BASE_URL app/.env | cut -d= -f2-)/reference/upload-url" && curl -s -o /dev/null -w '%{http_code}\n' https://d2ivnoigym2xlu.cloudfront.net/supplier && git diff --quiet HEAD -- firestore.rules && echo RULES_UNTOUCHED</automated>
  </verify>
  <done>함수 layer = 새 버전(:21 아님) · LastUpdateStatus Successful · SSM supplier-uids 가 한 항목(FDJr…:BELLE)이고 UmH3 없음(SSM_V1_OK) · 롤백 파일 있음(600) · 무토큰 401 · /supplier 200 · 규칙 파일 무변경 · DEPLOY.md 에 보존 경로·layer 파일 sha 대조·새 layer ARN·SSM v2(가림)·v1 되돌린 버전과 시각·Task 5 시작 가능 시각·롤백 명령 3종(layer · 함수 코드 · SSM, SSM 값은 가림)·이관 결과 suppliers 1건(BELLE)·라이브 표 9행([확인]/[미확인] 표기)·뒤처리 0건·웹 빌드 sha·entry 번들 이름·빈 "폰 확인" 절이 있다.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 5: belle 폰 확인 — A-2(두 번째 계정) → TESTB 초대 수락 → 본 계정 홈 코드 줄 · 크게 보기</name>
  <files>(없음 — 확인만. 2)·5) 의 데이터 쓰기는 오케스트레이터가 한다)</files>
  <action>Task 4 가 끝나고 DEPLOY.md 의 "Task 5 시작 가능 시각"(SSM 되돌림 + 60초)이 지난 뒤, 아래 how-to-verify 를 단계별로 진행한다. 실행기는 코드·배포·데이터를 바꾸지 않는다. 2) 초대 생성과 5) 회수는 **오케스트레이터**가 한다(체크포인트 안에서 명시 허용된 데이터 쓰기 — 결정 (f)). × 가 오면 번호별로 SUMMARY 의 관측 절에 적고 오케스트레이터에게 돌려준다(스스로 고치지 않는다).</action>
  <verify><automated>curl -s -o /dev/null -w '%{http_code}\n' https://d2ivnoigym2xlu.cloudfront.net/supplier</automated></verify>
  <done>belle 의 1·3·4 ○/× 답이 SUMMARY 에 원문으로 있다. 3 이 ○ 면 진짜 Google 계정 초대 수락이 [확인] 이다. 5) 회수가 돌아 두 번째 계정 uid 의 suppliers active False · supplierCodes/TESTB active False · 초대 revoked 이고, DEPLOY.md "폰 확인" 절에 가려 기록돼 있다(uid 앞 4자 · 메일 가림).</done>
  <what-built>서버가 메일 초대를 probe 에서 수락한다. 403 은 not_invited(로그인 메일 포함)이다. 회수는 수락 초대까지 revoked 로 바꾸고 되살리기는 reactivate 로만 된다. 공급자 페이지는 A-2 v2, 강사 코드 줄 + 크게 보기로 바뀌었고 빌드 라벨이 빠졌다. 운영 스크립트가 있다. Lambda·웹은 재배포됐다. SSM 명단은 v1(BELLE 만)로 되돌렸고(v2 는 롤백 파일에 보존) 이관은 BELLE 1건이다 — 두 번째 계정은 명단 밖이다. 일회용 계정으로 수락·거부·취소·회수·되살리기를 라이브에서 확인했다(DEPLOY.md 표).</what-built>
  <how-to-verify>
    1. 폰 Safari 에서 `https://d2ivnoigym2xlu.cloudfront.net/supplier` 를 연다. 옛 화면이 보이면 탭을 닫고 다시 연다. 두 번째 Google 계정(catharina…)으로 로그인된 상태에서 A-2 가 보여야 한다:
       - 제목 `초대받은 분만 쓸 수 있어요`
       - 회색 면에 `지금 로그인한 계정` + 그 계정 메일
       - `다른 계정으로 로그인` 버튼
       - `초대가 필요하거나 계정이 헷갈리면` 아래 문의 두 줄(카카오 노란 아이콘 / 메일 아이콘)
       - 내 ID 상자·`ID 복사`·`등록 확인하기`가 없어야 한다.
       카카오 줄을 누르면 pf.kakao.com 채널 페이지가 새 창으로, 메일 줄을 누르면 메일 앱이 cs@sunity.ai 로 열린다.
       ○/× 로 답하고, ○ 면 화면에 보인 메일을 알려 주세요(다음 단계 초대에 씁니다).
    2. (오케스트레이터가 한다 — belle 는 기다린다) `backend/.venv/bin/python backend/scripts/supplier_invite.py create --email <1에서 보인 메일> --code TESTB --name "테스트 공급자"` → 두 줄 출력 확인.
    3. 폰에서 그 페이지를 새로고침한다 → 곧바로 홈이 열리고 시트 맨 위에 `내 강사 코드 TESTB` + [복사] [크게 보기] 한 줄이 있어야 한다. ○/×. (진짜 Google 계정 초대 수락 확인)
    4. 홈 맨 아래 `다른 계정으로 로그인` → 로그인 화면(아래 `빌드 dev` 없음) → 본 계정으로 로그인 → 홈:
       - 시트 맨 위에 `내 강사 코드 BELLE` + [복사] [크게 보기] 한 줄이 있다.
       - 사진이 든 `내 코드` 큰 카드가 없다. 맨 아래·로그인 화면 아래 `빌드` 글자가 없다.
       - [복사] → 위에 `복사됐어요` 토스트. 메모장에 붙이면 BELLE.
       - [크게 보기] → 흰 화면에 `{belle 이름} 강사님의 코드`, 큰 주황 BELLE, 안내 두 줄. 오른쪽 위 X 로 닫힌다. 열고 닫을 때 흐려졌다 나타나기만 해야 한다(미끄러짐 없음).
       ○/× 로 답해 주세요. × 면 번호와 사진.
    5. (오케스트레이터가 한다 — 확인이 끝난 뒤) `supplier_invite.py deactivate --uid <두 번째 계정 uid — list 로 확인>` → 출력에 code TESTB · revokedInvite(가린 메일). W2 에서 실제 수강생이 TESTB 를 쓰지 못하게 하는 단계다. DEPLOY.md "폰 확인" 절에 uid 앞 4자 · 가린 메일 · 시각을 적는다.
  </how-to-verify>
  <resume-signal>"1 ○ (메일)", "3 ○", "4 ○" 또는 번호별 ×와 사진</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 브라우저 → API Gateway `POST /reference/upload-url` | Firebase ID 토큰(uid·email·email_verified)만 신뢰. 본문은 probe 플래그와 폼만 |
| Lambda → Firestore(Admin SDK) | 규칙 우회 쓰기. suppliers·supplierCodes·supplierInvites 는 서버만 쓴다 |
| 운영 터미널 → Firestore/SSM | supplier_invite.py 는 로컬 SA·AWS 자격으로 돈다 — SSM 은 읽기만(스크립트 범위). SSM 쓰기는 배포 Task 4 E0 의 v1 되돌림 한 번뿐(AWS CLI, v2 롤백 파일 보존) |
| 클라이언트 SDK → Firestore | 세 새 컬렉션은 기본 차단 규칙이 막는다(규칙 무변경) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-lfw-01 | Spoofing | accept_supplier_invite | mitigate | 초대 doc id = 정규화된 메일. 토큰 `email_verified is True` 일 때만 수락을 시도한다. 다른 계정은 다른 메일이라 남의 초대를 수락할 수 없다(Figma 반면 사례 차단). 테스트: 미인증 → accept 호출 0 |
| T-lfw-02 | Elevation | 세 컬렉션 클라이언트 쓰기 | mitigate | firestore.rules 무변경 — 맨 끝 `/{document=**}` read/write false 가 막는다. Task 4 H 에서 규칙 diff 0 을 확인한다 |
| T-lfw-03 | Info disclosure | 403 not_invited email | accept | 돌려주는 메일은 요청자 자신의 토큰 메일뿐이다. 남의 초대 존재 여부는 새지 않는다(자기 메일에 초대가 있는지만 알 수 있다) |
| T-lfw-04 | Info disclosure | 로그·기록 문서 | mitigate | 핸들러·firestore_admin 로그는 mask_email 만 쓴다(caplog 테스트). DEPLOY/SUMMARY 도 메일을 가리고 uid 는 앞 4자만 적는다. SSM v2 원문은 리포 밖 롤백 파일(600)에만 |
| T-lfw-05 | Tampering | 강사 코드 탈취·중복 | mitigate | create 가 supplierCodes 존재 여부와 다른 메일의 pending 초대 코드를 검사한다. 수락 트랜잭션은 코드 doc 이 다른 uid 것이면 SupplierCodeConflict(쓰기 0, 500) |
| T-lfw-06 | Elevation | 회수된 공급자가 다시 통과(SSM 경로·수락 초대 멱등 경로·재초대) | mitigate | suppliers doc 이 있으면 active 가 SSM·BELLE_UID 보다 우선(roster_decision 테스트). deactivate 가 같은 트랜잭션에서 수락 초대를 revoked 로, 멱등 수락 분기는 suppliers active True 일 때만, active False uid 는 어떤 초대도 수락 안 함, acceptedUid 있는 메일은 create 거부 — 되살리기는 reactivate 로만(결정 (h), fake·핸들러 끝-끝 테스트, 라이브 7·8행). 캐시 60초 지연은 수용 |
| T-lfw-07 | Repudiation | 초대 수락·회수 | mitigate | acceptedUid·acceptedAt·since·revokedAt 를 서버 시각으로 기록한다. 회수 뒤에도 acceptedUid·acceptedAt 은 이력으로 남긴다 |
| T-lfw-08 | DoS | Firestore Spark 읽기 5만/일 | mitigate | probe 한 번 = suppliers 1 읽기(uid 60초 캐시) + 명단 밖 검증 메일이면 초대 트랜잭션 읽기 ≤3(음성 캐시와 무관하게 매번 — 명단 밖 사용자는 공급자 페이지에서 A-2 에 멈추므로 호출 수가 작다) |
| T-lfw-09 | Tampering | 배포 회귀 | mitigate | 함수 zip·layer :21 zip 보존, layer 파일 sha 대조(드리프트 시 멈춤), layer 먼저 교체, 함수 하나만 재바인딩, 롤백 명령 원문 기록 |
| T-lfw-10 | Tampering | SSM supplier-uids v1 되돌림(E0) | mitigate | 쓰기 전 v2 원문을 롤백 파일(600, 리포 밖)에 정확한 put-parameter 명령으로 보존 · v1 은 get-parameter-history 버전 1 에서만 읽음 · 형태 어긋나면 멈춤 · 쓰기 뒤 재읽기 확인 · dry-run 이 uid 1개 + belle-uid 일치가 아니면 이관 전 멈춤 |
| T-lfw-11 | Elevation | 시험 코드 TESTB 가 W2 에서 실제 수강생에게 쓰임 | mitigate | Task 5 5) 에서 두 번째 계정 uid 를 deactivate → supplierCodes/TESTB active False + 초대 revoked, DEPLOY.md 에 기록 |
| T-lfw-SC | Tampering | 패키지 설치 | accept | 이 플랜은 npm/pip 설치 0 — 해당 없음 |
</threat_model>

<verification>
- backend: `cd backend && .venv/bin/python -m pytest tests -q` fail 0(전체, test_supplier_invite_script.py 포함).
- app: `npm run typecheck` exit 0 · node 테스트 6파일(supplierCopy · pickerFailure · supplierForm · supplierRules · videoDuration · videoMeta) fail 0 · `CI=1 npx expo export --platform web` 성공.
- 계약 3벌 — 파일마다 따로 건다(한 파일에만 있어도 통과하는 합산 grep 금지): `for f in docs/contract.md backend/shared/python/sunity_shared/models.py app/src/types/analysis.ts; do for t in not_invited displayName 'suppliers/' supplierCodes supplierInvites; do grep -q "$t" "$f" || echo "MISSING $t in $f"; done; done` 출력 0줄.
- 스크립트: `supplier_invite.py --help` 에 일곱 서브커맨드 · 주석 밖 put_parameter 0.
- 라이브: DEPLOY.md 표 9행 + 뒤처리 0건 + SSM 한 항목(UmH3 없음) + 롤백 파일 있음 + 웹 번들 확인.
- belle 폰 1·3·4 ○ + 오케스트레이터 5) 회수 기록(Task 5).
</verification>

<success_criteria>
- 초대받은 검증 메일은 첫 probe 한 번에 공급자가 된다. 운영이 uid 를 받아 SSM 을 고치는 절차가 사라진다. belle 두 번째 계정으로 진짜 Google 수락을 폰에서 본다(TESTB).
- 명단 밖은 모두 A-2 한 화면(로그인 메일 + 다른 계정 + 문의 2)으로 간다. belle 가 두 번째 계정으로 폰에서 확인한다.
- 회수된 공급자는 수락했던 초대·SSM·재초대 어느 길로도 다시 들어오지 못하고, reactivate 로만 되살아난다(테스트 + 라이브 7·8행).
- 홈에는 강사 코드 한 줄과 크게 보기만 있다. 큰 코드 카드·빌드 라벨은 없다. belle 가 본 계정으로 확인한다.
- supplier_invite.py 7 서브커맨드가 있고, SSM v1 되돌림 → 이관(suppliers 1건 BELLE)이 실제로 돌았다. UmH3 는 이관하지 않았고, 폰 확인 뒤 두 번째 계정 uid 는 deactivate 되어 TESTB 가 막혔다.
- 롤백 수단(보존 zip 2 + SSM v2 롤백 파일 + 명령 3종)이 DEPLOY.md 와 `/Users/Shared/sunity-motion-rollback/lfw/` 에 있다.
</success_criteria>

<output>
`.planning/quick/260930-lfw-supplier-email-invite/260930-lfw-SUMMARY.md` 를 만든다(관측 [확인]/[미확인] 과 진단을 다른 절에 — CLAUDE.md §7 보고 규칙). SUMMARY·PLAN·STATE 는 커밋하지 않는다(오케스트레이터 몫).
</output>
