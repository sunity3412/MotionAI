# Phase 38: 공급자 링크 — 실증 최소 (supplier-link) - Context

**Gathered:** 2026-09-26
**Status:** Ready for planning
**Source:** SEED Express Path — `.planning/phases/38-supplier-link/38-SEED.md`(belle ○× 09-25~26 전부 반영) + 기획안 `.planning/quick/260925-pln-two-sided-plan/260925-pln-PLAN-two-sided.md` §4·§6·§7·§9·§10·§C. discuss-phase 는 돌리지 않았다 — SEED 의 "이미 결정된 것(다시 묻지 말 것)" 표가 그 자리다.

<domain>
## Phase Boundary

정은지가 폰 브라우저 링크 한 장으로 동작 영상을 올리면 **사람 손 없이** 채점 가능한 기준(`reference/{id}` doc + angles)이 되고 앱 picker 에 뜬다. 링크는 임시물이 아니라 같은 앱의 공급자 모드 **첫 화면**이다. CLAUDE.md 파일럿 Step 2 그 자체.

통과 기준은 하나 — **"정은지가 올린 영상이 사람 손 없이 채점 가능한 기준이 되나."** 그 밖의 표면(앱 안 공급자 모드 · 학원 · 정산)은 기획안 §10 단계 4(실증 뒤).

ROADMAP Success: ① belle 이 아닌 사람이 링크만으로 새 동작 1개를 올려 앱 picker 에 뜨고 mode1 이 RuntimeError 없이 돈다 ② 실패 4형이 각각 문구로 나온다(합성 입력으로 강제) ③ 자기 재현성 = 정은지 본인 영상 100 근처 ④ 기존 기준 11개·저장 분석 무접촉(불변 id 조인).

살아 있는 규칙: "실증까지 새 기능 금지"(belle 09-19)의 belle 예외가 이 phase 다. 인터럽트: 정은지 추가 영상이 오면 **시험 영상 2차**(`backend/scripts/sealed_test.py`)가 이 phase 보다 먼저. Pod 작업 전 push 먼저.

</domain>

<decisions>
## Implementation Decisions

ROADMAP Requirements 1~8 을 이 문서에서는 `REQ-38-1` ~ `REQ-38-8` 로 부른다. 플랜 frontmatter `requirements` 에 이 라벨을 쓴다.

### 제품 형태 (belle Q1·Q2 ○)
- **D-01:** 같은 앱의 공급자 모드. 링크 = 그 모드의 첫 화면(임시물 아님). 폰 브라우저에서 연다. 폼 항목·동의문은 끝 그림 기준으로 지금 쓴다. (기획안 §7-1)
- **D-02:** 링크 페이지 = 공급자 마이페이지 축소판 = **내 동작(+올리기 폼) + 내 코드** 두 카드. 앱 안 공급자 모드 화면은 범위 밖. (§7-4)
- **D-03:** 실증 공급자 인증 = uid 화이트리스트(`BELLE_UID` → `SUPPLIER_UIDS` 확장, 정은지 uid 포함). 역할 클레임은 끝 그림. 로그인은 같은 Firebase 프로젝트(익명·Google·Apple 중 웹에서 되는 것 — 연구로 확정). (SEED 열린 질문 2)

