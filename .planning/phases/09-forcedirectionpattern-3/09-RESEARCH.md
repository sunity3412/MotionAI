# Phase 09: ForceDirectionPattern + 실패 원인 후보 3개 — Research

**Researched:** 2026-06-10
**Domain:** Force-pattern inference layer (pure-function, deterministic) over Phase 8 / 8.1 산출 (`ForceSignalsReport`)
**Confidence:** HIGH (모든 input contract / 패턴 / 인접 phase 산출 직접 inspect 후 합성)

## Summary

Phase 9 는 **Layer 1 단독 추론 layer** 다. `ForceSignalsReport` (Phase 8/8.1 umbrella) 의 4 metric + 5 phase boundary 위에 deterministic 6 signal detector → 5-pattern enum 매핑 → Top-3 ranking 을 적용하고, 18 canned KO interpretation 으로 카드 데이터를 emit 한다. RunPod / Gemini / Cerebras 호출은 **영구 차단** — pure function + numpy 만으로 모든 경로 검증 가능하며 (Wave 2 production sweep OUT of scope), 단위 test + 3-way schema lockstep + Firestore scoped validator + 금지 표현 grep gate 가 회귀 차단의 4 축이다.

Phase 8.1 D-05 의 **raw signal only guard** (Codex C-M4 정합) 는 본 phase 의 핵심 제약이다: `axisMetrics[*].severity` 직접 trust 절대 금지 — raw `shoulder_tilt` / `hip_tilt` + `confidence` + `warnings` 만 사용하고, warnings 에 `axis_metric_transitional` / `tilt_unavailable` / `tilt_thresholds_fallback` 포함 시 raw tilt 도 무시한다 (Phase 8.1 sensitivity gate 미통과 신호). 반면 `stabilityMetrics` / `contactMetrics` 의 severity 는 guard scope 밖 — Phase 8 본체 신뢰 OK. 패턴 추론은 IPSF tolerance 20° (`tilt_thresholds.yaml::ipsf_tolerance.tolerance_deg`) + Phase 8 jitter/jerk 임계 (`JITTER_SEVERITY_THRESHOLDS=(8.0, 20.0)` / `JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED=(5000.0, 15000.0)`) 위에 박제한다.

**Primary recommendation:**
- Wave 0 = 3-way schema lockstep atomic commit (TS interface + frozen Python dataclass + docs/contract.md §9.11 신설 + Firestore scoped validator + frontend null-guard).
- Wave 1 = `force_pattern.py` 신설 모듈 + `force_pattern_copy.py` 18 canned + pipeline 1줄 wiring + 단위 test ≥ 18 케이스 + AST grep gate ≥ 10 표현.
- 모든 패키지 install 없음 (numpy / yaml 기존 의존만 사용) — slopcheck 무관.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Force pattern detection (6 signal → 5 pattern enum) | Backend / pure-function `force_pattern.py` | — | numpy 만 의존, network/LLM 무관 — Layer 1 단독 (D-09-C1) |
| Top-3 ranking + tie-break | Backend / `force_pattern.py` | — | 결정론적 sort key. UI 임의 정렬 X |
| Canned KO interpretation mapping (18 = 6 signal × 3 modeContext) | Backend / `force_pattern_copy.py` 신설 | — | Phase 7 `copy_templates.py` 패턴 정합. UI 자체 카피 작성 차단 (D-09-D2) |
| ModeContext 산출 (mode1 / mode3_first / mode3_progress) | Backend / `pipeline/app.py::_process` | — | Phase 12.5 `build_mode3(is_first)` + `get_previous_analysis` 재사용 (D-09-D6) |
| Firestore 저장 + nested-array guard | Backend / `firestore_admin._validate_force_pattern_inference` 신설 | — | Phase 8 `_validate_force_signals_report` 패턴 정합 (D-09-U5) |
| Schema lockstep enforcement | TS `analysis.ts` ↔ Python dataclass ↔ docs §9.11 | — | 3-way atomic commit (D-09-U1) |
| Frontend null-guard | App / `userAnalyses.ts::normalize` | — | Phase 8 `forceSignalsReport` null-guard 패턴 정합 (immutable spread + `?? null`) |
| 자연어 풍부화 + LLM 호출 | — | Phase 11 (CoachCommentHook) | Phase 9 = canned only. Phase 11 = Gemini 자연어 번역 (D-09-C3) |
| 영상 위 좌표 오버레이 / 실측 각도 노출 | — | Phase 12 | Phase 9 = backend data only, UI 미관여 (D-09-D5) |
| Sweep evidence / 정은지 재검증 | — | Phase 11 통합 시점 자연 검증 + Phase 15 sweep | Wave 2 본 phase OUT of scope (D-09-E2) |

## User Constraints (from CONTEXT.md)

### Locked Decisions (must research THESE, no alternatives)

**(A) Pattern Inference 룰 — Layer 1 motion-agnostic baseline**
- D-09-A1: 6 signal pool (axis_tilt / pelvis_drop / late_contact / high_jitter / high_jerk / abnormal_release) × 5 phase = 30 candidate. "어깨 elevation" / "elbow lock" = v2 deferred.
  - axis_tilt → `release`
  - pelvis_drop → `release`
  - late_contact → `brace`
  - high_jitter → `unknown`
  - high_jerk → `unknown`
  - abnormal_release → `release`
- D-09-A2 (CORE GUARD): `axisMetrics[*].severity` 직접 trust 영구 차단. raw shoulder_tilt + hip_tilt + confidence + warnings 만 사용. Tilt 임계 = `ipsf_tolerance.tolerance_deg = 20.0°`. axis warnings 에 `axis_metric_transitional` / `tilt_unavailable` / `tilt_thresholds_fallback` 포함 시 raw tilt 도 무시 + `axis_signal_unavailable` warning. stabilityMetrics / contactMetrics severity 는 사용 OK.
- D-09-A3: phase 별 multiple finding 가능 (signal 별 독립 검출).
- D-09-A4: phase 미인식 시 `phase_unavailable_for_inference` warning + skip (분석 죽지 않음).
- D-09-A5: `finding.confidence = base_confidence × phase_metric_confidence_factor`. base_confidence: axis_tilt=0.72 / pelvis_drop=0.72 / late_contact=0.70 / high_jitter=0.63 / high_jerk=0.63 / abnormal_release=0.75. phase_metric_confidence_factor = min(axisMetric.confidence, stabilityMetric.confidence) (0/0.5/1 numeric).

**(B) Top-3 Ranking**
- D-09-B1: 후보 pool = 6 signal × 5 phase = 최대 30. detection 미통과 시 candidate 생성 X.
- D-09-B2: `score = confidence × signal_weight`. signal_weight: axis_tilt=1.0 / pelvis_drop=1.0 / late_contact=0.95 / abnormal_release=1.1 / high_jerk=0.85 / high_jitter=0.80.
- D-09-B3: tie-break = phase priority (lock > hold > transition > final_shape > entry) → signal priority (axis > contact > stability) → confidence DESC.
- D-09-B4: findings length 0~3. 0개 시 `overallConfidence='low'` + `no_significant_force_pattern_signal` warning + canned "이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다…" 본문. fabrication 금지.
- D-09-B5: 동일 pattern 중복 finding 시 top confidence 1개만. 단 phase 다르면 OK (`release@lock` + `release@hold`).

**(C) Layer 2 영구 차단**
- D-09-C1: Layer 2 (Gemini) 영구 차단.
- D-09-C2: motion_id 인식 시 confidence × 1.05 (cap 1.0).
- D-09-C3: 자연어 번역 = Phase 11 책임. Phase 9 = canned KO mapping 만.

**(D) Schema + 카피**
- D-09-D1: `ForcePatternFinding` 8 필드 (pattern / phase / sourceSignal / reason EN / interpretation KO / confidence / jointHint / warnings) + `ForcePatternInference` 5 필드 (version / findings / overallConfidence / warnings / modeContext).
- D-09-D2: canned mapping = (sourceSignal × modeContext) → 18 카피 (6 × 3). phase 분기 X (v2). 모듈 = `backend/shared/python/sunity_shared/analysis/force_pattern_copy.py`.
- D-09-D3: 금지 표현 grep gate 10종 (research §10.2 6종 + 신규 4종).
- D-09-D4: raw 수치 노출 X (canned 만). Phase 12 가 실측 노출 책임.
- D-09-D5: UI hint = 없음 (Phase 12/12.5 downstream).
- D-09-D6: mode_context 산출 = pipeline `_process` → `infer_force_direction_pattern(..., mode_context=...)` 전달. mode3 first/progress 판단 = `prev = get_previous_analysis(...)` 결과 + `build_mode3(is_first=not prev)` 패턴 재사용.

**(E) Plan 구조**
- D-09-E1: 2 wave (Wave 0 schema lockstep + Wave 1 inference 본체).
- D-09-E2: Wave 2 production sweep OUT of scope.

**(U) Universal**
- D-09-U1~U6: 3-way contract lockstep + pure function + frozen dataclass + camelCase 변환 + Firestore nested-array 금지 + 단정 금지 grep gate.

### Claude's Discretion (research options, recommend)

- `force_pattern.py` 신설 모듈 vs `force_signals.py` 확장 — **권장: 신설** (Phase 8 D-08-C3 분리 패턴 정합, force_signals.py 1762줄 확장 회피).
- 18 canned KO interpretation 정확한 본문 — researcher 가 §10.1 톤 + 부위별 원인 어휘로 draft, plan 단계 belle 검수.
- `jointHint` 부위 키워드 매핑 — researcher 가 draft.
- `phase_metric_confidence_factor` 산식 (min / avg / weighted) — **권장: min** (보수적, [[feedback-analysis-first]] 정합).
- Firestore scoped validator 화이트리스트 schema — planner 박제.
- pipeline `_process` 안 호출 위치 — `compute_force_signals` 호출 직후 + `complete_analysis(force_pattern_inference=...)` 추가.
- modeContext 산출 helper 위치 — pipeline `_process` 내부 inline (별도 helper 신설 불필요).

