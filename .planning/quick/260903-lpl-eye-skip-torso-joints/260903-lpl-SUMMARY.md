---
phase: quick-260903-lpl
plan: "01"
status: complete
subsystem: analysis-card-gates
tags: [machine-eye, gemini, torso-joint, hip, shoulder, card-gates, false-positive]
requires: [quick-260903-jxn]
provides:
  - "card_gates.EYE_SKIP_KINDS = {hip, shoulder} + eye_applicable(joint) 순수 함수 — 몸통 관절은 기계 눈 검사 제외, 미등록 관절은 True(종전 동작)"
  - "pipeline _eye_check: eye_applicable False 면 (True, 'skip:torso_joint', False) 조기 반환 — 비구속, Gemini 호출 0, eye_ledger 항목 0"
  - "verdict 로그 survivors 항목에 eye=사유 동반 (dropped 와 같은 midrange 제외 규칙) — 몸통 카드 생존이 eye=skip:torso_joint 로 보인다"
affects: [pipeline-card-gates]
tech-stack:
  added: []
  patterns: ["눈 적용 여부는 card_gates 순수 함수 한 곳(eye_applicable) — 호출측은 midrange 와 같은 모양의 조기 반환"]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/card_gates.py
    - backend/tests/test_card_gates.py
    - backend/functions/pipeline/app.py
decisions:
  - "제외 키 공간 = _LIMB_OF 와 같은 관절 이름 꼬리(hip/shoulder) — joint_limb/joint_kind_ko 와 동일한 split('_')[-1] 관례, 좌/우 이름 미사용"
  - "survivors 로그의 eye 사유는 skip 만 특수취급하지 않고 dropped 와 같은 규칙(비어있지 않고 midrange 아님)으로 동반 — 눈 통과 카드도 eye=bent->bent/leg 로 보임"
  - "테스트에 jxn _HINT_KINDS 정합 불변식 추가: 힌트가 붙는 종류 == 눈 검사 대상, 몸통 종류 == 제외"
metrics:
  duration: "~12분"
  completed: "2026-09-03"
  tasks: "2/2"
  pytest: "4589 passed / 0 failed / 20 skipped (기준선 4586 + 신규 3)"
---

# Quick 260903-lpl: 기계 눈 검사에서 몸통 관절(엉덩이·어깨) 제외 Summary

**One-liner:** `card_gates.eye_applicable(joint)` (꼬리 hip/shoulder → False) 를 추가하고 pipeline `_eye_check` 진입에서 캐시 조회 뒤·각도 계산 전에 `(True, "skip:torso_joint", False)` 로 조기 반환 — 몸통 관절 확정 카드는 hold·pair 게이트만 받고 Gemini 호출·원장 항목 0, verdict 로그 survivors 에 `eye=skip:torso_joint` 로 생존이 남는다. belle 09-03 "비교 사진이 있어야 뭘 보지 저것만 보고 어케 알아" — 한 장 크롭으로 엉덩이 접힘/폄은 기준 없이 안 정해짐(3/5, 힌트 1/5).

## 판정: 코드·테스트 성립 (라이브 확인은 다음 Pod 세션 — pdshape 왼엉덩이 카드 생존 여부)

- **순수 함수** — `eye_applicable("left_hip"/"right_shoulder") is False`, 무릎·팔꿈치·발목·손목(hand 별칭 포함) True, 미등록 `left_foo`/`split`/`split_angle` True. `EYE_SKIP_KINDS <= set(_LIMB_OF)`. jxn 정합: `_KIND_KO` 전 종류에 대해 `eye_applicable == (ko in _HINT_KINDS)`.
- **조기 반환 모양** — midrange 와 동일: `_eye_cache[key]` 적재 + 3-튜플 반환. `eye_calls` 미증가, `eye_ledger.append` 미도달, `machine_eye` 미호출 → 원장 항목 0·호출 0.
- **verdict 로그** — 기존 조립은 `dropped` 에만 `eye=` 를 실었고 survivors 는 `rid:inherit@u/r` 뿐이라 생존한 몸통 카드의 사유가 안 보였다 → survivors 에도 같은 규칙으로 동반 (`_survivor_str`). `emitted` 튜플 형상(5원소, 위치 참조 `t[0]/t[1]/t[2]/t[4]`)은 무변경 — 별도 `survivor_eye: dict[rid -> why]`.
- **무접촉 확인** — `_eye_verdict`, `_claim_question`, `eye_judge*`, response_schema, 게이트 순서(hold→pair→eye), 원장 필드, `app/`, 계약: diff 0. 두 커밋의 변경 파일 = card_gates.py / test_card_gates.py / app.py 3건뿐. Gemini 호출·API 키 조회·출력 0.

## Task 별 변경

### Task 1 — card_gates: `EYE_SKIP_KINDS` + `eye_applicable` + 테스트 3건 (`96d3061b`)

