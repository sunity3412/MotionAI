---
phase: 1
slug: poseengine-mediapipe-nlf-r-d
reviewer: Claude Code (fresh context, independent session)
reviewed: 2026-05-31
verdict: NEEDS_REPLAN
high_count: 5
medium_count: 5
low_count: 2
---

# Phase 1 — Cross-AI Independent Review

> 다른 Claude Code 세션에서 fresh-context로 6 plans 정밀 리뷰. Sonnet plan-checker가 통과시킨 plans에 대해 locked decisions·실제 코드 정합성·downstream cascade 사각지대를 점검.

## 총평

현 계획만으로 Phase 1의 큰 구성요소는 대부분 커버됨. **다만 그대로 승인 금지** — 핵심 사유는 D-08/D-16 순서 위반. 현재 Plan 05에서 atomic swap을 먼저, Plan 06에서 검증인데, locked decision은 "회귀 검증 통과 후 swap".

---

## HIGH

### H-1: D-08/D-16 위반 — atomic swap이 회귀 검증보다 앞에 있음

**Locked:** 01-CONTEXT.md:49 "MediaPipe 구현 완성 + 회귀 검증 통과 후 atomic swap"
**Current:** Plan 05(Wave 3) swap 완료 후 Plan 06(Wave 4) 검증. Plan 06 실패 시 "git revert 또는 NLF 임시 복귀" 명시.
**Conflict:** D-16의 "swap 안 됐으니 제품 회귀 없음" 전제와 정면 충돌.

**근거:**
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md:49`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-05-PLAN.md:45`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-06-PLAN.md:192`

**Fix 방향:**
- Wave 2: 01-06 (compare_engines.py + belle checkpoint) — NLF/MediaPipe 둘 다 살아있을 때 비교
- Wave 3: 01-04 + 01-05 (belle 승인 후 격리 + atomic swap 같은 wave에서 한 번에)
- 또는 Plan 06이 NLF를 옛 위치(`sunity_shared/analysis/pose_estimator.py`)에서 import 가능한 상태에서 비교 → belle 승인 → swap

### H-2: Plan 05의 Lambda fail-fast가 module import 단계에서 깨질 수 있음

**Issue:** ARM64 mediapipe 미지원은 fail-fast로 처리하려 하지만, Plan 05는 `pipeline/app.py` 상단에 `HoughPoleDetector` / `MediaPipePoseEngine` import를 추가하라고 함. Plan 03 detector는 `cv2`를 module-level import, adapter/aligner도 `scipy` import 조기 발생 여지 있음.

**Risk:** Lambda가 RunPod 위임만 하더라도 `pipeline/app.py` import 자체가 실패. fail-fast는 import 이후 단계여야 작동.

**근거:**
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-RESEARCH.md:149` (Pitfall 1)
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-05-PLAN.md:91`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-03-PLAN.md:93`

**Fix 방향:**
- 새 heavy deps import는 전부 `_ensure_adapters()` 내부 lazy import로 내리기
- detector/aligner도 module-level `import cv2`/`import scipy` 금지 → 클래스 `__init__` 또는 첫 호출 시점에 lazy
- acceptance_criteria에 `python -c "from backend.functions.pipeline.app import lambda_handler"`가 mediapipe·cv2·scipy 미설치 환경에서도 성공해야 한다고 명시

### H-3: PoleAxis 메타가 PoseFrame 계약에서 빠져 D-12/Success #3이 불완전

**Locked:** D-12 = raw + pole-aligned 둘 다 + PoleAxis도 메타로 저장
**Current:** Plan 01은 PoleAxis 타입은 만들지만 PoseFrame 필드에는 `pole_axis`/`poleAxis` 없음. Plan 05도 결과 문서의 pole confidence 표기 deferred.
**Impact:** 후속 phase가 "수직 fallback / low confidence" 알 수 없음.

