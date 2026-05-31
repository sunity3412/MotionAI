---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "09"
subsystem: ml-pose-engine
tags:
  - spike
  - alphapose
  - license-blocked
  - sideway-spin
  - lifter-evaluation

dependency_graph:
  requires:
    - 01-07  # MotionBERT spike pattern
    - 01-08  # MP+MotionBERT production 4/5 PASS
  provides:
    - "AlphaPose 라이선스 박제 (Noncommercial Research Only) — 상업 파일럿 진입 금지"
    - "측면 자세 보강 대안 lifter 후보 정리 (HybrIK MIT, MMPose Apache 2.0, HRNet MIT)"
    - "belle 의사결정 checkpoint — 대안 lifter spike vs 4/5 수용 vs 운영 변경"
  affects:
    - 01-10  # 다음 plan 분기는 belle 응답에 따라 달라짐

tech_stack:
  added: []
  patterns:
    - "라이선스 게이트 우선 — 코드 작성 전 LICENSE 원문 확인"

key_files:
  created:
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-09-SUMMARY.md
  modified: []

decisions:
  - "AlphaPose 라이선스 = Noncommercial Research Only (Shanghai Jiao Tong University). Plan 09 hard truth #3 '안 맞으면 spike 중단' 발동 → 어댑터·spike 러너·단위 테스트 작성하지 않음."
  - "spike 작성 보류 — belle 의사결정 (대안 lifter spike 또는 4/5 수용) 필요"

requirements_completed: []

metrics:
  duration: "~15 min (라이선스 research 단계에서 HALT)"
  completed_date: "2026-06-01"
  tasks_completed: 1
  tasks_total: 4
  files_created: 1
  files_modified: 0
---

# Phase 01 Plan 09: AlphaPose Spike — License Blocked (Halted at T-1-1)

**One-liner:** AlphaPose 라이선스가 Noncommercial Research Only (Shanghai Jiao Tong University) — 상업 파일럿 MVP에 도입 불가. Plan 09 hard truth #3 발동, spike 코드 작성 전 STOP. belle 의사결정 대기.

---

## 결론 (TL;DR)

| 항목 | 내용 |
|---|---|
| **Verdict** | `license_blocked` |
| **단계 도달** | T-1-1 (라이선스 확인) |
| **AlphaPose 라이선스** | "ACADEMIC OR NON-PROFIT ORGANIZATION NONCOMMERCIAL RESEARCH USE ONLY" |
| **Licensor** | Shanghai Jiao Tong University |
| **확인 일자** | 2026-06-01 |
| **출처** | https://github.com/MVIG-SJTU/AlphaPose/blob/master/LICENSE |
| **작성한 코드** | 없음 (hard truth 발동) |
| **작성한 테스트** | 없음 |
| **만든 커밋** | `docs(01-09): record AlphaPose license-blocked verdict` (이 SUMMARY 1건) |

---

## T-1-1 라이선스 검증 결과

### AlphaPose LICENSE 원문 핵심 조항

> "ACADEMIC OR NON-PROFIT ORGANIZATION NONCOMMERCIAL RESEARCH USE ONLY"
>
> "...hereby grants to Licensee a personal, non-exclusive, non-transferable license to use the Software for **noncommercial research purposes**, without the right to sublicense..."
>
> "USES NOT PERMITTED: You may not distribute, copy or use the Software except as explicitly permitted herein... You may not sell, rent, lease, sublicense, lend, time-share or transfer, in whole or in part, or provide third parties access to prior or present versions (or any parts thereof) of the Software."

### Sunity AI Coach 상업 사용 충돌 분석

| 조항 | Sunity 사용 케이스 | 충돌 여부 |
|---|---|---|
| Noncommercial only | 폴스포츠 학원 파일럿 → 유료 SaaS 지향 (CLAUDE.md §2) | **충돌** |
| No sublicense | RunPod Pod 배포 + Lambda 위임 = 제3자 인프라 사용 | 충돌 가능 |
| No distribution | git 추적 금지로 회피 가능 | 회피 가능 |
| No third-party access | 수강생이 분석 결과 받음 — 출력은 derivative 일 수 있음 | 회피 어려움 |

**판정**: AlphaPose 도입은 상업 파일럿 MVP 라이선스 컴플라이언스 위반이다. Plan 09 frontmatter `must_haves.truths[2]` ("AlphaPose 라이선스 Apache 2.0 확인 후 진입. 안 맞으면 spike 중단 + belle 재검토") hard rule 발동.

### Plan 09 hard constraint 준수

이 executor 는 Plan 09 의 다음 scope_limits / hard truths 를 따라 STOP:

1. `must_haves.truths[2]`: "AlphaPose 라이선스 Apache 2.0 확인 후 진입. 안 맞으면 spike 중단"
2. Executor 시스템 프롬프트 hard constraint: "HALT condition (T-1-1): AlphaPose license must be Apache 2.0 or MIT or BSD. If GPL/AGPL/non-commercial, STOP, do not write the adapter"

