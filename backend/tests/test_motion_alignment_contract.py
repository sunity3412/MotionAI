"""Phase 28 (ALGN-01) — motionAlignment 계약 validator + 3-way lockstep 테스트.

검증 대상:
  1. `firestore_admin._validate_motion_alignment` scoped validator behavior
     (유효/None/nested/상한/비단조/미등재 tier/NaN + tier↔anchors 역불변식 3케이스).
  2. 3-way lockstep(텍스트 대조 쪽 — B1): models.MOTION_ALIGNMENT_KEYS 각 키가
     app/src/types/analysis.ts MotionAlignment 소스에 존재.
  3. RATE 클램프 lockstep(W4): app/src/lib/alignmentWarp.ts 의
     RATE_MIN=0.5 / RATE_MAX=2.0 (belle 고정값, 28-CONTEXT D-01).

B1 (병렬 wave 격리): 이 파일은 28-02 산출 알고리즘 모듈(sunity_shared.analysis 아래)을
불러오지 않는다. 상한 lockstep(모듈 MAX 상수 == models.MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS)
단언은 28-04 의 test_pipeline_motion_alignment.py(wave 3)로 이동됨. 여기서는 models/TS
텍스트 쪽 단독 검증만 수행한다(병렬 실행 시 collection error 회피).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TS_ANALYSIS = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_TS_WARP = _REPO_ROOT / "app" / "src" / "lib" / "alignmentWarp.ts"


def _valid_warped() -> dict:
    """유효 warped alignment — anchors 2쌍(u 단조 증가, r 비감소)."""
    return {
        "version": "ma-v1",
        "source": "dtw",
        "tier": "warped",
        "reason": None,
        "anchors": [0.0, 0.0, 1.0, 2.0],
        "anchorCount": 2,
        "distance": 5.0,
    }


# ── validator behavior ────────────────────────────────────────────────


def test_valid_warped_passes() -> None:
    """유효 dict (ma-v1, warped, anchors 4 float 단조) → raise 0."""
    firestore_admin._validate_motion_alignment(_valid_warped())


def test_none_passes() -> None:
    """None → 통과 (optional, legacy doc)."""
    firestore_admin._validate_motion_alignment(None)


def test_nested_anchors_raises_typeerror() -> None:
    """anchors 에 list 중첩 → TypeError (firestore-nested-array-flat)."""
    payload = _valid_warped()
    payload["anchors"] = [[0.0, 0.0], [1.0, 2.0]]
    with pytest.raises(TypeError):
        firestore_admin._validate_motion_alignment(payload)


def test_anchors_over_limit_raises_valueerror() -> None:
    """anchors 길이 513+ → ValueError (40k index-entry 상한)."""
    payload = _valid_warped()
    n = models.MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS + 2  # 짝수 유지, 상한 초과
    # 단조 u / 비감소 r 를 만족시키되 길이만 초과.
    anchors: list[float] = []
    for k in range(n // 2):
        anchors.extend([float(k), float(k)])
    payload["anchors"] = anchors
    payload["anchorCount"] = len(anchors) // 2
    with pytest.raises(ValueError):
        firestore_admin._validate_motion_alignment(payload)


def test_non_monotonic_u_raises_valueerror() -> None:
    """anchors u 비단조(감소) → ValueError."""
    payload = _valid_warped()
    payload["anchors"] = [1.0, 0.0, 0.5, 2.0]  # u: 1.0 -> 0.5 감소
    with pytest.raises(ValueError):
        firestore_admin._validate_motion_alignment(payload)


def test_unregistered_tier_raises_valueerror() -> None:
    """tier 미등재값 → ValueError."""
    payload = _valid_warped()
    payload["tier"] = "stretched"
    with pytest.raises(ValueError):
        firestore_admin._validate_motion_alignment(payload)


def test_key_outside_whitelist_raises_valueerror() -> None:
    """키 화이트리스트 밖 → ValueError."""
    payload = _valid_warped()
    payload["evilKey"] = 1
    with pytest.raises(ValueError):
        firestore_admin._validate_motion_alignment(payload)


def test_nan_anchor_raises_valueerror() -> None:
    """anchors 에 NaN → ValueError (finite 강제)."""
    payload = _valid_warped()
    payload["anchors"] = [0.0, 0.0, float("nan"), 2.0]
    with pytest.raises(ValueError):
        firestore_admin._validate_motion_alignment(payload)


def test_inf_anchor_raises_valueerror() -> None:
    """anchors 에 inf → ValueError (finite 강제)."""
    payload = _valid_warped()
    payload["anchors"] = [0.0, 0.0, 1.0, float("inf")]
    with pytest.raises(ValueError):
        firestore_admin._validate_motion_alignment(payload)


# ── 역불변식 (리뷰 MEDIUM-3) ──────────────────────────────────────────


def test_disabled_empty_anchors_passes() -> None:
    """tier=='disabled' + anchors==[] → 통과 (degenerate 방출 형상)."""
    payload = {
        "version": "ma-v1",
        "source": "dtw",
        "tier": "disabled",
        "reason": "insufficient_anchors",
        "anchors": [],
        "anchorCount": 0,
        "distance": 0.0,
    }
    firestore_admin._validate_motion_alignment(payload)


def test_warped_empty_anchors_raises_valueerror() -> None:
    """tier=='warped' + anchors==[] → ValueError (모순 데이터, 저장 전 거부)."""
    payload = _valid_warped()
    payload["anchors"] = []
    payload["anchorCount"] = 0
    with pytest.raises(ValueError):
        firestore_admin._validate_motion_alignment(payload)


def test_trim_only_single_pair_raises_valueerror() -> None:
    """tier=='trim_only' + anchors 1쌍(2 float) → ValueError (>=2쌍 필수)."""
    payload = _valid_warped()
    payload["tier"] = "trim_only"
    payload["anchors"] = [0.0, 1.0]
    payload["anchorCount"] = 1
    with pytest.raises(ValueError):
        firestore_admin._validate_motion_alignment(payload)


# ── 3-way lockstep 텍스트 대조 (B1 — models/TS 쪽 단독) ────────────────


def test_models_keys_present_in_ts_source() -> None:
    """models.MOTION_ALIGNMENT_KEYS 각 키가 analysis.ts MotionAlignment 소스에 존재."""
    src = _TS_ANALYSIS.read_text(encoding="utf-8")
    for key in models.MOTION_ALIGNMENT_KEYS:
        assert re.search(rf"\b{re.escape(key)}\b", src), (
            f"MOTION_ALIGNMENT_KEYS 의 '{key}' 가 analysis.ts 에 없음 — "
            f"3-way lockstep drift"
        )


def test_motion_alignment_tiers_present_in_ts_source() -> None:
    """MOTION_ALIGNMENT_TIERS 각 값이 analysis.ts MotionAlignment 소스에 존재."""
    src = _TS_ANALYSIS.read_text(encoding="utf-8")
    for tier in models.MOTION_ALIGNMENT_TIERS:
        assert f"'{tier}'" in src, (
            f"MOTION_ALIGNMENT_TIERS 의 '{tier}' 가 analysis.ts 에 없음"
        )


def test_rate_clamp_lockstep_alignmentwarp() -> None:
    """W4 — alignmentWarp.ts 의 RATE_MIN=0.5 / RATE_MAX=2.0 (belle 고정값)."""
    src = _TS_WARP.read_text(encoding="utf-8")
    m_min = re.search(r"RATE_MIN\s*=\s*([0-9]*\.?[0-9]+)", src)
    m_max = re.search(r"RATE_MAX\s*=\s*([0-9]*\.?[0-9]+)", src)
    assert m_min is not None, "alignmentWarp.ts 에 RATE_MIN 선언 없음"
    assert m_max is not None, "alignmentWarp.ts 에 RATE_MAX 선언 없음"
    assert float(m_min.group(1)) == 0.5, "RATE_MIN 은 belle 고정값 0.5 여야 함 (D-01)"
    assert float(m_max.group(1)) == 2.0, "RATE_MAX 는 belle 고정값 2.0 여야 함 (D-01)"
