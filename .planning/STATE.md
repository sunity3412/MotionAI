---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: milestone
status: paused
stopped_at: "Plan 08 belle 5영상 검증 4/5 PASS — Path B (AlphaPose 측면 보강) 확정. Plan 09 stub 작성됨. RunPod Pod Terminate 후 내일 setup.sh 재실행 → Plan 09 spike 진입."
last_updated: "2026-05-31T15:00:00.000Z"
last_activity: 2026-05-31 -- Plan 08 belle 검증 완료, Path B 결정 (AlphaPose)
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 9
  completed_plans: 6
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** 분석 정확도 — 점수가 믿을 만하고 첫 분석이 "전문가 수준으로 구체적". 수치는 보조, 원인이 핵심.
**Current focus:** Phase 01 — Wave 2 belle 검증 진행 중. Plan 06/07/08 통과, Plan 09 (AlphaPose spike) 진입 대기.

## Current Position

Phase: 01 (poseengine-mediapipe-nlf-r-d) — PAUSED at Plan 09 진입 직전
Plan: 6/9 complete (01, 02, 03, 06, 07, 08 done)
Status: Paused — belle 내일 재진입
Last activity: 2026-05-31 -- Plan 08 belle 검증 완료, B 결정

Progress: [██████░░░░] 67%

## ▶ 내일 재개 — Plan 09 진입 절차

1. **RunPod 새 Pod 생성** (PyTorch 2.4+, RTX 4090 / 3090 / RTX 5000 Ada, 16GB+ VRAM)
2. **환경 복원** (Pod SSH):
   ```bash
   cd /workspace
   git clone https://github.com/sunity3412/MotionAI.git SunityMotion
   cd SunityMotion/backend
   bash runpod_inference/setup.sh
   ```
3. **MotionBERT 가중치 scp** (Plan 08 와 동일):
   ```bash
   # belle 로컬에서
   scp -P <port> -i ~/.ssh/id_ed25519 -r \
     ~/Downloads/FT_MB_lite_MB_ft_h36m_global_lite \
     root@<pod-ip>:/workspace/MotionBERT/checkpoint/pose3d/
   ```
4. **AWS 키 export + PYTHONPATH** (Plan 08 README 참조)
5. **Plan 09 진입**:
   ```bash
   # 로컬에서 (이 디렉토리에서)
   /gsd-execute-phase 1
   ```
   → Plan 09 만 incomplete 로 잡혀서 자동 실행. spike code → belle Pod 에서 ref-sideway-spin 실행 → 결과 보고

## Plan 08 5영상 검증 결과 (재인용)

| 모션 | MP+lifter | NLF | D-15① ≥70 |
|---|---|---|---|
| ref-climb | 85 | 58 | PASS |
| ref-foxtop-split | 75 | 62 | PASS |
| ref-foxtop | 90 | 64 | PASS |
| ref-invert | 92 | 65 | PASS |
| **ref-sideway-spin** | **64** | 81 | **FAIL** |

평균 81.2 (Plan 06 단독 MP: 22.8 → **3.5배 회복**). D-15① 4/5 PASS.

**Path B 결정**: AlphaPose 2D 어댑터로 측면 자세 보강 → ref-sideway-spin ≥ 70 회복 spike (Plan 09) → 통과 시 5영상 sweep + 게이트 룰 재정의 + Wave 3 진입 (Plan 10).

## Performance Metrics

**Velocity:**

