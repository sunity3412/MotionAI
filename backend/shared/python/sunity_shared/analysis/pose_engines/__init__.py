"""포즈 엔진 어댑터 모음 (MediaPipe/RTMW 제품, NLF는 R&D 격리 — backend/research에 별도).

Phase 1 D-06/D-07 박제:
  - MediaPipePoseEngine: 제품 경로 (sunity_shared 안)
  - MediaPipeWithLifterEngine: MP 2D + MotionBERT 3D lift 복합 (Plan 01-08)
  - NlfPoseEngine: R&D 격리 (backend/research/pose_engines/nlf/ — 제품 import 경로 밖)

Plan 01-21 추가 (D-17 운영 백본 RTMW pivot):
  - RTMWPoseEngine: RTMW 133 wholebody 어댑터 (Apache-2.0)
  - LicenseViolationError: D-25 라이선스 게이트 예외

H-2 박제: 모든 엔진은 lazy export (접근 시점에만 import).
  Module load 단계에서 mediapipe/torch/rtmlib import 없음 — Lambda fail-fast 안전.
"""

from __future__ import annotations

from ..interfaces import PoseEngine, NoHumanError

__all__ = [
    "PoseEngine",
    "NoHumanError",
    "MediaPipePoseEngine",
    "MediaPipeWithLifterEngine",
    "RTMWPoseEngine",
    "LicenseViolationError",
]


def __getattr__(name: str) -> object:
    """H-2 박제: 엔진 클래스는 접근 시점에만 import (lazy module load)."""
    if name == "MediaPipePoseEngine":
        from .mediapipe_engine import MediaPipePoseEngine  # noqa: PLC0415
        return MediaPipePoseEngine
    if name == "MediaPipeWithLifterEngine":
        from .mediapipe_lifter_engine import MediaPipeWithLifterEngine  # noqa: PLC0415
        return MediaPipeWithLifterEngine
    if name == "RTMWPoseEngine":
        from .rtmw.rtmw_engine import RTMWPoseEngine  # noqa: PLC0415
        return RTMWPoseEngine
    if name == "LicenseViolationError":
        from .rtmw.rtmw_engine import LicenseViolationError  # noqa: PLC0415
        return LicenseViolationError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
