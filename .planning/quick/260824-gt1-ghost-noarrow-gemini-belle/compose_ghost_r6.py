"""6라운드 — 잔상 결정론 합성 (quick-260824-gt1, belle 파란선 스펙 08-24).

belle 이 r2-3 위에 파란 선으로 잔상 다리의 정답 위치를 직접 그려줌 →
생성/편집 모델 배제, 실선 다리를 복사·회전해 그 선 위에 정확히 얹는다.
각도가 숫자 다이얼이라 "더 좁혀/벌려"는 상수 수정 1회로 끝난다.

베이스 = out_r5/ghost-r5-3 (잔상이 지워져 나온 본 — 깨끗한 실선 캔버스).
스펙 = belle 파란선 (r2-3 좌표계 → 896x1200 환산):
  윗잔상 축   : 수직(위)에서 오른쪽으로 약 50도
  아랫잔상 축 : 수직(아래)에서 오른쪽으로 약 76도 (수평 조금 아래)
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
BASE = HERE / "out_r5" / "ref-power-spin--leg__ghost-r5-3.jpg"

# ── 다이얼 (belle 파란선 실측치. 조정 요청 = 이 숫자만 바꾼다) ──────────────
RAISED_ROT_DEG = 64.0  # belle4 왼쪽 프레임 실측: 수직에서 66도 - 실선축 1.6도   # 윗다리: 시계방향(오른쪽으로 벌어짐) +
LOWER_ROT_DEG = -49.0  # belle4 실측: 아래수직에서 68도 - 실선축 19도   # 아랫다리: 반시계(발이 수평 쪽으로 올라감) -
GHOST_ALPHA = 0.42
GHOST_BLUR = 1.2

# 실선 다리 폴리곤·피벗 (base_grid.png 실측, 896x1200 좌표계)
RAISED_PIVOT = (480, 595)
RAISED_POLY = [
    (468, 612), (474, 430), (470, 300), (478, 205), (482, 148),
    (508, 146), (514, 240), (518, 400), (512, 520), (502, 622),
]
LOWER_PIVOT = (485, 660)
LOWER_POLY = [
    (470, 622), (512, 642), (545, 720), (585, 785), (628, 900),
    (645, 1012), (633, 1062), (598, 1056), (572, 948), (528, 828),
    (468, 728), (448, 682),
]


def _ghost_layer(base: Image.Image, poly, pivot, rot_deg: float) -> Image.Image:
    w, h = base.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    ImageDraw.Draw(mask).rectangle([448, 0, 481, 560], fill=0)  # 폴 스트립 제외 (다리 접합부 y>560 은 유지)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    # 잔상 = 배경색 쪽으로 눌러 밝힌 "흐린 선 그림" (그림자·얼룩 아님, 20-1 잔상 문법)
    bg = Image.new("RGB", base.size, base.getpixel((40, 40)))
    faded = Image.blend(bg, base, 0.42)
    # 배경과 거의 같은 픽셀은 잔상에서 제외 (사각 얼룩 방지)
    lum = base.convert("L")
    ink = lum.point(lambda v: 255 if v < 236 else 0)
    from PIL import ImageChops
    mask = ImageChops.multiply(mask, ink.filter(ImageFilter.MaxFilter(5)))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.paste(faded.convert("RGBA"), (0, 0), mask)
    layer = layer.rotate(-rot_deg, center=pivot, resample=Image.BICUBIC)
    layer = layer.filter(ImageFilter.GaussianBlur(0.6))
    return layer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "out_r6" / "ref-power-spin--leg__ghost-r6.jpg"))
    ap.add_argument("--debug-axes", action="store_true", help="목표 축 선 오버레이 (검수용)")
    args = ap.parse_args()

    base = Image.open(BASE).convert("RGB")
    canvas = base.convert("RGBA")

    for poly, pivot, rot in (
        (RAISED_POLY, RAISED_PIVOT, RAISED_ROT_DEG),
        (LOWER_POLY, LOWER_PIVOT, LOWER_ROT_DEG),
    ):
        canvas = Image.alpha_composite(canvas, _ghost_layer(base, poly, pivot, rot))

    # 실선·몸통을 원본 그대로 재보증 — 잔상이 몸 위를 물들이지 않게 몸 영역 복원
    # (몸 영역 = 대략 실루엣 좌측 절반 + 실선 다리 폴리곤)
    body_mask = Image.new("L", base.size, 0)
    bd = ImageDraw.Draw(body_mask)
    bd.polygon(RAISED_POLY, fill=255)
    bd.polygon(LOWER_POLY, fill=255)
    bd.polygon([(200, 380), (462, 380), (462, 700), (440, 880), (380, 870),
                (250, 640), (200, 520)], fill=255)
    body_mask = body_mask.filter(ImageFilter.GaussianBlur(2))
    canvas.paste(base, (0, 0), body_mask)

    if args.debug_axes:
        d = ImageDraw.Draw(canvas)
        for pivot, deg_from, length in (
            (RAISED_PIVOT, -90 + RAISED_ROT_DEG, 460),
            (LOWER_PIVOT, 90 - LOWER_ROT_DEG, 430),
        ):
            rad = math.radians(deg_from)
            end = (pivot[0] + length * math.cos(rad) if False else 0, 0)
        # 단순화: 윗축 = 수직에서 +50도, 아랫축 = 수직아래에서 +76도
        for pivot, ang_screen, length, color in (
            (RAISED_PIVOT, math.radians(-90 + RAISED_ROT_DEG), 460, (0, 0, 255)),
            (LOWER_PIVOT, math.radians(90 + LOWER_ROT_DEG), 430, (0, 128, 255)),
        ):
            end = (
                pivot[0] + length * math.cos(ang_screen),
                pivot[1] + length * math.sin(ang_screen),
            )
            d.line([pivot, end], fill=color, width=4)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, quality=92)
    print(f"saved {out} (raised {RAISED_ROT_DEG} / lower {LOWER_ROT_DEG} / alpha {GHOST_ALPHA})")


if __name__ == "__main__":
    main()
