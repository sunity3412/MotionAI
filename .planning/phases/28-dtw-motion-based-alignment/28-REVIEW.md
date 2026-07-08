---
phase: 28-dtw-motion-based-alignment
reviewed: 2026-07-08T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - app/src/app/analysis/result.tsx
  - app/src/components/DeductionDetailSheet.tsx
  - app/src/components/VideoCompare.tsx
  - app/src/lib/alignmentWarp.ts
  - app/src/types/analysis.ts
  - backend/functions/pipeline/app.py
  - backend/scripts/measure_reference_fps.py
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/shared/python/sunity_shared/analysis/motion_alignment.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/models.py
  - backend/tests/test_fault_zoom_ref_match.py
  - backend/tests/test_fault_zoom_relaxed_crop.py
  - backend/tests/test_motion_alignment.py
  - backend/tests/test_motion_alignment_contract.py
  - backend/tests/test_pipeline_mode3.py
  - backend/tests/test_pipeline_motion_alignment.py
  - docs/contract.md
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-07-08
**Depth:** standard (diff-focused on `53860a1..HEAD`)
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 28 (DTW 동작 기반 시간 정렬)의 백본 — `build_motion_alignment` 순수 함수, `_validate_motion_alignment` scoped validator, 3-way 계약(analysis.ts / models.py / contract.md §11), `alignmentWarp.ts` 순수 함수 — 는 견고하다. 핵심 invariant 를 직접 검증했다:

- **채점 무접촉**: `motion_alignment.py` 는 채점 모듈 import 0 (AST 가드 테스트로 봉인). `_attach_motion_alignment` 의 유일한 부작용은 `motionAlignment` 키 1개 추가이며 `test_no_scoring_contact_only_key_added` 가 deepcopy diff 0 을 기계 판정한다. overallScore/deductionBreakdown 값을 바꾸는 경로는 없다. 단, WR-03 의 non-finite distance 경로는 **분석 전체를 실패시킬 수 있는** 간접 경로다 (점수 변조는 아니지만 결과 소실).
- **fps 도메인**: mode1 은 정확하다 (ref angles=18fps 를 doc 메타 `keypointReport.fps` 에서 읽고 초 단위로만 방출, fault_zoom D2 fix 의 rep↔frames 변환도 mode1 reference doc 에서 정합). 그러나 **mode3 fault-zoom 은 도메인 전제가 깨진다 (CR-01)** — 사용자 분석 doc 의 keypointReport 는 18fps 로 upsample 저장되는데 prev angles 는 9fps 라 "angles 공간 == keypointReport 공간" 가정이 mode1 reference doc 에서만 성립한다.
- **Firestore**: anchors flat/finite/짝수/상한 512/단조성/tier↔anchors 역불변식 모두 validator 가 강제. nested 는 TypeError. 정상.
- **App 폴백/클램프**: 부재·null·disabled → 절대시계 legacy 경로 100% 보존 확인. `segmentRate` 는 0.5~2.0 클램프, warped tier 는 방출 시점에 slopes_ok 필수라 정합. 다만 정렬 **활성** 경로에서 기존 컨트롤(stepBy/togglePlay/seekBoth)이 warped 타임라인과 절대 타임라인을 섞는 결함이 있다 (CR-02, WR-01, WR-02).

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Mode3 fault-zoom — DTW ref 인덱스(9fps prev angles)를 18fps keypointReport 공간으로 오독 (프레임/좌표가 절반 시각으로 밀림)

**File:** `backend/shared/python/sunity_shared/analysis/fault_zoom.py:865-883`, `backend/functions/pipeline/app.py:3020-3028`, `backend/functions/pipeline/app.py:4670-4674`
**Issue:** 28-05 의 D2 fix 는 `_matched_ref_frame` 반환을 "ref angles(rep) 공간 = keypointReport fps 공간"으로 취급한다:

