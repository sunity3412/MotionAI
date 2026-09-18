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

## ★ 결함 A — 재시도가 구조적으로 죽어 있다

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
| **A** | `app.py:3518` 의 `retry_frames=()` 를 실제 후보로 채운다 | 눈 호출 최대 ×3 | 낮음 — 이미 설계된 경로를 살리는 것 |
| **B** | 지우기 **직전에** 2단(`mark_part`)을 묻고 둘 다 mismatch 일 때만 지운다 (`adjudicate` 계약 그대로) | 지울 뻔한 패널당 +1 질의 | 낮음 — 1단 보정(36패널 계기)은 **안 건드린다** |

★ **재튜닝이 아니다.** `ANCHOR_CHECK_CROP_FRAC=0.18` 과 1단 질문은 36패널 측정의
계기값이라 손대지 않는다([[panel-measuring-instrument-must-declare-its-window]]).
B 는 1단이 **mismatch 라고 한 뒤**에만 개입한다.

## 아직 모르는 것

**지워진 5건이 실제로 맞는 표식이었는지는 확인 못 했다.** 지워진 패널은 표식이
안 그려져 나오므로 belle 이 볼 그림이 없다. 수리 후 같은 영상을 다시 돌려
**전/후 카드를 belle 에게 나란히** 보이는 것이 확인 경로다.
