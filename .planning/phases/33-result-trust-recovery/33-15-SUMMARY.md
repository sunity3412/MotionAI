---
phase: 33-result-trust-recovery
plan: 15
subsystem: ui
tags: [wave-b, d-16, d-17, number-demotion, safe-area, typography, tidy-up]

# Dependency graph
requires:
  - phase: 33-result-trust-recovery (33-11, A-4)
    provides: "6R 확정 문형(초 표기 라벨 '감점 부분' 계열 + 괄호 보조 = 브랜드 컬러) + 화면 어휘 게이트"
  - phase: 33-result-trust-recovery (33-12, A-5)
    provides: "FaultZoomComparison.criterion scalar (33-12+ 크롭 = 초 베이크 보장 — 초 라벨 게이트 키) + crop 각도 배지 언베이크 (defect #6)"
  - phase: 33-result-trust-recovery (33-13, A-6)
    provides: "초 표기 라벨 문형 이관 기록 (Deferred → 33-15 입력) + 어휘 게이트 pytest 핀"
  - phase: 33-result-trust-recovery (33-14, A-7)
    provides: "DeductionDetailSheet.illustrationSlot 위치 계약 (행동 큐 아래 — 유지 확인)"
provides:
  - "각도 수치 단일 거처 = 점수 계산 내역 (코칭 팁 카드 각도 줄 제거 + '관절 각도 참고' 영역 신설, D-16)"
  - "수치 강등 토큰 typography.metricNumber(17) — 내역 행·종합·심사 코너·근거 박스 공용"
  - "참고하세요 모순 카피 해소 + 무엇을 왜 보는지 안내 1줄"
  - "safe-area 실측 inset 컨테이너 패딩 (본문↔상태바 겹침 수정, D-17)"
  - "자세히 보기 토글(펼침=상세 앵커 스크롤 / 재탭=접기·복귀) + 추가 감점 항목 어포던스"
  - "초 표기 라벨 문형 '(감점 부분)' 브랜드 컬러 괄호 보조 (A-6 이관, criterion 카드 한정)"
