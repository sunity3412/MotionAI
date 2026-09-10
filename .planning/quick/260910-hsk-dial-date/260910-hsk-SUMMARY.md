---
id: 260910-hsk
title: 결과 화면 점수 아래 날짜 표기
date: 2026-09-10
status: implemented-unverified-on-device
---

# 점수 원 아래 'Today' → 실제 분석 시각

박힌 문자열 `const DIAL_LABEL = 'Today'` 를 제거하고 `createdAt` 에서 계산한 한 줄 표기로
바꿨다. 규칙·경계는 PLAN 그대로 (달력 날짜 기준 · 7일 경계 · 미래는 오늘로 접기 · 결측은 빈 문자열).

## 바뀐 파일과 커밋

| 커밋 | 파일 | 내용 |
|---|---|---|
| `4bb81fdb` | `app/src/lib/analysisDate.ts` (신설, 85줄) | `formatAnalysisMoment(createdAtMs, nowMs)` + `ABSOLUTE_DATE_FROM_DAYS = 7`. react/react-native/expo import 0 |
| `4bb81fdb` | `app/src/lib/__tests__/analysisDate.test.ts` (신설) | 검증축 7개 |
| `2871daef` | `app/src/app/analysis/result.tsx` (+27 −5) | 상수 제거 → `useMemo` 배선, 접근성 라벨에 날짜 포함, 주석 이력 갱신 |

삭제된 파일 0 (`git diff --diff-filter=D` 두 커밋 모두 빈 출력).
범위 밖 파일(`(tabs)/index.tsx`, `(tabs)/history.tsx`, `RenderedComparePlayer.tsx`,
`sourceSwapSeek.ts`)은 두 커밋 어디에도 들어가지 않았다 — `git log --name-only` 로 확인.

## 실제로 돌린 검증 명령과 출력 숫자

기준선(손대기 전, 같은 명령):

```
node --test $(find src -path '*__tests__*' -name '*.test.ts')
  → tests 234 · pass 234 · fail 0
npx tsc --noEmit
  → 출력 없음, exit 0
```

Task 1 직후:

```
node --test src/lib/__tests__/analysisDate.test.ts
  → tests 7 · pass 7 · fail 0
node --test $(find src -path '*__tests__*' -name '*.test.ts')
  → tests 241 · pass 241 · fail 0   (234 + 7, 줄어든 건 없음)
npx tsc --noEmit
  → TSC_EXIT=0, 에러 0
```

Task 2 직후 (최종):

```
npx tsc --noEmit
  → TSC_EXIT=0, 에러 0
node --test $(find src -path '*__tests__*' -name '*.test.ts')
  → tests 241 · pass 241 · fail 0 · duration_ms 427
```

검증축 7개 전건 이름:

1. 같은 날이면 오늘 + 시각, 시:분은 2자리 고정 (`09:05`)
2. 20분 차이라도 자정을 넘었으면 어제 (`23:50` → `어제 23:50`)
3. 2~6일 전은 N일 전 (시각 없음)
4. 7일째부터 날짜로 (6↔7 경계 — `9월 4일`분은 `6일 전`, `9월 3일`분은 `9월 3일`)
5. 미래 시각은 오늘로 접는다 (`-1일 전` 없음)
6. createdAt 이 없거나 유한수가 아니면 빈 문자열 (NaN · 0 · undefined · 음수 · Infinity,
   그리고 nowMs 가 NaN 인 경우까지)
7. 연도를 넘는 일수 계산 (12/28 → 1/3 = `6일 전`, 1/4 = `12월 28일`, 12/31 23:50 → 1/1 00:10 = `어제 23:50`)

## ResultScoreDial 이 빈 문자열 라벨에서 어떻게 동작하는가

**결론: 깨지지 않는다. 그래서 그 줄을 조건부로 걷어내지 않았다.** (렌더 실행이 아니라 코드
판독으로 확인한 것임 — 아래가 근거다.)

- `ResultScoreDial.tsx:172-179` `styles.label` = `position: 'absolute', left: 0, right: 0`.
  절대배치라 형제(점수 숫자 Text, SVG 호)의 배치에 영향을 주지 못한다.
- `:138-142` 의 `top` 계산은 `D.labelCenterY` · `fontSize` · `LABEL_LH` · `LABEL_INK_OFFSET`
  상수만 쓴다. **글자 내용이 인자로 들어가지 않는다** — 빈 문자열이어도 숫자 위치가 안 움직인다.
- 부모 `wrap` 은 `:92-94` 에서 `width: size, height: size` 로 못박혀 있어, 라벨이 비어도
  원반이 오그라들 수 없다.
