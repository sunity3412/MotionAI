---
phase: quick-260831-bjj-belle-08-17-1
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/features.py
  - backend/tests/test_posture_axes.py
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/coach_writer.py
  - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
  - backend/tests/test_coach_writer.py
  - backend/tests/gemini/test_coach_writer_v2.py
  - .planning/quick/260831-bjj-belle-08-17-1/verify_peterpan_axes.py
  - .planning/quick/260831-bjj-belle-08-17-1/peterpan-axes-verdict.txt
autonomous: true
requirements: ["CONTINUE-2026-08-31 내일 첫 작업 #1 — belle 08-17 판독 축 구현"]

must_haves:
  truths:
    - "mode1 분석에서 상체 꼿꼿함·머리-척추 1자 축이 기준-학생 델타로 계산된다 (동작명 분기 0 — 모든 동작 공통)"
    - "유의미한 델타일 때만 양 coach writer(Cerebras+Gemini) 프롬프트에 인과형 한국어 지시가 들어간다 (수치는 보조)"
    - "피터팬 align.json 실데이터에서 belle 원문 방향('기준이 학생보다 상체 꼿꼿')과 같은 방향의 출력이 나온다 — 증거 파일 박제"
    - "기존 백엔드 테스트 4496개 무회귀 (0 failed)"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/features.py"
      provides: "head_spine_alignment_series / torso_uprightness_series / posture_axis_summary 순수 함수"
      contains: "def head_spine_alignment_series"
    - path: "backend/tests/test_posture_axes.py"
      provides: "새 축 단위 테스트 (합성 자세로 방향 검증)"
      min_lines: 60
    - path: "backend/functions/pipeline/app.py"
      provides: "mode1 배선 — ref joints3d 복원 + postureAxes coach_context 주입"
      contains: "postureAxes"
    - path: ".planning/quick/260831-bjj-belle-08-17-1/peterpan-axes-verdict.txt"
      provides: "피터팬 방향 검증 증거 (사전 박제 예측 + PASS/FAIL)"
  key_links:
    - from: "backend/functions/pipeline/app.py (_process mode1 분기)"
      to: "sunity_shared.analysis.features 새 축 함수"
      via: "_compute_posture_axes 헬퍼"
      pattern: "torso_uprightness_series|head_spine_alignment_series"
    - from: "backend/functions/pipeline/app.py (_build_coach_context)"
      to: "coach_writer.py + gemini/coach_writer_v2.py 프롬프트"
      via: "coach_context['postureAxes']"
      pattern: "postureAxes"
---

<objective>
belle 2026-08-17 판독 원문이 지목한 축 2종 — "상체 꼿꼿함"과 "머리-척추 1자" — 를
기존 좌표(COCO17 keypoints)로 계산하는 순수 함수로 구현하고, mode1 기준-학생 비교
델타를 양 coach writer 프롬프트에 인과형 한국어로 연결한다.

Purpose: CONTINUE-2026-08-31 Mode1 약점 #1 — "belle 이 실제로 보는 축이 코드에 없다.
전부 이미 가진 좌표로 계산 가능 — 데이터가 없는 게 아니라 식을 안 써놨다."
정답지 13일 방치를 코드로 옮기는 일. Pod 불필요, belle 결정 불필요.

Output: features.py 새 순수 함수 3개 + 단위 테스트, pipeline mode1 배선 +
coach_context `postureAxes` 키 + 양 writer 렌더, 피터팬 align.json 방향 검증 증거.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/CONTINUE-2026-08-31.md
@backend/shared/python/sunity_shared/analysis/skeleton.py
@backend/shared/python/sunity_shared/analysis/features.py
@backend/shared/python/sunity_shared/analysis/side_match.py

정본 근거 (belle 08-17 판독 원문, memory belle-readings-20260817-discovery):
- 피터팬: "오른팔 어깨가 딱 곧게 펴지면서 상체의 꼿꼿해짐이 전체적 영향을 미치고,
  오른쪽 다리의 접힘 — 이렇게가 전체적인 원인인 듯" (기준이 학생보다 상체 꼿꼿).
