# Phase 29: 결과·비교 화면 완성 - Pattern Map

**Mapped:** 2026-07-09
**Files analyzed:** 11 (new 3 / modified 8)
**Analogs found:** 10 / 11 (가로 전환 네이티브 감지만 repo 무선례 — 폴백 분기는 기존 코드)

라인 번호는 2026-07-09 main 실측 기준. 대부분의 수정 대상은 "자기 자신이 최고 analog" — 같은 파일 안의 mode1 선례를 mode3 로 확장하는 작업이다.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/functions/pipeline/app.py` (D-01/02 seam) | pipeline service | batch/transform | 동일 파일 `_apply_vision_veto_from_context` 의 24-04 low_alignment tally-eligible 선례 (:2533-2631) | exact (in-file) |
| `backend/functions/pipeline/app.py` (D-08 zoom) | pipeline service | batch/transform | 동일 파일 `_build_mode3_fault_zoom_comparisons` (:2970-3039) — joint 선택 소스만 교체 | exact (in-file) |
| `backend/tests/test_mode3_tally_seam.py` (NEW) | test | unit (mock) | `backend/tests/test_pipeline_deduction_seam.py` (:1-84 헬퍼) + `test_pipeline_mode3.py` (:1-55 prev doc 헬퍼) | exact |
| `backend/evals/phase29/run_sweep.py` + `assert_gates.py` (NEW) | eval harness | batch (SERIAL) | `backend/evals/phase25/` (자체가 phase24 복제-확장 — 같은 계보 3대째) | exact |
| `docs/contract.md` §10 서술 | config/contract | — | 기존 §10/§11 optional-field 서술 (faultZoomStatus/motionAlignment 절) | exact |
| `app/src/types/analysis.ts` + `models.py` | contract mirror | — | 기본 권고 변경 0 (RESEARCH Pattern 2). 필드 신설 시 analog = `faultZoomStatus`/`motionAlignment` optional+legacy 폴백 주석 (analysis.ts:553-572) | exact |
| `app/src/app/analysis/result.tsx` | screen component | Firestore onSnapshot → render | 동일 파일 mode1 게이트 4곳 (:771, :813, :905, :892) + 28 배너 (:1471) + prev 재발급 (:683-706) | exact (in-file) |
| `app/src/components/InjuryRiskSection.tsx` | component | render-only (copy map) | 동일 파일 FLAG_COPY (:29-46) + 카드 (:51-67) | exact (in-file) |
| `app/src/components/ScoreBreakdownSection.tsx` | component | render-only | 동일 파일 basisLine (:55) / footnote 슬롯 (:127-152) | exact (in-file) |
| `app/src/components/VideoCompare.tsx` | component | video playback | 동일 파일 전체화면 Modal (:954-994) + open/close (:285-292); 네이티브 감지는 무선례 → RESEARCH Pattern 3 | role-match |
| `app/package.json` + `app/app.json` | config | — | `expo-mail-composer` plugins 등록 선례 (app.json:56) | exact |

## Pattern Assignments

### `backend/functions/pipeline/app.py` — D-01/D-02 mode3 tally seam (pipeline, transform)

**Analog:** 동일 파일 `_apply_vision_veto_from_context` — 24-04 low_alignment 를 tally-eligible 로 편입한 선례를 mode3_held 에 그대로 이식.

**현행 게이트 — 삽입 지점** (app.py:2560-2583):
```python
status = ctx.collection_status
# tally-eligible: candidate_verdict(Gemini 결함) / no_fault(정타지만 measured seed 가
# 감점 가능 — iter5 HIGH-1) / low_alignment_confidence(정렬 낮음이지만 RTMW 측정 편차는
# 정렬-독립 — 24-04 Option A). 그 외 status 는 측정 불가 → score-free passthrough.
if status not in ("candidate_verdict", "no_fault", "low_alignment_confidence"):
    passthrough_map = {
        "resource_limited": "resource_limited",
        "disabled": "disabled",
        "mode3_held": "mode3_held",          # ← ★ D-01: 여기서 md 보유 시 tally 분기 절개
        "missing_reference": "missing_reference",
        "missing_current_video": "missing_local_video",
        "skipped_error": "skipped_error",
    }
    final = passthrough_map.get(status, "skipped_error")
    audit = {"status": final}
    ...
    return {**score_result, "visionVeto": audit}
