"""RTMWPoseEngine + POSE_ENGINE config 플래그 테스트 (Plan 01-21 Task 2 RED).

D-21: POSE_ENGINE 환경변수 = 'RTMW' (기본) / 'NLF_SMPLX' (R&D).
D-22: RTMWPoseEngine 이 PoseEngine Protocol 구현.
D-25: weights_manifest.json production_eligible=true 가중치만 허용. 그 외 LicenseViolationError.
H-2: module-level rtmlib/mmpose/mmcv import 0.

rtmlib 은 unittest.mock.MagicMock 으로 DI — CI 환경에서 rtmlib 미설치 가정.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_PATH = (
    REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "pose_engines"
    / "rtmw"
    / "rtmw_engine.py"
)


# ── 픽스처 ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def default_pole_axis():
    from sunity_shared.analysis.pose_frame import PoleAxis
    return PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )


@pytest.fixture
def mock_inferencer():
    """Mock rtmlib wholebody inferencer — (133, 3) keypoints + (133,) scores 반환."""
    mock = MagicMock()
    # rtmlib Wholebody 반환 형식: (keypoints, scores) 튜플
    # keypoints: (N_person, 133, 2또는3), scores: (N_person, 133)
    kps = np.zeros((1, 133, 2), dtype=np.float32)  # 1명, 133키포인트, xy
    scores = np.full((1, 133), 0.9, dtype=np.float32)
    mock.return_value = (kps, scores)
    return mock


@pytest.fixture
def mock_frames():
    """Mock (T, H, W, 3) RGB uint8 프레임 배열."""
    return np.zeros((3, 480, 640, 3), dtype=np.uint8)


@pytest.fixture
def real_manifest_path():
    return (
        REPO_ROOT
        / "backend"
        / "shared"
        / "python"
        / "sunity_shared"
        / "analysis"
        / "pose_engines"
        / "rtmw"
        / "weights_manifest.json"
    )


@pytest.fixture
def no_eligible_manifest_path(tmp_path):
    """production_eligible=false 만 있는 임시 manifest."""
    import json
    manifest = {
        "manifest_version": "1.0",
        "audit_date": "2026-06-02",
        "weights": [
            {
                "name": "rtmw-l-256x192",
                "url": "https://example.com/rtmw.onnx",
                "sha256": None,
                "input_size": [256, 192],
                "training_data": [],
                "training_data_summary": "test",
                "license_status": "restricted",
                "production_eligible": False,
                "source_audit_ref": "test",
            }
        ],
    }
    p = tmp_path / "weights_manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


# ── Test 1: PoseEngine Protocol 만족 ─────────────────────────────────────

def test_rtmw_engine_implements_pose_engine_protocol(real_manifest_path, mock_inferencer):
    """RTMWPoseEngine 이 PoseEngine Protocol 시그니처를 만족한다."""
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine

    engine = RTMWPoseEngine.create_with_inferencer(
        inferencer=mock_inferencer,
        manifest_path=real_manifest_path,
    )
    # duck-typing Protocol 검증 — estimate 메서드 존재 + callable
    assert hasattr(engine, "estimate"), "estimate 메서드 없음"
    assert callable(engine.estimate), "estimate 가 callable 이어야 함"
    # inspect 시그니처 검증
    import inspect
    sig = inspect.signature(engine.estimate)
    params = list(sig.parameters.keys())
    assert "frames" in params, "estimate 에 frames 파라미터 없음"
    assert "pole_axis" in params, "estimate 에 pole_axis 파라미터 없음"


# ── Test 2: estimate → list[PoseFrame] ───────────────────────────────────

def test_rtmw_engine_estimate_returns_list_pose_frame(
    real_manifest_path, mock_inferencer, mock_frames, default_pole_axis
):
    """mock inferencer 주입 → estimate() → list[PoseFrame] 반환."""
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
    from sunity_shared.analysis.pose_frame import PoseFrame

    engine = RTMWPoseEngine.create_with_inferencer(
        inferencer=mock_inferencer,
        manifest_path=real_manifest_path,
    )
    result = engine.estimate(frames=mock_frames, pole_axis=default_pole_axis)

    assert isinstance(result, list), f"list 반환 필요, got {type(result)}"
    assert len(result) == len(mock_frames), (
        f"프레임 수 일치 필요: {len(mock_frames)} frames → {len(result)} PoseFrame"
    )
    for frame in result:
        assert isinstance(frame, PoseFrame), f"각 element 가 PoseFrame 이어야 함, got {type(frame)}"


# ── Test 3: manifest 로드 성공 ───────────────────────────────────────────

def test_rtmw_engine_loads_manifest_on_init(real_manifest_path, mock_inferencer):
    """production_eligible=true 가중치 포함 manifest → RTMWPoseEngine 초기화 성공."""
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine

    # create_with_inferencer 가 manifest 검사 통과해야 함
    engine = RTMWPoseEngine.create_with_inferencer(
        inferencer=mock_inferencer,
        manifest_path=real_manifest_path,
    )
    assert engine is not None


# ── Test 4: non-eligible manifest → LicenseViolationError ────────────────

def test_rtmw_engine_rejects_non_eligible_weights(no_eligible_manifest_path, mock_inferencer):
    """production_eligible=false 만 있는 manifest → LicenseViolationError (D-25)."""
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine, LicenseViolationError

    with pytest.raises(LicenseViolationError):
        RTMWPoseEngine.create_with_inferencer(
            inferencer=mock_inferencer,
            manifest_path=no_eligible_manifest_path,
        )


# ── Test 5: module-level no rtmlib import ────────────────────────────────

def test_rtmw_engine_module_level_no_rtmlib_import():
    """rtmw_engine.py 의 module-level (top-level) import 에 rtmlib/mmpose/mmcv 0건 (H-2 박제).

    module-level = ast.Module.body 의 직접 자식 Import/ImportFrom 노드만 검사.
    함수/클래스 내부의 lazy import (try: from rtmlib import ...) 는 허용.
    """
    assert ENGINE_PATH.exists(), f"rtmw_engine.py 없음: {ENGINE_PATH}"
    source = ENGINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # module-level = ast.Module.body 의 직접 자식만 검사 (H-2: lazy import 허용)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.lower()
                assert "rtmlib" not in mod, f"module-level rtmlib import 금지: {alias.name}"
                assert "mmpose" not in mod, f"module-level mmpose import 금지: {alias.name}"
                assert "mmcv" not in mod, f"module-level mmcv import 금지: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.lower()
                assert "rtmlib" not in mod, f"module-level rtmlib import 금지: {node.module}"
                assert "mmpose" not in mod, f"module-level mmpose import 금지: {node.module}"
                assert "mmcv" not in mod, f"module-level mmcv import 금지: {node.module}"


# ── Test 6: 빈 결과 → NoHumanError ──────────────────────────────────────

def test_rtmw_engine_no_human_raises_nohumanerror(
    real_manifest_path, mock_frames, default_pole_axis
):
    """inferencer 가 빈 결과 (사람 없음) 반환 → NoHumanError raise."""
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
    from sunity_shared.analysis.interfaces import NoHumanError

    # 사람 없는 결과: (0, 133, 2) keypoints
    no_human_inferencer = MagicMock()
    no_human_inferencer.return_value = (
        np.zeros((0, 133, 2), dtype=np.float32),  # 0명 감지
        np.zeros((0, 133), dtype=np.float32),
    )

    engine = RTMWPoseEngine.create_with_inferencer(
        inferencer=no_human_inferencer,
        manifest_path=real_manifest_path,
    )

    with pytest.raises(NoHumanError):
        engine.estimate(frames=mock_frames, pole_axis=default_pole_axis)


# ── Test 7: pose_engines __init__ lazy export ─────────────────────────────

def test_pose_engines_init_lazy_exports_rtmw():
    """from sunity_shared.analysis.pose_engines import RTMWPoseEngine 성공."""
    from sunity_shared.analysis.pose_engines import RTMWPoseEngine
    assert RTMWPoseEngine is not None
    assert RTMWPoseEngine.__name__ == "RTMWPoseEngine"


# ── Test 8: get_pose_engine 기본값 = RTMW ────────────────────────────────

def test_config_get_pose_engine_returns_rtmw_by_default():
    """POSE_ENGINE env unset → get_pose_engine() = 'RTMW' (D-21 기본값)."""
    env_backup = os.environ.pop("POSE_ENGINE", None)
    try:
        from sunity_shared.config import get_pose_engine
        result = get_pose_engine()
        assert result == "RTMW", f"기본값 'RTMW' 필요, got {result!r}"
    finally:
        if env_backup is not None:
            os.environ["POSE_ENGINE"] = env_backup


# ── Test 9: get_pose_engine 환경변수 반영 ───────────────────────────────

def test_config_get_pose_engine_respects_env():
    """POSE_ENGINE='NLF_SMPLX' env → get_pose_engine() = 'NLF_SMPLX'."""
    os.environ["POSE_ENGINE"] = "NLF_SMPLX"
    try:
        import importlib
        import sunity_shared.config as cfg_mod
        importlib.reload(cfg_mod)
        result = cfg_mod.get_pose_engine()
        assert result == "NLF_SMPLX", f"'NLF_SMPLX' 필요, got {result!r}"
    finally:
        del os.environ["POSE_ENGINE"]


# ── Test 10: 잘못된 POSE_ENGINE 값 → 에러 ──────────────────────────────

def test_config_invalid_pose_engine_raises():
    """POSE_ENGINE='INVALID' → ValueError 또는 ConfigurationError raise."""
    os.environ["POSE_ENGINE"] = "INVALID_ENGINE"
    try:
        import importlib
        import sunity_shared.config as cfg_mod
        importlib.reload(cfg_mod)
        with pytest.raises((ValueError, Exception)) as exc_info:
            cfg_mod.get_pose_engine()
        # 에러 메시지에 엔진명 포함 확인
        assert "INVALID_ENGINE" in str(exc_info.value) or "POSE_ENGINE" in str(exc_info.value)
    finally:
        del os.environ["POSE_ENGINE"]
