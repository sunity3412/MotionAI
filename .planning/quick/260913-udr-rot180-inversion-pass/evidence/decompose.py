"""개선이 검출기에서 오는가 포즈모델에서 오는가 — 4변형 동일 프레임 분해.

A prod_orig   : Wholebody(원본)            = 프로덕션 그대로
B prod_rot    : Wholebody(180° 돌린 프레임) = 검출+포즈 둘 다 회전 혜택
C box_orig    : A의 박스 고정 + rot=0 crop  (A 재현 검증용)
D box_rot     : A의 박스 고정 + rot=180 crop (포즈모델 단독 효과)
"""
import os, sys, time
import numpy as np, imageio.v2 as imageio, cv2
from PIL import Image

BASE="/Users/Shared/sunity-lr-audit"
BONES=((5,7),(7,9),(6,8),(8,10),(11,13),(13,15),(12,14),(14,16))

def main(video, prefix, stride=3):
    from rtmlib import Wholebody
    from rtmlib.tools.pose_estimation.pre_processings import bbox_xyxy2cs, get_warp_matrix
    from rtmlib.tools.pose_estimation.post_processings import get_simcc_maximum
    wb=Wholebody(det=os.environ["YOLOX_ONNX_PATH"],det_input_size=(640,640),
                 pose=os.environ["RTMW_ONNX_PATH"],to_openpose=False,
                 backend="onnxruntime",device="cpu")
    pm=wb.pose_model; w,h=pm.model_input_size

    def pose_rot(img,bbox,rot):
        c,s=bbox_xyxy2cs(np.asarray(bbox,float),padding=1.25)
        ar=w/h; bw,bh=np.hsplit(s.reshape(1,2),[1])
        s2=np.where(bw>bh*ar,np.hstack([bw,bw/ar]),np.hstack([bh*ar,bh]))[0]
        M=get_warp_matrix(c.reshape(2),s2,rot,output_size=(w,h))
        crop=cv2.warpAffine(img,M,(int(w),int(h)),flags=cv2.INTER_LINEAR)
        if pm.mean is not None: crop=(crop-np.array(pm.mean))/np.array(pm.std)
        locs,sc=get_simcc_maximum(*pm.inference(crop))
        kp=locs[0]/2.0
        Minv=cv2.invertAffineTransform(M)
        back=(Minv@np.concatenate([kp,np.ones((kp.shape[0],1))],axis=-1).T).T
        return back[:17], sc[0][:17]

    V=("prod_orig","prod_rot","box_orig","box_rot")
    K={k:[] for k in V}; S={k:[] for k in V}; FR=[]; ndet={k:0 for k in V}
    rd=imageio.get_reader(video); t0=time.perf_counter()
    for n,fr in enumerate(rd):
        if n%stride: continue
        H0,W0=fr.shape[:2]; sc0=640/max(H0,W0)
        img=np.asarray(Image.fromarray(fr).resize((round(W0*sc0),round(H0*sc0)),Image.BILINEAR))
        H,W=img.shape[:2]; rimg=np.ascontiguousarray(np.rot90(img,2))
        nan=(np.full((17,2),np.nan), np.zeros(17))

        k,s=wb(img)
        if k is not None and len(k): K["prod_orig"].append(k[0][:17,:2]); S["prod_orig"].append(s[0][:17]); ndet["prod_orig"]+=1
        else: K["prod_orig"].append(nan[0]); S["prod_orig"].append(nan[1])

        k,s=wb(rimg)
        if k is not None and len(k):
            kk=k[0][:17,:2].copy(); kk[:,0]=(W-1)-kk[:,0]; kk[:,1]=(H-1)-kk[:,1]
            K["prod_rot"].append(kk); S["prod_rot"].append(s[0][:17]); ndet["prod_rot"]+=1
        else: K["prod_rot"].append(nan[0]); S["prod_rot"].append(nan[1])

        b=wb.det_model(img)
        if b is not None and len(b):
            bbox=b[0]
            for name,rot in (("box_orig",0),("box_rot",180)):
                kk,ss=pose_rot(img,bbox,rot); K[name].append(kk); S[name].append(ss); ndet[name]+=1
        else:
            for name in ("box_orig","box_rot"): K[name].append(nan[0]); S[name].append(nan[1])
        FR.append(n)
        if len(FR)%25==0: print(f"  {len(FR)}f {time.perf_counter()-t0:.0f}s",flush=True)
    rd.close()
    K={k:np.array(v) for k,v in K.items()}; S={k:np.array(v) for k,v in S.items()}
    np.savez(f"{BASE}/out/{prefix}_decomp.npz", frames=np.array(FR),
             **{f"{k}_k":K[k] for k in V}, **{f"{k}_s":S[k] for k in V})

    def torso(A):
        sh=A[:,[5,6],:].mean(1); hp=A[:,[11,12],:].mean(1)
        return np.linalg.norm(sh-hp,axis=-1)
    print(f"\n===== {prefix} — {len(FR)}프레임 =====")
    print(f"{'변형':<12}{'평균conf':>10}{'붕괴':>7}{'미검출':>8}{'뼈위반p90평균':>15}")
    for k in V:
        A,Sc=K[k],S[k]
        uniq=np.array([len(set(map(tuple,np.round(A[t],1)))) for t in range(len(A))])
        bv=[]
        for i,j in BONES:
            L=np.linalg.norm(A[:,i,:]-A[:,j,:],axis=-1)/(torso(A)+1e-9)
            bv.append(np.nanpercentile(np.abs(np.log((L+1e-9)/(np.nanmedian(L)+1e-9))),90))
        print(f"{k:<12}{np.nanmean(Sc):>10.4f}{int((uniq<=8).sum()):>7}{len(FR)-ndet[k]:>8}{np.mean(bv):>15.3f}")
    tl=np.nanmean(np.stack([torso(K['prod_orig']),torso(K['prod_rot'])]),axis=0)
    d=np.linalg.norm(K['prod_orig']-K['prod_rot'],axis=-1)/(tl[:,None]+1e-9)
    print(f"\n불일치 prod_orig↔prod_rot (torso배): p10={np.nanpercentile(d,10):.3f} "
          f"p50={np.nanpercentile(d,50):.3f} p90={np.nanpercentile(d,90):.3f} p99={np.nanpercentile(d,99):.3f}")

if __name__=="__main__":
    main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 3)
