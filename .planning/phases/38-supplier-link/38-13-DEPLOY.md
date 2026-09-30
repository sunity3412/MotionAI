# 38-13 배포 기록 — 공급자 링크 HTTPS (S3 정적 버킷 + CloudFront OAC)

- 실행: 2026-09-30 01:47~01:55 UTC (10:47~10:55 KST), 실행자 = gsd-executor (opus)
- 계정 976369350031, 사용자 `arn:aws:iam::976369350031:user/sunity-motion`, `AWS_PROFILE=sunity-motion`, 버킷 리전 ap-northeast-2 (CloudFront 는 글로벌)
- 빌드 기준 코드: HEAD `12cbc972` (quick 260930-eal 로 Figma 282:506 시안 반영된 화면) + `app/app.json` `web.output: "single"` 명시(이 플랜 Task 1 커밋)
- 38-04 결정 = option-1(Expo Router web export). 링크 = `/supplier`
- 영상 버킷 `sunity-motion-pilot-videos` 는 건드리지 않았다(정책·알림·CORS 조회도 쓰기도 0)

**Authorized domains 에 넣을 도메인: `d2ivnoigym2xlu.cloudfront.net`**

링크(belle·정은지에게 줄 한 장): `https://d2ivnoigym2xlu.cloudfront.net/supplier`

## 리소스

| 리소스 | 값 | 이 플랜이 새로 만듦(a) / 재사용(b) |
|---|---|---|
| S3 버킷 | `sunity-motion-pilot-supplier-web` (ap-northeast-2, 퍼블릭 차단 4개 true, BucketOwnerEnforced, SSE AES256 기본) | (a) 신규 |
| 버킷 정책 | `infra/supplier-bucket-policy.json` — Principal `cloudfront.amazonaws.com`, `s3:GetObject`, `AWS:SourceArn` = 아래 distribution ARN | (a) 신규 (버킷과 함께 생김) |
| 버킷 객체 | `app/dist` 60개, 19,259,239 bytes | (a) 신규 |
| OAC | `sunity-supplier-oac` Id `EDVM240S2C0RM` (s3 · sigv4 · always) | (a) 신규 |
| CloudFront distribution | Id `E16SR4IPFYH46Q`, ARN `arn:aws:cloudfront::976369350031:distribution/E16SR4IPFYH46Q`, 도메인 `d2ivnoigym2xlu.cloudfront.net`, Comment `Phase 38 supplier link` | (a) 신규 |
| 무효화 | `I4GUC7WPFFGQSOLCJ5WUHEK98I` `/*` → Completed | — |

재사용 리소스는 0개다. 그래서 `infra/cloudfront-before.json` · `infra/supplier-bucket-policy-before.json` · `/Users/Shared/sunity-motion-rollback/38-13/site-before/` 는 만들지 않았다(복원할 원본이 없다). 롤백은 전부 (a) 삭제다.

## 읽기 먼저 (멱등 확인, 01:47:56Z — 어떤 쓰기보다 앞)

```
aws sts get-caller-identity           → 976369350031  user/sunity-motion
aws s3api head-bucket --bucket sunity-motion-pilot-supplier-web
                                      → (404) Not Found, exit 254   → 생성 진행
aws cloudfront list-origin-access-controls --query "...[?Name=='sunity-supplier-oac'].Id"
                                      → None                        → 생성 진행
aws cloudfront list-distributions --query "...[?Comment=='Phase 38 supplier link'].[Id,DomainName]"
                                      → None                        → 생성 진행
aws cloudfront list-distributions (전체) → None  (이 계정에 distribution 이 하나도 없었다)
```

다시 돌리면: head-bucket 200 · OAC Id `EDVM240S2C0RM` · distribution `E16SR4IPFYH46Q` 가 나오므로 생성 단계는 건너뛰고 sync + invalidation 만 하면 된다.

## 명령 (실행 순서 원문)

