---
phase: quick-260930-o0u
plan: 01
status: complete
subsystem: app/profile(마이 탭) + firestore.rules + ops script (Phase 38 W2)
tags: [instructor-code, supplier, student, 38-DESIGN-v2, 38-SCENARIOS, ota]
requires: [quick-260930-lfw (suppliers · supplierCodes), 38-09 (규칙 게시 경로)]
provides: [수강생 강사 코드 입력(마이 탭 행 3상태 · 입력 시트 · 강사 확인 · 토스트) · instructorLinks create-once 규칙 · instructor_link.py show/unlink · OTA preview ios b2b148b4]
affects: [38-13 폰 확인 나머지 · 38-14 정은지 초대(학생이 BELLE 코드로 연결) · 강사 대시보드(연결 목록을 읽을 곳)]
key-files:
  created:
    - app/src/lib/instructorCode.ts (+ instructorCode.test.ts)
    - app/src/lib/instructorLink.ts
    - app/src/components/InstructorCodeSheet.tsx
    - backend/scripts/instructor_link.py (+ backend/tests/test_instructor_link_script.py)
    - .planning/quick/260930-o0u-student-instructor-code-input/{260930-o0u-DEPLOY.md, rulesprobe_o0u.py, firestore-rules-before.rules, sim/01~09}
  modified:
    - firestore.rules (instructorLinks · supplierCodes get · suppliers self get)
    - docs/contract.md · backend/shared/python/sunity_shared/{models,firestore_admin}.py · app/src/types/analysis.ts
    - app/src/constants/profileCopy.ts · app/src/theme/colors.ts · app/src/app/(tabs)/profile.tsx
commits: [6e4b2e1e, 5dc1789c, aa78d126, 2e9d39fa, 80a75b8f, e813c9ee, 63d77803]
ota: {branch: preview, platform: ios, runtime: 1.2.4, group: b2b148b4-a789-49fe-bd18-b926fefb8fa9, commit: e813c9ee, rollback_group: b59f97ae-3b1f-4b67-9819-7a5c8a592ed1}
completed: 2026-09-30
---

# quick 260930-o0u — 수강생 강사 코드 입력 (W2)

belle 2026-09-30: *"수강생 입력 칸까지 이번에 만들기"* + *"오케이 일단 고"* → 명세 `38-DESIGN-v2.md` §W2 → 이 작업.
belle 판정(2026-09-30, sim 01~08 한 장 모음을 보고): **"안내 글자만 맞추고 OTA 진행"**.

## 한 것 — 관측

- **규칙**: `instructorLinks/{uid}` 는 본인이 한 번만 만든다. 본인 코드 · 없는 코드 · 비활성 코드 · supplierUid/displayName 위조 · 클라이언트가 정한 linkedAt · 다섯째 필드는 모두 막힌다. `supplierCodes` 는 로그인 사용자 get 만, `suppliers` 는 본인 get 만 된다 [확인 라이브 probe 22/22, DEPLOY §B].
- **앱**: 마이 탭 로그인 카드 아래 '강사 코드' 행(로딩 / 미연결 '입력하기' / 연결됨 두 줄), 아래에서 올라오는 입력 시트 → 같은 시트에서 강사 확인 → '연결하기' → 토스트 [확인 시뮬 01~08, belle ○].
- **운영 스크립트** `backend/scripts/instructor_link.py show / unlink [--dry-run]` — 첫 실전에서 시뮬 연결을 지웠다 [확인 DEPLOY §F-3].
- **belle 수정 1건** `e813c9ee`: 강사 코드 행 힌트 글자를 명세 값 15(`text.auxFaint`)에서 바로 위 로그인 힌트와 같은 `typography.caption`(12) + `colors.textSecondary` 로 바꿨다. 미연결·연결됨 두 힌트가 같은 스타일을 쓴다 [확인 코드]. 시뮬 09 에서 두 힌트의 AX 높이가 모두 14.33pt 이고, 눈으로 봐도 크기·색·들여쓰기가 같다 [확인].
- **시험 공급자 TESTB**: 08:52:07Z 에 켜서 09:19:56Z 에 다시 껐다(약 28분). 지금 suppliers·supplierCodes 둘 다 active False 다 [확인 Admin 다시 읽기].
- **instructorLinks** 문서 수는 지금 0이다 [확인].

## 테스트·게이트 — 관측

