---
status: awaiting_human_verify
trigger: "확대비교(fault-zoom) 크롭이 모든 결함 관절에 대해 같은 단일 프레임에서 잘려 나온다 — 결함별 최악 순간이 아니라 한 순간의 부위별 확대일 뿐. belle §6.6 재발 버그"
created: 2026-07-25
updated: 2026-07-28
---

# fault-zoom 크롭이 전부 한 프레임에서 잘림 (결함별 최악 순간 미반영)

## Symptoms
- Expected: 확대비교 카드 N장이 **각 결함 관절의 자기 최악 순간**에서 크롭된다 (무릎은 무릎이 제일 틀어진 프레임, 어깨는 어깨가 제일 틀어진 프레임).
- Actual: 모든 크롭이 **동일 userFrame(140) + 동일 refFrame**에서 나온다. 관절만 다르고 순간은 하나. 결함이 그 프레임에서 안 두드러지면 확대해도 안 보임.
- Timeline: 재발 버그. belle이 33-PLANNING-APPROACH §6.6에 이미 기록("확대비교 3장이 전부 같은 순간 / doc faultZoomComparisons 덤프 1분").
- Repro: elbow-twist-sister/fault Mode1 분석 → result.faultZoomComparisons 의 모든 항목 userFrameIdx 동일.

## Evidence
- timestamp: 2026-07-25 라이브 Pod 9w5es4y760il9w, elbow-twist-sister/fault 2회 재분석 (fix 前)
  - shadow phase33-cm3-run1: crop left_knee userFrame=140 / right_shoulder userFrame=140 (둘 다 140, refFrame 162)
  - production phase4_v1: crop left_knee / left_hand / left_shoulder 전부 userFrame=140 (refFrame 324)
  - 모든 크롭 동일 userFrame + 동일 refFrame. 관절만 다름.
- timestamp: 2026-07-25 라이브 Pod 213.173.107.230:17519 (commit 149b770), elbow-twist-sister/fault (fix 後)
  - AID=elbowtwistINVCHK260725pjfix, shadow phase33-cm3-run1, PR_INVERSION_ENABLED=1. STATUS=done SCORE=60.
  - CROP left_knee (confirmed): userFrame=140 refFrame=162
  - CROP right_shoulder (advisory): userFrame=148 refFrame=166
  - CROP right_hand (advisory): userFrame=148 refFrame=166
  - **결론: 크롭이 더 이상 전부 140 아님** — 무릎 카드(140)와 팔 카드(148)가 다른 프레임(≈0.44s@18fps 차)에서 잘림. fix 前 knee/shoulder 동일 140 → fix 後 knee 140 / shoulder 148. 뭉개기 해소 실증.
  - 팔 2관절(right_shoulder+right_hand)이 둘 다 148 = 같은 팔이라 co-visible(정상, 붕괴 아님). 차별화는 부위/가시성 기준으로 창발.
  - ⚠ 환경: cudnn9 부재로 onnxruntime CUDA EP 로드 실패 → RTMW **CPU 폴백**(WALL 502s). 프레임 선택(fix)은 keypoint conf 기반이라 CPU/GPU 무관하게 동작하지만, keypoint 품질은 GPU 대비 다를 수 있음(육안 시 참고). 이번 fixture 는 confirmed 카드 1장뿐 — confirmed 배치 내 다관절 차별화는 다관절 confirmed fixture 로 재확인 여지.
  - S3 crop keys (belle 육안):
    - results/phase25eval/elbowtwistINVCHK260725pjfix/zoom_left_knee.png
    - results/phase25eval/elbowtwistINVCHK260725pjfix/zoom_adv_right_shoulder.png
    - results/phase25eval/elbowtwistINVCHK260725pjfix/zoom_adv_right_hand.png

## Evidence — DTW 정렬 fix 재렌더 (2026-07-25, commit ea55069, Pod 213.173.107.230:17519 GPU 복구)
- GPU 복구: onnxruntime CPU 폴백 원인 = 비대화형 ssh 셸이 ~/.bashrc(LD_LIBRARY_PATH cudnn/cublas 이미 설정) 미소스. fix = 실행 셸에 LD_LIBRARY_PATH(nvidia/{cudnn,cublas,...}/lib) + RTMW env 명시 export. 직접 InferenceSession 프로브: rtmw-x-384.onnx / yolox_m.onnx 둘 다 `providers=['CUDAExecutionProvider','CPUExecutionProvider']` (CUDA 활성). 재렌더 WALL=156.2s (구 CPU 502s → −346s = RTMW GPU 가속분; 잔여 156s 는 Gemini veto 네트워크 대기). ★ 영구 fix 아님 — .bashrc 는 이미 맞음(대화형만), 비대화형 렌더는 env 명시 필요. flip 용 서버(uvicorn pid3289)는 대화형 기동이라 GPU 정상.
- AID=elbowtwistINVCHK260725align, SHADOW=phase33-cm3-run1, PR_INVERSION_ENABLED=1. STATUS=done SCORE=60 (149b770 과 동일 — 채점 무접촉 실증).
- sourceFrameIndices(9fps): USER_WINDOW=[70,71,72,73,74] REF_WINDOW=[73,74,75,76,77] (DTW 오프셋 +3@9fps=+6@kp18fps 일정). keypointReport fps=18.
- **카드별 DTW 정렬 (userFrameIdx/refFrameIdx=kp18fps 공간, →9fps=÷2, window position):**
  - left_knee (confirmed): user kp140→9fps70=pos0 / ref kp146→9fps73=REF pos0 → **같은 window index 0 ✓**
  - right_shoulder (advisory): user kp144→9fps72=pos2 / ref kp150→9fps75=REF pos2 → **같은 index 2 ✓**
  - right_hand (advisory): user kp148→9fps74=pos4 / ref kp154→9fps77=REF pos4 → **같은 index 4 ✓**
  - 세 카드 전부 student↔reference 같은 window position(DTW 짝). user→ref 갭 일정(kp +6) = position-lock 시그니처. fix 前(149b770): knee 140→162(갭22)/shoulder 148→166(갭18) 가변 = 독립선택 붕괴.
- S3 crop keys (belle 육안 — 카드 내 정은지 패널이 학생과 같은 순간인지):
  - results/phase25eval/elbowtwistINVCHK260725align/zoom_left_knee.png
  - results/phase25eval/elbowtwistINVCHK260725align/zoom_adv_right_shoulder.png
  - results/phase25eval/elbowtwistINVCHK260725align/zoom_adv_right_hand.png
- 육안 확정 = PENDING (belle). 코드/프레임 정렬은 검증됐으나 "두 패널이 같은 동작 순간으로 보이는가"는 이미지 open 필요.

## belle 육안 결과 (2026-07-25, commit 149b770 크롭 3장 open)
- ✅ 마커 위치 = belle "아주 잘돼" (손 크롭: 머리카락에 가려진 손을 정확히 집음 — Claude 오독 정정). 마커 로직 무접촉.
- ✅ 프레임 뭉침(전부 140) 해소는 됨 (knee 140 / arms 148).
- ❌ **NEW 서브버그 (belle): 카드 안에서 학생 패널 ↔ 정은지 패널이 서로 다른 동작 순간.** 손 카드 user=148 / ref=166 인데 두 패널이 동작의 다른 지점 → "정은지 쪽은 아예 다른 장면" 이질감. 카드 내 student↔reference 는 같은 DTW 순간이어야 함.
- (부차) 카드 간 프레임 차이(140 vs 148 ≈0.9s)가 눈엔 같은 순간 — "카드마다 의미있게 다른 순간"은 설계질문 → 확대비교 트랙(33-10 목업). 이 debug 범위 아님.

## NEW 근본원인 (코드 확인, 149b770 fault_zoom.py)
- line 68-73: `sel_u = select_confident_frame(user_report, user_frame_candidates, unit.members)` = **학생 가시성**으로 프레임값 선택.
- line 79-91: `sel_r = select_confident_frame(ref_report, ref_frame_candidates, unit.members)` = **기준 가시성**으로 **독립** 선택.
- window(user/ref candidates)는 DTW-대응 index-정렬 리스트인데, sel_u/sel_r 을 각자 confidence로 고르면 index 가 달라져 → student↔reference DTW 짝 깨짐. (fix 전 단일프레임 경로도 동일 독립선택이었으나 1쌍이라 덜 드러남.)

## FIX 방향 (정렬)
- window **인덱스**를 학생 가시성으로 1개 선택(크롭 앵커=학생 결함) → 기준 프레임 = `ref_frame_candidates[그 index]` (DTW 짝) 사용. sel_r 독립선택 제거.
- select_confident_frame 이 값 반환이면 그 값의 user_frame_candidates 내 index 를 찾아 ref_frame_candidates[index] 로 매핑. 인덱스 어긋남 방지.
- confirmed + advisory 양쪽. marker/deficit 로직 무접촉. 채점 무접촉(D-20).
- 검증: 재렌더 → user/ref frame 이 같은 DTW 순간(카드 내 정렬) + belle 육안. (프레임선택 CPU/GPU 동일이라 정렬검증은 CPU 렌더로 충분 — GPU/cudnn9 복구는 flip용 별건.)

## belle 육안 #2 (2026-07-25, commit ea55069 — DTW-정렬 크롭) → NEW 요구 (1순위)
- ✅ 마커 위치 "정말 잘 해주고 있음" (belle 재확인).
- ❌ **still 미완 — 카드 내 두 패널이 "같은 포즈"가 아님.** 무릎 카드: 정은지는 앞을 보는데 학생은 뒤돌아본 순간 → "이게 무슨 비교지? 무릎을 뭘 어쨌다는 거지?" belle: "시작점·길이 다른 건 이해하나 **최대한 비슷한 포즈를 캡처해서 비교**해야지."
- **진단:** 오늘 한 DTW-인덱스 정렬은 **타이밍 대응**이지 **시각 포즈 대응**이 아님. DTW path 가 두 사람 역립 회전을 느슨히 맞춰 같은 window position 이어도 방향(앞/뒤)이 어긋남.
- **NEW FIX 방향 (내일 1순위, belle "이것부터 고쳐야 다음 개선 얹힘"):** 기준 패널 프레임을 **학생 프레임과 포즈 유사도 최대**인 것으로 선택 (같은 방향·국면). DTW 인덱스 단독 신뢰 대신 pose-distance(관절각/방향) 최소화. 기준 keypointReport 존재 → 계산 가능. window 확대 검토. confirmed+advisory 공통.
- **그 뒤 순위 (belle "이것 말고도 할말 많음"):** ① 크롭 표기 숫자 ≠ 채점 숫자 불일치(무릎 크롭20°/채점30°, 어깨66°/36°) ② advisory(참고) 크롭이 "감점 부위"로 오해됨(손 크롭=비채점) ③ 각도 숫자 사용자 노출 제거 ④ 비역립 동작(power-spin) 전수 검증 ⑤ 크롭+감점근거(정은지 이렇게/학생 이렇게) 세트 제시.
- status: 오늘 여기까지(belle 수면). 내일 이 debug continue — 같은-포즈 매칭부터.

## belle 요청 — 크롭↔감점 근거 동봉 (내부 검수용, 사용자 화면 아님)
- 크롭 보여줄 때 카드별 "정은지는 이렇게 바른데 학생은 이렇게 해서 감점 → 여기 표기" 를 같이. 확정/추정 태그. §6.5 "근거 동봉=내부 검수용".
- ⚠ 대조서 발견: 크롭 deficitDeg(vision window) ≠ deductionBreakdown measuredValue(채점). advisory 크롭(손)은 채점 record 자체 없음. 역립 fixture 라 채점이 8관절 전부 ~30° 균일(아티팩트=마커 발동 이유) → 이 케이스선 부위 귀속 원래 불신. **완벽 크롭 판단은 비역립(power-spin)으로.**