`backend/shared/python/sunity_shared/analysis/card_gates.py` (joint_kind_ko 뒤, track_claim 앞)
- `EYE_SKIP_KINDS = frozenset({"hip", "shoulder"})` — 주석: 키 공간 = `_LIMB_OF` 꼬리, 눈을 안 받는 카드도 hold·pair 는 그대로.
- `def eye_applicable(joint: str) -> bool: return joint.split("_")[-1] not in EYE_SKIP_KINDS` — docstring 에 belle 원문·측정(엉덩이 3/5, 힌트 1/5, 무릎·팔꿈치 5/5)·구조적 원인(눈에 기준 미제공)·"기준 사진 동반 질문은 같은 순간 검증과 얽혀 별건"·미등록 관절 True 근거 명시.

`backend/tests/test_card_gates.py` (test_joint_kind_ko_mapping 뒤) 신규 3건
- `test_eye_applicable_torso_joints_skipped` — 좌/우 hip·shoulder False + `EYE_SKIP_KINDS <= _LIMB_OF` + `_HINT_KINDS` 정합 불변식.
- `test_eye_applicable_midlimb_joints_kept` — knee/elbow/ankle/wrist/hand True.
- `test_eye_applicable_unknown_joint_defaults_true` — left_foo/split/split_angle True.

검증: `backend/.venv/bin/python -m pytest backend/tests/test_card_gates.py -q` → **29 passed** (jxn 26 + 신규 3).

### Task 2 — pipeline: `_eye_check` 조기 반환 + verdict survivors 눈 사유 (`7090a317`)

`backend/functions/pipeline/app.py` `_run_gated_card_inherit`
- `_eye_check`: `if key in _eye_cache` 뒤·`ang = cg.joint_angle(...)` 앞에 `if not cg.eye_applicable(gate_joint): _eye_cache[key] = (True, "skip:torso_joint", False); return True, "skip:torso_joint", False` + 주석 1줄(belle 09-03 원문 요지, quick-260903-lpl).
- `survivor_eye: dict[str, str] = {}` 선언(emitted/dropped 옆) → inherit 생존 시 `if eye_why and eye_why != "midrange": survivor_eye[rid] = eye_why`.
- verdict `log.info` 의 survivors 리스트를 `_survivor_str(t)` 로 조립: 기존 `rid:path@u../r..` + (있으면) ` eye={why}`. dropped 조립·`eye_calls`·문자열 포맷 나머지 무변경.

검증: `backend/.venv/bin/python -m pytest backend/tests -q` → **4589 passed / 0 failed / 20 skipped** (59s). 기준선 4586 → +3 (전부 Task 1 신규), failed 0 유지. `py_compile` OK.

## Commits

| Task | Commit | 파일 |
|------|--------|------|
| 1 | `96d3061b` | card_gates.py, test_card_gates.py |
| 2 | `7090a317` | functions/pipeline/app.py |

두 커밋 사이에 동시 작업 에이전트의 `cf5ee317 feat(quick-260903-lr6)` (app/ DeductionCard) 가 끼어 있음 — 파일 겹침 0, 96d3061b 는 HEAD 조상 확인. 작업 트리의 `app/src/app/analysis/result.tsx` 수정은 lr6 몫이라 미접촉·미스테이징. docs(SUMMARY·STATE) 커밋은 오케스트레이터 몫 — 이 파일은 미커밋. ROADMAP 무변경.

## Deviations from Plan

None - plan executed as written. 계획의 조건문 1건만 기록:
- Task 2 "verdict 로그 문자열에 `eye=skip:torso_joint` 로 보이는지 확인(기존 조립이 eye_why 를 그대로 싣는다면 무변경)" — 기존 조립은 `dropped` 에만 eye 사유를 싣고 survivors 에는 안 실어, 생존한 몸통 카드는 사유가 안 보였다. must_have("verdict 로그에 eye=skip:torso_joint 로 남고 … 생존")를 만족시키려 survivors 에도 dropped 와 같은 규칙으로 동반하도록 로그 문자열만 바꿈 (`survivor_eye` dict + `_survivor_str`). 부수 효과: 눈 통과 카드도 `eye=bent->bent/leg` 로 보임 (로그 한정, 판정·원장 무변경).

## 오케스트레이터 후속 (계획 <verification>)

- 다음 Pod 세션 pdshape 재분석 → 서버 로그 `card_gates verdict … survivors=[… 'left_hip:inherit@u…/r… eye=skip:torso_joint' …]` 확인 + 같은 분석의 `card_gates eye side=… joint=left_hip` 로그 0줄(호출 0) + S3 ledger.json 에 hip/shoulder 항목 0.
- STATE·착수점 갱신은 오케스트레이터 몫 (이 세션 .planning 무커밋).

## Known Stubs

없음.

## Threat Flags

없음 — 신규 네트워크/인증/파일 표면 0. 몸통 관절 Gemini 호출이 사라져 외부 호출 표면은 오히려 축소.

## Self-Check: PASSED

3 소스 파일 + SUMMARY 실물 존재, 커밋 2건(96d3061b, 7090a317) git log 확인, 마커 `def eye_applicable`(card_gates.py) / `skip:torso_joint`(app.py) 존재. 96d3061b 는 HEAD 조상. backend/ 미추적·미커밋 변경 0 (app/ result.tsx 수정은 동시 작업 lr6 몫).
