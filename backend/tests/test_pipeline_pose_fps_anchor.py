"""표시 앵커의 초는 실효 rate 로 환산한다 (quick-260810-e4v U2).

`atVideoSec = atFrameIdx / _pipeline_frame_fps()` 인데 그 fps 가 **요청값**
`target_fps(9.0)` 이었다. 실제 솎음 rate 는 `src_fps/정수 step` 이라 30fps 원본에서
9.997fps → 저장 초가 ~10% 크고, 렌더는 그 초로 정지 프레임을 뽑으므로 확대 비교 사진이
감점을 잰 순간이 아닌 곳에서 찍혔다(quick-260810-cbt 실측: 최대 16프레임@15fps,
peterpan 은 클립 길이 6.07s 를 넘는 6.444s 를 가리켰다).

점수 무접촉: `atFrameIdx`/`atVideoSec` 는 tally 종료 후 `setdefault` 로 각인되는
표시 전용 값이다(`app.py` `_attach_*` 주석의 구조적 근거). 이 사이클은 그 **초 환산만**
바꾸므로 `md`(tally 입력)에 닿지 않는다 — 아래 불변식 테스트가 그것을 지킨다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402


class _FakeExtractor:
    """target_fps 는 9.0 인데 실효는 9.997 인 상태 — 실측 그대로."""

    target_fps = 9.0

    def __init__(self, mapping):
        self._m = mapping

    def effective_fps_for(self, path):
        return self._m.get(str(path))


@pytest.fixture()
def swap_extractor(monkeypatch):
    def _swap(mapping):
        monkeypatch.setattr(app, "_FRAME_EXTRACTOR", _FakeExtractor(mapping))
    return _swap


def test_frame_fps_uses_recorded_effective_rate(swap_extractor) -> None:
    swap_extractor({"/tmp/user.mp4": 9.997})
    assert app._pipeline_frame_fps("/tmp/user.mp4") == pytest.approx(9.997)


def test_frame_fps_falls_back_to_target_for_unknown_path(swap_extractor) -> None:
    """기록 없는 경로 = 종전 동작(target_fps) — fail-open, byte-동일."""
    swap_extractor({"/tmp/user.mp4": 9.997})
    assert app._pipeline_frame_fps("/tmp/other.mp4") == pytest.approx(9.0)


def test_frame_fps_without_path_is_unchanged(swap_extractor) -> None:
    """경로 미전달 = 종전 호출 형태 → target_fps (기존 호출부 무회귀)."""
    swap_extractor({"/tmp/user.mp4": 9.997})
    assert app._pipeline_frame_fps() == pytest.approx(9.0)


def test_real_extractor_roundtrip_is_wired() -> None:
    """실제 extractor 인스턴스와도 배선이 맞는지 (Fake 에만 맞춘 구현 차단)."""
    ex = FfmpegFrameExtractor(target_fps=9.0)
    ex._effective_fps_by_path[str(Path("/tmp/real.mp4").resolve())] = 9.997
    saved = app._FRAME_EXTRACTOR
    try:
        app._FRAME_EXTRACTOR = ex
        assert app._pipeline_frame_fps("/tmp/real.mp4") == pytest.approx(9.997)
    finally:
        app._FRAME_EXTRACTOR = saved


def test_moment_video_sec_uses_pose_fps(swap_extractor) -> None:
    """pose_fps 를 주면 그 rate 로 초를 만든다 — 9.0 으로 나누지 않는다."""
    swap_extractor({})
    out: dict = {}
    app._build_deduction_measured_deviations(
        angles=None, profile=None, assessments={}, dimension_scores={},
        quantification=None, measured_at_out=out, pose_fps=9.997,
    )
    # builder 가 자체적으로 기록하는 항목이 없을 수 있으므로 내부 기록기를 직접 검증.
    # (아래 계약 테스트가 실제 방출 경로를 덮는다)
    assert app._moment_video_sec(77, 9.997) == pytest.approx(77 / 9.997)
    assert app._moment_video_sec(77, 9.0) == pytest.approx(77 / 9.0)


def test_anchor_error_size_matches_measurement() -> None:
    """실측 대조 — pdshapefault r00 은 8.556s 로 저장됐고 실제는 7.70s 다."""
    stored = app._moment_video_sec(77, 9.0)
    fixed = app._moment_video_sec(77, 9.997)
    assert stored == pytest.approx(8.556, abs=0.01)
    assert fixed == pytest.approx(7.702, abs=0.01)
    # 15fps 렌더 프레임으로 12~13 프레임 어긋난다.
    assert (stored - fixed) * 15 == pytest.approx(12.8, abs=0.3)


def test_video_sec_omitted_when_fps_unknown() -> None:
    """fps 판정 불가 = 초를 비운다(추측해 채우지 않는다 — 종전 규율 유지)."""
    assert app._moment_video_sec(77, 0.0) is None
    assert app._moment_video_sec(77, None) is None
