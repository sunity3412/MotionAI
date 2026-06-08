# Phase 7: 차이 분류 — Pattern Map

**Mapped:** 2026-06-08
**Files analyzed:** 13 (3 modified + 10 new)
**Analogs found:** 13 / 13 (Phase 6 박제 코드 100% 재사용)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/body_normalizer.py` (MOD) | model + classification logic | transform | self — Phase 6 본체 (dataclass + measure_ipsf_absolute_deficits + compare_body_profiles) | exact (확장) |
| `backend/shared/python/sunity_shared/analysis/copy_templates.py` (NEW) | canned strings module | static lookup | `backend/shared/python/sunity_shared/analysis/assemble.py` (`_DIMENSION_BASELINES_MODE1/_MODE3`, `_GOOD_COPY_BY_DIM`) + `skeleton.py` (`JOINT_LABEL_KO`) | role-match (dict literal canned 카피 패턴) |
| `app/src/types/analysis.ts` (MOD) | TS contract | schema lockstep | self — `BodyComparisonFinding` + `BodyComparisonReport` Phase 6 박제 | exact (필드 확장) |
| `docs/contract.md` §8 + §8.1 (MOD) | docs contract | schema lockstep | self — Phase 6 §8 박제 | exact (필드 확장) |
| `backend/tests/phase07/__init__.py` (NEW) | test marker | n/a | `backend/tests/phase06/__init__.py` | exact |
| `backend/tests/phase07/conftest.py` (NEW) | test config | n/a | `backend/tests/phase06/conftest.py` | exact |
| `backend/tests/phase07/fixtures/_factory.py` (NEW) | fixture loader | file I/O | `backend/tests/phase06/fixtures/_factory.py` (load_fixture_raw + JSON loader) | exact (단순화 — PoseFrame 불요, finding dict 직접 로딩) |
| `backend/tests/phase07/fixtures/*.json` × 7 (NEW) | test fixtures | static data | `backend/tests/phase06/fixtures/fixture_*.json` | role-match (구조 단순화) |
| `backend/tests/phase07/test_classify_findings.py` (NEW) | unit test | request-response | `backend/tests/phase06/test_body_normalizer_ipsf_deficit.py` | exact (산식 단위 test 패턴) |
| `backend/tests/phase07/test_copy_templates_no_forbidden.py` (NEW) | unit test (grep gate) | static check | (없음 — 신규 패턴, parametrize over FORBIDDEN tuple) | partial — pytest parametrize 패턴은 phase06 정합 |
| `backend/tests/phase07/test_copy_templates_render.py` (NEW) | unit test | request-response | `backend/tests/phase06/test_body_normalizer_ipsf_deficit.py` (단순 함수 호출 + assert) | role-match |
| `backend/tests/phase07/test_body_comparison_report_phase7_lockstep.py` (NEW) | lockstep test | static grep | `backend/tests/phase06/test_body_comparison_report_lockstep.py` (TS / Python / contract.md 3-way regex grep) | exact |
| `backend/tests/phase07/test_compare_body_profiles_phase7_integration.py` (NEW) | integration test | request-response | `backend/tests/phase06/test_compare_body_profiles.py` | exact |
| `backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py` (NEW) | unit test | transform | `backend/tests/phase06/test_dataclass_to_camel_case_dict.py` (5-case helper 자동 변환) | exact |

## Pattern Assignments

### `backend/shared/python/sunity_shared/analysis/body_normalizer.py` (modified — schema + classification)

**Analog:** self (Phase 6 본체)

**Frozen dataclass + `__post_init__` validator 패턴** (`body_normalizer.py:787-820`):

```python
@dataclass(frozen=True)
class BodyComparisonFinding:
    deficit_code: str
    joint_key: str | None
    measured_value: float
    deduction_score: float
    confidence: float
    body_type_adjusted: bool

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"BodyComparisonFinding.confidence must be in [0, 1], "
                f"got {self.confidence}"
            )
```

→ Phase 7 확장: `category` Literal enum + `phase` nullable str + 2 optional Korean str. `__post_init__` 에 enum 검증 추가 (`category not in ("body_type_allowed", "needs_adjustment", "uncertain")` → ValueError). Phase 6 `comparison_type` 검증 패턴 (`body_normalizer.py:858-862`) 그대로 미러.

**BodyComparisonReport 확장 패턴** (`body_normalizer.py:826-895`):
```python
@dataclass(frozen=True)
class BodyComparisonReport:
    comparison_type: ComparisonType
    body_normalization_confidence: float
    ...
    used_reference_fallback: bool = False  # W1 — Gemini fallback 신호

    def __post_init__(self) -> None:
        # 기존 검증 ...
        if not isinstance(self.warnings, list):
            raise TypeError(...)
```
→ Phase 7: `do_not_over_correct: list[str] = field(default_factory=list)` + `recommended_focus: list[str] = field(default_factory=list)` 두 필드 append. Phase 6 `warnings` 의 `field(default_factory=list)` 패턴 그대로.

**Pure function 산식 시그너처** (`body_normalizer.py:901-927`):
```python
def measure_ipsf_absolute_deficits(
    angles: np.ndarray | None,
    technique_profile,
    normalized_keypoints: dict | None = None,
    *,
    pose_frames: list | None = None,
) -> list[BodyComparisonFinding]:
    """IPSF Page 21 절대 deficit 산식 + Sunity pose_reliability_low (C14 fix).
    ...
    """
    findings: list[BodyComparisonFinding] = []
    body_type_adjusted = normalized_keypoints is not None
```
→ Phase 7 `classify_findings()` 시그너처: numpy 인자 0 (순수 dict/list lookup), keyword-only `used_reference_fallback`, return 3-tuple `(list[BodyComparisonFinding], list[str], list[str])`. Phase 6 R8 박제 (extra_warnings injection 금지) 정합 — `dataclasses.replace` 우회 X, 새 인스턴스 생성.

**`compare_body_profiles()` wiring 위치** (`body_normalizer.py:1263-1297`):
```python
# 5) IPSF deficit 측정 (gate 무관 — confidence 낮으면 raw 좌표만)
findings = measure_ipsf_absolute_deficits(
    angles,
    technique_profile,
    normalized_keypoints=normalized_keypoints,
    pose_frames=pose_frames,
)

# 6) R8 fix — extra_warnings merge + validate (frozenset)
...

# 7) BodyComparisonReport 조립 — __post_init__ 의 frozenset 검증 통과 보장.
return BodyComparisonReport(
    comparison_type=comparison_type,
    body_normalization_confidence=confidence,
    ...
    used_reference_fallback=used_reference_fallback,
    ...
)
```
→ Phase 7: line 1264-1269 (measure 호출) 직후 `classify_findings()` 1줄 wiring. Return BodyComparisonReport 에 `do_not_over_correct=dnoc, recommended_focus=rec_focus` 두 kwarg 추가. `findings=classified_findings` 로 교체.

**Adapter notes:**
- Phase 7 `classify_findings` 은 **numpy 무관** (Phase 6 산식 함수와 다르게 — keypoint/angle 입력 X). Phase 6 finding dataclass 의 필드만 lookup.
- frozen dataclass 의 신설 4 필드는 모두 `dataclasses.replace()` 우회 금지 — 새 `BodyComparisonFinding(...)` 인스턴스 생성. Phase 6 R8 박제 (`backend/shared/python/sunity_shared/analysis/body_normalizer.py:885-895` warnings frozenset 검증) 정합.
- `CATEGORY_GATE = 0.2` / `CATEGORY_CONF_GATE = 0.5` 모듈 상수 추가 — Phase 6 `CONFIDENCE_GATE` (Phase 6 D-06-U1) 패턴 정합 (`body_normalizer.py` 모듈 상수 SCREAMING_SNAKE_CASE).

---

### `backend/shared/python/sunity_shared/analysis/copy_templates.py` (NEW — canned strings module)

**Analog:** `backend/shared/python/sunity_shared/analysis/assemble.py` (mode-aware baseline dict literal) + `backend/shared/python/sunity_shared/analysis/skeleton.py` (`JOINT_LABEL_KO`)

**Module docstring + spec citation 패턴** (`assemble.py:1-10`):
```python
"""KISMAM 결과 → contract.md §4 AnalysisResult dict 조립.

키 이름은 app/src/types/analysis.ts 와 정확히 일치해야 한다(계약 단일 진실).
Cerebras 문장이 없으면 실제 편차값 기반 폴백 문장 사용(수치 위조 아님).

Phase 12.5 (2026-06-07): dimensionExplanation 추가 — 사용자가 결과 화면에서
"왜 이 점수인지" 를 볼 수 있도록 차원별 baseline + weightPercent + deficitSummary
출력. ...
"""
```
→ Phase 7 module docstring: `research §10.1 권장 카피 4종 톤 정합 + §10.3 금지 6종 grep gate. Sunity 추가 톤 룰 3종: 가능성 언어 / AI 보조 도구 톤 / 부위별 원인 언어.` (CLAUDE.md Cross-cutting `§` shorthand 정합).

**mode-aware baseline dict literal 패턴** (`assemble.py:25-34`):
```python
_DIMENSION_BASELINES_MODE1 = {
    "angle": "정은지 측정값 + IPSF 실행 기준 참고",
    "line": "정은지 측정값 + 신전 완성도 (IPSF 실행 기준 참고)",
    "stability": "hold 구간 떨림 (절대 지표)",
}
_DIMENSION_BASELINES_MODE3 = {
    "angle": "이전 영상 대비 관절 각도 일관성",
    "line": "신전 완성도 (실행 기준 참고)",
    "stability": "hold 구간 떨림 (절대 지표)",
}
```
→ Phase 7 `_MODE_PREFIX: dict[ComparisonType, str]` 3 case 미러 (mode1/mode3_first/mode3_progress). `_COPY_TEMPLATES: dict[tuple[str, Category, JointGroup], tuple[str, str]]` 4축 tuple key + (interp, recom) value pair. Phase 12.5 RESEARCH.md §"Mode Branch Carry-over" 박제.

**한국어 라벨 dict 박제** (`skeleton.py:53-62`):
```python
JOINT_LABEL_KO: dict[str, str] = {
    "left_elbow": "왼쪽 팔꿈치",
    "right_elbow": "오른쪽 팔꿈치",
    "left_shoulder": "왼쪽 어깨",
    ...
}
```
→ Phase 7 `copy_templates.py` 내 `from .skeleton import JOINT_LABEL_KO` 재사용 (8 관절 라벨, 한국어 부위 어휘 source). joint_group 부위 그룹화 mapping `_JOINT_TO_GROUP` 신규 (17→5 그룹 축소).

**fallback 패턴** (`assemble.py:155-158`):
```python
def _issue_text(a: JointAssessment) -> str | None:
    if a.score >= GOOD_SCORE_THRESHOLD:
        return None
    return f"기준 대비 평균 {round(a.deviation_deg)}° 차이"
```
→ Phase 7 `render_finding_copy()` 의 KeyError fallback: `dict.get(key)` → None 이면 generic 카피 tuple 반환 (`"이 부분은 AI 분석 결과예요."`, `"강사와 함께 영상을 한 번 더 확인해 보세요."`) + `logging.warning(...)` (Phase 11 LLM 진입 전 graceful).

**FORBIDDEN_PHRASES tuple 박제 (신규 패턴):**
- Phase 7 신규 모듈 상수 — `FORBIDDEN_PHRASES: tuple[str, ...]` (6 research §10.3) + `FORBIDDEN_PHRASES_SUNITY: tuple[str, ...]` (3 memory 박제). 모듈 export 로 단위 test 가 grep gate parametrize.

**Adapter notes:**
- `_COPY_TEMPLATES` 의 **value** = 한국어, **key tuple** = 영어 enum literal (CLAUDE.md Cross-cutting `한국어 user-facing 카피, 영어 식별자`).
- `_MODE_PREFIX` 의 한국어 string 도 grep gate 통과 필수 — 단위 test 가 `_COPY_TEMPLATES` + `_MODE_PREFIX` 양쪽 iterate.
- 신규 패키지 의존성 0 — stdlib `typing.Literal` + `from .skeleton import JOINT_LABEL_KO` 만.
- 모듈 import 시 1회 로드 (singleton 불요, stateless dict literal).
- 카피 안 이모지 금지 (CLAUDE.md §7) + `"박제"` 단어 금지 (memory `[[no-baekje-filler]]`) — grep gate backstop.

---

### `app/src/types/analysis.ts` (modified — TS contract)

**Analog:** self (Phase 6 박제 `BodyComparisonFinding` line 490-497, `BodyComparisonReport` line 536-550)

**TS interface 패턴** (`app/src/types/analysis.ts:490-497`):
```typescript
export interface BodyComparisonFinding {
  deficitCode: string;
  jointKey?: string | null;
  measuredValue: number;
  deductionScore: number;
  confidence: number;
  bodyTypeAdjusted: boolean;
}
```
→ Phase 7 4 신설 필드:
```typescript
/** 'body_type_allowed' = 체형 허용 차이, 'needs_adjustment' = 개선 필요, 'uncertain' = AI 확신 부족 */
category: 'body_type_allowed' | 'needs_adjustment' | 'uncertain';
/** v1 = 'hold' 단일 (D-07-C1). v2 에서 'entry'/'lock'/'transition'/'final_shape' 확장. */
phase?: string | null;
/** Korean canned interpretation — Phase 11 LLM 입력 source. */
bodyTypeInterpretation?: string | null;
/** Korean canned recommendation — Phase 11 LLM 입력 source. */
recommendation?: string | null;
```

**Report 확장** (`app/src/types/analysis.ts:536-550`):
```typescript
export interface BodyComparisonReport {
  comparisonType: ComparisonType;
  bodyNormalizationConfidence: number;
  ...
  usedReferenceFallback: boolean;
}
```
→ Phase 7 2 신설 필드 (non-optional `string[]` — frontend normalize() default `[]` 처리):
```typescript
/** body_type_allowed 분류 finding 의 카피 aggregate. */
doNotOverCorrect: string[];
/** needs_adjustment + uncertain 분류 finding 의 카피 aggregate. */
recommendedFocus: string[];
```

**Adapter notes:**
- TS `string | null` ↔ Python `str | None` 정합 (Phase 6 박제 패턴).
- JSDoc 주석에 `D-07-C1` / `Phase 11` 사양 인용 (CLAUDE.md Cross-cutting `§` shorthand 정합).
- `bodyTypeInterpretation` / `recommendation` 은 optional (per-finding 4 필드는 fallback 후방향 호환).
- `doNotOverCorrect` / `recommendedFocus` 는 **non-optional** — Phase 7 백엔드가 항상 산출 (빈 list `[]` 가능).

---

### `docs/contract.md` §8 + §8.1 (modified — docs contract lockstep)

**Analog:** self (Phase 6 `docs/contract.md §8` line 376-481, line 407 BodyComparisonFinding 표, line 445 BodyComparisonReport 표)

**Phase 6 박제 패턴:**
- `### §8` heading + `### BodyComparisonFinding (R9 fix: ...)` 서브섹션
- 필드 표 (필드명 + 타입 + 설명) — TS/Python field map 1:1
- `### §8.1 IPSF divergence note (C14 fix)` 인용 — 박제 메모 직접 표시

