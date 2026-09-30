---
phase: quick-260930-w9l
plan: 01
subsystem: supplier-link (공급자 올리기 폼 · 등록 경로 · 썸네일)
tags: [supplier, reference-registration, ffmpeg, playback-url, expo-web, ota]

requires:
  - phase: 38-supplier-link (38-13 Task 3 belle 폰 확인)
    provides: belle 수정 요청 12항목(원문 = 38-13-DEPLOY.md Task 3 절)
provides:
  - 공급자 폼: 필수 4 + '필수' 표시 · 동의 2 + 보기 · 학습 계약 안내 · 5초~2분 · 1GB · 선수 이름 읽기 전용(없으면 차단)
  - 서버: 옛 본문 호환 · 409 supplier_name_missing · athleteName = 공급자 displayName · 동의 기록 trainingBasis
  - Pod 등록 경로(코드+테스트, 배포 38-14): 소리 제거(fail-closed) · 서 있는 시작 썸네일 · 1GB · 120초
  - playback-url asset 'thumbnail' · 앱 썸네일 표시(공급자 행 · 홈 도전 카드)
  - 레벨 라벨 '초급'
affects: [38-14 (Pod 배포·정은지 초대), 공급자 계약서, belle 폰 재확인]

tech-stack:
  added: []
  patterns:
    - "doc 에 서명 URL 대신 S3 키 + playback-url 서버 구성 키 exact 비교 재서명(썸네일에도 적용)"
    - "pipeline Lambda 에 없는 의존성(imageio_ffmpeg)은 함수 안 지연 import — 최상단 import 는 표준 라이브러리만(테스트가 잠금)"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/reference_media.py
    - backend/tests/test_reference_media.py
    - app/src/lib/referenceThumbs.ts
  modified:
    - backend/shared/python/sunity_shared/{models,validation,firestore_admin,s3keys}.py
    - backend/functions/{reference-upload-url,playback-url,pipeline}/app.py
    - backend/scripts/supplier_invite.py
    - app/src/lib/{supplierForm,supplierRules,supplierFixtures,api,referenceMotions}.ts
    - app/src/constants/supplierCopy.ts · docs/supplier-guide.md · docs/contract.md · docs/reference-motions.md · docs/ia.md
    - app/src/components/SupplierUi.tsx · app/src/app/supplier/{upload,index}.tsx · app/src/app/(tabs)/index.tsx · app/src/app/analysis/reference.tsx · app/src/types/analysis.ts

key-decisions:
  - "옛 웹 번들 필드(athleteName·isCombo·isSplit·hasHold·standingStart·consent.silent/training)는 서버가 검증 없이 무시, 새 doc 에 선언 4 를 쓰지 않는다"
  - "이름 없는 공급자는 등록 차단(앱 '다음' 비활성 + 서버 409 supplier_name_missing), 해결 = revoke 후 create --name 실명"
  - "썸네일 = doc 에 thumbnailS3Key, URL 은 POST /playback-url asset 'thumbnail'(1시간), 프레임 = 서 있는 시작 창 가운데"
  - "콤보 상한 삭제, 길이 상한 120초 하나"
  - "학습 근거 = 공급자 계약(consent.training true + trainingBasis 'supplier_contract', CONSENT_VERSION 2026-09-30)"
  - "기준 경로 용량 초과 = too_large + 1GB 문구(수강생 size_exceeded 100MB 문구 아님)"
  - "소리 제거 실패 = 등록 server_error(fail-closed), 썸네일 실패는 경고만"
  - "홈 초급 첫 카드 부제 = '초급'만(belle 10-01, '입문 초급' 방지)"

requirements-completed: [REQ-38-2, REQ-38-3, REQ-38-6, REQ-38-8]

duration: 약 1시간 10분 (첫 커밋 23:37 KST 전후 ~ OTA 00:24 KST, belle 판정 대기 제외 불가 — 연속 기록 없음)
completed: 2026-10-01
---

# quick-260930-w9l: 공급자 폼 수정 묶음 (belle 09-30 폰 확인 뒤) Summary

**공급자 올리기 폼을 필수 4 · 동의 2 · 5초~2분 · 1GB · 선수 이름 고정으로 바꾸고, Pod 등록 경로에 소리 제거·서 있는 시작 썸네일을, playback-url 에 썸네일 재서명을 붙여 Lambda 2개(layer :23) · 웹 · OTA 까지 배포했다(Pod 는 38-14).**