- Total plans completed: 6 (01-01, 01-02, 01-03, 01-06, 01-07, 01-08)
- Average duration: ~30 min/plan (executor) + belle Pod 실행 별도

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [2026-05-31 아키텍처]: 두 엔진 분리 — 엔진 A(체형 보정, coaching 모드 정규화 ON) + 엔진 B(힘 패턴, 움직임 방향만 측정·근육 힘 단정 금지)
- [2026-05-31 포즈 — 최종]: **상용/베타 제품 = MediaPipe + Gemini** (Apache 2.0, 라이선스 리스크 0). **NLF/SMPL-X = 라이선스 확인 전까지 제품 코드 비포함, 내부 비상업 R&D 비교군으로만 사용**. 입수처 = https://is.mpg.de/ps/code, https://smpl-x.is.tue.mpg.de. PoseEngine 인터페이스 추상화 — `MediaPipePoseEngine`(제품) + `NlfPoseEngine`(R&D 격리) 어댑터 2개 운영. NLF/SMPL-X 출시 사용 시 Max Planck Innovation 상업 라이선스(`info@max-planck-innovation.de`) 클리어 필수. 공개 베타·유료 파일럿·고객 영상 처리에 NLF/SMPL-X 절대 사용 금지
- [2026-05-31 모드]: judging 모드(IPSF Code of Points) v1.5로 분리, 데이터 수집은 v1 평행 (belle/강사)
- [2026-05-31 UX]: 다중 시점 촬영 v1 포함 (occlusion 완화)
- [2026-05-31 Gemini]: 역할 = 자연어 번역 전용. 좌표·판단·점수 출력 금지 (운동학 휴리스틱 + 코치 마무리)
- [2026-05-31 코치]: 모든 리포트에 CoachCommentHook 부착 (v1 데이터 구조), UI/입력은 v2
- [전반]: 채점 차원 = IPSF 기반 (각도/라인/안정성), 균형(대칭) 제거 — 위양성(41점) 주범 제거
- [Phase 14]: 기준 모션 등록 = 다각도 캡처 프로토콜 + 두 엔진 출력 포함 (Mode 1 신뢰도의 기준)
- [Phase 15]: Mode 3 = 발전(progress) 표시, %일치 헤드라인 금지 (세션 간 델타)

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- [Phase 1 — 마이그레이션 HIGH]: 현 제품 코드는 NLF 기반 (`backend/shared/python/sunity_shared/analysis/pose_estimator.py`, RunPod GPU pod). Phase 1에서 MediaPipe 어댑터로 전환 + NLF 모듈을 R&D 비교군으로 격리 필요. RunPod GPU pod 비용 절감 + 라이선스 리스크 0 효과.
- [라이선스 — 출시 게이트]: NLF/SMPL-X는 R&D 비교군 전용으로 제품 비포함 결정 — Phase 진행은 블로킹되지 않음. 향후 NLF/SMPL-X를 제품에 도입하려면 Max Planck Innovation 상업 라이선스 클리어 필수 (`info@max-planck-innovation.de`). Meshcapade 채널은 종료됨.
- [Phase 5 — 외부 의존]: Gemini API 키(belle, Google AI Studio) 필요. Parameter Store / RunPod env 주입 전까지 Phase 5 블로킹.
- [v1.5 — 데이터 수집]: IPSF Code of Points 임계값(3~5개 동작 × phase별 GeometricCriterion) 라벨링은 v1 평행 진행 (belle/강사 협업).
- [전반 — 보안 HIGH]: 노출된 `sunity-api` AWS 키 비활성화 미완 (plan.md cleanup 큐). 작업 착수 전 처리 권장.
- [Phase 15 — 운영]: RunPod Pod 생명주기 수동. 재생성 시 proxy URL 변경 → Lambda env(RunpodAnalyzeUrl) 동기화 필요. 중단 시 실분석 전면 중단.
- [Phase 15 — iOS]: iOS 26+ native style 회귀(letterSpacing SIGABRT) — 빌드 10에서 ship 필요, 음수 style 값 audit.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-31T06:58:06.038Z
Stopped at: Phase 1 context gathered (4 areas: MediaPipe variant, NLF R&D 격리, 폴 축 검출, 회귀 검증 — 16 decisions)
Resume file: .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md
Next: /gsd:discuss-phase 1 — Phase 1 (PoseEngine + MediaPipe + 폴 축 + NLF R&D 격리) 본격 시작
