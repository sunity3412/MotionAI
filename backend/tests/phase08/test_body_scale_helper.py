"""median_torso_length helper test.

REVIEWS Cycle 1 R2 — BodyNormalizationProfile.torso_scale 사용 영구 금지 drift defense.

per Plan 08-00 Task 1 <behavior>.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from sunity_shared.analysis import body_scale
from sunity_shared.analysis.body_scale import median_torso_length

from .fixtures._factory import (
    make_keypoint2d,
    make_keypoint3d,
    make_keypoint3d_aligned,
    make_pose_frame,
)


def test_median_torso_length_image_2d(synthetic_pose_frames) -> None:
    """synthetic frames (shoulder y=0.3, hip y=0.6) → median = ~0.3."""
    result = median_torso_length(synthetic_pose_frames, space="image_2d")
    assert result is not None
    assert result == pytest.approx(0.3, abs=1e-2)


def test_median_torso_length_pole_aligned(synthetic_pose_frames) -> None:
    """pole_aligned 좌표 — shoulder mid y=0.0, hip mid y=-0.3 → distance = 0.3."""
    result = median_torso_length(synthetic_pose_frames, space="pole_aligned")
    assert result is not None
    assert result == pytest.approx(0.3, abs=1e-2)


def test_median_torso_length_world_3d(synthetic_pose_frames) -> None:
    """world_3d 좌표 — shoulder y=1.5, hip y=1.2 → distance = 0.3."""
    result = median_torso_length(synthetic_pose_frames, space="world_3d")
    assert result is not None
    assert result == pytest.approx(0.3, abs=1e-2)


def test_median_torso_length_missing_keypoints_returns_none() -> None:
    """60 frame 중 55 frame 가 missing keypoint → valid frame < 5 → None."""
    frames = []
    # 5 valid frames 미만 강제 — 60 frame 중 4 frame 만 valid.
    for i in range(60):
        if i < 4:
            kp2d = {
                "left_shoulder": make_keypoint2d(0.45, 0.3),
                "right_shoulder": make_keypoint2d(0.55, 0.3),
                "left_hip": make_keypoint2d(0.46, 0.6),
                "right_hip": make_keypoint2d(0.54, 0.6),
            }
        else:
            # left_hip missing — frame skip 강제.
            kp2d = {
                "left_shoulder": make_keypoint2d(0.45, 0.3),
                "right_shoulder": make_keypoint2d(0.55, 0.3),
                "right_hip": make_keypoint2d(0.54, 0.6),
            }
        frames.append(
            make_pose_frame(
                frame_index=i,
                timestamp_ms=i * 33,
                keypoints_2d=kp2d,
                reliability="medium",
            )
        )
    result = median_torso_length(frames, space="image_2d")
    assert result is None


def test_median_torso_length_invalid_space_raises() -> None:
    """space enum 검증 — invalid space → ValueError."""
    with pytest.raises(ValueError):
        median_torso_length([], space="invalid_space")  # type: ignore[arg-type]


def _strip_comments_and_docstrings(source: str) -> str:
    """AST 기반 — module/class/function docstring + 한 줄 주석 제거.

    drift defense test 가 docstring 의 정당한 설명 ('BodyNormalizationProfile 사용
    금지' 같은) 까지 차단하면 false positive — 본 helper 가 실행 가능한 코드만 추출.
    """
    import ast
    import io
    import tokenize

    # 한 줄 주석 (# ...) 제거.
    out_tokens: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            continue
        out_tokens.append(tok.string if tok.type != tokenize.NL else "\n")
    no_comments = tokenize.untokenize(
        (t.type, t.string)
        for t in tokenize.generate_tokens(io.StringIO(source).readline)
        if t.type != tokenize.COMMENT
    )

    # AST 의 docstring 제거 — module / FunctionDef / AsyncFunctionDef / ClassDef.
    tree = ast.parse(no_comments)
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body.pop(0)
    return ast.unparse(tree)


def test_torso_scale_is_not_used_as_denominator() -> None:
    """body_scale.py 의 **실행 코드** 안 BodyNormalizationProfile 영구 차단 (R2 drift defense).

    docstring 의 정당한 설명 ('사용 금지' 안내) 은 통과 — AST 로 docstring 제거 후
    실행 코드만 검증. median_torso_length 가 observed length 만 산출 강제.
    """
    src = inspect.getsource(body_scale)
    code_only = _strip_comments_and_docstrings(src)
    assert "BodyNormalizationProfile" not in code_only, (
        "body_scale.py executable code must not reference BodyNormalizationProfile "
        "(REVIEWS R2 drift defense — torso_scale is a self-ratio, not observed length)"
    )
    # body_normalization import 도 영구 차단.
    assert "body_normalization" not in code_only, (
        "body_scale.py executable code must not import body_normalization "
        "(REVIEWS R2 drift defense)"
    )


def test_body_scale_source_imports_clean() -> None:
    """AST import 검증 — body_normalization module import 영구 차단."""
    import ast

    src = Path(body_scale.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "body_normalization", (
                f"body_scale.py imports body_normalization (line {node.lineno}) "
                "— REVIEWS R2 drift defense"
            )
            if node.module:
                assert "body_normalization" not in node.module, (
                    f"body_scale.py imports {node.module} (line {node.lineno}) "
                    "— REVIEWS R2 drift defense"
                )
            for alias in node.names:
                assert alias.name != "BodyNormalizationProfile", (
                    f"body_scale.py imports BodyNormalizationProfile "
                    f"(line {node.lineno}) — REVIEWS R2 drift defense"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert "body_normalization" not in alias.name, (
                    f"body_scale.py imports {alias.name} (line {node.lineno}) "
                    "— REVIEWS R2 drift defense"
                )
