---
phase: 38
checked_at: 2026-09-26
checker: gsd-plan-checker (리뷰 R1-R15 반영본 대상)
status: resolved
resolved_at: 2026-09-28
resolved_by: gsd-planner 수정 1회 + gsd-plan-checker 1회 (model fable — belle 09-28 선택)
blockers: 3
warnings: 2
---

# Phase 38 — 리뷰 반영 뒤 plan-checker 결과 (차단 3 해소 2026-09-28)

## 해소 (2026-09-28)

belle 지시: *"재계획은 하지 않고, 차단 3건만 플래너 1회와 검사 1회로 고친 뒤 실행으로"*.

- **차단 3 전부 해소** [확인: 검사기 `## VERIFICATION PASSED` — 새 차단 0 · 코드 소비처까지 추적(`hold_height._arrays` 키 `joints/frames/data/confidence` · `_NEEDED` 8관절 ⊂ `build_keypoint_report` 12관절) · 오케스트레이터 grep: 38-06 `13함수` 0 / `9함수` 5 · 38-09 `--offline` 5 · 38-07 `_dataclass_to_camel_case_dict` 6 / `dataclasses.asdict(report)` 0 · 38-14 diff 0].
- 바뀐 파일: 38-05 · 38-06 · 38-07 · 38-09 PLAN + 38-VALIDATION(Wave 0 세 줄). wave · depends_on · files_modified · task 수 무변경. 테스트 하한 38-05 ≥15 · 38-07 ≥17 · 38-09 ≥6 · 38-06 ≥24 유지.
  - 차단 1: 38-07 T2 step 8 `report_obj → None 이면 server_error → _dataclass_to_camel_case_dict` 한 dict 를 `check_registration` 과 `set_reference_angles` 에 같은 객체로. 38-05 T1 `_require_mapping` — 비Mapping TypeError, 형상 불량 Mapping 은 fail-closed 그대로(`hold_height._arrays` 무변경).
  - 차단 2: `_require_registration_ref_id` = reference 쓰기 9함수만. 읽기 3(`get_reference_registration` · `_private` · `list_…_by_status`)과 `create_analysis_doc` · `self_check_authorized` 는 비가드. 테스트 `test_legacy_ref_id_read_allowed` 추가.
  - 차단 3: 38-09 T1 에 `--diff <before> --out <path> --offline <after.json>`(Firestore · AWS 호출 0) + exit 0/1 규약(온라인 · 오프라인 같음). 38-14 무변경.
- **미반영(이월, belle "차단 3건만")**: 아래 경고 2 · 정보 전부. 검사기 추가 관측:
  - **W2 실패 기전 재현** [검사기 확인, Node 24.15]: supplierForm 이 `./supplierRules` 를 값 import 하면 이어 붙인 `rules.js` 가 자기 자신을 import → 모듈 컴파일 `SyntaxError`, 그런데 T1 게이트 `node --check` 는 통과(못 봄). **38-04 가 단일 HTML(38-12)을 고르면 38-12 실행 전에 W2 결정을 반영할 것.** 38-10/38-11 경로면 무관.
  - 정보: 38-09 T1 의 "docs/reference-motions.md §3 의 id 11개" — 실제 `ref-*` 는 §5(= `motionThumbs.ts` 11개), §3 엔 0개.
  - 정보: 38-06 "writer 13종" 라벨 = I/O 함수 수(쓰기 9 + 읽기 3 + `create_analysis_doc`). 가드 범위는 본문 · truth · acceptance 가 9 로 못 박아 실행 모순 아님(검사기 판정).
- 결정 커버리지 게이트 21/22 — D-06(clipRange 승격 선택) 미인용 → belle proceed-anyway, STATE.md 에 기록.

## 원 검사 기록 (2026-09-26)

> 리뷰(`38-REVIEWS.md`, Codex R1-R15)는 전부 플랜에 들어갔다. 38-01 끝 `## Review Response` 표가 기록이고, 검사기가 R 항목 15개를 플랜 본문과 대조해 PASS 했다.
> 그 반영 과정에서 플랜 사이 계약 불일치 3건이 새로 생겼다. 수정 에이전트가 Fable 크레딧 소진(HTTP 429)으로 중단돼 **아직 안 고쳤다** [확인: `13함수` 1건 · `--offline` 0건 · `_dataclass_to_camel_case_dict` 0건].
> **이 3건을 고치기 전에는 `/gsd-execute-phase 38` 금지.** 차단 1 은 정상 등록을 전부 실패시킨다.

