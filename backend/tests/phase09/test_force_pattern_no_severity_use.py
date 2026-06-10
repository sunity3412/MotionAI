"""Phase 9 Wave 1 T2 — D-09-A2 raw signal only guard 회귀 차단.

force_pattern.py 안 axisMetric.severity 직접 trust 0 회. AST walk 로
`ast.Attribute(attr='severity')` 노드 중 receiver name token 이 axis 계열인
케이스 reject. substring grep 도 동시 검사 (defense in depth).

stabilityMetric / contactMetric 의 severity 는 guard scope 밖 (Phase 8 본체 신뢰).

per Plan 09-02 Task T2 / D-09-A2 / T-09-T1 / [[plan-vs-pivot-cross-check]].
"""

from __future__ import annotations

import ast
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = (
    _REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "force_pattern.py"
)


def test_force_pattern_py_does_not_access_axis_severity_via_ast() -> None:
    """D-09-A2 — force_pattern.py 안 axisMetric.severity 접근 0 회.

    AST walk 로 `ast.Attribute(attr='severity')` 노드 중 receiver 이름 token 이
    axis 계열 ({"axis", "axis_metric", "axisMetric", "a"}) 인 케이스 reject.
    """
    src = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    axis_receiver_tokens = {"axis", "axis_metric", "axisMetric", "a"}
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "severity":
            recv = node.value
            recv_name: str | None = None
            if isinstance(recv, ast.Name):
                recv_name = recv.id
            elif isinstance(recv, ast.Attribute):
                recv_name = recv.attr
            if recv_name in axis_receiver_tokens:
                violations.append((node.lineno, ast.unparse(node)))
    assert not violations, (
        f"D-09-A2 위반 — force_pattern.py 안 axis 계열 .severity 접근 발견: "
        f"{violations}"
    )


def test_force_pattern_py_no_axis_severity_substring() -> None:
    """Defense-in-depth substring grep — axis_metric.severity / axisMetric.severity
    / axis.severity 모두 검출.
    """
    src = _MODULE_PATH.read_text(encoding="utf-8")
    for bad in ("axis.severity", "axis_metric.severity", "axisMetric.severity"):
        assert bad not in src, f"D-09-A2 위반 substring 발견: {bad!r}"
