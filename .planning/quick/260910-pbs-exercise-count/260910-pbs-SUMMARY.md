---
id: 260910-pbs
title: 보완운동을 분석마다 다르게
date: 2026-09-10
status: done
---

# 보완운동 — 개수는 분석이 정하고, 종류는 감점이 정한다

## 한 줄

보완운동 개수를 늘 5로 붙여놓던 백필을 없애고(결함당 대표 1개, 상한 6), 실제 감점
부위를 운동 선정에 넣었으며, '더 보기' 모달이 이 분석의 그룹만 그리게 했다.

## 커밋

| 커밋 | Task | 바뀐 파일 |
|---|---|---|
| `8c97aac` | 1 — 백필 제거 · 결함당 1개 · 상한 6 | `backend/shared/python/sunity_shared/analysis/exercise_map.py` · `models.py` · `firestore_admin.py` · `backend/functions/pipeline/app.py`(주석) · `backend/tests/phase13/test_map_exercises.py` · `test_recommended_exercises_lockstep.py` · `docs/contract.md` · `app/src/types/analysis.ts`(주석) · `app/src/lib/userAnalyses.ts`(주석) |
| `e9eae6b` | 2 — 감점 부위를 운동 종류에 | `backend/shared/python/sunity_shared/analysis/vision_veto.py` · `exercise_map.py` · `backend/functions/pipeline/app.py` · `backend/tests/phase13/test_deduction_parts_to_exercises.py`(신규) |
| `d103679` | 3 — 모달을 이 분석 것만 | `app/src/lib/exerciseSections.ts`(신규) · `app/src/lib/__tests__/exerciseSections.test.ts`(신규) · `app/src/components/RecommendedExerciseModal.tsx` · `app/src/app/analysis/result.tsx` · `app/src/data/correctiveExercises.ts` · `app/src/components/result/ResultExerciseTab.tsx`(주석만) |

## 검증 숫자 (착수 전 → 후)

| 게이트 | 착수 전 | 최종 |
|---|---|---|
| `backend` pytest | 4643 passed · 12 failed · 27 skipped · 수집오류 7 | **4662 passed** · 12 failed · 27 skipped · 수집오류 7 |
| `app` typecheck | 0 | **0** |
| `app` node --test | 241 pass | **253 pass** · 0 fail |

기존 실패 12건과 수집오류 7건(`imageio_ffmpeg` 부재)은 착수 전과 **목록까지 동일**하다
— 내가 만든 것이 아니고 하나도 늘지 않았다. 신규 테스트 31건(백엔드 19 · 앱 12).

## ★ 4개 doc 실측표

Firebase 에서 doc 4건을 **읽기만** 해서(쓰기 0) 저장된 입력(faultKeypointSets /
findings / painAreas / deductionBreakdown.records)을 `map_exercises` 에 다시 넣었다.

**재현 충실도 확인:** 착수 전 코드로 재투입했을 때 4건 **전부 저장된
`recommendedExercises` 와 완전히 동일**하게 나왔다(`reproducesStored: true` ×4).
입력 재구성이 실제 산출 경로와 일치한다는 뜻이라, 아래 전/후 비교는 같은 저울 위의
비교다.

### 개수

| doc | 동작 | 종합 | 감점 | 전 | Task1 후 | **최종** |
|---|---|---|---|---|---|---|
| c64afae6 (대표) | pdshape | 60 | 6 | 5 | 1 | **4** |
| 890e3b8b | climb | 92 | **1** | 5 | 2 | **3** |
| 03a5b62d | kip-up | 88 | **1** | 5 | 4 | **4** |
| 26a6c7e1 | kip-up | 47 | 3 | 5 | 5 | **5** |

**전부 5로 고정 → 3·4·4·5 로 갈린다.** 개수가 분석을 따라간다.

### 종류

