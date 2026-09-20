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

## 6. 다시 새지 않게 — 시험 19건

`backend/tests/test_mode3_reference_relative_wiring.py` (신규).

- 플래그: 기본 OFF · falsy set 은 리포 관례 그대로(새 규칙 0)
- **OFF 면 Firestore 를 읽지도 않는다** — 켜지 않은 채 머지해도 비용 0
- ON 이면 기준 각도가 실제로 감점 md 에 닿는다(끝까지 따라감)
- 동작을 모르면 켜져 있어도 안 붙인다(D-08)
- 정렬이 깨지면 예외 대신 종전 mode3 로 강등 — 분석이 죽지 않는다
- 라벨 6값 전수 + Mode1 `reference_motion` 유입 차단
- ★ **구조 게이트**: `mode3_ref_*` 가 승인된 자리 밖에 나타나면 실패.
  확대카드 호출부에 일부러 새게 해 **변이 검증** 통과 — 게이트가 실제로 잡는다.

게이트: `backend/.venv/bin/python -m pytest backend/tests` → **4984 passed / 20 skipped
/ 0 failed** (기준 4965 + 신규 19). 앱 `npm run typecheck` clean.

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
- `[확인]` kip-up 은 이 축으로 안 고쳐진다 — 별건.
- **belle 판정 대기**: mode3 가 지금처럼 점수를 안 띄우는 상태로 실증에 들어가도
  되는지(260920-stn §6 의 (나)). 이 배선이 켜지면 그 질문 자체가 사라진다.

**프로세스**: GSD 기본 모델(Fable) 크레딧 소진이 이어져 플래너 에이전트는 못 띄웠고
PLAN/SUMMARY 를 직접 작성했다(260920-stn 과 같은 이탈).
