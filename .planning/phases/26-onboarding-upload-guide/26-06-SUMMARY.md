---
phase: 26-onboarding-upload-guide
plan: 06
subsystem: ui
tags: [react-native, expo-router, ui-rearrange, opt-out-consent, human-uat, tutorial-images, checkpoint]

# Dependency graph
requires:
  - phase: 26-onboarding-upload-guide
    provides: "26-01~05 wave 1-2 산출 (튜토리얼/FAQ/opt-in/카톡 경고/F3/F4) — 재배치·확인 대상"
provides:
  - "belle 확정 재배치안 Ⓐ 구현 (소스 선택 ScrollView + 촬영 안내 통합 캡션)"
  - "학습활용 동의 opt-out 전환 (기본 체크 ON, 해제 시 learningOptIn=false — belle 제품 결정)"
  - "카톡 경고 [다른 영상 선택] → 앨범 재오픈, 기타 빈 입력 확인 다이얼로그, 튜토리얼 이미지 3장"
  - "26-HUMAN-UAT.md — 잔여 실기기 확인 + Firestore 증거 체크리스트 (배치 UAT 정책)"
affects: [22-custom-vlm-finetune (learningOptIn 소비), phase-26-batch-uat, pilot-upload-flow]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "동의 UI opt-out: UI 초기값만 반전, 기록 경로(param → === '1' → boolean)와 fail-safe(유실=미동의)는 불변"
    - "Modal 닫힘 후 후속 present/focus 는 fade-out 지연(450ms) 뒤 실행 — iOS VC presentation 충돌 회피"
    - "확인 다이얼로그 양갈래는 performSave(인자) 로 stale state 우회 — setState 반영 대기 없이 즉시 분기 실행"

key-files:
  created:
    - .planning/phases/26-onboarding-upload-guide/26-06-REARRANGE-MOCKUPS.md
    - .planning/phases/26-onboarding-upload-guide/26-HUMAN-UAT.md
    - app/assets/tutorial/slide-1.jpg
    - app/assets/tutorial/slide-2.jpg
    - app/assets/tutorial/slide-3.jpg
  modified:
    - app/src/app/(tabs)/analyze.tsx
    - app/src/app/tutorial.tsx
    - app/src/components/BodyProfileForm.tsx
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md

key-decisions:
  - "재배치 = Ⓐ 확정 (belle): 소스 선택 화면만 — guidance 2캡션 통합 + ScrollView, 프라이버시/동의 pick 직전 위치 고정. Ⓑ 홈 재진입 링크는 미구현"
  - "학습활용 동의 opt-out 전환 (belle 제품 결정 2026-07-08): 기본 체크 ON, 해제하면 노학습"
  - "D-04 Figma 정합 = belle 확인 완료: Figma 시안이 아이콘 플레이스홀더 상태라 현 구현 수용, 이후 승인 생성 이미지 3장으로 채움"
  - "잔여 재확인·Firestore 증거 = 배치 UAT 정책으로 26-HUMAN-UAT.md 이월 (phase 22·26~31 완료 후 직원 합동 세션)"

patterns-established:
  - "재배치는 목업 선제시(최악 데이터 케이스 포함) → belle 확정 → 승인 범위 내 구현 — 자율 확정 0"

requirements-completed: [ONBD-01]

# Metrics
duration: ~55min (checkpoint 대기 제외, 3라운드)
completed: 2026-07-08
---

# Phase 26 Plan 06: 화면 순서 재배치 + phase 산출 belle 확인 Summary

**재배치안 3종을 최악 데이터 케이스 목업으로 선제시해 belle 이 Ⓐ(소스 선택 ScrollView + 촬영 안내 통합)를 확정·구현했고, belle 1차 실기기 확인에서 나온 수정 지시 3건(opt-out 전환·앨범 재오픈·기타 빈 입력 확인)+튜토리얼 이미지 3장을 phase 내 즉시 반영 — 잔여 재확인과 Firestore 동의 증거는 belle 배치 UAT 정책에 따라 26-HUMAN-UAT.md 로 이월.**

## Performance

- **Duration:** ~55 min 작업 (checkpoint 2회 대기 제외, 2026-07-07 밤 ~ 07-08)
- **Tasks:** 3 (Task 1 decision checkpoint / Task 2 구현 / Task 3 human-verify — 1차 확인 + 수정 반영 + 배치 UAT 이월로 완료 처리)
- **Files:** 5 created + 6 modified, 커밋 7개

## Task Commits

1. **Task 1 준비: 재배치안 목업 선제시 (현행/A/B + 최악 케이스)** - `6020641` (docs)
2. **Task 2: 재배치안 Ⓐ 구현 (ScrollView + 촬영 안내 통합 캡션)** - `54a6513` (feat)
3. **Task 3 수정 1: 학습활용 동의 opt-out 전환 + 3-way lockstep** - `a64c769` (fix)
4. **Task 3 수정 2: 카톡 경고 [다른 영상 선택] → 앨범 재오픈** - `a607924` (fix)
5. **Task 3 수정 3: 기타 빈 입력 확인 다이얼로그** - `fa8eea3` (fix)
6. **Task 3 추가: 튜토리얼 슬라이드 이미지 3장 (belle 승인 생성분)** - `79dca59` (feat)
7. **메타데이터 (SUMMARY + HUMAN-UAT + STATE/ROADMAP)** - 본 커밋

