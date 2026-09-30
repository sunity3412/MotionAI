# 38 공급자 링크 v2 — 메일 초대 + 강사 코드 (2026-09-30)

> 결정 정본 = `38-SCENARIOS.md` 맨 위 "리서치 반영판" + "belle 결정 (2026-09-30, 확정)".
> 시각 정본 = Figma `jrdI7kp245HkPfLB0nclsz` 섹션 `282:506` v2 프레임. 실행기는 Figma 를 못 연다. 이 파일이 그 값을 옮겨 적은 것이다.
> v1 명세 `38-DESIGN.md` 는 그대로 유효하다. 이 파일은 바뀌는 곳만 적는다.
> belle 가 v2 시안에 "오케이 일단 고"(2026-09-30).
> 시안 글꼴은 Noto Sans KR 이다. 코드는 Pretendard 를 유지한다.

## W1. 공급자 메일 초대 (공급자 페이지 + 서버 + 운영 스크립트)

### 데이터 (제안 — 플래너가 코드 대조 뒤 확정하고, 바꾸면 이유를 적는다)
- **`supplierInvites/{emailLower}`** — 클라이언트 읽기·쓰기 금지(Admin 만)
  - 필드: `email` · `code` · `displayName`(선수 이름) · `createdAt` · `expiresAt`(기본 +14일) · `status`(`pending`|`accepted`|`revoked`) · `acceptedUid` · `acceptedAt`
- **`suppliers/{uid}`** — 공급자 명단의 새 정본. 클라이언트는 본인 doc 만 읽는다.
  - 필드: `email` · `code` · `displayName` · `active` · `since`
- **`supplierCodes/{CODE}`** — 코드로 공급자를 찾는 표. 로그인한 사용자는 읽을 수 있고, 쓰기는 금지.
  - 필드: `supplierUid` · `displayName` · `active`
  - W2 의 코드 조회가 이 doc 을 읽는다.
- 코드 규칙
  - 대문자 A–Z·2–9, 4~8자.
  - O·0·I·1·L 금지(Classting 이 오타 원인으로 짚음, 리서치 [확인]).
  - 중복 금지. 스크립트가 검사한다.
- **기존 SSM `supplier-uids` 명단**(`FDJr…:BELLE`, `UmH3…`)은 하위 호환으로 **계속 인정한다**(합집합).
  - 이관 스크립트로 `suppliers`·`supplierCodes` 에 옮긴다.
  - SSM 을 없애는 것은 이관을 확인한 뒤 따로 한다(이번 범위 밖).

### 서버 — 확인(probe) 한 곳에서 수락
- 경로: 지금의 `POST /reference/upload-url {probe:true}`(`backend/functions/reference-upload-url/app.py`)
- 판정 순서
  1. uid 가 명단(`suppliers` active 또는 SSM)에 있음 → 200 `{status:'supplier', code, displayName}`. **초대 상태와 무관하게 항상 홈.**
  2. 명단에 없음 + 토큰의 `email_verified == true` + `supplierInvites/{email}` 이 `pending` 이고 만료 전 → **수락**. 한 트랜잭션에서 아래를 모두 한다.
     - `suppliers/{uid}` 생성
     - `supplierCodes/{code}` 생성
     - 초대를 `accepted` 로 바꾸고 `acceptedUid`·`acceptedAt` 기록
     - 그 뒤 1 과 같은 응답
  3. 그 밖(초대 없음·만료·취소·메일 미인증) → 403 `{error:{code:'not_invited', email:<로그인 메일>}}`
     - 화면은 하나다. 만료와 없음을 나누지 않는다(리서치 권고).
- 업로드(비-probe) 권한도 같은 명단 판정을 쓴다.
- 명단 캐시(60초)는 수락 직후 그 uid 에 대해 무효화한다.
- 계약 3벌(`contract.md` · `models.py` · `analysis.ts`)을 같이 고친다.
- `forbidden` 코드 대신 `not_invited` 를 쓴다. 기존 `forbidden` 을 받는 앱 코드도 함께 정리한다.
- 배포: CFN 변경(Lambda 에 Firestore 쓰기 권한이 이미 있는지 먼저 확인)이 있으면 **belle 체크포인트**를 둔다. 코드만 바뀌면 38-09 절차(zip 보존 + 롤백 명령)로 한다.

