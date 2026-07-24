---
status: verifying
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
- timestamp: 2026-07-25 라이브 Pod 9w5es4y760il9w, elbow-twist-sister/fault 2회 재분석
  - shadow phase33-cm3-run1: crop left_knee userFrame=140 / right_shoulder userFrame=140 (둘 다 140, refFrame 162)
  - production phase4_v1: crop left_knee / left_hand / left_shoulder 전부 userFrame=140 (refFrame 324)
  - 모든 크롭 동일 userFrame + 동일 refFrame. 관절만 다름.

## Current Focus
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
