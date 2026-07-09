"""학습셋 provenance + 금지 모델 fence 테스트 (22-02 Task 1, FT-06).

불변식:
  · 모든 매니페스트 행에 provenance(source_url·license_evidence·usage) 필수.
  · label_bucket 은 정타|fault 만 — 사람 숫자 점수 라벨 어디에도 없음(버킷만).
  · 매니페스트 어느 행에도 uid/사용자 식별자 필드 없음 (T-22-04).
  · backend/training + backend/evals/phase22 의 .py 주석 제외 라인에 llava/internvl-u
    식별자 0 (금지 모델 fence — 상업 불가/오염).
"""

import json
import re
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]
_MANIFEST = _BACKEND / "training" / "data" / "manifest.json"

REQUIRED_PROVENANCE_FIELDS = ("source_url", "license_evidence", "usage")
VALID_BUCKETS = ("정타", "fault")
# uid/사용자 식별자 화이트리스트 금지 필드.
FORBIDDEN_IDENTITY_FIELDS = ("uid", "user_id", "userId", "email", "phone")
# 금지 모델 — 상업 불가(LLaVA) / 생성헤드 오염(InternVL-U).
FORBIDDEN_MODEL_IDENTIFIERS = ("llava", "internvl-u", "internvl_u")


def _load_rows() -> list[dict]:
    if not _MANIFEST.exists():
        return []
    data = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    return data.get("rows", [])


def _row_provenance_ok(row: dict) -> bool:
    return all(row.get(f) for f in REQUIRED_PROVENANCE_FIELDS)


def test_all_rows_have_required_provenance():
    """provenance 필수 필드(source_url·license_evidence·usage) 부재 시 FAIL."""
    rows = _load_rows()
    for row in rows:
        assert _row_provenance_ok(row), f"provenance 누락 행: {row.get('s3_key')}"
    # 합성 결손 행은 반드시 거부되어야(가드 자체 검증).
    assert _row_provenance_ok({"source_url": "x"}) is False


def test_label_bucket_rejects_numeric_and_out_of_enum():
    """label_bucket 이 정타|fault 밖(숫자 점수 포함)이면 FAIL."""
    rows = _load_rows()
    for row in rows:
        assert row.get("label_bucket") in VALID_BUCKETS, (
            f"label_bucket 이 enum 밖(숫자 점수 라벨 금지): {row.get('label_bucket')!r}"
        )
    # 숫자 점수 라벨은 enum 밖.
    assert "87" not in VALID_BUCKETS
    assert 41 not in VALID_BUCKETS


def test_no_uid_or_identity_fields_in_any_row():
    """매니페스트 어느 행에도 uid/사용자 식별자 필드 없음 (D-12, T-22-04)."""
    rows = _load_rows()
    for row in rows:
        for forbidden in FORBIDDEN_IDENTITY_FIELDS:
            assert forbidden not in row, f"금지 식별자 필드 {forbidden!r} 등장: {row.get('s3_key')}"


def _strip_comments(source: str) -> str:
    """.py 소스에서 주석 라인 + 인라인 주석 + 문자열 리터럴/독스트링 제거(근사).

    금지 모델 fence 는 '주석 제외 실행 라인'만 검사한다 — 독스트링/주석의 설명적
    언급(예: 'LLaVA 상업 불가')은 허용, 실제 코드 식별자만 차단.
    """
    # 트리플쿼트 독스트링/문자열 제거.
    source = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    source = re.sub(r"'''.*?'''", "", source, flags=re.DOTALL)
    out_lines = []
    for line in source.splitlines():
        # 인라인 주석 제거.
        hash_idx = line.find("#")
        if hash_idx != -1:
            line = line[:hash_idx]
        # 단일따옴표/쌍따옴표 문자열 리터럴 제거(근사).
        line = re.sub(r'"[^"]*"', "", line)
        line = re.sub(r"'[^']*'", "", line)
        out_lines.append(line)
    return "\n".join(out_lines)


def test_forbidden_model_identifiers_fenced():
    """backend/training + backend/evals/phase22 의 .py 실행 라인에 llava/internvl-u 0."""
    scan_dirs = [
        _BACKEND / "training",
        _BACKEND / "evals" / "phase22",
    ]
    violations = []
    for d in scan_dirs:
        if not d.exists():
            continue
        for py in d.rglob("*.py"):
            code = _strip_comments(py.read_text(encoding="utf-8")).lower()
            for ident in FORBIDDEN_MODEL_IDENTIFIERS:
                if ident in code:
                    violations.append(f"{py}: {ident}")
    assert not violations, f"금지 모델 식별자 등장(실행 라인): {violations}"


def test_strip_comments_allows_docstring_mentions():
    """가드 자체 검증 — 독스트링/주석의 LLaVA 언급은 fence 통과(설명 허용)."""
    sample = '"""LLaVA 는 상업 불가 — 사용 금지."""\nx = 1  # internvl-u 아키텍처 차용만\n'
    stripped = _strip_comments(sample).lower()
    assert "llava" not in stripped
    assert "internvl-u" not in stripped
