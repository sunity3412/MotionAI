---
phase: quick-260905-ota
plan: "01"
subsystem: analysis-card-photo-audit
tags: [fault-zoom, machine-eye, audit, adjudication]
requires: [quick-260905-mvm]
provides:
  - "card_gates claim 'mark_part' — 카드 사진에서 '빨간 표시가 놓인 부위' 토큰(13 부위 + no_mark)만 읽는 관측 claim (좌우·기대 관절 0)"
  - "card_photo_audit.adjudicate / needs_mark_query / card_verdict — 2단 판정 순수 함수 (by=center|mark|none, 결말 4종 + 판정 불가)"
  - "scripts/audit_card_photos.py 2단화 — 1단 탈락+표시 패널에만 mark_part, marked_flags(게이트 B), --replay, 마지막 줄 total/mismatched/unresolved"
affects: [card_gates(추가만), card_photo_audit(추가만), audit_card_photos]
tech-stack:
  added: []
  patterns: ["싼 선별 → 탈락분에만 정밀 질문 (기존 게이트 관례) — 비용은 1단 + 탈락 패널분", "경계는 감이 아니라 측정으로 — 허용 집합 조정은 표시 측정이 지지할 때만", "판정 규칙이 순수하면 옛 런을 --replay 로 같은 규칙에 다시 태운다 (눈 호출 0)"]
key-files:
  created:
    - .planning/quick/260905-ota-mark-part-adjudication/evidence/ (run1·run2 로그+JSON, replay 로그+JSON, compare_run1_run2.txt, smoke_powerspin.json)
  modified:
    - backend/shared/python/sunity_shared/analysis/card_gates.py
    - backend/shared/python/sunity_shared/analysis/card_photo_audit.py
    - backend/scripts/audit_card_photos.py
    - backend/tests/test_card_gates.py
    - backend/tests/test_card_photo_audit.py
    - backend/tests/test_audit_card_photos_script.py
decisions:
  - "expected_parts 무변경 — 표시 측정 8패널 중 집합 밖 표시는 전부 원거리(어깨 카드에 knee·thigh·hip·head/neck). 경계 3종은 잴 표시가 없거나(오른어깨 ref refMarked=False, 참고 왼골반 ref 게이트 B 무마킹·눈 no_mark 3/3 ×2런) 1단 통과(엘보 ref elbow 16/16)"
  - "1단 못 읽음(unclear 동률) 패널도 표시가 있으면 2단으로 — 못 읽음은 통과가 아니고 표시 질문이 정중앙 질문보다 카드가 가리키는 지점에 정확하다 (엘보 왼어깨 ref: run1 unclear→mark hip 로 해소)"
  - "표시 flag 부재(참고 카드) = 게이트 B: 기준 측 무마킹 — mvm 의 양측 True 기본값은 오류(Rule 1). 2단 실측이 그 패널에 no_mark 3/3 ×2런을 답해 드러남"
  - "기존 claim 4종·limb 접미/enum 은 sha256 핀으로 byte 고정 — 질문을 의도적으로 바꾸는 단위는 해시와 근거를 같이 갱신"
requirements-completed: []
metrics:
  duration: "약 60분 (08:53Z → 09:53Z, 그중 라이브 2런 38분)"
  completed: "2026-09-05"
  tasks: "4/4"
  pytest: "4655 passed / 0 failed / 20 skipped (기준선 4627/0/20 + 신규 28)"
---

# Quick 260905-ota: 표시 위치로 경계 판정 — 감사 2단화 Summary

**One-liner:** 카드 감사에 2단(1단 정중앙 탈락 + 표시 있는 패널에만 "빨간 표시가 놓인 부위")을 얹어 mvm 의 인접 경계 3종을 측정으로 갈랐다 — 09-03 라이브 21장 × 2런에서 카드 판정 21/21 재현, 최종 `total=21 mismatched=7 unresolved=0` 양 런 동일, belle 2장 유지, 표시가 살린 카드 2장. 허용 집합은 측정이 지지하지 않아 **무변경**. 참고 카드 기준 측 표시 flag 기본값 오류(게이트 B) 1건 수리. backend 4655/0.

