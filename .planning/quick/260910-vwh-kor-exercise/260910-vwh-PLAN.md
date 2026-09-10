---
id: 260910-vwh
title: 보완운동 한글 이름 + 분석별 구성
date: 2026-09-10
status: planned
---

# 보완운동을 수강생 말로, 그리고 분석이 말하는 대로

## belle 지시 (2026-09-10, 원문)

- **"보완 운동말이야? 좀 한국사람들에게 익숙한 키워드? 단어로 바꾸는게 가능한가? 뭔가
  어려워보이네 직관적이지 않고"**
- **"어깨 끌어내리기는 무슨 말인지 잘 모르겠엉, 수축-이완도 마찬가지고 이런게 몇 개 있네"**
- **"예를 들면 팔굽혀펴기는 완전 좋지, 누구나 아는 용어잔항. 골반 앞쪽 늘리기 → 골반 교정
  스트레칭 뭐 이런? 느낌 오나..?"** → 동작 **설명**이 아니라 **들어본 적 있는 이름표**.
- **"전공 용어보단 더 쉬운 용어로 하면 내가 꼭 알려준 스트레칭을 안써도 돼"**
- **"스트레칭 뿐만 아니라 근력을 키우는 헬스도 있을거고 다양하게 구성하여 분석에 따라
  배전해주면 좋을거 같은데?"**
- ★ **"균형 잡히게 섞는거 물론 좋지. 근데 그게 규칙이 될 필요는 없어. 분석마다 다를거아냐.
  근력이 충분한데 뭐하러 헬스를 하겠어"**
- ★ **"말이 그렇다는거지 분석 보고에 따라 조절 되어야 한다는 말이야"**

## 이 지시가 정하는 선 (설계 원칙)

**분석이 아는 것으로만 배분한다.**

- 아는 것 = **어느 부위가 걸렸는가**. 이건 감점 record 가 직접 말한다 → **배분 근거로 쓴다.**
- 모르는 것 = **힘이 없어서인가 뻣뻣해서인가**. 지금 파이프라인에 그 신호가 없다
  → **배분 근거로 쓰지 않는다.** "근력 1 + 유연성 1" 같은 강제 혼합은 원인을 아는 척하는 것이고,
  belle 이 정확히 그것을 기각했다("근력이 충분한데 뭐하러 헬스를").
- 성격(근력/유연성/준비운동)은 **강제하지 않고 표시만** 한다. 표시는 거짓말이 아니다 —
  수강생과 강사가 보고 고를 수 있게 한다.

## 참고 자료

같은 디렉터리 `RESEARCH.md` — 29개 운동의 한국 통용명 조사 원문(근거 인용·유통도 포함).
**이름을 지어내지 말고 그 조사 결과를 쓰라.** 조사가 "대중 이름 없음"이라 한 것만 창작한다.

---

## Task 1 — 이름과 설명을 수강생 말로

**files**: `backend/data/corrective_exercises.json`, `app/src/data/corrective_exercises.json`
(byte 동기 — 게이트 `backend/tests/phase13/test_corrective_exercises_app_lockstep.py`)

**action**: 29개 `name` 을 아래 확정표대로 바꾼다. `purpose` 도 같이 손본다.

**belle 확정 4건**
| 지금 | 바꿀 것 | 근거 |
|---|---|---|
| Hip Flexor Stretch | **골반 앞 스트레칭** | "장요근"은 전공어라 기각, "골반 교정"은 비둘기 자세와 뜻 겹침 |
| PNF Stretch | **파트너 스트레칭** | 원본 setsReps 가 "파트너 수축/이완" — 뜻 보존 |
| Scapular Depression Drills | **매달려 어깨 내리기** | 대중 이름 부재. 조사가 확인. 폴에 매달린 채 하는 동작이라 이 말이 유일하게 읽힌다 |
| Bicep/Tricep Balance | **아래 Task 4 에서 교체** | 이건 운동이 아니라 원칙이다 |

**외래어 유지 (번역하면 오히려 낯설어짐 — 조사 결론)**
Squats→**스쿼트** · Lunges→**런지** · Deadlift→**데드리프트** · Planks→**플랭크** ·
Side Planks→**사이드 플랭크** · Russian Twists→**러시안 트위스트** · Farmer's Walk→**파머스 워크**

