---
phase: quick-260802-mrg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/lib/deductionSheet.ts
  - app/src/lib/__tests__/deductionSheet.test.ts
  - app/src/components/DeductionDetailSheet.tsx
  - app/src/app/analysis/result.tsx
  - backend/tests/test_phrasebook_cause_grouping.py
autonomous: true
requirements: [BELLE-0802-MERGE, BELLE-0802-COPY-A, BELLE-0802-COPY-B]

must_haves:
  truths:
    - "같은 원인(exerciseId 공유)으로 판정된 감점이 화면에서 항목 1개(칩 1개·마커 1경계·시트 1장)로 보인다"
    - "묶인 항목 안에서 각 감점의 크기(−X점)를 개별로 볼 수 있다"
    - "묶인 항목은 그 동작이 무엇을 하려는 것인지 한 문장으로 설명한다"
    - "재생 중 자막이 목표가 아니라 결함을 먼저 말한다"
    - "총점·각 record 의 points·measuredValue 가 변경 전과 동일하다"
    - "exerciseId 가 없는 record 는 묶이지 않고 지금과 똑같이 보인다"
  artifacts:
    - path: "app/src/lib/deductionSheet.ts"
      provides: "buildCauseGroupKeys / splitGoalClause / composeCueSubtitleKo + RegionSheetView.goalLine"
      exports: ["buildCauseGroupKeys", "splitGoalClause", "composeCueSubtitleKo"]
    - path: "app/src/lib/__tests__/deductionSheet.test.ts"
      provides: "병합 단조성·투명성·fail-closed·하위호환 불변식"
      contains: "buildCauseGroupKeys"
    - path: "backend/tests/test_phrasebook_cause_grouping.py"
      provides: "phrasebook (motion × exerciseId) 묶음의 해부학 정합 데이터 게이트"
      contains: "exerciseId"
  key_links:
    - from: "app/src/lib/deductionSheet.ts"
      to: "DeductionRecord.exerciseId"
      via: "병합 키 (신규 계약 0 — 이미 실 doc record 에 실려 있음)"
      pattern: "exerciseId"
    - from: "app/src/lib/deductionSheet.ts:buildPartGroups/buildPartChips/buildRegionSheetView"
      to: "buildCauseGroupKeys"
      via: "그룹 키 단일 출처 교체 (regionPartKeyForRecord 사본 0 유지)"
      pattern: "buildCauseGroupKeys"
    - from: "app/src/app/analysis/result.tsx"
      to: "composeCueSubtitleKo"
      via: "자막 text 조립 (결함 먼저)"
      pattern: "composeCueSubtitleKo"
---

<objective>
같은 원인에서 나온 감점을 **화면에서 한 항목으로** 묶고(표시 전용, 채점 무접촉),
장면과 안 맞는 문구 두 결함을 고친다.

Purpose: belle 실기기(08-01) — 어깨 항목과 팔꿈치 항목이 한 잘못인데 따로 보이고,
자막이 결함 대신 목표를 말한다.
Output: 앱 표시 계층의 원인 병합 + 문구 재배치. 백엔드 산출·점수 무변경.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/CLAUDE.md
@app/src/lib/deductionSheet.ts
@app/src/lib/deductionLabels.ts
@app/src/types/analysis.ts
@app/src/components/DeductionDetailSheet.tsx
@backend/data/phrasebook.json
@.planning/quick/260801-gbk-record-atframeidx-criterion/260801-gbk-SUMMARY.md
</context>

---

## 착수 전에 읽을 것 — 이 플랜이 근거로 삼은 실측

아래는 전부 **직접 열어서 읽은 값**이다. 규칙은 이 표에서 나왔지 추정에서 나오지 않았다.

### 측정 1 — record 별 측정 순간 (실 fixture 4건 재생 산출)

출처: `.planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json`
(quick-260802-czw 가 `backend/evals/realfixture/replay.py` 로 실 fixture 를 현행 코드로 재생한 산출).
저장 fixture 자체는 `atFrameIdx` 가 전부 `null` 이다 — quick-260801-gbk 이전 doc 이라서다.

`elbowtwistsisterFault` (감점 8건, 학생 9fps):

