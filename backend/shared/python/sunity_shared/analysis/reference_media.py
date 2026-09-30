"""공급자 기준 영상 후처리 — 소리 제거 · 썸네일 한 장 (quick-260930-w9l, Pod 등록 경로 전용).

근거(belle 2026-09-30 폰 확인, 항목 8): 공급자 폼의 무음 체크·무음 동의가 "영상 소리까지 신경 써야
하느냐"는 부담이었다. 무음 동의를 없애는 대신 서버가 저장본의 소리를 지운다 — 그래서 소리 제거 실패는
등록 실패(fail-closed)다. 이 모듈은 그 보장을 하는 유일한 곳이다. 재인코딩은 하지 않는다(비디오 스트림
복사, `-an`) — 화질·프레임·회전 표식(displaymatrix)이 그대로 남아 등록 판정이 본 바이트와 재생·자기
재현성이 쓰는 바이트가 같은 영상이다.

썸네일 프레임(플래너 판단 3): 서 있는 시작 창의 가운데 순간 — 호출측이 t = (n_stand / real_fps) / 2 로
정한다. belle 08-31 썸네일 기각 사유가 "민망한 자세"·"사람이 거꾸로"였고, 등록을 통과한 영상은 이 창이
서 있는 자세임을 파이프라인이 이미 확인했다. 번들 11개(motionThumbs.ts, execPeakS 기준)는 이 규칙과
무관하다. 새 썸네일은 belle 눈 판정 대상이다.

의존: ffmpeg 바이너리는 imageio_ffmpeg 가 준다(RunPod requirements 에 있다). pipeline Lambda 에는
imageio_ffmpeg 가 없으므로 **함수 안에서** 지연 import 한다 — 이 모듈을 import 하는 것만으로 Lambda 가
깨지면 안 된다(최상단 import 는 표준 라이브러리만, tests/test_reference_media.py 가 잠근다).
보안: subprocess 리스트 인자(셸 없음), 경로는 서버 임시 파일, timeout, stderr 는 끝 500자만(T-w9l-06).
"""

from __future__ import annotations

import os
import re
import subprocess

_STRIP_TIMEOUT_S = 600
_THUMB_TIMEOUT_S = 60
_PROBE_TIMEOUT_S = 60
_STDERR_TAIL = 500
_CONTAINERS = ("mp4", "mov")
_STREAM_RE = re.compile(r"^\s*Stream #\d+:\d+.*?: (Video|Audio):", re.M)


class ReferenceMediaError(RuntimeError):
    """ffmpeg 실패 · 읽을 수 없는 입력 · 결과 파일 없음. 메시지는 stderr 끝 500자 이하."""


def _ffmpeg() -> str:
    import imageio_ffmpeg  # 지연 import — pipeline Lambda 에는 없다.

    return imageio_ffmpeg.get_ffmpeg_exe()


def _tail(text: str) -> str:
    text = (text or "").strip()
    return text[-_STDERR_TAIL:]


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [_ffmpeg(), "-hide_banner", "-nostdin", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise ReferenceMediaError(f"ffmpeg timeout {timeout}s") from e
    except OSError as e:
        raise ReferenceMediaError(f"ffmpeg 실행 실패 {type(e).__name__}") from e


def _stream_kinds(path: str) -> list[str]:
    """`ffmpeg -i path` stderr 의 스트림 종류 목록. 출력 파일이 없어 종료코드는 늘 1 이다 —
    스트림 줄이 하나도 없으면 읽을 수 없는 입력으로 본다."""
    proc = _run(["-i", path], _PROBE_TIMEOUT_S)
    kinds = _STREAM_RE.findall(proc.stderr or "")
    if not kinds:
        raise ReferenceMediaError(_tail(proc.stderr) or "스트림 없음")
    return kinds


def has_audio(path: str) -> bool:
    """오디오 스트림이 하나라도 있으면 True. 읽을 수 없는 파일은 ReferenceMediaError."""
    return "Audio" in _stream_kinds(path)


def strip_audio(src: str, dst: str, container: str) -> None:
    """첫 비디오 스트림만 **스트림 복사**로 dst 에 쓴다(오디오·자막·데이터 제거, 재인코딩 없음).

    container ∈ {'mp4','mov'} — 원본 확장자와 같게(같은 v1 키에 다시 올린다). 회전 표식은 스트림
    복사로 남는다. 실패·빈 결과는 ReferenceMediaError.
    """
    if container not in _CONTAINERS:
        raise ValueError(f"container 는 {_CONTAINERS} 중 하나: {container!r}")
    proc = _run(
        [
            "-y",
            "-i", src,
            "-map", "0:v:0",
            "-c:v", "copy",
            "-an", "-sn", "-dn",
            "-map_metadata", "0",
            "-movflags", "+faststart",
            "-f", container,
            dst,
        ],
        _STRIP_TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise ReferenceMediaError(_tail(proc.stderr) or f"ffmpeg rc={proc.returncode}")
    if not os.path.exists(dst) or os.path.getsize(dst) == 0:
        raise ReferenceMediaError("무음본이 비었다")


def extract_thumbnail(src: str, t_sec: float, dst: str, width: int = 360) -> None:
    """t_sec 순간의 프레임 한 장을 가로 width px jpg 로(세로는 비율 유지, 짝수).

    회전 표식은 ffmpeg 기본 자동 회전으로 반영된다(폰 세로 영상 → 세로 썸네일). t_sec 가 영상 길이를
    넘으면 프레임이 없어 ReferenceMediaError — 호출측이 길이 안으로 자른다.
    """
    t = max(0.0, float(t_sec))
    proc = _run(
        [
            "-y",
            "-ss", f"{t:.3f}",
            "-i", src,
            "-frames:v", "1",
            "-vf", f"scale={int(width)}:-2",
            "-q:v", "4",
            dst,
        ],
        _THUMB_TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise ReferenceMediaError(_tail(proc.stderr) or f"ffmpeg rc={proc.returncode}")
    if not os.path.exists(dst) or os.path.getsize(dst) == 0:
        raise ReferenceMediaError("썸네일 프레임 없음")