```python
r_matched = _matched_ref_frame(dtw_match, u_idx, r_rep_frames)
if r_matched is not None:
    r_kp_idx = r_matched  # 이미 rep(angles) 공간 — 추가 변환 불필요
    r_idx = _to_rep_idx(r_matched, r_rep_fps, frames_fps, r_n)
```

이 가정(anglesFrames == keypointReport.frames, 같은 fps)은 **mode1 reference doc 에서만** 성립한다 (28-01 실측이 검증한 것도 reference 11 doc 뿐). 28-04/28-05 가 새로 wiring 한 **mode3** 경로에서는:

- `prev_dtw_match` 의 path ref 인덱스 = 이전 분석 doc 의 `angles` 공간 = **9fps** (파이프라인 저장분)
- `ref_report` = 이전 분석 doc 의 `keypointReport` = **18fps** (`build_keypoint_report(fps=9.0)` → `upsample_to_fps(target_fps=18.0)`, `app.py:4411-4416`)

따라서 mode3 second+ 확대 카드에서 `r_kp_idx = r_matched` 는 9fps 인덱스를 18fps report 에 넣어 **의도한 시각의 절반** 좌표를 읽고, `r_idx = _to_rep_idx(r_matched, 18.0, 9.0, r_n) = r_matched // 2` 로 지난 영상 프레임도 **절반 시각**을 확대한다. 예: 학생 worst pose 5.0s 에 DTW 가 지난 영상 4.4s(인덱스 40)를 대응시켜도 카드에는 지난 영상 2.2s 프레임이 실린다. 이 phase 가 제거하려던 "엉뚱한 pose 확대" 오도(파일럿 D2)가 mode3 에서 재생산되며, 종전 ratio 근사(시간비례라 대략 정합)보다 오히려 나쁘다. 테스트 `test_dtw_ref_frame_identity_when_both_9fps` 가 "9fps/9fps(mode3 도메인)"라고 주석했지만 실제 mode3 의 ref_report 는 18fps 라 이 fixture 전제가 프로덕션과 다르다 — 회귀 가드가 버그를 통과시킨다.
**Fix:** DTW path 의 ref 인덱스가 사는 fps 공간을 **인자로 명시**하고 rep/frames 각각 변환한다. 예:

```python
# build_fault_zoom_comparisons 에 dtw_ref_fps: float 인자 추가 (mode1=r_rep_fps 와 동일, mode3=9.0)
r_matched = _matched_ref_frame(dtw_match, u_idx, huge_or_domain_frames)
if r_matched is not None:
    r_kp_idx = _to_rep_idx(r_matched, dtw_ref_fps, r_rep_fps, r_rep_frames)
    r_idx = _to_rep_idx(r_matched, dtw_ref_fps, frames_fps, r_n)
```

mode1 호출은 `dtw_ref_fps=r_rep_fps`(현행과 동일 결과), mode3 호출(`_build_mode3_fault_zoom_comparisons` → `_render_fault_zoom`)은 `dtw_ref_fps=9.0`(prev angles fps). 클램프 상한도 dtw 도메인 프레임 수(prev `anglesFrames`)로 잡아야 한다. 테스트에 "ref_report 18fps + dtw 9fps"(실제 mode3 형상) 케이스를 추가할 것.

### CR-02: VideoCompare stepBy — 정렬 활성 시 warped rightCurrent 를 절대 타임라인 base 로 사용 → 0.1s 스텝 버튼이 학생 영상을 수 초 점프시킴

**File:** `app/src/components/VideoCompare.tsx:544-557`
**Issue:** 새 정렬이 활성이면 `rightCurrent`(=warp 된 정은지 시각)와 `leftCurrent`(학생 master 시각)는 서로 다른 타임라인이다. 그런데 스텝 컨트롤은 여전히 두 값을 섞는다:

```typescript
const base =
  hasLeft && hasRight
    ? Math.min(leftCurrent, rightCurrent)
    : ...
seekBoth(base + deltaS);
```

