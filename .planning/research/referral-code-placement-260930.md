# 조사 — 강사 코드(추천 코드)는 어디에 두고, 어떻게 입력받나 (2026-09-30)

> 계기: belle 2026-09-30 — *"코드 복사를 대문짝만하게 메인 홈에 … 마이페이지가 없어서 지금 이런 사단이"*.
> 단순하고 안정적으로 운영되는 실제 앱의 패턴을 찾아 38-SCENARIOS §3 초안을 판정한다.
> 표기: **[확인]** = 출처 페이지를 직접 열어 읽음(2026-09-30). **[미확인]** = 검색 요약·2차 글·일반 지식만 있음.
> 앞선 조사는 반복하지 않고 인용한다: `market-coaching-platforms-260925.md` §F-6(Kling·Ringle·Polesphere·Virtu 등),
> `260925-pln-PLAN-two-sided.md` §C-2(코드 방식 권장)·§7-4(공급자 마이페이지)·§8(메인 화면).
> 이 문서의 "판정·추천" 절은 **진단**이다. belle ○× 전에는 결정이 아니다.

---

## 0. 한 줄 판정

- **코드를 홈의 주인공으로 두는 앱은 찾지 못했다.** 추천 코드는 프로필·설정·"계정" 탭 안의 **한 줄/한 메뉴**에 있다(Peloton·Airbnb·Uber·Toss·지그재그·Whosfan).
- 예외 하나는 **"반(class)을 운영하는 교사 도구"**다(Google Classroom·Remind·Classting·ClassDojo). 여기서는 코드가 그 반의 화면이나 설정에 있다. 대신 **작은 칸 + "크게 보기(프로젝터)"** 로 둔다.
- 우리 공급자 페이지는 이 "반 화면"에 해당한다. 그래서 초안 §3 의 **"헤더 아래 작은 한 줄 + 복사"는 벤치와 맞다.** → **동의**
- 고칠 점은 넷이다.
  1. 코드 글자 규칙: 대소문자를 무시하고, 헷갈리는 글자(O/0, I/1/L)를 뺀다.
  2. 연결된 뒤 마이 탭 줄은 "정은지 강사님" 으로 바뀌어야 한다.
  3. 변경을 막는 대신 "바꾸려면 문의" 탈출구를 둔다.
  4. 연결 시각을 남겨, 나중에 보상 조건을 판정할 수 있게 한다(§7).

---

## 1. 주는 쪽(강사·교사·추천인) — 코드는 어디에 있나

