---
phase: 24-transparent-deduction-scoring
plan: 260626-jwu (quick)
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/ipsf_criteria.py
  - backend/shared/python/sunity_shared/analysis/deduction_engine.py
  - backend/tests/test_deduction_engine.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_pipeline_deduction_seam.py
autonomous: true
requirements:
  - "24-07-FIX-① — reference-relative per-joint angle deviation을 deduction 엔진 granular seed로 배선 (미등록 동작 md 빔 → per-joint granular tally)"
user_setup: []

must_haves:
  truths:
    - "미등록 동작(expects_extension 전부 False)에서 reference 대비 무릎/팔꿈치 편차가 tol(20°) 초과하면 deduction_engine.tally 가 dimension_overall_fallback 이 아니라 관절별 reference_relative DeductionRecord 를 방출한다"
    - "같은 영상 self-compare(per_joint_deviation median=0)는 reference_relative 감점 0 (위양성 0)"
    - "등록 동작에서 leg_extension(ipsf_absolute) seed 가 있으면 같은 무릎 관절에 reference_relative 가 double-count 되지 않는다"
    - "동일 입력 반복 시 records/final 이 결정적으로 동일하다"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/ipsf_criteria.py"
      provides: "JOINT_KEYS 별 reference_relative 각도 criterion (deviation_source=reference_relative, tolerance=20°=kismam, slope=_SLOPE, cap=_ANGLE_CAP) + _MEASURABLE_SEED_IDS 확장"
      contains: "angle_vs_reference"
    - path: "backend/shared/python/sunity_shared/analysis/deduction_engine.py"
      provides: "_criterion_deduction reference_relative 각도 분기 + HIGH-5 확장 cross-exclusion(active ipsf_absolute joint_keys → reference_relative 동일관절 discard)"
      contains: "reference_relative"
    - path: "backend/functions/pipeline/app.py"
      provides: "_build_deduction_measured_deviations 가 reference_dtw_match+reference_angles 로 per_joint_deviation 산출→ expects_extension 미소유 관절만 reference_relative md 방출 + seam 배선"
      contains: "per_joint_deviation"
  key_links:
    - from: "pipeline/app.py _build_deduction_measured_deviations"
      to: "motiondtw.per_joint_deviation"
      via: "match.path + angles[start:end] + reference_angles"
      pattern: "per_joint_deviation\\(.*path"
    - from: "deduction_engine.tally"
      to: "ipsf_criteria.CRITERION_GROUPS reference_relative 각도 criteria"
      via: "criteria_from_measured_deviations seed + _ordered 순회"
      pattern: "angle_vs_reference"
---

<objective>
Phase 24 결함 ① fix — pod 재-sweep(2026-06-26)로 확정된 "(A) 엔진 게이트는 고쳤지만 md(seed)가 비어 inert" 결함을 닫는다. 미등록 동작(인식기가 reference 동작을 미등재 → `expects_extension` 전부 False → ipsf_absolute seed 빔 → `dimension_overall_fallback`)에서, 이미 측정 가능한 reference-상대 per-joint 각도 편차(`motiondtw.per_joint_deviation`)를 deduction 엔진 seed 로 배선해 belle 핵심 wish(−X 왼무릎 −Y 오른팔꿈치 항목별 내역)를 실현한다.

24-07-FIX-DESIGN §3 을 그대로 구현. **재설계·재calibration 금지** — kismam `_IPSF_TOLERANCE_DEG=20.0` + `_PENALTY_PER_DEG`(=`_SLOPE`) 재사용([[calibration-source-hard-gate]]).

Purpose: 미등록 동작의 Mode1 헤드라인이 dimension_overall(72 등 단일 score)에서 reference-relative per-joint granular 합산으로 바뀐다 (ND-01/05 의도). 점수 의미 = "정은지 대비 per-joint 편차 합산" — belle 투명 감점 철학 그 자체([[scoring-must-be-transparent-deduction-tally]]).

