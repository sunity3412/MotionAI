---
id: 260910-woq
title: 운동 식별자를 표시 이름과 분리
date: 2026-09-10
status: done
---

# 이름을 바꿔도 과거 분석이 안 끊긴다

이름이 표시 문자열이자 조인 키를 겸하던 것을 갈랐다. 조인은 `id`, 표시는 `name`.
09-10 개명(vwh) 이전 doc 은 저장된 옛 영문명으로 폴백해서 받는다.

## 커밋

| 커밋 | Task | 바뀐 파일 |
|---|---|---|
| `58feb7f0` | 1 — 라이브러리에 id 부여 | `backend/data/corrective_exercises.json`, `app/src/data/corrective_exercises.json` (각 43행) |
| `25c3a6f5` | 2 — 조인을 id 로 | `app/src/lib/exerciseSections.ts`, `app/src/data/legacyExerciseNames.ts` (신규), `app/src/data/correctiveExercises.ts`, `app/src/components/RecommendedExerciseModal.tsx`, `app/src/components/result/ResultExerciseTab.tsx`, `app/src/lib/resultSummary.ts`, `app/src/types/analysis.ts`, `backend/shared/python/sunity_shared/analysis/exercise_map.py`, `backend/shared/python/sunity_shared/models.py`, `docs/contract.md`, 테스트 2벌 |
| `c6dc3c43` | 3 — 재발 방지 테스트 | `app/src/lib/__tests__/exerciseSections.test.ts`, `app/src/data/__tests__/legacyExerciseNames.test.ts` (신규), `backend/tests/phase13/test_exercise_id_contract.py` (신규) |

## id 유니크성 — 실제로 센 숫자

| 항목 | 수 |
|---|---|
| 라이브러리 운동 행 (defects 30 + painAreas 13) | **43** |
| 유니크 id | **28** (PLAN 예상과 일치) |
| 같은 이름인데 id 가 다른 경우 | **0** |
| 같은 id 인데 이름이 다른 경우 | **0** |
| id 삽입 외 변경된 문자 | **0** (43행 전부 raw 치환 후 역검증) |
| backend / app JSON byte 동일 | `cmp` 통과 |

- 28은 종전 29에서 하나 준 것. vwh 가 팔꿈치 통증 항목을 `Bicep/Tricep Balance` →
  `어깨 위로 밀기`(= 기존 `overhead_press`)로 교체해 합쳐졌다.
- id 는 **옛 영문명**에서 유도했다 (`git show 9ceca050~1:backend/data/corrective_exercises.json`).
  예: `Farmer's Walk` → `farmers_walk`, `Scapular Depression Drills` → `scapular_depression_drills`.
  한글 이름 파생 금지는 테스트로 박제(ASCII 스네이크 케이스 정규식).
- `sourceRef` / `setsReps` / `purpose` / `kind` / `avoid` / `triggers` 무접촉.
  `schemaVersion` 은 1.0.0 유지 — `id` 는 가산 필드이고 분기하는 소비처가 없다.
  값을 박제한 테스트(`test_corrective_exercises_fixture.py:33`)가 있어 굳이 흔들지 않았다.

## 착수 전 / 후 검증 숫자

| 게이트 | 착수 전 | 착수 후 |
|---|---|---|
| `pytest -q --continue-on-collection-errors` | 4673 passed, 12 failed, 27 skipped, 7 errors | **4680 passed** (+7), 12 failed, 27 skipped, 7 errors |
| 실패/수집오류 **집합** | — | `diff` 결과 **동일** (새로 깬 것 0, 고친 것 0) |
| `tsc --noEmit` | 0 | **0** |
| `node --test src/**/__tests__/*.test.ts` | 260 passed | **276 passed** (+16) |

+16 내역: `exerciseSections` +7, `legacyExerciseNames` +8(신규 파일), `resultSummary` +1.
+7(pytest) 내역: `test_exercise_id_contract.py` 신규 7건.

## ★ 레거시 폴백 실측 — 검증본 doc 에서 실제로 돌렸다

`users/qdeLN9Ur1yMFb9duNT2ep3g4pmT2/analyses/c64afae69fd24366b4b5f375aa0a91fb`
(Firestore 읽기만. 앱의 순수 모듈 `buildExerciseSections` 를 그대로 호출).

**doc 이 실제로 들고 있던 것**

```
recommendedExercises 5건, id 보유 0 / 5 — 전부 옛 영문명
  Push-ups · Overhead Press · Scapular Depression Drills · Arm Circles · Cross-Shoulder Stretch
bodyProfile.painAreas: []
```

**결과**