### Deferred Ideas (OUT OF SCOPE)

- "어깨 elevation" / "elbow lock" 절대 joint angle 패턴 → v2 (features.py angles_tj 통합 필요)
- Phase-aware canned mapping (`sourceSignal × phase × modeContext`) → Phase 11 LLM 풍부화
- Confidence factor 정밀화 (joint-level + phase-level + technique-level weighted) → v2
- `rotate` pattern detection 정밀화 (angular velocity 별도 산출) → v2 (Phase 9 v1 = `rotate` enum 박제만, 자동 검출 X)
- EMG / 챔피언 근력 측정 통합 → v2 R&D
- 다각도 카메라 시점 통합 → Phase 4 완료 후 v2
- Cross-phase aggregate summary (`patternSummaryByPhase`) → v2
- **Wave 2 production sweep / 정은지 재분석 → Phase 11 통합 시점 자연 검증 + Phase 15 sweep**

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FORCE-01 | 중심축 이탈 + 접촉점 안정성 + jerk/jitter 기초 신호로부터 ForceDirectionPattern(pull/push/brace/rotate/release)이 phase별로 추론, 실패 원인 후보 상위 3개 카드 | (1) 6 signal detection rules (D-09-A1), (2) Top-3 ranking (D-09-B1~B5), (3) 5-pattern enum (research §4.1), (4) `forcePatternInference` Firestore 저장 |
| FEED-02 | 피드백이 "실패 원인 후보 3개 카드 → 내 몸 기준 힘 쓰는 방향·중심축 → 필요한 유연성/근력 → 보조 동작" 순서. 부위별 언어 (고관절·후굴·코어·내전근·전완근·광배 등) | 18 canned interpretation (D-09-D2) + jointHint 부위 어휘 (D-09-D1) + 금지 표현 grep gate (D-09-D3) |

## Project Constraints (from CLAUDE.md)

- 작업 시작 전 design.md / plan.md 확인 — Phase 9 는 backend only, design.md 무관 (UI hint 없음, D-09-D5).
- 기술 스택 변경 금지 — Phase 9 는 신규 의존성 X (numpy / yaml 기존만).
- AWS Parameter Store 사용, `.env` 하드코딩 금지 — Phase 9 는 secret 무관.
- 한국어 user-facing copy + 영어 identifier — `force_pattern_copy.py` 의 canned KO 본문 + 코드 영어.
- 이모지 / 슬롭 코드 금지 (CLAUDE.md §7) — canned 카피 안 이모지 0회 (grep gate 추가 검토 가능, 기존 forbidden 10종에 포함 X 시 별도 단위 test).
- Light theme only — backend 만 변경, UI 변경 X.

**Project skills:** 미발견 (`.claude/skills/` 등 부재 — `gsd-sdk init.phase-op` 응답 정합).

## Standard Stack

### Core (이미 사용 중, 신규 의존성 X)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | >=1.26,<3 (이미 backend/requirements) | Confidence 계산 + sort key 계산 | Phase 8 force_signals.py 의존. 신규 install X |
| pyyaml | (이미 backend/requirements) | `tilt_thresholds.yaml` lazy load | `_get_tilt_thresholds()` 헬퍼 재사용 (force_signals.py:255) |
| pytest | >=8,<9 (이미 backend/requirements-dev) | 단위 test framework | Phase 8/8.1/7 패턴 정합 |

### Supporting (재사용 모듈)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sunity_shared.analysis.force_signals` | Phase 8/8.1 | `ForceSignalsReport` / `AxisDeviationMetric` / `StabilityMetric` / `ContactStabilityMetric` / `PhaseBoundary` / `MotionPhase` enum / 상수 `JITTER_SEVERITY_THRESHOLDS` / `JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED` / `_get_tilt_thresholds` helper | `force_pattern.py` 가 모든 입력 type + 임계 reference |
| `sunity_shared.firestore_admin` | Phase 8 | `_validate_force_signals_report` 패턴 (신설 `_validate_force_pattern_inference` source) | scoped validator 신설 위치 |
| `pipeline.app._dataclass_to_camel_case_dict` | Phase 6/8 | snake → camelCase 자동 변환 (5-case: dataclass / list / dict / Enum / scalar) | Wave 1 wiring 시 재사용 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 모듈 신설 `force_pattern.py` | `force_signals.py` 확장 | 신설 권장 — Phase 8 D-08-C3 분리 패턴 정합 + force_signals.py 1762줄 이미 큼 + 진단 vs 추론 책임 분리 명확 |
| min(confidence) | avg / weighted | min — 보수적, [[feedback-analysis-first]] 정합 (위양성 < 위음성 우선) |
| Phase-aware 18+ canned | 6 × 3 = 18 단일 | 18 — v1 단순화 (D-09-D2). phase 차별 카피는 Phase 11 LLM 풍부화 |
| inline jointHint string | enum literal | inline string — Phase 7 `JOINT_LABEL_KO` 패턴 정합 (한국어 어휘 박제, enum 도입 시 v2 다국 alias 대비 변경 폭 큼) |

**Installation:** 신규 install 없음 — Phase 8 backend/requirements 와 동일.

**Version verification:** Phase 9 의존성은 모두 backend/requirements*.txt 에 기존 박제 (Phase 8 Plan 03 시점 검증 완료). 신규 install 없으므로 npm view / pip index 불필요.

## Package Legitimacy Audit

> 본 phase 는 외부 패키지 install 없음 (numpy / pyyaml / pytest 모두 기존 의존성 재사용). slopcheck protocol 실행 불필요 (적용 대상 0). Phase 8/8.1 시점에 이미 통과한 의존성 위에 박제.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (없음) | — | — | — | — | — | 신규 install 없음 |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[ Phase 8 산출 ]                   [ Phase 9 본 phase ]                   [ Phase 11 downstream ]
                                                                          
ForceSignalsReport ────────────►   force_pattern.py                  ────► CoachCommentHook
  ├ phaseBoundaries[]                infer_force_direction_pattern()        autoFindingsSummary
  ├ axisMetrics[*]                   ├ 6 signal detector                    (Gemini 자연어 번역)
  │   .shoulder_tilt (raw)           │   ├ axis_tilt (raw + warnings 무시)
  │   .hip_tilt (raw)                │   ├ pelvis_drop (asymmetry)
  │   .confidence                    │   ├ late_contact (contactMetric)
  │   .warnings                      │   ├ high_jitter (StabilityMetric)
  ├ stabilityMetrics[*]              │   ├ high_jerk (StabilityMetric)
  │   .jitter_score                  │   └ abnormal_release (warnings)
  │   .jerk_score                    │
  │   .confidence                    ├ ForcePatternFinding[] 후보 pool (≤ 30)
  ├ contactMetrics[*]                │
  │   .estimated_stable              ├ Top-3 ranking
  │   .near_pole_ratio               │   ├ score = confidence × signal_weight
  │   .warnings                      │   ├ tie-break (phase → signal → confidence)
  └ warnings (umbrella)              │   └ pattern 중복 차단 (D-09-B5)
                                     │
[ tilt_thresholds.yaml ]             ├ findings[0..3] 산출
  └ ipsf_tolerance                   │
      .tolerance_deg = 20.0          ├ 18 canned import
                                     │   force_pattern_copy.py
[ Phase 8 모듈 상수 ]                │   _COPY (sourceSignal, modeContext) → KO
  ├ JITTER_SEVERITY_THRESHOLDS       │
  └ JERK_SEVERITY_THRESHOLDS         └ ForcePatternInference 산출
                                            │
[ pipeline/app.py::_process ]               │
  compute_force_signals(...)                │
  ─►  mode_context = ...                    │
       (mode + prev 유무)                   │
  ─►  infer_force_direction_pattern( ◄──────┘
        force_signals_report,
        motion_id,
        mode_context,
      )
  ─►  _dataclass_to_camel_case_dict(...)
  ─►  complete_analysis(
        ...,
        force_signals_report=...,
        force_pattern_inference=...,  ◄── 신설 kwarg
      )
                  │
                  ▼
        Firestore users/{uid}/analyses/{id}
          result.forceSignalsReport (Phase 8)
          result.forcePatternInference  ◄── 신설 필드
                  │
                  ▼ onSnapshot
        userAnalyses.ts::normalize
          forcePatternInference null-guard (Phase 8 패턴 정합)
                  │
                  ▼
        AnalysisDoc.result.forcePatternInference
        (Phase 11/12/12.5 가 consume)
```

### Recommended Project Structure

```
backend/shared/python/sunity_shared/analysis/
├── force_signals.py          # Phase 8/8.1 (입력 source — 본 phase 변경 X)
├── force_pattern.py          # 신설 — 본 phase 산출 본체
├── force_pattern_copy.py     # 신설 — 18 canned KO mapping (Phase 7 copy_templates.py 패턴)
├── copy_templates.py         # Phase 7 — 패턴 reference (변경 X)
└── assemble.py               # Phase 12.5 — mode 분기 패턴 reference (변경 X)

backend/shared/python/sunity_shared/
└── firestore_admin.py        # +`_validate_force_pattern_inference` 신설
                              # +complete_analysis 시그니처 확장

backend/functions/pipeline/
└── app.py                    # +infer_force_direction_pattern 호출 + camelCase 변환
                              # +complete_analysis(force_pattern_inference=...) 추가
                              # +mode_context 산출 (inline)

app/src/types/
└── analysis.ts               # +ForcePatternFinding interface
                              # +ForcePatternInference interface
                              # +AnalysisResult.forcePatternInference?: ForcePatternInference | null

