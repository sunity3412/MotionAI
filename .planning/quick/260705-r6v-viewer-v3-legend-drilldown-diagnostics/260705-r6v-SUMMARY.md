---
quick: 260705-r6v
title: 뷰어 v3 + 드릴다운 시트 + 참고 지표 진단 문장
status: complete
completed: 2026-07-05
tasks: 3/3
typecheck: GREEN
scope: JS-only (OTA), app/src 한정 — 백엔드/계약 무접촉
---

# quick-260705-r6v — 뷰어 v3 + 드릴다운 + 진단 문장 Summary

belle 실기기 4차 피드백 + 해외 사례(Sportsbox/HomeCourt/Tempo/Frame.io) 수렴 설계 3건을
결과 화면에 배선했다. 재생 중엔 번호 점만, 설명은 여백 범례/드릴다운 시트로 — "번호 다 1"
혼란과 "각도 유사도 99 인데 47점" 모순 카피를 해소한다.

## 커밋

- `3571087` feat(quick-260705-r6v): deductionLabels 순수 helper — 그룹 마커/타임라인 틱/진단 문장
- `5759c9e` feat(quick-260705-r6v): 뷰어 v3 — pill 제거 + 중점 점 + 여백 범례 + 타임라인 틱
- `4dcfb10` feat(quick-260705-r6v): 확대사진 드릴다운 시트 + 참고 지표 진단 문장 전환

## 변경 파일 (app/src 한정, 7)

- `app/src/lib/deductionLabels.ts` — buildDeductionMarkers.groupMarkers 확장 + buildDeductionTicks + composeDimensionDiagnosisKo + circledNumberKo 승격
- `app/src/components/KeypointOverlay.tsx` — 텍스트 pill 전면 제거, groupMarkers centroid 1점, onMarkerPress 히트 레이어(box-none)
- `app/src/components/VideoCompare.tsx` — overlayContainer box-none, 전체화면 여백 범례, 재생바 결함 틱(탭=동기 seek)
- `app/src/components/ScoreBreakdownSection.tsx` — onRecordPress 행 탭 진입점 + chevron, circledNumberKo import
- `app/src/components/DeductionDetailSheet.tsx` — 신설 (확대사진 + 수치 + 행동구 드릴다운)
- `app/src/components/FaultZoomCompare.tsx` — 삭제 (소비처 1곳 → 시트로 자산 이식)
- `app/src/app/analysis/result.tsx` — 배선(그룹 마커/범례/틱/시트 3 진입점/진단 문장 전환/섹션 제거)

## 검증

- `cd app && npm run typecheck` → GREEN (유일한 정적 게이트)
- grep 게이트: KeypointOverlay 에 pill 잔재(labelTextWidth/showAngleLabels/actionLabels/Rect) 0, FaultZoomCompare 참조 0, DeductionDetailSheet/composeDimensionDiagnosisKo/onMarkerPress/seekBoth 배선 존재
- diff 범위: 전부 `app/src` (JS-only, OTA 가능). 백엔드/계약/테마 토큰 정의 무접촉. 저장값 재계산 0, 하드코딩 색/간격 0, 이모지 0.

---

## 1. 최악 케이스 시뮬레이션 — 감점 4건 재생 중 화면

가정: 스플릿(vision, faultJoints=[left_hip,right_hip,left_knee,right_knee]) ① +
왼어깨(angle_vs_reference__left_shoulder) ② + 오른어깨(angle_vs_reference__right_shoulder) ③ +
팔꿈치(angle_vs_reference__left_elbow→left_hand) ④.

### (a) 영상 위 점 개수/위치 (재생 중, 텍스트 pill 0)

