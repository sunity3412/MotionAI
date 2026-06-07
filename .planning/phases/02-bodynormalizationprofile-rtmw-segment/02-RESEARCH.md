# Phase 2: BodyNormalizationProfile 자동 측정 (RTMW segment 기반) — Research

**Researched:** 2026-06-07
**Domain:** RTMW 133 wholebody keypoint → body segment 측정 + 시간 평균 + jitter 스무딩 + confidence/warnings 집계
**Confidence:** HIGH (Phase 1 RTMW + BodyNormalizationProfile contract 박제 완료, segment 측정만 신설)

---

## Summary

Phase 1 (commit 2a8aa72) 에서 운영 백본은 **RTMW 133 wholebody (Apache-2.0)** 로 swap 완료. `RTMWPoseEngine.estimate(frames, pole_axis) → list[PoseFrame]` 가 작동하고, 각 `PoseFrame.raw_keypoints_133` 에 133개 풀 키포인트가 보존된다 (D-20). `BodyNormalizationProfile` dataclass + TS interface + contract.md §7 은 **3-way lockstep 으로 이미 박제** (Plan 01-19, D-19/D-21). `PoseFrame.body_shape: Optional[BodyNormalizationProfile] = None` 도 nullable 필드로 박제.

**Phase 2 가 신설할 것 = "RTMW 133 → BodyNormalizationProfile" 측정기 본체**. contract 변경은 0 (이미 박제), 측정 알고리즘 + smoothing + warnings 집계 + R&D 비교 harness 만 신설.

**Primary recommendation:** `backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py` 신설. `measure_body_profile(pose_frames: list[PoseFrame]) → BodyNormalizationProfile`. 내부에서 (1) PoleAxis 길이 = normalize 단위, (2) Phase 1 `temporal.py` 패턴 (MAD outlier + weighted moving average) 재사용, (3) per-segment confidence = endpoint conf 의 percentile aggregation, (4) warnings = 5종 enum. R&D 비교군은 `backend/research/evaluations/compare_body_profile.py` 로 NLF→SMPL-X path 별도 격리. RTMW path 통합은 `_RTMWNlfCompat` 가 `body_shape` 도 함께 채우도록 한 줄 추가.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Segment 길이 측정 (raw px) | API/Backend (sunity_shared.analysis) | — | RTMW PoseFrame 위에서만 순수 numpy. 모델/네트워크 무관 (Phase 1 algorithm core 원칙 정합) |
| Normalize unit 산출 (pole axis 길이) | API/Backend (analysis) | — | PoleAxis 이미 PoseFrame 에 박혀있음. 새 의존성 없음 |
| Jitter smoothing | API/Backend (analysis) | — | Phase 1 `temporal.py` MAD 재사용 |
| Confidence 집계 | API/Backend (analysis) | — | RTMW score = `Keypoint3D.confidence` 직접 매핑 (D-22) |
| Warnings 출력 | API/Backend (analysis) | — | 측정기 자체에서 판정 |
| PoseFrame.body_shape 주입 | Runpod Pose Engine 위 (`_RTMWNlfCompat` / pipeline `_process`) | — | 측정기 output → 모든 frame 동일 video-level profile 공유 (D-10 PoleAxis 패턴 정합) |
| R&D 비교 (NLF→SMPL-X β) | R&D 격리 (backend/research/evaluations) | — | 제품 코드 import 금지 (D-23, [[license-blocklist-pose]]) |
| Lambda 런타임 영향 | None | — | 모든 측정은 Pod (RunPod) 단계에서 일어남 — Lambda 는 Firestore 저장만 |

---

## Existing Code Map (Phase 1 산출 — Phase 2 가 위에 얹는 것)

### 박제 완료 (재사용)

| 항목 | 위치 | Phase 2 사용 방식 |
|------|------|-------------------|
| `BodyNormalizationProfile` dataclass | `backend/shared/python/sunity_shared/analysis/body_normalization.py` | 측정기 출력 타입 — 수정 X |
| TS interface | `app/src/types/analysis.ts:373-388` | TS 측 lockstep — 수정 X |
| contract.md §7 | `docs/contract.md:321-368` | 명세 — 수정 X (warnings enum 확장만) |
| `PoseFrame.body_shape: Optional[...]` | `pose_frame.py:241` nullable | RTMW path 가 채울 곳 |
| `PoseFrame.raw_keypoints_133: dict[str, Keypoint3D]` | `pose_frame.py:246` | 측정 input — 133 풀 키포인트 |
| `RTMW_KEYPOINT_INDICES` 표 | `pose_engines/rtmw/wholebody_keypoints.py:117` | segment 인덱싱 lookup |
| `PoleAxis` (video-level, D-10) | `pose_frame.py:167` | normalize 단위 (axis_vector 길이) |
| `temporal.py` MAD outlier + weighted MA | `analysis/temporal.py` | smoothing 재사용 |
| 3-way lockstep 테스트 | `backend/tests/test_body_normalization_lockstep.py` | drift 방어 — 수정 X |
| `BodyNormalizationProfile` validator 테스트 | `backend/tests/test_body_normalization_profile.py` | 신설 측정기가 valid profile 만 출력하는지 검증 추가 |
| `_RTMWNlfCompat` 호환 어댑터 | `backend/functions/pipeline/app.py:202` | Phase 2 에서 `to_coco17_array` 외에 `body_shape` 도 frame 마다 주입하도록 확장 |

### Stub 상태 (Phase 2 가 본체 채움)

| 항목 | 현재 상태 | Phase 2 채울 것 |
|------|-----------|-----------------|
| 측정기 모듈 | **없음** | `body_normalization_measurer.py` 신설 |
| Pipeline 통합 | `_RTMWNlfCompat` 가 `body_shape` 안 채움 (모든 frame `None`) | 측정 후 video-level profile 을 모든 PoseFrame 에 박제 |
| R&D 비교 harness (BodyProfile) | `compare_engines.py` 는 점수 비교 전용 (BodyProfile X) | `compare_body_profile.py` 신설 — NLF→SMPL-X β path 격리 + RTMW segment vs SMPL-X β 갭 보고 |

### 누락 (Phase 2 외 — 의존성 X)

| 항목 | 위치 (예상) | Phase |
|------|-------------|-------|
| 다운스트림 (체형 정규화 비교) | — | Phase 6 |
| 자가입력 BodyProfileInput UX | — | Phase 3 |
| 좌우 비대칭 활용 (좌/우 scale 별도 분리) | — | Phase 7 v1, 본 phase 는 좌우 평균만 |

---

## RTMW 133 Keypoint Segment Mapping (CONTEXT.md Q1 답)

