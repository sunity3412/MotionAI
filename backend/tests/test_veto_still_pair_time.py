"""quick-260923-u2q — Gemini 에 보내는 정은지 still 이 학생 still 과 **같은 시각**인가.

기준 쪽 인덱스 공간이 둘이다:
  기준 각도(angles)   — 기준 doc 재처리 공간, ~15fps (kip-up 118행 / 7.9초)
  기준 영상 프레임    — veto 가 기준 영상을 9fps 목표로 새로 뽑은 배열, ~10fps (79장)
`fault_zoom._matched_ref_frame` 은 **각도 공간** 인덱스를 돌려준다(그 독스트링이 "호출측이
9fps frames 로 변환할 책임"이라 경고). 확대 카드 경로는 28-05(2026-07-08)에 변환을 넣었는데
veto still 경로(`_build_selected_frame_pair`, 23-01)는 변환 없이 영상 프레임 배열에 그대로 꽂았다.

2026-09-23 실측(kip-up 정타 = 기준과 같은 테이크, 픽셀 대조): 운영이 고른 기준 still 0/10 이
같은 순간 — 학생 2.0초에 정은지 3.0초, 후반 1/3 은 전부 기준 마지막 프레임.
Gemini 판정이 실행된 실수 영상 4건 중 3건의 still 이 1.1~3.1초 어긋나 있었다(저장 인덱스로 계산).

또 `MotionMatch.path` 의 기준 인덱스는 window-local 이다 — `_matched_ref_frame` 이
`ref_start` 를 안 더하면 창이 미끄러진 학생 영상(기준의 1.2~1.5배 길이)에서 더 어긋난다
(같은 결함군: quick-260923-sqt).

프레임 i 의 red 채널 = i 로 만든 합성 영상으로 "어느 프레임이 뽑혔나"를 픽셀로 확인한다.
실 영상·Gemini·S3 호출 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis import frame_extractor  # noqa: E402
from sunity_shared.analysis.motiondtw import MotionMatch  # noqa: E402

_FRAMES_FPS = 10.0   # 9fps 목표 추출의 실효 fps (30fps 원본 → step 3)
_ANGLES_FPS = 15.0   # 기준 doc 각도 공간 (18fps 목표 재처리 → step 2)


def _video(n: int) -> np.ndarray:
    a = np.zeros((n, 32, 24, 3), dtype=np.uint8)
    for i in range(n):
        a[i, :, :, 0] = i
    return a


class _FakeExtractor:
    """FfmpegFrameExtractor 대역 — 경로별 합성 프레임 + 실효 fps."""

    videos: dict = {}

    def __init__(self, target_fps: float = 9.0, max_side: int = 640) -> None:
        pass

    def extract(self, path):
        return self.videos[str(path)]

    def effective_fps_for(self, path):
        return _FRAMES_FPS


def _same_take_match(n_user: int, n_ref_angles: int, ref_start: int = 0) -> MotionMatch:
    """학생 프레임 u(10fps) ↔ 기준 각도 행(15fps) — 같은 시각 대응. path 는 window-local."""
    path = []
    for u in range(n_user):
        j = min(int(round(u * _ANGLES_FPS / _FRAMES_FPS)), n_ref_angles - 1) - ref_start
        if j >= 0:
            path.append((u, j))
    return MotionMatch(start=0, end=n_user, ref_start=ref_start, ref_end=n_ref_angles,
                       distance=0.0, path=path)


def _red(png_path: str) -> int:
    return int(np.asarray(Image.open(png_path).convert("RGB"))[0, 0, 0])


@pytest.fixture
def fake_videos(monkeypatch):
    user, ref = _video(79), _video(79)          # 같은 7.9초 테이크, 둘 다 10fps 로 추출됨
    _FakeExtractor.videos = {"/v/user.mp4": user, "/v/ref.mp4": ref}
    monkeypatch.setattr(frame_extractor, "FfmpegFrameExtractor", _FakeExtractor)
    return user, ref


def _pair(match, u, n_ref_angles):
    pair = app._build_selected_frame_pair(
        user_video_path="/v/user.mp4",
        reference_video_path="/v/ref.mp4",
        reference_dtw_match=match,
        user_frame_idx=u,
        reference_angles_len=n_ref_angles,
        reference_angles_fps=_ANGLES_FPS,
    )
    assert pair is not None
    return pair


@pytest.mark.parametrize("u", [4, 20, 44, 60, 76])
def test_reference_still_is_taken_at_the_same_moment(fake_videos, u):
    """기준 still 은 학생 still 과 같은 시각의 영상 프레임이어야 한다 (같은 테이크 → 같은 번호)."""
    pair = _pair(_same_take_match(79, 118), u, 118)
    try:
        assert _red(pair.reference_frame_path) == u, "기준 still 이 다른 순간에서 뽑혔다"
        # 정량화는 기준 **각도**를 인덱싱한다 — 그 공간의 같은 시각 행.
        assert pair.ref_frame_idx == int(round(u * _ANGLES_FPS / _FRAMES_FPS))
        # Gemini 캐시 키·메타는 실제로 보낸 이미지의 번호.
        assert pair.ref_image_idx == u
    finally:
        for p in pair.cleanup_paths:
            Path(p).unlink(missing_ok=True)


def test_reference_window_offset_is_added_back(fake_videos):
    """창이 미끄러진 경우(ref_start>0) — path 의 window-local 인덱스를 전체 기준 인덱스로."""
    m = _same_take_match(79, 118, ref_start=12)
    pair = _pair(m, 40, 118)
    try:
        assert pair.ref_frame_idx == 60          # 40 × 1.5 (전체 기준 각도 공간)
        assert _red(pair.reference_frame_path) == 40
    finally:
        for p in pair.cleanup_paths:
            Path(p).unlink(missing_ok=True)


def test_matched_ref_frame_is_global_and_unchanged_without_offset():
    base = [(i, i) for i in range(5)]
    m0 = MotionMatch(start=0, end=5, ref_start=0, ref_end=5, distance=0.0, path=base)
    m7 = MotionMatch(start=0, end=5, ref_start=7, ref_end=12, distance=0.0, path=base)
    assert fz._matched_ref_frame(m0, 2, 100) == 2      # 종전과 동일
    assert fz._matched_ref_frame(m7, 2, 100) == 9      # window-local 2 + ref_start 7
