# quick-260930-w9l — 배포 기록

> **상태: Task 6 끝 — 배포 완료(2026-09-30 15:20~15:24Z = 10-01 00:20~00:24 KST).** layer **:23** → reference-upload-url · playback-url · 웹 재배포(무효화 `IA83OV9SRXLSAVLLUPILU2U5Q9`) · OTA preview ios group **`62eb42e4-afa8-443d-8afa-ff55757bbd59`**. Pod 코드는 38-14.
> 코드 커밋: `301d4d02`(백엔드 계약) · `b18e279a`(Pod 등록 경로 + playback-url) · `59a5d1e8`(앱 규칙·문구·가이드·라벨) · `ea6a7560`(앱 화면·썸네일) · `faf83234`(belle 10-01 판정 뒤 수리 2건).
> belle Task 5 판정 원문(10-01): *"가 : 그렇게 해 / 나 : 응 / 다 : 응"* — 가 = 홈 초급 첫 카드 '입문' 접두어 빼기, 나 = 가이드 s6 낡은 '(입력 칸은 다음 업데이트에서 열려요)' 삭제, 다 = 배포 계획 ○.

## A. 게이트 (Task 4 끝, 2026-10-01 00:0x KST)

| 게이트 | 결과 |
|---|---|
| backend `.venv/bin/python -m pytest tests -q` | **5755 passed, 20 skipped** [확인] (플랜 기준 "5566 부근" — 실제 수) |
| app `npm run typecheck` | 0 오류 [확인] |
| app `node --test src/lib/*.test.ts src/constants/*.test.ts` (7파일) | **82 tests, 82 pass, 0 fail** [확인] |
| 웹 번들 `CI=1 npx expo export --platform web --output-dir <scratchpad>/w9l-web` | 성공 — entry `entry-d770bcb0…js` 2.97 MB [확인]. dist 는 Task 6 이 app/dist 로 다시 만든다 |
| `REFERENCE_COMBO_MAX_DURATION_SEC` (backend shared·functions·scripts·runpod_inference · app/src) | 0건 [확인 grep] |
| 표시 문자열 `'기본기'` (app/src) | 0건 [확인 grep]. 주석 속 Figma 원문 인용 1곳(`(tabs)/index.tsx:51`)은 그대로 |

## B. 시뮬레이터 (수강생 앱)

관측:
- 기기 iPhone 16 Pro iOS 18.6 (`873D7CB3-…`), Debug dev client + Metro `:8081` (`npx expo start --ios --port 8081`, 백그라운드로 켜 둠) [확인]. Metro `iOS Bundled 16833ms … (1475 modules)` [확인].
- 번들 신선도 = 02 에 새 탭 문구 '초급' 이 보인다 [확인].
- 게스트로 시작하기 → 기존 익명 사용자(분석 기록 있음, 평균 69점) [확인 화면].

| 파일 | 관측 |
|---|---|
| `sim/01-home.png` | 홈. '오늘 도전해볼 동작' 3개 = 엘보 트위스트 시스터(고급 새로 추가됨) · 콤보(고급) · 폭스탑(고급), 셋 다 번들 썸네일(실사 프레임) 그대로 [확인]. 고급 우선 정렬이라 초급 카드는 이 화면에 없다 [확인] |
| `sim/02-reference-tabs.png` | 홈 '전체보기' → 기준 동작 선택. 탭 **'초급'**(선택) · 중급 · 고급. 초급 목록 = 클라임 · 킵업 · 피터팬(정은지) [확인] |

시뮬에서 못 본 것:
- 공급자 화면(STEP 01/02 · 가이드 · 내 동작 행) — 로그인 필요, 웹 전용 라우트 [미확인 — belle 폰, 배포 뒤].
- 공급자 등록 기준 동작의 원격 썸네일 — 활성 공급자 등록 doc 이 없다(Pod 꺼짐, Pod 코드 미배포) [미확인 — 38-14 첫 등록 뒤].
- 홈 초급 카드 문구: 첫 초급 카드는 `입문 ${레벨}` 이라 이제 **'입문 초급'** 이 된다 [확인 코드 `(tabs)/index.tsx` challengeCopy]. 이 화면엔 초급 카드가 안 떠서 실물은 못 봤다 [미확인]. 플랜 범위 밖이라 안 고쳤다 — belle 판정 대상.

## C. OTA 사전 점검 (쓰기 0 — 발행 안 함)

