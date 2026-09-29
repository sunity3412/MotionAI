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

## 다음 (2026-09-30 00시 갱신 — 38-04 결정 option-1, 다음 웨이브 4)

**진행 7/14 실행 완료 + 38-12 skipped-by-decision** — 38-01 · 38-02 · 38-03 · 38-04 · 38-05 · 38-06 · 38-07 (각 `38-NN-SUMMARY.md`). 38-04 결정 = belle "option-1 앱을 웹으로"(38-10·38-11 실행, 38-12 는 `38-12-SUMMARY.md` skipped-by-decision) · `selfScoreMin: 90 유지` [확인 belle 2026-09-30]. 38-04 끝 앱 typecheck 0 [확인]. 아래 6/14 시점 스위트 수치는 그때 값. 전체 pytest 5499 passed · 20 skipped · 앱 typecheck 0 [확인 2026-09-29, HEAD cfe369e6]. 착수 기준선 5184 passed.

**재개 = `/gsd-execute-phase 38`** — SUMMARY 있는 플랜은 건너뛴다(use_worktrees=false → 순차, executor fable).
1. ~~**38-04**~~ 완료(`38-04-SUMMARY.md`) — Task 1 측정(react-native-web 설치 · `expo export --platform web` · 후보 (2) probe · 시뮬레이터 Mobile Safari 서빙) → **Task 2 belle 실측 체크포인트**(8줄 ○×) → **Task 3 결정**(option-1 Expo web → 38-10·38-11 / option-2 단일 HTML → 38-12, 미선택은 SUMMARY `skipped-by-decision`). option-2 면 38-12 실행 전에 W2(rules.js 자기 import) 먼저.
2. **다음 = 웨이브 4 = 38-08 + 38-10.** 38-10 은 38-04 실측 이월로 맨 앞 Task 0(웹 영상 길이 초→ms 수리, TDD) · 맨 끝 Task 4(시뮬레이터 belle 재측정 체크포인트 — 후보 (1) PUT·onSnapshot·`.mov` + 공급자 probe CORS·reference 구독)가 붙어 `autonomous: false`. 그 뒤 → 웨이브 5 = **38-09 결정**(인프라 + 규칙 배포) + 38-11 → 웨이브 6 = 38-13(belle) → 웨이브 7 = 38-14(Pod `pod:go`).
3. 웨이브마다 끝나면 전체 스위트(`cd backend && .venv/bin/python -m pytest tests -q` + `cd app && npm run typecheck` + node 테스트) — 실행기는 플랜 범위만 돌려 격리 누수를 못 본다(웨이브 2 에서 43건).

**belle 결정 대기**
- **push 방식** — 로컬 25커밋 미push(origin/main = ca739390, 38-04 끝 기준). 38-05 실행기의 `git push` 가 auto mode 분류기에 막혀(Out-of-Place Publication) 대신 push 하지 않았다(하위 에이전트 거부 동작 대행 금지). 38-14 Pod 전까지만 필요. 선택지: `.claude/settings.local.json` 에 `Bash(git push origin main)` 좁은 규칙 → Claude 가 push / belle 이 `! git push origin main`.

**다음 플랜이 알아야 할 관측**
- 38-09: 라이브 규칙 `--test` 가 HTTP 403 `firebaserules.rulesets.test`(Admin SA 권한 부족) [확인 38-06] → `--release` 도 막힐 가능성 [미확인]. IAM 부여 또는 belle 콘솔 배포가 38-09 결정에 들어간다.
- 배포 순서: 38-07 Lambda 코드가 Pod `/register-reference`(38-08)보다 먼저 살면 위임 404 → `failed(server_error)` [38-07 SUMMARY]. 38-09 는 38-08 뒤라 순서는 맞지만 배포 때 재확인.
- Pod 자격증명의 `reference/*`·`uploads/*` PutObject 범위 [미확인 — 38-09 T3 (E) / 38-14 T2 3-b].
- 38-02 Figma 노드 1:754 대조 [미확인 — 실행기에 Figma 도구 없음]. 시뮬레이터 실물 2장은 확인함.
- REQUIREMENTS.md 에 REQ-38-* 행이 없어 실행기의 추적표 갱신이 매번 not_found(로드맵·플랜에만 정의).
- 웨이브 2 게이트 43건 실패 = 기존 테스트 `sys.modules` 누수(`test_firestore_admin_gemini_cache`) → b10415ef 로 원천 수리.
- STATE.md frontmatter `stopped_at` 은 본문 `Session Continuity` 의 `Stopped at:` 줄에서 복사된다(3ee2c58b) — 착수점을 바꿀 때 둘 다, `: ` 없이.

## 다음 세션 (2026-09-26 기록 — 이행 완료)

`/gsd-plan-phase 38 --reviews` 로 들어가되 **재계획하지 않는다.** 오케스트레이터가 이 파일을 checker_issues 로 넣어 플래너 수정 1회(plan-phase 12단계) → 검사기 1회 → 통과하면 이 파일 `status: resolved` + 커밋·push → `/gsd-execute-phase 38`.
주의: `.planning/config.json` 의 `model_overrides` 가 GSD 에이전트 전부 `fable` 이다. 바꾸지 않으면 에이전트가 Fable 크레딧을 쓴다(belle 결정 대기, 2026-09-26).
