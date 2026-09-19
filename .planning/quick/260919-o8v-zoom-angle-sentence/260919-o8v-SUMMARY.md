---
id: 260919-o8v
title: 표시 억제가 각도까지 지우는 것을 멈춘다 (원만 지운다)
date: 2026-09-19
status: complete
tasks: 2/2
commits:
  - 2a1ec0c  fix(quick-260919-o8v) 억제를 원 마커로 좁힌다 + 시험 8항
  - 26b8330  docs(quick-260919-o8v) userMarked/refMarked 의미 개정 3-way lockstep
gates:
  backend_pytest: "4880 passed / 20 skipped / 0 failed (backend/.venv 직접 실행)"
  app_tsc: "clean"
---

# 요약 — 판정 먼저

**됐다.** 기계 눈이 "이 패널에서 부위를 못 찾겠다"고 말했을 때, 종전에는 **각도까지**
지웠다. 이제 **원 마커만** 지운다. 각도를 그린 패널은 되돌리지 않고, 그 측 인증
(`userMarked`/`refMarked`)도 True 로 남는다.

belle 2026-09-18 규칙 2 — 09-06 원문 "사진 **대신** 각도"의 "대신"을 "**함께**"로
개정한 그 결정의 배선이다. 게이트가 사진을 없앨 권한이 없듯(규칙 1) 각도를 없앨
권한도 없다.

**채점은 한 줄도 안 건드렸다.** `card_gates.py` 0줄 — 게이트가 **무엇을 억제할지**는
그대로이고, 억제됐을 때 **무엇을 지울지**만 바꿨다.

---

## 무엇을 했나

### Task 1 — 억제를 원 마커로 좁힌다 (`2a1ec0c`)

`fault_zoom.py` 억제 블록 1곳 + docstring 1곳. 드로잉 로직·게이트 판정 무접촉.

```
억제됐다 ∧ 각도/사이각을 그렸다  → 되돌리지 않는다 (지울 원이 없다). 플래그 True 유지.
억제됐다 ∧ 각도가 없다           → 종전대로 무표시 판으로 되돌리고 플래그 False.
```

되돌릴 필요가 없는 근거는 코드에 이미 있었다: 각도와 원(·화살표)은 **배타적**이다
(`if u_drew_legs or u_drew_angle: _mark(circle=False)`). 각도를 그린 패널에는 지울
원이 애초에 없다. 그래서 새 스냅샷을 뜰 필요 없이 **되돌리기를 건너뛰기만** 하면 됐다.

`kept_angle=` 을 억제 로그에 붙였다 — 라이브에서 이 변경이 실제로 발화하는지
(억제 ∧ 각도-그림 교집합)를 사후에 셀 수 있는 유일한 수단이다.

**덤으로 닫힌 구멍:** 각도 베이크는 `_u_ok and _r_ok` 양측 대칭이 불변식인데, 종전
억제는 한쪽만 걸리면 그 쪽 각도만 지워 **한 패널만 각도**인 비대칭을 만들고 있었다.
이제 구조적으로 양측 보존이다.

### Task 2 — 3-way lockstep 등재 (`26b8330`)

새 필드 0. 바뀐 것은 기존 두 필드의 **의미**다 — `userMarked`/`refMarked` 가
"억제되면 무조건 false" 가 아니게 됐다. 네 면이 같은 말을 하게 맞췄다:
`fault_zoom` docstring · `contract.md §11.9/§11.11` · `pipeline/app.py` 주석 ·
`analysis.ts` JSDoc. contract 새 절 신설 0(기존 절 개정만), 중복 §11.11 번호 무접촉.

**앱 런타임 diff 0줄** — 주석뿐이다. `USER_UNMARKED_NOTE`/`REF_UNMARKED_NOTE` 는
이번 변경으로 **덜 뜨게** 될 뿐이다(각도가 살아 플래그가 True 가 되므로).

---

## 시험 — 무엇을 잠갔나

### 신규 8항 (`backend/tests/test_fault_zoom_suppress_keeps_angle.py`)