관측:
- `eas whoami` = sunity3412@gmail.com [확인].
- 최신 TestFlight iOS 빌드: profile testflight-preview · channel **preview** · appVersion 1.2.4 (build 40) · runtime **1.2.4** · gitCommit `d95f2885` · 2026-09-03 · STORE [확인 eas build:list].
- 채널 `preview` → 브랜치 `preview` 하나(branchMappingLogic true) [확인 eas channel:view].
- app.json version 1.2.4 · runtimeVersion policy → 발행 runtime 1.2.4 = 빌드 40 runtime 일치 [확인 app.json · o0u §E 와 같음].
- 네이티브 변경: `d95f2885..HEAD` 의 app/package.json 1줄(react-native-web, 웹 전용 — o0u §D 에서 확인된 같은 줄) · app.json/lock 변경은 o0u 이전 것 [확인 git diff --stat]. 이번 w9l 은 의존성 추가 0 [확인].
- 브랜치 preview 최신 group = **`b2b148b4-a789-49fe-bd18-b926fefb8fa9`** · ios · runtime 1.2.4 · gitCommit `e813c9ee` · 2026-09-30T09:23:31Z (o0u 발행분) [확인 eas update:view]. → **롤백 대상 group = b2b148b4** (플랜 예상과 같다).
- OTA 로 같이 나갈 앱 커밋(`e813c9ee..HEAD -- app/src`): `301d4d02`(analysis.ts 문구 + supplierCopy row.fail) · `59a5d1e8`(규칙·문구·라벨) · `ea6a7560`(화면·썸네일) [확인 git log]. 수강생 앱에서 보이는 변화 = 레벨 '초급'(기준 선택 탭 · 홈 카드 문구) + 홈 도전 카드의 등록 썸네일 배선(지금은 해당 동작 없음) [확인 코드].

발행 명령(아직 안 함, Task 6):
```
cd app && npx eas update --branch preview --platform ios --message "quick-260930-w9l: 레벨 초급 + 기준 동작 썸네일 배선" --non-interactive
```
롤백:
```
cd app && npx eas update:republish --group b2b148b4-a789-49fe-bd18-b926fefb8fa9 --message "ROLLBACK: quick-260930-w9l" --non-interactive
```

## D. Task 2 조사 (코드 변경 없음)

- (a) pipeline Lambda 의 `reference/` 분기는 `_handle_reference_upload` 로 가고, 이 함수는 doc 확인 → Pod 상태 → claim → `_delegate_to_runpod(url=/register-reference)` 뿐이다 [확인 `pipeline/app.py:328-392`]. `_register_reference` 호출처는 `runpod_inference/server.py:262` 하나 [확인 grep]. → 바뀐 등록 코드는 Pod 에서만 돈다. pipeline Lambda 배포 불필요 [확인 — 호출 경로 기준].
- (b) 수강생 `_process` 경로에 서버 쪽 길이·용량 상한은 없다 — `MAX_VIDEO_BYTES`·길이 검사는 `validate_upload_request`(upload-url Lambda, 수강생 presign 때)와 `_register_reference` 에만 있다 [확인 grep `pipeline/app.py`]. 자기 재현성은 v1 을 `uploads/` 로 **서버 복사**해 upload-url Lambda 를 거치지 않으므로, 120초·최대 1GB 기준 영상이 그대로 `_process` 에 들어간다 [확인 코드 `_trigger_self_check`]. `_process` 의 `extract` 는 end_s 캡이 없다 [확인 `pipeline/app.py:1877`] — 2분 영상 = 9fps 기준 약 1080 프레임 [추정 — 산술]. 처리 시간·메모리 영향은 [미확인 — 38-14 실측].
- (c) `REGISTRATION_LEASE_SEC` 900 · extract 캡 121초 × 9fps · Pod 디스크가 1GB 4K 2분에 충분한가 [미확인 — 38-14 실측]. 무음본은 스트림 복사라 로컬 디스크를 원본만큼(최대 약 1GB) 한 번 더 쓴다 [확인 코드 — 임시 파일 두 벌].
- (d) 앱에서 기준 영상 원본을 소리 켜고 재생하는 곳: 없음. VideoCompare(`muted = true` :574·579) · PoseCompareFrames(:75) · 공급자 미리보기(SupplierUi VideoPreview/VideoThumb muted) [확인]. ReferenceCornerSection 은 회전 참고 영상(`results/…/rotation.mp4`) [확인 :85]. RenderedComparePlayer 는 서버 합성 영상이고 그 소리는 코칭 TTS mp3 만 amix 한다 [확인 `compare_render.py` audio_plan 1743-1951].
- supplierRules.mapPresignFailure 는 상태코드만 본다(401 · 403 · 0 · 나머지 presignFail) [확인 코드]. → 서버 기준 경로 too_large(400) · supplier_name_missing(409) 모두 화면에선 presignFail 문구('잠깐 문제가 있었어요…')로 나온다 [확인 fixture apiFailures 2행 추가]. 앱이 1GB 를 먼저 거르고, 이름 없음은 '다음' 을 먼저 막으므로 이 분기에 닿는 것은 신고 크기 우회·경합뿐이다 [추정].

