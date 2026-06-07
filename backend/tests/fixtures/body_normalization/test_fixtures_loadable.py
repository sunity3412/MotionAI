"""5 fixture × pose_frame_from_dict smoke load + image y-order convention guard.

HIGH-2 v1→v2 박제: PoseFrame dataclass 시그너처 (timestamp_ms / uncertainty_proxy
/ PoleAxis 4 필드 origin 박멸) 정합.

MEDIUM-3 v5 박제:
  - normal_pose 의 80%+ frame 이 mid_shoulder.y < mid_hip.y (image y-down upright).
  - inverted_pose 의 80%+ frame 이 mid_shoulder.y > mid_hip.y (image y-down inverted).
  - 두 fixture 모두 default axis_vector (0.0, 1.0, 0.0) — axis_vector 가
    inversion verdict 와 무관함을 박제.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixtures.body_normalization._factory import pose_frame_from_dict


_FIXTURES_DIR = Path(__file__).parent

_FIXTURE_NAMES = [
    "normal_pose",
    "inverted_pose",
    "occluded_leg",
    "short_clip",
    "asymmetric_pose",
]


def _load_fixture(name: str) -> list[dict]:
    path = _FIXTURES_DIR / f"{name}_pose_frames.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", _FIXTURE_NAMES)
def test_all_fixtures_load_via_factory(name: str) -> None:
    """5 fixture 모두 pose_frame_from_dict 로 load PASS."""
    raw = _load_fixture(name)
    assert len(raw) > 0, f"{name} fixture empty"
    frames = [pose_frame_from_dict(r) for r in raw]
    assert len(frames) == len(raw)
    # 모든 frame 은 timestamp_ms (int) 보유
    for f in frames:
        assert isinstance(f.timestamp_ms, int)
        assert isinstance(f.frame_index, int)


@pytest.mark.parametrize("name", _FIXTURE_NAMES)
def test_pole_axis_no_origin_field(name: str) -> None:
    """HIGH-2 v1→v2 박제: PoleAxis 에 origin 필드 0 (4-field schema)."""
    raw = _load_fixture(name)
    for r in raw:
        pa = r.get("pole_axis")
        if pa is None:
            continue
        assert "origin" not in pa, (
            f"{name} fixture 에 PoleAxis.origin 필드 박멸 위반 (HIGH-2 v1→v2)"
        )


@pytest.mark.parametrize("name", _FIXTURE_NAMES)
def test_keypoint3d_has_uncertainty_proxy(name: str) -> None:
    """Keypoint3D 가 uncertainty_proxy 필드 보유 (D-05)."""
    raw = _load_fixture(name)
    sample = raw[0]
    for kp_name, kp in sample["keypoints_3d"].items():
        assert "uncertainty_proxy" in kp, (
            f"{name}/{kp_name} 의 keypoints_3d 가 uncertainty_proxy 누락"
        )


def _mid_y(frame_kp: dict, top_names: tuple[str, ...], bot_names: tuple[str, ...]) -> tuple[float, float]:
    """frame keypoints_3d 에서 (mid_shoulder.y, mid_hip.y) 추출."""
    top_y = sum(frame_kp[n]["y"] for n in top_names) / len(top_names)
    bot_y = sum(frame_kp[n]["y"] for n in bot_names) / len(bot_names)
    return top_y, bot_y


_SHOULDERS = ("left_shoulder", "right_shoulder")
_HIPS = ("left_hip", "right_hip")


def test_normal_pose_is_upright_in_y_down_image() -> None:
    """MEDIUM-3 v5 박제: normal_pose 80%+ frame 이 image-y-down upright."""
    raw = _load_fixture("normal_pose")
    upright_count = 0
    for r in raw:
        sh_y, hp_y = _mid_y(r["keypoints_3d"], _SHOULDERS, _HIPS)
        if sh_y < hp_y:  # y-down: 어깨가 화면 위쪽
            upright_count += 1
    ratio = upright_count / len(raw)
    assert ratio >= 0.8, (
        f"normal_pose upright frame ratio {ratio:.2f} < 0.8 (MEDIUM-3 v5)"
    )


def test_inverted_pose_is_inverted_in_y_down_image() -> None:
    """MEDIUM-3 v5 박제: inverted_pose 80%+ frame 이 image-y-down inverted."""
    raw = _load_fixture("inverted_pose")
    inverted_count = 0
    for r in raw:
        sh_y, hp_y = _mid_y(r["keypoints_3d"], _SHOULDERS, _HIPS)
        if sh_y > hp_y:  # y-down: 어깨가 화면 아래쪽 = 인버트
            inverted_count += 1
    ratio = inverted_count / len(raw)
    assert ratio >= 0.8, (
        f"inverted_pose inverted frame ratio {ratio:.2f} < 0.8 (MEDIUM-3 v5)"
    )


def test_inverted_pose_axis_vector_is_default_unchanged() -> None:
    """MEDIUM-3 v5 박제: inverted_pose 의 PoleAxis.axis_vector == (0,1,0).

    axis_vector 가 inversion 결정에 관여하지 않는다 — 박제 증거.
    """
    raw = _load_fixture("inverted_pose")
    for r in raw:
        ax = r["pole_axis"]["axis_vector"]
        assert tuple(ax) == (0.0, 1.0, 0.0), (
            f"inverted_pose frame {r['frame_index']} axis_vector "
            f"{ax} != (0,1,0) — MEDIUM-3 v5 박제 위반"
        )
