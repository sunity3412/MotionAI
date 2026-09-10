---
id: 260910-ovo
title: 붕괴 사지 판정불가 게이트
date: 2026-09-10
status: planned
---

# 관측하지 못한 사지에는 감점을 매기지 않는다 (붕괴 축 한정)

## belle 지시 (2026-09-10)

> "아는척 하면 안되지."
> "내가 오른팔이라고 확정했으니 정답이 아니라, 너가 그걸 잡아내야했던게 맞아 — 정확히는 우리 앱 분석이."

**(가) 채택** — 판정 불가 관절은 **감점 행과 확대 카드를 만들지 않는다.** (나)(행은 남기고 숫자만
제거)는 belle 이 기각했다: *"문제는 그 사진"* — 아무 데도 안 가리키는 확대 사진이 남으면 불만이
하나도 안 고쳐진다.

## 왜 붕괴 축만인가 (측정으로 결정됨, 2026-09-10)

판정가능성 축 3종을 승인 fixture 5대상에 실측한 결과:

- **(a) 절대 신뢰도 0.5 하한 — 이번에 쓰지 않는다.** 6동작 14 멈춤 중 **7건**에서 그 멈춤의
  감점이 전부 판정 불가가 되어 멈춤 자체가 사라진다(elbow-twist 는 4/4 전부 → 멈춤 없는 비교영상).
  게다가 계기가 위태롭다 — 정립 fixture powerspin `left_hip` 이 **정확히 0.5000**(한 프레임 차이로
  판정이 뒤집힘)이고, RTMW conf 는 역립·정립 구분 없이 전부 0.4~0.6 에 몰려 있어 임계가 분포
  **한가운데**에 그어진다. 방향은 맞지만 크기를 못 믿는다. **별건으로 분리.**
- **(c) 좌우 자기모순 — 사문.** 5대상 실측 0.047~0.175, 임계 0.20 미달로 한 번도 발화 안 함.
  이 데이터로는 임계 근거가 없다. 넣지 않는다.
- **(b) 붕괴 — 채택.** 분리가 한 자릿수 넘게 난다:

  | | 단축/장축(aspect) | 길이비 L/median(L) |
  |---|---|---|
  | 대표 사례 f162 **오른팔**(폴에 붕괴) | **0.052** | **0.46** |
  | 같은 프레임 **왼팔**(정상) | **0.748** | — |
  | kipup f16 곧게 편 다리 | 0.016~0.042 | **1.16 / 0.88** |

  belle 이 눈으로 짚은 서명("가로 12px / 세로 220px" = 0.055)과 계산값 0.052 가 일치한다.

**★ 함정 — 공선성 단독 사용 금지 (실측으로 재현됨).** 곧게 편 정상 다리도 공선이다
(kipup aspect 0.016~0.042 로 붕괴한 팔보다 더 납작하다). 공선성만 쓰면 **정립 fixture 5행이
위양성**으로 걸린다. 갈라주는 축은 **단축(foreshortening)** — 붕괴한 사지는 길이가 평소의 절반로
줄어든다(0.46) 반면 곧게 편 다리는 안 줄어든다(0.88~1.16). **두 조건 AND 가 필수.**

**★ 곡선맞춤 위험을 박제한다.** 길이비 임계 0.60 은 위 두 숫자(0.46 vs 0.88) 사이에 그은 값이고,
게이트 실패를 본 뒤 **사후에 추가**된 축이다. 표본이 5대상뿐이다. 그래서 이번에는 **보수적으로**
잡고(붕괴 쪽에 붙여), 정립에서 하나라도 발화하면 즉시 실패로 본다.

측정 스크립트 원본이 같은 디렉터리에 있다: `measured_judgeability_reference.py`
(참고용이다. 그대로 복사하지 말고 프로덕션 규약에 맞게 다시 쓸 것.)

---

## Task 1 — 순수 붕괴 판정 모듈 + 테스트

**files**: `backend/shared/python/sunity_shared/analysis/limb_collapse.py` (신설),
`backend/tests/test_limb_collapse.py` (신설 — 기존 테스트 위치 규약을 확인해 맞출 것)

**action**:
analysis 패키지의 기존 순수 모듈 규약을 따른다 — **numpy 만**, AWS/모델/네트워크 의존 0,
모듈 헤더 docstring 에 목적과 근거(위 표) 인용.

