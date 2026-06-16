---
phase: 13-llm-coaching-detail
plan: B
type: execute
wave: 2
depends_on: ["13-A"]
files_modified:
  - backend/data/motion_ipsf_map.json
  - backend/data/registered_move_angles.json
  - backend/shared/python/sunity_shared/analysis/assemble.py
  - backend/shared/python/sunity_shared/analysis/coach_writer.py
  - backend/functions/pipeline/app.py
  - backend/tests/phase13/test_dimension_explanation_ipsf_branch.py
  - backend/tests/phase13/test_motion_ipsf_map_coverage.py
  - backend/tests/phase13/test_build_result_branch_passthrough.py
  - backend/tests/phase13/test_coach_prompt_angle_fixture.py
  - backend/tests/phase13/test_branch2_forbidden_phrase_gate.py
autonomous: false
requirements: [PERS-03, studio-term-3branch-system]
user_setup:
  - service: cerebras
    why: "실 LLM 코칭(tip.detail2) 활성화 — criteria 5"
    env_vars:
      - name: CEREBRAS_KEY_PARAM
        source: "AWS Parameter Store SecureString (예: /sunity/motion/cerebras-key) — Lambda env + RunPod Pod env 둘 다 설정"
    dashboard_config:
      - task: "Cerebras API 키를 Parameter Store SecureString 으로 저장 후 Pod env 주입 + uvicorn 재시작"
        location: "AWS SSM Parameter Store + RunPod Pod"
must_haves:
  truths:
    - "실 영상 → 실 Cerebras → tip.detail2(causes/injuryRisk/coachNote) 가 Firestore 에 채워진다 (criteria 5, Pod 검증)"
    - "ipsfCode 등재 여부로 차원 자세히 카피가 분기된다 — 분기1 '세계 심사 기준(IPSF)+EXTEND 관절 180°' / 분기2 '정은지 선수 기준' (criteria 6)"
    - "coach 프롬프트가 동작별 IPSF/정은지 정의 각도(180° 가 아닌 값 포함)를 인용한다 (criteria 7)"
    - "분기2(학원 통용) 카피에 '세계 심사 기준' / '180°' 가 절대 나오지 않는다 (criteria 8)"
    - "REGISTERED_MOTIONS 의 모든 motion_id 가 motion_ipsf_map 에 의도적 분기 결정(또는 isRegistered:null 폴백 사유)을 가진다 (BLOCKER-1)"
  artifacts:
    - path: "backend/data/motion_ipsf_map.json"
      provides: "production motion_id → {ipsfCode|null, isRegistered, officialName, branch, sourceNote} 명시 curated join table (REGISTERED_MOTIONS 전수 cover)"
      contains: "isRegistered"
    - path: "backend/data/registered_move_angles.json"
      provides: "분기1 등재 동작별 IPSF 정의 각도 fixture — dimension 별(angle/line/stability) + 180°≠universal, NON-180 값 포함 (human-verify 후 lock)"
      contains: "Ayesha"
    - path: "backend/shared/python/sunity_shared/analysis/assemble.py"
      provides: "build_result + build_dimension_explanation 가 ipsf_code/is_registered 분기 pass-through"
      exports: ["build_result", "build_dimension_explanation"]
  key_links:
    - from: "backend/shared/python/sunity_shared/analysis/assemble.py"
      to: "motion_ipsf_map.json"
      via: "profile.motion_id → is_registered 분기 baseline (build_result → build_dimension_explanation 전달)"
      pattern: "is_registered"
    - from: "backend/shared/python/sunity_shared/analysis/coach_writer.py"
      to: "registered_move_angles.json / 정은지 criteria yaml"
      via: "_build_prompt(motion_name, branch, angle_fixture)"
      pattern: "angle_fixture"
---

<objective>
실 Cerebras LLM 을 활성화(Pod/SSM env, 코드는 이미 graceful)하고, 동작의 IPSF 등재 여부(`ipsfCode`)로 차원 자세히 카피를 분기한다 — 분기1(IPSF 등재) = "세계 심사 기준(IPSF) + 해당 동작에서 EXTEND 인 팔꿈치/무릎 180° 신전", 분기2(학원 통용 정은지 reference) = "정은지 선수 기준 자세". coach_writer 프롬프트에 동작 분기 + 동작별 정의 각도 fixture(180° 아닌 값 포함)를 주입해 LLM 이 정확한 각도를 인용하게 한다. (ROADMAP Phase 13 success criteria 5-8, D-05, studio-term-3branch-system 메모리, criteria 8 forbidden-phrase 게이트.)