```bash
export AWS_PROFILE=sunity-motion

# 1. 빌드 (app/, 10초, exit 0)
cd app && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist
#   → index.html 1개(SPA), entry-768b3ad2388b38b80c0cc9e841589d53.js 2.95 MB, du -sh dist = 19M, 파일 60개
#   번들 해시가 quick-260930-eal 때와 같다 = web.output "single" 명시는 기존 기본값과 같은 산출

# 2. 버킷 (01:48:41Z)
aws s3api create-bucket --bucket sunity-motion-pilot-supplier-web --region ap-northeast-2 \
  --create-bucket-configuration LocationConstraint=ap-northeast-2
aws s3api put-public-access-block --bucket sunity-motion-pilot-supplier-web \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api get-bucket-location --bucket sunity-motion-pilot-supplier-web   # → ap-northeast-2

# 3. OAC (01:48:49Z)
aws cloudfront create-origin-access-control --origin-access-control-config \
  'Name=sunity-supplier-oac,Description=Phase 38 supplier link static site,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3'
#   → Id EDVM240S2C0RM

# 4. Distribution (01:49:01Z)
aws cloudfront create-distribution \
  --distribution-config file://.planning/phases/38-supplier-link/infra/cloudfront-supplier.json
#   → Id E16SR4IPFYH46Q, DomainName d2ivnoigym2xlu.cloudfront.net, ETag E23ZP02F085DFQ

# 5. 버킷 정책 (01:49:12Z)
aws s3api put-bucket-policy --bucket sunity-motion-pilot-supplier-web \
  --policy file://.planning/phases/38-supplier-link/infra/supplier-bucket-policy.json
aws s3api get-bucket-policy-status --bucket sunity-motion-pilot-supplier-web   # → IsPublic false

# 6. 업로드 (01:49:15Z)
aws s3 sync app/dist s3://sunity-motion-pilot-supplier-web --delete --only-show-errors

# 7. 배포 대기 (01:49:29Z → 01:52:33Z, 약 3분) + 무효화 (01:52:40Z)
aws cloudfront wait distribution-deployed --id E16SR4IPFYH46Q
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"
#   → I4GUC7WPFFGQSOLCJ5WUHEK98I, Completed
```

재배포(코드 고친 뒤) = 1 빌드 → 6 sync(`--delete`) → 7 무효화만.

## 검증

관측 [확인 — 이 세션 curl/aws 출력]:

| 확인 | 결과 |
|---|---|
| `curl -sI https://d2ivnoigym2xlu.cloudfront.net/` | `HTTP/2 200` · `content-type: text/html` · 1221 bytes |
| `/supplier` · `/supplier/upload` · `/supplier/guide` | 셋 다 `HTTP/2 200` · `text/html` · 1221 bytes · `x-cache: Error from cloudfront` (= 403 을 SPA 폴백 index.html 로 바꿔 준 것) |
| 없는 경로 `/does-not-exist` | 200 index.html (SPA 폴백 — 앱이 자기 404 화면을 그린다) |
| `http://…/supplier` | `301` → `https://d2ivnoigym2xlu.cloudfront.net/supplier` |
| `curl -s https://…/ \| grep -c 'id="root"'` | 1 |
| JS 번들 | 200 `text/javascript`, 원본 2,951,143 bytes → `Accept-Encoding: br,gzip` 면 `content-encoding: br` 842,304 bytes |
| S3 직접 `https://sunity-motion-pilot-supplier-web.s3.ap-northeast-2.amazonaws.com/index.html` | `403 Forbidden` (OAC 로만 읽힘) |
| `get-public-access-block` | 4개 전부 true |
| `get-bucket-policy-status` | `IsPublic: false` |
| `list-distributions` Comment `Phase 38 supplier link` | 정확히 1개 `E16SR4IPFYH46Q d2ivnoigym2xlu.cloudfront.net Deployed` |
| 번들 env 인라인 | API 호스트 `2rbpecm4d8.execute-api.ap-northeast-2.amazonaws.com` 1회 · `sunity-ai-coach` 4회 · Firebase apiKey 값 1회(값은 출력 안 함) · 남은 `EXPO_PUBLIC_` 참조 0 |
| API CORS (Origin `https://d2ivnoigym2xlu.cloudfront.net`) | `OPTIONS /reference/upload-url` → 204, `access-control-allow-origin: *`, methods `GET,OPTIONS,POST`, headers `authorization,content-type` · `POST /reference/upload-url` 무토큰 → 401 + `access-control-allow-origin: *` · `POST /upload-url` 무토큰 → 401 + 같은 헤더 |
| 시뮬 Safari (iPhone 16 Pro, iOS 18.6) `https://d2ivnoigym2xlu.cloudfront.net/supplier` | A-1 로그인 화면: Sunity 워드마크 · `강사·선수 전용` 칩 · `시작해 볼까요?` · 본문 · `Google로 시작하기` · 흐린 힌트 · 아래 `빌드 dev` — 스크린샷 `38-13-cf-a1.png` (휘발 scratchpad `/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/ef3648dc-db87-4310-a2aa-b555fa84c027/scratchpad/`) |

