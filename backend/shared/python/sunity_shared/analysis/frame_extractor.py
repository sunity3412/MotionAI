"""영상 → 프레임 추출 (FrameExtractor 구현, #7-follow Phase 1).

imageio + imageio-ffmpeg 로 디코딩. 성능을 위해 두 축으로 다운샘플:
  - 시간축: target_fps(기본 9) 로 프레임 솎음 — DTW/각도 분석에 30fps 불필요
  - 공간축: 긴 변 max_side(기본 640) 로 리사이즈
reference 영상은 start_s~end_s(clipRange) 구간만 추출 (reference-motions.md §4).

interfaces.FrameExtractor 프로토콜 구현. start_s/end_s 는 옵셔널 확장 인자라
프로토콜(extract(path))과 호환된다.
"""

from __future__ import annotations

import imageio
import numpy as np
from PIL import Image


class FfmpegFrameExtractor:
    def __init__(self, target_fps: float = 9.0, max_side: int = 640) -> None:
        self.target_fps = target_fps
        self.max_side = max_side

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        longest = max(h, w)
        if longest <= self.max_side:
            return frame
        scale = self.max_side / longest
        size = (round(w * scale), round(h * scale))
        return np.asarray(Image.fromarray(frame).resize(size, Image.BILINEAR))

    def extract(
        self,
        local_video_path: str,
        start_s: float | None = None,
        end_s: float | None = None,
    ) -> np.ndarray:
        """영상 → (T, H, W, 3) RGB uint8. start_s~end_s 구간만(없으면 전체)."""
        reader = imageio.get_reader(local_video_path)
        try:
            meta = reader.get_meta_data()
            src_fps = float(meta.get("fps") or 30.0)
            step = max(1, round(src_fps / self.target_fps))
            start_idx = 0 if start_s is None else int(start_s * src_fps)
            end_idx = None if end_s is None else int(end_s * src_fps)

            frames: list[np.ndarray] = []
            for i, frame in enumerate(reader):
                if i < start_idx:
                    continue
                if end_idx is not None and i >= end_idx:
                    break
                if (i - start_idx) % step != 0:
                    continue
                rgb = np.asarray(frame)[:, :, :3]  # RGBA 입력 대비
                frames.append(self._resize(rgb))
        finally:
            reader.close()

        if not frames:
            raise ValueError(f"프레임을 추출하지 못했습니다: {local_video_path}")
        return np.stack(frames).astype(np.uint8)
