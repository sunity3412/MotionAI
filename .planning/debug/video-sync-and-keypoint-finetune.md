---
slug: video-sync-and-keypoint-finetune
status: fixed
trigger: belle UAT 4차 (TestFlight Build 14, 2026-06-11 16:24-16:28) — keypoint timing drift fix (Build 14) 후 큰 폭 drift 해소됐으나 3가지 미세 finding 남음. (1) 1-2초 미세 drift, (2) 반복 재생 시 정은지 영상 멈춤, (4) 다리 keypoint 길이.
created: 2026-06-11
updated: 2026-06-11
---

# video-sync-and-keypoint-finetune

## Symptoms

### Finding 1 — 1-2초 미세 drift (정은지 영상 약간 빠름)

- **Expected**: 두 영상 currentTime 이 동기화돼서 같은 시점 자세 비교
- **Actual**:
  - Image 19 (시작): 0:00 / 0:00 — 동기 OK
  - Image 20 (재생 중): 내 영상 0:06 / 정은지 0:07 — 정은지 1초 빠름
  - Image 21 (14초): 0:14 / 0:14 — 동기 OK
  - Image 22 (끝): 내 영상 0:16 / 정은지 0:17 — 정은지 1초 빠름
  - belle 평가: "아주 미세하게 정은지 선수 영상이 좀더 빠름"
- **Reproduction**: 분석 결과 → 동작 비교 → 재생 → 영상 진행 따라 시간 라벨 관찰

### Finding 2 — 반복 재생 시 정은지 영상 멈춤

- **Expected**: 다시 재생 시 두 영상 모두 0:00 부터 같이 재생
- **Actual**:
  - Image 23 (4:28, 첫 재생 후 다시 재생): 내 영상 0:08 / 정은지 0:06 (이미 어긋남)
  - Image 24 (4:28, 끝): 내 영상 0:17 (끝) / 정은지 0:06 (멈춤)
  - belle 평가: "반복해서 영상을 돌리다 보니 정은지 선수 영상이 멈추는 현상발생"
- **Reproduction**: 동작 비교 재생 끝까지 → 처음으로(restart) 또는 다시 play → 정은지 영상이 진행 안 함

### Finding 4 — 다리 keypoint 길이 짧음

- **Expected**: 다리 keypoint (knee) 가 사람의 발끝까지 연결되는 시각 정합
- **Actual**: 다리 부분 bone 이 짧음 — belle 평가 "키포인트 다리부분이 좀 길어져야 하지 않나"
- 현재 keypoint = 8개 (어깨 좌/우, 엉덩이 좌/우, 무릎 좌/우, 손 좌/우) — **발목/발끝 없음**. 무릎까지만 박힘.
- 사람 시각 = 다리가 무릎 아래로 더 길어 보이는데 keypoint 는 무릎에서 끝남 → 다리 짧아 보이는 인상

## Hypotheses

### H1 (Finding 1) — VideoCompare player 시작 시점/속도 비동기

- VideoCompare 의 togglePlay 가 두 player 에 `play()` 동시 호출하지만 실 재생 시작 시점은 buffer 상태에 따라 다름
- 정은지 영상 = S3 presigned URL → 네트워크 buffer 박힘. 사용자 영상 (작을 가능성) 보다 buffer 빠를 수도
- 또는 두 영상 native fps 차이 (사용자 24, 정은지 30) → expo-video 의 frame stepping 미세 차이가 누적
- fix 방향: tick 안에서 `|leftCurrent - rightCurrent| > 0.3` 이면 빠른 쪽 pause 잠시 또는 느린 쪽 seek 보정

### H2 (Finding 2) — VideoCompare togglePlay 가 정은지 영상 reset 못함

- togglePlay 의 endcheck:
  ```ts
  if (duration > 0 && current >= duration - 0.05) {
    if (leftPlayer) leftPlayer.currentTime = 0;
    if (rightPlayer) rightPlayer.currentTime = 0;
  }
  ```
- `current` 는 `leftCurrent` (사용자 영상 기준). 사용자 영상이 17초 (정은지 17초 와 같다고 가정) — 둘 다 reset.
- 그러나 실제로는 정은지 영상의 실 duration 이 미세하게 다를 수 있음 (정확히 17초 박힘 vs 17.078초 박힘). 또는 expo-video 의 currentTime = 0 reset 이 다음 play() 호출과 race condition.
- 또는 tick 의 pause 로직: `cL >= shorter - 0.05 || cR >= shorter - 0.05` — **OR 조건** → 한쪽이 끝나면 둘 다 pause. 정은지가 약간 빠른 상황 (H1 박힘) 이면 정은지가 먼저 endpoint 도달 → 양쪽 pause → 사용자 영상 17초 안 끝났는데 pause 됨. 그리고 다음 play 시 사용자만 다시 진행, 정은지는 이미 끝나서 멈춤.
- fix 방향: tick 의 pause 트리거 = Math.min(cL,cR) >= shorter (AND-like). togglePlay 의 end-check = Math.max(leftCurrent, rightCurrent). reset 후 seek→play race 회피용 setTimeout 60ms.

