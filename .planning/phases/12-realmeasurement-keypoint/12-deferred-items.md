# Phase 12 Deferred Items

Phase 12 (realmeasurement-keypoint) Wave 2 (Plan 12-03) 실증 follow-up + 후속 결정 보류 항목.

T4 belle iOS UAT 결과로 일부 항목이 추가/수정됨. 본 파일은 Wave 2 commit 시점의
스냅샷이며 T4 후 추가 정보가 채워짐.

---

## 1. A2 — mode1 reference 측 floating angle label

- **현재 상태**: Wave 2 사용자 측 KeypointOverlay 만 floating "N°" 라벨 노출.
  mode1 reference (정은지) 측은 brand 컬러 강조 (점/본) 만 + floating label X.
- **이유**: 사용자 측과 reference 측이 동시에 라벨을 띄우면 split 화면 시각
  중복 + 강조 의도 모호. belle UAT 후 reference 측 라벨 추가 여부 결정.
- **결정 시점**: T4 belle UAT.
- **결정 input 필요**: "reference 측 라벨 보고 싶다 / 사용자 측만 충분".

## 2. Low-reliability KeypointOverlay 시각 treatment

- **현재 상태**: Wave 2 MVP scope OUT. 저신뢰 frame 의 keypoint 가 일반 frame
  과 동일한 시각 (Circle stroke + bone Line).
- **이유**: dashed stroke / opacity 0.5 등 시각 복잡도 증가 가능성 + 결과
  화면 영역 5 ⚠ amber badge + 영역 6 "추정 N°" 으로 이미 occlusion 표기.
- **결정 시점**: Phase 12.5 또는 학원 파일럿 후.
- **decision input 필요**: 사용자가 KeypointOverlay 자체에서 저신뢰 frame
  구분이 필요한지.

## 3. KEYPOINT_DELTA_HIGHLIGHT_DEG sensitivity

- **현재 값**: 10.0° (Wave 1 lock, D-12-C3).
- **검증 데이터**: T4 belle iOS UAT 가 정은지 vs 사용자 분석 1건 실측 →
  delta ≥ 10° 발생 joint 갯수 박제.
- **조정 후보**: 너무 빈번 (대부분 joint 강조) → 15°. 너무 드물 (1-2 개) → 7°.
- **결정 시점**: T4 belle UAT.

## 4. 토글 ON/OFF 사용자 선호도

- **현재 상태**: 디폴트 ON + AsyncStorage 키 `'@sunity:keypoint_overlay_enabled'`.
  Pitfall 6 우회로 OFF 사용자는 진입 시 잠시 ON 깜빡임 수용.
- **검증 데이터**: 학원 파일럿 + belle UAT 동안 사용자가 토글을 끄는 빈도.
- **결정 시점**: 학원 파일럿 후. 끄는 빈도 높으면 디폴트 OFF 로 전환 검토.

## 5. True frame-level delta + DTW alignment

- **현재 상태**: Wave 2 MVP = 영상 전체 대표 편차 (JointScore 평균 current/
  target). delta 강조도 일정 (frame 별 변하지 않음).
- **이유**: frame-level delta 는 DTW alignment + 시간 normalize 필요 →
  복잡도 + 정확도 trade-off. MVP 는 "대표" 편차로 충분.
- **결정 시점**: v2 (Phase 13+).

## 6. Phase 9 카드 vs 차원 카드 순서

- **현재 상태**: Wave 1 layout (영역 3 = Phase 9 finding, 영역 5 = 세부 점수).
- **검증 시점**: T4 belle UAT.
- **결정 input 필요**: 사용자 흐름상 "실패 원인" 이 "세부 점수" 보다 먼저
  나오는 것이 자연스러운지.

## 7. Frontend test infra