| 경로 | 섹션 | 운동 행 |
|---|---|---|
| 지금 코드 (폴백 있음) | **1** — `shoulder_unstable` / 어깨 안정화 | **5** (팔굽혀펴기, 어깨 위로 밀기, 매달려 어깨 내리기, 팔 돌리기, 어깨 뒤 스트레칭) |
| 대조군: 폴백 끄고 id 만 | **0** | **0** |

PLAN 이 적은 "이름 교체 전에는 '어깨 안정화' 5줄을 정상 표시했다"와 같은 화면이
돌아왔다. 그리고 **폴백이 없으면 0/0**, 즉 빈 모달이라는 것이 같은 doc 위에서
실측으로 확인됐다 — 폴백이 이 작업의 핵심이라는 PLAN 의 판단이 맞다.

## 재발 방지 테스트 5축 — 무엇을 잡는가 (뮤테이션 확인 완료)

각 축이 실제로 결함을 잡는지 코드/데이터를 되돌려 확인했다. **전부 잡혔다.**

| 뮤턴트 (되돌린 것) | 깨진 테스트 |
|---|---|
| M1 조인을 이름으로 되돌림 (`ids.has` 제거) | `exerciseSections` 19건 중 **12건 fail** |
| M2 레거시 폴백 제거 (id 만 봄) | 축2, 축2-b |
| M3 앱 dedup 을 이름 기준으로 | 축1-c |
| M4 신 doc 에도 이름 폴백 개방 | 축3-b |
| M6 데드리프트에 `squats` id 부여 (축4 위반) | backend 2건 + app 1건 |
| M7 둔근 그룹 스쿼트만 다른 id (축5 위반) | backend 2건 + app 2건 |
| M8 옛 이름 표에서 `push_ups` 1행 제거 | 옛 이름 커버리지 (backend 무관, app 1건) |
| M9 id 를 한글 표시명(`팔굽혀펴기`)으로 | id 형식 게이트 |
| M10 백엔드 dedup 을 이름 기준으로 | `test_dedup_is_by_id_not_name` |
| M11 산출에서 `id` 제거 | `test_id_reaches_map_exercises_output`, `test_dedup_is_by_id_not_name`, `test_output_keys_lockstep_with_contract` |

**축별로 무엇을 붙잡고 있는가**

1. **축1 — id 가 그대로면 이름이 바뀌어도 섹션 유지.** 이 결함의 직접 재현이다.
   라이브러리 표시명 전부에 접두사를 붙여 "다음 개명"을 흉내내고, 저장된 이름이
   라이브러리 어디에도 없다는 **전제까지 assert** 한다 (전제가 깨지면 축이 사문이 되므로).
   파생 축1-b/1-c 는 중복 제거도 id 기준임을 잡는다 — 1-c 는 그룹마다 이름이 어긋난
   라이브러리를 만들어, 이름 dedup 이면 같은 운동이 두 번 그려지는 것을 잡는다.
2. **축2 — 옛 doc 이 폴백으로 매칭.** 실물 검증본 doc 과 같은 모양(id 없음, 옛
   영문명)을 입력으로 쓴다. 대조군으로 `legacyName` 을 뺀 라이브러리에서는 빈
   목록임을 같이 박제했다 — 이 대조군이 없으면 폴백을 지워도 테스트가 안 깨진다.
   축2-b 는 개명(vwh)과 id 도입(woq) **사이**에 만들어진 doc(id 도 없고 옛
   영문명도 아님)을 지금 이름으로 받는 경로.
3. **축3 — 아무것도 안 맞으면 빈 목록.** 조용한 오매칭 금지. 라이브러리에서 사라진
   옛 운동(`Bicep/Tricep Balance`)도 아무것도 못 끌어온다는 것을 포함.
   축3-b 는 반대 방향 — **id 를 가진 doc 에는 이름 폴백을 열지 않는다.** 개명으로
   서로 다른 두 운동이 한 이름을 나눠 갖는 날 B 그룹이 조용히 딸려 나오는 것을 막는다.
4. **축4 — id 유니크성.** 같은 id 인데 이름이 다르면 = 서로 다른 운동이 id 를 공유.
   유니크 id 수 28도 박제 — 숫자가 바뀌면 옛 이름 표도 같이 봐야 한다는 신호다.
5. **축5 — 같은 운동은 어느 그룹에 있든 같은 id.** 여러 그룹에 실린 운동이 실제로
   있다는 것(스쿼트 3그룹, 옆으로 다리 들기 2그룹)까지 assert 해 축이 사문이 되지 않게 했다.

**추가로 막는 것**

- `id` 형식(ASCII 스네이크). 한글 표시명 파생이 바로 다음 개명 때 이 결함을
  재발시키는 경로라 형식 자체를 게이트로 세웠다.
