"""Phase 6 fixture factory helper.

본 fixture 는 합성 (synthetic). 실제 RTMW 출력 대용. 6 fixture 의 의도된 임계값은
NotebookLM Notebook 1 §1.4/1.5/3.4 + Notebook 4 §4.2 인용 + 2026-06-08 Codex Direct
Review R5 (high dispersion fixture) 박제.

backend/tests/fixtures/body_normalization/_factory.py 의 pose_frame_from_dict 를
재사용 (re-export). 추가 helper `load_paired_frames` 는 fixture_160cm_pro_vs_140cm_student
처럼 두 PoseFrame list 를 담은 fixture 의 분리 로딩을 담당.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.fixtures.body_normalization._factory import (  # re-export
    pose_frame_from_dict,
)

from sunity_shared.analysis.pose_frame import PoseFrame


_FIXTURE_DIR: Path = Path(__file__).resolve().parent


def load_fixture_raw(name: str) -> dict[str, Any]:
    """fixture JSON 을 dict 로 raw 로딩 (metadata 등 접근용).

    Args:
        name: fixture 파일명 ("fixture_xxx.json" 확장자 없이 또는 포함 둘 다 허용).

    Returns:
        JSON 으로 파싱된 dict.
    """
    if not name.endswith(".json"):
        name = f"{name}.json"
    path = _FIXTURE_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def load_single_frames(name: str) -> list[PoseFrame]:
    """단일 PoseFrame list 를 가진 fixture 로딩.

    fixture 형식: {"frames": [<frame dict>, ...], "metadata": {...}}

    Args:
        name: fixture 파일명.

    Returns:
        list[PoseFrame].
    """
    raw = load_fixture_raw(name)
    frames_raw = raw.get("frames")
    if frames_raw is None:
        raise ValueError(
            f"fixture {name} 에 'frames' 키가 없음 — paired/multi fixture 인 경우 "
            "load_paired_frames 또는 load_frames_by_key 사용"
        )
    return [pose_frame_from_dict(r) for r in frames_raw]


def load_paired_frames(
    name: str, *, key_a: str, key_b: str
) -> tuple[list[PoseFrame], list[PoseFrame]]:
    """두 PoseFrame list 를 가진 fixture 분리 로딩.

    예: fixture_160cm_pro_vs_140cm_student → (pro_frames, student_frames)
        fixture_split_angle_hipline → (short_leg_frames, long_leg_frames)

    Args:
        name: fixture 파일명.
        key_a: 첫 번째 list 의 key.
        key_b: 두 번째 list 의 key.

    Returns:
        (list_a, list_b) tuple.
    """
    raw = load_fixture_raw(name)
    if key_a not in raw or key_b not in raw:
        raise ValueError(
            f"fixture {name} 에 '{key_a}' 또는 '{key_b}' key 없음. "
            f"available keys: {list(raw.keys())}"
        )
    a = [pose_frame_from_dict(r) for r in raw[key_a]]
    b = [pose_frame_from_dict(r) for r in raw[key_b]]
    return a, b


__all__ = (
    "pose_frame_from_dict",
    "load_fixture_raw",
    "load_single_frames",
    "load_paired_frames",
)
