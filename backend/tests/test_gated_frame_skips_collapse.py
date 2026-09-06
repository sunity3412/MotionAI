"""gated(멈춤 상속) 카드가 붕괴 앵커에서 가장 가까운 성한 프레임으로 옮긴다 (quick-260906-f4j).

2026-09-06 실측(09-03 라이브 6문서 21장 = 42패널): 앵커 붕괴 패널 14(학생 5 · 정은지 9).
conf<0.5 겹침 8 → 신뢰도는 붕괴의 부분집합. 14개 **전부 gated 카드**(경로별 gated 12 /
stage1 3 / advisory 6, stage1·advisory 붕괴 0). 구제 가능성(코드가 실제 고르는 9fps 격자):
±2 에 10/14, ±4 에 11/14, ±8 에 14/14. 최대 이동 0.78초, 대부분 0.11초.
반사실(학생 불건전 5패널 전수를 옮겨 기계 눈 재질문): 1장 불일치→통과, 4장 통과 유지, 악화 0.

기전(코드로 확인): gated 호출부(app.py `_run_gated_card_inherit`)가 `dtw_match=None`,
`at_frame_idx=None`, `user_frame_idx=u9`/`ref_frame_idx=r9` 로 프레임을 고정해 부르므로
`build_fault_zoom_comparisons` 의 후보 합성 블록(`if unit.at_frame_idx is not None and
dtw_match is not None`)이 **구조적으로 미도달** — 08-10(ms2/e4v) 붕괴 방어(`_drop_collapsed` ·
`select_confident_frame` · `_ring(±2→±4)` 승급)가 정작 필요한 카드에서 안 돈다.

그래서 순수 함수 `nearest_usable_frame` 을 두고 호출부가 u9/r9 를 넘기기 전에 옮긴다.
성한 판정은 창 승급 블록과 **같은 함수 한 개**(`_frame_usable`) — 붕괴만 보면 그릴 수 없는
프레임으로 간다(실측 p34fresh1786349646). 반경은 새 상수 없이 `_MOMENT_ANCHOR_RADIUS_WIDE`(4).
"""

from __future__ import annotations

import inspect
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


# ── nearest_usable_frame — 옮긴다 / 그대로 ─────────────────────────────────


def test_collapsed_anchor_moves_to_nearest_usable_frame() -> None:
    """앵커 3 과 ±1 이 전부 붕괴면 거리 2 의 성한 프레임(1)으로 옮긴다 — 실측 대부분 0.11초 이동."""
    kinds = ["o", "o", "x", "x", "x", "o", "o"]
    rep = _mk(kinds, [0.9] * len(kinds))
    assert fz.nearest_usable_frame(rep, 3, MEMBERS, n_frames=len(kinds)) == (1, "moved")


def test_tie_prefers_lower_index() -> None:
    """같은 거리면 작은 인덱스 — select_confident_frame 의 오름차순 tie-break 관례와 정합(결정론)."""
    kinds = ["o", "x", "o"]
    rep = _mk(kinds, [0.9] * len(kinds))
    assert fz.nearest_usable_frame(rep, 1, MEMBERS, n_frames=len(kinds)) == (0, "moved")


def test_healthy_anchor_is_kept_even_if_neighbor_is_more_confident() -> None:
    """비붕괴 앵커는 재선택하지 않는다 — 09-06 실측 비붕괴 28패널 byte-동일 보장(무회귀 대조군)."""
    kinds = ["o", "o", "x", "x", "x", "o", "o"]
    rep = _mk(kinds, [0.6, 0.95, 0.9, 0.9, 0.9, 0.9, 0.9])
    assert fz.nearest_usable_frame(rep, 0, MEMBERS, n_frames=len(kinds)) == (0, "kept")


