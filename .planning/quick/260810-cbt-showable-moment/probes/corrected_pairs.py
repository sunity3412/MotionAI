"""교정된 시각으로 **기존 짝 선정 함수를 그대로** 다시 돌려 대조 (관찰 전용).

`fps_label_audit.py` 가 확인한 것: record 의 `atVideoSec = atFrameIdx / 9.0` 인데
실제 솎음 rate 는 `src_fps / round(src_fps/9)` (30fps 원본 → 9.997fps) 라서 저장된
초가 ~10% 크다. `select_pairs` 는 사용자 프레임을 그 초에서 **클램프해서 그대로** 쓰고
(재탐색 없음) 기준만 ±2초 재탐색하므로, 틀린 사용자 프레임에 기준을 맞춘 짝이 된다.

여기서 새 규칙을 만들지 않는다. `compare_align.select_pairs` · `pose_feature` ·
`dtw` 를 **그대로 호출**하고 입력의 초만 교정해서, 카드가 무엇을 보여주게 되는지
대조한다. 정렬(DTW 곡선)·짝 선정 로직 무접촉.

usage: corrected_pairs.py <video_dir> [case...]
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))
sys.path.insert(0, str(HERE))

from sunity_shared.analysis import compare_align as ca  # noqa: E402
from sunity_shared.analysis import compare_render as cr  # noqa: E402
from rest_body_alignment import pd_rest  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"
TARGET_FPS = 9.0
USER_VIDEO = {
    "pdshapefault": "pdshapefault1785373695.mp4",
    "peterpan": "peterpanfault1785373695.mp4",
    "elbow": "elbow_fault.mp4",
    "powerspin": "powerspin_fault.mp4",
    "kipup": "kipup_fault.mp4",
}


def real_fps(video: Path) -> tuple[float, float, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate,nb_frames", "-of", "json", str(video)],
        capture_output=True, text=True, check=True).stdout
    st = json.loads(out)["streams"][0]
    num, den = st["avg_frame_rate"].split("/")
    src = float(num) / float(den)
    step = max(1, round(src / TARGET_FPS))
    return src / step, src, int(st["nb_frames"])


def run(vdir: Path, case: str):
    d = ROOT / case
    doc = json.load(open(d / "doc.json"))
    align = json.load(open(d / "align.json"))
    vid = vdir / USER_VIDEO.get(case, "")
    if not vid.exists():
        print(f"\n=== {case} === 영상 없음 — 건너뜀")
        return
    rfps, src, _ = real_fps(vid)

    afps = float(align["fps"])
    uF, rF = int(align["userFrames"]), int(align["refFrames"])
    joints = list(align["joints17"])
    ukn = np.asarray(align["userKp"], dtype=float).reshape(uF, 17, 2)
    rkn = np.asarray(align["refKp"], dtype=float).reshape(rF, 17, 2)
    usc = np.asarray(align["userScore"], dtype=float)
    rsc = np.asarray(align["refScore"], dtype=float)

    # build_align 과 같은 출처로 D·curve 재구성 (정렬 로직 무접촉)
    fu, fr = ca.pose_feature(ukn, usc), ca.pose_feature(rkn, rsc)
    D = np.linalg.norm(fu[:, None, :] - fr[None, :, :], axis=2)
    curve = ca.smooth_curve(ca.dtw_path(D), len(fu))

    recs = [r for r in (doc["result"].get("deductionBreakdown") or {}).get("records") or []
            if r.get("atFrameIdx") is not None]
    fixed = []
    for r in recs:
        r2 = dict(r)
        r2["atVideoSec"] = float(r["atFrameIdx"]) / rfps
        fixed.append(r2)

    old = ca.select_pairs(recs, D, curve, ukn, usc, rsc)
    new = ca.select_pairs(fixed, D, curve, ukn, usc, rsc)

    u_at, r_at = cr._kp_reader(align, "user"), cr._kp_reader(align, "ref")

    print(f"\n=== {case} ===  실제 {rfps:.3f}fps (원본 {src:.2f}fps) · "
          f"클립 {uF}프레임 = {uF/afps:.2f}s")
    print(f"  {'rid':<5}{'관절':<15}"
          f"{'현행 u/ref':>16}{'교정 u/ref':>16}{'Δu프레임':>9}"
          f"   그림: 차이 / 나머지몸정렬")
    for r in recs:
        rid = r["recordId"].split(":")[0]
        if rid not in old or rid not in new:
            continue
        jk = r["criterion"].split("__", 1)[1] if "angle_vs_reference__" in r["criterion"] \
            else None
        o, n = old[rid], new[rid]
        du = (n["atVideoSec"] - o["atVideoSec"]) * afps

        def shot(p):
            ut, rt = float(p["atVideoSec"]), float(p["refVideoSec"])
            ut_c = min(ut, (uF - 1) / afps)      # select_pairs 의 클램프 재현
            if jk is None or jk not in cr._ANGLE_TRIPLES:
                return "-", None, None
            a = cr._joint_angle(u_at, jk, ut_c, conf_min=cr.KP_CONF_MIN)
            b = cr._joint_angle(r_at, jk, rt, conf_min=cr.KP_CONF_MIN)
            pr = pd_rest(u_at, r_at, joints, ut_c, rt, set(cr._ANGLE_TRIPLES[jk]))
            dv = None if (a is None or b is None) else abs(a - b)
            return (("-" if dv is None else f"{dv:.1f}도")
                    + ("/-" if pr is None else f"/{pr:.3f}"), dv, pr)

        so, dvo, pro = shot(o)
        sn, dvn, prn = shot(n)
        mark = ""
        if dvo is not None and dvn is not None:
            mark = ("  차이↑" if dvn > dvo else "  차이↓")
            if pro is not None and prn is not None:
                mark += " 정렬" + ("↑" if prn < pro else "↓")
        elif dvo is None and dvn is not None:
            mark = "  미표시→표시"
        elif dvo is not None and dvn is None:
            mark = "  표시→미표시"
        over = ""
        if o["atVideoSec"] * afps > uF - 1:
            over = f"  ★현행이 클립 밖({o['atVideoSec']*afps:.0f}>{uF-1})"
        print(f"  {rid:<5}{(jk or r['criterion'])[:15]:<15}"
              f"{o['atVideoSec']:7.2f}/{o['refVideoSec']:<7.2f}"
              f"{n['atVideoSec']:7.2f}/{n['refVideoSec']:<7.2f}{du:>+9.1f}"
              f"   {so} → {sn}{mark}{over}")


if __name__ == "__main__":
    vdir = Path(sys.argv[1])
    for c in (sys.argv[2:] or ["elbow", "pdshapefault", "peterpan", "powerspin"]):
        run(vdir, c)
