---
phase: quick-260903-jxn
plan: 01
type: execute
wave: 1
depends_on: [quick-260903-jka]
files_modified:
  - backend/shared/python/sunity_shared/analysis/card_gates.py
  - backend/tests/test_card_gates.py
  - backend/functions/pipeline/app.py
autonomous: true
requirements: [quick-260903-jxn]
must_haves:
  truths:
    - "관절 종류 힌트는 사지 중간 관절(무릎·팔꿈치·발목·손목)에만 붙는다. 엉덩이·어깨는 jka 이전 질문과 byte-동일"
    - "기계 눈이 첫 판정에서 불일치(match=False)를 내면 같은 크롭에 최대 2회 더 물어 3회 다수결로 확정한다. 첫 판정이 일치면 추가 호출 0 (비용·시간 무변화)"
    - "다수결의 반환 형상은 eye_judge 와 동일(observed/limb/match/confidence/reason) + rounds(호출 수) — 원장(ledger) 기존 필드 무변경, rounds 는 추가 필드"
    - "_eye_verdict·응답 스키마·게이트 순서·앱·계약 무접촉. pytest 4579/0 → 신규 포함 전부 pass"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/card_gates.py"
      provides: "_HINT_KINDS 한정 + eye_judge_majority(…, max_rounds=3)"
      contains: "def eye_judge_majority"
    - path: "backend/functions/pipeline/app.py"
      provides: "machine_eye 경로가 다수결 판정을 쓴다"
      contains: "eye_judge_majority"
---

<objective>
기계 눈 힌트를 사지 중간 관절에 한정 + 불일치 시 3회 다수결.

**측정(09-03, jka 운영 질문, 5회 반복, evidence/eye_regression_results.json):**

| 크롭 | 기대 | 힌트 있음 | 힌트 없음 |
|---|---|---|---|
| 클라임 오클루전 무릎 09-02 / 09-01 | True | **4/5 · 5/5** | 2/5 · 1/5 |
| kneepath 마크-전위 무릎 | False | 0/5 | 0/5 |
| fresh r00 팔꿈치 / r02 어깨 / pdshape 팔꿈치 | True | 5/5 · 5/5 · 5/5 | (09-02 원장 True) |
| elbow r03 무릎 extended | True | 5/5 | — |
| **pdshape 엉덩이(09-02 확정 카드)** | True | **1/5** | **3/5** |
| fresh r03 엉덩이(전환 프레임, hold 게이트가 이미 기각) | False | 2/5 | 0/5 |

읽기: 무릎·팔꿈치·어깨는 힌트로 안정. **엉덩이는 힌트 없이도 불안정(3/5)하고 힌트가 더 나쁘게 만든다** — 눈이
"엉덩이 굽힘"을 다리 방향으로 오독(허벅지가 아래로 뻗음=extended). 어깨는 5/5 였지만 엉덩이와 같은 몸통 관절이라
보수적으로 힌트 제외(측정 전 상태 = jka 이전 질문 그대로). 남은 비결정(클라임 4/5, 엉덩이 3/5)은 **불일치일 때만**
재질문하는 다수결로 줄인다: p=0.8 → 0.93, p=0.6 → 0.74, kneepath p=0 → 0 (위양성 증가 없음). 일치 시 추가 호출 0.

**손대지 않는 것:** _eye_verdict, 스키마, 게이트 순서(hold→pair→eye), 원장 기존 필드, 앱, 계약. 엉덩이 판정 자체의 신뢰도(3/5)는
belle 판정 항목(눈 게이트에서 엉덩이·어깨 제외 여부)으로 착수점에 올림 — 이 작업 범위 밖.
</objective>

