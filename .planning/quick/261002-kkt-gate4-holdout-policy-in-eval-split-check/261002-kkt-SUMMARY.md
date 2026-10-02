---
phase: quick-261002-kkt
plan: 01
subsystem: training-data (재학습 게이트 4 — 평가셋 분리 점검)
tags: [phase-37, continuous-learning, eval-split, holdout-policy, training-due]
requires: [quick-260925-nnt eval_split_check 틀 · belle 09-26 holdout 정책 · sealed_test.py status 수명]
provides:
  - eval_split_check.eval_groups — status != closed 인 시험의 rows 만 평가 해시, practice 미포함, 반환에 closed(test_id 목록)
  - eval_split_check.verdict_code(ev, leaks) -> 0/1/2 (보고서 판정 줄과 main exit 코드 공용)
  - .planning/sealed/EVAL-SPLIT.md 10-02 재생성본 (평가셋 없음, exit 2)
  - TRAINING-DUE 게이트 4 행 · 돌리는 법 4번 exit 코드 뜻
affects: [TRAINING-DUE 게이트 4, 다음 재학습 사이클 증류 후보(manifest eligible 행), 다음 시험 영상 봉인]
tech-stack:
  added: []
  patterns: [판정 코드 단일화(보고서 문구 = exit 코드), 빈 입력은 통과가 아니라 별도 코드]
key-files:
  created: []
  modified:
    - backend/scripts/eval_split_check.py
    - backend/tests/test_eval_split_check.py
    - .planning/sealed/EVAL-SPLIT.md
    - .planning/TRAINING-DUE.md
decisions:
  - "시험 영상 = 안 닫힌 시험(status sealed/run/graded, status 없음 포함)의 rows 만. closed 시험 영상과 practice 는 연습 영상 → 학습 후보 (belle 09-26 '시험 영상은 배우지 않는다, 나머지는 전부 배운다')"
  - "평가셋 0편 = exit 2 '평가셋 없음 — 다음 시험 영상이 봉인되기 전까지 게이트 4 꺼짐'. 누수 0 이어도 통과(exit 0)로 안 읽힌다"
  - "sealed_tests.jsonl 은 이력이라 안 고치고 status 로 코드에서 처리. --mark-holdout 은 안 돌렸다(누수 0)"
  - "'인물 분리 불가' 단락은 평가 인물이 정확히 1명일 때만 — 0명에 '1명뿐(정은지)' 은 거짓"
metrics:
  started: 2026-10-02T05:53:08Z
  completed: 2026-10-02
  tasks: 2
  files: 4
requirements: [QUICK-261002-kkt]
---

# Quick 261002-kkt: 게이트 4 — 닫힌 시험 = 연습 영상, 평가셋 없음 = exit 2 Summary

belle 09-26 holdout 정책을 `eval_split_check.py` 에 넣었다. 이제 안 닫힌 시험의 영상만 평가로 보고, 평가셋이 0편이면 "세션 분리 OK"(exit 0)가 아니라 "평가셋 없음"(exit 2)으로 판정한다. 오늘 데이터로 다시 돌리니 exit 2 였다. 정은지 실수 fixtures 6편은 L1 누수에서 빠져 학습 후보로 남았다.

## 커밋

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | eval_groups 정책 + verdict_code + render_report/main 연결 + 테스트 | `179d1392` |
| 2 | EVAL-SPLIT.md 재생성 + TRAINING-DUE 게이트 4 행 · 돌리는 법 4번 | `486d5f5f` |

## 관측 (잰 값 · 코드 사실 — 승계 가능)

- [확인] `backend/tests/test_eval_split_check.py`: 8 passed (6 함수, 안 닫힌 시험 확장 테스트가 status sealed/run/graded 3개로 parametrize).
- [확인] RED: 고치기 전 코드에 새 테스트를 돌리면 4 failed · 4 passed 였다. 실패 = `verdict_code` 없음(AttributeError) 과 옛 규칙(닫힌 시험·practice 를 평가에 넣음). 통과 = 안 닫힌 시험 확장 3개 + `test_leak_levels` — 이번에 바꾸지 않는 동작이라 처음부터 통과하는 게 맞다.
- [확인] 재실행 `backend/.venv/bin/python backend/scripts/eval_split_check.py; echo "exit=$?"` (rtk 없이, 플래그 없이) → **exit=2**.
- [확인] 보고서 숫자: 학습 후보 577행 · 시험 영상 0편 · 평가 그룹 [] · 평가 인물 [] · 평가 그룹 클립 0편 · 닫힌 시험 1건 ['260925-mvh'] · L1 0 · L2 0 · L3 0.
- [확인] 판정 줄 = `판정: 평가셋 없음 — 다음 시험 영상이 봉인되기 전까지 게이트 4 꺼짐`. "세션 분리 OK" 와 "인물 분리 불가" 는 보고서에 없다.
- [확인] 바로 뒤 `git diff --quiet backend/training/data/manifest.json backend/training/data/sealed_tests.jsonl` → 0 (두 파일 무변경). `--mark-holdout` 은 실행하지 않았다.
- [확인] 커밋된 EVAL-SPLIT.md 의 시각은 `2026-10-02T05:55:19+00:00` 이다. 계획의 Task 2 자동 verify 가 스크립트를 한 번 더 돌려서 05:54:35 판을 덮었고, 두 번째 실행도 exit 2 였다(`test $? -eq 2` 통과). 시각을 빼면 내용은 같다.
- [확인] TRAINING-DUE.md 는 diff 상 2줄만 바뀌었다(게이트 4 행 · 돌리는 법 4번). `<!-- flywheel:counts -->` 마커 줄, 제목 줄, 다른 행은 그대로다. 옛 문구("정책이 아직 코드에 안 들어갔다" · "sealed_tests.jsonl 에서 빼고" · "현황: 누수" · "봉인 시험지")는 파일에서 0건이다(grep).
- [확인] `eval_split_check` 를 import 하는 파일은 `backend/tests/test_eval_split_check.py` 하나뿐이다(grep, backend/ 전체 *.py).
- [확인] `gemini_teacher.eligible_for_distill` 은 holdout 있는 행을 빼고, s3_key 없는 행을 빼고, 고객 소스는 anonymized=true 만 통과시킨다(코드 544행~).
- [확인] 전체 백엔드 스위트 `backend/.venv/bin/python -m pytest backend/tests -q -x` (rtk test 래퍼) → **5860 passed, 20 skipped**, 98 warnings, 61초, exit 0. 실패 0이다(계획의 이전 기준은 약 5833 passed).

