"""기준 크롭 매핑 사슬은 **진짜 시간축 매핑과 같아야 한다** (quick-260810-e4v U4).

`fault_zoom` 의 기준 크롭 인덱스는 두 단계 사슬이다:

    m (rep 인덱스)  --_to_rep_idx(m, 18.0, 9.0, ·)-->  라벨 9.0 공간
                    --ref_display_frame_index(·, ×4/3)-->  비디오 배열 인덱스

두 입력이 **둘 다 거짓**이다: 기준 라벨 18.0(실제 ~14.94)과 리터럴 9.0(실제 ~9.96).
그런데 결과는 진짜 매핑 `m × (렌더추출 실효 / 기준 실측)` 과 반올림(≤2프레임) 안에서
일치한다 — 07-27 에 belle 이 승인한 것이 그래서 옳았다.

★**왜 옳은가 — 우연이 아니라 대수적 소거다.** 사슬을 전개하면

    r_idx = m / rep_fps × frames_fps
    scale = video_n / (rep_frames × frames_fps / rep_fps)
    j     = r_idx × scale = m × video_n / rep_frames      ← fps 두 개가 전부 소거

즉 결과는 **프레임 수 비율**만으로 결정되고, 프레임 수는 참값이다. 그래서 라벨이
거짓이어도 맞는다. (내 1차 진단 "4/3 이 잔여 이중 보정"과 2차 "우연한 상쇄"는 둘 다
틀렸다 — 테스트가 정정했다.)

★**그래서 실제 취약점은 라벨이 아니라 짝의 일관성이다.** 두 호출에 **서로 다른** fps 를
주면(한쪽만 실효 rate 로 교체하는 부분 수리) 소거가 깨져 기준 크롭이 ~10% 어긋난다 —
승인본 카드가 조용히 깨진다. 이 파일이 그 짝을 못 박는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis.fault_zoom import (  # noqa: E402
    _to_rep_idx, ref_display_frame_index,
)
from sunity_shared.analysis.frame_extractor import (  # noqa: E402
    decimation_step, effective_fps,
)

LABEL_REP_FPS = 18.0      # 기준 doc 저장 라벨 (재처리 때 요청한 target)
LITERAL_FRAMES_FPS = 9.0  # app.py 가 fault_zoom 에 넘기는 리터럴
ROUNDING_SLACK = 2        # 두 경로의 반올림 차이 허용 (실측 최대 2프레임)

# (motionId, 기준영상 src_fps, 총 프레임, anglesFrames) — ffprobe·Firestore 실측
REFS = [
    ("ref-pdshape", 29.8734, 472, 237),
    ("ref-peter-pan", 29.7683, 256, 130),
    ("ref-power-spin", 30.0, 316, 159),
    ("ref-elbow-twist-sister", 29.9087, 654, 329),
    ("ref-kip-up", 30.0, 234, 118),
]


def _extracted_n(src_frames: int, step: int) -> int:
    """extract() 의 실제 산출 프레임 수 (강제 마지막 프레임 규칙 포함)."""
    idx = list(range(0, src_frames, step))
    return len(idx) + (1 if (src_frames - 1) > idx[-1] else 0)


def _chain(m: int, video_n: int, rep_frames: int) -> int:
    """운영 사슬 — app.py 가 실제로 주는 인자(거짓 라벨 두 개)로."""
    r_idx = _to_rep_idx(m, LABEL_REP_FPS, LITERAL_FRAMES_FPS, video_n)
    return ref_display_frame_index(
        r_idx, video_n, rep_frames, LABEL_REP_FPS, LITERAL_FRAMES_FPS
    )


def _truth(m: int, video_n: int, rep_real_fps: float, render_eff_fps: float) -> int:
    """진짜 매핑 — 시간축으로 직접 (rep 실측 rate → 렌더 추출 실효 rate)."""
    return min(video_n - 1, max(0, round(m / rep_real_fps * render_eff_fps)))


@pytest.mark.parametrize("mid,src_fps,src_frames,rep_frames", REFS)
def test_chain_matches_truth_for_every_rep_index(
    mid, src_fps, src_frames, rep_frames
) -> None:
    step = decimation_step(src_fps, LITERAL_FRAMES_FPS)
    video_n = _extracted_n(src_frames, step)
    render_eff = effective_fps(src_fps, LITERAL_FRAMES_FPS)
    rep_real = effective_fps(src_fps, LABEL_REP_FPS)

    worst, worst_m = 0, None
    for m in range(rep_frames):
        d = abs(_chain(m, video_n, rep_frames)
                - _truth(m, video_n, rep_real, render_eff))
        if d > worst:
            worst, worst_m = d, m
    assert worst <= ROUNDING_SLACK, (
        f"{mid}: rep 인덱스 {worst_m} 에서 사슬이 진짜 매핑과 {worst} 프레임 벌어짐. "
        f"라벨({LABEL_REP_FPS})·리터럴({LITERAL_FRAMES_FPS}) 중 한쪽만 고치면 이렇게 된다 — "
        "양쪽을 함께 고쳐야 하고, 승인 카드 대조가 선행이다."
    )


def test_consistent_label_swap_is_safe() -> None:
    """두 호출에 **같은** fps 를 주면 라벨이 무엇이든 결과가 같다 (소거의 직접 증명).

    저장 라벨을 실측으로 바꾸는 마이그레이션이 와도 이 경로는 안전하다는 뜻이다.
    """
    _mid, src_fps, src_frames, rep_frames = REFS[0]
    step = decimation_step(src_fps, LITERAL_FRAMES_FPS)
    video_n = _extracted_n(src_frames, step)
    rep_real = effective_fps(src_fps, LABEL_REP_FPS)

    for m in range(0, rep_frames, 7):
        with_label = _chain(m, video_n, rep_frames)
        r_idx = _to_rep_idx(m, rep_real, LITERAL_FRAMES_FPS, video_n)
        with_real = ref_display_frame_index(
            r_idx, video_n, rep_frames, rep_real, LITERAL_FRAMES_FPS
        )
        assert abs(with_label - with_real) <= 1, f"m={m}"


def test_inconsistent_pair_breaks_it() -> None:
    """★진짜 취약점 — 한쪽 호출만 실효 rate 로 바꾸면 소거가 깨진다.

    이 테스트가 통과한다는 것은 "부분 수리는 승인본을 깬다"가 사실이라는 뜻이고,
    이 파일이 그 부분 수리를 막는 자리라는 뜻이다.
    """
    _mid, src_fps, src_frames, rep_frames = REFS[0]
    step = decimation_step(src_fps, LITERAL_FRAMES_FPS)
    video_n = _extracted_n(src_frames, step)
    render_eff = effective_fps(src_fps, LITERAL_FRAMES_FPS)
    rep_real = effective_fps(src_fps, LABEL_REP_FPS)

    m = rep_frames // 2
    # _to_rep_idx 만 실효 rate 로 바꾸고 ref_display_frame_index 는 리터럴 유지
    r_idx = _to_rep_idx(m, LABEL_REP_FPS, render_eff, video_n)
    broken = ref_display_frame_index(
        r_idx, video_n, rep_frames, LABEL_REP_FPS, LITERAL_FRAMES_FPS
    )
    truth = _truth(m, video_n, rep_real, render_eff)
    assert abs(broken - truth) > ROUNDING_SLACK, (
        "부분 수리가 결과를 안 바꾼다면 이 파일의 전제가 틀렸다 — 재측정 필요"
    )


def test_scale_is_data_derived_not_hardcoded() -> None:
    """4/3 은 상수가 아니라 유도값이다 — 기준마다 조금씩 다르다(1.32~1.34)."""
    scales = []
    for _mid, src_fps, src_frames, rep_frames in REFS:
        step = decimation_step(src_fps, LITERAL_FRAMES_FPS)
        video_n = _extracted_n(src_frames, step)
        scales.append(video_n / (rep_frames * LITERAL_FRAMES_FPS / LABEL_REP_FPS))
    assert all(1.30 < s < 1.36 for s in scales)
    assert len(set(round(s, 4) for s in scales)) > 1, "전부 같은 값이면 하드코딩 의심"