→ Phase 7 갱신: BodyComparisonFinding 표에 4 행 추가 (`category` / `phase` / `bodyTypeInterpretation` / `recommendation`), BodyComparisonReport 표에 2 행 추가 (`doNotOverCorrect` / `recommendedFocus`). `### §8.3 Phase 7 분류 룰` 신규 서브섹션 추가 — D-07-A1/A2/U1 박제 + 21 canned + 3 mode prefix coverage 표.

**Adapter notes:**
- 단일 atomic commit (3-way lockstep) — `body_normalizer.py` + `analysis.ts` + `contract.md` 동시 갱신. Phase 6 commit `116f400` / `a444726` 패턴.
- 부분 commit 금지 (RESEARCH.md §"Pitfall 5").

---

### `backend/tests/phase07/__init__.py` + `conftest.py` (NEW — test bootstrap)

**Analog:** `backend/tests/phase06/__init__.py` (빈 파일) + `backend/tests/phase06/conftest.py:1-14`

**Excerpt** (`backend/tests/phase06/conftest.py`):
```python
"""Phase 6 단위 테스트 공통 helper. Validation Architecture 6 fixture 정합.
...
기존 backend/tests/conftest.py 가 parents[1]/shared/python 을 sys.path 에 자동 주입
하므로 본 파일은 별도 path 주입 X — Phase 6 fixture 디렉토리 경로 상수만 노출.
"""

from __future__ import annotations

from pathlib import Path

PHASE06_FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"
```
→ Phase 7 미러: `PHASE07_FIXTURES_DIR` 단일 상수, 동일 docstring 패턴.

