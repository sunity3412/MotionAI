---
phase: quick-260903-lpl
plan: 01
type: execute
wave: 1
depends_on: [quick-260903-jxn]
files_modified:
  - backend/shared/python/sunity_shared/analysis/card_gates.py
  - backend/tests/test_card_gates.py
  - backend/functions/pipeline/app.py
autonomous: true
requirements: [quick-260903-lpl]
must_haves:
  truths:
    - "몸통 관절(엉덩이·어깨) 확정 카드는 기계 눈 검사를 받지 않는다 — hold·pair 게이트만. 무릎·팔꿈치·발목·손목은 종전대로 눈 검사"
    - "눈을 건너뛴 카드는 verdict 로그에 eye=skip:torso_joint 로 남고, 원장(eye_ledger)에는 항목이 생기지 않는다(호출 0)"
    - "_eye_verdict·질문·다수결·스키마 무접촉. pytest 4586/0 → 신규 포함 전부 pass"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/card_gates.py"
      provides: "EYE_SKIP_KINDS + eye_applicable(joint) 순수 함수"
      contains: "def eye_applicable"
    - path: "backend/functions/pipeline/app.py"
      provides: "_eye_check 진입에서 eye_applicable False 면 (True, 'skip:torso_joint', False)"
      contains: "skip:torso_joint"
---

<objective>
기계 눈 검사에서 몸통 관절(엉덩이·어깨) 제외.

belle 09-03: "비교 사진이 있어야 뭘 보지 저것만 보고 어케 알아" — 눈은 사진 한 장(내 영상 크롭 + 원)만 받고 "그 관절이
접혔나 펴졌나"를 절대 판정한다. 무릎·팔꿈치는 한 장에서 각이 보여 성립하지만(회귀 5/5), 엉덩이는 기준 없이 정해지지
않는다(같은 크롭 5회: 3/5, 힌트 주면 1/5 — quick-260903-jka/jxn evidence). 감점 자체가 정은지 대비 각도 차이인데 눈에는
기준을 안 준 것이 구조적 원인. 기준 사진을 함께 주는 방향은 "같은 순간" 검증(참고 카드 × 사유)과 얽혀 별건.
지금은 몸통 관절을 눈 검사에서 빼 pdshape 왼엉덩이 같은 확정 사진이 운으로 사라지지 않게 한다. 정지 여부(hold)·
짝 프레임(pair) 게이트는 그대로 적용된다.
</objective>

<context>
읽을 것: `card_gates.py` 의 `_LIMB_OF`/`joint_limb`/`joint_kind_ko`/`_HINT_KINDS`(jka·jxn), `app.py` 4978-5010 `_eye_check`
(캐시·midrange 조기 반환 관례) + 5095-5130 verdict 로그 조립(`eye_why` 문자열이 `dropped`/`survivors` 사유에 들어가는 방식),
`backend/tests/test_card_gates.py`. pytest = `backend/.venv/bin/python -m pytest backend/tests -q` (기준선 4586/0). Gemini 호출·키 조회 금지.
</context>

<tasks>

<task id="1" name="card_gates.eye_applicable + 테스트">
files: backend/shared/python/sunity_shared/analysis/card_gates.py, backend/tests/test_card_gates.py
action:
- `EYE_SKIP_KINDS = frozenset({"hip", "shoulder"})` (joint 이름 꼬리 — `_LIMB_OF` 키 공간) + `def eye_applicable(joint: str) -> bool` (꼬리가 EYE_SKIP_KINDS 면 False, 그 외 True — 미등록 관절도 True 로 종전 동작). docstring 에 belle 원문·측정(3/5, 1/5)·"기준 사진 동반 질문은 별건" 명시.
- 테스트 3건: left_hip/right_shoulder → False; left_knee/right_elbow/left_ankle → True; 미등록 'left_foo' → True.
verify: `backend/.venv/bin/python -m pytest backend/tests/test_card_gates.py -q` pass
done: 순수 함수 + 테스트 green
</task>

<task id="2" name="pipeline _eye_check 조기 반환 + verdict 사유">
files: backend/functions/pipeline/app.py
action:
- `_eye_check` 에서 캐시 조회 뒤·각도 계산 전에 `if not cg.eye_applicable(gate_joint): _eye_cache[key] = (True, "skip:torso_joint", False); return True, "skip:torso_joint", False` (midrange 조기 반환과 같은 모양 — 비구속, 호출 0, 원장 항목 0).
- verdict 로그 문자열에 이 사유가 `eye=skip:torso_joint` 로 보이는지 확인(기존 조립이 eye_why 를 그대로 싣는다면 무변경). 주석 1줄(quick-260903-lpl, belle 원문 요지).
verify: `backend/.venv/bin/python -m pytest backend/tests -q` → 4586 + 신규 전부 pass, fail 0 (수치 보고)
done: 몸통 관절 카드가 눈 없이 hold·pair 만으로 판정
</task>

</tasks>

<verification>
- pytest fail 0. 라이브 확인은 다음 Pod 세션(pdshape 재분석 시 왼엉덩이 카드가 verdict 로그에 eye=skip:torso_joint 로 생존).
</verification>
