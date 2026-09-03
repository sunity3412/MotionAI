---
phase: quick-260903-jxn
plan: "01"
status: complete
subsystem: analysis-card-gates
tags: [machine-eye, gemini, occlusion, false-positive, card-gates, joint-kind, majority-vote]
requires: [quick-260903-jka]
provides:
  - "card_gates._HINT_KINDS = {무릎, 팔꿈치, 발목, 손목} — 관절 종류 힌트는 사지 중간 관절에만, 엉덩이·어깨는 jka 이전 질문 byte-동일"
  - "card_gates.eye_judge_majority(crop, claim, *, api_key, expected_limb, joint_kind, model, timeout_s, max_rounds=3) — 불일치 시만 최대 3회 다수결, 반환 = eye_judge 형상 + rounds/votesTrue/votesFalse"
  - "card_gates.machine_eye(..., majority=False) — True 면 다수결, 기본은 종전 단발"
  - "pipeline app.py 운영 경로 majority=True + eye_ledger 항목에 rounds 추가 필드 + 판정마다 eye 로그 1줄"
affects: [pipeline-card-gates]
tech-stack:
  added: []
  patterns: ["다수결은 eye_judge 위에서 표만 센다 — 질문·스키마·_eye_verdict 무접촉, 일치 시 추가 호출 0"]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/card_gates.py
    - backend/tests/test_card_gates.py
    - backend/functions/pipeline/app.py
decisions:
  - "힌트 게이트는 _HINT_KINDS 한 곳 — _KIND_SEGMENTS(6종)·joint_kind_ko 는 그대로 두어 belle 판정(엉덩이·어깨 눈 게이트 제외 여부) 후 집합 1줄로 되돌릴 수 있게 함"
  - "다수결은 계획 문자 그대로 (max_rounds-1)회 추가 호출 — 조기 종료(F,F 에서 3회째 생략) 미적용, rounds 의미 = 총 호출 수 단순 유지"
  - "eye_ledger 는 rounds 만 추가 (votesTrue/votesFalse 는 반환 dict 에만) — 원장 필드 최소 추가"
metrics:
  duration: "~15분"
  completed: "2026-09-03"
  tasks: "2/2"
  pytest: "4586 passed / 0 failed / 20 skipped (기준선 4579 + 신규 7)"
---

# Quick 260903-jxn: 기계 눈 힌트 사지 중간 관절 한정 + 불일치 시 3회 다수결 Summary

**One-liner:** jka 관절 종류 힌트를 무릎·팔꿈치·발목·손목에만 붙이고(엉덩이·어깨는 09-03 측정에서 힌트가 3/5→1/5 로 판정을 해쳐 jka 이전 질문으로 복귀), 기계 눈 첫 판정이 불일치일 때만 같은 크롭에 최대 2회 더 물어 3회 다수결로 확정하는 `eye_judge_majority` 를 추가해 운영 경로(`machine_eye(majority=True)`)에 배선 — 일치 시 추가 호출 0, 원장에는 `rounds` 추가 필드만.

## 판정: 코드·테스트 성립 (라이브 회귀 `--majority` 하네스는 오케스트레이터 몫)

- **엉덩이/어깨 byte-동일** — `_claim_question(claim, "leg", "엉덩이") == _claim_question(claim, "leg")`, 어깨/arm 동일, bent/extended 양쪽, "참고:" 0 (test_claim_question_torso_kinds_no_hint_byte_identical). `joint_kind_ko` 는 여전히 엉덩이/어깨 반환 — 호출측 무변경.
- **4종 힌트 유지** — 무릎/발목/팔꿈치/손목은 vlu 변형 + 공백 1 + "참고:" 1문장, 조사 가/이 유지. 무릎/leg 측정본 리터럴 테스트(jka) 무변경 통과.
- **다수결 대본 검증(네트워크 0)** — `eye_judge` 를 monkeypatch: `[True]` → 호출 1·rounds 1; `[F,T,T]` → True·rounds 3·반환 r1(True 쪽 첫 결과); `[F,F,T]` → False·반환 r0; `[F,error,T]` → error 는 False 표 → False; max_rounds 0/2/4 → ValueError·호출 0, 5 는 허용.
- **하위호환** — `machine_eye(..., majority=False)` 기본은 종전 단발, 반환에 rounds/votes 키 없음 (test_machine_eye_majority_kwarg). `eye_judge` 시그니처·본문 무변경.
- **하네스 시그니처** — `inspect.signature(cg.eye_judge_majority).bind(crop, 'bent', api_key=..., expected_limb=..., joint_kind=...)` 바인딩 성립, 반환에 `rounds` 포함 (하네스가 `calls += r["rounds"]` 로 누적).
- **무접촉 확인** — `_eye_verdict`, `_CLAIM_ENUM`/`_LIMB_ENUM`/response_schema, app.py 게이트 순서(hold→pair→eye), 원장 기존 필드(side/joint/frameIdx/sec/trackAngleDeg/claim/observed/limb/match/confidence/reason/png) 이름·순서·의미, `app/`, 계약: diff 0. 두 커밋의 변경 파일 = card_gates.py / test_card_gates.py / app.py 3건뿐. Gemini 호출·API 키 조회·출력 0.

## Task 별 변경

### Task 1 — card_gates: `_HINT_KINDS` 한정 + `eye_judge_majority` + `machine_eye(majority=)` + 테스트 (`84265478`)

