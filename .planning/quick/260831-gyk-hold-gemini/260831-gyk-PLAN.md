---
phase: quick-260831-gyk-hold-gemini
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/dimensions.py
  - backend/tests/test_dimensions.py
  - backend/tests/test_record_measured_at.py
  - .planning/quick/260831-gyk-hold-gemini/verify_hold_subwindow.py
  - .planning/quick/260831-gyk-hold-gemini/VERIFY.md
autonomous: true
requirements: []

must_haves:
  truths:
    - "파워스핀 정타 실데이터(0bc7aedf...)에서 Gemini 힌트 창 (54,90) 내부 안정 부창이 홀드 구간(약 68 이후)으로 이동해 무릎 평균 >= 170, leg_extension deficit < 20 → 위양성 감점 소멸 + line micro-bent 미발화"
    - "Gemini 국면 창의 목적(33-A4: 국면 밖 프레임 배제)은 유지 — 부창은 항상 힌트 창 내부 (s' >= s, e' <= e)"
    - "fault < correct 방향 보존 — 파워스핀 fault(0e53101b...)의 홀드 무릎 평균은 correct 보다 낮게 유지"
    - "backend pytest 0 failed — 기대값이 바뀌는 기존 테스트는 케이스별 정당화 주석과 함께만 변경"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/dimensions.py"
      provides: "_select_window 힌트-창-내부 안정 부창 재선택 (새 튜닝 상수 0)"
      contains: "hold_window(a[s:e])"
    - path: ".planning/quick/260831-gyk-hold-gemini/VERIFY.md"
      provides: "사전 박제 예측 + 실데이터 before/after 증거"
    - path: ".planning/quick/260831-gyk-hold-gemini/verify_hold_subwindow.py"
      provides: "Firestore 실데이터 재현 스크립트 (Pod 불필요)"
  key_links:
    - from: "backend/shared/python/sunity_shared/analysis/dimensions.py::_select_window"
      to: "backend/shared/python/sunity_shared/analysis/dimensions.py::hold_window"
      via: "힌트 창 슬라이스 a[s:e] 에 기존 분산-최소 로직 재적용 + s 오프셋"
      pattern: "hold_window\\(a\\[s:e\\]\\)"
    - from: "line_score / stability_score / extension_deviation / line_deficits_by_joint / stability_wobble_by_joint / safety_flags / pipeline._hold_window_median_dict"
      to: "_select_window"
      via: "기존 호출 그대로 — 함수 1개만 수정, 소비처 무접촉"
      pattern: "_select_window\\("
---

<objective>
Gemini 국면 창(hold moment ±2초)이 스핀 진입 전환부를 측정 창에 섞어 파워스핀 정타에
leg_extension -20 위양성 + line 0점을 만든 결함 수리 (belle 08-31 × 판정: "아니 쫙 펴져 있어").

수리 = Gemini 창을 "국면 힌트"로 강등: `_select_window` 가 profile.hold_window 를 그대로
쓰지 않고, 그 창 **내부에서** 기존 `hold_window`(분산 최소) 로직으로 안정 부창을 재선택한다.
새 튜닝 상수 0, 동작명 분기 0. 33-A4 국면 게이트 목적(국면 밖 프레임 배제)은 유지되고
hold_window docstring 의 정의("홀딩=동작이 완성돼 정지한 지점")가 창 내부에서 회복된다.

스코프 밖 (명시적 보류): `gemini_technique_recognizer._hold_window_from_moments` 의 fps 9.0
리터럴 수정. 안정 부창 재선택이 fps 오차를 완충하고, 리터럴 수정은 실효 fps 인자 배관
(_pipeline_frame_fps 경로)이 필요해 스코프가 넓어지며 검증 귀속을 흐린다 — 이번 수리 효과를
단일 변경에 귀속시키기 위해 보류. (memory fps-label-vs-actual 계열 함정으로 이미 박제됨)

Purpose: 파워스핀 정타 -20 위양성 제거 (Core Value = 분석 정확도, 고수 위양성 금지)
Output: dimensions.py `_select_window` 수정 + 테스트 정합 + 실데이터 증거 파일
</objective>

<context>
@.planning/quick/260831-gyk-hold-gemini/  (오케스트레이터 진단은 이 플랜 하단 <diagnosis> 참조)
@backend/shared/python/sunity_shared/analysis/dimensions.py
@backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
@backend/tests/test_dimensions.py
@backend/tests/test_record_measured_at.py
</context>