> RTMW body 17 = COCO-17 표준 (인덱스 0~16). 모든 segment 는 **body 17 안에서만** 측정. 손가락/얼굴 (인덱스 17~132) 은 사용 X — 폴스포츠 인버트/사이드 자세에서 얼굴/손가락은 occlusion 가장 잦은 영역. body 17 의 어깨/팔꿈치/손목/엉덩이/무릎/발목 6쌍이 측정 안정성 최적.

### Segment → keypoint pair 표

| Segment | Left endpoints | Right endpoints | 좌우 처리 |
|---------|----------------|-----------------|----------|
| 상완 (upper arm) | `left_shoulder` (5) ↔ `left_elbow` (7) | `right_shoulder` (6) ↔ `right_elbow` (8) | 좌우 평균 = `armScale` 의 입력 |
| 전완 (forearm) | `left_elbow` (7) ↔ `left_wrist` (9) | `right_elbow` (8) ↔ `right_wrist` (10) | 좌우 평균 = `armScale` 의 입력 |
| 대퇴 (thigh) | `left_hip` (11) ↔ `left_knee` (13) | `right_hip` (12) ↔ `right_knee` (14) | 좌우 평균 = `legScale` 의 입력 |
| 하퇴 (shank) | `left_knee` (13) ↔ `left_ankle` (15) | `right_knee` (14) ↔ `right_ankle` (16) | 좌우 평균 = `legScale` 의 입력 |
| 몸통 (torso) | `mid_shoulder` ↔ `mid_hip` (둘 다 좌우 중점) | — | 단일 = `torsoScale` |
| 어깨너비 | `left_shoulder` (5) ↔ `right_shoulder` (6) | — | 단일 = `shoulderHipRatio` 분자 |
| 골반너비 | `left_hip` (11) ↔ `right_hip` (12) | — | 단일 = `shoulderHipRatio` 분모 |

### 인덱스 lookup 코드

```python
# Phase 2 신설: body_normalization_measurer.py 의 상수
SEGMENT_PAIRS: dict[str, tuple[str, str]] = {
    "left_upper_arm":  ("left_shoulder",  "left_elbow"),
    "right_upper_arm": ("right_shoulder", "right_elbow"),
    "left_forearm":    ("left_elbow",     "left_wrist"),
    "right_forearm":   ("right_elbow",    "right_wrist"),
    "left_thigh":      ("left_hip",       "left_knee"),
    "right_thigh":     ("right_hip",      "right_knee"),
    "left_shank":      ("left_knee",      "left_ankle"),
    "right_shank":     ("right_knee",     "right_ankle"),
    "shoulder_width":  ("left_shoulder",  "right_shoulder"),
    "hip_width":       ("left_hip",       "right_hip"),
    # torso 는 mid-shoulder/mid-hip — 별도 처리 (4 keypoint 평균)
}
TORSO_TOP_KPS = ("left_shoulder", "right_shoulder")
TORSO_BOTTOM_KPS = ("left_hip", "right_hip")
```

### 인버트 / 사이드 자세 visibility 고려

폴스포츠 인버트 자세에서 RTMW score 분포 (Phase 1 sweep 2026-06-03 sweep_rtmw_20260603_1409 기준): body 17 score 평균 0.90~0.95, 손가락/발끝 score 0.5~0.8 폭. body 17 만 사용하면 인버트 측정 안정성 충분히 확보. **얼굴/손가락 사용 X 정합**.

[VERIFIED: Phase 1 sweep report `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.json` — rtmw_mean_score 95.37%]

---

## Smoothing 알고리즘 (CONTEXT.md Q2 답)

### 결론: **MAD-based outlier rejection → median-of-frames + 좌우 평균** (Phase 1 `temporal.py` 패턴 재사용)

### 비교 표

| 알고리즘 | 장점 | 단점 | 평가 |
|----------|------|------|------|
| Moving average (단순 mean) | 구현 단순, scipy 의존 X | 이상치 (인버트 occlusion frame 의 점프) 에 weak | ❌ 폴스포츠 occlusion 빈도 높음 |
| Robust median + MAD rejection | 이상치 robust, 폴스포츠 occlusion 친화적 | "robust median" 자체는 noise 에는 약함 (boundary frame 만 보면) | ✅ **선택** |
| Exponential moving average | latency 최적, 실시간 친화적 | bias toward 최신 frame, video-level 분석 불필요 | ❌ 본 phase 는 batch (영상 1개 = profile 1개) |
| Kalman filter | 모션 모델링 정확 | scipy/filterpy 의존 + over-engineering | ❌ over-engineering (`MVP 단순+실증 퀄리티` 정합) |

### 선택 이유

1. **Phase 1 정합** — `temporal.py` 이미 `_column_outliers` (MAD k=3) + `_smooth_column` (weighted MA) 박제. 같은 패턴 재사용 = 새 의존성 0 + 회귀 위험 0.
2. **폴스포츠 occlusion 친화** — 인버트 frame 의 keypoint 점프 (예: hip ↔ knee 가 frame 1 에서 320px → frame 2 에서 50px) 가 MAD outlier 로 잘 잡힘 (Phase 1 검증됨).
3. **scipy 의존 회피** — Lambda Layer 용량 / SAM 빌드 시간 증가 부담. numpy 만으로 가능.

### 알고리즘 sketch

```python
# Phase 2 신설: body_normalization_measurer.py
import numpy as np

def _measure_segment_per_frame(
    pose_frames: list[PoseFrame],
    kp_start: str,
    kp_end: str,
) -> tuple[np.ndarray, np.ndarray]:
    """프레임별 segment 길이 + endpoint confidence (T,) (T,) 반환.

    좌표 = keypoints_3d (raw, NOT pole_aligned — 길이는 회전 불변).
    NaN = 키포인트 미감지 frame.
    confidence = min(start.confidence, end.confidence) — 둘 중 약한 쪽 (보수적).
    """
    T = len(pose_frames)
    lengths = np.full(T, np.nan, dtype=np.float64)
    confidences = np.zeros(T, dtype=np.float64)
    for t, frame in enumerate(pose_frames):
        kps = frame.keypoints_3d
        if kp_start in kps and kp_end in kps:
            a, b = kps[kp_start], kps[kp_end]
            dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z
            lengths[t] = np.sqrt(dx*dx + dy*dy + dz*dz)
            confidences[t] = min(a.confidence, b.confidence)
    return lengths, confidences


def _robust_median(lengths: np.ndarray, confidences: np.ndarray,
                   conf_threshold: float = 0.5,
                   mad_k: float = 3.0) -> tuple[float, float]:
    """confidence 게이트 통과 frame 중 MAD-rejected median + 자체 confidence."""
    valid = (confidences >= conf_threshold) & np.isfinite(lengths)
    if valid.sum() < 5:  # 최소 5 frame
        return float('nan'), 0.0
    samples = lengths[valid]
    med = float(np.median(samples))
    mad = float(np.median(np.abs(samples - med)))
    if mad > 0:
        kept = samples[np.abs(samples - med) <= mad_k * 1.4826 * mad]
    else:
        kept = samples
    final_median = float(np.median(kept))
    # 자체 confidence = (kept frame 비율) × (kept frame mean conf)
    self_conf = (len(kept) / len(lengths)) * float(confidences[valid].mean())
    return final_median, min(1.0, self_conf)
```

