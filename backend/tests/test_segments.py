"""구간별 점수 — 합성 시퀀스로 결정적 검증. AWS 불필요."""

import numpy as np

from sunity_shared.analysis import segments
from sunity_shared.analysis.skeleton import NUM_JOINTS

CLIP = {"execStartS": 1.0, "landEndS": 27.0}  # 동작 구간 26초
COMBO_REF = {
    "motionId": "ref-foxtop",
    "sharedBaseMotionId": "ref-invert",
    "baseUntilS": 6.0,
    "clipRange": CLIP,
}


def test_boundary_frame_ratio():
    # baseUntilS 6, execStart 1, landEnd 27 → frac (6-1)/26 ≈ 0.192
    assert segments.ref_boundary_frame(CLIP, 6.0, 100) == 19
    # 경계가 구간 시작/끝이면 클램프
    assert segments.ref_boundary_frame(CLIP, 1.0, 100) == 0
    assert segments.ref_boundary_frame(CLIP, 27.0, 100) == 100


def test_boundary_frame_degenerate_span():
    # span 이 0 이면 분할 불가 → 전부 베이스(=ref_len)
    assert segments.ref_boundary_frame({"execStartS": 5, "landEndS": 5}, 5, 40) == 40


def test_split_path_by_ref():
    path = [(i, i) for i in range(20)]
    base, ext = segments.split_path_by_ref(path, 8)
    assert [r for _, r in base] == list(range(8))
    assert [r for _, r in ext] == list(range(8, 20))


def test_segment_scores_combo_perfect_match():
    T = 20
    a_ref = np.zeros((T, NUM_JOINTS))
    user_seg = np.zeros((T, NUM_JOINTS))  # 완벽 일치
    path = [(i, i) for i in range(T)]
    s = segments.segment_scores(COMBO_REF, "인버트", path, user_seg, a_ref)
    assert s is not None
    assert s["base"] == 100 and s["extension"] == 100
    assert s["baseMotionId"] == "ref-invert"
    assert s["baseMotionName"] == "인버트"


def test_segment_scores_extension_worse_than_base():
    # 확장 구간(경계 이후 프레임)만 관절 편차 → extension < base
    T = 20
    a_ref = np.zeros((T, NUM_JOINTS))
    user_seg = np.zeros((T, NUM_JOINTS))
    boundary = segments.ref_boundary_frame(CLIP, 6.0, T)
    user_seg[boundary:, :] = 25.0
    path = [(i, i) for i in range(T)]
    s = segments.segment_scores(COMBO_REF, "인버트", path, user_seg, a_ref)
    assert s["base"] > s["extension"]


def test_segment_scores_none_for_single_motion():
    single = {"motionId": "ref-sideway-spin", "clipRange": CLIP}
    s = segments.segment_scores(
        single, "", [(0, 0)], np.zeros((1, NUM_JOINTS)), np.zeros((1, NUM_JOINTS))
    )
    assert s is None
