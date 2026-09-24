---
quick_id: 260924-vw2
slug: kip-up-card-photo
date: 2026-09-24
status: complete
---

# Quick 260924-vw2 — kip-up 카드 **사진** 배선 (belle 4/4 ○)

> 선행 vj1(문장, `33ffae38`). 코드 커밋 `c83700d6` + 자막 수리 `6d70f4b1`(push). Pod E2E 완료(L4 `4v60m6rjwnm5e3`, 약 40분 ≈ $0.33, 종료·주소 되돌림 확인).
> **belle 사진 ○× 대기** — 판정지 `judge_e2e_kipup.png`(운영 산출물 그대로).

## 0. 판정 (belle 에게)

**된다(kip-up 카드).** 앱과 같은 경로(Pod)에서 kip-up 실수 분석의 카드 문장 3줄·카드 사진·합성 영상 멈춤이 전부 belle ○ 후보와 같은
순간(2.11s|2.53s)·같은 표시(왼팔·낮은발 동그라미, 각도 선 0)로 나왔다. 점수 83 불변. 넘기기 전에 내가 찾은 결함 1건(영상 멈춤에서 학생 발 원이
자막에 가려짐)은 고쳐서 다시 돌렸다(§5). 원 위치는 내 눈으로 닫지 않았다 — belle 사진 ○× 로 닫는다. 나머지 9편은 불변(§6).

## 1. 바뀐 것 (코드 `c83700d6`)

| 자리 | 무엇 |
|---|---|
| `hold_height.representative_pair` | 창 안 운영 DTW 짝 중 1:1(정체 아님) · 몸이 그립 손 같은 쪽 · 표식 관절(그 팔 어깨·팔꿈치·손 + 낮은발) 신뢰 ≥ 0.35 · 짝 높이 차가 창 상수에 가장 가까운 짝. uff 때 내 눈으로 뺀 후보 c(몸이 폴 반대쪽)를 이제 측정 조건이 뺀다 |
| record 새 필드 (3-way: models · analysis.ts · contract.md §10.2.2) | `measuredPattern` · `atRefVideoSec`. 그 record 의 `atFrameIdx/atVideoSec` = 대표 짝 학생 프레임. 대표 짝 없으면 문장도 안 바꾼다(반쪽 카드 금지) |
| `compare_align.select_pairs` | measuredPattern record 는 `atRefVideoSec` 그대로(자세거리 재선정 0) |
| `compare_render.build_timeline/render` | 그 record 는 재선정(피크·폴·그립·가중)·사이각 선 0, `circle_viz`(양 패널 그 팔·낮은발 원). 리포트 `circleViz` |
| `compare_render.circle_card_png` | 카드 = 영상 멈춤 두 프레임을 **같은 정규화 상자**(두 인물 상자 합집합)로 정사각 두 장(726×360, 앱 종횡비) + 같은 원, 표시 없는 판 동반 |
| `app._measured_pattern_card` + 게이트 루프 훅 | measuredPattern record 는 좁은 크롭 대신 이 카드. 실패 시 종전 카드 경로. 게이트 상태 싣기 세 줄을 `_stamp_gate_states` 로 모아 두 경로 공유(게이트 축 무변경) |
| 테스트 26 신규 | test_hold_height +6 · test_measured_phrase_variants +5 · phase35/test_measured_card_freeze 11 · test_measured_pattern_card 4 |

무접촉: 점수 경로 · 다른 record/동작의 순간·짝·표시(새 필드 부재 = byte-동일) · 게이트 판정 로직.

## 2. 관측 — 오프라인