**Adapter notes:**
- 별도 path 주입 X (`backend/tests/conftest.py` 가 자동 처리).
- pytest.ini collection 자동 (디렉토리 명 기반).

---

### `backend/tests/phase07/fixtures/_factory.py` (NEW — fixture loader)

**Analog:** `backend/tests/phase06/fixtures/_factory.py` (Phase 6 lines 1-96)

**Excerpt:**
```python
import json
from pathlib import Path
from typing import Any

_FIXTURE_DIR: Path = Path(__file__).resolve().parent

def load_fixture_raw(name: str) -> dict[str, Any]:
    if not name.endswith(".json"):
        name = f"{name}.json"
    path = _FIXTURE_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))
```
→ Phase 7: `load_fixture_raw()` 동일 재사용 + `load_finding_from_fixture(name)` 헬퍼 신규. 입력 fixture dict 의 `finding` 키를 `BodyComparisonFinding(**dict)` 로 dataclass 변환 (Phase 6 의 `pose_frame_from_dict` 미러 — 단순 JSON → dataclass 변환).

**Adapter notes:**
- Phase 6 `pose_frame_from_dict` 재사용 불요 (Phase 7 fixture 는 finding dict 만, PoseFrame 무관).
- 입력 JSON 스키마 — Phase 7 fixture 는 `{"finding": {...}, "context": {body_normalization_confidence, comparison_type, used_reference_fallback}, "expected": {category, ...}}` 단순 구조.

