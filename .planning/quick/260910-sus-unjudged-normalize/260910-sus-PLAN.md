---
id: 260910-sus
title: unjudgedJoints 정규화 누락 — 앱이 필드를 통째로 버린다
date: 2026-09-10
status: planned
---

# 백엔드가 보내도 앱이 못 받는다

## 증상 (시뮬레이터 실물 관측, 2026-09-10)

`quick-260910-ovo` 가 `result.unjudgedJoints` 를 계약 3벌에 넣고 앱에 한 줄
(`result.tsx:855-861` → `UNJUDGED_NOTE`)까지 배선했다. **타입체크 0, 백엔드 pytest 4662,
앱 테스트 253 전건 통과.**

그런데 시뮬레이터에서 그 필드를 실제로 넣은 doc 을 열었더니 **줄이 안 그려진다.**

## 원인 (코드로 확정)

`app/src/lib/userAnalyses.ts` 의 정규화는 **아는 필드만 골라 담는 화이트리스트 구조**다
(`:702-736` 부근, `attributionReliability` / `coachAudio` / `spotCheck` 등을 하나씩 명시).
`unjudgedJoints` 는 그 목록에 **없다** (`grep unjudgedJoints app/src/lib/userAnalyses.ts` = 0건).

→ Firestore 가 필드를 보내도 정규화 단계에서 **버려진다.** `result.unjudgedJoints` 는 앱에서
영원히 `undefined` 이고, `result.tsx:857` 의 `?? 0` 이 항상 0 을 만들어 줄이 안 그려진다.

**이 결함은 타입체크·단위테스트가 원리적으로 못 잡는다.** 타입은 옵셔널 필드라 통과하고,
테스트는 정규화를 거치지 않은 객체를 직접 만들어 쓴다. 화면을 띄워야만 드러난다.

## Task 1 — 정규화 추가 + 그 층을 덮는 테스트

**files**: `app/src/lib/userAnalyses.ts`, `app/src/lib/__tests__/` 아래 신규 또는 기존 테스트

**action**:

(a) `normalizeAttributionReliability`(`:351`) 와 **같은 방어 수준**으로
`normalizeUnjudgedJoints(value: unknown): UnjudgedJoint[] | undefined` 를 쓴다.

- 배열이 아니면 `undefined`
- 각 원소: 객체이고 `joint` 가 **비어있지 않은 문자열**, `reason` 이 **`UnjudgedReason` 허용값**
  일 때만 보존. 아니면 그 원소만 버린다(전체를 버리지 않는다 — `normalizeRecordPhraseFields`
  의 "malformed 는 강등하되 나머지는 보존" 관례).
- 살아남은 게 0개면 **빈 배열을 그대로** 돌려라 (`undefined` 로 바꾸지 마라).
  타입 주석이 **"빈 배열 = 봤는데 붕괴 0" / "부재 = 안 봤다"** 로 둘을 구분한다
  (`app/src/types/analysis.ts:955-958`). 그 구분을 정규화가 뭉개면 안 된다.
- `reason` 허용값은 `analysis.ts` 의 `UnjudgedReason` 을 **정본으로 import** 해서 쓰라.
  문자열을 손으로 복사하지 마라 — 나중에 신뢰도 축이 붙으면 어긋난다.

(b) `:733` 의 `attributionReliability:` 옆에 `unjudgedJoints: normalizeUnjudgedJoints(r.unjudgedJoints)`
를 추가한다. 주석에 **왜 이 줄이 필요한지**(화이트리스트 구조라 빠지면 통째로 버려진다)를 적어라.

(c) **★ 같은 구멍이 더 있는지 확인하라.** `app/src/types/analysis.ts` 의 `AnalysisResult` 필드
목록과 `userAnalyses.ts` 정규화가 담는 필드 목록을 **대조**해서, 정규화에서 빠진 필드가
`unjudgedJoints` 말고 또 있는지 세라. 있으면 **고치지 말고 목록만 SUMMARY 에 보고**하라
(이번 범위는 이 필드 하나다).

**테스트 축 (반드시 포함)**
1. 정상 배열 → 그대로 보존, length 유지
2. **빈 배열 → 빈 배열** (undefined 로 바뀌면 안 됨)
3. 부재 → undefined
4. 배열 아님(객체·문자열·null) → undefined
5. 원소 중 하나가 malformed(joint 가 숫자 / reason 이 미허용 문자열) → **그 원소만 제외**,
   나머지 보존
6. 전원 malformed → 빈 배열
7. ★ **정규화 경유 통합 축** — 이 결함의 재발을 막는 유일한 축이다.
   Firestore raw shape 에 가까운 객체를 정규화 함수에 통과시켰을 때 `unjudgedJoints` 가
   **살아남는지**. (지금 테스트들이 정규화를 건너뛰고 객체를 직접 만들어 쓰기 때문에
   이 결함이 통과했다.)

**verify**:
```bash
cd app && npm run typecheck
cd app && node --test $(find src -path '*__tests__*' -name '*.test.ts')
```
착수 전 기준선을 먼저 재라 (직전 관측 = typecheck 0 / 253 pass).

**done**: 타입체크 0, 테스트 무감소, 신규 축 전건 통과.

## ★ 하지 말 것

- `result.tsx` 의 렌더 로직·문구 상수를 건드리지 마라. 거긴 정상이다.
- 다른 필드의 정규화를 고치지 마라 (있으면 보고만).
- 백엔드·계약 무접촉. 이건 앱 읽기 층 단일 결함이다.

## 검증의 한계

이 수리가 실제로 줄을 그리는지는 **시뮬레이터에서 그 필드를 가진 doc 을 열어야** 확인된다.
테스트 통과는 "정규화가 필드를 통과시킨다"까지고, "화면에 그려진다"가 아니다.
검증본 doc(`users/qdeLN9Ur1yMFb9duNT2ep3g4pmT2/analyses/c64afae69fd24366b4b5f375aa0a91fb`)에
이미 `result.unjudgedJoints = [{joint:"right_elbow", reason:"collapse"}]` 가 들어가 있다.
