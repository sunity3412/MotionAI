"""RTMWLifterPoseEngine — 옵션 B 어댑터 (Plan 01-22 Task 2 실 구현).

D-18 옵션 B: 단일 카메라 3D path = RTMW 2D + MotionBERT lifter (plan 07 재사용).
  RTMWPoseEngine (plan 21) 2D 산출 → COCO-17 → H3.6M 17 변환 →
  MotionBertLifter.lift() → (T, 17, 3) → COCO-17 역변환 → PoseFrame keypoints_3d 교체.

본 파일 (Plan 22 Task 2) = belle = "option_b" (2026-06-03 박제, 본 plan
three_d_path_decision.md §5) 응답 후 실 구현. 옵션 A (`rtmw3d_engine.py`)
는 NotImplementedError 유지 (plan 24 R&D 격리 입력).

PoseEngine Protocol 호환 (D-24):
  estimate(frames: np.ndarray, pole_axis: PoleAxis) → list[PoseFrame]

기존 MediaPipeWithLifterEngine (mediapipe_lifter_engine.py) 의 패턴과 동일:
  1. inner 2D engine (RTMWPoseEngine) 가 PoseFrame 리스트 (keypoints_3d 의
     xy 가 RTMW 픽셀 좌표, z=0) 반환.
  2. PoseFrame.keypoints_3d 에서 COCO-17 17개 xy 추출.
  3. COCO-17 → H3.6M 17 변환 (limb 12 직접 매핑 + 파생 5: hip / spine / thorax /
     neck_nose / head).
  4. MotionBertLifter.lift() → (T, 17, 3) H3.6M xyz.
  5. H3.6M 17 → COCO-17 역변환 (`h36m17_to_coco17_subset`) → (T, 17, 4=xyz+uncertainty).
  6. 원본 PoseFrame 의 keypoints_3d / keypoints_3d_pole_aligned / reliability
     교체. raw_keypoints_133, keypoints_2d, pole_axis, pole_extension_landmarks
     보존 (D-20 / H-3).

plan 17 mapping fix 정합:
  Cycle 3 audit (5 mapping source 58 row canonical) 박제 — H3.6M ↔ COCO-17
  변환은 `pose_lifters/mediapipe_to_h36m17.py` 의
  `H36M_TO_COCO17_LIMB_PAIRS` (12 pair canonical) + `h36m17_to_coco17_subset`
  를 그대로 활용. 좌우 swap_ratio 회귀 방지: 본 모듈에서 좌/우 인덱스
  취급 시 COCO-17 KEYPOINT_NAMES 순서를 단일 source of truth 로 사용
  (skeleton.py KEYPOINT_NAMES).

H-2 박제: mediapipe / mmpose / torch / rtmlib module-level import 0.
  모든 heavy import 는 인스턴스화 시점 또는 estimate() 내 lazy.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

import numpy as np

from ...pose_frame import (
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
    compute_frame_reliability,
)
from ...skeleton import KEYPOINT_NAMES

# rtmlib / torch / mediapipe 은 module-level import 금지 (H-2 박제).
# RTMWPoseEngine / MotionBertLifter 도 인스턴스화 시점에서만 lazy import.

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# COCO-17 인덱스 ↔ 이름 (KEYPOINT_NAMES 와 동일 — 단일 source of truth, plan 17 정합)
_COCO17_IDX_TO_NAME: dict[int, str] = {i: name for i, name in enumerate(KEYPOINT_NAMES)}
_COCO17_NAME_TO_IDX: dict[str, int] = {name: i for i, name in enumerate(KEYPOINT_NAMES)}

# H3.6M 17-joint 인덱스 상수 (mediapipe_to_h36m17.py 와 동일 컨벤션, 단일 source of truth)
_H36M_HIP = 0
_H36M_R_HIP = 1
_H36M_R_KNEE = 2
_H36M_R_FOOT = 3
_H36M_L_HIP = 4
_H36M_L_KNEE = 5
_H36M_L_FOOT = 6
_H36M_SPINE = 7
_H36M_THORAX = 8
_H36M_NECK_NOSE = 9
_H36M_HEAD = 10
_H36M_L_SHOULDER = 11
_H36M_L_ELBOW = 12
_H36M_L_WRIST = 13
_H36M_R_SHOULDER = 14
_H36M_R_ELBOW = 15
_H36M_R_WRIST = 16

_NUM_H36M_JOINTS = 17


# ── RTMWLifterPoseEngine (옵션 B 실 구현) ─────────────────────────────────

class RTMWLifterPoseEngine:
    """RTMW 2D + MotionBERT 3D lifter 복합 어댑터 (옵션 B, PoseEngine Protocol 구현).

    Plan 22 Task 2 (belle approved: option_b 박제 후) 실 구현:
      1. RTMWPoseEngine.estimate(frames, pole_axis) → list[PoseFrame] (RTMW 2D, z=0).
      2. PoseFrame.keypoints_3d 의 COCO-17 17개 xy 추출 → (T, 17, 2) 배열.
      3. COCO-17 → H3.6M 17 변환 (limb 12 직접 매핑 + 파생 5).
      4. MotionBertLifter.lift() → (T, 17, 3) H3.6M xyz.
      5. H3.6M 17 → COCO-17 역변환 → (T, 17, 4=xyz+uncertainty).
      6. 원본 PoseFrame 의 keypoints_3d / keypoints_3d_pole_aligned / reliability
         교체. raw_keypoints_133, keypoints_2d, pole_axis, pole_extension_landmarks
         보존 (D-20 / H-3).

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

        rtmw_engine / lifter 둘 다 None 이면 lazy 생성:
          - RTMWPoseEngine (plan 21) — manifest_path 검증 포함.
          - MotionBertLifter (plan 07) — MOTIONBERT_ROOT / MOTIONBERT_WEIGHTS env.

        하나라도 주입되면 본 __init__ 는 인자 보존만. 첫 estimate() 호출 시
        나머지 None 인 컴포넌트 만 lazy 생성 (`_ensure_components`).

        Args:
            manifest_path: weights_manifest.json 경로 (RTMWPoseEngine 용).
            target_fps: 영상 target FPS.
            rtmw_engine: 이미 생성된 RTMWPoseEngine 인스턴스 (None 이면 lazy 생성).
            lifter: 이미 생성된 MotionBertLifter 인스턴스 (None 이면 lazy 생성).
        """
        self._manifest_path = manifest_path
        self._target_fps = target_fps
        self._rtmw_engine = rtmw_engine
        self._lifter = lifter

    @classmethod
    def create_with_engines(
        cls,
        rtmw_engine: Any,
        lifter: Any,
        target_fps: float = 30.0,
    ) -> "RTMWLifterPoseEngine":
        """DI factory — 단위 테스트가 mock RTMWPoseEngine + mock MotionBertLifter 주입.

        mediapipe / rtmlib / torch / mmpose 의 lazy import 모두 skip — 테스트
        환경에서 안전하게 사용. estimate() 흐름 검증 진입점.

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

    def _ensure_components(self) -> None:
        """rtmw_engine / lifter 미지정 시 lazy 생성.

        rtmw_engine 은 plan 21 `RTMWPoseEngine` (manifest gate 적용).
        lifter 는 plan 07 `MotionBertLifter` (env var 기반 가중치 경로).
        """
        if self._rtmw_engine is None:
            from .rtmw_engine import RTMWPoseEngine  # noqa: PLC0415

            self._rtmw_engine = RTMWPoseEngine(
                manifest_path=self._manifest_path,
                target_fps=int(self._target_fps),
            )
            log.info("RTMWPoseEngine lazy created (manifest_path=%s)", self._manifest_path)

        if self._lifter is None:
            from ...pose_lifters.motionbert_lifter import MotionBertLifter  # noqa: PLC0415

            self._lifter = MotionBertLifter()
            log.info("MotionBertLifter lazy created from env vars")

    def estimate(
        self,
        frames: np.ndarray,
        pole_axis: PoleAxis,
    ) -> list[PoseFrame]:
        """프레임 시퀀스 → list[PoseFrame] (RTMW 2D xy + MotionBERT 3D z).

        흐름:
          1. RTMWPoseEngine.estimate(frames, pole_axis) → list[PoseFrame] (RTMW 2D).
          2. PoseFrame.keypoints_3d 에서 COCO-17 17개 xy 추출 → (T, 17, 2) 배열.
          3. COCO-17 → H3.6M 17 변환 (limb 12 직접 매핑 + 파생 5: hip/spine/thorax/neck_nose/head).
          4. MotionBertLifter.lift() → (T, 17, 3) H3.6M xyz.
          5. H3.6M 17 → COCO-17 역변환 → (T, 17, 4=xyz+uncertainty).
          6. 원본 PoseFrame 의 keypoints_3d / keypoints_3d_pole_aligned / reliability
             교체. raw_keypoints_133, keypoints_2d, pole_axis, pole_extension_landmarks
             보존 (D-20 / H-3).

        Args:
            frames: (T, H, W, 3) RGB uint8 배열.
            pole_axis: PoleDetector 산출 PoleAxis (D-10/H-3).

        Returns:
            list[PoseFrame] — len = T. 미감지 프레임은 빈 채로 유지 (lifter 출력 미주입).

        Raises:
            NoHumanError: 전 프레임 미감지 (RTMWPoseEngine 이 raise).
        """
        self._ensure_components()

        # 1. RTMW 2D 추출 (PoseFrame 리스트)
        rtmw_pose_frames = self._rtmw_engine.estimate(frames, pole_axis)
        T = len(rtmw_pose_frames)
        if T == 0:
            return []

        # 2. PoseFrame.keypoints_3d 에서 COCO-17 17개 xy 추출 → (T, 17, 2)
        coco17_xy = self._extract_coco17_xy_from_pose_frames(rtmw_pose_frames)  # (T, 17, 2)

        # 3. COCO-17 → H3.6M 17 변환
        h36m_2d = _coco17_to_h36m17_xy(coco17_xy)  # (T, 17, 2)

        # 4. MotionBERT lift → (T, 17, 3) H3.6M xyz
        h36m_xyz = self._lifter.lift(h36m_2d)  # (T, 17, 3)
        h36m_xyz_arr = np.asarray(h36m_xyz, dtype=np.float32)
        if h36m_xyz_arr.shape != (T, _NUM_H36M_JOINTS, 3):
            raise ValueError(
                f"MotionBertLifter.lift() 반환 형상 불일치: "
                f"기대 ({T}, 17, 3), 받은 {h36m_xyz_arr.shape}"
            )

        # 5. H3.6M 17 → COCO-17 (T, 17, 4=xyz+uncertainty)
        from ...pose_lifters.mediapipe_to_h36m17 import (  # noqa: PLC0415
            h36m17_to_coco17_subset,
        )
        coco17_arr = h36m17_to_coco17_subset(h36m_xyz_arr)  # (T, 17, 4)

        # 6. 원본 PoseFrame 교체 (limb 12 joints 만 — face 5 joints 는 RTMW 원본 보존)
        result: list[PoseFrame] = []
        for t, frame in enumerate(rtmw_pose_frames):
            new_frame = self._replace_keypoints(frame, coco17_arr[t], pole_axis)
            result.append(new_frame)

        return result

    def _extract_coco17_xy_from_pose_frames(
        self,
        pose_frames: list[PoseFrame],
    ) -> np.ndarray:
        """PoseFrame 리스트에서 (T, 17, 2) COCO-17 xy 배열 재구성.

        keypoints_3d (RTMW path = COCO-17 17개) 에서 KEYPOINT_NAMES 순서로
        x/y 추출. 미감지 keypoint (dict 에 없거나 미감지 sentinel) 는 NaN.
        MotionBERT lifter 는 NaN → 0.0 으로 대체 (motionbert_lifter.lift 내부).

        plan 17 mapping fix 정합: KEYPOINT_NAMES (skeleton.py) 가 단일
        source of truth — RTMW path 의 좌/우 인덱스 헷갈림 없음.
        """
        T = len(pose_frames)
        out = np.full((T, len(KEYPOINT_NAMES), 2), np.nan, dtype=np.float32)

        for t, frame in enumerate(pose_frames):
            kp3d = frame.keypoints_3d
            if not kp3d:
                # 미감지 프레임 — NaN 유지 (MotionBertLifter 가 0.0 으로 대체)
                continue
            for j, name in enumerate(KEYPOINT_NAMES):
                kp = kp3d.get(name)
                if kp is None:
                    continue
                out[t, j, 0] = kp.x
                out[t, j, 1] = kp.y

        return out

    def _replace_keypoints(
        self,
        frame: PoseFrame,
        coco17_row: np.ndarray,  # (17, 4=xyz+uncertainty)
        pole_axis: PoleAxis,
    ) -> PoseFrame:
        """원본 PoseFrame 의 keypoints_3d / keypoints_3d_pole_aligned / reliability 교체.

        coco17_row 의 NaN (face 5 joints — nose/eyes/ears) 은 RTMW 원본 keypoints_3d
        에서 보존 (z=0 그대로). limb 12 joints (COCO 5~16) 만 MotionBERT z 로 교체.
        raw_keypoints_133, keypoints_2d, pole_extension_landmarks, body_shape 는 보존.
        pole_axis 는 H-3 박제 — 인자 그대로 전달.

        Args:
            frame: 원본 RTMW PoseFrame (keypoints_3d xy = RTMW 픽셀 좌표, z=0).
            coco17_row: (17, 4) — H3.6M lift 결과를 COCO-17 로 역변환한 1 프레임.
            pole_axis: H-3 박제 인자.

        Returns:
            교체된 PoseFrame — limb joints xyz 는 MotionBERT, face joints 는 RTMW 원본.
        """
        # 기존 keypoints_3d 복사 (face 5 joints 보존용)
        new_kp3d: dict[str, Keypoint3D] = dict(frame.keypoints_3d)

        for j, name in enumerate(KEYPOINT_NAMES):
            row = coco17_row[j]
            x, y, z, uncertainty = (
                float(row[0]),
                float(row[1]),
                float(row[2]),
                float(row[3]),
            )
            if np.isnan(x) or np.isnan(y) or np.isnan(z):
                # face joints (nose/eyes/ears) → coco17_row 에서 NaN.
                # RTMW 원본 keypoints_3d 에 있으면 그대로 유지, 없으면 skip.
                continue
            # MotionBERT uncertainty 를 confidence proxy 로 변환 (D-05 정합)
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
            from ...pole.aligner import (  # noqa: PLC0415
                apply_alignment,
                compute_alignment_matrix,
            )

            R = compute_alignment_matrix(pole_axis.axis_vector)
            new_aligned = apply_alignment(new_kp3d, R)
        except (ImportError, ValueError):
            # aligner 미설치 또는 zero vector → raw xyz 로 폴백
            for n, kp in new_kp3d.items():
                new_aligned[n] = Keypoint3DAligned(x=kp.x, y=kp.y, z=kp.z)

        # reliability 재산출 — keypoints_3d 의 평균 confidence 기반
        if new_kp3d:
            mean_conf = float(np.mean([kp.confidence for kp in new_kp3d.values()]))
            new_reliability = compute_frame_reliability(mean_conf)
        else:
            new_reliability = "low"

        # dataclass frozen=True → replace()
        return replace(
            frame,
            keypoints_3d=new_kp3d,
            keypoints_3d_pole_aligned=new_aligned,
            pole_axis=pole_axis,
            reliability=new_reliability,
        )


