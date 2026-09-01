---
phase: quick-260901-vlu
quick_id: 260901-vlu
slug: machine-eye-occlusion-fp
date: 2026-09-01
status: planned
description: 기계 눈(machine_eye) 오클루전 위양성 수리 — 다른 사지가 기대 관절을 가리면 limb 상충 FAIL 로 확정 확대비교 카드가 삭제되는 것을, 기대 사지 명시 질문(_CLAIM_QUESTION 의 expected_limb 반영형)으로 교정. belle 2026-09-01 "반드시 잡아야지" 승인. 마크-전위 차단(ii0 §6-3)은 1급 무회귀.
wave: 1
depends_on: []
type: execute
plan: 01
autonomous: true
requirements: [BELLE-EYE-OCCLUSION-FP]
files_modified:
  - backend/shared/python/sunity_shared/analysis/card_gates.py
  - backend/tests/test_card_gates.py
  - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/eye_ledger.json
  - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/eye_crop.png
  - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/stage1_confirmed_card.png
  - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/run_live_eye.py
  - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/live_eye_results.json
  - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/live_eye_run.log
  - .planning/quick/260901-vlu-machine-eye-occlusion-fp/260901-vlu-SUMMARY.md

must_haves:
  truths:
    - "expected_limb 가 'arm'|'leg' 인 bent/extended claim 에서 기계 눈 질문이 '판정 대상 = 원 위치의 기대 사지, 다른 사지에 가려져 뒤에 있어도 그 사지를 판정'을 명시한다. expected_limb=None 과 off_pole claim 의 질문은 오늘과 문자 단위 동일 (하위호환 — 질문 무변경)"
    - "오클루전 라이브 재판정: belle 실물 크롭(evidence/eye_crop.png — uid csKWYvI3WCPYPysNQ9KkWecaUvq1 / ea975e6e83374564a7803ca31aefa46b, right_knee 3.0s)이 새 프롬프트 Gemini 실호출에서 match=True 로 전환. 증거 = 실행 로그 + 결과 JSON (통과 주장은 실행 로그로 — wiring-claims-need-log-evidence)"
    - "마크-전위 라이브 회귀: ii0 kneepath 실물 크롭(.planning/quick/260811-ii0-card-gates-5/evidence/eye_kneepath_user_left_knee.png — 무릎 마크가 굽은 팔 위, 기대 사지 부재)이 새 프롬프트에서도 match=False 유지. 이 회귀가 깨지면 수리 반려 — 오클루전 PASS 보다 우선하는 1급"
    - "_eye_verdict 의 arm↔leg 확정 상충 차단은 diff 0 (ii0 §6-3 지정 수리 무접촉). 질문·코드 어디에도 좌/우 해부학 이름(왼/오른/left/right) 0"
    - "pytest 무회귀: cd backend && .venv/bin/python -m pytest tests 가 failed=0, passed>=4537 (신규 테스트 증가분만 허용, 시스템 python3 금지)"
    - "채점 로직 무접촉 (이 수리는 표시 게이트의 질문/판정만). app.py 무접촉 — expected_limb 는 app.py:4754 에서 이미 전달되고 있어 배선 변경 불필요. 모델 문자열 하드코딩 0 — DEFAULT_C_MODEL(gemini/config.py) 경유 유지"
    - "scratchpad(휘발) 재현 자산 중 보존 필요분 3건(eye_ledger.json / eye_crop.png / stage1_confirmed_card.png)이 evidence/ 로 복사 박제됨"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/card_gates.py"
      provides: "_claim_question(claim, expected_limb) 질문 조립 순수 함수 + eye_judge(마킹 크롭 입력 판정 진입점) + machine_eye 배선"
      contains: "_claim_question"
    - path: "backend/tests/test_card_gates.py"
      provides: "질문 조립 불변식 테스트 (하위호환 byte-동일 / 기대 사지 명시 / 좌우 이름 0 / off_pole 무변경)"
      contains: "_claim_question"
    - path: ".planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/live_eye_results.json"
      provides: "라이브 재판정 결과 — caseA(오클루전) match=true, caseB(마크-전위) match=false"
    - path: ".planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/live_eye_run.log"
      provides: "Gemini 실호출 실행 로그 (판정 근거 reason 원문 포함)"
  key_links:
    - from: "backend/shared/python/sunity_shared/analysis/card_gates.py::machine_eye"
      to: "_claim_question"
      via: "질문 조립 호출 (기존 _CLAIM_QUESTION[claim] 직참조 대체)"
      pattern: "_claim_question\\("
    - from: "backend/functions/pipeline/app.py:4752-4755"
      to: "card_gates.machine_eye(expected_limb=cg.joint_limb(...))"
      via: "기존 호출 그대로 — expected_limb 인자가 이미 흐르고 있어 새 질문이 자동 활성 (app.py diff 0 이 곧 배선 증거)"
      pattern: "expected_limb=cg\\.joint_limb"
    - from: "evidence/run_live_eye.py"
      to: "card_gates.eye_judge"
      via: "하네스는 card_gates 경유만 — 프롬프트/스키마 재구현 금지 (운영 코드 경로 그대로 검증)"
      pattern: "eye_judge\\("
