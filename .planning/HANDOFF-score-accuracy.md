# Handoff — Score Accuracy Comprehensive Upgrade

**작성:** 2026-06-12
**다음 진행:** `/gsd-plan-phase` 로 phase `score-accuracy-comprehensive` 시작

---

## 배경

belle UAT 검증 결과:
- 같은 정은지 두 촬영본 비교 (talkv-elbow-twist vs ref-elbow-twist-sister) → angle dim **69점** (median fix 후)
- belle 기대: 같은 정은지 = **95~100점**

belle 의 원칙 (rejection 후 확정):
1. 우회 (tol 완화 / UX 메시지) 금지 — 객관 측정 정확도로 가야 함
2. tol 완화 불가 (KISMAM tol=20° 유지)
3. 같은 영상 = 95+ 가 정상
4. Phase 18 (새 백본) 미루기 불가 — 현재 architecture 안에서 해결
5. 시간/비용 무관, 정확도 최우선
6. Gemini Vision 점수 path 에 활용

진단:
- `bodyNormalizationProfile.confidence: 0.40`, warnings `pose_too_inverted` + `occluded_endpoint`
- per-joint median |Δ| 13~21° (8 관절 전부 같은 방향 = systematic bias)
- 원인: RTMW 가 inverted 자세에서 카메라각/라이팅 의존
- Gemini Vision 현재 점수 path 에 미사용 (Phase 17 = recognizer + coach 만)

---

## 자체 검증 게이트 (8개, 모두 PASS 시만 belle Xcode 검증 요청)

1. talkv-elbow-twist vs ref-elbow-twist-sister → angle dim ≥ 95
2. talkv-climb vs ref-climb → angle dim ≥ 95 (regression 0)
3. talkv-powerspin vs ref-power-spin → 95+
4. 다른 trick / 잘못된 자세 → 50 이하 정직 (객관성 유지)
5. 화면 "측정 불가" 알림 0회 (`jointAssessments.isEstimated` = 0)
6. 8 관절 전부 점수/deviation 표시 (missing 0)
7. 코칭팁 Gemini 자연어 (KISMAM numeric fallback 0)
8. 자세한 내용 (관절별 deviation/근거) 명확

테스트 데이터:
- talkv-elbow-twist: `_talkv_dJMcaL4ZHKA_yX7uPsCsGTncpdNrFlHTk1_talkv_high.mp4` (정은지)
- talkv-climb: `_talkv_wzPWR5bAZW_JD6AkSr0ugQLxy7qblpdnk_talkv_high.mp4` (정은지)
- talkv-powerspin: `_talkv_dJMcaItFttI_jwDiWGkuWNohoQqLkUykP0_talkv_high.mp4` (정은지)
- uid: `csKWYvI3WCPYPysNQ9KkWecaUvq1`

---

## 스코프 (5 stage)

| Stage | 목적 | 핵심 | 예상 |
|---|---|---|---|
| A | RTMW confidence Firestore 저장 | per-frame per-joint conf | ~2h |
| B | Gemini-anchored DTW | key moment timestamps → DTW anchor | ~4h |
| **C** | **Gemini per-pose 시각 점수** | **점수 path 에 Gemini 직접 박힘 (핵심)** | ~6h |
| D | Multi-reference ensemble | 정은지 take 2~3개 best match | ~4h |
| E | Gemini holistic verifier | edge case sanity check | ~3h |

총 ~19h. (Stage F IPSF gates 는 다음 phase 보류 — ~5h)

---

## 진행 — 단계별 Xcode 검증 (belle 박힌 박힌)

### Iteration 1 (~12h) — Stage A + B + C
- 자체 검증 8 게이트 → 모두 PASS → Pod 배포 → belle Xcode 검증
- PASS → 끝
- FAIL → Iteration 2

### Iteration 2 (~7h 추가) — + Stage D + E
- 자체 검증 → Pod 배포 → belle Xcode 검증
- PASS → 끝
- FAIL → Iteration 3

