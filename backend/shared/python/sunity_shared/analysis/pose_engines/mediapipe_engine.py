"""MediaPipePoseEngine — MediaPipe Tasks API BlazePose Heavy 어댑터.

Phase 1 D-01/D-02/D-03/D-04/D-05 + REVIEWS H-2 박제.

D-01: BlazePose Heavy variant (최고 정확도 — 폴 가림/접힌 자세)
D-02: MediaPipe Tasks API (PoseLandmarker, .task 모델 파일, VIDEO RunningMode)
D-03: world landmarks(metric 3D) + image landmarks(UI 오버레이용) 둘 다 추출
D-04: raw 33 전체 보존 + COCO-17 + 폴 확장(toe/heel/grip)
D-05: confidence = visibility × presence, uncertainty_proxy = 1 - confidence

REVIEWS:
  H-2: module-level mediapipe import 절대 금지 — __init__ 내부에서만 lazy import.
       Lambda ARM64 미지원 fail-fast (ARM64 wheel 없음 — Pitfall 1 / RESEARCH §Standard Stack).
       RunPod 서버(x86_64)에서만 동작.

Pitfalls (RESEARCH §Common Pitfalls):
  Pitfall 1: MediaPipe wheel은 Linux ARM64 미지원 → Lambda ARM64 직접 배포 불가.
             Lambda는 RunPod 위임 모드만 사용. 폴백 경로에서 MediaPipe import 금지.
  Pitfall 2: VIDEO RunningMode timestamp 단조 증가 강제.
             timestamp_ms = int(t * 1000 / self._target_fps)
  Pitfall 4: protobuf 의존성 버전 충돌 가능 — try/except import 가드.

Factory: create_with_landmarker(landmarker, target_fps) — DI 패턴, 단위 테스트용.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from ..interfaces import NoHumanError
from ..pose_frame import PoseFrame, PoleAxis
from ..adapters.mediapipe_to_coco17 import convert_landmarks_to_coco17_and_pole_ext

# mediapipe, cv2, scipy 등 heavy library는 module level에서 import 금지 (H-2 박제).
# MediaPipePoseEngine.__init__ 내부에서만 lazy import.

_DEFAULT_MODEL_ENV = "MEDIAPIPE_POSE_MODEL_PATH"
_DEFAULT_MODEL_FILENAME = "pose_landmarker_heavy.task"

__all__ = ["MediaPipePoseEngine"]


class MediaPipePoseEngine:
    """MediaPipe Tasks API PoseLandmarker 어댑터.

    H-2 박제: mediapipe import는 __init__ 내부에서만 수행.
    모듈 로드만으로는 mediapipe가 필요 없다 — Lambda fail-fast 안전.
    인스턴스화 시점에 mediapipe import 실패 → RuntimeError (ARM64/미설치 안내).

    단위 테스트: create_with_landmarker(mock_landmarker) factory 사용.
    """

    def __init__(
        self,
        model_path: str | None = None,
        target_fps: float = 9.0,
    ) -> None:
        """MediaPipe PoseLandmarker 초기화.

        H-2 박제: mediapipe lazy import — 인스턴스화 시점에만 시도.
        Pitfall 1 박제: ARM64 미지원 RuntimeError + RunPod 안내.
        Pitfall 4 박제: try/except import 가드.

        Args:
            model_path: pose_landmarker_heavy.task 경로.
                        None이면 MEDIAPIPE_POSE_MODEL_PATH env var 참조.
            target_fps: 영상 target FPS (timestamp 단조 계산에 사용 — Pitfall 2).
        """
        # H-2 박제: 인스턴스화 시점에만 lazy import
        try:
            import mediapipe as mp  # noqa: PLC0415
            from mediapipe.tasks import python as mp_python  # noqa: PLC0415
            from mediapipe.tasks.python import vision as mp_vision  # noqa: PLC0415
        except ImportError as e:
            raise RuntimeError(
                "mediapipe library 미설치 — RunPod 서버(x86_64)에서만 동작. "
                "Lambda ARM64 미지원 (Pitfall 1 / REVIEWS H-2). "
                "모듈 import는 깨끗하지만 인스턴스화는 mediapipe 필요. "
                f"원인: {e}"
            ) from e

        # 모델 파일 경로 결정 + 검증
        resolved_path = model_path or os.environ.get(_DEFAULT_MODEL_ENV, "")
        if not resolved_path or not Path(resolved_path).exists():
            raise RuntimeError(
                f"{_DEFAULT_MODEL_FILENAME} 모델 파일 없음: {resolved_path!r}. "
                f"{_DEFAULT_MODEL_ENV} env 또는 명시적 경로 필요. "
                "RESEARCH §Runtime State Inventory — Pod setup.sh에서 다운로드."
            )

        # PoseLandmarkerOptions: VIDEO mode, D-01 Heavy variant
        options = mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=resolved_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        self._target_fps = target_fps

    @classmethod
    def create_with_landmarker(
        cls,
        landmarker: object,
        target_fps: float = 9.0,
    ) -> "MediaPipePoseEngine":
        """DI factory — 단위 테스트가 mock landmarker 주입.

        mediapipe import skip — 테스트 환경(macOS, ARM64)에서 안전하게 사용.
        """
        instance = cls.__new__(cls)
        instance._landmarker = landmarker
        instance._target_fps = target_fps
        return instance

    def estimate(
        self,
        frames: np.ndarray,
        pole_axis: PoleAxis,
    ) -> list[PoseFrame]:
        """프레임 시퀀스 → list[PoseFrame].

        D-02/D-03: detect_for_video 호출 + world+image landmark 추출.
        Pitfall 2: timestamp_ms = int(t * 1000 / self._target_fps) 단조 증가.
        H-3: pole_axis 인자를 각 PoseFrame에 보존.
        H-4: reliability는 convert_landmarks_to_coco17_and_pole_ext 내부에서 산출.
        전 프레임 미감지 시 NoHumanError("MediaPipe 전 프레임 미감지").
        """
        T = len(frames)
        if T == 0:
            return []

        pose_frames: list[PoseFrame] = []
        detected_count = 0

        for t in range(T):
            # Pitfall 2: timestamp 단조 증가 보장
            timestamp_ms = int(t * 1000 / self._target_fps)

            # MediaPipe Image 객체 생성 — DI mock에서는 frames[t] 실제 사용 안 함
            # 실제 mediapipe 환경에서는 mp.Image(image_format=..., data=frames[t]) 필요
            # mock은 detect_for_video 시그니처만 맞추면 됨
            image = self._create_image(frames[t])
            result = self._landmarker.detect_for_video(image, timestamp_ms)

            # 감지 결과 확인
            if (
                not result.pose_landmarks
                or not result.pose_world_landmarks
            ):
                # 미감지 프레임 → PoseFrame.empty + pole_axis 보존 (H-3)
                pose_frames.append(
                    PoseFrame.empty(
                        frame_index=t,
                        timestamp_ms=timestamp_ms,
                        pole_axis=pole_axis,
                    )
                )
                continue

            detected_count += 1
            world_landmarks = result.pose_world_landmarks[0]
            image_landmarks = result.pose_landmarks[0]

            frame = convert_landmarks_to_coco17_and_pole_ext(
                frame_index=t,
                timestamp_ms=timestamp_ms,
                world_landmarks=world_landmarks,
                image_landmarks=image_landmarks,
                pole_axis=pole_axis,  # H-3 박제
            )
            pose_frames.append(frame)

        # 전 프레임 미감지 시 NoHumanError
        if detected_count == 0:
            raise NoHumanError(
                f"MediaPipe 전 프레임 미감지 ({T}개 중 0개). "
                "영상에 사람이 없거나 카메라 각도를 확인하세요."
            )

        return pose_frames

    def _create_image(self, frame_rgb: np.ndarray) -> object:
        """numpy RGB 프레임 → MediaPipe Image 객체.

        mock 환경에서는 detect_for_video가 image 인자를 사용하지 않으므로
        simple wrapper 또는 frame 자체를 반환해도 동작.
        실제 mediapipe 환경에서는 MediaPipe Image 생성.
        """
        try:
            import mediapipe as mp  # noqa: PLC0415
            return mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame_rgb.astype(np.uint8),
            )
        except (ImportError, AttributeError):
            # mock 환경(mediapipe 미설치 또는 DI 주입) — frame 자체 반환
            return frame_rgb