| criterion | atFrameIdx | atVideoSec | points | exerciseId |
|---|---|---|---|---|
| left_elbow | 27 | 3.00 | −3.8 | grip_weak |
| right_elbow | 44 | 4.89 | −12.4 | grip_weak |
| left_shoulder | 67 | 7.44 | −0.5 | shoulder_unstable |
| right_shoulder | 27 | 3.00 | −11.1 | shoulder_unstable |
| left_hip | 30 | 3.33 | −2.2 | hip_hamstring_tight |
| right_hip | 54 | 6.00 | −2.1 | hip_hamstring_tight |
| left_knee | 134 | 14.89 | −2.2 | legs_not_extended |
| right_knee | 18 | 2.00 | −2.6 | legs_not_extended |

`powerspinFault` (재생 4건): leg_extension 72/8.00 −20 · left_shoulder 66/7.33 −12.8 ·
left_hip 7/0.78 −2.9 · right_hip 11/1.22 −1.9.

### 측정 2 — "같은 순간" 규칙은 성립하지 않는다 (기각)

오케스트레이터가 1순위 후보로 준 **`같은 순간` + `해부학 인접` + `같은 측`** 의 실측 결과:

- `left_elbow`(27) ↔ `left_shoulder`(67) = **40프레임 = 4.4초 차이**
- `right_elbow`(44) ↔ `right_shoulder`(27) = **17프레임 = 1.9초 차이**
- → 어깨·팔꿈치 record 를 둘 다 가진 **유일한** 실 fixture 에서 **병합 0건.**

그리고 `같은 순간` 단독은 **틀린 병합을 만든다**:

- `left_elbow`(27) 과 `right_shoulder`(27) 은 **정확히 같은 프레임**인데 반대측·비인접.
- powerspin `leg_extension`(72) 과 `left_shoulder`(66) = **0.67초 차이**인데 다리↔어깨.

→ **시간 근접은 병합 기준에서도 veto 조건에서도 쓰지 않는다.** 한 원인이 서로 다른
순간에 드러날 수 있다는 것이 실측이고, belle 이 지목한 "80점에서도 설명하는 팔꿈치"가
정확히 그 형태다. 시간 veto 를 넣으면 belle 이 요청한 병합이 다시 막힌다.

### 측정 3 — 병합 키는 이미 실 doc 에 실려 있다

저장 fixture 4건 **전 record 에 `exerciseId` 가 존재**한다(위 표 + powerspin/kipup/pdshape 확인).
`backend/shared/python/sunity_shared/models.py:255` `DEDUCTION_PHRASE_KEYS` 에 포함되어 각인되고,
`app/src/types/analysis.ts:739` 에 계약으로 이미 노출돼 있다.

→ **백엔드 변경 0, Pod 재분석 0.** belle 이 지금 들고 있는 doc 으로 OTA 만으로 동작한다.

### 측정 4 — exerciseId 단독 분할은 위험, 합집합은 안전

`exerciseId` 로 **새로 나누면** ref-elbow-twist-sister 에서 현행 부위 그룹 3개(shoulder/arm/leg)가
4개가 되고, `hip_hamstring_tight`(엉덩이)와 `legs_not_extended`(무릎)가 **둘 다 "다리" 칩**이 된다 —
같은 이름 칩 2개. 쪼개는 방향은 belle 요청의 반대이기도 하다.

→ 규칙 = **부위 그룹을 쪼개지 않는다. exerciseId 를 공유하는 부위 그룹만 합친다**
(merge-only. 그룹 수는 절대 늘지 않는다).

### 측정 5 — 합집합의 해부학 정합 (phrasebook 전수)

`backend/data/phrasebook.json` 67 entry 를 (motion × exerciseId) 로 묶어 부위 토큰 span 을 계산:

| exerciseId | 부위 span |
|---|---|
| core_weak | (투영 없음) |
| glute_hip_unstable | leg |
| grip_weak | arm |
| hip_hamstring_tight | leg |
| legs_not_extended | leg |
| shoulder_unstable | **shoulder + arm** |

상체·하체를 걸치는 묶음은 **0건**. 유일하게 부위를 걸치는 `shoulder_unstable` 이
**정확히 belle 이 지목한 어깨↔팔꿈치**다.

- **power-spin**: shoulder = `ref-power-spin` 전용 entry → `shoulder_unstable`,
  elbow = `__common__` → `shoulder_unstable` → **병합 성립.**