- **현재 상태**: app/ 에 test runner 미설치 (typecheck 만 gate).
- **결정 시점**: Phase 15 통합 sweep 시점.
- **결정 input 필요**: KeypointOverlay / ForcePatternCard / VideoCompare 의
  snapshot 또는 unit test 필요성. RN 환경에서는 Jest + React Native Testing
  Library 가 표준.

## 8. Phase 12.5 차원 카드 ⚠ badge 위치 미세 조정

- **현재 상태**: Wave 2 영역 5 sectionHeader row 우측 ⚠ amber badge.
- **검증 시점**: T4 belle UAT.
- **결정 input 필요**: 카드 안 우상단 (각 차원별) vs 섹션 헤더 (현재).
  현재 = 1개 badge / 차원별 = 3개 badge. 차원별 noisy 가능성.

## 9. 성장 차트 위치 (D-12-A1 #6)

- **현재 상태**: Wave 1 layout 미박제.
- **결정 시점**: T4 belle UAT.
- **결정 input 필요**: 차원 카드 ↔ 각도 상세 사이로 이동 가능성.

## 10. Pitfall 1-9 실 발현 박제 (T4 결과)

T4 belle iOS UAT 결과로 채워짐. 미실행.

| Pitfall | 발현 / WORKAROUND / 미발현 | 비고 |
| ------- | --------------------------- | ---- |
| Pitfall 1 (iOS seek bug) | T4 미실행 | useEvent.currentTime 사용 시 정합 검증 |
| Pitfall 2 (60fps jank) | T4 미실행 | iOS Instruments 또는 belle 직관 |
| Pitfall 6 (토글 깜빡임) | T4 미실행 | useState(true) initial 박제 정합 |
| Pitfall 7 (Firestore 1 MiB) | T4 미실행 | result.keypointReport doc size 실측 |
| Pitfall 9 (timeline vs overlay 동기) | T4 미실행 | 250ms 폴링 vs ~30ms useEvent drift |

## 12. UAT 2차 (2026-06-11) — 추가 4 finding

belle iOS UAT 2차 (TestFlight Build 12, 18fps + finding gate + reference keypoints 적용 후).

### 12-A — 좌/우 mirror (6~7초+, Phase 13 분리)

- **현상**: 정은지 자기-비교 영상에서 사람이 회전해 등을 카메라 쪽으로 돌리는 순간
  keypoint 좌/우 라벨이 swap. 14초쯤 다리 keypoint 가 폴 밖 (사람은 폴 안착).
- **원인**: RTMW 모델 학습 한계 — 정면 시점 기준 좌/우 라벨, 회전 시 front-back
  모호성 발생. RTMW 가중치 자체 한계.
- **해결 방향 (Phase 13 신규 plan)**:
  1. 회전 phase 감지 (어떤 frame 부터 mirror 상태인지 — heading vector 변화)
  2. confidence + frame-to-frame stability + (가능하면) 3D z-coord 부호로
     mirror 검출
  3. 검출 frame 에 좌/우 swap correction post-process
  4. 다양한 회전 영상 sweep — false positive/negative 검증
- **추정 작업량**: 1-2일 + 별도 test fixtures
- **Phase 13 신규 plan 으로 박제**.

### 12-B — 영상 끝 ~0.5초 keypoint 정지 (Phase 12 내일 fix)

- **현상**: 17초 영상의 15~17초 구간에서 keypoint 가 종료 자세로 정지 (사람은
  아직 회전 중). 9fps 추출 결과: 17 × 9 = 153 frame, 마지막 frame = 16.89초.
- **원인**: `frame_extractor.py` 의 step loop 가 균등 sample 만 박제 — 영상 끝
  근처 잔여 frame 무시. 18fps upsample 도 마지막 frame 이후 데이터 없음 → 보간
  X.
- **해결 방향**: `frame_extractor.py` 의 step loop 가 마지막 frame 강제 포함.
  ~5줄 패치.
- **작업량**: 30분. Phase 12 내일 fix.

### 12-C — 두 영상 timeline 미세 drift (Phase 12 내일 fix)

