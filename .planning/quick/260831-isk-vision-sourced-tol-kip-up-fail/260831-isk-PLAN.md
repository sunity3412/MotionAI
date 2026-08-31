---
phase: quick-260831-isk
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/deduction_engine.py
  - backend/tests/test_deduction_engine.py
autonomous: true
requirements:
  - "belle 2026-08-31 승인: kip-up 페어 스윕 방향 FAIL(fault 100=correct 100) — '1번 수리하자'"
must_haves:
  truths:
    - "vision-sourced split_angle 편차는 tol 재적용 없이 감점된다 (over = dev): 편차 20° → record points -20.0"
    - "geometry-sourced split_angle 편차의 tol(20°) 적용은 byte-불변 (기존 geometric 테스트 무수정 PASS)"
    - "kip-up fault 상당 fixture(오늘 재현 verdict: student 145°/reference 165°/severity minor)에서 split_angle record 발생, correct 상당(supported_differences 0)은 무변화"
    - "전체 pytest 무회귀(기준선 4532 passed/0 failed + 신규) + phase24/25 pod-free assert_gates PASS"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/deduction_engine.py"
      provides: "_criterion_deduction vision_sourced tol-bypass (reference_relative 분기)"
      contains: "vision_sourced"
    - path: "backend/tests/test_deduction_engine.py"
      provides: "vision tol-bypass 단위 테스트 3케이스 + geometry 불변 + 실 verdict fixture"
  key_links:
    - from: "deduction_engine.py tally 루프 (L429 부근)"
      to: "_criterion_deduction"
      via: "vision_sourced=cid in vision_measured 키워드 인자"
      pattern: "vision_sourced=cid in vision_measured"
---

<objective>
vision-sourced reference_relative 편차에 tol 재적용 제거 (over = dev) — kip-up 페어
스윕 방향 FAIL(fault 100 = correct 100) 수리.

스펙 정본 = `.planning/quick/260831-kipup-diagnosis/DIAGNOSIS.md`. 결함: vision 이
지지한 split 결함 편차 20°가 reference_relative tol 20°와 동률이라 over=0 → 감점
record 0 → fault 100점. 수리 규칙: **source=vision 인 측정 편차에는 tol 을 재적용하지
않는다.** tol=20 은 "항상 재는" 기하 측정기의 무차별 노이즈 마진이고, vision 은 결함
발견 시에만 값을 내며 support 게이트가 이미 노이즈 게이트 역할을 한다(correct 대조
실증 0건). geometry-sourced 는 불변.

Purpose: 방향 복원 — fault < correct. 모델 세대의 크기 추정 드리프트(50°↔20°)는
per-record cap(-20)이 흡수하므로 점수가 안정된다.
Output: deduction_engine.py 단일 seam 수정 + 테스트, Pod 불필요.

**금지 (DIAGNOSIS + 오케스트레이터 명시):** severity→점수 밴드 재도입(ND-01), 새 튜닝
상수, 동작명 분기, 이 영상 맞춤 조정, `vision_veto.py` 수정(계약 확인용 read-only).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260831-kipup-diagnosis/DIAGNOSIS.md
@backend/shared/python/sunity_shared/analysis/deduction_engine.py
@backend/tests/test_deduction_engine.py
</context>

<interface_measurement>
플래너 실측 결과 (구현 위치 확정 — 실행자는 재조사 불필요, grep 재확인만):

1. **주입 seam**: `deduction_engine.py` tally 함수 L317~359 — vision 편차는
   `_vision_measured_deviation(member/diff)` → `split_vision_candidates` →
   `_median_lower` 집계 → `md["split_angle"] = dev` + `vision_measured["split_angle"] = dev`
   (L356-359). **`vision_measured` dict 가 곧 source 마커다** — record 의
   `source="vision"` 도 이미 `cid in vision_measured` 로 결정된다 (L489).
2. **tol 적용 지점**: `_criterion_deduction(cid, crit, md, quantification, baseline_kind)`
   L584. split_angle 은 `deviation_source="reference_relative"` + `direction="over_target"`
   (ipsf_criteria.py L98-107) → L605-611 분기에서 `over = max(0.0, d - tol)`.
   호출부는 L429 단일 지점 (`meta = _criterion_deduction(...)`) — 함수는 source 정보를
   받지 않는다. **여기가 유일한 tol 관문** — criterion 활성화는 `pointed`(라우팅) 경유라
   seed 단계 tol 필터(`criteria_from_measured_deviations`)는 vision 경로를 막지 않는다
   (seed 는 L315, 주입은 L356 — 주입 전 md 로 계산됨).
