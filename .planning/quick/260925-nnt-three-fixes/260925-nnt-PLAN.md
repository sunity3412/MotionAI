---
quick_id: 260925-nnt
slug: three-fixes
date: 2026-09-25
status: executing
---

# 세 칸 수리 — belle "그럼 세 칸 고쳐봐" (봉인 시험지 1회 0/2 뒤)

세 칸 = 260925-mvh SUMMARY 의 진단 후보 3건. 규율: 영상별 조절 0 · 새 문턱은 양쪽 실측 여유와 둔감성 테스트로만 ·
정타 5편 침묵 확인 · 문장은 belle ○× 전까지 초안.

## Task 1 — Gemini severity none 경로 (climb)
`_collect_vision_fault_context`: rank-median severity 가 none 이어도 support 게이트(K-of-N) 통과 지목이 있으면
no_fault ctx 에 supported/root_causes 를 싣는다. 감점은 종전대로 기하(tally · window 측정 · tol). 테스트 2.

## Task 2 — 높이 카드 일반화 (power-spin)
`hold_height.body_low_grip_low`(엉덩이 1/3 전부 낮음 + 그립 손 GRIP_LOW_BODY_LENGTH 넘게 낮음) · `grip_side_majority` ·
`_measured_phrase_variants` 가 몸 전체 패턴은 어느 record 든 승인 문장이 있으면 호스트 · 동그라미 = 그립 손 + 엉덩이 중점 ·
phrasebook `ref-power-spin.leg_extension.body_low_grip_low` 초안 3줄. 테스트 15.

## Task 3 — 벌림 게이트 (power-spin) → 열지 않는다
오프라인 실측: 2D peak split 이 기준 tuck(r43)에서 180°, kip-up 기준도 180°, pdshape 173.7° — 자가 포화. power-spin 실수 165.3 →
부족 14.7° < tol 20 이라 열어도 침묵. 자가 고장이라 게이트를 열면 위양성/침묵만 남는다. belle 에게 "무릎 덜 펴짐 = 벌림?" ○× 질문으로 대체.

## 검증
오프라인 게이트(저장 doc 10편) → 전체 pytest → Pod E2E 10편(앱 경로) → 카드·멈춤 프레임 판정지 → Pod 종료.