[미확인]:
- Google 팝업 로그인 — 도메인을 Firebase 허용 목록에 넣기 전이라 누르지 않았다(Task 2 뒤 Task 3 에서 belle 실기기).
- 로그인 뒤 모든 화면(A-2 · A-3 · STEP 01/02 · A-5 · 다이얼로그) — 여전히 한 번도 그려 보지 않았다.
- `빌드 dev` 라벨: 웹 번들에 빌드 식별값이 없어 `dev` 로 뜬다 [확인 화면]. 앱이 `extra.commitSha` 같은 값을 읽는 곳은 없다 [확인 grep `app/src`]. 이 플랜에서는 넣지 않았다.

진단 (재검증 대상):
- `/supplier` 가 `x-cache: Error from cloudfront` 인 것은 S3 가 없는 키에 403 을 주고(OAC 는 ListBucket 권한이 없으니 404 대신 403) CloudFront 가 CustomErrorResponses 403→/index.html 200 으로 바꾼 것이다 [추정 — S3 응답 코드를 CloudFront 로그로 보지는 않았다. 로깅 꺼짐].

## 비용

- S3: 객체 60개, `aws s3 ls --summarize` Total Size **19,259,239 bytes (약 18.4 MiB)** [확인]. 저장 요금은 이 크기 기준이다.
- CloudFront 과금 방식 **[미확인]**. `get-distribution` 응답 필드에 요금제 관련 항목이 없다(`PriceClass: PriceClass_All`, `Staging: false` 뿐) [확인]. 이 계정이 종량제인지 정액 요금제인지는 콘솔 CloudFront/Billing 화면에서만 보인다 — belle 확인 전까지 단정하지 않는다.
- 트래픽 규모 관측값: 첫 화면 전송 = index.html 1.2 KB + JS br 약 0.84 MB + 폰트·이미지(필요한 것만). 공급자 1~2명.

## 롤백

(a) 이 플랜이 **새로 만든** 리소스 — 전부 삭제. (b) 재사용 리소스 = 없음(복원 명령 없음).

| 리소스 | 구분 | 롤백 |
|---|---|---|
| distribution `E16SR4IPFYH46Q` | (a) | 끄고 → 배포 대기 → 삭제 |
| OAC `EDVM240S2C0RM` | (a) | distribution 삭제 뒤 삭제 |
| 버킷 `sunity-motion-pilot-supplier-web` (+정책·객체) | (a) | 비우고 삭제 |
| 영상 버킷 · Firebase · Lambda | 무접촉 | 없음 |

```bash
export AWS_PROFILE=sunity-motion
ID=E16SR4IPFYH46Q

# 1) distribution 끄기
aws cloudfront get-distribution-config --id $ID > /tmp/cf-cur.json
ETAG=$(python3 -c 'import json;print(json.load(open("/tmp/cf-cur.json"))["ETag"])')
python3 -c 'import json;d=json.load(open("/tmp/cf-cur.json"))["DistributionConfig"];d["Enabled"]=False;json.dump(d,open("/tmp/cf-off.json","w"))'
aws cloudfront update-distribution --id $ID --distribution-config file:///tmp/cf-off.json --if-match $ETAG
aws cloudfront wait distribution-deployed --id $ID

# 2) distribution 삭제
ETAG=$(aws cloudfront get-distribution --id $ID --query ETag --output text)
aws cloudfront delete-distribution --id $ID --if-match $ETAG

# 3) OAC 삭제
ETAG=$(aws cloudfront get-origin-access-control --id EDVM240S2C0RM --query ETag --output text)
aws cloudfront delete-origin-access-control --id EDVM240S2C0RM --if-match $ETAG

# 4) 버킷 삭제 (정책·객체 포함)
aws s3 rb s3://sunity-motion-pilot-supplier-web --force

# 5) Firebase Authorized domains 에서 d2ivnoigym2xlu.cloudfront.net 제거 (belle 콘솔)

# 6) app/app.json 의 "output": "single" 줄은 기본값과 같아 되돌리지 않아도 된다 (되돌리려면 git revert 로 Task 1 커밋)
```

