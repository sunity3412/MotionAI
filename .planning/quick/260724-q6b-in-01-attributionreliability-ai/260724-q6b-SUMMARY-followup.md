# 260724-q6b Follow-up — 역립 저신뢰 확대비교 도달 가능화 + 시트 hedge

belle 결정: `attributionUnreliable`(역립/자기가림 저신뢰) 상태에서 확대비교(fault-zoom
crop comparison)가 "예상 부위"로 **도달 가능**해야 한다. 직전 IN-01 커밋이 진입점을
전부 억제해 도달 불가(그녀 의도와의 gap)였음. "AI 공부 중" 안내줄이 맥락을 주므로
사용자는 단정이 아닌 추정임을 이해한다.

## 변경 (presentation-only, 2 파일 1 커밋)

### 1. app/src/app/analysis/result.tsx — 도달 가능한 진입점 추가

- `ATTR_ZOOM_ESTIMATED_ENTRY_LABEL = '예상 부위 확대 비교 보기'` (module 상수).
- `estimatedAreaRecordIndex` memo 추가 — `estimatedAreaKeypoints` 의 record 경로와
  **동일 선택 로직**(angle_vs_reference prefix + KEYPOINT_FROM_ANGLE_KEY 매핑 +
  |points| 최대)으로 record INDEX(number | null) 산출. 진입점과 오버레이 주황 점이
  같은 관절을 가리킨다. windowMedian 폴백 경로는 대응 record 없어 null.
- 안내줄 JSX 직후, `attributionUnreliable && estimatedAreaRecordIndex != null &&
  (matchZoomForRecord(records[idx]) || zoomPending)` 일 때만 Pressable 카드 렌더 →
  onPress `setDetailRecordIndex(estimatedAreaRecordIndex)`. 매칭 크롭 없고 pending 도
  아니면 미렌더(빈 시트 금지 — 안내줄 + 정은지 비교는 그대로).
- 접근성: accessibilityRole="button", accessibilityLabel, hitSlop.
- 스타일 `estimatedZoomEntry*` (advisoryOrangeBg/advisoryOrange 톤, radius.card,
  spacing.cardPadding, typography.bodyMdBold — 토큰만, 신규 색 0).
- `<DeductionDetailSheet ... estimatedArea={attributionUnreliable} />` 는 직전 커밋에서
  이미 배선됨 → 이 진입점이 저신뢰 모드의 시트 opener 역할.

### 2. app/src/components/DeductionDetailSheet.tsx — estimatedArea 시 거짓 정밀도 hedge

- 제목: `estimatedArea` 시 `ESTIMATED_AREA_TITLE = '예상 부위 (참고)'` (관절 단정 금지).
  원문자 번호(①)도 억제 — 저신뢰 오버레이는 마커 번호를 표시하지 않아 대응 점이 없다.
  비-estimated 모드 무변경.
- 감점 수치: `estimatedArea` 시 metricRow(측정 detail + "−20점") 억제 →
  `ESTIMATED_AREA_POINTS_NOTE`('이 부위는 추정이라 관절별 감점 수치는 종합 점수로만
  반영돼요')로 대체. 특정 관절에 −X 귀속 불가하므로 관절별 수치 제거. 비-estimated
  모드 무변경.
- 크롭 이미지 비교 + "예상 부위" 배지는 그대로 유지(belle 가 원하는 가치).
- 스타일 `estimatedPointsNote` (bodySm/textMid, 토큰만).

## 불변식 준수

- 점수 값(overallScore/deductionBreakdown.final/records) byte-불변 — 표현 전용.
- `attributionUnreliable` false/부재(일반 케이스): 진입점 null + 시트 else 분기 →
  일반 분석 렌더 diff 0.
- 토큰만(src/theme), 하드코딩 색/여백 0, 이모지 0, 라이트 전용, Korean copy.
- `cd app && npm run typecheck` PASS (clean).

## 미확인

- 시뮬레이터 렌더/OTA 미실행 (오케스트레이터가 재검증). typecheck 만 통과.