[CITED: Phase 1 `backend/shared/python/sunity_shared/analysis/temporal.py:_column_outliers` MAD k=3 패턴 정합]

---

## Length Normalization Unit (CONTEXT.md Q3 답)

### 결론: **Torso self-reference 비율 (mid-shoulder ↔ mid-hip 길이 = 1.0)**

### 비교 표

| Option | 장점 | 단점 | 평가 |
|--------|------|------|------|
| (a) Frame width ratio | 단순 | 카메라 거리/줌 변화에 직접 영향 | ❌ 카메라 invariant 아님 |
| (b) Pole axis length | 폴 길이 = 실제 고정 길이 (~3m) | PoleAxis 는 **단위 벡터** (norm=1.0) 로 저장됨 — 폴 자체 길이는 측정 안 함. PoleDetector 는 방향만 산출 | ❌ 현재 박제 PoleAxis 가 길이 정보 없음. 신설 비용 큼 |
| (c) **Torso self-reference** | 카메라 / 거리 / 줌 invariant, 추가 측정 0 | torso 자체가 평균 가정 (1.0 으로 박제) | ✅ **선택** |
| (d) Shoulder width self-ref | 좌우 명확 | 인버트 자세에서 shoulder occlusion 빈도 ↑ | ❌ |

### 결정 이유

1. **PoleAxis 가 단위 벡터만 박제** — `pose_frame.py:194` `axis_vector` 는 norm ≈ 1.0 강제 검증. 실제 폴 길이 정보가 contract 에 들어와 있지 않음. 폴 길이 측정기 신설 = 별도 Phase 책임 (R&D scope).
2. **카메라 invariant 필수** — Mode 1 (학생 vs 정은지) 비교는 두 영상이 다른 카메라/거리로 찍힘. self-reference 만 scale-invariant.
3. **Phase 6 의존성 정합** — Phase 6 `normalizeStudentPoseToProReference` 가 segment 비율을 사용. 절대 단위 (cm) 가 아닌 **비율** 이 다운스트림이 원하는 형태.

### 정규화 공식

```python
# torso = mid_shoulder ↔ mid_hip (4 keypoint 평균)
torso_length = robust_median_of(
    distance(mid(left_shoulder, right_shoulder), mid(left_hip, right_hip))
)  # 단위: 화소 (frame width 단위)

# segment 비율 = torso 대비
arm_scale = (left_upper_arm + right_upper_arm + left_forearm + right_forearm) / 4 / torso_length
leg_scale = (left_thigh + right_thigh + left_shank + right_shank) / 4 / torso_length
torso_scale = 1.0  # self-reference 정의상 항상 1.0 — 단, 평균 인구 대비 비율 정보 = 다른 trick 필요
shoulder_hip_ratio = shoulder_width / hip_width

# estimatedHeightScale = (arm + leg + torso) heuristic 의 합산 비율
# 평균 인구 대비 절대 스케일은 영상만으로 추정 불가 (BODY-02 자가입력 키와 결합 시점 = Phase 6)
# v1 에서는 estimatedHeightScale = (arm_scale + leg_scale + 1.0) / 3 로 박제 (1.0 around)
```

### v1 의 estimatedHeightScale 의미

영상만으로는 절대 키 측정 불가 (카메라 거리 미상). v1 의 `estimatedHeightScale = 1.0 근처` 는 **체형 비율 균형 지표** — torso 대비 사지 비율의 평균. 절대 키 추정은 Phase 3 (자가입력 BODY-02) + Phase 6 결합 시점.

[ASSUMED] — torso 대비 사지 비율의 평균이 `estimatedHeightScale` 으로 의미 있다는 가정. Phase 6 통합 시 belle 검토 대상.

---

## Confidence + Warnings Spec (CONTEXT.md Q4·Q5 답)

### Per-segment confidence 집계 공식

```
segment_confidence = (frame_kept_ratio × mean_endpoint_confidence)

  frame_kept_ratio = (MAD outlier reject 후 살아남은 frame 수) / (전체 frame 수)
  mean_endpoint_confidence = mean over valid frames of min(start_kp.conf, end_kp.conf)
```

**선택 이유 (Q4 답):** percentile/mean 중 **mean of min(endpoints)** 가 보수적 안전. min 은 "두 endpoint 중 약한 쪽" = 측정 신뢰의 하한. 시간 평균은 단일 frame outlier 에 robust.

### Profile-level confidence

```
profile.confidence = mean over all 11 segments of segment_confidence
```

11 segment = 8 arm/leg + torso + shoulder_width + hip_width. 단순 평균 (median 은 segment 수가 적어 의미 없음).

### 임계값 default (Phase 1 정합)

| 임계값 | 값 | 출처 |
|--------|-----|------|
| `CONF_GATE_PER_FRAME` | 0.5 | Phase 1 `compare_engines.py:AVG_CONFIDENCE_THRESHOLD` 정합 (D-15 ③) |
| `MIN_VALID_FRAMES` | 5 | numpy median 안정성 하한 |
| `MAX_BAD_FRAME_RATIO` | 0.6 | 60% 초과 occlusion 시 warning `insufficient_frames` + confidence=0 |
| `MAD_K` | 3.0 | Phase 1 `temporal.py:DEFAULT_OUTLIER_K` 정합 |
| `LOW_CONFIDENCE_GATE` | 0.4 | profile.confidence < 0.4 → warning `low_keypoint_confidence` |

### Warnings enum (full taxonomy)

```python
# Phase 2 신설: body_normalization_measurer.py
WARNING_CODES = frozenset({
    "low_keypoint_confidence",   # profile.confidence < 0.4
    "occluded_endpoint",         # 특정 segment 의 endpoint 가 60% 이상 frame 에서 conf < 0.5
    "insufficient_frames",       # T < 30 frame (3 sec @ 9fps)
    "asymmetric_landmark_count", # 좌우 segment 측정 frame 수 차이 > 30%
    "pose_too_inverted",         # avg torso vertical alignment 가 60° 초과 기울어짐 (인버트 비중 > 50%)
})
```

`pose_too_inverted` 판정 = 프레임 평균 (`mid_shoulder.y < mid_hip.y`) frame 비율 > 0.5 → RTMW score 분포가 정상 자세 대비 변동 큼 → segment 측정 자체는 가능하나 신뢰도 낮음을 표기. (확정 임계값은 v1 측정 후 belle 검토 — `pose_too_inverted` 만 [ASSUMED])

### Warnings 출력 정책 (D-03 정합)