def test_radius_four_reaches_and_five_does_not() -> None:
    """±4 도달(11/14)·미도달(stuck) — belle 지목 카드가 ±4 에서 구제된 실측 경계."""
    n = 11
    kinds = ["x"] * n
    kinds[1] = "o"
    rep = _mk(kinds, [0.9] * n)
    assert fz.nearest_usable_frame(rep, 5, MEMBERS, n_frames=n) == (1, "moved")

    kinds = ["x"] * n
    kinds[0] = "o"
    rep = _mk(kinds, [0.9] * n)
    assert fz.nearest_usable_frame(rep, 5, MEMBERS, n_frames=n) == (5, "stuck")


def test_destination_must_be_drawable_not_only_uncollapsed() -> None:
    """붕괴만 보면 그릴 수 없는 프레임으로 간다(p34fresh1786349646) — 목적지는 비붕괴 AND 멤버 valid."""
    kinds = ["o", "o", "x", "o"]
    # frame 1 은 비붕괴지만 전 멤버 conf 0.3 → _member_pts valid 빈 리스트(relaxed 만).
    rep = _mk(kinds, [0.9, 0.3, 0.9, 0.9])
    assert fz.nearest_usable_frame(rep, 2, MEMBERS, n_frames=len(kinds)) == (3, "moved")


def test_reference_report_at_18fps_is_judged_in_rep_index_space() -> None:
    """정은지 doc 는 18fps rep(붕괴 9/14 가 기준측) — 판정이 _to_rep_idx 변환을 거쳐야 한다."""
    n9 = 8
    kinds = ["o"] * (2 * n9)
    for i in (6, 7, 8, 9):
        kinds[i] = "x"
    rep = _mk(kinds, [0.9] * len(kinds))
    rep["fps"] = 18.0
    # anchor(9fps)=4 → rep 8 "x". cand 3 → rep 6 "x", cand 5 → rep 10 "o".
    assert fz.nearest_usable_frame(rep, 4, MEMBERS, n_frames=n9) == (5, "moved")


def test_legacy_report_without_joints_is_kept() -> None:
    """joints 메타 없는 legacy 리포트 = 판정 불가 → is_collapsed_frame False → 그대로(fail-open)."""
    kinds = ["x", "x", "x"]
    rep = _mk(kinds, [0.9] * len(kinds))
    rep.pop("joints")
    assert fz.nearest_usable_frame(rep, 1, MEMBERS, n_frames=len(kinds)) == (1, "kept")


def test_boundary_candidates_are_skipped_not_clamped() -> None:
    """범위 밖 후보는 클램프 중복이 아니라 스킵 — 앵커 0 에서 -1 은 없고 1 로 간다."""
    rep = _mk(["x", "o"], [0.9, 0.9])
    assert fz.nearest_usable_frame(rep, 0, MEMBERS, n_frames=2) == (1, "moved")

    rep = _mk(["x"], [0.9])
    assert fz.nearest_usable_frame(rep, 0, MEMBERS, n_frames=1) == (0, "stuck")


def test_radius_default_reuses_wide_anchor_radius_constant() -> None:
    """새 임계 금지 — 반경 기본값은 _MOMENT_ANCHOR_RADIUS_WIDE 그 객체(=4)."""
    p = inspect.signature(fz.nearest_usable_frame).parameters["radius"]
    assert p.default is fz._MOMENT_ANCHOR_RADIUS_WIDE  # noqa: SLF001
    assert fz._MOMENT_ANCHOR_RADIUS_WIDE == 4  # noqa: SLF001


# ── _frame_usable — 창 승급과 gated 이동이 공유하는 단일 판정 ─────────────────


def test_frame_usable_requires_uncollapsed_and_drawable() -> None:
    """붕괴 → False / 비붕괴·conf 0.3(그릴 수 없음) → False / 비붕괴·conf 0.9 → True."""
    rep = _mk(["x", "o", "o"], [0.9, 0.3, 0.9])
    n = int(rep["frames"])
    assert fz._frame_usable(rep, 0, MEMBERS, 9.0, 9.0, n) is False  # noqa: SLF001
    assert fz._frame_usable(rep, 1, MEMBERS, 9.0, 9.0, n) is False  # noqa: SLF001
    assert fz._frame_usable(rep, 2, MEMBERS, 9.0, 9.0, n) is True  # noqa: SLF001
