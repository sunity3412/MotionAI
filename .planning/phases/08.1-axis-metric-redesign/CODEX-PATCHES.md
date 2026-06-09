---
phase: 08.1-axis-metric-redesign
type: iteration-2-patches
status: archived-2026-06-09-merged-into-plans
created: 2026-06-09
archived_at: 2026-06-09
review_origin: 08.1-DIRECT-REVIEW.md (Codex iteration 1)
applies_to: [08.1-00-PLAN.md, 08.1-01-PLAN.md, 08.1-02-PLAN.md]
merged_status: |
  Codex iteration 2 review (08.1-DIRECT-REVIEW-ITERATION2.md) found dual
  source of truth conflict between this patches doc and plan bodies. Per
  belle decision (2026-06-09 "단일 source of truth로 잠그는 것"), all
  C-B1/C-H1/C-H2/C-H3/C-M1/C-M3/C-M4/C-M5/C-MH1 patches were merged
  DIRECTLY into the 3 plan files + 08.1-CONTEXT.md + ROADMAP.md. This
  doc is preserved as history only — DO NOT treat as override or active
  spec. Plan bodies are now the single source of truth.
---

> **ARCHIVED 2026-06-09** — content merged into plan bodies. Read 08.1-00/01/02-PLAN.md + 08.1-CONTEXT.md + ROADMAP.md for current spec. This doc retained only for audit trail of Codex iteration 1 findings.



# Phase 8.1 Codex Patches — Iteration 2

**목적**: Codex `08.1-DIRECT-REVIEW.md` 가 발견한 1 BLOCKER + 4 HIGH + 1 MED-HIGH + 4 MEDIUM 을 3 plans 위에 patch 박제. plans 본문 큰 재작성 없이 본 문서가 iteration 2 단일 spec. execute-phase 진입 시 executor 가 plans + 본 patches 두 source 동시 따름.

belle 결정 (2026-06-09): "수정 하고 외부 AI 한번 더 돌리자" — 본 iteration 2 적용 후 belle 가 Codex review 재진입.

---

## C-B1 (BLOCKER) — coordinate_space references in compute_force_signals 정리

**Codex 발견**: 08.1-00 가 `AxisDeviationMetric.coordinate_space` 필드를 제거하지만, `compute_force_signals()` body L1743-1745 가 여전히 `m.coordinate_space == "unavailable"` 참조 → Wave 0 commit 직후 AttributeError.

**확인 (grep evidence)**: `backend/shared/python/sunity_shared/analysis/force_signals.py` L1743-1745:
```python
if axis_metrics and all(
    m.coordinate_space == "unavailable" for m in axis_metrics
):
    warnings_top.append("coordinate_space_unavailable")
```

**Fix (08.1-00 Wave 0 Task 1 에 추가)**:
- L1743-1745 block 제거 (`coordinate_space_unavailable` warning 자체 제거 — distance 차원 부재 이므로 의미 없음)
- 또는 Wave 0 transitional stub 검출 로직으로 교체:
  ```python
  if axis_metrics and all(
      "phase_8_1_wave_0_transitional" in (m.warnings or [])
      for m in axis_metrics
  ):
      warnings_top.append("axis_metric_transitional")
  ```
- 회귀 test 추가: `test_compute_force_signals_does_not_reference_coordinate_space` — grep guard.

**Affected files**:
- `backend/shared/python/sunity_shared/analysis/force_signals.py` L1743-1745 (수정)
- `backend/tests/phase08_1/test_compute_force_signals_axis_cleanup.py` (신설 — grep guard)

---

## C-H1 (HIGH) — Wave 0 stub low masking + axis_metric_transitional

**Codex 발견**: Wave 0 stub 의 `severity='low'` 가 "측정 안 됨" 을 "낮은 위험" 으로 silently 변환. Phase 8 fail pattern 재발 위험.

**Fix (08.1-00 + 08.1-02 양쪽 적용)**:

### 08.1-00 (Wave 0 stub design)
- stub 의 warnings 그대로 (`['phase_8_1_wave_0_transitional']`)
- 추가: `compute_force_signals()` 의 top-level `warnings_top` 에 `axis_metric_transitional` 박제 (C-B1 의 fix block 활용)
- 추가: 본 plan 의 must_haves 에 명시: "**Wave 0 stub 는 production 진입 금지** — Wave 0 + Wave 1 한 release boundary 로 ship. Pod 재배포 (08.1-02 Wave 2) 시점 까지 stub 만 배포된 상태 없음."

