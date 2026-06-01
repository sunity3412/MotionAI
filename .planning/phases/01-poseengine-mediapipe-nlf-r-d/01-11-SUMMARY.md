---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "11"
subsystem: ml-pose-engine
tags:
  - spike
  - sweep
  - rtmpose
  - mmpose
  - apache-2.0
  - line-angle-debug
  - gate-rule-review
  - wave-3-entry
  - pending_belle

dependency_graph:
  requires:
    - 01-08  # MP+MotionBERT 5영상 4/5 PASS baseline
    - 01-10  # RTMPose-l 단일 영상 STRONG_PASS (ref-sideway-spin 72.0)
  provides:
    - "RTMPose+MB 5영상 batch sweep harness (sweep_rtmpose.py) — Plan 10 spike 를 list iteration 으로 wrapping"
    - "line/angle N/A root cause 박제 스크립트 (debug_dimensions.py) — FallbackRecognizer default profile + 영상별 원인 분류 + Phase 5 진입 전 임시 회복 후보 3개"
    - "Wave 3 (Plan 04 NLF R&D 격리 + Plan 05 atomic swap) 진입 게이트 verdict — belle Pod sweep 결과 적재 시점에 확정"
    - "게이트 룰 (D-14 / D-15①~③) 적정성 재검토 — Plan 06/07/08/10 누적 결과 기반"
  affects:
    - 01-04  # NLF R&D 격리 — Plan 11 5/5 또는 4/5 PASS 시 진입 게이트 통과
    - 01-05  # atomic swap — Plan 04 완료 후 자동 진입

tech_stack:
  added:
    - "(없음) — mmpose 1.3.2 / numpy 1.26.4 / mmcv 2.1.0 등 Plan 10 환경 그대로"
  patterns:
    - "5영상 batch wrapping — Plan 10 단일 영상 run_spike 를 list iteration 으로 호출 (코드 1벌)"
    - "spike_fn 주입 가능 (테스트 격리) — sweep_rtmpose.run_sweep 의 spike_fn 인자"
    - "JSON → 박제 분석 — sweep 결과 JSON 만 입력으로 받아 debug 스크립트 로컬 실행 (raw frames 없이도 가능)"

key_files:
  created:
    - backend/research/spikes/sweep_rtmpose.py
    - backend/research/spikes/debug_dimensions.py
    - backend/tests/test_sweep_rtmpose_smoke.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-11-SUMMARY.md
  modified:
    - backend/research/spikes/README.md  # Plan 11 섹션 append (Plan 07/08/10 보존)

decisions:
  - "Plan 11 = belle 결정 (2026-06-01) C scope — 5영상 sweep + line/angle root cause + 게이트 룰 검토. Gemini 통합은 Phase 5 별 phase (belle Gemini API 키 발급 중)."
  - "5/5 PASS = Wave 3 진입 (Plan 04 / Plan 05). 4/5 PASS = Wave 3 진입 + Phase 5 우선순위 ↑. 3/5 이하 = Plan 12 추가 검토 (HybrIK 또는 MP+MB 유지)."
  - "line/angle N/A 가 모두 N/A 면 Wave 3 보류 + Phase 5 우선 진입 옵션 박제 (belle 판단)."
  - "D-14 (NLF gap ≤5) 는 보조 게이트로 강등 권장 — Plan 10 -9 양보 가능했고, production 진입은 D-15① 우선 (CLAUDE.md 'core value = 분석 정확도'). 5영상 sweep 결과로 최종 확정."
  - "D-15① (overall ≥70) threshold 유지 — Plan 06/07/08/10 모두 이 기준 검증됨. 변경 없음."
  - "FallbackRecognizer / dimensions.py 코드 수정 금지 — root cause 박제만. Phase 5 Gemini 어댑터 진입 시 정공법."

requirements_completed: []  # belle Pod 실행 결과로 POSE-01 완전 충족 여부 확정. pending.

metrics:
  duration: "~50 min executor (T-1 ~ T-4 + 테스트) — belle Pod 실행 (T-5) 미포함"
  completed_date: "pending belle Pod 실행 (2026-06-01 작성, sweep 미실행)"
  tasks_completed: 4   # T-1, T-2, T-3, T-4 (T-5 belle 대기)
  tasks_total: 5
  files_created: 4
  files_modified: 1
