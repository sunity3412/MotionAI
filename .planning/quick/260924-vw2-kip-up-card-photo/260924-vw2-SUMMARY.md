---
quick_id: 260924-vw2
slug: kip-up-card-photo
date: 2026-09-24
status: in-progress
---

# Quick 260924-vw2 — kip-up 카드 **사진** 배선 (belle 4/4 ○)

> 선행 vj1(문장, `33ffae38`). 코드 커밋 `c83700d6`(push). **Pod E2E 대기** — 볼륨 데이터센터에 GPU 재고 0(L4·4090·L40S·Ada·Ampere 전부),
> 백그라운드 재시도 중. Pod·크레딧 0 (이 문서 시점).

## 0. 판정 (belle 에게)

**반쪽 — 코드는 됐고 실물 확인 전.** 카드 사진과 영상 멈춤이 belle ○ 사진과 같은 순간·같은 표시를 쓰게 배선했다.
저장 doc 오프라인 게이트와 로컬 미리보기(운영 합성 함수)는 ○ 사진과 같은 그림을 낸다. 앱 경로(Pod)로 실제 분석을 돌려
카드 PNG·영상 멈춤 프레임을 **운영 산출물 그대로** 보기 전에는 "된다"라고 쓰지 않는다([[wiring-claims-need-log-evidence]]).

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