### 08.1-02 (downstream guard)
- Task 2 sweep 검증 추가: forceSignalsReport.warnings 에 `axis_metric_transitional` 있으면 sweep FAIL → Pod 재배포 미완 (Wave 1 commit Pod 도달 안 됨)
- 추가: SWEEP-EVIDENCE.md §10 "Phase 8.1 verifier 진입 준비" 직전 새 §0 "Stub 검출 게이트" — `axis_metric_transitional` warning 0 건 확인.

### Phase 9 guard (Phase 9 의 별도 plan 작성 시 명시)
- Phase 9 가 `axis severity` 직접 trust 금지. raw `shoulder_tilt` + `hip_tilt` + `confidence` + `warnings` 만 사용. severity 는 `warnings` 가 `axis_metric_transitional` 또는 `tilt_unavailable` 포함 시 무시.

**Affected files**:
- `backend/shared/python/sunity_shared/analysis/force_signals.py` (stub 본문 + top-level warning)
- `.planning/phases/08.1-axis-metric-redesign/08.1-00-PLAN.md` must_haves
- `.planning/phases/08.1-axis-metric-redesign/08.1-02-PLAN.md` Task 2 + SWEEP-EVIDENCE schema

---

## C-H2 (HIGH) — P90 → max(P100 + margin, IPSF floor)

**Codex 발견**: P90 calibration 으로는 25/25 low acceptance 보장 안 됨. 분포 interpolation 에 따라 top sample 이 medium 됨. **belle 가 Codex 전략 동의** (2026-06-09): "P90이 아니라 max observed + margin 방식".

**Fix (08.1-01 Wave 1 Task 2)**:

### tilt_thresholds.yaml schema 변경
```yaml
version: "1.1"   # iteration 2 (C-H2 fix)
calibrated_at: <ISO timestamp>
source:
  sweep_uid: sweep_phase8_1780986673
  sample_size: 25  # 5 영상 × 5 phase
  source_doc_ids: [<5 Firestore doc ids>]
  null_tilt_verified: true  # C-H3 정합
shoulder_tilt:
  distribution:  # visibility only (운영 cutoff 도출에 안 씀)
    p25: <float>
    p50: <float>
    p75: <float>
    p90: <float>
    p100: <float>   # max observed
  operational_cutoff:
    margin_deg: 5.0  # max+margin 의 margin
    medium_cutoff_deg: max(p100 + margin_deg, ipsf_tolerance_deg)
    high_cutoff_deg: max(medium_cutoff_deg * 1.5, ipsf_major_fault_deg)
hip_tilt:
  # 동일 구조
ipsf_tolerance:
  source_ref: "NotebookLM citation 9 Page 87 Glossary + Aerial Pole CoP Page 63 S55 Iron X ±20°"
  tolerance_deg: 20.0
  major_fault_deg: 40.0  # IPSF major fault 추정 (논의 필요)
```

### calibrate_tilt_thresholds.py 변경
- P90 산출 제거 → P25/P50/P75/P90/P100 모두 산출 + medium_cutoff = max(P100 + margin, IPSF floor) 박제
- margin_deg 기본 5.0 (belle 조정 가능)
- output: yaml + stdout 분포 표 + medium/high cutoff 값 + 사용 근거 (margin 또는 IPSF floor 어느쪽이 더 큰지)

### Severity 로직 (force_signals.py)
- 비교 규칙 epsilon-safe: `severity_medium = (tilt > medium_cutoff_deg + 1e-9)` (boundary value 가 medium 안 되도록)
- 또는 `severity_low = (tilt <= medium_cutoff_deg)` 명시 (Codex strict comparison rule)

### 회귀 test
- `test_calibration_uses_max_plus_margin` — yaml.operational_cutoff.medium_cutoff_deg == max(p100 + margin, ipsf_tolerance_deg)
- `test_severity_boundary_value_is_low` — tilt == medium_cutoff_deg 시 severity='low'

**Affected files**:
- `backend/judging_data/tilt_thresholds.yaml` (schema 변경)
- `backend/scripts/calibrate_tilt_thresholds.py` (P90 → max+margin)
- `backend/shared/python/sunity_shared/analysis/force_signals.py` (severity 비교 boundary epsilon)
- `backend/tests/phase08_1/test_tilt_thresholds_calibration.py` (test 갱신)
- `.planning/phases/08.1-axis-metric-redesign/08.1-01-PLAN.md` Task 2