| 앱 | 위치 | 형태 | 규칙 | 출처 |
|---|---|---|---|---|
| **Google Classroom** | 반 → **Settings** → General. 반의 **Stream(반 첫 화면)** 에서도 바로 "코드 표시" | 코드 + 초대 링크 복사. "Display class code" → **Full screen**(프로젝터용) | 재설정·끄기·켜기 가능("Reset / Disable / Enable invite codes") | [확인] support.google.com/edu/classroom/answer/6020282 |
| **Remind** | 반 이름 → **settings 탭**(웹). 앱은 반 이름을 탭 | `@코드` 3~10자. "add people" → **printable PDF / in-person instructions** | 교사가 언제든 바꿀 수 있다. 바꾸면 **옛 코드는 더 이상 안 된다** | [확인] help.remind.com/hc/en-us/articles/202685535 |
| **Classting**(국내) | 클래스 → **[구성원 초대하기]** 메뉴 | 코드 복사 · 초대문구(링크) 복사 · QR · 무료 문자 · **초대장 인쇄**(반 이름·코드·QR·유효기간) | 코드와 QR 은 **30일 유효**. 재발급하면 이전 코드·QR 이 무효. 기존 구성원에는 영향 없음 | [확인] support.classting.com/hc/ko/articles/15024932636569 · /16062564662937 |
| **ClassDojo** | 반 → **Invite Families** 패널 | 개인 코드 인쇄물 · 메일/문자 초대 · 반 링크 · **반 QR "Display code"** | 화면 QR 은 **7일 뒤 자동 만료**. 인쇄 QR·반 링크는 **교사 승인 뒤** 연결 | [확인] help.classdojo.com/hc/en-us/articles/202794025 |
| **Kahoot** | 호스트가 게임을 시작하면 **호스트 화면**에 PIN | PIN + 참가 링크 + QR | 세션마다 새 PIN(최대 8시간). "Lock game joining" 가능 | [확인] support.kahoot.com/hc/en-us/articles/360000109048 |
| **Duolingo for Schools** | 교사 웹 → Students 탭 → Manage Students → **Add Students** 창 | 반 링크, 링크 끝 6자가 코드 | (2027-07-31 서비스 종료 예정이라는 검색 요약 있음) | [확인] duolingoschools.zendesk.com/…/6845646493965 · 종료 [미확인] |
| **Peloton** 추천 | 설정 URL `/settings/referrals` · 웹 ≡ 메뉴 "Refer friends" · 앱은 **메뉴 3곳**(Community "Add Friends", You → more, 프로필 아이콘 → 맨 아래) | 링크(코드 아님) | 연 4명 한도. 쿠폰 사이트 게시 등은 남용으로 본다 | [확인] support.onepeloton.com/s/article/204445185 |
| **Airbnb** 추천 | **프로필 → 친구 추천하기** → 초대 링크 공유 | 링크 | 연 10건 보상 한도. 친구 대신 계정을 만드는 것 금지 | [확인] airbnb.co.kr/help/article/84 · /3613 |
| **Uber(한국)** 추천 | 앱 아래쪽 **계정 → 친구 초대하고 혜택받기** | 링크 | 친구가 첫 이용을 마친 뒤 보상. 최대 100명. 이용 이력 없는 사람만 | [확인] uber.com/kr/ko/referral |
| **토스** 초대 이벤트 | 이벤트 홈 → **설정** → 친구 초대 → 9자리 코드 | 코드 | 받는 사람은 가입 후 24시간 안에 입력. 탈퇴 이력이 있으면 지급 없음 | [확인] support.toss.im/faq/4689 |
| **Whosfan**(국내) | **마이 페이지 → Referral Code 버튼**(누르면 클립보드 복사) | 버튼 하나 | 받는 사람은 **가입 때 한 번만** 입력 | [확인] hanteo.zendesk.com/…/360032937532 |
| **Everfit**(코치 도구) | 관리자 **Team Page** 에서 코치별 초대 링크 | 링크 | 링크로 가입하면 그 코치에게 배정. 좌석이 차면 "Waiting Activation" | [확인] help.everfit.io/en/articles/5369004 |
| **Trainerize / TrueCoach**(코치 도구) | 코치가 고객 목록에서 **+ New / Add Client**(메일 입력) | 메일 초대. 링크 복사로 재전송 | 코드 없음. Trainerize 초대 링크는 30일 만료 | [확인] help.trainerize.com/…/31088360792980 · help.truecoach.co/…/2403903 · 30일 [미확인] |
| Kling 추천 | 초대 페이지 `kling.ai/app/invitation` | 코드 + 링크 | 친구가 **첫 유료 구매** 뒤 보상(검색 요약) | [미확인] 페이지가 스크립트 렌더라 본문을 못 읽음. §F-6 은 belle 관측 |
| 당근·배민·쿠팡 | — | — | 공식 도움말에서 코드 위치를 찾지 못함. 배민은 "선물코드 등록 = My배민 → 받은 선물" 뿐 | [미확인] |
| Strava 클럽 · Mindbody/Glofox | 클럽 링크 공유 / 스튜디오는 검색·전용 앱 | 링크 | 코드 방식이 아님 | [미확인] |

**관측 요약** (위 표의 [확인] 행만 셈)
- **추천 보상형**(Peloton·Airbnb·Uber·Toss·Whosfan): 11곳 중 5곳. 모두 **프로필·계정·설정 메뉴 안**에 있고, 홈 카드는 0곳이다.
- **반 운영형**(Classroom·Remind·Classting·ClassDojo·Kahoot): 모두 **그 반의 화면이나 설정**에 있다.
  - "크게 보여 주기"는 따로 누르는 기능이다(Full screen · Display code · 호스트 화면 · 인쇄물).
  - 기본 화면에서 코드는 작다. Classroom 은 Stream 의 작은 칸이다 [확인: "you can quickly display the code from the Stream page"].
