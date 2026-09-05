---
phase: quick-260905-mvm
status: planned
subsystem: analysis-card-photo-audit
tags: [fault-zoom, machine-eye, audit, self-check]
created: 2026-09-05
---

# quick-260905-mvm: 확대 카드 사진이 제목의 부위를 보여주는지 검사하는 감사 도구

## 왜

2026-09-05, belle 이 확대 사진 대장을 보고 "6.1초 오른팔꿈치 카드가 5.3초 왼팔꿈치 카드와 같은 팔로
보인다"를 먼저 찾아냈다. 확인 결과 **21장 중 5장이 제목과 다른 부위를 보여주고 있었다**
(pdshape 오른팔꿈치=등허리 · 파워스핀 왼어깨=허벅지 · 엘보 오른팔꿈치 기준=겨드랑이 ·
엘보 왼어깨=양쪽 허벅지 · 엘보 참고 왼어깨=머리).

우리 통과 기준은 이걸 못 잡는다. 09-03 "6동작 6/6 PASS"는 `expected_units == emitted`,
**사진 장수만** 셌다. 사진이 자기 제목의 부위를 보여주는지는 한 번도 세지 않았다.

좌표로 감사하면 안 된다는 것도 09-05 에 확인했다 — crop 중심의 출처가 경로마다 다르다
(게이트 통과 카드 = align 17-kp, 폴백 카드 = rep12 `keypointReport`). doc 에는 rep12 만 실려서
rep12 신뢰도로 판정하면 오판이 난다(실제로 3장 오판). **사람이 보는 그림은 경로가 뭐든 하나뿐이므로
거기서 검사한다.**

## 설계 원칙 (기존 기계 눈 승계 — 재구현 금지)

`card_gates.eye_judge` 가 이미 인라인 JPEG + response_schema + fail-closed + 다수결
(`eye_judge_majority`)을 갖고 있다. 새 caller 를 만들지 않고 **claim 하나를 추가**한다.

★ 승계할 핵심 규칙: **질문에 좌우·관절 이름을 절대 넣지 않는다.** keypoint 환각이 나면 마크가
엉뚱한 곳에 찍히고 그 불일치를 눈이 잡아야 하는데, 정답을 알려주면 눈이 짜맞춘다
(`_CLAIM_QUESTION` 주석, bz5 부록 C). 눈은 "무엇이 보이는가"만 답하고 **기대와의 대조는 코드가** 한다.

## 하는 일

### Task 1 — `part` claim 추가 (card_gates)

`backend/shared/python/sunity_shared/analysis/card_gates.py`
- `_CLAIM_QUESTION["part"]`: "사진 정중앙에 가장 크게 보이는 신체 부위는 무엇입니까?" +
  기존 `_LIMB_QUESTION` 접미. 좌우·관절명 0.
- `_CLAIM_ENUM["part"]`: `["head","neck","shoulder","armpit","elbow","hand","chest",
  "abdomen","back_waist","hip","thigh","knee","foot","unclear"]` (영문 토큰 — 기존
  bent/extended/off_body 관례).
- `_eye_verdict` 에 `part` 분기: **기대 부위를 모르는 함수이므로 판정하지 않는다** —
  `observed not in ("unclear",)` 만 반환한다(= "부위를 읽어냈다"). 제목과의 대조는 Task 2 의
  순수 함수가 한다. 이 분리가 기존 계약(눈은 관측, 게이트는 결정)과 동형이다.
- 기존 claim 3종(bent/extended/off_pole)의 질문·스키마·판정은 **byte 무변경**.

`verify`: 기존 card_gates 테스트 전건 통과 + 신규 `part` 질문에 좌/우/left/right 문자열 0 을
단언하는 테스트.
`done`: `eye_judge(crop, "part", ...)` 가 부위 토큰을 반환한다.

### Task 2 — 순수 대조 모듈 `card_photo_audit.py`

