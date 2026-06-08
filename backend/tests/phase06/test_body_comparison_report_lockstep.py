"""Task 5: 3-way contract lockstep — TS + Python + docs/contract.md §8/§8.2 drift defense.

CLAUDE.md Cross-cutting 룰: BodyComparisonReport / BodyComparisonSourcePose 변경 시
세 곳 동시 갱신 — 본 테스트가 drift 를 방어.

W1 (2026-06-08): 3 ComparisonType + usedReferenceFallback boolean.
C14 (2026-06-08 reviews): deficit code 'pose_reliability_low' (IPSF
  judge-observation 'bad_angle' 과 의미 다름).
R2 (2026-06-08 round-2 reviews): BodyComparisonSourcePose 신규 — Firestore reference
  컬렉션 영속, flat values (nested-array 회피).
"""

from __future__ import annotations

import re
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TS_PATH = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_PY_MODELS_PATH = (
    _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared" / "models.py"
)
_PY_BODY_NORMALIZER_PATH = (
    _REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "body_normalizer.py"
)
_CONTRACT_PATH = _REPO_ROOT / "docs" / "contract.md"


# BodyComparisonReport 9 필드 — TS camelCase ↔ Python snake_case.
_FIELD_MAP = {
    "comparisonType": "comparison_type",
    "bodyNormalizationConfidence": "body_normalization_confidence",
    "scaleProfile": "scale_profile",
    "findings": "findings",
    "warnings": "warnings",
    "referenceMotionId": "reference_motion_id",
    "referenceAthleteName": "reference_athlete_name",
    "previousAnalysisId": "previous_analysis_id",
    "usedReferenceFallback": "used_reference_fallback",  # W1
}

# BodyComparisonSourcePose 6 필드 (R2 fix).
_SOURCE_POSE_FIELD_MAP = {
    "jointKeys": "joint_keys",
    "values": "values",
    "frameIndex": "frame_index",
    "torsoPx": "torso_px",
    "confidence": "confidence",
    "measuredAt": "measured_at",
}


# ── Test 1: TS BodyComparisonReport interface + 9 필드 + ComparisonType 3 cases ──


def test_ts_body_comparison_report_interface() -> None:
    src = _TS_PATH.read_text(encoding="utf-8")
    assert "interface BodyComparisonReport" in src
    # 3 ComparisonType (W1)
    assert (
        "type ComparisonType" in src
        and "'mode1'" in src
        and "'mode3_first'" in src
        and "'mode3_progress'" in src
    )
    # 9 필드 (camelCase)
    for camel in _FIELD_MAP:
        assert camel in src, f"TS analysis.ts BodyComparisonReport.{camel} 누락"


# ── Test 2: Python re-export consistency ──────────────────────────────


def test_python_re_export_consistency() -> None:
    src = _PY_MODELS_PATH.read_text(encoding="utf-8")
    # R2 — BodyComparisonSourcePose 포함
    for name in (
        "BodyComparisonReport",
        "BodyComparisonFinding",
        "BodyComparisonSourcePose",
        "ScaleProfile",
        "ComparisonType",
    ):
        assert name in src, f"models.py re-export 에 '{name}' 누락"
    assert "from .analysis.body_normalizer import" in src


# ── Test 3: docs/contract.md §8 ──────────────────────────────────────


def test_docs_contract_md_section_8() -> None:
    src = _CONTRACT_PATH.read_text(encoding="utf-8")
    assert "## §8. BodyComparisonReport" in src
    # 3 ComparisonType union
    assert "'mode1'" in src and "'mode3_first'" in src and "'mode3_progress'" in src
    # usedReferenceFallback
    assert "usedReferenceFallback" in src
    # 8 warning enum (reference_source_pose_missing — R2 fix)
    for w in (
        "low_confidence_normalization_off",
        "foreshortening_off",
        "shoulder_hip_ratio_off",
        "temporal_variance_high",
        "spatial_dispersion_high",
        "reference_profile_missing",
        "fallback_reference_not_found",
        "reference_source_pose_missing",  # R2 fix
    ):
        assert w in src, f"contract.md §8 warning enum '{w}' 누락"
    # C14 IPSF divergence note (§8.1)
    assert "§8.1" in src
    assert (
        "pose_reliability_low" in src and "bad_angle" in src
    ), "C14 IPSF divergence note (pose_reliability_low vs bad_angle) 누락"
    # §8.2 BodyComparisonSourcePose 명세 (R2 fix)
    assert "## §8.2 BodyComparisonSourcePose" in src
    assert "flat float array" in src, "§8.2 nested-array 회피 명시 누락"