전형 케이스(학생 영상 준비 구간이 길어 `u0 > r0` — 학생은 3s 에 동작 시작, 정은지 클립은 0.5s)에서 `rightCurrent = warp(cL) ≈ cL − 2.5` 가 항상 작으므로 `base = cL − 2.5`. 사용자가 "0.1초 앞으로"를 누르면 `seekBoth(cL − 2.4)` 가 학생(master) 영상을 **2.4초 뒤로** 점프시킨다. 정밀 프레임 비교용 핵심 컨트롤(belle "0.0초 단위" 요구)이 정렬 활성 doc 에서 전부 오동작한다. `seekBoth` 자체는 warp 경유로 수정됐지만 base 산출이 남아 워핑 활성 경로에 절대시간 혼합이 새는 — 28-06 MEDIUM-1 이 차단하려던 바로 그 클래스다.
**Fix:** 정렬 활성 시 base 는 master(left)만 사용:

```typescript
const base = alignmentActive
  ? leftCurrent
  : hasLeft && hasRight
    ? Math.min(leftCurrent, rightCurrent)
    : hasLeft ? leftCurrent : rightCurrent;
```

(`stepBy` 가 `alignmentActive` 를 deps 로 받거나 `alignmentRef` 를 읽게 할 것.)

## Warnings

### WR-01: warp 목표시각을 [0, dR] 로 클램프하지 않음 — 학생 준비 구간 동안 100ms 마다 음수 seek 폭풍

**File:** `app/src/components/VideoCompare.tsx:311-319, 363-373`, `app/src/lib/alignmentWarp.ts:59-63`
**Issue:** `warpTime` 은 범위 밖을 기울기 1.0 으로 연장하므로 `u0 > r0`(일반 케이스: 학생 준비 구간 > 정은지 트림 시작)에서 `warp(cL) < 0` 인 구간이 존재한다 (`warp(0) = r0 − u0`). tick 의 feedback 보정은 `drift = |cR − targetRefTime(cL)|` 인데, 플레이어가 음수 시각을 0 으로 클램프하는 동안 target 이 음수인 한 drift 는 계속 임계(0.2s)를 넘어 **매 tick(100ms)마다** `rightPlayer.currentTime = 음수` seek 를 발사한다. `cL ≥ u0 − r0 − 0.2` 가 될 때까지 정은지 영상이 seek 폭풍으로 프레임 0 에서 버벅인다 — 코드 자신이 rate 재설정에 대해 경고한 "매 tick 재설정 = 재버퍼" 안티패턴과 동일. 영상 끝쪽에서도 `warp(cL) > dR` seek 가 1회 이상 발생할 수 있다.
**Fix:** `setRightToStudentTime`/drift 계산에서 target 을 `Math.max(0, Math.min(target, dR > 0 ? dR : target))` 로 클램프하고, 클램프된 target 과 cR 의 차이가 임계 이하면 seek 를 생략한다 (정은지는 시작 프레임에서 자연 대기).

### WR-02: 정렬 활성 시 togglePlay 종료 판정·seek 범위·progress bar 가 warped cR 과 min(dL,dR) 도메인을 혼합

**File:** `app/src/components/VideoCompare.tsx:440-449, 468-475, 521-542, 579-584, 622-623`
**Issue:** tick 의 종료 판정은 either-own-end 로 정렬 대응이 됐지만 나머지는 미정합:
- `togglePlay`: `isAtEnd = max(leftCurrent, rightCurrent) >= min(dL,dR) − 0.05`. 워핑으로 `cR = warp(cL)` 가 min-duration 을 조기에 넘으면(정은지 영상이 짧거나 오프셋이 크면) **중간 일시정지 후 재생이 재개가 아니라 0 초 재시작**이 된다.
- `seekBoth` 의 `maxAllowed = min(dL, dR)`: master(left) 도메인의 seek 상한을 정은지 native duration 으로 자른다. 워핑 하에서는 학생초 X 가 정은지초 warp(X) < dR 에 대응할 수 있으므로 비교 가능한 구간인데도 스크럽이 막힌다 (반대 방향의 과다 허용도 가능).
- `progressPct`/`scrubAtX` 의 `duration = min(dL,dR)`: 활성 경로의 재생 정의역(either-own-end 까지의 left 시각)과 다르다 — 재생 중인데 진행 바가 100% 에 고정되는 구간이 생긴다.
**Fix:** `alignmentActive` 일 때 단일 기준 도메인을 left(master)로 통일: `duration = dL`(또는 min(dL, warp⁻¹(dR))), `isAtEnd` 는 `leftCurrent >= duration − 0.05 || rightCurrent >= dR − 0.05`, `seekBoth` 클램프도 같은 도메인으로. 비활성 경로는 현행 유지.

