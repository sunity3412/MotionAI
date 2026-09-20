"""R-1 (반증) — E-4 의 '가장 관대한 몫 상한 39%' 재계산.

E-2 는 시점 기술자 9종 중 좌우 사지 투영길이 log 비(lr_uparm/forearm/thigh/shank)의
짝쌍 계통 성분을 실제로 계산해 json 에 넣어놓고, E-4 의 δ 환산에서는 그 4종을 뺐다
(δ_sw/δ_hw/δ_ear/δ_tilt/δ_shax 만 사용). 좌우 사지 투영길이 비야말로 방위각에
가장 직접 반응하는 단축(foreshortening) 지표다. 같은 환산 규칙을 그 4종에도
적용하면 '가장 관대한 읽기'가 얼마가 되는지 다시 낸다. 새 계기는 쓰지 않는다 —
E-2/E-3/E-4 가 이미 만든 값만 재조합한다.
"""
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"

rows = json.load(open(f"{D}/out/E_02_matched_pairs.json"))
SIM_D = np.array([0, 5, 10, 15, 20, 30, 45, 60, 90])
SIM_M = np.array([0.0, 2.23, 4.42, 6.52, 8.59, 12.50, 18.03, 22.38, 25.96])


def implied_delta(logratio):
    r = float(np.exp(logratio)); r = r if r <= 1 else 1.0 / r
    r = min(max(r, 1e-6), 1.0)
    return float(np.degrees(np.arccos(r)))


print(f"{'motion':24s}{'label':9s}{'바닥°':>8s}{'δ_max(E4)':>11s}{'몫(E4)':>9s}"
      f"{'δ_lr_max':>10s}{'δ_max(+lr)':>12s}{'몫(+lr)':>10s}  최대기여 기술자")
out = []
for r in rows:
    base = {"sw": implied_delta(r["sw_torso_sysdex"]), "hw": implied_delta(r["hw_torso_sysdex"]),
            "ear": implied_delta(r["ear_torso_sysdex"]),
            "tilt": abs(r["body_tilt_deg_sysdeg"]), "shax": abs(r["sh_axis_deg_sysdeg"])}
    lr = {k: implied_delta(r[f"lr_{k}_sys"]) for k in ("uparm", "forearm", "thigh", "shank")}
    d_e4 = max(base.values())
    d_lr = max(lr.values())
    d_all = max(d_e4, d_lr)
    allk = dict(base); allk.update({f"lr_{k}": v for k, v in lr.items()})
    top = max(allk, key=allk.get)
    cap_e4 = float(np.interp(d_e4, SIM_D, SIM_M))
    cap_all = float(np.interp(d_all, SIM_D, SIM_M))
    out.append(dict(motion=r["motion"], label=r["label"], floor=r["dev"],
                    d_e4=d_e4, share_e4=cap_e4 / r["dev"],
                    d_lr_max=d_lr, d_all=d_all, cap_all=cap_all,
                    share_all=cap_all / r["dev"], top=top, deltas=allk))
    print(f"{r['motion']:24s}{r['label']:9s}{r['dev']:8.2f}{d_e4:11.1f}{cap_e4/r['dev']:9.1%}"
          f"{d_lr:10.1f}{d_all:12.1f}{cap_all/r['dev']:10.1%}  {top}")
json.dump(out, open(f"{D}/out/R_01_share_with_limbs.json", "w"), ensure_ascii=False, indent=1)