**나머지**
Push-ups→**팔굽혀펴기** · Calf Raises→**까치발 들기** · Dead Hang→**철봉 매달리기** ·
Hand Grippers→**악력기 운동** · Assisted Pull-ups→**밴드 턱걸이** · Neck Stretch→**목 스트레칭** ·
Supermans→**슈퍼맨 운동** · Pigeon Pose→**비둘기 자세** · Dynamic Leg Swings→**앞뒤로 다리 흔들기** ·
Arm Circles→**팔 돌리기** · Quad Stretch→**허벅지 앞 스트레칭** · Hamstring Stretch→**허벅지 뒤 스트레칭** ·
Lateral Leg Raise→**옆으로 다리 들기** · Hanging Leg Raise→**매달려 다리 들기** ·
Plank with Leg Lift→**한 다리 들고 플랭크** · Overhead Press→**어깨 위로 밀기** ·
Cross-Shoulder Stretch→**어깨 뒤 스트레칭** · High Kick→**다리 차올리기**

**purpose 도 같이 고친다.** 지금 "견갑 하강 안정화" / "어깨 상방 안정성 강화" / "미는 근력
밸런스로 어깨 안정화" 같은 것이 이름만큼 안 통한다. 규칙: **이름은 뭘 하는지, 설명은 왜 하는지 —
둘 다 그냥 읽어서 알게.** 전공어를 쓰지 말고, 원래 뜻을 잃지도 마라.

**★ 함정 (반드시 지킬 것)**
1. **`name` 은 dedup 키다** (`exercise_map.py` 가 name 문자열로 중복 제거). 29개가 **전부 서로 다른
   문자열**이어야 하고, 같은 운동이 여러 그룹에 있으면(스쿼트 3곳·런지 3곳 등) **같은 한글 이름**
   이어야 한다. 바꾼 뒤 **실제로 세어서 확인**하라.
2. 다리 계열 4개(`앞뒤로 다리 흔들기`/`다리 차올리기`/`옆으로 다리 들기`/`매달려 다리 들기`)와
   플랭크 계열 3개는 서로 비슷하다. **줄여 쓰지 마라.**
3. 앱 미러는 **byte 동기**다. 한쪽만 고치면 게이트가 깨진다.
4. `sourceRef` 는 **건드리지 마라** — 출처 이력이다.
5. JSON 실제 키는 `Bicep/Tricep Balance` (슬래시 포함).

**verify**: `cd backend && python3 -m pytest -q --continue-on-collection-errors`
(★ 이 플래그가 없으면 기존 수집오류 7건에서 중단되어 숫자를 못 본다)
+ `cd app && npm run typecheck` + `node --test $(find src -path '*__tests__*' -name '*.test.ts')`
착수 전 기준선을 먼저 재라. 직전 = pytest 4662 passed(기존 실패 12·수집오류 7) / tsc 0 / node 260.

**done**: 29개 이름 유니크 확인, 양쪽 JSON byte 동기, 테스트 무감소.

---

## Task 2 — 운동에 성격 표시 (강제 배분 아님)

**files**: `backend/data/corrective_exercises.json` + 앱 미러, 계약 3벌
(`models.py` / `app/src/types/analysis.ts` / `docs/contract.md`), `exercise_map.py`

**action**:
각 운동에 `kind` 를 붙인다. 값은 셋: `strength`(근력) / `flexibility`(유연성) / `warmup`(준비운동).

- 29개 분류는 **명백하다**(스쿼트=근력, 허벅지 뒤 스트레칭=유연성, 팔 돌리기=준비운동).
  애매한 것이 있으면 **판단하지 말고 SUMMARY 에 목록으로 올려라** — belle 이 정한다.
- 한글 표시명(`근력` / `유연성` / `준비운동`)은 **앱에 상수 하나**로 둔다. belle 이 문구를 바꿀 수 있게.
- `kind` 는 `recommendedExercises` 항목에 실려 앱까지 간다. 계약 3벌 동시 수정.
- ★ **이 값으로 선택을 바꾸지 마라.** Task 2 는 **데이터와 표시**까지다. 배분은 Task 3.