## 차단 3

1. **38-07 T2 step 8 · 38-05 T1** — `check_registration` 에 `build_keypoint_report()` 의 `KeypointReport` frozen dataclass(`keypoint_frame.py:113-114`)가 그대로 들어간다. 38-05 의 판정 함수는 전부 `hold_height._arrays` 를 타는데, 이 함수는 Mapping 이 아니면 None 을 낸다(`hold_height.py:63-66`). 결과: 정상 영상도 `no_standing_start`(fail-closed) 또는 TypeError, Success ① 도달 불가.
   - 수정: `report_obj = build_keypoint_report(...)`; None 이면 `_fail_registration(server_error)`; `report = _dataclass_to_camel_case_dict(report_obj)`(`pipeline/app.py:1966`, 기존 11개 `referenceKeypointReport` 와 같은 camelCase 형상 = D-05, 앱은 `kr.axisData` 를 읽는다 `referenceMotions.ts:122`). 같은 dict 를 `check_registration` 과 `set_reference_angles(keypoint_report=report)` 둘 다에 넘기고 step 10 의 asdict 우회는 지운다.
   - 38-05 T1: `check_registration`·`low_confidence_joints`·`standing_start_*` 입력 = keypointReport **dict**(joints/frames/data/confidence, `test_hold_height._report` 형상), Mapping 아니면 TypeError(fail-loud).
   - 38-07 T2 acceptance 추가: happy path 테스트가 `check_registration` 이 dict(joints 12개)로 호출됐음을 단언.
2. **38-06 T1 ↔ 38-09 T1 · 38-14 T2/T4** — `ref-` legacy 가드가 "13함수"로 읽기 함수(`get_reference_registration`·`get_reference_registration_private`)까지 막는다. R10 기준선은 legacy 11개를 그 읽기 함수로 읽으므로 첫 id 에서 ValueError, Success ④ 증거를 못 만든다.
   - 수정: `_require_registration_ref_id` 는 쓰는 함수 9개만 — `create_reference_registration`, `claim_registration`, `set_registration_queued`, `set_registration_expired`, `set_registration_active`, `set_registration_failed`, `set_reference_angles`, `begin_self_check`, `set_reference_self_check`. 읽기 2개와 `list_reference_registrations_by_status` 는 아무 id 허용(38-09/38-14 의 raw legacy 읽기). "13함수" → "9함수". 테스트 추가: `get_reference_registration("ref-kip-up")` 가 raise 하지 않는다.
3. **38-09 T1 ↔ 38-14 T2** — 38-14 T2 게이트가 `snapshot_reference_baseline.py --offline <after.json>` 을 부르는데, 스크립트 주인인 38-09 T1 스펙엔 `--out` 과 `--diff <before> --out <after>` 뿐이다. 38-14 는 그 스크립트를 고칠 권한이 없다.
   - 수정: 38-09 T1 스펙과 `test_snapshot_reference_baseline.py` 에 `--offline <after.json>`(두 파일 비교, Firestore 읽기 0, exit 0/1) 추가. 38-14 는 그대로.

## 경고 2 (오케스트레이터 결정 포함)

1. **과적 task** — 38-04 T1(파일 16개: 설치 · export 최대 2회 · 웹 로그인 분기 · 프로브 3파일 · 이중 서빙 · 스크린샷 · 측정 기록)과 38-09 T1(기준선 보존 + 스냅샷 스크립트/테스트 + 5함수 보존 + 규칙 캡처 + template + SSM + `sam build` + changeset, 12파일). R10 "쓰기 전 기준선" 순서가 커밋 순서로만 지켜진다.
   - 결정: 38-04 T1 → T1a(설치·export·웹 로그인) / T1b(프로브·서빙·측정). 38-09 step 0 → 플랜 첫 번째 읽기 전용 task 로 분리(순서를 task 경계로). task 40 → 42, VALIDATION 행 갱신, wave·의존 변경 없음.
2. **38-12 T1** — `rules.js` 에 `supplierRules.ts` + `supplierForm.ts` 를 이어 붙이면 `./supplierRules` → `./rules.js` 치환 때문에 번들이 자기 자신을 import 하고, "표 밖이면 빌드 실패" 가드는 못 잡는다.
   - 결정: `rules.js` 와 `form.js` 를 따로 내보낸다(`form.js` 가 `./rules.js` 를 import). 남은 specifier 가 번들 자신을 가리키면 빌드 실패.

## 정보 (반영 결정)

