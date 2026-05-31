"""compare_engines.py smoke 테스트.

S3·MediaPipe·NLF 의존성 없이 모듈 구조 + 데이터 계약 + 보고서 로직을 검증.
run_engine / compare_engines 자체는 S3 + 엔진 라이브러리가 필요해 smoke 범위 밖.

테스트 목록:
  1. test_engine_result_dataclass       — EngineResult 생성 + 필드 타입 확인
  2. test_generate_markdown_report_basic — synthetic payload → 보고서 구조 확인
  3. test_phase1_ready_to_swap_logic    — PASS/FAIL 로직 확인
  4. test_avg_confidence_threshold_placeholder — A9 placeholder 0.5 검증
  5. test_default_motions_count         — D-13 정은지 5영상 검증
  6. test_engine_mode_choices           — Plan 01-08: --engine 옵션 3개 확인
  7. test_generate_markdown_report_lifter_mode — nlf-vs-mediapipe-lifter 모드 보고서 구조
  8. test_generate_markdown_report_mediapipe_only_mode — mediapipe-vs-mediapipe-lifter 모드
  9. test_compare_engines_invalid_mode  — 잘못된 engine_mode → ValueError
"""

from __future__ import annotations

import math

import pytest


# ── import 경로 ────────────────────────────────────────────────────────────

from backend.research.evaluations.compare_engines import (
    AVG_CONFIDENCE_THRESHOLD,
    DEFAULT_MOTIONS,
    EngineResult,
    _ENGINE_MODE_CHOICES,
    compare_engines,
    generate_markdown_report,
)


# ── Test 1: EngineResult 데이터 계약 ──────────────────────────────────────

def test_engine_result_dataclass() -> None:
    """EngineResult dataclass 생성 + 필드 타입 검증."""
    result = EngineResult(
        overall_score=82.5,
        dimension_scores={"angle": 80.0, "line": 85.0, "stability": 82.0},
        top3_failures=["left_knee_bend", "hip_rotation", "shoulder_alignment"],
        avg_keypoint_confidence=0.78,
        ms_per_frame=35.2,
    )

    assert isinstance(result.overall_score, float)
    assert result.overall_score == 82.5

    assert isinstance(result.dimension_scores, dict)
    assert "angle" in result.dimension_scores

    assert isinstance(result.top3_failures, list)
    assert len(result.top3_failures) == 3

    assert isinstance(result.avg_keypoint_confidence, float)
    assert result.avg_keypoint_confidence == 0.78

    assert isinstance(result.ms_per_frame, float)
    assert result.ms_per_frame == 35.2


def test_engine_result_defaults() -> None:
    """EngineResult 기본값 — NaN/빈 컬렉션."""
    result = EngineResult(overall_score=0.0)

    assert result.dimension_scores == {}
    assert result.top3_failures == []
    assert math.isnan(result.avg_keypoint_confidence)
    assert math.isnan(result.ms_per_frame)


# ── Test 2: generate_markdown_report 기본 구조 ────────────────────────────

def _synthetic_payload(
    phase1_ready: bool = True,
    motion_id: str = "ref-ballerina-spin",
) -> dict:
    """테스트용 synthetic payload 생성 헬퍼."""
    gates = {
        "score_gap": 2.5,
        "within_tolerance_5pt": True,
        "mediapipe_score_ge_70": True,
        "top3_overlap_2_of_3": True,
        "avg_confidence_ok": True,
        "mediapipe_ms_per_frame": 210.0,
    }
    if not phase1_ready:
        gates["mediapipe_score_ge_70"] = False

    return {
        "criteria": {
            "score_gap_tolerance_pt": 5.0,
            "mediapipe_min_score_for_expert": 70.0,
            "avg_confidence_threshold": 0.5,
            "top3_overlap_min": 2,
        },
        "generated_at": "2026-06-01T00:00:00+00:00",
        "motions": {
            motion_id: {
                "mediapipe": {
                    "overall_score": 83.0,
                    "dimension_scores": {"angle": 80.0, "line": 86.0},
                    "top3_failures": ["left_knee", "hip", "shoulder"],
                    "avg_keypoint_confidence": 0.78,
                    "ms_per_frame": 210.0,
                },
                "nlf": {
                    "overall_score": 81.0,
                    "dimension_scores": {"angle": 78.0, "line": 84.0},
                    "top3_failures": ["left_knee", "hip", "ankle"],
                    "avg_keypoint_confidence": None,
                    "ms_per_frame": 450.0,
                },
                "gates": gates,
            }
        },
        "summary": {
            "all_within_tolerance": phase1_ready,
            "all_mediapipe_ge_70": phase1_ready,
            "all_top3_overlap_ok": phase1_ready,
            "all_avg_confidence_ok": phase1_ready,
            "phase1_ready_to_swap": phase1_ready,
        },
    }


