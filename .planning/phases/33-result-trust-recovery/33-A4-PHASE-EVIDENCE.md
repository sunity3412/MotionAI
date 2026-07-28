# 33-A4 — 국면(phase) 귀속 증거 조사: power-spin 감점은 "언제"를 잰 것인가

- 조사 대상 doc: uid `csKWYvI3WCPYPysNQ9KkWecaUvq1` / analysis `071df9f894d64d1696f106e613f51f5c`
  (mode1 · ref-power-spin · 51점 · 파일명 `파워스핀(잘못된예시).mp4`)
- 조사 방식: Firestore doc 전체 덤프 + S3 원본 영상 2건 다운로드 + doc 저장 각도행렬로
  채점 산식 로컬 재현(byte-일치 확인) + 측정 순간 프레임을 직접 추출·열람. **코드/데이터/목업 무수정.**
- belle 질문: r00(무릎 신전 −20) · r01(벌림 −12)이 P3(무릎 모아 회전 — 굽힘이 정답인 국면)에서
  측정됐는가, P4/P5(신전·스플릿 국면)에서 측정됐는가. + 목업 ④ "멈춤 컷 1.89s = 감점을 잰 순간" 재검증.

---

## 0. 판정 요약 (한 줄씩)

| 질문 | 판정 |
|---|---|
| r00(무릎 신전 141°)은 P3 tuck 에서 쟀나? | **아니오 — 학생 영상 실시간 6.31~8.18s(마무리 신전·스플릿 국면) 20프레임 평균.** 국면은 맞게 잡혔으나 **운(자동 창)이지 설계가 아님** (§3) |
| r01(벌림 30°)은 어느 프레임에서 쟀나? | **특정 프레임 없음 — Gemini 가 두 영상 전체를 보고 낸 영상 단위 시각 추정치** (§4) |
| 감점 항목에 국면(phase) 조건이 코드에 있나? | **사실상 없음.** yaml 은 hold_moment 로 스코프를 선언하지만, 이 분석에서는 그 스코프를 구현하는 유일한 장치(profile.hold_window)가 **캐시 히트로 소실**되어 "분산 최소 자동 창"으로 폴백 (§3, §5) |
| 목업 ④ "멈춤 컷 1.89s = 감점을 잰 바로 그 순간(u34)" | **오류.** u34(=s017)는 감점 측정 순간이 아니라 **줌/비전 표시용 창의 프레임**이다. 실제 r00 측정 구간은 6.31~8.18s. 게다가 s017 의 실영상 시각은 1.89s 가 아니라 **1.70s** — 그 순간 학생은 **tuck 진입 국면**이라, 그 컷에 스플릿 코칭 음성을 얹으면 belle 가 의심한 국면 오귀속이 **표시 층에서 실제로 발생**한다 (§6) |
| belle 의 의심("처음 결함이 어디냐를 못 잡고 있는 듯") | **구조적으로는 정당.** 이 doc 의 r00 숫자는 우연히 옳은 국면에서 나왔지만, 국면을 보장하는 메커니즘은 존재하지 않고(§5), 신선-경로였다면 tuck 국면(무릎 78°)을 쟀을 것이다 — 반증 계산 §5-1 |

---

## 1. 두 영상의 실측 타임라인 (파이프라인 명목시각 ≠ 실영상 시각)

먼저 시각 환산부터. 파이프라인은 "9fps 추출"을 가정하지만 실제 추출은 `round(src_fps/9)=3` 프레임
간격이라(30fps 원본 → **실효 10.0fps**), 명목시각 = idx/9 는 실영상 시각보다 항상 크다.

- 학생 영상: 8.21s · 29.95fps · 원본 246frame → 각도행렬 83frame (원본 3i 프레임). 실시각 = idx×0.1002s
- 기준 영상: 10.53s · 30fps · 원본 316frame → 기준 각도행렬 159frame (원본 2j 프레임, 실효 15fps;
  doc 메타 `keypointReport.fps=18.0` 은 명목값). 실시각 = idx×(1/15)s
