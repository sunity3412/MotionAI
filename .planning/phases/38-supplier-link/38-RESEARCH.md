# Phase 38: 공급자 링크 — 실증 최소 (supplier-link) - Research

**Researched:** 2026-09-26
**Domain:** S3 이벤트 파이프라인(기준 등록 자동화) · Firestore admin writer · RTMW 기반 실패 판정 · Expo/Firebase 웹 페이지 호스팅·로그인 · 앱 입력 검증
**Confidence:** MEDIUM — 코드·AWS 실측은 HIGH, 페이지 호스팅(web export)은 의존성 게이트에서 멈춰 **못 쟀다**(LOW), 실패 4형 문턱값은 설계 제안(ASSUMED)

> 보고 규칙(CLAUDE.md §7 ★): 문장마다 `[확인]`(이 세션에서 파일을 열었거나 명령을 돌렸다) / `[미확인]` / `[ASSUMED]` / `[CITED: url]`. **관측(§관측)과 진단(§진단)을 다른 절에 둔다.** 관측은 다음 세션이 승계해도 되고, 진단은 재검증 대상이다.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

ROADMAP Requirements 1~8 을 이 문서에서는 `REQ-38-1` ~ `REQ-38-8` 로 부른다. 플랜 frontmatter `requirements` 에 이 라벨을 쓴다.

#### 제품 형태 (belle Q1·Q2 ○)
- **D-01:** 같은 앱의 공급자 모드. 링크 = 그 모드의 첫 화면(임시물 아님). 폰 브라우저에서 연다. 폼 항목·동의문은 끝 그림 기준으로 지금 쓴다. (기획안 §7-1)
- **D-02:** 링크 페이지 = 공급자 마이페이지 축소판 = **내 동작(+올리기 폼) + 내 코드** 두 카드. 앱 안 공급자 모드 화면은 범위 밖. (§7-4)
- **D-03:** 실증 공급자 인증 = uid 화이트리스트(`BELLE_UID` → `SUPPLIER_UIDS` 확장, 정은지 uid 포함). 역할 클레임은 끝 그림. 로그인은 같은 Firebase 프로젝트(익명·Google·Apple 중 웹에서 되는 것 — 연구로 확정). (SEED 열린 질문 2)

#### 뒤쪽 자동화 — REQ-38-1 · REQ-38-2 · REQ-38-3
- **D-04:** `reference/` 용 presigned PUT 입구(`POST /reference/upload-url` 또는 upload-url 에 `kind=reference`). 발급 시 `reference/{id}` doc 선작성(`status: registering`, 폼 메타). 지금 presigned PUT 은 `uploads/*` 만(`template.yaml:194`)이고 `parse_upload_key` 가 `reference/` 키를 거부한다(`s3keys.py:18`). (REQ-38-1)
- **D-05:** 업로드 트리거 → 파이프라인 `register_reference` 경로: 다운로드 → RTMW → angles(flat: `angles·anglesJointKeys·anglesFrames·anglesUpdatedAt`) 를 `reference/{id}` 에 쓰는 admin 함수 신설. `update_reference_body_data`(`firestore_admin.py:2173`)·`update_reference_downstream_data`(2272) 패턴 mirror, **ADD-only merge, 기존 11개 무접촉**. angles 없으면 mode1 `RuntimeError`(`pipeline/app.py:8905`) — 그것을 없애는 것이 이 칸의 목적. S3 알림·SQS 가 `reference/` 접두사도 받아야 한다(버킷 알림은 template 밖 — 실측 필요). (REQ-38-2)
- **D-06:** clipRange 승격은 **선택** — 손 입력 유지 가능. Gemini A(`clip_range` → 상단 `clipRange`)는 기존 `POST /reference/auto-register` 그대로 붙이거나 뒤로 미룬다. clipRange 없을 때 런타임은 DTW 폴백(`pipeline/app.py:9026`). (§7-2 ③)
- **D-07:** 폼 메타 → doc: `name·athleteName·level`(없으면 picker 가 버린다 `referenceMotions.ts:72-78`) + 선언 4개: 동작 이름(기술 사전에서 선택, 새 이름 허용) · 스플릿 동작인가 · 유지 구간이 있는가 · 서 있는 자세에서 시작했는가. 선언은 지금 코드에 박힌 값(`SPLIT_LINE_ELEMENTS` `technique.py:43`, criteria yaml `hold_moment`, 높이 자 바닥 전제)을 **doc 필드로 받아 두는 것**까지가 범위. 사전/규칙 분리 코드는 범위 밖. (REQ-38-3, §7-2)
- **D-08:** 동의(폼 체크, 문안 §6 그대로): 초상·성명 사용(필수) · 영상 이용 허락 — 분석 기준·프레임 추출·표시·썸네일(필수) · 무음 영상 확인(필수) · 학습 사용(선택, **기본 꺼짐**) · 철회 절차 한 줄 + 철회 시 수요자 기록 스냅샷 유지 고지. 동의 결과는 doc 에 남긴다. (REQ-38-3)

#### 등록 실패 4형 · 자기 재현성 — REQ-38-4
- **D-09:** 실패 4형 각각 문구 + 재촬영 안내: 사람 미검출(기존 `no_human` 재사용) · 여러 명(YOLOX 검출 수) · 서 있는 시작 없음(높이 자 바닥 규칙, 09-25 nnt §3) · 저신뢰(못 읽은 부위 목록). doc `status: failed` + `reason` → 페이지 문구. 각 형은 **합성 입력으로 강제 재현**할 수 있어야 한다(Success ②).
- **D-10:** 자기 재현성: 등록 완료 뒤 같은 영상을 `mode1` 로 자기 기준에 대해 1회 분석 → doc 에 `selfScore` 한 줄. 100 근처가 아니면 재촬영 권고 문구. 정은지 fixture 12편이 이미 이 경로다. (§7-3·§B-3-2)
- **D-11:** 새 기술 key 는 **기본 경로**(reference_relative 기하 + Gemini 지목 + "못 잰 부위 한 줄")로만 돈다. 벌림 감점·신전 기준·문구집·접점·썸네일 없음은 받아들인다. 얼마나 맞는지는 **시험 영상으로만** 잰다. 기술 사전 채우기는 플랫폼 운영·실증 뒤. (§7-3·§9-4)

#### 강사 코드 · 돈 — REQ-38-5
- **D-12:** 강사 코드 = 공급자 id 기반 짧은 문자(예 `EUNJI`). 링크 페이지 "내 코드" 카드에 표시·복사. 수요자 입력 자리 = 마이 탭 계정 카드 아래 한 줄 — **이 phase 는 표시만**, 입력·귀속·크레딧 지급은 다음(§C-2 (a), §10 단계 2 이후 belle 승인).
- **D-13:** 실증 = 돈을 받지 않는다. 크레딧은 숫자만(또는 안 보임), 결제 SDK 없음. (§C-6)

