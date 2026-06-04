---
phase: 05-gemini
plan: 05
subsystem: backend/research/evaluations
tags: [sweep, cli-flag, gemini, gate-verdict, b1-fix, blocking-human-checkpoint]
requires:
  - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py (Plan 5-01)
  - backend/shared/python/sunity_shared/analysis/technique_cache.py (Plan 5-02)
  - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py (Plan 01-13)
  - backend/shared/python/sunity_shared/firestore_admin.py (record_unregistered_keyword, Plan 5-02)
provides:
  - 'compare_rtmw_vs_ipsf.py --recognizer {fallback,gemini} CLI flag (Plan 5-05)'
  - 'GateVerdict 3-state literal (PASS/FAIL/out_of_scope_PASS, B1 fix)'
  - 'gate_passed / is_in_scope helper (verdict counter)'
  - 'compute_line_angle_gates(recognizer, video_path) DI (Plan 5-05)'
  - '_build_recognizer factory (D-16 lazy import 박제)'
  - 'phase5_ready_to_release_d16_block report field'
affects:
  - backend/research/evaluations/compare_rtmw_vs_ipsf.py (sweep main loop + GateVerdict 박제 + Recognizer report header)
  - backend/tests/test_compare_rtmw_vs_ipsf_recognizer_flag.py (신설 12 tests, 293 lines)
tech-stack:
  added: []
  patterns:
    - 'Argparse choices 강제 (default=fallback, 회귀 보존)'
    - 'Factory + DI (recognizer 1회 생성 + 5영상 loop 재사용 → cache hit 효과)'
    - 'Literal 3-state verdict (PASS / FAIL / out_of_scope_PASS) — bool 박제 X'
    - 'D-16 lazy import (gemini path 만 google.genai/firebase_admin import)'
key-files:
  created:
    - backend/tests/test_compare_rtmw_vs_ipsf_recognizer_flag.py
  modified:
    - backend/research/evaluations/compare_rtmw_vs_ipsf.py
decisions:
  - 'B1 fix 박제 (2026-06-04 belle 박제 결정): GateVerdict = Literal["PASS","FAIL","out_of_scope_PASS"]. ref-climb yaml hold_moment 빈 list → out_of_scope_PASS counted as PASS (D-20 박제 정신 정합). 강등 X, 정의 정확화 ([[gap-and-line-angle-mandatory-gates]])'
  - 'Phase 5 게이트 정의 = "ref-climb 제외 채점 영역 모션 N/N PASS + ref-climb out-of-scope counted" (D-01 박제 정신 + B1 fix 정합)'
  - 'default=fallback 박제 (Plan 11/23 박제 보존, 회귀 0)'
  - '_build_recognizer 가 D-16 lazy import 정합 — gemini 선택 시점에만 google.genai/firebase_admin import'
  - 'recognizer 1회 생성 + 5영상 loop 안 재사용 (D-14 cache 박제 효과 보존)'
metrics:
  duration: 7m24s
  completed: 2026-06-04
  tasks_completed: 1
  tasks_total: 2
  tests_added: 12
  tests_passed: 23
  files_created: 1
  files_modified: 1
checkpoint_status: 'Task 2 = blocking-human checkpoint emit. belle Pod sweep 미실행 (orchestrator + belle 후속 처리).'
---

# Phase 5 Plan 5: Sweep --recognizer Gemini Flag + Belle Pod Verdict Summary

Plan 5-05 Task 1 박제 — `compare_rtmw_vs_ipsf.py` sweep CLI 에 `--recognizer
{fallback,gemini}` flag + GateVerdict 3-state literal (B1 fix) + 단위 테스트 12 PASS.
Task 2 = belle Pod sweep verdict checkpoint (blocking-human) 으로 emit, 별 path 처리.

## What was built (Task 1)

### 1. `compare_rtmw_vs_ipsf.py --recognizer` CLI flag

- argparse `--recognizer {fallback,gemini}` 추가. default = `fallback` (Plan 11/23
  박제 보존, 회귀 0).
- `--recognizer foo` 같은 잘못된 값 = SystemExit (argparse choices 강제).
- B7 fix 정합 — 기존 `--videos` / `--output-dir` flag 호환 보존 (`--motions` /
  `--output` 신설 박제 X).

