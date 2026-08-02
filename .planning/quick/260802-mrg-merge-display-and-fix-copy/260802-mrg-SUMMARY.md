---
phase: quick-260802-mrg
plan: 01
subsystem: app-display
tags: [deduction-display, cause-merge, subtitle-copy, phrasebook-gate]
requires: [DeductionRecord.exerciseId, phrasebook 33-13 목표-선행 문형]
provides: [buildCauseGroupKeys, splitGoalClause, composeCueSubtitleKo, RegionSheetView.goalLine]
affects: [부위 칩, 그룹 마커, 감점 상세 시트, 재생 중 자막, illu-float 일러스트]
tech-stack:
  added: []
  patterns: [union-find over part keys, merge-only 단조성, fail-closed 절 분리]
key-files:
  created: [backend/tests/test_phrasebook_cause_grouping.py]
  modified:
    - app/src/lib/deductionSheet.ts
    - app/src/lib/__tests__/deductionSheet.test.ts
    - app/src/components/DeductionDetailSheet.tsx
    - app/src/app/analysis/result.tsx
decisions:
  - "병합 키 = exerciseId (시간 근접 규칙은 실측으로 기각)"
  - "병합은 부위 키 단위 — record 단위로 가르지 않는다 (merge-only 보존)"
  - "phrasebook 무변경 — 앱이 렌더 시점에 목표 절 자리만 옮긴다"
metrics:
  tasks: 3
  commits: 3
  duration: 약 1시간
  completed: 2026-08-02
---

# quick-260802-mrg: 감점 표시 병합 + 문구 교정 Summary

같은 원인(`exerciseId`)에서 나온 감점을 화면에서 한 항목으로 묶는 표시 계층 규칙과,
재생 자막을 목표-선행에서 결함-선행으로 재배치. 채점은 무접촉.

**커밋**

| # | hash | 내용 |
|---|---|---|
| 1 | `4b4150aa` | 원인 병합 키 + 목표 절 분리 순수 함수 |
| 2 | `3eca966f` | 칩·마커·시트·자막을 원인 단위로 배선 |
| 3 | `e75dea64` | phrasebook (motion × exerciseId) 해부학 정합 게이트 |

---

## 1. 병합이 실 fixture 에서 실제로 몇 건 발동하는가 — **0건**

출하되는 `buildCauseGroupKeys` 를 저장 fixture 4건에 그대로 먹여 센 값이다
(문서 인용 아님 — 함수 산출).

### 합계

| | 값 |
|---|---|
| fixture | 4건 (elbow-twist-sister / kip-up / pd-shape / power-spin) |
| record | 14건 |
| 그룹 수 (병합 전 → 후) | **8 → 8** |
| 병합으로 새로 생긴 항목 | **0건** |
| 화면 칩 변화 | **없음** (`팔 \| 어깨 \| 다리`, `다리 \| 어깨`, `다리`, `다리 \| 어깨` 그대로) |

### 왜 안 묶였나 — record 별 `exerciseId`

| fixture | criterion | exerciseId | before | after | 병합? |
|---|---|---|---|---|---|
| elbow-twist-sister | `left_elbow` | `grip_weak` | arm | arm | 아니오 |
| elbow-twist-sister | `right_elbow` | `grip_weak` | arm | arm | 아니오 |
| elbow-twist-sister | `left_shoulder` | `shoulder_unstable` | shoulder | shoulder | 아니오 |
| elbow-twist-sister | `right_shoulder` | `shoulder_unstable` | shoulder | shoulder | 아니오 |
| elbow-twist-sister | `left_hip` | `hip_hamstring_tight` | leg | leg | 아니오 |
| elbow-twist-sister | `right_hip` | `hip_hamstring_tight` | leg | leg | 아니오 |
| elbow-twist-sister | `left_knee` | `legs_not_extended` | leg | leg | 아니오 |
| elbow-twist-sister | `right_knee` | `legs_not_extended` | leg | leg | 아니오 |
| kip-up | `split_angle` | `hip_hamstring_tight` | leg | leg | 아니오 |
| kip-up | `left_shoulder` | `shoulder_unstable` | shoulder | shoulder | 아니오 |
| pd-shape | `right_knee` | `glute_hip_unstable` | leg | leg | 아니오 |
| power-spin | `leg_extension` | `legs_not_extended` | leg | leg | 아니오 |
| power-spin | `split_angle` | `hip_hamstring_tight` | leg | leg | 아니오 |
| power-spin | `left_shoulder` | `shoulder_unstable` | shoulder | shoulder | 아니오 |