## 커밋

| 커밋 | 내용 |
|---|---|
| `301d4d02` | Task 1 — 백엔드 계약 3벌 + reference-upload-url + supplier_invite.py |
| `b18e279a` | Task 2 — reference_media · _register_reference · s3keys · set_registration_active · playback-url thumbnail |
| `59a5d1e8` | Task 3 — 앱 순수 규칙 · 문구 · 가이드 · 라벨 · 타입 |
| `ea6a7560` | Task 4 — 앱 화면 · 썸네일 배선 |
| `faf83234` | belle Task 5 판정 뒤 수리 2건(홈 초급 부제 · 가이드 s6 낡은 문구) |

배포: layer `sunity-motion-pilot-shared:23` → reference-upload-url · playback-url, 웹 무효화 `IA83OV9SRXLSAVLLUPILU2U5Q9`, OTA preview ios group `62eb42e4-afa8-443d-8afa-ff55757bbd59`. 상세·롤백 = `260930-w9l-DEPLOY.md`.

## 관측 (승계해도 되는 것)

- 게이트: backend 전체 pytest **5755 passed, 20 skipped** [확인] · app typecheck 0 [확인] · node 7파일 **82/82** [확인] · 웹 export 성공 [확인].
- 각 태스크 RED 먼저: Task 1 40 failed + 수집 오류 1, Task 2 18 failed + 38 errors, Task 3 11 failed → 구현 뒤 초록 [확인].
- 실제 ffmpeg 7.1(imageio_ffmpeg): 무음본 = 오디오 없음 · 비디오 프레임 수 동일 · `displaymatrix: rotation of 90` 유지(mp4 · mov), 회전 320x180 → 세로 360 폭 썸네일, 길이 넘는 t = ReferenceMediaError [확인 test_reference_media.py 10건].
- 라이브(쓰기 0): probe 200 TESTB displayName '테스트 공급자' · 동의 누락 400 '필수 동의 2가지…' · 1GB+1 400 too_large 1GB 문구 · 썸네일 ref-kip-up 404 · 영상 재서명 200(7일) · 다른 asset 400. TESTB 소유 reference doc 1 → 1 [확인 DEPLOY §E-4].
- 라이브 웹 번들에 새 문구 있음, 옛 문구('필수 3개'·'무음 영상 확인'·'이 동작에 대해') 없음 [확인 §E-5].
- 시뮬(수강생 앱): 기준 선택 탭 '초급' · 홈 도전 카드 번들 썸네일 그대로 [확인 sim/01·02]. belle ○ [확인 — "나 : 응"].
- supplierRules.mapPresignFailure 는 상태코드만 본다 → 서버 400 too_large · 409 supplier_name_missing 은 화면에서 presignFail 문구 [확인 코드 + fixture 2행].
- pipeline 의 reference 분기는 Pod 위임만 한다 — pipeline Lambda 배포 불필요 [확인 DEPLOY §D(a)].
- 수강생 `_process` 경로에 서버 쪽 길이·용량 상한이 없고, 자기 재현성은 v1 을 uploads/ 로 서버 복사해 그 경로에 넣는다 [확인 DEPLOY §D(b)].
- 앱 어디에도 기준 영상 원본 소리를 켜고 재생하는 곳이 없다 [확인 DEPLOY §D(d)].
- 원본 `upload.{ext}` 는 소리를 가진 채 비공개 버킷에 남는다 — 재생·분석은 v1(무음본)만 쓴다 [확인 코드, T-w9l-08 accept].
- 가이드 s6 의 낡은 '(입력 칸은 다음 업데이트에서 열려요)' 는 belle 판정으로 이번에 지웠다(`faf83234`) [확인].
- 항목 12(수강생 앱 아이클라우드 영상 구분) = 조치 없음 [확인 — belle 결정].

## 플래너 판단 (그대로 구현)

