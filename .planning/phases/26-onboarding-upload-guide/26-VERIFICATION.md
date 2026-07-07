---
phase: 26-onboarding-upload-guide
verified: 2026-07-07T15:34:35Z
status: human_needed
score: 28/29 must-haves verified (1 human-pending)
overrides_applied: 1
overrides:
  - must_have: "학습활용 opt-in 체크가 별도로 존재하고 기본값 off 이며, 미체크로 업로드가 지연/차단되지 않는다 (D-08/D-09)"
    reason: "belle 제품 결정 (2026-07-08, 26-06 1차 실기기 확인 중 지시): opt-out 전환 — 기본 체크 ON(자동 동의), 해제 시 learningOptIn=false. 기록 경로(buildOptInRouteParams → loading.tsx === '1' 엄격 비교 → 항상-boolean setDoc)와 fail-safe(param 유실=미동의)는 바이트 불변. 3-way lockstep(analysis.ts/models.py/contract.md) 주석 동기화 완료 (커밋 a64c769)"
    accepted_by: "belle"
    accepted_at: "2026-07-08T00:00:00+09:00"
human_verification:
  - test: "학습활용 동의 opt-out — 소스 선택 화면에서 기본 체크 ON 노출 + 탭 해제 + 해제 상태로도 업로드 진행"
    expected: "기본 ON, 해제 가능, 업로드 비차단"
    why_human: "UI 초기 상태·인터랙션은 grep 불가. 26-HUMAN-UAT.md (a) — belle 승인 배치 UAT 이월 (phase 22·26~31 완료 후 합동 세션)"
  - test: "카톡 경고 [다른 영상 선택] 탭 → 앨범 picker 자동 재오픈 (영상 버림)"
    expected: "다이얼로그 닫힘 후 450ms 지연 뒤 앨범 재오픈"
    why_human: "Modal fade-out 후 picker present 는 iOS 런타임 동작. 26-HUMAN-UAT.md (b)"
  - test: "통증부위 기타 빈 입력 저장 시 확인 다이얼로그 양갈래 ([없어요, 저장하기]=해제 후 저장 / [적을게요]=입력창 포커스)"
    expected: "양갈래 각각 정상 동작"
    why_human: "다이얼로그 분기·키보드 포커스는 실기기 확인 필요. 26-HUMAN-UAT.md (c)"
  - test: "튜토리얼 3슬라이드에 브랜드 레드 톤 이미지 3장 표시 (아이콘 플레이스홀더 아님)"
    expected: "slide-1~3.jpg 가 라운드 카드로 렌더, 스와이프/건너뛰기/시작하기 불변"
    why_human: "비주얼 정합은 육안 확인. 26-HUMAN-UAT.md (d)"
  - test: "opt-out 해제 업로드 → Firestore 분석 문서 learningOptIn: false (Claude firebase-admin 조회 대행, analysisId+값 원문 기록)"
    expected: "learningOptIn: false"
    why_human: "실 업로드→Firestore 기록의 런타임 증거. 26-HUMAN-UAT.md (e) — 리뷰 MEDIUM-2 증거 슬롯"
  - test: "기본 ON 유지 업로드 → Firestore 분석 문서 learningOptIn: true (조회 대행 동일)"
    expected: "learningOptIn: true"
    why_human: "동상. 26-HUMAN-UAT.md (f)"
---

# Phase 26: 온보딩·기대설정 + 원본 업로드 가이드 Verification Report

**Phase Goal:** 분석 이전 구간(시나리오 0/0.5/1/1.5)의 파일럿 gap 해소 — (a) 기대설정 온보딩(Figma 튜토리얼 + 여정 편입 + 샘플→FAQ 교체), (b) 프라이버시 1줄 + 학습 활용 고지, (c) 원본 업로드 가이드(카톡 `_talkv_` 감지·경고 + 촬영 거리 안내), (d) 잡 UI F3/F4. UI 화면 순서 재배치 제안 포함. 앱만.
**Verified:** 2026-07-07T15:34:35Z (KST 2026-07-08)
**Status:** human_needed
**Re-verification:** No — initial verification

## Must-Haves Source

ROADMAP.md 에 별도 success_criteria 배열 없음 → 6개 PLAN frontmatter must_haves(truths 29건)를 병합해 계약으로 사용. ROADMAP goal 의 (a)~(d) 4개 축은 전부 PLAN truths 로 커버됨 (누락 0).