Purpose: Phase 12.5 시뮬 한계(폭스탑 학원 용어 어색 + angle 차원 180° 명시 X)의 실 LLM 해결. 분석 정확도 = 신뢰.
Output: motion_ipsf_map.json(명시 curated join table) + registered_move_angles.json fixture(dimension 별, NON-180 포함) + assemble build_result/build_dimension_explanation 분기 pass-through + coach_writer 프롬프트 주입 + Cerebras OPS 활성화. 분기/프롬프트 로직은 순수(단위테스트), criteria 5 E2E 만 Pod.

Direct-review 박제: BLOCKER-1(motion_ipsf_map = derived 아닌 명시 curated join table, REGISTERED_MOTIONS 전수 cover + 폴백 명시) / HIGH-2(build_result pass-through 잠금 + 테스트) / HIGH-3(criteria 7 dimension 별 baseline, 180° 는 line/extension 전용, NON-180 fixture 테스트) / WARNING-1(branch-2 yaml 경로 double-prefix 금지) / WARNING-2(verify 명령 double cd 제거).
</objective>

<phase_goal>
**As a** 폴스포츠 수강생, **I want to** 분석 결과의 차원 설명과 코칭이 동작이 세계 심사 등재 동작인지(IPSF 동작별 정의 각도 기준) 학원 통용 동작인지(정은지 선수 기준)를 정확히 구분해 알려주길, **so that** 어색한 일반적 답변 대신 내 동작에 맞는 신뢰할 기준을 받는다.
</phase_goal>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/13-llm-coaching-detail/13-CONTEXT.md
@.planning/phases/13-llm-coaching-detail/13-RESEARCH.md
@.planning/phases/13-llm-coaching-detail/13-PATTERNS.md
@.planning/phases/13-llm-coaching-detail/13-VALIDATION.md
@.planning/phases/13-llm-coaching-detail/13-A-SUMMARY.md
@./CLAUDE.md
@./backend/CLAUDE.md
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 1 (checkpoint): 등재 동작 IPSF 정의 각도 fixture lock — belle/NotebookLM 재검증</name>
  <what-built>
    RESEARCH §"NotebookLM A" 표의 등재 동작(분기1) IPSF hold 각도 일부가 LLM-합성 값(RESEARCH Open Q1 / A4 — 예: Ayesha top shoulder ~110°, top elbow 20-30°)이라 fixture lock 전 재확인이 필요하다. 이 값들은 universal 180° 가 아니므로(HIGH-3) angle 차원 정의 각도로 정확히 박제해야 하며, 180° 로 덮어쓰면 안 된다. 분기2 정은지 측정 각도는 on-disk criteria yaml(`judging_data/criteria/ref-foxtop.yaml` extension_class: BENT_OK)에 이미 검증되어 재확인 불필요.
  </what-built>
  <how-to-verify>
    1. RESEARCH §"NotebookLM A" 표의 각 등재 동작(Ayesha / Iron X / Shoulder Mount / Inside Leg Hang(Scorpio) / Jade Split / Deadlift) joint별 각도를 검토 대상으로 제시. 특히 NON-180 값(Ayesha top shoulder ~110°, top elbow 20-30°)을 별도 표시 — 이 값은 angle 차원 정의 각도이지 신전 180° 가 아님.
    2. NotebookLM 노트북 96b061e8 ("IPSF Rules and Advanced Strength Pole Moves Guide")에 IPSF Code of Points 2024-2025 per-element 각도를 재query 하거나 belle 가 확인.
    3. 각 동작의 어깨/팔꿈치/무릎/split 각도 + tolerance 를 확정(또는 "범위로만 표기" 결정). 어느 joint 가 EXTEND(180° 신전) 이고 어느 joint 가 동작별 정의 각도(NON-180)인지 구분.
    4. 확정 값으로 `backend/data/registered_move_angles.json` 을 채울 수 있게 승인.
  </how-to-verify>
  <resume-signal>각 등재 동작 각도를 확정해 알려주거나(EXTEND joint=180° vs 동작별 정의 각도=NON-180 구분 포함), "RESEARCH §A 값 그대로 lock" / "범위 표기로 완화" 중 선택. 분기2(정은지)는 on-disk yaml 사용으로 재검증 불필요 — 확인만.</resume-signal>
