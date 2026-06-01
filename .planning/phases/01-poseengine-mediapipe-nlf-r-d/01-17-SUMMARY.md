---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "17"
status: blocked_no_static_mapping_defect
subsystem: ml-pose-engine
type: fix
tags:
  - fix
  - keypoint-mapping-audit
  - lr-swap
  - rtmpose-mb
  - mediapipe-mb
  - pose-01
  - plan-16-followup
  - no-static-mapping-defect
  - hard-abort
  - no-nlf
  - single-camera-baseline
  - no-human-scoring
  - blocked_no_static_mapping_defect

dependency_graph:
  requires:
    - 01-08  # MP+MB 5영상 baseline ref-invert frame-mean 92 비교군
    - 01-11  # RTMPose+MB ref-invert frame-mean 70 비교군 (swap fix 전)
    - 01-12  # (d) keypoint chain ordering 17/17 다름 verdict
    - 01-13  # measurement_unreliable_blocked verdict
    - 01-16  # belle Pod live mode swap_ratio 1.00 dominant root cause 박제
  provides:
    - "backend/research/spikes/reports/mapping_audit_01-17.md — 5 mapping source canonical audit 박제 (58 row, failed 0)"
    - "backend/tests/test_mapping_audit.py — 21 PASS 단위 테스트 (mmpose/torch/mediapipe import 0)"
    - "blocked/no-static-mapping-defect verdict 박제 — Plan 16 swap_ratio 1.00 root cause 의 비-static origin 확정"
  affects:
    - "후속 plan — Plan 18 권고 (multi-engine averaging, Plan 16 가설 (d) cross-engine 34.57° strong 후속) 또는 lift path 자체 신뢰도 path (Plan 16 가설 (b)(c) strong 후속)"
    - "Plan 14 진입 보류 — 본 plan 의 측정 신뢰도 entry gate 가 static mapping fix 로 해소되지 않음"

tech_stack:
  added: []
  patterns:
    - "static mapping audit report-only mode — 5 mapping source canonical assertion 박제, mmpose/torch/mediapipe import 0"
    - "AST/balanced-paren source 추출 — spike_rtmpose 사본 pairs 를 모듈 import 없이 검증"
    - "hard abort branch — 5 canonical assertion 모두 PASS 시 T-2 mapping edit prohibited, T-3/T-4 skip"
    - "detect_lr_swap 재호출 (Plan 16 모듈 import only) — canonical pipeline sentinel ratio 0 박제 + intentional swap fixture detect 박제"

key_files:
  created:
    - backend/research/spikes/reports/mapping_audit_01-17.md
    - backend/tests/test_mapping_audit.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-17-SUMMARY.md
  modified: []

requirements_completed: []
# POSE-01 — 본 plan = 측정 신뢰도 audit only. static mapping defect 없음 박제 후
# blocked/no-static-mapping-defect 로 stop. 측정 신뢰도 entry gate 충족은
# 후속 plan (Plan 18 multi-engine averaging 등) 통과 후.

metrics:
  duration: "~25 min executor (T-1 audit + T-5 SUMMARY, T-2~T-4 skip)"
  completed_date: "2026-06-01"
  tasks_completed: 2   # T-1 + T-5
  tasks_total: 5       # T-1~T-5 박제 — T-2/T-3/T-4 skip per abort branch
  files_created: 3
  files_modified: 0
---

# Phase 01 Plan 17: Keypoint mapping audit — blocked/no-static-mapping-defect

**5 mapping source (rtmpose direct_map / mediapipe direct_map / 공유 H36M→COCO 12 limb pairs / spike_rtmpose 사본 12 pairs / skeleton.JOINT_ANGLES 8 entry) 모두 canonical expected tuple 과 정확 일치 — Plan 16 박제 `left_elbow_vs_right_elbow` swap_ratio 1.00 dominant root cause 는 static keypoint index mapping defect 가 아님 박제. T-2 mapping edit prohibited, T-3/T-4 skip.**

---

## (1) TL;DR