### 뒤쪽 자동화 — REQ-38-1 · REQ-38-2 · REQ-38-3
- **D-04:** `reference/` 용 presigned PUT 입구(`POST /reference/upload-url` 또는 upload-url 에 `kind=reference`). 발급 시 `reference/{id}` doc 선작성(`status: registering`, 폼 메타). 지금 presigned PUT 은 `uploads/*` 만(`template.yaml:194`)이고 `parse_upload_key` 가 `reference/` 키를 거부한다(`s3keys.py:18`). (REQ-38-1)
- **D-05:** 업로드 트리거 → 파이프라인 `register_reference` 경로: 다운로드 → RTMW → angles(flat: `angles·anglesJointKeys·anglesFrames·anglesUpdatedAt`) 를 `reference/{id}` 에 쓰는 admin 함수 신설. `update_reference_body_data`(`firestore_admin.py:2173`)·`update_reference_downstream_data`(2272) 패턴 mirror, **ADD-only merge, 기존 11개 무접촉**. angles 없으면 mode1 `RuntimeError`(`pipeline/app.py:8905`) — 그것을 없애는 것이 이 칸의 목적. S3 알림·SQS 가 `reference/` 접두사도 받아야 한다(버킷 알림은 template 밖 — 실측 필요). (REQ-38-2)
- **D-06:** clipRange 승격은 **선택** — 손 입력 유지 가능. Gemini A(`clip_range` → 상단 `clipRange`)는 기존 `POST /reference/auto-register` 그대로 붙이거나 뒤로 미룬다. clipRange 없을 때 런타임은 DTW 폴백(`pipeline/app.py:9026`). (§7-2 ③)
- **D-07:** 폼 메타 → doc: `name·athleteName·level`(없으면 picker 가 버린다 `referenceMotions.ts:72-78`) + 선언 4개: 동작 이름(기술 사전에서 선택, 새 이름 허용) · 스플릿 동작인가 · 유지 구간이 있는가 · 서 있는 자세에서 시작했는가. 선언은 지금 코드에 박힌 값(`SPLIT_LINE_ELEMENTS` `technique.py:43`, criteria yaml `hold_moment`, 높이 자 바닥 전제)을 **doc 필드로 받아 두는 것**까지가 범위. 사전/규칙 분리 코드는 범위 밖. (REQ-38-3, §7-2)
- **D-08:** 동의(폼 체크, 문안 §6 그대로): 초상·성명 사용(필수) · 영상 이용 허락 — 분석 기준·프레임 추출·표시·썸네일(필수) · 무음 영상 확인(필수) · 학습 사용(선택, **기본 꺼짐**) · 철회 절차 한 줄 + 철회 시 수요자 기록 스냅샷 유지 고지. 동의 결과는 doc 에 남긴다. (REQ-38-3)

### 등록 실패 4형 · 자기 재현성 — REQ-38-4
- **D-09:** 실패 4형 각각 문구 + 재촬영 안내: 사람 미검출(기존 `no_human` 재사용) · 여러 명(YOLOX 검출 수) · 서 있는 시작 없음(높이 자 바닥 규칙, 09-25 nnt §3) · 저신뢰(못 읽은 부위 목록). doc `status: failed` + `reason` → 페이지 문구. 각 형은 **합성 입력으로 강제 재현**할 수 있어야 한다(Success ②).
- **D-10:** 자기 재현성: 등록 완료 뒤 같은 영상을 `mode1` 로 자기 기준에 대해 1회 분석 → doc 에 `selfScore` 한 줄. 100 근처가 아니면 재촬영 권고 문구. 정은지 fixture 12편이 이미 이 경로다. (§7-3·§B-3-2)
- **D-11:** 새 기술 key 는 **기본 경로**(reference_relative 기하 + Gemini 지목 + "못 잰 부위 한 줄")로만 돈다. 벌림 감점·신전 기준·문구집·접점·썸네일 없음은 받아들인다. 얼마나 맞는지는 **시험 영상으로만** 잰다. 기술 사전 채우기는 플랫폼 운영·실증 뒤. (§7-3·§9-4)

### 강사 코드 · 돈 — REQ-38-5
- **D-12:** 강사 코드 = 공급자 id 기반 짧은 문자(예 `EUNJI`). 링크 페이지 "내 코드" 카드에 표시·복사. 수요자 입력 자리 = 마이 탭 계정 카드 아래 한 줄 — **이 phase 는 표시만**, 입력·귀속·크레딧 지급은 다음(§C-2 (a), §10 단계 2 이후 belle 승인).
- **D-13:** 실증 = 돈을 받지 않는다. 크레딧은 숫자만(또는 안 보임), 결제 SDK 없음. (§C-6)

