# Phase 32: 분석 결과를 읽히게 만들기 (result-readability-3-omni) - Pattern Map

**Mapped:** 2026-07-21
**Files analyzed:** 38 (create 19 / modify 19)
**Analogs found:** 34 / 38 (exact 24, role-match 10, no-analog 4)

핵심 판정: 이 phase 는 신규 아키텍처가 없다. **모든 신규 파일에 대해 같은 저장소 안에 이미 검증된 선례가 존재**하며, wave-1 수리 3건은 수리 대상 파일 자신이 아날로그다(자체 패턴 유지 수정). 아래 발췌는 전부 실파일에서 라인 단위로 확인한 것이다.

---

## File Classification

### A. Wave-1 수리 3건 (크리티컬 패스 선두)

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `backend/shared/python/sunity_shared/analysis/motion_alignment.py` (modify) | 순수 알고리즘 | transform | 자기 자신 (tier 사다리 :167-180) | exact |
| `app/src/components/VideoCompare.tsx` (modify — 수동 슬라이더 + "대략 맞춤" 배지) | component | streaming(재생 제어) | 자기 자신 (WR-01 warp 경유 지점 :377-383, alignBadgeCopy :921-934) | exact |
| `app/src/lib/alignmentWarp.ts` (modify — 소비 확장 시) | utility | transform | 자기 자신 (warpTime :49-72, normalize :100-166) | exact |
| `app/src/app/analysis/result.tsx` (modify — 겹침 수리·legacy 오프셋 폴백·섹션 재배치) | screen | Firestore 구독 렌더 | 자기 자신 | exact |
| `backend/shared/python/sunity_shared/analysis/fault_zoom.py` (modify — `_side_crop` relaxed 프레이밍 분리) | adapter | file-I/O(PNG 생성) | 자기 자신 (:525-587) | exact |

### B. UI 본체 (요약 카드·번역 레이어·미션 표면)

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `app/src/components/SummaryCard.tsx` (create — D-01 요약 1장) | component | props 렌더 | `ScoreBreakdownSection.tsx` (카드 구조) + `result.tsx` 강사 섹션 :2009-2028 | role-match |
| 감점 카드 재구성 (create — D-08 3단 + D-20 인라인 줌 + 게이지 + 미션; `ScoreBreakdownSection` 승격 또는 신규 `DeductionCard.tsx`) | component | props 렌더 | `ScoreBreakdownSection.tsx` 전체 | exact |
| 목표 게이지 바 (create — D-10, 감점 카드 내) | component | props 렌더(SVG) | `OctagonScore.tsx` :32-61 (dashoffset 게이지) + `result.tsx` SegmentRow 트랙 바 :536-545 | role-match |
| 미션 배지·mode3 기록 갱신 배지 (create — D-10/D-26) | component | props 렌더 | `AccuracyLimitBadge.tsx` 전체 | exact |
| 코치마크 2종 (create — D-07, 첫 1회) | component + lib flag | local state | `AccuracyLimitBadge.tsx`(렌더) + `app/src/lib/onboarding.ts`(1회 플래그) | exact |
| `app/src/theme/typography.ts` (modify — D-05 신규 토큰 bodySm/bodyMd 등) | config(theme) | — | 자기 자신 (dialog* 신설 선례 :34-38) | exact |
| 용어 맵 (create — D-12, 예: `app/src/lib/terminologyMap.ts` + 백엔드 대응 상수) | utility(상수) | — | `app/src/lib/deductionLabels.ts` + `skeleton.py` JOINT_LABEL_KO | exact |
| 코치 질문 목록 강화 (D-28 — `result.tsx` 섹션 확장 또는 `CoachQuestionsSection.tsx` 분리) | component | props 렌더 + 점프 | `result.tsx` :2009-2028 + `userAnalyses.ts` normalizeCoachHook :42-58 | exact |
| 재생 중 자막 큐 (D-18 자막 — `VideoCompare.tsx` 내 큐 트랙) | component | streaming(tick) | `VideoCompare.tsx` tick 루프 :392-453 | exact |
| TTS 큐 모듈 (create — D-18 오디오, 샘플 게이트 후 택1) | lib adapter | streaming | 기기 TTS: 선례 없음(신규 모듈) / Polly: `playback-url/app.py` asset 패턴 | 조건부 |

### C. 문구집·미션 (백엔드 데이터/순수 함수)

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `backend/data/phrasebook.json` (create — D-11 고정 문구집) | data fixture | — | `backend/data/corrective_exercises.json` | exact |
| `backend/shared/python/sunity_shared/analysis/phrasebook.py` (create — 조립 순수 함수) | service(pure) | transform | `exercise_map.py` 전체 | exact |
| `backend/shared/python/sunity_shared/analysis/mission.py` (create — D-19 선정 규칙 + D-27 streak) | service(pure) | transform | `exercise_map.py`(순수성) + `firestore_admin.get_previous_analysis` :1532-1561(prev chain) | role-match |
| `coach_writer.py` (modify — D-11 가변부 슬롯 한정) | adapter(LLM) | request-response | 자기 자신 (graceful :217-279, "주입 실측만" 시스템 프롬프트 :39-41) | exact |

### D. 계약 3면 + 저장 + 앱 소비

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `docs/contract.md` (modify — mission/spotCheck/keypointReport 확장/오디오 asset) | contract 문서 | — | §11 motionAlignment 절 (3-way lockstep 서술 모범) | exact |
| `app/src/types/analysis.ts` (modify) | types(contract) | — | `MotionAlignment` interface :489-508 (주석 관례 포함) | exact |
| `backend/shared/python/sunity_shared/models.py` (modify) | constants(contract) | — | `MOTION_ALIGNMENT_KEYS` 블록 :185-198 | exact |
| `backend/shared/python/sunity_shared/firestore_admin.py` (modify — 신규 scoped validator + 사후 부분 업데이트 helper) | persistence | CRUD | `_validate_motion_alignment` :308-407 + `_validate_safety_flags` :288-305 + `update_analysis_fault_zoom` :1138-1187 | exact |
| `app/src/lib/userAnalyses.ts` (modify — 신규 필드 normalize) | hook(data-source) | Firestore onSnapshot | 자기 자신 (normalizeVisualStatus/normalizeFrameIdx :63-94) | exact |

