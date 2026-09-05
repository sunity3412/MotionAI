---
phase: quick-260905-mvm
plan: "01"
subsystem: analysis-card-photo-audit
tags: [fault-zoom, machine-eye, audit, self-check]
requires: []
provides:
  - "card_gates claim 'part' — 완성된 카드 사진에서 정중앙 부위 토큰만 읽는 관측 claim (좌우·기대 관절 0 질문)"
  - "card_photo_audit.py — expected_parts / audit_card / is_mismatch 순수 대조 (numpy·boto3·네트워크 0)"
  - "scripts/audit_card_photos.py — Firestore 카드 → PNG 이등분 → 눈 다수결 → 대조, 마지막 줄 `card_photo_audit total=N mismatched=M`"
affects: [card_gates(추가만), fault-zoom 카드 통과 기준(다음 단위 후보)]
tech-stack:
  added: []
  patterns: ["눈은 관측, 대조는 순수 함수 — 기대값을 질문에 넣지 않는다 (bz5 부록 C 승계)", "패널당 N회 질문 최빈 토큰 확정 — temperature 0 도 토큰이 흔들린다"]
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/card_photo_audit.py
    - backend/scripts/audit_card_photos.py
    - backend/tests/test_card_photo_audit.py
    - backend/tests/test_audit_card_photos_script.py
    - .planning/quick/260905-mvm-card-photo-audit/evidence/ (run1·2 단발, run3·4 다수결 로그+JSON)
  modified:
    - backend/shared/python/sunity_shared/analysis/card_gates.py
    - backend/tests/test_card_gates.py
decisions:
  - "part 질문에는 enum 13 토큰을 중립 순서로 전부 나열 — 어느 것이 정답인지 드러내지 않으면서 한국어→토큰 매핑을 고정. 좌우 어휘 0 은 테스트로 강제"
  - "_eye_verdict(part) 는 판정하지 않는다 — PART_TOKENS 안이면 '읽어냈다'. enum 밖 문자열은 fail-closed False"
  - "스크립트의 rounds 는 eye_judge_majority 가 아니라 eye_judge N회 최빈 토큰 — 측정 근거 아래 Deviations 1"
  - "허용 집합은 plan 그대로 (neck·elbow 를 shoulder 에, knee 를 hip 에 넣지 않음) — 실측 1벌에 맞춰 넓히지 않는다. 경계 사례는 아래 표에 박제, 판정은 belle"
requirements-completed: []
metrics:
  duration: "약 77분 (16:29 → 17:46 KST, 그중 라이브 4런 ≈ 55분)"
  completed: "2026-09-05"
  tasks: "3/3"
  pytest: "4627 passed / 0 failed / 20 skipped (기준선 4602/0/20 + 신규 25)"
---

# Quick 260905-mvm: 확대 카드 사진 감사 도구 Summary

**One-liner:** 확대 카드 사진을 좌/우 패널로 갈라 기계 눈에 "정중앙 부위"만 묻고(좌우·기대 관절 0) 제목 부위와 순수 함수로 대조하는 계측기 — 09-03 라이브 21장에서 belle 가 짚은 2장 포함 대장 5건 중 4건이 매 실행 재현되고, 대장에 없던 3장이 추가로 걸렸다. 파이프라인 무접촉, backend 4627/0.

## 판정: 된다 (계측기로서). 대장 5/5 재현은 안 된다 — 4/5 + 신규 3.

- **된다:** 같은 21장을 다수결(3회)로 두 번 돌려 카드 판정 20/21 일치, 패널 토큰 40/42 일치. belle 가 먼저 찾은 pdshape 6.1s 오른팔꿈치(=등허리)·파워스핀 왼어깨(=무릎/허벅지)는 4런 전부 불일치.
- **안 되는 것:** 대장 #3 "엘보 오른팔꿈치 기준 패널=겨드랑이" 는 눈이 10/10 회 `elbow` 라 재현 안 됨 (사진: 폴을 감은 팔에 원 — 팔꿈치도 원 안에 있어 겨드랑이/팔꿈치 경계). 반대로 대장에 없던 3장을 눈이 안정적으로 걸었다 (아래 표).