`backend/shared/python/sunity_shared/analysis/card_photo_audit.py` (numpy/네트워크 무관 순수)
- `expected_parts(criterion, joint) -> frozenset[str]` — 카드가 약속한 부위의 허용 집합.
  · `angle_vs_reference__{jk}` → jk 관절 종류에서 파생
    (elbow→{elbow,hand,shoulder} / shoulder→{shoulder,armpit,chest,back_waist} /
     hip→{hip,thigh,back_waist,abdomen} / knee→{knee,thigh,foot})
  · `split_angle` → {hip,thigh} · `leg_extension` → {thigh,hip,knee} · `arm_extension` → {elbow,hand,shoulder}
  · criterion 없는 참고 카드 → joint 로 같은 파생
  ★ 허용 집합에 이웃 부위를 넣는 이유: crop 은 관절 주변을 담으므로 "정중앙"이 인접 부위로
  읽히는 것은 정상이다. 잡으려는 것은 **팔꿈치 카드가 등허리를 보여주는** 종류다.
- `audit_card(expected, user_observed, ref_observed, *, user_marked, ref_marked) -> dict`
  — `{userOk, refOk, flags}`. 표시가 없는 측(userMarked=False)은 "표시 위치" 불일치를 묻지
  않고 "그 부위가 보이는가"만 본다.
- 문서 문자열에 09-05 실측 5건을 알려진 정답으로 박제.

`verify`: `backend/tests/test_card_photo_audit.py` — 09-05 실측 21장 중 알려진 5 불일치 +
정상 3장을 케이스로 (네트워크 0, 관측값은 하드코딩).
`done`: 순수 함수만으로 5/21 을 재현한다.

### Task 3 — 감사 스크립트 `backend/scripts/audit_card_photos.py`

- 입력: `--uid --analysis-id` (또는 `--pairs uid:aid,...`), 옵션 `--rounds 3`, `--out <json>`
- 절차: Firestore 문서 → `faultZoomComparisons` → 각 카드의 합성 PNG 를 `imageUrl` 로 내려받아
  **좌/우 패널로 이등분** → 패널마다 `eye_judge_majority(panel, "part", ...)` →
  `card_photo_audit.audit_card` → 표 + JSON.
  ★ 이등분해서 패널마다 따로 묻는다 — 기존 눈은 "한 장 한 판정" 형상이고, 반쪽씩 물어야 답이 섞이지 않는다.
- 모델: `resolve_model("C")` (raw 문자열 박제 0 — 지금 3.8).
- 키: 기존 경로 재사용 (env `GEMINI_API_KEY` → SSM 폴백).
- 출력 마지막 줄: `card_photo_audit total=N mismatched=M` (로그 grep 가능한 불변식 한 줄).

`verify`: `--help` 동작 + 09-03 라이브 6문서에 실행해 **5장 불일치**가 재현되는지 확인
(belle 이 지적한 파워스핀 왼어깨·pdshape 오른팔꿈치가 그 안에 있어야 한다).
`done`: 스크립트가 리포에 있고, 같은 입력에 같은 판정을 낸다.

## 하지 않는 일

- **파이프라인에 붙이지 않는다.** 분석 시점 게이트로 승격하는 것은 다음 단위 — 카드마다 눈 호출이
  늘고, 불일치일 때 무엇을 할지(사진을 다른 순간으로 옮길지)가 별도 결정이다.
- 게이트 미달 좌표로 crop 하지 않게 고치는 수리도 다음 단위 (원인 수리 ≠ 계측기).
- 기존 claim 3종과 `machine_eye` 운영 경로는 손대지 않는다.

## 게이트

- backend pytest 전체 — 직전 기준선 **4602 passed / 0 failed / 20 skipped**
- 신규 claim 질문에 좌우 어휘 0 (테스트로 강제)
- 09-03 라이브 21장 재실행에서 불일치 5장 재현
