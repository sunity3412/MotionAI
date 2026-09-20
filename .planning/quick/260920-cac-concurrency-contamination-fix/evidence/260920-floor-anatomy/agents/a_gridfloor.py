"""조사 A 단계2 — 순수 시간격자 바닥.

기준 각도행렬을 **그 자체로부터** 재샘플링(행을 고르기만 — 새 포즈 0, 보간 0)해
학생 자리에 넣고 운영 H.deviate 로 편차를 낸다. 포즈 데이터가 완전히 동일한데
시간 격자만 다를 때 생기는 바닥 = 시간축이 설명하는 몫.

격자 3종:
  identity : 기준 그대로 (건전성 확인 — 0 이어야 한다)
  ratio    : 라이브 학생 격자 재현. 기준 ~14.95fps → 학생 ~10.0fps (원본 30fps step3).
             user row i := ref row round(i * ref_fps/10.0 + phase)   (phase 0/0.5/1.0)
  intstep  : 정수 솎기 step 2/3, 위상 전부 (엄밀한 부분집합)
"""
import json, sys, time
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

STUDENT_FPS = 10.0  # self 5건 실측: nu/nr*ref_fps = 9.976~10.01

refs = H.load_references()
out = []
t0 = time.time()
for mid, rdoc in sorted(refs.items()):
    R = H.ref_matrix(rdoc)
    nr = R.shape[0]
    fps = H.ref_fps_of(rdoc)
    ratio = fps / STUDENT_FPS

    def run(tag, idx):
        idx = np.clip(np.asarray(idx, dtype=int), 0, nr - 1)
        U = R[idx]
        dev, m = H.deviate(U, rdoc)
        out.append(dict(motion=mid, grid=tag, nu=int(U.shape[0]), nr=nr,
                        ref_fps=fps, scalar=H.scalar(dev),
                        dev=[float(x) for x in dev], dtw=float(m.distance),
                        ustart=int(m.start), uend=int(m.end),
                        rstart=int(m.ref_start), rend=int(m.ref_end),
                        plen=len(m.path)))
        print(f"  {mid:24s} {tag:14s} nu={U.shape[0]:4d} scalar={H.scalar(dev):7.3f} "
              f"dtw={m.distance:7.3f}  ({time.time()-t0:.0f}s)", flush=True)

    run("identity", np.arange(nr))
    nu = int(round(nr / ratio))
    for ph in (0.0, 0.5, 1.0):
        run(f"ratio_ph{ph}", np.round(np.arange(nu) * ratio + ph))
    for step in (2, 3):
        for ph in range(step):
            run(f"step{step}_ph{ph}", np.arange(ph, nr, step))

json.dump(out, open(f"{H.D}/out/a_gridfloor.json", "w"))
print(f"\n저장 {len(out)} 행  {time.time()-t0:.0f}s")
