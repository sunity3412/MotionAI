---
id: 260910-woq
title: 운동 식별자를 표시 이름과 분리
date: 2026-09-10
status: planned
---

# 이름을 바꾸면 과거 분석이 끊긴다

## 증상 (시뮬레이터 실물 관측, 2026-09-10)

`quick-260910-vwh` 가 운동 이름 29개를 영문 → 한글로 바꾼 직후, 기존 분석의
'전체 보완 운동 보기' 모달이 **"이번 분석에서 짚인 보완 부위가 없어요"** 빈 상태가 됐다.
같은 doc 이 이름 교체 **전에는 "어깨 안정화" 5줄을 정상 표시**했다 (같은 세션에서 직접 확인).

## 원인 (코드로 확정)

`app/src/lib/exerciseSections.ts:60-67` — 섹션 선택이 **운동 이름 문자열 비교**다:

```
const wantedNames = new Set(query.exerciseNames ?? []);
... wantedNames.has(s.exercises[0].name)
```

- `query.exerciseNames` = 저장된 doc 의 `result.recommendedExercises[].name` (분석 당시 스냅샷)
- `s.exercises[0].name` = **지금 라이브러리**의 이름

이름을 바꾸면 이 둘이 어긋나 **매칭이 0** 이 된다. 같은 파일 `:74-78` 의 중복 제거도 이름 키다.

**이것은 시뮬레이터만의 문제가 아니다.** 배포하면 **이름 교체 이전에 만들어진 모든 사용자의
모달이 빈 화면**이 된다. belle 이 앞으로 문구를 또 다듬을 때마다 같은 일이 반복된다.

**근본 원인: 이름이 표시 문자열이자 조인 키를 겸하고 있다.** 표시는 바뀌어야 하고 조인 키는
바뀌면 안 되는데 한 필드가 둘을 맡고 있다.

## 처방 — 안 변하는 식별자를 도입하고, 이름은 표시 전용으로

### Task 1 — 라이브러리에 `id` 부여

**files**: `backend/data/corrective_exercises.json`, `app/src/data/corrective_exercises.json`
(byte 동기 — 게이트 `backend/tests/phase13/test_corrective_exercises_app_lockstep.py`)

- 각 운동 항목에 `id` 를 추가한다. **영문 스네이크 케이스**, 원래 영문명에서 유도
  (예: `Push-ups` → `push_ups`, `Scapular Depression Drills` → `scapular_depression_drills`).
  ★ **한글 이름에서 만들지 마라** — 이름이 또 바뀌어도 id 는 그대로여야 한다.
  ★ 영문명은 `git show 9ceca050~1:backend/data/corrective_exercises.json` 에서 얻어라.
- 같은 운동이 여러 그룹에 있으면 **같은 id**. 서로 다른 운동은 **다른 id**.
  전수로 세어서 확인하라 (28개 유니크 예상 — vwh Task 4 로 하나 줄었다).
- `sourceRef` / `setsReps` / `purpose` / `kind` / `avoid` / `triggers` 무접촉.

### Task 2 — 조인을 id 로, 이름은 표시 전용

**files**: `app/src/lib/exerciseSections.ts`, `app/src/types/analysis.ts`,
`backend/shared/python/sunity_shared/analysis/exercise_map.py`,
`backend/shared/python/sunity_shared/models.py`, `docs/contract.md`,
`app/src/data/correctiveExercises.ts`, 관련 테스트

- 백엔드가 `recommendedExercises[]` 에 **`id` 를 함께 실어** 앱까지 보낸다 (계약 3벌 동시 수정).
- `exerciseSections.buildExerciseSections` 의 선택·중복제거를 **id 기준**으로 바꾼다.
- ★ **레거시 폴백 필수**: `id` 가 없는 옛 doc(오늘 이전 전부)은 **이름으로 매칭**한다.
  그 doc 들은 옛 영문 이름을 들고 있으므로, 라이브러리의 **`id` → 옛 영문명** 표가 필요하다.
  그 표를 어디에 둘지 정하고 주석으로 근거를 남겨라. (제안: 라이브러리 항목에 `legacyName`
  필드를 두고, 폴백이 그것과도 비교한다. 다른 방법이 더 깨끗하면 그것을 쓰되 이유를 적어라.)
  **폴백이 없으면 오늘 이전 분석이 전부 빈 모달이 된다 — 이 Task 의 존재 이유다.**
- 백엔드 `exercise_map` 의 dedup 도 **id 기준**으로 바꾼다 (지금은 name 기준).
  단 라이브러리 자체가 정합하면 결과는 같아야 한다 — 4개 doc 실측으로 확인하라.

### Task 3 — 재발 방지 테스트

**files**: 앱·백엔드 테스트

반드시 덮을 축:
1. **id 가 바뀌지 않은 채 name 만 바뀌어도 섹션 매칭이 유지된다** ← 이 결함의 직접 재현
2. `id` 없는 레거시 doc(옛 영문명) → 폴백으로 매칭된다
3. `id` 도 이름도 안 맞는 doc → 빈 목록 (조용한 오매칭 금지)
4. 라이브러리 id 유니크성 (중복 id 가 들어오면 실패)
5. 같은 운동이 여러 그룹에 있을 때 id 가 동일한지

**verify**:
```
cd backend && python3 -m pytest -q --continue-on-collection-errors
cd app && npm run typecheck && node --test $(find src -path '*__tests__*' -name '*.test.ts')
```
착수 전 기준선을 먼저 재라. 직전 = pytest 4673 passed(기존 실패 12·수집오류 7) / tsc 0 / node 260.

**실물 확인 (필수)**: 검증본 doc
`users/qdeLN9Ur1yMFb9duNT2ep3g4pmT2/analyses/c64afae69fd24366b4b5f375aa0a91fb`
는 **옛 영문 이름**을 들고 있다. 이것으로 레거시 폴백이 실제로 동작하는지
`buildExerciseSections` 를 직접 호출해 확인하고 결과를 SUMMARY 에 적어라 (Firestore 읽기만).

## ★ 하지 말 것

- 운동 이름·설명·kind·setsReps 를 다시 바꾸지 마라. 이번은 **식별자 도입**이다.
- `_EXERCISES_PER_DEFECT` / `_MAX_EXERCISES` / `MAX_ROWS` 무접촉.
- 붕괴 게이트·날짜·재생기 관련 파일 무접촉.
- 레거시 폴백을 **생략하지 마라.** "앞으로 만들어질 분석은 괜찮다"는 이유로 빼면
  오늘 이전 사용자가 전부 빈 화면을 본다.

## 검증의 한계

시뮬레이터에서 모달을 실제로 열어봐야 닫힌다. `tsc`·`pytest` 는 렌더를 못 본다.
★ 시뮬에서 "안 보인다"를 만나면 **코드보다 번들 시각을 먼저 재라**
(`stat -f "%Sm" "$(xcrun simctl get_app_container <UDID> com.sunity.aicoach)/main.jsbundle"`).