**근거:**
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md:55`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-01-PLAN.md:104`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-05-PLAN.md:127`

**Fix 방향:**
- Plan 01 `PoseFrame` 필드에 `poleAxis: PoleAxis | null` 추가 (Python + TS + contract.md 3-way)
- Pipeline 결과에 PoleAxis 메타 정보 (axis vector, confidence, source) 보존
- Plan 05 acceptance에 "분석 결과 doc에 poleAxis 필드 존재" 추가

### H-4: Success #4 "추정 표기 + 후속 분석 단정 금지"가 계산까지만, 게이트가 닫히지 않음

**Locked:** ROADMAP Phase 1 Success #4 + D-05 "각도 low reliability 마킹, 과분석 금지, 고객 기술용어 노출 금지"
**Current:** Plans는 confidence/uncertainty 계산은 함. 저신뢰 프레임/각도에 "estimated/low reliability" 남기는 필드나 downstream over-analysis 차단 기준 없음.
**Impact:** Success #4 미달성.

**근거:**
- `.planning/ROADMAP.md:63`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md:38`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-01-PLAN.md:91`

**Fix 방향:**
- PoseFrame에 frame-level `reliability: 'high' | 'medium' | 'low'` 필드 추가
- 각도(angle) 산출 코드(features.py 또는 신규 wrapper)에 "필수 keypoint가 저신뢰면 각도 자체에 `low_reliability=True` 마킹" 게이트 추가
- 고객 리포트(downstream coach_writer)에 기술 용어 노출 금지 정책 일관 적용 검증 (Phase 1 범위에서 최소 contract.md에 명시)

### H-5: NLF 격리 acceptance가 100% enforce되지 않음

**Issue:** Plan 04 action에는 `_nlf_smoke.py`, `verify_nlf_overlay.py` 이동 언급. **frontmatter/acceptance에는 빠짐**. 현재 repo에 둘 다 존재 + NLF/YOLO 직접 참조.
**Risk:** 실행자가 acceptance만 따르면 NLF 스크립트가 `backend/scripts/`에 남음.

**근거:**
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-04-PLAN.md:125`
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-04-PLAN.md:149`

**Fix 방향:**
- Plan 04 frontmatter `files_modified`에 `backend/scripts/_nlf_smoke.py`, `backend/scripts/verify_nlf_overlay.py` 명시
- acceptance_criteria에 `! test -f backend/scripts/_nlf_smoke.py && ! test -f backend/scripts/verify_nlf_overlay.py` 추가
- `ls backend/scripts/ | grep -iE "nlf|yolo"` 결과 빈 줄 검증

---

## MEDIUM

### M-1: D-05 필드명 정확성 (raw_visibility / raw_presence)

**Locked:** D-05 = `raw_visibility`, `raw_presence`, `confidence`, `uncertainty_proxy` 모두 별도 저장
**Current:** Plan 01은 `visibility`, `presence`로 계약화 (raw_ prefix 없음).
**Fix:** PoseFrame 필드명을 `raw_visibility`, `raw_presence`로 정확히 맞춤. TS도 `rawVisibility`, `rawPresence`.

**근거:** `01-CONTEXT.md:40`, `01-01-PLAN.md:99`

### M-2: D-11 `confidence='low'` 타입 일관성

**Locked:** D-11 = PoleAxis 검출 실패 시 `confidence='low'` 표기
**Current:** Plan 03이 numeric 0.3 + `source` 필드로 대체.
**Fix:** `confidenceLevel: 'low'|'medium'|'high'` enum 필드 또는 `warningCode` 별도 필드. 후속 UI/리포트가 string 분기 쓰기 안전.

**근거:** `01-CONTEXT.md:54`, `01-03-PLAN.md:78`

### M-3: 폴 확장 `grip` landmark 계약 모호함

**Locked:** D-04 = toe·heel·grip 확장
**Current:** Plan 02는 heel/foot_index/pinky/thumb 중심. `left_grip`/`right_grip` 산출 계약 없음.
**Risk:** 후속 grip 분석(P2/P3 phase) 생기면 계약 다시 흔들림.
**Fix:** Plan 02에 `pole_grip_left`, `pole_grip_right` (MediaPipe 33 인덱스 pinky+thumb 평균 또는 wrist proxy) 명시. A2 belle 확정 항목과 묶기.

**근거:** `01-CONTEXT.md:37`, `01-02-PLAN.md:87`

### M-4: RunPod README 잔여 NLF 참조

**Issue:** Plan 05는 `setup.sh`는 바꾸지만 `backend/runpod_inference/README.md`는 `files_modified`에 없음. 현재 README에 `NLF_MODEL_PATH`와 Pod 운영 메모 남음.
**Risk:** 배포 운영자가 잘못된 셋업 따를 수 있음.
**Fix:** Plan 05 `files_modified`에 README.md 추가 + NLF 관련 섹션 MediaPipe로 갱신 acceptance.

### M-5: docs/contract.md ↔ TS `angles` shape 불일치 방치

**Issue:** docs/contract.md는 `angles?: number[][]`, TS는 flat `number[]`.
**Current:** Plan 01이 PoseFrame만 추가 → "3-way lockstep 문화"는 선언되지만 기존 핵심 계약 불일치는 남음.
**Fix:** Plan 01 또는 별도 task로 docs/contract.md `angles` shape를 TS 실제(flat) + Firestore 저장 방식(flat + anglesJointKeys + anglesFrames)에 맞춰 동기화.

**근거:** `docs/contract.md:123`, `app/src/types/analysis.ts:152`

---

## LOW

### L-1: ROADMAP Success #3 wording vs D-10

**Issue:** Roadmap Success #3은 "frame별 PoleAxis", D-10은 "영상 전체 평균 축 1개".
**Current:** Plan 03은 D-10을 따르므로 방향은 맞음.
**Fix:** Roadmap 문구를 "video-level PoleAxis를 모든 frame에 적용"으로 정리.

**근거:** `ROADMAP.md:62`, `01-CONTEXT.md:53`

### L-2: Plan 06 실행 경로 vs RunPod setup 문서

**Issue:** Plan 06 실행 경로 `/workspace` 기준. 기존 RunPod setup 문서는 `/workspace/SunityMotion/backend` 기준.
**Fix:** 실제 Pod 경로와 `python -m backend.research...` import 경로 하나로 고정.

---

## 판정

| 기준 | 결과 |
|------|------|
| 1. Success Criteria 6개 plans 합산 달성 | 부분 달성 가능, **HIGH 수정 필요** |
| 2. D-01~D-16 16개 locked decisions 반영 | 대부분 반영, **D-08/D-12/D-05/D-11 불완전** |
| 3. ARM64 pitfall 처리 | 인지했지만 **Plan 05 import 위치 때문에 fail-fast 깨질 위험** |
| 4. NLF atomic swap 11개 라인 enforce | **전부 enforce 안 됨** (HIGH #5) |
| 5. PoseFrame 3-way lockstep | 있음 (단 PoleAxis 필드 누락 — HIGH #3) |
| 6. Wave 순서 합당 | **D-08 기준 부적합** (HIGH #1) |
| 7. Sonnet plan-checker 사각지대 | "검증 전 swap", "Lambda module import crash", "PoleAxis/low reliability 메타 미보존" |

**최종 판정: NEEDS_REPLAN** — `/gsd:plan-phase 1 --reviews`로 본 리뷰 반영해 6 plans 재작성 권장.

## 우선순위 (replan 시 반드시 반영)

1. **Wave 구조 재조립 (H-1)** — Wave 2 = compare_engines (NLF/MP 공존 상태), Wave 3 = isolation + swap atomic
2. **Lazy import 강제 (H-2)** — 모든 heavy deps `_ensure_adapters()` 내부로
3. **PoseFrame 필드 보강 (H-3, H-4, M-1, M-2)** — poleAxis, reliability, raw_visibility/raw_presence, confidenceLevel
4. **NLF 격리 acceptance 강화 (H-5)** — files_modified + grep 검증
5. **MEDIUM/LOW는 같은 replan turn에 함께 정리**
