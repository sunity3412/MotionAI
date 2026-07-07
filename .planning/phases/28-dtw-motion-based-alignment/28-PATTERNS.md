# Phase 28: 동작 기반 비교 정렬 (DTW 워핑) - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** 10 (신규 3 / 수정 7)
**Analogs found:** 9 / 10 (앱측 playbackRate 제어만 코드베이스 무선례 — RESEARCH Pattern 3 사용)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/motion_alignment.py` [신규] | 순수 분석 모듈 | transform (MotionMatch→앵커/tier) | `analysis/vision_veto.py::assess_alignment_confidence` (:919-983) + `analysis/dimensions.py` 헤더 관례 | exact |
| `backend/shared/python/sunity_shared/analysis/fault_zoom.py` [수정, D-04] | 렌더/표시 모듈 | transform (frame 대응) | 자기 자신 (`_to_rep_idx` :177, `_matched_ref_frame` :250, 근사 폴백 :849-859, 3단 강하 :819-821) | exact (self) |
| `backend/functions/pipeline/app.py` [수정] | 파이프라인 오케스트레이터 | batch (SQS consumer) | 자기 자신 (dtw 생산 :3305-3311, complete_analysis 호출 :4131-4153) + safetyFlags "result 안으로" 선례 | exact (self) |
| `backend/shared/python/sunity_shared/firestore_admin.py` [수정] | 영속화 + validator | CRUD (write) | `_validate_safety_flags` (:288-305) + `complete_analysis` scoped-validator 훅 (:904-916) | exact |
| `backend/tests/test_motion_alignment.py` [신규] | test | — | `backend/tests/test_dimensions.py` (순수 모듈 unit, AWS 무관) | exact |
| `app/src/lib/alignmentWarp.ts` [신규] | 순수 TS lib 모듈 | transform (보간/rate) | `app/src/lib/deductionLabels.ts` (:1-26) | exact |
| `app/src/components/VideoCompare.tsx` [수정] | component | streaming (player 제어 tick) | 자기 자신 (tick :280-350, seekBoth :424-442, 배지 :735-758, 상수 :156) | exact (self) |
| `app/src/app/analysis/result.tsx` [수정, D-05] | screen | request-response (Firestore 구독 소비) | 자기 자신 (조건부 배지/1줄 카피 :1104-1135, 재분석 CTA :1673-1679) | exact (self) |
| `app/src/types/analysis.ts` [수정] | 계약 (TS) | — | `FaultZoomComparison.region/tier` optional 필드 + lockstep 주석 (:443-459) | exact |
| `backend/shared/python/sunity_shared/models.py` + `docs/contract.md` [수정] | 계약 (Python/문서) | — | `DEDUCTION_RECORD_KEYS` 3-way lockstep 블록 (models.py:150-169) | exact |

## Pattern Assignments

### `analysis/motion_alignment.py` [신규] (순수 분석 모듈, transform)

**Analog 1 — 기능적 최근접:** `backend/shared/python/sunity_shared/analysis/vision_veto.py::assess_alignment_confidence`
같은 입력(MotionMatch)으로 신뢰도 3단 판정을 하는 프로덕션 순수 함수. **임계 상수도 여기서 재사용** (D-03, 자기 sweep 재보정 아님).

**임계 상수 + 출처 주석 관례** (vision_veto.py:908-916):
```python
# 채택 경로 enum: single | window_union | low_alignment_confidence.
# 임계는 generic 상수 — 특정 영상 튜닝 금지(D-06). DTW median(per_joint_deviation)은
# scoring 경로이므로 본 helper 와 섞지 않는다(D-10 HIGH-3).
_ALIGN_GLOBAL_T1 = 8.0     # 글로벌 distance 1차 임계 (초과 시 window_union 고려)
_ALIGN_GLOBAL_T2 = 25.0    # 글로벌 distance 2차 임계 (초과 시 low_alignment 후보)
```
→ motion_alignment.py 는 이 두 상수를 import(또는 값 재사용 + 출처 주석 "vision_veto H4 프로덕션 상수 재사용")하여 tier 사다리(warped ≤8.0 / trim_only ≤25.0 / disabled >25.0)를 가른다.

**MotionMatch 방어적 접근 패턴** (vision_veto.py:932-940 — getattr + 기본값, 예외 없이 graceful):
```python
    distance = float(getattr(match, "distance", 0.0) or 0.0)
    path = getattr(match, "path", None) or []
    start = int(getattr(match, "start", 0) or 0)
    local = selected_user_frame - start
    near = [j for (i, j) in path if abs(i - local) <= window]
