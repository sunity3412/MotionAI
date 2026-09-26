# Phase 38 SEED — 공급자 링크(실증 최소): 정은지가 올리면 사람 손 없이 기준이 된다

> 착수점(2026-09-26 밤 이후). 읽는 순서: CLAUDE.md → design.md → 이 문서 → 기획안 `.planning/quick/260925-pln-two-sided-plan/260925-pln-PLAN-two-sided.md` §7·§9·§C → `/gsd-plan-phase 38`.
> 기획 섹션(09-25~26)은 닫혔다. belle ○× 는 기획안 §A·§C 에 전부 있고 미결은 정산 비율 하나뿐.

## belle 원문 (이 phase 의 정의)
- 09-25: *"공급자 쪽의 주소(지금처럼의 베타앱)을 만들어야 하는데…"* / *"실증까지 공급자 링크가 나와도 좋을 것 같고"*
- 09-26: Q1 ○ *"한 앱 괜찮음"* · Q2 ○ *"공급자의 마이페이지도 간략하게나마 잘 구축 필요"* · *"공급자쪽 안 만들거야? 다음 섹션에 진행할 수 있도록 클리어하고 뭐라고 쓰면 되는지 결정하자"*
- 살아 있는 규칙: 실증까지 새 기능 금지(09-19)는 이 phase 에 belle 예외. 그래도 통과 기준은 하나 — **"정은지가 올린 영상이 사람 손 없이 채점 가능한 기준이 되나."** 그 밖의 표면(공급자 모드 화면·학원·정산)은 §10 단계 4.
- 인터럽트: 정은지 추가 영상이 오면 **시험 영상 2차**(`backend/scripts/sealed_test.py`)가 이 phase 보다 먼저.

## 이미 결정된 것 (다시 묻지 말 것)
| 결정 | 내용 | 출처 |
|---|---|---|
| Q1 | 같은 앱의 공급자 모드. 링크 = 그 모드의 첫 화면(임시물 아님). 폼 항목·동의문은 끝 그림 기준 | 기획안 §A·§7-1 |
| Q2 | 뒤쪽 자동화: ① `reference/` presigned PUT ② 각도 자동 추출 ④ 폼 메타. ③ clipRange 승격은 선택(손 입력 유지 가능) | §7-2 |
| Q2 추가 | 공급자 마이페이지 축소판 = **내 동작(+올리기) + 내 코드** 두 카드 | §7-4 |
| 폼 선언 4 | 동작 이름(기술 사전에서 선택, 새 이름 허용) · 스플릿 동작인가 · 유지 구간이 있는가 · 서 있는 자세에서 시작했는가 | §7-2 |
| 실패 4형 | 사람 미검출 · 여러 명 · 서 있는 시작 없음 · 저신뢰 — 각각 문구 + 재촬영 안내 | §4 |
| 재현성 | 등록 직후 본인 영상을 자기 기준으로 재서 "N점" 한 줄. 100 근처가 아니면 재촬영 권고 | §7-3·§B-3-2 |
| 동의 | 초상·성명(필수) · 이용 허락(필수) · 무음 확인(필수) · 학습 사용(선택, 기본 꺼짐) · 철회 고지 | §6 |
| 강사 코드 | 공급자 id 기반 짧은 문자(예 `EUNJI`). 링크 페이지에 표시·복사. 수요자 입력 자리는 마이 탭 한 줄(이 phase 는 표시만, 입력·귀속은 다음) | §C-2 |
| 돈 | 실증 = 무료. 크레딧 숫자만, 결제 없음 | §C-6 |
| 정확도 | 새 기술 key 는 기본 경로(reference_relative + Gemini 지목 + 못 잰 부위)로만 돈다. 얼마나 맞는지는 시험 영상으로만 | §7-3·§9-4 |