## E0. belle 판정 뒤 수리 — `faf83234`

- 홈 도전 카드 첫 초급 카드 부제 = 레벨명만('초급') — `(tabs)/index.tsx` challengeCopy `입문 ${lv}` → `lv`, 주석에 Figma 원문 '입문 기본기' 와 belle 10-01 결정 [확인 diff]. 이 문자열을 잠근 테스트·fixture 는 없었다 [확인 grep '입문' app/src — profile.tsx '입문 (기본값)' 은 다른 화면이라 그대로].
- 가이드 s6 둘째 줄에서 ' (입력 칸은 다음 업데이트에서 열려요)' 삭제 — supplierCopy.ts 와 docs/supplier-guide.md 같은 글자, supplierCopy.test.ts 에 새 값 + md 에 옛 문구 없음 잠금 [확인].
- 게이트: node 82/82 · typecheck 0 [확인]. 백엔드 무접촉 → pytest 재실행 안 함(마지막 전체 = 5755 passed) [확인].

## E. 배포 기록

### E-1. 드리프트 대조 (배포 전, 읽기만)

- 배포 전 상태 [확인 get-function-configuration]:

| 함수 | layer | CodeSha256 | LastModified |
|---|---|---|---|
| reference-upload-url | `:22` | `an9JJEbD…` | 2026-09-30T07:49:47Z |
| playback-url | `:21` | `9Y2ahu2W…` | 2026-09-29T23:57:22Z |

  다른 4함수(upload-url · pipeline · reference · reference-auto-register)는 `:21` [확인 list-functions].