## 라이브 검증 — 09-03 라이브 6문서 21장 (`gemini-3.8-flash`, temperature 0)

문서: `verifyupx0903b/bf929095…`(pdshape 2회차 6장) + `verifyupx0903/{c357f6b4 클라임 3, f5e8e134 파워스핀 2, 363fcea9 엘보 6, fb695059 킵업 1, 4cf49d80 피터팬 3}` = 21.

| 실행 | 방식 | total | mismatched | 비고 |
|---|---|---|---|---|
| run1 | 패널당 1회 | 21 | 8 | |
| run2 | 패널당 1회 | 21 | 8 | run1 과 **다른 8** — 토큰 5/42 변동, 카드 판정 2/21 뒤집힘 |
| run3 | 3회 최빈 | 21 | 7 | unreadable 1 (엘보 왼어깨 ref: knee/thigh/hip 1:1:1 동률) |
| run4 | 3회 최빈 | 21 | 8 | run3 대비 토큰 2/42 변동, 카드 판정 1/21 (클라임 참고 왼골반 ref: 2:1 이 양쪽으로) |

**카드별 (M=불일치, 순서 run1/2/3/4):**

| 카드 | user / ref 토큰 (run3) | 판정 | 대장 | 사진 확인 (오케스트레이터 2차 의견, belle 판정 아님) |
|---|---|---|---|---|
| pdshape [0] 오른팔꿈치 6.1s | back_waist / hand | MMMM | #1 belle | 정중앙 = 허리·등. 표시 없는 카드(userMarked=False) → part_not_shown |
| pdshape [2] 왼무릎 ref | knee / **elbow** | .MMM | 없음 | 폴 옆 위로 뻗은 사지에 각도선 — 팔인지 다리인지 내 눈으로 애매, 눈은 10회 중 7회 elbow |
| pdshape [3] 오른어깨 ref | shoulder / **neck**(head 1) | MMMM | 없음 | 정중앙 = 목·어깨 이음 — 인접 경계. 허용 집합에 neck 없음 |
| pdshape [5] 참고 왼어깨 | **head** / chest | MMMM | 없음 | 원이 얼굴 위 — 엘보 참고 카드와 같은 패턴 |
| 클라임 [1] 참고 왼골반 ref | thigh / knee↔thigh | MM.M | 없음 | 정중앙 = 골반·허벅지·무릎 사이 — 경계, 2:1 로 흔들림 |
| 파워스핀 [1] 왼어깨 | **knee** / armpit | MMMM | #2 belle | 각도선이 든 다리에 — 어깨 아님 |
| 엘보 [0] 오른팔꿈치 ref | shoulder / elbow | .... | #3 | 눈 10/10 elbow. 원 안에 팔꿈치·겨드랑이 둘 다 — 대장과 눈이 갈림 |
| 엘보 [1] 왼어깨 | **thigh** / unclear(다리 3종 동률) | MMMM | #4 | 두 패널 다 허벅지에 각도선 ("양쪽 허벅지" 그대로) |
| 엘보 [2] 오른어깨 ref | shoulder / shoulder | M... | 없음 | run1 단발 elbow 는 눈 오독 — 다수결에서 소멸 |
| 엘보 [5] 참고 왼어깨 | **head**(neck 1) / chest | MMMM | #5 | 원이 얼굴 위 |
| 나머지 11장 | — | .... | — | 4런 전부 정상 |

사진: `/Users/Shared/sunity-card-audit-260905/` (걸린 패널 9장 + `all_panels_42/`). 리포에는 인물 이미지 안 넣음.

## Task Commits

1. **Task 1 — card_gates `part` claim** — `f2a3640f` (feat)
2. **Task 2 — card_photo_audit 순수 모듈** — `10593941` (feat)
3. **Task 3 — audit_card_photos 스크립트** — `62656643` (feat)

