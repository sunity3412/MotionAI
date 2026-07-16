"""Phase 29 (29-03, D-08) — mode3 확대비교(zoom) 대상 선택 소스 회귀 테스트.

박제 정신 (29-CONTEXT D-08 + 29-PLAN-REVIEW HIGH-1):
  · mode3 zoom 카드 대상 = 이번 분석 deductionBreakdown 감점 record 의
    criterion id → region 매핑 (leg_extension/split_angle→legs, arm_extension→arms).
    구 |Δscore| top-2 (현재↔지난 per-joint score 차) 소스는 폐기.
  · kind == "improved" 는 어떤 경로에서도 방출 금지 — 개선 부위 축하 카드 = deferred.
  · 감점 record 0 → zoom 카드 0 = 의도된 동작 (4/5 빈 criteria 동작 자연 귀결).
  · line / dimension_overall_fallback 은 collective 전신 criterion — region 무투영
    (29-04 앱 helper 무투영 결정과 정합, 특정 부위 카드가 오도).
  · dtw_match / dtw_ref_fps 렌더 인자는 현행 유지 (28-05/CR-01 무회귀).

전부 mock-based — 실 S3 / 실 렌더 / 실 Firestore 호출 0. PYTHONPATH=shared/python.
"""

from __future__ import annotations

import sys
from pathlib import Path

# pipeline/app.py + shared layer path 주입 (test_pipeline_deduction_seam.py 관례).
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared.analysis import technique  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402

# 앱 REGION_MEMBER_KEYPOINTS 미러 (app/src/lib/deductionLabels.ts:90-96) —
# keypointReport 8-keypoint 이름공간. 이 집합과 zoom 방출 관절이 일치해야
# result.tsx:962-974 드릴다운 매칭(REGION_MEMBER_KEYPOINTS[region] 교집합) 성립.
_LEGS_MEMBERS = {"left_hip", "right_hip", "left_knee", "right_knee"}
_ARMS_MEMBERS = {"left_shoulder", "right_shoulder", "left_hand", "right_hand"}


# ── helpers ──────────────────────────────────────────────────────────────────


def _profile(name: str = "t") -> technique.TechniqueProfile:
    exp = {k: technique.JOINT_BENT_OK for k in JOINT_KEYS}
    return technique.TechniqueProfile(
        name=name, category="unknown", joint_expectations=exp
    )


def _rec(criterion: str) -> dict:
    """감점 record 스텁 — zoom 소스 선택엔 criterion 만 유의미 (DeductionRecord
    to_dict 형상, keypoint 필드 없음 — 29-PLAN-REVIEW HIGH-1)."""
    return {
        "criterion": criterion,
        "measuredValue": 100.0,
        "baselineValue": 180.0,
        "deviation": 80.0,
        "ruleId": "extension_gap",
        "points": -10.0,
        "unit": "deg",
        "ipsfAnchor": "test",
        "source": "geometry",
        "deviationSource": "ipsf_absolute",
    }


def _result(records=None, joints=None) -> dict:
    out: dict = {"overallScore": 80}
    if records is not None:
        out["deductionBreakdown"] = {"records": records, "final": 80}
    if joints is not None:
        out["joints"] = joints
    return out


def _prev(joints=None) -> dict:
    return {
        "result": {
            "keypointReport": {"fps": 9.0, "frames": []},
            "myVideoKey": "uploads/u1/prev.mp4",
            "joints": joints or [],
        }
    }


# |Δscore| 소스가 살아있으면(RED) 렌더를 트리거하는 score 변화 페어 —
# left_elbow 90↔70 = keypoint left_hand 개선(improved) 후보.
_CURR_JOINTS_IMPROVED = [{"key": "left_elbow", "score": 90.0}]
_PREV_JOINTS_IMPROVED = [{"key": "left_elbow", "score": 70.0}]


class _S3Stub:
    def download_file(self, bucket, key, path):  # noqa: ARG002 - stub
        return None


def _run(monkeypatch, result, prev, dtw_match=None):
    """빌더 실행 — _render_fault_zoom / _s3 / _FRAME_EXTRACTOR mock 후 호출 캡처."""
    calls: list[tuple[tuple, dict]] = []

    def _fake_render(*a, **k):
        calls.append((a, k))
        return [{"joint": "stub"}]

    monkeypatch.setattr(app, "_render_fault_zoom", _fake_render)
    monkeypatch.setattr(app, "_s3", _S3Stub())

    class _Ext:
        target_fps = 9.0

    monkeypatch.setattr(app, "_FRAME_EXTRACTOR", _Ext())
    out = app._build_mode3_fault_zoom_comparisons(
        result,
        "/tmp/user-video.mp4",
        {"fps": 9.0, "frames": []},
        prev,
        _profile(),
        "uid1",
        "an1",
        "bucket",
        cached_user_frames=None,
        dtw_match=dtw_match,
    )
    return out, calls


# ── 케이스 1: 감점 record criterion → region 소스 ────────────────────────────


