---
phase: quick-260903-jka
plan: "01"
status: complete
subsystem: analysis-card-gates
tags: [machine-eye, gemini, occlusion, false-positive, card-gates, joint-kind]
requires: [quick-260901-vlu]
provides:
  - "card_gates.joint_kind_ko(joint) — 관절 이름 → 종류 한국어 (무릎·팔꿈치·엉덩이·어깨·발목·손목)"
  - "card_gates._claim_question(claim, expected_limb, joint_kind=None) — 등록 종류면 vlu 오클루전 변형 + 힌트 1문장"
  - "card_gates.eye_judge / machine_eye — joint_kind kwarg 통과 (기본 None = 종전 질문)"
  - "pipeline app.py 운영 호출부가 joint_kind=cg.joint_kind_ko(gate_joint) 전달"
affects: [pipeline-card-gates]
tech-stack:
  added: []
  patterns: ["질문 힌트는 순수 함수 _joint_kind_hint 로 분리 — 하네스가 운영 경로(eye_judge) 그대로 재판정"]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/card_gates.py
    - backend/tests/test_card_gates.py
    - backend/functions/pipeline/app.py
decisions:
  - "무릎/leg 힌트 문장은 09-03 측정본(5/5)과 문자 동일 — 문형·조사 변경 금지 (테스트가 리터럴로 고정)"
  - "종류↔expected_limb 불일치(leg 에 '팔꿈치')는 힌트 미부착 — 비문 방지 (계획 외 소규모 방어, 운영 경로는 항상 일치)"
  - "joint_kind None·미등록·off_pole 은 byte-동일 (vlu 하위호환) — harvest/스크립트 호출부 무변경으로 종전 질문 유지"
metrics:
  duration: "~12분"
  completed: "2026-09-03"
  tasks: "2/2"
  pytest: "4579 passed / 0 failed / 20 skipped (기준선 4572 + 신규 7)"
---

# Quick 260903-jka: 기계 눈 질문 관절 종류 힌트 Summary

**One-liner:** 기계 눈 질문 끝에 "이 원은 {관절 종류} 표시, 다른 사지가 앞을 가로질러 가릴 수 있음, 뒤로 두 분절이 이어지면 그 사지가 대상" 힌트 1문장을 붙이고 운영 경로(app.py machine_eye 호출)가 관절 종류를 넘기게 함 — 09-03 측정에서 클라임 오클루전 크롭 2/5·1/5 → 5/5·5/5, kneepath 마크-전위 0/5 유지였던 문형을 코드로 고정.

## 판정: 코드·테스트 성립 (라이브 회귀는 오케스트레이터 하네스 몫)

- **무릎/leg 힌트 = 측정본과 문자 동일** — `_joint_kind_hint("leg","무릎") == " " + 측정 문장` 을 테스트 리터럴로 고정 (test_claim_question_knee_leg_hint_matches_measured_sentence).
- **하위호환 byte-동일** — `_claim_question("bent","leg") == _claim_question("bent","leg",None)`, 미등록 종류·expected_limb None·off_pole 전부 종전 그대로. 09-01 vlu 테스트 5건 무변경 통과.
- **무접촉 확인** — `_eye_verdict`, `_CLAIM_ENUM`/`_LIMB_ENUM`, 원장 필드, `machine_eye` 반환 형상, app.py 게이트 순서, `app/`, 계약: diff 0. 두 커밋의 변경 파일 = card_gates.py / test_card_gates.py / app.py(+3줄) 3건뿐.
- **좌/우 이름 0** — 새 힌트 6종 전부 `_assert_occlusion_question`(왼/오른/left/right 부재 포함) 통과.
- **하네스 시그니처** — `inspect.signature(cg.eye_judge).bind(crop, 'bent', api_key=..., expected_limb='leg', joint_kind='무릎')` 바인딩 성립, `cg.joint_kind_ko` 존재 (네트워크 호출 0, 키 미조회).

## Task 별 변경

### Task 1 — card_gates: joint_kind_ko + 힌트 변형 + 시그니처 통과 + 테스트 (`3016c7d1`)

`backend/shared/python/sunity_shared/analysis/card_gates.py`
- `_KIND_KO` (knee→무릎, elbow→팔꿈치, hip→엉덩이, shoulder→어깨, ankle→발목, wrist/hand→손목) + `_KIND_LIMB` (종류→arm/leg, `_LIMB_OF` 에서 유도) + `joint_kind_ko(joint)` (`split("_")[-1]` 관례, 미등록 None).
- `_KIND_SEGMENTS` (무릎: 허벅지와 정강이 / 엉덩이: 몸통과 허벅지 / 발목: 정강이와 발 / 팔꿈치: 위팔과 아래팔 / 어깨: 몸통과 위팔 / 손목: 아래팔과 손), `_ga_i(word)` 받침 조사 헬퍼, `_joint_kind_hint(expected_limb, joint_kind)` 순수 함수 (선행 공백 포함 1문장, 미등록/불일치는 "").
- `_claim_question(claim, expected_limb, joint_kind=None)`: 기존 본문 문자열 무변경, 끝에 `_joint_kind_hint` 결과를 이어붙임. docstring 에 09-03 측정 수치 인용.
- `eye_judge(..., expected_limb=None, joint_kind=None, ...)` → `_claim_question(claim, expected_limb, joint_kind)`; `machine_eye(..., joint_kind=None, ...)` → eye_judge 로 통과. 반환 형상 무변경.

