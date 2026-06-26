---
phase: quick-260627-afq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/judging_data/criteria/ref-kip-up.yaml
  - backend/judging_data/criteria/ref-power-spin.yaml
  - backend/judging_data/criteria/ref-peter-pan.yaml
  - backend/judging_data/criteria/ref-elbow-twist-sister.yaml
  - backend/judging_data/criteria/ref-pdshape.yaml
  - backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py
  - backend/data/motion_ipsf_map.json
  - backend/tests/test_geometric_criterion_loader.py
  - backend/tests/test_gemini_motion_classifier.py
requirements: [P1-RECOGNIZER-REGISTER, P1-OBJECTIVE-EXTENSION]
must_haves:
  truths:
    - "5 moves (ref-kip-up, ref-power-spin, ref-peter-pan, ref-elbow-twist-sister, ref-pdshape) are in REGISTERED_MOTIONS and have Korean+English aliases that classify to recognized"
    - "each new criteria yaml has hold_moment knee entries with extension_class: EXTEND, angle_target 180, source_ref citing IPSF glossary fully-extended-leg + intended form"
    - "loader validate() passes for all 5 new yamls"
    - "with EXTEND knees in profile, a bent-knee input produces a leg_extension (ipsf_absolute) deduction and the reference_relative angle_vs_reference__knee for those knees is cross-excluded (no double count)"
    - "a straight-knee (180-ish) input produces ~0 knee deduction even when it differs from a 정은지-measured knee angle (de-contamination proof, pod-free)"
  artifacts:
    - path: "backend/judging_data/criteria/ref-kip-up.yaml"
      provides: "objective knee-extension criteria for kip-up (headline 100/100 false-positive target)"
      contains: "extension_class: EXTEND"
    - path: "backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py"
      provides: "5 moves registered + aliased"
      contains: "ref-kip-up"
  key_links:
    - from: "criteria yaml extension_class: EXTEND"
      to: "GeminiTechniqueRecognizer._build_profile extend_joints"
      via: "load_grouped_criteria(motion) hold_moment EXTEND -> joint_expectations JOINT_EXTEND"
      pattern: "extension_class"
    - from: "profile.expects_extension(knee)"
      to: "ipsf_criteria leg_extension (ipsf_absolute) + reference_relative cross-exclusion"
      via: "dimensions.extension_deviation -> leg_extension seed; 24-07 cross-exclusion drops angle_vs_reference__knee"
      pattern: "leg_extension"
---

<objective>
P1 step 4 — recognizer 등록 + 객관 IPSF 무릎 신전 채점 wiring. 디버그(recognizer-ipsf-fallback)가
확정: 객관 채점 스키마/배선은 완비, 빠진 건 데이터(EXTEND 인코딩 + 동작 등록). 이 작업은 순수
데이터+등록+테스트 (엔진 코드 변경 0).

belle 결정(15-IPSF-SOURCING-2026-06-27.md): IPSF가 이 동작들을 element로 정의 안 함 →
곧아야 할 관절(무릎)을 객관 180°(ipsf_absolute)로 채점. "왜" 강해야(범주형 제외, 비례 유지).
기준은 사용자에게 노출. source_ref는 IPSF 보편기준(Glossary fully-extended-leg) + 동작 의도된
폼(belle 도메인) — 존재 안 하는 element code 날조 금지.

효과: 무릎이 EXTEND면 leg_extension(ipsf_absolute, 180°)이 켜지고, 그 무릎의 reference_relative
(angle_vs_reference__knee, 정은지 흉내=오염원)는 cross-exclusion으로 빠짐 →
(1) 정타 오염 제거(정타의 곧은 다리≈180°→감점0, 정은지와 14~18° 차이 무관),
(2) kip-up 18° 굽음 검출(현재 100/100 위양성).
</objective>

<context>
@./CLAUDE.md
@backend/judging_data/README.md
@backend/judging_data/criteria/ref-invert.yaml
@backend/shared/python/sunity_shared/judging/geometric_criterion.py
@backend/shared/python/sunity_shared/judging/loader.py
@backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py
@backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
@backend/shared/python/sunity_shared/analysis/ipsf_criteria.py
@backend/shared/python/sunity_shared/analysis/dimensions.py
@backend/data/motion_ipsf_map.json
@.planning/phases/15-mode-1-mode-3-testflight/15-IPSF-SOURCING-2026-06-27.md
</context>

