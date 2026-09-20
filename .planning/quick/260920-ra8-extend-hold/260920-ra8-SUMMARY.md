---
id: 260920-ra8
title: EXTEND 채점 hold 창을 기하 창으로 전환 + 사용자 문구 정리
date: 2026-09-20
status: complete
---

# 260920-ra8 — 국면 힌트를 버리고 기하 hold 창으로

## 0. 판정

**됐다.** 정은지 본인 파워스핀 정타의 위양성(80점)이 사라진다. 저장 코퍼스 재계산에서
**정타 위양성 4건 제거 + 일부러 낸 실수 8건 신규 검출** — 한쪽을 얻고 한쪽을 잃는 교환이
아니라 양방향 개선이다. **새 임계값·새 상수 0개** (힌트를 빼는 일이다).

belle 판정 인용: *"너무 과하게 오르지 않고, 분석이 그게 맞다면 인정해야지"*,
범위는 *"1번"*(점수·화면 같이), 그리고 *"사용자 보기 편한 용어나 표기도 잊지말라구"*.

## 1. 무엇을 고쳤나

| | 전 | 후 |
|---|---|---|
| `dimensions._select_window` | `profile.hold_window`(Gemini 국면 힌트) **안에서** 분산-최소 부창 재선택 | 힌트를 쓰지 않고 항상 `hold_window(a)` |
| `technique.TechniqueProfile.hold_window` | 채점 창을 정했다 | **EXTEND 쪽만** 소비처 0. ★흔들림 채점은 아직 읽는다(정정, 아래 §5) |
| `gemini_technique_recognizer._hold_window_from_moments` | 그 창의 산출처 | 동일. **"지금 아무도 안 쓴다"** 주석 |
| 사용자 문구 | `신전 완성도` · `신전 부족` · `hold 구간 떨림` | `얼마나 곧게 폈나` · `덜 폈음` · `버티는 동안 떨림` |

소비처가 하나이므로(`_select_window` 공통 함수) **점수·화면 각도·대표 프레임이 같은 창을
본다** — TRUST-01 유지. 이것이 belle 이 "1번"으로 고른 이유다.

## 2. 왜 — 근거는 §17 이고 여기 요약만 둔다

Pod 실측(commit `a5ec1b08` · ROT180 on · 기준 `rot180_v1`): 정은지 파워스핀 정타가 80점,
감점 record 1건 = `leg_extension 88.69 (−20)`. Gemini 가 10.60초 클립의 hold 를 **1.0초**
(스핀 진입부)라 답했고 그 시각 무릎이 88.7도였다. 같은 영상 5벌(캐시 우회)로 다시 물으니
hold 가 **8.0초 아니면 1.0초**로 갈리고 중간값이 없다 — **2/5 가 틀린 쪽**.

```
가설                    부창        무릎R   line_score  leg_extension
Gemini hold 1.0초     [13, 19)     88.7        0          −20     ← 수리 전 라이브
기하 창                [79,105)    171.6       91            0     ← 수리 후
```

2026-08-31 수리(quick-260831-gyk)는 힌트 창 **내부**에서 부창을 재선택하는 것이라,
힌트 창 **전체**가 진입부면 무력하다. 그 이력은 지우지 않고 docstring 에 이어 적었다.

## 3. 산출 확인 (수리 후 실측)

**(a) 라이브 각도 박제로 사슬 확인** —
`evidence/260920-floor-anatomy/pod-run/powerspin_correct_angles.json`

```
힌트 있음 (Gemini hold 1.0초 → 창 (0,27))  부창=[79,105)  무릎R=171.6  line=91  감점 0
힌트 없음                                 부창=[79,105)  무릎R=171.6  line=91  감점 0
   → 힌트가 창을 못 옮긴다. 수리 전에는 [13,19) / 88.7 / line 0 / −20 이었다.
```

**(b) 저장 코퍼스 재계산** (power-spin, `line` 차원 보유 분석)

```
label      n    저장 line=0   수리후 line=0
correct   49        4    →        0     정타 위양성 4건 제거
fault     60       52    →       60     실수 8건 신규 검출
```

`[미확인]` ★ 이 코퍼스는 **영상 2편(정타 1 · 실수 1)의 재분석**이다
([[firestore-analyses-are-fixtures-not-students]]). 49·60 은 표본 크기가 아니라 재분석
횟수이므로 **두 영상 사이의 분리**이지 모집단 분리가 아니다. 학생 영상은 미측정이다.

