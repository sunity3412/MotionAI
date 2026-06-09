"""Plan 08.1-01 Wave 1 — compute_axis_deviation 실 tilt-only 본체 정합 검증.

Phase 8.1 박제 (2026-06-09): distance 차원 hard break — IPSF Code of Points 글로벌
distance 항목 부재. compute_axis_deviation 본체 = tilt-only metric (Wave 1).

Wave 0 transitional stub 시절의 4 test 가 Wave 1 가 실 본체 배포 시 RED 가 됨 —
본 파일 에서 새 본체 test 로 교체 (Wave 1 plan must_haves 박제). 신설 본 본체 test
들은 phase08_1/test_compute_axis_tilt_only.py 가 보유 — 본 파일 은 R2 drift
defense (torso_scale denominator 영구 금지) 만 보존.
"""

from __future__ import annotations


# ── R2 drift defense — Wave 1 본체 정합 보존 ──────────────────────────────


def test_torso_scale_not_used_as_denominator() -> None:
    """REVIEWS R2 drift defense — compute_axis_deviation 모듈 안에서
    BodyNormalizationProfile.torso_scale 사용 영구 금지.

    Wave 1 본체 = tilt-only metric. torso scale 분모 사용 부재 (distance 차원 영구 제거).
    """
    import inspect

    from sunity_shared.analysis import force_signals

    src = inspect.getsource(force_signals)
    # 본 module 안에서 BodyNormalizationProfile 사용 금지.
    assert "BodyNormalizationProfile" not in src
    # torso_scale literal 사용 금지 (median_torso_length 만 사용).
    assert ".torso_scale" not in src
