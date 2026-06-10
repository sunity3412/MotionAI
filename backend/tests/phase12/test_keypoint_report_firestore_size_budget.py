"""Phase 12 Wave 0B (Plan 12-01) — Firestore size budget (R5 정합).

9 fps × worst-case 60 s synthetic KeypointReport 의 Firestore JSON byte
측정. ≤ 700 KiB. 미통과 시 Cloud Storage JSON pointer 박제 plan (별도 plan 14,
follow-up).

NOTE: 실제 Firestore 는 1 MiB 한도. 700 KiB 는 다른 필드 (forceSignalsReport,
body_comparison_report 등) 합산 마진 박제 (R5 정합).
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


def _load_pipeline_app():
    pipeline_dir = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
    if str(pipeline_dir) not in sys.path:
        sys.path.insert(0, str(pipeline_dir))
    sys.modules.pop("app", None)
    import app as pipeline_app  # noqa: WPS433

    return importlib.reload(pipeline_app)


def test_worst_case_size_budget_under_700_kib() -> None:
    """9 fps × 60 s × 10 필드 worst-case → ≤ 700 KiB."""
    from sunity_shared.analysis.keypoint_frame import (
        NUM_KEYPOINTS_PHASE12,
        KeypointReport,
    )

    pipeline_app = _load_pipeline_app()

    FPS = 9.0
    DURATION_S = 60
    T = int(FPS * DURATION_S)  # 540
    J = NUM_KEYPOINTS_PHASE12  # 8

    # Synthetic worst-case — 모든 float 가 7-digit precision (0.1234567 같은 박제).
    # JSON 직렬화 시 한 number 당 ~9 byte ("0.1234567,").
    report = KeypointReport(
        version="1.0",
        joints=[
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_hand",
            "right_hand",
        ],
        frames=T,
        fps=FPS,
        data=[0.1234567] * (T * J * 2),
        confidence=[0.9876543] * (T * J),
        reliability=["high"] * T,
        axis_data=[0.1234567] * (T * 3 * 2),
        axis_mask=[True] * (T * 3),
        warnings=["axis_polyline_unavailable"],
    )

    # camelCase 변환 (Firestore 저장 직전 형태).
    payload = pipeline_app._dataclass_to_camel_case_dict(report)
    # Firestore 는 JSON 유사 직렬화 — JSON byte 측정으로 근사.
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    size_kib = len(json_bytes) / 1024.0

    # 측정값 기록 (CI log).
    print(f"\n[size-budget] T={T} J={J} → {size_kib:.1f} KiB")

    assert size_kib <= 700.0, (
        f"R5 size budget 초과: {size_kib:.1f} KiB > 700 KiB. "
        f"Cloud Storage JSON pointer 박제 plan 박제 (별도 plan 14)."
    )


def test_typical_30s_size_budget_under_350_kib() -> None:
    """typical 30 s × 9 fps → ≤ 350 KiB (worst-case 의 1/2 sanity)."""
    from sunity_shared.analysis.keypoint_frame import (
        NUM_KEYPOINTS_PHASE12,
        KeypointReport,
    )

    pipeline_app = _load_pipeline_app()

    FPS = 9.0
    DURATION_S = 30
    T = int(FPS * DURATION_S)  # 270
    J = NUM_KEYPOINTS_PHASE12

    report = KeypointReport(
        version="1.0",
        joints=[
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_hand",
            "right_hand",
        ],
        frames=T,
        fps=FPS,
        data=[0.5] * (T * J * 2),
        confidence=[0.9] * (T * J),
        reliability=["high"] * T,
        axis_data=[0.5] * (T * 3 * 2),
        axis_mask=[True] * (T * 3),
        warnings=[],
    )
    payload = pipeline_app._dataclass_to_camel_case_dict(report)
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    size_kib = len(json_bytes) / 1024.0
    print(f"\n[size-budget typical 30s] T={T} → {size_kib:.1f} KiB")
    assert size_kib <= 350.0