---

### `backend/tests/phase07/fixtures/*.json` × 7 (NEW — fixture data)

**Analog:** `backend/tests/phase06/fixtures/fixture_*.json` 6 fixture (포맷 단순화)

**Phase 7 fixture 7개** (RESEARCH.md §"Test Fixtures" 박제):
1. `fixture_classification_allowed.json` — `body_type_adjusted=True`, `deduction=-0.2`, `confidence=0.85` → expect `category='body_type_allowed'`
2. `fixture_classification_needs.json` — `body_type_adjusted=True`, `deduction=-0.5` (pose_reliability_low) → expect `category='needs_adjustment'`
3. `fixture_classification_uncertain_raw.json` — `body_type_adjusted=False` → expect `category='uncertain'`
4. `fixture_classification_uncertain_low_conf.json` — `finding.confidence=0.3` → expect `category='uncertain'`
5. `fixture_classification_uncertain_global_low.json` — `body_normalization_confidence=0.3` → expect 모든 `category='uncertain'`
6. `fixture_classification_mode3_first_fallback.json` — `comparison_type='mode3_first'`, `used_reference_fallback=True` → expect 모든 `category='uncertain'`
7. `fixture_canned_no_forbidden_full.json` — `_COPY_TEMPLATES + _MODE_PREFIX` 전체 iterate input (기대: 9 금지 표현 0 발견)