- 옛 이름 표 ↔ 라이브러리 id **양방향** 커버 (누락도 고아도 fail) + 옛 이름 유니크성.
- 무행동 회귀: 라이브러리가 정합인 동안 id dedup 과 name dedup 산출이 같다.

## PLAN 과 다르게 한 것

1. **"4개 doc 실측" → 어휘 전수 576건 대조.**
   PLAN 은 백엔드 dedup 변경이 무행동임을 4개 doc 으로 확인하라고 했다. doc 에는
   `map_exercises` 의 **산출**만 있고 입력(감점 부위·findings)이 그대로 남아 있지
   않아 표본 재현이 불안정하다. 대신 감점 부위 어휘 8값의 1~2개 조합 64가지 x
   통증부위 9가지 = **576건 전수**로 id dedup ↔ name dedup 산출을 대조했다
   (`test_id_dedup_matches_name_dedup_on_the_real_library`). 표본보다 넓고, 표본이
   안 건드리는 조합까지 덮는다.

2. **`legacyName` 을 라이브러리 JSON 이 아니라 별도 동결 모듈에 뒀다.**
   PLAN 이 "다른 방법이 더 깨끗하면 그것을 쓰되 이유를 적어라"고 열어 둔 자리.
   `app/src/data/legacyExerciseNames.ts` 로 뺀 이유 셋 (파일 머리주석에도 있다):
   (a) JSON 은 살아 있는 표시 데이터고 이 표는 동결 이력이다. 한 파일에 두면 다음
   개명 때 "옛 이름도 같이 고쳐야지" 하고 손대게 되고 그 순간 폴백이 죽는다 —
   이 작업이 막으려는 결함의 재발 경로다. (b) 백엔드는 이 표가 필요 없다(신 doc 은
   항상 id 를 싣는다). (c) JSON 은 같은 운동이 여러 그룹에 중복 등재돼 있어
   legacyName 도 43벌이 되지만, 여기는 id 당 1행 28개라 자체 모순이 불가능하다.
   섹션을 만들 때(`correctiveExercises.ts`) 붙여 보내므로 순수 모듈
   `exerciseSections.ts` 는 여전히 JSON 을 import 하지 않는다.

3. **PLAN 파일 목록에 없던 `resultSummary.ts` / `ResultExerciseTab.tsx` 도 고쳤다.**
   결과 화면의 운동 배지("손목 보완")가 **같은 결함**이었다 —
   `exerciseBadgeLabel(ex.name, ...)` 로 이름 조인을 하고 있어, 개명 이후 옛 doc 의
   배지가 통째로 사라진다. 빈 모달만큼 눈에 띄지 않지만 원인이 하나라 같이 닫았다.
   되짚기는 id 우선 + 이름 폴백, 옛 영문명 → id 변환은 호출측이 `resolveExerciseId` 로.
   PLAN 의 "하지 말 것"(이름·내용·상수 재변경)에는 저촉되지 않는다 — 식별자 도입이다.

`_EXERCISES_PER_DEFECT` / `_MAX_EXERCISES` / `MAX_ROWS` 무접촉.
붕괴 게이트·날짜·재생기 파일 무접촉. 운동 이름·설명·kind·setsReps 무접촉.

## 검증의 한계 (PLAN §검증의 한계 승계 — 닫히지 않았다)

- **시뮬레이터에서 모달을 실제로 열어봐야 닫힌다.** `tsc`·`pytest`·`node --test` 는
  렌더를 못 본다. 이번에 한 실물 확인은 **데이터 경로**(검증본 doc → 섹션 5행)까지고,
  화면에 그려지는 것은 확인하지 않았다.
- 시뮬에서 "안 보인다"를 만나면 **코드보다 번들 시각을 먼저 재라**:
  `stat -f "%Sm" "$(xcrun simctl get_app_container <UDID> com.sunity.aicoach)/main.jsbundle"`
- 배포(OTA)도 하지 않았다. 다음 사람이 이어서 해야 할 것 = 시뮬 확인 → OTA.
- `id` 를 싣는 **신 doc 은 아직 하나도 없다.** Pod 이 종료돼 있어 새 분석을 못 돌렸고,
  현재 확인된 것은 전부 폴백 경로다. 신 doc 경로는 단위 테스트로만 덮여 있다.

## 자평

- 폴백은 실물 doc 위에서 대조군까지 두고 쟀다 (있음 5행 / 없음 0행). 여기는 단단하다.
- 5축은 전부 뮤테이션으로 "실제로 잡는다"를 확인했다. 축이 사문이 되는 것을 막는
  전제 assert 도 넣었다.
- 안 한 것: 시뮬 렌더 확인, 신 doc(id 보유) 실물 확인. 둘 다 위에 남겼다.