- 전체 backend **5095 통과**(20 skip, 실패 0) · app `tsc` 통과 · 화면 어휘 게이트 5/5.
- 저장 doc 10편 게이트(`scripts/gate10.py`): **kip-up 실수만** `measuredPattern=body_low_arm_open · atFrameIdx=21 · atVideoSec=2.106 · atRefVideoSec=2.533` + 승인 문장 3줄. 나머지 9편 변화 없음.
- 대표 짝 규칙이 **belle ○ 사진과 같은 짝**(학생 f21 2.11s | 정은지 f38 2.53s)을 눈 없이 고른다. 정타 doc 은 (1.2s|1.2s)를 고르지만 패턴 불성립이라 쓰이지 않는다.
- 로컬 미리보기(`preview_card_local.png`, 운영 `circle_card_png` + 로컬 영상 1080 높이 프레임 + 저장 키포인트) = ○ 사진과 같은 구도·원 위치.
  첫 판은 정사각 상자가 프레임 왼쪽 밖으로 나가 어두운 띠가 생겨 **안쪽으로 미는 규칙**을 넣었다.
- 감시 테스트 1건(`test_existing_pair_gate_surface_unchanged` — `pair_state` 글자 수)이 걸렸다 → 게이트 상태 싣기를 공용 함수 하나로 모아 통과(감시 테스트 무수정).

## 3. 미확인 — Pod E2E 에서 닫을 것

- `[미확인]` 운영 align(Pod 15fps 재추출) 좌표로 그린 원이 맞는 자리에 있는가 — 로컬 미리보기는 저장 9fps 키포인트 근사다. **표식 위치는 내 눈으로 닫지 않는다** → belle ○×.
- `[미확인]` 리그(compare_verify) 전 항목 PASS — H2(멈춤 순간 == record 순간)는 구조로 성립해야 한다.
- `[미확인]` 스팟체크(Gemini)가 새 문장을 `mismatch` 로 숨기지 않는가(규칙상 "명백히 반증"일 때만).
- `[미확인]` 앵커 부위 확인(Gemini part check)은 이 카드에 **돌지 않는다**(좁은 크롭 문법 전용) — 원 위치의 안전망이 하나 빠진 상태. E2E 사진으로 belle 판정.
- `[미확인]` GPU 종류 — L4 재고 없으면 다른 종류로 돈다. 점수 비교(구간 제거 판 재검증)는 L4 일 때만 유효.

## 4. 다음
Pod 기동 → 10편 재분석(`intake_clips.py analyze --hash …`) → 로그(`hold heights` · `measured variant applied` · `measured_card` · `card_gates verdict` · `compare_render done`) →
kip-up 실수 doc 의 카드 PNG·영상 멈춤 프레임을 판정지로 → belle ○× → 앱 화면(시뮬레이터) 캡처 → Pod 종료(`pod_teardown.py <id>`).

## 5. 관측 — Pod E2E (L4 `4v60m6rjwnm5e3`, 앱과 같은 경로)

- Pod 확보: 볼륨 DC(EU-RO-1) 비-Blackwell GPU **전부 재고 0** → 90초 간격 헌트(L4 우선 → Ada → Ampere)로 2분 만에 **L4**($0.49/h, 지난 두 판과 같은 종류).
- 서버 health: commitSha 85ff775f → (자막 수리 뒤) **6d70f4b1**, RTMWPoseEngine · GeminiTechniqueRecognizer, Lambda 주소 자동 동기(RUNPOD_POD_ID export).
- **1차 kip-up 실수(466ee4c5, 85ff775f)** — 로그 `[확인]`:
  `hold heights … hip=-0.145 lowFoot=-0.220 grip=-0.021 hipBelowHand=-0.126`(오프라인과 같은 값) ·
  `measured variant applied … pair=u21/r38 (2.11s/2.53s)` · `card_gates verdict … survivors=['r00:inherit@u2.106/r2.53 … pair=match eye=skip:torso_joint']` ·
  `measured_card rid=r00 … u9=21 at=21 marked=True` · `compare_render done … freezes=1`(리그 전 항목 PASS 후에만 done).
  doc: 점수 **83 그대로** · record measuredPattern/atFrameIdx 21/atVideoSec 2.106/atRefVideoSec 2.533 · 승인 문장 3줄 · spotCheck hidden 0 ·
  확정 카드 userVideoSec 2.106 / refVideoSec 2.53 / userMarked·refMarked True / atMatched True / pairDeviationSec 0.13.
