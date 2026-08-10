"""현행 카드 대 단위교정 카드 실물 뽑기 (belle 판정용 A/B).

`corrected_pairs.py` 는 수치로만 대조한다. belle 이 판정하려면 **사진**이 있어야 하고
(memory `open-the-artifact-before-claiming-done`), 사진은 승인된 경로 그대로 나와야 한다
— 그래서 `compare_render.render(..., zoom_dir=...)` 를 **무접촉으로 두 번** 호출한다:

  A) 현행  = doc·align 그대로
  B) 교정  = record 의 atVideoSec 만 `atFrameIdx / (src_fps/step)` 로 바꾸고
            `compare_align.select_pairs` 를 그대로 재호출해 align.pairs 재생성

렌더러·짝선정·정렬 로직 diff 0. 바뀌는 것은 입력의 초 하나뿐이다.

usage: render_zoom_ab.py <video_dir> <out_dir> <case> [ref_video_name]
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

from sunity_shared.analysis import compare_align as ca  # noqa: E402
from sunity_shared.analysis import compare_render as cr  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"
TARGET_FPS = 9.0
USER_VIDEO = {
    "pdshapefault": "pdshapefault1785373695.mp4",
    "peterpan": "peterpanfault1785373695.mp4",
    "elbow": "elbow_fault.mp4",
    "powerspin": "powerspin_fault.mp4",
}
REF_VIDEO = {
    "pdshapefault": "ref-pdshape.mp4",
    "peterpan": "ref-peter-pan.mp4",
    "elbow": "ref-elbow-twist-sister.mp4",
    "powerspin": "ref-power-spin.mp4",
}


def src_fps(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True).stdout.strip()
    num, den = out.split("/")
    return float(num) / float(den)


def dummy_audio(doc: dict, adir: Path):
    """render 는 mp3 길이만 쓴다 — 무음 더미로 대체 (SUMMARY 260809-zcm 절차)."""
    adir.mkdir(parents=True, exist_ok=True)
    recs = (doc["result"].get("deductionBreakdown") or {}).get("records") or []
    for i, _ in enumerate(recs):
        p = adir / f"r{i:02d}.mp3"
        if not p.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                            "-i", "anullsrc", "-t", "2.2", str(p)], check=True)


def corrected(doc: dict, align: dict, rfps: float) -> tuple[dict, dict]:
    recs = (doc["result"].get("deductionBreakdown") or {}).get("records") or []
    doc2 = json.loads(json.dumps(doc))
    recs2 = (doc2["result"]["deductionBreakdown"]["records"])
    for r in recs2:
        if r.get("atFrameIdx") is not None:
            r["atVideoSec"] = float(r["atFrameIdx"]) / rfps

    uF, rF = int(align["userFrames"]), int(align["refFrames"])
    ukn = np.asarray(align["userKp"], dtype=float).reshape(uF, 17, 2)
    rkn = np.asarray(align["refKp"], dtype=float).reshape(rF, 17, 2)
    usc = np.asarray(align["userScore"], dtype=float)
    rsc = np.asarray(align["refScore"], dtype=float)
    fu, fr = ca.pose_feature(ukn, usc), ca.pose_feature(rkn, rsc)
    D = np.linalg.norm(fu[:, None, :] - fr[None, :, :], axis=2)
    curve = ca.smooth_curve(ca.dtw_path(D), len(fu))
    align2 = dict(align)
    align2["pairs"] = ca.select_pairs(recs2, D, curve, ukn, usc, rsc)
    _ = recs  # 원본은 손대지 않는다
    return doc2, align2


def main():
    vdir, odir, case = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    d = ROOT / case
    doc = json.load(open(d / "doc.json"))
    align = json.load(open(d / "align.json"))
    uv, rv = vdir / USER_VIDEO[case], vdir / REF_VIDEO[case]
    rfps = src_fps(uv) / max(1, round(src_fps(uv) / TARGET_FPS))
    print(f"{case}: 실제 {rfps:.3f}fps")

    odir.mkdir(parents=True, exist_ok=True)
    adir = odir / "audio"
    dummy_audio(doc, adir)
    doc2, align2 = corrected(doc, align, rfps)
    json.dump(align2["pairs"], open(odir / f"{case}_pairs_corrected.json", "w"),
              ensure_ascii=False, indent=1)

    for tag, dd, aa in (("A_current", doc, align), ("B_fixed", doc2, align2)):
        wd = odir / f"wk_{case}_{tag}"
        zd = odir / f"zoom_{case}_{tag}"
        out = odir / f"{case}_{tag}.mp4"
        rep = cr.render(dd, uv, rv, adir, wd, out, align_json=aa, zoom_dir=zd)
        made = [p.name for p in sorted(zd.glob("*.png"))] if zd.exists() else []
        print(f"  {tag}: 카드 {len(made)}장 {made}")
        for fz in rep.get("freezes", []):
            print(f"     {fz.get('rid')} userSec={fz.get('userSec')} "
                  f"refSec={fz.get('refSec')} pairSrc={fz.get('pairSrc')}")


if __name__ == "__main__":
    main()
