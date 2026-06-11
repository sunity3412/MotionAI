---
phase: 12-realmeasurement-keypoint
reviewer: Claude Code (Fable 5)
date: 2026-06-11
scope: keypoint-overlay-drift-root-cause
status: diagnosis-confirmed — fix 미적용 (전달용 리뷰)
evidence_verified:
  - ffprobe (S3 presigned): reference 5건 + belle UAT 사용자 영상 1건
  - reference-keypoint-reports.json / reference-keypoint-reports-18fps.json 수치 분석
  - Firestore 실문서 read: users/csKWYvI3WCPYPysNQ9KkWecaUvq1/analyses/b08f04df7def4de39771516eaf4336bb
code_read:
  - app/src/components/KeypointOverlay.tsx
  - app/src/components/VideoCompare.tsx
  - app/src/app/analysis/result.tsx
  - backend/shared/python/sunity_shared/analysis/frame_extractor.py
  - backend/shared/python/sunity_shared/analysis/assemble.py (build_keypoint_report)
  - backend/shared/python/sunity_shared/analysis/keypoint_frame.py (upsample_to_fps)
  - backend/shared/python/sunity_shared/analysis/adapters/rtmw_133_to_coco17.py
  - backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py
  - backend/functions/pipeline/app.py (keypoint report 산출부)
  - backend/scripts/extract_reference_keypoint_reports.py
  - app/scripts/seed-reference-motions.mjs
---

# Phase 12 키포인트 오버레이 어긋남 — Root Cause 리뷰

## Executive Verdict

키포인트가 사람 위에 안 붙는 원인은 **좌표(x, y)가 아니라 시간축이다.**

KeypointReport 의 `fps` 라벨이 실제 샘플링 레이트와 다르다. `FfmpegFrameExtractor` 가
`step = round(src_fps / target_fps)` 로 정수 양자화하면서 **실효 fps = src_fps / step ≠ target_fps**
가 되는데, report 에는 요청값(target)이 그대로 박힌다. `KeypointOverlay` 는
`frameIndex = floor(currentTime × fps라벨)` 로 시간→프레임을 매핑하므로, 스켈레톤이
영상보다 **12.5~20% 빠르거나 10% 느리게** 재생되고, 라벨이 실효보다 클 때는 데이터가
영상 끝 전에 소진돼 **마지막 2~3초 동안 얼어붙는다.**

좌표 자체는 전 구간 정상이다. t=0 에서는 양쪽 스켈레톤이 정확히 사람 위에 올라간다
(인덱스 0 은 라벨과 무관). 재생할수록 어긋나고, 폴 동작에서 1~2.5초 차이는 스핀
반대편/공중이므로 "사람이 아닌 곳에 떠 있다"로 보인다.

이 진단은 코드 추론이 아니라 **실데이터 전수 검증으로 확정**했다. reference 5건 +
사용자 UAT 영상 1건 모두에서 "report 가 주장하는 길이 ÷ 실제 영상 길이" 비율이
step 양자화 수식의 예측값과 소수점 셋째 자리까지 일치한다 (§3).

## 1. 증상 정의 (belle UAT 2차)

- 사용자/reference 양쪽 모두 키포인트가 사람 몸에서 멀리 떨어져 표시 (공중, 폴 근처).
- 좌/우 라벨 스왑(Phase 13)과 별개 — (x, y) 자체가 틀려 보임.
- 선행 fix 4건 (12-B frame 포함 / 12-C timeline 분리 / 12-D 저신뢰 표시 / 18fps 재추출)
  적용 후에도 재현.

## 2. Root Cause — 오류 체인 4단계

```
[1] frame_extractor.py:44
    step = max(1, round(src_fps / target_fps))
    → 30fps 원본, target 18 → step=2 → 실효 15fps  (요청 18 과 다름)
    → 30fps 원본, target 9  → step=3 → 실효 10fps
    → 24fps 원본, target 9  → step=3 → 실효 8fps
    실효 fps 는 어디에도 기록되지 않고 frames 배열만 반환된다.

[2] 호출부가 "요청값"을 라벨로 박음
    - pipeline/app.py:1263   build_keypoint_report(pose_frames, fps=9.0)   ← 실효 8~10
    - extract_reference_keypoint_reports.py:112  fps=target_fps(18.0)      ← 실효 15

[3] keypoint_frame.py upsample_to_fps(report, 18.0)
    src_duration = frames / report.fps 로 거짓 라벨을 신뢰
    → 9라벨(실효 8) × 2배 보간 = 18라벨(실효 16)  — 오차가 보존·확대된 채 통과

[4] KeypointOverlay.tsx:197
    frameIndex = floor(currentTime × keypointReport.fps)
    → 표시 시점 = t × (라벨 / 실효).  t=0 만 정확, 오차는 t 에 선형 비례.
    라벨 > 실효이면 인덱스가 T-1 에 조기 도달 → clamp → 끝부분 freeze.
```