- **코치 도구**(Trainerize·TrueCoach·Everfit)는 코드가 아니라 **메일 초대/링크**다. 강사가 할 일이 는다.

---

## 2. 받는 쪽(수강생) — 어디서 입력하고, 무엇이 되나

| 앱 | 입력 위치 | 때 | 바꾸기 | 연결 뒤 | 출처 |
|---|---|---|---|---|---|
| **Duolingo** | 앱 **프로필 → 톱니(설정) → "Duolingo for Schools"(정보 바로 아래 첫 버튼)** → 코드 입력 | 가입 뒤 아무 때나 | 반 나가기 있음 | 반에 들어감 | [확인] duolingoschools.zendesk.com/…/6845646493965 |
| **Google Classroom** | 상단 **Join class** → 코드 | 아무 때나 | 여러 반 가능 | 반 목록에 추가 | [확인] support.google.com/edu/classroom/answer/6020297 |
| **Classting** | 클래스 가입 화면에서 코드 | 아무 때나(유효기간 안) | — | 클래스 구성원 | [확인] support.classting.com/…/8014374775065 |
| **Toss** | **전체 탭 → "초대 코드 입력하기"** | 가입 후 **24시간 안** | — | 포인트 지급 | [확인] support.toss.im/faq/4689 |
| **지그재그** | **마이페이지 → 오늘의 혜택 → 친구초대 → 나의 초대 현황 → 초대 코드 입력하기** | 가입 후 **7일 안**, 최초 가입자만 | — | "리워드 지급 팝업" | [확인] zigzagkr.zendesk.com/…/5322080755486 |
| **Whosfan** | **가입 화면** | 가입 때만. 놓치면 끝 | 불가(코드 하나) | — | [확인] hanteo.zendesk.com/…/360032937532 |
| Uber · Airbnb · Peloton | 입력 칸 없음. **링크를 눌러 가입/구매**하면 자동 적용 | 링크를 탈 때만(Peloton "cannot be applied retroactively") | — | 쿠폰 자동 표시 | [확인] 위 §1 출처 |

**오류 경우와 문구** (원문 요지 → 우리 말로 옮긴 예)

| 경우 | 실제 앱 | 우리 문구 예 |
|---|---|---|
| 형식 틀림·오타 | Classroom: 6~8자 영숫자·공백 불가, 대소문자 확인 [확인]. Classting: **O/0, 1/L/I 혼동** 확인, 6자리 [확인] | "코드를 다시 확인해 주세요 (예: EUNJI)" |
| 없는 코드 | Classroom: 맞게 넣었는데 안 되면 "contact your teacher" [확인] | "없는 코드예요. 강사님께 코드를 다시 물어봐 주세요" |
| 만료·재발급된 코드 | Classting 30일·재발급 시 무효 [확인] · ClassDojo 30일 [확인] · Kahoot 세션 종료 [확인] | (실증은 만료 없음 → 해당 없음) |
| 사용 한도 초과 | ClassDojo 코드당 4회 · 학생당 가족 4명 [확인] | (강사 코드는 인원 무제한 → 해당 없음) |
| 이미 연결됨 | Whosfan "only one referral code" [확인] | "이미 ○○ 강사님과 연결돼 있어요" |
| 자기 추천 | Airbnb 약관: 추천인이 대신 계정 생성·예약 금지 [확인] | "본인 코드는 넣을 수 없어요" |
| 기간 지남 | Toss 24h · 지그재그 7일 · 재가입/탈퇴 이력 불가 [확인] | (실증은 기간 제한 없음) |
| 막혔을 때 | ClassDojo "submit a request … we can reset the code on our end" [확인] | "해결이 안 되면 운영팀에 알려 주세요" + 문의처 |

---

## 3. 코드 · 링크 · QR — 학원 현장(강사가 말로 불러 줌)에서 무엇이 가장 안정적인가

