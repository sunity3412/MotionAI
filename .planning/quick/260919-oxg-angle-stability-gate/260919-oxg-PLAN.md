---
id: 260919-oxg
title: 각도 표시 게이트에 시간축 안정성 축을 더한다 (신뢰도 문턱은 그대로)
date: 2026-09-19
status: planned
---

# 문턱을 내리지 않고, 축을 하나 더 세워 침묵을 연다

각도 표시가 카드 절반에서 침묵한다. 원인은 신뢰도 문턱 `_KP_CONF_MIN = 0.5` 하나이고,
**그 문턱은 좋은 좌표와 나쁜 좌표를 가르지 못한다**(아래 실측 2). 그래서 문턱을
내리는 대신 **시간축 안정성**이라는 두 번째 축을 세운다.

```
지금:  conf >= 0.5
이후:  conf >= 0.5                          (지금 통과하는 것 — 전부 그대로)
        OR  (conf >= 0.35 AND 시간축 안정)    (새로 열리는 것만 실제로 재서 통과)
```

**순수 additive.** 지금 그려지는 V 는 하나도 바뀌지 않는다. 새 경로는 기존 두 경로
(rep12 스펙 → align 폴백)가 **둘 다 None 일 때만** 불린다.

---

## 왜 (belle 2026-09-19 지시)

> "분석의 정도를 높여서 왠만하면 다 찾아내야지.
>  앱에 이미 있는 것과 부딪히면 뭐가 맞는지 둘 다 맞는지를 판단하는 것도 분석이야."

