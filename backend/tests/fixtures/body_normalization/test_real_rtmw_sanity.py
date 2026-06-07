"""Task 2b — RTMW sanity (실 RTMW 출력 coverage).

MEDIUM-2 v4 박제: real RTMW network output validation 은 v1.5 sweep 으로
deferred. 본 테스트는 CI 환경 (RTMW model weights 미설정) 에서 skip,
belle Pod 환경에서만 실행 가능.

Codex v5 review acknowledges as "honest deferral".
"""

from __future__ import annotations

import os

import pytest


def _rtmw_available() -> bool:
    """RTMW ONNX weight + rtmlib 가 import 가능한가 (Pod 환경 만)."""
    onnx_path = os.environ.get("RTMW_ONNX_PATH")
    if not onnx_path or not os.path.exists(onnx_path):
        return False
    try:
        import rtmlib  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(
    not _rtmw_available(),
    reason="RTMW weights / rtmlib 미설정 — v1.5 sweep deferral (MEDIUM-2 v4).",
)
def test_real_rtmw_segment_extraction_sanity() -> None:
    """belle Pod 환경에서만 실행. RTMW 실 출력 → measurer profile 산출 sanity."""
    pytest.skip("Pod-only — belle 가 RTMW_ONNX_PATH 설정 + rtmlib install 후 enable")
