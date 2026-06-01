---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: milestone
status: active
last_updated: "2026-06-01T15:30:00.000Z"
last_activity: 2026-06-01 -- Plan 12 T-1~T-4 완료 (debug_gap_root_cause.py + 11 smoke 테스트 PASS). report-only verdict = (c) strong / (d) strong, live mode (a)(b)(e) belle Pod 대기. Plan 12 = pending_belle.
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 14
  completed_plans: 8
  percent: 57
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** 분석 정확도 — 점수가 믿을 만하고 첫 분석이 "전문가 수준으로 구체적". 수치는 보조, 원인이 핵심.
**Current focus:** Phase 01 — Plan 12 T-1~T-4 완료, T-5 belle Pod live mode 대기. report-only verdict = (c) NLF baseline 편차 strong + (d) keypoint chain 정의 strong. live mode (a) frame-mean / (b) RTMPose headdown / (e) 두 엔진 3D 분포 — belle 실행 후 verdict 확정 → Plan 13 진입 권고.

## Current Position

Phase: 01 (poseengine-mediapipe-nlf-r-d) — ACTIVE, Plan 12 T-1~T-4 완료, T-5 belle Pod live mode 대기
Plan: 8/14 complete (01, 02, 03, 06, 07, 08, 10, 11 done) + 09 closed as license_blocked + 12 T-1~T-4 (pending_belle T-5), 13, 14 진입 대기 + 04, 05 (Wave 3 — Plan 14 통과 후 진입)
Status: Active — Plan 12 debug_gap_root_cause.py 완성, 11 smoke 테스트 PASS. report-only mode 1차 verdict (c) strong (NLF overall span 23 ≥ 20) + (d) strong (RTMPose H36M ordering vs NLF COCO ordering 17/17 다름). live mode (a)(b)(e) belle Pod 대기. belle Pod live 실행 후 → 본 SUMMARY verdict 갱신 → `/gsd:plan-phase 1 --plan 13` (Plan 13 Gemini key moment + criteria PLAN 작성) 진입.
Last activity: 2026-06-01 -- Plan 12 T-1~T-4 commit (debug_gap_root_cause + 11 smoke 테스트 + README + SUMMARY). T-5 belle Pod live mode 대기 (2영상 또는 5영상 선택).

Progress: [█████▋░░░░] 57%

## ▶ Plan 11 sweep verdict `gap_too_wide_blocked` (2026-06-01) — Plan 12/13/14 신설

belle Pod 5영상 sweep (`sweep_rtmpose_20260601_0411`) 결과:

| 모션 | RTMPose+MB | NLF | gap | D-15① ≥70 | D-14 |gap|≤5 | line | angle |
|---|---|---|---|---|---|---|---|
| ref-climb | 89.0 | 58.0 | **+31** | PASS | **FAIL** | N/A | N/A |
| ref-foxtop-split | 79.0 | 63.0 | **+16** | PASS | **FAIL** | N/A | N/A |
| ref-foxtop | 81.0 | 64.0 | **+17** | PASS | **FAIL** | N/A | N/A |
| ref-invert | 70.0 | 65.0 | +5 | PASS | PASS | N/A | N/A |
| ref-sideway-spin | 80.0 | 81.0 | -1 | PASS | PASS | N/A | N/A |

D-15① 5/5 PASS, D-14 2/5 PASS, line·angle 0/5 PASS. 평균 |gap| = 14점.

**belle 결정 (2026-06-01)**: "갭은 어떻게든 줄여야 한다. Gemini 든 다른 수단이든 가리지 말고." + "라인과 각도도 계획에 들어가야 한다." → D-14 강등 거부. 갭 + line/angle 둘 다 Wave 3 진입 1순위 게이트. Plan 12/13/14 신설.

### 신설 Plan 12 / 13 / 14