즉 (a) 표시가 침묵하는 것을 줄여라, (b) 충돌 판정은 belle 에게 올리지 말고 **재서**
답을 내라. 이 단위는 (a) 를 실행하고, 충돌 2건(승인 문법 4R#1 · 기준측 미측정)을
belle 에게 묻지 않고 **경계를 그어** 해소한다(아래 "충돌 판정 2건").

---

## 실측 — 재조사 금지, 그대로 쓴다

### 1. 게이트가 카드 절반을 막는다
`card_moment_conf.py` (라이브 Firestore, 각도 대상 카드 109장). 각도 표시 조건 =
꼭짓점 + 이웃 2점이 **모두** `conf >= 0.5`, 그리고 양측 대칭.

```
3점 최소 신뢰도 중앙값 = 0.504     현행 문턱 = 0.5   ← 문턱이 데이터 중앙값 위에 앉아 있다
현행 0.5 로 3점 통과  : 55/109 (50%)
    0.45 라면        : 73/109 (67%)
    0.40 라면        : 75/109 (69%)
    0.35 라면        : 99/109 (91%)
실패 54장의 병목: 이웃 관절 44장 / 꼭짓점 10장   ← 짚으려는 관절이 아니라 보조점이 막는다
```

### 2. ★ 그 문턱은 좋은 좌표와 나쁜 좌표를 못 가른다
`conf_vs_accuracy.py` (doc 25건 / 표본 1.5만).
지표 = `|각도(t) − 시간축 이웃(±2프레임) 중앙값|` (도). 좌표가 튀면 커진다.

```
신뢰도 구간      표본    중앙값편차   p75     p90    >20도
<0.30          1455     5.97    12.61   19.90    9.8%
0.30-0.35       515     5.25    11.77   19.81    9.7%
0.35-0.40       547     6.70    13.45   18.97    8.4%
0.40-0.45       614     5.20    11.68   18.49    5.5%
0.45-0.50       666     6.23    12.74   19.66    9.2%   ← 문턱 바로 아래 (버려진다)
0.50-0.60      1899     5.06    10.54   17.19    6.3%   ← 문턱 바로 위  (통과한다)
0.60-0.70      3573     3.15     8.11   14.50    4.0%
>=0.70         5663     1.70     4.95    9.74    1.6%
```

**문턱 바로 위아래가 사실상 같은 품질이다(6.23 vs 5.06도).** 신뢰도가 실제로 품질을
예측하는 것은 **0.6 위부터**고 그 아래는 0.30이든 0.49든 평평하다.
**0.5 는 아무것도 가르지 않는 선이다.**

### 3. 0.35 는 이 리포가 이미 쓰는 층이다 — 새 상수 발명 아님
`card_gates.py:63-67` 원문:

```
HOLD_CONF_MIN = 0.35       # 각도 측정 좌표 신뢰 하한 — 렌더러 표시 게이트(0.35) 재사용
                           # (fz._KP_CONF_MIN 0.5 는 확정 시각 언어용 — 속도 추정은
                           #  표본 수가 생명이라 렌더러 몸라인/피크와 같은 층을 쓴다)
PAIR_CONF_MIN = 0.35       # 포즈거리 기저 채택 신뢰 하한 — 같은 근거
```

0.30 이 아니라 0.35 를 고르는 이유 두 가지 (표에서 읽는다):
- 0.35 만으로 이미 99/109(91%) 가 열린다 — 더 내려서 얻는 장수는 적다(실측 1).
- `<0.30` 구간은 `>20도` 비율이 9.8% 로 표 전체 최악이다 — 튐 꼬리가 가장 굵다(실측 2).

### 4. 코드 실측 — 기존 시험은 한 건도 뒤집히지 않는다
`backend/tests/test_fault_zoom*.py` 의 confidence 리터럴 전수:
`0.9 / 0.95 / 0.7 / 0.6 / 0.57 / 0.56 / 0.5 / 0.3 / 0.2 / 0.1 / 0.0`.
**`[0.35, 0.5)` 구간 값이 0건이다.** 0.5 이상은 기존 경로 무변경, 0.3 이하는 새 하한
미달. 즉 이 변경으로 기대값을 고쳐야 하는 기존 시험은 **원리적으로 없다**
(전량 회귀가 이것을 증명한다 — 하나라도 깨지면 유도가 코드와 안 맞는다는 신호이니
멈추고 보고할 것).

---

## 코드 실측이 경계를 정한다 — 재조사 금지

### A. 고칠 자리는 한 곳뿐이다 (`fault_zoom.py:3751-3776`)

```python
                    u_spec = build_angle_bake_spec(
                        unit.criterion, unit.members, user_report, u_kp_idx_unit,
                        _gated_kp,
                    )
                    if u_spec is None:
                        u_spec = align_bake_spec(          # seam 1 (nh4)
                            unit.criterion, unit.members, _ab_user
                        )
                    r_spec = build_angle_bake_spec(... make_reference_anchor_resolver(...))
                    if r_spec is None:
                        r_spec = align_bake_spec(unit.criterion, unit.members, _ab_ref)
                    if u_spec is None:
                        angle_reason = "user_gate"
                    elif r_spec is None:
                        angle_reason = "ref_gate"
```

**seam 2 는 `if u_spec is None: angle_reason = "user_gate"` 바로 앞**이다.
여기 끼우면 하류(`shift_bake_spec` / `angle_mark_admissible` / 하이브리드 / degenerate /
원 마커 배타 / 억제 / 인증 플래그)는 **한 줄도 안 바뀐다** — 바뀌는 것은
"어느 spec 이 None 이 아닌가" 하나뿐이다.

### B. ★★ 위쪽 `build_angle_bake_spec` 호출(`:3529-3545`)은 절대 건드리지 말 것

그 호출의 산출(`_u_spec_frac`/`_r_spec_frac`)은 `criterion_crop_frac` → `crop_side_px`
로 흘러 **크롭 크기**를 정한다(`:3552-3563`). 여기에 완화 해상기를 넣으면
**지금 나가는 사진의 크롭이 바뀐다** = 순수 additive 파괴 + belle 규칙 1(사진 무접촉) 위반.
같은 함수를 부르는 두 자리의 목적이 다르다: 위 = 크롭 치수, 아래 = 그릴 좌표.
**아래만 고친다.**

### C. `_KP_CONF_MIN` 자체는 손대지 않는다
운영 소비처가 각도 밖에도 있다 (전수 grep 결과):
`fault_zoom.py:675`(포즈 매칭) `:980` `:1178`(`_gated_kp`) `:1407`(`_member_pts` = 크롭 kind),
`side_match.py:40,103`, `pipeline/app.py:5688,5717,5718`(align_bake 페이로드).
상수를 바꾸면 크롭 앵커·포즈 매칭·align 페이로드가 전부 같이 움직인다.
**새 하한은 새 이름의 별도 상수**로 둔다.

### D. 진입 게이트(`u_kind`/`r_kind == "valid"`)는 이번 범위 밖 — 사유 명시
`:3731-3734` 에서 `angle_reason` 이 `user_crop_relaxed`/`ref_crop_relaxed` 로 떨어지는
자리는 **크롭 앵커 축**(`_member_pts`)이지 그릴 좌표 축이 아니다. 여기를 열면 크롭
중심이 저신뢰 점으로 이동한 카드에 V 를 그리게 되어 **승인 4R#1("꼭짓점 = 패널
정중앙")이 깨진다**. 이 축의 라이브 비중은 이미 `angle_bake=omitted:user_crop_relaxed`
로 로그에 찍히고 있으므로, 다음 단위는 새 코드 없이 **세기만 하면** 판단할 수 있다.

---

## 충돌 판정 2건 — belle 에게 올리지 않고 재서 답을 낸다

### 판정 1. 꼭짓점은 완화하지 않는다 (승인 4R#1 과의 충돌)

크롭 중심은 `criterion_vertex_xy(..., _gated_kp)` 가 정한다(`:3490-3508`).
꼭짓점이 저신뢰면 `u_vertex = None` → 크롭이 멤버 앵커로 잡힌다. 그 카드에 완화
꼭짓점으로 V 를 그리면 **V 의 꼭짓점이 패널 정중앙이 아니게 된다** = 승인 4R#1 위반.

판정: **꼭짓점 = 엄격(`_gated_kp`) 유지, 방향 2점만 완화.**
근거는 실측 1 의 병목 분해다 — 막힌 54장 중 **44장(81%)이 이웃 관절**이고 꼭짓점은
10장뿐이다. 승인 문법을 깨지 않고 막힌 것의 81% 를 연다. 남는 10장은 좌표 정확도
문제이지 게이트 문제가 아니다([[keypoints-are-wrong-not-the-frame-choice]]).

이 판정에는 구현 함정이 하나 있다: 어깨 계열 꼭짓점은 겨드랑이 내분점이라
`{side}_shoulder` + **`{side}_hip`** 을 쓰는데(`:1518-1527`), `ANGLE_BAKE_MAP["shoulder"]`
의 몸통 방향점도 **같은 `{side}_hip`** 이다. 관절명만 보고 완화하면 꼭짓점까지 완화된다.
→ 해상기를 이름으로 가르지 말고 **역할로 가른다**: `build_angle_bake_spec` 에
`direction_resolver` 인자를 더해 꼭짓점 경로와 방향점 경로가 **다른 해상기**를 쓰게 한다.

### 판정 2. 기준(정은지) 측 적용 여부는 Task 1 이 재서 정한다

실측 2 의 표는 **학생 doc 25건**에서 나왔다. 기준 doc(11편, 18fps, legacy 8/12관절)은
다른 모집단이라 표를 그대로 옮기면 "재지 않은 것을 쟀다"고 말하는 셈이다.
→ Task 1 이 기준 doc 에 대해 **같은 표**를 만든다. 결과에 따른 행동은 Task 1 에
미리 적어 둔다(집행 중 판단 금지).

---

## 이번 단위의 경계 — 넘지 말 것

- **채점 무접촉.** 점수·감점·veto 경로 0줄. `dimensions.py`/`kismam.py`/`card_gates.py` 0줄.
- **사진 무접촉.** 카드 장수·존재 조건·크롭 치수·프레임 선정 무변경(경계 B).
- **`_KP_CONF_MIN` 상수 무변경**(경계 C). 기존 소비처 8곳 전부 그대로.
- **"확인 안 됨" 류 문구·배지·아이콘 신설 0** (belle 규칙 3). 앱 코드 0줄.
- **페이로드·계약 무변경.** 새 필드를 만들지 않는다 — 완화 경로를 탔다는 사실은
  **로그에만** 남긴다. (`app/src/types/analysis.ts` + `models.py` + `docs/contract.md`
  동시 개정은 이 단위의 범위가 아니다.)
- **`pngPlain` 무접촉.**
- **conf 부재(legacy report)는 계속 불허.** 2026-07-05 pod 실측에서 confidence 없는
  기준 report 가 통과해 선이 폭주했다(`_gated_kp` docstring). 완화 하한도 `None` conf 는
  거부한다 — 완화는 "낮은 신뢰"를 여는 것이지 "증명 없음"을 여는 것이 아니다.

---

## 완료 조건 (must-haves)

**관측 가능한 사실**
1. 지금 V 가 그려지는 카드의 PNG 는 바이트 동일하다 (새 경로가 안 불린다).
2. conf `[0.35, 0.5)` 방향점 + 시간축 안정 카드에서 V 가 새로 그려진다.
3. conf `[0.35, 0.5)` 방향점이지만 **불안정한** 카드는 계속 침묵한다(원 마커 폴백).
4. conf `< 0.35` 또는 conf 부재는 종전대로 침묵한다.
5. 꼭짓점이 저신뢰인 카드는 종전대로 침묵한다(판정 1).
6. 로그가 배선의 증인이다 — 완화 경로로 그린 카드는 `angle_bake=drawn:stable(...)`.

**산출물**
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — 상수 4 + 함수 2 + 인자 2 + seam 2.
- `backend/tests/test_fault_zoom_angle_stability.py` (신규).
- `.planning/quick/260919-oxg-angle-stability-gate/260919-oxg-CALIBRATION.md` (Task 1 표 + 임계 유도).
- `.planning/quick/260919-oxg-angle-stability-gate/260919-oxg-EVIDENCE.md` (Task 3 실개통 장수).

**기계 게이트**
- `cd backend && .venv/bin/python -m pytest -q` → 기준선 **4880 passed / 20 skipped / 0 failed**
  + 신규분. **failed 0.** 서브에이전트 보고 수치 금지 — `backend/.venv` 로 직접 돌린다
  ([[dont-trust-subagent-gate-numbers]]).
- 앱 무접촉이므로 `tsc` 불필요. 앱 파일이 `git diff` 에 뜨면 범위 이탈이다.

---

## Task 1 — 코드와 같은 자로 다시 재서 임계를 유도한다

**왜 다시 재나.** 실측 2 의 편차는 doc 최상위 `angles` = `compute_joint_angles(keypoints_4ch)`
= **joints3d 공간** 각도다. 반면 게이트가 보게 될 각도는 `build_angle_bake_spec` 이 돌려주는
**정규화 좌표** 3점의 사이각이다. 두 공간의 도(度) 값은 같지 않다. 실측 2 는 **모양**
(0.5 가 아무것도 안 가른다)을 증명하고, **숫자**는 코드가 실제로 쓸 공간에서 다시 읽는다.
이것이 "표에서 유도하되 커브핏 금지"의 실행 형태다.

> 왜 정규화 공간인가: 그려지는 각도는 이미지 평면 px 각(=`_to_crop_px` 가 x·y 를
> w·h 로 곱하므로 크롭 px 각과 같다)인데, **라이브 doc 은 영상 W·H 를 저장하지 않는다**
> (`keypointReport` 화이트리스트에 width/height 없음 — `firestore_admin._validate_keypoint_report`).
> 그래서 게이트도 계기도 **둘 다 정규화 공간**으로 통일한다. 종횡비 왜곡은 t 와 이웃
> 프레임에 같은 값으로 걸리므로 "튐 탐지"는 보존되고, 임계를 같은 공간에서 읽으므로
> 계기와 게이트의 자가 일치한다. (이 한계는 아래 "증명하지 못하는 것" 4번에 박제한다.)

**파일**
- `.planning/quick/260919-oxg-angle-stability-gate/calibrate_direction_conf.py` (신규)
- `.planning/quick/260919-oxg-angle-stability-gate/260919-oxg-CALIBRATION.md` (신규)

**작업**

`conf_vs_accuracy.py` 의 구조를 그대로 쓰되 **세 가지를 바꾼다**:

1. **각도 출처** — doc `angles` 가 아니라 `result.keypointReport` 좌표에서
   `ANGLE_BAKE_MAP` 삼각형(꼭짓점 + 방향 2점)의 사이각을 정규화 좌표로 계산한다.
   어깨 계열 꼭짓점은 겨드랑이 내분점(`fz._ARMPIT_T`) — `fz.criterion_vertex_xy` 를
   그대로 불러 쓴다(재구현 금지, 단일 출처).
   관절명 별칭(`wrist`↔`hand`)은 `card_gates._resolve` 와 같은 규칙으로 처리한다.
2. **버킷 x축** — 꼭짓점 conf 가 아니라 **방향 2점 conf 의 최소값**으로 버킷을 나눈다.
   우리가 여는 것이 바로 그 값이기 때문이다(판정 1). 버킷 경계는 실측 2 표와 동일.
3. **창 폭** — 실측 2 는 9fps 축에서 ±2 프레임 = **±0.222초**였다. report 는 fps 가
   다르므로(학생 라벨 fps / 기준 18.0) `w = max(1, round(0.222 * report.fps))` 로
   초 단위를 맞춘다. fps 라벨 오차 ~10%([[fps-label-vs-actual-decimation-rate]])는
   창 폭에 10% 영향이고 지표가 중앙값이라 무해하다 — 그래도 표에 기록할 것.
   이웃 표본은 실측 2 와 같이 **중앙 프레임을 뺀 이웃**의 중앙값을 쓴다.

같은 doc 모집단을 쓴다 (`users` limit 30 × `analyses` limit 25 → doc 25건).
Firestore 는 Spark 무료 플랜 읽기 5만/일이다 — **전수 스캔 금지**
([[firestore-spark-50k-read-cap-is-a-live-risk]]).

그리고 **기준(정은지) doc 11편**에 대해 같은 표를 하나 더 만든다
(`firestore_admin.list_reference_motions()`).

**산출: `260919-oxg-CALIBRATION.md`**

- 학생 표 / 기준 표 (같은 8개 버킷, 표본·중앙값·p75·p90·>20도).
- 이웃 표본 부족으로 측정 불가였던 (프레임, 관절) 비율.
- 채택 임계 1개와 **어느 칸에서 읽었는지**.

**임계 선택 규칙 (집행 중 판단 금지 — 아래대로만)**

```
_ANGLE_STABILITY_MAX_DEV_DEG = min(학생 표 0.50-0.60 행 p75,  기준 표 0.50-0.60 행 p75)
                               를 소수 첫째 자리로 내림(보수적)
```

- **왜 0.50-0.60 행인가**: 지금 **실제로 통과하고 있는** 밴드다. 새로 여는 점은
  "이미 나가고 있는 것과 같은 수준으로 안정하다"를 증명해야 한다.
- **왜 p75 인가**: 중앙값은 지금 나가는 것의 절반을 거절하는 선이라 여는 목적을
  스스로 없앤다. p90(원 표 17.19)은 `>20도` 튐 꼬리에 붙어 있어 튐을 통과시킨다.
  p75 = **지금 나가는 것의 4분의 3이 보이는 안정성** — 현행과 모순되지 않는 가장 좁은 칸.
- **왜 min(학생, 기준) 인가**: 두 모집단 중 **엄한 쪽**에 맞추면 상수 1개로 양측을
  덮으면서 어느 쪽에서도 현행보다 느슨해지지 않는다(판정 2 해소).

**멈추고 물어야 하는 조건 (CLAUDE.md §7)**

- 학생 표에서 `0.45-0.50` 행 중앙값이 `0.50-0.60` 행 **p75 를 넘으면** — 실측 2 의 결론
  ("문턱 위아래가 같은 품질")이 코드 공간에서 성립하지 않는다는 뜻이다. **중단하고 보고.**
- 기준 표가 표본 부족(어느 버킷이든 30 미만)으로 못 만들어지면 — `min()` 이 성립하지
  않는다. 이때만 **대체 규칙**: 임계는 학생 표에서 읽고, **완화 경로를 학생 측에만**
  배선한다(기준 측 해상기는 `_gated_kp` 그대로). 이 경우 Task 2·3 의 기준측 항목을
  "미적용"으로 표시하고 CALIBRATION.md 에 사유를 박제한다.

**검증**
```
cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python \
  .planning/quick/260919-oxg-angle-stability-gate/calibrate_direction_conf.py
```
→ 두 표가 출력되고 `260919-oxg-CALIBRATION.md` 에 저장된다. 채택 임계가 한 줄로 찍힌다.

**완료 기준**
- CALIBRATION.md 에 표 2개 + 임계 1개 + 읽은 칸 좌표(행·열)가 있다.
- 채택 임계가 `min(...)` 규칙의 산술로 재현 가능하다(직접 대입해 확인 가능).
- 코드 변경 0줄 (이 태스크는 계기만 만든다).

---

## Task 2 — fault_zoom 에 안정성 축을 심는다 (배선은 아직 안 한다)

**파일**
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py`
- `backend/tests/test_fault_zoom_angle_stability.py` (신규)

### 2-a. 시험을 먼저 쓴다 (이 시점에 FAIL 해야 한다)

픽스처는 `tests/test_fault_zoom_suppress_keeps_angle.py` 의
`_KP/_Match/_identity/_report/_frames/_unit/_UNITS/_build` 와 `test_fault_zoom_display_repair.py`
의 `_report_conf`(관절별 conf override)를 **복제**한다 — 테스트 모듈 간 import 금지 관행.
합성 report + 프로덕션 함수 직접 호출. GPU/S3/네트워크/눈 0.

박제할 것 (전부 `build_stable_angle_bake_spec` 직접 호출 — 배선 전이므로 순수 단위):

1. **엄격 경로 무간섭**: conf 0.9 report → `build_angle_bake_spec(..., _gated_kp)` 의
   산출과 `direction_resolver` 미지정 호출의 산출이 **완전히 같다**(기본값이 기존 동작).
2. **완화 + 안정 → 성립**: 방향점 conf 0.42(꼭짓점 0.9), 전 프레임 동일 좌표(편차 0도)
   → spec 이 3점 튜플로 나온다.
3. **완화 + 불안정 → None**: 같은 conf 인데 측정 프레임의 방향점만 크게 튀게 해
   편차가 임계를 넘게 만든다 → `None`. (튐 폭은 임계의 3배 이상으로 잡아 임계값
   변경에 시험이 흔들리지 않게 한다.)
4. **하한 미달 → None**: 방향점 conf 0.30 → 안정해도 `None`.
5. **conf 부재 → None**: `confidence` 키 없는 legacy report → 안정해도 `None`
   (경계 "conf 부재는 계속 불허").
6. **꼭짓점은 안 열린다 (판정 1)**: 꼭짓점 conf 0.42 / 방향점 0.9 → `None`.
   어깨 계열(`angle_vs_reference__left_shoulder`)로도 같은 결과여야 한다 —
   `left_hip` 이 꼭짓점 내분점과 몸통 방향점에 **동시에** 쓰이는 함정 박제.
   (`left_hip` conf 0.42 → 어깨 꼭짓점이 저신뢰가 되므로 `None`.)
7. **이웃 표본 부족 → None**: 프레임 수가 창을 못 채우거나 이웃이 전부 게이트 탈락 →
   `None` (fail-closed). `fps` 가 없거나 0 인 report 도 `None`.
8. **임계 경계**: 편차가 임계 바로 아래면 성립, 바로 위면 `None`
   (상수를 읽어 만든 입력으로 — 값 하드코딩 금지).

시험 모듈 docstring 에 **왜**를 적는다: belle 2026-09-19 지시, 실측 1·2 표의 해당 칸,
`quick-260919-oxg`, 판정 1(꼭짓점 비완화)의 근거(44:10), 그리고 "안정성은 튀는 것을
잡지 일관되게 틀린 것은 못 잡는다"는 한계.

**검증 (이 시점)**
```
cd backend && .venv/bin/python -m pytest tests/test_fault_zoom_angle_stability.py -q
```
→ 2·3·6·7·8 이 **FAIL**(함수 부재). 여기서 PASS 가 나오면 시험이 아무것도 안 재고 있는 것.

### 2-b. 상수 4개 — 유도를 주석에 박는다

`_KP_CONF_MIN = 0.5` (`:115`) **바로 아래**에 잇는다. 기존 상수는 한 글자도 안 바꾼다.

```python
# ── 각도 표시 2번째 축: 시간축 안정성 (quick-260919-oxg, belle 2026-09-19) ──
# belle: "분석의 정도를 높여서 왠만하면 다 찾아내야지."
#
# 왜 문턱을 안 내리고 축을 더하나 — 2026-09-19 라이브 실측(doc 25건 / 표본 1.5만,
# 지표 = |각도(t) − 시간축 이웃 중앙값|, 도):
#     신뢰도 0.45-0.50 : 중앙값 6.23  p75 12.74  >20도 9.2%   (버려진다)
#     신뢰도 0.50-0.60 : 중앙값 5.06  p75 10.54  >20도 6.3%   (통과한다)
# 문턱 바로 위아래가 같은 품질이다. 0.5 는 좋은 좌표와 나쁜 좌표를 **가르지 않는 선**
# 이고(예측력은 0.6 위부터 생긴다), 같은 실측에서 각도 대상 카드 109장 중 55장(50%)
# 만 통과했다. 그래서 문턱을 유지한 채 **실제로 재는 축**을 하나 더 세운다:
#     conf >= _KP_CONF_MIN  OR  (conf >= _ANGLE_DIR_CONF_MIN AND 시간축 안정)
# 순수 additive — 종전 통과분은 첫 항에서 그대로 통과하고 두 번째 항은 불리지 않는다.
_ANGLE_DIR_CONF_MIN = 0.35
# 0.35 근거 2줄: (a) card_gates.HOLD_CONF_MIN/PAIR_CONF_MIN 과 같은 값 — 이 리포가
# 이미 "측정용 하한"으로 쓰는 층이다(card_gates.py:63 주석: "fz._KP_CONF_MIN 0.5 는
# 확정 시각 언어용"). (b) 0.35 만으로 109장 중 99장(91%)이 열려 더 내려서 얻는 장수는
# 적은 반면 <0.30 구간은 >20도 비율 9.8% 로 표 전체에서 튐 꼬리가 가장 굵다.

_ANGLE_STABILITY_MAX_DEV_DEG = <Task 1 산출>
# 유도: 260919-oxg-CALIBRATION.md 의 **0.50-0.60 행 p75 칸**(학생/기준 중 작은 쪽,
# 소수 첫째 자리 내림). 그 밴드 = 지금 실제로 통과하고 있는 품질이므로, 새로 여는 점은
# "이미 나가는 것의 4분의 3이 보이는 안정성" 이상을 증명해야 한다. 중앙값은 지금
# 나가는 것의 절반을 거절해 여는 목적을 없애고, p90 은 >20도 튐 꼬리에 붙는다.
# 계기와 게이트는 **같은 정규화 좌표 공간**에서 잰다(라이브 doc 에 영상 W·H 가 없다).

_ANGLE_STABILITY_HALF_WINDOW_SEC = 2.0 / 9.0
# 실측 표가 쓴 창과 같은 시간 폭 — 9fps 각도축 ±2프레임 = ±0.222초. report fps 는
# 측마다 다르므로(학생 라벨 fps / 기준 18.0) 프레임이 아니라 **초**로 옮긴다.
# fps 라벨 오차 ~10% 는 창 폭 10% 오차이고 지표가 중앙값이라 무해하다.

_ANGLE_STABILITY_MIN_NEIGHBORS = 2
# 실측 표는 중앙을 뺀 이웃 4점의 중앙값을 기준선으로 썼다. 이웃이 1점이면 "중앙값"이
# 그 1프레임 자신이라 튐 하나가 기준선이 되어 판정이 우연에 걸린다. 2점 미만 = 측정불가
# = FAIL (fail-closed — 잴 수 없는 순간에 확정 시각 언어를 그리지 않는다).
```

### 2-c. 완화 해상기 + 안정성 측정 + 조립 (함수 2개 + 인자 2개)

**(1) `_relaxed_dir_kp(report, frame_idx, joint)`** — `_gated_kp`(`:1163`) 바로 아래.
`_gated_kp` 와 같은 형태, 하한만 `_ANGLE_DIR_CONF_MIN`. conf `None` 은 계속 거부.
docstring 에 "방향점 전용 — 꼭짓점에는 절대 주입하지 않는다(판정 1)"를 적는다.

**(2) `build_angle_bake_spec(..., direction_resolver=None)`** — 인자 1개 추가(`:2091`).
`direction_resolver` 미지정이면 `resolver` 를 그대로 쓴다 = **기존 호출 전부 무변경**.
지정되면 `limb`/`torso` 조회에만 쓰고 `criterion_vertex_xy` 에는 **`resolver` 를 넘긴다**.
docstring 에 "꼭짓점과 방향점을 다른 해상기로 가르는 이유 = 어깨 계열에서 `{side}_hip`
이 두 역할에 동시에 쓰이므로 관절명으로는 가를 수 없다"를 적는다.

**(3) `make_reference_anchor_resolver(..., gated_kp=_gated_kp)`** — 인자 1개 추가(`:1436`).
내부 3곳(`:1457, :1462, :1465`)이 모듈 상수 대신 이 인자를 쓰게 한다. 기본값이
`_gated_kp` 라 기존 호출 2곳(`:3527`, `:3764`)은 무변경. 기준측 방향 해상기를
앵커 대입과 함께 만들기 위해 필요하다.

**(4) `build_stable_angle_bake_spec(criterion, members, report, frame_idx, *, vertex_resolver, direction_resolver)`**
— `build_angle_bake_spec` 바로 아래. 순수 함수, 채점 무접촉.

```
① spec = build_angle_bake_spec(..., vertex_resolver, direction_resolver=direction_resolver)
   None → None  (꼭짓점 저신뢰 / 미선언 / 방향점이 0.35 미달 — 전부 종전 침묵)
② fps = report["fps"];  fps<=0 또는 부재 → None
   w = max(1, round(_ANGLE_STABILITY_HALF_WINDOW_SEC * fps))
③ dev 기준선 = [frame_idx-w, frame_idx+w] 중 frame_idx 를 **뺀** 프레임에서
   같은 인자로 spec 을 다시 만들어 사이각(도)을 구한 값들의 중앙값
   (프레임 범위는 report["frames"] 로 clamp, 성립 안 하는 프레임은 건너뛴다)
④ 유효 이웃 < _ANGLE_STABILITY_MIN_NEIGHBORS → None
⑤ |사이각(frame_idx) − 기준선| > _ANGLE_STABILITY_MAX_DEV_DEG → None
⑥ 그 외 spec 반환
```

사이각 계산은 **정규화 3점 사이각** — 새 헬퍼 1개(`_spec_inner_deg_norm`)로 두고
`_spec_inner_deg_px`(`:2225`)는 손대지 않는다(그쪽은 패널 px 공간 = 하이브리드 이식각용).
퇴화(길이 0 벡터)는 `None` → 그 프레임은 표본에서 제외.

**검증**
```
cd backend && .venv/bin/python -m pytest tests/test_fault_zoom_angle_stability.py -q
cd backend && .venv/bin/python -m pytest tests/test_fault_zoom.py \
  tests/test_fault_zoom_display_repair.py tests/test_fault_zoom_anchor_check.py \
  tests/test_fault_zoom_arrow.py tests/test_fault_zoom_ref_marked.py \
  tests/test_fault_zoom_relaxed_crop.py tests/test_fault_zoom_suppress_keeps_angle.py -q
```
→ 신규 8항 PASS. 기존 fault_zoom 계열 **기대값 변경 0**(실측 4 — 배선 전이라 당연하고,
`test_fault_zoom_ref_marked.py:201` 의 `assert fz._KP_CONF_MIN == 0.5` 도 그대로 PASS).

**완료 기준**
- 신규 8항 통과, 기존 계열 회귀 0.
- `git diff` 에서 `_KP_CONF_MIN` 줄 0 변경, `:3529-3545` 블록 0 변경(경계 B).
- 상수 4개 전부에 "어느 칸에서 읽었는가" 주석이 있다.

---

## Task 3 — seam 2 배선 + additive 불변식 박제 + 실개통 장수

**파일**
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` (`:3755-3772` 부근 + docstring)
- `backend/tests/test_fault_zoom_angle_stability.py` (배선 시험 추가)
- `.planning/quick/260919-oxg-angle-stability-gate/replay_open_count.py` (신규)
- `.planning/quick/260919-oxg-angle-stability-gate/260919-oxg-EVIDENCE.md` (신규)

### 3-a. 배선 시험을 먼저 쓴다 (FAIL 확인)

Task 2-a 와 같은 픽스처로 `build_fault_zoom_comparisons` 를 직접 부른다.
브랜드색 픽셀 헬퍼(`_brand_px_left_panel`/`_brand_px_right_panel`)는
`test_fault_zoom_suppress_keeps_angle.py` 에서 복제한다.

1. **★ additive 불변식 (이 과제의 핵심)**: conf 0.9 배치의 `png` 가 **바이트 동일**하다
   — 변경 전 산출을 기대값으로 박을 수 없으므로, **같은 실행 안에서** 완화 경로가
   불가능한 배치(전 관절 conf 0.9)와 완화 경로가 가능한 배치를 각각 만들어
   전자의 산출이 `_gated_kp` 단독 경로와 같음을 `angle_bake=drawn`(접미사 없음)
   로그로 인증한다. 완화 경로를 탔다면 로그에 `:stable(` 이 찍히므로 **로그가 증인**이다.
2. **새로 열린다**: 방향점 conf 0.42 + 안정 → `len(items)` 동일, `angle_bake=drawn:stable(user)`,
   학생 패널 브랜드 픽셀 > 0, **`userMarked is True`**.
3. **양측 대칭 유지**: 2번 카드에서 기준 패널도 브랜드 픽셀 > 0 + `refMarked is True`
   (both-or-neither 가 안 깨진다).
4. **불안정은 계속 침묵**: 방향점 conf 0.42 + 튐 → `angle_bake=omitted:user_gate`,
   원 마커 폴백(브랜드 픽셀 > 0 이지만 V 없음 — `userMarked True` 는 원 마커로 성립).
   `png` 가 1번 배치의 그것과 다르되 **완화 이전과 같아야** 한다.
5. **장수 불변**: 모든 배치에서 `len(items)` 가 같다 (belle 규칙 1).
6. **`pngPlain` 무접촉**: 모든 배치에서 양 패널 브랜드 픽셀 0.
7. **크롭 무변경 (경계 B 자물쇠)**: 방향점 conf 0.42 배치와 0.9 배치에서
   `pngPlain` 이 **바이트 동일**하다. `pngPlain` 은 같은 크롭·같은 초 도장에 표시만
   없는 판이므로, 크롭 치수가 움직였다면 여기서 깨진다.
   **이 시험이 `:3529-3545` 를 건드리는 구현을 즉시 잡는다.**

### 3-b. seam 2 배선 (`:3755-3772`)

```python
                    if u_spec is None:
                        u_spec = align_bake_spec(
                            unit.criterion, unit.members, _ab_user
                        )
                    if u_spec is None:
                        # ★ seam 2 (quick-260919-oxg, belle 2026-09-19) — 두 번째 축.
                        # 여기까지 왔다는 것은 rep12 엄격 경로도 align 폴백도 좌표를
                        # 못 준 것이고, 종전에는 이 자리에서 그대로 침묵했다(원 마커
                        # 폴백). 실측: 각도 대상 카드 109장 중 54장이 여기서 죽고 그중
                        # **44장(81%)의 병목이 꼭짓점이 아니라 이웃(방향) 관절**이다.
                        # 신뢰도 0.45-0.50 과 0.50-0.60 의 좌표 품질은 사실상 같으므로
                        # (중앙값 6.23 vs 5.06도) 문턱을 내리는 대신, 방향점만
                        # _ANGLE_DIR_CONF_MIN 까지 열고 **시간축 안정성을 실제로 재서**
                        # 통과시킨다. 꼭짓점은 엄격 유지 — 크롭 중심의 단일 출처라
                        # 완화하면 승인 4R#1(꼭짓점 = 패널 정중앙)이 깨진다.
                        u_spec = build_stable_angle_bake_spec(
                            unit.criterion, unit.members, user_report, u_kp_idx_unit,
                            vertex_resolver=_gated_kp,
                            direction_resolver=_relaxed_dir_kp,
                        )
                        if u_spec is not None:
                            _stable_sides.append("user")
```
기준 측도 대칭으로 잇되 방향 해상기는 앵커 대입을 얹어 만든다:
`make_reference_anchor_resolver(motion_id, unit.criterion, anchors=reference_anchor_overrides, gated_kp=_relaxed_dir_kp)`.
(Task 1 의 대체 규칙이 발동했다면 기준 측은 배선하지 않고 그 사유를 주석에 박는다.)

`_stable_sides: list[str] = []` 는 `_hybrid_note = ""`(`:3719`) 옆에서 카드마다 초기화한다.

로그(`:3842-3849`)는 접미사 한 칸만 늘린다 — 판정·드로잉 무접촉:
```python
_stable_note = f":stable({'+'.join(_stable_sides)})" if _stable_sides else ""
...  f"drawn{_hybrid_note}{_stable_note}" if u_drew_angle else f"omitted:{angle_reason}",
```
`angle_reason` 문자열은 **바꾸지 않는다** — `test_fault_zoom_display_repair.py:284,313,326`
가 부분문자열로 잠그고 있고, 완화 시도 후 탈락도 종전과 같은 사유(`user_gate`/`ref_gate`)가
맞다(잴 수 없어서 안 그린 것). 완화가 **성공한** 경우만 새 접미사로 드러난다.

`build_fault_zoom_comparisons` docstring 의 각도 절(`:3006-3020`)에 seam 2 를 한 문단으로
추가한다 — seam 1 서술과 같은 자리. "conf 게이트는 호출측 소유"라는 기존 문장과
모순되지 않게, 완화는 **방향점에만·안정성 확인 후에만** 적용됨을 명시한다.

### 3-c. 전량 회귀

```
cd backend && .venv/bin/python -m pytest -q
```
기준선 **4880 passed / 20 skipped / 0 failed** + 신규분. **failed 0.**
하나라도 깨지면 실측 4(기존 시험에 `[0.35,0.5)` conf 가 0건)가 틀렸다는 뜻이니
**멈추고 보고**할 것 — 기대값을 고쳐서 넘어가지 말 것.

### 3-d. 실개통 장수 (열어볼 수 있는 물건)

`replay_open_count.py` — `card_moment_conf.py` 와 **같은 라이브 doc 모집단**에서
각도 대상 카드를 다시 훑되, 신뢰도 산술을 재구현하지 말고
**프로덕션 함수 `build_stable_angle_bake_spec` 를 직접 호출**한다.

- `members` 는 `card_moment_conf.py` 와 같은 규칙으로 재구성하고
  (`criterion` 접미사 → report 이름공간, `wrist`↔`hand` 별칭 포함),
  표본 몇 건에서 `fz._criterion_vertex_joint(criterion, members)` 가 기대 관절을
  돌려주는지 **먼저 확인**한다. 확인이 안 되면 수치를 내지 말고 중단·보고할 것
  (재구성이 틀리면 장수 전체가 거짓이 된다).
- 센다: ① 엄격 경로로 이미 통과(= 종전 55장) ② **새로 열림** ③ 안정성 탈락
  ④ 이웃 표본 부족 ⑤ 꼭짓점 저신뢰라 의도적 미개통(판정 1) ⑥ 0.35 미달.
- 참고로 함께 센다: `_member_pts` valid 0 인 카드 수 = 진입 게이트(경계 D)에 막혀
  이 단위로는 못 여는 몫. **근사치라고 명시**할 것(실제 `u_kind` 는 `_side_crop` 산출).

**산출: `260919-oxg-EVIDENCE.md`** — 위 6+1 칸의 장수와 doc 수, 그리고 한 줄 결론
("109장 중 X장이 실제로 열렸다"). 추정·전망 금지, 센 것만.

**완료 기준**
- 배선 시험 7항 + Task 2 의 8항 전부 통과. 전량 회귀 failed 0.
- `git diff` 범위: `fault_zoom.py` + 신규 시험 파일 + `.planning/` 뿐.
  `card_gates.py` 0줄, `pipeline/app.py` 0줄, `app/` 0줄, 드로잉 함수(`_draw_*`) 0줄.
- EVIDENCE.md 에 실개통 장수가 **센 값**으로 적혀 있다.
- 로그에 `:stable(` 이 실제로 찍히는 시험이 있다(배선의 증인).

---

## 증명하지 못하는 것 (과장 금지 — 문서·주석에 박는다)

1. **시간축 안정성은 튀는 좌표를 잡지, 일관되게 틀린 좌표는 못 잡는다.**
   관절 좌표 자체의 정확도 문제는 이것으로 안 풀린다
   ([[keypoints-are-wrong-not-the-frame-choice]]). 매끄럽게 틀린 팔은 매끄럽게 통과한다.
2. **belle 눈 판정이 남아 있다.** 새로 열린 카드의 V 가 실제로 옳은 부위에 옳은 각으로
   앉았는지는 **완성된 사진**을 봐야 안다([[grammar-approval-is-not-asset-approval]],
   [[card-photo-audit-by-machine-eye]]). 지금은 Pod 이 전부 내려가 있어
   ([[pilot-postponed-to-mid-october]]) 렌더 대조를 할 수 없다. 이 단위는
   **게이트가 옳다**까지만 증명하고, **그림이 옳다**는 Pod 재기동 후로 남는다.
   내 눈으로 좁은 크롭 표식을 판정하지 말 것 — 2연속으로 틀렸다
   ([[my-tight-crop-eye-is-unreliable-twice-wrong]]).
3. **진입 게이트(크롭 relaxed)로 죽는 몫은 안 열린다**(경계 D). 그 몫의 크기는
   Task 3 의 근사치와 라이브 `angle_bake=omitted:*_crop_relaxed` 로그로만 안다.
4. **정규화 공간 도(度)는 그려지는 각(이미지 평면 px 각)과 같은 수가 아니다.**
   라이브 doc 에 영상 W·H 가 없어 계기·게이트를 둘 다 정규화 공간으로 통일했다.
   임계를 같은 공간에서 읽으므로 자가 일치하지만, `_ANGLE_STABILITY_MAX_DEV_DEG` 를
   "화면에서 보이는 N도"로 읽으면 안 된다.
5. **실개통 장수는 라이브 25 doc 표본의 값**이지 모집단 값이 아니다.