| doc | 전 (운동 5개) | 최종 |
|---|---|---|
| c64afae6 | Push-ups · Overhead Press · Scapular Depression Drills · Arm Circles · Cross-Shoulder Stretch — **전부 `shoulder_unstable` 한 그룹** | Push-ups · **Hamstring Stretch** · **Squats** · **Lateral Leg Raise** |
| 890e3b8b | Farmer's Walk · Hand Grippers · Assisted Pull-ups · Dead Hang · Deadlift — **전부 `grip_weak` 한 그룹** | **Hamstring Stretch** · **Squats** · Farmer's Walk |
| 03a5b62d | Hamstring Stretch · Hip Flexor Stretch · Squats · Lunges · Farmer's Walk | Hamstring Stretch · Squats · Farmer's Walk · Hand Grippers |
| 26a6c7e1 | Farmer's Walk · Hand Grippers · Push-ups · Overhead Press · Hamstring Stretch | Push-ups · Hamstring Stretch · Squats · Farmer's Walk · Hand Grippers |

26a6c7e1 은 개수가 5로 같지만 **종류가 바뀌었다** — 종전엔 통증부위(손목) 운동이 앞
두 자리를 먹었고, 지금은 실제 감점(어깨 −20.0/−13.2, 스플릿 −20.0)이 앞에 온다.

### 감점 1건짜리가 1~2개까지는 안 내려갔다 (계획 요구 대비 미달, 원인 규명)

플랜 요구는 `890e3b8b`·`03a5b62d` 가 **1~2개**였는데 실제는 **3개·4개**다. 백필이 아닌
다른 경로가 채우고 있다 — 셋이고, 전부 실측으로 분해했다:

1. **부위 1개가 defect 2개로 펼쳐진다.** `_KEYPOINT_SET_TO_DEFECTS["leg"] =
   ("hip_hamstring_tight", "legs_not_extended")` — 무릎 감점 1건이 "결함 2개"로 세어져
   운동 2개가 된다. `["hip"]` 도 2-튜플이다.
   → 부위당 1개로 줄이려면 `exercise_map._defect_keys_from_keypoint_sets` 의 조회
   결과에 `[:1]` 한 줄.