### 2. `_build_recognizer(name)` factory (D-16 lazy import)

```python
def _build_recognizer(name: str) -> Any:
    if name == "gemini":
        # D-16 lazy import — gemini 선택 시점에만.
        from sunity_shared.analysis.gemini_technique_recognizer import GeminiTechniqueRecognizer
        from sunity_shared.analysis.technique_cache import TechniqueCache
        from sunity_shared.judging import GeminiMomentExtractor
        from sunity_shared import firestore_admin
        return GeminiTechniqueRecognizer(
            extractor=GeminiMomentExtractor(),
            cache=TechniqueCache(),
            unregistered_hook=lambda kw, vh: firestore_admin.record_unregistered_keyword(
                kw, uid="sweep-rtmw-gemini", video_hash=vh,
            ),
        )
    return FallbackRecognizer()
```

박제 정신:
- D-09 case 3 — `unregistered_hook` 박제 (자동 수집 트리거).
- D-14 — `TechniqueCache` 박제 (sweep 재실행 시 cache hit).
- D-16 — `gemini` 선택 시점에만 google.genai / firebase_admin import.

### 3. `compute_line_angle_gates` GateVerdict tuple (B1 fix)

기존 시그너처:
```python
def compute_line_angle_gates(joint_angles, pole_axis) -> tuple[bool, bool]:
```

신 시그너처 (Plan 5-05 박제):
```python
GateVerdict = Literal["PASS", "FAIL", "out_of_scope_PASS"]

def compute_line_angle_gates(
    joint_angles: np.ndarray,
    pole_axis: PoleAxis,
    recognizer: Any = None,
    video_path: str | None = None,
) -> tuple[GateVerdict, GateVerdict]:
    if recognizer is None:
        recognizer = FallbackRecognizer()
    profile = recognizer.recognize(joint_angles, frames=video_path)
    # B1 fix 박제 — ref-climb 같이 yaml hold_moment 빈 list 박제 시 out_of_scope_PASS.
    if not profile.joint_expectations:
        return "out_of_scope_PASS", "out_of_scope_PASS"
    ls = line_score(joint_angles, profile)
    line_verdict = "PASS" if (ls is not None and ls >= 50) else "FAIL"
    ss = stability_score(joint_angles)
    angle_verdict = "PASS" if ss >= 50 else "FAIL"
    return line_verdict, angle_verdict
```

박제 정신:
- D-20 정합 — ref-climb 차원 별 phase 책임, sweep 게이트에서 PASS counted.
- [[gap-and-line-angle-mandatory-gates]] "강등/우회 금지" 정신 정합 = 정의 정확화
  (강등 X, 채점 영역 모션은 그대로 PASS/FAIL 박제).
- 회귀 보존 — `recognizer=None` default → FallbackRecognizer (기존 호출자 호환).

### 4. `gate_passed` / `is_in_scope` helper

```python
def gate_passed(verdict: GateVerdict) -> bool:
    return verdict in ("PASS", "out_of_scope_PASS")

def is_in_scope(verdict: GateVerdict) -> bool:
    return verdict != "out_of_scope_PASS"
```

`gate_passed` = verdict counter (X/N 산정 시 out_of_scope_PASS counted).
`is_in_scope` = 분모 N 산정 (채점 영역 모션 수).

### 5. SweepReport + write_report 박제 갱신

- `SweepReport` 박제 = `recognizer` / `line_verdicts` / `angle_verdicts` 필드 추가.
- JSON summary 박제 = `phase5_ready_to_release_d16_block` (recognizer=gemini +
  ready_to_swap=True 시 True), `line_inscope_count` / `out_of_scope_count` 박제.
- Markdown header 박제 = `**Recognizer:** {fallback|gemini}` + B1 fix 박제 정의 정리
  blockquote + verdict 표 분자/분모 정의 정확화 (`out-of-scope counted as PASS`).
- 모션별 결과 표 박제 = `line verdict` / `angle verdict` 컬럼 (3-state literal).

### 6. 단위 테스트 (12 tests, 293 lines)

`backend/tests/test_compare_rtmw_vs_ipsf_recognizer_flag.py`:

| # | 테스트 | 박제 |
|---|---|---|
| 1 | `test_recognizer_flag_default_is_fallback` | argparse default 박제 (회귀 보존) |
| 2 | `test_recognizer_flag_accepts_fallback` | fallback 인식 |
| 3 | `test_recognizer_flag_accepts_gemini` | gemini 인식 |
| 4 | `test_recognizer_flag_rejects_invalid` | choices 강제 (SystemExit) |
| 5 | `test_build_recognizer_fallback` | FallbackRecognizer instance |
| 6 | `test_build_recognizer_gemini` | GeminiTechniqueRecognizer + cache + hook |
| 7 | `test_compute_line_angle_gates_default_recognizer_none` | recognizer=None default |
| 8 | `test_compute_line_angle_gates_uses_injected_recognizer` | mock 주입 검증 |
| 9 | `test_compute_line_angle_gates_out_of_scope_when_no_joint_expectations` | B1 fix out_of_scope_PASS 분기 |
| 10 | `test_gate_passed_counts_pass_and_out_of_scope` | B1 fix verdict counter |
| 11 | `test_is_in_scope_excludes_out_of_scope` | B1 fix 분모 산정 |
| 12 | `test_compute_line_angle_gates_passes_video_path_to_recognizer` | video_path frames 전달 |

## Verification

```
cd backend
python3 -m pytest tests/test_compare_rtmw_vs_ipsf_recognizer_flag.py \
                 tests/test_compare_rtmw_vs_ipsf_smoke.py \
                 tests/test_compare_rtmw_vs_ipsf_pole_axis.py -q
# → 23 passed in 0.15s (12 new + 11 existing, 회귀 0)
```

`--help` 출력 검증 (B7 fix):
```
--videos VIDEOS [VIDEOS ...]
--output-dir OUTPUT_DIR
--recognizer {fallback,gemini}
```
`--motions` / `--output` flag 박제 X 확인.

## Acceptance Criteria

- [x] `compare_rtmw_vs_ipsf.py` 에 `--recognizer` flag 박제 (grep count = 3)
- [x] `_build_recognizer` 함수 박제 (grep count = 1)
- [x] `compute_line_angle_gates` 시그너처에 `recognizer=` + `video_path=` 인자 추가
- [x] default = fallback 박제 정합 (argparse default 검증)
- [x] B7 fix 검증 — `--videos` / `--output-dir` flag 호환 보존
- [x] B1 fix 검증 — GateVerdict tuple + `gate_passed` / `is_in_scope` helper + ref-climb 단위 시험 PASS
- [x] test 파일 신설 (line count = 293, 함수 = 12 개)
- [x] `pytest tests/test_compare_rtmw_vs_ipsf_recognizer_flag.py -x` PASS
- [x] 기존 sweep smoke + pole_axis 테스트 회귀 0 (11 PASS 보존)
- [x] report.md 박제 헤더 = `**Recognizer:**` + `phase5_ready_to_release_d16_block` 필드

## Deviations from Plan

None — Task 1 plan 박제 정신 그대로 박제. 환경 박제: 로컬 macOS 에 PyYAML 미설치
→ `pip install --break-system-packages 'pyyaml>=6'` 박제 후 회귀 테스트 환경 박제 (코드 변경 0).

## Task 2 — CHECKPOINT REACHED (blocking-human)

Task 2 = `checkpoint:human-verify gate="blocking-human"` — belle Pod sweep
`--recognizer gemini` 실행 + verdict 박제 + Phase 5 게이트 판정. executor 는 emit
후 STOP. orchestrator 가 belle 와 함께 직접 SSH path 처리 (executor scope 외).

박제 결정 항목 (A)~(G) 박제 후 본 SUMMARY.md 박제 = orchestrator 가 보강.

## Commits

- `b59a16a` — feat(05-05): sweep --recognizer gemini flag + GateVerdict tuple (B1 fix)

## Self-Check

- [x] `backend/research/evaluations/compare_rtmw_vs_ipsf.py` 박제 박제
- [x] `backend/tests/test_compare_rtmw_vs_ipsf_recognizer_flag.py` 박제 박제
- [x] commit `b59a16a` 존재 확인

## Self-Check: PASSED