- 잉크 기준 정렬 계산(`:38-51`, `:59-62`)은 **폰트 메트릭 상수**지 측정된 텍스트 폭이 아니다.
  PLAN 이 우려한 "빈 문자열에서 레이아웃이 무너짐" 경로는 이 구현에 없다.
- 다만 컴포넌트 **기본** 접근성 라벨(`:102` `` `${점수}점 ${label}` ``)은 빈 라벨에서 꼬리
  공백이 남는다. result.tsx 는 항상 명시 `accessibilityLabel` 을 넘기므로 이 화면에서는
  그 기본값이 쓰이지 않고, 넘기는 쪽에서 빈 문자열이면 점수만 읽도록 분기했다.

## 라벨이 길어진 것(5자 → 8자)의 잘림 위험 — 코드로 점검

`styles.label` 에 `numberOfLines` 가 없다. 즉 **넘치면 잘리는 게 아니라 두 줄로 감긴다** —
그게 이 자리에서의 실제 사고 형태다(원 안 두 줄). 그래서 "가용 폭 대비 실제 advance 합"을 쟀다.

번들 폰트 `app/assets/fonts/Pretendard-Regular.ttf` 를 직접 파싱해(cmap fmt4 + hmtx +
head.unitsPerEm=2048) 글자별 advance 를 합산했다. `typography.resultDialLabel` 은
letterSpacing 이 없어(typography.ts:105) advance 합이 곧 렌더 폭이다.

가용 폭 = 원반 지름 = `292.62 × K` (K = 390/467.206) = **244.26pt**, 라벨 = **22pt**.
둘 다 `s = width/390` 에 같이 곱해지므로 **비율은 기기 폭과 무관**하다.

| 라벨 | 폭(pt) | 여유(pt) | 사용률 |
|---|---|---|---|
| `Today` (종전) | 62.35 | 181.92 | 25.5% |
| `오늘 10:24` | 98.53 | 145.74 | 40.3% |
| `어제 23:50` | 101.86 | 142.41 | 41.7% |
| `어제 44:44` (숫자 최악) | 104.05 | 140.22 | **42.6%** |
| `12월 28일` | 92.36 | 151.90 | 37.8% |
| `3일 전` | 57.13 | 187.14 | 23.4% |

최악 조합도 가용 폭의 43% 다. **줄바꿈·잘림 여지 없음.** (계측 스크립트는 scratchpad —
휘발성이라 보존물로 치지 않는다. 재현하려면 위 파싱 절차 그대로.)

## PLAN 이탈

없음. 규칙·경계는 PLAN 표와 "경계 정의" 그대로 구현했다. 한 가지 **기록해 둘 한계**:

- 일수 계산을 PLAN 지시대로 `floor((오늘 자정 − 그날 자정) / 86400000)` 로 했다. DST 가 있는
  타임존에서는 23시간짜리 날에 floor 가 하루를 삼킬 수 있다(어제가 오늘로 보임). 파일럿 대상
  KST 는 DST 가 없어 실제 피해가 없고, 임의로 바꾸지 말라는 지시가 있어 그대로 두되
  `analysisDate.ts` 헤더에 주석으로 못박았다. DST 지역 지원 시 여기부터 고칠 것.

## 검증의 한계 (PLAN §검증의 한계 승계)

**시뮬레이터로 실물을 보기 전에는 "됐다"고 하지 않는다.**

`tsc` 와 `node --test` 는 렌더 결과를 못 본다. 09-09 에 글자를 시안 크기로 키웠더니
'보완운동' 이 '보와우동' 으로 렌더된 적이 있고 그때도 tsc 0 · 테스트 226/0 을 통과했다
(quick-260909-ji1). 이번 수리는 **라벨 길이가 5자에서 8자로 늘어난다**. 위 폰트 실측은
"이론상 폭이 남는다"까지만 말하고, 실제 렌더(자간 처리·한글 글꼴 폴백·잉크 정렬)는 말하지 못한다.

남은 확인:
1. 시뮬레이터에서 결과 화면 요약 탭을 열어 원 안 한 줄이 **한 줄로** 나오는지, 숫자와의
   간격이 09-09 대조본에서 안 벌어졌는지.
2. 기록 탭에서 **오래된 분석**을 열어 `N일 전` / `M월 D일` 이 실제로 뜨는지 (오늘 건만
   보면 이 수리의 요점인 "거짓 Today" 를 못 본다).

이 두 가지 전에는 belle 에게 판정 요청을 올리지 않는다.

## Self-Check: PASSED

- `app/src/lib/analysisDate.ts` — FOUND
- `app/src/lib/__tests__/analysisDate.test.ts` — FOUND
- 커밋 `4bb81fdb` — FOUND (`git log --all`)
- 커밋 `2871daef` — FOUND
- SUMMARY 는 미커밋 상태 유지 (`git status` = untracked) — 지시대로