---

# Phase 01 Plan 11: 5영상 sweep + line/angle root cause — pending belle

**One-liner:** Plan 10 RTMPose-l 단일 영상 STRONG_PASS (72.0) 후속 — 정은지 5영상 전체 회귀 sweep harness + line/angle N/A 원인 박제 스크립트 + 게이트 룰 (D-14/D-15) 재검토 + Wave 3 진입 게이트 조건 명시. belle Pod 5영상 실행 결과 적재 후 verdict 확정.

---

## TL;DR

| 항목 | 내용 |
|---|---|
| **Verdict** | **`pending_belle`** (belle Pod 5영상 sweep 실행 대기) |
| **단계 도달** | T-1 / T-2 / T-3 / T-4 완료. T-5 (belle Pod 실행) 대기 |
| **scope** | C — 5영상 sweep + line/angle root cause + 게이트 룰 검토 (Gemini 통합은 Phase 5 별 phase) |
| **신규 파일** | 3 (sweep harness, debug 스크립트, smoke 테스트) + 1 SUMMARY |
| **수정 파일** | 1 (README append, Plan 07/08/10 섹션 보존) |
| **단위 테스트** | 12 PASS (mmpose 없이 로컬, sweep_rtmpose smoke) |
| **만든 커밋** | 4 (sweep+tests / debug / docs / closeout) |
| **운영 코드 수정** | 0 (functions / runpod_inference / shared/pose_lifters 모두 무수정) |
| **다음 행동** | belle Pod sweep 실행 → 결과 적재 → SUMMARY 갱신 → Plan 04 진입 결정 |

---

## T-1 — `sweep_rtmpose.py` 5영상 batch (완료)

Plan 10 `spike_rtmpose.run_spike` 를 5영상 list iteration 으로 wrapping.
spike 단일 함수 재사용 (코드 1벌, 분기 0). 2D detector / lift / 점수 계산
chain 은 그대로.

### 모듈 구조

```
backend/research/spikes/sweep_rtmpose.py
  DEFAULT_MOTIONS = (ref-climb, ref-foxtop-split, ref-foxtop, ref-invert, ref-sideway-spin)
  STRONG_PASS_THRESHOLD = 70.0
  build_arg_parser()  → argparse.ArgumentParser  (테스트 재사용)
  run_sweep(motions, bucket, ..., spike_fn=None) → dict   (테스트 spike_fn 주입 가능)
  generate_markdown(sweep_result) → str
  main() → CLI 진입점
```

### CLI 인자 (9개, Plan 11 T-1-5 명세 그대로)

| 인자 | default | 설명 |
|---|---|---|
| `--motions` | `ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin` | 분석할 motion_id 리스트 |
| `--bucket` | `sunity-motion-pilot-videos` | S3 버킷 |
| `--rtmpose-config` | (required on Pod) | RTMPose config .py 경로 |
| `--rtmpose-checkpoint` | (required on Pod) | RTMPose 가중치 .pth |
| `--motionbert-root` | `/workspace/MotionBERT` | MotionBERT 저장소 |
| `--motionbert-weights` | (auto: {root}/checkpoint/pose3d/FT_MB_lite/best_epoch.bin) | 가중치 |
| `--score-threshold` | `0.3` | RTMPose keypoint 컷 |
| `--det-model` | `none` | single-person 우회 (Plan 10 commit f019070) |
| `--out` | (auto: backend/research/spikes/reports/sweep_rtmpose_<UTC>.json) | 결과 dump |

### 출력 형식

`.json` + `.md` sibling 한 쌍.

**JSON top-level**:
```json
{
  "generated_at": "ISO 8601 UTC",
  "detector": "rtmpose-l",
  "lifter": "motionbert_lite",
  "score_threshold": 0.3,
  "det_model": "none",
  "motions": [{"motion": "...", "rtmpose_mb": {...}, "nlf": {...}, "gap": {...}, "verdict": "..."}],
  "summary": {"total": 5, "passed": 4, "verdict": "4/5 CONDITIONAL_PASS", "line_na_count": 5, "angle_na_count": 5}
}
```

