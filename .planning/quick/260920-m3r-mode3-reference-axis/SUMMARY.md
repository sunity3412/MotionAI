---
id: 260920-m3r
title: mode3 를 기준 선수 각도 축에 배선 (플래그 뒤, 기본 꺼짐)
date: 2026-09-20
status: complete
---

# 260920-m3r — mode3 가 "발전했나"를 읽을 수 있게 고정 잣대를 걸었다 (아직 안 켰다)

## 0. 판정

**됐다. 단, 켜지 않았다.** 배선은 들어갔고 오프라인으로 끝까지 따라가 확인했다.
학생 영상이 오면 세 가지를 재고, 그 뒤에 스위치를 올린다.

## 1. 무엇이 문제였나

belle: *"mode3 학생 비교는 틀리고 맞고가 아니라 발전해냐 안했냐겠지?"*

`[확인]` mode3 종합점수는 **떨림 단독**이다. 동작을 모른다고 보아 `line` 차원이
구조적으로 안 생기고([[mode3-score-is-wobble-only]]), 이전 영상 대비 유사도는 종합에서
**일부러 뺐다** — 코드 주석에 이유가 박제돼 있다: 발전하면 못하던 과거의 나와 덜
비슷해져 점수가 역전된다([[mode3-overall-exclude-angle-similarity]]).

즉 **그 판단은 옳았고, 그래서 mode3 에는 움직이지 않는 잣대가 없어졌다.**
기준 선수의 각도가 바로 그 잣대다.

## 2. 배선 전에 확인한 것 — 숫자가 화면까지 닿는지

`[확인]` `tally` 의 `dimension_overall` 은 **폴백 전용**이다
(`deduction_engine.py:382` — `if quant_unavailable and not activated`).
감점 criterion 이 하나라도 서면 안 쓰인다. 그래서 내가 앞서 오프라인 측정에서
`dimension_overall=100` 을 넣은 것이 수치를 왜곡하지 않았다. 감점이 0이면 오늘의 떨림
점수로 자연 강등된다 — 깨끗한 퇴로.

`[확인]` 방출 게이트 `profile.expects_extension(jk)` 가 쓰는 EXTEND 집합을 인식기가
**criteria yaml** 에서 만든다(`gemini_technique_recognizer.py:430`). 측정이 쓴 출처와 같다.

`[확인]` mode3 는 이미 `_match_reference_by_motion_id(motion_id)` 로 기준 doc 을 손에
쥐고 `bodyNormalizationProfile` 한 필드만 쓰고 버린다. 각도는 이미 거기 있었다.

## 3. 범위를 좁게 잡은 이유 — 그 변수의 소비처가 여섯이다

`reference_dtw_match` / `reference_angles_for_veto` 를 mode3 에서 채우면 여섯이 같이
움직인다. 전부 세고 나서 셋만 남겼다:

| 소비처 | 배선 후 |
|---|---|
| 감점 builder (`_build_deduction_measured_deviations`) | **채운다 — 이게 목표** |
| vision_veto context | 안 건드림 |
| quantification | 안 건드림 |
| safety flags · motionAlignment · **확대카드(fault-zoom)** | 이미 mode 로 분기돼 있어 불변 |

★ 확대카드가 "지난 영상 대비"에서 "기준 선수 대비"로 바뀌는 것은 **별개의 제품 결정**
이다. belle 이 승인한 것은 채점 축이지 카드 문법이 아니다(mode3 = progress).
그래서 mode3 전용 변수 3개를 따로 두고 감점 builder 한 곳에만 넣었고, 이 경계를
**구조 게이트로 상시 강제**한다(§6).

## 4. 화면이 채점 출처를 틀리게 말하지 않도록 — 라벨도 같이 고쳤다

`[확인]` 계약이 명시적이었다: *"Mode3 허용 scoringBasis = 정확히 4 값. reference_motion
은 Mode1 전용 — Mode3 에 들어오면 거짓 reference 비교 함의(신뢰 문제 재발)"*
(`assemble.py:577`, `models.py:55`, `contract.md:775`).

그 전제("Mode3 에는 reference 비교가 존재하지 않음")가 **배선이 켜지면 거짓이 된다.**
절대트랙 라벨을 단 채 기준 비교 점수를 내면 화면이 채점 출처를 틀리게 말한다 —
TRUST-03 이 막으려던 바로 그것이다. 그래서 두 값을 더했다:

```
recognized_motion_reference_relative       등재 동작 — 기준 선수 각도 대비 평가
previous_analysis_plus_reference_relative  이전 분석 대비 + 기준 선수 각도
```