| Plan | 역할 | 게이트 통과 path |
|---|---|---|
| **01-12** (NEW) | 갭 root cause 디버그 spike | 가설 a~e (frame-mean / RTMPose headdown / NLF baseline 편차 / keypoint 매핑 / MotionBERT lift path) + ref-invert 22점 회귀 + sideway-spin Plan10 vs Plan11 비일관성 박제 |
| **01-13** (NEW) | Gemini key moment + criteria extractor | multimodal 2.5 Pro. hold/peak/setup/release 시점 + EXTEND/BENT criteria. dimensions sampling frame-mean → moment-list 교체. line/angle 회복 + 갭 줄이기 동시 path. |
| **01-14** (NEW) | 5영상 재검증 sweep | Plan 12 fix + Plan 13 key moment 적용 후 sweep_rtmpose 재실행. **게이트 = 갭 ≤5 + line/angle 5/5 PASS** |

Plan 14 통과 → Plan 04 / Plan 05 (Wave 3) 진입.

### Plan 08 (MP+MB) 대비 RTMPose 회귀

| 모션 | MP+MB (P08) | RTMPose+MB (P11) | Δ |
|---|---|---|---|
| ref-climb | 85 | 89 | +4 |
| ref-foxtop-split | 75 | 79 | +4 |
| ref-foxtop | 90 | 81 | -9 |
| **ref-invert** | **92** | **70** | **-22** ← 회귀 |
| ref-sideway-spin | 64 | 80 | +16 |

ref-invert RTMPose headdown 약점 가설 — Plan 12 에서 frame-by-frame avg_rtm_score 분포 분석.

### Plan 10 spike vs Plan 11 sweep — ref-sideway-spin 비일관성

| | Plan 10 spike | Plan 11 sweep | Δ |
|---|---|---|---|
| overall | 72 | 80 | +8 |
| ms/frame | 37 | 21 | 절반 |

같은 영상/설정. frame seek/sampling 차이 가설 — Plan 12 에서 spike vs sweep 같은 영상 비교 trace.

## ▶ Plan 10 STRONG_PASS 결과 (2026-06-01) — Plan 11 (C scope) 진입

**Plan 10 verdict** = `strong_pass`. ref-sideway-spin 1영상:

| 항목 | RTMPose+MB | NLF | 갭 | 게이트 |
|---|---|---|---|---|
| overall | **72.0** | 81.0 | -9.0 | D-15① PASS (≥70) |
| stability | 72.0 | 81.0 | -9.0 | — |
| line | N/A | N/A | N/A | **Phase 5 게이트** |
| angle | N/A | N/A | N/A | **Phase 5 게이트** |
| ms/frame | 37 | 665 | — | 18x faster (production win) |

**핵심 발견**: line / angle N/A = FallbackRecognizer 한계 (PROJECT.md "현 핵심 블로커"와 정확히 일치 — "굽은 그립 자세에서 EXTEND 못 찾아 line 차원 None"). 해결은 **Phase 5 Gemini 기술 인식기** 통합.

### Plan 11 scope (belle approved C, 2026-06-01)

- **T-1**: 5영상 sweep (ref-climb / ref-foxtop-split / ref-foxtop / ref-invert / ref-sideway-spin) — RTMPose+MB vs NLF baseline
- **T-2**: line / angle N/A root cause 박제 — FallbackRecognizer 한계 정확히 어떤 자세/관절에서 발동? threshold 조정으로 일부 회복 가능? 다른 4영상에서도 같은 패턴?
- **T-3**: 게이트 룰 검토 — D-15① 70 threshold 적정 여부, D-14 (NLF gap ≤5) production 우선순위 재확인
- **T-4**: Wave 3 진입 게이트 — Plan 04 (NLF R&D 격리) + Plan 05 (atomic swap) 진입 조건 명시
- **T-5**: belle Pod 실행 + 5영상 결과 판정

Gemini 통합은 **Phase 5 별 phase** — belle Gemini API 키 (Google AI Studio) 발급 + Parameter Store 주입 wiring 선행 필요.

### belle Gemini API 키 작업 (병행, 2026-06-01 발급 진행)

| Phase | Gemini 역할 | 권장 모델 | 키 발급 path |
|---|---|---|---|
| **Phase 5** | 기술 인식기 (영상 → 분류 + EXTEND/BENT) | **Gemini 2.5 Pro** (multimodal) | Google AI Studio → /sunity/motion/gemini-api-key (SecureString) |
| **Phase 11** | 자연어 코칭 번역 | Cerebras llama3.1 유지 권장 (이미 동작 중) | — |

