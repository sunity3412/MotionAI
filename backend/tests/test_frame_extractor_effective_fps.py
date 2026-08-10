"""실효 솎음 rate 를 산출·기록한다 (quick-260810-e4v U1).

`extract()` 는 `step = max(1, round(src_fps / target_fps))` 정수 step 으로 솎으므로
실제 산출 rate 는 `src_fps / step` 이고 요청값 `target_fps` 와 같지 않다. 그런데
파이프라인은 요청값으로 프레임↔초를 환산해 왔다(quick-260810-cbt 실측: 30fps 원본에서
실제 9.997fps → 저장 초가 9.7~10.0% 큼 → 확대 비교 사진의 앵커가 최대 16프레임 어긋남,
peterpan 은 클립 밖 6.444s > 6.07s 를 가리켰다).

여기서는 **산출 배열을 바꾸지 않고** 실효 rate 를 산출·기록만 한다. 기록을 경로별로
두는 이유: 한 분석에서 사용자·기준·이전 영상을 같은 인스턴스로 추출하므로 단일 속성이면
서로 덮어써 조용히 오염된다.
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

if "imageio" not in sys.modules:  # 로컬 dev env 대비 (Pod 에는 정상 설치)
    fake = types.ModuleType("imageio")
    fake.get_reader = MagicMock()  # type: ignore[attr-defined]
    sys.modules["imageio"] = fake
if "PIL" not in sys.modules:
    pil_mod = types.ModuleType("PIL")
    image_mod = types.ModuleType("PIL.Image")
    image_mod.BILINEAR = 2  # type: ignore[attr-defined]
    image_mod.fromarray = MagicMock()  # type: ignore[attr-defined]
    pil_mod.Image = image_mod  # type: ignore[attr-defined]
    sys.modules["PIL"] = pil_mod
    sys.modules["PIL.Image"] = image_mod

from sunity_shared.analysis import frame_extractor as fe  # noqa: E402
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402


class FakeReader:
    def __init__(self, frames: list[np.ndarray], fps: float) -> None:
        self._frames, self._fps = frames, fps

    def get_meta_data(self) -> dict[str, float]:
        return {"fps": self._fps}

    def __iter__(self):
        return iter(self._frames)

    def close(self) -> None:
        pass


def _frames(n: int) -> list[np.ndarray]:
    return [np.full((8, 6, 3), i % 256, dtype=np.uint8) for i in range(n)]


def _extract(extractor, frames, src_fps, path="dummy.mp4", **kw):
    with patch("sunity_shared.analysis.frame_extractor.imageio.get_reader",
               return_value=FakeReader(frames, src_fps)):
        return extractor.extract(path, **kw)


# ── 순수 함수 ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "src_fps,target_fps,expected",
    [
        (30.0, 9.0, 10.0),        # 실측 케이스 — step 3, 요청 9 인데 실제 10
        (29.991, 9.0, 9.997),     # pdshapefault 실측
        (29.87, 18.0, 14.935),    # 기준 트랙(ref-pdshape) — 라벨 18, 실제 ~15
        (24.0, 9.0, 8.0),         # step 3 → 요청보다 느림 (부호가 반대로도 생긴다)
        (60.0, 9.0, 60.0 / 7),    # step 7
        (5.0, 9.0, 5.0),          # target > src → step 1, 원본 그대로
    ],
)
def test_effective_fps_is_src_over_integer_step(src_fps, target_fps, expected) -> None:
    assert fe.effective_fps(src_fps, target_fps) == pytest.approx(expected, abs=1e-3)


def test_effective_fps_rejects_nonpositive() -> None:
    """비정상 입력은 None — 0 이나 target_fps 로 눙치지 않는다(fail-closed)."""
    assert fe.effective_fps(0.0, 9.0) is None
    assert fe.effective_fps(30.0, 0.0) is None
    assert fe.effective_fps(-30.0, 9.0) is None
    assert fe.effective_fps(float("nan"), 9.0) is None


def test_effective_fps_never_equals_target_when_step_rounds() -> None:
    """요청값을 그대로 돌려주는 구현이면 이 테스트가 잡는다."""
    assert fe.effective_fps(30.0, 9.0) != 9.0


# ── extract() 기록 ─────────────────────────────────────────────────────────


def test_extract_records_effective_fps_per_path() -> None:
    ex = FfmpegFrameExtractor(target_fps=9.0)
    _extract(ex, _frames(60), 30.0, path="/tmp/user.mp4")   # step 3 → 10.0
    _extract(ex, _frames(40), 24.0, path="/tmp/ref.mp4")    # step 3 →  8.0

    # 같은 인스턴스로 추출한 두 영상이 서로 다른 실효 rate 를 갖고,
    # 나중 추출이 앞 기록을 덮지 않는다(단일 속성 구현이면 여기서 깨진다).
    assert ex.effective_fps_for("/tmp/user.mp4") == pytest.approx(10.0, abs=1e-3)
    assert ex.effective_fps_for("/tmp/ref.mp4") == pytest.approx(8.0, abs=1e-3)


def test_effective_fps_for_unknown_path_is_none() -> None:
    """미지 경로 = None → 호출측이 종전 동작으로 fail-open 할 수 있어야 한다."""
    ex = FfmpegFrameExtractor(target_fps=9.0)
    assert ex.effective_fps_for("/tmp/never-extracted.mp4") is None


def test_recording_does_not_change_frames() -> None:
    """산출 배열 무변경 — 기록은 부수효과일 뿐."""
    frames = _frames(60)
    a = _extract(FfmpegFrameExtractor(target_fps=9.0), frames, 30.0, path="/tmp/a.mp4")
    b = _extract(FfmpegFrameExtractor(target_fps=9.0), frames, 30.0, path="/tmp/b.mp4")
    assert a.shape == b.shape
    assert np.array_equal(a, b)


def test_recorded_rate_matches_produced_frame_count() -> None:
    """기록한 rate 가 실제 산출 프레임 수와 정합해야 한다 (자기검증).

    강제 마지막 프레임 1장을 뺀 본 표본은 `rate × 구간초` 와 맞아야 한다 —
    이 관계가 깨지면 기록이 거짓말을 하는 것이다.
    """
    src_fps, n = 29.991, 543          # pdshapefault 실측 (18.105s)
    ex = FfmpegFrameExtractor(target_fps=9.0)
    out = _extract(ex, _frames(n), src_fps, path="/tmp/p.mp4")
    rate = ex.effective_fps_for("/tmp/p.mp4")
    assert rate is not None
    # 실측 대조: joints3dFrames == 182 (강제 마지막 포함)
    assert out.shape[0] == 182
    duration = n / src_fps
    assert (out.shape[0] - 1) == pytest.approx(rate * duration, rel=0.01)


def test_path_normalised_so_same_file_reads_back() -> None:
    """상대·절대 경로 표기가 달라도 같은 파일이면 읽힌다(호출측 표기에 안 걸리게)."""
    ex = FfmpegFrameExtractor(target_fps=9.0)
    _extract(ex, _frames(60), 30.0, path="dummy.mp4")
    assert ex.effective_fps_for(str(Path("dummy.mp4").resolve())) == pytest.approx(10.0)
    assert ex.effective_fps_for("dummy.mp4") == pytest.approx(10.0)