<diagnosis>
오케스트레이터 실측 (실행자는 Task 2 스크립트로 재확인 — 주장 승계 금지 규율):

1. Gemini 인식기 "hold=8.0초" → `_hold_window_from_moments` 단일 순간 ±2초 × fps 9.0
   리터럴 = 프레임 창 (54, 90).
2. 실제 국면: 프레임 54~67 = 스핀 진입 전환부 (무릎 55°~145° 변화), 68~ = 진짜 홀드
   (무릎 177~178° 유지, 최장 신전 연속 38프레임이 105에서 끝남).
3. `_select_window` 는 profile.hold_window 무조건 우선 → 창 (54,90) 평균 right_knee
   135.81° (감점 record measuredValue 와 소수점까지 일치, deficit 44.19 → over 24.19
   → raw -29 → cap -20).
4. 같은 평균이 line_score micro-bent 0-fail (평균 < 160°) 도 발화 → line 차원 0.
5. 자동 안정창 `hold_window` 는 (79,105) 를 골라 평균 171.6° — 정답을 내고 있었다.
   Gemini 창이 이를 덮어써 위양성 발생.

재현 재료 (Firestore 에 angles 저장, Pod 불필요):
- correct: users/QAN8VPwk4Oh13FMhTenphxYPdxH2/analyses/0bc7aedf1032474280d544a3a2ad418e
- fault:   users/8fPsUnXWNiOW9Y6cawCMcHGVb6z1/analyses/0e53101beff4433e90159334554ba893
- admin SA = 리포 루트 sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json,
  backend/.venv 에 firebase-admin 설치돼 있음.
- angles 는 Firestore nested-array 금지로 평탄 저장 (angles + anglesJointKeys +
  anglesFrames) → (T, J) 재구성 필요.
