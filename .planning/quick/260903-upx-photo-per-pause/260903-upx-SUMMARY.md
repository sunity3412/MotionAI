---
phase: quick-260903-upx
plan: 01
status: complete
subsystem: analysis-fault-zoom-card-gates
tags: [fault-zoom, card-gates, photo-per-pause, belle-rule]
requires: [quick-260903-lpl, quick-260903-jxn, quick-260903-jka]
provides:
  - card_gates.decide_card — 게이트는 표시만 정한다(emit 항상 True, 눈 실제 불일치=학생 표시 생략, hold/pair/eye 상태)
  - fault_zoom.build_fault_zoom_comparisons — ref 대응 실패·양측 좌표 부재·배율 불일치에도 criterion 카드 방출, suppress_marks, userMarked
  - pipeline _run_gated_card_inherit — 무삭제·상한 해제·display_anchor 부재 측 표시 생략·1단계 카드 보존 병합·expected/emitted 불변식 로그
  - 계약 userMarked/holdState/pairState/eyeState (3중 미러) + 시트 "왼쪽 사진에는 … 표시를 넣지 않았어요"
affects: [pod-live-verification-6-motions, app-build-1.2.5(시트 한 줄)]
key-files:
  modified:
    - backend/shared/python/sunity_shared/analysis/card_gates.py
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_card_gates.py
    - backend/tests/test_fault_zoom.py
    - backend/tests/test_fault_zoom_record_moment.py
    - backend/tests/phase33/test_zoom_join_joint_exact.py
    - backend/tests/phase33/test_criterion_vertex_crop.py
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/app/analysis/result.tsx
key-decisions:
  - "belle 09-03 원문이 규칙: '확대사진을 그 멈추는 구간은 다 보여줘야 하고, 그걸 모든 동작에서 통과시켜야 한다' — 사진별 ○× 폐지, 기계 불변식(expected_units == emitted)으로 통과 판정"
  - "눈은 hold/pair 결과와 무관하게 판정 대상 관절에서 항상 묻는다(표시 결정 재료). 실제 불일치(observed≠claim 또는 arm↔leg)만 학생 표시 생략, 눈이 못 본 것(frame_missing/no_api_key/midrange/skip)은 표시 유지"
  - "display_anchor 부재 측은 그 측 표시만 생략(엉뚱한 rep12 좌표로 그리지 않는다는 원칙 유지) — 카드는 남는다"
  - "1단계 카드 보존: 게이트가 못 낸 record(freeze 없음·초 무효)는 최종 부착에서 유지(criterion/joint 키 병합)"
metrics:
  commits: [c22f99eb, 8187d66c, 808eaf19, 7016e8c3]
  pytest: "4600 passed / 0 failed / 20 skipped (기준선 4589 + 신규; 종전 미방출 assert 2건은 새 규칙으로 갱신)"
  app: "tsc 0 · node --test 219/0"
  executor: "gsd-executor 가 Task 1 뒤 API 500/529 로 두 번 끊김 → Task 2 검토·커밋과 Task 3·4 는 오케스트레이터가 직접"
completed: 2026-09-03
---

# quick-260903-upx: 멈춤 구간마다 확대 사진 1장 보장 Summary

**사진이 사라지던 6곳을 전부 "사진은 남기고 표시만 조정"으로 바꿨다.** 감점 record 마다 확정 카드 1장이 반드시 있고,
게이트(멈춤·짝·눈)는 학생 패널 표시를 그릴지만 정한다. 불변식은 서버 로그
`card_gates 대체 부착 완료 analysis_id=… expected_units=N emitted=N confirmed= stage1_keep= advisory=` 가 증언한다.

| # | 위치 | 종전 | 지금 |
|---|---|---|---|
| 1 | criterion_units_from_records 상한 4 (1단계·게이트) | 5번째 record 부터 카드 없음 | max_units = max(4, record 수) |
| 2 | fault_zoom D-12 ① ref 대응 실패 | criterion 카드 미방출 | 방출 + ref 전신 폴백 + refMatch='failed' |
| 3 | fault_zoom 양측 좌표 0 | skip | criterion 카드 방출, 표시 0 (userMarked/refMarked=false) |
| 3' | fault_zoom 배율 parity | criterion 카드 drop | 카드 유지 + 로그 |
| 4 | 게이트 hold/pair/eye FAIL | dropped | emitted + decide_card(표시 정책) + holdState/pairState/eyeState |
| 5 | display_anchor 부재 | 카드 미방출 | 그 측 표시만 생략(suppress_marks) |
| 6 | 최종 부착 | 1단계 카드 전부 대체 | 게이트 카드 + 1단계 보존(freeze 없는 record) + advisory |

## 검증

- pytest 4600/0(전체), 앱 tsc 0 · 219/0.
- 라이브(오케스트레이터, Pod sgl4muagt7xlb9): `scratchpad/verify_photo_per_pause.py` — 6동작 fixture(fault) 각각 expected_units vs
  confirmed 카드 수 기계 대조. 결과는 착수점/STATE 에 기록.

## 남은 것

- 시트 한 줄(userUnmarked)은 다음 앱 빌드(1.2.5)에 실린다. 서버 변경은 Pod 반입으로 즉시.
- 눈 호출이 record 마다 1회(종전엔 hold·pair 통과분만) — 비용은 카드 수 × ≤3회.