**어깨↔팔 병합이 성립하려면 두 부위가 같은 `exerciseId` 를 공유해야 한다.**
보유 fixture 에서 그 조합이 성립하는 doc 이 하나도 없다:

- **elbow-twist-sister** 는 어깨·팔꿈치 record 를 **둘 다** 가진 유일한 fixture 지만,
  팔꿈치가 동작 전용 `grip_weak` 라 어깨(`shoulder_unstable`)와 묶이지 않는다.
  엘보 트위스트에서 팔꿈치는 그립이지 어깨 결함이 아니다 — 도메인적으로 옳고,
  이 판단은 코드 분기가 아니라 승인 fixture 데이터(phrasebook)가 한다.
- **power-spin** 은 phrasebook 매핑상 병합이 성립한다(어깨 = 동작 전용
  `shoulder_unstable`, 팔꿈치 = `__common__` → `shoulder_unstable`). 그러나
  **저장 doc 에 팔꿈치 record 자체가 없다**(3건 = leg_extension / split_angle /
  left_shoulder). 그래서 실 doc 으로는 발동하지 않는다.
- kip-up(2건) · pd-shape(1건) 은 애초에 어깨·팔 동시 보유가 아니다.

즉 **belle 이 실기기에서 본 화면은 이번 fixture 셋으로 재현되지 않는다.** 병합 코드는
합성 형상(테스트)에서만 발동을 확인했다. 아래 §5 미검증에 그대로 남긴다.

### 기각한 규칙 — "같은 순간"

오케스트레이터 1순위 후보였던 `같은 순간 + 해부학 인접 + 같은 측` 은 실측으로 기각했다.
근거는 재생 산출(`quick-260802-czw/replay_out.json`)의 프레임 값이다:

| 쌍 | 프레임 | 차이 | 판정 |
|---|---|---|---|
| `left_elbow` ↔ `left_shoulder` (elbow-twist) | 27 ↔ 67 | **40프레임 = 4.4초** | 병합 불성립 |
| `right_elbow` ↔ `right_shoulder` (elbow-twist) | 44 ↔ 27 | **17프레임 = 1.9초** | 병합 불성립 |
| `left_elbow` ↔ `right_shoulder` (elbow-twist) | 27 ↔ 27 | **0프레임** | 반대측·비인접인데 **묶임** |
| `leg_extension` ↔ `left_shoulder` (power-spin) | 72 ↔ 66 | **0.67초** | 다리↔어깨인데 **묶임** |

시간 근접은 병합 기준으로도 veto 조건으로도 쓰지 않았다. 한 원인이 서로 다른 순간에
드러나는 것이 실측이고, veto 로 넣으면 belle 이 요청한 병합이 다시 막힌다.

### 병합이 발동하는 조건 (phrasebook 전수)

`(motion × exerciseId)` 묶음의 부위 span 을 phrasebook 67 entry 전수로 계산했다.
**상하체를 걸치는 묶음은 0건.** 부위를 걸치는 유일한 묶음이 정확히 belle 이 지목한
어깨↔팔이다:

| exerciseId | 전역 부위 span |
|---|---|
| `core_weak` | (투영 없음 — `line`) |
| `glute_hip_unstable` | leg |
| `grip_weak` | arm |
| `hip_hamstring_tight` | leg |
| `legs_not_extended` | leg |
| `shoulder_unstable` | **shoulder + arm** |

동작별로 `shoulder_unstable` 이 shoulder+arm 을 함께 덮는 곳은
`__common__` · `ref-peter-pan` · `ref-sideway-spin` 3곳이다(전수 확인). power-spin 은
어깨만 동작 전용 entry 를 갖고 팔꿈치는 `__common__` 으로 떨어져 결과적으로 병합된다.

