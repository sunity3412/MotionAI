"""quick-260930-w9l — `analysis.reference_media` (소리 제거 · 썸네일) 실제 ffmpeg 로 잠근다.

imageio_ffmpeg 가 없으면 건너뛴다(pipeline Lambda 환경에는 없다 — 모듈 import 자체는 그 환경에서도
깨지면 안 되므로 마지막 테스트가 최상단 import 를 확인한다). 입력은 lavfi 로 그때그때 만든다(tmp_path).

잠그는 것:
  · has_audio: 소리 있는 mp4 → True, 소리 없는 입력 → False, 깨진 파일 → ReferenceMediaError
  · strip_audio: 오디오 트랙 없음 · 비디오 프레임 수 동일(스트림 복사) · 회전 정보(displaymatrix) 유지 · mov 도 같다
  · extract_thumbnail: 회전된 320x180 → 세로 jpg(너비 360) · 길이를 넘는 t 는 ReferenceMediaError
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

imageio_ffmpeg = pytest.importorskip("imageio_ffmpeg")

from sunity_shared.analysis import reference_media  # noqa: E402
from sunity_shared.analysis.reference_media import ReferenceMediaError  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
_MODULE = (
    Path(__file__).resolve().parents[1]
    / "shared" / "python" / "sunity_shared" / "analysis" / "reference_media.py"
)


def _ff(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [FF, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _info(path: Path) -> str:
    """`ffmpeg -i` stderr — 출력 파일이 없어 종료코드는 1 이지만 스트림 정보는 나온다."""
    return subprocess.run(
        [FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True
    ).stderr


def _video_frames(path: Path) -> int:
    out = subprocess.run(
        [FF, "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "null", "-"],
        capture_output=True,
        text=True,
    ).stderr
    counts = re.findall(r"frame=\s*(\d+)", out)
    assert counts, out[-500:]
    return int(counts[-1])


def _make(tmp_path: Path, name: str, *, audio: bool, fmt: str = "mp4", rotate: int | None = None) -> Path:
    base = tmp_path / f"base_{name}.{fmt}"
    args = ["-f", "lavfi", "-i", "testsrc=size=320x180:rate=10:duration=2"]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2"]
    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        args += ["-c:a", "aac", "-shortest"]
    _ff(*args, str(base))
    if rotate is None:
        return base
    out = tmp_path / f"{name}.{fmt}"
    # 폰 세로 촬영 = 가로 픽셀 + 회전 표식. 스트림 복사로 표식만 건다.
    _ff("-display_rotation", str(rotate), "-i", str(base), "-c", "copy", str(out))
    return out


def test_has_audio_true_for_sine_track(tmp_path):
    src = _make(tmp_path, "av", audio=True)
    assert reference_media.has_audio(str(src)) is True


def test_has_audio_false_for_video_only(tmp_path):
    src = _make(tmp_path, "v", audio=False)
    assert reference_media.has_audio(str(src)) is False


def test_broken_file_raises(tmp_path):
    bad = tmp_path / "broken.mp4"
    bad.write_bytes(b"not a video at all")
    with pytest.raises(ReferenceMediaError):
        reference_media.has_audio(str(bad))
    with pytest.raises(ReferenceMediaError):
        reference_media.strip_audio(str(bad), str(tmp_path / "out.mp4"), "mp4")


@pytest.mark.parametrize("fmt", ["mp4", "mov"])
def test_strip_audio_removes_audio_keeps_frames_and_rotation(tmp_path, fmt):
    src = _make(tmp_path, "rot", audio=True, fmt=fmt, rotate=90)
    assert "displaymatrix" in _info(src)  # 전제: 입력에 회전 표식이 있다
    dst = tmp_path / f"silent.{fmt}"
    reference_media.strip_audio(str(src), str(dst), fmt)
    assert dst.exists() and dst.stat().st_size > 0
    assert reference_media.has_audio(str(dst)) is False
    info = _info(dst)
    assert re.search(r"Stream #\d+:\d+.*: Video:", info)
    assert "Audio:" not in info
    assert re.search(r"displaymatrix: rotation of -?90", info), info
    assert _video_frames(dst) == _video_frames(src)


def test_strip_audio_rejects_unknown_container(tmp_path):
    src = _make(tmp_path, "av", audio=True)
    with pytest.raises(ValueError):
        reference_media.strip_audio(str(src), str(tmp_path / "x.avi"), "avi")


def test_extract_thumbnail_is_portrait_for_rotated_input(tmp_path):
    src = _make(tmp_path, "rot", audio=False, rotate=90)
    dst = tmp_path / "thumb.jpg"
    reference_media.extract_thumbnail(str(src), 0.5, str(dst), width=360)
    info = _info(dst)
    m = re.search(r"Video: mjpeg.*?, (\d+)x(\d+)", info)
    assert m, info
    w, h = int(m.group(1)), int(m.group(2))
    assert w == 360 and h > w  # 세로 — 자동 회전이 적용됐다


def test_extract_thumbnail_past_end_raises(tmp_path):
    """구현 결정: 길이를 넘는 t 는 프레임을 못 뽑으므로 ReferenceMediaError(호출측이 t 를 자른다)."""
    src = _make(tmp_path, "v", audio=False)
    dst = tmp_path / "thumb.jpg"
    with pytest.raises(ReferenceMediaError):
        reference_media.extract_thumbnail(str(src), 50.0, str(dst))


def test_error_message_is_stderr_tail_only(tmp_path):
    bad = tmp_path / "broken.mp4"
    bad.write_bytes(b"x" * 10)
    with pytest.raises(ReferenceMediaError) as e:
        reference_media.strip_audio(str(bad), str(tmp_path / "o.mp4"), "mp4")
    assert len(str(e.value)) <= 600


def test_module_top_level_imports_are_stdlib_only():
    """pipeline Lambda 에는 imageio_ffmpeg 가 없다 — 최상단 import 로 깨지면 안 된다(지연 import)."""
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    tops = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = []
    for n in tops:
        if isinstance(n, ast.Import):
            names += [a.name for a in n.names]
        else:
            names.append(n.module or "")
    assert not any("imageio" in n for n in names), names
    assert set(names) <= {"__future__", "re", "subprocess", "os", "pathlib"}, names
