"""D-05 known-answer 앵커 검증 — 정은지 fault/correct 6 페어 방향 판정 + synthetic above-cutoff.

실영상 6 페어 앵커는 RTMW(GPU) + S3 fixture 가 필요하므로 per-test @requires_anchor_env 로
gate 한다. **module-level pytestmark 금지** (ITER-2 HIGH-1) — 같은 파일의 synthetic
above-cutoff 케이스(GPU 불필요)까지 skip 되는 모순을 피한다. synthetic 케이스는 마커 없이
항상 실행되어 sensitivity gate 를 항시 검증한다.

실영상 앵커 활성화:
    RUN_PHASE19_ANCHORS=1 pytest tests/test_anchor_known_answer.py -q

경계 (절대): 19-D05 표의 ~편차는 **방향 판정 근거(주석)** 으로만 사용. assert 비교 임계로
하드코딩 금지 ([[calibration-source-hard-gate]] [[scoring-redesign-must-generalize-no-overfit]]).
단언 = fault 종합 < correct 종합(방향) + 페어별 dominant 차원 지배. 점수 숫자 타깃 아님.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

import app  # noqa: E402
from sunity_shared.analysis import dimensions, technique  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS  # noqa: E402

# 실영상/GPU 앵커 전용 per-test 마커 (module-level 금지 — ITER-2 HIGH-1).
requires_anchor_env = pytest.mark.skipif(
    os.environ.get("RUN_PHASE19_ANCHORS") != "1",
    reason="RUN_PHASE19_ANCHORS=1 + S3/GPU(RTMW) 필요 — 실영상 fault/correct 페어 앵커",
)

# D-05 6 페어 메타 (19-D05-VISION-GROUNDING-SPIKE.md). skip 되더라도 보존 — 활성화가
# mechanical 하도록 real fixture S3 key + 페어별 지배 차원(dominant dimension) 상수화.
# dominant: line = 라인/신전 붕괴(척추/스플릿/발끝), angle = 관절각 결함(무릎 굽음).
# ~편차 수치는 방향 근거 주석으로만 — assert 임계 아님 (calibration-source-hard-gate).
_S3_FIXTURE_PREFIX = "fixtures"  # spike_vision_grounding_pair.py 의 "fixtures:<motion>-<cls>.mp4"
ANCHOR_PAIRS = (
    # (motion, fault_key, correct_key, dominant_dimension, 근거 주석)
    ("climb", "fixtures:climb-fault.mp4", "fixtures:climb-correct.mp4", dimensions.DIM_LINE),       # 등 말림 ~25°
    ("kip-up", "fixtures:kip-up-fault.mp4", "fixtures:kip-up-correct.mp4", dimensions.DIM_ANGLE),   # 무릎 굽음 ~35°
    ("pdshape", "fixtures:pdshape-fault.mp4", "fixtures:pdshape-correct.mp4", dimensions.DIM_ANGLE),# 자유다리 무릎 ~35°
    ("elbow-twist-sister", "fixtures:elbow-twist-sister-fault.mp4", "fixtures:elbow-twist-sister-correct.mp4", dimensions.DIM_LINE),  # 스플릿 ~40°
    ("power-spin", "fixtures:power-spin-fault.mp4", "fixtures:power-spin-correct.mp4", dimensions.DIM_ANGLE),  # 무릎×2+스플릿 major3
    ("peter-pan", "fixtures:peter-pan-fault.mp4", "fixtures:peter-pan-correct.mp4", dimensions.DIM_ANGLE),    # 뻗은다리 무릎 ~25°
)


def _profile() -> technique.TechniqueProfile:
    """팔꿈치/무릎 EXTEND 결정적 프로파일."""
    exp = {
        k: technique.JOINT_EXTEND
        if k.endswith("elbow") or k.endswith("knee")
        else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(name="t", category="unknown", joint_expectations=exp)


@requires_anchor_env
@pytest.mark.parametrize(
    "motion,fault_key,correct_key,dominant",
    ANCHOR_PAIRS,
    ids=[p[0] for p in ANCHOR_PAIRS],
)
def test_anchor_fault_lower_than_correct(motion, fault_key, correct_key, dominant):
    """실영상 페어: fault 종합 < correct 종합(방향) + 지배 차원 깎임.

    RTMW(GPU) 로 두 영상을 분석 → 재설계 채점기에 통과. 단언은 방향만:
      - fault 종합 < correct 종합 (major fault 가 종합을 끌어내림)
      - dominant 차원(line/angle)이 fault 에서 더 낮음 (지배 결함 반영)
    19-D05 ~편차 수치는 방향 근거일 뿐 비교 임계로 쓰지 않는다.
    """
    analyze = getattr(app, "analyze_fixture_for_anchor", None)
    if analyze is None:
        pytest.skip("analyze_fixture_for_anchor harness 부재 — Pod 재개 후 Wave 1+ 가 추가")
    fault = analyze(fault_key, _profile())
    correct = analyze(correct_key, _profile())
    assert fault["overall"] < correct["overall"]
    assert fault["dimensionScores"][dominant] < correct["dimensionScores"][dominant]


def test_above_cutoff_synthetic_stays_high():
    # 마커 없음 — 항상 실행 (ITER-2 HIGH-1, sensitivity gate). GPU/S3 불필요.
    # synthetic 정상 동작(신전관절 거의 완전 신전 + 떨림 작음) → 종합 high 유지.
    # 재설계가 above-cutoff(고득점이어야 정상) 케이스를 깎으면 FAIL (위양성 방지).
    profile = _profile()
    rng = np.random.default_rng(5)
    base = np.full(NUM_JOINTS, 178.0)  # 신전관절 거의 180° (라인 만점 영역)
    angles = base + rng.normal(0, 1.5, size=(30, NUM_JOINTS))  # 떨림 작음
    dims = dimensions.absolute_dimension_scores(angles, profile)
    overall = dimensions.overall_from_dimensions(dims)
    assert overall >= 90
