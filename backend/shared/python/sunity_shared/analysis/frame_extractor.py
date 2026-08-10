"""영상 → 프레임 추출 (FrameExtractor 구현, #7-follow Phase 1).

imageio + imageio-ffmpeg 로 디코딩. 성능을 위해 두 축으로 다운샘플:
  - 시간축: target_fps(기본 9) 로 프레임 솎음 — DTW/각도 분석에 30fps 불필요
  - 공간축: 긴 변 max_side(기본 640) 로 리사이즈
reference 영상은 start_s~end_s(clipRange) 구간만 추출 (reference-motions.md §4).

interfaces.FrameExtractor 프로토콜 구현. start_s/end_s 는 옵셔널 확장 인자라
프로토콜(extract(path))과 호환된다.
"""

from __future__ import annotations

import math
import os

import imageio
import numpy as np
from PIL import Image


def decimation_step(src_fps: float, target_fps: float) -> int | None:
    """extract() 가 실제로 쓰는 솎음 간격 — 정수. 비정상 입력은 None(fail-closed)."""
    for v in (src_fps, target_fps):
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            return None
    return max(1, round(float(src_fps) / float(target_fps)))


def effective_fps(src_fps: float, target_fps: float) -> float | None:
    """**실제 산출 rate** = src_fps / 정수 step. `target_fps` 와 같지 않다.

    `extract()` 는 정수 step 으로 솎으므로 요청값을 그대로 얻지 못한다 —
    30fps 원본에 target 9 를 주면 step 3 → **10.0fps** 가 나온다(요청보다 빠름),
    24fps 에 target 9 를 주면 step 3 → **8.0fps**(요청보다 느림). 어느 쪽이든
    프레임↔초 환산에 `target_fps` 를 쓰면 그만큼 시각이 어긋난다.

    실측 피해(quick-260810-cbt): 감점 record 의 `atVideoSec = atFrameIdx / 9.0` 가
    실제보다 9.7~10.0% 커서 확대 비교 사진이 감점을 잰 순간이 아닌 프레임에서
    찍혔다(최대 16프레임@15fps, peterpan 은 클립 길이를 넘는 6.444s 를 가리켰다).

    반환 None = 판정 불가(비정상 입력). 0 이나 target_fps 로 눙치지 않는다 —
    모르는 것과 아는 것을 섞으면 조용한 오차가 된다.
    """
    step = decimation_step(src_fps, target_fps)
    if step is None:
        return None
    return float(src_fps) / float(step)


def _norm_path(path) -> str:
    """기록 키 — 상대·절대 표기 차이로 못 읽는 일이 없게 정규화."""
    try:
        return os.path.realpath(str(path))
    except (TypeError, ValueError, OSError):
        return str(path)


class FfmpegFrameExtractor:
    def __init__(self, target_fps: float = 9.0, max_side: int = 640) -> None:
        self.target_fps = target_fps
        self.max_side = max_side
        # 경로 → 그 추출의 실효 rate. **경로별인 이유**: 한 분석에서 사용자·기준·
        # 이전 영상을 같은 인스턴스로 추출하므로(pipeline `_FRAME_EXTRACTOR` 싱글턴)
        # 단일 속성이면 나중 추출이 앞 기록을 덮어 조용히 오염된다.
        self._effective_fps_by_path: dict[str, float] = {}

    def effective_fps_for(self, path) -> float | None:
        """그 영상의 실효 솎음 rate — 추출 이력이 없으면 None (호출측 fail-open)."""
        return self._effective_fps_by_path.get(_norm_path(path))

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
            step = decimation_step(src_fps, self.target_fps) or 1
            # 실효 rate 기록 — 산출 배열 무접촉, 프레임↔초 환산의 단일 출처
            # (quick-260810-e4v U1). target_fps 로 환산하던 것이 표시 앵커를 어긋냈다.
            eff = effective_fps(src_fps, self.target_fps)
            if eff is not None:
                self._effective_fps_by_path[_norm_path(local_video_path)] = eff
            start_idx = 0 if start_s is None else int(start_s * src_fps)
            end_idx = None if end_s is None else int(end_s * src_fps)

            frames: list[np.ndarray] = []
            # 12-deferred §12-B — 마지막 frame 강제 포함 추적.
            # step 모듈로 떨어지지 않은 영상 끝의 잔여 frame 이 무시되면 결과 영상의
            # 마지막 ~step/src_fps 초가 keypoint 정지 표시되는 finding (belle UAT 2차).
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
                    rgb = np.asarray(frame)[:, :, :3]  # RGBA 입력 대비
                    last_resized = self._resize(rgb)
                    continue
                rgb = np.asarray(frame)[:, :, :3]  # RGBA 입력 대비
                last_resized = self._resize(rgb)
                frames.append(last_resized)
                last_idx_appended = i
        finally:
            reader.close()

        # 12-deferred §12-B — loop 종료 후 마지막 frame 이 step 모듈로 미달이라
        # 미포함된 경우 강제 추가. 영상 끝 keypoint 정지 finding 해소.
        if (
            last_resized is not None
            and last_idx_seen > last_idx_appended
        ):
            frames.append(last_resized)

        if not frames:
            raise ValueError(f"프레임을 추출하지 못했습니다: {local_video_path}")
        return np.stack(frames).astype(np.uint8)