---

<objective>
기계 눈(A3 게이트)의 오클루전 위양성 수리. belle 실 분석(mode1 92점)에서 정상 생성된
확정 확대비교 카드(right_knee, 3.0s)가, "뻗은 팔이 굽힌 무릎 앞을 가로지르는" 프레임을
눈이 limb=arm 마크-전위로 오판(관측 재현 완료 — 재조사 금지)해 삭제됐다. 원인은
`machine_eye` 가 `expected_limb` 를 인자로 받으면서 **프롬프트에는 쓰지 않는** 것:
눈이 "원 위치에서 가장 앞에 보이는 사지"를 답하면 2단 판정이 상충 차단한다.

수리 = 질문을 expected_limb 반영형으로 교정 (판정 대상 사지를 명시하고, 가려져 뒤에
있어도 그 사지를 판정하게). `_eye_verdict` 의 arm↔leg 상충 차단(ii0 §6-3)은 무접촉 —
마크-전위 케이스(기대 사지가 그 자리에 아예 없음)는 여전히 FAIL 이어야 한다.

Purpose: 확정 카드가 오클루전 프레임에서 사라지는 앱 표면 결함 제거 (belle 승인 건).
Output: card_gates.py 질문 조립 수리 + 단위 테스트 + 라이브 양방향 재판정 증거 박제.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/shared/python/sunity_shared/analysis/card_gates.py
@backend/tests/test_card_gates.py
@.planning/quick/260811-ii0-card-gates-5/260811-ii0-SWEEP-REPORT.md

재현 완료 사실 (planning_context 원문 — 재조사 금지):
- 확정 카드는 정상 생성 후 compare_render 사후 카드 게이트에서 눈 FAIL 로 삭제됨.
- 눈 원장: joint=right_knee, claim="bent", observed="extended", limb="arm", match=false,
  conf 0.95, reason "The orange circle marks the elbow joint of the arm that is
  horizontally outstretched" — 원 위치는 맞고, 팔 뒤의 무릎이 명백히 보이는 프레임.
- 재현 자산 = scratchpad fzrepro/ (휘발): analysis_doc.json, user.mp4, ref.mp4,
  stage1_confirmed_card.png, eye_crop.png, eye_ledger.json, repro_stage1.py.
  경로: /private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/18afea29-d548-43ec-bf72-08bbe3512370/scratchpad/fzrepro/