## Goal Achievement

### Observable Truths

| #   | Truth (plan)                                                             | Status             | Evidence |
| --- | ------------------------------------------------------------------------ | ------------------ | -------- |
| 1   | 첫 실행 게스트는 홈 진입 전 튜토리얼 1회 (D-03) [26-01]                  | ✓ VERIFIED         | `index.tsx:26-27` `hasSeenTutorial().then(seen => router.replace(seen ? '/(tabs)' : '/tutorial'))` |
| 2   | 스킵/완료 후 재노출 없음 [26-01]                                          | ✓ VERIFIED         | `tutorial.tsx:72-73` finish() 단일 수렴 → markTutorialSeen(); 건너뛰기(:87)/시작하기(:133) 모두 finish 경유 |
| 3   | 튜토리얼 내용 = 기대설정 중심 (D-04) [26-01]                              | ✓ VERIFIED         | `tutorial.tsx:39-56` SLIDES 3장: 무엇을 측정/강사 보조 포지셔닝/원본 촬영 안내. 비주얼 D-04 belle 1차 확인 PASS (HUMAN-UAT 1차 표) |
| 4   | AsyncStorage 오류에도 앱 진입 비차단 [26-01]                              | ✓ VERIFIED         | `onboarding.ts:22` catch → true 반환, `:30` setItem `.catch(() => {})` |
| 5   | 샘플 미리보기 → 이용방법/FAQ 교체 (F2/D-05) [26-02]                       | ✓ VERIFIED         | samples.tsx/simulationWriter.ts/simulatedResult.ts 부재, help.tsx 196줄 존재, analyze.tsx:673 `router.push('/help')` |
| 6   | FAQ 에서 튜토리얼 재진입 (D-03) [26-02]                                   | ✓ VERIFIED         | `help.tsx:96` `router.push('/tutorial')` + "튜토리얼 다시 보기" |
| 7   | FAQ 최소 6항목 (측정/원본/거리/실패/보관·삭제/재보기) [26-02]              | ✓ VERIFIED         | help.tsx FAQ_ITEMS title 6개 grep 확인 — 계획된 6주제 전부 일치 |
| 8   | 시뮬레이션 샘플 코드 잔존 참조 0 (result.tsx dev 폴백 포함) [26-02]        | ✓ VERIFIED         | `grep -rn "analysis/samples\|simulationWriter\|simulatedResult" app/src docs` = 0 매치 |
| 9   | result.tsx wrapper/Content 분리, 훅 순서 회귀 없음 (리뷰 HIGH-1) [26-02]  | ✓ VERIFIED         | result.tsx:544 wrapper(AnalysisResult), :575 `if (!storedDoc?.result)` 안내 렌더, :605-606 non-null 조건에서만 `<AnalysisResultContent result={storedDoc.result}>` 마운트, :618 child 정의. getSimulatedResult 참조 0 |
| 10  | 업로드 직전 프라이버시 1줄 고지 — 동의 버튼 아님 (D-08) [26-03]            | ✓ VERIFIED         | analyze.tsx:479 "영상은 분석에만 사용하고 안전하게 보관해요. 언제든 삭제를 요청할 수 있어요." — pick 직전 소스 선택 화면, Text 고지만 |
| 11  | opt-in 체크 별도 존재 + **기본값 off** + 업로드 비차단 (D-08/D-09) [26-03] | ◑ PASSED (override) | 체크 행 존재(:489 checkbox a11y)·비차단(learningOptIn 이 validate/에러 경로 미등장) VERIFIED. 기본값은 `useState(true)`(:120) — Override: belle 제품 결정 opt-out 전환 (a64c769), accepted by belle on 2026-07-08 |
| 12  | learningOptIn 항상 boolean 기록 → Phase 22 게이트 소비 가능 (D-09) [26-03] | ✓ VERIFIED         | loading.tsx:337 `learningOptIn === '1'` 엄격 비교 → :147 setDoc 무조건 필드 기록 (조건부 spread 아님). Phase 22 게이트측 필터는 후속 항목으로 26-03 SUMMARY 플래그 존재 |
| 13  | mode1 경로(reference.tsx)에서 동의값 유실 없음 [26-03]                     | ✓ VERIFIED         | reference.tsx:36 destructure, :47 타입, :104 loading push pass-through |
| 14  | param↔계약 필드 learningOptIn 단일 네이밍 (리뷰 LOW-1) [26-03]            | ✓ VERIFIED         | `grep -rn "trainingOptIn" app/src docs` = 0. buildOptInRouteParams(:76-81) 단일점 |
| 15  | 촬영 거리 안내(약 2~3m) pick 전 노출 (D-01-i) [26-03]                     | ✓ VERIFIED         | analyze.tsx:472 통합 캡션 (26-06 재배치 Ⓐ — 카피 원문 병합, pick 직전 유지) |
| 16  | not_pole 게이트/임계 무변경 (D-01) [26-03]                                | ✓ VERIFIED         | phase 전체 backend diff = models.py +17줄, 전부 주석 (비주석 diff 0), ast 파싱 OK |
| 17  | _talkv_ pick 시 경고 + 진행 허용 (하드 차단 금지, D-06) [26-04]           | ✓ VERIFIED         | analyze.tsx:91 isKakaoCompressedVideoName 순수 헬퍼(named export), :316-319 감지→보류, :347-350 continueTalkv "이대로 계속" 진행. 실기기 1차 확인 PASS |
| 18  | talkv 승인 영상 not_pole 실패 시 화질 원인 우선 (D-07) [26-04]            | ✓ VERIFIED         | continueTalkv(:350) `{ ...p, lowQuality: true }` → loading.tsx:414 `isLowQualityNotPole = isNotPole && lowQuality === '1'` 우선 분기. 실기기 1차 not_pole 분기 문구 PASS |
| 19  | 카톡 경고·저화질 경고 이중 노출 없음 (직렬 체인) [26-04]                  | ✓ VERIFIED         | analyze.tsx:316-319 talkv 감지 시 `return` — checkLowQuality(:321) 도달 불가 |
| 20  | 플래그 없는 not_pole 에 구도/거리 + 재촬영 안내 (D-01-ii) [26-04]         | ✓ VERIFIED         | loading.tsx:419 isPlainNotPole, :429-430 구도/거리 본문, :481 tipCard 항목 보강. 기존 타이틀 2종(:423, :425) 불변 |
| 21  | not_pole 게이트/D-07 분기 우선순위 로직 불변 [26-04]                      | ✓ VERIFIED         | isLowQualityNotPole 조건식 원형 유지 + backend diff 0 (truth 16 과 동일 증거) |
| 22  | 통증 부위 마지막에 '기타' + 자유입력 (F3) [26-05]                         | ✓ VERIFIED         | BodyProfileForm.tsx:324-336 기타 chip(로컬 etcSelected, enum 배열 밖) + TextInput "직접 입력해 주세요" |
| 23  | 기타 메모 저장·복원 + BodyProfile 계약 무접촉 [26-05]                     | ✓ VERIFIED         | bodyProfile.ts:235 savePainAreaNote merge-write, :118/:170 useBodyProfile painAreaNote 반환, profile.tsx:165 prefill + :57 요약. painAreaNote 는 analysis.ts/contract.md 미등장 (grep 0), dirty-guard(:176-181) 존재 |
| 24  | 홈 공지 배너 간격 >= 12 + 카피 축약 (F4) [26-05]                          | ✓ VERIFIED         | index.tsx:319 TOP_AREA_HEIGHT 240→260 (카드 -16 겹침 해소), :116 "기준모션 추가" (원문 "기준모션이 추가되었어요" 제거) |
| 25  | backend/·docs/contract.md 무접촉 (26-05 스코프) [26-05]                   | ✓ VERIFIED         | 26-05 커밋(9244f14, 6ce7e5f)은 app 4파일만. phase 전체 backend 비주석 diff 0 |
| 26  | 재배치안 목업 선제시(최악 케이스) → belle 확정 후에만 구현 [26-06]         | ✓ VERIFIED         | 26-06-REARRANGE-MOCKUPS.md 존재 (커밋 6020641, 최악 데이터 케이스 포함), belle Ⓐ 확정 후 54a6513 구현 — analyze.tsx만 수정 (승인 범위 일치) |
| 27  | belle 이 phase 26 전체 산출 확인 [26-06]                                  | ✓ VERIFIED         | 26-HUMAN-UAT.md "1차 확인 완료" 표 8항목 PASS (2026-07-08 belle 실기기) + 수정 지시 3건 phase 내 반영 (a64c769/a607924/fa8eea3) |
| 28  | opt-in 기본값·talkv 우선순위 증거(transcript + Firestore 조회) SUMMARY 기록 [26-06] | ⏸ HUMAN    | Transcript = 26-06-SUMMARY §Task 3 기록됨. Firestore 실증(analysisId+값 2건)은 belle 승인 배치 UAT 정책으로 26-HUMAN-UAT.md (e)(f) 이월 — human_verification 항목으로 추적 (영속처 인정: 실행 컨텍스트 belle 결정) |
| 29  | belle 이 거부한 재배치안(Ⓑ 홈 재진입)은 미구현 [26-06]                    | ✓ VERIFIED         | `grep -n "tutorial\|help" app/src/app/(tabs)/index.tsx` = 0 매치 — 홈 재진입 링크 부재 |

