---
slug: recognizer-ipsf-fallback
status: diagnosed
trigger: "recognizer가 등록 동작(power-spin/pdshape/kip-up/elbow-twist/peter-pan)을 객관 IPSF 기하 채점으로 라우팅하지 못하고 정은지-따라하기(reference-relative) 폴백으로 떨어진다. 근본이 코드 갭인가 IPSF 도메인 데이터 부재인가 못박아야 함."
created: 2026-06-27
updated: 2026-06-27
---

# Debug: recognizer IPSF 라우팅 폴백 (P1 본체)

## Symptoms

- **Expected**: 등록된 동작은 객관 IPSF 기하 기준(이 관절이 실제 180° 펴졌나 / 라인이 곧은가)으로 채점 → extension_deviation/line_score 경로가 켜져야 함.
- **Actual**: 6개 동작이 전부 reference-relative(정은지 각도 흉내) 폴백으로 채점. 결과: 정타가 정은지와 14~18° 어긋나면(체형/스타일) 오염 → kip-up 18° fault 미검출(100/100).
- **Errors**: 런타임 에러 없음 — 조용한 정확도 부채.
- **Timeline**: Phase 15에서 발견([[phase15-recognizer-student-video-line-none]]) 후 "데모 5개 우선"으로 미룸. Phase 18/19/20/24가 이 위에 쌓임.
- **Reproduction**: 6개 동작 영상 분석 → profile.expects_extension 빈 채로 absolute_dimension_scores 호출 → line=None → angle(reference-relative)만 남음.

## Known facts (from exploration 2026-06-27)

- `backend/data/motion_ipsf_map.json`: 6개 동작 등록됨 but 전부 `copyBranch=branch2_eunji_reference` + `angleSource=no_angle_criterion` → `assemble.is_reference_free_motion()=True`.
- `backend/shared/python/sunity_shared/analysis/technique.py` `FallbackRecognizer.recognize()`: 항상 `motion_id=None`, 팔꿈치/무릎 4관절만 각도≥150°(`_EXTENSION_ZONE_DEG`) 휴리스틱으로 JOINT_EXTEND 마킹. category="unknown".
- `backend/shared/python/sunity_shared/analysis/dimensions.py` `line_score`/`extension_deviation`: `profile.expects_extension(joint)`로 분기 → EXTEND 관절 없으면 line=None.
- `assemble.lookup_motion_branch(None)` → `_SAFE_DEFAULT_BRANCH`(branch2).

## Investigation goal

근본을 (a) 코드 로직 갭 vs (b) IPSF 도메인 데이터 부재로 파일·함수·데이터 레벨에서 못박기.
- 코드 갭 → 그 자리에서 fix.
- IPSF 데이터 부재 → 어느 동작의 어느 관절 신전/라인 요건을 NotebookLM IPSF 노트북(id 96b061e8-bb7c-41c5-8606-8ceef2ce1aa3)에서 소싱해야 하는지 **정확한 입력 명세**를 산출(curve-fit 금지 — 임의 IPSF 요건 정의 금지).

## Current Focus

- hypothesis: CONFIRMED — 근본은 LAYERED지만 ~90% (b) IPSF 도메인 데이터 부재. 객관 IPSF 기하 요건을 운반하는 스키마/배선은 end-to-end로 **존재하고 작동**한다(끊긴 wiring 없음). 빠진 것은 데이터: 어떤 동작에도 EXTEND가 단 한 번도 인코딩된 적 없고(전 yaml에 EXTEND 0개), 6개 동작은 yaml 자체가 없으며 REGISTERED_MOTIONS에도 없음. 동반 (a)는 등록 plumbing(REGISTERED_MOTIONS + alias + registry routing)인데 데이터-게이트(belle IPSF 요건 없이는 채울 수 없음)라 독립 코드 fix가 아님.
- next_action: DONE — goal=find_root_cause_only이고 갭이 데이터-게이트라 코드 fix 미적용. 6개 동작 입력 명세(criteria yaml extension_class: EXTEND 스키마) 산출 완료. ROOT CAUSE FOUND 반환.

