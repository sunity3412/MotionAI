---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: 17
task: T-1
report_type: keypoint-mapping-audit
mapping_sources_audited: 5
mapping_edit_authorization: prohibited
verdict: blocked/no-static-mapping-defect
generated: 2026-06-01
---

# Plan 01-17 T-1 — Keypoint Mapping Audit (RTMPose / MediaPipe / 공유 H36M→COCO / spike_rtmpose private copy / JOINT_ANGLES)

본 보고서 = Plan 01-17 T-1 책임 박제. RTMPose / MediaPipe / 공유 H36M_TO_COCO17_LIMB_PAIRS / spike_rtmpose._h36m17_to_coco17_subset / skeleton.JOINT_ANGLES 5개 mapping source 를 canonical expected tuple 과 비교한다. 모든 source 가 canonical 일치 시 `blocked/no-static-mapping-defect` 박제 후 T-2 mapping edit 금지.

---

## (1) Plan 16 verdict 인용 — 본 plan dominant root cause

Plan 01-16 belle Pod live mode verdict (`spike_measurement_trace_live_20260601_1144`, ref-invert 단독, 173 frame):

| pair                              | swap_ratio | 정상 임계 0.05 | verdict                  |
|-----------------------------------|------------|----------------|--------------------------|
| left_elbow_vs_right_elbow         | **1.00**   | 0.05           | **systematic (100% swap)** |
| left_shoulder_vs_right_shoulder   | 0.01       | 0.05           | 정상                     |
| left_hip_vs_right_hip             | 0.32       | 0.05           | 의심                     |
| left_knee_vs_right_knee           | 0.14       | 0.05           | 정상 근접                |

Cross-engine joint 별 disagreement 평균:

| joint           | mean_abs_deg |
|-----------------|--------------|
| **left_elbow**  | **75.88°** (peak) |
| left_knee       | 68.72°       |
| left_shoulder   | 45.23°       |
| right_hip       | 30.42°       |
| right_shoulder  | 17.06°       |
| left_hip        | 15.89°       |
| right_knee      | 14.46°       |
| right_elbow     | 8.91°        |

Plan 16 dominant 가설 = "RTMPose+MB 와 MediaPipe+MB 두 변환 path 중 한 쪽 left/right keypoint index 가 systematic swap". 본 audit 의 책임 = 5개 mapping source 가 canonical 인지 정합 검증.

---

## (2) RTMPose direct_map audit 표 (`backend/research/spikes/rtmpose_to_h36m17.py:206-220`)

상수 박제 (`rtmpose_to_h36m17.py:103-115, 119-134`): `_COCO_*` (5..16) + `_H36M_*` (0..16). expected tuple = `_COCO_<JOINT>` → `_H36M_<JOINT>` (좌우 정합).

| # | COCO idx | H36M idx | COCO name (skeleton.KEYPOINT_NAMES) | H36M name (rtmpose_to_h36m17.H36M_JOINT_NAMES) | 좌우 일치 | 판정 |
|---|----------|----------|--------------------------------------|------------------------------------------------|----------|------|
| 1 | 12 (`_COCO_R_HIP`)       | 1 (`_H36M_R_HIP`)       | right_hip      | r_hip      | R = R | OK |
| 2 | 14 (`_COCO_R_KNEE`)      | 2 (`_H36M_R_KNEE`)      | right_knee     | r_knee     | R = R | OK |
| 3 | 16 (`_COCO_R_ANKLE`)     | 3 (`_H36M_R_FOOT`)      | right_ankle    | r_foot     | R = R | OK |
| 4 | 11 (`_COCO_L_HIP`)       | 4 (`_H36M_L_HIP`)       | left_hip       | l_hip      | L = L | OK |
| 5 | 13 (`_COCO_L_KNEE`)      | 5 (`_H36M_L_KNEE`)      | left_knee      | l_knee     | L = L | OK |
| 6 | 15 (`_COCO_L_ANKLE`)     | 6 (`_H36M_L_FOOT`)      | left_ankle     | l_foot     | L = L | OK |
| 7 | 0  (`_COCO_NOSE`)        | 10 (`_H36M_HEAD`)       | nose           | head       | central | OK |
| 8 | 5  (`_COCO_L_SHOULDER`)  | 11 (`_H36M_L_SHOULDER`) | left_shoulder  | l_shoulder | L = L | OK |
| 9 | 7  (`_COCO_L_ELBOW`)     | 12 (`_H36M_L_ELBOW`)    | left_elbow     | l_elbow    | L = L | OK |
| 10| 9  (`_COCO_L_WRIST`)     | 13 (`_H36M_L_WRIST`)    | left_wrist     | l_wrist    | L = L | OK |
| 11| 6  (`_COCO_R_SHOULDER`)  | 14 (`_H36M_R_SHOULDER`) | right_shoulder | r_shoulder | R = R | OK |
| 12| 8  (`_COCO_R_ELBOW`)     | 15 (`_H36M_R_ELBOW`)    | right_elbow    | r_elbow    | R = R | OK |
| 13| 10 (`_COCO_R_WRIST`)     | 16 (`_H36M_R_WRIST`)    | right_wrist    | r_wrist    | R = R | OK |

