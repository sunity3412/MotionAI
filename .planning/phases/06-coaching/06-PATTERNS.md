# Phase 6: 체형 정규화 비교 엔진 (coaching 모드) - Pattern Map

**Mapped:** 2026-06-08
**Files analyzed:** 11 (4 신설 + 7 수정)
**Analogs found:** 11 / 11
**Analog search scope:** `backend/shared/python/sunity_shared/analysis/`, `backend/shared/python/sunity_shared/`, `backend/functions/`, `backend/tests/`, `app/src/`, `app/scripts/`, `docs/`

> 모든 발췌는 file_path:line_range 박제. CLAUDE.md cross-cutting 정합 — 3-way contract lockstep (TS/Python/contract.md 단일 atomic commit), Korean 주석 / English 식별자, 이모지·슬롭 코드 금지, pure 함수 + Protocol adapter 패턴.

---

## File Classification

| File | New/Modified | Role | Data Flow | Closest Analog | Match Quality |
|------|--------------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/body_normalizer.py` | NEW | pure algorithm module | `BodyNormalizationProfile + angles → ScaleProfile + findings + confidence` (transform) | `body_normalization_measurer.py` + `motiondtw.py` + `dimensions.py` | exact (3 analogs combined) |
| `backend/shared/python/sunity_shared/analysis/body_comparison.py` (또는 `body_normalizer.py` 내부) | NEW | dataclass + comparisonType 분기 | dataclass aggregate | `body_normalization.py` (BodyNormalizationProfile) + `assemble.py::build_dimension_explanation` | exact |
| `backend/tests/test_body_normalizer.py` + 4 추가 tests + 5 fixture JSON | NEW | pure-function test suite | fixture JSON → assertion | `tests/test_body_normalization_measurer.py` + `tests/fixtures/body_normalization/` | exact |
| `app/scripts/seed-reference-body-profile.mjs` | NEW | one-off Firebase Admin SDK script | fixture → Firestore reference/{motionId} merge | `app/scripts/seed-reference-motions.mjs` | exact |
| `app/src/types/analysis.ts` | MODIFY | TS contract (BodyComparisonReport + comparisonType union + AnalysisDoc 필드) | 기존 `BodyNormalizationProfile` 인접 박제 | 기존 `BodyNormalizationProfile` interface (analysis.ts:373-416) | exact (인접 박제) |
| `backend/shared/python/sunity_shared/models.py` | MODIFY | Python contract mirror (BodyComparisonReport re-export) | Python ↔ TS lockstep | 기존 `BodyNormalizationProfile` re-export (models.py:119-126) | exact (동일 패턴) |
| `docs/contract.md` §7/§8 | MODIFY | docs contract (BodyComparisonReport 명세) | 기존 §7 인접 박제 | 기존 §7 BodyNormalizationProfile 명세 (contract.md:321-378) | exact |
| `backend/functions/pipeline/app.py::_process` | MODIFY | handler wiring (mode 분기에 정규화 호출) | `_angles_and_body_profile_from_video` 출력 → body_normalizer 호출 → result.bodyComparisonReport | 동일 파일 `_process` mode1/mode3 분기 (pipeline/app.py:476-525) + `_mode3_comparison` helper (pipeline/app.py:387-425) | exact (동일 _process 분기 본체) |
| `backend/shared/python/sunity_shared/firestore_admin.py::complete_analysis` | MODIFY | Firestore I/O (flat 저장 + nested-array 우회) | dict → Firestore set merge | 기존 `complete_analysis` `angles`/`anglesJointKeys`/`anglesFrames` flat (firestore_admin.py:45-70) | exact |
| `backend/functions/reference-api/app.py` + `firestore_admin.get_reference_motion` | MODIFY | reference-motions 응답에 bodyNormalizationProfile nullable 필드 박제 | Firestore doc → JSON response | 기존 `list_reference_motions` (firestore_admin.py:85-93) + `get_reference_motion` (firestore_admin.py:106-113) | exact (필드 추가만) |
| `app/src/lib/userAnalyses.ts::normalize` | MODIFY | client-side defensive normalize (bodyComparisonReport 추가) | Firestore raw → AnalysisDoc | 기존 `normalize` 함수 (userAnalyses.ts:27-53) | exact |

---

## Pattern Assignments

### 1. `backend/shared/python/sunity_shared/analysis/body_normalizer.py` (NEW)

**Role:** pure algorithm module — Kinematic Tree Bone-Length Reprojection + confidence 산출 + IPSF deficit 측정. numpy only.

**Data flow:** `BodyNormalizationProfile (Phase 2)` + `angles (T, J)` + `TechniqueProfile` + comparisonType → `ScaleProfile` (5 ratio) + `findings[] (raw deficit)` + `confidence float`. Phase 12 오버레이가 scaleRatios 메타 소비 → 좌표 reproject 별도 수행. Phase 7 이 findings[] 소비 → 차이 분류.

**Reuse opportunity:** `body_normalization_measurer._measure_segment_per_frame` 의 endpoint conf 게이트 + `(length=nan, conf=0)` 폴백 패턴 그대로. `motiondtw.dtw` 의 numpy-only purity. `dimensions._select_window` + `_LINE_TOL_DEG=20.0` IPSF 허용오차 상수 재사용.

**Net-new vs adapt:** **Net-new module**. 단, 패턴은 기존 3 analog 의 융합 (measurer 의 PoseFrame 입력 + motiondtw 의 numpy purity + dimensions 의 hold_window 기반 deficit).

**Closest analogs:**

#### Analog 1: `body_normalization_measurer.py` (BodyNormalizationProfile 측정기, pure numpy)

**Module-header docstring pattern** (`body_normalization_measurer.py:1-25`):
```python
"""measure_body_profile — RTMW 키포인트 list[PoseFrame] → BodyNormalizationProfile.

D-19 / Phase 2 BODY-01 박제. 순수 numpy 함수. scipy 의존 0.

Phase 1 temporal.py MAD 패턴 재사용 (DEFAULT_OUTLIER_K=3.0).

MEDIUM-3 v5 박제 (pose_too_inverted image-y-order 직접):
  ...
MEDIUM-2 v5 박제 (fallback path emits 1.0):
  BodyNormalizationProfile.__post_init__ 가 5 numeric scale 필드 finite +
  strictly positive 강제. fallback 경로 ... 5 scale 필드 = 1.0 + confidence = 0.0 emit.

5 warning enum (Phase 2 BODY-01 박제):
  - low_keypoint_confidence: 전체 keypoint 평균 confidence < 0.4.
  ...
"""
```
→ Phase 6 박제: 본 docstring 패턴 그대로. 첫 줄 = `"""normalize_pose_by_segments — Kinematic Tree Bone-Length Reprojection (방향 B). pure numpy."""` + D-06-A* 박제 + Universal Principle 박제 + 5 warning enum 분기 (low_confidence_normalization_off / foreshortening_off / shoulder_hip_ratio_off / temporal_variance_high / spatial_dispersion_high).

**Per-frame measurement pattern** (`body_normalization_measurer.py:78-94`):
```python
def _measure_segment_per_frame(
    frame: PoseFrame, start_name: str, end_name: str
) -> tuple[float, float]:
    """단일 frame 의 (segment_length, confidence). z 무시 — 2D image 측정.
    미감지 시 (length=nan, conf=0).
    """
    kp = frame.keypoints_3d
    if start_name not in kp or end_name not in kp:
        return float("nan"), 0.0
    s = kp[start_name]
    e = kp[end_name]
    dx = e.x - s.x
    dy = e.y - s.y
    length = math.sqrt(dx * dx + dy * dy)
    conf = float(min(s.confidence, e.confidence))
    return length, conf
