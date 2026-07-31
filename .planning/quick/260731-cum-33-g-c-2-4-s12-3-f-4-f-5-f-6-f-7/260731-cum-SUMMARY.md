---
phase: quick-260731-cum
plan: 01
subsystem: ui
tags: [react-native, expo, node-test, phrasebook, avaudiosession, expo-audio, expo-video]

requires:
  - phase: quick-260730-l7t
    provides: "§C-1 백엔드 — userVideoSec/refVideoSec 방출, criterion 정중앙 crop"
  - phase: quick-260730-py1
    provides: "§C-2 1단위 — 부위 단위 시트(deductionSheet.buildRegionSheetView), 블록 요소"
  - phase: quick-260730-szk
    provides: "§C-2 2단위 — F-8 마커 게이트, S1 그룹 경계, S3 부위 칩, S19 선/원 분기"
  - phase: quick-260731-2jt
    provides: "§C-2 3단위 — S13 일러스트 장면일치 fail-closed, S23 illu-float"
provides:
  - "S12 화면 어휘 게이트 — app/src 전수 스캔 상시 테스트 + 렌더 표면 16곳 교체"
  - "F-4 헤드라인 조립 제거(백엔드 뿌리) + 길이·조립 강등(앱 2겹)"
  - "F-5 게이지 기호 라벨(지금/목표) — 마커와 단일 스타일 소스"
  - "F-7 펼침/접기 앵커 = 요약 카드 자신 (pickExpandAnchorY 순수 함수)"
  - "F-6 소스 증거표 + 후보 순위표 + belle 실기기 분기 판별 절차 (원인 미상 유지)"
affects: [33-result-trust-recovery, §C-4-pod, belle-확인-③]

tech-stack:
  added: []
  patterns:
    - "화면 어휘 게이트 = 백엔드 단일 출처(phrasebook.json _meta) 를 앱 테스트가 직접 읽어 전수 스캔"
    - "헤드라인 렌더 안전 = 데이터 층 강등(승인 상수) + 렌더 층 numberOfLines 2겹"
    - "스크롤 앵커 선택 = 순수 함수(pickExpandAnchorY) 로 격리, 폴백 체인 보존"

key-files:
  created:
    - app/src/lib/__tests__/screenVocabulary.test.ts
  modified:
    - app/src/lib/summarySource.ts
    - app/src/lib/resultSections.ts
    - app/src/components/GoalGaugeBar.tsx
    - app/src/components/SummaryCard.tsx
    - app/src/lib/audioCue.ts
    - app/src/app/analysis/result.tsx
    - backend/shared/python/sunity_shared/analysis/phrasebook.py
    - backend/tests/phase33/test_phrasebook_motion_specific.py

key-decisions:
  - "Q-22: 앱 길이 게이트가 백엔드 잔여 상수 2개(43자·40자)도 강등한다 — 절삭보다 승인 상수가 낫다"
  - "Q-23: F-6 세션 경합은 실증됐으나 카테고리는 양쪽 .playback 으로 수렴 — 무음 축은 미설명, PASS 주장 금지"
  - "Q-24: F-6 최상위 후보 = speakCue 3중 false 게이트(설정 off / cueId 미조인 / 캐시 미스). 판별자 = 큐 시점에 영상이 멈추는가"

patterns-established:
  - "게이트 제외는 파일→필드 레지스트리 + 소비자 0 grep 증거 (파일 통째 면제 금지)"
  - "마커·범례 스와치는 MARKER_FILL 단일 소스에서 파생 (라벨이 거짓이 되지 않게)"

requirements-completed: [S12, F-4, F-5, F-7]

duration: ~75min
completed: 2026-07-31
---

# 33-G §C-2 앱 4단위 (S12 · F-4 · F-5 · F-6 · F-7) Summary

**S12 를 3곳 패치가 아니라 앱 전수 스캔 게이트로 닫고(16곳/7파일), F-4 의 근본원인이
백엔드 헤드라인 조립임을 실증해 뿌리+앱 2겹으로 막고, F-5 기호에 이름을, F-7 앵커를
요약 카드 자신으로 옮겼다. F-6 은 실기기 없이 증명 불가라 원인 미상으로 남기고 증거표·
후보 순위·belle 분기 절차를 산출물로 냈다 — 어디에도 PASS 로 쓰지 않았다.**

## Performance

- **Duration:** ~75분
- **Tasks:** 3/3
- **Files modified:** 22 (신설 1 · 삭제 1)

## Task Commits

1. **Task 1: S12 화면 어휘 게이트 — 렌더 표면 전수 + 게이트 테스트** — `747e756` (fix)
2. **Task 2: F-4 헤드라인 조립 제거·길이 통제 + F-7 자세히보기 전환** — `ac19aa3` (fix)
3. **Task 3: F-5 게이지 기호 라벨 + F-6 실기기 무음 재조사** — `ad9210a` (fix)

## 검증 결과

| 게이트 | 결과 |
|---|---|
| `screenVocabulary.test.ts` (신설) | **5 pass** — 위반 0 / 스캔 72파일 |
| `deductionSheet.test.ts` | 35 pass (라벨 기대 1줄 갱신, 로직 기대 무변경) |
| `summarySource.test.ts` | **14 pass** (11 → +3 F-4 케이스) |
| `resultSections.test.ts` | **6 pass** (5 → +1 F-7 4케이스) |
| 나머지 앱 테스트 (cueTrack/focusShape/gaugeGeometry/illustrationScene/manualOffset/visualCards) | 61 pass, 회귀 0 |
| `backend/tests` 전체 | **회귀 0** — FAILED/ERROR node ID **42건이 baseline(`8065e53`)과 완전 동일**, 3764 passed |
| `backend/tests/phase32` + `phase33` | 313 pass |
| `npm run typecheck` | clean |
| 앱 금지어 raw grep (제외 레지스트리·주석 밖) | **0줄** |
| F-4/F-7 grep 게이트 | 조립 보간 0 / `numberOfLines={2}` / `pickExpandAnchorY` / `anchor:summaryCard` 전건 존재 |
| F-5/F-6 grep 게이트 | `지금`·`목표` 존재 / hex 리터럴 0 / `{goalHint}` 0 / `expo-av` 0 |
| 채점 무접촉 (D-44) | `analysis/` 하위 diff = `phrasebook.py` **1개뿐**(카피 조립). 점수·산식·임계·`judging_data` diff **0** |
| 배포 (D-45) | OTA·EAS **0** |
| 신규 패키지 | **0** |

