---
id: 260910-sus
title: unjudgedJoints 정규화 — 계획서 진단이 틀렸다
date: 2026-09-10
status: done (수리는 됐으나 증상은 안 고쳐진다)
commit: c7296031
---

# 판정 먼저

**안 된다 — 이 작업은 "줄이 안 그려진다"를 고치지 못한다. 계획서의 원인 진단이 틀렸다.**

계획서는 "정규화가 아는 필드만 골라 담는 화이트리스트라 `unjudgedJoints` 가
**버려진다**"고 단정했다. 실측 결과 그건 사실이 아니다. 필드는 버려지지 않는다.

대신 **다른 구멍이 실재했고 그건 고쳤다** — malformed 값이 무검증으로 화면까지 새는 쪽.

---

## 1. 무엇을 재서 그렇게 말하는가

계획서를 그대로 구현한 뒤, 추가한 한 줄만 지우고 테스트를 돌리는 뮤테이션 점검을 했다.
"필드가 살아남는가" 축이 **그 줄 없이도 통과**했다. 그래서 HEAD 코드 자체를 직접 쟀다.

`git show HEAD:app/src/lib/userAnalyses.ts` 를 그대로 복사해 (`unjudgedJoints` 등장
횟수 = 0 인, 손대기 전 원본) 검증본 doc 형상을 통과시켰다:

```
HEAD normalize -> result.unjudgedJoints = [{"joint":"right_elbow","reason":"collapse"}]
hidden = 1   total = 3
```

`hidden = 1`. 소비처(`result.tsx:856-857`)가 세는 그 값이 1로 나온다. 0이 아니다.
**손대기 전에도 필드는 정상으로 통과하고 있었다.**

### 왜 계획서가 틀렸나 — pick 이 아니라 overlay 다

`normalize()` 는 필드를 골라 담지 않는다:

```
let result = raw.result as AnalysisDoc['result'] | undefined;   // :476  raw 키를 전부 물고 시작
...
result = { ...result, mission: ..., attributionReliability: ... };  // 아는 필드만 "덮어쓴다"
```

`{ ...result, ... }` 스프레드는 목록에 없는 키를 **보존**한다. 목록은 화이트리스트가
아니라 덮어쓰기 목록이다. 그래서 여기 없는 필드는 *사라지는 게 아니라*
**검증 없이 raw 그대로 화면까지 간다.**

`grep unjudgedJoints userAnalyses.ts = 0건`은 사실이었지만, 그 0건이 "버려진다"를
뜻하지는 않았다. 파일에 없다 ≠ 드롭된다.

## 2. 그래서 실제로 고친 것

남아 있던 진짜 위험은 반대 방향이다. 소비처는 `result.unjudgedJoints?.length ?? 0`
하나로만 분기한다. 백엔드가 문자열(`"right_elbow"` → length 11)이나 malformed 원소를
실으면 **없는 관절 수를 그대로 세어 사용자에게 말한다.** 이 파일의 다른 백엔드 방출
필드(`attributionReliability`/`coachAudio`/`spotCheck`/`coachQuestions`)는 전부
방어 파싱이 있는데 이 필드만 없었다. 그 격차를 메웠다.

## 3. 바뀐 줄

**커밋:** `c7296031` — `fix(app): unjudgedJoints 방어 파싱 + normalize() 첫 통합 테스트`
2 files changed, 229 insertions(+), 1 deletion(-)

| 파일 | 위치 | 내용 |
|---|---|---|
| `app/src/lib/userAnalyses.ts` | `:35-36` | `UnjudgedJoint`, `UnjudgedReason` 타입 import |
| | `:372-402` | `UNJUDGED_REASONS` 상수 + `normalizeUnjudgedJoints()` (신규 31줄) |
| | `:442-450` | `normalize()` 를 `export` 로 (검증 목적, 주석으로 이유 명시) |
| | `:776-784` | overlay 블록에 `unjudgedJoints:` 한 줄 + overlay 구조 주석 |
| `app/src/lib/__tests__/unjudgedJoints.test.ts` | 신규 | 7축, 176줄 |

