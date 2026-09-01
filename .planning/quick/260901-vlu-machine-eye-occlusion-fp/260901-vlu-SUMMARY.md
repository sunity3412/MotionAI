---
phase: quick-260901-vlu
plan: "01"
subsystem: analysis-card-gates
tags: [machine-eye, gemini, occlusion, false-positive, card-gates]
requires: []
provides:
  - "card_gates._claim_question — expected_limb 반영형 기계 눈 질문 조립 (순수 함수)"
  - "card_gates.eye_judge — 마킹 크롭(PIL) 입력 판정 진입점 (운영 프롬프트·스키마 한 벌)"
affects: [pipeline-card-gates, harvest-eye-미영향(원장 필드 무변경)]
tech-stack:
  added: []
  patterns: ["질문 조립 순수 함수 분리 — 하네스가 운영 경로 그대로 재판정"]
key-files:
  created:
    - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/run_live_eye.py
    - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/live_eye_results.json
    - .planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/live_eye_run.log
  modified:
    - backend/shared/python/sunity_shared/analysis/card_gates.py
    - backend/tests/test_card_gates.py
decisions:
  - "off_pole 질문은 expected_limb 를 줘도 무변경 — 이번 수리 범위 밖 (계획 확정)"
  - "오클루전 변형에 _LIMB_QUESTION 접미 미부착 — limb 지시 본문 내장으로 중복/모순 방지"
  - "eye_judge 는 crop 미반환, machine_eye 가 첨부 — 공개 시그니처·원장 필드 전부 무변경"
metrics:
  duration: "~10분"
  completed: "2026-09-01"
  tasks: "2/2"
  live-rounds: "1회 (반복 불필요)"
---

# Quick 260901-vlu: 기계 눈 오클루전 위양성 수리 Summary

**One-liner:** 기계 눈 질문을 expected_limb 반영형으로 교정해 "뻗은 팔이 굽힌 무릎을 가리는" 프레임의 확정 카드 삭제 위양성을 제거 — 라이브 1회차에 오클루전 match=True 전환 + 마크-전위 match=False 유지 동시 성립.

## 판정: 된다

- **오클루전 (belle 실물, 이 수리의 존재 이유):** match=True 전환 — Gemini 가 "원 위치 뒤쪽으로 접혀 올라온 다리"를 판정 대상으로 잡음 (conf 0.95).
- **마크-전위 (ii0 kneepath, 1급 무회귀):** match=False 유지 — "원 위치에 다리가 존재하지 않으며" 실제 놓인 팔을 보고 → arm↔leg 확정 상충 차단 작동 (conf 0.95).
- **pytest:** 4548 passed / 0 failed / 20 skipped (기준선 >=4537 충족. +11 중 4건이 이번 신규, 나머지는 08-31~09-01 선행 작업분의 증가 — failed 0 유지).
- 반복 0회 — 초안 프롬프트가 1회차에 양방향 동시 성립. 프롬프트 재조정 없음.

## 수리 내용

### 원인 (관측 재현 완료본 — 계획 승계)

`machine_eye` 가 `expected_limb` 를 인자로 받으면서 프롬프트에는 쓰지 않아, 눈이
"원 위치에서 가장 앞에 보이는 사지"(뻗은 팔)를 답하면 `_eye_verdict` 의 arm↔leg
상충 차단이 정상 카드를 삭제했다. 원장 실측: right_knee 3.0s, claim=bent,
observed=extended, limb=arm, match=false, conf 0.95.

### 질문 전문 (전/후)

**전 (bent, 현행 = expected_limb=None 하위호환으로 계속 사용):**

> 사진의 주황색 원은 관절 하나를 표시합니다. 그 관절이 이루는 사지(팔 또는 다리)가 '접혀 있음(bent)'인지 '펴져 있음(extended)'인지 판정하세요. 원이 신체 위에 있지 않으면 'off_body'. 또한 원 안의 관절이 팔의 관절인지 다리의 관절인지 limb 필드로 함께 판정하세요 (팔='arm', 다리='leg', 그 외='other').

**후 (bent + expected_limb=leg — 라이브 성립본, prompt_sha256 79d4fd89...):**

> 사진의 주황색 원은 관절 하나를 표시합니다. 원 주변에는 팔과 다리가 겹쳐 보일 수 있습니다. 판정 대상은 원 위치의 다리입니다. 원 위치에 다리가 보이면 — 다른 사지에 부분적으로 가려져 뒤에 있어도 — 그 다리가 '접혀 있음(bent)'인지 '펴져 있음(extended)'인지 판정하고 limb 필드에 그 사지 종류를 적으세요 (팔='arm', 다리='leg'). 원 위치와 그 바로 뒤 어디에도 다리가 보이지 않으면(표시가 엉뚱한 곳에 찍힌 경우), 원이 실제로 놓인 사지의 접힘/펴짐을 판정하고 limb 필드에 실제로 보이는 사지 종류를 적으세요 (그 외='other'). 원이 신체 위에 있지 않으면 observed 는 'off_body' 로 하세요.

(arm 변형은 대칭 — "판정 대상은 원 위치의 팔입니다". 좌/우 해부학 이름 0,
_LIMB_QUESTION 접미 미부착, 응답 스키마 무변경.)

### 코드 변경 (backend/shared/python/sunity_shared/analysis/card_gates.py)