```python
def limb_aspect_and_length(p0, p1, p2) -> tuple[float, float]:
    """사지 3점(어깨-팔꿈치-손 / 엉덩이-무릎-발목)의 납작한 정도와 길이.

    aspect = PCA 단축/장축.  length = |p0-p1| + |p1-p2|.
    """

def is_limb_collapsed(
    aspect: float, length: float, median_length: float,
    *, aspect_max: float = COLLAPSE_ASPECT_MAX,
    length_frac_max: float = COLLAPSE_LENGTH_FRAC_MAX,
) -> bool:
    """납작함 AND 단축 — 둘 다여야 붕괴다. (곧게 편 정상 사지는 납작하지만 안 줄어든다.)"""
```

- 상수는 모듈 상단에 이름 붙여 선언하고, **각 값 옆에 위 표의 실측 근거를 주석으로** 달 것.
- 3점 중 하나라도 결측(NaN)이면 판정 불가가 아니라 **False**(붕괴 아님)를 돌려라 —
  이 게이트는 감점을 **없애는** 쪽이라 의심스러우면 보수적으로(안 없앰) 가야 한다.
- `median_length` 는 클립 전체 프레임의 그 사지 길이 중앙값이다. 계산 헬퍼도 이 모듈에.

**테스트 축 (반드시 포함)**
1. 대표 사례 서명 재현 — aspect 0.05 수준 + 길이비 0.46 → **True**
2. 같은 프레임 정상 팔 — aspect 0.75 → **False**
3. **곧게 편 정상 다리 — aspect 0.02, 길이비 1.16 → False** (이 축이 없으면 정립 위양성)
4. 납작하지만 안 줄어든 경우 → False (AND 조건 확인)
5. 줄었지만 안 납작한 경우 → False
6. NaN 포함 → False
7. 길이 0 / median 0 → 0 나눗셈 없이 False

**verify**: `cd backend && python3 -m pytest tests/test_limb_collapse.py -q`
그리고 전체 `python3 -m pytest -q` 로 기존 건수가 줄지 않는지 확인.
착수 전 기준선을 먼저 재서 SUMMARY 에 적을 것 (인계서 기록은 4731 passed).

**done**: 신규 테스트 전건 통과, 기존 pytest 건수 무감소.

---

## Task 2 — 파이프라인 배선 + 사실 기록

**files**: `backend/functions/pipeline/app.py`,
`backend/shared/python/sunity_shared/models.py`, `docs/contract.md`,
`app/src/types/analysis.ts`

**action**:

(a) **게이트 지점 = `_emit_reference_relative(jk, v)`** (`pipeline/app.py:2750` 부근).
이 함수는 이미 "방출하지 않음" 규칙들의 단일 관문이고 bool 을 돌린다. 여기에 조건을 하나 더 얹는다:

```
if 그 관절이 속한 사지가 측정 순간에 붕괴했으면:
    unjudged 로 기록하고 return False   # md 미방출 → criterion 미seed → record·freeze·card 전부 미생성
```

★ **이 지점이어야 하는 이유** — 멈춤(freeze)은 record 에서 태어난다
(`compare_render.py:1227` records 루프 → `:1345` freezes.append). record 를 안 만들면 그 멈춤도
같이 안 생기므로 **"사진 0장인 멈춤"이 원리적으로 생기지 않는다.** 표시층에서 카드만 지우면
사진 0장 멈춤이 남아 09-03 규칙("멈추는 구간은 다 보여줘야 한다")을 위반한다.

관절 → 사지 3점 매핑은 `reliability.ANGLE_REQUIRED_KEYPOINTS`(`reliability.py:26-46`)를
**재사용**하라. 새 매핑표를 만들지 마라.
판정 프레임은 **그 감점의 측정 순간**이다. 순간을 특정할 수 없으면(레거시 doc 처럼
`atFrameIdx` 가 없으면) **게이트를 걸지 마라** — 의심스러우면 안 없앤다.

(b) **사실을 기록한다.** 없앤 것을 없었던 일로 만들지 않는다.
```
result.unjudgedJoints: [{ joint: str, reason: "collapse" }]
```
- `reason` 은 지금 "collapse" 하나뿐이지만 **문자열 enum 으로 열어 둔다**
  (신뢰도 축이 나중에 붙는다).