## 판정: 된다. 경계 3종이 측정으로 갈렸고, 갈린 결과가 집합을 넓히라고 말하지 않는다.

- **된다:** 같은 21장을 2번 돌려 카드 판정 21/21 일치 (정중앙 토큰 37/42, 표시 토큰 5/8 패널). 마지막 줄이 양 런 `card_photo_audit total=21 mismatched=7 unresolved=0` (replay 후; 원 런은 `mismatched=6 unresolved=1` — 아래 Deviations 1).
- **belle 이 먼저 찾은 2장**은 두 런 다 불일치이고 표시 측정이 그 이유를 말한다: pdshape 6.1s 오른팔꿈치 = 표시 없음 + 정중앙 등허리(`False/none`), 파워스핀 왼어깨 = 표시가 무릎(`knee` 3/3, `False/mark:mark_elsewhere`).
- **2단이 살린 카드 2장** (정중앙은 인접 맥락이었을 뿐): pdshape 왼무릎 ref 정중앙 `elbow` 3/3 → 표시 `knee` → 통과 `by=mark` (mvm 에서 3/4 런 불일치였던 카드), 엘보 오른어깨 ref 정중앙 `elbow` 2:1 → 표시 `shoulder` → 통과 `by=mark`.
- **안 되는 것 / 남는 것:** 경계 3종 가운데 2종은 표시가 없어 2단이 잴 것이 없다(오른어깨 ref `refMarked=False`, 참고 왼골반 ref 는 정책상 무마킹). 그 2장은 "표시 없고 정중앙도 아님"으로 확정될 뿐 사진이 그 부위를 보여주는지는 이 계측기가 답하지 않는다 — 판정은 belle 몫(사진별 ○× 는 묻지 않는다, 09-03 규칙).

## 라이브 검증 — 09-03 라이브 6문서 21장, `gemini-3.8-flash`, temperature 0, 3회 최빈

문서: mvm 과 동일 (`verifyupx0903b/bf929095…` pdshape 6 + `verifyupx0903/{c357f6b4 클라임 3, f5e8e134 파워스핀 2, 363fcea9 엘보 6, fb695059 킵업 1, 4cf49d80 피터팬 3}`).

| 런 | 스크립트 | total | mismatched | unresolved | 2단 패널 | 소요 |
|---|---|---|---|---|---|---|
| run1 (원) | `07225636` | 21 | 6 | 1 | 6 (+18 호출) | 17.0분 |
| run2 (원) | `07225636` | 21 | 6 | 1 | 8 (+24 호출) | 20.9분 |
| run1 replay | `e50a8ac5` marked_flags | 21 | **7** | **0** | (재판정만) | 0 |
| run2 replay | `e50a8ac5` marked_flags | 21 | **7** | **0** | (재판정만) | 0 |

원 런과 replay 의 차이는 클라임 참고 왼골반 ref 한 패널 — 원 런은 mvm 기본값(참고 카드 기준 측 표시 있음)으로 2단을 물었고 눈이 `no_mark` 3/3 ×2런 → `mark_disagreement`(unresolved). 게이트 B(참고 카드 기준 측 무마킹 정책)로 기본값을 고치면 2단 없이 `False/none` 확정 → mismatched 7. 카드 집합은 mvm run4 의 8장에서 pdshape 왼무릎(표시가 살림)을 뺀 것과 정확히 같다.

**카드별 (replay 기준, run1 | run2; 결말 = `ok/by:reason`):**

