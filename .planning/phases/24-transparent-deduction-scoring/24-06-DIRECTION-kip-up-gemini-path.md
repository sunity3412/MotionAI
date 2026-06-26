---
phase: 24-transparent-deduction-scoring
plan: 06 (DIRECTION — belle 방향 선택용, 미실행)
subsystem: scoring / vision-veto
tags: [kip-up, false-positive, gemini-vision, alignment-gate, non-angle-fault, collect-side-bail, objectivity]
status: DIRECTION — belle 방향 결정 대기 (코드 미수정, 진단 pod-run 1회 선행 권고)
---

# Phase 24 Plan 06 (DIRECTION): kip-up FP — Gemini 시각 경로를 어떻게 살릴까

> **상태: 방향 선택 문서. 코드 미수정.** (A) fix(24-05)로 안 풀리는 잔여 결함을 정리한다. belle 의 "정렬 게이트 vs 비-각도형 fault" 프레이밍에 옵션·트레이드오프·권고를 붙인다.

---

## 1. 문제 (한 줄)

kip-up **fault** clip 이 **100점**(위양성 — 결함을 못 잡음)으로 나온다. 결함이 **비-각도형**(관절 신전/라인 편차가 아님)이라 measured-seed 가 비어 (A) fix 로도 폴백된다. 잡으려면 **Gemini 시각 경로**가 돌아 vision-located fault 를 내야 하는데, 그게 **collect-side 에서 차단**된다.

## 2. 메커니즘 (코드 확증 — pod 불필요)

### 2-1. 차단 지점
`_collect_vision_fault_context` (`app.py:1829-1833`): alignment 채택이 `low_alignment_confidence` 면 **Gemini 호출 전 bail** → `frame_pairs=[]`, `supported_differences=[]`. Gemini 가 한 번도 안 돌아 vision-located fault 가 0 → kip-up 결함 미검출.

### 2-2. 왜 kip-up 이 low_alignment 로 떨어지나
`assess_alignment_confidence` (`vision_veto.py:751-815`) 의 발화 조건:
- `low_alignment_confidence` = **(distance>25 AND local 약함)** 또는 **(local 약함 AND visibility<0.35 AND ref-frame 부재)**
- 임계: `_ALIGN_GLOBAL_T2=25.0`(DTW distance), `_ALIGN_VIS_MIN=0.35`(keypoint 가시성), `_ALIGN_LOCAL_PATH_MIN=2`(로컬 path 대응)

kip-up = **바닥 기반 동작**(`baseline_kind="floor"`): 몸이 바닥 근처, 자기-occlusion, 빠른 모션 → RTMW keypoint 가시성/대응이 낮고, 학생↔reference DTW distance 가 크다.

### 2-3. 설계 스멜 — keypoint 게이트가 pixel-vision 경로를 막는다
`assess_alignment_confidence` 는 **RTMW keypoint 신뢰도** 게이트다. 그런데 그게 막는 건 **Gemini(픽셀 비전)** 경로다. **Gemini 는 keypoint 가 아니라 이미지를 본다** — keypoint 가 저신뢰여도 픽셀로는 비교 가능할 수 있다. 즉 게이트가 "RTMW keypoint 불안정" 을 "비교 자체 불가" 로 **혼동**해서, keypoint 가 약한 바로 그 동작(kip-up)에서 Gemini 를 꺼버린다.

추가로, **큰 DTW distance 는 두 가지를 구별 못 한다**: (a) 프레임이 어긋나 비교 불가 vs (b) 잘 보이는데 학생이 크게 틀림(= 결함 그 자체). 게이트는 큰 distance 를 (a)로 간주해 bail → **결함이 클수록 Gemini 를 더 끈다**(위음성 메커니즘).

### 2-4. 왜 이 게이트가 존재하는가 (함부로 못 푸는 이유)
D-03 객관성: **어긋난 프레임에서 Gemini 가 거짓 결함을 fabricate** 하는 걸 막으려고 pre-emptive bail 한다([[analysis-objectivity-no-human-scores]], [[vision-score-must-analyze-not-stamp]]). 그냥 임계만 낮추면 다른 동작에서 위양성(fabrication) 구멍이 열린다. 그래서 "정렬 게이트를 푼다" 가 단순 임계 완화가 되면 안 된다.

---

## 3. 모르는 것 (진단 pod-run 1회로 확정해야 — 옵션 선택의 선결 조건)

로컬 sweep 산출물은 `deductionBreakdown` + `activatedCriteria` 만 캡처했고 **visionVeto.collectionStatus / alignment 텔레메트리는 안 남겼다.** 그래서 다음을 **추정만** 했다:

| 미확정 | 왜 중요 | 확인 방법 |
|---|---|---|
| kip-up 이 정확히 어느 조건으로 low_alignment 발화하나 (distance>25? visibility<0.35? local path<2?) | 옵션 B1/B3 의 갈림 — distance 문제면 게이트 분리, visibility 문제면 Gemini 가 픽셀로 볼 수 있는지부터 | sweep 시 alignment dict(distance/visibility/localPathCount) 로깅 |
| 선택된 still-pair 에서 **Gemini 가 kip-up 결함을 실제로 짚을 수 있나** | 게이트를 열어도 Gemini 가 못 보면 무의미 (다른 fix 필요) | kip-up still-pair 에 Gemini probe 1회 (support 게이트 통과 여부) |

> **권고: 옵션 확정 전, 위 2개를 캡처하는 진단 pod-run 을 (A) 검증 sweep 에 끼워서 1회 돌린다.** (A) 재-sweep 어차피 pod 켜므로 추가 비용 ~0. 텔레메트리 로깅은 순수 코드(로컬 작성 가능).

