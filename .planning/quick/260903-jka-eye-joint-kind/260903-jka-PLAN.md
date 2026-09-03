---
phase: quick-260903-jka
plan: 01
type: execute
wave: 1
depends_on: [quick-260901-vlu]
files_modified:
  - backend/shared/python/sunity_shared/analysis/card_gates.py
  - backend/tests/test_card_gates.py
  - backend/functions/pipeline/app.py
autonomous: true
requirements: [quick-260903-jka]
must_haves:
  truths:
    - "기계 눈 질문에 관절 종류(무릎·팔꿈치·엉덩이·어깨·발목·손목)와 '다른 사지가 앞을 가로질러 가릴 수 있다 + 뒤로 이어지는 분절이 있으면 그 사지가 대상' 기준이 한 문장으로 붙는다 — 운영 경로(app.py machine_eye 호출)가 관절 종류를 넘긴다"
    - "joint_kind 미지정(None)·off_pole 은 종전 질문과 byte-동일 (vlu 하위호환 유지) — 09-01 테스트 전부 그대로 통과"
    - "_eye_verdict·응답 스키마·원장 필드·machine_eye 반환 형상 무접촉 (마크-전위 차단 ii0 §6-3 그대로)"
    - "좌/우 해부학 이름(왼/오른/left/right) 은 질문에 0"
    - "pytest 기준선 4572/0 → 신규 테스트 포함 전부 pass"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/card_gates.py"
      provides: "joint_kind_ko(joint) + _claim_question(claim, expected_limb, joint_kind=None) 힌트 변형 + eye_judge/machine_eye joint_kind 통과"
      contains: "def joint_kind_ko"
    - path: "backend/functions/pipeline/app.py"
      provides: "machine_eye 호출에 joint_kind=cg.joint_kind_ko(gate_joint)"
      contains: "joint_kind=cg.joint_kind_ko(gate_joint)"
  key_links:
    - from: "backend/functions/pipeline/app.py (_run_gated_card_inherit machine_eye 호출, 5006 부근)"
      to: "card_gates._claim_question 힌트 변형"
      via: "joint_kind kwarg → eye_judge → _claim_question(claim, expected_limb, joint_kind)"
      pattern: "joint_kind"
---

<objective>
기계 눈 질문에 관절 종류 명시 + 교차 가림 기준 — 오클루전 위양성이 비결정(2/5)이던 것을 5/5 로, 회귀 0/5 유지.

**측정(09-03, 운영 경로 card_gates.eye_judge 그대로, temperature 0, 5회 반복):**

| 크롭 | 운영 질문(vlu) | V2 = 운영 질문 + 무릎 힌트 1문장 |
|---|---|---|
| 클라임 3.0s 09-02 운영 크롭 (뻗은 팔이 굽힌 무릎 앞을 가로지름, claim=bent, leg) | 2/5 성립 | **5/5** |
| 같은 프레임 09-01 하네스 크롭 | 1/5 | **5/5** |
| 회귀 기준: kneepath 무릎 마크가 팔 위 (마크-전위, 기대 False) | 0/5 | **0/5** |

09-01 수리(vlu)의 "라이브 1회 PASS"는 5회 중 1~2회 나오는 운이었다. 갈린 원인은 크롭 차이가 아니라(두 크롭 픽셀 동일,
링 주변만 미세 차) 눈의 비결정성이고, 질문에 "이 원은 무릎 관절 표시, 팔이 앞을 가로질러 가릴 수 있음, 팔 뒤로
허벅지와 정강이가 이어지면 그 다리가 대상" 을 주면 안정된다. 원본 측정 = 오케스트레이터 스크래치
`eye_repeat.py`/`eye_variants.py` 결과(이 디렉터리 evidence/ 에 결과 JSON 사본 박제 예정).

**손대지 않는 것:** _eye_verdict(2단 판정), 응답 스키마(_CLAIM_ENUM/_LIMB_ENUM), 원장 필드, machine_eye 반환 형상, 카드 게이트
순서(hold→pair→eye), 앱, 계약. 클라임 라이브 재분석(Pod)은 이 작업 뒤 별도.
</objective>

<context>
읽을 것:
- `backend/shared/python/sunity_shared/analysis/card_gates.py` 60-105 (`_LIMB_OF`, `joint_limb`), 400-520 (`_CLAIM_QUESTION`, `_claim_question`, `_eye_verdict`), 520-606 (`eye_judge`, `machine_eye`)
- `backend/tests/test_card_gates.py` 140-200 (vlu 테스트 — byte-동일 하위호환·오클루전 변형 assert)
- `backend/functions/pipeline/app.py` 4998-5012 (machine_eye 호출부)
- `.planning/quick/260901-vlu-machine-eye-occlusion-fp/260901-vlu-SUMMARY.md` (설계 규율: 좌/우 이름 금지, 마크-전위 차단 유지, 질문 본문에 limb 지시 내장)
- 이 디렉터리 `evidence/run_eye_regression.py` (오케스트레이터가 실행할 회귀 하네스 — 신규 시그니처 `eye_judge(..., joint_kind=...)`, `joint_kind_ko` 를 전제)