### 운영 스크립트 (`backend/scripts/supplier_invite.py`)
- `create --email x@gmail.com --code EUNJI --name 정은지 [--days 14]`
  - 코드 규칙과 중복을 검사한다. 출력: 공급자에게 보낼 링크와 안내 문장 두 줄.
- `extend --email … [--days 14]` · `revoke --email …` · `list`
- `migrate-ssm`: SSM 명단을 `suppliers`/`supplierCodes` 로 옮긴다.
  - 코드 없는 uid 는 코드 없이 옮긴다. 화면에는 코드 줄이 없다.
- `deactivate --uid …`: 공급자 권한을 회수한다(S9).
- 순수 함수(코드 검증·만료 판정)는 pytest 로 잠근다.

### 화면 (Figma v2)
**A-2 초대받은 분만** (`283:543` v2) — 로그인했는데 403 `not_invited` 일 때
- 워드마크 → 32 → 알림 아이콘 44 → 16 → 제목 30/700 `초대받은 분만 쓸 수 있어요` → 8
- 본문 17 #5A5A5A `공급자 페이지는 Sunity 가 초대한 강사·선수만 쓸 수 있어요. 초대받으셨다면 초대받은 Google 계정으로 로그인해 주세요.` → 24
- 회색 면(#F5F5F5, 반경 13, 패딩 14 16): `지금 로그인한 계정` 15 #5A5A5A / 메일 17/700 → 12
- 주 CTA 54 `다른 계정으로 로그인`(signOut → A-1) → 40
- `초대가 필요하거나 계정이 헷갈리면` 17/700 → 4 → `아래로 알려 주세요. 운영팀이 확인해 드려요.` 15 #5A5A5A → 12
- 문의 행 2개(1px #D9D9D9, 반경 13, 패딩 12 16, 간격 8)
  - 아이콘 32 + 제목 17/700 / 부제 15 #5A5A5A + 쉐브론 20 #B1B6BE
  - ① 카카오 아이콘(노란 #FEE500 사각 반경 8) `카카오톡 채널로 문의` / `pf.kakao.com/_CyNxkn` → `http://pf.kakao.com/_CyNxkn` 새 창
  - ② 메일 아이콘(#F5F5F5 사각) `메일로 문의` / `cs@sunity.ai` → `mailto:cs@sunity.ai`
  - 카카오 노랑은 브랜드 예외(외부 서비스 식별). 토큰 1개로 추가한다.
- **없앤다**: 내 ID 상자, `ID 복사`, `등록 확인하기`, 힌트, 기존 `noAccess.*` 문구 중 쓰지 않는 것.

**A-3 홈** (`284:528` · `288:539` v2)
- **없앤다**: `내 코드` 카드 전체(사진·오버레이·코드·코드 복사·안내), `빌드` 라벨(전 화면)
- 시트 맨 위(`내 동작` 카드 위, 간격 12)에 **강사 코드 줄**을 둔다. 코드가 있을 때만 보인다.
  - 흰 면, 1px #D9D9D9, 반경 15, 패딩 12 12 12 16, 가로 정렬
  - 왼쪽 세로: `내 강사 코드` 13 #5A5A5A / 코드 20/700 #FF4B33 자간 +6%
  - 오른쪽 알약 버튼 2개(높이 36, 반경 18, 1px #B1B6BE, 라벨 15/700, 좌우 패딩 14, 간격 8)
    - `복사` → 클립보드 + 토스트 `복사됐어요`
    - `크게 보기`

**크게 보기** (`299:666`, 새 화면, 전체 화면 모달)
- 흰 바탕, 오른쪽 위 X 28(누르면 닫힘, ESC 도 닫힘)
- 세로 가운데 정렬:
  - `{displayName} 강사님의 코드` 20/700 #5A5A5A → 16
  - 코드 72/700 #FF4B33 자간 +8% → 24
  - `Sunity 앱 → 마이 → 강사 코드에\n이 코드를 넣어 주세요` 17 #5A5A5A 가운데
- 움직임: 열림·닫힘은 투명도만 바꾼다(reduced-motion 과 같게).

## W2. 수강생 강사 코드 입력 (앱 마이 탭)

### 동작
- 코드 조회: `supplierCodes/{정규화된 코드}` get
  - 정규화 = 공백 제거 + 대문자
  - 없음 또는 `active != true` → "없는 코드"
- 연결 저장: `users/{uid}` 아래 한 곳(플래너가 기존 구조를 보고 정한다. 예: `users/{uid}/private/instructorLink`)
  - 필드: `{code, supplierUid, displayName, linkedAt: serverTimestamp}`
- 규칙(firestore.rules)
  - **create 만** 허용, update·delete 는 금지(한 번만).
  - `supplierUid != request.auth.uid`(본인 코드 금지).
  - 코드가 `supplierCodes` 에 실제로 있는지 규칙에서 `exists()` 로 확인한다.
  - 규칙은 38-09 와 같이 **belle 콘솔 게시**로 올린다(Admin SA 로 `--release` 는 403 이었다). 게시 전 규칙 파일과 라이브 probe 계획을 준비한다.
- 해제는 운영 스크립트 `backend/scripts/instructor_link.py unlink --uid …`(ClassDojo 형 운영 해제).
- 게스트(익명) 수강생도 된다. uid 기준이고, 로그인해도 uid 는 바뀌지 않는다(메모리 login-gate).
- 크레딧은 만들지 않는다(실증 무료). `linkedAt` 만 남긴다.

### 화면 (Figma v2, 기존 `app/src/app/(tabs)/profile.tsx` 의 강사 코드 행 자리)
1. **미연결 행**: 기존 행 모양 그대로.
   - 왼쪽 `강사 코드`(#767676)
   - 오른쪽 `입력하기` 17/700 #FF4B33 + 쉐브론(브랜드)
   - 행 아래 힌트 15 #767676 `수업에서 받은 코드를 넣으면 강사님과 연결돼요.`
   - 행 전체를 누르면 시트가 열린다.
2. **입력 시트**(아래에서 올라옴, 뒤 막 `brandOverlay` 40%, 위 반경 20, 그랩바 36×5 #D9D9D9, 패딩 20, 아래 34)
   - `강사 코드 입력` 20/700 → 4 → `수업에서 받은 코드를 넣어 주세요. 대소문자는 상관없어요.` 15 #5A5A5A → 20
   - 입력칸 54: 포커스 테두리 브랜드, 값 20 자간 +6%, 자동 대문자, 자동 수정 끔 → 20
   - 주 CTA `확인`(빈 칸이면 비활성)
3. **오류** — 입력칸 테두리 #54B8CD, 입력칸 아래 8 에 #2C7C8C 15
   - 없는 코드: `없는 코드예요. 강사님께 받은 코드를 다시 확인해 주세요.`
   - 본인 코드: `본인 코드는 넣을 수 없어요.`
   - 네트워크: 기존 offline 문구
4. **강사 확인**(같은 시트, 코드가 맞은 뒤)
   - 원형 64 #FFE3DF → 12 → `{displayName} 강사님` 20/700 → 4 → `코드 {CODE}` 15 #767676 → 16
   - 회색 면 `연결은 한 번만 할 수 있어요. 나중에 바꾸려면 cs@sunity.ai 로 알려 주세요.` 15 #5A5A5A → 20
   - 주 CTA `연결하기` → 12 → `취소` 17 #5A5A5A 밑줄
5. **연결됨 행**
   - 오른쪽이 세로 두 줄: `{displayName} 강사님` 17/700 / 코드 13 #767676. 쉐브론 없음, 누를 수 없음.
   - 힌트 `바꾸려면 cs@sunity.ai 로 알려 주세요.`
   - 연결 직후 토스트 `{displayName} 강사님과 연결됐어요`(탭바 위)
- 문구는 기존 `profileCopy.instructorCode` 를 확장한다. 한국어 리터럴은 화면에 두지 않는다.
- 배포: 앱 변경이다. **시뮬레이터 확인 → belle 확인 → OTA**(메모리 verify-ui-on-simulator-before-ota).

## 순서
1. W1 → 공급자 웹 재배포(sync + invalidation) → belle 가 A-2(두 번째 계정) · 홈 코드 줄 · 크게 보기를 폰으로 확인
2. W2 → 규칙 게시(belle 콘솔) → 시뮬레이터 → OTA
3. 38-13 폰 확인 나머지(올리기 STEP 01/02 · 가이드) → 38-13 마무리
4. 정은지 선수 메일을 받아 초대를 만든다 → 38-14
