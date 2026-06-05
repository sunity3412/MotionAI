---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: milestone
status: executing
stopped_at: "/gsd:plan-phase 5 완료 — Pattern mapper + Planner (6 plan) + Plan-checker iter 1 (8 blocker + 6 warning) + Revision iter 1 (15/15 fix) + Plan-checker iter 2 (0 blocker + 4 warning) + 인라인 fix (4 warning). 6 plan 박제 = 5-00 (yaml 정정 belle checkpoint Wave 0) → 5-01+5-02 평행 (어댑터+캡싱 Wave 1) → 5-03 (pipeline swap Wave 2) → 5-04 (Pod wiring Wave 3) → 5-05 (sweep + belle Pod checkpoint Wave 4). D-01 게이트 = "채점 영역 모션 N/N PASS + out-of-scope counted as PASS" (B1 fix, ref-climb out-of-scope 박제). CONTEXT.md/RESEARCH.md/IPSF-LOOKUP.md/PATTERNS.md 박제 완비."
last_updated: "2026-06-04T07:26:31.965Z"
last_activity: 2026-06-04 -- Phase 05 execution started
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 31
  completed_plans: 23
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** 분석 정확도 — 점수가 믿을 만하고 첫 분석이 "전문가 수준으로 구체적". 수치는 보조, 원인이 핵심.
**Current focus:** Phase 05 — gemini

## Current Position

Phase: 05 (gemini) — EXECUTING
Plan: 1 of 6
Status: Executing Phase 05
Last activity: 2026-06-04 -- Phase 05 execution started

Progress: [██████░░░░] 60%

## ▶ Plan 23 sweep verdict `phase1_ready_to_swap=False` (2026-06-03) — D-16 보류

belle Pod 5영상 sweep (`backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.md`) 결과:

| 게이트 | 결과 | 박제 기준 |
|---|---|---|
| IPSF within_tolerance | **1/5 PASS** | 5/5 필요 |
| line PASS | **3/5 PASS** | 5/5 필요 |
| angle PASS | **0/5 PASS** | 5/5 필요 |
| pole_axis | 5/5 low (수직 폴백) | high 필요 |

| 모션 | pole_axis | IPSF | line | angle | ms/f | rtmw_score |
|---|---|---|---|---|---|---|
| ref-climb | low | PASS | PASS | FAIL | 2201 | 95.4 |
| ref-foxtop-split | low | FAIL | FAIL | FAIL | 2164 | 93.0 |
| ref-foxtop | low | FAIL | FAIL | FAIL | 2083 | 93.3 |
| ref-invert | low | FAIL | PASS | FAIL | 2116 | 93.6 |
| ref-sideway-spin | low | FAIL | PASS | FAIL | 2009 | 94.8 |

**핵심 진단 (root cause 3종 동시 발현)**:

1. **IPSF criteria target=180° 일률 — FallbackRecognizer 한계**
   - 모든 hold moment 의 shoulder/hip/knee target=180° (완전 EXTEND 가정)
   - measured 값 21~107° = 실제 자세는 굽힘인데 yaml 은 폄 가정
   - Plan 11 박제 ("FallbackRecognizer 가 굽은 자세에서 EXTEND 못 찾아 line 차원 None") 그대로 — Phase 5 (Gemini 기술 인식기) 통합 전엔 IPSF angle 게이트 의미 없음

2. **HoughPoleDetector 미설치 → pole_axis 부정확**
   - 5영상 모두 axis_vector=(0,1,0) low confidence (수직 폴백)
   - 실제 카메라 각도/폴 회전 있을 시 line 측정값 부정확
   - line 3/5 PASS 도 폴백 영향 가능

3. **AKA 매핑 vs yaml criteria 정합 미검증**
   - belle 매핑: `ref-foxtop.yaml` ← 인버트 버터플라이, `ref-invert.yaml` ← 플랭크 스핀, 등
   - yaml hold target=180° 가 그 자세의 IPSF 기준인지 belle/정은지/NotebookLM IPSF CoP 2024-2025 재검증 필요