규율: 한국어 docstring/주석에 출처(quick-260903-jka, 측정 수치). 백엔드 테스트는 `backend/.venv/bin/python -m pytest backend/tests -q` (기준선 4572 passed / 0 failed). 앱 무접촉.
</context>

<tasks>

<task id="1" name="card_gates: joint_kind_ko + 힌트 변형 질문 + 시그니처 통과 + 테스트">
files: backend/shared/python/sunity_shared/analysis/card_gates.py, backend/tests/test_card_gates.py
action:
- `_KIND_KO = {"knee": "무릎", "elbow": "팔꿈치", "hip": "엉덩이", "shoulder": "어깨", "ankle": "발목", "wrist": "손목", "hand": "손목"}` + `def joint_kind_ko(joint: str) -> str | None` (joint_limb 과 같은 `split("_")[-1]` 관례).
- 분절 표: `_KIND_SEGMENTS = {"무릎": "허벅지와 정강이", "엉덩이": "몸통과 허벅지", "발목": "정강이와 발", "팔꿈치": "위팔과 아래팔", "어깨": "몸통과 위팔", "손목": "아래팔과 손"}`.
- `_claim_question(claim, expected_limb, joint_kind: str | None = None)`:
  · claim=off_pole 또는 expected_limb ∉ {arm, leg} → 종전 그대로(byte-동일).
  · joint_kind None 또는 미등록 → 종전 오클루전 변형 그대로(byte-동일, vlu).
  · 등록된 joint_kind → 종전 오클루전 변형 **+ 힌트 1문장** (측정된 V2 문형, leg/arm 대칭):
    leg: `" 참고: 이 원은 {kind} 관절 표시이며, 팔이 {kind} 앞을 가로질러 가릴 수 있습니다. 팔 뒤로 {segments}가 이어지면 그 다리가 판정 대상입니다."`
    arm: `" 참고: 이 원은 {kind} 관절 표시이며, 다리가 {kind} 앞을 가로질러 가릴 수 있습니다. 다리 뒤로 {segments}이 이어지면 그 팔이 판정 대상입니다."`
    (무릎/leg 문장은 측정본과 **문자 동일**하게: "참고: 이 원은 무릎 관절 표시이며, 팔이 무릎 앞을 가로질러 가릴 수 있습니다. 팔 뒤로 허벅지와 정강이가 이어지면 그 다리가 판정 대상입니다." — 조사(가/이)는 분절 표 마지막 글자 받침으로 결정하는 작은 헬퍼로.)
  · 좌/우 이름 0 유지. docstring 에 09-03 측정 수치(2/5→5/5, 회귀 0/5) 인용.
- `eye_judge(..., expected_limb=None, joint_kind: str | None = None, ...)` → `_claim_question(claim, expected_limb, joint_kind)`. `machine_eye(..., expected_limb=None, joint_kind: str | None = None, ...)` → eye_judge 로 통과. 반환 형상 무변경.
- 테스트(기존 파일에 추가): (a) `_claim_question("bent","leg")` == `_claim_question("bent","leg",None)` byte-동일 + 기존 vlu 테스트 무변경 통과 (b) 무릎/leg 힌트 문장이 측정본과 문자 동일 (c) 팔꿈치/arm 힌트가 대칭 문형 + "왼/오른/left/right" 0 (d) off_pole + joint_kind 는 무변경 (e) `joint_kind_ko("right_knee")=="무릎"`, `("left_hand")=="손목"`, 미등록 None.
verify: `backend/.venv/bin/python -m pytest backend/tests/test_card_gates.py -q` 전부 pass
done: 시그니처·질문·테스트 green
</task>

<task id="2" name="pipeline: machine_eye 호출에 joint_kind 전달 + 전체 pytest">
files: backend/functions/pipeline/app.py
action:
- 5006 부근 `cg.machine_eye(... expected_limb=cg.joint_limb(gate_joint), ...)` 에 `joint_kind=cg.joint_kind_ko(gate_joint)` 추가. 주석 1줄(quick-260903-jka, 측정 수치).
- 다른 호출부가 있으면(grep `machine_eye(`·`eye_judge(`) 동일 적용 — harvest/스크립트 경로는 kwarg 기본값 None 이라 무변경이어도 됨(하위호환).
verify: `backend/.venv/bin/python -m pytest backend/tests -q` → 4572 + 신규 전부 pass, fail 0 (수치 보고)
done: 운영 경로가 관절 종류를 넘김, 전체 기준선 green
</task>

</tasks>

<verification>
- pytest 전체 fail 0 (기준선 4572 → 4577 부근)
- 오케스트레이터: `evidence/run_eye_regression.py` (GEMINI 키 env) — 오클루전 2크롭 5/5, kneepath 0/5, ii0·pdshape 확정 크롭(팔꿈치·어깨·엉덩이·extended 무릎) 기대 판정 유지. 결과 JSON 을 evidence/ 에 박제.
- 클라임 라이브 재분석은 Pod 세션에서 별도(착수점에 누적).
</verification>

<success_criteria>
- 커밋 2개(코드만). docs 커밋은 오케스트레이터.
</success_criteria>
