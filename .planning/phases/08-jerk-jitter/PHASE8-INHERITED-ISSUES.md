---
phase: 08-jerk-jitter
type: inherited-issues
status: locked
created: 2026-06-09
inherits_to: 08.5-axis-metric-redesign
review_audience: cross-AI (Codex / Gemini / Claude review during Phase 8.5 plan-review-convergence)
---

# Phase 8 → Phase 8.5 Inherited Issues

**목적**: Phase 8 종료 후 발견된 axis metric 도메인 정합성 문제를 Phase 8.5 의 research/discuss/plan/review 단계에서 단일 evidence source 로 참조. 외부 AI reviewer 가 본 문서만 읽어도 Phase 8 의 어디서 무엇이 깨졌는지 판단 가능해야 함.

---

## TL;DR

Phase 8 의 `compute_axis_deviation` 산출 distance 값이 **도메인 정합성을 위반** — 정은지 (폴 세계챔피언) 5개 reference 영상 모든 phase 에서 `severity='high'` 출력. 도메인적으로 명백히 잘못된 결과. Phase 9/10 입력으로 그대로 사용 불가.

**핵심**: schema/wiring 은 정상. **distance metric 의 좌표계 정의 + threshold calibration 이 깨짐**.

Phase 8.5 는 axis metric 의 **수치 산출 자체를 재설계**해야 함. Phase 9 (force pattern 추론) 의 신뢰 가능한 axis 입력 박제가 목적.

---

## 1. 직접 관찰된 증거 (3차 sweep, 2026-06-09)

### sweep 환경

