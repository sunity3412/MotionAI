# Step 0 사전 기준 박제 — 관절 좌표 학습이 필요한가

> **이 파일은 측정 전에 커밋된다.** 커밋 시각 이후의 어떤 수치도 이 기준을 바꾸지 못한다.
> 규율 근거: [[belle-eye-is-the-answer-key-predict-before-asking]] · 09-06 어깨 문법 시험과 같은 방식
> (`.planning/quick/260906-n2j-stage-1-advisory/evidence/SHOULDER-GRAMMAR-PREREGISTRATION.md`).

작성 2026-09-07. 대상 = 09-06 라이브 6문서
(uid `NdVZrpbmUbPMNMjASFwUgy8Fj9p1`).

---

## 0. 대상 명부 — 8면이 아니라 5면 (자기 점검 결과)

09-06 판정문이 쓴 "불일치 8면" 중 **3면은 계기 자신의 조회 실패**다.

`panel_center_eye_measure_v2.py:104-110` 은 크롭 로그를 `(doc8, joint, crit)` 로 찾고
criterion-only 로 폴백한다. advisory 카드는 로그에 `region=arms criterion=none` 으로 적히므로
조회가 빗나가고, `info['vertex_centered']` 가 `None` 으로 남아 `:131` 의
`if info['vertex_centered'] is False` 분기가 안 탄다. 그 결과 **중심을 안 맞추도록 설계된 카드**가
v2 가 없애려던 바로 그 리터럴 `0.42` 크롭으로 측정돼 `mismatch` 로 계상됐다.

크롭 로그 원문이 그 카드들을 `vertex_centered=False` 라고 말한다
(`evidence/crop_logs_n2j.txt`: `4e232c4a region=arms criterion=none ... vertex_centered=False`,
`5ae210fa region=arms criterion=none ... vertex_centered=False`).

**오계상 3면:** `4e232c4a[04] user left_shoulder` · `5ae210fa[02] ref left_elbow` ·
`5ae210fa[02] user left_elbow`.

**정정 집계: ok 16 · not_center_anchored 15 · mismatch 5.**

### 대상 5면 (vertex_centered=True + 크롭 비율 기록 있음)

| # | doc | idx | side | joint | card_frac | rep idx | 프레임 원장 |
|---|---|---|---|---|---|---|---|
| 1 | 4e232c4a | 03 | user | left_knee | 0.5324 | 112 | user_frame=56 |
| 2 | 5ae210fa | 01 | user | left_shoulder | 0.4000 | 108 | user_frame=54 |
| 3 | a559705f | 01 | ref | right_hip | 0.4048 | 102 | ref_rep_idx=51 ref_video_idx=68 |
| 4 | a559705f | 02 | ref | left_shoulder | 0.4000 | 92 | ref_rep_idx=46 ref_video_idx=61 |
| 5 | d213622a | 00 | ref | left_hip | 0.5500 | 180 | ref_rep_idx=90 ref_video_idx=120 |

**대조군 13면** (`final=ok` + `vertex_centered=True` + card_frac 기록):
`21b1b7ed[00]` ref·user · `4e232c4a[00]` ref·user · `4e232c4a[02]` ref·user ·
`4e232c4a[03]` ref · `5ae210fa[01]` ref · `a559705f[00]` ref·user · `a559705f[01]` user ·
`a559705f[02]` user · `d213622a[00]` user.

대조군은 선택이 아니라 **필수**다. 대조군 없이 5면만 보면 계기가 우리 편인지 아닌지를 모른다.

---

## 1. 공통 임계 — 왜 이 값인가

좌표 불일치는 **크롭 중심을 부위 밖으로 밀어낼 때만** 결함이다.
배달 카드의 크롭 한 변 = `card_frac × min(W,H)`, `card_frac` 은 카드마다 크롭 로그에 기록돼 있다.

> **THRESHOLD_i = 0.25 × card_frac_i** (짧은 변 정규화 단위) = 크롭 반지름의 절반.

| 대상 | THRESHOLD | 360px 환산 |
|---|---|---|
| 4e232c4a[03] | 0.1331 | 47.9 px |
| 5ae210fa[01] | 0.1000 | 36.0 px |
| a559705f[01] | 0.1012 | 36.4 px |
| a559705f[02] | 0.1000 | 36.0 px |
| d213622a[00] | 0.1375 | 49.5 px |

대조군은 각자의 `card_frac` 으로 같은 공식을 쓴다.
**측정 A 와 B 가 같은 임계를 쓴다** — 두 결과를 한 표에 넣기 위해서다.

좌표 비교는 **픽셀에서** 한다. 저장 좌표는 x 를 W 로, y 를 H 로 **따로** 정규화하므로
(`fault_zoom.py:2461`) 정규화 좌표를 그대로 빼면 안 된다:
`dpx=(x₂-x₁)·W`, `dpy=(y₂-y₁)·H`, `d = hypot(dpx,dpy)/min(W,H)`.

---

