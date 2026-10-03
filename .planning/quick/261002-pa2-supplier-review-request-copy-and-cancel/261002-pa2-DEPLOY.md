# quick-261002-pa2 — 배포 명령서 (배포 전, 오케스트레이터 검토 대기)

> **2026-10-02 마감 보존:** 보조 스크립트는 scratchpad 가 휘발이라 `tools/` 에 옮겨 뒀다 — `tools/pa2_bundle_check.mjs` · `tools/pa2_livecheck.py` · `tools/pa2_literal_gate.mjs` · `tools/pa2_smoke.py`(원 `pa2-build/smoke.py`). 아래 본문의 `<scratchpad>/…` 스크립트 경로는 이 사본으로 읽을 것. zip 조립물은 배포 때 롤백 보존본에서 다시 만든다. **배포는 10-03 belle 와 함께**(belle 10-02 "마무리하자").


> **상태: 배포 안 함.** 이 문서는 준비물이다 — AWS 쓰기 명령(publish-layer-version · update-function-* · s3 sync ·
> create-invalidation)을 하나도 실행하지 않았다 [확인 — 이 세션 명령 기록]. 아래 실측은 전부 읽기 명령이고
> (2026-10-02 09:40~09:45Z, `AWS_PROFILE=sunity-motion`), 조립물은 scratchpad 에만 있다(휘발 — 배포 때 다시 만든다).
> 코드 커밋: `8c716824`(서버 취소 + 계약 3벌) · `c7e732cc`(공급자 웹). push 안 함.
> 범위 = layer(models · firestore_admin · validation) + reference-upload-url(코드 + 새 layer) + 공급자 웹.
> pipeline · Pod · playback-url · Firestore 규칙 · OTA · sam deploy 는 하지 않는다(아래 '하지 않는 것').

## 실측 — 지금 라이브 (읽기만, 09:40:27Z)

| 대상 | layer | CodeSha256 | LastModified | 판정 |
|---|---|---|---|---|
| reference-upload-url | `:23` | `N4cyKXyzZVoZIcLb0S0uCRfLio7TXbKFyj3HIbSUnFY=` | 2026-09-30T15:21:03Z | thx 시점과 같다 [확인 — thx DEPLOY 표] |
| playback-url | `:24` | `VcZQ59dX2YJWqo1xhw38IY8YHtha+vOHDg99msVtQWA=` | 2026-10-01T13:14:09Z | thx R-2 값 그대로 [확인] · 이번 무접촉 |
| pipeline | `:21` | `RFXSEcgMOrxCllCQXu6l2aJWbNa9Owyj3kROf8sAp1I=` | **2026-10-02T08:36:05Z** | 이번 무접촉. 코드 해시는 thx 기록 접두(`RFXSEcgM…`)와 같고 LastModified 만 오늘 — 설정(env) 변경으로 보인다 [미확인 — 38-14 Pod 정리 때 `RUNPOD_ANALYZE_URL` 자리표시자로 되돌린 것으로 추정] |
| layer 최신 | `:24` (2026-10-01T13:13:48Z, "quick-261001-thx …") · CodeSha256 `kZJQWDFyKRppF0ISG7bI/9V5h/7S47x8aZUAymwqlEU=` · 16,644,258 B | | | [확인 list-layer-versions · get-layer-version] |
| 웹 `/supplier` | 200 · `entry-394e74aeb945c1696825abb05949fe17.js` | | | = thx 배포 기록 2 W-1 entry [확인 curl] |

- 공급자 명단(읽기, `supplier_invite.py list`, 09:4xZ) [확인]: `FDJr…` BELLE active True(이름 없음) · `UmH3…` TESTB **active False**
  (38-14 정리에서 회수) · TESTB 초대 revoked. → 배포 뒤 TESTB 토큰 확인은 전부 403 이 정답이다(아래 P 표).