| # | 잠그는 것 | 변경 전 |
|---|---|---|
| ① | 학생 억제 → `userMarked True` + 왼쪽 패널 브랜드 픽셀 > 0 | **FAIL** |
| ② | 기준 억제 → `refMarked True` + 오른쪽 패널 픽셀 > 0 | **FAIL** |
| ③ | 양측 억제 → 둘 다 True + 양 패널 픽셀 > 0 + `png != pngPlain` | **FAIL** |
| ④ | 장수 불변 (belle 규칙 1) | PASS |
| ⑤ | **회귀 가드** — 원만 그리던 카드(`hand`=`unmapped`)는 종전대로 False + 픽셀 0 | PASS |
| ⑥ | advisory(criterion 없음 → 각도 경로 미진입) 무변경 | PASS |
| ⑦ | `suppress_marks` 인자 입구도 같은 규칙 | **FAIL** |
| ⑧ | `pngPlain` 무접촉 — 억제 여부와 무관하게 양 패널 픽셀 0 | PASS |

RED 단계에서 ①②③⑦ 이 정확히 계획대로 FAIL 했다(4 failed / 4 passed). 구현 후 8/8 PASS.

⑤ 가 이 단위의 경계를 지키는 시험이다 — **없던 각도를 지어내지 않는다.** `unmapped`
/`*_crop_relaxed` 카드는 각도를 **잴 수 없어서** 안 그린 것이라, 억제됐다고 각도를
만들면 "재지 않은 것을 쟀다"고 말하는 셈이다. 두 억제 사유를 섞는 구현을 즉시 깨뜨린다.

### 기대값 정정 3건 — 시험 삭제 0, 증인 교체

`tests/test_fault_zoom_anchor_check.py` 의 3건은 **belle 이 뒤집은 바로 그 동작**을
플래그로 잠그고 있었다. 이 파일의 픽스처 카드 2장은 `angle_bake=drawn` 이다(접미사
shoulder/knee + conf 0.9 — 2026-09-19 로그 직접 실측). 그래서 플래그가 뒤집힌다.

플래그가 더 이상 "어느 측이 억제됐는가"의 증인이 아니므로 **증인을 억제 로그로
옮겼다** (`_suppressed_sides_by_criterion` 헬퍼 신설). 각 시험이 원래 지키려던 성질은
그대로 살아 있다:

| 시험 | 종전 증인 | 새 증인 |
|---|---|---|
| `..._suppresses_only_returned_side` | `userMarked False` | 억제 로그 `sides` 가 `{"user"}` 뿐 |
| `..._can_suppress_per_card` | `right_knee refMarked False` | 로그에 `right_knee` 만 오르고 `left_shoulder` 는 아예 안 오른다 |
| `..._unions_with_suppress_marks` | 양쪽 False | 로그 `sides` 가 전 카드 `"user,ref"` (인자 ∪ 콜백) |

정정 지점마다 **왜 뒤집혔는지** 한 줄 주석을 달았고, 모듈 docstring ② 항에 개정
블록을 붙였다. 선례: `phase33/test_zoom_join_joint_exact.py:199` "기대값만 갱신(테스트 삭제 0)".

### 계획이 "안 깨져야 한다"고 지목한 시험 — 전부 통과

- `test_fault_zoom.py::test_suppress_marks_user_keeps_ref_marks` — 그 픽스처의 report
  joints 는 `(left_knee, right_knee, left_hip)` 이라 `ANGLE_BAKE_MAP["knee"]=(ankle,hip)`
  의 `left_ankle` 이 없다 → 각도 미성립 → 종전대로 False + 픽셀 0.
- advisory 3건 — `criterion_units` 미전달 = 각도 경로 미진입.
- `phase33/test_zoom_join_joint_exact.py:423` 양측 억제 → `png == pngPlain` 그대로 성립.

즉 계획의 사실 1/4 유도가 코드와 맞았다. **멈출 사유 없음.**

---

## 게이트 (직접 실측 — 서브에이전트 수치 아님)

```
backend/.venv/bin/python -m pytest -q
  → 4880 passed, 20 skipped, 0 failed  (48s)
    기준선 4872 + 신규 8 = 4880. 회귀 0.

app/ npx tsc --noEmit
  → No errors found
```

Task 2 편집 후 전량 재실행해 같은 수치를 확인했다.

## 무접촉 확인 (`git diff` 실측)

`git diff HEAD~2 HEAD --name-only` = 6파일. 다음은 **한 줄도 안 바뀌었다**:

- `card_gates.py` (파일 자체가 diff에 없음)
- 점수/감점 경로 — `dimensions.py` · `kismam.py` · `assemble.py` · `deduction*`
- `fault_zoom.py` 의 `_draw_*` · `_side_crop` · `_compose` · `_mark` — diff 전체에서
  이 이름이 붙은 `+`/`-` 줄 **0건** (grep 실측)