**백엔드 회귀 판정 방법:** `git stash` 금지라 baseline 커밋 `8065e53` 을 `git archive`
로 스크래치패드에 풀어 같은 pytest 를 돌리고 FAILED/ERROR node ID 를 정렬 비교했다
(`diff` = 빈 출력). 42건은 이 플랜과 무관한 pre-existing(geminid wiring·spike smoke 등).
`test_pole_detector.py`·`test_rtmw_133_to_coco17_adapter.py` 2건은 baseline 에서도
collection error 라 양쪽 동일하게 제외했다.

---

## S12 렌더 표면 전수

33-G 는 잔재를 **3곳**으로 적었다. 게이트를 먼저 만들어 스캔하니 **7파일 16곳**이었다
(Q-1 이 옳았음이 수치로 확인됨). 게이트 최초 실행 출력:

```
화면 어휘 게이트 위반 16건 (스캔 72파일):
  components/DimensionDetailModal.tsx:94,141,147,152 : 완성도 ×4
  components/InjuryRiskSection.tsx:59                : 신전
  data/correctiveExercises.ts:57                     : 신전
  data/corrective_exercises.json:52~56               : 신전 ×5
  lib/deductionLabels.ts:479,480                     : 신전 ×2
  lib/terminologyMap.ts:14                           : 완성도
  app/analysis/loading.tsx:68,72                     : 완성도 ×2
```

### 교체 내역 (문장 길이 같거나 짧게 — D-05)

| 파일 | 전 | 후 |
|---|---|---|
| `deductionLabels.ts:479` | 다리 신전(펴짐) | **다리 펴기** |
| `deductionLabels.ts:480` | 팔 신전(펴짐) | **팔 펴기** |
| `terminologyMap.ts:14` + `backend/data/terminology_map.json` | …만드는 라인의 완성도 | **…만드는 라인** |
| `loading.tsx:68` | 회전 속도보다 라인의 완성도가 | **회전 속도보다 라인이 곧은지가** |
| `loading.tsx:72` | 작은 각도 차이가 완성도의 차이를 | **작은 각도 차이가 자세의 차이를** |
| `InjuryRiskSection.tsx:59` | 무릎·팔꿈치 과신전 가능성 | **무릎·팔꿈치 과하게 젖혀짐** |
| `correctiveExercises.ts:57` | 다리 신전 강화 | **다리 펴기 강화** |
| `corrective_exercises.json` purpose ×5 | 다리 신전 근력 기반 / 단측 다리 신전 강화 / 발목/종아리 신전 마무리 / 능동 다리 신전 가동 / 측면 다리 신전 근력 | **다리 펴는 근력 기반 / 한쪽 다리 펴기 강화 / 발목·종아리 펴기 마무리 / 능동 다리 펴기 가동 / 측면 다리 펴는 근력** |
| `DimensionDetailModal.tsx` (완성도 ×4) | — | **파일 삭제** (Q-3) |

미러 정합: `corrective_exercises.json` 은 app/backend **byte-for-byte 동일**(diff 0 확인),
`terminology_map.json` 도 앱 미러와 함께 수정 → phase13·phase32 lockstep 테스트 통과.
`sourceRef` 인용값은 무접촉.

### 제외 항목 — 소비자 0 grep 증거

| 파일:필드 | 판정 | 증거 |
|---|---|---|
| `lib/illustrationScene.ts` `provenance` (신전 ×4) | **유지 + 게이트 제외** (Q-5) | export 3개(`sceneCoversParts`/`illustrationMotionForPart`/`hasIllustrationFor`) 어느 것도 이 필드를 반환하지 않음. `grep -rn "\.provenance\|provenance:" app/src` 결과 = `illustrationScene.ts` 자신 + `illustrationScene.test.ts` 3줄(근거 문장 **품질 검사**)뿐, 렌더 컴포넌트 0. 33-14 검수 증거 원문이라 바꾸면 증거가 훼손된다 |
| `types/analysis.ts:114,181` · `DefectIllustration.tsx:12` · `deductionSheet.ts:125` | 대상 밖 | **주석**. 게이트가 `.ts/.tsx` 를 주석 제거 후 검사(줄 번호 보존 스트리퍼 + 단위 테스트 1건) |
| `contract` 필드 `ipsfAnchor` (백엔드 값에 '신전' 포함) | 대상 밖 | `grep -rn "ipsfAnchor" app/src` = 타입 선언 1 + 주석 1 + 테스트 픽스처 2. **`<Text>` 도달 0** |
| `backend/judging_data/**` `source_ref` · `motion_ipsf_map.json` `sourceNote` | 대상 밖 | 채점 내부 provenance. `rendered_copy_strings()` 스코프 밖이고 앱이 읽지 않음 |

`deductionSheet.ts:125` 의 JSDoc 예시 문자열은 게이트 대상이 아니지만 **낡은 라벨을
인용**하고 있어 새 라벨로 갱신했다(문서 정확성, 렌더 영향 0).

### 게이트 설계 (재발 차단축)

- 금지어 = `backend/data/phrasebook.json` `_meta.screenVocabularyGate.words` **직접 읽기**.
  앱에 목록 리터럴 0 (Q-6 — 복제하면 다음 라운드에 drift).
- 스캔 = `app/src/**/*.{ts,tsx}` + `app/src/**/*.json`, `__tests__` 제외. json 은 문자열
  **값**만(키 제외). sanity 가드 2개(파일 ≥50 · 금지어 ≥4)로 glob 붕괴 시 vacuous pass 차단.
- 제외는 **파일→필드** 레지스트리로만. 파일 통째 면제 불가 — 전용 단위 테스트가
  "지정 필드만 면제되고 옆 필드는 여전히 걸린다"를 고정한다.