app/src/lib/
└── userAnalyses.ts           # +forcePatternInference null-guard (immutable spread)

docs/
└── contract.md               # +§9.11 신설 (Phase 8 §9.3~9.10 패턴 정합)

backend/tests/
└── phase09/                  # 신설 — Phase 8/8.1 conftest.py 패턴 정합
    ├── __init__.py
    ├── conftest.py
    ├── test_infer_force_direction_pattern.py        # 6 signal detection + 0/1/2/3 케이스
    ├── test_force_pattern_ranking.py                # Top-3 ranking + tie-break
    ├── test_force_pattern_copy_no_forbidden.py      # AST 10 금지 표현 grep gate
    ├── test_force_pattern_lockstep.py               # 3-way schema lockstep
    ├── test_dataclass_to_camel_case_dict_phase9.py  # camelCase 자동 변환
    ├── test_firestore_lockstep_phase9.py            # scoped validator
    └── test_force_pattern_pipeline_wiring.py        # pipeline _process wiring + mode_context
```

### Pattern 1: 신설 모듈 + frozen dataclass + `__post_init__` validator

**What:** Phase 8 `force_signals.py` 의 `@dataclass(frozen=True)` 박제. enum literal 검증을 `frozenset` + `__post_init__` 으로.

**When to use:** 모든 ForcePatternFinding / ForcePatternInference 산출 시.

**Example:**
```python
# Source: backend/shared/python/sunity_shared/analysis/force_signals.py:355-397 (AxisDeviationMetric 패턴)
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

ForceDirectionPattern = Literal["pull", "push", "brace", "rotate", "release", "unknown"]
ForceSourceSignal = Literal[
    "axis_tilt", "pelvis_drop", "late_contact",
    "high_jitter", "high_jerk", "abnormal_release",
]
ModeContext = Literal["mode1", "mode3_first", "mode3_progress"]
_FORCE_PATTERNS = frozenset({"pull", "push", "brace", "rotate", "release", "unknown"})
_FORCE_SOURCE_SIGNALS = frozenset({
    "axis_tilt", "pelvis_drop", "late_contact",
    "high_jitter", "high_jerk", "abnormal_release",
})
_MODE_CONTEXTS = frozenset({"mode1", "mode3_first", "mode3_progress"})

@dataclass(frozen=True)
class ForcePatternFinding:
    pattern: ForceDirectionPattern
    phase: "MotionPhase"  # force_signals.MotionPhase
    source_signal: ForceSourceSignal
    reason: str           # EN 한 문장
    interpretation: str   # KO canned
    confidence: float     # [0.0, 1.0]
    joint_hint: str | None
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.pattern not in _FORCE_PATTERNS:
            raise ValueError(f"pattern must be one of {_FORCE_PATTERNS}, got {self.pattern!r}")
        if self.source_signal not in _FORCE_SOURCE_SIGNALS:
            raise ValueError(f"source_signal must be one of {_FORCE_SOURCE_SIGNALS}, got {self.source_signal!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be [0, 1], got {self.confidence}")
        if not self.interpretation:
            raise ValueError("interpretation must be non-empty (canned KO)")
```

### Pattern 2: Pure-function inference + signal detection helpers

**What:** Phase 8 `compute_force_signals` 의 umbrella + private helper 패턴 정합. `infer_force_direction_pattern` = public entry, 6 `_detect_*` helper + 1 `_rank_findings` + 1 `_phase_metric_confidence_factor`.

**When to use:** Wave 1 `force_pattern.py` 본체.

**Example pseudocode:**
```python
# 본체 entrypoint (D-09-A1 / A5 / B2 / C2 정합)
def infer_force_direction_pattern(
    force_signals_report: ForceSignalsReport,
    motion_id: str | None,
    mode_context: ModeContext,
) -> ForcePatternInference:
    candidates: list[ForcePatternFinding] = []
    warnings_top: list[str] = []

    boundaries_by_phase: dict[MotionPhase, PhaseBoundary] = {
        b.phase: b for b in force_signals_report.phase_boundaries
    }
    axis_by_phase = {m.phase: m for m in force_signals_report.axis_metrics}
    stability_by_phase = {m.phase: m for m in force_signals_report.stability_metrics}
    contact_by_phase: dict[MotionPhase, list[ContactStabilityMetric]] = {}
    for cm in force_signals_report.contact_metrics:
        contact_by_phase.setdefault(cm.phase, []).append(cm)

    for phase in ("entry", "lock", "transition", "final_shape", "hold"):
        if phase not in boundaries_by_phase:
            warnings_top.append("phase_unavailable_for_inference")
            continue
        axis = axis_by_phase.get(phase)
        stab = stability_by_phase.get(phase)
        contacts = contact_by_phase.get(phase, [])
        cf = _phase_metric_confidence_factor(axis, stab)  # min

        # signal 6종 — D-09-A1
        for finding in _detect_axis_tilt(axis, phase, cf, mode_context):
            candidates.append(finding)
        for finding in _detect_pelvis_drop(axis, phase, cf, mode_context):
            candidates.append(finding)
        for finding in _detect_late_contact(contacts, phase, cf, mode_context):
            candidates.append(finding)
        for finding in _detect_high_jitter(stab, phase, cf, mode_context):
            candidates.append(finding)
        for finding in _detect_high_jerk(stab, phase, cf, mode_context):
            candidates.append(finding)
        for finding in _detect_abnormal_release(contacts, phase, cf, mode_context):
            candidates.append(finding)

    # motion_id 보강 (D-09-C2)
    if motion_id is not None:
        candidates = [_apply_motion_id_boost(c) for c in candidates]

    # Top-3 ranking + tie-break + 중복 차단 (D-09-B1~B5)
    findings = _rank_top3(candidates)

    # 0개 시 fallback (D-09-B4)
    if not findings:
        warnings_top.append("no_significant_force_pattern_signal")
        overall: MetricConfidence = "low"
    else:
        overall = _overall_confidence_from_findings(findings)

    return ForcePatternInference(
        version="1.0",
        findings=findings,
        overall_confidence=overall,
        warnings=warnings_top,
        mode_context=mode_context,
    )
```

### Pattern 3: 18 canned mapping (Phase 7 `copy_templates.py` 패턴)

**What:** dict[tuple[sourceSignal, modeContext], str] singleton + `render_finding_copy` 같은 lookup helper.

**When to use:** `force_pattern_copy.py` 신설.

**Example:**
```python
# Source: backend/shared/python/sunity_shared/analysis/copy_templates.py:48-52
# Phase 9 신설 (force_pattern_copy.py)
_MODE_PREFIX: dict[ModeContext, str] = {
    "mode1": "정은지 선수 기준 패턴과 비교했을 때,",
    "mode3_first": "이번 첫 분석에서,",
    "mode3_progress": "지난 영상 대비,",
}

# (sourceSignal, modeContext) → interpretation KO 1 sentence (D-09-D2)
_FORCE_PATTERN_COPY: dict[tuple[ForceSourceSignal, ModeContext], str] = {
    ("axis_tilt", "mode1"): "정은지 선수 기준 패턴과 비교했을 때, 코어로 중심축을 잡는 감각이 덜 형성된 가능성이 보여요.",
    ("axis_tilt", "mode3_first"): "이번 첫 분석에서, 척추 라인이 한쪽으로 기울며 코어 고정이 풀리는 흐름이 보이네요.",
    ("axis_tilt", "mode3_progress"): "지난 영상 대비, 중심축이 더 흔들리는 흐름으로 코어 고정 감각을 다시 점검해 볼 수 있어요.",
    ...
}

def force_pattern_canned_text(
    source_signal: ForceSourceSignal, mode_context: ModeContext
) -> str:
    return _FORCE_PATTERN_COPY[(source_signal, mode_context)]
```

### Pattern 4: AST 기반 금지 표현 grep gate

**What:** Phase 7 `test_copy_templates_no_forbidden.py` 의 ast.walk + `_COPY` / `_MODE_PREFIX` dict literal 추출 + parametrize 검사.

**When to use:** `test_force_pattern_copy_no_forbidden.py` 신설.

**Example:**
```python
# Source: backend/tests/phase07/test_copy_templates_no_forbidden.py:46-80
import ast, pytest
from pathlib import Path
from sunity_shared.analysis.force_pattern_copy import (
    FORBIDDEN_PHRASES_RESEARCH,  # research §10.2 6종
    FORBIDDEN_PHRASES_PHASE9,    # D-09-D3 신규 4종
)

