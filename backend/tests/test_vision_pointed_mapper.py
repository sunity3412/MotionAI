"""Phase 25 (25-01 Task 1) — 좁은 pointed-joint 매퍼 단위 테스트.

pointed_joints_from_supported_differences: Gemini supported_differences 의 canonical
`_faultKey` 만 소비해 "감점 window-측정 eligible 관절" 을 좁게 도출한다 (OD-1).

박제 정신 (25-RESEARCH §2 · 함정 ⑥):
  · 표시용 fault_joints_from_differences(trunk/양다리 broad 확장)와 **분리** — line 하나가
    양어깨 4관절을 "짚은" 것으로 만들면 vision 게이트가 무력화됨.
  · 명시 keypoint_set 4종(shoulder/arm/leg/hip)만 매핑, line/torso/head_neck/grip 은 방출 0.
  · side=unknown → 양측 eligible (OD-1 — 판정은 측정+tol 20° 게이트, fail-closed 버리기 금지).
  · 반환 = JOINT_KEYS 순서 안정 tuple, 중복 제거, JOINT_KEYS 외 방출 0.
전부 순수 함수 — 실 Gemini/Pod/S3/Firestore 호출 0. PYTHONPATH=shared/python.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402
from sunity_shared.analysis.vision_veto import (  # noqa: E402
    FaultKey,
    pointed_joints_from_supported_differences,
)


def _rec(keypoint_set: str, side: str = "unknown", *, part_scope: str = "upper_body",
         fault_kind: str = "extension_or_alignment", as_dict: bool = False) -> dict:
    """supported_differences record stub — `_faultKey` 메타만 본다 (body_part 재파싱 금지)."""
    fk = FaultKey(
        part_scope=part_scope, side=side,
        keypoint_set=keypoint_set, fault_kind=fault_kind,
    )
    return {
        "body_part": "자유텍스트 (매퍼가 읽으면 안 됨)",
        "_faultKey": fk.to_dict() if as_dict else fk,
        "_supportCount": 2,
        "_sourceIds": ("a", "b"),
    }


# ── 명시 keypoint_set 4종 side 해소 ─────────────────────────────────────────────


def test_shoulder_left_maps_single_side():
    assert pointed_joints_from_supported_differences(
        [_rec("shoulder", "left")]
    ) == ("left_shoulder",)


def test_shoulder_unknown_maps_both_sides():
    """OD-1 — side=unknown 은 양측 모두 window-측정 eligible (판정은 측정+tol 게이트)."""
    assert pointed_joints_from_supported_differences(
        [_rec("shoulder", "unknown")]
    ) == ("left_shoulder", "right_shoulder")


def test_arm_right_maps_elbow():
    assert pointed_joints_from_supported_differences(
        [_rec("arm", "right")]
    ) == ("right_elbow",)


def test_leg_maps_knee_and_hip_maps_hip():
    assert pointed_joints_from_supported_differences(
        [_rec("leg", "left", part_scope="lower_body")]
    ) == ("left_knee",)
    assert pointed_joints_from_supported_differences(
        [_rec("hip", "right", part_scope="lower_body")]
    ) == ("right_hip",)


def test_hip_unknown_maps_both_hips():
    assert pointed_joints_from_supported_differences(
        [_rec("hip", "unknown", part_scope="lower_body")]
    ) == ("left_hip", "right_hip")


# ── broad 확장 금지 (리서치 함정 ⑥) ───────────────────────────────────────────


def test_broad_keypoint_sets_emit_nothing():
    """line/torso/head_neck/grip → 방출 0 — line 하나가 4관절을 '짚은' 것으로 만들면
    vision 게이트 무력화 (해당 관절은 기존 full-path median 유지)."""
    for kp_set, scope in (
        ("line", "line"), ("torso", "core"),
        ("head_neck", "upper_body"), ("grip", "upper_body"),
    ):
        assert pointed_joints_from_supported_differences(
            [_rec(kp_set, "unknown", part_scope=scope)]
        ) == (), f"{kp_set} 가 pointed 관절을 방출했다 (broad 확장 금지)"


def test_broad_record_does_not_leak_into_mixed_union():
    """line + shoulder 혼재 → shoulder 관절만 (line 은 기여 0)."""
    out = pointed_joints_from_supported_differences(
        [_rec("line", "unknown", part_scope="line"), _rec("shoulder", "left")]
    )
    assert out == ("left_shoulder",)


# ── union / 순서 / 중복 / 방어 ────────────────────────────────────────────────


def test_union_is_joint_keys_order_stable_and_deduped():
    """복수 record union: 입력 순서 무관 JOINT_KEYS 순서, 중복 제거."""
    records = [
        _rec("hip", "right", part_scope="lower_body"),
        _rec("shoulder", "unknown"),
        _rec("arm", "left"),
        _rec("shoulder", "left"),  # left_shoulder 중복
    ]
    out = pointed_joints_from_supported_differences(records)
    assert out == ("left_elbow", "left_shoulder", "right_shoulder", "right_hip")
    # JOINT_KEYS 순서 안정 재확인 (하드코딩 아닌 순서 계약)
    assert list(out) == [jk for jk in JOINT_KEYS if jk in out]


def test_all_outputs_are_joint_keys_members():
    records = [
        _rec("shoulder", "unknown"), _rec("arm", "unknown"),
        _rec("leg", "unknown", part_scope="lower_body"),
        _rec("hip", "unknown", part_scope="lower_body"),
    ]
    out = pointed_joints_from_supported_differences(records)
    assert out and all(jk in JOINT_KEYS for jk in out)


def test_missing_or_malformed_faultkey_skipped():
    """`_faultKey` 부재/형상불량 record → graceful skip (방출 0)."""
    assert pointed_joints_from_supported_differences([{"body_part": "어깨"}]) == ()
    assert pointed_joints_from_supported_differences([{"_faultKey": "not-a-key"}]) == ()
    assert pointed_joints_from_supported_differences([None, {}, 42]) == ()


def test_faultkey_dict_input_accepted_unknown_enum_skipped():
    """dict `_faultKey` 는 FaultKey.from_dict 시도 — enum 밖 값은 skip (T-25-01)."""
    ok = _rec("shoulder", "left", as_dict=True)
    assert pointed_joints_from_supported_differences([ok]) == ("left_shoulder",)
    bad = {
        "_faultKey": {
            "part_scope": "upper_body", "side": "left",
            "keypoint_set": "tail",  # enum 밖
            "fault_kind": "extension_or_alignment",
        }
    }
    assert pointed_joints_from_supported_differences([bad]) == ()


def test_empty_or_none_input():
    assert pointed_joints_from_supported_differences([]) == ()
    assert pointed_joints_from_supported_differences(None) == ()