**빈 배열 vs 부재 구분** (핵심 요구): `normalizeUnjudgedJoints` 는 배열이 **아닐 때만**
`undefined` 를 돌려준다. 원소가 전부 malformed 로 걸러져 0개가 돼도 **빈 배열 그대로**
반환한다. "봤는데 붕괴 0"(빈 배열)과 "안 봤다"(부재)는 다른 사실이고
`analysis.ts:955-958` 주석이 그 둘을 구분한다 — 정규화가 뭉개면 안 된다.
축2·축3·축6 이 이 구분을 각각 고정한다.

**reason 허용값**: 문자열 배열이 아니라 `Record<UnjudgedReason, true>` 로 뒀다.
`readonly UnjudgedReason[]` 은 부분집합도 타입이 통과해서, 나중에 신뢰도 축이 union 에
붙어도 조용히 어긋난다. `Record` 는 키 누락이 **컴파일 에러**라 동기화가 강제된다.

## 4. 착수 전 / 후 검증 숫자

| | 착수 전 | 착수 후 |
|---|---|---|
| `npx tsc --noEmit` | exit **0** | exit **0** |
| `node --test $(find src -path '*__tests__*' -name '*.test.ts')` | **253 pass / 0 fail** | **260 pass / 0 fail** |
| 신규 축 | — | **7 pass / 0 fail** |

착수 전 253은 직접 측정했다(계획서 기재값과 일치).

**뮤테이션 점검** — 추가한 `unjudgedJoints:` 한 줄만 지우고 재실행:

| | 줄 있음 | 줄 지움 |
|---|---|---|
| 축1 정상 배열 보존 | pass | **pass** ← 이 줄 없이도 통과 (진단 반증) |
| 축2 빈 배열 → 빈 배열 | pass | **pass** ← 마찬가지 |
| 축3 부재 → undefined | pass | **pass** ← 마찬가지 |
| 축4 배열 아님 → undefined | pass | fail |
| 축5 malformed 원소만 제외 | pass | fail |
| 축6 전원 malformed → 빈 배열 | pass | fail |
| 축7 실물 doc 통합 | pass | fail |

축1~3이 "줄 지움"에서도 통과하는 것이 계획서 진단이 틀렸다는 증거다.
축4~7은 이 커밋이 실제로 바꾸는 동작(무검증 통과 차단)을 고정한다.

## 5. (c) 대조 결과 — 정규화에서 빠진 필드 목록 (고치지 않음, 보고만)

`AnalysisResult` 최상위 45개 + `ScoreSuppression` 1개 = **46개** 중 **29개**는 방어
파싱이 있고, **17개**는 방어 없이 raw 통과한다.

★ 다시 강조: 이건 "버려지는 필드 목록"이 **아니다.** overlay 구조이므로 전부 화면까지
도달한다. **무검증으로** 도달할 뿐이다.

| # | 필드 | opt/req | 비고 |
|---|---|---|---|
| 1 | `overallScore` | req | 점수 원값. 소비처가 `Math.round()` 로 바로 씀 |
| 2 | `dimensionScores` | req | |
| 3 | `joints` | req | ★ `unjudgedNote` 게이트의 `total` 이 이 배열 길이다 |
| 4 | `tips` | req | |
| 5 | `comparison` | req | |
| 6 | `myVideoUrl` | req | |
| 7 | `scoreSuppressed` | req | `ScoreSuppression` 상속분 |
| 8 | `timingsMs` | opt | audit 전용, UI 비노출 |
| 9 | `visionVeto` | opt | 재생바 결함 틱 |
| 10 | `faultZoomStatus` | opt | |
| 11 | `coachStatus` | opt | |
| 12 | `motionAlignment` | opt | |
| 13 | `renderedCompare` | opt | |
| 14 | `scoreSuppressionAudit` | opt | |
| 15 | `dimensionExplanation` | opt | |
| 16 | `myVideoKey` | opt | ★ S3 key — `coachAudio.key` 는 `results/` prefix 를 강제(H-02)하는데 이쪽은 무검증 |
| 17 | `referenceVideoUrl` | opt | |