→ T-2 (어댑터), T-3 (spike 러너), T-4 (Pod 실행 checkpoint) **모두 미실행**.
→ 운영 코드 (functions/, shared/pose_lifters/) 변경 없음.
→ 테스트 파일 생성 없음.

---

## 측면 자세 보강 대안 후보 (belle 검토용)

Plan 08 ref-sideway-spin 64점 fail 의 원인은 MotionBERT 가 H3.6M (정면 walking/sitting) 학습이라 측면 z 복원이 약함. AlphaPose 가 막혔으니 대안 lifter / 대안 2D detector 후보를 정리:

### Option A — 다른 lifter 로 측면 보강 (3D lift 단계 교체)

| 후보 | 라이선스 | 메모 | 측면 강점 |
|---|---|---|---|
| **HybrIK** | MIT (Jeff-sjtu, SJTU MVIG, 별도 fork) | SMPL-X 출력 — 신체 모델 기반 reconstruction, body shape 까지 복원 | 측면 z 복원이 SMPL prior 로 안정. Plan 07 README 에서 이미 백업 후보로 박제 |
| **VideoPose3D** | CC-BY-NC (Facebook Research) | 시간축 conv — 옛 SOTA. 측면 데이터 학습 분포 미상 | 비상용 라이선스 — Sunity 도입 불가 |
| **MotionBERT (current) 측면 fine-tune** | Apache 2.0 (그대로) | 폴스포츠 측면 라벨 데이터로 추가 학습 | 데이터 확보 비용 큼 — belle 보유 영상 확인 필요 |

### Option B — 2D detector 단계 교체 (MediaPipe 대안)

| 후보 | 라이선스 | 메모 | 측면 강점 |
|---|---|---|---|
| **MMPose RTMPose** | Apache 2.0 (OpenMMLab) | COCO-17 직접 출력, 측면 데이터 포함 학습. CPU/GPU 양쪽 추론 | RTMPose-l 측면 PCK 높음. AlphaPose 직접 대체에 가장 가까움 |
| **MMPose HRNet** | Apache 2.0 (OpenMMLab) | HRNet 기반, top-down. Microsoft 원본 동등 | 정확도 높지만 무거움 |
| **HRNet 원본 (Microsoft)** | MIT | deep-high-resolution-net.pytorch. AlphaPose 와 거의 동급 베이스라인 | 측면 자세 robust (MS-COCO 학습) |

### Option C — 게이트 룰 재정의 path (4/5 수용)

Plan 08 belle 검증 결과 `4/5 PASS, ref-sideway-spin 만 64`. AlphaPose 측면 보강을 포기하고 게이트 룰을 "5영상 중 4영상 (80%) ≥70 만족 시 PASS" 로 재정의 → Wave 3 진입.

| 장점 | 단점 |
|---|---|
| 추가 코드 작업 없음 | sideway-spin 분석 정확도 약점이 production 으로 들어감 |
| Wave 3 (NLF 격리 + atomic swap) 즉시 진입 가능 | "core value = 분석 정확도" (CLAUDE.md) 와 약간 충돌 |
| Plan 10 = 게이트 룰 재정의 + Wave 3 진입 | 측면 자세 영상이 늘면 unknown limitation 노출 위험 |

### Option D — 다중 시점 v1 활용

PROJECT.md `[2026-05-31 UX] 다중 시점 촬영 v1 포함 (occlusion 완화)`. 측면 영상을 입력 단계에서 정면+측면 두 각도 캡처로 보완 → lift 단계 부담 분산.

| 장점 | 단점 |
|---|---|
| 라이선스 게이트 회피 | 사용자 onboarding 부담 증가 |
| occlusion 완화는 belle 가 이미 결정한 path | 다중 시점 fusion 알고리즘 구현 비용 (별도 plan 필요) |
| 정은지 reference 도 다중 시점 박제 가능 | 파일럿 시연 일정 압박 (CLAUDE.md §2) |

---

## 권장 사항 (executor 의견 — belle 결정 권한)

executor 추천 우선순위:

1. **Option B-1 (MMPose RTMPose)** — Apache 2.0 + 측면 강함 + AlphaPose 의 직접 대체. RunPod 환경에 통합 쉬움. spike pattern 은 Plan 07 spike_motionbert.py 그대로 재사용 가능.
2. **Option A (HybrIK)** — Plan 07 README 에서 이미 백업 후보로 명시. MIT + SMPL prior 기반 측면 안정. MotionBERT 와는 다른 lift 방식이라 ablation 명확.
3. **Option C (4/5 수용)** — 추가 R&D 비용 0. 단 분석 정확도 core value 와 약간의 충돌. belle 가 시연 우선이면 즉시 채택.
4. **Option D (다중 시점)** — 시간 여유 있을 때만. 별도 plan 작성 필요.

**executor 단독 결정은 하지 않는다** — 라이선스 결정 + lifter 선택 = belle 권한.

---

## belle Pod checkpoint Payload (조건부 — belle 가 Option A/B 채택 시)

