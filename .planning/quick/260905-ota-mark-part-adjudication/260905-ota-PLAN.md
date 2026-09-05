---
phase: quick-260905-ota
status: planned
subsystem: analysis-card-photo-audit
tags: [fault-zoom, machine-eye, audit]
created: 2026-09-05
requires: [quick-260905-mvm]
---

# quick-260905-ota: 표시 위치로 경계 판정 — 감사 2단화

## 왜

mvm 감사(09-03 라이브 21장, 4런)에서 **8장 가운데 3장이 인접 경계**로 걸렸다:
목↔어깨(pdshape 오른어깨 ref = `neck`), 무릎↔엉덩이(클라임 참고 왼골반 ref = `knee`), 그리고
겨드랑이↔팔꿈치. 여기서 허용 집합을 넓히면 이번 21장 숫자는 줄지만 **잡으려던 종류
("팔꿈치 카드가 등허리를 보여준다")까지 같이 놓친다.** mvm 은 그래서 넓히지 않고 남겨뒀다.

경계를 감으로 정하지 않는다. 구분할 **측정**이 있다: 지금 눈에게 묻는 것은 "crop 정중앙에 무엇이
보이는가" 뿐인데, **표시가 있는 카드에서 정확한 질문은 "빨간 표시가 어느 부위에 놓였는가"** 다.
crop 은 관절 주변 맥락을 일부러 담으므로 정중앙이 이웃 부위로 읽히는 것은 정상이고, 표시는
그 카드가 실제로 가리키는 지점이다.

## 설계 — 2단 판정 (기존 게이트 관례 승계)

```
1단(싼 선별)  패널마다 "정중앙 부위" N회 → 최빈 토큰. 허용 집합 안 → 통과, 끝.
2단(정밀 판정) 1단 탈락 패널만:
   · 그 패널에 표시가 있으면 → "빨간 표시가 놓인 부위" N회 → 최빈 토큰
       허용 집합 안  → 통과 (crop 중앙은 인접 맥락이었을 뿐)
       허용 집합 밖  → 확정 불일치 (사진이 다른 부위를 가리킨다)
   · 표시가 없으면    → 판정 불가 확정 — "가리키는 표시가 없고 중앙도 그 부위가 아니다"
```

호출 비용은 1단 그대로 + 탈락분에만 추가(21장 기준 8장 × 1~2패널). 전수 2배가 아니다.
표시 유무는 doc 의 `userMarked`/`refMarked` 를 쓴다 — 09-05 감사에서 이 두 필드는 21장 전부
실제 그림과 일치함이 확인됐다(그 필드는 정직하다).

★ 승계 규칙 불변: 질문에 좌우·관절 이름 0. 눈은 "무엇이 보이는가"만, 대조는 코드가.

## 하는 일

### Task 1 — `mark_part` claim 추가 (card_gates)

- `_CLAIM_QUESTION["mark_part"]`: "사진 안의 빨간색 표시(선·원·화살표)는 어느 신체 부위에
  놓여 있습니까? 표시가 없으면 no_mark." + `part` 와 같은 13개 부위 어휘. 좌우·관절명 0.
- `_CLAIM_ENUM["mark_part"]` = `PART_TOKENS + ["no_mark", "unclear"]`.
- `_eye_verdict("mark_part")` = `part` 와 동형 — 토큰을 읽어냈는지만 (`no_mark` 도 읽어낸 것).
- 기존 claim 4종(bent/extended/off_pole/part)·`machine_eye` byte 무변경, 테스트로 고정.

`verify`: 신규 질문에 좌우 어휘 0 단언 + enum lockstep 테스트.
`done`: `eye_judge(panel, "mark_part")` 가 부위 토큰 또는 `no_mark` 를 준다.

### Task 2 — 2단 판정을 순수 함수로 (card_photo_audit)

`adjudicate(expected, center_token, mark_token, *, marked) -> dict`
- `center_token ∈ expected` → `{"ok": True, "by": "center"}`
- 아니고 `marked` 이고 `mark_token ∈ expected` → `{"ok": True, "by": "mark"}`
- 아니고 `marked` → `{"ok": False, "by": "mark", "reason": "mark_elsewhere"}`
- 아니고 `not marked` → `{"ok": False, "by": "none", "reason": "no_mark_and_center_elsewhere"}`
- `mark_token == "no_mark"` 인데 doc 은 표시 있다고 함 → `{"ok": None, "reason": "mark_disagreement"}`
  (판정 불가 — doc 과 그림이 어긋난 것 자체가 보고 대상)
- `unclear`/`error` → `ok=None`, `unreadable`

기존 `audit_card` 는 유지하고 `adjudicate` 를 얹는다(mvm 테스트 무회귀).

`verify`: 테스트 — 각 분기 + 09-05 경계 3종을 관측값 하드코딩으로.
`done`: 순수 함수만으로 4가지 결말이 구분된다.

### Task 3 — 스크립트 2단화 + 21장 재측정

`backend/scripts/audit_card_photos.py`
- 1단 탈락 패널에만 `mark_part` 질의 추가(같은 N회 모달).
- 출력에 `by=center|mark|none` 과 사유를 싣고, 마지막 줄을
  `card_photo_audit total=N mismatched=M unresolved=K` 로 확장.
- 09-03 라이브 6문서 21장에 **2회** 실행해 재현성 확인.

`verify`: 두 런의 카드 판정 일치율 + belle 이 먼저 찾은 2장이 여전히 불일치인지.
`done`: 경계 3종이 측정으로 갈린다 — 통과면 통과 사유(`by=mark`)가, 불일치면 표시가 어디 있는지가 남는다.

### Task 4 — 측정 결과로 허용 집합 확정

Task 3 결과를 보고 `expected_parts` 를 **필요한 만큼만** 조정한다. 조정하면 근거(어느 카드에서
표시가 어디에 있었는지)를 주석에 날짜와 함께 남긴다. 조정할 이유가 없으면 그대로 두고
"측정 결과 조정 불필요"를 SUMMARY 에 남긴다. **이번 1벌에 맞춰 넓히는 것 금지** — 표시 측정이
허용을 지지할 때만.

`done`: 집합 변경이 있든 없든 그 판단의 근거가 코드/SUMMARY 에 박혀 있다.

## 하지 않는 일

- 파이프라인 부착(분석 시점 게이트)은 여전히 다음 단위.
- 게이트 미달 좌표로 crop 하지 않게 하는 원인 수리도 별도.
- 사진별 ○× 를 belle 에게 묻지 않는다 (09-03 규칙).

## 게이트

- backend pytest 전체 — 직전 기준선 **4627 passed / 0 failed / 20 skipped**
- 신규 질문에 좌우 어휘 0
- 21장 2회 재실행에서 카드 판정 재현
