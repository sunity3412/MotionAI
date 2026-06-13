---
phase: 04-ux-occlusion-confidence
reviewer: Codex
date: 2026-06-13
scope: wave2-entry-gate-review
status: revise-before-wave2
wave1_status: coded
plans_reviewed:
  - 04-02-PLAN.md
  - 04-03-PLAN.md
  - 04-04-PLAN.md
  - 04-05-PLAN.md
  - 04-UI-SPEC.md
code_reviewed:
  - app/src/types/analysis.ts
  - app/src/lib/userAnalyses.ts
  - app/src/lib/referenceMotions.ts
  - app/src/app/analysis/result.tsx
  - app/package.json
  - app/app.json
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/synthesis/interfaces.py
  - backend/shared/python/sunity_shared/firestore_admin.py
external_sources_checked:
  - https://r3f.docs.pmnd.rs/getting-started/installation
  - https://docs.expo.dev/versions/latest/sdk/gl-view/
  - https://raw.githubusercontent.com/pmndrs/react-three-fiber/master/packages/fiber/package.json
  - https://raw.githubusercontent.com/pmndrs/drei/master/package.json
verification:
  app_typecheck: "PASS — npm run typecheck"
  phase04_pytest: "PASS — python3 -m pytest backend/tests/phase04/ -q (27 passed)"
  python_command: "FAIL in local shell — python not found, python3 available"
---

# Wave 2 진입 전 게이트 리뷰

## 결론

**판정: revise-before-wave2.**

Wave 1 코드는 현재 기준으로 기본 검증을 통과한다.

- `npm run typecheck` 통과.
- `python3 -m pytest backend/tests/phase04/ -q` → 27 passed.
- `AnalysisResult.joints3d`, `aiSynthesisMeta`, `debugWarnings`, `pole_aligned`, G4 guard, `SYNTHESIS_ENABLED` default OFF 는 실제 코드에 들어갔다.

하지만 **04-02 plan 자체가 그대로 실행되면 typecheck 실패 가능성이 높다.** 특히 `userAnalyses.ts` nullable 대입, `AccuracyLimitBadge` import/export 불일치, dependency install 명령 오기 때문에 Wave 2 진입 전 plan patch 가 필요하다.

04-03~05 는 4차 리뷰 때보다 많이 정리됐다. 다만 후속 wave 에서 실행 게이트가 섞이는 부분은 아직 남아 있다.

## 외부 소스 확인

R3F/Expo 쪽은 2026-06-13 기준 공식 문서/소스와 대체로 정합한다.

- R3F 공식 설치 문서는 `@react-three/fiber@9` 가 React 19와 짝이라고 설명한다. 현재 앱은 React 19.1.0 이므로 방향은 맞다.
- 같은 문서는 React Native에서 `@react-three/fiber/native` import 와 `expo-gl` 설치를 요구한다.
- Expo GLView 문서는 Expo 최신 SDK bundled `expo-gl` 버전을 `~56.0.5` 로 표시하고, 설치 명령으로 `npx expo install expo-gl` 을 안내한다.
- R3F package source 는 v9.6.1 peer dependency 로 React `>=19 <19.3`, React Native `>=0.78`, `expo-gl >=11`, `three >=0.156` 를 둔다. 현재 앱의 React Native 0.81.5 / React 19.1.0 은 맞다.

따라서 Wave 2의 기술 선택 자체는 유지 가능하다. 문제는 plan의 실행 문구와 타입 계약이다.

## Findings

### BLOCKER-1 — 04-02 `userAnalyses.ts` normalize 계획이 현재 `AnalysisResult` 타입과 충돌한다

**근거**

- Wave 1 코드의 `AnalysisResult` 필드는 nullable 이 아니다. `joints3d?: number[]`, `joints3dKeys?: string[]`, `joints3dFrames?: number`, `coordDim?: number`, `space?: 'rtmw3d' | 'pole_aligned'` 로 정의돼 있다 (`app/src/types/analysis.ts:275-279`).
- 그런데 04-02 plan 은 normalize block 에서 invalid/missing 값을 `null` 로 대입하라고 지시한다 (`04-02-PLAN.md:207-215`).
- 현재 app typecheck 는 strict TS 경로로 돌아가며 통과한다. 이 plan 그대로 구현하면 optional-only 필드에 `null` 이 들어가 `tsc` 에서 막히거나, 타입을 억지로 넓히는 수정으로 계약이 흔들릴 수 있다.

**위험**

Wave 2의 핵심 acceptance 인 `npm run typecheck 0 errors` 를 executor 가 plan 그대로 구현하는 순간 깨뜨릴 가능성이 높다. 특히 `result` 는 `AnalysisDoc['result']` 타입으로 좁혀져 있으므로, spread 후 null 값을 넣으면 기존 타입과 불일치한다.

