---
slug: keypoint-drift-fps-label
status: fixed
trigger: belle UAT 3차 (TestFlight Build 13) — keypoint 가 사람을 안 따라가고 영상 중앙에 들러붙음. 영상 끝부분에 keypoint 가 종료 자세로 정지. 사용자 영상의 keypoint 가 정은지 영상 자세와 유사한 모양으로 표시.
created: 2026-06-11
updated: 2026-06-11
---

# keypoint-drift-fps-label

## Symptoms

- **Expected**: 두 영상 (사용자, 정은지 reference) 의 keypoint 오버레이가 영상 안 사람을 정확히 따라가야 함. 영상 진행 중 사람 움직임에 맞춰 keypoint 도 같이 이동.
- **Actual**:
  - frame 0 (시작 시점) keypoint 는 사람과 거의 일치
  - 시간 진행할수록 keypoint 가 사람과 어긋남. 12-15초 시점에 사람과 완전히 다른 위치 (영상 중앙 폴 부근)
  - 영상 끝 ~1-2초 동안 keypoint 가 종료 자세로 정지
  - belle 의 인상: "키프레임이 프로 영상 기준이 된 듯"
- **Error messages**: 없음 (시각적 finding 만)
- **Timeline**: TestFlight Build 12 (UAT 2차, 2026-06-10) 부터 보이기 시작. Build 13 (UAT 3차, 2026-06-11) 에서도 동일. 빌드 11 까지는 keypoint 자체가 없었음 (Phase 12 신규 기능).
- **Reproduction**: 분석 결과 화면 → "동작 비교" 토글 ON → 두 영상 동시 재생 → 시간 진행 관찰.

## Root Cause (confirmed by fable review)

`12-KEYPOINT-DRIFT-ROOT-CAUSE-REVIEW.md` 의 진단 채택. 좌표가 아닌 **시간축 문제**.

`FfmpegFrameExtractor` 가 `step = max(1, round(src_fps / target_fps))` 로 정수 양자화 → **실효 fps = src_fps / step ≠ target_fps**. 그런데 `build_keypoint_report` 호출부가 **target_fps (요청값)** 을 라벨로 박음. `KeypointOverlay` 의 `frameIndex = floor(currentTime × keypointReport.fps)` 가 거짓 라벨로 산출 → 시간 진행할수록 drift.

오차 공식: **표시되는 포즈의 실제 시점 = t × (fps라벨 / fps실효)**

belle 영상 (24fps, target 9→upsample 18):
- step = round(24/9) = 3 → 실효 8fps → ×2 upsample = 실효 16fps
- 라벨 = 18 (요청값)
- 라벨/실효 = 18/16 = 1.125 → 12.5% 빠르게 진행
- T-1 도달 시 clamp → 영상 끝 ~1.9s freeze

Reference (30fps, target 18):
- step = round(30/18) = 2 → 실효 15fps
- 라벨 = 18 → 라벨/실효 = 1.20 → 20% 빠름

### Evidence

- 6영상 전수 검증 (reference 5 + 사용자 1): JSON.frames / ffprobe duration = 예측값과 소수점 셋째 자리까지 일치
- Pod 에서 RTMW + YOLOX raw output 직접 시각화 (frame 단위 추론) → keypoint 좌표 자체는 사람 위에 정확. 시간 매칭만 어긋남.
- 사용자 UAT 영상 = ref-climb 의 re-encode (406×720/24fps, 17.125s). "사용자 keypoint 가 정은지 자세 같다" 의 진짜 원인 = 콘텐츠 동일성 (data swap 아님).

### Eliminated hypotheses

| # | 가설 | 기각 근거 |
|---|---|---|
| 1 | RTMW 가 사람 아닌 객체 detect | Pod raw 추론 시각화 — bbox + keypoint 모두 사람 위에 정확 |
| 2 | YOLOX 가 식물/그림자 사람으로 오인식 | bbox[1] (식물) 은 있지만 rtmw_engine 은 `kps_batch[0]` 만 사용. bbox[0] = belle 정확 |
| 3 | 좌/우 mirror (12-A) 영향 | 12-A 는 좌/우 라벨 swap. 본 finding 은 (x,y) 자체 어긋남. 별개 |
| 4 | 사용자 ↔ reference 데이터 swap | result.tsx 배선 정상 (left=keypointReport, right=referenceKeypointReport). seed 도 motionId 키 정상 |
| 5 | SVG viewBox / preserveAspectRatio | 현재 콘텐츠 9:16 only → 발화 X. 휴면 결함 별도 박제 |
| 6 | 시작 시점 비동기 (정은지 영상 buffer) | Image 17 의 0:03/0:03 동기화 시점에도 drift 존재 — 단순 동기화 문제 아님 |

## Fix (proposed)

### Fix A — 앱 hotfix (즉시 적용, 기존 데이터 그대로 구제)

`app/src/components/KeypointOverlay.tsx` 의 frameIndex 산출:

```tsx
// BEFORE
const fps = keypointReport.fps > 0 ? keypointReport.fps : 1;
const idx = Math.floor(currentTime * fps);

// AFTER
const duration = (player?.duration ?? 0);
const effectiveFps = duration > 0
  ? keypointReport.frames / duration
  : keypointReport.fps;
const idx = Math.floor(currentTime * effectiveFps);
```

- 검산: belle 영상 274 / 17.125 = 16.0 (실효와 일치), reference 257 / 17.078 = 15.05 (일치)
- 백엔드 재추출 / Firestore reseed 불필요 — 기존 데이터 즉시 복구
- Fix B 배포 후에도 무해 (frames/duration == 라벨 박힘 시 동일 결과)