코드 좌표 (실측 확인됨):
- card_gates.py:428 `_CLAIM_QUESTION` — 현행 질문 3종. 좌우 해부학 이름 금지 주석 유지.
- card_gates.py:454 `_eye_verdict` — 2단 판정. **무접촉.**
- card_gates.py:490 `machine_eye` — expected_limb 인자 수신, 프롬프트 미사용. 수리 지점.
- app.py:4752-4755 — `expected_limb=cg.joint_limb(gate_joint)` 이미 전달 중. **app.py 무접촉.**
- app.py:5080-5086 대체 부착 로직 — 범위 밖, 무접촉.
- 눈 원장 스키마(claim/observed/limb/match/...)는 harvest_eye.py(Phase22 수확기)가 소비 —
  필드 무변경이므로 영향 0 (확인됨).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: _claim_question 기대-사지 반영형 질문 조립 + eye_judge 추출 + 단위 테스트</name>
  <files>backend/shared/python/sunity_shared/analysis/card_gates.py, backend/tests/test_card_gates.py</files>
  <behavior>
    신규 테스트 (test_card_gates.py — 기존 합성 트랙/순수 함수 관례 유지, 네트워크 mock 불필요.
    프롬프트 전문(全文) 일치가 아니라 **안정 불변식**만 단정할 것 — Task 2 의 문구 반복
    여지를 남긴다):
    - 하위호환: `_claim_question("bent", None) == _CLAIM_QUESTION["bent"]`,
      `_claim_question("extended", None) == _CLAIM_QUESTION["extended"]`,
      `_claim_question("off_pole", "leg") == _CLAIM_QUESTION["off_pole"]` (off_pole 은
      expected_limb 를 줘도 무변경 — 이번 수리 범위 밖 결정).
    - leg 변형: `q = _claim_question("bent", "leg")` 이 (a) 판정 대상이 다리임을 명시
      ("다리" 포함), (b) 가림/겹침 상황을 언급 ("가려" 또는 "겹" 포함), (c) 기대 사지
      부재 시 실제 보이는 사지를 limb 에 적으라는 지시 포함, (d) 좌/우 해부학 이름 0
      ("왼", "오른", "left", "right" 미포함 — 대소문자 무관), (e) 'off_body' 이스케이프 유지.
    - arm 변형: `_claim_question("extended", "arm")` 대칭 단정 ("팔" 이 판정 대상).
    - `machine_eye` 미지 claim ValueError 유지 (기존 검증 경로 무변경).
    - 기존 test_eye_verdict_limb_mismatch 등 전 테스트 무회귀.
  </behavior>
  <action>
    card_gates.py 수리 3건 (채점 무접촉 — 이 파일의 게이트/질문 층만):

    1) `_claim_question(claim: str, expected_limb: str | None) -> str` 순수 함수 추가.
       - claim=="off_pole" 또는 expected_limb not in ("arm","leg") →
         `_CLAIM_QUESTION[claim]` 그대로 반환 (byte-동일 하위호환).
       - claim in ("bent","extended") and expected_limb in ("arm","leg") → 오클루전
         반영 질문. 초안 (fix_design 골격 — {target}=다리|팔, {other_hint}=팔='arm'|다리='leg'):
         "사진의 주황색 원은 관절 하나를 표시합니다. 원 주변에는 팔과 다리가 겹쳐
         보일 수 있습니다. 판정 대상은 원 위치의 {target}입니다. 원 위치에 {target}가
         보이면 — 다른 사지에 부분적으로 가려져 뒤에 있어도 — 그 {target}가 '접혀
         있음(bent)'인지 '펴져 있음(extended)'인지 판정하고 limb 필드에 그 사지
         종류를 적으세요 (팔='arm', 다리='leg'). 원 위치와 그 바로 뒤 어디에도
         {target}가 보이지 않으면(표시가 엉뚱한 곳에 찍힌 경우), 원이 실제로 놓인
         사지의 접힘/펴짐을 판정하고 limb 필드에 실제로 보이는 사지 종류를 적으세요
         (그 외='other'). 원이 신체 위에 있지 않으면 observed 는 'off_body' 로 하세요."
         이 변형에는 `_LIMB_QUESTION` 접미를 붙이지 않는다 (limb 지시가 본문에
         내장돼 중복/모순 방지). 응답 스키마(_CLAIM_ENUM/_LIMB_ENUM)는 무변경.
       - 좌/우 해부학 이름 금지 주석(현 _CLAIM_QUESTION 상단)의 취지를 새 함수
         docstring 으로 승계하고, 오클루전 수리 출처(quick-260901-vlu, belle 09-01
         승인)와 마크-전위 차단이 _eye_verdict + "기대 사지 부재 시 실제 사지 보고"
         분기로 유지됨을 명기.

    2) `eye_judge(crop, claim, *, api_key, expected_limb=None, model=DEFAULT_C_MODEL,
       timeout_s=60.0) -> dict` 추출 — 현 machine_eye 의 JPEG 인코딩→HTTP→파싱→
       _eye_verdict 블록을 PIL 이미지 입력으로 받는 함수로 분리. 질문은
       `_claim_question(claim, expected_limb)` 로 조립. 반환 dict 와 fail-closed
       (observed="error", match=False) 의미론 무변경.
       `machine_eye` = claim 검증(ValueError) + `mark_crop` + `eye_judge` + 반환에
       "crop" 첨부. **공개 시그니처·반환 형상·원장 필드 전부 오늘과 동일** —
       app.py:4752 호출부와 harvest_eye 수확기는 무접촉으로 새 질문이 활성된다.

    3) `_eye_verdict` 는 diff 0. app.py 도 diff 0.

    테스트는 behavior 블록의 불변식으로 먼저 작성(RED 확인) 후 구현(GREEN).
    이모지 0, 모델 문자열 하드코딩 0 (DEFAULT_C_MODEL import 그대로).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/test_card_gates.py -q && .venv/bin/python -m pytest tests -q</automated>
  </verify>
  <done>
    test_card_gates.py 전건 PASS (신규 질문 조립 테스트 포함), 전체 스위트 failed=0 /
    passed>=4537. `grep -n "_claim_question(" card_gates.py` 로 machine_eye→eye_judge→
    _claim_question 배선 확인. `git diff` 에 _eye_verdict 함수와 app.py 변경 0.
  </done>