- 검증: `ffprobe` 실측 (frame_extractor.py:44 `step = round(src_fps/target_fps)` 코드 근거)

| 인덱스 | 명목시각 | **실영상 시각** |
|---|---|---|
| 학생 f17 (= kp34, 목업 s017) | 1.89s | **1.70s** |
| 학생 f19 (worst-pose 중심) | 2.11s | 1.90s |
| 학생 f63~f82 (r00 측정 창) | 7.00~9.11s | **6.31~8.18s** |
| 기준 r44~r48 (비전 정량화 창) | 2.44~2.67s | **2.93~3.20s** |
| 기준 r90 (faultZoom refFrameIdx) | 5.00s | 6.00s (각도공간) / 크롭 실물은 4.50s (§6-2) |

belle 국면표(기준 영상, 실시각 육안 재확인): P3 tuck ≈ 2.9~6.5s 로 belle 언급(~0:03)보다 길게 지속,
P4 신전 ≈ 7.0s(`evidence_a4/ref_real7.00s_P4_extend.png`), P5 위아래 스플릿 ≈ 9.0s
(`evidence_a4/ref_real9.00s_P5_vsplit.png`). 학생 영상의 자체 국면: ~0.6s 직립 → 0.8~6.2s 회전
(1.9~6.2s 대부분 tuck) → **6.3~8.2s 스플릿 시도(마무리)**.

---

## 2. 세 record 의 측정 출처 전수표

| record | 값 | 측정 방식 | 측정 순간(실영상) | 코드 경로 |
|---|---|---|---|---|
| r00 `leg_extension` | 140.86° → −20 | **기하 — 자동 hold 창 20프레임 평균** (단일 순간 아님) | 학생 **6.31~8.18s** (f63~f82) | `dimensions.extension_deviation` → `_select_window` → `hold_window` (dimensions.py:277-283, 186-199) → `app.py:2394-2396` max(무릎) → `deduction_engine._criterion_deduction` (deduction_engine.py:498) `180−39.14=140.86` |
| r01 `split_angle` | 30° 편차 → −12 | **비전 — Gemini full-video 시각 추정** (프레임 미고정) | 특정 순간 없음 (두 영상 전체) | Gemini fan-out(전체 영상 입력, app.py:2067-2074 주석) → differences 의 각도 추정 → `vision_veto.fault_joint_deficits_from_differences` (vision_veto.py:873-898) → `deduction_engine._median_lower(split candidates)` = 30 |
| r02 `angle_vs_reference__left_shoulder` | 34.49° → −17.4 | **기하 — DTW 전 경로 median** (단일 순간 아님) | 학생 **전 구간** 0~8.2s ↔ 기준 전 구간 | `per_joint_deviation(match.path, …)` (app.py:4196) — 전 83frame↔159frame 경로의 관절별 median|Δ| |