- **elbow-twist-sister**: elbow = 동작 전용 `grip_weak` → 어깨와 **병합 안 됨.**
  (엘보 트위스트에서 팔꿈치는 그립이지 어깨 결함이 아니다 — 도메인적으로 옳고,
  코드 분기 0. 판단은 승인 fixture 데이터가 한다.)

### 측정 6 — belle 이 인용한 어깨 문구는 stale doc 이다 (먼저 말해둔다)

belle 인용 = "왼쪽 어깨(겨드랑이) **벌린** 각도가 기준 자세와 차이가 있어요"
= `__common__.angle_vs_reference__left_shoulder`.statusLine (동작 미해석 폴백 문구).

현행 코드는 실 fixture 4건 전부 `motionId` 해석에 성공한다(`ref-power-spin`/`ref-kip-up`/
`ref-pdshape`/`ref-elbow-twist-sister` — replay 산출 확인). 그 경로의 저장 문구는
"왼쪽 어깨(겨드랑이) 각도가 **파워스핀** 기준 자세와 차이가 있어요"다(저장 fixture 실측).
동작 전용 entry 는 `5065a1ab`(33-09) 에서 생겼다.

→ **belle 화면의 그 문자열은 이번 수정과 무관하게 다시 나오지 않는다.** 다만 belle 의
지적("관절 각도를 기계적으로 이름 붙인다")은 두 문구 모두에 그대로 성립하므로 고친다.

### 측정 7 — 자막은 3줄로 하드 클립된다

`app/src/components/VideoCompare.tsx:1553` `numberOfLines={3}`.
목표-선행 cueLine 길이 = **중앙값 84자 / 최대 107자**, belle 이 본 킵업 split = **77자**.
→ 목표 절이 앞에 있으면 **잘리는 쪽은 행동 절**이고, **결함은 애초에 자막에 없다.**

### 측정 8 — 목표-선행 cueLine 은 belle 승인 + 테스트 핀이다 (되돌리지 않는다)

`33-11` 4R belle 승인 → `33-13` 구현(`0f7cf700`), `_meta.goalFirstCueLine` 박제,
`test_motion_specific_cueline_goal_first` 전수 핀. 동작 전용 54/67 entry 의 cueLine 이
`"목표는 {목표}. {행동 큐}"` 이고, **54건 전부 `". "` 구분자를 가진다**(전수 확인).
`__common__` entry 에는 목표 절이 **없다**.

→ **phrasebook 은 한 글자도 고치지 않는다.** 목표 절은 **앱이 렌더 시점에 분리**해
말하는 자리를 옮긴다. 승인 문형·핀·기존 doc·기존 mp3 전부 그대로 산다.