@pytest.mark.parametrize(
    "phrase", FORBIDDEN_PHRASES_RESEARCH + FORBIDDEN_PHRASES_PHASE9
)
def test_no_forbidden_in_force_pattern_copy(phrase: str) -> None:
    src = _MODULE_PATH.read_text("utf-8")
    tree = ast.parse(src)
    strings: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        target_id = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            target_id = t.id if isinstance(t, ast.Name) else None
        elif isinstance(node, ast.AnnAssign):
            t = node.target
            target_id = t.id if isinstance(t, ast.Name) else None
        if target_id in ("_FORCE_PATTERN_COPY", "_MODE_PREFIX"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    strings.append((sub.value, sub.lineno))
    violations = [(s, ln) for s, ln in strings if phrase in s]
    assert not violations, f"금지 표현 {phrase!r} 발견: {violations}"
```

### Pattern 5: Firestore scoped validator (Phase 8 `_validate_force_signals_report` 패턴)

**What:** `_validate_force_pattern_inference` 신설 — `findings` (list[dict-of-scalars]) + `warnings` (list[str]) 화이트리스트, nested dict / list[list] reject.

**When to use:** `complete_analysis(force_pattern_inference=...)` 호출 직전 validate.

**Example:**
```python
# Source: backend/shared/python/sunity_shared/firestore_admin.py:148-210 (force_signals 정합)
_FORCE_PATTERN_FINDING_SCALAR_LIST_KEYS: frozenset[str] = frozenset({"warnings"})

def _validate_force_pattern_inference(
    payload: dict, *, path: str = "forcePatternInference"
) -> None:
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(f"_validate_force_pattern_inference: dict 만, path={path}")
    for key, value in payload.items():
        sub = f"{path}.{key}"
        # version / overallConfidence / modeContext = scalar
        if value is None or isinstance(value, (str, int, float, bool)):
            continue
        if isinstance(value, dict):
            raise ValueError(f"{sub} unexpected nested dict")
        if isinstance(value, list):
            if key == "warnings":
                # top-level warnings = list[str]
                for i, item in enumerate(value):
                    if item is not None and not isinstance(item, (str, int, float, bool)):
                        raise ValueError(f"{sub}[{i}] must be scalar")
                continue
            if key == "findings":
                # findings = list[dict]
                for i, item in enumerate(value):
                    item_path = f"{sub}[{i}]"
                    if not isinstance(item, dict):
                        raise ValueError(f"{item_path} must be dict")
                    _validate_force_pattern_finding_dict(item, path=item_path)
                continue
            raise ValueError(f"{sub} unexpected list at top-level")
        raise ValueError(f"{sub} unexpected type {type(value).__name__}")


def _validate_force_pattern_finding_dict(d: dict, *, path: str) -> None:
    # 8 필드 — pattern / phase / sourceSignal (camelCase) / reason / interpretation /
    #        confidence / jointHint / warnings (list[str])
    for k, v in d.items():
        sub = f"{path}.{k}"
        if v is None or isinstance(v, (str, int, float, bool)):
            continue
        if isinstance(v, dict):
            raise ValueError(f"{sub} nested dict in finding entry not allowed")
        if isinstance(v, list):
            if k not in _FORCE_PATTERN_FINDING_SCALAR_LIST_KEYS:
                raise ValueError(
                    f"{sub} list field not in force_pattern_finding whitelist "
                    f"({sorted(_FORCE_PATTERN_FINDING_SCALAR_LIST_KEYS)}); reject"
                )
            for i, item in enumerate(v):
                if isinstance(item, (list, dict)):
                    raise ValueError(f"{sub}[{i}] nested reject")
                if item is not None and not isinstance(item, (str, int, float, bool)):
                    raise ValueError(f"{sub}[{i}] must be scalar")
            continue
        raise ValueError(f"{sub} unexpected type")
```

### Pattern 6: pipeline `_process` wiring (Phase 8 패턴 1줄 추가)

**What:** Phase 8 `compute_force_signals` 호출 직후 (`pipeline/app.py:1118-1140`) — 동일 패턴으로 `infer_force_direction_pattern` + camelCase 변환 + `complete_analysis(force_pattern_inference=...)` 추가.

**Example:**
```python
# Source: backend/functions/pipeline/app.py:1117-1140 (Phase 8 wiring 패턴)
        layer2_recognizer = _get_force_signals_layer2_recognizer()
        force_signals_report = fs.compute_force_signals(
            inputs.pose_frames,
            inputs.pole_axis_measurement,
            student_profile,
            angles=angles,
            fps=9.0,
            motion_id=getattr(profile, "motion_id", None),
            preflight_label_gate_passed=_preflight_label_gate_passed(),
            technique_profile=profile if layer2_recognizer is not None else None,
        )
        force_signals_dict = _dataclass_to_camel_case_dict(force_signals_report)

        # ── Phase 9 신설 (D-09-D6 wiring) ────────────────────────────
        # mode_context 산출 inline — Phase 12.5 build_mode3(is_first) 패턴 정합.
        if mode == models.MODE_REFERENCE:
            mode_context = "mode1"
        else:
            # _mode3_comparison 가 이미 prev 를 fetch 했으므로 comparison["isFirst"] 재사용
            is_first = comparison.get("isFirst", True) if isinstance(comparison, dict) else True
            mode_context = "mode3_first" if is_first else "mode3_progress"

        force_pattern_inference = infer_force_direction_pattern(
            force_signals_report,
            motion_id=getattr(profile, "motion_id", None),
            mode_context=mode_context,
        )
        force_pattern_inference_dict = _dataclass_to_camel_case_dict(force_pattern_inference)
        # ────────────────────────────────────────────────────────────

        firestore_admin.complete_analysis(
            uid,
            analysis_id,
            result,
            angles=np.asarray(angles, dtype=float).reshape(-1).tolist(),
            angles_joint_keys=list(skeleton.JOINT_KEYS),
            angles_frames=int(np.asarray(angles).shape[0]),
            body_comparison_report=body_comparison_report_dict,
            body_normalization_profile=body_normalization_profile_dict,
            force_signals_report=force_signals_dict,
            force_pattern_inference=force_pattern_inference_dict,  # ◄── Phase 9 신설
        )
```

### Anti-Patterns to Avoid

- **`axisMetrics[*].severity` 직접 trust.** D-09-A2 영구 차단. raw `shoulder_tilt` + `hip_tilt` 만 + IPSF 20° 임계 + warnings 무시 룰.
- **`stabilityMetrics` / `contactMetrics` severity 추가 차단.** D-09-A2 guard scope 밖 — Phase 8 본체 신뢰 OK. 과도하게 guard 확장 시 Phase 8 stabilityMetric 사용 자체가 막힘.
- **Layer 2 (Gemini) 호출.** D-09-C1 영구 차단. Phase 11 책임 경계 침범.
- **수치 raw 노출 (예: "shoulder_tilt 87°").** D-09-D4 — Phase 12 책임. interpretation 본문 = canned KO 만.
- **fabrication (0 개 finding 일 때 강제로 1~3 개 emit).** D-09-B4 위반. `no_significant_force_pattern_signal` warning + canned fallback 본문.
- **"박제" / "%일치" / "유사도" 단어 canned 본문 사용.** [[no-baekje-filler]] / [[mode3-progress-not-similarity]] 위반. AST grep gate 가 회귀 차단.
- **phase 미인식 시 fallback finding 만들기.** D-09-A4 — `phase_unavailable_for_inference` warning 만 + skip.
- **Phase 9 안에서 BodyComparisonReport 의 finding 과 cross-link 시도.** Phase 9 = force 신호 단독 layer. Phase 11 CoachCommentHook 가 통합 책임.
- **`rotate` pattern 자동 검출 시도.** v2 deferred — Phase 9 v1 은 enum 박제만, detection 0 (rotate 산출 불가능 — angular velocity 별도 산출 필요).
- **camelCase 변환 수동 작성.** `_dataclass_to_camel_case_dict` 5-case helper 재사용 (Phase 6 C8 fix 박제).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| snake → camelCase 변환 | 수동 변환 | `pipeline.app._dataclass_to_camel_case_dict` (Phase 6 C8 fix) | dataclass / list / dict / Enum / scalar 5-case 박제 + 단위 test 박제 |
| tilt 임계 yaml load | 별도 yaml loader | `force_signals._get_tilt_thresholds()` (Phase 8.1 Wave 1) | schema_v2 검증 + lazy cache + fallback 박제 |
| jitter / jerk 임계 | 새 상수 | `force_signals.JITTER_SEVERITY_THRESHOLDS` / `JERK_SEVERITY_THRESHOLDS_DEG_PER_SEC_CUBED` | Phase 8 박제 calibration 재사용 (drift 차단) |
| mode3 first/progress 판단 | 별도 helper | pipeline `_process` 의 `_mode3_comparison(...)` 가 산출한 `comparison["isFirst"]` 재사용 | Phase 12.5 `build_mode3` 패턴 정합 |
| Firestore scoped validator | 새 validator class | Phase 8 `_validate_force_signals_report` 패턴 미러 | nested-array 금지 + 화이트리스트 패턴 박제 |
| frontend null-guard | optional chaining 산발 | `userAnalyses.ts::normalize` 의 immutable spread + `?? null` 패턴 | Phase 8 forceSignalsReport null-guard 직접 모방 |
| Confidence enum sort | 새 Lookup | `force_signals._overall_confidence` 의 `order = {"low": 0, "medium": 1, "high": 2}` 패턴 | Phase 8 박제 |
| AST grep gate | regex 직접 | Phase 7 `test_copy_templates_no_forbidden.py` 의 ast.walk | dict literal 만 검사 (docstring / fallback 본문 false positive 차단) |

**Key insight:** Phase 9 = Phase 7 + Phase 8 + Phase 12.5 의 박제 패턴 합성. 신설 모듈 + 신설 schema + 신설 validator 모두 있으나, 각 항목은 **기존 패턴 정합 1:1 mirror** 다. 새 패턴 도입은 D-09-A1 의 6 signal detection rule + D-09-A5 의 confidence 산식 + D-09-B 의 ranking 알고리즘뿐.

## Runtime State Inventory

> Phase 9 = greenfield (신설 모듈 + 신설 필드). 기존 string rename / data migration 없음. 본 섹션 일부만 적용.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None** — 신설 `forcePatternInference` 필드만 추가. 기존 Firestore doc 에 부재해도 frontend null-guard 가 처리 (Phase 8 패턴 정합) | none |
| Live service config | **None** — RunPod / Lambda env / SAM template 변경 없음 (pure function, 신규 env var 없음) | none |
| OS-registered state | **None** — 본 phase = backend code only | none |
| Secrets/env vars | **None** — Gemini / Cerebras / Pod token 등 변경 없음 (D-09-C1 Layer 2 차단) | none |
| Build artifacts | **None** — pyproject.toml / requirements*.txt 변경 없음. `sam build --use-container` 재실행은 Wave 1 종료 후 mock E2E test 시점에만 필요 (Plan 단위 — Phase 8 패턴 정합) | none |

**확정:** 본 phase 는 schema 신설 + code 신설만 하므로 runtime state drift 위험 0. 단, **신규 Firestore 필드 `result.forcePatternInference` 의 write path 가 pipeline `_process` 한 곳으로 단일** 인지를 plan-checker 가 검증해야 한다 (다중 write path = data divergence 위험).

## Common Pitfalls

### Pitfall 1: pelvis_drop 룰의 정량 임계 모호

**What goes wrong:** D-09-A1 의 pelvis_drop 룰 = "hip_tilt >> shoulder_tilt + axis warning 부재". "≫" 의 정량 임계 (10° 차이? 5° 차이?) 가 CONTEXT.md 에 미명시. planner 가 자의 해석 시 hip-drop 검출이 너무 빡빡 / 너무 느슨해짐.

**Why it happens:** research §4.2 의 "골반이 아래로 떨어짐" = 정성 표현. D-09-A1 이 그대로 인용.

**How to avoid:** Wave 1 plan 단계에 **임계 = `hip_tilt - shoulder_tilt > 10°` AND `hip_tilt > 20°` (IPSF tolerance)** 박제 권장. 10° 근거 = (1) Phase 8.1 정은지 25 sample 의 shoulder_tilt P50 = 24.8° vs hip_tilt P50 = 27.7° 차이 = 2.9° 가 "정상", P75 차이 = 5°, P90 차이 = 2° → 10° 차이는 정은지 분포 P100 (8.7° = p100 차이) 도 초과 = 비대칭 명확. (2) IPSF tolerance 20° 와 동일 자릿수. 단, 본 임계는 **belle 검수 필요** (plan 단계 확인).

**Warning signs:** Phase 9 종료 후 정은지 영상에 pelvis_drop finding 0개여야 정합 (Phase 8.1 sensitivity gate 5/5 통과 정합). 1개 이상 시 임계 재calibration 필요.

### Pitfall 2: warnings 무시 룰 적용 시점 (signal 별 vs phase 별)

**What goes wrong:** D-09-A2 의 "warnings 에 `axis_metric_transitional` / `tilt_unavailable` / `tilt_thresholds_fallback` 포함 시 raw tilt 도 무시" 룰을 phase 별 axisMetric 단위로 적용해야 함. umbrella warnings 단위로 적용 시 1 phase 의 일시적 warning 이 전체 axis_tilt detection 봉쇄.

**Why it happens:** ForceSignalsReport 가 top-level warnings + 각 metric.warnings 양쪽에 박제 가능 (Phase 8 패턴). `axis_metric_transitional` 은 _전체_ axisMetric 의 transitional 상태일 때만 top-level emit (`force_signals.py:1673-1677`).

**How to avoid:** Phase 별 axisMetric 의 `warnings` 만 검사 — `if any(w in axis.warnings for w in ("axis_metric_transitional", "tilt_unavailable", "tilt_thresholds_fallback"))` → 해당 phase 만 skip + `axis_signal_unavailable` warning 추가. top-level `report.warnings` 는 검사 X.

**Warning signs:** 단위 test 에 axis warning 1 phase 만 인 fixture 박제, 다른 phase 의 axis_tilt detection 정상 동작 검증.

### Pitfall 3: mode3 first/progress 판단 source 불일치

**What goes wrong:** D-09-D6 의 mode_context 산출 시 (1) `analysis.mode == MODE_SELF` 인지 (2) prev 가 있는지 두 단계 판단. 둘 중 하나라도 misalign 시 `mode3_first` 와 `mode3_progress` canned 카피가 잘못 노출.

**Why it happens:** Phase 12.5 `build_mode3(is_first, previous_analysis_id)` 의 first 판단 룰 = `is_first or not previous_analysis_id` (assemble.py:245). 중복 조건.

**How to avoid:** pipeline `_process` 에서 `_mode3_comparison` 가 산출한 `comparison["isFirst"]` 를 single source 로 사용 (`mode3_first` if isFirst else `mode3_progress`). mode1 분기는 단순 — `mode == MODE_REFERENCE` → `"mode1"` 박제. 별도 helper 신설 X.

**Warning signs:** pipeline 통합 test 에 mode1 / mode3_first (prev 없음) / mode3_progress (prev 있음) 3 fixture 박제, ForcePatternInference.modeContext 값 비교.

### Pitfall 4: confidence enum → float 변환 자리수

**What goes wrong:** D-09-A5 의 `phase_metric_confidence_factor` = min(axisMetric.confidence, stabilityMetric.confidence). 두 confidence 는 `MetricConfidence` Literal ('low'/'medium'/'high') — float 변환 룰 필요.

**Why it happens:** Phase 8 `_overall_confidence` 는 `order = {"low": 0, "medium": 1, "high": 2}` 정수 사용 (string sort). 본 phase 는 곱셈 필요 → float 변환.

**How to avoid:** `_CONFIDENCE_TO_FACTOR: dict[MetricConfidence, float] = {"low": 0.3, "medium": 0.7, "high": 1.0}` 박제 권장. 근거 = Phase 8 `force_signals.RELIABILITY_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.3}` (force_signals.py:193) — 동일 매핑 재사용 (drift 차단).

**Warning signs:** 단위 test 에 confidence 'low' + base 0.72 → finding.confidence = 0.216 검증 / 'high' → 0.72 검증.

### Pitfall 5: motion_id 보강의 적용 순서

**What goes wrong:** D-09-C2 의 motion_id 보강 (× 1.05, cap 1.0) 을 Top-3 ranking 이후 적용 시 score (= confidence × signal_weight) 의 정렬이 보강 전 값으로 굳어짐. ranking 결과 변경됨.

**Why it happens:** confidence × 1.05 은 score 계산에 영향 → ranking sort 키 변경.

**How to avoid:** **ranking 전에 모든 candidate 의 confidence 에 motion_id 보강 적용** 후 score 산출. `_rank_top3` 안에 score = boosted_confidence × signal_weight.

**Warning signs:** 단위 test 에 motion_id 있을 때 vs 없을 때 Top-3 순서 변경 케이스 박제.

### Pitfall 6: phase priority tie-break 의 정수 매핑 부족

**What goes wrong:** D-09-B3 의 phase priority `lock > hold > transition > final_shape > entry` 의 sort 가 string 비교로 자연 정렬되지 않음 (예: `'entry' < 'final_shape'` string 비교 결과는 알파벳).

**Why it happens:** Python `sorted()` 의 기본은 string 비교.

**How to avoid:** 명시 `_PHASE_PRIORITY: dict[MotionPhase, int] = {"lock": 0, "hold": 1, "transition": 2, "final_shape": 3, "entry": 4}` (낮은 값 = 높은 우선). signal priority 동일 `_SIGNAL_PRIORITY: dict[ForceSourceSignal, int] = {"axis_tilt": 0, "pelvis_drop": 0, "abnormal_release": 1, "late_contact": 1, "high_jerk": 2, "high_jitter": 2}` (axis > contact > stability 라서 axis_tilt + pelvis_drop = 0, contact 계열 = 1, stability 계열 = 2).

**Warning signs:** 단위 test 에 score 동점인 candidate 2개 (lock vs entry, 같은 signal) → lock 우선 검증.

### Pitfall 7: forbidden 표현의 한국어 변형 누락

**What goes wrong:** D-09-D3 의 10 금지 표현 중 `\d+%.*감점` 정규식이 단일 grep gate 의 substring match 와 호환 안 됨. 한국어 변형 (`"광배 N% 부족"` vs `"광배 N프로 부족"`) 도 누락 위험.

**Why it happens:** Phase 7 AST gate 는 substring match (string `in` substring). 정규식 사용 X.

**How to avoid:** D-09-D3 의 `\d+%.*감점` 은 정규식이 아닌 **고정 substring 박제** 권장 — `"% 감점"` / `"% 깎"` / `"점 감점"` 3종 박제. 또는 별도 단위 test 에서 regex `re.search(r"\d+%\s*감점", s)` 적용 (Phase 7 패턴 변경 없이 추가 test 1건). 박제 권장 = 후자 (regex test 1건 추가 — substring gate 와 양립).

**Warning signs:** 단위 test 에 "30% 감점입니다" 같은 fixture 박제 → reject 검증.

### Pitfall 8: Frontend null-guard 의 findings 내부 default

**What goes wrong:** Phase 8 패턴 (`userAnalyses.ts:74-88`) 는 top-level 필드 default 만 제공. ForcePatternFinding 의 개별 필드 (예: `warnings: []`, `jointHint: null`) 의 default 누락 시 old doc render 시 crash.

**Why it happens:** TS interface 의 non-optional 필드 (예: `warnings: string[]`) 가 undefined 시 React render 에러.

**How to avoid:** normalize 안에 `findings: (report.findings ?? []).map((f) => ({ ...f, warnings: f.warnings ?? [], jointHint: f.jointHint ?? null }))` 박제.

**Warning signs:** Frontend 단위 test 박제 X (현재 app 에 test runner 없음) — 대신 TS strict mode + `tsc --noEmit` (`npm run typecheck`) gate.

## Code Examples

### Signal detection — axis_tilt (D-09-A1 + D-09-A2 정합)

```python
# Source: D-09-A1 + 본 RESEARCH §"Pitfall 2"
def _detect_axis_tilt(
    axis: AxisDeviationMetric | None,
    phase: MotionPhase,
    cf: float,
    mode_context: ModeContext,
) -> list[ForcePatternFinding]:
    if axis is None:
        return []
    # axis warnings 무시 룰 (D-09-A2)
    ignore_axis = any(
        w in axis.warnings
        for w in (
            "axis_metric_transitional",
            "tilt_unavailable",
            "tilt_thresholds_fallback",
        )
    )
    if ignore_axis:
        # raw tilt 무시 — finding 생성 X (axis_signal_unavailable 은 umbrella 가 emit)
        return []
    # raw shoulder_tilt + hip_tilt 검사 — IPSF tolerance 20°
    shoulder, hip = _get_tilt_thresholds()  # force_signals helper 재사용
    # tolerance 값을 yaml 의 ipsf_tolerance 에서 가져오려면 별도 헬퍼 신설 가능
    # (또는 force_signals 의 ipsf_tolerance loader 가 추가될 때까지 fixed 20.0)
    IPSF_TOL = 20.0
    s_tilt = axis.shoulder_tilt if axis.shoulder_tilt is not None else 0.0
    h_tilt = axis.hip_tilt if axis.hip_tilt is not None else 0.0
    if max(s_tilt, h_tilt) <= IPSF_TOL:
        return []
    return [
        ForcePatternFinding(
            pattern="release",
            phase=phase,
            source_signal="axis_tilt",
            reason="Axis tilt exceeds IPSF tolerance (20°)",
            interpretation=force_pattern_canned_text("axis_tilt", mode_context),
            confidence=min(1.0, 0.72 * cf),
            joint_hint="코어",
            warnings=[],
        )
    ]
