---
phase: 33-result-trust-recovery
plan: 09
subsystem: presentation-phrasebook
tags: [a-track, a-2, coach-voice, phrasebook, d-02, d-14, data-only]
requires:
  - "33-08 (33-A1-MOTION-STANDARDS.md — 동작 x 4질의 표, 방향 실측 원천)"
  - "33-20 (33-COVERAGE-MATRIX.md — canonical 10등재+1미등재 인벤토리)"
  - "candidate substrate phase33-cm3-run1 (33-17 shadow resolver 경로 — 방향 게이트 기준 프레임)"
provides:
  - "backend/data/phrasebook.json 동작 전용 entry 54건 (등재 9동작 x 방출 criterion, climb=의도된 0)"
  - "backend/tests/phase33/test_phrasebook_motion_specific.py (override 우선순위 + 천장 금지 + 키 유효성 + coverageMatrix lockstep + 금지어 게이트)"
affects:
  - "33-10 (A-3 크롭 — 같은 A-1 ④열 소비)"
  - "33-16 (phase gate — 실기기에서 신규 큐 음성/자막 확인)"
tech-stack:
  added: []
  patterns:
    - "motion-specific phrasing override (표현만 동작-조건부, 채점 무접촉 — technique-conditional 철학의 카피 레이어 적용)"
    - "direction hard-gate: authored cueLine 전수를 candidate ref-frame 기하 predicate 로 검사 (fail-closed beats confident-wrong)"
key-files:
  created:
    - backend/tests/phase33/test_phrasebook_motion_specific.py
  modified:
    - backend/data/phrasebook.json
decisions:
  - "override scope = 실방출 조합만: 6 fixture 동작은 phase25 sweep fault activatedCriteria 실측(25건), fixture-less 4동작은 A-1 대체 행의 criteria yaml 6관절 + techniqueProfile expects_extension(29건) — 198셀 전면 작성 아님"
  - "ref-climb override 0 = 의도(비교 게이트 전용, activatedCriteria=None) / ref-combo = __common__ 유지 (COVERAGE-MATRIX consumer contract)"
  - "UNVERIFIED claim(파워스핀 위 다리 좌우 라벨, 사이드웨이 스핀 척추 아치)은 어떤 큐에도 미사용 — 큐는 기능 역할(위 다리/훅 무릎/그립 팔)로 지칭"
  - "기준 관절이 mid-굽힘(훅/접힘/엘보 그립)인 조합은 방향 지시 없이 '모양 유지+겹쳐 맞추기' 큐만 (편차 부호 미상 — 오답 방향 지시 원천 차단)"
metrics:
  duration: "21m"
  tasks: 2
  files: 2
completed: 2026-07-28
---

# Phase 33 Plan 09: A-2 동작 전용 코칭 문구 (phrasebook motion-specific) Summary

**한줄 요약:** phrasebook.json 에 등재 동작 x 방출 criterion 전용 entry 54건을 작성해
power-spin 이 더 이상 "천장" 큐를 말하지 않게 했고(수직 스플릿 큐로 교체), 전 cueLine 을
reprocessed candidate 프레임 기하 predicate 로 전수 대조(54/54 PASS)했다 — 코드 변경 0
(phrasebook.py byte-무변경), Polly 음성+자막이 같은 문자열을 읽으므로 데이터 수정 한 번으로
둘 다 고쳐진다.

## 수행 내용

### Task 1 — RED: test_phrasebook_motion_specific.py (commit 9c10534)

- `test_motion_specific_overrides_common`: ref-power-spin x leg_extension 이 미등재 동작의
  `__common__` cueLine 과 달라야 함 — 작성 전 RED (공통 '천장' 큐로 fall-through 하는 것을
  정확히 잡음), Task 2 후 GREEN.
- `test_power_spin_leg_cue_not_ceiling`: D-14 헤드라인 케이스 박제 — 천장 리터럴 금지.
- `test_motion_specific_keys_are_valid`: 전용 키 = REGISTERED_MOTIONS 실존 동작 x __common__
  실존 criterion, exerciseId = corrective_exercises defects 실존 키 (fabrication 0).