- 보존 zip 의 base64 sha256 = AWS CodeSha256 (두 함수, layer :21 · :22 모두) [확인].
- 드리프트: layer :22 의 sunity_shared/*.py 118개를 w9l 직전 커밋 `d7b00c89` 와 대조 → 다른 파일 = models.py · firestore_admin.py 둘, 차이는 전부 **추가 줄**(o0u instructorLinks 상수·함수 — :22 게시 뒤 커밋 `6e4b2e1e`) [확인 diff '>' 만]. 두 함수 zip 의 app.py = `d7b00c89` 와 같음 [확인].
- playback-url 은 :21 → :23 으로 lfw 변경(auth.verify_request_claims 추가 · verify_request 는 그 uid 만 반환 · responses.error extra 인자 추가)도 함께 받는다 — 둘 다 옛 호출 모양을 유지하는 추가다 [확인 diff :21↔:22]. 이 둘은 reference-upload-url 에서 09-30 부터 운영 중 [확인 lfw DEPLOY].

### E-2. 새 zip

- layer = `:22` zip 복사본 + 리포 HEAD 5파일 덮어쓰기(models · validation · firestore_admin · s3keys · analysis/reference_media 신설). 파일 1104 → 1105. 풀어서 HEAD 와 cmp: 5파일 + supplier_invites · auth SAME [확인].
- 함수 = 보존 zip 복사본 + `app.py` 만(각 2266 파일 그대로) [확인].
- 스모크(Docker `public.ecr.aws/sam/build-python3.12:latest-arm64`, /opt/python + 함수 폴더) [확인]: 두 핸들러 무토큰 → 401 unauthorized · `REFERENCE_MAX_VIDEO_BYTES` 1GB · `CONSENT_VERSION` 2026-09-30 · 콤보 상한 식별자 없음 · thumb 키 · 동의 오류 문구 '필수 동의 2가지에 체크해주세요.' → `SMOKE_OK`.

### E-3. Lambda (15:20:31Z ~ 15:21:25Z)

```bash
export AWS_PROFILE=sunity-motion
aws lambda publish-layer-version --layer-name sunity-motion-pilot-shared \
  --description "quick-260930-w9l supplier form revisions (from :22 + 5 files)" \
  --zip-file fileb://<scratch>/w9l-build/layer-new.zip --compatible-runtimes python3.12 --compatible-architectures arm64
#   → arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared:23 (CodeSha256 tZDzyZl1… = 로컬)
for F in sunity-motion-pilot-reference-upload-url sunity-motion-pilot-playback-url; do
  aws lambda update-function-configuration --function-name $F --layers <:23 ARN>; aws lambda wait function-updated --function-name $F
done
aws lambda update-function-code --function-name sunity-motion-pilot-reference-upload-url --zip-file fileb://<scratch>/w9l-build/fn-rul-new.zip
aws lambda update-function-code --function-name sunity-motion-pilot-playback-url --zip-file fileb://<scratch>/w9l-build/fn-pb-new.zip
```

| 함수 | layer | CodeSha256 (= 로컬 zip) | LastUpdateStatus |
|---|---|---|---|
| reference-upload-url | `:22` → **`:23`** | `an9JJEbD…` → `N4cyKXyz…` | Successful [확인] |
| playback-url | `:21` → **`:23`** | `9Y2ahu2W…` → `nRJilv5H…` | Successful [확인] |

- template.yaml · IAM · 환경변수 · CFN 변경 없음 — sam deploy 불필요 [확인 — 바꾼 것은 layer 참조와 함수 코드뿐]. pipeline 함수는 무접촉(:21) [확인].
- 이 두 함수의 :23 은 CFN 밖 드리프트다 — 다음 `sam deploy` 가 스택 정의로 되돌린다 [추정 — lfw 와 같은 구조].

### E-4. 라이브 판별 (쓰기 0, 15:21~15:22Z)

토큰: Admin SDK 커스텀 토큰(TESTB uid `UmH3…`) → Identity Toolkit signInWithCustomToken → ID 토큰(메일 클레임 없음). 스크립트 = scratchpad `livecheck.py`(휘발).

| # | 요청 | 결과 | 뜻 |
|---|---|---|---|
| A1 | POST /reference/upload-url `{probe:true}` | **200** `supplierCode TESTB` · `displayName '테스트 공급자'` [확인] | TESTB 이름 있음 → belle 재확인 때 '다음' 이 막히지 않는다 |
| A2 | 동의 빠진 본문 | **400** bad_request '필수 동의 2가지에 체크해주세요.' [확인] | 새 코드(옛 코드는 '3가지') |
| A3 | fileSizeBytes = 1GB+1 | **400** too_large '용량이 너무 커요. 1GB 이하 영상으로 다시 올려주세요.' [확인] | 새 한도·새 문구 |
| B1 | POST /playback-url `{referenceMotionId:'ref-kip-up', asset:'thumbnail'}` | **404** not_found [확인] | 새 분기(키 없는 legacy doc) |
| B2 | `{referenceMotionId:'ref-kip-up'}` | **200** 7일 영상 URL(604800) [확인] | 기존 재서명 무회귀 |
| B3 | `{referenceMotionId:'ref-kip-up', asset:'coachAudio'}` | **400** [확인] | 다른 asset 거부 |

부작용: TESTB 소유 reference doc 수 전후 1 → 1 [확인 Admin 읽기]. A2·A3 는 검증 단계에서 끝나 presign·doc 생성 0 [확인 코드 순서 + 문서 수]. Firebase Auth 의 UmH3 로그인 기록(lastSignIn)은 갱신됐다 [추정 — signIn 200]. TESTB 는 active 그대로, belle 시험 doc 그대로.

### E-5. 웹 (15:22:25Z ~ 15:22:50Z)

```bash
cd app && rm -rf dist && CI=1 npx expo export --platform web --output-dir dist   # entry-4075a633…js 2.97 MB
aws s3 sync app/dist s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"      # IA83OV9SRXLSAVLLUPILU2U5Q9
aws cloudfront wait invalidation-completed --distribution-id E16SR4IPFYH46Q --id IA83OV9SRXLSAVLLUPILU2U5Q9
```
- 배포 전 라이브 index.html 번들 = `entry-44cc4571…` · 버킷 객체 60개 → `web-before/` 60개 보존 [확인].
- 무효화 완료 뒤 `/supplier` 200 · index.html 이 `entry-4075a633…` 를 가리킨다 = 새 dist 와 같다 [확인 curl]. 라이브 번들 안 문구: '필수 2개' 1 · '영상 이용 동의' 1 · '5초~2분' 3 · '공급자 계약에 따라' 2 · '초급' 5 / '필수 3개' 0 · '무음 영상 확인' 0 · '이 동작에 대해' 0 [확인 — 번들 텍스트 검색].
- app/dist 는 gitignore [확인].

### E-6. OTA (15:23:56Z)

```bash
cd app && npx eas update --branch preview --platform ios --message "quick-260930-w9l: 레벨 초급 + 기준 동작 썸네일 배선" --non-interactive
```
- Update group **`62eb42e4-afa8-443d-8afa-ff55757bbd59`** · ios · runtime 1.2.4 · gitCommit `faf83234` · 2026-09-30T15:23:56Z [확인 eas update:view]. 출력의 커밋 옆 `*` = 리포 작업 트리가 더러움 — 커밋 안 한 `.planning` 파일뿐, `app/` 은 깨끗 [확인 git status app].
- belle 안내: **앱을 완전히 종료한 뒤 다시 켜기를 2번** 해야 새 번들이 뜬다(1번째 실행이 받고 2번째에 적용).
- 롤백 = 아래 '롤백' 4).

## 롤백

> 배포 **전에** 적었다(2026-10-01 00:2x KST). 보존물 = `/Users/Shared/sunity-motion-rollback/w9l/`(폴더 700).

보존물 [확인 — 로컬 base64 sha256 = AWS CodeSha256]:
```
function-before-sunity-motion-pilot-reference-upload-url.zip  sha an9JJEbDfzBHG7AzNk/tSGpRf5n3bM3suQiP4takjcw=  (layer :22)
function-before-sunity-motion-pilot-playback-url.zip          sha 9Y2ahu2W56DyWXQxCpANNN16H5bUP3/6Jj7ZRwEH5/Q=  (layer :21)
layer-21.zip  sha aZdI7F6x…   layer-22.zip  sha Ydgkf3IH…
lambda-before.json · before-config-<fn>.json(get-function-configuration 원문)
web-before/  = s3://sunity-motion-pilot-supplier-web 전체 sync
```

명령(원문):
```bash
export AWS_PROFILE=sunity-motion
R=/Users/Shared/sunity-motion-rollback/w9l
L=arn:aws:lambda:ap-northeast-2:976369350031:layer:sunity-motion-pilot-shared

# 1) reference-upload-url → layer :22 + 옛 코드
aws lambda update-function-configuration --function-name sunity-motion-pilot-reference-upload-url --layers $L:22
aws lambda wait function-updated --function-name sunity-motion-pilot-reference-upload-url
aws lambda update-function-code --function-name sunity-motion-pilot-reference-upload-url \
  --zip-file fileb://$R/function-before-sunity-motion-pilot-reference-upload-url.zip
aws lambda wait function-updated --function-name sunity-motion-pilot-reference-upload-url

# 2) playback-url → layer :21 + 옛 코드
aws lambda update-function-configuration --function-name sunity-motion-pilot-playback-url --layers $L:21
aws lambda wait function-updated --function-name sunity-motion-pilot-playback-url
aws lambda update-function-code --function-name sunity-motion-pilot-playback-url \
  --zip-file fileb://$R/function-before-sunity-motion-pilot-playback-url.zip
aws lambda wait function-updated --function-name sunity-motion-pilot-playback-url

# 3) 웹 번들 되돌리기
aws s3 sync $R/web-before s3://sunity-motion-pilot-supplier-web --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id E16SR4IPFYH46Q --paths "/*"

# 4) OTA
cd app && npx eas update:republish --group b2b148b4-a789-49fe-bd18-b926fefb8fa9 --message "ROLLBACK: quick-260930-w9l" --non-interactive
```
- 새 layer 버전은 남겨도 된다(참조하는 함수가 없으면 무해). 옛 layer :21·:22 는 게시된 채 있다 → 되붙이기가 롤백 [확인 list-layer-versions].
- **순서 주의**: 서버를 되돌리면 새 웹 번들 본문(silent·isSplit·standingStart·athleteName 없음)을 옛 서버가 400 으로 거부한다 [확인 옛 validation 코드]. 롤백은 3) 웹 → 1) 서버 순으로 한다.
- 새 등록 doc(consent version 2026-09-30, trainingBasis)은 옛 코드도 읽는 데 문제없다 — 옛 Pod(`_register_reference`)가 비공개 doc 에서 읽는 필드는 isCombo · clipRange · consent.training 셋이다 [확인 `git show d7b00c89:backend/functions/pipeline/app.py:10539-10541`]. 옛 Pod 는 isCombo 없음 = False = 30초 상한으로 본다 — 38-14 에서 Pod 코드를 requeue 전에 배포해야 하는 이유.
