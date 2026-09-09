"""'관절선 끄기' 판에도 자막은 남는다 (belle 09-09).

관절선 끄기 영상판(`compare_v1__plain.mp4`)은 정지 프레임에서 표시를 그리기
**전** 상태를 떠서 만든다. 그 지점을 그대로 두면 표시와 함께 자막까지 사라진다 —
실제로 첫 렌더가 그랬다(t=5.5s 프레임 대조에서 밴드가 통째로 없었다).

토글이 끄겠다고 이름 붙인 것은 관절선뿐이므로, 자막은 두 판 모두에 굽는다.
여기서 지키는 불변식: **자막은 넘긴 캔버스 전부에 똑같이 찍힌다.**
"""

from __future__ import annotations

from PIL import Image, ImageFont

from sunity_shared.analysis.compare_render import PANEL_H, _draw_caption

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
