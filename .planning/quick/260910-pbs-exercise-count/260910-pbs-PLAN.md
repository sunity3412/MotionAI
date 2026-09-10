---
id: 260910-pbs
title: 보완운동을 분석마다 다르게
date: 2026-09-10
status: planned
---

# 보완운동 — 분석이 실제로 필요로 하는 것만, 그만큼만

## belle 지시

**2026-09-10**
> "보완운동이 너무 과하게 많아 동작별 최대 6개 정도로만 줄이고, 1개 필요하면 진짜 1개만,
>  3개 필요하면 3개, 진짜로 분석별로 나타낼 수 있게... 이거 저번에 말했는데 구체화해야함."

**같은 날 확인**
> "분석마다 다른 개수 다른 종류가 될 수도 있지 (같은 종류가 될 수도 있고!) 동작마다 다른거 맞아!"

**2026-09-03 (같은 지시, 미구현)** — `.planning/research/pdshape-report-trim-2026-09-03.md:36`
> "뭐가 이렇게 많아. 뭘 다 나열해놨어. 동작별로 어울리는 거 부위별로 한 두개씩만 대표로
>  나오도록 축소하자 그게 더 신뢰도를 줄 듯"

**그 이전 (D-13, 미구현)** — `.planning/phases/32-result-readability-3-omni/32-CONTEXT.md:37`
> "전면엔 top-1 결함 연결 운동 1개 + 이유 1줄 필수, '다른 운동 보기' 최대 3개. 5개 세로 나열 폐지."

## 실측된 현재 상태 (2026-09-10)

**개수가 분석과 무관하다. 거의 항상 상한 5로 채워진다.**

| doc | 동작 | 종합 | 감점 | 보완운동 |
|---|---|---|---|---|
| c64afae6 (대표) | pdshape | 60 | 6 | **5** |
| 890e3b8b | climb | 92 | **1** | **5** |
| 03a5b62d | kip-up | 88 | **1** | **5** |
| 26a6c7e1 | kip-up | 47 | 3 | **5** |

원인 = `exercise_map.py:198-199` 의 **(4) 백필**. 결함 키 하나만 매칭돼도 그 그룹의 fixture 5개가
cap 을 그대로 채운다. 대표 doc 실측: 감점 6건인데 나온 운동 5개가 **전부 `shoulder_unstable`
한 그룹**(Push-ups / Overhead Press / Scapular Depression Drills / Arm Circles / Cross-Shoulder
Stretch) — 팔꿈치·무릎·엉덩이 감점은 운동에 **반영 자체가 안 된다.**

**'전체 보완 운동 보기' 모달은 분석을 아예 안 받는다.**
`RecommendedExerciseModal.tsx` props = `{visible, onClose}` 뿐 → 어느 분석에서 열어도 같은
**43행**(이름 기준 유니크 29, 즉 14행이 중복). belle 09-03 "뭘 다 나열해놨어"가 이 화면이다.
`correctiveExercises.ts:47` 주석은 "name 중복 제거"라 적혀 있으나 코드에 그 제거가 없다.

현재 상한 3곳: 생성 `exercise_map.py:68 _MAX_EXERCISES = 5` · 저장 거부선
`models.py:479 MAX_RECOMMENDED_EXERCISES = 5` · 표시 `ResultExerciseTab.tsx:31 MAX_ROWS = 3`.
`_MIN_EXERCISES = 3` (`exercise_map.py:69`) 은 **참조 0건인 죽은 상수**.

---

## Task 1 — 백필 제거 + 결함당 대표 1개 + 상한 6

**files**: `backend/shared/python/sunity_shared/analysis/exercise_map.py`,
`backend/shared/python/sunity_shared/models.py`, 해당 테스트

**action**:

(a) **(4) 백필을 제거한다** (`exercise_map.py:197-199`). 이것이 "고정 개수로 채우기"의 정체다.

(b) **결함 하나당 대표 1개.** `_FAULT_LEAD_PER_DEFECT` 를 **2 → 1**.
belle 09-10 "1개 필요하면 진짜 1개만" 의 문자 그대로다.
★ belle 09-03 은 "한 두개씩"이라 했으므로 **1 이냐 2 냐는 belle 이 화면 보고 정할 여지**가 있다.
그래서 이 값은 **상수 하나로 유지**하고, SUMMARY 에 "1→2 는 상수 한 줄" 이라고 적어라.

(c) **(3) findings 유래 defect 도 같은 상한을 받는다.** 지금 `:196` 은 `_defect_exercises(defect_key)`
를 **슬라이스 없이** 통째로 넣어 5개가 들어간다. (b)와 같은 상한을 적용하라.

(d) **상한 5 → 6** — `_MAX_EXERCISES`, `models.py:479 MAX_RECOMMENDED_EXERCISES`,
그리고 `firestore_admin.py:823-855 _validate_recommended_exercises` 의 거부선까지 **셋을 같이**.
belle "최대 6개".

(e) **죽은 상수 `_MIN_EXERCISES` 를 지운다.** 참조 0건이고, 하한이 있다는 오해를 만든다.

**verify**: `cd backend && python3 -m pytest -q` — 착수 전 기준선을 먼저 재서 적을 것.
그리고 **실측 검증**: 위 표의 4개 doc 을 Firebase MCP 로 읽어 그 입력(faultKeypointSets /
findings / painAreas)으로 `map_exercises` 를 직접 호출해 **전/후 개수를 표로** 내라.
요구: 감점 1건짜리 doc(890e3b8b · 03a5b62d)에서 **5개 → 1~2개**로 줄어야 한다.
안 줄면 백필 말고 다른 경로가 채우고 있는 것이므로 찾아서 보고하라.

