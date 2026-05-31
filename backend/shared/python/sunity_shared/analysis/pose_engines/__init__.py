"""포즈 엔진 어댑터 모음 (MediaPipe 제품, NLF는 R&D 격리 — backend/research에 별도).

Phase 1 D-06/D-07 박제:
  - MediaPipePoseEngine: 제품 경로 (sunity_shared 안)
  - MediaPipeWithLifterEngine: MP 2D + MotionBERT 3D lift 복합 (Plan 01-08)
  - NlfPoseEngine: R&D 격리 (backend/research/pose_engines/nlf/ — 제품 import 경로 밖)

H-2 박제: 모든 엔진은 lazy export (접근 시점에만 import).
  Module load 단계에서 mediapipe/torch import 없음 — Lambda fail-fast 안전.
"""

from __future__ import annotations

from ..interfaces import PoseEngine, NoHumanError

__all__ = ["PoseEngine", "NoHumanError", "MediaPipePoseEngine", "MediaPipeWithLifterEngine"]


def __getattr__(name: str) -> object:
    """H-2 박제: 엔진 클래스는 접근 시점에만 import (lazy module load)."""
    if name == "MediaPipePoseEngine":
        from .mediapipe_engine import MediaPipePoseEngine  # noqa: PLC0415
        return MediaPipePoseEngine
    if name == "MediaPipeWithLifterEngine":
        from .mediapipe_lifter_engine import MediaPipeWithLifterEngine  # noqa: PLC0415
        return MediaPipeWithLifterEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