소계 13/13 canonical (좌우 일치). PLAN 16 박제 left_elbow swap_ratio 1.00 root cause 의 후보 #1 (rtmpose direct_map) = **canonical, 매핑 결함 없음**.

---

## (3) MediaPipe direct_map audit 표 (`backend/research/spikes/mediapipe_to_h36m17.py:184-198`)

상수 박제 (`mediapipe_to_h36m17.py:86-98, 102-117`): MediaPipe pose_landmarker 표준 `_MP_*` (0, 11..16, 23..28) + `_H36M_*` (0..16). expected tuple = `_MP_<JOINT>` → `_H36M_<JOINT>` (좌우 정합).

| # | MP idx | H36M idx | MP name (MediaPipe pose_landmarker 표준) | H36M name (mediapipe_to_h36m17.H36M_JOINT_NAMES) | 좌우 일치 | 판정 |
|---|--------|----------|------------------------------------------|--------------------------------------------------|----------|------|
| 1 | 24 (`_MP_R_HIP`)      | 1 (`_H36M_R_HIP`)       | r_hip      | r_hip      | R = R | OK |
| 2 | 26 (`_MP_R_KNEE`)     | 2 (`_H36M_R_KNEE`)      | r_knee     | r_knee     | R = R | OK |
| 3 | 28 (`_MP_R_ANKLE`)    | 3 (`_H36M_R_FOOT`)      | r_ankle    | r_foot     | R = R | OK |
| 4 | 23 (`_MP_L_HIP`)      | 4 (`_H36M_L_HIP`)       | l_hip      | l_hip      | L = L | OK |
| 5 | 25 (`_MP_L_KNEE`)     | 5 (`_H36M_L_KNEE`)      | l_knee     | l_knee     | L = L | OK |
| 6 | 27 (`_MP_L_ANKLE`)    | 6 (`_H36M_L_FOOT`)      | l_ankle    | l_foot     | L = L | OK |
| 7 | 0  (`_MP_NOSE`)       | 10 (`_H36M_HEAD`)       | nose       | head       | central | OK |
| 8 | 11 (`_MP_L_SHOULDER`) | 11 (`_H36M_L_SHOULDER`) | l_shoulder | l_shoulder | L = L | OK |
| 9 | 13 (`_MP_L_ELBOW`)    | 12 (`_H36M_L_ELBOW`)    | l_elbow    | l_elbow    | L = L | OK |
| 10| 15 (`_MP_L_WRIST`)    | 13 (`_H36M_L_WRIST`)    | l_wrist    | l_wrist    | L = L | OK |
| 11| 12 (`_MP_R_SHOULDER`) | 14 (`_H36M_R_SHOULDER`) | r_shoulder | r_shoulder | R = R | OK |
| 12| 14 (`_MP_R_ELBOW`)    | 15 (`_H36M_R_ELBOW`)    | r_elbow    | r_elbow    | R = R | OK |
| 13| 16 (`_MP_R_WRIST`)    | 16 (`_H36M_R_WRIST`)    | r_wrist    | r_wrist    | R = R | OK |

