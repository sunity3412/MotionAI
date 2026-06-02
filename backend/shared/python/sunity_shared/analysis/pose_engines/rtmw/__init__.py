"""RTMW 어댑터 패키지 (plan 21 구현 완료, plan 22 3D path stub 추가).

RTMWPoseEngine: rtmlib RTMW 133 wholebody → PoseEngine Protocol 구현 (plan 21).
LicenseViolationError: weights_manifest 게이트 위반 예외 (plan 21).

Plan 22 (3D path stub):
  RTMW3DPoseEngine: 옵션 A 어댑터 stub — RTMW3D 직접 사용.
  RTMWLifterPoseEngine: 옵션 B 어댑터 stub — RTMW 2D + MotionBERT lifter.

본 두 어댑터는 Plan 22 Task 1 산출 stub 이며, Task 2 belle checkpoint
응답 (option_a 또는 option_b) 후 선택된 1개만 실 구현. 자세 비교는
`three_d_path_decision.md` 참조.

Plan 20: weights_manifest.json + license audit (docs/licenses/rtmw-weights-audit.md).
Plan 21: RTMWPoseEngine 구현 (Task 2) + RTMW133ToCOCO17Adapter (Task 1).
Plan 22: three_d_path_decision.md + RTMW3DPoseEngine stub + RTMWLifterPoseEngine stub.

H-2 박제: 모든 엔진 클래스는 접근 시점에만 import (lazy __getattr__).
manifest schema 강제: backend/tests/test_rtmw_weights_manifest.py
audit doc: docs/licenses/rtmw-weights-audit.md
"""

from __future__ import annotations

__all__ = [
    "RTMWPoseEngine",
    "LicenseViolationError",
    "RTMW3DPoseEngine",
    "RTMWLifterPoseEngine",
]


def __getattr__(name: str) -> object:
    """H-2 박제: 엔진 클래스는 접근 시점에만 import (lazy module load)."""
    if name == "RTMWPoseEngine":
        from .rtmw_engine import RTMWPoseEngine  # noqa: PLC0415
        return RTMWPoseEngine
    if name == "LicenseViolationError":
        from .rtmw_engine import LicenseViolationError  # noqa: PLC0415
        return LicenseViolationError
    if name == "RTMW3DPoseEngine":
        from .rtmw3d_engine import RTMW3DPoseEngine  # noqa: PLC0415
        return RTMW3DPoseEngine
    if name == "RTMWLifterPoseEngine":
        from .lifter_pipeline import RTMWLifterPoseEngine  # noqa: PLC0415
        return RTMWLifterPoseEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
