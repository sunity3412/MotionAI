---
phase: quick-261002-kkt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/scripts/eval_split_check.py
  - backend/tests/test_eval_split_check.py
  - .planning/sealed/EVAL-SPLIT.md
  - .planning/TRAINING-DUE.md
autonomous: true
requirements: [QUICK-261002-kkt]

must_haves:
  truths:
    - "status 가 closed 인 시험의 rows 는 평가 해시를 하나도 만들지 않는다 — 채점이 끝난 영상은 연습 영상이라 학습 후보다 (belle 09-26 '시험 영상은 배우지 않는다, 나머지는 전부 배운다')"
    - "practice 영상은 평가가 아니다 — practice 해시의 manifest 행은 L1/L2 누수로 잡히지 않는다"
    - "안 닫힌 시험(status sealed / run / graded)의 영상은 지금과 똑같이 짝 → 같은 (subject, session) 클립까지 평가로 확장된다"
    - "평가 해시가 0편이면 보고서 판정 줄 = '평가셋 없음 — 다음 시험 영상이 봉인되기 전까지 게이트 4 꺼짐' 이고 '세션 분리 OK' 는 안 나오며 main 은 exit 2 다"
    - "오늘 데이터로 재실행하면 exit 2 · L1 0 이고 manifest.json · sealed_tests.jsonl 은 한 바이트도 안 바뀐다"
    - "TRAINING-DUE 게이트 4 행이 '정책 코드 반영 · exit 2 평가셋 없음 · 다음 시험 영상 봉인 때 켜짐 · 인물 분리 불가'를 적고, 돌리는 법 4번이 exit 2 = 통과 아님을 적는다"
  artifacts:
    - path: "backend/scripts/eval_split_check.py"
      provides: "status != closed 만 평가로 보는 eval_groups + verdict_code(ev, leaks) -> 0/1/2"
      contains: "def verdict_code"
    - path: "backend/tests/test_eval_split_check.py"
      provides: "닫힌 시험·practice 학습 가능·안 닫힌 시험 확장·평가셋 없음 판정 단언"
      contains: "평가셋 없음"
    - path: ".planning/sealed/EVAL-SPLIT.md"
      provides: "10-02 재생성 보고서 — 평가셋 없음"
      contains: "평가셋 없음"
    - path: ".planning/TRAINING-DUE.md"
      provides: "게이트 4 행 갱신 + 돌리는 법 4번 exit 코드"
      contains: "exit 2"
  key_links:
    - from: "backend/scripts/eval_split_check.py::main"
      to: "verdict_code"
      via: "return verdict_code(ev, leaks) (mark-holdout 분기 제외)"
      pattern: "return verdict_code\\(ev, leaks\\)"
    - from: "backend/scripts/eval_split_check.py::render_report"
      to: "verdict_code"
      via: "판정 줄 문구를 같은 코드로 고른다 — 보고서와 exit 코드가 갈라지지 않게"
      pattern: "verdict_code\\(ev, leaks\\)"
    - from: "backend/scripts/eval_split_check.py::eval_groups"
      to: "sealed_tests.jsonl status"
      via: "t.get('status') != 'closed' 인 시험의 rows 만 평가 해시"
      pattern: "!= \"closed\""
---

<objective>
재학습 게이트 4 — belle 2026-09-26 holdout 정책("시험 영상은 배우지 않는다, 나머지는 전부 배운다", 시험 영상 = 처음 채점하는 영상만)을 `backend/scripts/eval_split_check.py` 에 넣는다.

Purpose: 지금 코드는 닫힌 시험의 영상과 practice 영상까지 평가로 잡아 정은지 06-17 세션 전체를 평가셋으로 만들고, 그래서 실수 fixtures 6편이 L1 누수로 나와 exit 1 이 된다. 정책대로면 그 6편은 이미 채점이 끝난 연습 영상이라 학습 후보다. 동시에 평가셋이 0편이 되면 보고서가 "세션 분리 OK" 로 읽히는 구멍이 생기므로, 평가셋 없음을 별도 판정(exit 2)으로 만든다 — 통과가 아니라 "게이트 4 꺼짐".

Output: 고친 스크립트 + 테스트, 재생성한 `.planning/sealed/EVAL-SPLIT.md`(exit 2 기록), 갱신한 `.planning/TRAINING-DUE.md` 게이트 4 행.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@backend/scripts/eval_split_check.py
@backend/tests/test_eval_split_check.py
@.planning/TRAINING-DUE.md

