---
phase: 29-mode3-result-screen-completion
plan: 04
subsystem: app-result-screen (mode3 결과화면 소비 — 투영 helper + 게이트 무관화 + 안내 UX)
tags: [mode3, result-screen, deduction-projection, ota-safe, wave-2]
requirements: [D-03, D-04, D-05, D-06, D-07, D-10]
dependency_graph:
  requires:
    - "29-02 (mode3_held tally seam — mode3 등록 동작 md 보유 시 deductionBreakdown 방출, overallScore==final)"
  provides:
    - "projectDeductionRecordKeypoints 공용 투영 helper 1벌 (규칙 사본 0) + CRITERION_REGION_KEYPOINTS ipsf_absolute 매핑"
    - "mode1 게이트 3곳(showBreakdownSection·actionLabels hasBreakdown·cleanPass) mode 무관화 — mode3 breakdown 소비"
    - "D-03 미등록 행동 유도 / D-04 배너 통합 / D-05 한계 고지 / D-06 지난·이번 라벨 / D-07 첫 분석 안내 / D-10 워핑 경로 검증"
  affects:
    - "29-03 (backend mode3 zoom criterion→region 파생 — cross-side 매핑 표 대조 대상)"
    - "29-08 (HUMAN-UAT — power-spin 드릴다운·mode3 second+ 워핑 실기기 확인 항목)"
tech_stack:
  added: []
  patterns:
    - "규칙 1벌: 두 사본(buildDeductionMarkers 내부 + result.tsx 로컬)을 projectDeductionRecordKeypoints 공용 helper 로 이관"
    - "optional prop diff-0 관례 (ScoreBreakdownSection.limitNotice) — 미전달 시 렌더 무변경"
    - "reason-owns-copy (suppressedHeaderCopy) 유지 + 행동 유도로 카피 전진"
key_files:
  created: []
  modified:
    - app/src/lib/deductionLabels.ts
    - app/src/app/analysis/result.tsx
    - app/src/components/ScoreBreakdownSection.tsx
decisions:
  - "criterion 테이블 분기를 source==='vision' 분기 뒤에 배치 — mode1 vision-sourced split_angle 은 종전 faultJoints 투영 불변 (테이블 legs 4관절 드리프트 금지)"
  - "그룹(중점) 마커 판정을 source==='vision' 한정에서 projected.length>=2 로 일반화 — mode3 leg_extension legs 4관절도 centroid 1점"
  - "D-04: legacy 전용 배너 신설 대신 Phase 28 alignUpsellBanner 통합 (재량) — 빈 criteria 신선 doc 에서도 참인 판정이라 거짓 약속 회피 위해 '최신 분석 적용' 일반화"
  - "D-05: mode3 결과에 한계 고지 정확히 1곳 — breakdown 있으면 ScoreBreakdownSection footnote, 없으면 !showBreakdownSection 독립 1줄"
  - "D-06: mode3 드릴다운(DeductionDetailSheet) 라벨도 '지난 영상' 으로 일관 (VideoCompare 와 동일 계열)"
metrics:
  duration_min: 40
  tasks_completed: 4
  files_created: 0
  completed_date: 2026-07-16
---

# Phase 29 Plan 04: Mode3 결과화면 앱 소비 Summary

**한 줄:** 29-02 가 방출하는 mode3 `deductionBreakdown` 을 앱이 그리도록 criterion→keypoint 투영 규칙을 공용 helper 1벌(`projectDeductionRecordKeypoints` + ipsf_absolute 매핑)로 승격하고, mode1 게이트 3곳을 mode 무관화하며, D-03(행동 유도)·D-04(배너 통합)·D-05(한계 고지)·D-06(지난/이번 라벨)·D-07(첫 분석 안내)·D-10(워핑 경로 검증) UX 를 완성했다 — 전부 OTA-safe(JS-only).

## 수행 내역

### Task 1 — HIGH-1 투영 helper + ipsf_absolute 매핑 (commit 3ecb6cc)

- `deductionLabels.ts`: `projectDeductionRecordKeypoints(record, faultJoints)` 신설 — 종전 두 사본(buildDeductionMarkers 내부 :200-216, result.tsx `recordProjectedKeypoints` :288-305)의 규칙을 이 한 함수로 이관 (규칙 사본 0).
- `CRITERION_REGION_KEYPOINTS` 모듈 상수 테이블 추가 — 값은 `REGION_MEMBER_KEYPOINTS` 재사용(중복 선언 0).
- **평가 순서 고정:** (1) fallback/score_delta → [] / (2) angle_vs_reference__{jk} → 단일 keypoint / (3) source==='vision' → faultJoints 전체 / (4) 위 3규칙 비매치 record 에만 criterion 테이블 적용. mode1 vision-sourced split_angle 은 (3)에서 faultJoints 로 투영되고 테이블 legs 4관절로 절대 바뀌지 않음 (무회귀).
- `buildDeductionMarkers` 가 helper 소비 + 그룹 마커 판정 `source==='vision'` 한정 → `projected.length >= 2` 일반화 (mode3 leg_extension legs 4관절 = centroid 그룹 1점).
- `result.tsx`: 로컬 `recordProjectedKeypoints` 삭제 → helper import. `actionPhraseForRecord`·`selectedZoom` 소비 경로 인자 동일 — 호출부 무변경.

