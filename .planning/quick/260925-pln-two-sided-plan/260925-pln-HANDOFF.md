# 260925-pln HANDOFF — 양면 플랫폼 기획안 (2026-09-26 밤 섹션 종료 — 착수점은 이제 `.planning/phases/38-supplier-link/38-SEED.md`)

> 읽는 순서: CLAUDE.md → design.md → 이 문서 → `.planning/research/market-coaching-platforms-260925.md` §0 (판정 10줄만).
> ~~기획안은 아직 한 줄도 안 썼다.~~ **09-26: 기획안 정본 `260925-pln-PLAN-two-sided.md` 작성 + §B 벤치 매칭 + belle 판정 9건 반영(§A).** 4차: 원가 실측(§C-1) + 상품 구조 **초기 버전 확정**(§C-6, belle "실증까진 돈을 받을 순 없으니 초기 버전엔 이렇게"). 5·6차: ○× 전부 닫힘(무만료 · 모션팩 묶음 + 귀속 수강생 개방 · 추천 2/2 · holdout "시험 영상은 배우지 않는다"). **용어 확정: 시험 영상 / 연습 영상(구 봉인 시험지).** 다음 세션은 정은지 영상 대기(시험 영상 2차)와 §10 순서(코드는 belle 승인 뒤). 미결 = 정산 비율.
> 이전 착수점 `260925-nnt-HANDOFF.md` = 이력(봉인 시험지·세 칸 수리·관찰문 — 그쪽 "다시 하지 말 것"은 그대로 유효).

## ★ 기획의 기준 — belle 09-25 밤 마지막 지시 (최우선, 이 문서의 나머지를 이 기준으로 읽을 것)

belle 원문: *"실증까지는 아니다라는 기준, 물론 중요하지만 완성도 높은 앱. 그리고 그 미래를 만드는 생태계를 봐야함. 실증은 중간과정임을 잊지말라. 그래서 기획의 완성은 멀리 봐야할 것이고 그 안에서 실증의 기간동안 어떻게 할지 맞춰야하는 것이 중요하노라. 그 부분을 반드시 인계서에 기억하게 해야할 것이야."*

1. **기획의 완성 = 완성도 높은 앱 + 그 미래를 만드는 생태계**(수요자·공급자·학원·플랫폼이 서로를 키우는 구조). 끝 그림을 먼저 그린다.
2. **실증은 중간 과정이다.** "실증까지는 아니다"를 답으로 쓰지 말 것. 질문마다 답은 두 층 — **끝 그림에서의 답** → **그 안에서 실증 기간에 하는 것**. 아래 §3 초안은 이 순서로 다시 적었다.
3. (내 해석, belle 말 아님) 코드 규칙 "실증까지 분석만, 새 기능 금지"(belle 09-19)는 그대로다 — **문서는 멀리, 코드는 단계.** 두 규칙은 충돌하지 않는다: 기획안이 끝 그림을 정하고, 실증 기간의 코드는 그 끝 그림의 첫 단계만 만든다.

## 0. belle 발언 원문 (09-25 밤, 순서대로) — 관측, 정정 대상 아님
1. *"오케이 일단 영상은 받기로 했으니 기다리면 되는데... 그림 이제 우리가 기획할게 있어. … 1. 그런 사용자 여정 시나리오를 모든 경우의 수로 짜서 우리의 기획안에 넣어놓을 것. 2. … 수요자 앱과 공급자 앱, 그리고 공급자를 선택하는 기능등… 일단 공급자 쪽의 주소(지금처럼의 베타앱)을 만들어야 하는데..."*
2. *"공급자의 경우 무엇으로 증명할까?"* → 내 답: 3층(자격·경력 서류 / 본인 실행 영상 자체가 증명 = 분석기가 잰다 / 후기·추천) + 권리 동의. belle 반응 없음(승인 아님).
3. *"오케이 일단 우리와 비슷한 수요자, 공급자가 가르치는 것(꼭 모션이 아니더라도) 왠만하면 스포츠쪽으로 해외 스타트업 등을 Nlm 으로 충분히 조사도 해서 자료를 먼저 수집하자"*
4. *"그럼 스포츠가 아닌 산업에서도 찾아보라. 수요자 공급자 역할은 굉장히 많을테니까"*
5. *"그럼 이제 기획안 써봐. 실증까지 공급자 링크가 나와도 좋을 것 같고... 메인 화면을 어떻게 해야하려나.. https://www.onepeloton.com/ 이런걸로 따라야하나... 공급자 앱을 따로 만드는게 낫나? 공급자가 어떻게 업로드 하는 방안이 제일 효율적일까 등등 모두 고려하여 기획안을 작성하자"*
6. (인터럽트) *"인계서 작성하고 내일 진행하자... 인계서 작성전 한번더 검토하고 peloton 도 한번 조사해줘 쓸만한지. 공급자 앱을 따로 만드는게 나을런지, 공급자가 어떻게 업로드하는게 효율적인것인지... 꼭 공급자 앱이 필요한것인지 등등도 관건일 것 같네."*

