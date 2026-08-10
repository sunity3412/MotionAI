"""후보 순간이 "같은 국면"인지 눈으로 본다 — 정규화 스켈레톤 겹쳐 그리기 (관찰 전용).

수치만으로는 "차이 42.9도"가 같은 결함이 더 크게 보이는 것인지, 두 사람이 다른 국면인
것인지 가릴 수 없다(08-09 에 그걸 못 가려서 "최대 차이 순간" 안을 폐기했다).

여기서는 짝거리(`_pose_dist`)가 실제로 재는 공간 — 골반 원점 · 몸통 길이 1 정규화 —
에 **두 사람을 겹쳐** 그린다. 국면이 다르면 겹치지 않는 것이 즉시 보인다.
영상·Firestore 불필요(align kp 만 씀).

usage: phase_contact_sheet.py <case> [out.png]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import compare_render as cr  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"

BONES = [
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_shoulder", "right_shoulder"), ("left_hip", "right_hip"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
]
CELL = 300
PAD = 34
U_COL, R_COL = (30, 130, 255), (255, 90, 40)


def _norm_pts(kp_at, joints: list[str], t: float):
    """골반 원점 · 몸통 길이 1 정규화 좌표 (`_pose_dist` 와 같은 공간)."""
    pts, conf = {}, {}
    for n in joints:
        p, c = kp_at(n, t)
        pts[n], conf[n] = np.asarray(p, dtype=float), c
    sh = (pts["left_shoulder"] + pts["right_shoulder"]) / 2
    hp = (pts["left_hip"] + pts["right_hip"]) / 2
    torso = float(np.linalg.norm(sh - hp))
    if torso < 1e-6:
        return None, None
    return {n: (pts[n] - hp) / torso for n in joints}, conf


def _draw(d: ImageDraw.ImageDraw, org, pts, conf, col, tri):
    def to_px(p):
        return (org[0] + CELL / 2 + p[0] * CELL * 0.24,
                org[1] + CELL / 2 + p[1] * CELL * 0.24)

    for a, b in BONES:
        if a in pts and b in pts:
            wide = 5 if (a in tri and b in tri) else 2
            d.line([to_px(pts[a]), to_px(pts[b])], fill=col, width=wide)
    for n, p in pts.items():
        x, y = to_px(p)
        r = 5 if n in tri else 2
        low = conf.get(n, 1.0) < cr.KP_CONF_MIN
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=(200, 0, 0) if low else col)


def run(case: str, out: Path):
    d0 = ROOT / case
    doc = json.load(open(d0 / "doc.json"))
    align = json.load(open(d0 / "align.json"))
    curve = align.get("curveRefSec")
    pairs = align.get("pairs") or {}
    afps = float(align["fps"])
    uF = int(align["userFrames"])
    joints = list(align["joints17"])
    u_at, r_at = cr._kp_reader(align, "user"), cr._kp_reader(align, "ref")

    pds = []
    for i in range(uF):
        pd = cr._pose_dist(u_at, r_at, i / afps, float(curve[i]))
        pds.append(pd)
    fin = [p for p in pds if p is not None]
    p10, pmed = float(np.percentile(fin, 10)), float(np.percentile(fin, 50))

    recs = [r for r in (doc["result"].get("deductionBreakdown") or {}).get("records") or []
            if "angle_vs_reference__" in (r.get("criterion") or "")
            and (r.get("criterion") or "").split("__", 1)[1] in cr._ANGLE_TRIPLES
            and (r.get("recordId") or "").split(":")[0] in pairs]
    if not recs:
        print(f"{case}: 대상 record 없음")
        return

    cols = ["현행 표시", "pd<=승인", "pd<=중앙", "pd<=p10"]
    W = PAD + len(cols) * (CELL + PAD)
    H = PAD + len(recs) * (CELL + 3 * PAD)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(img)

    for ri, rec in enumerate(recs):
        jk = (rec.get("criterion") or "").split("__", 1)[1]
        tri = set(cr._ANGLE_TRIPLES[jk])
        rid = (rec.get("recordId") or "").split(":")[0]
        pair = pairs[rid]
        ut0, rt0, pd0 = (float(pair["atVideoSec"]), float(pair["refVideoSec"]),
                         float(pair["poseDist"]))

        # 후보 수집 (표시 게이트 통과 = 양쪽 각도 산출 가능)
        cand = []
        for i in range(uF):
            ut, rt = i / afps, float(curve[i])
            a = cr._joint_angle(u_at, jk, ut, conf_min=cr.KP_CONF_MIN)
            b = cr._joint_angle(r_at, jk, rt, conf_min=cr.KP_CONF_MIN)
            if a is None or b is None or pds[i] is None:
                continue
            cand.append({"ut": ut, "rt": rt, "d": abs(a - b), "pd": pds[i],
                         "a": a, "b": b})

        def best_under(thr):
            c = [x for x in cand if x["pd"] <= thr]
            return max(c, key=lambda x: x["d"]) if c else None

        a0 = cr._joint_angle(u_at, jk, ut0, conf_min=cr.KP_CONF_MIN)
        b0 = cr._joint_angle(r_at, jk, rt0, conf_min=cr.KP_CONF_MIN)
        shots = [
            {"ut": ut0, "rt": rt0, "pd": pd0,
             "d": (abs(a0 - b0) if (a0 is not None and b0 is not None) else None),
             "a": a0, "b": b0},
            best_under(pd0), best_under(pmed), best_under(p10),
        ]

        y = PAD + ri * (CELL + 3 * PAD)
        dr.text((PAD, y), f"{case}  {rid}  {jk}  pts={rec.get('points')} "
                          f"dev={rec.get('deviation')}", fill=(0, 0, 0))
        for ci, (label, s) in enumerate(zip(cols, shots)):
            x = PAD + ci * (CELL + PAD)
            dr.rectangle([x, y + 18, x + CELL, y + 18 + CELL], outline=(210, 210, 210))
            if s is None:
                dr.text((x + 8, y + 24), f"{label}: 후보 없음", fill=(150, 0, 0))
                continue
            up, uc = _norm_pts(u_at, joints, s["ut"])
            rp, rc = _norm_pts(r_at, joints, s["rt"])
            if up:
                _draw(dr, (x, y + 18), up, uc, U_COL, tri)
            if rp:
                _draw(dr, (x, y + 18), rp, rc, R_COL, tri)
            dv = "-" if s["d"] is None else f"{s['d']:.1f}"
            ang = ("-" if s["a"] is None or s["b"] is None
                   else f"{s['a']:.0f} vs {s['b']:.0f}")
            dr.text((x + 4, y + 22 + CELL),
                    f"{label}  {s['ut']:.2f}s/{s['rt']:.2f}s", fill=(0, 0, 0))
            dr.text((x + 4, y + 34 + CELL),
                    f"차이 {dv}도 ({ang})  짝거리 {s['pd']:.3f}", fill=(0, 0, 0))
        print(f"{case} {rid} {jk}: " + " | ".join(
            "없음" if s is None else
            f"{c} d={'-' if s['d'] is None else f'{s[chr(100)]:.1f}'} pd={s['pd']:.3f}"
            for c, s in zip(cols, shots)))
    img.save(out)
    print("wrote", out, img.size, f"(파랑=나 / 주황=정은지, 빨강 점=conf<{cr.KP_CONF_MIN})")


if __name__ == "__main__":
    case = sys.argv[1]
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/tmp/{case}_phase.png")
    run(case, out)
