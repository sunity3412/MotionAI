---
phase: 26-onboarding-upload-guide
plan: 03
subsystem: ui
tags: [react-native, expo-router, firestore, privacy-consent, opt-in, data-contract, learning-optin]

# Dependency graph
requires:
  - phase: 22-custom-vlm-finetune
    provides: "22-04 학습 JSONL manifest 게이트 (learningOptIn 동의값의 예정 소비처)"
provides:
  - "AnalysisDoc.learningOptIn 계약 필드 (3-way lockstep: analysis.ts + models.py + contract.md)"
  - "업로드 직전 프라이버시 1줄 고지 + 학습활용 opt-in 체크 (D-08/D-09)"
  - "촬영 거리 안내(약 2~3m) — not_pole 오반려 예방 레이어 (D-01-i)"
  - "buildOptInRouteParams 순수 헬퍼 — 라우트 param 조립 단일점"
  - "learningOptIn boolean Firestore 기록 (loading.tsx, 항상 boolean)"
affects: [22-custom-vlm-finetune, phase-22-manifest-gate, learning-flywheel-consent]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "라우트 param 조립 순수 헬퍼(named export, React/expo import 무관) — 테스트 가능 단일점"
    - "계약 필드 항상-boolean 기록 (조건부 spread 아님) — 동의 증거 명시적 잔존, param 유실 시 false fail-safe"

key-files:
  created:
    - .planning/phases/26-onboarding-upload-guide/26-03-SUMMARY.md
  modified:
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - app/src/app/analysis/loading.tsx
    - app/src/app/(tabs)/analyze.tsx
    - app/src/app/analysis/reference.tsx

key-decisions:
  - "learningOptIn 을 라우트 param + 계약 필드 단일 네이밍으로 통일 (리뷰 LOW-1, 구 명칭 trainingOptIn 미사용)"
  - "loading.tsx 는 learningOptIn 을 항상 boolean 으로 기록 (부재≠false 제거) — === '1' 엄격 비교로 미동의 방향 fail-safe"
  - "models.py 는 주석-only 계약 미러 (검증 함수/normalizer 없음) — 백엔드 로직 무접촉, not_pole 게이트 불변 (D-01)"
  - "param 조립을 buildOptInRouteParams 순수 헬퍼 단일점으로 (리뷰 MEDIUM-2), 기존 lowQuality 방출도 이 헬퍼로 이동"

patterns-established:
  - "학습활용 동의: 기본 off, 세션 간 비영속 (매 업로드 명시적 체크)"
  - "3-way lockstep 계약 확장: 필드 추가만 허용 시 models.py 는 주석 미러로 로직 무접촉"

requirements-completed: [ONBD-02, ONBD-03]

# Metrics
duration: 20min
completed: 2026-07-07
---

# Phase 26 Plan 03: 프라이버시 고지 + 학습 opt-in + 촬영 거리 안내 Summary

**업로드 직전 프라이버시 1줄 고지 + 학습활용 opt-in 체크(기본 off) + 촬영 거리 안내를 analyze.tsx 에 삽입하고, 동의값을 AnalysisDoc.learningOptIn boolean 계약 필드(3-way lockstep)로 항상 기록 — 백엔드 로직 무접촉.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-07T23:03:55+09:00 (base)
- **Completed:** 2026-07-07T23:23:18+09:00
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- learningOptIn 계약 필드 3-way lockstep 확장 (analysis.ts 필드 + models.py 주석 미러 + contract.md §3 행) — 필드 추가만, 백엔드 채점/게이트 무접촉 (D-01)
- loading.tsx 가 업로드 시점 동의값을 항상 boolean 으로 Firestore 분석 문서에 기록 (Phase 22 학습 플라이휠 동의 근거)
- analyze.tsx 소스 선택 단계에 프라이버시 1줄 고지(D-08) + 학습활용 opt-in 체크 행(D-08/D-09, 기본 off·비차단) + 촬영 거리 안내(D-01-i/A1 예방) 삽입
- buildOptInRouteParams 순수 헬퍼로 라우트 param 조립을 단일점화 (리뷰 MEDIUM-2), lowQuality 방출도 흡수
- reference.tsx learningOptIn passthrough — mode1 미선택 경로 동의값 유실 방지
- 샘플 링크 → `/help` '이용 방법 · FAQ' 교체 (F2/D-05, 26-02 라우트 이관)

## Task Commits

Each task was committed atomically:

1. **Task 1: learningOptIn 계약 필드 3-way lockstep + loading.tsx Firestore 기록** - `25533ad` (feat)
2. **Task 2: analyze.tsx 프라이버시 1줄 + opt-in 체크 + 촬영 거리 안내 + param 순수 헬퍼** - `1402ead` (feat)

_Plan metadata (SUMMARY): committed separately in worktree mode._

## Files Created/Modified

