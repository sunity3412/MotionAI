"""Plan 01-22 Task 2 — 선택된 어댑터 (옵션 B: RTMW 2D + MotionBERT lifter) contract pytest 게이트.

belle = "approved: option_b" (2026-06-03 박제, three_d_path_decision.md §5).
본 파일은 옵션 B 의 RTMWLifterPoseEngine 의 estimate() 실 구현 contract 검증:

  1. test_selected_engine_no_not_implemented:
     mock RTMWPoseEngine + mock MotionBertLifter 주입 시 estimate() 가
     NotImplementedError 미발생 + list[PoseFrame] 반환.

  2. test_selected_engine_z_coord_filled:
     반환된 모든 PoseFrame 의 keypoints_3d.z 가 numpy.nan 아님 + 분산 > 0
     (스칼라 0 채움 회귀 방지 — MotionBERT lift 출력이 PoseFrame.keypoints_3d
     에 반영됨을 검증).

  3. test_selected_engine_no_left_right_swap:
     plan 17 mapping fix 정합 — 합성 mock 입력 (좌=+x, 우=-x) 주입 시
     출력의 모든 프레임에서 좌 keypoint 의 x > 우 keypoint 의 x.
     어깨/팔꿈치/손목/엉덩이/무릎/발목 6쌍 검증.

비선택 옵션 A (RTMW3DPoseEngine) 의 NotImplementedError 유지 검증은
test_rtmw_3d_path.py::test_both_engines_unselected_raises_not_implemented 가
계속 담당 (test_rtmw_3d_path.py 의 옵션 A 검증은 Task 2 후에도 유지).
"""

from __future__ import annotations

import numpy as np
import pytest

from sunity_shared.analysis.pose_engines import RTMWLifterPoseEngine
from sunity_shared.analysis.pose_frame import (
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
)
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES


# ── 헬퍼: PoleAxis / PoseFrame 픽스처 ─────────────────────────────────────

def _make_pole_axis() -> PoleAxis:
    """수직 폴 축 (z+1) — D-11 vertical_fallback 정합."""
    return PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
        frame_index=None,
    )


# left_* / right_* 12 limb 짝 (plan 17 mapping fix swap_ratio 회귀 게이트 대상)
_LR_LIMB_PAIRS: tuple[tuple[str, str], ...] = (
    ("left_shoulder", "right_shoulder"),
    ("left_elbow", "right_elbow"),
    ("left_wrist", "right_wrist"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
    ("left_ankle", "right_ankle"),
)


def _make_rtmw_pose_frame(
    frame_index: int,
    *,
    left_x: float = 1.0,
    right_x: float = -1.0,
    y_base: float = 0.5,
    z_base: float = 0.0,
) -> PoseFrame:
    """좌/우 한쪽 keypoint 가 +x, 다른 한쪽이 -x 인 합성 RTMW PoseFrame.

    RTMW path 의 추론 결과 시뮬레이션:
      - keypoints_3d 의 xy = RTMW 픽셀 좌표 (좌측 = +x, 우측 = -x)
      - z = 0 (RTMW 2D 추론 결과의 z 패딩, lifter 가 채움)
      - confidence = 0.9 (모든 keypoint)

    plan 17 mapping fix 정합 — left_*/right_* 인덱스는 KEYPOINT_NAMES 순서.
    """
    kp3d: dict[str, Keypoint3D] = {}
    for name in KEYPOINT_NAMES:
        if name.startswith("left_"):
            x_val = left_x
        elif name.startswith("right_"):
            x_val = right_x
        else:
            # nose / unused face joints — 중앙 (x=0)
            x_val = 0.0
        kp3d[name] = Keypoint3D(
            x=x_val,
            y=y_base + 0.01 * frame_index,
            z=z_base,
            confidence=0.9,
            uncertainty_proxy=0.1,
        )

    pole = _make_pole_axis()
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=frame_index * 33,
        raw_landmarks_33={},
        keypoints_3d=kp3d,
        keypoints_3d_pole_aligned={
            n: Keypoint3DAligned(x=kp.x, y=kp.y, z=kp.z)
            for n, kp in kp3d.items()
        },
        keypoints_2d=None,
        pole_extension_landmarks=None,
        pole_axis=pole,
        reliability="high",
    )


# ── Mock 인스턴스 ────────────────────────────────────────────────────────

