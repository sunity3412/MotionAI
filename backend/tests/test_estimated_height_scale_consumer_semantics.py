"""estimatedHeightScale / estimated_height_scale identifier 의 모든 deployable
consumer 가 인접 (±3 라인) 에 'torso-relative proportion heuristic' (또는
TS 'torso-relative') 주석 박제했는지 lint scan.

MEDIUM-3 v4 + LOW-1 v5 박제: 필드명이 absolute height 처럼 보이는 risk 차단.
scan 4 dir = Python (sunity_shared + backend/functions + backend/runpod_inference)
           + TS (app/src).
제외 = backend/research/ (R&D throwaway) + backend/tests/ + app/scripts/.

현재 consumer 0 → vacuous PASS. Phase 6+ consumer 추가 시 load-bearing.

Rename Option B reject 사유: 필드 rename 은 3-way lockstep + CONTEXT.md +
dataclass 모두 깨짐. Option A (lint) 만 채택.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]

_PY_PATTERN = re.compile(r"\b(estimatedHeightScale|estimated_height_scale)\b")
_TS_PATTERN = re.compile(r"\bestimatedHeightScale\b")

# 정의 파일 (Python) — 정의 line 은 consumer 가 아님
_PY_DEFINITION_FILES = {
    _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared" / "analysis" / "body_normalization.py",
    _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared" / "analysis" / "body_normalization_measurer.py",
}

# 정의 파일 (TS)
_TS_DEFINITION_FILE = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"


@dataclass(frozen=True)
class ConsumerSite:
    file: Path
    line: int  # 1-based
    content: str
    lang: str  # 'python' | 'ts'


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


# ── Python 스캔 ──────────────────────────────────────────────────────────


def _scan_python_consumer_lines(root: Path) -> list[ConsumerSite]:
    """root.rglob('*.py') 전체에서 identifier 매치 line 박제. 정의 파일 제외."""
    sites: list[ConsumerSite] = []
    if not root.exists():
        return sites
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path in _PY_DEFINITION_FILES:
            continue
        try:
            lines = _read_lines(path)
        except OSError:
            continue
        for idx, line in enumerate(lines, start=1):
            if _PY_PATTERN.search(line):
                sites.append(
                    ConsumerSite(file=path, line=idx, content=line, lang="python")
                )
    return sites


# ── TS 스캔 ──────────────────────────────────────────────────────────────


def _scan_ts_consumer_lines(root: Path) -> list[ConsumerSite]:
    """root.rglob('*.ts(x)') 전체에서 identifier 매치 line 박제.

    analysis.ts 의 BodyNormalizationProfile interface 안 첫 정의 line 제외 —
    consumer 측 등장만 검색.
    """
    sites: list[ConsumerSite] = []
    if not root.exists():
        return sites

    # 정의 파일 안 'estimatedHeightScale: number;' (interface 본체 안) 제외
    definition_lines_in_def_file: set[int] = set()
    if _TS_DEFINITION_FILE.exists():
        try:
            def_lines = _read_lines(_TS_DEFINITION_FILE)
            for idx, line in enumerate(def_lines, start=1):
                # interface 본체 안 필드 정의 line 은 통상 `  estimatedHeightScale:`
                # 패턴 (identifier 뒤 `:` 가 따라옴) — 이 line 만 정의 line 으로 간주.
                if re.search(r"\bestimatedHeightScale\b\s*:", line):
                    definition_lines_in_def_file.add(idx)
        except OSError:
            pass

    for ext in ("*.ts", "*.tsx"):
        for path in root.rglob(ext):
            try:
                lines = _read_lines(path)
            except OSError:
                continue
            for idx, line in enumerate(lines, start=1):
                if not _TS_PATTERN.search(line):
                    continue
                # 정의 파일 안 정의 line 만 제외 (consumer 측 등장은 포함)
                if path == _TS_DEFINITION_FILE and idx in definition_lines_in_def_file:
                    continue
                sites.append(
                    ConsumerSite(file=path, line=idx, content=line, lang="ts")
                )
    return sites


# ── 검증 helper ──────────────────────────────────────────────────────────


def _assert_semantic_comment_nearby(
    site: ConsumerSite, *, required_substring: str
) -> None:
    """매치 line ±3 라인 안에 required_substring 포함 여부 검사."""
    try:
        all_lines = _read_lines(site.file)
    except OSError:
        raise AssertionError(
            f"LOW-1 v5 박제 위반: {site.file} 읽기 실패"
        )
    start = max(0, site.line - 1 - 3)
    end = min(len(all_lines), site.line - 1 + 3 + 1)
    window = "\n".join(all_lines[start:end])
    if required_substring not in window:
        raise AssertionError(
            f"LOW-1 v5 박제 위반: {site.file}:{site.line} ({site.lang}) — "
            f"estimatedHeightScale 사용 시 인접 (±3 라인) 에 "
            f"'{required_substring}' 주석 박제 필수. 본 필드는 absolute height "
            f"아님 — torso 길이 대비 사지 비율 heuristic (per Phase 2 Task 1 lockstep)."
        )


# ── 테스트 5개 (LOW-1 v5) ─────────────────────────────────────────────────


def test_python_consumers_have_semantic_comment_in_sunity_shared() -> None:
    """sunity_shared consumer 스캔 (정의 파일 제외) — 현재 vacuous PASS."""
    sites = _scan_python_consumer_lines(
        _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared"
    )
    for site in sites:
        _assert_semantic_comment_nearby(
            site, required_substring="torso-relative proportion heuristic"
        )


def test_python_consumers_have_semantic_comment_in_functions_and_runpod() -> None:
    """LOW-1 v5 신규: backend/functions + backend/runpod_inference consumer 스캔.

    현재 vacuous PASS — Phase 6+ consumer 추가 시 load-bearing.
    """
    sites = _scan_python_consumer_lines(
        _REPO_ROOT / "backend" / "functions"
    ) + _scan_python_consumer_lines(
        _REPO_ROOT / "backend" / "runpod_inference"
    )
    for site in sites:
        _assert_semantic_comment_nearby(
            site, required_substring="torso-relative proportion heuristic"
        )


def test_ts_consumers_have_semantic_comment_in_app_src() -> None:
    """LOW-1 v5 신규: app/src TS consumer 스캔.

    analysis.ts 의 BodyNormalizationProfile interface 안 정의 line 제외 —
    consumer 측 등장만 검색. 현재 vacuous PASS.
    """
    sites = _scan_ts_consumer_lines(_REPO_ROOT / "app" / "src")
    for site in sites:
        _assert_semantic_comment_nearby(
            site, required_substring="torso-relative"
        )


def test_scan_excludes_definition_files() -> None:
    """정의 파일 line 결과에 포함 0."""
    # Python 정의 파일 제외 확인
    py_sites = _scan_python_consumer_lines(
        _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared"
    )
    for site in py_sites:
        assert site.file not in _PY_DEFINITION_FILES, (
            f"Python 정의 파일이 consumer 스캔에 포함됨: {site.file}"
        )

    # TS 정의 파일 안 interface 정의 line 제외 확인
    ts_sites = _scan_ts_consumer_lines(_REPO_ROOT / "app" / "src")
    for site in ts_sites:
        if site.file == _TS_DEFINITION_FILE:
            # 정의 line (필드: 패턴) 은 제외되어야 함
            assert not re.search(r"\bestimatedHeightScale\b\s*:", site.content), (
                f"TS 정의 line 이 consumer 스캔에 포함됨: {site.file}:{site.line}"
            )


def test_scan_excludes_research_tests_scripts() -> None:
    """backend/research/ + backend/tests/ + app/scripts/ 등장 포함 0."""
    sites: list[ConsumerSite] = []
    sites.extend(_scan_python_consumer_lines(_REPO_ROOT / "backend" / "research"))
    sites.extend(_scan_python_consumer_lines(_REPO_ROOT / "backend" / "tests"))
    sites.extend(_scan_ts_consumer_lines(_REPO_ROOT / "app" / "scripts"))

    # 위 함수들은 scan 대상이 아니라 단순 helper 호출 — 만약 등장하더라도 스캔
    # 대상 4 dir 에 포함되지 않으므로 assert 트리거 0. 정확한 의미: 4 dir 의
    # 스캔 결과에 backend/research / backend/tests / app/scripts 경로가 절대
    # 포함되지 않음.

    # 4 dir 스캔 결과 검사
    actual_sites: list[ConsumerSite] = []
    actual_sites.extend(
        _scan_python_consumer_lines(
            _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared"
        )
    )
    actual_sites.extend(_scan_python_consumer_lines(_REPO_ROOT / "backend" / "functions"))
    actual_sites.extend(
        _scan_python_consumer_lines(_REPO_ROOT / "backend" / "runpod_inference")
    )
    actual_sites.extend(_scan_ts_consumer_lines(_REPO_ROOT / "app" / "src"))

    for site in actual_sites:
        rel = site.file.relative_to(_REPO_ROOT)
        parts = rel.parts
        assert "research" not in parts, f"research 가 4 dir scan 결과에 포함됨: {rel}"
        assert "tests" not in parts, f"tests 가 4 dir scan 결과에 포함됨: {rel}"
        # app/scripts 는 TS scan root (app/src) 와 무관 — 별도 검사 불필요
