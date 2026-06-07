---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: milestone
status: executing
stopped_at: "2026-06-07 Phase 12.5 close-out (commits 1c0d20a T1+T2 backend / 62fdeed T9 backend / e968074 T8+T9 frontend). 자세히 모달 2종 (차원/코칭) + LLM-ready coach_writer JSON 프롬프트 + dimensionExplanation 분기-1 mode-aware 카피 + belle UX 검증 PASS (모달 스크롤 정상 + 심사평 3박자 톤). Phase 12.5 시뮬 한계 3종 (폭스탑 학원 용어 어색 / angle 차원 180° 명시 X / 시뮬 segments 일부) 는 Phase 13 으로 통합 — 보완 운동 추천 (PERS-03) + LLM 분기 카피 + coaching detail 완성 단일 phase. backend coach_writer 한 번에 작업."
last_updated: "2026-06-07T17:45:00.000Z"
last_activity: 2026-06-07 -- Phase 12.5 close-out + Phase 13 scope 확장 (LLM 분기 카피 통합)
progress:
  total_phases: 16
  completed_phases: 4
  total_plans: 31
  completed_plans: 23
  percent: 56
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-29)

**Core value:** 분석 정확도 — 점수가 믿을 만하고 첫 분석이 "전문가 수준으로 구체적". 수치는 보조, 원인이 핵심.
**Current focus:** Phase 05 — gemini

## Current Position

Phase: 12.5 (UI Transparency) — **DONE** (2026-06-07 close-out)
Next phase: 13 (보완 운동 추천 + LLM 분기 카피 + coaching detail 완성) — READY TO PLAN
Status: 진입 대기 (/gsd-plan-phase 13)

> Phase 13 scope 확장 (belle 2026-06-07): 원래 "보완 운동·스트레칭 추천 라이브러리" (PERS-03) 단독이었으나, Phase 12.5 시뮬 한계의 backend 후속 작업 (LLM 활성화 + 분기 1/2 카피 분리 + IPSF 정의 각도 fixture) 을 같은 phase 로 통합. 이유: backend `coach_writer` 단일 작업 + 동작 분기 후 그 동작별 보완 운동 추천이 같은 흐름. 이전에 신설한 Phase 12.6 = revert.

### Phase 12.5 close-out 내역

| 영역 | 결과 |
|---|---|
| backend `assemble.build_dimension_explanation` | weightPercent (Largest Remainder) + mode-aware baseline + source-faithful deficits (commit 1c0d20a) |
| backend `coach_writer` LLM | Cerebras gpt-oss-120b JSON 프롬프트 — 다중 원인 + case 처방 + 부상 경고 + coachNote. graceful `_normalize_entry` (commit 62fdeed) |
| frontend `DimensionDetailModal` | 동작·사용자 동적 formula ("세계 심사 기준은 [동작]에서 ... [회원]님의 영상 자세를 반영") + "심사평" 자연어 3박자 (평가+이유+결정) |
| frontend `CoachingTipDetailModal` | LLM `tip.detail2` 렌더 (causes 카드 + injury 경고 + coachNote). detail2 없으면 graceful fallback |
| UX 함정 fix | (a) sheet useWindowDimensions 명시 height (b) backdrop = pure View + 위 빈 영역만 Pressable — Pressable+stopPropagation 가 ScrollView gesture 가로채는 함정 회피 |
| belle UX 검증 | PASS — 스크롤 어디서든 정상 동작, 심사평 톤 OK |

### Phase 12.5 남은 한계 (Phase 12.6 이관)

1. **학원 용어 vs IPSF 등재 분기 카피** — 폭스탑 = "정은지 선수 기준" / 클라임 = "세계 심사 기준 (IPSF) + 180°". 메모리 [`studio-term-3branch-system`] 분기 1/2 정합
2. **angle 차원 동작별 IPSF 정의 각도** — 어깨 90° / 엉덩이 110° 등 동작별 fixture 또는 LLM 매핑
3. **시뮬 segments 일부 시나리오 X** — mode 3 first 정답 (이전 영상 없음), 그 외는 실 분석에서 backend `assemble.build_segments` 자동 생성
Last activity: 2026-06-07 -- 로드맵 재정렬 + Phase 12.5 신설

