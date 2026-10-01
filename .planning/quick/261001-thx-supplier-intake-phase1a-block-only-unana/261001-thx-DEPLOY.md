# quick-261001-thx — 배포 명령서 · 배포 기록

> **상태: 배포 완료 (2026-10-01 13:13~13:15Z = 22:13~22:15 KST).** belle 승인(10-01 "오케이 진행하자") 범위 = (1) layer · (2) playback-url · (6) 웹.
> (3) reference-upload-url 은 건너뜀, (4) pipeline · (5) Pod · (7) OTA 는 안 함. → layer **:24** · playback-url `Successful` ·
> 웹 무효화 **`IBUCA5QK6UNO7SLDR7CVATU667`**. 기록 = 맨 아래 '## 배포 기록 (2026-10-01)'.
> 코드 커밋: `79977722`(백엔드) · `2989c191`(공급자 문구 · 검수 CLI) · `656c9c99`(가이드 문구를 확인 흐름에 맞춤 + 문구 다듬기 —
> models.py 의 rejected 문구가 바뀌어 layer 는 이 커밋에서 다시 조립했다). push `6b9d98dc..656c9c99`.
> 아래 '롤백' · '배포' 절은 배포 전에 쓴 명령서 그대로다(숫자 일부는 배포 때 다시 잰 값이 '배포 기록' 에 있다).

## 롤백

> 배포 **전에** 적었다(2026-10-01 21:5x KST). 보존 폴더 = **`/Users/Shared/sunity-motion-rollback/thx/`**(700, 홈 디렉터리 밖).
> 보존물은 아직 안 만들었다 — 배포 승인 뒤 아래 "준비" 를 **배포 직전에** 돌린다(그 순간의 라이브를 보존해야 하므로).

### 준비 (배포 직전, 읽기만)

```bash
export AWS_PROFILE=sunity-motion
R=/Users/Shared/sunity-motion-rollback/thx
mkdir -p $R && chmod 700 $R
L=arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared

# playback-url — 설정 원문 + 현재 코드 zip
aws lambda get-function-configuration --function-name sunity-motion-pilot-playback-url > $R/before-config-playback-url.json
curl -s -o $R/function-before-sunity-motion-pilot-playback-url.zip \
  "$(aws lambda get-function --function-name sunity-motion-pilot-playback-url --query Code.Location --output text)"
openssl dgst -sha256 -binary $R/function-before-sunity-motion-pilot-playback-url.zip | base64   # = CodeSha256 이어야 한다

# (3) 을 고르면 reference-upload-url 도 같은 두 줄
aws lambda get-function-configuration --function-name sunity-motion-pilot-reference-upload-url > $R/before-config-reference-upload-url.json

# 현재 layer :23 zip (되붙이기 대상 — 게시된 채 남지만 원본도 보관)
curl -s -o $R/layer-23.zip \
  "$(aws lambda get-layer-version --layer-name sunity-motion-pilot-shared --version-number 23 --query Content.Location --output text)"

# 웹 버킷 전체
aws s3 sync s3://sunity-motion-pilot-supplier-web $R/web-before --only-show-errors
curl -s https://d2ivnoigym2xlu.cloudfront.net/supplier | grep -o 'entry-[0-9a-f]*\.js' > $R/web-before-entry.txt
```

지금 실측한 배포 전 상태 (지금 실행함, 2026-10-01 12:5xZ, 읽기만) [확인]:

| 대상 | layer | CodeSha256 | LastModified |
|---|---|---|---|
| playback-url | `:23` | `nRJilv5HScm2cfv4GxaN1cZ4xqkKgnf+ajZI6IPfZi8=` (= w9l 배포값) | 2026-09-30T15:21:17Z |
| reference-upload-url | `:23` | `N4cyKXyzZVoZIcLb0S0uCRfLio7TXbKFyj3HIbSUnFY=` (= w9l 배포값) | 2026-09-30T15:21:03Z |
| pipeline | `:21` | `RFXSEcgM…` | 2026-10-01T03:38:50Z (이번 플랜 무관 — 무엇이 바뀌었는지 [미확인]) |
| layer 최신 | `:23` (w9l, 2026-09-30T15:20:40Z) · CodeSha256 `tZDzyZl1qzwo52M1IJADlNOYWQiD1fZjITk2bNKyd9s=` | | |
| 웹 | 라이브 `/supplier` → `entry-4075a633…js` (= w9l 배포분) · 버킷 객체 60개 | | |