#### 업로드 기준 · 문구 · 보관 · 가이드 — REQ-38-6 · REQ-38-7 · REQ-38-8 (belle 09-26 ○)
- **D-14:** 길이 하한·상한 즉시 검사 — 수요자 3~90초(앱 `analyze.tsx` validate 에 duration 추가, IA 3-3 `AC-VID-003-1L` 문구 재사용) · 공급자 5~30초(콤보 60초, 링크 페이지). 형식 mp4/mov · 100MB 는 그대로. (REQ-38-6)
- **D-15:** 문구 정정 — 앱 팁 "측면 45°, 2~3m"(`loading.tsx:519,546`) · 실패 문구 "정면으로"(`loading.tsx:490`) · `docs/ia.md` §3-2 "측면 45° / 2~3m" · `docs/reference-capture-guide.md` §2 "정면 우선" → 전부 **"기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)"**. (REQ-38-6)
- **D-16:** 촬영 기준 = **정은지 기준 영상의 조건**: 세로 · 고정(삼각대/거치) · 허리~가슴 높이 수평 · 폴 전체(천장~바닥)+전신이 동작 내내 안에(약 4~5m) · 한 사람 · 밝은 실내(역광 실루엣 금지) · 무음 · 서 있는 자세에서 시작 · 동작 1개 = 영상 1개. **각도 고정값(정면/45°)은 두지 않는다**(시작 방향은 동작마다 다르다 — 09-26 실물). 고스트 오버레이·자세 인식 자동 시작은 끝 그림 선택 항목(범위 밖).
- **D-17:** 수요자 원본 영상 보관 **영구** — `uploads/` 30일 만료 수명주기(버킷 설정, template 밖 `template.yaml:135`)를 해제. `s3keys.py:3` 주석 정정. 기록 화면 원본 재생이 30일 뒤 사라지지 않는다. 동의분 연습 영상 접두사도 영구. 비용 30MB × 1,000편 ≈ 30GB ≈ $0.7/월. (REQ-38-7)
- **D-18:** 공급자 가이드 — 링크 페이지 안 "촬영 전 체크 5" + 상세 가이드 화면 + 문서 정본 `docs/supplier-guide.md`(쉬운 말, 공급자용). 내용 7: ① 촬영 조건 = 정은지 영상 조건(예시 = 정은지 프레임) ② 동작 1개 = 영상 1개, 5~30초, 서 있는 시작, 무음 ③ 폼 선언 4개를 왜 묻는지 한 줄씩 ④ 등록 뒤 보게 되는 것(재현성 점수, 실패 4형과 대처) ⑤ 권리·동의(공급자 소유, 이용 허락, 철회) ⑥ 내 코드를 수강생에게 알려주는 법 ⑦ 자주 틀리는 것(너무 가까움 2~3m · 손 촬영 · 뒤에 사람 · 역광 · 음악 · 여러 동작 이어 찍기). `docs/reference-capture-guide.md` §6 운영자 절차는 그대로 둔다. design.md 톤(라이트 · #FF4B33 · Pretendard). (REQ-38-8)

#### 무접촉 · 조인 · Pod
- **D-19:** 기존 기준 11개 · 저장 분석 무접촉. 조인은 불변 id(표시 문자열을 조인 키로 쓰지 않는다). 앱 picker 는 무접촉 — `name·athleteName·level·isActive` 만 맞으면 뜬다. 썸네일은 없으면 기본 이미지(하드코딩 11개 `motionThumbs.ts` 그대로).
- **D-20:** Pod 없을 때 등록 대기 상태(`queued`) 표시 + Pod 기동 시 처리. 온디맨드 자동 기동은 범위 밖(실사용 전제일 뿐). Pod 기동은 손 절차 5분(메모리 demo-only).
- **D-21:** 사람 영상은 `manifest.json` 에 넣지 않는다 — 등록 = `intake_clips.py` → clips.jsonl(메모리 human-videos-stay-out-of-manifest). 공급자 영상도 같은 규칙.

### Claude's Discretion
- **페이지 호스팅** — SEED 권장은 Expo Router 공급자 라우트 **web export** → S3(+CloudFront) 정적 배포(같은 코드베이스 = Q1 "같은 앱"의 문자 그대로). 대안 = 단일 HTML. **권장은 재고 나서**: 연구에서 이 앱(expo-video · react-native-svg · firebase auth 웹 · expo-image-picker 웹)의 web export 가 실제로 빌드되는지, 로그인이 폰 브라우저에서 되는지 실측한 뒤 플래너가 정한다. 못 쟀으면 "권장 없음, 이걸 재야 답이 나온다"로 적는다.
- **`reference/` 키 체계** — 지금 `reference/{motionId}.mp4` 유지 vs `reference/{supplierId}/{techniqueKey}/{v}.mp4`(§7-2 분리 대비). 기존 11개는 그대로 두고 새 등록만 새 체계 가능. 조인은 불변 id.
- **Lambda 배치** — 새 함수(`reference-upload-url`) vs 기존 `upload-url`/`reference-auto-register` 확장. doc 필드명. SQS 라우팅(같은 큐 + 키 접두사 분기 vs 별도 큐).
- **테스트 구성** — 실패 4형 합성 입력의 형태(pytest, 순수 함수 단위), 웹 페이지 typecheck 게이트.
- **Gemini "unregistered" 경로** — 새 동작이 등록 목록 10개 밖이면 신전 기준 0. 받아들인다(§7-3). 설계 여지 없음, 문서에만 남긴다.

### Deferred Ideas (OUT OF SCOPE)
- 앱 안 공급자 모드 화면(카드 5: 내 수강생 · 크레딧/정산 · 권리/동의) · 학원 콘솔 · 정산 비율 · 증명 1·3층 — §10 단계 4
- 기술 사전 / 기준 인스턴스 분리 코드(§7-2 D2) — 실증 뒤. 단 폼 "동작 이름"은 사전 선택형으로 미리
- 강사 코드 **입력·귀속·양쪽 크레딧 지급(2/2)** — 표시만 이번, 나머지는 belle 승인 뒤
- Pod 온디맨드 자동 기동("Pod 한 명령") — §10 단계 1, 이 phase 밖(실사용 전제)
- 고스트 오버레이 · 자세 인식 자동 시작 · 폴 검출(09-25 시도 실패) — 끝 그림 선택 항목
- 결제 SDK(RevenueCat) · 크레딧 원장 — 실증 뒤
- 홈 "내 공급자" 칸(NEW 배너 → 정은지 카드) — belle 이 실증 전에 하라고 할 때만
- Gemini thinking 실측 로그(usage_metadata) — 실증 첫 주
- 시험 영상 2차(`sealed_test.py`) — 이 phase 의 일이 아니라 **인터럽트**(정은지 영상 도착 즉시 먼저)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-38-1 | `reference/` 용 presigned PUT + 파이프라인 입구 | §관측 Q1(버킷 알림은 `uploads/` 만), Q2(파이프라인이 `reference/` 키를 버리는 줄 10309-10312), Q11(배포 경로·CORS), §패턴 1·2, 코드 예시 A·B |
| REQ-38-2 | 각도 자동 추출 → `reference/{id}` doc | Q3(추출 스크립트 산출·mode1 이 읽는 필드 전수), Q4(admin writer 형상), §패턴 3, 코드 예시 C |
| REQ-38-3 | 폼 메타 + 선언 4 + 동의 4 | Q4(선작성 writer 는 `create()` 로 ADD-only), Q7(uid 화이트리스트), §보안 V5 |
| REQ-38-4 | 실패 4형 문구 + 자기 재현성 | Q5(4형 각각의 원시 함수·file:line·합성 입력), Q6(fixture 경로·selfScore 훅 자리), 코드 예시 D·E |
| REQ-38-5 | 강사 코드 표시, 크레딧 숫자만 | Q10(기존 개념 0건 [확인], profile.tsx 한 줄 자리) |
| REQ-38-6 | 길이 검사 + 문구 정정 | Q9(validate() 형상 · `duration` ms · 정정 문구 원문 5곳) |
| REQ-38-7 | `uploads/` 영구 보관 | Q1(lifecycle 규칙 1개뿐 → `delete-bucket-lifecycle`, 교체-전체 함정) |
| REQ-38-8 | 공급자 가이드 | §벤치·상류 훑기, Q9(정정 대상 문서 원문), design.md §0·§5 규칙 |
</phase_requirements>

## Summary

**판정 먼저.** 뒤쪽 자동화(REQ-38-1·2·4)는 지금 코드에 붙일 자리가 전부 실재하고 재사용 부품이 있다 — 된다. 페이지 호스팅은 **못 쟀다**(web export 가 `react-native-web` 부재로 1.4초 만에 멈춤) — 권장 없음, 잴 것을 §진단 §H 에 적었다. 가장 값싼 결정타 세 가지: (1) S3 버킷 알림은 `uploads/` 접두사 하나뿐이라 `reference/` 는 오늘 파이프라인에 **아예 도착하지 않는다**[확인]; (2) 도착해도 `lambda_handler` 의 `parse_upload_key` 가 `None` 을 돌려 "스킵" 로그만 남기고 버린다(`pipeline/app.py:10309-10312`)[확인]; (3) mode1 이 기준 doc 에서 **반드시** 요구하는 필드는 `angles` 하나이고(`:8905`), 나머지(`clipRange`·`referenceKeypointReport`·`videoS3Key`·`anglesRealFps`·`bodyNormalizationProfile`)는 전부 fail-open/조용한 기능 축소다[확인]. 따라서 "angles 만 있어도 RuntimeError 없이 돈다"는 참이되, 카드·높이 자·비교 영상까지 살리려면 `referenceKeypointReport` + `anglesRealFps` + `videoS3Key` 를 같이 써야 한다.

실패 4형은 원시 함수가 셋은 있고 하나는 없다: 사람 미검출 = `NoHumanError`(`rtmw_engine.py:234`), 서 있는 시작 없음 = `hold_height.py:171-179` 의 바닥 위반 판정(10% 분위 < −0.10), 저신뢰 = 키포인트 score(`rtmw_133_to_coco17.py:132`)·`build_keypoint_report` 의 `confidence`; **여러 명은 엔진이 N 을 버린다**(`rtmw_engine.py:274-276` "첫 번째 사람 사용") — 프레임별 사람 수를 돌려주는 경로를 새로 내야 한다. 넷 다 합성 입력으로 강제할 수 있다(mock inferencer 패턴 `tests/test_rtmw_engine.py:48-56`, 합성 keypointReport 패턴 `tests/test_hold_height.py:33-58`).

로그인: 같은 Firebase 프로젝트의 웹 SDK 로 익명·Google 은 된다(Apple 웹 미지원 [CITED]). 화이트리스트 전제라 **익명은 부적합**(uid 가 브라우저 저장소에 묶여 바뀐다), **Google 팝업**이 후보이나 S3/CloudFront 도메인에서는 `signInWithRedirect` 가 Safari 16.1+/Chrome M115+ 에서 막히므로 팝업 또는 Firebase Hosting 도메인이 필요하다 [CITED]. 이것도 폰 브라우저 실측 전까지는 [미확인].

**Primary recommendation:** 뒤쪽부터 만든다 — `parse_reference_key` + 버킷 알림 2번째 QueueConfiguration + Lambda/Pod 분기 + `register_reference`(어댑터 재사용, 채점 경로 미호출) + ADD-only writer 3개 + 실패 4형 순수 함수 → 그 다음 페이지. 페이지는 `npx expo install react-native-web` 을 **승인된 task 로** 넣고 export 를 재서 결정한다.

## Project Constraints (from CLAUDE.md)

- 기술 스택 변경 금지: Expo+RN(TS) / Lambda(Python)+SAM / Firestore / S3 / RTMW / EAS. 새 프레임워크 도입 금지. [확인 CLAUDE.md §3]
- Motion AI 인프라는 별도 Lambda+S3 — 기존 sunity.ai EC2 에 얹지 말 것. 페이지 호스팅도 EC2 금지. [확인]
- 시크릿은 AWS Parameter Store(`.env` 하드코딩 금지) — `SUPPLIER_UIDS` 도 SSM 동적 참조로. [확인]
- 디자인: #FF4B33 · Pretendard · 라이트 전용 · 다크 배경 금지(로딩 화면 예외만). 테마 토큰 하드코딩 금지(`app/CLAUDE.md`). 미설계 화면은 design.md §0 결정 트리로 자체 설계. [확인]
- 계약 3벌 동시 수정: `app/src/types/analysis.ts` ↔ `models.py`/`validation.py` ↔ `docs/contract.md`. **`PIPELINE_SEQUENCE`/status enum 에 절대 추가 금지**(`models.py:721,755`) — 기준 등록 상태는 별도 필드·별도 enum 으로. [확인]
- Firestore nested array 금지 → flat + `anglesJointKeys`. Spark 플랜 읽기 5만/일 캡 — 전수 스캔 금지. [확인 memory]
- 품질: 작은 단위 · 의미 있는 테스트만 · 이모지·슬롭 금지 · 막히면 "Do not work yet". 보고 규칙 §7 ★(관측/진단 분리, 소비처까지 추적). [확인]
- 사람 영상은 `manifest.json` 금지(`intake_clips.py` → clips.jsonl). Pod 작업 전 push. Pod 은 시연 때만(지금 전부 down, 공용 계정). [확인 memory]
- `sam deploy` 는 메모리상 금지("라이브 스택 낙후") — 새 라우트는 CFN 없이 못 만든다는 충돌이 있다(§관측 Q11). [확인 memory + 실측]
- 앱 UI 변경은 시뮬 확인 후 OTA(typecheck 는 렌더 크래시 못 잡음). [확인 memory]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 공급자 인증(uid 화이트리스트) | API / Backend (Lambda `verify_request` + `SUPPLIER_UIDS`) | Browser (Firebase 웹 SDK 로그인) | 토큰 검증·화이트리스트 판정은 서버만; 브라우저는 ID 토큰을 얻어 보낼 뿐 |
| `reference/` presigned PUT 발급 + doc 선작성 | API / Backend (신규 Lambda) | Database (Firestore `reference/{id}` via Admin SDK) | `firestore.rules` 가 `reference/**` 쓰기를 `false` 로 막는다 — 브라우저는 못 쓴다 |
| 영상 업로드 | Browser (XHR PUT → S3) | CDN/Static (S3 CORS PUT `*`) | 영상은 Lambda 를 거치지 않는다(계약 §1) |
| 트리거 → 등록 파이프라인 | Backend (S3 알림 → SQS → pipeline Lambda → Pod `/register-reference`) | GPU Pod (RTMW) | 각도 추출은 CUDA 필요 — Lambda 는 위임만 |
| 실패 4형 판정 | GPU Pod (pipeline 순수 함수, pose_frames 위) | — | 프레임·키포인트가 있는 곳에서만 판정 가능; 순수 함수라 pytest 가능 |
| 자기 재현성(mode1 1회) | Backend (등록 완료 후 doc 선작성 + S3 copy → 기존 분석 경로) | GPU Pod | 기존 `_process` 를 그대로 태우고 결과를 기준 doc 에 한 줄 복사 |
| 페이지(내 동작 + 내 코드) | Browser (정적 SPA) | CDN/Static (S3+CloudFront 또는 Firebase Hosting — **미결**) | 서버 렌더 불필요; 상태는 Firestore `onSnapshot`(인증 읽기 허용) |
| 강사 코드 표시(앱 마이 탭 한 줄) | Browser/Client (RN) | — | 표시만, 데이터 없음(이번 phase) |
| 길이 검사(수요자 3~90s) | Browser/Client (RN `validate`) | — | 픽 시점 즉시 검사; `duration` ms 는 iOS/Android 만 제공 |
| `uploads/` 영구 보관 | CDN/Static (S3 lifecycle 삭제, template 밖) | — | 버킷 설정 1회 명령 |

## 관측 — 이 세션에서 잰 것 (전부 [확인], 예외는 표시)

### Q1. S3 버킷 상태 (template 밖 설정) — REQ-38-1 · REQ-38-7

- 자격증명: 기본 프로파일 = `arn:aws:iam::976369350031:user/sunity-api`; 프로파일 `sunity-motion` = `user/sunity-motion` [확인 `aws sts get-caller-identity`]. `sunity-api` 는 `cloudformation:DescribeStacks`·`cloudfront:ListDistributions`·`lambda:GetFunctionConfiguration`·`ssm:DescribeParameters` 전부 AccessDenied; `sunity-motion` 은 넷 다 통과 [확인]. **Motion AI 읽기 명령은 `AWS_PROFILE=sunity-motion`** 으로(메모리 aws-keys 와 일치). 쓰기 권한 범위는 [미확인].
- 버킷 알림 (`get-bucket-notification-configuration`): QueueConfiguration **1개** — Id `M2Y1OTFkZDctN2RiYi00MTFhLTliMDctZWI0OTM1M2JjM2Nl`, QueueArn `arn:aws:sqs:ap-northeast-2:976369350031:sunity-motion-pilot-analysis`, Events `s3:ObjectCreated:*`, Filter prefix **`uploads/`**. → `reference/` 접두사는 **알림 대상이 아니다** [확인].
- 수명주기 (`get-bucket-lifecycle-configuration`): 규칙 **1개** — ID `expire-raw-uploads-30d`, Filter prefix `uploads/`, `Expiration.Days: 30`, Status Enabled; `TransitionDefaultMinimumObjectSize: all_storage_classes_128K` [확인]. `results/`·`reference/`·`fixtures/` 에는 규칙 없음.
- CORS (`get-bucket-cors`): AllowedMethods `[PUT]`, AllowedOrigins `[*]`, AllowedHeaders `[*]`, MaxAgeSeconds 3000 [확인]. 브라우저 XHR PUT 은 통과; `fetch` GET 은 CORS 에 없다(`<video src>` 재생은 CORS 불요).
- 버킷: 리전 ap-northeast-2, 정적 웹사이트 설정 없음(`NoSuchWebsiteConfiguration`), Transfer Acceleration `Enabled` [확인].
- 접두사 목록: `_archive/ _artifacts/ _eval-tmp/ backups/ fixtures/ proto/ reference/ results/ sweep_temp/ training/ uploads/`; `reference/` 는 평면 mp4 11개(`ref-climb.mp4` 40.9MB … `ref-kip-up.mp4` 2.3MB) + `reference/_archive/`(재귀 12 객체) [확인 `aws s3 ls`].
- CloudFormation(`sunity-motion` 프로파일): 스택 `sunity-motion-pilot` `UPDATE_COMPLETE`, Created 2026-05-27, **LastUpdated 2026-07-21T16:17Z**. Outputs: `ApiBaseUrl=https://2rbpecm4d8.execute-api.ap-northeast-2.amazonaws.com/pilot`, `AnalysisQueueUrl=https://sqs.ap-northeast-2.amazonaws.com/976369350031/sunity-motion-pilot-analysis`, `VideoBucket=sunity-motion-pilot-videos` [확인].
- CloudFront `list-distributions` → `null`(배포 0개 또는 비가시) [확인, `sunity-motion`].
- SSM 파라미터 이름(값은 안 봄): `/sunity/motion/{belle-uid, runpod-analyze-url, runpod-auth-token, pod-expected, runpod-pod-expected, gemini-api-key, gemini-a-model, firebase-sa, cerebras-api-key, runpod-api-key, runpod-s3-access-key, runpod-s3-secret-key, pair-id-hmac-keys, openai-api-key, hf-token, dashscope-api-key}` [확인]. `supplier-uids` 는 **없다**.
- 원본 명령 정본: `backend/README.md:72-111` "외부 버킷 노티 설정" — lifecycle/CORS/notification 3개 `put-*` 명령이 그대로 있다 [확인].

**교체-전체 함정 (REQ-38-7·REQ-38-1)** — `put-bucket-lifecycle-configuration` 은 "Creates a new lifecycle configuration for the bucket or replaces an existing lifecycle configuration … this will overwrite an existing lifecycle configuration" [CITED: docs.aws.amazon.com/cli/latest/reference/s3api/put-bucket-lifecycle-configuration.html]. 지금 규칙이 1개뿐이므로 해제 = `aws s3api delete-bucket-lifecycle --bucket sunity-motion-pilot-videos --profile sunity-motion` 한 줄로 끝난다(다른 규칙을 다시 넣을 것이 없다). 알림도 같은 교체-전체 의미라 `put-bucket-notification-configuration` 에 **`uploads/` 와 `reference/` 두 QueueConfiguration 을 함께** 넣어야 한다(하나만 넣으면 기존 `uploads/` 알림이 사라진다). 같은 이벤트 타입에 겹치지 않는 접두사 둘은 허용된다 [CITED: docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-filtering.html "multiple non-overlapping prefixes … allowed"].

### Q2. `reference/` 키가 오늘 파이프라인에서 죽는 자리 — REQ-38-1 · 2

- 입구: `backend/functions/pipeline/app.py:10297 lambda_handler` → `iter_s3_keys_from_sqs(event)`(`sunity_shared/events.py:13`, 순수 파서) → **`parse_upload_key(key)` :10309 → `None` 이면 `log.warning("스킵: 인식 불가 S3 키 %s")` + `continue` :10310-10312**. 정규식 `_UPLOAD_KEY_RE = ^uploads/(uid)/(analysis_id [A-Za-z0-9]+)\.(mp4|mov)$`(`s3keys.py:18-20`). 여기가 `reference/` 키가 죽는 자리다(알림이 오면).
- 위임: `_runpod_enabled()`(:194, `RUNPOD_ANALYZE_URL`+`RUNPOD_AUTH_TOKEN` env 비공백) → `update_analysis_status(uid, id, queued)` :10318 → `_delegate_to_runpod(bucket, key)` :210-239: `POST {RUNPOD_ANALYZE_URL}` JSON `{"bucket","key"}` 헤더 `X-RunPod-Token`·UA, timeout `_RUNPOD_TIMEOUT_S=10`(:190), 200/202 외 → `RuntimeError` → `fail_analysis(server_error)` :10342-10347.
- Pod: `backend/runpod_inference/server.py:439-456 POST /analyze` — `AnalyzeRequest{bucket:str, key:str}`(:142-144), `parse_upload_key` 실패 시 **400 `invalid key format`** :444-448, 성공 시 `BackgroundTasks` 로 `_process_in_background(bucket, key, uid, analysis_id)`(:184-215; NoHuman/NotPole/그 외 매핑) → `pipeline_app._process`. **`register_reference` 가 같은 payload `{bucket,key}` 를 재사용할 수 있다** — 키 접두사로 분기하면 된다(Lambda 와 Pod 양쪽에 `parse_reference_key` 분기 필요).
- `_resolve_is_reference(key, meta)` :417-437 — `key.startswith("reference/")` 또는 doc `mode == "mode1_register"`(`_MODE_REFERENCE_REGISTER` :411, `_REFERENCE_KEY_PREFIX` :414) → `_process` 안 :8670 `is_reference_local` → scene prefetch·G4 가드 플래그에만 쓰인다. 기준 각도를 쓰는 소비처 없음. `mode1_register` 는 상수만 있고 `models.MODE_*` 에 없다(`models.py:10-12` `MODES=(mode1, mode3)`).
- `_process`(:8595) 는 첫 줄에서 `users/{uid}/analyses/{id}` doc 을 요구한다(:8604-8607 `RuntimeError("분석 문서 없음")`) → **등록 경로는 `_process` 를 호출하면 안 된다**; 대신 어댑터만 재사용한다.
- 재사용 부품(채점 경로 밖): `_ensure_adapters()` :1514(락 포함) → `_FRAME_EXTRACTOR`(`FfmpegFrameExtractor(target_fps=9.0, max_side=640)` `frame_extractor.py:60`, `extract()` :111) · `_POSE_ESTIMATOR`(`_RTMWNlfCompat` :1453-1512; `.estimate(frames)`→(T,17,4), `._engine`=`RTMWPoseEngine`, `._default_pole` 수직 폴백) · `_RTMW_ENGINE`. 다운로드 helper `_download_analysis_video(bucket, key, *, timings_ms, analysis_id)` :1666-1691(임시파일 경로 반환, 예외 시 unlink). 각도 산출 원형 `_angles_from_video` :1575-1590 = `extract → estimate → compute_joint_angles → temporal_fill(angles, joint_uncertainty)`.
- 최소 분기점 제안(설계, §진단 §A): Lambda `lambda_handler` 에서 `parse_upload_key` **앞에** `parse_reference_key` 를 시도 → 맞으면 기준 doc 상태 갱신 + Pod 위임(같은 `_delegate_to_runpod` 를 URL 만 바꿔 `/register-reference` 로, 또는 `/analyze` 가 키로 분기).

### Q3. `extract_reference_angles.py` 산출과 seed merge, mode1 이 읽는 기준 doc 필드 전수 — REQ-38-2

- `backend/scripts/extract_reference_angles.py`(235줄): S3 `reference/{motionId}.mp4` 다운로드(:92-95) → `FfmpegFrameExtractor()`(기본 9fps/640px) → `RTMWPoseEngine()` + 수직 `PoleAxis` + `measure_body_profile` + `to_coco17_array`(:98-115) → `compute_joint_angles` → `joint_uncertainty` → `occluded_mask` → `temporal_fill`(:125-130). 동작당 `{numFrames: T, occludedFrames: {joint: n}, angles: (T,8) 소수 2자리·NaN→0.0 (:140-146), referenceSplitAngle: peak max-split | None (:153-154)}`; 파일 상단 `{generatedAt, jointKeys: skeleton.JOINT_KEYS(8), numJoints, motions}`(:216-220). 관절 키 8 = `left/right_{elbow,shoulder,hip,knee}`(`skeleton.py:50-51`, 라벨 `JOINT_LABEL_KO`).
- seed merge `app/scripts/seed-reference-motions.mjs:493-500`: `doc.angles = a.angles.flat(); doc.anglesUpdatedAt = Date.now(); doc.anglesFrames = a.numFrames; doc.anglesJointKeys = anglesPayload.jointKeys;` (+ `referenceSplitAngle` :503) → `batch.set(ref, doc, {merge:true})` :521. 같은 doc 에 손 입력 `name·athleteName·level·clipRange·checkpoints·isActive·baseUntilS`(:476-491).
- **그러나** 지금 11개 doc 의 각도 정본은 이 스크립트가 아니라 Pod 재처리 `reprocess_reference_motions_phase4.py` 다(`docs/reference-motions.md` §3 주석 "reprocess" [확인]): `reference/{id}/versions/{v}` 에 11키(`angles, anglesJointKeys, anglesFrames, keypointReport, joints3d, joints3dKeys, joints3dFrames, coordDim, space, pipelineVersion, reprocessedAt` :139-143) 저장 + 전역 포인터 `reference/_release.activeCandidate`(`firestore_admin.py:2483-2484`). `get_reference_motion`(:2558)은 포인터가 있으면 `versions/{v}` 의 `_REFERENCE_CONSUMER_FIELDS`(:2491-2496 = 위 11키 중 9개)를 top-level 위에 덮고, **버전 doc 이 없으면 top-level 로 폴백**한다(:2600 주석) → 새 등록 doc 은 versions 하위가 없으므로 top-level `angles` 가 그대로 소비된다.
- mode1 이 기준 doc 에서 읽는 필드(`grep 'ref\.get\|ref\['` 전수, pipeline/app.py): **`angles`(:8905 없으면 `RuntimeError("기준 모션 또는 keyframe 데이터 없음")`, :9012, :9089)** · `anglesJointKeys`(:9001, 없으면 `skeleton.NUM_JOINTS`) · `clipRange`(:9010/:9014, `_reference_exec_window` :2795-2815 → 없으면 None → DTW 폴백 :9026) · `baseUntilS`·`sharedBaseMotionId`(:9008-9014, :9187-9189 콤보만) · `referenceSplitAngle`(:8956) · `bodyNormalizationProfile`(:8922)·`bodyComparisonSourcePose`(:8928) · `referenceKeypointReport`(:9204 → 확대 카드·`hold_height`) · `videoS3Key`(:9207 `if ref.get(...)` → 비교 영상 서명 URL) · `anglesRealFps` / `keypointReport.fps`(`_reference_angles_fps` :7744-7770, 0.0 이면 "ref-경계 제외 미적용 fail-open" :9034) · `level`(:9686). mode3 기준축도 같은 필드(:761-780). **`checkpoints`·`keyframes` 를 읽는 줄은 0건**(grep) — 런타임 입력이 아니다.
- 앱 picker 필수: `name`·`athleteName`·`level ∈ {basic,intermediate,advanced}` 아니면 `normalize()` 가 null(`referenceMotions.ts:72-78`), `isActive === false` 면 제외(:78). 썸네일은 `motionThumbs.ts` 하드코딩 11개, 없으면 회색 자리(주석 :19).
- 계약 정본: `docs/reference-motions.md` §3 스키마(seed/reprocess/backfill 출처 표기), `docs/contract.md:296 videoS3Key 'reference/{motionId}.mp4'`, `analysis.ts:1302 ReferenceMotion`.

### Q4. Admin writer 패턴 — REQ-38-2 · 3

- `update_reference_body_data(motion_id, body_profile, source_pose=None)` `firestore_admin.py:2173-2252`: 빈 id 거부 → 필수 키 검사 → `_validate_flat_dict_no_nested_array` → payload `{field, fieldUpdatedAt: now_ms}` → `_doc(models.reference_motion_path(id)).set(payload, merge=True)`. idempotent, partial 허용.
- `update_reference_downstream_data(motion_id, *, mean_angles, technique_profile, body_normalization_profile, force_direction_pattern, capture_views=1)` :2272-2360: 같은 패턴 + scoped validator, "ADD-only — joints3d/angles/activeVersion 은 절대 payload 에 포함하지 않는다(Pitfall 4 / D-02)". **즉 지금 writer 둘은 의도적으로 `angles` 를 안 쓴다** — angles writer 는 신설이 맞다.
- `set_reference_motion_with_gemini(motion_id, gemini_a, *, idempotent=True)` :2368-2443: `doc.get()` 로 존재 확인 → 새 doc 이면 `isActive/inactiveReason` 결정, 기존 doc 이면 `isActive` 보존 → `motionId·geminiA·geminiAUpdatedAt` merge.
- `fail_analysis` :2446-2455 형상 `{status:'failed', error:{code,message}, updatedAt}` — 실패 4형 doc 형상의 선례.
- Firestore 규칙: `reference/{document=**}` `allow read: if request.auth != null; allow write: if false;`(`firestore.rules:14-17`) → 모든 쓰기는 Admin SDK(Lambda/Pod) 로만.

### Q5. 실패 4형 원시 함수 — REQ-38-4

(a) **사람 미검출** — `rtmw_engine.py:230-238`: `T == 0 → return []`(예외 아님!), 프레임별 `_infer_raw`(:254-285) 가 `kps_batch is None or len==0` 이면 `None`(:267-269) → `_build_pose_frames` 가 `detected_count` 를 세고 **0 이면 `NoHumanError`**(:234). `_process` 는 `NoHumanError` → `fail_analysis(no_human)`(`app.py:10324`, `server.py:192`). 합성 강제: `RTMWPoseEngine.create_with_inferencer(mock, manifest_path)`(:170-193) + `mock.return_value = (np.zeros((0,133,2)), np.zeros((0,133)))` + `frames=np.zeros((3,480,640,3),uint8)` → `NoHumanError`. 픽스처 원형 `tests/test_rtmw_engine.py:48-56`.
(b) **여러 명** — `_infer_raw` :274-276 `kps = kps_batch[0]  # 첫 번째 사람(인덱스 0) 사용 (폴스포츠 = 1인 영상)`. **N 은 버려진다**; 프레임별 사람 수를 돌려주는 API 가 없다. 인스턴스 사이드카 상태는 금지(`_RTMWNlfCompat.estimate_with_profile` 주석 "HIGH-1 v4 … local-return tuple … 사이드카 mutable state 0" :1487-1495; Pod 는 `BackgroundTasks` 로 동시 분석). 합성 강제: mock 이 `(np.zeros((2,133,2)), np.full((2,133),0.9))` 를 돌려주면 매 프레임 N=2.
(c) **서 있는 시작 없음** — `sunity_shared/analysis/hold_height.py`: `_frame_series(report, window)` :96-135 — 바닥 = 창 이전 프레임(`[:w0]`) 발목 y 중앙값, 몸길이 = (발목−어깨) 중앙값, `w0 ≥ MIN_STAND_FRAMES(3)`, `w1−w0 ≥ MIN_WINDOW_FRAMES(5)`, 몸길이 ≤ 0 이면 None, conf < `MIN_CONF 0.35` 는 NaN(:83-87). `hold_window_heights` :151-183 의 바닥 위반 판정 :171-179: 창 안 `lowFoot` 의 **10% 분위 < −`FLOOR_VIOLATION_BODY_LENGTH`(= 2×0.05 = 0.10, :47-55)** 이면 None(= "창 이전 = 서 있음" 거짓). 입력 = keypointReport dict `{joints, frames, data(T·J·2 flat), confidence(T·J flat)}` = `assemble.build_keypoint_report(pose_frames, fps=)`(`assemble.py:901-990`, 12관절 `_KEYPOINT_NAMES`). 합성 강제 원형 `tests/test_hold_height.py:33-58`(`_report/_pose` 헬퍼).
(d) **저신뢰** — 키포인트 신뢰도 = RTMW score 그대로(`adapters/rtmw_133_to_coco17.py:81-95 confidence=score, uncertainty_proxy=1−score`; 2D `np.clip(scores_133[idx],0,1)` :132/:148); 프레임 reliability = 133점 평균 → `compute_frame_reliability`(:258-261; 문턱 high ≥0.7 / medium ≥0.4 / low, `pose_frame.py:63-66`). 각도 도메인 불확실도 = 관절각을 만드는 3점의 최대값(`features.joint_uncertainty` :280-301). 표시 게이트 `_KP_CONF_MIN = 0.5`(fault_zoom; `app.py:6229,6251`), 메모리 conf-05-gate: 0.5 위아래 품질 차 없음·의미는 0.6 위부터. RTMW body 17 = COCO-17 인덱스 0~16 1:1(`rtmw_133_to_coco17.py:33-37`) → 합성 강제: mock scores 의 인덱스 15·16(발목) = 0.2.

### Q6. 자기 재현성 — REQ-38-4

- fixture 경로: `backend/scripts/e2e_app_path.py`(앱 순서 정본: 익명 signin → `POST /upload-url` → **Firestore doc 먼저** `{analysisId, mode, referenceMotionId, status:'uploading', …}` → S3 PUT → 완료 폴링; uid 지정 시 admin custom token). `intake_clips.py analyze` 가 이것을 부른다(:15-16). `verify_self_comparison.py` 는 구식 self-DTW 순수 검증(`--quick` 로컬). 전부 Pod 필요(quick 제외).
- 점수 자리: `users/{uid}/analyses/{id}.result.overallScore`(`analysis.ts:1082` = `deductionBreakdown.final`), 쓰는 곳 `firestore_admin.complete_analysis(uid, analysis_id, result, *, angles…)`(:1237) 호출부 `pipeline/app.py:10110-10139`; 바로 뒤 :10140 `log.info("분석 완료 …")` 에서 `meta`(:8604)·`result` 가 스코프에 있다 → **selfScore 훅 자리**.
- 트리거 재료: 등록 완료 후 (i) `users/{supplierUid}/analyses/{newId}` doc 선작성(Admin SDK; `firestore_admin` 에 create helper 없음 → 신설) (ii) `s3.copy_object(reference/… → uploads/{supplierUid}/{newId}.mp4)` → 기존 알림(`uploads/`) → SQS → Lambda → Pod `/analyze` → `_process`(mode1, 자기 기준). 순서 = doc 먼저(메모리 demo-only: "문서를 PUT 뒤에 쓰면 조용히 mode3"). 메모리 copied-doc 함정은 **다른 uid 로 doc 을 복사**할 때의 일 — 여기서는 새 doc·같은 uid 라 해당 없음; 단 "`uploads/` 에 객체가 생기면 파이프라인이 깨어난다"는 그 함정의 관측이 여기선 **의도된 트리거**다.
- Pod 가 없으면 `_delegate_to_runpod` 예외 → 자기 분석 doc 이 `failed(server_error)` 로 떨어진다(:10342) → 기준 doc 의 `selfScore` 는 영영 안 채워진다 — 상태 필드(`selfCheckStatus`)가 필요하다.

### Q7. 공급자 인증 · 웹 로그인

- 화이트리스트: `reference-auto-register/app.py:50 _BELLE_UID = os.environ.get("BELLE_UID","")`, :89-99 `if not _BELLE_UID or uid != _BELLE_UID: 403 forbidden`(env 미설정도 거부). env 출처 `template.yaml` `BELLE_UID: "{{resolve:ssm:/sunity/motion/belle-uid}}"`. uid = `sunity_shared/auth.py:91-104 verify_request(event)`: `Authorization: Bearer <idToken>` → `firebase_admin.auth.verify_id_token` → `decoded["uid"]`. 테스트 선례 `tests/test_reference_auto_register_handler.py:31-46`(env monkeypatch + `import app`).
- `SUPPLIER_UIDS` 배선: SSM `/sunity/motion/supplier-uids`(쉼표 구분) **먼저 생성**(동적 참조는 deploy 시점에 해석) → template env `SUPPLIER_UIDS: "{{resolve:ssm:/sunity/motion/supplier-uids}}"` → 순수 파서 `{u.strip() for u in v.split(",") if u.strip()}`.
- 앱 Firebase: `app/src/lib/firebase.ts:52-63` `initializeAuth(app, {persistence: getReactNativePersistence(ReactNativeAsyncStorage)})` 를 `try` 로 감싸고 실패 시 `getAuth(app)`. `Platform` 분기 **없음**. `getReactNativePersistence` 는 `@firebase/auth/dist/rn/index.js`(react-native 조건)에만 있고 웹 빌드 `dist/esm/index.js` 에는 0건 [확인 grep]; `firebase/package.json exports["./auth"]` = node/browser/default 만(브라우저 = `esm/index.esm.js`) [확인]. `@react-native-async-storage/async-storage` 는 `AsyncStorage.js`(기본) + `AsyncStorage.native.js` [확인 ls]. 웹 config 는 `EXPO_PUBLIC_FIREBASE_*` 7키(`app/.env` 키만 확인, 값 안 봄) — **앱과 같은 프로젝트**.
- `socialAuth.ts`: 모듈 최상단 `GoogleSignin.configure(...)`(:41-44), `expo-apple-authentication`·`@react-native-google-signin/google-signin` import. `auth/login.tsx:17` 이 정적 import. `authUser.ts` 는 의도적으로 `firebase/auth` 만 쓴다(:3-8 주석).
- 웹에서의 두 네이티브 라이브러리: `@react-native-google-signin/google-signin@16.1.4` 는 `lib/module/signIn/GoogleSignin.web.js` 로 해석되며 `configure` 는 `console.warn` 만, `signIn/signInSilently` 는 `PLAY_SERVICES_NOT_AVAILABLE` 로 **throw**("Web support is only available to sponsors") [확인 파일]. `expo-apple-authentication` 은 `requireOptionalNativeModule('ExpoAppleAuthentication') || {…}` 폴백(`build/ExpoAppleAuthentication.js:1-5`) 이라 import 는 안전, 공식 문서 "does not yet support Android or web" [CITED: docs.expo.dev/versions/v54.0.0/sdk/apple-authentication/].
- Firebase 공식 문서: 웹 기본 persistence 는 `local` [CITED: firebase.google.com/docs/auth/web/auth-state-persistence]; 익명 로그인은 콘솔에서 Anonymous 활성 필요(앱이 이미 익명을 쓰므로 활성 [확인 index.tsx 선례]) + `linkWithCredential` 로 승격 가능 [CITED: …/anonymous-auth]; `signInWithRedirect` 는 "required on Firefox 109+ and Safari 16.1+ … Chrome M115+" 에서 5가지 옵션 중 하나 없이는 동작하지 않으며, 팝업은 "less smooth for mobile users" [CITED: firebase.google.com/docs/auth/web/redirect-best-practices]; OAuth 는 앱 도메인을 **Authorized domains** 에 추가해야 한다 [CITED: …/google-signin].

### Q8. 페이지 호스팅 — 실측 결과

- `app/package.json`: `react-native-web` **없음**, `react-dom 19.1.0` 있음; `app/node_modules/@expo/metro-runtime` 존재(전이), `react-native-web` 디렉터리 없음 [확인]. `app.json` `"web": {"favicon"}` 만(`output`·`bundler` 미지정 → 기본 SPA `single` [CITED: docs.expo.dev/guides/publishing-websites/ "single (default)"]). `metro.config.js`·`babel.config.js` 없음.
- **실측:** `CI=1 npx expo export --platform web --output-dir <scratchpad>/web-export` → exit 1, 1.36초: `CommandError: It looks like you're trying to use web support but don't have the required dependencies installed. Install react-native-web@^0.21.0 by running: npx expo install react-native-web` [확인, 로그 `scratchpad/web-export.log`]. `npm install` 금지 조건이라 여기서 멈췄다 → 번들 성공 여부·크기·첫 런타임 차단 요인은 **[미확인]**.
- 번들에 들어갈 라우트: `src/app/{(tabs)/{index,analyze,history,profile}, analysis/{loading,reference,result}, auth/{login,signup}, help, index, inquiry, legal/[doc], tutorial}` [확인 find]. `expo-gl`/three 를 쓰는 `PoseViewer3D*.tsx`·`PoseCompareViewer.tsx` 는 `src/app` 에서 import 하는 파일이 0건 [확인 grep] → 번들 밖. `expo-video` importer 13, `react-native-svg` 10 [확인]. 공식 호환표: expo-image-picker 웹 지원(`file` 필드는 웹 전용, **`duration` 은 Android/iOS 만**) [CITED: …/sdk/imagepicker/]; expo-video 웹 지원 [CITED: …/sdk/video/].
- 플랫폼 분기 규칙: `src/app` 안의 `.web.tsx` 는 **비플랫폼 판이 함께 있을 때만** 허용, `src/app` 밖(lib/components)은 자유 [CITED: docs.expo.dev/router/reference/platform-specific-modules/]. → `firebase.web.ts`·`socialAuth.web.ts` 분기는 `src/lib` 이라 가능.
- npm 레지스트리: `react-native-web` 0.21.3(2026-09-25 갱신, repo necolas/react-native-web, postinstall 없음) [확인 `npm view`]. slopcheck(npm 생태계 지정) OK [확인]. **사고:** `slopcheck install` 은 검사 뒤 **실제로 `npm install` 을 실행**한다 — npm prefix 가 리포가 아니라 홈 디렉터리(`/Users/kimtaesung`, 자체 git 저장소)로 잡혀 `~/package.json`·`~/package-lock.json`·`~/node_modules`(24 패키지)에 설치됐고, `npm uninstall react-native-web` 으로 전부 되돌렸다(리포 `git status` clean, 홈 lock/package.json 에 `react-native-web` 0건, 15:22 생성 디렉터리 0개) [확인]. 플래너 지시: **`slopcheck install` 을 쓰지 말 것**(`npm view` + 수동 확인으로 대체).
- CloudFront 가격 페이지: "Free plan $0/month — 1M requests, 100GB data transfer" [CITED: aws.amazon.com/cloudfront/pricing/]. S3 정적 웹사이트 문서는 Amplify Hosting 또는 CloudFront(HTTPS·OAC)를 권장 [CITED: docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html]. S3 website endpoint 가 HTTP 전용이라는 문장은 이번에 원문 확인 못 함 [ASSUMED].

### Q9. 앱 길이 검사 · 정정 문구 원문 — REQ-38-6

- `app/src/app/(tabs)/analyze.tsx:206-213 validate(asset): PickFailureKind | null` — 확장자 ∉ `['mp4','mov']` → `'format'`, `fileSize > 100MB` → `'tooLarge'`(상수 :46-47). 문구 소유는 `pickerFailure.ts` 단일점(주석 :204-205). `checkLowQuality` :218-236 이 이미 `asset.duration`(ms, `>0` 일 때만) 을 쓴다. 타입 `ImagePickerAsset.duration?: number | null`(`expo-image-picker@17.0.11 build/ImagePicker.types.d.ts:299`); `videoMaxDuration` 옵션 "Maximum duration, in seconds, for video recording"(:486) — `launchCameraAsync` 호출부 :470-472.
- 정정 대상 원문(verbatim):
  - `loading.tsx:490` — `'촬영 구도나 거리가 기준 영상과 많이 다르면 이렇게 나올 수 있어요. 몸 전체가 화면에 들어오는 거리에서 정면으로 다시 찍어보면 좋아요.'`
  - `loading.tsx:519` — `<Text style={styles.tipItem}>· 측면 45°, 2~3m 거리</Text>` (이어서 :520 `· 밝은 환경, 폴 전체로 보이게`, :521 `· 3초 이상, 동작 전체 포함`)
  - `loading.tsx:546` — `· 몸 전체가 화면에 들어오는 거리(약 2~3m)에서 정면으로 촬영했는지` (JSX 3줄 :545-547)
  - `docs/ia.md:189` — `| AC-VID-002-1 | Pole sports angle guide | 전신 / 폴 전체 / 측면 45° | 완벽해요! 분석을 시작합니다. | AI 분석으로 이동 |`
  - `docs/ia.md:191` — `| AC-VID-002-2 | Lighting / distance guide | 밝은 환경 / 2~3m 거리 | 환경이 좋아요. 분석 정확도가 높아집니다. | 촬영 계속 |`
  - `docs/ia.md:200`(재사용 문구) — `| AC-VID-003-1L | Duration check | Fail | 3초 미만 | 영상이 너무 짧아요. 동작 전체가 담긴 영상이 필요해요. | 재업로드 |`
  - `docs/reference-capture-guide.md` §1 표 `| 기본 시점 | **단일시점 1개** (정면 우선) |`(:27) · §2 `- **정면성:** 정면(또는 동작이 가장 잘 드러나는 단일 각도)을 기본으로 한다. 비스듬한 사각(斜角)은 좌우 occlusion 을 키운다.`(:47-48)
  - 실패 문구 정본(3벌 동일) `no_human: '영상에서 사람을 찾지 못했어요. 전신이 보이게 다시 촬영해주세요.'`(`models.py:810`, `analysis.ts:2221`)

### Q10. 강사 코드 — REQ-38-5

- 백엔드(`sunity_shared`·`functions` .py)에 `supplier|instructor|studioCode|instructorCode|referral` 0건; `attribution` 1건은 `_assess_attribution_reliability`(관절 귀속 신뢰, 무관) [확인 grep]. 앱도 `attributionReliability` 뿐 [확인]. Firestore `suppliers`/`attribution` 컬렉션은 코드에 없다.
- `app/src/app/(tabs)/profile.tsx`(426줄): 계정 카드 블록 :137-176(게스트 `Pressable`/회원 `View`, 스타일 `card·avatar·profileText·profileName·profileMeta·cardAction·guestHint`) → "내 몸 정보" :178-200 → 통계 `StatBox` :203-210 → 정보 리스트 `InfoRow(label,value,isLast)` :213-227(주 종목/레벨/앱 버전) → 안내 :230-234 → 로그아웃 :237+. 테마 `colors, layout, radius, spacing, typography`(:28). **한 줄 자리** = 계정 카드 바로 아래(D-12 "계정 카드 아래 한 줄"): `InfoRow` 재사용이 가장 싸다.

### Q11. 배포 경로 · CORS

- `backend/samconfig.toml`: stack `sunity-motion-pilot`, region ap-northeast-2, `confirm_changeset = true`, `resolve_s3 = true`, `parameter_overrides "Stage=pilot VideoBucketName=… FirebaseSaParam=…"`; 빌드 `cached·parallel`. 메모리: `sam build --use-container` 필수.
- 라이브 함수(`sunity-motion`): `upload-url`·`reference`·`reference-auto-register` LastModified **2026-07-21**(layer `sunity-motion-pilot-shared:16`), `pipeline` 2026-09-25(layer :16), `playback-url` 2026-09-09(layer **:20**, Timeout 30/Memory 512 — template 의 07-22 커밋 값과 일치), `podwatch-probe` 08-18 [확인]. 스택 LastUpdated 07-21 이후 `template.yaml` 커밋 2건(07-22 `9615d7cb`, `f07b3a5c` 32-16) [확인 git log]. → 라이브 = "CFN 스택(07-21) + 손 갱신(playback-url 설정·layer 20, pipeline 코드)". 메모리 lambda-code-update: "`sam deploy` 는 금지" + 코드/레이어만 갈아끼우는 절차. **새 라우트·함수는 그 절차로 못 만든다**(HttpApi route·integration·permission·log group = CFN 리소스).
- HTTP API CORS: template :178-181 `AllowOrigins ["*"], AllowHeaders [Content-Type, Authorization], AllowMethods [GET, POST, OPTIONS]`; 라이브도 동일(`apigatewayv2 get-apis`) [확인]. 라이브 라우트 4개: `POST /reference/auto-register`, `POST /playback-url`, `GET /reference`, `POST /upload-url` [확인]. → 브라우저 `fetch` + `Authorization` 헤더 통과. S3 PUT 은 Q1 CORS 로 통과.
- `sunity-motion` 의 `cloudformation:CreateChangeSet/ExecuteChangeSet`·`lambda:CreateFunction`·`apigatewayv2:CreateRoute` 권한 [미확인].

### Q12. 테스트

- `backend/tests/`(182 항목) + `conftest.py`(sys.path 에 `shared/python`·`scripts`·리포 루트 주입). `backend/.venv` Python 3.14.6 / pytest 8.4.2. `pytest.ini`·`pyproject` 없음. 실행: `cd backend && .venv/bin/python -m pytest tests/test_s3keys.py tests/test_validation.py tests/test_hold_height.py tests/test_reference_auto_register_handler.py -q` → **83 passed, 1.53s** [확인]. 전체 suite 소요 [미확인].
- 선례: `test_s3keys.py`(라운드트립·외부 키 거부 — `reference/` 는 거부 목록에 아직 없다 :20-27), `test_validation.py`, `test_reference_auto_register_handler.py`(핸들러 dir sys.path + env monkeypatch + `import app`), `test_hold_height.py`(합성 keypointReport), `test_rtmw_engine.py`(mock inferencer), `test_events`(SQS 파서). 앱: `npm run typecheck` = `tsc --noEmit` **clean, 4.3s** [확인]; JS 러너 없음(`__tests__/unjudgedJoints.test.ts` 는 있으나 script 없음).

### Q13. Pod 의존 · 부재 판정

- Lambda 는 Pod 생존을 모른다 — `_runpod_enabled()` 는 env 비공백만 본다(:194); 라이브 `RUNPOD_ANALYZE_URL` 은 **설정돼 있다**(`runpodUrlSet: true`) [확인] — Pod 은 전부 down(메모리). 위임 실패(연결 거부/404/타임아웃 10s) → `RuntimeError` → `fail_analysis(server_error)` 문구 "분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요."(`models.py:812`; 앱 `loading.tsx:491` "…잠시 후 다시 시도하면 대부분 잘 돼요.") — 기획안 §10 단계 1 ⑴의 "거짓말".
- Pod 부재 신호 두 개: SSM `/sunity/motion/pod-expected`(podwatch `pod_expected_up()` `backend/infra/podwatch.yaml:135-146`: 값 ≠ "down" 이면 up, 파라미터 없으면 up) — `start_server.sh:95-97` 이 `up`, `pod_teardown.py:125-127` 이 `down` 을 쓴다; `GET /health`(`server.py:301-323`: `status, pipeline_loaded, commitSha, envFlags, modelInitCanary.modelLoaded`, 인증 불요; podwatch `probe()` 는 `status=="ok" and pipeline_loaded` 를 healthy 로 본다 :157-168).
- SQS: `AnalysisQueue` VisibilityTimeout 960s, `maxReceiveCount 3` → DLQ(14일 보존)(`template.yaml:140-154`). Lambda 가 예외를 던지면 3회 재시도(~48분) 뒤 DLQ — **Pod 기동 시 자동 재개 수단이 아니다**.
- Pod 쪽 다운로드는 read timeout 이 없어 링크가 멎으면 "분석 중" 에 머문다(메모리 pod-link; `_s3_download` :160-180 실측 코드) — 등록도 같은 경로를 타므로 같은 위험.

## 진단 · 권장 (재검증 대상 — 관측이 아니다)

### A. 등록 경로의 최소 분기점 (REQ-38-1·2)

1. `s3keys.py`: `REFERENCE_UPLOAD_KEY_RE = ^reference/(?P<uid>[A-Za-z0-9]+)/(?P<ref_id>[A-Za-z0-9]+)\.(?P<ext>mp4|mov)$` + `build_reference_upload_key(uid, ref_id, ext)` / `parse_reference_key(key)`. uid 세그먼트를 영숫자로 제한하면 `reference/_archive/…`·평면 `reference/ref-*.mp4` 는 매치되지 않아 기존 객체·손 업로드가 절대 새 경로로 들어오지 않는다. `videoS3Key` 도 이 키 → playback-url 의 `reference/*` GetObject 권한(template :216-241 ARN `reference/*`) 안에 있다. 조인 키 = `ref_id`(uuid hex, `validate_analysis_id_format` 재사용) — 표시 문자열 금지(메모리).
2. 버킷 알림: 같은 큐 ARN 으로 두 번째 QueueConfiguration(prefix `reference/`) 추가 — README 명령을 두 항목으로 확장해 **한 번에 put**. 별도 큐는 불필요(Lambda 하나, 접두사 분기).
3. `lambda_handler`: `parse_reference_key` 를 먼저 시도 → 성공 시 (i) 기준 doc 이 `registrationStatus == 'registering'` 인지 확인(없으면 스킵 로그 — 손 업로드 방어) (ii) Pod 부재 판정: SSM `pod-expected == down` **또는** `/health` 실패(12s) → doc `registrationStatus: 'queued', queuedReason: 'pod_down', updatedAt` 후 **정상 반환**(메시지 소비) (iii) 있으면 doc `'processing'` + `POST {RUNPOD_BASE}/register-reference {bucket,key}`. 실패 → doc `'failed', reason: 'server_error'`.
4. `server.py`: `POST /register-reference`(같은 토큰 검증, `parse_reference_key`, BackgroundTasks → `pipeline_app._register_reference(bucket, key, uid, ref_id)`), `/analyze` 는 무접촉.
5. `pipeline/app.py::_register_reference`: `_ensure_adapters()` → `_download_analysis_video` → `_FRAME_EXTRACTOR.extract(path)` → `pose_frames = _POSE_ESTIMATOR._engine.estimate_with_person_counts(frames, _POSE_ESTIMATOR._default_pole)`(신설, §B) → 실패 4형 판정(순수 함수, §B) → `kp = to_coco17_array(pose_frames)`; `angles = temporal_fill(compute_joint_angles(kp), joint_uncertainty(kp))`; `report = build_keypoint_report(pose_frames, fps=effective_fps(src_fps, 9.0))`(`frame_extractor.effective_fps` :30 — 라벨 fps 가 아니라 **실효 fps** 를 `anglesRealFps` 에 기록, `_reference_angles_fps` 우선순위와 일치) → `firestore_admin.set_reference_angles(...)` → `registrationStatus: 'active'` + `isActive: true` → §C 자기 재현성 트리거. 채점 경로(`recognizer`, `dimensions`, `assemble.build_mode1`)는 호출하지 않는다.
6. 재개: Pod 기동 절차(메모리 demo-only 5단계)에 6단계 추가 — `backend/scripts/requeue_reference_registrations.py`: `reference` 컬렉션에서 `registrationStatus == 'queued'` 를 **단일 where 쿼리**(읽기 수 ≈ 대기 건수, Spark 캡 무관)로 뽑아 Pod `/register-reference` 에 순차 POST. 온디맨드 자동 기동은 범위 밖(D-20).

### B. 실패 4형 — 순수 함수 하나로 모은다 (REQ-38-4)

`sunity_shared/analysis/registration_checks.py`(numpy 만, Pod/Firestore 무관) 에 `check_registration(pose_frames, person_counts, report, *, n_stand, fps) -> RegistrationVerdict(ok, reason, detail)`:
- `no_human`: 엔진의 `NoHumanError` 를 그대로 받아 `reason='no_human'`(문구 = 기존 `ERROR_MESSAGE[no_human]` 재사용, D-09).
- `multiple_people`: `person_counts`(프레임별 N) 에서 `N ≥ 2` 인 프레임 비율 ≥ **0.30** 이면 실패 [ASSUMED 문턱 — 순간 지나가는 사람 1~2프레임은 봐준다]. 엔진 변경: `_infer_raw` 가 `(kps, scores, n)` 을 돌려주거나 `estimate_with_person_counts()` 를 신설해 **반환값으로만** 전달(사이드카 금지). `estimate()` 는 byte-동일.
- `no_standing_start`: `hold_height._frame_series(report, (n_stand, T))` 가 None(창 이전 프레임 부족·몸길이 ≤ 0) 이거나 창 `lowFoot` 10% 분위 < −0.10 이면 실패. `n_stand` = 폼의 `clipRange.execStartS × fps`(있으면) 아니면 **첫 1.0초** [ASSUMED 기본값 — nnt 규칙은 "창 이전 = 서 있음" 이라 서 있는 길이를 정해야 한다]. `hold_height` 의 판정을 공개 함수 `floor_reference_valid(report, window) -> bool | None` 로 빼서 두 소비처가 같은 상수를 쓰게 한다(상수 `FLOOR_VIOLATION_BODY_LENGTH` 이동 금지).
- `low_confidence`: keypointReport `confidence`(T×12) 의 **관절별 중앙값 < 0.5** 인 관절 목록 [ASSUMED 문턱 = 표시 게이트 `_KP_CONF_MIN` 과 같은 값; 메모리상 0.6 위가 유의미하므로 문턱은 상수 하나로 두고 시험 영상으로만 조정]. 문구 "일부 관절을 못 읽었어요(부위 목록)" — 12관절 한국어 라벨은 `skeleton.JOINT_LABEL_KO`(8개) 에 발목·손·팔꿈치 추가 필요 [확인 8개뿐].
- doc 형상: `registrationStatus ∈ {registering, queued, processing, failed, active}`(**analysis status enum 과 별개 필드**, `models.py:721` 규칙), `registrationError: {code, message, joints?: [..]}`, `queuedReason`, `*UpdatedAt`. 3벌 lockstep: `analysis.ts ReferenceMotion` + `models.py` 상수 + `contract.md §3`.

### C. 자기 재현성 (REQ-38-4)

등록 `active` 직후 Pod 가: (1) `firestore_admin.create_analysis_doc(supplier_uid, new_id, {mode:'mode1', referenceMotionId: ref_id, status:'uploading', fileName, createdAt, updatedAt, selfCheckForReference: ref_id})` (2) `s3.copy_object` → `uploads/{supplier_uid}/{new_id}.mp4` (3) 기준 doc `selfCheckStatus: 'pending', selfCheckAnalysisId`. `_process` 의 `complete_analysis` 직후(:10140)에 `if meta.get("selfCheckForReference"): firestore_admin.set_reference_self_score(ref_id, result["overallScore"], analysis_id)` — 채점 무접촉, 실패는 graceful 로그. **uid = 공급자 uid** 권장: 기획안 §4 "공급자가 본인 영상을 수요자로 올림 = 재현성 감시의 정규 경로" 와 같고, 정은지 앱 기록에 남아 눈으로 확인할 수 있다 [ASSUMED 선택 — 서비스 uid 대안은 기록에 안 보인다]. 페이지 문구: `selfScore ≥ 90` 이면 "N점 — 기준으로 쓸 수 있어요", 아니면 "N점 — 다시 찍어 주세요" [ASSUMED 문턱 90; "100 근처" 의 숫자는 belle 가 정한다 — 목표 숫자 금지 메모리].

### D. 공급자 인증 · 로그인 (D-03)

- 화이트리스트 = `SUPPLIER_UIDS`(SSM) ∪ `BELLE_UID`. 익명 uid 는 브라우저 저장소에 묶여 바뀌므로 화이트리스트 재료로 부적합 → **Google 로그인**(정은지 Google 계정)이 실증 후보. 웹에서는 `firebase/auth` 의 `signInWithPopup(auth, new GoogleAuthProvider())`(socialAuth 의 네이티브 경로 대신 `socialAuth.web.ts` 분기) — Firebase 콘솔 Authorized domains 에 페이지 도메인 추가 [CITED]. `signInWithRedirect` 는 S3/CloudFront 도메인에서 Safari/Chrome 차단 대상이라 쓰지 않는다(옵션 1 = Firebase Hosting 커스텀 authDomain 이면 가능) [CITED]. 같은 프로젝트라 그 uid 는 **앱에서 Google 로 로그인해도 같은 uid** → 화이트리스트 1건이 페이지와 미래의 앱 공급자 모드에 같이 쓰인다.
- 폰 브라우저에서 팝업이 실제로 되는지는 **[미확인]** — §H 측정 항목.

### E. `reference/` 키 체계 · Lambda 배치 · SQS (Claude's Discretion)

- 키: `reference/{supplierUid}/{refId}.{ext}` (기존 11개 평면 키 무접촉). techniqueKey/버전 세그먼트는 §7-2 분리(범위 밖) 때 doc 필드(`techniqueKey`, `version`)로 두면 되고 키에 박을 필요 없다 — 키를 바꾸면 조인이 표시 문자열에 묶인다.
- Lambda: **새 함수 `reference-upload-url`**(`POST /reference/upload-url`). 이유: `upload-url` 은 `uploads/*` PutObject 만(template :192-195) 이라 `reference/*` PutObject 정책 + Firestore 쓰기(SSM SA)가 추가로 필요하고, 얇은 핸들러 규율상 분기보다 함수가 낫다. 응답 `{refId, uploadUrl, s3Key, expiresInSec}`; 요청 = 폼 메타(`name, athleteName, level, techniqueName, isSplit, hasHold, standingStart, clipRange?, consent{portrait, usage, silent, training(default false)}, format, fileSizeBytes, durationSec`).
- SQS: 같은 큐, 키 접두사 분기(§A-2).

### F. 앱 길이 검사·문구 (REQ-38-6)

`validate()` 에 `duration` 검사 추가 — `asset.duration` 이 유효(`> 0`)할 때만 `sec < 3 → 'tooShort'`, `sec > 90 → 'tooLong'`, 없으면 통과(fail-open; iOS/Android 는 제공 [CITED]). `PickFailureKind` 에 두 종류 + `pickerFailure.ts` 문구(`tooShort` = IA `AC-VID-003-1L` 문구 재사용, `tooLong` 신규 [ASSUMED 문구]). 카메라는 `videoMaxDuration: 90`. 서버 계약(`validate_upload_request`) 무변경 — 공급자 5~30초는 Pod 가 `T / anglesRealFps` 로 실측해 `registrationError: too_long/too_short` 로 두 번째 방어 [ASSUMED 설계]. 문구 정정 5곳은 Q9 원문을 D-15 문장으로 치환.

### G. `uploads/` 영구 보관 (REQ-38-7)

`aws s3api delete-bucket-lifecycle --bucket sunity-motion-pilot-videos --profile sunity-motion` + 확인 `get-bucket-lifecycle-configuration` → `NoSuchLifecycleConfiguration`. 주석 정정 3곳: `s3keys.py:3-4`, `template.yaml:130-135`, `backend/README.md:79-82`(명령 자체를 "해제됨(2026-09, D-17)" 로), `intake_clips.py:27` 주석("`uploads/` 는 30일 뒤 지워진다"). 비용 서술은 CONTEXT 값 유지.

### H. 페이지 호스팅 — **권장 없음, 이걸 재야 답이 나온다**

| 후보 | 지금 상태 | 재야 할 것 | 배포 절차(측정 뒤) | 비용 |
|---|---|---|---|---|
| (1) Expo Router 공급자 라우트 web export → S3+CloudFront | `react-native-web` 부재로 export 가 의존성 게이트에서 정지 [확인] | ① `cd app && npx expo install react-native-web`(lockfile 변경 — **승인 task**) ② `npx expo export --platform web` 성공 여부·`dist/` 크기 ③ `npx serve dist` 를 폰 Safari/Chrome 에서 열어 익명 로그인·Google 팝업·`.mov` 파일 선택·presigned PUT 4가지 ④ 실패 시 `src/lib/{firebase,socialAuth}.web.ts` 분기 후 재측정 | 새 버킷 + CloudFront(OAC, SPA 404→index.html) + `aws s3 sync dist/` + invalidation; CloudFront 생성 권한 [미확인] | S3 센트 단위 + CloudFront Free plan(1M req/100GB) [CITED] |
| (2) 단일 HTML(vanilla JS + Firebase 웹 SDK ESM + fetch + XHR PUT + `onSnapshot`) | 의존성 0, 지금 당장 만들 수 있다 | 같은 폰 브라우저 4가지(로그인·파일·PUT·구독) | 같은 S3+CloudFront | 같음 |
| (3) (1) 또는 (2) 를 **Firebase Hosting**(같은 프로젝트) 에 | `.firebaserc` 있음, `firebase-tools` devDep 없음 [확인] | 로그인 리다이렉트가 같은 도메인에서 되는지 | `firebase deploy --only hosting` | 무료 tier [ASSUMED] |

판정 기준(플래너가 쓸 것): "같은 앱" 을 문자 그대로 지키려면 (1); 실증 마감이 우선이면 (2). 어느 쪽이든 로그인·PUT 실측 없이는 고르지 않는다. design.md §0 결정 트리(카드 15pt radius, CTA 54pt/13pt, 흰 배경, #FF4B33)와 Pretendard 는 (2) 에서도 CSS 로 재현 가능.

### I. 배포 (REQ-38-1 새 라우트)

새 함수+라우트는 CFN 변경이 필요하다. 두 길: (a) `sam build --use-container` → `sam deploy`(changeset 확인 — samconfig 가 이미 `confirm_changeset=true`): 라이브와 template 의 드리프트는 실측상 playback-url 설정(이미 손 반영)·layer 버전(16/20 혼재) 정도라 changeset 이 보여줄 변경은 "layer 새 버전으로 5함수 재바인딩 + 새 함수/라우트" 다 — 메모리가 경고한 '한 달치 드리프트 얹기'가 이번엔 layer 전체 갱신이므로 **belle 승인 체크포인트** 뒤에만; (b) CLI 로 함수·라우트·통합·권한·로그그룹 수동 생성 — 드리프트를 키운다. 권장 (a). 선행: SSM `/sunity/motion/supplier-uids` 생성(동적 참조), `sunity-motion` 의 CFN 권한 확인 [미확인].

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| boto3 (Lambda 런타임 제공) | 런타임 | presigned PUT · S3 copy · SSM | 기존 `upload-url`·pipeline 과 동일 [확인] |
| firebase-admin >=6,<7 | 기존 | 토큰 검증 · `reference/` Admin 쓰기 | `auth.py`·`firestore_admin.py` [확인] |
| numpy | 기존 | 실패 4형 순수 판정 | 분석 코어 규율 [확인] |
| rtmlib RTMW-x + YOLOX (Pod) | 기존 | 각도 추출·사람 수 | 운영 백본 [확인] |
| firebase JS SDK ^12.13.0 | 기존 | 웹 페이지 로그인·`onSnapshot` | 앱과 같은 프로젝트 [확인] |
| pytest >=8,<9 · tsc | 기존 | 게이트 | `requirements-dev.txt`, `npm run typecheck` [확인] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-native-web | ^0.21.0 (레지스트리 0.21.3) | Expo web export 의존성 | 후보 (1) 을 재기로 할 때만 [확인 npm view] |
| expo-image-picker ~17.0.11 | 설치됨 | `duration`(ms) 길이 검사 | 앱 REQ-38-6 [확인] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Expo web export | 단일 HTML | 코드베이스 분리 vs 의존성·번들 리스크 0 (§H) |
| S3+CloudFront | Firebase Hosting | 리다이렉트 로그인 가능·HTTPS 기본 vs 스택 문서(S3+CloudFront) 와 다름 |
| 같은 SQS 큐 접두사 분기 | 별도 큐 | 함수 하나로 끝 vs CFN 리소스 추가 |

**Installation:** 신규 백엔드 패키지 없음. 앱은 후보 (1) 일 때만 `cd app && npx expo install react-native-web`.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| react-native-web | npm (0.21.3, modified 2026-09-25) | 다년(necolas) | [미확인] | github.com/necolas/react-native-web | [OK] (npm 생태계 지정) | Approved — **설치는 승인 task 로** |

**Packages removed due to slopcheck [SLOP] verdict:** none (PyPI 로 잘못 검사한 1차 [SLOP] 은 생태계 오지정 — npm 재검사 OK).
**Packages flagged as suspicious [SUS]:** none.
**주의:** `slopcheck install` 은 검사 뒤 실제 설치를 실행한다 — 이번 세션에서 홈 디렉터리에 설치됐다가 되돌렸다(Q8). 플래너는 `slopcheck install` 을 task 에 넣지 말 것.

## Architecture Patterns

### System Architecture Diagram

```
[정은지 폰 브라우저]
   │ Firebase 웹 로그인(Google 팝업 / 익명은 화이트리스트 부적합)
   │ POST /reference/upload-url {폼 메타, 선언 4, 동의 4, format, size, durationSec}  (Bearer idToken)
   ▼
[Lambda reference-upload-url]  verify_request → SUPPLIER_UIDS 화이트리스트 → 검증(순수)
   │  refId=uuid hex · key=reference/{uid}/{refId}.mp4 · presigned PUT(900s)
   │  Firestore reference/{refId} create() {registrationStatus:'registering', 폼·동의, supplierUid, videoS3Key, isActive:false}
   ▼
[브라우저] XHR PUT → S3 (CORS PUT *)          [브라우저] onSnapshot(reference/{refId}) — 상태·실패 문구·selfScore
   ▼
[S3 ObjectCreated prefix reference/] → SQS AnalysisQueue (2번째 QueueConfiguration)
   ▼
[Lambda pipeline lambda_handler]
   parse_reference_key ─┬─ None → 기존 parse_upload_key 경로(무접촉)
                        └─ 매치 → doc 'registering' 확인 → Pod 판정(SSM pod-expected / GET /health)
                              ├─ 없음 → doc 'queued'(queuedReason pod_down) → return   ··· Pod 기동 시 requeue 스크립트
                              └─ 있음 → doc 'processing' → POST Pod /register-reference {bucket,key}
   ▼
[Pod server.py /register-reference] → pipeline._register_reference
   download → extract(9fps/640) → RTMW estimate_with_person_counts → 실패 4형 판정(순수)
   ├─ 실패 → doc 'failed' {code, message, joints?}
   └─ 통과 → angles(flat)+anglesRealFps+referenceKeypointReport+referenceSplitAngle → set_reference_angles
             → doc 'active', isActive:true  → [앱 picker 에 뜸: name·athleteName·level]
             → 자기 재현성: users/{uid}/analyses/{id} 선작성 → S3 copy → uploads/ 알림 → 기존 mode1 경로
                                                      └─ complete_analysis 직후 훅 → reference/{refId}.selfScore
```

### Recommended Project Structure
```
backend/
├── functions/reference-upload-url/app.py        # 신규 Lambda (얇게: 인증→화이트리스트→검증→서명+doc 선작성)
├── functions/pipeline/app.py                    # lambda_handler 접두사 분기 + _register_reference
├── runpod_inference/server.py                   # POST /register-reference
├── shared/python/sunity_shared/
│   ├── s3keys.py                                # build/parse_reference_key (+ :3 주석 정정)
│   ├── validation.py                            # validate_reference_upload_request (순수)
│   ├── models.py                                # REGISTRATION_STATUS_* · REGISTRATION_ERROR_MESSAGE · supplier 파서
│   ├── firestore_admin.py                       # create_reference_registration / set_reference_angles / set_reference_registration_status / set_reference_self_score / create_analysis_doc
│   └── analysis/registration_checks.py          # 실패 4형 순수 판정 (+ hold_height 공개 함수, rtmw_engine person counts)
├── scripts/requeue_reference_registrations.py   # Pod 기동 시 queued 재개
└── tests/test_{s3keys,validation,registration_checks,reference_upload_url_handler,firestore_reference_writers,supplier_whitelist}.py
app/src/
├── app/(tabs)/analyze.tsx · lib/pickerFailure.ts   # duration 검사 + 문구
├── app/analysis/loading.tsx · (tabs)/profile.tsx   # 문구 정정 · 강사 코드 한 줄
├── app/supplier/{index,guide}.tsx (후보 1) 또는 web/supplier.html (후보 2)
└── lib/{firebase,socialAuth}.web.ts (후보 1, 필요 시)
docs/supplier-guide.md · docs/ia.md · docs/reference-capture-guide.md · docs/contract.md
```

### Pattern 1: 얇은 Lambda + 순수 검증 (기존 `upload-url` 미러)
**What:** 인증 → 순수 검증(`ValidationError(code,message,http_status)`) → 부작용 1(서명 + doc create) → 응답 봉투 `responses.ok/error`.
**When to use:** `reference-upload-url`. `uploads/` 와 정책·키 규칙이 다르므로 함수 분리.

### Pattern 2: 접두사 분기 + Pod 부재 fail-safe
**What:** `lambda_handler` 에서 `parse_reference_key` 우선; Pod 부재면 doc 상태만 바꾸고 정상 반환(메시지 소비). 재개는 명시적 스크립트.
**When to use:** 등록 경로 전용. 학생 분석 경로는 무접촉(이번 phase 범위 밖 — 기획안 §10 단계 1 ⑴).

### Pattern 3: ADD-only writer (`update_reference_*` 미러)
**What:** 빈 id 거부 → 필수 키 검사 → `_validate_flat_dict_no_nested_array` → `*UpdatedAt` → `set(merge=True)`. 선작성은 `doc.create()`(존재하면 실패) 로 기존 11개를 구조적으로 못 건드리게. `set_reference_angles` 는 `angles` 를 **쓰는 유일한 writer** 이며 legacy id(`ref-*`) 를 거부하는 가드 한 줄을 둔다.

### Pattern 4: 판정은 순수 함수, 강제는 합성 입력
**What:** 실패 4형은 `pose_frames`/`person_counts`/`keypointReport` 만 받는 순수 함수; 테스트는 mock inferencer + 합성 report 로 넷 다 강제.

### Anti-Patterns to Avoid
- **`_process` 를 등록에 재사용:** 첫 줄에서 분석 doc 을 요구하고(:8604) 채점·Gemini·카드까지 다 돈다. 어댑터만 빌린다.
- **엔진 인스턴스에 사이드카 상태(사람 수) 저장:** 동시 분석에서 섞인다(HIGH-1 v4 주석). 반환값으로.
- **analysis `status` enum 에 등록 상태 추가:** `models.py:721` 금지. 기준 doc 의 별도 필드.
- **알림/수명주기 `put-*` 를 한 항목만으로 실행:** 교체-전체라 기존 `uploads/` 알림이 사라진다.
- **표시 문자열(동작 이름)을 doc id·S3 키로:** 조인 불변 id 규칙(메모리).
- **익명 uid 화이트리스트:** 브라우저 저장소 초기화마다 uid 가 바뀐다.
- **`slopcheck install`:** 실제 설치를 실행한다.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| presigned PUT | 직접 SigV4 | `boto3 generate_presigned_url(put_object)`(`upload-url/app.py:53-57`) | 기존 검증된 호출 |
| S3 이벤트 파싱 | 새 파서 | `sunity_shared.events.iter_s3_keys_from_sqs` | URL 디코딩·깨진 레코드 처리 포함 |
| ID 토큰 검증 | JWT 수동 | `sunity_shared.auth.verify_request` | firebase-admin 인증서 회전 처리 |
| 각도·보간 | 새 수식 | `compute_joint_angles`·`joint_uncertainty`·`temporal_fill`(`extract_reference_angles.py:127-130` 순서 그대로) | 기준 11개와 같은 산출 경로(= mode1 양쪽 원질) |
| keypointReport | 직접 flat 조립 | `assemble.build_keypoint_report(pose_frames, fps=)` | 12관절·conf·reliability 규약 |
| 실효 fps | 라벨 fps 저장 | `frame_extractor.effective_fps(src, 9.0)` → `anglesRealFps` | `_reference_angles_fps` 우선순위 (quick-260810-e4v) |
| 바닥 기준 | 새 판정 | `hold_height` 상수·`_frame_series` | nnt 규칙과 상수 하나 |
| nested-array 검증 | 수동 검사 | `_validate_flat_dict_no_nested_array` | 프로젝트 정책 |

**Key insight:** 등록 경로의 산출물이 기준 11개와 **같은 함수**로 나와야 mode1 이 같은 원질을 비교한다(D-09 정신). 새 수식은 곧 위양성이다.

## Runtime State Inventory

> 이 phase 는 rename/refactor 가 아니라 신설이다. 단 "무접촉" 요구가 있어 런타임 상태를 점검했다.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `reference` 11 doc + `reference/{id}/versions/*` + `reference/_release` 포인터 [확인 코드]; 저장 분석 875건(메모리) | 무접촉 — 새 doc 은 `create()`, legacy id 가드 |
| Live service config | 버킷 알림(prefix `uploads/`) · lifecycle 1규칙 · CORS PUT · SSM 16 파라미터 [확인] | 알림 2항목 put · lifecycle delete · SSM `supplier-uids` 생성 |
| OS-registered state | launchd `com.sunity.flywheel`(주 1회, manifest 기반) [확인 기획안 §10-2] | 공급자 영상은 manifest 밖(D-21) — 접촉 없음 |
| Secrets/env vars | Lambda env `BELLE_UID`(SSM) · Pod `RUNPOD_AUTH_TOKEN` [확인 키만] | `SUPPLIER_UIDS` 추가만, 기존 키 불변 |
| Build artifacts | 라이브 layer :16/:20 혼재, 스택 07-21 [확인] | `sam deploy` 시 layer 재바인딩 — 체크포인트 |

## Common Pitfalls

### Pitfall 1: 알림이 `reference/` 를 받지 않는다
**What goes wrong:** 업로드가 끝나도 아무 일도 안 일어난다. **Why:** 버킷 알림 prefix 가 `uploads/` 뿐 [확인]. **How to avoid:** 2항목 put + 확인 `get-bucket-notification-configuration`. **Warning signs:** CloudWatch pipeline 로그에 `/register-reference` 0건.

### Pitfall 2: 도착해도 "스킵" 로그로 사라진다
**What:** `parse_upload_key → None → continue`(:10309-10312). **Avoid:** `parse_reference_key` 를 먼저. **Signs:** 로그 `스킵: 인식 불가 S3 키 reference/...`.

### Pitfall 3: doc 을 PUT 뒤에 쓰면 조용히 틀린 모드
**What:** 자기 재현성 분석 doc 이 없으면 `_process` 가 `RuntimeError("분석 문서 없음")`, 있어도 `mode` 없으면 mode3 로 떨어진다(메모리 demo-only). **Avoid:** doc 먼저, `mode:'mode1'`+`referenceMotionId`. **Signs:** 자기 분석이 mode3 결과.

### Pitfall 4: Pod 부재가 `server_error` 로 위장
**What:** 위임 실패 → `failed(server_error)`(:10342). **Avoid:** 등록 경로는 SSM/health 로 먼저 판정해 `queued`. **Signs:** `RUNPOD_ANALYZE_URL` 설정됐는데 `pod-expected=down`.

### Pitfall 5: `duration` 이 웹·일부 픽에서 없다
**What:** iOS/Android 만 제공 [CITED]; 앱도 0/누락 가능(:218 주석). **Avoid:** 유효할 때만 검사(fail-open) + 서버 실측 2차 방어.

### Pitfall 6: 저장 fps 라벨 ≠ 실효 fps
**What:** 9fps 요청이 30fps 원본에서 10.0fps 로 나온다(`frame_extractor.py:30-40`). **Avoid:** `anglesRealFps` 에 실효값 기록.

### Pitfall 7: `T == 0` 은 `NoHumanError` 가 아니다
**What:** `estimate` 가 빈 리스트를 돌려준다(:230-231) → 각도 계산에서 다른 예외. **Avoid:** 프레임 0 은 등록 검증에서 `bad_video` 로 먼저 잡는다.

### Pitfall 8: Firestore 읽기 캡
**What:** Spark 5만/일. **Avoid:** requeue 스크립트는 `where registrationStatus == 'queued'` 단일 쿼리, 페이지 `onSnapshot` 은 자기 doc(또는 `supplierUid ==` 쿼리) 만.

### Pitfall 9: 웹에서 네이티브 로그인 모듈
**What:** `GoogleSignin.signIn` 이 웹에서 throw(스폰서 전용) [확인]. **Avoid:** 웹은 `firebase/auth` `signInWithPopup` 로 별도 파일.

## Code Examples

### A. `s3keys.py` — reference 키 (순수)
```python
# Source: 기존 _UPLOAD_KEY_RE 패턴 미러 (backend/shared/python/sunity_shared/s3keys.py:18-44)
_REFERENCE_KEY_RE = re.compile(
    r"^reference/(?P<uid>[A-Za-z0-9]+)/(?P<ref_id>[A-Za-z0-9]+)\.(?P<ext>mp4|mov)$"
)

def build_reference_upload_key(uid: str, ref_id: str, ext: str) -> str:
    return f"{REFERENCE_PREFIX}/{uid}/{ref_id}.{ext}"

@dataclass(frozen=True)
class ParsedReferenceKey:
    uid: str
    ref_id: str
    ext: str

def parse_reference_key(key: str) -> ParsedReferenceKey | None:
    m = _REFERENCE_KEY_RE.match(key)
    return None if not m else ParsedReferenceKey(m["uid"], m["ref_id"], m["ext"])
# 기존 평면 키 'reference/ref-kip-up.mp4' 와 'reference/_archive/…' 는 매치되지 않는다.
```

### B. `lambda_handler` 분기 (기존 루프 앞부분, :10308-10312 자리)
```python
# Source: backend/functions/pipeline/app.py:10297-10348 구조 유지
for bucket, key in iter_s3_keys_from_sqs(event):
    ref = parse_reference_key(key)
    if ref is not None:
        _handle_reference_upload(bucket, key, ref)   # queued/processing/failed 를 doc 에만 기록, 예외 삼킴
        continue
    parsed = parse_upload_key(key)
    if parsed is None:
        log.warning("스킵: 인식 불가 S3 키 %s", key)
        continue
    ...  # 이하 byte-동일
```

### C. ADD-only angles writer (`update_reference_body_data` 미러)
```python
# Source: firestore_admin.py:2173-2252 패턴
def set_reference_angles(ref_id: str, *, angles_flat: list, joint_keys: list, frames: int,
                         real_fps: float, keypoint_report: dict, split_angle: float | None) -> None:
    if not ref_id or ref_id.startswith("ref-"):           # legacy 11개 가드
        raise ValueError("ref_id invalid or legacy")
    if len(angles_flat) != frames * len(joint_keys):
        raise ValueError("angles length must be frames × len(joint_keys)")
    _validate_flat_dict_no_nested_array(keypoint_report, path="referenceKeypointReport")
    now_ms = int(time.time() * 1000)
    payload = {
        "angles": angles_flat, "anglesJointKeys": joint_keys, "anglesFrames": int(frames),
        "anglesUpdatedAt": now_ms, "anglesRealFps": float(real_fps),
        "referenceKeypointReport": keypoint_report,
        **({"referenceSplitAngle": split_angle} if split_angle is not None else {}),
    }
    _doc(models.reference_motion_path(ref_id)).set(payload, merge=True)
```

### D. 실패 4형 합성 강제 (pytest)
```python
# Source: tests/test_rtmw_engine.py:48-56 (mock), tests/test_hold_height.py:33-58 (report)
def test_no_human(real_manifest_path, default_pole_axis):
    mock = MagicMock(); mock.return_value = (np.zeros((0, 133, 2), np.float32), np.zeros((0, 133), np.float32))
    eng = RTMWPoseEngine.create_with_inferencer(mock, real_manifest_path)
    with pytest.raises(NoHumanError):
        eng.estimate(np.zeros((3, 480, 640, 3), np.uint8), default_pole_axis)

def test_multiple_people_counts():
    mock = MagicMock(); mock.return_value = (np.zeros((2, 133, 2), np.float32), np.full((2, 133), 0.9, np.float32))
    eng = RTMWPoseEngine.create_with_inferencer(mock, real_manifest_path)
    frames, counts = eng.estimate_with_person_counts(np.zeros((5, 480, 640, 3), np.uint8), pole)
    assert counts == [2, 2, 2, 2, 2]

def test_no_standing_start():   # 시작부터 매달림: 바닥이 공중 발목으로 잡혀 창 낮은발이 -0.10 아래
    rep = _report(_pose(T=40, stand=10, hip=0.5, low_ankle=0.83, high_ankle=0.8, hand=0.3), 40)
    # _pose 의 stand 프레임 ankle 을 0.6 으로 바꾼 변형 → lowFoot ≈ (0.6-0.83)/body < -0.10
    assert registration_checks.standing_start_ok(rep, n_stand=10) is False

def test_low_confidence_lists_ankles():
    scores = np.full((1, 133), 0.9, np.float32); scores[0, 15] = scores[0, 16] = 0.2   # COCO 15/16 = 발목
    ...  # build_keypoint_report → 관절별 중앙값 → ['left_ankle', 'right_ankle']
```

### E. selfScore 훅 (채점 무접촉)
```python
# Source: pipeline/app.py:10110-10140 complete_analysis 직후
ref_id = meta.get("selfCheckForReference")
if ref_id:
    try:
        firestore_admin.set_reference_self_score(ref_id, float(result["overallScore"]), analysis_id)
    except Exception:  # noqa: BLE001 - 기록 실패가 분석을 막지 않는다
        log.exception("selfScore 기록 실패 ref=%s analysis_id=%s", ref_id, analysis_id)
```

### F. 버킷 명령 (교체-전체 주의)
```bash
# Source: backend/README.md:72-111 + 이번 실측
export AWS_PROFILE=sunity-motion
aws s3api delete-bucket-lifecycle --bucket sunity-motion-pilot-videos                       # REQ-38-7 (규칙 1개뿐)
QUEUE_ARN=arn:aws:sqs:ap-northeast-2:976369350031:sunity-motion-pilot-analysis
aws s3api put-bucket-notification-configuration --bucket sunity-motion-pilot-videos \
  --notification-configuration "{\"QueueConfigurations\":[
    {\"Id\":\"uploads\",\"QueueArn\":\"$QUEUE_ARN\",\"Events\":[\"s3:ObjectCreated:*\"],\"Filter\":{\"Key\":{\"FilterRules\":[{\"Name\":\"prefix\",\"Value\":\"uploads/\"}]}}},
    {\"Id\":\"reference\",\"QueueArn\":\"$QUEUE_ARN\",\"Events\":[\"s3:ObjectCreated:*\"],\"Filter\":{\"Key\":{\"FilterRules\":[{\"Name\":\"prefix\",\"Value\":\"reference/\"}]}}}]}"
aws s3api get-bucket-notification-configuration --bucket sunity-motion-pilot-videos     # 두 항목 확인
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 손 3단계(S3 cp → Pod 스크립트 → seed merge) | 링크 업로드 → 자동 각도 → doc | 이 phase | 정은지가 스스로 기준을 올린다 |
| `reprocess…phase4.py` versions + 포인터 | 새 doc 은 top-level 소비(포인터 폴백) | 33-17 이후 | 새 등록은 versions 없이 동작 |
| `signInWithRedirect` 기본 | 팝업 또는 같은 도메인 authDomain | Safari 16.1+/Chrome M115+ [CITED] | S3/CloudFront 도메인에서 리다이렉트 불가 |

**Deprecated/outdated:** 앱 팁 "측면 45°, 2~3m" · 촬영 가이드 "정면 우선"(D-15) · `s3keys.py:3` "30일 후 자동 삭제"(D-17).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | web export 의 다음 차단 요인은 firebase/socialAuth 웹 분기 정도이고 expo-video·svg·picker 는 통과한다 | Q8/§H | 후보 (1) 공수 급증 → (2) 로 전환 |
| A2 | `firebase.ts` 는 웹에서 try/catch 폴백(`getAuth`)으로 우연히 동작한다 | Q7 | 로그인 자체 실패 → `.web.ts` 분기 필수 |
| A3 | Google OAuth 팝업은 HTTPS 도메인이 필요하다 | §D/§H | HTTP 로컬 테스트 불가, CloudFront 선행 |
| A4 | S3 website endpoint 는 HTTP 전용 | §H | CloudFront 없이도 될 수 있음(그래도 A3) |
| A5 | 서 있는 구간 기본값 = 첫 1.0초 | §B | 짧은 준비 동작을 실패로 오판 → 폼 `clipRange` 로 덮어쓰기 |
| A6 | 여러 명 문턱 = N≥2 프레임 비율 0.30 | §B | 지나가는 사람에 실패 남발 또는 두 사람 통과 |
| A7 | 저신뢰 문턱 = 관절 중앙값 0.5(표시 게이트와 동일) | §B | 메모리상 0.6 위가 유의미 — 시험 영상으로만 조정 |
| A8 | 자기 재현성은 공급자 uid 로 돌린다 | §C | 기록 오염이 싫으면 서비스 uid |
| A9 | selfScore 통과선 90 | §C | belle 가 정한다(목표 숫자 금지) |
| A10 | `sunity-motion` 프로파일에 CFN/Lambda 생성 권한이 있다 | §I | belle 계정으로 deploy |
| A11 | Firebase Hosting 무료 tier 로 충분 | §H | 비용 소액 |
| A12 | 웹 duration 은 `<video>` metadata 로 잰다 | §F | 페이지에서 길이 검사 못 함 → 서버 2차 방어 |
| A13 | 공급자 5~30초 서버 실측은 `T / anglesRealFps` | §F | 오차 ±1프레임 |
| A14 | `tooLong` 문구 신규 | §F | IA 표에 행 추가 |
| A15 | 전체 pytest suite 소요 시간 | Q12 | 게이트 시간 예측 불가 |

## Open Questions (RESOLVED)

> 2026-09-26 플래너 리비전 1 — 다섯 질문 전부 **재는 task 로 귀속**됐다(답을 미리 적지 않는다; 잰 값은 그 task 의 산출물에 `[확인]` 으로). 원문은 그대로 두고 `RESOLVED:` 줄만 붙였다.

1. **폰 브라우저에서 Google 팝업 로그인이 실제로 되는가**
   - 아는 것: 문서상 팝업은 모바일에서 "less smooth"; 리다이렉트는 S3/CloudFront 도메인에서 차단 [CITED]
   - 모르는 것: iOS Safari 팝업 차단 기본값에서의 실제 동작
   - 권장: §H 측정 ③ 을 계획의 첫 체크포인트로
   - RESOLVED: 38-04 Task 1(로컬 export + 시뮬 Safari 스모크) → Task 2(belle 4항목 ○/× `[확인 belle]`, `38-04-MEASUREMENT.md` 관측 절) → Task 3(결정 + 미선택 트랙 스킵). 실기기 HTTPS 는 38-13 Task 3.
2. **web export 가 번들되는가** — 의존성 설치 뒤에만 답이 난다(§H).
   - RESOLVED: 38-04 Task 1(`npx expo install react-native-web` → `CI=1 npx expo export --platform web` exit/소요 초/크기 → MEASUREMENT.md 관측 절; 그 소요 초가 38-10/38-11 의 플랜 단위 export 게이트 기준값).
3. **`sunity-motion` 의 배포 권한** — `sam deploy` changeset 생성으로 확인.
   - RESOLVED: 38-09 Task 1(`sam deploy --no-execute-changeset` — AccessDenied 면 그 명령·오류 원문을 CHANGESET.md 에 적고 멈추는 auth gate) → Task 2 belle 승인 → Task 3 실행 + (E) `iam simulate-principal-policy` 읽기 전용 확인.
4. **정은지 Google uid** — 로그인 1회 뒤 페이지가 uid 를 보여주고 belle 가 SSM 에 넣는 절차가 필요(닭-달걀: 화이트리스트 전에 페이지 접근은 "권한 없음" 화면).
   - RESOLVED: 38-14 Task 1(체크포인트 — 정은지/대역이 A-2 화면 `내 ID` 를 belle 에게, belle 이 `uid:CODE` + `pod:go <GPU>`) → Task 2 step 0(`aws ssm put-parameter --overwrite`, 배포 없이 60초 캐시 뒤 반영; 롤백 = `get-parameter-history`).
5. **여러 명·저신뢰 문턱** — 상수 하나로 두고 시험 영상 2차로만 조정(A6·A7).
   - RESOLVED: 38-05 Task 1 의 상수 `MULTI_PERSON_FRAME_RATIO = 0.30` · `LOW_CONFIDENCE_MEDIAN_MIN = 0.5` · `STANDING_START_DEFAULT_SEC = 1.0` — `[ASSUMED A5·A6·A7]` 주석 박제, **시험 영상 2차(`sealed_test.py`)로만 조정**(목표 숫자 금지; 38-14 에서 실물 실패가 나오면 코드·문구만 기록).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node / npm | 앱 typecheck·export | ✓ | v24.15.0 / 11.12.1 | — |
| react-native-web | web export | ✗ | (npm 0.21.3) | 단일 HTML 후보 |
| SAM CLI | 새 라우트 배포 | ✓ | 1.161.0 | CLI 수동 생성(비권장) |
| Docker (daemon) | `sam build --use-container` | client ✓ / daemon [미확인] | — | — |
| Python (backend/.venv) | pytest | ✓ | 3.14.6 / pytest 8.4.2 | — |
| AWS CLI + 프로파일 | 버킷 설정·읽기 | ✓ | 2.34.53; `sunity-motion` 읽기 확인 | — |
| RunPod Pod | 각도 추출·E2E | ✗ (의도적 down) | — | `queued` 상태 + 기동 시 requeue |
| Firebase Admin SA json | e2e·requeue 스크립트 | ✓ 리포 루트(e2e 스크립트 참조) | — | — |
| Context7 MCP / ctx7 | 문서 조회 | ✗ | — | WebFetch 공식 문서(사용함) |
| slopcheck | 패키지 검사 | ✓ (사용자 설치 0.6.1) | — | `npm view` |

**Missing dependencies with no fallback:** Pod(등록·E2E·selfScore 는 Pod 기동 세션에서만 검증 가능).
**Missing dependencies with fallback:** react-native-web(단일 HTML).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 (backend/.venv, Python 3.14.6); tsc 5.9 (`npm run typecheck`) |
| Config file | none — `backend/tests/conftest.py` 가 sys.path 주입 |
| Quick run command | `cd backend && .venv/bin/python -m pytest tests/test_s3keys.py tests/test_validation.py tests/test_registration_checks.py tests/test_reference_upload_url_handler.py -q` (현재 4파일 1.5s 급) |
| Full suite command | `cd backend && .venv/bin/python -m pytest tests -q` (소요 [미확인]) · `cd app && npm run typecheck` (4.3s) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-38-1 | `parse_reference_key` 라운드트립 · legacy/`_archive` 거부 · `uploads/` 무접촉 | unit | `pytest tests/test_s3keys.py -q` | ✅ 확장 |
| REQ-38-1 | `reference-upload-url` 핸들러: 401/403(화이트리스트)/400(폼)/200 + doc create 호출 | unit (monkeypatch) | `pytest tests/test_reference_upload_url_handler.py -q` | ❌ Wave 0 |
| REQ-38-1 | `lambda_handler` 접두사 분기: Pod down → queued(예외 0), up → 위임 호출 | unit (monkeypatch `_delegate`, SSM) | `pytest tests/test_pipeline_reference_dispatch.py -q` | ❌ Wave 0 |
| REQ-38-1/7 | 버킷 알림 2항목 · lifecycle 없음 | manual/smoke (AWS 읽기) | `aws s3api get-bucket-notification-configuration …`, `get-bucket-lifecycle-configuration` → NoSuchLifecycleConfiguration | — |
| REQ-38-2 | `set_reference_angles` 형상(길이 불일치 거부·legacy id 거부·flat 검증·payload 키) | unit (`_doc` monkeypatch) | `pytest tests/test_firestore_reference_writers.py -q` | ❌ Wave 0 |
| REQ-38-2 | 등록 산출 = 기준 11개와 같은 함수 순서(extract→estimate→angles→fill) | unit (mock engine) | `pytest tests/test_register_reference_pipeline.py -q` | ❌ Wave 0 |
| REQ-38-2 | 새 doc 으로 mode1 이 RuntimeError 없이 완주 · picker 노출 | **manual E2E (Pod)** | `e2e_app_path.py --mode mode1 --reference <refId>` | — |
| REQ-38-3 | 폼 검증 순수 함수(level enum·선언 4 bool·동의 필수 3 true·training 기본 false·5~30s) | unit | `pytest tests/test_validation.py -q` | ✅ 확장 |
| REQ-38-4 | 실패 4형 각각 합성 입력으로 강제 (Success ②) | unit | `pytest tests/test_registration_checks.py -q` | ❌ Wave 0 |
| REQ-38-4 | selfScore 훅: `selfCheckForReference` 있을 때만 writer 호출, 실패 graceful | unit (monkeypatch) | `pytest tests/test_self_score_hook.py -q` | ❌ Wave 0 |
| REQ-38-4 | 정은지 본인 영상 selfScore 100 근처 (Success ③) | **manual (Pod)** | 페이지/doc 확인 | — |
| REQ-38-5 | 마이 탭 한 줄 렌더 | typecheck + 시뮬 스크린샷 | `npm run typecheck` | ✅ |
| REQ-38-6 | `validate()` duration 3~90 · duration 없으면 통과 | unit (순수 함수로 분리 시) 또는 typecheck | `npm run typecheck` (+ 순수 함수 추출하면 node 로 실행) | ⚠ JS 러너 없음 |
| REQ-38-6 | 문구 정정 5곳 | grep 게이트 | `rtk grep -n '45°\|2~3m\|정면 우선' app/src docs` → 0건 | — |
| REQ-38-7 | 주석 정정 | grep | `rtk grep -n '30일' backend/shared/python/sunity_shared/s3keys.py` → 0건 | — |
| REQ-38-8 | `docs/supplier-guide.md` 7항목 존재 · 페이지 체크 5 | doc review + 시뮬/브라우저 스크린샷 | manual | — |
| 페이지 | 로그인·파일 선택·PUT·onSnapshot | **manual (폰 브라우저)** | §H ③ | — |

### Sampling Rate
- **Per task commit:** quick run command (+ `npm run typecheck` when app touched)
- **Per wave merge:** full suite command
- **Phase gate:** Full suite green + Pod E2E(등록 1건 → picker → mode1 완주 → selfScore) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_registration_checks.py` — REQ-38-4 (합성 4형)
- [ ] `backend/tests/test_reference_upload_url_handler.py` — REQ-38-1/3
- [ ] `backend/tests/test_pipeline_reference_dispatch.py` — REQ-38-1 (Pod down/up)
- [ ] `backend/tests/test_firestore_reference_writers.py` — REQ-38-2
- [ ] `backend/tests/test_register_reference_pipeline.py` — REQ-38-2
- [ ] `backend/tests/test_self_score_hook.py` — REQ-38-4
- [ ] `tests/test_s3keys.py`·`tests/test_validation.py` 확장
- [ ] 프레임워크 설치 없음(기존 pytest/tsc)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Firebase ID 토큰 `verify_request` (기존) |
| V3 Session Management | yes (웹) | Firebase 웹 persistence `local` 기본, 페이지는 자기 doc 만 구독 |
| V4 Access Control | yes | `SUPPLIER_UIDS` 화이트리스트(env 미설정 = 거부, auto-register 선례); S3 키의 uid 는 **토큰 uid 로만** 구성(클라이언트 값 금지); `firestore.rules` 쓰기 `false` 유지 |
| V5 Input Validation | yes | 순수 `validate_reference_upload_request`(enum·bool·길이·형식·크기·`validate_analysis_id_format`); 키 정규식으로 path injection 차단 |
| V6 Cryptography | yes | boto3 SigV4 presign(직접 구현 금지) |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 임의 uid/refId 로 남의 키에 PUT | Spoofing/Tampering | 키는 서버가 토큰 uid + 서버 생성 refId 로만 구성 |
| 손으로 `reference/` 에 올린 객체가 등록 경로를 깨움 | Tampering | `parse_reference_key` 영숫자 uid + doc `registering` 확인 없으면 스킵 |
| 기존 11개 doc 덮어쓰기 | Tampering | `create()` 선작성 + writer legacy id 가드 |
| 다른 공급자 doc 열람 | Information disclosure | `reference/**` 는 이미 인증 사용자 전체 읽기(규칙) — 파일럿 수용, 개인정보는 doc 에 두지 않는다(동의 텍스트 버전만) |
| 대용량·긴 영상으로 Pod 점유 | DoS | 100MB · 5~30s · 화이트리스트 |
| 동의 부인 | Repudiation | `consent{…, at, version, uid}` 를 Lambda 가 서버 시각으로 기록 |
| 프롬프트/OAuth 리다이렉트 | — | 웹 로그인은 팝업, Authorized domains 등록 |

## 벤치·상류 훑기 (페이지)

- 코치 도구형(Onform·CoachNow·Trainera)은 코치가 월정액을 내는 별도 도구, 마켓형(Skillest)은 같은 앱 — 우리 실증은 후자(같은 앱의 모드) [확인 `.planning/research/market-coaching-platforms-260925.md` §F-1]. Skillest "compare it side by side or overlay with another golfer, add skeleton tracking" → 고스트 오버레이는 끝 그림(범위 밖).
- 촬영 가이드 벤치(§F-7): 골프 온라인 레슨 가이드(삼각대·렌즈 높이 mid-torso·조명·배경), UNFORCE "Record a short test … Review it before recording a longer session", Onform "Full control over lighting and angles", SwingVision 저조도 오판 → `docs/supplier-guide.md` ①⑦ 재료. 폴댄스 7곳엔 강사용 업로드 가이드 소스 없음(§F-5) → 빈 자리.
- 상류 문서(이번 세션 조회): Expo publishing websites(`expo export -p web`, `dist/`, `web.output single|static|server`) · platform-specific modules(`.web.tsx` 규칙) · image-picker(웹 지원, `duration` Android/iOS) · video(웹 지원) · apple-authentication(웹 미지원) · react-native-google-signin web(스폰서 전용, `GoogleOneTapSignIn`) · Firebase redirect-best-practices / auth-state-persistence / anonymous-auth / google-signin · AWS lifecycle put(교체-전체) · S3 notification filtering(겹침 규칙) · S3 website hosting(Amplify/CloudFront 권장) · CloudFront pricing(Free plan).

## Sources

### Primary (HIGH confidence)
- 코드 실측(file:line 전부 이 세션에서 열었다): `backend/functions/pipeline/app.py`, `backend/runpod_inference/server.py`, `backend/shared/python/sunity_shared/{s3keys,auth,validation,models,events,firestore_admin}.py`, `analysis/{hold_height,features,temporal,assemble,frame_extractor,pose_frame}.py`, `analysis/pose_engines/rtmw/rtmw_engine.py`, `analysis/adapters/rtmw_133_to_coco17.py`, `backend/functions/{upload-url,reference-auto-register}/app.py`, `backend/scripts/{extract_reference_angles,reprocess_reference_motions_phase4,e2e_app_path,sealed_test,intake_clips,verify_self_comparison}.py`, `backend/infra/podwatch.yaml`, `backend/template.yaml`, `backend/samconfig.toml`, `backend/README.md`, `firestore.rules`, `app/src/{lib/{firebase,socialAuth,authUser,api,referenceMotions}.ts, app/(tabs)/{analyze,profile}.tsx, app/analysis/loading.tsx, types/analysis.ts, constants/motionThumbs.ts}`, `app/{package.json,app.json,tsconfig.json}`, `app/scripts/seed-reference-motions.mjs`, `docs/{ia,reference-capture-guide,reference-motions,contract}.md`, `design.md`, `app/CLAUDE.md`, node_modules 실물(`@firebase/auth`, `@react-native-google-signin`, `expo-apple-authentication`, `@react-native-async-storage`, `expo-image-picker` types)
- AWS 읽기 실측(`sunity-api`/`sunity-motion`): s3api get-bucket-{notification-configuration,lifecycle-configuration,cors,location,website,accelerate-configuration}, s3 ls, cloudformation describe-stacks, lambda list-functions/get-function-configuration, apigatewayv2 get-apis/get-routes, ssm describe-parameters(이름만), cloudfront list-distributions
- 명령 실측: `npx expo export --platform web`(실패 로그), `pytest`(83 passed), `npm run typecheck`(clean), `npm view react-native-web`, slopcheck 0.6.1
- 공식 문서 [CITED]: firebase.google.com/docs/auth/web/{redirect-best-practices, auth-state-persistence, anonymous-auth, google-signin}; docs.expo.dev/{guides/publishing-websites, router/reference/platform-specific-modules, versions/v54.0.0/sdk/{imagepicker,video,apple-authentication}}; react-native-google-signin.github.io/docs/setting-up/web; docs.aws.amazon.com/{cli/latest/reference/s3api/put-bucket-lifecycle-configuration.html, AmazonS3/latest/userguide/{notification-how-to-filtering,WebsiteHosting}.html}; aws.amazon.com/cloudfront/pricing/

### Secondary (MEDIUM confidence)
- 프로젝트 메모리(이 세션 밖 관측): demo-only-pod-bring-up-procedure, pod-link-can-collapse-silently, copied-doc-cannot-take-the-composited-path, lambda-code-update-without-sam-deploy, aws-keys-and-bucket, angle-bake-blocked-by-confidence, conf-05-gate-separates-nothing, human-videos-stay-out-of-manifest, display-string-is-not-a-join-key, firestore-spark-50k-read-cap
- 기획안 `.planning/quick/260925-pln-two-sided-plan/260925-pln-PLAN-two-sided.md` §4·§6·§7·§9·§10·§C-2·§C-6, 시장조사 노트북 §F

### Tertiary (LOW confidence)
- §H 의 web export 다음 차단 요인 예측, S3 website HTTP 전용, Google OAuth HTTPS 요구 — 전부 [ASSUMED], 측정 전

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 신규 패키지 0(후보 1 의 react-native-web 만 조건부)
- Architecture: HIGH(백엔드 분기점·writer·실패 4형 원시 함수는 전부 file:line 실측) / LOW(페이지 호스팅·웹 로그인은 측정 불가)
- Pitfalls: HIGH — 버킷 알림·스킵 로그·doc 순서·Pod 위장은 실측 또는 메모리 실측

**Research date:** 2026-09-26
**Valid until:** 2026-10-26 (AWS 버킷 설정·라이브 함수 상태는 손으로 바뀔 수 있어 착수 시 Q1·Q11 명령을 다시 돌릴 것)