- `test_coverage_matrix_lockstep`: `_meta.coverageMatrix.motionOverrides` == 실제 entries.
- phase32 금지어 게이트(수치/%/금지 리터럴 + sanity ≥ 50) verbatim 재사용 — 신규 카피가
  자동으로 게이트 스코프에 들어감.
- RED 확인: 3 failed (데이터 부재) / 10 passed (게이트·폴백 회귀 방어).

### Task 2 — 전용 entry 54건 작성 + 방향 하드 게이트 (commit 5065a1a)

- **6-슬롯 동일 스키마**로 `{motion}.{criterion}` entry 54건 추가. `_meta` lockstep 갱신:
  schemaVersion 1.1.0, cellRule 개정(override 레이어 설명), `motionOverrides` 단일 원천 추가,
  evidence 에 방향 대조 방법 기록.
- **직접 열어 확인 (D-19):** Firestore `reference/{id}/versions/phase33-cm3-run1` 을 읽기
  전용으로 열어 (F,17,2) 재구성 → A-1 peak window 프레임별 다리 방향각·무릎/팔꿈치각·
  벌림각·인버전을 재산출(probe), authored 전 조합의 emitted cueLine 값을 assemble_phrases
  로 출력하고 조합별 기하 predicate 로 검사(gate). 스크립트는 세션 scratchpad, write 0.
- **게이트 결과: 54/54 PASS, 모순 0 → fail-closed 강등 0.** (작성 자체를 A-1 실측
  방향에서만 시작했고, UNVERIFIED claim 은 처음부터 큐에 넣지 않은 결과.)
- 회귀 방어: phase32 phrasebook/emission/coach_audio/terminology 테스트 포함 74 passed.
- `git diff` = backend/data/phrasebook.json 단독 (tests/phase33 는 Task 1 커밋) —
  phrasebook.py byte-무변경(code-change-0), 채점 파일 무접촉 (D-20).

## Authored vs fail-closed 전수 목록 (D-18)

**Authored (54 — 전부 방향 게이트 PASS):**

| 동작 | 조합 | 방향 근거 (candidate 실측) |
|---|---|---|
| ref-power-spin (4) | leg_extension, angle_vs_reference__{left_hip, right_hip, left_shoulder} | f71~f92 수직 스플릿(한 다리 155~180° 위/반대 0~33° 아래), 무릎 med 171/174 신전. '천장'/'옆으로' 금지어 검사 통과 |
| ref-peter-pan (3) | angle_vs_reference__{left_shoulder, right_elbow, right_knee} | f18~f54 오른무릎 hook med 60 / 왼무릎 신전 med 177 (33-08 정정 계승), 그립 팔꿈치 med 174 신전 |
| ref-elbow-twist-sister (7) | angle_vs_reference__{left_elbow, right_elbow, left_knee, right_knee, left_shoulder, right_shoulder, left_hip} | 엘보 그립 팔꿈치 med 92/83 굽힘(감음 큐), 상하 가위 스플릿 실재(open max 178) |
| ref-pdshape (8) | angle_vs_reference__ 8관절 전부 | 무릎 med 90/48 깊은 접힘 — "무릎을 펴는 게 아니라" 역-신전 큐, 그립 팔꿈치 med 55/48 |
| ref-kip-up (3) | angle_vs_reference__{left_shoulder, right_shoulder}, split_angle | 스트래들 open max 79°, 무릎 med 174/174 신전 |
| ref-invert (8) | split_angle, leg_extension, angle_vs_reference__{knees, hips, shoulders} | f63 벌림각 152° 일자 찢기(max 175), 무릎 med 174/172 신전 |
| ref-foxtop (6) | angle_vs_reference__{knees, hips, shoulders} | f164~f183 수직 스플릿 실재, 무릎 med 168/169 신전 |
| ref-foxtop-split (7) | split_angle, angle_vs_reference__{knees, hips, shoulders} | f108 펼침각 98.8°(max 107), 신전측 kneeL med 170 / 훅측 kneeR med 92 |
| ref-sideway-spin (8) | leg_extension, arm_extension, angle_vs_reference__{knees, hips, shoulders} | 무릎 med 174/176 신전, 그립 팔꿈치 med 176 신전. 아치 곡률(UNVERIFIED) 큐 미사용 |