### WR-03: build_motion_alignment 이 non-finite `match.distance` 를 통과시킴 — validator 가 complete_analysis 에서 raise 하면 표시 전용 필드가 분석 전체를 실패시킴

**File:** `backend/shared/python/sunity_shared/analysis/motion_alignment.py:75`, `backend/shared/python/sunity_shared/firestore_admin.py:352-355`, `backend/functions/pipeline/app.py:3340-3369`
**Issue:** `distance = float(getattr(match, "distance", 0.0) or 0.0)` — `float('nan') or 0.0` 은 NaN 이 truthy 라 NaN 이 그대로 남는다 (inf 도 동일). NaN 은 tier 비교(`NaN <= 8.0` → False)를 전부 통과해 tier='disabled' 로 **방출되고**, `_validate_motion_alignment` 의 `distance finite` 검사에서 ValueError 가 난다. 이 검증은 `_attach_motion_alignment` 의 graceful try/except **바깥**(complete_analysis 내부)에서 실행되므로, 채점이 전부 끝난 분석이 표시 전용 필드 때문에 `fail_analysis(server_error)` 로 통째로 실패한다 — helper docstring 의 "방출 실패는 분석 비차단" 약속과 모순. 현재 파이프라인은 `temporal_fill` 이 NaN 각도를 0 으로 채워 발생 확률이 낮지만, DTW 입력 경로가 바뀌면(예: reference 재처리, fill 정책 변경) 조용히 전량 실패 모드가 된다.
**Fix:** 방출 지점에서 1줄 방어:

```python
raw = getattr(match, "distance", 0.0)
distance = float(raw) if isinstance(raw, (int, float)) and math.isfinite(float(raw)) else 0.0
```

(또는 non-finite 면 `_disabled(0.0, "invalid_distance")`.) `test_motion_alignment.py` 에 `distance=float('nan')` 케이스 추가.

### WR-04: veto still 경로는 여전히 `_matched_ref_frame` 반환(18fps angles 공간)을 9fps frames 인덱스로 오독 — 문서화만 되고 미해결/미추적

**File:** `backend/functions/pipeline/app.py:1875-1888`, `backend/shared/python/sunity_shared/analysis/fault_zoom.py:250-275`
**Issue:** 28-05 가 `_matched_ref_frame` docstring 을 "반환은 ref angles(rep) 공간 — 호출측이 변환 책임"으로 갱신했지만, 공유 호출자 `_build_selected_frame_pair` 는 여전히 `_matched_ref_frame(reference_dtw_match, u_idx, r_n)` 로 18fps angles 인덱스를 **9fps frames 개수(r_n)로 클램프해 9fps ref_frames 에 그대로 인덱싱**한다 → veto still 의 기준 프레임이 의도 시각의 2배(대개 끝프레임 클램프)다. 이 still pair 는 Gemini 비전 채점 입력이라 **점수에 영향**하는 known-wrong 상태다. "본체 수정 금지 — 그쪽 입력이 바뀌면 점수가 움직인다"(Open Q2)는 phase 범위 결정으로 존중하되, 클램프가 도메인 오류를 조용히 삼키는 현 상태는 (a) 후속 phase 백로그로 명시 추적되고 (b) `ref_match_source="dtw"` provenance 가 사실상 "2x-shifted dtw" 임이 소비자 쪽에 문서화되어야 한다.
**Fix:** 즉시 코드 수정 대신: 후속 phase 항목 등록 + `_build_selected_frame_pair` 주석에 도메인 결함 명시. 수정 시에는 fault_zoom 과 동일한 `_to_rep_idx` 역변환을 적용하고 채점 회귀(전 fixture 6동작) 게이트로 검증.