| 수단 | 현장에서 | 운영 부담(딥링크 인프라 없음 전제) | 실패 방식 | 사례 |
|---|---|---|---|---|
| **짧은 코드** | 말로 불러 주고, 칠판·단톡에 적는다 | **0**. 문자열 비교뿐 | 오타. 설치 뒤 잊음 | Classroom·Remind·Classting·Kahoot PIN [확인] |
| 링크 | 단톡방에 붙여넣기 | 설치를 거치면 맥락이 끊긴다 → 지연 딥링크 서비스가 필요 [미확인: 일반 지식. Firebase Dynamic Links 는 2025 종료로 알려짐] | 설치 뒤 귀속 누락 | Uber·Airbnb·Peloton [확인] — 모두 앱 설치 이전 웹 단계에서 적용 |
| QR | 화면·인쇄물을 비춘다 | QR 이 링크를 담으면 링크와 같은 문제. **코드를 적은 안내 페이지로 보내는 QR** 이면 부담 0 | 카메라·조명 | ClassDojo Display code(7일)·Classting 초대장 [확인] |

**판단(진단)**
- 실증 = **코드 하나**다.
- 반 운영형 앱들도 코드를 기본으로 두고, 링크·QR·인쇄물을 **위에 얹는다**(Classting 4종, ClassDojo 4종, Kahoot 3종 [확인]).
- 링크·QR 의 귀속은 끝 그림에서 다룬다. 그때도 **코드가 바닥**이다. 링크를 타면 코드를 미리 채워 주는 수준이면 충분하다.

---

## 4. 값싼 어뷰징 방어 — 실제 규칙

| 규칙 | 사례 [확인] | 우리 비용 |
|---|---|---|
| 수강생 1명 = 연결 1개(첫 코드) | Whosfan "only one referral code" | 필드 하나(`attribution` 이 있으면 거절) |
| 자기 추천 금지 | Airbnb 약관 | `supplierUid == uid` 비교 |
| **보상은 첫 실사용 뒤** | Airbnb 첫 여행 · Uber 첫 이용 · Peloton 첫 하드웨어 구매 · Kling 첫 구매 [미확인] · Virtu 첫 결제(§F-6) | 첫 분석 완료 시각 하나. 실증은 보상 없음 → 시각만 기록 |
| 신규만(재가입·탈퇴 이력 제외) | Toss · 지그재그 · Peloton "must be a new customer" | 끝 그림. 익명 게스트를 여러 개 만드는 것을 막는 문제와 같음 |
| 입력 기간 창 | Toss 24h · 지그재그 7일 | 끝 그림 보상 조건으로만. 연결 자체엔 두지 않음(§6) |
| 추천인당 보상 상한 | Peloton 연 4 · Airbnb 연 10 · Uber 100명 | 끝 그림. 강사당 월 상한 한 줄 |
| 대량 살포 금지 | Peloton: 쿠폰 사이트 게시 = 남용 | 약관 문장 하나 |
| 입장 잠금·승인 | Kahoot Lock · ClassDojo 승인 | 쓰지 않음(강사 일이 는다) |

---

## 5. 가장 단순하고 안정적인 조합 (추천 — 진단)

**실증 (2026-10)**
1. **공급자 페이지**: 헤더 아래 **한 줄** `내 추천 코드 EUNJI [복사]`. 사진·큰 카드는 없다.
   - 선택: `[크게 보기]` 하나. 수업 중에 폰·태블릿을 들어 보여 주는 용도다. 버튼 하나, 전체 화면 흰 배경에 코드만 띄운다. Classroom Full screen · ClassDojo Display code 형이다.
2. **코드 모양**: 강사 이름을 딴 고정 코드다(Remind `@코드` 형).
   - 대문자만 쓴다. 입력은 대소문자를 무시하고 앞뒤 공백을 없앤다.
   - O·0·I·1·L 이 섞이지 않게 만든다(Classting 혼동 사례).
   - 만료는 없다. 운영자만 바꿀 수 있다.
3. **수강생 앱**: 마이 탭 한 줄 `강사 코드 입력 >` → 시트(입력 칸 + [연결]).
   - Duolingo "프로필 → 설정 → 첫 버튼", Toss "전체 → 초대 코드 입력하기" 와 같은 층이다.
   - 연결 뒤 그 줄은 `강사  정은지 강사님` 표시로 바뀐다(탭하면 안내만 보이고 변경은 없다).
4. **규칙 3개만**: 없는 코드 / 이미 연결 / 본인 코드. 기간 창, 만료, 승인은 없다.
5. **기록**: `users/{uid}.attribution = { supplierId, code, linkedAt }`. 첫 분석 시각은 이미 analyses 에 있다. 보상을 소급할지, 조건을 어떻게 둘지는 나중에 판단할 수 있다.