## Evidence

- checked: dimensions.py line_score(240)/extension_deviation(270)/absolute_dimension_scores(365)
  found: 전부 `profile.expects_extension(joint)` gate. EXTEND 관절이 0개면 line=None(절대 라인 차원 생략) → angle(reference-relative)만 남음. 스키마(profile.joint_expectations)는 **존재**, 채점 경로는 **살아있음**.
  implication: 객관 채점 슬롯은 코드에 있다. 비어있을 뿐.

- checked: technique.py TechniqueProfile.joint_expectations: dict[str,str] (JOINT_EXTEND/BENT_OK/CONTACT) + FallbackRecognizer.recognize(92-113)
  found: 스키마 슬롯 존재. 단 FallbackRecognizer는 motion_id=None + 순수 휴리스틱(4사지 평균각≥150°→EXTEND)으로 채움 — per-move IPSF 데이터 아님. "학생이 이미 하고 있는 것"을 EXTEND로 표시 → 학생이 굽히면 BENT_OK → 절대 안 깎음(오염의 메커니즘).
  implication: Fallback path는 yaml/motion_id 미경유 → 객관 per-move 채점에 영구 도달 불가(데이터 있어도). 객관 채점 활성 경로는 Gemini recognizer 단독.

- checked: gemini_technique_recognizer.py _build_profile(256-324)
  found: 객관 EXTEND를 채우는 **유일한 production 경로**. `load_grouped_criteria(motion)` → `extend_joints={c.joint_key for c in hold_criteria if c.extension_class=="EXTEND"}` → joint_expectations[j]=JOINT_EXTEND. 즉 "어느 관절이 180° 펴져야 하나"의 입력 슬롯 = criteria yaml의 `extension_class: EXTEND`.
  implication: 입력 포맷/리더는 존재. yaml에 EXTEND가 인코딩되면 객관 line 채점이 켜진다.

- checked: geometric_criterion.py(VALID_EXTENSION_CLASSES=("EXTEND","BENT_OK"), default BENT_OK) + loader.py:134 (extension_class=entry.get(...,"BENT_OK"))
  found: extension_class 필드 스키마 + validator + 로더 전부 존재하고 검증됨.
  implication: 스키마는 완비. data-entry만 비어 있음.

