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

### 1차 sweep verdict (2026-06-05 03:16 UTC — Pod RTX 3090, Firebase SA 미박제)

`sweep_rtmw_2026-06-05T03-16-03-950082+00-00`

| 항목 | 결과 | 박제 |
|---|---|---|
| (A) IPSF within_tolerance | 1/5 (전체) | ref-climb 만 PASS |
| (B) line PASS (채점 영역) | **5/0** | 분모=0 — 모든 영상 motion='auto' → out_of_scope_PASS |
| (C) angle PASS (채점 영역) | **5/0** | 동일 — 분모=0 |
| (D) Gemini 좌표/점수/판단 reject 위반 | 0건 | reject pattern 가드 정상 |
| (E) Gemini motion 분류 정확도 | **0/5** | 5영상 모두 motion='auto' (Firestore SA lookup 실패) |
| (F) Phase 5 게이트 verdict | **fail** | D-01 게이트 = "ref-climb 제외 N/N PASS + ref-climb out-of-scope counted" 정의상 분모 0 통과 불가 |
| (G) startup fail-loud 검증 | PASS | RTMW init + Gemini init OK, log 정상 진행 |

**모션별 결과** (1차):

| 모션 | IPSF | line | angle | ms/f | rtmw_score |
|---|---|---|---|---|---|
| ref-climb | PASS | out_of_scope_PASS | out_of_scope_PASS | 94.8 | 81.1 |
| ref-foxtop | FAIL | out_of_scope_PASS | out_of_scope_PASS | 31.9 | 72.1 |
| ref-foxtop-split | FAIL | out_of_scope_PASS | out_of_scope_PASS | 32.3 | 72.1 |
| ref-invert | FAIL | out_of_scope_PASS | out_of_scope_PASS | 33.1 | 74.7 |
| ref-sideway-spin | FAIL | out_of_scope_PASS | out_of_scope_PASS | 31.9 | 80.3 |

ms/f 평균 44.8 (CPU 박제 ~2000ms 대비 **45배 GPU 가속** ✓).

### 1차 sweep 박제 함정 7종 누적 (commit/fix)

| # | 함정 | Fix |
|---|---|---|
| 12 | mmcv CUDA build single-core 30분+ | setup_pod_full.sh `MAX_JOBS=$(nproc)` (commit f9e7e15) |
| 13 | rtmlib default = onnxruntime CPU only | setup_pod_full.sh onnxruntime-gpu 명시 install |
| 14 | RTMWPoseEngine `device="cpu"` hardcode | commit 50af90b — `RTMW_DEVICE` env var 매개 |
| 15 | onnxruntime-gpu 1.18.x = CUDA 11 미스매치 | 1.19.2 (CUDA 12 + cuDNN 9 native) 명시 |
| 16 | cuDNN 9 system path 미설치 | torch 번들 `LD_LIBRARY_PATH` 박제 |
| 17 | `_load_video_frames` OOM (4K 영상 21GB 전체 로드) | commit 391c933 — `FfmpegFrameExtractor` 위임 (175MB, 120배 감소) |
| 18 | Firebase SA Pod 미박제 → Gemini 학원 용어 매핑 graceful degrade | `FIREBASE_SA_PATH` 박제 + setup_pod_full.sh WARN |

박제 누적 = [[runpod-gpu-env.md]] 함정 1-18 (Plan 11 era 1-5 + Plan 23 6-11 + Plan 5-05 12-18).

### 2차 sweep verdict (2026-06-05 03:45 UTC — Firebase SA 박제 후)

`sweep_rtmw_2026-06-05T03-45-05-503023+00-00`

**결과 = 1차와 동일 (motion='auto' 폴백 유지)**. Firebase SA 박제 영향 0.

| 항목 | 결과 | 박제 |
|---|---|---|
| (A) IPSF within_tolerance | 1/5 (전체) | ref-climb 만 PASS (1차 동일) |
| (B) line PASS (채점 영역) | **5/0** | 분모=0 유지 |
| (C) angle PASS (채점 영역) | **5/0** | 분모=0 유지 |
| (D) Gemini reject 위반 | 0건 | 정상 |
| (E) Gemini motion 분류 정확도 | **0/5** | 5영상 모두 'auto' 유지 |
| (F) Phase 5 게이트 verdict | **fail** | 1차 동일 |
| (G) startup fail-loud 검증 | PASS | 1차 동일 |