</task>

<task type="auto">
  <name>Task 2: motion_ipsf_map(명시 curated join) + registered_move_angles fixture + assemble build_result/build_dimension_explanation 분기 pass-through + 분기2 forbidden-phrase 게이트</name>
  <files>backend/data/motion_ipsf_map.json, backend/data/registered_move_angles.json, backend/shared/python/sunity_shared/analysis/assemble.py, backend/tests/phase13/test_dimension_explanation_ipsf_branch.py, backend/tests/phase13/test_motion_ipsf_map_coverage.py, backend/tests/phase13/test_build_result_branch_passthrough.py, backend/tests/phase13/test_branch2_forbidden_phrase_gate.py</files>
  <read_first>
    - backend/data/aka-mapping.json (분기1 ipsfCode/isRegistered/ipsfOfficialName 소스 — 단 motionId 없음, display name 만) + backend/data/reference-motions-branch2.json (ref-foxtop = motionId + ipsfRegistered:false + championPersonalAlias 소스)
    - backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py L20-29 (REGISTERED_MOTIONS 5개 = ref-climb/ref-foxtop/ref-foxtop-split/ref-invert/ref-sideway-spin — join table cover 대상)
    - backend/shared/python/sunity_shared/analysis/assemble.py L28-130 (_DIMENSION_BASELINES_MODE1/3 + build_dimension_explanation signature + mode-aware baseline 선택) + L271-323 (build_result signature + 내부 build_dimension_explanation 호출 site)
    - .planning/phases/13-llm-coaching-detail/13-RESEARCH.md §"Plan B — ipsfCode branch" + §"ipsfCode Source" + §"NotebookLM A" 표(criteria 7 각도, NON-180 예시) + §"Common Pitfalls Pitfall 2/3"
    - backend/shared/python/sunity_shared/analysis/force_pattern_copy.py (FORBIDDEN_PHRASES_PHASE9_REGEX grep 게이트 precedent — STATE Plan 09-02 close-out)
    - Task 1 checkpoint 에서 확정된 등재 동작 각도
  </read_first>
  <action>
    **BLOCKER-1: `backend/data/motion_ipsf_map.json` = 명시 curated join table(derived 금지), production `motion_id` 로 keyed**: `{ "<motion_id>": {"ipsfCode": str|null, "isRegistered": bool|null, "officialName": str, "branch": "branch1"|"branch2"|"unknown", "sourceNote": str} }`. **REGISTERED_MOTIONS 5 id 전수 cover, 각 id 마다 의도적 branch 결정 + sourceNote**:
      - `ref-foxtop` → branch2, isRegistered:false, ipsfCode:null (sourceNote = reference-motions-branch2.json ref-foxtop ipsfRegistered:false).
      - `ref-foxtop-split` / `ref-invert` / `ref-climb` / `ref-sideway-spin` → 각각 branch1/branch2/unknown 명시 결정 + sourceNote(어떤 aka-mapping ipsfOfficialName 또는 branch2 근거인지, 또는 IPSF 미확인 시 unknown + isRegistered:null). aka-mapping.json 은 motionId 가 없으므로 display name 추론 금지 — 각 결정을 sourceNote 에 근거로 박제.
    **is_registered=None 폴백 EXPLICIT**: pipeline 은 motion_ipsf_map lookup 으로 실제 값을 공급한다. motion_id 가 map 에 없으면(미등록 신규) lookup 이 `isRegistered=None` 을 반환 → build_dimension_explanation 이 기존 mode-aware baseline(_DIMENSION_BASELINES_MODE1/3)을 의도적 폴백으로 사용(silent old-copy 아니라 문서화된 폴백). 이 동작을 motion_ipsf_map.json 헤더 + assemble docstring 에 박제.
    `backend/data/registered_move_angles.json` 신설: Task 1 에서 확정된 분기1 등재 동작별 IPSF 정의 각도. **HIGH-3: dimension 별로 분리 + 180°≠universal** — joint 별 `{angle, tolerance, fault, isExtension:bool}`, EXTEND joint 만 180°(isExtension:true), 동작별 정의 각도(예: Ayesha top shoulder ~110°, top elbow 20-30°)는 isExtension:false 로 실제 값 박제. content = checkpoint 승인 값(임의 생성 금지). 헤더에 source(NotebookLM 96b061e8 + belle 확정일) 박제.
    `assemble.py`:
      - **build_dimension_explanation 에 backward-compatible kwarg `ipsf_code: str | None = None, is_registered: bool | None = None` 추가**(joint_angles/profile 가 12.5 에서 추가된 방식 그대로 — 기존 호출자/None 동작 불변). 분기 baseline (HIGH-3: dimension 별):
        - `is_registered is True` → 분기1 baseline dict. **angle 차원 = "IPSF 동작별 정의 각도"**(180° universal 아님), **line 차원 = "IPSF 신전 기준, 해당 동작에서 EXTEND 인 팔꿈치/무릎은 180°"**(180° 는 line/extension 전용 카피), **stability 차원 = "hold 구간 안정성"**.
        - `is_registered is False` → 분기2 baseline dict ("정은지 선수 기준 자세") — **"세계 심사 기준" / "180°" 절대 미포함**.
        - `is_registered is None` → 기존 mode-aware baseline(_DIMENSION_BASELINES_MODE1/3) = 의도적 하위호환 폴백(FallbackRecognizer / motion_id 미등록, Pitfall 3).
      - **HIGH-2: build_result 에 `ipsf_code: str | None = None, is_registered: bool | None = None` kwarg 추가하고 내부 `build_dimension_explanation(...)` 호출(L317)에 두 kwarg 를 forward.** build_result 가 실제로 build_dimension_explanation 을 호출하는 함수이므로, 여기서 pass-through 가 끊기면 pipeline 분기가 무효. 기존 호출자/None 동작 불변.
    ipsf_code/is_registered 해석: 작은 헬퍼 `lookup_motion_ipsf(motion_id: str | None) -> tuple[str | None, bool | None]`(또는 call site)에서 motion_ipsf_map.json 을 profile.motion_id 로 lookup, 미존재 시 (None, None). **motion_ipsf_map 은 TechniqueProfile 채점 경로에 추가하지 않음(objectivity / D-05) — 카피 분기 전용.**
    `test_dimension_explanation_ipsf_branch.py`: is_registered True → angle 차원 카피가 "IPSF 동작별 정의 각도" 포함 + line 차원에 "180°" 포함(angle 차원 카피에는 universal 180° 미포함), False → "정은지 선수 기준" 포함 + "세계 심사 기준" 미포함, None → 기존 mode-aware baseline 동일(회귀).
    **`test_motion_ipsf_map_coverage.py`(신규, BLOCKER-1): REGISTERED_MOTIONS 를 iterate 하며 각 motion_id 가 motion_ipsf_map 에 entry 보유 OR 의도적 isRegistered:null 폴백 사유(sourceNote)를 가짐을 assert.** 신규 id 누락을 fail-closed.
    **`test_build_result_branch_passthrough.py`(신규, HIGH-2): `assemble.build_result(..., is_registered=False)` 호출 → `result["dimensionExplanation"]` 가 분기2 카피("정은지 선수 기준")를 받음을 assert + is_registered=True → 분기1 카피.** build_dimension_explanation 직접 테스트로는 불충분(pipeline 이 build_result 경유이므로 pass-through 가 끊기면 분기 무효).
    `test_branch2_forbidden_phrase_gate.py`: FORBIDDEN_PHRASES regex(`세계 심사 기준` / `180°` / `180도`)로 분기2 모든 baseline 카피 스캔 — 0 hit 강제(criteria 8). precedent FORBIDDEN_PHRASES_PHASE9_REGEX.
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/phase13/test_dimension_explanation_ipsf_branch.py tests/phase13/test_motion_ipsf_map_coverage.py tests/phase13/test_build_result_branch_passthrough.py tests/phase13/test_branch2_forbidden_phrase_gate.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - motion_ipsf_map.json 이 REGISTERED_MOTIONS 5 id 전수 cover, 각 id 마다 명시 branch 결정 + sourceNote (derived 아님, BLOCKER-1)
    - is_registered=None 폴백이 헤더/docstring 에 문서화된 의도적 폴백 (silent old-copy 아님)
    - registered_move_angles.json content = Task 1 승인 값(임의 생성 0) + NON-180 값(isExtension:false) 포함 (HIGH-3)
    - build_dimension_explanation angle 차원 카피 = 동작별 정의 각도, line 차원만 180° 사용 (HIGH-3)
    - build_result 가 ipsf_code/is_registered 를 build_dimension_explanation 으로 forward (HIGH-2)
    - test_motion_ipsf_map_coverage / test_build_result_branch_passthrough / test_dimension_explanation_ipsf_branch / test_branch2_forbidden_phrase_gate 모두 그린
    - 분기2 카피에 "세계 심사 기준"/"180°" 0회 (forbidden-phrase 게이트)
  </acceptance_criteria>
  <done>명시 motion_ipsf_map join + build_result pass-through + dimension 별 등재 각도 fixture 박제 (criteria 6,7-fixture,8 + BLOCKER-1 + HIGH-2 + HIGH-3).</done>