### 백엔드 뿌리 차단 (Q-7)

`test_screen_vocabulary_gate` 의 스코프는 phrasebook fixture 3섹션(`entries`/
`safetyEntries`/`failClosed`)뿐이었다. **'완성도' 가 `terminology_map.json` 에 살아남은
구조적 이유가 이 누락이다.** `phrasebook.rendered_copy_strings()`(terminology terms +
summaryPraise 헤드라인 상수 포함)를 같은 게이트에 덧붙였다. 실증:

```
rendered_copy_strings count = 425
  terms.line in scope: True        ← 확장 후
  구 스코프(fixture 3섹션)에 terms.line 포함? -> False   ← 누락 실증
```

경로 정보가 있는 기존 fixture walk 는 그대로 두고 옆에 더했다(진단 문구 보존).

### 10동작 일반화 (single-motion-fixation 금지)

`grep -rn "power-spin\|kip-up" app/src --include='*.ts' --include='*.tsx'` = **7건**.
내역: 주석 3(`analysis.ts:679`, `ScoreBreakdownSection.tsx:3`, `PoseCompareViewer.tsx:32`)
+ **데이터 맵 키 4**(`DefectIllustration.tsx:41-42` 에셋 레지스트리, `illustrationScene.ts:79,84`
장면 레지스트리 — 33-14 산출). **동작별 카피 파일 0.** 이번에 바꾼 문자열은 전부
criterion 키 맵(`CRITERION_LABEL_KO`) · defect 키 맵(`DEFECT_TITLES`, corrective defects) ·
차원 키 맵(`TERMINOLOGY_MAP`) · safetyFlagType 맵(`FLAG_COPY`) · 동작 무관 팁 배열
(`POLE_TIPS`)이라 **동작 분기가 존재하지 않는다**. 게이트가 `app/src` 전수를 스캔해 0 hit
인 것이 곧 10동작 일반화 증거다.

---

## F-4 지목 위치 정정

**33-G 는 `result.tsx:475-505 계열`(요약 카피 빌더)을 지목했으나 근본원인은 앱이 아니라
백엔드다.**

- `phrasebook.py:179`(구) `_PRAISE_HEADLINE_CLEAN_DIMENSION_PREFIX = "감점 없이 통과한 항목이 있어요 — "`
- `phrasebook.py:223`(구) `"headline": f"{_PRAISE_HEADLINE_CLEAN_DIMENSION_PREFIX}'{term}'"`

→ 산출물 `"감점 없이 통과한 항목이 있어요 — '동작의 전체 흐름이 기준 자세와 얼마나 나란히
이어지는지'"` = **약 50자**. 이것이 `SummaryCard.praiseHeadline`(`typography.bodyLg` 24/700)
한 곳에 그대로 들어가 belle 이 본 상자 이탈이 됐다. `result.tsx` 는 `praise` 를 전달만 한다
(렌더 지점은 `SummaryCard.tsx:68-70` 단 1곳 — grep 확인).

### 수리 2겹

| 겹 | 위치 | 내용 |
|---|---|---|
| 뿌리 (새 doc) | `phrasebook.py` | 조립 제거 → 완성 문장 1개 `_PRAISE_HEADLINE_CLEAN_DIMENSION = "감점 없이 통과한 항목이 있어요"`(17자). 이름에서 `_PREFIX` 제거 = 조립 의도 삭제. `clean_dimensions` 루프·terminology 조회는 **유지**(D-06 근거 없는 칭찬 금지 게이트, Q-13) |
| 데이터 (기존 doc) | `summarySource.selectPraise` | doc headline 이 **조립형**(`\s—\s'…'$`) **또는** 길이 > 24 면 같은 source 의 **승인 로컬 상수**로 강등. `source`/`evidenceValue`/`evidenceUnit` 통과 |
| 렌더 (하드 스톱) | `SummaryCard.praiseHeadline` | `numberOfLines={2}` |

잃는 정보(어느 차원이 깨끗했나)는 부위 상세 시트의 용어줄(`DeductionDetailSheet` `terminologyPlain`)이
이미 렌더한다 — 같은 정보를 두 곳에서 말하지 않는다(D-05 ①, Q-12).

### 승인 상수 글자 수 대 상한 24 (T-33G4-05 — 정상 카피 절삭 0 증명)

| 상수 | 글자 수 | 상한 대비 |
|---|---|---|
| `PRAISE_HEADLINE.mission_improved` "지난번보다 확실히 나아졌어요" | 15 | 여유 9 |
| `PRAISE_HEADLINE.clean_dimension` "이 부분은 기준에 맞게 잘 해냈어요" | 19 | 여유 5 |
| `PRAISE_HEADLINE.criteria_met` "측정된 자세에서 기본 기준은 지켰어요" | 20 | 여유 4 |
| `SummaryCard.HONEST_NO_PRAISE` "측정된 잘한 점을 아직 찾지 못했어요" | 20 | 여유 4 |
| (참고) 구 조립 산출물 | ~50 | **초과 — 강등 대상** |

전부 20자 이하 = bodyLg 2줄 안에서 **절대 절삭되지 않는다**. 회귀 가드 테스트
(Test 8c)가 세 source 를 실제로 파생시켜 상한·무수치를 상시 고정한다.

---

## F-7 — 앵커를 요약 카드 자신으로

**구 거동**(`result.tsx:2130` 계열): 펼치는 즉시 `anchor:scoreGauge` → `anchor:scoreBreakdown`
순으로 **펼치기 전에 측정된** y 로 점프. 요약 카드에서 한참 아래라 belle 이 "확 내려감"
으로 읽었고, 그 y 자체도 stale(펼침이 레이아웃을 바꾸는데 갱신 전 값). 접기는 최상단 복귀.