**끝 그림**
- 코드 위치를 공급자 마이페이지 "내 코드" 행으로 옮긴다(§7-4). 기능은 복사 · 공유 · 크게 보기 · 인쇄 안내문(Remind in-person instructions / Classting 초대장).
- 링크·QR 은 코드 위에 얹는다. 링크를 타면 시트에 코드를 **미리 채워 주기만** 한다. 귀속의 정본은 여전히 코드 입력이다.
- 받는 쪽 입력 자리를 더 둔다: 가입 직후 한 번("강사님께 받은 코드가 있나요? 건너뛰기"), 그리고 마이 탭. 두 자리가 같은 시트를 연다.
- 변경은 확인 뒤 허용하고 이전 기록을 남긴다(§C-2 원안).
- 보상(+2/+2)은 첫 분석 완료 뒤 지급한다. 조건은 "연결이 첫 분석 **전**" 또는 "가입 N일 안"(Toss·지그재그 형)이다. 강사당 상한을 둔다(Peloton·Airbnb 형).

---

## 6. 가져오지 않는 것

- **홈 히어로 카드로서의 코드**: 조사한 앱 중 홈 주인공으로 둔 곳이 없다(§1 요약).
- **가입 때만 입력**(Whosfan) **/ 24시간·7일 창**(Toss·지그재그): 우리 수강생은 설치하고 며칠 뒤 수업에서 코드를 듣는다. 입력 창을 닫으면 귀속이 조용히 빠진다. 창은 보상 조건에만 쓴다(끝 그림).
- **30일 만료·재발급 코드**(Classting·ClassDojo), **세션 PIN**(Kahoot):
  - 학교는 아동 보호 때문에 반 입장을 좁힌다.
  - 우리 코드는 강사가 몇 달 동안 입으로 되풀이하는 이름표라, 만료되면 현장에서 깨진다.
- **공급자가 코드를 스스로 바꾸기**(Remind: 바꾸면 옛 코드 무효): 이미 말로 퍼진 코드가 죽는다. 실증에서는 운영자만 바꾼다.
- **승인 대기**(ClassDojo 반 링크): 강사가 할 일이 는다. 강사 코드 연결은 권한이 아니라 귀속이다. 틀려도 피해가 작으므로 승인 없이 연결한다.
- **메일 초대로 고객 등록**(Trainerize·TrueCoach): 강사가 수강생 연락처를 입력해야 한다. §C-2 (d) 로 끝 그림에서만 병행한다.
- **링크만으로 귀속**(Uber·Airbnb·Peloton): 웹 단계에서 적용되는 구조라, 앱 설치를 거치는 우리에게는 딥링크 인프라가 필요하다(§3).

---

## 7. 초안 38-SCENARIOS §3 판정

