"""RTMW 어댑터 패키지 (plan 21 구현 완료).

RTMWPoseEngine: rtmlib RTMW 133 wholebody → PoseEngine Protocol 구현.
LicenseViolationError: weights_manifest 게이트 위반 예외.

Plan 20: weights_manifest.json + license audit (docs/licenses/rtmw-weights-audit.md).
Plan 21: RTMWPoseEngine 구현 (Task 2) + RTMW133ToCOCO17Adapter (Task 1).

H-2 박제: RTMWPoseEngine 클래스는 접근 시점에만 import (lazy __getattr__).
manifest schema 강제: backend/tests/test_rtmw_weights_manifest.py
audit doc: docs/licenses/rtmw-weights-audit.md
"""

from __future__ import annotations

__all__ = ["RTMWPoseEngine", "LicenseViolationError"]


def __getattr__(name: str) -> object:
    """H-2 박제: RTMWPoseEngine 클래스는 접근 시점에만 import (lazy module load)."""
    if name == "RTMWPoseEngine":
        from .rtmw_engine import RTMWPoseEngine  # noqa: PLC0415
        return RTMWPoseEngine
    if name == "LicenseViolationError":
        from .rtmw_engine import LicenseViolationError  # noqa: PLC0415
        return LicenseViolationError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