**재현 검증 (byte-일치):** doc 저장 `angles`(83×8)로 로컬 재계산 —
자동 hold 창 = frames [63,83) (t//4=20 프레임, 분산최소), 창 평균 left_knee = **140.86°** = doc
measuredValue 140.86 정확 일치. DTW 재실행 → distance 60.414 = doc `alignment.distance` 일치,
left_shoulder 전경로 median = **34.49** = r02 measuredValue 일치. path 에서 u19↔r46, u17↔r44 —
doc `windowMedianAngleDeltas.sourceFrameIndices {user:[17..21], reference:[44..48]}` 와 일치.

---

## 3. r00 (무릎 신전 −20): 어느 국면을 쟀나 — 시각 실증

측정 창 = 학생 실시간 **6.31~8.18s**, 학생 자신의 P4/P5 상당(스플릿 시도~마무리) 국면. 프레임 직접 열람:

| 프레임 | 실시각 | 무릎각 (L/R) | 육안 분류 |
|---|---|---|---|
| f63 `stu_f63_real6.31s_r00window_start.png` | 6.31s | 103/127 | 스플릿 열기 시작 — 한 다리 위, 한 다리 밖 |
| f66 `stu_f66_real6.61s_r00window_vsplit.png` | 6.61s | 171/167 | 세로 스플릿 — 두 무릎 폄 |
| f70 `stu_f70_real7.01s_r00window_split.png` | 7.01s | 167/168 | 넓은 스플릿 유지 — 폄 |
| f75 `stu_f75_real7.51s_r00window_rebend.png` | 7.51s | **93/160** | **왼다리 도로 접음** — 다리 뒤로 접힌 순간 |
| f82 `stu_f82_real8.18s_r00window_end_vsplit.png` | 8.18s | 165/168 | 위아래 스플릿 재신전(마무리) |

**결론 (b):** r00 은 tuck(P3)이 아니라 **신전이 요구되는 마무리 국면에서 측정됐다** — 국면 자체는
정당. 141°는 "한 순간의 각도"가 아니라 **폄(165~171°)과 도로 접음(f72~f78, 왼무릎 92~140°)이 섞인
20프레임 평균**이다. 감점의 실체적 근거가 되는 순간은 **7.3~7.7s 의 왼다리 재굽힘**이다.

비교: 같은 구간 tuck 프레임 증거 — 학생 1.9~2.4s 는 완전 tuck
(`stu_f19_real1.90s_worstpose_center.png`, `stu_f21_real2.10s_tuck.png`, `stu_f24_real2.40s_tuck_deep.png`).
측정 창이 이 구간을 포함하지 **않았다**는 것이 r00 국면 정당성의 핵심 증거다.

---

## 4. r01 (벌림 30° −12): 측정 순간이 존재하지 않는다

- 30.0 의 출처: Gemini fan-out 이 **두 영상 전체**를 입력으로 받아(스틸 아님 — app.py:2067-2074,
  Phase 24 close-out A) "양다리가 벌어지는 각도가 눈에 띄게 좁음"(doc rootCauseHypotheses[2] 원문)
  이라는 difference 에 각도 추정을 붙인 값. `faultJointDeficits` 에서 hip/knee 4관절 모두 30.0,
  어깨 2관절 55.0 — 관절별 실측이 아니라 결함 단위 시각 추정치가 부위로 복제된 형태다.
- 따라서 "r01 을 잰 프레임"은 doc 어디에도 없다. `windowMedianAngleDeltas` 의 창(user 17~21)은
  **기하 정량화·표시용 창**이지 r01 의 측정 순간이 아니다(r01 값 30 은 이 창의 기하값과 무관 —
  창의 hip 편차는 −37.97/−51.33).
- 국면 판정: Gemini 의 서술("벌어지는 각도가 좁음")은 의미상 스플릿 국면 비교로 읽히고 영상 단위
  판단이라 P3 오귀속의 **직접 증거는 없음**. 단, 프레임 고정이 없으므로 "P4/P5 에서 쟀다"는 것을
  **증명할 수도 없다** — 정직한 상태는 "영상 전체에 대한 시각 판단"이다.

---

## 5. 국면 게이트는 코드에 존재하는가 — 메커니즘 규명 (c)

**선언은 있으나 구현이 끊겨 있다.** 체인 전체:

1. `backend/judging_data/criteria/ref-power-spin.yaml:13` — 무릎 신전 기준은 `hold_moment:` 아래
   선언 (setup/peak/release 는 빈 리스트). 즉 "hold 국면에서 잰다"가 설계 의도.
2. 이 스코프를 시간축에 구현하는 유일한 장치 = `TechniqueProfile.hold_window`
   (technique.py:56) — Gemini KeyMoments[hold] timestamp → 프레임 창
   (gemini_technique_recognizer.py:309-320).
3. **끊긴 지점 1 — 캐시 히트는 hold_window 를 버린다:** `_profile_from_cache`
   (gemini_technique_recognizer.py:383-392)는 `hold_window=` 를 복원하지 않는다(필드 자체가 없음).
   이 분석은 캐시 히트였다 — `timingsMs.recognizer=351ms` (Gemini 신선 호출은 수십 초;
   coach_dual=31,599ms 와 대비). → `_select_window` 가 **분산 최소 자동 창**으로 폴백
   (dimensions.py:305-318). 자동 창은 "가장 안 흔들린 구간"이지 "완성 국면"이 아니다.
4. **끊긴 지점 2 — Gemini 국면 라벨 자체가 틀렸다:** 이 영상의 기술 캐시 doc
   (video_hash `574a774c…`, gemini_cache) 실물 — setup 0.0s / **hold 2.1s** / peak 3.0s /
   release 4.0s. 학생의 실제 완성(스플릿)은 실시간 6.3~8.2s 인데 Gemini 는 hold 를 2.1s
   (**tuck 한복판**)에 찍었다.

### 5-1. 반증 계산 — 신선 경로였다면 무엇을 쟀나

캐시 미스(신선 Gemini)였다면 hold_window = (2.1±2)s × 9 = frames [1,37) = 실시간 0.10~3.71s.
doc 각도로 그 창의 평균을 계산하면 **right_knee 78.25°** → measuredValue 78° (부족분 102°).
즉 **tuck 국면 한복판을 "무릎 안 폈음"으로 잰다** — belle 가 의심한 바로 그 오귀속이 신선 경로의
기본 동작이다. 이 doc 이 옳은 국면(6.3~8.2s)을 잰 것은 (i) 캐시 히트로 Gemini 창이 버려지고
(ii) 자동 분산최소 창이 **우연히** 마무리 구간에 앉았기 때문이다. 다른 영상에서는 자동 창이
어디에든 앉을 수 있다(예: 긴 tuck 회전이 가장 안정적인 영상이면 tuck 을 잰다).

**결론 (c/d):** 국면 게이트는 **작동하지 않는다**. 이 doc 은 phase-correct(운) / 시스템은
phase-unguaranteed. 메커니즘 명명: ① yaml hold_moment 스코프의 유일한 구현이 cache-hit 시 소실,
② 소실 후 폴백(분산최소 창)은 국면 무관, ③ 국면 라벨 공급자(Gemini KeyMoments)의 timestamp 는
이 영상에서 실측과 4초 이상 어긋남 — 3중 결함.

---

## 6. 목업 ④ "1.89s 멈춤 컷" 재검증 (e) — u17 vs u34 포함

### 6-1. 판정

- **u34 = s017 인덱스 동치 자체는 맞다.** doc `faultZoomComparisons[].userFrameIdx=34` 는
  keypointReport(명목 18fps) 공간, s017 은 프레임(명목 9fps) 공간 — 같은 순간의 두 표기다(34=2×17).
- **"감점을 잰 바로 그 순간"이라는 서술이 틀렸다.** u34 는 비전 정량화 창(user 17~21) 안에서
  **표시용으로 뽑힌 크롭 프레임**이다(fault_zoom.py:222 "candidates = sourceFrameIndices" +
  app.py:3105-3126 주석 — "crop 프레임 = vision 측정 window"). 세 감점 중 어느 것도 이 순간에
  측정되지 않았다: r00 은 6.31~8.18s 창 평균(§3), r01 은 프레임 미고정(§4), r02 는 전 경로
  median(§2).
- **시각도 어긋난다:** s017 의 실영상 시각은 1.70s(명목 1.89s). 그 순간 학생은
  **P2→P3 전환(다리 수평, 이후 즉시 tuck)** —
  `evidence_a4/stu_f17_real1.70s_nominal1.89s_pausecut_u34.png` 육안: 다리가 수평으로 뻗다가
  0.2초 뒤 완전 tuck(f19~f24 증거). 여기서 멈추고 "위아래 한 줄 스플릿" 음성을 읽으면,
  **화면은 굽힘이 정당한 국면을 보여주며 스플릿 감점을 서술**하게 된다 — belle 의심의 표시-층 실증.
  (4라운드에 "아래로"가 이해 안 된 것도 같은 뿌리다: 멈춤 컷이 감점 국면의 그림이 아니었기 때문.)

### 6-2. 부수 확인 — 기준 쪽 크롭 순간도 어긋나 있었다 (표시 전용, 채점 무접촉)

`refFrameIdx=90`(=디스플레이 45)의 크롭 실물 순간은 실영상 **4.5s**, 그런데 DTW 가 실제로 짝지은
측정 순간은 기준 각도공간 r46 = 실영상 **3.07s** 다. 구 렌더(07-22)가 기준 창 인덱스(각도공간,
실효 15fps)를 디스플레이 프레임(실효 10fps) 인덱스로 그대로 써서 생긴 공간 혼동이다.
두 순간 모두 P3 tuck 이라(`ref_r46_real3.07s_dtwmatch_P3tuck.png` vs
`ref_real4.50s_storedcrop_panel_P3tuck.png` — 자세 유사) 육안으로는 안 들켰다. 목업 ⑤ 의
"refFrameIdx 90(kp 18fps) = v45 (t≈4.5s)" 표기는 크롭 실물과는 일치하지만, 명목 18fps 환산
(90/18=5.0s)과 실물(4.5s)의 모순은 이 공간 혼동의 흔적이다. 채점에는 영향 없음.

### 6-3. DTW 정렬 자체는 국면 정합이었다

u19(실 1.90s, tuck 진입) ↔ r46(실 3.07s, tuck) — tuck↔tuck 매칭으로 국면상 옳다
(`stu_f19_real1.90s_worstpose_center.png` vs `ref_r46_real3.07s_dtwmatch_P3tuck.png`).
"DTW 가 학생 스플릿을 기준 tuck 에 붙였다"는 시나리오는 이 doc 에서는 **발생하지 않았다**.

---

## 7. (기록만 — 수정 없음) 이 doc 의 정직한 코칭이 되려면

belle 판단 입력용. 이 플랜에서는 어떤 데이터/코드/카피도 바꾸지 않았다.

- r00 의 정직한 서술: "마무리 스플릿 구간(실영상 6.3~8.2초)에서 무릎이 평균 141° — 특히
  **7.3~7.7초에 왼다리를 도로 접었다**(93°까지). 스플릿을 편 순간들(6.6~7.0s, 8.0~8.2s)은 165~171°로
  좋았다." → 멈춤 컷의 올바른 후보는 **f75(실 7.51s)** 또는 창 내 재굽힘 프레임이지 1.7s 가 아니다.
- r01 의 정직한 서술: "영상 전체 비교에서 AI 시각 판단으로 다리 벌림이 기준보다 좁다고 추정(30°) —
  특정 순간 실측 아님." 표시 앵커를 쓴다면 학생 최대 스플릿 순간(≈7.0s) vs 기준 P5(≈9s)가 정직하다.
- 구조 후속(별도 플랜 소관): ① `_profile_from_cache` 의 hold_window 미복원, ② 자동 분산최소 창의
  국면 무관성, ③ Gemini hold timestamp 불신뢰(이 영상 4초+ 오차), ④ 명목 9/18fps vs 실효
  10/15fps 시각 표기 오차(사용자 노출 초 표기가 최대 ~0.9s 어긋남) — 4건이 국면 귀속의 실제 결함 지점.

## 증거 파일 (전부 직접 열람함)

`evidence_a4/` — 학생 9컷(측정 창 5 + tuck 대조 3 + 멈춤 컷 1), 기준 5컷(측정 창 2 +
크롭 실물 순간 1 + P4/P5 앵커 2). 각 파일명에 실영상 시각 포함. 원본 = S3 실물 영상에서
파이프라인 동일 그리드(학생 3i / 기준 2j 원본 프레임)로 추출, 합성·보정 0.