1. `_claim_question(claim, expected_limb)` 순수 함수 신설 — off_pole/None 은
   `_CLAIM_QUESTION[claim]` byte-동일 반환 (하위호환), bent/extended + arm/leg 만
   오클루전 반영 변형.
2. `eye_judge(crop, claim, *, api_key, expected_limb, model, timeout_s)` 추출 —
   JPEG 인코딩→Gemini 호출→`_eye_verdict` 를 크롭 입력형으로 분리. fail-closed
   (observed="error", match=False) 의미론 무변경.
3. `machine_eye` = claim 검증(ValueError) + `mark_crop` + `eye_judge` + crop 첨부.
   공개 시그니처·반환 형상·원장 필드 전부 동일 — app.py:4752 호출부(이미
   `expected_limb=cg.joint_limb(gate_joint)` 전달 중)와 harvest_eye 수확기 무접촉으로
   새 질문 자동 활성.

**무접촉 확인:** `_eye_verdict` diff 0 (ii0 §6-3 차단 유지), app.py diff 0, 채점
산식 파일 diff 0 (`git diff HEAD~2 --name-only` = card_gates.py + test_card_gates.py
2건뿐). 모델 문자열 하드코딩 0 (DEFAULT_C_MODEL 경유 유지).

## 라이브 판정 표 (Gemini 실호출 — evidence/live_eye_run.log)

| 회차 | 케이스 | 크롭 | 기대 | observed | limb | match | conf | reason (원문) |
|------|--------|------|------|----------|------|-------|------|----------------|
| 1 | A 오클루전 | evidence/eye_crop.png (belle 실물 right_knee 3.0s) | True | bent | leg | **True** | 0.95 | "원 위치 뒤쪽으로 접혀 올라온 다리(무릎 관절)가 위치해 있으며, 무릎이 강하게 굽혀진 상태(bent)입니다." |
| 1 | B 마크-전위 | 260811-ii0 evidence/eye_kneepath_user_left_knee.png | False | bent | arm | **False** | 0.95 | "원 위치에 다리가 존재하지 않으며, 원은 폴을 잡고 있는 팔의 상완/어깨 부위에 위치해 있습니다. 해당 팔은 팔꿈치 관절이 굽혀져 있으므로 bent로 판정됩니다." |

final = 1회차 그대로 (caseA.match=true / caseB.match=false). 모델 = gemini-3.7-flash
(DEFAULT_C_MODEL 해석값 — 기록용, 하드코딩 아님). API 키는 SSM→env 로만 주입,
로그·결과·하네스 3파일 키-누출 스캔 clean.

## 테스트 (TDD)

- RED `eb912c3`: `_claim_question` 불변식 3건 실패 확인 (AttributeError) + machine_eye
  미지 claim ValueError 유지 테스트.
- GREEN `7933985`: 구현 후 test_card_gates.py 12/12 PASS.
- 불변식만 단정 (전문 일치 금지): 하위호환 byte-동일 / 판정 대상 명시 / 가림·겹침
  언급 / 실제 사지 보고 지시 / 좌우 이름 0 (왼·오른·left·right 대소문자 무관) /
  off_body 유지 / _LIMB_QUESTION 접미 미부착.
- 전체 스위트: **4548 passed / 0 failed / 20 skipped** (49.5s, backend/.venv).

## 보존 자산 (evidence/ — scratchpad 휘발 대비, md5 대조 완료)

| 파일 | 내용 |
|------|------|
| eye_crop.png | belle 실물 오클루전 마킹 크롭 (Case A 입력, md5 8718e234...) |
| eye_ledger.json | 위양성 원장 원본 (observed=extended, limb=arm, match=false) |
| stage1_confirmed_card.png | 삭제됐던 확정 확대비교 카드 실물 |
| run_live_eye.py | 라이브 하네스 (cg.eye_judge 경유만 — 프롬프트 재구현 0) |
| live_eye_results.json | rounds/final 판정 기록 (prompt_sha256 포함) |
| live_eye_run.log | 실행 로그 (reason 원문 — 통과 주장의 증거) |

user.mp4/ref.mp4 는 evidence/ 미복사 (S3 원본 보존처 — 리포 비대화 방지, 계획 확정).

## Deviations from Plan

None - plan executed exactly as written. (라이브 반복 조항은 1회차 성립으로 미발동.)

## Commits

| Task | Commit | 내용 |
|------|--------|------|
| 1 (RED) | eb912c3 | test: expected-limb 질문 조립 불변식 (실패 확인 후 커밋) |
| 1 (GREEN) | 7933985 | feat: _claim_question + eye_judge 추출, machine_eye 재구성 |
| 2 | (미커밋) | evidence/ + SUMMARY 는 오케스트레이터가 belle 확인 후 커밋 |

## TDD Gate Compliance

RED(`eb912c3` test) → GREEN(`7933985` feat) 순서 성립. REFACTOR 커밋 없음 (불필요).

## Known Stubs

없음.

## Threat Flags

없음 — 신규 보안 표면 0 (기존 Gemini 추론 호출 경로 그대로, 신규 패키지 0).
T-vlu-01(키 노출) mitigate 이행: env-만 주입 + 박제 3파일 grep 스캔 clean.

## Self-Check: PASSED

산출물 9건 실물 존재 + 커밋 2건(eb912c3, 7933985) git log 확인. Task 2 자동 검증
(final caseA.match=true / caseB.match=false + 로그·크롭 실물) PASS. 키-누출 스캔 clean.