```

### Signal detection — abnormal_release (D-09-A1 + Phase 8 정합)

```python
def _detect_abnormal_release(
    contacts: list[ContactStabilityMetric],
    phase: MotionPhase,
    cf: float,
    mode_context: ModeContext,
) -> list[ForcePatternFinding]:
    # Phase 8 _detect_abnormal_release 가 contactMetric.warnings 에
    # 'abnormal_release_during_hold' 박제. Phase 9 = 본 warning 가진 contact 검사.
    for cm in contacts:
        if "abnormal_release_during_hold" in (cm.warnings or []):
            return [
                ForcePatternFinding(
                    pattern="release",
                    phase=phase,
                    source_signal="abnormal_release",
                    reason="Contact lost during lock/hold phase",
                    interpretation=force_pattern_canned_text("abnormal_release", mode_context),
                    confidence=min(1.0, 0.75 * cf),
                    joint_hint="광배",
                    warnings=[],
                )
            ]
    return []
```

### Top-3 ranking with tie-break (D-09-B2 + B3 + B5)

```python
_PHASE_PRIORITY: dict[MotionPhase, int] = {
    "lock": 0, "hold": 1, "transition": 2, "final_shape": 3, "entry": 4,
}
_SIGNAL_PRIORITY: dict[ForceSourceSignal, int] = {
    "axis_tilt": 0, "pelvis_drop": 0,
    "abnormal_release": 1, "late_contact": 1,
    "high_jerk": 2, "high_jitter": 2,
}
_SIGNAL_WEIGHT: dict[ForceSourceSignal, float] = {
    "axis_tilt": 1.0, "pelvis_drop": 1.0,
    "late_contact": 0.95, "abnormal_release": 1.1,
    "high_jerk": 0.85, "high_jitter": 0.80,
}