**신 거동**: `pickExpandAnchorY(cardYRef.current, ['anchor:summaryCard', ...DETAIL_ANCHOR_KEYS], 12)`
를 **펼침·접기 양쪽**에서 사용. 요약 카드를 감싸는 스타일 없는 `View` 1겹이 `onLayout` 으로
`anchor:summaryCard` 를 기록한다(content 컨테이너의 flex 자식 수가 1개 그대로라 `gap: 14`
영향 0). 요약 카드 y 는 펼침으로 **변하지 않으므로** layout 대기가 불필요하고 stale-y 경합도
함께 사라진다. 폴백 체인(기존 상세 앵커 → `scrollToEnd`/`y:0`)은 그대로 뒤에 붙였다(Q-19).

무회귀: `jumpToRecordKey`·`jumpToQuestion`·`jumpToCollapsedList`·`DETAIL_ANCHOR_KEYS` 기록
지점 무변경. `SummaryCard` 의 `expanded` prop·'접기' 라벨·chevron 방향(33-15 D-17, 이미
PASS) 무접촉.

---

## F-5 — 기호에 이름

`legendRow` 의 `goalHint` 문장('목표까지 줄이기')을 빼고 범례 2칸을 뒀다:
`[검은 점] 지금` · `[브랜드 세로선] 목표`.

- 스와치 채움은 `MARKER_FILL` **단일 소스**에서 마커와 함께 파생(Q-16). 기하(위치·크기)만
  다르고 "무엇으로 채워졌는가"는 같다 — 스와치가 마커와 어긋나면 라벨이 오히려 거짓이 된다.
- **문장 수 순감**: 문장 −1, 단어 라벨 +2 (D-05 "새로 추가되는 문장 최대 1줄" 충족).
- 방향 정보는 기하(점이 선의 좌/우) + a11y 라벨(`directionHint`, 문구 원문 유지)에 남겼다.
- 허용 오차 밴드(`tolBand`)에는 라벨 미부착 — belle 이 지목한 건 두 기호이고, 요소를 늘리면
  D-07 ⑥(화면이 전보다 단순해야)에 어긋난다.
- 수치 배지(`badgePill`)·`computeGaugeGeometry`·`null` 폴백 무변경. hex 리터럴 0(토큰만).

---

## F-6 재조사

> **판정: FAIL 유지 — 원인 미상.** 실기기가 없어 증명이 불가능하므로 해결됐다고 주장하지
> 않는다. 아래는 **사실(파일:줄)** 과 **추론(후보)** 을 분리한 기록이다.

버전: `expo-audio 1.1.1` / `expo-video 3.0.16` (둘 다 `package.json` 선언과 일치).

### (1) 소스 증거표 — 사실만

| # | 파일:줄 | 사실 |
|---|---|---|
| E1 | `app/src/lib/audioCue.ts:43` | `let enabled = false` — 오디오 큐 **기본 off**(학원 소음). `hydrate` 가 AsyncStorage 값을 읽어 덮는다 |
| E2 | `audioCue.ts:81-83` | `hydrate()` 는 `hydrated` 가드로 **앱 수명당 1회**만 실효 |
| E3 | `audioCue.ts:105-110`(신) | 오디오 모드 선언 = `setAudioModeAsync({playsInSilentMode:true, interruptionMode:'duckOthers'})`. **fire-and-forget** — 반환 promise 를 검사하지 않고 `.catch` 로 삼킨다. 실기기 실패 여부를 알 방법이 코드에 없다 |
| E4 | `audioCue.ts:110-119` | `setAudioCueEnabled(next)` 는 `hydrated = true` 로 세우지만 **오디오 모드를 선언하지 않는다.** `hydrate()` 보다 먼저 호출되면 그 세션 동안 선언이 영영 없다 |
| E5 | `grep -rn "setIsAudioActiveAsync" app/src` = **0건** | 앱은 오디오 세션을 명시적으로 활성화하지 않는다. 활성화는 expo-audio 의 `play()` 에 위임 |
| E6 | `audioCue.ts:169-193` | `speakCue` 는 소리를 내기 전에 **false 를 반환하는 게이트 3개**를 통과해야 한다: ① `!enabled` ② `cueId == null` ③ `urlCache` 미스(prefetch 실패/미조인) |
| E7 | `audioCue.ts:178` `createAudioPlayer(url)` + `expo-audio/build/ExpoAudio.js:299` | 옵션 미전달 → `keepAudioSessionActive = false`(기본값). 문서: "sound effects that should not interfere with ongoing video playback" 용도로 `true` 를 권함 |
| E8 | `expo-audio/ios/AudioModule.swift:544-582` | `playsInSilentMode:true` → `category = .playback`(:552) + `.duckOthers`(:558-559). `setCategory(category, options:)` 는 **mode 인자 없음** → mode = `.default`(:580) |
| E9 | `AudioModule.swift:173-177` → `:584-586` | 오디오 `play()` 마다 `activateSession()` = `setActive(true)` |
| E10 | `AudioModule.swift:199-204` → `:588-603` | `pause()` 및 `onPlaybackComplete`(:96-100)에서 `keepAudioSessionActive=false` 면 **0.1초 뒤** `setActive(false, .notifyOthersOnDeactivation)` |
| E11 | `app/src/components/VideoCompare.tsx:378, 383` | 두 비디오 플레이어는 **`muted = true`** |
| E12 | `expo-video/ios/VideoPlayer.swift:311` | `onIsPlayingChanged` — 재생 상태가 바뀔 **때마다** `VideoManager.shared.setAppropriateAudioSessionOrWarn()` |
| E13 | `expo-video/ios/VideoManager.swift:105-111` | 공유 세션의 category/mode/options 중 하나라도 다르면 **`setCategory(.playback, mode: .moviePlayback, options:)` 로 덮어쓴다.** E8 직후에는 `mode(.default) != .moviePlayback` 이 **항상 참**이라 이 덮어쓰기가 매번 발생 |
| E14 | `VideoManager.swift:78-80` | `isOutputtingAudio = 플레이어가 재생 중 && !isMuted`. E11 때문에 **항상 false** |
| E15 | `VideoManager.swift:93-103` | 우리 큐 시점(두 영상 pause) 계산 결과 = `.mixWithOthers` **삽입** + `.duckOthers` **제거**(expo-audio 가 넣은 옵션이 지워진다) |
| E16 | `VideoManager.swift:114-120` | `setActive(true)` 는 `isOutputtingAudio \|\| doNotMixOverride` 일 때만. 큐 시점(재생 플레이어 0 → `findAudioMixingMode()` = nil)에는 **둘 다 false → 활성화하지 않는다** |
| E17 | `VideoCompare.tsx:691-707` / `:723-729` | 큐 1회당 `pause()` **2회**(발화 직후) + `play()` **2회**(발화 종료). E12 에 의해 큐 1회당 최대 **4번**의 공유 세션 재작성이 **발화 직전·직후에** 일어난다 |

