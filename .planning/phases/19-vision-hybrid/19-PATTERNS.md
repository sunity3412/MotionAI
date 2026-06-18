# Phase 19: 분석 점수 신뢰도 재설계 (vision-hybrid) - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 11 (수정 8 / 신규 3 테스트)
**Analogs found:** 11 / 11 (전부 in-repo — 신규 인프라 없음, 기존 모듈 수정/모방)

> 핵심: 본 phase는 **새 모듈 생성이 아니라 기존 순수함수의 집계 철학 교체**다. 거의 모든
> "analog"은 **수정 대상 파일 자기 자신** — 같은 파일 안 기존 함수의 docstring/네이밍/에러
> 처리/순수함수 스타일을 그대로 따라 신함수를 추가하거나 본문을 교체한다. 신규 테스트만 진짜
> "다른 파일 모방"이다.

---

## File Classification

| 수정/신규 파일 | Role | Data Flow | Closest Analog | Match Quality |
|----------------|------|-----------|----------------|---------------|
| `backend/.../analysis/kismam.py` | service (scoring core, pure) | transform | 자기 자신 (`overall_score`/`score_from_deviation`) | exact (in-place) |
| `backend/.../analysis/dimensions.py` | service (scoring core, pure) | transform | 자기 자신 (`line_score`/`overall_from_dimensions`) | exact (in-place) |
| `backend/functions/pipeline/app.py` | controller (SQS consumer, orchestration) | event-driven / request-response | 자기 자신 (MODE_EXPERT 분기, `_mode3_comparison`) | exact (in-place) |
| `backend/.../analysis/assemble.py` | service (result/copy 조립, pure) | transform | 자기 자신 (`build_mode3`/`build_dimension_explanation`) | exact (in-place) |
| `app/src/lib/joints.ts` | utility (reshape, pure) | transform | 자기 자신 (`reshapePose3dData`) | exact (in-place) |
| `app/src/components/PoseViewer3D.tsx` | component | transform/render | 자기 자신 (Canvas camera/scale) | exact (TRUST-04 선택지 C만) |
| `app/src/app/analysis/result.tsx` | component (screen) | request-response | 자기 자신 (joints3d 빌드 628-640) | exact (in-place) |
| `app/src/types/analysis.ts` | config (contract) | — | 자기 자신 (`AnalysisResult`/`dimensionScores`) | exact (in-place) |
| `backend/.../sunity_shared/models.py` | config (contract mirror) | — | 자기 자신 (`DIM_*`/`SCORE_DIMENSIONS`) | exact (in-place) |
| `backend/tests/test_kismam.py` (신규 케이스) | test | transform | 자기 자신 (기존 케이스) | exact |
| `backend/tests/test_dimensions.py` (신규 케이스) | test | transform | 자기 자신 (기존 케이스) | exact |
| `backend/tests/test_pipeline_mode3.py` (신규 케이스) | test | event-driven | 자기 자신 (`_video`/`_as_prev` 픽스처) | exact |
| `backend/tests/test_anchor_known_answer.py` (신규 파일) | test (GPU-skip) | transform | `test_pipeline_mode3.py` 구조 | role-match |

---

## Pattern Assignments

### `backend/.../analysis/kismam.py` (service, transform) — SCORE-06 / TRUST-02

**Analog:** 자기 자신. `overall_score`(182-189)를 감점식으로 교체/병치, `score_from_deviation`(87-93)와
`assess`/`top_issues`는 재사용(교체 금지 — RESEARCH "Don't Hand-Roll").

**모듈 docstring 컨벤션** (1-11): 모듈 상단에 알고리즘 의도 + 점수 매핑 공식 + contract 인용
(`contract.md §0`). 신함수도 이 스타일 — **왜** 감점식인지 + IPSF 트랙 근거 인용.

