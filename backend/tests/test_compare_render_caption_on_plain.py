"""'관절선 끄기' 판에도 자막은 남는다 (belle 09-09).

관절선 끄기 영상판(`compare_v1__plain.mp4`)은 정지 프레임에서 표시를 그리기
**전** 상태를 떠서 만든다. 그 지점을 그대로 두면 표시와 함께 자막까지 사라진다 —
실제로 첫 렌더가 그랬다(t=5.5s 프레임 대조에서 밴드가 통째로 없었다).

토글이 끄겠다고 이름 붙인 것은 관절선뿐이므로, 자막은 두 판 모두에 굽는다.
여기서 지키는 불변식: **자막은 넘긴 캔버스 전부에 똑같이 찍힌다.**
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageFont

from sunity_shared.analysis.compare_render import (
    APP_BLOCK_ASPECT,
    PANEL_H,
    _caption_bottom,
    _draw_caption,
)

W = 400
S = 1.0


def _canvas() -> Image.Image:
    return Image.new("RGB", (W, PANEL_H), (20, 18, 17))


def _band_rows(img: Image.Image, band_h: int) -> list[tuple[int, int, int]]:
    return [img.getpixel((W // 2, y)) for y in range(PANEL_H - band_h, PANEL_H)]


def test_caption_is_baked_into_every_canvas() -> None:
    """표시 판과 관절선 끄기 판이 자막에서 byte 단위로 같아야 한다."""
    marked, plain = _canvas(), _canvas()
    band_h = _draw_caption([marked, plain], "어깨를 눌러 잡으세요", ImageFont.load_default(),
                           W, 16, 24, S)
    assert band_h > 0
    assert marked.tobytes() == plain.tobytes()


def test_caption_actually_changes_the_band() -> None:
    """밴드가 실제로 칠해졌는지 — 호출만 되고 안 그려지는 것을 배제한다."""
    img = _canvas()
    before = _band_rows(img, 40)
    band_h = _draw_caption([img], "어깨를 눌러 잡으세요", ImageFont.load_default(),
                           W, 16, 24, S)
    assert _band_rows(img, band_h) != before[: band_h]


def test_single_canvas_still_works() -> None:
    """재생 프레임처럼 판이 하나뿐인 경로도 그대로 동작한다."""
    img = _canvas()
    assert _draw_caption([img], "짧게", ImageFont.load_default(), W, 16, 24, S) > 0


# ── 자막 안전영역 (belle 09-09 시뮬 실측) ──────────────────────────────────
# 앱은 이 mp4 를 시안 블록 비율에 폭 맞춰 넣고 위아래를 자른다. 프레임 맨 아래에
# 굽던 자막은 그 잘림 구간에 통째로 들어가 화면에서 사라졌다 (0:43.5 — 표시는
# 보이는데 문장이 없다). 밴드를 보이는 창 안쪽 밑선에 붙인다.


def test_caption_sits_inside_the_window_the_app_shows() -> None:
    W = 1224  # 실측 (compare_v1.mp4)
    bottom = _caption_bottom(W)
    visible_h = W / APP_BLOCK_ASPECT
    assert bottom < PANEL_H, "잘리는 프레임인데 밴드가 맨 아래에 그대로 있다"
    assert bottom == pytest.approx(PANEL_H - (PANEL_H - visible_h) / 2, abs=1.0)


def test_caption_stays_at_the_frame_bottom_when_nothing_is_cropped() -> None:
    """블록이 영상보다 세로로 길면 크롭이 없다 — 종전 문법 그대로."""
    assert _caption_bottom(round(PANEL_H * APP_BLOCK_ASPECT) + 200) == PANEL_H


def test_caption_band_is_drawn_at_that_bottom() -> None:
    """계산만 맞고 그리는 자리는 안 바뀌는 회귀를 막는다."""
    img = _canvas()
    band_h = _draw_caption([img], "어깨를 눌러 잡으세요", ImageFont.load_default(),
                           W, 16, 24, S)
    bottom = _caption_bottom(W)
    ground = (20, 18, 17)
    assert img.getpixel((W // 2, bottom - 2)) != ground   # 밴드 안
    assert img.getpixel((W // 2, bottom - band_h - 4)) == ground   # 밴드 위
    if bottom < PANEL_H - 4:
        assert img.getpixel((W // 2, bottom + 4)) == ground   # 밴드 아래(잘림 구간)