- 38-09 T1: legacy id 출처 = `app/src/constants/motionThumbs.ts`(11개). `docs/reference-motions.md` 에만 있는 12번째 `ref-gemini-to-ayesha-combo` 도 Firestore 에 있으면 기준선에 포함, 없으면 absent 로 기록.
- 38-04 T3 · VALIDATION 범례의 `⏭` → ASCII `[skipped-by-decision]`(CLAUDE.md §7 이모지 금지). `★` 는 그대로.
- 그 밖(rtk 접두 없음 · PATTERNS 행 누락 · low_confidence 가 multiple_people 보다 먼저) 변경 없음.

## 다음 (2026-10-01 새벽 갱신 — belle "일단 여기까지 하고 정리하자", 38-13 완료 = 13/14)

### 진행 [확인]

- **38-13 완료** (`38-13-SUMMARY.md`). belle 실기기 최종 원문 *"1~9번 다 오케이"*. 링크 = `https://d2ivnoigym2xlu.cloudfront.net/supplier`.
- 그 사이 belle 폰 확인 수정 3건이 quick 으로 나갔다:
  - 260930-lfw 공급자 메일 초대(W1) · 260930-o0u 수강생 강사 코드 입력(W2, belle 폰 키보드 ○)
  - **260930-w9l 공급자 폼 수정 묶음** — 필수 4 · 동의 2(`[필수] … · 보기 >`) · 학습 체크박스 삭제 → 공급자 계약 근거 기록 · 5초~2분 단일 상한 · 공급자만 1GB · '이 동작에 대해' 3문항 삭제 · 선수 이름 = 초대 실명 고정(서버 409 supplier_name_missing) · '기본기'→'초급'. 배포 = layer `:23`(reference-upload-url · playback-url) · 웹 무효화 `IA83OV9SRXLSAVLLUPILU2U5Q9` · OTA preview `62eb42e4`. belle 결정 원문 = 메모리 `supplier-form-decisions-20260930`.
- 정리 끝: 시험 doc(클라임) 백업 뒤 삭제 + S3 객체 삭제 · TESTB deactivate(2026-09-30T15:30:15Z). 남은 reference doc 12개 = 시드, 대기 0 [확인].
- 게이트(w9l 끝): backend pytest 5755 passed / 20 skipped · typecheck 0 · node 82/82.

### 재개 = 웨이브 7 = 38-14 (Pod `pod:go` E2E + 정은지 초대)

순서가 중요하다:
1. Pod 기동(`/start` 절차) → **Pod 코드 배포를 requeue 보다 먼저** — w9l 의 `_register_reference`(소리 제거 · 서 있는 시작 썸네일 · 1GB · 120초). 옛 Pod 코드는 새 doc 을 isCombo 없음 = 30초 상한으로 본다.
2. `requeue_reference_registrations.py --dry-run` → 대기 0 이어야 정상(시험 doc 지움).
3. 정은지 초대 전 확인 2개: (a) 공급자 계약서에 AI 학습 조항이 들어가고 서명됐는가 — w9l 부터 새 등록은 learningOptIn true 로 기록된다 [미확인 — 법률 자문]. (b) 초대 `create --name` 에 **서류로 확인한 실명**.
4. 38-14 실측 대상 [미확인]: 1GB 4K 2분 영상의 폰 업로드(presign 900초) · Pod 다운로드·추출 · lease 900초 · 새 썸네일 프레임 belle 눈 판정.

### belle 결정 대기

- **push 방식** — 로컬 커밋 미push(origin/main = `ca739390`). 38-14 Pod 전까지 필요.
- **BELLE 코드** — Google 로그인 없는 옛 익명 계정(FDJr…)에 붙어 있음. belle 본인 Google 계정으로 초대할지.

### 알려진 작은 것

- 서버가 400 too_large · 409 supplier_name_missing 을 주면 화면은 일반 문구 '잠깐 문제가 있었어요'(`mapPresignFailure` 가 상태코드만 봄). 화면에서 먼저 막으니 보통 안 보인다.
- Figma 282:506 은 w9l 이후 코드와 다르다(`38-DESIGN-v2.md` 끝 w9l 절).
- `GET /reference` 500(08-31 부터, 앱 미사용) 그대로.

## 다음 (2026-09-30 새벽 갱신 — 이행 완료, 이력)

belle: *"일단 정리하고 인계서작성해줘 시간이 늦었다"* — 38-09·38-11 은 시작하지 않았다.

### 진행 [확인]

