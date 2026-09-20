"""조사 A 단계7 — (1) 같은 영상 재분석의 각도행렬이 동일한가(결정론)
                   (2) 격자 실험의 median 0 이 '중앙값이라서'인지 확인 (mean 도 같이)."""
import json, sys, collections
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

facts = json.load(open(f"{H.D}/facts.json"))
by_id = {s["id"]: s for s in H.load_students()}

# (1) 같은 videoKey 를 쓴 분석들의 각도행렬 대조
g = collections.defaultdict(list)
for f in facts:
    if f["vk"]:
        g[f["vk"]].append(f["id"])
print("=== 같은 videoKey 재분석의 각도행렬 동일성 ===")
n_same = n_diff = 0
examples = []
for vk, ids in sorted(g.items()):
    if len(ids) < 2:
        continue
    base = H.student_matrix(by_id[ids[0]])
    worst = 0.0; shapes = {base.shape}
    for i in ids[1:]:
        M = H.student_matrix(by_id[i]); shapes.add(M.shape)
        if M.shape != base.shape:
            worst = float("inf"); continue
        worst = max(worst, float(np.nanmax(np.abs(M - base))))
    if worst == 0.0:
        n_same += 1
    else:
        n_diff += 1
        examples.append((vk, len(ids), worst, sorted(shapes)))
print(f"videoKey 그룹 {n_same+n_diff}개 중 전원 byte-동일 = {n_same}, 차이 있음 = {n_diff}")
for e in examples[:10]:
    print("  차이:", e[0], "n=", e[1], "max|d|=", e[2], "shapes=", e[3])

# self 분석 createdAt
print("\n=== self 분석 createdAt ===")
for f in facts:
    if f["label"] == "self":
        print(" ", f["id"], f["ref"], by_id[f["id"]].get("createdAt"))
        
# (2) 격자 실험: median 0 의 내부 (mean / 0 스텝 비율)
print("\n=== 격자(ratio) 실험의 내부 — median 0 이 무엇을 가리고 있나 ===")
refs = H.load_references()
print(f"{'motion':24s}{'med':>7s}{'mean':>8s}{'p75':>8s}{'p90':>8s}{'frac|d|=0':>11s}")
for mid, rdoc in sorted(refs.items()):
    R = H.ref_matrix(rdoc); nr = R.shape[0]; ratio = H.ref_fps_of(rdoc) / 10.0
    nu = int(round(nr / ratio))
    idx = np.clip(np.round(np.arange(nu) * ratio).astype(int), 0, nr - 1)
    U = R[idx]
    dev, m = H.deviate(U, rdoc)
    Useg = U[m.start:m.end]; Rwin = R[m.ref_start:m.ref_end]
    D = np.abs(np.asarray([Useg[u] - Rwin[r] for u, r in m.path]))
    print(f"{mid:24s}{np.median(D):7.3f}{np.mean(D):8.3f}{np.percentile(D,75):8.3f}"
          f"{np.percentile(D,90):8.3f}{float(np.mean(D==0)):11.3f}")
