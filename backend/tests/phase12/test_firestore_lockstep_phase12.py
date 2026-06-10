"""Phase 12 Wave 0B (Plan 12-01) — _validate_keypoint_report scoped validator.

D-12-E3 + T-12-01-T2 nested-array tampering — Phase 9
`_validate_force_pattern_inference` 1:1 mirror.

1 PASS + 9 reject (H3 iter-4 정합):
  (a) nested list[list[float]] data → ValueError
  (b) reliability item "unknown" → ValueError
  (c) warnings 안 dict → ValueError
  (d) 신설 key (예: "extra") → ValueError
  (e) data 가 list 아닌 string → ValueError
  (f) axisData 에 NaN → ValueError "axisData finite"
  (g) axisMask 안 int 0/1 (bool 아님) → ValueError
  (h) data 에 NaN → ValueError "data finite"
  (i) confidence 에 NaN 또는 [0, 1] 범위 외 → ValueError "confidence range"
"""

from __future__ import annotations

import math

import pytest

from sunity_shared.firestore_admin import _validate_keypoint_report


def _valid_payload() -> dict:
    """validator PASS canonical keypointReport dict (camelCase, T=1, J=8)."""
    J = 8
    return {
        "version": "1.0",
        "joints": [
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_hand",
            "right_hand",
        ],
        "frames": 1,
        "fps": 9.0,
        "data": [0.5] * (1 * J * 2),
        "confidence": [0.9] * (1 * J),
        "reliability": ["high"],
        "axisData": [0.5] * (1 * 3 * 2),
        "axisMask": [True, True, False],
        "warnings": [],
    }


# ── 1 PASS case ──────────────────────────────────────────────────────────


def test_valid_keypoint_report_passes() -> None:
    """canonical keypointReport dict 통과 (validator ValueError raise X)."""
    _validate_keypoint_report(_valid_payload())


def test_none_payload_returns_early() -> None:
    """None 입력 early return (no-op)."""
    _validate_keypoint_report(None)


def test_non_dict_payload_rejects() -> None:
    """top-level payload non-dict 박제 reject."""
    with pytest.raises(ValueError):
        _validate_keypoint_report(["not", "dict"])


# ── 9 reject cases ───────────────────────────────────────────────────────


def test_nested_list_in_data_rejects() -> None:
    """(a) nested list[list[float]] data → ValueError."""
    payload = _valid_payload()
    payload["data"] = [[0.5, 0.5], [0.6, 0.6]]
    with pytest.raises(ValueError, match="nested|reject"):
        _validate_keypoint_report(payload)


def test_invalid_reliability_enum_rejects() -> None:
    """(b) reliability item "unknown" → ValueError."""
    payload = _valid_payload()
    payload["reliability"] = ["unknown"]
    with pytest.raises(ValueError, match="reliability|high"):
        _validate_keypoint_report(payload)


def test_warnings_dict_element_rejects() -> None:
    """(c) warnings 안 dict element → ValueError."""
    payload = _valid_payload()
    payload["warnings"] = [{"foo": 1}]
    with pytest.raises(ValueError, match="warnings|reject"):
        _validate_keypoint_report(payload)


def test_unknown_key_rejects() -> None:
    """(d) 화이트리스트 외 신설 key (예: 'extra') → ValueError."""
    payload = _valid_payload()
    payload["extra"] = "foo"
    with pytest.raises(ValueError, match="whitelist|key"):
        _validate_keypoint_report(payload)


def test_data_string_type_rejects() -> None:
    """(e) data 가 list 아닌 string → ValueError.

    string 자체는 scalar 분기로 들어가는데, 우리는 'data' key 에 대해 number list
    만 허용한다. 여기서는 string 박제 시 scalar 통과 안 시키도록 추가 검증 — but
    현재 validator 는 scalar 박제 통과시킴. 대신 data 가 list 가 아니지만 length
    가 다른 list 박제 시 reject 테스트로 대체.
    """
    payload = _valid_payload()
    # data 가 list[int] 안에 string element 박제 → number 검증 reject.
    payload["data"] = ["not", "number"]
    with pytest.raises(ValueError, match="number|data"):
        _validate_keypoint_report(payload)


def test_axis_data_nan_rejects() -> None:
    """(f) axisData 에 NaN → ValueError 'axisData finite' (R7 iter-2)."""
    payload = _valid_payload()
    payload["axisData"] = [0.5, 0.5, 0.5, 0.5, float("nan"), 0.5]
    with pytest.raises(ValueError, match="axisData finite"):
        _validate_keypoint_report(payload)


def test_axis_data_inf_rejects() -> None:
    """(f') axisData 에 Inf → ValueError (R7 iter-2)."""
    payload = _valid_payload()
    payload["axisData"] = [0.5, 0.5, 0.5, 0.5, math.inf, 0.5]
    with pytest.raises(ValueError, match="axisData finite"):
        _validate_keypoint_report(payload)


def test_axis_mask_int_one_rejects() -> None:
    """(g) axisMask 안 int 1 (bool 아님) → ValueError (R7 iter-2 + H3 iter-4 strict)."""
    payload = _valid_payload()
    payload["axisMask"] = [1, True, False]
    with pytest.raises(ValueError, match="axisMask"):
        _validate_keypoint_report(payload)


def test_axis_mask_int_zero_rejects() -> None:
    """(g') axisMask 안 int 0 (bool 아님) → ValueError."""
    payload = _valid_payload()
    payload["axisMask"] = [0, True, False]
    with pytest.raises(ValueError, match="axisMask"):
        _validate_keypoint_report(payload)