- **2026-09-30 오전 38-09 완료 → 12/14, 웨이브 5 끝** (`61a255e2` · `d50cf39f` · `c8f6607f` · `6989f64a`, 상세 `38-09-SUMMARY.md` · `38-09-CHANGESET.md`). CFN 배포(belle 승인) — `POST /reference/upload-url` 무토큰 401 + CORS, 6함수 layer `:21`, pipeline `POD_EXPECTED_PARAM`. 버킷 알림 `uploads/`+`reference/` · 수명주기 없음(D-17) · baseline 재diff 0. Firestore 규칙 = belle 콘솔 게시(선택 B) → 라이브 = 리포 바이트 동일(`rulesets/18587bf6…`) + 라이브 probe 6/6. 미결: `GET /reference` 500(10초 타임아웃, 08-31 부터, 앱 미사용 — belle 보고됨) · Pod 코드 미배포(38-14).
- **공급자 Figma 시안 (2026-09-30, belle 요청 → 오케스트레이터가 직접 그림)**: fileKey `jrdI7kp245HkPfLB0nclsz` 섹션 `282:506` "Phase 38 - 공급자 페이지 시안 (Claude, 2026-09-30)" — 화면 11 + 컴포넌트 5 + UI-SPEC 과 다른 점 8개 노트. 글꼴 Noto Sans KR(MCP 에 Pretendard 없음). **`/supplier` 코드를 38-13 전에 이 시안에 맞출지 belle 결정 대기.**
- **2026-09-30 아침 38-11 완료** (`685f02ce` · `b51e9fbc` · `4d66855d`) — `/supplier/upload`(STEP 01/02 · 제출 · 진행/취소 · 실패 패널) + `/supplier/guide`. typecheck 0 · node 65/65 · web export 15초(SPA, 세 라우트 번들 포함). 폼 화면은 로그인+화이트리스트가 필요해 아직 한 번도 그려 보지 않음 [미확인] → 38-13. Figma D-22 실측 또 미실행(MCP 없음) — 표는 `38-11-SUMMARY.md` 'Figma 실측'. 홈 index.tsx 에 justUploaded 토스트 · `?expired=1` 문구 추가. 남은 웨이브 5 = 38-09 Task 2 belle 체크포인트(changeset 생성만, 미실행).
- **9/14 실행 완료 + 38-12 skipped-by-decision** — 38-01~08 · 38-10 (각 `38-NN-SUMMARY.md`). 웨이브 1~4 끝.
- 38-10 (`3254d11e` 까지) = 웹 영상 길이 초→ms 수리(TDD `55f8eae6` → `0c902e29`) + `/supplier` 라우트(로그인 · 권한 없음 · 홈 두 카드 · 실패/만료/등록됨 상세). belle 시뮬 재측정 원문 *"1번 오케이, 2번은.. 한 8% 가다가 이렇게 문제가 있어요 실패. 3번도 마찬가지."* → 1·2·3 ○(Pod 끈 측정이라 실패 화면 도달 = 정상). 표 = `38-04-MEASUREMENT.md` "## 38-10 재측정".
- 게이트 (2026-09-30 01시, HEAD `3254d11e` 기준 재실행): backend 전체 `pytest tests -q` **5566 passed, 20 skipped** · app `npm run typecheck` exit 0 · node 테스트 6파일 **65 pass / 0 fail**. 착수 기준선 5184 passed.

### 재개

`/gsd-execute-phase 38` — SUMMARY 있는 플랜은 건너뛴다(use_worktrees=false → 순차, executor = opus).
1. **웨이브 5 = 38-09**(인프라 + rules 배포 — belle 체크포인트) **+ 38-11**(올리기 폼 · 가이드).
2. 웨이브 6 = 38-13(HTTPS 배포 + Authorized domain + 실기기 belle 검증).
3. 웨이브 7 = 38-14(Pod `pod:go` E2E).
4. 웨이브마다 끝나면 전체 스위트(backend pytest + app typecheck + node 테스트).

### belle 결정 대기

- **Figma 시안 반영 여부** — `/supplier` 코드를 38-13 전에 섹션 `282:506` 시안에 맞출지(위 진행 절).
- **push 방식** — 로컬 39커밋 미push(origin/main = `ca739390`, 이 인계 커밋 포함). 38-14 Pod 전까지만 필요. 선택지: `.claude/settings.local.json` 에 `Bash(git push origin main)` 좁은 규칙 → Claude 가 push / belle 이 `! git push origin main`.

### 다음 플랜이 알아야 할 관측 (진단은 따로 표시)

