"""RTMWLifterPoseEngine — 옵션 B 어댑터 stub (Plan 01-22 Task 1).

D-18 옵션 B: 단일 카메라 3D path = RTMW 2D + MotionBERT lifter (plan 07 재사용).
  RTMWPoseEngine (plan 21) 2D 산출 → COCO-17 → H3.6M 17 변환 →
  MotionBertLifter.lift() → (T, 17, 3) → COCO-17 역변환 → PoseFrame keypoints_3d 교체.

본 파일 (Plan 22 Task 1) = stub 상태 — Task 2 belle checkpoint 응답이
"옵션 B (option_b)" 일 때만 estimate() 실 구현. 옵션 A 선택 시 본 모듈은
plan 24 에서 R&D 격리 대상 (또는 stub 유지).

PoseEngine Protocol 호환 (D-24):
  estimate(frames: np.ndarray, pole_axis: PoleAxis) → list[PoseFrame]

기존 MediaPipeWithLifterEngine (mediapipe_lifter_engine.py) 의 패턴과 동일:
  1. inner 2D engine (RTMWPoseEngine) 가 PoseFrame 리스트 (keypoints_3d 는
     z=0 패딩 또는 score 기반) 반환.
  2. PoseFrame 에서 2D xy 추출 후 H3.6M 17 변환.
  3. MotionBertLifter.lift() → (T, 17, 3).
  4. H3.6M 17 → COCO-17 역변환 → PoseFrame 의 keypoints_3d 교체.
  5. pole_axis 보존 (H-3), keypoints_3d_pole_aligned 재산출.

plan 17 mapping fix 정합:
  Cycle 3 audit (5 mapping source 58 row canonical) 박제 — H3.6M ↔ COCO-17
  변환은 `pose_lifters/mediapipe_to_h36m17.py` 의 `h36m17_to_coco17_subset`
  를 그대로 활용 (canonical 검증 완료). RTMW → H3.6M 변환은 plan 17 에서
  검증된 변환을 RTMW 17 keypoint subset 으로 재이식 (Task 2 belle 결정 후).

H-2 박제: mediapipe / mmpose / torch / rtmlib module-level import 0.
  모든 heavy import 는 인스턴스화 시점 또는 estimate() 내 lazy.

Plan 22 Task 1 (현재 상태):
  - 클래스 + Protocol 시그니처 박제 완료.
  - __init__ + create_with_engines DI factory 박제 완료.
  - estimate() 는 NotImplementedError raise — 옵션 B 미선택 stub.
  - Task 2 (belle 결정 = option_b) 후 실 구현 진행.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ...pose_frame import PoseFrame, PoleAxis

# rtmlib / torch / mediapipe 은 module-level import 금지 (H-2 박제).
# RTMWPoseEngine / MotionBertLifter 도 인스턴스화 시점에서만 lazy import.

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# ── RTMWLifterPoseEngine (stub) ───────────────────────────────────────────

class RTMWLifterPoseEngine:
    """RTMW 2D + MotionBERT 3D lifter 복합 어댑터 (옵션 B, PoseEngine Protocol 구현 stub).

    Plan 22 Task 1 단계 = stub. estimate() 호출 시 NotImplementedError.
    Task 2 belle = "option_b" 응답 후 실 구현 (mediapipe_lifter_engine.py 패턴
    동일):
      1. RTMWPoseEngine.estimate(frames, pole_axis) → list[PoseFrame] (RTMW 2D).
      2. PoseFrame.keypoints_3d 의 COCO-17 xy 추출 (z 폐기).
      3. COCO-17 → H3.6M 17 변환 (plan 17 mapping fix 정합 — canonical 박제).
      4. MotionBertLifter.lift() → (T, 17, 3) H3.6M xyz.
      5. H3.6M 17 → COCO-17 역변환.
      6. 원본 PoseFrame 의 keypoints_3d / keypoints_3d_pole_aligned / reliability
         교체. raw_keypoints_133, keypoints_2d, raw_landmarks_33 보존 (D-20).

    DI 패턴: create_with_engines(rtmw_engine, lifter) — 단위 테스트용 (mock
    RTMWPoseEngine + mock MotionBertLifter 주입). mediapipe_lifter_engine.py
    의 create_with_engines 와 동일 패턴.
    """

    def __init__(
        self,
        manifest_path: Any = None,
        target_fps: float = 30.0,
        rtmw_engine: Any = None,
        lifter: Any = None,
    ) -> None:
        """RTMWLifterPoseEngine 초기화.

        Plan 22 Task 1 stub — Task 2 belle = "option_b" 후 실 구현 진행 시:
          1. RTMWPoseEngine lazy 생성 (manifest_path 검증 포함).
          2. MotionBertLifter lazy 생성 (MOTIONBERT_ROOT / MOTIONBERT_WEIGHTS env
             또는 명시 인자).
          3. plan 17 mapping fix 정합 검증 (canonical 박제).

        Args:
            manifest_path: weights_manifest.json 경로 (RTMWPoseEngine 용).
            target_fps: 영상 target FPS.
            rtmw_engine: 이미 생성된 RTMWPoseEngine 인스턴스 (None 이면 lazy 생성).
            lifter: 이미 생성된 MotionBertLifter 인스턴스 (None 이면 lazy 생성).

        Raises:
            NotImplementedError: 옵션 B 미선택 stub (Plan 22 Task 1 현재 상태).
        """
        # 인자 보존 (Task 2 실 구현 시 사용)
        self._manifest_path = manifest_path
        self._target_fps = target_fps
        self._rtmw_engine = rtmw_engine
        self._lifter = lifter

        # 옵션 B 미선택 stub — RTMWPoseEngine + MotionBertLifter 초기화 미구현.
        raise NotImplementedError(
            "RTMWLifterPoseEngine 은 옵션 B 미선택 stub 상태입니다 "
            "(Plan 01-22 Task 1). belle 가 three_d_path_decision.md §5 에 "
            "`selected: option_b` 박제 후 Task 2 에서 본 __init__ 의 "
            "RTMWPoseEngine + MotionBertLifter lazy 생성 + plan 17 mapping "
            "fix 정합 검증을 구현하세요."
        )

    @classmethod
    def create_with_engines(
        cls,
        rtmw_engine: Any,
        lifter: Any,
        target_fps: float = 30.0,
    ) -> "RTMWLifterPoseEngine":
        """DI factory — 단위 테스트가 mock RTMWPoseEngine + mock MotionBertLifter 주입.

        Plan 22 Task 1 stub: factory 자체는 통과 가능 (인스턴스 반환), estimate()
        호출 시점에 NotImplementedError raise. Task 2 belle = "option_b" 응답
        후 실 구현 시 본 factory 가 단위 테스트 진입점.

        mediapipe / rtmlib / torch / mmpose 의 lazy import 모두 skip — 테스트
        환경에서 안전하게 사용.

        Args:
            rtmw_engine: RTMWPoseEngine 인스턴스 (mock 가능, estimate(frames, pole_axis) 만족).
            lifter: MotionBertLifter 인스턴스 (mock 가능, lift(landmarks_2d) 만족).
            target_fps: 영상 target FPS.
        """
        instance = cls.__new__(cls)
        instance._manifest_path = None
        instance._rtmw_engine = rtmw_engine
        instance._lifter = lifter
        instance._target_fps = target_fps
        return instance

    def estimate(
        self,
        frames: np.ndarray,
        pole_axis: PoleAxis,
    ) -> list[PoseFrame]:
        """프레임 시퀀스 → list[PoseFrame] (RTMW 2D xy + MotionBERT 3D z).

        Plan 22 Task 1 stub: NotImplementedError raise.
        Task 2 belle = "option_b" 응답 후 실 구현 (mediapipe_lifter_engine.py
        패턴 정합):
          1. RTMWPoseEngine.estimate(frames, pole_axis) → list[PoseFrame].
          2. PoseFrame.keypoints_3d 의 COCO-17 xy 추출.
          3. COCO-17 → H3.6M 17 변환 (plan 17 canonical 박제).
          4. MotionBertLifter.lift() → (T, 17, 3) H3.6M xyz.
          5. H3.6M 17 → COCO-17 역변환.
          6. 원본 PoseFrame 교체 (dataclass replace). pole_axis 보존 (H-3),
             keypoints_3d_pole_aligned 재산출.
          7. raw_keypoints_133 / keypoints_2d / raw_landmarks_33 보존 (D-20).

        Args:
            frames: (T, H, W, 3) RGB uint8 배열.
            pole_axis: PoleDetector 산출 PoleAxis (D-10/H-3).

        Returns:
            list[PoseFrame] — len = T (실 구현 후).

        Raises:
            NotImplementedError: 옵션 B 미선택 stub (Plan 22 Task 1 현재 상태).
        """
        raise NotImplementedError(
            "RTMWLifterPoseEngine.estimate() 는 옵션 B 미선택 stub 입니다 "
            "(Plan 01-22 Task 1). belle 가 three_d_path_decision.md §5 에 "
            "`selected: option_b` 박제 후 Task 2 에서 본 메서드의 RTMW 2D 추론 "
            "+ MotionBERT lift + H3.6M ↔ COCO-17 변환 흐름을 구현하세요. "
            f"입력 형상: frames={frames.shape}, pole_axis={pole_axis!r}."
        )