- checked: grep "EXTEND" backend/judging_data/criteria/*.yaml
  found: NONE — 5개 yaml(ref-climb/foxtop/foxtop-split/invert/sideway-spin) 모든 criterion이 extension_class: BENT_OK. ref-invert는 명시적으로 "정은지 reference 측정값(분기2) — Body Position 차원=D-19 별 phase"로 객관 채점을 의도적으로 미룸.
  implication: **객관 line 트랙은 시스템 전체에서 단 한 동작도 켜진 적 없다.** EXTEND 슬롯이 system-wide 비어있음. (b) 데이터 부재가 주근본.

- checked: 6개 문제 동작 yaml 존재 여부 + REGISTERED_MOTIONS(gemini_motion_classifier.py:21)
  found: criteria 디렉토리에 6개(power-spin/pdshape/kip-up/elbow-twist-sister/peter-pan/combo) yaml **전무**. REGISTERED_MOTIONS = {ref-climb, ref-foxtop, ref-foxtop-split, ref-invert, ref-sideway-spin} — 6개 동작 **미포함** → Gemini가 "unregistered" 분류 → joint_expectations={} → line=None.
  implication: 6개 동작은 (1) 분류 단계에서 unregistered로 떨어지고 (2) yaml도 없어 EXTEND를 못 얻음. 이중 차단.

- checked: motion_ipsf_map.json 6개 엔트리 + assemble.lookup_motion_branch(106) 소비처
  found: 6개 전부 branch2_eunji_reference + angleSource=no_angle_criterion + criteriaYaml=null. map 헤더 명시: "채점 경로 미진입 — 카피/프롬프트 분기 전용." lookup_motion_branch는 baseline 카피 텍스트 + scoringBasis 라우팅에만 쓰임, joint_expectations 채점 경로와 무관.
  implication: registry는 설계상 객관 채점 source가 아니다. 객관 채점 활성은 REGISTERED_MOTIONS + criteria yaml 경유. map 업데이트는 branch1 카피 정합용(채점 활성과 별개).

## Eliminated

- hypothesis: 스키마(객관 IPSF 타깃이 들어올 자리)조차 코드에 없다 = 순수 코드 로직 갭
  evidence: TechniqueProfile.joint_expectations + criteria yaml extension_class + loader + _build_profile + dimensions.expects_extension-gated 채점 + ipsf_criteria deduction engine(ipsf_absolute seed)까지 end-to-end 완비. 끊긴 wiring 없음. 이미 채워진 필드를 드롭하는 버그도 없음.
  timestamp: 2026-06-27

- hypothesis: registry(motion_ipsf_map.json)를 객관 타깃 source로 배선하면 켜진다 = registry wiring 코드 갭
  evidence: 채점 경로(joint_expectations)는 recognizer의 load_grouped_criteria(yaml) 경유지 registry 경유가 아님. registry는 카피/프롬프트 전용(헤더 명시). registry를 채점에 끌어들이는 건 불필요한 신규 경로 — 기존 yaml 슬롯이 정답.
  timestamp: 2026-06-27

## Resolution

root_cause: |
  LAYERED, 주근본 (b) IPSF 도메인 데이터 부재. 객관 IPSF 기하 요건(어느 관절이 180° 신전 /
  어느 라인이 곧은가)을 recognizer→채점으로 운반하는 코드 스키마/배선은 완비되어 작동한다:
  criteria yaml `hold_moment[].extension_class: EXTEND` (slot) → loader.load_grouped_criteria
  → GeminiTechniqueRecognizer._build_profile → TechniqueProfile.joint_expectations[j]=JOINT_EXTEND
  → dimensions.line_score/extension_deviation/absolute_dimension_scores (expects_extension-gated)
  → ipsf_criteria deduction engine ipsf_absolute seed. 끊긴 wiring·드롭된 필드 없음.
  빠진 것은 데이터: (1) 전 criteria yaml에 extension_class: EXTEND가 0개 — 객관 line 트랙이
  어떤 동작에도 켜진 적 없음. (2) 6개 문제 동작은 criteria yaml 자체가 없고 REGISTERED_MOTIONS
  에도 없어 "unregistered"→joint_expectations={}→line=None→angle(reference-relative)만 남음=오염.
  동반 (a) 코드/설정 변경(REGISTERED_MOTIONS 등록 + alias + per-move yaml 생성)은 belle/IPSF
  도메인 데이터가 있어야만 의미를 가지므로 데이터-게이트 — 독립 순수-코드 fix가 아님.
  추가 wiring 고려(step 4): 객관 per-move 채점은 GeminiTechniqueRecognizer 경유로만 활성화됨.
  FallbackRecognizer(Gemini off)는 motion_id=None + yaml 미경유라 데이터가 있어도 객관 경로에
  도달 못 함 → GEMINI_RECOGNIZER_ENABLED 보장 또는 non-Gemini path의 yaml 조회 배선 필요.

fix: |
  코드 fix 미적용 (goal=find_root_cause_only + 갭이 데이터-게이트). IPSF 요건 값 날조 금지.
  입력 명세(아래 ROOT CAUSE FOUND)를 step (3) NotebookLM 소싱 → step (4) 등록/배선으로 넘김.

verification: (해당 없음 — 진단 전용)

files_changed: []
