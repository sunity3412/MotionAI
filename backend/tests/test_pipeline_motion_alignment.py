"""pipeline `_attach_motion_alignment` — motionAlignment 방출 단위 + 채점 무접촉 게이트.

이 phase 의 hard 게이트: **채점 무접촉** (28-CONTEXT '점수·verdict 절대 불변').
alignment 방출의 유일한 부작용은 result 에 motionAlignment 키 1개 추가다 — overallScore/
deductionBreakdown 을 포함한 기존 키·값은 deepcopy diff 0 으로 불변임을 기계 판정한다
(ALGN-06). 그 외: 초 단위 방출, degenerate 'disabled' 방출(W3, legacy 필드 부재와 구분),
build 예외 graceful skip, match=None 미방출(legacy), 방출 dict 의 validator 통과(방출↔저장
계약 정합)를 검증한다.

상한 lockstep (B1): motion_alignment.MAX_ANCHOR_FLOATS == models.MOTION_ALIGNMENT_MAX_
ANCHOR_FLOATS 단언은 28-03 test_motion_alignment_contract.py 에서 이 파일로 **이동**했다 —
같은 wave(2)에서 28-02 산출물(motion_alignment)을 import 하면 병렬 collection error 가 나기
때문. 이 플랜은 wave 3, depends_on 에 28-02/28-03 이 모두 있어 안전하게 두 상수를 import 한다.

pipeline 모듈 로드는 test_pipeline_dispatch 관례 재사용 (functions/pipeline 를 path 에 추가).
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import motion_alignment
from sunity_shared.analysis.motiondtw import MotionMatch

# functions/pipeline/ 를 path 에 추가 — app 모듈 임포트 (dispatch 테스트 관례).
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

import app  # noqa: E402


def _match(path, distance, start=0, end=None):
    """합성 MotionMatch 빌더 (test_motion_alignment 관례 재사용)."""
    if end is None:
        end = start + (max((i for i, _ in path), default=-1) + 1) if path else start
    return MotionMatch(start=start, end=end, distance=distance, path=list(path))


def _scored_result() -> dict:
    """overallScore/deductionBreakdown 을 포함한 채점 확정 result fixture (무접촉 대조용)."""
    return {
        "overallScore": 87,
        "verdict": "good",
        "dimensionScores": {"angle": 87, "line": 90, "stability": 82},
        "deductionBreakdown": [
            {"joint": "left_knee", "deduction": 8, "reason": "무릎 신전 부족"},
        ],
        "joints": [{"key": "left_knee", "score": 88}],
    }


def test_no_scoring_contact_only_key_added():
    """채점 무접촉 (hard 게이트) — deepcopy diff 0, motionAlignment 키만 추가."""
    result = _scored_result()
    baseline = copy.deepcopy(result)
    path = [(i, 2 * i) for i in range(18)]
    app._attach_motion_alignment(
        result, _match(path, distance=1.0),
        user_fps=9.0, ref_fps=18.0, uid="u", analysis_id="a",
    )
    # motionAlignment 를 제외한 모든 기존 키·값이 완전히 동일 (채점 불변).
    added = {k: v for k, v in result.items() if k != "motionAlignment"}
    assert added == baseline
    assert "motionAlignment" in result  # 유일 부작용


def test_emits_seconds_and_tier():
    """방출: user 9fps/ref 18fps → anchors 는 초 단위(max ≤ 구간초+1), tier ∈ 3종."""
    result = _scored_result()
    path = [(i, 2 * i) for i in range(18)]  # identity-in-time (uSec≈rSec)
    app._attach_motion_alignment(
        result, _match(path, distance=1.0),
        user_fps=9.0, ref_fps=18.0, uid="u", analysis_id="a",
    )
    ma = result["motionAlignment"]
    assert ma["tier"] in {"warped", "trim_only", "disabled"}
    anchors = ma["anchors"]
    assert anchors and len(anchors) % 2 == 0
    span_sec = (18 - 1) / 9.0
    assert max(anchors) <= span_sec + 1.0  # 인덱스(2i=34)가 아니라 초(≈1.9s)


def test_degenerate_emits_disabled_with_empty_anchors():
    """degenerate (W3): ref_fps=0 → tier 'disabled' + anchors [] (키 존재 — legacy 와 구분)."""
    result = _scored_result()
    path = [(i, 2 * i) for i in range(18)]
    app._attach_motion_alignment(
        result, _match(path, distance=1.0),
        user_fps=9.0, ref_fps=0.0, uid="u", analysis_id="a",
    )
    ma = result["motionAlignment"]
    assert ma["tier"] == "disabled"
    assert ma["anchors"] == []


def test_build_exception_is_graceful():
    """graceful: build_motion_alignment 이 raise 해도 helper 는 통과 + result 무변경."""
    result = _scored_result()
    baseline = copy.deepcopy(result)

    def _boom(*_a, **_k):
        raise RuntimeError("build 폭발")

    orig = app.build_motion_alignment
    app.build_motion_alignment = _boom
    try:
        path = [(i, 2 * i) for i in range(18)]
        app._attach_motion_alignment(
            result, _match(path, distance=1.0),
            user_fps=9.0, ref_fps=18.0, uid="u", analysis_id="a",
        )
    finally:
        app.build_motion_alignment = orig
    assert result == baseline  # 방출 실패 = result 완전 무변경


def test_none_match_does_not_emit():
    """미방출: match=None → motionAlignment 키 부재 (legacy 필드 부재 유지)."""
    result = _scored_result()
    app._attach_motion_alignment(
        result, None, user_fps=9.0, ref_fps=18.0, uid="u", analysis_id="a",
    )
    assert "motionAlignment" not in result


def test_emitted_dict_passes_firestore_validator():
    """방출↔저장 계약 정합: 정상+degenerate 방출 dict 가 validator 를 raise 없이 통과."""
    # 정상 (warped/trim_only) 방출.
    normal = motion_alignment.build_motion_alignment(
        _match([(i, 2 * i) for i in range(18)], distance=1.0),
        user_fps=9.0, ref_fps=18.0,
    )
    firestore_admin._validate_motion_alignment(normal)
    # degenerate 방출 (disabled + 빈 anchors) — 역불변식 예외 통과.
    degenerate = motion_alignment.build_motion_alignment(
        _match([(i, 2 * i) for i in range(18)], distance=1.0),
        user_fps=9.0, ref_fps=0.0,
    )
    assert degenerate["tier"] == "disabled"
    firestore_admin._validate_motion_alignment(degenerate)


def test_max_anchor_floats_lockstep():
    """상한 lockstep (B1 — 28-03 에서 이동): motion_alignment ↔ models 상수 동일."""
    assert (
        motion_alignment.MAX_ANCHOR_FLOATS
        == models.MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS
    )