</task>

<task type="auto">
  <name>Task 3: coach_writer 프롬프트 동작명/분기/정의각도 주입 + assemble 분기 pipeline wiring</name>
  <files>backend/shared/python/sunity_shared/analysis/coach_writer.py, backend/functions/pipeline/app.py, backend/tests/phase13/test_coach_prompt_angle_fixture.py</files>
  <read_first>
    - backend/shared/python/sunity_shared/analysis/coach_writer.py L18-30 (_SYSTEM) + L49-86 (_build_prompt joints 라인 빌더) + L107-143 (write context→prompt)
    - backend/functions/pipeline/app.py L738-785 (_build_coach_context — joints/mode/bodyProfile 키) + L1819-1862 (_COACH_WRITER.write 호출 + assemble.build_result 진입) + L1862-1876 (build_result 호출 site — ipsf_code/is_registered 전달 지점) + L1900-1950 (profile.motion_id 가용 위치)
    - backend/data/registered_move_angles.json (Task 2 산출 — 분기1 각도) + backend/judging_data/criteria/ref-foxtop.yaml (분기2 정은지 측정 각도, extension_class BENT_OK — 파일명이 이미 ref- 로 시작)
    - .planning/phases/13-llm-coaching-detail/13-RESEARCH.md §"Plan B — IPSF angle fixture → coach prompt" + §"Real Cerebras activation path"
  </read_first>
  <action>
    coach_writer.py: `_build_prompt` signature 확장 — `_build_prompt(joints: list[dict], motion_name: str | None = None, branch: str | None = None, angle_fixture: dict | None = None) -> str`(기본 None = 기존 동작 불변). joints 편차 라인은 유지하고, angle_fixture 가 있으면 동작별 정의 각도("아이샤 아래 어깨 180°, 위 어깨 110°" 식 — 180° 와 NON-180 값 모두)를 user 프롬프트에 prepend(LLM 이 정확한 각도 인용, 180° 로 환원 금지). `_SYSTEM` 에 한 줄 가드 추가: "정확한 기준 각도만 인용하고 임의 수치를 생성하지 않으며, 동작별 정의 각도를 180° 로 일반화하지 않는다". write(context) 가 context 의 `motionName`/`branch`/`angleFixture` 를 읽어 `_build_prompt` 로 전달(없으면 None graceful).
    pipeline app.py: `_build_coach_context` 에 `motion_name`/`branch`/`angle_fixture` 주입 — profile.motion_id 로 motion_ipsf_map lookup → is_registered 결정 → branch="registered"/"branch2", angle_fixture = registered_move_angles.json(분기1) 또는 **분기2 정은지 측정각 yaml**.
    **WARNING-1: 분기2 yaml 경로 double-prefix 금지** — helper `criteria_path = criteria_dir / f"{motion_id}.yaml"` (motion_id 는 이미 `ref-` 로 시작하므로 절대 `ref-` 를 prepend 하지 않음 → `ref-ref-foxtop.yaml` 금지). 즉 `motion_id="ref-foxtop"` → `criteria/ref-foxtop.yaml`.
    **HIGH-2 wiring: build_result 호출 site(app.py L1862-1876)에 motion_ipsf_map lookup 결과의 실제 ipsf_code/is_registered 를 전달** — `ipsf_code, is_registered = lookup_motion_ipsf(getattr(profile, "motion_id", None))` 후 `assemble.build_result(..., ipsf_code=ipsf_code, is_registered=is_registered)`. motion_id 미존재 시 (None, None) 전달(의도적 baseline 하위호환 폴백).
    `test_coach_prompt_angle_fixture.py`:
      - _build_prompt(joints, motion_name="아이샤", branch="registered", angle_fixture={...NON-180 포함...}) 결과 문자열에 정의 각도 인용 포함 + angle_fixture=None 시 기존 프롬프트와 동일(회귀). _SYSTEM 에 "임의 수치" + "180° 일반화 금지" 가드 라인 존재 검증.
      - **HIGH-3 NON-180 fixture 테스트: angle_fixture 에 NON-180 등재 각도(예: top shoulder 110° 또는 top elbow 20-30°) 포함 → 프롬프트가 그 값을 그대로 인용하고 180° 로 치환하지 않음을 assert.** criteria-6 substring 테스트가 "180°" 에 over-focus 하지 않도록 별도 NON-180 검증.
      - **WARNING-1 branch-2 경로 테스트: real `motion_id="ref-foxtop"` 로 criteria 로드 → `criteria/ref-foxtop.yaml` 에서 각도가 로드됨을 확인(`ref-ref-foxtop.yaml` 시도 0).**
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/phase13/test_coach_prompt_angle_fixture.py -x -q && python -m pytest tests/phase13 -q</automated>
  </verify>
  <acceptance_criteria>
    - _build_prompt 가 motion_name/branch/angle_fixture 주입 시 정의 각도(NON-180 포함) 인용, None 시 기존 프롬프트와 동일(회귀)
    - _SYSTEM 에 임의 수치 생성 금지 + 180° 일반화 금지 가드 라인 존재
    - 분기2 yaml 경로가 `criteria/{motion_id}.yaml`(ref- 중복 prepend 0), ref-foxtop 실 로드 테스트 그린 (WARNING-1)
    - pipeline 이 motion_ipsf_map lookup → coach_context + build_result(→build_dimension_explanation) 양쪽에 분기 전달 (HIGH-2 wiring)
    - NON-180 fixture 테스트 그린 (HIGH-3)
    - phase13 전 테스트 그린
  </acceptance_criteria>
  <done>coach 프롬프트 각도 주입(NON-180 포함) + build_result 분기 pipeline wiring + branch-2 yaml 경로 정정 (criteria 7 + HIGH-2 + HIGH-3 + WARNING-1/2).</done>
