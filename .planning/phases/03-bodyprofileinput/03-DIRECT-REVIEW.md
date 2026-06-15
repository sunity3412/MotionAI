---
phase: 03-bodyprofileinput
reviewer: Codex
date: 2026-06-15
scope: direct-plan-review
status: revise-before-execution
reviewed_plans:
  - 03-CONTEXT.md
  - 03-RESEARCH.md
  - 03-PATTERNS.md
  - 03-VALIDATION.md
  - 03-01-PLAN.md
  - 03-02-PLAN.md
  - 03-03-PLAN.md
---

# Phase 3 Direct Review

## Executive Verdict

Phase 3 방향은 맞다. "마이페이지 상시 편집 + 첫 분석 직전 1회 선택 권유"는 게스트 우선 파일럿과 충돌하지 않고, `users/{uid}.bodyProfile` 저장 후 analysis doc 에 snapshot 하는 설계도 현재 파이프라인과 잘 맞는다. 새 endpoint 없이 `loading.tsx` 의 analysis doc 생성 지점을 쓰는 판단도 좋다.

다만 **현재 plan 그대로 실행하면 몇 군데에서 막힌다.** 특히 결과 화면 표기 설계가 analysis snapshot 원칙과 어긋나고, `analyze.tsx` 게이트는 현재 즉시 라우팅 구조를 멈춰 세울 pending state 가 명시돼 있지 않다. 또한 몇 개 grep 검증은 현재 코드에 이미 존재하는 주석/스타일 때문에 false fail 한다.

내 판정은 **짧은 plan patch 후 실행**이다. 구현 범위는 적절하지만, 아래 BLOCKER/HIGH 항목은 실행 전에 반영해야 한다.

## Reviewed Inputs

- `.planning/phases/03-bodyprofileinput/03-CONTEXT.md`
- `.planning/phases/03-bodyprofileinput/03-RESEARCH.md`
- `.planning/phases/03-bodyprofileinput/03-PATTERNS.md`
- `.planning/phases/03-bodyprofileinput/03-VALIDATION.md`
- `.planning/phases/03-bodyprofileinput/03-01-PLAN.md`
- `.planning/phases/03-bodyprofileinput/03-02-PLAN.md`
- `.planning/phases/03-bodyprofileinput/03-03-PLAN.md`
- `.planning/ROADMAP.md` Phase 3
- `.planning/REQUIREMENTS.md` BODY-02
- `app/src/app/analysis/loading.tsx`
- `app/src/app/(tabs)/analyze.tsx`
- `app/src/app/(tabs)/profile.tsx`
- `app/src/app/analysis/result.tsx`
- `app/src/lib/userAnalyses.ts`
- `app/src/types/analysis.ts`
- `backend/functions/pipeline/app.py`
- `backend/shared/python/sunity_shared/models.py`
- `backend/shared/python/sunity_shared/analysis/coach_writer.py`
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py`

## Findings

### R1. 결과 화면은 live profile 이 아니라 analysis snapshot 을 표시해야 한다

Severity: **BLOCKER**

Evidence:

- 03-01 은 `loading.tsx` 에서 `users/{uid}/analyses/{analysisId}.bodyProfile` 로 snapshot 하는 설계를 잡고 있다.
- 03-03 은 `result.tsx` 에 `useBodyProfile()` 를 추가해 현재 `users/{uid}.bodyProfile` 을 표시한다고 되어 있다.
- 현재 `AnalysisDoc` 타입에는 top-level `bodyProfile` 이 없다 (`app/src/types/analysis.ts:286-300`).
- 현재 `useAnalysisDoc()` normalize 는 raw top-level 필드 중 `bodyProfile` 을 보존하지 않는다 (`app/src/lib/userAnalyses.ts:27-160`).

Risk:

- 사용자가 나중에 키/몸무게/통증부위를 수정하면 과거 분석 결과 화면도 새 profile 을 표시한다.
- analysis doc 에 snapshot 을 저장해도 앱 normalize 가 버리므로 결과 화면에서는 snapshot 을 쓸 수 없다.
- "분석 당시 입력값"과 "현재 입력값"이 섞이면 Phase 3 의 재현성 원칙이 깨진다.

Recommendation:

- `BodyProfile` 타입을 만든 뒤 `AnalysisDoc` 에 `bodyProfile?: BodyProfile | null` 을 추가한다.
- `app/src/lib/bodyProfile.ts` 의 normalizer 를 `normalizeBodyProfile` 로 export 하고, `userAnalyses.ts` normalize 에서 `raw.bodyProfile` 을 같은 함수로 정규화해 보존한다.
- `result.tsx` 는 `storedDoc?.bodyProfile` 을 우선 표시한다.
- `useBodyProfile()` live read 는 old doc fallback 또는 profile tab 전용으로만 둔다. 결과 화면 기본 소스는 snapshot 이어야 한다.

### R2. `analyze.tsx` 권유 게이트는 pending picked video state 없이는 구현이 불완전하다

Severity: **BLOCKER**

Evidence:

- 현재 `handleResult()` 는 영상 검증 후 바로 `routeAfterPick(...)` 를 호출한다 (`app/src/app/(tabs)/analyze.tsx:124-140`).
- `routeAfterPick()` 는 즉시 `/analysis/loading` 또는 `/analysis/reference` 로 push 한다 (`app/src/app/(tabs)/analyze.tsx:83-122`).
- 03-03 은 "pick 완료 후 routeAfterPick 직전 게이트"라고만 되어 있고, modal 표시 중 라우팅에 필요한 `Picked` 값을 어디에 보관할지 명시하지 않는다.

Risk:

- 모달을 띄우려면 라우팅을 중단해야 하는데, 현재 구조는 pick 결과를 즉시 소비한다.
- [입력하기] 후 저장, [건너뛰기], backdrop/native back 이후 모두 동일한 picked video 로 라우팅을 재개해야 한다.
- 이 상태가 명시되지 않으면 executor 가 routeAfterPick 호출 위치만 옮기다 mode/referenceMotionId stale closure 또는 영상 선택값 유실 버그를 만들 가능성이 높다.

Recommendation:

- 03-03 에 `pendingPicked: Picked | null` 를 명시한다.
- `handleResult()` 는 `maybePromptBeforeRoute(picked)` 만 호출하고, gate 대상이면 `setPendingPicked(picked); setPromptVisible(true); return;` 한다.
- `continuePendingRoute()` 는 `const picked = pendingPicked; setPendingPicked(null); setPromptVisible(false); if (picked) routeAfterPick(picked);` 형태로 단일화한다.
- [입력하기] 저장 완료, [건너뛰기], backdrop, native back 은 모두 `continuePendingRoute()` 로 수렴시킨다.
- mode1 에서 reference 선택 전 prompt 를 띄울지, reference 선택 후 loading 직전 prompt 를 띄울지 plan 에 명시한다. 현재 plan 의 위치는 "영상 pick 직후, reference 선택 전"이다.

### R3. 검증 grep 이 현재 코드 때문에 false fail 한다

Severity: **HIGH**

Evidence:

- 03-02 Task 2 verify 는 `profile.tsx` 전체에서 `fontSize:[0-9]` 를 금지한다.
- 현재 `profile.tsx` 에 이미 `fontSize: 28` 이 있다 (`app/src/app/(tabs)/profile.tsx:177`).
- 03-03 Task 2 verify 는 `result.tsx` 전체에서 hex color 를 금지한다.
- 현재 `result.tsx` 주석에 `#FF4B33` 이 이미 있다 (`app/src/app/analysis/result.tsx:95`, `:236`).