| 항목 | 값 |
|------|-----|
| verdict | `blocked/no-static-mapping-defect` (Plan 17 T-1 hard abort branch) |
| Plan 14 진입 게이트 | **보류** (PASS/PARTIAL/FAIL 어느 분기도 도달 못 함 — 본 plan 이 측정 신뢰도 entry gate 해소 책임이었으나 static mapping fix 가 정답 아님 박제) |
| 신규 파일 | 3 (audit 보고서 + 단위 테스트 + SUMMARY) |
| 변경 파일 | 0 |
| 단위 테스트 | 21 PASS, 0.15s (≥ 14 박제 통과) |
| 운영 코드 수정 | 0 줄 (functions / runpod_inference / shared/analysis / shared/judging) |
| Plan 13 모듈 수정 | 0 줄 (gemini_moment_extractor / moment_dimensions) |
| Plan 15 데이터 수정 | 0 줄 (geometric_criterion / loader / 5영상 YAML) |
| Plan 16 모듈 수정 | 0 줄 (spike_measurement_trace.py / test_spike_measurement_trace*.py) |
| 기존 spike 수정 | 0 줄 (spike_rtmpose / sweep_rtmpose / debug_dimensions / debug_gap_root_cause / spike_motionbert / spike_gemini_moment / rtmpose_to_h36m17 / mediapipe_to_h36m17) |
| NLF 호출 | 0 (Plan 12 (c) verdict 영구 폐기 박제) |
| 외부 LLM API 호출 | 0 |
| 사람 점수 라벨링 | 0 (memory `analysis-objectivity-no-human-scores.md` 박제) |
| 이모지 | 0 (CLAUDE.md §7) |
| single-camera baseline 유지 | OK (다른 시야 옵션 0건 박제) |

---

## (2) Plan 16 verdict 인용 — 본 plan dominant root cause

ref-invert 단독 belle Pod live mode (`spike_measurement_trace_live_20260601_1144`, 173 frame) verdict — Plan 17 의 fix 대상:

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

Plan 16 의 dominant 가설은 "RTMPose+MB 와 MediaPipe+MB 두 변환 path 중 한 쪽이 systematic 좌우 keypoint index swap" 이었다. 본 plan T-1 audit 의 책임 = 5 mapping source 가 canonical 인지 검증, defect 있으면 T-2 fix, 없으면 abort.

---

## (3) T-1 audit 결과 — 5 mapping source 표 + Static Mapping Verdict + T-2 Eligibility

5 표 + Static Mapping Verdict + T-2 Eligibility 전문은 `backend/research/spikes/reports/mapping_audit_01-17.md` §2-§9 박제. 요약:

| Mapping Source | Audit Rows | Failed Rows | Verdict |
|----------------|------------|-------------|---------|
| `rtmpose_to_h36m17.direct_map` (line 206-220) | 13 | 0 | canonical |
| `mediapipe_to_h36m17.direct_map` (line 184-198) | 13 | 0 | canonical |
| `mediapipe_to_h36m17.H36M_TO_COCO17_LIMB_PAIRS` (line 128-141) | 12 | 0 | canonical |
| `spike_rtmpose._h36m17_to_coco17_subset` pairs (line 398-411) | 12 | 0 | canonical |
| `skeleton.JOINT_ANGLES` (line 39-48) | 8 | 0 | canonical |
| **총계** | **58** | **0** | **canonical** |

**Static Mapping Verdict = `blocked/no-static-mapping-defect`**.

**T-2 Eligibility**:
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
  T-3: skip (T-3 단위 테스트는 fix 검증 목적; fix 없음 시 의미 없음 — T-1 audit 테스트 21 PASS 가 mapping 정합 회귀 가드 역할 대체)
  T-4: skip (belle Pod live mode 재검증은 fix 후 재현 목적; fix 없음 시 동일 명령 재실행해도 Plan 16 결과와 동일할 것)
  T-5: normal (본 SUMMARY)
```

**detect_lr_swap asymmetric sentinel 보조 박제** (audit 보고서 §8):
- canonical pipeline asymmetric sentinel (양 path 동일 semantic 입력) → swap_frame_ratio = 0.00, 4 pair 모두 0.00 (≤ 0.05 모두 PASS)
- intentional swap fixture (한 path 의 left/right elbow column 교환) → elbow pair ratio = 1.00 (DETECTED, 함수 자체 정합 확인)

**결론**: static mapping 이 canonical 인 stub fixture 에서 두 path 가 동일 좌우 부호를 출력 → detect_lr_swap = 0. 한쪽 path 에 의도적 swap 을 주입하면 detect_lr_swap = 1.0. **Plan 16 belle Pod live 173 frame 의 swap_ratio 1.00 은 static mapping defect 가 아니라 lift path 자체 (occlusion 자세에서 lifter 가 좌우를 헷갈리는 신뢰도 문제 — Plan 16 가설 (b)(c)(d) strong 박제) 의 부산물.**

---

## (4) T-2 swap fix 결과

`skipped per T-1 hard abort branch (mapping edits prohibited)`.

- 변경 파일: 0
- 변경 line: 0
- authorized failed assertion row: 0
- `git diff HEAD~1 -- backend/research/spikes/rtmpose_to_h36m17.py backend/research/spikes/mediapipe_to_h36m17.py backend/research/spikes/spike_rtmpose.py` = empty

PLAN T-2 acceptance 박제 "blocked/no-static-mapping-defect branch: mapping files 변경 0줄" 충족.

---

## (5) T-3 단위 테스트 결과

`skipped per T-1 hard abort branch (no fix to validate)`.

대신 T-1 audit 단위 테스트 21 PASS 가 mapping 정합 회귀 가드 역할 대체 (audit report `## (10)` 박제):

