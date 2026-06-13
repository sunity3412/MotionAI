"""Phase 4 Wave 0 — synthetic fixture (Spike 002d 패턴 재사용).

POSE-03-a~f 6 test 파일이 공유하는 numpy synthetic fixture 박제.
joint_seq_60f / conf_seq_60f 는 evaluate_4way (04-03 Task 2, 04-05 Task 2) 가
T=60 기대에 대응 — T=30 fixture 는 confidence gate / synthesis merge / warning
lockstep 단위 테스트용 (짧은 시퀀스로 충분).

per Plan 04-00 must_haves.artifacts — joint_seq_30f, joint_seq_60f,
conf_seq_30f, conf_seq_60f, low_conf_seq, scene_findings_occlusion,
scene_findings_clean 7개 fixture.

기존 backend/tests/conftest.py 가 parents[1]/shared/python 을 sys.path 에 자동
주입하므로 본 파일은 별도 path 주입 X.
"""

from __future__ import annotations

import numpy as np
import pytest

# COCO17 joint count — sunity_shared.analysis.keypoint_frame.NUM_KEYPOINTS_PHASE12
# 와 별개로 Phase 4 합성 단위 테스트는 RTMW → COCO17 (17 joint) 출력 형상 기준.
_NUM_JOINTS_COCO17 = 17


def _make_joint_seq(num_frames: int, *, seed: int) -> np.ndarray:
    """(T, 17, 3) float32 합성 시퀀스 — 값 0~1 normalized.

    deterministic seed 로 numpy RNG 박제 — test reproducibility.
    """
    rng = np.random.default_rng(seed)
    arr = rng.uniform(low=0.0, high=1.0, size=(num_frames, _NUM_JOINTS_COCO17, 3))
    return arr.astype(np.float32)


def _make_conf_seq(num_frames: int, *, seed: int) -> np.ndarray:
    """(T, 17) float32 confidence — 값 0~1.

    base level 0.7 이상으로 시작 — low_conf_seq 가 명시적으로 일부만 0.1 로
    낮추는 occlusion 시뮬레이션 입력값과 구분.
    """
    rng = np.random.default_rng(seed)
    arr = rng.uniform(low=0.7, high=1.0, size=(num_frames, _NUM_JOINTS_COCO17))
    return arr.astype(np.float32)


@pytest.fixture
def joint_seq_30f() -> np.ndarray:
    """(30, 17, 3) float32 합성 joint 시퀀스 — confidence gate / merge 테스트용."""
    seq = _make_joint_seq(30, seed=2604)
    assert seq.shape == (30, _NUM_JOINTS_COCO17, 3)
    assert seq.dtype == np.float32
    return seq


@pytest.fixture
def joint_seq_60f() -> np.ndarray:
    """(60, 17, 3) float32 합성 joint 시퀀스 — evaluate_4way / cylindrical mesh
    (04-03, 04-05) T=60 기대 fixture 의존성 충족."""
    seq = _make_joint_seq(60, seed=2606)
    assert seq.shape == (60, _NUM_JOINTS_COCO17, 3)
    assert seq.dtype == np.float32
    return seq


@pytest.fixture
def conf_seq_30f() -> np.ndarray:
    """(30, 17) float32 confidence — 값 0~1, base 0.7~1.0."""
    arr = _make_conf_seq(30, seed=2614)
    assert arr.shape == (30, _NUM_JOINTS_COCO17)
    assert arr.dtype == np.float32
    return arr


@pytest.fixture
def conf_seq_60f() -> np.ndarray:
    """(60, 17) float32 confidence — evaluate_4way T=60 의존성."""
    arr = _make_conf_seq(60, seed=2616)
    assert arr.shape == (60, _NUM_JOINTS_COCO17)
    assert arr.dtype == np.float32
    return arr


@pytest.fixture
def low_conf_seq(conf_seq_30f: np.ndarray) -> np.ndarray:
    """occlusion 시뮬 — frame 10~20, joint 3~7 confidence 를 0.1 로 낮춤.

    POSE-03-a confidence gate test (synthesis_mask_low_confidence) 가 이
    영역을 mask=True 로 식별해야 한다 (임계값 0.3 < 0.1 영역).
    """
    arr = conf_seq_30f.copy()
    arr[10:20, 3:7] = 0.1
    return arr


@pytest.fixture
def scene_findings_occlusion() -> dict:
    """SceneFinder 결과 — occlusion_severe=True (피사체 가림 심각 신호).

    POSE-03-a — scene 레벨 occlusion 신호가 confidence gate 에 반영되는지
    확인하는 테스트 입력. 04-RESEARCH.md §scene_findings 박제 형식.
    """
    return {
        "occlusion_severe": True,
        "camera_angle_problematic": False,
    }


@pytest.fixture
def scene_findings_clean() -> dict:
    """SceneFinder 결과 — occlusion / camera angle 모두 정상.

    confidence gate 가 scene 신호 부재 시 frame 별 임계값 판정만으로
    동작하는지 확인하는 baseline fixture.
    """
    return {
        "occlusion_severe": False,
        "camera_angle_problematic": False,
    }