---

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 원인 병합 규칙 + 목표 절 분리 (순수 함수)</name>
  <files>app/src/lib/deductionSheet.ts, app/src/lib/__tests__/deductionSheet.test.ts</files>
  <behavior>
    buildCauseGroupKeys(records, faultJoints) → string[] (record별 그룹 키)
    - T1: exerciseId 를 공유하는 두 부위 그룹(shoulder / arm)이 한 키 `shoulder+arm` 로 합쳐진다
    - T2: 같은 부위 안의 서로 다른 exerciseId(hip_hamstring_tight / legs_not_extended)는
          **쪼개지지 않는다** — 둘 다 `leg` (측정 4)
    - T3: 단조성 — 임의 입력에서 distinct 키 수 ≤ regionPartKeyForRecord 의 distinct 키 수
    - T4: fail-closed — exerciseId 부재(legacy doc) record 전건이면 결과가
          regionPartKeyForRecord 결과와 **완전 동일**
    - T5: exerciseId 가 빈 문자열/비문자열이면 병합 간선 0 (억지 병합 금지)
    - T6: `criterion:` 접두 그룹은 병합에 참여하지 않는다 (그릴 부위가 없어 라벨 모호)
    - T7: 결정성 — 입력 순서 동일 시 출력 동일, 키 안의 부위 토큰 순서는 PART_ORDER

    splitGoalClause(cueLine) → { goalLine: string|null, actionLine: string }
    - T8: `"목표는 A. B"` → { goalLine: "목표는 A.", actionLine: "B" }
    - T9: 목표 접두 없음(`__common__` 문형) → { goalLine: null, actionLine: 원문 그대로 }
    - T10: `". "` 구분자 없음 → { goalLine: null, actionLine: 원문 그대로 } (fail-closed)
    - T11: actionLine 은 항상 원 cueLine 의 부분 문자열 (음성이 말하지 않은 말 금지)
    - T12: null/undefined/빈 문자열 → { goalLine: null, actionLine: '' } 크래시 0

    composeCueSubtitleKo(record, fallbackActionPhrase) → string|null
    - T13: statusLine + actionLine 있으면 `"{statusLine} {actionLine}"` (결함이 먼저)
    - T14: statusLine 없으면 actionLine 단독
    - T15: cueLine 없으면 fallbackActionPhrase (기존 legacy 폴백 유지)
    - T16: 둘 다 없으면 null (자막 미렌더)
    - T17: 산출에 `목표는` 리터럴이 0회
  </behavior>
  <action>
    `app/src/lib/deductionSheet.ts` 에 순수 함수 3종을 추가한다. **새 파일을 만들지 않는다** —
    부위 키 산출(`regionPartKeyForRecord`)이 이 파일 소유이고, 그룹핑 규칙 사본을 2벌로
    만들지 않는 것이 이 파일 헤더의 기존 계약이다(N-16).

    (1) `buildCauseGroupKeys(records, faultJoints)`:
        ① 먼저 record 마다 `regionPartKeyForRecord` 로 오늘의 부위 키를 구한다 — **이 함수는
           손대지 않는다.** ② `criterion:` 접두가 아닌 부위 키들만 대상으로, 각 부위 키가
           보유한 `record.exerciseId`(비어있지 않은 string) 집합을 모은다. ③ exerciseId 를
           하나라도 공유하는 부위 키끼리 union-find 로 합친다. ④ 클러스터의 대표 키 =
           멤버 부위 키들의 토큰 합집합을 `PART_ORDER` 순으로 `+` 결합 — 기존 키 문법
           그대로라 `partLabelKo` 가 이미 "어깨·팔" 을 만든다(신규 어휘 0). ⑤ `criterion:`
           키와 exerciseId 없는 record 는 자기 부위 키를 그대로 유지한다.
        규칙은 **merge-only** 다: 오늘 한 그룹인 것이 갈라지는 경로가 없어야 한다(T3).
        시간 근접(`atFrameIdx`/`atVideoSec`)은 **쓰지 않는다** — 측정 2 근거를 주석에 남긴다
        (숫자와 함께. "안 맞았다"가 아니라 40프레임/17프레임/0.67초를 적는다).

    (2) `splitGoalClause(cueLine)`: `_meta.goalFirstCueLine`(33-13, belle 4R 승인 문형)이
        보장하는 `"목표는 …. {행동}"` 구조를 **첫 `". "` 에서 1회만** 자른다. 접두·구분자
        어느 하나라도 없으면 자르지 않는다(fail-closed). phrasebook 은 읽지도 고치지도
        않는다 — 앱은 doc 에 실려 온 문자열만 다룬다.

    (3) `composeCueSubtitleKo(record, fallbackActionPhrase)`: 자막 1줄 조립.
        `statusLine`(결함) 먼저, 그 뒤에 `actionLine`(목표 절 제거된 행동). 목표 절은
        자막에서 빠지고 병합 항목 head 에서 **한 번만** 말한다(Task 2).

    (4) `RegionSheetView` 에 `goalLine: string | null` 필드를 추가하고
        `buildRegionSheetView` 에서 채운다: 그룹 멤버 중 `|points|` 최대(동점이면 저장
        순서 앞선) record 의 `splitGoalClause(...).goalLine`. 없으면 `null`(문구 창작 0).
        각 블록의 `cueLine` 은 `actionLine` 으로 바꾼다 — 같은 목표 문장을 N번 반복하지
        않는 것이 "한 항목처럼 한 문장으로 설명"의 실체다.
        `numNote`(개별 −X점)·`formatDeductionRecord` 는 **손대지 않는다**(투명 합산).

    주석은 한국어, `quick-260802-mrg` 인용. 동작명 리터럴(`ref-…`) 금지 — 규칙은
    `criterion`/`exerciseId`/부위 투영으로만 키잉한다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app &amp;&amp; npm run typecheck &amp;&amp; node --test src/lib/__tests__/deductionSheet.test.ts</automated>
  </verify>
  <done>
    T1~T17 전건 통과. `buildCauseGroupKeys`/`splitGoalClause`/`composeCueSubtitleKo` export.
    `regionPartKeyForRecord` 본문 무변경(git diff 로 확인). 신규 파일 0.
  </done>