| # | 초안 | 판정 | 무엇을 바꾸나 / 근거 |
|---|---|---|---|
| R1 | 큰 카드 제거 → 헤더 아래 작은 한 줄 `내 추천 코드 BELLE [복사]`. 사진 카드 제거 | **동의** | Classroom Stream 의 작은 칸, Whosfan 마이 버튼 하나와 같은 형이다. **추가 제안**: `[크게 보기]` 버튼 하나(선택, belle ○× 대상). 라벨은 R2 와 같은 말로 맞출지 정해야 한다 — 수강생 쪽이 "강사 코드"면 공급자 쪽도 **"내 강사 코드"** 가 짝이 맞는다 |
| R2 | 앱 마이 탭 "강사 코드" 줄 → 입력 시트 → "김서니 강사님과 연결됐어요" | **동의 + 1** | Duolingo·Toss·지그재그와 같은 층이다. **추가**: 연결 뒤 줄이 `강사 · 정은지 강사님` 으로 바뀐다(연결 상태가 보여야 R4 문의가 줄어든다). 입력 전 줄의 문구는 "강사님께 받은 코드 입력" |
| R3 | 없는 코드 문구 | **동의 + 1** | 입력 정규화(대문자로 바꾸기·공백 제거)를 넣는다. 코드 생성 때 O/0/I/1/L 을 피한다(Classting) |
| R4 | 실증은 변경 막음 "이미 ○○ 강사님과 연결돼 있어요" | **동의 + 1** | 탈출구 문장 "바꾸려면 운영팀에 알려 주세요" 를 붙이고, 운영 스크립트로 해제한다(ClassDojo "we can reset … on our end" 형). 막기만 하면 오입력 1건이 영구 귀속이 된다 |
| R5 | 본인 코드 입력 막음 | **동의** | Airbnb 약관과 같은 방향. 비교 한 줄이면 된다 |
| R6 | 게스트도 입력 가능(uid 불변) | **동의** | 입력 창을 닫지 않는 이유와 같다(§6) |
| R7 | 크레딧은 만들지 않음, 연결 기록만 | **동의 + 1** | `linkedAt` 을 반드시 남긴다. 끝 그림 보상 조건("연결이 첫 분석 전인가")을 소급 판정하려면 이 시각이 필요하다. 첫 분석 시각은 analyses 에서 읽는다 [미확인: 필드명은 코드 대조 전] |
| R8 | 초대 때 코드도 정한다 | **동의** | Remind 형 고정 코드. 공급자가 직접 바꾸는 기능은 두지 않는다 |
| 링크 전용·크레딧 없음·1회 | (지시문 요약) | **동의** | §3: 실증은 코드 하나가 가장 안정적이다. 링크·QR 은 끝 그림에서 코드 위에 얹는다 |

**belle 에게 물을 것(○×)**
1. 공급자 쪽 라벨: "내 추천 코드" vs **"내 강사 코드"**(수강생 쪽과 같은 말).
2. `[크게 보기]` 버튼을 실증에 넣을지.
3. 수강생 연결 해제는 운영팀 문의로만 할지(앱에는 변경 버튼 없음).

---

## 8. 출처 (2026-09-30 열람)

- Google Classroom 교사: https://support.google.com/edu/classroom/answer/6020282 [확인]
- Google Classroom 학생: https://support.google.com/edu/classroom/answer/6020297 [확인]
- Remind 코드 변경: https://help.remind.com/hc/en-us/articles/202685535-How-do-I-change-my-class-code [확인]
- Classting 코드 초대: https://support.classting.com/hc/ko/articles/15024932636569 [확인]
- Classting 초대장 인쇄: https://support.classting.com/hc/ko/articles/16062564662937 [확인]
- Classting 가입 불가: https://support.classting.com/hc/ko/articles/8014374775065 [확인]
- ClassDojo 가족 초대: https://help.classdojo.com/hc/en-us/articles/202794025-Invite-Families-to-ClassDojo [확인]
- ClassDojo 부모 코드 문제: https://help.classdojo.com/hc/en-us/articles/29014748010381-Troubleshooting-Parent-Codes [확인]
- Kahoot PIN: https://support.kahoot.com/hc/en-us/articles/360000109048-How-to-find-Kahoot-PIN [확인]
- Duolingo for Schools: https://duolingoschools.zendesk.com/hc/en-us/articles/6845646493965 [확인]
- Peloton 추천: https://support.onepeloton.com/s/article/204445185-Refer-A-Friend [확인]
- Airbnb 추천: https://www.airbnb.co.kr/help/article/84 · 약관 https://www.airbnb.co.kr/help/article/3613 [확인]
- Uber 한국 추천: https://www.uber.com/kr/ko/referral [확인]
- 토스 초대 코드: https://support.toss.im/faq/4689 [확인]
- 지그재그 초대 코드: https://zigzagkr.zendesk.com/hc/ko/articles/5322080755486 [확인]
- Whosfan 추천 코드: https://hanteo.zendesk.com/hc/en-us/articles/360032937532 [확인]
- Everfit 코치 링크: https://help.everfit.io/en/articles/5369004-public-client-invite-link [확인]
- Trainerize 고객 추가: https://help.trainerize.com/hc/en-us/articles/31088360792980 [확인]
- TrueCoach 고객 추가: https://help.truecoach.co/en/articles/2403903-adding-a-new-client [확인]
- Kling 초대: https://kling.ai/app/invitation [미확인 — 본문 렌더 불가, 검색 요약만]