<key_facts>
- yaml은 파일명 {motion}.yaml로 resolve (loader._resolve_yaml_path). 새 파일 = backend/judging_data/criteria/ref-{move}.yaml.
- _build_profile: extend_joints = {c.joint_key for c in hold_criteria if c.extension_class=="EXTEND"} → joint_expectations[j]=JOINT_EXTEND. yaml 미등재 joint = 자동 BENT_OK.
- GeometricCriterion.validate() 가드: tolerance_full>0, deduction_per_step>0, 0≤angle_target≤360, minimum_requirement≤angle_target, source_ref 비어있지 않음, moment_key∈{setup,hold,peak,release}.
- 8 JOINT_KEYS: left/right elbow, left/right shoulder, left/right hip, left/right knee. 무릎각 180°=다리 곧음.
- ipsf_criteria.leg_extension = deviation_source ipsf_absolute, profile.expects_extension-gated. 24-07 reference_relative per-joint(angle_vs_reference__{jk})는 cross-exclusion으로 leg_extension이 claim한 joint에서 빠짐(double-count 0).
- 객관 채점은 GeminiTechniqueRecognizer 경유로만 활성(FallbackRecognizer는 motion_id=None). 이 작업은 데이터/등록만 — 분석 경로 Gemini 활성화(GEMINI_RECOGNIZER_ENABLED)는 step 5 pod 셋업에서 보장.
- REGISTERED_MOTIONS 변경 = Phase 5 scope 변경(코멘트 경고). 이 P1 작업이 그 변경의 sanctioned 근거. 커밋/summary에 명시.
</key_facts>

<tasks>

<task type="auto">
  <name>Task 1: 5 criteria yaml 생성 (객관 무릎 신전 EXTEND)</name>
  <files>backend/judging_data/criteria/ref-kip-up.yaml, ref-power-spin.yaml, ref-peter-pan.yaml, ref-elbow-twist-sister.yaml, ref-pdshape.yaml</files>
  <action>
    ref-invert.yaml을 템플릿으로 각 동작 yaml 생성. hold_moment에 무릎 EXTEND entry:
      - kip-up / power-spin / peter-pan / elbow-twist-sister: left_knee + right_knee 둘 다 (대칭, 양 다리 곧음).
      - pdshape: left_knee + right_knee 둘 다 추가하되, 파일 상단 주석에 "비대칭(자유 다리만 곧음) — 양 무릎 EXTEND는 anchor 다리 위양성 위험. step5 pod sweep + clean-residual 게이트로 검증, 정타 잔차 뜨면 자유 다리만으로 재조정" 명시.
    각 무릎 entry:
      joint: left_knee / right_knee
      angle_target: 180.0
      tolerance_full: 20.0
      deduction_per_step: 0.2
      minimum_requirement: 160.0   # IPSF micro-bent 경계(180-20). validate: ≤angle_target OK.
      source_ref: "IPSF Pole Sports Code of Points Glossary 'Fully extended leg' (범주형 신전 기준, p.130-131) + 동작 의도된 폼(다리 완전 신전, belle 도메인). NotebookLM 확정: 본 동작은 IPSF element 미등재 — element code 날조 금지, 보편 신전기준 적용."
      extension_class: EXTEND
    setup_moment/peak_moment/release_moment = []. 파일 상단 주석: 출처 = 15-IPSF-SOURCING-2026-06-27.md + belle 결정(범주형 제외/객관 180°/Mode1 프로기준). 사람 점수 라벨링 금지 정신 유지. 이모지 금지.
    주의: angle_target=180은 정은지 측정값이 아니라 IPSF 보편 신전기준(객관). 기존 ref-invert식 정은지-measured BENT_OK와 다른 트랙임을 주석에 명시.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python python3 -c "from sunity_shared.judging.loader import load_grouped_criteria; [print(m, [(c.joint_key,c.extension_class) for c in load_grouped_criteria(m)['hold_moment']]) for m in ['ref-kip-up','ref-power-spin','ref-peter-pan','ref-elbow-twist-sister','ref-pdshape']]"</automated>
  </verify>
  <done>5 yaml 로드 + validate 통과, 각 hold_moment에 EXTEND 무릎 entry 존재.</done>
</task>

<task type="auto">
  <name>Task 2: 5 moves 등록 (classifier REGISTERED_MOTIONS + 한/영 alias)</name>
  <files>backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py</files>
  <action>
    REGISTERED_MOTIONS frozenset에 5개 추가: ref-kip-up, ref-power-spin, ref-peter-pan, ref-elbow-twist-sister, ref-pdshape.
    _ALIAS_TABLE에 한국어+영어 alias 추가(lowercase):
      킵업/킵 업/kip-up/kip up/kipup → ref-kip-up
      파워스핀/파워 스핀/power spin/power-spin/powerspin → ref-power-spin
      피터팬/피터 팬/peter pan/peter-pan/peterpan → ref-peter-pan
      엘보 트위스트 시스터/엘보트위스트/엘보 트위스트/elbow twist sister/elbow twist/elbow-twist → ref-elbow-twist-sister
      pdshape/pd shape/pd-shape/피디쉐입/피디 쉐입 → ref-pdshape
    substring 매치 우선순위(긴 alias 우선) 기존 로직과 충돌 없는지 확인(예: "elbow twist"가 "elbow twist sister"를 가로채지 않도록 — 둘 다 같은 canonical이라 무해, 단 확인). 헤더 코멘트의 "5영상 scope(D-01)" 문구를 "P1(2026-06-27): 10 motion scope — 기존 5 + kip-up/power-spin/peter-pan/elbow-twist-sister/pdshape 객관 무릎신전 등록"으로 갱신.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python python3 -c "from sunity_shared.analysis.gemini_motion_classifier import classify_motion_name as f; [print(n, f(n)) for n in ['킵업','kip-up','파워스핀','피터팬','엘보 트위스트 시스터','pdshape','pd shape']]"</automated>
  </verify>
  <done>7개 입력 전부 (ref-*, "recognized") 반환.</done>