buildDeductionMarkers 결과:
- 스플릿 record → `groupMarkers=[{ number:1, keypoints:[left_hip,right_hip,left_knee,right_knee] }]`
  (4관절 각각 keypointNumbers 미기록 — first-wins 점유). KeypointOverlay 가 4관절 현재 frame
  위치 산술 평균(centroid) **1점**에 강조 원 + 흰 "①". 다리 4관절 자체는 highlightKeypoints 로
  빨강 강조(bone 포함) 유지하되 **개별 숫자 없음** → "번호 다 1" 근본 해소.
- 왼어깨 ② / 오른어깨 ③ → 각각 keypointNumbers[left_shoulder]=2, [right_shoulder]=3 →
  해당 keypoint 위치에 번호 점 1개씩.
- 팔꿈치 ④ → keypointNumbers[left_hand]=4 (elbow 의 시각 proxy=손) → 손 위치에 번호 점 1개.

**영상 위 번호 점 = 총 4개** (중점 ① + 어깨 ② + 어깨 ③ + 손 ④). 텍스트 pill 0개.
그 외 스플릿 멤버 관절(hip×2, knee×2)은 빨강 강조 점(번호 없음)으로 보임 → 결함 부위 시각화 유지.

### (b) 여백 범례 4-entry 가로 나열 폭 추산 (iPhone 393×852)

전체화면은 회전 컨테이너 width=fsLong=**852**. fsTopBar paddingHorizontal≈16(spacing.cardPadding),
fsLegend flex:1 + paddingRight 12, 우측에 오버레이 토글(~90pt) + 닫기 버튼(36pt).
→ 범례 가용 폭 ≈ 852 − 2×16 − 90 − 36 − 12 ≈ **682pt**.

범례 폰트 = captionSmall(10) × FULLSCREEN_TEXT_SCALE(2.0×0.75=1.5) = **15pt**.
CJK 한 글자 ≈ 15pt, 원문자 ≈ 15pt, "−N" ≈ 8pt/글자로 근사한 entry 폭(번호+gap4+텍스트):

| entry | 텍스트(행동구/폴백) | 근사 폭 |
|------|------|------|
| ① | 다리 더 벌리기 −12 | ~140pt |
| ② | 팔 더 벌리기 −8 | ~110pt |
| ③ | 오른쪽 어깨(정은지 대비 각도) −8 (dedupe 폴백) | ~300pt |
| ④ | 팔꿈치 더 펴기 −6 | ~120pt |

합계 ≈ 140+110+300+120 + gap(3×8) ≈ **694pt** > 가용 682pt → **flexWrap 로 2번째 줄로 소폭 넘어감**
(③ 폴백이 최악 길이). 상단 검은 여백(fsTopBar)은 stack overlay 라 영상 높이를 깎지 않고 2줄까지
수용. 행동구가 정상 조립(짧은 문구)되면 4 entry 가 1줄(~510pt)에 들어간다. flexWrap 1줄 가로
나열 허용은 belle 승인 사항 — 폭 초과 시 자연 줄바꿈으로 graceful.

> 주: ③ 은 좌우 어깨가 같은 행동구("팔 더 벌리기")면 actionLabels dedupe 로 한쪽만 행동구를
> 얻고 나머지는 criterionLabelKo 폴백(긴 문자열)을 쓴다 — 위 추산은 그 최악을 가정.

### (c) 재생바 틱 병합 결과

buildDeductionTicks 는 windowMedianAngleDeltas.sourceFrameIndices.user 의 **median frame 1개**에,
번호가 부여된 record 전부의 번호를 오름차순 병합 → **틱 1개 { numbers:[1,2,3,4], frameIndex:m }**.
재생바에는 `sec = m × duration / userFrames` 위치에 "①②③④" 미니 라벨 + 세로 마크 1개.
탭하면 seekBoth(sec) 로 양쪽 영상 동기 seek. (현 계약상 window 공유 단일 시점 → 틱 1개.
record별 시점이 백엔드에 생기면 배열 구조 그대로 틱 분리 확장.)

---

## 2. 유사도 낮은 케이스 문장 시뮬레이션 (composeDimensionDiagnosisKo, 거짓 문장 0)

