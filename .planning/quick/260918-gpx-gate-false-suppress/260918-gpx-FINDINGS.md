---
date: 2026-09-18
description: 확대 카드 게이트가 멀쩡한 표식을 지우는가 — 결함 2건 확정
---

# 게이트 false-suppress 조사 — 결함 2건

## 왜 봤나

belle 2026-09-18 판정: 확대 카드 `zoom_adv_left_shoulder` 의 학생측 원 위치 = **"어깨 맞음"**.
같은 게이트가 **기준(정은지) 패널의 표식은 `suppressed / head/mismatch` 로 지웠다.**
맞는 것을 지우는 것은 fail-open 보다 나쁘므로 먼저 봤다.

## 실측 — 로그 전수

`fault_zoom_anchor_check` 17건: **pass 12 / suppressed 5 (29%)**.

지운 5건:

| 측·관절 | 관측 | 재시도 | 경로 |
|---|---|---|---|
| ref · left_shoulder | head | **0회** | advisory |
| user · left_elbow | head | **0회** | advisory |
| user · left_hip | elbow | **0회** | stage1 |
| user · right_elbow | thigh ×3 | 2회 | render(r00) |
| ref · right_elbow | thigh | 0회 | render(r00) |

## ~~결함 A — 재시도가 구조적으로 죽어 있다~~ → ★ 철회 (결함 아님)

`verify_anchor_side` 는 mismatch 면 후보 프레임을 **최대 2개** 더 물어보게 돼 있다
(`ANCHOR_CHECK_MAX_RETRY=2`, 그 안전망이 suppressed 의 유일한 완충이다).

**그런데 호출 두 곳 중 한 곳이 후보를 아예 안 준다:**

```python
# backend/functions/pipeline/app.py:3518
res = cg.verify_anchor_side(
    anchor_idx=0, expected=expected, retry_frames=(), ask=_ask,   # ← 하드코딩 빈 튜플
)
```

다른 호출부(5755)는 `cg.anchor_retry_frames(...)` 로 실제 후보를 준다.

**결과:** 이 경로에서는 **눈이 한 번 mismatch 라고 하면 즉시 지운다.** 로그의
재시도 0회 4건이 전부 이 경로다 — **belle 님이 판정한 그 카드(advisory)도 여기다.**

### ★ 철회 — 결함이 아니다 (2026-09-18, 같은 날 수정)

`_make_card_anchor_check` docstring 이 그 빈 튜플을 **의도적으로** 설명하고 있었다:

> *"재확인 프레임을 주지 않는다(`retry_frames=()`). 09-06 j8g 라이브 `moved=0/15` —
> 재확인이 카드를 구제한 적이 한 번도 없다(틀린 좌표는 이웃 프레임에서도 틀리다).
> 게다가 이 두 경로는 이미 관절별 confidence 최대 프레임을 스스로 고른다."*

**측정 근거(라이브 15건 중 구제 0)가 있는 설계 결정**이지 빠뜨린 것이 아니다.
내가 함수 본문만 보고 docstring 을 안 읽은 채 결함이라 불렀고 belle 에게도 그렇게
보고했다 — 철회한다.

**다만 A 가 걱정하던 것(단일 판독으로 지움)은 B 가 그대로 덮는다** — B 의 2단이
곧 "두 번째 의견"이고, 이웃 프레임이 아니라 **같은 프레임에 다른 질문**을 던지므로
j8g 가 반증한 방식(이웃 프레임 재확인)과 다르다.

## ★ 결함 B — 리포가 "더 정확하다"고 적어둔 2단이 운영에 없다

게이트가 눈에게 던지는 질문(`_CLAIM_QUESTION["part"]`) 원문:

> **"사진 정중앙에 가장 크게 보이는 신체 부위는 무엇입니까?"**

**"정중앙에"(위치)와 "가장 크게 보이는"(크기)이 충돌한다.** 역립·접힌 자세에서
어깨 18% 크롭(`ANCHOR_CHECK_CROP_FRAC=0.18`)에는 **머리가 어깨보다 크게** 들어온다.
눈은 질문대로 "head"라고 **정확히** 답하고, 게이트는 그것을 **"좌표가 틀렸다"로 읽어
멀쩡한 표식을 지운다.** 계기가 재는 것은 *두드러짐*인데 게이트는 *위치*로 읽는다.

**리포는 이미 이걸 알고 있다.** `card_photo_audit.needs_mark_query` 주석 원문:

> *"표시 질문이 정중앙 질문보다 카드가 가리키는 지점에 정확하다"*

그래서 **2단 설계**가 있다 — 1단(`part`)이 통과가 아니고 표시가 있으면
2단(`mark_part`, *"원의 중심이 놓인 부위"*)으로 다시 묻고 `adjudicate` 로 종결.

