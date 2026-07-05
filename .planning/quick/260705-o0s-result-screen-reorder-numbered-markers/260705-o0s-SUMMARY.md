---
phase: quick-260705-o0s
plan: 01
subsystem: app-result-screen
tags: [react-native, overlay, deduction-tally, clean-pass-gate, section-reorder]
requires:
  - quick-260705-k8y (행동 지시 라벨 메커니즘)
  - quick-260704-fz4 (confirmedKeypoints 단일 소스 + 2단 시각 언어)
  - quick-260702-q8q (ScoreBreakdownSection)
  - quick-260702-t0v (sizeScale 메커니즘)
provides:
  - buildDeductionMarkers/isCleanPass/composeShortActionLabelKo/composeScoringBasisKo 순수 헬퍼
  - 결과 화면 승인 섹션 순서 (내역 승격 + 참고 지표 강등)
  - 감점 0 게이트 (문제-계열 섹션 숨김 + 축하 섹션/카피)
affects:
  - app/src/app/analysis/result.tsx
  - app/src/components/KeypointOverlay.tsx
  - app/src/components/ScoreBreakdownSection.tsx
tech-stack:
  added: []
  patterns:
    - "표·마커 동일 소스 (buildDeductionMarkers — fz4 confirmedKeypoints 선례)"
    - "단일 게이트 신호 (isCleanPass — 분기 산개 금지)"
key-files:
  created: []
  modified:
    - app/src/lib/deductionLabels.ts
    - app/src/types/analysis.ts
    - app/src/components/KeypointOverlay.tsx
    - app/src/components/ScoreBreakdownSection.tsx
    - app/src/app/analysis/result.tsx
    - app/src/theme/colors.ts
  deleted:
    - app/src/components/ForcePatternCard.tsx
    - app/src/components/ForcePatternDetailModal.tsx
decisions:
  - "번호 부여 first-wins: 앞 record 가 번호 붙인 keypoint 는 첫 번호 유지 — 점 하나에 숫자 하나"
  - "geometry 소스의 관절명 없는 record(leg_extension 등)는 투영 없음 → 내역 행 번호 없이 정직 표기"
  - "advisory(주황) 관절 라벨 미부여 — 감점 아님, 영상 위 최소 표시"
  - "cleanPass 여도 점수 계산 내역 렌더 유지 — '측정 감점 없음' 행이 100점의 공식 근거"
metrics:
  duration: ~25min
  completed: 2026-07-05
  tasks: 3
  commits: [24c5bfb, 2b85c24, e02fba9]
---

# Quick 260705-o0s: 결과 화면 재배치 + 번호 오버레이 + 감점 0 게이트 Summary

belle 3차 실기기 피드백 반영 — 감점 record 관절에만 빨간 번호 점(내역 행과 단일 소스), 각도 숫자 없는 짧은 행동구(dedupe), 점수 계산 내역 승격 + 채점 기준 1줄, 실패 원인 후보 삭제, 참고 지표 개명·강등, 감점 0(100점) 시 보완 카피 금지 + 축하 섹션.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | 순수 헬퍼 4종 + 차원 라벨 개명 | 24c5bfb | deductionLabels.ts, types/analysis.ts |
| 2 | 오버레이 번호 점 + 내역 번호/기준문구 prop | 2b85c24 | KeypointOverlay.tsx, ScoreBreakdownSection.tsx |
| 3 | result.tsx 재배치 + 삭제 + 게이트 + 배선 | e02fba9 | result.tsx, deductionLabels.ts, colors.ts, types/analysis.ts, ForcePattern 2파일 삭제 |

## 섹션 순서 (구현 결과, 승인 순서 정합)

header → mode1 기준 모션 메타 카드 → ① 종합 점수 카드(억제 분기 유지) → 부상 위험 InjuryRiskSection → [감점 0: 성공 축하 카드] → ② 점수 계산 내역(번호 + 채점 기준 1줄) → 구간별 점수(콤보) → ③ 동작 비교(영상 + 오버레이) → ④ 문제 부위 확대 비교(감점 0 숨김) → ⑤ 코칭 팁('먼저 교정할 점' lead 는 감점 0 숨김) → ⑥ 강사에게 확인할 점 → 보완 운동 → ⑦ 참고 지표(구 세부 점수, 맨 아래) → CTA.

미언급 섹션 재량 배치 근거: 부상 위험 = 안전 신호라 점수 직후 유지 / 구간별 점수 = 점수 상세 계열이라 내역 직후 / 보완 운동 = 행동 콘텐츠라 참고 지표 위 유지.

## 시뮬레이션 (1) 최악 케이스 — record 4개 + advisory 2관절, 재생 중