---

## C-H3 (HIGH) — Calibration source verify 25 non-null real tilt

**Codex 발견**: Firestore reachability 만 검증, 25 non-null real tilt 검증 부재. transitional stub 값 (`shoulder_tilt=None`) 으로 calibrate 시 fallback warning 만 박제. partial data calibration 위험.

**Fix (08.1-01 Wave 1 Task 2 — calibrate script preflight)**:

```python
def _preflight_calibration_source(sweep_uid: str) -> None:
    """C-H3 fix — 25 non-null real tilt 검증."""
    db = firestore_admin._db()
    docs = list(db.collection("users").document(sweep_uid)
                .collection("analyses").stream())
    if len(docs) != 5:
        raise RuntimeError(
            f"Expected 5 영상, found {len(docs)} in sweep_uid={sweep_uid}"
        )
    null_tilt_count = 0
    transitional_count = 0
    for snap in docs:
        d = snap.to_dict() or {}
        ax = (d.get("result") or {}).get("forceSignalsReport", {}).get("axisMetrics", [])
        if len(ax) != 5:
            raise RuntimeError(
                f"Expected 5 phase, found {len(ax)} in doc={snap.id}"
            )
        for m in ax:
            if m.get("shoulderTilt") is None or m.get("hipTilt") is None:
                null_tilt_count += 1
            if "phase_8_1_wave_0_transitional" in (m.get("warnings") or []):
                transitional_count += 1
    if null_tilt_count > 0:
        raise RuntimeError(
            f"Calibration source has {null_tilt_count} null tilt — "
            "Wave 0 stub values detected. Re-sweep after Wave 1 deploy."
        )
    if transitional_count > 0:
        raise RuntimeError(
            f"Calibration source has {transitional_count} transitional warnings — "
            "Wave 0 stub residue. Re-sweep after Wave 1 deploy."
        )
```

### yaml schema 갱신 (C-H3 정합)
- `source.null_tilt_verified: true` 필드 신설 (calibrate script 가 검증 후 true 박제)
- `source.source_doc_ids: [<5 doc ids>]` 명시 박제

### 회귀 test
- `test_calibration_preflight_rejects_null_tilt` — synthetic null tilt 입력 시 RuntimeError
- `test_calibration_preflight_rejects_transitional` — synthetic transitional warning 입력 시 RuntimeError
- `test_calibration_preflight_passes_real_tilt` — Phase 8 sweep_phase8_1780986673 (실제 source) 사용 시 PASS

**Affected files**:
- `backend/scripts/calibrate_tilt_thresholds.py` (preflight 신설)
- `backend/judging_data/tilt_thresholds.yaml` schema (source.null_tilt_verified, source.source_doc_ids)
- `backend/tests/phase08_1/test_tilt_thresholds_calibration.py` (3 신설 test)

---

## C-MH1 (MEDIUM-HIGH) — Metric rename 검토

**Codex 발견**: `AxisDeviationMetric` 이름이 의미 overclaim (distance 없는데 deviation 명).

**Codex 추천**:
- Best: `AxisTiltMetric` 또는 `BodyLineTiltMetric` rename
- Acceptable: 이름 유지 + docstring caveat

**belle 미명시 — 본 iteration 2 의 결정**: **Acceptable 옵션 적용** (이름 유지 + docstring caveat). 이유:
- Rename 은 TS interface + Python dataclass + docs §9.3 + tests + frontend 영향 → 작업량 큼
- 본 iteration 2 의 목적 = 도메인/단위 정합 fix. rename 은 cosmetic.
- belle 가 이후 rename 추진 결정 시 별도 plan (예: 08.2 metric-rename) 으로 분리 가능.

**Fix (양쪽 docstring + ROADMAP 메모)**:

