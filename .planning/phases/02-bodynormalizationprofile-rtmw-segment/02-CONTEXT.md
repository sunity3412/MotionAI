# Phase 2 CONTEXT — BodyNormalizationProfile 자동 측정 (RTMW segment 기반)

> **Goal restated**: RTMW 133 wholebody 키포인트로부터 신체 segment 길이 (상완·전완·대퇴·하퇴·몸통, 어깨/골반 폭) 및 비율을 산출해 `BodyNormalizationProfile` (estimatedHeightScale, armScale, legScale, torsoScale, shoulderHipRatio, confidence, warnings) 을 자동 출력한다 — 두 엔진 (체형 보정 + 힘 방향 패턴) 의 공유 입력.

---

## 1. Scope (in / out)

### In scope (v1)

| 항목 | 산출 |
|---|---|
| segment 길이 추출 | RTMW 키포인트 → 상완·전완·대퇴·하퇴·몸통 길이 (px → frame normalize) |
| segment 비율 산출 | shoulder width / hip width / arm-to-torso ratio / leg-to-torso ratio |
| 시간 평균 + 안정화 | 프레임별 jitter 스무딩 (moving average 또는 robust median) |
| confidence | segment 별 confidence 집계 (keypoint conf × visibility) |
| warnings | low conf / occlusion / missing landmark 사유 표기 |
| 데이터 contract 3-way lockstep | `BodyNormalizationProfile` 타입 — `analysis.ts` ↔ `models.py` ↔ `contract.md` |
| R&D 비교군 (선택) | NLF → SMPL-X β 추출 BodyProfile vs RTMW segment 산출 갭 보고서 (제품 코드 비호출) |

### Out of scope (v1)

| 항목 | 사유 |
|---|---|
| Phase 3 자가입력 BodyProfileInput | belle 결정 — 자가입력은 보조, 자동 측정 우선 |
| BodyProfile 의 다운스트림 활용 (체형 정규화 비교) | Phase 6 에서 |
| 좌우 비대칭 자동 결정 | confidence/warnings 만 v1, 비대칭 자체 활용은 Phase 7 |
| 다각도 입력 통합 | Phase 4 |
| SMPL-X β 본격 도입 | R&D 비교군만, 상업 라이선스 X |

---

## 2. Dependencies (verified)

### Upstream

| Phase | 상태 | 산출 사용 |
|---|---|---|
| Phase 1 (PoseEngine + RTMW 133) | [x] close-out (commit 2a8aa72 swap) | `PoseEngine.run(video) → PoseFrame[]` — RTMW 키포인트가 폴 축 정렬된 좌표계로 제공 |

### Downstream (Phase 2 가 unblock 하는 것)

| Phase | 사용 방식 |
|---|---|
| Phase 6 (체형 정규화 비교 엔진) | `normalizeStudentPoseToProReference` 에서 학생 / 프로 BodyProfile 차이로 segment scale 재계산 |
| Phase 7 (차이 분류) | 체형 허용 차이 임계값 산정에 BodyProfile 사용 |
| Phase 8/9 (힘 패턴) | 중심축/접촉점 정규화에 segment 비율 사용 |
| Phase 12 (실측 각도 + 키포인트 오버레이) | 키포인트 정규화 좌표계 사용 |

---

## 3. Requirements

### BODY-01 (v1)

> RTMW 키포인트로부터 신체 segment 길이·비율·좌우 비대칭이 자동 추출되어 `BodyNormalizationProfile`(키·팔/다리/몸통 스케일·어깨/골반 비율·confidence·warnings)이 두 엔진의 공유 입력으로 산출된다. SMPL-X β 비교군은 R&D 평가 스크립트에서만 갭 보고 (제품 코드 비호출).

(REQUIREMENTS.md line 30 — Phase 1 RTMW pivot 후 "MediaPipe" → "RTMW" 정합 필요. PLAN 작성 후 동시 갱신.)

---

## 4. Success Criteria (from ROADMAP)