Risk:

- 구현이 맞아도 plan 검증이 실패한다.
- executor 가 Phase 3 와 무관한 기존 스타일/주석을 제거하거나 리팩터링하게 된다.

Recommendation:

- full-file grep 대신 신규 파일만 검사한다: `BodyProfileForm.tsx`, `BodyProfilePromptModal.tsx`.
- 기존 파일은 diff 기반 검증으로 바꾼다. 예: "새로 추가한 styles/bodyProfile 섹션에 hardcoded hex/fontSize 없음".
- 최소 수정안: `profile.tsx` 와 `result.tsx` grep gate 에 기존 line allowlist 를 둔다.

### R4. `weightKg` 비유입 gate 가 너무 좁다

Severity: **HIGH**

Evidence:

- 03-01 Task 3 verify 는 `dimensions.py`, `kismam.py`, `body_normalizer.py` 만 grep 한다.
- Phase 3 요구는 `weightKg` 가 분석 단정/점수 산출에 쓰이지 않는 것이다.
- 현재 관련 분석 모듈에는 `body_normalization.py`, `force_signals.py`, `force_pattern.py` 등도 있다.

Risk:

- `weightKg` 가 다른 scoring/analysis module 로 들어가도 gate 가 잡지 못한다.
- D-05 의 핵심 안전장치가 plan 문구보다 약하게 검증된다.

Recommendation:

- 금지 대상은 "coach context/display/storage 를 제외한 scoring/analysis consumers" 로 명시한다.
- 최소 gate 예:

```bash
! rg -n "weightKg|weight_kg" \
  backend/shared/python/sunity_shared/analysis/dimensions.py \
  backend/shared/python/sunity_shared/analysis/kismam.py \
  backend/shared/python/sunity_shared/analysis/body_normalization.py \
  backend/shared/python/sunity_shared/analysis/body_normalizer.py \
  backend/shared/python/sunity_shared/analysis/force_signals.py \
  backend/shared/python/sunity_shared/analysis/force_pattern.py
```

