"""Plan 08-01 Task 2 — contact_points.yaml 구조 유효성 + ContactPrimitiveKind 동행 검증.

검증:
  - yaml.safe_load 호출 (RCE 방지)
  - motions / default 키 존재 + 5 motion entry 모두 존재
  - 각 entry 의 name 이 12 ContactPoint enum 안 박제
  - 각 entry 의 kind 가 3 ContactPrimitiveKind enum 안 박제 (Plan 08-00 정합)
  - left_inner_thigh.kind == 'segment' / hip.kind == 'region_proxy' / left_hand.kind == 'keypoint'
  - default["expected_contact_points"] == []
  - yaml 본문에 !!python/ 태그 없음 (safe_load 호환성)

Plan 08-02 의 force_signals._load_expected_contact_points 가 본 파일 load + kind
박제 활용 (산출 방식 분기 source).
"""

from __future__ import annotations

from pathlib import Path

import yaml

# Plan 08-00 docs/contract.md §9.0.7 12 contact 분류 표 정합.
_VALID_CONTACT_POINTS = frozenset(
    {
        "left_hand",
        "right_hand",
        "left_inner_thigh",
        "right_inner_thigh",
        "left_knee",
        "right_knee",
        "left_foot",
        "right_foot",
        "left_ankle",
        "right_ankle",
        "hip",
        "unknown",
    }
)

# Plan 08-00 박제 ContactPrimitiveKind enum.
_VALID_KINDS = frozenset({"keypoint", "segment", "region_proxy"})

_EXPECTED_MOTION_IDS = (
    "ref-invert",
    "ref-foxtop",
    "ref-foxtop-split",
    "ref-climb",
    "ref-sideway-spin",
)

_YAML_PATH = (
    Path(__file__).resolve().parents[2] / "judging_data" / "contact_points.yaml"
)


def _load_raw() -> dict:
    with _YAML_PATH.open("r", encoding="utf-8") as fp:
        raw = yaml.safe_load(fp)
    assert isinstance(raw, dict), "contact_points.yaml top-level must be dict"
    return raw


def test_yaml_structure() -> None:
    raw = _load_raw()
    assert "motions" in raw and isinstance(raw["motions"], dict)
    assert "default" in raw and isinstance(raw["default"], dict)
    for motion_id in _EXPECTED_MOTION_IDS:
        assert motion_id in raw["motions"], (
            f"motion_id '{motion_id}' missing from contact_points.yaml"
        )


def test_motion_entries_all_valid_contact_points() -> None:
    raw = _load_raw()
    for motion_id, motion_block in raw["motions"].items():
        entries = motion_block["expected_contact_points"]
        assert isinstance(entries, list), (
            f"{motion_id}.expected_contact_points must be list"
        )
        for entry in entries:
            assert isinstance(entry, dict), (
                f"{motion_id} entry must be dict, got {type(entry).__name__}"
            )
            name = entry["name"]
            assert name in _VALID_CONTACT_POINTS, (
                f"{motion_id}: invalid contact point name {name!r} "
                f"(must be one of {_VALID_CONTACT_POINTS})"
            )


def test_motion_entries_kind_field_present() -> None:
    raw = _load_raw()
    seen_kinds: dict[str, str] = {}
    for motion_id, motion_block in raw["motions"].items():
        for entry in motion_block["expected_contact_points"]:
            assert "kind" in entry, (
                f"{motion_id}: entry missing 'kind' field — {entry}"
            )
            kind = entry["kind"]
            assert kind in _VALID_KINDS, (
                f"{motion_id}: invalid kind {kind!r} (must be one of {_VALID_KINDS})"
            )
            seen_kinds[entry["name"]] = kind

    # Plan 08-00 docs/contract.md §9.0.7 정합 검증
    assert seen_kinds.get("left_inner_thigh") == "segment"
    assert seen_kinds.get("right_inner_thigh") == "segment"
    assert seen_kinds.get("hip") == "region_proxy"
    assert seen_kinds.get("left_hand") == "keypoint"
    assert seen_kinds.get("right_hand") == "keypoint"


def test_default_entry_present() -> None:
    raw = _load_raw()
    assert raw["default"]["expected_contact_points"] == []


def test_yaml_uses_safe_load_path() -> None:
    """yaml.safe_load 호환성 검증 — !!python/ 태그 영구 차단 (RCE 방지)."""
    text = _YAML_PATH.read_text(encoding="utf-8")
    assert "!!python/" not in text, (
        "contact_points.yaml must be safe_load-compatible — !!python/ tags forbidden"
    )