## 1. 오늘 산출물 (관측)
- **시장조사 정본** `.planning/research/market-coaching-platforms-260925.md` — §0 판정 10줄, §A 한국·해외 표, §B 해외 영상 코칭 8 + 폴댄스 7, §C 비스포츠(언어·음악·과외·게임·창작자), §D 전문 기술 평가 + 가로지르기 패턴, §E Peloton.
- NotebookLM `21f482ad-2a03-4682-8871-73dc5a7dbbf5` — 소스 151(중복 약 20), 노트 "종합 1"~"종합 5". 읽기 페이지 https://claude.ai/artifact/VNqep3D5iKdvft4srB7QHS (v3).
- **검토(belle "한번더 검토")**: §0 핵심 주장 10건을 소스 원문 문장으로 대조 → 10/10 [확인]. 표의 나머지 숫자는 미대조.
- **Peloton 판정(belle "쓸만한지")**: 쓸 만한 것 = 홈 첫 칸 "Your Instructors"(강사 먼저) + 강사 브랜드화. 아닌 것 = 하드웨어·대규모 강사 로스터·1:N 방송·클래스 카탈로그. Peloton IQ 는 카메라 자세 피드백이 아니다(소스 없음). 숫자: 월 이탈 1.2%, App One $12.99 / App+ $28.99 / Strength+ $9.99, 강사 클래스당 $500~750(2차 소스 FourWeekMBA — 미확인).
- 커밋: 3d36ea80 · 048d1141 · eb0f29ad · 880d1f7c · (이 인계서). 전부 push.

## 2. 시장조사에서 기획안으로 가져갈 것 (10줄은 정본 §0, 여기는 결론만)
- 공급자 개인의 실행 하나를 기준으로 AI 가 비교하는 서비스 = **0**(스포츠·비스포츠 약 60곳). AI 비교 = 일반 기준, 개인 기준 = 사람이 본다(40:60). **우리 자리는 비어 있다** — 그 자리가 비어 있는 이유는 "개인 기준을 AI 가 재는 것이 어렵기 때문"일 수 있다(진단, 미확인).
- 가장 가까운 셋: Skillest(양면 마켓, 코치 월 $59 + 온라인 13%) · 골프존 GDR AI(프로 영상 나란히 + 50자세, 무료) · Speechling(성우 시연 ↔ 학생 녹음 나란히, 사람 코치 24h). 공급자 앱 방향 = Trainera(코치 100%).
- 수수료 최빈 10~20% · 공급자 증명 4종(자격/심사/후기/무검증) · 강사가 AI 코치를 거부하는 이유 5(맥락 무시·저차원 지표·약점 위주·블랙박스·감정) · 정확도 불만 4형 · 권리 동의 4규정.

## 3. 관건 3문제 — 지금 생각 (권장 **초안**, 진단 = 내일 §4 대조 뒤 재검증)

**Q1 꼭 공급자 앱이 필요한가?**
- 사실: 시장에서 코치 전용 앱을 가진 곳(Onform·CoachNow·Trainera)은 코치가 월정액을 내는 도구, 마켓(Skillest)은 코치도 같은 앱, 폴댄스 7곳은 공급자 도구가 아예 없다(운영자가 올린다). 실증 공급자 = 정은지 1명(+ 학원 강사 몇).
- **끝 그림**: 공급자에게 **자기 도구가 있다** — 동작 등록·재촬영·교체, 자기 학생 현황(누가 어떤 동작에서 막히나), 정산, 권리 관리(동의·철회), 증명 갱신. 이것이 별도 앱인지 같은 앱의 '공급자 모드'인지는 끝 그림에서 **공급자 수와 기능 폭**으로 정한다 — 공급자가 수십 명이고 학생 현황·정산까지 있으면 별도 앱(Onform·Trainera 형), 그 전까지는 같은 앱의 모드(Skillest 형)가 유력. 초안 = 같은 앱의 모드에서 시작해 필요해지면 분리.
- **실증 기간**: 링크 한 장(폰 브라우저: 동작 선택·촬영/파일·동의·업로드). 이 링크는 끝 그림 공급자 도구의 **첫 화면**이지 임시물이 아니다 — 폼 항목과 동의문은 끝 그림 기준으로 만든다.

