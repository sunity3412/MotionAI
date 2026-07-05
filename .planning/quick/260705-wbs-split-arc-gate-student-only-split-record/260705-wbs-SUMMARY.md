---
phase: quick-260705-wbs
plan: 01
subsystem: backend/fault-zoom-display
tags: [fault-zoom, split-angle, display-only, gate, kip-up]
requires: [fault_zoom.split_angle_degs_from_records, fault_zoom._draw_side_leg_angle]
provides:
  - fault_zoom.has_split_angle_record
  - build_fault_zoom_comparisons.split_angle_present
  - _render_fault_zoom.split_angle_present
affects: [Mode1 fault-zoom PNG 렌더]
tech-stack:
  added: []
  patterns: [존재-판정과-수치-판정-분리, display-전용-게이트]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/tests/test_fault_zoom.py
    - backend/functions/pipeline/app.py
decisions:
  - "게이트 A: split_angle criterion 존재(records)로만 legs 사이각 진입 — 무릎/골반 오적용 제거"
  - "게이트 B: 학생(user) 측만 사이각, 정은지(ref) 측은 도립 pose 폭주로 미드로잉"
  - "존재 판정(has_split_angle_record)과 수치 판정(split_angle_degs_from_records) 분리 — kip-up reference_relative 는 수치 None 이나 사이각은 그림"
metrics:
  duration: ~15m
  completed: 2026-07-05
---

# Phase quick-260705-wbs Plan 01: 사이각 게이트 (split 확정 + 학생 측만) Summary

r6x 의 "다리 사이각(선 2 + 호 + 수치)" 렌더를 두 게이트로 좁혀, split 확정 결함의 학생 측에만 그리고 무릎/골반 legs 카드와 정은지 도립 pose 폭주에서 제거했다 — 채점 무접촉 display 전용.

## What Was Built

- **게이트 A (존재 판정):** `fault_zoom.has_split_angle_record(records)` 신규 순수 헬퍼. `criterion=='split_angle' AND unit=='deg'` record 존재 여부만 반환(None/비리스트/빈 graceful). 수치 추출(`split_angle_degs_from_records`, ipsf_absolute 만 값)과 **분리** — kip-up `reference_relative` 경로는 measuredValue 가 편차라 수치는 None 이지만 "다리 벌림" 사이각 자체는 의미 있어 선+호를 그려야 하므로 게이트만 연다.
- **게이트 A 배선:** `build_fault_zoom_comparisons(..., split_angle_present=False)` 키워드 파라미터 추가. legs 드로잉 블록에 `and split_angle_present` 조건 추가 — split record 없는 legs 카드(무릎 leg_extension / 골반 hip)는 블록 미진입, r6x 이전 circle 렌더로 완전 복귀(power-spin=leg_extension+hip, elbow-twist=hip+knee 오적용 회귀 방지).
- **게이트 B (학생 측만):** 기준(ref) 측 `_draw_side_leg_angle` 호출 블록 완전 제거, `r_deg`/`r_kind`/`r_box` 미사용 처리. 정은지 측은 kip-up 도립 pose 부정확으로 선이 폭주해 선 없는 crop 유지. `TODO(Phase 22)`: 자체학습 pose 개선 후 ref 측 재활성 주석 삽입.
- **pipeline 배선:** `_render_fault_zoom` 에 `split_angle_present` 전파 — confirmed 배치에만 전달, advisory("측정 초과·확인 권장")는 확정 스플릿 아니므로 `False` 명시. `_attach_fault_zoom_comparisons` 는 `has_split_angle_record(records)` 로 게이트 A 계산. Mode3 는 default `False` 유지(도립 pose 대칭 문제, 안전 생략).

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 (RED) | 게이트 A/B 테스트 계약 | 8618609 |
| 1 (GREEN) | fault_zoom 게이트 A/B 구현 | bf0a76f |
| 2 | pipeline records→split_angle_present 배선 | 830985c |

## Verification

- `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_fault_zoom.py tests/test_fault_zoom_relaxed_crop.py -q` → **50 passed**.
- `python3 -m py_compile functions/pipeline/app.py` → 통과.
- 배선 assert(`split_angle_present` 4회 이상 + `has_split_angle_record` 존재) → OK.

## Tests Added / Changed

- 신규 `test_legs_no_split_record_keeps_circle`: legs 카드 + split_angle_present 기본 False → 사이각 미드로잉 + circle 렌더 복귀(게이트 A 회귀 가드).
- 신규 `test_has_split_angle_record_pure`: reference_relative→True, ipsf_absolute→True, line-only/unit!='deg'/None/비리스트/빈→False.
- 기존 r6x 테스트 5개를 게이트 계약으로 갱신(split_angle_present=True 추가, leg_calls 2→1 = 학생 측만).

## Deviations from Plan

None — 계획대로 실행. (정리성 개선 1건: 게이트 B 로 미사용된 `r_kind`/`r_box` 를 `_r_kind`/`_r_box` 로 언더스코어 처리 + 설명 주석. 채점/동작 무영향.)

## Known Stubs

None. display 게이트 로직은 완전히 배선됨.

## PENDING (실기기 검증)

- **실 PNG 재확인은 pod 재분석 PENDING.** 코드/유닛 게이트가 계약을 못 박았으나, 실제 렌더 검증(kip-up 학생 측만 사이각 표시 / power-spin·elbow-twist 사이각 없음 / 정은지 측 선 없는 crop)은 pod 재분석 후 belle 육안 확인 필요.

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/fault_zoom.py (has_split_angle_record + split_angle_present)
- FOUND: backend/functions/pipeline/app.py (split_angle_present 배선)
- FOUND commits: 8618609, bf0a76f, 830985c
