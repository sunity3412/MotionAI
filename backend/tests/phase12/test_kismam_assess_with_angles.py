"""Phase 12 Wave 0A R4 (Codex 직접 리뷰 2026-06-10) — kismam.assess() 3 call site wiring 검증.

기존: pipeline/app.py 의 3 call site (mode1 / mode3_progress / mode3_first) 모두
kwarg 없이 kismam.assess(deviation) 호출 → JointAssessment.current_angle/target_angle
항상 None → JointScore 가 currentAngle/targetAngle 비어 내려감 → result.tsx 시뮬 fallback.

본 test 가 R4 fix 회귀 차단:
  - 3 call site 모두 user_angles + reference_angles + target_source kwarg 박제 검증
    (AST 기반, H1 iter-4 정합 — grep 영구 폐기).
  - kismam.assess() body 의 mode3 first non-extension joint → 'unavailable' 분기.
  - _angles_to_mean_dict NaN 처리.

cite: 12-00-PLAN.md Task T2 + Task T5.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np
import pytest

from sunity_shared.analysis import kismam
from sunity_shared.analysis.skeleton import JOINT_KEYS


# pipeline/app.py 위치 — repo root 기준.
_PIPELINE_APP_PY = (
    Path(__file__).resolve().parents[2] / "functions" / "pipeline" / "app.py"
)

# functions/pipeline/ 을 sys.path 에 추가 — `import app` 가능 (기존 phase test 패턴 mirror).
_PIPELINE_DIR = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))


def test_kismam_assess_ast_all_calls_have_user_angles():
    """H1 iter-4 정합 — AST 기반 검증 (grep multiline/주석 false-positive 차단).

    Python stdlib `ast` 로 pipeline/app.py 파싱 → 모든 kismam.assess() Call 노드에서
    user_angles + reference_angles + target_source 3 kwarg 박제 검증.
    """
    src = _PIPELINE_APP_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    call_sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # kismam.assess(...) 만 매칭 (Attribute → Name 'kismam', attr='assess').
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "assess":
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "kismam":
            continue
        call_sites.append(node)

    assert len(call_sites) >= 3, (
        f"kismam.assess() call site 3 미만 — pipeline 구조 변경 감지 "
        f"(found {len(call_sites)}). Phase 12 R4 wiring 회귀 가능."
    )

    required_kwargs = {"user_angles", "reference_angles", "target_source"}
    for i, node in enumerate(call_sites):
        kwarg_names = {kw.arg for kw in node.keywords if kw.arg is not None}
        missing = required_kwargs - kwarg_names
        assert not missing, (
            f"kismam.assess() call site #{i} (line {node.lineno}) missing kwargs: "
            f"{sorted(missing)}. Phase 12 R4 BLOCKER — wiring 회귀."
        )


def test_pipeline_call_sites_target_source_values_valid():
    """3 call site 의 target_source 값이 4 enum 중 하나 (R4 정합)."""
    src = _PIPELINE_APP_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    allowed = {
        "reference_motion",
        "previous_analysis",
        "extension_requirement",
        "unavailable",
    }
    found_values: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "assess":
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id != "kismam":
            continue
        for kw in node.keywords:
            if kw.arg == "target_source":
                # ast.Constant (Python 3.8+).
                assert isinstance(kw.value, ast.Constant), (
                    f"target_source must be string literal at line {node.lineno}"
                )
                assert kw.value.value in allowed, (
                    f"target_source={kw.value.value!r} at line {node.lineno} "
                    f"not in {sorted(allowed)}"
                )
                found_values.append(kw.value.value)
    # 3 call site 중 최소 mode1/mode3_progress/mode3_first 1개씩 (3 enum 박제).
    assert {"reference_motion", "previous_analysis", "extension_requirement"} <= set(
        found_values
    ), (
        f"3 mode target_source 모두 박제 안 됨. found: {found_values}. "
        f"mode1 = reference_motion, mode3_progress = previous_analysis, "
        f"mode3_first = extension_requirement."
    )


def test_kismam_assess_mode3_first_non_extension_joint_unavailable():
    """mode3 first 의 non-extension joint → target_source='unavailable' 자동 분기.

    extension_requirement caller (reference_angles 가 extension 관절만 포함) 시,
    reference_angles 에 key 없는 joint = expects_extension(joint) == False
    → JointAssessment.target_source='unavailable', target_angle=None.
    """
    n = len(JOINT_KEYS)
    deviation = np.zeros(n, dtype=float)
    user_means = {key: 150.0 for key in JOINT_KEYS}
    # extension 필요 관절만 reference_angles 에 박제 (left_elbow, right_knee 2개만).
    ext_targets = {"left_elbow": 180.0, "right_knee": 180.0}
    result = kismam.assess(
        deviation,
        user_angles=user_means,
        reference_angles=ext_targets,
        target_source="extension_requirement",
    )
    # extension-required joint
    elbow_left = next(a for a in result if a.key == "left_elbow")
    assert elbow_left.target_source == "extension_requirement"
    assert elbow_left.target_angle == 180.0
    # non-extension joint (예: left_shoulder)
    shoulder_left = next(a for a in result if a.key == "left_shoulder")
    assert shoulder_left.target_source == "unavailable"
    assert shoulder_left.target_angle is None


def test_kismam_assess_mode1_target_source_reference_motion():
    """mode1 caller: 모든 joint 가 reference_angles 박제 → target_source='reference_motion'."""
    n = len(JOINT_KEYS)
    deviation = np.zeros(n, dtype=float)
    user_means = {key: 150.0 for key in JOINT_KEYS}
    ref_means = {key: 170.0 for key in JOINT_KEYS}
    result = kismam.assess(
        deviation,
        user_angles=user_means,
        reference_angles=ref_means,
        target_source="reference_motion",
    )
    for a in result:
        assert a.target_source == "reference_motion"
        assert a.target_angle == 170.0
        assert a.current_angle == 150.0


def test_kismam_assess_target_source_none_when_not_passed():
    """legacy caller (kwarg 없음) → target_source 모두 None (이전 빌드 호환)."""
    n = len(JOINT_KEYS)
    deviation = np.zeros(n, dtype=float)
    result = kismam.assess(deviation)
    for a in result:
        assert a.target_source is None


def test_angles_to_mean_dict_handles_nan():
    """_angles_to_mean_dict — NaN 포함 frame 시 nanmean 박제."""
    from app import _angles_to_mean_dict  # noqa: PLC0415

    n_frames = 3
    n_joints = len(JOINT_KEYS)
    angles = np.full((n_frames, n_joints), 100.0, dtype=float)
    angles[1, 0] = np.nan  # left_elbow frame 1 = NaN
    result = _angles_to_mean_dict(angles, JOINT_KEYS)
    # NaN 무시 (frame 0, 2 의 100.0 평균 = 100.0).
    assert result[JOINT_KEYS[0]] == pytest.approx(100.0)


def test_angles_to_mean_dict_empty_returns_empty():
    """빈 입력 → 빈 dict."""
    from app import _angles_to_mean_dict  # noqa: PLC0415

    assert _angles_to_mean_dict(None, JOINT_KEYS) == {}
    assert _angles_to_mean_dict(np.empty((0, len(JOINT_KEYS))), JOINT_KEYS) == {}


def test_angles_to_mean_dict_all_nan_column_skipped():
    """모든 frame 에서 NaN 인 joint → 결과 dict 에서 skip."""
    from app import _angles_to_mean_dict  # noqa: PLC0415

    n_frames = 3
    n_joints = len(JOINT_KEYS)
    angles = np.full((n_frames, n_joints), 100.0, dtype=float)
    angles[:, 0] = np.nan  # left_elbow 모든 frame NaN
    result = _angles_to_mean_dict(angles, JOINT_KEYS)
    assert JOINT_KEYS[0] not in result
    # 나머지 joint 는 박제.
    for key in JOINT_KEYS[1:]:
        assert result[key] == pytest.approx(100.0)