---

## 2. 채점 무접촉 — "통과했다" 가 아니라 출력값

### (a) 모듈 diff — 전부 빈 출력

`BASE=18417364` 고정. 아래 8경로의 `git diff $BASE` 는 **한 줄도 나오지 않았다**:

```
backend/shared/python/sunity_shared/analysis/deduction_engine.py
backend/shared/python/sunity_shared/analysis/dimensions.py
backend/shared/python/sunity_shared/analysis/ipsf_criteria.py
backend/shared/python/sunity_shared/analysis/fault_zoom.py
backend/functions/pipeline/app.py
backend/data/phrasebook.json
app/src/components/ScoreBreakdownSection.tsx
app/src/lib/deductionLabels.ts
```

실행 결과: 두 명령 모두 출력 0바이트. `phrasebook.json` 무변경이 곧
33-13 belle 승인 문형·`test_motion_specific_cueline_goal_first` 핀 보존의 증거다.

전체 변경분은 5파일뿐이다:

```
 app/src/app/analysis/result.tsx                 |  38 +-
 app/src/components/DeductionDetailSheet.tsx     |  26 ++
 app/src/lib/__tests__/deductionSheet.test.ts    | 526 ++++++++++++++++++++++++
 app/src/lib/deductionSheet.ts                   | 260 +++++++++++-
 backend/tests/test_phrasebook_cause_grouping.py | 208 ++++++++++
```

### (b) pytest 기준선 diff — FAILED/ERROR node ID 완전 동일

```
착수:  59 failed, 3807 passed, 27 skipped   in 43.37s
종료:  59 failed, 3812 passed, 27 skipped   in 40.76s
```

| 항목 | 값 |
|---|---|
| FAILED/ERROR node ID (before) | 59개 |
| FAILED/ERROR node ID (after) | 59개 |
| only-in-after (신규 실패) | **NONE** |
| only-in-before (사라진 실패) | **NONE** |
| 집합 동일 | **True** |

passed 증가 +5 = 이번에 추가한 `test_phrasebook_cause_grouping.py` 의 테스트 5개와
정확히 일치한다.

기준선 파일: `pytest-before.txt` / `pytest-after.txt` / `failed-before.txt` /
`failed-after.txt` (scratchpad `.../mrg/`). 리포 루트에서
`PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests` 로 실행.

> **플랜 기준선 수치와의 차이:** 플랜은 `59 failed / 3808 passed` 로 적었으나
> 실측은 `3807 passed` 였다. failed 수와 node ID 집합은 일치하므로 게이트 판정에는
> 영향이 없다. 문서 값이 아니라 실측 값을 기준으로 diff 했다.

### (c) 런타임 무변형 증명 — frozen record

문서 대조가 아니라 실행으로 확인했다. 저장 fixture 의 record 를 `Object.freeze`
재귀 적용한 뒤 표시 계층 전부(`buildCauseGroupKeys` / `buildPartGroups` /
`buildPartChips` / `buildRegionSheetView` × 전 record / `composeCueSubtitleKo`)를
돌렸다. ES module 은 strict mode 라 frozen 객체 쓰기는 TypeError 를 던진다.

**TypeError 0건.** 그리고 record 에서 점수를 재구성해 저장값과 대조:

| fixture | Σpoints | 재구성 final | 저장 final | overallScore | 일치 |
|---|---|---|---|---|---|
| elbow-twist-sister | −36.9 | 63 | 63 | 63 | ✅ |
| kip-up | −20.8 | 79 | 79 | 79 | ✅ |
| pd-shape | −0.2 | 100 | 100 | 100 | ✅ |
| power-spin | −44.8 | 60 | 60 | 60 | ✅ |

`formatDeductionRecord` 의 `pointsText` 도 record 원값 그대로 출력된다:
`−3.8, −12.4, −0.5, −11.1, −2.2, −2.1, −2.2, −2.6` (elbow-twist 8건) ·
`−20, −12, −12.8` (power-spin 3건).

### (d) 투명 합산 — 묶어도 개별 수치가 남는다

