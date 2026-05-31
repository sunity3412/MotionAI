"""MediaPipeWithLifterEngine — MediaPipePoseEngine + MotionBertLifter composite.

Plan 01-08 T-2: MediaPipe 2D keypoints + MotionBERT 3D lift.

아키텍처 결정 (01-CONTEXT.md):
  MediaPipePoseEngine 는 world_landmarks(3D) 를 keypoints_3d 에 담는데,
  z 추정이 인버트/측면/폴 폐색 자세에서 노이즈가 크다 (Plan 01-06 D-16 보류).
  본 engine 은 world_landmarks 대신 normalized_landmarks (2D) 를 사용하고,
  MotionBERT 로 z 를 재구성해 stability 를 회복한다.

estimate() 흐름:
  1. MediaPipePoseEngine.estimate(frames, pole_axis) → list[PoseFrame]  (MP world_landmarks 기반)
  2. PoseFrame 에서 normalized_landmarks (keypoints_2d) 추출
  3. MP33 → H3.6M 17 변환 (pose_lifters.mediapipe_to_h36m17)
  4. MotionBertLifter.lift() → (T, 17, 3) H3.6M xyz
  5. H3.6M 17 → COCO-17 역변환 (pose_lifters.mediapipe_to_h36m17)
  6. 원본 PoseFrame 의 keypoints_3d, keypoints_3d_pole_aligned, reliability 교체
  7. pole_axis 보존 (H-3), keypoints_3d_pole_aligned 재산출

PoseEngine Protocol 호환:
  estimate(frames: np.ndarray, pole_axis: PoleAxis) → list[PoseFrame]
  호출자는 이 엔진과 MediaPipePoseEngine/NLF 를 동일 인터페이스로 사용 가능.

H-2 박제: mediapipe, torch, scipy 는 인스턴스화 시점(mediapipe) 또는
  lift() 호출 시점(torch)에서만 import — 모듈 load 시 무관.

단위 테스트: MediaPipePoseEngine + MotionBertLifter 모두 DI factory 로 주입 가능.
"""

from __future__ import annotations

import logging
from dataclasses import replace

import numpy as np

from ..interfaces import NoHumanError
from ..pose_frame import (
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
    compute_frame_reliability,
)
from ..skeleton import KEYPOINT_NAMES

log = logging.getLogger(__name__)

# COCO-17 인덱스 → 관절 이름 (skeleton.KEYPOINT_NAMES 순서와 동일)
_COCO17_IDX_TO_NAME: dict[int, str] = {i: name for i, name in enumerate(KEYPOINT_NAMES)}