## 4. 게이트 — 실패 16건을 건별로 판정했다

`backend/.venv/bin/python -m pytest backend/tests` (baseline 4958 passed / 20 skipped / 0 failed).
변경 직후 **16 failed / 4949 passed**. 단언을 느슨하게 만들어 통과시킨 건 **0건**이다.

| 분류 | 건수 | 판정과 처리 |
|---|---|---|
| **힌트 메커니즘 박제** | 3 | 의도가 뒤집혔다. `test_select_window_uses_profile_when_set` → `..._ignores_the_phase_hint`, `..._subwindow_always_inside_hint` → `test_no_hint_value_can_move_the_window` 로 **계약을 새로 박았다**. `test_helpers_share_window_with_score_functions` 는 의도(창 공유) 유지, 창 폭 단언만 2→5 갱신 |
| **fixture 가 홀드를 힌트로만 표현** | 9 | phase10 6건 + `test_record_measured_at` 3건. **fixture 를 고쳤다** — 진입부에 실제 움직임을 넣어 홀드가 각도 자체로 드러나게(`conftest.with_entry_motion`), 그리고 홀드를 새 창 폭(4프레임)에 맞게 늘렸다. 검증 수치(집계 40, 최근접 프레임 11)는 **그대로 보존** |
| **내 문구 변경(T3)이 깬 copy pin** | 4 | `180°` 도수 기호는 **문구 쪽을 되돌렸다**(사용자에게도 이게 낫다). `신전 부족`/`안정` pin 2건은 새 문구로 갱신하되 `==` 로 **더 정확하게** 박았다 |

**최종 게이트: **4965 passed / 20 skipped / 0 failed** (baseline 4958 + 신규 7건)**

신규 회귀 테스트 1건 — `backend/tests/test_extend_uses_geometric_hold_window.py`
("힌트가 진입부를 가리켜도 EXTEND 채점이 기하 창을 본다" + "홀드에서 진짜 굽으면 그대로 잡는다").

## 5. 남은 것 / 주의

- `[정정 2026-09-20 밤]` **"소비처가 0" 은 틀렸다.** `_select_window`(EXTEND)는 더 이상 안 보지만
  **`_select_stability_window`(dimensions.py:366)는 아직 `profile.hold_window` 를 읽는다.**
  그리고 mode3 는 core 차원이 없어 종합이 stability 단독이라
  (`overall_from_dimensions` — core 부재 시 절대트랙 단독), **이 국면 힌트가 mode3 점수에 그대로 닿는다.**
  같은 파일 :357 이 이미 별도 불일치를 경고해 둔 자리다 — 창 선택자는 *위치 분산 최소*로 고르는데
  stability 는 *프레임간 흔들림*으로 채점한다(스윕 12건에서 창을 바꾸면 −15~+5점 양방향 이동).
  → **파일럿 성공기준 1번(Mode3 성장 확인)에 직접 닿는 미결이다.** '실증 무관' 으로 분류하면 안 된다.
- `[확인]` `_hold_window_from_moments` 는 EXTEND 경로에서 소비처가 0 이다.
  지우지 않고 주석으로 표시했다 — 국면 인식을 고치면 다시 꽂히는 자리다.
  같은 함수의 `fps = 9.0` 하드코딩(실측 ~9.96)도 그때 같이 고칠 자리로 적어뒀다.
- `[미확인]` **안전 경고의 국면 대조(phase co-location)가 이제 기하 창을 쓴다.**
  phase10 게이트는 전부 통과했지만 그 fixture 는 합성이다. 실물 영상에서 안전 경고가
  어느 국면에 붙는지는 **안 쟀다**.
- `[미확인]` **학생 영상 0편.** 위 3-(b) 는 정은지 영상 2편의 재분석이다.
- `[미확인]` `safety_flags.py:748` 의 `역꺾임(과신전)` 문구는 안전 카피라 손대지 않았다.
  belle 이 원하면 별건으로.

**프로세스**: `/gsd-quick` 으로 착수했으나 기본 모델(Fable)의 크레딧 소진으로 플래너
에이전트가 죽어(HTTP 429), PLAN·실행·SUMMARY 를 직접 작성했다. 산출물 모양은 동일하다.
