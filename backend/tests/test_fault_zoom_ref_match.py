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


# ─────────── Task 2 — ratio 근사 제거 + 전신 폴백 + refMatch 방출 (D-04) ───────────


def test_no_dtw_forces_ref_fullbody_and_failed_flag():
    """dtw_match=None(대응 실패) → ref 전신 폴백 + refMatch='failed', 학생 카드 유지.

    시간비례 근사(어느 pose 인지 모르는 채 시간만 맞춘 프레임 확대)를 제거하고 —
    ref 는 정직한 전신(오도 0), 앱은 refMatch 로 캡션. 세로 프레임(400x200)의 전신
    contain-fit 은 좌우 흰 패딩이 생겨 crop(프레임 내용)과 구별된다.
    """
    frames = _frames(9, h=400, w=200)
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0, dtw_match=None,
    )
    assert len(comps) == 1, "학생 카드는 유지 (D-04)"
    assert comps[0]["refMatch"] == "failed"
    assert isinstance(comps[0]["refMatch"], str), "scalar str (flat 제약)"
    # ref 전신 contain-fit → 좌상단 흰 패딩 (crop 이면 프레임 내용).
    from io import BytesIO

    from PIL import Image

    px = Image.open(BytesIO(comps[0]["png"])).convert("RGB").getpixel(
        (fz._OUT + 6 + 2, 2)
    )
    assert px == (255, 255, 255), "ref 전신 폴백 (부위 crop 아님)"


def test_dtw_success_emits_dtw_flag():
    """DTW 대응 성공 → refMatch=='dtw'."""
    n = 10
    m = _Match(start=0, path=[(i, i) for i in range(n)])
    comps = fz.build_fault_zoom_comparisons(
        _frames(n), _frames(n), _report(n, 9.0), _report(n, 9.0),
        worst_seconds=0.5, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0, dtw_match=m, user_frame_idx=6,
    )
    assert len(comps) == 1
    assert comps[0]["refMatch"] == "dtw"


def test_ref_frame_override_treated_as_dtw():
    """ref_frame_idx override 경로 = vision 측정 프레임 정합 → refMatch=='dtw'."""
    m = _Match(start=0, path=[(i, 0) for i in range(9)])
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.5, fault_joints=["left_knee"], joint_deltas=None,
        frames_fps=9.0, dtw_match=m, ref_frame_idx=5,
    )
    assert len(comps) == 1
    assert comps[0]["refMatch"] == "dtw"


def test_ratio_approximation_removed_from_source():
    """시간비례(ratio) 근사 코드가 소스에서 소멸 (주석 제외)."""
    src = Path(fz.__file__).read_text(encoding="utf-8")
    code = "\n".join(
        ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
    )
    assert "ratio * (r_n - 1)" not in code
    assert "ratio * (r_rep_frames - 1)" not in code


# ─────────── Task 2 (HIGH-1) — refMatch 가 app.py mapper 를 통과해 생존 ───────────


def _load_pipeline_app():
    _PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
    if str(_PIPELINE) not in sys.path:
        sys.path.insert(0, str(_PIPELINE))
    import app  # noqa: WPS433

    return app


def _patch_render_deps(app, monkeypatch, cards):
    """_render_fault_zoom 의 추출기/S3/build 를 스텁 — mapper 로직만 노출.

    frame_extractor 실모듈은 imageio(테스트 환경 미설치) 를 top-import 하므로 가짜
    모듈을 sys.modules 에 주입한다 — _render_fault_zoom 내부의 lazy
    `from ...frame_extractor import FfmpegFrameExtractor` 가 이 스텁을 집는다.
    """
    import types

    from sunity_shared.analysis import fault_zoom as fzmod

    class _FakeExt:
        def __init__(self, *a, **k) -> None:
            pass

        def extract(self, _path):
            return np.zeros((3, 8, 8, 3), dtype=np.uint8)

    fake_fe = types.ModuleType("sunity_shared.analysis.frame_extractor")
    fake_fe.FfmpegFrameExtractor = _FakeExt
    monkeypatch.setitem(
        sys.modules, "sunity_shared.analysis.frame_extractor", fake_fe
    )
    monkeypatch.setattr(fzmod, "build_fault_zoom_comparisons", lambda *a, **k: cards)

    class _FakeS3:
        def put_object(self, **k):
            return None

    monkeypatch.setattr(app, "_s3", _FakeS3())
    monkeypatch.setattr(app, "_signed_get", lambda b, k: "https://signed")


def _run_render(app):
    return app._render_fault_zoom(
        {}, "u.mp4", "r.mp4", {"joints": []}, {"joints": []},
        ["left_knee"], {"left_knee": 20.0}, {}, 0.5, "u1", "a1", "bucket",
    )


def test_mapper_preserves_refmatch_failed(monkeypatch):
    """build 가 refMatch='failed' 카드 반환 → 최종 comparisons[0].refMatch 생존 (HIGH-1)."""
    app = _load_pipeline_app()
    _patch_render_deps(app, monkeypatch, [
        {"joint": "left_knee", "deficitDeg": 20.0, "png": b"\x89PNG",
         "refMatch": "failed"},
    ])
    out = _run_render(app)
    assert out[0]["refMatch"] == "failed"


def test_mapper_preserves_refmatch_dtw(monkeypatch):
    """build 가 refMatch='dtw' 카드 반환 → 최종 comparisons[0].refMatch 생존."""
    app = _load_pipeline_app()
    _patch_render_deps(app, monkeypatch, [
        {"joint": "left_knee", "deficitDeg": 20.0, "png": b"\x89PNG",
         "refMatch": "dtw"},
    ])
    out = _run_render(app)
    assert out[0]["refMatch"] == "dtw"


def test_mapper_omits_refmatch_for_legacy_card(monkeypatch):
    """refMatch 없는 legacy 형상 카드 → 최종 item 에도 키 부재 (region 선례와 동일 조건부)."""
    app = _load_pipeline_app()
    _patch_render_deps(app, monkeypatch, [
        {"joint": "left_knee", "deficitDeg": 20.0, "png": b"\x89PNG"},
    ])
    out = _run_render(app)
    assert "refMatch" not in out[0]