</task>

<task type="auto">
  <name>Task 2: 표시 배선 — 칩·마커·시트·자막을 원인 단위로</name>
  <files>app/src/lib/deductionSheet.ts, app/src/components/DeductionDetailSheet.tsx, app/src/app/analysis/result.tsx, app/src/lib/__tests__/deductionSheet.test.ts</files>
  <action>
    (1) `buildPartGroups` / `buildPartChips` / `buildRegionSheetView` 의 그룹 키 호출을
        `regionPartKeyForRecord` 단건 호출에서 `buildCauseGroupKeys` 가 만든 **키 배열
        조회**로 바꾼다. 세 소비처가 같은 배열을 쓰므로 "마커 그룹 = 부위 칩 = 상세 시트"
        가 같은 단위라는 기존 불변식(33-G S1/S3)이 원인 단위에서도 유지된다.
        `buildPartChips` 의 참고(advisory) 칩 경로·`estimatedArea` 억제·번호 부여
        (`recordNumbers`)는 **한 줄도 바꾸지 않는다**.

    (2) `DeductionDetailSheet` 에 `view.goalLine` 렌더를 추가한다 — 제목 아래, 블록 위,
        `oneCap`(사진 설명)과 **다른 자리**. `null` 이면 자리도 두지 않는다.
        스타일은 기존 토큰만(`src/theme/`) — 색·여백 하드코딩 금지.

    (3) `result.tsx` 자막 큐 조립부(현재 `rec.cueLine ?? 행동구` 로 `text` 를 만드는 지점)를
        `composeCueSubtitleKo(rec, 행동구)` 로 교체한다. 이 한 지점만 바꾼다 —
        `cueTrack.buildCueWindows` 의 타이밍·밀도·`recordId` 조인은 무접촉.

    (4) **손대지 않는 표면(투명 합산 보호)**: `ScoreBreakdownSection`(점수 계산 내역),
        `deductionLabels.ts`, `formatDeductionRecord`. 점수 tally 는 record 1:1 로 남는다.
        묶었다고 개별 수치를 숨기지 않는다는 belle 원칙이 여기서 지켜진다.

    (5) 테스트 증축(같은 파일):
        - 병합 시트에서 `blocks.length` == 멤버 record 수, 각 블록 header 에 자기 `(−X점)`
        - 병합 시트 `goalLine` 이 1개(대표 record 유래), 블록 `cueLine` 에 `목표는` 0회
        - `goalLine` 부재(폴백 문구/legacy) → `null`, 렌더 자리 없음
        - 측정 1 표의 elbow-twist 8건 형상으로: 그룹 3개 유지(어깨/팔/다리),
          어깨·팔 **미병합**(grip_weak) — 도메인 회귀 가드
        - power-spin 형상(shoulder=shoulder_unstable + elbow=shoulder_unstable)으로:
          그룹 2개 → **어깨·팔 1개로 병합**, 배지 번호 병합
        - legacy doc(exerciseId·statusLine·atFrameIdx 전부 부재) → 칩·그룹·시트 산출이
          변경 전과 동일

    (6) 시뮬레이터로 결과 화면을 **직접 열어** 병합 항목 1개·목표 문장 1줄·개별 −X점 노출·
        자막 첫머리를 눈으로 확인한다. `npm run typecheck` 는 렌더 크래시를 잡지 못한다
        ([[verify-ui-on-simulator-before-ota]]). 못 열었으면 SUMMARY 에 "안 봤다"로 적는다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app &amp;&amp; npm run typecheck &amp;&amp; node --test src/lib/__tests__/deductionSheet.test.ts src/lib/__tests__/cueTrack.test.ts src/lib/__tests__/resultSections.test.ts src/lib/__tests__/summarySource.test.ts src/lib/__tests__/screenVocabulary.test.ts src/lib/__tests__/illustrationScene.test.ts</automated>
  </verify>
  <done>
    앱 테스트 전건 통과 + typecheck 0 error.
    `git diff $BASE -- app/src/components/ScoreBreakdownSection.tsx app/src/lib/deductionLabels.ts` 가 **빈 출력**.
    시뮬레이터 렌더 확인 결과(봤다/못 봤다)가 SUMMARY 에 기록됨.
  </done>