# ── Test 4: TS camelCase ↔ Python snake_case 양방향 lockstep ───────


def test_camelcase_snake_case_field_map() -> None:
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    py_src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")
    for camel, snake in _FIELD_MAP.items():
        assert camel in ts_src, f"TS 에 BodyComparisonReport.{camel} 누락"
        assert snake in py_src, f"Python body_normalizer.py 에 {snake} 누락"


# ── Test 5: 4번째 case 'mode3_first_with_fallback' 금지 (W1) ────────


def test_no_legacy_mode3_first_with_fallback() -> None:
    """TS + Python + docs 모두에 mode3_first_with_fallback 부재 (W1 fix)."""
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    py_src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")
    contract_src = _CONTRACT_PATH.read_text(encoding="utf-8")
    # contract 는 'mode3_first_with_fallback' 같은 4번째 케이스 금지 명시.
    # 단, "4번째 케이스 금지" 라는 부정 표현 자체는 contract 에 있을 수 있음.
    # → enum literal 형태 ('mode3_first_with_fallback') 만 부재 검증.
    pattern = re.compile(r"['\"]mode3_first_with_fallback['\"]")
    assert not pattern.search(ts_src), "TS 에 'mode3_first_with_fallback' 발견 (W1 위반)"
    assert not pattern.search(py_src), "Python 에 'mode3_first_with_fallback' 발견 (W1 위반)"
    # contract.md 는 enum literal 로 표시할 일 없음. literal-only 검증.
    assert not pattern.search(contract_src), "docs 에 'mode3_first_with_fallback' literal 발견 (W1 위반)"


# ── Test 6 (C14): pose_reliability_low present + bad_angle absent ───


def test_pose_reliability_low_present_bad_angle_absent() -> None:
    """TS + docs 에 'pose_reliability_low' 존재. body_normalizer.py 에는
    'bad_angle' literal string 부재."""
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    contract_src = _CONTRACT_PATH.read_text(encoding="utf-8")
    py_src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")

    assert "pose_reliability_low" in ts_src
    assert "pose_reliability_low" in contract_src

    # body_normalizer.py 의 비주석/비docstring 코드에 "bad_angle" double-quoted literal 부재
    # (plan grep gate 정합 — 단순 string literal 만 검사. 단일 quote 의 historical
    # 설명 docstring 은 허용 — C14 fix 의 의미 설명용.)
    py_non_comment = "\n".join(
        line for line in py_src.splitlines() if not line.lstrip().startswith("#")
    )
    pattern_double_quoted = re.compile(r'"bad_angle"')
    assert not pattern_double_quoted.search(py_non_comment), (
        "body_normalizer.py 에 \"bad_angle\" double-quoted literal 존재 — C14 fix 위반"
    )


# ── Test 7 (R2 fix): BodyComparisonSourcePose lockstep ────────────────


def test_body_comparison_source_pose_lockstep() -> None:
    """TS BodyComparisonSourcePose 6 필드 ↔ Python class 6 필드 ↔ docs §8.2."""
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    py_src = _PY_BODY_NORMALIZER_PATH.read_text(encoding="utf-8")
    contract_src = _CONTRACT_PATH.read_text(encoding="utf-8")

    assert "interface BodyComparisonSourcePose" in ts_src
    assert "class BodyComparisonSourcePose" in py_src
    assert "BodyComparisonSourcePose" in contract_src

    # 6 필드 camel/snake 양방향
    for camel, snake in _SOURCE_POSE_FIELD_MAP.items():
        assert camel in ts_src, f"TS BodyComparisonSourcePose.{camel} 누락"
        assert snake in py_src, f"Python BodyComparisonSourcePose.{snake} 누락"

    # ReferenceMotion.bodyComparisonSourcePose 필드
    assert "bodyComparisonSourcePose" in ts_src, (
        "TS ReferenceMotion.bodyComparisonSourcePose 필드 누락 (R2 fix)"
    )