오차 공식: **표시되는 포즈의 실제 시점 = t × (fps라벨 / fps실효)**

| 슬롯 | 원본 fps | 체인 | 라벨/실효 | 증상 |
|---|---|---|---|---|
| reference (18fps 재추출본) | 30 | step=2 → 15fps, 라벨 18 | 18/15 = **1.20** | 20% 앞서감 + 마지막 ~17% freeze |
| 사용자 (belle UAT, 24fps 영상) | 24 | step=3 → 8fps, 라벨 9 → ×2 upsample → 16fps, 라벨 18 | 18/16 = **1.125** | 12.5% 앞서감 + 마지막 ~1.9s freeze |
| 사용자 (30fps 폰 촬영 가정) | 30 | step=3 → 10fps, 라벨 9 → ×2 → 20fps, 라벨 18 | 18/20 = **0.90** | 10% 뒤처짐 (freeze 없음, 데이터 잉여) |

오차의 크기와 방향이 **원본 영상 fps 에 따라 달라진다**는 점이 이 버그의 재현성을
어렵게 만든 핵심이다. 같은 코드가 24fps 영상에선 앞서가고 30fps 영상에선 뒤처진다.

## 3. 증거 (전수 검증 — 예측 전부 적중)

### 3-1. reference 5건, 18fps JSON vs ffprobe

전부 2160×3840 (정확히 9:16 세로), 30fps, rotation 메타데이터 없음.

| motion | 실제 길이 / 프레임 | JSON 주장 (T/18) | 비율 | step=2 예측 T | 실제 T |
|---|---|---|---|---|---|
| ref-sideway-spin | 19.79s / 593f | 16.6s | 1.196 | 297+1=298 | **298** |
| ref-climb | 17.08s / 512f | 14.3s | 1.196 | 256+1=257 | **257** |
| ref-invert | 17.25s / 517f | 14.4s | 1.195 | ~260 | **260** |
| ref-foxtop | 28.31s / 849f | 23.7s | 1.196 | ~426 | **426** |
| ref-foxtop-split | 32.30s / 968f | 26.9s | 1.200 | 484+1=485 | **485** |

비율이 5/5 전부 18/15 = 1.2. ("+1" 은 12-B 마지막 frame 강제 포함 — frame 수까지
수식 그대로라 추출 경로 자체가 확정된다.)

### 3-2. 구 9fps JSON (참고)

claimed 19.0~35.9s vs 실제 17.1~32.3s — 전부 9/10 = 0.9 배. 즉 9fps 시절에는
오버레이가 10% 뒤처졌고, 18fps 재추출은 reference 쪽 오차를 10%→20%로 **악화**시켰다.

### 3-3. 사용자 측 — Firestore 실문서 (mode1, ref-climb, status done)

- 업로드 영상 (S3): **406×720, 24fps, 17.125s, 411f** (rotation 없음, 사실상 9:16)
- Firestore `result.keypointReport`: **frames=274, fps=18 → 주장 길이 15.22s**
- 예측: 411/3=137 → ×2 upsample = 274. **적중.** 비율 17.125/15.22 = 1.125 = 18/16. **적중.**

## 4. 가설 판정

| # | 가설 | 판정 | 근거 |
|---|---|---|---|
| 1 | RTMW 가 사람 아닌 물체 검출 | **기각** | 데이터가 해부학적으로 정상: torso 벡터 (-0.03, +0.10) 아래방향, mean conf 0.55~0.71, centroid 가 동작 따라 이동 (x 0.33→0.66), invert 구간에서 torso 부호 반전까지 정확 |
| 2 | 정규화 좌표계 불일치 | **기각** | rtmlib 출력(입력 frame px) ÷ 같은 frame 의 W,H — 일관. 영상 6건 전부 9:16 + rotation 메타 없음 → letterbox/회전 변형 0 |
| 3 | 사용자↔reference 데이터 스왑 | **기각** | result.tsx:636-651 배선 정상 (left=`result.keypointReport`, right=`refMotion.referenceKeypointReport`). seed 는 motionId 키 단위. "사용자 키포인트가 정은지 포즈 모양"으로 보인 건 **belle 테스트 영상 자체가 ref-climb 의 re-encode** 이기 때문 (17.125s vs 17.078s, 동일 climb 동작, 406×720/24fps 압축본) |
| 4 | SVG viewBox/preserveAspectRatio | **기각 (현재) / 휴면 결함 (장래)** | §7-1 참조. 현재 콘텐츠가 전부 9:16 이라 발화하지 않음 |
| 5 (신규) | **fps 라벨 ≠ 실효 샘플링 fps** | **확정** | §2~§3. 6개 영상 전수에서 수식 예측과 일치 |