**verify**: 위와 동일 + 계약 3벌 일치.

---

## Task 3 — 분석이 말하는 대로 구성

**files**: `backend/shared/python/sunity_shared/analysis/exercise_map.py`

**action**:

(a) **부위로 배분한다.** 지금은 결함 그룹 순서대로 앞에서 자르기 때문에 한 부위가 목록을
독식한다(대표 분석 실측: 4개 중 4개가 전부 어깨). 감점이 걸린 **부위마다 대표를 하나씩** 먼저
채우고, 자리가 남으면 감점이 큰 부위부터 두 번째를 준다.
→ 어깨·팔꿈치·무릎이 걸렸으면 세 부위가 다 나온다. **이것이 "분석 보고에 따라 조절"의 실체다.**

(b) **준비운동은 맨 앞으로.** `kind == "warmup"` 인 항목은 순서상 앞. 이건 원인 판단이 아니라
다치지 말라는 상식이라 규칙으로 둔다.

(c) ★ **성격(strength/flexibility)으로 개수를 강제하지 마라.** belle 이 명시적으로 기각했다:
*"균형 잡히게 섞는거 물론 좋지. 근데 그게 규칙이 될 필요는 없어 … 근력이 충분한데 뭐하러
헬스를 하겠어."* 지금 분석은 원인(근력/유연성)을 모르므로 그 축으로 배분하면 아는 척이 된다.

(d) `_EXERCISES_PER_DEFECT = 1`, `_MAX_EXERCISES = 5` 는 **건드리지 마라.**

**verify**: `map_exercises` 를 아래 4개 실제 doc 입력에 직접 호출해 **전/후 표**를 내라
(Firestore 읽기만, 쓰기 0):
`c64afae69fd24366b4b5f375aa0a91fb`(pdshape 감점6) · `890e3b8b…`(climb 감점1) ·
`03a5b62d…`(kip-up 감점1) · `26a6c7e1…`(kip-up 감점3)
**요구: 대표 doc 에서 어깨 독식이 깨지고 다른 부위가 들어와야 한다.** 안 되면 그대로 보고하라.

---

## Task 4 — 운동이 아닌 항목 교체

**files**: `backend/data/corrective_exercises.json` + 앱 미러

**action**:
`Bicep/Tricep Balance` (painAreas.elbow) 는 setsReps 가 "수직+수평 당기기 균형" 으로,
**동작이 아니라 루틴 구성 원칙**이다. 수강생이 이걸 보고 할 수 있는 게 없다.

→ **실제로 할 수 있는 운동**으로 바꾼다. `RESEARCH.md` 와 `backend/data/corrective_exercises.json`
안에 이미 있는 항목 중 팔꿈치 부하에 맞는 것을 고르되, **근거 없이 새 운동을 지어내지 마라.**
고를 근거가 부족하면 **교체하지 말고 SUMMARY 에 "belle 판정 필요"로 올려라.**

`avoid` 문구("엘보 그립 안쪽 과하중 경계")는 **유지**한다 — 그건 유효한 안전 안내다.

---

## ★ 하지 말 것

- `_EXERCISES_PER_DEFECT` / `_MAX_EXERCISES` / `MAX_ROWS = 3` 무접촉.
- 붕괴 게이트(`limb_collapse.py`)와 그 배선 무접촉.
- `sourceRef` 무접촉.
- 운동 **내용**(setsReps 의 실제 횟수·시간)을 바꾸지 마라. 이름·설명·분류만이다.
- 성격으로 개수를 강제하는 코드를 쓰지 마라 (Task 3-c).

## 검증의 한계

- 화면 확인은 시뮬레이터에서 해야 한다. `tsc`·`pytest` 는 렌더를 못 본다.
- ★ **시뮬에서 "안 보인다"를 만나면 코드보다 번들 시각을 먼저 재라** — 오늘 그것으로 한 번 헛짚었다
  (`stat -f "%Sm" "$(xcrun simctl get_app_container <UDID> com.sunity.aicoach)/main.jsbundle"`).
- 백엔드 변경은 `sam deploy` 전까지 실제 분석에 반영되지 않는다. belle 기존 doc 도 안 바뀐다.
