---
phase: 26-onboarding-upload-guide
reviewed: 2026-07-07T15:33:51Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - app/src/app/(tabs)/analyze.tsx
  - app/src/app/(tabs)/index.tsx
  - app/src/app/(tabs)/profile.tsx
  - app/src/app/analysis/loading.tsx
  - app/src/app/analysis/reference.tsx
  - app/src/app/analysis/result.tsx
  - app/src/app/help.tsx
  - app/src/app/index.tsx
  - app/src/app/tutorial.tsx
  - app/src/components/BodyProfileForm.tsx
  - app/src/lib/bodyProfile.ts
  - app/src/lib/onboarding.ts
  - app/src/types/analysis.ts
  - backend/shared/python/sunity_shared/models.py
  - docs/contract.md
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-07-07T15:33:51Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 26 (onboarding-upload-guide) 변경분 15개 파일을 diff base 9cebb82 기준으로 전수 검토했다. 구조적(fallow) 프리패스는 제공되지 않아 본 리뷰는 내러티브 findings 만 포함한다. `npm run typecheck` (앱의 유일한 정적 게이트) PASS 확인.

리뷰 포커스 항목 검증 결과:

- **learningOptIn 기록 경로** — 건전. `buildOptInRouteParams` 는 true 인 키만 `'1'` 로 방출하고, loading.tsx 는 `learningOptIn === '1'` 엄격 비교 후 `setDoc` 에 **항상 boolean** 으로 기록한다 (조건부 spread 아님, loading.tsx:147). param 유실/오염/배열화 시 false(미동의) 로 강하 — opt-out 반전 후에도 fail-safe 방향(미동의)이 유지되고 undefined/crash 경로 없음. mode1 미선택 경로(analyze → reference → loading)의 passthrough (reference.tsx:104) 도 확인.
- **talkv → lowQuality → bodyProfile 직렬 체인** — 이중 경고 없음(talkv 감지 시 `return` 으로 화질 검사 스킵, analyze.tsx:316-325), 영상 유실 없음(continue/cancel 4-경로 모두 보류 picked 캡처 후 처리). 단, 모달 체이닝의 iOS presentation 타이밍 리스크 2건 발견 (WR-01, WR-02).
- **result.tsx wrapper/Content 분리** — 건전. wrapper 훅은 전부 조기 return 이전 호출, 자식은 non-null `result: AnalysisResult` prop 으로만 마운트되고 자식 내부에 null 분기 잔재 없음. 훅 순서 렌더 간 안정.
- **튜토리얼 라우팅** — 건전. `hasSeenTutorial()` 은 내부 try/catch 로 절대 reject 하지 않고 읽기 실패 시 `true`(본 것으로 간주) 반환 → 스토리지 오류가 홈 진입을 막지 않는다. `markTutorialSeen()` 은 fire-and-forget graceful.
- **models.py** — 주석 17줄 추가만 확인(diff 검증). 로직 드리프트 0. 3-way lockstep (analysis.ts:619 / models.py / contract.md §3) 세 곳 모두 opt-out 의미·fail-safe 방향 서술 일치.

## Warnings

### WR-01: talkv/lowQuality [이대로 계속] 직후 BodyProfilePromptModal 즉시 present — 코드 자신이 문서화한 iOS Modal presentation 충돌 클래스 미방어

**File:** `app/src/app/(tabs)/analyze.tsx:347-351` (continueTalkv), `:332-336` (continueLowQuality), `:613-620` (BodyProfilePromptModal)
**Issue:** `continueTalkv` 는 `setTalkvPicked(null)` (talkv Modal fade-out 시작)과 동기적으로 `maybePromptBeforeRoute` 를 호출하고, 첫-pick 게이트 조건(프로필 미입력 AND 미dismiss AND 세션 첫 권유)이 참이면 같은 커밋에서 `setPromptVisible(true)` 로 두 번째 RN Modal(BodyProfilePromptModal, Modal 컴포넌트 확인함)을 present 한다. 이 파일 스스로 "iOS 는 Modal fade-out 중에 VC 를 띄우면 presentation 충돌" (analyze.tsx:54-57) 이라며 picker 재오픈에는 `TALKV_REPICK_DELAY_MS=450` 을 두었는데, 동일 충돌 클래스인 경고모달→권유모달 체인에는 지연이 없다. 충돌 시 증상이 나쁘다: `pendingPicked` 는 세팅됐지만 모달이 화면에 뜨지 않아 사용자는 소스 선택 화면에서 아무 일도 안 일어난 것처럼 보이고 선택한 영상이 사실상 유실된다. "첫 사용자 + 카톡 영상" 조합은 파일럿에서 가장 흔한 시나리오라 발생 확률이 낮지 않다.
**Fix:** 경고 모달 경유 재개 시 권유 모달 오픈을 닫힘 애니메이션 뒤로 지연:
```tsx
const notEntered = profile === null;
const notDismissed = promptDismissedAt == null;
if (notEntered && notDismissed) {
  setPendingPicked(picked);
  // 경고 Modal(fade) 닫힘 후 present — picker 재오픈(TALKV_REPICK_DELAY_MS)과 동일 근거.
  setTimeout(() => setPromptVisible(true), TALKV_REPICK_DELAY_MS);
  return;
}
```
(또는 `InteractionManager.runAfterInteractions` / Modal `onDismiss` 콜백 후 open. 26-06 실기기 확인이 이 정확한 경로 — 프로필 미입력 상태에서 talkv [이대로 계속] — 를 커버했는지도 검증 필요.)

### WR-02: cancelTalkv 의 450ms 지연 picker 재오픈 — 타이머 미정리 + busy 미가드로 동시 presentation 레이스