병합 시트에서 `blocks.length == 멤버 record 수` 이고, 각 블록이 자기 헤더에
`(−12.8점)` / `(−3.8점)` 을 달고 블록 맨 뒤 `numNote`(`측정 수치(참고) — …`)를
유지한다는 것을 테스트로 고정했다. `ScoreBreakdownSection`·`deductionLabels`·
`formatDeductionRecord` 는 무접촉(위 (a) 빈 diff)이라 점수 tally 는 record 1:1 로 남는다.

---

## 3. 자막이 실제로 어떻게 바뀌는가 — 실 record before/after

출하되는 `composeCueSubtitleKo` 산출이다. `before` 는 종전 조립식
(`rec.cueLine ?? 행동구`).

### 대표 4건

| fixture / criterion | | 문자열 |
|---|---|---|
| power-spin `left_shoulder` | BEFORE (85자) | 목표는 폴을 따라 위아래 한 줄 스플릿이에요. 어깨가 귀 쪽으로 으쓱 올라가지 않게 견갑을 눌러 잡고, 팔과 몸통 사이 각을 기준 자세에 겹쳐 맞춰보세요 |
| | AFTER (95자) | 왼쪽 어깨(겨드랑이) 각도가 파워스핀 기준 자세와 차이가 있어요 어깨가 귀 쪽으로 으쓱 올라가지 않게 견갑을 눌러 잡고, 팔과 몸통 사이 각을 기준 자세에 겹쳐 맞춰보세요 |
| kip-up `split_angle` | BEFORE (77자) | 목표는 무릎을 편 채 양다리를 좌우로 크게 벌려 반동을 만드는 거예요. 다리를 와이드 스트래들로 활짝 벌린 채, 반동을 다리로 만들어보세요 |
| | AFTER (60자) | 다리를 벌린 각도가 킵업 기준보다 좁아요 다리를 와이드 스트래들로 활짝 벌린 채, 반동을 다리로 만들어보세요 |
| pd-shape `right_knee` | BEFORE (95자) | 목표는 거꾸로 매달려 한 다리는 걸고 한 다리는 깊게 접은 모양을 그대로 지키는 거예요. 무릎을 펴는 게 아니라, 깊게 접은 다리 모양 그대로 기준 자세에 겹쳐 맞춰보세요 |
| | AFTER (72자) | 오른쪽 무릎 각도가 기준 셰이프와 차이가 있어요 무릎을 펴는 게 아니라, 깊게 접은 다리 모양 그대로 기준 자세에 겹쳐 맞춰보세요 |
| power-spin `split_angle` | BEFORE (37자) | 양 무릎을 각각 반대쪽 벽으로 밀어낸다는 느낌으로 다리를 벌려보세요 |
| | AFTER (57자) | 다리를 벌린 각도가 기준보다 좁아요 양 무릎을 각각 반대쪽 벽으로 밀어낸다는 느낌으로 다리를 벌려보세요 |

### 길이 통계 (n=14)

| | 중앙값 | 최대 | 추정 클립 초과 |
|---|---|---|---|
| BEFORE | 83자 | 99자 | 3건 |
| AFTER | 81자 | 96자 | **3건 (변화 없음)** |

- AFTER 가 더 짧아진 record 8건 / 더 길어진 record 6건.
- `목표는` 으로 시작하는 record: **14 → 0건**. 결함 문장으로 시작: **0 → 14건**.

**`numberOfLines={3}` 클립에 여전히 걸린다.** 길이는 실질적으로 안 줄었다 —
목표 절이 빠진 만큼 `statusLine` 이 들어오기 때문이고, `__common__` 문형
(목표 절이 애초에 없던 record)은 statusLine 이 붙어 **길어진다**(37→57, 45→74).

이 수정의 값어치는 길이가 아니라 **순서**다. 잘리는 쪽이 목표 절 뒤의 행동 절에서
행동 절의 꼬리로 바뀌었고, 결함은 이제 자막 맨 앞에 항상 있다. belle 의 지적
("자막이 결함 대신 목표를 말한다")은 순서 문제였다.