방어 파싱이 있는 29개(참고): `unjudgedJoints`(이번 추가), `attributionReliability`,
`deductionBreakdown`, `faultZoomComparisons`, `correctedPose*`(4), `rotation*`(3),
`mission`, `missionOutcome`, `summaryPraise`, `coachQuestions`, `coachAudio`,
`spotCheck`, `bodyComparisonReport`, `forceSignalsReport`, `safetyFlags`,
`forcePatternInference`, `recommendedExercises`, `keypointReport`, `aiSynthesisMeta`,
`joints3d`/`Keys`/`Frames`, `coordDim`, `space`.

> 계획서 지시대로 **고치지 않았다.** 다만 위 17개 중 `myVideoKey`(S3 key 무검증)와
> `joints`(unjudgedNote 게이트 입력)는 별건으로 볼 값어치가 있어 보인다.

## 6. 검증의 한계 (PLAN §검증의 한계 승계 + 이번에 추가된 것)

- **"화면에 그려진다"고 말하지 않는다.** 시뮬레이터에서 그 필드를 가진 doc 을 열어보기
  전에는 확인된 것이 없다. 테스트 통과는 "정규화가 malformed 를 거른다"까지다.
- **더 나아가, 이 커밋은 그 증상을 고칠 것으로 기대되지 않는다.** §1의 실측이
  그 이유다. 시뮬레이터에서 다시 열어봐도 줄은 여전히 안 그려질 가능성이 높다.
- **줄이 안 그려지는 진짜 원인은 미상이다.** 이번 작업으로 배제된 것은 "정규화가
  필드를 버린다" 하나뿐이다.

## 7. 남은 관측 (진단 아님 — 다음 사람이 재야 할 것)

증상은 그대로다. 아래는 **아직 재지 않은** 후보이며, 관측이 아니라 후보다.

1. **doc 에 필드가 실제로 실려 있는가.** Firestore 를 직접 읽어 확인하지 않았다.
   메모리 `[[partial-field-writes-invisible-to-inmemory-doc]]` 은 "사후 부분갱신
   필드는 in-memory 조립본에 안 실린다 — 2회 재발" 을 기록하고 있다. 검증본 doc 에
   필드를 어떻게 넣었는지(파이프라인 산출 vs 사후 부분갱신)에 따라 갈린다.
   → **가장 먼저 잴 것.** 재는 법: 그 doc 을 읽어 `result.unjudgedJoints` 존재 확인.
2. **`total` 게이트.** 소비처는 `total <= 0` 이거나 `hidden > total` 이면 `null` 을
   돌려 아무것도 안 그린다. `result.joints` 가 비었거나 `unjudgedJoints` 가 더 길면
   조용히 사라진다. (`joints` 는 §5의 무검증 17개 중 하나다.)
3. **시뮬레이터 번들이 그 배선을 담고 있었는가.** `unjudgedNote` 는 `resultTab ===
   'summary'` 안 `:1664` 에 렌더된다. 배선 자체는 코드상 정상으로 보인다.
4. **복사 doc 여부.** 메모리 `[[copied-doc-cannot-take-the-composited-path]]`.

계획서 §하지 말 것 준수: `result.tsx` 무접촉(읽기만), 백엔드·계약 무접촉,
다른 필드 정규화 무접촉.

## 8. LLM 학습 영향

없음. 앱 읽기 층 단일 변경이며 프롬프트·코퍼스·학습 경로에 걸리지 않는다.

## 9. 자기 점검

- [x] `c7296031` 커밋 존재 확인 (`git log -1`)
- [x] `app/src/lib/__tests__/unjudgedJoints.test.ts` 생성 확인
- [x] 착수 전 기준선 직접 측정 (253 pass / typecheck 0)
- [x] 뮤테이션 점검으로 테스트가 실제로 무엇을 잡는지 확인
- [x] 계획서 진단을 HEAD 원본 코드로 직접 반증
- [x] SUMMARY 미커밋 (지시대로)
- [ ] 시뮬레이터 실물 확인 — **안 했다.** §6 참조.
