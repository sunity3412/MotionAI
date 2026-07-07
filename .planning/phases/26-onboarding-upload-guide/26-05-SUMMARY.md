---
phase: 26-onboarding-upload-guide
plan: 05
subsystem: app
tags: [ui, onboarding, pilot-feedback, body-profile, home-banner]
requires:
  - "app/src/lib/bodyProfile.ts (useBodyProfile / merge-write 선례)"
  - "app/src/components/BodyProfileForm.tsx (통증부위 chip 렌더)"
provides:
  - "savePainAreaNote 앱-로컬 merge-write helper + useBodyProfile.painAreaNote"
  - "BodyProfileForm 기타 chip + 자유입력 (initialPainAreaNote prefill + dirty-guard)"
  - "홈 NEW 공지 배너 간격/카피 정리"
affects:
  - "app/src/app/(tabs)/profile.tsx (마이페이지 요약·prefill)"
  - "app/src/app/(tabs)/index.tsx (홈 상단 배너)"
tech-stack:
  added: []
  patterns:
    - "앱-로컬 필드 (promptDismissedAt 선례) — 계약 밖 raw 별도 read/merge-write"
    - "dirty-guard 저장 (prefill 없는 호출부에서 덮어쓰기 방지)"
key-files:
  created: []
  modified:
    - "app/src/lib/bodyProfile.ts"
    - "app/src/components/BodyProfileForm.tsx"
    - "app/src/app/(tabs)/profile.tsx"
    - "app/src/app/(tabs)/index.tsx"
decisions:
  - "기타 통증 메모는 앱-로컬 painAreaNote (promptDismissedAt 선례) — BodyProfile 계약/normalize/PainArea enum 무접촉으로 3-way lockstep·백엔드 소비 경로 무변경"
  - "F4 간격은 TOP_AREA_HEIGHT 240→260 으로 확보 (배너 하단 -16 카드 겹침 해소), 배너 marginTop 16 은 유지"
metrics:
  tasks: 2
  files_modified: 4
  completed: 2026-07-07
---

# Phase 26 Plan 05: F3 통증부위 기타 자유입력 + F4 홈 공지 배너 정리 Summary

파일럿 피드백 F3/F4 잡 UI. 통증부위 입력에 닫힌 8개 enum 밖의 `기타` chip + 자유입력을 앱-로컬 `painAreaNote` 필드(promptDismissedAt 선례)로 추가하고, 홈 NEW 공지 배너의 카드 밀착 간격과 장황한 카피를 정리했다. BodyProfile 계약·백엔드 소비 경로는 무접촉 (JS-only, OTA 가능).

## What Was Built

### Task 1 — F3 통증부위 '기타' + 자유입력 (앱-로컬 painAreaNote)
- `bodyProfile.ts`:
  - `savePainAreaNote(note: string | null)` merge-write helper 추가 (`dismissBodyProfilePrompt` 패턴 그대로 — bodyProfile map 안 painAreaNote 만 갱신, WR-01: 비움은 null 명시).
  - `useBodyProfile` 반환에 `painAreaNote: string | null` 추가 — promptDismissedAt 처럼 raw 에서 별도 read (`typeof === 'string' && trim !== ''` 일 때만 값). `normalizeBodyProfile` 은 무변경 (계약 필드 아님 → 분석 snapshot 자동 배제).
- `BodyProfileForm.tsx`:
  - Props `initialPainAreaNote?: string | null` (옵셔널 — analyze 등 prefill 없는 호출부 무변경).
  - 통증부위 chip 그룹 마지막에 `기타` chip (로컬 `etcSelected` boolean, enum 배열 미포함) + 선택 시 자유입력 TextInput (placeholder `직접 입력해 주세요` / `colors.textDisabled`, 포커스 시 `colors.brand` 보더, `layout.inputHeight` 단일행).
  - 저장 시 dirty-guard: `noteStr.trim()`(기타 해제 시 '' 취급) 이 `initialPainAreaNote` 와 다를 때만 `savePainAreaNote` 호출 — 같은 try/catch/finally 흐름에 합류.
- `profile.tsx`: `painAreaNote` 를 받아 BodyProfileForm prefill + `summarizeBodyProfile` 에 넘겨 요약 라인에 `기타: <메모>` 추가 (계약 필드 전부 비어도 메모만 있으면 노출).

### Task 2 — F4 홈 공지 배너 간격 + 카피
- `TOP_AREA_HEIGHT` 240→260 (+20): NEW 배너 하단이 `cardArea` 의 `marginTop -16` 겹침으로 카드 상단과 밀착돼 있던 것을 해소, 배너 하단과 카드 상단 간격 12 이상 확보. 배너 위쪽 간격(`marginTop 16`)은 유지.
- 카피 `{name} 기준모션이 추가되었어요.` → `{name} 기준모션 추가` (numberOfLines=1 내 긴 모션명 잘림 최소화).
- 배너 비주얼(brand pill, NEW 배지, rgba 배경, numberOfLines=1) 불변.

## Verification

- `npm --prefix app run typecheck` GREEN (both tasks).
- `app/src/types/analysis.ts`, `backend/`, `docs/contract.md` diff 0 — 계약·채점 무접촉 (`painAreaNote` 계약 미등장 확인).
- `normalizeBodyProfile` 함수 본문 diff 0 — raw 별도 read 는 useBodyProfile 쪽만.
- `app/src/app/(tabs)/analyze.tsx` diff 0 — BodyProfileForm 호출부 무변경 (initialPainAreaNote 옵셔널).
- 배너 원문 카피 `기준모션이 추가되었어요` 제거 확인, `newsBanner` 렌더 구조 불변.

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface

계약/백엔드 무접촉. painAreaNote 는 기존 bodyProfile map(동일 rules·동일 민감도) 안의 앱-로컬 표시 전용 필드로, 백엔드/채점/LLM 프롬프트에 미소비 (normalizeBodyProfile 밖). dirty-guard 로 prefill 없는 호출부의 메모 소실 방지 (T-26-12/13/14 register 그대로, 신규 surface 없음).

## Self-Check: PASSED

- All 4 modified files present + SUMMARY.md created.
- Both task commits present: 9244f14 (Task 1 F3), 6ce7e5f (Task 2 F4).