소계 13/13 canonical (좌우 일치). PLAN 16 박제 root cause 후보 #2 (mediapipe direct_map) = **canonical, 매핑 결함 없음**.

---

## (4) 공유 H36M_TO_COCO17_LIMB_PAIRS audit 표 (`backend/research/spikes/mediapipe_to_h36m17.py:128-141`)

H36M → COCO 12 tuple back-projection (양 엔진 공유). expected tuple = `(_H36M_<JOINT>, COCO_<JOINT>)` (좌우 정합).

| # | H36M idx | H36M name  | COCO idx | COCO name (skeleton.KEYPOINT_NAMES) | 좌우 일치 | 판정 |
|---|----------|------------|----------|--------------------------------------|----------|------|
| 1 | 11 (`_H36M_L_SHOULDER`) | l_shoulder | 5  | left_shoulder  | L = L | OK |
| 2 | 14 (`_H36M_R_SHOULDER`) | r_shoulder | 6  | right_shoulder | R = R | OK |
| 3 | 12 (`_H36M_L_ELBOW`)    | l_elbow    | 7  | left_elbow     | L = L | OK |
| 4 | 15 (`_H36M_R_ELBOW`)    | r_elbow    | 8  | right_elbow    | R = R | OK |
| 5 | 13 (`_H36M_L_WRIST`)    | l_wrist    | 9  | left_wrist     | L = L | OK |
| 6 | 16 (`_H36M_R_WRIST`)    | r_wrist    | 10 | right_wrist    | R = R | OK |
| 7 | 4  (`_H36M_L_HIP`)      | l_hip      | 11 | left_hip       | L = L | OK |
| 8 | 1  (`_H36M_R_HIP`)      | r_hip      | 12 | right_hip      | R = R | OK |
| 9 | 5  (`_H36M_L_KNEE`)     | l_knee     | 13 | left_knee      | L = L | OK |
| 10| 2  (`_H36M_R_KNEE`)     | r_knee     | 14 | right_knee     | R = R | OK |
| 11| 6  (`_H36M_L_FOOT`)     | l_foot     | 15 | left_ankle     | L = L | OK |
| 12| 3  (`_H36M_R_FOOT`)     | r_foot     | 16 | right_ankle    | R = R | OK |

소계 12/12 canonical (좌우 일치). PLAN 16 박제 root cause 후보 #3 (공유 H36M_TO_COCO17_LIMB_PAIRS) = **canonical, 매핑 결함 없음**.

---

## (5) spike_rtmpose private H36M → COCO copy audit 표 (`backend/research/spikes/spike_rtmpose.py:398-411`)

`_h36m17_to_coco17_subset` 내부 12 tuple `pairs`. expected tuple set = 공유 `H36M_TO_COCO17_LIMB_PAIRS` 와 정확 일치.

| # | H36M idx | COCO idx | H36M name  | COCO name      | 공유 pairs 와 일치 | 판정 |
|---|----------|----------|------------|----------------|---------------------|------|
| 1 | 11 | 5  | l_shoulder | left_shoulder  | OK | OK |
| 2 | 14 | 6  | r_shoulder | right_shoulder | OK | OK |
| 3 | 12 | 7  | l_elbow    | left_elbow     | OK | OK |
| 4 | 15 | 8  | r_elbow    | right_elbow    | OK | OK |
| 5 | 13 | 9  | l_wrist    | left_wrist     | OK | OK |
| 6 | 16 | 10 | r_wrist    | right_wrist    | OK | OK |
| 7 | 4  | 11 | l_hip      | left_hip       | OK | OK |
| 8 | 1  | 12 | r_hip      | right_hip      | OK | OK |
| 9 | 5  | 13 | l_knee     | left_knee      | OK | OK |
| 10| 2  | 14 | r_knee     | right_knee     | OK | OK |
| 11| 6  | 15 | l_foot     | left_ankle     | OK | OK |
| 12| 3  | 16 | r_foot     | right_ankle    | OK | OK |