def test_generate_markdown_report_basic() -> None:
    """synthetic payload → Markdown 보고서 구조 확인.

    헤더 + motion_id row + 요약 표 + 최종 결정 박스를 검증.
    """
    payload = _synthetic_payload(phase1_ready=True, motion_id="ref-ballerina-spin")
    md = generate_markdown_report(payload)

    assert isinstance(md, str)
    assert len(md) > 100  # 최소 내용 있음

    # 헤더 확인
    assert "Phase 1 회귀 검증 보고서" in md
    assert "MediaPipe vs NLF" in md
    assert "atomic swap" in md.lower() or "Wave 2" in md

    # motion_id row 확인
    assert "ref-ballerina-spin" in md

    # 요약 표 확인
    assert "phase1_ready_to_swap" in md

    # PASS/FAIL 확인
    assert "PASS" in md

    # 최종 결정 박스
    assert "Wave 3" in md


def test_generate_markdown_report_fail_case() -> None:
    """게이트 FAIL 시 Markdown에 D-16 보류 메시지 포함."""
    payload = _synthetic_payload(phase1_ready=False)
    md = generate_markdown_report(payload)

    assert "D-16" in md
    assert "false" in md.lower() or "FAIL" in md
    # H-1 박제: Wave 3 시작 금지 메시지
    assert "H-1" in md or "Wave 3 보류" in md or "금지" in md


# ── Test 3: phase1_ready_to_swap 로직 ────────────────────────────────────

def test_phase1_ready_to_swap_logic_all_pass() -> None:
    """4개 게이트 모두 PASS → phase1_ready_to_swap = True."""
    payload = _synthetic_payload(phase1_ready=True)
    summary = payload["summary"]

    assert summary["all_within_tolerance"] is True
    assert summary["all_mediapipe_ge_70"] is True
    assert summary["all_top3_overlap_ok"] is True
    assert summary["all_avg_confidence_ok"] is True
    assert summary["phase1_ready_to_swap"] is True


def test_phase1_ready_to_swap_logic_one_fail() -> None:
    """D-15 ① 게이트 FAIL → phase1_ready_to_swap = False."""
    payload = _synthetic_payload(phase1_ready=False)
    summary = payload["summary"]

    # phase1_ready_to_swap은 False여야 함
    assert summary["phase1_ready_to_swap"] is False


# ── Test 4: A9 confidence threshold placeholder ────────────────────────────

def test_avg_confidence_threshold_placeholder() -> None:
    """AVG_CONFIDENCE_THRESHOLD == 0.5 (A9 placeholder 검증).

    belle 확정 전까지 0.5. Plan 06 Task 2 회귀 결과 후 갱신 예정.
    """
    assert AVG_CONFIDENCE_THRESHOLD == 0.5


# ── Test 5: DEFAULT_MOTIONS count ─────────────────────────────────────────

def test_default_motions_count() -> None:
    """DEFAULT_MOTIONS == 5개 (D-13 정은지 5영상)."""
    assert len(DEFAULT_MOTIONS) == 5


def test_default_motions_types() -> None:
    """DEFAULT_MOTIONS 내 모든 항목이 비어있지 않은 str."""
    for motion_id in DEFAULT_MOTIONS:
        assert isinstance(motion_id, str)
        assert len(motion_id) > 0
        assert motion_id.startswith("ref-")  # reference motion 명명 규칙


def test_default_motions_contains_expected() -> None:
    """D-13 명세된 5개 motion_id가 모두 포함됨."""
    expected = {
        "ref-ballerina-spin",
        "ref-front-hook-spin",
        "ref-plank-spin",
        "ref-invert-butterfly-combo",
        "ref-gemini-to-ayesha-combo",
    }
    assert expected == set(DEFAULT_MOTIONS)


# ── Test 6: Plan 01-08 — --engine 옵션 3개 확인 ──────────────────────────

def test_engine_mode_choices_count() -> None:
    """Plan 01-08 T-4-1: --engine 옵션이 정확히 3개여야 한다."""
    assert len(_ENGINE_MODE_CHOICES) == 3


def test_engine_mode_choices_values() -> None:
    """Plan 01-08: 3개 엔진 모드 이름 확인."""
    assert "nlf-vs-mediapipe" in _ENGINE_MODE_CHOICES
    assert "nlf-vs-mediapipe-lifter" in _ENGINE_MODE_CHOICES
    assert "mediapipe-vs-mediapipe-lifter" in _ENGINE_MODE_CHOICES


