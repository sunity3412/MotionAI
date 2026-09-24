---
quick_id: 260924-vj1
slug: kip-up-card-text
date: 2026-09-24
status: complete
---

# Quick 260924-vj1 — kip-up 카드 **문장** 배선 (belle 4/4 ○)

> belle 09-24 밤: uff 판정지 4/4 ○ → *"짜맞추는거면 이게 무슨 소용일지"* → *"지금 할거 하자"*.
> 코드 커밋 `33ffae38`. Pod 0 · Firestore 읽기 13회(저장 doc 10 + 기준 5, 게이트용) · 크레딧 0.

## 0. 판정 (belle 에게)

**된다(문장).** kip-up 실수 카드의 제목·설명·교정이 ○ 받은 문장으로 바뀐다. 이 영상에 맞춘 문자열이 아니라
**분석마다 잰 값**(유지 구간 몸 높이 + 겨드랑이 방향)이 네 조건을 모두 만족할 때만 쓰고, 하나라도 못 재면 지금 문구 그대로다.
저장된 10편으로 돌리면 kip-up 실수 한 편에만 나온다. **사진은 아직** — 영상 멈춤 순간과 같이 바꿔야 해서 다음 quick.
앱 화면 반영은 다음 분석(Pod)부터다(`[미확인: Pod E2E]`).

## 1. 바뀐 것 (코드 `33ffae38`)

| 자리 | 무엇 |
|---|---|
| `sunity_shared/analysis/hold_height.py` (새, 순수) | `hold_window_heights` — 기준 clipRange 창 안 엉덩이·낮은발·그립 손 높이, 손 기준 높이, 앞/중/뒤 1/3. 단위 = 서 있을 때 몸길이(창 이전), 바닥 = 창 이전 발목. `body_low_arm_open` — ①1/3 전부 엉덩이·낮은발 낮음 ②그립 손 같음 ③손 기준 엉덩이 낮음 ④그 관절 창 상수 부호 +. 잡음 폭 0.05 몸길이 |
| `backend/data/phrasebook.json` | 새 절 `measuredVariants["ref-kip-up.angle_vs_reference__left_shoulder"]["body_low_arm_open"]` = uff 판정지 문장 3줄 그대로 + `_meta.measuredVariantsProvenance` |
| `phrasebook.py` | `assemble_measured_variant` · `rendered_copy_strings` 에 새 절 포함(숫자·%·금지어 게이트가 새 문장도 검사) |
| `pipeline/app.py` | `_measured_phrase_variants` — mode1 · 동작 일치 · 키포인트↔각도 프레임 1:1 · **상수 경로가 그 관절을 잰 경우**만. `_attach_translation_emission(measured_phrases=)` 가 문구집보다 먼저 3슬롯을 채운다(coachQuestion·운동은 문구집 그대로). 로그 `hold heights …` · `measured variant applied …` |
| 테스트 50 (새) | `test_hold_height.py` 28 · `test_measured_phrase_variants.py` 22 |

무접촉: 점수·허용 20·slope·캡·seed 값·record 순간·확대 사진·합성 영상. 변형이 없으면 record 는 byte-동일(테스트).

## 2. 관측 — 게이트

- 전체 backend 테스트 **5069 통과**, 20 skip, 실패 0 (ig3 5019 + 새 50). 앱 화면 어휘 게이트 5/5 통과.
- 테스트가 **실제 버그 1건**을 잡았다: 새 선택기가 모듈에 없는 이름 `JOINT_KEYS` 를 써서 예외 → except 가 {} 로 삼켜
  **운영에서 조용히 "대체 없음"**이 될 뻔했다. `skeleton.JOINT_KEYS` 로 고침. [[wiring-claims-need-log-evidence]] — 그래서 Pod 로그 확인이 남는다.
- 모듈 = uff 측정 재현: 엉덩이 −0.145 · 낮은발 −0.220 · 그립 −0.021 · 손 기준 엉덩이 −0.126(uff −0.15/−0.22/−0.02/−0.13, 신뢰 하한 0.3→0.35 차이).
- **문턱 둔감성**: 잡음 폭 0.03~0.12 어디서든 실수 True · 정타 False(테스트로 잠금). 0.02 에선 그립 −0.021 이 "같음"을 못 넘고, 0.13 부터는 손 기준 엉덩이가 못 넘는다.
- **오프라인 게이트 — 운영 함수를 저장 doc 10편에** (`gate10_offline.txt`):

```
동작          판       점수   엉덩이  낮은발  그립손  손아래엉덩이  1/3전부낮음  대체
power-spin   정타     100   -0.048  +0.088  -0.075   +0.031     False      -
power-spin   실수      80   -0.184  +0.260  -0.646   +0.393     False      -
kip-up       정타     100   -0.008  +0.000  -0.015   +0.005     False      -
kip-up       실수      83   -0.145  -0.220  -0.021   -0.126     True       왼어깨 → 승인 문장 3줄
climb        정타     100   -0.002  -0.004  +0.008   -0.007     False      -
climb        실수      60   -0.203  -0.012  +0.312   -0.501     False      -
peter-pan    정타     100   +0.011  +0.004  +0.016   -0.015     False      -
peter-pan    실수      60   못 잼(창이 0 에서 시작 — 서 있는 프레임 없음)          -
pdshape      정타·실수 100·80 못 잼(시작이 봉 위 — 서 있는 자세 아님, 몸길이 ≤ 0)   -
```

## 3. 진단 — 재검증 대상

- `[미확인]` **다른 테이크의 정타 변동.** kip-up 정타는 기준과 **같은 테이크**(c3m)라 0 이 당연하다 — 잡음 폭의 근거로 약하다.
  유일한 다른 테이크 정타(power-spin)는 낮은발 +0.088(위쪽)·그립 −0.075 까지 났다. 네 조건을 동시에 만족한 정타는 없었지만,
  새 테이크(정은지 추가 촬영)가 오면 이 폭부터 본다 — 봉인 시험지의 첫 문항.
- `[관측, 해석 미정]` 높이 축은 다른 실수에서도 뭔가를 말한다: power-spin 실수는 **손을 훨씬 낮게 잡았고**(그립 −0.65) 몸은 손 기준 위,
  climb 실수는 **엉덩이가 낮고 손은 높다**(+0.31). 문장으로 쓰려면 동작별 belle 판정이 필요하다(지금 범위 밖).
- 인식 동작(profile.motion_id) ≠ 사용자가 고른 기준이면 대체하지 않는다 — 그 경우 문구집 조회 키도 달라지므로 일관.

## 4. 다음

- **사진**(다음 quick): 카드 사진은 합성 비교 영상의 멈춤 순간을 물려받는다(belle 08-09 규칙). 지금 record 순간(1.4s)이
  "창 안 학생 중앙값 최근접"으로 고른 것이라 기준 쪽이 다른 국면(3.6s)이 됐다 → 순간을 **같은 국면·대표 차이 짝**으로 고르는 규칙을
  record 순간에 넣고, 영상 멈춤·카드가 그걸 물려받게 한 뒤, 카드 그림을 전신·동그라미로. 합성 영상(belle 승인 표면)이 바뀌므로 판정지 다시.
- Pod E2E 한 번에: 이 문장 + 사진 + 구간 제거 판(e45d325f) 재검증, 같은 GPU 종류로.

## 5. 기록
PLAN · SUMMARY · `gate10_offline.txt` · `scripts/`(gate10.py · check_module.py — 운영 함수 호출만) · STATE · 인계서 §4.
