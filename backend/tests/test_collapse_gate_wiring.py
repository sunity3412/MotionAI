"""quick-260910-ovo Task 2 — 붕괴 게이트가 `_emit_reference_relative` 에 배선됐는가.

Task 1 이 판정 규칙을 잠갔다면 여기서 잠그는 것은 **배선**이다:

  ① 판정기 미전달(default) → md 는 이 사이클 이전과 **byte-동일**. 게이트는 켜야 켜진다.
  ② 붕괴 판정 → 그 관절의 `angle_vs_reference__{jk}` 가 md 에서 사라지고,
     `unjudged_out` 에 사실이 남고, `measured_at_out` 에도 순간이 안 남는다
     (md 키와 순간 키가 정확히 대응 — 사진 0장 멈춤이 원리적으로 안 생기는 근거).
  ③ 같은 프레임의 반대쪽 관절은 그대로 남는다 (게이트가 관절 단위다).
  ④ 측정 순간을 모르면(레거시) 게이트를 안 건다 — 의심스러우면 안 없앤다.
  ⑤ 판정기가 예외를 던져도 감점은 유지된다 (fail-open).

전부 순수 builder 테스트 — Pod/S3/Firestore/Gemini 호출 0.
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

import numpy as np  # noqa: E402

import app  # noqa: E402
from sunity_shared import models  # noqa: E402
from sunity_shared.analysis import technique  # noqa: E402
from sunity_shared.analysis.motiondtw import MotionMatch  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402

_LEFT_ELBOW = JOINT_KEYS.index("left_elbow")
_RIGHT_ELBOW = JOINT_KEYS.index("right_elbow")

_T = 10


def _profile():
    """미등록 동작 — expects_extension 전부 False (angle_vs_reference 경로가 열린다)."""
    return technique.TechniqueProfile(
        name="미등록: ovo", category="unknown", joint_expectations={}
    )


def _angles(deg=170.0):
    return np.full((_T, len(JOINT_KEYS)), deg, dtype=float)


def _inputs():
    """양 팔꿈치에 편차를 준 학생/기준 각도 — 두 관절이 다 방출되는 것이 기본값."""
    ref = _angles()
    usr = _angles()
    usr[:, _LEFT_ELBOW] = 130.0   # 편차 40
    usr[:, _RIGHT_ELBOW] = 140.0  # 편차 30
    return usr, ref


def _build(**kw):
    usr, ref = _inputs()
    return app._build_deduction_measured_deviations(
        angles=usr, profile=_profile(), assessments=[], dimension_scores={},
        quantification=None,
        reference_dtw_match=MotionMatch(
            start=0, end=_T, ref_start=0, ref_end=_T,
            distance=0.0, path=[(i, i) for i in range(_T)],
        ),
        reference_angles=ref, **kw,
    )


def _collapse_only(*joints):
    """지정 관절만 붕괴라고 답하는 판정기 — 프레임과 무관."""
    wanted = set(joints)
    return lambda _frame, joint: joint in wanted


# ── ① 미전달 = 종전 산출 ──────────────────────────────────────────────────
def test_gate_off_by_default_is_byte_identical():
    baseline = _build()
    assert baseline == _build(limb_collapsed=None)
    assert "angle_vs_reference__left_elbow" in baseline
    assert "angle_vs_reference__right_elbow" in baseline


# ── ②③ 붕괴 관절만 사라진다 ──────────────────────────────────────────────
def test_collapsed_joint_is_not_emitted_and_is_recorded():
    baseline = _build()
    unjudged: list = []
    measured_at: dict = {}
    md = _build(
        limb_collapsed=_collapse_only("right_elbow"),
        unjudged_out=unjudged,
        measured_at_out=measured_at,
    )
    # 붕괴 관절은 seed 자체가 없다 → record 도 그 record 가 낳는 멈춤·카드도 안 생긴다.
    assert "angle_vs_reference__right_elbow" not in md
    # 반대쪽 팔은 그대로 — 게이트는 관절 단위다.
    assert md["angle_vs_reference__left_elbow"] == pytest.approx(
        baseline["angle_vs_reference__left_elbow"]
    )
    # 없앤 것을 없었던 일로 만들지 않는다.
    assert unjudged == [
        {"joint": "right_elbow", "reason": models.UNJUDGED_REASON_COLLAPSE}
    ]
    # md 키와 순간 키가 정확히 대응 — 미방출 관절에는 순간도 안 남는다.
    assert "angle_vs_reference__right_elbow" not in measured_at
    assert "angle_vs_reference__left_elbow" in measured_at


def test_reason_is_a_known_enum_value():
    """reason 은 계약 enum 에서만 나온다 (3-way lockstep 방어)."""
    unjudged: list = []
    _build(limb_collapsed=_collapse_only("right_elbow"), unjudged_out=unjudged)
    assert {u["reason"] for u in unjudged} <= set(models.UNJUDGED_REASONS)


def test_every_joint_collapsed_removes_every_reference_relative_seed():
    unjudged: list = []
    md = _build(limb_collapsed=lambda _f, _j: True, unjudged_out=unjudged)
    assert not [k for k in md if k.startswith("angle_vs_reference__")]
    assert len(unjudged) == len({u["joint"] for u in unjudged})  # 중복 없음


# ── ④ 순간 미상이면 게이트를 안 건다 ─────────────────────────────────────
def test_unknown_measurement_moment_does_not_gate():
    """at_frame=None(레거시 doc 처럼 순간 미상) → 게이트 미적용, 감점 유지.

    `dtw_frame_by_joint` 를 비우면 순간이 없다 — per_joint_representative_frames 가
    아무것도 못 내는 상황(레거시/형상 불량)의 재현이다. 그 상태에서 판정기가 "전부
    붕괴"라고 답해도 감점은 하나도 사라지지 않아야 한다.
    """
    import sunity_shared.analysis.motiondtw as _mdtw

    baseline = _build()
    orig = _mdtw.per_joint_representative_frames
    app_orig = getattr(app, "per_joint_representative_frames", None)
    try:
        app.per_joint_representative_frames = lambda *_a, **_k: {}
        unjudged: list = []
        md = _build(limb_collapsed=lambda _f, _j: True, unjudged_out=unjudged)
    finally:
        if app_orig is not None:
            app.per_joint_representative_frames = app_orig
        _mdtw.per_joint_representative_frames = orig
    assert md == baseline
    assert unjudged == []


# ── ⑤ 판정기 실패는 감점 유지 ────────────────────────────────────────────
def test_predicate_exception_keeps_the_deduction():
    def _boom(_frame, _joint):
        raise RuntimeError("판정기 고장")

    baseline = _build()
    unjudged: list = []
    md = _build(limb_collapsed=_boom, unjudged_out=unjudged)
    assert md == baseline
    assert unjudged == []


# ── result 부착 ──────────────────────────────────────────────────────────
def test_attach_unjudged_joints_keeps_empty_list_and_drops_malformed():
    """빈 리스트도 싣는다 — "봤는데 없다"와 "안 봤다"를 doc 에서 구분하기 위해."""
    result: dict = {}
    app._attach_unjudged_joints(result, [])
    assert result["unjudgedJoints"] == []

    result2: dict = {}
    app._attach_unjudged_joints(result2, [
        {"joint": "right_elbow", "reason": "collapse"},
        {"joint": "", "reason": "collapse"},   # 이름 없는 항목은 싣지 않는다
        {"joint": "left_elbow"},               # reason 없는 항목도
        "not-a-dict",
    ])
    assert result2["unjudgedJoints"] == [
        {"joint": "right_elbow", "reason": "collapse"}
    ]