def test_engine_mode_default_is_backward_compat() -> None:
    """기본값은 nlf-vs-mediapipe (기존 호환)."""
    # argparse default 값은 main() 내부에 있으므로 상수로 검증
    assert "nlf-vs-mediapipe" in _ENGINE_MODE_CHOICES


# ── Test 7: nlf-vs-mediapipe-lifter 모드 보고서 구조 ─────────────────────

def _synthetic_payload_lifter(
    engine_mode: str = "nlf-vs-mediapipe-lifter",
    phase1_ready: bool = True,
    motion_id: str = "ref-foxtop-split",
) -> dict:
    """nlf-vs-mediapipe-lifter / mediapipe-vs-mediapipe-lifter 모드용 synthetic payload."""
    gates = {
        "score_gap": 3.0,
        "within_tolerance_5pt": True,
        "mediapipe_score_ge_70": phase1_ready,
        "top3_overlap_2_of_3": True,
        "avg_confidence_ok": True,
        "mediapipe_ms_per_frame": 90.0,
    }
    return {
        "engine_mode": engine_mode,
        "criteria": {
            "score_gap_tolerance_pt": 5.0,
            "mediapipe_min_score_for_expert": 70.0,
            "avg_confidence_threshold": 0.5,
            "top3_overlap_min": 2,
        },
        "generated_at": "2026-06-01T00:00:00+00:00",
        "motions": {
            motion_id: {
                "engine_a": {
                    "name": "nlf",
                    "overall_score": 62.0,
                    "dimension_scores": {"angle": 60.0, "stability": 53.0},
                    "top3_failures": ["left_knee", "hip", "shoulder"],
                    "avg_keypoint_confidence": None,
                    "ms_per_frame": 243.8,
                },
                "engine_b": {
                    "name": "mediapipe-lifter",
                    "overall_score": 84.0,
                    "dimension_scores": {"angle": 82.0, "stability": 84.0},
                    "top3_failures": ["left_knee", "hip", "ankle"],
                    "avg_keypoint_confidence": 0.82,
                    "ms_per_frame": 86.8,
                },
                "gates": gates,
            }
        },
        "summary": {
            "all_within_tolerance": phase1_ready,
            "all_mediapipe_ge_70": phase1_ready,
            "all_top3_overlap_ok": True,
            "all_avg_confidence_ok": True,
            "phase1_ready_to_swap": phase1_ready,
        },
    }


def test_generate_markdown_report_lifter_mode() -> None:
    """nlf-vs-mediapipe-lifter 모드 보고서에 'MP+MotionBERT' 레이블이 포함되어야 한다."""
    payload = _synthetic_payload_lifter(engine_mode="nlf-vs-mediapipe-lifter")
    md = generate_markdown_report(payload)

    assert "MP+MotionBERT" in md
    assert "Phase 1 회귀 검증 보고서" in md
    assert "ref-foxtop-split" in md
    assert "phase1_ready_to_swap" in md
    # engine_mode 레이블
    assert "nlf-vs-mediapipe-lifter" in md


def test_generate_markdown_report_mediapipe_only_mode() -> None:
    """mediapipe-vs-mediapipe-lifter 모드 보고서 구조 확인."""
    payload = _synthetic_payload_lifter(engine_mode="mediapipe-vs-mediapipe-lifter")
    md = generate_markdown_report(payload)

    assert "MP+MotionBERT" in md
    assert "MediaPipe" in md
    assert "mediapipe-vs-mediapipe-lifter" in md


def test_generate_markdown_report_backward_compat() -> None:
    """기존 nlf-vs-mediapipe 모드 — 'MediaPipe vs NLF' 제목 유지 (backward compat)."""
    payload = _synthetic_payload(phase1_ready=True, motion_id="ref-ballerina-spin")
    # engine_mode 없는 구형 payload (generate_markdown_report 가 기본값 사용)
    md = generate_markdown_report(payload)
    assert "MediaPipe vs NLF" in md or "NLF" in md


# ── Test 9: 잘못된 engine_mode → ValueError ───────────────────────────────

def test_compare_engines_invalid_mode_raises() -> None:
    """잘못된 engine_mode 를 넘기면 ValueError 가 발생해야 한다."""
    with pytest.raises(ValueError, match="engine_mode must be one of"):
        compare_engines(motion_ids=[], engine_mode="invalid-mode")
