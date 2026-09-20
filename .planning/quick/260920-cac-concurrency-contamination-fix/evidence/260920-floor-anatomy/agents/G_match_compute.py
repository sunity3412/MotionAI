"""조사 G 단계 1 — 875건 전부 × 기준 11편 DTW 매칭 전량 계산.

운영 함수만 호출한다: H.deviate -> pipeline/app.py::_deviation_against -> motion_dtw.
매칭 지표 = MotionMatch.distance (정규화 DTW 거리) — §11-1 이 쓴 것과 같은 지표.
편차 스칼라도 함께 저장(오분류 대가 측정에 재사용 가능).

출력: out/G_match.json  [{id,uid,ref,vk,label,pred,dist{refid:d},scalar{refid:s}}]
"""
from __future__ import annotations
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import numpy as np  # noqa: E402

_H = None
_REFS = None


def _init():
    global _H, _REFS
    import harness as H
    _H = H
    _REFS = H.load_references()


def _one(payload):
    aid, angles, nj = payload
    if _H is None:
        _init()
    m = np.asarray(angles, dtype=float).reshape(-1, nj)
    dist, sc = {}, {}
    for rid, rdoc in _REFS.items():
        try:
            dev, match = _H.deviate(m, rdoc)
            dist[rid] = float(match.distance)
            sc[rid] = float(_H.scalar(dev))
        except Exception as e:  # noqa: BLE001 — 실패도 기록해야 표본이 안 사라진다
            dist[rid] = float("nan")
            sc[rid] = float("nan")
    return aid, dist, sc


def main():
    facts = json.load(open(f"{D}/facts.json"))
    students = {s["id"]: s for s in json.load(open(f"{D}/students.json"))}
    jobs = []
    for r in facts:
        s = students[r["id"]]
        nj = len(s.get("keys") or []) or 8
        jobs.append((r["id"], s["angles"], nj))
    print(f"jobs={len(jobs)}", flush=True)
    t0 = time.time()
    out = {}
    with ProcessPoolExecutor(max_workers=8, initializer=_init) as ex:
        for i, (aid, dist, sc) in enumerate(ex.map(_one, jobs, chunksize=4)):
            out[aid] = (dist, sc)
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    rows = []
    for r in facts:
        dist, sc = out[r["id"]]
        fin = {k: v for k, v in dist.items() if np.isfinite(v)}
        pred = min(fin, key=fin.get) if fin else None
        rows.append(dict(id=r["id"], uid=r["uid"], ref=r["ref"], vk=r["vk"],
                         fn=r["fn"], label=r["label"], frames=r["frames"],
                         pred=pred, dist=dist, sc=sc))
    json.dump(rows, open(f"{D}/out/G_match.json", "w"))
    print(f"done {len(rows)} rows in {time.time()-t0:.0f}s -> out/G_match.json")


if __name__ == "__main__":
    main()
