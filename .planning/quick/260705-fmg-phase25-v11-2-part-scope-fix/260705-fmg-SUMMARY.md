---
phase: quick-260705-fmg
plan: 01
subsystem: ml-analysis
tags: [gemini, vision-veto, prompt, phase25]
requires: [phase25 v11.1 (e697364), run5 baseline 승격 (4c452f4)]
provides:
  - "PROMPT v11.2: part_scope 배타(exclusive) 강제 — 부위-전용 판정 + 타 부위 방출 금지"
  - "v11.1 캐시 verdict 무효화 (PROMPT_VERSION bump)"
affects: [pod sweep (kipup_upper (c) 게이트), vision veto 3-scope 집계]
tech-stack:
  added: []
  patterns: ["scope-집중 특정성 상향 (flash-beats-pro 교훈: 진짜 레버 = 프롬프트 특정성)"]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/tests/test_gemini_vision_scorer.py
decisions:
  - "part_scope suffix 를 '참고: 집중' 참고 문구에서 '중요: 부위 전용 판정 + 타 부위 방출 금지' 배타 지시로 교체"
  - "SCHEMA_VERSION v8.1 / AGGREGATION_VERSION agg4 불변 — 프롬프트 문자열만 변경, 집계/라우터/스키마 무접촉"
metrics:
  duration: "~10min"
  completed: 2026-07-05
  tasks: 2
  tests: "178 passed (test_gemini_vision_scorer 85 + test_deduction_engine + test_phase25_eval_gates)"
---

# Quick 260705-fmg: Phase25 v11.2 part_scope 배타 강제 Summary

**One-liner:** Gemini part_scope 호출 프롬프트를 부위-전용 배타 판정으로 강화(v11.2) — 2026-07-05 pod 진단에서 upper_body scope 6회 중 상체 방출 0/하체 중복 방출 4 였던 "집중 참고 문구 무시" 문제를 타-부위 방출 금지 지시로 fix, 동시에 3-scope 하체 중복 방출의 support 자기부풀림(supportCount 3) 차단.

## What Changed

### Task 1 — v11.2 배타 프롬프트 + PROMPT_VERSION bump (commit 673daa5)

- `_call_gemini_comparison` 의 `if part_scope:` suffix 교체:
  - 신규 배타 강제: "이번 호출은 [{label}] 부위 **전용** 판정", differences[] 에 해당 부위 항목만, "다른 부위는 별도 호출이 담당하므로 여기서는 방출 금지", 타 부위 결함(예: 다리/스플릿)은 눈에 띄어도 무시 — generic 신체 부위 표현만 사용(동작명 0, D-06 유지).
  - 순차 점검 구체화: "라벨 괄호 안에 열거된 세부 부위를 하나씩 순서대로 기준 영상과 대조 점검" — `_PART_SCOPE_LABEL` 값의 해부학 열거를 활용, label 별 분기 없음(단일 generic 문구 + {label} 주입).
  - 기존 계약 전부 보존: 관찰-전량 방출("하나도 빠짐없이", 서사-only "누락/금지/무효"), 좌/우 수행자 "신체 기준" + "확실하지 않으면" 생략, 각도쌍 rubric(student/reference_angle_deg + measurement_basis), "1·2번 규칙" 정타 방어("항목을 만들지 말고 빈 배열이 정답").
- `PROMPT_VERSION` "v11.1" → "v11.2" (이력 주석 맨 앞에 근거 1줄 추가). 캐시 키에 포함되므로 v11.1 stale verdict 전부 무효화.
- part_scope=None 경로 byte-동일 (`test_part_scope_none_prompt_unchanged_no_structuring_suffix` 무수정 PASS).

### Task 2 — 테스트 정합 + 배타 문구 테스트 (commit 0b95138)

- `test_prompt_schema_version`: pin v11.2, stale negative 튜플에 "v11.1" 추가.
- `test_part_scope_prompt_exclusive_scope_only` 신규 (섹션 헤더 스타일 준수): 전 `VETO_PART_SCOPES` 에서 "전용" + "다른 부위"/"방출 금지" + "무시" 존재 assert.
- 기존 프롬프트 계약 테스트 3종(구조화 강제/generic 동작명 0/None 경로) 무수정 GREEN — 계약 완화 0.

## Verification

- `PYTHONPATH=shared/python:. python3 -m pytest tests/test_gemini_vision_scorer.py tests/test_deduction_engine.py tests/test_phase25_eval_gates.py -q` → **178 passed, 0 failed**
- `git diff` 범위: gemini_vision_scorer.py + test_gemini_vision_scorer.py 2개 파일만 (집계/라우터/스키마 무접촉 증명)
- `SCHEMA_VERSION = "v8.1"` grep count == 1, `AGGREGATION_VERSION = "agg4"` == 1 (불변 확인)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## PENDING — pod 실효 검증

실효 검증(kip-up fault 페어에서 upper_body scope 가 실제로 어깨 편차를 differences[] 로 방출 → 감점 산출 → run5 게이트 kipup_upper (c) PASS)은 pod sweep 필요 — 본 quick 범위 밖. 다음 pod 세션에서:
1. push 후 pod pull + 서버 재시작 (PROMPT_VERSION bump 로 캐시 자동 무효화, 수동 삭제 불필요)
2. kip-up 페어 fresh sweep — 상체 방출 여부 + supportCount 자기부풀림 감소 확인
3. success 100 유지 (배타 문구가 정타 방어를 밀어내지 않았는지 — 유닛 계약은 GREEN 이나 실측 필수)

## Self-Check: PASSED

- backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py — FOUND (modified)
- backend/tests/test_gemini_vision_scorer.py — FOUND (modified)
- commit 673daa5 — FOUND
- commit 0b95138 — FOUND
- 178 passed 확인