## 관측 — 오늘 모습 (09-26 파일 대조, 전부 [확인])
- 기준 doc `reference/{motionId}`, 앱 읽기 전용(`firestore.rules`). 필수 `name·athleteName·level`(`referenceMotions.ts:72-78`).
- presigned PUT 은 `uploads/*` 만(`template.yaml:194`). `parse_upload_key` 정규식 `uploads/{uid}/{id}.(mp4|mov)`(`s3keys.py:18`) → `reference/` 키는 파이프라인 입구(`pipeline/app.py:10309`)를 못 지난다.
- 파이프라인 `_resolve_is_reference`(`pipeline/app.py:417-437`): key 접두사 `reference/` 또는 doc `mode == "mode1_register"` → True. 쓰임 = scene 플래그·G4 합성 스킵뿐. **기준 각도를 쓰는 코드 없음.**
- 각도 추출은 Pod 손 스크립트 `backend/scripts/extract_reference_angles.py`(S3 `reference/{id}.mp4` → `--out json`) → `app/scripts/seed-reference-motions.mjs --angles`(손으로 쓴 MOTIONS 11개, clipRange·checkpoints 손 입력).
- `POST /reference/auto-register`(`reference-auto-register/app.py`, belle uid 화이트리스트): Gemini A → `geminiA·geminiAUpdatedAt(+isActive)` 만 씀(`firestore_admin.py:2368-2430`). 백필 writer 둘 있음: `update_reference_body_data`(2173) · `update_reference_downstream_data`(2272) — angles 는 안 쓴다.
- 새 기술 key 기본값: 스플릿 집합 `{"ref-power-spin"}`(`technique.py:43`) · criteria yaml 10 · `REGISTERED_MOTIONS` 10 · 문구집 67 · ipsf map 11 · 접점 5 · 썸네일 11 하드코딩(`app/src/constants/motionThumbs.ts`). mode1 yaml 키 = Gemini canonical, referenceMotionId 는 힌트(`gemini_technique_recognizer.py:325-355`).
- 인증: 익명 + Google + Apple(`socialAuth.ts`). 웹에서 앱 경로를 쓰려면 Firebase 웹 config(`EXPO_PUBLIC_FIREBASE_*`)로 같은 프로젝트 로그인 가능(미검증).
- Pod: 없으면 각도 추출 불가. 기동은 손 절차 5분 [기억 demo-only].

## 만들 것 (순서 제안 — 뒤쪽부터, 화면은 마지막)
1. **업로드 입구** — `POST /reference/upload-url`(또는 upload-url 에 `kind=reference`): 공급자 uid 화이트리스트(`BELLE_UID` → `SUPPLIER_UIDS` 확장), `reference/{supplierId}/{motionId}.mp4` presigned PUT, doc 선작성(`status: registering`, 폼 메타). S3 알림·SQS 가 `reference/` 접두사도 받게(버킷 알림은 template 밖 — 실측 필요).
2. **각도 자동 추출** — 파이프라인에 `register_reference` 경로: 다운로드 → RTMW → angles(flat) 를 `reference/{id}` 에 쓰는 admin 함수 신설(`update_reference_*` 패턴 mirror, ADD-only merge, 기존 11개 무접촉). Gemini A 는 지금 auto-register 그대로 붙이거나 뒤로.
3. **실패 4형** — 사람 미검출(기존 `no_human`) · 여러 명(검출 수) · 서 있는 시작 없음(높이 자 바닥 규칙 [기억 nnt §3]) · 저신뢰(부위 목록). doc `status: failed + reason` → 페이지 문구.
4. **자기 재현성** — 등록 완료 뒤 같은 영상을 `mode1` 로 자기 기준에 대해 한 번 분석 → `selfScore` 한 줄. (fixture 12편이 이미 이 경로)
5. **페이지** — 폰 브라우저. 권장 = **Expo Router 의 공급자 라우트를 web export** 해 S3+CloudFront 에 정적 배포(같은 코드베이스 = Q1 "같은 앱"의 문자 그대로; Firebase 웹 로그인 동일 프로젝트). 대안 = 단일 HTML. design.md 규칙(#FF4B33·Pretendard·라이트) 그대로. 카드 2: 내 동작(+올리기 폼) · 내 코드.
6. **앱 picker** 는 무접촉 — `name·athleteName·level·isActive` 만 맞으면 뜬다. 썸네일은 없으면 기본 이미지(하드코딩 11개는 그대로).

## 열린 질문 (discuss/plan 에서 정할 것)
1. 페이지 호스팅: Expo web export(권장) vs 단일 HTML — 빌드·배포 경로가 다르다.
2. 공급자 인증: 정은지 uid 화이트리스트(실증) vs 역할 클레임(끝 그림). 실증은 화이트리스트로.
3. `reference/` 키 체계: `reference/{motionId}.mp4`(지금) 유지 vs `reference/{supplierId}/{techniqueKey}/{v}.mp4`(§7-2 분리 대비). 기존 11개는 그대로 두고 새 등록만 새 체계? 조인은 불변 id.
4. Pod 없을 때: 등록 대기 상태(`queued`) 표시 + Pod 기동 시 처리. 온디맨드 자동 기동은 별도.
5. 새 동작의 Gemini 분류 "unregistered" 경로 — 실증에서 정은지 새 동작이 등록 목록 10개 밖이면 신전 기준 0. 받아들이고 시험 영상으로 잰다(§7-3).

## belle 이 다음 세션 첫 줄에 칠 것
`/gsd-plan-phase 38` — 계획이 나오면 belle 이 보고 `/gsd-execute-phase 38`. Pod 작업 전 push 먼저(규칙).