class _MockRTMWEngine:
    """RTMWPoseEngine.estimate(frames, pole_axis) 시뮬레이션.

    합성 PoseFrame 리스트 반환 — 좌/우 keypoint 의 x 좌표가 정렬돼 있어
    lift 후 swap_ratio 회귀 (plan 17) 검증 진입점.
    """

    def __init__(
        self,
        num_frames: int,
        *,
        left_x: float = 1.0,
        right_x: float = -1.0,
    ) -> None:
        self._num_frames = num_frames
        self._left_x = left_x
        self._right_x = right_x

    def estimate(self, frames: np.ndarray, pole_axis: PoleAxis) -> list[PoseFrame]:
        return [
            _make_rtmw_pose_frame(
                i,
                left_x=self._left_x,
                right_x=self._right_x,
            )
            for i in range(self._num_frames)
        ]


class _MockLifter:
    """MotionBertLifter.lift(landmarks_2d: (T, 17, 2)) → (T, 17, 3) 시뮬레이션.

    z 채움 검증 + swap 회귀 검증 둘 다 통과하도록:
      - 출력 xy = 입력 xy (좌우 정합 보존, plan 17 mapping fix 정합).
      - 출력 z = 입력 y * 0.5 + 0.1 * t (t = 프레임 인덱스 0~T-1).
        분산 > 0 보장 + 모든 프레임에서 numpy.nan 아님.

    NaN 입력은 0.0 으로 대체 (motionbert_lifter.lift 의 실제 동작과 정합).
    """

    def lift(self, landmarks_2d: np.ndarray) -> np.ndarray:
        arr = np.asarray(landmarks_2d, dtype=np.float32)
        # 실제 MotionBertLifter 와 동일: NaN → 0.0
        arr = np.nan_to_num(arr, nan=0.0)
        T = arr.shape[0]
        out = np.zeros((T, 17, 3), dtype=np.float32)
        out[:, :, 0] = arr[:, :, 0]  # x 보존 (lift 가 좌우 swap 미발생)
        out[:, :, 1] = arr[:, :, 1]  # y 보존
        # z = y * 0.5 + 0.1 * t (모든 keypoint 같은 z 패턴, 분산 > 0)
        for t in range(T):
            out[t, :, 2] = arr[t, :, 1] * 0.5 + 0.1 * t
        return out


# ── Test 1: NotImplementedError 미발생 ───────────────────────────────────


def test_selected_engine_no_not_implemented() -> None:
    """옵션 B 실 구현 확인 — estimate() 가 NotImplementedError raise 하지 않아야 한다.

    mock RTMW + mock lifter 주입 → estimate() 호출 → list[PoseFrame] 반환.
    Plan 22 Task 2 acceptance.
    """
    mock_rtmw = _MockRTMWEngine(num_frames=3)
    mock_lifter = _MockLifter()
    engine = RTMWLifterPoseEngine.create_with_engines(
        rtmw_engine=mock_rtmw,
        lifter=mock_lifter,
    )

    dummy_frames = np.zeros((3, 64, 64, 3), dtype=np.uint8)
    pole = _make_pole_axis()

    # NotImplementedError 가 raise 되면 본 호출에서 즉시 실패.
    result = engine.estimate(dummy_frames, pole)

    assert isinstance(result, list), (
        f"estimate() 반환 타입은 list 이어야 합니다. 받은 타입: {type(result)}"
    )
    assert len(result) == 3, (
        f"estimate() 결과 길이는 입력 프레임 수와 일치해야 합니다. 받은 길이: {len(result)}"
    )
    for i, frame in enumerate(result):
        assert isinstance(frame, PoseFrame), (
            f"frame[{i}] 는 PoseFrame 이어야 합니다. 받은 타입: {type(frame)}"
        )


# ── Test 2: z 좌표 채움 + 분산 > 0 (스칼라 0 회귀 방지) ──────────────────