def _rank_top3(candidates: list[ForcePatternFinding]) -> list[ForcePatternFinding]:
    # sort key tuple — 모두 ASC (낮을수록 우선)
    def key(f: ForcePatternFinding) -> tuple[float, int, int, float]:
        score = f.confidence * _SIGNAL_WEIGHT[f.source_signal]
        return (
            -score,                              # score DESC → -score ASC
            _PHASE_PRIORITY[f.phase],            # phase priority ASC
            _SIGNAL_PRIORITY[f.source_signal],   # signal priority ASC
            -f.confidence,                       # confidence DESC → -confidence ASC
        )
    ranked = sorted(candidates, key=key)
    # 중복 pattern 차단 (D-09-B5) — 단 phase 다른 동일 pattern 은 OK
    seen: set[tuple[str, MotionPhase]] = set()
    result: list[ForcePatternFinding] = []
    for f in ranked:
        sig = (f.pattern, f.phase)
        if sig in seen:
            continue
        seen.add(sig)
        result.append(f)
        if len(result) == 3:
            break
    return result
```

### Pipeline `_process` mode_context 산출 inline

```python
# Source: 본 RESEARCH §"Pattern 6"
# pipeline/app.py::_process 의 compute_force_signals 호출 직후 1줄로 박제 가능.
if mode == models.MODE_REFERENCE:  # mode1
    mode_context = "mode1"
else:
    is_first = (
        comparison.get("isFirst", True)
        if isinstance(comparison, dict)
        else True
    )
    mode_context = "mode3_first" if is_first else "mode3_progress"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 8 axisMetrics severity 'high' 직접 trust | Raw shoulder_tilt + hip_tilt + warnings 무시 룰 (D-09-A2) | 2026-06-09 (Codex C-M4 / Phase 8.1 D-05) | Phase 9 의 axis_tilt detection 이 sensitivity gate 통과 후에도 보수적 — 위양성 차단 |
| Top-3 KISMAM 차원 별 worst joint | Top-3 force pattern finding (D-09-B) | 2026-06-10 (Phase 9 신설) | KISMAM = 각도 차원만, Phase 9 = phase 별 force 신호 차원 추가 |
| Layer 2 (Gemini) 패턴 추론 보강 | Layer 1 단독 + Phase 11 LLM 풍부화 (D-09-C1/C3) | 2026-06-10 (Phase 9 신설) | Deterministic + 객관성 강제, LLM 출력 판단 영역 영구 분리 |
| Phase 7 canned 33 (deficit_code × category × joint_group) | Phase 9 canned 18 (sourceSignal × modeContext) | 2026-06-10 | Phase 9 v1 단순화. phase 분기 v2 deferred |

**Deprecated/outdated:**
- 정은지/belle 사람 점수 라벨링 ground truth — [[analysis-objectivity-no-human-scores]] 박제. fabrication finding 영구 금지.
- 단정 표현 ("근육량 부족" / "정답 자세 아님" / "X% 감점") — research §10.2 + D-09-D3 grep gate.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pelvis_drop 임계 = `(hip_tilt - shoulder_tilt) > 10°` AND `hip_tilt > 20°` | Pitfall 1 | 임계 너무 빡빡 시 정상 pelvis_drop 검출 X. 너무 느슨 시 위양성 (정은지 영상에 finding 발생). Wave 1 plan 단계 belle 검수 필요. |
| A2 | confidence enum → float 매핑 = `{"low": 0.3, "medium": 0.7, "high": 1.0}` | Pitfall 4 | Phase 8 `RELIABILITY_WEIGHT` 와 동일 — 정합성 확률 HIGH. 변경 시 finding.confidence 분포 shift. |
| A3 | jointHint 부위 매핑 — axis_tilt='코어', pelvis_drop='고관절', late_contact='내전근', abnormal_release='광배', high_jerk=None, high_jitter=None | Pattern 6 | 부위 어휘 = belle 검수 필요. research §10.1 + 폴스포츠-지식.md 어휘 정합. high_jerk/jitter = 부위 불명확 (전신 떨림). |
| A4 | `signal_priority`: axis_tilt + pelvis_drop = 0, abnormal_release + late_contact = 1, high_jerk + high_jitter = 2 | Pattern: Top-3 ranking | D-09-B3 "axis > contact > stability" 매핑. axis_tilt + pelvis_drop 모두 axis 계열, abnormal_release + late_contact 모두 contact 계열 (abnormal_release 가 contactMetric.warnings 에서 검출), high_jerk + high_jitter 가 stability 계열. 정합성 HIGH. |
| A5 | force_pattern_copy.py 모듈명 + `force_pattern_canned_text(source_signal, mode_context)` helper API | Pattern 3 | Phase 7 `copy_templates.py::render_finding_copy` 패턴 정합 — 명명 OK. 단, 카피 본문 자체는 belle 검수 필요 (Wave 1 종료 시점). |
| A6 | Wave 0 atomic commit = TS interface + Python dataclass + docs/contract.md §9.11 신설 + Firestore validator + frontend null-guard 동시 | D-09-E1 / U1 | 5 파일 atomic commit — Phase 7/8/8.1 패턴 정합. commit 분리 시 schema drift 위험. |
| A7 | docs/contract.md 신설 섹션 번호 = §9.11 (§9.0~§9.10 이미 박제) | Pattern: contract.md | 본 phase 가 새 섹션 박제 — §9 가 ForceSignalsReport 단일 umbrella 이므로 ForcePatternInference 는 별도 §9.11 적정. planner 가 docs/contract.md 끝 행 확인 후 §9.11 또는 §10 (신설 umbrella) 결정. |
| A8 | mode3 first/progress 판단 source = pipeline `_process` 의 `comparison["isFirst"]` (Phase 12.5 `build_mode3` 산출) | Pitfall 3 | Phase 12.5 build_mode3 박제 — `is_first or not previous_analysis_id` 중복 조건. 본 source 신뢰 HIGH. |
| A9 | Phase 9 가 신규 yaml / config 파일 없음. IPSF tolerance 20° = `tilt_thresholds.yaml::ipsf_tolerance.tolerance_deg` 의 force_signals.py 안 loader (또는 fixed const) | D-09-A2 / Pattern: axis_tilt detection | force_signals.py 의 `_get_tilt_thresholds()` 는 operational_cutoff 만 반환 (ipsf_tolerance 미반환). 본 phase 가 yaml `ipsf_tolerance.tolerance_deg` 추가 loader 신설 vs `IPSF_TOL = 20.0` const 박제 결정 필요. planner 권장 = const 박제 (단순화 + Phase 8.1 yaml 단일 source 의 cap 으로). |

**Mitigation:** Wave 1 plan 의 첫 task 에 A1 (pelvis_drop 임계) + A3 (jointHint 매핑) + A5 (canned 본문) belle 검수 checkpoint 박제 권장. cross-AI plan-review (Codex) D-09-E3 정합.

