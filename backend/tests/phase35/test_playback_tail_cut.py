"""재생 상한(기준 정지 꼬리 제외) 순수 함수 — Phase 34 Pod 스윕 라운드.

판정 입력은 **실제로 렌더될 ref 프레임 인덱스**다(곡선 slope 아님) — 1차 시도가
slope 로 판정했다가 미발동한 실측(_simplify_curve 단순화가 slope 0.000 을 0.102
크롤로 바꿈) 후 교정. 상수 근거는 compare_render 모듈 상단 PLAYBACK_* 주석.
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND / "shared" / "python"))

from sunity_shared.analysis import compare_render as cr  # noqa: E402


def _warp(slope: float, flat_from: float | None = None):
    """user초 -> ref초. flat_from 이후는 기준 시간 고정(완전 정지)."""
    def warp(t: float) -> float:
        u = t if flat_from is None or t < flat_from else flat_from
        return u * slope
    return warp


def test_normal_speed_keeps_full_duration():
    assert cr.playback_end_s(_warp(1.0), 5.0) == 5.0


def test_flat_tail_is_cut_to_its_start():
    end = cr.playback_end_s(_warp(1.0, flat_from=4.0), 5.0)
    assert 3.9 <= end <= 4.05, end


def test_short_stall_below_run_min_is_untouched():
    """5프레임(167ms) 정지 = STUTTER_RUN_MAX 이하 → 지각 대역 밖, 무접촉."""
    end = cr.playback_end_s(_warp(1.0, flat_from=5.0 - 5 / cr.FPS_OUT), 5.0)
    assert end == 5.0


def test_slow_crawl_tail_is_cut():
    """크롤(slope 0.1 = 30fps 에서 10프레임 중복)도 '멈춤'으로 잡힌다.

    이것이 1차 slope 판정과 갈리는 지점 — pdshapefault/belle 반려본 계열의
    실제 형상(단순화 곡선 slope 0.102)이 여기 해당한다.
    """
    end = cr.playback_end_s(_warp(0.1), 5.0)
    assert end < 5.0


def test_cut_shorter_than_min_run_s_is_untouched():
    """총 절단이 PLAYBACK_TAIL_MIN_RUN_S 미만이면 잔돈 절단하지 않는다."""
    flat = 5.0 - (cr.PLAYBACK_TAIL_MIN_RUN_S - 0.02)
    end = cr.playback_end_s(_warp(1.0, flat_from=flat), 5.0)
    assert end == 5.0


def test_degenerate_short_input_returns_input():
    assert cr.playback_end_s(_warp(1.0), 0.05) == 0.05


def test_approved_fixture_shapes_are_untouched():
    """승인 코퍼스 꼬리 형상(중복 run 2~3)은 무접촉 — 회귀 핀.

    실측(2026-08-08): elbow 2 · kipup 2 · peterpan 2 · powerspin 3.
    """
    for run in (2, 3):
        end = cr.playback_end_s(_warp(1.0, flat_from=5.0 - run / cr.FPS_OUT), 5.0)
        assert end == 5.0, run