**순수함수 + frozen dataclass value object** (96-111): `JointAssessment` = `@dataclass(frozen=True)`,
`from __future__ import annotations`. numpy 입력은 `np.asarray(dtype=float)` + shape 검증 후 `ValueError`.

**교체 대상 — 현재 평균(희석)** (182-189):
```python
def overall_score(assessments, weight=None) -> int:
    """가중 평균 종합 점수 0~100 (KISMAM)."""
    w = {**DEFAULT_WEIGHT, **(weight or {})}
    num = sum(a.score * w[a.key] for a in assessments)
    den = sum(w[a.key] for a in assessments)
    return int(round(num / den)) if den else 0  # ← 평균이 결함 희석 (94점 원인)
```
**신함수 모방 형식** (RESEARCH Code Examples §감점식, 19-IPSF-DEDUCTION-NOTES §A 트랙2):
100에서 시작 → 관절별 `max(0, dev_i − tol)` 누적 감점. clamp `max(0, min(100, ...))` 는 기존
`score_from_deviation`(93)과 동일 박제. 감점계수는 **IPSF 근거에서만** (보유 sweep 재calibrate 금지 — D-05 경계).

**COACHING_FOCUS 어깨 라벨 정정** (53-62): 현재 `"left_shoulder": "안정성"`. TRUST-02 = 어깨는
STATIC POSE ANGLE이지 stability(떨림)가 아니므로 '안정성' 라벨 오인 제거. **주의** (50-52 주석):
`JOINT_LABEL_KO`에 이미 부위 한글("오른쪽 어깨")이 있어 FOCUS 값에 부위 키워드 중복 금지.

---

### `backend/.../analysis/dimensions.py` (service, transform) — SCORE-07 / TRUST-02

**Analog:** 자기 자신. `line_score`(226-245)에 micro-bent 0점 트랙 분기 추가, `overall_from_dimensions`(348-351)
감점식+stability 분리로 교체.

**기술 조건부 신전 — 기존 가드 재사용** (238-242): `profile.expects_extension(k)` 필터가 이미 있다.
SCORE-07 0점 트랙은 **이 필터 안에서만** 적용 (Pitfall 4: 의도적 굽힘 위양성 차단).
```python
deficits = [
    max(0.0, _FULL_EXTENSION_DEG - float(rep[JOINT_KEYS.index(k)]))
    for k in JOINT_KEYS
    if profile.expects_extension(k) and not np.isnan(rep[JOINT_KEYS.index(k)])
]
```
**신 0점 트랙 형식** (RESEARCH Code Examples §micro-bent): `extend_joints` 루프에서 `rep_angle < 160.0`
이면 `return 0` (요소 무효, 비례감점 아님). 임계 상수는 기존 `_LINE_TOL_DEG`/`_STABILITY_TOL_DEG`(158-160)
처럼 모듈 상수 + IPSF 근거 인용 주석으로 박제. 160° = 180° − 20° tol ([CITED: 19-IPSF-DEDUCTION-NOTES §A]).