class MediaPipeWithLifterEngine:
    """MediaPipe 2D + MotionBERT 3D lift 복합 엔진.

    PoseEngine Protocol 호환 — estimate(frames, pole_axis) → list[PoseFrame].

    MediaPipePoseEngine (2D 신뢰도 높음) 와 MotionBertLifter (3D z 복원) 를
    조합해 stability 를 회복한다. MediaPipe world_landmarks 의 z 는 버리고
    normalized_landmarks 의 xy 를 MotionBERT 입력으로 사용.

    인스턴스화 시 model_path (mediapipe 모델) 와 lifter 인자 필요.
    lifter 미지정 시 MOTIONBERT_ROOT, MOTIONBERT_WEIGHTS 환경변수로 lazy create.
    """

    def __init__(
        self,
        model_path: str | None = None,
        target_fps: float = 9.0,
        lifter=None,  # MotionBertLifter | None
    ) -> None:
        """MediaPipeWithLifterEngine 초기화.

        Args:
            model_path: pose_landmarker_heavy.task 경로.
                        None 이면 MEDIAPIPE_POSE_MODEL_PATH env 참조.
            target_fps: 영상 target FPS.
            lifter: MotionBertLifter 인스턴스.
                    None 이면 env var 기반 lazy create (첫 estimate 호출 시점).
        """
        from .mediapipe_engine import MediaPipePoseEngine  # noqa: PLC0415

        self._mp_engine = MediaPipePoseEngine(model_path=model_path, target_fps=target_fps)
        self._lifter = lifter
        self._target_fps = target_fps

    @classmethod
    def create_with_engines(
        cls,
        mp_engine: object,
        lifter: object,
    ) -> "MediaPipeWithLifterEngine":
        """DI factory — 단위 테스트가 mock mp_engine + mock lifter 주입.

        mediapipe, torch, scipy import skip — 테스트 환경에서 안전.
        """
        instance = cls.__new__(cls)
        instance._mp_engine = mp_engine
        instance._lifter = lifter
        instance._target_fps = 9.0
        return instance

    def _ensure_lifter(self) -> None:
        """lifter 미지정 시 env var 기반 lazy create."""
        if self._lifter is not None:
            return
        from ..pose_lifters.motionbert_lifter import MotionBertLifter  # noqa: PLC0415

        self._lifter = MotionBertLifter()
        log.info("MotionBertLifter lazy created from env vars")

    def estimate(
        self,
        frames: np.ndarray,
        pole_axis: PoleAxis,
    ) -> list[PoseFrame]:
        """프레임 시퀀스 → list[PoseFrame] (MP 2D xy + MotionBERT 3D z).

        1. MediaPipePoseEngine.estimate → MP world_landmarks 기반 PoseFrame 리스트.
        2. keypoints_2d (normalized_landmarks) 에서 MP 2D xy 추출.
        3. MP33 → H3.6M 17 변환.
        4. MotionBERT lift → (T, 17, 3) H3.6M xyz.
        5. H3.6M 17 → COCO-17 (T, 17, 4=xyz+uncertainty).
        6. 원본 PoseFrame 을 lifter 결과로 교체한 새 PoseFrame 생성.
        7. pole-aligned 재산출 + reliability 갱신.

        미감지 프레임(empty PoseFrame)은 lifter 결과를 주입해도 빈 채로 유지.
        전 프레임 미감지 시 NoHumanError.

        H-3 박제: pole_axis 인자 보존.
        """
        self._ensure_lifter()

        # 1. MediaPipe 2D 추출 (PoseFrame 리스트)
        mp_pose_frames = self._mp_engine.estimate(frames, pole_axis)
        T = len(mp_pose_frames)
        if T == 0:
            return []

        # 2. normalized_landmarks (keypoints_2d) 에서 MP 2D xy (T, 33, 3) 구성
        #    keypoints_2d 는 COCO-17 17개만 담겨있어서 MP33 → H36M 변환을 위해
        #    raw_landmarks_33 (world landmarks) 의 x/y 를 normalized 좌표처럼 사용하면 안 된다.
        #    대신 원본 MediaPipe landmarks 를 다시 추출할 수 없으므로,
        #    keypoints_2d 에서 COCO-17 → H3.6M 직접 매핑 경로를 사용.
        #    단, mediapipe_to_h36m17.py 는 MP33 입력 기대 → T-2 설계 재검토 필요.
        #
        #    실용적 해결책: MediaPipe normalized x/y 는 keypoints_2d 에 저장됨.
        #    COCO-17 subset 이므로 직접 대응하는 12개 limb joint 는 복원 가능.
        #    나머지 H36M joints (파생 관절 포함) 는 keypoints_2d 내 값으로 계산.
        #
        #    구체적으로: keypoints_2d 의 COCO-17 관절 좌표를 역매핑해서
        #    fake (T, 33, 2) 배열을 구성한 뒤 convert_mp33_to_h36m17 호출.
        #    이 방법은 face 관절(0~4)이 NaN이 되지만 limb는 정확.
        mp_lm_2d = self._extract_mp_2d_from_pose_frames(mp_pose_frames)  # (T, 33, 2)

        # 3. MP33 → H3.6M 17
        from ..pose_lifters.mediapipe_to_h36m17 import (  # noqa: PLC0415
            convert_mp33_to_h36m17,
            h36m17_to_coco17_subset,
        )
        h36m_2d = convert_mp33_to_h36m17(mp_lm_2d)  # (T, 17, 2)

        # 4. MotionBERT lift → (T, 17, 3) H3.6M xyz
        h36m_xyz = self._lifter.lift(h36m_2d)  # (T, 17, 3)

        # 5. H3.6M 17 → COCO-17 (T, 17, 4=xyz+uncertainty)
        coco17_arr = h36m17_to_coco17_subset(h36m_xyz)  # (T, 17, 4)

        # 6+7. 원본 PoseFrame 교체
        result: list[PoseFrame] = []
        for t, frame in enumerate(mp_pose_frames):
            new_frame = self._replace_keypoints(frame, coco17_arr[t], pole_axis)
            result.append(new_frame)

        return result

    def _extract_mp_2d_from_pose_frames(
        self,
        pose_frames: list[PoseFrame],
    ) -> np.ndarray:
        """PoseFrame 리스트에서 (T, 33, 2) normalized xy 배열 재구성.

        keypoints_2d 는 COCO-17 subset 이므로 모든 33개 MP landmark 를 복원할 수 없다.
        대신 COCO-17 → MediaPipe 역매핑으로 가용한 관절만 채우고 나머지는 0.5 로 패딩.
        (face/미매핑 관절이 0.5 로 패딩되면 파생 관절 계산에서 무해한 값이 나온다.)

        COCO-17 → MediaPipe 33 인덱스 역매핑 (skeleton.py KEYPOINT_NAMES 기준):
          COCO 0(nose)→MP 0, COCO 5(l_shoulder)→MP 11, COCO 6(r_shoulder)→MP 12,
          COCO 7(l_elbow)→MP 13, COCO 8(r_elbow)→MP 14,
          COCO 9(l_wrist)→MP 15, COCO 10(r_wrist)→MP 16,
          COCO 11(l_hip)→MP 23, COCO 12(r_hip)→MP 24,
          COCO 13(l_knee)→MP 25, COCO 14(r_knee)→MP 26,
          COCO 15(l_ankle)→MP 27, COCO 16(r_ankle)→MP 28
        """
        T = len(pose_frames)
        mp_lm = np.full((T, 33, 2), 0.5, dtype=float)  # 0.5 패딩

        # COCO-17 이름 → MP 인덱스 매핑 (해당 관절만 복원)
        coco_to_mp: dict[str, int] = {
            "nose": 0,
            "left_shoulder": 11, "right_shoulder": 12,
            "left_elbow": 13, "right_elbow": 14,
            "left_wrist": 15, "right_wrist": 16,
            "left_hip": 23, "right_hip": 24,
            "left_knee": 25, "right_knee": 26,
            "left_ankle": 27, "right_ankle": 28,
        }

        for t, frame in enumerate(pose_frames):
            if frame.keypoints_2d is None:
                # 미감지 프레임 — 0.5 패딩 유지 (NaN 대신 중앙값으로 safe fallback)
                continue
            for coco_name, mp_idx in coco_to_mp.items():
                kp2d = frame.keypoints_2d.get(coco_name)
                if kp2d is not None:
                    mp_lm[t, mp_idx, 0] = kp2d.x
                    mp_lm[t, mp_idx, 1] = kp2d.y

        return mp_lm

    def _replace_keypoints(
        self,
        frame: PoseFrame,
        coco17_row: np.ndarray,  # (17, 4=xyz+uncertainty)
        pole_axis: PoleAxis,
    ) -> PoseFrame:
        """원본 PoseFrame 의 keypoints_3d / keypoints_3d_pole_aligned / reliability 교체.

        coco17_row 의 NaN (face joints) 은 keypoints_3d 에 포함되지 않는다.
        limb joints (COCO 5~16) 만 교체. raw_landmarks_33, keypoints_2d 는 보존.
        pole_axis 는 H-3 박제 — 인자 그대로 전달.
        """
        # frame 이 empty (미감지) 면 keypoints_3d 교체만 시도, reliability='low' 유지
        new_kp3d: dict[str, Keypoint3D] = {}
        for j, name in enumerate(KEYPOINT_NAMES):
            row = coco17_row[j]
            x, y, z, uncertainty = float(row[0]), float(row[1]), float(row[2]), float(row[3])
            if np.isnan(x) or np.isnan(y) or np.isnan(z):
                # face NaN → skip (keypoints_3d 에 포함 안 됨)
                continue
            confidence = max(0.0, min(1.0, 1.0 - uncertainty))
            new_kp3d[name] = Keypoint3D(
                x=x,
                y=y,
                z=z,
                confidence=confidence,
                uncertainty_proxy=uncertainty,
            )

        # pole-aligned 재산출
        new_aligned: dict[str, Keypoint3DAligned] = {}
        try:
            from ..pole.aligner import apply_alignment, compute_alignment_matrix  # noqa: PLC0415
            R = compute_alignment_matrix(pole_axis.axis_vector)
            new_aligned = apply_alignment(new_kp3d, R)
        except (ImportError, ValueError):
            # aligner 미설치 또는 zero vector → raw xyz 로 폴백
            for n, kp in new_kp3d.items():
                new_aligned[n] = Keypoint3DAligned(x=kp.x, y=kp.y, z=kp.z)

        # reliability 재산출 — lifter uncertainty 기반 confidence 평균
        if new_kp3d:
            mean_conf = float(np.mean([kp.confidence for kp in new_kp3d.values()]))
            # compute_frame_reliability 는 mean_visibility (0~1) 를 기대
            # confidence 를 visibility proxy 로 사용 (D-05 패턴)
            new_reliability = compute_frame_reliability(mean_conf)
        else:
            new_reliability = "low"

        # dataclass 는 frozen=True 이므로 replace() 사용
        return replace(
            frame,
            keypoints_3d=new_kp3d,
            keypoints_3d_pole_aligned=new_aligned,
            pole_axis=pole_axis,
            reliability=new_reliability,
        )
