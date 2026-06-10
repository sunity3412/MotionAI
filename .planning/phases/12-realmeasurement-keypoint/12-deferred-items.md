# Phase 12 Deferred Items

Phase 12 (realmeasurement-keypoint) Wave 2 (Plan 12-03) 실증 follow-up + 후속 결정 보류 항목.

T4 belle iOS UAT 결과로 일부 항목이 추가/수정됨. 본 파일은 Wave 2 commit 시점의
스냅샷이며 T4 후 추가 정보가 채워짐.

---

## 1. A2 — mode1 reference 측 floating angle label

- **현재 상태**: Wave 2 사용자 측 KeypointOverlay 만 floating "N°" 라벨 노출.
  mode1 reference (정은지) 측은 brand 컬러 강조 (점/본) 만 + floating label X.
- **이유**: 사용자 측과 reference 측이 동시에 라벨을 띄우면 split 화면 시각
  중복 + 강조 의도 모호. belle UAT 후 reference 측 라벨 추가 여부 결정.
- **결정 시점**: T4 belle UAT.
- **결정 input 필요**: "reference 측 라벨 보고 싶다 / 사용자 측만 충분".

## 2. Low-reliability KeypointOverlay 시각 treatment

- **현재 상태**: Wave 2 MVP scope OUT. 저신뢰 frame 의 keypoint 가 일반 frame
  과 동일한 시각 (Circle stroke + bone Line).
- **이유**: dashed stroke / opacity 0.5 등 시각 복잡도 증가 가능성 + 결과
  화면 영역 5 ⚠ amber badge + 영역 6 "추정 N°" 으로 이미 occlusion 표기.
- **결정 시점**: Phase 12.5 또는 학원 파일럿 후.
- **decision input 필요**: 사용자가 KeypointOverlay 자체에서 저신뢰 frame
  구분이 필요한지.

## 3. KEYPOINT_DELTA_HIGHLIGHT_DEG sensitivity

- **현재 값**: 10.0° (Wave 1 lock, D-12-C3).
- **검증 데이터**: T4 belle iOS UAT 가 정은지 vs 사용자 분석 1건 실측 →
  delta ≥ 10° 발생 joint 갯수 박제.
- **조정 후보**: 너무 빈번 (대부분 joint 강조) → 15°. 너무 드물 (1-2 개) → 7°.
- **결정 시점**: T4 belle UAT.

## 4. 토글 ON/OFF 사용자 선호도

- **현재 상태**: 디폴트 ON + AsyncStorage 키 `'@sunity:keypoint_overlay_enabled'`.
  Pitfall 6 우회로 OFF 사용자는 진입 시 잠시 ON 깜빡임 수용.
- **검증 데이터**: 학원 파일럿 + belle UAT 동안 사용자가 토글을 끄는 빈도.
- **결정 시점**: 학원 파일럿 후. 끄는 빈도 높으면 디폴트 OFF 로 전환 검토.

## 5. True frame-level delta + DTW alignment

- **현재 상태**: Wave 2 MVP = 영상 전체 대표 편차 (JointScore 평균 current/
  target). delta 강조도 일정 (frame 별 변하지 않음).
- **이유**: frame-level delta 는 DTW alignment + 시간 normalize 필요 →
  복잡도 + 정확도 trade-off. MVP 는 "대표" 편차로 충분.
- **결정 시점**: v2 (Phase 13+).

## 6. Phase 9 카드 vs 차원 카드 순서

- **현재 상태**: Wave 1 layout (영역 3 = Phase 9 finding, 영역 5 = 세부 점수).
- **검증 시점**: T4 belle UAT.
- **결정 input 필요**: 사용자 흐름상 "실패 원인" 이 "세부 점수" 보다 먼저
  나오는 것이 자연스러운지.

## 7. Frontend test infra

- **현재 상태**: app/ 에 test runner 미설치 (typecheck 만 gate).
- **결정 시점**: Phase 15 통합 sweep 시점.
- **결정 input 필요**: KeypointOverlay / ForcePatternCard / VideoCompare 의
  snapshot 또는 unit test 필요성. RN 환경에서는 Jest + React Native Testing
  Library 가 표준.

## 8. Phase 12.5 차원 카드 ⚠ badge 위치 미세 조정

- **현재 상태**: Wave 2 영역 5 sectionHeader row 우측 ⚠ amber badge.
- **검증 시점**: T4 belle UAT.
- **결정 input 필요**: 카드 안 우상단 (각 차원별) vs 섹션 헤더 (현재).
  현재 = 1개 badge / 차원별 = 3개 badge. 차원별 noisy 가능성.

## 9. 성장 차트 위치 (D-12-A1 #6)

- **현재 상태**: Wave 1 layout 미박제.
- **결정 시점**: T4 belle UAT.
- **결정 input 필요**: 차원 카드 ↔ 각도 상세 사이로 이동 가능성.

## 10. Pitfall 1-9 실 발현 박제 (T4 결과)

T4 belle iOS UAT 결과로 채워짐. 미실행.

| Pitfall | 발현 / WORKAROUND / 미발현 | 비고 |
| ------- | --------------------------- | ---- |
| Pitfall 1 (iOS seek bug) | T4 미실행 | useEvent.currentTime 사용 시 정합 검증 |
| Pitfall 2 (60fps jank) | T4 미실행 | iOS Instruments 또는 belle 직관 |
| Pitfall 6 (토글 깜빡임) | T4 미실행 | useState(true) initial 박제 정합 |
| Pitfall 7 (Firestore 1 MiB) | T4 미실행 | result.keypointReport doc size 실측 |
| Pitfall 9 (timeline vs overlay 동기) | T4 미실행 | 250ms 폴링 vs ~30ms useEvent drift |
