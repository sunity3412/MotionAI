"""frame_extractor.probe_duration_sec — 추출 없이 메타로 길이 (Phase 38-07 Task 2, 리뷰 R9).

`probe_effective_fps` 와 같은 reader/meta 어법이다. 판정 불가는 None — 0 이나 추정값으로 눙치지
않는다(모듈 상단 규율). 호출측(`_register_reference`)이 None 이면 `extract(end_s=상한+1)` 캡으로
2차 방어한다. imageio 는 monkeypatch — 실제 디코딩 0.
"""

from __future__ import annotations

import math

import pytest

from sunity_shared.analysis import frame_extractor as fe


class _Reader:
    def __init__(self, meta: dict | None, *, meta_exc: Exception | None = None) -> None:
        self._meta = meta
        self._meta_exc = meta_exc
        self.closed = False

    def get_meta_data(self) -> dict:
        if self._meta_exc is not None:
            raise self._meta_exc
        return dict(self._meta or {})

    def close(self) -> None:
        self.closed = True

    def __iter__(self):
        raise AssertionError("probe 는 프레임을 읽지 않는다")


def _patch(monkeypatch, reader: _Reader | None = None, exc: Exception | None = None):
    def get_reader(_path):
        if exc is not None:
            raise exc
        return reader

    monkeypatch.setattr(fe.imageio, "get_reader", get_reader)


def test_probe_duration_from_meta(monkeypatch):
    r = _Reader({"duration": 12.34, "fps": 30, "nframes": 370})
    _patch(monkeypatch, r)
    assert fe.FfmpegFrameExtractor().probe_duration_sec("/tmp/x.mp4") == pytest.approx(12.34)
    assert r.closed is True


def test_probe_duration_falls_back_to_nframes_over_fps(monkeypatch):
    _patch(monkeypatch, _Reader({"fps": 30, "nframes": 300}))
    assert fe.FfmpegFrameExtractor().probe_duration_sec("/tmp/x.mp4") == pytest.approx(10.0)


@pytest.mark.parametrize(
    "meta",
    [
        {},
        {"fps": 30},
        {"nframes": 300},
        {"fps": 0, "nframes": 300},
        {"fps": 30, "nframes": math.inf},
        {"duration": 0.0},
        {"duration": -3.0},
        {"duration": math.inf},
        {"duration": "12"},
    ],
)
def test_probe_duration_none_when_unknown(monkeypatch, meta):
    """duration 이 유한·양수가 아니고 nframes/fps 도 못 쓰면 None — 추정값 금지."""
    _patch(monkeypatch, _Reader(meta))
    assert fe.FfmpegFrameExtractor().probe_duration_sec("/tmp/x.mp4") is None


def test_probe_duration_bad_duration_uses_nframes_fallback(monkeypatch):
    _patch(monkeypatch, _Reader({"duration": math.nan, "fps": 25, "nframes": 250}))
    assert fe.FfmpegFrameExtractor().probe_duration_sec("/tmp/x.mp4") == pytest.approx(10.0)


def test_probe_duration_reader_open_failure_is_none(monkeypatch):
    _patch(monkeypatch, exc=OSError("cannot open"))
    assert fe.FfmpegFrameExtractor().probe_duration_sec("/tmp/missing.mp4") is None


def test_probe_duration_meta_failure_is_none_and_closes(monkeypatch):
    r = _Reader(None, meta_exc=RuntimeError("broken meta"))
    _patch(monkeypatch, r)
    assert fe.FfmpegFrameExtractor().probe_duration_sec("/tmp/x.mp4") is None
    assert r.closed is True


def test_probe_duration_does_not_record_effective_fps(monkeypatch):
    """길이 probe 는 fps 이력을 만들지 않는다 — `effective_fps_for` 는 추출 이력만(quick-260810-e4v)."""
    _patch(monkeypatch, _Reader({"duration": 8.0, "fps": 30}))
    ext = fe.FfmpegFrameExtractor()
    assert ext.probe_duration_sec("/tmp/x.mp4") == pytest.approx(8.0)
    assert ext.effective_fps_for("/tmp/x.mp4") is None
