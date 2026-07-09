---
phase: 22-custom-vlm-finetune
plan: 05
subsystem: testing
tags: [bake-off, vlm, eval-harness, qwen, internvl, grounding-l2, circulareval, guided-json]

# Dependency graph
requires:
  - phase: 22-01
    provides: schema.py (REPORT_KEYS / bind_key_prompt / normalize_report / select_frame_indices) + perturb.py (perturb_sequence / make_temporal_trap)
  - phase: 22-02
    provides: training/data/manifest.json (동작별 소스 풀 + A2/A3 hard-negative holdout)
provides:
  - "bake-off 하네스 run_bakeoff.py — 4축 순수 계측(grounding L2 / temporal CircularEval / json parse·EM·CER / coaching blind judge) + run_sweep 규율 승계"
  - "평가 미니셋 manifest.yaml — real(균등) + hard_negative + synthetic_grounding + trap 4 타입 37 항목"
  - "pod-free 단위 테스트 19건 — 계측 수학이 Pod 실행 전 확정"
affects: [22-06, 22-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "bake-off 계측은 순수 함수(모델 호출 없음) — Pod 실행부는 배선만, 22-06 이 채움"
    - "grounding L2 = synthetic_grounding 트랙 전용(실영상 정답 좌표 부재, Open Question 1)"
    - "judge 는 주입 가능 callable — mock 으로 블라인드성 pod-free 검증"

key-files:
  created:
    - backend/evals/phase22/fixtures/manifest.yaml
    - backend/evals/phase22/run_bakeoff.py
    - backend/tests/phase22/test_bakeoff_harness.py
  modified: []

key-decisions:
  - "모델 백엔드 = vLLM OpenAI 호환 endpoint + --model 파라미터화(후보 ID 는 22-06 확정, 추측 하드코딩 금지)"
  - "guided JSON(response_format json_schema)로 포맷 변수 통제 — 순수 추론력만 비교"
  - "F2 svg_spec wellformedness 는 선정 축 아닌 관측치 — 정식 게이트는 SFT 후 22-07"

patterns-established:
  - "EVAL_OUT_DIR repo-밖 강제 + SERIAL + _meta provenance + cold re-run + ALLDONE (run_sweep 승계)"
  - "schema.bind_key_prompt / normalize_report 재사용으로 학습·서빙·bake-off 프롬프트 일치"

requirements-completed: [FT-01]

# Metrics
duration: 33min
completed: 2026-07-09
---

# Phase 22 Plan 05: Bake-off 하네스 + 평가 미니셋 Summary

**Qwen 3.6-VL-8B vs InternVL 3.5-8B bake-off 의 4축 계측 하네스(grounding L2 / 시계열 CircularEval / JSON 준수 / 코칭 블라인드 judge)와 균등·함정 포함 평가 미니셋을 로컬에서 pod-free 로 완성 — 22-06 은 실행·판정만 수행**

## Performance

- **Duration:** ~33 min
- **Started:** 2026-07-09
- **Completed:** 2026-07-09
- **Tasks:** 3
- **Files created:** 3

## Accomplishments
- **평가 미니셋 박제** — `manifest.yaml` 37항목 4타입: real(등록5+climb+미보유8, 14동작 균등, kip-up 최다 아님) / hard_negative(A2 피터팬·A3 power-spin 위양성 함정) / synthetic_grounding(perturb 원좌표 정답, grounding L2 유일 트랙) / trap(역재생·셔플 shortcut 검출).
- **4축 계측 하네스** — `run_bakeoff.py` 순수 계측 함수 4종 + F2 svg 관측 함수. run_sweep 규율(EVAL_OUT_DIR repo-밖 강제·SERIAL·_meta provenance·temp0 결정성·ALLDONE·Pod env 헤더) 승계. 모델 백엔드(vLLM)·judge(gemini) 는 lazy — import-time GPU/네트워크 0.
- **pod-free 검증** — 19 단위 테스트로 계측 수학(L2 / EM·CER / CircularEval / judge 블라인드 / 라우팅)을 Pod 실행 전 확정. phase22 전체 55 passed / 2 skipped.

## Task Commits

1. **Task 1: eval 미니셋 매니페스트** - `0e6b5fb` (feat)
2. **Task 2: run_bakeoff.py 4축 계측 하네스** - `62fc02c` (feat)
3. **Task 3: 계측 함수 pod-free 단위 테스트** - `f6c9308` (test)

_TDD 노트: 플랜 태스크 순서가 Task 2(하네스 구현) → Task 3(하네스 테스트)로 test-after 를 명시함. Task 3 은 tdd="true" 이나 계측 함수가 Task 2 에서 이미 존재하므로 RED 단계 없이 즉시 GREEN(19/19). 순수 계측 로직이라 회귀 방어가 목적 — 별도 feat 커밋은 Task 2 가 담당._

## Files Created/Modified
- `backend/evals/phase22/fixtures/manifest.yaml` - 평가 미니셋(4타입 37항목 + _meta 카운트 표/객관성/grounding scope/serial 규율)
- `backend/evals/phase22/run_bakeoff.py` - 4축 계측 하네스(순수 함수 + Pod 실행 골격, 계측 함수 배선만 확정하고 추론부는 22-06)
- `backend/tests/phase22/test_bakeoff_harness.py` - 계측 함수 pod-free 검증 19건

## Decisions Made
- **모델 ID 파라미터화** — 정확한 HF/ms-swift 모델 ID 는 22-06(RESEARCH A6) 확정. `--model` 인자 + `BAKEOFF_MODEL` env 로 파라미터화하고 추측 ID 를 사실로 하드코딩하지 않음(승자 미가정, 양 백본 공정 비교).
- **grounding=합성 전용** — 실영상엔 진짜 정답 좌표가 없어 grounding L2 는 synthetic_grounding 트랙(perturb 원좌표 자가 라벨)에서만 계측. 실영상 좌표 정확도는 shadow 일치율로 대리(Open Question 1, 하네스 docstring + manifest _meta 에 명시).
- **guided JSON 포맷 통제** — vLLM `response_format` json_schema 로 최상위 키 집합 강제(값 스키마는 느슨). 정규식 파싱 대신 guided decoding(22-RESEARCH "Don't Hand-Roll").
- **judge 주입 설계** — score_coaching 이 judge callable 을 주입받아 mock 으로 블라인드성(모델명 미포함)을 pod-free 로 검증.

## Deviations from Plan

None - plan executed exactly as written.

_Task 2 verify 명령이 `sys.path` 에 backend/shared/python 만 주입하나 run_bakeoff 는 backend/training(schema)도 필요 — 하네스가 HERE 기준으로 shared/python·backend·training 3경로를 자체 주입해 해결(구조 정합, 신규 의존/우회 없음). 이는 run_sweep 의 self-inject 패턴과 동일._

## Issues Encountered
- 초안 `_meta` 카운트(총 38/real 22)가 실제 항목 수(37/21)와 불일치 → 실측 카운트로 교정하고 self-consistency 검증 추가(`total_items == len(items)`, `type_counts.real == real 항목 수`). 커밋 전 해소.

## Known Stubs
- `run_bakeoff.main()` 의 항목별 추론 루프는 Pod 실행부(S3 프레임 준비 + caller 호출 + 4축 계측)를 **의도적으로 미구현**으로 남김 — 22-06 스코프(실 GPU 추론). 로컬(22-05)은 `--dry-run`(계측 로드 + 미니셋 라우팅, ALLDONE)과 단위 테스트로 pod-free 검증. 계측 함수·규율·계약은 완성 상태이며, 22-06 은 이 루프만 채워 실행·판정한다. 하네스 docstring + 코드 주석에 "22-06 이 채움" 명시.

## Threat Flags
None - 신규 네트워크 endpoint/인증 경로/스키마 변경 없음. 모델 출력 파싱(T-22-14)은 schema.normalize_report 화이트리스트로 감점 계측(크래시 아님), 리포트 _meta 는 runId/model_id/버전 화이트리스트(T-22-15).

## User Setup Required
None - 로컬 계측기·미니셋만. 실 추론 env(vLLM serve + GEMINI_API_KEY + EVAL_OUT_DIR)는 22-06 Pod 실행 시 하네스 docstring 참조.

## Next Phase Readiness
- **22-06(Pod bake-off 실행) 진입 준비 완료** — 계측기·미니셋·규율이 pod-free 로 확정. 남은 것은 Pod 에서 후보 백본 순차 serve + main() 추론 루프 채우기 + 4축 판정.
- **경계**: 정확한 모델 ID(RESEARCH A6), 프레임 서브샘플 실측 정합(9fps↔VLM), few-shot 예시 3개 실데이터는 22-06 에서 확정. hard_negative A2/A3 영상 relocate(fixtures/phase22/hard_negative/)도 22-06 선행.

## Self-Check: PASSED

- Files: FOUND manifest.yaml / run_bakeoff.py / test_bakeoff_harness.py
- Commits: FOUND 0e6b5fb / 62fc02c / f6c9308
- `pytest backend/tests/phase22 -x -q`: 55 passed, 2 skipped (pod-free, no GPU/network/Pod)
- run_bakeoff import 가능 + EVAL_OUT_DIR repo-밖 강제 로직 존재 + Pod env 헤더 docstring 존재
- 모듈 top-level 에 torch/openai/google import 없음(lazy)

---
*Phase: 22-custom-vlm-finetune*
*Completed: 2026-07-09*