**교체 대상 — 현재 단순평균** (348-351):
```python
def overall_from_dimensions(dimension_scores) -> int:
    """차원 점수 평균 = 종합 점수. 빈 dict 면 0."""
    vals = list(dimension_scores.values())
    return int(round(sum(vals) / len(vals))) if vals else 0  # ← stability 인플레
```
**신 형식** (RESEARCH §종합 stability 분리): `DIM_ANGLE`/`DIM_LINE`만 종합 입력, `DIM_STABILITY`는
표시만. `min(core)` 또는 감점합 (Claude's Discretion — 권장: angle은 감점합, 종합은 min-of-core).
**Pitfall 2**: `dimension_scores` 키/순서는 보존 — `overall_from_dimensions` 입력만 변경. Mode3 delta는
절대차원 유지.

**공유 window helper 재사용** (270-289): `_select_window` = line/stability/deficit source 단일 진입.
신함수가 별도 window 계산 금지 (Codex v3 HIGH-2 drift 방지 — RESEARCH "Don't Hand-Roll").

---

### `backend/functions/pipeline/app.py` (controller, event-driven) — TRUST-01 / TRUST-03 / TRUST-04(저장부) / TRUST-05

**Analog:** 자기 자신. MODE_EXPERT 분기(1740-1838), MODE_SELF 분기(1839-1847), `_angles_to_mean_dict`(1515-1538),
`_mode3_comparison`(1572-1629), joints3d 저장(2318-2342).

**TRUST-01 표시-점수 정합** — 비대칭 근본원인 (1800-1801):
```python
user_mean_mode1 = _angles_to_mean_dict(user_seg, skeleton.JOINT_KEYS)  # matched sub-window
ref_mean_mode1 = _angles_to_mean_dict(a_ref, skeleton.JOINT_KEYS)      # ← 전체 ref clip (비대칭!)
```
`_angles_to_mean_dict`(1515-1538)는 whole-clip `np.nanmean` — 점수가 쓰는 `per_joint_deviation`(median)와
불일치. `_deviation_against`(1557-1569)가 이미 `match.path`/`user_seg`/`a_ref`를 반환하므로 **DTW path-정렬
동일 구간의 median**으로 교체. `per_joint_deviation`(motiondtw)가 하는 방식 재사용. `_mode3_comparison`의
`ref_mean = _angles_to_mean_dict(prev_seg, ...)`(1609)도 동일 수정. **순수성 유지** — numpy만, AWS 무관.

**TRUST-03 Mode3 게이트** — not_pole은 MODE_EXPERT 전용 (1812):
```python
if angle_dim < models.NOT_POLE_SIMILARITY_THRESHOLD:   # MODE_EXPERT 안에만 있음
    raise NotPoleMotionError(...)
```
MODE_SELF 분기(1839-1847)에는 게이트 없음 → 어떤 영상도 97점. TRUST-03 = `_mode3_comparison`(또는
MODE_SELF 진입부)에 `assemble.lookup_motion_branch(motion_id)` 연결 → 미보유(`_SAFE_DEFAULT_BRANCH`)면
"기준 동작 없음 — 절대 자세 기준 평가" 근거 플래그 + 절대트랙 채점. **fail-closed/raise 금지** —
`_SAFE_DEFAULT_BRANCH`(68-77, copyBranch=branch2)는 의도적으로 점수를 주되 근거 명시
([[motion-routing-generalize-principle]]).

**MODE_SELF prev 함정 가드 유지** (1842-1843): `get_previous_analysis(uid, analysis_id, mode=models.MODE_SELF)`
— 같은 mode만 검색 (2026-06-07 belle fix, Pitfall 5). 변경 금지.

**TRUST-04 저장부 (선택지 A — 비권장)** (2327-2342): 현재 raw 픽셀 flat 저장 (`pole_aligned`, recenter/rescale
없음). RESEARCH 권장은 선택지 B(joints.ts) — 저장부 불변, 과거 doc 호환. 만약 A 선택 시 `space` enum 변경 →
3중 계약 동기화. nan 처리 패턴 (2331-2332): `np.nan_to_num(src, nan=0.0, posinf=0.0, neginf=0.0)`.

**TRUST-05 v2 hook (비-차단)** (RESEARCH Code Examples §v2 hook): 감점식 점수 산출 직후 pass-through
`_apply_vision_veto(score_result, ...)` 자리만 — v1은 identity. 기존 adapter lazy-import 패턴
(`_ensure_adapters()`) 모방, `_gemini_vision_enabled()` OFF 시 입력 그대로 반환.

**에러 처리 컨벤션** (2312-2316, 2338-2342): 분석 흐름 차단 0 박제 — `except Exception: # noqa: BLE001`
+ `log.exception(...)` + graceful skip. 신 hook도 동일.

---

### `backend/.../analysis/assemble.py` (service, transform) — TRUST-03 근거 카피

**Analog:** 자기 자신. `build_mode3`(539-562), `build_dimension_explanation`(190-266), `lookup_motion_branch`(91-113).

**copyBranch 라우팅 재사용 — 새 boolean 금지** (91-113, RESEARCH "Don't Hand-Roll"): `lookup_motion_branch`
→ `MotionBranchInfo`(frozen dataclass, 39-53). 채점 미진입 주석(33-37) — TRUST-03이 이를 **게이트/근거 카피**로
확장. `_SAFE_DEFAULT_BRANCH`(68-77) = 미지 동작 안전 기본.

**baseline 카피 분기 형식** (140-187): `_DIMENSION_BASELINES_BRANCH1/2` 상수 dict + `_baselines_for_branch`.
근거 카피 ("기준 동작 없음 — 절대 자세 기준 평가") 도 이 형식으로 상수화. **금지 문구 가드**
(151-158): `BRANCH2_FORBIDDEN_PHRASES` = ("세계 심사 기준","IPSF","180°","180도") — branch2 카피에 "89% 일치"
같은 거짓 프레이밍 금지 가드를 같은 패턴으로 추가 가능.

**weightPercent 합 100 — 직접 반올림 금지** (161-171): `_largest_remainder_pct` 재사용 (33×3=99 버그 방지).

**build_mode3 progress 정신** (539-562): "% 일치" 헤드라인 금지, deltaFromPrevious는 절대차원만
([[mode3-progress-not-similarity]]). 근거 필드 추가 시 이 dict에 키 추가 (옵셔널).

---

### `app/src/lib/joints.ts` (utility, transform) — TRUST-04 (권장 선택지 B)

**Analog:** 자기 자신. `reshapePose3dData`(24-57).

**graceful null 정책 + length guard** (12-13, 29-41): 형식 불일치/누락/길이 mismatch → throw 대신 null.
`Array.isArray` + `flat.length !== T * J * 3` 가드. 신 normalize도 같은 graceful — torso=0 / hip 누락 시
fallback (0-div 가드, RESEARCH Security V5 + A4).

**Firestore flat 제약 주석** (4-11): nested-array 금지로 flat 저장 → 읽는 쪽 reshape. 정규화를 이
reshape 단계에 추가하는 것이 "자연스러움" (RESEARCH Pattern 4). 박제 정신 인용 컨벤션 유지.

**구현** (RESEARCH Pattern 4): 각 frame의 hip midpoint `(left_hip+right_hip)/2` 빼기(recenter) +
torso length `shoulder_mid↔hip_mid` 거리로 나누기(normalize) → origin-centered, viewer frustum(distance 3,
fov 50) 안. JointKeys로 hip/shoulder 인덱스 lookup. **앱 JS 테스트 러너 없음** (CLAUDE.md) → 순수함수
수동/typecheck 검증 (RESEARCH Wave 0 Gaps).

---

### `app/src/components/PoseViewer3D.tsx` (component, render) — TRUST-04 (선택지 C, 비권장)

**Analog:** 자기 자신. Canvas camera (345-356), sphere/bone 렌더 (157-168), CAMERA_PRESETS (52-54).

**현재 정규화 기대값** (RESEARCH Pattern 4 근본원인): camera `position [0,0,3]`, `fov: 50`,
`sphereGeometry args={[0.04, ...]}` — **origin-centered normalized** 좌표 기대. raw 픽셀(중심 ~320,240)이
frustum 밖. RESEARCH는 선택지 B(joints.ts) 권장 — viewer 불변. C 선택 시 per-frame hip 중심이 달라
단일 `<group>` transform 부족.

**ErrorBoundary 패턴** (24-29, 76-98): GL 컨텍스트 실패 시 route 전체 안 죽게 class ErrorBoundary.
좌표 변경이 NaN/crash 유발 안 하게 (Security DoS) joints.ts에서 finite 처리.

---

### `app/src/app/analysis/result.tsx` (screen) — TRUST-04 빌드부 / TRUST-03 근거 표시

**Analog:** 자기 자신 (628-640 joints3d 빌드 — `reshapePose3dData` 호출부). 근거 카피 표시는
기존 `dimensionExplanation` 렌더 패턴 모방.

**소비 흐름:** `result.joints3d/joints3dKeys/joints3dFrames` → `reshapePose3dData` → `PoseViewer3D`.
TRUST-04 선택지 B면 result.tsx 변경 불필요 (joints.ts가 정규화 흡수). TRUST-03 근거 헤드라인은
`comparison`/`dimensionExplanation`에서 읽어 표시.

---

### 3중 계약: `analysis.ts` ↔ `models.py` ↔ `docs/contract.md` (config)

**Analog:** 자기 자신. TS `AnalysisResult`/`dimensionScores` (317-374), Python `DIM_*`/`SCORE_DIMENSIONS` (14-23).

**동기화 규칙 (Anti-Pattern: 한쪽만 수정 금지):**
- TS (322): `dimensionScores: Partial<Record<ScoreDimension, number>>` — 차원 추가/근거 필드 시 옵셔널 선언
  (이전 빌드 doc 호환 — `dimensionExplanation?` 패턴 324-325).
- Python (17-23): `DIM_ANGLE/LINE/STABILITY`, `SCORE_DIMENSIONS`, `ABSOLUTE_DIMENSIONS` — TS와 1:1.
- `joints3d`/`space` (369-373 TS): TRUST-04 선택지 B면 schema 불변. A면 `space` enum 동기화.
- **schema 변경 시** EAS 재빌드 + `sam build --use-container` 재배포 (RESEARCH Runtime State).
- **집계식만 교체(schema 미변경) 시** 3중 계약 불변 — 과거 doc 그대로 읽힘 (점수 필드 동일).

---

### 신규 테스트 (test)

**Analog:** `backend/tests/test_kismam.py`, `test_dimensions.py`, `test_pipeline_mode3.py` (기존 케이스).

**test 컨벤션** (`test_dimensions.py` 16-30): 모듈 docstring "AWS 불필요" + 결정적 픽스처 헬퍼
(`_pose`/`_profile`/`_video`/`_as_prev`). `np.full`/`np.tile`/`rng = np.random.default_rng(seed)`로 합성 angles.
`TechniqueProfile(name, category, joint_expectations)` 명시 생성.

**단일 케이스 형식** (`test_kismam.py` 19-27, 39-46): `assert s0 > s1 > s2` 단조성, `pytest.approx`, 
worst-3 순서 검증. SCORE-06 신케이스:
- `test_single_major_fault_dominates` — 한 관절 큰 dev → 종합 급락 (평균 희석 안 됨)
- `test_clean_pose_high_score` — 모든 dev<tol → 종합 high (위양성 0)
- `test_stability_does_not_inflate` — stability 높아도 angle/line 낮으면 종합 낮음
- `test_micro_bent_zero_track` / `test_intentional_bend_not_penalized` — expects_extension 필터

**신규 파일 `test_anchor_known_answer.py`** (analog = `test_pipeline_mode3.py` sys.path 부트스트랩 1-21):
GPU skip marker (`@pytest.mark.skipif`) — D-05 6 앵커 **방향 판정**(fault<correct), 점수 수치 타깃 아님
([[calibration-source-hard-gate]]). Pre-existing 실패 격리 (RESEARCH Wave 0): test_pole_detector 등 본 phase
무관 — 회귀 판정 제외.

---

## Shared Patterns

### 순수함수 + frozen dataclass value object
**Source:** `kismam.py:96-111` (`JointAssessment`), `dimensions.py:39-57` (`AxisFrame`), `assemble.py:39-53` (`MotionBranchInfo`)
**Apply to:** 모든 ML core 변경 (kismam/dimensions/assemble)
```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class JointAssessment:
    key: str
    score: int          # 0~100
    deviation_deg: float
```
모든 모듈 상단 `from __future__ import annotations`. numpy 입력은 `_as_tj`/`np.asarray(dtype=float)` +
shape 검증 후 `ValueError` (`dimensions.py:165-169`, `kismam.py:132-134`). 이모지 금지, snake_case.

### 모듈 docstring = 왜 + 도메인 인용
**Source:** `kismam.py:1-11`, `dimensions.py:1-19`, `assemble.py:1-10`
**Apply to:** 모든 수정/신규 백엔드 모듈
한국어 block 주석 상단 — 알고리즘 의도 + 공식 + spec 인용 (`contract.md §0`, `보고서 5·6`,
`19-IPSF-DEDUCTION-NOTES §A`). 재교정 시 dated 주석 (`dimensions.py:158-160` "2026-06-12 belle 결정").

### 점수 clamp 박제
**Source:** `kismam.py:93`, `assemble.py:614`
**Apply to:** 모든 점수 산출 함수
```python
return max(0, min(100, int(round(...))))   # 0~100 정수 (contract.md §0)
```

### graceful 에러 boundary (흐름 차단 0)
**Source:** `pipeline/app.py:2312-2316, 2338-2342`, `joints.ts:12-13, 29-41`
**Apply to:** pipeline wiring (신 hook 포함), 앱 reshape/normalize
백엔드: `except Exception: # noqa: BLE001` + `log.exception(...)` + graceful skip (None). 앱: throw 대신
null + 0-div/finite 가드.

### Firestore flat 저장 (nested-array 금지)
**Source:** `joints.ts:4-11`, `pipeline/app.py:2344-2350` (`angles`+`anglesJointKeys`+`anglesFrames`)
**Apply to:** joints3d 정규화 (읽는 쪽 reshape), 차원 schema 변경
`(T, J)` 행렬은 flat + Frames + JointKeys 메타. 읽는 쪽 reshape. 정규화는 reshape 단계에 흡수(선택지 B).

### 공유 window / source helper (drift 방지)
**Source:** `dimensions.py:270-289` (`_select_window`)
**Apply to:** line/stability/deficit/표시값 — 별도 window 계산 금지
점수 산식과 표시/deficit이 **같은 frames**를 보게 단일 helper (Codex v3 HIGH-2).

---

## No Analog Found

없음 — 본 phase는 신규 인프라 0, 전부 in-repo 기존 모듈 수정/모방. v2 비전 거부권(`_apply_vision_veto`)
본체는 deferred (v1은 pass-through hook 자리만 — 기존 Gemini 어댑터 lazy-import 패턴 재사용).

| (참고) v2 항목 | Role | Data Flow | 비고 |
|------|------|-----------|------|
| `_apply_vision_veto` 본체 | service (adapter) | request-response | v1 = identity pass-through. 본체는 Phase 18 검증 후. analog = `pipeline._ensure_adapters()` lazy-import |

---

## Metadata

**Analog search scope:** `backend/shared/python/sunity_shared/analysis/`, `backend/functions/pipeline/`,
`backend/tests/`, `app/src/lib/`, `app/src/components/`, `app/src/types/`, `backend/shared/.../models.py`
**Files scanned:** kismam.py, dimensions.py, pipeline/app.py(targeted), assemble.py, joints.ts,
PoseViewer3D.tsx(targeted), analysis.ts(targeted), models.py(targeted), test_kismam.py, test_dimensions.py,
test_pipeline_mode3.py
**Pattern extraction date:** 2026-06-18
**핵심 경계:** D-05 — 감점 임계는 IPSF 근거에서만, 보유 sweep 재calibrate 금지
([[calibration-source-hard-gate]] [[scoring-redesign-must-generalize-no-overfit]]).