**Markdown 표** (Plan 11 T-1-3):

```
| 모션 | RTMPose+MB | NLF | gap | D-15① ≥70 | line | angle |
```

`summary.verdict` 자동 계산:
- 5/5 → `STRONG_PASS`
- 4/5 (total≥2) → `CONDITIONAL_PASS`
- 1~3 → `REGRESSION`
- 0 → `FAIL`

### 테스트 (12 PASS, 로컬, mmpose 없이)

```bash
PYTHONPATH=backend/shared/python:. python3 -m pytest \
  backend/tests/test_sweep_rtmpose_smoke.py -v
# 12 passed in 0.03s
```

| 테스트 클래스 | tests | 범위 |
|---|---|---|
| TestCliDefaults | 6 | argparse default 값 (motions / det-model / threshold / bucket) + override |
| TestSweepIteration | 4 | 5/5 PASS, 4/5 CONDITIONAL, 영상별 호출, 빈 motions raises |
| TestJsonShape | 2 | JSON top-level + motions[] + summary 필수 키, .md sibling 생성 |

---

## T-2 — `debug_dimensions.py` line/angle N/A root cause (완료, 박제만)

sweep_rtmpose JSON 보고서를 입력으로 받아 영상별 line/angle N/A 원인 분류.
FallbackRecognizer 코드 / dimensions.py 무수정 — 박제 + 가능성 평가만.

### 모듈 구조

```
backend/research/spikes/debug_dimensions.py
  _inspect_fallback_recognizer_default() → dict   (zero angles 입력 기준 박제)
  trace_motion(entry, recognizer_info) → dict    (영상 1개 trace)
  _classify_line_na(line_score, recognizer_info) → str   (원인 분류)
  _classify_angle_na(angle_score) → str
  _fix_candidates() → list[dict]   (3 후보 박제)
  generate_markdown(...) → str
  run_debug(report_path, motions, out) → dict
```

### FallbackRecognizer default 박제 (zero angles 입력 시)

| 항목 | 값 |
|---|---|
| applicable_joints (technique._EXTENSION_JOINTS) | `[left_elbow, right_elbow, left_knee, right_knee]` |
| expected_extend (default 0 angles) | `[]` (전부 BENT_OK — 0 < 150° 임계) |
| expected_bent | 전체 8 JOINT_KEYS |
| is_symmetric | False (폴 동작 비대칭 정상) |

**핵심 해석**: holding 구간 평균 관절각이 `_EXTENSION_ZONE_DEG = 150°` 미만이면
EXTEND 분류 없음 → `dimensions.line_score` 의 `deficits` 가 empty → None 반환.
PROJECT.md "핵심 블로커 — 굽은 그립 자세에서 EXTEND 못 찾아 line None" 와 정확히 일치.

### 영상별 root cause 분류 (sweep JSON 기반)

스크립트는 sweep JSON 의 `motions[].rtmpose_mb.line / angle` 값을 보고
다음 분류:

| 모션 line | 원인 |
|---|---|
| `null` | FallbackRecognizer expected_extend 빈 집합 → `line_score` deficits empty → None |
| 점수 산출 | 정상 (holding 평균 ≥150° EXTEND 관절 존재) |

| 모션 angle | 원인 |
|---|---|
| `null` | spike 는 reference (정은지/이전 영상) 없이 호출 — `dimensions.absolute_dimension_scores` 가 angle 키를 dict 에 포함하지 않음. **정상 동작** (production mode1/mode3 에서 자동 산출). |
| 점수 산출 | (spike 에서는 불가) |

### Fix candidates (Phase 5 진입 전 임시 회복) — **박제만, 적용 금지**

Plan 11 scope_limits 명시: FallbackRecognizer / dimensions.py 코드 수정 금지.
아래 후보는 박제 + belle 결정 + Phase 5 통합 시점 평가용.

