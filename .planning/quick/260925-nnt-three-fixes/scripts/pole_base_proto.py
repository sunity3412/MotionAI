"""프로토타입 — 폴 바닥 y: Hough 수직 선분 중 폴 x 근처 선분의 아래 끝점(프레임별 최대 y)의 중앙값. 프레임 = ffmpeg 9fps 640px."""
import sys, math, subprocess, tempfile, pathlib, numpy as np, cv2
def frames(path, fps=3, w=640, n=40):
    d = tempfile.mkdtemp(); subprocess.run(["ffmpeg","-loglevel","error","-y","-i",path,"-vf",f"fps={fps},scale={w}:-1","-frames:v",str(n),f"{d}/f%03d.png"])
    return [cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB) for p in sorted(pathlib.Path(d).glob("f*.png"))]
def pole_extent(fr):
    H, W = fr[0].shape[:2]; xs=[]; segs=[]
    for f in fr:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY); e = cv2.Canny(g, 50, 150, apertureSize=3)
        L = cv2.HoughLinesP(e, 1, np.pi/180, 80, minLineLength=int(H*0.15), maxLineGap=10)
        if L is None: segs.append([]); continue
        fs=[]
        for x1,y1,x2,y2 in np.asarray(L).reshape(-1,4):
            if abs(math.degrees(math.atan2(abs(y2-y1),abs(x2-x1)))-90) > 5: continue
            fs.append((x1,y1,x2,y2)); xs.append((x1+x2)/2/W)
        segs.append(fs)
    if not xs: return None
    px = float(np.median(xs)); bottoms=[]; tops=[]
    for fs in segs:
        near=[s for s in fs if abs((s[0]+s[2])/2/W - px) < 0.02]
        if near: bottoms.append(max(max(s[1],s[3]) for s in near)/H); tops.append(min(min(s[1],s[3]) for s in near)/H)
    return px, float(np.median(bottoms)), float(np.percentile(bottoms,90)), float(np.median(tops)), len(bottoms)
for p in sys.argv[1:]:
    fr = frames(p); r = pole_extent(fr)
    print(pathlib.Path(p).name, "frames", len(fr), "→ pole x=%.3f base_y med=%.3f p90=%.3f top_y med=%.3f (n=%d)" % r if r else "None")