## 2. 측정 A — 다른 기성 모델 대조

**모델:** MediaPipe Pose (BlazePose Heavy), `mediapipe==0.10.35`, `RunningMode.IMAGE`, num_poses=1.
독립성(다른 벤더·구조·학습 코퍼스), Apache-2.0(ADR-0001 화이트리스트), CPU 전용.
**IMAGE 모드 고정** — VIDEO 모드는 프레임 간 추적 상태를 물고 가서 독립성을 파괴한다.

### 면별 판정
- **AGREE**: `d_norm ≤ THRESHOLD_i` **그리고** `visibility ≥ 0.5`
- **DISAGREE**: `d_norm > THRESHOLD_i` **그리고** `visibility ≥ 0.5`
- **INCONCLUSIVE**: `visibility < 0.5` 또는 미검출 → MediaPipe 의 의견을 버린다.
  **불일치로 세지 않는다.**

신뢰도 하한 0.5 는 우리 자신의 `fault_zoom._KP_CONF_MIN = 0.5` 와 같은 값이다.

### A 단독 판정
- **학습 필요:** 5면 중 **3면 이상 DISAGREE**, **그리고** 대조군 13면 중 DISAGREE **≤ 2**.
  → 대조군 조항이 반증자다. 이미 맞는 면에서도 MediaPipe 가 우리와 다르면
  MediaPipe 는 심판 자격이 없고 A 는 무조건 INCONCLUSIVE 다.
- **학습 불필요:** 5면 중 **3면 이상 AGREE** 이고 **DISAGREE 0**.
  → 해석(미리 적어둔다): 실패한 카드가 쓴 바로 그 프레임에서 독립 모델이 우리 좌표를 확인했다.
  결함은 좌표보다 **아래쪽**(크롭 창·표시·눈의 부위 어휘)에 있고, 이 근거로는 학습이 정당화되지 않는다.
- **INCONCLUSIVE:** 그 밖의 모든 경우. INCONCLUSIVE = **학습하지 않는다.**

---

## 3. 측정 B — 다중 프레임 다수결

**모델 재실행 없음. Firestore 만으로 한다.** (GPU·Pod 불필요, 검증됨)

### 표본 구조 — 먼저 검사하고 아니면 그 면을 버린다
- 학생 리포트: `frames == 2 × (문서 최상위 anglesFrames)` 이고 홀수 인덱스가 이웃의 중점
  (오차 1e-9 이내)임을 확인 → 홀수는 선형 보간이라 **정보가 없다. 걸음 = ±2**.
- 기준 리포트: `frames == ref anglesFrames` 이고 위 중점 검사가 **실패**함을 확인
  (진짜 표본이라는 증거) → **걸음 = ±1**.

어느 쪽이 어느 쪽인지 하드코딩하지 않는다 — **잰다**.

### 표본 선별
중심 = 카드의 `userFrameIdx`(학생) / `refFrameIdx`(기준), rep 공간 그대로.
오프셋 −2·걸음 … +2·걸음, 배열 밖은 자른다.
버리는 표본: `_kp_conf == 0.0` (부재를 (0,0) 으로 적는다) · `is_collapsed_frame == True`.

### 투표
살아남은 표본의 **좌표별 중앙값**을 픽셀에서 계산한다.
연속량의 투표는 최빈값이 아니라 **중앙값**이다 — 산출물에 그렇게 적는다.

### 면별 판정
- **VOTE_MOVES**: `delta_norm > THRESHOLD_i`
- **VOTE_HOLDS**: `delta_norm ≤ THRESHOLD_i`
- **VOTE_UNAVAILABLE**: 살아남은 표본 3개 미만

### B 단독 판정
- **학습 불필요, 다수결이 곧 수리:** 아래 셋을 **전부** 만족할 때만.
  (i) 5면 중 3면 이상 VOTE_MOVES
  (ii) 움직인 면마다 측정 A 의 MediaPipe 좌표가 **투표 좌표**의 THRESHOLD 안에 있다
       — 투표가 그냥 움직이는 게 아니라 **독립 모델 쪽으로** 움직여야 한다
  (iii) 대조군 13면 중 VOTE_MOVES ≤ 2
       — 이게 반증자다. 이미 맞는 면까지 움직이는 투표는 평활기이고,
         그걸 넣으면 3면 고치려고 좋은 카드 13장을 깬다.
- **다수결은 수리가 아니다:** 5면 중 3면 이상 VOTE_HOLDS.
  → 이웃한 진짜 프레임들이 문제의 프레임에 동의한다 = 시간축 흔들림이 기전이 아니다.
- **INCONCLUSIVE:** VOTE_UNAVAILABLE 2면 이상, 또는 위 둘 어디에도 안 맞는 경우.
  INCONCLUSIVE = **학습하지 않는다.**

**금지:** 표본이 모자란다고 창을 ±3 으로 넓히는 것은 사후 기준 변경이다.
모자라면 판정은 VOTE_UNAVAILABLE 이다.

---