가정 doc: records = [split_angle(source=vision, faultJoints=[left_hip, right_hip]), angle_vs_reference__left_knee, angle_vs_reference__right_elbow, angle_vs_reference__left_shoulder], windowMedianAngleDeltas 에 hip 부호 없음(vision-측정 split), advisory(주황) = right_knee, right_shoulder.

- **빨간 번호 점**: 5개 점 / 4개 번호. split record → 양쪽 hip 에 같은 ① (같은 감점의 시각 분산), left_knee=②, right_hand=③(elbow proxy), left_shoulder=④. buildDeductionMarkers first-wins 로 점 하나당 숫자 하나 보장.
- **주황 점**: 2개(right_knee, right_shoulder) — 라벨·번호 없음 (감점 아님, 점만).
- **라벨(dedupe 후)**: 최대 3개 — "왼쪽 무릎 더 펴기"(②), "오른쪽 팔꿈치 더 펴기"(③), "팔 더 벌리기"(④). hip 은 windowMedian 부호 부재 → 라벨 없이 번호 점만 (방향 fabricate 금지). hip 부호가 있는 케이스라도 좌우 "다리 더 모으기" 는 dedupe 로 |delta| 큰 1개만.
- **pill 폭 추정(labelTextWidth, S=1 명목 pt)**: "왼쪽 무릎 더 펴기" = 한글 7×14 + 공백 3×8 + 패딩 16 ≈ 138 / "팔 더 벌리기" = 한글 5×14 + 공백 2×8 + 16 ≈ 102. 이전 라벨 "왼쪽 무릎 23° 더 펴야" ≈ 170 대비 개당 ~20~40% 감소.
- **이전 대비 정량**: 구 렌더 = 라벨 5개+(주황 포함 시 7개) × 각도 숫자 포함 긴 pill 이 영상 중앙부를 뒤덮음. 신 렌더 = 라벨 ≤3개(짧은 행동구) + 번호 점 5 + 주황 점 2 — 라벨 면적 대략 60% 이상 감소, 각도 수치는 내역 행 ①~④ 로 이동.
- **세로 카드 vs 가로 전체화면**: sizeScale 메커니즘 재사용 — 세로 S=1(번호 fontSize 13 normalized), 가로 전체화면 S=2(모든 점/번호/라벨 2배). 동일 규칙 자동, 신규 분기 0.
- **내역 행 대응**: ① 다리 스플릿 각도 −N / ② 왼쪽 무릎(정은지 대비 각도) −N / ③ 오른쪽 팔꿈치(정은지 대비 각도) −N / ④ 왼쪽 어깨(정은지 대비 각도) −N + 상단 채점 기준 1줄 + "번호는 위 영상의 빨간 점 위치와 같아요." 각주.

## 시뮬레이션 (2) 감점 0 케이스 — 정은지 정타 100점 (records 빈 배열)

- **노출 섹션**: 기준 모션 메타 카드 / 종합 점수 카드(100) / (safetyFlags 있으면) 부상 위험 / **성공 축하 카드** / 점수 계산 내역("측정 감점 없음 — 기준 점수 그대로예요.", 채점 기준 1줄은 records 빈 배열이라 null → 미표기) / 동작 비교(오버레이 = 뼈대만, 번호·라벨 자연히 0) / 코칭 팁(backend tips 잔여) / 강사에게 확인할 점(질문 있으면) / 보완 운동 / 참고 지표 / CTA.
- **숨김 섹션**: 문제 부위 확대 비교(advisory 2° 노이즈 카드 포함 전체) / '먼저 교정할 점' lead 카드. 실패 원인 후보는 섹션 삭제로 자동 해소.
- **요약 카피 실제 문자열**:
  - summary: "정은지 선수와 동일한 수준이에요. 이 자세를 유지하세요!"
  - ScoreContext: "정은지 기준 100점 — 감점 항목 없이 통과했어요."
  - 축하 카드: "감점 항목이 없어요" / "측정 기준을 모두 통과했어요. 이 자세를 그대로 유지하세요."
- **"보완하면 더 올라가요" / "거의 다 왔어요" 미출현 확인**: mode1Summary cleanPass 분기가 티어 카피("거의 다 왔어요!" 등) 전부 우회, ScoreContext cleanPass 분기가 correctionPoint 조립("보완하면 더 올라가요") 우회. 두 소비처 모두 isCleanPass 단일 신호.
- cleanPass=false(감점 있는 doc) 경로는 게이트 도입 전과 동일 렌더 (섹션 순서 재배치 제외).

## (3) DIMENSION_LABEL_KO 개명 소비처 목록