**Q2 공급자 업로드, 제일 효율적인 방법?**
- 후보 4: (a) 우리가 대신(지금 방식, §4) (b) 링크 페이지 (c) 앱 안 '기준 등록' 모드 (d) 학원 운영자 콘솔.
- **끝 그림**: 공급자가 스스로 동작을 올리면 **사람 손 없이 채점 가능한 기준**이 된다. §4 를 보면 이것은 화면 문제가 아니라 뒤쪽 자동화다 — 오늘은 mp4 를 S3 에 손으로 넣고, Pod 스크립트를 손으로 돌려 angles 를 뽑고, seed 스크립트의 손으로 쓴 목록(name·level·**clipRange 까지 손으로**)으로 doc 을 쓴다. 자동 등록 Lambda 는 있지만 angles 를 안 만들고 name/level 도 안 써서 **채점 불가 + 앱에 안 보임**. 끝 그림의 네 칸: ① reference/ 용 presigned PUT ② 업로드 트리거 → Pod 각도 추출 자동 ③ Gemini A 의 clip_range 를 상단 clipRange 로 승격 ④ name/athleteName/level 을 폼에서. 그리고 폼이 **코드에 박힌 선언을 대신 받는다**: 동작 이름 · 스플릿 동작인가(`SPLIT_LINE_ELEMENTS` 대체) · 유지 구간이 있는가 · 서 있는 자세에서 시작했는가(높이 자 바닥). 새 동작은 criteria yaml·phrasebook·contact_points·thumbs 가 없으니 기본 경로(reference_relative + Gemini 지목 + 못 잰 부위 한 줄)로만 돈다 — 그게 얼마나 맞는지는 **봉인 시험지로만** 안다. (b)+(c) 는 같은 뒤쪽을 쓰는 두 입구, (d) 는 학원이 공급자를 대신 등록하는 생태계 입구 — 끝 그림에는 셋 다 있다.
- **실증 기간**: (b) 링크 + 네 칸 중 최소(①②④; ③은 clipRange 손 입력 유지 가능). 정은지 1명이 올린 영상이 자동으로 기준이 되는 것 = CLAUDE.md 파일럿 Step 2 그대로.

**Q3 메인 화면 — Peloton 식?**
- **끝 그림**: Peloton 에서 **"강사 먼저" 한 칸**을 가져온다. 홈 = [내 공급자 카드 + 그 공급자의 동작 목록] → [영상 올리기 큰 버튼] → [최근 분석·성장]. 공급자가 여럿이면 "내 공급자" 가 목록·검색·학원 코드가 된다(Skillest 형). 클래스 카탈로그·라이브·소셜 루프·챌린지는 우리 것이 아니다(Peloton 판정 §1).
- **실증 기간**: 지금 홈(§4 B2) 유지. 바뀔 자리는 "NEW 동작 배너 + 오늘 도전 3개" → "내 공급자(정은지) + 동작 5개" 하나뿐이고, 그것도 belle 이 실증 전에 하라고 할 때만(분석 아님).

**belle 결정 필요**: Q1~Q3 초안 승인/기각 · `eval_split_check.py --mark-holdout`(정은지 실수 fixtures 6편 학습 제외) · 기획안을 어디에 쓸지(리포 md 정본 + Claude Docs 검토용 / 페이지).

## 4. 기술 관측 — 기준 등록 경로 오늘 모습 [09-26 파일 대조 완료 — 아래 줄 전부 [확인], 정정·보강은 첫 항목]
- **09-26 대조 결과(파일 열어 확인, 정본은 `260925-pln-PLAN-two-sided.md` §9)**: 인계서 서술은 전부 맞았다. 정정 3건 + 미확인 1건 닫힘.
  ① `pipeline/app.py` RuntimeError 줄은 8904 → **8905**. ② `motionThumbs.ts` 위치는 `app/src/lib/` 가 아니라 **`app/src/constants/`**.
  ③ auto-register 가 쓰는 필드 = `geminiA` · `geminiAUpdatedAt` (+ 새 doc 이면 `isActive`/`inactiveReason`) — `firestore_admin.py:2368-2430`. "geminiA 만" 은 맞고 위치를 보강.
  ④ **[미확인] 닫힘 — mode1 이 yaml 을 고르는 키**: `referenceMotionId` 는 Gemini 프롬프트 힌트로만(`pipeline/app.py:8670-8673` → `recognize(motion_hint=…)` 8875-8880). yaml 키 = Gemini 가 낸 이름을 분류한 canonical(`gemini_technique_recognizer.py:325-355` `_classify_motion` → `_build_profile(canonical, …)`). 등록 목록 밖이면 "unregistered" → joint_expectations 빈 dict.
  대조 안 한 것 1: `reference/{id}/versions/{v}` + `_release.activeCandidate`(버전 구조) — 기획안 §11-3 에 [미확인] 으로 남김.