### 업로드 기준 · 문구 · 보관 · 가이드 — REQ-38-6 · REQ-38-7 · REQ-38-8 (belle 09-26 ○)
- **D-14:** 길이 하한·상한 즉시 검사 — 수요자 3~90초(앱 `analyze.tsx` validate 에 duration 추가, IA 3-3 `AC-VID-003-1L` 문구 재사용) · 공급자 5~30초(콤보 60초, 링크 페이지). 형식 mp4/mov · 100MB 는 그대로. (REQ-38-6)
- **D-15:** 문구 정정 — 앱 팁 "측면 45°, 2~3m"(`loading.tsx:519,546`) · 실패 문구 "정면으로"(`loading.tsx:490`) · `docs/ia.md` §3-2 "측면 45° / 2~3m" · `docs/reference-capture-guide.md` §2 "정면 우선" → 전부 **"기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)"**. (REQ-38-6)
- **D-16:** 촬영 기준 = **정은지 기준 영상의 조건**: 세로 · 고정(삼각대/거치) · 허리~가슴 높이 수평 · 폴 전체(천장~바닥)+전신이 동작 내내 안에(약 4~5m) · 한 사람 · 밝은 실내(역광 실루엣 금지) · 무음 · 서 있는 자세에서 시작 · 동작 1개 = 영상 1개. **각도 고정값(정면/45°)은 두지 않는다**(시작 방향은 동작마다 다르다 — 09-26 실물). 고스트 오버레이·자세 인식 자동 시작은 끝 그림 선택 항목(범위 밖).
- **D-17:** 수요자 원본 영상 보관 **영구** — `uploads/` 30일 만료 수명주기(버킷 설정, template 밖 `template.yaml:135`)를 해제. `s3keys.py:3` 주석 정정. 기록 화면 원본 재생이 30일 뒤 사라지지 않는다. 동의분 연습 영상 접두사도 영구. 비용 30MB × 1,000편 ≈ 30GB ≈ $0.7/월. (REQ-38-7)
- **D-18:** 공급자 가이드 — 링크 페이지 안 "촬영 전 체크 5" + 상세 가이드 화면 + 문서 정본 `docs/supplier-guide.md`(쉬운 말, 공급자용). 내용 7: ① 촬영 조건 = 정은지 영상 조건(예시 = 정은지 프레임) ② 동작 1개 = 영상 1개, 5~30초, 서 있는 시작, 무음 ③ 폼 선언 4개를 왜 묻는지 한 줄씩 ④ 등록 뒤 보게 되는 것(재현성 점수, 실패 4형과 대처) ⑤ 권리·동의(공급자 소유, 이용 허락, 철회) ⑥ 내 코드를 수강생에게 알려주는 법 ⑦ 자주 틀리는 것(너무 가까움 2~3m · 손 촬영 · 뒤에 사람 · 역광 · 음악 · 여러 동작 이어 찍기). `docs/reference-capture-guide.md` §6 운영자 절차는 그대로 둔다. design.md 톤(라이트 · #FF4B33 · Pretendard). (REQ-38-8)

### 무접촉 · 조인 · Pod
- **D-19:** 기존 기준 11개 · 저장 분석 무접촉. 조인은 불변 id(표시 문자열을 조인 키로 쓰지 않는다). 앱 picker 는 무접촉 — `name·athleteName·level·isActive` 만 맞으면 뜬다. 썸네일은 없으면 기본 이미지(하드코딩 11개 `motionThumbs.ts` 그대로).
- **D-20:** Pod 없을 때 등록 대기 상태(`queued`) 표시 + Pod 기동 시 처리. 온디맨드 자동 기동은 범위 밖(실사용 전제일 뿐). Pod 기동은 손 절차 5분(메모리 demo-only).
- **D-21:** 사람 영상은 `manifest.json` 에 넣지 않는다 — 등록 = `intake_clips.py` → clips.jsonl(메모리 human-videos-stay-out-of-manifest). 공급자 영상도 같은 규칙.

### Claude's Discretion
- **페이지 호스팅** — SEED 권장은 Expo Router 공급자 라우트 **web export** → S3(+CloudFront) 정적 배포(같은 코드베이스 = Q1 "같은 앱"의 문자 그대로). 대안 = 단일 HTML. **권장은 재고 나서**: 연구에서 이 앱(expo-video · react-native-svg · firebase auth 웹 · expo-image-picker 웹)의 web export 가 실제로 빌드되는지, 로그인이 폰 브라우저에서 되는지 실측한 뒤 플래너가 정한다. 못 쟀으면 "권장 없음, 이걸 재야 답이 나온다"로 적는다.
- **`reference/` 키 체계** — 지금 `reference/{motionId}.mp4` 유지 vs `reference/{supplierId}/{techniqueKey}/{v}.mp4`(§7-2 분리 대비). 기존 11개는 그대로 두고 새 등록만 새 체계 가능. 조인은 불변 id.
- **Lambda 배치** — 새 함수(`reference-upload-url`) vs 기존 `upload-url`/`reference-auto-register` 확장. doc 필드명. SQS 라우팅(같은 큐 + 키 접두사 분기 vs 별도 큐).
- **테스트 구성** — 실패 4형 합성 입력의 형태(pytest, 순수 함수 단위), 웹 페이지 typecheck 게이트.
- **Gemini "unregistered" 경로** — 새 동작이 등록 목록 10개 밖이면 신전 기준 0. 받아들인다(§7-3). 설계 여지 없음, 문서에만 남긴다.

</decisions>

<specifics>
## Specific Ideas

- belle 09-25: *"공급자 쪽의 주소(지금처럼의 베타앱)을 만들어야 하는데…"* / *"실증까지 공급자 링크가 나와도 좋을 것 같고"*
- belle 09-26: Q1 ○ *"한 앱 괜찮음"* · Q2 ○ *"공급자의 마이페이지도 간략하게나마 잘 구축 필요"* · *"공급자쪽 안 만들거야? 다음 섹션에 진행할 수 있도록 클리어하고 뭐라고 쓰면 되는지 결정하자"*
- belle 09-26 촬영: *"현재 정은지 영상 정도의 각도나 이정도면 괜찮지? 유튜브 보면 알겠지만 동작의 기교를 빼고 보면 각도와 거리가 거의 비슷한게 폴스포츠라 좀 괜찮을거야."*
- belle 09-26 보관·가이드: *"둘 다 오케이, 보관은 영구로 가자. 공급자 가이드도 잘 만들어주도록"*
- 실물(09-26, S3 기준 영상 프레임): power-spin 1080x1920 10.5s · climb 2160x3840 7.9s · kip-up 1080x1920 7.8s, 전부 30fps 세로. 카메라 고정, 허리~가슴 높이, 폴 전체+전신, 거리 약 4~5m, 단색 스튜디오, 한 사람. 시작 방향은 동작마다 다르다.
- 벤치(기획안 §B·§F-7): Skillest·Onform "camera overlay" · 골프존 자동 시작 · 골프 온라인 레슨 가이드(삼각대·높이·조명·배경) · UNFORCE "테스트 촬영 먼저" · Kling·Ringle 추천 코드. 폴댄스 7곳엔 강사용 가이드 소스 없음 → 빈 자리.
- 보고 규칙(CLAUDE.md §7 ★): 숫자·상수는 소비처까지 따라간 뒤 보고. `[확인]`/`[미확인]` 표식. 관측과 진단을 다른 절에.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 착수점 · 기획
- `.planning/phases/38-supplier-link/38-SEED.md` — 이 phase 의 정의 · 결정 표 · 09-26 코드 관측 · 만들 것 순서 · 촬영 기준 표 · 추가 요구 6~9 · 열린 질문
- `.planning/quick/260925-pln-two-sided-plan/260925-pln-PLAN-two-sided.md` §4(공급자 여정·실패 4형 문구) · §6(동의 문안) · §7(공급자 도구: 7-1 Q1 · 7-2 뒤쪽 4칸+선언 4 · 7-3 새 동작 기본 경로 · 7-4 마이페이지 카드) · §9(기술 관측 파일:줄 전부) · §10(단계 배치) · §C-2(강사 코드) · §C-6(실증 무료)
- `.planning/ROADMAP.md` "### Phase 38" — Goal · Requirements 1~8 · Success ①~④ · Depends on · Not in scope
- `.planning/quick/260925-nnt-three-fixes/260925-nnt-HANDOFF.md` :20 · :35 · :70-72 — 높이 자 바닥 규칙(서 있는 프레임이 없으면 None: 창 낮은발 10% 분위 < −0.10 이면 바닥 기준 거짓). 서 있는 시작 전제의 출처

### 디자인 · 문구
- `design.md` §0(미설계 화면 자율 설계 원칙) · §5(컬러 #FF4B33 · 버튼 · 카드) — 페이지·가이드 화면 규칙. 라이트 전용, Pretendard
- `docs/ia.md` §3-2(촬영 가이드 문구 — 정정 대상 "측면 45° / 2~3m") · §3-3(`AC-VID-003-1L` 3초 미만 문구 재사용)
- `docs/reference-capture-guide.md` — §2 "정면 우선"(정정 대상) · §6 운영자 절차(그대로 둔다). 새 `docs/supplier-guide.md` 의 반면교사
- `app/src/app/analysis/loading.tsx` :490 · :519 · :546 — 정정할 문구 세 자리

### 백엔드 계약 · 인프라
- `docs/contract.md` — API 계약(`playback-url` :124 · `reference/{id}.mp4` :296)
- `backend/template.yaml` — :20-21 버킷 알림은 template 밖 · :130-135 uploads/ 30일 lifecycle 주석 · :194 presigned PUT `uploads/*` 만 · :216-241 reference/* GetObject · :255-299 `/reference/auto-register`
- `backend/shared/python/sunity_shared/s3keys.py` — :3 주석(정정 대상) · :18 `_UPLOAD_KEY_RE`
- `backend/shared/python/sunity_shared/validation.py` · `models.py`(:694 100MB · :833-836 reference 컬렉션) — 계약 3벌 동시 수정 규칙(`app/src/types/analysis.ts` · `docs/contract.md`)
- `backend/functions/upload-url/app.py` — presigned PUT 발급 패턴
- `backend/functions/reference-auto-register/app.py` — belle uid 화이트리스트(:86-98) · Gemini A 호출
- `backend/shared/python/sunity_shared/firestore_admin.py` — :2173 `update_reference_body_data` · :2272 `update_reference_downstream_data` · :2368-2430 `set_reference_motion_with_gemini`
- `backend/functions/pipeline/app.py` — :417-437 `_resolve_is_reference` · :2795-2813 `_reference_exec_window` · :8670-8673 · :8875-8880 motion_hint · :8905 angles 없을 때 RuntimeError · :9026 DTW 폴백 · :10309 파이프라인 입구
- `backend/runpod_inference/server.py` — Pod `/analyze` 입구(같은 `_process`)
- `backend/scripts/extract_reference_angles.py` — 각도 추출 손 스크립트(자동화의 원본)
- `app/scripts/seed-reference-motions.mjs` — MOTIONS 11개 손 입력(clipRange·checkpoints), angles merge 패턴
- `firestore.rules` — reference 읽기 전용 블록
- `backend/shared/python/sunity_shared/analysis/technique.py` :43 `SPLIT_LINE_ELEMENTS` · `gemini_technique_recognizer.py` :325-355 · :434-446 · `gemini_motion_classifier.py` :26-41 · `frame_extractor.py` :4-5(640px·9fps)
- `backend/scripts/sealed_test.py` — 시험 영상 2차(인터럽트) · `backend/scripts/intake_clips.py` — 사람 영상 등록 경로

### 앱
- `app/src/lib/referenceMotions.ts` :72-78 — picker 필수 필드 `normalize()`
- `app/src/app/(tabs)/analyze.tsx` :46-47 · :215-235 — validate(형식·100MB·저화질 경고) — duration 검사 추가 자리
- `app/src/app/(tabs)/profile.tsx` — 마이 탭(강사 코드 표시 한 줄 자리)
- `app/src/lib/socialAuth.ts` :95 · :153 — Google·Apple 로그인 · `app/src/lib/firebase.ts` — 웹 config
- `app/src/constants/motionThumbs.ts` — 썸네일 11개 하드코딩(기본 이미지 폴백 자리)
- `app/CLAUDE.md` — 앱 규칙(테마 토큰 하드코딩 금지)

### 메모리(절대 경로, 이 세션 밖의 관측)
- `/Users/kimtaesung/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/demo-only-pod-bring-up-procedure.md` — Pod 기동 5분 절차 · E2E 순서
- `.../memory/human-videos-stay-out-of-manifest.md` — 사람 영상 manifest 금지
- `.../memory/display-string-is-not-a-join-key.md` — 조인은 불변 id
- `.../memory/until-pilot-analysis-only.md` — 실증까지 분석만(이 phase 는 belle 예외)
- `.../memory/gsd-pod-work-push-first.md` — Pod 작업 전 push
- `.../memory/firestore-spark-50k-read-cap-is-a-live-risk.md` — Firestore 읽기 5만/일 하드 캡
- `.../memory/pod-link-can-collapse-silently.md` — Pod↔S3 가속 전송(`S3_USE_ACCELERATE=1`)
- `.../memory/copied-doc-cannot-take-the-composited-path.md` — doc 복사 함정

</canonical_refs>

<code_context>
## Existing Code Insights (SEED 09-26 파일 대조, 전부 [확인])

### Reusable Assets
- `upload-url` Lambda 의 presigned PUT 발급 + Firebase 토큰 인증(`sunity_shared.auth`) — `reference/` 입구의 원형
- `reference-auto-register` Lambda 의 uid 화이트리스트 + `reference/*` 읽기 권한 — 공급자 인증의 원형
- `firestore_admin.update_reference_*` 두 writer — angles writer 의 mirror 대상(ADD-only merge)
- `extract_reference_angles.py` — S3 `reference/{id}.mp4` → angles json. 파이프라인 안으로 옮기는 원본
- `pipeline._process` — Lambda·Pod 공용 단일 경로("분기 0, 코드 1벌"). 등록 경로도 여기 붙인다
- 실패 문구·`no_human` 에러 코드(`models.py:808-814`) — 실패 4형 중 1형 재사용
- 정은지 fixture 12편의 mode1 자기 비교 경로 — 자기 재현성의 원형

### Established Patterns
- 계약 3벌 동시 수정: `app/src/types/analysis.ts` ↔ `models.py`/`validation.py` ↔ `docs/contract.md`
- Firestore nested array 금지 → angles 는 flat(`angles·anglesJointKeys·anglesFrames`)
- Lambda 핸들러는 얇게(인증 → 검증 → 부작용 1 → 응답), 순수 함수는 boto3 무관 → pytest
- `sam build --use-container` · 시크릿은 SSM Parameter Store · `.env` 하드코딩 금지
- 앱: 테마 토큰만(하드코딩 색 금지) · 한국어 문구 · 이모지 금지 · `npm run typecheck` 가 유일한 정적 게이트 · UI 변경은 시뮬 확인 후

### Integration Points
- S3 버킷 알림(template 밖) → SQS `AnalysisQueue` → pipeline Lambda → RunPod `/analyze`. `reference/` 접두사가 알림에 포함되는지 실측 필요
- `uploads/` lifecycle 30일(버킷 설정, template 밖) — 해제 대상
- 앱 picker(`analysis/reference`)는 `reference` 컬렉션 `isActive` + 필수 3필드만 본다 → 새 doc 이 그 조건을 채우면 무접촉으로 뜬다
- 마이 탭 계정 카드 — 강사 코드 표시 한 줄 자리

</code_context>

<deferred>
## Deferred Ideas

- 앱 안 공급자 모드 화면(카드 5: 내 수강생 · 크레딧/정산 · 권리/동의) · 학원 콘솔 · 정산 비율 · 증명 1·3층 — §10 단계 4
- 기술 사전 / 기준 인스턴스 분리 코드(§7-2 D2) — 실증 뒤. 단 폼 "동작 이름"은 사전 선택형으로 미리
- 강사 코드 **입력·귀속·양쪽 크레딧 지급(2/2)** — 표시만 이번, 나머지는 belle 승인 뒤
- Pod 온디맨드 자동 기동("Pod 한 명령") — §10 단계 1, 이 phase 밖(실사용 전제)
- 고스트 오버레이 · 자세 인식 자동 시작 · 폴 검출(09-25 시도 실패) — 끝 그림 선택 항목
- 결제 SDK(RevenueCat) · 크레딧 원장 — 실증 뒤
- 홈 "내 공급자" 칸(NEW 배너 → 정은지 카드) — belle 이 실증 전에 하라고 할 때만
- Gemini thinking 실측 로그(usage_metadata) — 실증 첫 주
- 시험 영상 2차(`sealed_test.py`) — 이 phase 의 일이 아니라 **인터럽트**(정은지 영상 도착 즉시 먼저)

</deferred>

---

*Phase: 38-supplier-link*
*Context gathered: 2026-09-26 via SEED Express Path (38-SEED.md + 기획안 260925-pln)*
