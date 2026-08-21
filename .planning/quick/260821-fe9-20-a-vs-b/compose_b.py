"""B 길 — 앱 오버레이 합성: exq stage20-1 위 코랄 화살표 2개 + 소형 표기 1곳 (quick-260821-fe9).

belle 2026-08-21 판정 반영 (D-03, D-04):
  화살표 시작점 = 반드시 잔상의 발 (폴 가운데 출발 금지), 끝점 = 같은 쪽 실선 발.
  표기 = 방향 문장만 소형 1곳 ("20° 정도 더 벌리세요" — "좁다" 금지).
  소스(260821-exq out/)는 읽기 전용 — 출력은 fe9 out/ 에만 (D-01, exq dir 무변경).

Pillow 12.2.0 로컬 설치 확인됨, 한글 폰트 AppleSDGothicNeo.ttc 로드 확인됨 — 신규 설치 0.
2배 슈퍼샘플 후 축소로 곡선 계단 현상 억제.

실행: python3 compose_b.py  (cwd 무관, 경로는 스크립트 기준 절대경로)
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC = REPO / ".planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out/ref-kip-up--leg__ghost-stage20-1.jpg"
OUT_DIR = HERE / "out"
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

CORAL = (255, 75, 51, 255)  # #FF4B33 (브랜드 컬러, design.md)

# 발 좌표 4점 — 소스 이미지(896x1200) 절대 픽셀.
# 눈으로 잡음(3배 확대 + 격자 대조), 배선 시 앵커 메타로 대체.
COORDS = {
    "ghostL": (213, 1043),  # 잔상 왼발 (안쪽, 연함)
    "solidL": (110, 1015),  # 실선 왼발 (바깥, 진함)
    "ghostR": (645, 1035),  # 잔상 오른발
    "solidR": (742, 990),   # 실선 오른발
}

LABEL = "20° 정도 더 벌리세요"  # 방향 문장만 — "좁다" 금지 (D-04)

SS = 2  # 슈퍼샘플 배율


def _bezier(p0, p1, p2, n=48):
    """quadratic bezier 를 선분 폴리라인 점 목록으로."""
    pts = []
    for k in range(n + 1):
        t = k / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def _arrow(draw: ImageDraw.ImageDraw, start, ctrl, end, width, head):
    """잔상 발(start) -> 실선 발(end) 곡선 화살표. 머리는 끝점 접선 방향 삼각형."""
    pts = _bezier(start, ctrl, end)
    # 화살촉이 앉을 자리만큼 몸통을 살짝 줄인다
    body = pts[: -max(2, int(len(pts) * head / max(1.0, _dist(start, end)) * 0.5))]
    draw.line(body, fill=CORAL, width=width, joint="curve")
    # 접선 = 제어점 -> 끝점
    ang = math.atan2(end[1] - ctrl[1], end[0] - ctrl[0])
    tip = end
    left = (end[0] - head * math.cos(ang - 0.45), end[1] - head * math.sin(ang - 0.45))
    right = (end[0] - head * math.cos(ang + 0.45), end[1] - head * math.sin(ang + 0.45))
    draw.polygon([tip, left, right], fill=CORAL)


def _dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _label(draw: ImageDraw.ImageDraw, xy, font):
    """소형 표기 1곳 — 흰 반투명 패드 위 코랄 텍스트."""
    bbox = draw.textbbox(xy, LABEL, font=font)
    pad = 10 * SS
    draw.rounded_rectangle(
        (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad),
        radius=8 * SS, fill=(255, 255, 255, 200),
    )
    draw.text(xy, LABEL, font=font, fill=CORAL)


def compose(variant: int) -> Path:
    base = Image.open(SRC).convert("RGBA")
    w, h = base.size  # (896, 1200)
    big = base.resize((w * SS, h * SS), Image.LANCZOS)
    layer = Image.new("RGBA", big.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    width = max(2, round(w * 0.006)) * SS       # 선 굵기 ~0.6% of width
    head = round(w * 0.025) * SS                # 화살촉 ~2.5% of width
    s = lambda p: (p[0] * SS, p[1] * SS)

    gL, sL = COORDS["ghostL"], COORDS["solidL"]
    gR, sR = COORDS["ghostR"], COORDS["solidR"]
    # 제어점 = 현 중점에서 바깥(아래) 방향 — 다리가 고관절 축으로 벌어지는 호 모양
    ctrlL = ((gL[0] + sL[0]) / 2 - 8, (gL[1] + sL[1]) / 2 + 46)
    ctrlR = ((gR[0] + sR[0]) / 2 + 8, (gR[1] + sR[1]) / 2 + 46)
    _arrow(draw, s(gL), s(ctrlL), s(sL), width, head)
    _arrow(draw, s(gR), s(ctrlR), s(sR), width, head)

    font = ImageFont.truetype(FONT_PATH, round(w * 0.03) * SS)  # 소형 ~3% of width
    if variant == 1:
        # 1안: 하단 중앙
        tw = draw.textlength(LABEL, font=font)
        _label(draw, ((w * SS - tw) / 2, (h - 62) * SS), font)
    else:
        # 2안: 오른쪽 화살표 근처 (곡선 바깥, 발 아래).
        # 실물 확인에서 우측 패드가 이미지 가장자리에 잘려 x 를 클램프 (패드+여백만큼 안쪽으로)
        tw = draw.textlength(LABEL, font=font)
        x = min((gR[0] + 24) * SS, w * SS - tw - 24 * SS)
        _label(draw, (x, (gR[1] + 52) * SS), font)

    merged = Image.alpha_composite(big, layer).resize((w, h), Image.LANCZOS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"ref-kip-up--leg__B-overlay20-{variant}.png"
    merged.convert("RGB").save(out, "PNG")
    print(f"saved {out.name} ({out.stat().st_size} bytes)")
    return out


if __name__ == "__main__":
    for v in (1, 2):
        compose(v)