- **현상**: 1초 시점에 사용자 영상 vs 정은지 영상이 미세하게 다른 위치 표시.
  분석쪽이 약간 빠름.
- **원인**: 두 영상 native duration / native fps 가 다름. `VideoCompare.tsx` 가
  하나의 progress bar 만 표시 (현재 어느 쪽 기준인지 모호).
- **해결 방향**:
  - Option A: 각 player 별 currentTime 표시 (player1: "0:01 / 0:17",
    player2: "0:01 / 0:16")
  - Option B: 짧은 영상 기준으로 progress bar normalize, 긴 쪽은 종료 시점에
    정지 + indicator
- **작업량**: 1-2시간. Phase 12 내일 fix (UI 작업).

### 12-D — 저신뢰 keypoint 시각 처리 (Wave 2 #2 끌어올림 — Phase 12 내일)

- **현상**: 14초 다리 keypoint 가 폴 밖 (occluded — 폴 뒤 다리). confidence
  낮은 추정인데 일반 keypoint 와 같은 표시 → 사용자 혼동.
- **원인**: Wave 2 MVP 에선 occlusion 표기를 결과 화면 (영역 4 ⚠ amber badge,
  영역 5 "추정 N°") 만 박제. KeypointOverlay 자체는 시각 변경 X (Wave 2 #2
  deferred 박제).
- **해결 방향**: KeypointOverlay 가 `visibility < 0.5` keypoint 를 회색 stroke +
  dashed line 처리. 본 plan deferred items #2 정합.
- **작업량**: 1시간. Phase 12 내일 fix.

### 박제 우선순위 (내일 belle 합류 시)

1. **12-B** 30분 — frame_extractor 마지막 frame 보장 (가장 명확한 효과)
2. **12-D** 1시간 — 저신뢰 keypoint 회색/dashed (가장 사용자 인지 효과)
3. **12-C** 1-2시간 — 두 영상 timeline 분리 표시
4. **12-A** (Phase 13 분리) — 새 plan, 새 scope

### Phase 13 신규 scope (잠정)

- **이름**: keypoint-rotation-mirror-correction (혹은 belle 검수)
- **scope**: 좌/우 mirror correction post-process layer
- **trigger**: Phase 12 종료 후 다음 belle chain
- **의존**: Phase 12 (KeypointReport schema 확정)

---

## 11. RunPod Network Storage 전환

- **현재 상태**: Pod ephemeral storage 사용. Pod terminate → NLF 모델 (~500MB)
  + MotionBERT clone + MediaPipe 모델 + venv 전부 휘발 → 매번 setup.sh 30분+ 재실행.
- **2026-06-10 belle 발견**: RunPod Inbox "Share data across Pods in the same data
  center with Network Storage" 알림. Volume 1개 생성 후 다중 Pod 마운트.
  모델/데이터셋/output 영구 보존 + Pod 재생성 시 mount 만 하면 setup 1분.
- **비용**: ~$0.05-0.10 / GB·월. 모델 20GB 잡으면 월 $1-2 (무시 가능).
- **제약**: 같은 datacenter Pod 만 mount 가능 (region lock-in).
- **결정**: 다음 Pod 재생성 시점에 Network Storage 전환. 이번 (9rsf2w9hpso73q,
  3090) 은 ephemeral 로 진행 — 전환에 추가 30분+ 필요 → T4 UAT 더 지연.
- **결정 시점**: T4 UAT 완료 직후 또는 다음 Pod 종료 시점.
- **action**: Volume 20GB 생성 → 새 Pod template 에 mount path `/workspace` 지정 →
  setup.sh 1회 실행 → 이후 Pod stop/start/recreate 모두 setup 스킵.
- **연관 박제**: [[runpod-gpu-env]] "Stop 금지" 규칙은 Network Storage 도입 시
  완화 가능 (data 휘발 X → stop OK).
