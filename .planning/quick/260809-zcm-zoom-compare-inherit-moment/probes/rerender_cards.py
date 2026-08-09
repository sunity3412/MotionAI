"""확대 비교 카드 로컬 재현 하네스 (관찰/실험 전용 — 프로덕션 무접촉).

저장된 keypointReport + S3 영상만으로 fault_zoom 의 **실제 함수**를 호출해
criterion 카드 1장을 재현한다. GPU 불필요(포즈는 이미 doc 에 있다).

  base : 현행 게이트(_KP_CONF_MIN=0.5) 그대로 → 프로덕션 PNG 와 대조용
  open : 게이트를 열고(conf 무시) 그릴 수 있는 건 다 그림 → "낮은 신뢰 좌표로
         그리면 실제로 어디에 찍히는가"를 눈으로 보기 위한 실험

usage: python3 rerender_cards.py <uid> <aid> <user.mp4> <ref.mp4> <outdir>
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402


def frames_of(path: str, cache: pathlib.Path) -> np.ndarray:
    if cache.exists():
        return np.load(cache)
    arr = FfmpegFrameExtractor(target_fps=9.0, max_side=640).extract(path)
    np.save(cache, arr)
    return arr


def render_card(card, u_rep, r_rep, u_frames, r_frames, motion_id, conf_min):
    """production 경로(criterion 카드)를 그대로 밟아 (png, 사유) 반환."""
    old = fz._KP_CONF_MIN
    fz._KP_CONF_MIN = conf_min
    try:
        joint, crit = card["joint"], card.get("criterion")
        members = (joint,)
        ukp, rkp = int(card["userFrameIdx"]), int(card["refFrameIdx"])
        u_idx = int(round(float(card["userVideoSec"]) * 9.0))
        r_idx = int(round(float(card["refVideoSec"]) * 9.0))
        u_frame = u_frames[min(u_idx, len(u_frames) - 1)]
        r_frame = r_frames[min(r_idx, len(r_frames) - 1)]

        u_valid, u_relaxed = fz._member_pts(u_rep, ukp, members)
        r_valid, r_relaxed = fz._member_pts(r_rep, rkp, members)
        r_res = fz.make_reference_anchor_resolver(motion_id, crit)

        u_vertex = fz.criterion_vertex_xy(crit, members, u_rep, ukp, None, fz._gated_kp)
        r_vertex = fz.criterion_vertex_xy(crit, members, r_rep, rkp, None, r_res)
        shared_side = None
        if u_vertex is not None and r_vertex is not None:
            shared_side = max(16, int(round(min(
                min(u_frame.shape[0], u_frame.shape[1]),
                min(r_frame.shape[0], r_frame.shape[1]),
            ) * fz._CRITERION_CROP_FRAC)))
        else:
            u_vertex = r_vertex = None

        u_img, u_kind, u_anchor, u_box = fz._side_crop(
            u_frame, [xy for _n, xy in u_valid], u_relaxed,
            anchor=fz._anchor_xy(u_valid, None) if u_valid else None,
            center=u_vertex, side_override=shared_side)
        r_img, r_kind, r_anchor, r_box = fz._side_crop(
            r_frame, [xy for _n, xy in r_valid], r_relaxed,
            anchor=fz._anchor_xy(r_valid, None) if r_valid else None,
            center=r_vertex, side_override=shared_side)

        reason, drew = "unmapped", False
        if u_kind != "valid" or u_box is None:
            reason = "user_crop_relaxed"
        elif r_kind != "valid" or r_box is None:
            reason = "ref_crop_relaxed"
        else:
            u_spec = fz.build_angle_bake_spec(crit, members, u_rep, ukp, fz._gated_kp)
            r_spec = fz.build_angle_bake_spec(crit, members, r_rep, rkp, r_res)
            if u_spec is None:
                reason = "user_gate"
            elif r_spec is None:
                reason = "ref_gate"
            else:
                ut, rt = u_img.copy(), r_img.copy()
                uo = fz._draw_side_joint_angle(ut, u_frame, u_spec, u_box)
                ro = uo and fz._draw_side_joint_angle(rt, r_frame, r_spec, r_box)
                if uo and ro:
                    u_img, r_img, drew, reason = ut, rt, True, "drawn"
                else:
                    reason = "degenerate"

        u_crop = (fz._mark(u_img, circle=False, anchor_px=None) if drew
                  else fz._mark(u_img, circle=u_kind == "valid", anchor_px=u_anchor))
        if not drew:
            r_img = fz._mark(r_img, circle=r_kind == "valid", anchor_px=r_anchor)
        u_crop = fz._stamp_time(u_crop, float(card["userVideoSec"]))
        return fz._compose(u_crop, r_img), reason
    finally:
        fz._KP_CONF_MIN = old


def main():
    uid, aid, uvid, rvid, outdir = sys.argv[1:6]
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    doc = (fa._db().collection("users").document(uid)
           .collection("analyses").document(aid).get().to_dict())
    res = doc["result"]
    mid = doc.get("referenceMotionId")
    u_rep = res["keypointReport"]
    r_rep = (fa.get_reference_motion(mid) or {})["referenceKeypointReport"]
    u_frames = frames_of(uvid, out / "_u.npy")
    r_frames = frames_of(rvid, out / "_r.npy")
    print(f"frames user={u_frames.shape} ref={r_frames.shape}")

    for i, card in enumerate(res.get("faultZoomComparisons") or []):
        if not card.get("criterion") or "refVideoSec" not in card:
            print(f"[{i}] {card.get('joint')} skip (advisory/ref미대응)")
            continue
        for tag, cm in (("base", 0.5), ("open", 0.0)):
            png, reason = render_card(card, u_rep, r_rep, u_frames, r_frames, mid, cm)
            p = out / f"{i}_{card['joint']}__{tag}.png"
            p.write_bytes(png)
            print(f"[{i}] {card['joint']:<15} {tag}: {reason:<18} -> {p.name}")


if __name__ == "__main__":
    main()
