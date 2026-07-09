# Phase 30: 성장 추적 개선 — 평균 기반·동작별 막대 - Pattern Map

**Mapped:** 2026-07-09
**Files analyzed:** 11 (신규 1 + 수정 10)
**Analogs found:** 10 / 11 (동작별 막대 뷰만 부분 analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/src/components/GrowthChart.tsx` (교체/확장) | component (svg chart) | transform (scores → svg) | 자기 자신 (현행 88줄) | exact |
| `app/src/lib/growthSelectors.ts` 류 (신규 — 집계 selector) | utility (순수 함수) | transform (AnalysisDoc[] → 주별 평균/동작별 델타) | `app/src/lib/alignmentWarp.ts` | role+flow exact |
| `app/src/app/(tabs)/index.tsx` (GrowthCard 재작업) | screen component | request-response (Firestore 구독 → 렌더) | 자기 자신 + `BodyProfileForm.tsx` Segmented (토글) | exact |
| `app/src/lib/userAnalyses.ts` (normalize 방어 파싱) | data-source hook | streaming (onSnapshot) | 자기 자신 — `learningOptIn` 키-존재 spread 선례 | exact |
| `app/src/types/analysis.ts` (Mode3Comparison optional 필드) | data contract (TS) | — | `scoringBasis?` / `tier?` optional 선례 | exact |
| `app/src/theme/colors.ts` (▼ 파란계열 토큰) | config (theme token) | — | `advisoryOrange` alias 신설 블록 선례 | exact |
| `backend/shared/.../models.py` (필드 명세) | data contract (Python) | — | `MODE3_SCORING_BASES` 섹션 (:45-67) | exact |
| `backend/shared/.../analysis/assemble.py` (`build_mode3` kwarg) | pure builder | transform | `build_mode3` 자신의 `scoring_basis` kwarg 패턴 | exact |
| `backend/functions/pipeline/app.py` (인식 동작명 배선) | pipeline orchestrator | event-driven (SQS) | `_mode3_comparison` 의 `_mode3_scoring_basis` 배선 (:3280, :3319) | exact |
| `backend/shared/.../firestore_admin.py` (complete_analysis 검증) | persistence | CRUD (write) | `safetyFlags` in-result 검증 선례 (신규 kwarg 없음, :1017-1021) | role-match |
| `docs/contract.md` §4 (Mode3Comparison 절) | docs contract | — | `scoringBasis` 서술 블록 (:401-427) | exact |
| (테스트) `backend/tests/test_assemble.py` | test | — | `test_mode3_*` + scoringBasis emit 검증 (:60-121) | exact |

**동작별 막대(주식창식) 리스트 뷰** — 정확한 analog 없음(하단 "No Analog Found" 참조). 행 리스트 구조는 `history.tsx` 행(:86-122), svg 렌더는 `GrowthChart.tsx` 패턴을 부분 재사용.

---

## Pattern Assignments

### `app/src/components/GrowthChart.tsx` (component, transform)

**Analog:** 자기 자신 — 현행 파일이 그대로 재사용 골격. props 를 raw scores → 주별 평균 포인트로 바꾸는 것이 D-01 의 최소 변경.

**Imports + svg 패턴** (`GrowthChart.tsx:1-11`):
```typescript
import { View } from 'react-native';
import Svg, {
  Circle, Defs, LinearGradient, Polygon, Polyline, Stop,
  Text as SvgText,
} from 'react-native-svg';
import { colors } from '../theme';
```

**핵심 차트 패턴 — viewBox 고정 좌표계 + min/max 정규화** (`GrowthChart.tsx:17-38`):
```typescript
const W = 320;
const H = 132;
const PAD_X = 18;
const PAD_TOP = 22; // 점수 라벨 공간
const PAD_BOT = 14;

export function GrowthChart({ scores }: { scores: number[] }) {
  if (scores.length < 2) return null;
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = max - min || 1; // 전부 동점이면 평평하게
  const innerW = W - PAD_X * 2;
  const innerH = H - PAD_TOP - PAD_BOT;
  const pts = scores.map((s, i) => {
    const x = PAD_X + (i / (scores.length - 1)) * innerW;
    const y = PAD_TOP + (1 - (s - min) / range) * innerH;
    return [x, y] as const;
  });
```
- 브랜드 그라디언트 area(`Defs`+`Polygon`, :43-49) / 점 강조(마지막 점 채움, :58-71) / `SvgText` 점수 라벨(:72-84) 전부 토큰(`colors.brand`, `colors.bg`, `colors.textSecondary`)만 사용.
- D-06 막대 뷰도 동일 svg 직접 패턴으로(CONTEXT 재량: 신규 차트 라이브러리 도입 금지 — `victory-native` 는 미설치 상태 유지, `react-native-svg` 15.12.1 이 유일 렌더러).
- **컴포넌트 상단 Korean 블록 주석에 스펙 출처 인용** (`GrowthChart.tsx:13-15`: `design.md §6 + Figma 1:719` 형식) — 신규/수정 시 동일 관례.

---

### 신규 집계 selector (예: `app/src/lib/growthSelectors.ts`) (utility, transform)

**Analog:** `app/src/lib/alignmentWarp.ts` — "순수 함수만, player/react 의존 0, tsc --noEmit 만으로 검증" 패턴이 CONTEXT Integration Points("집계 selector 는 순수 함수로 분리해 테스트 가능하게")와 1:1 대응. **앱에 JS 테스트 러너 없음** — 검증 게이트는 `npm run typecheck` 뿐이므로 alignmentWarp 처럼 타입으로 계약을 조이는 것이 실효적.

**모듈 헤더 + 순수성 선언 패턴** (`alignmentWarp.ts:1-16`):
```typescript
// 정렬 목표시각 계산의 단일 출처 — `rightPlayer.currentTime =` 는 전부 여기 경유
// (28-RESEARCH Pitfall 7: ...).
// 순수 함수만 (player/react 의존 0 — `tsc --noEmit` 만으로 검증 가능).
import type { MotionAlignment } from '../types/analysis';

export type { MotionAlignment };
```

**상수는 출처 박제 + named export** (`alignmentWarp.ts:18-26`):
```typescript
// belle 고정값 (28-CONTEXT specifics) — 배속 클램프 0.5~2배. ... 감으로 변경 금지, 출처 박제.
export const RATE_MIN = 0.5;
export const RATE_MAX = 2.0;
```

**기존 집계 로직의 최소 선례 — `averageScore`** (`(tabs)/index.tsx:58-64`, 헤더 "(평균 N점)" 의 현행 구현 — Claude 재량으로 유지/정리 대상):
```typescript
function averageScore(analyses: AnalysisDoc[]): number | null {
  const scores = analyses
    .map((a) => a.result?.overallScore)
    .filter((s): s is number => typeof s === 'number');
  if (scores.length === 0) return null;
  return Math.round(scores.reduce((sum, s) => sum + s, 0) / scores.length);
}
```
- 주별 평균 selector 는 이 필터 관용구(`filter((s): s is number => ...)`) + `useMemo`(index.tsx:72) 조합을 확장.
- 동작별 그룹핑 키 판별은 `history.tsx:23-32` 를 그대로 복사:
```typescript
function motionLabel(doc: AnalysisDoc): string {
  if (doc.result?.comparison.mode === 'mode1') {
    return doc.result.comparison.referenceMotionName;
  }
  return '내 동작 분석';
}
function modeBadge(doc: AnalysisDoc): string {
  return doc.mode === 'mode1' ? '프로 비교' : '내 기록';
}
```
(D-09 통합 리스트의 배지 카피 = `modeBadge` 재사용, mode1 그룹핑 키 = `comparison.referenceMotionName`, mode3 부재 시 '내 기록' 단일 그룹.)

---

### `app/src/app/(tabs)/index.tsx` (screen, GrowthCard 재작업)

**Analog (수정 지점):** 자기 자신. 현행 GrowthCard/GrowthLockedCard (`index.tsx:292-313`):
```typescript
function GrowthCard({ analyses }: { analyses: AnalysisDoc[] }) {
  // 분석 점수(overallScore) 추이 꺾은선. Figma 1:719 — 차트 안 상단 라벨.
  const recent = analyses.slice(0, 6).reverse(); // 최근 6건, 오래된→최근
  const scores = recent.map((a) => a.result?.overallScore ?? 0);
  return (
    <View style={styles.growthCard}>
      <Text style={styles.growthHeader}>이번주 성장 그래프</Text>
      <GrowthChart scores={scores} />
    </View>
  );
}

function GrowthLockedCard() {
  return (
    <View style={styles.growthLocked}>
      <Text style={styles.growthLockedText}>
        분석을 2번 이상 하면{'\n'}AI 그래프가 보여요
      </Text>
    </View>
  );
}
```
- 데이터 소스는 이미 `const { analyses } = useMyAnalyses({ doneOnly: true })` (:68) — 추가 쿼리 없이 selector 만 얹는다(CONTEXT 확정).
- 소형 프레젠테이션 helper 는 같은 파일에 named function + inline prop type (컨벤션 — `RecentAnalysisCard`/`ChallengeRow` 선례).
- 카드 스타일 = `styles.growthCard` (:440-447, `colors.cardBg`/`layout.cardBorderWidth`/`radius.card`/`spacing.cardPadding` 토큰).

**Analog (2층 토글 UI — D-02/D-03/D-08):** `app/src/components/BodyProfileForm.tsx` 의 제네릭 `Segmented` (:460-499) — 프로젝트 유일의 단일선택 세그먼트 선례:
```typescript
// 제네릭 단일선택 세그먼트 (경력/우세손). ...
function Segmented<T extends string>({ label, options, selected, groupLabel, onSelect }: {
  label: string;
  options: ReadonlyArray<{ value: T; label: string }>;
  selected: T | null;
  groupLabel: string;
  onSelect: (v: T) => void;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.segmentRow}>
        {options.map((opt) => {
          const isSel = selected === opt.value;
          return (
            <Pressable
              key={opt.value}
              onPress={() => onSelect(opt.value)}
              accessibilityRole="button"
              accessibilityState={{ selected: isSel }}
              accessibilityLabel={`${groupLabel} ${opt.label}${isSel ? ', 선택됨' : ''}`}
              hitSlop={6}
              style={[styles.segment, isSel && styles.segmentSelected]}
            >
              <Text style={[styles.segmentText, isSel && styles.segmentTextSelected]}>
                {opt.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}
```
- 선택 상태 스타일 선례: `chipSelected: { backgroundColor: colors.brandTint, borderColor: colors.brand }` (BodyProfileForm.tsx:562) — D-03 "토글 활성 상태 브랜드색 명확 표시" 요구와 정합 (`colors.brandTint` = `rgba(255,75,51,0.15)`).
- a11y 필수 세트: `accessibilityRole` + `accessibilityState({ selected })` + `accessibilityLabel`(한국어) + `hitSlop` — 프로젝트 컨벤션.
- 이진 on/off 만 필요하면 `KeypointOverlayToggle.tsx` (controlled switch, caller 가 state 소유) 도 참고 — 단 D-02 는 라벨 있는 2-옵션 세그먼트라 `Segmented` 쪽이 정확.

**Analog (동작별 행 리스트 — D-04/D-09):** `history.tsx` 행 렌더 (:86-122) — 배지+제목+우측 수치 행 구조:
```typescript
<View style={styles.rowHead}>
  <Text style={styles.rowBadge}>{modeBadge(doc)}</Text>
  <Text style={styles.rowDate}>{formatDate(doc.createdAt)}</Text>
</View>
<Text style={styles.rowMotion} numberOfLines={1}>{motionLabel(doc)}</Text>
...
<Text style={styles.rowScore}>{doc.result?.overallScore ?? 0}</Text>
```
- `rowBadge` 스타일 (:152-160): `colors.brand` bg + `colors.textWhite` + `borderRadius: 8` — D-09 '프로' 배지 시각 그대로 복사 가능.

---

### `app/src/types/analysis.ts` (contract, Mode3Comparison optional 필드)

**Analog:** `Mode3Comparison.scoringBasis?` 선례 (:258-277) — "optional + legacy 호환 + Python lockstep 인용" 3요소가 전부 들어있는 모범:
```typescript
export interface Mode3Comparison {
  mode: 'mode3';
  isFirst: boolean; // 첫 분석이면 절대값만 (비교 대상 없음)
  previousAnalysisId?: string;
  deltaFromPrevious?: Partial<Record<ScoreDimension, number>>;
  // Phase 19 TRUST-03 — 실제 채점 SOURCE 라벨 (Mode3 4-value enum). OPTIONAL (legacy 호환).
  scoringBasis?:
    | 'reference_free_absolute'
    | 'recognized_motion_absolute'
    | 'previous_analysis_plus_absolute'
    | 'previous_analysis_plus_reference_free_absolute';
  scoringBasisLabel?: string;
}
```
- 신규 인식 동작 필드(예: `recognizedMotionId?` / `recognizedMotionName?`)는 이 인터페이스에 optional 로 삽입. 주석 서술 모범 = `tier?` (:451-459) — "부재(legacy doc)=X 취급 — 하위호환. Python lockstep: <방출부> (선례명과 동일 규칙)" 형식:
```typescript
  /**
   * 2단 시각 언어 tier (quick-260704-fz4, CONTEXT locked) — ...
   * 부재(legacy doc)= confirmed 취급 — advisory 카드 미생성 하위호환. Python lockstep: pipeline
   * _render_fault_zoom tier 방출 (region 선례와 동일 — ...).
   */
  tier?: 'confirmed' | 'advisory' | null;
```
- Mode1 쪽 그룹핑 키는 이미 존재 — `Mode1Comparison.referenceMotionId/Name` (:245-246). 앱 층은 수정 불필요.
- `learningOptIn?` 주석 (:657-666) 이 "3-way lockstep: models.py + docs/contract.md §3 과 동시 갱신" 문구 선례 — 신규 필드 주석에 동일 문구 필수.

---

### `app/src/lib/userAnalyses.ts` (normalize 방어 파싱)

**Analog:** 같은 파일의 `learningOptIn` 키-존재 spread (:348-354) — **scalar optional 필드의 최소 방어 패턴** (신규 필드가 comparison 내부 string 이라도 접근 관용구 동일):
```typescript
    // [IN-03] Phase 26 (D-08/D-09) — 업로드 시점 학습활용 동의값. boolean 일 때만
    // 매핑(방어) — 필드 부재/타입 불일치면 키 생략해 undefined 유지 ...
    ...(typeof raw.learningOptIn === 'boolean'
      ? { learningOptIn: raw.learningOptIn }
      : {}),
```
- comparison 은 현재 normalize 가 통째로 신뢰(`raw.result as AnalysisDoc['result']`, :91) — 신규 string 필드도 optional 이므로 **깊은 검증 불필요**가 기존 관례("backend validator 가 flat 강제하므로 여기선 얕게", :166-169 recommendedExercises 주석). selector 소비 시점에 `typeof === 'string'` 가드만 두면 충분.
- 만약 normalize 층에 가드를 넣는다면 immutable spread + `?? fallback` 패턴 (:122-136 forceSignalsReport 블록) mirror.
- **하지 말 것:** malformed 시 `null` 대입 — optional 필드는 `undefined` 로 두어 optional 유지 (:243-244 BLOCKER-1 주석의 명시 규칙).

---

### `backend/shared/python/sunity_shared/models.py` (필드 명세)

**Analog:** `MODE3_SCORING_BASES` 섹션 (:45-67) — 계약 상수 + 3중 계약 인용 주석 형식:
```python
# ── Phase 19 (TRUST-03): comparison.scoringBasis 명세 ──────────────────
# 결과 화면에 "어떤 SOURCE 로 채점했는지" 를 정확히 노출 (거짓 confident 점수 차단).
# 3중 계약: app/src/types/analysis.ts (Mode1Comparison/Mode3Comparison) +
# assemble.build_mode1/build_mode3 + docs/contract.md 와 lockstep.
MODE1_SCORING_BASIS = "reference_motion"
MODE3_SCORING_BASES = (
    "reference_free_absolute",
    ...
)
```
- 신규 인식 동작명 필드는 enum 이 아니라 free string(동작 id/명)이므로 상수 tuple 은 불필요할 수 있음 — 그 경우에도 **"── Phase 30: ... 명세 ──" 섹션 주석 + 3중 계약 인용** 은 동일 형식으로 추가 (파일 헤더 :1-4 가 "이 파일이 바뀌면 contract.md 와 app 타입도 같이" 명시).

---

### `backend/shared/.../analysis/assemble.py` (`build_mode3` 확장)

**Analog:** `build_mode3` 자신의 `scoring_basis` optional kwarg 패턴 (assemble.py:641-706 부근) — **None 미전달 시 기존 dict 정확히 보존(키 미추가), 전달 시에만 emit + 허용값 검증**:
```python
def build_mode3(
    is_first: bool,
    previous_analysis_id: str | None = None,
    prev_dimension_scores: dict | None = None,
    cur_dimension_scores: dict | None = None,
    scoring_basis: str | None = None,
    scoring_basis_label: str | None = None,
) -> dict:
    """...
    Phase 19 (ITER-2 MEDIUM-2 backward-compat + ITER-3 HIGH-2 4-value enum):
    scoring_basis 미전달(None) 시 기존 dict 정확히 보존 (scoringBasis 키 미추가).
    전달 시에만 scoringBasis + scoringBasisLabel emit. ...
    """
    if scoring_basis is not None and scoring_basis not in _MODE3_SCORING_BASES:
        raise ValueError(...)
    out: dict = {"mode": "mode3", "isFirst": bool(is_first)}
    if scoring_basis is not None:
        out["scoringBasis"] = scoring_basis
        out["scoringBasisLabel"] = (
            scoring_basis_label or _MODE3_SCORING_BASIS_LABELS.get(scoring_basis, "")
        )
```
- 신규 kwarg (예: `recognized_motion_id: str | None = None`, `recognized_motion_name: str | None = None`)도 같은 규칙: None → 키 미추가(legacy 동형 보존, 기존 `test_mode3_first_has_no_delta` 의 exact-dict assert 를 깨지 않음), 전달 시에만 camelCase 키 emit.
- Mode1 always-emit 대비 Mode3 conditional-emit 차이에 주의 — 인식 실패/FallbackRecognizer 경로에선 `profile.motion_id` 가 None 이므로 conditional 이 맞다.

---

### `backend/functions/pipeline/app.py` (인식 동작명 배선)

**Analog:** `_mode3_scoring_basis` 배선 — recognizer 결과(profile)가 이미 `_mode3_comparison` 에 도달해 있는 seam:

**seam 함수 시그니처** (app.py:3233-3238):
```python
def _mode3_comparison(
    angles: np.ndarray,
    prev: dict | None,
    profile: technique.TechniqueProfile,
    branch_info: assemble.MotionBranchInfo | None = None,
):
```
- `profile` 은 `technique.TechniqueProfile` frozen dataclass — **인식 동작 id/명의 source 필드가 이미 존재**: `profile.motion_id` (technique.py:64, "Gemini canonical motion name 을 reference 컬렉션 lookup 의 stable key 로") + `profile.name` (technique.py:46, 표시용 기술명, "미상" 가능).

**first 분기 emit 지점** (app.py:3280-3288):
```python
        first_basis = _mode3_scoring_basis(
            is_first=True, is_reference_free=is_reference_free
        )
        return (
            assessments,
            abs_dims,
            overall,
            assemble.build_mode3(is_first=True, scoring_basis=first_basis),
            None,
        )
```

**progress 분기 emit 지점** (app.py:3319-3328):
```python
    progress_basis = _mode3_scoring_basis(
        is_first=False, is_reference_free=is_reference_free
    )
    comparison = assemble.build_mode3(
        is_first=False,
        previous_analysis_id=prev.get("analysisId"),
        prev_dimension_scores=prev_dims,
        cur_dimension_scores=abs_dims,
        scoring_basis=progress_basis,
    )
```
- 신규 필드 배선 = 두 `build_mode3(...)` 호출에 `profile.motion_id`/`profile.name` (또는 getattr 방어) kwarg 추가가 최소 변경. `_mode3_comparison` 은 "순수(어댑터/S3/Firestore 불필요, 테스트 가능)" 선언(:3239) — 순수성 유지.
- **주의:** `_apply_score_suppression` (:3175-3230) 이 comparison dict 를 사후 변형(scoringBasisLabel override)하는 후처리가 존재 — 인식 저신뢰(`low_confidence`) 시 동작명 표기의 신뢰 문제가 있으면 이 층이 처리 seam. 저장 자체는 D-04 "데이터 적립"이 목적이므로 억제와 독립적으로 emit 해도 계약상 무방(플래너 판단 사항으로 명시).
- 저장 경로: comparison 은 `build_result` → `firestore_admin.complete_analysis` (호출부 app.py:4622) 로 자동 포함 — comparison 내부 scalar string 이라 **파이프라인에 별도 저장 코드 불필요**.

---

### `backend/shared/.../firestore_admin.py` (complete_analysis 검증)

**Analog:** `safetyFlags` in-result 검증 선례 (:1017-1021) — **신규 kwarg 없이 result 내부로 흘러온 값을 scoped 검증**:
```python
    if result:
        _validate_deduction_breakdown((result or {}).get("deductionBreakdown"))
        # Plan 10-02 (T-10-01) — safetyFlags 단일 persistence path. result 안으로
        # 흘러온 list[dict] 를 scalar-only scoped validator 로 검증 (신규 kwarg 없음).
        _flags = (result or {}).get("safetyFlags")
        if isinstance(_flags, list):
            _validate_safety_flags(_flags)
```
- 신규 필드는 comparison dict 안 **scalar string** — nested array 위험 0 이므로 `scoringBasis`/`scoringBasisLabel` 과 동일하게 **전용 validator 불필요**가 기존 관례 (scoringBasis 도 validator 없이 저장됨). 굳이 검증을 넣는다면 위 safetyFlags 형식(신규 kwarg 금지, in-result get + isinstance 가드)만 허용.
- **금지:** `_validate_dict_only_scalars` 본체 변경 — "본체 변경 영구 0" 이 파일 전체에 반복 박제된 불변 규칙 (:1000 등).

---

### `docs/contract.md` §4 Mode3Comparison 절

**Analog:** scoringBasis 서술 블록 (contract.md:401-427) — 필드 시그니처 코드블록 + 의미 표 + "Mode1 전용/Mode3 부재" 경계 명시 형식:

~~~
`Mode3Comparison` (자기 성장)
```
mode='mode3', isFirst(bool),
previousAnalysisId?, deltaFromPrevious?{line?,stability,angle?}  (isFirst면 없음)
scoringBasis?          실제 채점 SOURCE (Phase 19, Mode3 = 정확히 4 값)
scoringBasisLabel?     사용자 표시용 한국어 라벨
```
~~~

- 신규 필드 행을 이 코드블록에 추가 + 아래에 "OPTIONAL (legacy doc 호환) — 부재 시 앱은 '내 기록' 단일 그룹" 서술. `learningOptIn` 절(:97-112)의 "> Phase 26 (Plan 26-03) — 신설. ... 3-way lockstep 대상 나열" 각주 형식도 참조.

---

### `backend/tests/test_assemble.py` (테스트)

**Analog:** 기존 mode3 테스트 (:91-118) — exact-dict / 키 존재 assert 스타일:
```python
def test_mode3_first_has_no_delta():
    # 첫 분석 = 비교 대상 없음 → 절대 점수만 (delta 없음).
    c = assemble.build_mode3(is_first=True)
    assert c == {"mode": "mode3", "isFirst": True}
```
- **이 exact-dict assert 가 backward-compat 게이트** — 신규 kwarg 를 None-default 로 설계하면 이 테스트가 그대로 통과해야 한다. 신규 emit 테스트는 scoringBasis emit 테스트(:60-69 의 `assert c["scoringBasis"] == ...` 스타일)를 mirror.
- 실행: `backend/requirements-dev.txt` pytest, `rtk pytest` 로 backend/tests 실행.

---

## Shared Patterns

### 3-way lockstep (단일 atomic commit)
**Source:** `analysis.ts` 헤더 주석 관례 + `models.py:1-4` + `contract.md` 해당 절
**Apply to:** analysis.ts + models.py + contract.md (+ assemble.py 방출부) — 한 커밋으로 동시 변경. 각 파일 주석에 상호 인용 필수 (예: "3-way lockstep: models.py + docs/contract.md §4 와 동시 갱신").

### Optional 필드 + legacy 폴백 (no migration)
**Source:** `analysis.ts:459` `tier?` / `:567` `faultZoomStatus?` / `assemble.py build_mode3 scoring_basis`
**Apply to:** 신규 계약 필드 전부. 규칙: (a) TS optional `?`, (b) Python builder 는 None → 키 미추가, (c) 부재 시 앱 동작을 주석에 명시("부재(legacy doc)=내 기록 그룹"), (d) migration 없음.

### 테마 토큰 신설 (하락 파란계열 — D-06)
**Source:** `colors.ts:77-83` advisoryOrange alias 블록
```typescript
// ── quick-260704-fz4 신설 토큰 (2단 시각 언어) ────────────────────────
// 빨강(brand)=확정 감점 결함 / 주황=측정 초과·확인 권장 ...
// brand #FF4B33 변경 0 (CLAUDE.md §4).
advisoryOrange: '#E6A300', // warnAmber alias — advisory 마커/텍스트/칩
```
**Apply to:** ▲/▼ 색. ▲=`colors.brand` 그대로. ▼=신규 토큰을 이 블록 형식으로 추가 — 기존 후보: `highlight: '#006FFD'`(:34) alias 또는 `progressGreen/progressRed`(:45-46, mode3 발전 +/− 기존 토큰) 재검토. **주의:** 기존 `progressGreen(+)/progressRed(−)` 는 D-06 의 주식창 관례(상승=빨강/하락=파랑)와 부호-색이 반대 — 성장 카드에 그대로 재사용하면 의미 충돌하므로 신규 토큰(+주석에 D-06 근거 박제)이 안전. 하드코딩 절대 금지.

### 데이터 소스 격리 + 클라이언트 집계
**Source:** `userAnalyses.ts:1-6` 헤더 ("화면은 데이터 소스에 무지하도록 격리") + `useMyAnalyses({ doneOnly: true })`
**Apply to:** 신규 쿼리/인덱스 추가 금지 — 기존 구독 위에 순수 selector. Firestore 폴링 금지(anti-pattern).

### Firestore flat (nested array 금지)
**Source:** `firestore_admin._validate_flat_dict_no_nested_array` + `analysis.ts:646-650` angles flat 선례
**Apply to:** 이번 phase 신규 필드는 scalar string 이라 자동 준수 — 만약 플래너가 주별 집계를 문서에 저장하는 설계로 바꾼다면(비권장, 클라이언트 집계가 확정) flat 규칙 적용.

### 주석/카피 컨벤션
**Apply to:** 전 파일. 사용자 카피 한국어(예: history.tsx `'프로 비교'/'내 기록'` 재사용 — D-08 토글 라벨), 주석에 스펙 출처 인용(`design.md §6`, `contract.md §4`, `30-CONTEXT D-0n`), 이모지 금지, `console.log` 금지.

### 배포 경계
**Apply to:** 앱 변경 전부 OTA(JS-only) 가능 / backend 방출 필드는 `sam build --use-container` + deploy. 실기기 확인은 HUMAN-UAT.md 적립(즉시 belle 호출 금지).

---

## No Analog Found

| File/Feature | Role | Data Flow | Reason |
|------|------|-----------|--------|
| 동작별 상승/하락 막대 리스트(주식창식) 뷰 | component | transform | 델타 ▲▼ 막대 UI 는 코드베이스에 선례 없음. 조합으로 해결: 행 구조=`history.tsx:86-122`, 배지=`rowBadge`(:152-160), svg 막대=`GrowthChart.tsx` svg 패턴, 델타 부호 색=신규 토큰. **Figma(fileKey jrdI7kp245HkPfLB0nclsz) 우선 확인 필수** (CONTEXT 재량 + ui-figma-first) |
| D-03 기본 토글 폴백 로직 (마지막 분석 모드 따라가기 + 주별 점 2개 미만 시 타 모드 폴백) | utility | transform | 순수 신규 로직 — analog 없음. selector 모듈에 순수 함수로 두고 `alignmentWarp.ts` 방어적 소비 스타일(anchorCount 불신, :32-33) 적용 |

## Metadata

**Analog search scope:** `app/src/{components,app,lib,theme,types}`, `backend/shared/python/sunity_shared/`, `backend/functions/pipeline/`, `backend/tests/`, `docs/contract.md`
**Files scanned:** 18 (read) + grep 전수 탐색
**Pattern extraction date:** 2026-07-09
