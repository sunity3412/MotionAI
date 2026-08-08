"""재생 상한(기준 정지 꼬리 제외) 순수 함수 — Phase 34 Pod 스윕 라운드.

주의: 이 게이트는 **함수의 성질**만 고정한다. 실제 렌더 발동 여부는 별개다 —
현행 임계로는 pdshapefault 계열이 미발동(모듈 상단 PLAYBACK_TAIL_* 주석의 실측:
_simplify_curve 9키포인트 단순화가 꼬리 slope 0.000 을 0.102 크롤로 바꾼다).
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND / "shared" / "python"))

from sunity_shared.analysis import compare_render as cr  # noqa: E402


def _linear(slope: float, upto: float, flat_from: float | None = None):
    """user초 -> ref초. flat_from 이후는 정지(기준 시간 고정)."""
    def warp(t: float) -> float:
        if flat_from is not None and t >= flat_from:
            return flat_from * slope
        return t * slope
    return warp


def test_no_flat_tail_keeps_full_duration():
    assert cr.playback_end_s(_linear(1.0, 5.0), 5.0) == 5.0


def test_flat_tail_longer_than_min_run_is_cut():
    # 마지막 1.0s 가 완전 정지 → 상한이 그 시작으로 당겨진다.
    end = cr.playback_end_s(_linear(1.0, 5.0, flat_from=4.0), 5.0)
    assert 3.9 <= end <= 4.05, end


def test_flat_tail_shorter_than_min_run_is_untouched():
    # 0.1s(<PLAYBACK_TAIL_MIN_RUN_S) 정지는 지각 대역 밖 — 무접촉.
    end = cr.playback_end_s(_linear(1.0, 5.0, flat_from=4.9), 5.0)
    assert end == 5.0


def test_slow_crawl_above_threshold_is_not_cut():
    """크롤(slope 0.1)은 '정지'가 아니라 통과 — 현행 임계의 성질을 명시 고정.

    이 성질 때문에 pdshapefault 계열이 미발동한다(실측). 임계를 바꿀 때 이
    테스트가 함께 바뀌어야 하며, 그때 승인 5편 렌더 영향 재측정이 조건이다.
    """
    end = cr.playback_end_s(_linear(0.1, 5.0), 5.0)
    assert end == 5.0


def test_degenerate_short_input_returns_input():
    assert cr.playback_end_s(_linear(1.0, 0.05), 0.05) == 0.05