- 검수 CLI `review_reference_registrations.py list` → `검수 대기 0건`, exit 0 [확인 — 배포 전 기준선].

## 드리프트 · 조립 (scratchpad `pa2-build/` — 휘발)

받은 것(읽기): 라이브 함수 zip `fn-ruu-live.zip` — 로컬 sha256 `N4cyKXyz…` = AWS CodeSha256 [확인] · layer `:24` zip
`layer-24.zip` — 로컬 sha256 `kZJQWDFy…` = AWS CodeSha256 [확인].

| 검사 | 결과 |
|---|---|
| 라이브 함수 `app.py` vs `git show 301d4d02:backend/functions/reference-upload-url/app.py` | **같다** [확인 cmp]. 301d4d02 와 pa2 직전 HEAD `7e701c36` 사이에 이 파일을 바꾼 커밋 0 [확인 git log] |
| 함수 zip 안 `sunity_shared/` | 0개 — 함수는 layer 의 sunity_shared 만 쓴다 [확인 unzip -Z1] |
| layer `:24` sunity_shared/*.py 119개 vs 리포 HEAD | 다른 파일 = **정확히 3개**: `models.py` · `firestore_admin.py` · `validation.py` [확인 cmp]. 리포에만 있거나 layer 에만 있는 파일 0 |
| 3파일의 함수 단위 차이 | firestore_admin = `cancel_reference_registration`(pa2) + `deactivate_reference_registration`(thx e1a74f51 — :24 뒤 커밋, 호출자는 로컬 CLI 뿐) · validation = `validate_reference_cancel_request` · models = `REGISTRATION_STATUS_CANCELLED` + 취소 상수 4 (주석 밖 삭제 줄 0) [확인 diff] |

조립(지금 실행함 — 배포 때 **보존본 위에서 다시** 같은 명령으로 만든다):
```bash
B=<scratchpad>/pa2-build; S=backend/shared/python
cp $B/layer-24.zip $B/layer-new.zip                     # 배포 때는 $R/layer-24.zip (아래 롤백 준비)
mkdir -p $B/stage/python/sunity_shared
cp $S/sunity_shared/models.py $S/sunity_shared/firestore_admin.py $S/sunity_shared/validation.py $B/stage/python/sunity_shared/
(cd $B/stage && zip -q ../layer-new.zip python/sunity_shared/models.py python/sunity_shared/firestore_admin.py python/sunity_shared/validation.py)
cp $B/fn-ruu-live.zip $B/fn-ruu-new.zip                 # 배포 때는 $R/function-before-sunity-motion-pilot-reference-upload-url.zip
mkdir -p $B/fnstage && cp backend/functions/reference-upload-url/app.py $B/fnstage/
(cd $B/fnstage && zip -q ../fn-ruu-new.zip app.py)
```

| 조립 검사 | 결과 |
|---|---|
| layer 파일 수 | 1105 → 1105 [확인] |
| 새 layer 의 sunity_shared/*.py 119개 = HEAD | 119/119 [확인 cmp] |
| 새 layer vs `:24` 바뀐 파일 (zip 안 전 파일) | models · firestore_admin · validation **3개뿐** [확인] |
| 함수 파일 수 | 2266 → 2266 [확인] |
| 새 함수 vs 라이브 바뀐 파일 | `app.py` 하나 = HEAD [확인 cmp] |
| 로컬 sha256 | layer-new `IUAD7VKaFdqkRB3DG212iF/qKdD0q8PDNeNDQpAmuts=` · fn-ruu-new `HEzmt1+IUjtn7f+iM6xGFqWHLJvP1rbXBE/yt0h87+Q=` — 다시 조립하면 zip 메타(시각) 때문에 달라질 수 있다. 게시 응답 CodeSha256 = 그때 로컬 값인지만 본다 |

## Docker 스모크 (로컬 컨테이너 — 배포 아님)

`public.ecr.aws/sam/build-python3.12:latest-arm64`(05b9de903b15), `--platform linux/arm64`, `PYTHONPATH=/opt/python:/var/task`,
`VIDEO_BUCKET` 더미 env. 스크립트 = scratchpad `pa2-build/smoke.py`(휘발). Docker Desktop 은 `open -a Docker` 로 켰다.

| 조합 | 결과 | 뜻 |
|---|---|---|
| 새 layer + 새 함수 | **`SMOKE_OK unauth=401 probe_unauth=401 cancelled=ok writer=ok validator=bad_request(ref-kip-up)`** [확인] | `import app` 성공 · 무토큰 취소/probe 401 · `REGISTRATION_STATUS_CANCELLED == 'cancelled'`(튜플 끝) · 취소 상수 2 · `cancel_reference_registration` · `deactivate_reference_registration` 존재 · `_REGISTRATION_TERMINAL` 에 cancelled · `validate_reference_cancel_request({'refId':'ref-kip-up'})` → ValidationError bad_request 400, 32hex 통과 |
| 라이브 함수 + 새 layer | `SMOKE_OK_OLD_CODE_NEW_LAYER unauth=401 import=ok` [확인] | 배포 (2) 의 "layer 먼저" 중간 상태가 안전하다 — 옛 코드는 새 layer 위에서 돈다(추가만 있다) |
| 새 함수 + layer `:24` | `EXPECTED_IMPORT_ERROR ImportError: cannot import name 'validate_reference_cancel_request' from 'sunity_shared.validation'` [확인] | 순서를 거꾸로 하면(코드 먼저) **import 단계에서 죽어 probe · 업로드까지 멈춘다** — 배포는 layer 먼저, 롤백은 코드 먼저인 근거(T-pa2-07) |

## 웹 번들 빌드 확인 (scratchpad `pa2-web/` — app/dist 아님)

`cd app && CI=1 npx expo export --platform web --output-dir <scratchpad>/pa2-web` → exit 0, `entry-c8639132d39774951dfd1606aef76533.js` [확인].
번들은 한글을 `\uXXXX`, 가운뎃점을 `\xb7` 로 내보내므로 grep 으로는 0 이 나온다 — 둘 다 풀어서 세는 scratchpad
`pa2_bundle_check.mjs`(휘발, 인자 = 번들 경로 또는 URL)로 셌다. 디코더 검증: 라이브 옛 번들에서 옛 문구 '확인 중 · 끝나면 수강생에게 보여요' 1 ·
'운영팀 확인이 끝나면 앱에 보여요' 1 이 잡힌다 [확인].

| 문구 | 새 번들 |
|---|---|
| 검토 중이에요 · 요청 취소됨 · 검토는 보통 하루 안에 끝나요 · 검토를 요청했어요. 보통 하루 안에 끝나요. · 검토 요청을 취소할까요? · 지금은 취소할 수 없어요 | 각 1 [확인] |
| 검토 요청 취소 | 2 (패널 링크 · 확인창 주버튼 — 같은 글자 두 키) [확인] |
| 옛 '확인 중 · 끝나면 수강생에게 보여요' · 옛 '운영팀 확인이 끝나면 앱에 보여요' · '메일로 알려' · '일 이내' | 0 [확인] |

## 롤백

보존 폴더 = **`/Users/Shared/sunity-motion-rollback/pa2/`**(700, 홈 디렉터리 밖). **아직 만들지 않았다** — 배포 승인 뒤
아래 "준비" 를 **배포 직전에** 돌린다(그 순간의 라이브를 보존해야 하므로).

### 준비 (배포 직전, 읽기만)

```bash
export AWS_PROFILE=sunity-motion
R=/Users/Shared/sunity-motion-rollback/pa2
mkdir -p $R && chmod 700 $R
F=sunity-motion-pilot-reference-upload-url

# reference-upload-url — 설정 원문 + 현재 코드 zip (sha = CodeSha256 이어야 한다)
aws lambda get-function-configuration --function-name $F > $R/before-config-reference-upload-url.json
curl -s -o $R/function-before-$F.zip "$(aws lambda get-function --function-name $F --query Code.Location --output text)"
openssl dgst -sha256 -binary $R/function-before-$F.zip | base64      # = N4cyKXyz…(지금 값) 이어야 한다

# 그 함수가 지금 붙은 layer(:23) 와 조립 원본 layer(:24) — 둘 다 게시된 채 남지만 원본도 보관
curl -s -o $R/layer-23.zip "$(aws lambda get-layer-version --layer-name sunity-motion-pilot-shared --version-number 23 --query Content.Location --output text)"
curl -s -o $R/layer-24.zip "$(aws lambda get-layer-version --layer-name sunity-motion-pilot-shared --version-number 24 --query Content.Location --output text)"
openssl dgst -sha256 -binary $R/layer-24.zip | base64                # = kZJQWDFy… 이어야 한다

# 웹 버킷 전체 + 라이브 entry
aws s3 sync s3://sunity-motion-pilot-supplier-web $R/web-before --only-show-errors
curl -s https://d2ivnoigym2xlu.cloudfront.net/supplier | grep -o 'entry-[0-9a-f]*\.js' > $R/web-before-entry.txt   # = entry-394e74ae… 예상
```

### 롤백 명령

```bash
export AWS_PROFILE=sunity-motion
R=/Users/Shared/sunity-motion-rollback/pa2
F=sunity-motion-pilot-reference-upload-url
L=arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared

# 1) 웹 먼저 — 새 웹 + 옛 Lambda 면 취소가 폼 검증 400 으로 떨어진다(새 웹이 서버보다 오래 살면 안 된다)
aws s3 sync $R/web-before s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"

# 2) 함수 **코드 먼저** — 새 app.py 는 옛 layer 위에서 import 단계에서 죽는다(Docker 스모크 3번째 조합 [확인]).
#    옛 app.py 는 새 layer 위에서도 돈다(스모크 2번째 조합 [확인]) → 코드를 먼저 되돌리면 중간 상태가 안전하다.
aws lambda update-function-code --function-name $F --zip-file fileb://$R/function-before-$F.zip
aws lambda wait function-updated --function-name $F
# 3) 그다음 layer 를 원래 버전으로
aws lambda update-function-configuration --function-name $F --layers $L:23
aws lambda wait function-updated --function-name $F
aws lambda get-function-configuration --function-name $F --query '{sha:CodeSha256,layers:Layers[].Arn,st:LastUpdateStatus}'
#    → sha N4cyKXyz… · :23 · Successful
```

- 새 layer 버전은 남겨도 된다(참조하는 함수가 없으면 무해). `:23` · `:24` 는 게시된 채 있다 → 되붙이기가 롤백 [확인 list-layer-versions].
- 롤백 뒤에도 Firestore 에 이미 생긴 `cancelled` doc 은 남는다. 옛 웹은 그 상태를 모르는 값 → `registering` 기본값으로
  읽어 '확인 중 · 끝나면 수강생에게 보여요' 행으로 보인다 [확인 코드 — 옛 `supplierRules.normalizeRegistration` 기본값]. 수강생 노출은
  없다(isActive false, picker `referenceMotions.ts:79` 가 거른다). 옛 CLI · 파이프라인도 cancelled 를 대기로 보지 않는다(코드 무변경).

## 배포 (오케스트레이터가 실행 — belle 승인 뒤)

순서 = (1) layer → (2) reference-upload-url(**layer 먼저 → 코드 다음**) → (3) 웹. **웹은 반드시 (2) 뒤** — 새 웹 + 옛 Lambda 면
'검토 요청 취소' 가 폼 검증 400(일반 문구)으로 떨어진다 [확인 코드 — 옛 app.py 에 cancel 분기 없음].

### (1) layer — `:24` 보존본 + 3파일

```bash
export AWS_PROFILE=sunity-motion
B=<scratchpad>/pa2-build; R=/Users/Shared/sunity-motion-rollback/pa2; S=backend/shared/python
rm -rf $B/stage && mkdir -p $B/stage/python/sunity_shared && cp $R/layer-24.zip $B/layer-new.zip
cp $S/sunity_shared/models.py $S/sunity_shared/firestore_admin.py $S/sunity_shared/validation.py $B/stage/python/sunity_shared/
(cd $B/stage && zip -q ../layer-new.zip python/sunity_shared/models.py python/sunity_shared/firestore_admin.py python/sunity_shared/validation.py)
# 게시 전: 파일 수 1105 · sunity_shared/*.py 119개 = HEAD · :24 대비 바뀐 파일 3개 · Docker 스모크 SMOKE_OK (위 절과 같은 검사)
aws lambda publish-layer-version --layer-name sunity-motion-pilot-shared \
  --description "quick-261002-pa2 cancelled state + cancel writer + cancel validator (from :24 + 3 files)" \
  --zip-file fileb://$B/layer-new.zip --compatible-runtimes python3.12 --compatible-architectures arm64
#   → :25 예상. 응답 Version · CodeSha256 = 로컬 zip sha256 을 '배포 기록' 에 적는다
```

### (2) reference-upload-url — 새 layer 붙이기 → 코드 (app.py 만 교체)

```bash
F=sunity-motion-pilot-reference-upload-url
L=arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared
cp $R/function-before-$F.zip $B/fn-ruu-new.zip
mkdir -p $B/fnstage && cp backend/functions/reference-upload-url/app.py $B/fnstage/
(cd $B/fnstage && zip -q ../fn-ruu-new.zip app.py)                     # 파일 수 2266 그대로 · app.py = HEAD
aws lambda update-function-configuration --function-name $F --layers $L:<새 버전>   # layer 먼저
aws lambda wait function-updated --function-name $F
aws lambda update-function-code --function-name $F --zip-file fileb://$B/fn-ruu-new.zip   # 그다음 코드
aws lambda wait function-updated --function-name $F
aws lambda get-function-configuration --function-name $F --query '{sha:CodeSha256,layers:Layers[].Arn,st:LastUpdateStatus,mod:LastModified}'
```
- layer 먼저인 이유: 새 app.py 는 `validate_reference_cancel_request` · `REGISTRATION_STATUS_CANCELLED` · 취소 상수를 import 하는데 `:23` 에는
  없다 → 코드 먼저면 import 실패로 probe · 업로드 · 취소가 전부 초기화 실패 [확인 Docker 스모크 — `:24` 위에서 ImportError.
  `:23` 은 `:24` 보다 더 옛것이라 같은 결과일 것 — `:23` 으로는 돌리지 않았다 [추정]].
- 이 함수가 `:23` → 새 버전으로 건너뛰며 thx 의 `:24` 차이(models rejected 문구 · review 상수 · writer 추가)도 같이 받는다 — 이 함수가 쓰는
  `create_reference_registration` 은 :23 이후 무변경이고 상수는 추가만이라 동작 차이 0 [확인 thx DEPLOY (3) 절 · 이번 diff].
- template.yaml · IAM · 환경변수 무변경 — sam deploy 안 함. 이 layer/코드 갱신은 CFN 밖 드리프트(다음 `sam deploy` 가 스택 정의로 되돌린다)
  [추정 — w9l · thx 와 같은 구조].

### (3) 웹 — 검토 중 문구 · 검토 중 패널 · 요청 취소

```bash
cd app && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist
node <scratchpad>/pa2_bundle_check.mjs dist/_expo/static/js/web/entry-*.js            # BUNDLE_COPY_OK 여야 올린다
aws s3 sync app/dist s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"
aws cloudfront wait invalidation-completed --distribution-id E16SR4IPFYH46Q --id <무효화 id>
curl -s https://d2ivnoigym2xlu.cloudfront.net/supplier | grep -o 'entry-[0-9a-f]*\.js'     # = 새 dist entry
```
- app/dist 는 gitignore(`app/.gitignore:8 dist/`) [확인 git check-ignore].

## 하지 않는 것과 이유

| 대상 | 이유 |
|---|---|
| pipeline Lambda | cancelled 는 `_handle_reference_upload`(`pipeline/app.py:332`)의 registering 검사(`:354`)로 '스킵: 등록 대기 doc 아님'(`:357`) — 코드 변경 0 [확인 코드 + 테스트 `test_reput_after_registration_is_skipped_and_v1_immutable[cancelled]` 코드 무변경 통과]. 이 Lambda 는 `:21` 그대로 둔다 |
| Pod | 취소는 등록 실행 전(queued)과 후(review)에서만 된다 — Pod 코드 경로 변경 0. claim 화이트리스트 밖이라 cancelled 는 Pod 로 가지 않는다 [확인 테스트 — run_contended 양방향]. 다음 Pod 기동 때 HEAD 를 받으면 models/firestore_admin 이 같이 들어가지만 Pod 쪽 소비 0 [확인 grep — `backend/runpod_inference` · `backend/functions/pipeline` · `backend/scripts` 에 `cancel_reference_registration` · `REGISTRATION_STATUS_CANCELLED` 0] |
| requeue CLI | queued · processing · registering 만 조회(`requeue_reference_registrations.py:119` · `:122` · `:127`) → cancelled 무접촉 [확인 코드] |
| 검수 CLI | 로컬 리포 코드라 배포물이 아니다. list 는 review 만(`review_reference_registrations.py:123`), approve/reject/deactivate 는 writer 의 상태 검사가 cancelled 를 ValueError 로 거부 [확인 테스트 `test_ops_writers_refuse_cancelled`] |
| playback-url | 무변경, `:24` 유지. cancelled doc 은 `_visible_to` 상 review 가 아닌 비활성이라 소유자에게도 썸네일 404(아이콘 자리) — failed/rejected 와 같은 기존 동작 [확인 코드] |
| Firestore 규칙 | 무변경 — 취소 쓰기는 Lambda Admin SDK. 공개 doc 은 원래 인증자 읽기 |
| OTA | 수강생 picker 는 isActive false 를 이미 숨긴다(`referenceMotions.ts:79` 무변경). analysis.ts 변경은 유니온 · 타입 추가뿐. 공급자 라우트는 수강생 화면에서 닿지 않는다(thx DEPLOY (7) 근거 그대로) |
| sam deploy | 금지 — 이 갱신은 CFN 밖 드리프트(w9l · thx 와 같은 구조). 새 API 라우트 없음(같은 `POST /reference/upload-url`) |

## 배포 뒤 확인

### 쓰기 0 (오케스트레이터)

먼저 대상 공급자의 명단 상태를 Admin 읽기로 본다 — 지금(09:4xZ) TESTB `UmH3…` = **active False**(38-14 회수) [확인 `supplier_invite.py list`].
그래서 TESTB 토큰의 기대값은 403 이다. 표에 그대로 적는다.

스크립트 = scratchpad `pa2_livecheck.py`(휘발 — 만들어 두고 py_compile 만 했다, 실행 안 함). thx `thx_livecheck.py` 방식:
대상 uid 커스텀 토큰 → `signInWithCustomToken` → ID 토큰 → `POST /reference/upload-url`. 부작용 = 그 uid 의 Auth lastSignIn 갱신뿐 [추정].
```bash
AWS_PROFILE=sunity-motion FIREBASE_SA_PATH=$PWD/firebase-sa.json backend/.venv/bin/python <scratchpad>/pa2_livecheck.py --uid <UmH3…> [--p4-ref d8e849f7…]
```

| # | 요청 | TESTB 지금 상태(active False) 기대 | TESTB 가 active 일 때 기대 |
|---|---|---|---|
| P0 | 무토큰 `{cancel:true, refId:<32hex>}` | **401** unauthorized | 401 |
| P1 | TESTB probe | **403** not_invited | 200 (probe 무회귀) |
| P2 | TESTB 임의 32hex 취소 | **403** | **404** not_found |
| P3 | TESTB `ref-kip-up` 취소 | **403** | **400** bad_request |
| P4 | TESTB 소유 `d8e849f7…`(38-14 테스트 기준 — 기록상 registrationStatus active · isActive false [확인 38-14-E2E 기록, 지금 재조회 안 함]) 취소 | **403** · doc 전후 동일 | **409** not_cancellable · doc 전후 동일 |
| P5 | 웹 `/supplier` | 200 + 새 entry + `pa2_bundle_check.mjs <라이브 entry URL>` → BUNDLE_COPY_OK | 같음 |
| P6 | `review_reference_registrations.py list` | exit 0 (배포 전 기준선 `검수 대기 0건` [확인]) | 같음 |

- P2~P4 를 403 이 아닌 값으로 보려면 활성 공급자 토큰이 필요하다. 선택지(오케스트레이터 · belle 판단, 내가 정하지 않음):
  (a) TESTB 를 잠깐 되살림 — `supplier_invite.py reactivate --uid <UmH3…>` → 확인 → `deactivate`(쓰기 2, 38-14 와 같은 절차) ·
  (b) BELLE uid `FDJr…`(active True) 로 P1~P3 — Firestore 쓰기 0 이지만 belle 실계정의 Auth lastSignIn 이 바뀐다. BELLE 소유 등록 doc 이 있는지는 [미확인] →
  P4 는 못 할 수 있다 · (c) 403 으로 두고 취소 분기는 단위 테스트 + Docker 스모크로만 [확인된 범위]로 둔다.

### 선택 확인 (쓰기 있음 — belle 승인 뒤에만, Pod 꺼진 상태 전제)

belle 이 화면을 보는 자리다(로그인 뒤 화면은 fixture 로 그리는 장치가 없다 — 렌더 확인은 여기서만).
1. TESTB 되살림(위 (a)) — 지금 active False 라 이 단계가 먼저다.
2. scratchpad 에서 imageio-ffmpeg 로 6초 검은 화면 mp4 를 만든다(`정은지님 영상/` 은 열지 않는다).
3. TESTB 로 공급자 웹에서 업로드 → 파이프라인이 Pod 부재로 `queued` → 홈 행 '중급 · 검토 중'(진행 점) · 토스트 '검토를 요청했어요. 보통 하루 안에 끝나요.'
4. 행을 눌러 검토 중 패널 — '검토 중이에요' · 하루 안 안내 · 틸 '검토 요청 취소' 링크.
5. 링크 → 화면 안 확인창(분홍 카드 · 느낌표 · [닫기] / [검토 요청 취소]) → 확인 → 패널이 '검토 요청을 취소했어요' 로, 행이 '요청 취소됨'(쉐브론)으로.
6. 같은 refId 로 두 번째 취소(livecheck `--p4-ref`) → 200 `alreadyCancelled: true`.
7. `requeue_reference_registrations.py --dry-run` 표에 그 refId 없음 · 수강생 picker 미노출(isActive false).
8. 정리: 그 doc · S3 upload 객체 처리(belle 판단) → TESTB `deactivate`.

## 배포 기록

### 2026-10-03 배포 (belle "pa2 배포부터")

**롤백 보존 (08:23Z, 읽기)** — `/Users/Shared/sunity-motion-rollback/pa2/`(700) [확인 ls]
- 함수 zip sha `N4cyKXyz…` = AWS CodeSha256 · layer-23 `tZDzyZl1…` = AWS · layer-24 `kZJQWDFy…` = 기록값 [확인 openssl]
- 웹 버킷 60 파일, 라이브 entry `entry-394e74ae…` 포함 · `before-config-reference-upload-url.json` [확인]

**조립 검사 (scratchpad, 보존본 위)** — layer 1105→1105 · :24 대비 바뀐 파일 3개(models · firestore_admin · validation) ·
sunity_shared/*.py 119/119 = HEAD · 함수 2266→2266 · 바뀐 파일 `app.py` 하나 = HEAD [확인 diff -rq · cmp]

**Docker 스모크 (arm64 컨테이너)** [확인]
- 새 layer + 새 함수 → `SMOKE_OK unauth=401 probe_unauth=401 cancelled=ok writer=ok validator=bad_request(ref-kip-up)`
- 라이브 함수 + 새 layer → `SMOKE_OK_OLD_CODE_NEW_LAYER`
- 새 함수 + `:24` → ImportError · 새 함수 + **`:23`** → ImportError (위 (2) 절의 `:23` [추정]이 이번에 [확인])

**웹 빌드** — `entry-c8639132d39774951dfd1606aef76533.js`(10-02 빌드와 같은 해시) · `BUNDLE_COPY_OK` [확인]

| 단계 | 시각(Z) | 결과 |
|---|---|---|
| (1) layer 게시 | 08:25:16 | **`:25`** · CodeSha256 `ky2+xIvB9UkcZiNfH3nncWt15r5sGSE9lVqUbSwM5lg=` = 로컬 zip · 16,646,773 B [확인] |
| (2a) 함수 layer → `:25` | 08:25:29 | Successful · 코드 sha 아직 `N4cyKXyz…` [확인] |
| (2b) 함수 코드 | 08:25:52 | CodeSha256 `N+3DnoINzqoba527206ayv533pkuZGCm6qHQvfYUl2c=` = 로컬 zip · layer `:25` · Successful [확인] |
| P0 (웹 올리기 전) | 08:26 | 무토큰 cancel 401 · 무토큰 probe 401 — 핸들러 실행(import 성공) [확인 curl] |
| (3) 웹 | 08:2x | s3 sync --delete · 무효화 `IB4MGFP3A71UQROZE6AEZVCTX6` 완료 · `/supplier` 200 · 라이브 entry `c8639132…` · 라이브 URL 로 `BUNDLE_COPY_OK` [확인] |

**배포 뒤 확인**
- P6 `review_reference_registrations.py list` → `검수 대기 0건`, exit 0 [확인]
- belle 선택(10-03) = **(a) TESTB 잠깐 되살림**. `reactivate` 09:01:35Z → active True [확인 list]
- `pa2_livecheck.py --uid UmH3… --p4-ref d8e849f7…` (09:01:54Z) [확인]:

| # | 결과 | 기대(TESTB active) |
|---|---|---|
| P0 | 401 unauthorized | 401 ○ |
| P1 | 200 probe | 200 ○ |
| P2 | 404 not_found | 404 ○ |
| P3 | 400 bad_request | 400 ○ |
| P4 | 409 not_cancellable · doc 전후 동일 True (status active) | 409 ○ |

- belle 폰 확인(선택 확인 2~8) = **보류** — belle 10-03 *"실증이 얼마 안 남았다 일단 다른거 부터 개발"*. 렌더(토스트 · 검토 중 패널 · 확인창 · 요청 취소됨 행)는 **[미확인]**.
- TESTB 회수 `deactivate` 10:06:55Z → active False [확인 list]. 폰 확인 재개 때 `reactivate` 부터 다시.
- 이번 확인으로 생긴 Firestore · S3 쓰기 = 공급자 doc active 두 번 토글뿐(취소 쓰기 0 — P2~P4 전부 거절 응답) [확인 응답 코드].
- 배포 중 Pod 꺼짐 상태 무접촉: SSM `pod-expected = down`, pipeline `RUNPOD_ANALYZE_URL` = `pod-down.invalid` 자리표시자 [확인 읽기].
