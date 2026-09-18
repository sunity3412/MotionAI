"""관절 좌표를 회전시켜 그리는 최소 렌더러 — PIL 만 쓴다 (신규 의존 0).

목적: '아바타를 돌려본다'가 실제로 어떻게 보이는지 belle 에게 실물로 보여주기.
좌측 = 오늘 저장된 joints3d (z=0), 우측 = 깊이가 있는 경우.
"""
from __future__ import annotations
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_FONT_PATH = "/Users/kimtaesung/Dev/SunityMotion/app/assets/fonts/Pretendard-SemiBold.ttf"
_FONT_REG = "/Users/kimtaesung/Dev/SunityMotion/app/assets/fonts/Pretendard-Regular.ttf"
def _font(sz, bold=True):
    try:
        return ImageFont.truetype(_FONT_PATH if bold else _FONT_REG, sz)
    except Exception:
        return ImageFont.load_default()

COCO = ['nose','left_eye','right_eye','left_ear','right_ear','left_shoulder','right_shoulder',
        'left_elbow','right_elbow','left_wrist','right_wrist','left_hip','right_hip',
        'left_knee','right_knee','left_ankle','right_ankle']
BONES = [(5,7),(7,9),(6,8),(8,10),(5,6),(5,11),(6,12),(11,12),(11,13),(13,15),(12,14),(14,16),(0,5),(0,6)]
BRAND = (255,75,51)
GREY  = (120,120,130)

def rotate_y(P, deg):
    """세로축(y) 기준 회전 — 카메라가 인물 주위를 도는 것과 같다."""
    t = np.radians(deg); c, s = np.cos(t), np.sin(t)
    R = np.array([[c,0,s],[0,1,0],[-s,0,c]])
    return P @ R.T

def draw(P, size=340, pad=34, title="", sub="", flat_warn=False):
    img = Image.new("RGB", (size, size+46), (255,255,255))
    d = ImageDraw.Draw(img)
    ok = np.isfinite(P).all(axis=-1)
    if ok.sum() >= 3:
        Q = P[:, :2].copy()
        v = Q[ok]
        lo, hi = v.min(0), v.max(0)
        span = max((hi-lo).max(), 1e-6)
        Q = (Q - (lo+hi)/2) / span * (size-2*pad) + size/2
        Q[:,1] = Q[:,1]  # y 는 이미 아래쪽 증가
        for a,b in BONES:
            if ok[a] and ok[b]:
                d.line([tuple(Q[a]), tuple(Q[b])], fill=BRAND if a in (5,6,11,12) else GREY, width=5)
        for i in range(len(P)):
            if ok[i] and i >= 5:
                x,y = Q[i]; r = 5
                d.ellipse([x-r,y-r,x+r,y+r], fill=(40,40,48))
    d.rectangle([0,size,size,size+46], fill=(248,248,250))
    d.text((12, size+7), title, fill=(20,20,24), font=_font(14))
    d.text((12, size+26), sub, fill=(200,45,25) if flat_warn else (110,110,120), font=_font(12, False))
    d.rectangle([0,0,size-1,size+45], outline=(226,226,232))
    return img

def strip(P, angles, labels, flat_warn=False):
    ims = [draw(rotate_y(P, a), title=l, sub=s, flat_warn=flat_warn)
           for a,(l,s) in zip(angles, labels)]
    W = sum(i.width for i in ims); H = ims[0].height
    out = Image.new("RGB",(W,H),(255,255,255)); x=0
    for i in ims: out.paste(i,(x,0)); x += i.width
    return out
