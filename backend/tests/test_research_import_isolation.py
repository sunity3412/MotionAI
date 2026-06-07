"""Phase 2 R&D 격리 + 라이선스 차단 AST 자동 검증.

MEDIUM-1 v3: 스캔 범위 sunity_shared + backend/functions + backend/runpod_inference.
LOW-2 v4 박제: importlib.import_module + __import__ + spec_from_file_location literal
모두 차단. 잔여 위험: 비-literal 동적 import (variable 인자) 정적 분석 한계 — PR
manual review 정합.

v1→v2 HIGH-3 박제 유지 — mediapipe 차단 제외 (legacy mediapipe code 는
lazy import 유지). 차단 대상 prefix:
  - research / backend.research
  - nlf
  - smplx / smpl_x

목표: 운영 제품 코드 (sunity_shared / functions / runpod_inference) 가
backend.research (R&D throwaway) 또는 NLF / SMPL-X (PS:License 1.0, 비상업)
모듈을 import 하지 못하도록 차단.

# TODO(LOW-2 v4 잔여 위험):
#   비-literal 동적 import (variable 인자 importlib.import_module(name) 등) 는
#   정적 AST 분석으로 차단 불가. PR review + runtime gate 로 보완 필요.
# TODO(HIGH-3 v2): mediapipe 차단은 제외 — legacy lazy import 유지 (pose_engines/
#   __init__.py + mediapipe_engine.py). RTMW pivot 후 별도 plan 에서 폐기.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]

_SCAN_DIRS = (
    _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared",
    _REPO_ROOT / "backend" / "functions",
    _REPO_ROOT / "backend" / "runpod_inference",
)

# 차단 prefix — research / nlf / smplx / smpl_x. mediapipe 는 제외 (HIGH-3 v2 박제).
_BLOCKED_PREFIXES = ("research", "backend.research", "nlf", "smplx", "smpl_x")


def _iter_py_files(roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            # 캐시/빌드 결과 제외
            if "__pycache__" in p.parts:
                continue
            files.append(p)
    return files


def _module_prefix_blocked(module_name: str) -> bool:
    """root 모듈명 (예: "backend.research.evaluations.compare_body_profile")
    이 차단 prefix 중 하나로 시작하는지 검사."""
    if not module_name:
        return False
    parts = module_name.split(".")
    head = parts[0]
    head_two = ".".join(parts[:2]) if len(parts) >= 2 else head
    if head in _BLOCKED_PREFIXES:
        return True
    if head_two in _BLOCKED_PREFIXES:
        return True
    return False


def _find_static_blocked_imports(tree: ast.AST, path: Path) -> list[str]:
    """`import X` / `from X import Y` 에서 X 가 차단 prefix 면 사이트 박제."""
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _module_prefix_blocked(alias.name):
                    findings.append(
                        f"{path}:{node.lineno} static import — `import {alias.name}`"
                    )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            # `from . import x` 는 level>0 → mod 비어있을 수 있음 → skip
            if node.level == 0 and _module_prefix_blocked(mod):
                findings.append(
                    f"{path}:{node.lineno} static from-import — `from {mod} import ...`"
                )
    return findings


def _find_dynamic_importlib(tree: ast.AST, path: Path) -> list[str]:
    """importlib.import_module(literal) 차단."""
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != "import_module":
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            if _module_prefix_blocked(first.value):
                findings.append(
                    f"{path}:{node.lineno} dynamic importlib.import_module("
                    f"{first.value!r})"
                )
    return findings


def _find_dynamic_dunder_import(tree: ast.AST, path: Path) -> list[str]:
    """__import__(literal) 차단."""
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name):
            continue
        if func.id != "__import__":
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            if _module_prefix_blocked(first.value):
                findings.append(
                    f"{path}:{node.lineno} dynamic __import__({first.value!r})"
                )
    return findings


def _find_dynamic_spec_from_file_location(tree: ast.AST, path: Path) -> list[str]:
    """spec_from_file_location(name_literal, path_literal) — name 첫 인자가
    차단 prefix 이거나 path basename 이 차단 모듈명 매치 시 차단.

    runpod_inference/server.py:73 legitimate 사용:
      spec_from_file_location("sunity_pipeline_app", pipeline_path)
      → name="sunity_pipeline_app" 매치 0 + path 는 변수 → PASS.
    """
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != "spec_from_file_location":
            continue
        # 첫 인자: name (literal 만 검사)
        if node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                if _module_prefix_blocked(first.value):
                    findings.append(
                        f"{path}:{node.lineno} dynamic spec_from_file_location "
                        f"name={first.value!r}"
                    )
        # 두 번째 인자: path (literal 만 검사 — basename 차단 모듈명 매치)
        if len(node.args) >= 2:
            second = node.args[1]
            if isinstance(second, ast.Constant) and isinstance(second.value, str):
                basename = Path(second.value).stem
                if basename in _BLOCKED_PREFIXES or any(
                    second.value.endswith(f"/{prefix}.py")
                    or second.value.endswith(f"/{prefix}/__init__.py")
                    for prefix in _BLOCKED_PREFIXES
                ):
                    findings.append(
                        f"{path}:{node.lineno} dynamic spec_from_file_location "
                        f"path={second.value!r}"
                    )
    return findings


# ── 테스트 5개 ───────────────────────────────────────────────────────────


def _collect_static_findings(root: Path) -> list[str]:
    findings: list[str] = []
    for path in _iter_py_files((root,)):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        findings.extend(_find_static_blocked_imports(tree, path))
    return findings


def test_sunity_shared_does_not_import_research_or_nlf_or_smplx() -> None:
    """MEDIUM-1 v3: sunity_shared static import 검사."""
    root = _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared"
    findings = _collect_static_findings(root)
    assert not findings, (
        "차단 prefix static import 발견 — 운영 코드는 backend.research / nlf / smplx 를 import 할 수 없음:\n"
        + "\n".join(findings)
    )


def test_backend_functions_does_not_import_research_or_nlf_or_smplx() -> None:
    """MEDIUM-1 v3: backend/functions static import 검사."""
    root = _REPO_ROOT / "backend" / "functions"
    findings = _collect_static_findings(root)
    assert not findings, (
        "차단 prefix static import 발견 — Lambda functions 는 backend.research / nlf / smplx 를 import 할 수 없음:\n"
        + "\n".join(findings)
    )


def test_backend_runpod_inference_does_not_import_research_or_nlf_or_smplx() -> None:
    """MEDIUM-1 v3: backend/runpod_inference static import 검사."""
    root = _REPO_ROOT / "backend" / "runpod_inference"
    findings = _collect_static_findings(root)
    assert not findings, (
        "차단 prefix static import 발견 — RunPod server 는 backend.research / nlf / smplx 를 import 할 수 없음:\n"
        + "\n".join(findings)
    )


def test_no_dynamic_importlib_import_of_research_or_nlf_or_smplx() -> None:
    """LOW-2 v4: importlib.import_module(literal) 3 디렉터리 전체 검사."""
    all_findings: list[str] = []
    for path in _iter_py_files(_SCAN_DIRS):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        all_findings.extend(_find_dynamic_importlib(tree, path))
    assert not all_findings, (
        "차단 prefix 의 importlib.import_module(literal) 호출 발견:\n"
        + "\n".join(all_findings)
    )


def test_no_dynamic_dunder_import_or_spec_from_file_location_of_research_or_nlf_or_smplx() -> None:
    """LOW-2 v4: __import__(literal) + spec_from_file_location(name_literal) 차단.

    runpod_inference/server.py:73 의 `spec_from_file_location("sunity_pipeline_app", ...)`
    는 name="sunity_pipeline_app" (차단 prefix 아님) + path 가 변수 → 매치 0 → PASS.
    """
    all_findings: list[str] = []
    for path in _iter_py_files(_SCAN_DIRS):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        all_findings.extend(_find_dynamic_dunder_import(tree, path))
        all_findings.extend(_find_dynamic_spec_from_file_location(tree, path))
    assert not all_findings, (
        "차단 prefix 의 __import__(literal) 또는 spec_from_file_location(literal) 발견:\n"
        + "\n".join(all_findings)
    )
