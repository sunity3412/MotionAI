"""Task 1 (Plan 06-03, R2 fix 2026-06-08 round-2) — firestore_admin.update_reference_body_data.

박제 정신:
  - R2 fix (round-2): 단일 helper 가 두 필드 (bodyNormalizationProfile +
    bodyComparisonSourcePose) atomic merge. 기존 plan 의 단일 필드 helper
    `update_reference_body_profile` 폐기.
  - [[firestore-nested-array-flat]]: Plan 06-02 의 `_validate_flat_dict_no_nested_array`
    재사용 — list[list] 또는 nested-dict-with-list 거절.
  - source_pose=None 시 partial backfill 허용 (Plan 06-03 백필 도중 일부 motion 의
    대표 frame 추출 실패 graceful).
  - R2 핵심: source_pose.values 길이 == 4 × len(jointKeys).
  - Test 1~9 = Plan 06-03 behavior block 1:1 매핑.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _body_profile_basic() -> dict:
    """기본 BodyNormalizationProfile (camelCase, Firestore 쓰기 형식)."""
    return {
        "estimatedHeightScale": 1.0,
        "armScale": 1.05,
        "legScale": 0.95,
        "torsoScale": 1.0,
        "shoulderHipRatio": 1.0,
        "confidence": 0.8,
        "warnings": [],
    }


def _source_pose_basic() -> dict:
    """기본 BodyComparisonSourcePose (camelCase, Firestore 쓰기 형식).

    jointKeys 17 + values 68 (= 4 × 17). 모든 값 finite.
    """
    joint_keys = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle",
    ]
    # 17 keypoint × 4채널 = 68 flat float.
    values = [float(i) for i in range(68)]
    return {
        "jointKeys": joint_keys,
        "values": values,
        "frameIndex": 12,
        "torsoPx": 350.0,
        "confidence": 0.85,
        "measuredAt": 1700000000000,
    }


@pytest.fixture
def mock_doc(monkeypatch):
    """firestore_admin._doc → MagicMock 박제."""
    from sunity_shared import firestore_admin

    doc = MagicMock()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: doc)
    return doc


def test_update_reference_body_data_sets_both_fields(mock_doc):
    """Test 1 — body_profile + source_pose 모두 박제.

    Firestore set merge 호출 + payload 의 두 필드 모두 박제 + 두 필드의 *UpdatedAt 타임스탬프.
    """
    from sunity_shared import firestore_admin

    bp = _body_profile_basic()
    sp = _source_pose_basic()
    firestore_admin.update_reference_body_data(
        "ref-climb", body_profile=bp, source_pose=sp
    )
    assert mock_doc.set.called
    call = mock_doc.set.call_args
    payload = call.args[0]
    assert call.kwargs.get("merge") is True
    assert payload["bodyNormalizationProfile"] == bp
    assert payload["bodyComparisonSourcePose"] == sp
    assert isinstance(payload["bodyNormalizationProfileUpdatedAt"], int)
    assert isinstance(payload["bodyComparisonSourcePoseUpdatedAt"], int)


def test_update_reference_body_data_rejects_nested_array_in_body_profile(mock_doc):
    """Test 2 (W5 정합) — body_profile.warnings 가 list[list] → TypeError."""
    from sunity_shared import firestore_admin

    bp = _body_profile_basic()
    bp["warnings"] = [["nested"], ["bad"]]  # list[list] 위반
    sp = _source_pose_basic()
    with pytest.raises(TypeError):
        firestore_admin.update_reference_body_data(
            "ref-climb", body_profile=bp, source_pose=sp
        )


def test_update_reference_body_data_rejects_nested_array_in_source_pose(mock_doc):
    """Test 3 (W5 정합) — source_pose.values 안에 list 가 들어있으면 TypeError.

    BodyComparisonSourcePose.values 는 정의상 flat float list 만 허용.
    """
    from sunity_shared import firestore_admin

    bp = _body_profile_basic()
    sp = _source_pose_basic()
    # values 안에 nested list 주입 → 길이 검증보다 nested-array 검증이 먼저 트리거되지
    # 않더라도 W5 path 가 TypeError. 길이 자체는 일치 유지 (68개).
    sp["values"] = [[0.0]] * 68
    with pytest.raises(TypeError):
        firestore_admin.update_reference_body_data(
            "ref-climb", body_profile=bp, source_pose=sp
        )


def test_update_reference_body_data_rejects_missing_motion_id(mock_doc):
    """Test 4 — motion_id 빈 문자열 → ValueError."""
    from sunity_shared import firestore_admin

    with pytest.raises(ValueError):
        firestore_admin.update_reference_body_data(
            "", body_profile=_body_profile_basic(), source_pose=_source_pose_basic()
        )


def test_update_reference_body_data_validates_body_profile_required_fields(mock_doc):
    """Test 5 — body_profile 에 estimatedHeightScale 누락 → ValueError."""
    from sunity_shared import firestore_admin

    bp = _body_profile_basic()
    bp.pop("estimatedHeightScale")
    with pytest.raises(ValueError):
        firestore_admin.update_reference_body_data(
            "ref-climb", body_profile=bp, source_pose=_source_pose_basic()
        )


def test_update_reference_body_data_validates_source_pose_required_fields(mock_doc):
    """Test 6 — source_pose 에 jointKeys 또는 values 누락 → ValueError."""
    from sunity_shared import firestore_admin

    sp = _source_pose_basic()
    sp.pop("jointKeys")
    with pytest.raises(ValueError):
        firestore_admin.update_reference_body_data(
            "ref-climb", body_profile=_body_profile_basic(), source_pose=sp
        )


def test_update_reference_body_data_source_pose_values_length_matches_joint_keys(
    mock_doc,
):
    """Test 7 (R2 핵심) — values length != 4 × len(jointKeys) → ValueError.

    jointKeys 17개 + values 60개 → ValueError (필요 = 68).
    """
    from sunity_shared import firestore_admin

    sp = _source_pose_basic()
    # 17 키 유지, values 만 60개로 축소 (4 × 17 = 68 ≠ 60)
    sp["values"] = [float(i) for i in range(60)]
    with pytest.raises(ValueError):
        firestore_admin.update_reference_body_data(
            "ref-climb", body_profile=_body_profile_basic(), source_pose=sp
        )


def test_update_reference_body_data_accepts_list_of_strings_in_warnings(mock_doc):
    """Test 8 (W5 정합) — body_profile.warnings 가 list[str] → PASS (예외 없음)."""
    from sunity_shared import firestore_admin

    bp = _body_profile_basic()
    bp["warnings"] = ["temporal_variance_high", "spatial_dispersion_high"]
    firestore_admin.update_reference_body_data(
        "ref-climb", body_profile=bp, source_pose=_source_pose_basic()
    )
    assert mock_doc.set.called


def test_update_reference_body_data_source_pose_optional(mock_doc):
    """Test 9 (R2 핵심 — partial backfill 허용) — source_pose=None.

    body_profile 만 merge, bodyComparisonSourcePose 필드 무수정.
    """
    from sunity_shared import firestore_admin

    firestore_admin.update_reference_body_data(
        "ref-climb", body_profile=_body_profile_basic(), source_pose=None
    )
    assert mock_doc.set.called
    payload = mock_doc.set.call_args.args[0]
    assert "bodyNormalizationProfile" in payload
    assert "bodyNormalizationProfileUpdatedAt" in payload
    # source_pose 미박제 → 키 자체 부재 (Firestore 가 기존 값 보존)
    assert "bodyComparisonSourcePose" not in payload
    assert "bodyComparisonSourcePoseUpdatedAt" not in payload
