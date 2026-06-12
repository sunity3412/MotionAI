"""Phase 17 eval/guardrail 박제 (Plan 06).

박제 정신:
  · AI-SPEC §5 (E1~E8 8 dimension) + §6 (G1~G6 6 guardrail) + §7 (Phoenix 5 metric
    + Smart Sampling) 코드화.
  · `phoenix_setup` 의 telemetry 부트스트랩 + `llm_judge` 의 영역 B 코칭 톤 binary
    pass + `sampling` 의 가중치 산출 + Firestore eval/phase17 박제.
  · 본 패키지는 optional — telemetry extras 미설치 환경에서도 import 자체는 박힘
    (분석 흐름 차단 0).

표준 진입점:
  >>> from sunity_shared.eval import bootstrap_tracing, TELEMETRY_OK
  >>> if TELEMETRY_OK:
  ...     bootstrap_tracing()
"""

from __future__ import annotations

from .phoenix_setup import TELEMETRY_OK, bootstrap_tracing

__all__ = ["TELEMETRY_OK", "bootstrap_tracing"]