- `pngPlain` 합성부
- 앱 `.tsx` 런타임 코드 · UI 문구 상수 (앱 diff = 주석 7줄이 전부)

`fault_zoom.py` diff 위치는 두 곳뿐이다 — docstring(3041~3050)과 억제 블록(3922~3958).

---

## ★ belle 판정 대기 1건 (이번엔 손대지 않았다)

**기존 UI 문구 2개가 belle 규칙 3과 충돌할 수 있다.** 실물:

```
app/src/components/DeductionDetailSheet.tsx:136
  REF_UNMARKED_NOTE  = '오른쪽 사진에는 관절 위치를 확인하지 못해 표시를 넣지 않았어요'
app/src/components/DeductionDetailSheet.tsx:138
  USER_UNMARKED_NOTE = '왼쪽 사진에는 관절 위치를 확인하지 못해 표시를 넣지 않았어요'
```

belle 09-18 규칙 3은 "**확인 안 됨** 류 문구는 쓰지 않는다 — 수강생에게 우리
불확실성을 방송해 신뢰를 깎는다"이다. 위 두 문장은 문자 그대로 "확인하지 못해"다.
그러나 이번 지시의 제약은 **신설 금지**이고, 두 문장은 quick-260802-tie/260903-upx
에서 **승인받아 들어간 기존 문구**다. 승인된 카피를 belle 의 명시 지시 없이 지우는
것은 승인이 생산 경로에 붙는다는 원칙 위반이다.

→ **belle 께 물을 것:**
"이 두 문장도 규칙 3에 걸립니까? (이번 변경으로 발화 빈도는 줄지만 0은 아닙니다)"

---

## 이 단위가 증명하지 못하는 것 (정직하게)

- **라이브에서 몇 장을 살리는지 모른다.** 오늘 실측은 doc 47건 / 카드 192장 중 게이트
  상태를 가진 카드가 24장이고 `userMarked` False 17건 · `refMarked` False 27건인데,
  그 False 중 **몇 개가 "각도를 그렸다가 억제로 지워진 것"인지는 doc 에 흔적이 없다.**
  그래서 `kept_angle=` 로그를 붙였다. Pod 은 내려가 있고 실증은 10월 중순으로 밀렸다.
  이 단위는 **합성 입력 단위 시험까지**다 — "배선했다"를 "값이 맞다"로 말하지 않는다.
- **각도가 옳은 자리에 그려졌는지는 여전히 안 잰다.** 기계 눈이 "부위를 못 찾겠다"고
  한 패널에 각도를 남기는 것이 이번 결정이다. 그 각도의 좌표가 맞는지는 별건이고
  근본 원인은 좌표 정확도다. 좁은 크롭 표식 위치는 내가 판정하면 틀린다 — belle 눈으로만 닫힌다.
- **저신뢰(conf<0.5) 패널은 그대로 사진만 남는다.** 역립 doc 은 전 관절 0.33~0.48 이라
  이 경로로 떨어진다. 이번 단위는 그 칸을 건드리지 않았다.
- **`refMatched=true` 거짓 보증은 그대로 살아 있다** (카드 192장 전수 False 0장,
  quick-260919-mhl 실측). 이 단위는 그 거짓말을 고치지 않는다.

---

## 다음 단위 후보

1. 위 UI 문구 2개 belle 판정 → 답에 따라 제거 또는 유지.
2. `kept_angle=` 로그를 Pod 기동 시 수확해 **억제 ∧ 각도-그림** 교집합 실측 → belle 보고.
3. 억제된 패널의 각도 좌표 정확도 — belle 눈 대조.
4. `refMatched=true` 거짓 보증 제거 (`atMatched` 형제 규칙 적용).

---

## Self-Check: PASSED

- `backend/tests/test_fault_zoom_suppress_keeps_angle.py` — FOUND
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — FOUND (수정)
- `backend/tests/test_fault_zoom_anchor_check.py` — FOUND (수정)
- `docs/contract.md` · `backend/functions/pipeline/app.py` · `app/src/types/analysis.ts` — FOUND (수정)
- 커밋 `2a1ec0c` — FOUND
- 커밋 `26b8330` — FOUND
- 삭제된 추적 파일 0건 (`git diff --diff-filter=D HEAD~2 HEAD` 공집합)
