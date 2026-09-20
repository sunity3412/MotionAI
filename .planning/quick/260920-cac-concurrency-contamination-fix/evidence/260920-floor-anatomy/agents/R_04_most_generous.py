"""R-4 (반증) — '가장 관대하게 읽어도 상한 39%' 를 정말 가장 관대하게 다시 읽는다.
두 군데만 고친다. 둘 다 조사 자신이 만든 값이다.
  (1) δ 환산에 좌우 사지 투영길이 계통차(lr_*)를 포함 — E-2 가 계산해 json 에 넣고
      E-4 가 뺀 값. 단축(foreshortening)은 방위각의 1차 지표다.
  (2) 왜곡 곡선을 균일 임의자세(E-3 median) 대신 그 동작의 실제 각도 분포로 가중한
      곡선(R-2)으로 — E-3 스스로 '민감 구간은 2.8배'라고 적었다.
"""
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
r01 = {x["motion"]: x for x in json.load(open(f"{D}/out/R_01_share_with_limbs.json"))}
r02 = {x["motion"]: x for x in json.load(open(f"{D}/out/R_02_conditional_bound.json"))}
DELT = np.array([0, 5, 10, 15, 20, 30, 45, 60, 90], float)
E3 = np.array([0.0, 2.23, 4.42, 6.52, 8.59, 12.50, 18.03, 22.38, 25.96])

print(f"{'motion':24s}{'바닥(fixture)°':>15s}{'몫: E-4 주장':>14s}{'+lr':>9s}{'+lr+동작가중':>14s}"
      f"{'필요δ(E3)':>11s}{'필요δ(가중)':>12s}{'관측δ상한':>11s}")
for m, a in r01.items():
    curve = np.array([0.0] + r02[m]["curve"])
    floor = a["floor"]
    cap_w = float(np.interp(a["d_all"], DELT, curve))
    need_e3 = float(np.interp(floor, E3, DELT, left=0, right=np.inf))
    need_w = float(np.interp(floor, curve, DELT, left=0, right=np.inf))
    print(f"{m:24s}{floor:15.2f}{a['share_e4']:14.1%}{a['share_all']:9.1%}{cap_w/floor:14.1%}"
          f"{need_e3:11.0f}{need_w:12.0f}{a['d_all']:11.1f}")
print()
print("주: 관측δ상한 > 필요δ 이면 '가장 관대한 읽기'로는 카메라가 바닥을 전부 덮을 수 있다는 뜻.")