**Schema 예시** (`fixture_classification_allowed.json`):
```json
{
  "finding": {
    "deficit_code": "knee_toe_alignment",
    "joint_key": "left_knee",
    "measured_value": 12.5,
    "deduction_score": -0.2,
    "confidence": 0.85,
    "body_type_adjusted": true
  },
  "context": {
    "body_normalization_confidence": 0.85,
    "comparison_type": "mode1",
    "used_reference_fallback": false
  },
  "expected": {
    "category": "body_type_allowed",
    "phase": "hold",
    "do_not_over_correct_count": 1,
    "recommended_focus_count": 0
  }
}
```

**Adapter notes:**
- Phase 6 fixture 는 PoseFrame list (시계열 데이터, 영상 30-frame 합성) — Phase 7 fixture 는 단일 finding dict 정도로 90% 단순. fixture 1개 = 1 finding + context + expected.
- `fixture_canned_no_forbidden_full.json` 은 fixture data X — `copy_templates.py` 의 dict literal 직접 iterate (별도 JSON 불요, test 안에서 `_COPY_TEMPLATES.items()` 호출).

---

### `backend/tests/phase07/test_classify_findings.py` (NEW — classification rule unit test)

**Analog:** `backend/tests/phase06/test_body_normalizer_ipsf_deficit.py` (산식 단위 test 패턴)

**예상 test 8개** (RESEARCH.md §"Test Specifications" + Wave 0 Gaps 박제):

```python
def test_allowed_when_adjusted_and_small_deduction():
    """D-07-A1 — body_type_adjusted=True + |deduction|<=0.2 → body_type_allowed."""
    finding = BodyComparisonFinding(
        deficit_code="knee_toe_alignment",
        joint_key="left_knee", measured_value=12.5,
        deduction_score=-0.2, confidence=0.85, body_type_adjusted=True,
        category="body_type_allowed",  # placeholder — classify_findings 재할당
    )
    classified, dnoc, rec = classify_findings(
        [finding], body_normalization_confidence=0.85, comparison_type="mode1",
    )
    assert classified[0].category == "body_type_allowed"
    assert len(dnoc) == 1
    assert len(rec) == 0
```

→ 다른 7개:
- `test_needs_adjustment_when_large_deduction` (deduction=-0.5)
- `test_uncertain_when_raw_coords` (body_type_adjusted=False)
- `test_uncertain_when_finding_low_confidence` (confidence=0.3)
- `test_uncertain_when_report_low_confidence` (body_normalization_confidence=0.3 → 모든 finding demotion)
- `test_uncertain_when_mode3_first_fallback` (comparison_type='mode3_first', used_reference_fallback=True)
- `test_phase_default_hold` (모든 classified finding 의 `phase=='hold'`)
- `test_aggregate_lists_populated` (do_not_over_correct + recommended_focus 정확한 mapping)

**Adapter notes:**
- Phase 6 `test_body_normalizer_ipsf_deficit.py` 의 `np.array` keypoint 합성 패턴 불요 — Phase 7 test 는 BodyComparisonFinding dataclass 인스턴스 직접 합성.
- `dataclasses.replace()` 호출 grep test 추가 — 회귀 차단 (Pitfall 1).

---

### `backend/tests/phase07/test_copy_templates_no_forbidden.py` (NEW — grep gate)

**Analog:** 패턴 없음 (신규 grep gate 패턴). pytest parametrize 박제는 Phase 6 정합.

**Excerpt (RESEARCH.md §Code Examples Example 3 박제):**
```python
import pytest
from sunity_shared.analysis.copy_templates import (
    _COPY_TEMPLATES,
    _MODE_PREFIX,
    FORBIDDEN_PHRASES,
    FORBIDDEN_PHRASES_SUNITY,
)


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES + FORBIDDEN_PHRASES_SUNITY)
def test_canned_strings_have_no_forbidden_phrase(phrase: str) -> None:
    """research §10.3 6 금지 + Sunity 추가 3종 grep gate."""
    violations: list[str] = []
    for key, (interp, recom) in _COPY_TEMPLATES.items():
        if phrase in interp:
            violations.append(f"{key} interpretation: {interp!r}")
        if phrase in recom:
            violations.append(f"{key} recommendation: {recom!r}")
    for mode, prefix in _MODE_PREFIX.items():
        if phrase in prefix:
            violations.append(f"_MODE_PREFIX[{mode!r}]: {prefix!r}")

    assert not violations, (
        f"금지 표현 {phrase!r} 가 canned string 에서 발견됨:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
```

