---
id: 260920-m3r
title: mode3 를 정은지 기준 축에 배선 (플래그 뒤, 기본 꺼짐)
date: 2026-09-20
status: complete
---

# 260920-m3r — mode3 가 "발전했나"를 읽을 수 있게 고정 잣대를 건다

## 왜

belle: *"mode3 학생 비교는 틀리고 맞고가 아니라 발전해냐 안했냐겠지?"*

지금 mode3 종합점수는 **떨림 단독**이다. 동작을 모른다고 보아 `line` 차원이 구조적으로
안 생기고([[mode3-score-is-wobble-only]]), 이전 영상 대비 유사도는 **일부러 종합에서
뺐다** — 발전하면 과거의 못하던 나와 덜 비슷해져 점수가 역전되기 때문이다
([[mode3-overall-exclude-angle-similarity]], 주석에 belle 관측 "틀린 kip-up 98 →
올바른 영상 88" 박제).

그래서 mode3 에는 **움직이지 않는 잣대가 없다.** 정은지 기준이 바로 그 잣대다.

오프라인 전량 측정(같은 영상, 오늘 코드):

```
발전 한 쌍 (못한 판 → 잘한 판)      지금 mode3        배선 mode3
ref-pdshape                      83 → 58  (−24)    66 → 100  (+34)
ref-power-spin                   91 → 97  ( +6)    66 → 100  (+34)
ref-elbow-twist                  74 → 77  ( +4)    73 → 100  (+27)
ref-peter-pan                    98 → 98  ( ±0)    80 → 100  (+20)
ref-climb                        87 → 95  ( +8)    92 → 100  ( +8)
ref-kip-up                       98 → 97  ( −1)   100 → 100  ( ±0)
발전을 못 읽는 동작:  지금 3/6  →  배선 1/6
```

## 무엇을

`profile.motion_id` 가 등재 기준을 가리키면, mode3 도 그 기준 각도와 DTW 비교해
`angle_vs_reference__{joint}` 를 방출한다. **감점 경로만** 먹인다.

배선 범위를 좁게 잡는 근거 — 그 두 변수(`reference_dtw_match` /
`reference_angles_for_veto`)의 소비처를 전부 셌다:

| 소비처 | 지금 | 배선 후 |
|---|---|---|
| `_build_deduction_measured_deviations` (:8632) | mode3 None | **채운다 — 이게 목표** |
| vision_veto context (:8479) | mode3 None | 건드리지 않는다 |
| quantification (:8566) | mode3 None | 건드리지 않는다 |
| safety flags (:8769) | `if mode == EXPERT` 로 이미 분기 | 불변 |
| motionAlignment (:9134) | 이미 분기 | 불변 |
| fault zoom 확대카드 (:9279) | 이미 분기(mode3=이전영상) | 불변 |

belle 이 승인한 것은 **채점 축**이다. 확대카드가 "지난 영상 대비"에서 "정은지 대비"로
바뀌는 것은 별개의 제품 결정이라 이번 범위 밖.

## 확인해 둔 것 (배선 전 선검증)

- `[확인]` `tally` 의 `dimension_overall` 은 **폴백 전용** — 감점 criterion 이 하나라도
  서면 안 쓰인다(`deduction_engine.py:382` `if quant_unavailable and not activated`).
  그래서 오프라인 측정에서 `dimension_overall=100` 을 넣은 것이 수치를 왜곡하지 않았다.
  감점이 0이면 오늘의 떨림 점수로 자연 강등된다 — 깨끗한 퇴로.
- `[확인]` 방출 게이트 `profile.expects_extension(jk)` 가 쓰는 EXTEND 집합은 인식기가
  **criteria yaml** 에서 만든다(`gemini_technique_recognizer.py:430`). 오프라인 측정이
  쓴 출처와 같다 → 수치 재현된다.
- `[확인]` mode3 는 이미 `_match_reference_by_motion_id(motion_id)` 로 기준 doc 을
  손에 쥐고 `bodyNormalizationProfile` 한 필드만 쓴다(:8371). 각도는 이미 거기 있다.

## 켜는 조건 (셋 다 통과해야)

학생 영상이 오면 잰다. 하나라도 안 되면 켜지 않는다.

1. 같은 학생의 두 영상이 **같은 기준에 일관되게** 붙나
2. 강사 ○× 가 발전 방향과 일치하나
3. 카메라 각도가 바뀌어도 견디나

## 작업

- [x] `_mode3_reference_relative_enabled()` — env `MODE3_REFERENCE_RELATIVE_ENABLED`, 기본 off
- [x] mode3 분기에서 기준 각도 DTW 비교 → mode3-local 변수 3개
- [x] 감점 builder 호출부에만 주입
- [x] 회귀시험: 플래그 off = 종전 그대로 / on = 기준 축 발화
- [x] 게이트 `backend/.venv/bin/python -m pytest backend/tests` (기준 4965 passed)