**Fail-closed 강등 (0):** 방향 모순으로 삭제된 큐 없음 — 작성 원천을 A-1 검증 claim 으로
한정하고 UNVERIFIED/부호-미상 조합은 처음부터 방향 지시를 넣지 않는 방식으로 게이트를
설계 단계에서 통과시켰다. (모순 발생 시 절차: cueLine/exerciseId/exerciseReason 삭제 →
statusLine/whyLine/coachQuestion 3-슬롯 entry 로 잔류.)

**의도된 미작성 (조용한 스킵 아님, D-23):**

- `ref-climb` — mode1 비교 게이트 전용(sweep status=comparison, activatedCriteria=None,
  점수/감점 record 방출 0) → 전용 entry 를 만들 조합 자체가 없음. COVERAGE-MATRIX (a) 항.
- `ref-combo` — 미등재 → `__common__` 경로 유지가 설계 (COVERAGE-MATRIX (c) 항).
  `test_unregistered_motion_still_falls_to_common` 이 이 폴백을 회귀 방어.
- fixture-less 4동작의 elbow per-joint 조합 — criteria yaml 박제 6관절(어깨/힙/무릎) 밖
  → A-1 대체 행 scope 밖이라 미작성. 방출 시 `__common__` 의 방향 중립("겹쳐 맞추기")
  큐로 떨어지므로 오답 방향 지시 위험 0.

## Deviations from Plan

### 1. [계획 문면 stale — 33-08 정정 계승] power-spin 큐는 "옆으로" 가 아니라 수직 스플릿

- 계획 Task 2 action 은 "power-spin leg cue says 옆으로, not 천장" 이라 지시했으나, Wave 1
  (33-08)이 실측으로 "옆(스트래들)" 도 오답임을 확정했다(폴 축 상하 수직 스플릿). 오케스트레이터
  track_context 와 33-A1 표를 따라 **위·아래 다리를 구분하는 수직 스플릿 큐**로 작성했고,
  게이트에 '천장'과 '옆으로' 둘 다 금지어로 넣어 검사했다.

### 2. [계획 문면 stale — belle A-트랙 우선 결정] "post-flip substrate" → candidate 직접 대조

- 계획 objective 의 "REPROCESSED reference frames (post-flip substrate)" 는 flip(33-07) 이연
  결정(2026-07-28, 계획 상단 수정 노트) 이후 **staged candidate** (reference/{id}/versions/
  phase33-cm3-run1) 를 뜻한다. 방향 게이트는 candidate 문서를 읽기 전용으로 직접 열어
  수행했다 — flip 후 활성화될 데이터와 동일하므로 flip 시 재작업 없음.

### 3. [Rule 2 — 검증 장치 추가] 계획 명세 밖 테스트 2건 추가

- `test_power_spin_leg_cue_not_ceiling` (D-14 헤드라인 회귀 방어)와
  `test_coverage_matrix_lockstep` (_meta 와 entries drift 차단), 전용 키 유효성 테스트를
  계획의 behavior 명세(override + forbidden)에 더해 추가했다 — "틀리면 걸리는 장치" (D-18)
  강화 목적, 코드 무변경 데이터 검증만.

## Self-Check: PASSED

- [x] `backend/data/phrasebook.json` `ref-power-spin.` 키 실존 (grep 4건) + JSON valid
- [x] `backend/tests/phase33/test_phrasebook_motion_specific.py` 존재, `assemble_phrases` 포함
- [x] pytest 13/13 (파일 단독) + 74/74 (phase32 회귀 포함)
- [x] phrasebook.py byte-무변경, git diff 스코프 = data + tests/phase33
- [x] commit 9c10534 (Task 1 RED) / 5065a1a (Task 2 GREEN) 존재
- [x] STATE.md / ROADMAP.md 무접촉 (worktree 모드 — 오케스트레이터 소관)