- `pipeline/app.py` 와 `coach_writer` 쪽은 허용 경로로 별도 분리한다.

### R5. snapshot 시 client-side normalize 사용을 plan 에 명시해야 한다

Severity: **MEDIUM-HIGH**

Evidence:

- 03-01 Task 2 는 `bodyProfile.ts` 에 defensive `normalize()` 를 만든다.
- 03-01 Task 3 은 `loading.tsx` 가 `users/{uid}.bodyProfile` 을 읽고 analysis doc 에 spread 한다고만 되어 있다.

Risk:

- `loading.tsx` 가 Firestore raw object 를 그대로 snapshot 하면 오래된 doc, dev console 수정, 잘못된 타입이 analysis doc 에 들어갈 수 있다.
- pipeline 은 `normalize_body_profile()` 로 graceful 하게 막더라도, 앱 결과 화면과 contract 문서에는 malformed snapshot 이 남을 수 있다.

Recommendation:

- `bodyProfile.ts` 에 `normalizeBodyProfile(raw)` 와 `getBodyProfileOnce()` 를 export 한다.
- `loading.tsx` 는 Firestore 직접 `getDoc` 로 raw spread 하지 말고 `getBodyProfileOnce()` 를 호출한다.
- "전 필드 empty 면 snapshot 생략" 규칙도 helper 안에 둔다.

### R6. 폼 UI 는 small screen + keyboard safe 레이아웃이 필요하다

Severity: **MEDIUM**

Evidence:

- Phase 3 은 앱의 첫 실제 `TextInput` 폼이다.
- 03-02 는 iOS number-pad dismiss caveat 는 잡았지만, 작은 화면에서 5필드 + CTA 가 키보드에 가려지는 경우를 acceptance 에 명시하지 않는다.

Risk:

- TestFlight 실기기에서 저장 버튼이 키보드 뒤에 숨거나, 통증부위 칩이 하단 safe area 와 겹칠 수 있다.
- 부분 입력 UX 가 "가볍게" 느껴지지 않는다.

Recommendation:

- `BodyProfileForm` 은 `KeyboardAvoidingView` 또는 `ScrollView` 기반으로 만든다.
- CTA 는 하단 safe-area 여백을 확보하고, keyboard open 상태에서도 접근 가능해야 한다.
- Manual verification 에 iPhone SE급 작은 화면 입력/저장 시나리오를 추가한다.

## Strengths

- Plan 03-01/02/03 의 wave 순서는 좋다. 계약/저장/snapshot seam 을 먼저 만들고, 그 위에 profile UI 와 prompt UI 를 얹는 순서가 맞다.
- 새 upload endpoint 를 만들지 않고 analysis doc snapshot 을 쓰는 판단은 현재 `referenceMotionId` 패턴과 잘 맞는다.
- `weightKg` 보조-only, 유연성/근력 입력 제외, partial input 허용은 Phase 3 의 scope creep 을 잘 막는다.
- RN primitive 로 폼을 만드는 방향은 EAS/native dependency 리스크를 줄인다.
- Gemini/Cerebras writer 는 현재 `bodyProfile` key 를 prompt 에 쓰지 않으므로, D-04 seam 을 추가해도 Phase 13 전에는 코칭 문장 행동 변화가 거의 없다.

## Suggested Patch Summary

실행 전 plan 에 최소한 아래 수정만 반영하면 된다.

1. 03-01 에 `AnalysisDoc.bodyProfile` + `userAnalyses.normalize()` 보존 작업을 추가한다.
2. 03-03 결과 화면 소스를 `useBodyProfile()` live read 에서 `storedDoc?.bodyProfile` snapshot 으로 바꾼다.
3. 03-03 `analyze.tsx` 게이트에 `pendingPicked` / `continuePendingRoute()` state machine 을 명시한다.
4. 03-02/03 hardcoded style grep 을 신규 파일 또는 diff 기반으로 좁힌다.
5. D-05 grep gate 에 `body_normalization.py` 등 scoring-adjacent module 을 포함한다.
6. `BodyProfileForm` acceptance 에 small-screen keyboard-safe 검증을 추가한다.

## Risk Assessment

Overall risk: **MEDIUM-HIGH until patched, LOW-MEDIUM after patch**.

Phase 3 자체는 알고리즘 변경이 아니라 계약 + UI + context seam 이라 blast radius 는 작다. 하지만 analysis snapshot 과 live profile 을 혼동하면 결과 화면의 의미가 틀어지고, 잘못된 grep gate 는 실행을 불필요하게 막는다. 위 수정 후에는 구현 난이도와 운영 리스크 모두 낮은 편이다.