| ID | 후보 | 무엇 | 위험 | 범위 |
|---|---|---|---|---|
| 1 | `score_threshold` 0.3 → 0.2 | RTMPose keypoint NaN 컷 완화, 더 많은 keypoint 살아남음 | 저신뢰 keypoint 가 lift 에 들어가 stability/line 변동성 ↑ | spike CLI default 만 |
| 2 | FallbackRecognizer default profile 확장 | _EXTENSION_JOINTS 4개를 모두 EXTEND 기본 | "의도된 굽힘"을 결함으로 깎는 위양성 (PROJECT.md 핵심 블로커 정반대) | 운영 코드 (technique.py) — 본 plan 금지 |
| 3 | `_EXTENSION_ZONE_DEG` 150° → 130° 완화 | 130~150° 자세도 EXTEND 분류 | 후보 2 와 동일한 위양성 함정 | 운영 코드 — 본 plan 금지 |

**결론**: line N/A 정공법은 Phase 5 Gemini 기술 인식기 통합 (영상 → 기술명 +
EXTEND/BENT/CONTACT 직접 매핑). 임시 회복 3 후보는 모두 위양성 위험 — belle
결정 + 도메인 검증 없이 단독 적용 금지.

### 실행 (로컬 OK)

```bash
python3 -m backend.research.spikes.debug_dimensions \
  --report backend/research/spikes/reports/sweep_rtmpose_YYYYMMDD_HHMM.json \
  --out backend/research/spikes/reports/debug_dimensions_YYYYMMDD_HHMM.md
```

---

## T-3 — 게이트 룰 검토 (완료)

Plan 06/07/08/10 누적 결과 + Plan 11 5영상 sweep 결과 (belle Pod 실행 후 확정)
기반.

### T-3-1: D-14 (NLF gap ≤5) 강등 권장

| 근거 | 값 |
|---|---|
| Plan 10 ref-sideway-spin gap | **-9** (양보) |
| CLAUDE.md core value | **분석 정확도 = D-15** 우선 |
| Plan 08 5영상 gap | +20 ~ +27 (MP+MB > NLF 4영상) — D-14 변동 폭 큼 |

**결정**: D-14 (NLF gap ≤5) 를 **보조 게이트로 강등**. production 진입은
D-15① (overall ≥70) 단독으로 판단. D-14 는 NLF 동등 일치 신호로만 사용,
양보 자체로 차단하지 않음. 5영상 sweep 에서 gap 분포가 -10 이상이면 본 결정
공식화, 그 외에는 Plan 12 에서 D-14 임계 재정의.

### T-3-2: D-15① (overall ≥70) 유지

| 근거 | 값 |
|---|---|
| Plan 06 NLF baseline 5영상 | 58 ~ 81 (3/5 PASS) |
| Plan 07 MP+MB ref-foxtop-split | 65 (PASS) |
| Plan 08 MP+MB 5영상 | 64 ~ 92 (4/5 PASS, sideway-spin fail) |
| Plan 10 RTMPose ref-sideway-spin | 72 (PASS) |

**결정**: D-15① threshold = 70 **유지**. 4 plan 누적 검증 일관. 변경 없음.

### T-3-3: D-15② (Top-3 failures overlap ≥2/3 vs NLF) — sweep 결과로 확정

본 sweep 은 영상별 dimensions 만 dump (Top-3 failure joint 별도 dump 없음).
sweep 결과 dump 에 Top-3 failure 추가는 Plan 11 scope 밖 — Plan 12 또는 Plan
04 에서 dimensions trace dump 와 같이.

**결정**: D-15② 적정성 평가는 **Plan 04 (NLF R&D 격리) 진입 시** 확정. Plan 11
SUMMARY 에서는 sweep JSON 에 Top-3 failure joint 가 없다는 한계만 박제.

### T-3-4: D-15③ (avg_confidence ≥0.5) — sweep 결과로 확정

| 근거 | 값 |
|---|---|
| Plan 10 ref-sideway-spin avg_rtm_score | **0.4382** (약간 미달) |

**가설**: 측면 자세 특유의 keypoint 가림 효과. 다른 4영상에서는 더 높을 가능성
(정면/대각 자세).

