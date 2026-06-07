"""TS ↔ Python ↔ contract.md 3-way lockstep 테스트 (Plan 01-19 Task 2).

CLAUDE.md Cross-cutting 룰: PoseFrame / BodyNormalizationProfile 변경 시
세 곳 동시 갱신 — 본 테스트가 drift 를 방어.

검증 대상:
  1. TS PoseFrame.bodyShape: BodyNormalizationProfile | null 필드 존재
     (app/src/types/analysis.ts).
  2. TS BodyNormalizationProfile interface 7개 필드 정의.
  3. Python models.py 의 PoseFrame 미러 / re-export 에 body_shape 반영.
  4. docs/contract.md 가 BodyNormalizationProfile 7개 필드 명세.
  5. TS camelCase ↔ Python snake_case 필드명 1:1 매핑.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TS_PATH = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_PY_MODELS_PATH = (
    _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared" / "models.py"
)
_CONTRACT_PATH = _REPO_ROOT / "docs" / "contract.md"


# 필드 매핑 — TS camelCase ↔ Python snake_case 1:1.
_FIELD_MAP = {
    "estimatedHeightScale": "estimated_height_scale",
    "armScale": "arm_scale",
    "legScale": "leg_scale",
    "torsoScale": "torso_scale",
    "shoulderHipRatio": "shoulder_hip_ratio",
    "confidence": "confidence",
    "warnings": "warnings",
}


def test_ts_pose_frame_has_body_shape_field() -> None:
    """TS PoseFrame interface 에 bodyShape: BodyNormalizationProfile | null."""
    src = _TS_PATH.read_text(encoding="utf-8")
    # bodyShape 가 PoseFrame interface 내부에 BodyNormalizationProfile | null 로 등장
    pattern = re.compile(
        r"bodyShape\s*:\s*BodyNormalizationProfile\s*\|\s*null"
    )
    assert pattern.search(src), (
        "PoseFrame interface 에 'bodyShape: BodyNormalizationProfile | null' "
        "필드 누락 (D-21)"
    )


def test_ts_body_normalization_profile_interface() -> None:
    """TS BodyNormalizationProfile interface 가 7개 필드를 정의."""
    src = _TS_PATH.read_text(encoding="utf-8")
    assert "interface BodyNormalizationProfile" in src, (
        "BodyNormalizationProfile interface 정의 누락"
    )
    # 7개 camelCase 필드 모두 등장
    for camel in _FIELD_MAP.keys():
        assert camel in src, (
            f"BodyNormalizationProfile.{camel} 필드 누락 — TS analysis.ts"
        )


def test_python_models_mirror_pose_frame_body_shape() -> None:
    """backend/shared/python/sunity_shared/models.py 에 body_shape 반영."""
    src = _PY_MODELS_PATH.read_text(encoding="utf-8")
    # body_shape 또는 BodyNormalizationProfile 둘 중 하나 이상 등장
    assert (
        "body_shape" in src or "BodyNormalizationProfile" in src
    ), (
        "models.py 가 body_shape / BodyNormalizationProfile 를 re-export "
        "또는 정의해야 함 (TS↔Python lockstep)"
    )


def test_contract_md_lists_body_normalization_profile_fields() -> None:
    """docs/contract.md 에 BodyNormalizationProfile 7개 필드 모두 명시."""
    src = _CONTRACT_PATH.read_text(encoding="utf-8")
    assert "BodyNormalizationProfile" in src, (
        "docs/contract.md 가 BodyNormalizationProfile 를 언급해야 함"
    )
    # 7개 필드 (camelCase 또는 snake_case 둘 중 하나라도) 등장
    for camel, snake in _FIELD_MAP.items():
        assert camel in src or snake in src, (
            f"contract.md 가 BodyNormalizationProfile.{camel}/{snake} "
            "필드를 명시해야 함"
        )


def test_ts_python_field_name_lockstep() -> None:
    """TS camelCase 7 ↔ Python snake_case 7 매핑 1:1."""
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    py_src = (
        _REPO_ROOT
        / "backend"
        / "shared"
        / "python"
        / "sunity_shared"
        / "analysis"
        / "body_normalization.py"
    ).read_text(encoding="utf-8")

    for camel, snake in _FIELD_MAP.items():
        assert camel in ts_src, (
            f"TS analysis.ts 에 BodyNormalizationProfile.{camel} 누락"
        )
        assert snake in py_src, (
            f"Python body_normalization.py 에 {snake} 필드 누락"
        )


# ── Phase 2 v5 박제: 추가 lockstep — string/regex 검증 (AST 아님, LOW-1 v4 호칭) ──

# 5종 warning enum (Phase 2 BODY-01 박제). 3 파일 모두 동일 문자열.
_WARNING_ENUM = (
    "low_keypoint_confidence",
    "occluded_endpoint",
    "insufficient_frames",
    "asymmetric_landmark_count",
    "pose_too_inverted",
)

_PY_BODY_NORM_PATH = (
    _REPO_ROOT
    / "backend"
    / "shared"
    / "python"
    / "sunity_shared"
    / "analysis"
    / "body_normalization.py"
)


def test_warnings_enum_lockstep_across_3_files() -> None:
    """5종 warning enum 이 contract.md / analysis.ts / body_normalization.py 3 파일에 등장.

    string/regex 검증 — AST 아님 (LOW-1 v4).
    """
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    py_src = _PY_BODY_NORM_PATH.read_text(encoding="utf-8")
    contract_src = _CONTRACT_PATH.read_text(encoding="utf-8")

    for enum_val in _WARNING_ENUM:
        assert enum_val in ts_src, (
            f"TS analysis.ts 에 warning enum '{enum_val}' 누락"
        )
        assert enum_val in py_src, (
            f"Python body_normalization.py 에 warning enum '{enum_val}' 누락"
        )
        assert enum_val in contract_src, (
            f"docs/contract.md 에 warning enum '{enum_val}' 누락"
        )


def test_estimated_height_scale_semantics_lockstep() -> None:
    """'torso-relative proportion heuristic' 표현이 3 파일 모두 등장 (M3).

    string/regex 검증 — AST 아님 (LOW-1 v4).
    """
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    py_src = _PY_BODY_NORM_PATH.read_text(encoding="utf-8")
    contract_src = _CONTRACT_PATH.read_text(encoding="utf-8")

    needle = "torso-relative proportion heuristic"
    assert needle in ts_src, (
        f"TS analysis.ts 에 '{needle}' (M3 박제) 누락"
    )
    assert needle in py_src, (
        f"Python body_normalization.py 에 '{needle}' (M3 박제) 누락"
    )
    assert needle in contract_src, (
        f"docs/contract.md 에 '{needle}' (M3 박제) 누락"
    )


def test_numeric_scale_contract_lockstep() -> None:
    """5 numeric scale 필드 contract — 'finite' + 'strictly positive' 3 파일 박제.

    MEDIUM-2 v5: __post_init__ validator 확장. 3 파일 모두 ≥1회 등장.
    """
    ts_src = _TS_PATH.read_text(encoding="utf-8")
    py_src = _PY_BODY_NORM_PATH.read_text(encoding="utf-8")
    contract_src = _CONTRACT_PATH.read_text(encoding="utf-8")

    for needle in ("finite", "strictly positive"):
        assert needle in ts_src, (
            f"TS analysis.ts 에 '{needle}' (MEDIUM-2 v5 박제) 누락"
        )
        assert needle in py_src, (
            f"Python body_normalization.py 에 '{needle}' (MEDIUM-2 v5 박제) 누락"
        )
        assert needle in contract_src, (
            f"docs/contract.md 에 '{needle}' (MEDIUM-2 v5 박제) 누락"
        )