### E. 엔진 레버 3종 (뒤 웨이브)

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| omni 스팟체크 모듈 (create — 예: `analysis/spot_check.py`) | adapter(외부 API) | request-response | `gemini_vision_scorer.py` (_ensure_client :763-782, PROMPT_VERSION :77, 캐시 규율) | role-match |
| `backend/functions/pipeline/app.py` (modify — 스팟체크 사후 스테이지) | orchestrator | event-driven(SQS) | 자기 자신 (`firestore_complete` :5236 / `fault_zoom` 사후 :5289-5320, `_stage` :122-140) | exact |
| `backend/shared/python/sunity_shared/analysis/keypoint_frame.py` (modify — 8→12) | schema(value object) | — | 자기 자신 (:51-81) | exact |
| `backend/shared/python/sunity_shared/analysis/assemble.py` (modify — `build_keypoint_report` :863 확장) | service | transform | 자기 자신 + `keypoint_frame.py` | exact |
| PR 인버전 보정 (modify — Pod 추론 전처리, `pose_estimator.py` 또는 crop 단계) | adapter(GPU) | transform | spike 산출물 `pr_warp_pod.py` (.planning/spikes/004 디렉터리·Pod 볼륨) | spike-artifact |
| `backend/functions/playback-url/app.py` (modify — Polly 채택 시 오디오 asset 확장) | API lambda | request-response | 자기 자신 `_handle_asset` :77-124 (H-02) | exact |
| `backend/template.yaml` (modify — Polly 채택 시 IAM `polly:SynthesizeSpeech` 1줄) | IaC | — | 기존 함수 정의 블록 | exact |

### F. 테스트 (Wave 0)

| New File | Role | Closest Analog | Match |
|---|---|---|---|
| `backend/tests/phase32/conftest.py` (create) | test scaffold | `backend/tests/phase31/conftest.py` :36-41(sys.path) + :346-370(fake_firestore) | exact |
| `backend/tests/phase32/test_motion_alignment_ladder.py` | unit | `backend/tests/test_motion_alignment.py` + `test_motion_alignment_contract.py` (기존 방출/lockstep 테스트) | exact |
| `backend/tests/phase32/test_fault_zoom_crop_parity.py` | unit | `backend/tests/test_fault_zoom_relaxed_crop.py` (relaxed crop 전용 기존 테스트) | exact |
| `backend/tests/phase32/test_phrasebook_forbidden.py` | unit(grep 게이트) | `backend/tests/phase07/test_copy_templates_no_forbidden.py` (AST 게이트) | exact |
| `backend/tests/phase32/test_mission_rules.py` | unit | 순수 함수 테스트 관례 + phase31 fake_firestore | role-match |
| `backend/tests/phase32/test_keypoint_report_expansion.py` | unit | 기존 `test_assemble.py`/KeypointReport validator 테스트 | role-match |
| `app/src/lib/__tests__/manualOffset.test.ts` | unit(node --test) | `app/src/lib/pickerFailure.test.ts` | exact |

---

## Pattern Assignments

### A-1. `motion_alignment.py` — 사다리 재배치 (D-16 수리 본체)

**Analog:** 자기 자신. 수정 지점과 보존 대상이 명확하다.

**수리 대상 분기** (`motion_alignment.py:167-180`) — else 분기를 `trim_only` 로 바꾸되 reason 은 유지:
```python
reason = None
if distance <= DISTANCE_T1 and slopes_ok:
    tier = "warped"
elif distance <= DISTANCE_T2:
    tier = "trim_only"
    if not slopes_ok:
        reason = "rate_clamp_exceeded"
    elif length_extreme:
        reason = "length_extreme"
    else:
        reason = "low_global_confidence"
else:
    tier = "disabled"                     # ← 수리: trim_only + reason 으로 방출 (anchors 보존)
    reason = "low_global_confidence"
```

**보존해야 할 degenerate 경로** (`motion_alignment.py:47-62`, `:90-95`, `:147-148`) — `disabled` 는 이후 진짜 degenerate 3종에만 남는다:
```python
def _disabled(distance: float, reason: str) -> dict:
    return {
        "version": MOTION_ALIGNMENT_VERSION,
        "source": "dtw",
        "tier": "disabled",
        "reason": reason,
        "anchors": [],          # 빈 anchors 는 disabled 만 허용 (validator 역불변식)
        "anchorCount": 0,
        "distance": float(distance),
    }
# 호출처: invalid_fps(:91) / empty_path(:95) / insufficient_anchors(:148) — 이 3곳만 유지
```

**모듈 헤더 관례** (`motion_alignment.py:1-22`): 목적 + fps 도메인 함정 + 임계 출처(calibration-source-hard-gate) + 채점 무접촉 선언을 docstring 에 명시. 수정 시 이 docstring 에 32 결정(D-16) 각주를 추가하는 방식을 따를 것.

**계약 무변경 근거:** tier enum 에 `trim_only` 가 이미 있고(`models.py:196` `MOTION_ALIGNMENT_TIERS`), validator(`firestore_admin.py:389-393`)는 `trim_only` 에 anchors ≥ 2쌍만 요구 — else 분기도 pairs ≥ 2 를 이미 통과한 상태라 그대로 성립한다.

---

### A-2. `VideoCompare.tsx` — 수동 ±초 슬라이더 + 배지 카피 교체

**Analog:** 자기 자신. 슬라이더의 삽입 지점이 코드 주석으로 이미 지정돼 있다.

