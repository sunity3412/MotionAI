# 아바타 시각 예시 — 오늘 데이터로는 돌려도 볼 것이 없다 (2026-09-18)

belle 요청: *"아바타 모델이라는 것이 예를 들면 어떻게 나오는거지? 예시로라도
시각적으로 좀 보여지면 판단이 빠를 거 같은데"*

## ★ 먼저 나온 실측: 저장된 `joints3d` 의 z 가 전부 0 이다

`doc.result.joints3d` 는 **T×17×3 COCO-17** 로 저장되고 앱 계약(`analysis.ts:1133`)
에도 열려 있다. 그런데 **z 채널이 전부 0.0** 이다 — 3D 모양의 그릇에 2D 가 담겨 있다.

로컬 저장 doc 8건 전수:

```
docs_after/elbowtwistsisterFault   180프레임   z std 0.0000   [0.0, 0.0]
docs_after/kipupFault               68프레임   z std 0.0000   [0.0, 0.0]
docs_after/pdshapeCorrect          159프레임   z std 0.0000   [0.0, 0.0]
docs_after/powerspinFault           83프레임   z std 0.0000   [0.0, 0.0]
docs_before/* (같은 4건)                       z std 0.0000   [0.0, 0.0]
```

`31-CLOSEOUT.md` 의 *"2D 자세 비교 뷰어 … 회전 없음(RTMW depth 부재로 정직한
회전 불가)"* 이 정확했다. 운영 엔진은 RTMW **2D**(`rtmw-x-384.onnx`)이고,
3D 리프터(`pose_lifters/motionbert_lifter.py`, `mediapipe_to_h36m17.py`)는
**`backend/research/` 안에서만** 불린다 — 운영 경로(`runpod_inference/server.py`,
`functions/pipeline/app.py`)에 배선 0.

## 그림 — `avatar-depth-isolated.png`

**같은 프레임·같은 자세에서 z 만 없앤 것**과 대조했다(변수 1개 고정).
입력 = `gate_in/power-spin.mp4` 8초, 9fps 74프레임, MediaPipe Pose(heavy)
`pose_world_landmarks` → COCO-17 매핑.

| | 0도 | 30도 | 60도 | 90도 |
|---|---|---|---|---|
| **z=0 (오늘)** | 정상 | 납작한 판지 | 납작한 판지 | **선으로 붕괴** |
| **z 복원** | 정상 | 입체 유지 | 입체 유지 | **옆모습이 읽힌다** |

실측 z 표준편차: 오늘 저장분 **0.0000** / MediaPipe **0.1597** (z/x 비 0.920).

## 이 그림이 말하는 것과 말하지 않는 것

**말하는 것**
- "아바타를 손가락으로 돌려본다"는 **깊이가 있어야만 성립**한다. 오늘 데이터로
  뷰어를 붙이면 90도에서 선이 된다.
- 아바타는 **측정된 관절을 그리는 결정론적 렌더**라 환각이 구조적으로 불가능하다.
  belle 이 2026-07-20 에 회전 영상을 끈 사유(*"없는 결함을 만들어내는 시각물"*)가
  아바타에는 성립하지 않는다.

**말하지 않는 것 (과대해석 금지)**
- **MediaPipe 가 정답이라는 뜻이 아니다.** 여기서는 "깊이가 있으면 어떻게 보이는가"를
  보이려고 쓴 대역일 뿐이다. 우리 실측으로 **MP 단독 22.8점 → MP+MotionBERT 81.2점**
  ([[lifter-mp-motionbert-decision]]) 이므로 단독 사용은 부족하다.
- **점수 정확도와 무관하다.** 관절 좌표가 틀리면 아바타도 똑같이 틀린다. 이것은
  시각화 트랙이지 정확도 트랙이 아니다 — 자리는 "참고하세요 코너"(비채점)다.
- 재현 스크립트 `render_skeleton.py` 는 PIL 만 쓴다(신규 의존 0). MediaPipe 는
  격리 venv 에 설치해 썼고 리포에 들이지 않았다. macOS 함정: `mediapipe 1.0.1` 은
  Metal 서비스 오류로 죽는다 — `0.10.30` + `MEDIAPIPE_DISABLE_GPU=1` +
  `delegate=CPU` + `RunningMode.IMAGE` 로 통과.

## 그래서 막힌 곳은 하나

**2D → 3D 리프팅 배선.** MotionBERT 는 **Apache 2.0(상업 OK)** 이고
2026-05-31 belle 5영상 검증에서 4/5 PASS(평균 81.2)를 받은 물건이며 코드가
이미 리포에 있다. RTMW 로 피벗하면서 운영 경로에서 빠졌을 뿐이다.

기사가 추천한 **WHAM / SMPL 은 우리가 못 쓴다** — 비상업 라이선스
([[license-blocklist-pose]]), belle 이 "완전 최후의 보류"로 못 박음.