</task>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 4 (checkpoint): criteria 5 — 실 Cerebras E2E (Pod 활성화 + 1건 실분석)</name>
  <what-built>
    coach_writer 실 Cerebras 호출은 코드상 이미 graceful(키 unset → {} → 수치 폴백). 활성화 = OPS: (1) SSM SecureString 에 Cerebras 키 저장, (2) Lambda env `CEREBRAS_KEY_PARAM` 설정, (3) RunPod Pod env `CEREBRAS_KEY_PARAM` 주입 + uvicorn 재시작(모듈 캐시 _COACH_WRITER 가 첫 _process 에서 생성되므로 재시작으로 새 env pickup). `GEMINI_COACH_ENABLED` 는 OFF 유지(Cerebras-only else 분기). 실 _process 는 Lambda 가 아니라 Pod 에서 돈다 — Pod env 누락 시 production 에서 detail2 빈 채로 남음(RESEARCH Pitfall 1). 이 단계는 Pod 필요 — pod-ops-claude-runs 메모리대로 Claude 가 Pod SSH/env/uvicorn/E2E 실행, belle 는 production 승인.
  </what-built>
  <how-to-verify>
    1. SSM SecureString 생성(예: `/sunity/motion/cerebras-key`) + Lambda env CEREBRAS_KEY_PARAM 설정(aws lambda update-function-configuration / SAM).
    2. RunPod Pod env CEREBRAS_KEY_PARAM 주입 + uvicorn 재시작 → `/health` 가 auth_configured:true, pipeline_loaded:true 보고.
    3. `python -c "import cerebras.cloud.sdk"` 로 Pod 에 dep 존재 확인.
    4. 실 영상 1건 분석 실행 → Firestore doc 의 `result.tips[].detail2`(causes/injuryRisk/coachNote) 채워짐 확인(빈 dict 아님).
    5. 분기2(폭스탑, motion_id=ref-foxtop) 동작 1건으로 차원 자세히 카피가 "정은지 선수 기준" + "세계 심사 기준" 미포함 확인(criteria 6/8 실 검증).
  </how-to-verify>
  <resume-signal>Firestore doc 의 tips[].detail2 가 실 LLM 으로 채워졌고 분기2 카피에 "세계 심사 기준" 없음을 확인하면 "approved", 문제 있으면 증상 기술.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Cerebras API key (SSM) → coach_writer | SecureString 비밀이 Lambda/Pod env 경유로 LLM 클라이언트에 주입 |
