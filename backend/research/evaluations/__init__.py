"""MediaPipe vs NLF 회귀 검증 평가 패키지.

compare_engines.py의 핵심 public API를 re-export한다.

Phase 1 Wave 2 시점 — NLF는 아직 sunity_shared.analysis.pose_estimator
(옛 위치)에서 import. compare_engines.py가 그 경로를 사용 (H-1 박제).
"""

from .compare_engines import (  # noqa: F401
    run_engine,
    EngineResult,
    AVG_CONFIDENCE_THRESHOLD,
)
