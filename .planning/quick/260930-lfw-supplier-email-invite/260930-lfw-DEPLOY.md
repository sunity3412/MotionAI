# quick-260930-lfw 배포 기록 — 공급자 메일 초대 (Lambda layer+코드 · SSM v1 되돌림 · 이관)

> **상태: 멈춤 (F 라이브 확인 중 체크포인트).** 콜드 호출이 함수 타임아웃 10초를 넘는다(아래 F).
> 고치려면 함수 설정(Timeout·Memory)을 바꿔야 한다. 이 값은 CFN 템플릿이 관리한다 → belle 결정 대기.
> G(웹 재배포)·F 7~8행은 아직 하지 않았다.

- 실행: 2026-09-30 07:14~07:21 UTC (16:14~16:21 KST), 실행자 = gsd-executor (opus)
- `AWS_PROFILE=sunity-motion`, 계정 976369350031, 리전 ap-northeast-2
- 코드 기준: Task 1 `f433b6a3` · Task 2 `24c28248` · Task 3 `eaef58f3`
- 메일은 전부 가려 적는다. uid 는 앞 4자 + `…`. 롤백 보존물은 리포 밖 `/Users/Shared/sunity-motion-rollback/lfw/` 한 곳(폴더 700).

## 리소스

| 리소스 | 전 | 후 |
|---|---|---|
| 함수 `sunity-motion-pilot-reference-upload-url` layer | `sunity-motion-pilot-shared:21` | `sunity-motion-pilot-shared:22` |
| 함수 CodeSha256 | `q89ZcGTr5g/U8xaP2gVGNwTOF3y0Dnto+7loTuOKl8I=` | `an9JJEbDfzBHG7AzNk/tSGpRf5n3bM3suQiP4takjcw=` |
| 함수 Timeout / Memory | 10 s / 256 MB | 그대로 (바꾸지 않았다) |
| SSM `/sunity/motion/supplier-uids` | v2 `FDJr…:BELLE, UmH3…` | v3 = v1 값 `FDJr…:BELLE` |
| Firestore `suppliers` · `supplierCodes` · `supplierInvites` | 없음 | `suppliers/FDJr…` 1건 · `supplierCodes/BELLE` 1건 · 초대 0건 |
| 웹 버킷 `sunity-motion-pilot-supplier-web` | 38-13 번들 | 그대로 (G 안 함) |

전 값 원본: `lambda-before.json`(env 는 키 이름만).

## A. 멈춤 조건 확인 (쓰기 전)

- 새 코드가 읽는 SSM = `firebase-sa`(인증 초기화, 이미 쓰던 것) · `supplier-uids`(이미 쓰던 것) 둘뿐이다 [확인 코드]. `belle-uid` 는 env `BELLE_UID` 로 이미 들어온다(템플릿 `{{resolve:ssm:…}}`).
- 함수 역할의 ssm 리소스 = 위 두 파라미터(`backend/template-38-09-deploy.yaml:203-206`) [확인].
- Firestore 쓰기는 Admin SA 로 한다 — IAM 과 무관 [확인 코드]. 새 AWS 리소스 0.
- → 쓰기 전 판단: IAM·CFN 변경 필요 없음. **단 F 에서 타임아웃 문제가 새로 나왔다(아래).**
- 쓰기 전 관측(3일 로그): 콜드 probe = handler 약 4.9 s + Init 약 0.95 s(인증 초기화만, Firestore 없음) [확인 CloudWatch REPORT].

## B. 보존 (07:14:39Z)

```
/Users/Shared/sunity-motion-rollback/lfw/function-before.zip   33,322,088 B  base64 sha256 = q89ZcGTr5g/… (= AWS CodeSha256)
/Users/Shared/sunity-motion-rollback/lfw/layer-21.zip          16,630,042 B  base64 sha256 = aZdI7F6x…   (= :21 Content.CodeSha256)
```

layer :21 안 파일 sha256 ↔ 이 플랜 전 커밋(`f433b6a3^`) 대조 [확인]:

| 파일 | 결과 |
|---|---|
| models.py | SAME (3266e8b1f106) |
| firestore_admin.py | SAME (a7b498457f2f) |
| auth.py | SAME (a0d338ff3522) |
| responses.py | SAME (7e3ee19b3654) |
| `sunity_shared/*.py` 파일 목록 전체 | SAME |
| 함수 zip `app.py` | SAME (38ab3f2e5072) |

드리프트 0.

## C. 새 zip

- layer = :21 zip 복사본 + 리포 5파일 덮어쓰기(models · firestore_admin · auth · responses · supplier_invites). 파일 1103 → 1104.
- 함수 = 옛 함수 zip 복사본 + `app.py` 만 덮어쓰기. 파일 2266 그대로.
- 스모크 [확인]: Mac venv 는 layer 의 linux arm64 numpy 를 못 읽어 실패 → Docker `public.ecr.aws/sam/build-python3.12:latest-arm64` 에서 `/opt/python` + `/var/task` 로 `import app` · `firestore_admin.accept_supplier_invite` · `auth.verify_request_claims` 존재 · 무토큰 호출 401 `unauthorized` → `SMOKE_OK`.

## D. 배포 (07:15:53Z ~ 07:16:19Z)

```bash
export AWS_PROFILE=sunity-motion
F=sunity-motion-pilot-reference-upload-url
aws lambda publish-layer-version --layer-name sunity-motion-pilot-shared \
  --description "quick-260930-lfw supplier email invite (from :21 + 5 files)" \
  --zip-file fileb://<scratch>/lfw-build/layer-new.zip \
  --compatible-runtimes python3.12 --compatible-architectures arm64
#   → arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared:22
aws lambda update-function-configuration --function-name $F \
  --layers arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared:22
aws lambda wait function-updated --function-name $F          # 07:16:05Z
aws lambda update-function-code --function-name $F --zip-file fileb://<scratch>/lfw-build/function-new.zip
aws lambda wait function-updated --function-name $F          # 07:16:19Z
```

- 확인 [확인]: Layers[0] = `:22`, LastUpdateStatus `Successful`, CodeSha256 = 로컬 zip base64 sha256 `an9JJEbD…`.
- **이 함수 하나만** :22 로 바꿨다. 배포 스택의 다른 5함수는 :21 그대로 — CFN 밖 드리프트다(다음 `sam deploy` 가 :21 계열로 되돌린다).

## E0. SSM supplier-uids v1 되돌림

1. 읽기: 값 `FDJr…:BELLE, UmH3…` · Version 2 · Type String [확인].
2. 롤백 파일 `/Users/Shared/sunity-motion-rollback/lfw/ssm-supplier-uids-rollback.sh` (600) — v2 원문으로 put-parameter 한 줄.
3. 이력: v1 = `FDJr…:BELLE` 한 항목(2026-09-30 07:43:56 KST), v2 = `FDJr…:BELLE, UmH3…`(14:41:03 KST) [확인]. v1 항목 = v2 첫 항목 · UmH3 없음 확인 뒤 진행.
4. `put-parameter --overwrite` v1 값 → **Version 3, 2026-09-30T07:16:59Z (16:16:59 KST)**.
5. 재읽기 = v1 값과 같음 [확인].
6. Lambda SSM 캐시 60초 → **Task 5 시작 가능 시각 = 07:17:59Z (16:17:59 KST) 이후.** (새 코드 컨테이너는 07:16:19Z 이후에 떴고, 되돌림 전 40초 사이 SSM 을 읽은 요청은 무토큰 1건뿐이라 v2 를 캐시한 컨테이너는 없다 [추정 — 로그의 START 기준].)

## E. 이관 (07:17:49Z)

