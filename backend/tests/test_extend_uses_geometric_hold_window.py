"""EXTEND 채점은 국면 힌트가 아니라 기하 hold 창을 본다 (quick-260920-ra8).

belle 승인 2026-09-20. 근거 =
`.planning/quick/260920-cac-concurrency-contamination-fix/260920-cac-SUMMARY.md` §17.

무엇을 막는 테스트인가:
  Gemini 국면 인식이 정은지 파워스핀 정타(10.60초)의 hold 를 1.0초(스핀 진입부)라고
  답했다. 진입부는 무릎이 굽어 있는 국면이라 leg_extension -20 · line 0 위양성이 났다.
  같은 영상을 캐시 우회로 5번 물으면 hold 가 8.0초(정답)와 1.0초로 갈리고 중간값이
  없다 — 2/5 가 틀린 쪽이다. 즉 힌트를 신뢰하면 정타가 복권에 걸린다.

  2026-08-31 수리(quick-260831-gyk)는 힌트 창 **내부에서** 안정 부창을 재선택하는
  것이었는데, 힌트 창 **전체**가 진입부면 그 안 어디를 골라도 굽은 무릎이다.
  그래서 `dimensions._select_window` 가 힌트를 아예 쓰지 않도록 바꿨다.

AWS·네트워크·GPU 불필요. 합성 각도 시계열로 같은 모양을 만든다.
"""

import numpy as np

from sunity_shared.analysis import dimensions, technique
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS

_ENTRY_FRAMES = 30   # 진입: 무릎이 굽어 있고 흔들린다
_HOLD_FRAMES = 40    # 홀드: 무릎이 펴진 채 멈춘다
_BENT_DEG = 88.0
_STRAIGHT_DEG = 172.0


def _clip() -> np.ndarray:
    """앞은 굽은 무릎 + 흔들림, 뒤는 펴진 무릎 + 정지. 실제 파워스핀과 같은 모양."""
    rng = np.random.default_rng(0)
    entry = np.full((_ENTRY_FRAMES, NUM_JOINTS), 90.0)
    hold = np.full((_HOLD_FRAMES, NUM_JOINTS), 90.0)
    for k in ("left_knee", "right_knee"):
        i = JOINT_KEYS.index(k)
        # 진입부를 일부러 '분산 최소'로 만들지 않는다 — 흔들려야 기하 창이 홀드를 고른다.
        entry[:, i] = _BENT_DEG + rng.normal(0.0, 6.0, _ENTRY_FRAMES)
        hold[:, i] = _STRAIGHT_DEG
    return np.vstack([entry, hold])


def _profile(hold_window):
    return technique.TechniqueProfile(
        name="파워스핀",
        category="recognized",
        joint_expectations={"left_knee": "extend", "right_knee": "extend"},
        motion_id="ref-power-spin",
        hold_window=hold_window,
    )


def test_entry_pointing_hint_does_not_move_the_window():
    """힌트가 진입부를 통째로 가리켜도 창은 홀드에 남는다."""
    a = _clip()
    misleading = _profile((0, _ENTRY_FRAMES))       # 진입부만 가리키는 힌트
    none_hint = _profile(None)

    _, win_hint = dimensions._select_window(a, misleading)
    _, win_none = dimensions._select_window(a, none_hint)

    assert win_hint == win_none, (
        f"국면 힌트가 창을 옮겼다: 힌트있음={win_hint} 힌트없음={win_none}. "
        "quick-260920-ra8 — EXTEND 채점은 힌트를 쓰지 않아야 한다."
    )
    assert win_hint[0] >= _ENTRY_FRAMES, (
        f"창이 진입부({0}~{_ENTRY_FRAMES})에 걸쳤다: {win_hint}"
    )


def test_entry_pointing_hint_does_not_create_a_false_deduction():
    """그래서 정타가 감점되지 않는다 — line 은 만점권, 신전 부족분은 0 에 가깝다."""
    a = _clip()
    misleading = _profile((0, _ENTRY_FRAMES))

    score = dimensions.line_score(a, misleading)
    dev = dimensions.extension_deviation(a, misleading)
    worst = max(dev[JOINT_KEYS.index(k)] for k in ("left_knee", "right_knee"))

    # 홀드의 무릎은 172도 = 180 대비 8도 부족. IPSF 허용오차 20도 안이다.
    assert worst < 20.0, f"신전 부족분 {worst:.1f}도 — 허용오차 20도를 넘었다"
    assert score is not None and score >= 80, f"line_score={score}"


def test_bent_hold_still_scores_zero():
    """반대 방향 — 홀드에서 진짜로 굽어 있으면 그대로 잡는다(수리가 채점을 무디게 하지 않았다)."""
    a = _clip()
    for k in ("left_knee", "right_knee"):
        a[_ENTRY_FRAMES:, JOINT_KEYS.index(k)] = _BENT_DEG

    score = dimensions.line_score(a, _profile(None))
    # 160도 미만 = IPSF micro-bent 요소 무효 → 0점 (dimensions._SPLIT_FAIL_THRESHOLD_DEG)
    assert score == 0, f"굽은 홀드가 잡히지 않았다: line_score={score}"