**Adapter notes:**
- 9 금지 표현 (6 research + 3 Sunity) parametrize → 9 test case 자동 생성. CI failure 메시지 = `{phrase!r} 가 X 위치에서 발견됨`.
- scope = `copy_templates._COPY_TEMPLATES + _MODE_PREFIX` 만 (RESEARCH.md §Pitfall 6 — Phase 11/13 캔드 별도 grep 룰).
- "감점" 같은 generic 단어 false positive 가능 — Phase 7 모듈 한정 + belle plan-review 보강 (Pitfall 4).

---

### `backend/tests/phase07/test_copy_templates_render.py` (NEW — render lookup test)

**Analog:** `backend/tests/phase06/test_body_normalizer_ipsf_deficit.py` (단순 함수 호출 + assert)

**예상 test 패턴:**
- 21 카피 매핑 coverage test (RESEARCH.md §"Canned String Coverage Audit" 표 21 항)
- 3 mode prefix prepend test (mode1 → "정은지 선수 영상 기준으로 보면 ...", mode3_first → "세계 심사 기준 ...", mode3_progress → "이전 영상 대비 ...")
- fallback test (키 미발견 시 generic tuple + WARNING log capture via `caplog`)
- `body_type_interpretation` 은 mode 무관 검증 (3 mode 호출 시 interp 동일)
- `recommendation` 만 prefix 다름 검증

**Adapter notes:**
- `_COPY_TEMPLATES.keys()` 전체 iterate parametrize — 21 카피 모두 정상 lookup. Phase 6 fixture 패턴 정합.

---

### `backend/tests/phase07/test_body_comparison_report_phase7_lockstep.py` (NEW — TS/Python/contract 3-way grep)

**Analog:** `backend/tests/phase06/test_body_comparison_report_lockstep.py` (TS/Python/contract.md 3-way regex grep)

**Excerpt** (`backend/tests/phase06/test_body_comparison_report_lockstep.py:1-50`):
```python
"""Task 5: 3-way contract lockstep — TS + Python + docs/contract.md §8/§8.2 drift defense.

CLAUDE.md Cross-cutting 룰: BodyComparisonReport / BodyComparisonSourcePose 변경 시
세 곳 동시 갱신 — 본 테스트가 drift 를 방어.
"""

from __future__ import annotations

import re
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_PATH = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_PY_MODELS_PATH = (
    _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared" / "models.py"
)
_PY_BODY_NORMALIZER_PATH = (
    _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared" / "analysis" / "body_normalizer.py"
)
_CONTRACT_PATH = _REPO_ROOT / "docs" / "contract.md"


# BodyComparisonReport 9 필드 — TS camelCase ↔ Python snake_case.
_FIELD_MAP = {
    "comparisonType": "comparison_type",
    "bodyNormalizationConfidence": "body_normalization_confidence",
    ...
    "usedReferenceFallback": "used_reference_fallback",  # W1
}
```

→ Phase 7 미러: `_FIELD_MAP` 에 4+2 신설 필드 추가 (BodyComparisonFinding 4 + BodyComparisonReport 2):
```python
# Phase 7 신설 (BodyComparisonFinding)
"category": "category",
"phase": "phase",
"bodyTypeInterpretation": "body_type_interpretation",
"recommendation": "recommendation",
# Phase 7 신설 (BodyComparisonReport)
"doNotOverCorrect": "do_not_over_correct",
"recommendedFocus": "recommended_focus",
```
→ 각 필드를 TS regex grep + Python regex grep + contract.md grep 3 곳 검증.

**Adapter notes:**
- Phase 6 패턴 그대로 — regex pattern 만 신설 6 필드 추가.
- `assert TS field 발견 AND Python field 발견 AND contract field 발견` 3 way fail-fast.

---

### `backend/tests/phase07/test_compare_body_profiles_phase7_integration.py` (NEW — integration)

**Analog:** `backend/tests/phase06/test_compare_body_profiles.py`

**패턴:**
- `compare_body_profiles()` 호출 후 결과 `BodyComparisonReport.findings[*].category` 모두 valid enum 검증
- `BodyComparisonReport.do_not_over_correct` + `recommended_focus` 두 list 가 populated (또는 빈 list[] 정상)
- Phase 6 fixture (`fixture_160cm_pro_vs_140cm_student.json`) 재사용 + Phase 7 신설 필드 자동 산출 검증

**Adapter notes:**
- Phase 6 fixture 100% 재사용 — 신규 fixture 불요. `compare_body_profiles()` 출력의 신설 필드 검증만 추가.
- Pipeline wiring 변경 없음 — `compare_body_profiles` 안에서 `classify_findings` 자동 호출 (RESEARCH.md §Architecture Patterns 박제).

---

### `backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py` (NEW — auto-conversion)