<facts_measured_at_planning>
[확인 2026-10-02, planner 가 파일을 직접 읽음]
- `backend/training/data/sealed_tests.jsonl` 에는 시험 1건뿐: test_id 260925-mvh, status "closed", rows = fixtures/phase15/power-spin/fault.mp4 · fixtures/phase15/climb/fault.mp4 의 해시 2개(sub_je, session 2026-06-17), practice = [].
- clips.jsonl 12편 전부 sub_je / 2026-06-17, pairs.jsonl 6쌍.
- 현재 `.planning/sealed/EVAL-SPLIT.md`(git 추적됨): 평가 영상 4편, 평가 그룹 [('sub_je','2026-06-17')], L1 6 · L2 0 · L3 11, exit 1.
- 시험 상태 수명(`backend/scripts/sealed_test.py`): seal → "sealed", cmd_run → "run", cmd_grade → "graded", cmd_close(belle ○×) → "closed". practice = 봉인 때 이미 분석된 영상(정답이 이미 알려진 영상).
- `eval_split_check` 를 import 하는 곳은 `backend/tests/test_eval_split_check.py` 하나뿐(grep, backend/ 전체).
- `main()` 은 고정 경로(MANIFEST/CLIPS/PAIRS/SEALED/REPORT)를 읽으므로 exit 코드 매핑은 순수 헬퍼 `verdict_code` 로 빼서 테스트한다.
- 새 정책 적용 뒤 오늘 데이터 예상(코드로 계산, 실행 전이라 [미확인]): 평가 해시 0 → groups·subjects·clips 비어 L1 0 · L2 0 · L3 0 → exit 2.
</facts_measured_at_planning>

<hard_prohibitions>
- `정은지님 영상/` 폴더와 어떤 중급콤보 영상도 열지 않는다, 목록을 보지 않는다, 분석하지 않는다 — 다음 시험 영상(아직 아무도 짚지 않은 영상)이다 (belle 09-30: Phase 38 뒤).
- `backend/training/data/manifest.json` 수정 금지. `--mark-holdout` 실행 금지.
- `backend/training/data/sealed_tests.jsonl` 수정·삭제 금지 — 이력이다. 정책은 status 로 코드에서 처리한다.
- `.planning/STATE.md` 의 `stopped_at` 을 건드리지 않는다(quick 행 추가는 오케스트레이터 몫).
- 사용자에게 보이는 글(보고서·TRAINING-DUE)에서는 "시험 영상 / 연습 영상" 이라 쓰고 "봉인 시험지" 라 쓰지 않는다.
- Python 스타일: `from __future__ import annotations` 유지, 왜를 설명하는 한국어 주석 + 출처 인용(belle 09-26, TRAINING-DUE 게이트 4), 이모지 금지, 파일의 기존 압축 스타일(한 줄 `;` 결합 등)에 맞춘다. 새 기능 추가 금지.
</hard_prohibitions>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: eval_groups 를 '안 닫힌 시험만 평가'로 바꾸고 평가셋 없음 = exit 2 를 verdict_code 로 단일화</name>
  <files>backend/scripts/eval_split_check.py, backend/tests/test_eval_split_check.py</files>
  <behavior>
    - test_open_test_expands_by_pair_and_session (status "sealed" / "run" / "graded" 로 parametrize): sealed = [{"status": s, "rows": [d, b], "practice": []}] 이면 hashes == {d, b, a}(a 는 b 의 짝), groups == {("sub_s01","2026-10-05"), ("sub_je","2026-06-17")}, clips 해시 == {a, b, c, d}(c 는 같은 세션), subjects == {"sub_je","sub_s01"} — 기존 확장 규칙이 안 닫힌 시험에서는 그대로임을 단언.
    - test_closed_test_is_practice_not_eval: sealed = [{"status": "closed", "rows": [b], "practice": []}] 이면 hashes · groups · subjects 가 비고 clips == [], closed == ["t-closed"](test_id), verdict_code(ev, 빈 누수) == 2.
    - test_practice_and_closed_rows_are_learnable: sealed = [닫힌 시험 rows [b]] + [{"status": "sealed", "rows": [d], "practice": [e]}] 이면 hashes == {d}(b 도 e 도 아니고, b 가 평가가 아니니 짝 a 도 아님), groups == {("sub_s01","2026-10-05")}. manifest 에 b·e·a 의 s3_key 행이 있어도 find_leaks 의 L1·L2·L3 어디에도 안 잡힌다.
    - test_leak_levels: 기존 단언 유지 — ev 를 {"status": "sealed", "rows": [d, b]} 로 만들면 L1 == [ps/fault, climb/fault], L2 == [], L3 == [intake/e.mov, reference/ref-kip-up.mp4], holdout 행은 후보 아님.
    - test_report_states_single_subject_limit_and_verdict: {"status": "sealed", "rows": [c]} 로 만든 ev 에서 누수 0 이면 md 에 "인물 분리 불가" 와 "세션 분리 OK", verdict_code == 0; L1 1건이면 md 에 "누수", verdict_code == 1.
    - test_empty_eval_set_is_not_a_pass: 닫힌 시험만 있는 ev 로 render_report → md 에 "평가셋 없음 — 다음 시험 영상이 봉인되기 전까지 게이트 4 꺼짐" 포함, "세션 분리 OK" 미포함, "인물 분리 불가" 미포함(0명인데 "1명뿐(정은지)" 이라고 쓰면 거짓), verdict_code == 2.
  </behavior>
  <action>