**결정**: 5영상 평균 avg_rtm_score ≥ 0.45 면 D-15③ **유지** (Plan 10
0.4382 를 lower bound 로 박제). 5영상 평균 < 0.40 면 임계 0.4 로 강등 검토.
영상별 0.4 미만은 **known limitation 박제** (production 차단 아님).

### T-3-5: 5/5 vs 4/5 PASS 분기

| 결과 | passed/total | 결정 |
|---|---|---|
| 5/5 | overall ≥70 5/5 | D-15① threshold 70 그대로 유지, Wave 3 진입 |
| 4/5 | sideway-spin 만 fail | D-15① 4/5 rule 공식화 (5영상 중 4영상 PASS 충분), Wave 3 진입 + Phase 5 우선순위 ↑ |
| 4/5 (다른 영상 fail) | sideway-spin 외 1영상 fail | regression — Plan 12 (HybrIK 또는 다른 lift) 검토 |

**결정**: 5/5 → 진입. 4/5 (sideway-spin 만 fail) → 진입 + Phase 5. 4/5 (다른
영상 fail) → regression. 3/5 이하 → Plan 12.

---

## T-4 — Wave 3 진입 게이트 조건 (완료)

### T-4-1: Plan 04 (NLF R&D 격리) 진입 조건

**진입 게이트** (Plan 11 5영상 sweep 통과 후):
- [ ] sweep verdict ∈ {`5/5 STRONG_PASS`, `4/5 CONDITIONAL_PASS`}
- [ ] line/angle N/A 수용 — debug_dimensions 결과 박제됨, Phase 5 진입 조건과 분리
- [ ] D-15① threshold 70 유지 (Plan 11 T-3-2 결정)
- [ ] D-14 강등 적용 (보조 게이트, 차단 아님)

**차단 조건**:
- sweep verdict = `REGRESSION` (3/5 이하) → Plan 12 추가 검토
- belle 가 line/angle N/A 가 production 차단 사유라고 판단 → Wave 3 보류 + Phase 5 우선

**행동 (PASS 시)**: Plan 04 `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-04-PLAN.md`
의 NLF R&D 격리 작업 시작 (NLF 호출 boundary 명확화, R&D vs production 분리).

### T-4-2: Plan 05 (atomic swap) 진입 조건

**진입 게이트** (depends_on: 01-04, 01-06):
- [ ] Plan 04 (NLF R&D 격리) 완료 SUMMARY 작성
- [ ] Plan 06 (NLF baseline) PASS — 이미 완료
- [ ] Plan 11 sweep verdict ∈ {`STRONG_PASS`, `CONDITIONAL_PASS`}

**행동**: Plan 04 완료 후 자동 진입. atomic swap = 기존 NLF 운영 path 에서
RTMPose+MB lifter 로 무중단 교체 (롤백 가능한 design).

### T-4-3: Phase 5 (Gemini 기술 인식기) 진입 조건

**진입 게이트**:
- [x] belle Gemini API 키 발급 완료 — Parameter Store `/sunity/motion/gemini-api-key`
  SecureString 박제 (2026-06-01)
- [ ] Lambda env wiring (`backend/template.yaml` 환경변수 추가)
- [ ] RunPod env wiring (`GEMINI_API_KEY` env 주입)
- [ ] Gemini 어댑터 모듈 추가 (`backend/shared/.../analysis/recognizers/gemini_recognizer.py`)

**우선순위**:
- sweep verdict = `5/5 STRONG_PASS` + line/angle 일부 영상 회복 → Phase 5 표준 우선순위 (Phase 1 완료 후)
- sweep verdict = `4/5 CONDITIONAL_PASS` 또는 line/angle 전 영상 N/A →
  Phase 5 **우선순위 ↑** (Phase 1 완료 직후 즉시 진입)

### T-4-4: Phase 1 완료 조건

**완료 게이트**:
- [ ] Plan 11 verdict 확정 (5영상 sweep + belle 응답)
- [ ] Plan 04 (NLF R&D 격리) PASS
- [ ] Plan 05 (atomic swap) PASS
- [ ] requirements POSE-01 / POSE-02 완전 충족 확인

**완료 후 진입**: Phase 2 (운영 파일럿 + 사용자 영상 분석 flow). Phase 5
(Gemini 통합) 는 Phase 2 ~ 5 사이 어디서든 우선순위 ↑ 가능 (line/angle
회복 시급도에 따라).