## 한 일

### Task 1 (`f2a3640f`)
- `_CLAIM_QUESTION["part"]` "사진 정중앙에 가장 크게 보이는 신체 부위는 무엇입니까? …(13 토큰 중립 나열)… 분간이 안 되면 'unclear'." + 기존 `_LIMB_QUESTION` 접미. `_CLAIM_ENUM["part"]` 14 토큰, `PART_TOKENS`.
- `_claim_question`: `part` 는 `off_pole` 과 같은 분기 — 오클루전 변형·관절 종류 힌트 미부착 (기대가 새는 경로 차단). `_eye_verdict`: `part` 는 `observed in PART_TOKENS` 만.
- 기존 3 claim 질문·스키마·판정·`machine_eye` 코드 무변경 (테스트 `test_existing_claims_unchanged_by_part_addition`). 테스트 6종 — 좌우 어휘 0(왼/오른/좌/우측/left/right, 대소문자 무관), enum=plan, 관측 전용 verdict, urlopen 가로채기로 요청 본문(질문·enum·temp 0·모델) 박제.

### Task 2 (`10593941`)
- `expected_parts(criterion, joint)` — plan 표 그대로 (elbow→{elbow,hand,shoulder} / shoulder→{shoulder,armpit,chest,back_waist} / hip→{hip,thigh,back_waist,abdomen} / knee→{knee,thigh,foot}; split_angle·leg_extension·arm_extension; 참고 카드는 joint 파생). 미지 criterion 은 joint 폴백, 둘 다 미지면 빈 집합(감사 불가, 불일치 아님).
- `audit_card(...)` → `{userOk, refOk, flags}`; 표시 있는 측 `mark_mismatch`, 없는 측 `part_not_shown`, unclear/error/어휘 밖 `unreadable`(None), 관측 없음 `unobserved`. `is_mismatch` 헬퍼.
- 순수: numpy·boto3·urllib·card_gates import 0 (테스트로 강제), 어휘는 `card_gates.PART_TOKENS` 와 lockstep 테스트.
- 테스트 15: 대장 5 불일치 + 정상 3 (관측 하드코딩) → 순수 함수로 5/5 재현, 파생 규칙, 판정 불가 의미론.

### Task 3 (`62656643`)
- `--uid/--analysis-id | --pairs uid:aid,…`, `--rounds 3`(홀수), `--out JSON`, `--dump-dir`(패널 JPEG). Firestore → `faultZoomComparisons` → `imageUrl` 다운로드(실패 시 `imageKey` S3 폴백) → `_compose` 기하(정사각 2 + gap, 높이=패널 변)로 좌/우 복원 → 패널마다 `eye_judge(claim="part")` N회 최빈 토큰 → `audit_card`. 모델 `resolve_model("C")`, 키 `_load_api_key`(env → SSM).
- 마지막 줄 `card_photo_audit total=N mismatched=M`, 바로 위 `unreadable=K unaudited=J`. 파이프라인 무접촉, Firestore 쓰기 0.
- 테스트 4: `modal_token` 동률 fail-closed, `split_panels` 기하 복원/폴백, `parse_pairs`.

## 계획과 다르게 한 것

**1. [Rule 1 - Bug] 스크립트의 판정 확정을 `eye_judge_majority` 대신 `eye_judge` N회 최빈 토큰으로**
- **발견:** Task 3 라이브 검증. `part` claim 에서 `eye_judge_majority` 의 "불일치"는 unclear/error(못 읽음)뿐이라 읽어낸 토큰은 1회차에 확정된다 → `--rounds` 가 아무것도 안 한다. 실측: 같은 21장 단발 2회(run1·run2)에서 패널 토큰 5/42 변동, 카드 판정 2/21 뒤집힘 — plan 의 done "같은 입력에 같은 판정" 이 성립하지 않았다.
- **처리:** `judge_panel` 이 `eye_judge` 를 rounds 회 호출하고 `modal_token`(PART_VOCAB 안 최빈, 동률·전부 못 읽음 = unclear)으로 확정. 질문·스키마·판정은 eye_judge 그대로 — 표만 센다 (`eye_judge_majority` 가 match 표를 세는 것과 같은 자리, 대상만 토큰). 결과: 다수결 2회(run3·run4) 토큰 2/42 변동, 판정 1/21. 비용 3배(카드당 6 호출, 21장 ≈ 14분).
- **파일:** `backend/scripts/audit_card_photos.py`, `backend/tests/test_audit_card_photos_script.py`. **커밋:** `62656643`.

