"""임의 영상에 대해 원본/180° 두 방향 추론을 돌려 관측 품질을 비교한다.
usage: orient_probe.py <video> <out_prefix> [stride]
"""
import os, sys, json, time
import numpy as np, imageio.v2 as imageio
from PIL import Image
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
from sunity_shared.analysis.inversion_warp import INVERSION_MARGIN

BASE = "/Users/Shared/sunity-lr-audit"
BONES = {"L상완":(5,7),"L전완":(7,9),"R상완":(6,8),"R전완":(8,10),
         "L대퇴":(11,13),"L하퇴":(13,15),"R대퇴":(12,14),"R하퇴":(14,16)}

def run(video, prefix, stride=3):
    from rtmlib import Wholebody
    infer = Wholebody(det=os.environ["YOLOX_ONNX_PATH"], det_input_size=(640,640),
                      pose=os.environ["RTMW_ONNX_PATH"], to_openpose=False,
                      backend="onnxruntime", device="cpu")
    rd = imageio.get_reader(video)
    K0=[];S0=[];K1=[];S1=[];FR=[]
    t0=time.perf_counter()
    for n, fr in enumerate(rd):
        if n % stride: continue
        H0,W0 = fr.shape[:2]; sc = 640/max(H0,W0)
        img = np.asarray(Image.fromarray(fr).resize((round(W0*sc),round(H0*sc)), Image.BILINEAR))
        H,W = img.shape[:2]
        for orient, arrK, arrS in (("orig",K0,S0), ("rot180",K1,S1)):
            inp = img if orient=="orig" else np.ascontiguousarray(np.rot90(img,2))
            k,s = infer(inp)
            if k is None or not len(k):
                arrK.append(np.full((133,2),np.nan)); arrS.append(np.zeros(133)); continue
            kk = k[0][:,:2].astype(float).copy()
            if orient=="rot180":
                kk[:,0]=(W-1)-kk[:,0]; kk[:,1]=(H-1)-kk[:,1]
            arrK.append(kk); arrS.append(s[0].astype(float))
        FR.append(n)
        if len(FR)%25==0: print(f"  {len(FR)} frames  {time.perf_counter()-t0:.0f}s", flush=True)
    rd.close()
    K0,S0,K1,S1,FR = map(np.array,(K0,S0,K1,S1,FR))
    np.savez(f"{BASE}/out/{prefix}_both.npz", k0=K0,s0=S0,k1=K1,s1=S1,frames=FR)
    return K0,S0,K1,S1,FR

def torso(K):
    sh=K[:,[5,6],:].mean(1); hp=K[:,[11,12],:].mean(1)
    return np.linalg.norm(sh-hp,axis=-1)

def report(K0,S0,K1,S1,FR,label):
    c0=S0[:,:17].mean(1); c1=S1[:,:17].mean(1)
    uniq=np.array([len(set(map(tuple,np.round(K0[t,:17,:],1)))) for t in range(len(K0))])
    uniq1=np.array([len(set(map(tuple,np.round(K1[t,:17,:],1)))) for t in range(len(K1))])
    m1=(K1[:,[5,6],:].mean(1)[:,1]-K1[:,[11,12],:].mean(1)[:,1])/(torso(K1)+1e-9)
    ok=(S1[:,[5,6,11,12]]>0.3).all(-1)
    inv=ok&(m1>INVERSION_MARGIN); upr=ok&(m1<-INVERSION_MARGIN)
    print(f"\n===== {label} — {len(FR)}프레임 =====")
    print(f"  평균 conf      orig {c0.mean():.3f}   rot180 {c1.mean():.3f}   rot 우세 {(c1>c0).mean()*100:.1f}%")
    print(f"  붕괴 프레임     orig {int((uniq<=8).sum())}        rot180 {int((uniq1<=8).sum())}")
    print(f"  역립 {int(inv.sum())}프레임  정립 {int(upr.sum())}프레임")
    if inv.sum(): print(f"    역립: orig {c0[inv].mean():.3f} -> rot {c1[inv].mean():.3f}  우세 {(c1[inv]>c0[inv]).mean()*100:.1f}%")
    if upr.sum(): print(f"    정립: orig {c0[upr].mean():.3f} -> rot {c1[upr].mean():.3f}  우세 {(c1[upr]>c0[upr]).mean()*100:.1f}%")
    print(f"  뼈 길이 위반 p90 (중앙값 대비 |log|):")
    for nm,(i,j) in BONES.items():
        v=[]
        for K in (K0,K1):
            L=np.linalg.norm(K[:,i,:]-K[:,j,:],axis=-1)/(torso(K)+1e-9)
            v.append(np.nanpercentile(np.abs(np.log((L+1e-9)/(np.nanmedian(L)+1e-9))),90))
        print(f"    {nm:<8} orig {v[0]:.3f}  ->  rot180 {v[1]:.3f}")

if __name__=="__main__":
    v,p = sys.argv[1], sys.argv[2]
    st = int(sys.argv[3]) if len(sys.argv)>3 else 3
    K0,S0,K1,S1,FR = run(v,p,st)
    report(K0,S0,K1,S1,FR,p)
