# RTMW 3D Path 결정 (D-18)

> Plan 01-22 Task 1 산출. Task 2 belle checkpoint 응답 후 §5 갱신.
>
> 본 문서는 단일 카메라 (폰) 환경에서 RTMW 운영 백본 위에 z 좌표를 산출하는
> 방법을 결정한다. Pose2Sim (멀티 카메라) 는 본 plan scope 외 — Phase 4
> (다중 시점) 에서 통합. memory `single-camera-first-multi-view-last` 정합.

---

## 1. 배경

Plan 01-19 ~ 01-21 박제 RTMW pivot:

- D-17: 운영 백본 = rtmlib RTMW 133 wholebody (Apache-2.0). MediaPipe + MotionBERT
  운영 path 는 R&D 격리 대상 (plan 24).
- D-20: 원본 보존 = RTMW 133, 스코어링 계약 = COCO-17 + 폴 확장. Plan 21 의
  `RTMW133ToCOCO17Adapter` 가 변환 담당.
- D-21: `PoseFrame.body_shape` 는 RTMW path 에서 None (SMPL-X β 없음).
- D-25: `weights_manifest.json` `production_eligible=true` 가중치만 로드.

Plan 21 의 `RTMWPoseEngine` 은 2D 키포인트 (xy + score) 만 산출한다. 다운스트림
분석 레이어 (`features.py`, `temporal.py`, `kismam.py`, `dimensions.py`) 는 3D
각도 계산을 요구한다 (`features.compute_joint_angles` 가 3D vector 의 dot/cross
사용). 따라서 RTMW pivot 의 v1 슬라이스를 완성하려면 z 좌표 산출 path 가 필요.

D-18 박제 단일 카메라 옵션:

1. **옵션 A**: RTMW3D 직접 사용 (rtmlib 의 3D wholebody 변형 — `rtmw3d-*` 가중치).
2. **옵션 B**: RTMW 2D + MotionBERT lifter (plan 07 lifter 재사용 + Apache-2.0).

belle 가 둘 중 1개를 선택하면, 본 plan 의 Task 2 에서 선택된 어댑터만
완전 구현하고 비선택 어댑터는 stub 유지 (R&D 격리는 plan 24 책임).

---

## 2. 옵션 A: RTMW3D 직접 사용

**구성:** rtmlib RTMW3D 가중치 → 단일 추론 → (T, 133, 3) 직접 산출 →
`RTMW133ToCOCO17Adapter` 로 COCO-17 + 폴 확장 변환.

### Pro

- **단일 추론 경로** — 2D 와 3D 가 동일 모델에서 산출. 두 단계 추론 latency 없음
  (plan 23 ms/frame 비교 시 옵션 B 보다 빠를 가능성).
- **lift path 좌우 swap 약점 (plan 17 audit Cycle 3) 부재** —
  Plan 16 belle Pod live mode 의 `swap_ratio 1.00` (left_elbow_vs_right_elbow)
  root cause = lifter 자체 신뢰도 (Plan 16 가설 b/c/d strong). 옵션 A 는
  lifter 가 없으므로 회귀 위험 0.
- **MotionBERT 추가 의존 0** — `torch` 모델 1개만 (RTMW3D ONNX). MotionBERT
  체크포인트 (`best_epoch.bin`) 와 DSTformer Python 패키지 의존 제거.

### Con

- **rtmlib RTMW3D 가중치 라이선스 미확정** — `weights_manifest.json` 의
  `rtmw3d-x-384x288` entry 는 현재 `license_status: "restricted"`,
  `production_eligible: false`. Cocktail14 학습 데이터 (AI Challenger /
  CrowdPose 등) 의 상업 약관 리스크가 RTMW 2D 와 동일. belle 가중치 승급
  결정 (plan 20 audit 도 정합) 필요.
- **단안 (monocular) 3D 정확도 한계** — 개발 지시 §2 "모노큘러 3D 정확도 한계"
  인용. 단일 카메라에서 z 의 절대 스케일은 부정확 (relative pose 만 신뢰).
  옵션 B 도 동일 한계 (lifter 도 monocular).
- **rtmlib 의 RTMW3D 변형 가용 가중치 부족** — plan 20 audit §1-1 deviation
  박제: "plan 명시 RTMW3D-l 는 mmpose 공식 zoo 부재 — RTMW3D-x 로 대체".

### 가중치 후보 (weights_manifest §rtmw3d-x-384x288)

```
name      : rtmw3d-x-384x288
url       : https://huggingface.co/Soykaf/RTMW3D-x/resolve/main/onnx/rtmw3d-x_8xb64_cocktail14-384x288-b0a0eab7_20240626.onnx
sha256    : null  (plan 22/23 다운로드 시 박제 예정)
input_size: [384, 288]
ap_wholebody: 68.0
license_status     : restricted
production_eligible: false  (Task 2 belle 결정 시 true 로 승급 필요)
```

