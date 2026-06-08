"""WR-05 regression — KINEMATIC_TREE_EDGES 와 _ref_segment_ratio 의 정합 강제.

박제 정신 (WR-05 / 2026-06-08 review):
  - 13 edge tree 중 하나라도 _ref_segment_ratio 의 if-chain 에 빠지면 production
    에서 KeyError → caller broad except → server_error 로 silently 매핑 → 모든
    사용자에게 분석 실패. dev-time fail-fast 가 더 안전.
  - body_normalizer.py import 자체가 assert 로 정합 강제 — 본 테스트는 그 assert
    가 발동 가능한 상태인지 검증 (양방향 set 일치).
"""

from __future__ import annotations


def test_all_kinematic_tree_edges_have_ref_segment_ratio_mapping() -> None:
    """WR-05 — 모든 tree edge 가 _KNOWN_REF_SEGMENT_RATIO_EDGES 에 포함."""
    from sunity_shared.analysis.body_normalizer import (
        KINEMATIC_TREE_EDGES,
        _KNOWN_REF_SEGMENT_RATIO_EDGES,
    )
    missing = set(KINEMATIC_TREE_EDGES) - _KNOWN_REF_SEGMENT_RATIO_EDGES
    assert not missing, (
        f"KINEMATIC_TREE_EDGES 에 _ref_segment_ratio 매핑 없는 edge: {sorted(missing)}. "
        f"_ref_segment_ratio 의 if 분기에 매핑 추가 + _KNOWN_REF_SEGMENT_RATIO_EDGES 도 갱신."
    )


def test_ref_segment_ratio_known_set_has_no_dead_mappings() -> None:
    """WR-05 — _KNOWN_REF_SEGMENT_RATIO_EDGES 에 KINEMATIC_TREE_EDGES 부재 dead mapping 없음."""
    from sunity_shared.analysis.body_normalizer import (
        KINEMATIC_TREE_EDGES,
        _KNOWN_REF_SEGMENT_RATIO_EDGES,
    )
    dead = _KNOWN_REF_SEGMENT_RATIO_EDGES - set(KINEMATIC_TREE_EDGES)
    assert not dead, (
        f"_KNOWN_REF_SEGMENT_RATIO_EDGES 에 dead mapping: {sorted(dead)}. "
        f"_KNOWN_REF_SEGMENT_RATIO_EDGES 에서 제거 (tree 에 없는 edge)."
    )


def test_ref_segment_ratio_does_not_raise_for_any_tree_edge() -> None:
    """WR-05 — 13 tree edge 모두 _ref_segment_ratio 에서 정상 float 반환."""
    import math

    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.body_normalizer import (
        KINEMATIC_TREE_EDGES,
        _ref_segment_ratio,
    )

    profile = BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.9,
        warnings=[],
    )
    for parent, child in KINEMATIC_TREE_EDGES:
        v = _ref_segment_ratio(parent, child, profile, apply_shoulder_hip_ratio=True)
        assert isinstance(v, float), f"edge ({parent}, {child}) 반환 타입 다름"
        assert math.isfinite(v) and v > 0, (
            f"edge ({parent}, {child}) ratio 비양수/non-finite: {v}"
        )
