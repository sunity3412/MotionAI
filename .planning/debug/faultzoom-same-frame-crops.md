---
status: awaiting_human_verify
trigger: "확대비교(fault-zoom) 크롭이 모든 결함 관절에 대해 같은 단일 프레임에서 잘려 나온다 — 결함별 최악 순간이 아니라 한 순간의 부위별 확대일 뿐. belle §6.6 재발 버그"
created: 2026-07-25
updated: 2026-07-25
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

## Current Focus (ACTIVE — 같은-포즈 매칭, 2026-07-26)
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

## Resolution (3차 — 같은-포즈 매칭, ACTIVE)
- root_cause: 기준 패널 프레임을 **DTW window position** 으로만 정했다. DTW 는 관절각(방향 불변) 시퀀스 위에서 계산되므로 타이밍만 대응시킬 뿐 시각 국면(앞/뒤 facing·굽힘/폄)을 보장하지 않는다 → 학생이 등 돌려 웅크린 순간에 정은지가 정면 응시 + 다리 뻗은 순간이 짝지어졌다. 게다가 후보 window 가 ±2프레임(9fps)뿐이라 **시각적으로 맞는 기준 프레임(실측 5프레임=0.55s 밖)이 후보에 아예 없었다** — window 내 재선택으로는 구조적으로 도달 불가.
- fix: DTW 짝을 anchor 로 강등하고, anchor ±1.2s 확대 탐색 안에서 **학생 프레임과 pose_distance 최소**인 기준 프레임을 선택. 거리 = 공통 신뢰관절 Procrustes(이동+스케일 정규화, 회전·좌우 보존). 판정 불가 시 anchor 유지(종전 동작).
- files_changed: backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom.py (app.py 무접촉 — 배선은 ea55069 에서 이미 candidates pass-through)
- verification:
  - ✅ 유닛테스트 52 PASS (신규 9 — facing 반전 검출 / 탐색범위 / 동률 tie-break / 폴백 / end-to-end)
  - ✅ 백엔드 전체 스위트 회귀 0 — 잔여 실패 45건 + 수집오류 12건은 HEAD 의 fault_zoom.py 로 되돌려도 **동일하게 재현**(pre-existing, gemini/body-profile 계열, fault_zoom 미참조)
  - ✅ 지표 실물 검증 — 실 ref keypoint 랭킹 산출 후 **해당 프레임 이미지 직접 open**, 최근접=웅크린 역립 계열 / 최원거리=편 역립·선 자세로 분리 확인
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