- backend `tests/test_instructor_link_script.py` 21 passed [확인 — 이 실행기가 다시 돌렸다].
- app `instructorCode.test.ts` 9/9. 공급자 6파일을 합친 node 7파일은 79/79, fail 0이다 [확인 — 힌트 수리 뒤 tap 리포터로 다시 돌렸다].
- `npm run typecheck` 오류 0 [확인, 힌트 수리 뒤].
- 공급자 파일(SupplierUi · supplier/* · supplierCopy · supplierRules)은 이 작업에서 바뀐 게 없다. 그래서 웹 export 게이트는 필요 없다 [확인 `git diff --stat 6e4b2e1e~1..HEAD` 빈 출력].
- RED 인용 2줄: 이 요약을 쓴 실행기는 Task 8 부터 이어받아서 Task 1·2 의 RED 출력을 직접 보지 못했다 [미확인]. 커밋 메시지에는 "pytest 먼저 / node --test 9 new tests"라고만 적혀 있다.

## 플래너 결정 (a)~(f) · 명세에서 바꾼 것

- 커밋 메시지와 DEPLOY 에는 결정 (a)~(f) 를 바꿨다는 기록이 없다. 그래서 바꾼 것은 없다고 본다 [미확인 — Task 1~3 의 실행기 판단 기록은 이어받지 못했다].
- 명세에서 달라진 점 1: 힌트 글자 15 → 12. belle 판정에 따른 것이다 [확인 `e813c9ee`]. 38-DESIGN-v2 §W2 의 15 값은 문서에 아직 그대로 있다. 다음에 명세를 손볼 때 12(caption)로 맞출 대상이다.
- 명세에서 달라진 점 2: `errors.failed` 문구 '연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.'를 더했다. 명세에는 없는 문구다. 알 수 없는 오류에 오프라인 문구를 보여 주면 거짓말이 되기 때문이다 [확인 PLAN · profileCopy].
- 시뮬 09 파일 이름은 오케스트레이터 지시에 따라 `09-row-empty-after-unlink.png` 로 했다. PLAN verify 가 찾는 이름은 `09-after-unlink.png` 다. 이름만 다르고 내용은 같은 증거다 [확인].

## OTA — 관측

- 명령: `eas update --branch preview --platform ios --message "W2 강사 코드 입력 + 38-02 길이 검사·문구 (quick 260930-o0u)" --non-interactive`. exit 0 [확인].
- **group `b2b148b4-a789-49fe-bd18-b926fefb8fa9`** · ios · runtime **1.2.4** · 커밋 `e813c9ee` · 2026-09-30T09:23:31Z [확인 `eas update:view` 다시 읽기]. runtime 은 TestFlight 빌드 40(channel preview → branch preview)과 같다 [확인 DEPLOY §E].
- 함께 나간 것: W2 전부 + 38-02 영상 길이 검사·촬영 문구 + 강사 질문 말투 등이다(DEPLOY §E 표). 09-20 이후 처음 나가는 수강생 앱 변경이다 [확인 커밋 범위]. 폰에서는 아직 아무도 보지 않았다 [미확인].
- 롤백: `cd app && eas update:republish --group b59f97ae-3b1f-4b67-9819-7a5c8a592ed1 --message "ROLLBACK: quick-260930-o0u" --non-interactive`. 옵션이 있는지는 `--help` 로 확인했지만 실제로 돌려 보지는 않았다 [미확인].
- Metro(8081)는 멈췄다. 시뮬레이터는 켜 둔 채 두었다 [확인].

## [확인] / [미확인] 정리

- [미확인 — belle 폰] **실제 폰에서 키보드가 입력칸이나 '확인' 버튼을 가리지 않는지.** 시뮬에서는 화면 키보드가 끝까지 뜨지 않았다.
- [미확인 — probe + unit] **본인 코드 오류 화면** '본인 코드는 넣을 수 없어요.'. 시뮬 uid 가 공급자가 아니라서 화면으로는 못 봤다. 규칙은 probe 4행, 앱 쪽은 reducer 테스트가 덮는다.
- [미확인(시뮬)] **이름 없는 공급자일 때 코드를 이름 자리에 쓰는 경로**(`instructorName` → code). 시험 코드 TESTB 에는 이름이 있다. unit 테스트만 덮는다.
- [미확인] 네트워크 오류 문구 · reduced motion 모습 · 연결됨 상태에서 줄인 힌트가 어떻게 보이는지(같은 스타일인 것은 코드로 확인).
- [미확인] belle 폰에 OTA 가 적용됐는지.

## 진단(재검증 대상)

- 번들 내용이 커밋 `e813c9ee` 의 app/ 과 같다고 본다. 발행 때 app/ 에는 바뀐 파일이 없었고 `*`(작업 트리 미정리)는 `.planning/` 파일 때문이다 [추정 — 번들 해시로 따로 대조하지 않았다].
- TESTB 를 끈 뒤 최대 60초 동안 reference-upload-url 의 따뜻한 컨테이너는 UmH3… 를 공급자로 볼 수 있었다 [추정 — 코드 읽기].

## belle 에게 전할 말

- 새 화면은 TestFlight 앱을 **완전히 종료했다가 다시 켜기를 두 번** 하면 적용돼요. 첫 실행에 받아 두고 그다음 실행에 바뀝니다. 마이 탭 로그인 카드 아래에 '강사 코드 · 입력하기'가 보이면 새 버전이에요.
- 폰에서 확인할 것 두 가지:
  1. 입력칸을 눌러 키보드가 올라올 때 입력칸과 '확인' 버튼이 가려지지 않는지.
  2. 영상 고를 때 3초보다 짧거나 90초보다 길면 바로 막히는지(38-02).

## 다음 할 일

- belle 폰 확인(위 두 가지). 문제가 있으면 롤백 명령을 쓴다.
- belle 폰에서 BELLE 코드로 시험 연결을 했다면, 확인 뒤 `instructor_link.py show --uid <belle 폰 uid>` → `unlink --dry-run` → `unlink` 로 지운다(파일럿 학생 데이터와 섞이지 않게).
- 38-DESIGN-v2 §W2 의 힌트 값 15 → 12(caption) 문서 정정.

## Self-Check: PASSED

- 파일: `sim/09-row-empty-after-unlink.png` · `260930-o0u-DEPLOY.md`(§F, 'unlinked' 포함) 있음 [확인].
- 커밋: 6e4b2e1e · 5dc1789c · aa78d126 · 2e9d39fa · 80a75b8f · e813c9ee · 63d77803 모두 `git log` 에 있음 [확인].
- instructorLinks 0건 [확인]. push 0 [확인].
