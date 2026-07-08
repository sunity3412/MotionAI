"""fault_zoom DTW 성공 경로 fps 정합 + ratio 근사 제거 + refMatch 방출 회귀 가드 (28-05).

D2(파일럿) 종결 두 메커니즘을 못 박는다:
  1. DTW "성공" 경로의 fps 오독 — `_matched_ref_frame` 반환은 ref angles(keypointReport)
     fps 공간(phase4_v1=18fps, 28-01 실측)인데 9fps frames 배열에 그대로 인덱싱하면
     시간이 2배로 밀려 엉뚱한(끝프레임 클램프) 정은지 프레임이 확대된다.
  2. 대응 실패 시 시간비례(ratio) 근사 — 어느 pose 인지 모르는 채 시간만 맞춘 프레임을
     확대해 "비교 부위 아닌 곳" 을 보여준다. 제거 후 ref 전신 폴백 + refMatch='failed'.

또한 refMatch scalar 가 app.py `_render_fault_zoom` mapper 를 통과해 최종 comparisons
list 까지 생존하는지(HIGH-1) 를 mapper-level 로 검증한다.

순수 — PIL/numpy 외 의존 0 (mapper 테스트만 pipeline app 로드, S3/추출기 monkeypatch).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402


# ─────────── 합성 fixture (test_fault_zoom 관례 재사용) ───────────


def _frames(n: int, h: int = 200, w: int = 120) -> np.ndarray:
    """프레임 i 의 red 채널 = i*10 — ref crop 픽셀색으로 '어느 프레임' 검증."""
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    for i in range(n):
        a[i, :, :, 0] = (i * 10) % 255
    return a


def _report(n: int, fps: float, joints=("left_knee", "right_knee", "left_hip")):
    nj = len(joints)
    data: list[float] = []
    for _f in range(n):
        for _j in range(nj):
            data += [0.5, 0.5]  # 중앙 (전부 valid)
    return {"joints": list(joints), "frames": n, "fps": fps, "data": data}


@dataclass
class _Match:
    start: int
    path: list


def _ref_red(png: bytes) -> int:
    """합성 [user|ref] PNG 의 ref 반쪽 중앙 red — ref crop 출처 프레임 식별."""
    from io import BytesIO

    from PIL import Image

    x = fz._OUT + 6 + fz._OUT // 2
    y = fz._OUT // 2
    return Image.open(BytesIO(png)).convert("RGB").getpixel((x, y))[0]


# ─────────── Task 1 — DTW 성공 경로 fps 정합 (표시 경로 전용 변환) ───────────


def test_dtw_ref_frame_converts_18fps_angles_to_9fps_frames():
    """ref angles 18fps / frames 9fps, path=[(i,2i)] → ref frames 인덱스 = i (같은 시간).

    구 코드는 ref angles 인덱스(2i)를 9fps frames 배열에 그대로 인덱싱 + r_n 으로
    클램프해 2배 오독/끝프레임 클램프(=D2). u_idx=6 → ref angles 12 → 9fps frames 6
    (red 60). 구 코드였다면 12 를 r_n-1=9 로 클램프 → red 90.
    """
    n = 10
    m = _Match(start=0, path=[(i, 2 * i) for i in range(n)])
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n),
        _report(n, 9.0), _report(2 * n, 18.0),  # user 9fps / ref angles 18fps
        worst_seconds=0.5, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0, dtw_match=m, user_frame_idx=6,
    )
    assert len(comps) == 1
    assert _ref_red(comps[0]["png"]) == 60, "ref frames 인덱스 = 6 (18fps→9fps 변환)"


def test_dtw_ref_frame_identity_when_both_9fps():
    """9fps/9fps(mode3 도메인) path=[(i,i)] → ref frames 인덱스 == i (변환 identity).

    mode1 전용(18fps) 규칙 하드코딩이 아님을 증명 (Pitfall 6) — fps 는 인자.
    """
    n = 10
    m = _Match(start=0, path=[(i, i) for i in range(n)])
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n),
        _report(n, 9.0), _report(n, 9.0),  # 양측 9fps
        worst_seconds=0.5, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0, dtw_match=m, user_frame_idx=6,
    )
    assert len(comps) == 1
    assert _ref_red(comps[0]["png"]) == 60, "9fps identity — ref frames 인덱스 == 6"


def test_dtw_ref_clamp_domain_is_angles_not_frames():
    """클램프 도메인 = ref angles(keypointReport) 프레임 수 r_rep_frames, frames 수 r_n 아님.

    ref angles 20프레임(18fps) / frames 10(9fps). path=[(6,15)] → ref angles 15 는
    r_n=10 이 아니라 r_rep_frames=20 안이라 클램프 안 됨 → 9fps frames 인덱스
    round(15/18*9)=8 (red 80). 구 코드는 15 를 r_n-1=9 로 클램프 → red 90.
    """
    m = _Match(start=0, path=[(6, 15)])
    comps = fz.build_fault_zoom_comparisons(
        _frames(10), _frames(10),
        _report(10, 9.0), _report(20, 18.0),
        worst_seconds=0.5, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0, dtw_match=m, user_frame_idx=6,
    )
    assert len(comps) == 1
    assert _ref_red(comps[0]["png"]) == 80, "angles 15 → frames 8 (r_rep_frames 클램프)"