> **추정치 고지:** "추정 클립 >88자" 는 caption fontSize 12 · 자막 폭
> 390−16−20=354pt · 한글 글리프 약 12pt → 줄당 약 29자 → 3줄 약 88자 로 계산한
> **산술 추정**이다. 실기기·시뮬로 렌더해 줄 수를 세지 않았다.

---

## 4. 시뮬레이터로 화면을 열었는가 — **안 봤다**

`npm run typecheck` 는 렌더 크래시를 잡지 못한다
([[verify-ui-on-simulator-before-ota]]). 그런데 이번 사이클에서는 열지 못했다.
이유를 그대로 적는다:

1. `xcrun simctl list devices booted` = 부팅된 시뮬레이터 **0대**.
2. 이 태스크의 실행 제약이 **네트워크 금지 · 패키지 설치 금지**다. 결과 화면은
   Firestore `onSnapshot` 으로 doc 을 받아야 렌더되고 Expo dev server 기동도
   네트워크를 탄다 — 제약 안에서 실행 불가.
3. 설령 열었어도 **병합 화면은 볼 수 없다.** 보유 실 doc 4건 중 병합이 발동하는
   것이 0건이기 때문이다(§1). 시뮬로 확인 가능한 것은 미병합 경로(=오늘과 동일)와
   goalLine·자막뿐이다.

따라서 아래는 **코드 게이트로만 확인**했고 눈으로 본 것이 아니다:
`goalLine` 박스 렌더, 병합 항목 칩 1개, 자막 첫머리. 실기기 확인 항목은 §5.

---

## 5. 미검증 — 전건

| # | 항목 | 상태 | 이유 |
|---|---|---|---|
| 1 | 실 doc 병합 실증 | **미검증** | 보유 fixture 4건에서 병합 0건(§1). 합성 형상 테스트로만 발동 확인 |
| 2 | 시뮬/실기기 렌더 | **안 봤다** | §4 — 시뮬 미부팅 + 네트워크 금지 + 병합 doc 부재 |
| 3 | `numberOfLines={3}` 실제 클립 | **미측정** | 글자수만 셌다. 줄 수는 산술 추정 |
| 4 | 음성 mp3 ↔ 자막 낭독 차이 | **안 들었다** | mp3 는 분석 시점 cueLine(목표 포함), 자막은 statusLine+행동. 음성 기본 off + F-6 무음 미해결이라 현재 관측 불가 |
| 5 | belle 인용 어깨 문자열 재현 | **재현 안 됨(의도)** | 인용 문자열은 `__common__` 폴백 유래 stale doc. 현행 경로는 실 fixture 4건 전부 `motionId` 해석에 성공해 동작 전용 문구를 낸다 |
| 6 | 병합 시 일러스트 부착 | **측정함 — 안 붙는다** | 아래 별도 항목 참조 |

### 6번 상세 — 병합이 발동하면 일러스트가 사라진다 (측정값)

`app/src/lib/illustrationScene.ts` 의 `ILLUSTRATION_SCENES` 를 전수로 읽었다.
`parts` 값은 `['leg']` ×6 · `['shoulder']` ×2 · `['arm']` ×1 뿐이고 **`['shoulder','arm']`
을 함께 덮는 장면은 0건**이다. `sceneCoversParts` 는 "항목 토큰 **전부**가 장면
`parts` 에 있어야" 참이므로, 병합된 `shoulder+arm` 항목은 `illustrationAssetForPart`
= null 이 되어 **시트 일러스트와 영상 위 illu-float 가 둘 다 렌더되지 않는다.**

- 크래시는 없다. 두 표면이 **같은 판정**이라 P-9(시트에서 숨긴 그림이 영상 위에
  뜨는 결함)도 안 생긴다 — 이탈 2 의 교체가 이 정합을 지킨다.
- 다만 병합의 대가로 그림 1장을 잃는 것은 사실이다. 병합이 실제로 발동하는 doc 이
  나오면(§1 기준 현재 0건) belle 눈에 그대로 보인다.