## Open Questions

1. **`rotate` pattern enum 박제만 + detection 0 의 frontend 노출 정합성**
   - What we know: D-09-deferred 의 "rotate pattern detection 정밀화 → v2" 박제. enum 박제만 (`pattern: 'rotate'` 산출 X).
   - What's unclear: ForcePatternFinding.pattern 의 TS Literal union 에 'rotate' 포함하지만 backend 가 절대 emit X 시 dead code 인지. v2 박제 시점에 union 갱신 vs 이미 박제 둘 다 정합.
   - Recommendation: 본 phase Wave 0 schema 에 `'rotate'` literal 포함 (v2 박제 시 schema migration 0) + 단위 test 에 "rotate 미산출" 검증 (`assert not any(f.pattern == "rotate" for f in findings)` regression guard).

2. **IPSF tolerance 20° = fixed const vs yaml loader 확장**
   - What we know: `tilt_thresholds.yaml::ipsf_tolerance.tolerance_deg = 20.0` 박제, `force_signals._get_tilt_thresholds()` 는 operational_cutoff 만 반환.
   - What's unclear: 본 phase 가 yaml 의 `ipsf_tolerance` 도 load 하는 helper 신설할지, fixed const `IPSF_TOL = 20.0` 박제 만 할지.
   - Recommendation: **fixed const 박제** (Wave 1 plan). 근거 = (1) Phase 8.1 yaml 의 single source — 본 phase 가 추가 helper 신설 시 cache invalidation 책임 분산. (2) 20° 는 IPSF 박제 — calibration 변경 시 yaml 의 operational_cutoff 만 영향, ipsf_tolerance 는 ground truth. (3) tilt_thresholds.yaml schema_v2 의 ipsf_tolerance section 이 향후 변경되면 별도 plan 으로 yaml loader 확장 (현 phase boundary 외).

3. **0 finding 시 fallback interpretation 본문 vs mode 분기 본문**
   - What we know: D-09-B4 의 fallback = "이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다. 강사와 함께 확인하는 것을 권장해요."
   - What's unclear: 본 fallback 이 mode 분기 무관 단일인지, mode1 / mode3 별 다른 본문인지.
   - Recommendation: **단일 본문 박제** (CONTEXT.md 의 표기 그대로). 근거 = (1) fallback 자체가 "이슈 없음" 신호이므로 mode 분기 효용 낮음. (2) mode3 progress 의 "지난 영상 대비" 의미 자체가 부재 (이슈 없음 → 비교 무의미). 단, Wave 1 plan 단계 belle 검수.

4. **단위 test fixture 의 ForceSignalsReport 생성 방법**
   - What we know: Phase 8 `backend/tests/phase08/fixtures/` 의 dict literal fixture 박제. Phase 8 _compute_force_signals 의 단위 test 가 frozen dataclass instantiation.
   - What's unclear: Phase 9 단위 test 가 Phase 8 frozen dataclass 직접 instantiate vs dict fixture → dataclass 변환 helper 사용.
   - Recommendation: **frozen dataclass 직접 instantiate** + factory helper (`_make_axis_metric(phase='lock', shoulder_tilt=25.0, ...)` 같은). 근거 = Phase 8 단위 test 패턴 정합 + frozen dataclass __post_init__ 검증 동시 통과.

## Environment Availability