## Figma 대조 (D-22)

- 이 실행기는 Figma 를 열지 않았다(오케스트레이터 지시 — Figma 비교는 오케스트레이터가 한다). 그래서 `get_screenshot` 1:717 · 1:960 · 1:646 · 1:1064 · 1:499 경로는 여기 없다 [미확인 — 오케스트레이터가 Task 3 전에 채운다].
- 대조 기준은 이제 Figma 섹션 `282:506` = `38-DESIGN.md` (quick 260930-eal 이 코드에 반영). 옛 "D-22 `≈` 네 칸" 이월은 이 시안으로 대체됐다.

## Task 2 — Authorized domain (belle 콘솔)

- 넣을 도메인: `d2ivnoigym2xlu.cloudfront.net` (와일드카드·`https://`·경로 없이 이 글자 그대로)
- 등록 결과: 대기 중 (belle 응답 뒤 이 줄을 확인 표식 줄로 바꾼다)

## Task 3 — 실기기 검증 (belle ○/×)

- Task 2 는 quick 260930-lfw 에서 belle 폰 Google 로그인 성공으로 사실상 통과 [확인 belle — lfw SUMMARY "실제 Google 계정 초대 수락"]. 콘솔 등록 줄 자체는 이 파일에 원문이 없다.
- A-1 · A-2(v2) · A-3 홈 · 코드 줄 · 복사 · 크게 보기 = lfw 에서 ○ [확인 belle]. 남은 것 = STEP 01 · STEP 02 · 가이드(A-6) · Figma 282:506 대조 · 부제 뺀 A-2 재확인.
- 웹 번들: 마지막 공급자 재배포(`cff7d634`) 뒤 app/ 변경은 수강생 앱 profile 탭뿐(o0u 4커밋, `colors.ts` 는 토큰 추가만) → 재배포 불필요 [확인 `git diff --stat cff7d634 HEAD -- app/src`].

### 시험 창 — TESTB 되살림 (2026-09-30 저녁)

- `supplier_invite.py reactivate --uid UmH3…` → `reactivate uid=UmH3… code=TESTB revokedInvite=-`, **창 시작 2026-09-30T13:23:51Z** [확인]. 다시 읽기: suppliers active True [확인 list].
- 끄는 명령(폰 확인 끝나면 반드시): `AWS_PROFILE=sunity-motion FIREBASE_SA_PATH=$PWD/firebase-sa.json backend/.venv/bin/python backend/scripts/supplier_invite.py deactivate --uid <UmH3 전체 uid>`
- 주의: STEP 02 에서 올린 시험 영상은 `reference` doc 이 `대기 중`(Pod down)으로 남는다. 38-14 에서 `requeue_reference_registrations.py` 를 돌리면 이 시험 영상까지 기준 모션으로 등록된다 [추정 — 코드 미확인]. 폰 확인 뒤 시험 doc 정리 필요.

belle 2026-09-30 저녁 총평 원문: *"너가 말한 기능은 모두 검증되는데 수정사항을 잘 체크해봐"* → 기능 ○ [확인 belle], 문구·구성 수정 요청 다수.

| 단계 | ○/× | belle 원문 |
|---|---|---|
| 수강생 1 키보드 겹침 | ○ | *"1번 오케이"* |
| 수강생 2 영상 길이 검사 | ○ + 불편 | *"2번 오케이인데 아이클라우드에 있는거 구분이 명확히 안되서 햇깔리네 자꾸"* |
| STEP 01 | ○ + 수정 | *"동의 안하면 다음 버튼 비활성화 맞음"* · 수정 요청은 아래 |
| STEP 02 | ○ + 수정 | *"동의 부분 필수쪽 선택 안할시 올리기 버튼 비활성화"* · *"동작을 올렸어요 알람이 등장하고 대기중으로 되어있음. 사진(썸네일 네모)는 등록 안되어 있는듯?"* |
| 촬영 가이드 · A-2 · Figma | ○(총평) | 개별 언급 없음 |

