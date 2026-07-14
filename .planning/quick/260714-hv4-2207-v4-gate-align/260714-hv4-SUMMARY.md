---
phase: quick-260714-hv4
plan: 01
subsystem: ml-eval
tags: [phase22, sft-gates, bakeoff, prompt-alignment, vllm]
requires: [22-07 v4 SFT 모델, run_bakeoff 하네스(22-05/06), assert_gates(22-07)]
provides:
  - schema.extract_report_json — thought 스트립 + raw_decode balanced JSON 방어 파서 (단일 진실)
  - run_bakeoff --prompt-mode aligned / --media / --repetition-penalty (opt-in, 기본 legacy 불변)
  - assert_gates._parsed_report 파서 교체 (판정 기준 무변경)
  - run_sft_gates.sh PROMPT_MODE/REPETITION_PENALTY 배선 + aligned video 서빙
  - POD-RECHECK.md — Pod D-15 재계측 커맨드 시퀀스 (오케스트레이터 SSH 실행)
affects: [22-07 게이트 재판정, 22-08 서빙 배선]
tech-stack:
  added: []
  patterns: [opt-in 플래그로 기본 경로 바이트 불변, 방어 파서 단일 함수 공유, auto 모달리티 폴백]
key-files:
  created:
    - .planning/quick/260714-hv4-2207-v4-gate-align/POD-RECHECK.md
  modified:
    - backend/training/datagen/schema.py
    - backend/tests/phase22/test_schema.py
    - backend/evals/phase22/run_bakeoff.py
    - backend/evals/phase22/assert_gates.py
    - backend/tests/phase22/test_bakeoff_harness.py
    - backend/tests/phase22/test_assert_gates.py
    - backend/training/sft/run_sft_gates.sh
decisions:
  - "방어 파서는 schema.extract_report_json 단일 함수 — run_bakeoff aligned 와 assert_gates 공유, 복제 금지"
  - "aligned 는 shots=zero 강제 (few-shot 예시가 legacy 양식이라 학습 분포에 부재)"
  - "rp=1.0 이면 요청 바디 legacy 와 바이트 동일 — repetition_penalty 는 A/B 관찰 전용 노출, 본판정 1.0 고정"
  - "aligned 파싱 실패는 기존과 동일하게 실패 집계 (score_json 비-dict → parse 0.0, 관대화 금지)"
metrics:
  duration: 12min
  completed: 2026-07-14T04:11:26Z
  tasks: 3
  tests: "phase22 237→248 passed (신규 11), 1 skipped 유지"
---

# Quick 260714-hv4: 22-07 v4 게이트 계측-학습 양식 정렬 Summary

aligned 프롬프트 모드(opt-in)로 v4 게이트의 계측-학습 분포 불일치 4겹(모달리티/지시문/시스템/디코딩)을 해소 — 판정 기준 4종은 한 글자도 불완화, 기본 legacy 경로 바이트 불변.

## Tasks

| Task | 내용 | Commits |
|------|------|---------|
| 1 | schema.extract_report_json — thought 스트립 + raw_decode balanced JSON 추출 (TDD) | fbeb661 (RED) / 43420ba (GREEN) |
| 2 | run_bakeoff aligned 모드 + assert_gates 파서 교체 (TDD) | 55e4484 (RED) / e3ef0cc (GREEN) |
| 3 | run_sft_gates.sh PROMPT_MODE/REPETITION_PENALTY 배선 + POD-RECHECK.md | 4f12979 |

## 4겹 정렬 내역

1. **모달리티**: aligned `--media auto|video` 는 vLLM video_url(file://) 시도, BadRequest/4xx 시 frames(image_url 64장) 폴백 전환 후 이후 항목 유지 — 레코드별 `modality`(video/frames/none) 기록. 합성 트랙은 BASE_SYNTH 로컬 영상 존재 시 첨부, 없으면 좌표 단독(정상 폴백).
2. **지시문**: aligned user 텍스트 = `build_jsonl._rtmw_text + _TASK_INSTRUCTION` import 재사용 — 학습 JSONL user 양식과 문자 단위 동일(테스트가 모듈 객체 identity 로 복사 검출).
3. **시스템 프롬프트**: aligned 메시지에 system 롤 0건, 동작명 라인·few-shot 없음, content = media 먼저 → text 마지막(학습 [video, text] 순서 미러).
4. **디코딩**: aligned 리포트 태스크는 response_format 미전송(자유생성 — 학습 타겟이 `<thought>` 프리앰블 허용). 파싱은 extract_report_json. trap 트랙은 aligned 무관 guided enum 유지.

## 판정 기준 불완화 검증

- assert_gates diff = `_parsed_report` 파서 교체(+docstring)만 — check_synthetic_holdout / check_eval18_no_regression / check_traceability_and_monotonicity / check_determinism 의 임계·비교식·SKIPPED 규칙 변경 0건 (git diff 육안 확인).
- legacy 무플래그 경로: 메시지 조립/guided/파싱 로직 분기 밖 — rp=1.0 시 요청 바디도 기존과 바이트 동일(response_format 항상 전송, extra_body 미포함). 테스트 `test_legacy_report_messages_unchanged` 로 고정.
- 파싱 실패 관대화 금지: extract_report_json None → score_json 에 비-dict 전달(parse 0.0), _parsed_report None(실패 의미 동일).

## Deviations from Plan

None - plan executed exactly as written.

## Pod 재계측 (이 plan 범위 밖 — 오케스트레이터 몫)

POD-RECHECK.md 시퀀스: push → Pod pull → **기존 legacy v4 아티팩트 `phase22_legacy_v4/` mv 백업(파일명 동일 규약 — 덮어쓰기 소실 방지)** → `PROMPT_MODE=aligned` 본판정(rp=1.0, `GATES ALLDONE` 마커) → rp=1.05 소규모 A/B(본판정 금지 경고). 현 Pod: xkaejqz9u72osv A100 80GB, `ssh root@213.173.105.9 -p 43181`.

## Known Stubs

None — 신규 경로는 전부 배선 완료. POD-RECHECK.md 는 의도적 커맨드 문서(Pod 실행 없음이 plan 명시 스코프).

## Verification

1. `python3 -m pytest tests/phase22/ -q` — 248 passed, 1 skipped (기존 237 무회귀 + 신규 11).
2. `run_bakeoff.py --dry-run` — ALLDONE + `prompt_mode=legacy` 표기.
3. `bash -n run_sft_gates.sh` — 문법 오류 0, PROMPT_MODE 8회 배선.
4. `_TASK_INSTRUCTION` 문자열 원문은 build_jsonl.py 단일 존재 (복사본 0건 grep 확인).

## Self-Check: PASSED

- FOUND: backend/training/datagen/schema.py (extract_report_json)
- FOUND: backend/evals/phase22/run_bakeoff.py (prompt_mode)
- FOUND: backend/evals/phase22/assert_gates.py (extract_report_json)
- FOUND: backend/training/sft/run_sft_gates.sh (PROMPT_MODE)
- FOUND: .planning/quick/260714-hv4-2207-v4-gate-align/POD-RECHECK.md
- FOUND commits: fbeb661, 43420ba, 55e4484, e3ef0cc, 4f12979