---

## 4. 옵션 (belle 의 "정렬 게이트 vs 비-각도형 fault" 전개)

### Option B1 — 게이트 분리: still-frame *선택* 품질 ≠ Gemini *실행* 결정 [권고 후보]
alignment 게이트가 "어느 프레임을 고를까(선택 품질)" 만 결정하게 하고, **"Gemini 를 돌릴까" 는 분리**한다. low_alignment 여도 best-effort 로 frame-pair 를 고르고 Gemini 를 돌리되, **fabrication 방어는 pre-bail 이 아니라 출력단 support 게이트로 이동** — Gemini 가 캐논 FaultKey + support count + 명시 시각 증거로 확증한 difference 만 채택(이미 `assess_fault_context` 에 support 게이트 존재, `vision_veto.py` RootCauseHypothesis: "support 게이트가 drop 한 환각 difference").
- **장점:** kip-up 처럼 keypoint 약하지만 픽셀로 보이는 결함을 살림. 객관성은 support 게이트가 지킴(방어를 없애는 게 아니라 위치를 옮김).
- **위험:** support 게이트만으로 fabrication 을 충분히 막는지 = §3 두 번째 미지수. 진단 probe 로 먼저 확인.
- **scope:** `assess_alignment_confidence` 반환에 "Gemini-eligible(저신뢰 플래그 부착)" 경로 추가 + collect bail 을 "frame 못 고름" 일 때만으로 축소 + apply 단 저신뢰 verdict 라벨링.

### Option B2 — 비-각도형 fault 의 floor-baseline 측정 경로
kip-up(`baseline_kind="floor"`)의 결함을 reference-DTW 정렬 없이 **floor baseline 대비 기하**로 측정 → measured-seed 에 새 criterion(예: floor-relative 몸 라인/높이)을 추가. Gemini 없이 (A) 엔진이 granular 감점.
- **장점:** 정렬 의존 0(바닥은 절대 기준). 객관 측정이라 fabrication 위험 0.
- **위험:** kip-up 결함이 floor 기하로 환원되는지 불명(비-각도형이라 했지 floor-기하형이란 보장 없음). 새 criterion 은 IPSF 앵커 필요([[judging-baseline-ipsf-code-of-points]]) — 도메인 lookup 선행. 일반화 위험(kip-up 1개에 curve-fit 금지, [[scoring-redesign-must-generalize-no-overfit]]).
- **scope:** 큼 — 새 측정 substrate + IPSF 앵커 + dimensions 배선. (A)보다 무겁다.

### Option B3 — low_alignment 를 원인별로 분기 (distance vs visibility)
`low_alignment_confidence` 를 둘로 쪼갠다: (a) **visibility 바닥**(진짜 안 보임 — Gemini 도 픽셀 occlusion) → bail 유지 / (b) **distance 큼 + visibility OK**(잘 보이는데 발산 = 결함) → Gemini 실행. (b)만 게이트 통과.
- **장점:** B1 보다 보수적 — "안 보이는" 경우만 막고 "보이는데 틀린" 경우만 연다. 원인 기반이라 일반화 안전.
- **위험:** kip-up 이 실제로 (b)인지 = §3 첫 번째 미지수. 만약 kip-up 이 visibility 바닥(a)이면 B3 로는 안 풀리고 Gemini probe(§3-2)가 픽셀로 보는지부터 확인해야 함.
- **scope:** 중간 — `assess_alignment_confidence` 분기 1개 추가 + collect 가 (b)를 Gemini 로 라우팅.

---

## 5. 권고

**진단 우선 → B3 또는 B1, B2 는 최후.**

1. **(A) 재-sweep 에 진단 텔레메트리를 끼운다** (순수 코드, 로컬 작성): alignment dict 로깅 + kip-up still-pair Gemini probe 1회. → §3 두 미지수 확정.
2. 진단 결과로 분기:
   - kip-up 이 **distance 큼 + visibility OK** → **B3**(원인 분기, 가장 안전·최소 scope).
   - kip-up 이 **visibility 바닥 but Gemini 가 픽셀로 결함을 봄** → **B1**(선택/실행 분리 + support 게이트로 방어 이동).
   - Gemini 가 still-pair 로도 결함을 **못 봄** → B1/B3 무의미. **B2**(floor 측정) 검토하되 IPSF 앵커·일반화 게이트 선행. 그조차 안 되면 belle 도메인 판단(다각도/신기술, [[single-camera-first-multi-view-last]]).
3. 어느 경로든 **객관성 불변**: 사람 점수 라벨 0, Gemini 는 측정대상/시각증거만 짚고 fabrication 은 support 게이트가 차단. "wrong→<50" 무지성 스탬프 금지([[vision-score-must-analyze-not-stamp]]).

## 6. (A)와의 관계 / 순서

- (A)(24-05)는 **각도형** 결함의 granular 감점을 복구했다 — power-spin/peter-pan/elbow/pdshape 류. **kip-up 은 (A) scope 밖**(비-각도형)이라 의도적으로 안 건드렸다.
- (B)는 **(A) 검증 sweep 과 같은 pod-run** 에서 진단만 먼저 캡처하면 된다(추가 pod 비용 ~0). 옵션 구현은 진단 후 belle 결정.
- 따라서 **다음 pod-run 1회 = (A) 실증 검증 + (B) 진단 캡처** 를 묶는다.

---
*Phase: 24-transparent-deduction-scoring · Plan 06 DIRECTION · 2026-06-26 · 코드 미수정, belle 방향 결정 + 진단 pod-run 대기*