Output: ipsf_criteria reference_relative 각도 criterion + 엔진 _criterion_deduction 분기 + 엔진 cross-exclusion + seam 배선 + 순수 단위테스트(미등록→granular / self-compare 0 / 등록 double-count 차단 / 결정성). **score-shift 의 pod 재검증은 별도 sweep — 이 task 는 로컬 단위테스트 green 까지만.**
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/24-transparent-deduction-scoring/24-07-FIX-DESIGN-reference-relative-granular-seed.md

# 구현 대상 (이미 정독된 substrate — 변경/확장 지점)
@backend/shared/python/sunity_shared/analysis/ipsf_criteria.py
@backend/shared/python/sunity_shared/analysis/deduction_engine.py
@backend/functions/pipeline/app.py
@backend/shared/python/sunity_shared/analysis/motiondtw.py
@backend/shared/python/sunity_shared/analysis/kismam.py
@backend/shared/python/sunity_shared/analysis/skeleton.py
@backend/tests/test_deduction_engine.py
@backend/tests/test_pipeline_deduction_seam.py

# 박제 설계 결정 (이 plan 이 선택·문서화한 fork 해소)
# (1) per-joint family vs N joint-specific criteria → N joint-keyed criteria(JOINT_KEYS 순회 생성)
#     선택. 근거: _criterion_deduction 의 "criterion 1개 = record 1개" 모델에 그대로 맞고,
#     엔진 cross-exclusion(요구된 "등록 동작 double-count 0" ENGINE 테스트)을 profile 없이
#     표현 가능. criterion id 가 관절을 운반(angle_vs_reference__{joint}) → granular wish 직격.
# (2) line(collective, joint_keys=()) cross-exclusion 은 엔진이 profile 부재로 구성관절을 못 셈.
#     → 2-layer: seed-stage(builder, profile 보유)가 expects_extension True 관절은 reference_relative
#       md 자체를 안 만든다(line/leg/arm/split 모두 expects_extension 파생이므로 정확). 엔진-stage는
#       active leg/arm/split 의 explicit joint_keys 로 추가 discard(profile-독립 + 테스트 가능 보증).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: reference_relative per-joint 각도 criterion + 엔진 분기 + cross-exclusion (config+engine+engine-tests)</name>
  <files>backend/shared/python/sunity_shared/analysis/ipsf_criteria.py, backend/shared/python/sunity_shared/analysis/deduction_engine.py, backend/tests/test_deduction_engine.py</files>
  <behavior>
    - 미등록 동작 seed: md 에 `angle_vs_reference__left_knee=35` (tol 20° 초과) → tally 가 그 관절 reference_relative DeductionRecord 1개 방출 (criterion="angle_vs_reference__left_knee", deviation_source="reference_relative", unit="deg", points<0). dimension_overall_fallback 아님.
    - dead-zone: md `angle_vs_reference__left_knee=12` (< tol 20°) → seed 안 됨 → record 0.
    - self-compare: md 에 모든 angle_vs_reference__* = 0 → record 0, final=100.
    - double-count 차단: md `{leg_extension:30, angle_vs_reference__left_knee:35, angle_vs_reference__right_knee:33}` → leg_extension record 1개만, 무릎 reference_relative 2개는 cross-exclusion 으로 discard (knee double-count 0).
    - 보완 유지: md `{leg_extension:30, angle_vs_reference__left_shoulder:40}` → leg_extension(무릎) + reference_relative 어깨 둘 다 방출 (어깨는 어떤 ipsf_absolute 도 claim 안 함 = 순수 보완).
    - 결정성: 동일 md 2회 호출 → records 동일 순서·값.
    - LINEAR/cap 정합: over=max(0, dev-20)·_SLOPE, ipsf_cap=_ANGLE_CAP 로 saturate (병적 입력만).
  </behavior>
  <action>