push + OTA(production/preview) 발행 완료 시점 = `79dca59` (2026-07-08, 오케스트레이터 수행).

## Task 1 — 재배치 결정 경위 (belle 확정, 자율 확정 0)

- **목업 선제시:** `26-06-REARRANGE-MOCKUPS.md` — 현행 구조 감사(소스 선택 화면 = 비-스크롤 View + 카드 아래 4블록 밀집) + **최악 데이터 케이스**(긴 모션명 modeContext + error + 권한 안내 동시 노출 → 소형 기기 하단 잘림 위험) ASCII 와이어프레임 + 3안(⓪ 현행 유지 / Ⓐ 안내 밀도 분산 / Ⓑ A+홈 상시 재진입) SCENARIO 0→0.5→1→1.5 정합 근거 표기.
- **belle 확정 = Ⓐ.** analyze.tsx 단계 2만: guidance 2캡션(원본 화질/카톡 + 촬영 거리 2~3m) 1블록 통합(카피 원문 병합, 신규 주장 0) + 본문 ScrollView 래핑 + 프라이버시/동의 행 pick 직전 위치 고정.
- **Ⓑ 거부분 미구현:** belle 이 부속 질문(홈 재진입 형태)에서 '링크(권장)'를 골랐으나 "권장 표시를 따라 골랐을 뿐"이라 확인 — 재배치안 자체는 Ⓐ 선택이므로 홈(index.tsx) 무접촉. 홈 재진입 링크는 향후 잡 UI 후보로만 기록.
- 결과적으로 files_modified 후보 4파일 중 **analyze.tsx 만** 수정 (index.tsx/_layout.tsx/help.tsx 무접촉 — 승인 범위 준수, T-26-16).

## Task 3 — belle 1차 실기기 확인 transcript 요지 (2026-07-08)

**승인(PASS):** 튜토리얼 노출/라우팅(D-03), FAQ 6항목+재진입(F2/D-05), 재배치 Ⓐ 레이아웃, 카톡 감지/다이얼로그 표시/[이대로 계속] 진행(D-06), not_pole 분기 문구(D-07/D-01-ii), 업로드 플로우, F3 기타 chip, F4 배너 간격. belle: "나머진 괜찮을 것 같고".

**D-04 (Figma 정합) — belle 직접 확인, 수정 불필요:** "이 화면이긴 한데 피그마는 지금은 그냥 아이콘 형태" — Figma 튜토리얼 시안의 이미지 영역이 아이콘 플레이스홀더 상태라 현 구현 수용, **D-04 확인 완료** 처리. 이후 belle 승인 생성 이미지 3장으로 이미지 카드를 채움(`79dca59`).

**수정 지시 3건 → phase 내 즉시 반영 (이월 0):**

1. **[belle 제품 결정] 학습활용 동의 opt-out 전환** ("동의에 클릭하지말고 해제버전으로. 자동 동의 → 해제하면 노학습") — `learningOptIn` UI 초기값 true, 해제 시 false 기록. 기록 경로(buildOptInRouteParams → loading.tsx `=== '1'` → Firestore boolean) 바이트 불변, param 유실 fail-safe = 미동의 유지. 3-way lockstep 주석 동기화(analysis.ts + models.py 주석-only/AST OK + contract.md §3). — `a64c769`
2. **카톡 경고 [다른 영상 선택] → 앨범 재오픈** ("앨범 다시 켜져야 해") — cancelTalkv 가 영상 버림 후 Modal fade-out 지연(450ms) 뒤 pickFromLibrary 재호출. D-06/D-07 게이트 체인 불변. — `a607924`
3. **기타 빈 입력 확인** ("기타 선택하고 아무것도 입력 안 하면 물어봐야") — 저장 시도 시 확인 다이얼로그: [없어요, 저장하기]=기타 해제 후 즉시 저장(performSave(false)), [적을게요]/back=닫고 입력창 포커스. 부분 입력 graceful(D-06) 유지. — `fa8eea3`

## 잔여 확인 + 증거 이월 (belle 배치 UAT 정책, 2026-07-08)

**belle 결정:** phase 22, 26~31 개발 완료 후 직원 합동 실기기 세션에서 일괄 수행. 잔여 항목 = `26-HUMAN-UAT.md` (status: partial): (a) opt-out 기본 ON+해제, (b) 앨범 재오픈, (c) 기타 확인 양갈래, (d) 튜토리얼 이미지, **(e)(f) Firestore `learningOptIn` false/true 증거 2건** — (e)(f) 조회는 Claude 가 firebase-admin 으로 대행하고 analysisId+값 원문을 기록한다.

