"""E-4 — 관측된 시점 불일치를 각도(도)로 환산해 '촬영 각도가 바닥에서 먹는 몫'을 낸다.

환산 사슬 (전부 보수적으로 카메라에 유리하게):
 1) 짝쌍 계통 비 (E-2) 를 cos 단축으로 읽어 implied Δ방위각 δ 를 뽑는다.
    한쪽이 완전 정면(φ=0)이라고 가정 → δ 는 가능한 최대값(상한).
 2) δ 를 E-3 시뮬 median 곡선에 통과시켜 '그 δ 가 만들 수 있는 편차 스칼라' 로 환산.
 3) 실측 바닥 대비 몫.

기술자 불일치에는 자세 차이도 섞여 있으므로 δ 도 몫도 전부 상한이다.
"""
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D); sys.path.insert(0, f"{D}/out")

rows = json.load(open(f"{D}/out/E_02_matched_pairs.json"))
# E-3 시뮬 median 곡선 (δ도 → median |Δ2D각|도)
SIM_D = np.array([0, 5, 10, 15, 20, 30, 45, 60, 90])
SIM_M = np.array([0.0, 2.23, 4.42, 6.52, 8.59, 12.50, 18.03, 22.38, 25.96])


def implied_delta(logratio):
    """log(stu/ref) → 가능한 최대 Δ방위각(도). 한쪽 정면 가정."""
    r = float(np.exp(logratio))
    r = r if r <= 1 else 1.0 / r
    r = min(max(r, 1e-6), 1.0)
    return float(np.degrees(np.arccos(r)))


print(f"{'motion':24s}{'label':9s}{'바닥(실측)°':>12s}"
      f"{'δ_sw':>7s}{'δ_hw':>7s}{'δ_ear':>7s}{'δ_max':>8s}{'시뮬상한°':>11s}{'몫(상한)':>10s}")
out = []
for r in rows:
    ds = implied_delta(r["sw_torso_sysdex"])
    dh = implied_delta(r["hw_torso_sysdex"])
    de = implied_delta(r["ear_torso_sysdex"])
    # 몸축 기울기·어깨선 각 차이도 방위각 차이로 그대로 읽어준다(추가 관대)
    dt = abs(r["body_tilt_deg_sysdeg"]); da = abs(r["sh_axis_deg_sysdeg"])
    dmax = max(ds, dh, de, dt, da)
    cap = float(np.interp(dmax, SIM_D, SIM_M))
    floor = r["dev"]
    out.append(dict(motion=r["motion"], label=r["label"], floor=floor,
                    d_sw=ds, d_hw=dh, d_ear=de, d_tilt=dt, d_shax=da,
                    d_max=dmax, sim_cap=cap, share=cap / floor))
    print(f"{r['motion']:24s}{r['label']:9s}{floor:12.2f}{ds:7.1f}{dh:7.1f}{de:7.1f}"
          f"{dmax:8.1f}{cap:11.2f}{cap/floor:10.1%}")
json.dump(out, open(f"{D}/out/E_04_share.json", "w"), ensure_ascii=False, indent=1)

print()
print("δ_tilt / δ_shax (몸축 기울기·어깨선 각 계통차, 도):")
for r in rows:
    print(f"   {r['motion']:24s} tilt={r['body_tilt_deg_sysdeg']:+7.2f}  shax={r['sh_axis_deg_sysdeg']:+7.2f}")

print()
print("바닥을 카메라만으로 설명하려면 필요한 δ (E-3 median 곡선 역산):")
for r in rows:
    need = float(np.interp(r["dev"], SIM_M, SIM_D, left=0, right=np.inf))
    print(f"   {r['motion']:24s} 바닥 {r['dev']:5.2f}° → δ ≈ {need if np.isfinite(need) else float('nan'):.0f}°"
          + ("  (시뮬 최대 δ=90° 로도 도달 불가)" if r["dev"] > SIM_M[-1] else ""))