- TestRtmposeDirectMap (3 tests, runtime conversion 포함)
- TestMediapipeDirectMap (3 tests)
- TestSharedLimbPairs (3 tests — 공유 pairs + spike_rtmpose 사본 set equality 박제)
- TestJointAnglesSelfConsistency (4 tests — vertex/key 일치 + 좌우 일관 + 4 pair coverage + skeleton.KEYPOINT_NAMES 참조)
- TestStaticMappingAbortGate (3 tests — 5 canonical assertion + canonical pipeline swap 0 + intentional swap detect)
- TestAuditReportArtifacts (4 tests — 보고서 존재 + Static Mapping Verdict + T-2 Eligibility + 다중 시야 어휘 가드 (PLAN T-1 verify grep 패턴 0 매치))
- test_no_heavy_imports_in_this_module (1 test — mmpose/torch/mediapipe import 0)

총 21 PASS, 0.15s 실행, mmpose/torch/mediapipe import 0건. Plan 13/15/16 기존 테스트 회귀 0건.

---

## (6) T-4 belle Pod 재검증 결과

`skipped per T-1 hard abort branch (no fix to validate on Pod)`.

PLAN T-4 박제 authoritative gate 3 checks (참고용):
- (1) trace JSON `cross_engine.lr_swap.swap_frame_ratio_per_pair` 4 pair 모두 ≤ 0.05
- (2) trace JSON `cross_engine.lr_swap.swap_frame_ratio` ≤ 0.05
- (3) scoring JSON `lifter.overall` ≥ 85

본 plan 에서는 fix 가 없어 Plan 16 결과와 동일할 것으로 예상되므로 belle Pod ~5분 실행을 보존한다. authoritative gate 3 check 의 fix 후 측정값은 후속 plan 책임 박제.

진단 수치 record-only rows (Plan 16 박제 그대로 인용):
- Plan 13 frame 88 `right_shoulder` 18.2° (인체학적 비정상, target ≥ 80°): 본 plan 미해소
- cross-engine left_elbow disagreement 75.88°: 본 plan 미해소
- Plan 16 4 가설 (a) rejected / (b)(c)(d) strong: 본 plan 미해소

위 진단 수치들은 record-only — Codex Cycle 3 박제 따라 PASS/PARTIAL/FAIL 을 바꾸지 못한다. 본 plan 은 authoritative gate 3 check 어디에도 도달하지 못한 채 hard abort 한다.

---

## (7) Plan 14 진입 게이트 verdict 분기 + 후속 plan 권고

| T-4 측정 (참고용) | verdict | 후속 plan |
|-------------------|---------|-----------|
| (실행 안 됨) | **N/A — `blocked/no-static-mapping-defect`** | 후속 plan 권고 (아래) |

**Plan 14 진입 = 보류**. 본 plan 의 측정 신뢰도 entry gate 가 static mapping fix 로 해소되지 않음 박제.

**후속 plan 권고**:

1. **Plan 18 신설 (multi-engine averaging) — 권고 우선순위 1**
   - Plan 16 가설 (d) cross-engine 34.57° strong 박제 후속.
   - 두 lift path (RTMPose+MB / MediaPipe+MB) 의 frame-by-frame angle 을 가중 평균 또는 confidence-weighted 결합으로 occlusion 좌우 헷갈림 완화.
   - 본 plan 의 detect_lr_swap intentional-swap-detect 박제로 mapping 정합 회귀 가드는 이미 확보 — Plan 18 은 측정 자체의 신뢰도 합성.

2. **lift path 자체 신뢰도 path (occlusion 좌우 keypoint 신뢰도) — 권고 우선순위 2**
   - Plan 16 가설 (b)(c) strong 박제 후속 (RTMPose+MB 영상 평균 |L-R| 43.14° strong, lifter occlusion swap 0.37 strong).
   - lifter 가 거꾸로 매달림 / 측면 자세에서 좌우 keypoint 를 헷갈리는 systematic noise 원인 추적 — pre-lift 2D keypoint score / visibility filtering 또는 post-lift symmetry constraint.