소수점 차이 (sampling 변동 + ms/f 약간 다름) 외 결과 변화 0.

### 박제 함정 19 — Gemini recognizer motion_query_hint default 'auto' 박제-코드 정합 위배

2차 sweep 결과 확인 후 코드 path 진단 결과:

- `gemini_technique_recognizer.py:235`: `motion_query = self.motion_query_hint or "auto"`
- `_build_recognizer("gemini")` (compare_rtmw_vs_ipsf.py:697) 가 `motion_query_hint` 안 넘김
- sweep main loop 가 영상 파일명 (`ref-climb`/`ref-foxtop` 등) 알면서도 recognizer 에 안 넘김

흐름:
1. recognizer 가 motion_query='auto' 로 extractor 호출
2. extractor `_last_motion_name = 'auto'` (caller query 그대로 박제 — B5/W3 fix 박제 정신)
3. recognizer 가 `raw_motion_name='auto'` → `classify_motion_name('auto')` → unregistered (REGISTERED_MOTIONS / _ALIAS_TABLE 어디에도 'auto' 없음)
4. → out_of_scope_PASS, D-01 게이트 분모=0

**핵심 진단**: sweep 박제 정신 = "정은지 reference 영상은 motion known case (file name = motion ID)" 인데, `_build_recognizer` 가 motion_query_hint 미박제. 박제 정신과 코드 정합 위배.

### Phase 5 게이트 verdict = FAIL (D-01)

D-01 게이트 = "ref-climb 제외 채점 영역 모션 N/N PASS + ref-climb out-of-scope counted as PASS". 분모 0 = 통과 불가.

후속 fix path 후보 (belle 결정):

| Path | 내용 | 적용 범위 |
|---|---|---|
| **A** | sweep main loop 가 영상별 `recognizer.motion_query_hint = motion_name` 박제 | ref motion known 케이스 (sweep 한정). 단순 (3 line code change). 박제 정신 정합 |
| **B** | Gemini prompt 에 motion 분류 응답 추가 → caller 가 Gemini 응답 motion 사용 | production user upload path. Gemini 의 "auto" 분류 능력 검증 필요 |
| **C** | extractor `_last_motion_name` 가 caller query 아닌 Gemini 응답 반영 | B5/W3 fix 박제 정신 변경. 박제 정신 재의논 필요 |

Path A 가 sweep 즉시 진행 가능 (Phase 5 게이트 재판정). Path B/C 는 production 시점 별 plan.

### 3차 sweep verdict (2026-06-05 04:32 UTC — Path A 적용 후, commit 2ebe8d3)

`sweep_rtmw_2026-06-05T04-32-12-972175+00-00`

**Path A 효과 박제 ✓** = motion 분류 정상화 (out_of_scope_PASS 폴백 0 — 실제 채점 영역 진입). 그러나 D-01 게이트 여전히 FAIL — 새 root cause 3개 박제.

| 항목 | 결과 | 박제 |
|---|---|---|
| (A) IPSF within_tolerance | 1/5 | ref-climb 만 PASS |
| (B) line PASS (채점 영역) | **0/5** | 채점 영역 진입했으나 모두 FAIL |
| (C) angle PASS (채점 영역) | **0/5** | 동일 |
| (D) Gemini reject 위반 | 0건 | 정상 |
| (E) Gemini motion 분류 정확도 | **5/5** | Path A 효과 — 모든 영상 ref motion 매핑 ✓ |
| (F) Phase 5 게이트 verdict | **fail** | 채점 결과 0/5 |
| (G) startup fail-loud 검증 | PASS | 정상 |

**모션별 결과** (3차):

| 모션 | IPSF | line | angle | gap detail |
|---|---|---|---|---|
| ref-climb | PASS | **FAIL** | **FAIL** | yaml hold_moment 빈 list — out_of_scope_PASS 분기 동작 안 함 (함정 20 후보) |
| ref-foxtop | FAIL | FAIL | FAIL | 0/6 within_tol — left_shoulder target 139° vs measured 30.4° (108.6° gap!) yaml target 의문 |
| ref-foxtop-split | FAIL | FAIL | FAIL | 3/6 within_tol — 일부 PASS, right_knee 58.6° gap (target 78.9° vs 137.5°) |
| ref-invert | FAIL | FAIL | FAIL | **5/6 within_tol** — knee 1개 (17.8° gap) 만 FAIL |
| ref-sideway-spin | FAIL | FAIL | FAIL | **5/6 within_tol** — right_knee 1개 (16.9° gap) 만 FAIL |