임계 `DIMENSION_DIAGNOSIS_HIGH_THRESHOLD = 90`. cleanPass = isCleanPass(감점 0).

| 케이스 | dim | value | 감점 | cleanPass | 출력 문장 | 거짓? |
|------|-----|------|-----|-----------|---------|------|
| A | angle | 72 | 2건 | false | "동작 흐름 자체가 기준과 차이가 있어요. 전체 동작을 기준 영상과 비교하며 따라가 보세요." | 아니오 (value<90 → "기준대로 타고" 거짓 문장 차단) |
| B | stability | 85 | 2건 | false | "버티는 구간에서 흔들림이 있어요. 자세 교정과 함께 버티는 힘을 길러 보세요." | 아니오 (value<90 → 흔들림 인정) |
| C | angle | 99 | 4건 | false | "동작 전체 흐름은 기준대로 타고 있어요 — 감점은 특정 순간의 자세에서 나왔어요. 위 항목만 교정하면 됩니다." | 아니오 (흐름 99 高 사실 + 감점은 순간 자세로 정직 분리 → "99인데 47점" 모순 해소) |
| D | angle | 100 | 0건 | true | "동작 흐름과 순간 자세 모두 기준과 일치해요." | 아니오 (감점 0 → 순간 자세도 일치 사실) |

핵심: value<90 분기가 낮은 지표에 "기준대로 타고 있어요" 거짓 문장을 원천 차단(T-r6v-02).
C 케이스가 belle 지적 모순("각도 유사도 99인데 낮은 종합")을 "흐름은 높다 + 감점은 순간 자세"
로 재프레임해 해소. 숫자(99/85 등)는 '자세히' 모달(DimensionDetailModal) 안에 그대로 남는다.

---

## 3. FaultZoomCompare 삭제로 소멸한 카피 + 사유

삭제한 `caption()` 이 조립하던 문구:
- **advisory tier**: "{부위} · 기준과 N° 차이 — 감점은 아니지만 확인해 보세요" / "{부위} · 기준과
  차이가 커요 — 감점은 아니에요" + "참고 · 감점 아님" 배지.
- **Mode3**: "{부위} · 지난 분석보다 좋아졌어요" / "지난 분석보다 아쉬워졌어요".
- **Mode1 deficit**: "{부위} · 기준보다 N° 부족해요".

**이식 안 한 사유**: DeductionDetailSheet 는 **감점 record(confirmed tier)에서만** 열린다
(내역 행/여백 범례/번호 점 = 전부 감점 tally 진입점). zoom 매칭도 tier='confirmed'(또는 tier
부재 legacy)만 허용하고 advisory 는 명시적으로 배제(planner_findings 7) — 감점 시트에 "감점
아님" 카드를 오매칭하면 자기모순이므로 advisory 카피는 이식 불요. Mode3 성장 방향 캡션은
'참고 지표'의 성장 델타 행(DimensionScoreRow delta)이 이미 담당하며, Mode3 확대사진 carousel
자체가 이번 스코프에서 제거됨(belle 승인 — 재생 중 최소 표시 원칙). 남는 Mode1 deficit 정보는
시트의 formatDeductionRecord.detailText("기준 대비 N° 차이 (허용 …)")가 더 정밀하게 승계한다.

**후속 백로그 후보**: Mode3(지난 분석 대비) 확대 비교 드릴다운 — 현재 시트는 감점 tally(mode1)
전용. Mode3 성장 확대사진이 필요하면 별도 진입점(성장 델타 행 탭)으로 신규 phase.

---

## Self-Check: PASSED

- 파일: app/src/components/DeductionDetailSheet.tsx FOUND, FaultZoomCompare.tsx REMOVED (의도적)
- 커밋: 3571087 / 5759c9e / 4dcfb10 FOUND (git log)
- typecheck GREEN, grep 게이트 전부 PASS