3. **선택한 구현 (A안)**: `_criterion_deduction` 에 `vision_sourced: bool = False`
   키워드 인자 추가, reference_relative/over_target 분기에서만
   `over = d if vision_sourced else max(0.0, d - tol)`. 호출부 L429 에서
   `vision_sourced=cid in vision_measured` 전달. md dict 계약(cid→float) 무변경,
   기본값 False 라 geometry 경로 byte-불변.
4. **기각한 대안 (B안, 주입 seam 에서 dev+tol 주입)**: record 의 `measured_value` 가
   실측 편차가 아닌 dev+tol 로 오염된다 — belle 2026-06-29 결정 A 의 투명 표기
   ("split N° 좁음(vision 측정) −X")가 깨지고 median 집계 의미도 왜곡. 기각.
5. **상수 실측**: `_SLOPE = kismam._PENALTY_PER_DEG = 1.2`, `PER_RECORD_DEDUCTION_CAP
   = 20.0`, split tol = `_ANGLE_TOLERANCE_DEG = 20.0`. 따라서 dev 20 → raw 24.0 →
   cap_hit(24>20) → points **-20.0**, raw_points -24.0, cap_applied True. DIAGNOSIS
   사전 박제 예측(-20, overall 80)과 산술 일치 확인됨.
6. **ipsf_absolute 분기(L613-634)는 건드리지 않는다** — `vision_measured` 는 현행
   split_angle(reference_relative) 만 담을 수 있다. DIAGNOSIS 스펙도 reference_relative
   로 한정. DORMANT critical 분기(L625-632) 무접촉.
</interface_measurement>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: vision-sourced tol-bypass 구현 (RED→GREEN)</name>
  <files>backend/shared/python/sunity_shared/analysis/deduction_engine.py, backend/tests/test_deduction_engine.py</files>
  <behavior>
    신규 테스트 (test_deduction_engine.py, 기존 vision-주입 테스트 근처 §에 추가 —
    기존 helper `_ctx`/`_diff`/`_tally` 재사용, Gemini 호출 0):
    - Test 1 (dev == tol, kip-up 재현 핵심): geometric md 에 split 부재 + vision diff 가
      split 편차 20° 주입 → split_angle record **방출**, deviation == 20.0,
      measured_value == 20.0, source == "vision", points == -20.0 (raw 24.0 cap),
      cap_applied True. 단독-record fixture 면 final == 80 (DIAGNOSIS 사전 박제와 대조).
    - Test 2 (dev < tol): vision 편차 12° → record 방출, deviation == 12.0,
      points == pytest.approx(-14.4) (1.2×12, cap 미달). 종전 dead-zone 이던 구간이
      vision 에서는 감점됨을 명시 — support 게이트가 노이즈 게이트라는 근거를
      docstring 에 DIAGNOSIS 인용으로 박제.
    - Test 3 (dev > tol): vision 편차 30° → deviation == 30.0 (종전 10.0 아님),
      points == -20.0 (raw 36.0 cap).
    - Test 4 (geometry 불변 게이트): geometric md["split_angle"]=40 직접 주입(vision
      diff 없음) → 종전과 동일하게 deviation == 20.0 (tol 적용 유지). geometric
      12° → record 미방출(dead-zone 유지). — 기존 L753-763 테스트가 이미 커버하지만
      "이 수리가 geometry 를 안 건드림"을 한 테스트 안에서 대조 단언.
  </behavior>
  <action>
    RED: 위 4테스트 작성 → Test 1-3 FAIL / Test 4 PASS 확인.
    GREEN: interface_measurement §3 대로 구현 —
    (1) `_criterion_deduction` 시그니처에 `vision_sourced: bool = False` 추가,
        reference_relative/over_target 분기(L605-611)에서
        `over = d if vision_sourced else max(0.0, d - tol)`. 주석에 DIAGNOSIS 근거
        (vision 은 support 게이트가 노이즈 게이트, tol 은 기하 무차별 측정 마진) +
        quick-260831-isk 인용. ipsf_absolute 분기 무접촉.
    (2) 호출부(L429, 단일 call site — `grep -n "_criterion_deduction(" ` 로 재확인)에서
        `vision_sourced=cid in vision_measured` 전달.
    새 튜닝 상수 0, 동작명 분기 0, vision_veto.py 무접촉.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_deduction_engine.py -x -q -k "vision"</automated>
  </verify>
  <done>신규 4테스트 PASS. `_criterion_deduction` 기본값 경로(geometry) 산출 byte-불변 (Test 4 + 기존 geometric split 테스트 무수정 통과).</done>
