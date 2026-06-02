"""Plan 01-22 Task 1 — RTMW 3D path stub 단위 테스트.

D-18 옵션 A (RTMW3DPoseEngine) / 옵션 B (RTMWLifterPoseEngine) 두 어댑터의:
  1. three_d_path_decision.md 비교 문서 존재 + 핵심 섹션 박제.
  2. PoseEngine Protocol 만족 (estimate(frames, pole_axis) 시그니처).
  3. module-level rtmlib / mmpose / mmcv / torch / mediapipe import 0건 (H-2 박제).
  4. belle 결정 전 두 엔진 모두 estimate() 호출 시 NotImplementedError.

Task 2 belle 응답 ('option_a' 또는 'option_b') 후 선택된 1개 어댑터만 실 구현
→ test_rtmw_3d_path_selected.py 에서 z 채움 + swap_ratio 0 + Protocol contract
검증 (별 plan 22 Task 2 책임). 본 모듈은 Task 1 stub-level 게이트.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

RTMW_DIR = (
    REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "pose_engines"
    / "rtmw"
)
RTMW3D_PATH = RTMW_DIR / "rtmw3d_engine.py"
LIFTER_PATH = RTMW_DIR / "lifter_pipeline.py"
DECISION_DOC_PATH = RTMW_DIR / "three_d_path_decision.md"
MANIFEST_PATH = RTMW_DIR / "weights_manifest.json"


# ── Test 1: three_d_path_decision.md 존재 + 핵심 섹션 ────────────────────

def test_three_d_path_decision_doc_exists():
    """three_d_path_decision.md 존재 + 필수 섹션 (§1~§6 박제 항목 포함).

    Plan 22 acceptance: §5 belle 결정 + §6 격리 대상 검증 항목 포함 +
    grep -c '^## ' >= 6.
    """
    assert DECISION_DOC_PATH.exists(), f"three_d_path_decision.md 없음: {DECISION_DOC_PATH}"

    source = DECISION_DOC_PATH.read_text(encoding="utf-8")

    # Markdown level-2 헤더 ≥ 6 (## 1, ## 2, ## 3, ## 4, ## 5, ## 6 박제).
    header_lines = [line for line in source.splitlines() if line.startswith("## ")]
    assert len(header_lines) >= 6, (
        f"three_d_path_decision.md 의 ## 헤더 ≥ 6 필요, "
        f"got {len(header_lines)}: {header_lines}"
    )

    # 핵심 섹션 = §5 belle 결정 + §6 격리 대상.
    assert "## 5. belle 결정" in source, (
        "three_d_path_decision.md 에 '## 5. belle 결정' 섹션 박제 필요 "
        "(Task 2 checkpoint 응답 박제 위치)"
    )
    assert "## 6. 선택 후 격리 대상" in source, (
        "three_d_path_decision.md 에 '## 6. 선택 후 격리 대상' 섹션 박제 필요 "
        "(plan 24 입력)"
    )

    # 핵심 키워드 박제 (Plan 22 acceptance).
    for keyword in ("RTMW3D", "MotionBERT", "MIT", "Pose2Sim", "single-camera-first-multi-view-last"):
        assert keyword in source, (
            f"three_d_path_decision.md 에 키워드 {keyword!r} 박제 필요 "
            f"(옵션 A/B 비교 + Phase 4 정합 + 라이선스 명시)"
        )


# ── Test 2: RTMW3DPoseEngine PoseEngine Protocol 만족 ────────────────────

def test_rtmw3d_engine_implements_protocol():
    """RTMW3DPoseEngine 이 PoseEngine Protocol (estimate(frames, pole_axis))을 만족한다.

    Plan 22 Task 1: factory + estimate 시그니처 박제 필요. 호출 시 NotImplementedError
    는 별 테스트 (test_both_engines_unselected_raises_not_implemented) 에서 검증.
    """
    from sunity_shared.analysis.pose_engines import RTMW3DPoseEngine

    # 클래스 자체에서 estimate 메서드 존재 + 시그니처 검증 (인스턴스화 없이).
    assert hasattr(RTMW3DPoseEngine, "estimate"), "RTMW3DPoseEngine.estimate 없음"
    assert callable(RTMW3DPoseEngine.estimate), "estimate 가 callable 이어야 함"

    sig = inspect.signature(RTMW3DPoseEngine.estimate)
    params = list(sig.parameters.keys())
    assert "frames" in params, f"estimate 에 'frames' 파라미터 없음: {params}"
    assert "pole_axis" in params, f"estimate 에 'pole_axis' 파라미터 없음: {params}"

    # DI factory 존재 — 단위 테스트 진입점 (Plan 21 RTMWPoseEngine 패턴 정합).
    assert hasattr(RTMW3DPoseEngine, "create_with_inferencer"), (
        "RTMW3DPoseEngine.create_with_inferencer DI factory 박제 필요"
    )


# ── Test 3: RTMWLifterPoseEngine PoseEngine Protocol 만족 ────────────────

def test_rtmw_lifter_engine_implements_protocol():
    """RTMWLifterPoseEngine 이 PoseEngine Protocol 을 만족한다.

    옵션 B 어댑터 stub — RTMW 2D + MotionBERT lifter 결합.
    """
    from sunity_shared.analysis.pose_engines import RTMWLifterPoseEngine

    assert hasattr(RTMWLifterPoseEngine, "estimate"), "RTMWLifterPoseEngine.estimate 없음"
    assert callable(RTMWLifterPoseEngine.estimate), "estimate 가 callable 이어야 함"

    sig = inspect.signature(RTMWLifterPoseEngine.estimate)
    params = list(sig.parameters.keys())
    assert "frames" in params, f"estimate 에 'frames' 파라미터 없음: {params}"
    assert "pole_axis" in params, f"estimate 에 'pole_axis' 파라미터 없음: {params}"

    # DI factory 존재 — mediapipe_lifter_engine.py create_with_engines 패턴 정합.
    assert hasattr(RTMWLifterPoseEngine, "create_with_engines"), (
        "RTMWLifterPoseEngine.create_with_engines DI factory 박제 필요"
    )


# ── Test 4: module-level 무거운 import 0건 (H-2 박제) ────────────────────

def test_both_engines_no_module_level_heavy_import():
    """rtmw3d_engine.py + lifter_pipeline.py module-level import 검사.

    H-2 박제: rtmlib / mmpose / mmcv / torch / mediapipe / ultralytics 의 module-level
    import 0건. tree.body (module-level 직접 자식) 만 검사 — 함수 내 lazy import 는
    허용 (Plan 21 RTMWPoseEngine 의 test_rtmw_engine_module_level_no_rtmlib_import
    패턴 정합).
    """
    forbidden_prefixes = ("rtmlib", "mmpose", "mmcv", "torch", "mediapipe", "ultralytics")

    for path in (RTMW3D_PATH, LIFTER_PATH):
        assert path.exists(), f"{path.name} 없음: {path}"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.lower()
                    for forbidden in forbidden_prefixes:
                        assert forbidden not in mod, (
                            f"{path.name} module-level import 에 {forbidden!r} 금지 "
                            f"(H-2 박제): {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.lower()
                    for forbidden in forbidden_prefixes:
                        assert forbidden not in mod, (
                            f"{path.name} module-level import 에 {forbidden!r} 금지 "
                            f"(H-2 박제): {node.module}"
                        )


# ── Test 5: 두 엔진 모두 estimate() 호출 시 NotImplementedError ──────────

def test_both_engines_unselected_raises_not_implemented():
    """belle 결정 전 — 두 어댑터 모두 estimate() 호출 시 NotImplementedError.

    Task 1 stub-level 게이트: 둘 다 옵션 미선택 상태이므로 estimate() 실 구현 없음.
    Task 2 belle 응답 ('option_a' 또는 'option_b') 후 선택된 1개만 NotImplementedError
    제거 + 실 구현 (test_rtmw_3d_path_selected.py 에서 별도 검증).

    DI factory 로 인스턴스화 시도 — RTMW3DPoseEngine 은 RTMW3D production_eligible
    가중치 부재로 LicenseViolationError 가 먼저 발생할 수 있음 (현재 manifest 박제 상태).
    이 경우도 옵션 A 미선택 상태와 정합 — manifest gate 통과 시 NotImplementedError 가
    estimate() 에서 발생함을 보장하기 위해 factory 의 manifest gate 를 우회한 instance
    직접 구성 path 로 검증.
    """
    from sunity_shared.analysis.pose_engines import (
        RTMW3DPoseEngine,
        RTMWLifterPoseEngine,
    )
    from sunity_shared.analysis.pose_frame import PoleAxis

    pole_axis = PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )
    frames = np.zeros((2, 64, 64, 3), dtype=np.uint8)

    # RTMW3DPoseEngine — factory manifest gate 통과 위해 mock instance 구성
    # (manifest 에 production_eligible=true 인 RTMW3D entry 없으면 LicenseViolationError
    # 도 정합 — 옵션 A 미선택 상태). 본 테스트는 estimate() 의 NotImplementedError 만 검증.
    rtmw3d_instance = RTMW3DPoseEngine.__new__(RTMW3DPoseEngine)
    rtmw3d_instance._inferencer = MagicMock()
    rtmw3d_instance._selected_weight = {"name": "rtmw3d-stub"}
    rtmw3d_instance._target_fps = 30
    with pytest.raises(NotImplementedError) as exc_info_a:
        rtmw3d_instance.estimate(frames=frames, pole_axis=pole_axis)
    assert "옵션 A" in str(exc_info_a.value) or "option_a" in str(exc_info_a.value), (
        f"RTMW3DPoseEngine.estimate NotImplementedError 메시지에 옵션 A 명시 필요: "
        f"{exc_info_a.value}"
    )

    # RTMWLifterPoseEngine — create_with_engines factory 통과 후 estimate 호출.
    mock_rtmw = MagicMock()
    mock_lifter = MagicMock()
    lifter_engine = RTMWLifterPoseEngine.create_with_engines(
        rtmw_engine=mock_rtmw,
        lifter=mock_lifter,
    )
    with pytest.raises(NotImplementedError) as exc_info_b:
        lifter_engine.estimate(frames=frames, pole_axis=pole_axis)
    assert "옵션 B" in str(exc_info_b.value) or "option_b" in str(exc_info_b.value), (
        f"RTMWLifterPoseEngine.estimate NotImplementedError 메시지에 옵션 B 명시 필요: "
        f"{exc_info_b.value}"
    )
