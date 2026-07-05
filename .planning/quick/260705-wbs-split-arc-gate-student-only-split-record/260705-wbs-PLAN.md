---
phase: quick-260705-wbs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/tests/test_fault_zoom.py
  - backend/functions/pipeline/app.py
autonomous: true
requirements: [WBS-GATE-A, WBS-GATE-B, WBS-TESTS]

must_haves:
  truths:
    - "스플릿 아닌 legs 결함 카드(무릎 leg_extension / 골반 hip)는 사이각 선·호를 그리지 않고 r6x 이전 circle/relaxed/full 렌더로 복귀한다"
    - "split_angle criterion 이 records 에 있는 legs 카드만 사이각을 그린다"
    - "사이각은 학생(user) 측 crop 에만 그려지고 기준(정은지) 측 crop 은 선 없이 유지된다"
    - "cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_fault_zoom.py tests/test_fault_zoom_relaxed_crop.py -q 가 GREEN"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "has_split_angle_record 게이트 + split_angle_present 파라미터 + user-측 전용 사이각 드로잉"
      contains: "has_split_angle_record"
    - path: "backend/functions/pipeline/app.py"
      provides: "records → split_angle_present 계산 후 _render_fault_zoom 로 전달"
      contains: "split_angle_present"
  key_links:
    - from: "backend/functions/pipeline/app.py::_attach_fault_zoom_comparisons"
      to: "fault_zoom.has_split_angle_record"
      via: "deductionBreakdown.records 로 split 존재 판정"
      pattern: "has_split_angle_record"
    - from: "fault_zoom.build_fault_zoom_comparisons"
      to: "_draw_side_leg_angle"
      via: "unit.region=='legs' AND split_angle_present AND u_kind=='valid' (user 측만)"
      pattern: "split_angle_present"
---

<objective>
r6x 가 추가한 "다리 사이각(선 2 + 호 + 수치)" 렌더가 region=='legs' 카드에 무조건
그려지는 오적용을 두 게이트로 좁힌다. legs 카드는 스플릿뿐 아니라 무릎(leg_extension)/
골반(hip) 결함으로도 뜨는데 (2026-07-05 pod 전동작 검증: power-spin=leg_extension+hip,
elbow-twist=hip+knee 에 사이각 오적용), 사이각은 "다리 벌림"의 시각 언어라 스플릿 아닌
결함에 그리면 오독을 낳는다.

- 게이트 A: 사이각은 **split_angle criterion 이 실제 records 에 있을 때만** 그린다.
  스플릿 아닌 legs 카드는 r6x 이전 circle/relaxed/full 렌더로 완전 복귀.
- 게이트 B: split_angle 카드라도 **학생(user) 측만** 그린다. 정은지 측은 kip-up 도립
  pose 부정확으로 선이 폭주(pose 한계) — 기존 crop 렌더 유지(비교 사진은 나오되 선만
  없음). Phase 22 자체학습 pose 개선 후 ref 측 재활성.