## Evidence — 같은-포즈 매칭 로컬 조사 (2026-07-26, commit ea55069 산출물 직접 open)
- **크롭 3장 직접 open 완료** (S3 elbowtwistINVCHK260725align). belle 지적 재현 확인:
  - zoom_left_knee: 학생=몸 말고 등 돌린 채 머리 아래로(웅크림) / 정은지=카메라 정면 응시 + 다리 옆으로 뻗음. 명백히 다른 국면.
  - zoom_adv_right_hand: 정은지 패널은 골반·발 위주라 학생 패널(머리·손)과 부위조차 안 맞음.
- **프레임 육안 대조 (9fps 그리드, ffmpeg 로컬 추출):** 학생 S70(무릎카드 프레임) vs 기준 R64~R90 전수 비교 →
  - 시각 최적 매칭 = **R68** (웅크린 역립 + 등 돌림 + 머리 아래, S70 과 같은 국면). R66/R79 도 근접.
  - 현재 DTW 짝 = **R73** (다리 옆으로 뻗고 정면 응시) = 다른 국면. belle 지적과 정확히 일치.
  - ★ **R68 은 anchor(R73) 에서 5프레임(9fps, ≈0.55s) 떨어짐 → 현행 후보 window(±2)를 완전히 벗어남.** 즉 window 내에서 아무리 잘 골라도 도달 불가 = **window 확대가 선택이 아니라 필수**.
- **제약 발견 — 역립 구간 keypoint 신뢰도 붕괴** (ref-elbow-twist-sister, phase4_v1 8관절 dump 실측):
  - 전체 329프레임 중 4관절 이상 conf≥0.5 = 137 (42%). 토르소 4관절 전부 conf≥0.5 = 92 (28%), 역립 구간 kp120~190 에선 20/70.
  - 9fps 61~85 관절 유효수: `65:4 66:5 67:2 68:3 69:3 70:1 71:0 72:4 73:3 74:4 75:3 76:0 77:3 78:0 79:0 80:7 81:7 82:8 83:8`
  - → 토르소 고정 기준 정규화는 불가. **공통-신뢰관절 Procrustes(이동+스케일 정규화)** 로 가야 함. 후보 scoreable 수: ±2 window=2/5, ±10=8/21, ±12=9/25 → **window 확대가 정규화 가능성도 같이 올림**.
  - ⚠ R68(시각 최적)은 유효관절 3개라 최소기준(4) 미달 가능 → 이 fixture 에선 R66/R79 급으로 수렴 예상. 완전 해결이 아니라 **개선**. keypoint 품질 한계는 별건(IN-01 attribution 계열).
- **환경 제약(조사 중 확인):** Firestore DNS 차단(sandbox 안팎 모두 `firestore.googleapis.com` lookup 실패) → 프로덕션 doc(학생 keypointReport) 로컬 확보 불가. 로컬에 pose estimator(torch/ultralytics/onnxruntime) 없음 → 학생 keypoint 로컬 산출 불가. 따라서 **학생↔기준 실측 검증은 Pod 재렌더 필수**.
- **Pod 상태:** 9w5es4y760il9w proxy `/health` = HTTP 404 (uvicorn 미기동), 직결 213.173.107.230:17519 = connection refused, runpodctl/API key 로컬 부재 → **재렌더 블로커**.

## Evidence — 지표 실물 검증 (2026-07-26, 실제 ref keypoint + 실제 프레임 이미지)
- 출하 함수 `fz.pose_distance` 를 ref-elbow-twist-sister 실 keypoint 에 직접 적용해 랭킹 산출 → **해당 프레임 이미지를 열어 육안 대조**.
- query R82(웅크린 역립, 머리 아래, 다리 하나 뻗음), 시간이웃(±8) 제외 59프레임 채점:
  - 최근접: R65(.24) R72(.26) R66(.34) R91(.36) → 전부 **웅크린 역립 + 머리 아래 + 머리카락 늘어짐** 계열. R91 은 다리 뻗은 각도까지 거의 동일.
  - 최원거리: R163(1.51) R112(1.60) = **쭉 편 역립**(다리 모아 수직), R31(1.57) = **선 자세**(비역립), R7(1.57) = 수평 벌림.
  - → 지표가 (a) 역립 여부 (b) 굽힘 vs 폄 (c) 팔다리 배치를 **실 footage 에서 판별**함을 실증. belle 케이스(학생=웅크림 vs 기준=폄+정면)가 정확히 이 축에서 갈린다.
- ⚠ 미검증(Pod 필요): 학생↔기준 **교차 인물** 실측. 로컬에 학생 keypoint 확보 경로 없음(Firestore DNS 차단 + pose estimator 부재).

## Evidence — 코드리뷰 BLOCKER 자체 재현 (2026-07-27, commit 191c296)

Pod 대기 중 191c296 에 대해 Python 코드리뷰 실행 → BLOCKER 1 / WARNING 1 / INFO 1.
**권위로 수용하지 않고 실제 출하 코드에 직접 재현**함. 3개 독립 probe 전부 재현됨.

- **BLOCKER 주장**: `pose_distance` 가 후보 프레임마다 `common = set(pose_a) & set(pose_b)` 를
  **따로** 계산 → 후보마다 **다른 관절 기저**로 정규화되어 "최소 거리 승자" 가 like-for-like
  비교가 아님. 관절 수가 적은 프레임일수록 이동+스케일 제거 후 남는 자유도가 작아 **구조적으로
  낮은 거리**를 받음.
- **probe A (리뷰어 재현 구성, 실 `fz.pose_distance`)**: user=6관절 / refA=6관절 거의 동일(노이즈
  0.004) / refB=토르소 4관절만 + 학생 4관절의 **정확한 닮음변환**(다리는 미상).
  - refA = **0.01546**, refB = **5.6e-16** → **알고리즘이 refB 를 선호 = 재현됨.**
  - 게다가 `tie = best*1.05` 가 ~0 으로 붕괴 → 동률 밴드가 anchor 와 refA 를 **배제** →
    "폴백=anchor 유지" 보증이 **성공 경로에서는 성립하지 않음** (리뷰어 지적 정확).
- **probe B (구조적 편향, 랜덤 포즈 4000회 × k=4..8)**: 평균은 평평(1.266~1.282)이라 "평균이
  낮다"는 틀림. 그러나 알고리즘이 실제로 쓰는 통계는 **최소값**이고 하위꼬리는 단조:
  `p05` 0.720(k=4) → 0.935(k=8), `min` 0.185(k=4) → 0.486(k=8).
  → 관절 적은 후보가 **우승할 확률**이 체계적으로 높다 = 편향 실재(리뷰어 표현이 정확).
- **probe C (실 fixture, ref-elbow-twist-sister 실 keypoint, ±1.2s window)**:
  - query kp=164(8관절), scorable 16 → **승자 = kp144, 거리 0.263, 공통관절 k=4** 로
    모든 k=8 후보(최선 0.356)를 이김. `corr(joint_count, distance) = -0.171`.
  - 다른 조합(q=192,a=202)에서도 OLD 승자 = 223 @ **0.049, k=4** (고정 기저에선 채점 자체
    불가) vs 일관 기저 정직한 승자 = 220 @ 0.701.
  - → **합성 케이스가 아니라 이 fixture 의 실제 탐색 window 안에서 발생**.
- **판정: BLOCKER 유효.** Pod 재렌더를 하기 전에 고치지 않으면 렌더 결과가 inconclusive
  (기준 프레임이 움직여도 그게 개선인지 저관절 허위승리인지 구분 불가).