> Phase 9 = pure-function backend code only. 외부 도구 / 서비스 의존 없음.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | force_pattern.py 본체 | ✓ | 3.12 (backend/template.yaml `Runtime: python3.12`) | — |
| numpy | confidence factor 계산 | ✓ | >=1.26,<3 (Phase 8 박제) | — |
| pyyaml | (사용 가능, 본 phase 에서는 미사용 권장 — Open Q 2) | ✓ | 기존 | yaml 미사용 시 IPSF_TOL = 20.0 fixed const |
| pytest | 단위 test | ✓ | >=8,<9 (Phase 8 박제) | — |
| Cerebras / Gemini / RunPod | (영구 미사용 — D-09-C1) | n/a | — | 없음 (Layer 2 영구 차단) |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 |
| Config file | `backend/pytest.ini` 또는 root conftest (Phase 8 박제 정합 — `backend/tests/conftest.py` 박제) |
| Quick run command | `cd backend && pytest tests/phase09/ -x -q` |
| Full suite command | `cd backend && pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FORCE-01 SC#1 | `infer_force_direction_pattern` 가 5 pattern enum 중 하나 이상 phase별 반환 | unit | `pytest tests/phase09/test_infer_force_direction_pattern.py::test_six_signals_each_emit_one_finding -x` | ❌ Wave 0 |
| FORCE-01 SC#2 | 후보가 정확히 상위 3개로 정렬 (KISMAM Top-3 진화) | unit | `pytest tests/phase09/test_force_pattern_ranking.py::test_top3_ranking_with_signal_weight -x` | ❌ Wave 0 |
| FORCE-01 SC#3 | 모든 finding 에 confidence + interpretation + "가능성" 언어 | unit | `pytest tests/phase09/test_force_pattern_copy_no_forbidden.py -x` | ❌ Wave 1 |
| FORCE-01 SC#4 | 단정 표현 ("근육 힘 방향 확정") 출력 부재 | unit (AST grep gate) | `pytest tests/phase09/test_force_pattern_copy_no_forbidden.py -x` | ❌ Wave 1 |
| FEED-02 | 18 canned (sourceSignal × modeContext) + 부위별 어휘 (jointHint) | unit | `pytest tests/phase09/test_force_pattern_copy_render.py -x` | ❌ Wave 1 |
| D-09-A2 guard | axisMetrics.severity 사용 0 회 + axis warnings 무시 룰 | unit + AST grep | `pytest tests/phase09/test_force_pattern_no_severity_use.py -x` (AST 검사 — force_pattern.py 안 `.severity` 키 액세스 0회) | ❌ Wave 1 |
| D-09-B4 | 0 finding 시 `no_significant_force_pattern_signal` warning + fallback 본문 | unit | `pytest tests/phase09/test_infer_force_direction_pattern.py::test_no_signal_emits_fallback -x` | ❌ Wave 1 |
| D-09-B5 | 동일 pattern + 같은 phase 중복 차단, 다른 phase 는 OK | unit | `pytest tests/phase09/test_force_pattern_ranking.py::test_pattern_dedup_by_phase -x` | ❌ Wave 1 |
| D-09-C2 | motion_id 인식 시 confidence × 1.05 cap 1.0, ranking 전 적용 | unit | `pytest tests/phase09/test_force_pattern_ranking.py::test_motion_id_boost_before_ranking -x` | ❌ Wave 1 |
| D-09-D1 | 3-way schema lockstep (TS / Python / docs §9.11) | unit | `pytest tests/phase09/test_force_pattern_lockstep.py -x` | ❌ Wave 0 |
| D-09-U4 | camelCase 자동 변환 (`source_signal` → `sourceSignal`, `joint_hint` → `jointHint`, `mode_context` → `modeContext`) | unit | `pytest tests/phase09/test_dataclass_to_camel_case_dict_phase9.py -x` | ❌ Wave 0 |
| D-09-U5 | Firestore scoped validator (`_validate_force_pattern_inference`) — nested list 거부 + warnings list[str] 허용 | unit | `pytest tests/phase09/test_firestore_lockstep_phase9.py -x` | ❌ Wave 0 |
| D-09-D6 | pipeline _process 가 modeContext 산출 (mode1 / mode3_first / mode3_progress) 후 inference 호출 | integration | `pytest tests/phase09/test_force_pattern_pipeline_wiring.py -x` | ❌ Wave 1 |

### Sampling Rate

- **Per task commit:** `pytest tests/phase09/ -x -q` (Wave 별 분할)
- **Per wave merge:** `pytest tests/ -x` (전체 회귀 — Phase 6/7/8/8.1 회귀 0 검증)
- **Phase gate:** Full suite green + `npm run typecheck` (`tsc --noEmit`) green + 금지 표현 grep gate 10/10 PASS + Wave 1 종료 시 belle 박제 검수 (D-09-E3)

### Wave 0 Gaps

- [ ] `backend/tests/phase09/__init__.py` — 신설
- [ ] `backend/tests/phase09/conftest.py` — fixture factory (`_make_axis_metric` / `_make_stability_metric` / `_make_contact_metric` / `_make_phase_boundary` helper)
- [ ] `backend/tests/phase09/fixtures/` — Phase 9 단위 test 용 dict fixture 또는 dataclass factory module
- [ ] `backend/tests/phase09/test_force_pattern_lockstep.py` — 3-way schema lockstep (TS Literal union ↔ Python frozenset ↔ docs §9.11 표) — Phase 8 `test_force_signals_lockstep.py` 미러
- [ ] `backend/tests/phase09/test_dataclass_to_camel_case_dict_phase9.py` — pipeline `_dataclass_to_camel_case_dict` 의 신설 3 필드 (source_signal / joint_hint / mode_context) 변환 검증 — Phase 7 `test_dataclass_to_camel_case_dict_phase7.py` 미러
- [ ] `backend/tests/phase09/test_firestore_lockstep_phase9.py` — `_validate_force_pattern_inference` 검증 (PASS + reject case 4종 — nested dict / list[list] / list[non-whitelist] / non-scalar warnings entry) — Phase 8 `test_firestore_lockstep.py` 미러

### Wave 1 Gaps

- [ ] `backend/tests/phase09/test_infer_force_direction_pattern.py` — 6 signal detection 별 임계 경계 케이스 (각 signal 별 ON / OFF / phase 미인식 fallback) + 0/1/2/3 finding 케이스 + warnings 무시 룰 (axis warning 3종) + phase_metric_confidence_factor 검증
- [ ] `backend/tests/phase09/test_force_pattern_ranking.py` — Top-3 sort + tie-break (phase priority / signal priority / confidence DESC) + motion_id 보강 위치 + pattern 중복 차단 (D-09-B5 — 동일 pattern 같은 phase 차단, 다른 phase OK)
- [ ] `backend/tests/phase09/test_force_pattern_copy_render.py` — 18 canned 매핑 lookup PASS + mode 분기 prefix 검증 + jointHint 부위 어휘 단위 검증
- [ ] `backend/tests/phase09/test_force_pattern_copy_no_forbidden.py` — AST 기반 10 금지 표현 grep gate (research §10.2 6종 + Phase 9 신규 4종) — Phase 7 `test_copy_templates_no_forbidden.py` 미러 + `\d+%\s*감점` regex 단위 1건 추가
- [ ] `backend/tests/phase09/test_force_pattern_no_severity_use.py` — D-09-A2 정합: `force_pattern.py` 의 AST 분석 — `axis_metric.severity` / `axisMetric.severity` 액세스 0회 검증. stabilityMetric.severity / contactMetric.severity 는 허용.
- [ ] `backend/tests/phase09/test_force_pattern_pipeline_wiring.py` — pipeline `_process` mock 통합 test — mode1 / mode3_first (prev 없음) / mode3_progress (prev 있음) 3 case 각각 modeContext 정합 + complete_analysis 호출에 `force_pattern_inference` kwarg 포함 검증

### 회귀 차단 (Existing Suite)

- `cd backend && pytest tests/phase06/ tests/phase07/ tests/phase08/ tests/phase08_1/ -x` — Phase 9 wave 1 종료 후 모두 PASS 검증 (Phase 8 8/8 / Phase 8.1 25/25 evidence 박제 회귀 0).
- `cd app && npm run typecheck` — TS strict mode + ForcePatternInference / ForcePatternFinding 신설 type compile 검증 (Phase 8 정합).
- `git diff app/src/types/analysis.ts backend/shared/python/sunity_shared/analysis/force_pattern.py docs/contract.md` — Wave 0 atomic commit lockstep manual check.

### Wave 2 (production sweep) — 본 phase OUT of scope (D-09-E2)

- Phase 11 통합 시점 (CoachCommentHook + Gemini 자연어 번역) → mode1/mode3 실 영상 sweep → Phase 9 finding 분포 검증 (정은지 = 대부분 0~1 finding low confidence + 학생 = 1~3 finding medium confidence).
- Phase 15 (Mode 1·Mode 3 실영상 + TestFlight) → 종합 production validation.

## Security Domain

> `security_enforcement` flag 미설정 (default = enabled). 본 phase 는 데이터 처리 layer (Firestore 저장) — auth / session / crypto 차원 신규 없음, 입력 validation 만 핵심.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 본 phase = backend pipeline 내부 호출 (Firebase Auth 는 upload-url / reference-api 책임) |
| V3 Session Management | no | 본 phase = stateless pure function |
| V4 Access Control | no | Firestore rules + Lambda IAM (Phase 8 박제 — 본 phase 변경 X) |
| V5 Input Validation | **yes** | `ForcePatternFinding` `__post_init__` validator (frozen dataclass) + `_validate_force_pattern_inference` Firestore scoped validator |
| V6 Cryptography | no | 본 phase = data layer only |

### Known Threat Patterns for Pure-Function Backend Layer

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted ForceSignalsReport 입력 (예: malicious `warnings` 안 거대한 list 또는 type 변종) | Tampering | `__post_init__` validator 가 frozen dataclass + Literal enum 검증, 비정합 시 ValueError raise (caller 가 catch → fail_analysis) |
| Firestore nested-array attack (writeflow client 가 nested 의 list[list] 박제) | Tampering | `_validate_force_pattern_inference` scoped validator — list[list] / list[dict] (non-finding) 거부 |
| canned 본문 escape (외부 입력이 canned KO 본문에 inject) | Tampering | canned 본문은 모듈-level dict literal singleton (외부 입력 무관) — `force_pattern_canned_text()` lookup 만 |
| LLM prompt injection via finding.interpretation | Tampering | Phase 11 책임 (Phase 9 = canned only — interpretation 본문이 모듈 literal singleton, 외부 input 0) |
| Confidence 조작 (외부에서 0.99 강제) | Spoofing | Phase 9 confidence 산출 = base × cf × motion_id_boost — caller-controlled 항목 0. all internal source. |
| 단정 표현 회귀 (refactor 시 누군가 "X% 감점" 같은 문구 부주의 박제) | Repudiation | AST grep gate 10/10 + CI 회귀 차단 |

## Sources

### Primary (HIGH confidence — verified)

- `[VERIFIED: 직접 inspect]` `backend/shared/python/sunity_shared/analysis/force_signals.py` (1-250 + 1500-1700) — Phase 8/8.1 입력 schema + 임계 상수 + helper
- `[VERIFIED: 직접 inspect]` `backend/shared/python/sunity_shared/analysis/copy_templates.py` (1-334) — Phase 7 canned mapping 패턴 (force_pattern_copy.py source)
- `[VERIFIED: 직접 inspect]` `backend/shared/python/sunity_shared/firestore_admin.py` (100-322) — `_validate_force_signals_report` + `complete_analysis` 시그니처
- `[VERIFIED: 직접 inspect]` `backend/functions/pipeline/app.py` (690-1141) — `_dataclass_to_camel_case_dict` + `compute_force_signals` wiring + `_mode3_comparison`
- `[VERIFIED: 직접 inspect]` `backend/shared/python/sunity_shared/analysis/assemble.py` (1-100, 230-310) — `build_dimension_explanation` mode 분기 + `build_mode3(is_first)` 패턴
- `[VERIFIED: 직접 inspect]` `backend/judging_data/tilt_thresholds.yaml` — `ipsf_tolerance.tolerance_deg = 20.0` (Phase 8.1 D-03 박제 단일 source)
- `[VERIFIED: 직접 inspect]` `app/src/types/analysis.ts` (170-200, 460-635) — 현 ForceSignalsReport TS interface + AnalysisResult.forceSignalsReport
- `[VERIFIED: 직접 inspect]` `app/src/lib/userAnalyses.ts` (1-100) — normalize null-guard 패턴 (Phase 8 forceSignalsReport 박제)
- `[VERIFIED: 직접 inspect]` `docs/contract.md` (793-990) — §9 ForceSignalsReport 명세 (Phase 9 §9.11 신설 source)
- `[VERIFIED: 직접 inspect]` `docs/research/02_힘방향_힘조절_엔진_FINAL.md` (120-435) — §4.1 / §4.2 / §8 / §9.2 / §10.1 / §10.2 / §11 (단일 도메인 source)
- `[VERIFIED: 직접 inspect]` `.planning/phases/08-jerk-jitter/08-CONTEXT.md`, `.planning/phases/08.1-axis-metric-redesign/08.1-CONTEXT.md` (D-05 line 50-52 직접 박제), `.planning/phases/07-difference-classification/07-CONTEXT.md`, `.planning/phases/09-forcedirectionpattern-3/09-CONTEXT.md`
- `[VERIFIED: 직접 inspect]` `backend/tests/phase07/test_copy_templates_no_forbidden.py` (1-80) — AST grep gate 패턴
- `[VERIFIED: 직접 inspect]` `backend/tests/phase09/` 디렉토리 부재 확인 (신설 필요) — `ls` via `gsd-sdk init.phase-op`

### Secondary (MEDIUM confidence — cross-referenced)

- `[CITED: .planning/ROADMAP.md §Phase 9 line 277-291]` — goal + SC + axis raw signal only guard
- `[CITED: .planning/REQUIREMENTS.md line 51-52, 60-61]` — FORCE-01 + FEED-02
- `[CITED: .planning/STATE.md line 6, 30, 60-82]` — Phase 8/8.1 close-out evidence + Phase 9 평행 진입 박제
- `[CITED: research/00_시스템_아키텍처_FINAL.md]` (CONTEXT.md 인용 — direct inspect 미실시) — 두 엔진 분리 + AI vs 코치 경계
- `[CITED: research/폴스포츠-지식.md]` (CONTEXT.md 인용 — direct inspect 미실시) — 부위 어휘 source

### Tertiary (LOW confidence — flagged for validation)

- `[ASSUMED]` pelvis_drop 임계 정량값 (10° / 20°) — 본 RESEARCH §"Pitfall 1" 의 정은지 분포 기반 inference. plan 단계 belle 검수 필수.
- `[ASSUMED]` 18 canned KO interpretation 본문 — 본 RESEARCH 가 톤만 박제, 실 본문은 planner draft + belle 검수 필요.
- `[ASSUMED]` jointHint 부위 어휘 매핑 — A3 가정. belle 검수 필요.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 신규 의존성 0, 기존 numpy / pyyaml / pytest 박제.
- Architecture: HIGH — 모든 패턴이 Phase 6/7/8/8.1/12.5 직접 mirror, 신설 패턴 0.
- Schema (Wave 0): HIGH — Phase 8 ForceSignalsReport schema 패턴 + Phase 7 BodyComparisonFinding 패턴 합성.
- Inference 알고리즘 (Wave 1): MEDIUM — D-09-A1~A5 + D-09-B1~B5 locked, 단 pelvis_drop 임계 + 18 canned 본문 + jointHint 매핑 = belle 검수 필요 (Assumption A1/A3/A5).
- Pitfalls: HIGH — Phase 8/8.1 verifier evidence + 본 직접 inspect 합성.
- Testing: HIGH — Phase 7/8 단위 test 패턴 직접 mirror, 신설 패턴 0.
- Security: HIGH — pure function + frozen dataclass + scoped validator 3 축 박제.

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (30 days — Phase 8/8.1 산출 stable, 본 phase 의 입력 schema 변경 위험 0).