- (9) 폼은 isSplit·hasHold·standingStart·isCombo·athleteName 을 보내지 않고, 서버는 이 다섯 + consent.silent/training 이 와도 **검증 없이 무시**(standingStart false 사전 차단 폐지 — 서 있는 시작은 파이프라인 no_standing_start). 새 비공개 doc 에 선언 4 를 쓰지 않는다. 옛 doc 값은 그대로, 타입·계약엔 '2026-09-30 이전 doc 에만' 선택 필드. REQUIRED_FIELD_COUNT = 4.
- (10) 이름 없는 공급자 = 등록 차단: 앱은 probe 가 끝났는데 displayName 이 비면 '다음' 비활성 + 안내(probe 실패·로딩 중에는 막지 않는다 — 서버가 409 로 다시 막는다), 서버는 폼 검증 통과 뒤·presign 전에 409 `supplier_name_missing`. 운영 해결 = revoke 후 `create --name <실명>`. `--name` 30자 초과 exit 2, 도움말 '실명(…)'.
- (3 URL 방식) doc 에 서명 URL(thumbnailUrl)을 박지 않고 `thumbnailS3Key` + POST /playback-url `{referenceMotionId, asset:'thumbnail'}` 1시간 URL. 서버 가드 = doc 존재 · isActive 가 false 아님 · supplierUid 문자열 · 서버 구성 키와 exact · `reference/` 접두사, 위반은 전부 같은 404. 번들 썸네일 11개가 먼저.
- (3 프레임) t = (n_stand / real_fps) / 2, 영상 길이 − 0.1 로 자르고 하한 0. 번들 11개 표(motionThumbs.ts)는 무접촉.
- (6) 콤보 상한 상수 삭제(식별자 0), REFERENCE_MAX_DURATION_SEC = 120.0 하나, 파이프라인은 비공개 isCombo 를 읽지 않는다.
- (5+11) 요청 consent = {portrait, usage}. 서버 비공개 기록 = {portrait, usage, training: true, trainingBasis: 'supplier_contract', version: '2026-09-30', at, uid}. 파이프라인은 consent.training 을 자기 재현성 learningOptIn 으로 넘긴다 — 새 등록은 **true** 가 된다.
- (7) 기준 경로 용량 초과 = REG_ERR_TOO_LARGE + 1GB 문구.
- (8) 소리 제거 실패 = server_error 로 등록 실패(fail-closed), 썸네일 실패 = 경고만. 순서 = 판정 통과 뒤 · set_reference_angles 앞, 오디오 없으면 재업로드 없음(ETag 그대로), 있으면 같은 v1 키에 upload_file → 새 ETag 를 videoETag 로.

## 진단 · 미확인 (승계 전 재검증)

- [미확인 — 법률 자문] 공급자 계약 조항만으로 AI 학습 근거가 충분한가.
- [미확인 — 38-14 초대 전 확인] 공급자 계약서에 학습 조항이 실제로 들어가고 서명되기 전엔, 새 등록의 learningOptIn true 가 근거 없이 켜진다.
- [미확인 — 38-14 실측] 1GB 4K 2분 영상의 Pod 다운로드·추출 시간, REGISTRATION_LEASE_SEC 900 이 충분한가, extract 캡(121초 × 9fps) 메모리, Pod 디스크(무음본이 원본만큼 한 벌 더).
- [미확인 — 38-14 실측] 1GB 를 폰 브라우저가 presign 900초 안에 올리는가(느린 회선이면 만료 → expired 행).
- [미확인 — 38-14 실측] 자기 재현성이 120초·최대 1GB 기준 영상을 수강생 `_process` 경로(길이 상한 없음, extract end_s 캡 없음)로 돌릴 때의 처리 시간·메모리.
- [미확인 — belle 눈] 새 썸네일 프레임(서 있는 시작 창 가운데)이 괜찮은가 — 08-31 기각 사유('민망한 자세'·'거꾸로')를 피하려 고른 순간이지만 판정은 belle 눈.
- [추정] playback-url 이 :21 → :23 으로 lfw 의 auth·responses 변경을 함께 받았다 — 옛 호출 모양을 유지하는 추가라 영향 없다고 보지만, 이 함수에서의 확인은 라이브 B1~B3 뿐이다(asset 경로 correctedPose·coachAudio·faultZoom 은 이번에 다시 부르지 않았다).
- [추정] 두 함수의 layer :23 은 CFN 밖 드리프트 — 다음 `sam deploy` 가 되돌린다.

## Deviations from Plan