- elbow r02cand03: "고개 — 학생은 안 들어 머리카락이 오른팔 안쪽, 기준은 들어
  몸-머리가 1자라 바깥으로" (머리-척추 1자 축의 정의 근거).
- belle 판독은 전부 "부위 → 무엇을 해서 → 어떤 결과" 인과 형태. 코칭 문구도 이 형태.

사전 확정 사실 (오케스트레이터 실측 — 재탐색 불필요):
- 학생 keypoints: `inputs.keypoints_4ch` (T,17,4) — pipeline app.py `_process` 내 가용.
- 기준 keypoints: mode1 ref doc `ref["joints3d"]` + `ref["joints3dKeys"]` (flat,
  NaN→0.0 sentinel 저장 — side_match.py L59-61 규약, 전-0 triple = 무효).
  app.py L6980-6984 에서 side_match.grip_side 가 같은 재료를 소비하는 선례.
- coach 연결 지점: `_build_coach_context` (app.py L910) — Cerebras/Gemini 양 writer
  공유 단일 dict (B3 정합). 호출부 L7230. graceful None 선례 = bodyProfile/branch_info.
- 검증 데이터: .planning/phases/35-server-rendered-comparison-video/data/peterpan/align.json
  — refKp (129,34)=17관절×xy flat, userKp (91,34), refScore/userScore (T,17) 신뢰도,
  joints17 = skeleton.KEYPOINT_NAMES 와 동일 순서, 정규화 xy (y-down).