옵션 A 채택 시 belle 가 `weights_manifest.json` 의 `rtmw3d-x-384x288` entry 를
`production_eligible: true` 로 승급 + `belle_decision` 블록 추가 (RTMW 2D 의
`rtmw-x-384x288` 와 동일 패턴 — Plan 21 박제).

---

## 3. 옵션 B: RTMW 2D + MotionBERT lifter (plan 07 재사용)

**구성:** RTMW 2D (plan 21 `RTMWPoseEngine`) → COCO-17 → H3.6M 17 변환 →
`MotionBertLifter.lift()` → (T, 17, 3) → COCO-17 역변환 → `PoseFrame.keypoints_3d`.

### Pro

- **MotionBERT 라이선스 = Apache 2.0 박제** (plan 07 SUMMARY 인용,
  https://github.com/Walter0807/MotionBERT/blob/main/LICENSE). MIT 도
  허용 라이선스 (HybrIK 백업 후보, plan 07).
- **plan 17 keypoint mapping fix 적용 path 그대로 활용** — Cycle 3 audit
  PASS (5 mapping source 58 row canonical). MediaPipe path 의 분석 정합
  검증을 RTMW 2D 로 그대로 이식 가능 (단, COCO-17 → H3.6M 17 변환은
  RTMW 용으로 신규 작성 필요 — `rtmpose_to_h36m17.py` 또는
  `mediapipe_to_h36m17.py` 의 패턴 활용).
- **분리 가능성** — 2D (RTMW) 와 3D (MotionBERT) 가 독립 모듈. 두 단계 각각
  단위 테스트 + 디버깅 가능. lifter 만 교체 (HybrIK 등) 가능성 보존.

### Con

- **2 단계 추론 latency** — RTMW 추론 + MotionBERT lifter 추론. ms/frame
  의 합산이 plan 23 의 옵션 A 단일 추론 대비 클 것으로 예상 (plan 07 spike
  에서 MP+MotionBERT 86.8ms/frame, NLF 243.8ms/frame — MP 대신 RTMW 면
  추가 ~50ms/frame 예상).
- **lift path swap_ratio 1.00 회귀 위험 (plan 16, plan 17 audit)** —
  Plan 16 belle Pod live mode `left_elbow_vs_right_elbow swap_ratio 1.00`
  dominant root cause = lifter 자체 (occlusion / 거꾸로 매달림 자세에서
  좌우 keypoint 헷갈림, Plan 16 가설 b/c/d strong). 본 plan 의
  `test_selected_engine_no_left_right_swap` 게이트 가 회귀 방지 강제.
- **MotionBERT 가중치 파일 추가** — `best_epoch.bin` (~ 수십 MB) 을 RunPod
  Pod 에 별도 배치 + `MOTIONBERT_ROOT` / `MOTIONBERT_WEIGHTS` env 주입.
  RTMW 2D 가중치 외 운영 의존 +1.
- **MotionBERT 데이터셋 학습 셋 (H3.6M)** — H3.6M 라이선스 사용 약관 검토
  필요 (학술 license, 상업 사용 명시되지 않음 — 다만 본 plan 단계에서는
  validation-pilot scope, plan 21 박제 정합).

---

## 4. 결정 기준

belle 결정 시 다음 4가지 기준 가중치로 판단 (우선순위 = 1~4 순서):

| 기준 | 옵션 A | 옵션 B | 비고 |
|------|--------|--------|------|
| (a) **정확도** (plan 23 회귀 검증 결과) | 미측정 | 미측정 | plan 23 실행 후 비교 가능. 현재 단계에서는 둘 다 monocular 한계. |
| (b) **latency** (plan 23 ms/frame) | ~ 단일 추론 | ~ 2 단계 추론 | 옵션 A 가 약 1.5~2× 빠를 가능성 (정성적). plan 23 측정. |
| (c) **라이선스** (plan 20 audit) | RTMW3D = restricted (현재) | RTMW 2D = commercial_ok + MotionBERT = Apache-2.0 + H3.6M = academic | 옵션 B 가 라이선스 측면에서 깔끔. 옵션 A 채택 시 belle 가 RTMW3D 가중치 승급 결정 필요. |
| (d) **plan 17 swap_ratio 회귀 위험** | 0 (lifter 없음) | ≥ 0 (Plan 16 dominant root cause 회귀 가능) | 옵션 A 가 위험 0. 옵션 B 는 `test_selected_engine_no_left_right_swap` 가 회귀 방지 게이트. |

**MVP (분석 정확도 우선, CLAUDE.md core value 박제):** (a) > (d) > (c) > (b).
즉 정확도가 가장 중요, 그 다음 swap 회귀 위험 (분석 신뢰), 그 다음 라이선스,
마지막 latency.

본 plan 단계에서 (a) 측정 불가 — plan 23 의 회귀 검증에서 산출. 따라서
belle 는 (b)(c)(d) + 시점 정성 판단으로 결정. plan 23 결과가 예상과 다르면
plan 24 단계에서 path 재변경 가능 (단, swap 비용 발생 — 본 plan §6 격리 대상 박제).

---

## 5. belle 결정

selected: option_b

- **결정일자:** 2026-06-03
- **응답자:** belle (`approved: option_b`)
- **선택 path:** 옵션 B — RTMW 2D + MotionBERT lifter (plan 07 재사용).

### 결정 근거 (핵심)

**1. 라이선스 (기준 c, 우선순위 3):** 옵션 A 의 RTMW3D 가중치
`rtmw3d-x-384x288` 은 현재 `weights_manifest.json` 에서
`license_status: "restricted"` + `production_eligible: false`
박제. plan 20 audit (`docs/licenses/rtmw-weights-audit.md`) 가 동일
결론. 옵션 A 채택 시 belle 가중치 승급 결정 + 별도 commercial-clean
가중치 확보가 필요 — 비용 + 일정 리스크. 반면 옵션 B 는 운영
RTMW 2D 가중치 (`rtmw-x-384x288`, plan 20 belle 승급 완료) +
MotionBERT lite Apache-2.0 (plan 07 SUMMARY 박제) + H3.6M 학습셋
(validation-pilot scope 한정, 상업 출시 전 별도 plan 확보) 로 즉시
조립 가능.

**2. 운영 path 단계적 검증 (기준 b/d, 우선순위 2/4):** 옵션 B 는 2D
(plan 21 RTMW) 와 3D (plan 07 MotionBERT) 가 분리된 path — 두 단계
독립 디버깅 + plan 23 회귀 검증에서 swap_ratio + latency 를 각 단계별로
측정 가능. plan 17 mapping fix (Cycle 3 audit, swap_ratio 회귀
root cause 박제) 가 옵션 B path 에 즉시 적용됨. 옵션 A 는 단일 모델로
회귀 발견 시 디버깅 단위가 크다.

**3. 정확도 비교는 plan 23 단계로 이연 (기준 a, 우선순위 1):** 본
plan 단계에서 (a) 측정 불가. plan 23 회귀 검증에서 옵션 B path 의
ms/frame + 정확도가 임계 미달이면 옵션 A 재평가 (별 plan 24/25 의
입력) — 단, 옵션 B 의 라이선스/단계 분리 이점이 plan 23 결과보다
선결과제.

### 비선택 옵션 A 의 R&D 격리 (plan 24 입력)

- **격리 대상:** `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw3d_engine.py`
  (NotImplementedError stub 유지). `weights_manifest.json` 의
  `rtmw3d-x-384x288` entry 는 `production_eligible: false` 유지 (D-25 게이트).
- **격리 위치 (plan 24 책임):** 별도 R&D 트리 또는 stub 잔존. 본 plan 은
  운영 path 격리만 박제, 실제 이동은 plan 24 가 일괄 처리.
- **운영 코드 유지:** `RTMWPoseEngine` (plan 21) + 본 plan
  `RTMWLifterPoseEngine` (옵션 B 실 구현) + `MotionBertLifter` (plan 07).
- **`MediaPipeWithLifterEngine` 의 격리:** 옵션 B 채택으로 MediaPipe path 가
  RTMW 로 교체됨 — `mediapipe_lifter_engine.py` 는 plan 24 의 R&D 격리 대상.

---

## 6. 선택 후 격리 대상 (plan 24 입력)

옵션 A 선택 시:

- **격리 대상 (R&D 이동)**: plan 07 `backend/shared/python/sunity_shared/analysis/pose_lifters/motionbert_lifter.py`,
  `backend/research/spikes/mediapipe_to_h36m17.py`, plan 08 합산
  `MediaPipeWithLifterEngine` (`backend/shared/python/sunity_shared/analysis/pose_engines/mediapipe_lifter_engine.py`).
- **격리 위치 (plan 24)**: `backend/research/pose_engines/` 또는 별 R&D 트리
  (D-06/D-07 NLF 격리 패턴 정합).
- **운영 코드 유지**: `RTMWPoseEngine` (plan 21), 본 plan 의 `RTMW3DPoseEngine`.

옵션 B 선택 시:

- **격리 대상 (R&D 이동)**: 본 plan `RTMW3DPoseEngine` stub. RTMW3D 가중치는
  `weights_manifest.json` 에 entry 만 유지 (production_eligible=false).
- **운영 코드 유지**: `RTMWPoseEngine` (plan 21), `MotionBertLifter` (plan 07),
  본 plan `RTMWLifterPoseEngine`. `MediaPipeWithLifterEngine` 는 R&D 격리
  (MediaPipe 운영 path 가 RTMW 로 교체되었으므로).

---

## 7. 후속 plan

- plan 23: 선택된 path 로 5영상 회귀 검증 + IPSF score 측정 (분석 정확도 (a) 확정).
- plan 24: 비선택 path R&D 격리 + 운영 path atomic swap (POSE_ENGINE=RTMW 강제).
- plan 25: 운영 배포 + RunPod 환경 path 동기화.

Pose2Sim (멀티 카메라) 통합은 Phase 4 (다중 시점) — 본 plan scope 외.
`single-camera-first-multi-view-last` 정책 그대로 적용.