### Fix B — 백엔드 근본 (후속)

`FfmpegFrameExtractor` 가 실효 fps (src_fps / step) 도 반환 + 호출부 2곳 (pipeline/app.py, extract_reference_keypoint_reports.py) 이 그 값을 라벨로 사용. 다음 신규 분석부터 라벨 정직.

### 추가 박제 (별도)

- jerk fps³ 스케일 영향 (fable §6-2): `_compute_jerk` 가 거짓 라벨 fps 사용 → 카메라 fps 가 점수에 누설. 점수 영향 평가 후 별도 fix.
- SVG letterbox 휴면 결함 (fable §9-1): 가로/4:3 영상 업로드 시 발화. UI 후속.
- belle UAT 가이드: 본인 촬영 영상으로만 검증 (ref-climb re-encode 업로드 회피).

## Verification plan

1. **앱 t=0/중간/끝 3점 체크**: t=0 keypoint 사람 위 (현재도 OK), 중간 재생 중 따라감, 영상 끝까지 freeze 없음
2. **자동 정합**: `report.frames / report.fps` vs ffprobe duration 비교 — 오차 < 1 frame
3. **단위 테스트**: 합성 fps 매트릭스 (24/30/60fps × target 9/18) 에서 라벨 == src_fps/step 검증
4. **belle UAT 4차**: TestFlight Build 14 → 학원에서 실 영상 분석 → 4 체크 시나리오 (B/C/D + keypoint drift 해소)

## Current Focus

hypothesis: KeypointOverlay 가 fps 라벨 (target_fps) 로 frame index 산출 → 실효 fps (src_fps/step) 와 차이만큼 시간 진행할수록 drift 누적. Fix A (frames/duration 으로 실효 fps 산출) 로 해결 가능.

test: Fix A 적용 후 belle 영상 + reference 양쪽에서 t=0 / 중간 / 끝 시점 keypoint 가 사람 위 유지되는지

expecting: Fix A 적용 후 drift 0 — frame_index = floor(currentTime × frames/duration) 이므로 currentTime=duration 시점에 idx=frames-1 정확히 도달

next_action: belle TestFlight Build 14 UAT 4차 — 영상 끝까지 keypoint 가 사람 따라가는지 확인

reasoning_checkpoint: fable 진단 + Pod raw 시각화 + 6영상 전수 ffprobe 검증 모두 정합. 가설 5/6 다 기각. Fix A 코드 반영 + EAS Build 14 submit 완료.

## Files involved

- `app/src/components/KeypointOverlay.tsx` (Fix A 적용 완료, commit 15a7f21)
- `backend/shared/python/sunity_shared/analysis/frame_extractor.py` (Fix B 대상, 후속)
- `backend/functions/pipeline/app.py` (Fix B 대상, 후속)
- `backend/scripts/extract_reference_keypoint_reports.py` (Fix B 대상, 후속)
- `.planning/phases/12-realmeasurement-keypoint/12-KEYPOINT-DRIFT-ROOT-CAUSE-REVIEW.md` (fable 진단 원본)

## Evidence

- timestamp: 2026-06-11T05:30:00Z — belle UAT 3차 (Build 12 그대로) finding 4건 + 새 finding (keypoint 사람 따라가지 않음)
- timestamp: 2026-06-11T06:00:00Z — 우리가 우회 시도 1: 동기화 문제로 진단 → belle 가 100% 매칭 아님 박제로 정정
- timestamp: 2026-06-11T06:15:00Z — 우리가 우회 시도 2: YOLOX 식물 detect / 거울 가설 → Pod raw 시각화 + belle 의 "거울 없음" 박제로 기각
- timestamp: 2026-06-11T06:30:00Z — fable review 도착: timing drift / fps 라벨 불일치 진단. 6영상 전수 검증 완료
- timestamp: 2026-06-11T06:35:00Z — Pod raw 시각화 PNG 확인 → keypoint 좌표 자체는 사람 위 정확 (fable 진단 정합)
- timestamp: 2026-06-11T07:15:00Z — Fix A 적용 (KeypointOverlay frames/duration → effective fps). typecheck PASS. commit 15a7f21 → origin/main push. EAS Build 14 (b7c73d0e-3563-40df-b483-ffe0c8eae3ed) production iOS auto-submit 트리거. ASC submission d8772313-c8c2-4974-b4d9-b52ab047cf71.

## Resolution

root_cause: KeypointReport.fps 라벨 = target_fps (요청값) ≠ 실효 fps (src_fps / step). KeypointOverlay 가 라벨로 frame index 산출 → 시간 진행할수록 drift.
fix: KeypointOverlay 가 frames / player.duration 으로 실효 fps 직접 산출 (Fix A). 백엔드 라벨 정직화는 Fix B 별도.
verification: pending — belle TestFlight Build 14 UAT 4차 (영상 끝까지 keypoint 가 사람 따라가는지 확인).
files_changed: app/src/components/KeypointOverlay.tsx
commit: 15a7f21
eas_build: b7c73d0e-3563-40df-b483-ffe0c8eae3ed (https://expo.dev/accounts/sunity3412/projects/sunity-ai-coach/builds/b7c73d0e-3563-40df-b483-ffe0c8eae3ed)
asc_submission: d8772313-c8c2-4974-b4d9-b52ab047cf71 (https://expo.dev/accounts/sunity3412/projects/sunity-ai-coach/submissions/d8772313-c8c2-4974-b4d9-b52ab047cf71)