- 컬렉션은 `reference/{motionId}` (`models.py:836`). `referenceMotions` 는 없다(`contract.md:330-333`). S3 `reference/{id}.mp4`. 버전은 `reference/{id}/versions/{v}` + `_release.activeCandidate`.
- **등록 = 손 3단계**: ① mp4 를 S3 `reference/` 에 직접 ② Pod 에서 `backend/scripts/extract_reference_angles.py`(RTMW → angles JSON), `extract_reference_body_profiles.py`, `extract_reference_keypoint_reports.py` ③ `app/scripts/seed-reference-motions.mjs`(ADC 로그인, 손으로 쓴 MOTIONS 11개 L141-405: name·athleteName·level·entryType·**clipRange·checkpoints 손으로**) `--angles --keypoint-reports` 로 doc merge. mp4 업로드는 안 한다.
- **자동 등록 Lambda 가 이미 있다**: `backend/functions/reference-auto-register/app.py` `POST /reference/auto-register`(template.yaml:299) — belle uid 화이트리스트(L89), body `{s3Key, studioAlias?, overrideMotionId?}`, S3 GetObject `reference/*` 만, Gemini A `extract_reference_metadata` → `geminiA{routing_branch, motion_name_ipsf, clip_range, checkpoint_joints, confidence}` 만 씀. **angles 없음 → mode1 `RuntimeError("기준 모션 또는 keyframe 데이터 없음")`(pipeline/app.py:8904)**, name/athleteName/level 없음 → 앱 picker 가 버림(`referenceMotions.ts:72-78`). 호출처는 `reactivate_new6_motions.py` 뿐.
- exec 창은 저장 안 함 — 런타임에 상단 `clipRange` 에서 유도(`_reference_exec_window` 2796-2813), 없으면 DTW 폴백(9026). Gemini A 의 clip_range 는 geminiA 안에만.
- **새 referenceMotionId 가 기본으로 받는 것**: `SPLIT_LINE_ELEMENTS={"ref-power-spin"}`(technique.py:43) → 벌림 감점 없음(recognizer `required_split_deg` 와 OR) · criteria yaml 10개(`backend/judging_data/criteria/`, ref-combo 없음) — 없으면 FileNotFoundError 를 recognizer 가 잡아 8관절 전부 BENT_OK(gemini_technique_recognizer.py:434-446) = line/신전 감점 0 · Gemini 분류기 `REGISTERED_MOTIONS` 10개 고정, 모르면 "unregistered"(gemini_motion_classifier.py:26-47,130-175) · phrasebook 67 entries(climb·combo 0), lookup `{motion}.{criterion}` → `__common__` → failClosed · `motion_ipsf_map.json` 11개, 모르면 `_SAFE_DEFAULT_BRANCH`(branch2, angleSource=unavailable; 점수 억제는 mode3 만, mode1 점수는 나감 9631) · contact_points.yaml 5동작 · reference_anchors power-spin 만 · `reference_axis_floors.json` 5동작(수동, 파이프라인은 안 읽음) · 앱 `motionThumbs.ts` 11개 하드코딩.
- **업로드 경로**: presigned PUT 은 `uploads/*` 만(IAM template.yaml:195), 올리면 S3→SQS 로 **학생 분석이 시작**된다. `reference/` 용 presigned PUT 은 없다. CORS 는 `*`(178-181), 버킷 PUT `*`. 웹 페이지가 쓰려면 Firebase 익명 토큰 + `users/{uid}/analyses/{id}` doc 선작성(loading.tsx:146-163) 필요.
- **인증**: 익명 + Google + Apple(`auth/login.tsx`, `socialAuth.ts` 링크). 이메일·카카오 없음. uid = ID 토큰.
- **앱 화면**: routes `(tabs)/{index,analyze,history,profile}`, `analysis/{loading,reference,result}`, `auth/{login,signup}`, `help,inquiry,tutorial,legal/[doc]`. 홈 = 그라디언트 헤더 + NEW 동작 배너(최근 updatedAt) + 최근 분석 카드(없으면 "첫 분석하기") + "오늘 도전해볼 동작" 3개(전체보기 → `/analysis/reference`) + 주간 성장 그래프. analyze = `referenceMotionId` 파라미터면 mode1 강제, 없으면 mode 카드 2개 → mode1 은 picker.
- ~~[미확인] mode1 이 yaml 을 고를 때 Gemini 분류 결과를 쓰는지 referenceMotionId 를 쓰는지.~~ → 09-26 닫힘(위 ④): Gemini canonical 이 키, referenceMotionId 는 힌트.