ipsf_criteria.py:
- `CRITERION_GROUPS` 에 JOINT_KEYS(skeleton, 8개) 순회로 reference_relative 각도 criterion 8개를 **프로그램적으로 생성·append** (8개 손-작성 dict 금지 — loop 로 만들어 tuple 에 합친다). 각 criterion 박제:
  · `id = f"angle_vs_reference__{jk}"`, `joint_keys = (jk,)`,
  · `tolerance = _ANGLE_TOLERANCE_DEG` (20°, [CITED] kismam 재사용 — 새 임계 금지),
  · `slope = _SLOPE`, `ipsf_cap = _ANGLE_CAP` ([ASSUMED] 기존 상수 재사용, re-fit 금지),
  · `rule_id = "angle_vs_reference_over_tol_linear"`,
  · `ipsf_anchor = "expert_reference_deviation (정은지 대비 per-joint 편차)"`,
  · `deviation_source = "reference_relative"`, `direction = "over_target"`,
  · `keypoint_set = None` (router 대상 아님 — _MEASURABLE_SEED_IDS seed 전용. 새 keypoint_set 문자열 도입 금지 → 153행 partition assert 불변).
- `_MEASURABLE_SEED_IDS` 에 위 8개 id 를 합친다 (criteria_from_measured_deviations 가 seed 하도록). 기존 4개(leg/arm/split/line) 보존.
- 24-07 § 인용 + provenance 주석([CITED]/[ASSUMED]) 박제. 순수 유지(numpy 외 import 0).

deduction_engine.py:
- `_criterion_deduction` 에 reference_relative 각도 분기 추가. 조건 = `crit["deviation_source"] == "reference_relative" and crit["direction"] == "over_target"` (body_relative_reach 는 insufficient_reach 분기로 이미 분리). 반환: `dev = _finite(md.get(cid))`; None → None(honest 0); `over = max(0.0, dev - tol)`, `measured_value = dev`, `baseline_value = 0.0` (목표 = reference 대비 0° 편차), unit="deg", dev_kind="reference_relative". 24-07 §3-1 박제 — `_IPSF_ABSOLUTE_BASELINE`(180) 경로와 섞지 말 것.
- `tally` cross-exclusion 확장 (HIGH-5 패턴 바로 뒤): active `{leg_extension, arm_extension, split_angle}` 의 `crit["joint_keys"]` 합집합 = `claimed_joints` 구성 → activated 중 `angle_vs_reference__{jk}` 이고 `jk in claimed_joints` 인 것 discard. 주석으로 "line(collective)은 엔진이 profile 부재로 구성관절 모름 → seed-stage(builder)가 expects_extension 으로 차단(Task 2). 엔진-stage 는 explicit joint_keys 보유 criterion(leg/arm/split)만 profile-독립 보증" 박제.
- DeductionRecord 형상 불변(deviation_source 가 이미 reference_relative 지원). 새 contract 키 0. 순수 유지.

