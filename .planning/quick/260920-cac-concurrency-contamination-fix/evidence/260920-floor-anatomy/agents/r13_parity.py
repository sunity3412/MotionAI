"""반증 r13-C — '같은 원본 프레임' 전제의 직접 검정.

전제가 맞다면(학생 10fps=원본 step3, 기준 15fps=원본 step2, 같은 위상)
  학생 **짝수** 행 i -> 기준행 1.5i 는 정수 = 같은 원본 프레임 (위상차 0)
  학생 **홀수** 행 i -> 기준행 1.5i 는 .5 = 기준 프레임 사이 (위상차 1/30초)
따라서 짝수행 잔차 << 홀수행 잔차 여야 한다. 차이가 없으면
'같은 원본 프레임 짝을 쟀다'는 주장 자체가 성립하지 않는다.
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
selfs, seen = [], set()
for f in facts:
    if f["label"] == "self" and f["ref"] not in seen:
        seen.add(f["ref"]); selfs.append(f)

print(f"{'motion':22s}{'scale':>8s}{'sh':>5s}{'all':>8s}{'even(정수)':>11s}{'odd(사이)':>11s}{'odd/even':>9s}{'n_e':>5s}{'n_o':>5s}")
out=[]
for f in sorted(selfs, key=lambda x: x["ref"]):
    mid=f["ref"]
    U = H.student_matrix(by_id[mid_id:=f["id"]]) if False else H.student_matrix(by_id[f["id"]])
    R = H.ref_matrix(refs[mid])
    nu, nr = U.shape[0], R.shape[0]; scale = nr/nu
    best=None
    for sh in np.arange(-3, 3.01, 0.5):
        pos = np.arange(nu)*scale + sh
        idx = np.clip(np.round(pos).astype(int), 0, nr-1)
        per = np.median(np.abs(U - R[idx]), axis=1)
        v = float(np.median(per))
        if best is None or v < best[0]: best=(v, float(sh), pos, idx, per)
    v, sh, pos, idx, per = best
    # 위상: 기준행 격자에서의 소수부 (0 = 정확히 기준 프레임 위)
    frac = np.abs(pos - np.round(pos))
    on  = frac < 0.12          # 기준 프레임과 사실상 일치
    off = frac > 0.38          # 기준 프레임 사이
    res = dict(motion=mid, scale=round(scale,4), sh=sh, all=round(v,2),
               on=round(float(np.median(per[on])),2) if on.sum() else None,
               off=round(float(np.median(per[off])),2) if off.sum() else None,
               n_on=int(on.sum()), n_off=int(off.sum()))
    ratio = res["off"]/res["on"] if res["on"] else float('nan')
    out.append(res)
    print(f"{mid:22s}{scale:8.4f}{sh:5.1f}{v:8.2f}{res['on'] if res['on'] else float('nan'):11.2f}"
          f"{res['off'] if res['off'] else float('nan'):11.2f}{ratio:9.2f}{res['n_on']:5d}{res['n_off']:5d}")

print("\n대조 — 같은 검정을 '기준을 스스로 10fps 로 솎은 가짜 학생'에 적용 (포즈 동일, 격자만 다름)")
print(f"{'motion':22s}{'all':>8s}{'even(정수)':>11s}{'odd(사이)':>11s}")
for f in sorted(selfs, key=lambda x: x["ref"]):
    mid=f["ref"]; R=H.ref_matrix(refs[mid]); nr=R.shape[0]
    fps=H.ref_fps_of(refs[mid]); ratio=fps/10.0
    nu=int(round(nr/ratio))
    pos=np.arange(nu)*ratio
    idx=np.clip(np.round(pos).astype(int),0,nr-1)
    U=R[idx]                      # 진짜 라이브라면 여기가 '원본의 그 시점 포즈'여야 한다
    per=np.median(np.abs(U-R[idx]),axis=1)
    frac=np.abs(pos-np.round(pos))
    print(f"{mid:22s}{np.median(per):8.2f}{np.median(per[frac<0.12]):11.2f}"
          f"{(np.median(per[frac>0.38]) if (frac>0.38).sum() else float('nan')):11.2f}")
json.dump(out, open("r13_parity.json","w"))
