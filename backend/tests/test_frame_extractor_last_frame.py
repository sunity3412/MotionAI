"""12-deferred §12-B — frame_extractor 마지막 frame 강제 포함 단위 테스트.

belle UAT 2차 (2026-06-10) finding: 17초 영상의 15~17초 구간에서 keypoint 가
종료 자세로 정지 (사람은 회전 중). 9fps step loop 가 영상 끝 잔여 frame 무시
→ 결과 frame 의 마지막이 영상의 마지막보다 ~step/src_fps 초 앞.

본 테스트는 imageio.get_reader 를 mock 해서 다음을 검증:
  1. step 모듈로 떨어지지 않는 영상 끝 frame 이 추가됨
  2. step 모듈로 정확히 떨어지는 영상에서는 중복 추가 X (idempotent)
  3. start_s/end_s clip 시에도 동일 보장
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared" / "python"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

# imageio 가 로컬 dev env 에 미설치된 경우를 대비한 stub (Pod 에는 정상 설치).
# 본 테스트는 imageio.get_reader 만 mock 하므로 module 만 있으면 동작.
if "imageio" not in sys.modules:
    fake = types.ModuleType("imageio")
    fake.get_reader = MagicMock()  # type: ignore[attr-defined]
    sys.modules["imageio"] = fake

# PIL.Image 도 동일 (frame_extractor 가 _resize 에서 사용 — max_side 초과 시만 호출).
# 본 테스트의 frame 은 64×48 < 640 max_side 라 _resize 안 들어감 → import 만 보장.
if "PIL" not in sys.modules:
    pil_mod = types.ModuleType("PIL")
    image_mod = types.ModuleType("PIL.Image")
    image_mod.BILINEAR = 2  # type: ignore[attr-defined]
    image_mod.fromarray = MagicMock()  # type: ignore[attr-defined]
    pil_mod.Image = image_mod  # type: ignore[attr-defined]
    sys.modules["PIL"] = pil_mod
    sys.modules["PIL.Image"] = image_mod

from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402


class FakeReader:
    """imageio Reader 의 최소 동작 mock — __iter__ + get_meta_data + close."""

    def __init__(self, frames: list[np.ndarray], fps: float) -> None:
        self._frames = frames
        self._fps = fps

    def get_meta_data(self) -> dict[str, float]:
        return {"fps": self._fps}

    def __iter__(self):
        return iter(self._frames)

    def close(self) -> None:
        pass


def _make_frame(value: int, h: int = 64, w: int = 48) -> np.ndarray:
    """value 로 채워진 H×W×3 uint8 frame — frame 식별용 (각 frame 의 value 가 다르게)."""
    return np.full((h, w, 3), value, dtype=np.uint8)


def test_last_frame_appended_when_remainder_skipped() -> None:
    """src_fps=10, target_fps=3, step=3, 11 frame → idx 0/3/6/9 + idx 10 (마지막)."""
    src_fps = 10.0
    frames = [_make_frame(i) for i in range(11)]  # idx 0..10
    extractor = FfmpegFrameExtractor(target_fps=3.0, max_side=640)

    with patch(
        "sunity_shared.analysis.frame_extractor.imageio.get_reader",
        return_value=FakeReader(frames, src_fps),
    ):
        out = extractor.extract("dummy.mp4")

    # step = round(10/3) = 3. 정상 sample = idx 0, 3, 6, 9 (4 frame).
    # fix 후 = idx 10 의 마지막 frame 추가 → 5 frame.
    assert out.shape[0] == 5, f"expected 5 frames after fix, got {out.shape[0]}"
    # 마지막 frame 의 value == 10 (idx 10 의 fill value 검증).
    assert int(out[-1, 0, 0, 0]) == 10, (
        f"last frame should be idx 10 (value=10), got value={int(out[-1,0,0,0])}"
    )


def test_no_duplicate_when_last_already_appended() -> None:
    """idx 마지막이 step 모듈로 정확히 떨어지면 중복 추가 X."""
    src_fps = 10.0
    # idx 0..9 (10 frame). step=3 → sample idx 0/3/6/9. 마지막 idx 9 == 가장 최근 append.
    # fix 동작 = last_idx_seen (9) > last_idx_appended (9) → False → 미추가.
    frames = [_make_frame(i) for i in range(10)]
    extractor = FfmpegFrameExtractor(target_fps=3.0, max_side=640)

    with patch(
        "sunity_shared.analysis.frame_extractor.imageio.get_reader",
        return_value=FakeReader(frames, src_fps),
    ):
        out = extractor.extract("dummy.mp4")

    assert out.shape[0] == 4, f"expected 4 frames (no dup), got {out.shape[0]}"
    assert int(out[-1, 0, 0, 0]) == 9


def test_last_frame_appended_with_clip_range() -> None:
    """start_s/end_s clip 시에도 마지막 frame 보존."""
    src_fps = 10.0
    # 20 frame, clip = 0.3s ~ 1.1s → idx 3..10 (end_idx=11 미포함).
    # step=3, sample 시작 idx 3, (3-3)%3=0 → 3, 다음 6, 9. idx 10 미포함.
    # fix 후 idx 10 추가 → 4 frame.
    frames = [_make_frame(i) for i in range(20)]
    extractor = FfmpegFrameExtractor(target_fps=3.0, max_side=640)

    with patch(
        "sunity_shared.analysis.frame_extractor.imageio.get_reader",
        return_value=FakeReader(frames, src_fps),
    ):
        out = extractor.extract("dummy.mp4", start_s=0.3, end_s=1.1)

    # idx 3, 6, 9 (sample) + idx 10 (last) = 4 frame
    assert out.shape[0] == 4, f"expected 4 frames in clip, got {out.shape[0]}"
    assert int(out[-1, 0, 0, 0]) == 10


def test_empty_reader_raises() -> None:
    """frame 0개면 ValueError (기존 동작 유지)."""
    extractor = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
    with patch(
        "sunity_shared.analysis.frame_extractor.imageio.get_reader",
        return_value=FakeReader([], 30.0),
    ):
        with pytest.raises(ValueError, match="프레임을 추출하지 못했습니다"):
            extractor.extract("dummy.mp4")


def test_uat_finding_17s_video() -> None:
    """belle UAT 2차 재현 시나리오 — 17초 src_fps=30 영상 → target_fps=9.

    기존: 17 × 9 = 153 frame, 마지막 = 16.89초 (영상 끝 0.11초 정지).
    fix 후: 154 frame, 마지막 = 영상 마지막 frame 자체.
    """
    src_fps = 30.0
    duration_s = 17.0
    n_src = int(src_fps * duration_s)  # 510
    frames = [_make_frame(i % 256) for i in range(n_src)]
    extractor = FfmpegFrameExtractor(target_fps=9.0, max_side=640)

    with patch(
        "sunity_shared.analysis.frame_extractor.imageio.get_reader",
        return_value=FakeReader(frames, src_fps),
    ):
        out = extractor.extract("dummy.mp4")

    # step = round(30/9) = 3. n_src=510 → sample idx 0/3/.../507 = 170 frame.
    # 510-1=509 (마지막 idx, enumerate 0-based) → 509 % 3 = 2 ≠ 0 → step miss
    # fix 후 +1 → 171.
    expected_with_fix = 170 + 1  # 171
    assert out.shape[0] == expected_with_fix, (
        f"expected {expected_with_fix} frames after fix, got {out.shape[0]}"
    )
    # 마지막 frame 의 value 가 영상 마지막 idx (509 % 256 = 253)
    assert int(out[-1, 0, 0, 0]) == 509 % 256