**증거가 반증하는 것(중요):** 두 작성자 모두 카테고리를 **`.playback` 으로 수렴**시킨다
(E8 · E13). `.playback` 은 무음 스위치를 무시하는 카테고리다. 따라서 **세션 경합만으로는
"무음 스위치 때문에 안 들린다"가 설명되지 않는다.** §9 유력 가설(`playsInSilentMode` 미지정)이
이미 반증된 데 이어, 그 후속 가설도 부분적으로만 성립한다.

### (2) 후보 순위표 — 추론 (증거로 뒷받침되는 것만)

| 순위 | 후보 | 근거(파일:줄) | 시뮬에서 관측 불가한 이유 | 실기기에서 참/거짓을 만드는 관찰 |
|---|---|---|---|---|
| **1** | **발화가 애초에 시작되지 않았다** — `speakCue` 3중 게이트 중 하나에서 false. ① 오디오 큐 토글이 **off**(기본값) ② `cue.recordId` 미조인 ③ presigned URL prefetch 실패(캐시 미스) | E1·E6·E4 | 시뮬 검증자는 토글을 켜고 테스트했다. off 상태·네트워크 실패는 재현 조건이 다르다 | **큐 시점에 영상이 멈추는가.** `started=true` 일 때만 pause + "잠시 멈춤" 라벨이 뜬다(`VideoCompare.tsx:692-699`). **안 멈추면 후보 1 확정**(소리 이전의 문제), **멈추는데 소리만 없으면 후보 1 기각** |
| **2** | 세션 쓰기 순서 경합 — 우리의 1회성 모드 선언이 큐마다 4번 일어나는 expo-video 재작성에 덮인다. 특히 큐 시점에 `.duckOthers` 제거 + `.mixWithOthers` 삽입 + **`setActive(true)` 미호출**(E16) | E2·E12·E13·E15·E16·E17 | 시뮬은 무음 스위치가 없고 세션 라우팅이 단순해 카테고리 변화가 가청 차이를 만들지 않는다 | 무음 스위치 **끈 상태(벨 모드)** 에서도 여전히 안 들리면 후보 2 쪽(카테고리·활성화 축), 벨 모드에서 들리면 무음 스위치 축 = 후보 3 |
| **3** | 무음 스위치 축 잔존 — 모드 선언이 애초에 적용되지 않았을 때(E4 경로: 토글을 먼저 누른 세션) 앱 기본 카테고리(`.soloAmbient`)로 재생 → 무음 스위치가 막는다 | E4·E8 | 시뮬레이터에는 무음 스위치 자체가 없다 | 무음 스위치 끄면 들리고 켜면 안 들리면 **후보 3 확정** |
| **4** | 세션 비활성화 churn — `keepAudioSessionActive=false` 라 큐가 끝날 때마다 0.1초 뒤 `setActive(false)`; 다음 큐의 `setActive(true)` 와 expo-video 의 비동기 `managerQueue` 재작성이 교차 | E7·E10·E12 | 타이밍 경합이고 시뮬은 오디오 스택 지연 특성이 다르다 | **첫 큐만 들리고 두 번째부터 안 들리는가** — 그렇다면 후보 4 |
| **5** | 출력 라우팅·볼륨 — 미디어 볼륨 0, 통화 라우팅, 블루투스 잔류 연결 | (앱 코드 밖) | 시뮬은 호스트 오디오를 그대로 쓴다 | 이어폰 연결 시 들리면 라우팅 축 |

**근거 없는 추측은 쓰지 않았다.** 예컨대 "mp3 파일이 깨졌다"는 코드 증거가 없어 넣지 않았다
(`coachAudio.status='failed'` 는 후보 1-③에 이미 포함).

### (3) 코드 변경 — 후보 2 완화 1건 (미확정)

Q-21 조건을 만족해 **1건만** 적용했다.

- **무엇:** `speakCue` 가 `player.play()` 직전에 오디오 모드를 **다시 선언**한다
  (`declareAudioMode()`). 종전엔 앱 수명당 1회(E2).
- **왜 허용 범위인가:** E12·E13·E15·E16·E17 이 **세션 쓰기 순서 경합을 파일:줄로 실증**한다
  (플랜 Task 3 (4) 조건).
- **안전 조건 충족:**
  ① 기존 성공 경로의 **상위집합** — 같은 값을 더 자주 선언할 뿐, 시뮬에서 관측 가능한 변화 0.
  ② `speakCue` **반환 semantics 불변** — `declareAudioMode` 는 자체 `try/catch` 로 동기 throw
  까지 삼켜 `speakCue` 의 catch 에 도달하지 않는다.
  ③ 실패는 기존과 동일하게 조용히 삼킨다.
- **되돌리는 방법 (1줄):** `app/src/lib/audioCue.ts` 의 `speakCue` 안 `declareAudioMode();`
  **한 줄을 삭제**한다 (hydrate 쪽 호출은 종전 동작 그대로라 남긴다).
- **라벨: `후보(미확정)`.** 이것이 원인이라는 증명은 없다 — 위 "증거가 반증하는 것" 참조.

적용하지 **않은** 후보 (1건 한도 + 상위집합 아님):
`createAudioPlayer(url, { keepAudioSessionActive: true })`(E7). 문서상 우리 용도에 맞지만
세션 **수명주기를 바꾸는** 변경이라 상위집합이 아니고, 다른 앱 오디오 ducking 이 계속
유지될 수 있다. 후보 4 가 실기기에서 살아남으면 다음 라운드 1순위.