소계 12/12 canonical, 공유 pairs 와 set equality. spike_rtmpose private copy = **canonical, 매핑 결함 없음**.

---

## (6) skeleton.JOINT_ANGLES audit 표 (`backend/shared/python/sunity_shared/analysis/skeleton.py:39-48`)

8 angle joint 의 `(a, vertex, c)` triplet. expected = vertex == key AND `left_*` vertex 면 a/c 모두 `left_*`, `right_*` vertex 면 a/c 모두 `right_*` (자체 정합).

| # | key            | a              | vertex (== key?) | c              | 자체 정합 (left/right 일관) | 판정 |
|---|----------------|----------------|------------------|----------------|------------------------------|------|
| 1 | left_elbow     | left_shoulder  | left_elbow ✓     | left_wrist     | L L L | OK |
| 2 | right_elbow    | right_shoulder | right_elbow ✓    | right_wrist    | R R R | OK |
| 3 | left_shoulder  | left_elbow     | left_shoulder ✓  | left_hip       | L L L | OK |
| 4 | right_shoulder | right_elbow    | right_shoulder ✓ | right_hip      | R R R | OK |
| 5 | left_hip       | left_shoulder  | left_hip ✓       | left_knee      | L L L | OK |
| 6 | right_hip      | right_shoulder | right_hip ✓      | right_knee     | R R R | OK |
| 7 | left_knee      | left_hip       | left_knee ✓      | left_ankle     | L L L | OK |
| 8 | right_knee     | right_hip      | right_knee ✓     | right_ankle    | R R R | OK |

소계 8/8 자체 정합. PLAN 16 박제 root cause 후보 #5 (JOINT_ANGLES) = **canonical, 매핑 결함 없음**.

---

## (7) Static Mapping Verdict

| Mapping Source | Audit Rows | Failed Rows | Verdict |
|----------------|------------|-------------|---------|
| `rtmpose_to_h36m17.direct_map` (line 206-220) | 13 | 0 | canonical |
| `mediapipe_to_h36m17.direct_map` (line 184-198) | 13 | 0 | canonical |
| `mediapipe_to_h36m17.H36M_TO_COCO17_LIMB_PAIRS` (line 128-141) | 12 | 0 | canonical |
| `spike_rtmpose._h36m17_to_coco17_subset` pairs (line 398-411) | 12 | 0 | canonical |
| `skeleton.JOINT_ANGLES` (line 39-48) | 8 | 0 | canonical |

**verdict: `blocked/no-static-mapping-defect`**

5개 mapping source 모두 canonical expected tuple 과 정확 일치. Plan 16 박제 dominant root cause (`left_elbow_vs_right_elbow` swap_ratio 1.00, cross-engine 75.88° peak) 는 **static keypoint index mapping defect 가 아니다.** 본 plan 의 T-2 mapping edit 책임 영역은 비어 있음.

---

## (8) detect_lr_swap asymmetric sentinel 재실행 결과 (current-code pipeline)

PLAN T-1 step 7 박제 — canonical assertion 이 모두 PASS 인 경우 sentinel 결과는 "근거 보조 (supports the no-static verdict)" 로만 기록된다 (verdict 자체는 Static Mapping Verdict 가 결정).

**baseline asymmetric sentinel (양 엔진 동일 semantic 입력)** — 좌우 좌표가 모두 고유한 sentinel keypoint 를 RTMPose / MediaPipe 두 변환 path 동일하게 통과시킨 후 detect_lr_swap 호출. expected = swap_frame_ratio = 0.0, swap_frame_ratio_per_pair 4 pair 모두 = 0.0.

실측값 박제 (`test_mapping_audit.py::TestStaticMappingAbortGate::test_canonical_pipeline_asymmetric_sentinel_swap_zero` 검증 — Plan 17 T-1 단위 테스트 실행 결과):