**warp 목표시각 단일 경유 지점** (`VideoCompare.tsx:366-383`) — `manualOffsetSec` 는 반드시 여기서만 합성:
```ts
// WR-01 — 정렬 활성 경로에서만 warp 목표시각을 [0, dR] 로 클램프. ...
const clampRefTarget = (tStudent: number, dR: number): number => {
  const a = alignmentRef.current;
  const raw = a && a.tier !== 'disabled' ? warpTime(a, tStudent) : tStudent;
  if (!a || a.tier === 'disabled') return raw; // legacy identity — 무클램프
  return dR > 0 ? Math.max(0, Math.min(raw, dR)) : Math.max(0, raw);
};
// right 쓰기의 유일한 warp 경유 지점 (MEDIUM-1 코드 형태 규율) — 정렬 활성 경로의
// rightPlayer.currentTime 대입은 전부 여기로 격리, 비활성 시 identity 라 legacy 동일.
const setRightToStudentTime = (tStudent: number) => {
  if (rightPlayer) {
    rightPlayer.currentTime = clampRefTarget(tStudent, rightPlayer.duration ?? 0);
  }
};
```
→ 32 수리: `clampRefTarget` 내부에서 `raw + manualOffsetSec` 후 클램프. drift 보정 tick(:436-440)·togglePlay·seek 가 전부 이 함수를 경유하므로 자동 반영된다 (RESEARCH §수리 #1-3 정합).

**ref 미러 패턴** (`VideoCompare.tsx:352-356`) — 슬라이더 상태도 동일하게 tick 클로저에서 읽도록 ref 미러 필수:
```ts
// 최신 alignment 를 tick(setInterval 클로저)이 읽도록 ref 미러 — alignment 는 매
// 렌더 새 객체라 effect deps 에 넣으면 interval 재설치 churn. ref 로 stale 클로저 회피
const alignmentRef = useRef(alignment);
alignmentRef.current = alignment;
```

**배지 카피 분기** (`VideoCompare.tsx:921-934`) — "자동 정렬 꺼짐" 폐지·"대략 맞춤" 신설 지점:
```ts
const alignBadgeCopy: { title: string; hint: string } | null = !alignment
  ? null
  : alignment.tier === 'warped'
    ? { title: '자동 구간 맞춤', hint: '동작 기준으로 자동 구간을 맞췄어요' }
    : alignment.tier === 'trim_only'
      ? { title: '자동 구간 맞춤', hint: '동작 차이가 있어 시작점만 맞췄어요 (배속 조정은 꺼짐)' }
      : { title: '자동 정렬 꺼짐', hint: '기준 동작과 차이가 커 자동 정렬을 껐어요' };
```
→ 32 수리: `tier === 'trim_only' && reason === 'low_global_confidence'` 분기를 "대략 맞춤" 정직 라벨로 추가. 수치(DTW distance) 비표기 원칙(:922-924 주석) 유지 — D-09 와 정합.

**자막 큐 삽입 지점**: tick 루프(:392-453)가 100ms 간격으로 `cL`(학생 currentTime)을 이미 계산한다. 큐 트랙은 이 tick 에서 `cL ∈ 결함구간` 판정 → 오버레이 state 갱신으로 구현 (신규 타이머 금지 — 기존 tick 재사용).

---

### A-3. `result.tsx` — 겹침 수리 + legacy 오프셋 폴백 + 재배치

**Analog:** 자기 자신.

**겹침 버그 스타일** (`result.tsx:2545-2550`) — 수리 지점 그 자체:
```ts
diagSentence: {
  ...typography.body,      // fontSize 25 상속
  color: colors.textPrimary,
  lineHeight: 21,          // ← fontSize(25) > lineHeight(21) = 다중 행 줄겹침. lineHeight ≥ 33 또는 작은 토큰으로
  marginTop: 6,
},
```
렌더 소비처는 `DimensionDiagnosisRow`(:508-533, '동작 흐름'/'안정성' 장문 렌더). D-03 에 따라 wave-1 은 최소 수리만.

**legacy doc 오프셋 폴백 재료** (`result.tsx:855-858` + `analysis.ts:473-487`):
```ts
const compareFrames = useMemo(
  () => pickCompareFrames(result.faultZoomComparisons),
  [result.faultZoomComparisons],
);
```
```ts
// analysis.ts:484-486 — 31-03 이 방출한 DTW 대응 프레임 쌍 (kr 프레임 공간)
userFrameIdx?: number;
refFrameIdx?: number;
refMatched?: boolean;
```

**fps 환산 정본** (`result.tsx:2105-2135`, Pitfall 2 — 하드코딩 9/18 금지, 각자의 `report.fps` 로만):
```ts
timeSec: compareFrames.userIdx / (result.keypointReport?.fps || 9),
...
timeSec: compareFrames.refIdx / (referenceKeypointReport?.fps || 18),
```
→ legacy 오프셋: `offset ≈ refFrameIdx/refKr.fps − userFrameIdx/userKr.fps` 를 같은 패턴으로 산출.

**섹션 카드 렌더 관례** (`result.tsx:2009-2028` 강사에게 확인할 점 — SummaryCard·코치 질문 목록이 복제할 형태):
```tsx
{openQuestionsForCoach.length > 0 && (
  <>
    <Text style={styles.sectionTitle}>강사에게 확인할 점</Text>
    <Text style={styles.coachSectionSub}>아래 질문을 강사와 함께 확인해보세요.</Text>
    <View style={[styles.card, styles.coachCard]}>
      {openQuestionsForCoach.map((q, i) => (
        <View key={`${q}-${i}`} style={styles.coachQuestionRow}>
          <Ionicons name="chatbubble-ellipses-outline" size={16} color={colors.brand} />
          <Text style={styles.coachQuestionText}>{q}</Text>
        </View>
      ))}
    </View>
  </>
)}
```

**재배치 invariant** (`result.tsx:2082-2088`) — 참고코너는 채점 표면 뒤 유지 (31 D-09, RESEARCH 순서안 #10):
```tsx
{/* ── Phase 31 (D-09): "참고하세요" 참고코너 ─── 배치 = 보완 운동 **아래** ...
    채점 관련 표면(점수카드·감점 내역·보완 운동)을 전부 지난 뒤에 오므로
    "점수 비반영"이 레이아웃만 봐도 드러난다 — 위로 올리면 비채점 생성물이
    채점 근거처럼 읽힌다. */}
<ReferenceCornerSection ... />
```

---

### A-4. `fault_zoom.py` — relaxed 프레이밍 분리 (D-20 수리)

**Analog:** 자기 자신. 상수 `_BBOX_MARGIN = 1.8`(:86), `_RELAXED_MARGIN = 2.0`(:95).

**수리 지점** (`fault_zoom.py:558-587`):
```python
def _box_for(pts: list[tuple[float, float]], margin: float):
    ...
    floor_side = int(round(min(h, w) * _CROP_FRAC))
    side = floor_side
    if len(pts) > 1:
        bbox_side = max(max(xs) - min(xs), max(ys) - min(ys))
        side = max(floor_side, int(round(bbox_side * _BBOX_MARGIN * margin)))
    return _crop_box(h, w, cx, cy, side)

if valid_pts:
    left, top, s = _box_for(valid_pts, 1.0)          # 내 자세: 1.8배
    ...
    return _render_crop(frame, left, top, s), "valid", anchor_px, (left, top, s)
if relaxed_pts:
    left, top, s = _box_for(relaxed_pts, _RELAXED_MARGIN)   # ← 수리: margin 1.0 으로 (프레이밍 양측 동일 배율)
    return _render_crop(frame, left, top, s), "relaxed", None, (left, top, s)
    #                                          ^^^^^^^^^ crop_kind="relaxed" 유지 → 마커(anchor) 생략 게이트는 현행대로
return _full_frame_fit(frame), "full", None, None
```
분리 원칙(메모리 박제 그대로): 프레이밍은 좌표 오차 둔감 → 양측 1.8배 통일, 마커는 민감 → relaxed 는 anchor_px=None 유지. display 전용 — 채점·veto 무접촉. 새 분석부터 적용(재처리 금지).

---

### B-1. 감점 카드 재구성 — `ScoreBreakdownSection.tsx` 가 정본 아날로그

**Analog:** `app/src/components/ScoreBreakdownSection.tsx` (렌더 diff 0 원칙의 opt-in prop 확장 모범).

**opt-in prop 확장 패턴** (`ScoreBreakdownSection.tsx:31-55`) — 3단 문장·게이지·미션·줌 인라인을 추가할 때 이 방식(미전달 시 렌더 diff 0)을 복제:
```ts
export function ScoreBreakdownSection({
  breakdown,
  recordNumbers,   // 미전달 시 렌더 diff 0 (다른 소비처/legacy 무회귀)
  basisLine,       // null/미전달 시 생략
  limitNotice,     // 미전달 시 렌더 diff 0 (mode1 호출부 무변경)
  onRecordPress,   // 전달 시에만 행을 Pressable 로 감쌈
}: { ... })
```

**record 행 + 드릴다운 진입** (`ScoreBreakdownSection.tsx:114-129`) — D-15 드릴다운 시트 연결 그대로 재사용:
```tsx
return onRecordPress ? (
  <Pressable
    key={`${rec.criterion}-${i}`}
    style={styles.row}
    onPress={() => onRecordPress(i)}
    accessibilityRole="button"
    accessibilityLabel={`${row.label} 감점 상세 보기`}
    hitSlop={4}
  >
    {inner}
  </Pressable>
) : ( ... );
```

**카드 스타일 정본** (`ScoreBreakdownSection.tsx:169-176`) — 신규 카드(SummaryCard 포함) 공통:
```ts
card: {
  backgroundColor: colors.cardBg,
  borderRadius: radius.card,
  borderWidth: layout.cardBorderWidth,
  borderColor: colors.divider,
  padding: spacing.cardPadding,
  gap: 12,
},
```

**정직 고지 각주 패턴** (`ScoreBreakdownSection.tsx:150-159`) — D-29 부분 실패 커버리지 고지가 복제할 형태:
```tsx
{gapCount > 0 && (
  <Text style={styles.footnote}>
    {`측정하지 못해 점수에 반영하지 않은 항목이 ${gapCount}건 있어요.`}
  </Text>
)}
```

**문구집 키 소스** (`analysis.ts:523-534` DeductionRecord — 문구집 키는 이 실존 방출값으로만):
```ts
export interface DeductionRecord {
  criterion: string;
  ...
  ruleId: string;
  points: number; // SIGNED NEGATIVE (감점). final = max(0, round(100 + Σ points)).
  unit: 'deg' | 'notch' | 'score_delta';
  ipsfAnchor: string;
  source: 'geometry' | 'vision';
  ...
}
```

---

### B-2. 게이지·배지 — SVG 선례 2종

**Analog 1 — 진행 게이지** (`OctagonScore.tsx:32-61`, react-native-svg dashoffset 방식. 신규 차트 lib 금지):
```tsx
const clamped = Math.max(0, Math.min(100, Math.round(score)));
const dashOffset = PERIMETER * (1 - clamped / 100);
...
<Polygon points={POINTS} fill="none" stroke="url(#octaScoreGrad)"
  strokeWidth={STROKE} strokeDasharray={PERIMETER} strokeDashoffset={dashOffset} />
```
D-10 게이지 바는 선형이므로 `result.tsx` SegmentRow 의 트랙+채움 View 방식(:536-545, `styles.track` 안에 비율 width)이 더 단순한 1차 후보 — SVG 는 눈금/목표 마커가 필요할 때만.

**Analog 2 — 배지 컴포넌트 전형** (`AccuracyLimitBadge.tsx:26-46`) — 미션 배지·기록 갱신 배지·소형 수치 신뢰 배지(D-09)가 복제할 형태:
```tsx
const LINE_OCCLUSION = '가림 구간 정확도가 제한적이에요';   // 카피 상수 분리 (변경 시 스펙 동시 갱신 주석)

interface AccuracyLimitBadgeProps { visible: boolean; }    // caller 파생 boolean 만 받음

export function AccuracyLimitBadge({ visible }: AccuracyLimitBadgeProps) {
  if (!visible) return null;                               // 조건 미충족 = null 반환 (자체 숨김)
  return (
    <View style={styles.container} accessibilityRole="alert"
      accessibilityLabel={`${LINE_OCCLUSION}. ${LINE_SIDE}`}>
      ...
    </View>
  );
}
```
스타일은 전부 토큰 참조(`:48-72` — `colors.warnAmber`/`radius.card`/`spacing.screenX`/`typography.boxLabel`). 하드코딩 금지.

---

### B-3. 코치마크 (D-07) — 첫 1회 플래그

**Analog:** `app/src/lib/onboarding.ts` 전체 (AsyncStorage 1회 플래그, 실패 방향까지 규정):
```ts
const TUTORIAL_SEEN_KEY = '@sunity:tutorial_seen';   // '@sunity:' prefix 필수 — Firebase Auth namespace 충돌 회피

export async function hasSeenTutorial(): Promise<boolean> {
  try {
    const v = await AsyncStorage.getItem(TUTORIAL_SEEN_KEY);
    return v === 'true';
  } catch {
    return true;   // graceful: 읽기 실패 = "본 것으로 간주" (재노출 루프 방지)
  }
}

export function markTutorialSeen(): void {
  AsyncStorage.setItem(TUTORIAL_SEEN_KEY, 'true').catch(() => {
    /* graceful — 쓰기 실패해도 현재 세션은 이미 진행 */
  });
}
```
→ 코치마크는 `@sunity:result_coachmark_seen` 류 키로 동일 구조 lib helper 신설. 화면은 helper 경유만(데이터소스 격리 원칙, 파일 헤더 :4-7).

---

### B-4. 타이포 토큰 (D-05)

**Analog:** `app/src/theme/typography.ts` 자기 자신 — 토큰 신설 선례가 이미 있다 (:30-38):
```ts
// ── quick-260720-hn8 신설 (Figma node 1:499 `Group 53` 실측) ────────────
// letterSpacing 만 위 박제 규칙에 따라 0 — 음수 letterSpacing 은 iOS 26+ SIGABRT라 적용 금지.
dialogTitle: { fontSize: 18, fontWeight: '700', lineHeight: 25, letterSpacing: track(18) },
dialogBody: { fontSize: 13, fontWeight: '400', lineHeight: 23, letterSpacing: track(13) },
```
→ 신규 토큰(bodySm 17/bodyMd 19 등)도 같은 형태: **lineHeight 를 fontSize 이상으로 명시**(Pitfall 3 방지), `track()=0` 유지(음수 letterSpacing 금지 :2-6), `as const`. 전역값 상향이 아니라 결과 화면용 단계 추가(RESEARCH 옵션 b).

---

### B-5. 용어 맵 (D-12)

**Analog:** `app/src/lib/deductionLabels.ts` — 단일 출처 상수 맵 + cross-side 계약 주석 관례.

**단일 출처 선언 + 이중 키 공간 커버** (`deductionLabels.ts:28-42`):
```ts
// 관절 한국어 라벨 — keypoint 이름(left_hand 등)과 kismam angle key(left_elbow 등)
// 양쪽 키 공간을 한 맵으로 커버 (중복 2벌 금지 — 드릴다운 시트가 import).
export const JOINT_LABEL_KO: Record<string, string> = {
  left_shoulder: '왼쪽 어깨', ...
};
```

**"측정 용어 → 사람 말" 기존 층** (`deductionLabels.ts:62-71` — 용어 맵의 직접 전신):
```ts
export const ANGLE_MEANING_KO: Record<string, string> = {
  left_elbow: '팔꿈치 굽힘', ... left_hip: '다리 벌림', ... left_knee: '무릎 굽힘',
};
```

**cross-side 계약 주석 관례** (`deductionLabels.ts:108-110` — 백엔드 대응표와의 lockstep 을 주석으로 박제):
```ts
// **cross-side 계약:** 이 표는 29-03 backend zoom region 파생 표
//   (_build_mode3_fault_zoom_comparisons)와 항목 동일해야 한다 (측당 1벌).
export const CRITERION_REGION_KEYPOINTS: Record<string, readonly KeypointName[]> = { ... };
```
백엔드 대응 = `skeleton.py:53-62` `JOINT_LABEL_KO`. 용어 맵은 이들의 교체가 아니라 상위 매핑(측정 용어→심사 언어) 신설 — 양측에 같은 리터럴 + lockstep 주석 + (권장) phase32 테스트로 drift 차단.

---

### C-1. 문구집 fixture + 조립 함수 (D-11)

**Analog:** `exercise_map.py` + `backend/data/corrective_exercises.json`.

**fixture 경로/lazy 캐시** (`exercise_map.py:29-84`):
```python
_CORRECTIVE_EXERCISES_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "data" / "corrective_exercises.json"
)
_CORRECTIVE_EXERCISES_CACHE: dict | None = None

def _load_corrective_exercises() -> dict:
    global _CORRECTIVE_EXERCISES_CACHE
    if _CORRECTIVE_EXERCISES_CACHE is None:
        _CORRECTIVE_EXERCISES_CACHE = json.loads(
            _CORRECTIVE_EXERCISES_PATH.read_text(encoding="utf-8")
        )
    return _CORRECTIVE_EXERCISES_CACHE
```

**순수성 선언 + 출력 형상** (`exercise_map.py:7-17` 모듈 docstring — phrasebook.py 헤더가 복제할 문구):
```python
순수성 (Layer 2 boto3 영구 차단):
  - numpy/AWS-free, network-free. 단위 test 로 전부 검증.
  - 입력은 plain dict / list[str] / str|None, 출력은 plain camelCase scalar dict
    (dataclass 아님 — Firestore 가 그대로 저장).
3-way contract lockstep: TS analysis.ts ↔ models.py ↔ docs/contract.md
```

**graceful 소비 + fabrication 금지** (`exercise_map.py:120-128`, `:220-224`):
```python
# 알 수 없는 keypoint_set 값은 조용히 skip (graceful — enum drift 시 크래시 0).
...
if not deduped:
    return []
# 3~5 cap. 후보가 3 미만이면 있는 만큼만 (fabrication 금지).
return deduped[:_MAX_EXERCISES]
```

**문구집 키 설계:** RESEARCH 확정 — 동작 × `DeductionRecord.criterion`/`ruleId` → {상태문, 이유문, 행동문(외부 큐), 코치질문 완성문(D-28), 운동 연결 이유(D-13)}. 키는 반드시 실존 방출값과 대조(31 화살표 함정 §6-5 재발 방지).

**canned 문자열 구조 선례** (`copy_templates.py:95-107` — 톤 룰 포함 dict literal):
```python
_COPY_TEMPLATES: dict[tuple[str, Category, JointGroup], tuple[str, str]] = {
    ("knee_toe_alignment", "body_type_allowed", "leg"): (
        "다리 길이 비율 차이로 무릎-발끝 정렬에 작은 차이가 보일 수 있어요.",
        "지금 자세는 체형 범위 안에서 자연스러워 보이네요. ...",
    ),
    ...
}
```
graceful fallback(`copy_templates.py:304-316`): 키 미발견 시 generic 카피 + WARNING log — 크래시 금지.

---

### C-2. 금지어 grep 게이트 (D-09/D-11)

**Analog 1 — 금지어 튜플** (`copy_templates.py:247-265`):
```python
FORBIDDEN_PHRASES: tuple[str, ...] = (
    "프로보다 못합", "정답 자세가 아닙", "근육량이 부족",
    "체형이 안 맞", "대회 총점", "감점입니다",
)
FORBIDDEN_PHRASES_SUNITY: tuple[str, ...] = (
    "박제",   # [[no-baekje-filler]]
    "%일치",  # [[mode3-progress-not-similarity]]
    "유사도",
)
```
→ 32 확장: D-09 위반 패턴(수치 헤드라인·% 환산) 추가. 문구집이 JSON fixture 라면 게이트는 AST 가 아니라 JSON 순회로 단순화된다(모든 string 값 iterate).

**Analog 2 — AST 게이트 테스트** (`backend/tests/phase07/test_copy_templates_no_forbidden.py:72-91`):
```python
@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES + FORBIDDEN_PHRASES_SUNITY)
def test_no_forbidden_phrase_in_copy_templates(phrase: str) -> None:
    strings = _extract_template_strings()
    violations = [(s, ln) for s, ln in strings if phrase in s]
    assert not violations, f"금지 표현 {phrase!r} 발견: {violations}"

def test_ast_gate_extracts_strings() -> None:
    """sanity: 추출이 string 을 실제로 발견하는지 (0-string 게이트 무의미 회귀 차단)."""
    strings = _extract_template_strings()
    assert len(strings) >= 66, ...
```
sanity 테스트(추출 0건 = 게이트 무의미)를 반드시 함께 복제할 것.

---

### C-3. LLM 가변부 (D-11) — `coach_writer.py` graceful 패턴

**Analog:** 자기 자신 (수정 대상이자 패턴 원본).

**키 로드 + graceful 초기화** (`coach_writer.py:47-60`, `:217-229`):
```python
def _load_api_key() -> str | None:
    param_name = os.environ.get("CEREBRAS_KEY_PARAM")
    if not param_name:
        return None
    try:
        import boto3  # Lambda 런타임 제공
        ssm = boto3.client("ssm")
        return ssm.get_parameter(Name=param_name, WithDecryption=True)["Parameter"]["Value"]
    except Exception:  # noqa: BLE001
        log.exception("Cerebras 키 로드 실패")
        return None
# __init__: api_key 없으면 self._client = None → write() 가 {} 반환, assemble 폴백
```

**전체 실패 시 골격 성립 원칙** (`coach_writer.py:246-279`):
```python
if self._client is None:
    return {}
...
except Exception:  # noqa: BLE001
    log.exception("Cerebras 코칭 생성 실패 — 수치 폴백 사용")
    return {}
```
→ 32 원칙: LLM 이 {} 를 반환해도 문구집 골격만으로 감점 카드 3단이 성립해야 한다. 시스템 프롬프트의 "주입된 실측 데이터만, 임의 수치 생성 금지"(:39-41)는 유지·강화.

---

### C-4. 미션 선정·streak (D-19/D-26/D-27)

**Analog 1 — 순수 함수 형태:** `exercise_map.map_exercises`(:141-224) — plain dict 입출력, 우선순위 병합(:183-198 의 (1)→(4) ordered 병합), dedup, cap. 미션 규칙도 동일 형태: `select_mission(deduction_breakdown, safety_flags, prev_mission) -> dict` 순수 함수 + 우선순위 ①안전 ②반복 미개선 ③감점 최대.

**Analog 2 — prev chain 읽기** (`firestore_admin.py:1532-1561`):
```python
def get_previous_analysis(uid: str, current_id: str, mode: str | None = None) -> dict | None:
    """Mode3 비교용: 가장 최근 완료(done) 분석 1건 (현재 건 제외).
    query 는 status + createdAt 만 (기존 index) — mode 는 in-memory filter."""
    col = _db().collection(f"users/{uid}/analyses")
    q = (col.where("status", "==", models.STATUS_DONE)
         .order_by("createdAt", direction=firestore.Query.DESCENDING)
         .limit(20))
    for snap in q.stream():
        if snap.id == current_id:
            continue
        data = snap.to_dict() or {}
        if mode is not None and data.get("mode") != mode:
            continue
        data.setdefault("analysisId", snap.id)
        return data
    return None
```
→ streak 는 doc 체인 전파(직전 1건의 `mission.streak` + 1) — 신규 쿼리/컬렉션/인덱스 0. composite index 함정 주석(:1541-1543) 준수: 신규 where 절 추가 금지.

---

### D-1. 계약 3면 + scoped validator + normalize 대칭 (신규 필드 전부)

미션 오브젝트·spotCheck 플래그·keypointReport 12관절·오디오 key 전부 이 4중 대칭을 따른다. 정본 선례 = motionAlignment 1건이 4면을 전부 갖췄다.

**(1) models.py 상수 블록** (`models.py:193-198` — 신규 키도 같은 형태 + lockstep 주석):
```python
# 3-way lockstep: app/src/types/analysis.ts MotionAlignment + docs/contract.md §11.
MOTION_ALIGNMENT_KEYS = (
    "version", "source", "tier", "reason", "anchors", "anchorCount", "distance",
)
MOTION_ALIGNMENT_TIERS = ("warped", "trim_only", "disabled")
MOTION_ALIGNMENT_SOURCES = ("dtw", "vlm")
MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS = 512
```

**(2) analysis.ts interface** (`analysis.ts:489-508` — 하위호환 서술 관례 포함):
```ts
// (b) 부재(legacy doc) = 현행 절대시계 동작 (하위호환, tier? 선례와 동일 규칙 — no migration).
// (d) Python lockstep: models.py MOTION_ALIGNMENT_KEYS + docs/contract.md §11.
export interface MotionAlignment {
  version: string;
  source: 'dtw' | 'vlm';
  tier: 'warped' | 'trim_only' | 'disabled';
  reason?: string;
  anchors: number[];      // flat [u0,r0, ...] ([[firestore-nested-array-flat]])
  anchorCount: number;    // reshape 메타 — anglesFrames 선례
  distance: number;
}
```

**(3) 백엔드 scoped validator** (`firestore_admin.py:308-345` 발췌 — 신규 `_validate_mission`/`_validate_spot_check` 가 복제할 뼈대):
```python
def _validate_motion_alignment(payload, *, path: str = "motionAlignment") -> None:
    """... `result['motionAlignment']` 단일 persistence path 전용 — complete_analysis 에 신규
    kwarg 없음 (safetyFlags 선례, "result 안으로 흐른다"). None/부재 graceful(legacy doc)."""
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(...)
    extra = set(payload) - set(models.MOTION_ALIGNMENT_KEYS)   # 키 화이트리스트
    if extra:
        raise ValueError(f"{path}: 화이트리스트 밖 키 {sorted(extra)}")
    tier = payload.get("tier")
    if tier not in models.MOTION_ALIGNMENT_TIERS:              # enum 강제
        raise ValueError(f"{path}.tier 미등재값: {tier!r}")
    ...
    if not _math_kr.isfinite(distance):                        # finite 강제
        raise ValueError(f"{path}.distance 는 finite 여야 함")
```
list[dict] 형 신규 필드는 `_validate_safety_flags`(:288-305) 형태 — 각 항목을 `_validate_dict_only_scalars` 로 라우팅, **generic validator 본체 무수정**.

**(4) 앱 normalize 방어 파싱** (`userAnalyses.ts:63-94` — 신규 필드용 헬퍼가 복제할 3종):
```ts
const VISUAL_STATUSES = ['pending', 'done', 'failed'] as const;
function normalizeVisualStatus(value: unknown): VisualStatus | undefined {
  return VISUAL_STATUSES.includes(value as VisualStatus) ? (value as VisualStatus) : undefined;
}
// S3 key 방어: 결과물 key 는 반드시 `results/` prefix. 그 외는 undefined 강등 (H-02)
function normalizeResultKey(value: unknown): string | undefined {
  return typeof value === 'string' && value.startsWith('results/') ? value : undefined;
}
// 배열 인덱스로 쓰이므로 음수/소수/NaN 전부 거부.
function normalizeFrameIdx(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : undefined;
}
```
원칙(:60-62 주석): "임의 값은 undefined 로 조용히 강등하고, 필드를 drop 하지는 않는다 (부재 = legacy doc 하위호환)."

---

### E-1. omni 스팟체크 (D-22/D-23) — 사후 스테이지 + lazy client

**Analog 1 — 사후 분리 스테이지** (`pipeline/app.py:5236-5320`). 스팟체크는 fault_zoom 과 같은 자리(status='done' 확정 이후)에 신규 `with _stage(...)` 블록으로 삽입:
```python
result["timingsMs"] = timings_ms
with _stage(timings_ms, analysis_id, "firestore_complete"):  # Phase 27 SPD-01 — 여기서 status='done'
    firestore_admin.complete_analysis(uid, analysis_id, result, ...)
log.info("분석 완료 uid=%s analysis_id=%s mode=%s", uid, analysis_id, mode)
...
# Phase 27 SPD-04 (D-06) — fault_zoom 사후 렌더. complete_analysis 로 점수/verdict 확정
# 뒤(status='done'), zoom PNG 를 렌더해 update_analysis_fault_zoom(done/failed) 부분
# 업데이트로 도착시킨다. **분석 간 SERIAL 불변** — 다음 분석은 이 BackgroundTask
# 종료(finally) 후에만 시작하므로 별도 태스크 불필요.
if fault_zoom_kind is not None:
    with _stage(timings_ms, analysis_id, "fault_zoom"):
        ...
        _run_deferred_fault_zoom(render=_zoom_render, uid=uid, analysis_id=analysis_id)
```
`_stage` 컨텍스트 매니저(:122-140): try/finally 로 elapsed 기록 + `stage_timing analysis_id=%s stage=%s elapsed_ms=%d` 구조 로그. 스팟체크 스테이지도 동일하게 감싼다 — "동기 경로 신규 외부 호출 금지" 예산을 구조로 지킴.

**Analog 2 — 사후 부분 업데이트 쓰기** (`firestore_admin.py:1138-1187` `update_analysis_fault_zoom` — 스팟체크 플래그 쓰기 helper 가 복제):
```python
if status not in models.FAULT_ZOOM_STATUSES:
    raise ValueError(...)
for i, c in enumerate(_comparisons):
    _validate_dict_only_scalars(c, path=f"faultZoomComparisons[{i}]")   # validator 본체 무수정 재사용
_doc(models.analysis_doc_path(uid, analysis_id)).update(
    {
        "result.faultZoomComparisons": _comparisons,   # 해당 필드만 field-path 부분 갱신
        "result.faultZoomStatus": status,              # 그 외 result.* 사후 변경 금지 (D-03 경계)
        "updatedAt": int(time.time() * 1000),
    }
)
```

**Analog 3 — lazy client 싱글톤** (`gemini_vision_scorer.py:161-162`, `:763-782`):
```python
# 모듈 캐시 싱글톤 (recognizer 패턴) — _ensure_client() 가 1회만 client 생성.
_CLIENT = None

def _ensure_client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    try:
        from google import genai  # lazy — top-level import 금지(D-16)
        api_key = _load_api_key()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY 부재")
        _CLIENT = genai.Client(api_key=api_key)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Gemini client 생성 실패: {exc}") from exc
    return _CLIENT
```
모델 ID env 주입 선례(:104): `DEFAULT_VISION_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")` — 스팟체크 모델도 env 로 (omni 스모크 실패 시 3.1-pro 폴백, RESEARCH A1). 프롬프트 캐시 규율(:77 주석): 프롬프트 문자열 변경 = `PROMPT_VERSION` bump (캐시 무효화, Pitfall 8).

---

### E-2. RTMW 측정층 확장 (D-22 1단)

**Analog:** `keypoint_frame.py:51-81` — 확장의 단일 출처. 두 이름공간을 절대 혼동하지 말 것(Pitfall 1):

```python
_KEYPOINT_NAMES: tuple[KeypointName, ...] = (
    "left_shoulder", "right_shoulder", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_hand", "right_hand",
)   # ← 좌표 표시층 8개. 확장 = +left/right_ankle, +left/right_elbow → 12

NUM_KEYPOINTS_PHASE12: int = len(_KEYPOINT_NAMES)   # 파생값 — len() 이므로 자동 추종

JOINT_KEY_TO_ANGLE_KEY: dict[str, str] = {
    ...,
    "left_hand": "left_wrist",    # COCO-17 키로 loose 매핑 — ankle/elbow 는 1:1 추가
    "right_hand": "right_wrist",
}
```
각도 측정층은 별개(`skeleton.py:39-48` `JOINT_ANGLES` 8관절 — 팔꿈치2·어깨2·엉덩이2·무릎2; 무릎 각이 발목 키포인트를 이미 소비 = 데이터 실존 증거). 확장 절차의 lockstep 대상: `KeypointReport` validator(len==8 강제부), `firestore_admin._validate_keypoint_report`(:716), `assemble.build_keypoint_report`(:863), 계약 3면, 앱 소비처의 하드코딩 8 검사 전수 grep. 앱 라벨은 `deductionLabels.JOINT_LABEL_KO` 에 ankle 라벨 추가.

---

### E-3. 오디오 asset (D-18 클라우드 채택 시) — H-02 패턴

**Analog:** `playback-url/app.py::_handle_asset`(:77-124) — 서버가 key 구성 + exact 비교:
```python
def _handle_asset(uid: str, analysis_id: str, asset: str) -> dict:
    """asset 재서명 — 서버가 key 를 **구성**하고 저장 key 와 exact 비교 (M2-01).
    클라이언트는 asset 종류만 고르고 key 는 절대 보내지 않는다(H-02/H-05)."""
    doc = firestore_admin.get_analysis(uid, analysis_id) or {}
    result = doc.get("result") if isinstance(doc.get("result"), dict) else {}
    ...
    expected = f"results/{uid}/{analysis_id}/rotation.mp4"   # 서버 구성 canonical key
    guards_ok = (
        status == models.VISUAL_STATUS_DONE       # failed/pending/부재 = stale key 여도 404
        and expected is not None
        and isinstance(stored, str)
        and stored == expected                    # exact equality — prefix 부분일치 불가
    )
    if not guards_ok:
        return responses.error("not_found", "시각 교정물을 찾을 수 없어요.", status=404)
    url = _sign_get(expected, expires=_ASSET_EXPIRES, content_type=_ASSET_CONTENT_TYPE[ext])
```
→ 오디오 확장: `models.VISUAL_JOB_KINDS` 류 enum 에 audio 종류 추가 + `results/{uid}/{analysisId}/coach_audio.mp3` canonical + `_ASSET_CONTENT_TYPE` 에 `"mp3": "audio/mpeg"`. 기존 경로 바이트 불변 원칙(:192-193 주석) 유지. 앱 측 key 방어는 `userAnalyses.normalizeResultKey`(`results/` prefix 강등) 재사용.

---

### F-1. 백엔드 테스트 스캐폴드

**Analog:** `backend/tests/phase31/conftest.py`.

**sys.path 주입 관례** (:36-41):
```python
_BACKEND = Path(__file__).resolve().parents[2]
_LAYER = _BACKEND / "shared" / "python"
_SCRIPTS = _BACKEND / "scripts"
for _p in (_BACKEND, _LAYER, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
```

**fake_firestore fixture** (:346-370) — 미션 streak/스팟체크 플래그 쓰기 테스트에 그대로 재사용 가능 (`firestore_admin` seam 5종을 in-memory 로 patch, `_apply_update` 가 field-path `.update()` 의 교체 의미까지 재현 :81-96). phase32 conftest 는 phase31 것을 import 하거나 필요한 fixture 만 복제.

**실행 관례:** `cd backend && python -m pytest tests/phase32 -x -q` (RESEARCH Validation Architecture). 전체 suite 는 baseline diff 비교(57 failed/3366 passed 초과 금지).

---

### F-2. 앱 순수 로직 테스트 (node --test)

**Analog:** `app/src/lib/pickerFailure.test.ts`.

**헤더 관례** (:1-18 — 러너 금지 사유까지 명시):
```ts
// 실행: node --test app/src/lib/pickerFailure.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (belle: 1,120개 의존성 이유로 테스트 러너 승인 철회).
// node:test / node:assert 표준 모듈만 쓰고 `.ts` 확장자 import 를 명시한다.
import test from 'node:test';
import assert from 'node:assert/strict';
import { describePickFailure, type PickFailureKind } from './pickerFailure.ts';
```

**전수 불변식 검사 형태** (:71-83 — manualOffset 클램프·warp 합성 테스트가 복제):
```ts
test('모든 실패 종류가 제목·2줄 본문·버튼 라벨을 갖는다', () => {
  for (const kind of ALL_KINDS) {
    const f = describePickFailure(kind);
    assert.ok(f.title.length > 0, `${kind}: title 이 비어 있음`);
    ...
  }
});
```
전제: 테스트 대상 로직은 player/react 의존 0 순수 함수로 분리돼 있어야 한다 — `alignmentWarp.ts` 헤더(:1-3 "순수 함수만, player/react 의존 0")가 그 모범. manualOffset 합성도 순수 함수로 빼서 테스트.

---

## Shared Patterns

### SP-1. "result 안으로 흐른다" — complete_analysis 신규 kwarg 금지
**Source:** `firestore_admin.py:288-296` (_validate_safety_flags docstring) + `:1005-1010`
**Apply to:** 미션 오브젝트·스팟체크 플래그 등 result 내 신규 필드 전부
```python
"""`result['safetyFlags']` 의 단일 persistence path 에서만 호출 (complete_analysis 에
신규 kwarg 추가 X — 플래그는 result 안으로 흐른다). ... [[firestore-nested-array-flat]] 보존."""
```
`complete_analysis` 시그니처(:959-982)는 이미 kwarg 21개 — 더 늘리지 않는 것이 확립된 규율. 신규 필드는 result dict 안에 넣고 scoped validator 로만 검증.

### SP-2. flat 저장 + reshape 메타 (nested-array 금지)
**Source:** `motion_alignment.py:182-193` (flat anchors + anchorCount), `keypoint_frame.py:93-100` (data flat T×J×2)
**Apply to:** 미션(flat scalar dict), keypointReport 확장(J 12), 스팟체크 결과
```python
anchors: list[float] = []
for u_sec, r_sec in pairs:
    anchors.append(float(u_sec))
    anchors.append(float(r_sec))
result = {..., "anchors": anchors, "anchorCount": len(anchors) // 2, ...}
```

### SP-3. graceful 어댑터 (키 부재/실패 = no-op, 분석 비차단)
**Source:** `coach_writer.py:217-229/246-279`, `gemini_vision_scorer._ensure_client:763-782`
**Apply to:** 스팟체크(실패 = 카드 숨김 없이 통과 + 로그), TTS 생성 단계, LLM 가변부
원칙: 표시 전용 부가물의 실패가 완료된 분석을 fail 시키면 안 된다 (`motion_alignment.py:76-81` 주석의 "방출 실패 비차단" 교훈과 동일).

### SP-4. 카피 상수 분리 + 금지어 게이트
**Source:** `copy_templates.py:247-265` + `phase07/test_copy_templates_no_forbidden.py`
**Apply to:** 문구집 전체, 배지/코치마크/실패 화면(D-30) 카피, "대략 맞춤" 라벨
D-09 확장 금지 패턴(수치 헤드라인·% 환산)을 FORBIDDEN 목록에 추가하고 sanity(추출 0건 방지) 테스트 동반.

### SP-5. 테마 토큰 + 접근성 props (하드코딩 금지)
**Source:** `AccuracyLimitBadge.tsx:48-72`, `ScoreBreakdownSection.tsx:167-224`, `result.tsx:521-528`
**Apply to:** 신규 컴포넌트 전부
```tsx
<Pressable onPress={...} accessibilityRole="button"
  accessibilityLabel="..." hitSlop={8}>
```
스타일 값은 `colors/radius/spacing/typography/layout` 토큰만. lineHeight 명시 시 fontSize 이상(Pitfall 3).

### SP-6. fps 도메인 분리
**Source:** `result.tsx:2105-2135` (kr fps 나눗셈 정본), `motion_alignment.py:7-11` (초 단위 방출 원칙)
**Apply to:** 수동 오프셋·legacy 폴백·자막 큐 타이밍·2D 뷰어
프레임↔초 환산은 각자의 `keypointReport.fps` 로만. 9/18 하드코딩 금지. joints3d(9fps) 공간과 kr 공간 혼합 금지.

### SP-7. 스펙 인용 주석 관례
**Source:** 전 파일 공통 — `// Phase 28 (ALGN-01...)`, `# 29-PLAN-REVIEW HIGH-2`, `(design.md §5-4)` 식
**Apply to:** 신규 코드 전부 — 32 결정은 `32-CONTEXT D-08` 식으로 인용. 커밋되는 코드에 console.log 금지, 백엔드는 `log.info("... uid=%s analysis_id=%s", ...)` 구조 로그.

---

## No Analog Found

RESEARCH.md 패턴을 대신 사용할 파일:

| File | Role | Data Flow | Reason |
|---|---|---|---|
| TTS 기기 경로 (`expo-speech` 소비 lib) | lib adapter | streaming | 코드베이스에 오디오 코드 0. RESEARCH §TTS 비교의 `Speech.speak(text, {language:'ko-KR'})` + 이전 발화 stop 처리 사용. 설치는 `npx expo install` 만 |
| Polly 합성 스테이지 (백엔드, 클라우드 채택 시) | adapter | request-response | boto3 `client("polly")` 신규 — 단 S3 저장·사후 스테이지·asset 재서명은 각각 SP-1/E-1/E-3 아날로그로 커버 |
| 인체 일러스트 정적 에셋 (D-21) | asset | — | 정적 에셋 번들 선례 없음(앱은 아이콘 폰트만). 샘플 게이트 통과 시 `app/assets/` 번들 + 미달 시 실프레임 폴백(코드 관점 무산출) |
| PR 인버전 워프 코드 | GPU 전처리 | transform | 저장소 밖 spike 산출물(`pr_warp_pod.py`, spike 004 디렉터리·Pod 볼륨)이 원본 — 코드베이스 편입 시 `pose_estimator.py` 의 어댑터 관례(Protocol, lazy import)를 따를 것 |

---

## Metadata

**Analog search scope:** `app/src/{app,components,lib,theme,types}`, `backend/shared/python/sunity_shared/{analysis,·}`, `backend/functions/{pipeline,playback-url}`, `backend/tests/{·,phase07,phase31}`, `backend/data`
**Files scanned:** 디렉터리 전수 목록 + 대형 8파일 앵커 grep + 25개 파일 실독(전체 15 / 타겟 구간 10)
**핵심 라인 앵커 (planner 즉시 참조용):**
- 수리 3건: `motion_alignment.py:167-180` / `result.tsx:2545-2550` / `fault_zoom.py:558-587`
- 삽입 지점: `VideoCompare.tsx:371-383`(수동 오프셋) / `pipeline/app.py:5289`(사후 스테이지 자리) / `keypoint_frame.py:51`(12관절 확장)
- 검증 뼈대: `firestore_admin.py:308-407`(validator 모범) / `phase31/conftest.py:346-370`(fake_firestore)
**Pattern extraction date:** 2026-07-21