RED 먼저: `backend/tests/test_eval_split_check.py` 를 위 behavior 대로 고친다. 픽스처 `_clips()` · `_pairs()` 는 그대로 쓰고, 옛 규칙을 박은 `_sealed()`(practice b 를 평가로 기대)와 `test_eval_groups_expand_by_pair_and_session` 은 status 가 있는 시험 dict 를 만드는 작은 헬퍼(예: `_test(status, rows, practice=(), test_id="t")` → {"test_id", "status", "rows": [{"video_hash": h}…], "practice": [...]})로 바꿔 위 6개 테스트로 재구성한다. 모듈 docstring 의 단언 목록을 새 규칙으로 다시 쓴다: (1) 안 닫힌 시험(sealed/run/graded) 영상 → 짝 → 같은 인물·세션 클립까지 평가 (2) 닫힌 시험 영상과 practice 는 연습 영상 — 평가 아님, 학습 후보 (belle 09-26, TRAINING-DUE 게이트 4) (3) L1/L2/L3 분류 (4) 인물 1명이면 '인물 분리 불가' (5) 평가셋 0편이면 '평가셋 없음' + verdict 2, 통과로 안 읽힌다 (6) holdout 행은 학습 후보가 아니다. 이때 pytest 가 실패(verdict_code 없음, 옛 practice 규칙)하는 것을 확인한다.