### 수정안 실데이터 평가 (3안 비교, 실 keypoint 12개 탐색)
- `OLD`(후보마다 자기 교집합) — alive 12/12. **비교 불가(버그).**
- `NEW`(기저 = 학생 ∩ **anchor**) — 이론상 매력적(anchor 가 항상 채점 가능 → "anchor 보다
  나은가" 의미가 명확)이나 **alive 4/12**. anchor 프레임 자체가 역립 구간에서 자주 붕괴
  (기저 크기 0~3) → 기능이 정작 필요한 구간에서 죽음. **기각**.
- `STRICT`(기저 = **학생 프레임의 신뢰관절**, 후보는 그 전부를 신뢰관절로 가져야 채점) —
  **alive 12/12**, 후보수 3~18. 12건 중 2건에서 승자가 OLD 와 달라지고, 달라진 2건이 정확히
  저관절 허위승리 케이스. probe A 의 refB 는 **채점 불가(None)** → 추월 불가. **채택**.

## Evidence — 기저 고정 fix 구현 + 출하 함수 검증 (2026-07-27, commit 95ee80f)
- fix: `pose_distance(basis=)` + `select_pose_matched_ref_frame` 탐색 진입 시
  `basis = sorted(user_pose)` 1회 고정, 전 후보 강제. 신규 튜닝상수 0
  (`_POSE_MIN_COMMON_JOINTS` 기저 게이트 겸용). 기저 미커버 후보 = None(제외),
  후보 전멸 = None → anchor 유지(ea55069 폴백 불변).
- **출하 함수 실 keypoint 재검증** (재구현 아닌 실제 `fz.select_pose_matched_ref_frame`,
  ref-elbow-twist-sister 18fps, identity fps 매핑, scratchpad verify_shipped_basis.py):
  - 12개 (query,anchor) 탐색: 독립 STRICT 계산과 **12/12 일치**, 저관절 승자 **0**,
    alive **12/12**, 전 건 anchor 에서 이동(자기프레임 proxy 특성상 정당).
  - 종전 허위승자 kp144(q=164,a=170) / kp223(q=192,a=202): 고정 기저에서 **채점
    불가(None)** — 최소값 경쟁 진입 자체가 불가 = 구조적 배제 실증.
- 테스트: test_fault_zoom.py 52→55 PASS (신규 3 — probe A 부분후보 배제 / 기저가
  채점관절을 정확히 규정 / 저관절 닮음사본 select 우승 불가). 인접 11개 파일 375 PASS.
- 전체 스위트 A/B (fix ↔ HEAD revert): 61 fail/12 err **동일**, fix 측 +3 pass(신규
  테스트) — fix 유발 회귀 0. (07-26 기록 45 fail 에서 61 로 드리프트한 것은
  gemini 모델/설정 계열 pre-existing, fault_zoom 무관 — revert A/B 로 실증.)
- INFO fix 포함: 붕괴 폴백 테스트가 4관절 전좌표 붕괴로 실제 붕괴 분기를 태움.
- 미완(Pod): 교차 인물(학생↔기준) 실측 + belle 육안 — ref↔ref proxy 한계는 종전 기록대로.

## Evidence — 새 Pod 재렌더 + 무발동 실측 (2026-07-27, commit 6d4722e, Pod ovblalej2102sb)
- **새 Pod**: `ovblalej2102sb` (RTX 4090, EU). SSH `root@213.173.99.44 -p 32613`, proxy
  `https://ovblalej2102sb-8000.proxy.runpod.net`. 구 9w5es4y760il9w 대체(belle 신규 생성),
  Network Volume 생존. `bootstrap_full.sh` 재실행(새 컨테이너 pip 초기화), 서버 기동
  (health commitSha=6d4722e, CUDA EP 활성 probe 확인), **SSM `/sunity/motion/runpod-analyze-url`
  (v19) + Lambda `RUNPOD_ANALYZE_URL` 새 proxy 로 동기화 완료** — 앱/프로덕션 경로 이 Pod.
- **재렌더**: AID=`elbowtwistINVCHK260727pose`, shadow phase33-cm3-run1, PR_INVERSION_ENABLED=1,
  RTMW GPU. WALL 169.0s. STATUS=done **SCORE=60** (149b770/ea55069 와 동일 — 채점 무접촉 3연속 실증).
- **크롭 프레임 = ea55069 렌더와 완전 동일**: left_knee(confirmed) u_kp140/r_kp146,
  right_shoulder(advisory) u144/r150, right_hand(advisory) u148/r154. → **pose-match 전 카드 무발동.**
- ⚠ 로그 판별 함정: `_inv_check.py` 단독 실행은 logging 핸들러 미구성 → `fault_zoom_pose_match`
  INFO 가 lastResort(WARNING+)에 삼켜져 **로그 0줄 = 미실행 증거 아님**. 프로브로 대체 판별.
- **프로브 (`/workspace/_pose_probe.py`, 출하 `fz.select_pose_matched_ref_frame`/`pose_distance`
  직접 호출, 실 doc keypoint)**: 무발동의 원인 3카드 3갈래 —
  - left_knee: **학생** kp140 신뢰관절 2개(right_ankle,right_knee) < 4 → 탐색 스킵(user-side 게이트).
  - right_hand: 학생 kp148 신뢰관절 3개 < 4 → 탐색 스킵(user-side 게이트).
  - right_shoulder: 기저 6관절 성립, window 23후보(r=64..86) 중 **기저 커버 0개** → 전멸 → None.
    ref 신뢰관절수 0~8 요동(역립 keypoint 붕괴); 8관절 후보(r=82,83,85)도 기저 미커버.
  - `select_pose_matched_ref_frame` 반환 = None (3카드 전부) — reasoning_checkpoint
    falsification_test **(b) 현실화** + user-side 게이트 병행 원인(예견 밖 신규 사실).
- 판정: 무발동 폴백은 안전(악화 0)하나 **belle 1순위(무릎 카드 같은-포즈)는 미해결** — 무릎
  카드가 ea55069 와 같은 프레임이므로 belle 육안 재요청 무의미. 게이트/기저 재설계 필요.

## Evidence — 게이트/기저 A/B + **NEW 근본원인: ref 타임베이스 4/3 불일치** (2026-07-27, Pod ovblalej2102sb)
- **A/B 1차 (게이트 재설계, /workspace/_gate_ab_probe.py):**
  - 신규 사실 #1 — **관절 이름공간 불일치**: user keypointReport = 12관절(ankle/elbow 포함),
    ref referenceKeypointReport = **8관절**(ankle/elbow 아예 없음). 95ee80f 무발동의
    right_shoulder 갈래(기저6 커버0)의 실체 = 기저 6관절 중 4개(ankles/elbows)가 ref
    이름공간에 **존재 자체를 안 함** → 커버 0 구조 확정. confidence 붕괴 아님.
  - 이름공간 교집합(8관절)으로 기저 제한 + conf 게이트 제거(A_free)/학생 conf 가중(D_wgt)
    /temporal ±1(C_tmp) 전부 **alive 23/23, 3카드 전부 발동**. knee 카드 승자 R67
    (0.442, 2위 0.742 — 압도적 마진), 오답 anchor R73=1.266 최하위권 ✓ 판별력 실증.
- **신규 사실 #2 (더 큰 근본원인) — ref 크롭 표시가 처음부터 시간 왜곡:**
  - ref videoS3Key 영상: raw 655프레임/PTS 24.4s → frame_extractor(렌더러가 크롭에 쓰는
    배열) = **220프레임**. referenceKeypointReport = 329@18fps = **9fps 환산 164.5**.
  - Pod 에서 출하 RTMW 를 ref 영상 220프레임에 실행 → video-space report 생성 →
    doc-report 각 프레임을 pose_distance 최소로 video 프레임에 대응(/workspace/_timebase_map.py):
    단조 사슬 = **t_vid = (4/3)·t_rep, 오프셋 0** (양 끝점 정확: rep0→vid0, rep18.0s→vid24.0s;
    rk216→vj144 = 정확히 4/3, d=0.013). 해석: report 는 raw **매 2프레임** 샘플(655/2≈329,
    18fps 로 라벨), extractor 는 PTS 9fps(매 ~3프레임) — **rep 인덱스 ↔ video 인덱스가
    4/3 배율로 어긋남**. 학생측은 report 가 같은 extractor 프레임에서 in-run 생성이라
    배율 1.0(무왜곡) — 학생 패널이 늘 맞았던 이유.
  - **함의**: 렌더러는 ref_frames[rep인덱스] 로 크롭 → 모든 ref 패널이 자기 타임스탬프의
    3/4 지점(결함 창 기준 ≈2.7s 이른 순간)을 보여줘 왔음. belle "정은지 쪽은 아예 다른
    장면" + "부위조차 안 맞음"(크롭 박스 좌표는 진짜 순간의 관절좌표인데 이미지는 다른
    순간) 정량 설명. 07-26 "GT: video R68" 은 video-space 관찰 — 잘못된 창(왜곡 인덱스
    주변)에서의 시각 최적이었고, rep-space 탐색과 창 자체가 달랐음.
- 판정: fix 는 2단 — (1) **ref 표시 인덱스 타임베이스 매핑** `v_idx = round(r9 · N_video/N_rep9)`
  (양쪽 report/영상 길이에서 유도 — 상수 0, 정합 ref 는 배율 1.0 자동 no-op, 표시 전용),
  (2) 게이트/기저 재설계(이름공간 교집합 + 매칭 전용 conf 완화) 로 pose-match 발동.

## belle 육안 #3 (2026-07-28, commit 4cb272a — drivetb260727 크롭 3장) → **NOT FIXED**
- belle verbatim (요지): "이렇게 잡는건 이전이랑 변하는게 없는데... 큰일이네 계획부터 다시 짜야하나 기술적 문제인건가"
  1. **무릎 카드 (1순위)**: 학생 무릎을 집는 건 좋음(마커 OK). 그러나 **정은지 패널이 같은 자세에서 무릎을 잡은 화면이 아님 — "엉뚱한 사진"**. 비교가 성립 안 함.
  2. **어깨 카드**: (i) **REGRESSION — 어제(ea55069 렌더)는 어깨를 잘 집었는데 오늘은 목을 집음.** (ii) facing 불일치 지속(정은지=정면 / 학생=측면) → 비교 사진 아님.
  3. **손 카드**: 두 패널 자세 다름 + "손 모양을 뭐 어떻게 하라는지 모르겠음" → advisory 실행가능성 설계 이슈(기존 큐 "advisory 오해" 항목) — belle 없이 구현 금지, 기록만.
  4. **세 카드가 크게 다른 장면으로 안 느껴짐** (회전 동작 특성 감안) → belle 승인 추가: **크롭 아래/위에 영상 몇 초인지 타임스탬프 기입** (display-only). 각도 배지↔타임스탬프 교체 여부는 belle 질문으로 기록(무단 제거 금지).
- ⚠ 자체판정(scratchpad/tbfix open — "같은 국면·facing·부위")과 belle 판정 충돌 → 자체판정 근거 재검증 필요. 내가 연 이미지와 belle이 본 S3 이미지가 같은 것인지 + "국면 일치"와 "무릎이 비교 가능하게 프레이밍됨"은 다른 기준임을 유의.

## Evidence — belle #3 반려 원인 실측 (2026-07-28, drivetb260727 크롭 + Pod keypoint dump)
- **S3↔로컬 md5 동일** — belle 과 같은 이미지를 봤음. 이전 자체판정("같은 부위")이 무릎 카드에서 오판이었음 (국면 일치 ≠ 부위 프레이밍).
- **[H1 확정 — 무릎 카드 ref 패널]** Pod dump: ref rep kp134 에서 left_knee=(0.446,0.546) conf **0.70** / right_knee=(0.507,0.551) conf **0.68** — 그러나 RV090 실물에서 그 좌표는 **정은지 얼굴/턱** 위치. 실제 무릎은 y≈0.36~0.42 (엉덩이 위). 오버레이(overlay_kp134_on_RV090.png)로 실증: hips(conf 0.44~0.48)는 대략 맞고, "knees"는 머리에 환각 — **역립 keypoint 환각이 conf 0.5 게이트를 통과**. 크롭박스 valid=[가짜 무릎 2점] → 머리/가슴 중심 크롭 → 진짜 무릎 프레임 밖. **순간(rep67↔video90 매핑)은 맞고, 프레이밍이 가짜 좌표를 따라감.**
- **[H3 기각 — 어깨 카드 "목" 회귀]** 어제(ea55069 렌더) ↔ 오늘(drivetb) 학생 패널 **픽셀 동일**(meanabs diff 0.00~0.01) — 코드/데이터 회귀 없음. 마커 링은 항상 크롭 중심(180,180) r=57 (크롭박스가 앵커 중심이므로). belle 의 "어제는 어깨 잘 잡았다" = **149b770 크롭(u_kp148)** 기억 — kp148 에선 어깨가 시각적으로 분리돼 보임(pjfix_shoulder.png 확인). ea55069 의 DTW-정렬 fix 가 어깨 카드 학생 프레임을 kp148→kp144 로 옮겼고(conf 0.57 vs 0.56 — 사실상 동률), kp144 에선 어깨 keypoint(0.507,0.540)가 얼굴 옆이라 링이 "목"으로 읽힘.
- **[H4 기각]** driven build 는 출하 build 함수 + 실 doc/report/프레임 사용 — 자연 렌더와 같은 경로.
- 어깨 카드 facing 불일치(ref 정면/학생 측면)는 지속 — pose-match 가중거리에서 환각 ref 좌표가 판별을 흐리는 keypoint 품질 한계(IN-01 계열)와 얽힘.

## Evidence — 심화 실측: 전이 프레이밍 기각 + 진짜 구조 (2026-07-28)
- **전이(transfer) 프레이밍 검증 → 이 카드에선 무효**: 학생 kp140 가중 Procrustes 로 학생 legs 좌표를 ref 프레임에 사상 → 전이 박스(left89,top249,side151) ≈ 출하 박스(96,276,151). 이유 = **학생의 무릎(턱 포즈라 진짜로 머리 옆) ↔ ref 의 환각 무릎(머리에 가짜)이 같은 위치로 수렴**. 프레이밍 기법 문제가 아니라 **선택된 ref 프레임 자체가 다른 포즈**.
- **ref 프레임 선택의 구조적 한계 실측 (콘택트시트 sheet_win_62_112 / sheet_zoom_cands)**:
  - 학생 S70 = 몸 웅크린(tuck) 역립. 진짜 시각 매칭 = **RV068 / RV082** (tuck+등돌림, 07-26 GT 정합).
  - 현 탐색창 = DTW anchor rep73 ±1.2s = **video ≈83..112** → RV068(밖), RV082(경계 밖 1프레임). 도달 불가.
  - 승자 RV090(rep67) = 다리 편 아치 자세(≠tuck). 그런데 keypoint 공간에선 tuck 처럼 보임 — **환각 무릎(머리 위치, conf 0.68~0.70)이 학생의 진짜 tuck 무릎(머리 옆)과 우연히 겹침** → 지표가 "실제 tuck"과 "환각상 tuck"을 구분 불가. 07-27 A/B 의 "RV090 ✓ 육안"은 오판(대충 역립+머리아래만 보고 국면 일치로 침).
  - DTW anchor 자체가 이 구간에서 video 기준 ≈2.5~3s 어긋나 있음(역립 구간 ref 각도 품질 저하 → DTW path drift 추정).