| 카드 | user 정중앙→표시 | ref 정중앙→표시 | 결말 | mvm | 비고 |
|---|---|---|---|---|---|
| pdshape [0] 오른팔꿈치 6.1s | back_waist→- `False/none` ×2 | hand ok | **MISMATCH** ×2 | M | belle #1. userMarked=False — 표시 없음 |
| pdshape [1] 왼팔꿈치 | elbow | elbow | ok ×2 | ok | |
| pdshape [2] 왼무릎 | knee | run1 knee 2:1 (1단 통과) / run2 elbow 3:0→**knee** 2:1 `True/mark` | ok ×2 | M(3/4) | **표시가 살림** — 정중앙이 팔로 읽히는 프레임, 표시는 무릎 |
| pdshape [3] 오른어깨 | shoulder | neck 2:1→- `False/none` ×2 | **MISMATCH** ×2 | M | 경계 목↔어깨. refMarked=False — 잴 표시 없음 |
| pdshape [4] 왼골반 | back_waist | back_waist | ok ×2 | ok | |
| pdshape [5] 참고 왼어깨 | head 3/3→**neck** (2:1 / 3:0) `False/mark` | chest ok | **MISMATCH** ×2 | M | 원이 얼굴·목 위 |
| 클라임 [0] 오른무릎 | knee | knee | ok ×2 | ok | |
| 클라임 [1] 참고 왼골반 | thigh ok | knee 3/3→(no_mark 3/3) `False/none` ×2 | **MISMATCH** ×2 | M(3/4) | 경계 무릎↔엉덩이. 참고 카드 기준 측 = 게이트 B 무마킹, 눈도 no_mark |
| 클라임 [2] 참고 왼어깨 | shoulder | chest | ok ×2 | ok | |
| 파워스핀 [0] 다리 뻗음 | hip | hip | ok ×2 | ok | |
| 파워스핀 [1] 왼어깨 | knee (2:1 / 3:0)→**knee** (2:1 / 3:0) `False/mark` | armpit ok | **MISMATCH** ×2 | M | belle #2. 각도선 꼭짓점이 든 다리의 무릎 |
| 엘보 [0] 오른팔꿈치 | shoulder ok | elbow 3/3 ×2 (1단 통과) | ok ×2 | ok | 경계 겨드랑이↔팔꿈치 — 눈 16/16 elbow, 대장 armpit 은 사람 판독 |
| 엘보 [1] 왼어깨 | thigh 3/3→**thigh** 2:1 / hip 2:1→**thigh** 3/3 `False/mark` | run1 unclear(3자)→**hip** 3/3 `False/mark` / run2 thigh 2:1→unclear(3자) `None` | **MISMATCH** ×2 | M | 양쪽 다 표시가 다리·골반. run1 은 1단 못 읽은 패널을 표시가 해소 |
| 엘보 [2] 오른어깨 | shoulder | run1 shoulder 2:1 / run2 elbow 2:1→**shoulder** 2:1 `True/mark` | ok ×2 | ok | **표시가 살림** |
| 엘보 [3] 왼골반 · [4] 오른골반 | hip | hip | ok ×2 | ok | |
| 엘보 [5] 참고 왼어깨 | head (3/3, 2:1)→**head** 2:1 ×2 `False/mark` | chest ok | **MISMATCH** ×2 | M | 원이 얼굴 위 |
| 킵업 [0] 벌림각 | thigh 3/3 / hip 2:1 | hip | ok ×2 | ok | 두 토큰 다 집합 안 |
| 피터팬 [0][1][2] | — | — | ok ×2 | ok | |

재현성: 카드 판정 21/21, 정중앙 토큰 37/42 (달라진 5 패널: pdshape 왼무릎 ref knee↔elbow, 엘보 왼어깨 user thigh↔hip / ref unclear↔thigh, 엘보 오른어깨 ref shoulder↔elbow, 킵업 user thigh↔hip — 전부 2단 또는 집합 안에서 흡수), 표시 토큰 5/8 패널 (2단이 한 런에만 돈 2 패널 + 엘보 왼어깨 ref 3자 동률 1). 사진: `/Users/Shared/sunity-card-audit-260905-ota/run{1,2}/` (42 패널씩, 리포 밖).

