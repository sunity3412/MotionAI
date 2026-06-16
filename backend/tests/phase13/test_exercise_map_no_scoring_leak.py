"""D-05 비유입 게이트 — exercise_map.py 소스에 채점 토큰 0회.

painAreas 는 보완운동 매핑 출력에만 흐르고 어떤 점수/dimension 경로에도 닿지
않는다. exercise_map.py 본체가 dimension_scores / absolute_dimension_scores /
build_dimension_explanation 토큰을 참조하지 않음을 grep (주석 제외) 으로 강제.

precedent: backend/tests/phase09/test_force_pattern_no_severity_use.py.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = (
    _REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "exercise_map.py"
)

_FORBIDDEN_TOKENS = (
    "dimension_scores",
    "absolute_dimension_scores",
    "build_dimension_explanation",
)


def _non_comment_source() -> str:
    lines = _MODULE_PATH.read_text(encoding="utf-8").splitlines()
    # 주석 줄 (선두 #) 제외 — docstring 내부 멘션은 본 게이트 scope 가 아니나
    # 보수적으로 코드 라인만 검사.
    return "\n".join(ln for ln in lines if not ln.lstrip().startswith("#"))


def test_exercise_map_does_not_reference_scoring_tokens() -> None:
    src = _non_comment_source()
    for token in _FORBIDDEN_TOKENS:
        assert token not in src, (
            f"D-05 위반 — exercise_map.py 가 채점 토큰 {token!r} 참조"
        )