- 해결은 데이터 쪽이다 — `shoulder+arm` 장면 1건 추가. 이번 범위 밖(신규 일러스트
  자산 생성·검증은 §C-4 계열 작업)이라 하지 않았다. **다음 사이클 후보.**

---

## 6. 플랜 이탈

### 이탈 1 — 병합 단위: record 단위 → **부위 키 단위** (Rule 1)

플랜 Task 1 action ⑤ 는 "`criterion:` 키와 **exerciseId 없는 record** 는 자기 부위
키를 그대로 유지한다" 였다. 그대로 구현하면 **T3(단조성)과 충돌한다**:

한 부위 키 안에 exerciseId 보유 record 와 미보유 record 가 섞이면, 보유분은
`shoulder+arm` 으로 가고 미보유분은 `shoulder` 에 남아 **오늘 한 그룹이던 것이
갈라진다**. 부위 키 2개(shoulder/arm)가 각각 미보유 record 를 하나씩 가지면
출력 키가 `{shoulder+arm, shoulder, arm}` = 3개가 되어 그룹 수가 **늘어난다**.
이는 같은 action 이 명시한 "merge-only — 오늘 한 그룹인 것이 갈라지는 경로가
없어야 한다(T3)" 와 must_have 의 "칩 1개·마커 1경계·시트 1장" 을 동시에 깬다.

**채택**: 병합 판정은 부위 키 단위로만 하고, 한 부위 키의 record 는 exerciseId
보유 여부와 무관하게 같은 클러스터 키를 받는다. `exerciseId` 미보유 record 는
병합 **간선**을 만들지 않는다(T5 유지) — 자기 부위 키의 결정에 따를 뿐이다.

- 부위 키 → 클러스터 키가 **함수**가 되어 distinct 출력 ≤ distinct 부위 키가
  구조적으로 보장된다 (T3 무작위 400회 통과).
- 전건 미보유(legacy doc)면 간선 0 → 클러스터 전부 싱글턴 → `regionPartKeyForRecord`
  와 **완전 동일** (T4 통과).
- 가드 테스트 신설: `T3b — 한 부위 키의 record 는 exerciseId 보유 여부와 무관하게
  같은 키를 받는다`.

### 이탈 2 — `result.tsx` illu-float 부위 키도 교체 (Rule 2)

플랜 Task 2 는 `result.tsx` 에서 자막 조립 한 지점만 바꾸라고 했다. 그러나
`cueIllustrationForRecordId`(result.tsx:1852)가 `regionPartKeyForRecord` 를 직접
호출하고 있었고, 그 자리의 기존 주석이 **"마커 그룹·부위 칩·부위 시트와 같은 단위
(P-1)" · "장면일치는 시트와 같은 판정(P-9)"** 을 불변식으로 명시한다.

시트만 원인 단위로 옮기면 병합된 항목에서 시트는 `어깨·팔` 로, 영상 위 illu-float 는
`어깨` 로 판정해 **P-1/P-9 가 깨진다** — 시트에서 숨긴 그림이 영상 위에 뜨는 경로다.
같은 `buildCauseGroupKeys` 산출을 쓰도록 교체했다(useMemo 1개 추가). 파생 계산이라
점수·표시 문구에는 영향이 없다.

### 이탈 3 — 계약 주석의 점수 산식이 stale (수정 안 함, 관찰만)

`app/src/types/analysis.ts:706` 과 `deduction_engine.py:6,124` 의 주석은
`final = max(0, round(100 + Σ points))` 라고 적혀 있다. 실 fixture 로 재구성하면
power-spin 이 어긋난다(Σ=−44.8 → 55 ≠ 저장 60). 실제 산식은 Wave R 2트랙
(`deduction_engine.py:409`) `final = max(25, round(100 − min(40, Σ|실행|) − Σ|치명|))`
이고, 이 식으로는 4건 전부 일치한다(§2c).

**이번 작업 범위 밖이라 고치지 않았다** (scope boundary — 채점/계약 문서는 무접촉
대상). 다음 사이클 후보로 남긴다: 계약 주석 3곳(TS/Python/contract.md) lockstep 갱신.

---

## 7. 무엇이 바뀌었나 (코드 요약)