belle 수정 요청 원문(순서대로):
- *"체크 5개중 동작 하나만 담았어요는 아닐 수도 있어, 콤보일 수도 있음. 콤보를 원하는 수요자도 있음. 콤보는 약 1분15초도 넘는다. 90초까지는 아직 모르겠네."*
- *"소리가 있으면 뭐 방해요소가 되는건가? 그냥 소리를 우리가 끌 수 있다면?"*
- *"60초 이상되는 콤보도 있어. 그리고 위에서 하나만 담은 동작이냐고 물어봐놓고 아래에서 갑자기 콤보를 선택한다는걸 알려주면 이상하지"*
- *"선수 이름은 수정이 가능한게 맞는지는 잘 모르겠다."*
- *"기본기 -> 초급"*
- *"이 동작에 대해는 혹시 중요한건가?"*
- *"영상파일도 마찬가지로 위에서 수정되면 여기도 문구 바뀌어야 하고,"*
- *"용량이 100메가 이하만 된다네 지금 내가 가지고 있는 영상들이 폭스탑 계열이 160메가까지 올라가는디.."*
- *"아무것도 체크 안하면 필수항목 6개가 남았어요로 되어있는데 뭐뭐인지 모르겠네 필수라는 표기가 없어서"*
- *"학습 사용 동의는 체크 상태가 기본값."* · *"AI학습은 외부 노출이 아님을 알려줘야할 것."*
- *"동의는 언제든 철회할 수 있어요 이런 구구절절 문구가 필요한가? 보통 필수 항목에 동의 안해도되는데 그럼 서비스 이용 못한다고 써있거나 그냥 이용약관이나 이런걸로 연결 버튼이 있지 않아?"*

관측(수정 목록 근거):
- 썸네일: 행 컴포넌트가 썸네일을 받지 않고 아이콘 고정 [확인 `SupplierUi.tsx:293`]. 백엔드 어디에도 기준 동작 썸네일 생성 코드가 없다 [확인 grep `thumbnail` backend 0건] — 기존 기준 동작 썸네일은 앱 번들 `assets/motion-thumbs/` [확인 guide.tsx:37].
- 학습 동의 초기값 = false [확인 `upload.tsx:67`], 전체 동의는 필수 3 만 켠다 [확인 `upload.tsx:406`].
- 스플릿·유지 답은 저장만 되고 채점 소비처가 없다 [확인 grep — `firestore_admin.py:4568` 저장뿐]. 서 있는 시작은 파이프라인이 영상으로 따로 검사한다(`no_standing_start`) [확인 `pipeline/app.py:10456`].
- STEP 01 필수 = 8칸(체크 확인 · 동작 이름 · 선수 이름 · 레벨 · 스플릿 · 유지 · 서 있는 시작 · 파일) [확인 `supplierForm.ts:26`].
- 받은 기준 영상 최대 159MB = 4K(2160×3840) 30fps 32.3초, 오디오 트랙 있음 [확인 ffprobe `ref-foxtop-split.mp4` 외 3개 — 넷 다 오디오 있음]. 선수 콤보 74초 [확인 메모리 jeongeunji-combo-videos].
- 한도: 공급자·수강생 공용 `MAX_VIDEO_BYTES` 100MB, 콤보 60초 — 앱 `supplierForm.ts:20-23` · `models.py:717,973-975` · `validation.py:242` · `pipeline/app.py:10551`.

시험 doc: belle 이 올린 `클라임 · 기본기 · 대기 중` 1건이 TESTB(UmH3…) 소유로 남아 있다 — 정리 대상.

수정 반영 = quick-260930-w9l (2026-10-01 00:20~00:24 KST · layer `sunity-motion-pilot-shared:23` → reference-upload-url · playback-url · 웹 재배포 무효화 `IA83OV9SRXLSAVLLUPILU2U5Q9` · OTA preview ios group `62eb42e4-afa8-443d-8afa-ff55757bbd59`), belle 폰 재확인 대기 — 목록은 `.planning/quick/260930-w9l-supplier-form-revisions-belle-phone-chec/260930-w9l-SUMMARY.md` 끝. TESTB 는 아직 켜져 있다(재확인용).