### 08.1-00 Wave 0 Task 1 의 dataclass docstring + TS interface JSDoc
```python
@dataclass(frozen=True)
class AxisDeviationMetric:
    """body line tilt signal — shoulder/hip tilt 만 산출 (no distance).

    Phase 8.1 (2026-06-09) 가 distance 차원 제거 — IPSF Code of Points 에
    글로벌 axis deviation deduction 부재 (NotebookLM citation 9 Page 87
    Glossary). 본 metric 은 IPSF deduction 이 아니며 global correctness
    score 도 아님. shoulder/hip tilt 만 측정 — 기술 조건부 axis 평가는
    Phase 11 GeometricCriterion 담당.

    이름 'AxisDeviation' 은 historical naming (Phase 8 박제). 의미 정합
    rename 후보 = BodyLineTiltMetric (Codex 추천). 본 iteration 미적용,
    belle 결정 시 별도 plan.
    """
    phase: PhaseLabel
    shoulder_tilt: float | None
    hip_tilt: float | None
    severity: SeverityLevel
    confidence: MetricConfidence
    warnings: list[str]
```

### docs/contract.md §9.3
```markdown
### §9.3 AxisDeviationMetric (Phase 8.1 — Body Line Tilt Signal)

> **Naming note** (Phase 8.1, 2026-06-09): 본 metric 의 이름은
> historical (Phase 8 distance 시절). distance 차원 제거 후 의미적으로
> "body line tilt" 가 정확. 의미 정합 rename (e.g., `BodyLineTiltMetric`)
> 은 미래 plan 으로 분리. 본 metric 은 IPSF Code of Points 의 어떤
> global deduction 도 아님.
```

**Affected files**:
- `backend/shared/python/sunity_shared/analysis/force_signals.py` dataclass docstring
- `app/src/types/analysis.ts` interface JSDoc
- `docs/contract.md` §9.3 메모
- `.planning/ROADMAP.md` Phase 8.1 "Future: AxisDeviationMetric → BodyLineTiltMetric rename 별도 plan"

---

## C-M1 (MEDIUM) — 2D fallback undirected angle normalization

**Codex 발견**: 5° vs 185° = same physical line (undirected). modulo 180° normalization 부재 시 keypoint ordering artifact → artificial high tilt.

**Fix (08.1-01 Wave 1 Task 1)**:

### compute_axis_deviation 의 2D fallback path (현재 보존된 helper)
```python
def _normalize_angle_undirected(angle_deg: float) -> float:
    """undirected line angle → [0, 90] 정규화.

    C-M1 fix (Codex 2026-06-09) — 5° vs 185° = same physical line.
    keypoint ordering artifact (left/right swap) 차단.
    """
    a = angle_deg % 180.0   # [0, 180)
    if a > 90.0:
        a = 180.0 - a       # [0, 90]
    return a
```

### 적용 위치
- `_shoulder_tilt_2d` (보존된 helper) 의 반환값에 `_normalize_angle_undirected` 적용
- `_hip_tilt_2d` 동일

### Unit tests (4 case)
- vertical (90° expected)
- horizontal (0° expected)
- near-180 (5° → 5°)
- swapped keypoints (185° → 5°, 즉 동일 결과)

**Affected files**:
- `backend/shared/python/sunity_shared/analysis/force_signals.py` (`_normalize_angle_undirected` 신설 + 2D tilt helper 정합)
- `backend/tests/phase08_1/test_axis_2d_angle_normalization.py` (신설)

---

## C-M3 (MEDIUM, 사실상 HIGH) — Sensitivity evidence (synthetic)

**Codex 발견**: 정은지 25/25 low 만 acceptance 면 "threshold 너무 높아 아무것도 안 잡힘" 위험. **negative evidence 동시 검증 필수** — belle 가 명시 동의 (2026-06-09).

**Fix (08.1-02 Wave 2 추가 task)**:

### Task 2.5 — Synthetic sensitivity suite

`backend/scripts/synthetic_sensitivity_check.py` 신설:
- input: tilt_thresholds.yaml + force_signals.py 의 severity 로직
- synthetic case 5개 생성:
  1. shoulder_tilt = medium_cutoff_deg + 1° → severity='medium' 기대
  2. shoulder_tilt = medium_cutoff_deg - 1° → severity='low' 기대
  3. shoulder_tilt = high_cutoff_deg + 1° → severity='high' 기대
  4. hip_tilt = high_cutoff_deg + 10° → severity='high' 기대
  5. shoulder_tilt + hip_tilt 모두 0° (perfect vertical) → severity='low' 기대
- 각 case 결과 = expected match 확인
- output: stdout 표 + SWEEP-EVIDENCE 의 §sensitivity section 박제