`docs/contract.md` + CoachCommentHook 원칙: **확률적 표현으로만 출력**. Phase 2 측정기는 `["low_keypoint_confidence", "occluded_endpoint"]` 같은 코드만 출력. 한국어 카피로 풀어주는 책임 = Phase 11 `coach_writer`.

---

## BodyNormalizationProfile Schema (3-way) — 기존 박제 확인

**Phase 2 는 schema 변경 0**. 이미 박제된 contract 그대로 사용. 측정기 출력 = `BodyNormalizationProfile(...)`.

### TS interface (수정 X — `app/src/types/analysis.ts:373-388`)

```ts
export interface BodyNormalizationProfile {
  estimatedHeightScale: number;
  armScale: number;
  legScale: number;
  torsoScale: number;
  shoulderHipRatio: number;
  confidence: number;     // [0.0, 1.0]
  warnings: string[];     // WARNING_CODES enum
}
```

### Python dataclass (수정 X — `analysis/body_normalization.py:30-82`)

```python
@dataclass(frozen=True)
class BodyNormalizationProfile:
    estimated_height_scale: float
    arm_scale: float
    leg_scale: float
    torso_scale: float
    shoulder_hip_ratio: float
    confidence: float
    warnings: list[str] = field(default_factory=list)
```

### contract.md §7 (확장 — warnings enum 문서화만)

현 `docs/contract.md:342` 의 `warnings` 행 설명: `"측정 품질 이슈 (예: 'short_arm_clip', 'occluded_torso'). 기본값 []."` — Phase 2 가 확정한 5개 enum 으로 갱신. 이것 1줄만 변경 (3-way lockstep 필요).

### 단위 표

| 필드 | 단위 | 의미 |
|------|------|------|
| estimatedHeightScale | ratio (≈1.0) | 사지+torso 평균 — torso 대비 사지 비율 균형 |
| armScale | ratio (≈1.0) | (상완+전완) 좌우 평균 ÷ torso 길이 |
| legScale | ratio (≈1.0) | (대퇴+하퇴) 좌우 평균 ÷ torso 길이 |
| torsoScale | 1.0 fixed (v1) | self-reference, 항상 1.0 |
| shoulderHipRatio | ratio | shoulder_width ÷ hip_width |
| confidence | [0.0, 1.0] | profile 전체 신뢰도 (11 segment conf 평균) |
| warnings | enum list | WARNING_CODES 집합 부분집합 |

---

## R&D 비교 Harness (CONTEXT.md Q5 답)

### 결론: `backend/research/evaluations/compare_body_profile.py` 신설 — `compare_engines.py` 패턴 정합

### 격리 경계 (D-23 / D-24 정합)

```
backend/shared/python/sunity_shared/  ← 운영 제품 코드 (Lambda + RunPod import)
    └─ NLF / SMPL-X 절대 import 금지
       (Plan 01-24 미완 작업이 .samignore + import 차단 단위 테스트 신설 예정)

backend/research/  ← R&D 격리 디렉터리
    ├─ evaluations/  ← belle 평가 보고서 산출
    │  └─ compare_body_profile.py  ← Phase 2 신설
    └─ spikes/       ← 일회성 실험
```

### Harness 입출력 형식

```python
# backend/research/evaluations/compare_body_profile.py — Phase 2 신설
"""RTMW segment vs NLF→SMPL-X β BodyNormalizationProfile 갭 보고.

D-23 박제: NLF/SMPL-X 모듈 import 는 본 파일에서만. sunity_shared 무관.
[CITED: license-blocklist-pose memory — SMPL-X 상업 불가 / R&D 만]
실행 환경: belle 사내 RunPod GPU pod (Lambda/RunPod 운영 path X)
"""

# 입력
#   --videos ref-foxtop ref-foxtop-split ref-invert ref-sideway-spin ref-climb
#   --rtmw-keypoints-dir backend/research/evaluations/reports/sweep_rtmw_20260603_1409/keypoints/
#   --output backend/research/evaluations/reports/body_profile_gap_$(date +%Y%m%d).json

# 출력 (report.json)
{
  "timestamp": "...",
  "videos": {
    "ref-foxtop": {
      "rtmw_profile": {  # 운영 path 산출
        "estimated_height_scale": 1.02, "arm_scale": 0.98, ...
      },
      "smplx_profile": {  # R&D path 산출 (NLF→SMPL-X β → segment 비율 변환)
        "estimated_height_scale": 1.04, "arm_scale": 1.01, ...
      },
      "gap": {
        "arm_scale_abs_diff": 0.03,
        "leg_scale_abs_diff": 0.02,
        ...
      }
    }
  },
  "aggregate": {
    "mean_gap_arm_scale": 0.04,
    "mean_gap_leg_scale": 0.03,
    "verdict": "within_5pct_tolerance"  # belle 검토
  }
}
```

### 운영 코드 import 차단 검증

Plan 01-24 신설 예정인 `backend/tests/test_research_import_isolation.py` 가 다음을 검증 (Phase 2 plan 에 같이 박을 수도 있음 — planner 판단):

```python
def test_sunity_shared_does_not_import_research() -> None:
    """sunity_shared 어떤 모듈도 backend/research/ 를 import 금지."""
    # AST 스캔 — backend/shared/python/sunity_shared/**/*.py 에서
    # `from backend.research` 또는 `from research` 또는 `import research` 검출 시 fail
```

---

## Test Fixture Plan (CONTEXT.md Q6 답)

### 결론: **Phase 1 sweep_rtmw_20260603_1409 keypoint dump 재사용 + 인버트/사이드 fixture 1개 추가**

### 재사용

| Fixture | 경로 | 사용 시나리오 |
|---------|------|---------------|
| sweep_rtmw_20260603_1409 (5 영상) | `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/` | RTMW pose_frames 입력 → measurer 출력 검증 (정상 자세) |
| 정은지 hold-frame measurements | `backend/research/evaluations/reports/eunji_reference_measurements/measurements.json` | 정은지 영상의 RTMW 출력 = "정상 인간 BodyProfile" reference. confidence > 0.7 + 0 warnings expected |

> ⚠️ Phase 1 sweep 의 raw keypoint dump 가 실제로 디스크에 있는지 확인 필요. report.json/.md 만 있고 keypoint .npz 가 없으면, planner 가 **첫 task 로 keypoint dump 재생성** plan 을 넣어야 함. (`measure_eunji_reference.py` 의 `_extract_pose_frames` 패턴 참고)

### 신설 fixture 필요한 케이스