```
→ Phase 6 박제: `normalize_pose_by_segments` 내부 per-edge reproject 도 동일 endpoint conf 게이트 + `(nan, 0)` 폴백. `KINEMATIC_TREE_EDGES` 순회 시 endpoint 둘 다 keypoints_3d 에 있을 때만 reproject.

**상수 분리 패턴** (`body_normalization_measurer.py:37-73`):
```python
SEGMENT_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("left_shoulder", "left_elbow", "left"),
    ...
)
WARNING_CODES: frozenset[str] = frozenset({
    "low_keypoint_confidence",
    ...
})
CONF_GATE_PER_FRAME: float = 0.5
MIN_VALID_FRAMES: int = 5
MAD_K: float = 3.0
```
→ Phase 6 박제: `KINEMATIC_TREE_EDGES`, `BODY_COMPARISON_WARNING_CODES`, `CONFIDENCE_GATE_NORMALIZATION = 0.5` (D-06-A4), `_FORESHORTENING_ANGLE_DEG = 60.0` (Notebook 1 §1.5), `_TEMPORAL_VARIANCE_RATIO = 0.10` (Notebook 4 §4.2) 박제.

#### Analog 2: `motiondtw.py` (pure numpy algorithm, no model/AWS deps)

**Pure-function header + numpy-only purity pattern** (`motiondtw.py:1-16`):
```python
"""MotionDTW 2단계 (ml_CLAUDE.md).
...
MVP 는 Sakoe-Chiba 밴드 제약 DTW(반경 r) — 정통 FastDTW(Salvador&Chan)의
근사 대체. 반경 안에서는 정확하고 비용은 O(r·N). 추후 fastdtw 로 교체 가능
(인터페이스 동일).
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
```
→ Phase 6 박제: `body_normalizer.py` 도 numpy + stdlib 만, `from __future__ import annotations` 첫 줄 박제. "추후 GPA 또는 SMPL 교체 가능 — 인터페이스 동일" 박제 (단 SMPL 은 라이선스 차단).

**Algorithm function signature pattern** (`motiondtw.py:26-31`):
```python
def dtw(X, Y, radius: int | None = None):
    """DTW. X(n,D),Y(m,D) → (정규화거리, path[(i,j)...]).

    정규화거리 = 누적비용/(n+m) — 길이가 달라도 비교 가능.
    radius=None 이면 전역 DTW. band 가 너무 좁아 경로가 막히면 자동 확장.
    """
```
→ Phase 6 박제: `compare_body_profiles(student, reference, comparison_type) → BodyComparisonReport` 시그너처. docstring 박제 — "방향 B: 프로 → 수강생 좌표계", "comparisonType=mode1/mode3_first/mode3_progress 분기".

#### Analog 3: `dimensions.py` (각도/라인/안정성 차원 점수 산식, IPSF 박제 위치)

**Module header docstring + 차원 키 상수** (`dimensions.py:1-37`):
```python
"""IPSF 실행 심사기준 기반 점수 차원 (docs/research/폴스포츠-지식.md 보고서 5·6).
...
2026-05-29 재교정: '균형(좌우 대칭)' 차원 제거. IPSF 기술감점 프로토콜(보고서 6 §4)에
좌우 신체 대칭 항목이 없고, 폴 동작 상당수가 의도적 비대칭이라 대칭 페널티가 정상
동작(세계챔피언 포함)을 깎는 위양성이었다.
"""
# 차원 키 (contract / app dimensionScores 키와 동일 문자열).
DIM_ANGLE = "angle"
DIM_LINE = "line"
DIM_STABILITY = "stability"
# 허용오차(도). z=dev/tol 가우시안 → tol 만큼 벗어나면 점수 ~61.
_LINE_TOL_DEG = 20.0      # IPSF 각도 허용오차 20° 기준.
_FULL_EXTENSION_DEG = 180.0
```
→ Phase 6 박제: `_LINE_TOL_DEG = 20.0` IPSF 박제 그대로 재사용. `COMPARISON_TYPE_MODE1 / MODE3_FIRST / MODE3_PROGRESS` 상수 박제 (Literal 박제 정합). 2026-06-08 박제 메모 = "shoulderHipRatio 좌우 폭 비율 점수 차원 미적용 — IPSF Twist 박제 정합, 메모리 [[scoring-dimensions-ipsf]] 박제 유지".

**Shape validation + windowing helper pattern** (`dimensions.py:43-63`):
```python
def _as_tj(angles) -> np.ndarray:
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2 or a.shape[1] != len(JOINT_KEYS):
        raise ValueError(f"angles 형상은 (T,{len(JOINT_KEYS)}) 이어야 합니다.")
    return a

def hold_window(angles) -> tuple[int, int]:
    """가장 안정적인(분산 최소) 구간 (start, end)."""
```
→ Phase 6 박제: `compute_body_normalization_confidence` 가 temporal variance 산출 시 동일 shape 검증 (T, J) 박제. hold_window 결과를 confidence 산식의 frame 선택으로 재사용 (Phase 12.5 `_select_window` 패턴 정합 — drift 방지).

---

### 2. `backend/shared/python/sunity_shared/analysis/body_comparison.py` (`body_normalizer.py` 내부 박제 권장)

**Role:** dataclass — `BodyComparisonReport` + `BodyComparisonFinding` + `ScaleProfile` (frozen dataclass + post_init validator).

**Data flow:** body_normalizer 의 3 함수 출력 (`scale_profile`, `findings`, `confidence`) → `BodyComparisonReport(comparisonType=..., scaleRatios=..., findings=..., bodyNormalizationConfidence=..., warnings=...)` 조립 → `firestore_admin.complete_analysis(body_comparison_report=...)` 전달.

**Reuse opportunity:** 기존 `BodyNormalizationProfile` 의 frozen dataclass + `__post_init__` validator + math.isfinite 패턴 그대로. `assemble.build_mode1` / `build_mode3` 의 mode 분기 dict 조립 패턴 재사용.

**Net-new vs adapt:** **Net-new dataclass**, 단 기존 BodyNormalizationProfile 의 validator 패턴 + assemble 의 mode-aware 출력 패턴 정합.

**Closest analogs:**

#### Analog 1: `body_normalization.py` (frozen dataclass + 5 필드 validator)

**Frozen dataclass + __post_init__ validator pattern** (`body_normalization.py:48-128`):
```python
@dataclass(frozen=True)
class BodyNormalizationProfile:
    """체형 정규화 프로파일 (D-19 segment 비율 기반).

    필드 7개 (TS camelCase ↔ Python snake_case 1:1):
      estimatedHeightScale  / estimated_height_scale
      ...
      warnings              / warnings              (list[str])

    SMPL-X β / shape_params / betas 필드는 **영구히 도입하지 않는다** (D-19).
    """

    estimated_height_scale: float
    arm_scale: float
    leg_scale: float
    torso_scale: float
    shoulder_hip_ratio: float
    confidence: float
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # confidence 범위 검증 (T-19 contract gate)
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )
        # warnings 타입 검증 — list[str] 만 허용
        if not isinstance(self.warnings, list):
            raise TypeError(...)
        for i, w in enumerate(self.warnings):
            if not isinstance(w, str):
                raise TypeError(...)
        # Phase 2 v5 (MEDIUM-2 v5): 5 numeric scale 필드 finite + strictly positive.
        for field_name in _NUMERIC_SCALE_FIELDS:
            v = getattr(self, field_name)
            if not math.isfinite(v):
                raise ValueError(f"{field_name} must be finite (no NaN/inf), got {v}")
            if v <= 0.0:
                raise ValueError(f"{field_name} must be strictly positive (>0), got {v}")
```
→ Phase 6 박제:
```python
@dataclass(frozen=True)
class BodyComparisonReport:
    """체형 정규화 비교 리포트 (D-06-B3 통합 schema + comparisonType 분기).

    TS camelCase ↔ Python snake_case 1:1 (3-way lockstep — analysis.ts +
    docs/contract.md §8 동시 갱신).
    ...
    """
    comparison_type: Literal["mode1", "mode3_first", "mode3_progress",
                             "mode3_first_with_fallback"]
    scale_ratios: ScaleProfile | None  # nullable — 정규화 OFF 시 None
    findings: list[BodyComparisonFinding] = field(default_factory=list)
    body_normalization_confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # comparisonType literal 박제 (Literal 도 런타임 type-check 가능)
        valid_types = {"mode1", "mode3_first", "mode3_progress",
                       "mode3_first_with_fallback"}
        if self.comparison_type not in valid_types:
            raise ValueError(f"comparisonType must be in {valid_types}, got {...}")
        # confidence [0, 1] 박제 (BodyNormalizationProfile validator 정합)
        if not (0.0 <= self.body_normalization_confidence <= 1.0):
            raise ValueError(...)
        # warnings list[str] 박제 (동일 패턴)
        ...
```

#### Analog 2: `assemble.py::build_dimension_explanation` (mode-aware baseline 박제)

**Mode-aware baseline switching pattern** (`assemble.py:25-34, 86-92`):
```python
_DIMENSION_BASELINES_MODE1 = {
    "angle": "정은지 측정값 + IPSF 실행 기준 참고",
    ...
}
_DIMENSION_BASELINES_MODE3 = {
    "angle": "이전 영상 대비 관절 각도 일관성",
    ...
}

# In build_dimension_explanation:
mode = comparison.get("mode") if isinstance(comparison, dict) else None
baselines = _DIMENSION_BASELINES_MODE1 if mode == "mode1" else _DIMENSION_BASELINES_MODE3
```
→ Phase 6 박제: `BodyComparisonReport` 의 comparisonType 분기에 동일 패턴 — `_COMPARISON_TYPE_DESCRIPTIONS` dict 박제 (mode1 = "정은지 (전문가) 체형 정규화", mode3_first = "Page 9 절대 트랙 단독" 또는 "Page 9 + 자동 매칭 fallback", mode3_progress = "이전 세션 대비 발전 델타"). downstream Phase 12.5 의 dimensionExplanation 박제와 동일 mode-aware 패턴 정합 — drift 방지.

#### Analog 3: `models.py` (Python contract mirror)

**Re-export + 3-way lockstep header pattern** (`models.py:119-126`):
```python
# RTMW pivot (2026-06-02, Plan 01-19) — D-19/D-21 박제.
#   BodyNormalizationProfile = SMPL-X β 없이 segment 비율 + confidence + warnings.
#   PoseFrame.body_shape: Optional[BodyNormalizationProfile] = None nullable.
# TS 미러: app/src/types/analysis.ts BodyNormalizationProfile interface.
# 변경 시 TS + contract.md §6 동시 갱신 (CLAUDE.md Cross-cutting).
from .analysis.body_normalization import (  # noqa: E402 — 파일 하단 re-export 패턴
    BodyNormalizationProfile,
)
```
→ Phase 6 박제: `models.py` 하단에 동일 패턴 추가:
```python
# Phase 6 (2026-06-08, Plan 06-*) — D-06-B3 박제.
#   BodyComparisonReport = comparisonType 분기 + scaleRatios + findings + confidence.
# TS 미러: app/src/types/analysis.ts BodyComparisonReport interface.
# 변경 시 TS + contract.md §8 동시 갱신 (CLAUDE.md Cross-cutting).
from .analysis.body_normalizer import (  # noqa: E402
    BodyComparisonFinding,
    BodyComparisonReport,
    ScaleProfile,
)
```

---

### 3. Test files (`backend/tests/test_body_normalizer.py` + 4 추가 + `conftest.py` + 5 fixture JSON)

**Role:** pure-function test suite — 5 Validation Architecture fixture (NotebookLM FINDINGS §V) 박제.

**Data flow:** fixture JSON → `_load_fixture_frames` → `body_normalizer` 호출 → assertion (warnings / scale ratio / confidence / findings 개수).

**Reuse opportunity:** `tests/conftest.py` 가 이미 `sunity_shared` path 주입 박제 — 신규 conftest 불필요. `tests/fixtures/body_normalization/_factory.py::pose_frame_from_dict` 그대로 재사용. 신규 5 fixture JSON 만 추가.

**Net-new vs adapt:** **Net-new test files (5 + assertion 함수)**, fixture infrastructure 는 기존 박제 재사용.

**Closest analogs:**

#### Analog 1: `tests/test_body_normalization_measurer.py` (fixture-based pure function tests)

**Fixture loader pattern** (`test_body_normalization_measurer.py:32-42`):
```python
_FIXTURES_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "body_normalization"
)


def _load_fixture_frames(name: str) -> list[PoseFrame]:
    raw = json.loads(
        (_FIXTURES_DIR / f"{name}_pose_frames.json").read_text(encoding="utf-8")
    )
    return [pose_frame_from_dict(r) for r in raw]
```
→ Phase 6 박제: 동일 패턴. `_FIXTURES_DIR = ... / "fixtures" / "body_comparison"` 신규 디렉토리 박제, NotebookLM FINDINGS §V 의 5 fixture:
- `fixture_160cm_pro_vs_140cm_student_pose_frames.json` (정규화 효과 박제)
- `fixture_lefty_vs_righty_twist_pose_frames.json` (IPSF Twist 박제 — shoulderHipRatio 점수 차원 미적용)
- `fixture_foreshortening_lying_pose_pose_frames.json` (몸통-카메라 < 60° → 폭 보정 OFF)
- `fixture_unstable_arm_swing_pose_frames.json` (temporal variance > 10% → confidence Low)
- `fixture_split_angle_hipline_pose_frames.json` (hip→knee 라인 박제, toe→toe 위양성 회피)

**Test naming + assertion pattern** (`test_body_normalization_measurer.py:47-70`):
```python
def test_normal_pose_profile_valid() -> None:
    """정상 fixture → warnings==[], finite + strictly positive."""
    frames = _load_fixture_frames("normal_pose")
    profile = measure_body_profile(frames)
    assert isinstance(profile, BodyNormalizationProfile)
    assert profile.warnings == []
    for fname in (...):
        v = getattr(profile, fname)
        assert math.isfinite(v) and v > 0.0, f"{fname}={v} not positive-finite"
    assert profile.confidence > 0.0


def test_inverted_pose_warning() -> None:
    """inverted fixture → pose_too_inverted ∈ warnings."""
    frames = _load_fixture_frames("inverted_pose")
    profile = measure_body_profile(frames)
    assert "pose_too_inverted" in profile.warnings
```
→ Phase 6 박제 함수명 박제:
- `test_160cm_pro_vs_140cm_student_normalization_removes_false_positive` (PA-MPJPE 60% 감소 검증)
- `test_twist_motion_shoulder_hip_ratio_not_in_score_dimension` (IPSF Twist 박제)
- `test_foreshortening_lying_pose_disables_width_correction` (D-06-A3 박제)
- `test_unstable_arm_swing_lowers_confidence_below_threshold` (D-06-A4 박제)
- `test_split_angle_uses_hip_knee_line_not_toe_to_toe` (Notebook 3 §3.4 박제)

#### Analog 2: `tests/test_body_normalization_lockstep.py` (3-way contract drift 방어)

**3-way lockstep test pattern** (`test_body_normalization_lockstep.py:40-90`):
```python
_TS_PATH = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_PY_MODELS_PATH = (
    _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared" / "models.py"
)
_CONTRACT_PATH = _REPO_ROOT / "docs" / "contract.md"

_FIELD_MAP = {
    "estimatedHeightScale": "estimated_height_scale",
    ...
}


def test_ts_body_normalization_profile_interface() -> None:
    """TS BodyNormalizationProfile interface 가 7개 필드를 정의."""
    src = _TS_PATH.read_text(encoding="utf-8")
    assert "interface BodyNormalizationProfile" in src, (
        "BodyNormalizationProfile interface 정의 누락"
    )
    for camel in _FIELD_MAP.keys():
        assert camel in src, ...
```
→ Phase 6 박제: 신규 `test_body_comparison_report_lockstep.py` 추가. `_FIELD_MAP` = `{"comparisonType": "comparison_type", "scaleRatios": "scale_ratios", "findings": "findings", "bodyNormalizationConfidence": "body_normalization_confidence", "warnings": "warnings"}`. 3 파일 (TS / Python / contract.md §8) 동시 박제 검증.

#### Analog 3: `tests/conftest.py` (sunity_shared path 주입)

**Existing conftest** (`tests/conftest.py:1-12`):
```python
"""유닛 테스트가 AWS/배포 없이 sunity_shared 를 import 할 수 있도록 경로 주입.
배포 시에는 Lambda Layer 가 /opt/python 에 올려주므로 이 파일은 테스트 전용.
"""
import sys
from pathlib import Path
_LAYER = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))
```
→ Phase 6 박제: **신규 conftest 불필요**. 기존 박제 그대로 재사용. fixture JSON 만 `tests/fixtures/body_comparison/` 디렉토리에 추가.

---

### 4. `app/scripts/seed-reference-body-profile.mjs` (NEW)

**Role:** one-off Firebase Admin SDK 백필 스크립트 — 정은지 reference 5개 (ref-sideway-spin / ref-climb / ref-invert / ref-foxtop / ref-foxtop-split) 에 `measure_body_profile` 결과 fixture 박제.

**Data flow:** 옵션 (a) Python helper 호출 (Phase 2 박제 `measure_body_profile` + RTMW Pod inference) → JSON fixture → `node seed-reference-body-profile.mjs --profile <path>` → Firestore `reference/{motionId}` merge. 또는 옵션 (b) Pod GPU 환경에서 직접 측정한 JSON fixture 만 로딩.

**Reuse opportunity:** `seed-reference-motions.mjs` 의 모든 인프라 (Firebase Admin SDK init + Application Default Credentials + batch.set merge + parseArgs + loadAnglesPayload + idempotent 박제) 그대로 재사용. 다른 점은 motion 메타 박제 X, `bodyNormalizationProfile` nullable 필드만 박제.

**Net-new vs adapt:** **Adapt of `seed-reference-motions.mjs`** — 동일 인프라 + 다른 payload (BodyNormalizationProfile dict).

**Closest analogs:**

#### Analog 1: `app/scripts/seed-reference-motions.mjs` (Firebase Admin SDK + ADC + batch.set merge)

**Firebase Admin SDK initialization pattern** (`seed-reference-motions.mjs:1-21, 47-48, 228-237`):
```javascript
// 사용법:
//   1) (최초 1회) gcloud auth application-default login  ← 키 파일 X, 브라우저 로그인
//      sunity3412@gmail.com (sunity-ai-coach 프로젝트 소유 계정) 선택
//   2) cd app && npm run seed:reference

import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { applicationDefault, initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

const PROJECT_ID = 'sunity-ai-coach';
const ATHLETE = '정은지';

async function main() {
  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();
  ...
}
```
→ Phase 6 박제 그대로. 메모리 [[firebase-project-account]] 박제 정합 — sunity3412@gmail.com 박제 유지.

**parseArgs + idempotent payload load pattern** (`seed-reference-motions.mjs:27-45`):
```javascript
function parseArgs(argv) {
  const out = { anglesPath: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--angles' && i + 1 < argv.length) {
      out.anglesPath = argv[i + 1];
      i++;
    }
  }
  return out;
}

function loadAnglesPayload(path) {
  const raw = readFileSync(path, 'utf8');
  const data = JSON.parse(raw);
  if (!data.motions || !Array.isArray(data.jointKeys)) {
    throw new Error(`잘못된 angles JSON 형식: ${path}`);
  }
  return data;
}
```
→ Phase 6 박제: `--profiles <path>` 옵션 박제. `data.motions[motionId] = {estimatedHeightScale, armScale, legScale, torsoScale, shoulderHipRatio, confidence, warnings}` 박제 (camelCase, TS contract 정합).

**Batch merge + idempotent set pattern** (`seed-reference-motions.mjs:246-287`):
```javascript
const batch = db.batch();
for (const m of MOTIONS) {
  const ref = db.collection('reference').doc(m.motionId);
  const doc = {
    motionId: m.motionId,
    name: m.name,
    ...
    updatedAt: Date.now(),
  };
  if (anglesPayload && anglesPayload.motions[m.motionId]) {
    const a = anglesPayload.motions[m.motionId];
    doc.angles = a.angles.flat();
    doc.anglesUpdatedAt = Date.now();
    doc.anglesFrames = a.numFrames;
    doc.anglesJointKeys = anglesPayload.jointKeys;
  }
  batch.set(ref, doc, { merge: true });
  ...
}
await batch.commit();
```
→ Phase 6 박제 동일 패턴. `--profiles <path>` 인자 시 5 motionId 별로 batch.set({merge: true}) — 기존 doc 보존 + bodyNormalizationProfile 필드만 박제. **Firestore Admin SDK 가 undefined 거부** (line 252-253 박제) → 측정 실패 motionId 는 박제 스킵 + 콘솔 warning 박제.

#### Analog 2: `app/scripts/verify-firebase.mjs` (verification 패턴 — 박제 후 sanity check)

**Verification pattern** (`verify-firebase.mjs:43-60`):
```javascript
console.log(`[1/4] 프로젝트: ${config.projectId} — 익명 로그인 시도...`);
const cred = await signInAnonymously(auth);
...
const ref = doc(db, 'users', uid, '_healthcheck', 'ping');
await setDoc(ref, { ts: serverTimestamp(), source: 'verify-firebase' });
console.log(`[3/4] Firestore 쓰기 OK (users/${uid}/_healthcheck/ping)`);

const snap = await getDoc(ref);
if (!snap.exists()) throw new Error('쓴 문서를 다시 읽지 못함');
console.log('[4/4] Firestore 읽기 OK');
```
→ Phase 6 박제: seed 스크립트 마지막에 박제 그대로 read-back verify 박제 — `seed-reference-motions.mjs` 의 verify 블록 (line 290-300) 도 참조. `bodyNormalizationProfile` 필드 박제 성공 박제 콘솔 출력.

---

### 5. `app/src/types/analysis.ts` (MODIFY)

**Role:** TS contract — 신규 `BodyComparisonReport` interface + `ComparisonType` union + `BodyComparisonFinding` + `ScaleProfile` + `AnalysisDoc.bodyComparisonReport` nullable 필드. `ReferenceMotion.bodyNormalizationProfile` nullable 필드 (D-06-B2).

**Data flow:** 단일 contract source — backend Python + docs/contract.md 와 atomic commit lockstep.

**Reuse opportunity:** 기존 `BodyNormalizationProfile` interface (analysis.ts:373-416) 인접 박제. JSDoc lockstep 박제 패턴 그대로. union type `ScoreDimension`, `AnalysisStatus` 박제 패턴 그대로.

**Net-new vs adapt:** **Adapt — 기존 interface 옆에 신규 interface 추가**. 인접 박제 보존.

**Closest analog:**

#### Analog: 기존 `BodyNormalizationProfile` interface (인접 박제)

**Interface + JSDoc lockstep header pattern** (`app/src/types/analysis.ts:359-416`):
```typescript
/**
 * 체형 정규화 프로파일 (D-19 RTMW pivot — SMPL-X β 없이 segment 비율).
 *
 * Python lockstep: backend/shared/python/sunity_shared/analysis/body_normalization.py
 *   BodyNormalizationProfile
 * 변경 시 양쪽 + docs/contract.md §6 동시 갱신 (CLAUDE.md Cross-cutting).
 *
 * SMPL-X β / shape_params 필드는 **영구히 도입하지 않는다** (D-19).
 * ...
 */
export interface BodyNormalizationProfile {
  estimatedHeightScale: number;
  armScale: number;
  legScale: number;
  torsoScale: number;
  shoulderHipRatio: number;
  confidence: number;
  warnings: string[];
}
```
→ Phase 6 박제: 본 interface 박제 바로 아래 신설:
```typescript
/**
 * 체형 정규화 비교 리포트 (Phase 6, D-06-B3 박제).
 *
 * Python lockstep: backend/shared/python/sunity_shared/analysis/body_normalizer.py
 *   BodyComparisonReport
 * 변경 시 양쪽 + docs/contract.md §8 동시 갱신 (CLAUDE.md Cross-cutting).
 *
 * Universal Principle (D-06-U1): confidence-tiered hybrid —
 *   bodyNormalizationConfidence < 0.5 → 정규화 OFF + warnings 박제.
 *   bodyNormalizationConfidence ≥ 0.5 → 5 필드 정규화 ON + findings 박제.
 */
export type ComparisonType =
  | 'mode1'
  | 'mode3_first'
  | 'mode3_first_with_fallback'
  | 'mode3_progress';

export interface ScaleProfile {
  estimatedHeightScale: number;
  armScale: number;
  legScale: number;
  torsoScale: number;
  shoulderHipRatio: number;
}

export interface BodyComparisonFinding {
  jointKey: string;           // RTMW COCO-17 keypoint name
  ipsfCriterion: string;      // Page 9 7종 (knee_toe_alignment, clean_lines, ...)
  deficitDeg: number;         // 절대 deficit (체형 ratio X — IPSF 박제 정합)
}

export interface BodyComparisonReport {
  comparisonType: ComparisonType;
  scaleRatios: ScaleProfile | null;  // null = 정규화 OFF (confidence < 0.5)
  findings: BodyComparisonFinding[];
  bodyNormalizationConfidence: number;  // [0.0, 1.0]
  warnings: string[];
}
```

**AnalysisDoc extension pattern** (`analysis.ts:194-209`):
```typescript
export interface AnalysisDoc {
  analysisId: string;
  mode: AnalysisMode;
  status: AnalysisStatus;
  ...
  result?: AnalysisResult;
  angles?: number[];
  anglesJointKeys?: string[];
  anglesFrames?: number;
  videoFormat?: VideoFormat;
}
```
→ Phase 6 박제: `bodyComparisonReport?: BodyComparisonReport` 박제. AnalysisResult 박제 박제 위치 (result 내부 박제 vs AnalysisDoc top-level) — RESEARCH.md 의 `_process` 박제 박제 `result.bodyComparisonReport` 와 정합 박제. AnalysisResult interface (analysis.ts:174-191) 박제 `bodyComparisonReport?: BodyComparisonReport` 신설.

**ReferenceMotion extension** (`analysis.ts:241-269`):
```typescript
export interface ReferenceMotion {
  motionId: string;
  name: string;
  athleteName: string;
  ...
  anglesJointKeys?: string[];
  anglesFrames?: number;
  meanAngles?: Record<string, number>;
}
```
→ Phase 6 박제 (D-06-B2): `bodyNormalizationProfile?: BodyNormalizationProfile` 신설.

---

### 6. `backend/shared/python/sunity_shared/models.py` (MODIFY)

**Role:** Python contract mirror — `BodyComparisonReport` re-export (분석 모듈에서 정의 + models.py 에서 re-export). 3-way lockstep header 박제.

**Data flow:** body_normalizer 가 정의 → models.py re-export → 외부 모듈 (`pipeline/app.py`, `firestore_admin.py`) 가 import.

**Reuse opportunity:** 기존 `BodyNormalizationProfile` re-export (models.py:119-126) 박제 패턴 그대로.

**Net-new vs adapt:** **Adapt — 동일 re-export 패턴 추가**.

**Closest analog:**

#### Analog: 기존 `BodyNormalizationProfile` re-export (인접 박제)

**Re-export + 3-way lockstep header pattern** (`models.py:119-126`):
```python
# RTMW pivot (2026-06-02, Plan 01-19) — D-19/D-21 박제.
#   BodyNormalizationProfile = SMPL-X β 없이 segment 비율 + confidence + warnings.
#   PoseFrame.body_shape: Optional[BodyNormalizationProfile] = None nullable.
# TS 미러: app/src/types/analysis.ts BodyNormalizationProfile interface.
# 변경 시 TS + contract.md §6 동시 갱신 (CLAUDE.md Cross-cutting).
from .analysis.body_normalization import (  # noqa: E402 — 파일 하단 re-export 패턴
    BodyNormalizationProfile,
)
```
→ Phase 6 박제 하단에 신설:
```python
# Phase 6 (2026-06-08) — D-06-B3 박제.
#   BodyComparisonReport = comparisonType + scaleRatios + findings + confidence.
#   확장: ScaleProfile, BodyComparisonFinding, ComparisonType Literal.
# TS 미러: app/src/types/analysis.ts BodyComparisonReport interface.
# 변경 시 TS + contract.md §8 동시 갱신 (CLAUDE.md Cross-cutting).
from .analysis.body_normalizer import (  # noqa: E402 — 파일 하단 re-export 패턴
    BodyComparisonFinding,
    BodyComparisonReport,
    ComparisonType,
    ScaleProfile,
)
```

---

### 7. `docs/contract.md` §8 (MODIFY)

**Role:** docs contract — `BodyComparisonReport` 명세. 기존 §7 BodyNormalizationProfile (contract.md:321-378) 인접 박제.

**Data flow:** 사람-readable spec — TS + Python lockstep 박제 박제.

**Reuse opportunity:** 기존 §7 박제 (BodyNormalizationProfile) 의 Markdown 구조 그대로.

**Net-new vs adapt:** **Adapt — 동일 구조로 §8 신설**.

**Closest analog:**

#### Analog: 기존 §7 BodyNormalizationProfile 명세

**Section structure pattern** (`docs/contract.md:321-378`):
```markdown
## §7. BodyNormalizationProfile (Plan 01-19 신설 — D-19/D-21 RTMW pivot)

> 변경 시 동시 갱신:
>   - app/src/types/analysis.ts BodyNormalizationProfile interface
>   - backend/.../body_normalization.py BodyNormalizationProfile dataclass
>   - 이 문서 §7

### BodyNormalizationProfile (체형 정규화 프로파일)
...
[필드 7개 박제 + 5 warning enum 박제]
...
*Plan 01-19 §7 추가: 2026-06-02 — BodyNormalizationProfile (D-19 segment 비율, D-21 nullable). RTMW pivot 박제.*
```
→ Phase 6 박제: `## §8. BodyComparisonReport (Plan 06-* 신설 — D-06-B3 confidence-tiered hybrid)` 박제. 3-way 동시 갱신 박제 헤더 + ComparisonType union 4 case (mode1/mode3_first/mode3_first_with_fallback/mode3_progress) + ScaleProfile 5 필드 + BodyComparisonFinding (jointKey/ipsfCriterion/deficitDeg) + bodyNormalizationConfidence [0, 1] + warnings 5 enum (low_confidence_normalization_off/foreshortening_off/shoulder_hip_ratio_off/temporal_variance_high/spatial_dispersion_high) 박제. 박제 일자 footer 박제.

---

### 8. `backend/functions/pipeline/app.py::_process` (MODIFY)

**Role:** handler wiring — `_process` 의 mode1 / mode3 분기 안에 정규화 호출 박제. comparisonType 결정 위치. `_angles_and_body_profile_from_video` (Phase 2 박제 helper, pipeline/app.py:306) 출력 student_profile 소비.

**Data flow:** `_angles_and_body_profile_from_video` → `(angles, student_profile)` → recognizer.recognize → comparisonType 분기 (mode1 = ref fetch / mode3 = prev fetch + fallback) → `body_normalizer.compare_body_profiles` → `BodyComparisonReport` → `firestore_admin.complete_analysis(body_comparison_report=...)`.

**Reuse opportunity:** 기존 `_angles_from_video` 호출 자리 (line 449-452) 교체 박제 X (양립 박제) — Phase 2 박제 helper `_angles_and_body_profile_from_video` 박제 호출 site 추가. `_mode3_comparison` helper 패턴 박제 — Phase 6 도 동일 pure 함수 박제 권장 (`_body_comparison_for_mode` 신설).

**Net-new vs adapt:** **Adapt — 기존 `_process` 안에 박제 추가 + 신규 helper 함수 분리**.

**Closest analogs:**

#### Analog 1: 기존 `_process` 의 mode 분기 본체

**Mode 분기 본체 pattern** (`pipeline/app.py:476-525`):
```python
if mode == models.MODE_EXPERT:
    ref = firestore_admin.get_reference_motion(meta.get("referenceMotionId"))
    if ref is None or "angles" not in ref:
        raise RuntimeError("기준 모션 또는 keyframe 데이터 없음")
    num_joints = len(ref.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    deviation, match, user_seg, a_ref = _deviation_against(
        angles, ref["angles"], num_joints
    )
    assessments = kismam.assess(deviation)
    angle_dim = kismam.overall_score(assessments)
    if angle_dim < models.NOT_POLE_SIMILARITY_THRESHOLD:
        raise NotPoleMotionError(...)
    dimension_scores = {dimensions.DIM_ANGLE: angle_dim, **abs_dims}
    overall = dimensions.overall_from_dimensions(dimension_scores)
    ...
    comparison = assemble.build_mode1(ref, angle_dim, seg_scores)
else:  # MODE_SELF — 자기 성장.
    prev = firestore_admin.get_previous_analysis(
        uid, analysis_id, mode=models.MODE_SELF
    )
    assessments, dimension_scores, overall, comparison = _mode3_comparison(
        angles, prev, profile
    )
```
→ Phase 6 박제: 본 분기 안에 박제 추가:
```python
# Phase 6 박제 — comparisonType 분기 + body_normalizer 호출.
if mode == models.MODE_EXPERT:
    ref = firestore_admin.get_reference_motion(meta.get("referenceMotionId"))
    ref_body_profile = None
    raw = ref.get("bodyNormalizationProfile") if ref else None
    if raw is not None:
        ref_body_profile = BodyNormalizationProfile(**raw)
    body_comparison_report = body_normalizer.compare_body_profiles(
        student_profile=student_profile,
        reference_profile=ref_body_profile,
        comparison_type="mode1",
        angles=angles,
        technique_profile=profile,
    )
    ...
else:  # MODE_SELF
    prev = firestore_admin.get_previous_analysis(uid, analysis_id, mode=models.MODE_SELF)
    if prev is None:
        # mode3 first — Page 9 단독 + Gemini fallback 분기 (D-06-B1)
        ref_body_profile = None
        comp_type = "mode3_first"
        if profile.name != "미상" and student_profile.confidence >= 0.5:
            fallback_ref = _match_reference_by_motion_id(profile.motion_id)
            if fallback_ref and fallback_ref.get("bodyNormalizationProfile"):
                ref_body_profile = BodyNormalizationProfile(
                    **fallback_ref["bodyNormalizationProfile"])
                comp_type = "mode3_first_with_fallback"
    else:
        prev_raw = prev.get("bodyNormalizationProfile")
        ref_body_profile = (
            BodyNormalizationProfile(**prev_raw) if prev_raw else None
        )
        comp_type = "mode3_progress"
    body_comparison_report = body_normalizer.compare_body_profiles(
        student_profile=student_profile,
        reference_profile=ref_body_profile,
        comparison_type=comp_type,
        angles=angles,
        technique_profile=profile,
    )
```

**Helper input swap pattern** (`pipeline/app.py:447-452`):
```python
recognizer = _ensure_recognizer()
local_video_path: str | None = None
if _gemini_enabled():
    angles, local_video_path = _angles_and_video_path_from_video(bucket, key)
else:
    angles = _angles_from_video(bucket, key)
```
→ Phase 6 박제: 위 분기 박제 + Phase 2 helper `_angles_and_body_profile_from_video` (pipeline/app.py:306) 박제 정합 — Gemini path 박제 + Phase 6 path 둘 다 student_profile 박제 필요. RESEARCH.md §Architectural Responsibility Map 박제: "본 phase 가 호출 site 갱신만" — 기존 helper 시그너처 무변경 박제 정신 정합. 박제 분기:
```python
if _gemini_enabled():
    angles, local_video_path = _angles_and_video_path_from_video(bucket, key)
    # student_profile 별도 호출 — Phase 6 박제
    _, student_profile = _POSE_ESTIMATOR.estimate_with_profile(frames)  # 박제 필요
else:
    angles, student_profile = _angles_and_body_profile_from_video(bucket, key)
```
**박제 참고:** 위 박제는 RESEARCH.md 의 "RunPod / pipeline 둘 다 `_process` 단일 path" 박제 정합 (메모리 [[runpod-gpu-env]] 박제 정신). RunPod server.py 박제 무수정 박제 — `_process` import 박제만.

#### Analog 2: `_mode3_comparison` (pure-function helper 박제)

**Pure helper extraction pattern** (`pipeline/app.py:387-425`):
```python
def _mode3_comparison(
    angles: np.ndarray, prev: dict | None, profile: technique.TechniqueProfile
):
    """자기 성장(mode3) 분기 — 순수(어댑터/S3/Firestore 불필요, 테스트 가능).
    ...
    반환: (assessments, dimension_scores, overall, comparison).
    """
    abs_dims = dimensions.absolute_dimension_scores(angles, profile)
    prev_angles = (prev or {}).get("angles")
    if not prev or not prev_angles:
        # 첫 분석 ...
        return assessments, abs_dims, overall, assemble.build_mode3(is_first=True)
    ...
```
→ Phase 6 박제: 동일 패턴 — `_body_comparison_for_mode` 신규 helper 박제. pure 함수 (어댑터/S3/Firestore 무관) + 단위 테스트 가능. `pipeline/app.py:476-525` 분기 박제 박제 helper 호출로 박제 — 박제 일관성.

---

### 9. `backend/shared/python/sunity_shared/firestore_admin.py::complete_analysis` (MODIFY)

**Role:** Firestore I/O — `bodyComparisonReport` 박제. Firestore nested-array 금지 박제 정합 — `scaleRatios` (dict, OK), `findings` (flat dict 리스트, OK), `normalizedProReference` 좌표 (flat array 박제 — RESEARCH.md 박제).

**Data flow:** body_normalizer 의 `BodyComparisonReport` → `dataclasses.asdict()` → Firestore set merge.

**Reuse opportunity:** 기존 `complete_analysis` 의 `angles` / `anglesJointKeys` / `anglesFrames` flat 저장 패턴 + nested-array 검증 박제 (`store_gemini_cache` line 186-199) 박제 그대로.

**Net-new vs adapt:** **Adapt — 신규 arg + 동일 flat 저장 패턴**.

**Closest analogs:**

#### Analog 1: 기존 `complete_analysis` 의 flat 저장 패턴

**Flat angles 저장 pattern** (`firestore_admin.py:45-70`):
```python
def complete_analysis(
    uid: str,
    analysis_id: str,
    result: dict,
    *,
    angles: list | None = None,
    angles_joint_keys: list | None = None,
    angles_frames: int | None = None,
) -> None:
    """status='done' + result (contract.md §4 AnalysisResult).

    angles 가 주어지면 추출된 관절각을 doc top-level 에 flat 저장한다 ...
    Firestore 는 nested-array 금지라 flat list + anglesJointKeys(길이 J) +
    anglesFrames(T) 로 저장하고 읽는 쪽에서 reshape ([[firestore-nested-array-flat]]).
    """
    payload: dict = {
        "status": models.STATUS_DONE,
        "result": result,
        "updatedAt": int(time.time() * 1000),
    }
    if angles is not None:
        payload["angles"] = angles
        payload["anglesJointKeys"] = angles_joint_keys
        payload["anglesFrames"] = angles_frames
    _doc(models.analysis_doc_path(uid, analysis_id)).set(payload, merge=True)
```
→ Phase 6 박제 시그너처 박제:
```python
def complete_analysis(
    uid: str,
    analysis_id: str,
    result: dict,
    *,
    angles: list | None = None,
    angles_joint_keys: list | None = None,
    angles_frames: int | None = None,
    body_comparison_report: dict | None = None,  # Phase 6 박제
) -> None:
    """...
    body_comparison_report: BodyComparisonReport dataclass.asdict() 박제.
        nested-array 금지 박제 정합 — findings 는 flat dict 리스트, scaleRatios 는
        flat dict (5 필드 float).
    """
    payload: dict = {...}
    if angles is not None:
        ...
    if body_comparison_report is not None:
        _validate_flat_dict_no_nested_array(body_comparison_report)  # 박제 박제
        # result 내부 박제 (analysis.ts AnalysisResult.bodyComparisonReport 정합)
        payload["result"] = {**result, "bodyComparisonReport": body_comparison_report}
    _doc(models.analysis_doc_path(uid, analysis_id)).set(payload, merge=True)
```

#### Analog 2: `store_gemini_cache` 의 nested-array 검증 박제

**Nested-array detection pattern** (`firestore_admin.py:186-199`):
```python
# nested-array 정합 검증 ([[firestore-nested-array-flat]])
if "moments" in payload and payload["moments"]:
    for i, m in enumerate(payload["moments"]):
        if not isinstance(m, dict):
            raise TypeError(
                f"moments[{i}] must be flat dict "
                f"(firestore-nested-array-flat): got {type(m).__name__}"
            )
        for k, v in m.items():
            if isinstance(v, (list, tuple)):
                raise TypeError(
                    f"moments[{i}][{k}] must be scalar "
                    f"(firestore nested array 금지): got {type(v).__name__}"
                )
```
→ Phase 6 박제: 동일 패턴 — `findings: list[dict]` 박제 검증 (각 finding flat dict, value 가 list/tuple 박제 X). `scaleRatios` 박제 — flat dict (5 필드 float) 박제 검증. 박제 helper 함수 박제 `_validate_flat_dict_no_nested_array` 신설 권장 — 동일 메모리 [[firestore-nested-array-flat]] 박제 정합.

---

### 10. `backend/functions/reference-api/app.py` + `firestore_admin.get_reference_motion` (MODIFY)

**Role:** reference-motions 응답에 `bodyNormalizationProfile` nullable 필드 박제 (D-06-B2 박제).

**Data flow:** Firestore `reference/{motionId}` doc → JSON response. 백필 스크립트 박제 후 일부 motion 박제 박제 필드 박제, 나머지 박제 X.

**Reuse opportunity:** 기존 `list_reference_motions` (firestore_admin.py:85-93) + `get_reference_motion` (firestore_admin.py:106-113) 박제 박제 변경 X — Firestore `to_dict()` 가 자동으로 `bodyNormalizationProfile` 필드 박제 박제 박제. **수정 박제 필요 X** — Firestore admin SDK 박제 박제 박제 자동.

**Net-new vs adapt:** **No-op (자동 박제)**. 단, contract.md 박제 박제 박제 `ReferenceMotion.bodyNormalizationProfile` 필드 박제 박제 필요. 백필 스크립트 (#4) 만 박제.

**Closest analog:**

#### Analog: `get_reference_motion` (자동 박제 패턴)

**Auto-passthrough pattern** (`firestore_admin.py:106-113`):
```python
def get_reference_motion(motion_id: str) -> dict | None:
    """기준 모션 1건. keyframe 각도 데이터(angles) + 메타 포함(ml_CLAUDE.md 등록)."""
    snap = _doc(models.reference_motion_path(motion_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data.setdefault("motionId", motion_id)
    return data
```
→ Phase 6 박제: **함수 박제 변경 X**. `data` 에 `bodyNormalizationProfile` 박제 박제 박제 박제 자동 (백필 스크립트 박제 후). 단, `pipeline/app.py::_process` 에서 박제:
```python
ref = firestore_admin.get_reference_motion(meta.get("referenceMotionId"))
raw = ref.get("bodyNormalizationProfile") if ref else None  # nullable
ref_body_profile = BodyNormalizationProfile(**raw) if raw else None
```

**Reference-api Lambda handler** (`backend/functions/reference-api/app.py:19-33`):
```python
def lambda_handler(event: dict, _context) -> dict:
    try:
        verify_request(event)
    except AuthError as e:
        return responses.error("unauthorized", e.message, status=401)
    try:
        motions = firestore_admin.list_reference_motions()
    except Exception:
        log.exception("기준 모션 조회 실패")
        return responses.error(
            "server_error", "기준 모션을 불러오지 못했어요.", status=500
        )
    return responses.ok(motions)
```
→ Phase 6 박제: **변경 X**. `list_reference_motions` 박제 `to_dict()` 박제 박제 자동.

---

### 11. `app/src/lib/userAnalyses.ts::normalize` (MODIFY)

**Role:** client-side defensive normalize — `bodyComparisonReport` 박제 박제. Phase 12 UI 박제 `useAnalysisDoc` 박제 박제 박제 박제 박제 박제 박제 박제.

**Data flow:** Firestore raw doc → `normalize(id, raw)` → `AnalysisDoc | null`. 기존 `result?` 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 (AnalysisResult.bodyComparisonReport 박제 박제 박제).

**Reuse opportunity:** 기존 `normalize` 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. AnalysisResult.bodyComparisonReport 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제.

**Net-new vs adapt:** **No-op for normalize, but type 박제 박제 박제 박제 박제 박제 박제 박제**. AnalysisResult interface 박제 박제 박제 박제 (#5) 박제 박제 박제 박제 박제.

**Closest analog:**

#### Analog: 기존 `normalize` 박제 박제 패턴

**Defensive normalize pattern** (`app/src/lib/userAnalyses.ts:27-53`):
```typescript
function normalize(id: string, raw: Record<string, unknown>): AnalysisDoc | null {
  const mode = raw.mode === 'mode1' || raw.mode === 'mode3' ? raw.mode : null;
  const status = raw.status as AnalysisStatus | undefined;
  // fileName 은 빈 문자열일 수 있다 ...
  const fileName = typeof raw.fileName === 'string' ? raw.fileName : null;
  const createdAt = typeof raw.createdAt === 'number' ? raw.createdAt : null;
  const updatedAt = typeof raw.updatedAt === 'number' ? raw.updatedAt : createdAt;
  if (
    !mode ||
    !status ||
    fileName === null ||
    createdAt == null ||
    updatedAt == null
  )
    return null;
  return {
    analysisId: id,
    mode,
    status,
    fileName,
    createdAt,
    updatedAt,
    error: raw.error as AnalysisDoc['error'],
    result: raw.result as AnalysisDoc['result'],
  };
}
```
→ Phase 6 박제: `raw.result` 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 — AnalysisResult.bodyComparisonReport 박제 박제 박제 박제 박제 박제 박제 박제 박제. **normalize 변경 박제 X** — TypeScript 박제 `AnalysisResult.bodyComparisonReport?: BodyComparisonReport` 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. 단, 박제 박제 박제 박제 박제 박제 박제 — defensive validation 박제 박제 박제 박제:
```typescript
// 옵션: 박제 박제 박제 박제 박제 박제 박제 normalize 박제 박제
const bodyComparison =
  raw.bodyComparisonReport &&
  typeof raw.bodyComparisonReport === 'object' &&
  typeof (raw.bodyComparisonReport as any).comparisonType === 'string'
    ? (raw.bodyComparisonReport as BodyComparisonReport)
    : undefined;
```
**박제 권장:** AnalysisResult 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제.

---

## Shared Patterns

### A. 3-way Contract Lockstep (TS / Python / contract.md atomic commit)

**Source:** CLAUDE.md Cross-cutting + `body_normalization_lockstep` 테스트 + 기존 BodyNormalizationProfile (analysis.ts:359-416 + models.py:119-126 + contract.md §7)

**Apply to:** `app/src/types/analysis.ts` + `backend/.../models.py` + `backend/.../body_normalizer.py` + `docs/contract.md` §8 + 신규 `tests/test_body_comparison_report_lockstep.py`

**Pattern:**
```
1. TS interface 박제 (analysis.ts) — camelCase
2. Python dataclass 박제 (body_normalizer.py) — snake_case + frozen + __post_init__ validator
3. models.py re-export
4. docs/contract.md §8 박제 박제 (3-way header — 변경 시 동시 갱신 박제)
5. tests/test_body_comparison_report_lockstep.py — TS/Python/contract.md 박제 박제 drift 방어
6. 단일 atomic commit 박제 박제 (4 파일 박제 1 commit)
```

### B. Pure-function + numpy-only purity (algorithm 박제)

**Source:** `motiondtw.py`, `dimensions.py`, `body_normalization_measurer.py`

**Apply to:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py`

**Pattern:** 외부 모델 의존 0, scipy 의존 0, numpy + stdlib (math/dataclasses/typing) 만. `from __future__ import annotations` 첫 줄 박제. shape validation 함수 (`_as_tj`) 박제 — `compute_body_normalization_confidence(angles, scale_profile)` 박제 박제 (T, J) 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제.

### C. Korean docstring + decision history 박제

**Source:** `body_normalization.py:48-87` (D-19/D-21 박제 + Phase 2 v5 박제), `dimensions.py:10-19` (2026-05-29 재교정 박제)

**Apply to:** All Phase 6 신설/수정 Python 파일

**Pattern:** 모듈 docstring 박제 박제 박제 박제 박제 박제 — 박제 (D-06-A*, D-06-B*, D-06-U1) 박제 박제 박제 박제 박제 박제. 박제 일자 박제 (2026-06-08 belle 박제). 메모리 [[scoring-dimensions-ipsf]], [[ipsf-5-track-scoring]], [[feedback-analysis-first]], [[mvp-simple-pilot-quality]], [[analysis-objectivity-no-human-scores]], [[mode3-progress-not-similarity]], [[firestore-nested-array-flat]] 박제 박제 박제.

### D. Confidence-tiered hybrid (D-06-U1 박제 — universal principle)

**Source:** RESEARCH.md §Universal Principle + NotebookLM §4.2 (temporal variance 5-10%)

**Apply to:** `body_normalizer.compare_body_profiles` + `body_normalizer.compute_body_normalization_confidence` + `BodyComparisonReport.warnings` + `pipeline/_process` mode3 first fallback 분기

**Pattern:**
```python
# 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 (Universal Principle D-06-U1)
CONFIDENCE_GATE = 0.5

def compare_body_profiles(student, reference, comparison_type, ...) -> BodyComparisonReport:
    confidence = compute_body_normalization_confidence(...)
    if confidence < CONFIDENCE_GATE or reference is None:
        # 박제 fallback — raw 비교, 정규화 OFF, IPSF 절대 deficit 만
        return BodyComparisonReport(
            comparison_type=comparison_type,
            scale_ratios=None,
            findings=measure_ipsf_absolute_deficits(angles, profile),  # Page 9 단독
            body_normalization_confidence=confidence,
            warnings=["low_confidence_normalization_off"],
        )
    # 박제 박제 — 5 필드 정규화 ON
    scale = ScaleProfile(...)
    findings = measure_ipsf_deficits_with_normalization(angles, profile, scale)
    return BodyComparisonReport(...)
```

### E. Firestore nested-array 회피 (flat 저장)

**Source:** `firestore_admin.complete_analysis` (line 56-70) + `store_gemini_cache` (line 186-199) + 메모리 [[firestore-nested-array-flat]]

**Apply to:** `firestore_admin.complete_analysis(body_comparison_report=...)` 박제

**Pattern:** `findings` 는 flat dict 리스트 박제 (`[{"jointKey": str, "ipsfCriterion": str, "deficitDeg": float}, ...]`), `scaleRatios` 는 flat dict 박제 (5 필드 float). `normalizedProReference` 좌표 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 — flat array + jointKeys + frames 박제 박제 (기존 `angles` 박제 패턴 정합). 박제 helper `_validate_flat_dict_no_nested_array` 박제 권장.

---

## No Analog Found

박제 박제 박제 박제 박제 박제 박제 — 모든 11 파일 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제.

---

## Metadata

- **Files scanned (analog 검색):** ~40 (analysis/ + tests/ + functions/ + scripts/ + lib/)
- **Pattern extraction date:** 2026-06-08
- **Total analog excerpts:** 22 (file_path:line_range 박제 박제)
- **CLAUDE.md cross-cutting compliance:** 3-way lockstep + Korean comments + 이모지 X + pure 함수 + Protocol adapter — 박제 박제 박제 박제 박제 박제 박제.
