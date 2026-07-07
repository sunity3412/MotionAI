"""Phase 27 SPD-01 — stage-timing 계측 단위 테스트 (27-RESEARCH Pattern 6).

박제 정신 (D-01 before/after 표의 데이터 소스):
  · `_stage` contextmanager 가 timings dict 에 int ms 를 누적하고
    `stage_timing analysis_id=%s stage=%s elapsed_ms=%d` 로그 라인을 방출한다
    (%-lazy 포맷 — [[never-log-secrets]] / 구조 로그 규율).
  · stage 블록 안에서 예외가 나도 elapsed 를 기록한 뒤 예외를 전파한다 (try/finally).
  · timings dict 는 `dict[str, int]` flat — `firestore_admin._validate_dict_only_scalars`
    통과 ([[firestore-nested-array-flat]] 정합, nested list/dict 없음).

전부 순수 함수 검증 — 실 S3 / 실 Firestore / 실 Gemini / 네트워크 호출 0.
PYTHONPATH=shared/python:. (pipeline/app.py 는 sys.path 주입으로 import).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

# pipeline/app.py + shared layer path 주입 (test_pipeline_deduction_seam.py 관례).
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared import firestore_admin  # noqa: E402


def test_stage_records_int_ms_and_emits_log(caplog) -> None:
    """Test 1 — timings dict 에 int ms 누적 + stage_timing 로그 라인 방출."""
    timings: dict[str, int] = {}
    with caplog.at_level(logging.INFO):
        with app._stage(timings, "analysis-xyz", "s3_download"):
            pass

    # dict 에 int ms 가 기록됐다.
    assert "s3_download" in timings
    assert isinstance(timings["s3_download"], int)
    assert timings["s3_download"] >= 0

    # stage_timing 로그 라인이 방출됐다 (analysis_id + stage 포함).
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "stage_timing" in joined
    assert "analysis-xyz" in joined
    assert "s3_download" in joined


def test_stage_records_elapsed_then_reraises_on_exception() -> None:
    """Test 2 — stage 블록 안 예외가 elapsed 기록 후 전파된다 (try/finally)."""
    timings: dict[str, int] = {}

    class _Boom(RuntimeError):
        pass

    with pytest.raises(_Boom):
        with app._stage(timings, "analysis-err", "rtmw"):
            raise _Boom("stage 안 예외")

    # 예외가 나도 elapsed 가 finally 에서 기록됐다.
    assert "rtmw" in timings
    assert isinstance(timings["rtmw"], int)


def test_timings_dict_is_flat_scalar_only() -> None:
    """Test 3 — timings dict 는 flat dict[str, int] — _validate_dict_only_scalars 통과."""
    timings: dict[str, int] = {}
    for name in ("s3_download", "frame_extract", "rtmw", "dtw_scoring", "coach_dual"):
        with app._stage(timings, "analysis-flat", name):
            pass

    # nested list/dict 없음 — [[firestore-nested-array-flat]] 정합.
    firestore_admin._validate_dict_only_scalars(timings, path="result.timingsMs")
    # 모든 값이 int scalar.
    assert all(isinstance(v, int) for v in timings.values())
    assert len(timings) == 5