| Case | 목적 | 입력 | Expected |
|------|------|------|---------|
| `test_inverted_pose_fixture` | `pose_too_inverted` warning 발화 검증 | mid_shoulder.y < mid_hip.y in 80% frames | warnings contains `pose_too_inverted`, confidence < 0.7 |
| `test_occluded_leg_fixture` | `occluded_endpoint` warning 발화 검증 | left_knee.confidence < 0.3 in 70% frames | warnings contains `occluded_endpoint`, leg_scale 측정 가능하지만 confidence 낮음 |
| `test_short_clip_fixture` | `insufficient_frames` 발화 | T < 30 frames | warnings contains `insufficient_frames`, confidence < 0.3 |
| `test_normal_pose_fixture` | 정상 케이스 — Phase 1 sweep 의 ref-foxtop 같은 정상 hold | 정은지 ref-foxtop 의 hold_window frame 만 추출 | profile valid, confidence > 0.7, warnings == [] |
| `test_asymmetric_landmark_fixture` | `asymmetric_landmark_count` 발화 | 좌측만 70% 가림, 우측만 30% 가림 | warnings contains `asymmetric_landmark_count` |

신설 fixture 는 **synthetic** (`numpy.random.RandomState(seed=42)` + keypoint 생성기) 로 만드는 게 가장 빠름 — 실제 영상 RTMW 출력 재생산보다 4시간 절감. 실 영상 fixture (정은지 ref-foxtop hold) 는 1개만 재사용.

### Fixture 위치

```
backend/tests/fixtures/body_normalization/
    ├─ normal_pose_pose_frames.json    # PoseFrame[] JSON serialized
    ├─ inverted_pose_pose_frames.json
    ├─ occluded_leg_pose_frames.json
    ├─ short_clip_pose_frames.json
    └─ asymmetric_pose_frames.json
```

---

## Pipeline Integration Plan

### 통합 지점

`backend/functions/pipeline/app.py:202` 의 `_RTMWNlfCompat.estimate(frames)` 가 현재 `pose_frames` 를 만든 뒤 즉시 `(T,17,4)` ndarray 로 변환해 버림. body_shape 는 모든 frame `None`.

**Phase 2 변경:**

```python
class _RTMWNlfCompat:
    def estimate(self, frames):
        from sunity_shared.analysis.pose_frame import to_coco17_array
        from sunity_shared.analysis.body_normalization_measurer import measure_body_profile  # NEW

        pose_frames = self._engine.estimate(frames, self._default_pole)

        # NEW: video-level BodyProfile 측정 + 모든 frame 에 박제 (PoleAxis D-10 패턴 정합)
        profile = measure_body_profile(pose_frames)
        pose_frames = [
            dataclasses.replace(pf, body_shape=profile) for pf in pose_frames
        ]
        # (선택) Firestore 에 video-level profile 저장 — Phase 6 가 사용
        # 본 pipeline 에서는 angles 만 사용. body_shape 저장은 별도 task 결정.

        return to_coco17_array(pose_frames)
```

### Firestore 저장 (선택 — planner 결정)

`firestore_admin.complete_analysis(...)` 호출에 `bodyNormalizationProfile` 필드 추가 시:
- TS `AnalysisDoc` lockstep — `app/src/types/analysis.ts` 의 `AnalysisDoc` 에 `bodyNormalizationProfile?: BodyNormalizationProfile` 추가
- Firestore nested-array 제약 정합 — `BodyNormalizationProfile` 은 array 없음 (warnings 가 array 지만 nested 아님) — 안전

v1 scope 에서 Firestore 저장은 **Phase 6 가 필요할 때만** 추가하는 것을 권장 (`MVP 가볍게+실증 퀄리티` 정합).

---

## Risks + Mitigations (Top 3)

### Risk 1: 인버트 자세 confidence collapse

**증상:** Phase 1 sweep `ref-invert-butterfly-combo` 에서 RTMW body 17 keypoint 의 hip ↔ shoulder occlusion 잦음. mid_shoulder/mid_hip 측정 자체 실패.

**확률:** MEDIUM (Phase 1 sweep 에서 RTMW mean score 0.90+ 였지만, frame 별 분포는 인버트 frame 에서 50% 까지 떨어짐)

**Mitigation:**
- v1: `pose_too_inverted` warning 발화 + body_shape.confidence < 0.4 시 다운스트림 (Phase 6) 에서 normalize 적용 안 함 (graceful degrade)
- MAD outlier rejection 으로 인버트 frame 자체를 측정에서 제거 → 영상의 standing/transition frame 만으로 측정. 단, 영상 전체가 인버트면 fail (warnings 표기)
- v2: Phase 4 다중 시점 + Phase 3 자가입력 키와 결합

### Risk 2: 측정 평균값이 좌우 비대칭을 못 잡음

**증상:** 폴스포츠 사용자가 한쪽 다리 부상 회복 중 → 우측 다리 length 측정값이 좌측보다 짧음 (anatomical asymmetry 가 아닌 occlusion 때문). Phase 2 v1 은 좌우 평균 만 출력 → 비대칭 정보 손실.

**확률:** LOW (v1 scope 는 좌우 평균만, 비대칭 활용은 Phase 7 책임)

**Mitigation:**
- CONTEXT.md §1 out-of-scope 정합 — 좌우 비대칭 결정은 Phase 7 책임. v1 은 `asymmetric_landmark_count` warning 만 발화. 측정값 자체는 좌우 평균 출력.
- 내부적으로 좌/우 segment 개별 length 를 측정해서 측정기 디버깅용 보조 dict 로 노출 (v2 에서 활용)

### Risk 3: torso self-reference 가 카메라 perspective 에 영향받음

**증상:** RTMW 가 monocular path → z 좌표가 신뢰 낮음 (Phase 1 박제: RTMW3D path 미선택, monocular only). 카메라 각도가 sagittal/coronal 에 따라 torso 측정값이 변함.

**확률:** MEDIUM-HIGH

**Mitigation:**
- segment length = `sqrt(dx² + dy²)` (2D distance 만) — z 좌표 사용 X 가 Phase 2 default. v1 의 PoseFrame.keypoints_3d 의 z 가 RTMW 2D 결과면 0 — 자동으로 2D 가 됨.
- Phase 4 (다중 시점) 가 카메라 perspective 보정 책임. v1 은 정면 가정.
- 카메라 perspective robust 한 normalize 가 필요하면 v1.5/Phase 6 에서 재논의.

---

## Project Constraints (from CLAUDE.md)

| 제약 | 영향 |
|------|------|
| 라이트 테마 전용 / #FF4B33 / Pretendard | Phase 2 = backend only — UI 영향 없음 |
| 작은 단위 작업 + 의미 있는 테스트 | atomic commit 5~7개 (아래 task 제안 정합) |
| 이모지 금지 / 슬롭 코드 금지 | RESEARCH.md 본문 정합. 측정기 한국어 주석은 OK (Phase 1 패턴) |
| Tech stack 변경 금지 | numpy only — scipy/scikit-learn 추가 X |
| SAM build native deps | numpy already in layer — 신설 의존성 0 |
| Firestore nested array 금지 | `warnings: list[str]` 은 flat — 안전 |
| 사람 점수 라벨링 영구 금지 | 정은지 ref-foxtop 측정값을 "정답 profile" 로 fixture 박제 = OK (객관 측정값, 사람 점수 아님) |
| 분석 정확도 최우선 | confidence/warnings 항상 출력 = 본 phase 정신 정합 |
| Phase 1 RTMW 백본 swap 완료 정합 | `_RTMWNlfCompat` 가 통합 지점 — 한 줄 변경으로 통합 |