## 진단 (왜 그런가 — 승계 전 재검증 대상)

- [확인] exit 2 가 나온 이유: sealed_tests.jsonl 의 시험이 260925-mvh 하나뿐이고 status 가 closed 다. 그래서 평가 해시가 비고, 짝·세션 확장이 시작되지 않는다. 그 결과 groups·subjects·clips 가 모두 비어 L1·L2·L3 이 0 이다.
- [확인] 옛 판정 L1 6 이 0 이 된 이유: 옛 코드는 닫힌 시험 rows 2편에서 시작해 짝을 붙이고 (sub_je, 2026-06-17) 세션 전체 12편으로 넓혔다. 새 코드는 그 시작점(닫힌 시험 rows)을 평가로 보지 않는다.
- [확인] L3 11 → 0 은 reference 11편이 "분리됐다"는 뜻이 아니다. 평가 인물이 0명이라 같은 인물을 찾을 대상이 없어서다. 다음 시험 영상이 정은지 영상으로 봉인되면 reference 11편은 다시 L3 경고로 나올 것이다 — 코드 규칙상 예상이며 실행은 안 했다 [미확인].
- [미확인] 연습 영상 6편이 실제로 다음 학습에 들어가는지는 모른다. 플라이휠·증류 단계를 돌리지 않았다. 확인한 것은 두 가지뿐이다: eligible_for_distill 의 선택 규칙(위 관측)과, 옛 보고서에서 이 6편이 L1(= eligible 행)으로 잡혔다는 점.
- [확인] 게이트 4 는 여전히 꺼져 있다. 다음 시험 영상이 봉인되어야 평가셋이 생긴다. 인물이 1명뿐이라 인물 분리도 여전히 할 수 없다.

## LLM 학습 영향

다음 사이클의 증류 후보가 이 6편만큼 늘 수 있다 [미확인 — 증류 미실행]. 지금은 학습이 없다. 게이트 3·5·6·7 이 꺼져 있다(TRAINING-DUE 표) [확인].

## Deviations from Plan

없다. 계획대로 실행했다. 참고 2건:
- 계획의 Task 1 verify/커밋 지시("코드 + 테스트만, 커밋 1개")를 따라 RED 를 따로 커밋하지 않았다. RED 실패는 위 관측에 실행 결과로 남겼다.
- eval_groups 루프는 계획의 key_link 패턴(`!= "closed"`)에 맞춰 `if status != "closed": rows 추가 / else: closed 목록` 형태로 썼다. 동작은 계획 (a) 그대로다.

## TDD Gate Compliance

RED 를 확인했다(4 failed). 다만 별도 `test(...)` 커밋은 없다 — 계획이 코드와 테스트를 한 커밋으로 묶으라고 했다. GREEN 은 `179d1392`(fix 타입)이고, REFACTOR 는 없다.

## Known Stubs

없음.

## 금지 항목 점검

- [확인] `정은지님 영상/` 과 중급콤보 영상은 열지도, 목록을 보지도, 분석하지도 않았다.
- [확인] manifest.json 과 sealed_tests.jsonl 은 무변경이다(git diff --quiet).
- [확인] `--mark-holdout` 은 실행하지 않았다.
- [확인] STATE.md `stopped_at` 과 ROADMAP.md 는 건드리지 않았다.

## Self-Check: PASSED

- 파일 5개 존재(스크립트 · 테스트 · EVAL-SPLIT.md · TRAINING-DUE.md · 이 SUMMARY), 커밋 179d1392 · 486d5f5f 존재(git log --all). 스텁 패턴 0건.