## 경계 3종의 측정 결말 (Task 4 근거)

| 경계 | 패널 | 측정 | 집합 조정 |
|---|---|---|---|
| 목↔어깨 | pdshape 오른어깨 ref (정중앙 neck 2:1 ×2) | `refMarked=False` — 잴 표시가 없다. 표시가 neck/head 로 읽힌 패널은 참고 왼어깨 2장(원이 얼굴 위)뿐이고 그것은 표시 전위 그 자체 — shoulder 에 neck 을 넣으면 그 카드가 `by=mark` 로 통과한다 (테스트 `test_widening_shoulder_to_neck_would_pass_face_circle_cards` 가 고정) | **없음** |
| 무릎↔엉덩이 | 클라임 참고 왼골반 ref (정중앙 knee 3/3 ×2) | 참고 카드 기준 측은 게이트 B 무마킹, 눈도 no_mark 3/3 ×2. hip 에 knee 를 넣으면 이 패널이 `by=center` 로 통과하지만 표시 측정이 지지할 길이 없다 — 이번 1벌을 깨끗하게 보이려는 조정 | **없음** |
| 겨드랑이↔팔꿈치 | 엘보 오른팔꿈치 ref | 눈 elbow 3/3 ×2 (mvm 포함 16/16) — 1단 통과, 2단 불필요. 대장의 armpit 은 사람 판독 | **없음** (집합이 이미 맞다) |

표시 측정 8패널 중 집합 밖 표시 = knee·thigh·hip·head/neck 이 전부 **어깨 카드**에 — 인접 확장으로 구제될 사례 0. 근거는 `card_photo_audit._KIND_PARTS` 주석(날짜 포함)과 테스트 `test_ota_0905_measured_marks`(두 런 일치 표시 토큰 6패널 핀)에 박제.

## Task Commits

1. **Task 1 — card_gates `mark_part` claim** — `59bb1e84` (feat)
2. **Task 2 — card_photo_audit `adjudicate` 2단 순수 함수** — `45e2df21` (feat)
3. **Task 3 — 스크립트 2단화 + 21장 2런** — `07225636` (feat) + `e50a8ac5` (fix, Deviations 1)
4. **Task 4 — 허용 집합 무변경 근거 박제** — `593fd19e` (docs)

## 한 일