---

## F-6 실기기 판별 절차 (belle)

**로그 없이 belle 이 혼자 할 수 있는 분기 절차.** 각 결과가 어느 후보를 확정/기각하는지
화살표로 적었다.

**사전 준비 (필수)**
1. 결과 화면에서 **LogBox 경고 배너를 먼저 닫는다** — 배너 우측 X. 배너가 재생 버튼 탭을
   가로채서, 안 닫으면 "재생이 안 눌린다"가 무음으로 오인된다(1~3단위 실측).
2. 동작 비교 카드에서 **오디오 큐 토글을 켠다**(기본 off — 이 확인 자체가 후보 1-① 판별).
   토글이 이미 켜져 있었는지 **기억해서 알려주세요**: 꺼져 있었다면 그것이 곧 원인 후보다.

**분기 A — 소리 이전의 문제인가 (후보 1 판별, 가장 먼저)**
- 재생 → 자막이 뜨는 순간 **영상이 멈추고 "잠시 멈춤" 라벨이 보이는가?**
  - **안 멈춘다** → **후보 1 확정.** 발화가 시작조차 안 됐다(토글 off / 음성 파일 미조인 /
    URL 발급 실패). 소리 문제가 아니다. → 분기 B~D 불필요. 여기서 멈추고 알려주세요.
  - **멈추는데 소리만 없다** → 후보 1 기각. 분기 B 로.

**분기 B — 무음 스위치 축인가 (후보 3 vs 2)**
- 기기 측면 **무음 스위치를 끄고(벨 모드)** 같은 지점 재생.
  - **소리가 난다** → **후보 3 확정**(무음 모드 선언 미적용). → 분기 C·D 불필요.
  - **여전히 무음** → 후보 3 기각(카테고리·활성화 축 = 후보 2). 분기 C 로.

**분기 C — 볼륨·라우팅인가 (후보 5)**
1. 무음 ON 상태 + **미디어 볼륨 최대**(영상 재생 중 볼륨 버튼을 눌러 "미디어" 슬라이더가
   뜨는지 확인 — "벨소리" 슬라이더면 우리 세션이 잡히지 않은 것 = 후보 2 보강 증거) → 재생.
2. **유선/블루투스 이어폰 연결** 후 재생.
   - 이어폰에서만 들린다 → **후보 5(라우팅) 확정.**
   - 둘 다 무음 → 후보 5 기각. 분기 D 로.

**분기 D — 세션이 잡히긴 하는가 + 첫 큐만인가 (후보 2 vs 4)**
1. **음악 앱(애플뮤직/유튜브뮤직)을 재생한 채로** 앱에 들어와 동작 비교를 재생.
   - 큐 시점에 **음악 볼륨이 잠깐 작아진다** → 우리 세션이 활성화되고 `duckOthers` 가
     먹고 있다 = **세션은 잡혔는데 우리 소리만 안 난다**(후보 2 강화 — 다음 라운드는
     플레이어/볼륨 축으로).
   - 음악이 **전혀 안 줄어든다** → 우리 세션이 활성화되지 않았다(**후보 2 확정** —
     E16 의 `setActive` 미호출 경로).
2. 큐가 2개 이상인 영상에서 **첫 번째 큐만 들리고 두 번째부터 안 들리는가?**
   - 그렇다 → **후보 4 확정**(세션 비활성화 churn).

**알려줄 것:** 분기 A/B/C/D 각각의 답 한 줄 + 오디오 토글이 원래 켜져 있었는지.
그것만 있으면 다음 라운드에서 후보를 하나로 좁힐 수 있다.

**F-6 은 시뮬레이터 검증 대상이 아니다** — 무음 스위치·실기기 오디오 라우팅이 없다.
belle 확인 ③ 로 넘긴다.

---

## 시뮬 확인 요청 (오케스트레이터)

실행자 도구에 시뮬레이터가 없다. **33-G 표는 미갱신** — 아래 결과로 오케스트레이터가 판정한다.
공통 준비: **결과 화면 진입 후 LogBox 경고 배너의 X 를 먼저 닫을 것**(배너가 하단 컨트롤
탭을 가로챈다 — 1~3단위 실측). Metro 디버그 빌드, OTA 미발행(D-45).