Purpose: 사이각을 스플릿 확정 결함의 학생 측으로 한정해 오적용·폭주를 제거 (belle 승인
2026-07-05). 채점 무접촉 — display 렌더 전용.
Output: fault_zoom 게이트 + pipeline 배선 + 유닛 테스트 GREEN.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@backend/shared/python/sunity_shared/analysis/fault_zoom.py
@backend/tests/test_fault_zoom.py
@backend/tests/test_fault_zoom_relaxed_crop.py
@backend/functions/pipeline/app.py
@CLAUDE.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: fault_zoom 사이각 게이트 A/B + 유닛 테스트</name>
  <files>backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom.py</files>
  <behavior>
    - has_split_angle_record(records): records 에 criterion=='split_angle' AND unit=='deg' 하나라도 있으면 True.
      · kip-up 경로 reference_relative split record → True (수치는 None 이어도 사이각 의미 있음)
      · ipsf_absolute split record → True
      · line-only record / split 없음 → False
      · None / 비리스트 / 빈 리스트 → False (graceful)
    - build_fault_zoom_comparisons(split_angle_present=False) 기본값: legs 카드라도 사이각 미드로잉, 기존 circle 렌더 유지
    - split_angle_present=True + legs valid 카드: 학생(user) 측만 _draw_side_leg_angle 1회, 기준(ref) 측 미드로잉
    - split_angle_present=True + split_angle_degs=(130,170): user 측에 130 만 전달 (ref 측 호출 없음)
    - split_angle_present=True + split_angle_degs=None (kip-up): user 측 angle_deg=None 로 선+호만
    - non-legs 카드(arms 등): split_angle_present 무관하게 사이각 0회, 기존 circle=True 규칙 유지
  </behavior>
  <action>
    fault_zoom.py:
    1. 신규 순수 헬퍼 has_split_angle_record(records) -> bool 추가 (split_angle_degs_from_records 근처).
       criterion=='split_angle' AND unit=='deg' 인 record 존재 여부만 반환. None/비리스트 graceful.
       한국어 why 주석: 수치(split_angle_degs_from_records)와 분리하는 이유 — kip-up reference_relative
       는 measuredValue 가 편차라 수치는 생략(None)하지만 사이각 자체는 의미 있어 선+호를 그려야 함
       (2026-07-05 전동작 검증).
    2. build_fault_zoom_comparisons 시그니처에 keyword-only 파라미터 split_angle_present: bool = False 추가
       (기존 split_angle_degs 뒤). docstring 에 게이트 A/B 취지 1문단.
    3. legs 드로잉 블록(현 864~871행) 게이트 수정:
       · 게이트 A — 조건에 `and split_angle_present` 추가. split 아닌 legs 카드는 이 블록 미진입 → 기존
         _mark circle 렌더로 폴백.
       · 게이트 B — 기준(ref) 측 _draw_side_leg_angle 호출 블록 완전 제거. r_deg 변수 삭제. user 측만 유지.
       · 한국어 why 주석: power-spin=leg_extension+hip / elbow-twist=hip+knee 오적용 + kip-up 정은지
         도립 pose 폭주 인용. "TODO(Phase 22): 자체학습 pose 개선 후 ref 측 사이각 재활성" 1줄.
       · u_drew_legs 분기(원 생략 vs 기존 circle)는 그대로 — user 가 그렸으면 circle=False, 아니면 기존.
    test_fault_zoom.py (r6x 섹션):
    4. 기존 r6x 테스트를 게이트 계약으로 수정 — 사이각을 기대하는 build 호출에 split_angle_present=True 인자 추가:
       · test_legs_valid_side_draws_angle: leg_calls == 2 → == 1 (user 측만), 주석 게이트 B 반영.
         mark_calls == [(False, None)] 유지(user 원 생략, ref 는 _mark 없음).
       · test_legs_split_angle_numbers_passed: [c[3] ...] == [130.0, 170.0] → == [130.0] (user 만).
       · test_legs_split_angle_none_omits_numbers: [None, None] → [None].
       · test_legs_low_conf_ref_side_no_angle / test_legs_conf_absent_ref_side_no_angle:
         split_angle_present=True 추가, len(leg_calls) == 1 유지, 주석을 "게이트 B: ref 측 무조건 미드로잉" 로.
    5. 신규 테스트 2개 추가:
       · test_legs_no_split_record_keeps_circle: _LEGS_XY legs 카드 + split_angle_present 미지정(기본 False)
         → leg_calls == [] AND mark_calls 첫 원소 circle=True (스플릿 아닌 legs = 기존 circle 복귀 가드).
         power-spin/elbow 오적용 회귀 방지 근거 주석.
       · test_has_split_angle_record_pure: reference_relative split → True, ipsf_absolute split → True,
         line-only → False, unit!='deg' → False, None/'nope'/[] → False.
    이모지 금지, 한국어 why 주석, 근거 인용(2026-07-05 belle pod 전동작 검증). 채점/veto/게이트 경로 무접촉.
  </action>
  <verify>
    <automated>cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_fault_zoom.py tests/test_fault_zoom_relaxed_crop.py -q</automated>
  </verify>
  <done>두 테스트 파일 GREEN. legs 카드는 split_angle_present=True 일 때만 user 측 사이각을 그리고, split 없는 legs 카드는 circle 렌더로 복귀한다.</done>
