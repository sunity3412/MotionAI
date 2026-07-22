---
phase: 32-result-readability-3-omni
plan: 15
subsystem: backend-pipeline, ml-engine, deploy
tags: [d22, d23, pr-inversion, perspective-rotation, 2pass, rtmw, homography, pod-deploy, d23-sweep, phase-final, python]

# Dependency graph
requires:
  - phase: 32-14
    provides: "스윕 기준선 (runId 1784676884) + 배포·스윕 관례 (run_sweep_3214.sh mirror) + 12관절 conf 분포"
  - phase: spike-006
    provides: "PR 수학(H=K·R·K⁻¹) + invert −58% 실측 + kpts 실데이터 (.planning/spikes/004)"
provides:
  - "inversion_warp.py — 인버전 검출 휴리스틱(순수 numpy) + 호모그래피 forward/inverse + 프레임 워프 (spike pr_warp_pod 편입)"
  - "RTMWPoseEngine 2-pass 조건부 훅 — PR_INVERSION_ENABLED env (제한 게이트 PASS 후 production on)"
  - "phase 32 엔진 웨이브 최종 전수 스윕 (runId 1784683741) — 비검출 8멤버 diff 0 + 검출 4멤버 개선 실측"
affects: [32 phase 마감 (belle 최종 확인), reference 재처리 후속 결정 (인버전 기준 모션 비대칭), 2단 감점 편입 게이트 (후속 phase)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "2-pass 조건부 보정 = 1차 추론(기존 경로 불변) → 결과 기반 검출 → 참일 때만 워프 2차 추론 → H⁻¹ 원본 공간 복원 — 순환 의존 0, 좌표계 불변, 미검출=바이트 동일"
    - "엔진 레버 게이트 = env 코드 기본 off → 제한 통합 게이트(수치) → production 박제 mirror on → 전수 스윕 양방 검증"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/inversion_warp.py
    - backend/tests/phase32/test_inversion_warp.py
  modified:
    - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py

key-decisions:
  - "훅 위치 = rtmw_engine.py (플랜 명목 pose_estimator.py 는 DEPRECATED NLF 미사용 경로 — 프로덕션 단일 관문에 삽입)"
  - "검출 상수 = margin 0.3·ratio 0.15·run 5 (spike 10 clip 재계측 — TP 최소 0.289/run9 vs FP 최대 0.042/run2 양방 여유)"
  - "elbow-twist-sister·pdshape = 실측 인버전 동작 (신체 방향 기준 일반화 — 이름 열거 아님). 검출 4멤버 변화는 게이트 의미론상 허용·실측 기록, 비검출 8멤버 diff 0 달성"
  - "PR_INVERSION_ENABLED=1 production 박제 (start_server.sh) — 제한 게이트 PASS(invert 46.8%↑·+2.97s·bounds·육안) 후"

patterns-established:
  - "engine-lever bounded gate: Pod 수동 실행 2건(개선 실증 + 무회귀 실증)을 전수 스윕 앞에 배치 — 실패 시 env off 안전 마감 경로 확보"

requirements-completed: [D-22, D-23]

# Metrics
duration: ~2h 50m (스윕 98분 포함)
completed: 2026-07-22
---

# Phase 32 Plan 15: PR 인버전 보정 + phase 32 최종 전수 스윕 Summary

**spike 006 실측(−58%)의 PR(PersPose 위상회전) 보정을 2-pass 조건부 아키텍처(1차 추론 → 검출 → 참일 때만 워프 2차 추론 → H⁻¹ 원본 공간 복원)로 프로덕션 추론 관문(RTMWPoseEngine)에 넣고, 제한 통합 게이트(invert boneCV −46.8% ≥30% / latency +2.97s ≤60s / 좌표 bounds·육안 정합 / power-spin detect False) PASS 후 production env on — phase 32 엔진 웨이브 최종 6동작 전수 스윕(runId 1784683741)에서 비검출 8멤버 점수·criteria·keypointReport 바이트 완전 diff 0 + 검출 4멤버(elbow-twist·pdshape = 실측 인버전 동작)의 좌표 기질 대폭 개선(boneCV −62.8~−92.8%)과 fault/success 분리 확대(pdshape 42→53)를 수치로 실측**

## Task Commits

| Task | 내용 | 커밋 |
|---|---|---|
| 1 (RED) | 검출·round-trip·fail-safe·순수성 실패 테스트 15건 | `0c9d2eb` |
| 1 (GREEN) | inversion_warp.py — 검출(spike 캘리브레이션) + numpy Rodrigues H + fail-safe | `e8dc788` |
| 2 | RTMWPoseEngine 2-pass 조건부 훅(기본 off) + 배선 테스트 5건 | `f3dd6f2` |
| 2-3 | Pod 배포·제한 게이트·production on·전수 스윕 (코드 무수정 — 본 SUMMARY 기록) | (docs 커밋) |

## 검출 휴리스틱 캘리브레이션 (Task 1 — spike 실데이터)

- 판정 = 프레임별 (어깨mid_y − 엉덩이mid_y)/torso > **0.3** 인 "역위 프레임"이 유효 프레임의 **≥15%** AND 최장 연속 **≥5프레임**(9fps ~0.56s). 두 조건 AND — 고속 스핀의 순간 역전은 run 조건이 차단.
- spike 10 clip 재계측(margin 0.3): TP측 invert 0.289/run18 · straddle-invert 0.300/20 · elbow-twist 1.000/9 vs FP측 power-spin 0.042/2 · sideway-spin 0.025/1 · 정립 5종 0.000/0 — **양방 2~3.6배 여유**.
- **elbow-twist-sister 분류 정정 (실측):** 플랜 예시 열거엔 없었으나 신체 방향 실측 91% 역위(hip-above-shoulder ratio 1.000 — invert 본인보다 강함) → TP. 이름 열거가 아닌 기준(신체 방향)으로 일반화 ([[motion-routing-generalize-principle]]).
- 로컬 테스트 20건: 합성 4(정립/지속/flicker/저신뢰) + spike 실데이터 10 clip TP3/FP0 + round-trip eps 1e-6 + 프레임 fail-safe 4 + 순수성 3 + 엔진 배선 5. `pytest tests/phase32` **191 passed**.

## 2-pass 조건부 훅 (Task 2 — 리뷰 blocker 6 해소)

- `estimate()` 를 `_infer_raw`(추론) + `_build_pose_frames`(변환) 로 byte-equivalent 분리 후, 1차 추론 **완료 뒤** `_maybe_second_pass_inversion` 삽입. 검출 입력 = 1차 추론 결과 → **순환 의존 0**.
- 참이면: 1차 kpts 평활 중심(창 9, spike 동일) → 프레임별 H=K·R·K⁻¹ → cv2 워프 → 2차 추론 → **좌표를 H⁻¹로 원본 프레임 공간 복원**(body 17 유효성 판정 + 133 전량 유한 시만 교체 — 프레임 단위 폴백) → 신뢰도는 2차 것. 거짓/off/워프 실패/센터 부재 = 1차 결과 그대로 (같은 객체 반환 — 바이트 동일 구조 보장).
- **훅 위치 편차(기록):** 플랜 files_modified 의 pose_estimator.py(NlfPoseEstimator) 는 DEPRECATED — 프로덕션은 pipeline `_RTMWNlfCompat`→`RTMWPoseEngine` 단일 관문 (pipeline/app.py 의 NlfPoseEstimator 참조는 주석 2곳뿐, grep 실측). 죽은 경로에 훅을 넣지 않고 실제 관문에 삽입.
- 로그: `pr_inversion detect is_inverted=… ratio=… run=… valid=…` + `applied=true replaced=n/T second_pass_ms=…` (key=value).

## 제한 통합 게이트 (Task 2 — Pod 실측, PASS)

배포: push `f3dd6f2` → Pod pull → start_server.sh 재기동(env off) → `/health` 200 (내부+proxy).

**(a) invert 클립** (spike004 gate_in/invert.mp4, production 기질 9fps/640px, GPU EP):

| 게이트 | 실측 | 판정 |
|---|---|---|
| 검출 | is_inverted=True ratio 0.269 / run 5 / valid 52 | 검출 |
| boneCV 개선 ≥30% | 0.987 → 0.525 = **−46.8%** | **PASS** |
| latency ≤ +60s | 2차 소요 2.97s (내부 계측; replaced 81/81) | **PASS** |
| 좌표 원본 범위 | 전 좌표 유한·bounds 내 | PASS |
| 오버레이 육안 | off(적)/on(녹) 점이 원본 프레임 인체 위 정합 — 워프 공간 누출 0 | PASS |

**(b) power-spin fixture:** fault detect **False** (0.027/run1) · correct **False** (0.013/run1) — 미검출 = 1차 결과 그대로(구조는 배선 테스트가 증명, e2e 는 아래 스윕 diff 0). **PASS**

**fixture 12멤버 검출 프리뷰 (게이트 부속 실측 — GPU EP):**

| member | detect (ratio/run) | boneCV off→on | 개선 | 2차 latency |
|---|---|---|---|---|
| power-spin f/c | **False** (0.027/1 · 0.013/1) | — | — | — |
| peter-pan f/c | False (0.000/0 ×2) | — | — | — |
| elbow-twist f | **True** (0.678/9) | 1.920→0.714 | **−62.8%** | +6.65s |
| elbow-twist c | **True** (0.674/13) | 9.671→2.151 | **−77.8%** | +8.33s |
| pdshape f | **True** (0.705/15) | 10.325→0.746 | **−92.8%** | +7.55s |
| pdshape c | **True** (0.702/11) | 2.169→2.078 | −4.2% | +5.92s |
| kip-up f/c | False (0.000/0 ×2) | — | — | — |
| climb f/c | False (0.000/0 · 0.014/1) | — | — | — |

- **pdshape·elbow-twist = 실측 인버전 동작** (크롭 PNG 육안으로도 역위 확인). kip-up fixture 는 정립(0.000) — "kip-up 거꾸로 계열" 가정은 이 fixture 들에선 불성립 (spike 8s 트림과 동일 실측).
- 게이트 PASS → `PR_INVERSION_ENABLED=1` **production start_server.sh 박제** + 재기동 + `/health` 200 (rollback = 해당 줄 삭제 + 재기동).

## D-23 최종 전수 스윕 (Task 3 — phase 게이트)

- **일시:** 2026-07-22 01:29 ~ 03:07 UTC (98분, SERIAL — [[pipeline-not-concurrency-safe-eval-serial]])
- **runId:** `1784683741` / uid `phase25eval` / Pod `6seluxc43awmqi` (RTX 4090)
- **기질:** run_sweep_3214.sh mirror + `PR_INVERSION_ENABLED=1` (`/workspace/eval32/run_sweep_3215.sh`, CPU EP + rtmw_deterministic=1 — 32-14 기준선 1784676884 와 동일 기질)

### 점수·verdict·criteria (diff_3209.py — 32-14 기준선 대비)

| member | 기준선 → 신규 | 판정 | 원인 (실측) |
|---|---|---|---|
| power-spin fault | 55 → **55** | diff 0 | 미검출 — krBytes 143966 → 143966 **바이트 동일** |
| power-spin success | 100 → **100** | diff 0 | 미검출 — 바이트 동일 |
| peter-pan fault | 79 → **79** | diff 0 | 미검출 — 바이트 동일 |
| peter-pan success | 100 → **100** | diff 0 | 미검출 — 바이트 동일 |
| **elbow-twist fault** | 66 → **65** (−1) | 변화(검출) | right_hip criterion 탈락(20.61°→임계 미만 — 경계 활성 소거) + 좌우 어깨·팔꿈치 ±1~3° 재측정 (아래 표) |
| elbow-twist success | 100 → **100** | 동일(검출) | 2차 적용에도 감점 0 유지 |
| **pdshape fault** | 58 → **46** (−12) | 변화(검출) | left_elbow 24.45°→**33.02°**(−5.3→−15.6) 등 — 결함이 팔로 선명 귀속 (아래 표) |
| **pdshape success** | 100 → **99** (−1) | 변화(검출) | left_knee 21.19° 신규 경계 활성(−1.4) — 95~100 엘리트 밴드 내 |
| kip-up fault | 80 → **80** | diff 0 | 미검출 — 바이트 동일 |
| kip-up success | 100 → **100** | diff 0 | 미검출 — 바이트 동일 |
| climb f/c | gate → gate | diff 0 | comparison gate 동일 (기준선과 동일 정상) |

- **비검출 8멤버: 점수·activatedCriteria·status 완전 일치 + keypointReport 직렬화 바이트 동일** — "미검출 = 기존 경로 바이트 동일" 구조 보장의 e2e 실증.
- diff_3209 의 `DIFF_MEMBERS=3 (FAIL)` 표기는 구(all-diff-0) 의미론 — 32-15 게이트 의미론(비검출 diff 0 + 검출 변화 실측 기록)으로는 **PASS**.

### 검출 멤버 변화 원인 표 (record-level 실측 — 방향·크기·원인)

**elbow-twist fault (66→65):** criteria 7→6 (right_hip 소거)

| criterion | 측정° (기준선→신규) | 감점 (기준선→신규) |
|---|---|---|
| left_elbow | 24.73 → 22.49 | −5.7 → −3.0 |
| left_hip | 22.30 → 23.04 | −2.8 → −3.7 |
| left_knee | 21.86 → 22.75 | −2.2 → −3.3 |
| left_shoulder | 21.18 → 23.67 | −1.4 → −4.4 |
| right_elbow | 31.98 → 31.47 | −14.4 → −13.8 |
| right_hip | 20.61 → **소거** | −0.7 → 0 |
| right_shoulder | 25.66 → 25.62 | −6.8 → −6.7 |

**pdshape fault (58→46):** criteria 동일 7종, 심도 재배분

| criterion | 측정° (기준선→신규) | 감점 (기준선→신규) |
|---|---|---|
| left_elbow | 24.45 → **33.02** | −5.3 → **−15.6** |
| left_hip | 23.73 → 23.28 | −4.5 → −3.9 |
| left_knee | 31.30 → 26.90 | −13.6 → −8.3 |
| left_shoulder | 25.08 → 22.18 | −6.1 → −2.6 |
| right_elbow | 28.27 → 30.61 | −9.9 → −12.7 |
| right_knee | 20.69 → 24.75 | −0.8 → −5.7 |
| right_shoulder | 21.51 → 24.19 | −1.8 → −5.0 |

- **개선 방향 판독:** ① 좌표 기질이 실측으로 대폭 개선 (boneCV: pdshape fault 10.3→0.75 = 사지 길이 요동 13.8배→정상권 — 종전 측정은 오염 기질 위였음) ② **fault/success 분리 확대** — pdshape 42→53, elbow 34→35 (결함 변별력 강화 = core value 방향) ③ 경계값(20°±2) 잡음 활성/소거 2건(elbow right_hip 소거·pdshape success left_knee 활성)은 ±1점 규모 ④ pdshape success 99 는 [[score-spec-95-100-elite-vision-fix]] 95~100 밴드 내.
- **주의(belle 리뷰 사항):** 기준 모션(reference 11종)은 구경로(무 PR) 좌표 — 인버전 동작에서 학생만 보정되는 **비대칭**이 angle_vs_reference 절대값에 섞임 (pdshape fault 심화의 일부 가능성). 후속 옵션 = 인버전 reference 재처리([[reference-v1-pinned-force-config]] pinned 정책과 상충 — belle 결정 필요).

### 결정론·latency·표면 검증

- **결정론 (범위 명기 — 포즈·측정 기질 한정, Gemini 텍스트 산출 제외·캐시 히트 시 동일):** in-run cold 재실행 pdshape success(PR 검출 멤버) = warm 99 / cold **99**, criteria 동일(left_knee), selection_identical=true — 2차 추론 전체 재실행(rtmw 578.2s vs 578.7s) 후에도 측정 결정론 유지.
- **latency:** 비검출 멤버 rtmw stage ±1% 노이즈 (155.4→154.9s 등). 검출 멤버는 스윕(CPU EP·eval 전용 기질)에서 +289~407s — **production(GPU EP, start_server.sh LD_LIBRARY_PATH)은 게이트 실측 +2.97~8.33s ≤ +60s 예산 PASS**. CPU EP 수치는 기준선 비교성 유지를 위한 eval 기질 아티팩트로 기록.
- **keypointReport:** 전 done 멤버 joints **12**·version 1.1·validator **PASS**. 신규 관절 conf 분포(2단 게이트 재료): 비검출 멤버 = 32-14 와 동일, 검출 멤버 = 2차 신뢰도 기준 소폭 변동 (elbow f l_ankle 0.53→0.48 등 — 동작·화질 종속 밴드 유지).
- **spotCheck:** 전 done 멤버 status done · hidden 0 · praiseMismatch false (오숨김 0 정답 분포 유지).
- **크롭 PNG 전수 육안 (21장):** 전 멤버 crop 이 인체 위 정합·줌 쌍 배율 parity 유지 (32-01 수리분). 검출 멤버(pdshape·elbow) crop 도 신좌표 기준 정상 — kip-up 다리 라인 발목 연장(32-14 소비 실현)도 확인.
- **Pod:** 스윕 후 `/health` 200 (내부+proxy) — env on 가동 상태.

## Deviations from Plan

### Auto-fixed / 실측 정정

**1. [Rule 1 - 플랜 대상 파일 정정] 훅 삽입처 = rtmw_engine.py (pose_estimator.py 아님)**
- **Found during:** Task 2 (read_first — 추론 파이프라인 구조 실측)
- **Issue:** 플랜 files_modified 의 pose_estimator.py(NlfPoseEstimator)는 DEPRECATED — 프로덕션 추론은 `_RTMWNlfCompat`→`RTMWPoseEngine` 단일 관문 (NLF 참조는 주석 2곳뿐)
- **Fix:** 훅을 실제 관문 `RTMWPoseEngine.estimate` 에 삽입 — 죽은 경로 무수정
- **Files modified:** rtmw_engine.py — **Commit:** `f3dd6f2`

**2. [실측 정정 - 게이트 분포] "비인버전 5동작" 가정 → 실측 인버전 4멤버/비검출 8멤버**
- **Found during:** Task 1 캘리브레이션 + Task 2 fixture 프리뷰
- **Issue:** 플랜은 비인버전 5동작 diff 0 을 가정 — 실측: elbow-twist(91% 역위)·pdshape(70% 역위)가 인버전 동작 (spike clip 에 pdshape 부재·elbow 는 미열거라 플랜 시점 미지)
- **처리:** 게이트 의미론을 검출 기준으로 적용 — 비검출 8멤버 diff 0 달성 + 검출 4멤버 방향·크기·원인 표 기록 (오케스트레이터 게이트 지시 정합)

**3. [Rule 2 - 관측성] 제한 게이트에 fixture 12멤버 검출 프리뷰 추가**
- **Found during:** Task 2 (스윕 전 fail-fast 필요 판단)
- **Fix:** Gemini 비용 0 인 엔진 레벨 검출 프리뷰로 전수 스윕 전에 검출 분포·boneCV·latency 를 선실측 — 스윕 기대치 사전 고정
- **Files modified:** 없음 (Pod 스크립트 `/workspace/eval32/pr_gate_3215.py` — repo 밖 관례)

**Total deviations:** 3. **Impact:** 전부 실측 정합 — scope creep 0, 채점 코어(각도·감점 산식) 무수정.

## TDD Gate Compliance

- RED `0c9d2eb` (test — collection ImportError 확인 후 커밋) → GREEN `e8dc788` (feat — 15/15). REFACTOR 커밋 불필요. Task 2 배선 테스트 5건은 auto 태스크 산출로 `f3dd6f2` 동승.

## Verification

- `pytest tests/phase32` → **191 passed** (기존 186 + 신규 20 − 15 RED 중복 없음 산술: 파일 신규 20 포함 총 191) / 회귀 selection(phase32+phase12+phase31+rtmw engine+pipeline recognizer) **803 passed, 0 failed**
- 풀-스위트 잔여 12 collection error 는 `backend.research.*` import 의 pre-existing 로컬 결손 (32-13 기록과 동일 — baseline 초과 0. 내 diff 는 research/ 무접촉)
- 채점 코어 무접촉: skeleton/dimensions/kismam/fault_zoom diff 0 (수정 파일 3개뿐 — 전부 추론 어댑터층)
- Pod `/health` 200 (배포 전후·게이트·스윕 후, 내부+proxy) + PR_INVERSION_ENABLED=1 박제 확인
- 스윕: 비검출 8멤버 diff 0(바이트 동일) + 검출 4멤버 실측 표 + validator 전 PASS + spotCheck 정상 + 크롭 육안 + 결정론(측정 한정) + production latency 예산 내
- STATE.md/ROADMAP.md 무접촉 (orchestrator 소관)

## Known Stubs

없음 — 검출·워프·역변환 전부 실좌표 실측 경로. env off 시 코드 경로 자체가 1차 결과 반환(스텁 아닌 기존 경로).

## Threat Flags

없음 — 플랜 threat register 4건 전부 mitigate 이행: T-32-37(오검출 워프) = 지속성 휴리스틱 + spike FP0 + 비검출 바이트 동일 + env 게이트, T-32-41(역변환 누락) = round-trip 테스트 + 프레임 fail-safe + 오버레이 육안, T-32-38(스윕 오염) = SERIAL + fixture 계정 한정, T-32-39(게이트 주장) = 본 SUMMARY 수치 표 + belle checkpoint.

## 산출물 (Pod, repo 밖 — baseline 무접촉 관례)

`/workspace/eval32/pr/phase25/phase25_sweep_report.json` + `pr_docs.json` + `pr_sweep.log` + `pr_gate_report.json` + `pr/crops/*.png`(21) + `pr/invert_overlay_*.png`(3) + `run_sweep_3215.sh` / `pr_gate_3215.py` / `compare_3215.py` / `fetch_spot_3215.py` (로컬 사본 /tmp/prcrops/, /tmp/invert_overlay_*.png)

## Next / belle 확인 대기 (checkpoint)

1. **스윕 결과 표 승인** — 특히 pdshape fault 58→46 (fault 변별 강화 vs reference 비대칭 해석), pdshape success 99 (95~100 밴드 내), elbow fault 66→65.
2. **PR on/off 최종 상태** — 현재 production **on** (게이트 PASS 근거). off 원복 = start_server.sh 한 줄 삭제 + 재기동.
3. **reference 재처리 후속 트랙** — 인버전 동작(elbow-twist·pdshape 등) 기준 모션을 PR 경로로 재추출할지 (pinned 정책과 상충 — belle 결정).
4. **D-22 짚기 정밀화 = 스팟체크 사후 검수 갈음 해석 확인 (W-3).**
5. **2단(신규 관절 감점 편입) 판단** — conf 분포 재료 기준 후속 결정 (이 phase 범위 밖).
6. 잔여 실기기 항목 = 32-HUMAN-UAT.md §E 적립.

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/inversion_warp.py
- FOUND: backend/tests/phase32/test_inversion_warp.py
- FOUND: .planning/phases/32-result-readability-3-omni/32-15-SUMMARY.md
- FOUND commits: 0c9d2eb / e8dc788 / f3dd6f2 (git log 확인)
- 파일 삭제 0 (커밋 3건 전부 add/modify만)
- Pod HEAD f3dd6f2 = origin/main, /health 200(내부+proxy), PR_INVERSION_ENABLED=1 박제, 스윕 산출물 Pod 존재 확인

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-22*