</task>

<task type="auto">
  <name>Task 2: tol-재적용을 박제한 기존 테스트 기대값 정정 + 실 verdict fixture</name>
  <files>backend/tests/test_deduction_engine.py, backend/tests/test_record_moment_engraving.py</files>
  <action>
    (1) **기존 기대값 변경 — 전건 정당화 주석 필수** (오케스트레이터 명시 조건:
    "vision-sourced tol 을 인코딩한 기존 테스트 기대값 변경은 정당화 주석과 함께").
    플래너 실측으로 확정한 변경 대상 (test_deduction_engine.py):
    - L777-786 부근: vision 30° 주입 → `deviation == 10.0` → **30.0** (points 도 -20.0
      cap 으로 재계산).
    - L920-931 부근: 부모 승계 dev 28 → "over-tol = 8" → **28.0** (points -20.0 cap).
    - L935-946 부근: 멤버 자신 30 우선 → over 10 → **30.0**. 이 테스트의 목적은
      "부모 50 아닌 멤버 30 사용" 검증 — 수리 후 부모/멤버 구분이 deviation 30 vs 50
      으로 여전히 판별됨(cap 전 raw_points 36 vs 60 으로도 판별 가능). 단언을 판별력
      유지 방향으로 갱신.
    - L950-962 부근: 명시 각도쌍 |180−150|=30 → over 10 → **30.0**.
    - L979-992 부근: median(20,26,30)=26 → `rec.deviation == 6.0` → **26.0**
      (points -20.0 cap). md 주입값 26.0 단언은 불변.
    - **L1040-1067 부근 (프로덕션 재현 테스트 — 이 결함을 박제한 장본인)**: "dev 20 ==
      tol 20 → dead-zone, split record 미방출, final 99" 를 **뒤집는다** → split record
      방출, deviation 20.0, points -20.0, final = 종전 99 에서 -20 반영값(실행 트랙
      합산-캡 안이면 79 — 실행해 확정). 정당화 주석에 DIAGNOSIS 관측 체인(스윕 doc
      records=0 → fault 100 = correct 100 방향 FAIL) 인용.
    각 변경 주석 형식: `# quick-260831-isk: vision-sourced tol 재적용 제거 (DIAGNOSIS.md) — 종전 기대 N 은 결함 박제`.
    (2) **실 verdict fixture 테스트 신규 1건**: 오늘(08-31) 로컬 재현 verdict 를 dict 로
    재구성 — supported_differences 1건: fault_category "split_angle",
    student_angle_deg 145.0, reference_angle_deg 165.0, severity "minor" (명시 각도쌍
    경로 → `explicit_measured_deviation_deg` = 20.0). tally → split_angle record 발생,
    source "vision", measured_value 20.0, points -20.0 단언. 대조: 같은 md 에
    supported_differences 0건(correct 상당) → split record 0, 점수 무변화 단언.
    **Gemini 재호출 금지 — 순수 dict fixture.** severity 는 어떤 산식에도 쓰지 않는다
    (ND-01: severity→점수 밴드 재도입 금지 — fixture 필드로만 존재).
    (3) test_record_moment_engraving.py L130-156 (vision split record 순간-필드 부재
    테스트): record 존재 전제만 확인 — deviation 수치를 박제했으면 (1)과 동일 형식으로
    정정, 아니면 무접촉.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_deduction_engine.py tests/test_record_moment_engraving.py -q</automated>
  </verify>
  <done>두 파일 전건 PASS. 기대값 변경 전건에 quick-260831-isk 정당화 주석. 실 verdict fixture 가 DIAGNOSIS 사전 박제 예측(record -20 / correct 무변화)과 일치.</done>
</task>