---

## Architecture Pattern: Phase 1 정합 정리

### Pattern: Pure Algorithm + Lazy Adapter 경계

Phase 1 의 `temporal.py` / `dimensions.py` / `kismam.py` 와 동일 패턴.

```python
# backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py
# Phase 2 신설 — 순수 함수, numpy only, network/model/AWS 의존 X
# 단위 테스트 가능, Lambda Layer 호환

def measure_body_profile(
    pose_frames: list[PoseFrame],
    *,
    conf_gate: float = 0.5,
    mad_k: float = 3.0,
    min_valid_frames: int = 5,
    low_conf_gate: float = 0.4,
) -> BodyNormalizationProfile:
    """RTMW PoseFrame list → 측정된 BodyNormalizationProfile.

    Phase 1 temporal.py MAD 패턴 정합. scipy 의존 X.
    Phase 2 BODY-01 본체 — D-19 segment 비율 측정.
    """
    # 1. 각 segment 별로 per-frame length + confidence 측정
    # 2. MAD outlier rejection → robust median
    # 3. 좌우 평균 → arm/leg/torso scale
    # 4. shoulder_hip_ratio = shoulder_width / hip_width
    # 5. 각 segment confidence aggregate → profile.confidence
    # 6. warnings enum 판정
    # 7. BodyNormalizationProfile 반환
```

---

## Don't Hand-Roll

| 문제 | 직접 구현 X | 재사용 | 이유 |
|------|-------------|--------|------|
| MAD outlier detection | 새 구현 | `analysis/temporal.py:_column_outliers` 패턴 그대로 복사/추출 | Phase 1 검증된 패턴 |
| numpy stats | scipy.stats | numpy median/std | scipy 의존 회피 (Lambda Layer 용량) |
| keypoint name → RTMW index lookup | hardcode | `RTMW_KEYPOINT_INDICES` dict | 어댑터 박제 정합 |
| Frame → BodyProfile 데이터 흐름 | 새 schema | `PoseFrame.body_shape` nullable 필드 | D-21 박제 정합 |
| 3-way lockstep | manual | `test_body_normalization_lockstep.py` 가 이미 박제 — drift 자동 차단 | Plan 01-19 산출 |
| BodyProfile validator | manual | dataclass `__post_init__` 박제 | confidence ∈ [0,1] + warnings list[str] 자동 검증 |

---

## Common Pitfalls

### Pitfall 1: PoleAxis 가 단위 벡터인 걸 모르고 폴 길이로 normalize 시도

**증상:** PoleAxis.axis_vector 가 (0, 1, 0) 형태 unit vector. 곱하면 항상 1.0. normalize unit 으로 못 씀.
**예방:** torso self-reference 만 사용 — 본 RESEARCH 결정 정합.
**탐지:** unit test 가 `BodyNormalizationProfile.torsoScale == 1.0` 검증.

### Pitfall 2: RTMW 2D path 의 z=0 좌표를 3D 처럼 사용

**증상:** Phase 1 RTMW 운영 path 는 2D wholebody. `Keypoint3D.z = 0` 인 경우 많음. `sqrt(dx²+dy²+dz²)` 면 z=0 안전하지만, 다른 알고리즘에서 z 사용 시 함정.
**예방:** segment length = `sqrt(dx² + dy²)` 만 사용 (본 RESEARCH 의 Risk 3 mitigation). 단위 테스트가 z=0 fixture 로 검증.
**탐지:** `test_z_axis_ignored_when_zero` 단위 테스트.

### Pitfall 3: `dataclasses.replace(frame, body_shape=profile)` 가 frozen field 우회

**증상:** `PoseFrame` 은 `@dataclass(frozen=True)`. 직접 `frame.body_shape = profile` 은 `FrozenInstanceError`.
**예방:** `dataclasses.replace(frame, body_shape=profile)` 표준 패턴 사용.
**탐지:** lint / mypy.

### Pitfall 4: Firestore 에 BodyProfile 저장 시 nested array 함정

**증상:** `warnings: list[str]` 자체는 OK, 하지만 `BodyProfile` 을 `analysisDoc.results.body_normalization_profile.warnings` 처럼 깊이 중첩하면 Firestore 가 거부할 수 있음.
**예방:** v1 에서는 Firestore 저장 안 함 (Pipeline 내 RAM 만 사용). Phase 6 통합 시 평면 저장 (예: `bodyNormalizationProfile.warnings: array<string>`).
**탐지:** Firestore admin save 시점 schema validation.

### Pitfall 5: SMPL-X import 가 운영 path 에 leak

**증상:** R&D harness 가 `from sunity_shared.analysis.body_normalization_measurer import ...` 한 뒤 NLF/SMPL-X 도 추가 import. 누군가 `compare_body_profile.py` 를 `sunity_shared` 안으로 옮기면 운영 path 가 NLF 의존.
**예방:** `backend/research/` 에 격리 + `test_research_import_isolation.py` 자동 차단 (Plan 01-24 정합).
**탐지:** import path AST scan.

---

## Runtime State Inventory (없음 — greenfield 측정기)

Phase 2 는 신설 코드 — 기존 stored data / live service config / OS state / secrets / build artifacts 변경 없음.