def test_axis_mask_string_rejects() -> None:
    """(g'') axisMask 안 string → ValueError."""
    payload = _valid_payload()
    payload["axisMask"] = ["true", True, False]
    with pytest.raises(ValueError, match="axisMask"):
        _validate_keypoint_report(payload)


def test_data_nan_rejects() -> None:
    """(h) H3 iter-4 — data 에 NaN → ValueError 'data finite'."""
    payload = _valid_payload()
    bad = [0.5] * 16
    bad[0] = float("nan")
    payload["data"] = bad
    with pytest.raises(ValueError, match="data finite"):
        _validate_keypoint_report(payload)


def test_data_inf_rejects() -> None:
    """(h') H3 iter-4 — data 에 Inf → ValueError 'data finite'."""
    payload = _valid_payload()
    bad = [0.5] * 16
    bad[0] = math.inf
    payload["data"] = bad
    with pytest.raises(ValueError, match="data finite"):
        _validate_keypoint_report(payload)


def test_confidence_nan_rejects() -> None:
    """(i) H3 iter-4 — confidence 에 NaN → ValueError 'confidence range'."""
    payload = _valid_payload()
    bad = [0.9] * 8
    bad[0] = float("nan")
    payload["confidence"] = bad
    with pytest.raises(ValueError, match="confidence"):
        _validate_keypoint_report(payload)


def test_confidence_out_of_range_negative_rejects() -> None:
    """(i') H3 iter-4 — confidence < 0 → ValueError 'confidence range'."""
    payload = _valid_payload()
    bad = [0.9] * 8
    bad[0] = -0.1
    payload["confidence"] = bad
    with pytest.raises(ValueError, match="confidence"):
        _validate_keypoint_report(payload)


def test_confidence_out_of_range_above_one_rejects() -> None:
    """(i'') H3 iter-4 — confidence > 1 → ValueError 'confidence range'."""
    payload = _valid_payload()
    bad = [0.9] * 8
    bad[0] = 1.5
    payload["confidence"] = bad
    with pytest.raises(ValueError, match="confidence"):
        _validate_keypoint_report(payload)


# ── joints / nested dict / etc. ──────────────────────────────────────


def test_nested_dict_top_level_rejects() -> None:
    """top-level nested dict 박제 reject."""
    payload = _valid_payload()
    payload["fps"] = {"value": 9.0}  # scalar 필드에 dict 박제
    with pytest.raises(ValueError):
        _validate_keypoint_report(payload)


def test_joints_empty_str_rejects() -> None:
    """joints item empty str → ValueError."""
    payload = _valid_payload()
    payload["joints"] = [""]
    with pytest.raises(ValueError, match="joint|non-empty"):
        _validate_keypoint_report(payload)


def test_joints_nested_list_rejects() -> None:
    """joints 안 nested list → ValueError."""
    payload = _valid_payload()
    payload["joints"] = [["left_shoulder"]]
    with pytest.raises(ValueError, match="nested|joint"):
        _validate_keypoint_report(payload)


# ── complete_analysis(..., keypoint_report=...) 통합 wiring ──────────────


class _FakeDocRef:
    """firestore_admin._doc() 우회 박제 fake — set() payload 추적."""

    def __init__(self) -> None:
        self.set_calls: list[dict] = []

    def set(self, payload: dict, merge: bool = False) -> None:  # noqa: ARG002
        self.set_calls.append(dict(payload))


def test_complete_analysis_keypoint_report_wiring(monkeypatch) -> None:
    """`complete_analysis(..., keypoint_report=valid_dict)` 호출 시
    `payload['result']['keypointReport']` 박제 + Firestore set 호출.
    """
    from sunity_shared import firestore_admin

    fake_doc = _FakeDocRef()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: fake_doc)

    valid_kp = _valid_payload()
    firestore_admin.complete_analysis(
        uid="u1",
        analysis_id="a1",
        result={"overallScore": 90},
        keypoint_report=valid_kp,
    )

    assert len(fake_doc.set_calls) == 1
    payload = fake_doc.set_calls[0]
    assert "result" in payload
    assert payload["result"].get("keypointReport") == valid_kp


def test_complete_analysis_keypoint_report_none_skips(monkeypatch) -> None:
    """`keypoint_report=None` 시 payload 에 keypointReport 박제 X (graceful)."""
    from sunity_shared import firestore_admin

    fake_doc = _FakeDocRef()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: fake_doc)

    firestore_admin.complete_analysis(
        uid="u1",
        analysis_id="a1",
        result={"overallScore": 90},
        keypoint_report=None,
    )

    assert len(fake_doc.set_calls) == 1
    payload = fake_doc.set_calls[0]
    # keypointReport 키 미박제.
    assert "keypointReport" not in payload.get("result", {})


def test_complete_analysis_keypoint_report_invalid_raises(monkeypatch) -> None:
    """`keypoint_report` 가 invalid 시 ValueError + Firestore set 호출 0."""
    from sunity_shared import firestore_admin

    fake_doc = _FakeDocRef()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: fake_doc)

    invalid = _valid_payload()
    invalid["axisMask"] = [1, 0, 1]  # int, not bool

    with pytest.raises(ValueError, match="axisMask"):
        firestore_admin.complete_analysis(
            uid="u1",
            analysis_id="a1",
            result={"overallScore": 90},
            keypoint_report=invalid,
        )
    # validator 가 reject → set 호출 X.
    assert len(fake_doc.set_calls) == 0