- 테스트 기준선: 4496 passed / 0 failed. 실행 = `cd backend && .venv/bin/python -m pytest tests`
  (시스템 python3 금지).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 자세 축 순수 함수 2종 + 요약 헬퍼 (features.py)</name>
  <files>backend/shared/python/sunity_shared/analysis/features.py, backend/tests/test_posture_axes.py</files>
  <behavior>
    - head_spine_alignment_series: 일직선 합성 자세(골반중점-어깨중점-귀중점 일렬) → ≈180°, 고개 숙인 자세(귀중점 이탈) → 180° 미만으로 감소
    - torso_uprightness_series: y-down 좌표에서 수직 척추(어깨 y &lt; 골반 y) → ≈0°, 수평 척추 → ≈90°, 도립(어깨 y &gt; 골반 y) → ≈180°
    - (T,17,2) 입력 == (T,17,3) z=0 입력과 결과 동일, (T,17,4) 는 4채널 무시
    - 정의 keypoint(귀/어깨/골반) 중 NaN 포함 프레임 → 해당 프레임 NaN (전파)
    - posture_axis_summary: nanmedian 기반 {studentDeg, referenceDeg, deltaDeg, significant}, delta=student-reference, |delta| &gt;= POSTURE_DELTA_SIGNIFICANT_DEG(5.0) 일 때만 significant=True, 한쪽이라도 유한값 0개면 None
  </behavior>
  <action>
    features.py 에 split_angle_series 선례와 같은 패턴(순수 numpy, NaN 전파,
    _angle_deg 재사용 — 중복 구현 금지)으로 추가한다:

    1. `head_spine_alignment_series(keypoints)` → (T,) 도.
       mid_hip=(left_hip+right_hip)/2, mid_shoulder=(left_shoulder+right_shoulder)/2,
       mid_ear=(left_ear+right_ear)/2. 프레임별 `_angle_deg(mid_hip, mid_shoulder, mid_ear)`
       — vertex=어깨중점, 180°=머리-척추 1자. 귀중점(코 아님)을 쓰는 근거 주석:
       코는 앞으로 돌출해 측면 각도에서 고개 판정을 왜곡, 귀중점이 머리 중심 근사
       (belle elbow r02cand03 원문 "고개를 들어 몸-머리가 1자" 인용).

    2. `torso_uprightness_series(keypoints, up=None)` → (T,) 도.
       척추 방향벡터 = mid_shoulder - mid_hip. up 기본값 (0,-1,0) — 이미지/카메라
       y-down 규약 (align.json 정규화 xy·RTMW 카메라 좌표 공통). 근거 주석 필수:
       절대값은 촬영 규약 의존이므로 제품 사용은 기준-학생 **델타**만 — 규약 오차는
       양쪽 동일해 상쇄, 도립에서도 양쪽 같은 규약이라 델타 비교 성립 (동작명 분기 0).
       각도는 `_angle_deg(spine_vec, zero, up_vec)` — vertex=원점 재사용
       (split_angle_series 선례). 0°=수직 꼿꼿, 커질수록 기울어짐.

    3. 입력 수용: 두 함수 모두 (T,17,2|3|4). 2채널이면 z=0 패딩 후 계산, 4채널이면
       불확실도 무시(:3). 기존 함수(split_angle_series 등)의 3채널 요구는 건드리지
       않는다 — 과잉 일반화로 기존 승인 항목 깨뜨리기 금지.

    4. `POSTURE_DELTA_SIGNIFICANT_DEG = 5.0` 모듈 상수. 근거 주석: RTMW 프레임 jitter
       는 수° 수준(window_median_angle_deltas 가 ±2프레임 median 으로 흡수하는 것과
       같은 계열) — 그 아래 델타는 잡음이라 코칭 지시로 승격하지 않는다. 실측 재조정 여지 명기.

    5. `posture_axis_summary(student_series, reference_series)` → dict|None.
       각 시계열 nanmedian (유한값 0개면 None 반환). delta = student - reference
       (frame_pair_angle_deltas 의 delta 부호 선례와 동일). significant =
       abs(delta) >= POSTURE_DELTA_SIGNIFICANT_DEG. median 선택 근거 주석: 자세 축은
       지속 품질 신호 — max_split 의 peak 논리와 반대로, 한 프레임 jitter 가 판정을
       오염시키지 않게 robust median.

    테스트는 backend/tests/test_posture_axes.py 신규 (test_split_angle.py 선례 참고,
    합성 keypoints 로 behavior 항목 전부 커버). 모듈 docstring 에 스펙 인용:
    belle 08-17 판독 (memory belle-readings-20260817-discovery), CONTINUE-2026-08-31 #1.
    이모지 금지.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_posture_axes.py tests/test_features.py tests/test_split_angle.py -q</automated>
  </verify>
  <done>새 함수 3종이 behavior 케이스 전부 통과, 기존 features/split_angle 테스트 무회귀, 2D/3D/4채널 입력 모두 수용.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: mode1 배선 + coach_context postureAxes + 양 writer 렌더</name>
  <files>backend/functions/pipeline/app.py, backend/shared/python/sunity_shared/analysis/coach_writer.py, backend/shared/python/sunity_shared/gemini/coach_writer_v2.py, backend/tests/test_coach_writer.py, backend/tests/gemini/test_coach_writer_v2.py, backend/tests/test_posture_axes.py</files>
  <behavior>
    - _reference_keypoints_coco17: flat joints3d + joints3dKeys → (T,17,3), KEYPOINT_NAMES 순서 재배열, 전-0 triple → NaN, 키 누락 관절 → NaN, malformed → None
    - _build_coach_context(posture_axes=...) → context["postureAxes"] 전달, 미전달 시 None (기존 키·프롬프트 불변)
    - Cerebras coach_writer: postureAxes 에 significant 축 있으면 프롬프트에 인과형 한국어 지시 포함, None/전부 insignificant 면 프롬프트 byte-불변
    - Gemini coach_writer_v2: 동일 규칙
  </behavior>
  <action>
    1. **app.py 헬퍼 2개** (mode1 분기 근처, side_match 관측 블록 L6966 선례와 같은 규율):
       - `_reference_keypoints_coco17(ref: dict)` → np.ndarray|None.
         ref["joints3d"](flat)+ref["joints3dKeys"] 를 (T,K,3) reshape 후
         skeleton.KEYPOINT_NAMES 순서로 재배열(이름→인덱스 매핑, 키 없는 관절은 NaN 행).
         **전-0 triple → NaN 복원** — joints3d 저장 sentinel 규약 주석 인용
         (side_match.py L59-61: "NaN→0.0 sentinel, 0,0,0 을 실좌표로 읽으면 오인").
         형상/키 malformed → None.
       - `_compute_posture_axes(keypoints_4ch, ref)` → dict|None.
         student = keypoints_4ch, reference = _reference_keypoints_coco17(ref).
         features.head_spine_alignment_series / torso_uprightness_series 각각 양쪽 계산,
         features.posture_axis_summary 로 요약 →
         `{"headSpine": {...}|None, "uprightness": {...}|None}`. 둘 다 None 이면 None.
         전체 try/except graceful (log.info + None 반환) — 코칭 보조 실패는 분석 중단
         금지 (side_match 관측 선례 규율, D-03 사후 점수 변경 0).

    2. **_process 배선**: `posture_axes = None` 을 mode 분기 전 초기화
       (reference_angles_for_veto L6804 선례와 같은 자리). mode1 분기에서 a_ref 확보
       지점(L7001-7007 부근) 직후 `posture_axes = _compute_posture_axes(inputs.keypoints_4ch, ref)`.
       mode3 는 None 유지 — 이 축은 belle 의 기준-학생 판독(08-17)이 근거라 기준 비교
       에서만 발화. 주석에 근거 명기. **점수 경로 진입 금지** — coach context 전달만
       (bodyProfile D-05 선례와 동일 규율).

    3. **_build_coach_context** (L910): kwarg `posture_axes=None` 추가 →
       `"postureAxes": posture_axes`. docstring 에 graceful 규칙 추가 (None 시 양
       writer 프롬프트 불변 — bodyProfile/branch_info 선례). 호출부 L7230 에 전달.

    4. **coach_writer.py (Cerebras)**: 프롬프트 조립부(context.get("joints") 소비
       지점)에 postureAxes 렌더 추가. 규칙:
       - significant=True 인 축만, 그리고 **학생이 나쁜 방향일 때만** 렌더
         (결함 코칭 목적 — 기준 우위 전제, 근거 주석):
         uprightness delta &gt; 0 (학생이 더 기울어짐) / headSpine delta &lt; 0 (학생이 덜 1자).
       - 문구는 인과형(부위 → 행동 → 결과), 수치는 "N° 정도" 보조 (memory
         how-illustration-arrow-and-number-grammar — "좁다" 식 상태 서술 금지):
         uprightness → "상체가 기준보다 {|delta|:.0f}° 정도 더 기울어져 있어요 —
         상체를 세워 꼿꼿하게 만들면 동작 전체 라인이 산다" 방향의 지시를 LLM 프롬프트에.
         headSpine → "고개를 들어 머리-척추가 1자가 되게" (belle elbow 원문 인용 주석).
       - postureAxes None/전부 미발화 → 프롬프트 byte-불변 (zero behavior change).
    5. **gemini/coach_writer_v2.py**: 같은 context 키·같은 발화 규칙으로 해당 프롬프트
       조립부에 렌더 (양 writer 단일 context 공유 B3 정합 — 발화 판정 로직이 두 곳에
       중복되지 않게, 판정에 쓰는 부호·significant 는 features.posture_axis_summary
       산출값만 소비).

    6. **테스트**: test_posture_axes.py 에 _reference_keypoints_coco17 sentinel→NaN·
       재배열 테스트(pipeline 모듈 로드는 기존 pipeline 테스트의 import 방식 선례 따름
       — grep "_build_coach_context" backend/tests/test_body_profile.py 가 passthrough
       테스트 선례). test_coach_writer.py / gemini/test_coach_writer_v2.py 에
       significant 시 프롬프트 포함·None 시 불포함 각 1건. 수치 채우기 금지 —
       의미있는 케이스만.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_posture_axes.py tests/test_coach_writer.py tests/gemini/test_coach_writer_v2.py tests/test_body_profile.py -q</automated>
  </verify>
  <done>mode1 에서 postureAxes 가 양 writer 프롬프트에 조건부 렌더되고, None 경로는 기존 프롬프트 byte-불변. 새 테스트 전부 pass.</done>
