"""quick-260801-gbk Task 2 — record 에 측정 순간 각인 (additive, 채점 무접촉).

_attach_translation_emission(measured_at=...) 가 record 에 atFrameIdx/atVideoSec 을
setdefault 로만 얹는지, 기존 키·값이 한 톨도 안 움직이는지를 본다.

각인 시점은 deduction_engine.tally 가 **끝난 뒤**다 — 점수를 만든 코드는 이 값을
볼 수 없다. 그것이 불변식 1(점수 무접촉)의 구조적 근거이고, 아래 테스트는 그
구조가 실제로 유지되는지를 값으로 확인한다.

Pod/S3/Firestore/Gemini 호출 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared import models  # noqa: E402
from sunity_shared.analysis import deduction_engine, vision_veto  # noqa: E402


def _record(criterion, **over):
    """계약 필수 11키를 갖춘 최소 record dict."""
    rec = {
        "criterion": criterion,
        "measuredValue": 40.0,
        "baselineValue": 180.0,
        "baselineKind": None,
        "deviation": 20.0,
        "ruleId": f"{criterion}_over_tol_linear",
        "points": -12.0,
        "unit": "deg",
        "ipsfAnchor": "engineering_interpretation",
        "source": "geometry",
        "deviationSource": "ipsf_absolute",
    }
    rec.update(over)
    return rec


def _result(records):
    return {"deductionBreakdown": {"baseline": 100, "records": records, "final": 88}}


def _emit(result, measured_at):
    app._attach_translation_emission(
        result, mode="mode1", motion_id=None, prev_doc=None,
        uid="u", analysis_id="a", measured_at=measured_at,
    )


# ── 각인 additive ───────────────────────────────────────────────────────────


def test_engraving_leaves_every_pre_existing_key_untouched():
    """필수 11키 + cap 2키 + track 값이 각인 전후로 완전히 동일하다."""
    rec = _record(
        "leg_extension", rawPoints=-24.0, capApplied=True, track="critical"
    )
    before = dict(rec)
    result = _result([rec])
    _emit(result, {"leg_extension": {"frame_idx": 7, "video_sec": 0.7}})
    for k, v in before.items():
        assert rec[k] == v, f"{k} 가 각인으로 움직였다"
    assert rec["atFrameIdx"] == 7
    assert rec["atVideoSec"] == pytest.approx(0.7)


def test_only_records_with_a_moment_get_the_keys():
    """measured_at 에 항목이 있는 record 만 필드를 얻는다."""
    legs = _record("leg_extension")
    reach = _record("body_relative_reach", unit="notch",
                    deviationSource="reference_relative")
    result = _result([legs, reach])
    _emit(result, {"leg_extension": {"frame_idx": 3, "video_sec": 0.3}})
    assert "atFrameIdx" in legs
    assert "atFrameIdx" not in reach
    assert "atVideoSec" not in reach


def test_none_and_empty_measured_at_are_safe():
    """measured_at=None / 빈 dict 로도 크래시 0, record 형상 종전 유지."""
    for arg in (None, {}):
        rec = _record("line")
        before = dict(rec)
        _emit(_result([rec]), arg)
        assert "atFrameIdx" not in rec
        assert "atVideoSec" not in rec
        for k, v in before.items():
            assert rec[k] == v


def test_values_are_flat_scalars_of_the_right_type():
    """atFrameIdx=int / atVideoSec=float — 중첩 배열·dict 0 (Firestore flat 제약)."""
    rec = _record("arm_extension")
    _emit(_result([rec]), {"arm_extension": {"frame_idx": 11, "video_sec": 1.25}})
    assert isinstance(rec["atFrameIdx"], int) and not isinstance(rec["atFrameIdx"], bool)
    assert isinstance(rec["atVideoSec"], float)


def test_setdefault_never_overwrites_an_existing_value():
    """이미 값이 있으면 각인이 덮지 않는다 (기존 키 무변경 규율)."""
    rec = _record("line", atFrameIdx=2, atVideoSec=0.2)
    _emit(_result([rec]), {"line": {"frame_idx": 99, "video_sec": 9.9}})
    assert rec["atFrameIdx"] == 2
    assert rec["atVideoSec"] == pytest.approx(0.2)


def test_malformed_moment_entry_is_ignored():
    """frame_idx 가 비수치면 그 record 는 필드를 얻지 않는다 (fail-closed)."""
    rec = _record("line")
    _emit(_result([rec]), {"line": {"frame_idx": "3", "video_sec": None}})
    assert "atFrameIdx" not in rec
    assert "atVideoSec" not in rec


# ── vision 주입 split record 는 순간을 얻지 못한다 (D-gbk-07) ────────────────


def test_vision_injected_split_record_has_no_moment():
    """엔진이 vision 주입으로 만든 split_angle record 에 순간 필드가 없다.

    이 record 의 measuredValue 는 Gemini 추정이다 — 우리가 그 프레임에서 재지
    않았으므로 "여기서 쟀다" 계약을 붙일 수 없다. 빌더 out-param 이 split 을
    아예 채우지 않으므로 fail-closed 는 추가 코드 없이 성립한다.
    """
    diff = {
        "body_part": "스플릿", "correct_state": "", "fault_state": "벌어짐 부족",
        "severity": "moderate", "approx_angle_deviation_deg": 30.0,
    }
    quant = vision_veto.VisionQuantificationResult(
        quantificationStatus="available", angleDeltas=None,
        bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=(),
    )
    breakdown = deduction_engine.tally(
        quant, {"supported_differences": [diff]},
        dimension_overall=80, measured_deviations={},
        dimension_scores=None, baseline_kind="hip_line",
    )
    split = [r for r in breakdown.records if r.criterion == "split_angle"]
    assert len(split) == 1
    assert split[0].source == "vision"
    records = [r.to_dict() for r in breakdown.records]
    # 빌더가 split 순간을 만들지 않았으므로 measured_at 에도 항목이 없다.
    _emit(_result(records), {})
    for rec in records:
        if rec["criterion"] == "split_angle":
            assert "atFrameIdx" not in rec
            assert "atVideoSec" not in rec


# ── 계약 집합 ───────────────────────────────────────────────────────────────


def test_moment_keys_are_disjoint_from_every_other_record_key_set():
    """4번째 집합이 기존 3집합과 겹치지 않는다 (lockstep 전제)."""
    moment = set(models.DEDUCTION_RECORD_MOMENT_KEYS)
    assert moment == {"atFrameIdx", "atVideoSec"}
    for other in (
        models.DEDUCTION_RECORD_KEYS,
        models.DEDUCTION_RECORD_OPTIONAL_KEYS,
        models.DEDUCTION_RECORD_EXTENSION_KEYS,
    ):
        assert not moment & set(other)
