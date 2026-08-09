"""프레임 위에 저장된 keypoint 전건을 이름·신뢰도와 함께 찍는다 (관찰 전용).

각도가 맞는 자리에 그려지는지 판단하려면 먼저 **포즈 자체가 맞는지** 봐야 한다.
usage: python3 plot_pose.py <uid> <aid> <user.mp4|ref.mp4> <user|ref> <repIdx> <videoSec> <out.png>
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

BONES = [
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_hand"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_hand"),
    ("left_shoulder", "right_shoulder"), ("left_hip", "right_hip"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
]


def main():
    uid, aid, vid, side, rep_idx, sec, outp = sys.argv[1:8]
    rep_idx, sec = int(rep_idx), float(sec)
    doc = (fa._db().collection("users").document(uid)
           .collection("analyses").document(aid).get().to_dict())
    mid = doc.get("referenceMotionId")
    rep = (doc["result"]["keypointReport"] if side == "user"
           else (fa.get_reference_motion(mid) or {})["referenceKeypointReport"])

    cache = pathlib.Path(outp).with_suffix(f".{side}.npy")
    if cache.exists():
        frames = np.load(cache)
    else:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        frames = FfmpegFrameExtractor(target_fps=9.0, max_side=640).extract(vid)
        np.save(cache, frames)
    f = frames[min(int(round(sec * 9.0)), len(frames) - 1)]
    img = Image.fromarray(f).convert("RGB")
    # 2배 확대해 라벨이 읽히게
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    W, H = img.size

    def px(j):
        xy = fz._kp_xy(rep, rep_idx, j)
        return None if xy is None else (xy[0] * W, xy[1] * H)

    for a, b in BONES:
        pa, pb = px(a), px(b)
        if pa and pb:
            d.line([pa, pb], fill=(0, 160, 255), width=3)
    for j in (rep.get("joints") or []):
        p = px(j)
        if not p:
            continue
        c = fz._kp_conf(rep, rep_idx, j)
        hot = c is not None and c < 0.5
        col = (255, 60, 40) if hot else (30, 220, 90)
        d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=col)
        d.text((p[0] + 9, p[1] - 7), f"{j} {c:.2f}" if c is not None else j, fill=col)
    d.text((8, 8), f"{side} rep={rep_idx} sec={sec:.2f}", fill=(255, 255, 0))
    img.save(outp)
    print("wrote", outp, img.size)


if __name__ == "__main__":
    main()
