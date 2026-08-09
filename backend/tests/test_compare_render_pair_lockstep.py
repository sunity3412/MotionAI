"""사이각 수치 짝 lockstep (quick-260809-jnb — belle 08-09 실기기 반려).

반려 증상: 합성 비교 영상의 정지 화면에서 **내 자세 패널에만 "48°"** 가 찍히고
정은지 선수 패널에는 수치가 없었다 ("얘만 각도 수치 비교가 없네"). 원인은 두 패널이
각자 keypoint 신뢰(>=0.5) 게이트를 따로 통과하는 구조 — 한쪽만 통과하면 한쪽만
숫자가 남고, 혼자 있는 수치는 비교가 아니라 오독이 된다.

여기서 지키는 불변식: **수치는 양쪽 다 있거나 양쪽 다 없다.**
쐐기·호(무엇을 보라)는 신뢰와 무관하게 남아야 하므로 좌표 필드는 무접촉.
"""

from __future__ import annotations

from sunity_shared.analysis.compare_render import _pair_lockstep_degrees


def _panel(deg: float | None) -> dict:
    return {"v": [0.5, 0.5], "a": [0.6, 0.4], "b": [0.4, 0.6], "deg": deg}


def test_both_present_passes_through_unchanged() -> None:
    viz = {"user": _panel(48.0), "ref": _panel(61.0)}
    out = _pair_lockstep_degrees(viz)
    assert out["user"]["deg"] == 48.0
    assert out["ref"]["deg"] == 61.0


def test_ref_missing_degree_suppresses_user_degree() -> None:
    """belle 반려 그 경우 — 내 자세만 48°, 기준은 신뢰 미달."""
    viz = {"user": _panel(48.0), "ref": _panel(None)}
    out = _pair_lockstep_degrees(viz)
    assert out["user"]["deg"] is None
    assert out["ref"]["deg"] is None


def test_user_missing_degree_suppresses_ref_degree() -> None:
    viz = {"user": _panel(None), "ref": _panel(61.0)}
    out = _pair_lockstep_degrees(viz)
    assert out["user"]["deg"] is None
    assert out["ref"]["deg"] is None


def test_geometry_fields_survive_suppression() -> None:
    """수치만 지운다 — 쐐기·호를 그리는 좌표는 그대로여야 지목이 남는다."""
    viz = {"user": _panel(48.0), "ref": _panel(None)}
    out = _pair_lockstep_degrees(viz)
    for key in ("user", "ref"):
        assert out[key]["v"] == [0.5, 0.5]
        assert out[key]["a"] == [0.6, 0.4]
        assert out[key]["b"] == [0.4, 0.6]


def test_input_dict_not_mutated() -> None:
    """순수 함수 — 호출측이 원본을 재사용해도 안전."""
    viz = {"user": _panel(48.0), "ref": _panel(None)}
    _pair_lockstep_degrees(viz)
    assert viz["user"]["deg"] == 48.0


def test_none_and_missing_panel_are_left_to_upstream_rule() -> None:
    """패널 자체 부재는 상위 both-or-neither 담당 — 여기서 형태를 바꾸지 않는다."""
    assert _pair_lockstep_degrees(None) is None
    viz = {"user": _panel(48.0), "ref": None}
    assert _pair_lockstep_degrees(viz) is viz
