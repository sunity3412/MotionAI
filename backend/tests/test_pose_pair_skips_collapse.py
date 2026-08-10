"""짝 선정(운영 카드 경로)이 붕괴 프레임을 건너뛴다 (quick-260810-ms2).

`select_confident_index` 에만 배제를 넣은 U6(quick-260810-e4v)은 **실행되지 않았다** —
08-10 Pod 실측(p34fresh1786343621) 로그가 `fault_zoom_pose_pair` 5/5 였고 카드 5장의
프레임이 U6 전후 완전 동일(106/76, 118/82, 276/196, 96/24, 142/196)했다. 운영 경로의
실제 선택자는 `select_pose_matched_pair` 이므로 배제는 여기 있어야 한다.

**왜 양쪽인가**: 학생 프레임이 붕괴하면(관절이 폴 위 한 줄로 뭉침) 포즈 거리 최소인
기준 프레임도 같이 뭉개진 프레임이 된다 — 붕괴가 붕괴를 끌어당긴다.

각 배제 테스트에는 **대조군**을 붙였다: 같은 데이터에서 붕괴만 없애면 종전 승자가
그대로 뽑힌다. 대조군이 없으면 "배제가 이겼다"와 "애초에 그게 답이었다"를 못 가른다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis import pose_collapse  # noqa: E402

JOINTS = ["left_shoulder", "right_shoulder", "left_hip", "right_hip",
          "left_knee", "right_knee", "left_elbow", "right_elbow"]
MEMBERS = ("right_elbow", "right_shoulder")

# 깨끗한 포즈 — x 가 전부 흩어져 있다.
P1 = [[0.20 + 0.06 * i, 0.25 + 0.05 * i] for i in range(8)]

# 폴 위 한 세로선 (08-10 실측 패턴) — x 동일.
BAR = [[0.500, 0.30 + 0.04 * i] for i in range(8)]

# 앞 4관절 x 가 **거의** 같은 깨끗한 포즈(양자화로 갈린다 → 붕괴 아님).
P2 = [[0.400 + 0.0001 * i, 0.25 + 0.05 * i] for i in range(4)] + \
     [[0.46 + 0.06 * (i - 4), 0.25 + 0.05 * i] for i in range(4, 8)]
# 같은 포즈인데 앞 4관절 x 가 **정확히 같은** 값 → 붕괴로 판정된다. 좌표 이동은 1e-4 대라
# 포즈 거리는 거의 0 — "가장 닮았는데 붕괴"인 프레임을 만든다.
P2_SNAP = [[0.400, p[1]] for p in P2[:4]] + [list(p) for p in P2[4:]]
# 형상이 실제로 다른 이웃 (마지막 관절 y 이동) — 붕괴는 아니고 거리는 P2_SNAP 보다 멀다.
P2_FAR = [list(p) for p in P2[:7]] + [[P2[7][0], P2[7][1] + 0.03]]
# 아예 다른 포즈 — 어떤 후보보다도 멀어야 한다.
OTHER = [[0.10 + 0.02 * i, 0.80 - 0.03 * i] for i in range(8)]


def _report(frames: list[list[list[float]]], conf: float = 0.9) -> dict:
    return {
        "joints": JOINTS, "fps": 9.0, "frames": len(frames),
        "data": [c for f in frames for p in f for c in p],
        "confidence": [conf] * (len(frames) * len(JOINTS)),
        "version": "test",
    }


def _pair(user_frames, ref_frames, u_cands, r_cands, **kw):
    return fz.select_pose_matched_pair(
        _report(user_frames), _report(ref_frames),
        list(u_cands), list(r_cands), MEMBERS, len(ref_frames),
        frames_fps=9.0,
        user_rep_fps=9.0, user_rep_frames=len(user_frames),
        ref_rep_fps=9.0, ref_rep_frames=len(ref_frames),
        search_seconds=kw.get("search_seconds", 0.5),
        traj_radius=kw.get("traj_radius", 0),
    )


# ── 전제: 테스트 데이터가 의도한 대로 붕괴/정상으로 갈리는가 ──────────────────
def test_fixture_collapse_judgments_are_as_intended() -> None:
    assert pose_collapse.is_collapsed(BAR) is True
    assert pose_collapse.is_collapsed(P2_SNAP) is True
    assert pose_collapse.is_collapsed(P1) is False
    assert pose_collapse.is_collapsed(P2) is False
    assert pose_collapse.is_collapsed(P2_FAR) is False


def test_is_collapsed_frame_is_the_single_source() -> None:
    """붕괴 판정 단일 출처 — 리포트 프레임 인덱스로 직접 묻는다(창 승급이 이걸 쓴다)."""
    rep = _report([P1, BAR, P2_SNAP])
    assert fz.is_collapsed_frame(rep, 0) is False
    assert fz.is_collapsed_frame(rep, 1) is True
    assert fz.is_collapsed_frame(rep, 2) is True


def test_is_collapsed_frame_fail_open_without_joints_meta() -> None:
    """joints 메타 부재(legacy 리포트) = 판정 불가 → False. 종전 경로 유지."""
    rep = _report([BAR])
    rep["joints"] = []
    assert fz.is_collapsed_frame(rep, 0) is False


# ── 원본 해상도 프레임 폴백 ───────────────────────────────────────────────────
class _Arr:
    """ndim 만 흉내내는 최소 스텁 (numpy 없이 계약만 확인)."""

    def __init__(self, ndim: int, tag: str) -> None:
        self.ndim, self.tag = ndim, tag


def test_native_frame_used_when_provider_returns_one() -> None:
    small = [_Arr(3, "small0"), _Arr(3, "small1")]
    got = fz.native_or_downscaled(lambda w, i: _Arr(3, "native%d" % i), "user", 1, small)
    assert got.tag == "native1"


def test_falls_back_to_downscaled_without_provider() -> None:
    small = [_Arr(3, "small0"), _Arr(3, "small1")]
    assert fz.native_or_downscaled(None, "user", 1, small).tag == "small1"


def test_falls_back_when_provider_raises() -> None:
    """원본 추출 실패는 표시 품질 저하일 뿐 — 카드는 나와야 한다."""
    small = [_Arr(3, "small0")]

    def _boom(_w, _i):
        raise RuntimeError("ffmpeg died")

    assert fz.native_or_downscaled(_boom, "user", 0, small).tag == "small0"


def test_falls_back_when_provider_returns_unusable() -> None:
    """None·비정상 shape 도 폴백 — 잘못된 배열을 크롭에 흘리지 않는다."""
    small = [_Arr(3, "small0")]
    assert fz.native_or_downscaled(lambda w, i: None, "user", 0, small).tag == "small0"
    assert fz.native_or_downscaled(
        lambda w, i: _Arr(2, "flat"), "user", 0, small
    ).tag == "small0"


# ── 학생 측 배제 ─────────────────────────────────────────────────────────────
def test_collapsed_user_candidate_is_skipped() -> None:
    """학생 후보가 붕괴면 그 짝이 거리 0 이어도 뽑히지 않는다."""
    got = _pair([BAR, P1], [BAR, P1], [0, 1], [0, 1])
    assert got == (1, 1), f"붕괴한 pos 0 을 피하고 깨끗한 pos 1 을 골라야 함: {got}"


def test_control_same_data_without_collapse_picks_pos0() -> None:
    """대조군 — 붕괴만 없애면 종전 승자(pos 0)가 그대로 뽑힌다."""
    got = _pair([OTHER, P1], [OTHER, P1], [0, 1], [0, 1])
    assert got == (0, 0), f"붕괴가 없으면 pos 0 이 이겨야 함(데이터 전제 확인): {got}"


def test_falls_back_when_every_user_candidate_is_collapsed() -> None:
    """전 후보가 붕괴면 배제를 포기한다 — 카드가 사라지는 것보다 낫다(fail-open)."""
    got = _pair([BAR, BAR], [BAR, BAR], [0, 1], [0, 1])
    assert got is not None, "전건 붕괴에서 None 이면 카드가 통째로 사라진다"
    assert got == (0, 0), f"fail-open 은 종전 규칙 산출과 같아야 함: {got}"


# ── 기준 측 배제 ─────────────────────────────────────────────────────────────
def test_collapsed_ref_frame_is_skipped() -> None:
    """기준 탐색에서 붕괴 프레임을 건너뛴다 — 학생이 깨끗해도 짝이 뭉개질 수 있다."""
    ref = [OTHER, OTHER, OTHER, OTHER, P2_SNAP, P2_FAR, OTHER, OTHER]
    got = _pair([P2], ref, [0], [4])
    assert got == (0, 5), f"붕괴한 r=4 를 피하고 r=5 를 골라야 함: {got}"


def test_control_ref_frame_without_collapse_is_picked() -> None:
    """대조군 — r=4 가 붕괴가 아니면 그것이 뽑힌다(더 닮았으므로)."""
    ref = [OTHER, OTHER, OTHER, OTHER, P2, P2_FAR, OTHER, OTHER]
    got = _pair([P2], ref, [0], [4])
    assert got == (0, 4), f"붕괴가 없으면 더 닮은 r=4 가 이겨야 함: {got}"


def test_falls_back_when_every_ref_frame_in_range_is_collapsed() -> None:
    """기준 범위가 전부 붕괴면 배제를 포기한다(fail-open)."""
    ref = [BAR, BAR, BAR, BAR, BAR, BAR, BAR, BAR]
    got = _pair([BAR], ref, [0], [4])
    assert got is not None, "전건 붕괴에서 None 이면 카드가 사라진다"


# ── fail-open 은 축별로 (2차 수리) ────────────────────────────────────────────
def test_user_all_collapsed_still_keeps_ref_exclusion() -> None:
    """학생이 전건 붕괴여도 **기준 축 배제는 살린다** — 08-10 right_elbow 실측 결함.

    1차 구현은 두 축을 한 덩어리로 묶어, 학생이 전건 붕괴면 기준 배제까지 같이 풀렸다
    (재분석 p34fresh1786347291: right_elbow 만 u/r 양쪽 불변 118/82).
    """
    ref = [OTHER, OTHER, OTHER, OTHER, BAR, P2_FAR, OTHER, OTHER]
    got = _pair([BAR], ref, [0], [4])
    assert got is not None
    assert got[1] != 4, f"학생이 다 깨졌다고 기준 붕괴(r=4)까지 허용하면 안 됨: {got}"


def test_control_user_all_collapsed_picks_collapsed_ref_without_staging() -> None:
    """대조군 — 기준 후보가 붕괴뿐이면(다른 축 선택지 없음) 그것을 쓴다(최종 fail-open)."""
    ref = [OTHER, OTHER, OTHER, OTHER, BAR, BAR, OTHER, OTHER]
    got = _pair([BAR], ref, [0], [4])
    assert got is not None, "마지막 단계까지 내려가면 배제 없이라도 짝을 내야 한다"