### Task 2 — mode1 게이트 3곳 mode 무관화 + D-03 (commit 51d80eb)

- `showBreakdownSection`: `cmp.mode === 'mode1' &&` 제거 → `result.deductionBreakdown != null` 단독.
- `actionLabels` 내부 `hasBreakdown`: 동일 mode1 조건 제거.
- `cleanPass`: `isCleanPass(cmp.mode === 'mode1' ? ... : null)` → `isCleanPass(result.deductionBreakdown)` mode 무관.
- mode3 감점 0 축하 카피 별도 신설 (cleanPass 카드 mode 분기, 발전/자세 형태 중심, 정은지 미언급, "각도" 0).
- D-03: `suppressedHeaderCopy` 미등록(unheld)/저신뢰 케이스를 "제공 불가" 단독 통보 → 행동 유도(코치님 비교/새 영상 이전 연습 비교)로 전진형 교체. reason-owns-copy 구조 유지.
- `timelineTicks`·`useDiagnosis`·`vetoApplied` 무변경 (mode3 는 window 시점/veto 없음 — 빈 배열 유지가 정직).

### Task 3 — D-04 배너 통합 + D-05 한계 고지 (commit 853b6da)

- `ScoreBreakdownSection`: `limitNotice?: string` optional prop 신설 — 카드 최하단 footnote 슬롯에 기존 footnote 토큰으로 렌더, 미전달 시 diff 0.
- `result.tsx`: `MODE3_LIMIT_NOTICE` 모듈 상수(belle 승인 뼈대) — breakdown 표시 중이면 ScoreBreakdownSection footnote, 부재(미등록/legacy/빈 criteria/suppressed)면 `!showBreakdownSection` 게이트로 독립 1줄. mode3 결과에 한계 고지 정확히 1곳.
- D-04: `alignUpsellBanner`(motionAlignment===undefined 판정) 카피를 "다시 분석하면 자동 구간 맞춤 등 최신 분석이 적용돼요" 로 일반화 — mode3 전용 배너 신설 없음.
- "각도" 0건 (ScoreBreakdownSection + 신규 카피).

### Task 4 — D-06 라벨 + D-07 안내 + D-10 검증 (commit 04bad79)

- D-06: mode3 `leftLabel` `'이번 영상'` / `rightLabel` `'지난 영상'` (VideoCompare + DeductionDetailSheet 일관). mode1 라벨(`${cmp.athleteName} 선수`) diff 0.
- D-07: 첫 분석(mode3 isFirst) 비교 섹션 숨김 게이트 유지 + 안내 1줄 신설 ("다음 분석부터 이전 영상과 비교해 발전을 확인해 드려요.", D-05 톤 통일, 정은지 폴백 없음).
- D-10: `alignment={videoAlignment}` 전달부에 mode 조건 추가 없음 확인 + 근거 주석. 신규 워핑 코드 0. `VideoCompare.tsx`(29-07 소유) 무접촉.

## criterion → 투영 매핑 표 (cross-side 박제 — 29-03 SUMMARY 표와 대조용)

| criterion id | 29-04 앱 helper (projectDeductionRecordKeypoints) | 29-03 backend zoom region | 일치 |
|---|---|---|---|
| `leg_extension` | REGION_MEMBER_KEYPOINTS.legs (left_hip, right_hip, left_knee, right_knee) | `legs` | ✓ |
| `arm_extension` | REGION_MEMBER_KEYPOINTS.arms (left_shoulder, right_shoulder, left_hand, right_hand) | `arms` | ✓ |
| `split_angle` | REGION_MEMBER_KEYPOINTS.legs | `legs` | ✓ |
| `line` | 무투영 [] (의도된 결정 — collective 전신 라인, joint_keys 빈 튜플) | 무방출 | ✓ |
| `dimension_overall_fallback` / `unit=score_delta` / 미등록 id | 무투영 [] (fabricate 0) | 무방출 | ✓ |

앱은 `record.source==='vision'`(mode1 vision-sourced) 분기가 테이블보다 **앞**이므로, mode1 vision split_angle record 는 테이블 legs 고정값이 아닌 faultJoints(vision 확정 부분집합)로 투영된다 — 두 측 계약은 **mode3 geometry-sourced record**(source!='vision')에 한해 일치한다. 29-03 backend 는 mode3 경로만 파생하므로 정합.

## 검증 결과