**belle 결정 (2026-06-03)**: 결과 박제 commit 먼저 + 다음 plan 의논. 박제 [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" 정신 유지.

**Plan 24 / 25 진입 차단 — D-16 보류**. 다음 후보:

- (A) Phase 5 (Gemini 기술 인식기) 통합 선행
- (B) Plan 26 (가칭) — root cause 3종 동시 fix plan 신설 (Gemini wiring + HoughPoleDetector + yaml 재검증)

### Plan 23 belle Pod sweep 함정 5종 박제 (재사용 위함)

| 함정 | Fix |
|---|---|
| `imageio` pyav 플러그인 누락 | `pip install 'imageio[pyav]'` |
| rtmlib 0.0.15 `pose` alias 부재 | `export RTMW_ONNX_PATH=<unzipped end2end.onnx>` 강제 (commit 3b27c25) |
| rtmlib Wholebody batch 미지원 | 단일 (H,W,3) frame 입력 (commit 375c21c) |
| mmpose `chumpy` 빌드 fail | `pip install --no-build-isolation chumpy` 선행 |
| onnx 위치 패턴 | `<weights_root>/20230928/rtmpose_onnx/<model>/end2end.onnx` |

상세 박제 = [[runpod-gpu-env.md]] 업데이트 누적 중.

---

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

### belle Gemini API 키 작업 (병행, 2026-06-01 발급 진행 / 2026-06-03 모델 갱신)

| Phase | Gemini 역할 | 권장 모델 (2026-06-03 belle 결정) | 키 발급 path |
|---|---|---|---|
| **Phase 5** | 기술 인식기 (영상 → 분류 + EXTEND/BENT) | **Gemini 3.1 Pro 단일** (belle 2026-06-04 확정, 3.0 삭제). 3.5 Flash 는 v1 미사용 — v2 비용 분석 후 별 plan 평가 | Google AI Studio → /sunity/motion/gemini-api-key (SecureString) |
| **Phase 11** | 자연어 코칭 번역 | Cerebras llama3.1 유지 권장 (이미 동작 중) — Gemini 3.5 Flash 도 후보 (한국어 품질 비교 필요) | — |

belle 박제 (2026-06-03): "분석이 완벽해야 한다는 것 = 모든 박제 기준. 우회/대체 상황이면 언제든 제안 OK". 모델 선택은 분석 정확도 기준 — 이전 박제 (2.5 Pro) 는 정보 부족 시점 추정, 3.0/3.1 Pro 가 실제 사용 가능 시점에 정확도 + multimodal 성능 우위.

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
- [2026-06-02 학원 용어 + 5트랙]: Phase 16 신설 — Studio Terminology Foundation. 학원 용어 3분기 시스템 (AKA 매핑 13개 / 정은지 reference 비등재 동작 / 자동 수집 + UX 카피) + IPSF 5트랙 채점 v1 scope (a) Compulsory Criteria + (c) Technical Deduction + Page 9 "all components" 절대 트랙. **MVP 가볍게 — 코드 통합 후속, 박제만 v1**. **실증 검증 게이트** = 파일럿 후 사용자 키워드 분기 1/2/3 비율 + 자동 수집 누적 패턴 → 한 번에 확장. NotebookLM IPSF CoP 2024-2025 lookup 박제 (Element Code Matching p.138-139, Page 9 "all components" CoP 2021-2024, AKA 13개 매핑). v1 신설 SCORE-05/TERM-01/TERM-DATA-01/TERM-COPY-01 + v2 신설 SCORE-V2-02/03 + TERM-V2-01/02. memory studio-term-3branch-system + ipsf-5-track-scoring 박제.
- [Phase ?]: Plan 16-01 T-6 belle threshold 결정

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
- [Phase 16 — 데이터/스펙 박제]: Phase 1~15 의존성 없음 (v1 평행). Phase 1 진행 중 평행 진입 가능. 단 Phase 5 (Gemini 기술 인식기) / Phase 14 (정은지 reference) 가 Phase 16 데이터를 소비하므로 그 시점에 통합 필요. 첫 plan (16-01-PLAN.md) = AKA 매핑 13개 + 5트랙 spec + 카피 박제 (코드 통합 X).

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-06-05 -- Wave 4 (Plan 5-05) Task 2 — 3차 sweep (Path A 적용 후) 완료. motion 분류 정상화 ✓ but D-01 게이트 여전히 FAIL — 새 root cause 3종 박제 (함정 20/21/22).
Stopped at: 2026-06-05 박제 함정 11종 누적 (Plan 5-05 기준 19→22). 3차 sweep = 5/5 ref motion 매핑 ✓ but line/angle 0/5 PASS. ref-climb out_of_scope_PASS 분기 동작 안 함 (함정 20). ref-foxtop yaml target ↔ RTMW measured 108° gap (함정 21). ref-invert/sideway-spin 5/6 within_tol — knee 1개만 FAIL (함정 22 tolerance 검토). main HEAD = 2ebe8d3.
Resume file: .planning/phases/05-gemini/05-05-SUMMARY.md (Task 2 1차+2차+3차 verdict + 함정 11종 + Path A 효과 박제 + Path D/E/F/G 후보 박제)
Next: belle 결정 — Path D (함정 20 ref-climb out_of_scope_PASS 분기 fix, 단순) + E (함정 21 ref-foxtop yaml target ↔ RTMW measured 갭 진단 spike, 깊음) + F (함정 22 tolerance 임계값 IPSF CoP lookup, 정책) 동시 진행 또는 우선순위 결정. ref-invert/sideway-spin 5/6 = 거의 통과 — tolerance 가 핵심일 수도.