**File:** `app/src/app/(tabs)/analyze.tsx:358-363`
**Issue:** `cancelTalkv` 는 `setTimeout(() => void pickFromLibrary(), 450)` 을 걸지만 (1) 타이머 핸들을 보관/정리하지 않아 450ms 안에 사용자가 뒤로가기(backToModeSelect)·탭 전환·다른 화면 이동을 해도 앨범 picker 가 뜬금없이 열리고, (2) `busy` 가드를 안 타므로 450ms 안에 [즉석 촬영] 을 탭하면 카메라 present 중에 `pickFromLibrary` 가 두 번째 picker VC 를 동시 present 시도한다 — 이 파일이 회피하려는 바로 그 iOS presentation 충돌. 또한 talkv 모달의 native back(`onRequestClose={cancelTalkv}`)도 앨범을 재오픈하는데, 같은 화면의 lq 모달 native back 은 조용히 버리기만 해서(cancelLowQuality) 동작이 비대칭이다.
**Fix:**
```tsx
const repickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
useEffect(() => () => { if (repickTimer.current) clearTimeout(repickTimer.current); }, []);

const cancelTalkv = () => {
  setTalkvPicked(null);
  repickTimer.current = setTimeout(() => {
    if (!busy) void pickFromLibrary();
  }, TALKV_REPICK_DELAY_MS);
};
```
(busy 는 ref 미러 또는 함수 내 최신값 참조 필요 — stale closure 주의. native back 은 재오픈 없이 버리기만 하는 별도 핸들러 분리 권장.)

## Info

### IN-01: samples 삭제 후 loading.tsx 의 presetAnalysisId 분기가 호출자 0 인 죽은 경로 + stale 주석

**File:** `app/src/app/analysis/loading.tsx:38, 289, 311-314, 322`
**Issue:** 이번 phase 에서 samples.tsx(+simulatedResult/simulationWriter)를 삭제했는데, `/analysis/loading` 에 `analysisId` 를 넘기는 유일한 호출자가 samples 였다 (grep 확인: 현재 push 호출자는 analyze.tsx 2곳·reference.tsx 1곳뿐, 모두 analysisId 미전달). `presetAnalysisId` 업로드-스킵 분기는 이제 도달 불가 코드이고, 주석 3곳("samples 경로")은 존재하지 않는 진입점을 가리킨다.
**Fix:** 분기를 유지할 거면 주석을 "구독-전용 진입(현재 호출자 없음, 방어)" 으로 갱신하고, 아니면 param/분기 제거. 최소한 stale 주석 3곳은 정리.

### IN-02: /analysis/result 호출부들이 이제 읽지 않는 param(mode/referenceMotionId/referenceMotionName)을 계속 전달

**File:** `app/src/app/analysis/loading.tsx:362-371`, `app/src/app/(tabs)/index.tsx:137-149`
**Issue:** result.tsx wrapper 는 이번 phase 리팩터 후 `name`/`analysisId` 만 읽는다 (result.tsx:546-549, "referenceMotionId/Name·mode 파라미터는 … 소멸" 주석). 그러나 loading.tsx 의 done-라우팅과 홈 최근분석 카드는 여전히 mode/referenceMotionId/referenceMotionName 을 전달한다 — 무해하지만 죽은 배선이라 다음 독자가 소비된다고 오인하기 쉽다.
**Fix:** 두 호출부에서 미소비 param 제거 (history 탭 등 다른 호출부도 동일 정리 대상인지 확인).

### IN-03: AnalysisDoc.learningOptIn 이 TS 계약 타입에 선언됐지만 userAnalyses.normalize() 읽기 경로에서 항상 탈락

**File:** `app/src/types/analysis.ts:619`, `app/src/lib/userAnalyses.ts:322-348`
**Issue:** `normalize()` 는 화이트리스트 방식으로 필드를 조립하는데 `learningOptIn` 을 매핑하지 않는다. 따라서 Firestore 에 true/false 가 기록돼 있어도 앱이 읽는 `AnalysisDoc` 에서는 항상 `undefined` 다. 현재 앱 내 소비처가 없고 Phase 22 게이트는 Firestore 를 직접 읽으므로 당장 버그는 아니지만, `angles` 류와 달리 "normalize 제외" 가 명시돼 있지 않아 향후 동의 상태 표시 UI 를 붙일 때 조용히 틀어진다.
**Fix:** 의도적 제외라면 analysis.ts:619 주석에 "앱 읽기 경로 normalize 제외(백엔드 전용 소비)" 를 명시하거나, normalize 에 `...(typeof raw.learningOptIn === 'boolean' ? { learningOptIn: raw.learningOptIn } : {})` 1줄 추가.

### IN-04: (pre-existing) 홈 챌린지 우회 진입 시 뒤로가기가 모드 선택으로 돌아가지 못하는 루프

**File:** `app/src/app/(tabs)/analyze.tsx:147-157`
**Issue:** 이번 phase 변경분은 아니지만 리뷰 대상 파일에서 관찰됨. 챌린지 카드로 진입(`referenceMotionId` param 보유)한 뒤 소스 선택 화면의 뒤로가기(backToModeSelect)를 누르면 `setMode(null)` 직후 F1-fix useEffect(`referenceMotionId && mode === null → setMode('mode1')`)가 즉시 mode1 을 재설정해 화면이 소스 선택으로 되돌아온다 — 탭 전환 외에는 모드 선택 단계로 나갈 수 없다.
**Fix:** backToModeSelect 에서 param 클리어(`router.setParams({ referenceMotionId: undefined })`) 또는 "사용자가 명시적으로 뒤로갔음" ref 가드로 effect 재발동 차단. 별도 quick 작업으로 처리 권장.

---

_Reviewed: 2026-07-07T15:33:51Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