GREEN: `backend/scripts/eval_split_check.py` 를 고친다.
(a) eval_groups — 평가 해시의 시작은 `t.get("status") != "closed"` 인 시험의 rows 만이다(status 없는 dict 는 안 닫힌 것으로 본다). practice 를 eval_hashes 에 넣던 루프와 그 주석("연습 문제로 빠졌어도 정답이 공개된 영상 — 학습에 넣지 않는다")을 지운다 — belle 09-26 정책과 반대다. 닫힌 시험의 test_id 목록을 반환 dict 에 "closed" 키로 더한다(보고서가 왜 비었는지 적기 위해서만). 짝 확장 · (subject, session) 확장 · clips/groups/subjects 계산은 한 글자도 바꾸지 않는다. docstring 을 정책 + 출처로 다시 쓴다: 시험 영상 = 처음 채점하는 영상만(status sealed/run/graded), closed = 채점이 끝난 연습 영상 → 학습 후보, practice = 봉인 때 이미 분석된 영상 → 연습 영상 → 학습 후보, 출처 belle 2026-09-26 "시험 영상은 배우지 않는다, 나머지는 전부 배운다" · TRAINING-DUE 게이트 4. 안 닫힌 시험과 같은 (subject, session) 에 있는 practice 영상은 기존 세션 규칙(37-DATA-SPEC 규칙 6)으로 여전히 평가 클립이 된다는 점을 docstring 에 한 줄 적는다(규칙 6 은 이번에 안 바꾼다).
(b) 새 순수 함수 `verdict_code(ev: dict, leaks: dict) -> int` 를 find_leaks 아래에 둔다: 평가 해시가 비면 2, 아니면 L1 또는 L2 가 있으면 1, 아니면 0. 주석에 세 코드의 뜻을 적는다(2 = 평가셋 없음 = 통과 아님, 게이트 4 꺼짐).
(c) render_report — 판정 줄을 verdict_code 로 고른다: 0 → "세션 분리 OK (L1·L2 = 0)", 1 → 기존 누수 문구 그대로, 2 → "평가셋 없음 — 다음 시험 영상이 봉인되기 전까지 게이트 4 꺼짐". '인물 분리 불가' 단락은 평가 인물이 정확히 1명일 때만 낸다(`<= 1` → `== 1`; 0명인데 "1명뿐(정은지)" 은 거짓). 사용자에게 보이는 문구의 "봉인 시험지" 를 "시험 영상" 으로 바꾼다: 요약 줄은 "시험 영상(안 닫힌 시험 + 짝): N편 · …", 인물 분리 불가 단락은 "다른 사람의 시험 영상이 생겨야 게이트 4 가 켜진다". ev["closed"] 가 있으면 요약 아래 한 줄 "- 닫힌 시험 N건 [test_id…] — 채점이 끝난 연습 영상이라 평가에서 빼고 학습 후보로 둔다 (belle 09-26)" 를 더한다. 표·누수 목록 부분은 그대로.
(d) main — 마지막 return 을 `return verdict_code(ev, leaks)` 로 바꾼다. `--mark-holdout` 분기는 그대로 둔다(평가셋이 비면 L1·L2 가 0 이라 기존 조건상 이미 안 돈다 — 새 가드 추가 금지).
(e) 모듈 docstring: 첫 줄의 "봉인 시험지 영상" → "시험 영상", 출처에 quick-261002-kkt 를 더한다. "무엇을 점검하나" 의 평가 항목 줄을 "sealed_tests.jsonl 에서 status != closed 인 시험의 rows(시험 영상) + 짝 + 같은 (subject, session) 클립. closed 시험 영상과 practice 는 연습 영상 → 학습 후보 (belle 09-26)" 로 고친다. "사용" 절에 exit 코드 세 줄을 적는다: 0 = 평가셋 있음 + L1·L2 = 0, 1 = L1 또는 L2 누수, 2 = 평가셋 없음(다음 시험 영상 봉인 전 — 통과 아님).

pytest 녹색 확인 뒤 커밋(코드 + 테스트만): 메시지 예 "fix(eval-split): 게이트 4 — 닫힌 시험 = 연습 영상, 평가셋 없음은 exit 2 (quick-261002-kkt)" + 빈 줄 + "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>". 커밋 해시를 Task 2 에 쓴다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python -m pytest backend/tests/test_eval_split_check.py -q && grep -q 'def verdict_code' backend/scripts/eval_split_check.py && grep -q 'return verdict_code(ev, leaks)' backend/scripts/eval_split_check.py && ! grep -q 'eval_hashes.add(p\[' backend/scripts/eval_split_check.py</automated>
  </verify>
  <done>테스트 파일 전부 통과(6개 테스트, open 확장은 status 3종 parametrize). eval_groups 는 closed 시험 rows 와 practice 를 평가에 안 넣고, verdict_code 가 0/1/2 를 내며 render_report 와 main 이 둘 다 그것을 쓴다. 코드+테스트 커밋 1개.</done>
</task>

<task type="auto">
  <name>Task 2: 오늘 데이터로 재실행해 EVAL-SPLIT.md 재생성 · 전체 테스트 · TRAINING-DUE 게이트 4 행 갱신</name>
  <files>.planning/sealed/EVAL-SPLIT.md, .planning/TRAINING-DUE.md</files>
  <action>
(1) 재실행 — exit 코드가 측정값이므로 rtk 로 감싸지 않는다: `cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python backend/scripts/eval_split_check.py; echo "exit=$?"`. 플래그 없이 한 번만. 기대 exit=2, 보고서에 "평가셋 없음", L1 0 · L2 0. 다르면 멈추고 실제 값을 SUMMARY 에 관측으로 적는다(숫자를 맞추려고 코드를 다시 만지지 않는다). 직후 `git diff --quiet backend/training/data/manifest.json backend/training/data/sealed_tests.jsonl` 로 두 파일 무변경을 확인한다.