**Analog:** `backend/tests/phase06/test_dataclass_to_camel_case_dict.py` (5-case helper 자동 변환 단위 test)

**Excerpt** (Phase 6 test 패턴):
```python
def _app():
    import importlib
    sys.modules.pop("app", None)
    import app  # noqa: WPS433
    return importlib.reload(app)


def test_dataclass_to_camel_case_dict_recurses_nested_dataclass():
    """Test 7 (C8 Case 2) — 중첩 dataclass 변환."""
    app = _app()
    from sunity_shared.analysis.body_normalizer import (
        BodyComparisonReport, ScaleProfile,
    )
    bcr = BodyComparisonReport(...)
```

→ Phase 7 미러 (RESEARCH.md §Code Examples Example 4 박제):
```python
def test_phase7_new_fields_camel_case_automatic() -> None:
    """Phase 6 _dataclass_to_camel_case_dict 가 신설 4+2 필드 자동 변환."""
    from backend.functions.pipeline.app import _dataclass_to_camel_case_dict

    finding = BodyComparisonFinding(
        deficit_code="knee_toe_alignment",
        joint_key="left_knee", measured_value=120.0,
        deduction_score=-0.2, confidence=0.85, body_type_adjusted=True,
        category="body_type_allowed",
        phase="hold",
        body_type_interpretation="다리 길이 비율 차이로...",
        recommendation="정은지 선수 영상 기준으로 보면 지금 자세는...",
    )
    report = BodyComparisonReport(
        comparison_type="mode1",
        body_normalization_confidence=0.85,
        findings=[finding],
        do_not_over_correct=["정은지 선수 영상 기준으로..."],
        recommended_focus=[],
    )
    out = _dataclass_to_camel_case_dict(report)

    assert "doNotOverCorrect" in out
    assert "recommendedFocus" in out
    assert out["findings"][0]["category"] == "body_type_allowed"
    assert out["findings"][0]["phase"] == "hold"
    assert out["findings"][0]["bodyTypeInterpretation"]
    assert out["findings"][0]["recommendation"]
```

**Adapter notes:**
- Phase 6 C8 `_dataclass_to_camel_case_dict` 5-case helper (`backend/functions/pipeline/app.py:597-617`) 자동 변환 보장 — 신설 필드 코드 변경 0. Phase 7 test 는 회귀 차단만.
- `_snake_to_camel("do_not_over_correct") → "doNotOverCorrect"` 검증 (4 단어 변환 패턴 — 기존 5-case helper 가 처리).

---

## Shared Patterns

### Pattern A: Frozen dataclass + `__post_init__` Literal validator
**Source:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py:787-820` + `:826-895`
**Apply to:** `BodyComparisonFinding` 확장 (category enum 검증), `BodyComparisonReport` 확장 (defaults `list[str] = field(default_factory=list)`)

```python
@dataclass(frozen=True)
class X:
    field1: Literal["a", "b", "c"]
    field2: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.field1 not in ("a", "b", "c"):
            raise ValueError(f"field1 must be one of (a, b, c), got {self.field1!r}")
```

### Pattern B: Pure function 산식 (numpy / boto3 / network 무관)
**Source:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py:901-1112` (measure_ipsf_absolute_deficits)
**Apply to:** `classify_findings()` 신규 — keyword-only args, return tuple.

```python
def classify_findings(
    findings: list[BodyComparisonFinding],
    body_normalization_confidence: float,
    comparison_type: ComparisonType,
    *,
    used_reference_fallback: bool = False,
) -> tuple[list[BodyComparisonFinding], list[str], list[str]]:
    """Pure function — numpy 무관, network 무관, LLM 무관. 단위 test 가능."""
    ...
```

### Pattern C: 3-way atomic lockstep commit (TS + Python + contract.md)
**Source:** `backend/tests/phase06/test_body_comparison_report_lockstep.py` (Phase 6 commit `116f400`, `a444726` 패턴)
**Apply to:** Phase 7 schema 확장 — 단일 commit (body_normalizer.py + analysis.ts + contract.md §8 동시).

### Pattern D: 5-case camelCase 자동 변환
**Source:** `backend/functions/pipeline/app.py:597-617` (`_dataclass_to_camel_case_dict`)
**Apply to:** 신설 4+2 필드 모두 자동 변환 (코드 변경 0). 회귀 차단 단위 test 만 추가.

```python
def _dataclass_to_camel_case_dict(obj):
    """C8 fix 5 case 명시. dataclass / list / dict / Enum / scalar."""
    if obj is None:
        return None
    if dataclasses.is_dataclass(obj):
        raw = dataclasses.asdict(obj)
        return {_snake_to_camel(k): _dataclass_to_camel_case_dict(v) for k, v in raw.items()}
    if isinstance(obj, Enum):
        return str(obj.value)
    if isinstance(obj, list):
        return [_dataclass_to_camel_case_dict(x) for x in obj]
    ...
```