| pair                              | swap_ratio | 임계 0.05 | 판정 |
|-----------------------------------|------------|-----------|------|
| left_elbow_vs_right_elbow         | 0.00       | 0.05      | PASS |
| left_shoulder_vs_right_shoulder   | 0.00       | 0.05      | PASS |
| left_hip_vs_right_hip             | 0.00       | 0.05      | PASS |
| left_knee_vs_right_knee           | 0.00       | 0.05      | PASS |
| swap_frame_ratio (4 pair 평균)     | 0.00       | 0.05      | PASS |

**intentional swapped sentinel (한 엔진의 left/right elbow column 교환)** — detect 함수 자체 정합 검증. expected = elbow pair ratio ≥ 0.30.

| pair                              | swap_ratio | 임계 0.30 | 판정 |
|-----------------------------------|------------|-----------|------|
| left_elbow_vs_right_elbow         | 1.00       | 0.30      | DETECTED |

결론: static mapping 이 canonical 인 stub fixture 에서 두 path 가 동일 좌우 부호를 출력 → detect_lr_swap = 0. 한쪽 path 에 의도적 swap 을 주입하면 detect_lr_swap = 1.0. **Plan 16 belle Pod live 173 frame 의 swap_ratio 1.00 은 static mapping defect 가 아니라 lift path 자체의 occlusion 좌우 keypoint 신뢰도 (Plan 16 가설 (b)(c)(d) strong 박제) 의 부산물.**

---

## (9) T-2 Eligibility

```yaml
eligible: false
reason: blocked/no-static-mapping-defect
mapping_edits_allowed: false
files_blocked_from_edit:
  - backend/research/spikes/rtmpose_to_h36m17.py
  - backend/research/spikes/mediapipe_to_h36m17.py
  - backend/research/spikes/spike_rtmpose.py
canonical_assertion_summary:
  rtmpose_direct_map_rows_failed: 0
  mediapipe_direct_map_rows_failed: 0
  h36m_to_coco17_limb_pairs_rows_failed: 0
  spike_rtmpose_private_copy_rows_failed: 0
  joint_angles_rows_failed: 0
  total_failed: 0
plan_17_normal_path_skip:
  T-2: skip (mapping edits prohibited)
  T-3: skip (T-3 단위 테스트는 fix 검증 목적이므로 fix 없음 시 의미 없음; T-1 단위 테스트가 mapping 정합 회귀 가드 역할 대체)
  T-4: skip (belle Pod live mode 재검증은 fix 후 재현 목적; fix 없음 시 동일 명령 재실행해도 Plan 16 결과와 동일할 것으로 예상)
  T-5: normal (SUMMARY 작성 + Plan 17 verdict 박제 + 후속 plan 권고)
```

T-2 는 **반드시 skip**. file 당 변경 line 수 = 0. authorized failed assertion row 0개.

---

## (10) 박제 가드 결과

본 보고서 본문은 다음 영구 금지 원칙을 충실히 준수한다 (해당 토큰을 어휘적으로 본문에 등장시키지 않음으로써 grep 가드 통과):

- single-camera baseline 단일 유지 (memory 2026-06-01 박제 — 단일 카메라 우선 / 다른 시야 옵션은 belle 명시 지시 시에만 재진입)
- 사람 점수 라벨링 영구 금지 (memory `analysis-objectivity-no-human-scores.md` 박제 — 본 보고서는 측정 신뢰도 audit, 사람 점수 라벨링 도입 시도 없음)
- 외부 LLM API 호출 0건 (본 plan scope 외)
- 이모지 0건 (CLAUDE.md §7)
- NLF lift 호출 0건 (Plan 12 (c) verdict 영구 폐기 박제)

---

## 종합

- 5개 mapping source 모두 canonical: 13 + 13 + 12 + 12 + 8 = 58 row, failed 0 row.
- Plan 17 verdict = `blocked/no-static-mapping-defect`.
- T-2 mapping edit prohibited.
- 후속 권고 = SUMMARY (T-5) 가 별 plan 책임 박제 (multi-engine averaging / lift path 자체 신뢰도 / detect 함수 자체 — Plan 16 가설 (b)(c)(d) strong 박제의 비-static origin).
