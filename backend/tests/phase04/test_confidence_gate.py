"""Phase 4 Wave 0 — POSE-03-a: confidence gate (occlusion target identifier).

identify_occlusion_targets(keypoint_confidence, scene_flags, phase_boundaries,
                           threshold=0.3) → np.ndarray bool mask (T, 17)

D-04 (a)(b)(c)(d) 4가지 트리거 결합:
  (a) per-frame per-joint confidence < threshold
  (b) scene_findings.occlusion_severe=True 영역
  (c) phase 경계 부근 신호
  (d) joint cluster 단위 가림 (optional)

Wave 1 (04-01 Task 1) 가 synthesis/interfaces.py:identify_occlusion_targets 박제.
Wave 0 시점에서는 ImportError → pytest.skip (collect error 방지).
"""

from __future__ import annotations

import numpy as np
import pytest


def _load_identifier():
    """Wave 1 박제 위치에서 lazy import — Wave 0 부재 시 skip."""
    try:
        from sunity_shared.analysis.synthesis.interfaces import (
            identify_occlusion_targets,
        )
    except ImportError:
        pytest.skip(
            "synthesis.interfaces.identify_occlusion_targets — Wave 1 (04-01) 미박제"
        )
    return identify_occlusion_targets


def test_synthesis_mask_low_confidence(
    conf_seq_30f: np.ndarray,
    low_conf_seq: np.ndarray,
    scene_findings_clean: dict,
) -> None:
    """conf < 0.3 frame/joint → mask True."""
    identify_occlusion_targets = _load_identifier()

    mask = identify_occlusion_targets(
        low_conf_seq,
        scene_findings_clean,
        [],
        threshold=0.3,
    )

    # 0.1 < 0.3 영역(10~20, 3~7) 전부 True 여야 함.
    assert mask.shape == low_conf_seq.shape
    assert mask.dtype == bool
    assert mask[10:20, 3:7].all()


def test_synthesis_mask_all_high(
    conf_seq_30f: np.ndarray,
    scene_findings_clean: dict,
) -> None:
    """모든 confidence >= 0.7 → mask 전부 False (임계 0.3 기준)."""
    identify_occlusion_targets = _load_identifier()

    mask = identify_occlusion_targets(
        conf_seq_30f,
        scene_findings_clean,
        [],
        threshold=0.3,
    )

    assert mask.shape == conf_seq_30f.shape
    assert mask.dtype == bool
    assert not mask.any()


def test_synthesis_mask_scene_occlusion(
    conf_seq_30f: np.ndarray,
    scene_findings_occlusion: dict,
) -> None:
    """scene_findings.occlusion_severe=True → 영향 frame mask True 1개 이상."""
    identify_occlusion_targets = _load_identifier()

    mask = identify_occlusion_targets(
        conf_seq_30f,
        scene_findings_occlusion,
        [],
        threshold=0.3,
    )

    # confidence 자체는 모두 0.7 이상이라 frame 단독 신호로는 false.
    # scene occlusion_severe=True 가 mask 신호를 끌어올렸는지 검증 — 1개 이상 True.
    assert mask.shape == conf_seq_30f.shape
    assert mask.dtype == bool
    assert mask.any(), (
        "scene_findings.occlusion_severe=True 신호가 mask 에 반영되지 않음 — POSE-03-a D-04(b)"
    )