3. **본 plan 재진입 — 비권고**
   - 본 plan 의 audit 가 5 mapping source 58 row 모두 canonical 박제 했으므로 재실행해도 동일 verdict. 후속은 별 plan 책임.

**single-camera baseline 유지** — 다른 시야 옵션 0건 박제 (memory 2026-06-01 박제, single-camera-first 정책 — 다중 카메라 옵션은 belle 명시 지시 시에만 재진입).

---

## (8) 핵심 결정 박제 11항목

PLAN must_haves.truths 11개 항목 본문 박제:

1. **dominant root cause 가설 검증** — Plan 16 swap_ratio 1.00 의 origin = static mapping defect 가 아님 박제. 5 mapping source 58 row 모두 canonical (audit § 2-§ 6). lift path 자체 신뢰도 (Plan 16 가설 b/c/d) 가 origin.

2. **T-1 hard abort gate 발동** — 5 canonical assertion 모두 PASS → audit verdict `blocked/no-static-mapping-defect`, T-2 mapping edit prohibited, mapping files 변경 0줄. PLAN T-1 step 6 박제 따름.

3. **변경 line 최소화 (목표 0)** — T-2 skip 으로 file 당 변경 line = 0. `git diff HEAD~1 -- (mapping files)` = empty.

4. **운영 코드 무수정** — functions/** / runpod_inference/** / shared/python/sunity_shared/analysis/** / shared/python/sunity_shared/judging/** / shared/python/sunity_shared/pose_lifters/** 0줄. dimensions.py / technique.py / FallbackRecognizer / pose_estimator.py / features.py / temporal.py / skeleton.py 무수정 박제. `git diff` empty.

5. **Plan 13 모듈 무수정** — gemini_moment_extractor.py / moment_dimensions.py / spike_gemini_moment.py 0줄. **Plan 15 데이터 무수정** — geometric_criterion.py / loader.py / 5영상 YAML 0줄. **Plan 16 모듈 무수정** — spike_measurement_trace.py / test_spike_measurement_trace*.py 0줄 (T-1 단위 테스트가 detect_lr_swap import only). **다른 기존 spike 무수정** — spike_rtmpose / sweep_rtmpose / debug_dimensions / debug_gap_root_cause / spike_motionbert 0줄. `git diff` empty.

6. **NLF 호출 0** — Plan 12 (c) verdict 영구 폐기 박제 (memory `license-blocklist-pose.md`). 본 plan audit + 단위 테스트 NLF lift 호출 0건.

7. **8 angle joints 한정 박제** — skeleton.JOINT_KEYS = left/right × elbow/shoulder/hip/knee 8 joint 만 검증. 파생 joint (hip center / spine / thorax / neck_nose / head) 매핑 수정 0줄. Plan 16 LR_PAIRS 4 tuple 정합 유지 (audit 보고서 §6).

8. **single-camera baseline 영구 유지** — memory 2026-06-01 박제, 다른 시야 옵션은 belle 명시 지시 시에만 재진입. 본 plan 코드 / 권고 / 분기 / 문서 / 테스트 / audit 보고서 / 본 SUMMARY 어디에도 해당 어휘 0건 (검증: PLAN T-1 verify 자동화 명령의 grep 정규식 본문 0 매치 — 정규식 자체는 본 SUMMARY 에 어휘적으로 등장하지 않음).

9. **외부 LLM API 호출 0건 + 사람 점수 라벨링 0건** — 본 plan 은 측정 path audit 자체. 외부 LLM moment 추출 / 외부 LLM frame 정확도 검증 호출 0건. 사람 점수 라벨링 0건 (memory `analysis-objectivity-no-human-scores.md` 영구 금지 박제).

10. **Plan 16 swap detection 함수 재사용 박제** — T-1 단위 테스트 `TestStaticMappingAbortGate::test_canonical_pipeline_asymmetric_sentinel_swap_zero` + `test_intentional_swap_fixture_detected` 가 `detect_lr_swap` 함수 import only, 무수정 박제. Plan 16 모듈 시그너처 의존만, 호출 only.

11. **belle 박제 정합** — "고객은 결과만 본다" + "분석 정확도 최우선" + "정은지 = 폴스포츠 세계챔피언이므로 IPSF minimum 못 가는 자세 불가능" 일관 — 본 plan abort 결과는 후속 plan (multi-engine averaging) 책임으로 ref-invert overall 90+ 회복 가능성을 이관. 본 plan 자체는 측정 신뢰도 audit 책임만 완료.

---

## (9) Deviations from Plan

`None - plan 의 T-1 hard abort branch 박제 그대로 따름` + 작은 보고서 textual variation:

- **(d1) audit 보고서 §(10) 가드 박제 표현 우회** — PLAN T-1 step 9 (10) 박제는 PLAN T-1 verify 자동화 명령의 grep 정규식과 동일한 어휘 토큰을 메타-라벨로 표시하는 0건 확인 표를 명시한다. 이 표를 그대로 작성하면 해당 토큰이 grep 가드에 매치되어 self-defeating 이 된다. 따라서 보고서 §(10) 을 affirmative-only 박제 (single-camera baseline 유지 + memory filename 직접 인용 회피) 로 표현해 grep 가드를 통과한다. PLAN 의 의도 (해당 토큰이 본문에 등장하지 않음) 와 일치하며, 표 형식만 변경한다.

- **(d2) T-1 단위 테스트 14 → 21 PASS** — PLAN 박제 ≥ 14, 실제 21 (auditing 5 source × 다양한 assertion 패턴 + audit report 산출물 박제 4 + heavy import 가드 1). PLAN 박제 acceptance criteria 가 ≥ 14 이므로 통과.

기타 deviation 없음.

---

## (10) Known Stubs

`None`.

본 plan 은 측정 path audit only. UI / 데이터 흐름 stub 없음.

---

## (11) Threat Flags

`None`.

본 plan 의 audit 보고서 / 단위 테스트 / SUMMARY 모두 측정 신뢰도 audit 책임 한정. 새 trust boundary / 새 network endpoint / 새 auth path 도입 0건.

---

## (12) Self-Check

| 항목 | 검증 명령 | 결과 |
|------|-----------|------|
| audit 보고서 존재 | `test -s backend/research/spikes/reports/mapping_audit_01-17.md` | PASS |
| Static Mapping Verdict 섹션 | `grep -q '^## (7) Static Mapping Verdict' (위 path)` | PASS |
| T-2 Eligibility 섹션 | `grep -q '^## (9) T-2 Eligibility' (위 path)` | PASS |
| 단위 테스트 PASS | `pytest backend/tests/test_mapping_audit.py -v` | 21 PASS, 0.15s |
| audit 보고서 다중 시야 어휘 가드 (본문) | PLAN T-1 verify grep 정규식 | 0 matches |
| 본 SUMMARY 다중 시야 어휘 가드 (본문) | PLAN T-5 verify grep 정규식 | 0 matches (아래 자동 검증) |
| 운영 코드 무수정 | `git diff HEAD~1 -- backend/functions/ backend/runpod_inference/ backend/shared/` | empty |
| Plan 13/15/16 모듈 무수정 | `git diff HEAD~1 -- backend/research/spikes/spike_measurement_trace.py backend/research/spikes/spike_gemini_moment.py backend/shared/python/sunity_shared/judging/` | empty |
| 다른 기존 spike 무수정 | `git diff HEAD~1 -- backend/research/spikes/spike_rtmpose.py spike_motionbert.py sweep_rtmpose.py debug_*.py rtmpose_to_h36m17.py mediapipe_to_h36m17.py` | empty |
| mmpose/torch/mediapipe import 0 (단위 테스트) | `grep -E '^import (torch|mmpose|mediapipe)' backend/tests/test_mapping_audit.py` | 0 matches |
| 변경 파일 (신규) | 3 (audit 보고서 + 단위 테스트 + 본 SUMMARY) | OK |
| 변경 파일 (수정) | 0 | OK |

## Self-Check: PASSED

---

## (13) Verdict 요약 (orchestrator 에게)

- **verdict**: `blocked/no-static-mapping-defect`
- **one-liner**: "Plan 16 swap_ratio 1.00 dominant root cause 는 static keypoint mapping defect 가 아님 박제 (5 source 58 row canonical) — T-2 mapping edit prohibited, Plan 18 multi-engine averaging 후속 권고"
- **commits**: T-1 audit `d63f7f6`, T-5 SUMMARY (본 commit, hash 별도)
- **next action**: orchestrator 가 STATE.md + ROADMAP.md 갱신. Plan 14 진입 보류. `/gsd:plan-phase 1 --plan 18` (multi-engine averaging) 권고 — 또는 lift path 자체 신뢰도 path 권고 우선순위 2.
- **single-camera baseline**: 유지 (memory 2026-06-01 박제).

---

*Phase: 01-poseengine-mediapipe-nlf-r-d*
*Completed: 2026-06-01*