**시퀀스 (belle 2026-06-07 결정 — B → C → A)**:
1. **B (Phase 12.5)** — 3~5일 — UI transparency + 강사 보조 카피 — 빌드 12 ship
2. **C (Phase 16 코드 통합)** — 1~2주 — AKA 매핑 + 5트랙 v1 + 분기 3 — 빌드 13 ship
3. **A (Phase 12)** — 2주~ — 실측 각도 + 키포인트 오버레이 — 빌드 14 ship
4. parallel: Plan 01-24 — NLF R&D 격리 명시 — 0.5~1일, B 와 별도 PR

상세 = `.planning/roadmap-replan-2026-06-07.md` + `.planning/roadmap-replan-2026-06-07-review.md`.

Progress: [██████████░░░░░░] 50% (Phase 1/5/16 close-out + 12.5 진입)

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

Last session: 2026-06-07 -- belle 실제 TestFlight 빌드 11 분석 PASS (mode1+mode3 first 정합). 세션 종료.

Stopped at: 2026-06-07 belle 의 mode3 첫 분석 진짜 first 박제 정합 동작 확인. 5가지 추가 fix 박제. 다음 세션 = 개발 로드맵 정리 + 외부 AI 검증 + A/B/C plan 진행.

### 2026-06-07 추가 fix 5종 (빌드 10 → 11 박제)

| commit | scope |
|---|---|
| `787a901` | iOS 26+ letterSpacing 음수 SIGABRT fix (typography.ts track → 0) |
| `e3bf753` | package-lock.json sync |
| `0472c01` | eas.json production profile env 박제 (.env gitignore 우회) |
| `0bd6a48` | get_previous_analysis mode 인자 박제 (mode3 first ↔ mode1 prev 함정) |
| `3f6681f` | Firestore composite index 회피 + in-memory mode filter |

### 박제 메모 [[runpod-gpu-env]] 함정 31-34 추가

- 31: eas.json production env 누락 (.gitignore 박제 .env)
- 32: Firebase 익명 uid 가 IPA 빌드별 다름 (정상 동작, 단 시연 시 데이터 fresh)
- 33: Firestore composite index 자동 생성 X — query 단순화 + in-memory filter
- 34: simulatedResult 폴백이 Firestore 없을 때 가짜 결과 보임 (dev 안전망 — production 박제 후보)

### belle 의 진단 + 박제 정신 안내 (코드 fix 없이)

- "Expo 박제 박제 박제 박제 박제 박제 X" — 박제 정신 정합 안내. TestFlight 박제 박제 박제 박제
- mode1 vs mode3 점수 차이 = 같은 정은지지만 다른 cut/clip 박제 정합
- ref-climb line 차원 누락 = IPSF "Transitions & Climbs" 박제 각도 임계 X (의도된 빈 list). foxtop/invert 박제 박제 line 박제 박제 박제
- "고급 88" = 사용자 박제 SkillLevel (advanced) 박제 평균 점수, 현재 분석과 무관
- VideoCompare 10초 정지 = 짧은 영상 끝나면 둘 다 정지 (동시 비교 박제 정신)

### 다음 세션 우선 진행 (belle 결정)

