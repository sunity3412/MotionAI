"""PoseEngine Protocol contract 테스트 (Plan 01-19 Task 1).

목적:
  - RTMW pivot (D-17~D-25) 이후 PoseEngine Protocol 이 backend-agnostic 한
    contract 로 박제되는지 검증.
  - PoseEngine.estimate(frames, pole_axis) -> list[PoseFrame] 시그니처 강제.
  - interfaces.py 자체가 rtmlib / mediapipe / torch / ultralytics 를 직접
    import 하지 않는다 (T-19-01 threat mitigation).
  - PoseFrame.body_shape: Optional[BodyNormalizationProfile] = None 필드 존재.
  - PoseFrame 기존 9개 필드 (plan 01-01/01-02 산출) 회귀 없음.
  - pose_engines/__init__.py 의 __all__ 에 PoseEngine 노출.

본 테스트는 어떤 구현체 (RTMW / MediaPipe / NLF) 도 import 하지 않는다 —
오직 인터페이스/타입/모듈 import 만 검증.
"""

from __future__ import annotations

import ast
import inspect
import typing
from dataclasses import fields
from pathlib import Path


# 인터페이스 정의 위치
_INTERFACES_PATH = (
    Path(__file__).resolve().parents[1]
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "interfaces.py"
)


# ---------------------------------------------------------------------------
# Test 1: PoseEngine Protocol 시그니처 (estimate(frames, pole_axis) -> list[PoseFrame])
# ---------------------------------------------------------------------------
def test_pose_engine_protocol_has_estimate_signature() -> None:
    from sunity_shared.analysis.interfaces import PoseEngine

    # Protocol 자체에 estimate 메서드가 존재해야 함
    assert hasattr(PoseEngine, "estimate"), (
        "PoseEngine Protocol 에 estimate 메서드가 정의되어 있어야 함"
    )

    sig = inspect.signature(PoseEngine.estimate)
    param_names = list(sig.parameters.keys())

    # self 제외 두 인자: frames, pole_axis
    assert "frames" in param_names, (
        f"estimate(frames, pole_axis) 필요 — 현재 params={param_names}"
    )
    assert "pole_axis" in param_names, (
        f"estimate(frames, pole_axis) 필요 (pole_axis 누락) — params={param_names}"
    )


# ---------------------------------------------------------------------------
# Test 2: interfaces.py 가 백엔드 의존 모듈을 직접 import 하지 않는다 (D-24)
# ---------------------------------------------------------------------------
def test_pose_engine_protocol_backend_agnostic() -> None:
    """T-19-01 mitigation — PoseEngine Protocol 모듈은 backend-agnostic.

    interfaces.py 가 직접 rtmlib / mediapipe / torch / ultralytics 를
    import 한다면 RTMW pivot (D-24) 의 "다운스트림 무수정 / 구현체만 교체"
    약속이 깨진다. AST 로 ImportFrom / Import 모두 수집해 검증.
    """
    forbidden = {"rtmlib", "mediapipe", "torch", "ultralytics"}

    source = _INTERFACES_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in forbidden:
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            top = mod.split(".")[0]
            if top in forbidden:
                found.append(mod)

    assert not found, (
        "interfaces.py 가 backend 모듈을 직접 import 함 "
        f"(D-24 위반): {found}. Protocol 은 typing.TYPE_CHECKING 또는 "
        "구현체 모듈로 옮길 것."
    )


# ---------------------------------------------------------------------------
# Test 3: BodyNormalizationProfile 필수 필드 (D-19)
# ---------------------------------------------------------------------------
def test_body_normalization_profile_required_fields() -> None:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    field_names = {f.name for f in fields(BodyNormalizationProfile)}
    expected = {
        "estimated_height_scale",
        "arm_scale",
        "leg_scale",
        "torso_scale",
        "shoulder_hip_ratio",
        "confidence",
        "warnings",
    }
    assert field_names == expected, (
        f"BodyNormalizationProfile 필드 집합 mismatch — "
        f"expected={expected}, got={field_names}"
    )