| motion name / BodyProfile → Cerebras 프롬프트 | 동작명·자가입력 컨텍스트가 LLM user 프롬프트로 흐름 |
| LLM 출력(tip.detail2) → Firestore → 결과 화면 | 생성 코칭 문장이 사용자에게 노출 |
| motion_ipsf_map.json → assemble 분기 | 명시 curated join 이 카피 분기 결정 (채점 경로 미진입) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-13B-01 | Information Disclosure | Cerebras 키 누출 | mitigate | SSM SecureString WithDecryption + `_load_api_key` except 가 키 값 미로깅(코드 기존), .env/코드 하드코딩 금지 (CLAUDE.md §3) |
| T-13B-02 | Tampering (prompt injection) | motion_name 으로 LLM 프롬프트 주입 | mitigate | motion_name 은 통제된 recognizer enum(REGISTERED_MOTIONS / motion_ipsf_map 키)에서만, 자유 사용자 텍스트 아님 |
| T-13B-03 | Tampering (분기 오류) | 분기2 동작이 180°/세계 심사 카피 받음 | mitigate | motion_ipsf_map isRegistered 게이트 + build_result pass-through(HIGH-2) + test_branch2_forbidden_phrase_gate.py (criteria 8 hard 게이트) |
| T-13B-04 | Information Disclosure / 의료 단정 | LLM injuryRisk 출력 | accept | injuryRisk 는 tip.detail2 한 줄 LLM 출력 수준 유지(SAFE 본격 UI = v2), 진단·치료 단정 아님 (D-05 / Deferred) |
| T-13B-05 | Tampering (objectivity) | ipsf_code 가 채점 경로 유입 | mitigate | motion_ipsf_map 은 카피/프롬프트 분기 전용 — TechniqueProfile scoring 경로 미추가 (objectivity / D-05) |
| T-13B-06 | Tampering (각도 환원) | 등재 동작 NON-180 정의 각도가 universal 180° 로 덮임 | mitigate | registered_move_angles isExtension 구분 + dimension 별 baseline(HIGH-3) + NON-180 fixture 테스트 (criteria 7) |
| T-13B-SC | Tampering | npm/pip installs | mitigate | Phase 13 신규 install 0 (cerebras-cloud-sdk 기존 dep, RESEARCH Package Legitimacy Audit informational) — slopcheck 불필요 |
</threat_model>