2. **painArea 운동은 슬라이스가 없다.** `03a5b62d` 는 손목 통증 신고가 있어
   `wrist` 그룹 2개(Farmer's Walk, Hand Grippers)가 통째로 들어온다.
   → `map_exercises` 의 `ordered.extend(area.get("exercises", []))` 에 `[:1]` 한 줄.
   (건드리지 않았다 — 통증부위 안전 운동을 자르는 건 belle 판단 영역이다.)
3. **findings 경로가 감점과 무관하게 defect 를 하나 더 낸다.** `890e3b8b` 은 감점이
   오른무릎 −7.8 하나뿐인데 `late_contact` finding 이 `grip_weak` 를 트리거해
   Farmer's Walk 가 붙는다.

세 경로 다 "고정 개수 채우기"는 아니고 **각자 근거가 있는** 유입이라, 임의로 자르지
않고 그대로 두고 보고한다. 화면을 보고 더 줄일지는 belle 이 정할 일이다.

## 대표 doc 에서 팔꿈치·무릎 계열이 들어왔는가

**무릎 = 들어왔다. 팔꿈치 = 어깨 운동으로 접힌다 (어휘의 한계, 그대로 보고).**

`c64afae6` 감점 6건이 부위로 접힌 결과 (감점 합 내림차순):

| 부위 | 감점 record | \|합\| | → defect | → 운동 |
|---|---|---|---|---|
| `arm` | left_elbow −15.1 · right_elbow −10.7 | 25.8 | `shoulder_unstable` | Push-ups |
| `leg` | left_knee −7.8 · right_knee −6.7 | 14.5 | `hip_hamstring_tight` · `legs_not_extended` | Hamstring Stretch · Squats |
| `shoulder` | right_shoulder −6.7 | 6.7 | `shoulder_unstable` (중복) | — |
| `hip` | left_hip −4.0 | 4.0 | `glute_hip_unstable` | Lateral Leg Raise |

- **무릎:** Hamstring Stretch · Squats 로 들어왔다. 엉덩이도 Lateral Leg Raise 로
  들어왔다. 종전엔 둘 다 0이었다.
- **팔꿈치:** 기존 어휘가 `팔꿈치/elbow/팔/arm → "arm"` 이고, `_KEYPOINT_SET_TO_DEFECTS`
  가 `"arm" → ("shoulder_unstable",)` 이다. 즉 **팔꿈치는 어깨 운동으로 접힌다** —
  이 doc 에서 가장 큰 감점(−15.1/−10.7)이 Push-ups 로 나온 이유다. 팔꿈치 전용 결함
  그룹은 `corrective_exercises.json` 의 `defects` 에 없다(있는 것은 통증 경로 전용
  `painAreas.elbow = Bicep/Tricep Balance` 뿐). 플랜 지시대로 **새 어휘를 만들지
  않았고**, 이을 수 없는 지점을 그대로 남겨 보고한다. 팔꿈치 결함 그룹을 새로 만드는
  것은 fixture(NotebookLM 출처, 앱 미러와 byte 동기) 편집이라 이번 범위 밖이다.

## 붕괴 게이트와의 상호작용

**확인했다 — 별도 처리 불필요하고, 그 사실을 테스트로 박제했다.**

오늘 들어간 붕괴 게이트(quick-260910-ovo)로 판정 불가 처리된 관절은 감점 record 자체가
만들어지지 않는다. `_deduction_keypoint_sets` 는 record 만 읽으므로, record 가 없으면
그 부위도 목록에 없고 따라서 그 부위 운동도 안 나온다. 근거 없는 감점에서 나온 운동은
근거가 없다는 원칙이 자동으로 지켜진다.
검증: `test_collapse_gate_removes_the_part_because_record_is_gone` — 무릎 record 가
있을 때 Hamstring Stretch 가 나오고, 빠지면 사라진다.
코드 접촉 0: `limb_collapse.py` 와 그 배선(`pipeline/app.py` 붕괴 게이트 구간, ~8313)은
손대지 않았다. 이번 `app.py` 변경 hunk 는 7468(신규 헬퍼) · 8601(주석) · 8637(호출부)
셋뿐이다.

## 결함당 1개 → 2개로 바꾸려면

**한 줄이다:**

```
backend/shared/python/sunity_shared/analysis/exercise_map.py
    _EXERCISES_PER_DEFECT = 1     ←  이 값을 2 로
```

- 구 이름 `_FAULT_LEAD_PER_DEFECT` 에서 바꿨다. 백필이 사라져 "선두(lead)"라는 뜻이
  없어졌고, 이제 감점/vision fault/findings **세 경로가 이 값 하나를 공유**한다.
- 상한(6)은 별개이며 **3곳 동시**여야 한다: `exercise_map._MAX_EXERCISES` ·
  `models.MAX_RECOMMENDED_EXERCISES` · `firestore_admin._validate_recommended_exercises`.
  셋이 어긋나면 유효한 운동이 조용히 잘리거나 저장이 거부된다 — 어긋남을 막는 테스트
  (`test_generation_cap_locksteps_with_storage_cap`)를 넣어 뒀다.
- 참고: 2로 올리면 위 실측표 개수가 대략 두 배가 된다(상한 6에서 잘림). belle 09-03 은
  "한 두개씩"이라 했으므로 1이냐 2냐는 화면을 보고 정할 여지가 있다.

## 모달 ('보완 운동 더 보기') 실측

| | 섹션 | 행 | 이름 중복 |
|---|---|---|---|
| **전 (모든 분석 동일)** | 14 | **43** | **14행** (유니크 29) |
| c64afae6 | 4 | 17 | 0 |
| 890e3b8b | 3 | 15 | 0 |
| 03a5b62d | 4 | 15 | 0 |
| 26a6c7e1 | 5 | 20 | 0 |

- 결함 그룹은 **그 그룹의 대표 운동이 처방됐을 때만** 포함한다. 처음엔 "아무 항목이나
  겹치면"으로 짰다가 실측했더니 `Squats` 하나 때문에 둔근 그룹이 **4개 doc 전부에**
  딸려 나왔다(라이브러리가 같은 운동을 여러 그룹이 공유한다). 대표 기준으로 바꾸니
  둔근 그룹은 실제로 엉덩이 감점이 있는 `c64afae6` 에만 남는다.
- 중복 제거는 **선택 이후**에만 돈다. 반대로 하면 표시되지 않는 섹션이 먼저 이름을
  가져가 정작 보여줄 그룹에서 그 운동이 사라진다(앞면 카드엔 있는데 모달엔 없는 구멍).
  "처방된 운동은 모달 어딘가에 반드시 보인다"를 테스트로 고정했다.
- 통증부위 그룹은 중복 제거로 운동이 0이 되어도 **회피 안내가 있으면 남긴다** —
  안전 정보라서.
- 감점 부위가 하나도 없으면 빈 상태 문구를 그린다. 화살표만 있고 아무것도 없는 화면은
  만들지 않았다.

## 하지 말라고 한 것 — 지켰는지

| 금지 | 상태 |
|---|---|
| `corrective_exercises.json` 내용 편집 | 무접촉 (byte 동기 게이트 `test_corrective_exercises_app_lockstep` PASS) |
| LLM 으로 운동 생성 | 안 했다 — 순수 규칙 매핑 유지. **이번 변경의 LLM 학습 영향 0** (Cerebras/Gemini 경로 미접촉, 프롬프트·코퍼스 무변경) |
| `ResultExerciseTab.tsx MAX_ROWS = 3` | 값 무접촉 (주석의 "3~5" 표기만 갱신) |
| `exerciseId`(phrasebook) | 무접촉 |
| `RenderedComparePlayer.tsx` / `sourceSwapSeek.ts` / `analysisDate.ts` / `limb_collapse.py` + 배선 | 전부 무접촉 |
| 새 부위 어휘 신설 | 안 만들었다 — 기존 두 표(`vision_veto._KEYPOINT_SET_BY_KEYWORD`, `exercise_map._KEYPOINT_SET_TO_DEFECTS`)를 이었다. `vision_veto.match_keypoint_set` 은 **같은 표를 조회하는 공개 구멍**이지 새 표가 아니다 (미상 시 기본값 `torso` 로 삼키는 대신 `None` 을 돌려준다 — 보완운동 쪽에서 기본값은 근거 없는 코어 운동 처방이 되므로) |
| Firestore 쓰기 | 읽기만 (`collection_group("analyses").stream()`) |

## 검증의 한계 (플랜 승계 + 추가)

플랜 §검증의 한계를 그대로 승계한다:

- `map_exercises` 직접 호출 실측은 **저장된 입력을 다시 넣어 본 것**이지 실제 파이프라인
  실행이 아니다. 실제 분석에서 같은 결과가 나오는지는 **Pod 실행으로만** 확인된다.
  (다만 착수 전 코드로는 4건 전부 저장값과 완전 일치했으므로, 입력 재구성 자체는 충실하다.)
- belle 기존 doc 은 안 바뀐다. 화면에서 보려면 **재분석이 필요**하다.
- 결함당 1개냐 2개냐는 **belle 이 화면 보고 정할 것**이다. 숫자로 미리 못 정한다.

이번 작업에서 추가로 남는 한계:

- **`fault_keypoint_sets` 재구성은 근사다.** pipeline 은 `supported_differences` 와
  `root_cause_hypotheses` 둘에서 뽑는데 doc 에는 후자만 저장된다. 4건 전부 저장값을
  정확히 재현했으니 이 표본에선 문제가 없었지만, 일반적으로 일치가 보장되진 않는다.
- **앱 화면은 렌더 미확인이다.** typecheck 와 순수함수 테스트만 돌렸다 —
  typecheck 는 렌더 크래시를 못 잡는다([[verify-ui-on-simulator-before-ota]]).
  **OTA 전에 시뮬레이터에서 모달을 열어보는 것이 필수**다. 특히 확인할 것 둘:
  (1) 감점 없는 분석에서 빈 상태 문구, (2) 통증부위 섹션이 운동 0개 + 회피 박스만
  있는 모양.
- **표본이 4건이다.** 09-10 이전 doc 중 `deductionBreakdown.records` 를 가진 것만
  이 경로를 탄다. 구 doc(레코드 부재)은 `deduction_keypoint_sets=None` 으로 기존 경로와
  byte-동등이라 안전하지만, 그만큼 개선도 없다.

## 다음에 물어볼 것 (belle)

1. 결함당 **1개**로 충분한가, **2개**인가 (`_EXERCISES_PER_DEFECT` 한 줄).
2. 통증부위 운동도 1개로 줄일까 (`03a5b62d` 가 4개인 이유의 절반).
3. 팔꿈치 감점이 어깨 운동으로 나오는 것을 두는가 — 두지 않으려면
   `corrective_exercises.json` 에 팔꿈치 결함 그룹을 **사람이** 추가해야 한다
   (NotebookLM 출처 원칙상 내가 지어내면 안 된다).