`grep -rn "DIMENSION_LABEL_KO" app/src` 결과 (types/analysis.ts 선언 제외):

| 소비처 | 위치 | 영향 |
| ------ | ---- | ---- |
| result.tsx DimensionScoreRow | partLabel + 자세히 accessibilityLabel | '각도 유사도'/'안정성' 렌더 + ' (참고)' 접미(결과 화면 전용 labelSuffix prop) |
| DimensionDetailModal.tsx | 모달 제목 라벨 | 개명 자동 반영 (접미 없음 — 의도, 접미는 결과 화면 렌더 전용) |

표시 문자열만 변경 — ScoreDimension 계약 키 무접촉 (contract.md 미러 대상 아님). 기록 탭/차트 소비처 없음. auxCaption 도 "동작 안정성은" → "안정성은" 정합 갱신.

## (4) 실패 원인 후보 시트 정보 흡수 점검

| 시트 고유 정보 | 흡수처 | 상태 |
| ------------- | ------ | ---- |
| 측정 방법 문구(measurementText) | 신규 채점 기준 1줄(composeScoringBasisKo) + 내역 행 detailText | 흡수 완료 |
| 가능한 원인(rootCauseHypotheses) | '먼저 교정할 점' vetoRootCauses (기존 유지) | 기존 커버 |
| 관절별 현재→기준 각도 | 코칭 팁 angleGuide + 내역 detailText | 흡수 완료 |
| windowMedian 전 관절 편차 표(비-record 관절 포함) | 주황 attention 마커로 위치만 표시 (수치 미표시) | 수용된 손실 — 감점 아님(advisory)인 수치를 표에 나열하던 것으로, "영상 위/화면 = 최소 표시" 원칙과 [[window-median-silent-seed-fp-reverted]] 위양성 교훈에 정합. 확정 감점 수치는 전부 내역이 커버 |
| supportCount 신뢰도 라벨 | 미흡수 | 수용된 손실 — fallback finding 카드 전용 표기였고 카드 자체가 중복으로 삭제됨 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] worktree 에 node_modules 부재 → typecheck 불가**
- **Found during:** Task 1 검증
- **Issue:** git worktree 는 node_modules 를 포함하지 않아 `npm run typecheck` 실패
- **Fix:** 메인 repo node_modules 심링크로 검증 수행 후 작업 종료 시 제거 (커밋 오염 0)
- **Files modified:** 없음 (임시 심링크)

**2. [Rule 2 - 정합] grep 게이트 충족 위해 주석 내 '실패 원인 후보' 문구 개서**
- **Found during:** Task 3
- **Issue:** types/analysis.ts 주석 2곳이 삭제된 섹션명을 인용 — 게이트(`grep -rl '실패 원인 후보' src` = 0) 위반 + 삭제된 UI 참조 슬롭
- **Fix:** "힘 패턴 findings" / "원인 카드 UI 는 quick-260705-o0s 에서 삭제" 로 개서. colors.ts 의 ForcePatternCard 주석도 동일 정리
- **Files modified:** app/src/types/analysis.ts, app/src/theme/colors.ts
- **Commit:** e02fba9

## Known Stubs

없음 — 전부 저장값 배선, 하드코딩 빈 값/placeholder 0.

## Threat Flags

없음 — 표시 전용 JS 레이어, 신규 네트워크/저장 경로 0, 백엔드/계약 무접촉.

## Verification

- `npm run typecheck` GREEN (Task 1/2/3 각각 + 최종)
- grep 게이트: `grep -rl '실패 원인 후보' src` = 0 / `grep -rn 'composeDeviationOnlyLabelKo' src | grep -v deductionLabels.ts` = 0
- 섹션 렌더 순서 = 승인 순서 (grep 라인 번호로 확인: 1007 점수 → 1055 축하 → 1072 내역 → 1085 구간 → 1113 비교 → 1195 확대 → 1204 팁 → 1324 강사 → 1353 운동 → 1401 참고 지표 → 1470 CTA)
- prop 미전달 경로(legacy doc/mode3): KeypointOverlay markerNumbers 미전달 → 렌더 diff 0 (G 래핑만, 시각 동일) / ScoreBreakdownSection 두 prop 미전달 → 기존 렌더 동일
- ForcePatternCard/ForcePatternDetailModal 잔여 소비처 0 확인 후 파일 삭제 (의도된 삭제 — git diff --diff-filter=D 로 확인)

## Self-Check: PASSED

- 커밋 3건 존재 확인 (24c5bfb / 2b85c24 / e02fba9)
- SUMMARY.md 생성 확인, ForcePattern 2파일 삭제 확인
- typecheck GREEN + grep 게이트 2건 통과 (최종 재확인)