### Plan 10 디버그 이력 (Pod 4함정 박제)

1. mmcv 빌드 실패 → `pip install --no-build-isolation "mmcv>=2.0,<2.2"` (mmcv 2.1.0)
2. numpy ABI 불일치 → `pip install "numpy>=1.26,<2"` (1.26.4 다운그레이드)
3. detector alias 카탈로그 실패 → spike 코드 패치 commit `f019070` (single-person 우회 default)
4. Pod git pull 갱신 안 됨 → 로컬 commit 후 `git push origin main` 누락. push 후 Pod pull 정상.

상세 fix 명령 + 환경 변수 = `.claude/projects/.../memory/runpod-gpu-env.md` 박제됨.
GSD process rule = `.claude/projects/.../memory/gsd-pod-work-push-first.md` 박제됨.

### 현재 Pod 환경 (2026-06-01 22:00 시점, Plan 11 진입 준비됨)

**Pod 살아있음. 추가 install 없음.** Plan 11 belle 실행 = git pull + sweep 명령만.

| 항목 | 상태 |
|---|---|
| GPU / Container | RTX 3090 / RunPod PyTorch 2.4 template, Python 3.11 |
| torch | 2.4.1+cu124 (검증됨) |
| numpy | 1.26.4 (다운그레이드, opencv-python warning 무시 가능) |
| mmcv / mmengine / mmdet / mmpose | 2.1.0 / 0.10.7 / 3.3.0 / 1.3.2 |
| xtcocotools | 1.14.3 (numpy 1.x 호환) |
| MotionBERT | `/workspace/MotionBERT/` clone + `best_epoch.bin` (~120MB) |
| RTMPose-l weights | `/workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth` + `.py` config |
| SunityMotion git HEAD | 10683aa (Plan 10 closeout + Plan 11) — push 됨, Pod 에서 `git pull` 시 받음 |
| detector default | single-person 우회 (`--det-model none`) — commit f019070 |
| AWS 자격증명 | env 박제됨 (Plan 08 setup 이래 유지) |
| Firebase SA | `/workspace/firebase-sa.json` |
| Gemini API 키 | Parameter Store `/sunity/motion/gemini-api-key` (SecureString, 2026-06-01 박제). Pod env 주입은 Phase 5 진입 시 wiring |

**Memory 박제 완료** (`license-blocklist-pose.md`): AlphaPose Noncommercial → 향후 plan 후보군에서 영구 제외.

### Plan 09 의사결정 매트릭스 (이력 보존)

| belle 응답 | Plan 10 방향 | 결과 |
|---|---|---|
| **option-b-1, spike RTMPose** | Apache 2.0 + 2D detector 교체 | **✓ 선택됨 (2026-06-01) → STRONG_PASS** |
| option-a, spike HybrIK | MIT + SMPL prior lift | 미선택 |
| option-c, accept 4/5 | 게이트 룰 재정의 | 미선택 |
| option-d, multi-view | 다중 시점 v1 spec | 미선택 |
| option-b-2 / b-3 | MMPose HRNet / MS HRNet | 미선택 |
| hold + research more | 별도 research 후 신규 plan | 미선택 |

## Plan 08 5영상 검증 결과 (재인용)

| 모션 | MP+lifter | NLF | D-15① ≥70 |
|---|---|---|---|
| ref-climb | 85 | 58 | PASS |
| ref-foxtop-split | 75 | 62 | PASS |
| ref-foxtop | 90 | 64 | PASS |
| ref-invert | 92 | 65 | PASS |
| **ref-sideway-spin** | **64** | 81 | **FAIL** |

평균 81.2 (Plan 06 단독 MP: 22.8 → **3.5배 회복**). D-15① 4/5 PASS.

**Path B 결정 (2026-05-31)**: AlphaPose 2D 어댑터로 측면 자세 보강 → ref-sideway-spin ≥ 70 회복 spike (Plan 09).
**Path B 수정 (2026-06-01)**: AlphaPose 라이선스 Noncommercial → **RTMPose-l (Apache 2.0)** 로 대체 (Plan 10). 통과 시 5영상 sweep + 게이트 룰 재정의 + Wave 3 진입 (Plan 11+).

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
