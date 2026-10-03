"""프레임 추출 — 버리는 프레임 축소 생략이 출력 바이트를 바꾸지 않는다 (quick-261003-svg).

배경: `FfmpegFrameExtractor.extract` 는 시간축 솎음(step)으로 버리는 프레임까지 매번
`_resize` 했다. 그 결과를 쓰는 곳은 루프 뒤 마지막 프레임 강제 포함(12-deferred §12-B)
하나뿐이었다. 로컬 실측(오케스트레이터 scratchpad fx_bench.py, HEVC 2160×3840 30fps
593프레임) 25.7초 중 ≈10초가 이 버리는 축소였다.

여기서 잠그는 것 두 가지:
  1. 출력 바이트 동일 — 새 extract 결과가 옛 루프를 그대로 복제한 `_extract_old` 결과와
     shape · dtype · `tobytes()` 모두 같다. 실제 PIL 축소가 일어나는 크기(긴 변 > max_side)로 잰다.
  2. 축소 호출 수 — `_resize` 는 남는 프레임 수 + (마지막 강제 포함이 일어나면 1) 만큼만 불린다.

진짜 PIL 이 필요하다(축소 바이트 비교가 목적). 그래서 다른 frame_extractor 테스트처럼
가짜 PIL/imageio stub 을 sys.modules 에 넣지 않고, FakeReader 도 이 파일 안에 따로 둔다
(그 모듈들을 import 하면 stub 이 따라 들어온다).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image  # noqa: F401 — 진짜 PIL 을 먼저 올린다(다른 테스트의 가짜 stub 방지)

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared" / "python"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from sunity_shared.analysis import frame_extractor as fe  # noqa: E402
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402

_GET_READER = "sunity_shared.analysis.frame_extractor.imageio.get_reader"


class FakeReader:
    """imageio Reader 의 최소 동작 — get_meta_data · __iter__ · close."""

    def __init__(self, frames: list[np.ndarray], fps: float) -> None:
        self._frames = frames
        self._fps = fps

    def get_meta_data(self) -> dict[str, float]:
        return {"fps": self._fps}

    def __iter__(self):
        return iter(self._frames)

    def close(self) -> None:
        pass


def _frames(n: int, h: int, w: int, channels: int = 3) -> list[np.ndarray]:
    """프레임마다 내용이 다른 uint8 배열 — idx 를 시드로 채운다."""
    return [
        np.random.default_rng(idx).integers(0, 256, size=(h, w, channels), dtype=np.uint8)
        for idx in range(n)
    ]


def _extract_old(extractor: FfmpegFrameExtractor, path, start_s=None, end_s=None) -> np.ndarray:
    """quick-261003-svg 이전 구현 — 바이트 비교 기준.

    frame_extractor.py extract 루프(변경 전)를 그대로 복제했다. 버리는 프레임에서도
    `extractor._resize` 를 부른다. meta fps · decimation_step 은 모듈 함수를 그대로 쓴다.
    `_effective_fps_by_path` 기록은 바이트와 무관해 뺐다.
    """
    reader = fe.imageio.get_reader(path)
    try:
        meta = reader.get_meta_data()
        src_fps = float(meta.get("fps") or 30.0)
        step = fe.decimation_step(src_fps, extractor.target_fps) or 1
        start_idx = 0 if start_s is None else int(start_s * src_fps)
        end_idx = None if end_s is None else int(end_s * src_fps)

        frames: list[np.ndarray] = []
        last_resized: np.ndarray | None = None
        last_idx_seen = -1
        last_idx_appended = -1
        for i, frame in enumerate(reader):
            if i < start_idx:
                continue
            if end_idx is not None and i >= end_idx:
                break
            last_idx_seen = i
            if (i - start_idx) % step != 0:
                rgb = np.asarray(frame)[:, :, :3]
                last_resized = extractor._resize(rgb)
                continue
            rgb = np.asarray(frame)[:, :, :3]
            last_resized = extractor._resize(rgb)
            frames.append(last_resized)
            last_idx_appended = i
    finally:
        reader.close()

    if last_resized is not None and last_idx_seen > last_idx_appended:
        frames.append(last_resized)

    if not frames:
        raise ValueError(f"프레임을 추출하지 못했습니다: {path}")
    return np.stack(frames).astype(np.uint8)


# (id, src_fps, target_fps, 프레임 수, start_s, end_s, 채널, 새 호출 수, 옛 호출 수)
_CASES = [
    ("a_divisible", 30.0, 9.0, 10, None, None, 3, 4, 10),
    ("b_remainder", 30.0, 9.0, 11, None, None, 3, 5, 11),
    ("c_clip_remainder", 10.0, 3.0, 20, 0.3, 1.1, 3, 4, 8),
    ("d_clip_divisible", 10.0, 3.0, 20, 0.3, 1.0, 3, 3, 7),
    ("e_start_only", 10.0, 3.0, 8, 0.2, None, 3, 3, 6),
    ("f_end_past_video", 10.0, 3.0, 8, None, 5.0, 3, 4, 8),
    ("g_step_one", 9.0, 9.0, 5, None, None, 3, 5, 5),
    ("h_rgba_remainder", 30.0, 9.0, 11, None, None, 4, 5, 11),
]
_IDS = [c[0] for c in _CASES]


@pytest.mark.parametrize(
    "case_id,src_fps,target_fps,n,start_s,end_s,channels,new_calls,old_calls",
    _CASES,
    ids=_IDS,
)
def test_output_bytes_identical_to_old_loop(
    case_id, src_fps, target_fps, n, start_s, end_s, channels, new_calls, old_calls
) -> None:
    """새 extract 와 옛 루프 복제가 바이트까지 같다 — 실제 PIL 축소 크기(H48×W80, max_side 32)."""
    if isinstance(fe.Image.fromarray, MagicMock):
        pytest.skip(
            "frame_extractor 가 다른 테스트 모듈의 가짜 PIL stub 으로 적재됐다 — "
            "축소 바이트 비교 불가(이 파일을 명령줄 앞에 두면 진짜 PIL 로 돈다)"
        )
    src = _frames(n, h=48, w=80, channels=channels)
    extractor = FfmpegFrameExtractor(target_fps=target_fps, max_side=32)

    with patch(_GET_READER, side_effect=lambda p: FakeReader(src, src_fps)):
        new = extractor.extract("dummy.mp4", start_s=start_s, end_s=end_s)
        old = _extract_old(extractor, "dummy.mp4", start_s=start_s, end_s=end_s)

    # 실제로 축소가 일어났는지(이 크기를 고른 이유) — 긴 변 80 → 32.
    assert new.shape[1:] == (19, 32, 3)
    assert new.shape == old.shape
    assert new.dtype == old.dtype == np.uint8
    assert np.array_equal(new, old)
    assert new.tobytes() == old.tobytes()
    assert new.shape[0] == new_calls


@pytest.mark.parametrize(
    "case_id,src_fps,target_fps,n,start_s,end_s,channels,new_calls,old_calls",
    _CASES,
    ids=_IDS,
)
def test_resize_called_only_for_kept_frames(
    monkeypatch, case_id, src_fps, target_fps, n, start_s, end_s, channels, new_calls, old_calls
) -> None:
    """`_resize` 호출 수 = 남는 프레임 + (마지막 강제 포함이면 1). 옛 루프는 범위 안 전 프레임."""
    src = _frames(n, h=24, w=16, channels=channels)  # max_side 640 → `_resize` 는 원본 반환
    extractor = FfmpegFrameExtractor(target_fps=target_fps, max_side=640)
    original = extractor._resize
    calls = {"n": 0}

    def spy(frame: np.ndarray) -> np.ndarray:
        calls["n"] += 1
        return original(frame)

    monkeypatch.setattr(extractor, "_resize", spy)

    with patch(_GET_READER, side_effect=lambda p: FakeReader(src, src_fps)):
        new = extractor.extract("dummy.mp4", start_s=start_s, end_s=end_s)
        new_count = calls["n"]
        calls["n"] = 0
        old = _extract_old(extractor, "dummy.mp4", start_s=start_s, end_s=end_s)
        old_count = calls["n"]

    assert new_count == new_calls
    assert old_count == old_calls
    assert new.shape[0] == new_calls
    assert np.array_equal(new, old)