## 5. 선행 fix 4건이 못 잡은 이유

| fix | 회고 |
|---|---|
| 12-B 마지막 frame 포함 | "끝부분 keypoint 정지" finding 의 진짜 원인은 누락 frame 이 아니라 인덱스가 12.5~20% 빨리 달려 T-1 에 조기 도달+clamp 되는 것. 증상의 표면만 건드림 |
| 12-C timeline 분리 | 표시 계층 — 무관 |
| 12-D 저신뢰 회색 | 표시 계층 — 무관 |
| 18fps 재추출 (fps "맞춤") | 라벨끼리는 18 vs 18 로 맞췄지만 실효는 16 vs 15. reference 쪽 오차는 10%→20% 악화. "fps 박힘"이라는 문제 인식 자체는 옳았으나 라벨이 거짓이라는 한 겹 아래를 못 봄 |

## 6. 영향 범위

1. **KeypointOverlay (주 증상)** — 모든 기존 분석 doc + reference 5건의 fps 라벨이 거짓.
   재추출 없이도 앱 쪽 보정으로 구제 가능 (§7 Fix A).
2. **force_signals jerk (부수, 점수 영향)** — `_compute_jerk(angles, fps)` 가 dt=1/fps 를
   쓰는데 pipeline/app.py:1205 가 `fps=9.0` 하드코드. 실효 8fps(24fps 원본) 입력이면
   jerk 가 (9/8)³ ≈ **1.42배 과대**, 실효 10fps(30fps 원본)이면 (9/10)³ ≈ 0.73배 과소.
   즉 **사용자 카메라 fps 에 따라 jerk 스케일이 ±40% 출렁인다.** Phase 8/9 calibration
   sweep 은 30fps 영상(실효 10fps)으로 돌았으므로 24/60fps 사용자 영상은 calibration 과
   다른 스케일을 받는다. 본 리뷰의 fix 범위에는 넣지 않되 별도 박제 필요.
3. **DTW/각도/kismam 본체** — frame 단위 연산이라 fps 절대값 무관. 영향 없음.

## 7. 수정 제안 (리뷰어 입장 — 본 세션에서 코드 수정하지 않음)

### Fix A — 앱 hotfix: 실효 fps 를 데이터에서 직접 산출 (기존 데이터 전부 즉시 구제)

`KeypointOverlay` 에서 라벨 대신 **실효 fps = report.frames / player.duration** 사용
(duration > 0 일 때; 아니면 기존 라벨 fallback).

- 검산: 사용자 274/17.125 = 16.0 (실효와 일치), reference 257/17.078 = 15.05 (일치).
  마지막 인덱스가 정확히 영상 끝에서 T-1 에 도달 — drift 와 freeze 가 동시에 해소된다.
- 장점: **백엔드 재추출/reseed 없이 기존 저장 데이터 전부 즉시 복구.** 근본 fix 배포
  후에도 frames/duration == 라벨이 되므로 무해하게 공존.
- 단점: player.duration 로드 전엔 fallback. 근본 원인(데이터의 거짓 라벨)은 잔존.

### Fix B — 백엔드 근본: 라벨 정직화 (extractor 가 실효 fps 를 산출물로 전달)

`FfmpegFrameExtractor` 가 step 확정 후 **실효 fps = src_fps / step** 를 함께 반환하고,
호출부 2곳이 하드코드 대신 그 값을 라벨로 사용:

- `pipeline/app.py:1263` `fps=9.0` → `fps=실효값`
- `extract_reference_keypoint_reports.py:112` `fps=target_fps` → `fps=실효값`

`upsample_to_fps` 는 수정 불필요 — 입력 라벨이 정직하면 출력도 정직해진다
(8fps→18fps 비정수배 선형 보간 이미 지원). KeypointReport contract(3-way lockstep)도
필드 추가 없이 fps **값**만 바뀌므로 TS/Python/docs 동시 수정이 필요 없다.