**done**: 백필 제거, 상한 3곳 6으로 일치, 실측 표에서 개수가 분석마다 달라짐, 테스트 무감소.

---

## Task 2 — 감점 부위가 운동에 반영되게

**files**: `backend/shared/python/sunity_shared/analysis/exercise_map.py`,
`backend/functions/pipeline/app.py` (호출부 `:8478-8483`)

**action**:
belle "다른 **종류**가 될 수도 있지" 를 만족시키는 축이다. 지금은 결함 종류가 vision faultKey 와
findings 에서만 오고, **실제 감점 record 의 관절은 운동 선정에 안 들어간다.** 그래서 대표 doc 이
팔꿈치·무릎 감점을 갖고도 어깨 운동만 받았다.

- 감점 record 의 관절(`criterion` 의 `angle_vs_reference__{jk}` 에서 뽑은 `jk`)을
  **부위 어휘로 접고**, 그 어휘를 defect 키로 매핑해 후보에 추가하라.
  ★ 새 매핑표를 **짓지 마라.** 이미 두 개가 있다 —
  `vision_veto.py:168` 계열(팔꿈치/elbow/팔/arm → "arm") 과
  `exercise_map.py:57-66 _KEYPOINT_SET_TO_DEFECTS`(부위 8값 → defect).
  이 둘을 이어 쓰라. 이을 수 없으면 **이을 수 없는 이유를 적고 멈춰라** — 새 어휘를 만들지 말 것.
- 우선순위: 감점이 **큰** 부위가 앞에 온다 (points 기준 내림차순). belle "필요한 만큼" 의
  자연스러운 순서다.
- ★ **오늘 들어간 붕괴 게이트와의 결합**: 판정 불가로 빠진 감점은 record 자체가 없으므로
  그 부위 운동도 자동으로 안 나온다. **이게 맞는 동작이다** — 근거 없는 감점에서 나온 운동은
  근거가 없다. 별도 처리 불필요하지만, SUMMARY 에 이 상호작용을 확인했다고 적어라.

**verify**: Task 1 과 같은 4개 doc 실측 표를 다시 내라. 요구:
대표 doc(c64afae6)에서 **어깨 말고 팔꿈치·무릎 계열 운동이 최소 1개 들어와야** 한다.
안 들어오면 매핑이 안 이어진 것이니 그대로 보고하라.

**done**: 감점 부위가 운동 종류에 반영됨이 실측 표로 확인, 테스트 무감소.

---

## Task 3 — '전체 보완 운동 보기' 를 이 분석 것만

**files**: `app/src/components/RecommendedExerciseModal.tsx`,
`app/src/app/analysis/result.tsx` (호출부), 필요 시 `app/src/data/correctiveExercises.ts`

**action**:
belle 09-03 지시 그대로 — 모달이 **이 분석의 감점 부위**만 보여준다.

- 모달이 분석 결과를 받도록 props 를 넓힌다 (지금 `{visible, onClose}` 뿐).
- 그 분석의 감점 부위(+ 사용자 통증 부위)에 해당하는 섹션만 그린다.
- **이름 중복을 실제로 제거한다** — `correctiveExercises.ts:47` 주석이 이미 그렇게 적혀 있는데
  구현이 없다. 주석과 코드를 일치시켜라.
- 감점 부위가 하나도 없으면(만점 등) 모달을 **열 수 있게 두되 빈 상태 문구**를 그린다.
  화살표만 있고 아무것도 없는 화면은 만들지 마라.

**verify**: `cd app && npm run typecheck` + `node --test $(find src -path '*__tests__*' -name '*.test.ts')`
기준선 = typecheck 0 / 테스트 241 pass (다른 세션 작업으로 늘어 있을 수 있으니 착수 전에 재라).

**done**: 모달 행 수가 분석마다 달라지고 중복이 사라짐, 타입체크 0, 테스트 무감소.

---

## ★ 하지 말 것

- `backend/data/corrective_exercises.json` 의 **운동 내용을 편집하지 마라.** 출처가 NotebookLM
  폴스포츠 노트북이고 사람이 옮겨 적은 것이다. 앱 미러와 byte 동기 게이트
  (`backend/tests/phase13/test_corrective_exercises_app_lockstep.py`)가 있으니 건드리면 깨진다.
- 운동을 **LLM 으로 생성하지 마라.** 지금은 순수 규칙 매핑이고, 그게 이 목록의 신뢰 근거다.
- `ResultExerciseTab.tsx:31 MAX_ROWS = 3` (시안 4 근거, belle 09-09)을 건드리지 마라 —
  전면 카드 수는 시안이 정한 것이고 이번 지시 범위가 아니다.
- `exerciseId`(phrasebook 계통)를 건드리지 마라. 보완운동 목록과 코드상 연결이 없다.
- 오늘 다른 세션이 만진 파일 무접촉: `RenderedComparePlayer.tsx`, `sourceSwapSeek.ts`,
  `analysisDate.ts`, `limb_collapse.py` 및 그 배선.

## 검증의 한계

- `map_exercises` 를 직접 호출한 실측은 **저장된 입력을 다시 넣어 보는 것**이지 실제 파이프라인
  실행이 아니다. 실제 분석에서 같은 결과가 나오는지는 Pod 실행으로만 확인된다.
- belle 기존 doc 은 안 바뀐다. 화면에서 보려면 재분석이 필요하다.
- 결함당 1개냐 2개냐는 **belle 이 화면 보고 정할 것**이다. 숫자로 미리 못 정한다.
