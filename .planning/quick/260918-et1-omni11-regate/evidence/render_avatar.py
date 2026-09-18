"""관절 좌표 -> 살을 입힌 3D 아바타 렌더 (PIL 만, 신규 의존 0).

점선 스켈레톤은 '계측기'다. 아바타는 그 위에 부피를 입힌 것 —
사지를 원뿔대(tapered capsule)로, 몸통을 덩어리로 그리고 깊이순으로 겹쳐 칠한다.
가까운 쪽이 밝고 먼 쪽이 어둡다(depth shading) — 그래야 돌렸을 때 입체로 읽힌다.
"""
from __future__ import annotations
import numpy as np
from PIL import Image, ImageDraw, ImageFont

F_BOLD = "/Users/kimtaesung/Dev/SunityMotion/app/assets/fonts/Pretendard-SemiBold.ttf"
F_REG  = "/Users/kimtaesung/Dev/SunityMotion/app/assets/fonts/Pretendard-Regular.ttf"
def font(sz, bold=True):
    try: return ImageFont.truetype(F_BOLD if bold else F_REG, sz)
    except Exception: return ImageFont.load_default()

# COCO-17
NOSE,LEY,REY,LEA,REA,LSH,RSH,LEL,REL,LWR,RWR,LHP,RHP,LKN,RKN,LAN,RAN = range(17)

# (a, b, 굵기a, 굵기b) — 몸 비율에 맞춘 상대 반지름
LIMBS = [
    (LSH,LEL,.052,.042), (LEL,LWR,.042,.030),
    (RSH,REL,.052,.042), (REL,RWR,.042,.030),
    (LHP,LKN,.070,.050), (LKN,LAN,.050,.033),
    (RHP,RKN,.070,.050), (RKN,RAN,.050,.033),
]
SKIN_NEAR = np.array([255,138,110], float)   # 가까운 쪽 (브랜드 계열 웜톤)
SKIN_FAR  = np.array([132, 58, 46], float)   # 먼 쪽

def rotate_y(P, deg):
    t=np.radians(deg); c,s=np.cos(t),np.sin(t)
    return P @ np.array([[c,0,s],[0,1,0],[-s,0,c]]).T

def _shade(zn):
    """zn 0(멀다)~1(가깝다) -> 색."""
    zn = float(np.clip(zn,0,1))
    return tuple(int(v) for v in (SKIN_FAR + (SKIN_NEAR-SKIN_FAR)*zn))

def _capsule(d, p, q, ra, rb, col, outline):
    v = q-p; L = np.hypot(*v)
    if L < 1e-6: return
    n = np.array([-v[1], v[0]])/L
    poly = [tuple(p+n*ra), tuple(q+n*rb), tuple(q-n*rb), tuple(p-n*ra)]
    d.polygon(poly, fill=col, outline=outline)
    d.ellipse([p[0]-ra,p[1]-ra,p[0]+ra,p[1]+ra], fill=col, outline=outline)
    d.ellipse([q[0]-rb,q[1]-rb,q[0]+rb,q[1]+rb], fill=col, outline=outline)

def draw_avatar(P3, size=340, pad=40, title="", sub="", warn=False, bg=(250,250,252)):
    img = Image.new("RGB",(size,size+46),bg); d = ImageDraw.Draw(img)
    ok = np.isfinite(P3).all(-1)
    if ok.sum() < 8:
        return img
    Q = P3[:,:2].astype(float).copy()
    v = Q[ok]; lo,hi = v.min(0), v.max(0)
    span = max((hi-lo).max(), 1e-6); scale = (size-2*pad)/span
    Q = (Q-(lo+hi)/2)*scale + size/2
    z = P3[:,2].astype(float)
    zr = z[ok]; zlo,zhi = zr.min(), zr.max()
    zn = (z-zlo)/(zhi-zlo) if zhi-zlo > 1e-9 else np.full_like(z,0.5)
    R = span*scale   # 반지름 환산 기준

    parts = []
    for a,b,fa,fb in LIMBS:
        if ok[a] and ok[b]:
            parts.append((float((z[a]+z[b])/2), "limb", (a,b,fa,fb)))
    if ok[LSH] and ok[RSH] and ok[LHP] and ok[RHP]:
        parts.append((float(z[[LSH,RSH,LHP,RHP]].mean()), "torso", None))
    if ok[NOSE] or (ok[LSH] and ok[RSH]):
        parts.append((float(z[NOSE] if ok[NOSE] else z[[LSH,RSH]].mean()), "head", None))

    for _, kind, meta in sorted(parts, key=lambda t: t[0]):   # 먼 것부터 칠한다
        if kind == "limb":
            a,b,fa,fb = meta
            col = _shade((zn[a]+zn[b])/2)
            _capsule(d, Q[a], Q[b], R*fa, R*fb, col, tuple(int(c*0.72) for c in col))
        elif kind == "torso":
            col = _shade(zn[[LSH,RSH,LHP,RHP]].mean())
            sh_c=(Q[LSH]+Q[RSH])/2; hp_c=(Q[LHP]+Q[RHP])/2
            _capsule(d, sh_c, hp_c, R*0.105, R*0.088, col, tuple(int(c*0.72) for c in col))
            d.polygon([tuple(Q[LSH]),tuple(Q[RSH]),tuple(Q[RHP]),tuple(Q[LHP])],
                      fill=col, outline=tuple(int(c*0.72) for c in col))
            for j,r in ((LSH,.055),(RSH,.055),(LHP,.062),(RHP,.062)):
                x,y=Q[j]; rr=R*r
                d.ellipse([x-rr,y-rr,x+rr,y+rr], fill=col, outline=tuple(int(c*0.72) for c in col))
        else:
            c0 = Q[NOSE] if ok[NOSE] else (Q[LSH]+Q[RSH])/2
            nk = (Q[LSH]+Q[RSH])/2 if ok[LSH] and ok[RSH] else c0
            col = _shade(zn[NOSE] if ok[NOSE] else 0.5)
            _capsule(d, nk, c0, R*0.045, R*0.030, col, tuple(int(c*0.72) for c in col))
            rr = R*0.085
            d.ellipse([c0[0]-rr,c0[1]-rr,c0[0]+rr,c0[1]+rr],
                      fill=col, outline=tuple(int(c*0.72) for c in col))

    d.rectangle([0,size,size,size+46], fill=(255,255,255))
    d.text((12,size+7), title, fill=(20,20,24), font=font(14))
    d.text((12,size+26), sub, fill=(200,45,25) if warn else (110,110,120), font=font(12,False))
    d.rectangle([0,0,size-1,size+45], outline=(226,226,232))
    return img

def strip(P3, angles, labels, warn=False):
    ims=[draw_avatar(rotate_y(P3,a), title=t, sub=s, warn=warn) for a,(t,s) in zip(angles,labels)]
    W=sum(i.width for i in ims); out=Image.new("RGB",(W,ims[0].height),(255,255,255)); x=0
    for i in ims: out.paste(i,(x,0)); x+=i.width
    return out
