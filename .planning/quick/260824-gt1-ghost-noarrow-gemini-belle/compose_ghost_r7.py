"""7라운드 — r2-3 원본 잔상을 떼어 실측 각도로 회전 합성 (quick-260824-gt1).

r6 교훈: 실선 다리를 픽셀 가공해 잔상을 새로 만들면 화풍이 깨진다(그림자/흰 띠).
r2-3 에는 모델이 그린 화풍 완벽한 잔상이 이미 있다 — r5-3(잔상 소실본)과의
차분으로 잔상 픽셀만 분리해, belle 캡처(4번 왼쪽 프레임) 실측 각도로 회전한다.

각도 스펙 (belle4 왼쪽 프레임 실측):
  윗잔상 축   : 수직(위)에서 오른쪽 66도  (r2-3 잔상 현재 약 22도 → +44 회전)
  아랫잔상 축 : 수직(아래)에서 오른쪽 68도 (r2-3 잔상 현재 약 34도 → -34 회전)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
GHOST_SRC = HERE / "out_r2" / "ref-power-spin--leg__ghost-r2-3.jpg"   # 잔상 원본
CANVAS = HERE / "out_r5" / "ref-power-spin--leg__ghost-r5-3.jpg"      # 깨끗한 실선

# ── 다이얼 ──────────────────────────────────────────────────────────────
RAISED_ROT_DEG = 44.0    # +: 시계방향 (더 벌어짐)
LOWER_ROT_DEG = -34.0    # -: 반시계 (발이 수평 쪽으로)
GHOST_FADE = 0.62        # 1=원본 농도, 낮출수록 흐려짐

RAISED_PIVOT = (492, 588)   # 윗잔상 뿌리(골반 우측)
LOWER_PIVOT = (500, 655)    # 아랫잔상 뿌리

# r2-3 좌표계에서 잔상 영역 폴리곤 (diff_vis 실측 — 실선·드리프트 제외)
RAISED_GHOST_POLY = [
    (508, 590), (520, 470), (545, 380), (590, 300), (640, 240), (672, 235),
    (668, 285), (620, 380), (575, 470), (545, 560), (528, 600),
]
LOWER_GHOST_POLY = [
    (528, 640), (575, 680), (640, 760), (710, 860), (775, 960), (792, 1010),
    (762, 1042), (700, 960), (628, 860), (566, 762), (520, 690),
]


def _ghost_layer(src: Image.Image, diffmask: Image.Image, poly, pivot, rot_deg):
    w, h = src.size
    region = Image.new("L", (w, h), 0)
    ImageDraw.Draw(region).polygon(poly, fill=255)
    mask = ImageChops.multiply(region, diffmask)
    # 윤곽 조각 -> 실루엣 채움: 팽창 후 이진화 (모폴로지 closing)
    mask = mask.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(3))
    mask = mask.point(lambda v: 255 if v > 70 else 0)
    mask = mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.5))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.paste(src.convert("RGBA"), (0, 0), mask)
    layer = layer.rotate(-rot_deg, center=pivot, resample=Image.BICUBIC)
    r, g, b, a = layer.split()
    a = a.point(lambda v: int(v * GHOST_FADE))
    return Image.merge("RGBA", (r, g, b, a))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "out_r7" / "ref-power-spin--leg__ghost-r7.jpg"))
    args = ap.parse_args()

    src = Image.open(GHOST_SRC).convert("RGB")
    canvas_img = Image.open(CANVAS).convert("RGB")
    diff = ImageChops.difference(src, canvas_img).convert("L")
    diffmask = diff.point(lambda v: 255 if v > 6 else 0)

    canvas = canvas_img.convert("RGBA")
    for poly, pivot, rot in (
        (RAISED_GHOST_POLY, RAISED_PIVOT, RAISED_ROT_DEG),
        (LOWER_GHOST_POLY, LOWER_PIVOT, LOWER_ROT_DEG),
    ):
        canvas = Image.alpha_composite(
            canvas, _ghost_layer(src, diffmask, poly, pivot, rot)
        )

    # 몸통·실선 복원 (잔상이 몸 위를 물들이지 않게) — 실선 다리·몸통 코어만
    body = Image.new("L", canvas_img.size, 0)
    bd = ImageDraw.Draw(body)
    bd.polygon([(200, 380), (470, 380), (500, 560), (505, 700), (620, 1000),
                (630, 1060), (585, 1060), (470, 780), (420, 700), (250, 640),
                (200, 520)], fill=255)
    bd.polygon([(468, 560), (470, 300), (478, 150), (508, 148), (516, 300),
                (512, 520), (500, 600)], fill=255)
    body = body.filter(ImageFilter.GaussianBlur(2))
    canvas.paste(canvas_img, (0, 0), body)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, quality=92)
    print(f"saved {out} (raised +{RAISED_ROT_DEG} / lower {LOWER_ROT_DEG} / fade {GHOST_FADE})")


if __name__ == "__main__":
    main()