`backend/shared/python/sunity_shared/analysis/card_gates.py`
- `_HINT_KINDS = frozenset({"무릎", "팔꿈치", "발목", "손목"})` (주석에 09-03 측정: 엉덩이 3/5→1/5, 어깨 5/5 였으나 몸통 관절이라 보수적 제외).
- `_joint_kind_hint`: `joint_kind not in _KIND_SEGMENTS` → `not in _HINT_KINDS` 로 게이트 교체 (limb 불일치 방어는 그대로). `_KIND_SEGMENTS`·`joint_kind_ko`·`_KIND_LIMB` 무변경.
- `eye_judge_majority(...)`: 1회 `eye_judge`; match=True 면 `dict(결과) + rounds=1, votesTrue=1, votesFalse=0`. False 면 (max_rounds-1)회 추가 호출 → `votes_true > len/2` 로 승자 결정 → 승자 쪽 **첫** 결과 dict 복사 + `rounds`(총 호출 수)/`votesTrue`/`votesFalse`. `bool(r.get("match"))` 로 세어 observed="error" 는 자동 False 표. `max_rounds < 1 or 짝수` → ValueError.
- `machine_eye(..., majority: bool = False)`: `judge = eye_judge_majority if majority else eye_judge` — 나머지 본문 동일, crop 첨부 동일.

`backend/tests/test_card_gates.py` — 신규 7건 + 기존 1건 갱신:
- (갱신) `test_claim_question_hint_particles_all_kinds`: 6종 → `_HINT_KINDS` 4종, `_HINT_KINDS <= set(_KIND_SEGMENTS)`, `q.startswith(base + " 참고: ")`, "참고:" 1회.
- (a) `test_claim_question_torso_kinds_no_hint_byte_identical` (b) 위 갱신 테스트 (c) `_scripted_eye_judge` 헬퍼 + `test_eye_majority_first_match_no_extra_calls` / `_false_then_true_true_flips_to_true` / `_false_false_true_stays_false` / `_error_counts_as_false_vote` (d) `test_eye_majority_even_max_rounds_rejected` + `test_machine_eye_majority_kwarg`.

검증: `backend/.venv/bin/python -m pytest backend/tests/test_card_gates.py -q` → **26 passed** (jka 19 + 신규 7).

### Task 2 — pipeline: `majority=True` + 원장 `rounds` + eye 로그 1줄 (`bf3f0e3f`)

`backend/functions/pipeline/app.py` `_run_gated_card_inherit` → `_eye_check` (5000-5043):
- `cg.machine_eye(..., majority=True)` 1줄 + 출처 주석(quick-260903-jxn, 측정 수치, "불일치 시만 재질문 — 일치 시 호출 0", `cg.eye_judge_majority` 지목).
- `log.info("card_gates eye side=%s joint=%s idx=%d claim=%s observed=%s limb=%s match=%s rounds=%d", ...)` — 판정마다 1줄 (배선 증거는 실행 로그로).
- `eye_ledger.append` dict 에 `"rounds": int(res.get("rounds", 1))` — `reason` 다음·`png` 앞 추가, 기존 필드 무변경. S3 `ledger.json` 직렬화 경로는 `png` 만 pop 하므로 `rounds` 는 그대로 실린다.
- `eye_calls` 카운터 의미(machine_eye 호출 수) 무변경 — 실제 Gemini 호출 수는 원장 `rounds` 합.

검증: `backend/.venv/bin/python -m pytest backend/tests -q` → **4586 passed / 0 failed / 20 skipped** (51s). 기준선 4579 → +7 (전부 이번 신규), failed 0 유지. `py_compile` OK.

## Commits

| Task | Commit | 파일 |
|------|--------|------|
| 1 | `84265478` | card_gates.py, test_card_gates.py |
| 2 | `bf3f0e3f` | functions/pipeline/app.py |

docs(SUMMARY·evidence·STATE) 커밋은 오케스트레이터 몫 — 이 파일은 미커밋. ROADMAP 무변경.

## Deviations from Plan

None - plan executed as written. 두 가지 선택만 기록:
- 다수결은 계획 문자대로 첫 불일치 후 항상 (max_rounds-1)회 추가 호출 — `[F,F]` 에서 3회째를 생략하는 조기 종료는 넣지 않았다 (결과 동일, `rounds` = 총 호출 수 의미 단순 유지). 비용이 문제되면 1줄로 추가 가능.
- `_KIND_SEGMENTS` 의 엉덩이/어깨 항목은 데이터로 남김 — 게이트는 `_HINT_KINDS` 한 곳 (belle 판정 후 되돌리기 1줄).

## 오케스트레이터 후속 (계획 <verification>)

- `GEMINI_API_KEY=... backend/.venv/bin/python .planning/quick/260903-jxn-eye-midlimb-majority/evidence/run_eye_regression.py 5 --majority` → 기대: 클라임 2크롭·팔꿈치·어깨·extended 무릎 5/5, kneepath 0/5, 엉덩이 2건은 REPORT(기대 미확정 — belle 항목). 결과 `evidence/eye_regression_results_majority.json`. 이 세션은 API 미호출·키 미조회.
- 클라임 라이브 재분석 = 다음 Pod 세션 (착수점).
- belle 판정 항목: 눈 게이트에서 엉덩이·어깨 제외 여부 (엉덩이 판정 자체 신뢰도 3/5).

## Known Stubs

없음.

## Threat Flags

없음 — 신규 네트워크/인증/파일 표면 0. 기존 Gemini 호출 경로가 불일치 시 최대 2회 더 호출될 뿐 (같은 크롭·같은 질문, 개인정보 미포함). API 키는 이 세션에서 조회·출력·기록 0.

## Self-Check: PASSED

3 파일 실물 존재 + 커밋 2건(84265478, bf3f0e3f) git log 확인 + `def eye_judge_majority` / `_HINT_KINDS` (card_gates.py), `majority=True` / `eye_judge_majority` / `"rounds"` (app.py) 마커 존재 + backend/ 미추적·미커밋 변경 0. 라이브 `--majority` 하네스는 미실행(오케스트레이터 몫).