**2. [fixture 정정] 엘보 왼어깨 케이스의 ref 관측을 shoulder → thigh**
- 대장 원문이 "양쪽 허벅지"였고 사진(`363fcea9_01_…_ref.jpg`)도 허벅지에 각도선. 첫 작성 때 한쪽만 틀린 것으로 넣었던 것을 커밋 전 정정 (`62656643` 에 포함).

**3. [범위 유지] 허용 집합을 실측에 맞춰 넓히지 않음**
- 눈이 건 신규 3장 중 2장(오른어깨 ref=neck, 참고 왼골반 ref=knee)은 인접 경계다. shoulder 에 neck 을, hip 에 knee 를 넣으면 이번 21장은 줄지만 plan 이 잡으려는 종류("팔꿈치 카드가 등허리")와 "무릎 중심의 골반 카드"를 구분 못 하게 된다. 판정은 belle (사진 경로 위) — 사진별 ○× 를 묻지는 않는다 (09-03 규칙).

## 검증 방식 (verify 대응)

- Task 1: `test_card_gates.py` 41 passed (기존 35 + 신규 6). `eye_judge(crop, "part")` 가 부위 토큰 반환 — 라이브 42 패널 × 4런에서 error 0, unclear 는 다수결 동률 1건뿐.
- Task 2: `test_card_photo_audit.py` 15 passed — 대장 5 불일치 + 정상 3, 순수 함수로 5/5.
- Task 3: `--help` 동작. 라이브 4런 로그·JSON = `evidence/`. 게이트 `cd backend && .venv/bin/python -m pytest -q` → **4627 passed / 0 failed / 20 skipped** (51s). `rtk pytest` 는 시스템 pytest 라 venv 경로 사용.

## 다음 단위 후보 (이번 범위 밖 — plan "하지 않는 일")

- **통과 기준 승격:** 09-03 "6/6 PASS" 가 장수만 세는 것을 이 감사로 보강할지 — 분석 시점 게이트로 붙이면 카드당 6 호출(≈40s) 추가, 불일치 시 처분(사진을 다른 순간으로 옮길지) 별도 결정.
- **원인 수리:** 걸린 카드의 공통 패턴 = 어깨/팔꿈치 카드 표시가 다리·머리 위 (파워스핀·엘보 왼어깨 → 다리, 참고 왼어깨 2장 → 머리) — keypoint 환각 순간에 crop. 게이트 미달 좌표로 crop 금지가 plan 의 다음 단위.
- 경계 사례(neck↔shoulder, knee↔hip 참고 카드, 겨드랑이↔팔꿈치) 의 허용 집합은 belle 사진 판정 후.

## Known Stubs

없음.

## Threat Flags

없음 — 새 네트워크 표면 없음(기존 Gemini generateContent·Firestore read·S3 GET 재사용), Firestore 쓰기 0, 인물 이미지는 리포 밖(`/Users/Shared`, scratchpad).

## Self-Check: PASSED

- 생성 파일 6건 존재 확인 (모듈·스크립트·테스트 2·evidence 2), 태스크 커밋 3건(`f2a3640f`·`10593941`·`62656643`) git log 에 존재.
- 미커밋 = `.planning/quick/260905-mvm-card-photo-audit/` (SUMMARY·evidence — 오케스트레이터 docs 커밋 몫). STATE.md·ROADMAP.md 무접촉.