</task>

<task type="auto">
  <name>Task 3: 불변식 게이트 — 채점 무접촉 증명 + phrasebook 데이터 정합</name>
  <files>backend/tests/test_phrasebook_cause_grouping.py</files>
  <action>
    (1) `backend/tests/test_phrasebook_cause_grouping.py` 신설. 앱이 이제 `exerciseId` 를
        **표시 병합 키로 의존**하므로, phrasebook 을 나중에 고칠 때 말이 안 되는 병합이
        조용히 생기지 않게 데이터를 게이트한다:
        - 모든 (motion, exerciseId) 묶음의 criterion 을 부위 토큰으로 투영해 **상체(shoulder/arm)와
          하체(leg)를 동시에 걸치는 묶음이 0** 임을 단정 (측정 5 재현).
        - `exerciseId` 는 `backend/data/corrective_exercises.json` 실존 키여야 한다.
        - 부위 투영 표는 앱 `BODY_PART_OF_KEYPOINT` + `CRITERION_REGION_KEYPOINTS` 의
          **테스트 로컬 미러**임을 헤더에 명시한다(`test_terminology_lockstep.py` 선례).
          motion 키는 `entries` 에서 **파생**한다 — 동작명 리터럴 하드코딩 금지.
        - 기존 `test_motion_specific_cueline_goal_first` 핀이 그대로 green 인지 같은
          실행에서 확인(목표-선행 문형은 되돌리지 않았다는 증거).

    (2) 착수 시점에 pytest 기준선을 **먼저** 캡처하고, 종료 시 diff 가 비는지 본다.
        ⚠ `cd backend && .venv/bin/python -m pytest` 는 수집에서 중단돼 0개 실행한다(거짓 통과).
        반드시 아래 형식으로 리포 루트에서 돌린다:
        `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests`
        2026-08-02 기준선 = **59 failed / 3808 passed**. 신규 테스트 수만큼 passed 가
        늘고 **FAILED/ERROR node ID 목록은 완전히 동일**해야 한다.

    (3) 채점 무접촉을 "통과했다"가 아니라 **출력값**으로 증명한다. `BASE=$(git rev-parse HEAD)`
        고정 후 아래가 전부 빈 출력이어야 한다 — 이번 작업에서 백엔드 산출 코드와 승인
        문구 데이터는 **한 글자도** 바뀌지 않는다:
        `backend/shared/python/sunity_shared/analysis/deduction_engine.py`,
        `.../dimensions.py`, `.../ipsf_criteria.py`, `.../fault_zoom.py`,
        `backend/functions/pipeline/app.py`, `backend/data/phrasebook.json`.
  </action>
  <verify>
    <automated>set -o pipefail; cd /Users/kimtaesung/Dev/SunityMotion &amp;&amp; PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    신규 테스트 통과 + FAILED/ERROR node ID diff 가 비어 있음(before/after 파일 경로를
    SUMMARY 에 기록). 위 6개 백엔드 경로의 `git diff $BASE` 가 전부 빈 출력.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 앱 렌더 | 백엔드가 쓴 record 문자열이 화면 문장으로 들어온다 |
| phrasebook.json → 앱 병합 의미 | 승인 fixture 데이터가 이제 **표시 그룹 경계**를 결정한다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-MRG-01 | Tampering | `buildCauseGroupKeys` 가 채점 표면에 새는 것 | mitigate | 병합은 표시 키만 산출. `ScoreBreakdownSection`/`deductionLabels`/`formatDeductionRecord` 무접촉을 `git diff $BASE` 빈 출력으로 게이트 |
| T-MRG-02 | Information disclosure | 묶으면서 개별 감점 크기가 사라짐 | mitigate | 블록 수 == 멤버 record 수 + 각 블록 header 의 `(−X점)` + `numNote` 를 테스트로 단정 |
| T-MRG-03 | Tampering | 미래 phrasebook 편집이 "어깨+다리" 같은 무의미 병합을 만듦 | mitigate | `test_phrasebook_cause_grouping.py` 해부학 span 게이트 |
| T-MRG-04 | Repudiation | `splitGoalClause` 가 음성 mp3 에 없는 말을 자막으로 만듦 | mitigate | T11 — `actionLine` 은 항상 원 `cueLine` 의 부분 문자열 |
| T-MRG-05 | Denial of service | legacy doc(필드 부재)에서 렌더 크래시 | mitigate | T4/T12 + legacy 하위호환 테스트 (병합 미발동 = 오늘과 동일 산출) |
| T-MRG-SC | Tampering | 공급망 | accept | 신규 npm/pip 설치 0 — 이번 변경에 install 태스크가 없다 |
</threat_model>