</task>

<task type="auto">
  <name>Task 2: 라이브 양방향 재판정 (Gemini 실호출) + 증거 박제 + SUMMARY</name>
  <files>.planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/, .planning/quick/260901-vlu-machine-eye-occlusion-fp/260901-vlu-SUMMARY.md</files>
  <action>
    GPU 불필요 — Gemini HTTP 실호출만. 순서:

    1) 보존 복사 (scratchpad = 휘발, 먼저 실행):
       /private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/18afea29-d548-43ec-bf72-08bbe3512370/scratchpad/fzrepro/
       에서 eye_ledger.json, eye_crop.png, stage1_confirmed_card.png 3건을 evidence/ 로
       복사 (복사 후 md5 대조). scratchpad 가 이미 소멸했으면 그 사실을 SUMMARY 에
       명시하고, S3 원본(uid csKWYvI3WCPYPysNQ9KkWecaUvq1 / ea975e6e83374564a7803ca31aefa46b
       — verified_facts 상 실물 존재)에서 user.mp4 를 받아 3.0s 프레임의 right_knee
       마킹 크롭을 machine_eye 경로(mark_crop)로 재생성한다. user.mp4(31MB)·ref.mp4(40MB)
       는 evidence/ 에 복사하지 않는다 (S3 가 원본 보존처 — 리포 비대화 방지).

    2) API 키: `aws ssm get-parameter --name /sunity/motion/gemini-api-key
       --with-decryption --profile sunity-motion --query Parameter.Value --output text`
       → 셸 변수로만 받아 GEMINI_API_KEY 환경변수로 하네스에 전달. 키를 코드/로그/
       evidence 어디에도 기록 금지 (박제 전 로그를 grep 으로 스캔해 키 미포함 확인).

    3) evidence/run_live_eye.py 하네스 작성 — sys.path 에 backend/shared/python 추가 후
       `from sunity_shared.analysis import card_gates as cg`. **프롬프트/스키마/HTTP 를
       하네스에서 재구현 금지** — cg.eye_judge 호출만 (운영 경로 그대로가 검증 대상).
       PIL 로 크롭 PNG 를 로드해 2건 실행:
       - Case A (오클루전 → PASS 전환 목표): evidence/eye_crop.png,
         claim="bent", expected_limb="leg". 기대 = match=True (observed=bent, limb=leg).
       - Case B (마크-전위 → FAIL 유지 회귀): /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260811-ii0-card-gates-5/evidence/eye_kneepath_user_left_knee.png
         (ii0 실물 — 무릎 마크가 굽은 팔 위, 기대 다리는 그 자리에 없음),
         claim="bent", expected_limb="leg". 기대 = match=False.
       결과를 evidence/live_eye_results.json 에 기록 — 형식: {"rounds": [회차별
       {caseA, caseB, prompt_sha256, ts}], "final": {"caseA": {...}, "caseB": {...}}},
       각 케이스에 observed/limb/match/confidence/reason + 모델명. 전체 stdout 은
       evidence/live_eye_run.log 로 tee.

    4) 유계 반복 (최대 3회): Case A 가 match=False 면 Task 1 의 질문 초안을 fix_design
       골격 안에서만 문구 수정(좌/우 이름 금지·_eye_verdict 무접촉·off_pole 무변경 유지)
       하고 **두 케이스 모두** 재실행. 모든 회차의 결과를 rounds 배열에 누적 박제.
       우선순위: **Case B 의 FAIL 유지가 1급** — B 가 match=True 로 새는 문구는 즉시 폐기.
       3회 안에 A=True AND B=False 동시 성립 실패 시 수리 반려로 정직 보고 (SUMMARY 에
       회차별 표 + 마지막 프롬프트 원문 박제 — 없는 성공을 쓰지 말 것, final 은 실측
       그대로 기록).

    5) 4)에서 card_gates.py 를 수정한 회차가 있으면
       `cd backend && .venv/bin/python -m pytest tests -q` 재실행 (failed=0 / passed>=4537)
       하고 결과를 로그로 박제. (Task 1 테스트는 안정 불변식만 단정하므로 골격 내
       문구 수정으로는 깨지지 않아야 정상 — 깨지면 불변식 위반 신호로 취급.)

    6) 260901-vlu-SUMMARY.md 작성: 판정 먼저(된다/반쪽/안된다 — belle-report-format),
       수리 내용(질문 전/후 원문), 라이브 판정 표(A/B × 회차, reason 원문), pytest 수치,
       보존 자산 목록.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && python3 -c "import json; r=json.load(open('.planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/live_eye_results.json')); f=r['final']; assert f['caseA']['match'] is True and f['caseB']['match'] is False, f; print('caseA PASS-전환 / caseB FAIL-유지 OK')" && test -s .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/live_eye_run.log && test -s .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/eye_crop.png</automated>
  </verify>
  <done>
    live_eye_results.json final 이 caseA.match=true / caseB.match=false. 실행 로그 실물
    존재 + API 키 미노출 확인. 보존 자산 3건 evidence/ 존재. SUMMARY 에 회차별 표와
    최종 프롬프트 원문 박제. (반려 시: final 실측 그대로 + 반려 사유 명시 — 그 경우 이
    verify 는 FAIL 이 정직한 결과이며 SUMMARY 가 그것을 보고한다.)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| card_gates → Gemini API | 마킹 크롭 이미지 + 질문이 외부 LLM 으로 나감 |
