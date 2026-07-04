# Phase 25 Validation Architecture — vision-pointed 상체 감점 커버리지

**Source:** 25-RESEARCH.md §Validation Architecture (2026-07-04) + plan-check blocker 1 반영.
**원칙:** Nyquist — 모든 태스크 `<verify>` 에 automated 명령. 게이트 = 감점 결과(구조 assert)가 지고, 짚기-FP율은 관측 지표 (OD-2). 특정 점수 assert 금지 (baseline 방향 비교만 허용).

## Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| Config | 없음 (관례: `backend/tests/`) |
| Quick run | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -k "deduction or vision or criteria" -x -q` |
| Full suite | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` — 기존 54 pre-existing fail(app-module-name-collision + gemini/knee env)은 HEAD 대비 diff IDENTICAL 로 회귀 판단 |
| Pod eval | `backend/evals/phase25/run_sweep.py` (phase24 헤더 env 커맨드 승계) — SERIAL 필수 |

## Phase Requirements → Test Map

| Req | Behavior | Test Type | Command / Artifact | Plan |
|-----|----------|-----------|--------------------|------|
| 짚인 관절만 window seed (SCORE-15) | pointed ∩ wm 만 window 값, 나머지 DTW full-path median; pointed=None → 기존 byte-동일 | unit (pure) | `pytest tests/test_deduction_seed_pointed_merge.py -q` | 25-01 T2 |
| 좁은 pointed 매퍼 (OD-1) | shoulder/arm/leg/hip 만 side 해소 방출, line/torso/head_neck/grip 방출 0 | unit (pure) | `pytest tests/test_vision_pointed_mapper.py -q` | 25-01 T1 |
| at_seconds=None 불변 (리서치 함정 ③) | `_collect_vision_fault_context` 호출 인자 무접촉 | diff gate | `git diff HEAD~ -- backend/functions/pipeline/app.py` 에 at_seconds 접촉 0 | 25-01 T2 verify |
| 집계 fragment fold | side/fault_kind fold 후 keypoint_set support 카운트, 대표 규칙 불변 | unit (pure) | `pytest tests/test_gemini_vision_scorer.py -q` (확장) | 25-02 T1 |
| 캐시 버전 bump | AGGREGATION_VERSION + PROMPT_VERSION 이 build_key 에 folding, marker 변경 = 다른 키 | unit | `pytest tests/test_gemini_vision_scorer.py -q` (build_key) | 25-02 T1/T2 |
| 프롬프트 generic (D-06) | 동작명/기대답 하드코딩 0 + differences[] 구조화 지시 포함 | unit (grep-style assert) | `pytest tests/test_gemini_vision_scorer.py -q` | 25-02 T2 |
| 확대 카드 3단 crop + 앵커 | valid→relaxed→full 강하, 카드별 중심 차별화, relaxed/full circle 생략 | unit (합성 프레임) | `pytest tests/test_fault_zoom_relaxed_crop.py -q` | 25-03 |
| 신규 게이트 3종 pod-free | success_100 / pointed_only_window / kipup_upper_structure (합성 fixture) | unit | `pytest tests/test_phase25_eval_gates.py -q` | 25-04 T1 |
| success 6/6==100 + 구조 게이트 + 무퇴행(fault ≤ phase24 baseline) + 결정론 | Pod 6페어 serial sweep cold+warm | integration (Pod, 수동 트리거) | `python3 evals/phase25/assert_gates.py` (artifact-gated) | 25-04 T3 |
| 짚기-FP율 관측 (OD-2, 게이트 아님) | success 멤버 collectObservation 캡처 → report 요약 | observation | phase25_sweep_report.json `collectObservation` | 25-04 T1/T3 |

## Sampling Rate

- **per task commit:** quick run (`-k "deduction or vision or criteria"` 필터) — 신규 FAIL 0
- **per wave:** backend full suite (pre-existing fail diff IDENTICAL) + 앱 접촉 시 `npm run typecheck` (본 phase 는 앱 무접촉 — 계약/스키마 변경 0)
- **phase gate:** Pod 6페어 serial sweep cold+warm — success 6/6==100 AND kip-up 구조 assert AND fault ≤ baseline 방향 무퇴행 AND cold/warm 결정론

## Wave 0 Gaps (플랜에 신설 배정됨)

- `backend/evals/phase25/` harness — phase24 복제 + success-멤버 collect 관측 tee(read-only) + seedObservation 캡처 + 신규 게이트 3 → 25-04 T1
- pointed 매퍼 / seed merge 단위 테스트 파일 (`test_vision_pointed_mapper.py`, `test_deduction_seed_pointed_merge.py`) → 25-01
- fault_zoom relaxed crop 테스트 (`test_fault_zoom_relaxed_crop.py`) → 25-03
- 게이트 자체 unit test (`test_phase25_eval_gates.py`) → 25-04 T1

## Grep/Diff Gates (hygiene: 주석 제외 필터 적용)

- 밴드 재도입 0: `grep -v '^\s*#' backend/functions/pipeline/app.py | grep -c "SEVERITY_CAP\|apply_downward_cap"` == 0
- 채점 무접촉 (25-03): diff 가 fault_zoom.py + 테스트만 — deduction_engine/dimensions/kismam 접촉 0
- at_seconds=None 불변 (25-01): `_collect_vision_fault_context` 호출부 diff 무접촉