- dry-run: `belle-uid: FDJr…` · 대상 uid 1개 · `plan uid=FDJr… code=BELLE email=- -> create` [확인].
- 실행: `created uid=FDJr… code=BELLE email=-` → `list`: 초대 0건, 공급자 1명 (FDJr…, BELLE, active True) · `supplierCodes/BELLE` = {supplierUid FDJr…, displayName null, active true} [확인].
- UmH3… 는 이관도 deactivate 도 하지 않았다(suppliers doc 없음 → 명단 밖).

### 관측 — BELLE 계정(FDJr…)은 로그인 수단이 없다

- Firebase Auth `FDJr…`: provider 0개, email 없음, 표시 이름 없음, 생성 2026-05-27, 마지막 로그인 2026-06-12 [확인 Admin SDK].
- `UmH3…`: provider `google.com`, 메일 `c***@gmail.com`, 마지막 로그인 2026-09-30 05:28Z [확인].
- 진단(재검증 대상): FDJr… 는 익명(게스트) 계정으로 보인다 [추정 — provider 0]. `/supplier` 는 익명 세션을 로그인 전(A-1)으로 다룬다. 그러면 Task 5 4) "본 계정으로 로그인 → 홈 BELLE" 는 Google 로그인으로는 FDJr… 에 닿지 않을 수 있다 [미확인 — belle 의 다른 Google 계정 uid 는 모른다].

## F. 라이브 확인 (일회용 계정 — 멈춤)

- 계정: Admin SDK `lfwtest-a`(검증) · `lfwtest-b`(미검증) · `lfwtest-c`(검증), 메일 `lfw-{a,b,c}@sunity-test.invalid`. custom token → Identity Toolkit `signInWithCustomToken` → ID 토큰.
- ID 토큰 payload 에 `email`·`email_verified` 클레임이 있다(a/c true, b false) [확인].
- 요청은 `Origin: https://d2ivnoigym2xlu.cloudfront.net` 을 붙인다(HTTP API CORS 는 Origin 이 있을 때만 ACAO 를 단다 [확인 curl 비교]).

| 행 | 기대 | 결과 | 표식 |
|---|---|---|---|
| 1 무토큰 | 401 + ACAO `*` | 401 `unauthorized` · ACAO `*` · 98 ms | [확인] |
| 2 a 초대 없음 | 403 not_invited + a 메일 | **500** `Internal Server Error` · 10,085 ms · REPORT `Status: timeout` 10000 ms | × |
| 3 create QZTEST → a probe | 200 QZTEST · 시험 | create 두 줄 출력 [확인] · probe **500** 10,896 ms · timeout · suppliers/lfwtest-a 없음 · 초대 pending 그대로(트랜잭션 미커밋) | × |
| 4 a 다시 | 200 | **500** 10,910 ms · timeout | × |
| 5 b(미검증) + 초대 QZTSTB | 403 not_invited, 초대 pending | 403 `not_invited` · email = b 메일 · 초대 pending [확인] · 10,841 ms(함수 약 9.9 s — 한도 직전) | [확인] |
| 6 c 초대 → revoke → probe | 403 | revoke 출력 `status=revoked` · probe 403 `not_invited` · 208 ms(warm, 수락 트랜잭션 포함) [확인] | [확인] |
| 7 deactivate → 65 s → a | 403, 초대 revoked | 안 함(멈춤) | [미확인] |
| 8 reactivate → 65 s → a / 재초대 exit 1 | 200 / exit 1 | 안 함 | [미확인] |
| 9 CloudWatch 원문 메일 | 원문 0, 가린 메일만 | 이 시간대 로그에서 `lfw-[abc]@` 원문 0건 · `email=l***@sunity-test.invalid` 2건 [확인] | [확인](실행한 행만) |

관측 [확인 CloudWatch REPORT, 07:18~07:20Z]:
- 콜드 컨테이너(INIT 뒤 첫 인증 호출) 3건 모두 `Duration 10000.00 ms Status: timeout`, Max Memory 187~189 MB / 256 MB.
- 타임아웃은 컨테이너를 버린다 → 다음 호출도 콜드 → 연속 500.
- 행 5(수락 시도 없음 — 미검증 메일)는 콜드인데 함수 약 9.9 s 로 겨우 끝났다. 그 뒤 warm 호출(행 6)은 141 ms.

