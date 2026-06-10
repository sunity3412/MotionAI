"""Plan 09-01 Wave 0 — _validate_force_pattern_inference scoped validator
(D-09-U5 / T-09-T2 nested-array tampering).

1 PASS + 13 reject (4 structural + 4 finding-level warning + 4 top-level warning +
1 unexpected-key) — iter-3 R3 + iter-5 R2 정합.

per Plan 09-01 must_haves + RESEARCH §"Pattern 5".
"""

from __future__ import annotations

import pytest

from sunity_shared.firestore_admin import _validate_force_pattern_inference


def _valid_finding() -> dict:
    """validator PASS 강제 - canonical finding dict (camelCase)."""
    return {
        "pattern": "release",
        "phase": "lock",
        "sourceSignal": "axis_tilt",
        "reason": "raw shoulder_tilt above ipsf 20deg",
        "interpretation": "정은지 선수 기준 패턴과 비교했을 때, 몸 중심 잡는 힘이 약해지는 모습이 보여요.",
        "confidence": 0.72,
        "jointHint": "몸 중심",
        "warnings": [],
    }


def _valid_payload() -> dict:
    """validator PASS 강제 - canonical top-level inference dict."""
    return {
        "version": "1.0",
        "findings": [_valid_finding()],
        "overallConfidence": "medium",
        "modeContext": "mode1",
        "warnings": [],
    }


# ── 1 PASS case ──────────────────────────────────────────────────────────


def test_valid_force_pattern_inference_passes() -> None:
    """canonical inference dict 통과 (validator 가 ValueError raise X)."""
    _validate_force_pattern_inference(_valid_payload())


# ── 4 structural reject cases ────────────────────────────────────────────


def test_nested_dict_in_finding_entry_rejects() -> None:
    """finding entry 안 nested dict 박제 reject."""
    payload = _valid_payload()
    payload["findings"][0]["nested"] = {"foo": 1}
    with pytest.raises(ValueError, match="nested dict|whitelist"):
        _validate_force_pattern_inference(payload)


def test_list_of_list_in_finding_warnings_rejects() -> None:
    """finding warnings = [[...]] 박제 reject (nested list reject)."""
    payload = _valid_payload()
    payload["findings"][0]["warnings"] = [["a", "b"]]
    with pytest.raises(ValueError):
        _validate_force_pattern_inference(payload)


def test_non_whitelist_list_in_finding_rejects() -> None:
    """finding entry 안 화이트리스트 외 list field (예: 'badList') 박제 reject."""
    payload = _valid_payload()
    # Add a list-typed field that's NOT in the camelCase whitelist (warnings only).
    # 'unexpectedList' is not a known finding key, so this gets caught by the
    # key whitelist gate first (which is correct per iter-5 R2).
    payload["findings"][0]["badList"] = ["x"]
    with pytest.raises(ValueError):
        _validate_force_pattern_inference(payload)


def test_non_scalar_warnings_entry_rejects() -> None:
    """finding warnings 에 dict element 박제 reject (non-scalar)."""
    payload = _valid_payload()
    payload["findings"][0]["warnings"] = [{"foo": 1}]
    with pytest.raises(ValueError):
        _validate_force_pattern_inference(payload)


# ── 4 finding-level warning strict cases (R2 / R10) ──────────────────────


@pytest.mark.parametrize("bad_value", [1, True, None, ""])
def test_finding_level_warnings_strict_rejects(bad_value) -> None:
    """finding warnings element 가 non-empty str 외 박제 (int / bool / None / '') reject.

    R2 iter-3 + R10 — Phase 9 warnings 는 contract 상 list[str] only.
    """
    payload = _valid_payload()
    payload["findings"][0]["warnings"] = [bad_value]
    with pytest.raises(ValueError, match="non-empty str|str"):
        _validate_force_pattern_inference(payload)


# ── 4 top-level warning strict cases (R2 / R10) ──────────────────────────


@pytest.mark.parametrize("bad_value", [1, True, None, ""])
def test_top_level_warnings_strict_rejects(bad_value) -> None:
    """top-level inference.warnings element 가 non-empty str 외 박제 reject.

    R2 iter-3 + R10 — top-level warnings 도 finding-level 과 동일 strictness.
    """
    payload = _valid_payload()
    payload["warnings"] = [bad_value]
    with pytest.raises(ValueError, match="non-empty str|str"):
        _validate_force_pattern_inference(payload)


# ── 1 unexpected-key reject case (iter-5 R2) ─────────────────────────────


def test_unexpected_key_in_finding_rejects() -> None:
    """finding dict 안 화이트리스트 외 key (예: 'unexpectedScalar') 박제 reject.

    R2 iter-5 — _FORCE_PATTERN_FINDING_KEYS 8 필드 strict 화이트리스트 검증.
    """
    payload = _valid_payload()
    payload["findings"][0]["unexpectedScalar"] = "x"
    with pytest.raises(ValueError, match="whitelist|key"):
        _validate_force_pattern_inference(payload)


# ── sanity — non-dict input ──────────────────────────────────────────────


def test_non_dict_payload_rejects() -> None:
    """top-level payload 가 dict 외 입력 박제 reject."""
    with pytest.raises(ValueError):
        _validate_force_pattern_inference(["not", "dict"])


def test_none_payload_returns_early() -> None:
    """None 입력 박제 early return (no-op) — Wave 1 stub path."""
    # exception X 강제.
    _validate_force_pattern_inference(None)


# ── findings list accepts list[dict] ─────────────────────────────────────


def test_findings_accepts_multiple_dicts() -> None:
    """top-level findings = list[dict] 박제 PASS (Top-3 까지 허용)."""
    payload = _valid_payload()
    payload["findings"] = [_valid_finding(), _valid_finding(), _valid_finding()]
    _validate_force_pattern_inference(payload)


def test_findings_length_over_three_rejects() -> None:
    """findings 길이 > 3 박제 reject (D-09-B4 fabrication 금지)."""
    payload = _valid_payload()
    payload["findings"] = [_valid_finding()] * 4
    with pytest.raises(ValueError, match="length > 3|fabrication"):
        _validate_force_pattern_inference(payload)
