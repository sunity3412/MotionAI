"""Phase 3 (Plan 03-01) — BodyProfile 자가입력 계약 + graceful normalize 검증.

대상:
  · models.normalize_body_profile — 부분/없음/잘못된 입력 graceful (D-06, SC#4).
  · pipeline _build_coach_context — bodyProfile context 키 graceful (D-04 seam).

normalize_body_profile 는 owner-write client 값(HTTP 검증 아님)이라 raise 하지
않고 None/정상값을 반환한다 (validation.py 의 validate_upload_request 와 대비).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# sunity_shared import 경로 (Lambda Layer /opt/python 미러).
_LAYER = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared import models  # noqa: E402


# ─────────────────── normalize_body_profile ───────────────────


class TestNormalizeBodyProfile:
    def test_none_returns_none(self) -> None:
        assert models.normalize_body_profile(None) is None

    def test_empty_dict_returns_none(self) -> None:
        # 전 필드 빈 → 전체 None.
        assert models.normalize_body_profile({}) is None

    def test_non_dict_returns_none(self) -> None:
        # 방어 — list/str/숫자 입력도 crash 없이 None.
        assert models.normalize_body_profile([1, 2, 3]) is None  # type: ignore[arg-type]
        assert models.normalize_body_profile("xxx") is None  # type: ignore[arg-type]

    def test_partial_height_only(self) -> None:
        out = models.normalize_body_profile({"heightCm": 165})
        assert out is not None
        assert out["heightCm"] == 165
        assert out["weightKg"] is None
        assert out["experience"] is None
        assert out["dominantHand"] is None
        assert out["painAreas"] == []

    def test_unknown_experience_enum_dropped(self) -> None:
        out = models.normalize_body_profile({"experience": "pro"})
        # 알 수 없는 enum → experience None. 전 필드 None 이므로 전체 None.
        assert out is None

    def test_valid_experience_kept(self) -> None:
        out = models.normalize_body_profile({"experience": "intermediate"})
        assert out is not None
        assert out["experience"] == "intermediate"

    def test_pain_areas_filters_non_string_and_non_member(self) -> None:
        out = models.normalize_body_profile(
            {"painAreas": ["shoulder", 3, "wrist", "xxx", None]}
        )
        assert out is not None
        assert out["painAreas"] == ["shoulder", "wrist"]

    def test_unknown_keys_ignored(self) -> None:
        out = models.normalize_body_profile({"heightCm": 170, "bogusKey": "x"})
        assert out is not None
        assert "bogusKey" not in out
        assert out["heightCm"] == 170

    def test_height_out_of_range_dropped(self) -> None:
        assert models.normalize_body_profile({"heightCm": 5}) is None
        assert models.normalize_body_profile({"heightCm": 9999}) is None

    def test_weight_out_of_range_dropped(self) -> None:
        assert models.normalize_body_profile({"weightKg": 9999}) is None
        assert models.normalize_body_profile({"weightKg": 5}) is None

    def test_weight_in_range_kept(self) -> None:
        out = models.normalize_body_profile({"weightKg": 60})
        assert out is not None
        assert out["weightKg"] == 60

    def test_dominant_hand_enum(self) -> None:
        assert models.normalize_body_profile({"dominantHand": "left"})["dominantHand"] == "left"  # type: ignore[index]
        assert models.normalize_body_profile({"dominantHand": "sideways"}) is None

    def test_non_numeric_height_dropped(self) -> None:
        # bool 은 int subclass 이므로 명시 거부, 문자열도 거부.
        assert models.normalize_body_profile({"heightCm": "170"}) is None
        assert models.normalize_body_profile({"heightCm": True}) is None

    def test_full_profile_roundtrip(self) -> None:
        out = models.normalize_body_profile(
            {
                "heightCm": 165,
                "weightKg": 55,
                "experience": "advanced",
                "painAreas": ["shoulder", "wrist"],
                "dominantHand": "right",
            }
        )
        assert out == {
            "heightCm": 165,
            "weightKg": 55,
            "experience": "advanced",
            "painAreas": ["shoulder", "wrist"],
            "dominantHand": "right",
        }
