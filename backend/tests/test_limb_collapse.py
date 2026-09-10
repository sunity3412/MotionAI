"""quick-260910-ovo Task 1 — 붕괴 사지 판정기.

잠그는 것은 셋이다.

  ① 대표 사례의 **실측 서명**을 재현한다 (aspect 0.05 / 길이비 0.46 → 붕괴).
  ② **공선성 단독 사용 금지** — 곧게 편 정상 다리(kip-up aspect 0.016~0.042,
     길이비 0.88~1.16)는 붕괴한 팔보다 더 납작하지만 붕괴가 **아니다**.
     이 축이 없으면 정립 fixture 가 위양성으로 걸린다.
  ③ 의심스러우면 붕괴가 아니다 — NaN·0 나눗셈·이름 미상은 전부 False.
     이 게이트는 감점을 *없애는* 쪽이라 보수적이어야 한다.

전부 순수 함수 테스트 — Pod/S3/Firestore/Gemini 호출 0.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sunity_shared.analysis.limb_collapse import (
    COLLAPSE_ASPECT_MAX,
    COLLAPSE_LENGTH_FRAC_MAX,
    collapse_from_pose_frames,
    is_limb_collapsed,
    limb_aspect_and_length,
    limb_keypoints_for_joint,
    median_limb_length,
)
from sunity_shared.analysis.reliability import ANGLE_REQUIRED_KEYPOINTS
from sunity_shared.analysis.skeleton import JOINT_KEYS

# ── 실측 서명 (2026-09-10, 승인 fixture 5대상) ────────────────────────────
# 대표 사례 c64afae6 f162 오른팔(폴에 붕괴): aspect 0.052 / 길이비 0.46.
# 아래 3점은 그 aspect 를 재현하도록 구성한 기하다(값은 계산으로 확인한다 —
# 좌표를 박고 숫자를 손으로 적어 두지 않는다).
_COLLAPSED_ARM = ((0.0, 0.0), (0.05, 0.50), (0.0, 1.0))
# 같은 프레임 왼팔(정상, 굽은 팔): aspect 0.748.
_NORMAL_ARM = ((0.0, 0.0), (0.5, 0.0), (0.5 * 0.657, 0.5))
# kip-up f16 곧게 편 다리: aspect 0.016~0.042 — 붕괴한 팔보다 **더** 납작하다.
_STRAIGHT_LEG = ((0.0, 0.0), (0.004, 0.50), (0.0, 1.0))


def _ratio_median(length: float, ratio: float) -> float:
    """그 프레임 길이가 클립 중앙값의 `ratio` 배가 되도록 하는 중앙값."""
    return length / ratio


# ── 축 1~3: 실측 서명 재현 ────────────────────────────────────────────────
def test_representative_collapsed_arm_is_collapsed():
    """대표 사례 서명 — aspect 0.05 수준 + 길이비 0.46 → 붕괴."""
    aspect, length = limb_aspect_and_length(*_COLLAPSED_ARM)
    assert aspect == pytest.approx(0.05, abs=0.005)
    med = _ratio_median(length, 0.46)
    assert is_limb_collapsed(aspect, length, med) is True


def test_same_frame_normal_arm_is_not_collapsed():
    """같은 프레임 정상 팔 — aspect 0.748 → 붕괴 아님 (길이비와 무관)."""
    aspect, length = limb_aspect_and_length(*_NORMAL_ARM)
    assert aspect == pytest.approx(0.748, abs=0.005)
    # 길이까지 절반으로 줄었다고 쳐도 납작하지 않으므로 붕괴가 아니다.
    assert is_limb_collapsed(aspect, length, _ratio_median(length, 0.46)) is False


def test_straight_leg_is_flatter_than_collapsed_arm_but_not_collapsed():
    """★ 이 축이 없으면 정립 위양성 — 곧게 편 다리는 납작하지만 안 줄어든다.

    kip-up f16 실측: aspect 0.016~0.042(붕괴 팔 0.052 보다 작다) / 길이비 1.16·0.88.
    공선성만 보는 판정기는 여기서 전부 발화해 승인 fixture 를 깬다.
    """
    leg_aspect, leg_length = limb_aspect_and_length(*_STRAIGHT_LEG)
    arm_aspect, _arm_length = limb_aspect_and_length(*_COLLAPSED_ARM)
    assert leg_aspect < arm_aspect  # 정상 다리가 붕괴한 팔보다 더 납작하다
    assert leg_aspect < COLLAPSE_ASPECT_MAX  # 공선 조건은 통과한다
    for ratio in (1.16, 0.88):
        med = _ratio_median(leg_length, ratio)
        assert is_limb_collapsed(leg_aspect, leg_length, med) is False


# ── 축 4~5: AND 조건 ──────────────────────────────────────────────────────
def test_flat_but_not_shortened_is_not_collapsed():
    """납작하지만 안 줄어든 경우 → False (AND 조건)."""
    aspect, length = limb_aspect_and_length(*_COLLAPSED_ARM)
    assert aspect < COLLAPSE_ASPECT_MAX
    # 길이가 클립 중앙값 그대로(비 1.0) — 단축 조건 미달.
    assert is_limb_collapsed(aspect, length, length) is False


def test_shortened_but_not_flat_is_not_collapsed():
    """줄었지만 안 납작한 경우 → False (AND 조건)."""
    aspect, length = limb_aspect_and_length(*_NORMAL_ARM)
    assert aspect > COLLAPSE_ASPECT_MAX
    med = _ratio_median(length, 0.30)  # 길이는 평소의 30% — 단축 조건은 통과
    assert is_limb_collapsed(aspect, length, med) is False


def test_and_boundary_each_side_of_the_thresholds():
    """임계 양옆 — 두 조건이 모두 임계 안일 때만 True."""
    a_in, a_out = COLLAPSE_ASPECT_MAX - 0.01, COLLAPSE_ASPECT_MAX + 0.01
    r_in, r_out = COLLAPSE_LENGTH_FRAC_MAX - 0.05, COLLAPSE_LENGTH_FRAC_MAX + 0.05
    assert is_limb_collapsed(a_in, r_in, 1.0) is True
    assert is_limb_collapsed(a_in, r_out, 1.0) is False
    assert is_limb_collapsed(a_out, r_in, 1.0) is False
    assert is_limb_collapsed(a_out, r_out, 1.0) is False
    # 임계 정확히 위 = 붕괴 아님 (엄격 부등호 — 경계는 없애지 않는 쪽).
    assert is_limb_collapsed(COLLAPSE_ASPECT_MAX, r_in, 1.0) is False
    assert is_limb_collapsed(a_in, COLLAPSE_LENGTH_FRAC_MAX, 1.0) is False


# ── 축 6~7: 보수적 fail-closed ────────────────────────────────────────────
@pytest.mark.parametrize(
    "pts",
    [
        ((float("nan"), 0.0), (0.05, 0.5), (0.0, 1.0)),
        ((0.0, 0.0), (0.05, float("nan")), (0.0, 1.0)),
        ((0.0, 0.0), (0.05, 0.5), (float("inf"), 1.0)),
    ],
)
def test_missing_point_is_not_collapsed(pts):
    """3점 중 하나라도 결측(NaN/Inf)이면 붕괴 아님 — 판정 불가가 아니라 False."""
    aspect, length = limb_aspect_and_length(*pts)
    assert math.isnan(aspect) and math.isnan(length)
    assert is_limb_collapsed(aspect, length, 1.0) is False


def test_zero_length_and_zero_median_do_not_divide_by_zero():
    """길이 0 / median 0 → 0 나눗셈 없이 False."""
    aspect, length = limb_aspect_and_length((0.5, 0.5), (0.5, 0.5), (0.5, 0.5))
    assert length == 0.0
    assert aspect == 1.0  # 한 점으로 뭉친 배치는 "가장 납작"이 아니라 판정 불가
    assert is_limb_collapsed(aspect, length, 0.0) is False
    assert is_limb_collapsed(0.01, 0.0, 0.0) is False
    assert is_limb_collapsed(0.01, 0.0, float("nan")) is False


def test_non_numeric_inputs_are_not_collapsed():
    assert is_limb_collapsed("0.01", 0.1, 1.0) is False
    assert is_limb_collapsed(None, 0.1, 1.0) is False


# ── 중앙값 헬퍼 ───────────────────────────────────────────────────────────
def test_median_limb_length_ignores_missing_frames():
    pts = np.full((5, 3, 2), np.nan)
    # 길이 1.0 프레임 3개 + 결측 2개 → 중앙값 1.0
    for t in (0, 2, 4):
        pts[t] = [(0.0, 0.0), (0.0, 0.5), (0.0, 1.0)]
    assert median_limb_length(pts) == pytest.approx(1.0)


def test_median_limb_length_is_nan_when_nothing_finite():
    assert math.isnan(median_limb_length(np.full((3, 3, 2), np.nan)))
    assert math.isnan(median_limb_length(np.zeros((0, 3, 2))))


# ── 관절 → 사지 3점 매핑 (ANGLE_REQUIRED_KEYPOINTS 재사용) ────────────────
def test_limb_keypoints_come_only_from_angle_required_keypoints():
    """새 좌표 매핑표 금지 — 3점은 전부 reliability 의 사슬에서 온다."""
    chains = {tuple(v) for v in ANGLE_REQUIRED_KEYPOINTS.values()}
    for jk in JOINT_KEYS:
        names = limb_keypoints_for_joint(jk)
        assert names is not None, jk
        assert names in chains, (jk, names)


@pytest.mark.parametrize(
    "joint,expected",
    [
        ("right_elbow", ("right_shoulder", "right_elbow", "right_wrist")),
        # 어깨는 몸통을 가로지르는 사슬(팔꿈치-어깨-엉덩이)이 아니라 같은 쪽 팔을 본다.
        ("right_shoulder", ("right_shoulder", "right_elbow", "right_wrist")),
        ("left_knee", ("left_hip", "left_knee", "left_ankle")),
        # 고관절도 마찬가지 — 같은 쪽 다리를 본다.
        ("left_hip", ("left_hip", "left_knee", "left_ankle")),
    ],
)
def test_limb_keypoints_for_joint(joint, expected):
    assert limb_keypoints_for_joint(joint) == expected


@pytest.mark.parametrize("bad", ["", "elbow", "nose", "left_nose", None, 3])
def test_unknown_joint_has_no_limb(bad):
    assert limb_keypoints_for_joint(bad) is None


# ── pose_frames 어댑터 ────────────────────────────────────────────────────
class _KP:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class _Frame:
    def __init__(self, kps):
        self.keypoints_2d = kps


def _arm_frame(p0, p1, p2, side="right"):
    return _Frame({
        f"{side}_shoulder": _KP(*p0),
        f"{side}_elbow": _KP(*p1),
        f"{side}_wrist": _KP(*p2),
    })


def _scaled(pts, k):
    return tuple((x * k, y * k) for x, y in pts)


def test_adapter_flags_only_the_collapsed_frame():
    """클립 중앙값은 정상 프레임들이 만들고, 붕괴 프레임만 발화한다."""
    normal = [_arm_frame(*_NORMAL_ARM) for _ in range(9)]
    # 붕괴 프레임 — 정상 길이의 0.46 배로 줄어든 납작한 팔.
    _a, normal_len = limb_aspect_and_length(*_NORMAL_ARM)
    _a2, arm_len = limb_aspect_and_length(*_COLLAPSED_ARM)
    k = (normal_len * 0.46) / arm_len
    frames = normal[:5] + [_arm_frame(*_scaled(_COLLAPSED_ARM, k))] + normal[5:]
    collapsed = collapse_from_pose_frames(frames)
    assert collapsed(5, "right_elbow") is True
    assert collapsed(4, "right_elbow") is False
    assert collapsed(6, "right_elbow") is False
    # 다른 쪽 팔은 좌표가 아예 없다 → 판정 불가 → 붕괴 아님.
    assert collapsed(5, "left_elbow") is False


def test_adapter_is_false_outside_the_frame_range_and_on_bad_input():
    frames = [_arm_frame(*_NORMAL_ARM)]
    collapsed = collapse_from_pose_frames(frames)
    assert collapsed(-1, "right_elbow") is False
    assert collapsed(99, "right_elbow") is False
    assert collapsed("x", "right_elbow") is False
    assert collapsed(0, "not_a_joint") is False
    assert collapse_from_pose_frames(None)(0, "right_elbow") is False
    assert collapse_from_pose_frames([object()])(0, "right_elbow") is False


def test_adapter_shoulder_reads_the_arm_chain():
    """어깨 감점도 같은 팔의 붕괴로 판정된다."""
    _a, normal_len = limb_aspect_and_length(*_NORMAL_ARM)
    _a2, arm_len = limb_aspect_and_length(*_COLLAPSED_ARM)
    k = (normal_len * 0.46) / arm_len
    frames = [_arm_frame(*_NORMAL_ARM) for _ in range(9)]
    frames[3] = _arm_frame(*_scaled(_COLLAPSED_ARM, k))
    collapsed = collapse_from_pose_frames(frames)
    assert collapsed(3, "right_shoulder") is True
    assert collapsed(2, "right_shoulder") is False
