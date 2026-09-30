---
phase: quick-260930-lfw
plan: 01
status: complete
subsystem: backend/reference-upload-url + app/supplier + ops scripts (Phase 38 W1)
tags: [supplier, invite, email, 38-DESIGN-v2, 38-SCENARIOS]
requires: [38-09, 38-13 Task 1, quick-260930-eal]
provides: [공급자 메일 초대(초대가 곧 검증) · A-2 초대받은 분만 · 강사 코드 한 줄 + 크게 보기 · 운영 스크립트 7종]
affects: [W2 수강생 강사 코드 입력(supplierCodes 를 읽는다) · 38-13 폰 확인 나머지 · 38-14 정은지 초대]
key-files:
  created:
    - backend/shared/python/sunity_shared/supplier_invites.py
    - backend/scripts/supplier_invite.py
    - backend/tests/test_supplier_invites.py
    - backend/tests/test_supplier_invite_script.py
    - .planning/quick/260930-lfw-supplier-email-invite/260930-lfw-DEPLOY.md
  modified:
    - backend/functions/reference-upload-url/app.py
    - backend/shared/python/sunity_shared/{models,auth,responses,firestore_admin}.py
    - docs/contract.md · app/src/types/analysis.ts
    - backend/template.yaml · backend/template-38-09-deploy.yaml (ReferenceUploadUrlFunction Timeout 30 / Memory 512)
    - app/src/app/supplier/{index,upload}.tsx · app/src/components/SupplierUi.tsx
    - app/src/constants/supplierCopy.ts(+test) · app/src/lib/{supplierRules,supplierFixtures,api}.ts
commits: [f433b6a3, 24c28248, eaef58f3, 6d93a090, c376ae02, 8c4ae364, cff7d634]
---

# quick 260930-lfw — 공급자 메일 초대 (W1)

belle 2026-09-30: *"우리가 검증할 사람을 찾아서 했다면 저런 과정은 필요없잖아"* → 리서치(Slack 메일 초대 정면 · Figma 반면) → 명세 `38-DESIGN-v2.md` §W1 → 이 작업.

## 한 것 [확인]

- **서버**: 공급자 판정이 probe 한 곳에서 초대를 수락한다.
  - 명단 = `suppliers/{uid}` doc(active 우선) ∪ SSM 하위호환.
  - 명단에 없고 `email_verified` + pending 초대 → 한 트랜잭션으로 `suppliers`·`supplierCodes`·초대 accepted.
  - 그 밖은 403 `not_invited` + 로그인 메일.
  - 회수(deactivate)는 수락 초대를 revoked 로 만들고, 되살리기는 `reactivate` 하나뿐.
  - 계약 3벌 동기.
- **운영 스크립트** `backend/scripts/supplier_invite.py`: create / extend / revoke / list / migrate-ssm / deactivate / reactivate. 코드 규칙 A–Z·2–9, 4~8자, O·0·I·1·L 금지(새 초대만. 기존 BELLE 은 이관 때 그대로).
- **화면**
  - A-2 "초대받은 분만" = 로그인 메일 + 다른 계정으로 로그인 + 카카오 채널·cs@sunity.ai 문의
  - 홈 = 큰 코드 카드·사진 제거 → `내 강사 코드` 한 줄 + [복사][크게 보기]
  - 크게 보기 모달(투명도만)
  - 빌드 라벨 제거
- **배포**
  - Lambda: layer :22, 이 함수만.
  - Timeout 30 / Memory 512 — 콜드 probe 가 10초를 넘어 belle 승인 A. 콜드 왕복 6.8초.
  - SSM 을 v1 로 되돌림. 수동으로 넣었던 두 번째 계정은 초대로 대체.
  - migrate-ssm: suppliers 1건(BELLE).
  - 웹 재배포 2회(마지막 무효화 `I7GAR3GF5UL7ASMUUGAI9OVRS2`).
  - 롤백 보존 `/Users/Shared/sunity-motion-rollback/lfw/`.
- **게이트**: backend 5676 passed / 20 skipped · typecheck 0 · node 6파일 70/70 · web export 0 · 라이브 확인 9행 전부 통과(DEPLOY F3).

## belle 폰 확인 [확인 belle]

| 단계 | 결과 | 원문 |
|---|---|---|
| A-2 두 번째 계정 | ○ | *"맞는거 같은데 카카오톡채널 문의 아래 링크 없어도 될 듯"* → 부제 제거·재배포(`cff7d634`) |
| 초대 생성(TESTB) → 새로고침 → 홈 + 코드 줄 | ○ | *"4번 5번 오케이"* — **실제 Google 계정 초대 수락** |
| 복사 · 크게 보기 | ○ | 같은 원문 |
| 두 번째 계정 권한 회수 | 실행 08:15:04Z | TESTB 비활성, 초대 revoked |

## 미확인 / 다음

- 부제를 뺀 A-2 를 belle 가 다시 보지는 않았다 [미확인].
- 콜드 컨테이너에서 **수락 쓰기**까지 하는 시간은 재지 않았다 [미확인]. 조회까지는 6.2초.
- BELLE(`FDJr…`)은 Google 로그인 수단이 없는 옛 익명 계정이다 [확인 Admin SDK]. belle 본인 Google 계정으로 공급자 페이지를 쓰려면 그 메일로 초대를 새로 만든다(코드 BELLE 을 옮길지는 belle 결정).
- 진단(재검증 대상): 콜드 10초 초과 → 6.2초는 메모리 512 로 CPU 몫이 커진 효과로 본다 [추정].
- `gradients.supplierPhotoShade` 토큰은 소비처가 0 이다(범위 밖이라 남김).
- 다음: W2 수강생 강사 코드 입력(`38-DESIGN-v2.md` §W2).