```

**복사할 tally 실행 + 방출 패턴** (app.py:2598-2631 — candidate/no_fault/low_alignment 경로):
```python
breakdown = deduction_engine.tally(
    quant, ctx,
    dimension_overall=score_result["overallScore"],
    measured_deviations=measured_deviations,
    dimension_scores=score_result.get("dimensionScores"),
    baseline_kind=baseline_kind,
)
has_deduction = bool(breakdown.records)
if has_deduction:
    ...
    return {
        **score_result,
        "overallScore": breakdown.final,          # D-02 (sweep 게이트 통과 후)
        "deductionBreakdown": breakdown.to_dict(),
        "visionVeto": audit,
    }
```
mode3 분기에서는 `quant=None, ctx 없음` — legacy 단일영상 경로(app.py:2492-2498)가 이미 `tally(None, None, ...)` 시그니처를 보여준다. **visionVeto.status 는 'mode3_held' 유지** (RESEARCH Pattern 1 옵션 a — 'applied' 재사용 시 result.tsx:711 `vetoApplied` 파생 의미 오염).

**md 는 이미 mode3 에서 빌드됨 — 인자 흐름이 D-01 "ipsf_absolute 전용"을 자동 보장** (app.py:4137-4149):
```python
measured_deviations = _build_deduction_measured_deviations(
    angles=angles, profile=profile, assessments=assessments,
    dimension_scores=dimension_scores, quantification=quantification,
    # 24-07 ① — mode1 에서 set, mode3/legacy 는 None → graceful 미방출.
    reference_dtw_match=reference_dtw_match,
    reference_angles=reference_angles_for_veto,
    # split — mode1 에서만 산출(reference_relative), mode3/legacy 는 None → 미방출.
    split_deficit_deg=split_deficit_deg,
    vision_pointed_joints=vision_pointed_joints,
)
```
**주의:** md 빌드는 `vision_fault_context is not None` 분기 안(:4108)에 있다. mode3 는 collect 가 mode3_held ctx 를 반환하므로 이 분기를 타는지 seam 에서 확인 — RESEARCH 는 "빌드됨" 실측(:4137). md 빈 dict → passthrough 유지 = D-03 자연 방어 + breakdown 미방출 권고 (RESEARCH Open Q2).

**Error handling 패턴:** 전체를 `try/except Exception: log.exception(...) → passthrough` 로 감싸는 기존 seam 스타일(:2526-2530) 준수 — 채점 hook 실패는 분석을 막지 않는다.

---

### `backend/functions/pipeline/app.py` — D-08 zoom joint 소스 교체 (pipeline, transform)

**Analog:** 동일 함수 `_build_mode3_fault_zoom_comparisons` — 교체 대상 로직 실체 (app.py:3000-3013):
```python
curr_scores = _joint_scores(result.get("joints") or [])
prev_scores = _joint_scores(prev_result.get("joints") or [])
# 양쪽에 score 있는 관절만 — 변화량(|Δscore|) 최대 top-2.
common = [k for k in curr_scores if k in prev_scores]
...
change_joints = [k for k in common if abs(curr_scores[k] - prev_scores[k]) >= 1.0][:2]
...
kinds = {
    k: ("improved" if curr_scores[k] >= prev_scores[k] else "worsened")
    for k in change_joints
}
```
D-08 = 이 `change_joints`/`kinds` 산출을 **deduction records 의 감점 관절**(criterion `angle_vs_reference__{jk}` — result.tsx:730-735 의 파싱 선례와 동일 규칙) 소스로 교체 + improved 억제. `_render_fault_zoom(...)` 호출부(:3026-3039)는 `dtw_match=dtw_match, dtw_ref_fps=_pipeline_frame_fps()` (28-05/CR-01) 포함 그대로 유지 — 관절 목록·kinds 인자만 바뀐다. record 관절 ∩ zoom 관절 일치가 앱 드릴다운 매칭(result.tsx:946-974) 성립 조건 (RESEARCH Pitfall 6).

---

### `backend/tests/test_mode3_tally_seam.py` (NEW — test, unit/mock)

**Analog:** `backend/tests/test_pipeline_deduction_seam.py` (Phase 24 seam 테스트 정본, 598줄)

**Imports + path 주입 패턴** (lines 17-38):
```python
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# pipeline/app.py + shared layer path 주입.
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import app  # noqa: E402
from sunity_shared.analysis import technique, vision_veto  # noqa: E402
```

**픽스처 헬퍼 패턴** (lines 44-73 — profile/ctx 스텁):
```python
def _profile(name: str = "t", motion_id: str | None = None) -> technique.TechniqueProfile:
    """팔꿈치/무릎 EXTEND 프로파일 (line/extension substrate 산출되게)."""
    exp = {
        k: technique.JOINT_EXTEND
        if k.endswith("elbow") or k.endswith("knee")
        else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(
        name=name, category="unknown", joint_expectations=exp, motion_id=motion_id
    )

def _ctx(status, *, verdict=None, supported=None, frame_pairs=None, cap=False):
    return vision_veto.VisionFaultContext(
        collection_status=status, verdict=verdict,
        supported_differences=list(supported or []), root_cause_hypotheses=[],
        selected_frame_pairs=list(frame_pairs or []), alignment={}, telemetry={},
        cap_would_apply=cap,
    )
```
mode3 케이스: `_ctx("mode3_held")` + md 유/무 매트릭스. prev doc 스텁은 `test_pipeline_mode3.py::_as_prev` (flat angles + anglesJointKeys + anglesFrames — Firestore flat 규칙 mirror) 재사용.

**모듈 헤더 docstring 관례** (test_pipeline_deduction_seam.py:1-15): 박제 정신 요약 + "전부 mock-based — 실 Gemini/실 S3 0" + "수치 타깃 아님 — 방향/구조 단언만 (curve-fit 금지)" 문구를 반드시 승계.

---

### `backend/evals/phase29/` (NEW — eval harness, batch SERIAL)

**Analog:** `backend/evals/phase25/run_sweep.py` + `assert_gates.py` (phase24 복제-확장 계보 — phase29 는 3대째 복제)

**run_sweep 골격** (phase25/run_sweep.py:56-94):
```python
from __future__ import annotations
import argparse, importlib.util, json, logging, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent.parent  # backend/
sys.path.insert(0, str(BACKEND / "shared" / "python"))
sys.path.insert(0, str(BACKEND))

# eval 은 항상 결정론 모드 — pipeline 로드 전 module-level env 주입 (setdefault 라
# 운영자 명시 export 가 우선).
os.environ.setdefault("RTMW_DETERMINISTIC", "1")
os.environ.setdefault("GEMINI_VISION_VETO_ENABLED", "1")   # mode3 sweep 에도 유지 —
os.environ.setdefault("GEMINI_MAX_VETO_WALL_S", "300")     # production mirror 원칙
```
산출물 규율 (run_sweep.py:21-29): `EVAL_OUT_DIR`(기본 /tmp/sunity_eval_out) 하위에만 기록, `--tag warm` 재실행 → `*_warm.json`, **repo 내 baseline/ 은 read-only** (2026-07-02 오염 사고 재발 금지). 실행 커맨드 헤더(:41-50)도 승계.

**assert_gates 골격** (phase25/assert_gates.py 헤더): phase24 게이트 **import 재사용** + 신규 게이트 추가. artifact 부재 시 SKIPPED(실패 아님), exit 0 = PASS / 1 = FAIL. **점수 리터럴 타깃 하드코딩 금지 — baseline artifact 대비 방향 비교만** (locked, scoring-redesign-must-generalize-no-overfit).

**phase29 전용 조정 (RESEARCH Pattern 5):** eval_keys = `evals/phase24/eval_keys.json` 6페어를 mode='mode3' 단독 분석으로 재사용. 게이트 기대치 = "power-spin 만 leg_extension 감점 변별, 나머지 4동작 fallback 항등"(Pitfall 1 — 4/5 동작 criteria yaml 이 비어 있음), cold=warm 결정성, success 무감점.

---

### `app/src/app/analysis/result.tsx` — mode1 게이트 4곳 mode3 확장 (screen, onSnapshot→render)

**Analog:** 동일 파일의 mode1 게이트들 — 확장 지점 원문.

**게이트 1 — cleanPass** (:766-773):
```tsx
// quick-260705-o0s — 감점 0 게이트 단일 신호 (belle 추가 피드백 #2). ...
// mode3/legacy doc(breakdown 부재)은 false → 기존 렌더 무회귀.
const cleanPass = isCleanPass(
  cmp.mode === 'mode1' ? result.deductionBreakdown : null,
);
```

**게이트 2 — actionLabels hasBreakdown** (:812-814):
```tsx
const actionLabels = useMemo<Partial<Record<KeypointName, string>>>(() => {
  const hasBreakdown =
    cmp.mode === 'mode1' && result.deductionBreakdown != null;
```
mode3 signed-delta 소스는 주석(:794-801)이 이미 명시: "2. JointScore.deltaDeg (kismam 평균, Mode3 커버)" — 게이트만 열면 기존 2순위 경로가 동작.

**게이트 3 — showBreakdownSection** (:902-906):
```tsx
// quick-260702-q8q — "점수 계산 내역" 섹션 렌더 가드. mode1 전용(mode3 는 veto
// 미실행 mode3_held) + deductionBreakdown 보유 doc 만 (legacy doc 은 필드 부재 →
// 섹션 자체 숨김, normalize 가 malformed 를 undefined 로 접음 — 크래시 0).
const showBreakdownSection =
  cmp.mode === 'mode1' && result.deductionBreakdown != null;
```
확장 방향(RESEARCH Pattern 6): `result.deductionBreakdown != null` 로 mode 무관화 — mode3 는 D-01 방출 시에만 필드 존재 → 미등록/legacy 자연 숨김.

**게이트 4 — timelineTicks** (:890-900): visionVeto 의존 — mode3 는 window 시점 없음 → 빈 배열 유지가 정직 (변경 불필요, 주석 근거 :890-891).

**D-03 안내 삽입 자리 — 억제 카피 선례** (:651-661):
```tsx
const isScoreSuppressed =
  cmp.mode === 'mode3' && result.scoreSuppressed === true;
// iter3 MEDIUM-1 / iter4 MEDIUM-1 — 억제 헤더 카피는 reason 이 소유 (reason-owns-copy).
const suppressedHeaderCopy = isScoreSuppressed
  ? result.scoreSuppressedReason === 'recognition_low_confidence'
    ? '동작 인식 신뢰도가 낮아 기준을 확정할 수 없어요.'
    : ...
  : null;
```

**D-04 재분석 배너 — Phase 28 D-05 원본** (:1471-1484):
```tsx
{result.motionAlignment === undefined ? (
  <View style={styles.alignUpsellBanner}>
    <Text style={styles.alignUpsellText}>
      다시 분석하면 자동 구간 맞춤이 적용돼요
    </Text>
    <Pressable
      onPress={() => router.replace('/(tabs)/analyze')}
      accessibilityRole="button"
      hitSlop={8}
    >
      <Text style={styles.alignUpsellCta}>다시 분석하기</Text>
    </Pressable>
  </View>
) : null}
```
판정 규칙 주석(:1464-1468) 필수 승계: "필드 자체 부재(undefined)만 순수 legacy — normalize null(malformed)은 배너 아님".

**D-06/D-07 — 비교 섹션 현행** (:1373, :1388-1396):
```tsx
{!(cmp.mode === 'mode3' && cmp.isFirst) && (   // ← D-07: 첫 분석 = 섹션 숨김 (현행). 안내 1줄 추가 지점.
  ...
  rightLabel={
    cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 분석'   // ← D-06 라벨 정본
  }
  rightUrl={
    cmp.mode === 'mode1'
      ? result.referenceVideoUrl || refMotion?.videoUrl || undefined  // ← D-09 D1 진단 대상
      : freshPrevUrl || prevDoc?.result?.myVideoUrl || undefined
  }
```

**D-09 D1 진단 — prev 재발급 선례 (mode3 전용, reference 는 경로 부재 = 유력 원인)** (:683-706):
```tsx
// 박제 (2026-06-06 belle): prev doc 의 myVideoUrl S3 sign 7일 TTL 만료 시
// (이전 분석이 6일+ 전이면) POST /playback-url 박제 재발급.
const SAFE_TTL_MS = 6 * 24 * 60 * 60 * 1000; // 6일 margin (7일 TTL 안전)
const age = Date.now() - (prevDoc.createdAt || 0);
if (age < SAFE_TTL_MS) { setFreshPrevUrl(null); return; }
requestPlaybackUrl(prevDoc.analysisId, ext)
  .then((resp) => { if (!cancelled) setFreshPrevUrl(resp.playbackUrl); })
  .catch((err) => { if (__DEV__) console.warn('[playback-url] 재발급 실패', err); });
```
D1 fix 가 reference 재서명으로 귀결되면 이 훅 + `requestPlaybackUrl` (api.ts) 이 복사 원본.

---

### `app/src/components/InjuryRiskSection.tsx` — D-14 FLAG_COPY 확장 (component, render-only)

**Analog:** 동일 파일 — 확장 대상 원문 (:29-46):
```tsx
// flagType → {title, why} 카피 맵 (10-UI-SPEC Copywriting Contract, 4종 전부).
const FLAG_COPY: Record<SafetyFlagType, { title: string; why: string }> = {
  asymmetry: {
    title: '좌우 비대칭 신호',
    why: '기준보다 좌우 움직임 차이가 크고, 동작이 흔들리는 구간이 있어요. ...',
  },
  trunk_hyperextension: { ... },
  joint_hyperextension: { ... },
  level_mismatch: { ... },
};
```
D-14 = `{title, why}` → `{title, why, recommendation}` 4종 전부 확장 (**백엔드 필드 신설 금지** — `SafetyFlag` 는 backend dataclass·TS·contract §9.13 모두 7필드, recommendation 부재. RESEARCH Pitfall 2).

**카드 행 추가 패턴** (:51-67 — why 행 아래 recommendation 행 복제):
```tsx
function InjuryRiskFlagCard({ flag }: { flag: SafetyFlag }) {
  const copy = FLAG_COPY[flag.flagType];
  if (!copy) return null; // 미지의 flagType — graceful skip (계약 외 값 방어).
  return (
    <View style={styles.card} accessibilityRole="alert"
      accessibilityLabel={`${copy.title}. ${copy.why}`}>
      <View style={styles.row}>
        <Ionicons name="warning" size={16} color={colors.warnAmber} />
        <Text style={styles.cardTitle}>{copy.title}</Text>
      </View>
      <Text style={styles.cardWhy}>{copy.why}</Text>
    </View>
  );
}
```
규칙 헤더(:1-14) 준수: amber 시맨틱만(브랜드 레드 금지), "부상 확정" 단정 금지, 토큰만, **변경 시 10-UI-SPEC Copywriting Contract 동시 갱신**. 기존 `EXPERT_REFERRAL`(:25 '정확한 판단은 강사 또는 전문가와 함께 확인해 주세요.')과 캡션 중복 조정은 재량 (CONTEXT D-14).

---

### `app/src/components/ScoreBreakdownSection.tsx` — D-05 한계 고지 슬롯 (component, render-only)

**Analog:** 동일 파일 — optional prop + footnote 슬롯 선례.

**optional prop 관례** (:31-47): `recordNumbers?`, `basisLine?`, `onRecordPress?` 전부 "미전달 시 렌더 diff 0 (다른 소비처/legacy 무회귀)" — D-05 한계 고지도 같은 optional prop 형태로 신설.

**footnote 슬롯 원문** (:127-152 — 한계 고지 삽입 위치의 형제들):
```tsx
{hasAnyNumber && (
  <Text style={styles.footnote}>번호는 위 영상의 빨간 점 위치와 같아요.</Text>
)}
...
{gapCount > 0 && (
  <Text style={styles.footnote}>
    {`측정하지 못해 점수에 반영하지 않은 항목이 ${gapCount}건 있어요.`}
  </Text>
)}
{breakdown.fallback === 'quantification_unavailable' && (
  <Text style={styles.footnote}>정밀 정량화가 불가해 측정 기하 종합으로 환산했어요.</Text>
)}
```
스타일 토큰: `footnote = { ...typography.captionSmall, color: colors.textSecondary, lineHeight: 16 }` (:209-213). 객관성 헤더(:13-14) 승계: "합계 검증이 어긋나도 UI 가 숫자를 조작하지 않는다". **D-05 카피에 "각도" 금지어** — 기존 `deductionLabels` 카피 재사용 시 "각도" 포함 여부 grep 필수 (CONTEXT D-05).

---

### `app/src/components/VideoCompare.tsx` — D-11/D-12 가로 전환 (component, video playback)

**Analog (폴백 분기 = 기존 코드):** 90° 회전 핵 원문.

**open/close + 치수 파생** (:268-292):
```tsx
const [fullscreen, setFullscreen] = useState(false);
const fullscreenRef = useRef(false);
const { width: winW, height: winH } = useWindowDimensions();
const fsShort = Math.min(winW, winH);
const fsLong = Math.max(winW, winH);
const fsBoxH = fsShort;
const fsBoxW = Math.round(fsShort * VIDEO_ASPECT);   // VIDEO_ASPECT = 9/16 (:195)
const openFullscreen = () => {
  fullscreenRef.current = true;   // ← D-11: 진짜 가로 분기에서 lockAsync 호출 삽입 지점
  setFullscreen(true);
};
const closeFullscreen = () => {
  fullscreenRef.current = false;  // ← 닫기: PORTRAIT_UP lock → close (역순 flicker 주의)
  setFullscreen(false);
};
```

**전체화면 Modal + 회전 컨테이너** (:954-979):
```tsx
{fullscreen && (
  <Modal
    visible
    transparent={false}
    animationType="fade"
    statusBarTranslucent
    supportedOrientations={['portrait']}   // ← 진짜 가로 분기: ['portrait','landscape'] 필요 (RESEARCH Pattern 4)
    onRequestClose={closeFullscreen}
  >
    <StatusBar hidden />
    <View style={styles.fsRoot}>
      <View
        style={[
          styles.fsRotated,               // { position:'absolute', transform:[{rotate:'90deg'}] } (:1226-1229)
          {
            width: fsLong, height: fsShort,
            left: (fsShort - fsLong) / 2, top: (fsLong - fsShort) / 2,
          },
        ]}
      >
```
진짜 가로 분기 = `fsRotated` transform + 축 스왑 치수 생략, window 치수 그대로. `FULLSCREEN_ZOOM = 1.35`(:202) 는 belle 승인값 — 변경 시 근거 필수.

**네이티브 감지 (repo 무선례 — RESEARCH Pattern 3 검증본 그대로 복사):**
```ts
// Source: expo-modules-core 3.0.29 src/requireNativeModule.ts:32 (로컬 실측)
import { requireOptionalNativeModule } from 'expo-modules-core';

const hasNativeOrientation =
  requireOptionalNativeModule('ExpoScreenOrientation') != null;

async function enterLandscape() {
  if (!hasNativeOrientation) return; // 구빌드 → 기존 90° 회전 핵 경로
  // 함수 스코프 lazy require — Metro 는 require 호출 시점에 모듈 평가
  const ScreenOrientation = require('expo-screen-orientation');
  await ScreenOrientation.lockAsync(
    ScreenOrientation.OrientationLock.LANDSCAPE_RIGHT,
  );
}
```
**절대 금지:** 파일 상단 정적 `import 'expo-screen-orientation'` — 구빌드(빌드 27) OTA 번들 평가 시점 크래시 (Pitfall 3). `npm install @latest` 금지 — `npx expo install` 로 ~9.0.9 고정.

---

### `app/src/types/analysis.ts` + `models.py` + `docs/contract.md` — 계약 (기본 변경 0)

**Analog (필드 신설이 필요해질 경우):** optional + legacy 폴백 + Python lockstep 명시 주석 3종 세트 (analysis.ts:560-572):
```ts
// Phase 27 SPD-04 (D-06) — zoom 사후 분리 로딩 상태. ... 부재(legacy doc)=faultZoomComparisons
// 유무로 판정 — 사후 분리 이전 doc 하위호환 (tier? 서술 모범 준수). Python lockstep:
// models.py FAULT_ZOOM_STATUSES + firestore_admin.update_analysis_fault_zoom +
// contract.md faultZoomStatus 절.
faultZoomStatus?: 'pending' | 'done' | 'failed';
// Phase 28 (ALGN-01) — 동작 기반 비교 정렬 맵. OPTIONAL (부재=현행 절대시계, legacy
// 하위호환, no migration). ... Python lockstep: models.py MOTION_ALIGNMENT_KEYS + ...
motionAlignment?: MotionAlignment;
```
`deductionBreakdown?: DeductionBreakdown`(:557) 은 이미 mode 무관 optional — mode3 방출은 계약 필드 0 으로 가능 (RESEARCH Pattern 2). contract.md 는 §10 에 mode3 방출 조건 서술만 추가. 3-way 를 건드리면 **셋 다 같은 커밋**에서.

---

### `app/app.json` — expo-screen-orientation plugin 등록 (config)

**Analog:** 기존 plugins 배열 (app.json:44-57):
```json
"plugins": [
  "expo-router",
  ["expo-image-picker", { "photosPermission": "...", ... }],
  "expo-video",
  "expo-asset",
  "expo-mail-composer"
],
```
`"expo-screen-orientation"` 를 문자열 항목으로 추가 (옵션 불필요 시 — initialOrientation 은 iOS 전용 옵션). **version(1.0.0)/runtimeVersion policy 는 건드리지 않는다** — bump 시 구빌드 OTA 채널이 갈라진다 (RESEARCH Pattern 3).

## Shared Patterns

### 계약 3-way lockstep
**Source:** `app/src/types/analysis.ts` ↔ `backend/shared/python/sunity_shared/models.py` ↔ `docs/contract.md`
**Apply to:** 계약을 만지는 모든 태스크. 한쪽만 수정 = anti-pattern. 필드는 optional + "부재 = 현행 렌더" legacy 폴백 + lockstep 주석 3종 세시.

### 스펙 인용 주석 (Korean why-comments)
**Source:** 전 코드베이스 관례
**Apply to:** 모든 신규/수정 코드. 형식: `// 28-CONTEXT D-01 — ...`, `# 24-04 Option A (belle 2026-06-26) — ...`, `[[memory-slug]]` 인용. 이모지 0. 사용자 카피는 "~해요" 체.

### 테마 토큰 강제
**Source:** `app/src/theme/` (colors/typography/radius/spacing/layout)
**Apply to:** 모든 앱 UI. 하드코딩 색/spacing 금지. 경고 시맨틱 = `warnAmber`/`warnAmberBg` (브랜드 레드는 긍정 강조 전용). 신규 스타일은 `StyleSheet.create` 파일 하단.

### 방어적 정규화 + graceful skip
**Source:** `userAnalyses.ts normalize()`, `InjuryRiskSection` `if (!copy) return null`, `VideoCompare normalizeMotionAlignment` (:299)
**Apply to:** Firestore doc 소비 전부 — malformed 는 undefined/null 로 접고 크래시 0, 렌더는 필드 유무로 자연 분기.

### eval 게이트 규율
**Source:** `backend/evals/phase25/` 헤더 계약
**Apply to:** `evals/phase29/`. SERIAL 필수, EVAL_OUT_DIR 밖 기록 금지(baseline read-only), cold/warm 결정성, 점수 리터럴 assert 금지(방향 비교만), artifact 부재 = SKIPPED, Pod 작업은 push 먼저.

### 백엔드 seam 에러 격리
**Source:** `_apply_vision_veto` (:2526-2530)
**Apply to:** pipeline 채점/zoom 변경 전부 — `except Exception: log.exception(...) → graceful passthrough`. 채점 hook 실패가 분석 실패가 되면 안 된다. 로그는 `log.info("... uid=%s ...", uid)` key=value 구조.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| expo-screen-orientation 런타임 감지 (VideoCompare 내 신규 헬퍼) | component util | native module detection | repo 에 `requireOptionalNativeModule` 사용 선례 0 — RESEARCH Pattern 3 의 검증된 코드(expo-modules-core 3.0.29 실측)를 그대로 사용. 폴백 분기 자체는 기존 90° 회전 핵(:954-994)이 원본 |

D-13 빌드 체인(eas build/submit)은 코드 파일이 아니라 RESEARCH "D-13: 빌드·제출 체인" 커맨드 + `app/eas.json` 기존 프로필을 그대로 사용 — 별도 analog 불필요.

## Metadata

**Analog search scope:** `backend/functions/pipeline/`, `backend/tests/`, `backend/evals/`, `app/src/app/analysis/`, `app/src/components/`, `app/src/types/`, `app/app.json`
**Files scanned:** 15 (targeted reads — 라인 앵커는 29-RESEARCH 실측과 교차 확인됨)
**Pattern extraction date:** 2026-07-09
