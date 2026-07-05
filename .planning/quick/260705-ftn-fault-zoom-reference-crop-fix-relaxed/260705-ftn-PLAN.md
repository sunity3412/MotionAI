---
phase: quick-260705-ftn-fault-zoom-reference-crop-fix-relaxed
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_fault_zoom_relaxed_crop.py
  - backend/tests/test_fault_zoom.py
autonomous: true
requirements: [QUICK-260705-FTN]

must_haves:
  truths:
    - "relaxed crop 에서 밀집/단일 저신뢰 좌표는 floor(_CROP_FRAC 줌 수준) 크기 부위 crop 이 된다 — 전폭 정사각(전신처럼 보이는) 크기 폭주 없음"
    - "relaxed crop 에서 흩어진 좌표는 bbox 파생분에만 _RELAXED_MARGIN 이 적용된 확대 crop 이 된다"
    - "Mode1 fault-zoom 표시 프레임은 sourceFrameIndices window 안에서 멤버 관절 평균 confidence 최대 프레임으로 user/ref 각각 독립 선택된다 (confidence 부재 legacy doc 은 기존 median 동작 유지)"
    - "채점 산출(deductionBreakdown/visionVeto) diff 0 — 변경은 display 전용 경로에 한정"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "relaxed crop 크기 fix (_side_crop._box_for) + 순수 표시 프레임 선택 helper (select_confident_frame)"
    - path: "backend/functions/pipeline/app.py"
      provides: "_attach_fault_zoom_comparisons 가 median 대신 helper 호출"
    - path: "backend/tests/test_fault_zoom_relaxed_crop.py"
      provides: "relaxed 크기 상한(전폭 미도달) 회귀 테스트 + 기존 widen 테스트의 새 계약 반영"
    - path: "backend/tests/test_fault_zoom.py"
      provides: "select_confident_frame 순수 helper 테스트"
  key_links:
    - from: "backend/functions/pipeline/app.py"
      to: "sunity_shared.analysis.fault_zoom.select_confident_frame"
      via: "_attach_fault_zoom_comparisons 의 sourceFrameIndices 처리 블록"
      pattern: "select_confident_frame"
    - from: "backend/shared/python/sunity_shared/analysis/fault_zoom.py::_side_crop"
      to: "_crop_box"
      via: "_box_for — margin 을 bbox 파생분에만 곱한 side 전달"
      pattern: "_BBOX_MARGIN \\* margin|margin \\* _BBOX_MARGIN"
---

<objective>
fault-zoom reference crop 정합 fix — belle 실기기 (2026-07-05, kip-up fault 76점): 확대 비교 카드 2장 모두 reference("정은지 선수") 측이 전신 와이드샷으로 나와 "비교 사진이랑 전혀 안맞아". pod 실측 재현으로 원인 2개 확정 (ref-kip-up, ref frame 37 = kp_idx 74, frame 360x640):

1. relaxed crop 크기 버그: `_side_crop._box_for(pts, _RELAXED_MARGIN)` 이 floor(min(h,w)*_CROP_FRAC)에도 margin 을 곱해 side 가 프레임 너비 360 에 클램프 — 모든 relaxed crop 이 전폭 정사각 = 전신처럼 보임. "부위-중심 완화 crop 으로 카드별 차별화" 의도(Phase 25-03)가 크기 폭주로 무력화.
2. 표시 프레임 선택: vision 측정 window sourceFrameIndices reference=[35..39] 의 median(37)을 맹목 사용 — 하필 keypoint 붕괴 구간. 동일 영상 다른 시각(30/59/80)에선 legs 4점 전부 valid — window 내 신뢰도 최대 프레임을 고르면 측정-표시 정합을 window 안에서 유지하면서 저신뢰 프레임 회피 가능.

Purpose: 확대 비교 카드의 reference 측이 실제 부위 crop 을 보여주도록 복원 (display 전용, 채점 무접촉).
Output: fault_zoom.py fix + 순수 helper, pipeline 배선, 회귀 테스트 GREEN.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/shared/python/sunity_shared/analysis/fault_zoom.py
@backend/functions/pipeline/app.py (lines 2614-2706 — _attach_fault_zoom_comparisons)
@backend/tests/test_fault_zoom_relaxed_crop.py
@backend/tests/test_fault_zoom.py
@CLAUDE.md
</context>