test_deduction_engine.py:
- 위 <behavior> 케이스 6종을 결정적 방향/구조 단언으로 추가 (수치 타깃·curve-fit 금지). 기존 헬퍼(`_measured` 류) 재사용하되 reference_relative md 키는 직접 dict 구성. quantification=None + dimension_overall 적당값으로 "unavailable 이어도 reference_relative seed 살아 granular" 경로 단언(24-05 게이트 정합).
  </action>
  <verify>
    <automated>cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_deduction_engine.py -x -q</automated>
  </verify>
  <done>새 6 케이스 포함 test_deduction_engine.py 전체 green. 미등록 seed→per-joint reference_relative record / self-compare 0 / leg_extension 동일관절 double-count 0 / 어깨 보완 유지 / 결정성 모두 통과. 기존 단언(no-final-band, gemini-silent, fallback traceable, partition) 회귀 0.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: seam 배선 — _build_deduction_measured_deviations reference-relative seed + 호출부 (pipeline+seam-tests)</name>
  <files>backend/functions/pipeline/app.py, backend/tests/test_pipeline_deduction_seam.py</files>
  <behavior>
    - 미등록 profile(expects_extension 전부 False) + reference_dtw_match + reference_angles 로 무릎에 편차가 있을 때 → 반환 md 에 `angle_vs_reference__left_knee` 등 per-joint 키가 존재(granular seed). leg_extension/arm_extension/line(ipsf_absolute) 키는 부재(profile-gated honest 0).
    - 등록 profile(무릎 expects_extension True) → 무릎 `angle_vs_reference__*_knee` 키는 md 에 **없음**(seed-stage cross-exclusion = 절대-신전 소유 관절 제외). 어깨(expects_extension False)는 편차 시 reference_relative 키 존재.
    - self-compare(reference_dtw_match.path identity → per_joint_deviation=0) → angle_vs_reference__* 키 0개(또는 0값 미방출).
    - reference_dtw_match=None 또는 reference_angles=None → reference_relative 미방출(graceful, mode3/legacy 무회귀).
    - 결정성: 동일 입력 2회 → 동일 md.
  </behavior>
  <action>
pipeline/app.py:
- `_build_deduction_measured_deviations` 시그니처에 `reference_dtw_match=None, reference_angles=None` keyword 추가. 기존 ipsf_absolute(extension_deviation) + reach forward 블록은 불변.
- 새 reference-relative seed 블록 추가: `reference_dtw_match` 와 `reference_angles` 가 모두 not None 이고 `angles` not None 일 때만 실행.
  · `match.path` 부재/빈 path → skip(graceful).
  · `user_seg = angles[match.start:match.end]` (angles = 학생 full 각도; _deviation_against 와 동일 인덱싱). 형상 mismatch/예외는 try/except(BLE001) 로 honest skip.
  · `dev = per_joint_deviation(match.path, user_seg, a_ref)` (이미 app.py:78 import 됨 — 재계산은 기존 path 순회만, 저비용).
  · for i, jk in enumerate(JOINT_KEYS): `v = float(dev[i])`; `v != v`(NaN) → skip; **`profile is not None and profile.expects_extension(jk)` → skip (seed-stage cross-exclusion — 절대-신전/ line 소유 관절은 ipsf_absolute 가 채점, double-count 금지. 24-07 §3-2)**; `md[f"angle_vs_reference__{jk}"] = v` (0 값도 넣되 엔진 tol gate 가 self-compare 0 을 거른다 — 단 굳이 0 을 안 넣어도 무방; v>0 만 넣어 md 슬림화 권장하고 주석으로 사유 박제).
  · score-not-deviation 안전: per_joint_deviation 은 deg 편차(0-100 score 아님) — HIGH-3 정합 주석 박제.
- seam 호출부(app.py ~3319 `_build_deduction_measured_deviations(...)`)에 `reference_dtw_match=reference_dtw_match, reference_angles=reference_angles_for_veto` 인자 추가. 두 변수는 _process 상단(~2901/2904) 초기화 + mode1 분기(~2987/2988)에서 set 되어 seam 에서 reliably 스코프됨. mode3/legacy 는 None → graceful 미방출.
- 24-07 § 인용 + Korean 주석. contract mirror 불필요(DeductionRecord 형상·models 불변, 새 키 없음 — TS app/src/types/analysis.ts 변경 0).

test_pipeline_deduction_seam.py:
- 위 <behavior> 5종을 mock 기반 단위테스트로 추가. 합성 `reference_dtw_match`(motiondtw.MotionMatch 또는 path 보유 stub) + `reference_angles`(작은 (T,J) 배열) + 미등록/등록 profile 헬퍼로 `_build_deduction_measured_deviations` 직접 호출해 반환 md 키 단언. self-compare = identity path → 0 키. reference_dtw_match=None → 무방출. 실 Gemini/Pod/S3/Firestore 호출 0. 방향/구조 단언만(수치 curve-fit 금지).
  </action>
  <verify>
    <automated>cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_pipeline_deduction_seam.py -x -q</automated>
  </verify>
  <done>seam 테스트 전체 green. 미등록→per-joint reference_relative md 방출 / 등록 무릎 seed-stage 제외 / 어깨 보완 / self-compare 0 / None-input graceful / 결정성 통과. 기존 seam 단언 회귀 0.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 측정 substrate → 채점 엔진 | per_joint_deviation(numpy 산출) 값이 deduction record 로 신뢰됨 — NaN/Inf 가 점수를 오염할 수 있는 지점 |
