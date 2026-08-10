"""표시 프레임 선택이 붕괴 프레임을 건너뛴다 (quick-260810-e4v U6).

`select_confident_frame` 은 창 후보 중 **멤버 관절 conf 평균 최대**를 고른다. 그런데
붕괴 프레임에서 모델이 오히려 확신하므로 그 규칙이 **붕괴를 끌어당긴다**(08-09 실측:
창 후보 9개 중 가장 나쁜 것이 뽑혔다 / 08-10 실측: conf 0.57 로 게이트 통과한 프레임이
12관절 중 10개가 폴 위 한 줄, 사이각 0도, −11.6점 카드).

그래서 후보에서 붕괴 프레임을 **먼저 배제**하고 그 안에서 종전 규칙을 쓴다.
이 순서가 08-09 의 벽을 푼다 — 창을 넓혀도 붕괴를 끌어당기지 않는다.

무회귀: 붕괴 후보가 없으면 산출은 종전과 동일해야 한다. 전 후보가 붕괴면 배제를 포기하고
종전 규칙으로 돌아간다(fail-open — 카드가 통째로 사라지는 것보다 낫다).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

JOINTS = ["left_shoulder", "right_shoulder", "left_hip", "right_hip",
          "left_knee", "right_knee", "left_elbow", "right_elbow"]
MEMBERS = ("right_elbow", "right_shoulder")


def _clean_frame(seed: float):
    """좌표가 흩어진 정상 프레임."""
    return [[0.30 + 0.07 * i, 0.20 + 0.09 * i + seed] for i in range(len(JOINTS))]


def _collapsed_frame():
    """폴 위 한 세로선 — x 동일 (08-10 실측 패턴)."""
    return [[0.532, 0.30 + 0.04 * i] for i in range(len(JOINTS))]


def _report(frames: list[list[list[float]]], confs: list[list[float]]) -> dict:
    return {
        "joints": JOINTS, "fps": 9.0, "frames": len(frames),
        "data": [c for f in frames for p in f for c in p],
        "confidence": [c for row in confs for c in row],
        "version": "test",
    }


def _mk(kind_by_frame, conf_by_frame):
    frames = [(_collapsed_frame() if k == "x" else _clean_frame(0.01 * i))
              for i, k in enumerate(kind_by_frame)]
    confs = [[c] * len(JOINTS) for c in conf_by_frame]
    return _report(frames, confs)


def test_collapsed_candidate_is_skipped_even_when_most_confident() -> None:
    """붕괴 프레임이 conf 최고여도 뽑히지 않는다 — 이것이 08-10 결함의 핵심."""
    rep = _mk(["o", "x", "o"], [0.55, 0.95, 0.60])
    got = fz.select_confident_frame(rep, [0, 1, 2], MEMBERS)
    assert got == 2, f"붕괴(1번, conf 0.95)를 피하고 깨끗한 최고 conf 를 골라야 함: {got}"


def test_output_unchanged_when_no_candidate_is_collapsed() -> None:
    """붕괴가 없으면 종전 산출과 동일 (무회귀)."""
    rep = _mk(["o", "o", "o"], [0.55, 0.95, 0.60])
    assert fz.select_confident_frame(rep, [0, 1, 2], MEMBERS) == 1


def test_falls_back_when_every_candidate_is_collapsed() -> None:
    """전 후보가 붕괴면 배제를 포기한다 — 카드가 사라지는 것보다 낫다(fail-open)."""
    rep = _mk(["x", "x", "x"], [0.55, 0.95, 0.60])
    got = fz.select_confident_frame(rep, [0, 1, 2], MEMBERS)
    assert got == 1, f"전건 붕괴면 종전 규칙(conf 최대)로 폴백: {got}"


def test_legacy_report_without_confidence_still_medians() -> None:
    """confidence 없는 legacy 리포트 = 종전 sorted median 폴백 유지."""
    rep = _mk(["o", "o", "o"], [0.55, 0.95, 0.60])
    rep.pop("confidence")
    assert fz.select_confident_frame(rep, [0, 1, 2], MEMBERS) == 1


def test_empty_candidates_still_none() -> None:
    rep = _mk(["o"], [0.6])
    assert fz.select_confident_frame(rep, [], MEMBERS) is None


def test_select_confident_index_agrees_with_frame() -> None:
    """index 판(DTW 짝맞춤용)도 같은 프레임을 가리켜야 한다 — 두 함수 어긋나면 짝이 깨진다."""
    rep = _mk(["o", "x", "o"], [0.55, 0.95, 0.60])
    cands = [0, 1, 2]
    f = fz.select_confident_frame(rep, cands, MEMBERS)
    i = fz.select_confident_index(rep, cands, MEMBERS)
    assert i is not None and cands[i] == f
