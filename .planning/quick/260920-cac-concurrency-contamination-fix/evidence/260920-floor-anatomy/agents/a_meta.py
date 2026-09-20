"""조사 A 단계1 — self 4건의 메타 대조 (프레임 수 / fps 라벨 / 길이 비율)."""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

refs = H.load_references()
students = H.load_students()
facts = {r["id"]: r for r in json.load(open(f"{H.D}/facts.json"))}
by_id = {s["id"]: s for s in students}

rows = []
for mid, r in sorted(refs.items()):
    kr = r.get("keypointReport") or {}
    rows.append(dict(
        motion=mid,
        ref_frames=r.get("anglesFrames"),
        ref_rows=len(r["angles"]) // len(r.get("anglesJointKeys") or [1]),
        anglesRealFps=r.get("anglesRealFps"),
        kr_fps=kr.get("fps"),
        kr_frames=kr.get("frames") or kr.get("frameCount"),
        backbone=r.get("anglesBackbone"),
        clipRange=r.get("clipRange"),
        baseUntilS=r.get("baseUntilS"),
        sharedBase=r.get("sharedBaseMotionId"),
        ref_fps_used=H.ref_fps_of(r),
        ref_boundary=H.ref_boundary_of(r),
        coordDim=r.get("coordDim"),
        pipelineVersion=r.get("pipelineVersion"),
    ))
print("=== 기준 doc 메타 ===")
for d in rows:
    print(json.dumps(d, ensure_ascii=False))

print()
print("=== self 분석 (학생 = 기준 영상 그 자체) ===")
selfs = [f for f in facts.values() if f["label"] == "self"]
seen = set()
for f in sorted(selfs, key=lambda x: x["ref"]):
    if f["ref"] in seen:
        continue
    seen.add(f["ref"])
    s = by_id[f["id"]]
    U = H.student_matrix(s)
    R = H.ref_matrix(refs[f["ref"]])
    print(json.dumps(dict(
        id=f["id"], motion=f["ref"], scalar=round(f["scalar"], 3), dtw=round(f["dtw"], 3),
        tier=f["tier"],
        user_rows=int(U.shape[0]), ref_rows=int(R.shape[0]),
        ratio_ref_over_user=round(R.shape[0] / U.shape[0], 4),
        user_keys=s.get("keys") == list(H.JOINT_KEYS),
        extractor=s.get("extractor"),
        anglesExtractedBy=s.get("anglesExtractedBy"),
        match_window=dict(ustart=f["ustart"], uend=f["uend"], rstart=f["rstart"], rend=f["rend"], plen=f["plen"]),
        user_nan_frac=round(float(np.mean(~np.isfinite(U))), 4),
        ref_nan_frac=round(float(np.mean(~np.isfinite(R))), 4),
    ), ensure_ascii=False))
