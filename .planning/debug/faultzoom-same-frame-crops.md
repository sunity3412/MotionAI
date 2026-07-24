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

## Current Focus (NEW 서브버그 — DTW 정렬, 2026-07-25)
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

## Resolution
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