### Task 1 (`59bb1e84`)
- `_CLAIM_QUESTION["mark_part"]` "사진 안의 빨간색(주황빛 빨강) 표시(선·원·화살표)는 어느 신체 부위에 놓여 있습니까? 선이면 꺾이거나 만나는 지점, 원이면 중심 … 13 부위 중립 나열 … 표시가 하나도 없으면 'no_mark', 분간이 안 되면 'unclear'." + `_LIMB_QUESTION`. 색 표기는 카드 렌더(`fault_zoom._BRAND` #FF4B33) 그대로.
- `_CLAIM_ENUM["mark_part"]` = part 13 + `no_mark` + `unclear` (15), `MARK_PART_TOKENS`/`NO_MARK`. `_claim_question` 은 part 와 같이 변형·힌트 미부착 통과, `_eye_verdict("mark_part")` = 읽어냈는가만 (no_mark 도 관측).
- 테스트 5: 좌우 어휘 0(왼/오른/좌/우측/left/right) + 힌트·변형 미부착, enum lockstep, 관측 전용 verdict, urlopen 가로채기로 요청 본문(질문·enum 15·temp 0·모델) 박제, **기존 claim 4종·limb 접미/enum sha256 핀**(mark_part 추가 직전 HEAD 01a13939 에서 계산). 기존 집합 단언에 mark_part 추가 1줄.

### Task 2 (`45e2df21`)
- `adjudicate(expected, center, mark, *, marked)` → `{ok, by, reason}`: `True/center`, `True/mark:mark_in_expected`, `False/mark:mark_elsewhere`, `False/none:no_mark_and_center_elsewhere`, 판정 불가 `None` (`mark_disagreement` 양방향, `unreadable`, `mark_unobserved`, `no_expectation`). `needs_mark_query`(표시 있음 + 1단 통과 아님), `card_verdict`(mismatch > unresolved > ok, 감사 불가 = unaudited). `audit_card` 무변경.
- 테스트 10: 분기 전수, 경계 3종(+팔↔다리) 관측값 하드코딩으로 두 결말 분기, 대장 5건이 2단 뒤에도 생존, `MARK_VOCAB == card_gates.MARK_PART_TOKENS`.

### Task 3 (`07225636`, `e50a8ac5`)
- `judge_panel(claim=part|mark_part)`, `modal_token(vocab)`(mark_part 는 no_mark 도 표), `audit_doc`: 1단 → `needs_mark_query` → 2단 → `adjudicate` → `card_verdict`. 로그 `user={center}→{mark|-} ok/by:reason`, `# mismatch cards` / `# unresolved cards`, 마지막 두 줄 `card_photo_audit unaudited=J tier2_panels=Q` / `card_photo_audit total=N mismatched=M unresolved=K`.
- 스모크(파워스핀 2장) → 2런(21장) `nohup` 순차 실행 (도구 백그라운드는 10분 상한이 있어 이관). 오프라인 테스트 6: 2단 호출이 탈락+표시 패널에만 (4장 fixture, 참고 카드 0회), mark 어휘 다수결, claim 전달, 표기, `marked_flags`, `replay_rows`.

### Task 4 (`593fd19e`)
- `_KIND_PARTS` 주석에 경계 3종의 측정 결말과 넓히지 않는 이유(잴 표시 없음 / 게이트 B / 1단 통과)를 날짜와 함께. 테스트: 두 런 일치 표시 토큰 6패널 핀, shoulder+neck 이면 얼굴 원 카드가 통과함을 고정, 참고 왼골반 fixture 를 정책(표시 없음)대로 정정.

## 계획과 다르게 한 것

**1. [Rule 1 - Bug] 참고(advisory) 카드의 표시 flag 기본값 — 기준 측은 게이트 B 무마킹**
- **발견:** run1 도중 참고 왼골반 ref 패널에서 눈이 `no_mark` 3/3 (run2 도 3/3). doc 을 열어 보니 `userMarked`/`refMarked` 는 **criterion 카드에만** 실린다 (contract §11.9/§11.11, `fault_zoom.py:3849` "legacy/advisory 는 키 부재"). 참고 카드는 게이트 B(`quick-260705-wbs`)로 학생 측만 그리고 기준 측은 무마킹이 정책인데 mvm 스크립트는 부재를 양측 True 로 읽었다 — mvm 의 클라임 참고 왼골반 `ref:mark_mismatch` 는 `ref:part_not_shown` 이어야 했고, plan 의 "이 두 필드는 21장 전부 실제 그림과 일치" 는 필드가 있는 15장에만 맞는 말이었다.
- **처리:** `marked_flags(card)` — 키가 있으면 그 값, 부재면 `(True, criterion is not None)`. 행에 `userMarkedRaw/refMarkedRaw` 보존, `--replay JSON` 으로 저장 토큰을 같은 규칙에 재판정(눈 호출 0). 두 런은 같은 스크립트 버전으로 끝까지 돌려 눈의 재현성을 재고, 수리 뒤 replay 로 양 런을 다시 셌다 (표: 6/1 → 7/0). 눈이 그 패널에 no_mark 를 답한 것 자체가 수리의 측정 근거.
- **파일:** `backend/scripts/audit_card_photos.py`, `backend/tests/test_audit_card_photos_script.py`. **커밋:** `e50a8ac5`.

**2. [해석] 1단 못 읽음(unclear 동률) 패널도 표시가 있으면 2단**
- plan 은 "1단 탈락 패널만" — 못 읽음을 탈락으로 볼지 판정 불가로 둘지 명시가 없었다. 못 읽음은 통과가 아니고 표시 질문이 정중앙 질문보다 카드가 가리키는 지점에 정확하므로(plan 의 2단 근거 그대로) 2단으로 보냈다. 실측: 엘보 왼어깨 ref run1 정중앙 3자 동률 → 표시 `hip` 3/3 → `False/mark` 로 해소 (mvm 의 unreadable 1건). 비용 +1 패널.

**3. [범위 유지] 허용 집합 무변경** — 위 "경계 3종의 측정 결말" 표. 조정 근거가 측정에 없어 두지 않았다.

## 검증 방식 (verify 대응)

- Task 1: `test_card_gates.py` 46 passed (기존 41 + 신규 5). 신규 질문 좌우 어휘 0 테스트 통과. 라이브 2런 mark_part 14패널 × 3회에서 `error` 0, 응답 근거 문장이 표시 형태(각도선 꼭짓점/원 중심)를 지칭.
- Task 2: `test_card_photo_audit.py` 32 passed (기존 15 + 신규 17). 순수 함수만으로 4 결말 분기.
- Task 3: 2런 카드 판정 21/21 일치, belle 2장 두 런 다 불일치. 로그·JSON·replay·비교 = `evidence/` (`compare_run1_run2.txt` 에 패널별 토큰·표·결말 양 런 나란히).
- Task 4: `_KIND_PARTS` 주석 + 테스트 2종.
- 게이트 `cd backend && .venv/bin/python -m pytest -q` → **4655 passed / 0 failed / 20 skipped** (45.6s). `rtk pytest` 는 시스템 pytest 라 venv 경로 사용.

## 다음 단위 후보 (이번 범위 밖 — plan "하지 않는 일")

- **파이프라인 부착:** 2단 규칙이 순수 함수라 분석 시점 게이트로 옮길 재료는 됐다. 비용은 카드당 6 호출 + 탈락 패널당 3. 불일치 시 처분(사진을 다른 순간으로 옮길지)은 별도 결정.
- **원인 수리 (게이트 미달 좌표로 crop 금지):** 걸린 7장의 공통 패턴이 더 또렷해졌다 — 어깨 카드 표시가 다리·골반·얼굴 위(파워스핀·엘보 왼어깨 양 패널·참고 왼어깨 2장), 표시 없는 카드의 정중앙이 등허리·목(pdshape 오른팔꿈치·오른어깨 ref). 참고 카드 기준 측은 정책상 표시가 없어 이 감사가 "그 부위가 보이는가"만 답한다 — 표시 없는 카드에 표시를 넣을지는 별개 결정.
- 눈의 세션 간 비결정 5/42 는 2단이 흡수했다(2장 구제). 단발 대신 3회 최빈 + 2단이 지금 계측기의 최소 형태.

## Known Stubs

없음.

## Threat Flags

없음 — 새 네트워크 표면 없음(기존 Gemini generateContent·Firestore read·S3/presigned GET 재사용), Firestore 쓰기 0, 인물 이미지는 리포 밖(`/Users/Shared/sunity-card-audit-260905-ota/`).

## Self-Check: PASSED

- 수정 파일 6건·SUMMARY·evidence 5건 존재, 태스크 커밋 5건(`59bb1e84`·`45e2df21`·`07225636`·`e50a8ac5`·`593fd19e`) git log 에 존재, replay 로그 양쪽 마지막 줄 `total=21 mismatched=7 unresolved=0` 확인.
- 미커밋 = `.planning/quick/260905-ota-mark-part-adjudication/` (SUMMARY·evidence — 오케스트레이터 docs 커밋 몫). STATE.md·ROADMAP.md 무접촉.