**수정 방안**

둘 중 하나를 명시해야 한다. 권장은 1번이다.

1. `AnalysisResult` 타입을 그대로 유지하고 normalize 에서는 `undefined` 를 사용한다.
   - `joints3d: Array.isArray(result.joints3d) ? result.joints3d : undefined`
   - `joints3dKeys: Array.isArray(result.joints3dKeys) ? result.joints3dKeys : undefined`
   - `joints3dFrames: typeof result.joints3dFrames === 'number' ? result.joints3dFrames : undefined`
   - `coordDim: result.coordDim === 3 ? 3 : undefined`
   - `space: result.space === 'rtmw3d' || result.space === 'pole_aligned' ? result.space : undefined`
2. 또는 `AnalysisResult` 를 nullable contract 로 명시 확장한다.
   - `joints3d?: number[] | null` 등으로 TS + docs/contract.md 동시 갱신.
   - 이 경우 04-01 contract 와 docs까지 같이 바꿔야 하므로 추천하지 않는다.

### BLOCKER-2 — `AccuracyLimitBadge` export/import 계약이 불일치한다

**근거**

- 04-02 plan 은 `AccuracyLimitBadge.tsx` 를 `named export AccuracyLimitBadge` 로 만들라고 한다 (`04-02-PLAN.md:249-257`).
- 같은 plan 의 result 통합 지시는 `import AccuracyLimitBadge from '../../components/AccuracyLimitBadge'` 라는 default import 를 쓰라고 한다 (`04-02-PLAN.md:325-327`).

**위험**

그대로 구현하면 default export 가 없어서 typecheck/import 에러가 난다. Wave 2의 `npm run typecheck` gate 를 정면으로 깨뜨리는 문서 오류다.

**수정 방안**

04-02 result.tsx action 을 named import 로 고친다.

```ts
import { AccuracyLimitBadge } from '../../components/AccuracyLimitBadge';
```

또는 컴포넌트를 default export 로 바꾸되, 이 repo의 최근 컴포넌트 패턴은 named export가 많으므로 named import가 더 작다.

### HIGH-1 — dependency install 명령이 shell 명령으로 잘못 적혀 있다

**근거**

- 04-02 Task 1 action 은 `npm install three @react-three/fiber expo-three @react-three/drei + npx expo install expo-gl` 라고 쓴다 (`04-02-PLAN.md:117`).
- shell 에서 `+` 는 명령 연결자가 아니다. 이 문장을 복사하면 `npm install` 에 `+`, `npx`, `expo`, `install`, `expo-gl` 이 패키지 인자로 들어갈 수 있다.
- R3F 공식 설치 문서는 React Native에서 `expo install expo-gl` 과 `npm install three @react-three/fiber` 를 별도 단계로 안내한다.

**위험**

package-lock 이 잘못 생성되거나 설치가 실패한다. Wave 2는 실기기 smoke 전 package-lock 안정성이 중요하므로, 이 오기는 반드시 고쳐야 한다.

**수정 방안**

명령을 분리한다.

```bash
cd /Users/kimtaesung/Dev/SunityMotion/app
npm install three @react-three/fiber @react-three/drei expo-three
npx expo install expo-gl
```

추가로 설치 후 아래를 확인한다.

```bash
npm ls three @react-three/fiber @react-three/drei expo-three expo-gl expo-asset expo-file-system
```

`expo-asset` / `expo-file-system` 은 현재 lock/node_modules 에 transitive 로 존재하지만, R3F native peer surface 에 걸려 있으므로 누락 시 `npx expo install expo-asset expo-file-system` 로 명시 설치한다.

### HIGH-2 — `aiSynthesisMeta.debugWarnings` 를 normalize 계획에서 드롭한다

**근거**

- Wave 1 contract 는 raw reason 을 `aiSynthesisMeta.debugWarnings` 로 분리 보존한다 (`app/src/types/analysis.ts:223-227`, `backend/functions/pipeline/app.py:641-688`).
- 04-02 normalize plan 은 `warnings`, audit 필드, cost 필드는 보존하지만 `debugWarnings` 를 복사하지 않는다 (`04-02-PLAN.md:218-244`).

**위험**

UI에는 노출하지 않더라도 raw reason 은 운영/리뷰 근거다. Wave 1에서 HIGH-4 fix 로 만든 public warning vs debug reason 분리가 Wave 2 normalize 에서 사라진다.

**수정 방안**

04-02 normalize block 에 추가한다.