### WR-05: tick effect cleanup 에서 released 가능성이 있는 rightPlayer 에 playbackRate 대입 — unmount 시 예외 위험

**File:** `app/src/components/VideoCompare.tsx:430-437`
**Issue:** cleanup 이 `rightPlayer.playbackRate = 1.0` 을 실행한다. React 는 unmount 시 effect cleanup 을 선언 순서로 실행하고, `useVideoPlayer`(컴포넌트 상단에서 먼저 선언)의 내부 cleanup 이 player 를 release 한 뒤 이 cleanup 이 돌 수 있다. expo-video 의 released shared object 에 속성을 쓰면 "released object" 예외가 발생할 수 있어(결과 화면 이탈 = 매번 unmount) 크래시/에러 리포트 위험이 있다. deps 변경(재설치) 경로는 안전하지만 unmount 경로는 검증되지 않았다.
**Fix:** try/catch 로 감싸거나, unmount 인지 deps 변경인지 구분 없이 안전하게:

```typescript
try { if (rightPlayer) rightPlayer.playbackRate = 1.0; } catch { /* released — 무해 */ }
```

실기기(HUMAN-UAT 적립분)에서 결과 화면 진입→이탈 시 에러 로그 확인 권장.

## Info

### IN-01: `_validate_motion_alignment` 가 `reason` 타입을 검증하지 않음

**File:** `backend/shared/python/sunity_shared/firestore_admin.py:308-405`
**Issue:** `reason` 은 키 화이트리스트에만 있고 타입 검사가 없다 — dict/list 가 들어와도 validator 를 통과해 Firestore 에 저장된다 (앱 normalizer 는 non-string 을 버리므로 소비는 안전). 다른 scalar 필드는 전부 타입 강제되는데 reason 만 예외.
**Fix:** `if payload.get("reason") is not None and not isinstance(payload["reason"], str): raise ValueError(...)` 1줄 추가.

### IN-02: normalizeMotionAlignment 이 warped tier 의 구간 기울기 클램프 위반을 검증하지 않음

**File:** `app/src/lib/alignmentWarp.ts:100-166`
**Issue:** 백엔드는 slopes_ok 일 때만 warped 를 방출하지만, 앱 normalizer 는 단조성만 검사한다. 조작/손상된 doc 이 tier='warped' + 기울기 100 앵커를 실으면 `segmentRate` 는 2.0 으로 클램프되는데 `warpTime` 은 클램프가 없어 seek 목표가 크게 튄다 (크래시는 없음 — 재생 이상만). 방어적 소비(V5) 완결성 차원의 defense-in-depth.
**Fix:** warped tier 검증 시 구간 기울기 [RATE_MIN, RATE_MAX] 검사 추가, 위반 → null (legacy 폴백).

### IN-03: 테스트 fixture 의 deductionBreakdown 이 §10 OBJECT 계약과 다른 bare list 형상

**File:** `backend/tests/test_pipeline_motion_alignment.py:45-55`
**Issue:** `_scored_result()` 가 `deductionBreakdown` 을 `[{joint, deduction, reason}]` bare list 로 모델링한다. Phase 24 계약(HIGH-1)은 `{baseline, records, final}` OBJECT 다. deepcopy diff 판정 목적에는 무해하지만, "채점 확정 result fixture" 라는 이름의 fixture 가 계약 밖 형상을 박제하면 후속 독자가 오독할 수 있다.
**Fix:** fixture 를 `{"baseline": 100, "records": [...], "final": 87}` 형상으로 교체 (assert 로직 무변경).

---

_Reviewed: 2026-07-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