</task>

<task type="auto">
  <name>Task 3: motion_ipsf_map.json 5 entry 정합 (criteriaYaml 링크 + 기준 노출 텍스트)</name>
  <files>backend/data/motion_ipsf_map.json</files>
  <action>
    5개 entry minimal 업데이트(스코어링은 yaml 파일명으로 동작하므로 map은 copy/표시 routing):
      criteriaYaml: "ref-{move}.yaml" (null → 파일명),
      angleSource: "no_angle_criterion" → "ipsf_extension_objective" (또는 코드가 소비하는 enum 확인 후 적합값; assemble.is_reference_free_motion/소비처 깨지지 않는 값으로. 불확실하면 angleSource 유지하고 criteriaYaml만 갱신),
      sourceNote 끝에 " | P1 2026-06-27: 객관 무릎 신전(IPSF 180° 보편기준) criteria yaml 추가 — 곧은 다리 채점, 사용자 노출 기준." 추가.
    주의: angleSource enum을 바꾸기 전 assemble.py/소비처에서 해당 값이 어떻게 분기되는지 확인. 깨질 위험 있으면 angleSource는 건드리지 말고 criteriaYaml+sourceNote만.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 -c "import json; m=json.load(open('backend/data/motion_ipsf_map.json')); print('valid json')"</automated>
  </verify>
  <done>JSON valid, 5 entry criteriaYaml 링크됨, 소비처 회귀 없음.</done>
</task>

<task type="auto">
  <name>Task 4: 테스트 — 등록 + 객관 채점 de-contamination(pod-free)</name>
  <files>backend/tests/test_geometric_criterion_loader.py, backend/tests/test_gemini_motion_classifier.py</files>
  <action>
    (a) loader 테스트: 5개 새 motion이 load_grouped_criteria로 validate 통과 + hold_moment에 EXTEND 무릎 존재 단언.
    (b) classifier 테스트: 한/영 alias가 (ref-*, "recognized") 매핑 단언.
    (c) **de-contamination + kip-up 검출 단위 테스트**(핵심, pod-free) — 신규 또는 적합 테스트 파일에:
        - EXTEND 무릎 profile 구성(load_grouped_criteria('ref-kip-up') 또는 joint_expectations 직접) 후,
        - 굽은 무릎 각도행렬(예: 양 무릎 162° = 180-18, kip-up fault급) → dimensions.extension_deviation/line_score 또는 ipsf_criteria seed 경로로 leg_extension(ipsf_absolute) 감점 발생 단언, 그리고 그 무릎의 reference_relative(angle_vs_reference__knee)가 cross-excluded(중복감점 0) 단언.
        - 곧은 무릎(예: 178°, 정은지 measured와 다른 값이어도) → 무릎 감점 ~0 단언(de-contamination 증명).
        실제 함수 시그니처(extension_deviation, line_score, criteria_from_measured_deviations, deduction_engine.tally)를 소스에서 확인 후 호출. 구조적 단언만(특정 점수 밴드 단언 금지). 의미있는 테스트만, 수치 채우기 금지.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python python3 -m pytest tests/test_geometric_criterion_loader.py tests/test_gemini_motion_classifier.py -q</automated>
  </verify>
  <done>전 테스트 통과. de-contamination 테스트(곧은 무릎=감점0, 굽은 무릎=감점) + cross-exclusion 단언 포함.</done>
</task>

</tasks>

<verification>
- cd backend && PYTHONPATH=shared/python python3 -m pytest tests/ -q — 회귀 없음(기존 테스트 포함).
- phase24 게이트: PYTHONPATH=shared/python python3 evals/phase24/assert_gates.py — clean-residual/sensitivity 신규 게이트 깨지지 않음(이 변경은 합성 아티팩트 미생성이라 generalization kip-up red는 step5 pod 전까지 유지).
- 이모지 0, 사람 점수 라벨 0, source_ref IPSF 인용 존재.
</verification>

<success_criteria>
- 5 moves 등록(REGISTERED_MOTIONS+alias) → classify recognized.
- 5 criteria yaml EXTEND 무릎 + IPSF 보편기준 source_ref + validate 통과.
- de-contamination 단위테스트: 곧은 무릎=감점0(정은지 측정값 무관) / 굽은 무릎=ipsf_absolute 감점 + reference_relative cross-excluded.
- 엔진 코드 변경 0(데이터+등록+테스트만). 회귀 없음.
</success_criteria>

<output>
Create .planning/quick/260627-afq-p1-step4-register-5-moves-objective-ipsf/260627-afq-SUMMARY.md when done.
</output>