<context>
읽을 것: `card_gates.py` 의 jka 변경부(`_KIND_KO`, `_KIND_SEGMENTS`, `_KIND_LIMB`, `_joint_kind_hint`, `_claim_question`, `eye_judge`, `machine_eye`), `backend/tests/test_card_gates.py` jka 테스트 7건, `app.py` 4998-5015 machine_eye 호출부(eye_ledger.append 포함 — 원장 필드 확인), `.planning/quick/260903-jka-eye-joint-kind/260903-jka-SUMMARY.md`, 이 디렉터리 `evidence/run_eye_regression.py`(--majority 모드가 `cg.eye_judge_majority` 를 호출).
규율: 한국어 docstring 에 출처(quick-260903-jxn, 측정 수치). pytest = `backend/.venv/bin/python -m pytest backend/tests -q` (기준선 4579/0). Gemini 호출·키 조회 금지(하네스는 오케스트레이터).
</context>

<tasks>

<task id="1" name="힌트 한정(무릎·팔꿈치·발목·손목) + eye_judge_majority">
files: backend/shared/python/sunity_shared/analysis/card_gates.py, backend/tests/test_card_gates.py
action:
- `_HINT_KINDS = frozenset({"무릎", "팔꿈치", "발목", "손목"})` — `_joint_kind_hint`(또는 `_claim_question`)가 이 집합 밖(엉덩이·어깨·미등록)이면 힌트 없이 종전 질문 byte-동일 반환. `joint_kind_ko` 자체는 그대로(엉덩이/어깨도 반환 — 호출측 무변경). docstring 에 측정 수치(엉덩이 3/5→1/5).
- `def eye_judge_majority(crop, claim, *, api_key, expected_limb=None, joint_kind=None, model=DEFAULT_C_MODEL, timeout_s=60.0, max_rounds=3) -> dict`: 1회 `eye_judge`; match=True 면 그대로 반환 + `rounds=1`. False 면 추가로 (max_rounds-1)회 호출해 match 다수결(True 개수 > 절반). 반환 = 다수 쪽 판정 중 **첫 번째** 결과 dict(observed/limb/match/confidence/reason) + `rounds`(총 호출 수) + `votesTrue`/`votesFalse`. observed="error"(호출 실패) 는 False 표로 셈(fail-closed 유지). max_rounds 는 홀수만(짝수면 ValueError).
- `machine_eye(..., majority: bool = False)`: True 면 eye_judge_majority 사용, 아니면 종전(하위호환·하네스). 반환 dict 에 rounds/votes 키는 majority 일 때만.
- 테스트: (a) 엉덩이/어깨 joint_kind 는 힌트 0 = jka 이전 질문 byte-동일 (b) 무릎/팔꿈치/발목/손목은 힌트 1문장 (c) eye_judge 를 monkeypatch 해 [False, True, True] → match True rounds 3; [True] → rounds 1 추가 호출 0; [False, False, True] → False; [False, error, True] → False (d) max_rounds 짝수 → ValueError.
verify: `backend/.venv/bin/python -m pytest backend/tests/test_card_gates.py -q` pass
done: 한정 + 다수결 + 테스트 green
</task>

<task id="2" name="pipeline: 다수결 사용 + 원장에 rounds 추가 필드">
files: backend/functions/pipeline/app.py
action:
- machine_eye 호출에 `majority=True`. 직후 eye_ledger.append 의 dict 에 **추가 필드** `rounds`(res.get("rounds", 1)) — 기존 필드 이름·순서·의미 무변경. 로그 1줄에 rounds 포함(`eye ... rounds=%d`).
- 주석: quick-260903-jxn, 측정 수치, "불일치 시만 재질문 — 일치 시 호출 0".
verify: `backend/.venv/bin/python -m pytest backend/tests -q` → 4579 + 신규 전부 pass, fail 0 (수치 보고)
done: 운영 경로 다수결, 원장 하위호환
</task>

</tasks>

<verification>
- pytest fail 0
- 오케스트레이터: `evidence/run_eye_regression.py 5 --majority` → 클라임 2크롭·팔꿈치·어깨·extended 무릎 5/5, kneepath 0/5, 엉덩이 결과는 보고만(기대값 미확정 — belle 항목).
- 클라임 라이브 재분석 = Pod 세션(착수점).
</verification>
