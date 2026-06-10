"""Phase 12 Wave 0B (Plan 12-01) — KeypointReport 3-way schema lockstep.

docs/contract.md §9.12 + TS interface (analysis.ts) + Python frozen dataclass
3 곳 모두 동일 10 필드 + 8 keypoint enum 박제 검증 (Phase 9 D-09-U1 mirror).
"""

from __future__ import annotations

from pathlib import Path

from sunity_shared.analysis.keypoint_frame import (
    NUM_KEYPOINTS_PHASE12,
    JOINT_KEY_TO_ANGLE_KEY,
    KeypointReport,
    _AXIS_POLYLINE_POINTS,
    _KEYPOINT_NAMES,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT_MD = _REPO_ROOT / "docs" / "contract.md"
_ANALYSIS_TS = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"


def test_docs_contract_has_9_12_heading() -> None:
    """docs/contract.md 가 §9.12 KeypointReport heading 보유."""
    contents = _CONTRACT_MD.read_text(encoding="utf-8")
    assert "§9.12 KeypointReport" in contents, (
        "docs/contract.md §9.12 KeypointReport heading 누락"
    )


def test_docs_contract_has_ten_fields() -> None:
    """docs/contract.md §9.12.2 표가 10 필드 모두 박제 (R10 + R7 iter-2)."""
    contents = _CONTRACT_MD.read_text(encoding="utf-8")
    required_fields = [
        "version",
        "joints",
        "frames",
        "fps",
        "data",
        "confidence",
        "reliability",
        "axisData",
        "axisMask",
        "warnings",
    ]
    # §9.12 section 안에서만 박제 검증.
    idx = contents.find("§9.12 KeypointReport")
    assert idx >= 0
    # next major section (`*Phase 12 Wave 0B 추가:` footer) 까지 slice.
    next_section = contents.find("*Phase 12 Wave 0B 추가:", idx)
    section = contents[idx : next_section if next_section >= 0 else len(contents)]
    for field in required_fields:
        assert field in section, f"§9.12 누락 필드: {field}"


def test_docs_contract_has_frames_joints_2_formula() -> None:
    """docs/contract.md §9.12 에 'T × J × 2' 또는 'frames × J × 2' 산식 박제."""
    contents = _CONTRACT_MD.read_text(encoding="utf-8")
    idx = contents.find("§9.12 KeypointReport")
    assert idx >= 0
    section = contents[idx : idx + 5000]
    assert (
        "T × 8 × 2" in section
        or "T × J × 2" in section
        or "frames × J × 2" in section
        or "T × 3 × 2" in section
    ), "§9.12 에 flat shape 산식 (T × J × 2 또는 T × 3 × 2) 누락"


def test_ts_interface_has_ten_fields() -> None:
    """TS KeypointReport interface 가 10 필드 박제 (Python dataclass mirror)."""
    contents = _ANALYSIS_TS.read_text(encoding="utf-8")
    assert "export interface KeypointReport" in contents
    # 10 필드 모두 박제.
    required_camel = [
        "version:",
        "joints:",
        "frames:",
        "fps:",
        "data:",
        "confidence:",
        "reliability:",
        "axisData:",
        "axisMask:",
        "warnings:",
    ]
    idx = contents.find("export interface KeypointReport")
    # interface body 끝 = `warnings: string[];\n}` (마지막 필드 다음 줄의 단독 `}`).
    end_idx = contents.find("\n}", idx)
    assert end_idx > idx
    section = contents[idx:end_idx]
    for field in required_camel:
        assert field in section, f"TS KeypointReport 누락 필드: {field}"


def test_ts_has_keypoint_name_literal() -> None:
    """TS KeypointName Literal 박제 (R11 — 8 entry)."""
    contents = _ANALYSIS_TS.read_text(encoding="utf-8")
    assert "export type KeypointName" in contents
    for name in _KEYPOINT_NAMES:
        assert f"'{name}'" in contents, f"TS KeypointName 누락: {name}"


def test_ts_analysis_result_has_keypoint_report_field() -> None:
    """TS AnalysisResult.keypointReport? 박제."""
    contents = _ANALYSIS_TS.read_text(encoding="utf-8")
    assert "keypointReport?: KeypointReport | null" in contents, (
        "AnalysisResult.keypointReport? optional + nullable 필드 누락"
    )


def test_ts_reference_motion_has_reference_keypoint_report() -> None:
    """TS ReferenceMotion.referenceKeypointReport? 박제 (R3 iter-2).

    `keypointReport?` 가 아니라 `referenceKeypointReport?` 강제 — 의미 분리.
    """
    contents = _ANALYSIS_TS.read_text(encoding="utf-8")
    assert "referenceKeypointReport?: KeypointReport | null" in contents, (
        "ReferenceMotion.referenceKeypointReport? optional + nullable 필드 누락"
    )


def test_python_dataclass_has_eight_body_keypoints() -> None:
    """Python _KEYPOINT_NAMES tuple 이 R11 정합 8 박제 (axis 제외)."""
    assert len(_KEYPOINT_NAMES) == 8
    assert NUM_KEYPOINTS_PHASE12 == 8
    expected = {
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_hand",
        "right_hand",
    }
    assert set(_KEYPOINT_NAMES) == expected
    # axis 는 KeypointName 안에 박제 X (별도 axisData field).
    assert "axis" not in _KEYPOINT_NAMES


def test_python_joint_key_to_angle_key_hand_to_wrist() -> None:
    """JOINT_KEY_TO_ANGLE_KEY 의 hand → wrist 매핑 박제 (loose hand)."""
    assert JOINT_KEY_TO_ANGLE_KEY["left_hand"] == "left_wrist"
    assert JOINT_KEY_TO_ANGLE_KEY["right_hand"] == "right_wrist"
    # 다른 6 keypoint 는 동일 키 매핑.
    for name in ("left_shoulder", "right_shoulder", "left_hip", "right_hip",
                 "left_knee", "right_knee"):
        assert JOINT_KEY_TO_ANGLE_KEY[name] == name


def test_axis_polyline_three_points() -> None:
    """R2 정합 — _AXIS_POLYLINE_POINTS = 3 (shoulder_mid/hip_mid/knee_mid?)."""
    assert _AXIS_POLYLINE_POINTS == 3


def test_python_dataclass_field_order_non_default_first() -> None:
    """Phase 9 D-09-R1 mirror — non-default → default 순서 강제.

    Python dataclass rule — default 이후 non-default 필드 금지.
    KeypointReport 의 warnings 만 default_factory 박제 (마지막).
    """
    import dataclasses

    fields = dataclasses.fields(KeypointReport)
    # 마지막 필드만 default 박제.
    for i, f in enumerate(fields[:-1]):
        # warnings 외 모든 필드는 default 없어야.
        assert f.default is dataclasses.MISSING and (
            f.default_factory is dataclasses.MISSING
        ), f"필드 {f.name} 가 default 보유 — order 룰 위반"
    last_field = fields[-1]
    assert last_field.name == "warnings"
    assert last_field.default_factory is not dataclasses.MISSING
