"""Phase 12 Wave 0B (Plan 12-01) — KeypointReport frozen dataclass + __post_init__.

10 필드 (R10 + R7 iter-2) validator 검증:
  - version / joints / frames / fps (R3 required)
  - data flat T*J*2 (H3 iter-4 finite only)
  - confidence flat T*J (H3 iter-4 finite + [0, 1])
  - reliability len T (enum)
  - axisData flat T*3*2 (R2 + R7 iter-2 finite only)
  - axisMask flat T*3 strict bool (H3 iter-4 strict)
  - warnings non-empty str only

Phase 9 force_pattern dataclass test 패턴 mirror.
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from sunity_shared.analysis.keypoint_frame import (
    NUM_KEYPOINTS_PHASE12,
    KeypointReport,
)


def _kwargs(**overrides) -> dict:
    """KeypointReport 기본 kwargs (frames=2, joints=NUM_KEYPOINTS_PHASE12).

    32-14: joints 를 _KEYPOINT_NAMES 파생으로 구성 — 8→12 확장 자동 추종.
    T=2 → data len=T*J*2, confidence len=T*J, axisData len=12 (2*3*2),
    axisMask len=6 (2*3), reliability len=2.
    """
    from sunity_shared.analysis.keypoint_frame import _KEYPOINT_NAMES

    T = 2
    J = NUM_KEYPOINTS_PHASE12
    base = dict(
        version="1.0",
        joints=list(_KEYPOINT_NAMES),
        frames=T,
        fps=9.0,
        data=[0.5] * (T * J * 2),
        confidence=[0.9] * (T * J),
        reliability=["high", "medium"],
        axis_data=[0.5] * (T * 3 * 2),
        axis_mask=[True, True, True, True, True, False],
        warnings=[],
    )
    base.update(overrides)
    return base


# ── 기본 정상 박제 ──────────────────────────────────────────────────────


def test_valid_keypoint_report_constructs() -> None:
    """canonical kwargs → 정상 instantiate + frozen."""
    report = KeypointReport(**_kwargs())
    assert report.version == "1.0"
    assert report.frames == 2
    assert report.fps == 9.0
    assert len(report.joints) == NUM_KEYPOINTS_PHASE12
    assert len(report.data) == 2 * NUM_KEYPOINTS_PHASE12 * 2
    assert len(report.confidence) == 2 * NUM_KEYPOINTS_PHASE12
    assert len(report.axis_data) == 2 * 3 * 2
    assert len(report.axis_mask) == 2 * 3
    # frozen 검증.
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.version = "2.0"  # type: ignore[misc]


def test_zero_frames_constructs() -> None:
    """T=0 — 모든 list 빈, dataclass 통과 (정상 edge case)."""
    report = KeypointReport(
        version="1.0",
        joints=["left_shoulder"],
        frames=0,
        fps=9.0,
        data=[],
        confidence=[],
        reliability=[],
        axis_data=[],
        axis_mask=[],
        warnings=[],
    )
    assert report.frames == 0


# ── R10/R7 iter-2 — length validators ──────────────────────────────────


def test_data_length_mismatch_raises() -> None:
    """data 길이 != T*J*2 → ValueError + 메시지 'data length'."""
    with pytest.raises(ValueError, match="data length"):
        KeypointReport(**_kwargs(data=[0.5] * 10))  # T*J*2 expected, got 10


def test_confidence_length_mismatch_raises() -> None:
    """confidence 길이 != T*J → ValueError."""
    with pytest.raises(ValueError, match="confidence length"):
        KeypointReport(**_kwargs(confidence=[0.5] * 10))  # T*J expected


def test_reliability_length_mismatch_raises() -> None:
    """reliability 길이 != T → ValueError."""
    with pytest.raises(ValueError, match="reliability length"):
        KeypointReport(**_kwargs(reliability=["high"]))  # 2 expected


def test_axis_data_length_mismatch_raises() -> None:
    """R2 — axis_data 길이 != T*3*2 → ValueError + 메시지 'axis_data length'."""
    with pytest.raises(ValueError, match="axis_data length"):
        KeypointReport(**_kwargs(axis_data=[0.5] * 10))  # 12 expected


def test_axis_mask_length_mismatch_raises() -> None:
    """R7 iter-2 — axis_mask 길이 != T*3 → ValueError + 메시지 'axis_mask length'."""
    with pytest.raises(ValueError, match="axis_mask length"):
        KeypointReport(**_kwargs(axis_mask=[True] * 4))  # 6 expected


# ── H3 iter-4 — finite + range validators ─────────────────────────────


def test_data_nan_raises() -> None:
    """H3 iter-4 — data 에 NaN → ValueError 'data finite'.

    32-14: bad 길이를 T*J*2 파생으로 (하드코딩 32 제거 — 길이 오류가 finite
    오류를 가리는 것 방지).
    """
    bad = [0.5] * (2 * NUM_KEYPOINTS_PHASE12 * 2)
    bad[0] = float("nan")
    with pytest.raises(ValueError, match="data finite"):
        KeypointReport(**_kwargs(data=bad))


def test_data_inf_raises() -> None:
    """H3 iter-4 — data 에 Inf → ValueError 'data finite'."""
    bad = [0.5] * (2 * NUM_KEYPOINTS_PHASE12 * 2)
    bad[5] = math.inf
    with pytest.raises(ValueError, match="data finite"):
        KeypointReport(**_kwargs(data=bad))


def test_confidence_nan_raises() -> None:
    """H3 iter-4 — confidence 에 NaN → ValueError 'confidence range'.

    32-14: bad 길이 T*J 파생 (하드코딩 16 제거 — 길이 오류가 range 오류를
    가리면 테스트 의도가 무효화됨).
    """
    bad = [0.5] * (2 * NUM_KEYPOINTS_PHASE12)
    bad[0] = float("nan")
    with pytest.raises(ValueError, match="confidence range"):
        KeypointReport(**_kwargs(confidence=bad))


def test_confidence_out_of_range_negative_raises() -> None:
    """H3 iter-4 — confidence < 0 → ValueError 'confidence range'."""
    bad = [0.5] * (2 * NUM_KEYPOINTS_PHASE12)
    bad[0] = -0.1
    with pytest.raises(ValueError, match="confidence range"):
        KeypointReport(**_kwargs(confidence=bad))


def test_confidence_out_of_range_above_one_raises() -> None:
    """H3 iter-4 — confidence > 1 → ValueError 'confidence range'."""
    bad = [0.5] * (2 * NUM_KEYPOINTS_PHASE12)
    bad[0] = 1.5
    with pytest.raises(ValueError, match="confidence range"):
        KeypointReport(**_kwargs(confidence=bad))


def test_axis_data_nan_raises() -> None:
    """R7 iter-2 — axis_data 에 NaN 1개라도 있으면 ValueError 'axis_data finite'."""
    bad = [0.5] * 12
    bad[0] = float("nan")
    with pytest.raises(ValueError, match="axis_data finite"):
        KeypointReport(**_kwargs(axis_data=bad))


def test_axis_data_inf_raises() -> None:
    """R7 iter-2 — axis_data 에 Inf → ValueError."""
    bad = [0.5] * 12
    bad[3] = -math.inf
    with pytest.raises(ValueError, match="axis_data finite"):
        KeypointReport(**_kwargs(axis_data=bad))


# ── enum / type validators ───────────────────────────────────────────


def test_reliability_invalid_enum_raises() -> None:
    """reliability item ∉ {"high","medium","low"} → ValueError."""
    with pytest.raises(ValueError, match="reliability"):
        KeypointReport(**_kwargs(reliability=["high", "ultra"]))


def test_fps_zero_raises() -> None:
    """R3 — fps <= 0 → ValueError."""
    with pytest.raises(ValueError, match="fps"):
        KeypointReport(**_kwargs(fps=0))


def test_fps_negative_raises() -> None:
    """R3 — fps < 0 → ValueError."""
    with pytest.raises(ValueError, match="fps"):
        KeypointReport(**_kwargs(fps=-1.0))


def test_version_empty_raises() -> None:
    """version empty str → ValueError."""
    with pytest.raises(ValueError, match="version"):
        KeypointReport(**_kwargs(version=""))


def test_frames_negative_raises() -> None:
    """frames < 0 → ValueError."""
    with pytest.raises(ValueError, match="frames"):
        KeypointReport(**_kwargs(frames=-1))


def test_axis_mask_int_one_strict_rejects() -> None:
    """R7 iter-2 + H3 iter-4 — type(item) is bool strict.

    bool 은 int 의 subclass — int 1/0 false-positive 차단.
    """
    # axis_mask 전체 6개 중 첫 element 만 int 1 박제 (rest bool).
    bad = [1, True, True, True, True, False]
    with pytest.raises(ValueError, match="axis_mask"):
        KeypointReport(**_kwargs(axis_mask=bad))


def test_warnings_non_str_raises() -> None:
    """warnings element non-str → ValueError."""
    with pytest.raises(ValueError, match="warnings"):
        KeypointReport(**_kwargs(warnings=[1]))


def test_warnings_empty_str_raises() -> None:
    """warnings element empty str → ValueError."""
    with pytest.raises(ValueError, match="warnings"):
        KeypointReport(**_kwargs(warnings=[""]))