<verification>
## 자동 게이트

1. `cd app && npm run typecheck` — 0 error
2. `cd app && node --test src/lib/__tests__/deductionSheet.test.ts` (+ Task 2 의 6개 러너)
3. `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests`
   — FAILED/ERROR node ID 목록이 착수 캡처와 **완전히 동일**
4. 채점 무접촉: `BASE=$(git rev-parse HEAD)` 고정 후 백엔드 산출 6경로 + 앱 tally 2경로의
   `git diff $BASE` 가 전부 빈 출력
5. 동작명 분기 0: 변경분 추가 라인에 `ref-` 동작명 리터럴·`9.0` 리터럴 0회

## 재봐야 아는 것 (done 조건 아님)

<human-check>
belle 실기기에서 확인할 것 (OTA 발행 후):
1. 파워스핀 결과 화면 — 어깨 항목과 팔꿈치 항목이 **칩 1개**로 보이는가
2. 그 항목을 열었을 때 **목표 문장 1줄**이 위에 있고, 아래에 감점 2건이 각각
   자기 −X점을 달고 있는가
3. 재생 자막이 **결함을 먼저** 말하는가 (킵업에서 "목표는…" 로 시작하지 않는가)
4. 병합 항목의 문장이 그 장면 설명으로 읽히는가 — 아니면 어느 문장이 어긋났는지
</human-check>

**이 플랜이 증명하지 못하는 것 (미리 적어둔다):**
- belle 이 인용한 정확한 어깨 문자열(`__common__` 폴백)은 stale doc 유래라 이번 수정으로
  재현되지 않는다 (측정 6). 현행 경로는 동작 전용 문구를 낸다.
- 실 doc 에서 어깨·팔꿈치 record 가 **동시에 잡히는 빈도**는 재지 않았다 —
  보유 fixture 4건 중 그 조합을 가진 것은 elbow-twist 뿐이고 거기선 `grip_weak` 라
  의도적으로 병합되지 않는다. power-spin 병합은 **phrasebook 매핑으로는 성립**하지만
  **실 doc 으로는 확인하지 않았다**(그 doc 에 elbow record 가 없다).
- 자막 문구 변경 이후 **음성 mp3 와의 낭독 차이**는 듣지 않았다. mp3 는 분석 시점 합성
  cueLine(목표 포함)이고 자막은 statusLine+행동이다. 음성 기본 off + F-6 무음 미해결
  상태라 현재 관측 불가.
</verification>

<success_criteria>
- 같은 원인(exerciseId 공유)으로 묶인 감점이 칩 1개·마커 1경계·시트 1장으로 보인다
- 묶인 시트에서 각 감점의 −X점을 개별로 읽을 수 있다 (투명 합산 유지)
- 묶인 항목에 목표 문장이 1줄 있고, 없으면 자리도 없다 (fail-closed)
- 재생 자막이 결함 문장으로 시작한다
- `overallScore`·`deductionBreakdown.final`·record 의 `points`/`measuredValue` 무변경
- exerciseId 없는 legacy doc 에서 산출이 변경 전과 동일하고 크래시 0
- 동작명 분기 0 — 규칙이 criterion·exerciseId·부위 투영으로만 키잉된다
- phrasebook.json 무변경 (33-13 belle 승인 문형·테스트 핀 보존)
</success_criteria>

<output>
Create `.planning/quick/260802-mrg-merge-display-and-fix-copy/260802-mrg-SUMMARY.md` when done.
SUMMARY 에 반드시 포함할 것:
- 병합 규칙을 정한 근거 표(측정 1~5)와 **기각한 규칙**(같은 순간 — 40프레임/17프레임/0.67초)
- 채점 무접촉 증거를 "통과했다"가 아니라 **출력값**으로 (git diff 빈 출력 + pytest node ID diff)
- 시뮬레이터로 화면을 열었는지 / 안 열었으면 "안 봤다"
- 미검증 항목 전건 (실 doc 병합 실증·음성/자막 낭독 차이)
</output>
