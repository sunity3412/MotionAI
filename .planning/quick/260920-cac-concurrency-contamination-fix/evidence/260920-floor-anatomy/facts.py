"""Shared fact table: per-analysis label (correct/fault/self/upload) + deviation + provenance."""
import json, collections, numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
b = json.load(open(f"{D}/baseline.json"))
src = json.load(open(f"{D}/src.json"))
st = {s["id"]: s for s in json.load(open(f"{D}/students.json"))}


def label(vk, sl, fn):
    v = (vk or "").lower(); s = (sl or "").lower(); f = (fn or "").lower()
    if v.startswith("reference/"):
        return "self"
    if "/correct" in v or ":success" in s or "correct" in f or "잘된" in f:
        return "correct"
    if "/fault" in v or ":fault" in s or "fault" in f or "잘못" in f:
        return "fault"
    if v.startswith("uploads/"):
        return "upload"
    return "unknown"


rows = []
for r in b:
    s = src.get(r["id"]) or {}
    vk, sl, fn = s.get("videoKey"), s.get("sourceLabel"), s.get("fileName")
    rows.append(dict(
        id=r["id"], uid=r["uid"], ref=r["ref"], vk=vk, sl=sl, fn=fn,
        label=label(vk, sl, fn), scalar=r["scalar"], dev=r["dev"],
        dtw=r["dtw"], frames=r["frames"], plen=r["plen"],
        ustart=r["ustart"], uend=r["uend"], rstart=r["rstart"], rend=r["rend"],
        overall=r.get("overall"), tier=r.get("tier"), body=r.get("body"),
        extractor=st[r["id"]].get("extractor"),
    ))
json.dump(rows, open(f"{D}/facts.json", "w"))

byref = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    byref[r["ref"]][r["label"]].append(r["scalar"])


def fmt(v):
    if not v:
        return "-"
    a = np.array(v)
    return f"{np.median(a):6.1f}+-{a.std(ddof=0):4.2f}(n{len(a)})"


order = sorted(byref, key=lambda k: -sum(len(v) for v in byref[k].values()))
print(f"{'motion':24s}{'correct':>20s}{'fault':>20s}{'ratio':>7s}{'self':>8s}{'upload':>14s}")
for m in order:
    d = byref[m]
    c, f = d.get("correct"), d.get("fault")
    ratio = f"{np.median(f)/np.median(c):5.2f}" if c and f and np.median(c) > 0 else "-"
    se = f"{np.median(d['self']):6.1f}" if d.get("self") else "-"
    up = f"{np.median(d['upload']):6.1f}(n{len(d['upload'])})" if d.get("upload") else "-"
    print(f"{m:24s}{fmt(c):>20s}{fmt(f):>20s}{ratio:>7s}{se:>8s}{up:>14s}")
print()
print("label counts:", dict(collections.Counter(r["label"] for r in rows)))
print("unknown videoKeys:", collections.Counter(
    (r["vk"] or "NONE") for r in rows if r["label"] == "unknown").most_common(8))