### 새 root cause 3종 박제 (3차 sweep)

**함정 20 후보 — ref-climb out_of_scope_PASS 분기 동작 안 함**:
- 박제 (B1 fix 2026-06-04 belle) = "ref-climb yaml hold_moment 빈 list → line/angle out_of_scope_PASS counted as PASS"
- 실제 (3차 sweep) = ref-climb `line=FAIL angle=FAIL` + `out-of-scope counted: 0 PASS`
- `compute_line_angle_gates` 의 out_of_scope_PASS 분기 조건 검증 필요 (joint_expectations 가 모두 BENT_OK 일 때 OR yaml hold_criteria 가 빈 list 일 때 — 어느 조건 박제?)

**함정 21 — yaml target vs RTMW measured 큰 갭 (Plan 23 root cause #1 재발현 가능성)**:
- ref-foxtop left_shoulder: target 139.0° vs measured 30.4° = **108.6° gap** (거의 90° 차이)
- 박제 Plan 23 root cause = "yaml hold_moment target=180° 일률 (FallbackRecognizer 한계)". Plan 5-00 에서 정은지 측정값 기준 yaml 박제 후 일부 해소 추정했으나, ref-foxtop 같은 큰 갭은 의문.
- 후보: (a) yaml target 박제값 자체 잘못, (b) RTMW pose 정확도 한계 (특히 head-down 자세), (c) Gemini key moment timestamp 가 wrong frame 선택, (d) 좌/우 swap 같은 정렬 문제

**함정 22 — within_tolerance_all 정의 ("모두 PASS = True") tolerance 임계값 검토**:
- ref-invert / ref-sideway-spin = **5/6 within_tol** (knee 1개 만 17~18° gap 으로 FAIL)
- within_tolerance_all 정의상 1개만 FAIL 이어도 전체 FAIL → 5/6 가 0/5 카운트
- tolerance 임계값 (현재 ±?°) 박제 검토 가능 영역 — 박제 [[judging-baseline-ipsf-code-of-points]] IPSF Code of Points 2024-2025 의 tolerance 정의 lookup 필요

### Path forward 후보 (belle 결정)

| Path | 내용 | 효과 |
|---|---|---|
| **D** | 함정 20 fix — `compute_line_angle_gates` out_of_scope_PASS 분기 코드 path 검증 + B1 fix 정신 정합 | ref-climb 만 PASS 카운트 회복 — D-01 게이트 분모 4, ref-climb out-of-scope counted as PASS |
| **E** | 함정 21 진단 spike — ref-foxtop yaml target ↔ RTMW measured 갭 root cause (a/b/c/d) 정확히 박제 | yaml 자체 fix 필요? RTMW 한계? Plan 5-00 측정값 vs 현재 yaml 정합 검증 |
| **F** | 함정 22 검토 — IPSF tolerance 임계값 박제 정신 검증 ([[ipsf-5-track-scoring]] / IPSF CoP lookup) | ref-invert/sideway-spin 5/6 → 6/6 가능성 — knee 1개 FAIL 의 임계값 의문 |
| **G** | D-01 게이트 정의 자체 재검토 — "N/N PASS" 가 within_tolerance_all (관절 6/6) 인지 IPSF gap counted (관절별 카운트) 인지 | 박제 정신 명확화 후 코드 path 정합 |

D + E + F 3개 동시 진행 필요할 듯 — D 가 가장 단순 (코드 path 1개), E 가 가장 깊음 (Gemini/RTMW/yaml 정합), F 가 belle 정책 결정.

## Commits

- `b59a16a` — feat(05-05): sweep --recognizer gemini flag + GateVerdict tuple (B1 fix)
- `50af90b` — fix(pose-engine): RTMW device hardcode='cpu' → env var (RTMW_DEVICE) — 함정 14 fix
- `391c933` — fix(sweep): _load_video_frames 9fps/640px 다운샘플 회복 (OOM 함정 17 fix)
- `f9e7e15` — chore(pod): setup_pod_full.sh 박제 갱신 — 함정 12,13,15,16,18 누적 fix

## Self-Check

- [x] `backend/research/evaluations/compare_rtmw_vs_ipsf.py` 박제 박제
- [x] `backend/tests/test_compare_rtmw_vs_ipsf_recognizer_flag.py` 박제 박제
- [x] commit `b59a16a` 존재 확인

## Self-Check: PASSED