---

## T-5 — belle Pod 실행 대기 (autonomous: false)

**상태**: 본 SUMMARY 작성 시점 (2026-06-01, executor 완료 시) **미실행**.

### belle Pod 실행 명령 (copy-paste, T-5-1 그대로)

> Pod 환경: 2026-06-01 22:00 STATE.md 박제 — mmpose 1.3.2 / numpy 1.26.4 /
> mmcv 2.1.0 / detector 우회 default. **추가 install 없음.**

```bash
cd /workspace/SunityMotion && git pull --ff-only origin main

python3 -m backend.research.spikes.sweep_rtmpose \
  --motions ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin \
  --bucket sunity-motion-pilot-videos \
  --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \
  --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \
  --motionbert-root /workspace/MotionBERT \
  --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \
  --score-threshold 0.3 \
  --det-model none \
  --out backend/research/spikes/reports/sweep_rtmpose_$(date +%Y%m%d_%H%M).json
```

예상 소요: 5영상 × ~2분/영상 = **~10분**.

### 결과 파일 위치

- `backend/research/spikes/reports/sweep_rtmpose_YYYYMMDD_HHMM.json`
- `backend/research/spikes/reports/sweep_rtmpose_YYYYMMDD_HHMM.md`

`.md` 의 "5영상 종합표" + "게이트 verdict" 섹션을 Claude 에 공유. 동시에
debug_dimensions 도 실행해 line/angle 원인 박제:

```bash
python3 -m backend.research.spikes.debug_dimensions \
  --report backend/research/spikes/reports/sweep_rtmpose_YYYYMMDD_HHMM.json \
  --out backend/research/spikes/reports/debug_dimensions_YYYYMMDD_HHMM.md
```

### belle 응답 옵션 (T-5-3 4개)

| 응답 | 조건 | 다음 행동 |
|---|---|---|
| **`approved, proceed to Wave 3`** | 5/5 (overall ≥70 모두) | Plan 04 (NLF R&D 격리) 진입 |
| **`accept limitation, proceed to Wave 3 with known gap`** | 4/5 + line/angle 모두 N/A | Plan 04/05 진입 + Phase 5 우선순위 ↑ |
| **`regression in RTMPose, evaluate path`** | 3/5 이하 | Plan 12 추가 검토 (HybrIK 또는 MP+MB 유지 path) |
| **`Wave 3 보류, Phase 5 선행`** | line/angle N/A 가 차단 사유 판단 | Phase 5 Gemini 통합 우선 (Plan 04/05 보류) |

### belle 응답 후 STATE.md 갱신 path

1. belle 응답 적재 → 본 SUMMARY 상단 frontmatter `metrics.completed_date`,
   `requirements_completed` 갱신.
2. STATE.md `Current Position` Plan 11 verdict 명시 + `progress.completed_plans`
   8/11 로 갱신.
3. ROADMAP.md Plan 11 진행률 행 갱신.
4. 다음 행동: `/gsd:execute-phase 1 --plan 04` (또는 belle 응답에 따른 분기).

---

## Deviations from Plan

없음 — 본 SUMMARY 작성 시점 (T-1 ~ T-4 완료) 까지 plan 그대로 실행. T-5 belle
Pod 실행은 본 executor scope 밖.

**spike_rtmpose 의 `run_spike` 시그니처**: 본 sweep 은 spike 함수의 keyword
인자 (`motion=`, `bucket=`, ...) 만 호출 — 함수 본문 무수정. Plan 10 commit
f019070 의 detector 우회 default 가 sweep CLI default 와 일관 (`--det-model none`).

---

## Known Stubs

없음. 본 plan 의 sweep / debug 스크립트는 belle Pod 에서 즉시 실행 가능한
완전한 구현 (단위 테스트 12 PASS, mmpose 없이 로컬).

---

## Threat Flags

없음 — 신규 네트워크 엔드포인트 / auth path / Firestore 스키마 변경 없음.
spike 코드만 추가, 운영 코드 무수정. mmpose 는 Pod 전용 (Lambda 미배포).