| 하네스 → SSM Parameter Store | Gemini API 키 조회 (aws --profile sunity-motion) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-vlu-01 | Information Disclosure | run_live_eye.py / 로그 | mitigate | 키는 SSM→셸 변수→env 로만 전달, 코드·로그·evidence 미기록. 박제 전 로그 grep 스캔 |
| T-vlu-02 | Information Disclosure | Gemini 추론 호출 (크롭 이미지) | accept | 기존 운영 경로와 동일 처분 (T-kpo-01 — 추론 호출만, 학습 재료 무접촉). 신규 데이터 표면 0 |
| T-vlu-03 | Tampering (게이트 약화) | _claim_question 프롬프트 변경 | mitigate | Case B(마크-전위) 라이브 회귀 + _eye_verdict diff 0 + 좌우 이름 금지 테스트 — 차단력 실측 유지 |
| T-vlu-SC | Tampering | 패키지 설치 | accept | 신규 패키지 설치 0 (기존 .venv 그대로) — 공급망 표면 무변 |
</threat_model>

<verification>
1. 단위: `cd backend && .venv/bin/python -m pytest tests/test_card_gates.py -q` — 기존 +
   신규 질문 조립 테스트 전건 PASS.
2. 전체: `cd backend && .venv/bin/python -m pytest tests -q` — failed=0, passed>=4537
   (시스템 python3 금지, .venv 고정).
3. 라이브 (Gemini 실호출, GPU 불필요): Case A 오클루전 match=True 전환 + Case B
   마크-전위 match=False 유지 — evidence/live_eye_results.json + live_eye_run.log.
4. 무접촉 확인: `git diff` 에 app.py 변경 0, _eye_verdict 변경 0, 채점 산식 파일
   (deduction_engine/dimensions/kismam/motiondtw/assemble) 변경 0.
5. 증거 박제: evidence/ 에 보존 자산 3건 + 하네스 + 결과 JSON + 로그.
</verification>

<success_criteria>
- 새 질문이 expected_limb(arm/leg) 반영형으로 조립되고 하위호환(None/off_pole 은
  byte-동일) 성립 — 테스트가 증인.
- belle 실물 오클루전 크롭 라이브 재판정 match=True (실행 로그 박제) — 이 수리의
  존재 이유.
- ii0 kneepath 실물 크롭 라이브 재판정 match=False 유지 — 마크-전위 차단 무회귀.
- pytest failed=0 / passed>=4537, 범위 밖 코드 diff 0, 이모지 0, 키·모델 문자열
  하드코딩 0.
- SUMMARY 에 판정 먼저 + 질문 전/후 원문 + 회차별 라이브 표.
</success_criteria>

<output>
Create `.planning/quick/260901-vlu-machine-eye-occlusion-fp/260901-vlu-SUMMARY.md` when done
</output>