- 라벨은 **의도가 아니라 산출을 따라간다** — 플래그가 켜져도 기준을 못 찾거나 정렬이
  실패하면 `reference_relative=False` 라 종전 라벨이 붙는다.
- 미등재는 기준을 못 찾으므로 이 라벨을 주장할 수 없다(방어 guard + 시험).
- `reference_motion` 은 **여전히 Mode1 전용**. Mode1 은 사용자가 기준을 *고른* 비교이고
  Mode3 는 인식된 동작으로 기준을 *찾아온* 비교라 근거의 출처가 다르다.
- 라벨에 선수 이름을 박지 않았다 — 기준 라이브러리가 바뀌면 과거 분석의 라벨이
  거짓이 된다([[display-string-is-not-a-join-key]]).
- 계약 4곳 동시 갱신: `assemble.py` · `models.py` · `docs/contract.md` · `analysis.ts`.

## 5. 실측 — 운영 함수를 플래그 켜고 그대로 돌렸다

`[확인]` 손으로 엮은 경로가 아니라 **방금 배선한 `_mode3_reference_axis`** 를 호출했다.
기준 32편/자기비교 코퍼스, 기준 doc 은 저장 분석과 같은 시대 판으로 맞췄다(14-3).

```
동작                        정타(지금→배선)      결함(지금→배선)   분리 지금  분리 배선
ref-pdshape                   58 → 100           83 →  66        −24       +34
ref-power-spin                97 → 100           91 →  66         +6       +34
ref-elbow-twist-sister        77 → 100           74 →  73         +4       +27
ref-peter-pan                 98 → 100           98 →  80         ±0       +20
ref-climb                     95 → 100           87 →  92         +8        +8
ref-kip-up                    97 → 100           98 → 100         −1        ±0

정타가 결함보다 높은 동작:   지금 3/6  →  배선 5/6
정타 vs 결함 분리(전체 중앙): 지금 +2점 → 배선 +19점
기준 축 발화 32/32
```

`[확인]` **kip-up 은 안 고쳐진다**(±0). 결함판이 100점을 받는다. 이 축은 kip-up 의
결함을 못 본다 — 알려진 건(geometric split 측정이 keypoint saturate 로 confounded).
이 배선의 공은 아니다.

## 5-1. kip-up 이 왜 안 잡혔나 — 재고 고쳤다 (belle: *"안 고쳐진다고만 하면 안돼 방법을 알려야지"*)

`[확인]` **축은 결함을 정확히 본다.** 기준 대비 편차가 결함판에서 뚜렷이 벌어진다:

```
관절            정타    결함      차
left_shoulder    3.5   20.6   +17.1      ← 6배
left_elbow       4.2   13.8    +9.6
right_shoulder   3.3   12.7    +9.4
right_hip        2.4    9.6    +7.2
```

막힌 곳은 그 다음 **두 칸**이다:

1. **허용오차 20도.** 20.6도는 문턱을 0.6도 넘었을 뿐이라 감점이 **−0.7점**이다.
   6배 차이가 0.7점으로 번역된다.
2. **신뢰구간 억제.** 왼어깨 CI 가 `15.9~24.3` 으로 문턱을 걸쳐서, 그 −0.7점마저
   "확신 없음"으로 억제된다(quick-260802-nse). 최종 100점.

★ **두 칸 다 점수로서는 옳다.** 오차 안이면 안 깎는 게 맞고, 확신 없으면 안 깎는 것도
맞다. 틀린 것은 **그 점수의 차이로 발전을 읽으려 한 것**이다.

### 방법 — 발전은 문턱이 필요 없는 양이다

```
발전_관절 = (이전 영상의 기준 대비 편차) − (지금 영상의 기준 대비 편차)
양수 = 기준에 가까워졌다
```

점수는 "허용오차를 넘었나"를 묻고, 발전은 "저번보다 가까워졌나"를 묻는다. **다른 질문
이라 다른 산식이어야 한다.** 이 읽기는 문턱을 안 쓰므로 둘 다 오차 안인 쌍도 읽는다.

`[확인]` 실측(운영 함수 `_mode3_reference_approach`, 정타/결함 쌍 6동작):

```
동작                     점수 이전→지금  점수로 발전   가까워진 관절  평균 좁힘  접근도로 발전
ref-climb                  92 → 100        읽음        8/8        13.0       읽음
ref-power-spin             66 → 100        읽음        8/8        12.0       읽음
ref-peter-pan              80 → 100        읽음        8/8        10.1       읽음
ref-pdshape                67 → 100        읽음        8/8         8.9       읽음
ref-kip-up                100 → 100      못 읽음        8/8         6.3       읽음  ←
ref-elbow-twist-sister     82 → 100        읽음        8/8         4.0       읽음

발전 방향을 맞힌 동작:   점수 5/6   →   기준 접근도 6/6
```