```

**Analog 2 — 입력 계약:** `analysis/motiondtw.py:72-77` (frozen dataclass — path 인덱스 도메인 주의):
```python
@dataclass(frozen=True)
class MotionMatch:
    start: int          # 사용자 시퀀스 동작 구간 시작 (프레임)
    end: int            # 끝 (exclusive)
    distance: float     # 정규화 DTW 거리 (작을수록 유사)
    path: list          # [(user_idx, ref_idx)...] (구간 로컬 인덱스 기준)
```
distance 정규화 근거 = motiondtw.py:29 "정규화거리 = 누적비용/(n+m)".

**Analog 3 — 모듈 헤더/docstring 관례:** `analysis/dimensions.py:1-26` — 모듈 docstring 에 (a) 무엇을/왜, (b) 스펙 출처 인용, (c) 날짜 박힌 설계결정 이력. motion_alignment.py 헤더에는 최소: 28-CONTEXT D-01~D-03 인용, fps 도메인(user 9fps vs ref 18fps) 함정 명시, "순수 numpy, 채점 무접촉" 선언 (`from __future__ import annotations` 첫 줄 — 분석 패키지 전 모듈 공통).

**1:N median 안정화 선례** (fault_zoom.py:264-268 — 앵커 생성 시 동일 규칙 재사용):
```python
    local = user_frame - start
    js = sorted(j for (i, j) in path if i == local)
    if not js:
        return None
    return max(0, min(int(js[len(js) // 2]), ref_n - 1))
```

---

### `analysis/fault_zoom.py` [수정, D-04] (표시 모듈, self-analog)

**제거 대상 — 시간비례 근사 폴백** (fault_zoom.py:848-859, D-04):
```python
    else:
        # B1: DTW match 로 같은-pose 기준 프레임. 불가 시 시간비례 근사 폴백.
        r_matched = _matched_ref_frame(dtw_match, u_idx, r_n)
        if r_matched is not None:
            r_idx = r_matched
            r_kp_idx = _to_rep_idx(r_matched, frames_fps, r_rep_fps, r_rep_frames)
        else:
            ratio = (u_idx / max(1, u_n - 1)) if u_n > 1 else 0.0
            r_idx = int(round(ratio * (r_n - 1))) if r_n > 1 else 0
            ...
```
→ `else` 블록(ratio 근사)을 전신 폴백 + scalar 플래그(예: `refMatch: "failed"`) 방출로 교체.

**fps 변환 단일 공식 관례** (fault_zoom.py:177-187 — RESEARCH Pitfall 1 의 fps 정합 fix 도 이 관례를 따라 단일 helper 로):
```python
def _to_rep_idx(
    idx: int, frames_fps: float, rep_fps: float, rep_frames: int
) -> int:
    """9fps frames 인덱스 → keypointReport fps 인덱스 (B1 변환 공식 단일 출처).

    build_fault_zoom_comparisons 와 select_confident_frame 이 같은 공식을
    공유한다 — 중복 공식 금지 (quick-260705-ftn)."""
    return max(0, min(
        int(round(idx / max(1e-6, frames_fps) * rep_fps)),
        max(0, rep_frames - 1),
    ))
```
주의: `_matched_ref_frame` docstring (:251-255) 의 "ref_idx = 기준 angles 9fps 절대" 는 stale (실제 18fps) — 정정 대상. **본체를 고치면 veto still 경로(app.py:1720)도 바뀌어 점수가 움직인다 → 표시 경로 전용 helper 분리 또는 별도 게이트** (RESEARCH Open Question 2).

**전신 폴백 선례 주석 톤** (fault_zoom.py:819-821, Phase 25-03 / 260702-sic):
```python
    측별 crop 은 3단 강하 (Phase 25-03): 신뢰 좌표=기존 crop → 저신뢰-유한
    좌표=부위-중심 완화(relaxed) crop (카드별 차별화, 앵커 생략) → 좌표 결측=
    전신 폴백. 양측 다 신뢰 좌표 0 이면 기존처럼 skip.
```

---

### `functions/pipeline/app.py` [수정] (오케스트레이터, self-analog)

**정렬 소스 접근 지점** (app.py:3305-3311 — EXPERT 분기, 여기서 `build_motion_alignment(match, user_fps=9.0, ref_fps=...)` 호출):
```python
            # seed 는 Firestore 의 nested-array 금지 회피로 angles 를 flat 저장.
            num_joints = len(ref.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
            deviation, match, user_seg, a_ref = _deviation_against(
                angles, ref["angles"], num_joints
            )
            reference_dtw_match = match  # B1 — fault-zoom 같은-pose 프레임 정렬용.
```
ref_fps 는 ref doc 의 `keypointReport.fps`(또는 top-level mirror)에서 읽기 — 하드코딩 금지 (RESEARCH Pitfall 1/6).

**result 주입 패턴 — "result 안으로 흐른다, 신규 kwarg 없음"** (firestore_admin.py:904-913 의 safetyFlags/deductionBreakdown 선례):
```python
    # Phase 24 (ND-01/HIGH-1) — deductionBreakdown 은 seam 에서 result 안에 OBJECT 로
    # 들어온다(visionVeto persistence analog, NO 신규 kwarg). payload['result']=dict(result)
    # 전에 scoped validator 로 records/coverageGaps flat 검증(firestore-nested-array-flat).
    if result:
        _validate_deduction_breakdown((result or {}).get("deductionBreakdown"))
        _flags = (result or {}).get("safetyFlags")
        if isinstance(_flags, list):
            _validate_safety_flags(_flags)
```
→ `result["motionAlignment"] = alignment_dict` 를 complete_analysis **호출 전에** result 에 넣는다 (27-06 "complete 후 result.* write 금지" 게이트 정합). complete_analysis 호출부 형상은 app.py:4131-4153 참조 (kwargs 마다 출처 plan 주석).

**실패 시 graceful skip 관례** (app.py:4125-4128 — alignment 방출 실패가 분석을 죽이면 안 됨):
```python
        except Exception:  # noqa: BLE001 - 분석 흐름 차단 0
            log.exception(
                "joints3d flat wiring raise — graceful skip joints3d 저장"
            )
```

---

### `firestore_admin.py` [수정] (scoped validator)

**Analog:** `_validate_safety_flags` (firestore_admin.py:288-305) — 신규 필드마다 전용 scoped validator, generic validator 본체 무변경:
```python
def _validate_safety_flags(flags, *, path: str = "safetyFlags") -> None:
    """SafetyFlag list[dict] 전용 scoped validator — Plan 10-02 (T-10-01 방어).

    `result['safetyFlags']` 의 단일 persistence path 에서만 호출 (complete_analysis 에
    신규 kwarg 추가 X — 플래그는 result 안으로 흐른다). ... [[firestore-nested-array-flat]] 보존.
    """
    if flags is None:
        return
    if not isinstance(flags, list):
        raise TypeError(
            f"{path} must be list[dict] (firestore-nested-array-flat): "
            f"got {type(flags).__name__}"
        )
    for i, flag in enumerate(flags):
        _validate_dict_only_scalars(flag, path=f"{path}[{i}]")
```
→ `_validate_motion_alignment(payload)` 신설: dict 강제, `anchors` = flat list[float] + 길이 상한(예: ≤512) + 단조성, 나머지 키 scalar-only. complete_analysis 의 :907-913 블록에 한 줄 추가 (docstring 에 Phase 28 이력 단락 추가 — 기존 Phase 6/8/10/24 단락 형식).

---

### `tests/test_motion_alignment.py` [신규] (test)

**Analog:** `backend/tests/test_dimensions.py:1-45` — 순수 모듈 unit 의 표준 형태: (1) 모듈 docstring "AWS 불필요", (2) 합성 입력 빌더 helper, (3) 의미 있는 단언 + None(가짜 값 안 만듦) 검증:
```python
"""IPSF 실행 차원 점수 — 절대 지표(라인/안정성)의 의미 검증. AWS 불필요."""
import numpy as np
from sunity_shared.analysis import dimensions, technique

def _pose(angle_map: dict[str, float], t: int = 30) -> np.ndarray:
    """모든 프레임이 동일한 (정지) 포즈. angle_map 외 관절은 90°."""
    ...

def test_line_none_when_no_extension_required():
    # 전부 의도적 굽힘 → 평가 대상 아님 → None(가짜 점수 안 만듦).
    p = _profile(extend=())
    assert dimensions.line_score(...) is None
```
→ 합성 MotionMatch 빌더(`_match(path, distance, start=0)`) + RESEARCH Test Map 케이스: 단조/초 단위/결정론/identity path→기울기 1.0/9fps-18fps 변환/tier 경계(8.0/25.0)/None 입력→None. 실행: `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_motion_alignment.py -q`.

---

### `app/src/lib/alignmentWarp.ts` [신규] (순수 TS lib)

**Analog:** `app/src/lib/deductionLabels.ts:1-26` — 헤더 주석(단일 출처 선언 + 원칙 인용) → `import type` → named export 순수 함수:
```typescript
// 점수 계산 내역 라벨/포맷터 (quick-260702-q8q) — 감점 record 표시의 단일 출처.
//
// 채점 원칙 ([[scoring-must-be-transparent-deduction-tally]]): ... 본 모듈은 저장된
// record 값을 **그대로** 표기만 한다 — 앱에서 점수/판정 재계산·재해석 금지 (객관성).

import type {
  DeductionBreakdown,
  DeductionRecord,
  ...
} from '../types/analysis';

export function circledNumberKo(n: number): string {
  return n >= 1 && n <= 9 ? CIRCLED_DIGITS_KO[n - 1] : `(${n})`;
}
```
→ alignmentWarp.ts 도 동일 형상: 헤더에 "정렬 목표시각 계산의 단일 출처 (28-RESEARCH Pitfall 7 — `rightPlayer.currentTime =` 는 전부 여기 경유)", `import type { MotionAlignment } from '../types/analysis'`, `export function warpTime(...)`, `export function segmentRate(...)` (player 의존 0 — tsc 만으로 검증 가능). 클램프 상수 `RATE_MIN=0.5/RATE_MAX=2.0` 은 belle 고정값 출처 주석 (VideoCompare.tsx:184-189 의 FULLSCREEN_ZOOM 승인값 주석 관례).

**방어적 normalize 패턴** (userAnalyses.ts:42-58 — malformed 데이터 graceful null, RESEARCH V5):
```typescript
function normalizeCoachHook(value: unknown): CoachCommentHook | null {
  if (value == null || typeof value !== 'object') return null;
  const hook = value as Record<string, unknown>;
  return {
    autoFindingsSummary:
      typeof hook.autoFindingsSummary === 'string' ? hook.autoFindingsSummary : '',
    ...
  };
}
```
→ anchors 비단조/NaN/홀수 길이 → null 반환(= legacy 폴백, 크래시 0)하는 `normalizeMotionAlignment` 를 같은 형상으로.

---

### `app/src/components/VideoCompare.tsx` [수정] (component, self-analog)

**drift tick — 목표값 교체 지점** (VideoCompare.tsx:303-325, 현행 `cR ≈ cL` 을 `cR ≈ warpTime(alignment, cL)` 로):
```typescript
      if (
        hasLeft && hasRight && bothPlaying && !scrubbingRef.current &&
        dL > 0 && dR > 0 && shorter > 0 &&
        Math.max(cL, cR) < shorter - 0.1 &&
        leftPlayer && rightPlayer
      ) {
        const drift = Math.abs(cL - cR);
        if (drift > DRIFT_CORRECT_THRESHOLD_S) {
          // 느린 쪽 시각을 authoritative time 으로 사용 (빠른 쪽 back-seek).
          const slowerTime = Math.min(cL, cR);
          if (cL > cR) { leftPlayer.currentTime = slowerTime; }
          else { rightPlayer.currentTime = slowerTime; }
        }
      }
```
워핑 모드에선 학생(left)=master 로 시계 불변, right 만 `warpTime(cL)` 로 보정. 상수 재사용: `DRIFT_CORRECT_THRESHOLD_S = 0.2` (:156, Build 16 UAT 산물 — 재학습 금지). 종료 판정(:334-342 shorter 로직)도 warp 정의역 반영.

**seekBoth — warp 경유 필요 지점** (VideoCompare.tsx:424-442):
```typescript
  const seekBoth = useCallback(
    (target: number) => {
      ...
      if (leftPlayer) leftPlayer.currentTime = safe;
      if (rightPlayer) rightPlayer.currentTime = safe;   // ← warpTime(safe) 로
      if (hasLeft) setLeftCurrent(safe);
      if (hasRight) setRightCurrent(safe);
    },
    [hasLeft, hasRight, leftPlayer, rightPlayer],
  );
```
Pitfall 7 grep 게이트: `rightPlayer.currentTime =` 전부 warp 경유 (tick/seekBoth/togglePlay/restart).

**배지 — tier 카피로 승격할 자리** (VideoCompare.tsx:735-758 — 주석이 이 phase 를 예고):
```typescript
      {/* Phase 20 (UI A4) — "자동 구간 맞춤" 신뢰 배지.
          ... LIGHT 버전(이번 plan): 정적 배지 + 한 줄 설명만. ... 가짜 수치 금지.
          TODO(deferred-backend): 실 정렬 신뢰도(DTW 매칭 품질 등)를 백엔드가
          내려주면 배지에 수치/강도를 표시. 현재는 contract 에 필드 없어 정적. */}
      {hasLeft && hasRight && (
        <View style={styles.alignBadgeRow}>
          <View style={styles.alignBadge}>
            <Ionicons name="git-compare-outline" size={12} color={colors.brand} />
            <Text style={styles.alignBadgeText}>자동 구간 맞춤</Text>
          </View>
          <Text style={styles.alignBadgeHint}>
            서로 다른 시작점을 핵심 구간 기준으로 자동 정렬했어요.
          </Text>
        </View>
      )}
```
→ tier 별 정직 카피 3종("~해요" 체), 수치는 `motionAlignment.distance` 실데이터만. 신규 prop 은 `alignment?: MotionAlignment | null` optional — props 목록 :191-203 참조, 부재 시 현행 코드 100% 보존.

**player 초기화 관례** (:211-220 — playbackRate 신설 시 이 setup 콜백/기존 인스턴스 재사용, 신규 useVideoPlayer 호출 금지 :652 주석):
```typescript
  const rightPlayer = useVideoPlayer(rightUrl ?? null, (p) => {
    p.muted = true;          // muted=true → preservesPitch 무관
    p.loop = false;
    p.timeUpdateEventInterval = 0.033;
  });
```

---

### `app/src/app/analysis/result.tsx` [수정, D-05] (screen, self-analog)

**legacy 배너 — 조건부 1줄/배지 렌더 관례** (result.tsx:1110-1135):
```typescript
          {/* Phase 4 (04-02 D-08 / BLOCKER-3) — 정확도 제한 배지. ... */}
          <AccuracyLimitBadge
            visible={hasSynthesisWarning(result, 'ai_synthesis_failed')}
          />
          ...
          {/* Phase 11 ... 가볍게 한 줄만 (전용 강조 배너 채택 안 함 —
              매 분석 반복 노출 거슬림, D-07). */}
          <Text style={styles.coachPositioning}>
            이 분석은 강사 지도를 돕는 참고예요.
          </Text>
```
legacy 판정 = `result.motionAlignment === undefined` (optional 부재 = legacy — region/tier 선례). 배너는 비교 카드(두 영상 보유) 문맥에서만.

**재분석 CTA — 기존 라우팅 재사용** (result.tsx:1673-1679, D-05 배너 CTA 도 동일):
```typescript
        <Pressable
          onPress={() => router.replace('/(tabs)/analyze')}
          accessibilityRole="button"
          hitSlop={8}
        >
          <Text style={styles.link}>다시 분석하기</Text>
        </Pressable>
```
accessibility props(`accessibilityRole`, `hitSlop`) 필수, 스타일은 theme 토큰만. VideoCompare 로의 prop 전달은 :1286 `<VideoCompare ...>` 호출부에 `alignment={...}` 추가. **주의: 26-02(wrapper 분리)/27-07(zoom placeholder) 이 이 파일을 먼저 수정 예정 — 라인 아님 심볼 기준 탐색.**

---

### 계약 3-way (`analysis.ts` + `models.py` + `docs/contract.md`)

**TS optional 필드 + lockstep 주석 관례** (analysis.ts:451-459 — tier 선례, motionAlignment 도 동일 형식):
```typescript
  /**
   * 2단 시각 언어 tier (quick-260704-fz4, CONTEXT locked) —
   * 'confirmed'=확정 결함(감점 근거, 빨강) / 'advisory'=측정 초과·확인 권장
   * (감점 아님, ... 표시 전용). 부재(legacy doc)=
   * confirmed 취급 — advisory 카드 미생성 하위호환. Python lockstep: pipeline
   * _render_fault_zoom tier 방출 (region 선례와 동일 ...).
   */
  tier?: 'confirmed' | 'advisory' | null;
```
`AnalysisResult` 에 추가하는 자리 관례 (:519-525 — OPTIONAL + legacy 호환 주석):
```typescript
  // Phase 20 SCORE-08 — 비전 하향 거부권 audit. OPTIONAL (legacy doc 호환).
  visionVeto?: VisionVeto;
  ...
  faultZoomComparisons?: FaultZoomComparison[];
```
→ `motionAlignment?: MotionAlignment;` + `MotionAlignment` interface (version/source/tier/reason/anchors/anchorCount/distance — RESEARCH Pattern 1). `FaultZoomComparison` 에는 `refMatch?: 'dtw' | 'failed'` 류 scalar 추가 (D-04 캡션).

**Python 계약 상수 블록 관례** (models.py:153-159):
```python
# 3-way lockstep: app/src/types/analysis.ts DeductionRecord/DeductionBreakdown +
#   docs/contract.md §10.
DEDUCTION_RECORD_KEYS = (
    "criterion", "measuredValue", "baselineValue", "baselineKind",
    "deviation", "ruleId", "points", "unit", "ipsfAnchor", "source",
    "deviationSource",
)
```
→ `MOTION_ALIGNMENT_KEYS` / `MOTION_ALIGNMENT_TIERS = ("warped", "trim_only", "disabled")` 동일 형식 + contract.md 신규 절. 세 파일 동시 수정 (한쪽만 수정 = 프로젝트 anti-pattern).

## Shared Patterns

### 1. Optional 계약 필드 + legacy 폴백
**Source:** `analysis.ts:451-459` (tier), `userAnalyses.ts:112-114` (`'coachCommentHook' in report` 키-부재 분기)
**Apply to:** motionAlignment, refMatch, 앱 소비 전부 — 필드 부재 = 현행 동작 100% 보존 (마이그레이션 0).

### 2. Firestore flat + scoped validator
**Source:** `firestore_admin.py:884-887` ("flat list + anglesJointKeys(길이 J) + anglesFrames(T) 로 저장하고 읽는 쪽에서 reshape") + `_validate_safety_flags` (:288-305)
**Apply to:** anchors flat float 쌍 + anchorCount 메타 (anglesFrames 선례). generic validator 본체 변경 영구 0.

### 3. 임계/상수 출처 주석 (calibration-source-hard-gate)
**Source:** `vision_veto.py:908-916` (_ALIGN_*, "특정 영상 튜닝 금지"), `VideoCompare.tsx:184-189` (FULLSCREEN_ZOOM belle 승인값 주석)
**Apply to:** motion_alignment.py 임계(8.0/25.0 재사용 출처), RATE_MIN/MAX(belle 고정), ANCHOR_STEP_S(크기 상한 근거).

### 4. 채점 무접촉 경계 주석
**Source:** `vision_veto.py:909-910` ("DTW median 은 scoring 경로이므로 본 helper 와 섞지 않는다"), `fault_zoom.py:201` ("표시 전용, 채점/veto/게이트 무접촉")
**Apply to:** motion_alignment.py 헤더 + fault_zoom D-04 수정부 — veto still 경로(`_build_selected_frame_pair`, app.py:1720) 접촉 금지 명시.

### 5. Korean why-주석 + spec 인용
**Source:** 전 발췌 공통 — `(28-CONTEXT D-0x)`, `(contract.md §)`, `(quick-260705-ftn)` 형식.
**Apply to:** 모든 신규/수정 코드.

## No Analog Found

| 대상 | Role | Data Flow | Reason |
|------|------|-----------|--------|
| expo-video `playbackRate` 제어 (VideoCompare 내 구간 rate 설정) | component 내 player 제어 | streaming | 코드베이스에 playbackRate 사용처 0 (grep 확인). RESEARCH Pattern 3 사용: rate=feedforward(구간 경계에서만 변경) + tick 보정 seek=feedback 안전망. 매 tick rate 재설정 금지. 실기기 manual 검증 항목 (A2) |

## Metadata

**Analog search scope:** `backend/shared/python/sunity_shared/{analysis/,firestore_admin.py,models.py}`, `backend/functions/pipeline/`, `backend/tests/`, `app/src/{lib,components,types,app/analysis}/`
**Files scanned:** 15 (발췌 추출 11)
**Pattern extraction date:** 2026-07-07