<verification>
- `cd backend && python -m pytest tests/phase13 -q` (Plan B 단위 테스트 그린 — 분기/프롬프트/forbidden-phrase/coverage/pass-through)
- `cd backend && python -m pytest -q` (회귀 0 — phase06/07/08/08.1/09/12.5 그린, build_result/build_dimension_explanation None 하위호환)
- criteria 5: **Pod E2E (Task 4 checkpoint)** — 단위테스트로 검증 불가, Pod + Cerebras 키 필요. Pod 없이 PASS 주장 금지.
- 분기2 forbidden-phrase 게이트 0 hit (criteria 8)
- REGISTERED_MOTIONS 전수 motion_ipsf_map cover (BLOCKER-1)
- build_result is_registered=False → 분기2 카피 pass-through (HIGH-2)
- NON-180 등재 각도 인용 보존 (HIGH-3)
</verification>

<success_criteria>
- 실 Cerebras tip.detail2 가 Firestore 에 채워짐 — criteria 5 (Pod 검증)
- ipsfCode 분기1/분기2 카피 분리 — criteria 6
- coach 프롬프트가 동작별 정의 각도(NON-180 포함) 인용 — criteria 7
- 분기2 카피에 "세계 심사 기준"/"180°" 0 — criteria 8
- motion_ipsf_map 명시 join + REGISTERED_MOTIONS 전수 cover — BLOCKER-1
- build_result pass-through + None 하위호환 + 회귀 0 — HIGH-2
</success_criteria>

<output>
Create `.planning/phases/13-llm-coaching-detail/13-B-SUMMARY.md` when done
</output>
</content>
