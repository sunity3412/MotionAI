"""quick-260808-jix 실 E2E 라운드 — E v2 (클러스터 스터터) 합성 역검증.

orchestrator 처분 ② 요건 (c): v1형 "가다-서다"(연속 dup run ≥2 클러스터)를 합성해
새 E 가 FAIL 을 내는지 기계 증명 — "잡던 걸 계속 잡는다". 동시에 승인 문법
3종(균일 슬로모 run=1 / 경계 정착 버스트 3회 / 스틸 크롤 run≥6)이 PASS 임을 핀.

2겹: ① 순수 판정 코어(stutter_stop_events/worst_stutter_window)에 합성 diff 열,
② 실 mp4 합성(ffmpeg 인코드 → verify() 전체 경로 — 추출·패널 분할·인코딩 노이즈
포함 end-to-end).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from sunity_shared.analysis import compare_verify as cv

FPS = 30.0
MOVE = 1.5   # 실모션 diff (승인 코퍼스 실측 1.3~1.7대)
DUP = 0.02   # 동일 프레임 diff
FLICKER = 0.06  # 스틸 콘텐츠 플리커 (dup 임계 초과·실모션 미달 — pdshapefault 헤드 실측 0.05~0.06)


# ═══════════════════ ① 순수 판정 코어 ═══════════════════


def test_v1_style_cluster_cadence_fails():
    """v1 "가다-서다" 케이던스 (hold 3 + move 2 반복) = 초당 6 이벤트 → 2s 창
    12회 >> 4 = FAIL 조건 성립. 잡던 증상을 계속 잡는다의 기계 증거."""
    diffs = np.array(([DUP] * 3 + [MOVE] * 2) * 24)  # 4초 분량
    events = cv.stutter_stop_events(diffs, fps=FPS)
    assert len(events) >= 20
    assert cv.worst_stutter_window(events) >= cv.STUTTER_FAIL_COUNT


def test_v1_style_hold2_cadence_fails():
    """hold 2 + move 3 변형 케이던스도 FAIL (run 하한 2 경계 검증)."""
    diffs = np.array(([DUP] * 2 + [MOVE] * 3) * 24)
    events = cv.stutter_stop_events(diffs, fps=FPS)
    assert cv.worst_stutter_window(events) >= cv.STUTTER_FAIL_COUNT


def test_uniform_slowmo_run1_passes():
    """승인 문법 ① 균일 슬로모 (slope~0.66 — 신선 doc GPU 실측 전 run=1):
    hold 1 + move 2 반복 → run=1 은 이벤트 아님 → 0."""
    diffs = np.array(([DUP] + [MOVE] * 2) * 40)
    assert cv.stutter_stop_events(diffs, fps=FPS) == []


def test_boundary_settle_burst_of_3_passes():
    """승인 문법 ② 경계 정착 버스트 — 승인 코퍼스 실측 상계(3회 @0.4s,
    powerspin 꼬리/pdshapefault 헤드)는 임계(4) 미만 = PASS 여유 핀."""
    burst = ([MOVE] + [DUP] * 3) * 3 + [MOVE]  # 정지 3회 몰림
    diffs = np.array([MOVE] * 30 + burst + [MOVE] * 30)
    events = cv.stutter_stop_events(diffs, fps=FPS)
    assert len(events) == 3
    assert cv.worst_stutter_window(events) == 3 < cv.STUTTER_FAIL_COUNT


def test_still_crawl_long_runs_pass():
    """승인 문법 ③ 스틸 크롤 (pdshapefault run 7·9) — run ≥6 은 '멈춤' 의미론,
    이벤트 아님."""
    diffs = np.array(([DUP] * 8 + [MOVE]) * 12)
    assert cv.stutter_stop_events(diffs, fps=FPS) == []


def test_still_flicker_without_motion_not_events():
    """스틸 플리커 (이웃이 실모션 미달 0.06) — '가다' 불성립, 이벤트 아님
    (모션-괄호 = dup 임계 ×10 decade-분리)."""
    diffs = np.array(([DUP] * 3 + [FLICKER]) * 20)
    assert cv.stutter_stop_events(diffs, fps=FPS) == []


def test_region_edge_run_excluded():
    """구간 가장자리에 닿은 run — 한쪽 '가다' 확인 불가 = 이벤트 아님."""
    diffs = np.array([DUP] * 3 + [MOVE] * 20 + [DUP] * 3)
    assert cv.stutter_stop_events(diffs, fps=FPS) == []


def test_playback_regions_excludes_freezes():
    report = {"freezes": [
        {"voiceStartOutS": 5.0, "freezeS": 10.0},
        {"voiceStartOutS": 20.0, "freezeS": 5.0},
    ]}
    regions = cv.playback_regions(report, actual=30.0)
    assert regions == [(0.3, 4.7), (15.3, 19.7), (25.3, 29.7)]
    # freeze 0 편 = 전 구간 (margin 만)
    assert cv.playback_regions({"freezes": []}, actual=10.0) == [(0.3, 9.7)]


# ═══════════════════ ② 실 mp4 end-to-end (합성 인코드) ═══════════════════


def _synth_mp4(tmp: Path, name: str, positions: list[int], size=(360, 240)) -> tuple[Path, dict]:
    """세로 바가 positions[i] 픽셀 x 에 있는 프레임열 → x264 mp4 (렌더러 인코드 설정).

    바는 전폭 패널 양쪽에 각각 존재 — 리그의 좌/우 패널 분할 모두 같은 패턴을 본다.
    """
    fdir = tmp / f"{name}_frames"
    fdir.mkdir(parents=True, exist_ok=True)
    W, H = size
    half = W // 2
    for i, x in enumerate(positions):
        arr = np.full((H, W), 40, dtype=np.uint8)
        for off in (0, half):  # 좌/우 패널 대칭
            x0 = off + (x % (half - 24))
            arr[:, x0:x0 + 16] = 230
        Image.fromarray(arr).save(fdir / f"{i + 1:05d}.png")
    out = tmp / f"{name}.mp4"
    subprocess.run(
        [cv.FF, "-y", "-loglevel", "error", "-framerate", "30",
         "-i", str(fdir / "%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-crf", "20", "-movflags", "+faststart", str(out)],
        check=True,
    )
    report = {
        "outDurationS": round(len(positions) / FPS, 2),
        "expectedFreezes": 0,
        "freezes": [],
    }
    return out, report


@pytest.mark.parametrize(
    "name,pattern,expect_ok",
    [
        # v1형 가다-서다: 3프레임 정지 + 2프레임 전진(8px/프레임) 반복 → E FAIL
        ("v1_cluster", "hold3_move2", False),
        # 균일 슬로모: 1프레임 정지 + 2프레임 전진 반복 (run=1) → ALL PASS
        ("uniform_slowmo", "hold1_move2", True),
    ],
)
def test_verify_end_to_end_on_synthetic_mp4(tmp_path, name, pattern, expect_ok):
    positions: list[int] = []
    x = 0
    hold = 3 if pattern == "hold3_move2" else 1
    move = 2
    for _ in range(36):  # 6초 (>=0.5s 구간 + 2s 창 다수)
        positions += [x] * hold
        for _ in range(move):
            x += 8
            positions.append(x)
    mp4, report = _synth_mp4(tmp_path, name, positions)
    ok, lines = cv.verify(mp4, report, tmp_path)
    e_lines = [ln for ln in lines if ln.strip().startswith(("[PASS] E", "[FAIL] E"))]
    assert e_lines, f"E 판정 라인 부재: {lines}"
    if expect_ok:
        assert ok, "\n".join(lines)
        assert all("[PASS]" in ln for ln in e_lines)
    else:
        assert not ok
        assert any("[FAIL]" in ln for ln in e_lines), "\n".join(lines)
        # v1형은 다른 항목이 아니라 정확히 E 로 떨어져야 한다 (A/C/F 는 PASS).
        non_e_fails = [ln for ln in lines if "[FAIL]" in ln and "E 저더" not in ln]
        assert non_e_fails == [], "\n".join(lines)