| 카테고리 | Items Found |
|----------|-------------|
| Stored data | None — Firestore schema 변경 0 (v1 scope) |
| Live service config | None — RUNPOD env 변경 0 |
| OS state | None |
| Secrets/env vars | None |
| Build artifacts | None — neww py 파일 추가만, Layer cache invalidation 자연 |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `backend/requirements-dev.txt` (config 명시 X — discovery 기본) |
| Quick run command | `cd backend && pytest tests/test_body_normalization_measurer.py -x` |
| Full suite command | `cd backend && pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| BODY-01 | segment 측정 + smoothing | unit | `pytest tests/test_body_normalization_measurer.py::test_normal_pose_profile -x` | ❌ Wave 0 |
| BODY-01 | warnings 발화 | unit | `pytest tests/test_body_normalization_measurer.py::test_inverted_pose_warning -x` | ❌ Wave 0 |
| BODY-01 | contract 3-way | unit | `pytest tests/test_body_normalization_lockstep.py -x` | ✅ 박제됨 |
| BODY-01 | validator 경계 | unit | `pytest tests/test_body_normalization_profile.py -x` | ✅ 박제됨 |
| BODY-01 | Pipeline 통합 | integration | `pytest tests/test_pipeline_body_profile_injection.py -x` | ❌ Wave 0 |
| BODY-01 (R&D) | NLF gap report | manual | belle Pod 에서 `python -m backend.research.evaluations.compare_body_profile` | ❌ R&D scope |

### Sampling Rate
- Per task commit: `pytest tests/test_body_normalization_measurer.py -x` (~2 sec)
- Per wave merge: `pytest tests/ -x` (full backend suite)
- Phase gate: 5 fixture 모두 PASS + contract lockstep PASS + R&D gap < 0.05 (belle 검토)

### Wave 0 Gaps
- [ ] `tests/test_body_normalization_measurer.py` — 5 fixture × 측정 검증
- [ ] `tests/fixtures/body_normalization/` — 5 fixture JSON 생성 스크립트
- [ ] `tests/test_pipeline_body_profile_injection.py` — `_RTMWNlfCompat` 통합 검증
- [ ] (선택) `tests/test_research_import_isolation.py` — Plan 01-24 와 통합 또는 별도

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — Pod 내부 함수 |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes | `BodyNormalizationProfile.__post_init__` 박제 + measurer 인자 validator |
| V6 Cryptography | no | n/a |

### 위협 패턴 + 표준 mitigation

| 패턴 | STRIDE | 표준 mitigation |
|------|--------|------------------|
| 비정상 confidence 값 ([0,1] 범위 외) | Tampering | dataclass validator 박제 (이미 PASS) |
| R&D 코드의 운영 코드 leak (SMPL-X 라이선스 위반) | Repudiation / 법적 | import isolation 테스트 + .samignore (Plan 01-24 정합) |
| 인버트 영상에서 NaN profile 출력 | Denial of Service | `insufficient_frames` warning + confidence=0 폴백, NaN 절대 출력 X (`__post_init__` 통과 위해 finite 강제) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | torso self-reference 가 카메라 invariant 최적 옵션이다 | Length Normalization | Phase 6 통합 시 Mode 1 (다른 카메라 학생 vs 정은지) 비교 정확도 ↓ — belle 검토 시 polish |
| A2 | `estimatedHeightScale = (arm + leg + torso) / 3` 가 의미 있다 | Normalize 공식 | 실제 키 추정 X — Phase 3 자가입력 결합 시점 의미 확정 |
| A3 | `pose_too_inverted` 임계값 = mid_shoulder.y < mid_hip.y in 50% frame | Warnings | 측정 후 실 sweep 데이터로 belle 검토 |
| A4 | RTMW 2D 운영 path 의 z=0 좌표가 segment 측정에 무해 | Common Pitfall 2 | z=0 fixture 단위 테스트로 검증. 만약 RTMW3D path 가 활성화되면 z 사용 재논의 |
| A5 | numpy median 안정 하한 = 5 frame | Confidence Spec | numpy 표준 권장값. fixture 검증으로 확정 |
| A6 | Phase 1 sweep keypoint dump 가 디스크에 있다 | Test Fixture | 만약 report.json/.md 만 있고 npz/keypoint 가 없으면 Phase 2 첫 task = fixture 생성 |
| A7 | `_RTMWNlfCompat` 한 줄 변경으로 통합 가능 (Firestore 저장 X) | Pipeline Integration | Phase 6 시점 Firestore 저장 필요할 수 있음 — 그때 별 plan |

---

## Open Questions (researcher 가 해소 못 한 것)

1. **Phase 1 sweep keypoint dump 실재 여부**
   - 알려진 것: `report.json` / `report.md` 있음
   - 불확실: raw keypoint dump (.npz / .json) 가 디스크에 있는지 미확인
   - 권장: planner 가 첫 task 로 `ls backend/research/evaluations/reports/sweep_rtmw_*` keypoint 파일 확인 → 없으면 Pod 에서 재추출

2. **estimatedHeightScale 의 v1 의미**
   - 알려진 것: 영상만으로 절대 키 측정 불가
   - 불확실: v1 의 값이 다운스트림에서 실제로 유의미하게 쓰이는지 (Phase 6 미구현)
   - 권장: Phase 6 시작 시 belle 검토. 본 phase 는 placeholder `(arm+leg+torso)/3` 으로 박제

3. **Firestore 저장 여부**
   - 알려진 것: contract.md §7 가 BodyProfile 명세 박제, AnalysisDoc 에는 아직 안 박혀있음
   - 불확실: v1 에 Firestore 저장이 필요한가? Phase 6 에서 어떻게 읽나?
   - 권장: v1 = 저장 X (RAM only). Phase 6 통합 시 추가.

4. **Plan 01-24 (.samignore + import 차단) 와 통합 시점**
   - 알려진 것: Plan 01-24 는 후속 별도 plan (ROADMAP Phase 1 close-out 정합)
   - 불확실: Phase 2 의 `compare_body_profile.py` 신설 시점에 import isolation 도 같이 추가? 별도?
   - 권장: planner 가 결정. 본 RESEARCH 는 Phase 2 task 에서 import isolation 테스트 1개만 신설 (Plan 01-24 가 본격 .samignore 처리)

---

## Plan Task Suggestions (5~7 tasks, atomic commit 정합)

> 모든 task = atomic commit. 의존 순서대로 정렬. 각 task = 1 PR 가능 단위.

### Task 1: contract.md §7 warnings enum 박제 (3-way lockstep)

**Goal:** `docs/contract.md:342` warnings 행에 5개 enum 정확히 박제 (`low_keypoint_confidence`, `occluded_endpoint`, `insufficient_frames`, `asymmetric_landmark_count`, `pose_too_inverted`).
**Input:** 현 docs/contract.md §7
**Output:** docs/contract.md 갱신 + `app/src/types/analysis.ts` BodyNormalizationProfile.warnings 주석 갱신 + `analysis/body_normalization.py` warnings docstring 갱신
**File path:** 3개 동시 변경 — atomic commit
**Test:** `test_body_normalization_lockstep.py` 가 이미 박제 — PASS 자동
**Success gate:** lockstep test green + grep 으로 5 enum 모두 3 파일에 등장

### Task 2: Test fixture JSON 5개 + helper 생성

**Goal:** `backend/tests/fixtures/body_normalization/` 디렉터리 + 5 fixture (normal/inverted/occluded/short/asymmetric) JSON 생성기 박제.
**Input:** numpy.random.RandomState(seed=42) — synthetic PoseFrame[] 생성
**Output:** `tests/fixtures/body_normalization/*.json` 5개 + `tests/fixtures/body_normalization/_generate.py` 생성기
**File path:** `backend/tests/fixtures/body_normalization/`
**Test:** `pytest tests/fixtures/body_normalization/test_fixtures_valid.py` — fixture JSON 이 `PoseFrame.from_dict()` 통과
**Success gate:** 5 fixture JSON 존재 + `_generate.py` 가 멱등 (seed 42 → 동일 출력)

### Task 3: body_normalization_measurer.py 본체 + 단위 테스트

**Goal:** `measure_body_profile(pose_frames) → BodyNormalizationProfile` 본체. SEGMENT_PAIRS 정의 + per-frame length 추출 + MAD outlier + robust median + 좌우 평균 + warnings 판정.
**Input:** `list[PoseFrame]`
**Output:** `BodyNormalizationProfile`
**File path:** `backend/shared/python/sunity_shared/analysis/body_normalization_measurer.py`
**Test:** `backend/tests/test_body_normalization_measurer.py` — 5 fixture × expected profile 검증
**Success gate:** 5 fixture 모두 PASS + confidence/warnings 정확

### Task 4: Pipeline 통합 — `_RTMWNlfCompat` 에 body_shape 주입

**Goal:** `backend/functions/pipeline/app.py:202` `_RTMWNlfCompat.estimate()` 가 `measure_body_profile` 호출 + `dataclasses.replace(frame, body_shape=profile)` 으로 모든 PoseFrame 에 video-level profile 박제.
**Input:** RTMWPoseEngine.estimate() 출력 `list[PoseFrame]`
**Output:** `list[PoseFrame]` (body_shape 채워진 상태) + 기존 `to_coco17_array` flow 유지
**File path:** `backend/functions/pipeline/app.py` (1 함수 수정)
**Test:** `backend/tests/test_pipeline_body_profile_injection.py` — fixture frames 입력 → 모든 frame 의 body_shape == 동일 profile
**Success gate:** 통합 테스트 PASS + 기존 pipeline 테스트 회귀 0

### Task 5: R&D 비교 harness `compare_body_profile.py` 신설

**Goal:** `backend/research/evaluations/compare_body_profile.py` — RTMW segment vs NLF→SMPL-X β path 갭 보고. belle Pod 에서 수동 실행.
**Input:** `--rtmw-keypoints-dir` (Phase 1 sweep dump) + `--nlf-keypoints-dir` (R&D path) + `--out report.json`
**Output:** JSON + Markdown 보고서. `compare_engines.py` 패턴 정합.
**File path:** `backend/research/evaluations/compare_body_profile.py`
**Test:** `backend/tests/test_compare_body_profile_smoke.py` — CLI argparse + 빈 입력 graceful fail 검증 (NLF/SMPL-X 실제 호출 X — 모킹)
**Success gate:** smoke test PASS + belle Pod 실행 시 5 영상 갭 보고서 생성

### Task 6: Import isolation 단위 테스트 (Plan 01-24 정합)

**Goal:** `backend/tests/test_research_import_isolation.py` — AST 스캔으로 `sunity_shared/**/*.py` 가 `backend.research` 또는 `from research` import 시 fail.
**Input:** AST 스캔
**Output:** 테스트 1개
**File path:** `backend/tests/test_research_import_isolation.py`
**Test:** self — 통과해야 함
**Success gate:** sunity_shared 가 research import 0 검증

### Task 7 (옵션, planner 결정): Firestore 저장

**Goal:** `firestore_admin.complete_analysis(...)` 시 `bodyNormalizationProfile` 저장. TS `AnalysisDoc` lockstep 갱신.
**Input:** 측정된 profile
**Output:** Firestore doc 에 새 필드 + TS `AnalysisDoc.bodyNormalizationProfile?` 추가
**File path:** `firestore_admin.py` + `app/src/types/analysis.ts`
**Test:** `test_firestore_admin_body_profile_save.py` (모킹)
**Success gate:** 저장 + lockstep PASS

> ⚠️ Task 7 은 v1 scope 에서 보류 권장 — Phase 6 통합 시 추가하는 게 정합. CONTEXT.md "v1 scope = 측정기 본체" 정신 정합.

### Task 의존 순서

```
Task 1 (contract enum)  ─┐
                         ├─→ Task 3 (measurer) ─→ Task 4 (pipeline integ) ─→ [Phase 끝]