## 4. 교차표 — 학습을 허가하는 칸은 하나뿐

| A | B | 판정 |
|---|---|---|
| AGREE 다수 | HOLDS 다수 | 이 프레임들에서 좌표는 맞다. **학습 안 함.** 크롭/눈 층으로 올린다 |
| DISAGREE 다수 | MOVES (ii)(iii) 충족 | **학습 안 함.** 수리는 파이프라인의 시간축 중앙값 |
| **DISAGREE 다수** | **HOLDS 다수** | **학습이 지시된다.** 이웃한 진짜 프레임 전반에 걸친 계통 오차이고 독립 모델이 거부한다 |
| AGREE 다수 | MOVES | 모순. 계기끼리 다툰다. **학습 안 함.** 계기를 다시 만든다 |
| 어느 쪽이든 INCONCLUSIVE 포함 | | **학습 안 함** |

---

## 5. 사전 예측 (박제 — 결과가 나를 반증할 수 있게)

**측정 A:** 5면 중 **4면 이상 AGREE, DISAGREE 0** → "학습 불필요".
근거: 표본으로 돌려본 한 면(`5ae210fa[01]` user left_shoulder)에서 MediaPipe 가
임계 36.0 px 에 대해 **5.5 px** 떨어진 곳에 찍었다.

**측정 B:** 기준측 3면은 **VOTE_HOLDS**(저장된 이웃이 조밀하다 — `a559705f` right_hip 은
idx 100..104 에서 0.03 이내), 학생측 2면은 **VOTE_MOVES**(`4e232c4a[03]` left_knee 는
이웃이 y 0.41→0.57 로 흔들리고 4개 중 2개가 붕괴). = **2-3 갈림 = 규칙상 INCONCLUSIVE.**
그 결과가 나오면 정직한 보고는 "다수결로는 결판이 안 난다"이지 반올림한 판정이 아니다.

---

## 6. 미리 적어두는 한계 — 결과와 함께 반드시 보고할 것

1. **n = 5.** 학생 2 · 기준 3. 통계적 여유가 없다. 이건 **방향**이지 증명이 아니다.
   3-2 갈림은 3-2 갈림이라고 보고한다.
2. **기준측 3면은 오늘 모델을 학습시켜도 안 고쳐진다.** 라이브 기준 문서는
   `anglesExtractedBy: rtmw-x-384-direct-2026-06-12` / `anglesBackbone: rtmw-x-384-bukuroo-2026-06-06`
   으로, Pod 에 지금 켜져 있는 2-pass 인버전 보정(`PR_INVERSION_ENABLED=1`) **이전**이다.
   깨끗한 "학습 필요" 판정이 나와도 5면 중 최대 2면에만 적용된다.
3. **MediaPipe 가 우리와 같은 자리를 찍는다고 그 자리가 옳은 건 아니다.** 접힌 자세에서
   두 모델이 같은 방식으로 틀릴 수 있다. 그걸 가르는 것은 이름표 골격 오버레이
   (`260906-n2j-.../evidence/skel_overlay_measure.py`)이고, **세 번째 계기**다.
4. **심판(기계 눈)이 교정되지 않았다.** 09-06 판정은 `card_gates.eye_part_token` 이
   접힌 몸의 0.40~0.55 크롭에 자유 어휘로 "무슨 부위냐"를 답한 것이다.
   left_elbow 크롭에 "armpit", left_shoulder 크롭에 "neck" 은 그 크롭 배율에서
   **어휘 충돌**일 수 있지 좌표 오류가 아닐 수 있다. A 도 B 도 이걸 시험하지 않는다.
5. **B 는 "다수결이 크롭 중심을 옮기는가"를 답하지, "그러면 카드가 옳은 부위를 보여주는가"를
   답하지 않는다.** 후자는 재렌더가 필요하고 Step 0 밖이다.
6. 기준측 이웃은 실질 ~15fps, 학생측은 ~10fps 다. 같은 ±2 표본 창이 서로 다른 실제 시간을
   덮는다(0.13초 vs 0.20초). **두 쪽을 한 숫자로 합치지 않는다.**

---

## 7. 실행 순서 (고정)

1. 명부 정정을 커밋한다 — 눈에게 다시 묻지 않는다. 메타데이터 수리이지 재판정이 아니다.
2. **이 파일을 커밋한다.** 그 전에는 아무것도 측정하지 않는다.
3. 측정 B (Firestore 전용, 가장 싸다) — 단독으로 Step 0 을 끝낼 수 있다.
4. 측정 A (MediaPipe).
5. 교차표의 다섯 칸 중 하나로 판정을 낸다.
6. 판정이 "좌표는 맞다"면 학습을 시작하지 않는다. 다음 계기는 이름표 골격 오버레이이고
   그것도 같은 방식으로 사전 박제한다.
7. **기준 재추출은 어떤 판정에서도 Step 0 안에서 건드리지 않는다** — 기준 `angles` 가 움직이고
   채점이 그 위에 서 있다.