<task type="auto">
  <name>Task 3: 전체 무회귀 + phase24/25 pod-free 게이트 + 점수 이동 예고</name>
  <files>(코드 변경 없음 — 게이트 실행 + SUMMARY 작성)</files>
  <action>
    (1) 전체 스위트: `cd backend && .venv/bin/python -m pytest tests -q` — 기준선
    4532 passed / 0 failed (260831-gyk 이후). 목표: failed 0, passed ≥ 4532+신규.
    Task 1-2 가 못 잡은 원거리 소비처(예: test_pipeline_vision_gate 등)가 vision-split
    tol 을 박제했으면 Task 2 (1)과 동일 규율로 정정.
    (2) phase24 게이트: `cd backend && .venv/bin/python evals/phase24/assert_gates.py`
    (인자 없음, pod-free). 플래너 실측 예측 = PASS: 합성 breakdown 의 `_diff` helper 는
    `approx_angle_deviation_deg: 0`(주입 불발), monotonicity/sensitivity/generalization
    fixture 는 geometric md 직접 주입(`{"split_angle": 45.0}` 등)이라 geometric tol
    경로 = 불변.
    (3) phase25 게이트: `cd backend && .venv/bin/python evals/phase25/assert_gates.py`
    — phase24 상속 7게이트(위와 동일 근거) + 신규 5게이트는 저장 artifact(JSON) 구조
    검사라 엔진 재실행 없음. 예측 = PASS. "pointed-only" 구조 규칙과도 정합: 이 수리는
    record 를 vision 이 짚은 관절에서만 **더 잘** 발생시킨다.
    (4) **STOP 규칙**: (2)/(3) 이 FAIL 하면 — 그 게이트의 기대가 "vision-sourced tol
    재적용"을 박제한 것인지 판단. 박제면 정당화 주석과 함께 정정, 아니면(실 회귀 신호)
    수정 없이 STOP 하고 FAIL 원문을 SUMMARY 에 박제 후 보고 (오케스트레이터 지시).
    (5) **SUMMARY 점수 이동 예고 (08-09 교훈 — 의무)**: SUMMARY.md 에 명시 —
    영향 범위: 현행 vision 주입은 split_angle 뿐(`vision_measured` 의 유일 키, 플래너
    실측). 이동 방향: vision-supported split 결함의 감점 발화 문턱이 tol 20°에서
    0°(support 게이트만)로 내려간다 — 종전 dead-zone(1~20°) 케이스가 새로 감점.
    예상 이동: kip-up fault 상당 100→약 80 (사전 박제), correct 영상(differences 0)
    무변화, split 을 vision 이 짚지 않는 동작 무변화. geometry 채점 전 경로 byte-불변.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests -q && .venv/bin/python evals/phase24/assert_gates.py && .venv/bin/python evals/phase25/assert_gates.py</automated>
  </verify>
  <done>pytest failed 0 (passed ≥ 4532+신규). phase24/25 게이트 PASS (또는 박제-기대 정정의 정당화가 SUMMARY 에 기록). SUMMARY 에 점수 이동 예고 섹션 존재.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Gemini verdict → deduction engine | vision 편차는 외부 모델 산출 — 단 이 수리는 새 입력면을 열지 않음 (기존 `_vision_measured_deviation` 의 finite/양수 검증 + support 게이트 그대로) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-isk-01 | Tampering | _criterion_deduction over 계산 | mitigate | vision-sourced 도 기존 `np.isfinite(over)` 가드 + per-record cap -20 통과 — 폭주 편차가 점수를 무한 하락시키지 못함 (기존 방어 재사용, 신규 검증 0) |
| T-isk-02 | DoS | 점수 경로 | accept | 신규 패키지 설치 0, 외부 호출 0 — 순수 산술 변경 |
</threat_model>

<verification>
- 신규 vision tol-bypass 테스트 4건 + 실 verdict fixture PASS
- geometry tol 경로 byte-불변 (기존 geometric split 테스트 무수정 통과)
- 전체 pytest failed 0 (기준선 4532 대비 무회귀)
- phase24/25 pod-free assert_gates PASS (FAIL 시 STOP 규칙 적용)
- 기대값 변경 전건에 quick-260831-isk 정당화 주석
</verification>

<success_criteria>
- kip-up fault 상당 fixture: split_angle record points -20.0 (DIAGNOSIS 사전 박제 일치),
  correct 상당: 무변화 — 방향 복원 (fault < correct)
- 수리 diff = deduction_engine.py 단일 함수 + 단일 call site (새 튜닝 상수 0,
  동작명 분기 0, severity 미사용, vision_veto.py 무접촉)
- SUMMARY 에 점수 이동 예고 명시
</success_criteria>

<output>
Create `.planning/quick/260831-isk-vision-sourced-tol-kip-up-fail/260831-isk-SUMMARY.md` when done
</output>