- **어깨 카드 학생 마커 "목" 실측 (sheet_shoulder_kps)**: 학생 right_shoulder keypoint 가 kp144 에서 **얼굴에 환각**(conf 0.57), kp148 에선 진짜 어깨(conf 0.56). 프레임 선택(멤버 평균 conf argmax)이 0.01 노이즈 차로 환각 프레임을 선택. 149b770 의 "어깨 잘 잡힌" 크롭은 **다른 doc(CPU RTMW 런)** 이라 노이즈가 반대로 떨어져 kp148 이 이긴 것 — 선택 규칙 회귀 아님, argmax 가 노이즈 위에서 구르는 구조.
  - window 내 right_shoulder 궤적: y=0.460/0.515/**0.540(환각,144)**/0.520/0.521(148) — **window 중앙값(≈0.520) 대비 kp144 가 최대 이탈** = 동률(conf 5% 밴드)시 "window 중앙값 좌표에 가장 가까운 프레임" tie-break 가 kp148 을 선택함(중앙값 = 환각-강건 합의 신호, fixture-무관 원리).

## Current Focus (ACTIVE — belle #3 반려 fix 설계, 2026-07-28)
- status: 원인 3겹 확정. fix 후보 설계/검증 국면.
- root_cause(#3, 3갈래):
  1. **탐색창이 진짜 매칭을 구조적으로 배제** — DTW anchor 가 역립 구간에서 ≈3s drift, ±1.2s 창 안에 tuck 프레임 없음 (GT RV068/082 도달 불가).
  2. **환각 keypoint 가 지표를 기만** — ref 무릎 환각이 학생 tuck 과 겹쳐 잘못된 프레임이 압도적 1위(0.442 vs 0.742).
  3. **학생측 프레임 선택도 환각 취약** — conf argmax 0.01 차가 환각 프레임(kp144, 어깨=얼굴)을 선택.
- fix 후보 검증 결과 (Pod 프로브 3종 — widen/traj/pair, 2026-07-28):
  - widen 단독(±4s): v80(진짜 tuck) 0.46 vs v90(환각) 0.45 = 동률 밴드 → anchor-근접 tie-break 가 **v90 유지 (실패)**. 중앙값-좌표 tie-break 도 이동 관절에서 실패(어깨 x 단조 이동 → 중앙값=환각 프레임 x 와 우연 일치, 로컬 계산으로 기각).
  - **trajectory-mean(±2k, per-k 고정 기저)**: v90 = 고립 최소점(이웃 0.84+, 환각 flicker 시그니처) → 궤적 평균에서 강등. knee 승자 v70(GT R68 인접, tuck family ✓ 육안), @148 승자 v132(팔 뻗은 아치 = S74 구조 일치 ✓ 육안).
  - **pair-opt (학생 후보 × 궤적 매칭, 학생 후보 = valid(conf≥0.5) 멤버 보유 프레임만)**:
    - legs: 유일 valid-anchor 후보 = u70 (belle 승인 프레임 자동 보존) → ref v70 (0.692, v90 0.706 강등)
    - right_shoulder: 후보 {72,73,74} → **u74(kp148, 마커=진짜 어깨) ↔ v132 (0.618)** 최적 — 환각 프레임(kp144)은 휴리스틱 없이 자연 강등(환각 포즈는 어떤 ref 와도 궤적 일치가 나쁨)
    - right_hand: 유일 후보 u74 → v132 (v115 보다 육안 근접)
  - 3카드 전부 육안 정합 + belle 승인 프레임/마커 보존 → **pair-opt + trajectory 채택**.
- **구현/검증 완료 (commit e8613e8)** — 위 "pair-opt 궤적 매칭 구현 + 검증" Evidence 절.
- next_action: **belle 육안 체크포인트** — S3 drivepair260728 크롭 3장. belle 에게 물을 것:
  ① 각도 배지(20°/36°/30°)를 타임스탬프로 **대체**할지, 병기 유지할지 (무단 제거 금지 원칙)
  ② 손(advisory) 카드 실행가능성("뭘 어떻게 하라는지") — 설계 항목, belle 지휘 필요
  ③ 어깨 카드 facing 잔차(정은지 약간 정면) — keypoint 품질 한계(IN-01 계열) 수용 여부
- 별도 보고(범위 밖): Gemini moment extractor 침묵 24h+ 지속 → 자연 렌더 카드 0장 (파이프라인 자체는 SCORE 60 정상). 회복 안 되면 별건 조사 필요.

## reasoning_checkpoint (belle #3 — pair-opt 궤적 매칭 + 타임스탬프, 2026-07-28)
- hypothesis: "belle #3 의 3가지 시각 결함은 공통 뿌리 = **역립 구간 keypoint 환각이 conf 게이트를 통과**하고, 단일프레임 신호(관절 conf argmax / 단일프레임 pose 거리)가 그 환각에 올라탐. 환각은 프레임 간 flicker 하므로 (a) ref 선택을 ±2 궤적 평균으로, (b) 학생 프레임 선택을 '최적 궤적 짝을 이루는 valid-마커 프레임'으로 바꾸면 환각 프레임이 자연 강등된다. 또 DTW anchor 가 이 구간에서 ≈2.4s drift(실측) → 탐색창 ±1.2s 로는 GT 도달 불가 → ±4.0s 로 확대."
- confirming_evidence:
  - "ref rep kp134 '무릎' = 정은지 얼굴 위치 (conf 0.68~0.70, 오버레이 실증) — 단일프레임 승자 v90 의 실체"
  - "v90 = 고립 최소(0.45, 이웃 0.84+) / 궤적 평균에선 v70(GT 인접) 이 승자 — flicker 시그니처 실측"
  - "학생 right_shoulder kp144 = 얼굴 환각(conf 0.57) vs kp148 = 진짜 어깨(0.56) — 0.01 노이즈 argmax 실증. pair-opt 는 kp148 을 자연 선택(0.618 vs 0.690)"
  - "GT rep51 vs DTW anchor rep73 = 2.4s drift 실측 → ±4s 필요"
  - "pair-opt 3카드: legs u70(승인 프레임 보존)+v70 / shoulder u74+v132 / hand u74+v132 — 전부 콘택트시트 육안 정합"
- falsification_test: "driven 재렌더에서 (a) knee 카드 ref 패널이 tuck 포즈+무릎 포함 크롭이 아니면 → rep kp104(v70) 좌표도 환각 = keypoint 신호 한계, 비-keypoint 국면 전환. (b) 어깨 카드 학생 마커가 어깨를 안 집으면 → kp148 재검. (c) SCORE 60 이탈 → D-20 위반 즉시 revert. (d) 기존 유닛테스트 의도 위반(폴백 경로 변화) → 재설계."
- fix_rationale: "환각을 감지하는 별도 휴리스틱(임계/λ)을 만들지 않고, **비교의 시간 폭을 늘려**(궤적) 환각의 시간 불안정성이 스스로 벌점이 되게 한다. 학생 프레임도 '마커 가능(valid) 후보 중 최적 짝'으로 골라 [마커 정확성]과 [포즈 대응]을 한 원리로 통일. 신규 상수 = _POSE_TRAJ_RADIUS(2, features window=2 관행 정합) 1개 + 기존 _POSE_SEARCH_SECONDS 값 변경(1.2→4.0, drift 실측 근거). anchor-근접 tie-break 는 pair 경로에서 제거 — 실측에서 환각 유지 장치로 작동(v90). 폴백 사슬 보존: pair-opt None → 기존 confident-index+단일프레임 매칭(ea55069+95ee80f) 그대로. 전부 표시 전용, 채점 무접촉."
- blind_spots:
  - "학생 후보 간 기저가 다를 수 있어 pair 점수가 엄밀 like-for-like 는 아님(기저 작은 후보의 구조적 저거리 편향 잔존 가능) — valid-멤버 게이트가 후보를 1~3개로 제한해 실효 위험 낮다고 판단, 문서화"
  - "±4s 확대가 비역립 동작(power-spin)에서 다른 국면 포착 위험 — 궤적 평균이 방어하나 미실측 (belle 우선순위 ④ 전수 검증에서 관측)"
  - "n=1 fixture 검증 — 마진 얇음(0.692 vs 0.706 = 2%). 원리(궤적=환각 강건)는 fixture-무관이나 수치 우위는 재현 미보장"
  - "v70 의 ref 크롭박스가 무릎을 담는지는 rep kp104 좌표 품질에 의존 — driven 렌더로 확인 예정"

## Current Focus (구 — 게이트/기저 재설계 A/B, 2026-07-27)
- status: **재설계 후보 실 keypoint A/B 평가 국면.** 95ee80f 재렌더에서 pose-match 전 카드
  무발동 실측(학생측 <4 게이트 2건 / ref 기저 커버 0 1건). 수용 기준(belle): 무릎 카드가
  학생 패널과 **같은 포즈/facing** 의 기준을 보여야 함 — 무릎 카드 학생 프레임의 신뢰관절이
  2개뿐이므로 **strict 신뢰관절 집합만으로는 어떤 재설계도 수용 기준 미달**(구조적).
  → 매칭 신호를 신뢰관절 집합과 분리하는 설계 필요(저신뢰 keypoint 매칭 전용 사용 등).
- hypothesis: "RTMW 는 저신뢰 구간에도 전 관절 좌표를 출력한다. 매칭(표시 전용)에 한해
  confidence 게이트를 완화/가중치화하면, 기저를 학생 프레임으로 고정하는 한 비교공정성
  (95ee80f)은 유지되면서 무발동 3갈래가 모두 열린다. 저신뢰 좌표가 국면(웅크림/facing)을
  판별하는지는 실측으로만 판정 가능."
- test: Pod 프로브(_pose_probe.py 패턴 확장)로 후보 설계 A/B — 실 doc 학생 keypoint
  (elbowtwistINVCHK260727pose) × 실 ref keypoint. **ground truth = 2026-07-26 육안 그리드**
  (학생 S70=kp140 의 시각 최적 ref = R68, 근접 R66/R79; DTW 짝 R73 은 오답).
  후보: (A) 매칭 전용 conf 게이트 제거/완화 — 기저 = 학생 프레임 finite 좌표 전체(고정),
  (D) 기저 = finite 전체 + **학생 confidence 를 관절 가중치로 고정**(후보 간 동일 가중 공간
  = like-for-like 유지, per-candidate 가중은 비교불가 재도입이라 금지),
  (B) 기저 = 학생 신뢰관절 ∩ window 가용성(참고용 — 무릎 카드 못 여는 것 확인용 대조군),
  (C) temporal window 다중프레임 — A/D 승자 위에 얹어 개선 여부만 확인.
- expecting: 무릎 카드에서 후보가 R66~R68/R79 계열(웅크림+등돌림)을 고르면 = 저신뢰 좌표도
  국면 판별 가능 → 채택. R73 근처/무작위면 = 좌표 자체가 붕괴 → keypoint 신호로는 불가,
  비-keypoint 신호(프레임 화소 등) 국면으로 전환.
- **A/B 결과 (실행 완료, 위 Evidence 절)**: 이름공간 교집합 필수 발견 + 타임베이스 4/3
  왜곡 발견. D_wgt(학생 conf 가중) 채택 — 3카드 발동, 정확 매핑 하에 육안 대조:
  knee S070↔RV090 같은 웅크린 역립 국면 ✓, shoulder S072↔RV102 ✓, hand S074↔RV115
  (아치+대각 다리) ✓ D_wgt 가 A_free 보다 근접.
- **구현 완료 (fault_zoom.py + test_fault_zoom.py, 커밋 전 검증 완료):**
  - `pose_distance(weights=)` — 가중 centroid/RMS/평균. 비가중 경로 byte-보존.
  - `select_pose_matched_ref_frame` — 기저 = finite ∩ ref 이름공간 ∩ conf>0,
    가중 = 학생 confidence(탐색 내 고정). legacy(conf 배열 부재) → None 보수성 유지.
    탐색 상한 = min(video, rep9 공간) — rep 밖 clamp 중복채점 차단.
  - `ref_display_frame_index` — rep 공간 → 비디오 배열 선형 매핑(길이비, 상수 0,
    정합 ref 는 identity). 크롭 지점에서만 적용, refFrameIdx 방출(kp 공간) 불변.
  - fault_zoom_crop 로그에 ref_rep_idx/ref_video_idx 추가 (Pod 관측용).
  - 테스트 55→60: 저신뢰 발동(수용 기준) / legacy None 분리 / 이름공간 교집합 /
    가중 할인+무효가중 None / 타임베이스 매핑 단위 / e2e 매핑된 비디오 프레임 크롭.
    닮음사본 회귀 게이트는 NaN 좌표 기반으로 재정의(ref conf 미사용 명문화).
  - 전체 스위트: 61 fail/12 err = 문서화된 pre-existing 과 동일, 3443 passed. 회귀 0.
- **검증 실행 결과 (2026-07-27 저녁, commit 4cb272a Pod 배포 후):**
  - 재렌더 tb/tb2/tb3/tb4: STATUS done SCORE **60 불변** (D-20 4연속) — 단
    **faultZoomComparisons 0장**. 원인 추적 완료 = **내 코드 아님**:
    visionVeto.status=applied + faultJoints 아침과 동일한데 **worst-moment 가 0 으로
    붕괴** (window [0,1,2] vs 아침 [70..74]). app.py:2018 `at=worst_pose_timestamp
    (profile)` 가 None → `(at or 0.0)*9` → frame 0. profile.key_moments = Gemini
    moment extractor 산출 — generateContent/File API 직접 curl 은 둘 다 HTTP 200
    (키 유효·쿼터 정상)이라 **일시적 Gemini 영상처리 지연/무응답**으로 판정
    (attributionReliability.geminiSilent=true 정합). window [0,1,2]에선 legs 관절
    양측 전부 conf 0.2~0.3 < 0.5 → 기존 "양측 valid 0 → 카드 skip" 규칙(구코드도
    동일)으로 0장 — pre-existing 경로.
  - ⚠ 부수 발견(별건, 채점인접이라 미수정): `(at or 0.0)` 이 None 을 frame 0 으로
    붕괴 — vision_veto.py:1043 이 경고한 바로 그 falsy-collapse 패턴이 호출측에 있음.
  - **결정적 검증(Gemini 우회, 출하 build 직접 구동)**: 아침 window [70..74]/[73..77]
    + 실 user keypointReport(260727pose doc) + 실 ref report + 실 extractor 프레임으로
    `build_fault_zoom_comparisons` 실행 → **3카드 전부 생성 + 예측값 전부 일치**:
    - left_knee: pose_match 73→67, refFrameIdx=134(kp), **ref_video_idx=90** ✓
    - right_shoulder: 75→76, refFrameIdx=152, **ref_video_idx=102** ✓
    - right_hand: 77→86, refFrameIdx=172, **ref_video_idx=115** ✓
    - userFrameIdx 140/144/148 불변(학생측 무접촉) ✓
  - **크롭 PNG 3장 직접 open (scratchpad/tbfix/)**: 세 카드 모두 학생↔정은지 패널이
    **같은 국면·같은 facing·같은 부위** — knee 카드(2회 반려된 그 카드) 양 패널 모두
    웅크린 역립+머리 아래, hand 카드 정은지 패널이 종전 "골반·발"이 아니라 학생과
    같은 머리/손 부위. 수용 기준 자체 판정 통과 — belle 육안 대기.
- next_action: belle 육안 체크포인트 (tb5 자연 렌더 재시도 병행 — Gemini moment 회복
  시 S3 실렌더 크롭으로, 아니면 driven 크롭 S3 업로드로 제시).
- **구현 (commit 95ee80f, fault_zoom.py + test_fault_zoom.py):**
  - `pose_distance(..., basis=)` — 기저 관절을 못 덮는 후보는 None(채점 불가). 자동
    공통관절 모드는 단일 쌍 비교 전용으로 격하 + docstring 에 비교불가 함정 실측 기록.
  - `select_pose_matched_ref_frame` — 탐색 진입 시 `basis = sorted(user_pose)` 1회 고정,
    전 후보에 `basis=` 강제. 모든 후보가 동일 관절 공간의 값으로 경쟁.
  - 신규 튜닝상수 **0** — `_POSE_MIN_COMMON_JOINTS`(4) 가 기저 크기 게이트 겸용(주석 명시).
  - 폴백 불변: 기저를 덮는 후보 0 → None → anchor 유지 = ea55069 동작.
- **검증 (커밋 전 완료):**
  - 유닛테스트 52→**55 PASS** (신규 3: 부분후보 배제(probe A 재현) / 기저가 채점관절을
    정확히 규정 / 저관절 닮음사본 우승 불가(end-to-end select)).
  - fault_zoom 인접 11개 테스트 파일 **375 PASS**.
  - 전체 스위트 A/B: HEAD 기준 61 fail/12 err ↔ fix 적용 61 fail/12 err (+3 pass = 신규
    테스트). **fix 유발 회귀 0** (61건은 gemini/body-profile 계열 pre-existing — 07-26
    기록 45건에서 드리프트했으나 fix 와 무관, revert A/B 로 실증).
  - **출하 함수 실 keypoint 검증**: `select_pose_matched_ref_frame` 를 ref-elbow-twist-sister
    실 keypoint(18fps identity 매핑)로 12개 (query,anchor) 탐색 → 독립 STRICT 계산과
    **12/12 일치, 저관절 승자 0, alive 12/12**. 종전 허위승자 kp144(q=164)/kp223(q=192)
    는 채점 불가(None)로 **구조적으로 추월 불가** 확인.
  - INFO fix: `test_build_keeps_dtw_ref_when_pose_match_impossible` 4관절 전좌표 붕괴로
    변경 — 실제 붕괴 분기(스케일 0 → None)를 태움. docstring 정합.
- **WARNING 판정 (mode3 / top-2 폴백 / override 경로 미진입)**: 아래 "판정 기록" 절 참조.
  결론 = **사실 인정 + 지금은 확대 안 함(의도적 유보, 근거 기록)**.
- next_action: belle Pod 기동 → `_inv_check.py` fresh AID 재렌더(shadow phase33-cm3-run1,
  PR_INVERSION_ENABLED=1) → `fault_zoom_pose_match` 로그(발동/폴백) + faultZoomComparisons
  refFrameIdx 확인 → 크롭 S3 다운로드 → 이미지 직접 open → belle 육안.

## Evidence — pair-opt 궤적 매칭 구현 + 검증 (2026-07-28, commit e8613e8)
- **구현 (fault_zoom.py + test_fault_zoom.py):**
  - `select_pose_matched_pair` — (학생 window position, 기준 9fps 프레임) 동시 최적화.
    학생 후보 = valid(conf≥0.5) 멤버 보유 프레임만(마커 보존 게이트). 채점 = ±2
    궤적 평균(per-k 기저·가중 고정 = 95ee80f 비교공정성 유지). anchor-근접
    tie-break 없음(완전 동률만 |r−anchor| 결정론). None → 종전 사슬
    (confident-index + 단일프레임 매칭) 폴백.
  - `_POSE_SEARCH_SECONDS` 1.2→4.0 (drift 실측 2.4s + 마진). `_POSE_TRAJ_RADIUS=2` 신설.
  - `_stamp_time` — 양 패널 좌하단 비디오 초 배지(fill 40,40,40 — 감점 시각언어와
    분리). refMatch='failed' 전신 폴백 패널은 미표기(대응 오독 방지). 각도 배지 유지.
- **유닛 검증**: test_fault_zoom 69 PASS (신규 9 — pair 환각 강등/마커 게이트/전멸
  None/legacy None/window 밖 도달, 타임스탬프 포맷/no-op/양패널 e2e/전신폴백 미표기).
  기존 2건 의도 보존 수정(단일 스파이크→plateau 픽스처 = 궤적 의미론 반영, 샘플
  픽셀 이동 = 새 배지 회피 — 각 docstring 에 사유 명시). 인접 11파일 320 PASS.
  전체 스위트 61 fail/12 err = pre-existing 동일, 3452 passed(+9=신규). 회귀 0.
- **Pod driven 렌더 (출하 build, 실 doc/report/프레임)**: 프로브 예측과 3카드 완전 일치 —
  - legs: u9=70(kp140 보존, belle 승인 마커) / ref rep9=52 → kp104, **video 70(RV070)**
  - right_shoulder: u9=74(**kp148 — 마커가 진짜 어깨**, 149b770 에서 belle 승인한 그 프레임) / ref video 132
  - right_hand: u9=74(kp148, 승인 마커) / ref video 132
- **크롭 3장 직접 open (scratchpad/pairfix)**:
  - knee 카드: 양 패널 모두 **웅크린(tuck) 역립, 같은 facing(등/측면), 엉덩이~머리 같은 부위** — ref kp104 무릎 keypoint(conf 0.50/0.61)가 tuck 포즈에선 실제 무릎 위치와 근사(RV070 오버레이+크롭박스 실측: 박스가 hips+무릎+토르소 전부 포함).
  - shoulder 카드: 학생 = kp148(어깨/겨드랑이 마커 — 반려된 kp144 "목" 아님), ref = 팔 위로 뻗은 아치(구조 일치). facing 잔차(정은지 약간 정면) 있음.
  - hand 카드: 양 패널 머리+머리카락+손 부위, 같은 국면.
  - 타임스탬프: 학생 7.8s/8.2s, 기준 7.8s/14.7s — 카드가 서로 다른 순간임이 표기됨.
- **자연 렌더 (AID elbowtwistINVCHK260728pair2)**: STATUS done **SCORE 60** (D-20 5연속
  불변 ✓). 단 faultZoomComparisons **0장** — **Gemini moment extractor 침묵 지속**
  (geminiSilent=true, 어젯밤과 동일, 24h+ 경과 — "일시적" 가정 흔들림. worst_pose_timestamp
  None → 카드 생성 자체 스킵, sourceFrameIndices 미방출). pre-existing(내 코드 아님,
  app.py:2018 falsy-collapse 별건 기록 유지). **belle 육안은 driven 크롭으로 진행**
  (전 사이클과 동일 방식 — driven=출하 build 함수 그대로라 대표성 있음).
- S3 (belle 육안): results/phase25eval/drivepair260728/drive_zoom_{left_knee,adv_right_shoulder,adv_right_hand}.png

## reasoning_checkpoint (게이트 재설계 + 타임베이스 매핑, 2026-07-27)
- hypothesis: "무발동의 3갈래는 (a) conf>=0.5 강성 게이트가 역립 학생 프레임(신뢰 2~3관절)을
  차단, (b) user 12관절 vs ref 8관절 이름공간 불일치로 기저 커버가 구조적으로 0. 그리고
  belle 의 '아예 다른 장면'의 더 깊은 원인은 (c) ref report 타임라인(매 2 raw 프레임,
  콘텐츠 18.3s)과 렌더러 비디오 배열(PTS 9fps, 24.4s)이 4/3 배율로 어긋나는데 렌더러가
  identity 로 인덱싱해 모든 ref 크롭이 이른 순간을 보여준 것."
- confirming_evidence:
  - "Pod 프로브: conf 게이트 제거+이름공간 교집합만으로 3카드 alive 23/23 (A/B 1차)"
  - "출하 RTMW 를 ref 비디오에 실행 → rep↔video 대응 실측: t_vid=(4/3)·t_rep, 오프셋 0,
    양 끝점 정확 (rk216→vj144 d=0.013)"
  - "정확 매핑 하 육안: knee 승자 rep R67 → 비디오 RV090 이 학생 S070 과 같은 웅크린
    역립+등돌림 국면 (3카드 전부 대조 완료, D_wgt 채택)"
  - "학생측은 report 가 in-run 생성이라 배율 1.0 — 학생 패널이 늘 맞았던 것과 정합"
- falsification_test: "재렌더에서 (a) fault_zoom_crop 로그 ref_video_idx 가 rep_idx 와 같으면
  (=배율 1.0 으로 계산됨) 매핑 미발동 → 메타 전달 경로 재조사. (b) 크롭 이미지의 정은지
  패널이 여전히 다른 국면이면 → 선형 매핑 가정(콘텐츠 등간 커버) 오류 → 비선형 대응 필요.
  (c) SCORE 가 60 에서 움직이면 D-20 위반 → 즉시 revert."
- fix_rationale: "타임베이스는 데이터(양쪽 길이)에서 유도되는 선형 매핑이라 상수 0, 정합
  ref 는 identity 로 자기보정. 매칭은 신호(finite 좌표)와 신뢰(가중)를 분리 — 게이트를
  낮추는 대신 기여를 conf 로 할인해 저신뢰 좌표의 발언권을 정보량만큼만 준다. 기저·가중
  고정으로 95ee80f 비교공정성 불변. 두 fix 모두 표시 전용 — 채점 경로 무접촉."
- blind_spots:
  - "선형 매핑은 '두 시퀀스가 같은 콘텐츠를 등간 커버' 가정 — 이 ref 에선 실측 성립,
    다른 ref(11개 라이브러리)는 미실측. 단 정합 ref 는 identity 라 악화 불가."
  - "가중 매칭의 저신뢰 좌표 사용이 다른 fixture(비역립 power-spin 등)에서 오히려
    소음일 가능성 — belle 우선순위 ④ 전수 검증에서 관측."
  - "veto still 경로(_build_selected_frame_pair)도 같은 타임베이스 버그를 공유하나
    채점(비전 veto) 입력이라 이 debug 범위 밖 — 아래 '알려진 미적용 갭' 에 기록."

## reasoning_checkpoint (기저 비교불가 BLOCKER, 2026-07-27)
- hypothesis: "후보마다 관절 기저가 달라 pose_distance 값이 서로 비교 불가다. 이동+스케일을
  제거하면 남는 자유도가 관절 수에 비례하므로, 관절이 적은 후보가 **최소값 경쟁에서** 구조적
  으로 유리하다. 따라서 탐색 1회 안에서 기저를 고정하면 승자 선택이 like-for-like 가 된다."
- confirming_evidence:
  - "probe A: 실 fz.pose_distance 로 4관절 닮음변환 사본(5.6e-16)이 6관절 거의동일(0.0155)을 이김"
  - "probe B: k=4→8 에서 min 0.185→0.486, p05 0.720→0.935 단조 — 최소값 통계의 편향 실측"
  - "probe C: 실 fixture 실 keypoint 탐색에서 k=4 후보가 k=8 후보 전부를 이김(corr −0.171)"
  - "실데이터 3안 비교: 기저 고정(STRICT) alive 12/12 로 기능 생존, refB 는 채점불가로 배제"
- falsification_test: "기저를 고정했는데도 Pod 재렌더에서 (a) 선택 프레임이 여전히 저관절
  프레임으로 쏠리면 = 기저 고정이 편향을 못 막은 것 → 거리 정의 자체 재설계. (b) 기저를 덮는
  후보가 0이라 전 카드가 anchor 로 폴백되면 = 학생/기준 신뢰관절 교집합이 실제로 비어
  기능 무발동 → 게이트(_KP_CONF_MIN 재사용) 재검토. 두 경우 다 `fault_zoom_pose_match` 로그로 판별."
- fix_rationale: "버그의 정확한 기전은 '거리 값이 후보마다 다른 공간에서 나온다' 이므로, 고쳐야
  할 것은 거리 공식이 아니라 **비교의 공정성**이다. 기저를 학생 프레임(탐색 내내 고정된 유일한
  기준점)으로 못 박으면 모든 후보가 같은 공간에서 나온 값이 된다. 증상(허위 저거리) 억제용
  가중치·페널티를 얹지 않는 이유 = 그건 λ 튜닝이고 fixture overfit 위험."
- blind_spots:
  - "학생 신뢰관절이 많고(예: 8) 기준 window 가 붕괴 구간이면 기저를 덮는 후보가 0 → 무발동.
    안전(anchor 유지)이지만 belle 이 본 그 카드에서 무발동일 가능성 — Pod 로그로만 관측 가능."
  - "실데이터 평가는 ref↔ref proxy(학생 keypoint 로컬 확보 불가, Firestore DNS 차단).
    교차 인물에서 기저 커버리지가 더 낮을 수 있음."
  - "tie 밴드가 곱셈(best*1.05)이라 best 가 0 근처면 밴드가 붕괴. 기저 고정 후에는 best≈0 이
    '진짜 거의 동일' 을 뜻하므로 옳은 동작이라 판단하고 상수를 추가하지 않음 — 단 이 판단은
    pose_distance 가 스케일 정규화(단위 RMS 반경) 되어 값 범위가 고정이라는 전제에 의존."

## 판정 기록 — WARNING(mode3 / top-2 폴백 / override 경로) 확대 유보
- **사실 확인 (코드 추적, 리뷰어 주장 검증됨):**
  - `_build_mode3_fault_zoom_comparisons`(app.py 3288) 은 `user_frame_candidates` 를
    **전달하지 않음** → mode3 zoom 카드는 여전히 DTW 인덱스 원본 기준 프레임. **사실**.
  - Mode1 "편차 top-2 폴백"(app.py 3139, vv.faultJoints 비었을 때) 도 candidates=None →
    미적용. **사실**.
  - override 경로(`user_frame_idx`/`ref_frame_idx`): `_render_fault_zoom` 호출부는 3184/3288
    두 곳뿐이고 **어느 쪽도 이 인자를 넘기지 않음** → 프로덕션 사문(dead) 파라미터.
    리뷰어 지적은 문자적으로 맞으나 실효 영향 없음.
- **커밋 메시지 문구 정정:** 191c296 의 "mode3/legacy 경로 byte-동일" 은 마치 **설계 요구**
  인 것처럼 읽히지만, debug 파일의 실제 제약은 "**sourceFrameIndices 부재/legacy doc** →
  기존 단일프레임 동작 폴백" 이다. 그건 하위호환 조항이지 "mode3 는 교정에서 제외한다" 가
  아니다. 리뷰어 지적대로 **부정확한 프레이밍**이었고 여기서 정정한다.
- **그럼에도 지금 확대하지 않는 결정 (의도적 유보):**
  1. 이 접근은 **아직 단 한 번도 렌더로 검증되지 않았다.** belle 은 포즈매칭된 크롭을 한 장도
     본 적이 없다. 검증 신호가 0인 휴리스틱을 경로 3개로 넓히면 실패 시 원인 분리가 불가능해진다.
  2. mode3 는 기준이 **같은 사람의 지난 영상**이고 dtw fps 공간도 다르다(9fps vs 18fps,
     CR-01). 포즈 거리의 의미와 인덱스 변환 상호작용이 Mode1 과 동일하다는 근거가 없다.
  3. top-2 폴백은 프레임 출처가 다르다(vision window 아님, worst_seconds 기반) — DTW 짝
     window 자체가 없어 anchor 개념이 성립하는지 별도 확인이 필요하다.
- **재검토 트리거:** belle 육안이 Mode1 포즈매칭 크롭을 승인하면 그때 mode3 + top-2 폴백으로
  확대(별도 사이클). 승인 못 받으면 확대할 이유 자체가 없다.
- **현재 상태 명시:** 이건 "정상 동작" 이 아니라 **알려진 미적용 갭**이다.
- **NEW 갭 (2026-07-27, 타임베이스)**: veto still 경로(app.py `_build_selected_frame_pair`
  1885-1898)도 rep 공간 DTW 인덱스로 ref 비디오 배열을 직접 인덱싱 — **같은 4/3 왜곡**.
  단 이 still 은 Gemini vision veto(채점 경로) 입력이라 고치면 faultJoints/점수가 움직인다
  → D-20(표시 전용) 범위 밖, 이 debug 에서 의도적 미수정. **함의가 큼**: veto 가 봐 온
  '기준 프레임'이 실제 DTW 순간보다 이르다 → 별도 사이클로 belle 결정 필요 (채점 영향
  검증 동반). mode1 fault_zoom 크롭만 이번에 교정.

## Current Focus (구 — 같은-포즈 매칭, 2026-07-26)
- status: **fix 구현 완료, 유닛테스트 52 PASS (기존 43 + 신규 9). Pod 재렌더 블로커.**
- **fix (backend/shared/python/sunity_shared/analysis/fault_zoom.py, +165, app.py 무접촉):**
  - 신규 `pose_distance(pose_a, pose_b)` — **공통 신뢰관절**만으로 centroid 이동 + RMS 반경 스케일 정규화 후 관절당 L2 평균. 이동·스케일은 제거(체격/카메라거리/화면위치 차이), **회전·좌우 배치는 일부러 보존** — facing(앞/뒤) 신호가 바로 거기 있으므로 회전 정규화하면 belle 지적을 못 잡는다. 토르소 4관절 고정 기준을 안 쓴 이유 = 역립 구간에서 토르소 전부 살아있는 프레임이 20/70뿐(실측).
  - 신규 `select_pose_matched_ref_frame(...)` — DTW 짝을 **anchor** 로만 쓰고 anchor ±`_POSE_SEARCH_SECONDS`(1.2s) 안 기준 프레임 전수에 대해 학생 포즈와의 거리를 재 최소 선택. 최소 대비 `_POSE_TIE_MARGIN`(5%) 안쪽은 동률로 보고 **anchor 에 가장 가까운 것**(DTW 타이밍 존중, 가중치 λ 튜닝 회피).
  - 게이트: 공통 신뢰관절 `_POSE_MIN_COMMON_JOINTS`(4) 미만 / 좌표 붕괴(스케일 0) / conf 부재(legacy) → None → **anchor 유지 = ea55069 동작 그대로**. 조용한 악화 없음.
  - conf 임계는 기존 `_KP_CONF_MIN`(0.5) 재사용 — 포즈매칭 전용 신규 튜닝상수 0.
  - build 루프에서 confirmed/advisory 양 배치 공통 경유(같은 build 함수). candidates None(mode3/legacy) 경로 미진입 = byte-동일. marker/deficit/채점 무접촉(사후 렌더, deductionBreakdown 불변).
  - `fault_zoom_pose_match analysis_id= region= user_kp= dtw_ref= posed_ref=` 구조 로그 — Pod 덤프에서 발동 여부 관측용(신규 doc 필드 0, TS 계약 무접촉).
- **신규 테스트 9**: 이동/스케일 불변 · **facing 반전 검출(>0.3)** · 최소 공통관절 4 · 붕괴 프레임 None · **anchor 아닌 포즈일치 프레임 선택** · 탐색범위 밖 완벽일치 무시 · 동률→anchor · 학생 저신뢰/legacy → None · **end-to-end refFrameIdx 가 DTW window 밖 포즈일치 프레임** · 판정불가 시 DTW 짝 보존.
- ⚠ **BLOCKER — Pod down**: 9w5es4y760il9w proxy /health=404, 직결 213.173.107.230:17519 refused, runpodctl/API key 로컬 부재. 재렌더 불가 → 학생↔기준 교차 실측 + belle 육안 대기.
- next_action: 커밋 → belle 에게 Pod 기동 요청 → `_inv_check.py` fresh AID 재렌더(shadow phase33-cm3-run1, PR_INVERSION_ENABLED=1) → `fault_zoom_pose_match` 로그로 발동 여부 확인 + faultZoomComparisons refFrameIdx 가 DTW 짝에서 이동했는지 → 크롭 S3 다운로드 → **이미지 직접 open** → belle 육안.

## reasoning_checkpoint (같은-포즈 매칭, 2026-07-26)
- hypothesis: "카드 내 두 패널이 다른 포즈인 원인은 두 가지가 겹친 것. (a) 기준 프레임을 **DTW window position** 으로만 정하는데 DTW 는 관절각(방향 불변) 위에서 계산돼 시각 국면(앞/뒤·팔다리 배치)을 보장하지 않는다. (b) 후보 window 가 ±2프레임(9fps)뿐이라 시각적으로 맞는 기준 프레임이 아예 후보에 없다. 따라서 window 를 확대하고 그 안에서 **학생 프레임과의 2D 포즈 거리 최소** 프레임을 고르면 같은 국면이 잡힌다."
- confirming_evidence:
  - "크롭 PNG 직접 open — knee 카드 학생=등 돌린 웅크림 / 기준=정면 응시 + 다리 뻗음 (다른 국면 실물 확인)"
  - "9fps 프레임 그리드 육안 — S70 에 시각 최적인 기준 프레임은 R68, 현재 쓰는 DTW 짝은 R73"
  - "R68 은 anchor 에서 5프레임 떨어져 현행 ±2 후보 window 밖 = window 내 재선택으로는 도달 불가(구조적 증명)"
  - "ref keypoint conf 실측 — 토르소 고정 정규화 불가(역립 구간 20/70), 공통-신뢰관절 Procrustes 필요"
- falsification_test: "Pod 재렌더에서 (a) 기준 프레임이 DTW 짝에서 안 움직이면 = pose 매칭 미발동(최소 공통관절 기준이 너무 빡빡하거나 학생 keypoint 붕괴) → 임계/신호 재설계. (b) 움직였는데 belle 육안이 여전히 '다른 포즈'면 = 2D keypoint 기하가 이 footage 에서 국면을 판별 못함 → keypoint 품질(IN-01 계열) 또는 비-keypoint 신호로 전환."
- fix_rationale: "belle 요구 = '최대한 비슷한 포즈를 캡처해서 비교'. DTW 는 타이밍 backbone 으로 남기고(anchor), 그 주변 ±search 안에서 시각 포즈 거리 최소를 고른다 = 타이밍 대응을 버리지 않으면서 시각 대응을 추가. 신뢰 못 하는 keypoint 로는 프레임을 옮기지 않고 DTW 짝 그대로(오늘 동작) 폴백 = 조용한 악화 없음."
- blind_spots:
  - "학생 keypointReport 를 로컬에서 못 봄(Firestore DNS 차단) → 학생측 신뢰관절 수가 최소기준을 넘는지 미검증. 못 넘으면 fix 가 이 fixture 에서 no-op."
  - "conf 임계는 신규 튜닝 없이 기존 _KP_CONF_MIN(0.5) 재사용 — 역립 구간에선 보수적이라 발동률이 낮을 수 있음. 발동률은 Pod 덤프로만 관측 가능."
  - "search 폭 1.2s 는 실측 오차(0.55s)의 약 2배 마진으로 정한 값 — 더 큰 타이밍 편차 fixture(power-spin 등)에서 부족/과다 여부 미검증."
  - "비역립 동작 전수 검증 안 됨 (belle 우선순위 ④). 역립 fixture 1건 기준."

## Current Focus (구 — NEW 서브버그, DTW 정렬, 2026-07-25)
- status: 정렬 fix 구현 완료, 유닛테스트 43 PASS. 커밋+push → 라이브 Pod GPU 복구 → 재렌더 → belle 육안 대기.
- **fix**: `build_fault_zoom_comparisons` 루프에서 sel_u/sel_r 독립 선택 제거. 신규 `select_confident_index(user_report, u_cands, members)` 로 학생 가시성 window **position** 1개 선택(크롭 앵커=학생 결함) → 학생 프레임 = `u_cands[pos]`, 기준 프레임 = `ref_frame_candidates[pos]`(DTW 짝). confirmed+advisory 양 배치 공유(둘 다 같은 build 함수 경유 — app.py 무접촉). None-candidates(mode3/legacy) 경로 byte-동일(진입 안 함). marker/deficit 무접촉. 채점 무접촉(사후 렌더, deductionBreakdown 불변).
- **신규 테스트**: `test_ref_frame_dtw_aligned_to_user_not_independent`(user window [3..7]/ref window [10..14] DTW 짝, ref conf peak=pos4 여도 학생 pos0 따라 ref=10), `test_multi_card_ref_frames_stay_dtw_aligned_per_card`(다관절 카드별 u_pos==r_pos), `test_select_confident_index_maps_value_to_position`.
- next_action: 커밋+push → Pod(213.173.107.230:17519) cudnn9 복구(CUDAExecutionProvider 활성화) → `_inv_check.py` fresh AID 재렌더 → faultZoomComparisons 덤프(카드별 user/ref DTW 정렬 확인) → 크롭 S3 → belle 육안(카드 내 student↔reference 같은 순간인지).

## reasoning_checkpoint (NEW 서브버그)
- hypothesis: "카드 안 student↔reference 이질감의 원인은 sel_r 독립선택. window(user/ref candidates)는 position 으로 DTW 대응인데 sel_u=학생 conf 최대값, sel_r=기준 conf 최대값을 각자 고르면 index 가 달라 서로 다른 DTW 순간을 렌더한다."
- confirming_evidence: ["149b770 line 1456-1468: sel_r = select_confident_frame(ref_report, ...) 독립 선택", "app.py 3130-3138: sourceFrameIndices user/reference 는 position 대응 리스트를 그대로 candidates 로 pass-through", "belle 육안: 손 카드 user=148/ref=166 두 패널이 동작의 다른 지점"]
- falsification_test: "재렌더 카드별 u_pos != r_pos 로 나오면(같은 window index 인데도 다른 순간) = position 대응 가정 오류 → DTW path 재검토 필요."
- fix_rationale: "학생 가시성으로 position 1개 선택 후 ref=same-position 후보 → 카드 내 두 패널이 같은 DTW 순간. 학생측 값 선택은 select_confident_frame 위임으로 byte-동일 보존(149b770 검증된 프레임 유지)."
- blind_spots: "position 대응이 실제 DTW 짝인지는 sourceFrameIndices 생성부(features.window_median_angle_deltas)의 user/reference 리스트가 정말 같은 DTW path 로 산출됐는지에 의존. Pod 육안이 최종 판정."

## Current Focus (구 — 프레임 뭉침 fix, 149b770)
- status: fix 구현 완료, 유닛테스트 PASS, 라이브 Pod 재렌더 대기.
- **구조 확정(요구 #1)**: `sourceFrameIndices` = `{"user":[c-2..c+2], "reference":[c-2..c+2]}` = worst-pose 중심 ±window(features.window_median_angle_deltas, window=2) **공용 연속 프레임 리스트**. **관절별 데이터 아님** (debug 초기 가설의 "관절별 데이터 존재"는 오류 — sfi["user"] 는 fault_joints 순서 정렬 배열이 아니라 단일 window). 관절→프레임 매핑은 sfi 에 없다. 따라서 관절별 차별화 = 이 window 안에서 unit(관절/region) 멤버 confidence 최대 프레임을 카드마다 독립 선택(select_confident_frame per-unit).
- **근본 원인 확정**: `_build_fault_zoom_comparisons`(app.py ~3106) 가 window 를 `select_confident_frame(user_report, u_list, **전 fault_joints**)` 로 단일 프레임으로 뭉개 `build_fault_zoom_comparisons` 에 넘김 → 함수가 그 단일 프레임을 unit 루프 전체에 재사용 → 모든 카드 동일 userFrame.
- **fix**: (1) app.py 는 window(u_list/r_list)를 `user_frame_candidates`/`ref_frame_candidates` 로 그대로 pass-through (단일 뭉개기 제거), confirmed+advisory 양쪽. (2) `build_fault_zoom_comparisons` 루프 안에서 candidates 주어지면 unit 멤버로 per-unit `select_confident_frame` → unit 별 u_idx/kp_idx/r_idx/kp_idx/ref_match 독립. candidates None(mode3/legacy) → 단일 프레임 경로 byte-동일 폴백.
- next_action: 커밋+push → 라이브 Pod(213.173.107.230:17519) `git pull --ff-only` → `_inv_check.py` 로 elbow-twist-sister/fault (shadow phase33-cm3-run1, fresh AID) 재분석 → faultZoomComparisons 덤프 → 카드별 userFrameIdx 상이 확인 → 크롭 다운로드 → belle 육안.

## Constraints
- 채점/임계 무접촉 (D-20/D-29). 렌더 전용 — deductionBreakdown byte 불변.
- sourceFrameIndices 구조를 코드로 확인 후 구현. 틀리면 크롭이 더 엉뚱한 프레임 가리킴.
- 검증 = 라이브 Pod 9w5es4y760il9w 재렌더 → S3 크롭 다운로드 → **실제 이미지 열어서** 각 결함이 서로 다른 프레임 + 맞는 관절에서 잘렸는지 육안. "코드 통과"는 검증 아님 (§6.6, [[open-the-artifact-before-claiming-done]]).
  - Pod env/드라이버: `backend/evals/phase25/run_sweep.py` 헤더 (RTMW+Gemini export), `/workspace/_inv_check.py` (단일 fixture 드라이버, INVCHK_AID + SUNITY_SHADOW_REFERENCE_VERSION env 지원). 인증 헤더 X-RunPod-Token, 프록시 curl.
- 하위호환: sourceFrameIndices 부재/legacy doc → 기존 단일프레임 동작 폴백 유지.

## Eliminated
- (반증) "같은 영상 두 번" 버그 아님: 학생=fixtures/phase15/elbow-twist-sister/fault.mp4, 기준=reference/ref-elbow-twist-sister.mp4 (다른 S3 객체). 시각적 유사=같은 스튜디오.

## Related (이 debug 범위 밖 — 확대비교 트랙 33-09/10/12 seed)
- advisory 크롭에 위치 마커 없음 (fault_zoom.py: 좌표 불확실 시 circle=False + deficit 배지 유지 = 위치 없이 숫자만).
- 각도 숫자 배지("81°"/"30°") 사용자 표기 부적절 (belle: 각도 인식 불가) — 제거 검토.
- 대체문구 "전체 자세가 정은지 선수보다 덜 정돈된 편이에요" 비실행적 → 확정결함 리드 + "AI 공부 중" + 코치 라우팅.

## Resolution (5차 — pair-opt 궤적 매칭 + 타임스탬프, ACTIVE — awaiting belle)
- root_cause (belle #3 반려, 3갈래 — 전부 실측):
  1. **탐색창이 진짜 매칭을 구조적으로 배제**: DTW anchor 가 역립 구간에서 video 기준
     ≈2.4s drift(GT rep51 vs anchor rep73) → ±1.2s 창 안에 같은-포즈(tuck) 프레임 부재.
  2. **환각 keypoint 가 단일프레임 지표를 기만**: ref 무릎이 머리에 환각(conf 0.68~0.70,
     오버레이 실증)돼 학생의 진짜 tuck 무릎(턱 포즈라 머리 옆)과 우연히 겹침 → 잘못된
     프레임 v90 이 고립 최소(0.45, 이웃 0.84+)로 압승. + anchor-근접 tie-break 가
     동률(진짜 tuck v80=0.46)에서 환각 쪽을 유지.
  3. **학생측 프레임 선택도 환각 취약**: right_shoulder 가 kp144 에서 얼굴에 환각
     (conf 0.57)돼 conf argmax 가 0.01 노이즈 차로 진짜 어깨 프레임(kp148, 0.56)을
     제침 — "목을 잡고 있음" 의 실체. (149b770 의 "잘 잡힌" 크롭은 다른 doc(CPU 런)
     노이즈가 반대로 떨어진 것 — 규칙 회귀 아님.)
- fix (commit e8613e8, fault_zoom.py 전용 — app.py 무접촉, 표시 전용 D-20):
  - `select_pose_matched_pair`: 학생 프레임(valid 멤버 보유 = 마커 가능 프레임만)과
    기준 프레임을 **±2 궤적 평균**으로 동시 최적화. 환각은 프레임 간 flicker 라
    궤적 평균에서 자연 강등 — 환각 감지 임계/λ 0개. anchor-근접 tie-break 제거
    (pair 경로). None → 종전 사슬(ea55069+95ee80f) 폴백.
  - `_POSE_SEARCH_SECONDS` 1.2→4.0 (drift 실측 근거). `_POSE_TRAJ_RADIUS=2` 신설
    (features window=2 관행 정합).
  - `_stamp_time`: 양 패널 좌하단 비디오 타임스탬프(belle 승인 요구 4). 전신 폴백
    ref 패널 미표기. 각도 배지는 유지(제거는 belle 질문으로 회부).
- verification:
  - ✅ 유닛 69 PASS(신규 9) / 인접 320 PASS / 전체 61f/12e pre-existing 동일(+9 pass)
  - ✅ Pod driven 렌더 = 프로브 예측 3카드 완전 일치 (legs u70→ref v70 / shoulder
    u74(kp148)→v132 / hand u74→v132)
  - ✅ 크롭 3장 직접 open — knee 양패널 tuck+같은 facing+무릎 포함(RV070 크롭박스
    실측), shoulder 마커=진짜 어깨(belle 승인 프레임), hand 같은 부위, 타임스탬프 표기
  - ✅ 자연 렌더 SCORE 60 불변(D-20 5연속)
  - ⏳ belle 육안 (S3 drivepair260728) — 승인 시 서버 재기동 + archive
- 남은 후속: ① 서버(uvicorn) 재기동으로 fix 반영(belle 승인 후) ② **Gemini moment
  extractor 침묵 24h+ 지속**(자연 렌더 카드 0장 — 별건 조사 후보 승격) ③ veto still
  타임베이스(채점인접, 별도 사이클) ④ app.py:2018 `(at or 0.0)` falsy-collapse(별건)
  ⑤ mode3/top-2 폴백 확대(승인 후) ⑥ power-spin 등 비역립 전수 검증(belle ④)
  ⑦ advisory 손 카드 실행가능성 + 각도 배지 제거 여부(belle 설계 결정).

## Resolution (4차 — ref 타임베이스 매핑 + 게이트 재설계, 구 — 5차로 계승)
- root_cause (2겹, 2026-07-27 확정):
  1. **ref 표시 타임베이스 불일치**: referenceKeypointReport(phase4_v1 재처리)는 raw
     매 2프레임 샘플(329@"18fps" = 콘텐츠 18.3s)인데 렌더러 frame_extractor 는 PTS
     9fps(220프레임 = 24.4s). 렌더러가 rep 공간 인덱스로 비디오 배열을 identity
     인덱싱 → **모든 ref 크롭이 자기 시점의 3/4 지점(≈2.7s 이른 순간)** 표시.
     실측: 출하 RTMW 로 rep↔video 대응 산출 → t_vid=(4/3)·t_rep, 오프셋 0.
     학생측은 report 가 같은 extractor 프레임에서 in-run 생성이라 무왜곡 — 학생
     패널만 늘 맞았던 이유. belle "정은지 쪽은 아예 다른 장면"+"부위조차 안 맞음"
     (크롭 박스 좌표는 진짜 순간, 이미지는 다른 순간)의 근본원인.
  2. **pose-match 무발동 게이트**: (a) user report 12관절 vs ref report 8관절
     (ankle/elbow 부재) 이름공간 불일치 → 기저 커버 구조적 0, (b) conf>=0.5 강성
     게이트가 역립 학생 프레임(신뢰 2~3관절)을 차단.
- fix (commit 4cb272a, fault_zoom.py 전용 — app.py 무접촉, 표시 전용 D-20):
  - `ref_display_frame_index`: rep 공간 → 비디오 배열 길이비 선형 매핑 (상수 0,
    정합 ref/mode3 는 identity 자기보정). 크롭 지점에서만 적용, refFrameIdx(kp 공간)
    방출 불변(뷰어 계약 무접촉).
  - `select_pose_matched_ref_frame` 재설계: 기저 = finite 좌표 ∩ ref 이름공간 ∩
    conf>0, 가중 = 학생 confidence(탐색 내 고정 — 95ee80f 비교공정성 불변). legacy
    (conf 배열 부재) → None → anchor 보수성 유지. ref conf 는 매칭 미사용(붕괴 구간
    무발동 재발 방지, garbage 좌표는 거리로 자기배제).
  - `pose_distance(weights=)` 가중 Procrustes. 비가중 경로 byte-보존.
- verification:
  - ✅ 유닛 60 PASS (신규: 저신뢰 발동/legacy None/이름공간 교집합/가중 할인/타임베이스
    매핑/e2e 매핑 크롭). 전체 스위트 61 fail/12 err = pre-existing 동일, 3443 passed.
  - ✅ Pod 실데이터: 출하 build 구동(아침 window) → 3카드 예측값 전부 일치
    (pose_match 73→67/75→76/77→86, video 90/102/115, 학생측 불변).
  - ✅ 크롭 PNG 직접 open — 3카드 전부 학생↔정은지 같은 국면·facing·부위.
    S3: results/phase25eval/drivetb260727/drive_zoom_{left_knee,adv_right_shoulder,
    adv_right_hand}.png
  - ✅ SCORE 60 불변 (tb~tb5 renders — 채점 무접촉 실증).
  - ⏳ belle 육안 + 자연 렌더 재확인 (Gemini moment 일시 장애 회복 후).
- 남은 후속: ① 서버(uvicorn, 6d4722e) 재기동으로 fix 반영(belle 승인 후) ② veto still
  경로 동일 타임베이스 버그(채점인접 — 별도 사이클, belle 결정) ③ app.py:2019
  `(at or 0.0)` None→frame0 붕괴(별건) ④ mode3/top-2 폴백 확대(승인 후) ⑤ 비역립
  power-spin 전수 검증(belle 우선순위 ④).

## Resolution (3차 — 같은-포즈 매칭 + 기저 고정, 완료 — 4차로 계승)
- root_cause: 기준 패널 프레임을 **DTW window position** 으로만 정했다. DTW 는 관절각(방향 불변) 시퀀스 위에서 계산되므로 타이밍만 대응시킬 뿐 시각 국면(앞/뒤 facing·굽힘/폄)을 보장하지 않는다 → 학생이 등 돌려 웅크린 순간에 정은지가 정면 응시 + 다리 뻗은 순간이 짝지어졌다. 게다가 후보 window 가 ±2프레임(9fps)뿐이라 **시각적으로 맞는 기준 프레임(실측 5프레임=0.55s 밖)이 후보에 아예 없었다** — window 내 재선택으로는 구조적으로 도달 불가.
  - **서브 root_cause (2026-07-27 BLOCKER)**: 1차 구현(191c296)의 pose_distance 가 후보마다 자기 교집합 관절로 채점 → 값이 서로 다른 공간에서 나와 비교 불가. 자유도가 관절 수에 비례해 **저관절 후보가 최소값 경쟁에서 구조적 승리**(실 fixture 재현: k=4 후보가 k=8 전부 추월).
- fix: DTW 짝을 anchor 로 강등하고, anchor ±1.2s 확대 탐색 안에서 **학생 프레임과 pose_distance 최소**인 기준 프레임을 선택. 거리 = 공통 신뢰관절 Procrustes(이동+스케일 정규화, 회전·좌우 보존). **관절 기저 = 학생 crop 프레임 신뢰관절로 탐색 내내 고정(95ee80f)** — 기저 미커버 후보는 채점 불가로 제외, 모든 후보가 동일 관절 공간에서 경쟁. 판정 불가 시 anchor 유지(종전 동작).
- files_changed: backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom.py (app.py 무접촉 — 배선은 ea55069 에서 이미 candidates pass-through). commits: 191c296(포즈매칭) + 95ee80f(기저 고정).
- verification:
  - ✅ 유닛테스트 55 PASS (191c296 신규 9 + 95ee80f 신규 3 — 기저 부분후보 배제/채점관절 규정/저관절 우승 불가)
  - ✅ 백엔드 전체 스위트 A/B 회귀 0 — HEAD revert ↔ fix 적용 61 fail/12 err 동일(+3 pass = 신규 테스트). pre-existing 은 gemini/body-profile 계열, fault_zoom 미참조
  - ✅ 지표 실물 검증 — 실 ref keypoint 랭킹 산출 후 **해당 프레임 이미지 직접 open**, 최근접=웅크린 역립 계열 / 최원거리=편 역립·선 자세로 분리 확인
  - ✅ 출하 함수 실 keypoint 검증(95ee80f) — 12/12 독립계산 일치, 저관절 승자 0, 종전 허위승자 2건 채점불가로 배제
  - ⏳ **미완: Pod 재렌더(학생↔기준 교차 실측) + belle 육안** — Pod down 으로 블로킹
- 남은 belle 우선순위 (이 fix 뒤): ① 크롭 표기 숫자 ≠ 채점 숫자 ② advisory 크롭이 감점부위로 오해 ③ 각도 숫자 노출 제거 ④ 비역립(power-spin) 전수 검증 ⑤ 크롭+감점근거 세트

## Resolution (2차 — 프레임 뭉침 + DTW 정렬, 완료)
- root_cause: `_build_fault_zoom_comparisons` 가 worst-pose window(sourceFrameIndices, 관절별 아님·공용 ±2 리스트)를 select_confident_frame(전 fault_joints)로 단일 프레임으로 뭉개 build_fault_zoom_comparisons 에 넘겨, 함수가 그 단일 프레임을 모든 crop unit 에 재사용 → 결함마다 같은 프레임.
- fix: window 를 candidates 로 pass-through 하고 build 루프가 unit 별로 confident-frame 을 독립 선택하도록 변경(confirmed+advisory). 채점 무접촉(deductionBreakdown byte-불변 — fault_zoom 은 complete 이후 사후 렌더, result read-only).
- files_changed: backend/functions/pipeline/app.py, backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom.py
- verification: 유닛테스트 118 PASS(신규 3: per-joint 상이 프레임 / candidates-none byte-동일 폴백 / legacy conf 부재 median 폴백). 라이브 Pod 육안 = pending (belle).
- reasoning_checkpoint:
    hypothesis: "select_confident_frame(전 fault_joints) 단일 뭉개기가 모든 카드를 한 프레임에 고정 — 원인은 뭉개기 지점, sfi 는 공용 window 라 관절별 프레임은 window 내 per-unit confident 선택으로만 창발."
    confirming_evidence: ["features.window_median_angle_deltas: sourceFrameIndices=단일 ±window 공용 리스트(관절별 아님)", "라이브 Pod 6-fixture 전 카드 userFrame=140 동일", "build_fault_zoom_comparisons 가 u_idx/u_kp_idx 를 루프 밖에서 1회 계산 후 전 unit 재사용"]
    falsification_test: "Pod 재렌더에서 카드별 userFrameIdx 가 여전히 전부 동일하면 = window(±2)가 너무 좁아 confidence 가 붕괴 → 관절별 최악-편차 프레임 트랙(별도 데이터) 필요."
    fix_rationale: "뭉개기를 제거하고 window 를 그대로 넘겨 unit 별 선택 → 각 카드가 자기 관절 최고 가시성 프레임. 채점 경로 무접촉(사후 렌더, result read-only)."
    blind_spots: "±2 window(≈0.44s)라 관절 confidence peak 이 같은 프레임이면 여전히 동일 프레임 가능(회전 동작에선 좌우 관절 가시성 상이 기대). 실증은 Pod 육안."