| 표면 | 변화 |
|---|---|
| `buildCauseGroupKeys` (신규) | 부위 키 → 원인 키. union-find, merge-only, 시간 근접 미사용 |
| `splitGoalClause` (신규) | 저장 cueLine 을 목표/행동 절로 분리. 접두+구분자 둘 다 성립할 때만 (fail-closed). `actionLine` 은 항상 원문 부분 문자열 |
| `composeCueSubtitleKo` (신규) | `statusLine` + `actionLine`. 자막 **유무 조건은 종전 그대로** — statusLine 만으로는 자막을 만들지 않는다(cueTrack 입력 집합 무변화) |
| `RegionSheetView.goalLine` (신규 필드) | 그룹 대표(`|points|` 최대, 동점이면 저장 순서 앞선) record 의 목표 절. 없으면 `null` |
| `RegionSheetBlock.cueLine` | 목표 절을 뺀 행동 절로 교체. 목표 절 없는 문형은 원문 그대로 |
| `buildPartGroups` / `buildPartChips` / `buildRegionSheetView` | 그룹 키를 `buildCauseGroupKeys` 배열 조회로 교체 (세 소비처 같은 배열) |
| `DeductionDetailSheet` | `goalLine` 박스 렌더 (제목 아래·블록 위, `oneCap` 과 다른 자리). 기존 토큰만(`softBg`/`border`/`bodySm`/`textMid`) — hex·수치 하드코딩 0 |
| `result.tsx` | 자막 조립 1지점 교체 + illu-float 부위 키 교체 |
| `test_phrasebook_cause_grouping.py` (신규) | 상하체 걸침 0 · exerciseId 실존 · 투영 미러 lockstep · 병합 대상 실존 · `__common__` 경로 |

`regionPartKeyForRecord` 본문은 **무변경**(diff 상 삭제 라인 0). 신규 파일은 백엔드
테스트 1개뿐이고 앱은 신규 파일 0.

---

## 8. 자동 게이트 결과

| 게이트 | 결과 |
|---|---|
| `npm run typecheck` | **0 error** |
| `node --test` (deductionSheet + cueTrack + resultSections + summarySource + screenVocabulary + illustrationScene) | **112 pass / 0 fail** |
| `node --test` (app/src/lib/__tests__ 전체) | **155 pass / 0 fail** |
| `deductionSheet.test.ts` 단독 | 41 → **66 pass** (신규 25) |
| pytest 전체 FAILED/ERROR node ID diff | **빈 집합** (59 = 59, 양방향 NONE) |
| 백엔드 산출 6경로 + 앱 tally 2경로 `git diff $BASE` | **전부 빈 출력** |
| 변경 추가 라인의 `ref-` 동작명 리터럴 / `9.0` 리터럴 | **0회** |
| 커밋별 파일 삭제 | **0건** (3커밋 전부) |

---

## 9. belle 실기기 확인 항목 (OTA 발행 후)

1. 파워스핀 결과 화면 — 어깨 항목과 팔꿈치 항목이 칩 1개로 보이는가
   (**주의: 현재 보유 doc 으로는 이 상황이 재현되지 않는다.** 팔꿈치 감점이 잡힌
   새 영상이 필요하다)
2. 항목을 열었을 때 목표 문장 1줄이 위에 있고, 아래 감점들이 각각 자기 −X점을 다는가
3. 재생 자막이 결함을 먼저 말하는가 (킵업에서 "목표는…" 으로 시작하지 않는가)
4. 자막이 3줄에서 잘리는 정도가 견딜 만한가 (길이는 안 줄었다 — §3)

---

## Self-Check: PASSED

- `app/src/lib/deductionSheet.ts` — FOUND (수정)
- `app/src/lib/__tests__/deductionSheet.test.ts` — FOUND (수정)
- `app/src/components/DeductionDetailSheet.tsx` — FOUND (수정)
- `app/src/app/analysis/result.tsx` — FOUND (수정)
- `backend/tests/test_phrasebook_cause_grouping.py` — FOUND (신규)
- 커밋 `4b4150aa` / `3eca966f` / `e75dea64` — 전건 `git log` 확인