| reference_dtw_match.path → builder | match.start/end + path 인덱스가 angles 길이를 벗어나면 IndexError |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-24q-01 | Tampering(데이터 무결성) | per_joint_deviation NaN/Inf → record points | mitigate | `_finite` guard(engine) + builder `v != v` skip — NaN 관절은 honest skip(밴드 주입 0). 기존 score_from_deviation WR-02 정신. |
| T-24q-02 | Denial(예외) | builder `angles[match.start:match.end]` 형상 mismatch | mitigate | builder try/except(BLE001) → honest skip(reference_relative 미방출), 채점 경로 무중단. |
| T-24q-03 | Repudiation(double-count) | 등록 동작에서 ipsf_absolute+reference_relative 동일관절 이중 감점 | mitigate | 2-layer cross-exclusion: seed-stage expects_extension gate(builder) + 엔진 active joint_keys discard(testable). 엔진 테스트가 leg_extension 케이스로 증명. |
| T-24q-SC | Tampering | npm/pip/cargo installs | accept | 신규 패키지 설치 0 — 기존 numpy/pytest만 사용. install task 없음(legitimacy gate 비해당). |
</threat_model>

<verification>
- 두 테스트 파일 green: `cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_deduction_engine.py tests/test_pipeline_deduction_seam.py -q`
- 순수성: ipsf_criteria.py + deduction_engine.py 는 numpy 외 import 0 (boto3/Gemini/firestore/network 금지). `grep -nE 'import (boto3|firebase|requests|google)' backend/shared/python/sunity_shared/analysis/ipsf_criteria.py backend/shared/python/sunity_shared/analysis/deduction_engine.py` → 0.
- 밴드 grep 게이트 (변경 후에도 0): `grep -rnE 'apply_downward_cap|SEVERITY_CAP|capApplied' backend/shared/python backend/functions | grep -v '^#' | wc -l` → 0.
- calibration-source 게이트: 새 tolerance/slope 상수 도입 0 — `_ANGLE_TOLERANCE_DEG`/`_SLOPE`/`_ANGLE_CAP` 재사용만 (`grep -n 'TOLERANCE\|SLOPE\|_PER_DEG\|= [0-9].*#.*tol' ipsf_criteria.py` 로 신규 수치 상수 부재 확인).
- contract mirror: DeductionRecord/models 키 변경 0 → app/src/types/analysis.ts 변경 불요(확인만).
</verification>

<success_criteria>
- 미등록 동작(expects_extension 전부 False) + reference 무릎 편차>20° → tally 가 `dimension_overall_fallback` 이 아닌 per-joint reference_relative DeductionRecord 방출 (belle granular wish 실현).
- self-compare(per_joint_deviation=0) → reference_relative 감점 0, final=100 (위양성 0).
- 등록 동작 leg_extension seed 존재 시 동일 무릎 reference_relative double-count 0; 미claim 관절(어깨)은 보완 감점 유지.
- 결정성 + 순수성 + 밴드/calibration 게이트 통과. 새 contract 키 0.
- **score-shift 자체의 pod 재검증(elite 95-100/fault 변별/일반화 게이트)은 본 task 범위 외 — 후속 sweep.**
</success_criteria>

<output>
Create `.planning/quick/260626-jwu-phase-24-fault-1-fix-wire-reference-rela/260626-jwu-SUMMARY.md` when done
</output>