진단(재검증 대상):
- 원인 = probe 경로에 Firestore 가 새로 들어왔다. 콜드 한 번에 인증 초기화(전: 약 4.9 s) + Firestore 클라이언트 초기화·첫 읽기 + (검증 메일이면) 수락 트랜잭션이 겹쳐 10 s 를 넘는다 [추정 — 구간별 시간은 재지 않았다].
- 선례: playback-url 도 같은 문제로 Timeout 30 · Memory 512 로 고쳤다(`template-38-09-deploy.yaml` 주석 "32-16 실측: cold auth 7.7s + Firestore 첫 init ~6s > 10s").

지금 운영 상태 [확인 + 추정 표시]:
- 함수는 새 코드(:22). warm 이면 정상, 콜드면 500 이 날 수 있다 [확인 행 2~4].
- 웹은 38-13 옛 번들이다. 옛 번들은 403 을 옛 A-2(내 ID 상자)로, 500 을 오류 문구 + 다시 시도로 보여 준다 [확인 코드 — 옛 번들 분기는 상태코드 기준].

뒤처리 [확인 07:20:31Z]: 일회용 Auth 사용자 3개 삭제 · `suppliers/lfwtest-*` · `supplierCodes/QZTEST|QZTSTB|QZTSTC` · `supplierInvites/lfw-*` 삭제 → 재조회 전부 0건. 남은 것 = suppliers `FDJr…` 1건 · supplierCodes `BELLE` 1건 · 초대 0건(이관 결과).

## G. 웹 재배포 — 안 함 (F 멈춤)

재개 때 순서: 먼저 보존 `aws s3 sync s3://sunity-motion-pilot-supplier-web /Users/Shared/sunity-motion-rollback/lfw/web-before/` → 빌드 → sync `--delete` → 무효화.

## H. 규칙 무접촉

- `firestore.rules` git diff 0 (이 플랜 커밋 3개에 없음) [확인 — 재개 때 verify 로 다시 본다].

## 롤백

```bash
export AWS_PROFILE=sunity-motion
F=sunity-motion-pilot-reference-upload-url

# 1) layer 를 :21 로
aws lambda update-function-configuration --function-name $F \
  --layers arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared:21
aws lambda wait function-updated --function-name $F

# 2) 함수 코드를 보존 zip 으로
aws lambda update-function-code --function-name $F \
  --zip-file fileb:///Users/Shared/sunity-motion-rollback/lfw/function-before.zip
aws lambda wait function-updated --function-name $F

# 3) SSM supplier-uids 를 v2 로 (정확한 값은 롤백 파일에만 — 아래는 값 가림)
#    aws ssm put-parameter --name /sunity/motion/supplier-uids --type String --overwrite --value 'FDJr…:BELLE, UmH3…'
sh /Users/Shared/sunity-motion-rollback/lfw/ssm-supplier-uids-rollback.sh

# 4) 웹 (G 를 한 뒤에만) — 보존본으로 되돌리고 무효화
aws s3 sync /Users/Shared/sunity-motion-rollback/lfw/web-before/ s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"
```

- Firestore `suppliers/FDJr…` · `supplierCodes/BELLE` 는 옛 코드가 읽지 않는다 — 롤백 때 남겨도 동작 영향 0. 지우려면 Admin SDK 로 두 doc delete.
- layer :22 버전 자체는 남겨도 된다(참조하는 함수가 없으면 무해).
- Task 5 의 deactivate 뒤에는 SSM 을 v2 로 되돌려도 UmH3… 는 suppliers doc(active False)이 우선해 막힌다(결정 (b)).

## 폰 확인 (Task 5)

(오케스트레이터가 적는 자리 — TESTB 초대·회수: 두 번째 계정 uid 앞 4자 · 가린 메일 · 시각)