- **Firestore 중첩 배열 금지** 제약을 확인하라. 객체 배열은 허용되지만, 안전하지 않다고
  판단되면 평탄화 규약(`angles`/`anglesJointKeys` 선례)을 따르고 그 이유를 주석에 적어라.

(c) **계약 3벌 동시 수정** — `docs/contract.md` 해당 절 + `models.py` + `app/src/types/analysis.ts`.
셋이 어긋나면 안 된다 (CLAUDE.md 교차 규칙).

**verify**:
```bash
cd backend && python3 -m pytest -q
cd app && npm run typecheck
```
그리고 **재현 하네스로 영향을 실측하라**: `backend/evals/realfixture/replay.py` 를 읽고
(GPU/Pod/Gemini/Firestore 0 이라고 헤더가 주장한다 — 코드로 확인) 수리 전/후를 돌려 diff 를 내라.
요구:
- **정립 fixture(powerspin / kipup): record 집합·points·카드 수 byte-동일.** 하나라도 바뀌면 실패.
- 대표 사례 계열: `right_elbow` 계열 record 1건만 빠지고 `left_elbow` 는 남는가.
- 사진 0장이 되는 멈춤 = **0건**.
하네스가 안 돌면 **왜 안 도는지 정확히 적고**, 대신 무엇으로 확인했는지 밝혀라. 안 돌렸으면 안 돌렸다고 적어라.

**done**: 위 3개 요구 전부 충족, 계약 3벌 일치, 테스트 무감소.

---

## Task 3 — 앱에 사실 한 줄

**files**: `app/src/app/analysis/result.tsx` (요약 탭 점수 근처), 필요하면 관련 컴포넌트

**action**:
`unjudgedJoints` 가 비어 있지 않으면 점수 아래/옆에 **짧은 한 줄**을 그린다.

- 초안 문구: **"8곳 중 1곳은 가려져서 못 봤어요"** (숫자는 `unjudgedJoints.length` 와 전체 관절 수)
- ★ **문구는 belle 이 정한다.** belle 이 아직 확정하지 않았다("글도 그냥 구구절절 될까바 애매하고").
  그래서 **문구를 상수 하나로 빼서 한 줄만 고치면 바뀌게** 만들어라. 여러 곳에 흩지 마라.
- 비어 있으면 **아무것도 안 그린다** (0곳일 때 "0곳은 못 봤어요" 금지).
- 기존 시안 대조로 맞춰 둔 치수(`ResultScoreDial.tsx:38-51`)를 건드리지 마라. 줄 하나 추가뿐.

**verify**: `cd app && npm run typecheck` + `node --test $(find src -path '*__tests__*' -name '*.test.ts')`
기준선 = typecheck 0 / 테스트 241 pass.

**done**: 타입체크 0, 테스트 무감소, 문구가 상수 1개로 모여 있음.

---

## ★ 하지 말 것

- **신뢰도(conf) 기준을 넣지 마라.** 이번 범위 밖이다. 측정에서 계기가 위태로운 것이 확인됐다.
- **`temporal.py` / `features.py` 를 고치지 마라.** 그 두 곳의 결함(신뢰도 무시, 마스크 통째 폐기)은
  확정됐지만 손대면 승인된 채점 전반이 움직인다. 별건.
- 좌우(chirality) 관련 코드를 건드리지 마라. **좌우는 문제가 없었던 것으로 오늘 확정됐다.**
- `VideoCompare.tsx`, 앱의 다른 날짜 표기 두 곳, `RenderedComparePlayer.tsx` 무접촉.
- 임계를 정립 fixture 가 통과하도록 **결과를 보고 조정하지 마라.** 한 번 정하고, 실패하면
  실패로 보고하라.

## 검증의 한계

- **이 수리는 새 분석에만 적용된다.** belle 의 기존 doc 은 이미 저장된 값이라 안 바뀐다.
  belle 이 화면에서 보려면 **Pod 을 띄워 재분석**해야 한다. 그건 이 작업 다음 단계다.
- 재현 하네스는 저장된 값을 다시 조립하는 것이지 실제 추론이 아니다. 실제 파이프라인에서
  같은 판정이 나오는지는 Pod 실행으로만 확인된다.
- 임계 2개는 표본 5대상에서 나왔다. **역립 동작이 더 들어오면 재검토 대상**이다.
