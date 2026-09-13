"""PR 원근 워프(현재 운영 ON) vs 180° 회전 — 같은 프레임 정면 대결.

A prod        : 현행 1-pass
B pr_warp     : 리포의 inversion_warp 그대로 (H=K·R·K⁻¹) 2차 추론
C rot180      : 프레임 180° 회전 2차 추론
D rot+pr      : 180° 회전 후 PR 워프까지
"""
import os, sys, time
import numpy as np, imageio.v2 as imageio, cv2
from PIL import Image
sys.path.insert(0,"/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
from sunity_shared.analysis.inversion_warp import (
    detect_inversion, smooth_centers, build_homography, warp_frames,
    unwarp_frame_keypoints, unwarp_points)

BASE="/Users/Shared/sunity-lr-audit"
BONES=((5,7),(7,9),(6,8),(8,10),(11,13),(13,15),(12,14),(14,16))

def torso(A):
    sh=A[:,[5,6],:].mean(1); hp=A[:,[11,12],:].mean(1)
    return np.linalg.norm(sh-hp,axis=-1)

def bone_violation(A):
    out=[]
    for i,j in BONES:
        L=np.linalg.norm(A[:,i,:]-A[:,j,:],axis=-1)/(torso(A)+1e-9)
        out.append(np.nanpercentile(np.abs(np.log((L+1e-9)/(np.nanmedian(L)+1e-9))),90))
    return float(np.mean(out))

def bone_cv(A):
    """뼈 길이 변동계수 — spike 가 쓴 지표."""
    cvs=[]
    for i,j in BONES:
        L=np.linalg.norm(A[:,i,:]-A[:,j,:],axis=-1)
        L=L[np.isfinite(L)&(L>0)]
        if len(L)>2: cvs.append(np.std(L)/np.mean(L))
    return float(np.mean(cvs))

def main(video, prefix, stride=3):
    from rtmlib import Wholebody
    wb=Wholebody(det=os.environ["YOLOX_ONNX_PATH"],det_input_size=(640,640),
                 pose=os.environ["RTMW_ONNX_PATH"],to_openpose=False,
                 backend="onnxruntime",device="cpu")
    # 1차 — 프레임 수집 + prod 결과
    rd=imageio.get_reader(video); frames=[]; K=[]; S=[]
    for n,fr in enumerate(rd):
        if n%stride: continue
        H0,W0=fr.shape[:2]; sc=640/max(H0,W0)
        img=np.asarray(Image.fromarray(fr).resize((round(W0*sc),round(H0*sc)),Image.BILINEAR))
        frames.append(img)
    rd.close()
    frames=np.array(frames); T,H,W,_=frames.shape
    print(f"{prefix}: {T}프레임 {W}x{H}")
    t0=time.perf_counter()
    k133=np.full((T,133,2),np.nan); s133=np.zeros((T,133))
    for t in range(T):
        k,s=wb(frames[t])
        if k is not None and len(k): k133[t]=k[0][:,:2]; s133[t]=s[0]
    print(f"  1차 {time.perf_counter()-t0:.0f}s")
    det=detect_inversion(k133,s133)
    print(f"  detect_inversion -> is_inverted={det.is_inverted} ratio={det.inverted_ratio:.3f} run={det.longest_run_frames}")

    res={"prod":(k133[:,:17,:].copy(), s133[:,:17].copy())}

    # B: PR warp (리포 그대로)
    centers=smooth_centers(k133,s133)
    Hs=[build_homography(centers[t],W,H) for t in range(T)]
    warped=warp_frames(frames,Hs)
    kb=np.full((T,17,2),np.nan); sb=np.zeros((T,17))
    for t in range(T):
        k,s=wb(warped[t])
        if k is None or not len(k): continue
        back,ok=unwarp_frame_keypoints(Hs[t],k[0][:17,:2],W,H)
        if ok: kb[t]=back; sb[t]=s[0][:17]
    res["pr_warp"]=(kb,sb)

    # C: rot180
    rot=np.ascontiguousarray(frames[:,::-1,::-1,:])
    kc=np.full((T,17,2),np.nan); sc_=np.zeros((T,17))
    for t in range(T):
        k,s=wb(rot[t])
        if k is None or not len(k): continue
        kk=k[0][:17,:2].copy(); kk[:,0]=(W-1)-kk[:,0]; kk[:,1]=(H-1)-kk[:,1]
        kc[t]=kk; sc_[t]=s[0][:17]
    res["rot180"]=(kc,sc_)

    # D: rot180 + PR warp
    kd=np.full((T,17,2),np.nan); sd=np.zeros((T,17))
    krot=np.full((T,133,2),np.nan); srot=np.zeros((T,133))
    for t in range(T):
        k,s=wb(rot[t])
        if k is not None and len(k): krot[t]=k[0][:,:2]; srot[t]=s[0]
    c2=smooth_centers(krot,srot)
    if c2 is not None:
        H2=[build_homography(c2[t],W,H) for t in range(T)]
        w2=warp_frames(rot,H2)
        for t in range(T):
            k,s=wb(w2[t])
            if k is None or not len(k): continue
            back,ok=unwarp_frame_keypoints(H2[t],k[0][:17,:2],W,H)
            if not ok: continue
            back=back.copy(); back[:,0]=(W-1)-back[:,0]; back[:,1]=(H-1)-back[:,1]
            kd[t]=back; sd[t]=s[0][:17]
    res["rot+pr"]=(kd,sd)

    print(f"\n{'변형':<10}{'평균conf':>10}{'붕괴':>7}{'미산출':>8}{'뼈위반p90':>12}{'boneCV':>10}")
    for name,(A,Sc) in res.items():
        uniq=np.array([len(set(map(tuple,np.round(A[t],1)))) for t in range(T)])
        miss=int(np.isnan(A[:,0,0]).sum())
        print(f"{name:<10}{np.nanmean(Sc):>10.4f}{int((uniq<=8).sum()):>7}{miss:>8}{bone_violation(A):>12.3f}{bone_cv(A):>10.3f}")
    np.savez(f"{BASE}/out/{prefix}_h2h.npz", **{f"{k}_k":v[0] for k,v in res.items()},
             **{f"{k}_s":v[1] for k,v in res.items()})

if __name__=="__main__":
    main(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 3)