### H3 (Finding 4) — keypoint 8개 박힘 발목 미포함, 다리 시각 한계

- KeypointOverlay 의 JOINTS = 8개 (어깨/엉덩이/무릎/손 좌우) — **발목 / 발끝 미박힘**
- 무릎까지만 그려지니 사람의 다리가 무릎 아래로 더 보이는데 keypoint 는 무릎에서 끝남
- RTMW 133 wholebody = 발목/발끝 keypoint 박힘 (COCO-17 의 left_ankle/right_ankle). 우리가 adapter 에서 8개만 추출.
- fix 방향: `JOINTS` 에 `left_ankle`, `right_ankle` 추가 (10개) + BONES 에 knee→ankle bone 추가. KeypointReport schema 영향 (T × 10 × 2). backend extract 도 같이 갱신 필요.
- 또는 시각 조정 only — 다리 bone 의 stroke width 또는 hip-knee bone 을 hip-knee-ankle proxy 로 시각 늘림 (덜 정확)

## Investigation result

### Finding 4 — backend 조사 결과

**Option B (backend schema change) 가 정답** — Option A (frontend-only) 는 불가능.

확인된 사실:
- `backend/shared/python/sunity_shared/analysis/keypoint_frame.py`:
  - `_KEYPOINT_NAMES` tuple = 8개 hardcoded (line 51-60): shoulder/hip/knee/hand 좌우 only. ankle 없음.
  - `NUM_KEYPOINTS_PHASE12 = 8` (line 62).
  - `__post_init__` 에서 `len(self.data) != T * J * 2` 검증 — schema lockstep 강제.
- `backend/shared/python/sunity_shared/analysis/assemble.py:390`:
  - `joints_list = list(_KEYPOINT_NAMES)` — 8개 hardcoded.
- `app/src/types/analysis.ts:755`:
  - `KeypointName` Literal Union = 8개 only.

즉 **KeypointReport.joints 에 ankle 이 들어있지 않다**. Firestore 저장 시점부터 ankle 좌표가 누락된 상태 (RTMW 가 산출은 하지만 adapter/assemble 에서 8개만 추출).

따라서 frontend-only fix 불가능 — 다음 3-way atomic commit + 5 reference reseed 필요:
1. Python `_KEYPOINT_NAMES` 에 `left_ankle, right_ankle` 추가 (10) + `NUM_KEYPOINTS_PHASE12 = 10`
2. Python `assemble.build_keypoint_report` 에서 ankle keypoint 추출 추가 (RTMW COCO-17 idx 15/16)
3. TS `KeypointName` Literal 에 `left_ankle, right_ankle` 추가
4. TS Firestore validator `_validate_keypoint_report` (있다면) length 검증 갱신
5. Frontend `KeypointOverlay.tsx`: `JOINT_KEY_TO_ANGLE_KEY` ankle 추가, `BONES` 에 knee→ankle 좌/우 추가
6. **5개 reference 영상 reseed** (`extract_reference_keypoint_reports.py` 재실행)
7. 기존 사용자 분석 doc (정은지 reference) 의 KeypointReport 는 8 joints 박혀있음 — schema migration 또는 fallback 처리 필요
8. docs/contract.md §9.12 갱신

→ Finding 4 는 별도 plan/phase 박제 권장 (이번 hotfix 범위 밖). Phase 12/13 에 후속 박제.

### Findings 1 + 2 — VideoCompare.tsx 박제 fix 적용

**적용된 변경 (`app/src/components/VideoCompare.tsx`)**:

1. **상수 신설** (line 89-91):
   - `DRIFT_CORRECT_THRESHOLD_S = 0.3` — 보정 진입 임계
   - `DRIFT_RESET_THRESHOLD_S = 0.15` — hysteresis reset (stutter 방지)
   - `REPLAY_SEEK_DELAY_MS = 60` — togglePlay seek→play race 회피 지연

2. **drift 보정 ref** (line 143): `correctingDriftRef = useRef(false)`

3. **tick 안 drift 보정** (line 152-180):
   - 둘 다 재생 중 + duration 산정됨 + 끝부분 진입 전 + drift > 0.3s + 미보정 상태 → 빠른 쪽을 느린 쪽 시각으로 back-seek
   - drift < 0.15s 로 회복되면 ref reset → 다음 보정 사이클 허용

4. **pause 트리거 변경** (line 188-198):
   - 이전 (Build 14): OR `cL >= shorter || cR >= shorter` — 빠른 쪽 도달 시 둘 다 pause
   - 현재 (Build 15): `Math.min(cL, cR) >= shorter` (AND-like) — 느린 쪽까지 기다림. drift 보정과 결합하면 자연스럽게 동기 pause.
   - Safety net: 둘 다 자기 native duration 도달 시도 pause (보정 fail 케이스).