샘플링 자체를 시간 기반(인덱스 = round(k × src_fps / target_fps))으로 바꿔 실효==target
을 보장하는 변형(B-2)도 가능하지만, **분석 입력 타이밍이 바뀌므로 Phase 6/7/8 게이트
재검증이 따라붙는다** ([[calibration-source-hard-gate]] — 자기 sweep 재칼리브레이션 금지
원칙과 충돌 위험). 지금 단계에서는 B(라벨 정직화)가 침습 최소.

### 권장 순서

1. **Fix A 먼저** — 데이터 그대로 두고 화면부터 복구 (UAT 재개 가능).
2. **Fix B** — 이후 신규 분석부터 라벨 정직. reference 재추출+reseed 는 B 배포 후 1회.
3. **jerk fps (§6-2)** 는 점수 영향 평가가 필요하므로 별도 항목으로 분리 박제.

### 하지 말 것

- target_fps 를 또 바꿔서 (예: 15로) 라벨을 우연히 맞추는 돌려막기. 24fps/60fps 원본이
  들어오는 순간 같은 버그가 다른 비율로 재현된다. 원본 fps 는 통제 불가 변수다.
- 12-B 마지막 frame 강제 포함 롤백. 그 자체는 유효한 보정이고 본 버그와 무관.

## 8. 수정 후 검증 계획

1. **앱 t=0/중간/끝 3점 체크** — t=0 일시정지(현재도 정확해야 함 = 진단 재확인), 중간
   재생 중 스켈레톤이 사람 위 유지, 영상 끝까지 freeze 없음. mode1 양쪽 슬롯 모두.
2. **자동 정합 체크** — `report.frames / report.fps` vs ffprobe duration 비교 스크립트.
   reference 5건 + 신규 분석 1건에서 오차 < 1 frame.
3. **단위 테스트** — 합성 fps 매트릭스 (24/25/30/60fps 원본 × target 9/18) 에서
   라벨 == src_fps/step 검증. 기존 `tests/phase12/test_assemble_wiring_all_joints.py`
   패턴에 추가.

## 9. 부수 발견 (별도 박제 권장 — 본 버그와 독립)

1. **SVG letterbox 휴면 결함**: 오버레이 SVG 가 영상 표시 영역이 아니라 9:16 슬롯
   전체에 깔린다 (`viewBox="0 0 1 1"` + `preserveAspectRatio="none"`,
   VideoCompare.tsx slotFrame `aspectRatio: 9/16`, KeypointOverlay 의 `videoSize` prop
   은 stroke 굵기에만 사용). 현재 콘텐츠가 전부 9:16 이라 발화하지 않지만, 가로/4:3
   영상 업로드 즉시 스켈레톤이 letterbox 위로 늘어난다. 영상 native size 를 받아
   contain rect 를 계산해 오버레이를 그 rect 에 맞추는 후속 작업 필요.
2. **belle UAT 사용자 영상 = ref-climb re-encode** (406×720/24fps 압축본, 동일 길이).
   "사용자 키포인트가 기준 선수 포즈 모양" 관찰은 데이터 스왑이 아니라 콘텐츠 동일성.
   향후 UAT 는 본인 촬영 영상으로 해야 사용자 path 의 독립 검증이 된다.
3. **upsample 선형 보간 한계**: 실효 8fps 샘플(125ms 간격)을 보간하면 빠른 스핀에서
   실재하지 않는 중간 포즈가 생긴다. fps 라벨 fix 후에도 잔상처럼 보이면 이것.
4. **jerk fps³ 스케일 (§6-2)** — 점수 일관성 이슈. 카메라 fps 가 점수에 새는 경로.

## 재현 커맨드 (검증에 사용)

```bash
# reference 영상 메타 (모두 동일 패턴)
URL=$(aws s3 presign s3://sunity-motion-pilot-videos/reference/ref-climb.mp4 --expires-in 600)
ffprobe -v error -select_streams v:0 \
  -show_entries "stream=width,height,r_frame_rate,duration,nb_frames:stream_side_data=rotation" \
  -of json "$URL"
# → 2160x3840, 30fps, 17.078s, 512f  vs  18fps JSON: T=257 → 257/18=14.3s (×1.2)

# JSON 수치 분석: 루트의 reference-keypoint-reports*.json 에서 frames/fps/claimed_dur 비교
# Firestore: users/{uid}/analyses/{id}.result.keypointReport.frames/fps vs 업로드 영상 ffprobe
```