```ts
debugWarnings: Array.isArray(meta.debugWarnings) ? meta.debugWarnings : [],
warnings: Array.isArray(meta.warnings) ? meta.warnings : [],
```

audit/cost 필드도 Firestore raw 방어 목적이면 `typeof` 검증과 기본값을 둔다. 현재 plan 의 `modelId: meta.modelId` 식 대입은 raw Firestore 방어 계층으로는 약하다.

### HIGH-3 — reference `joints3d` 는 04-05가 만들지만 `ReferenceMotion` 타입/normalizer 계획이 없다

**근거**

- 04-05는 `reference/{motion_id}` top-level mirror 에 `joints3d / joints3dKeys / joints3dFrames / coordDim / space` 를 쓰겠다고 한다 (`04-05-PLAN.md:178-181`, `04-05-PLAN.md:198-202`).
- UI-SPEC 은 mode1 에서 `referenceJoints={refMotion?.joints3d}` 를 전제로 둔다 (`04-UI-SPEC.md:156-158`).
- 현재 `ReferenceMotion` 타입에는 reference `joints3d` 필드가 없다 (`app/src/types/analysis.ts:330-379`).
- 현재 `referenceMotions.ts` normalize 도 해당 필드를 읽지 않는다 (`app/src/lib/referenceMotions.ts:70-155`).
- 04-02 plan 의 result.tsx 통합은 `PoseViewer3D` props 에 `referenceJoints?` 를 정의하지만 실제 삽입 예시는 사용자 `joints3d` 만 넘긴다 (`04-02-PLAN.md:314`, `04-02-PLAN.md:340-344`).

**위험**

04-05에서 reference `joints3d` 를 써도 앱 타입/normalizer 가 버린다. 이후 mode1 reference overlay 를 붙이려 할 때 `refMotion?.joints3d` 는 TS 에서 존재하지 않거나 runtime 에서 undefined 로만 남는다.

**수정 방안**

선택지를 명시해야 한다.

- Wave 2 MVP 에서는 user-only 3D viewer 로 간다: `04-02` / UI-SPEC 에 "referenceJoints 는 prop만 예약, 이번 wave 에는 전달하지 않음" 을 명시한다.
- Wave 5 이후 reference overlay 를 목표로 한다: `04-05` 또는 별도 follow-up 에 `app/src/types/analysis.ts ReferenceMotion` 과 `app/src/lib/referenceMotions.ts normalize()` 필드 추가를 files_modified/acceptance 에 포함한다.

현재 상태처럼 "04-05는 mirror, UI-SPEC은 소비, 타입/normalizer는 무계획" 으로 두면 안 된다.

### HIGH-4 — 04-05의 Wave 3b 비차단 원칙과 cylindrical axis_b 성공 기준이 섞여 있다

**근거**

- 04-03은 Wave 3b 실 RunPod RTMW 재추론이 미완이어도 Wave 2/UI와 Wave 5/reference 진행 가능하다고 말한다 (`04-03-PLAN.md:60`, `04-03-PLAN.md:275-277`).
- 04-05 frontmatter도 3b 미완이어도 Wave 5 진행 가능하다고 한다 (`04-05-PLAN.md:8-11`).
- 그런데 04-05 must-have / verification / success criteria 는 여전히 `cylindrical_mesh >= baseline` 을 Wave 5 완료 조건처럼 둔다 (`04-05-PLAN.md:26`, `04-05-PLAN.md:450-466`).
- 같은 04-05 objective 는 evaluate_4way 를 reference migration 과 분리된 평가 산출물이라고 한다 (`04-05-PLAN.md:60`).

**위험**

Wave 5 실행자가 3b skip 상태에서 reference migration 을 완료해도 success criteria 를 만족했는지 판단할 수 없다. 반대로 axis_b 를 맞추기 위해 placeholder cylindrical smoke 결과를 migration gate 로 오해할 수 있다.

**수정 방안**

04-05 완료 기준을 두 층으로 분리한다.

- **Wave 5 migration 완료 기준:** 5개 reprocess JSON + schema gate + `reference/{id}/versions/phase4_v1` write + active flip + rollback + belle 점수 비악화.
- **Optional / RunPod accuracy evidence:** Wave 3b가 준비된 경우에만 `cylindrical_mesh >= baseline` 을 별도 evidence 로 첨부. 3b skip 상태에서는 SKIP 이 정상이며 Wave 5 완료를 막지 않는다.

### MEDIUM-1 — 04-03~05 verify 명령은 이 로컬 환경에서 `python` 때문에 실패한다

**근거**