### Iteration 3 (?h) — Mirror handling + 기술 핸들링
- belle 명확화 (2026-06-12): "phase13 을 진행하란 소린 아니었고, 그거나 phase 남은거에서 같이 수정해야할 거 (예: 카메라 앵글 개발 측) 면 거기서 해도 된다"
- 즉 Phase 13 시작 X. 후속 phase 에 묶어 처리:
  - 좌/우 mirror handling (memory `phase-12-tomorrow-bcd-then-13a` = Phase 13 A deferred)
  - 카메라 앵글 single-view (memory `camera-angle-ai-single-view-synth` = Phase 4 redesign)
- Iteration 3 진입 시점에 belle 와 어느 phase 에 묶을지 결정

---

## Plan 검증 — 외부 cross-AI review 필수

belle 박힌 박힌 (2026-06-12): 이 정도 큰 변경은 외부 plan 리뷰 거쳐야 함.

- memory `cross-ai-plan-review-good`: Codex/gpt-5.5 plan-review-convergence 큰 plan 후 권장
- memory `codex-reviewer-smplx-bias`: 종료 시점 = belle 의 "그냥 반영하고 가자" 신호
- 사용 skill: `/gsd-review` 또는 `/gsd-plan-review-convergence`

### 자동 진행 (belle 잠자는 동안)
1. PLAN.md draft (~1h)
2. `/gsd-review` Codex 1~3 round (~1~2h)
3. HIGH concern 0 → 자동 진행 (Iteration 1 execute 시작)
4. HIGH concern 남음 → 잠 깬 belle 박힌 박힌

### belle 깰 때 보일 상태 (2가지)
- A. plan + review 깨끗 → Iteration 1 execute 진행 중 또는 완료 → **TestFlight 검증 박힌**
- B. plan HIGH concern 남음 → belle 박힌 박힌 박힌 박힌

---

## 기 완료 작업 (이 phase 진입 전)

1. `motiondtw.per_joint_deviation` mean → median (commit `cd11f21`)
   - 실측 (정은지 두 영상): 58 → 69 (+11)
   - 합성 예측보다 작은 폭 — RTMW noise 가 비대칭이라 median 으로도 못 잡는 systematic bias 발견
2. Lambda 배포 완료 (sunity-motion-pilot, 2026-06-12 13:20)
3. Pod 재시작 + AWS credentials + Gemini recognizer 활성
4. debug session `same-video-score-mismatch` → status: resolved

---

## Pod 상태 (다음 세션 진입 시)

- IP: `38.65.239.17` port `19360`
- SSH: `~/.ssh/id_ed25519`
- Workspace: `/workspace/SunityMotion` (main HEAD = `cd11f21` 박힌 박힌 추가 commit)
- env (다음 재시작 시 명시 export):
  - `RUNPOD_AUTH_TOKEN=59801424ce0960d8b2fba39afb8751a4fbfe88a67dac1c02d170b29121b07405`
  - `RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx`
  - `YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx`
  - `RTMW_DEVICE=cuda`
  - `LD_LIBRARY_PATH` = cuDNN/cublas python 경로
  - `FIREBASE_SA_PATH=/workspace/firebase-sa.json`
  - `AWS_PROFILE=sunity-motion` (`/root/.aws/credentials` 박힘)
  - `RECOGNIZER_BACKEND=gemini`
  - `GEMINI_API_KEY` = SSM `/sunity/motion/gemini-api-key`
- Pod URL: `https://z3fy82pjgu4mga-8000.proxy.runpod.net`
- Gemini billing: belle 가 spending cap 올림 (2026-06-12 박힘)

---

## 다음 세션 즉시 명령

```
/gsd-phase add
  name: score-accuracy-comprehensive
  goal: 같은 정은지 두 촬영본 비교 시 angle dim ≥ 95 (8 게이트 PASS)
  scope: Iteration 1 (A+B+C) 시작 → belle Xcode 검증

/gsd-plan-phase
  iteration 1 만 plan (A+B+C)

/gsd-review
  Codex cross-AI iteration until no HIGH concern

/gsd-execute-phase
  autonomous

자체 검증 8 게이트 → 모두 PASS → Pod 배포 → belle Xcode 검증 요청
```