def test_selected_engine_z_coord_filled() -> None:
    """반환된 모든 PoseFrame 의 keypoints_3d.z 가 numpy.nan 아님 + 분산 > 0.

    스칼라 0 채움 회귀 방지 — MotionBERT lift 출력이 PoseFrame.keypoints_3d
    의 z 에 반영됨을 검증. 모든 frame 의 모든 limb keypoint z 가 같은 값이면
    분산 = 0 → 회귀 시그널.

    Plan 22 Task 2 acceptance — test_selected_engine_z_coord_filled.
    """
    mock_rtmw = _MockRTMWEngine(num_frames=5)
    mock_lifter = _MockLifter()
    engine = RTMWLifterPoseEngine.create_with_engines(
        rtmw_engine=mock_rtmw,
        lifter=mock_lifter,
    )

    dummy_frames = np.zeros((5, 64, 64, 3), dtype=np.uint8)
    pole = _make_pole_axis()
    result = engine.estimate(dummy_frames, pole)

    # 모든 limb keypoint 의 z 수집 (face joints 는 lifter NaN → 본 검증 대상 외)
    limb_names = {n for pair in _LR_LIMB_PAIRS for n in pair}
    all_z: list[float] = []
    for frame in result:
        for name in limb_names:
            kp = frame.keypoints_3d.get(name)
            assert kp is not None, (
                f"limb keypoint {name!r} 가 keypoints_3d 에 없음 — "
                f"_replace_keypoints 가 lifter 결과를 반영하지 않았다."
            )
            assert not np.isnan(kp.z), (
                f"keypoints_3d[{name!r}].z 가 NaN 입니다. lifter z 채움 실패."
            )
            all_z.append(kp.z)

    z_arr = np.asarray(all_z, dtype=np.float32)
    z_variance = float(np.var(z_arr))
    assert z_variance > 0.0, (
        f"keypoints_3d.z 분산이 0 입니다 (스칼라 0 채움 회귀). "
        f"z values: {z_arr.tolist()}"
    )


# ── Test 3: 좌우 swap 없음 (plan 17 mapping fix 회귀 게이트) ─────────────


def test_selected_engine_no_left_right_swap() -> None:
    """plan 17 mapping fix 정합 — 좌=+x, 우=-x 입력 → 모든 프레임 좌 x > 우 x.

    합성 입력 (left_*.x = +1.0, right_*.x = -1.0) → estimate() → 출력의
    어깨/팔꿈치/손목/엉덩이/무릎/발목 6쌍 모두 모든 프레임에서
    keypoints_3d[left_*].x > keypoints_3d[right_*].x 임을 검증.

    이 조건이 깨지면:
      - COCO-17 → H3.6M 17 변환 시 좌/우 인덱스 swap (mapping 회귀), 또는
      - H3.6M → COCO-17 역변환 시 좌/우 인덱스 swap, 또는
      - lifter mock 자체의 swap 시뮬레이션 (본 테스트에서는 미발생 — _MockLifter 가 xy 보존).

    swap_ratio = 0 (Plan 16 박제 `swap_ratio 1.00` 회귀 방지).

    Plan 22 Task 2 acceptance — test_selected_engine_no_left_right_swap.
    """
    NUM_FRAMES = 4
    mock_rtmw = _MockRTMWEngine(num_frames=NUM_FRAMES, left_x=1.0, right_x=-1.0)
    mock_lifter = _MockLifter()
    engine = RTMWLifterPoseEngine.create_with_engines(
        rtmw_engine=mock_rtmw,
        lifter=mock_lifter,
    )

    dummy_frames = np.zeros((NUM_FRAMES, 64, 64, 3), dtype=np.uint8)
    pole = _make_pole_axis()
    result = engine.estimate(dummy_frames, pole)

    # 모든 frame x 모든 limb pair → 좌 x > 우 x
    swap_count = 0
    total = 0
    for t, frame in enumerate(result):
        for left_name, right_name in _LR_LIMB_PAIRS:
            left_kp = frame.keypoints_3d.get(left_name)
            right_kp = frame.keypoints_3d.get(right_name)
            assert left_kp is not None and right_kp is not None, (
                f"frame[{t}] 에 {left_name} / {right_name} keypoint 없음"
            )
            total += 1
            if left_kp.x <= right_kp.x:
                swap_count += 1

    swap_ratio = swap_count / total if total > 0 else 0.0
    assert swap_ratio == 0.0, (
        f"좌/우 swap_ratio = {swap_ratio:.2f} (기대 0). "
        f"plan 17 mapping fix 회귀 — {swap_count}/{total} pair 에서 "
        f"left.x <= right.x. COCO-17 ↔ H3.6M 17 변환 단계의 좌우 인덱스 "
        f"매핑을 확인하세요."
    )