</diagnosis>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: _select_window 힌트-창-내부 안정 부창 재선택 + 테스트 정합</name>
  <files>backend/shared/python/sunity_shared/analysis/dimensions.py, backend/tests/test_dimensions.py, backend/tests/test_record_measured_at.py</files>
  <behavior>
    신규 테스트 (test_dimensions.py 에 추가, 구현 전 작성):
    - Test 1 (전환부 오염 차단): 합성 angles — 힌트 창 앞부분은 각도가 크게 변하는
      전환부, 뒷부분은 일정한 홀드. profile.hold_window 를 전체 힌트 창으로 설정.
      기대: 부창이 홀드 구간에 안착 (부창 평균이 홀드값에 근접, 전환부 프레임 배제).
    - Test 2 (포함 불변식): 어떤 입력이든 반환 (s', e') 는 clamp 된 힌트 창 내부
      — s' >= s, e' <= e, s' < e'. 33-A4 국면 게이트 목적 유지의 기계 증명.
    - Test 3 (WR-05 보존): clamp 후 s == e 인 빈 힌트 창은 종전대로 전체 자동
      hold_window 폴백 (기존 test_select_window_* 계열과 공존).
    - Test 4 (profile 없음 무변경): profile=None / hold_window=None 경로는 종전
      hold_window(a) 그대로 — byte-동일 결과.
  </behavior>
  <action>
    dimensions.py `_select_window` (L292-317) **한 함수만** 수정. profile.hold_window
    가 있고 clamp 후 s < e 이면, 종전처럼 (s, e) 를 그대로 반환하지 않고
    `ss, se = hold_window(a[s:e])` 로 힌트 창 내부 분산-최소 부창을 재선택해
    `(s + ss, s + se)` 를 반환한다. 부창 폭은 hold_window 의 기존 규칙
    w = max(2, min(t', t'//4)) (t' = 힌트 창 길이) 이 그대로 적용됨 — **새 튜닝 상수 0**
    (curve-fit 금지: 이 영상에 맞춘 임계 도입 금지). WR-05 (s == e → 전체 자동 폴백),
    profile 부재 경로는 무변경. 주석에 근거 인용: belle 08-31 × 판정(파워스핀 정타
    leg_extension -20 위양성), Gemini 창 = 국면 힌트 강등, 33-A4 국면 게이트 목적
    (국면 밖 프레임 배제) 유지. 동작명 분기 0, 파워스핀 전용 예외 금지.

    소비처 드리프트 확인 (수정 아님, 확인만): profile.hold_window 를 창 선택에 읽는
    곳이 `_select_window` 하나뿐인지 grep 재확인 — line_score, line_deficits_by_joint,
    stability_score, stability_wobble, stability_wobble_by_joint, extension_deviation,
    extension_representative_frame, line_representative_frame, safety_flags(3곳),
    pipeline._hold_window_median_dict 는 전부 `_select_window` 경유라 함수 1개 수정으로
    일관 적용된다. (gemini_technique_recognizer 는 창 생산자 — 무접촉.)

    기존 테스트 기대값 정합 — **케이스별 정당화 주석 필수, 정당화 안 되는 변경은 회귀**:
    - test_dimensions.py::test_select_window_uses_profile_when_set (L150):
      `(s,e) == (5,15)` 정확 일치 단언이 깨진다 (constant 포즈 → 분산 0 균일 → 첫
      부창 (5,7)). 새 기대 = 포함 불변식 (5 <= s' < e' <= 15) + 부창 폭 규칙. 정당화:
      profile 창은 이제 국면 힌트 상한이지 창 그 자체가 아님 (이 수리의 정의 변경).
    - test_dimensions.py::test_helpers_share_window_with_score_functions (L218):
      `sliced.shape[0] == 10` → 부창 폭 (w=2). 테스트 의도(점수 함수들과 창 공유,
      drift 0)는 그대로 성립 — shape 단언만 새 의미로 갱신.
    - test_record_measured_at.py L250-300 (hold_window=(2,5) 3건): fixture 가 창
      verbatim 사용을 전제로 전환부형 변동 프레임만 담고 있어 부창 재선택 시 동점
      타이브레이크에 걸린다. 각 테스트의 **의도**(집계값 최근접 순간 선택, argmax 아님,
      창 포함)를 보존하도록 fixture 를 조정 — 힌트 창 안에 안정 홀드 구간을 두어 부창이
      결정론적으로 안착하게 만든 뒤 기대값 재산출. 의도 자체를 바꾸는 변경 금지.
    - 그 외 파급 (phase10/conftest.py HOLD_WINDOW 소비 safety_flags 테스트,
      test_assemble_dimension_explanation.py, test_p1_objective_knee_decontamination.py):
      전체 스위트 실행으로 발견되는 실패만 케이스별 정당화와 함께 갱신. 주의:
      test_spike_measurement_trace*.py 의 hold_window 파라미터는 별개 함수 인자
      (trace API) — 무접촉.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests -q 2>&1 | tail -3</automated>
  </verify>
  <done>
    pytest 0 failed (기준선 4528 passed 대비 신규 테스트만큼 증가, 기존 실패 0).
    수정 diff 는 dimensions.py 의 _select_window 함수 하나 + 테스트 파일들뿐.
    바뀐 기대값마다 정당화 주석 존재.
  </done>
</task>

<task type="auto">
  <name>Task 2: 실데이터 사전 박제 검증 (파워스핀 correct/fault 페어)</name>
  <files>.planning/quick/260831-gyk-hold-gemini/verify_hold_subwindow.py, .planning/quick/260831-gyk-hold-gemini/VERIFY.md</files>
  <action>
    순서 엄수 — **예측을 먼저 박제하고 스크립트를 실행**한다 (memory: 사전 박제 장부,
    belle-eye-is-the-answer-key).

    1. VERIFY.md 에 예측 블록 먼저 작성 (스크립트 실행 전):
       - correct (0bc7aedf...): 힌트 창 (54,90) 에서 부창이 안정 구간(시작 >= 68 근방)
         으로 이동, right_knee 부창 평균 >= 170, leg_extension deficit < tol(20) →
         감점 0, line micro-bent(평균 < 160) 미발화.
       - fault (0e53101b...): 홀드 자체가 불안정 (무릎 148~169 요동) → 수리 후에도
         fault 의 홀드 무릎 평균 < correct 의 홀드 무릎 평균 (방향 보존). fault 에는
         split_angle·angle_vs_reference 등 다른 감점이 별도로 존재.

    2. verify_hold_subwindow.py 작성 (Pod 불필요, 순수 함수 + 저장 실데이터):
       - firebase-admin (backend/.venv, SA = 리포 루트
         sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json) 으로 두 doc 로드:
         users/QAN8VPwk4Oh13FMhTenphxYPdxH2/analyses/0bc7aedf1032474280d544a3a2ad418e
         users/8fPsUnXWNiOW9Y6cawCMcHGVb6z1/analyses/0e53101beff4433e90159334554ba893
       - 평탄 angles + anglesJointKeys + anglesFrames → (T, J) 재구성
         (Firestore nested-array 금지 규약, firestore_admin.complete_analysis 참조).
       - 힌트 창: doc 에 저장된 gemini 캐시(geminiB/geminiC)의 hold moments 에서
         `_hold_window_from_moments` 로 도출. 저장 형태에서 도출 불가하면 correct 는
         역산 확정치 (54,90) 사용하고 그 사실을 VERIFY.md 에 명기 (fault 도 동일 규칙).
       - 무릎 EXTEND profile (technique.TechniqueProfile, hold_window=힌트 창) 구성 후:
         (a) 수리 전 의미 재현 = 힌트 창 verbatim 평균 → correct right_knee 135.81
             재현 확인 (감점 record measuredValue 와 일치 — 기질 동일성 증명),
         (b) 수리 후 = dimensions._select_window 실호출 → 부창 (s',e'), 부창 평균,
             deficit, micro-bent 발화 여부, line_score 를 양쪽 영상에 대해 출력.
       - 예측 부등식들을 assert 로 박제, 결과 전문을 stdout 으로.
    3. 스크립트 실행, 출력 원문을 VERIFY.md 측정 블록에 추가 (예측 블록 수정 금지).
    4. FAIL 시 curve-fit 금지 — 정의를 비틀지 말고 FAIL 그대로 박제하고 보고.

    주의: uid/analysisId 는 이미 .planning 에 박제된 가명 식별자 — 스크립트 출력에
    그 외 PII(파일명 등 필요 최소 외) 미포함. SA 키 파일 경로만 참조, 내용 미출력.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python .planning/quick/260831-gyk-hold-gemini/verify_hold_subwindow.py && grep -c "예측" .planning/quick/260831-gyk-hold-gemini/VERIFY.md</automated>
  </verify>
  <done>
    VERIFY.md 에 예측 블록(스크립트 실행 전 작성)과 측정 블록(스크립트 출력 원문)이
    함께 존재. correct: 부창 평균 >= 170 + deficit < 20 + micro-bent 미발화 확인
    (또는 FAIL 원문 박제). fault: 방향 보존 (fault 홀드 평균 < correct) 확인.
    수리 전 재현치 135.81 일치로 기질 동일성 증명 포함.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 검증 스크립트 → Firestore Admin | 기존 admin SA 재사용 (신규 권한 0). 읽기 전용 사용 — 프로덕션 doc 쓰기 금지 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-gyk-01 | Information Disclosure | verify_hold_subwindow.py 출력 | mitigate | SA 키 내용·불필요 PII 미출력, 가명 uid/analysisId 만 (이미 .planning 박제된 식별자) |
| T-gyk-02 | Tampering | Firestore 프로덕션 doc | mitigate | 스크립트는 get 만 사용 — set/update 호출 0 (코드 리뷰로 확인) |
| T-gyk-SC | Tampering | 패키지 설치 | accept | 신규 설치 0 — backend/.venv 기존 firebase-admin/numpy 만 사용 |
</threat_model>

<verification>
- cd backend && .venv/bin/python -m pytest tests -q → 0 failed (기대값 변경은 전부 정당화 주석 동반)
- git diff 로 프로덕션 변경이 dimensions.py `_select_window` 단일 함수임을 확인
- VERIFY.md: 예측 → 측정 순서 보존, correct 위양성 소멸 + fault 방향 보존 (또는 FAIL 박제)
</verification>

<success_criteria>
- 파워스핀 정타 실데이터에서 leg_extension -20 위양성 소멸 + line micro-bent 미발화 (실측 증거 파일)
- Gemini 국면 창 목적 유지: 부창은 항상 힌트 창 내부 (테스트로 기계 증명)
- fault < correct 방향 보존
- 새 튜닝 상수 0, 동작명 분기 0, 소비처 코드 무접촉 (함수 1개 수정)
- backend pytest 0 failed
</success_criteria>

<output>
완료 시 `.planning/quick/260831-gyk-hold-gemini/260831-gyk-SUMMARY.md` 작성:
바뀐 테스트 목록 + 케이스별 정당화, VERIFY.md 판정 요지 (PASS/FAIL 원문),
fps 9.0 리터럴 보류 사실 명기 (후속 후보로 등재).
</output>
