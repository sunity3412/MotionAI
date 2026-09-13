"""TTA 불일치를 관측가능성 계기로 쓸 수 있는가 — 관절별 실측.

seq_orig.npz (프로덕션 방향 1차 추론, 매 3프레임, 133kpt) 는 이미 있다.
여기서는 rot180 패스만 돌려 같은 프레임에 대해 관절별 불일치를 잰다.

불일치 = ||p_orig - p_rot180|| / torso_len   (해상도·거리 무관 정규화)
비교 대상 = RTMW conf (기존 계기)

물음: 불일치가 conf 보다 "봤다/못 봤다"를 잘 가르는가.
"""
import os, sys, json, time
import numpy as np
import imageio.v2 as imageio
from PIL import Image

BASE = "/Users/Shared/sunity-lr-audit"
BODY17 = ["nose","left_eye","right_eye","left_ear","right_ear","left_shoulder",
          "right_shoulder","left_elbow","right_elbow","left_wrist","right_wrist",
          "left_hip","right_hip","left_knee","right_knee","left_ankle","right_ankle"]

def main():
    from rtmlib import Wholebody
    src = np.load(f"{BASE}/seq_orig.npz") if os.path.exists(f"{BASE}/seq_orig.npz") \
          else np.load(f"{BASE}/out/seq_orig.npz")
    K0, S0, FR = src["kxy"], src["scores"], src["frames"]
    print(f"orig 시퀀스: {K0.shape} frames={FR[:3]}..{FR[-1]}")

    infer = Wholebody(det=os.environ["YOLOX_ONNX_PATH"], det_input_size=(640,640),
                      pose=os.environ["RTMW_ONNX_PATH"], to_openpose=False,
                      backend="onnxruntime", device="cpu")

    rd = imageio.get_reader(f"{BASE}/user.mp4")
    want = set(int(x) for x in FR)
    K1 = np.full_like(K0, np.nan); S1 = np.zeros_like(S0)
    pos = {int(f): i for i, f in enumerate(FR)}
    t0 = time.perf_counter()
    for n, fr in enumerate(rd):
        if n not in want: continue
        H0, W0 = fr.shape[:2]; sc = 640/max(H0, W0)
        img = np.asarray(Image.fromarray(fr).resize((round(W0*sc), round(H0*sc)), Image.BILINEAR))
        H, W = img.shape[:2]
        rot = np.ascontiguousarray(np.rot90(img, 2))
        k, s = infer(rot)
        i = pos[n]
        if k is not None and len(k):
            kk = k[0][:, :2].astype(float).copy()
            kk[:, 0] = (W-1) - kk[:, 0]; kk[:, 1] = (H-1) - kk[:, 1]
            K1[i] = kk; S1[i] = s[0].astype(float)
        if i % 20 == 0:
            print(f"  {i}/{len(FR)}  {time.perf_counter()-t0:.0f}s", flush=True)
    rd.close()
    np.savez(f"{BASE}/out/seq_rot180.npz", kxy=K1, scores=S1, frames=FR)

    # torso 길이로 정규화 (두 패스 평균)
    def torso(K):
        sh = K[:, [5,6], :].mean(1); hp = K[:, [11,12], :].mean(1)
        return np.linalg.norm(sh-hp, axis=-1)
    tl = np.nanmean(np.stack([torso(K0), torso(K1)]), axis=0)
    d = np.linalg.norm(K0[:, :17, :] - K1[:, :17, :], axis=-1) / (tl[:, None] + 1e-9)

    both = np.isfinite(d) & (S0[:, :17] > 0) & (S1[:, :17] > 0)
    print(f"\n유효 (프레임,관절) 쌍: {int(both.sum())}\n")
    print(f"{'관절':<16}{'불일치 p50':>11}{'p90':>9}{'최대':>9}{'conf0 p50':>11}{'conf1 p50':>11}")
    print("-"*70)
    rows = []
    for j, nm in enumerate(BODY17):
        m = both[:, j]
        if not m.any(): continue
        dj = d[m, j]; c0 = S0[m, j]; c1 = S1[m, j]
        rows.append((nm, np.percentile(dj,50), np.percentile(dj,90), dj.max(),
                     np.percentile(c0,50), np.percentile(c1,50)))
        print(f"{nm:<16}{rows[-1][1]:>11.3f}{rows[-1][2]:>9.3f}{rows[-1][3]:>9.2f}"
              f"{rows[-1][4]:>11.3f}{rows[-1][5]:>11.3f}")

    # 계기 비교: 불일치와 conf 가 서로 얼마나 다른 것을 말하는가
    dv = d[both]; cv = np.minimum(S0[:, :17], S1[:, :17])[both]
    print(f"\n불일치 분포 전체: p10={np.percentile(dv,10):.3f} p50={np.percentile(dv,50):.3f} "
          f"p90={np.percentile(dv,90):.3f} p99={np.percentile(dv,99):.3f} max={dv.max():.2f}")
    print(f"conf(min) 분포  : p10={np.percentile(cv,10):.3f} p50={np.percentile(cv,50):.3f} "
          f"p90={np.percentile(cv,90):.3f}")
    print(f"상관(스피어만 근사, 순위): {np.corrcoef(np.argsort(np.argsort(dv)), np.argsort(np.argsort(cv)))[0,1]:+.3f}")
    json.dump({"per_joint": [{"joint":r[0],"d_p50":r[1],"d_p90":r[2],"d_max":r[3],
                              "conf0_p50":r[4],"conf1_p50":r[5]} for r in rows]},
              open(f"{BASE}/out/tta_disagree.json","w"), indent=2, ensure_ascii=False)
    print(f"\n-> {BASE}/out/tta_disagree.json")

if __name__ == "__main__":
    main()