- 드리프트: 라이브 playback-url zip 의 `app.py` = thx 직전 커밋 `6b9d98dc` 와 같다 [확인 cmp]. layer :23 의 sunity_shared/*.py 119개 중 리포 HEAD 와 다른 파일 = **정확히 3개**(models · firestore_admin · analysis/registration_checks) [확인 cmp — 아래 (1) 표].

### 롤백 명령

```bash
export AWS_PROFILE=sunity-motion
R=/Users/Shared/sunity-motion-rollback/thx
L=arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared

# 1) 웹 먼저 — 새 번들은 옛 서버와도 동작하지만(review 행이 안 생길 뿐), 반려 사유 문구는 새 번들만 안다
aws s3 sync $R/web-before s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"

# 2) playback-url — **코드 먼저, layer 나중**
#    (새 app.py 는 models.REGISTRATION_STATUS_REVIEW 를 읽는다 → 옛 layer :23 위에서는 isActive false doc 에
#     AttributeError 500. 옛 app.py 는 새 layer 위에서도 문제없다 — 추가만 있다.)
aws lambda update-function-code --function-name sunity-motion-pilot-playback-url \
  --zip-file fileb://$R/function-before-sunity-motion-pilot-playback-url.zip
aws lambda wait function-updated --function-name sunity-motion-pilot-playback-url
aws lambda update-function-configuration --function-name sunity-motion-pilot-playback-url --layers $L:23
aws lambda wait function-updated --function-name sunity-motion-pilot-playback-url

# 3) (3) 을 골랐다면 reference-upload-url layer 만 되돌리기(코드는 안 바뀐다)
aws lambda update-function-configuration --function-name sunity-motion-pilot-reference-upload-url --layers $L:23
aws lambda wait function-updated --function-name sunity-motion-pilot-reference-upload-url

# 4) Pod (38-14 재개 때 새 코드가 올라간 뒤에만 해당) — 옛 판정(check_registration fail-closed)으로
#    볼륨 리포에서(38-14-E2E.md '관측 — Pod 재배포' 절과 같은 절차, 리포 경로는 그 절 그대로):
git fetch origin -q && git reset --hard 6b9d98dc -q
pkill -f "[u]vicorn runpod"     # 별도 ssh 호출
export RUNPOD_POD_ID=<pod id>; source /workspace/aws_env.sh; nohup bash /workspace/start_server.sh > /workspace/start_server_thx_rollback.log 2>&1 < /dev/null &
curl -s https://<pod-proxy>/health   # commitSha == 6b9d98dc…
```

- 새 layer 버전은 남겨도 된다(참조하는 함수가 없으면 무해). :23 은 게시된 채 있다 → 되붙이기가 롤백 [확인 list-layer-versions].
- 롤백 뒤에도 Firestore 에 이미 생긴 `review` doc 은 그대로 남는다 — 수강생에게는 안 보이고(isActive false, picker 무변경), 옛 playback-url 은 공급자 본인에게도 썸네일 404(아이콘 자리)를 준다. 승인/반려 CLI 는 로컬 리포 코드라 롤백과 무관하게 돈다 [확인 — CLI 는 배포물이 아니다].
- Pod 를 옛 코드로 되돌리면, 진행 중인 review doc 의 자기 재현성 선기록(`begin_self_check`)은 옛 코드가 active 만 허용해 막힌다 [확인 옛 코드 `6b9d98dc` firestore_admin.begin_self_check]. 그 doc 은 approve 뒤 재처리 대상이다.

## 배포 (belle 승인 대기)

순서 = (1) layer → (2) playback-url → (6) 웹 → (5) Pod(38-14 재개 때). (3) 은 선택, (4)(7) 은 불필요.

### (1) layer — :23 복사본 + 바뀐 3파일

조립(지금 실행함, 로컬 scratchpad `thx-build/` — 휘발, 배포 때 다시 만든다):
```bash
B=<scratchpad>/thx-build; S=backend/shared/python
cp layer-23.zip $B/layer-new.zip                                  # layer-23.zip = 위 준비에서 받은 것
mkdir -p $B/stage/python/sunity_shared/analysis
cp $S/sunity_shared/models.py $S/sunity_shared/firestore_admin.py $B/stage/python/sunity_shared/
cp $S/sunity_shared/analysis/registration_checks.py $B/stage/python/sunity_shared/analysis/
(cd $B/stage && zip -q ../layer-new.zip python/sunity_shared/models.py python/sunity_shared/firestore_admin.py \
   python/sunity_shared/analysis/registration_checks.py)
```

cmp 결과 (지금 실행함) [확인]:

| 대상 | :23 vs 리포 HEAD | 새 zip vs 리포 HEAD | 새 zip vs :23 |
|---|---|---|---|
| sunity_shared/models.py | 다름 | 같음 | **바뀜** |
| sunity_shared/firestore_admin.py | 다름 | 같음 | **바뀜** |
| sunity_shared/analysis/registration_checks.py | 다름 | 같음 | **바뀜** |
| 나머지 sunity_shared/*.py 116개 | 같음 | 같음 | 같음 |
| zip 파일 수 | 1105 | 1105 | — |

- 새 zip CodeSha256(로컬) = `Ge8URERyxnmVTRQfmk96wxBmTGM5B8p7OuSvKs40sN4=` [확인]. 배포 때 다시 조립하면 zip 메타(시각) 때문에 값이 달라질 수 있다 — 게시 응답의 CodeSha256 = 그때 로컬 값인지만 본다.
- 3파일 중 registration_checks 는 Lambda 에서 import 하는 곳이 없다(Pod 전용) — layer 일관성 목적 [확인 grep — functions/ 에서 registration_checks 소비처는 pipeline/app.py 뿐이고 `_register_reference` 는 Pod 에서만 돈다].

```bash
export AWS_PROFILE=sunity-motion
aws lambda publish-layer-version --layer-name sunity-motion-pilot-shared \
  --description "quick-261001-thx review state + approve/reject + diagnoses (from :23 + 3 files)" \
  --zip-file fileb://$B/layer-new.zip --compatible-runtimes python3.12 --compatible-architectures arm64
#   → :24 예상 (게시 응답의 Version 을 실측으로 적는다)
```

### (2) playback-url — 새 layer 붙이기 → 코드 (app.py 만 교체)

조립(지금 실행함):
```bash
cp $R/function-before-sunity-motion-pilot-playback-url.zip $B/fn-pb-new.zip     # 지금은 scratchpad 의 fn-pb-before.zip
mkdir -p $B/fnstage && cp backend/functions/playback-url/app.py $B/fnstage/
(cd $B/fnstage && zip -q ../fn-pb-new.zip app.py)
```
- 파일 수 2266 → 2266, 새 zip 의 app.py = 리포 HEAD [확인 cmp]. 로컬 CodeSha256 `PNvET3qI…` [확인].
- Docker 스모크 (지금 실행함 — `public.ecr.aws/sam/build-python3.12:latest-arm64`, /opt/python = 새 layer, /var/task = 새 함수) →
  **`SMOKE_OK unauth=401`** [확인]: 무토큰 thumbnail 요청 401 · `REGISTRATION_STATUS_REVIEW` · `REG_ERR_REJECTED` 문구 글자 ·
  `_visible_to`(review ∧ 본인 True · 타 uid False · failed 본인 False · active True) · writer 3개 존재 · `set_registration_active` 없음 ·
  `diagnose_registration` 있음/`check_registration` 없음.

```bash
F=sunity-motion-pilot-playback-url
aws lambda update-function-configuration --function-name $F --layers $L:<새 버전>     # 먼저 layer
aws lambda wait function-updated --function-name $F
aws lambda update-function-code --function-name $F --zip-file fileb://$B/fn-pb-new.zip  # 그다음 코드
aws lambda wait function-updated --function-name $F
aws lambda get-function-configuration --function-name $F --query '{sha:CodeSha256,layers:Layers[].Arn,st:LastUpdateStatus}'
```
- **순서가 중요하다**: 코드를 먼저 올리면 옛 layer :23 에 `REGISTRATION_STATUS_REVIEW` 가 없어 isActive false doc 요청이 500 이 된다 [확인 코드 — `_visible_to` 는 isActive false 일 때만 그 상수를 읽는다].
- 라이브 판별(배포 뒤, 쓰기 0) — w9l E-4 와 같은 방식(TESTB 커스텀 토큰): `ref-kip-up` 영상 200 · `ref-kip-up` thumbnail 404 · 무토큰 401. review doc 소유자 판별은 review doc 이 생긴 뒤(38-14 Task 3 재시도) [미확인].

### (3) reference-upload-url — 새 layer 붙일지 **belle 선택**

- 코드 변경 없음. 새 layer 의 차이(3파일) 중 이 함수가 쓰는 것은 `create_reference_registration` · models 상수인데 둘 다 **추가만** 있다 — 동작 차이 0 [확인 diff — create_reference_registration 무변경].
- 붙이면: 모든 공급자 경로 함수가 같은 models 를 본다(정합). 안 붙이면: 롤백 대상이 하나 줄어든다.
```bash
aws lambda update-function-configuration --function-name sunity-motion-pilot-reference-upload-url --layers $L:<새 버전>
aws lambda wait function-updated --function-name sunity-motion-pilot-reference-upload-url
```

### (4) pipeline Lambda — 배포 불필요

- `pipeline/app.py:332-380` `_handle_reference_upload` 는 doc 확인 → Pod 상태 → `set_registration_queued` 또는 claim → `_delegate_to_runpod(/register-reference)` 뿐이고 `_register_reference` 를 직접 돌리지 않는다 [확인 코드]. `_register_reference` 의 호출처는 `runpod_inference/server.py` 하나 [확인 grep].
- review doc 이 중복 S3 이벤트로 다시 오면 `status != registering` 이라 skip [확인 코드 :352-358 + 테스트 `test_reput_after_registration_is_skipped_and_v1_immutable[review]`].
- 자기 재현성 분석은 Lambda 가 Pod 로 위임하는 기존 경로 — 채점 쪽은 isActive 를 읽지 않는다 [확인 플래너 grep + `get_reference_motion` 가드 없음].

### (5) Pod — 지금 꺼져 있음. 38-14 재개 때

**등록 동작 변경(진단 전용 · review)은 Pod 코드에서만 산다** — Pod 가 새 코드를 받기 전까지는 등록이 옛 판정(fail-closed)으로 돈다.
```bash
# 볼륨 리포에서 — 38-14-E2E.md '관측 — Pod 재배포 (2026-10-01 11:25~11:28 KST)' 절과 같은 절차
# (재기동 전 Pod 로그를 먼저 scp — 메모리 pod-log-truncated-on-server-restart)
git fetch origin -q && git reset --hard origin/main -q            # → 2989c191 이상
md5sum backend/runpod_inference/start_server.sh /workspace/start_server.sh   # 다르면 사본 갱신
pkill -f "[u]vicorn runpod"                                       # 별도 ssh 호출
export RUNPOD_POD_ID=<pod id>; source /workspace/aws_env.sh; nohup bash /workspace/start_server.sh > /workspace/start_server_thx.log 2>&1 < /dev/null &
curl -s https://<pod-proxy>/health                                # commitSha == push 한 HEAD(2989c191 이상) 확인
```
- requeue 보다 먼저 올린다(MEMORY 착수점의 "Pod 코드 배포를 requeue 보다 먼저" 그대로).

### (6) 웹 — 공급자 홈 '검수 중' · 반려 사유

```bash
cd app && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist
aws s3 sync app/dist s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"
aws cloudfront wait invalidation-completed --distribution-id E16SR4IPFYH46Q --id <무효화 id>
curl -s https://d2ivnoigym2xlu.cloudfront.net/supplier | grep -o 'entry-[0-9a-f]*\.js'   # = 새 dist entry
```
- 번들 빌드는 지금 성공 확인만 했다(scratchpad `thx-web`, entry `entry-d28ff348…js`, 번들 안에 '검수 중 · 확인 뒤 수강생에게 보여요' 1곳) [확인]. 배포 때는 app/dist 로 다시 만든다.
- 옛 번들(라이브)은 review 를 미지 값 → '올린 영상 확인 중' 으로, rejected 를 미지 코드 → server_error 문구로 보인다 [확인 코드 `supplierRules.ts` 기본값]. **반려(reject)를 쓰기 전에 웹을 올려야** 공급자가 사유를 본다.

### (7) OTA — 불필요

- 수강생 앱 동작 변화 없음: picker 는 `isActive === false` 를 이미 숨긴다(`referenceMotions.ts:79` 무변경) [확인]. 앱 타입(`analysis.ts`) 변경은 유니온 추가뿐 [확인 typecheck 0].
- iOS 앱 안에서 `/supplier` 라우트: 파일은 번들에 들어 있지만(expo-router 파일 라우트) 수강생 화면 어디에도 그쪽으로 가는 `router.push`/`href` 가 없다 [확인 grep — `/supplier` 이동은 `app/src/app/supplier/` 안에서만]. 도달 = 딥링크 `sunityaicoach://supplier` 뿐 [추정 — app.json scheme, 실기기 미시험].

## 배포 뒤 확인

review 상태 doc 이 아직 없으므로(Pod 꺼짐 · 새 Pod 코드 미배포) 라이브 확인은 **38-14 Task 3 재시도**에서 한다:

1. Pod 새 코드 (5) → 대역 TESTB 계정으로 재업로드.
2. Pod 로그 `register-reference diagnostics ref_id=… person_ratio=… low_conf=… stand_unreadable=… standing_start=… n_stand=…` + `register-reference review …`.
3. 공급자 홈 행 = '검수 중 · 확인 뒤 수강생에게 보여요' + 썸네일(소유자 예외, (2)).
4. `backend/.venv/bin/python backend/scripts/review_reference_registrations.py list` → 진단 요약 확인.
5. `… show <refId>` → `/Users/Shared/sunity-motion-review/<refId>/` 의 thumb · 10/50/90% 프레임을 belle 에게.
6. belle OK → `… approve <refId> --by ops:belle`(먼저 `--dry-run`).
7. 수강생 앱 picker 에 노출 → mode1 분석.

기존 실패 doc `dc7812c6…` · `fc4a393d…` 와 TESTB 정리는 38-14 Task 4 몫 — 이 명령서에서 건드리지 않는다.


## 배포 기록 (2026-10-01)

### R-0. 보존 (13:13Z 직전, 읽기만) — `/Users/Shared/sunity-motion-rollback/thx/` (drwx------)

| 파일 | 확인 |
|---|---|
| `before-config-playback-url.json` | get-function-configuration 원문 [확인] |
| `function-before-sunity-motion-pilot-playback-url.zip` | 로컬 sha `nRJilv5HScm2cfv4GxaN1cZ4xqkKgnf+ajZI6IPfZi8=` = AWS CodeSha256 [확인] |
| `layer-23.zip` | 로컬 sha `tZDzyZl1qzwo52M1IJADlNOYWQiD1fZjITk2bNKyd9s=` = :23 CodeSha256 [확인] |
| `web-before/` | 버킷 객체 60개 [확인] |
| `web-before-entry.txt` | `entry-4075a63379751acbfe7a55ccf8fbfadf.js` [확인] |

reference-upload-url 설정은 (3) 을 건너뛰어 보존하지 않았다.

### R-1. layer (13:13:37Z)

- 조립 = `layer-23.zip`(보존본) + HEAD `656c9c99` 의 3파일. 새 zip 의 sunity_shared/*.py 119개 전부 = HEAD [확인 cmp, 차이 0] ·
  :23 대비 바뀐 파일 = models · firestore_admin · analysis/registration_checks **3개뿐**(zip 안 전 파일 비교) [확인] · 파일 수 1105 → 1105 [확인].
- 게시 전 Docker 스모크(새 layer + 새 playback-url, arm64) → `SMOKE_OK unauth=401` [확인] (rejected 문구 단언을 새 글자로 바꿔서 다시 돌림).

```bash
aws lambda publish-layer-version --layer-name sunity-motion-pilot-shared \
  --description "quick-261001-thx review state + approve/reject + diagnoses (from :23 + 3 files)" \
  --zip-file fileb://<scratch>/thx-build/layer-new.zip --compatible-runtimes python3.12 --compatible-architectures arm64
```
→ **Version 24** · `arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared:24` · CodeSha256
`kZJQWDFyKRppF0ISG7bI/9V5h/7S47x8aZUAymwqlEU=` = 로컬 zip [확인] · 16,644,258 B.

### R-2. playback-url (13:13:53Z ~ 13:14:13Z) — layer 먼저, 코드 나중

```bash
aws lambda update-function-configuration --function-name sunity-motion-pilot-playback-url --layers <:24 ARN>   # → wait
aws lambda update-function-code --function-name sunity-motion-pilot-playback-url --zip-file fileb://<scratch>/thx-build/fn-pb-new.zip   # → wait
```

| 항목 | 전 | 후 |
|---|---|---|
| layer | `:23` | **`:24`** [확인] |
| CodeSha256 | `nRJilv5H…` | `VcZQ59dX2YJWqo1xhw38IY8YHtha+vOHDg99msVtQWA=` = 로컬 zip [확인] |
| LastUpdateStatus | — | **Successful** [확인] |
| LastModified | 2026-09-30T15:21:17Z | 2026-10-01T13:14:09Z [확인] |

- 함수 zip = 보존본 + `app.py`(HEAD) 만, 파일 수 2266 그대로 [확인].
- template.yaml · IAM · 환경변수 무변경 — sam deploy 안 함. 이 :24 는 CFN 밖 드리프트(다음 `sam deploy` 가 스택 정의로 되돌린다) [추정 — w9l 과 같은 구조].
- reference-upload-url(:23) · pipeline(:21) 무접촉 [확인 — 명령 안 씀].

### R-3. 웹 (13:14:39Z ~ 13:15:04Z)

```bash
cd app && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist     # entry-b11437910972ee1a184af30fb929b4b5.js 2.97 MB
aws s3 sync app/dist s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"   # IBUCA5QK6UNO7SLDR7CVATU667
aws cloudfront wait invalidation-completed --distribution-id E16SR4IPFYH46Q --id IBUCA5QK6UNO7SLDR7CVATU667
```
- app/dist 는 gitignore(`app/.gitignore:8 dist/`) [확인].

### R-4. 배포 뒤 확인 (13:15~13:17Z, 쓰기 0)

웹 [확인 curl + 번들 텍스트 검색]:
- `/supplier` **200**, index.html → `entry-b11437910972ee1a184af30fb929b4b5.js` = 새 dist.
- 새 문구 있음: '운영팀 확인 중 · 끝나면 수강생에게 보여요' 1 · '잘 찍는 팁' 1 · '운영팀 확인에서 등록되지 않았어요' 2 · '위 3가지를 확인했어요' 1 · '촬영 팁' 1 · '내 강사 코드를 수강생에게 알려 주는 법' 1.
- 옛 문구 없음: '등록이 안 되는 4가지' 0 · '검수에서 반려' 0 · '위 4가지를 확인했어요' 0 · '서 있는 자세에서 시작했어요' 0 · '서 있는 자세에서 시작 · 소리' 0.
- '촬영 TIP!' 1 은 같은 웹 번들에 들어 있는 **수강생 앱 로딩 화면**(`app/src/app/analysis/loading.tsx:517`) 것이다 — 공급자 문구가 아니고 이번 범위 밖 [확인 grep].

playback-url — TESTB 커스텀 토큰(uid `UmH3…`) → signInWithCustomToken → ID 토큰. 스크립트 = scratchpad `thx_livecheck.py`(휘발) [확인]:

| # | 요청 | 결과 | 뜻 |
|---|---|---|---|
| P0 | 무토큰 `{referenceMotionId:'ref-kip-up'}` | **401** unauthorized | 인증 가드 그대로 |
| P1 | `ref-kip-up` 영상 | **200** 604800 | legacy 영상 재서명 무회귀 |
| P2 | `ref-kip-up` thumbnail | **404** not_found | 키 없는 legacy doc |
| P3 | `ref-kip-up` coachAudio | **400** bad_request | 다른 asset 거부 |
| P4 | 소유자(TESTB) failed doc `dc7812c6` · `fc4a393d` thumbnail | **404** · **404** | review 아닌 비활성 doc 은 소유자여도 404 (새 `_visible_to`, 라이브) |
| P5 | 같은 두 doc 영상 | **404** · **404** | 같음 |

- review 소유자 200 은 review doc 이 아직 없어 못 봤다 [미확인 — 38-14 Task 3 재시도. 단위 테스트 + Docker 스모크로만 확인].
- 부작용: TESTB reference doc 수 전후 2 → 2 [확인 Admin 읽기]. Auth lastSignIn 갱신 [추정].

검수 CLI (라이브 Firestore, 읽기만):
- `review_reference_registrations.py list` → `검수 대기 0건`, exit 0 [확인] — 실 Firestore 에서 `registrationStatus == 'review'` 단일 등가 쿼리가 돈다.

남은 확인 = 위 '배포 뒤 확인' 1~7(Pod 새 코드 → 대역 재업로드 → review → list/show → belle OK → approve → picker). Pod 는 38-14 재개 때.

## 배포 기록 2 (2026-10-01) — 승인 전 한 문구 · deactivate 명령

> belle 10-01 답 3건 반영("아주 심플하게 만들면 돼"). 코드 커밋 `e1a74f51`(push `4a0ff2c1..e1a74f51`). **웹만** 배포했다.

### 무엇을, 왜 이것만 배포했나

- 웹: 공급자 행의 승인 전 네 상태(registering · queued · processing · review)를 한 문구 '확인 중 · 끝나면 수강생에게 보여요' 로, 가이드 §4 '대기 중' 줄 삭제, 서버 꺼짐 알약 둘째 줄 '켜지면 올린 동작을 이어서 처리해요.'.
- **layer 재게시 안 함.** 바뀐 서버 쪽 코드 = `firestore_admin.deactivate_reference_registration` 추가뿐이고, 호출자는 로컬 운영 CLI(`review_reference_registrations.py deactivate`) 하나다. `backend/functions` · `backend/runpod_inference` 에서 이 함수를 부르는 곳 0 [확인 grep]. CLI 는 리포의 `backend/shared/python` 을 직접 import 하므로 layer 와 무관하다 [확인 — 스크립트 `_LAYER` sys.path]. models.py 는 이번에 안 바뀌었다 [확인 git diff 656c9c99..e1a74f51 -- models.py 0줄].
  → layer :24 의 firestore_admin.py 는 이제 리포 HEAD 보다 함수 하나가 적다(쓰는 Lambda 없음). 다음 layer 게시 때 자연히 들어간다.
- Pod 는 38-14 재개 때 HEAD 를 받으므로 그때 같이 들어간다(Pod 도 이 함수를 쓰지 않는다).

### W-0. 보존 (13:25Z 직전) — `/Users/Shared/sunity-motion-rollback/thx/web-before-2/` (drwx------)

- 버킷 객체 60개 [확인] · 배포 전 라이브 entry = `entry-b11437910972ee1a184af30fb929b4b5.js`(배포 기록 1 의 웹) → `web-before-2-entry.txt` [확인].

### W-1. 웹 (13:25:33Z ~ 13:25:59Z)

```bash
cd app && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist     # entry-394e74aeb945c1696825abb05949fe17.js 2.97 MB
aws s3 sync app/dist s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"   # I417VO9JEK2NZQZXH2OHWZZEJ2
aws cloudfront wait invalidation-completed --distribution-id E16SR4IPFYH46Q --id I417VO9JEK2NZQZXH2OHWZZEJ2
```

### W-2. 배포 뒤 확인 (curl + 번들 텍스트 검색) [확인]

- `/supplier` **200**, index.html → `entry-394e74aeb945c1696825abb05949fe17.js` = 새 dist.
- 새 문구: '확인 중 · 끝나면 수강생에게 보여요' 1 · '켜지면 올린 동작을 이어서 처리해요.' 1.
- 옛 문구 0: '올린 영상 확인 중' · '운영팀 확인 중' · "'대기 중'으로 있다가" · '켜지면 대기 중인 동작' · '등록 중 · 몇 분 걸려요'.

### 롤백 (웹만)

```bash
export AWS_PROFILE=sunity-motion
aws s3 sync /Users/Shared/sunity-motion-rollback/thx/web-before-2 s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"
```
(배포 기록 1 이전으로까지 되돌리려면 `web-before/` 를 같은 방식으로.)
