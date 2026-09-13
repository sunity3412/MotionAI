"""동일 bbox 강제 + 두 방향 — 교란(YOLOX 박스 차이)을 제거한 깨끗한 A/B.

변형 3종:
  A  orig      : 프로덕션 그대로 (rot=0 crop)
  B  framerot  : 프레임 전체를 180° 돌려 추론 후 좌표 역매핑
  C  warprot   : crop affine 에만 rot=180 (프레임 복사 없음 — 운영 후보)
세 변형 전부 **같은 bbox**(원본 방향 det 1회)를 쓴다.
"""
import os, sys, json, time
import numpy as np, imageio.v2 as imageio
from PIL import Image
import cv2

BASE = "/Users/Shared/sunity-lr-audit"
BODY = list(range(17))
NAMES = ["nose","left_eye","right_eye","left_ear","right_ear","left_shoulder",
         "right_shoulder","left_elbow","right_elbow","left_wrist","right_wrist",
         "left_hip","right_hip","left_knee","right_knee","left_ankle","right_ankle"]

def main(video, prefix, stride):
    from rtmlib import Wholebody
    from rtmlib.tools.pose_estimation.pre_processings import bbox_xyxy2cs, top_down_affine
    from rtmlib.tools.pose_estimation.post_processings import get_simcc_maximum
    wb = Wholebody(det=os.environ["YOLOX_ONNX_PATH"], det_input_size=(640,640),
                   pose=os.environ["RTMW_ONNX_PATH"], to_openpose=False,
                   backend="onnxruntime", device="cpu")
    pm = wb.pose_model

    def pose_with_rot(img, bbox, rot):
        """pm.preprocess 를 rot 지정으로 재현 → inference → postprocess."""
        from rtmlib.tools.pose_estimation.pre_processings import get_warp_matrix
        w, h = pm.model_input_size
        c, s = bbox_xyxy2cs(bbox, padding=1.25)
        ar = w / h
        b_w, b_h = np.hsplit(s.reshape(1,2), [1])
        s2 = np.where(b_w > b_h*ar, np.hstack([b_w, b_w/ar]), np.hstack([b_h*ar, b_h]))[0]
        M = get_warp_matrix(c.reshape(2), s2, rot, output_size=(w, h))
        crop = cv2.warpAffine(img, M, (int(w), int(h)), flags=cv2.INTER_LINEAR)
        if pm.mean is not None:                      # ★ 프로덕션과 동일 정규화
            crop = (crop - np.array(pm.mean)) / np.array(pm.std)
        out = pm.inference(crop)
        # postprocess 를 그대로 못 쓰므로(center/scale 기반) 역변환을 직접
        simcc_x, simcc_y = out
        locs, scores = get_simcc_maximum(simcc_x, simcc_y)
        kp = locs / 2.0            # simcc_split_ratio=2.0 — 입력 crop 픽셀 좌표계
        Minv = cv2.invertAffineTransform(M)
        kp_h = np.concatenate([kp[0], np.ones((kp.shape[1],1))], axis=-1)
        back = (Minv @ kp_h.T).T
        return back, scores[0]

    rd = imageio.get_reader(video)
    recs = {k: {"k":[], "s":[]} for k in ("orig","framerot","warprot")}
    FR=[]; t0=time.perf_counter()
    for n, fr in enumerate(rd):
        if n % stride: continue
        H0,W0 = fr.shape[:2]; sc = 640/max(H0,W0)
        img = np.asarray(Image.fromarray(fr).resize((round(W0*sc),round(H0*sc)), Image.BILINEAR))
        H,W = img.shape[:2]
        boxes = wb.det_model(img)
        if boxes is None or not len(boxes):
            for k in recs: recs[k]["k"].append(np.full((17,2),np.nan)); recs[k]["s"].append(np.zeros(17))
            FR.append(n); continue
        # 가장 큰 박스 = 인물
        areas=[(b[2]-b[0])*(b[3]-b[1]) for b in boxes]
        bbox = np.asarray(boxes[int(np.argmax(areas))], dtype=float)

        k,s = pose_with_rot(img, bbox, 0)
        recs["orig"]["k"].append(k[:17]); recs["orig"]["s"].append(s[:17])

        k,s = pose_with_rot(img, bbox, 180)
        recs["warprot"]["k"].append(k[:17]); recs["warprot"]["s"].append(s[:17])

        rimg = np.ascontiguousarray(np.rot90(img,2))
        rb = np.array([W-1-bbox[2], H-1-bbox[3], W-1-bbox[0], H-1-bbox[1]])
        k,s = pose_with_rot(rimg, rb, 0)
        k = k.copy(); k[:,0]=(W-1)-k[:,0]; k[:,1]=(H-1)-k[:,1]
        recs["framerot"]["k"].append(k[:17]); recs["framerot"]["s"].append(s[:17])
        FR.append(n)
        if len(FR)%25==0: print(f"  {len(FR)}f {time.perf_counter()-t0:.0f}s", flush=True)
    rd.close()
    out={k:{"k":np.array(v["k"]),"s":np.array(v["s"])} for k,v in recs.items()}
    np.savez(f"{BASE}/out/{prefix}_clean.npz", frames=np.array(FR),
             **{f"{k}_k":v["k"] for k,v in out.items()},
             **{f"{k}_s":v["s"] for k,v in out.items()})

    def torso(K):
        sh=K[:,[5,6],:].mean(1); hp=K[:,[11,12],:].mean(1)
        return np.linalg.norm(sh-hp,axis=-1)
    print(f"\n===== {prefix} — {len(FR)}프레임 · 동일 bbox 강제 =====")
    for k,v in out.items():
        K,S=v["k"],v["s"]
        uniq=np.array([len(set(map(tuple,np.round(K[t],1)))) for t in range(len(K))])
        bone=[]
        for i,j in ((5,7),(7,9),(6,8),(8,10),(11,13),(13,15),(12,14),(14,16)):
            L=np.linalg.norm(K[:,i,:]-K[:,j,:],axis=-1)/(torso(K)+1e-9)
            bone.append(np.nanpercentile(np.abs(np.log((L+1e-9)/(np.nanmedian(L)+1e-9))),90))
        print(f"  {k:<10} conf {S.mean():.4f}   붕괴 {int((uniq<=8).sum()):>3}   뼈위반p90(평균) {np.mean(bone):.3f}")
    # framerot vs warprot 일치 확인 (같은 연산이어야 함)
    d=np.linalg.norm(out['framerot']['k']-out['warprot']['k'],axis=-1)
    print(f"\n  framerot vs warprot 좌표차: p50={np.nanpercentile(d,50):.2f}px p99={np.nanpercentile(d,99):.2f}px")
    # 불일치 계기
    K0,K1=out['orig']['k'],out['warprot']['k']
    tl=np.nanmean(np.stack([torso(K0),torso(K1)]),axis=0)
    dis=np.linalg.norm(K0-K1,axis=-1)/(tl[:,None]+1e-9)
    print(f"  불일치(torso배): p10={np.nanpercentile(dis,10):.3f} p50={np.nanpercentile(dis,50):.3f} "
          f"p90={np.nanpercentile(dis,90):.3f} p99={np.nanpercentile(dis,99):.3f}")

if __name__=="__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 3)