# ---------------------------------------------------------------------------
# Test 4: BodyNormalizationProfile 에 SMPL-X β 잔여 필드 부재 (D-19, T-19-02)
# ---------------------------------------------------------------------------
def test_body_normalization_profile_no_smplx_beta() -> None:
    """T-19-02 mitigation — SMPL-X β 의존을 영구히 제거 (D-19)."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    field_names = {f.name for f in fields(BodyNormalizationProfile)}
    forbidden = {"beta", "smplx_beta", "shape_params", "betas"}
    leaked = field_names & forbidden
    assert not leaked, (
        f"D-19 위반 — BodyNormalizationProfile 에 SMPL-X 잔여 필드: {leaked}"
    )


# ---------------------------------------------------------------------------
# Test 5: confidence 범위 검증 (__post_init__)
# ---------------------------------------------------------------------------
def test_body_normalization_profile_confidence_range() -> None:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    # 정상 범위
    for c in (0.0, 0.5, 1.0):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=c,
        )

    # 범위 초과
    import pytest

    with pytest.raises(ValueError):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=-0.1,
        )

    with pytest.raises(ValueError):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=1.1,
        )


# ---------------------------------------------------------------------------
# Test 6: warnings 필드 = list[str] 기본값 빈 리스트
# ---------------------------------------------------------------------------
def test_body_normalization_profile_warnings_is_list() -> None:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    p = BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.8,
    )
    assert p.warnings == [], "warnings 기본값은 빈 리스트여야 함"
    assert isinstance(p.warnings, list), "warnings 타입은 list"

    # tuple / None 거부
    import pytest

    with pytest.raises((TypeError, ValueError)):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=0.8,
            warnings=("not", "a", "list"),  # type: ignore[arg-type]
        )

    with pytest.raises((TypeError, ValueError)):
        BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=0.8,
            warnings=None,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Test 7: PoseFrame.body_shape nullable 필드 (D-21)
# ---------------------------------------------------------------------------
def test_pose_frame_has_body_shape_nullable_field() -> None:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pose_frame import PoseFrame

    field_names = {f.name for f in fields(PoseFrame)}
    assert "body_shape" in field_names, (
        "PoseFrame.body_shape 필드 (D-21) 누락"
    )

    # 기본값 None 으로 instantiate 가능 (RTMW path)
    frame = PoseFrame(frame_index=0, timestamp_ms=0)
    assert frame.body_shape is None, (
        "PoseFrame.body_shape 기본값은 None (RTMW = null path, D-21)"
    )

    # NLF_SMPLX path — BodyNormalizationProfile 채우기 가능
    profile = BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.9,
    )
    frame2 = PoseFrame(frame_index=0, timestamp_ms=0, body_shape=profile)
    assert frame2.body_shape is profile


# ---------------------------------------------------------------------------
# Test 8: PoseFrame 기존 9개 필드 회귀 없음 (plan 01-01/01-02)
# ---------------------------------------------------------------------------
def test_pose_frame_existing_fields_preserved() -> None:
    from sunity_shared.analysis.pose_frame import PoseFrame

    field_names = {f.name for f in fields(PoseFrame)}
    existing = {
        "frame_index",
        "timestamp_ms",
        "raw_landmarks_33",
        "keypoints_3d",
        "keypoints_3d_pole_aligned",
        "keypoints_2d",
        "pole_extension_landmarks",
        "pole_axis",
        "reliability",
    }
    missing = existing - field_names
    assert not missing, (
        f"plan 01-01/01-02 의 PoseFrame 필드 회귀 발생: missing={missing}"
    )


# ---------------------------------------------------------------------------
# Test 9: pose_engines/__init__.py __all__ 에 'PoseEngine' 노출
# ---------------------------------------------------------------------------
def test_pose_engines_init_exports_pose_engine() -> None:
    import sunity_shared.analysis.pose_engines as pe_pkg

    assert hasattr(pe_pkg, "__all__"), "pose_engines 패키지에 __all__ 정의 필요"
    assert "PoseEngine" in pe_pkg.__all__, (
        f"pose_engines.__all__ 에 'PoseEngine' 노출 필요 — 현재={pe_pkg.__all__}"
    )

    # 실제 import 가능
    from sunity_shared.analysis.pose_engines import PoseEngine  # noqa: F401