| # | 항목 | 도달 경로 | 승인 요소 | PASS 조건 |
|---|---|---|---|---|
| V1 | **F-4 헤드라인** | 기록 탭 → **감점 0(100점) doc** 결과 화면 → 요약 카드 최상단 | 7R 요약 카드 헤드라인(짧은 한 문장) | 헤드라인에 **따옴표·` — ` 조립 꼬리 0**, 카드 테두리 안에서 **잘림·넘침 0**(말줄임표 `…` 도 없어야 함 — 있으면 승인 상수가 2줄을 넘은 것 = 회귀). 기대 문장 = "이 부분은 기준에 맞게 잘 해냈어요" 또는 "측정된 자세에서 기본 기준은 지켰어요" 또는 "지난번보다 확실히 나아졌어요" 중 하나 |
| V2 | **F-4 나머지 doc** | 렌더 가능한 doc **4건 전부** 요약 카드 | 동일 | 4건 모두 헤드라인 2줄 이내·조립 꼬리 0. **어느 doc 이 어느 문장을 보이는지 캡처해 주세요** — 백엔드 잔여 상수 강등(Q-22)이 실제로 어떤 doc 에 걸리는지 확인점 |
| V3 | **F-5 게이지 범례** | 파워스핀·킵업 doc 결과 화면 → "오늘 고칠 것" 카드(펼침 불필요, `result.tsx:2348`) → 목표 게이지 | 게이지 하단 범례 | **검은 점 + "지금"**, **브랜드 세로선 + "목표"** 두 칸이 보이고, 스와치가 트랙 위 마커와 **같은 색·모양**. '목표까지 줄이기' 문장 **사라짐**. 수치 배지("94°→71°")는 그대로 |
| V4 | **F-5 폴백 무회귀** | 게이지가 안 그려지는 카드(규칙 상수 부재 → 배지+텍스트 폴백) | — | 폴백 행이 종전과 동일(범례가 폴백에 새어 들어가지 않음) |
| V5 | **F-7 펼침** | 결과 화면 요약 카드 → "자세히 보기" 탭 | — | **탭 직전/직후 캡처 2장.** 요약 카드가 **화면에 그대로 남아** 있고 그 아래에 상세가 나타난다. 화면이 통째로 아래로 튀지 않는다 |
| V6 | **F-7 접기** | V5 상태에서 "접기" 탭 | — | **캡처 2장.** 최상단으로 튀지 않고 요약 카드가 같은 자리에 남는다. 라벨이 '자세히 보기'로 되돌아온다(33-15 무회귀) |
| V7 | **S12 시트 용어줄** | 감점 있는 doc → 부위 칩 탭 → 부위 상세 시트 | 시트 용어줄(`terminologyPlain`) | "…만드는 라인" — **'완성도' 미출현** |
| V8 | **S12 보완운동** | 결과 화면 → 보완 운동 섹션(개인화 추천 + 라이브러리) | — | 제목 "다리 펴기 강화", 운동 purpose 5건 모두 **'신전' 미출현** |
| V9 | **S12 부상위험** | safetyFlag `joint_hyperextension` 있는 doc → 위험 섹션 | — | "무릎·팔꿈치 과하게 젖혀짐" — **'과신전' 미출현** |
| V10 | **S12 로딩 팁** | 분석 로딩 화면(팁 6초 로테이션, 12개 중 2개가 대상) | — | "…라인이 곧은지가 더 중요해요" / "…자세의 차이를 만듭니다" |
| V11 | **1~3단위 회귀 0** | 같은 doc 들 | — | **S1**(그룹 경계+번호 배지, 개별 원 0) · **S3**(부위 칩 = 감점 부위 수) · **S6/S7**(부위 시트 = 블록 N개, 번호 헤더·basis·method·numnote) · **F-8**(토글 OFF = 마커 0, 안 보이는 탭 0) · **S13**(어깨 시트 일러스트 미부착 / 다리 시트 부착) 전건 종전과 동일 |
| V12 | **LogBox 신규 경고 0** | Metro stdout 캡처 | — | `expo-video allowsFullscreen` deprecation **2건만**(기존·무관). `Animated`·`Text` 계열 **신규 경고 0** |
| V13 | **크래시 0** | 위 전 경로 | — | 시트 열림/닫힘·펼침/접기 반복 시 크래시 0. 요약 카드 래퍼 View 추가로 **간격이 벌어지지 않았는지** 눈으로 확인(`gap: 14` 유지) |

**F-6 은 시뮬 검증 대상이 아님** — belle 실기기 확인 ③ (위 판별 절차).
**S19·S2·S23·S18·S22 는 재생 중에만 보이므로 시뮬 검증 불가**(`.continue-here.md` 실측) — 실기기.

---

## 33-G 재채점 제안 (표 미갱신 — 제안만)

| 행 | 현재 | 제안 | 근거 |
|---|---|---|---|
| **S12** | PARTIAL | **PASS 제안** (조건: V7~V10 렌더 확인) | 33-G 가 적은 3곳이 아니라 **7파일 16곳** 전건 교체 + `screenVocabulary.test.ts` 가 `app/src` 72파일을 상시 스캔해 0 hit. 백엔드 게이트도 `rendered_copy_strings()` 로 확장해 뿌리를 막았다. **정정 기록: 3곳은 부분 목록이었다** |
| **F-4** | FAIL | **PASS 제안** (조건: V1·V2 렌더 확인) | 백엔드 조립 제거(뿌리) + 앱 강등(기존 doc) + `numberOfLines={2}`(하드 스톱) 3겹. 승인 상수 전부 ≤20자로 상한 24 대비 여유 증명. **33-G 의 지목 위치(`result.tsx:475-505`)는 오기 — 근본원인은 `phrasebook.assemble_praise`** |
| **F-5** | FAIL | **PASS 제안** (조건: V3·V4 렌더 확인) | 두 기호에 단어 라벨 + 마커와 단일 스타일 소스 스와치. 화면 문장 수는 −1(순감) |
| **F-7** | FAIL | **PASS 제안** (조건: V5·V6 전·후 캡처) | 앵커 = 요약 카드 자신, 펼침·접기 양쪽. stale-y 경합도 소멸. 코드 게이트는 통과했으나 "튀지 않는다"는 화면으로만 판정 가능 |
| **F-6** | FAIL (원인 미상) | **FAIL 유지 — 원인 미상. 후보 5건 + 실기기 판별 절차 문서화. 후보 2 완화 1건 적용(미확정).** | 실기기 없이 증명 불가. §9 유력 가설(반증됨)에 이어 후속 가설도 **부분적으로만** 성립(카테고리는 양쪽 `.playback` 수렴). **PASS 아님** |
| S1·S3·S6·S7·S13·F-8 | (각자 현재) | **변경 없음** — V11 로 회귀 0 확인 요청 | 이 단위는 카피 상수·게이지 범례·스크롤 앵커·오디오 세션만 만졌다 |

---

## 자체 도출 결정 (Q-22 이후 추가분)

플랜의 Q-1~Q-21 은 그대로 집행했다. 집행 중 새로 필요해진 판단:

