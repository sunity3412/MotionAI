# kip-up fault 100=100 진단 (2026-08-31, 오케스트레이터 실측)

## 관측 체인 (전부 이 세션 직접 실행)

1. 스윕 doc (fault ibpoKd1F…/9539d194…): deductionBreakdown records=0,
   visionVeto={status: not_applicable, alignment: {distance 27.0, adoption window_union,
   localPathCount 5, visibility 0.806}}. 표시 델타: left_shoulder 23.0°.
2. adoption 로직 실측(vision_veto.assess_alignment_confidence): distance 27>T2(25) →
   global_ok=False, 로컬 견고 → **window_union** (bail 아님 — Gemini 호출됨).
3. **로컬 재현** (assess_fault_context_video, 킵업 잘못된예시 vs s3 ref-kip-up.mp4):
   status=candidate_verdict, supported_differences=1 —
   split_angle, student 145° vs reference 165° → 편차 20°, severity minor.
   → over = max(0, 20 − tol 20) = **0** → 감점 record 0 → not_applicable. 재현 완결.
4. **대조** (잘된예시 vs 같은 기준): supported_differences=**0**, severity none.
   vision 범주 판정은 오늘도 완벽 변별.
5. **6월 원장** (backend/evals/phase25/baseline/phase25_breakdowns.json kip-up.fault):
   split_angle measuredValue 50.0 / deviation 30.0 → -20 (source=vision) +
   angle_vs_reference__left_shoulder 40.15 → -20 (source=geometry).
   같은 영상의 vision 크기 추정이 50°→20°로 압축(모델 세대 변경 계열),
   geometry 쪽도 엔진 교체 후 편차 축소로 침묵.
6. 기하 split 재확인(features.split_angle_series, 저장 joints3d): fault·correct 둘 다
   max 180.0 포화(스퓨리어스) — 6월 "키포인트 포화로 기하 측정 불가" 소견 유지.
   vision 이 여전히 유일한 측정기.

## 수리 방향 (아래 quick 태스크의 스펙)

**vision-sourced reference_relative 편차에는 tol 재적용 금지** (over = dev, tol 우회).
- 근거: tol=20 은 "항상 재는" 기하 측정기의 무차별 노이즈 마진. vision 은 결함
  발견 시에만 값을 내고 support 게이트가 노이즈 게이트 역할을 이미 함(대조 실증 0건).
  cap 이 크기 드리프트(50↔20)를 흡수 — 모델 세대 변경에 점수 안정.
- geometry-sourced 편차의 tol 은 불변 (전 관절 무차별 측정이라 마진 필요).
- 새 튜닝 상수 0, severity→점수 밴드 재도입 금지(ND-01), 동작명 분기 0.

## 사전 박제 예측

- 수리 후 kip-up fault: split_angle record 발생(over 20 × slope → cap -20) → overall 80.
- kip-up correct: supported_differences 0 → 무변화 100.
- 방향 복원: fault 80 < correct 100.