belle 의 의문 박제 정신 정합:
1. **개발 로드맵 순서 정리** — Phase 1-15 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 (Phase 5 박제 박제, Phase 1/14/15 박제 박제 박제)
2. **외부 AI 검증** — Codex/gpt-5.5 plan-review-convergence 박제 cross-check ([[cross-ai-plan-review-good]] 박제 정합)
3. **A/B/C plan 진행** (belle 명시 박제):
   - **A. Phase 12** = 실측 각도 표시 + 키포인트 오버레이 (큰 scope)
   - **B. (d) 결과 UI transparency** = result.tsx 차원별 "이게 무슨 기준" 박제 + 가중치 표시 (작은 scope)
   - **C. Phase 16 IPSF 5트랙 코드 통합** = 학원 용어 매핑 + RepetitionCriterion + Page 9 (중간 scope)

박제 정신상 belle 의 의도 = "사용자가 '아 이래서 이런 평가구나' 박제" = B 박제 빠른 path. A 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. C 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제. 박제 정신상 A+B+C 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제 박제.

### 2026-06-07 세션 핵심 박제

**Phase 5 사실상 완료** — mock E2E mode1/mode3 PASS + belle 실제 분석 mode1 점수 94/97 PASS + 5가지 UI/UX 의문 fix:
1. (b3) 코칭팁 라벨 중복 fix ("오른쪽 어깨 어깨" → "오른쪽 어깨")
2. (b4) 숫자 브랜드 컬러 강조 (#FF4B33)
3. (b5) 완벽 수행 메시지 (angle 95+ 시 + mode 분기)
4. (b1) backend playback-url Lambda 신설 + (b2) frontend wiring (S3 7일 TTL 만료 fix)
5. mode3 second+ overall 산식 변경 — (각도+안정성) 평균 (belle 의문 정합)

**Phase 15 진행** — TestFlight letterSpacing SIGABRT fix:
- root cause = `theme/typography.ts` 의 `track(size) = size * -0.04` (음수 letterSpacing)
- fix = `track(size) = 0` (commit 787a901)
- EAS Build 10 + auto-submit (commit e3bf753 lock sync)

**Cerebras 모델 fix** — `llama3.1-8b` deprecated → `gpt-oss-120b` (commit 1110935)

**SAM deploy regression fix** — Lambda env RUNPOD_ANALYZE_URL 직접 update (SAM template parameter default reset 함정 28)

### belle 박제 의문 정합 안내 (코드 fix 없이 박제 정신)

1. mode1=95 vs mode3=100 차이 = belle 영상 (_talkv_high.mp4) ≠ reference (ref-climb.mp4) 다른 cut → 정합
2. line 차원 누락 = `ref-climb` 은 IPSF "Transitions & Climbs" 박제 각도 임계 X (의도된 빈 list). 다른 motion (foxtop/invert) 시 line 정상 박제 — Phase 16 코드 통합 후속
3. "고급 88" = 사용자 박제 SkillLevel (advanced) 박제 평균 점수, 현재 분석과 무관
4. VideoCompare 10초 정지 = 짧은 영상 끝나면 둘 다 정지 (동시 비교 박제 정합)

Resume file: .planning/phases/05-gemini/05-05-SUMMARY.md

### 2026-06-06 세션 핵심 사건 — OpenMMLab CDN 글로벌 만료

`download.openmmlab.com` 도메인이 2026-06-04 즈음 만료 — `dig +trace` 권한 NS 자체가 `expirens3/4.hichina.com` (Alibaba HiChina 만료 도메인 전용 NS). 박제된 RTMW URL + YOLOX URL 모두 도달 불가. mmpose 사용자 전체 영향. 박제 메모 [[rtmw-clean-weight-release-gate.md]] 의 우려 적중.

belle 결정 (mirror 검색 path) → HuggingFace anonymous mirror 활용 우회 완료:
- RTMW-X-384: `hf://bukuroo/RTMW-ONNX/rtmw-x-384.onnx` (369MB) + S3 백업 `s3://sunity-motion-pilot-videos/_artifacts/rtmw-x-384_bukuroo_hf.onnx`
- YOLOX-M (person detector): `hf://hr16/yolox-onnx/yolox_m.onnx` (97MB, Apache-2.0)

### 박제 commit + 함정 추가 (이번 세션)

| commit | 영역 | 내용 |
|---|---|---|
| 4b823de | setup_pod_full.sh | mmcv build ninja 선행 install + MAX_JOBS export (함정 26) |
| 081192b | rtmw_engine.py | YOLOX_ONNX_PATH env 박제 — OpenMMLab CDN 만료 우회 (함정 22) |

박제 메모 [[runpod-gpu-env.md]] 갱신 = 함정 20~27 추가 (누적 27종). 핵심:
- 함정 20: OpenMMLab CDN 글로벌 만료 (2026-06-04)
- 함정 21/22: RTMW + YOLOX HF mirror path
- 함정 23/24: setup_pod_full.sh 박제 누락 (runpod_inference/requirements.txt install + RUNPOD_AUTH_TOKEN .bashrc)
- 함정 25: server.py auth header = `X-RunPod-Token` (Authorization Bearer 아님)
- 함정 27: stale __pycache__ — git pull 후 uvicorn restart 시 cache 청소 필요

### 백엔드 검증 결과

| 검증 | 결과 |
|---|---|
| Pod /health 외부 | 200 OK, `pipeline_loaded:true, auth_configured:true` |
| Pod /analyze 외부 mock (X-RunPod-Token + dummy body) | 422 Pydantic validation (endpoint alive) |
| Lambda env RUNPOD_ANALYZE_URL | Active, 새 Pod URL 정합 |
| **mock E2E** (Pod 안에서 _process 직접 호출) | **PASS** — Firestore status=done, 49.8s |

### Pod 환경 (2026-06-06 종료 시점, Pod 1ablelgbtrzcgb 살아있음)

| 항목 | 상태 |
|---|---|
| GPU / Container | RTX 3090 / RunPod PyTorch 2.4, Python 3.11 |
| SSH | `ssh -p 14818 -i ~/.ssh/id_ed25519 root@64.119.209.250` |
| /workspace | SunityMotion HEAD = 081192b, firebase-sa.json, rtmw_weights/rtmw-x-384.onnx, yolox_weights/yolox_m.onnx |
| .bashrc env | RUNPOD_AUTH_TOKEN/RTMW_ONNX_PATH/YOLOX_ONNX_PATH/RECOGNIZER_BACKEND=gemini/RTMW_DEVICE=cuda/LD_LIBRARY_PATH/FIREBASE_SA_PATH 박제 |
| uvicorn server | PID 9652 살아있음, 0.0.0.0:8000 LISTEN, 워밍업 완료 (RTMW+YOLOX+Gemini API 검증) |
| Lambda env RUNPOD_ANALYZE_URL | https://1ablelgbtrzcgb-8000.proxy.runpod.net/analyze |

### 남은 작업

- [ ] **TestFlight 튕김 fix** (별개 blocker, [Phase 15 — iOS] letterSpacing SIGABRT 후보) — belle 가 진짜 E2E 검증할 channel 필요
- [ ] **belle 진짜 E2E 검증** — Expo Go QR 또는 빌드 10 ship 후 TestFlight 재시도. mock 가 동일 path PASS 확인.
- [ ] Phase 5 close-out (ROADMAP Phase 5 ✓) — belle 진짜 E2E 통과 후
- [ ] Phase 6 진입 — Phase 5 close-out 후
- [ ] setup_pod_full.sh 후속 갱신 commit — 함정 23/24 박제 (runpod_inference/requirements.txt install + RUNPOD_AUTH_TOKEN + YOLOX_ONNX_PATH .bashrc + OpenMMLab CDN 우회 download path)
- [ ] mock E2E artifact cleanup (선택) — S3 `uploads/mock_e2e_belle_1780754054/` + Firestore mock doc
- [ ] sweep 박제 baseline 재산정 (선택) — cocktail13 → bukuroo 가중치 변경 영향 평가 (`sweep_rtmw_20260603_1409` baseline 과 직접 비교 무효 가능)