**Score:** 28/29 (27 VERIFIED + 1 PASSED (override) + 1 human-pending)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app/src/app/tutorial.tsx` | 스와이프 튜토리얼 (min 80줄) | ✓ VERIFIED | 223줄. pagingEnabled + onMomentumScrollEnd + dot + 건너뛰기 + 시작하기 CTA + finish() 수렴. 인라인 hex 0 |
| `app/src/lib/onboarding.ts` | 첫 실행 플래그 helper (`@sunity:tutorial_seen`) | ✓ VERIFIED | 33줄. hasSeenTutorial/markTutorialSeen, 양방향 catch graceful |
| `app/src/app/help.tsx` | FAQ 화면 (min 100줄) | ✓ VERIFIED | 196줄. FAQ_ITEMS 6항목 아코디언 + 튜토리얼 재진입. 인라인 hex 0 |
| `app/src/types/analysis.ts` | `learningOptIn` 계약 필드 | ✓ VERIFIED | :619 `learningOptIn?: boolean` + 의무형 Phase 22 소비 주석 (현재형 단정 없음) |
| `docs/contract.md` | learningOptIn 계약 미러 | ✓ VERIFIED | §3 :97-112 필드 행 + 3-way lockstep 노트 + param 단일 네이밍 부기 |
| `backend/.../models.py` | learningOptIn 주석-only 미러 | ✓ VERIFIED | :236-252 주석 블록만. ast 파싱 OK, phase 전체 backend diff = 이 17줄 주석뿐 |
| `app/src/app/(tabs)/analyze.tsx` | `_talkv_` 감지 헬퍼 + 경고 다이얼로그 + 게이트 체인 | ✓ VERIFIED | :52 마커, :91 순수 헬퍼, :128 talkvPicked, :316 직렬 체인, :524-556 다이얼로그(onRequestClose=cancelTalkv) |
| `app/src/lib/bodyProfile.ts` | savePainAreaNote + useBodyProfile painAreaNote | ✓ VERIFIED | :235 helper, :118/:170 반환. normalizeBodyProfile 무변경 |
| `app/src/components/BodyProfileForm.tsx` | 기타 chip + 자유입력 | ✓ VERIFIED | :324-336 기타 chip, TextInput + dirty-guard + [26-06 수정 3] 빈 입력 확인 다이얼로그 |
| `.planning/.../26-06-SUMMARY.md` | belle 결정 기록 + transcript + 증거 | ◑ PARTIAL→HUMAN | 재배치 결정·1차 transcript·수정 3건 기록 완비. Firestore 증거는 26-HUMAN-UAT.md (e)(f) 슬롯 (belle 승인 이월) |
| `app/assets/tutorial/slide-{1,2,3}.jpg` | 튜토리얼 이미지 (belle 승인 생성분) | ✓ VERIFIED | 3파일 존재 (79dca59). 실기기 표시 확인은 HUMAN-UAT (d) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| index.tsx | onboarding.ts | hasSeenTutorial 라우팅 분기 | ✓ WIRED | :7 import, :26-27 분기 사용 |
| tutorial.tsx | onboarding.ts | markTutorialSeen (finish) | ✓ WIRED | :14 import, :73 호출, 스킵/CTA 양 경로 finish 경유 |
| help.tsx | /tutorial | 튜토리얼 다시 보기 | ✓ WIRED | :96 router.push('/tutorial') |
| analyze.tsx | loading.tsx | learningOptIn param ('1'\|미포함) | ✓ WIRED | buildOptInRouteParams(:76) → routeAfterPick optInParams(:198), mode1/mode3 양쪽 |
| reference.tsx | loading.tsx | mode1 pass-through | ✓ WIRED | :36/:47/:104 |
| loading.tsx | users/{uid}/analyses/{id} | setDoc learningOptIn boolean | ✓ WIRED | :337 `=== '1'` → :147 setDoc 항상 기록 |
| analyze.tsx | loading.tsx | talkv 승인 → lowQuality:true → 화질 우선 분기 | ✓ WIRED | continueTalkv(:350) 플래그 → loading.tsx:414 isLowQualityNotPole |
| loading.tsx | not_pole 실패 화면 | isPlainNotPole 구도 안내 | ✓ WIRED | :419/:429-430/:481 |
| BodyProfileForm.tsx | bodyProfile.ts | savePainAreaNote (dirty-guard) | ✓ WIRED | :29 import, :181 조건부 호출 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| loading.tsx | learningOptIn (param) | analyze.tsx useState → buildOptInRouteParams → router param → `=== '1'` → setDoc boolean | 코드 경로 완결 (Firestore 런타임 실증은 UAT (e)(f)) | ✓ FLOWING |
| result.tsx | storedDoc.result | useAnalysisDoc(Firestore onSnapshot) — 시뮬 폴백 제거 후 단일 소스 | 실 데이터만, 부재 시 한국어 안내 | ✓ FLOWING |
| profile.tsx | painAreaNote | useBodyProfile raw 별도 read (Firestore) | merge-write ↔ read 대칭 | ✓ FLOWING |
| tutorial.tsx | SLIDES | 모듈 상수 (정적 콘텐츠 — 의도적) | N/A (정적 화면) | ✓ N/A |
| help.tsx | FAQ_ITEMS | 모듈 상수 (정적 콘텐츠 — 의도적) | N/A (정적 화면) | ✓ N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| 앱 정적 게이트 (유일한 정적 게이트 — JS 테스트 하니스 없음) | `npm --prefix app run typecheck` | exit 0 | ✓ PASS |
| models.py 로직 무접촉 | `python3 -c "import ast; ast.parse(...)"` + phase 범위 `git diff -- backend/` | ast OK, +17줄 전부 주석 | ✓ PASS |
| 라우트 이관 최종 봉인 (리뷰 MEDIUM-1) | `grep -rn "analysis/samples\|simulationWriter\|simulatedResult" app/src docs` | 0 매치 | ✓ PASS |
| 구 명칭 잔존 (리뷰 LOW-1) | `grep -rn "trainingOptIn" app/src docs` | 0 매치 | ✓ PASS |
| 커밋 실재 (SUMMARY 17개 해시) | `git cat-file -t <hash>` × 17 | 17/17 OK | ✓ PASS |

런타임 행위 증거(opt-out 토글, 앨범 재오픈, Firestore 기록값)는 26-06 1차 transcript + 26-HUMAN-UAT.md 가 담당 (실행 컨텍스트의 리뷰 MEDIUM-2 폴백 정책).

### Probe Execution

SKIPPED — 앱-only phase. PLAN/SUMMARY 어디에도 probe 선언 없음, `scripts/*/tests/probe-*.sh` 는 마이그레이션/툴링 phase 용으로 본 phase 스코프 밖.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| ONBD-01 | 26-01, 26-02, 26-06 | 기대설정 온보딩 + FAQ + 여정 편입 | ✓ SATISFIED | Truths 1-9, 26-29 |
| ONBD-02 | 26-03 | 프라이버시·학습활용 동의 | ✓ SATISFIED | Truths 10-14 (기본값은 belle opt-out override) |
| ONBD-03 | 26-03, 26-04 | 원본 업로드 가이드 (카톡 감지·거리·not_pole 안내) | ✓ SATISFIED | Truths 15-21 |
| ONBD-04 | 26-05 | 잡 UI F3/F4 | ✓ SATISFIED | Truths 22-25 |

주: ONBD-01~04 는 REQUIREMENTS.md 에 미등재 — ROADMAP.md Phase 26 섹션에서 플래너가 mint 한 phase-goal 파생 ID (ROADMAP 명시 "ROADMAP TBD 를 플래너가 mint"). 고아 요구사항 없음 — 4개 ID 전부 플랜이 클레임하고 전부 검증됨.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (없음) | - | TBD/FIXME/XXX/TODO/HACK/placeholder/console.log/인라인 hex — 수정 13파일 전수 스캔 0건 | - | - |

### Human Verification Required

전부 26-HUMAN-UAT.md (belle 승인 배치 UAT 정책, 2026-07-08 — phase 22·26~31 완료 후 직원 합동 세션)에 영속 기록됨. 별도 신규 항목 없음 — 아래는 그 파일의 (a)~(f) 그대로.

### 1. opt-out 기본 ON + 해제 동작 (a)

**Test:** 소스 선택 화면 진입 → 동의 행 기본 체크 ON 확인 → 탭 해제 → 해제 상태로 업로드
**Expected:** 기본 ON, 해제 가능, 업로드 비차단
**Why human:** UI 초기 상태·인터랙션은 정적 검증 불가

### 2. 카톡 경고 [다른 영상 선택] → 앨범 재오픈 (b)

**Test:** `_talkv_` 영상 pick → 경고 → [다른 영상 선택]
**Expected:** 다이얼로그 닫힘 후 앨범 picker 자동 재오픈
**Why human:** iOS Modal fade-out 후 picker present 타이밍은 런타임 동작

### 3. 기타 빈 입력 확인 다이얼로그 양갈래 (c)

**Test:** 기타 chip 선택 + 빈 입력 저장 → 확인 다이얼로그 양갈래 확인
**Expected:** [없어요]=해제 후 저장, [적을게요]=입력창 포커스
**Why human:** 다이얼로그 분기 + 키보드 포커스는 실기기 확인 필요

### 4. 튜토리얼 이미지 3장 표시 (d)

**Test:** FAQ → 튜토리얼 다시 보기 → 3슬라이드 이미지 확인
**Expected:** 브랜드 레드 톤 이미지 라운드 카드 (플레이스홀더 아님)
**Why human:** 비주얼 정합은 육안 확인

### 5-6. Firestore learningOptIn 양방향 증거 (e)(f)

**Test:** 해제 업로드 → `learningOptIn: false` / 기본 유지 업로드 → `true` (Claude firebase-admin 조회 대행, analysisId+값 원문 기록)
**Expected:** 각각 false/true
**Why human:** 실 업로드→Firestore 런타임 기록 증거 (리뷰 MEDIUM-2 슬롯)

### Gaps Summary

가로막는 gap 없음. 29개 truth 중 27개 코드 증거로 VERIFIED, 1개는 belle 제품 결정(opt-out) override 로 PASS, 1개(Firestore 증거 기록)는 belle 승인 배치 UAT 이월로 human-pending. 특기 사항:

1. **opt-out 전환은 계획 대비 의도적 이탈** — 26-03 플랜의 "기본값 off" 는 belle 1차 실기기 확인(2026-07-08) 중 제품 결정으로 반전됨 (a64c769). 기록 경로·fail-safe·3-way lockstep 전부 동기화 확인 (models.py 주석에 opt-out 결정 명기). Override 로 처리.
2. **Phase 22 후속 의무 잔존 (이 phase 의 gap 아님)** — 22-04 manifest 게이트의 `learningOptIn === true` 필터는 미집행. 26-03 SUMMARY 후속 플래그 + 계약 3면 의무형 기술로 추적 중. opt-out 전환으로 학습 후보 풀이 커진 만큼 이 필터의 우선순위가 올라감 — Phase 22 작업 시 필수 픽업 항목.
3. **행위 증거 체계** — 앱에 JS 테스트 하니스가 없어 정적 게이트는 typecheck 뿐. 런타임 행위 증거는 (1) belle 1차 실기기 transcript (8항목 PASS, 26-06-SUMMARY), (2) 배치 UAT (a)~(f) 이월분으로 이원화. 이월은 belle 승인 상태(배치 UAT 정책)이며 26-HUMAN-UAT.md 가 영속처.

---

_Verified: 2026-07-07T15:34:35Z_
_Verifier: Claude (gsd-verifier)_