5. **togglePlay restart fix** (line 218-241):
   - 이전: `current` (= leftCurrent) 한쪽만 검사. seek=0 직후 즉시 play → race.
   - 현재: `Math.max(leftCurrent, rightCurrent)` end-check. 끝났으면 seek=0 + setTimeout(60ms) + play. drift ref 도 함께 reset.

6. **restart() 도 drift ref reset** (line 247).

**TypeScript check**: `cd app && npx tsc --noEmit` → exit 0, 에러 없음.

## Current Focus

hypothesis: H1 (1-2초 drift = 두 player 의 시작 시점/속도 비동기, tick 보정 필요) + H2 (반복 재생 멈춤 = tick 의 pause OR 조건 + togglePlay reset race) + H3 (발목 keypoint 추가로 다리 시각)

test: H1+H2 fix 후 belle UAT 영상에서 두 player 시간 라벨 동기화 + 반복 재생 시 정은지 영상 정상 진행. H3 fix 후 다리가 발끝까지 보임.

expecting: 1-2초 drift 0.3초 이내로 축소, 반복 재생 100% 동기, 다리 시각 자연.

next_action: belle UAT 5차 (Build 15) → Finding 1/2 시각 확인. Finding 4 = 별도 plan 박제.

## Files involved

- `app/src/components/VideoCompare.tsx` (H1, H2) — **fix 적용 완료 Build 15**
- `app/src/components/KeypointOverlay.tsx` (H3, JOINTS / BONES 박힘) — Finding 4 backend lockstep 의존
- `app/src/types/analysis.ts` (KeypointReport schema — H3 시 발목 추가) — Finding 4 backend lockstep 의존
- `backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py` (H3 시 발목 매핑)
- `backend/shared/python/sunity_shared/analysis/assemble.py` (H3 시 build_keypoint_report 박힘)
- `backend/shared/python/sunity_shared/analysis/keypoint_frame.py` (H3 시 `_KEYPOINT_NAMES`, `NUM_KEYPOINTS_PHASE12`)
- `backend/scripts/extract_reference_keypoint_reports.py` (H3 시 reference 5건 reseed)

## Out of scope

- Finding 3 (keypoint 가 일부 동작에서 사람 못 따라감) — RTMW 모델 정확도 한계. Phase 13 (좌/우 mirror) 와 함께 모델 영역 작업.
- Finding 4 (ankle keypoint 추가) — backend schema 영향 + reference reseed 필요. 별도 plan 박제. 이번 hotfix 범위 밖.
- UAT 효율화 (시뮬레이터 + fixture) — 별도 spike 박힘.

## Resolution

root_cause:
  - Finding 1: VideoCompare 의 tick 폴링이 두 player 의 currentTime 을 그저 관찰만 했고 보정 안 함. fps 미세 차이 + S3 buffer 차이가 누적되며 정은지 영상이 1~2초 빨라짐.
  - Finding 2: tick 의 pause OR 조건 (`cL >= shorter || cR >= shorter`) + togglePlay 의 한쪽 (`current = leftCurrent`) 만으로 end 판정. 정은지 (빠름) 가 먼저 자기 native end 도달 → 양쪽 pause → 다음 replay 시 정은지 native end 넘어 진행 X.
  - Finding 4: KeypointReport schema 가 8 joint hardcoded (ankle 없음). RTMW 는 ankle 산출하지만 assemble 에서 8개만 추출. Frontend-only fix 불가능.

fix:
  - Finding 1: tick 안에 drift 보정 (|cL-cR| > 0.3s 이면 빠른 쪽 back-seek to 느린 쪽 시각). hysteresis 0.15s reset 으로 매 tick seek stutter 방지.
  - Finding 2: pause 트리거 = Math.min(cL,cR) >= shorter (AND-like) + safety net (둘 다 native end). togglePlay end-check = Math.max(leftCurrent, rightCurrent). restart 시 seek=0 + setTimeout(60ms) + play (seek→play race 회피).
  - Finding 4: not applied — 별도 plan 박제 (backend schema change + reference 5 reseed 필요).

verification: belle UAT 5차 (Build 15) — (1) 16~17초 영상 끝까지 시간 라벨 차이 < 0.3초 유지, (2) 반복 재생 5회 모두 두 영상 0:00 부터 같이 진행. Finding 4 = Build 15 에 영향 X (별도 후속).

files_changed:
  - app/src/components/VideoCompare.tsx (Build 15)

next_step:
  - EAS Build 15 production submit (auto-submit) — 진행 중
  - belle TestFlight Build 15 UAT 5차 (Finding 1+2 확인)
  - Finding 4 = 별도 plan 박제 (Phase 12 후속 또는 Phase 13 묶음)