# ── 내부 헬퍼: COCO-17 → H3.6M 17 변환 ────────────────────────────────────

def _coco17_to_h36m17_xy(coco17_xy: np.ndarray) -> np.ndarray:
    """COCO-17 (T, 17, 2) xy → H3.6M 17 (T, 17, 2) xy 변환.

    plan 17 mapping fix 정합 (`pose_lifters/mediapipe_to_h36m17.py`
    `H36M_TO_COCO17_LIMB_PAIRS` 와 동일 규칙):

      H3.6M 직접 대응 (12 limb joints):
        H36M LShoulder(11) ← COCO left_shoulder(5)
        H36M RShoulder(14) ← COCO right_shoulder(6)
        H36M LElbow(12)   ← COCO left_elbow(7)
        H36M RElbow(15)   ← COCO right_elbow(8)
        H36M LWrist(13)   ← COCO left_wrist(9)
        H36M RWrist(16)   ← COCO right_wrist(10)
        H36M LHip(4)      ← COCO left_hip(11)
        H36M RHip(1)      ← COCO right_hip(12)
        H36M LKnee(5)     ← COCO left_knee(13)
        H36M RKnee(2)     ← COCO right_knee(14)
        H36M LFoot(6)     ← COCO left_ankle(15)
        H36M RFoot(3)     ← COCO right_ankle(16)

      H3.6M 파생 (5 derived joints):
        H36M Hip(0)       = mean(LHip, RHip)
        H36M Thorax(8)    = mean(LShoulder, RShoulder)
        H36M Spine(7)     = mean(Hip, Thorax)
        H36M NeckNose(9)  = mean(Thorax, Nose)
        H36M Head(10)     = COCO nose(0)

    NaN 입력은 NaN 그대로 전파 (구성 관절이 NaN 이면 파생 관절도 NaN).
    MotionBertLifter 는 NaN → 0.0 으로 대체.

    Args:
        coco17_xy: (T, 17, 2) — COCO-17 xy.

    Returns:
        (T, 17, 2) — H3.6M 17 xy.

    Raises:
        ValueError: 입력 형상 불일치.
    """
    arr = np.asarray(coco17_xy, dtype=np.float32)
    if arr.ndim != 3 or arr.shape[1] != 17 or arr.shape[2] != 2:
        raise ValueError(
            f"coco17_xy 형상은 (T, 17, 2) 이어야 합니다. 받은 형상: {arr.shape}"
        )

    T = arr.shape[0]
    out = np.full((T, _NUM_H36M_JOINTS, 2), np.nan, dtype=np.float32)

    # COCO-17 인덱스 (KEYPOINT_NAMES 순서)
    coco_nose = _COCO17_NAME_TO_IDX["nose"]
    coco_l_sh = _COCO17_NAME_TO_IDX["left_shoulder"]
    coco_r_sh = _COCO17_NAME_TO_IDX["right_shoulder"]
    coco_l_el = _COCO17_NAME_TO_IDX["left_elbow"]
    coco_r_el = _COCO17_NAME_TO_IDX["right_elbow"]
    coco_l_wr = _COCO17_NAME_TO_IDX["left_wrist"]
    coco_r_wr = _COCO17_NAME_TO_IDX["right_wrist"]
    coco_l_hp = _COCO17_NAME_TO_IDX["left_hip"]
    coco_r_hp = _COCO17_NAME_TO_IDX["right_hip"]
    coco_l_kn = _COCO17_NAME_TO_IDX["left_knee"]
    coco_r_kn = _COCO17_NAME_TO_IDX["right_knee"]
    coco_l_an = _COCO17_NAME_TO_IDX["left_ankle"]
    coco_r_an = _COCO17_NAME_TO_IDX["right_ankle"]

    # 직접 매핑 (12 limb)
    out[:, _H36M_L_SHOULDER, :] = arr[:, coco_l_sh, :]
    out[:, _H36M_R_SHOULDER, :] = arr[:, coco_r_sh, :]
    out[:, _H36M_L_ELBOW, :] = arr[:, coco_l_el, :]
    out[:, _H36M_R_ELBOW, :] = arr[:, coco_r_el, :]
    out[:, _H36M_L_WRIST, :] = arr[:, coco_l_wr, :]
    out[:, _H36M_R_WRIST, :] = arr[:, coco_r_wr, :]
    out[:, _H36M_L_HIP, :] = arr[:, coco_l_hp, :]
    out[:, _H36M_R_HIP, :] = arr[:, coco_r_hp, :]
    out[:, _H36M_L_KNEE, :] = arr[:, coco_l_kn, :]
    out[:, _H36M_R_KNEE, :] = arr[:, coco_r_kn, :]
    out[:, _H36M_L_FOOT, :] = arr[:, coco_l_an, :]
    out[:, _H36M_R_FOOT, :] = arr[:, coco_r_an, :]

    # 파생 관절 5개
    # Head ← nose
    out[:, _H36M_HEAD, :] = arr[:, coco_nose, :]
    # Hip ← mean(L hip, R hip)
    out[:, _H36M_HIP, :] = (arr[:, coco_l_hp, :] + arr[:, coco_r_hp, :]) / 2.0
    # Thorax ← mean(L shoulder, R shoulder)
    out[:, _H36M_THORAX, :] = (arr[:, coco_l_sh, :] + arr[:, coco_r_sh, :]) / 2.0
    # Spine ← mean(Hip, Thorax)
    out[:, _H36M_SPINE, :] = (out[:, _H36M_HIP, :] + out[:, _H36M_THORAX, :]) / 2.0
    # NeckNose ← mean(Thorax, Nose)
    out[:, _H36M_NECK_NOSE, :] = (out[:, _H36M_THORAX, :] + arr[:, coco_nose, :]) / 2.0

    return out