- **38-09 (완료 — 아래 네 줄은 착수 전 관측, 결과는 38-09-SUMMARY.md)**
  - rules `--test` 가 HTTP 403 `firebaserules.rulesets.test`(Admin SA) [확인 38-06]. `--release` 도 막힐 것 [추정]. IAM 부여 또는 belle 콘솔 배포 중 하나.
  - 배포 순서 = Pod 코드(38-08 `/register-reference`) → Lambda(38-07) → 버킷 알림 `reference/` 접두사 [38-08 SUMMARY]. 라우트 존재 확인 = Pod `POST /register-reference` 무토큰 401(토큰 미설정 503, 옛 코드 404).
  - `POST /reference/upload-url` = 404, CORS 헤더 없음 [확인 38-10 curl]. 그래서 지금 `/supplier` 는 `연결이 안 돼요` 로 뜬다 [확인 시뮬 스크린샷]. 배포 뒤 A-2/A-3 로 바뀔 것 [추정]. 38-09 라이브 검증에 Origin 헤더 curl 한 줄 추가됨(`a4ba62d2`).
  - Pod 자격증명의 `reference/*`·`uploads/*` PutObject 범위 [미확인 — 38-09 T3 (E) / 38-14].
- **38-11**: 다시 올리기 → `/supplier/upload` 파라미터 계약 = `name · athleteName · level · isSplit · hasHold · standingStart`(38-10 `8593792f`). 38-11 도 Figma D-22 를 요구한다 — 38-10 실행기는 Figma MCP 를 못 열었다.
- **38-13**
  - Figma D-22 실측 이월: `≈` 네 칸(outline 48 · google 48 · STEP 라벨 13.8 · noticePill 15) — 38-13-PLAN Task 3 에 문단 추가(`3254d11e`).
  - D-3 이월: 공급자 probe 브라우저 CORS · `reference` `where supplierUid` 구독 = Task 3 단계 1·4.
  - `.mp4` 형식 경로 [미확인]: 38-10 의 S3 객체 둘이 모두 `.mov` 시험 클립과 같은 8,108,834 bytes — 같은 파일을 두 번 골랐을 수 있다.
  - Authorized domain 은 belle 콘솔(Task 2, CLI 없음).
- **38-14**: Pod 기동 뒤 `AWS_PROFILE=sunity-motion backend/.venv/bin/python backend/scripts/requeue_reference_registrations.py --dry-run` → 대기 건 있으면 인자 없이 1회. Pod 이 중간에 죽었던 날은 `--reclaim-stale`, 오래된 `registering` 은 `--sweep-expired` [38-08 SUMMARY].
- 진단(재검증 대상): 38-10 측정의 "~8% 뒤 실패" = Pod 부재로 Pipeline Lambda 가 `failed/server_error` 기록 [추정 — CloudWatch 미열람; Firestore `server_error` 2건은 확인].
- 공통: REQUIREMENTS.md 에 REQ-38-* 행이 없어 `requirements.mark-complete` 가 매번 not_found. STATE frontmatter `stopped_at` 과 본문 `Stopped at:` 은 둘 다 고친다(`: ` 없이).

### 새 정보 — 정은지 중급콤보 영상 (09-29 도착)

- 메모리 `jeongeunji-combo-videos-20260929` 참조(파일·동작 목록은 거기에). 콤보 = 한 영상에 동작 3~5개, 학생 시계열 아님(Mode 1 재료).
- belle 09-30: *"일단 공급자 앱 개발을 먼저 끝내자"* → Phase 38 끝날 때까지 콤보 분석·시험 영상 2차 착수 금지. 콤보 = 아무도 짚지 않은 시험지 — 착수 때 상수·규칙을 먼저 맞추지 말고 현재 절차 그대로 돌려 박제한다. 절단 여부는 그때 belle 과 함께 정한다.

## 다음 세션 (2026-09-26 기록 — 이행 완료)

`/gsd-plan-phase 38 --reviews` 로 들어가되 **재계획하지 않는다.** 오케스트레이터가 이 파일을 checker_issues 로 넣어 플래너 수정 1회(plan-phase 12단계) → 검사기 1회 → 통과하면 이 파일 `status: resolved` + 커밋·push → `/gsd-execute-phase 38`.
주의: `.planning/config.json` 의 `model_overrides` 가 GSD 에이전트 전부 `fable` 이다. 바꾸지 않으면 에이전트가 Fable 크레딧을 쓴다(belle 결정 대기, 2026-09-26).