(2) 회귀 — `backend/.venv/bin/python -m pytest backend/tests -q -x` (Bash timeout 600000; 이전 기준 약 5833 passed). 10분 안에 안 끝나거나 eval_split_check 와 무관한 파일에서 멈추면, 그 실패 테스트가 eval_split_check 를 import 하지 않는다는 것을 grep 으로 확인하고 "기존 실패 [확인: import 없음]" 으로 SUMMARY 에 적고 고치지 않는다. 전체 실행을 못 마친 경우 "전체 스위트 [미확인] — import 하는 곳은 test_eval_split_check.py 하나뿐 [확인: grep]" 으로 적는다.

(3) `.planning/TRAINING-DUE.md` — 게이트 표의 4번 행(조건 "**인물·세션 분리 평가셋이 있나**")만 고친다. 상태 열 내용을 다음 뜻으로 다시 쓴다(행의 기존 상태 표시 문자 하나는 그대로 두고 새 이모지는 넣지 않는다): "틀 있음 · 정책 코드 반영(10-02, `<Task 1 커밋 해시 8자리>`)" — 평가 항목 = `sealed_tests.jsonl` 에서 안 닫힌 시험(status ≠ closed)의 시험 영상 + 짝 + 같은 인물·세션 클립. 닫힌 시험의 영상과 practice 는 연습 영상 → 학습 후보(belle 09-26 "시험 영상은 배우지 않는다, 나머지는 전부 배운다"; 시험 영상 = 처음 채점하는 영상만). 점검 = `backend/scripts/eval_split_check.py`(L1 같은 파일 · L2 같은 세션 = 오류, L3 같은 인물 = 경고). **10-02 재실행 [확인]: exit 2 평가셋 없음** — 유일한 시험 260925-mvh 가 closed 라 평가 영상 0편, 정은지 실수 fixtures 6편 = 연습 영상 → 학습 후보(L1 0). `sealed_tests.jsonl` 은 이력이라 그대로 두고 status 로 처리한다, `--mark-holdout` 은 안 돌렸다(누수 0이라 필요 없음). **게이트 4 는 다음 시험 영상이 봉인될 때 켜진다** — 다음 후보 = 정은지 중급콤보 영상(belle 09-30: Phase 38 뒤). 인물이 1명뿐이라 **인물 분리는 여전히 불가**. 확인 방법 열은 "`eval_split_check.py` exit 0 (exit 2 = 평가셋 없음 = 통과 아님)". 옛 문구 "sealed_tests.jsonl 에서 빼고" · "정책이 아직 코드에 안 들어갔다" · "현황: 누수" 는 사라져야 한다(사실이 아니게 됐다). (1) 의 실제 결과가 기대와 다르면 행에는 실제 값을 쓴다.
"돌리는 법" 4번을 "**`backend/scripts/eval_split_check.py` 가 exit 0 이어야 한다**(평가셋 있음 + 누수 0. exit 1 = 누수, exit 2 = 평가셋 없음 = 통과 아님 — 다음 시험 영상 봉인 전) → 전 사이클: preflight → label → assemble → train → gates → promote" 로 고친다.
다른 행 · 맨 위 제목 줄 · `<!-- flywheel:counts -->` 마커 줄은 한 글자도 바꾸지 않는다(플라이휠이 그 마커 줄만 덮어쓴다).

(4) 커밋: `.planning/sealed/EVAL-SPLIT.md` + `.planning/TRAINING-DUE.md` 만. 메시지 예 "docs(261002-kkt): 게이트 4 재실행 — exit 2 평가셋 없음, 정은지 실수 6편 = 연습 영상" + 빈 줄 + "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>". git 명령은 rtk 접두.