1. **[Rule 2 - 테스트 잠금]** apiFailures fixture 에 400 too_large · 409 supplier_name_missing → presignFail 두 행 추가 — 플랜이 "확인하라" 한 행동을 테스트로 잠갔다. (`59a5d1e8`)
2. **[순서]** Task 2 게이트 grep 이 `app/src` 까지 봐서 Task 2 끝엔 app 잔여(Task 3 몫)가 있었다 — 백엔드는 0, 저장소 전체 0 은 Task 3 에서 [확인].
3. **[belle 판정 수리]** Task 5 판정으로 홈 초급 첫 카드 부제 '입문' 접두어 삭제 + 가이드 s6 낡은 문구 삭제(`faf83234`). 플랜 밖이지만 belle 지시.
4. **[배포 범위]** playback-url 은 원래 layer :21 이었다 — :23 으로 올리며 lfw 변경(auth·responses 추가)도 함께 받았다(DEPLOY §E-1 에서 diff 확인 뒤 진행).
5. Docker 가 꺼져 있어 스모크 전에 Docker Desktop 을 켰다.

## Threat Flags

없음 — 새 표면(playback-url thumbnail · reference_media ffmpeg)은 플랜 threat_model T-w9l-04 · T-w9l-06 대로 구현·테스트됐다.

## Known Stubs

없음. 썸네일 배선은 데이터가 생기면(38-14 Pod 배포 뒤 첫 등록) 그대로 그린다 — 그 전엔 종전 아이콘/회색 자리가 설계된 폴백이다.

## 다음 할 일 (실행 금지 — 목록만)

1. 38-14: Pod 코드(`_register_reference` 소리 제거·썸네일·1GB·120초)를 **requeue 전에** 배포한다 — 옛 Pod 코드는 새 doc 을 isCombo 없음 = 30초 상한으로 본다.
2. 38-14 requeue 전에 belle 시험 doc '클라임 · 기본기(이제 초급) · 대기 중' 1건(TESTB 소유)을 삭제한다.
3. 시험 공급자 TESTB(UmH3…)는 belle 재확인까지 켜 둔다. 끄는 명령 = `38-13-DEPLOY.md` Task 3 '시험 창' 절(`supplier_invite.py deactivate --uid …`).
4. 공급자 계약서 학습 조항 존재·서명 확인(정은지 초대 전), 법률 자문.
5. Figma 282:506 은 이번에 안 건드렸다 — 시안과 코드가 `38-DESIGN-v2.md` 끝 w9l 절만큼 다르다.

## belle 폰 재확인 목록 (바뀐 화면만)

공급자 웹(https://d2ivnoigym2xlu.cloudfront.net/supplier, TESTB 계정):
1. STEP 01 — 촬영 전 체크 · 동작 이름 · 레벨 · 영상 파일 네 곳 옆 '필수' ○× · 아무것도 안 하면 '필수 항목 4개가 남았어요' ○×
2. STEP 01 — 콤보 체크와 '이 동작에 대해' 세 질문이 없다 ○×
3. STEP 01 — 선수 이름이 '테스트 공급자' 로 고정(고칠 수 없음) ○×
4. STEP 01 — 1GB 넘는 파일 → '1GB 이하' 다이얼로그 ○× · 2분 넘는 파일 → '2분 이내' 다이얼로그 ○× · 100MB~1GB 파일은 통과 ○×
5. STEP 02 — '[필수] 초상·성명 사용 동의 · 보기 >' / '[필수] 영상 이용 동의 · 보기 >' 두 줄, '보기' → 가이드 '권리와 동의' ○×
6. STEP 02 — '필수 항목에 동의하지 않으면 등록할 수 없어요.' + 학습 안내 한 줄, 학습 체크박스·긴 철회 문단 없음 ○×
7. 가이드 — s2 '길이와 시작' · s3 '올릴 때 무엇을 적나요' · s5(5줄) · s6(끝 괄호 없음) · s7(음악·콤보 줄 없음) ○×
8. 내 동작 행 — 썸네일은 38-14 전엔 아이콘 그대로 ○×
9. 완료 상세 정보 표 — 스플릿 · 유지 · 서 있는 시작 행 없음 ○× (완료 행이 있을 때만 보인다)

수강생 앱(TestFlight, **앱 완전 종료 후 재실행 2회** 뒤):
10. 기준 동작 선택 첫 탭 '초급' ○×

## Self-Check: PASSED

- 파일: reference_media.py · test_reference_media.py · referenceThumbs.ts · 260930-w9l-DEPLOY.md · sim/01-home.png · sim/02-reference-tabs.png — 전부 FOUND [확인].
- 커밋: 301d4d02 · b18e279a · 59a5d1e8 · ea6a7560 · faf83234 — 전부 FOUND [확인].
- 배포: 두 함수 Layers = :23 · LastUpdateStatus Successful · CodeSha256 = 로컬 zip [확인].