Task 2 (fixtures)  ──────┘                  └─→ Task 5 (R&D harness)
                                            └─→ Task 6 (import isolation)
                                                    └─→ (Task 7 옵션)
```

---

## Sources

### Primary (HIGH confidence — 박제 코드 직접 인용)
- `backend/shared/python/sunity_shared/analysis/body_normalization.py` (BodyNormalizationProfile dataclass)
- `backend/shared/python/sunity_shared/analysis/pose_frame.py` (PoseFrame.body_shape nullable)
- `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/wholebody_keypoints.py` (RTMW 133 인덱스)
- `backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py` (변환 패턴)
- `backend/shared/python/sunity_shared/analysis/temporal.py` (MAD outlier 패턴 — 재사용)
- `backend/functions/pipeline/app.py:202` (`_RTMWNlfCompat` 통합 지점)
- `app/src/types/analysis.ts:373-422` (TS interface lockstep)
- `docs/contract.md:321-368` (§7 BodyNormalizationProfile 명세)
- `backend/tests/test_body_normalization_lockstep.py` (3-way lockstep 박제)
- `backend/tests/test_body_normalization_profile.py` (validator 박제)
- `backend/research/spikes/measure_eunji_reference.py` (Phase 1 측정 패턴 참조)
- `backend/research/evaluations/compare_engines.py` (R&D harness 패턴)
- `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.json` (RTMW score 분포 verification)

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md` Phase 1 + Phase 2 정의
- `.planning/REQUIREMENTS.md` BODY-01
- Phase 1 plan 01-19 ~ 01-25 SUMMARY (commit log 정합 — 직접 읽지 않음)

### Tertiary (LOW — assumption)
- `pose_too_inverted` 임계값 50% — 실 sweep 후 belle 검토 필요
- `estimatedHeightScale` v1 의미 — Phase 6 통합 시 확정

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Phase 1 RTMW 박제 완료, 신설 의존성 0
- Architecture: HIGH — Phase 1 알고리즘 코어 패턴 (`temporal.py`) 재사용
- Segment mapping: HIGH — RTMW 표준 인덱스 박제
- Smoothing 알고리즘: HIGH — Phase 1 MAD 패턴 검증됨
- Normalize unit (torso self-ref): MEDIUM — 카메라 invariant 가정 (A1 — Phase 6 검증)
- Warnings enum: MEDIUM — 5종 정의 + 임계값 일부 [ASSUMED] (A3)
- R&D 격리: HIGH — Plan 01-24 정합 + 별도 디렉터리
- Test fixture: MEDIUM — Phase 1 dump 재사용 가정 (A6)
- Pitfalls: HIGH — Phase 1 검증된 함정 + Firestore nested array

**Research date:** 2026-06-07
**Valid until:** 2026-06-22 (15일 — Phase 1 안정 박제 정합)