</task>

<task type="auto">
  <name>Task 2: pipeline 배선 — records → split_angle_present 전달</name>
  <files>backend/functions/pipeline/app.py</files>
  <action>
    1. _render_fault_zoom 시그니처에 keyword-only 파라미터 split_angle_present: bool = False 추가
       (기존 split_angle_degs 뒤). docstring 1줄 갱신.
       · confirmed build_fault_zoom_comparisons 호출(현 2571~2585행)에 split_angle_present=split_angle_present 전달.
       · advisory build 호출(현 2592~2606행)에는 split_angle_present=False 명시 전달 — advisory("측정 초과·
         확인 권장") 카드는 확정 스플릿 결함이 아니므로 사이각을 그리지 않는다(한국어 why 주석).
    2. _attach_fault_zoom_comparisons(Mode1): split_degs 계산 직후 split_present =
       _fz.has_split_angle_record((result.get("deductionBreakdown") or {}).get("records")) 추가하고
       _render_fault_zoom(...) 호출에 split_angle_present=split_present 전달.
       한국어 why 주석: 게이트 A — split criterion 존재 시에만 legs 사이각. 수치(split_degs)와 존재
       판정(split_present)을 분리(kip-up reference_relative 는 수치 None 이나 사이각은 그림).
    3. _attach_mode3_fault_zoom(Mode3)는 default split_angle_present=False 유지(무접촉) — Mode3 는 기준이
       사용자 지난 영상이라 도립 pose 대칭 문제, 사이각 안전 생략. 코드 변경 없음(주석만 필요 시 1줄).
    이모지 금지, 한국어 why 주석. 채점 무접촉 — display 배선 전용.
  </action>
  <verify>
    <automated>cd backend && python3 -m py_compile functions/pipeline/app.py && PYTHONPATH=shared/python:. python3 -c "import ast,sys; s=open('functions/pipeline/app.py').read(); assert s.count('split_angle_present')>=4, 'wiring missing'; assert 'has_split_angle_record' in s; print('OK')"</automated>
  </verify>
  <done>_attach_fault_zoom_comparisons 가 records 로 split_angle_present 를 계산해 confirmed 배치에만 전달하고, advisory/Mode3 는 False. py_compile 통과.</done>
</task>

</tasks>

<verification>
- cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_fault_zoom.py tests/test_fault_zoom_relaxed_crop.py -q → GREEN
- cd backend && python3 -m py_compile functions/pipeline/app.py → 통과
- 실 PNG 재확인(kip-up 학생 측만 사이각 / power-spin·elbow-twist 사이각 없음)은 pod 재분석 PENDING — 코드/유닛 게이트가 계약을 못 박음.
</verification>

<success_criteria>
- 스플릿 아닌 legs 카드(무릎/골반)는 사이각 코드 미진입, 기존 circle 렌더 복귀
- split_angle criterion 존재 legs 카드는 학생 측만 사이각, 정은지 측은 선 없는 crop 유지
- 기존 r6x/relaxed_crop 테스트 계약 정합, 신규 게이트 테스트 2개 추가, 전체 GREEN
- 채점/veto/게이트 경로 무접촉(display 전용), 이모지 없음, 한국어 why 주석 + 근거 인용, Phase 22 TODO 주석
</success_criteria>

<output>
Create `.planning/quick/260705-wbs-split-arc-gate-student-only-split-record/260705-wbs-SUMMARY.md` when done
</output>