★ **한 동작 맞춤이 아니다** — 6동작 전부에서 관절 **8/8 만장일치**다.
방향 반전(정타→결함)도 음수로 뒤집힌다(시험으로 박제).

### 무엇을 넣었나

`comparison.referenceApproach` = `{byJoint, jointsCloser, jointsCompared,
meanNarrowedDeg}`. **관측 전용 — 점수·앱 무접촉**(260919-mhl `pairDeviationSec` 선례).
기준 축 미발화(플래그 OFF 포함)면 **키 자체가 없다**. 계약 3곳 동시 갱신.
관측 밖으로 새면 실패하는 정적 게이트 포함.

★ 허용오차 20도는 **안 건드렸다.** 문턱을 kip-up 에 맞춰 내리는 것은 커브핏이고
([[chasing-the-number-is-the-tangle]]), 점수의 신중함은 그대로 두는 게 맞다.

### 부수 발견 — criteria yaml 이 11편 중 5편 비었다

`[확인]` `load_grouped_criteria` 적재 현황:

```
criterion 6개 : ref-foxtop · ref-foxtop-split · ref-invert · ref-sideway-spin
criterion 2개 : ref-power-spin (EXTEND = 양 무릎)
criterion 0개 : ref-climb · ref-elbow-twist-sister · ref-kip-up · ref-pdshape · ref-peter-pan
파일 없음     : ref-combo
```

`angle_vs_reference__*` 는 관절 일반 criterion 이라 빈 yaml 에서도 돈다(그래서 배선이
5/6 을 낸다). 다만 **동작 고유 결함**(kip-up 의 다리 벌림 등)은 이 5편에서 채점될 수 없다.
belle 라벨링이 필요한 별건 — 이 배선의 범위 밖.

## 6. 다시 새지 않게 — 시험 24건

`backend/tests/test_mode3_reference_relative_wiring.py` (신규 24건).

- 플래그: 기본 OFF · falsy set 은 리포 관례 그대로(새 규칙 0)
- **OFF 면 Firestore 를 읽지도 않는다** — 켜지 않은 채 머지해도 비용 0
- ON 이면 기준 각도가 실제로 감점 md 에 닿는다(끝까지 따라감)
- 동작을 모르면 켜져 있어도 안 붙인다(D-08)
- 정렬이 깨지면 예외 대신 종전 mode3 로 강등 — 분석이 죽지 않는다
- 라벨 6값 전수 + Mode1 `reference_motion` 유입 차단
- ★ **구조 게이트**: `mode3_ref_*` 가 승인된 자리 밖에 나타나면 실패.
  확대카드 호출부에 일부러 새게 해 **변이 검증** 통과 — 게이트가 실제로 잡는다.

게이트: `backend/.venv/bin/python -m pytest backend/tests` → **4989 passed / 20 skipped
/ 0 failed** (기준 4965 + 신규 24). 앱 `npm run typecheck` clean.

## 7. 켜는 조건 — 셋 다 통과해야

학생 영상은 이 축을 **한 번도 안 탔다.** 위 수치는 전부 기준 영상·자기비교 코퍼스다.

1. 같은 학생의 두 영상이 **같은 기준에 일관되게** 붙나
2. 강사 ○× 가 발전 방향과 일치하나
3. 카메라 각도가 바뀌어도 견디나

켜는 법: Pod env `MODE3_REFERENCE_RELATIVE_ENABLED=1`
(`backend/runpod_inference/start_server.sh`). 배포 없이 스위치만 올린다.

## 8. 남은 것

- `[미확인]` **라이브에서 이 플래그를 켜고 돌린 적이 없다.** 오프라인으로 끝까지
  따라갔지만 Pod 실행 로그는 없다([[wiring-claims-need-log-evidence]]).
- `[미확인]` `ref-elbow-twist-sister` 바닥값은 현행 파이프라인에서 아직 안 쟀다.
- `[확인]` kip-up 의 **점수**는 이 축으로 안 오른다(허용오차 안). **발전 읽기는 §5-1 로 해결**.
- `[미확인]` criteria yaml 이 11편 중 5편 비어 동작 고유 결함이 채점 불가 — belle 라벨링 별건.
- **belle 판정 대기**: mode3 가 지금처럼 점수를 안 띄우는 상태로 실증에 들어가도
  되는지(260920-stn §6 의 (나)). 이 배선이 켜지면 그 질문 자체가 사라진다.

**프로세스**: GSD 기본 모델(Fable) 크레딧 소진이 이어져 플래너 에이전트는 못 띄웠고
PLAN/SUMMARY 를 직접 작성했다(260920-stn 과 같은 이탈).