`backend/tests/test_card_gates.py` — 신규 7건:
(a) joint_kind None/미등록/expected_limb None byte-동일 (b) 무릎/leg = 측정본 리터럴 + 공백 1 + "참고:" 1회 (c) 팔꿈치/arm 대칭 문형 리터럴 + 좌/우 0 (d) 6종 전부 조사 가/이 (정강이가·허벅지가·발이·아래팔이·위팔이·손이) (e) 종류↔사지 불일치 폴백 (f) off_pole + joint_kind 무변경 (g) `joint_kind_ko` 매핑 + POSE_BASIS_12 전부 `_KIND_LIMB == joint_limb`.

검증: `backend/.venv/bin/python -m pytest backend/tests/test_card_gates.py -q` → **19 passed** (기존 12 + 신규 7).

### Task 2 — pipeline: machine_eye 호출에 joint_kind 전달 + 전체 pytest (`e307009d`)

`backend/functions/pipeline/app.py` 5004-5011 (`_run_gated_card_inherit`): `joint_kind=cg.joint_kind_ko(gate_joint),` 1줄 + 출처 주석 2줄. 운영 경로 호출부는 이곳 1개뿐 (repo grep — `.aws-sam/` 빌드 사본 제외). harvest/스크립트 경로 없음.

검증: `backend/.venv/bin/python -m pytest backend/tests -q` → **4579 passed / 0 failed / 20 skipped** (62s). 기준선 4572 → +7 (전부 이번 신규), failed 0 유지. `py_compile` OK.

## 질문 전문 (무릎/leg, 운영 경로 = vlu 변형 + 힌트)

> 사진의 주황색 원은 관절 하나를 표시합니다. 원 주변에는 팔과 다리가 겹쳐 보일 수 있습니다. 판정 대상은 원 위치의 다리입니다. 원 위치에 다리가 보이면 — 다른 사지에 부분적으로 가려져 뒤에 있어도 — 그 다리가 '접혀 있음(bent)'인지 '펴져 있음(extended)'인지 판정하고 limb 필드에 그 사지 종류를 적으세요 (팔='arm', 다리='leg'). 원 위치와 그 바로 뒤 어디에도 다리가 보이지 않으면(표시가 엉뚱한 곳에 찍힌 경우), 원이 실제로 놓인 사지의 접힘/펴짐을 판정하고 limb 필드에 실제로 보이는 사지 종류를 적으세요 (그 외='other'). 원이 신체 위에 있지 않으면 observed 는 'off_body' 로 하세요. 참고: 이 원은 무릎 관절 표시이며, 팔이 무릎 앞을 가로질러 가릴 수 있습니다. 팔 뒤로 허벅지와 정강이가 이어지면 그 다리가 판정 대상입니다.

팔꿈치/arm 힌트: "참고: 이 원은 팔꿈치 관절 표시이며, 다리가 팔꿈치 앞을 가로질러 가릴 수 있습니다. 다리 뒤로 위팔과 아래팔이 이어지면 그 팔이 판정 대상입니다."

## Commits

| Task | Commit | 파일 |
|------|--------|------|
| 1 | `3016c7d1` | card_gates.py, test_card_gates.py |
| 2 | `e307009d` | functions/pipeline/app.py |

docs(SUMMARY·evidence·STATE) 커밋은 오케스트레이터 몫 — 이 파일은 미커밋.

## Deviations from Plan

**1. [소규모 추가] 종류↔expected_limb 불일치 방어** — `_joint_kind_hint` 는 `_KIND_LIMB[joint_kind] != expected_limb` 이면 힌트를 붙이지 않는다 (예: leg 에 '팔꿈치' 를 주면 "팔이 팔꿈치 앞을…" 같은 비문이 되므로). 계획 문구("등록된 joint_kind → 힌트")보다 한 조건 좁음. 운영 경로는 두 값을 같은 `gate_joint` 에서 유도하므로 영향 0; 테스트 (e) 로 고정. `_KIND_LIMB` 를 `_LIMB_OF` 에서 유도해 표 2벌 불일치 가능성을 없앰.

그 외 계획 그대로. 클라임 라이브 재분석(Pod)·하네스 실행은 계획대로 이 작업 밖.

## 오케스트레이터 후속 (계획 <verification>)

- `GEMINI_API_KEY=... backend/.venv/bin/python .planning/quick/260903-jka-eye-joint-kind/evidence/run_eye_regression.py 5` — 9 fixture 기대 판정, 결과 `evidence/eye_regression_results.json` 박제. 이 세션은 API 미호출·키 미조회.
- 클라임 라이브 재분석은 다음 Pod 세션 (착수점 누적).

## Known Stubs

없음.

## Threat Flags

없음 — 신규 네트워크/인증/파일 표면 0 (기존 Gemini 호출 경로에 질문 텍스트 1문장 추가만, 개인정보 미포함). API 키는 이 세션에서 조회·출력·기록 0.

## Self-Check: PASSED

3 파일 실물 존재 + 커밋 2건(3016c7d1, e307009d) git log 확인 + `def joint_kind_ko` / `joint_kind=cg.joint_kind_ko(gate_joint)` 마커 존재 + backend/ 미추적 파일 0. 라이브 하네스는 미실행(오케스트레이터 몫).