### SWEEP-EVIDENCE §11 (신설 section) — Sensitivity Evidence
```markdown
## §11 Sensitivity Evidence (C-M3)

Synthetic high-tilt cases (정은지 negative — 의도된 'medium'/'high'):

| Case | shoulder_tilt (deg) | hip_tilt (deg) | Expected severity | Observed severity |
|------|--------------------|----------------|-------------------|-------------------|
| Just above medium | medium_cutoff + 1 | 0 | medium | medium ✓ |
| Just below medium | medium_cutoff - 1 | 0 | low | low ✓ |
| Above high | high_cutoff + 1 | 0 | high | high ✓ |
| Hip high | 0 | high_cutoff + 10 | high | high ✓ |
| Perfect vertical | 0 | 0 | low | low ✓ |

**결론**: metric 이 정은지 (elite reference) 만 'low' 로 통과시키는 것이
아니라, 실제 axis tilt 가 있는 경우 medium/high 로 검출됨을 증명.
```

### 회귀 test
- `test_sensitivity_synthetic_above_medium_triggers_medium`
- `test_sensitivity_synthetic_above_high_triggers_high`
- `test_sensitivity_synthetic_perfect_vertical_is_low`

### Future (선택): perturbed real sample
- belle 가 정은지 영상 1개 의 keypoints 에 synthetic perturbation (예: shoulder_tilt + 30°) 추가하여 medium/high 검출 확인
- 미적용 — 본 iteration 2 의 synthetic case 로 충분

**Affected files**:
- `backend/scripts/synthetic_sensitivity_check.py` (신설)
- `backend/tests/phase08_1/test_sensitivity_synthetic.py` (3 신설 test)
- `.planning/phases/08.1-axis-metric-redesign/08.1-02-PLAN.md` Task 2.5
- `.planning/phases/08.1-axis-metric-redesign/08.1-SWEEP-EVIDENCE.md` §11

---

## C-M4 (MEDIUM) — Phase 9 raw signal only guidance

**Codex 발견**: 08.1 가 Phase 9 평행 진입 권장. Phase 9 가 `axis severity == low` 를 line quality correctness 로 trust 시 Phase 8 fail pattern 재발 위험.

**Fix (Phase 9 plan 작성 시 명시 — 본 iteration 2 의 docs only)**:

### 08.1-CONTEXT.md D-05 갱신 메모 박제
```markdown
### D-05 Phase 9 Parallel Entry — Raw Signal Only (C-M4 정합)

Phase 9 가 `forceSignalsReport.axisMetrics[*].severity` 직접 trust 금지.
대신 `shoulder_tilt` + `hip_tilt` + `confidence` + `warnings` raw 신호
만 사용. severity 는 `warnings` 가 `axis_metric_transitional` 또는
`tilt_unavailable` 포함 시 무시.

이유 (Codex C-M4): Phase 8.1 의 calibration 은 정은지 5영상 기반 elite
false-positive 차단 만 검증. 진짜 production validity 는 Phase 8.1 의
sensitivity evidence + Phase 9 의 실 영상 검증 후 확정.
```

### ROADMAP Phase 9 entry 메모 박제
"Phase 9 의 axis 처리는 raw shoulder/hip tilt + warnings 만 사용 (Phase 8.1 의 C-M4 guard)."

**Affected files**:
- `.planning/phases/08.1-axis-metric-redesign/08.1-CONTEXT.md` D-05 갱신
- `.planning/ROADMAP.md` Phase 9 entry 메모

---

## C-M5 (MEDIUM) — Sweep script hygiene

**Codex 발견**: `sweep_phase8_1.py` 의 evidence trail 강화 필요 — commit hash, threshold checksum, S3 cleanup, fallback fail.

**Fix (08.1-02 Wave 2 Task 0 — sweep_phase8_1.py 신설 시 박제)**:

### sweep_phase8_1.py 추가 기능
1. **timestamp**: epoch ms 사용 (Firestore evidence 와 정합)
2. **commit hash 기록**: `subprocess.run(["git", "rev-parse", "HEAD"])` 결과 stdout + Firestore docs 의 sourceLabel 박제
3. **threshold checksum**: `hashlib.sha256(open("backend/judging_data/tilt_thresholds.yaml", "rb").read()).hexdigest()` 결과 stdout + sourceLabel 박제
4. **S3 cleanup**: sweep 종료 후 `sweep_temp/<sweep_uid>/` prefix S3 객체 5개 일괄 삭제 (lifecycle policy 대신 명시 cleanup)
5. **Fallback fail**: tilt_thresholds.yaml 의 `version` 필드 확인 → version < 1.1 (iteration 2 calibration 미적용) 시 RuntimeError + 명시 메시지 ("Run calibrate_tilt_thresholds.py first")
6. **--allow-fallback flag**: 명시적 fallback-mode test 시 step 5 우회 (Wave 0 stub 검증 등 의도된 fallback)