1. RTMW 키포인트에서 segment 길이가 시간 평균으로 안정적으로 추출된다 (jitter 스무딩)
2. `BodyNormalizationProfile` 이 키·팔/다리/몸통 스케일·어깨/골반 비율·confidence·warnings 로 산출된다
3. 낮은 confidence (가림·저화질) 시 단정하지 않고 warnings 배열에 사유가 표기된다
4. R&D 비교군: 동일 영상에서 NLF→SMPL-X β로 추출한 BodyNormalizationProfile 과의 갭을 보고서로 출력 (제품 코드 비호출, 평가 전용)
5. 데이터 계약 (`analysis.ts` ↔ `models.py`) 에 `BodyNormalizationProfile` 타입이 lockstep 으로 추가된다

---

## 5. Locked Decisions (codify in PLAN)

| ID | Decision | Source |
|---|---|---|
| D-02-01 | RTMW 133 wholebody (Apache-2.0) 운영 백본 — MediaPipe X, NLF/SMPL-X R&D 만 | belle 2026-06-02 pivot, ROADMAP line 57 |
| D-02-02 | 데이터 contract 3-way lockstep 필수 (TS / Python / docs/contract.md) | 프로젝트 규칙 (CLAUDE.md cross-cutting) |
| D-02-03 | confidence/warnings 항상 출력 — 단정 금지 | CoachCommentHook 원칙, ROADMAP §1 |
| D-02-04 | SMPL-X 상업 라이선스 X — R&D 비교군 비공개 평가만 | belle 2026-05-31, ROADMAP §1 |
| D-02-05 | 자동 측정 우선, Phase 3 자가입력은 보조 | belle 2026-06-07 |
| D-02-06 | Phase 12.5 segment 시뮬 fixture (시뮬) 와 별개로, 실 영상 BodyProfile 산출만 v1 scope | Phase 12.5 close-out 정합 |

---

## 6. Open Questions (researcher 가 답해야)

1. **RTMW 133 키포인트 중 어떤 keypoint set 으로 segment 측정?** — COCO-17 subset 또는 wholebody 133. 안정성 vs 정확도 tradeoff
2. **jitter 스무딩 알고리즘** — moving average (단순) vs robust median (이상치 제거) vs Kalman filter (시간 모델링). 비용 vs 정확도
3. **segment 길이 normalize 단위** — 픽셀 그대로 vs 영상 frame 크기 비율 vs 폴 축 길이 비율 (Phase 1 PoleAxis 활용). 카메라 거리 / 해상도 무관 보장
4. **confidence 집계 방식** — segment confidence = min / mean / median (keypoint conf × visibility). low conf threshold 결정 근거
5. **R&D 비교군 (NLF→SMPL-X β) 평가 스크립트** — input/output 형식, 어디서 실행 (RunPod / 사내 노트북), 산출 보고서 형식
6. **테스트 fixture** — 실 영상 sweep 박제 (예: cocktail13 sweep_rtmw_20260603_1409) 의 keypoint 데이터 재사용 vs 새 fixture

---

## 7. Memory Refs (정합 확인)

- [`runpod-gpu-env`] — Pod 환경 함정 (RTMW + YOLOX HF mirror 등)
- [`rtmw-free-stack-pivot`] — RTMW Apache-2.0 단일 백본 결정
- [`rtmw-clean-weight-release-gate`] — 상업 출시 전 commercial-friendly weight 교체 필수
- [`license-blocklist-pose`] — SMPL-X 상업 불가 (R&D 만)
- [`analysis-objectivity-no-human-scores`] — 사람 점수 라벨링 영구 금지
- [`mvp-simple-pilot-quality`] — MVP 단순 + 실증 quality

---

## 8. Acceptance Format (planner 가 PLAN.md 에 반영)

각 Plan task 는:
1. **Goal** (한 줄)
2. **Input / Output 데이터 형식** (구체적 — TS interface / Python dataclass)
3. **Implementation file path** (구체)
4. **Test 전략** (pytest + fixture or e2e)
5. **Success gate** (메트릭 또는 어떤 assertion 통과)

contract 3-way lockstep task 는 반드시 한 atomic commit 으로 묶음 (TS + Python + docs/contract.md 동시 변경).
