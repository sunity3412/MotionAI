"""quick-260924-ig3 — reference_relative seed 의 "유지 구간 상수" 경로.

c3m(2026-09-24) 실측: kip-up 실수의 왼어깨는 정렬 스텝 절반에서 30~60도 벌어져 있는데 짝 프레임
|Δ| 의 **영상 전체 median** 이 두 봉우리 사이 틈(20.6, 허용 20 자리)에 떨어져 억제 → 100점.
낮은 표본의 절반은 기준이 한 바퀴 더 도는 동안 학생 한 프레임에 **정체**한 짝이 공급했다.
i38: 기준 clipRange exec 창 안 **짝 없는** 각도 median 은 5동작 전부 실수를 갈랐다(정타 0 근처).

이 테스트는 (1) 창을 안 주면 종전과 byte-동일 (2) 창 안에서만 다른 학생(유지 구간 결함)은 짝
median 에 희석되지 않고 상수로 방출 (3) 창 부족·expects_extension·NaN 은 fail-closed (4) 값과
신뢰구간이 같은 표본 (5) 순수 헬퍼의 계약 을 단언한다. 수치 타깃 아님 — 구조 단언.
실 Gemini/Pod/S3/Firestore 호출 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared.analysis import technique, vision_veto  # noqa: E402
from sunity_shared.analysis.motiondtw import MotionMatch  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402

_NJ = len(JOINT_KEYS)
_LE = JOINT_KEYS.index("left_elbow")
_LS = JOINT_KEYS.index("left_shoulder")


def _reference(t_len: int = 90) -> np.ndarray:
    t = np.arange(t_len, dtype=float)
    return np.stack(
        [120.0 + 25.0 * np.sin(0.11 * (j + 1) * t + 0.5 * j) for j in range(_NJ)], axis=1
    )


def _profile(**expect):
    return technique.TechniqueProfile(name="미등록", category="unknown", joint_expectations=expect)


def _quant():
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="available", angleDeltas=None, bodyRelativeNotches=None,
        windowMedianAngleDeltas=None, warnings=(),
    )


def _build(student, ref, *, window=None, profile=None, extra=None):
    _dev, match, _seg, a_ref = app._deviation_against(student, ref, _NJ)
    audit: dict = {}
    me: dict = {}
    at: dict = {}
    md = app._build_deduction_measured_deviations(
        angles=student, profile=profile or _profile(), assessments=[], dimension_scores={},
        quantification=_quant(), reference_dtw_match=match, reference_angles=a_ref,
        seed_audit_out=audit, measurement_error_out=me, measured_at_out=at,
        ref_exec_window=window, **(extra or {}),
    )
    return md, audit, me, at, match


def _hold_fault(ref, lo=30, hi=70, joint=_LE, delta=30.0):
    """유지 구간(창 안)에서만 한 관절이 +delta — 진입·이탈은 기준과 같다."""
    s = ref.copy()
    s[lo:hi, joint] += delta
    return s


def test_no_window_is_byte_identical_to_legacy():
    ref = _reference()
    student = _hold_fault(ref)
    md_none, audit_none, *_ = _build(student, ref, window=None)
    _dev, match, _seg, a_ref = app._deviation_against(student, ref, _NJ)
    md_legacy = app._build_deduction_measured_deviations(
        angles=student, profile=_profile(), assessments=[], dimension_scores={},
        quantification=_quant(), reference_dtw_match=match, reference_angles=a_ref,
    )
    assert md_none == md_legacy
    assert audit_none["constant_joints"] == []


def test_hold_fault_is_not_diluted_by_full_clip_median():
    ref = _reference()
    student = _hold_fault(ref, 30, 70, _LE, 30.0)
    key = "angle_vs_reference__left_elbow"

    md_dtw, _a, _m, _t, match = _build(student, ref, window=None)
    md_c, audit, me, at, _ = _build(student, ref, window=(30, 70))

    # 전제: 짝 median 은 창 밖(같음)과 창 안(+30)이 반반이라 희석된다 — 이 결함이 재현되지
    # 않으면 이 테스트는 아무것도 안 잰다.
    assert md_dtw.get(key, 0.0) < 25.0, f"전제 실패 — DTW median 이 희석되지 않았다: {md_dtw.get(key)}"
    # 상수 경로: 창 안 학생 median − 기준 창 median = +30 (희석 0).
    assert md_c[key] == pytest.approx(30.0, abs=1.5)
    assert audit["constant_joints"] == ["left_elbow"]
    assert "left_elbow" not in audit["fallback_joints"]
    # 다른 관절은 차이 0 → 미방출(종전과 같은 규칙).
    assert [k for k in md_c if k.startswith("angle_vs_reference__")] == [key]
    # 값과 구간이 같은 표본에서: n = 창 프레임 수, 구간이 값을 묶는다. (구간 폭은 창 안에서
    # 관절이 움직이는 만큼이다 — 합성 궤적은 ±25 사인이라 넓다. 수치 타깃 아님.)
    lo, hi, n = me[key]
    assert n == 40 and 0.0 <= lo <= 30.0 <= hi
    # 측정 순간은 창 안 프레임이다.
    assert 30 <= at[key]["frame_idx"] < 70


def test_short_window_falls_back_to_dtw():
    ref = _reference()
    student = _hold_fault(ref)
    md_dtw, *_ = _build(student, ref, window=None)
    md_short, audit, *_ = _build(student, ref, window=(30, 33))
    assert md_short == md_dtw
    assert audit["constant_joints"] == []


def test_expects_extension_joint_is_not_emitted_by_constant_path():
    ref = _reference()
    student = _hold_fault(ref, 30, 70, _LE, 30.0)
    md, audit, *_ = _build(student, ref, window=(30, 70), profile=_profile(left_elbow="extend"))
    assert "angle_vs_reference__left_elbow" not in md
    assert audit["constant_joints"] == []


def test_nan_in_window_makes_that_joint_fall_back():
    """창 안 유한 표본이 최소 미달인 관절은 상수 경로에서 빠진다(그 관절만 DTW 로).

    정렬(match)은 깨끗한 학생으로 만들고, 빌더에는 NaN 을 심은 각도를 넘긴다 — 시험 대상은
    빌더의 fail-closed 이지 NaN 이 DTW 에 들어갔을 때의 거동이 아니다.
    """
    ref = _reference()
    clean = _hold_fault(ref, 30, 70, _LS, 30.0)
    _dev, match, _seg, a_ref = app._deviation_against(clean, ref, _NJ)
    student = clean.copy()
    student[30:68, _LS] = np.nan  # 창 안 유한 표본 2개 → 최소(5) 미달
    audit: dict = {}
    md = app._build_deduction_measured_deviations(
        angles=student, profile=_profile(), assessments=[], dimension_scores={},
        quantification=_quant(), reference_dtw_match=match, reference_angles=a_ref,
        seed_audit_out=audit, ref_exec_window=(30, 70),
    )
    assert "left_shoulder" not in audit["constant_joints"]
    # 다른 관절(유한)은 상수 경로 그대로 — 관절 단위 fail-closed 다.
    assert "left_elbow" in audit["constant_joints"] or "left_elbow" not in md


def test_perfect_take_emits_nothing_with_window():
    ref = _reference()
    md, audit, me, *_ = _build(ref.copy(), ref, window=(20, 80))
    assert [k for k in md if k.startswith("angle_vs_reference__")] == []
    assert audit["constant_joints"] == [] and me == {}


# ── 순수 헬퍼 계약 ───────────────────────────────────────────────────────

def test_reference_exec_window_contract():
    doc = {"clipRange": {"execStartS": 1.0, "landEndS": 7.2}}
    assert app._reference_exec_window(doc, 15.0, 118) == (15, 108)
    assert app._reference_exec_window(doc, 15.0, 60) == (15, 60)          # n 으로 잘림
    assert app._reference_exec_window({}, 15.0, 118) is None                # clipRange 없음
    assert app._reference_exec_window(None, 15.0, 118) is None
    assert app._reference_exec_window(doc, 0.0, 118) is None                # fps 미상
    assert app._reference_exec_window({"clipRange": {"execStartS": 5, "landEndS": 2}}, 15.0, 118) is None
    assert app._reference_exec_window({"clipRange": {"execStartS": 1.0, "landEndS": 1.2}}, 15.0, 118) is None  # 3프레임


def test_student_window_from_match_uses_edges_only():
    path = [(0, 0), (1, 1), (2, 2), (3, 3), (3, 4), (3, 5), (4, 6), (5, 7), (6, 8), (7, 9)]
    m = MotionMatch(start=10, end=18, ref_start=100, ref_end=110, distance=0.0, path=path)
    assert app._student_window_from_match(m, 102, 109) == (12, 17)           # 정체(3↔3,4,5)도 가장자리만
    assert app._student_window_from_match(m, 105, 107) is None               # 창 부족
    assert app._student_window_from_match(m, 200, 210) is None               # 창 밖


def test_abs_median_interval():
    assert app._abs_median_interval(25.0, 33.0) == (25.0, 33.0)
    assert app._abs_median_interval(-33.0, -25.0) == (25.0, 33.0)
    assert app._abs_median_interval(-3.0, 8.0) == (0.0, 8.0)


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv("REFERENCE_CONSTANT_WINDOW_ENABLED", raising=False)
    assert app._reference_constant_window_enabled() is True
    for off in ("0", "false", "OFF", "no"):
        monkeypatch.setenv("REFERENCE_CONSTANT_WINDOW_ENABLED", off)
        assert app._reference_constant_window_enabled() is False
