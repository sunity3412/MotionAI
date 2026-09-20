"""E-5 — 카메라 불일치가 정확히 0 인 통제군에서도 바닥이 남는가.

통제군 구성: 기준 doc 자신의 raw joints3d 로 운영 features.compute_joint_angles 를
돌려 '학생 각도'를 만들고, 같은 doc 의 저장 angles 를 기준으로 운영
_deviation_against(H.deviate) 를 태운다.
  · 같은 영상 · 같은 프레임 · 같은 좌표 → 카메라 방위 불일치 = 정확히 0
  · 체형 불일치 = 0, 실력 불일치 = 0, 시간 격자 불일치 = 0 (프레임 1:1)
  · 남은 차이는 오직 temporal_fill (신뢰도 기반 시간축 보간) 뿐.
    운영 경로: angles = temporal_fill(compute_joint_angles(kp4ch),
               joint_uncertainty(kp4ch))   — pipeline/app.py:1560-1561
    joints3d 는 4번째 채널(신뢰도)이 없어 보간 전 값이다.

라이브 self 행(videoKey=reference/*.mp4)의 바닥과 나란히 놓고 본다.
"""
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D); sys.path.insert(0, f"{D}/out")
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
import harness as H, E_view as V
from sunity_shared.analysis import features
from sunity_shared.analysis.temporal import temporal_fill

refs = H.load_references()
facts = json.load(open(f"{D}/facts.json"))
byref = collections.defaultdict(lambda: collections.defaultdict(list))
for r in facts:
    byref[r["ref"]][r["label"]].append(r["scalar"])

# 라이브 self 행의 videoKey 확인 — 같은 영상인가
selfvk = collections.defaultdict(set)
for r in facts:
    if r["label"] == "self":
        selfvk[r["ref"]].add(r["vk"])
print("라이브 self 행 videoKey (카메라 불일치 0 의 근거):")
for m, v in sorted(selfvk.items()):
    print(f"   {m:24s} n={len(byref[m]['self']):3d}  vk={sorted(v)}")
print()

print(f"{'motion':24s}{'E5 zero-cam 바닥°':>18s}{'라이브 self°':>13s}{'라이브 correct°':>16s}"
      f"{'medConf':>9s}{'lowConf%':>10s}")
res = []
for m, r in sorted(refs.items()):
    nk = len(r["joints3dKeys"])
    kp = np.asarray(r["joints3d"], float).reshape(-1, nk, 3)
    # 운영 temporal_fill 을 불확실도 없이(NaN 보간+동일 스무딩) 태운다 — joints3d 에는
    # 신뢰도 채널이 없다. DTW 는 NaN 을 못 먹으므로 이 최소 보수는 필수.
    ua = temporal_fill(features.compute_joint_angles(kp))
    dev, match = H.deviate(ua, r)
    sc = H.scalar(dev)
    kr = r["keypointReport"]; conf = np.asarray(kr["confidence"], float)
    med = float(np.median(conf)); low = float((conf < 0.5).mean())
    se = byref[m]["self"]; co = byref[m]["correct"]
    res.append(dict(motion=m, zerocam=sc, dtw=float(match.distance),
                    live_self=float(np.median(se)) if se else None,
                    live_correct=float(np.median(co)) if co else None,
                    med_conf=med, low_conf=low))
    print(f"{m:24s}{sc:18.2f}{(np.median(se) if se else float('nan')):13.1f}"
          f"{(np.median(co) if co else float('nan')):16.1f}{med:9.3f}{low:10.1%}")
json.dump(res, open(f"{D}/out/E_05_zero_camera_control.json", "w"), ensure_ascii=False, indent=1)


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    ra = np.argsort(np.argsort(a)).astype(float); rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb))), int(a.size)


z = [x["zerocam"] for x in res]
print()
print("Spearman(E5 zero-cam 바닥, 라이브 self 바닥)   :", spearman(z, [x["live_self"] for x in res]))
print("Spearman(E5 zero-cam 바닥, 라이브 correct 바닥):", spearman(z, [x["live_correct"] for x in res]))
print("Spearman(저신뢰 프레임비율, 라이브 correct 바닥):",
      spearman([x["low_conf"] for x in res], [x["live_correct"] for x in res]))
print("Spearman(저신뢰 프레임비율, E5 zero-cam 바닥)  :",
      spearman([x["low_conf"] for x in res], z))