### CLI 갱신
```bash
python backend/scripts/sweep_phase8_1.py \
  --sweep-uid sweep_phase8_1_<ts_ms> \
  --videos ref-invert,ref-climb,ref-foxtop,ref-foxtop-split,ref-sideway-spin \
  [--allow-fallback]    # explicit fallback-mode test
  [--dry-run]
```

### SWEEP-EVIDENCE §1 Sweep metadata 갱신
- `commit_hash`, `threshold_checksum`, `cleanup_done: true`, `version_check_passed: true` 박제

**Affected files**:
- `backend/scripts/sweep_phase8_1.py` (Task 0 신설 시 hygiene 박제)
- `.planning/phases/08.1-axis-metric-redesign/08.1-02-PLAN.md` Task 0 (CLI + hygiene)
- `.planning/phases/08.1-axis-metric-redesign/08.1-SWEEP-EVIDENCE.md` §1 (metadata)

---

## 요약 — Iteration 2 changes per plan

### 08.1-00-PLAN.md
- **must_haves** 추가: "Wave 0 stub production 진입 금지 — 08.1-01 와 한 release boundary" (C-H1)
- **Task 1** 추가 step: `compute_force_signals()` L1743-1745 의 `coordinate_space` 참조 제거 + 회귀 test grep guard (C-B1)
- **Task 1** 추가 step: `axis_metric_transitional` top-level warning 박제 (C-H1)
- **dataclass docstring**: naming caveat 박제 (C-MH1)

### 08.1-01-PLAN.md
- **Task 2 calibration** 변경: P90 → `max(P100 + margin_deg, ipsf_tolerance_deg)` (C-H2)
- **Task 2 preflight** 신설: 25 non-null + transitional warning 0 검증 (C-H3)
- **yaml schema** 변경: version "1.1", distribution + operational_cutoff + source.null_tilt_verified + source_doc_ids (C-H2 + C-H3)
- **Task 1** 추가: `_normalize_angle_undirected` 신설 + 2D fallback 정합 + 4 unit test (C-M1)
- **severity 로직**: epsilon-safe boundary 비교 (C-H2 strict comparison)

### 08.1-02-PLAN.md
- **Task 0 sweep script**: hygiene 5종 (timestamp ms / commit hash / threshold checksum / S3 cleanup / fallback fail + --allow-fallback) (C-M5)
- **Task 2 sweep 검증** 추가: `axis_metric_transitional` warning 0 건 확인 (C-H1 downstream guard)
- **Task 2.5 신설**: Synthetic sensitivity check + SWEEP-EVIDENCE §11 (C-M3)
- **SWEEP-EVIDENCE.md** schema 갱신:
  - §0 신설 — Stub 검출 게이트 (C-H1)
  - §1 — commit_hash / threshold_checksum / cleanup_done (C-M5)
  - §11 신설 — Sensitivity Evidence (C-M3)

### 08.1-CONTEXT.md
- **D-05 갱신**: Phase 9 raw signal only guard (C-M4)

### ROADMAP.md
- Phase 8.1 entry: AxisDeviationMetric → BodyLineTiltMetric rename 별도 plan 메모 (C-MH1)
- Phase 9 entry: axis raw signal only guard 메모 (C-M4)

---

## Verification Path

본 patches 적용 후 belle 가:
1. 본 문서 검토 후 OK 시 commit + push
2. Codex review 재진입 — 본 문서 + 3 plans + 08.1-CONTEXT.md + 08.1-RESEARCH.md + PHASE8-INHERITED-ISSUES.md 모두 single evidence chain
3. Codex 가 HIGH 0 보고 시 execute-phase 진입 OK
4. HIGH 발견 시 iteration 3 또는 별도 plan 분리

belle 결정 박제 (2026-06-09):
- 전략 = Codex + belle 동의 (distance 삭제 / tilt-only 축소 / max+margin / synthetic sensitivity)
- 진행 = "수정 하고 외부 AI 한번 더 돌리자"