- `cd app && npm run typecheck` exit 0 (4개 태스크 각각 + 최종).
- 투영 규칙 1벌: `grep -c "function recordProjectedKeypoints" result.tsx` = 0 (로컬 사본 제거), helper grep = deductionLabels + result 양쪽 존재.
- 금지어 게이트: 전체 added-lines(base 3052043 대비) "각도" 0건(sed 's/심각도//g' 후), `ScoreBreakdownSection.tsx` "각도" 0건.
- D-05 3요소("자세 형태 기준" + "새 영상" + "코치님") 문구 존재.
- `alignUpsellBanner` 렌더 블록 1개 (전용 배너 신설 없음).
- `VideoCompare.tsx` diff 0 (29-07 소유권 침범 없음).

## Deviations from Plan

### Auto-fixed / 재량 판정

**1. [재량] `line`·미등록 criterion 무투영을 helper 폴백으로 처리 (테이블 항목 미기재)**
- **Found during:** Task 1
- **내용:** `CRITERION_REGION_KEYPOINTS` 에 `line` 을 명시 항목으로 넣지 않고, 테이블 미등록 id 는 helper 가 자동 `[]` 반환하도록 했다 (fabricate 0). `line` 무투영은 상수 주석 + SUMMARY 표에 의도로 문서화. plan 지시("line → 투영 없음, 주석으로 문서화")와 의미 동일 — 테이블에 `line: []` 를 넣지 않고 폴백으로 흡수해 "미등록=무투영" 규칙을 단일화.
- **Files modified:** app/src/lib/deductionLabels.ts
- **Commit:** 3ecb6cc

**2. [재량] D-06 드릴다운(DeductionDetailSheet) rightLabel 도 '지난 영상' 으로 변경**
- **Found during:** Task 4
- **내용:** plan D-06 은 VideoCompare rightLabel(:1394)만 명시했으나, DeductionDetailSheet(:1862)도 mode3 비교 라벨을 나르므로 '지난 분석' → '지난 영상' 으로 일관 정렬 (정은지 미언급 유지). mode1 라벨 무변경.
- **Files modified:** app/src/app/analysis/result.tsx
- **Commit:** 04bad79

기타: plan 그대로 실행.

## 전제 보정 확인 (Pitfall 1)

- 등록 5동작 중 4동작은 criteria 가 비어 breakdown 미방출 — "Mode3 내역" 실질 콘텐츠는 power-spin(등) 외 없음. breakdown 부재를 버그로 취급하지 않았고, D-05 한계 고지가 UX 본체가 되도록 breakdown 유/무 양쪽에 고지 1줄이 도달하게 배선.

## 29-08 HUMAN-UAT 후보 항목 (실기기 확인 적립)

- mode3 power-spin(등록 동작) 결과에서 감점 record → 내역 행 번호 · 그룹 마커(legs centroid) · region 'legs' zoom 드릴다운이 실제로 표시되는지.
- mode3 second+ 워핑: 이전 영상이 이번 영상 타임라인에 워핑돼 재생되는지(28 신뢰도 사다리·배속 클램프 동일 적용).
- mode3 미등록/legacy/첫 분석 각 경로에서 한계 고지·행동 유도·안내 1줄이 정확히 1곳씩 표시되는지.

## Known Stubs

없음 — 이 plan 산출물에 stub/placeholder 0 (added-lines TODO/FIXME/placeholder 스캔 0).

## Threat Flags

없음 — 신규 네트워크/인증/파일 접근 표면 0. threat register 전부 mitigate: T-29-04-01(앱 재계산)=투영은 표시 매핑만·값 무변경, T-29-04-02(malformed crash)=미등록 criterion → [] + normalize undefined 접기, T-29-04-03(오신뢰)=D-05 한계 고지 필수 렌더 + D-04 카피 일반화. 패키지 설치 0.

## Commits

| Task | Commit | 내용 |
|------|--------|------|
| 1 | 3ecb6cc | feat(29-04): projectDeductionRecordKeypoints 공용 투영 helper + ipsf_absolute 매핑 |
| 2 | 51d80eb | feat(29-04): mode1 게이트 3곳 mode 무관화 + D-03 행동 유도 안내 |
| 3 | 853b6da | feat(29-04): D-04 legacy 재분석 배너 통합 + D-05 한계 고지 |
| 4 | 04bad79 | feat(29-04): D-06 비교 라벨 + D-07 첫 분석 안내 + D-10 워핑 경로 검증 |

## Self-Check: PASSED

- 수정 파일 3종 존재 확인 (deductionLabels.ts / result.tsx / ScoreBreakdownSection.tsx).
- 커밋 4건 존재 확인 (3ecb6cc / 51d80eb / 853b6da / 04bad79).
- 최종 typecheck exit 0, node_modules 심링크 제거 후 working tree clean (node_modules 미커밋).