- 현재 shell 에서 `python` 은 없음. `python3` 는 `/opt/homebrew/bin/python3` 로 존재한다.
- 실제 확인: `python -m pytest ...` 는 `zsh: command not found: python` 으로 실패했고, `python3 -m pytest backend/tests/phase04/ -q` 는 27 passed.
- 04-03~05 plan 에는 `python -m pytest`, `python -c`, `python scripts/...` 명령이 다수 남아 있다 (`04-03-PLAN.md:155`, `04-03-PLAN.md:299`, `04-04-PLAN.md:123`, `04-05-PLAN.md:259`, `04-05-PLAN.md:356` 등).

**위험**

Codex/local executor 가 같은 환경에서 후속 wave 를 진행하면 verify 명령이 코드와 무관하게 실패한다.

**수정 방안**

local verify 명령은 `python3` 로 바꾸거나, repo 표준으로 `python` symlink/venv activation 을 plan 전제에 명시한다. RunPod 명령은 해당 Pod에 `python` alias 가 있다면 유지 가능하지만, local acceptance 는 `python3` 로 맞추는 게 안전하다.

### MEDIUM-2 — 04-05 success criteria 에 "ast 검증" 잔재가 남아 있다

**근거**

- 04-05 본문은 fake Firestore behavioral path assertion 으로 AST 검색을 폐기했다고 정리했다 (`04-05-PLAN.md:134-140`, `04-05-PLAN.md:263-268`).
- 하지만 success criteria 는 아직 "versioned write ast 검증" 이라고 쓴다 (`04-05-PLAN.md:464`).

**위험**

executor 가 최종 요약/검증에서 이전 AST constant 검증으로 회귀할 여지가 있다.

**수정 방안**

`04-05-PLAN.md:464` 를 "FakeFirestoreClient behavioral path 검증" 으로 바꾼다.

### MEDIUM-3 — 04-02 success criteria 에 UI-SPEC draft 문구가 남아 있다

**근거**

- `04-UI-SPEC.md` 는 이제 `status: approved` 다 (`04-UI-SPEC.md:4`).
- 04-02 objective note 도 approved 라고 말한다 (`04-02-PLAN.md:81`).
- 그러나 04-02 success criteria 는 아직 "UI-SPEC status draft → approved 기록" 이라고 한다 (`04-02-PLAN.md:419`).

**위험**

실행자가 이미 완료된 승인 상태를 다시 작업 항목으로 잡거나, summary 에 잘못된 상태 전환을 기록할 수 있다.

**수정 방안**

`04-02-PLAN.md:419` 를 "UI-SPEC status approved 유지 확인" 으로 바꾼다.

### MEDIUM-4 — 04-02 key link 는 helper보다 raw includes 를 강조한다

**근거**

- 04-02 done gate 는 `hasSynthesisWarning(doc?.result, 'ai_synthesis_failed')` 를 쓰라고 고쳐졌다 (`04-02-PLAN.md:277`, `04-02-PLAN.md:337-339`).
- 하지만 key link 는 아직 `result.aiSynthesisMeta.warnings.includes('ai_synthesis_failed')` 를 전면에 둔다 (`04-02-PLAN.md:58-60`).

**위험**

raw includes 자체는 canonical field 를 읽으므로 틀리진 않다. 다만 null/undefined guard 를 helper 에 모으려는 3차/4차 정리 방향이 약해진다.

**수정 방안**

key link 도 `hasSynthesisWarning(result, 'ai_synthesis_failed')` 로 맞춘다. 내부 구현 설명으로만 `result.aiSynthesisMeta?.warnings?.includes(...)` 를 둔다.

## Wave 2 진입 전 최소 패치

1. 04-02 `userAnalyses.ts` normalize block 의 `null` 대입을 `undefined` 로 바꾸거나 타입을 nullable 로 명시 확장한다. 권장은 `undefined`.
2. `AccuracyLimitBadge` import 를 named import 로 수정한다.
3. dependency install 명령에서 `+` 를 제거하고 npm/expo install 을 분리한다.
4. `debugWarnings` normalize 보존을 추가한다.
5. reference overlay 를 이번 Wave 2에서 제외할지, Wave 5 이후 타입/normalizer 추가까지 포함할지 명시한다.
6. 04-05 axis_b gate 를 migration 완료 기준과 optional RunPod accuracy evidence 로 분리한다.
7. 04-03~05 local verify 명령은 `python3` 기준으로 정리한다.

## 승인 가능 조건

위 최소 패치 후에는 Wave 2 진입 가능하다. 현재 남은 문제는 Wave 1 코드의 기능 실패라기보다 **Wave 2 plan 문구가 실제 TS 계약과 어긋나는 문제**다. 코드 베이스 자체는 Wave 2를 시작할 준비가 되어 있다.