**그 2단은 `backend/scripts/audit_card_photos.py`(오프라인 감사)에만 있다.**
운영 게이트(`verify_anchor_side`, pipeline 3곳에서 호출)는 **1단만으로 지운다.**

증거 정합: 지운 5건 중 `head` 2건이 **역립 자세**이고, 그중 하나는 belle 이
**같은 관절의 반대 측을 "맞음"으로 판정**했다.

## 수리안

| | 무엇 | 비용 | 위험 |
|---|---|---|---|
| ~~A~~ | ~~`retry_frames=()` 를 채운다~~ | — | **철회** — 결함 아님(위 참조) |
| **B** | 지우기 **직전에** 2단(`mark_part`)을 묻고 둘 다 mismatch 일 때만 지운다 (`adjudicate` 계약 그대로) | 지울 뻔한 패널당 +1 질의 | 낮음 — 1단 보정(36패널 계기)은 **안 건드린다** |

★ **재튜닝이 아니다.** `ANCHOR_CHECK_CROP_FRAC=0.18` 과 1단 질문은 36패널 측정의
계기값이라 손대지 않는다([[panel-measuring-instrument-must-declare-its-window]]).
B 는 1단이 **mismatch 라고 한 뒤**에만 개입한다.

## 아직 모르는 것

**지워진 5건이 실제로 맞는 표식이었는지는 확인 못 했다.** 지워진 패널은 표식이
안 그려져 나오므로 belle 이 볼 그림이 없다. 수리 후 같은 영상을 다시 돌려
**전/후 카드를 belle 에게 나란히** 보이는 것이 확인 경로다.


---

## 구현 (2026-09-18)

**B 만 넣었다.** A 는 철회.

- `card_gates.eye_part_token` 에 `claim` 파라미터 추가 — `"part"`(기본, 1단) /
  `"mark_part"`(2단). 어휘도 함께 갈린다(`PART_VOCAB` / `MARK_VOCAB`).
- `pipeline/app.py::_make_card_anchor_check` — `suppressed` 직전에만 2단:
  `mark_crop`(링 그린 크롭) → `eye_part_token(claim="mark_part")` → `cpa.adjudicate`.

**처분 규칙 (셋을 구분한다):**

| 2단 결과 | 처분 | 근거 |
|---|---|---|
| `ok=True` (mark_in_expected) | **지우지 않음** | 1단은 인접 맥락이었다 |
| `ok=False` (mark_elsewhere) | 지움 | 사진이 정말 다른 부위를 가리킨다 |
| `ok=None` (못 읽음·표시 불일치) | **지우지 않음** | 감사 불가는 불일치가 아니다 |
| **2단 자체가 불가**(키 부재·크롭 실패) | 지움 (1단 유지) | 2단 증거 0 — 인프라 장애가 표시를 되살리면 안 된다 |

★ 마지막 줄이 **테스트가 잡아준 것**이다. 처음엔 "2단을 못 물으면 1단을 따른다"고
주석에 적어놓고 코드는 구제하고 있었다(`mark_unobserved` → `ok=None` → 유지).
기존 테스트 2건이 그 어긋남을 바로 잡아냈다.

**계기 무접촉 확인:** `ANCHOR_CHECK_CROP_FRAC=0.18`, 1단 질문 원문, `anchor_verdict`,
`ANCHOR_CHECK_ROUNDS=3` 전부 그대로다. 2단은 1단이 mismatch 라고 **한 뒤에만** 돈다.

**로그:** `fault_zoom_anchor_stage2 ... mark=<토큰> adjudicated=<사유> disposition=kept|suppressed`
집계 키 `mark_calls` / `stage2_rescued` / `stage2_confirmed` / `stage2_unavailable`.

**테스트:** `backend/tests/test_pipeline_card_anchor_check.py` §⑤ 4건 신규
(구제 / 확정 / 못 읽음 구제 / 2단 불가 시 1단 유지) + 기존 스텁을 `claim` 대응으로
고쳐 **기존 테스트가 실제 2단 흐름을 타게** 했다(고치기 전에는 스텁이 `claim` 을
못 받아 예외로 빠지면서 "2단 불가" 경로만 타고 있었다 — 통과하고 있었지만 잠그는
대상이 아니었다).

## 남은 확인 — 라이브

**지워졌던 5건이 실제로 구제되는지는 아직 모른다.** 지워진 패널은 그림이 없어
비교 대상이 없다. 확인 경로 = Pod 에서 같은 영상 재분석 → `stage2_rescued` 로그 +
전/후 카드를 belle 에게 나란히.