SUMMARY 는 CLAUDE.md 보고 규칙대로 관측(exit 코드 · L1/L2/L3 건수 · 테스트 수)과 진단을 다른 절에, 문장마다 [확인]/[미확인]. 연습 영상 6편이 실제 다음 학습에 들어가는지는 플라이휠/증류 단계를 안 돌렸으므로 [미확인] 으로 적는다(eligible_for_distill 이 s3_key 보유·holdout 없음 행을 고른다는 것까지만 [확인]). LLM 학습 영향 한 줄: 다음 사이클 증류 후보가 이 6편만큼 늘 수 있다(게이트 3·5·6·7 이 아직 꺼져 있어 지금 학습은 없다).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && (backend/.venv/bin/python backend/scripts/eval_split_check.py >/dev/null; test $? -eq 2) && grep -q '평가셋 없음' .planning/sealed/EVAL-SPLIT.md && ! grep -q '세션 분리 OK' .planning/sealed/EVAL-SPLIT.md && git diff --quiet backend/training/data/manifest.json backend/training/data/sealed_tests.jsonl && grep -q 'flywheel:counts' .planning/TRAINING-DUE.md && grep -q 'exit 2' .planning/TRAINING-DUE.md && ! grep -q '정책이 아직 코드에 안 들어갔다' .planning/TRAINING-DUE.md</automated>
  </verify>
  <done>스크립트 재실행 exit 2, EVAL-SPLIT.md 에 "평가셋 없음" 판정(세션 분리 OK 없음), manifest.json · sealed_tests.jsonl 무변경, 전체 백엔드 테스트 결과(또는 [미확인] 사유)가 SUMMARY 에 기록, TRAINING-DUE 4번 행과 돌리는 법 4번이 갱신되고 마커 줄·다른 행은 그대로. 문서 커밋 1개.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| sealed_tests.jsonl / manifest.json → eval_split_check | 로컬 데이터 원장을 읽는 운영 스크립트. 외부 입력 없음, 네트워크 없음 |
| eval_split_check exit 코드 → 재학습 결정(TRAINING-DUE 돌리는 법 4번) | 이 코드가 "학습해도 되나"의 한 게이트로 읽힌다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-261002-kkt-01 | Tampering (평가 무결성) | eval_groups | mitigate | 안 닫힌 시험(sealed/run/graded)의 영상이 학습 후보로 새면 평가가 오염된다 — open 시험 확장 테스트를 status 3종으로 parametrize 해서 고정, 짝·세션 확장 코드는 안 바꾼다 |
| T-261002-kkt-02 | Repudiation (잘못된 통과) | render_report / main | mitigate | 평가셋 0편이 "세션 분리 OK"/exit 0 으로 읽히는 것 — verdict_code 하나로 보고서 문구와 exit 코드를 같이 정하고, 빈 평가셋 = exit 2 를 테스트로 고정, TRAINING-DUE 4번에 "exit 2 = 통과 아님" 명시 |
| T-261002-kkt-03 | Tampering (이력 손상) | manifest.json · sealed_tests.jsonl | mitigate | 두 파일은 수정 금지 — Task 2 verify 의 `git diff --quiet` 로 무변경 확인, `--mark-holdout` 미실행 |
| T-261002-kkt-04 | Information Disclosure | 정은지님 영상/ 중급콤보 | mitigate | 다음 시험 영상을 미리 보면 시험이 무효 — 폴더 열람·목록·분석 금지(hard_prohibitions) |
</threat_model>

<verification>
- `backend/.venv/bin/python -m pytest backend/tests/test_eval_split_check.py -q` 통과.
- 스크립트 재실행 exit 2, `.planning/sealed/EVAL-SPLIT.md` 판정 줄 = "평가셋 없음 — 다음 시험 영상이 봉인되기 전까지 게이트 4 꺼짐".
- `git diff --quiet backend/training/data/manifest.json backend/training/data/sealed_tests.jsonl` 성공.
- 전체 백엔드 스위트 결과 또는 [미확인] 사유가 SUMMARY 에 있다.
- `.planning/TRAINING-DUE.md` 4번 행 · 돌리는 법 4번만 바뀌었다(`git diff` 로 다른 행 무변경 확인).
</verification>

<success_criteria>
- 닫힌 시험 영상 · practice 영상은 평가셋에 안 들어간다(테스트로 고정).
- 안 닫힌 시험의 짝 · 세션 확장은 그대로다(테스트로 고정).
- 평가셋 0편은 exit 2 + "평가셋 없음" 이고 통과로 안 읽힌다.
- 오늘 데이터 결과 exit 2 · L1 0 이 보고서와 TRAINING-DUE 에 [확인] 으로 남는다.
- 금지 항목(중급콤보 영상 · manifest · sealed_tests.jsonl · --mark-holdout · stopped_at) 전부 미접촉.
</success_criteria>

<output>
Create `.planning/quick/261002-kkt-gate4-holdout-policy-in-eval-split-check/261002-kkt-SUMMARY.md` when done
</output>
