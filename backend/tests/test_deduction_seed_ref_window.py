"""quick-260923-sqt — 감점 seed 가 점수 경로와 **같은 기준 창**을 읽는가.

`MotionMatch.path` 의 기준 인덱스는 window-local 이다(motiondtw.MotionMatch 계약).
점수 경로(`_deviation_against`)는 `a_ref[ref_start:ref_end]` 로 잘라 소비하지만,
`_build_deduction_measured_deviations` 는 호출부가 넘긴 **전체** 기준 배열을 그대로
인덱싱했다. 기준 창이 0 이 아닌 곳에서 시작하면(학생 영상 길이가 기준의 80~100% 라
DTW 가 기준 안에서 창을 미끄러뜨린 경우) 감점 재료가 기준의 엉뚱한 프레임과 비교된다.

2026-09-23 운영 함수 재현(정은지 기준 영상의 앞 15% 를 잘라 학생으로 투입 — 올바른 정렬이면
편차 0): 점수 경로 편차 최대 0.0도, 감점 seed 최대 29~33도 → 최종 84~89점.

이 테스트는 학생 = 기준의 뒷부분(한 관절만 +25도)으로 **점수 경로와 감점 seed 가 같은 값**을
내는지 단언한다. 수치 타깃이 아니라 두 경로의 일치(같은 창) 단언이다 — curve-fit 아님.
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
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402

_NJ = len(JOINT_KEYS)
_LEFT_ELBOW = JOINT_KEYS.index("left_elbow")


def _reference(t_len: int = 80) -> np.ndarray:
    """관절마다 주기가 다른 비주기 궤적 — 창을 미끄러뜨렸을 때 최적 위치가 하나로 정해진다."""
    t = np.arange(t_len, dtype=float)
    cols = []
    for j in range(_NJ):
        cols.append(
            120.0
            + 35.0 * np.sin(0.13 * (j + 1) * t + 0.7 * j)
            + 12.0 * np.cos(0.041 * (j + 2) * t)
        )
    return np.stack(cols, axis=1)


def _profile():
    """미등록 동작 — expects_extension 전부 False 라 전 관절이 reference_relative seed 대상."""
    return technique.TechniqueProfile(
        name="미등록", category="unknown", joint_expectations={}
    )


def _quant():
    return vision_veto.VisionQuantificationResult(
        quantificationStatus="available",
        angleDeltas=None,
        bodyRelativeNotches=None,
        windowMedianAngleDeltas=None,
        warnings=(),
    )


def _seed_and_score_path(student: np.ndarray, ref: np.ndarray):
    """운영 mode1 과 같은 순서: _deviation_against → (match, 전체 a_ref) → 감점 builder."""
    dev, match, _seg, a_ref = app._deviation_against(student, ref, _NJ)
    md = app._build_deduction_measured_deviations(
        angles=student,
        profile=_profile(),
        assessments=[],
        dimension_scores={},
        quantification=_quant(),
        reference_dtw_match=match,
        reference_angles=a_ref,  # ★운영과 동일 — 호출부는 전체 배열을 넘긴다
    )
    seed = {
        jk: float(md.get(f"angle_vs_reference__{jk}", 0.0)) for jk in JOINT_KEYS
    }
    return seed, dict(zip(JOINT_KEYS, map(float, dev))), match


@pytest.mark.parametrize("cut", [8, 12])
def test_seed_matches_score_path_when_reference_window_is_offset(cut):
    ref = _reference()
    student = ref[cut:].copy()
    student[:, _LEFT_ELBOW] += 25.0  # 진짜 차이 하나

    seed, score_path, match = _seed_and_score_path(student, ref)

    # 전제: 이 입력은 기준 창을 실제로 미끄러뜨린다. 아니면 이 테스트는 아무것도 안 잰다.
    assert match.ref_start > 0, f"전제 실패 — 기준 창이 0 에서 시작 ({match})"

    # 점수 경로는 진짜 차이 하나만 본다.
    assert score_path["left_elbow"] == pytest.approx(25.0, abs=1e-6)
    # 감점 seed 는 점수 경로와 같은 창을 읽어야 한다 — 관절마다 같은 값.
    for jk in JOINT_KEYS:
        assert seed[jk] == pytest.approx(score_path[jk], abs=1e-6), (
            f"{jk}: 감점 seed {seed[jk]:.2f}도 ≠ 점수 경로 {score_path[jk]:.2f}도 "
            f"(기준 창 [{match.ref_start},{match.ref_end}))"
        )


def test_perfect_subsequence_emits_no_reference_deduction_seed():
    """정은지 자신의 동작(기준의 뒷부분)에는 기준 대비 감점 재료가 하나도 나오면 안 된다."""
    ref = _reference()
    student = ref[10:].copy()

    seed, score_path, match = _seed_and_score_path(student, ref)

    assert match.ref_start > 0, f"전제 실패 — 기준 창이 0 에서 시작 ({match})"
    assert max(score_path.values()) == pytest.approx(0.0, abs=1e-9)
    emitted = {jk: v for jk, v in seed.items() if v > 0.0}
    assert emitted == {}, f"완벽한 수행에 감점 재료가 생겼다: {emitted}"