- `app/src/types/analysis.ts` - AnalysisDoc.learningOptIn?: boolean 계약 필드 추가 (의무형 Phase 22 소비 주석)
- `backend/shared/python/sunity_shared/models.py` - learningOptIn 주석-only 계약 미러 (로직 무접촉, ast 파싱 통과)
- `docs/contract.md` - §3 AnalysisDoc learningOptIn 행 + 3-way lockstep 노트 + param 단일 네이밍 부기
- `app/src/app/analysis/loading.tsx` - param learningOptIn?, UploadInput 스레드(`=== '1'` 엄격 비교), setDoc 항상 boolean 기록
- `app/src/app/(tabs)/analyze.tsx` - 프라이버시 1줄 + 촬영 거리 안내 + opt-in 체크 행(a11y checkbox) + buildOptInRouteParams 헬퍼 + /help 링크
- `app/src/app/analysis/reference.tsx` - learningOptIn passthrough (mode1 경로 유실 방지)

## Decisions Made

- **단일 네이밍 learningOptIn (LOW-1):** 라우트 param 과 계약 필드를 동일 명칭으로 — 구 명칭 trainingOptIn 은 어디에도 존재하지 않음 (grep 0 검증).
- **항상-boolean 기록:** loading.tsx setDoc 이 조건부 spread 대신 `learningOptIn: input.learningOptIn` 로 항상 기록. `=== '1'` 엄격 비교로 param 유실/오염 시 false(미동의)로 안전 강하 — fail-safe = 미동의.
- **models.py 주석 미러:** 검증 함수/normalizer 없이 주석만. `git diff` 가 주석 추가만(비-주석 코드 diff 0), python3 ast 파싱 통과 — 로직 무접촉 증명.
- **param 조립 순수 헬퍼(MEDIUM-2):** buildOptInRouteParams 가 true 인 키만 '1' 로 포함, mode1/mode3 양쪽 push 가 경유. lowQuality 선례 동작('1'|미포함) 문자 그대로 불변.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **워크트리 node_modules 부재:** 워크트리에 `app/node_modules` 가 없어 `tsc` 실행 불가. 메인 체크아웃의 동일 의존성(package.json 무변경)을 임시 심볼릭 링크해 `npm run typecheck` GREEN 확인 후 링크 제거 — 커밋에 포함되지 않음(node_modules gitignored, 개별 파일만 스테이징). 두 태스크 모두 typecheck 0 errors.

## Follow-up Items (Phase 22 후속 반영 필요 — SUMMARY 플래그)

> **22-04 manifest 게이트에 `learningOptIn === true` 필터 추가 필요.** 현 22-04 게이트는 anonymized/등록 여부만 필터하고 learningOptIn 을 아직 읽지 않는다. 이 필터가 반영되기 전까지 D-09(동의한 영상만 학습 후보)는 **계약상 의무일 뿐 미집행** 상태다. 계약 3면(analysis.ts / models.py / contract.md)은 이 소비를 의무형("삼아야 한다"/"후속 반영 필요")으로 기술했으며 현재형 단정("조회한다"/"필터한다")은 0. 다음 Phase 22 작업 또는 gap closure 가 이 필터를 픽업해야 한다.

## Threat Model Coverage

- **T-26-05 (Tampering, learningOptIn 무결성):** mitigate 달성 — 기본 off + `=== '1'` 엄격 비교 + 항상-boolean 기록 + param 조립 순수 헬퍼 단일점.
- **T-26-06 (Repudiation, 동의 증거):** 부분 mitigate — 분석 문서 boolean 명시 기록 완료. Phase 22 게이트 true-필터는 후속 반영 항목(위 플래그). 실기기 Firestore 증거 기록은 26-06.
- **T-26-08 (Info Disclosure, 고지 미노출):** mitigate — 고지를 pick 직전 소스 선택 단계에 고정 배치. 실기기 노출 확인은 26-06 checkpoint.
- **T-26-SC (패키지 설치):** 해당 없음 — 패키지 설치 0.

## Deferred Verification (this plan's scope fence)

- 앱 정적 게이트는 typecheck 뿐 (JS 테스트 러너 미구성). opt-in 흐름·고지 노출의 행위 증거는 26-06 실기기 기록이 담당. buildOptInRouteParams 는 순수 함수로 추출돼 추후 테스트 하니스 도입 시 단위테스트 대상.

## Next Phase Readiness

- learningOptIn 동의값이 분석 문서에 기록되므로 Phase 22 학습 manifest 게이트가 소비할 계약 기반은 준비됨 (게이트측 필터는 위 후속 항목).
- 앱 런타임 변경은 OTA-safe (OTA 배포 가능). backend 는 models.py 주석-only 계약 미러라 Lambda 재배포 불필요 (리뷰 LOW-2).
- `/help` 링크는 26-02 가 신설하는 라우트에 의존 (동일 wave). 링크 타깃은 문자열 라우트(typedRoutes 미사용)라 typecheck 무관.

---
*Phase: 26-onboarding-upload-guide*
*Completed: 2026-07-07*