</task>

<task type="auto">
  <name>Task 3: 피터팬 실데이터 방향 검증 (사전 박제) + 전체 무회귀</name>
  <files>.planning/quick/260831-bjj-belle-08-17-1/verify_peterpan_axes.py, .planning/quick/260831-bjj-belle-08-17-1/peterpan-axes-verdict.txt</files>
  <action>
    검증 스크립트 verify_peterpan_axes.py 작성 (backend venv python 으로 실행,
    sys.path 에 backend/shared/python 추가):

    1. .planning/phases/35-server-rendered-comparison-video/data/peterpan/align.json 로드.
       refKp (129,34) / userKp (91,34) 를 (T,17,2) 로 reshape, joints17 ==
       skeleton.KEYPOINT_NAMES 순서 assert. refScore/userScore (T,17) 에서
       score &lt; 0.5 인 keypoint → NaN 마스킹 (conf&lt;0.5 게이트 선례 — memory
       angle-bake-blocked-by-confidence 주석 인용).
    2. 새 함수 2종을 2D 입력으로 호출, 양쪽 nanmedian + delta + significant 출력.
    3. **사전 박제 판정** (스크립트 상단 주석 + 출력에 명시, 실행 전 박제):
       belle 원문 "오른팔 어깨가 딱 곧게 펴지면서 상체의 꼿꼿해짐" → 예측 =
       **ref uprightness median &lt; user uprightness median** (기준이 더 꼿꼿).
       이 부등식 성립 = PASS. headSpine 은 관측만 출력 (피터팬 원문에 머리 축 없음
       — 그 축의 정답지는 elbow 건이라 방향 단정 금지, frames-before-numbers 규율).
    4. stdout 전문을 peterpan-axes-verdict.txt 로 저장 (증거 박제).
    5. **FAIL 시**: 정의를 데이터에 맞춰 비틀지 말 것 (curve-fit 금지,
       judgment-must-not-fixate-on-recent-fixture). FAIL 그대로 verdict 파일에 남기고
       SUMMARY 에 "완료 판정 미달 + 관측 수치" 로 보고 — 함수·배선은 유지.
    6. 전체 무회귀: `cd backend && .venv/bin/python -m pytest tests` — 기존 4496 +
       신규 전부 pass / 0 failed 확인.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260831-bjj-belle-08-17-1/verify_peterpan_axes.py && .venv/bin/python -m pytest tests -q</automated>
  </verify>
  <done>peterpan-axes-verdict.txt 에 사전 박제 예측 + 실측 수치 + PASS/FAIL 존재. 전체 테스트 0 failed (4496+ passed).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ref Firestore doc → pipeline | joints3d/joints3dKeys 는 백엔드가 쓴 값이나 형상은 방어적 파싱 (malformed → None graceful) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-quick-01 | Tampering/DoS | _compute_posture_axes | mitigate | 전체 try/except graceful — 코칭 보조 실패가 분석을 중단시키지 않음 (기존 side_match 관측 규율) |
| T-quick-SC | Tampering | 패키지 설치 | accept | 신규 패키지 설치 0건 — 순수 numpy·기존 의존만 |
</threat_model>

<verification>
- 새 단위 테스트 + 기존 4496 테스트 전부 pass (`cd backend && .venv/bin/python -m pytest tests`)
- 피터팬 align.json 방향 검증 PASS 증거 파일 존재
- postureAxes None 경로에서 양 writer 프롬프트 byte-불변 (테스트로 증명)
- 동작명 분기 0 (grep 으로 피터팬/elbow 등 동작명 문자열이 새 코드 경로에 없음)
</verification>

<success_criteria>
- belle 08-17 판독 축 2종이 순수 함수로 존재하고 단위 테스트로 방향이 증명됨
- mode1 기준-학생 델타가 양 coach writer 프롬프트에 인과형 한국어로 조건부 주입됨
- 피터팬 실데이터에서 "기준이 학생보다 상체 꼿꼿" 방향 출력 — 증거 박제
- 무회귀: 0 failed, Firestore 스키마 변경 0, 점수 경로 진입 0
</success_criteria>

<output>
Create `.planning/quick/260831-bjj-belle-08-17-1/260831-bjj-SUMMARY.md` when done
</output>