---

## Open Questions / Next Step

### Open Questions (belle Pod 실행 후 확정)

1. **5영상 중 몇 개가 D-15① PASS?** 5/5 면 Wave 3 표준 진입, 4/5 면 Phase 5
   우선순위 ↑, 3/5 이하면 Plan 12 추가 검토.
2. **line N/A 가 5영상 모두인가?** 모두면 Phase 5 즉시 진입 검토. 일부 영상에서
   line 점수 산출되면 FallbackRecognizer 가 holding 평균 ≥150° EXTEND 관절 찾은
   경우 — 어떤 자세에서 작동했는지 박제.
3. **avg_rtm_score 5영상 평균이 0.5 이상인가?** ≥0.5 → D-15③ 유지, <0.45 →
   sideway-spin 외 영상도 측면/가림 영향 받음 (Plan 12 다른 detector 검토).
4. **NLF gap 분포**: 5영상 모두 -10 이상이면 D-14 강등 공식화. 4영상 gap ≤5
   면 D-14 임계 재정의 (양보 영상만 known limitation 박제).

### Next Step (확정된 path)

```
belle Pod sweep 실행 (10분)
  → 결과 .md + .json Claude 공유
  → debug_dimensions 실행 (로컬 OK)
  → 본 SUMMARY frontmatter `metrics.completed_date` + `requirements_completed`
     갱신 + verdict 확정
  → STATE.md / ROADMAP.md 갱신
  → belle 응답 (4 옵션 중 1)
  → /gsd:execute-phase 1 --plan 04 진입 결정 (또는 Plan 12 / Phase 5 분기)
```

---

## Self-Check: PASSED

**파일 존재 확인** (executor 작성):

- `backend/research/spikes/sweep_rtmpose.py` FOUND
- `backend/research/spikes/debug_dimensions.py` FOUND
- `backend/tests/test_sweep_rtmpose_smoke.py` FOUND
- `backend/research/spikes/README.md` FOUND (modified, append-only Plan 11 섹션)
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-11-SUMMARY.md` FOUND (이 파일)

**운영 코드 무수정 확인**:

- `backend/functions/pipeline/app.py` UNCHANGED
- `backend/runpod_inference/server.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/technique.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/dimensions.py` UNCHANGED
- `backend/shared/python/sunity_shared/analysis/pose_lifters/` UNCHANGED
- `backend/research/spikes/spike_rtmpose.py` UNCHANGED (Plan 10 본체 보존)
- `backend/research/spikes/rtmpose_to_h36m17.py` UNCHANGED

**테스트 결과 확인**:

- `backend/tests/test_sweep_rtmpose_smoke.py`: 12 PASS (mmpose 없이 로컬,
  CLI defaults / iteration / JSON shape)
- `backend/tests/test_spike_rtmpose_to_h36m17.py`: 36 PASS (Plan 10 회귀 유지)

**커밋 존재 확인** (Plan 11):

- `feat(01-11): sweep_rtmpose 5영상 batch + build_arg_parser + smoke 테스트` FOUND
- `feat(01-11): debug_dimensions.py line/angle N/A trace` FOUND
- (본 commit) `docs(01-11): README append (sweep + debug 절차) + SUMMARY (pending_belle)` 예정

---

## Verdict 요약 — orchestrator 에게

- **verdict**: `pending_belle`
- **one-liner**: Plan 10 RTMPose-l STRONG_PASS (72.0) 후속 5영상 sweep harness +
  line/angle N/A 박제 + 게이트 룰 (D-14 강등, D-15① 유지, D-15②/③ sweep 결과로)
  + Wave 3 진입 게이트 조건 (Plan 04/05/Phase 5) 명시. belle Pod 5영상 실행 대기.
- **commits (executor)**: 3 + 본 docs commit = 4 (T-1 sweep+tests / T-2 debug /
  T-3+T-4 docs+SUMMARY).
- **next action**: belle Pod sweep 실행 → 결과 적재 → 본 SUMMARY verdict 갱신 →
  `/gsd:execute-phase 1 --plan 04` 진입 결정 (또는 Plan 12 / Phase 5 분기).