## 5. 내일 순서
1. §4 를 파일 열어 대조(특히 auto-register Lambda 와 seed 의 clipRange 손 입력, presigned PUT IAM). 틀린 줄은 여기 정정.
2. belle 에게 §3 Q1~Q3 초안을 **판정 요청 형식**(된다/반쪽/안 된다 + ○×)으로 먼저. 답 오기 전에 기획안 골격은 써도 된다.
3. 기획안 골격 — **끝 그림 먼저, 실증은 그 안의 한 구간**(★ 기준): ① 한 줄 결론 ② 끝 그림 — 완성 앱 + 생태계(역할 4: 수요자·공급자·학원·플랫폼, 각자 얻는 것, 돈의 흐름, 권리의 흐름, 공급자가 늘수록 수요자가 좋아지는 고리) ③ 전제(기준 = 공급자 실행 하나, 정확도 우선) ④ 시장조사 근거 5 ⑤ 공급자 여정 전 경우의 수(초대/자발 · 증명 제출 · 승인/보류/거절 · 동작 등록 1/여러/재촬영/교체/삭제 · 등록 실패 4형(사람 미검출·여러 명·서 있는 시작 없음·저신뢰) · 학생 현황 열람 · 정산 · 탈퇴/권리 철회 시 기존 분석) ⑥ 수요자 여정 전 경우의 수(첫 실행 게스트 · 공급자 선택(학원 코드/목록/기본 정은지) · 동작 선택 · 촬영/업로드 · 대기(로딩 이탈·타임아웃·Pod 없음) · 결과(100점 빈 상태·실패 문구·no_human·not_pole_motion) · 재분석 · 성장 mode3 · 공급자 바꾸기(점수 비교 불가 표시) · 공급자 사라짐 · 권한 거부 · 결제) ⑦ 공급자 증명 3층 + 권리 동의 ⑧ 공급자 도구와 업로드(§3 Q1·Q2 끝 그림) ⑨ 메인 화면(§3 Q3 끝 그림) ⑩ 기술 관측 — 되는 것/손 배선(§4) ⑪ **실증 구간을 끝 그림 안에 배치** — 실증 기간에 만드는 것과 순서(파일럿 깨는 것: 실패 문구·로딩 이탈/타임아웃·100점 빈 상태·Pod 한 명령 → 공급자 링크 최소 → 그 다음 단계들), 실증 뒤 단계별로 무엇이 열리나 ⑫ 열린 질문.
4. 쓰는 곳: 리포 `.planning/quick/260925-pln-two-sided-plan/260925-pln-PLAN-two-sided.md` 정본 + belle 읽기용(Claude Docs 또는 페이지 — belle 결정). 둘이면 정본은 리포.
5. 09-18 상태 보드(https://claude.ai/artifact/FERGtfdf8vD18aYQjRtKG8)에 오늘 항목 반영 — 아직 안 했다.

## 6. 다시 하지 말 것 / 미확인
- 시장조사 재수집 금지 — 노트북에 있다. NotebookLM MCP `research_status` 는 task_id 를 무시하고 최근 fast 작업을 돌려준다 → deep 모드 추적 불가, fast 로 나눠 돌릴 것. `note create` 의 content 에 파일 경로를 넣으면 경로 문자열이 저장된다(본문을 넣을 것).
- 기획안에 숫자를 인용할 때 §0 [확인] 10건 외에는 원문 대조 후. Peloton 강사 급여(FourWeekMBA)는 2차 소스.
- "실증까지 새 기능 금지"(belle 09-19)는 살아 있다 — 기획안은 문서이고, 코드로 옮기는 것은 ②파일럿 깨는 것 → ③공급자 링크 순서, 그것도 belle 승인 뒤. **단 "실증까지는 아니다"를 기획의 답으로 쓰지 말 것(★ 기준) — 끝 그림을 먼저, 실증은 그 안의 구간.**
- 정은지 추가 영상 오면 이 기획안보다 **봉인 시험지 2회가 먼저**(`sealed_test.py`, 서 있는 자세에서 시작 요청).
- 미확인: ~~§4 전부(서브에이전트 보고)~~ → 09-26 파일 대조 완료(버전 구조만 미대조) · 표 나머지 숫자 · "우리 자리가 비어 있는 이유" 진단.