affects: [33-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "수치 강등 토큰 — 감점/점수 숫자는 headline 스케일(24↑) 아래 badge 스케일(하한 17) 고정, 인라인 크기 0"
    - "이동 불가 시 삭제 금지 — legacy doc(내역 카드 부재)은 종전 각도 줄 유지 (투명 공개 원칙)"
    - "데이터 키잉 표시 게이트 — 초 라벨은 zoom.criterion 보유(=초 베이크 보장 세대)에서만 렌더"
    - "스크롤 앵커 = onLayout 실측 y 전용 슬롯 키(anchor:*) — record 키 공간과 분리"

key-files:
  created: []
  modified:
    - app/src/app/analysis/result.tsx
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/components/ReferenceCornerSection.tsx
    - app/src/components/ScoreBreakdownSection.tsx
    - app/src/components/SummaryCard.tsx
    - app/src/components/OctagonScore.tsx
    - app/src/theme/typography.ts

key-decisions:
  - "legacy doc(deductionBreakdown 부재)은 코칭 팁 각도 줄 종전 유지 — 내역 카드가 없어 이동하면 수치가 소멸(삭제 금지 원칙)"
  - "초 표기 라벨은 criterion 보유 크롭 한정 — 구 PNG(초 미베이크)에 없는 배지를 지칭하는 거짓 라벨 방지 (데이터 키잉)"
  - "OctagonScore 중앙 수치는 크기 유지 + 토큰화만 — D-09 로 이미 위치 강등된 채점 게이지 본체(홈 탭 공용)라 D-16 대상 아님으로 해석"
  - "'접기' = 상태 라벨 반전 + 최상단 복귀 스크롤 — 섹션 숨김 구조 변경은 tidy-up 범위 밖 (신규 UI 표면 0)"

# Metrics
duration: 20분 (2026-07-29 03:51~04:11 UTC)
completed: 2026-07-29
---

# Phase 33 Plan 15: Wave B 정돈 Summary

**각도 수치가 코칭 카드에서 점수 계산 내역 '관절 각도 참고'로 이사하고(단일 거처, 크롭 언베이크는 33-12 백엔드 소관 확인), 모순 카피·대시 나열·헤드라인급 수치가 정돈됐으며, 유일한 실버그(본문↔상태바 겹침)를 실측 safe-area inset 으로 수정 — 채점 무접촉, Wave A 무접촉**

## Task별 구현

### Task 1 — 수치 이동 + 모순 수정 + 안내 + 강등 (`3b5cf55`, D-16)

- **각도 수치 이동**: 코칭 팁 카드의 `현재 X° → 기준 Y°` 줄(및 추정 변형 + ⓘ) 제거, 행동 언어(`더 펴주세요`)만 잔류. 수치는 `ScoreBreakdownSection` 신설 `angleReference` prop → 점수 계산 내역 카드 하단 **'관절 각도 참고'** 영역으로 이동 (= 종합 행 아래 참고 톤, badge 스케일). 소스 = 종전과 동일한 displayTips 관절의 angleGuide — 모순 카피 필터·IN-01 저신뢰 per-joint 억제가 그대로 승계돼 저신뢰 시 자연히 빈 배열(관절 단정 0). 추정 관절은 `추정` 접두 + estimateGray + 각주 1줄.
- **크롭 PNG 배지 무접촉**: defect #6(각도 숫자 베이크)은 33-12 백엔드 언베이크(`79221f0` 선행 + 회귀 핀)가 소관 — 이 플랜은 fault_zoom/크롭에 손대지 않음 (grep: 백엔드 diff 0). 앱 카드 수치 이동과 합쳐 **수치의 거처는 내역 1곳** (D-16 single-home).
- **모순 카피 해소**: 참고하세요 섹션 서브 "점수에는 반영되지 않아요" ↔ 자세 비교 캡션 "점수에 반영된 비교 순간" 동거 종료 — 캡션을 "분석에서 비교한 순간의 실제 화면이에요"로 (사실 유지, '점수' 표현만 제거).
- **참고하세요 안내 1줄** (D-05): "내 자세와 기준 자세가 어디서 달라지는지 눈으로 견줘보는 용도예요" — cleanPass doc 에도 참인 중립 문형.
- **대시 나열 문장화**: `이 지표 — X` → `이 지표는 X{을/를} 봐요` (마지막 글자 종성 판정 `objectJosa` — "힘"→을/"크기"→를 조사 오표기 방지), `확인하기 — …` → `거울을 보며 동작을 직접 재현해서 확인해 보세요`.
- **수치 강등**: `typography.metricNumber`(17/700, lineHeight 23, track()=0) 신설 → 내역 행 `−17.4`·`−20`(listTitle 18), 종합 `51점`(listTitle 18), 심사 코너 감점·환산 점수(listTitle 18), 시트 근거 박스 감점(bodyMdBold 21) 전부 교체 — headline 스케일(24↑) 아래 badge 스케일(D-05 하한 17) 고정, 하드코딩 크기 0.
- **A-6 이관 — 초 표기 라벨 문형** (6R 확정): 시트 크롭 아래 "사진 속 초는 영상에서 이 순간을 찾는 위치예요 **(감점 부분)**" — 괄호 보조 = 브랜드 컬러 + bold (목업 .pnote 정합). `zoom.criterion` 보유 카드 한정(33-12+ 파이프라인 = `_stamp_time` 초 베이크 보장 세대) — 구 PNG 거짓 지칭 방지. IN-01 저신뢰(estimatedArea)는 확정 결함이 아니라 미표시. 회전류 기준측 실영상 초 상시 표기는 33-12 `stamp_ref`(백엔드)로 기완료 — 앱 추가 작업 없음 확인.

### Task 2 — safe-area + 자세히보기 + 어포던스 + 타입 스케일 (`b613886`, D-17)

- **safe-area 버그(유일한 실버그)**: 콘텐츠 안쪽 고정 `paddingTop: layout.safeAreaTop(59)` → 컨테이너 레벨 `useSafeAreaInsets().top` 으로 이전 (wrapper·본문 두 분기 동일). 고정 패딩이 스크롤 콘텐츠 내부라 스크롤 시 본문이 상태바 아래로 파고들던 구조 자체를 제거 — 뷰포트가 상태바 아래에서 시작. SafeAreaProvider = expo-router 루트 제공 (inquiry.tsx 선례, 신규 패키지 0).
- **자세히 보기 토글/스크롤**: 종전 topFix 점프(요약 바로 아래 = 거의 무이동 "오정지" + 재탭 무반응)를 → 펼침 시 점수 상세 앵커(게이지 카드 1순위 → 내역 섹션 2순위, onLayout 실측 y) 스크롤 + SummaryCard 라벨 `접기`/chevron-up, 재탭 시 최상단 복귀. 앵커 키 = `anchor:*` 전용 슬롯 (record 키 공간과 분리).
- **추가 항목 어포던스**: 오늘 고칠 것 카드 아래 "아래에 다른 감점 항목 N개 더 보기 ›" — 탭 시 '다른 감점 항목' 섹션으로 스크롤. 표시 조건 = 목록 섹션 렌더 조건 미러(모순 링크 0), 스팟체크 숨김 record 제외 카운트.
- **타입 스케일 전수**: 대상 파일 하드코딩 fontSize 0 확인 (grep). 유일한 인라인 잔재 OctagonScore `52/36` → `typography.scoreGaugeLg/Sm` 토큰화 (값 불변 — 렌더 diff 0 의도) + fontFamily 공급으로 Pretendard 정합(시스템 폰트 잔재 해소). letterSpacing 전 토큰 track()=0 유지 (iOS 26+ SIGABRT 가드).
- **좌우 여백 통일**: 최상위 텍스트 블록(mode3LimitNotice — IN-01 안내·성장 폴백 공용)의 임의 `paddingHorizontal: 4` 제거 — 좌우 가장자리는 content 의 `spacing.screenX` 단일 기준. 카드 내부 소형 인셋은 화면 여백이 아니라 무접촉.

## 검증 결과 (수치)

- **app**: `npm run typecheck` (tsc --noEmit) **clean** — Task 1·Task 2 각각 + 최종 재확인 (총 3회).
- **backend pytest**: `tests/phase33` + `tests/phase32/test_terminology_lockstep.py` = **69 passed / 0 failed** — **신규 깨짐 0** (백엔드 파일 무변경이므로 어휘 게이트·terminology lockstep 핀 무영향 확인용).
- **채점 무접촉 (D-20)**: 커밋 2건 diff = app/ 7파일뿐 — dimensions/kismam/deduction_engine/fault_zoom/pipeline grep 0. 점수 값·산식·임계값 접촉 0 (표시 크기·거처만 변경).
- **어휘 게이트**: 신규 diff 렌더 카피에 국면·신전·재신전·완성도 **0건** (grep). 기존 terminologyMap `line` 값의 "완성도"는 backend lockstep 고정 데이터(D-12 승인 표면)라 무접촉 — 신규 위반 문구 생성 0.
- **모순 카피**: `점수에 반영된` 렌더 카피 grep 0건 (수정 이력 주석에만 잔존).
- **Pod 무접촉**: 실분석/Pod 호출 0 (재검증 스위프 직렬 보호 — 검증 전부 로컬).
- **OTA 미발행**: 33-16 일괄 (플랜 계약).

## 10동작 일반화 성립 (blocking anti-pattern 대조)

동작명 하드코딩: **diff 내 0건** (`power.spin|foxtop|kip.up|...` grep 0). 모든 신규 규칙의 키잉 데이터:

- 각도 참고 행 = `displayTips[].joint`(doc 데이터) + `JOINT_LABEL_KO`(관절 이름공간 — 동작 무관), 등재 10동작 + mode3 공통
- 초 표기 라벨 게이트 = `zoom.criterion` 존재 여부(doc 데이터 — 파이프라인 세대 판별), 동작 무관
- 수치 강등 = typography 토큰 (전 동작·전 record 공통)
- 어포던스/앵커 = records 배열·섹션 렌더 조건(런타임 데이터), 동작 무관
- 조사 판정 = 한글 종성 유니코드 산술 (terminologyMap 전 항목 + 미등록 폴백 공통)

## Deviations from Plan

**1. [범위 내 판단] plan files_modified 밖 3파일 수정 + resultSections.ts 무변경**
- **Issue:** 계획 files_modified 는 result/시트/참고코너/resultSections/typography 5파일이나, 수치(−17.4·51점)의 물리적 렌더러는 `ScoreBreakdownSection.tsx`, 자세히보기 라벨 표면은 `SummaryCard.tsx`, 인라인 fontSize 잔재는 `OctagonScore.tsx`에 있었음
- **Fix:** 해당 3파일을 최소 diff 로 수정 (내역 prop 신설·옵셔널 prop·값 불변 토큰화 — 타 소비처 렌더 diff 0). `resultSections.ts` 는 섹션 순서·가시성 변경이 없어 무변경
- **Commits:** 3b5cf55, b613886

**2. [해석 결정] legacy doc 각도 수치 = 코칭 팁 잔류**
- **Issue:** "move, don't delete" — 내역 카드 부재 doc(legacy/미등록 동작)에서 각도 줄을 제거하면 이동할 거처가 없어 수치가 소멸(투명 공개 위반)
- **Fix:** `angleNumbersRelocated = showBreakdownSection` 게이트 — 내역 보유 doc 만 이동, legacy 는 종전 각도 줄 유지. 새 분석(mode1 전체 + 등록 mode3)은 전부 이동 경로

**3. [Rule 2 - 승인 계약 편입] 초 표기 라벨 문형 (A-6 이관분)**
- **Found during:** 플랜 로드 시 (33-13-SUMMARY Deferred + 오케스트레이터 제약 명시)
- **Issue:** 플랜 태스크 본문엔 없으나 belle 확인 ① 6R 확정 문형("감점 부분" 계열 + 괄호 보조 = 브랜드 컬러)이 33-15 상세 시트 소관으로 이관돼 있어 미구현 시 승인 계약 위반
- **Fix:** 시트 크롭 캡션 1줄 + 브랜드 괄호 스타일. criterion 게이트로 구 PNG 거짓 지칭 차단. "(감점 유지된 채 마무리)" 변형은 증거 컷 스트립(다중 컷) 전용 문형이라 단일 합성 크롭인 현 시트에는 미적용 — 문형 확장은 컷 스트립 표면이 생길 때
- **Commit:** 3b5cf55

**4. [해석 결정] OctagonScore "51점"은 크기 유지 (토큰화만)**
- **Issue:** D-16 "51점 헤드라인급 강등"의 후보 표면 중 게이지 중앙 수치(52pt)가 최대이나, 게이지는 D-09 로 이미 상세 영역으로 **위치** 강등된 채점 표면 본체 + 홈 탭 공용 컴포넌트
- **Fix:** D-16 대상 = 설명 인접 표면의 수치(내역·심사·근거 박스 — 전부 metricNumber 강등)로 해석, 게이지는 값 불변 토큰화만. 33-16 시뮬 확인에서 belle 재판단 재료로 명시

**Total deviations:** 2 해석 결정, 1 범위 내 판단, 1 Rule 2 편입

## 무엇을 열어서 확인했는가 (D-19) — 33-16 시뮬레이터 예약 항목

이번 플랜에서 직접 연 것: 목업 index.html 6R 문형·.pnote 스타일 원문, `_stamp_time`/stamp_ref 백엔드 소스(초 베이크 세대 확인), terminologyMap 전 값(조사 판정 대상), diff 전수 grep. **레이아웃·스크롤·겹침은 typecheck 가 못 잡는다** (D-21) — 아래를 33-16 시뮬레이터에서 육안 확인할 것. "typecheck passed"는 이 확인을 대체하지 않는다:

1. **safe-area**: 결과 화면 진입 + 스크롤 시 본문이 상단 상태바(시계)와 겹치지 않는지 (구 59 고정 대비 기기별 inset 반영).
2. **각도 수치 이동**: 코칭 팁 카드에 `X° → Y°` 없음(행동 언어만) + 점수 계산 내역 하단 '관절 각도 참고' 행 표시. legacy doc 은 팁에 수치 잔류(의도된 폴백).
3. **모순 카피**: 참고하세요 섹션 = "점수에는 반영되지 않아요" + 안내 1줄 + 자세 비교 캡션 "분석에서 비교한 순간…" (동거 해소).
4. **수치 강등**: 내역 −X·= 종합·심사 코너·시트 근거 박스 숫자가 badge 스케일(17)로 렌더 — 줄겹침·잘림 없는지.
5. **초 표기 라벨**: criterion 카드 시트에서 "(감점 부분)" 브랜드 컬러 괄호 + 크롭 베이크 초와 실제 대응 / legacy 카드 미표시. (crop 재생성은 Pod 재스위프 후 — 33-12 D-19 와 동일 완결 지점.)
6. **자세히 보기**: 탭 → 점수 상세로 스크롤 + '접기' 전환, 재탭 → 최상단 복귀. 오정지(엉뚱한 위치 멈춤) 재현 없는지.
7. **어포던스**: 오늘 고칠 것 아래 'N개 더 보기' 탭 → 다른 감점 항목 목록 도달.
8. **OctagonScore**: 홈 탭 + 결과 화면 중앙 수치 Pretendard 렌더 (공용 컴포넌트 — 값 불변 확인).

## 틀리면 걸리는 장치 (D-18)

- 렌더 크래시: tsc strict + 신규 스타일 전부 토큰 스프레드 (음수 letterSpacing 0 — track() 경유만).
- 어휘 재유입: 백엔드 `test_screen_vocabulary_gate` 핀 유지 (69 passed 재확인) — 앱 신규 카피는 diff grep 으로 0건 검증.
- 초 라벨 거짓 지칭: criterion 게이트 — 초 미베이크 세대 크롭은 라벨 렌더 경로 자체가 없음.
- 조사 오표기: objectJosa 종성 산술 — terminologyMap 5값 전수 수기 대조 (힘→을, 나머지→를).
- 레이아웃 회귀: 33-16 시뮬 예약 8항목 (위) — typecheck 사각지대 명시.

## Known Stubs

없음 — placeholder/빈 데이터 배선 0. 모든 신규 표면은 기존 저장값(records·tips·zoom.criterion)에 배선.

## Threat Flags

없음 — 신규 네트워크 표면·인증 경로·스키마 변경 0. T-33-51(음수 letterSpacing SIGABRT) = track()=0 유지 + 33-16 시뮬 예약, T-33-52(모순 잔존) = grep 0 + 시뮬 예약 3, T-33-53(크롭 배지 이중 처리) = 앱측 크롭 무접촉 grep 확인.

## Task Commits

1. **Task 1: 각도 수치 이동 + 모순 카피 + 수치 강등 + 초 표기 라벨 (D-16)** — `3b5cf55` (feat)
2. **Task 2: safe-area + 자세히보기 토글 + 어포던스 + 타입 스케일 (D-17)** — `b613886` (feat)

## Next Phase Readiness

- **33-16 (페이즈 게이트)**: 위 시뮬 예약 8항목 + Pod 재스위프 후 크롭 초·criterion 전수 열람 + OTA 일괄 발행 (이 플랜 OTA 0).
- 일러스트 슬롯(33-14) 위치 계약 유지 확인 — 시트 diff 는 캡션/문장화/수치 토큰만, illustrationSlot 순서 무접촉.

## Self-Check: PASSED

- 수정 파일 7개 존재 확인 (git diff 목록 = 계획+판단 범위)
- 커밋 2건 존재 확인 (3b5cf55, b613886)
- 코드 앵커 존재: angleReference/관절 각도 참고(ScoreBreakdownSection), metricNumber·scoreGaugeLg(typography), objectJosa·TIME_STAMP_NOTE_PAREN(DeductionDetailSheet), useSafeAreaInsets·anchor:scoreGauge(result.tsx), expanded(SummaryCard)
- typecheck clean + pytest 69 passed 재확인

---
*Phase: 33-result-trust-recovery*
*Completed: 2026-07-29*