| # | 지점 | 결정 | 근거 |
|---|---|---|---|
| **Q-22** | 앱 길이 게이트(24자)가 백엔드 **잔여** 상수 2개도 걸린다 — `_PRAISE_HEADLINE_MISSION_IMPROVED` **43자**, `_PRAISE_HEADLINE_CRITERIA_MET` **40자** | **그대로 둔다**(강등 허용). 백엔드 상수 재작성은 하지 않는다 | 두 문장은 `bodyLg 24/700` 에서 3~4줄이 되어 **F-4 가 지적한 상자 이탈과 같은 성질**이다. 강등 대상은 같은 source 의 승인 로컬 상수라 **의미 손실 0**(둘 다 "지난번보다 좋아졌다"/"감점 항목 없었다"). `numberOfLines={2}` 로 **절삭**되는 것보다 승인 문장을 보이는 편이 낫다. 백엔드 카피 재작성은 **수리가 아니라 카피 라운드**라 새 범위(D-43) |
| **Q-23** | 세션 경합이 실증됐지만 **무음 축을 설명하지 못한다**(양쪽 `.playback` 수렴) | 후보 완화는 적용하되 **라벨을 `후보(미확정)` 로 고정**하고, "증거가 반증하는 것" 절을 SUMMARY 에 명시 | Q-20 "안 되는 걸 고쳤다고 하는 게 가장 나쁘다". 경합 실증(적용 조건)과 인과 증명(PASS 조건)은 다른 기준이다 |
| **Q-24** | F-6 판별 절차의 **첫 분기**를 무엇으로 둘 것인가 | **"큐 시점에 영상이 멈추는가"** 를 1번 분기로 | `VideoCompare.tsx:692-699` 가 `started=true` 일 때만 pause 한다 = **소리 없이도 관측 가능한 `speakCue` 반환값 프록시**. 로그 없이 belle 이 "소리 이전의 문제"와 "소리만의 문제"를 한 번에 가른다 |
| **Q-25** | `deductionSheet.ts:125` JSDoc 이 낡은 라벨(`다리 신전(펴짐)`)을 예시로 인용 | **갱신**. 게이트 대상은 아니지만 문서가 틀린 것은 별개 | 목업 7R#1 "record 원문 보존"은 **증거·provenance**를 가리킨다. 포맷 예시는 증거가 아니라 설명이고, 틀린 예시는 다음 사람을 오도한다 |
| **Q-26** | 백엔드 회귀 판정을 어떻게 할 것인가(`git stash` 금지, 브랜치 전환 금지) | baseline 커밋을 `git archive` 로 **스크래치패드에 풀어** 같은 pytest 를 돌리고 node ID 정렬 비교 | 작업 트리·브랜치·stash 를 전혀 건드리지 않는 유일한 방법. §C-1 이 쓴 "FAILED/ERROR node ID 동일" 판정과 같은 축 |

---

## Deviations from Plan

**None — 플랜대로 집행.** 플랜이 지시한 범위 밖 수정 0.

기록해 둘 차이 2건(범위 확장 아님):
1. **`deductionSheet.ts` 가 `files_modified` 에 없었다** — JSDoc 예시 1줄 갱신(Q-25).
   렌더 영향 0, 게이트 대상 밖.
2. **`result.tsx` 요약 블록 33줄이 2칸 재들여쓰기됐다** — 래퍼 `View` 추가에 따른 공백만.
   diff 를 키우지만 들여쓰기가 깨진 JSX 를 남기지 않기 위해 함께 처리했다.

## Issues Encountered

1. **게이트 테스트 typecheck 실패** — `fs.Dirent.path` 가 현재 타입 정의에 없어
   `entry.parentPath ?? entry.path` 가 TS2339. `parentPath` 단독으로 교체해 해결.
2. **`node --test <디렉터리>` 실패** — 디렉터리 모드 실행은 실패하나 **파일 개별 실행은
   10/10 전부 통과**(pre-existing, 이번 변경과 무관). 검증은 파일 단위로 수행했다.
3. **`backend/tests` 전체에 pre-existing 실패 42건 + collection error 2건** — baseline
   대비 완전 동일(Q-26 방법). 이 플랜과 무관.

## 이관 항목 (발견분)

| # | 항목 | 이관처 | 근거 |
|---|---|---|---|
| ① | 백엔드 `_PRAISE_HEADLINE_MISSION_IMPROVED`(43자)·`_PRAISE_HEADLINE_CRITERIA_MET`(40자) 카피 축약 | **카피 라운드**(수리 밖) | Q-22. 현재는 앱이 승인 상수로 강등해 화면은 정상이나, 백엔드가 렌더되지 않을 문장을 계속 방출한다 |
| ② | F-6 후보 4 완화 = `createAudioPlayer(url, { keepAudioSessionActive: true })` | belle 확인 ③ **이후** | 세션 수명주기 변경이라 상위집합 아님. 분기 D-2 가 후보 4 를 지목하면 1순위 |
| ③ | LLM 생성 코치 문장은 정적 어휘 게이트 밖 | 후속 | 게이트는 fixture·상수·앱 소스를 덮는다. Cerebras/Gemini 런타임 산출물은 프롬프트 측 제약이 담당 |
| ④ | `KeypointOverlay.tsx` 흰색 hex 리터럴 12곳 토큰 교체 (2단위 소견) | 후속 | 이번 단위 `files_modified` 밖. `GoalGaugeBar` 는 hex 0 유지 확인 |

---

## Self-Check: PASSED

- 산출물 파일 존재: `screenVocabulary.test.ts`(신설) + 수정 8파일 + SUMMARY **전건 FOUND**
- 삭제 확인: `app/src/components/DimensionDetailModal.tsx` **부재**(의도된 삭제, Q-3)
- 커밋 존재: `747e756` · `ac19aa3` · `ad9210a` **전건 FOUND**
- F-6 라벨 규율: SUMMARY 내 "F-6 ... PASS" 는 **금지 문구 2줄뿐**(`PASS 주장 금지` / `PASS 아님`).
  해결·PASS 주장 **0**
- 이모지 **0** (CLAUDE.md §7)

**미수행(의도적):** `STATE.md` 갱신 · `ROADMAP.md` 갱신 · `33-G` 표 갱신 · docs 커밋.
오케스트레이터 지시(문서 산출물 커밋 금지 + 33-G 미갱신)에 따른다 — 재채점은 시뮬 렌더
확인(V1~V13) 결과가 나온 뒤 오케스트레이터가 판정한다.

---

*quick-260731-cum — 33-G §C-2 앱 **4단위(마지막)**. 자체 도출 결정 Q-1~Q-21(플랜) + Q-22~Q-26(집행).*
*다음 = 오케스트레이터 시뮬 렌더 확인(V1~V13) → 33-G 재채점 → §C-4(Pod).*