- `sweep_uid = sweep_phase8_1780986673`
- 5 reference videos (정은지): `ref-invert / ref-climb / ref-foxtop / ref-foxtop-split / ref-sideway-spin`
- 분석 경로: `pipeline._process()` direct call (race 회피 — `sweep_temp/` prefix, SQS 미발화)
- pose engine: RTMW (ONNX, GPU) + NLF alignment
- 좌표 공간: `pose_aligned 3D` (Phase 8 B' fix path 활성)
- 정규화 분모: `median_torso_length(space='pole_aligned')` (= ~54 units)

### axis distance 분포 (정은지 5/5 영상)

| 영상 | pelvis distance (phase 별, normalized by torso_length) | chest distance | shoulder tilt 범위 | hip tilt 범위 |
|------|-----------------------------------------------------|----------------|-------------------|---------------|
| ref-invert | 2.88 / 3.10 / 3.24 / 3.18 / **3.80** | 3.28 / 3.14 / 3.19 / 3.27 / 3.52 | 12° ~ 58° | 11° ~ 32° |
| ref-climb | 3.07 / 2.89 / 3.00 / 2.65 / 3.13 | 3.02 / 2.96 / 2.82 / 2.66 / 3.14 | 16° ~ 31° | 10° ~ 47° |
| ref-foxtop | 3.06 / 3.16 / 3.21 / 3.15 / 3.19 | 3.11 / 3.11 / 3.17 / 3.11 / 3.17 | 11° ~ 36° | 22° ~ 37° |
| ref-foxtop-split | 3.11 / 3.11 / 3.23 / 3.31 / 3.22 | 3.08 / 3.14 / 3.26 / 3.20 / 3.35 | 11° ~ 53° | 17° ~ 50° |
| ref-sideway-spin | 2.90 / 2.82 / 2.83 / 2.73 / 3.06 | 2.91 / 2.89 / 2.78 / 2.88 / 3.07 | 20° ~ 27° | 14° ~ 36° |

phase 순서: entry / lock / transition / final_shape / hold

**관찰**: pelvis distance 값 분포 = **2.65 ~ 3.80** (5영상 × 5 phase = 25 data points). 표준편차 작음. 영상 간 분산도 좁음.

### 현 thresholds

`backend/shared/python/sunity_shared/analysis/force_signals.py` 모듈 레벨 상수:
```python
AXIS_PELVIS_DISTANCE_THRESHOLDS = (0.3, 0.5)  # (medium_cutoff, high_cutoff)
AXIS_CHEST_DISTANCE_THRESHOLDS  = (0.3, 0.5)
AXIS_TILT_THRESHOLDS_DEG        = (15.0, 30.0)
```

**결과**: 정은지 pelvis distance 가 모두 2.65 이상 → 모두 `severity='high'` (threshold high=0.5 의 5배 이상).

### 출력 통계

| 차원 | 정은지 5/5 영상 결과 |
|------|--------------------|
| `axisCoordSpaces` | `pole_aligned` 5/5 (B' fallback path) |
| `axisSeverities` | `high` 5/5 ❌ |
| `axisWarnings` | `coordinate_space_pole_aligned_fallback` 5/5 |
| `direction` | `outward` 5/5 |
| `stabilitySeverities` | low/medium 혼합 (영상별 다름) — 분포 자연스러움 |
| `phaseSources` | `heuristic` 5/5 (Layer 2 unavailable warning — 다음 Phase 8.5 와 별개) |

---

## 2. Root Cause 분석

### 2.1 좌표계 원점 미정의

**현 구현** (`backend/shared/python/sunity_shared/analysis/pole/aligner.py`):

```python
def compute_alignment_matrix(pole_axis_direction):
    """폴 축 방향 → Z 축 정렬 회전행렬 (3×3)."""
    # scipy Rotation.align_vectors([0,0,1], [pole])
    return rot.as_matrix()

def apply_alignment(keypoints, R):
    """모든 키포인트에 R 적용 → pole-aligned 좌표 dict."""
    # 회전만 적용. translation 없음.
```

**의미**:
- pole 방향이 Z+ 로 정렬됨 ✓
- 하지만 **origin 은 RTMW pose engine 의 원래 원점 그대로** (회전 이후도 변경 없음)
- RTMW lift 결과의 원점이 무엇인지 명확히 정의되지 않음 (image 좌표계? camera 좌표계? hip-centered?)
- 즉 **"pelvis 가 폴 축으로부터 얼마나 떨어졌나"** 가 좌표계상 well-defined 가 아님

**증거 (직접 probe, 2026-06-09)**:
```
pose_frames count: 173
keypoints_2d: None  (RTMW 가 image 평면 좌표 미박제)
keypoints_3d: dict (15 joint name)
keypoints_3d_pole_aligned: dict (15 joint name)
median_torso_length(image_2d) = None
median_torso_length(world_3d) = 54.13660770623291
median_torso_length(pole_aligned) = 54.13660770623291
```

`pole_aligned` 와 `world_3d` 의 torso length 가 동일 — 회전만 적용됐기 때문. 즉 pole_aligned 는 단지 "rotated world_3d" 이며 origin 은 world_3d 의 origin.

**결과**: pelvis 가 origin 으로부터 (3 × torso_length) 떨어진 위치에 있을 수 있고, 그 값은 영상의 카메라 거리/줌/dancer 의 화면 위치에 따라 임의로 변동 — **"폴 축까지의 거리" 의미 부여 불가**.

### 2.2 Threshold 가 잘못된 단위 가정

Phase 8 plan 작성 당시 가정:
- distance = "image_2d 평면 normalized 0~1 좌표계 의 점-직선 수직거리"
- threshold (0.3, 0.5) = "frame 의 30%/50% 만큼 폴에서 떨어짐" (인체학적 의미)

실제 wiring 후:
- RTMW 는 `keypoints_2d` 미박제 → B' fix 가 `pole_aligned 3D` fallback
- pole_aligned distance 단위 = RTMW lift 출력의 임의 단위 (≈ 픽셀? 또는 normalized?)
- threshold (0.3, 0.5) 가 이 단위와 무관

### 2.3 결정적 단서

정은지 = 폴 세계챔피언 = axis 차원에서 사실상 reference truth (REVIEWS Suggestions §2 의 "sanity check distribution"). 그가 5/5 영상 모든 phase 에서 `high` = **시스템이 도메인 정합성을 위반** 한다는 가장 명확한 증거.

---

## 3. Phase 8 의 다른 부분은 살아있다

### 3.1 schema + wiring ✓

- `ForceSignalsReport` 3-way lockstep (TS + Python + docs §9) 완전
- pipeline `_process()` → `compute_force_signals()` wiring 정상
- Firestore scoped validator 작동
- Layer 2 default-off env switch + preflight ceiling 작동

### 3.2 tilt 데이터 ✓ (rotation-only, origin-invariant)

`shoulder_tilt` 와 `hip_tilt` = arcsin(|Δz| / ||Δ||) — 좌표계 origin 무관, 회전만 의존. 정은지 5/5 영상에서 자연스러운 분포 (10° ~ 58°). 동작에 따른 의미 보존:
- ref-invert (역위): shoulder tilt 58° (몸이 거꾸로 → 어깨 라인이 폴축과 큰 각)
- ref-sideway-spin: tilt 24~27° (옆 회전)
- ref-foxtop-split: hip tilt 50° (다리 split)

**Phase 9 가 이 tilt 데이터를 1차 신호로 사용 가능** — Phase 8.5 결과 기다리지 않고 평행 진입 가능 (의존성 일부 분리).

### 3.3 stability / jerk / contact ✓

- `jerkUnit='deg_per_sec_cubed'` FPS-normalized — 분포 자연스러움 (low/medium 혼합)
- `contactMetrics` 3 kind 분기 (keypoint/segment/region_proxy) 동작, 25 contact × 5 phase 정상 산출
- `phaseBoundaries` 5 phase (entry/lock/transition/final_shape/hold) 정상 분할

---

## 4. Phase 8.5 의 의사결정 공간

본 evidence 위에서 외부 AI 리뷰어가 평가해야 할 trade-off:

### 4.1 좌표계 fix 방향

| 옵션 | 의미 | 트레이드오프 |
|------|------|------------|
| α-1 | `pole_aligner` 에 translation 추가 (hip midpoint → origin) | pelvis = (0,0,0) 항상 → pelvis_distance metric 자체 의미 잃음 |
| α-2 | `pole_aligner` 에 translation: pole 검출 위치 → origin (image_2d pole_x → pole_aligned 의 origin 매핑) | 폴이 화면에 보여야 함, 카메라 calibration 필요 |
| α-3 | 좌표 fix 하지 않음 + metric 자체 변경 (absolute → relative displacement) | pelvis 의 phase 간 이동량 (jerk 같은 derivative) 만 사용 |
| α-4 | tilt-only metric + distance 차원 제거 | schema 변경 (axis 차원 축소) — IPSF axis 채점 항목 일부 미반영 |

### 4.2 Threshold calibration 방향

| 옵션 | 의미 | 트레이드오프 |
|------|------|------------|
| β-1 | 정은지 5영상 sweep distribution 의 median + N×stddev 기반 threshold | 5영상 = 작은 sample, fragile |
| β-2 | IPSF Code of Points 의 axis 채점 항목 (deduction range) 매핑 | 도메인 정합성 ↑, 그러나 IPSF 가 distance 수치를 직접 정의하지 않음 |
| β-3 | β-1 + β-2 combo: IPSF 의 정성 deduction (minor/major) 카테고리 + 정은지 분포 의 % 분위 매핑 | 가장 정직, 작업량 ↑ |

### 4.3 도메인 정합 어떤 metric 이 "축 이탈" 인가

본 evidence 가 외부 AI 에게 묻는 핵심 질문 — Phase 8.5 가 답해야 할 것:

> 폴스포츠 도메인 + IPSF 채점 관점에서 "축 이탈 (axis deviation)" 의 정의가 무엇인가? 본 문서의 정은지 sweep 결과를 reference 로 두었을 때, 어떤 metric 이 정은지 baseline 을 `severity='low'` 로 출력하고 학생 (예: 초보) 영상에서 `severity='medium'`/`'high'` 를 출력해야 도메인 정합 인가?

---

## 5. 코드 위치 (Phase 8.5 가 손볼 후보)

- `backend/shared/python/sunity_shared/analysis/pole/aligner.py` — alignment 좌표계 정의
- `backend/shared/python/sunity_shared/analysis/pole_geometry.py` — PoleLine2D / PoleAxisMeasurement / coordinate_space
- `backend/shared/python/sunity_shared/analysis/body_scale.py` — median_torso_length
- `backend/shared/python/sunity_shared/analysis/force_signals.py` — `compute_axis_deviation` (B' fallback path 포함, line 822-1240)
- `backend/shared/python/sunity_shared/analysis/force_signals.py` 모듈 레벨 상수 — `AXIS_*_THRESHOLDS`
- 3-way lockstep 동행 — `app/src/types/analysis.ts` AxisDeviationMetric + `docs/contract.md` §9

---

## 6. 외부 AI Reviewer 가 본 문서를 읽고 답해야 할 질문

1. Phase 8 의 어떤 가정이 처음부터 깨졌는지 (lockstep 단계에서 잡혔어야 할 사안인지)
2. 좌표계 fix (α-1 ~ α-4) 중 어느 옵션이 폴스포츠 도메인 + Phase 9/10 입력 정합성 관점에서 최적인지
3. Threshold calibration (β-1 ~ β-3) 중 어느 접근이 [[analysis-objectivity-no-human-scores]] memory invariant 와 정합인지
4. tilt-only 로 Phase 9 평행 진입 가능한지, 또는 distance 차원 박제 후 진입해야 하는지
5. 본 evidence 외에 Phase 8.5 plan 작성 전 추가로 확보해야 할 도메인/사실 자료가 있는지

---

## 7. Phase 8 본체에서 잘 한 부분 (Phase 8.5 가 보존해야 함)

- ForceSignalsReport schema 의 `coordinate_space` 필드 (image_2d / pole_aligned / world_3d / unavailable 박제) — 다중 좌표계 대응 contract 자체는 정합
- `warnings: list[str]` per metric — Phase 8.5 가 새 좌표계 도입 시 동행 warning 박제 가능
- Layer 2 `preflight_label_gate_passed` 3-state 제어 + `_min_confidence` ceiling — Phase 8.5 가 새 threshold 도입 시 동일 ceiling 패턴 재사용 가능
- `temporal_fill` 중복 호출 차단 + `jerkUnit='deg_per_sec_cubed'` FPS-normalized — 좌표계 변경과 무관, 그대로 보존
- contact `ContactPrimitiveKind` enum (keypoint/segment/region_proxy) — axis 와 별개, 보존

---

## 8. 본 문서의 위치 + 활용

- 본 문서 = Phase 8.5 의 **단일 evidence source**
- Phase 8.5 의 다음 artifacts 가 본 문서를 명시 참조:
  - `08.5-CONTEXT.md` (decision 기록) — §1, §4 의 evidence + 의사결정 박제
  - `08.5-RESEARCH.md` (research) — §4, §6 의 질문이 research scope
  - `08.5-PLAN.md` — §5 의 코드 위치 가 modification scope
  - cross-AI review prompts — §6 의 5 질문 박제, evidence path 명시
- belle 명시 결정 (2026-06-09): α (Phase 8.5 신설) 진행, NotebookLM IPSF Code of Points 활용

---

## 9. 직접 확인 가능한 raw data

- 3차 sweep Firestore docs: `users/sweep_phase8_1780986673/analyses/{5 doc ids}` — `result.forceSignalsReport` 필드 직접 조회
- raw distance 산출 코드: `force_signals.py:compute_axis_deviation` 의 `pole_aligned` 분기 (line 1100~1240)
- Pod sweep log: `/workspace/sweep_phase8.log` (RunPod xbdkj1g2ylnfwi)
- Phase 8 종료 commit: `0d2629a` (08-03-SUMMARY) + 직전 in-line fix commits c71c75b (B+C), f627905 (B')