<interface_contract>
신설 순수 helper (fault_zoom.py, Task 2에서 정의 — pipeline 은 이것만 호출):

- `select_confident_frame(report: dict, candidates: list, members: list[str] | tuple[str, ...], frames_fps: float = 9.0) -> int | None`
  - candidates: 9fps frames 인덱스 공간 (sourceFrameIndices 의 user 또는 reference 리스트). 빈 리스트/전원 비정수 → None (호출측 기존 폴백 = override 없음).
  - 각 candidate 를 rep 인덱스로 변환: round(idx / frames_fps * report fps), [0, report frames-1] clamp — build_fault_zoom_comparisons 내부 `_to_rep_idx` closure 와 동일 공식 (모듈 레벨 함수로 추출해 양쪽이 공유, 중복 공식 금지).
  - 점수 = 멤버 관절들의 `_kp_conf` 평균 (None 인 관절 제외). 전 candidate 전 멤버 conf None (legacy/confidence 부재 report) → 기존 동작 폴백: sorted(candidates)[len//2] median 반환 (하위호환 — diff 0).
  - 결정론 tie-break: 점수 최대, 동점이면 sorted(candidates) 오름차순에서 먼저 오는 인덱스.
  - 반환은 9fps frames 인덱스 (build_fault_zoom_comparisons 의 user_frame_idx/ref_frame_idx 로 그대로 전달 가능).
</interface_contract>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: relaxed crop 크기 fix — margin 을 bbox 파생분에만 적용</name>
  <files>backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom_relaxed_crop.py</files>
  <behavior>
    - 신규 테스트 (relaxed 크기 상한, 전폭 미도달): 400px 정방 gradient 프레임에서 밀집 2점 relaxed pts (예: (0.49,0.5),(0.51,0.5) — bbox 8px*_BBOX_MARGIN*_RELAXED_MARGIN=29 &lt; floor 168) 의 relaxed crop 이 같은 중심 단일 valid 점 crop 과 (0, _OUT//2) 에지 픽셀 동일 — side == floor 증명 (구 코드는 floor*2.0=336 으로 폭주, 2026-07-05 pod 재현: relaxed side=360 클램프). 기존 gradient 픽셀 검증 기법(_grad_frames + getpixel) 재사용.
    - 기존 `test_relaxed_margin_widens_crop_vs_valid` 재작성: 단일점 relaxed(=버그 크기 인코딩, 구 계약 변=336)를 흩어진 2점 케이스로 교체 — 예: (0.4,0.5),(0.6,0.5) → bbox 80px, valid 변 = max(168, 80*1.8=144)=168 / relaxed 변 = max(168, 80*1.8*2.0=288)=288 → relaxed 에지 픽셀 red 가 valid 보다 20 이상 작음(더 넓은 컨텍스트). 인라인 산술 주석도 새 수치로 갱신. 이 테스트는 수정 대상 버그의 크기 동작을 그대로 assert 하고 있어 재작성이 필수 — scope 축소 아님.
    - 나머지 기존 테스트 (three_tier_kinds, centers_follow, cards_differ_by_joint, low_conf_finite_is_crop 등) 는 무수정 GREEN — relaxed 중심 추적/kind 강하/앵커 규칙은 계약 불변.
  </behavior>
  <action>
    fault_zoom.py `_side_crop` 내부 `_box_for(pts, margin)` 수정: 현재는 side = max(floor, bbox_side*_BBOX_MARGIN) 산출 후 마지막에 side*margin 을 _crop_box 로 전달 — 이것이 floor 에도 margin 을 곱하는 버그. 변경: floor_side = round(min(h,w)*_CROP_FRAC) 는 margin 미적용 그대로 두고, len(pts)>1 일 때만 side = max(floor_side, round(bbox_side*_BBOX_MARGIN*margin)) 으로 margin 을 bbox 파생분에만 곱한다. _crop_box 에는 최종 side 를 그대로 전달 (기존 clamp/shift 로직 무접촉). valid 경로는 margin=1.0 이라 산출값 byte-동일 (max(floor, bbox*1.8*1.0) == 기존 max(floor, bbox*1.8)*1.0) — valid 경로 회귀 0. 신규 튜닝 상수 도입 금지 — 기존 _CROP_FRAC/_BBOX_MARGIN/_RELAXED_MARGIN 재사용 (constraints).

    docstring/주석 동기화 (한국어 why): `_side_crop` docstring (2)항 "변 = 기존 공식 x _RELAXED_MARGIN" 을 "변 = max(floor, bbox*_BBOX_MARGIN*_RELAXED_MARGIN) — margin 은 bbox 파생분에만, floor(기본 줌)는 그대로" 로 갱신하고, _RELAXED_MARGIN 상수 주석(line 58-62)에 근거 인용 추가: "2026-07-05 pod 재현 — floor 에도 margin 을 곱하면 side 가 프레임 전폭(360)에 클램프돼 모든 relaxed crop 이 전신처럼 보임 (belle 실기기)". 이모지 금지.

    테스트는 behavior 블록대로 test_fault_zoom_relaxed_crop.py 에 작성/재작성 (RED 먼저 확인 후 fix).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_fault_zoom_relaxed_crop.py tests/test_fault_zoom.py -q</automated>
  </verify>
  <done>relaxed 크기 상한 테스트 + 재작성된 widen 테스트 포함 전체 fault_zoom 테스트 GREEN. 밀집/단일 relaxed pts → floor 크기 부위 crop, 흩어진 pts → bbox 기반 확대. valid 경로 산출 무변경.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: window 내 confidence 최대 표시 프레임 선택 — 순수 helper + pipeline 배선</name>
  <files>backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/functions/pipeline/app.py, backend/tests/test_fault_zoom.py</files>
  <behavior>
    - Test 1 (confidence 선택): fps 9.0 / 9프레임 합성 report, 관절 left_knee 의 프레임별 confidence 를 candidates [3,4,5] 중 median(4)=0.1, 3=0.9, 5=0.5 로 세팅 → select_confident_frame(report, [3,4,5], ["left_knee"]) == 3 (median 이 아닌 conf 최대).
    - Test 2 (legacy 폴백): confidence 키 없는 report → sorted(candidates) median 반환 (기존 pipeline 동작과 동일 — 하위호환 diff 0).
    - Test 3 (edge): 빈 candidates → None. 멤버 2개 중 1개 conf None 이면 나머지로 평균.
  </behavior>
  <action>
    (1) fault_zoom.py: interface_contract 의 `select_confident_frame` 을 순수 함수로 신설 (numpy/_kp_conf 외 의존 0 — S3/네트워크 금지, 모듈 기존 원칙). build_fault_zoom_comparisons 내부 `_to_rep_idx` closure 를 모듈 레벨 `_to_rep_idx(idx, frames_fps, rep_fps, rep_frames)` 로 추출해 build_fault_zoom_comparisons 와 helper 양쪽이 같은 변환 공식을 공유 (build_fault_zoom_comparisons 산출은 무변경 — 순수 리팩터). docstring 에 why 기록: "window median 프레임이 keypoint 붕괴 구간이면 relaxed/full 강하로 카드가 망가짐 (2026-07-05 pod 재현: ref-kip-up frame 37 전 keypoint &lt;0.5, 동일 영상 30/59/80 에선 legs 4점 valid) — 측정-표시 정합은 window 안에서 유지하면서 신뢰 프레임을 고른다. 표시 전용, 채점/veto/게이트 무접촉".

    (2) pipeline app.py `_attach_fault_zoom_comparisons` (line 2653-2662): sfi 의 u_list/r_list median 계산을 helper 호출로 교체 — user_frame_idx = fault_zoom.select_confident_frame(user_report, u_list, fault_joints) / ref_frame_idx = 동일하게 ref_report, r_list 로 user/ref 각각 독립 선택. fault_joints 는 이 시점에 vv.faultJoints 의 keypoint 이름공간이라 report joints 와 정합. fault_zoom import 는 현재 line 2680 의 _fz 지연 import 를 블록 상단으로 올려 재사용. try/except (TypeError, ValueError) → None 가드 보존 (defensive, 기존 규칙). 분석 단위 1프레임 구조(카드별 아님)는 그대로 유지 — 구조 변경 최소화 (requested_changes 2). 주변 주석의 "각-측 median 프레임" 문구를 "window 내 멤버 관절 평균 confidence 최대 프레임 (부재 시 median 폴백)" 으로 갱신.

    (3) 테스트는 behavior 블록대로 test_fault_zoom.py 에 추가 (순수 helper — 기존 select_advisory_joints 테스트 군 옆). pipeline 쪽은 순수 helper 위임이라 별도 pipeline 테스트 불요 — 배선은 grep 게이트로 검증.

    채점 무접촉 확인: 변경 파일이 fault_zoom.py(표시 전용 모듈) + app.py 의 _attach_fault_zoom_comparisons 표시 블록 + 테스트뿐인지 git diff --name-only 로 확인 — dimensions/vision_veto/assemble 등 채점 경로 0 diff → deductionBreakdown/visionVeto diff 0.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_fault_zoom.py tests/test_fault_zoom_relaxed_crop.py -q && grep -c "select_confident_frame" functions/pipeline/app.py | grep -qv "^0$" && python3 -m compileall -q functions/pipeline/app.py</automated>
  </verify>
  <done>helper 테스트 3건 GREEN, pipeline 이 median 대신 select_confident_frame 을 user/ref 독립 호출 (grep 확인), app.py 컴파일 OK. confidence 부재 legacy doc 은 median 폴백으로 기존 산출 동일.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (신규 없음) | display 전용 backend 내부 변경 — 외부 입력 경계/패키지 설치/시크릿 무접촉 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-q260705ftn-01 | DoS | select_confident_frame 비정상 candidates | mitigate | int 강제 변환 실패 skip + clamp, 빈/전원 무효 → None (기존 defensive 규칙 계승) |
| T-q260705ftn-02 | Tampering | 채점 경로 오염 | mitigate | git diff --name-only 로 fault_zoom.py/표시 블록/테스트 외 0 diff 확인 (Task 2) |
</threat_model>

<verification>
- cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python:. python3 -m pytest tests/test_fault_zoom.py tests/test_fault_zoom_relaxed_crop.py -q → 전체 GREEN (기존 계약 + 신규 3건 이상)
- cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q → backend 전체 회귀 GREEN
- git diff --name-only 가 fault_zoom.py, functions/pipeline/app.py, tests/test_fault_zoom*.py 로 한정 — 채점 로직 무접촉 (deductionBreakdown/visionVeto diff 0)
- 실기기 PNG 재생성 검증(kip-up 재분석)은 pod 필요 — SUMMARY 에 PENDING 박제 (output 참조)
</verification>

<success_criteria>
- relaxed crop: 밀집/단일 저신뢰 좌표 → floor(_CROP_FRAC) 크기 부위 crop (전폭 미도달), 흩어진 좌표 → bbox*_BBOX_MARGIN*_RELAXED_MARGIN 확대 — 신규 상수 0
- 표시 프레임: sourceFrameIndices window 내 멤버 관절 평균 confidence 최대 프레임 (user/ref 독립, legacy median 폴백) — 순수 helper + pipeline 위임 구조
- 기존 fault_zoom 테스트 계약 GREEN (widen 테스트는 새 계약으로 재작성 — 구 테스트가 버그 크기를 assert 하고 있었음을 SUMMARY 에 명기)
- 채점 산출 diff 0
</success_criteria>

<output>
Create `.planning/quick/260705-ftn-fault-zoom-reference-crop-fix-relaxed/260705-ftn-SUMMARY.md` when done.
SUMMARY 에 반드시 박제: (1) 실기기 PNG 재생성 검증 = PENDING — pod 재분석(kip-up fault 페어) 필요, (2) test_relaxed_margin_widens_crop_vs_valid 재작성 사유(구 assert 가 버그 크기 336 을 인코딩).
</output>