- ★**넘기기 전 내가 찾은 결함 1건**: 영상 멈춤에서 **학생 낮은발 원이 자막 띠에 가려졌다**(발이 바닥 근처라 아래 자막 상자 안) —
  이 카드의 핵심 증거가 가려진다. 앱 카드 PNG 는 자막이 없어 무관. → `caption_should_move_up`(원이 아래 밴드에 걸리고 위 밴드엔 안 걸리는
  멈춤만 자막을 위로, 그 외 종전) 커밋 **6d70f4b1**, 서버 재기동 후 재분석.
- **2차 kip-up 실수(0f8ae558, 6d70f4b1)**: 같은 로그·같은 doc 값 + 영상 멈춤 자막이 위(천장 쪽)로 → **두 발 원 모두 보인다**, 손도 안 가린다.
- 판정지 = `judge_e2e_kipup.png`(앱 카드 PNG 그대로 + 영상 멈춤 장면 + 문장). 증거 = `e2e/`(카드·멈춤 프레임 · 1차 가려진 프레임).
- 참고: 같은 doc 에 옛 **advisory** 카드(1.40s|3.6s, 좁은 크롭)가 남아 있다 — fault_zoom 단계 산출을 게이트 상속이 보존.
  `[확인: 코드]` 앱 카드 연결(`app/src/lib/deductionLabels.ts:319-320` matchZoomForDeductionRecord)은 advisory 를 건너뛰고
  criterion 이 같은 확정 카드를 잡는다 → 이 record 에는 새 카드가 붙는다. advisory 는 이번 범위 밖, 무접촉.

## 6. 관측 — 나머지 9편 회귀 (같은 L4, 6d70f4b1) + 구간 제거 판 Pod 재검증

| 동작 | 정타 ig3→오늘 | 실수 ig3→오늘 | 새 문장/카드 | 합성 영상(오늘) |
|---|---|---|---|---|
| kip-up | 100 → 100 | 83 → 83 | **실수만 적용**(1건) | 정타 멈춤 0 done · 실수 멈춤 1 done(동그라미·자막 위) |
| power-spin | 100 → 100 | 80 → **68** | 없음 | 정타 done · 실수 **리그 FAIL**(아래) |
| climb | 100 → 100 | 60 → 60 | 없음 | 정타 done · 실수 done |
| peter-pan | 100 → 100 | 60 → 60 | 없음 | 정타 done · 실수 (§7 에 기록) |
| pdshape | 100 → 100 | 80 → 80 | 없음 | 정타 align_quality 스킵(ig3 때도 None) · 실수 (§7) |

- `[확인: Pod]` **구간 제거 판(e45d325f) 재검증 닫힘** — power-spin 실수 80 → **68** = ig3 때 산식으로 예상한 값 그대로. 나머지 불변.
- `[확인: 로그]` `measured variant applied` 는 kip-up 실수(0f8ae558) **1건뿐**, `measured_card` 1건. 높이 로그 7편은 오프라인 게이트 값과 같고,
  서 있는 구간이 없는 3편(peter-pan 실수 · pdshape 둘)은 `hold heights unavailable`(설계대로 fail-closed).
- `[관측]` **power-spin 실수 합성 영상 리그 FAIL** — `E 저더 ref 정지이벤트 4(임계 4)` · `Q 신뢰 커버리지 user 0.877(임계 0.88)`.
  보고서: 멈춤 **3개**(r02 4.71s · r00 5.73s 피크 · r01 6.81s, 전부 종전 문법 — 동그라미 아님). ig3 판은 같은 L4 에서 멈춤 1개로 done.
  `[진단, 미검증]` 구간 제거로 억제되던 어깨 감점 2건이 살아나 6.8초 영상에 멈춤이 1→3 이 되며 재생 구간이 잘게 쪼개진 결과로 보인다 —
  오늘(vw2) 변경은 이 doc 에 탈 경로가 없다(measuredPattern 0). 앱은 합성 영상이 없으면 듀얼 플레이어로 보여 준다(종전 폴백). 범위 밖 — 인계에 올림.
