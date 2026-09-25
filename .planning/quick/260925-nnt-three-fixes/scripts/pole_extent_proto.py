"""프로토타입 2 — 폴 x 를 Hough 로 잡은 뒤, 그 열 띠의 수직 에지 에너지(|Sobel x|)로 폴이 이어지는 행 구간을 찾는다. 아래 끝 = 바닥, 위 끝 = 천장 마운트."""
import sys, math, subprocess, tempfile, pathlib, numpy as np, cv2
def frames(path, fps=3, w=640, n=40):
    d = tempfile.mkdtemp(); subprocess.run(["ffmpeg","-loglevel","error","-y","-i",path,"-vf",f"fps={fps},scale={w}:-1","-frames:v",str(n),f"{d}/f%03d.png"])
    return [cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB) for p in sorted(pathlib.Path(d).glob("f*.png"))]
def pole_x(fr):
    H, W = fr[0].shape[:2]; xs=[]
    for f in fr:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY); e = cv2.Canny(g, 50, 150, apertureSize=3)
        L = cv2.HoughLinesP(e, 1, np.pi/180, 80, minLineLength=int(H*0.15), maxLineGap=10)
        if L is None: continue
        for x1,y1,x2,y2 in np.asarray(L).reshape(-1,4):
            if abs(math.degrees(math.atan2(abs(y2-y1),abs(x2-x1)))-90) <= 5: xs.append((x1+x2)/2/W)
    return float(np.median(xs)) if xs else None
def extent(fr, px, half=6):
    H, W = fr[0].shape[:2]; x0=int(px*W); bottoms=[]; tops=[]
    for f in fr:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32)
        sx = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3))
        band = sx[:, max(0,x0-half):x0+half+1].mean(axis=1)          # 행별 수직 에지 에너지
        thr = 0.35 * np.percentile(band, 95)
        on = band > thr
        # 가장 긴 연속 구간(작은 끊김 허용: 3행)
        best=(0,0,0); i=0; n=len(on)
        while i<n:
            if not on[i]: i+=1; continue
            j=i; gap=0
            while j<n and (on[j] or gap<3):
                gap = 0 if on[j] else gap+1; j+=1
            j -= gap
            if j-i > best[0]: best=(j-i,i,j)
            i=j+1
        if best[0] > 0.3*H: tops.append(best[1]/H); bottoms.append(best[2]/H)
    if not bottoms: return None
    return float(np.median(tops)), float(np.median(bottoms)), float(np.std(bottoms)), len(bottoms)
for p in sys.argv[1:]:
    fr = frames(p); px = pole_x(fr)
    r = extent(fr, px) if px is not None else None
    print(pathlib.Path(p).name, "pole x=%.3f" % px if px else "no pole", "→ top=%.3f base=%.3f (std %.3f, n=%d)" % r if r else "None")
