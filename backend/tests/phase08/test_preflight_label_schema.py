"""Pre-flight CSV schema + spec docs 존재 검증.

belle 운영 작업 진입 차단 해소 — preflight 디렉토리의 spec/template 파일이
존재하고 schema 가 정합한지 검증. belle 의 라벨링 값 (timestamp_ms_belle /
agreed) 은 빈칸 — 본 test 는 schema 만 검증.

per Plan 08-00 Task 3 <behavior> + REVIEWS Cycle 1 R4 + R5.
"""

from __future__ import annotations

import csv
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PREFLIGHT_DIR = (
    _REPO_ROOT
    / ".planning"
    / "phases"
    / "08-jerk-jitter"
    / "preflight"
)
_SPEC_MD = _PREFLIGHT_DIR / "PREFLIGHT-LABEL-SPEC.md"
_TEMPLATE_CSV = _PREFLIGHT_DIR / "preflight_label_template.csv"


def test_label_spec_md_exists() -> None:
    """PREFLIGHT-LABEL-SPEC.md 존재 + 8 section heading (§1~§8) 박제."""
    assert _SPEC_MD.exists(), f"{_SPEC_MD} not found"
    text = _SPEC_MD.read_text(encoding="utf-8")
    for section in (
        "## §1 목적",
        "## §2 라벨링 범위",
        "## §3 라벨링 방법",
        "## §4 PASS / FAIL 기준",
        "## §5 입력 파일",
        "## §6 FAIL 시 unwind path",
        "## §7 재실행",
        "## §8 박제 메모",
    ):
        assert section in text, f"missing section '{section}' in PREFLIGHT-LABEL-SPEC.md"
    # 핵심 임계 박제 grep.
    assert "80%" in text, "80% PASS 임계 missing"
    assert "200ms" in text, "200ms 일치 임계 missing"
    assert "ref-invert" in text, "ref-invert reference 영상 박제 missing"
    assert "preflight_label_template.csv" in text, "template csv 박제 missing"


def test_template_csv_header() -> None:
    """preflight_label_template.csv 의 header column 박제."""
    assert _TEMPLATE_CSV.exists(), f"{_TEMPLATE_CSV} not found"
    with _TEMPLATE_CSV.open("r", encoding="utf-8") as f:
        first_line = f.readline().rstrip("\n").rstrip("\r")
    expected = "video_id,motion_id,phase,timestamp_ms_belle,timestamp_ms_layer1,delta_ms,agreed"
    assert first_line == expected, (
        f"CSV header mismatch.\n  expected: {expected}\n  got:      {first_line}"
    )


def test_template_csv_25_rows() -> None:
    """preflight_label_template.csv = header 1 + 25 row (5 영상 × 5 phase)."""
    with _TEMPLATE_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 25, f"expected 25 row, got {len(rows)}"

    # 5 distinct video_id.
    video_ids = {r["video_id"] for r in rows}
    expected_videos = {
        "ref-invert",
        "ref-foxtop",
        "ref-foxtop-split",
        "ref-climb",
        "ref-sideway-spin",
    }
    assert video_ids == expected_videos, (
        f"video_id mismatch — expected {expected_videos}, got {video_ids}"
    )

    # 5 distinct phase boundary.
    phases = {r["phase"] for r in rows}
    expected_phases = {
        "entry_start",
        "lock_start",
        "transition_start",
        "final_shape_start",
        "hold_start",
    }
    assert phases == expected_phases, (
        f"phase mismatch — expected {expected_phases}, got {phases}"
    )

    # 각 video_id 별로 5 row (5 phase) 박제.
    from collections import Counter

    per_video = Counter(r["video_id"] for r in rows)
    for video, count in per_video.items():
        assert count == 5, f"{video} should have 5 rows (5 phase), got {count}"

    # belle 입력 값 (timestamp_ms_belle / agreed) 은 빈칸 (schema 만 검증).
    for r in rows:
        assert r["timestamp_ms_belle"] == "", (
            f"timestamp_ms_belle should be empty in template, "
            f"got {r['timestamp_ms_belle']!r} for {r['video_id']}/{r['phase']}"
        )
        assert r["agreed"] == "", (
            f"agreed should be empty in template, "
            f"got {r['agreed']!r} for {r['video_id']}/{r['phase']}"
        )