**리뷰 MEDIUM-2 폴백 현황 적시:** 앱에 JS 테스트 하니스가 없어 opt-in/talkv 우선순위의 행위 증거는 기록이 담당한다. **현 시점 증거** = (1) belle 1차 확인 transcript(위 — talkv 감지·진행·not_pole 화질/구도 분기 실기기 PASS 포함) + (2) 커밋 게이트 기록(typecheck GREEN, `_talkv_`/`learningOptIn`/`hasSeenTutorial` grep, loading.tsx `=== '1'` 엄격 비교·항상-boolean 기록 코드 경로 26-03 박제). **Firestore 실증(analysisId+값)은 배치 UAT 에서 확보** — 26-HUMAN-UAT (e)(f)가 그 슬롯이다. opt-out 전환으로 증거 방향은 "해제→false / 기본 유지→true"로 갱신됨.

## Deviations from Plan

**1. [Task 3 resume-signal 경로] belle 수정 지시 3건 + 이미지 추가 1건 반영** — 플랜의 "발견 이슈는 이 phase 내 즉시 수정" 규칙 그대로. files_modified 목록 밖 파일(BodyProfileForm.tsx, tutorial.tsx, assets, 계약 3면)은 belle 지시가 곧 범위 승인. 전부 위 커밋에 기록.

**2. [배치 UAT 이월] Task 3 의 "8항목 approved + Firestore 증거 SUMMARY 기재"를 1차 확인 + 26-HUMAN-UAT.md 이월로 대체** — belle 프로세스 결정(2026-07-08). must_haves 의 Firestore 증거 항목은 HUMAN-UAT (e)(f)로 추적 지속 (phase 22·26~31 완료 후 수행). 06-HUMAN-UAT 선례와 동일 패턴.

## Verification (phase 마감 게이트)

- `npm --prefix app run typecheck` GREEN (전 커밋 시점 + 최종 상태)
- backend 비주석 diff 0 (models.py = 주석-only 계약 미러, python AST 파싱 OK) — D-01 게이트/채점 불변
- 라우트 이관 최종 봉인 (26-02/리뷰 MEDIUM-1): `grep -rn "analysis/samples" app/src docs` = **0**, `simulationWriter|simulatedResult` = **0**
- 26-01~05 must_haves 재확인: `_talkv_`(2)/`learningOptIn`(12)/`hasSeenTutorial`(존재) grep PASS, 게이트 체인·동의 기록·첫 실행 플래그 로직 diff 0 (위치/구성만 이동)
- 수정 파일 = belle 승인 범위 일치 (git status 대조), 신규 인라인 hex 0, 신규 의존성 0 (JS-only, OTA 발행 완료)

## Threat Model Coverage

- **T-26-15 (재배치 중 동의/게이트 로직 회귀):** mitigate — grep 재확인 3종 PASS + 재배치는 레이아웃/캡션만(로직 diff 0) + opt-out 전환도 초기값 1줄 반전(기록 경로 불변). Firestore 양방향 실증은 HUMAN-UAT (e)(f) 슬롯.
- **T-26-16 (승인 범위 밖 변경):** mitigate — Task 2 는 analyze.tsx 만(Ⓐ 범위), Task 3 추가 파일은 belle 지시 = 범위 승인. git status 대조 완료.
- **T-26-SC (패키지 설치):** 해당 없음 — 설치 0.

## Known Stubs

없음. 26-HUMAN-UAT.md 의 pending 항목은 스텁이 아니라 확인 이월 (구현은 완료, 실기기 재확인·증거 수집만 배치 세션 대기).

## Next Phase Readiness

- Phase 26 코드 산출 완료, OTA 라이브 (79dca59). 배치 UAT 전 추가 개발 불필요.
- Phase 22 연동: learningOptIn 이 opt-out 기본 true 로 바뀌어 학습 후보 풀이 커짐 — 22-04 manifest 게이트의 `learningOptIn === true` 필터는 여전히 후속 반영 필요 (26-03 SUMMARY 플래그 유지).
- 배치 UAT 세션 진입점: `26-HUMAN-UAT.md` (a)~(f). (e)(f) Firestore 조회는 Claude 대행.

## Self-Check: PASSED

- FOUND: .planning/phases/26-onboarding-upload-guide/26-06-REARRANGE-MOCKUPS.md
- FOUND: .planning/phases/26-onboarding-upload-guide/26-HUMAN-UAT.md
- FOUND: app/assets/tutorial/slide-{1,2,3}.jpg, 수정 6파일 전부 존재
- FOUND commits: 6020641 / 54a6513 / a64c769 / a607924 / fa8eea3 / 79dca59
- typecheck EXIT 0, route-seal grep 0, backend 비주석 diff 0

---
*Phase: 26-onboarding-upload-guide*
*Completed: 2026-07-08*