### Pattern E: `from __future__ import annotations` + 모듈 docstring 사양 인용
**Source:** `backend/shared/python/sunity_shared/analysis/assemble.py:1-12`
**Apply to:** `copy_templates.py` 신규 모듈 — module docstring 에 `research §10.1` / `§10.3` / `[[memory]]` 인용.

### Pattern F: pytest parametrize over module-level tuple
**Source:** (신규) — Phase 6 도 pytest parametrize 사용하나 grep gate 패턴은 신규
**Apply to:** `test_copy_templates_no_forbidden.py` — `FORBIDDEN_PHRASES + FORBIDDEN_PHRASES_SUNITY` tuple 그대로 parametrize, 9 case 자동 생성.

### Pattern G: Phase06 test 디렉토리 구조 정합
**Source:** `backend/tests/phase06/{__init__.py, conftest.py, fixtures/_factory.py, test_*.py}`
**Apply to:** `backend/tests/phase07/` 동일 구조 — `PHASE07_FIXTURES_DIR` 상수 노출, `load_fixture_raw()` 헬퍼 재정의.

### Pattern H: 한국어 user-facing canned + 영어 식별자 dict literal
**Source:** `backend/shared/python/sunity_shared/analysis/assemble.py:25-40` (`_DIMENSION_BASELINES_MODE1`/`_GOOD_COPY_BY_DIM`) + `backend/shared/python/sunity_shared/analysis/skeleton.py:53-62` (`JOINT_LABEL_KO`)
**Apply to:** `copy_templates._COPY_TEMPLATES` dict literal — tuple key 영어 enum, tuple value 한국어 (interp, recom).

## No Analog Found

본 phase 모든 신규 파일이 Phase 6 박제 패턴 + Phase 12.5 박제 패턴 100% 재사용. **분류 룰 + 캔드 카피 매핑 자체** 가 신규 도메인이지만 (Phase 7 = 도메인 신설), **구현 패턴은 100% 기존 코드 박제**.

| File | Reason for partial match |
|------|--------------------------|
| `test_copy_templates_no_forbidden.py` | pytest parametrize grep gate 패턴은 신규 (Phase 6 에 grep gate test 없음). 단, parametrize over module tuple 자체는 표준 pytest 패턴. |
| `copy_templates.py` | canned string 매핑 dict literal 자체는 신규 (Phase 6 dict literal 은 산식 상수만). 단, 패턴 (mode-aware baseline + Korean canned + JOINT_LABEL_KO 활용) 은 `assemble.py` + `skeleton.py` 직접 재사용. |

## Metadata

**Analog search scope:**
- `backend/shared/python/sunity_shared/analysis/` (body_normalizer / assemble / skeleton / dimensions / kismam)
- `backend/functions/pipeline/app.py` (`_dataclass_to_camel_case_dict`)
- `backend/shared/python/sunity_shared/firestore_admin.py` (`_validate_flat_dict_no_nested_array`)
- `backend/tests/phase06/` (test 패턴 7 파일)
- `app/src/types/analysis.ts` (TS interface)
- `docs/contract.md §8` (Phase 6 박제)

**Files scanned:** 13 (모두 핵심 analog) + Phase 6 RESEARCH/CONTEXT
**Pattern extraction date:** 2026-06-08

## PATTERN MAPPING COMPLETE

**Phase:** 7 - 차이 분류 (Difference Classification)
**Files classified:** 13
**Analogs found:** 13 / 13

### Coverage
- Files with exact analog: 11
- Files with role-match analog: 2 (`copy_templates.py` partial — mode-aware baseline + JOINT_LABEL_KO 활용 / `test_copy_templates_no_forbidden.py` partial — parametrize gate 신규)
- Files with no analog: 0

### Key Patterns Identified
- Phase 6 박제 100% 재사용 — frozen dataclass + `__post_init__` Literal validator + 3-way lockstep + 5-case camelCase + pytest fixture loader 패턴
- canned string dict literal — `assemble.py:25-40` (`_DIMENSION_BASELINES_MODE1`/`_GOOD_COPY_BY_DIM`) 박제, mode-aware tuple-key + Korean value
- pytest parametrize grep gate — `FORBIDDEN_PHRASES + FORBIDDEN_PHRASES_SUNITY` tuple iterate, CI failure 시 위치 정확히 지목
- `_dataclass_to_camel_case_dict` 자동 변환 — 신설 4+2 필드 모두 코드 변경 0, 회귀 차단 test 만 추가
- 한국어 카피 source — `skeleton.JOINT_LABEL_KO` 8 관절 라벨 직접 import 재사용

### File Created
`/Users/kimtaesung/Dev/SunityMotion/.planning/phases/07-difference-classification/07-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files. 모든 신규 코드의 패턴 source 가 Phase 6/12.5 박제 코드에 명확히 매핑 — 신규 인프라 0, 신규 의존성 0.