> **참고**: 본 plan 09 는 라이선스 차단으로 spike 실행 자체가 없음. AlphaPose Pod install 절차는 의도적으로 제공하지 않음 (라이선스 위반 가능성).
> belle 가 Option B-1 (MMPose RTMPose) 또는 Option A (HybrIK) 채택 시, Plan 10 작성 단계에서 신규 install/실행 절차를 spike README 에 박제.

다음은 belle 가 가장 가능성 높은 path (Option B-1 RTMPose) 채택 가정 시, Plan 10 spike 의 Pod 실행 형태 (참고용 윤곽 — executor 가 이 plan 에서 실행하지 않음):

```bash
# Pod 환경 (Plan 08 setup.sh 가 복원한 상태 가정)
cd /workspace/SunityMotion
export PYTHONPATH="/workspace/SunityMotion/backend/shared/python:/workspace/SunityMotion:$PYTHONPATH"
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_DEFAULT_REGION=ap-northeast-2
export MOTIONBERT_ROOT=/workspace/MotionBERT
export MOTIONBERT_WEIGHTS=/workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin
export CUDA_VISIBLE_DEVICES=0

# Option B-1 spike 가설:
# pip install mmpose mmengine mmcv  (Plan 10 에서 박제)
# python3 -m backend.research.spikes.spike_rtmpose --motion ref-sideway-spin \
#   --bucket sunity-motion-pilot-videos \
#   --rtmpose-checkpoint <path> \
#   --out backend/research/spikes/reports/spike_rtmpose_$(date +%Y%m%d_%H%M).json
```

위 윤곽은 **Plan 10 작성 시 확정** — 본 plan 09 는 라이선스 게이트에서 STOP.

---

## 의사결정 매트릭스 (belle 응답)

| belle 응답 | 다음 plan 작성 |
|---|---|
| **"option-a, spike HybrIK"** | Plan 10 = HybrIK spike (Path = MIT 라이선스 박제 + spike harness + ref-sideway-spin 1영상) |
| **"option-b-1, spike MMPose RTMPose"** | Plan 10 = RTMPose spike (Apache 2.0 + 2D detector 교체 + MotionBERT lift 그대로) |
| **"option-b-2, spike MMPose HRNet" / "option-b-3, spike Microsoft HRNet"** | Plan 10 = HRNet 계열 spike |
| **"option-c, accept 4/5 and proceed"** | Plan 10 = 게이트 룰 재정의 (4/5 또는 80%) + Wave 3 진입 (NLF 격리 + atomic swap) |
| **"option-d, multi-view"** | Plan 10 = 다중 시점 v1 spec + 기준 모션 다각도 캡처 spike |
| **"hold + research more"** | Plan 09 은 license_blocked 로 닫고, belle 가 별도 research 후 새 plan ID 부여 |

---

## Deviations from Plan

### [Rule 4 - Architectural] License gate triggered HALT at T-1-1

- **Found during**: Task 1 (T-1-1 라이선스 확인)
- **Issue**: AlphaPose 라이선스가 Noncommercial Research Only — Apache 2.0 / MIT / BSD 가 아님.
- **Plan rule 발동**: `must_haves.truths[2]` "AlphaPose 라이선스 Apache 2.0 확인 후 진입. 안 맞으면 spike 중단 + belle 재검토"
- **Fix**: spike 코드 작성 안 함. SUMMARY 만 작성하여 belle 의사결정 받음.
- **Files modified**: 없음 (의도)
- **Verification**: LICENSE 원문 fetch 후 핵심 조항 인용 + GitHub API license metadata 검증.
- **Commit**: `docs(01-09): record AlphaPose license-blocked verdict + alternative candidates`

**Total deviations:** 1 (Rule 4 - Architectural). **Impact:** Plan 09 는 spike 코드 production 없이 종료. Plan 10 작성 방향이 belle 응답에 의존.

---

## Known Stubs

없음 — 어떤 code stub 도 작성하지 않음 (라이선스 게이트에서 STOP).

---

## Threat Flags

없음.

---

## Self-Check: PASSED

파일 존재 확인:
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-09-SUMMARY.md`: WRITING (이 파일)

생성하지 않은 파일 (의도적):
- `backend/research/spikes/alphapose_to_h36m17.py` — NOT CREATED (license 게이트)
- `backend/research/spikes/spike_alphapose.py` — NOT CREATED (license 게이트)
- `backend/tests/test_spike_alphapose_to_h36m17.py` — NOT CREATED (license 게이트)
- `backend/research/spikes/README.md` (AlphaPose section 추가) — NOT MODIFIED (license 게이트)

운영 코드 변경 0 — Plan 08 production code (`pose_lifters/`, `pose_engines/`) 무수정 유지.

---

## Verdict 요약 — orchestrator 에게

- **verdict**: `license_blocked`
- **one-liner**: AlphaPose 라이선스 Noncommercial Only → spike 코드 작성 전 STOP, belle 의 대안 lifter 결정 (HybrIK / MMPose RTMPose / 4/5 수용 / 다중 시점) 대기.
- **commits**: 1건 (이 SUMMARY 의 docs commit)
- **next action**: belle 응답 → Plan 10 작성 방향 분기 (위 의사결정 매트릭스 참조)
