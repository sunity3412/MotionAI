"""Phase 4 Wave 0 — POSE-03-c: merge_with_temporal 4-status branching.

merge_with_temporal(primary_joints, primary_conf, synth_result, synthesis_mask)
  → tuple[ndarray, ndarray]

SynthesisResult.status 4 case 분기 (R2 fix — None/zeros sentinel 분기 금지):
  - "applied"   → synth_conf > primary_conf 인 frame/joint 만 교체
  - "partial"   → applied 와 동일 로직, 부분 영역만 교체
  - "skipped"   → primary 그대로 반환 (synth_conf <= primary_conf 시도 0)
  - "failed"    → primary 그대로 반환 (joints/conf 가 None 이므로 merge 시도 없음)

temporal.py 재사용 — 동일 패키지의 temporal_fill 박제가 존재해야 함 (POSE-03-c
"temporal.py 존재 확인 테스트").

Wave 0 시점에서 merge_with_temporal 미박제 → ImportError → pytest.skip.
"""

from __future__ import annotations

import numpy as np
import pytest


def _load_merge_and_result():
    """Wave 1 박제 후 merge_with_temporal + SynthesisResult."""
    try:
        from sunity_shared.analysis.synthesis.interfaces import (
            SynthesisResult,
            merge_with_temporal,
        )
    except ImportError:
        pytest.skip(
            "synthesis.interfaces.{SynthesisResult, merge_with_temporal} "
            "— Wave 1 (04-01) 미박제"
        )
    return merge_with_temporal, SynthesisResult


def test_temporal_module_import() -> None:
    """POSE-03-c: temporal.py 재사용 — 모듈 import 가능 확인."""
    # Wave 0 시점부터 GREEN — sunity_shared.analysis.temporal 은 W7 이전부터 박제.
    from sunity_shared.analysis import temporal  # noqa: F401

    assert hasattr(temporal, "temporal_fill"), (
        "temporal.temporal_fill 미존재 — POSE-03-c 재사용 대상 함수 부재"
    )


def test_merge_higher_confidence_wins(
    joint_seq_30f: np.ndarray,
    conf_seq_30f: np.ndarray,
) -> None:
    """SynthesisResult(status='applied') + synth_conf > primary_conf 인 frame/joint
    만 교체된다."""
    merge_with_temporal, SynthesisResult = _load_merge_and_result()

    primary_joints = joint_seq_30f.copy()
    primary_conf = conf_seq_30f.copy()

    # synthesis 가 frame 5, joint 0 만 더 높은 confidence 로 추정.
    synth_joints = primary_joints.copy()
    synth_joints[5, 0] = np.array([0.9, 0.9, 0.9], dtype=np.float32)
    synth_conf = primary_conf.copy()
    synth_conf[:] = 0.0  # 기본은 낮춰서 합성이 안 이김.
    synth_conf[5, 0] = 0.95  # 단일 위치만 primary 보다 높음.

    synthesis_mask = np.zeros_like(primary_conf, dtype=bool)
    synthesis_mask[5, 0] = True

    result = SynthesisResult(
        status="applied",
        joints=synth_joints,
        confidence=synth_conf,
        warnings=(),
    )

    merged_joints, merged_conf = merge_with_temporal(
        primary_joints, primary_conf, result, synthesis_mask
    )

    # frame 5, joint 0 만 교체.
    assert np.allclose(merged_joints[5, 0], synth_joints[5, 0])
    # 다른 위치는 primary 유지.
    assert np.allclose(merged_joints[0, 0], primary_joints[0, 0])


def test_merge_primary_unchanged_when_synth_lower(
    joint_seq_30f: np.ndarray,
    conf_seq_30f: np.ndarray,
) -> None:
    """SynthesisResult(status='skipped') 또는 synth_conf <= primary_conf 시
    primary 유지."""
    merge_with_temporal, SynthesisResult = _load_merge_and_result()

    primary_joints = joint_seq_30f.copy()
    primary_conf = conf_seq_30f.copy()

    synthesis_mask = np.zeros_like(primary_conf, dtype=bool)
    result = SynthesisResult(
        status="skipped",
        joints=None,
        confidence=None,
        warnings=(),
    )

    merged_joints, merged_conf = merge_with_temporal(
        primary_joints, primary_conf, result, synthesis_mask
    )

    assert np.allclose(merged_joints, primary_joints)
    assert np.allclose(merged_conf, primary_conf)


def test_merge_status_failed_skips_merge(
    joint_seq_30f: np.ndarray,
    conf_seq_30f: np.ndarray,
) -> None:
    """SynthesisResult(status='failed') 는 primary 를 전혀 mutate 하지 않는다.

    joints/confidence 가 None 이므로 merge 시도 자체가 없어야 함 (R2 fix —
    None 분기 + status='failed' 분기 둘 다 hit).
    """
    merge_with_temporal, SynthesisResult = _load_merge_and_result()

    primary_joints = joint_seq_30f.copy()
    primary_conf = conf_seq_30f.copy()

    synthesis_mask = np.ones_like(primary_conf, dtype=bool)  # 전체 mask True 라도
    result = SynthesisResult(
        status="failed",
        joints=None,
        confidence=None,
        warnings=("ai_synthesis_failed",),
    )

    merged_joints, merged_conf = merge_with_temporal(
        primary_joints, primary_conf, result, synthesis_mask
    )

    # joints / conf 가 None 인데도 primary 가 변형되면 안 됨.
    assert np.allclose(merged_joints, primary_joints)
    assert np.allclose(merged_conf, primary_conf)


def test_merge_status_partial_merges_subset(
    joint_seq_30f: np.ndarray,
    conf_seq_30f: np.ndarray,
) -> None:
    """SynthesisResult(status='partial') 는 합성 confidence 가 더 높은 영역만
    교체. 나머지 primary 유지."""
    merge_with_temporal, SynthesisResult = _load_merge_and_result()

    primary_joints = joint_seq_30f.copy()
    primary_conf = conf_seq_30f.copy()

    # synthesis 가 frame 10~15, joint 5 만 더 높은 confidence.
    synth_joints = primary_joints.copy()
    synth_joints[10:15, 5] = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    synth_conf = primary_conf.copy()
    synth_conf[:] = 0.0
    synth_conf[10:15, 5] = 0.99

    synthesis_mask = np.zeros_like(primary_conf, dtype=bool)
    synthesis_mask[10:15, 5] = True

    result = SynthesisResult(
        status="partial",
        joints=synth_joints,
        confidence=synth_conf,
        warnings=("ai_synthesis_partial",),
    )

    merged_joints, merged_conf = merge_with_temporal(
        primary_joints, primary_conf, result, synthesis_mask
    )

    # 합성 영역은 교체.
    assert np.allclose(merged_joints[10:15, 5], synth_joints[10:15, 5])
    # 합성 영역 밖은 primary 유지.
    assert np.allclose(merged_joints[0, 0], primary_joints[0, 0])
    assert np.allclose(merged_joints[20, 5], primary_joints[20, 5])