def test_leg_extension_record_emits_legs_region(monkeypatch):
    """leg_extension record → legs region 멤버로 렌더 (|Δscore| 파생 관절 아님)."""
    result = _result(
        records=[_rec("leg_extension")], joints=_CURR_JOINTS_IMPROVED
    )
    out, calls = _run(monkeypatch, result, _prev(_PREV_JOINTS_IMPROVED))
    assert len(calls) == 1
    fault_joints = calls[0][0][5]
    assert set(fault_joints) == _LEGS_MEMBERS
    assert out == [{"joint": "stub"}]


def test_arm_extension_record_emits_arms_region(monkeypatch):
    """arm_extension record → arms region 멤버로 렌더."""
    result = _result(
        records=[_rec("arm_extension")], joints=_CURR_JOINTS_IMPROVED
    )
    _, calls = _run(monkeypatch, result, _prev(_PREV_JOINTS_IMPROVED))
    assert len(calls) == 1
    assert set(calls[0][0][5]) == _ARMS_MEMBERS


def test_split_angle_record_maps_to_legs(monkeypatch):
    """split_angle record → legs region (매핑 표 29-04 앱 helper 와 항목 동일)."""
    result = _result(records=[_rec("split_angle")])
    _, calls = _run(monkeypatch, result, _prev())
    assert len(calls) == 1
    assert set(calls[0][0][5]) == _LEGS_MEMBERS


def test_same_region_records_dedupe_to_single_card(monkeypatch):
    """leg_extension + split_angle (둘 다 legs) → 렌더 1회 + 멤버 중복 없음."""
    result = _result(records=[_rec("leg_extension"), _rec("split_angle")])
    _, calls = _run(monkeypatch, result, _prev())
    assert len(calls) == 1
    fault_joints = calls[0][0][5]
    assert len(fault_joints) == len(set(fault_joints))
    assert set(fault_joints) == _LEGS_MEMBERS


# ── 케이스 2: improved 억제 ──────────────────────────────────────────────────


def test_improved_kind_never_emitted(monkeypatch):
    """score 개선 입력이어도 kind 'improved' 는 방출 인자에 등장 금지 (deferred)."""
    result = _result(
        records=[_rec("leg_extension")], joints=_CURR_JOINTS_IMPROVED
    )
    _, calls = _run(monkeypatch, result, _prev(_PREV_JOINTS_IMPROVED))
    assert len(calls) == 1
    kinds = calls[0][0][7]
    assert "improved" not in set(kinds.values())
    assert set(kinds.values()) == {"deficit"}


# ── 케이스 3: record 0 → 카드 0 ──────────────────────────────────────────────


def test_no_breakdown_no_cards(monkeypatch):
    """deductionBreakdown 부재 → 렌더 미호출 + 빈 리스트 (score 변화 있어도).

    29-CONTEXT D-08 — 감점 record 없으면 zoom 카드 없음 = 의도된 동작
    (4/5 빈 criteria 동작 자연 귀결, RESEARCH Open Q4).
    """
    result = _result(records=None, joints=_CURR_JOINTS_IMPROVED)
    out, calls = _run(monkeypatch, result, _prev(_PREV_JOINTS_IMPROVED))
    assert calls == []
    assert out == []


def test_empty_records_no_cards(monkeypatch):
    """records 빈 리스트 → 렌더 미호출 + 빈 리스트."""
    result = _result(records=[], joints=_CURR_JOINTS_IMPROVED)
    out, calls = _run(monkeypatch, result, _prev(_PREV_JOINTS_IMPROVED))
    assert calls == []
    assert out == []


# ── 케이스 4: 비매핑 criterion → 카드 0 ──────────────────────────────────────


def test_unmapped_criteria_no_cards(monkeypatch):
    """line / dimension_overall_fallback 뿐 → 렌더 미호출 (collective 전신
    criterion 무투영 — 29-04 앱 helper 결정과 정합)."""
    result = _result(
        records=[_rec("line"), _rec("dimension_overall_fallback")],
        joints=_CURR_JOINTS_IMPROVED,
    )
    out, calls = _run(monkeypatch, result, _prev(_PREV_JOINTS_IMPROVED))
    assert calls == []
    assert out == []


# ── 케이스 5: 렌더 인자 보존 (28-05/CR-01 무회귀) ────────────────────────────


def test_dtw_args_preserved(monkeypatch):
    """dtw_match passthrough + dtw_ref_fps=_pipeline_frame_fps() 유지."""
    sentinel = object()
    result = _result(
        records=[_rec("leg_extension")], joints=_CURR_JOINTS_IMPROVED
    )
    _, calls = _run(
        monkeypatch, result, _prev(_PREV_JOINTS_IMPROVED), dtw_match=sentinel
    )
    assert len(calls) == 1
    kwargs = calls[0][1]
    assert kwargs["dtw_match"] is sentinel
    assert kwargs["dtw_ref_fps"] == app._pipeline_frame_fps()
    assert kwargs["cached_user_frames"] is None
