"""조사 A 단계2b — 격자 '오프셋' 몫까지 포함한 상한.

단계2(행 고르기)는 학생 격자가 **기준에 없는 원본 프레임**을 잡는 사실을 못 담는다.
그 사이 프레임을 선형보간으로 세워 올린 것이 여기의 interp 격자다 (실제 포즈는
아니지만 '기준 행이 아닌 시점' 몫의 대리값).
또 인접 행 차이(= 한 프레임 사이에 각도가 얼마나 움직이나)를 같이 잰다 —
반 프레임 어긋남이 만들 수 있는 최대치의 눈금.
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

STUDENT_FPS = 10.0
refs = H.load_references()
out = []
print(f"{'motion':24s}{'nr':>5s}{'adj|d|med':>10s}{'adj p90':>9s}"
      f"{'interp.5':>10s}{'interp.25':>10s}{'dtw(i.5)':>10s}")
for mid, rdoc in sorted(refs.items()):
    R = H.ref_matrix(rdoc); nr = R.shape[0]; fps = H.ref_fps_of(rdoc); ratio = fps / STUDENT_FPS
    adj = np.abs(np.diff(R, axis=0))
    nu = int(round(nr / ratio))
    row = dict(motion=mid, nr=nr, adj_med=float(np.nanmedian(adj)), adj_p90=float(np.nanpercentile(adj, 90)))
    for ph in (0.5, 0.25):
        pos = np.clip(np.arange(nu) * ratio + ph, 0, nr - 1.0001)
        lo = np.floor(pos).astype(int); w = (pos - lo)[:, None]
        U = R[lo] * (1 - w) + R[lo + 1] * w
        dev, m = H.deviate(U, rdoc)
        row[f"interp{ph}"] = H.scalar(dev)
        row[f"interp{ph}_dtw"] = float(m.distance)
        row[f"interp{ph}_dev"] = [float(x) for x in dev]
    out.append(row)
    print(f"{mid:24s}{nr:5d}{row['adj_med']:10.3f}{row['adj_p90']:9.2f}"
          f"{row['interp0.5']:10.3f}{row['interp0.25']:10.3f}{row['interp0.5_dtw']:10.3f}")
json.dump(out, open(f"{H.D}/out/a_gridfloor2.json", "w"))
